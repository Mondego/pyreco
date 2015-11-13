__FILENAME__ = index
#-*- coding:utf-8 -*-
import redis

try:
  import simplejson
except:
  from django.utils import simplejson

try:
  from django.core import serializers
  from django.db.models.loading import get_model
except:
  pass

import mmseg
from autocomplete.utils import queryset_iterator

class Autocomplete (object):
  """
  autocomplete.
  """

  def __init__ (self, scope, redisaddr="localhost", limits=5, cached=True):
    self.r = redis.Redis (redisaddr)
    self.scope = scope
    self.cached=cached
    self.limits = limits
    self.database = "database:%s" % scope
    self.indexbase = "indexbase:%s" % scope
    mmseg.Dictionary.load_dictionaries ()

  def _get_index_key (self, key):
    return "%s:%s" % (self.indexbase, key)

  def del_index (self):
    prefixs = self.r.smembers (self.indexbase)
    for prefix in prefixs:
      self.r.delete(self._get_index_key(prefix))
    self.r.delete(self.indexbase)
    self.r.delete(self.database)

  def sanity_check (self, item):
    """
    Make sure item has key that's needed.
    """
    for key in ("uid","term"):
      if not item.has_key (key):
        raise Exception ("Item should have key %s"%key )

  def add_item (self,item):
    """
    Create index for ITEM.
    """
    self.sanity_check (item)
    self.r.hset (self.database, item.get('uid'), simplejson.dumps(item))
    for prefix in self.prefixs_for_term (item['term']):
      self.r.sadd (self.indexbase, prefix)
      self.r.zadd (self._get_index_key(prefix),item.get('uid'), item.get('score',0))

  def del_item (self,item):
    """
    Delete ITEM from the index
    """
    for prefix in self.prefixs_for_term (item['term']):
      self.r.zrem (self._get_index_key(prefix), item.get('uid'))
      if not self.r.zcard (self._get_index_key(prefix)):
        self.r.delete (self._get_index_key(prefix))
        self.r.srem (self.indexbase, prefix)

  def update_item (self, item):
    self.del_item (item)
    self.add_item (item)

  def prefixs_for_term (self,term):
    """
    Get prefixs for TERM.
    """
    # Normalization
    term=term.lower()

    # Prefixs for term
    prefixs=[]
    tokens=mmseg.Algorithm(term)
    for token in tokens:
      word = token.text
      for i in xrange (1,len(word)+1):
        prefixs.append(word[:i])

    return prefixs

  def normalize (self,prefix):
    """
    Normalize the search string.
    """
    tokens = mmseg.Algorithm(prefix.lower())
    return [token.text for token in tokens]

  def search_query (self,prefix):
    search_strings = self.normalize (prefix)

    if not search_strings: return []

    cache_key = self._get_index_key (('|').join(search_strings))

    if not self.cached or not self.r.exists (cache_key):
      self.r.zinterstore (cache_key, map (lambda x: self._get_index_key(x), search_strings))
      self.r.expire (cache_key, 10 * 60)

    ids=self.r.zrevrange (cache_key, 0, self.limits)
    if not ids: return ids
    return map(lambda x:simplejson.loads(x),
               self.r.hmget(self.database, *ids))

########NEW FILE########
__FILENAME__ = utils
import gc

def queryset_iterator(queryset, chunksize=1000):
  '''''
  Iterate over a Django Queryset ordered by the primary key

  This method loads a maximum of chunksize (default: 1000) rows in it's
  memory at the same time while django normally would load all rows in it's
  memory. Using the iterator() method only causes it to not preload all the
  classes.

  Note that the implementation of the iterator does not support ordered query sets.
  '''
  pk = 0
  last_pk = queryset.order_by('-pk')[0].pk
  queryset = queryset.order_by('pk')
  while pk < last_pk:
    for row in queryset.filter(pk__gt=pk)[:chunksize]:
      pk = row.pk
      yield row
    gc.collect()

########NEW FILE########
__FILENAME__ = test
#-*-coding:utf-8-*-
from autocomplete import Autocomplete
import os
import unittest

class testAutocomplete (unittest.TestCase):
  def setUp (self):
    self.items=[{"uid":'1', "score":9, "term": u"轻轻地你走了"},
                {"uid":'2', "score":10, "term": u"正如你轻轻地来"},
                {"uid":'3', "score":8.5, "term":u"你挥一挥衣袖，不带走一片云彩"},
                ]

    self.a=Autocomplete("scope")
    self.a.del_index()
    for item in self.items:
      self.a.add_item (item)

  def test_search_query2 (self):
    results=self.a.search_query (u'轻轻')
    self.assertEqual(len(results),2)
    self.assertEqual(results[0]['uid'],'2')
    self.assertEqual(results[1]['uid'],'1')

  def test_search_query3 (self):
    results=self.a.search_query (u'你 带走')
    self.assertEqual(len(results),1)
    self.assertEqual(results[0]['uid'],'3')

  def test_search_query4 (self):
    results=self.a.search_query (u'你挥一挥衣袖，不带走一片云彩')
    self.assertEqual(len(results),1)
    self.assertEqual(results[0]['uid'],'3')

  def test_update_item (self):
    item = {"uid":'1', "score":13, "term": u"轻轻地你走了"}
    self.a.update_item (item)
    results=self.a.search_query (u'轻轻')
    self.assertEqual(len(results),2)
    self.assertEqual(results[0]['uid'],'1')
    self.assertEqual(results[1]['uid'],'2')

  def test_del_item (self):
    item = {"uid":'1', "score":9, "term": u"轻轻地你走了"}
    self.a.del_item (item)
    results=self.a.search_query (u'轻轻')
    self.assertEqual(len(results),1)
    self.assertEqual(results[0]['uid'],'2')

if __name__=='__main__':
  unittest.main ()

########NEW FILE########
