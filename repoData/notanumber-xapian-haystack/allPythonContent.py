__FILENAME__ = xapian_settings
import os
from settings import *

INSTALLED_APPS += [
    'xapian_tests',
]

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.xapian_backend.XapianEngine',
        'PATH': os.path.join('tmp', 'test_xapian_query'),
        'INCLUDE_SPELLING': True,
    }
}

########NEW FILE########
__FILENAME__ = models
from django.db import models


class Document(models.Model):
    type_name = models.CharField(max_length=50)
    number = models.IntegerField()
    name = models.CharField(max_length=200)

    date = models.DateField()

    summary = models.TextField()
    text = models.TextField()

########NEW FILE########
__FILENAME__ = search_indexes
from haystack import indexes

from . import models


class DocumentIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True)
    summary = indexes.CharField(model_attr='summary')

    type_name = indexes.CharField(model_attr='type_name')

    number = indexes.IntegerField(model_attr='number')

    name = indexes.CharField(model_attr='name')
    date = indexes.DateField(model_attr='date')

    tags = indexes.MultiValueField()

    def get_model(self):
        return models.Document()

    def prepare_tags(self, obj):
        l = [['tag', 'tag-test', 'tag-test-test'],
             ['tag', 'tag-test'],
             ['tag']]
        return l[obj.id % 3]

########NEW FILE########
__FILENAME__ = test_backend
from __future__ import unicode_literals

import datetime
import sys
import xapian
import subprocess
import os

from django.db import models
from django.test import TestCase

from haystack import connections
from haystack import indexes
from haystack.backends.xapian_backend import InvalidIndexError, _term_to_xapian_value
from haystack.utils.loading import UnifiedIndex

from core.models import MockTag, MockModel, AnotherMockModel
from core.tests.mocks import MockSearchResult


def get_terms(backend, *args):
    result = subprocess.check_output(['delve'] + list(args) + [backend.path],
                                     env=os.environ.copy()).decode('utf-8')
    result = result.split(": ")[1].strip()
    return result.split(" ")


def pks(results):
    return [result.pk for result in results]


class XapianMockModel(models.Model):
    """
    Same as tests.core.MockModel with a few extra fields for testing various
    sorting and ordering criteria.
    """
    author = models.CharField(max_length=255)
    foo = models.CharField(max_length=255, blank=True)
    pub_date = models.DateTimeField(default=datetime.datetime.now)
    exp_date = models.DateTimeField(default=datetime.datetime.now)
    tag = models.ForeignKey(MockTag)

    value = models.IntegerField(default=0)
    flag = models.BooleanField(default=True)
    slug = models.SlugField()
    popularity = models.FloatField(default=0.0)
    url = models.URLField()

    def __unicode__(self):
        return self.author


class XapianMockSearchIndex(indexes.SearchIndex):
    text = indexes.CharField(
        document=True, use_template=True,
        template_name='search/indexes/core/mockmodel_text.txt'
    )
    name = indexes.CharField(model_attr='author', faceted=True)
    pub_date = indexes.DateField(model_attr='pub_date')
    exp_date = indexes.DateField(model_attr='exp_date')
    value = indexes.IntegerField(model_attr='value')
    flag = indexes.BooleanField(model_attr='flag')
    slug = indexes.CharField(indexed=False, model_attr='slug')
    popularity = indexes.FloatField(model_attr='popularity')
    month = indexes.CharField(indexed=False)
    url = indexes.CharField(model_attr='url')
    empty = indexes.CharField()

    # Various MultiValueFields
    sites = indexes.MultiValueField()
    tags = indexes.MultiValueField()
    keys = indexes.MultiValueField()
    titles = indexes.MultiValueField()

    def get_model(self):
        return XapianMockModel

    def prepare_sites(self, obj):
        return ['%d' % (i * obj.id) for i in range(1, 4)]

    def prepare_tags(self, obj):
        if obj.id == 1:
            return ['a', 'b', 'c']
        elif obj.id == 2:
            return ['ab', 'bc', 'cd']
        else:
            return ['an', 'to', 'or']

    def prepare_keys(self, obj):
        return [i * obj.id for i in range(1, 4)]

    def prepare_titles(self, obj):
        if obj.id == 1:
            return ['object one title one', 'object one title two']
        elif obj.id == 2:
            return ['object two title one', 'object two title two']
        else:
            return ['object three title one', 'object three title two']

    def prepare_month(self, obj):
        return '%02d' % obj.pub_date.month

    def prepare_empty(self, obj):
        return ''


class XapianSimpleMockIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True)
    author = indexes.CharField(model_attr='author')
    url = indexes.CharField()
    non_anscii = indexes.CharField()
    funny_text = indexes.CharField()

    datetime = indexes.DateTimeField(model_attr='pub_date')
    date = indexes.DateField()

    number = indexes.IntegerField()
    float_number = indexes.FloatField()
    decimal_number = indexes.DecimalField()

    multi_value = indexes.MultiValueField()

    def get_model(self):
        return MockModel

    def prepare_text(self, obj):
        return 'this_is_a_word inside a big text'

    def prepare_author(self, obj):
        return 'david holland'

    def prepare_url(self, obj):
        return 'http://example.com/1/'

    def prepare_non_anscii(self, obj):
        return 'thsi sdas das corrup\xe7\xe3o das'

    def prepare_funny_text(self, obj):
        return 'this-text has funny.words!!'

    def prepare_datetime(self, obj):
        return datetime.datetime(2009, 2, 25, 1, 1, 1)

    def prepare_date(self, obj):
        return datetime.date(2008, 8, 8)

    def prepare_number(self, obj):
        return 123456789

    def prepare_float_number(self, obj):
        return 123.123456789

    def prepare_decimal_number(self, obj):
        return '22.34'

    def prepare_multi_value(self, obj):
        return ['tag', 'tag-tag', 'tag-tag-tag']


class HaystackBackendTestCase(object):
    """
    Abstract TestCase that implements an hack to ensure `connections`
    has the right index

    It has a method get_index() that returns a SearchIndex
    that must be overwritten.
    """
    def get_index(self):
        raise NotImplementedError

    def get_objects(self):
        raise NotImplementedError

    def setUp(self):
        self.old_ui = connections['default'].get_unified_index()
        self.ui = UnifiedIndex()
        self.index = self.get_index()
        self.ui.build(indexes=[self.index])
        self.backend = connections['default'].get_backend()
        connections['default']._index = self.ui

    def tearDown(self):
        self.backend.clear()
        connections['default']._index = self.old_ui


class BackendIndexationTestCase(HaystackBackendTestCase, TestCase):
    """
    Tests indexation behavior.

    Tests related to how the backend indexes terms,
    values, and others go here.
    """

    def get_index(self):
        return XapianSimpleMockIndex()

    def setUp(self):
        super(BackendIndexationTestCase, self).setUp()
        mock = XapianMockModel()
        mock.id = 1
        self.backend.update(self.index, [mock])

    def test_app_is_not_split(self):
        """
        Tests that the app path is not split
        and added as independent terms.
        """
        terms = get_terms(self.backend, '-a')

        self.assertFalse('tests' in terms)
        self.assertFalse('Ztest' in terms)

    def test_app_is_not_indexed(self):
        """
        Tests that the app path is not indexed.
        """
        terms = get_terms(self.backend, '-a')

        self.assertFalse('tests.xapianmockmodel.1' in terms)
        self.assertFalse('xapianmockmodel' in terms)
        self.assertFalse('tests' in terms)

    def test_fields_exist(self):
        """
        Tests that all fields are in the database
        """
        terms = get_terms(self.backend, '-a')
        for field in ['author', 'datetime', 'text', 'url']:
            is_inside = False
            for term in terms:
                if term.startswith("X%s" % field.upper()):
                    is_inside = True
                    break
            self.assertTrue(is_inside, field)

    def test_text_field(self):
        terms = get_terms(self.backend, '-a')
        self.assertTrue('this_is_a_word' in terms)
        self.assertTrue('Zthis_is_a_word' in terms)
        self.assertTrue('ZXTEXTthis_is_a_word' in terms)
        self.assertTrue('XTEXTthis_is_a_word' in terms)

        self.assertFalse('^this_is_a_word inside a big text$' in terms)

    def test_text_posting(self):
        """
        Tests that text is correctly positioned in the document
        """
        expected_order = ['^', 'this_is_a_word', 'inside', 'a', 'big', 'text', '$']

        def get_positions(term):
            """
            Uses delve to get
            the positions of the term in the first document.
            """
            return sorted([int(pos) for pos in get_terms(self.backend, '-r1', '-tXTEXT%s' % term)])

        # confirms expected_order
        previous_position = get_positions(expected_order[0])
        for term in expected_order[1:]:
            pos = get_positions(term)
            # only two positions per term
            # (one from term_generator, one from literal text)
            self.assertEqual(len(pos), 2)

            self.assertEqual(pos[0] - 1, previous_position[0])
            self.assertEqual(pos[1] - 1, previous_position[1])
            previous_position[0] += 1
            previous_position[1] += 1

    def test_author_field(self):
        terms = get_terms(self.backend, '-a')

        self.assertTrue('XAUTHORdavid' in terms)
        self.assertTrue('ZXAUTHORdavid' in terms)
        self.assertTrue('Zdavid' in terms)
        self.assertTrue('david' in terms)

    def test_funny_text_field(self):
        terms = get_terms(self.backend, '-r1')
        self.assertTrue('this-text' in terms)

    def test_datetime_field(self):
        terms = get_terms(self.backend, '-a')

        self.assertFalse('XDATETIME20090225000000' in terms)
        self.assertFalse('ZXDATETIME20090225000000' in terms)
        self.assertFalse('20090225000000' in terms)

        self.assertTrue('XDATETIME2009-02-25' in terms)
        self.assertTrue('2009-02-25' in terms)
        self.assertTrue('01:01:01' in terms)
        self.assertTrue('XDATETIME01:01:01' in terms)

    def test_date_field(self):
        terms = get_terms(self.backend, '-a')

        self.assertTrue('XDATE2008-08-08' in terms)
        self.assertTrue('2008-08-08' in terms)
        self.assertFalse('XDATE00:00:00' in terms)
        self.assertFalse('00:00:00' in terms)

    def test_url_field(self):
        terms = get_terms(self.backend, '-a')
        self.assertTrue('http://example.com/1/' in terms)

    def test_integer_field(self):
        terms = get_terms(self.backend, '-a')
        self.assertTrue('123456789' in terms)
        self.assertTrue('XNUMBER123456789' in terms)
        self.assertFalse('ZXNUMBER123456789' in terms)

    def test_float_field(self):
        terms = get_terms(self.backend, '-a')
        self.assertTrue('123.123456789' in terms)
        self.assertTrue('XFLOAT_NUMBER123.123456789' in terms)
        self.assertFalse('ZXFLOAT_NUMBER123.123456789' in terms)

    def test_decimal_field(self):
        terms = get_terms(self.backend, '-a')
        self.assertTrue('22.34' in terms)
        self.assertTrue('XDECIMAL_NUMBER22.34' in terms)
        self.assertFalse('ZXDECIMAL_NUMBER22.34' in terms)

    def test_multivalue_field(self):
        """
        Regression test for #103
        """
        terms = get_terms(self.backend, '-a')
        self.assertTrue('tag' in terms)
        self.assertTrue('tag-tag' in terms)
        self.assertTrue('tag-tag-tag' in terms)

        self.assertTrue('XMULTI_VALUEtag' in terms)
        self.assertTrue('XMULTI_VALUEtag-tag' in terms)
        self.assertTrue('XMULTI_VALUEtag-tag-tag' in terms)

    def test_non_ascii_chars(self):
        terms = get_terms(self.backend, '-a')
        self.assertIn('corrup\xe7\xe3o', terms)


class BackendFeaturesTestCase(HaystackBackendTestCase, TestCase):
    """
    Tests supported features on the backend side.

    Tests to features implemented on the backend
    go here.
    """

    def get_index(self):
        return XapianMockSearchIndex()

    def setUp(self):
        super(BackendFeaturesTestCase, self).setUp()

        self.sample_objs = []

        for i in range(1, 4):
            mock = XapianMockModel()
            mock.id = i
            mock.author = 'david%s' % i
            mock.pub_date = datetime.date(2009, 2, 25) - datetime.timedelta(days=i)
            mock.exp_date = datetime.date(2009, 2, 23) + datetime.timedelta(days=i)
            mock.value = i * 5
            mock.flag = bool(i % 2)
            mock.slug = 'http://example.com/%d/' % i
            mock.url = 'http://example.com/%d/' % i
            self.sample_objs.append(mock)

        self.sample_objs[0].popularity = 834.0
        self.sample_objs[1].popularity = 35.5
        self.sample_objs[2].popularity = 972.0

        self.backend.update(self.index, self.sample_objs)

    def test_update(self):
        self.assertEqual(pks(self.backend.search(xapian.Query(''))['results']),
                         [1, 2, 3])

    def test_duplicate_update(self):
        """
        Regression test for #6.
        """
        self.backend.update(self.index, self.sample_objs)
        self.assertEqual(self.backend.document_count(), 3)

    def test_remove(self):
        self.backend.remove(self.sample_objs[0])
        self.assertEqual(pks(self.backend.search(xapian.Query(''))['results']),
                         [2, 3])

    def test_clear(self):
        self.backend.clear()
        self.assertEqual(self.backend.document_count(), 0)

        self.backend.update(self.index, self.sample_objs)
        self.assertEqual(self.backend.document_count(), 3)

        self.backend.clear([AnotherMockModel])
        self.assertEqual(self.backend.document_count(), 3)

        self.backend.clear([XapianMockModel])
        self.assertEqual(self.backend.document_count(), 0)

        self.backend.update(self.index, self.sample_objs)
        self.assertEqual(self.backend.document_count(), 3)

        self.backend.clear([AnotherMockModel, XapianMockModel])
        self.assertEqual(self.backend.document_count(), 0)

    def test_search(self):
        # no match query
        self.assertEqual(self.backend.search(xapian.Query()), {'hits': 0, 'results': []})
        # all match query
        self.assertEqual(pks(self.backend.search(xapian.Query(''))['results']),
                         [1, 2, 3])

        # Other `result_class`
        self.assertTrue(isinstance(self.backend.search(xapian.Query('indexed'),
                                                       result_class=MockSearchResult)['results'][0],
                                   MockSearchResult))

    def test_search_field_with_punctuation(self):
        self.assertEqual(pks(self.backend.search(xapian.Query('http://example.com/1/'))['results']),
                         [1])

    def test_search_by_mvf(self):
        self.assertEqual(self.backend.search(xapian.Query('ab'))['hits'], 1)
        self.assertEqual(self.backend.search(xapian.Query('b'))['hits'], 1)
        self.assertEqual(self.backend.search(xapian.Query('to'))['hits'], 1)
        self.assertEqual(self.backend.search(xapian.Query('one'))['hits'], 3)

    def test_field_facets(self):
        self.assertEqual(self.backend.search(xapian.Query(), facets=['name']),
                         {'hits': 0, 'results': []})

        results = self.backend.search(xapian.Query('indexed'), facets=['name'])
        self.assertEqual(results['hits'], 3)
        self.assertEqual(results['facets']['fields']['name'],
                         [('david1', 1), ('david2', 1), ('david3', 1)])

        results = self.backend.search(xapian.Query('indexed'), facets=['flag'])
        self.assertEqual(results['hits'], 3)
        self.assertEqual(results['facets']['fields']['flag'],
                         [(False, 1), (True, 2)])

        results = self.backend.search(xapian.Query('indexed'), facets=['sites'])
        self.assertEqual(results['hits'], 3)
        self.assertEqual(results['facets']['fields']['sites'],
                         [('1', 1), ('3', 2), ('2', 2), ('4', 1), ('6', 2), ('9', 1)])

    def test_raise_index_error_on_wrong_field(self):
        """
        Regression test for #109.
        """
        self.assertRaises(InvalidIndexError, self.backend.search, xapian.Query(''), facets=['dsdas'])

    def test_date_facets(self):
        facets = {'pub_date': {'start_date': datetime.datetime(2008, 10, 26),
                               'end_date': datetime.datetime(2009, 3, 26),
                               'gap_by': 'month'}}

        self.assertEqual(self.backend.search(xapian.Query(), date_facets=facets),
                         {'hits': 0, 'results': []})

        results = self.backend.search(xapian.Query('indexed'), date_facets=facets)
        self.assertEqual(results['hits'], 3)
        self.assertEqual(results['facets']['dates']['pub_date'], [
            ('2009-02-26T00:00:00', 0),
            ('2009-01-26T00:00:00', 3),
            ('2008-12-26T00:00:00', 0),
            ('2008-11-26T00:00:00', 0),
            ('2008-10-26T00:00:00', 0),
        ])

        facets = {'pub_date': {'start_date': datetime.datetime(2009, 2, 1),
                               'end_date': datetime.datetime(2009, 3, 15),
                               'gap_by': 'day',
                               'gap_amount': 15}}
        results = self.backend.search(xapian.Query('indexed'), date_facets=facets)
        self.assertEqual(results['hits'], 3)
        self.assertEqual(results['facets']['dates']['pub_date'], [
            ('2009-03-03T00:00:00', 0),
            ('2009-02-16T00:00:00', 3),
            ('2009-02-01T00:00:00', 0)
        ])

    def test_query_facets(self):
        self.assertEqual(self.backend.search(xapian.Query(), query_facets={'name': 'da*'}),
                         {'hits': 0, 'results': []})

        results = self.backend.search(xapian.Query('indexed'), query_facets={'name': 'da*'})
        self.assertEqual(results['hits'], 3)
        self.assertEqual(results['facets']['queries']['name'], ('da*', 3))

    def test_narrow_queries(self):
        self.assertEqual(self.backend.search(xapian.Query(), narrow_queries={'name:david1'}),
                         {'hits': 0, 'results': []})
        results = self.backend.search(xapian.Query('indexed'), narrow_queries={'name:david1'})
        self.assertEqual(results['hits'], 1)

    def test_highlight(self):
        self.assertEqual(self.backend.search(xapian.Query(), highlight=True),
                         {'hits': 0, 'results': []})
        self.assertEqual(self.backend.search(xapian.Query('indexed'), highlight=True)['hits'], 3)

        results = self.backend.search(xapian.Query('indexed'), highlight=True)['results']
        self.assertEqual([result.highlighted['text'] for result in results],
                         ['<em>indexed</em>!\n1', '<em>indexed</em>!\n2', '<em>indexed</em>!\n3'])

    def test_spelling_suggestion(self):
        self.assertEqual(self.backend.search(xapian.Query('indxe'))['hits'], 0)
        self.assertEqual(self.backend.search(xapian.Query('indxe'))['spelling_suggestion'],
                         'indexed')

        self.assertEqual(self.backend.search(xapian.Query('indxed'))['hits'], 0)
        self.assertEqual(self.backend.search(xapian.Query('indxed'))['spelling_suggestion'],
                         'indexed')

        self.assertEqual(self.backend.search(xapian.Query('foo'))['hits'], 0)
        self.assertEqual(self.backend.search(xapian.Query('foo'), spelling_query='indexy')['spelling_suggestion'],
                         'indexed')

        self.assertEqual(self.backend.search(xapian.Query('XNAMEdavid'))['hits'], 0)
        self.assertEqual(self.backend.search(xapian.Query('XNAMEdavid'))['spelling_suggestion'],
                         'david1')

    def test_more_like_this(self):
        results = self.backend.more_like_this(self.sample_objs[0])

        self.assertEqual(pks(results['results']), [3, 2])

        results = self.backend.more_like_this(self.sample_objs[0],
                                              additional_query=xapian.Query('david3'))

        self.assertEqual(pks(results['results']), [3])

        results = self.backend.more_like_this(self.sample_objs[0],
                                              limit_to_registered_models=True)

        self.assertEqual(pks(results['results']), [3, 2])

        # Other `result_class`
        self.assertTrue(isinstance(self.backend.more_like_this(self.sample_objs[0],
                                                               result_class=MockSearchResult)['results'][0],
                                   MockSearchResult))

    def test_order_by(self):
        results = self.backend.search(xapian.Query(''), sort_by=['pub_date'])
        self.assertEqual(pks(results['results']), [3, 2, 1])

        results = self.backend.search(xapian.Query(''), sort_by=['-pub_date'])
        self.assertEqual(pks(results['results']), [1, 2, 3])

        results = self.backend.search(xapian.Query(''), sort_by=['exp_date'])
        self.assertEqual(pks(results['results']), [1, 2, 3])

        results = self.backend.search(xapian.Query(''), sort_by=['-exp_date'])
        self.assertEqual(pks(results['results']), [3, 2, 1])

        results = self.backend.search(xapian.Query(''), sort_by=['id'])
        self.assertEqual(pks(results['results']), [1, 2, 3])

        results = self.backend.search(xapian.Query(''), sort_by=['-id'])
        self.assertEqual(pks(results['results']), [3, 2, 1])

        results = self.backend.search(xapian.Query(''), sort_by=['value'])
        self.assertEqual(pks(results['results']), [1, 2, 3])

        results = self.backend.search(xapian.Query(''), sort_by=['-value'])
        self.assertEqual(pks(results['results']), [3, 2, 1])

        results = self.backend.search(xapian.Query(''), sort_by=['popularity'])
        self.assertEqual(pks(results['results']), [2, 1, 3])

        results = self.backend.search(xapian.Query(''), sort_by=['-popularity'])
        self.assertEqual(pks(results['results']), [3, 1, 2])

        results = self.backend.search(xapian.Query(''), sort_by=['flag', 'id'])
        self.assertEqual(pks(results['results']), [2, 1, 3])

        results = self.backend.search(xapian.Query(''), sort_by=['flag', '-id'])
        self.assertEqual(pks(results['results']), [2, 3, 1])

    def test_verify_type(self):
        self.assertEqual([result.month for result in self.backend.search(xapian.Query(''))['results']],
                         ['02', '02', '02'])

    def test_term_to_xapian_value(self):
        self.assertEqual(_term_to_xapian_value('abc', 'text'), 'abc')
        self.assertEqual(_term_to_xapian_value(1, 'integer'), '000000000001')
        self.assertEqual(_term_to_xapian_value(2653, 'integer'), '000000002653')
        self.assertEqual(_term_to_xapian_value(25.5, 'float'), b'\xb2`')
        self.assertEqual(_term_to_xapian_value([1, 2, 3], 'text'), '[1, 2, 3]')
        self.assertEqual(_term_to_xapian_value((1, 2, 3), 'text'), '(1, 2, 3)')
        self.assertEqual(_term_to_xapian_value({'a': 1, 'c': 3, 'b': 2}, 'text'),
                         "{u'a': 1, u'c': 3, u'b': 2}")
        self.assertEqual(_term_to_xapian_value(datetime.datetime(2009, 5, 9, 16, 14), 'datetime'),
                         '20090509161400')
        self.assertEqual(_term_to_xapian_value(datetime.datetime(2009, 5, 9, 0, 0), 'date'),
                         '20090509000000')
        self.assertEqual(_term_to_xapian_value(datetime.datetime(1899, 5, 18, 0, 0), 'date'),
                         '18990518000000')

    def test_build_schema(self):
        search_fields = connections['default'].get_unified_index().all_searchfields()
        (content_field_name, fields) = self.backend.build_schema(search_fields)

        self.assertEqual(content_field_name, 'text')
        self.assertEqual(len(fields), 14 + 3)
        self.assertEqual(fields, [
            {'column': 0, 'type': 'text', 'field_name': 'id', 'multi_valued': 'false'},
            {'column': 1, 'type': 'integer', 'field_name': 'django_id', 'multi_valued': 'false'},
            {'column': 2, 'type': 'text', 'field_name': 'django_ct', 'multi_valued': 'false'},
            {'column': 3, 'type': 'text', 'field_name': 'empty', 'multi_valued': 'false'},
            {'column': 4, 'type': 'date', 'field_name': 'exp_date', 'multi_valued': 'false'},
            {'column': 5, 'type': 'boolean', 'field_name': 'flag', 'multi_valued': 'false'},
            {'column': 6, 'type': 'text', 'field_name': 'keys', 'multi_valued': 'true'},
            {'column': 7, 'type': 'text', 'field_name': 'name', 'multi_valued': 'false'},
            {'column': 8, 'type': 'text', 'field_name': 'name_exact', 'multi_valued': 'false'},
            {'column': 9, 'type': 'float', 'field_name': 'popularity', 'multi_valued': 'false'},
            {'column': 10, 'type': 'date', 'field_name': 'pub_date', 'multi_valued': 'false'},
            {'column': 11, 'type': 'text', 'field_name': 'sites', 'multi_valued': 'true'},
            {'column': 12, 'type': 'text', 'field_name': 'tags', 'multi_valued': 'true'},
            {'column': 13, 'type': 'text', 'field_name': 'text', 'multi_valued': 'false'},
            {'column': 14, 'type': 'text', 'field_name': 'titles', 'multi_valued': 'true'},
            {'column': 15, 'type': 'text', 'field_name': 'url', 'multi_valued': 'false'},
            {'column': 16, 'type': 'integer', 'field_name': 'value', 'multi_valued': 'false'}
        ])

    def test_parse_query(self):
        self.assertEqual(str(self.backend.parse_query('indexed')),
                         'Xapian::Query(Zindex:(pos=1))')
        self.assertEqual(str(self.backend.parse_query('name:david')),
                         'Xapian::Query(ZXNAMEdavid:(pos=1))')

        if xapian.minor_version() >= 2:
            self.assertEqual(str(self.backend.parse_query('name:da*')),
                             'Xapian::Query(('
                             'XNAMEdavid1:(pos=1) SYNONYM '
                             'XNAMEdavid2:(pos=1) SYNONYM '
                             'XNAMEdavid3:(pos=1)))')
        else:
            self.assertEqual(str(self.backend.parse_query('name:da*')),
                             'Xapian::Query(('
                             'XNAMEdavid1:(pos=1) OR '
                             'XNAMEdavid2:(pos=1) OR '
                             'XNAMEdavid3:(pos=1)))')

        self.assertEqual(str(self.backend.parse_query('name:david1..david2')),
                         'Xapian::Query(VALUE_RANGE 7 david1 david2)')
        self.assertEqual(str(self.backend.parse_query('value:0..10')),
                         'Xapian::Query(VALUE_RANGE 16 000000000000 000000000010)')
        self.assertEqual(str(self.backend.parse_query('value:..10')),
                         'Xapian::Query(VALUE_RANGE 16 %012d 000000000010)' % (-sys.maxsize - 1))
        self.assertEqual(str(self.backend.parse_query('value:10..*')),
                         'Xapian::Query(VALUE_RANGE 16 000000000010 %012d)' % sys.maxsize)
        self.assertEqual(str(self.backend.parse_query('popularity:25.5..100.0')),
                         b'Xapian::Query(VALUE_RANGE 9 \xb2` \xba@)')

    def test_order_by_django_id(self):
        """
        We need this test because ordering on more than
        10 entries was not correct at some point.
        """
        self.sample_objs = []
        number_list = list(range(1, 101))
        for i in number_list:
            mock = XapianMockModel()
            mock.id = i
            mock.author = 'david%s' % i
            mock.pub_date = datetime.date(2009, 2, 25) - datetime.timedelta(days=i)
            mock.exp_date = datetime.date(2009, 2, 23) + datetime.timedelta(days=i)
            mock.value = i * 5
            mock.flag = bool(i % 2)
            mock.slug = 'http://example.com/%d/' % i
            mock.url = 'http://example.com/%d/' % i
            mock.popularity = i*2
            self.sample_objs.append(mock)

        self.backend.clear()
        self.backend.update(self.index, self.sample_objs)

        results = self.backend.search(xapian.Query(''), sort_by=['-django_id'])
        self.assertEqual(pks(results['results']), list(reversed(number_list)))

    def test_more_like_this_with_unindexed_model(self):
        """
        Tests that more_like_this raises an error when it is called
         with an unindexed model and if silently_fail is True.
         Also tests the other way around.
        """
        mock = XapianMockModel()
        mock.id = 10
        mock.author = 'david10'

        try:
            self.assertEqual(self.backend.more_like_this(mock)['results'], [])
        except InvalidIndexError:
            self.fail("InvalidIndexError raised when silently_fail is True")

        self.backend.silently_fail = False
        self.assertRaises(InvalidIndexError, self.backend.more_like_this, mock)

########NEW FILE########
__FILENAME__ = test_interface
from __future__ import unicode_literals

import datetime
from django.db.models import Q
from django.test import TestCase

from haystack import connections
from haystack.inputs import AutoQuery
from haystack.query import SearchQuerySet

from xapian_tests.models import Document
from xapian_tests.search_indexes import DocumentIndex
from xapian_tests.tests.test_backend import pks, get_terms


class InterfaceTestCase(TestCase):
    """
    Tests the interface of Xapian-Haystack.

    Tests related to usability and expected behavior
    go here.
    """

    def setUp(self):
        super(InterfaceTestCase, self).setUp()

        types_names = ['book', 'magazine', 'article']
        texts = ['This is a huge text',
                 'This is a medium text',
                 'This is a small text']
        dates = [datetime.date(year=2010, month=1, day=1),
                 datetime.date(year=2010, month=2, day=1),
                 datetime.date(year=2010, month=3, day=1)]

        summaries = ['This is a huge corrup\xe7\xe3o summary',
                     'This is a medium summary',
                     'This is a small summary']

        for i in range(1, 13):
            doc = Document()
            doc.type_name = types_names[i % 3]
            doc.number = i * 2
            doc.name = "%s %d" % (doc.type_name, doc.number)
            doc.date = dates[i % 3]

            doc.summary = summaries[i % 3]
            doc.text = texts[i % 3]
            doc.save()

        self.index = DocumentIndex()
        self.ui = connections['default'].get_unified_index()
        self.ui.build(indexes=[self.index])

        self.backend = connections['default'].get_backend()
        self.backend.update(self.index, Document.objects.all())

        self.queryset = SearchQuerySet()

    def tearDown(self):
        Document.objects.all().delete()
        #self.backend.clear()
        super(InterfaceTestCase, self).tearDown()

    def test_count(self):
        self.assertEqual(self.queryset.count(), Document.objects.count())

    def test_content_search(self):
        result = self.queryset.filter(content='medium this')
        self.assertEqual(sorted(pks(result)),
                         pks(Document.objects.all()))

        # documents with "medium" AND "this" have higher score
        self.assertEqual(pks(result)[:4], [1, 4, 7, 10])

    def test_field_search(self):
        self.assertEqual(pks(self.queryset.filter(name='8')), [4])
        self.assertEqual(pks(self.queryset.filter(type_name='book')),
                         pks(Document.objects.filter(type_name='book')))

        self.assertEqual(pks(self.queryset.filter(text='text huge')),
                         pks(Document.objects.filter(text__contains='text huge')))

    def test_field_contains(self):
        self.assertEqual(pks(self.queryset.filter(summary='huge')),
                         pks(Document.objects.filter(summary__contains='huge')))

        result = self.queryset.filter(summary='huge summary')
        self.assertEqual(sorted(pks(result)),
                         pks(Document.objects.all()))

        # documents with "huge" AND "summary" have higher score
        self.assertEqual(pks(result)[:4], [3, 6, 9, 12])

    def test_field_exact(self):
        self.assertEqual(pks(self.queryset.filter(name__exact='8')), [])
        self.assertEqual(pks(self.queryset.filter(name__exact='magazine 2')), [1])

    def test_content_exact(self):
        self.assertEqual(pks(self.queryset.filter(content__exact='huge')), [])

    def test_content_and(self):
        self.assertEqual(pks(self.queryset.filter(content='huge').filter(summary='medium')), [])

        self.assertEqual(len(self.queryset.filter(content='huge this')), 12)
        self.assertEqual(len(self.queryset.filter(content='huge this').filter(summary='huge')), 4)

    def test_content_or(self):
        self.assertEqual(len(self.queryset.filter(content='huge medium')), 8)
        self.assertEqual(len(self.queryset.filter(content='huge medium small')), 12)

    def test_field_and(self):
        self.assertEqual(pks(self.queryset.filter(name='8').filter(name='4')), [])

    def test_field_or(self):
        self.assertEqual(pks(self.queryset.filter(name='8 4')), [2, 4])

    def test_field_in(self):
        self.assertEqual(set(pks(self.queryset.filter(name__in=['magazine 2', 'article 4']))),
                         set(pks(Document.objects.filter(name__in=['magazine 2', 'article 4']))))

        self.assertEqual(pks(self.queryset.filter(number__in=[4])),
                         pks(Document.objects.filter(number__in=[4])))

        self.assertEqual(pks(self.queryset.filter(number__in=[4, 8])),
                         pks(Document.objects.filter(number__in=[4, 8])))

    def test_private_fields(self):
        self.assertEqual(pks(self.queryset.filter(django_id=4)),
                         pks(Document.objects.filter(id__in=[4])))
        self.assertEqual(pks(self.queryset.filter(django_id__in=[2, 4])),
                         pks(Document.objects.filter(id__in=[2, 4])))

        self.assertEqual(set(pks(self.queryset.models(Document))),
                         set(pks(Document.objects.all())))

    def test_field_startswith(self):
        self.assertEqual(len(self.queryset.filter(name__startswith='magaz')), 4)
        self.assertEqual(set(pks(self.queryset.filter(text__startswith='This is'))),
                         set(pks(Document.objects.filter(text__startswith='This is'))))

    def test_auto_query(self):
        # todo: improve to query text only.
        self.assertEqual(set(pks(self.queryset.auto_query("huge OR medium"))),
                         set(pks(Document.objects.filter(Q(text__contains="huge") |
                                                         Q(text__contains="medium")))))

        self.assertEqual(set(pks(self.queryset.auto_query("huge AND medium"))),
                         set(pks(Document.objects.filter(Q(text__contains="huge") &
                                                         Q(text__contains="medium")))))

        self.assertEqual(set(pks(self.queryset.auto_query("text:huge text:-this"))),
                         set(pks(Document.objects.filter(Q(text__contains="huge") &
                                                         ~Q(text__contains="this")))))

        self.assertEqual(len(self.queryset.filter(name=AutoQuery("8 OR 4"))), 2)
        self.assertEqual(len(self.queryset.filter(name=AutoQuery("8 AND 4"))), 0)

    def test_value_range(self):
        self.assertEqual(set(pks(self.queryset.filter(number__lt=3))),
                         set(pks(Document.objects.filter(number__lt=3))))

        self.assertEqual(set(pks(self.queryset.filter(django_id__gte=6))),
                         set(pks(Document.objects.filter(id__gte=6))))

    def test_date_range(self):
        date = datetime.date(year=2010, month=2, day=1)
        self.assertEqual(set(pks(self.queryset.filter(date__gte=date))),
                         set(pks(Document.objects.filter(date__gte=date))))

        date = datetime.date(year=2010, month=3, day=1)
        self.assertEqual(set(pks(self.queryset.filter(date__lte=date))),
                         set(pks(Document.objects.filter(date__lte=date))))

    def test_order_by(self):
        # private order
        self.assertEqual(pks(self.queryset.order_by("-django_id")),
                         pks(Document.objects.order_by("-id")))

        # value order
        self.assertEqual(pks(self.queryset.order_by("number")),
                         pks(Document.objects.order_by("number")))

        # text order
        self.assertEqual(pks(self.queryset.order_by("summary")),
                         pks(Document.objects.order_by("summary")))

        # date order
        self.assertEqual(pks(self.queryset.order_by("-date")),
                         pks(Document.objects.order_by("-date")))

    def test_non_ascii_search(self):
        """
        Regression test for #119.
        """
        self.assertEqual(pks(self.queryset.filter(content='corrup\xe7\xe3o')),
                         pks(Document.objects.filter(summary__contains='corrup\xe7\xe3o')))

    def test_multi_values_exact_search(self):
        """
        Regression test for #103
        """
        self.assertEqual(len(self.queryset.filter(tags__exact='tag')), 12)
        self.assertEqual(len(self.queryset.filter(tags__exact='tag-test')), 8)
        self.assertEqual(len(self.queryset.filter(tags__exact='tag-test-test')), 4)

########NEW FILE########
__FILENAME__ = test_query
from __future__ import unicode_literals

import datetime

from django.conf import settings
from django.test import TestCase

from haystack import indexes
from haystack import connections, reset_search_queries
from haystack.models import SearchResult
from haystack.query import SearchQuerySet, SQ

from core.models import MockModel, AnotherMockModel, AFourthMockModel
from core.tests.mocks import MockSearchResult
from xapian_tests.tests.test_backend import HaystackBackendTestCase


class MockQueryIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True)
    pub_date = indexes.DateTimeField()
    title = indexes.CharField()
    foo = indexes.CharField()

    def get_model(self):
        return MockModel


class XapianSearchQueryTestCase(HaystackBackendTestCase, TestCase):
    def get_index(self):
        return MockQueryIndex()

    def setUp(self):
        super(XapianSearchQueryTestCase, self).setUp()
        self.sq = connections['default'].get_query()

    def test_build_query_all(self):
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query(<alldocuments>)')

    def test_build_query_single_word(self):
        self.sq.add_filter(SQ(content='hello'))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query((Zhello OR hello))')

    def test_build_query_single_word_not(self):
        self.sq.add_filter(~SQ(content='hello'))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query((<alldocuments> AND_NOT (Zhello OR hello)))')

    def test_build_query_single_word_field_exact(self):
        self.sq.add_filter(SQ(foo='hello'))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query((ZXFOOhello OR XFOOhello))')

    def test_build_query_single_word_field_exact_not(self):
        self.sq.add_filter(~SQ(foo='hello'))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query((<alldocuments> AND_NOT (ZXFOOhello OR XFOOhello)))')

    def test_build_query_boolean(self):
        self.sq.add_filter(SQ(content=True))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query((Ztrue OR true))')

    def test_build_query_date(self):
        self.sq.add_filter(SQ(content=datetime.date(2009, 5, 8)))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query((Z2009-05-08 OR 2009-05-08))')

    def test_build_query_date_not(self):
        self.sq.add_filter(~SQ(content=datetime.date(2009, 5, 8)))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query((<alldocuments> AND_NOT (Z2009-05-08 OR 2009-05-08)))')

    def test_build_query_datetime(self):
        self.sq.add_filter(SQ(content=datetime.datetime(2009, 5, 8, 11, 28)))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query((Z2009-05-08 OR 2009-05-08 OR Z11:28:00 OR 11:28:00))')

    def test_build_query_datetime_not(self):
        self.sq.add_filter(~SQ(content=datetime.datetime(2009, 5, 8, 11, 28)))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query((<alldocuments> AND_NOT '
                         '(Z2009-05-08 OR 2009-05-08 OR Z11:28:00 OR 11:28:00)))')

    def test_build_query_float(self):
        self.sq.add_filter(SQ(content=25.52))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query((Z25.52 OR 25.52))')

    def test_build_query_multiple_words_and(self):
        self.sq.add_filter(SQ(content='hello'))
        self.sq.add_filter(SQ(content='world'))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query(((Zhello OR hello) AND (Zworld OR world)))')

    def test_build_query_multiple_words_not(self):
        self.sq.add_filter(~SQ(content='hello'))
        self.sq.add_filter(~SQ(content='world'))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query(('
                         '(<alldocuments> AND_NOT (Zhello OR hello)) AND '
                         '(<alldocuments> AND_NOT (Zworld OR world))))')

    def test_build_query_multiple_words_or(self):
        self.sq.add_filter(SQ(content='hello') | SQ(content='world'))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query((Zhello OR hello OR Zworld OR world))')

    def test_build_query_multiple_words_or_not(self):
        self.sq.add_filter(~SQ(content='hello') | ~SQ(content='world'))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query(('
                         '(<alldocuments> AND_NOT (Zhello OR hello)) OR '
                         '(<alldocuments> AND_NOT (Zworld OR world))))')

    def test_build_query_multiple_words_mixed(self):
        self.sq.add_filter(SQ(content='why') | SQ(content='hello'))
        self.sq.add_filter(~SQ(content='world'))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query(('
                         '(Zwhi OR why OR Zhello OR hello) AND '
                         '(<alldocuments> AND_NOT (Zworld OR world))))')

    def test_build_query_multiple_word_field_exact(self):
        self.sq.add_filter(SQ(foo='hello'))
        self.sq.add_filter(SQ(title='world'))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query(('
                         '(ZXFOOhello OR XFOOhello) AND '
                         '(ZXTITLEworld OR XTITLEworld)))')

    def test_build_query_multiple_word_field_exact_not(self):
        self.sq.add_filter(~SQ(foo='hello'))
        self.sq.add_filter(~SQ(title='world'))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query(('
                         '(<alldocuments> AND_NOT (ZXFOOhello OR XFOOhello)) AND '
                         '(<alldocuments> AND_NOT (ZXTITLEworld OR XTITLEworld))))')

    def test_build_query_or(self):
        self.sq.add_filter(SQ(content='hello world'))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query((Zhello OR hello OR Zworld OR world))')

    def test_build_query_not_or(self):
        self.sq.add_filter(~SQ(content='hello world'))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query('
                         '(<alldocuments> AND_NOT (Zhello OR hello OR Zworld OR world)))')

    def test_build_query_boost(self):
        self.sq.add_filter(SQ(content='hello'))
        self.sq.add_boost('world', 5)
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query(('
                         '(Zhello OR hello) AND_MAYBE '
                         '5 * (Zworld OR world)))')

    def test_build_query_not_in_filter_single_words(self):
        self.sq.add_filter(SQ(content='why'))
        self.sq.add_filter(~SQ(title__in=["Dune", "Jaws"]))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query('
                         '((Zwhi OR why) AND '
                         '(<alldocuments> AND_NOT ('
                         '(XTITLE^ PHRASE 3 XTITLEdune PHRASE 3 XTITLE$) OR '
                         '(XTITLE^ PHRASE 3 XTITLEjaws PHRASE 3 XTITLE$)))))')

    def test_build_query_in_filter_multiple_words(self):
        self.sq.add_filter(SQ(content='why'))
        self.sq.add_filter(SQ(title__in=["A Famous Paper", "An Infamous Article"]))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query(('
                         '(Zwhi OR why) AND ((XTITLE^ PHRASE 5 XTITLEa PHRASE 5 '
                         'XTITLEfamous PHRASE 5 XTITLEpaper PHRASE 5 XTITLE$) OR '
                         '(XTITLE^ PHRASE 5 XTITLEan PHRASE 5 XTITLEinfamous PHRASE 5 '
                         'XTITLEarticle PHRASE 5 XTITLE$))))')

    def test_build_query_in_filter_multiple_words_with_punctuation(self):
        self.sq.add_filter(SQ(title__in=["A Famous Paper", "An Infamous Article", "My Store Inc."]))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query(('
                         '(XTITLE^ PHRASE 5 XTITLEa PHRASE 5 XTITLEfamous PHRASE 5'
                         ' XTITLEpaper PHRASE 5 XTITLE$) OR '
                         '(XTITLE^ PHRASE 5 XTITLEan PHRASE 5 XTITLEinfamous PHRASE 5'
                         ' XTITLEarticle PHRASE 5 XTITLE$) OR '
                         '(XTITLE^ PHRASE 5 XTITLEmy PHRASE 5 XTITLEstore PHRASE 5'
                         ' XTITLEinc. PHRASE 5 XTITLE$)))')

    def test_build_query_not_in_filter_multiple_words(self):
        self.sq.add_filter(SQ(content='why'))
        self.sq.add_filter(~SQ(title__in=["A Famous Paper", "An Infamous Article"]))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query(('
                         '(Zwhi OR why) AND (<alldocuments> AND_NOT '
                         '((XTITLE^ PHRASE 5 XTITLEa PHRASE 5 XTITLEfamous PHRASE 5 '
                         'XTITLEpaper PHRASE 5 XTITLE$) OR (XTITLE^ PHRASE 5 '
                         'XTITLEan PHRASE 5 XTITLEinfamous PHRASE 5 '
                         'XTITLEarticle PHRASE 5 XTITLE$)))))')

    def test_build_query_in_filter_datetime(self):
        self.sq.add_filter(SQ(content='why'))
        self.sq.add_filter(SQ(pub_date__in=[datetime.datetime(2009, 7, 6, 1, 56, 21)]))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query(((Zwhi OR why) AND '
                         '(XPUB_DATE2009-07-06 AND_MAYBE XPUB_DATE01:56:21)))')

    def test_clean(self):
        self.assertEqual(self.sq.clean('hello world'), 'hello world')
        self.assertEqual(self.sq.clean('hello AND world'), 'hello AND world')
        self.assertEqual(self.sq.clean('hello AND OR NOT TO + - && || ! ( ) { } [ ] ^ " ~ * ? : \ world'),
                         'hello AND OR NOT TO + - && || ! ( ) { } [ ] ^ " ~ * ? : \ world')
        self.assertEqual(self.sq.clean('so please NOTe i am in a bAND and bORed'),
                         'so please NOTe i am in a bAND and bORed')

    def test_build_query_with_models(self):
        self.sq.add_filter(SQ(content='hello'))
        self.sq.add_model(MockModel)
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query(((Zhello OR hello) AND '
                         '0 * CONTENTTYPEcore.mockmodel))')

        self.sq.add_model(AnotherMockModel)

        self.assertTrue(str(self.sq.build_query()) in (
            'Xapian::Query(((Zhello OR hello) AND '
            '(0 * CONTENTTYPEcore.anothermockmodel OR '
            '0 * CONTENTTYPEcore.mockmodel)))',
            'Xapian::Query(((Zhello OR hello) AND '
            '(0 * CONTENTTYPEcore.mockmodel OR '
            '0 * CONTENTTYPEcore.anothermockmodel)))'))

    def test_build_query_with_punctuation(self):
        self.sq.add_filter(SQ(content='http://www.example.com'))
        self.assertEqual(str(self.sq.build_query()), 'Xapian::Query((Zhttp://www.example.com OR '
                                                     'http://www.example.com))')

    def test_in_filter_values_list(self):
        self.sq.add_filter(SQ(content='why'))
        self.sq.add_filter(SQ(title__in=MockModel.objects.values_list('id', flat=True)))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query('
                         '((Zwhi OR why) AND ('
                         '(XTITLE^ PHRASE 3 XTITLE1 PHRASE 3 XTITLE$) OR '
                         '(XTITLE^ PHRASE 3 XTITLE2 PHRASE 3 XTITLE$) OR '
                         '(XTITLE^ PHRASE 3 XTITLE3 PHRASE 3 XTITLE$))))')


class MockSearchIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr='author', faceted=True)
    pub_date = indexes.DateTimeField(model_attr='pub_date')
    title = indexes.CharField()

    def get_model(self):
        return MockModel


class SearchQueryTestCase(HaystackBackendTestCase, TestCase):
    """
    Tests expected behavior of
    SearchQuery.
    """
    fixtures = ['initial_data.json']

    def get_index(self):
        return MockSearchIndex()

    def setUp(self):
        super(SearchQueryTestCase, self).setUp()

        self.backend.update(self.index, MockModel.objects.all())

        self.sq = connections['default'].get_query()

    def test_get_spelling(self):
        self.sq.add_filter(SQ(content='indxd'))
        self.assertEqual(self.sq.get_spelling_suggestion(), 'indexed')
        self.assertEqual(self.sq.get_spelling_suggestion('indxd'), 'indexed')

    def test_startswith(self):
        self.sq.add_filter(SQ(name__startswith='da'))
        self.assertEqual([result.pk for result in self.sq.get_results()], [1, 2, 3])

    def test_build_query_gt(self):
        self.sq.add_filter(SQ(name__gt='m'))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query((<alldocuments> AND_NOT VALUE_RANGE 3 a m))')

    def test_build_query_gte(self):
        self.sq.add_filter(SQ(name__gte='m'))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query(VALUE_RANGE 3 m zzzzzzzzzzzzzzzzzzzzzzzzzzzz'
                         'zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz'
                         'zzzzzzzzzzzzzz)')

    def test_build_query_lt(self):
        self.sq.add_filter(SQ(name__lt='m'))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query((<alldocuments> AND_NOT '
                         'VALUE_RANGE 3 m zzzzzzzzzzzzzzzzzzzzzz'
                         'zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz'
                         'zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz))')

    def test_build_query_lte(self):
        self.sq.add_filter(SQ(name__lte='m'))
        self.assertEqual(str(self.sq.build_query()), 'Xapian::Query(VALUE_RANGE 3 a m)')

    def test_build_query_multiple_filter_types(self):
        self.sq.add_filter(SQ(content='why'))
        self.sq.add_filter(SQ(pub_date__lte=datetime.datetime(2009, 2, 10, 1, 59, 0)))
        self.sq.add_filter(SQ(name__gt='david'))
        self.sq.add_filter(SQ(title__gte='B'))
        self.sq.add_filter(SQ(django_id__in=[1, 2, 3]))
        self.assertEqual(str(self.sq.build_query()),
                         'Xapian::Query(((Zwhi OR why) AND '
                         'VALUE_RANGE 5 00010101000000 20090210015900 AND '
                         '(<alldocuments> AND_NOT VALUE_RANGE 3 a david) AND '
                         'VALUE_RANGE 7 b zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz'
                         'zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz AND '
                         '(QQ000000000001 OR QQ000000000002 OR QQ000000000003)))')

    def test_log_query(self):
        reset_search_queries()
        self.assertEqual(len(connections['default'].queries), 0)

        # Stow.
        old_debug = settings.DEBUG
        settings.DEBUG = False

        len(self.sq.get_results())
        self.assertEqual(len(connections['default'].queries), 0)

        settings.DEBUG = True
        # Redefine it to clear out the cached results.
        self.sq = connections['default'].get_query()
        self.sq.add_filter(SQ(name='bar'))
        len(self.sq.get_results())
        self.assertEqual(len(connections['default'].queries), 1)
        self.assertEqual(str(connections['default'].queries[0]['query_string']),
                         'Xapian::Query((ZXNAMEbar OR XNAMEbar))')

        # And again, for good measure.
        self.sq = connections['default'].get_query()
        self.sq.add_filter(SQ(name='bar'))
        self.sq.add_filter(SQ(text='moof'))
        len(self.sq.get_results())
        self.assertEqual(len(connections['default'].queries), 2)
        self.assertEqual(str(connections['default'].queries[0]['query_string']),
                         'Xapian::Query(('
                         'ZXNAMEbar OR '
                         'XNAMEbar))')
        self.assertEqual(str(connections['default'].queries[1]['query_string']),
                         'Xapian::Query(('
                         '(ZXNAMEbar OR XNAMEbar) AND '
                         '(ZXTEXTmoof OR XTEXTmoof)))')

        # Restore.
        settings.DEBUG = old_debug


class LiveSearchQuerySetTestCase(HaystackBackendTestCase, TestCase):
    """
    SearchQuerySet specific tests
    """
    fixtures = ['initial_data.json']

    def get_index(self):
        return MockSearchIndex()

    def setUp(self):
        super(LiveSearchQuerySetTestCase, self).setUp()

        self.backend.update(self.index, MockModel.objects.all())
        self.sq = connections['default'].get_query()
        self.sqs = SearchQuerySet()

    def test_result_class(self):
        # Assert that we're defaulting to ``SearchResult``.
        sqs = self.sqs.all()
        self.assertTrue(isinstance(sqs[0], SearchResult))

        # Custom class.
        sqs = self.sqs.result_class(MockSearchResult).all()
        self.assertTrue(isinstance(sqs[0], MockSearchResult))

        # Reset to default.
        sqs = self.sqs.result_class(None).all()
        self.assertTrue(isinstance(sqs[0], SearchResult))

    def test_facet(self):
        self.assertEqual(len(self.sqs.facet('name').facet_counts()['fields']['name']), 3)


class BoostMockSearchIndex(indexes.SearchIndex):
    text = indexes.CharField(
        document=True, use_template=True,
        template_name='search/indexes/core/mockmodel_template.txt'
    )
    author = indexes.CharField(model_attr='author', weight=2.0)
    editor = indexes.CharField(model_attr='editor')
    pub_date = indexes.DateField(model_attr='pub_date')

    def get_model(self):
        return AFourthMockModel


class BoostFieldTestCase(HaystackBackendTestCase, TestCase):
    """
    Tests boosted fields.
    """

    def get_index(self):
        return BoostMockSearchIndex()

    def setUp(self):
        super(BoostFieldTestCase, self).setUp()

        self.sample_objs = []
        for i in range(1, 5):
            mock = AFourthMockModel()
            mock.id = i
            if i % 2:
                mock.author = 'daniel'
                mock.editor = 'david'
            else:
                mock.author = 'david'
                mock.editor = 'daniel'
            mock.pub_date = datetime.date(2009, 2, 25) - datetime.timedelta(days=i)
            self.sample_objs.append(mock)

        self.backend.update(self.index, self.sample_objs)

    def test_boost(self):
        sqs = SearchQuerySet()

        self.assertEqual(len(sqs.all()), 4)

        results = sqs.filter(SQ(author='daniel') | SQ(editor='daniel'))

        self.assertEqual([result.id for result in results], [
            'core.afourthmockmodel.1',
            'core.afourthmockmodel.3',
            'core.afourthmockmodel.2',
            'core.afourthmockmodel.4'
        ])

########NEW FILE########
__FILENAME__ = xapian_backend
from __future__ import unicode_literals

import time
import datetime
import pickle
import os
import re
import shutil
import sys

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import force_text

from haystack import connections
from haystack.backends import BaseEngine, BaseSearchBackend, BaseSearchQuery, SearchNode, log_query
from haystack.constants import ID, DJANGO_ID, DJANGO_CT
from haystack.exceptions import HaystackError, MissingDependency
from haystack.inputs import AutoQuery
from haystack.models import SearchResult
from haystack.utils import get_identifier, get_model_ct

try:
    import xapian
except ImportError:
    raise MissingDependency("The 'xapian' backend requires the installation of 'Xapian'. "
                            "Please refer to the documentation.")


# this maps the different reserved fields to prefixes used to
# create the database:
# id str: unique document id.
# django_id int: id of the django model instance.
# django_ct str: of the content type of the django model.
# field str: name of the field of the index.
TERM_PREFIXES = {'id': 'Q',
                 'django_id': 'QQ',
                 'django_ct': 'CONTENTTYPE',
                 'field': 'X'
                 }

MEMORY_DB_NAME = ':memory:'

DEFAULT_XAPIAN_FLAGS = (
    xapian.QueryParser.FLAG_PHRASE |
    xapian.QueryParser.FLAG_BOOLEAN |
    xapian.QueryParser.FLAG_LOVEHATE |
    xapian.QueryParser.FLAG_WILDCARD |
    xapian.QueryParser.FLAG_PURE_NOT
)

# number of documents checked by default when building facets
# this must be improved to be relative to the total number of docs.
DEFAULT_CHECK_AT_LEAST = 1000

# field types accepted to be serialized as values in Xapian
FIELD_TYPES = {'text', 'integer', 'date', 'datetime', 'float', 'boolean'}

# defines the format used to store types in Xapian
# this format ensures datetimes are sorted correctly
DATETIME_FORMAT = '%Y%m%d%H%M%S'
INTEGER_FORMAT = '%012d'

# defines the distance given between
# texts with positional information
TERMPOS_DISTANCE = 100

class InvalidIndexError(HaystackError):
    """Raised when an index can not be opened."""
    pass


class XHValueRangeProcessor(xapian.ValueRangeProcessor):
    """
    A Processor to construct ranges of values
    """
    def __init__(self, backend):
        self.backend = backend
        xapian.ValueRangeProcessor.__init__(self)

    def __call__(self, begin, end):
        """
        Construct a tuple for value range processing.
        `begin` -- a string in the format '<field_name>:[low_range]'
        If 'low_range' is omitted, assume the smallest possible value.
        `end` -- a string in the the format '[high_range|*]'. If '*', assume
        the highest possible value.
        Return a tuple of three strings: (column, low, high)
        """
        colon = begin.find(':')
        field_name = begin[:colon]
        begin = begin[colon + 1:len(begin)]
        for field_dict in self.backend.schema:
            if field_dict['field_name'] == field_name:
                field_type = field_dict['type']

                if not begin:
                    if field_type == 'text':
                        begin = 'a'  # TODO: A better way of getting a min text value?
                    elif field_type == 'integer':
                        begin = -sys.maxsize - 1
                    elif field_type == 'float':
                        begin = float('-inf')
                    elif field_type == 'date' or field_type == 'datetime':
                        begin = '00010101000000'
                elif end == '*':
                    if field_type == 'text':
                        end = 'z' * 100  # TODO: A better way of getting a max text value?
                    elif field_type == 'integer':
                        end = sys.maxsize
                    elif field_type == 'float':
                        end = float('inf')
                    elif field_type == 'date' or field_type == 'datetime':
                        end = '99990101000000'

                if field_type == 'float':
                    begin = _term_to_xapian_value(float(begin), field_type)
                    end = _term_to_xapian_value(float(end), field_type)
                elif field_type == 'integer':
                    begin = _term_to_xapian_value(int(begin), field_type)
                    end = _term_to_xapian_value(int(end), field_type)
                return field_dict['column'], str(begin), str(end)


class XHExpandDecider(xapian.ExpandDecider):
    def __call__(self, term):
        """
        Return True if the term should be used for expanding the search
        query, False otherwise.

        Ignore terms related with the content type of objects.
        """
        if term.startswith(TERM_PREFIXES['django_ct']):
            return False
        return True


class XapianSearchBackend(BaseSearchBackend):
    """
    `SearchBackend` defines the Xapian search backend for use with the Haystack
    API for Django search.

    It uses the Xapian Python bindings to interface with Xapian, and as
    such is subject to this bug: <http://trac.xapian.org/ticket/364> when
    Django is running with mod_python or mod_wsgi under Apache.

    Until this issue has been fixed by Xapian, it is neccessary to set
    `WSGIApplicationGroup to %{GLOBAL}` when using mod_wsgi, or
    `PythonInterpreter main_interpreter` when using mod_python.

    In order to use this backend, `PATH` must be included in the
    `connection_options`.  This should point to a location where you would your
    indexes to reside.
    """
    inmemory_db = None

    def __init__(self, connection_alias, **connection_options):
        """
        Instantiates an instance of `SearchBackend`.

        Optional arguments:
            `connection_alias` -- The name of the connection
            `language` -- The stemming language (default = 'english')
            `**connection_options` -- The various options needed to setup
              the backend.

        Also sets the stemming language to be used to `language`.
        """
        super(XapianSearchBackend, self).__init__(connection_alias, **connection_options)

        if not 'PATH' in connection_options:
            raise ImproperlyConfigured("You must specify a 'PATH' in your settings for connection '%s'."
                                       % connection_alias)

        self.path = connection_options.get('PATH')

        if self.path != MEMORY_DB_NAME and not os.path.exists(self.path):
            os.makedirs(self.path)

        self.flags = connection_options.get('FLAGS', DEFAULT_XAPIAN_FLAGS)
        self.language = getattr(settings, 'HAYSTACK_XAPIAN_LANGUAGE', 'english')

        # these 4 attributes are caches populated in `build_schema`
        # they are checked in `_update_cache`
        # use property to retrieve them
        self._fields = {}
        self._schema = []
        self._content_field_name = None
        self._columns = {}

    def _update_cache(self):
        """
        To avoid build_schema every time, we cache
        some values: they only change when a SearchIndex
        changes, which typically restarts the Python.
        """
        fields = connections[self.connection_alias].get_unified_index().all_searchfields()
        if self._fields != fields:
            self._fields = fields
            self._content_field_name, self._schema = self.build_schema(self._fields)

    @property
    def schema(self):
        self._update_cache()
        return self._schema

    @property
    def content_field_name(self):
        self._update_cache()
        return self._content_field_name

    @property
    def column(self):
        """
        Returns the column in the database of a given field name.
        """
        self._update_cache()
        return self._columns

    def update(self, index, iterable):
        """
        Updates the `index` with any objects in `iterable` by adding/updating
        the database as needed.

        Required arguments:
            `index` -- The `SearchIndex` to process
            `iterable` -- An iterable of model instances to index

        For each object in `iterable`, a document is created containing all
        of the terms extracted from `index.full_prepare(obj)` with field prefixes,
        and 'as-is' as needed.  Also, if the field type is 'text' it will be
        stemmed and stored with the 'Z' prefix as well.

        eg. `content:Testing` ==> `testing, Ztest, ZXCONTENTtest, XCONTENTtest`

        Each document also contains an extra term in the format:

        `XCONTENTTYPE<app_name>.<model_name>`

        As well as a unique identifier in the the format:

        `Q<app_name>.<model_name>.<pk>`

        eg.: foo.bar (pk=1) ==> `Qfoo.bar.1`, `XCONTENTTYPEfoo.bar`

        This is useful for querying for a specific document corresponding to
        a model instance.

        The document also contains a pickled version of the object itself and
        the document ID in the document data field.

        Finally, we also store field values to be used for sorting data.  We
        store these in the document value slots (position zero is reserver
        for the document ID).  All values are stored as unicode strings with
        conversion of float, int, double, values being done by Xapian itself
        through the use of the :method:xapian.sortable_serialise method.
        """
        database = self._database(writable=True)

        try:
            term_generator = xapian.TermGenerator()
            term_generator.set_database(database)
            term_generator.set_stemmer(xapian.Stem(self.language))
            if self.include_spelling is True:
                term_generator.set_flags(xapian.TermGenerator.FLAG_SPELLING)

            def _add_text(termpos, text, weight, prefix=''):
                """
                indexes text appending 2 extra terms
                to identify beginning and ending of the text.
                """
                term_generator.set_termpos(termpos)

                start_term = '%s^' % prefix
                end_term = '%s$' % prefix
                # add begin
                document.add_posting(start_term, termpos, weight)
                # add text
                term_generator.index_text(text, weight, prefix)
                termpos = term_generator.get_termpos()
                # add ending
                termpos += 1
                document.add_posting(end_term, termpos, weight)

                # increase termpos
                term_generator.set_termpos(termpos)
                term_generator.increase_termpos(TERMPOS_DISTANCE)

                return term_generator.get_termpos()

            def _add_literal_text(termpos, text, weight, prefix=''):
                """
                Adds sentence to the document with positional information
                but without processing.

                The sentence is bounded by "^" "$" to allow exact matches.
                """
                text = '^ %s $' % text
                for word in text.split():
                    term = '%s%s' % (prefix, word)
                    document.add_posting(term, termpos, weight)
                    termpos += 1
                termpos += TERMPOS_DISTANCE
                return termpos

            def add_text(termpos, prefix, text, weight):
                """
                Adds text to the document with positional information
                and processing (e.g. stemming).
                """
                termpos = _add_text(termpos, text, weight, prefix=prefix)
                termpos = _add_text(termpos, text, weight, prefix='')
                termpos = _add_literal_text(termpos, text, weight, prefix=prefix)
                termpos = _add_literal_text(termpos, text, weight, prefix='')
                return termpos

            for obj in iterable:
                document = xapian.Document()
                term_generator.set_document(document)

                def add_non_text_to_document(prefix, term, weight):
                    """
                    Adds term to the document without positional information
                    and without processing.

                    If the term is alone, also adds it as "^<term>$"
                    to allow exact matches on single terms.
                    """
                    document.add_term(term, weight)
                    document.add_term(prefix + term, weight)

                def add_datetime_to_document(termpos, prefix, term, weight):
                    """
                    Adds a datetime to document with positional order
                    to allow exact matches on it.
                    """
                    date, time = term.split()
                    document.add_posting(date, termpos, weight)
                    termpos += 1
                    document.add_posting(time, termpos, weight)
                    termpos += 1
                    document.add_posting(prefix + date, termpos, weight)
                    termpos += 1
                    document.add_posting(prefix + time, termpos, weight)
                    termpos += TERMPOS_DISTANCE + 1
                    return termpos

                data = index.full_prepare(obj)
                weights = index.get_field_weights()

                termpos = term_generator.get_termpos()  # identifies the current position in the document.
                for field in self.schema:
                    if field['field_name'] not in list(data.keys()):
                        # not supported fields are ignored.
                        continue

                    if field['field_name'] in weights:
                        weight = int(weights[field['field_name']])
                    else:
                        weight = 1

                    value = data[field['field_name']]

                    if field['field_name'] in ('id', 'django_id', 'django_ct'):
                        # Private fields are indexed in a different way:
                        # `django_id` is an int and `django_ct` is text;
                        # besides, they are indexed by their (unstemmed) value.
                        if field['field_name'] == 'django_id':
                            value = int(value)
                        value = _term_to_xapian_value(value, field['type'])

                        document.add_term(TERM_PREFIXES[field['field_name']] + value, weight)
                        document.add_value(field['column'], value)
                        continue
                    else:
                        prefix = TERM_PREFIXES['field'] + field['field_name'].upper()

                        # if not multi_valued, we add as a document value
                        # for sorting and facets
                        if field['multi_valued'] == 'false':
                            document.add_value(field['column'], _term_to_xapian_value(value, field['type']))
                        else:
                            for t in value:
                                # add the exact match of each value
                                term = _to_xapian_term(t)
                                termpos = add_text(termpos, prefix, term, weight)
                            continue

                        term = _to_xapian_term(value)
                        if term == '':
                            continue
                        # from here on the term is a string;
                        # we now decide how it is indexed

                        if field['type'] == 'text':
                            # text is indexed with positional information
                            termpos = add_text(termpos, prefix, term, weight)
                        elif field['type'] == 'datetime':
                            termpos = add_datetime_to_document(termpos, prefix, term, weight)
                        else:
                            # all other terms are added without positional information
                            add_non_text_to_document(prefix, term, weight)

                # store data without indexing it
                document.set_data(pickle.dumps(
                    (obj._meta.app_label, obj._meta.module_name, obj.pk, data),
                    pickle.HIGHEST_PROTOCOL
                ))

                # add the id of the document
                document_id = TERM_PREFIXES['id'] + get_identifier(obj)
                document.add_term(document_id)

                # finally, replace or add the document to the database
                database.replace_document(document_id, document)

        except UnicodeDecodeError:
            sys.stderr.write('Chunk failed.\n')
            pass

        finally:
            database.close()

    def remove(self, obj):
        """
        Remove indexes for `obj` from the database.

        We delete all instances of `Q<app_name>.<model_name>.<pk>` which
        should be unique to this object.
        """
        database = self._database(writable=True)
        database.delete_document(TERM_PREFIXES['id'] + get_identifier(obj))
        database.close()

    def clear(self, models=(), commit=True):
        """
        Clear all instances of `models` from the database or all models, if
        not specified.

        Optional Arguments:
            `models` -- Models to clear from the database (default = [])

        If `models` is empty, an empty query is executed which matches all
        documents in the database.  Afterwards, each match is deleted.

        Otherwise, for each model, a `delete_document` call is issued with
        the term `XCONTENTTYPE<app_name>.<model_name>`.  This will delete
        all documents with the specified model type.
        """
        if not models:
            # Because there does not appear to be a "clear all" method,
            # it's much quicker to remove the contents of the `self.path`
            # folder than it is to remove each document one at a time.
            if os.path.exists(self.path):
                shutil.rmtree(self.path)
        else:
            database = self._database(writable=True)
            for model in models:
                database.delete_document(TERM_PREFIXES['django_ct'] + get_model_ct(model))
            database.close()

    def document_count(self):
        try:
            return self._database().get_doccount()
        except InvalidIndexError:
            return 0

    def _build_models_query(self, query):
        """
        Builds a query from `query` that filters to documents only from registered models.
        """
        registered_models_ct = self.build_models_list()
        if registered_models_ct:
            restrictions = [xapian.Query('%s%s' % (TERM_PREFIXES['django_ct'], model_ct))
                            for model_ct in registered_models_ct]
            limit_query = xapian.Query(xapian.Query.OP_OR, restrictions)

            query = xapian.Query(xapian.Query.OP_AND, query, limit_query)

        return query

    def _check_field_names(self, field_names):
        """
        Raises InvalidIndexError if any of a field_name in field_names is
        not indexed.
        """
        if field_names:
            for field_name in field_names:
                try:
                    self.column[field_name]
                except KeyError:
                    raise InvalidIndexError('Trying to use non indexed field "%s"' % field_name)

    @log_query
    def search(self, query, sort_by=None, start_offset=0, end_offset=None,
               fields='', highlight=False, facets=None, date_facets=None,
               query_facets=None, narrow_queries=None, spelling_query=None,
               limit_to_registered_models=True, result_class=None, **kwargs):
        """
        Executes the Xapian::query as defined in `query`.

        Required arguments:
            `query` -- Search query to execute

        Optional arguments:
            `sort_by` -- Sort results by specified field (default = None)
            `start_offset` -- Slice results from `start_offset` (default = 0)
            `end_offset` -- Slice results at `end_offset` (default = None), if None, then all documents
            `fields` -- Filter results on `fields` (default = '')
            `highlight` -- Highlight terms in results (default = False)
            `facets` -- Facet results on fields (default = None)
            `date_facets` -- Facet results on date ranges (default = None)
            `query_facets` -- Facet results on queries (default = None)
            `narrow_queries` -- Narrow queries (default = None)
            `spelling_query` -- An optional query to execute spelling suggestion on
            `limit_to_registered_models` -- Limit returned results to models registered in
            the current `SearchSite` (default = True)

        Returns:
            A dictionary with the following keys:
                `results` -- A list of `SearchResult`
                `hits` -- The total available results
                `facets` - A dictionary of facets with the following keys:
                    `fields` -- A list of field facets
                    `dates` -- A list of date facets
                    `queries` -- A list of query facets
            If faceting was not used, the `facets` key will not be present

        If `query` is None, returns no results.

        If `INCLUDE_SPELLING` was enabled in the connection options, the
        extra flag `FLAG_SPELLING_CORRECTION` will be passed to the query parser
        and any suggestions for spell correction will be returned as well as
        the results.
        """
        if xapian.Query.empty(query):
            return {
                'results': [],
                'hits': 0,
            }

        self._check_field_names(facets)
        self._check_field_names(date_facets)
        self._check_field_names(query_facets)

        database = self._database()

        if result_class is None:
            result_class = SearchResult

        if self.include_spelling is True:
            spelling_suggestion = self._do_spelling_suggestion(database, query, spelling_query)
        else:
            spelling_suggestion = ''

        if narrow_queries is not None:
            query = xapian.Query(
                xapian.Query.OP_AND, query, xapian.Query(
                    xapian.Query.OP_AND, [self.parse_query(narrow_query) for narrow_query in narrow_queries]
                )
            )

        if limit_to_registered_models:
            query = self._build_models_query(query)

        enquire = xapian.Enquire(database)
        if hasattr(settings, 'HAYSTACK_XAPIAN_WEIGHTING_SCHEME'):
            enquire.set_weighting_scheme(xapian.BM25Weight(*settings.HAYSTACK_XAPIAN_WEIGHTING_SCHEME))
        enquire.set_query(query)

        if sort_by:
            sorter = xapian.MultiValueSorter()

            for sort_field in sort_by:
                if sort_field.startswith('-'):
                    reverse = True
                    sort_field = sort_field[1:]  # Strip the '-'
                else:
                    reverse = False  # Reverse is inverted in Xapian -- http://trac.xapian.org/ticket/311
                sorter.add(self.column[sort_field], reverse)

            enquire.set_sort_by_key_then_relevance(sorter, True)

        results = []
        facets_dict = {
            'fields': {},
            'dates': {},
            'queries': {},
        }

        if not end_offset:
            end_offset = database.get_doccount() - start_offset

        ## prepare spies in case of facets
        if facets:
            facets_spies = self._prepare_facet_field_spies(facets)
            for spy in facets_spies:
                enquire.add_matchspy(spy)

        matches = self._get_enquire_mset(database, enquire, start_offset, end_offset)

        for match in matches:
            app_label, module_name, pk, model_data = pickle.loads(self._get_document_data(database, match.document))
            if highlight:
                model_data['highlighted'] = {
                    self.content_field_name: self._do_highlight(
                        model_data.get(self.content_field_name), query
                    )
                }
            results.append(
                result_class(app_label, module_name, pk, match.percent, **model_data)
            )

        if facets:
            # pick single valued facets from spies
            single_facets_dict = self._process_facet_field_spies(facets_spies)

            # pick multivalued valued facets from results
            multi_facets_dict = self._do_multivalued_field_facets(results, facets)

            # merge both results (http://stackoverflow.com/a/38990/931303)
            facets_dict['fields'] = dict(list(single_facets_dict.items()) + list(multi_facets_dict.items()))

        if date_facets:
            facets_dict['dates'] = self._do_date_facets(results, date_facets)

        if query_facets:
            facets_dict['queries'] = self._do_query_facets(results, query_facets)

        return {
            'results': results,
            'hits': self._get_hit_count(database, enquire),
            'facets': facets_dict,
            'spelling_suggestion': spelling_suggestion,
        }

    def more_like_this(self, model_instance, additional_query=None,
                       start_offset=0, end_offset=None,
                       limit_to_registered_models=True, result_class=None, **kwargs):
        """
        Given a model instance, returns a result set of similar documents.

        Required arguments:
            `model_instance` -- The model instance to use as a basis for
                                retrieving similar documents.

        Optional arguments:
            `additional_query` -- An additional query to narrow results
            `start_offset` -- The starting offset (default=0)
            `end_offset` -- The ending offset (default=None), if None, then all documents
            `limit_to_registered_models` -- Limit returned results to models registered in the search (default = True)

        Returns:
            A dictionary with the following keys:
                `results` -- A list of `SearchResult`
                `hits` -- The total available results

        Opens a database connection, then builds a simple query using the
        `model_instance` to build the unique identifier.

        For each document retrieved(should always be one), adds an entry into
        an RSet (relevance set) with the document id, then, uses the RSet
        to query for an ESet (A set of terms that can be used to suggest
        expansions to the original query), omitting any document that was in
        the original query.

        Finally, processes the resulting matches and returns.
        """
        database = self._database()

        if result_class is None:
            result_class = SearchResult

        query = xapian.Query(TERM_PREFIXES['id'] + get_identifier(model_instance))

        enquire = xapian.Enquire(database)
        enquire.set_query(query)

        rset = xapian.RSet()

        if not end_offset:
            end_offset = database.get_doccount()

        match = None
        for match in self._get_enquire_mset(database, enquire, 0, end_offset):
            rset.add_document(match.docid)

        if match is None:
            if not self.silently_fail:
                raise InvalidIndexError('Instance %s with id "%d" not indexed' %
                                        (get_identifier(model_instance), model_instance.id))
            else:
                return {'results': [],
                        'hits': 0}

        query = xapian.Query(
            xapian.Query.OP_ELITE_SET,
            [expand.term for expand in enquire.get_eset(match.document.termlist_count(), rset, XHExpandDecider())],
            match.document.termlist_count()
        )
        query = xapian.Query(
            xapian.Query.OP_AND_NOT, [query, TERM_PREFIXES['id'] + get_identifier(model_instance)]
        )

        if limit_to_registered_models:
            query = self._build_models_query(query)

        if additional_query:
            query = xapian.Query(
                xapian.Query.OP_AND, query, additional_query
            )

        enquire.set_query(query)

        results = []
        matches = self._get_enquire_mset(database, enquire, start_offset, end_offset)

        for match in matches:
            app_label, module_name, pk, model_data = pickle.loads(self._get_document_data(database, match.document))
            results.append(
                result_class(app_label, module_name, pk, match.percent, **model_data)
            )

        return {
            'results': results,
            'hits': self._get_hit_count(database, enquire),
            'facets': {
                'fields': {},
                'dates': {},
                'queries': {},
            },
            'spelling_suggestion': None,
        }

    def parse_query(self, query_string):
        """
        Given a `query_string`, will attempt to return a xapian.Query

        Required arguments:
            ``query_string`` -- A query string to parse

        Returns a xapian.Query
        """
        if query_string == '*':
            return xapian.Query('')  # Match everything
        elif query_string == '':
            return xapian.Query()  # Match nothing

        qp = xapian.QueryParser()
        qp.set_database(self._database())
        qp.set_stemmer(xapian.Stem(self.language))
        qp.set_stemming_strategy(xapian.QueryParser.STEM_SOME)
        qp.add_boolean_prefix('django_ct', TERM_PREFIXES['django_ct'])

        for field_dict in self.schema:
            # since 'django_ct' has a boolean_prefix,
            # we ignore it here.
            if field_dict['field_name'] == 'django_ct':
                continue

            qp.add_prefix(
                field_dict['field_name'],
                TERM_PREFIXES['field'] + field_dict['field_name'].upper()
            )

        vrp = XHValueRangeProcessor(self)
        qp.add_valuerangeprocessor(vrp)

        return qp.parse_query(query_string, self.flags)

    def build_schema(self, fields):
        """
        Build the schema from fields.

        :param fields: A list of fields in the index
        :returns: list of dictionaries

        Each dictionary has the keys
         field_name: The name of the field index
         type: what type of value it is
         'multi_valued': if it allows more than one value
         'column': a number identifying it
         'type': the type of the field
         'multi_valued': 'false', 'column': 0}
        """
        content_field_name = ''
        schema_fields = [
            {'field_name': ID,
             'type': 'text',
             'multi_valued': 'false',
             'column': 0},
            {'field_name': DJANGO_ID,
             'type': 'integer',
             'multi_valued': 'false',
             'column': 1},
            {'field_name': DJANGO_CT,
             'type': 'text',
             'multi_valued': 'false',
             'column': 2},
        ]
        self._columns[ID] = 0
        self._columns[DJANGO_ID] = 1
        self._columns[DJANGO_CT] = 2

        column = len(schema_fields)

        for field_name, field_class in sorted(list(fields.items()), key=lambda n: n[0]):
            if field_class.document is True:
                content_field_name = field_class.index_fieldname

            if field_class.indexed is True:
                field_data = {
                    'field_name': field_class.index_fieldname,
                    'type': 'text',
                    'multi_valued': 'false',
                    'column': column,
                }

                if field_class.field_type == 'date':
                    field_data['type'] = 'date'
                elif field_class.field_type == 'datetime':
                    field_data['type'] = 'datetime'
                elif field_class.field_type == 'integer':
                    field_data['type'] = 'integer'
                elif field_class.field_type == 'float':
                    field_data['type'] = 'float'
                elif field_class.field_type == 'boolean':
                    field_data['type'] = 'boolean'

                if field_class.is_multivalued:
                    field_data['multi_valued'] = 'true'

                schema_fields.append(field_data)
                self._columns[field_data['field_name']] = column
                column += 1

        return content_field_name, schema_fields

    @staticmethod
    def _do_highlight(content, query, tag='em'):
        """
        Highlight `query` terms in `content` with html `tag`.

        This method assumes that the input text (`content`) does not contain
        any special formatting.  That is, it does not contain any html tags
        or similar markup that could be screwed up by the highlighting.

        Required arguments:
            `content` -- Content to search for instances of `text`
            `text` -- The text to be highlighted
        """
        for term in query:
            for match in re.findall('[^A-Z]+', term):  # Ignore field identifiers
                match_re = re.compile(match, re.I)
                content = match_re.sub('<%s>%s</%s>' % (tag, term, tag), content)

        return content

    def _prepare_facet_field_spies(self, facets):
        """
        Returns a list of spies based on the facets
        used to count frequencies.
        """
        spies = []
        for facet in facets:
            slot = self.column[facet]
            spy = xapian.ValueCountMatchSpy(slot)
            # add attribute "slot" to know which column this spy is targeting.
            spy.slot = slot
            spies.append(spy)
        return spies

    def _process_facet_field_spies(self, spies):
        """
        Returns a dict of facet names with lists of
        tuples of the form (term, term_frequency)
        from a list of spies that observed the enquire.
        """
        facet_dict = {}
        for spy in spies:
            field = self.schema[spy.slot]
            field_name, field_type = field['field_name'], field['type']

            facet_dict[field_name] = []
            for facet in list(spy.values()):
                facet_dict[field_name].append((_from_xapian_value(facet.term, field_type),
                                               facet.termfreq))
        return facet_dict

    def _do_multivalued_field_facets(self, results, field_facets):
        """
        Implements a multivalued field facet on the results.

        This is implemented using brute force - O(N^2) -
        because Xapian does not have it implemented yet
        (see http://trac.xapian.org/ticket/199)
        """
        facet_dict = {}

        for field in field_facets:
            facet_list = {}
            if not self._multi_value_field(field):
                continue

            for result in results:
                field_value = getattr(result, field)
                for item in field_value:  # Facet each item in a MultiValueField
                    facet_list[item] = facet_list.get(item, 0) + 1

            facet_dict[field] = list(facet_list.items())
        return facet_dict

    @staticmethod
    def _do_date_facets(results, date_facets):
        """
        Private method that facets a document by date ranges

        Required arguments:
            `results` -- A list SearchResults to facet
            `date_facets` -- A dictionary containing facet parameters:
                {'field': {'start_date': ..., 'end_date': ...: 'gap_by': '...', 'gap_amount': n}}
                nb., gap must be one of the following:
                    year|month|day|hour|minute|second

        For each date facet field in `date_facets`, generates a list
        of date ranges (from `start_date` to `end_date` by `gap_by`) then
        iterates through `results` and tallies the count for each date_facet.

        Returns a dictionary of date facets (fields) containing a list with
        entries for each range and a count of documents matching the range.

        eg. {
            'pub_date': [
                ('2009-01-01T00:00:00Z', 5),
                ('2009-02-01T00:00:00Z', 0),
                ('2009-03-01T00:00:00Z', 0),
                ('2009-04-01T00:00:00Z', 1),
                ('2009-05-01T00:00:00Z', 2),
            ],
        }
        """
        facet_dict = {}

        for date_facet, facet_params in list(date_facets.items()):
            gap_type = facet_params.get('gap_by')
            gap_value = facet_params.get('gap_amount', 1)
            date_range = facet_params['start_date']
            facet_list = []
            while date_range < facet_params['end_date']:
                facet_list.append((date_range.isoformat(), 0))
                if gap_type == 'year':
                    date_range = date_range.replace(
                        year=date_range.year + int(gap_value)
                    )
                elif gap_type == 'month':
                    if date_range.month + int(gap_value) > 12:
                        date_range = date_range.replace(
                            month=((date_range.month + int(gap_value)) % 12),
                            year=(date_range.year + (date_range.month + int(gap_value)) / 12)
                        )
                    else:
                        date_range = date_range.replace(
                            month=date_range.month + int(gap_value)
                        )
                elif gap_type == 'day':
                    date_range += datetime.timedelta(days=int(gap_value))
                elif gap_type == 'hour':
                    date_range += datetime.timedelta(hours=int(gap_value))
                elif gap_type == 'minute':
                    date_range += datetime.timedelta(minutes=int(gap_value))
                elif gap_type == 'second':
                    date_range += datetime.timedelta(seconds=int(gap_value))

            facet_list = sorted(facet_list, key=lambda x: x[0], reverse=True)

            for result in results:
                result_date = getattr(result, date_facet)
                if result_date:
                    if not isinstance(result_date, datetime.datetime):
                        result_date = datetime.datetime(
                            year=result_date.year,
                            month=result_date.month,
                            day=result_date.day,
                        )
                    for n, facet_date in enumerate(facet_list):
                        if result_date > datetime.datetime(*(time.strptime(facet_date[0], '%Y-%m-%dT%H:%M:%S')[0:6])):
                            facet_list[n] = (facet_list[n][0], (facet_list[n][1] + 1))
                            break

            facet_dict[date_facet] = facet_list

        return facet_dict

    def _do_query_facets(self, results, query_facets):
        """
        Private method that facets a document by query

        Required arguments:
            `results` -- A list SearchResults to facet
            `query_facets` -- A dictionary containing facet parameters:
                {'field': 'query', [...]}

        For each query in `query_facets`, generates a dictionary entry with
        the field name as the key and a tuple with the query and result count
        as the value.

        eg. {'name': ('a*', 5)}
        """
        facet_dict = {}
        for field, query in list(dict(query_facets).items()):
            facet_dict[field] = (query, self.search(self.parse_query(query))['hits'])

        return facet_dict

    @staticmethod
    def _do_spelling_suggestion(database, query, spelling_query):
        """
        Private method that returns a single spelling suggestion based on
        `spelling_query` or `query`.

        Required arguments:
            `database` -- The database to check spelling against
            `query` -- The query to check
            `spelling_query` -- If not None, this will be checked instead of `query`

        Returns a string with a suggested spelling
        """
        if spelling_query:
            if ' ' in spelling_query:
                return ' '.join([database.get_spelling_suggestion(term) for term in spelling_query.split()])
            else:
                return database.get_spelling_suggestion(spelling_query)

        term_set = set()
        for term in query:
            for match in re.findall('[^A-Z]+', term):  # Ignore field identifiers
                term_set.add(database.get_spelling_suggestion(match))

        return ' '.join(term_set)

    def _database(self, writable=False):
        """
        Private method that returns a xapian.Database for use.

        Optional arguments:
            ``writable`` -- Open the database in read/write mode (default=False)

        Returns an instance of a xapian.Database or xapian.WritableDatabase
        """
        if self.path == MEMORY_DB_NAME:
            if not self.inmemory_db:
                self.inmemory_db = xapian.inmemory_open()
            return self.inmemory_db
        if writable:
            database = xapian.WritableDatabase(self.path, xapian.DB_CREATE_OR_OPEN)
        else:
            try:
                database = xapian.Database(self.path)
            except xapian.DatabaseOpeningError:
                raise InvalidIndexError('Unable to open index at %s' % self.path)

        return database

    @staticmethod
    def _get_enquire_mset(database, enquire, start_offset, end_offset, checkatleast=DEFAULT_CHECK_AT_LEAST):
        """
        A safer version of Xapian.enquire.get_mset

        Simply wraps the Xapian version and catches any `Xapian.DatabaseModifiedError`,
        attempting a `database.reopen` as needed.

        Required arguments:
            `database` -- The database to be read
            `enquire` -- An instance of an Xapian.enquire object
            `start_offset` -- The start offset to pass to `enquire.get_mset`
            `end_offset` -- The end offset to pass to `enquire.get_mset`
        """
        try:
            return enquire.get_mset(start_offset, end_offset, checkatleast)
        except xapian.DatabaseModifiedError:
            database.reopen()
            return enquire.get_mset(start_offset, end_offset, checkatleast)

    @staticmethod
    def _get_document_data(database, document):
        """
        A safer version of Xapian.document.get_data

        Simply wraps the Xapian version and catches any `Xapian.DatabaseModifiedError`,
        attempting a `database.reopen` as needed.

        Required arguments:
            `database` -- The database to be read
            `document` -- An instance of an Xapian.document object
        """
        try:
            return document.get_data()
        except xapian.DatabaseModifiedError:
            database.reopen()
            return document.get_data()

    def _get_hit_count(self, database, enquire):
        """
        Given a database and enquire instance, returns the estimated number
        of matches.

        Required arguments:
            `database` -- The database to be queried
            `enquire` -- The enquire instance
        """
        return self._get_enquire_mset(
            database, enquire, 0, database.get_doccount()
        ).size()

    def _multi_value_field(self, field):
        """
        Private method that returns `True` if a field is multi-valued, else
        `False`.

        Required arguemnts:
            `field` -- The field to lookup

        Returns a boolean value indicating whether the field is multi-valued.
        """
        for field_dict in self.schema:
            if field_dict['field_name'] == field:
                return field_dict['multi_valued'] == 'true'
        return False


class XapianSearchQuery(BaseSearchQuery):
    """
    This class is the Xapian specific version of the SearchQuery class.
    It acts as an intermediary between the ``SearchQuerySet`` and the
    ``SearchBackend`` itself.
    """
    def build_params(self, *args, **kwargs):
        kwargs = super(XapianSearchQuery, self).build_params(*args, **kwargs)

        if self.end_offset is not None:
            kwargs['end_offset'] = self.end_offset - self.start_offset

        return kwargs

    def build_query(self):
        if not self.query_filter:
            query = xapian.Query('')
        else:
            query = self._query_from_search_node(self.query_filter)

        if self.models:
            subqueries = [
                xapian.Query(
                    xapian.Query.OP_SCALE_WEIGHT,
                    xapian.Query('%s%s' % (TERM_PREFIXES['django_ct'], get_model_ct(model))),
                    0  # Pure boolean sub-query
                ) for model in self.models
            ]
            query = xapian.Query(
                xapian.Query.OP_AND, query,
                xapian.Query(xapian.Query.OP_OR, subqueries)
            )

        if self.boost:
            subqueries = [
                xapian.Query(
                    xapian.Query.OP_SCALE_WEIGHT,
                    self._term_query(term, None, None), value
                ) for term, value in list(self.boost.items())
            ]
            query = xapian.Query(
                xapian.Query.OP_AND_MAYBE, query,
                xapian.Query(xapian.Query.OP_OR, subqueries)
            )

        return query

    def _query_from_search_node(self, search_node, is_not=False):
        query_list = []

        for child in search_node.children:
            if isinstance(child, SearchNode):
                query_list.append(
                    self._query_from_search_node(child, child.negated)
                )
            else:
                expression, term = child
                field_name, filter_type = search_node.split_expression(expression)

                constructed_query_list = self._query_from_term(term, field_name, filter_type, is_not)
                query_list.extend(constructed_query_list)

        if search_node.connector == 'OR':
            return xapian.Query(xapian.Query.OP_OR, query_list)
        else:
            return xapian.Query(xapian.Query.OP_AND, query_list)

    def _query_from_term(self, term, field_name, filter_type, is_not):
        """
        Uses arguments to construct a list of xapian.Query's.
        """
        if field_name != 'content' and field_name not in self.backend.column:
            raise InvalidIndexError('field "%s" not indexed' % field_name)

        # It it is an AutoQuery, it has no filters
        # or others, thus we short-circuit the procedure.
        if isinstance(term, AutoQuery):
            if field_name != 'content':
                query = '%s:%s' % (field_name, term.prepare(self))
            else:
                query = term.prepare(self)
            return [self.backend.parse_query(query)]
        query_list = []

        # Handle `ValuesListQuerySet`.
        if hasattr(term, 'values_list'):
            term = list(term)

        if field_name == 'content':
            # content is the generic search:
            # force no field_name search
            # and the field_type to be 'text'.
            field_name = None
            field_type = 'text'

            # we don't know what is the type(term), so we parse it.
            # Ideally this would not be required, but
            # some filters currently depend on the term to make decisions.
            term = _to_xapian_term(term)

            query_list.append(self._filter_contains(term, field_name, field_type, is_not))
            # when filter has no filter_type, haystack uses
            # filter_type = 'contains'. Here we remove it
            # since the above query is already doing this
            if filter_type == 'contains':
                filter_type = None
        else:
            # get the field_type from the backend
            field_type = self.backend.schema[self.backend.column[field_name]]['type']

        # private fields don't accept 'contains' or 'startswith'
        # since they have no meaning.
        if filter_type in ('contains', 'startswith') and field_name in ('id', 'django_id', 'django_ct'):
            filter_type = 'exact'

        if field_type == 'text':
            # we don't know what type "term" is, but we know we are searching as text
            # so we parse it like that.
            # Ideally this would not be required since _term_query does it, but
            # some filters currently depend on the term to make decisions.
            if isinstance(term, list):
                term = [_to_xapian_term(term) for term in term]
            else:
                term = _to_xapian_term(term)

        # todo: we should check that the filter is valid for this field_type or raise InvalidIndexError
        if filter_type == 'contains':
            query_list.append(self._filter_contains(term, field_name, field_type, is_not))
        elif filter_type == 'exact':
            query_list.append(self._filter_exact(term, field_name, field_type, is_not))
        elif filter_type == 'in':
            query_list.append(self._filter_in(term, field_name, field_type, is_not))
        elif filter_type == 'startswith':
            query_list.append(self._filter_startswith(term, field_name, field_type, is_not))
        elif filter_type == 'gt':
            query_list.append(self._filter_gt(term, field_name, field_type, is_not))
        elif filter_type == 'gte':
            query_list.append(self._filter_gte(term, field_name, field_type, is_not))
        elif filter_type == 'lt':
            query_list.append(self._filter_lt(term, field_name, field_type, is_not))
        elif filter_type == 'lte':
            query_list.append(self._filter_lte(term, field_name, field_type, is_not))
        return query_list

    def _all_query(self):
        """
        Returns a match all query.
        """
        return xapian.Query('')

    def _filter_contains(self, term, field_name, field_type, is_not):
        """
        Splits the sentence in terms and join them with OR,
        using stemmed and un-stemmed.

        Assumes term is not a list.
        """
        if field_type == 'text':
            term_list = term.split()
        else:
            term_list = [term]

        query = self._or_query(term_list, field_name, field_type)
        if is_not:
            return xapian.Query(xapian.Query.OP_AND_NOT, self._all_query(), query)
        else:
            return query

    def _filter_in(self, term_list, field_name, field_type, is_not):
        """
        Returns a query that matches exactly ANY term in term_list.

        Notice that:
         A in {B,C} <=> (A = B or A = C)
         ~(A in {B,C}) <=> ~(A = B or A = C)
        Because OP_AND_NOT(C, D) <=> (C and ~D), then D=(A in {B,C}) requires `is_not=False`.

        Assumes term is a list.
        """
        query_list = [self._filter_exact(term, field_name, field_type, is_not=False)
                      for term in term_list]

        if is_not:
            return xapian.Query(xapian.Query.OP_AND_NOT, self._all_query(),
                                xapian.Query(xapian.Query.OP_OR, query_list))
        else:
            return xapian.Query(xapian.Query.OP_OR, query_list)

    def _filter_exact(self, term, field_name, field_type, is_not):
        """
        Returns a query that matches exactly the un-stemmed term
        with positional order.

        Assumes term is not a list.
        """
        if field_type == 'text':
            term = '^ %s $' % term
            query = self._phrase_query(term.split(), field_name, field_type)
        else:
            query = self._term_query(term, field_name, field_type, stemmed=False)

        if is_not:
            return xapian.Query(xapian.Query.OP_AND_NOT, self._all_query(), query)
        else:
            return query

    def _filter_startswith(self, term, field_name, field_type, is_not):
        """
        Returns a startswith query on the un-stemmed term.

        Assumes term is not a list.
        """
        # TODO: if field_type is of type integer, we need to marsh the value.
        if field_name:
            query_string = '%s:%s*' % (field_name, term)
        else:
            query_string = '%s*' % term

        query = self.backend.parse_query(query_string)

        if is_not:
            return xapian.Query(xapian.Query.OP_AND_NOT, self._all_query(), query)
        return query

    def _or_query(self, term_list, field, field_type):
        """
        Joins each item of term_list decorated by _term_query with an OR.
        """
        term_list = [self._term_query(term, field, field_type) for term in term_list]
        return xapian.Query(xapian.Query.OP_OR, term_list)

    def _phrase_query(self, term_list, field_name, field_type):
        """
        Returns a query that matches exact terms with
        positional order (i.e. ["this", "thing"] != ["thing", "this"])
        and no stem.

        If `field_name` is not `None`, restrict to the field.
        """
        term_list = [self._term_query(term, field_name, field_type,
                                      stemmed=False) for term in term_list]

        query = xapian.Query(xapian.Query.OP_PHRASE, term_list)
        return query

    def _term_query(self, term, field_name, field_type, stemmed=True):
        """
        Constructs a query of a single term.

        If `field_name` is not `None`, the term is search on that field only.
        If exact is `True`, the search is restricted to boolean matches.
        """
        constructor = '{prefix}{term}'

        # construct the prefix to be used.
        prefix = ''
        if field_name:
            prefix = TERM_PREFIXES['field'] + field_name.upper()
            term = _to_xapian_term(term)

        if field_name in ('id', 'django_id', 'django_ct'):
            # to ensure the value is serialized correctly.
            if field_name == 'django_id':
                term = int(term)
            term = _term_to_xapian_value(term, field_type)
            return xapian.Query('%s%s' % (TERM_PREFIXES[field_name], term))

        # we construct the query dates in a slightly different way
        if field_type == 'datetime':
            date, time = term.split()
            return xapian.Query(xapian.Query.OP_AND_MAYBE,
                                constructor.format(prefix=prefix, term=date),
                                constructor.format(prefix=prefix, term=time)
                                )

        # only use stem if field is text or "None"
        if field_type not in ('text', None):
            stemmed = False

        unstemmed_term = constructor.format(prefix=prefix, term=term)
        if stemmed:
            stem = xapian.Stem(self.backend.language)
            stemmed_term = 'Z' + constructor.format(prefix=prefix, term=stem(term).decode('utf-8'))

            return xapian.Query(xapian.Query.OP_OR,
                                xapian.Query(stemmed_term),
                                xapian.Query(unstemmed_term)
                                )
        else:
            return xapian.Query(unstemmed_term)

    def _filter_gt(self, term, field_name, field_type, is_not):
        return self._filter_lte(term, field_name, field_type, is_not=not is_not)

    def _filter_lt(self, term, field_name, field_type, is_not):
        return self._filter_gte(term, field_name, field_type, is_not=not is_not)

    def _filter_gte(self, term, field_name, field_type, is_not):
        """
        Private method that returns a xapian.Query that searches for any term
        that is greater than `term` in a specified `field`.
        """
        vrp = XHValueRangeProcessor(self.backend)
        pos, begin, end = vrp('%s:%s' % (field_name, _term_to_xapian_value(term, field_type)), '*')
        if is_not:
            return xapian.Query(xapian.Query.OP_AND_NOT,
                                self._all_query(),
                                xapian.Query(xapian.Query.OP_VALUE_RANGE, pos, begin, end)
                                )
        return xapian.Query(xapian.Query.OP_VALUE_RANGE, pos, begin, end)

    def _filter_lte(self, term, field_name, field_type, is_not):
        """
        Private method that returns a xapian.Query that searches for any term
        that is less than `term` in a specified `field`.
        """
        vrp = XHValueRangeProcessor(self.backend)
        pos, begin, end = vrp('%s:' % field_name, '%s' % _term_to_xapian_value(term, field_type))
        if is_not:
            return xapian.Query(xapian.Query.OP_AND_NOT,
                                self._all_query(),
                                xapian.Query(xapian.Query.OP_VALUE_RANGE, pos, begin, end)
                                )
        return xapian.Query(xapian.Query.OP_VALUE_RANGE, pos, begin, end)


def _term_to_xapian_value(term, field_type):
    """
    Converts a term to a serialized
    Xapian value based on the field_type.
    """
    assert field_type in FIELD_TYPES

    def strf(dt):
        """
        Equivalent to datetime.datetime.strptime(dt, DATETIME_FORMAT)
        but accepts years below 1900 (see http://stackoverflow.com/q/10263956/931303)
        """
        return '%04d%02d%02d%02d%02d%02d' % (
            dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

    if field_type == 'boolean':
        assert isinstance(term, bool)
        if term:
            value = 't'
        else:
            value = 'f'

    elif field_type == 'integer':
        value = INTEGER_FORMAT % term
    elif field_type == 'float':
        value = xapian.sortable_serialise(term)
    elif field_type == 'date' or field_type == 'datetime':
        if field_type == 'date':
            # http://stackoverflow.com/a/1937636/931303 and comments
            term = datetime.datetime.combine(term, datetime.time())
        value = strf(term)
    else:  # field_type == 'text'
        value = _to_xapian_term(term)

    return value


def _to_xapian_term(term):
    """
    Converts a Python type to a
    Xapian term that can be indexed.
    """
    return force_text(term).lower()


def _from_xapian_value(value, field_type):
    """
    Converts a serialized Xapian value
    to Python equivalent based on the field_type.

    Doesn't accept multivalued fields.
    """
    assert field_type in FIELD_TYPES
    if field_type == 'boolean':
        if value == 't':
            return True
        elif value == 'f':
            return False
        else:
            InvalidIndexError('Field type "%d" does not accept value "%s"' % (field_type, value))
    elif field_type == 'integer':
        return int(value)
    elif field_type == 'float':
        return xapian.sortable_unserialise(value)
    elif field_type == 'date' or field_type == 'datetime':
        datetime_value = datetime.datetime.strptime(value, DATETIME_FORMAT)
        if field_type == 'datetime':
            return datetime_value
        else:
            return datetime_value.date()
    else:  # field_type == 'text'
        return value


class XapianEngine(BaseEngine):
    backend = XapianSearchBackend
    query = XapianSearchQuery

########NEW FILE########
