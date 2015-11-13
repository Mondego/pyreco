__FILENAME__ = admin
#!/usr/bin/env python
#
# Copyright 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Defines the routing for the app's admin request handlers
(those that require administrative access)."""

from admin_handlers import *

import webapp2

application = webapp2.WSGIApplication(
    [
        ('/admin/manage', AdminHandler),
        ('/admin/create_product', CreateProductHandler),
        ('/admin/delete_product', DeleteProductHandler)
    ],
    debug=True)


########NEW FILE########
__FILENAME__ = admin_handlers
#!/usr/bin/env python
#
# Copyright 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" Contains the admin request handlers for the app (those that require
administrative access).
"""

import csv
import logging
import os
import urllib
import uuid

from base_handler import BaseHandler
import categories
import config
import docs
import errors
import models
import stores
import utils

from google.appengine.api import users
from google.appengine.ext.deferred import defer
from google.appengine.ext import ndb
from google.appengine.api import search


def reinitAll(sample_data=True):
  """
  Deletes all product entities and documents, essentially resetting the app
  state, then loads in static sample data if requested. Hardwired for the
  expected product types in the sample data.
  (Re)loads store location data from stores.py as well.
  This function is intended to be run 'offline' (e.g., via a Task Queue task).
  As an extension to this functionality, the channel ID could be used to notify
  when done."""

  # delete all the product and review entities
  review_keys = models.Review.query().fetch(keys_only=True)
  ndb.delete_multi(review_keys)
  prod_keys = models.Product.query().fetch(keys_only=True)
  ndb.delete_multi(prod_keys)
  # delete all the associated product documents in the doc and
  # store indexes
  docs.Product.deleteAllInProductIndex()
  docs.Store.deleteAllInIndex()
  # load in sample data if indicated
  if sample_data:
    logging.info('Loading product sample data')
    # Load from csv sample files.
    # The following are hardwired to the format of the sample data files
    # for the two example product types ('books' and 'hd televisions')-- see
    # categories.py
    datafile = os.path.join('data', config.SAMPLE_DATA_BOOKS)
    # books
    reader = csv.DictReader(
        open(datafile, 'r'),
        ['pid', 'name', 'category', 'price',
         'publisher', 'title', 'pages', 'author',
         'description', 'isbn'])
    importData(reader)
    datafile = os.path.join('data', config.SAMPLE_DATA_TVS)
    # tvs
    reader = csv.DictReader(
        open(datafile, 'r'),
        ['pid', 'name', 'category', 'price',
         'size', 'brand', 'tv_type',
         'description'])
    importData(reader)

    # next create docs from store location info
    loadStoreLocationData()

  logging.info('Re-initialization complete.')

def loadStoreLocationData():
    # create documents from store location info
    # currently logs but otherwise swallows search errors.
    slocs = stores.stores
    for s in slocs:
      logging.info("s: %s", s)
      geopoint = search.GeoPoint(s[3][0], s[3][1])
      fields = [search.TextField(name=docs.Store.STORE_NAME, value=s[1]),
                search.TextField(name=docs.Store.STORE_ADDRESS, value=s[2]),
                search.GeoField(name=docs.Store.STORE_LOCATION, value=geopoint)
              ]
      d = search.Document(doc_id=s[0], fields=fields)
      try:
        add_result = search.Index(config.STORE_INDEX_NAME).put(d)
      except search.Error:
        logging.exception("Error adding document:")


def importData(reader):
  """Import via the csv reader iterator using the specified batch size as set in
  the config file.  We want to ensure the batch is not too large-- we allow 100
  rows/products max per batch."""
  MAX_BATCH_SIZE = 100
  rows = []
  # index in batches
  # ensure the batch size in the config file is not over the max or < 1.
  batchsize = utils.intClamp(config.IMPORT_BATCH_SIZE, 1, MAX_BATCH_SIZE)
  logging.debug('batchsize: %s', batchsize)
  for row in reader:
    if len(rows) == batchsize:
      docs.Product.buildProductBatch(rows)
      rows = [row]
    else:
      rows.append(row)
  if rows:
    docs.Product.buildProductBatch(rows)


class AdminHandler(BaseHandler):
  """Displays the admin page."""

  def buildAdminPage(self, notification=None):
    # If necessary, build the app's product categories now.  This is done only
    # if there are no Category entities in the datastore.
    models.Category.buildAllCategories()
    tdict = {
        'sampleb': config.SAMPLE_DATA_BOOKS,
        'samplet': config.SAMPLE_DATA_TVS,
        'update_sample': config.DEMO_UPDATE_BOOKS_DATA}
    if notification:
      tdict['notification'] = notification
    self.render_template('admin.html', tdict)

  @BaseHandler.logged_in
  def get(self):
    action = self.request.get('action')
    if action == 'reinit':
      # reinitialise the app data to the sample data
      defer(reinitAll)
      self.buildAdminPage(notification="Reinitialization performed.")
    elif action == 'demo_update':
      # update the sample data, from (hardwired) book update
      # data. Demonstrates updating some existing products, and adding some new
      # ones.
      logging.info('Loading product sample update data')
      # The following is hardwired to the known format of the sample data file
      datafile = os.path.join('data', config.DEMO_UPDATE_BOOKS_DATA)
      reader = csv.DictReader(
          open(datafile, 'r'),
          ['pid', 'name', 'category', 'price',
           'publisher', 'title', 'pages', 'author',
           'description', 'isbn'])
      for row in reader:
        docs.Product.buildProduct(row)
      self.buildAdminPage(notification="Demo update performed.")

    elif action == 'update_ratings':
      self.update_ratings()
      self.buildAdminPage(notification="Ratings update performed.")
    else:
      self.buildAdminPage()

  def update_ratings(self):
    """Find the products that have had an average ratings change, and need their
    associated documents updated (re-indexed) to reflect that change; and
    re-index those docs in batch. There will only
    be such products if config.BATCH_RATINGS_UPDATE is True; otherwise the
    associated documents will be updated right away."""
    # get the pids of the products that need review info updated in their
    # associated documents.
    pkeys = models.Product.query(
        models.Product.needs_review_reindex == True).fetch(keys_only=True)
    # re-index these docs in batch
    models.Product.updateProdDocsWithNewRating(pkeys)


class DeleteProductHandler(BaseHandler):
  """Remove data for the product with the given pid, including that product's
  reviews and its associated indexed document."""

  @BaseHandler.logged_in
  def post(self):
    pid = self.request.get('pid')
    if not pid:  # this should not be reached
      msg = 'There was a problem: no product id given.'
      logging.error(msg)
      url = '/'
      linktext = 'Go to product search page.'
      self.render_template(
          'notification.html',
          {'title': 'Error', 'msg': msg,
           'goto_url': url, 'linktext': linktext})
      return

    # Delete the product entity within a transaction, and define transactional
    # tasks for deleting the product's reviews and its associated document.
    # These tasks will only be run if the transaction successfully commits.
    def _tx():
      prod = models.Product.get_by_id(pid)
      if prod:
        prod.key.delete()
        defer(models.Review.deleteReviews, prod.key.id(), _transactional=True)
        defer(
            docs.Product.removeProductDocByPid,
            prod.key.id(), _transactional=True)

    ndb.transaction(_tx)
    # indicate success
    msg = (
        'The product with product id %s has been ' +
        'successfully removed.') % (pid,)
    url = '/'
    linktext = 'Go to product search page.'
    self.render_template(
        'notification.html',
        {'title': 'Product Removed', 'msg': msg,
         'goto_url': url, 'linktext': linktext})


class CreateProductHandler(BaseHandler):
  """Handler to create a new product: this constitutes both a product entity
  and its associated indexed document."""

  def parseParams(self):
    """Filter the param set to the expected params."""

    pid = self.request.get('pid')
    doc = docs.Product.getDocFromPid(pid)
    params = {}
    if doc:  # populate default params from the doc
      fields = doc.fields
      for f in fields:
        params[f.name] = f.value
    else:
      # start with the 'core' fields
      params = {
          'pid': uuid.uuid4().hex,  # auto-generate default UID
          'name': '',
          'description': '',
          'category': '',
          'price': ''}
      pf = categories.product_dict
      # add the fields specific to the categories
      for _, cdict in pf.iteritems():
        temp = {}
        for elt in cdict.keys():
          temp[elt] = ''
        params.update(temp)

    for k, v in params.iteritems():
      # Process the request params. Possibly replace default values.
      params[k] = self.request.get(k, v)
    return params

  @BaseHandler.logged_in
  def get(self):
    params = self.parseParams()
    self.render_template('create_product.html', params)

  @BaseHandler.logged_in
  def post(self):
    self.createProduct(self.parseParams())

  def createProduct(self, params):
    """Create a product entity and associated document from the given params
    dict."""

    try:
      product = docs.Product.buildProduct(params)
      self.redirect(
          '/product?' + urllib.urlencode(
              {'pid': product.pid, 'pname': params['name'],
               'category': product.category
              }))
    except errors.Error as e:
      logging.exception('Error:')
      params['error_message'] = e.error_message
      self.render_template('create_product.html', params)



########NEW FILE########
__FILENAME__ = base_handler
#!/usr/bin/env python
#
# Copyright 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" The base request handler class.
"""


import webapp2
from webapp2_extras import jinja2
import json

from google.appengine.api import users


class BaseHandler(webapp2.RequestHandler):
  """The other handlers inherit from this class.  Provides some helper methods
  for rendering a template and generating template links."""

  @classmethod
  def logged_in(cls, handler_method):
    """
    This decorator requires a logged-in user, and returns 403 otherwise.
    """
    def auth_required(self, *args, **kwargs):
      if (users.get_current_user() or
          self.request.headers.get('X-AppEngine-Cron')):
        handler_method(self, *args, **kwargs)
      else:
        self.error(403)
    return auth_required

  @webapp2.cached_property
  def jinja2(self):
    return jinja2.get_jinja2(app=self.app)

  def render_template(self, filename, template_args):
    template_args.update(self.generateSidebarLinksDict())
    self.response.write(self.jinja2.render_template(filename, **template_args))

  def render_json(self, response):
    self.response.write("%s(%s);" % (self.request.GET['callback'],
                                     json.dumps(response)))

  def getLoginLink(self):
    """Generate login or logout link and text, depending upon the logged-in
    status of the client."""
    if users.get_current_user():
      url = users.create_logout_url(self.request.uri)
      url_linktext = 'Logout'
    else:
      url = users.create_login_url(self.request.uri)
      url_linktext = 'Login'
    return (url, url_linktext)

  def getAdminManageLink(self):
    """Build link to the admin management page, if the user is logged in."""
    if users.get_current_user():
      admin_url = '/admin/manage'
      return (admin_url, 'Admin/Add sample data')
    else:
      return (None, None)

  def createProductAdminLink(self):
    if users.get_current_user():
      admin_create_url = '/admin/create_product'
      return (admin_create_url, 'Create new product (admin)')
    else:
      return (None, None)

  def generateSidebarLinksDict(self):
    """Build a dict containing login/logout and admin links, which will be
    included in the sidebar for all app pages."""

    url, url_linktext = self.getLoginLink()
    admin_create_url, admin_create_text = self.createProductAdminLink()
    admin_url, admin_text = self.getAdminManageLink()
    return {
        'admin_create_url': admin_create_url,
        'admin_create_text': admin_create_text,
        'admin_url': admin_url,
        'admin_text': admin_text,
        'url': url,
        'url_linktext': url_linktext
        }


########NEW FILE########
__FILENAME__ = categories
#!/usr/bin/env python
#
# Copyright 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Specifies product category information for the app.  In this sample, there
are two categories: books, and televisions.
"""
from google.appengine.api import search


televisions = {'name': 'hd televisions', 'children': []}
books = {'name': 'books', 'children': []}

ctree =  {'name': 'root', 'children': [books, televisions]}

# [The core fields that all products share are: product id, name, description,
# category, category name, and price]
# Define the non-'core' (differing) product fields for each category
# above, and their types.
product_dict =  {'hd televisions': {'size': search.NumberField,
                                 'brand': search.TextField,
                                 'tv_type': search.TextField},
                 'books': {'publisher': search.TextField,
                           'pages': search.NumberField,
                           'author': search.TextField,
                           'title': search.TextField,
                           'isbn': search.TextField}
                }

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python
#
# Copyright 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" Holds configuration settings.
"""


PRODUCT_INDEX_NAME = 'productsearch1'  # The document index name.
    # An index name must be a visible printable
    # ASCII string not starting with '!'. Whitespace characters are
    # excluded.

STORE_INDEX_NAME = 'stores1'

# set BATCH_RATINGS_UPDATE to False to update documents with changed ratings
# info right away.  If True, updates will only occur when triggered by
# an admin request or a cron job.  See cron.yaml for an example.
BATCH_RATINGS_UPDATE = False
# BATCH_RATINGS_UPDATE = True

# The max and min (integer) ratings values allowed.
RATING_MIN = 1
RATING_MAX = 5

# the number of search results to display per page
DOC_LIMIT = 3

SAMPLE_DATA_BOOKS = 'sample_data_books.csv'
SAMPLE_DATA_TVS = 'sample_data_tvs.csv'
DEMO_UPDATE_BOOKS_DATA = 'sample_data_books_update.csv'

# the size of the import batches, when reading from the csv file.  Must not
# exceed 100.
IMPORT_BATCH_SIZE = 5

########NEW FILE########
__FILENAME__ = docs
#!/usr/bin/env python
#
# Copyright 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" Contains 'helper' classes for managing search.Documents.
BaseDocumentManager provides some common utilities, and the Product subclass
adds some Product-document-specific helper methods.
"""

import collections
import copy
import datetime
import logging
import re
import string
import urllib

import categories
import config
import errors
import models

from google.appengine.api import search
from google.appengine.ext import ndb


class BaseDocumentManager(object):
  """Abstract class. Provides helper methods to manage search.Documents."""

  _INDEX_NAME = None
  _VISIBLE_PRINTABLE_ASCII = frozenset(
    set(string.printable) - set(string.whitespace))

  def __init__(self, doc):
    """Builds a dict of the fields mapped against the field names, for
    efficient access.
    """
    self.doc = doc
    fields = doc.fields

  def getFieldVal(self, fname):
    """Get the value of the document field with the given name.  If there is
    more than one such field, the method returns None."""
    try:
      return self.doc.field(fname).value
    except ValueError:
      return None

  def setFirstField(self, new_field):
    """Set the value of the (first) document field with the given name."""
    for i, field in enumerate(self.doc.fields):
      if field.name == new_field.name:
        self.doc.fields[i] = new_field
        return True
    return False

  @classmethod
  def isValidDocId(cls, doc_id):
    """Checks if the given id is a visible printable ASCII string not starting
    with '!'.  Whitespace characters are excluded.
    """
    for char in doc_id:
      if char not in cls._VISIBLE_PRINTABLE_ASCII:
        return False
    return not doc_id.startswith('!')

  @classmethod
  def getIndex(cls):
    return search.Index(name=cls._INDEX_NAME)

  @classmethod
  def deleteAllInIndex(cls):
    """Delete all the docs in the given index."""
    docindex = cls.getIndex()

    try:
      while True:
        # until no more documents, get a list of documents,
        # constraining the returned objects to contain only the doc ids,
        # extract the doc ids, and delete the docs.
        document_ids = [document.doc_id
                        for document in docindex.get_range(ids_only=True)]
        if not document_ids:
          break
        docindex.delete(document_ids)
    except search.Error:
      logging.exception("Error removing documents:")

  @classmethod
  def getDoc(cls, doc_id):
    """Return the document with the given doc id. One way to do this is via
    the get_range method, as shown here.  If the doc id is not in the
    index, the first doc in the index will be returned instead, so we need
    to check for that case."""
    if not doc_id:
      return None
    try:
      index = cls.getIndex()
      response = index.get_range(
          start_id=doc_id, limit=1, include_start_object=True)
      if response.results and response.results[0].doc_id == doc_id:
        return response.results[0]
      return None
    except search.InvalidRequest: # catches ill-formed doc ids
      return None

  @classmethod
  def removeDocById(cls, doc_id):
    """Remove the doc with the given doc id."""
    try:
      cls.getIndex().delete(doc_id)
    except search.Error:
      logging.exception("Error removing doc id %s.", doc_id)

  @classmethod
  def add(cls, documents):
    """wrapper for search index add method; specifies the index name."""
    try:
      return cls.getIndex().put(documents)
    except search.Error:
      logging.exception("Error adding documents.")


class Store(BaseDocumentManager):

  _INDEX_NAME = config.STORE_INDEX_NAME
  STORE_NAME = 'store_name'
  STORE_LOCATION = 'store_location'
  STORE_ADDRESS = 'store_address'


class Product(BaseDocumentManager):
  """Provides helper methods to manage Product documents.  All Product documents
  built using these methods will include a core set of fields (see the
  _buildCoreProductFields method).  We use the given product id (the Product
  entity key) as the doc_id.  This is not required for the entity/document
  design-- each explicitly point to each other, allowing their ids to be
  decoupled-- but using the product id as the doc id allows a document to be
  reindexed given its product info, without having to fetch the
  existing document."""

  _INDEX_NAME = config.PRODUCT_INDEX_NAME

  # 'core' product document field names
  PID = 'pid'
  DESCRIPTION = 'description'
  CATEGORY = 'category'
  PRODUCT_NAME = 'name'
  PRICE = 'price'
  AVG_RATING = 'ar' #average rating
  UPDATED = 'modified'

  _SORT_OPTIONS = [
        [AVG_RATING, 'average rating', search.SortExpression(
            expression=AVG_RATING,
            direction=search.SortExpression.DESCENDING, default_value=0)],
        [PRICE, 'price', search.SortExpression(
            # other examples:
            # expression='max(price, 14.99)'
            # If you access _score in your sort expressions,
            # your SortOptions should include a scorer.
            # e.g. search.SortOptions(match_scorer=search.MatchScorer(),...)
            # Then, you can access the score to build expressions like:
            # expression='price * _score'
            expression=PRICE,
            direction=search.SortExpression.ASCENDING, default_value=9999)],
        [UPDATED, 'modified', search.SortExpression(
            expression=UPDATED,
            direction=search.SortExpression.DESCENDING, default_value=1)],
        [CATEGORY, 'category', search.SortExpression(
            expression=CATEGORY,
            direction=search.SortExpression.ASCENDING, default_value='')],
        [PRODUCT_NAME, 'product name', search.SortExpression(
            expression=PRODUCT_NAME,
            direction=search.SortExpression.ASCENDING, default_value='zzz')]
      ]

  _SORT_MENU = None
  _SORT_DICT = None


  @classmethod
  def deleteAllInProductIndex(cls):
    cls.deleteAllInIndex()

  @classmethod
  def getSortMenu(cls):
    if not cls._SORT_MENU:
      cls._buildSortMenu()
    return cls._SORT_MENU

  @classmethod
  def getSortDict(cls):
    if not cls._SORT_DICT:
      cls._buildSortDict()
    return cls._SORT_DICT

  @classmethod
  def _buildSortMenu(cls):
    """Build the default set of sort options used for Product search.
    Of these options, all but 'relevance' reference core fields that
    all Products will have."""
    res = [(elt[0], elt[1]) for elt in cls._SORT_OPTIONS]
    cls._SORT_MENU = [('relevance', 'relevance')] + res

  @classmethod
  def _buildSortDict(cls):
    """Build a dict that maps sort option keywords to their corresponding
    SortExpressions."""
    cls._SORT_DICT = {}
    for elt in cls._SORT_OPTIONS:
      cls._SORT_DICT[elt[0]] = elt[2]

  @classmethod
  def getDocFromPid(cls, pid):
    """Given a pid, get its doc. We're using the pid as the doc id, so we can
    do this via a direct fetch."""
    return cls.getDoc(pid)

  @classmethod
  def removeProductDocByPid(cls, pid):
    """Given a doc's pid, remove the doc matching it from the product
    index."""
    cls.removeDocById(pid)

  @classmethod
  def updateRatingInDoc(cls, doc_id, avg_rating):
    # get the associated doc from the doc id in the product entity
    doc = cls.getDoc(doc_id)
    if doc:
      pdoc = cls(doc)
      pdoc.setAvgRating(avg_rating)
      # The use of the same id will cause the existing doc to be reindexed.
      return doc
    else:
      raise errors.OperationFailedError(
          'Could not retrieve doc associated with id %s' % (doc_id,))

  @classmethod
  def updateRatingsInfo(cls, doc_id, avg_rating):
    """Given a models.Product entity, update and reindex the associated
    document with the product entity's current average rating. """

    ndoc = cls.updateRatingInDoc(doc_id, avg_rating)
    # reindex the returned updated doc
    return cls.add(ndoc)

# 'accessor' convenience methods

  def getPID(self):
    """Get the value of the 'pid' field of a Product doc."""
    return self.getFieldVal(self.PID)

  def getName(self):
    """Get the value of the 'name' field of a Product doc."""
    return self.getFieldVal(self.PRODUCT_NAME)

  def getDescription(self):
    """Get the value of the 'description' field of a Product doc."""
    return self.getFieldVal(self.DESCRIPTION)

  def getCategory(self):
    """Get the value of the 'cat' field of a Product doc."""
    return self.getFieldVal(self.CATEGORY)

  def setCategory(self, cat):
    """Set the value of the 'cat' (category) field of a Product doc."""
    return self.setFirstField(search.NumberField(name=self.CATEGORY, value=cat))

  def getAvgRating(self):
    """Get the value of the 'ar' (average rating) field of a Product doc."""
    return self.getFieldVal(self.AVG_RATING)

  def setAvgRating(self, ar):
    """Set the value of the 'ar' field of a Product doc."""
    return self.setFirstField(search.NumberField(name=self.AVG_RATING, value=ar))

  def getPrice(self):
    """Get the value of the 'price' field of a Product doc."""
    return self.getFieldVal(self.PRICE)

  @classmethod
  def generateRatingsBuckets(cls, query_string):
    """Builds a dict of ratings 'buckets' and their counts, based on the
    value of the 'avg_rating" field for the documents retrieved by the given
    query.  See the 'generateRatingsLinks' method.  This information will
    be used to generate sidebar links that allow the user to drill down in query
    results based on rating.

    For demonstration purposes only; this will be expensive for large data
    sets.
    """

    # do the query on the *full* search results
    # to generate the facet information, imitating what may in future be
    # provided by the FTS API.
    try:
      sq = search.Query(
          query_string=query_string.strip())
      search_results = cls.getIndex().search(sq)
    except search.Error:
      logging.exception('An error occurred on search.')
      return None

    ratings_buckets = collections.defaultdict(int)
    # populate the buckets
    for res in search_results:
      ratings_buckets[int((cls(res)).getAvgRating() or 0)] += 1
    return ratings_buckets

  @classmethod
  def generateRatingsLinks(cls, query, phash):
    """Given a dict of ratings 'buckets' and their counts,
    builds a list of html snippets, to be displayed in the sidebar when
    showing results of a query. Each is a link that runs the query, additionally
    filtered by the indicated ratings interval."""

    ratings_buckets = cls.generateRatingsBuckets(query)
    if not ratings_buckets:
      return None
    rlist = []
    for k in range(config.RATING_MIN, config.RATING_MAX+1):
      try:
        v = ratings_buckets[k]
      except KeyError:
        return
      # build html
      if k < 5:
        htext = '%s-%s (%s)' % (k, k+1, v)
      else:
        htext = '%s (%s)' % (k, v)
      phash['rating'] = k
      hlink = '/psearch?' + urllib.urlencode(phash)
      rlist.append((hlink, htext))
    return rlist

  @classmethod
  def _buildCoreProductFields(
      cls, pid, name, description, category, category_name, price):
    """Construct a 'core' document field list for the fields common to all
    Products. The various categories (as defined in the file 'categories.py'),
    may add additional specialized fields; these will be appended to this
    core list. (see _buildProductFields)."""
    fields = [search.TextField(name=cls.PID, value=pid),
              # The 'updated' field is always set to the current date.
              search.DateField(name=cls.UPDATED,
                  value=datetime.datetime.now().date()),
              search.TextField(name=cls.PRODUCT_NAME, value=name),
              # strip the markup from the description value, which can
              # potentially come from user input.  We do this so that
              # we don't need to sanitize the description in the
              # templates, showing off the Search API's ability to mark up query
              # terms in generated snippets.  This is done only for
              # demonstration purposes; in an actual app,
              # it would be preferrable to use a library like Beautiful Soup
              # instead.
              # We'll let the templating library escape all other rendered
              # values for us, so this is the only field we do this for.
              search.TextField(
                  name=cls.DESCRIPTION,
                  value=re.sub(r'<[^>]*?>', '', description)),
              search.AtomField(name=cls.CATEGORY, value=category),
              search.NumberField(name=cls.AVG_RATING, value=0.0),
              search.NumberField(name=cls.PRICE, value=price)
             ]
    return fields

  @classmethod
  def _buildProductFields(cls, pid=None, category=None, name=None,
      description=None, category_name=None, price=None, **params):
    """Build all the additional non-core fields for a document of the given
    product type (category), using the given params dict, and the
    already-constructed list of 'core' fields.  All such additional
    category-specific fields are treated as required.
    """

    fields = cls._buildCoreProductFields(
        pid, name, description, category, category_name, price)
    # get the specification of additional (non-'core') fields for this category
    pdict = categories.product_dict.get(category_name)
    if pdict:
      # for all fields
      for k, field_type in pdict.iteritems():
        # see if there is a value in the given params for that field.
        # if there is, get the field type, create the field, and append to the
        # document field list.
        if k in params:
          v = params[k]
          if field_type == search.NumberField:
            try:
              val = float(v)
              fields.append(search.NumberField(name=k, value=val))
            except ValueError:
              error_message = ('bad value %s for field %s of type %s' %
                               (k, v, field_type))
              logging.error(error_message)
              raise errors.OperationFailedError(error_message)
          elif field_type == search.TextField:
            fields.append(search.TextField(name=k, value=str(v)))
          else:
            # you may want to add handling of other field types for generality.
            # Not needed for our current sample data.
            logging.warn('not processed: %s, %s, of type %s', k, v, field_type)
        else:
          error_message = ('value not given for field "%s" of field type "%s"'
                           % (k, field_type))
          logging.warn(error_message)
          raise errors.OperationFailedError(error_message)
    else:
      # else, did not have an entry in the params dict for the given field.
      logging.warn(
          'product field information not found for category name %s',
          params['category_name'])
    return fields

  @classmethod
  def _createDocument(
      cls, pid=None, category=None, name=None, description=None,
      category_name=None, price=None, **params):
    """Create a Document object from given params."""
    # check for the fields that are always required.
    if pid and category and name:
      # First, check that the given pid has only visible ascii characters,
      # and does not contain whitespace.  The pid will be used as the doc_id,
      # which has these requirements.
      if not cls.isValidDocId(pid):
        raise errors.OperationFailedError("Illegal pid %s" % pid)
      # construct the document fields from the params
      resfields = cls._buildProductFields(
          pid=pid, category=category, name=name,
          description=description,
          category_name=category_name, price=price, **params)
      # build and index the document.  Use the pid (product id) as the doc id.
      # (If we did not do this, and left the doc_id unspecified, an id would be
      # auto-generated.)
      d = search.Document(doc_id=pid, fields=resfields)
      return d
    else:
      raise errors.OperationFailedError('Missing parameter.')

  @classmethod
  def _normalizeParams(cls, params):
    """Normalize the submitted params for building a product."""

    params = copy.deepcopy(params)
    try:
      params['pid'] = params['pid'].strip()
      params['name'] = params['name'].strip()
      params['category_name'] = params['category']
      params['category'] = params['category']
      try:
        params['price'] = float(params['price'])
      except ValueError:
        error_message = 'bad price value: %s' % params['price']
        logging.error(error_message)
        raise errors.OperationFailedError(error_message)
      return params
    except KeyError as e1:
      logging.exception("key error")
      raise errors.OperationFailedError(e1)
    except errors.Error as e2:
      logging.debug(
          'Problem with params: %s: %s' % (params, e2.error_message))
      raise errors.OperationFailedError(e2.error_message)

  @classmethod
  def buildProductBatch(cls, rows):
    """Build product documents and their related datastore entities, in batch,
    given a list of params dicts.  Should be used for new products, as does not
    handle updates of existing product entities. This method does not require
    that the doc ids be tied to the product ids, and obtains the doc ids from
    the results of the document add."""

    docs = []
    dbps = []
    for row in rows:
      try:
        params = cls._normalizeParams(row)
        doc = cls._createDocument(**params)
        docs.append(doc)
        # create product entity, sans doc_id
        dbp = models.Product(
            id=params['pid'], price=params['price'],
            category=params['category'])
        dbps.append(dbp)
      except errors.OperationFailedError:
        logging.error('error creating document from data: %s', row)
    try:
      add_results = cls.add(docs)
    except search.Error:
      logging.exception('Add failed')
      return
    if len(add_results) != len(dbps):
      # this case should not be reached; if there was an issue,
      # search.Error should have been thrown, above.
      raise errors.OperationFailedError(
          'Error: wrong number of results returned from indexing operation')
    # now set the entities with the doc ids, the list of which are returned in
    # the same order as the list of docs given to the indexers
    for i, dbp in enumerate(dbps):
      dbp.doc_id = add_results[i].id
    # persist the entities
    ndb.put_multi(dbps)

  @classmethod
  def buildProduct(cls, params):
    """Create/update a product document and its related datastore entity.  The
    product id and the field values are taken from the params dict.
    """
    params = cls._normalizeParams(params)
    # check to see if doc already exists.  We do this because we need to retain
    # some information from the existing doc.  We could skip the fetch if this
    # were not the case.
    curr_doc = cls.getDocFromPid(params['pid'])
    d = cls._createDocument(**params)
    if curr_doc:  #  retain ratings info from existing doc
      avg_rating = cls(curr_doc).getAvgRating()
      cls(d).setAvgRating(avg_rating)

    # This will reindex if a doc with that doc id already exists
    doc_ids = cls.add(d)
    try:
      doc_id = doc_ids[0].id
    except IndexError:
      doc_id = None
      raise errors.OperationFailedError('could not index document')
    logging.debug('got new doc id %s for product: %s', doc_id, params['pid'])

    # now update the entity
    def _tx():
      # Check whether the product entity exists. If so, we want to update
      # from the params, but preserve its ratings-related info.
      prod = models.Product.get_by_id(params['pid'])
      if prod:  #update
        prod.update_core(params, doc_id)
      else:   # create new entity
        prod = models.Product.create(params, doc_id)
      prod.put()
      return prod
    prod = ndb.transaction(_tx)
    logging.debug('prod: %s', prod)
    return prod

########NEW FILE########
__FILENAME__ = errors
#!/usr/bin/env python
#
# Copyright 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Contains the application errors."""


class Error(Exception):
  """Base error type."""

  def __init__(self, error_message):
    self.error_message = error_message


class NotFoundError(Error):
  """Raised when necessary entities are missing."""


class OperationFailedError(Error):
  """Raised when necessary operation has failed."""


########NEW FILE########
__FILENAME__ = handlers
#!/usr/bin/env python
#
# Copyright 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Contains the non-admin ('user-facing') request handlers for the app."""


import logging
import time
import traceback
import urllib
import wsgiref

from base_handler import BaseHandler
import config
import docs
import models
import utils

from google.appengine.api import search
from google.appengine.api import users
from google.appengine.ext.deferred import defer
from google.appengine.ext import ndb


class IndexHandler(BaseHandler):
  """Displays the 'home' page."""

  def get(self):
    cat_info = models.Category.getCategoryInfo()
    sort_info = docs.Product.getSortMenu()
    template_values = {
        'cat_info': cat_info,
        'sort_info': sort_info,
        }
    self.render_template('index.html', template_values)


class ShowProductHandler(BaseHandler):
  """Display product details."""

  def parseParams(self):
    """Filter the param set to the expected params."""
    # The dict can be modified to add any defined defaults.

    params = {
        'pid': '',
        'pname': '',
        'comment': '',
        'rating': '',
        'category': ''
    }
    for k, v in params.iteritems():
      # Possibly replace default values.
      params[k] = self.request.get(k, v)
    return params

  def get(self):
    """Do a document search for the given product id,
    and display the retrieved document fields."""

    params = self.parseParams()

    pid = params['pid']
    if not pid:
      # we should not reach this
      msg = 'Error: do not have product id.'
      url = '/'
      linktext = 'Go to product search page.'
      self.render_template(
          'notification.html',
          {'title': 'Error', 'msg': msg,
           'goto_url': url, 'linktext': linktext})
      return
    doc = docs.Product.getDocFromPid(pid)
    if not doc:
      error_message = ('Document not found for pid %s.' % pid)
      return self.abort(404, error_message)
      logging.error(error_message)
    pdoc = docs.Product(doc)
    pname = pdoc.getName()
    app_url = wsgiref.util.application_uri(self.request.environ)
    rlink = '/reviews?' + urllib.urlencode({'pid': pid, 'pname': pname})
    template_values = {
        'app_url': app_url,
        'pid': pid,
        'pname': pname,
        'review_link': rlink,
        'comment': params['comment'],
        'rating': params['rating'],
        'category': pdoc.getCategory(),
        'prod_doc': doc,
        # for this demo, 'admin' status simply equates to being logged in
        'user_is_admin': users.get_current_user()}
    self.render_template('product.html', template_values)


class CreateReviewHandler(BaseHandler):
  """Process the submission of a new review."""

  def parseParams(self):
    """Filter the param set to the expected params."""

    params = {
        'pid': '',
        'pname': '',
        'comment': 'this is a great product',
        'rating': '5',
        'category': ''
    }
    for k, v in params.iteritems():
      # Possibly replace default values.
      params[k] = self.request.get(k, v)
    return params

  def post(self):
    """Create a new review entity from the submitted information."""
    self.createReview(self.parseParams())

  def createReview(self, params):
    """Create a new review entity from the information in the params dict."""

    author = users.get_current_user()
    comment = params['comment']
    pid = params['pid']
    pname = params['pname']
    if not pid:
      msg = 'Could not get pid; aborting creation of review.'
      logging.error(msg)
      url = '/'
      linktext = 'Go to product search page.'
      self.render_template(
          'notification.html',
          {'title': 'Error', 'msg': msg,
           'goto_url': url, 'linktext': linktext})
      return
    if not comment:
      logging.info('comment not provided')
      self.redirect('/product?' + urllib.urlencode(params))
      return
    rstring = params['rating']
    # confirm that the rating is an int in the allowed range.
    try:
      rating = int(rstring)
      if rating < config.RATING_MIN or rating > config.RATING_MAX:
        logging.warn('Rating %s out of allowed range', rating)
        params['rating'] = ''
        self.redirect('/product?' + urllib.urlencode(params))
        return
    except ValueError:
      logging.error('bad rating: %s', rstring)
      params['rating'] = ''
      self.redirect('/product?' + urllib.urlencode(params))
      return
    review = self.createAndAddReview(pid, author, rating, comment)
    prod_url = '/product?' + urllib.urlencode({'pid': pid, 'pname': pname})
    if not review:
      msg = 'Error creating review.'
      logging.error(msg)
      self.render_template(
          'notification.html',
          {'title': 'Error', 'msg': msg,
           'goto_url': prod_url, 'linktext': 'Back to product.'})
      return
    rparams = {'prod_url': prod_url, 'pname': pname, 'review': review}
    self.render_template('review.html', rparams)

  def createAndAddReview(self, pid, user, rating, comment):
    """Given review information, create the new review entity, pointing via key
    to the associated 'parent' product entity.  """

    # get the account info of the user submitting the review. If the
    # client is not logged in (which is okay), just make them 'anonymous'.
    if user:
      username = user.nickname().split('@')[0]
    else:
      username = 'anonymous'

    prod = models.Product.get_by_id(pid)
    if not prod:
      error_message = 'could not get product for pid %s' % pid
      logging.error(error_message)
      return self.abort(404, error_message)

    rid = models.Review.allocate_ids(size=1)[0]
    key = ndb.Key(models.Review._get_kind(), rid)

    def _tx():
      review = models.Review(
          key=key,
          product_key=prod.key,
          username=username, rating=rating,
          comment=comment)
      review.put()
      # in a transactional task, update the parent product's average
      # rating to include this review's rating, and flag the review as
      # processed.
      defer(utils.updateAverageRating, key, _transactional=True)
      return review
    return ndb.transaction(_tx)


class ProductSearchHandler(BaseHandler):
  """The handler for doing a product search."""

  _DEFAULT_DOC_LIMIT = 3  #default number of search results to display per page.
  _OFFSET_LIMIT = 1000

  def parseParams(self):
    """Filter the param set to the expected params."""
    params = {
        'qtype': '',
        'query': '',
        'category': '',
        'sort': '',
        'rating': '',
        'offset': '0'
    }
    for k, v in params.iteritems():
      # Possibly replace default values.
      params[k] = self.request.get(k, v)
    return params

  def post(self):
    params = self.parseParams()
    self.redirect('/psearch?' + urllib.urlencode(
        dict([k, v.encode('utf-8')] for k, v in params.items())))

  def _getDocLimit(self):
    """if the doc limit is not set in the config file, use the default."""
    doc_limit = self._DEFAULT_DOC_LIMIT
    try:
      doc_limit = int(config.DOC_LIMIT)
    except ValueError:
      logging.error('DOC_LIMIT not properly set in config file; using default.')
    return doc_limit

  def get(self):
    """Handle a product search request."""

    params = self.parseParams()
    self.doProductSearch(params)

  def doProductSearch(self, params):
    """Perform a product search and display the results."""

    # the defined product categories
    cat_info = models.Category.getCategoryInfo()
    # the product fields that we can sort on from the UI, and their mappings to
    # search.SortExpression parameters
    sort_info = docs.Product.getSortMenu()
    sort_dict = docs.Product.getSortDict()
    query = params.get('query', '')
    user_query = query
    doc_limit = self._getDocLimit()

    categoryq = params.get('category')
    if categoryq:
      # add specification of the category to the query
      # Because the category field is atomic, put the category string
      # in quotes for the search.
      query += ' %s:"%s"' % (docs.Product.CATEGORY, categoryq)

    sortq = params.get('sort')
    try:
      offsetval = int(params.get('offset', 0))
    except ValueError:
      offsetval = 0

    # Check to see if the query parameters include a ratings filter, and
    # add that to the final query string if so.  At the same time, generate
    # 'ratings bucket' counts and links-- based on the query prior to addition
    # of the ratings filter-- for sidebar display.
    query, rlinks = self._generateRatingsInfo(
        params, query, user_query, sortq, categoryq)
    logging.debug('query: %s', query.strip())

    try:
      # build the query and perform the search
      search_query = self._buildQuery(
          query, sortq, sort_dict, doc_limit, offsetval)
      search_results = docs.Product.getIndex().search(search_query)
      returned_count = len(search_results.results)

    except search.Error:
      logging.exception("Search error:")  # log the exception stack trace
      msg = 'There was a search error (see logs).'
      url = '/'
      linktext = 'Go to product search page.'
      self.render_template(
          'notification.html',
          {'title': 'Error', 'msg': msg,
           'goto_url': url, 'linktext': linktext})
      return

    # cat_name = models.Category.getCategoryName(categoryq)
    psearch_response = []
    # For each document returned from the search
    for doc in search_results:
      # logging.info("doc: %s ", doc)
      pdoc = docs.Product(doc)
      # use the description field as the default description snippet, since
      # snippeting is not supported on the dev app server.
      description_snippet = pdoc.getDescription()
      price = pdoc.getPrice()
      # on the dev app server, the doc.expressions property won't be populated.
      for expr in doc.expressions:
        if expr.name == docs.Product.DESCRIPTION:
          description_snippet = expr.value
        # uncomment to use 'adjusted price', which should be
        # defined in returned_expressions in _buildQuery() below, as the
        # displayed price.
        # elif expr.name == 'adjusted_price':
          # price = expr.value

      # get field information from the returned doc
      pid = pdoc.getPID()
      cat = catname = pdoc.getCategory()
      pname = pdoc.getName()
      avg_rating = pdoc.getAvgRating()
      # for this result, generate a result array of selected doc fields, to
      # pass to the template renderer
      psearch_response.append(
          [doc, urllib.quote_plus(pid), cat,
           description_snippet, price, pname, catname, avg_rating])
    if not query:
      print_query = 'All'
    else:
      print_query = query

    # Build the next/previous pagination links for the result set.
    (prev_link, next_link) = self._generatePaginationLinks(
        offsetval, returned_count,
        search_results.number_found, params)

    logging.debug('returned_count: %s', returned_count)
    # construct the template values
    template_values = {
        'base_pquery': user_query, 'next_link': next_link,
        'prev_link': prev_link, 'qtype': 'product',
        'query': query, 'print_query': print_query,
        'pcategory': categoryq, 'sort_order': sortq, 'category_name': categoryq,
        'first_res': offsetval + 1, 'last_res': offsetval + returned_count,
        'returned_count': returned_count,
        'number_found': search_results.number_found,
        'search_response': psearch_response,
        'cat_info': cat_info, 'sort_info': sort_info,
        'ratings_links': rlinks}
    # render the result page.
    self.render_template('index.html', template_values)

  def _buildQuery(self, query, sortq, sort_dict, doc_limit, offsetval):
    """Build and return a search query object."""

    # computed and returned fields examples.  Their use is not required
    # for the application to function correctly.
    computed_expr = search.FieldExpression(name='adjusted_price',
        expression='price * 1.08')
    returned_fields = [docs.Product.PID, docs.Product.DESCRIPTION,
                docs.Product.CATEGORY, docs.Product.AVG_RATING,
                docs.Product.PRICE, docs.Product.PRODUCT_NAME]

    if sortq == 'relevance':
      # If sorting on 'relevance', use the Match scorer.
      sortopts = search.SortOptions(match_scorer=search.MatchScorer())
      search_query = search.Query(
          query_string=query.strip(),
          options=search.QueryOptions(
              limit=doc_limit,
              offset=offsetval,
              sort_options=sortopts,
              snippeted_fields=[docs.Product.DESCRIPTION],
              returned_expressions=[computed_expr],
              returned_fields=returned_fields
              ))
    else:
      # Otherwise (not sorting on relevance), use the selected field as the
      # first dimension of the sort expression, and the average rating as the
      # second dimension, unless we're sorting on rating, in which case price
      # is the second sort dimension.
      # We get the sort direction and default from the 'sort_dict' var.
      if sortq == docs.Product.AVG_RATING:
        expr_list = [sort_dict.get(sortq), sort_dict.get(docs.Product.PRICE)]
      else:
        expr_list = [sort_dict.get(sortq), sort_dict.get(
              docs.Product.AVG_RATING)]
      sortopts = search.SortOptions(expressions=expr_list)
      # logging.info("sortopts: %s", sortopts)
      search_query = search.Query(
          query_string=query.strip(),
          options=search.QueryOptions(
              limit=doc_limit,
              offset=offsetval,
              sort_options=sortopts,
              snippeted_fields=[docs.Product.DESCRIPTION],
              returned_expressions=[computed_expr],
              returned_fields=returned_fields
              ))
    return search_query

  def _generateRatingsInfo(
      self, params, query, user_query, sort, category):
    """Add a ratings filter to the query as necessary, and build the
    sidebar ratings buckets content."""

    orig_query = query
    try:
      n = int(params.get('rating', 0))
      # check that rating is not out of range
      if n < config.RATING_MIN or n > config.RATING_MAX:
        n = None
    except ValueError:
      n = None
    if n:
      if n < config.RATING_MAX:
        query += ' %s >= %s %s < %s' % (docs.Product.AVG_RATING, n,
                                        docs.Product.AVG_RATING, n+1)
      else:  # max rating
        query += ' %s:%s' % (docs.Product.AVG_RATING, n)
    query_info = {'query': user_query.encode('utf-8'), 'sort': sort,
             'category': category}
    rlinks = docs.Product.generateRatingsLinks(orig_query, query_info)
    return (query, rlinks)

  def _generatePaginationLinks(
        self, offsetval, returned_count, number_found, params):
    """Generate the next/prev pagination links for the query.  Detect when we're
    out of results in a given direction and don't generate the link in that
    case."""

    doc_limit = self._getDocLimit()
    pcopy = params.copy()
    if offsetval - doc_limit >= 0:
      pcopy['offset'] = offsetval - doc_limit
      prev_link = '/psearch?' + urllib.urlencode(pcopy)
    else:
      prev_link = None
    if ((offsetval + doc_limit <= self._OFFSET_LIMIT)
        and (returned_count == doc_limit)
        and (offsetval + returned_count < number_found)):
      pcopy['offset'] = offsetval + doc_limit
      next_link = '/psearch?' + urllib.urlencode(pcopy)
    else:
      next_link = None
    return (prev_link, next_link)


class ShowReviewsHandler(BaseHandler):
  """Show the reviews for a given product.  This information is pulled from the
  datastore Review entities."""

  def get(self):
    """Show a list of reviews for the product indicated by the 'pid' request
    parameter."""

    pid = self.request.get('pid')
    pname = self.request.get('pname')
    if pid:
      # find the product entity corresponding to that pid
      prod = models.Product.get_by_id(pid)
      if prod:
        avg_rating = prod.avg_rating  # get the product's average rating, over
            # all its reviews
        # get the list of review entities for the product
        reviews = prod.reviews()
        logging.debug('reviews: %s', reviews)
      else:
        error_message = 'could not get product for pid %s' % pid
        logging.error(error_message)
        return self.abort(404, error_message)
      rlist = [[r.username, r.rating, str(r.comment)] for r in reviews]

      # build a template dict with the review and product information
      prod_url = '/product?' + urllib.urlencode({'pid': pid, 'pname': pname})
      template_values = {
          'rlist': rlist,
          'prod_url': prod_url,
          'pname': pname,
          'avg_rating': avg_rating}
      # render the template.
      self.render_template('reviews.html', template_values)

class StoreLocationHandler(BaseHandler):
  """Show the reviews for a given product.  This information is pulled from the
  datastore Review entities."""

  def get(self):
    """Show a list of reviews for the product indicated by the 'pid' request
    parameter."""

    query = self.request.get('location_query')
    lat = self.request.get('latitude')
    lon = self.request.get('longitude')
    # the location query from the client will have this form:
    # distance(store_location, geopoint(37.7899528, -122.3908226)) < 40000
    # logging.info('location query: %s, lat %s, lon %s', query, lat, lon)
    try:
      index = search.Index(config.STORE_INDEX_NAME)
      # search using simply the query string:
      # results = index.search(query)
      # alternately: sort results by distance
      loc_expr = 'distance(store_location, geopoint(%s, %s))' % (lat, lon)
      sortexpr = search.SortExpression(
            expression=loc_expr,
            direction=search.SortExpression.ASCENDING, default_value=0)
      sortopts = search.SortOptions(expressions=[sortexpr])
      search_query = search.Query(
          query_string=query.strip(),
          options=search.QueryOptions(
              sort_options=sortopts,
              ))
      results = index.search(search_query)
    except search.Error:
      logging.exception("There was a search error:")
      self.render_json([])
      return
    # logging.info("geo search results: %s", results)
    response_obj2 = []
    for res in results:
      gdoc = docs.Store(res)
      geopoint = gdoc.getFieldVal(gdoc.STORE_LOCATION)
      resp = {'addr': gdoc.getFieldVal(gdoc.STORE_ADDRESS),
              'storename': gdoc.getFieldVal(gdoc.STORE_NAME),
              'lat': geopoint.latitude, 'lon': geopoint.longitude}
      response_obj2.append(resp)
    logging.info("resp: %s", response_obj2)
    self.render_json(response_obj2)

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
#
# Copyright 2011 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Defines the routing for the app's non-admin handlers.
"""


from handlers import *
import webapp2

application = webapp2.WSGIApplication(
    [('/', IndexHandler),
     ('/psearch', ProductSearchHandler),
     ('/product', ShowProductHandler),
     ('/reviews', ShowReviewsHandler),
     ('/create_review', CreateReviewHandler),
     ('/get_store_locations', StoreLocationHandler)
    ],
    debug=True)



########NEW FILE########
__FILENAME__ = models
#!/usr/bin/env python
#
# Copyright 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" Contains the Datastore model classes used by the app: Category, Product,
and Review.
Each Product entity will have a corresponding indexed "product" search.Document.
Product entities contain a subset of the fields in their corresponding document.
Product Review entities are not indexed (do not have corresponding Documents).
Reviews include a product id field, pointing to their 'parent' product, but
are not part of the same entity group, thus avoiding contention in
scenarios where a large number of product reviews might be edited/added at once.
"""

import logging

import categories
import docs

from google.appengine.api import memcache
from google.appengine.ext import ndb


class Category(ndb.Model):
  """The model class for product category information.  Supports building a
  category tree."""

  _CATEGORY_INFO = None
  _CATEGORY_DICT = None
  _RCATEGORY_DICT = None
  _ROOT = 'root'  # the 'root' category of the category tree

  parent_category = ndb.KeyProperty()

  @property
  def category_name(self):
    return self.key.id()

  @classmethod
  def buildAllCategories(cls):
    """ build the category instances from the provided static data, if category
    entities do not already exist in the Datastore. (see categories.py)."""

    # Don't build if there are any categories in the datastore already
    if cls.query().get():
      return
    root_category = categories.ctree
    cls.buildCategory(root_category, None)

  @classmethod
  def buildCategory(cls, category_data, parent_key):
    """build a category and any children from the given data dict."""

    if not category_data:
      return
    cname = category_data.get('name')
    if not cname:
      logging.warn('no category name for %s', category)
      return
    if parent_key:
      cat = cls(id=cname, parent_category=parent_key)
    else:
      cat = cls(id=cname)
    cat.put()

    children = category_data.get('children')
    # if there are any children, build them using their parent key
    cls.buildChildCategories(children, cat.key)

  @classmethod
  def buildChildCategories(cls, children, parent_key):
    """Given a list of category data structures and a parent key, build the
    child categories, with the given key as their entity group parent."""
    for cat in children:
      cls.buildCategory(cat, parent_key)

  @classmethod
  def getCategoryInfo(cls):
    """Build and cache a list of category id/name correspondences.  This info is
    used to populate html select menus."""
    if not cls._CATEGORY_INFO:
      cls.buildAllCategories()  #first build categories from data file
          # if required
      cats = cls.query().fetch()
      cls._CATEGORY_INFO = [(c.key.id(), c.key.id()) for c in cats
            if c.key.id() != cls._ROOT]
    return cls._CATEGORY_INFO

class Product(ndb.Model):
  """Model for Product data. A Product entity will be built for each product,
  and have an associated search.Document. The product entity does not include
  all of the fields in its corresponding indexed product document, only 'core'
  fields."""

  doc_id = ndb.StringProperty()  # the id of the associated document
  price = ndb.FloatProperty()
  category = ndb.StringProperty()
  # average rating of the product over all its reviews
  avg_rating = ndb.FloatProperty(default=0)
  # the number of reviews of that product
  num_reviews = ndb.IntegerProperty(default=0)
  active = ndb.BooleanProperty(default=True)
  # indicates whether the associated document needs to be re-indexed due to a
  # change in the average review rating.
  needs_review_reindex = ndb.BooleanProperty(default=False)

  @property
  def pid(self):
    return self.key.id()

  def reviews(self):
    """Retrieve all the (active) associated reviews for this product, via the
    reviews' product_key field."""
    return Review.query(
        Review.active == True,
        Review.rating_added == True,
        Review.product_key == self.key).fetch()

  @classmethod
  def updateProdDocsWithNewRating(cls, pkeys):
    """Given a list of product entity keys, check each entity to see if it is
    marked as needing a document re-index.  This flag is set when a new review
    is created for that product, and config.BATCH_RATINGS_UPDATE = True.
    Generate the modified docs as needed and batch re-index them."""

    doclist = []

    def _tx(pid):
      prod = cls.get_by_id(pid)
      if prod and prod.needs_review_reindex:

        # update the associated document with the new ratings info
        # and reindex
        modified_doc = docs.Product.updateRatingInDoc(
            prod.doc_id, prod.avg_rating)
        if modified_doc:
          doclist.append(modified_doc)
        prod.needs_review_reindex = False
        prod.put()
    for pkey in pkeys:
      ndb.transaction(lambda: _tx(pkey.id()))
    # reindex all modified docs in batch
    docs.Product.add(doclist)

  @classmethod
  def create(cls, params, doc_id):
    """Create a new product entity from a subset of the given params dict
    values, and the given doc_id."""
    prod = cls(
        id=params['pid'], price=params['price'],
        category=params['category'], doc_id=doc_id)
    prod.put()
    return prod

  def update_core(self, params, doc_id):
    """Update 'core' values from the given params dict and doc_id."""
    self.populate(
        price=params['price'], category=params['category'],
        doc_id=doc_id)

  @classmethod
  def updateProdDocWithNewRating(cls, pid):
    """Given the id of a product entity, see if it is marked as needing
    a document re-index.  This flag is set when a new review is created for
    that product.  If it needs a re-index, call the document method."""

    def _tx():
      prod = cls.get_by_id(pid)
      if prod and prod.needs_review_reindex:
        prod.needs_review_reindex = False
        prod.put()
      return (prod.doc_id, prod.avg_rating)
    (doc_id, avg_rating) = ndb.transaction(_tx)
    # update the associated document with the new ratings info
    # and reindex
    docs.Product.updateRatingsInfo(doc_id, avg_rating)


class Review(ndb.Model):
  """Model for Review data. Associated with a product entity via the product
  key."""

  doc_id = ndb.StringProperty()
  date_added = ndb.DateTimeProperty(auto_now_add=True)
  product_key = ndb.KeyProperty(kind=Product)
  username = ndb.StringProperty()
  rating = ndb.IntegerProperty()
  active = ndb.BooleanProperty(default=True)
  comment = ndb.TextProperty()
  rating_added = ndb.BooleanProperty(default=False)

  @classmethod
  def deleteReviews(cls, pid):
    """Deletes the reviews associated with a product id."""
    if not pid:
      return
    reviews = cls.query(
        cls.product_key == ndb.Key(Product, pid)).fetch(keys_only=True)
    return ndb.delete_multi(reviews)

########NEW FILE########
__FILENAME__ = sortoptions
#!/usr/bin/env python
#
# Copyright 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import logging

from google.appengine.api import search


def get_sort_options(expressions=None, match_scorer=None, limit=1000):
  """A function to handle the sort expression API differences in 1.6.4
  vs. 1.6.5+.

 An example of usage (NOTE: Do NOT put limit SortExpression or MatchScorer):

  expr_list = [
      search.SortExpression(expression='author', default_value='',
                            direction=search.SortExpression.DESCENDING)]
  sortopts = get_sort_options(expression=expr_list, limit=sort_limit)

  The returned value is used in constructing the query options:

  qoptions=search.QueryOptions(limit=doc_limit, sort_options=sortopts)

  Another example illustrating sorting on an expression based on a
  MatchScorer score:

  expr_list = [
      search.SortExpression(expression='_score + 0.001 * rating',
                            default_value='',
                            direction=search.SortExpression.DESCENDING)]
  sortopts = get_sort_options(expression=expr_list,
                              match_scorer=search.MatchScorer(),
                              limit=sort_limit)


  Args:
    expression: a list of search.SortExpression. Do not set limit parameter on
      SortExpression
    match_scorer: a search.MatchScorer or search.RescoringMatchScorer. Do not
      set limit parameter on either scorer
    limit: the scoring limit

  Returns: the sort options value, either list of SortOption (1.6.4) or
  SortOptions (1.6.5), to set the sort_options field in the QueryOptions object.
  """
  try:
    # using 1.6.5 or greater
    if search.SortOptions:
      logging.debug("search.SortOptions is defined.")
      return search.SortOptions(
          expressions=expressions, match_scorer=match_scorer, limit=limit)

  # SortOptions not available, so using 1.6.4
  except AttributeError:
    logging.debug("search.SortOptions is not defined.")
    expr_list = []
    # copy the sort expressions including the limit info
    if expressions:
      expr_list=[
          search.SortExpression(
              expression=e.expression, direction=e.direction,
              default_value=e.default_value, limit=limit)
          for e in expressions]
    # add the match scorer, if defined, to the expressions list.
    if isinstance(match_scorer, search.MatchScorer):
      expr_list.append(match_scorer.__class__(limit=limit))
    logging.info("sort expressions: %s", expr_list)
    return expr_list

########NEW FILE########
__FILENAME__ = stores
#!/usr/bin/env python
#
# Copyright 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# A set of example retail store locations, specified in terms
# of latitude and longitude.

stores =  [('gosford', 'Gosford', '123 Main St.',
			[-33.4282627126087, 151.341658830643]),
		('sydney','Sydney', '123 Main St.', [-33.873038, 151.20563]),
		('marrickville', 'Marrickville', '123 Main St.',
			[-33.8950341379958, 151.156479120255]),
		('armidale', 'Armidale', '123 Main St.', [-30.51683, 151.648041]),
		('ashfield', 'Ashfield', '123 Main St.', [-33.888424, 151.124329]),
		('bathurst', 'Bathurst', '123 Main St.', [-33.43528, 149.608887]),
		('blacktown', 'Blacktown', '123 Main St.', [-33.771873, 150.908234]),
		('botany', 'Botany Bay', '123 Main St.', [-33.925842, 151.196564]),
		('london', 'London', '123 Main St.', [51.5000,-0.1167]),
		('paris', 'Paris', '123 Main St.', [48.8667,2.3333]),
		('newyork', 'New York', '123 Main St.', [40.7619,-73.9763]),
		('sanfrancisco', 'San Francisco', '123 Main St.', [37.62, -122.38]),
		('tokyo', 'Tokyo', '123 Main St.', [35.6850, 139.7514]),
		('beijing', 'Beijing', '123 Main St.', [39.9289, 116.3883]),
		('newdelhi', 'New Delhi', '123 Main St.', [28.6000, 77.2000]),
		('lawrence', 'Lawrence', '123 Main St.', [39.0393, -95.2087]),
		('baghdad', 'Baghdad', '123 Main St.', [33.3386, 44.3939]),
		('oakland', 'Oakland', '123 Main St.',  [37.73, -122.22]),
		('sancarlos', 'San Carlos', '123 Main St.', [37.52, -122.25]),
		('sanjose', 'San Jose', '123 Main St.', [37.37, -121.92]),
		('hayward', 'Hayward', '123 Main St.', [37.65, -122.12]),
		('monterey', 'Monterey', '123 Main St.', [36.58, -121.85])
		]


########NEW FILE########
__FILENAME__ = run_unittests
#!/usr/bin/env python2.7
#
# Copyright 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import optparse
import os
import sys
import unittest
import logging

USAGE = """%prog SDK_PATH TEST_PATH
Run unit tests for App Engine apps.

SDK_PATH    Path to the SDK installation
TEST_PATH   Path to package containing test modules"""


def main(sdk_path, test_path):
    sys.path.insert(0, sdk_path)
    import dev_appserver
    dev_appserver.fix_sys_path()
    project_dir = os.path.dirname(os.path.dirname(__file__))
    suite = unittest.loader.TestLoader().discover(test_path,
                                                  top_level_dir=project_dir)
    unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == '__main__':
    parser = optparse.OptionParser(USAGE)
    options, args = parser.parse_args()
    if len(args) != 2:
        print 'Error: Exactly 2 arguments required.'
        parser.print_help()
        sys.exit(1)
    sdk_path = args[0]
    test_path = args[1]
    logging.getLogger().setLevel(logging.ERROR)
    main(sdk_path, test_path)

########NEW FILE########
__FILENAME__ = test_errors
#!/usr/bin/env python
#
# Copyright 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" Contains unit tests for exceptions."""

__author__ = 'tmatsuo@google.com (Takashi Matsuo)'


import unittest

import errors


class ErrorTestCase(unittest.TestCase):

  def setUp(self):
    pass

  def tearDown(self):
    pass

  def testException(self):
    error_message = 'It is for test.'
    try:
      raise errors.NotFoundError(error_message)
    except errors.Error as e:
      self.assertEqual(error_message, e.error_message)
    try:
      raise errors.OperationFailedError(error_message)
    except errors.Error as e:
      self.assertEqual(error_message, e.error_message)


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = test_search
#!/usr/bin/env python
#
# Copyright 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" Contains unit tests using search API.
"""

__author__ = 'tmatsuo@google.com (Takashi Matsuo), amyu@google.com (Amy Unruh)'

import os
import shutil
import tempfile
import unittest
import base64
import pickle

from google.appengine.api import apiproxy_stub_map
from google.appengine.api import files
from google.appengine.api import queueinfo
from google.appengine.api import search
from google.appengine.api import users
from google.appengine.api.search import simple_search_stub
from google.appengine.api.taskqueue import taskqueue_stub
from google.appengine.ext import db
from google.appengine.ext import deferred
from google.appengine.ext import testbed
from google.appengine.datastore import datastore_stub_util

import admin_handlers
import config
import docs
import errors
import models
import utils

PRODUCT_PARAMS = dict(
  pid='testproduct',
  name='The adventures of Sherlock Holmes',
  category='books',
  price=2000,
  publisher='Baker Books',
  title='The adventures of Sherlock Holmes',
  pages=200,
  author='Sir Arthur Conan Doyle',
  description='The adventures of Sherlock Holmes',
  isbn='123456')

def _add_mark(v, i):
  if isinstance(v, basestring):
    return '%s %s' % (v, i)
  else:
    return v + i

def create_test_data(n):
  """Create specified number of test data with marks added to its values."""
  ret = []
  for i in xrange(n):
    params = dict()
    for key in PRODUCT_PARAMS.keys():
      if key == 'category':
        # untouched
        params[key] = PRODUCT_PARAMS[key]
      else:
        params[key] = _add_mark(PRODUCT_PARAMS[key], i)
    ret.append(params)
  return ret


class FTSTestCase(unittest.TestCase):

  def setUp(self):
    # First, create an instance of the Testbed class.
    self.testbed = testbed.Testbed()
    # Then activate the testbed, which prepares the service stubs for use.
    self.testbed.activate()
    # Create a consistency policy that will simulate the High
    # Replication consistency model. It's easier to test with
    # probability 1.
    self.policy = \
      datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=1)
    # Initialize the datastore stub with this policy.
    self.testbed.init_datastore_v3_stub(consistency_policy=self.policy)
    self.testbed.init_memcache_stub()
    self.testbed.init_taskqueue_stub()

    # search stub is not available via testbed, so doing this by
    # myself.
    apiproxy_stub_map.apiproxy.RegisterStub(
      'search',
      simple_search_stub.SearchServiceStub())

  def tearDown(self):
    self.testbed.deactivate()

  def testBuildProduct(self):
    models.Category.buildAllCategories()
    self.assertRaises(errors.Error, docs.Product.buildProduct, {})

    product = docs.Product.buildProduct(PRODUCT_PARAMS)

    # make sure that a product entity is stored in Datastore
    self.assert_(product is not None)
    self.assertEqual(product.price, PRODUCT_PARAMS['price'])

    # make sure the search actually works
    sq = search.Query(query_string='Sir Arthur Conan Doyle')
    res = docs.Product.getIndex().search(sq)
    self.assertEqual(res.number_found, 1)
    for doc in res:
      self.assertEqual(doc.doc_id, product.doc_id)

  def testUpdateAverageRatingNonBatch1(self):
    "Test non-batch mode avg ratings updating."
    models.Category.buildAllCategories()
    product = docs.Product.buildProduct(PRODUCT_PARAMS)
    self.assertEqual(product.avg_rating, 0)
    config.BATCH_RATINGS_UPDATE = False

    # Create a review object and invoke updateAverageRating.
    review = models.Review(product_key=product.key,
                           username='bob',
                           rating=4,
                           comment='comment'
                           )
    review.put()
    utils.updateAverageRating(review.key)
    review = models.Review(product_key=product.key,
                           username='bob2',
                           rating=1,
                           comment='comment'
                           )
    review.put()
    utils.updateAverageRating(review.key)

    product = models.Product.get_by_id(product.pid)
    # check that the parent product rating average has been updated based on the
    # two reviews
    self.assertEqual(product.avg_rating, 2.5)
    # with BATCH_RATINGS_UPDATE = False, the product document's average rating
    # field ('ar') should be updated to match its associated product
    # entity.

    # run the task queue tasks
    taskq = self.testbed.get_stub(testbed.TASKQUEUE_SERVICE_NAME)
    tasks = taskq.GetTasks("default")
    taskq.FlushQueue("default")
    while tasks:
      for task in tasks:
        deferred.run(base64.b64decode(task["body"]))
      tasks = taskq.GetTasks("default")
      taskq.FlushQueue("default")

    sq = search.Query(query_string='ar:2.5')
    res = docs.Product.getIndex().search(sq)
    self.assertEqual(res.number_found, 1)
    for doc in res:
      self.assertEqual(doc.doc_id, product.doc_id)

  def testUpdateAverageRatingNonBatch2(self):
    "Check the number of tasks added to the queue when reviews are created."

    models.Category.buildAllCategories()
    product = docs.Product.buildProduct(PRODUCT_PARAMS)
    config.BATCH_RATINGS_UPDATE = False

    # Create a review object and invoke updateAverageRating.
    review = models.Review(product_key=product.key,
                           username='bob',
                           rating=4,
                           comment='comment'
                           )
    review.put()
    utils.updateAverageRating(review.key)
    review = models.Review(product_key=product.key,
                           username='bob2',
                           rating=1,
                           comment='comment'
                           )
    review.put()
    utils.updateAverageRating(review.key)

    # Check the number of tasks in the queue
    taskq = self.testbed.get_stub(testbed.TASKQUEUE_SERVICE_NAME)
    tasks = taskq.GetTasks("default")
    taskq.FlushQueue("default")
    self.assertEqual(len(tasks), 2)

  def testUpdateAverageRatingBatch(self):
    "Test batch mode avg ratings updating."
    models.Category.buildAllCategories()
    product = docs.Product.buildProduct(PRODUCT_PARAMS)
    config.BATCH_RATINGS_UPDATE = True

    # Create a review object and invoke updateAverageRating.
    review = models.Review(product_key=product.key,
                           username='bob',
                           rating=5,
                           comment='comment'
                           )
    review.put()
    utils.updateAverageRating(review.key)

    # there should not be any task queue tasks
    taskq = self.testbed.get_stub(testbed.TASKQUEUE_SERVICE_NAME)
    tasks = taskq.GetTasks("default")
    taskq.FlushQueue("default")
    self.assertEqual(len(tasks), 0)

    # with BATCH_RATINGS_UPDATE = True, the product document's average rating
    # field ('ar') should not yet be updated to match its associated product
    # entity.
    product = models.Product.get_by_id(product.pid)
    sq = search.Query(query_string='ar:5.0')
    res = docs.Product.getIndex().search(sq)
    self.assertEqual(res.number_found, 0)


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
#
# Copyright 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Contains utility functions."""

import logging

import config
import docs
import models

from google.appengine.ext.deferred import defer
from google.appengine.ext import ndb


def intClamp(v, low, high):
  """Clamps a value to the integer range [low, high] (inclusive).

  Args:
    v: Number to be clamped.
    low: Lower bound.
    high: Upper bound.

  Returns:
    An integer closest to v in the range [low, high].
  """
  return max(int(low), min(int(v), int(high)))

def updateAverageRating(review_key):
  """Helper function for updating the average rating of a product when new
  review(s) are added."""

  def _tx():
    review = review_key.get()
    product = review.product_key.get()
    if not review.rating_added:
      review.rating_added = True
      product.num_reviews += 1
      product.avg_rating = (product.avg_rating +
          (review.rating - product.avg_rating)/float(product.num_reviews))
      # signal that we need to reindex the doc with the new ratings info.
      product.needs_review_reindex = True
      ndb.put_multi([product, review])
      # We need to update the ratings associated document at some point as well.
      # If the app is configured to have BATCH_RATINGS_UPDATE set to True, don't
      # do this re-indexing now.  (Instead, all the out-of-date documents can be
      # be later handled in batch -- see cron.yaml).  If BATCH_RATINGS_UPDATE is
      # False, go ahead and reindex now in a transational task.
      if not config.BATCH_RATINGS_UPDATE:
        defer(
            models.Product.updateProdDocWithNewRating,
            product.key.id(), _transactional=True)
    return (product, review)

  try:
    # use an XG transaction in order to update both entities at once
    ndb.transaction(_tx, xg=True)
  except AttributeError:
    # swallow this error and log it; it's not recoverable.
    logging.exception('The function updateAverageRating failed. Either review '
                      + 'or product entity does not exist.')




########NEW FILE########
__FILENAME__ = search_demo
#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.

"""A simple guest book app that demonstrates the App Engine search API."""


from cgi import parse_qs
from datetime import datetime
import os
import string
import urllib
from urlparse import urlparse

import webapp2
from webapp2_extras import jinja2

from google.appengine.api import search
from google.appengine.api import users

_INDEX_NAME = 'greeting'

# _ENCODE_TRANS_TABLE = string.maketrans('-: .@', '_____')

class BaseHandler(webapp2.RequestHandler):
    """The other handlers inherit from this class.  Provides some helper methods
    for rendering a template."""

    @webapp2.cached_property
    def jinja2(self):
      return jinja2.get_jinja2(app=self.app)

    def render_template(self, filename, template_args):
      self.response.write(self.jinja2.render_template(filename, **template_args))


class MainPage(BaseHandler):
    """Handles search requests for comments."""

    def get(self):
        """Handles a get request with a query."""
        uri = urlparse(self.request.uri)
        query = ''
        if uri.query:
            query = parse_qs(uri.query)
            query = query['query'][0]

        # sort results by author descending
        expr_list = [search.SortExpression(
            expression='author', default_value='',
            direction=search.SortExpression.DESCENDING)]
        # construct the sort options
        sort_opts = search.SortOptions(
             expressions=expr_list)
        query_options = search.QueryOptions(
            limit=3,
            sort_options=sort_opts)
        query_obj = search.Query(query_string=query, options=query_options)
        results = search.Index(name=_INDEX_NAME).search(query=query_obj)
        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        template_values = {
            'results': results,
            'number_returned': len(results.results),
            'url': url,
            'url_linktext': url_linktext,
        }
        self.render_template('index.html', template_values)


def CreateDocument(author, content):
    """Creates a search.Document from content written by the author."""
    if author:
        nickname = author.nickname().split('@')[0]
    else:
        nickname = 'anonymous'
    # Let the search service supply the document id.
    return search.Document(
        fields=[search.TextField(name='author', value=nickname),
                search.TextField(name='comment', value=content),
                search.DateField(name='date', value=datetime.now().date())])


class Comment(BaseHandler):
    """Handles requests to index comments."""

    def post(self):
        """Handles a post request."""
        author = None
        if users.get_current_user():
            author = users.get_current_user()

        content = self.request.get('content')
        query = self.request.get('search')
        if content:
            search.Index(name=_INDEX_NAME).put(CreateDocument(author, content))
        if query:
            self.redirect('/?' + urllib.urlencode(
                #{'query': query}))
                {'query': query.encode('utf-8')}))
        else:
            self.redirect('/')


application = webapp2.WSGIApplication(
    [('/', MainPage),
     ('/sign', Comment)],
    debug=True)

########NEW FILE########
