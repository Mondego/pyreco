__FILENAME__ = admin
from __future__ import division
from __future__ import print_function

# -*- coding: utf-8 -*-
# Copyright 2013 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License")
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

__author__ = 'ericbidelman@chromium.org (Eric Bidelman)'


import datetime
import json
import logging
import os
import sys
import webapp2

# Appengine imports.
from google.appengine.api import files
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.ext import blobstore
from google.appengine.ext import db
from google.appengine.ext.webapp import blobstore_handlers

# File imports.
import common
import models
import settings
import uma


# uma.googleplex.com/data/histograms/ids-chrome-histograms.txt
BIGSTORE_BUCKET = '/gs/uma-dashboards/'
BIGSTORE_RESTFUL_URI = 'https://uma-dashboards.storage.googleapis.com/'

CSSPROPERITES_BS_HISTOGRAM_ID = str(0xbfd59b316a6c31f1)
ANIMATIONPROPS_BS_HISTOGRAM_ID = str(0xbee14b73f4fdde73)
FEATURE_OBSERVER_BS_HISTOGRAM_ID = str(0x2e44945129413683)

# For fetching files from the production BigStore during development.
OAUTH2_CREDENTIALS_FILENAME = os.path.join(
    settings.ROOT_DIR, 'scripts', 'oauth2.data')


class YesterdayHandler(blobstore_handlers.BlobstoreDownloadHandler):
  """Loads yesterday's UMA data from BigStore."""

  MODEL_CLASS = {
    CSSPROPERITES_BS_HISTOGRAM_ID: models.StableInstance,
    ANIMATIONPROPS_BS_HISTOGRAM_ID: models.AnimatedProperty,
    FEATURE_OBSERVER_BS_HISTOGRAM_ID: models.FeatureObserver,
  }

  def _SaveData(self, data, yesterday, histogram_id):
    try:
      model_class = self.MODEL_CLASS[histogram_id]
    except Exception, e:
      logging.error('Invalid CSS property bucket id used: %s' % histogram_id)
      return

    # Response format is "bucket-bucket+1=hits".
    # Example: 10-11=2175995,11-12=56635467,12-13=2432539420
    #values_list = data['kTempHistograms'][CSSPROPERITES_BS_HISTOGRAM_ID]['b'].split(',')
    values_list = data['kTempHistograms'][histogram_id]['b'].split(',')

    #sum_total = int(data['kTempHistograms'][CSSPROPERITES_BS_HISTOGRAM_ID]['s']) # TODO: use this.

    # Stores a hit count for each CSS property (properties_dict[bucket] = hits).
    properties_dict = {}

    for val in values_list:
      bucket_range, hits_string = val.split('=') # e.g. "10-11=2175995"

      parts = bucket_range.split('-')

      beginning_range = int(parts[0])
      end_range = int(parts[1])

      # Range > 1 indicates malformed data. Skip it.
      if end_range - beginning_range > 1:
        continue

      # beginning_range is our bucket number; the stable CSSPropertyID.
      properties_dict[beginning_range] = int(hits_string)

    # For CSSPROPERITES_BS_HISTOGRAM_ID, bucket 1 is total pages visited for
    # stank rank histogram. We're guaranteed to have it.
    # For the FEATURE_OBSERVER_BS_HISTOGRAM_ID, the PageVisits bucket_id is 52
    # See uma.py. The actual % is calculated from the count / this number.
    # For ANIMATIONPROPS_BS_HISTOGRAM_ID, we have to calculate the total count.
    if 1 in properties_dict and histogram_id == CSSPROPERITES_BS_HISTOGRAM_ID:
      total_pages = properties_dict.get(1)
    elif (uma.PAGE_VISITS_BUCKET_ID in properties_dict and
          histogram_id == FEATURE_OBSERVER_BS_HISTOGRAM_ID):
      total_pages = properties_dict.get(uma.PAGE_VISITS_BUCKET_ID)

      # Don't include PageVisits results.
      del properties_dict[uma.PAGE_VISITS_BUCKET_ID]
    else:
      total_pages = sum(properties_dict.values())

    for bucket_id, num_hits in properties_dict.items():
      # If the id is not in the map, use 'ERROR' for the name.
      # TODO(ericbidelman): Non-matched bucket ids are likely new properties
      # that have been added and need to be updated in uma.py. Find way to
      # autofix these values with the appropriate property_name later.
      property_map = uma.CSS_PROPERTY_BUCKETS
      if histogram_id == FEATURE_OBSERVER_BS_HISTOGRAM_ID:
        property_map = uma.FEATUREOBSERVER_BUCKETS

      property_name = property_map.get(bucket_id, 'ERROR')

      query = model_class.all()
      query.filter('bucket_id = ', bucket_id)
      query.filter('date =', yesterday)

      # Only add this entity if one doesn't already exist with the same
      # bucket_id and date.
      if query.count() > 0:
        logging.info('Cron data was already fetched for this date')
        continue

      # TODO(ericbidelman): Calculate a rolling average here
      # This will be done using a GQL query to grab information
      # for the past 6 days.
      # We average those past 6 days with the new day's data
      # and store the result in rolling_percentage

      entity = model_class(
          property_name=property_name,
          bucket_id=bucket_id,
          date=yesterday,
          #hits=num_hits,
          #total_pages=total_pages,
          day_percentage=(num_hits * 1.0 / total_pages)
          #rolling_percentage=
          )
      entity.put()

  def get(self):
    """Loads the data file located at |filename|.

    Args:
      filename: The filename for the data file to be loaded.
    """
    yesterday = datetime.date.today() - datetime.timedelta(1)
    yesterday_formatted = yesterday.strftime("%Y.%m.%d")

    filename = 'histograms/daily/%s/Everything' % (yesterday_formatted)

    if settings.PROD:
      try:
        with files.open(BIGSTORE_BUCKET + filename, 'r') as unused_f:
          pass
      except files.file.ExistenceError, e:
        self.response.write(e)
        return

      # The file exists; serve it.
      blob_key = blobstore.create_gs_key(BIGSTORE_BUCKET + filename)
      blob_reader = blobstore.BlobReader(blob_key, buffer_size=3510000)
      try:
        result = blob_reader.read()
      finally:
        blob_reader.close()
    else:
      # From the development server, use the RESTful API to read files from the
      # production BigStore instance, rather than needing to stage them to the
      # local BigStore instance.
      result, response_code = self._FetchFromBigstoreREST(filename)

      if response_code != 200:
        self.error(response_code)
        self.response.out.write(
            ('%s - Error doing BigStore API request. '
             'Try refreshing your OAuth token?' % response_code))
        return

    if result:
      data = json.loads(result)

      for bucket_id in self.MODEL_CLASS.keys():
        self._SaveData(data, yesterday, bucket_id)

  def _FetchFromBigstoreREST(self, filename):
    # Read the OAuth2 access token from disk.
    try:
      with open(OAUTH2_CREDENTIALS_FILENAME, 'r') as f:
        credentials_json = json.load(f)
    except IOError, e:
      logging.error(e)
      return [None, 404]

    # Attempt to fetch the file from the production BigStore instance.
    url = BIGSTORE_RESTFUL_URI + filename

    headers = {
        'x-goog-api-version': '2',
        'Authorization': 'OAuth ' + credentials_json.get('access_token', '')
        }
    result = urlfetch.fetch(url, headers=headers)
    return (result.content, result.status_code)


class FeatureHandler(common.ContentHandler):

  DEFAULT_URL = '/features'
  ADD_NEW_URL = '/admin/features/new'
  EDIT_URL = '/admin/features/edit'
  LAUNCH_URL = '/admin/features/launch'

  INTENT_PARAM = 'intent'
  LAUNCH_PARAM = 'launch'

  def __FullQualifyLink(self, param_name):
    link = self.request.get(param_name) or None
    if link:
      if not link.startswith('http'):
        link = db.Link('http://' + link)
      else:
        link = db.Link(link)
    return link

  def __ToInt(self, param_name):
    param = self.request.get(param_name) or None
    if param:
      param = int(param)
    return param

  def get(self, path, feature_id=None):
    # Remove trailing slash from URL and redirect. e.g. /metrics/ -> /metrics
    if path[-1] == '/':
      return self.redirect(self.request.path.rstrip('/'))

    # TODO(ericbidelman): This creates a additional call to
    # _is_user_whitelisted() (also called in common.py), resulting in another
    # db query.
    if not self._is_user_whitelisted(users.get_current_user()):
      #TODO(ericbidelman): Use render(status=401) instead.
      #self.render(data={}, template_path=os.path.join(path + '.html'), status=401)
      common.handle_401(self.request, self.response, Exception)
      return

    if not feature_id and not 'new' in path:
      # /features/edit|launch -> /features/new
      return self.redirect(self.ADD_NEW_URL)
    elif feature_id and 'new' in path:
      return self.redirect(self.ADD_NEW_URL)

    feature = None

    template_data = {
        'feature_form': models.FeatureForm()
        }

    if feature_id:
      f = models.Feature.get_by_id(long(feature_id))
      if f is None:
        return self.redirect(self.ADD_NEW_URL)

      # Provide new or populated form to template.
      template_data.update({
          'feature': f.format_for_template(),
          'feature_form': models.FeatureForm(f.format_for_edit()),
          'edit_url': '%s://%s%s/%s' % (self.request.scheme, self.request.host,
                                        self.EDIT_URL, feature_id)
          })

    if self.LAUNCH_PARAM in self.request.params:
      template_data[self.LAUNCH_PARAM] = True
    if self.INTENT_PARAM in self.request.params:
      template_data[self.INTENT_PARAM] = True

    self._add_common_template_values(template_data)

    self.render(data=template_data, template_path=os.path.join(path + '.html'))

  def post(self, path, feature_id=None):
    spec_link = self.__FullQualifyLink('spec_link')
    bug_url = self.__FullQualifyLink('bug_url')

    ff_views_link = self.__FullQualifyLink('ff_views_link')
    ie_views_link = self.__FullQualifyLink('ie_views_link')
    safari_views_link = self.__FullQualifyLink('safari_views_link')

    # Cast incoming milestones to ints.
    shipped_milestone = self.__ToInt('shipped_milestone')
    shipped_android_milestone = self.__ToInt('shipped_android_milestone')
    shipped_ios_milestone = self.__ToInt('shipped_ios_milestone')
    shipped_webview_milestone = self.__ToInt('shipped_webview_milestone')
    shipped_opera_milestone = self.__ToInt('shipped_opera_milestone')
    shipped_opera_android_milestone = self.__ToInt('shipped_opera_android_milestone')

    owners = self.request.get('owner') or []
    if owners:
      owners = [db.Email(x.strip()) for x in owners.split(',')]

    doc_links = self.request.get('doc_links') or []
    if doc_links:
      doc_links = [x.strip() for x in doc_links.split(',')]

    sample_links = self.request.get('sample_links') or []
    if sample_links:
      sample_links = [x.strip() for x in sample_links.split(',')]

    redirect_url = self.DEFAULT_URL

    # Update/delete existing feature.
    if feature_id: # /admin/edit/1234
      feature = models.Feature.get_by_id(long(feature_id))
      if feature is None:
        return self.redirect(self.request.path)

      if not 'delete' in path:
        feature.category = int(self.request.get('category'))
        feature.name = self.request.get('name')
        feature.summary = self.request.get('summary')
        feature.owner = owners
        feature.bug_url = bug_url
        feature.impl_status_chrome = int(self.request.get('impl_status_chrome'))
        feature.shipped_milestone = shipped_milestone
        feature.shipped_android_milestone = shipped_android_milestone
        feature.shipped_ios_milestone = shipped_ios_milestone
        feature.shipped_webview_milestone = shipped_webview_milestone
        feature.shipped_opera_milestone = shipped_opera_milestone
        feature.shipped_opera_android_milestone = shipped_opera_android_milestone
        feature.footprint = int(self.request.get('footprint'))
        feature.visibility = int(self.request.get('visibility'))
        feature.ff_views = int(self.request.get('ff_views'))
        feature.ff_views_link = ff_views_link
        feature.ie_views = int(self.request.get('ie_views'))
        feature.ie_views_link = ie_views_link
        feature.safari_views = int(self.request.get('safari_views'))
        feature.safari_views_link = safari_views_link
        feature.prefixed = self.request.get('prefixed') == 'on'
        feature.spec_link = spec_link
        feature.standardization = int(self.request.get('standardization'))
        feature.comments = self.request.get('comments')
        feature.web_dev_views = int(self.request.get('web_dev_views'))
        feature.doc_links = doc_links
        feature.sample_links = sample_links
    else:
      feature = models.Feature(
          category=int(self.request.get('category')),
          name=self.request.get('name'),
          summary=self.request.get('summary'),
          owner=owners,
          bug_url=bug_url,
          impl_status_chrome=int(self.request.get('impl_status_chrome')),
          shipped_milestone=shipped_milestone,
          shipped_android_milestone=shipped_android_milestone,
          shipped_ios_milestone=shipped_ios_milestone,
          shipped_webview_milestone=shipped_webview_milestone,
          shipped_opera_milestone=shipped_opera_milestone,
          shipped_opera_android_milestone=shipped_opera_android_milestone,
          footprint=int(self.request.get('footprint')),
          visibility=int(self.request.get('visibility')),
          ff_views=int(self.request.get('ff_views')),
          ff_views_link=ff_views_link,
          ie_views=int(self.request.get('ie_views')),
          ie_views_link=ie_views_link,
          safari_views=int(self.request.get('safari_views')),
          safari_views_link=safari_views_link,
          prefixed=self.request.get('prefixed') == 'on',
          spec_link=spec_link,
          standardization=int(self.request.get('standardization')),
          comments=self.request.get('comments'),
          web_dev_views=int(self.request.get('web_dev_views')),
          doc_links=doc_links,
          sample_links=sample_links,
          )

    if 'delete' in path:
      feature.delete()
      memcache.flush_all()
      return # Bomb out early for AJAX delete. No need for extra redirect below.
    else:
      key = feature.put()

      # TODO(ericbidelman): enumerate and remove only the relevant keys.
      memcache.flush_all()

      params = []
      if self.request.get('create_launch_bug') == 'on':
        params.append(self.LAUNCH_PARAM)
      if self.request.get('intent_to_implement') == 'on':
        params.append(self.INTENT_PARAM)

      if len(params):
        redirect_url = '%s/%s?%s' % (self.LAUNCH_URL, key.id(),
                                     '&'.join(params))

    return self.redirect(redirect_url)


app = webapp2.WSGIApplication([
  ('/cron/metrics', YesterdayHandler),
  ('/(.*)/([0-9]*)', FeatureHandler),
  ('/(.*)', FeatureHandler),
], debug=settings.DEBUG)


########NEW FILE########
__FILENAME__ = bulkloader_helpers
import datetime

from google.appengine.ext import db
from google.appengine.api import users


def email_to_list():
  def wrapper(value):
    if value == '' or value is None or value == []:
      return None
    return [db.Email(x.strip()) for x in value.split(',')]

  return wrapper

def finalize(input_dict, instance, bulkload_state_copy):
  #print input_dict
  if instance['owner'] is None:
    del instance['owner']
  if instance['created'] is None:
    instance['created'] = datetime.datetime.utcnow()
  if instance['updated'] is None:
    instance['updated'] = datetime.datetime.utcnow()
  if instance['created_by'] is None:
   instance['created_by'] = users.User(email='admin') #users.get_current_user().email()
  if instance['updated_by'] is None:
   instance['updated_by'] = users.User(email='admin') #users.get_current_user().email()
  if instance['summary'] == '' or instance['summary'] is None:
    instance['summary'] = ' '
  return instance

########NEW FILE########
__FILENAME__ = common
# -*- coding: utf-8 -*-
# Copyright 2013 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License")
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

__author__ = 'ericbidelman@chromium.org (Eric Bidelman)'


import datetime
import json
import logging
import webapp2

# App Engine imports.
from google.appengine.api import users

from django.template.loader import render_to_string
from django.utils import feedgenerator

import models
import settings


class BaseHandler(webapp2.RequestHandler):

  def __init__(self, request, response):
    self.initialize(request, response)

    # Add CORS and Chrome Frame to all responses.
    self.response.headers.add_header('Access-Control-Allow-Origin', '*')
    self.response.headers.add_header('X-UA-Compatible', 'IE=Edge,chrome=1')

    # Settings can't be global in python 2.7 env.
    logging.getLogger().setLevel(logging.DEBUG)


class JSONHandler(BaseHandler):

  def get(self, data, formatted=False):
    self.response.headers['Content-Type'] = 'application/json;charset=utf-8'
    if formatted:
      return self.response.write(json.dumps(data, separators=(',',':')))
    else:
      data = [entity.to_dict() for entity in data]
      return self.response.write(json.dumps(data, separators=(',',':')))


class ContentHandler(BaseHandler):

  def _is_user_whitelisted(self, user):
    if not user:
      return False

    is_whitelisted = False

    if users.is_current_user_admin():
      is_whitelisted = True
    elif user.email().endswith('@chromium.org'):
      is_whitelisted = True
    else:
      # TODO(ericbidelman): memcache user lookup.
      query = models.AppUser.all(keys_only=True).filter('email =', user.email())
      found_user = query.get()

      if found_user is not None:
        is_whitelisted = True

    return is_whitelisted

  def _add_common_template_values(self, d):
    """Mixin common values for templates into d."""

    template_data = {
      'prod': settings.PROD,
      'APP_TITLE': settings.APP_TITLE,
      'current_path': self.request.path,
      'VULCANIZE': settings.VULCANIZE
      }

    user = users.get_current_user()
    if user:
      template_data['login'] = (
          'Logout', users.create_logout_url(dest_url=self.request.path))
      template_data['user'] = {
        'is_whitelisted': self._is_user_whitelisted(user),
        'is_admin': users.is_current_user_admin(),
        'email': user.email(),
      }
    else:
      template_data['user'] = None
      template_data['login'] = (
          'Login', users.create_login_url(dest_url=self.request.path))

    d.update(template_data)

  def render(self, data={}, template_path=None, status=None, message=None,
             relpath=None):
    if status is not None and status != 200:
      self.response.set_status(status, message)

    # Add common template data to every request.
    self._add_common_template_values(data)

    try:
      self.response.out.write(render_to_string(template_path, data))
    except Exception:
      handle_404(self.request, self.response, Exception)

  def render_atom_feed(self, title, data):
    prefix = '%s://%s%s' % (self.request.scheme, self.request.host,
                             self.request.path.replace('.xml', ''))

    feed = feedgenerator.Atom1Feed(
        title=unicode('%s - %s' % (settings.APP_TITLE, title)),
        link=prefix,
        description=u'New features exposed to web developers',
        language=u'en'
        )
    for f in data:
      pubdate = datetime.datetime.strptime(str(f['updated'][:19]),
                                           '%Y-%m-%d  %H:%M:%S')
      feed.add_item(
          title=unicode(f['name']),
          link='%s/%s' % (prefix, f.get('id')),
          description=f.get('summary', ''),
          pubdate=pubdate,
          author_name=unicode(settings.APP_TITLE),
          categories=[f['category']]
          )
    self.response.headers.add_header('Content-Type',
      'application/atom+xml;charset=utf-8')
    self.response.out.write(feed.writeString('utf-8'))


def handle_401(request, response, exception):
  ERROR_401 = (
    '<title>401 Unauthorized</title>\n'
    '<h1>Error: Unauthorized</h1>\n'
    '<h2>User does not have permission to view this page.</h2>')
  response.write(ERROR_401)
  response.set_status(401)

def handle_404(request, response, exception):
  ERROR_404 = (
    '<title>404 Not Found</title>\n'
    '<h1>Error: Not Found</h1>\n'
    '<h2>The requested URL <code>%s</code> was not found on this server.'
    '</h2>' % request.url)
  response.write(ERROR_404)
  response.set_status(404)

def handle_500(request, response, exception):
  logging.exception(exception)
  ERROR_500 = (
    '<title>500 Internal Server Error</title>\n'
    '<h1>Error: 500 Internal Server Error</h1>')
  response.write(ERROR_500)
  response.set_status(500)

########NEW FILE########
__FILENAME__ = include_raw
from django.template import loader
from google.appengine.ext.webapp import template

register = template.create_template_register()

@register.simple_tag
def include_raw(path):
  return loader.find_template(path)[0]
 
########NEW FILE########
__FILENAME__ = verbatim
"""
jQuery templates use constructs like:

    {{if condition}} print something{{/if}}

This, of course, completely screws up Django templates,
because Django thinks {{ and }} mean something.

Wrap {% verbatim %} and {% endverbatim %} around those
blocks of jQuery templates and this will try its best
to output the contents with no changes.
"""

from django import template

register = template.Library()


class VerbatimNode(template.Node):

  def __init__(self, text):
      self.text = text
  
  def render(self, context):
      return self.text


@register.tag
def verbatim(parser, token):
  text = []
  while 1:
      token = parser.tokens.pop(0)
      if token.contents == 'endverbatim':
          break
      if token.token_type == template.TOKEN_VAR:
          text.append('{{')
      elif token.token_type == template.TOKEN_BLOCK:
          text.append('{%')
      text.append(token.contents)
      if token.token_type == template.TOKEN_VAR:
          text.append('}}')
      elif token.token_type == template.TOKEN_BLOCK:
          text.append('%}')
  return VerbatimNode(''.join(text))

########NEW FILE########
__FILENAME__ = metrics
# -*- coding: utf-8 -*-
# Copyright 2013 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License")
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

__author__ = 'ericbidelman@chromium.org (Eric Bidelman)'

import webapp2

from datetime import timedelta
from google.appengine.api import memcache

import common
import models
import settings


CACHE_AGE = 86400 # 24hrs


class TimelineHandler(common.JSONHandler):

  def get(self):
    try:
      bucket_id = int(self.request.get('bucket_id'))
    except:
      return super(self.MODEL_CLASS, self).get([])

    KEY = '%s|%s' % (self.MEMCACHE_KEY, bucket_id)

    data = memcache.get(KEY)
    if data is None:
      query = self.MODEL_CLASS.all()
      query.filter('bucket_id =', bucket_id)
      query.order('date')
      data = query.fetch(None) # All matching results.

      # Remove outliers if percentage is not between 0-1.
      data = filter(lambda x: 0 <= x.day_percentage <= 1, data)

      memcache.set(KEY, data, time=CACHE_AGE)

    super(TimelineHandler, self).get(data)


class PopularityTimelineHandler(TimelineHandler):

  MEMCACHE_KEY = 'css_pop_timeline'
  MODEL_CLASS = models.StableInstance

  def get(self):
    super(PopularityTimelineHandler, self).get()


class AnimatedTimelineHandler(TimelineHandler):

  MEMCACHE_KEY = 'css_animated_timeline'
  MODEL_CLASS = models.AnimatedProperty

  def get(self):
    super(AnimatedTimelineHandler, self).get()


class FeatureObserverTimelineHandler(TimelineHandler):

  MEMCACHE_KEY = 'featureob_timeline'
  MODEL_CLASS = models.FeatureObserver

  def get(self):
    super(FeatureObserverTimelineHandler, self).get()


class FeatureHandler(common.JSONHandler):

  def get(self):
    properties = memcache.get(self.MEMCACHE_KEY)

    if properties is None:
      # Find last date data was fetched by pulling one entry.
      result = self.MODEL_CLASS.all().order('-date').get()

      properties = []

      if result:
        query = self.MODEL_CLASS.all()
        query.filter('date =', result.date)
        query.order('-day_percentage')
        properties = query.fetch(None) # All matching results.

        # Go another day back if if data looks invalid.
        if (properties[0].day_percentage < 0 or
            properties[0].day_percentage > 1):
          query = self.MODEL_CLASS.all()
          query.filter('date =', result.date - timedelta(days=1))
          query.order('-day_percentage')
          properties = query.fetch(None)

        memcache.set(self.MEMCACHE_KEY, properties, time=CACHE_AGE)

    super(FeatureHandler, self).get(properties)


class CSSPopularityHandler(FeatureHandler):

  MEMCACHE_KEY = 'css_popularity'
  MODEL_CLASS = models.StableInstance

  def get(self):
    super(CSSPopularityHandler, self).get()


class CSSAnimatedHandler(FeatureHandler):

  MEMCACHE_KEY = 'css_animated'
  MODEL_CLASS = models.AnimatedProperty

  def get(self):
    super(CSSAnimatedHandler, self).get()


class FeatureObserverPopularityHandler(FeatureHandler):

  MEMCACHE_KEY = 'featureob_popularity'
  MODEL_CLASS = models.FeatureObserver

  def get(self):
    super(FeatureObserverPopularityHandler, self).get()


app = webapp2.WSGIApplication([
  ('/data/timeline/cssanimated', AnimatedTimelineHandler),
  ('/data/timeline/csspopularity', PopularityTimelineHandler),
  ('/data/timeline/featurepopularity', FeatureObserverTimelineHandler),
  ('/data/csspopularity', CSSPopularityHandler),
  ('/data/cssanimated', CSSAnimatedHandler),
  ('/data/featurepopularity', FeatureObserverPopularityHandler),
], debug=settings.DEBUG)

########NEW FILE########
__FILENAME__ = models
import datetime
import logging
import time

from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.ext import db
#from google.appengine.ext.db import djangoforms

#from django.forms import ModelForm
from django import forms

import settings


SIMPLE_TYPES = (int, long, float, bool, dict, basestring, list)

WEBCOMPONENTS = 1
MISC = 2
SECURITY = 3
MULTIMEDIA = 4
DOM = 5
FILE = 6
OFFLINE = 7
DEVICE = 8
COMMUNICATION = 9
JAVASCRIPT = 10
NETWORKING = 11
INPUT = 12
PERFORMANCE = 13
GRAPHICS = 14
CSS = 15

FEATURE_CATEGORIES = {
  CSS: 'CSS',
  WEBCOMPONENTS: 'Web Components',
  MISC: 'Misc',
  SECURITY: 'Security',
  MULTIMEDIA: 'Multimedia',
  DOM: 'DOM',
  FILE: 'File APIs',
  OFFLINE: 'Offline / Storage',
  DEVICE: 'Device',
  COMMUNICATION: 'Realtime / Communication',
  JAVASCRIPT: 'JavaScript',
  NETWORKING: 'Network / Connectivity',
  INPUT: 'User input',
  PERFORMANCE: 'Performance',
  GRAPHICS: 'Graphics',
  }

NO_ACTIVE_DEV = 1
PROPOSED = 2
IN_DEVELOPMENT = 3
BEHIND_A_FLAG = 4
ENABLED_BY_DEFAULT = 5
DEPRECATED = 6
NO_LONGER_PURSUING = 1000 # insure bottom of list

IMPLEMENATION_STATUS = {
  NO_ACTIVE_DEV: 'No active development',
  PROPOSED: 'Proposed',
  IN_DEVELOPMENT: 'In development',
  BEHIND_A_FLAG: 'Behind a flag',
  ENABLED_BY_DEFAULT: 'Enabled by default',
  DEPRECATED: 'Deprecated',
  NO_LONGER_PURSUING: 'No longer pursuing',
  }

MAJOR_NEW_API = 1
MAJOR_MINOR_NEW_API = 2
SUBSTANTIVE_CHANGES = 3
MINOR_EXISTING_CHANGES = 4
EXTREMELY_SMALL_CHANGE = 5

FOOTPRINT_CHOICES = {
  MAJOR_NEW_API: ('A major new independent API (e.g. adding a large # '
                  'independent concepts with many methods/properties/objects)'),
  MAJOR_MINOR_NEW_API: ('Major changes to an existing API OR a minor new '
                        'independent API (e.g. adding a large # of new '
                        'methods/properties or introducing new concepts to '
                        'augment an existing API)'),
  SUBSTANTIVE_CHANGES: ('Substantive changes to an existing API (e.g. small '
                        'number of new methods/properties)'),
  MINOR_EXISTING_CHANGES: (
      'Minor changes to an existing API (e.g. adding a new keyword/allowed '
      'argument to a property/method)'),
  EXTREMELY_SMALL_CHANGE: ('Extremely small tweaks to an existing API (e.g. '
                           'how existing keywords/arguments are interpreted)'),
  }

MAINSTREAM_NEWS = 1
WARRANTS_ARTICLE = 2
IN_LARGER_ARTICLE = 3
SMALL_NUM_DEVS = 4
SUPER_SMALL = 5

VISIBILITY_CHOICES = {
  MAINSTREAM_NEWS: 'Likely in mainstream tech news',
  WARRANTS_ARTICLE: 'Will this feature generate articles on sites like html5rocks.com',
  IN_LARGER_ARTICLE: 'Covered as part of a larger article but not on its own',
  SMALL_NUM_DEVS: 'Only a very small number of web developers will care about',
  SUPER_SMALL: "So small it doesn't need to be covered in this dashboard.",
  }

SHIPPED = 1
IN_DEV = 2
PUBLIC_SUPPORT = 3
MIXED_SIGNALS = 4
NO_PUBLIC_SIGNALS = 5
PUBLIC_SKEPTICISM = 6
OPPOSED = 7

VENDOR_VIEWS = {
  SHIPPED: 'Shipped',
  IN_DEV: 'In development',
  PUBLIC_SUPPORT: 'Public support',
  MIXED_SIGNALS: 'Mixed public signals',
  NO_PUBLIC_SIGNALS: 'No public signals',
  PUBLIC_SKEPTICISM: 'Public skepticism',
  OPPOSED: 'Opposed',
  }

DEFACTO_STD = 1
ESTABLISHED_STD = 2
WORKING_DRAFT = 3
EDITORS_DRAFT = 4
PUBLIC_DISCUSSION = 5
NO_STD_OR_DISCUSSION = 6

STANDARDIZATION = {
  DEFACTO_STD: 'De-facto standard',
  ESTABLISHED_STD: 'Established standard',
  WORKING_DRAFT: 'Working draft or equivalent',
  EDITORS_DRAFT: "Editor's draft",
  PUBLIC_DISCUSSION: 'Public discussion',
  NO_STD_OR_DISCUSSION: 'No public standards discussion',
  }

DEV_STRONG_POSITIVE = 1
DEV_POSITIVE = 2
DEV_MIXED_SIGNALS = 3
DEV_NO_SIGNALS = 4
DEV_NEGATIVE = 5
DEV_STRONG_NEGATIVE = 6

WEB_DEV_VIEWS = {
  DEV_STRONG_POSITIVE: 'Strongly positive',
  DEV_POSITIVE: 'Positive',
  DEV_MIXED_SIGNALS: 'Mixed signals',
  DEV_NO_SIGNALS: 'No signals',
  DEV_NEGATIVE: 'Negative',
  DEV_STRONG_NEGATIVE: 'Strongly negative',
  }


class DictModel(db.Model):
  # def to_dict(self):
  #   return dict([(p, unicode(getattr(self, p))) for p in self.properties()])

  def format_for_template(self):
    return self.to_dict()

  def to_dict(self):
    output = {}

    for key, prop in self.properties().iteritems():
      value = getattr(self, key)

      if value is None or isinstance(value, SIMPLE_TYPES):
        output[key] = value
      elif isinstance(value, datetime.date):
        # Convert date/datetime to ms-since-epoch ("new Date()").
        #ms = time.mktime(value.utctimetuple())
        #ms += getattr(value, 'microseconds', 0) / 1000
        #output[key] = int(ms)
        output[key] = unicode(value)
      elif isinstance(value, db.GeoPt):
        output[key] = {'lat': value.lat, 'lon': value.lon}
      elif isinstance(value, db.Model):
        output[key] = to_dict(value)
      elif isinstance(value, users.User):
        output[key] = value.email()
      else:
        raise ValueError('cannot encode ' + repr(prop))

    return output


# UMA metrics.
class StableInstance(DictModel):
  created = db.DateTimeProperty(auto_now_add=True)
  updated = db.DateTimeProperty(auto_now=True)

  property_name = db.StringProperty(required=True)
  bucket_id = db.IntegerProperty(required=True)
  date = db.DateProperty(verbose_name='When the data was fetched',
                         required=True)
  #hits = db.IntegerProperty(required=True)
  #total_pages = db.IntegerProperty()
  day_percentage = db.FloatProperty()
  rolling_percentage = db.FloatProperty()

class AnimatedProperty(StableInstance):
  pass

class FeatureObserver(StableInstance):
  pass


# Feature dashboard.
class Feature(DictModel):
  """Container for a feature."""

  DEFAULT_MEMCACHE_KEY = '%s|features' % (settings.MEMCACHE_KEY_PREFIX)

  def format_for_template(self):
    d = self.to_dict()
    d['id'] = self.key().id()
    d['category'] = FEATURE_CATEGORIES[self.category]
    d['visibility'] = VISIBILITY_CHOICES[self.visibility]
    d['impl_status_chrome'] = IMPLEMENATION_STATUS[self.impl_status_chrome]
    d['meta'] = {
      'needsflag': self.impl_status_chrome == BEHIND_A_FLAG,
      'milestone_str': self.shipped_milestone or d['impl_status_chrome']
      }
    d['ff_views'] = {'value': self.ff_views,
                     'text': VENDOR_VIEWS[self.ff_views]}
    d['ie_views'] = {'value': self.ie_views,
                     'text': VENDOR_VIEWS[self.ie_views]}
    d['safari_views'] = {'value': self.safari_views,
                         'text': VENDOR_VIEWS[self.safari_views]}
    d['standardization'] = {'value': self.standardization,
                            'text': STANDARDIZATION[self.standardization]}
    d['web_dev_views'] = {'value': self.web_dev_views,
                          'text': WEB_DEV_VIEWS[self.web_dev_views]}
    #d['owner'] = ', '.join(self.owner)
    return d

  def format_for_edit(self):
    d = self.to_dict()
    #d['id'] = self.key().id
    d['owner'] = ', '.join(self.owner)
    d['doc_links'] = ', '.join(self.doc_links)
    d['sample_links'] = ', '.join(self.sample_links)
    return d

  @classmethod
  def get_all(self, limit=None, order='-updated', filterby=None,
              update_cache=False):
    KEY = '%s|%s|%s' % (Feature.DEFAULT_MEMCACHE_KEY, order, limit)

    # TODO(ericbidelman): Support more than one filter.
    if filterby is not None:
      s = ('%s%s' % (filterby[0], filterby[1])).replace(' ', '')
      KEY += '|%s' % s

    feature_list = memcache.get(KEY)

    if feature_list is None or update_cache:
      query = Feature.all().order(order) #.order('name')

      # TODO(ericbidelman): Support more than one filter.
      if filterby:
        query.filter(filterby[0], filterby[1])

      features = query.fetch(limit)

      feature_list = [f.format_for_template() for f in features]

      memcache.set(KEY, feature_list)

    return feature_list

  @classmethod
  def get_chronological(limit=None, update_cache=False):
    KEY = '%s|%s|%s' % (Feature.DEFAULT_MEMCACHE_KEY, 'cronorder', limit)

    feature_list = memcache.get(KEY)

    if feature_list is None or update_cache:
      q = Feature.all()
      q.order('-shipped_milestone')
      q.order('name')
      features = q.fetch(None)

      features = [f for f in features if (IN_DEVELOPMENT < f.impl_status_chrome < NO_LONGER_PURSUING)]

      # Get no active, in dev, proposed features.
      q = Feature.all()
      q.order('impl_status_chrome')
      q.order('name')
      q.filter('impl_status_chrome <=', IN_DEVELOPMENT)
      pre_release = q.fetch(None)

      pre_release.extend(features)

      # Get no longer pursuing features.
      q = Feature.all()
      q.order('impl_status_chrome')
      q.order('name')
      q.filter('impl_status_chrome =', NO_LONGER_PURSUING)
      no_longer_pursuing = q.fetch(None)

      pre_release.extend(no_longer_pursuing)

      feature_list = [f.format_for_template() for f in pre_release]

      memcache.set(KEY, feature_list)

    return feature_list

  # Metadata.
  created = db.DateTimeProperty(auto_now_add=True)
  updated = db.DateTimeProperty(auto_now=True)
  updated_by = db.UserProperty(auto_current_user=True)
  created_by = db.UserProperty(auto_current_user_add=True)

  # General info.
  category = db.IntegerProperty(required=True)
  name = db.StringProperty(required=True)
  summary = db.StringProperty(required=True, multiline=True)

  # Chromium details.
  bug_url = db.LinkProperty()
  impl_status_chrome = db.IntegerProperty(required=True)
  shipped_milestone = db.IntegerProperty()
  shipped_android_milestone = db.IntegerProperty()
  shipped_ios_milestone = db.IntegerProperty()
  shipped_webview_milestone = db.IntegerProperty()
  shipped_opera_milestone = db.IntegerProperty()
  shipped_opera_android_milestone = db.IntegerProperty()

  owner = db.ListProperty(db.Email)
  footprint = db.IntegerProperty()
  visibility = db.IntegerProperty(required=True)

  #webbiness = db.IntegerProperty() # TODO: figure out what this is

  # Standards details.
  standardization = db.IntegerProperty(required=True)
  spec_link = db.LinkProperty()
  prefixed = db.BooleanProperty()

  ff_views = db.IntegerProperty(required=True, default=NO_PUBLIC_SIGNALS)
  ie_views = db.IntegerProperty(required=True, default=NO_PUBLIC_SIGNALS)
  safari_views = db.IntegerProperty(required=True, default=NO_PUBLIC_SIGNALS)

  ff_views_link = db.LinkProperty()
  ie_views_link = db.LinkProperty()
  safari_views_link = db.LinkProperty()

  # Web dev details.
  web_dev_views = db.IntegerProperty(required=True)
  doc_links = db.StringListProperty()
  sample_links = db.StringListProperty()
  #tests = db.StringProperty()

  comments = db.StringProperty(multiline=True)


class PlaceholderCharField(forms.CharField):

  def __init__(self, *args, **kwargs):
    #super(forms.CharField, self).__init__(*args, **kwargs)

    attrs = {}
    if kwargs.get('placeholder'):
      attrs['placeholder'] = kwargs.get('placeholder')
      del kwargs['placeholder']

    label = kwargs.get('label') or ''
    if label:
      del kwargs['label']

    self.max_length = kwargs.get('max_length') or None

    super(forms.CharField, self).__init__(label=label,
        widget=forms.TextInput(attrs=attrs), *args, **kwargs)


# class PlaceholderForm(forms.Form):
#   def __init__(self, *args, **kwargs):
#     super(PlaceholderForm, self).__init__(*args, **kwargs)

#     for field_name in self.fields:
#      field = self.fields.get(field_name)
#      if field:
#        if type(field.widget) in (forms.TextInput, forms.DateInput):
#          field.widget = forms.TextInput(attrs={'placeholder': field.label})


class FeatureForm(forms.Form):

  SHIPPED_HELP_TXT = ('First milestone the feature shipped with this status '
                      '(either enabled by default, experimental, or deprecated)')

  #name = PlaceholderCharField(required=True, placeholder='Feature name')
  name = forms.CharField(required=True, label='Feature')

  summary = forms.CharField(label='', required=True, max_length=500,
      widget=forms.Textarea(attrs={'cols': 50, 'placeholder': 'Summary description'}))

  # owner = PlaceholderCharField(
  #     required=False, placeholder='Owner(s) email',
  #     help_text='Comma separated list of full email addresses (@chromium.org preferred).')

  category = forms.ChoiceField(required=True,
                               choices=FEATURE_CATEGORIES.items())

  owner = forms.CharField(
      required=False, label='Owner(s) email',
      help_text='Comma separated list of full email addresses. Prefer @chromium.org.')


  bug_url = forms.URLField(required=False, label='Bug URL',
                           help_text='OWP Launch Tracking, crbug, etc.')

  impl_status_chrome = forms.ChoiceField(required=True,
                                         label='Status in Chrome',
                                         choices=IMPLEMENATION_STATUS.items())

  #shipped_milestone = PlaceholderCharField(required=False,
  #                                         placeholder='First milestone the feature shipped with this status (either enabled by default or experimental)')
  shipped_milestone = forms.IntegerField(required=False, label='',
      help_text='Chrome for desktop: ' + SHIPPED_HELP_TXT)

  shipped_android_milestone = forms.IntegerField(required=False, label='',
      help_text='Chrome for Android: ' + SHIPPED_HELP_TXT)

  shipped_ios_milestone = forms.IntegerField(required=False, label='',
      help_text='Chrome for iOS: ' + SHIPPED_HELP_TXT)

  shipped_webview_milestone = forms.IntegerField(required=False, label='',
      help_text='Chrome for Android web view: ' + SHIPPED_HELP_TXT)

  shipped_opera_milestone = forms.IntegerField(required=False, label='',
      help_text='Opera for desktop: ' + SHIPPED_HELP_TXT)

  shipped_opera_android_milestone = forms.IntegerField(required=False, label='',
      help_text='Opera for Android: ' + SHIPPED_HELP_TXT)

  prefixed = forms.BooleanField(
      required=False, initial=False, label='Prefixed?')

  standardization = forms.ChoiceField(
      label='Standardization', choices=STANDARDIZATION.items(),
      initial=EDITORS_DRAFT,
      help_text=("The standardization status of the API. In bodies that don't "
                 "use this nomenclature, use the closest equivalent."))

  spec_link = forms.URLField(required=False, label='Spec link',
                             help_text="Prefer editor's draft.")

  doc_links = forms.CharField(label='Doc links', required=False, max_length=500,
      widget=forms.Textarea(attrs={'cols': 50, 'placeholder': 'Links to documentation (comma separated)'}),
      help_text='Comma separated URLs')

  sample_links = forms.CharField(label='Samples links', required=False, max_length=500,
      widget=forms.Textarea(attrs={'cols': 50, 'placeholder': 'Links to samples (comma separated)'}),
      help_text='Comma separated URLs')

  footprint  = forms.ChoiceField(label='Technical footprint',
                                 choices=FOOTPRINT_CHOICES.items(),
                                 initial=MAJOR_MINOR_NEW_API)

  visibility  = forms.ChoiceField(
      label='Developer visibility',
      choices=VISIBILITY_CHOICES.items(),
      initial=WARRANTS_ARTICLE,
      help_text=('How much press / media / web developer buzz will this '
                 'feature generate?'))

  web_dev_views = forms.ChoiceField(
      label='Web developer views',
      choices=WEB_DEV_VIEWS.items(),
      initial=DEV_NO_SIGNALS,
      help_text=('How positive has the reaction from developers been? If '
                 'unsure, default to "No signals".'))

  safari_views = forms.ChoiceField(label='Safari views',
                                   choices=VENDOR_VIEWS.items(),
                                   initial=NO_PUBLIC_SIGNALS)
  safari_views_link = forms.URLField(required=False, label='',
      help_text='Citation link.')

  ff_views = forms.ChoiceField(label='Firefox views',
                               choices=VENDOR_VIEWS.items(),
                               initial=NO_PUBLIC_SIGNALS)
  ff_views_link = forms.URLField(required=False, label='',
      help_text='Citation link.')

  ie_views = forms.ChoiceField(label='IE views',
                               choices=VENDOR_VIEWS.items(),
                               initial=NO_PUBLIC_SIGNALS)
  ie_views_link = forms.URLField(required=False, label='',
      help_text='Citation link.')

  comments = forms.CharField(label='', required=False, widget=forms.Textarea(
      attrs={'cols': 50, 'placeholder': 'Additional comments, caveats, info...'}))

  class Meta:
    model = Feature
    #exclude = ('shipped_webview_milestone',)

  def __init__(self, *args, **keyargs):
    super(FeatureForm, self).__init__(*args, **keyargs)

    meta = getattr(self, 'Meta', None)
    exclude = getattr(meta, 'exclude', [])

    for field_name in exclude:
     if field_name in self.fields:
       del self.fields[field_name]

    for field, val in self.fields.iteritems():
      if val.required:
       self.fields[field].widget.attrs['required'] = 'required'


class AppUser(DictModel):
  """Describes a user for whitelisting."""

  #user = db.UserProperty(required=True, verbose_name='Google Account')
  email = db.EmailProperty(required=True)
  #is_admin = db.BooleanProperty(default=False)
  created = db.DateTimeProperty(auto_now_add=True)
  updated = db.DateTimeProperty(auto_now=True)

  def format_for_template(self):
    d = self.to_dict()
    d['id'] = self.key().id()
    return d

########NEW FILE########
__FILENAME__ = fetch_oauth_credentials
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2013 Google Inc. All Rights Reserved.

"""OAuth 2.0 Bootstrapper for App Engine dev server development.

Adapted from:
https://code.google.com/p/google-cloud-storage-samples/source/browse/gs-oauth.py
"""

__author__ = ('ericbidelman@chromium.org (Eric Bidelman), '
              'nherring@google.com (Nathan Herring)')


import datetime
import re
import os
import sys
from pkg_resources import parse_version


def downloadUsage(err, downloadUrl=None):
  """Emit usage statement with download information."""
  if downloadUrl is None:
    downloadString = 'Run'
  else:
    downloadString = 'Download available at %s or run' % downloadUrl
  print '%s\n%s%s' % (
      err,
      downloadString,
      ' setup.py on the google-api-python-client:\n' +
      'https://code.google.com/p/google-api-python-client/downloads')
  sys.exit(1)

def importUsage(lib, downloadUrl=None):
  """Emit a failed import error with download information."""
  downloadUsage('Could not load %s module.' % lib, downloadUrl)

#
# Import boilerplate to make it easy to diagnose when the right modules
# are not installed and how to remedy it.
#

try:
  from gflags import gflags
  print gflags.FLAGS
except:
  importUsage('gflags', 'https://code.google.com/p/python-gflags/downloads/')

try:
  import httplib2
except:
  importUsage('httplib2', 'https://code.google.com/p/httplib2/downloads/')

OAUTH2CLIENT_REQUIRED_VERSION = '1.0b8'
try:
  from oauth2client.file import Storage
  from oauth2client.client import flow_from_clientsecrets
  from oauth2client.client import OAuth2WebServerFlow
  from oauth2client.tools import run
  import oauth2client
except:
  importUsage('oauth2client')
oauth2client_version = None
if '__version__' not in oauth2client.__dict__:
  if '__file__' in oauth2client.__dict__:
    verMatch = re.search(r'google_api_python_client-([^-]+)',
                         oauth2client.__dict__['__file__'])
    if verMatch is not None:
      oauth2client_version = verMatch.group(1)
      oauth2client_version = re.sub('beta', 'b', oauth2client_version)
else:
  oauth2client_version = oauth2client.__dict__['__version__']
if oauth2client_version is None:
  downloadUsage('Could not determine version of oauth2client module.\n' +
      'Miminum required version is %s.' % OAUTH2CLIENT_REQUIRED_VERSION)
elif (parse_version(oauth2client_version) <
      parse_version(OAUTH2CLIENT_REQUIRED_VERSION)):
  downloadUsage(('oauth2client module version %s is too old.\n' +
      'Miminum required version is %s.') % (oauth2client_version, 
      OAUTH2CLIENT_REQUIRED_VERSION))

#
# End of the import boilerplate
#

FLAGS = gflags.FLAGS

gflags.DEFINE_multistring(
  'scope',
  'https://www.googleapis.com/auth/devstorage.read_only',
  'API scope to use')

gflags.DEFINE_string(
  'client_secrets_file',
  os.path.join(os.path.dirname(__file__), 'client_secrets.json'),
  'File name for client_secrets.json')

gflags.DEFINE_string(
  'credentials_file',
  os.path.join(os.path.dirname(__file__), 'oauth2.data2'),
  'File name for storing OAuth 2.0 credentials.',
  short_name='f')


def main(argv):
  try:
    argv = FLAGS(argv)
  except gflags.FlagsError, e:
    print '%s\nUsage: %s ARGS\n%s' % (e, sys.argv[0], FLAGS)
    sys.exit(1)

  storage = Storage(FLAGS.credentials_file)
  credentials = storage.get()
  if credentials is None or credentials.invalid:
    print 'Acquiring initial credentials...'
    
    # Need to acquire token using @google.com account.
    flow = flow_from_clientsecrets(
        FLAGS.client_secrets_file,
        scope=' '.join(FLAGS.scope),
        redirect_uri='urn:ietf:wg:oauth:2.0:oob',
        message='Error - client_secrets_file not found')

    credentials = run(flow, storage)
  elif credentials.access_token_expired:
    print 'Refreshing access token...'
    credentials.refresh(httplib2.Http())

  print 'Refresh token:', credentials.refresh_token
  print 'Access token:', credentials.access_token
  delta = credentials.token_expiry - datetime.datetime.utcnow()
  print 'Access token expires: %sZ (%dm %ds)' % (credentials.token_expiry,
      delta.seconds / 60, delta.seconds % 60)


if __name__ == '__main__':
  main(sys.argv)
########NEW FILE########
__FILENAME__ = fix_data
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2014 Google Inc. All Rights Reserved.

import models
import uma


def CorrectPropertyName(bucket_id):
  if bucket_id in uma.CSS_PROPERTY_BUCKETS:
    return uma.CSS_PROPERTY_BUCKETS[bucket_id]
  return None

def FetchAllPropertiesWithError(bucket_id=None):
  q = models.StableInstance.all()
  if bucket_id:
    q.filter('bucket_id =', bucket_id)
  q.filter('property_name =', 'ERROR')

  props = q.fetch(None)

  # Bucket 1 for CSS properties is total pages visited
  props = [p for p in props if p.bucket_id > 1]
  
  return props


if __name__ == '__main__':
  props = FetchAllPropertiesWithError()

  print 'Found', str(len(props)), 'properties tagged "ERROR"'

  need_correcting = {}
  for p in props:
    correct_name = CorrectPropertyName(p.bucket_id)
    if correct_name is not None:
      need_correcting[p.bucket_id] = correct_name

  for p in props:
    if p.bucket_id in need_correcting:
      new_name = need_correcting[p.bucket_id]
      print p.bucket_id, p.property_name, '->', new_name
      p.property_name = new_name
      p.put()

  print 'Done'


########NEW FILE########
__FILENAME__ = gflags
#!/usr/bin/env python
#
# Copyright (c) 2002, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# ---
# Author: Chad Lester
# Design and style contributions by:
#   Amit Patel, Bogdan Cocosel, Daniel Dulitz, Eric Tiedemann,
#   Eric Veach, Laurence Gonsalves, Matthew Springer
# Code reorganized a bit by Craig Silverstein

"""This module is used to define and parse command line flags.

This module defines a *distributed* flag-definition policy: rather than
an application having to define all flags in or near main(), each python
module defines flags that are useful to it.  When one python module
imports another, it gains access to the other's flags.  (This is
implemented by having all modules share a common, global registry object
containing all the flag information.)

Flags are defined through the use of one of the DEFINE_xxx functions.
The specific function used determines how the flag is parsed, checked,
and optionally type-converted, when it's seen on the command line.


IMPLEMENTATION: DEFINE_* creates a 'Flag' object and registers it with a
'FlagValues' object (typically the global FlagValues FLAGS, defined
here).  The 'FlagValues' object can scan the command line arguments and
pass flag arguments to the corresponding 'Flag' objects for
value-checking and type conversion.  The converted flag values are
available as attributes of the 'FlagValues' object.

Code can access the flag through a FlagValues object, for instance
gflags.FLAGS.myflag.  Typically, the __main__ module passes the command
line arguments to gflags.FLAGS for parsing.

At bottom, this module calls getopt(), so getopt functionality is
supported, including short- and long-style flags, and the use of -- to
terminate flags.

Methods defined by the flag module will throw 'FlagsError' exceptions.
The exception argument will be a human-readable string.


FLAG TYPES: This is a list of the DEFINE_*'s that you can do.  All flags
take a name, default value, help-string, and optional 'short' name
(one-letter name).  Some flags have other arguments, which are described
with the flag.

DEFINE_string: takes any input, and interprets it as a string.

DEFINE_bool or
DEFINE_boolean: typically does not take an argument: say --myflag to
                set FLAGS.myflag to true, or --nomyflag to set
                FLAGS.myflag to false.  Alternately, you can say
                   --myflag=true  or --myflag=t or --myflag=1  or
                   --myflag=false or --myflag=f or --myflag=0

DEFINE_float: takes an input and interprets it as a floating point
              number.  Takes optional args lower_bound and upper_bound;
              if the number specified on the command line is out of
              range, it will raise a FlagError.

DEFINE_integer: takes an input and interprets it as an integer.  Takes
                optional args lower_bound and upper_bound as for floats.

DEFINE_enum: takes a list of strings which represents legal values.  If
             the command-line value is not in this list, raise a flag
             error.  Otherwise, assign to FLAGS.flag as a string.

DEFINE_list: Takes a comma-separated list of strings on the commandline.
             Stores them in a python list object.

DEFINE_spaceseplist: Takes a space-separated list of strings on the
                     commandline.  Stores them in a python list object.
                     Example: --myspacesepflag "foo bar baz"

DEFINE_multistring: The same as DEFINE_string, except the flag can be
                    specified more than once on the commandline.  The
                    result is a python list object (list of strings),
                    even if the flag is only on the command line once.

DEFINE_multi_int: The same as DEFINE_integer, except the flag can be
                  specified more than once on the commandline.  The
                  result is a python list object (list of ints), even if
                  the flag is only on the command line once.


SPECIAL FLAGS: There are a few flags that have special meaning:
   --help          prints a list of all the flags in a human-readable fashion
   --helpshort     prints a list of all key flags (see below).
   --helpxml       prints a list of all flags, in XML format.  DO NOT parse
                   the output of --help and --helpshort.  Instead, parse
                   the output of --helpxml.  For more info, see
                   "OUTPUT FOR --helpxml" below.
   --flagfile=foo  read flags from file foo.
   --undefok=f1,f2 ignore unrecognized option errors for f1,f2.
                   For boolean flags, you should use --undefok=boolflag, and
                   --boolflag and --noboolflag will be accepted.  Do not use
                   --undefok=noboolflag.
   --              as in getopt(), terminates flag-processing


FLAGS VALIDATORS: If your program:
  - requires flag X to be specified
  - needs flag Y to match a regular expression
  - or requires any more general constraint to be satisfied
then validators are for you!

Each validator represents a constraint over one flag, which is enforced
starting from the initial parsing of the flags and until the program
terminates.

Also, lower_bound and upper_bound for numerical flags are enforced using flag
validators.

Howto:
If you want to enforce a constraint over one flag, use

gflags.RegisterValidator(flag_name,
                        checker,
                        message='Flag validation failed',
                        flag_values=FLAGS)

After flag values are initially parsed, and after any change to the specified
flag, method checker(flag_value) will be executed. If constraint is not
satisfied, an IllegalFlagValue exception will be raised. See
RegisterValidator's docstring for a detailed explanation on how to construct
your own checker.


EXAMPLE USAGE:

FLAGS = gflags.FLAGS

gflags.DEFINE_integer('my_version', 0, 'Version number.')
gflags.DEFINE_string('filename', None, 'Input file name', short_name='f')

gflags.RegisterValidator('my_version',
                        lambda value: value % 2 == 0,
                        message='--my_version must be divisible by 2')
gflags.MarkFlagAsRequired('filename')


NOTE ON --flagfile:

Flags may be loaded from text files in addition to being specified on
the commandline.

Any flags you don't feel like typing, throw them in a file, one flag per
line, for instance:
   --myflag=myvalue
   --nomyboolean_flag
You then specify your file with the special flag '--flagfile=somefile'.
You CAN recursively nest flagfile= tokens OR use multiple files on the
command line.  Lines beginning with a single hash '#' or a double slash
'//' are comments in your flagfile.

Any flagfile=<file> will be interpreted as having a relative path from
the current working directory rather than from the place the file was
included from:
   myPythonScript.py --flagfile=config/somefile.cfg

If somefile.cfg includes further --flagfile= directives, these will be
referenced relative to the original CWD, not from the directory the
including flagfile was found in!

The caveat applies to people who are including a series of nested files
in a different dir than they are executing out of.  Relative path names
are always from CWD, not from the directory of the parent include
flagfile. We do now support '~' expanded directory names.

Absolute path names ALWAYS work!


EXAMPLE USAGE:


  FLAGS = gflags.FLAGS

  # Flag names are globally defined!  So in general, we need to be
  # careful to pick names that are unlikely to be used by other libraries.
  # If there is a conflict, we'll get an error at import time.
  gflags.DEFINE_string('name', 'Mr. President', 'your name')
  gflags.DEFINE_integer('age', None, 'your age in years', lower_bound=0)
  gflags.DEFINE_boolean('debug', False, 'produces debugging output')
  gflags.DEFINE_enum('gender', 'male', ['male', 'female'], 'your gender')

  def main(argv):
    try:
      argv = FLAGS(argv)  # parse flags
    except gflags.FlagsError, e:
      print '%s\\nUsage: %s ARGS\\n%s' % (e, sys.argv[0], FLAGS)
      sys.exit(1)
    if FLAGS.debug: print 'non-flag arguments:', argv
    print 'Happy Birthday', FLAGS.name
    if FLAGS.age is not None:
      print 'You are a %d year old %s' % (FLAGS.age, FLAGS.gender)

  if __name__ == '__main__':
    main(sys.argv)


KEY FLAGS:

As we already explained, each module gains access to all flags defined
by all the other modules it transitively imports.  In the case of
non-trivial scripts, this means a lot of flags ...  For documentation
purposes, it is good to identify the flags that are key (i.e., really
important) to a module.  Clearly, the concept of "key flag" is a
subjective one.  When trying to determine whether a flag is key to a
module or not, assume that you are trying to explain your module to a
potential user: which flags would you really like to mention first?

We'll describe shortly how to declare which flags are key to a module.
For the moment, assume we know the set of key flags for each module.
Then, if you use the app.py module, you can use the --helpshort flag to
print only the help for the flags that are key to the main module, in a
human-readable format.

NOTE: If you need to parse the flag help, do NOT use the output of
--help / --helpshort.  That output is meant for human consumption, and
may be changed in the future.  Instead, use --helpxml; flags that are
key for the main module are marked there with a <key>yes</key> element.

The set of key flags for a module M is composed of:

1. Flags defined by module M by calling a DEFINE_* function.

2. Flags that module M explictly declares as key by using the function

     DECLARE_key_flag(<flag_name>)

3. Key flags of other modules that M specifies by using the function

     ADOPT_module_key_flags(<other_module>)

   This is a "bulk" declaration of key flags: each flag that is key for
   <other_module> becomes key for the current module too.

Notice that if you do not use the functions described at points 2 and 3
above, then --helpshort prints information only about the flags defined
by the main module of our script.  In many cases, this behavior is good
enough.  But if you move part of the main module code (together with the
related flags) into a different module, then it is nice to use
DECLARE_key_flag / ADOPT_module_key_flags and make sure --helpshort
lists all relevant flags (otherwise, your code refactoring may confuse
your users).

Note: each of DECLARE_key_flag / ADOPT_module_key_flags has its own
pluses and minuses: DECLARE_key_flag is more targeted and may lead a
more focused --helpshort documentation.  ADOPT_module_key_flags is good
for cases when an entire module is considered key to the current script.
Also, it does not require updates to client scripts when a new flag is
added to the module.


EXAMPLE USAGE 2 (WITH KEY FLAGS):

Consider an application that contains the following three files (two
auxiliary modules and a main module)

File libfoo.py:

  import gflags

  gflags.DEFINE_integer('num_replicas', 3, 'Number of replicas to start')
  gflags.DEFINE_boolean('rpc2', True, 'Turn on the usage of RPC2.')

  ... some code ...

File libbar.py:

  import gflags

  gflags.DEFINE_string('bar_gfs_path', '/gfs/path',
                      'Path to the GFS files for libbar.')
  gflags.DEFINE_string('email_for_bar_errors', 'bar-team@google.com',
                      'Email address for bug reports about module libbar.')
  gflags.DEFINE_boolean('bar_risky_hack', False,
                       'Turn on an experimental and buggy optimization.')

  ... some code ...

File myscript.py:

  import gflags
  import libfoo
  import libbar

  gflags.DEFINE_integer('num_iterations', 0, 'Number of iterations.')

  # Declare that all flags that are key for libfoo are
  # key for this module too.
  gflags.ADOPT_module_key_flags(libfoo)

  # Declare that the flag --bar_gfs_path (defined in libbar) is key
  # for this module.
  gflags.DECLARE_key_flag('bar_gfs_path')

  ... some code ...

When myscript is invoked with the flag --helpshort, the resulted help
message lists information about all the key flags for myscript:
--num_iterations, --num_replicas, --rpc2, and --bar_gfs_path.

Of course, myscript uses all the flags declared by it (in this case,
just --num_replicas) or by any of the modules it transitively imports
(e.g., the modules libfoo, libbar).  E.g., it can access the value of
FLAGS.bar_risky_hack, even if --bar_risky_hack is not declared as a key
flag for myscript.


OUTPUT FOR --helpxml:

The --helpxml flag generates output with the following structure:

<?xml version="1.0"?>
<AllFlags>
  <program>PROGRAM_BASENAME</program>
  <usage>MAIN_MODULE_DOCSTRING</usage>
  (<flag>
    [<key>yes</key>]
    <file>DECLARING_MODULE</file>
    <name>FLAG_NAME</name>
    <meaning>FLAG_HELP_MESSAGE</meaning>
    <default>DEFAULT_FLAG_VALUE</default>
    <current>CURRENT_FLAG_VALUE</current>
    <type>FLAG_TYPE</type>
    [OPTIONAL_ELEMENTS]
  </flag>)*
</AllFlags>

Notes:

1. The output is intentionally similar to the output generated by the
C++ command-line flag library.  The few differences are due to the
Python flags that do not have a C++ equivalent (at least not yet),
e.g., DEFINE_list.

2. New XML elements may be added in the future.

3. DEFAULT_FLAG_VALUE is in serialized form, i.e., the string you can
pass for this flag on the command-line.  E.g., for a flag defined
using DEFINE_list, this field may be foo,bar, not ['foo', 'bar'].

4. CURRENT_FLAG_VALUE is produced using str().  This means that the
string 'false' will be represented in the same way as the boolean
False.  Using repr() would have removed this ambiguity and simplified
parsing, but would have broken the compatibility with the C++
command-line flags.

5. OPTIONAL_ELEMENTS describe elements relevant for certain kinds of
flags: lower_bound, upper_bound (for flags that specify bounds),
enum_value (for enum flags), list_separator (for flags that consist of
a list of values, separated by a special token).

6. We do not provide any example here: please use --helpxml instead.

This module requires at least python 2.2.1 to run.
"""

import cgi
import getopt
import os
import re
import string
import struct
import sys
# pylint: disable-msg=C6204
try:
  import fcntl
except ImportError:
  fcntl = None
try:
  # Importing termios will fail on non-unix platforms.
  import termios
except ImportError:
  termios = None

import gflags_validators
# pylint: enable-msg=C6204


# Are we running under pychecker?
_RUNNING_PYCHECKER = 'pychecker.python' in sys.modules


def _GetCallingModuleObjectAndName():
  """Returns the module that's calling into this module.

  We generally use this function to get the name of the module calling a
  DEFINE_foo... function.
  """
  # Walk down the stack to find the first globals dict that's not ours.
  for depth in range(1, sys.getrecursionlimit()):
    if not sys._getframe(depth).f_globals is globals():
      globals_for_frame = sys._getframe(depth).f_globals
      module, module_name = _GetModuleObjectAndName(globals_for_frame)
      if module_name is not None:
        return module, module_name
  raise AssertionError("No module was found")


def _GetCallingModule():
  """Returns the name of the module that's calling into this module."""
  return _GetCallingModuleObjectAndName()[1]


def _GetThisModuleObjectAndName():
  """Returns: (module object, module name) for this module."""
  return _GetModuleObjectAndName(globals())


# module exceptions:
class FlagsError(Exception):
  """The base class for all flags errors."""
  pass


class DuplicateFlag(FlagsError):
  """Raised if there is a flag naming conflict."""
  pass

class CantOpenFlagFileError(FlagsError):
  """Raised if flagfile fails to open: doesn't exist, wrong permissions, etc."""
  pass


class DuplicateFlagCannotPropagateNoneToSwig(DuplicateFlag):
  """Special case of DuplicateFlag -- SWIG flag value can't be set to None.

  This can be raised when a duplicate flag is created. Even if allow_override is
  True, we still abort if the new value is None, because it's currently
  impossible to pass None default value back to SWIG. See FlagValues.SetDefault
  for details.
  """
  pass


class DuplicateFlagError(DuplicateFlag):
  """A DuplicateFlag whose message cites the conflicting definitions.

  A DuplicateFlagError conveys more information than a DuplicateFlag,
  namely the modules where the conflicting definitions occur. This
  class was created to avoid breaking external modules which depend on
  the existing DuplicateFlags interface.
  """

  def __init__(self, flagname, flag_values, other_flag_values=None):
    """Create a DuplicateFlagError.

    Args:
      flagname: Name of the flag being redefined.
      flag_values: FlagValues object containing the first definition of
          flagname.
      other_flag_values: If this argument is not None, it should be the
          FlagValues object where the second definition of flagname occurs.
          If it is None, we assume that we're being called when attempting
          to create the flag a second time, and we use the module calling
          this one as the source of the second definition.
    """
    self.flagname = flagname
    first_module = flag_values.FindModuleDefiningFlag(
        flagname, default='<unknown>')
    if other_flag_values is None:
      second_module = _GetCallingModule()
    else:
      second_module = other_flag_values.FindModuleDefiningFlag(
          flagname, default='<unknown>')
    msg = "The flag '%s' is defined twice. First from %s, Second from %s" % (
        self.flagname, first_module, second_module)
    DuplicateFlag.__init__(self, msg)


class IllegalFlagValue(FlagsError):
  """The flag command line argument is illegal."""
  pass


class UnrecognizedFlag(FlagsError):
  """Raised if a flag is unrecognized."""
  pass


# An UnrecognizedFlagError conveys more information than an UnrecognizedFlag.
# Since there are external modules that create DuplicateFlags, the interface to
# DuplicateFlag shouldn't change.  The flagvalue will be assigned the full value
# of the flag and its argument, if any, allowing handling of unrecognized flags
# in an exception handler.
# If flagvalue is the empty string, then this exception is an due to a
# reference to a flag that was not already defined.
class UnrecognizedFlagError(UnrecognizedFlag):
  def __init__(self, flagname, flagvalue=''):
    self.flagname = flagname
    self.flagvalue = flagvalue
    UnrecognizedFlag.__init__(
        self, "Unknown command line flag '%s'" % flagname)

# Global variable used by expvar
_exported_flags = {}
_help_width = 80  # width of help output


def GetHelpWidth():
  """Returns: an integer, the width of help lines that is used in TextWrap."""
  if (not sys.stdout.isatty()) or (termios is None) or (fcntl is None):
    return _help_width
  try:
    data = fcntl.ioctl(sys.stdout, termios.TIOCGWINSZ, '1234')
    columns = struct.unpack('hh', data)[1]
    # Emacs mode returns 0.
    # Here we assume that any value below 40 is unreasonable
    if columns >= 40:
      return columns
    # Returning an int as default is fine, int(int) just return the int.
    return int(os.getenv('COLUMNS', _help_width))

  except (TypeError, IOError, struct.error):
    return _help_width


def CutCommonSpacePrefix(text):
  """Removes a common space prefix from the lines of a multiline text.

  If the first line does not start with a space, it is left as it is and
  only in the remaining lines a common space prefix is being searched
  for. That means the first line will stay untouched. This is especially
  useful to turn doc strings into help texts. This is because some
  people prefer to have the doc comment start already after the
  apostrophe and then align the following lines while others have the
  apostrophes on a separate line.

  The function also drops trailing empty lines and ignores empty lines
  following the initial content line while calculating the initial
  common whitespace.

  Args:
    text: text to work on

  Returns:
    the resulting text
  """
  text_lines = text.splitlines()
  # Drop trailing empty lines
  while text_lines and not text_lines[-1]:
    text_lines = text_lines[:-1]
  if text_lines:
    # We got some content, is the first line starting with a space?
    if text_lines[0] and text_lines[0][0].isspace():
      text_first_line = []
    else:
      text_first_line = [text_lines.pop(0)]
    # Calculate length of common leading whitespace (only over content lines)
    common_prefix = os.path.commonprefix([line for line in text_lines if line])
    space_prefix_len = len(common_prefix) - len(common_prefix.lstrip())
    # If we have a common space prefix, drop it from all lines
    if space_prefix_len:
      for index in xrange(len(text_lines)):
        if text_lines[index]:
          text_lines[index] = text_lines[index][space_prefix_len:]
    return '\n'.join(text_first_line + text_lines)
  return ''


def TextWrap(text, length=None, indent='', firstline_indent=None, tabs='    '):
  """Wraps a given text to a maximum line length and returns it.

  We turn lines that only contain whitespace into empty lines.  We keep
  new lines and tabs (e.g., we do not treat tabs as spaces).

  Args:
    text:             text to wrap
    length:           maximum length of a line, includes indentation
                      if this is None then use GetHelpWidth()
    indent:           indent for all but first line
    firstline_indent: indent for first line; if None, fall back to indent
    tabs:             replacement for tabs

  Returns:
    wrapped text

  Raises:
    FlagsError: if indent not shorter than length
    FlagsError: if firstline_indent not shorter than length
  """
  # Get defaults where callee used None
  if length is None:
    length = GetHelpWidth()
  if indent is None:
    indent = ''
  if len(indent) >= length:
    raise FlagsError('Indent must be shorter than length')
  # In line we will be holding the current line which is to be started
  # with indent (or firstline_indent if available) and then appended
  # with words.
  if firstline_indent is None:
    firstline_indent = ''
    line = indent
  else:
    line = firstline_indent
    if len(firstline_indent) >= length:
      raise FlagsError('First line indent must be shorter than length')

  # If the callee does not care about tabs we simply convert them to
  # spaces If callee wanted tabs to be single space then we do that
  # already here.
  if not tabs or tabs == ' ':
    text = text.replace('\t', ' ')
  else:
    tabs_are_whitespace = not tabs.strip()

  line_regex = re.compile('([ ]*)(\t*)([^ \t]+)', re.MULTILINE)

  # Split the text into lines and the lines with the regex above. The
  # resulting lines are collected in result[]. For each split we get the
  # spaces, the tabs and the next non white space (e.g. next word).
  result = []
  for text_line in text.splitlines():
    # Store result length so we can find out whether processing the next
    # line gave any new content
    old_result_len = len(result)
    # Process next line with line_regex. For optimization we do an rstrip().
    # - process tabs (changes either line or word, see below)
    # - process word (first try to squeeze on line, then wrap or force wrap)
    # Spaces found on the line are ignored, they get added while wrapping as
    # needed.
    for spaces, current_tabs, word in line_regex.findall(text_line.rstrip()):
      # If tabs weren't converted to spaces, handle them now
      if current_tabs:
        # If the last thing we added was a space anyway then drop
        # it. But let's not get rid of the indentation.
        if (((result and line != indent) or
             (not result and line != firstline_indent)) and line[-1] == ' '):
          line = line[:-1]
        # Add the tabs, if that means adding whitespace, just add it at
        # the line, the rstrip() code while shorten the line down if
        # necessary
        if tabs_are_whitespace:
          line += tabs * len(current_tabs)
        else:
          # if not all tab replacement is whitespace we prepend it to the word
          word = tabs * len(current_tabs) + word
      # Handle the case where word cannot be squeezed onto current last line
      if len(line) + len(word) > length and len(indent) + len(word) <= length:
        result.append(line.rstrip())
        line = indent + word
        word = ''
        # No space left on line or can we append a space?
        if len(line) + 1 >= length:
          result.append(line.rstrip())
          line = indent
        else:
          line += ' '
      # Add word and shorten it up to allowed line length. Restart next
      # line with indent and repeat, or add a space if we're done (word
      # finished) This deals with words that cannot fit on one line
      # (e.g. indent + word longer than allowed line length).
      while len(line) + len(word) >= length:
        line += word
        result.append(line[:length])
        word = line[length:]
        line = indent
      # Default case, simply append the word and a space
      if word:
        line += word + ' '
    # End of input line. If we have content we finish the line. If the
    # current line is just the indent but we had content in during this
    # original line then we need to add an empty line.
    if (result and line != indent) or (not result and line != firstline_indent):
      result.append(line.rstrip())
    elif len(result) == old_result_len:
      result.append('')
    line = indent

  return '\n'.join(result)


def DocToHelp(doc):
  """Takes a __doc__ string and reformats it as help."""

  # Get rid of starting and ending white space. Using lstrip() or even
  # strip() could drop more than maximum of first line and right space
  # of last line.
  doc = doc.strip()

  # Get rid of all empty lines
  whitespace_only_line = re.compile('^[ \t]+$', re.M)
  doc = whitespace_only_line.sub('', doc)

  # Cut out common space at line beginnings
  doc = CutCommonSpacePrefix(doc)

  # Just like this module's comment, comments tend to be aligned somehow.
  # In other words they all start with the same amount of white space
  # 1) keep double new lines
  # 2) keep ws after new lines if not empty line
  # 3) all other new lines shall be changed to a space
  # Solution: Match new lines between non white space and replace with space.
  doc = re.sub('(?<=\S)\n(?=\S)', ' ', doc, re.M)

  return doc


def _GetModuleObjectAndName(globals_dict):
  """Returns the module that defines a global environment, and its name.

  Args:
    globals_dict: A dictionary that should correspond to an environment
      providing the values of the globals.

  Returns:
    A pair consisting of (1) module object and (2) module name (a
    string).  Returns (None, None) if the module could not be
    identified.
  """
  # The use of .items() (instead of .iteritems()) is NOT a mistake: if
  # a parallel thread imports a module while we iterate over
  # .iteritems() (not nice, but possible), we get a RuntimeError ...
  # Hence, we use the slightly slower but safer .items().
  for name, module in sys.modules.items():
    if getattr(module, '__dict__', None) is globals_dict:
      if name == '__main__':
        # Pick a more informative name for the main module.
        name = sys.argv[0]
      return (module, name)
  return (None, None)


def _GetMainModule():
  """Returns: string, name of the module from which execution started."""
  # First, try to use the same logic used by _GetCallingModuleObjectAndName(),
  # i.e., call _GetModuleObjectAndName().  For that we first need to
  # find the dictionary that the main module uses to store the
  # globals.
  #
  # That's (normally) the same dictionary object that the deepest
  # (oldest) stack frame is using for globals.
  deepest_frame = sys._getframe(0)
  while deepest_frame.f_back is not None:
    deepest_frame = deepest_frame.f_back
  globals_for_main_module = deepest_frame.f_globals
  main_module_name = _GetModuleObjectAndName(globals_for_main_module)[1]
  # The above strategy fails in some cases (e.g., tools that compute
  # code coverage by redefining, among other things, the main module).
  # If so, just use sys.argv[0].  We can probably always do this, but
  # it's safest to try to use the same logic as _GetCallingModuleObjectAndName()
  if main_module_name is None:
    main_module_name = sys.argv[0]
  return main_module_name


class FlagValues:
  """Registry of 'Flag' objects.

  A 'FlagValues' can then scan command line arguments, passing flag
  arguments through to the 'Flag' objects that it owns.  It also
  provides easy access to the flag values.  Typically only one
  'FlagValues' object is needed by an application: gflags.FLAGS

  This class is heavily overloaded:

  'Flag' objects are registered via __setitem__:
       FLAGS['longname'] = x   # register a new flag

  The .value attribute of the registered 'Flag' objects can be accessed
  as attributes of this 'FlagValues' object, through __getattr__.  Both
  the long and short name of the original 'Flag' objects can be used to
  access its value:
       FLAGS.longname          # parsed flag value
       FLAGS.x                 # parsed flag value (short name)

  Command line arguments are scanned and passed to the registered 'Flag'
  objects through the __call__ method.  Unparsed arguments, including
  argv[0] (e.g. the program name) are returned.
       argv = FLAGS(sys.argv)  # scan command line arguments

  The original registered Flag objects can be retrieved through the use
  of the dictionary-like operator, __getitem__:
       x = FLAGS['longname']   # access the registered Flag object

  The str() operator of a 'FlagValues' object provides help for all of
  the registered 'Flag' objects.
  """

  def __init__(self):
    # Since everything in this class is so heavily overloaded, the only
    # way of defining and using fields is to access __dict__ directly.

    # Dictionary: flag name (string) -> Flag object.
    self.__dict__['__flags'] = {}
    # Dictionary: module name (string) -> list of Flag objects that are defined
    # by that module.
    self.__dict__['__flags_by_module'] = {}
    # Dictionary: module id (int) -> list of Flag objects that are defined by
    # that module.
    self.__dict__['__flags_by_module_id'] = {}
    # Dictionary: module name (string) -> list of Flag objects that are
    # key for that module.
    self.__dict__['__key_flags_by_module'] = {}

    # Set if we should use new style gnu_getopt rather than getopt when parsing
    # the args.  Only possible with Python 2.3+
    self.UseGnuGetOpt(False)

  def UseGnuGetOpt(self, use_gnu_getopt=True):
    """Use GNU-style scanning. Allows mixing of flag and non-flag arguments.

    See http://docs.python.org/library/getopt.html#getopt.gnu_getopt

    Args:
      use_gnu_getopt: wether or not to use GNU style scanning.
    """
    self.__dict__['__use_gnu_getopt'] = use_gnu_getopt

  def IsGnuGetOpt(self):
    return self.__dict__['__use_gnu_getopt']

  def FlagDict(self):
    return self.__dict__['__flags']

  def FlagsByModuleDict(self):
    """Returns the dictionary of module_name -> list of defined flags.

    Returns:
      A dictionary.  Its keys are module names (strings).  Its values
      are lists of Flag objects.
    """
    return self.__dict__['__flags_by_module']

  def FlagsByModuleIdDict(self):
    """Returns the dictionary of module_id -> list of defined flags.

    Returns:
      A dictionary.  Its keys are module IDs (ints).  Its values
      are lists of Flag objects.
    """
    return self.__dict__['__flags_by_module_id']

  def KeyFlagsByModuleDict(self):
    """Returns the dictionary of module_name -> list of key flags.

    Returns:
      A dictionary.  Its keys are module names (strings).  Its values
      are lists of Flag objects.
    """
    return self.__dict__['__key_flags_by_module']

  def _RegisterFlagByModule(self, module_name, flag):
    """Records the module that defines a specific flag.

    We keep track of which flag is defined by which module so that we
    can later sort the flags by module.

    Args:
      module_name: A string, the name of a Python module.
      flag: A Flag object, a flag that is key to the module.
    """
    flags_by_module = self.FlagsByModuleDict()
    flags_by_module.setdefault(module_name, []).append(flag)

  def _RegisterFlagByModuleId(self, module_id, flag):
    """Records the module that defines a specific flag.

    Args:
      module_id: An int, the ID of the Python module.
      flag: A Flag object, a flag that is key to the module.
    """
    flags_by_module_id = self.FlagsByModuleIdDict()
    flags_by_module_id.setdefault(module_id, []).append(flag)

  def _RegisterKeyFlagForModule(self, module_name, flag):
    """Specifies that a flag is a key flag for a module.

    Args:
      module_name: A string, the name of a Python module.
      flag: A Flag object, a flag that is key to the module.
    """
    key_flags_by_module = self.KeyFlagsByModuleDict()
    # The list of key flags for the module named module_name.
    key_flags = key_flags_by_module.setdefault(module_name, [])
    # Add flag, but avoid duplicates.
    if flag not in key_flags:
      key_flags.append(flag)

  def _GetFlagsDefinedByModule(self, module):
    """Returns the list of flags defined by a module.

    Args:
      module: A module object or a module name (a string).

    Returns:
      A new list of Flag objects.  Caller may update this list as he
      wishes: none of those changes will affect the internals of this
      FlagValue object.
    """
    if not isinstance(module, str):
      module = module.__name__

    return list(self.FlagsByModuleDict().get(module, []))

  def _GetKeyFlagsForModule(self, module):
    """Returns the list of key flags for a module.

    Args:
      module: A module object or a module name (a string)

    Returns:
      A new list of Flag objects.  Caller may update this list as he
      wishes: none of those changes will affect the internals of this
      FlagValue object.
    """
    if not isinstance(module, str):
      module = module.__name__

    # Any flag is a key flag for the module that defined it.  NOTE:
    # key_flags is a fresh list: we can update it without affecting the
    # internals of this FlagValues object.
    key_flags = self._GetFlagsDefinedByModule(module)

    # Take into account flags explicitly declared as key for a module.
    for flag in self.KeyFlagsByModuleDict().get(module, []):
      if flag not in key_flags:
        key_flags.append(flag)
    return key_flags

  def FindModuleDefiningFlag(self, flagname, default=None):
    """Return the name of the module defining this flag, or default.

    Args:
      flagname: Name of the flag to lookup.
      default: Value to return if flagname is not defined. Defaults
          to None.

    Returns:
      The name of the module which registered the flag with this name.
      If no such module exists (i.e. no flag with this name exists),
      we return default.
    """
    for module, flags in self.FlagsByModuleDict().iteritems():
      for flag in flags:
        if flag.name == flagname or flag.short_name == flagname:
          return module
    return default

  def FindModuleIdDefiningFlag(self, flagname, default=None):
    """Return the ID of the module defining this flag, or default.

    Args:
      flagname: Name of the flag to lookup.
      default: Value to return if flagname is not defined. Defaults
          to None.

    Returns:
      The ID of the module which registered the flag with this name.
      If no such module exists (i.e. no flag with this name exists),
      we return default.
    """
    for module_id, flags in self.FlagsByModuleIdDict().iteritems():
      for flag in flags:
        if flag.name == flagname or flag.short_name == flagname:
          return module_id
    return default

  def AppendFlagValues(self, flag_values):
    """Appends flags registered in another FlagValues instance.

    Args:
      flag_values: registry to copy from
    """
    for flag_name, flag in flag_values.FlagDict().iteritems():
      # Each flags with shortname appears here twice (once under its
      # normal name, and again with its short name).  To prevent
      # problems (DuplicateFlagError) with double flag registration, we
      # perform a check to make sure that the entry we're looking at is
      # for its normal name.
      if flag_name == flag.name:
        try:
          self[flag_name] = flag
        except DuplicateFlagError:
          raise DuplicateFlagError(flag_name, self,
                                   other_flag_values=flag_values)

  def RemoveFlagValues(self, flag_values):
    """Remove flags that were previously appended from another FlagValues.

    Args:
      flag_values: registry containing flags to remove.
    """
    for flag_name in flag_values.FlagDict():
      self.__delattr__(flag_name)

  def __setitem__(self, name, flag):
    """Registers a new flag variable."""
    fl = self.FlagDict()
    if not isinstance(flag, Flag):
      raise IllegalFlagValue(flag)
    if not isinstance(name, type("")):
      raise FlagsError("Flag name must be a string")
    if len(name) == 0:
      raise FlagsError("Flag name cannot be empty")
    # If running under pychecker, duplicate keys are likely to be
    # defined.  Disable check for duplicate keys when pycheck'ing.
    if (name in fl and not flag.allow_override and
        not fl[name].allow_override and not _RUNNING_PYCHECKER):
      module, module_name = _GetCallingModuleObjectAndName()
      if (self.FindModuleDefiningFlag(name) == module_name and
          id(module) != self.FindModuleIdDefiningFlag(name)):
        # If the flag has already been defined by a module with the same name,
        # but a different ID, we can stop here because it indicates that the
        # module is simply being imported a subsequent time.
        return
      raise DuplicateFlagError(name, self)
    short_name = flag.short_name
    if short_name is not None:
      if (short_name in fl and not flag.allow_override and
          not fl[short_name].allow_override and not _RUNNING_PYCHECKER):
        raise DuplicateFlagError(short_name, self)
      fl[short_name] = flag
    fl[name] = flag
    global _exported_flags
    _exported_flags[name] = flag

  def __getitem__(self, name):
    """Retrieves the Flag object for the flag --name."""
    return self.FlagDict()[name]

  def __getattr__(self, name):
    """Retrieves the 'value' attribute of the flag --name."""
    fl = self.FlagDict()
    if name not in fl:
      raise AttributeError(name)
    return fl[name].value

  def __setattr__(self, name, value):
    """Sets the 'value' attribute of the flag --name."""
    fl = self.FlagDict()
    fl[name].value = value
    self._AssertValidators(fl[name].validators)
    return value

  def _AssertAllValidators(self):
    all_validators = set()
    for flag in self.FlagDict().itervalues():
      for validator in flag.validators:
        all_validators.add(validator)
    self._AssertValidators(all_validators)

  def _AssertValidators(self, validators):
    """Assert if all validators in the list are satisfied.

    Asserts validators in the order they were created.
    Args:
      validators: Iterable(gflags_validators.Validator), validators to be
        verified
    Raises:
      AttributeError: if validators work with a non-existing flag.
      IllegalFlagValue: if validation fails for at least one validator
    """
    for validator in sorted(
        validators, key=lambda validator: validator.insertion_index):
      try:
        validator.Verify(self)
      except gflags_validators.Error, e:
        message = validator.PrintFlagsWithValues(self)
        raise IllegalFlagValue('%s: %s' % (message, str(e)))

  def _FlagIsRegistered(self, flag_obj):
    """Checks whether a Flag object is registered under some name.

    Note: this is non trivial: in addition to its normal name, a flag
    may have a short name too.  In self.FlagDict(), both the normal and
    the short name are mapped to the same flag object.  E.g., calling
    only "del FLAGS.short_name" is not unregistering the corresponding
    Flag object (it is still registered under the longer name).

    Args:
      flag_obj: A Flag object.

    Returns:
      A boolean: True iff flag_obj is registered under some name.
    """
    flag_dict = self.FlagDict()
    # Check whether flag_obj is registered under its long name.
    name = flag_obj.name
    if flag_dict.get(name, None) == flag_obj:
      return True
    # Check whether flag_obj is registered under its short name.
    short_name = flag_obj.short_name
    if (short_name is not None and
        flag_dict.get(short_name, None) == flag_obj):
      return True
    # The flag cannot be registered under any other name, so we do not
    # need to do a full search through the values of self.FlagDict().
    return False

  def __delattr__(self, flag_name):
    """Deletes a previously-defined flag from a flag object.

    This method makes sure we can delete a flag by using

      del flag_values_object.<flag_name>

    E.g.,

      gflags.DEFINE_integer('foo', 1, 'Integer flag.')
      del gflags.FLAGS.foo

    Args:
      flag_name: A string, the name of the flag to be deleted.

    Raises:
      AttributeError: When there is no registered flag named flag_name.
    """
    fl = self.FlagDict()
    if flag_name not in fl:
      raise AttributeError(flag_name)

    flag_obj = fl[flag_name]
    del fl[flag_name]

    if not self._FlagIsRegistered(flag_obj):
      # If the Flag object indicated by flag_name is no longer
      # registered (please see the docstring of _FlagIsRegistered), then
      # we delete the occurrences of the flag object in all our internal
      # dictionaries.
      self.__RemoveFlagFromDictByModule(self.FlagsByModuleDict(), flag_obj)
      self.__RemoveFlagFromDictByModule(self.FlagsByModuleIdDict(), flag_obj)
      self.__RemoveFlagFromDictByModule(self.KeyFlagsByModuleDict(), flag_obj)

  def __RemoveFlagFromDictByModule(self, flags_by_module_dict, flag_obj):
    """Removes a flag object from a module -> list of flags dictionary.

    Args:
      flags_by_module_dict: A dictionary that maps module names to lists of
        flags.
      flag_obj: A flag object.
    """
    for unused_module, flags_in_module in flags_by_module_dict.iteritems():
      # while (as opposed to if) takes care of multiple occurrences of a
      # flag in the list for the same module.
      while flag_obj in flags_in_module:
        flags_in_module.remove(flag_obj)

  def SetDefault(self, name, value):
    """Changes the default value of the named flag object."""
    fl = self.FlagDict()
    if name not in fl:
      raise AttributeError(name)
    fl[name].SetDefault(value)
    self._AssertValidators(fl[name].validators)

  def __contains__(self, name):
    """Returns True if name is a value (flag) in the dict."""
    return name in self.FlagDict()

  has_key = __contains__  # a synonym for __contains__()

  def __iter__(self):
    return iter(self.FlagDict())

  def __call__(self, argv):
    """Parses flags from argv; stores parsed flags into this FlagValues object.

    All unparsed arguments are returned.  Flags are parsed using the GNU
    Program Argument Syntax Conventions, using getopt:

    http://www.gnu.org/software/libc/manual/html_mono/libc.html#Getopt

    Args:
       argv: argument list. Can be of any type that may be converted to a list.

    Returns:
       The list of arguments not parsed as options, including argv[0]

    Raises:
       FlagsError: on any parsing error
    """
    # Support any sequence type that can be converted to a list
    argv = list(argv)

    shortopts = ""
    longopts = []

    fl = self.FlagDict()

    # This pre parses the argv list for --flagfile=<> options.
    argv = argv[:1] + self.ReadFlagsFromFiles(argv[1:], force_gnu=False)

    # Correct the argv to support the google style of passing boolean
    # parameters.  Boolean parameters may be passed by using --mybool,
    # --nomybool, --mybool=(true|false|1|0).  getopt does not support
    # having options that may or may not have a parameter.  We replace
    # instances of the short form --mybool and --nomybool with their
    # full forms: --mybool=(true|false).
    original_argv = list(argv)  # list() makes a copy
    shortest_matches = None
    for name, flag in fl.items():
      if not flag.boolean:
        continue
      if shortest_matches is None:
        # Determine the smallest allowable prefix for all flag names
        shortest_matches = self.ShortestUniquePrefixes(fl)
      no_name = 'no' + name
      prefix = shortest_matches[name]
      no_prefix = shortest_matches[no_name]

      # Replace all occurrences of this boolean with extended forms
      for arg_idx in range(1, len(argv)):
        arg = argv[arg_idx]
        if arg.find('=') >= 0: continue
        if arg.startswith('--'+prefix) and ('--'+name).startswith(arg):
          argv[arg_idx] = ('--%s=true' % name)
        elif arg.startswith('--'+no_prefix) and ('--'+no_name).startswith(arg):
          argv[arg_idx] = ('--%s=false' % name)

    # Loop over all of the flags, building up the lists of short options
    # and long options that will be passed to getopt.  Short options are
    # specified as a string of letters, each letter followed by a colon
    # if it takes an argument.  Long options are stored in an array of
    # strings.  Each string ends with an '=' if it takes an argument.
    for name, flag in fl.items():
      longopts.append(name + "=")
      if len(name) == 1:  # one-letter option: allow short flag type also
        shortopts += name
        if not flag.boolean:
          shortopts += ":"

    longopts.append('undefok=')
    undefok_flags = []

    # In case --undefok is specified, loop to pick up unrecognized
    # options one by one.
    unrecognized_opts = []
    args = argv[1:]
    while True:
      try:
        if self.__dict__['__use_gnu_getopt']:
          optlist, unparsed_args = getopt.gnu_getopt(args, shortopts, longopts)
        else:
          optlist, unparsed_args = getopt.getopt(args, shortopts, longopts)
        break
      except getopt.GetoptError, e:
        if not e.opt or e.opt in fl:
          # Not an unrecognized option, re-raise the exception as a FlagsError
          raise FlagsError(e)
        # Remove offender from args and try again
        for arg_index in range(len(args)):
          if ((args[arg_index] == '--' + e.opt) or
              (args[arg_index] == '-' + e.opt) or
              (args[arg_index].startswith('--' + e.opt + '='))):
            unrecognized_opts.append((e.opt, args[arg_index]))
            args = args[0:arg_index] + args[arg_index+1:]
            break
        else:
          # We should have found the option, so we don't expect to get
          # here.  We could assert, but raising the original exception
          # might work better.
          raise FlagsError(e)

    for name, arg in optlist:
      if name == '--undefok':
        flag_names = arg.split(',')
        undefok_flags.extend(flag_names)
        # For boolean flags, if --undefok=boolflag is specified, then we should
        # also accept --noboolflag, in addition to --boolflag.
        # Since we don't know the type of the undefok'd flag, this will affect
        # non-boolean flags as well.
        # NOTE: You shouldn't use --undefok=noboolflag, because then we will
        # accept --nonoboolflag here.  We are choosing not to do the conversion
        # from noboolflag -> boolflag because of the ambiguity that flag names
        # can start with 'no'.
        undefok_flags.extend('no' + name for name in flag_names)
        continue
      if name.startswith('--'):
        # long option
        name = name[2:]
        short_option = 0
      else:
        # short option
        name = name[1:]
        short_option = 1
      if name in fl:
        flag = fl[name]
        if flag.boolean and short_option: arg = 1
        flag.Parse(arg)

    # If there were unrecognized options, raise an exception unless
    # the options were named via --undefok.
    for opt, value in unrecognized_opts:
      if opt not in undefok_flags:
        raise UnrecognizedFlagError(opt, value)

    if unparsed_args:
      if self.__dict__['__use_gnu_getopt']:
        # if using gnu_getopt just return the program name + remainder of argv.
        ret_val = argv[:1] + unparsed_args
      else:
        # unparsed_args becomes the first non-flag detected by getopt to
        # the end of argv.  Because argv may have been modified above,
        # return original_argv for this region.
        ret_val = argv[:1] + original_argv[-len(unparsed_args):]
    else:
      ret_val = argv[:1]

    self._AssertAllValidators()
    return ret_val

  def Reset(self):
    """Resets the values to the point before FLAGS(argv) was called."""
    for f in self.FlagDict().values():
      f.Unparse()

  def RegisteredFlags(self):
    """Returns: a list of the names and short names of all registered flags."""
    return list(self.FlagDict())

  def FlagValuesDict(self):
    """Returns: a dictionary that maps flag names to flag values."""
    flag_values = {}

    for flag_name in self.RegisteredFlags():
      flag = self.FlagDict()[flag_name]
      flag_values[flag_name] = flag.value

    return flag_values

  def __str__(self):
    """Generates a help string for all known flags."""
    return self.GetHelp()

  def GetHelp(self, prefix=''):
    """Generates a help string for all known flags."""
    helplist = []

    flags_by_module = self.FlagsByModuleDict()
    if flags_by_module:

      modules = sorted(flags_by_module)

      # Print the help for the main module first, if possible.
      main_module = _GetMainModule()
      if main_module in modules:
        modules.remove(main_module)
        modules = [main_module] + modules

      for module in modules:
        self.__RenderOurModuleFlags(module, helplist)

      self.__RenderModuleFlags('gflags',
                               _SPECIAL_FLAGS.FlagDict().values(),
                               helplist)

    else:
      # Just print one long list of flags.
      self.__RenderFlagList(
          self.FlagDict().values() + _SPECIAL_FLAGS.FlagDict().values(),
          helplist, prefix)

    return '\n'.join(helplist)

  def __RenderModuleFlags(self, module, flags, output_lines, prefix=""):
    """Generates a help string for a given module."""
    if not isinstance(module, str):
      module = module.__name__
    output_lines.append('\n%s%s:' % (prefix, module))
    self.__RenderFlagList(flags, output_lines, prefix + "  ")

  def __RenderOurModuleFlags(self, module, output_lines, prefix=""):
    """Generates a help string for a given module."""
    flags = self._GetFlagsDefinedByModule(module)
    if flags:
      self.__RenderModuleFlags(module, flags, output_lines, prefix)

  def __RenderOurModuleKeyFlags(self, module, output_lines, prefix=""):
    """Generates a help string for the key flags of a given module.

    Args:
      module: A module object or a module name (a string).
      output_lines: A list of strings.  The generated help message
        lines will be appended to this list.
      prefix: A string that is prepended to each generated help line.
    """
    key_flags = self._GetKeyFlagsForModule(module)
    if key_flags:
      self.__RenderModuleFlags(module, key_flags, output_lines, prefix)

  def ModuleHelp(self, module):
    """Describe the key flags of a module.

    Args:
      module: A module object or a module name (a string).

    Returns:
      string describing the key flags of a module.
    """
    helplist = []
    self.__RenderOurModuleKeyFlags(module, helplist)
    return '\n'.join(helplist)

  def MainModuleHelp(self):
    """Describe the key flags of the main module.

    Returns:
      string describing the key flags of a module.
    """
    return self.ModuleHelp(_GetMainModule())

  def __RenderFlagList(self, flaglist, output_lines, prefix="  "):
    fl = self.FlagDict()
    special_fl = _SPECIAL_FLAGS.FlagDict()
    flaglist = [(flag.name, flag) for flag in flaglist]
    flaglist.sort()
    flagset = {}
    for (name, flag) in flaglist:
      # It's possible this flag got deleted or overridden since being
      # registered in the per-module flaglist.  Check now against the
      # canonical source of current flag information, the FlagDict.
      if fl.get(name, None) != flag and special_fl.get(name, None) != flag:
        # a different flag is using this name now
        continue
      # only print help once
      if flag in flagset: continue
      flagset[flag] = 1
      flaghelp = ""
      if flag.short_name: flaghelp += "-%s," % flag.short_name
      if flag.boolean:
        flaghelp += "--[no]%s" % flag.name + ":"
      else:
        flaghelp += "--%s" % flag.name + ":"
      flaghelp += "  "
      if flag.help:
        flaghelp += flag.help
      flaghelp = TextWrap(flaghelp, indent=prefix+"  ",
                          firstline_indent=prefix)
      if flag.default_as_str:
        flaghelp += "\n"
        flaghelp += TextWrap("(default: %s)" % flag.default_as_str,
                             indent=prefix+"  ")
      if flag.parser.syntactic_help:
        flaghelp += "\n"
        flaghelp += TextWrap("(%s)" % flag.parser.syntactic_help,
                             indent=prefix+"  ")
      output_lines.append(flaghelp)

  def get(self, name, default):
    """Returns the value of a flag (if not None) or a default value.

    Args:
      name: A string, the name of a flag.
      default: Default value to use if the flag value is None.
    """

    value = self.__getattr__(name)
    if value is not None:  # Can't do if not value, b/c value might be '0' or ""
      return value
    else:
      return default

  def ShortestUniquePrefixes(self, fl):
    """Returns: dictionary; maps flag names to their shortest unique prefix."""
    # Sort the list of flag names
    sorted_flags = []
    for name, flag in fl.items():
      sorted_flags.append(name)
      if flag.boolean:
        sorted_flags.append('no%s' % name)
    sorted_flags.sort()

    # For each name in the sorted list, determine the shortest unique
    # prefix by comparing itself to the next name and to the previous
    # name (the latter check uses cached info from the previous loop).
    shortest_matches = {}
    prev_idx = 0
    for flag_idx in range(len(sorted_flags)):
      curr = sorted_flags[flag_idx]
      if flag_idx == (len(sorted_flags) - 1):
        next = None
      else:
        next = sorted_flags[flag_idx+1]
        next_len = len(next)
      for curr_idx in range(len(curr)):
        if (next is None
            or curr_idx >= next_len
            or curr[curr_idx] != next[curr_idx]):
          # curr longer than next or no more chars in common
          shortest_matches[curr] = curr[:max(prev_idx, curr_idx) + 1]
          prev_idx = curr_idx
          break
      else:
        # curr shorter than (or equal to) next
        shortest_matches[curr] = curr
        prev_idx = curr_idx + 1  # next will need at least one more char
    return shortest_matches

  def __IsFlagFileDirective(self, flag_string):
    """Checks whether flag_string contain a --flagfile=<foo> directive."""
    if isinstance(flag_string, type("")):
      if flag_string.startswith('--flagfile='):
        return 1
      elif flag_string == '--flagfile':
        return 1
      elif flag_string.startswith('-flagfile='):
        return 1
      elif flag_string == '-flagfile':
        return 1
      else:
        return 0
    return 0

  def ExtractFilename(self, flagfile_str):
    """Returns filename from a flagfile_str of form -[-]flagfile=filename.

    The cases of --flagfile foo and -flagfile foo shouldn't be hitting
    this function, as they are dealt with in the level above this
    function.
    """
    if flagfile_str.startswith('--flagfile='):
      return os.path.expanduser((flagfile_str[(len('--flagfile=')):]).strip())
    elif flagfile_str.startswith('-flagfile='):
      return os.path.expanduser((flagfile_str[(len('-flagfile=')):]).strip())
    else:
      raise FlagsError('Hit illegal --flagfile type: %s' % flagfile_str)

  def __GetFlagFileLines(self, filename, parsed_file_list):
    """Returns the useful (!=comments, etc) lines from a file with flags.

    Args:
      filename: A string, the name of the flag file.
      parsed_file_list: A list of the names of the files we have
        already read.  MUTATED BY THIS FUNCTION.

    Returns:
      List of strings. See the note below.

    NOTE(springer): This function checks for a nested --flagfile=<foo>
    tag and handles the lower file recursively. It returns a list of
    all the lines that _could_ contain command flags. This is
    EVERYTHING except whitespace lines and comments (lines starting
    with '#' or '//').
    """
    line_list = []  # All line from flagfile.
    flag_line_list = []  # Subset of lines w/o comments, blanks, flagfile= tags.
    try:
      file_obj = open(filename, 'r')
    except IOError, e_msg:
      raise CantOpenFlagFileError('ERROR:: Unable to open flagfile: %s' % e_msg)

    line_list = file_obj.readlines()
    file_obj.close()
    parsed_file_list.append(filename)

    # This is where we check each line in the file we just read.
    for line in line_list:
      if line.isspace():
        pass
      # Checks for comment (a line that starts with '#').
      elif line.startswith('#') or line.startswith('//'):
        pass
      # Checks for a nested "--flagfile=<bar>" flag in the current file.
      # If we find one, recursively parse down into that file.
      elif self.__IsFlagFileDirective(line):
        sub_filename = self.ExtractFilename(line)
        # We do a little safety check for reparsing a file we've already done.
        if not sub_filename in parsed_file_list:
          included_flags = self.__GetFlagFileLines(sub_filename,
                                                   parsed_file_list)
          flag_line_list.extend(included_flags)
        else:  # Case of hitting a circularly included file.
          sys.stderr.write('Warning: Hit circular flagfile dependency: %s\n' %
                           (sub_filename,))
      else:
        # Any line that's not a comment or a nested flagfile should get
        # copied into 2nd position.  This leaves earlier arguments
        # further back in the list, thus giving them higher priority.
        flag_line_list.append(line.strip())
    return flag_line_list

  def ReadFlagsFromFiles(self, argv, force_gnu=True):
    """Processes command line args, but also allow args to be read from file.

    Args:
      argv: A list of strings, usually sys.argv[1:], which may contain one or
        more flagfile directives of the form --flagfile="./filename".
        Note that the name of the program (sys.argv[0]) should be omitted.
      force_gnu: If False, --flagfile parsing obeys normal flag semantics.
        If True, --flagfile parsing instead follows gnu_getopt semantics.
        *** WARNING *** force_gnu=False may become the future default!

    Returns:

      A new list which has the original list combined with what we read
      from any flagfile(s).

    References: Global gflags.FLAG class instance.

    This function should be called before the normal FLAGS(argv) call.
    This function scans the input list for a flag that looks like:
    --flagfile=<somefile>. Then it opens <somefile>, reads all valid key
    and value pairs and inserts them into the input list between the
    first item of the list and any subsequent items in the list.

    Note that your application's flags are still defined the usual way
    using gflags DEFINE_flag() type functions.

    Notes (assuming we're getting a commandline of some sort as our input):
    --> Flags from the command line argv _should_ always take precedence!
    --> A further "--flagfile=<otherfile.cfg>" CAN be nested in a flagfile.
        It will be processed after the parent flag file is done.
    --> For duplicate flags, first one we hit should "win".
    --> In a flagfile, a line beginning with # or // is a comment.
    --> Entirely blank lines _should_ be ignored.
    """
    parsed_file_list = []
    rest_of_args = argv
    new_argv = []
    while rest_of_args:
      current_arg = rest_of_args[0]
      rest_of_args = rest_of_args[1:]
      if self.__IsFlagFileDirective(current_arg):
        # This handles the case of -(-)flagfile foo.  In this case the
        # next arg really is part of this one.
        if current_arg == '--flagfile' or current_arg == '-flagfile':
          if not rest_of_args:
            raise IllegalFlagValue('--flagfile with no argument')
          flag_filename = os.path.expanduser(rest_of_args[0])
          rest_of_args = rest_of_args[1:]
        else:
          # This handles the case of (-)-flagfile=foo.
          flag_filename = self.ExtractFilename(current_arg)
        new_argv.extend(
            self.__GetFlagFileLines(flag_filename, parsed_file_list))
      else:
        new_argv.append(current_arg)
        # Stop parsing after '--', like getopt and gnu_getopt.
        if current_arg == '--':
          break
        # Stop parsing after a non-flag, like getopt.
        if not current_arg.startswith('-'):
          if not force_gnu and not self.__dict__['__use_gnu_getopt']:
            break

    if rest_of_args:
      new_argv.extend(rest_of_args)

    return new_argv

  def FlagsIntoString(self):
    """Returns a string with the flags assignments from this FlagValues object.

    This function ignores flags whose value is None.  Each flag
    assignment is separated by a newline.

    NOTE: MUST mirror the behavior of the C++ CommandlineFlagsIntoString
    from http://code.google.com/p/google-gflags
    """
    s = ''
    for flag in self.FlagDict().values():
      if flag.value is not None:
        s += flag.Serialize() + '\n'
    return s

  def AppendFlagsIntoFile(self, filename):
    """Appends all flags assignments from this FlagInfo object to a file.

    Output will be in the format of a flagfile.

    NOTE: MUST mirror the behavior of the C++ AppendFlagsIntoFile
    from http://code.google.com/p/google-gflags
    """
    out_file = open(filename, 'a')
    out_file.write(self.FlagsIntoString())
    out_file.close()

  def WriteHelpInXMLFormat(self, outfile=None):
    """Outputs flag documentation in XML format.

    NOTE: We use element names that are consistent with those used by
    the C++ command-line flag library, from
    http://code.google.com/p/google-gflags
    We also use a few new elements (e.g., <key>), but we do not
    interfere / overlap with existing XML elements used by the C++
    library.  Please maintain this consistency.

    Args:
      outfile: File object we write to.  Default None means sys.stdout.
    """
    outfile = outfile or sys.stdout

    outfile.write('<?xml version=\"1.0\"?>\n')
    outfile.write('<AllFlags>\n')
    indent = '  '
    _WriteSimpleXMLElement(outfile, 'program', os.path.basename(sys.argv[0]),
                           indent)

    usage_doc = sys.modules['__main__'].__doc__
    if not usage_doc:
      usage_doc = '\nUSAGE: %s [flags]\n' % sys.argv[0]
    else:
      usage_doc = usage_doc.replace('%s', sys.argv[0])
    _WriteSimpleXMLElement(outfile, 'usage', usage_doc, indent)

    # Get list of key flags for the main module.
    key_flags = self._GetKeyFlagsForModule(_GetMainModule())

    # Sort flags by declaring module name and next by flag name.
    flags_by_module = self.FlagsByModuleDict()
    all_module_names = list(flags_by_module.keys())
    all_module_names.sort()
    for module_name in all_module_names:
      flag_list = [(f.name, f) for f in flags_by_module[module_name]]
      flag_list.sort()
      for unused_flag_name, flag in flag_list:
        is_key = flag in key_flags
        flag.WriteInfoInXMLFormat(outfile, module_name,
                                  is_key=is_key, indent=indent)

    outfile.write('</AllFlags>\n')
    outfile.flush()

  def AddValidator(self, validator):
    """Register new flags validator to be checked.

    Args:
      validator: gflags_validators.Validator
    Raises:
      AttributeError: if validators work with a non-existing flag.
    """
    for flag_name in validator.GetFlagsNames():
      flag = self.FlagDict()[flag_name]
      flag.validators.append(validator)

# end of FlagValues definition


# The global FlagValues instance
FLAGS = FlagValues()


def _StrOrUnicode(value):
  """Converts value to a python string or, if necessary, unicode-string."""
  try:
    return str(value)
  except UnicodeEncodeError:
    return unicode(value)


def _MakeXMLSafe(s):
  """Escapes <, >, and & from s, and removes XML 1.0-illegal chars."""
  s = cgi.escape(s)  # Escape <, >, and &
  # Remove characters that cannot appear in an XML 1.0 document
  # (http://www.w3.org/TR/REC-xml/#charsets).
  #
  # NOTE: if there are problems with current solution, one may move to
  # XML 1.1, which allows such chars, if they're entity-escaped (&#xHH;).
  s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)
  # Convert non-ascii characters to entities.  Note: requires python >=2.3
  s = s.encode('ascii', 'xmlcharrefreplace')   # u'\xce\x88' -> 'u&#904;'
  return s


def _WriteSimpleXMLElement(outfile, name, value, indent):
  """Writes a simple XML element.

  Args:
    outfile: File object we write the XML element to.
    name: A string, the name of XML element.
    value: A Python object, whose string representation will be used
      as the value of the XML element.
    indent: A string, prepended to each line of generated output.
  """
  value_str = _StrOrUnicode(value)
  if isinstance(value, bool):
    # Display boolean values as the C++ flag library does: no caps.
    value_str = value_str.lower()
  safe_value_str = _MakeXMLSafe(value_str)
  outfile.write('%s<%s>%s</%s>\n' % (indent, name, safe_value_str, name))


class Flag:
  """Information about a command-line flag.

  'Flag' objects define the following fields:
    .name  - the name for this flag
    .default - the default value for this flag
    .default_as_str - default value as repr'd string, e.g., "'true'" (or None)
    .value  - the most recent parsed value of this flag; set by Parse()
    .help  - a help string or None if no help is available
    .short_name  - the single letter alias for this flag (or None)
    .boolean  - if 'true', this flag does not accept arguments
    .present  - true if this flag was parsed from command line flags.
    .parser  - an ArgumentParser object
    .serializer - an ArgumentSerializer object
    .allow_override - the flag may be redefined without raising an error

  The only public method of a 'Flag' object is Parse(), but it is
  typically only called by a 'FlagValues' object.  The Parse() method is
  a thin wrapper around the 'ArgumentParser' Parse() method.  The parsed
  value is saved in .value, and the .present attribute is updated.  If
  this flag was already present, a FlagsError is raised.

  Parse() is also called during __init__ to parse the default value and
  initialize the .value attribute.  This enables other python modules to
  safely use flags even if the __main__ module neglects to parse the
  command line arguments.  The .present attribute is cleared after
  __init__ parsing.  If the default value is set to None, then the
  __init__ parsing step is skipped and the .value attribute is
  initialized to None.

  Note: The default value is also presented to the user in the help
  string, so it is important that it be a legal value for this flag.
  """

  def __init__(self, parser, serializer, name, default, help_string,
               short_name=None, boolean=0, allow_override=0):
    self.name = name

    if not help_string:
      help_string = '(no help available)'

    self.help = help_string
    self.short_name = short_name
    self.boolean = boolean
    self.present = 0
    self.parser = parser
    self.serializer = serializer
    self.allow_override = allow_override
    self.value = None
    self.validators = []

    self.SetDefault(default)

  def __hash__(self):
    return hash(id(self))

  def __eq__(self, other):
    return self is other

  def __lt__(self, other):
    if isinstance(other, Flag):
      return id(self) < id(other)
    return NotImplemented

  def __GetParsedValueAsString(self, value):
    if value is None:
      return None
    if self.serializer:
      return repr(self.serializer.Serialize(value))
    if self.boolean:
      if value:
        return repr('true')
      else:
        return repr('false')
    return repr(_StrOrUnicode(value))

  def Parse(self, argument):
    try:
      self.value = self.parser.Parse(argument)
    except ValueError, e:  # recast ValueError as IllegalFlagValue
      raise IllegalFlagValue("flag --%s=%s: %s" % (self.name, argument, e))
    self.present += 1

  def Unparse(self):
    if self.default is None:
      self.value = None
    else:
      self.Parse(self.default)
    self.present = 0

  def Serialize(self):
    if self.value is None:
      return ''
    if self.boolean:
      if self.value:
        return "--%s" % self.name
      else:
        return "--no%s" % self.name
    else:
      if not self.serializer:
        raise FlagsError("Serializer not present for flag %s" % self.name)
      return "--%s=%s" % (self.name, self.serializer.Serialize(self.value))

  def SetDefault(self, value):
    """Changes the default value (and current value too) for this Flag."""
    # We can't allow a None override because it may end up not being
    # passed to C++ code when we're overriding C++ flags.  So we
    # cowardly bail out until someone fixes the semantics of trying to
    # pass None to a C++ flag.  See swig_flags.Init() for details on
    # this behavior.
    # TODO(olexiy): Users can directly call this method, bypassing all flags
    # validators (we don't have FlagValues here, so we can not check
    # validators).
    # The simplest solution I see is to make this method private.
    # Another approach would be to store reference to the corresponding
    # FlagValues with each flag, but this seems to be an overkill.
    if value is None and self.allow_override:
      raise DuplicateFlagCannotPropagateNoneToSwig(self.name)

    self.default = value
    self.Unparse()
    self.default_as_str = self.__GetParsedValueAsString(self.value)

  def Type(self):
    """Returns: a string that describes the type of this Flag."""
    # NOTE: we use strings, and not the types.*Type constants because
    # our flags can have more exotic types, e.g., 'comma separated list
    # of strings', 'whitespace separated list of strings', etc.
    return self.parser.Type()

  def WriteInfoInXMLFormat(self, outfile, module_name, is_key=False, indent=''):
    """Writes common info about this flag, in XML format.

    This is information that is relevant to all flags (e.g., name,
    meaning, etc.).  If you defined a flag that has some other pieces of
    info, then please override _WriteCustomInfoInXMLFormat.

    Please do NOT override this method.

    Args:
      outfile: File object we write to.
      module_name: A string, the name of the module that defines this flag.
      is_key: A boolean, True iff this flag is key for main module.
      indent: A string that is prepended to each generated line.
    """
    outfile.write(indent + '<flag>\n')
    inner_indent = indent + '  '
    if is_key:
      _WriteSimpleXMLElement(outfile, 'key', 'yes', inner_indent)
    _WriteSimpleXMLElement(outfile, 'file', module_name, inner_indent)
    # Print flag features that are relevant for all flags.
    _WriteSimpleXMLElement(outfile, 'name', self.name, inner_indent)
    if self.short_name:
      _WriteSimpleXMLElement(outfile, 'short_name', self.short_name,
                             inner_indent)
    if self.help:
      _WriteSimpleXMLElement(outfile, 'meaning', self.help, inner_indent)
    # The default flag value can either be represented as a string like on the
    # command line, or as a Python object.  We serialize this value in the
    # latter case in order to remain consistent.
    if self.serializer and not isinstance(self.default, str):
      default_serialized = self.serializer.Serialize(self.default)
    else:
      default_serialized = self.default
    _WriteSimpleXMLElement(outfile, 'default', default_serialized, inner_indent)
    _WriteSimpleXMLElement(outfile, 'current', self.value, inner_indent)
    _WriteSimpleXMLElement(outfile, 'type', self.Type(), inner_indent)
    # Print extra flag features this flag may have.
    self._WriteCustomInfoInXMLFormat(outfile, inner_indent)
    outfile.write(indent + '</flag>\n')

  def _WriteCustomInfoInXMLFormat(self, outfile, indent):
    """Writes extra info about this flag, in XML format.

    "Extra" means "not already printed by WriteInfoInXMLFormat above."

    Args:
      outfile: File object we write to.
      indent: A string that is prepended to each generated line.
    """
    # Usually, the parser knows the extra details about the flag, so
    # we just forward the call to it.
    self.parser.WriteCustomInfoInXMLFormat(outfile, indent)
# End of Flag definition


class _ArgumentParserCache(type):
  """Metaclass used to cache and share argument parsers among flags."""

  _instances = {}

  def __call__(mcs, *args, **kwargs):
    """Returns an instance of the argument parser cls.

    This method overrides behavior of the __new__ methods in
    all subclasses of ArgumentParser (inclusive). If an instance
    for mcs with the same set of arguments exists, this instance is
    returned, otherwise a new instance is created.

    If any keyword arguments are defined, or the values in args
    are not hashable, this method always returns a new instance of
    cls.

    Args:
      args: Positional initializer arguments.
      kwargs: Initializer keyword arguments.

    Returns:
      An instance of cls, shared or new.
    """
    if kwargs:
      return type.__call__(mcs, *args, **kwargs)
    else:
      instances = mcs._instances
      key = (mcs,) + tuple(args)
      try:
        return instances[key]
      except KeyError:
        # No cache entry for key exists, create a new one.
        return instances.setdefault(key, type.__call__(mcs, *args))
      except TypeError:
        # An object in args cannot be hashed, always return
        # a new instance.
        return type.__call__(mcs, *args)


class ArgumentParser(object):
  """Base class used to parse and convert arguments.

  The Parse() method checks to make sure that the string argument is a
  legal value and convert it to a native type.  If the value cannot be
  converted, it should throw a 'ValueError' exception with a human
  readable explanation of why the value is illegal.

  Subclasses should also define a syntactic_help string which may be
  presented to the user to describe the form of the legal values.

  Argument parser classes must be stateless, since instances are cached
  and shared between flags. Initializer arguments are allowed, but all
  member variables must be derived from initializer arguments only.
  """
  __metaclass__ = _ArgumentParserCache

  syntactic_help = ""

  def Parse(self, argument):
    """Default implementation: always returns its argument unmodified."""
    return argument

  def Type(self):
    return 'string'

  def WriteCustomInfoInXMLFormat(self, outfile, indent):
    pass


class ArgumentSerializer:
  """Base class for generating string representations of a flag value."""

  def Serialize(self, value):
    return _StrOrUnicode(value)


class ListSerializer(ArgumentSerializer):

  def __init__(self, list_sep):
    self.list_sep = list_sep

  def Serialize(self, value):
    return self.list_sep.join([_StrOrUnicode(x) for x in value])


# Flags validators


def RegisterValidator(flag_name,
                      checker,
                      message='Flag validation failed',
                      flag_values=FLAGS):
  """Adds a constraint, which will be enforced during program execution.

  The constraint is validated when flags are initially parsed, and after each
  change of the corresponding flag's value.
  Args:
    flag_name: string, name of the flag to be checked.
    checker: method to validate the flag.
      input  - value of the corresponding flag (string, boolean, etc.
        This value will be passed to checker by the library). See file's
        docstring for examples.
      output - Boolean.
        Must return True if validator constraint is satisfied.
        If constraint is not satisfied, it should either return False or
          raise gflags_validators.Error(desired_error_message).
    message: error text to be shown to the user if checker returns False.
      If checker raises gflags_validators.Error, message from the raised
        Error will be shown.
    flag_values: FlagValues
  Raises:
    AttributeError: if flag_name is not registered as a valid flag name.
  """
  flag_values.AddValidator(gflags_validators.SimpleValidator(flag_name,
                                                            checker,
                                                            message))


def MarkFlagAsRequired(flag_name, flag_values=FLAGS):
  """Ensure that flag is not None during program execution.

  Registers a flag validator, which will follow usual validator
  rules.
  Args:
    flag_name: string, name of the flag
    flag_values: FlagValues
  Raises:
    AttributeError: if flag_name is not registered as a valid flag name.
  """
  RegisterValidator(flag_name,
                    lambda value: value is not None,
                    message='Flag --%s must be specified.' % flag_name,
                    flag_values=flag_values)


def _RegisterBoundsValidatorIfNeeded(parser, name, flag_values):
  """Enforce lower and upper bounds for numeric flags.

  Args:
    parser: NumericParser (either FloatParser or IntegerParser). Provides lower
      and upper bounds, and help text to display.
    name: string, name of the flag
    flag_values: FlagValues
  """
  if parser.lower_bound is not None or parser.upper_bound is not None:

    def Checker(value):
      if value is not None and parser.IsOutsideBounds(value):
        message = '%s is not %s' % (value, parser.syntactic_help)
        raise gflags_validators.Error(message)
      return True

    RegisterValidator(name,
                      Checker,
                      flag_values=flag_values)


# The DEFINE functions are explained in mode details in the module doc string.


def DEFINE(parser, name, default, help, flag_values=FLAGS, serializer=None,
           **args):
  """Registers a generic Flag object.

  NOTE: in the docstrings of all DEFINE* functions, "registers" is short
  for "creates a new flag and registers it".

  Auxiliary function: clients should use the specialized DEFINE_<type>
  function instead.

  Args:
    parser: ArgumentParser that is used to parse the flag arguments.
    name: A string, the flag name.
    default: The default value of the flag.
    help: A help string.
    flag_values: FlagValues object the flag will be registered with.
    serializer: ArgumentSerializer that serializes the flag value.
    args: Dictionary with extra keyword args that are passes to the
      Flag __init__.
  """
  DEFINE_flag(Flag(parser, serializer, name, default, help, **args),
              flag_values)


def DEFINE_flag(flag, flag_values=FLAGS):
  """Registers a 'Flag' object with a 'FlagValues' object.

  By default, the global FLAGS 'FlagValue' object is used.

  Typical users will use one of the more specialized DEFINE_xxx
  functions, such as DEFINE_string or DEFINE_integer.  But developers
  who need to create Flag objects themselves should use this function
  to register their flags.
  """
  # copying the reference to flag_values prevents pychecker warnings
  fv = flag_values
  fv[flag.name] = flag
  # Tell flag_values who's defining the flag.
  if isinstance(flag_values, FlagValues):
    # Regarding the above isinstance test: some users pass funny
    # values of flag_values (e.g., {}) in order to avoid the flag
    # registration (in the past, there used to be a flag_values ==
    # FLAGS test here) and redefine flags with the same name (e.g.,
    # debug).  To avoid breaking their code, we perform the
    # registration only if flag_values is a real FlagValues object.
    module, module_name = _GetCallingModuleObjectAndName()
    flag_values._RegisterFlagByModule(module_name, flag)
    flag_values._RegisterFlagByModuleId(id(module), flag)


def _InternalDeclareKeyFlags(flag_names,
                             flag_values=FLAGS, key_flag_values=None):
  """Declares a flag as key for the calling module.

  Internal function.  User code should call DECLARE_key_flag or
  ADOPT_module_key_flags instead.

  Args:
    flag_names: A list of strings that are names of already-registered
      Flag objects.
    flag_values: A FlagValues object that the flags listed in
      flag_names have registered with (the value of the flag_values
      argument from the DEFINE_* calls that defined those flags).
      This should almost never need to be overridden.
    key_flag_values: A FlagValues object that (among possibly many
      other things) keeps track of the key flags for each module.
      Default None means "same as flag_values".  This should almost
      never need to be overridden.

  Raises:
    UnrecognizedFlagError: when we refer to a flag that was not
      defined yet.
  """
  key_flag_values = key_flag_values or flag_values

  module = _GetCallingModule()

  for flag_name in flag_names:
    if flag_name not in flag_values:
      raise UnrecognizedFlagError(flag_name)
    flag = flag_values.FlagDict()[flag_name]
    key_flag_values._RegisterKeyFlagForModule(module, flag)


def DECLARE_key_flag(flag_name, flag_values=FLAGS):
  """Declares one flag as key to the current module.

  Key flags are flags that are deemed really important for a module.
  They are important when listing help messages; e.g., if the
  --helpshort command-line flag is used, then only the key flags of the
  main module are listed (instead of all flags, as in the case of
  --help).

  Sample usage:

    gflags.DECLARED_key_flag('flag_1')

  Args:
    flag_name: A string, the name of an already declared flag.
      (Redeclaring flags as key, including flags implicitly key
      because they were declared in this module, is a no-op.)
    flag_values: A FlagValues object.  This should almost never
      need to be overridden.
  """
  if flag_name in _SPECIAL_FLAGS:
    # Take care of the special flags, e.g., --flagfile, --undefok.
    # These flags are defined in _SPECIAL_FLAGS, and are treated
    # specially during flag parsing, taking precedence over the
    # user-defined flags.
    _InternalDeclareKeyFlags([flag_name],
                             flag_values=_SPECIAL_FLAGS,
                             key_flag_values=flag_values)
    return
  _InternalDeclareKeyFlags([flag_name], flag_values=flag_values)


def ADOPT_module_key_flags(module, flag_values=FLAGS):
  """Declares that all flags key to a module are key to the current module.

  Args:
    module: A module object.
    flag_values: A FlagValues object.  This should almost never need
      to be overridden.

  Raises:
    FlagsError: When given an argument that is a module name (a
    string), instead of a module object.
  """
  # NOTE(salcianu): an even better test would be if not
  # isinstance(module, types.ModuleType) but I didn't want to import
  # types for such a tiny use.
  if isinstance(module, str):
    raise FlagsError('Received module name %s; expected a module object.'
                     % module)
  _InternalDeclareKeyFlags(
      [f.name for f in flag_values._GetKeyFlagsForModule(module.__name__)],
      flag_values=flag_values)
  # If module is this flag module, take _SPECIAL_FLAGS into account.
  if module == _GetThisModuleObjectAndName()[0]:
    _InternalDeclareKeyFlags(
        # As we associate flags with _GetCallingModuleObjectAndName(), the
        # special flags defined in this module are incorrectly registered with
        # a different module.  So, we can't use _GetKeyFlagsForModule.
        # Instead, we take all flags from _SPECIAL_FLAGS (a private
        # FlagValues, where no other module should register flags).
        [f.name for f in _SPECIAL_FLAGS.FlagDict().values()],
        flag_values=_SPECIAL_FLAGS,
        key_flag_values=flag_values)


#
# STRING FLAGS
#


def DEFINE_string(name, default, help, flag_values=FLAGS, **args):
  """Registers a flag whose value can be any string."""
  parser = ArgumentParser()
  serializer = ArgumentSerializer()
  DEFINE(parser, name, default, help, flag_values, serializer, **args)


#
# BOOLEAN FLAGS
#


class BooleanParser(ArgumentParser):
  """Parser of boolean values."""

  def Convert(self, argument):
    """Converts the argument to a boolean; raise ValueError on errors."""
    if type(argument) == str:
      if argument.lower() in ['true', 't', '1']:
        return True
      elif argument.lower() in ['false', 'f', '0']:
        return False

    bool_argument = bool(argument)
    if argument == bool_argument:
      # The argument is a valid boolean (True, False, 0, or 1), and not just
      # something that always converts to bool (list, string, int, etc.).
      return bool_argument

    raise ValueError('Non-boolean argument to boolean flag', argument)

  def Parse(self, argument):
    val = self.Convert(argument)
    return val

  def Type(self):
    return 'bool'


class BooleanFlag(Flag):
  """Basic boolean flag.

  Boolean flags do not take any arguments, and their value is either
  True (1) or False (0).  The false value is specified on the command
  line by prepending the word 'no' to either the long or the short flag
  name.

  For example, if a Boolean flag was created whose long name was
  'update' and whose short name was 'x', then this flag could be
  explicitly unset through either --noupdate or --nox.
  """

  def __init__(self, name, default, help, short_name=None, **args):
    p = BooleanParser()
    Flag.__init__(self, p, None, name, default, help, short_name, 1, **args)
    if not self.help: self.help = "a boolean value"


def DEFINE_boolean(name, default, help, flag_values=FLAGS, **args):
  """Registers a boolean flag.

  Such a boolean flag does not take an argument.  If a user wants to
  specify a false value explicitly, the long option beginning with 'no'
  must be used: i.e. --noflag

  This flag will have a value of None, True or False.  None is possible
  if default=None and the user does not specify the flag on the command
  line.
  """
  DEFINE_flag(BooleanFlag(name, default, help, **args), flag_values)


# Match C++ API to unconfuse C++ people.
DEFINE_bool = DEFINE_boolean


class HelpFlag(BooleanFlag):
  """
  HelpFlag is a special boolean flag that prints usage information and
  raises a SystemExit exception if it is ever found in the command
  line arguments.  Note this is called with allow_override=1, so other
  apps can define their own --help flag, replacing this one, if they want.
  """
  def __init__(self):
    BooleanFlag.__init__(self, "help", 0, "show this help",
                         short_name="?", allow_override=1)
  def Parse(self, arg):
    if arg:
      doc = sys.modules["__main__"].__doc__
      flags = str(FLAGS)
      print doc or ("\nUSAGE: %s [flags]\n" % sys.argv[0])
      if flags:
        print "flags:"
        print flags
      sys.exit(1)
class HelpXMLFlag(BooleanFlag):
  """Similar to HelpFlag, but generates output in XML format."""
  def __init__(self):
    BooleanFlag.__init__(self, 'helpxml', False,
                         'like --help, but generates XML output',
                         allow_override=1)
  def Parse(self, arg):
    if arg:
      FLAGS.WriteHelpInXMLFormat(sys.stdout)
      sys.exit(1)
class HelpshortFlag(BooleanFlag):
  """
  HelpshortFlag is a special boolean flag that prints usage
  information for the "main" module, and rasies a SystemExit exception
  if it is ever found in the command line arguments.  Note this is
  called with allow_override=1, so other apps can define their own
  --helpshort flag, replacing this one, if they want.
  """
  def __init__(self):
    BooleanFlag.__init__(self, "helpshort", 0,
                         "show usage only for this module", allow_override=1)
  def Parse(self, arg):
    if arg:
      doc = sys.modules["__main__"].__doc__
      flags = FLAGS.MainModuleHelp()
      print doc or ("\nUSAGE: %s [flags]\n" % sys.argv[0])
      if flags:
        print "flags:"
        print flags
      sys.exit(1)

#
# Numeric parser - base class for Integer and Float parsers
#


class NumericParser(ArgumentParser):
  """Parser of numeric values.

  Parsed value may be bounded to a given upper and lower bound.
  """

  def IsOutsideBounds(self, val):
    return ((self.lower_bound is not None and val < self.lower_bound) or
            (self.upper_bound is not None and val > self.upper_bound))

  def Parse(self, argument):
    val = self.Convert(argument)
    if self.IsOutsideBounds(val):
      raise ValueError("%s is not %s" % (val, self.syntactic_help))
    return val

  def WriteCustomInfoInXMLFormat(self, outfile, indent):
    if self.lower_bound is not None:
      _WriteSimpleXMLElement(outfile, 'lower_bound', self.lower_bound, indent)
    if self.upper_bound is not None:
      _WriteSimpleXMLElement(outfile, 'upper_bound', self.upper_bound, indent)

  def Convert(self, argument):
    """Default implementation: always returns its argument unmodified."""
    return argument

# End of Numeric Parser

#
# FLOAT FLAGS
#


class FloatParser(NumericParser):
  """Parser of floating point values.

  Parsed value may be bounded to a given upper and lower bound.
  """
  number_article = "a"
  number_name = "number"
  syntactic_help = " ".join((number_article, number_name))

  def __init__(self, lower_bound=None, upper_bound=None):
    super(FloatParser, self).__init__()
    self.lower_bound = lower_bound
    self.upper_bound = upper_bound
    sh = self.syntactic_help
    if lower_bound is not None and upper_bound is not None:
      sh = ("%s in the range [%s, %s]" % (sh, lower_bound, upper_bound))
    elif lower_bound == 0:
      sh = "a non-negative %s" % self.number_name
    elif upper_bound == 0:
      sh = "a non-positive %s" % self.number_name
    elif upper_bound is not None:
      sh = "%s <= %s" % (self.number_name, upper_bound)
    elif lower_bound is not None:
      sh = "%s >= %s" % (self.number_name, lower_bound)
    self.syntactic_help = sh

  def Convert(self, argument):
    """Converts argument to a float; raises ValueError on errors."""
    return float(argument)

  def Type(self):
    return 'float'
# End of FloatParser


def DEFINE_float(name, default, help, lower_bound=None, upper_bound=None,
                 flag_values=FLAGS, **args):
  """Registers a flag whose value must be a float.

  If lower_bound or upper_bound are set, then this flag must be
  within the given range.
  """
  parser = FloatParser(lower_bound, upper_bound)
  serializer = ArgumentSerializer()
  DEFINE(parser, name, default, help, flag_values, serializer, **args)
  _RegisterBoundsValidatorIfNeeded(parser, name, flag_values=flag_values)

#
# INTEGER FLAGS
#


class IntegerParser(NumericParser):
  """Parser of an integer value.

  Parsed value may be bounded to a given upper and lower bound.
  """
  number_article = "an"
  number_name = "integer"
  syntactic_help = " ".join((number_article, number_name))

  def __init__(self, lower_bound=None, upper_bound=None):
    super(IntegerParser, self).__init__()
    self.lower_bound = lower_bound
    self.upper_bound = upper_bound
    sh = self.syntactic_help
    if lower_bound is not None and upper_bound is not None:
      sh = ("%s in the range [%s, %s]" % (sh, lower_bound, upper_bound))
    elif lower_bound == 1:
      sh = "a positive %s" % self.number_name
    elif upper_bound == -1:
      sh = "a negative %s" % self.number_name
    elif lower_bound == 0:
      sh = "a non-negative %s" % self.number_name
    elif upper_bound == 0:
      sh = "a non-positive %s" % self.number_name
    elif upper_bound is not None:
      sh = "%s <= %s" % (self.number_name, upper_bound)
    elif lower_bound is not None:
      sh = "%s >= %s" % (self.number_name, lower_bound)
    self.syntactic_help = sh

  def Convert(self, argument):
    __pychecker__ = 'no-returnvalues'
    if type(argument) == str:
      base = 10
      if len(argument) > 2 and argument[0] == "0" and argument[1] == "x":
        base = 16
      return int(argument, base)
    else:
      return int(argument)

  def Type(self):
    return 'int'


def DEFINE_integer(name, default, help, lower_bound=None, upper_bound=None,
                   flag_values=FLAGS, **args):
  """Registers a flag whose value must be an integer.

  If lower_bound, or upper_bound are set, then this flag must be
  within the given range.
  """
  parser = IntegerParser(lower_bound, upper_bound)
  serializer = ArgumentSerializer()
  DEFINE(parser, name, default, help, flag_values, serializer, **args)
  _RegisterBoundsValidatorIfNeeded(parser, name, flag_values=flag_values)


#
# ENUM FLAGS
#


class EnumParser(ArgumentParser):
  """Parser of a string enum value (a string value from a given set).

  If enum_values (see below) is not specified, any string is allowed.
  """

  def __init__(self, enum_values=None):
    super(EnumParser, self).__init__()
    self.enum_values = enum_values

  def Parse(self, argument):
    if self.enum_values and argument not in self.enum_values:
      raise ValueError("value should be one of <%s>" %
                       "|".join(self.enum_values))
    return argument

  def Type(self):
    return 'string enum'


class EnumFlag(Flag):
  """Basic enum flag; its value can be any string from list of enum_values."""

  def __init__(self, name, default, help, enum_values=None,
               short_name=None, **args):
    enum_values = enum_values or []
    p = EnumParser(enum_values)
    g = ArgumentSerializer()
    Flag.__init__(self, p, g, name, default, help, short_name, **args)
    if not self.help: self.help = "an enum string"
    self.help = "<%s>: %s" % ("|".join(enum_values), self.help)

  def _WriteCustomInfoInXMLFormat(self, outfile, indent):
    for enum_value in self.parser.enum_values:
      _WriteSimpleXMLElement(outfile, 'enum_value', enum_value, indent)


def DEFINE_enum(name, default, enum_values, help, flag_values=FLAGS,
                **args):
  """Registers a flag whose value can be any string from enum_values."""
  DEFINE_flag(EnumFlag(name, default, help, enum_values, ** args),
              flag_values)


#
# LIST FLAGS
#


class BaseListParser(ArgumentParser):
  """Base class for a parser of lists of strings.

  To extend, inherit from this class; from the subclass __init__, call

    BaseListParser.__init__(self, token, name)

  where token is a character used to tokenize, and name is a description
  of the separator.
  """

  def __init__(self, token=None, name=None):
    assert name
    super(BaseListParser, self).__init__()
    self._token = token
    self._name = name
    self.syntactic_help = "a %s separated list" % self._name

  def Parse(self, argument):
    if isinstance(argument, list):
      return argument
    elif argument == '':
      return []
    else:
      return [s.strip() for s in argument.split(self._token)]

  def Type(self):
    return '%s separated list of strings' % self._name


class ListParser(BaseListParser):
  """Parser for a comma-separated list of strings."""

  def __init__(self):
    BaseListParser.__init__(self, ',', 'comma')

  def WriteCustomInfoInXMLFormat(self, outfile, indent):
    BaseListParser.WriteCustomInfoInXMLFormat(self, outfile, indent)
    _WriteSimpleXMLElement(outfile, 'list_separator', repr(','), indent)


class WhitespaceSeparatedListParser(BaseListParser):
  """Parser for a whitespace-separated list of strings."""

  def __init__(self):
    BaseListParser.__init__(self, None, 'whitespace')

  def WriteCustomInfoInXMLFormat(self, outfile, indent):
    BaseListParser.WriteCustomInfoInXMLFormat(self, outfile, indent)
    separators = list(string.whitespace)
    separators.sort()
    for ws_char in string.whitespace:
      _WriteSimpleXMLElement(outfile, 'list_separator', repr(ws_char), indent)


def DEFINE_list(name, default, help, flag_values=FLAGS, **args):
  """Registers a flag whose value is a comma-separated list of strings."""
  parser = ListParser()
  serializer = ListSerializer(',')
  DEFINE(parser, name, default, help, flag_values, serializer, **args)


def DEFINE_spaceseplist(name, default, help, flag_values=FLAGS, **args):
  """Registers a flag whose value is a whitespace-separated list of strings.

  Any whitespace can be used as a separator.
  """
  parser = WhitespaceSeparatedListParser()
  serializer = ListSerializer(' ')
  DEFINE(parser, name, default, help, flag_values, serializer, **args)


#
# MULTI FLAGS
#


class MultiFlag(Flag):
  """A flag that can appear multiple time on the command-line.

  The value of such a flag is a list that contains the individual values
  from all the appearances of that flag on the command-line.

  See the __doc__ for Flag for most behavior of this class.  Only
  differences in behavior are described here:

    * The default value may be either a single value or a list of values.
      A single value is interpreted as the [value] singleton list.

    * The value of the flag is always a list, even if the option was
      only supplied once, and even if the default value is a single
      value
  """

  def __init__(self, *args, **kwargs):
    Flag.__init__(self, *args, **kwargs)
    self.help += ';\n    repeat this option to specify a list of values'

  def Parse(self, arguments):
    """Parses one or more arguments with the installed parser.

    Args:
      arguments: a single argument or a list of arguments (typically a
        list of default values); a single argument is converted
        internally into a list containing one item.
    """
    if not isinstance(arguments, list):
      # Default value may be a list of values.  Most other arguments
      # will not be, so convert them into a single-item list to make
      # processing simpler below.
      arguments = [arguments]

    if self.present:
      # keep a backup reference to list of previously supplied option values
      values = self.value
    else:
      # "erase" the defaults with an empty list
      values = []

    for item in arguments:
      # have Flag superclass parse argument, overwriting self.value reference
      Flag.Parse(self, item)  # also increments self.present
      values.append(self.value)

    # put list of option values back in the 'value' attribute
    self.value = values

  def Serialize(self):
    if not self.serializer:
      raise FlagsError("Serializer not present for flag %s" % self.name)
    if self.value is None:
      return ''

    s = ''

    multi_value = self.value

    for self.value in multi_value:
      if s: s += ' '
      s += Flag.Serialize(self)

    self.value = multi_value

    return s

  def Type(self):
    return 'multi ' + self.parser.Type()


def DEFINE_multi(parser, serializer, name, default, help, flag_values=FLAGS,
                 **args):
  """Registers a generic MultiFlag that parses its args with a given parser.

  Auxiliary function.  Normal users should NOT use it directly.

  Developers who need to create their own 'Parser' classes for options
  which can appear multiple times can call this module function to
  register their flags.
  """
  DEFINE_flag(MultiFlag(parser, serializer, name, default, help, **args),
              flag_values)


def DEFINE_multistring(name, default, help, flag_values=FLAGS, **args):
  """Registers a flag whose value can be a list of any strings.

  Use the flag on the command line multiple times to place multiple
  string values into the list.  The 'default' may be a single string
  (which will be converted into a single-element list) or a list of
  strings.
  """
  parser = ArgumentParser()
  serializer = ArgumentSerializer()
  DEFINE_multi(parser, serializer, name, default, help, flag_values, **args)


def DEFINE_multi_int(name, default, help, lower_bound=None, upper_bound=None,
                     flag_values=FLAGS, **args):
  """Registers a flag whose value can be a list of arbitrary integers.

  Use the flag on the command line multiple times to place multiple
  integer values into the list.  The 'default' may be a single integer
  (which will be converted into a single-element list) or a list of
  integers.
  """
  parser = IntegerParser(lower_bound, upper_bound)
  serializer = ArgumentSerializer()
  DEFINE_multi(parser, serializer, name, default, help, flag_values, **args)


def DEFINE_multi_float(name, default, help, lower_bound=None, upper_bound=None,
                       flag_values=FLAGS, **args):
  """Registers a flag whose value can be a list of arbitrary floats.

  Use the flag on the command line multiple times to place multiple
  float values into the list.  The 'default' may be a single float
  (which will be converted into a single-element list) or a list of
  floats.
  """
  parser = FloatParser(lower_bound, upper_bound)
  serializer = ArgumentSerializer()
  DEFINE_multi(parser, serializer, name, default, help, flag_values, **args)


# Now register the flags that we want to exist in all applications.
# These are all defined with allow_override=1, so user-apps can use
# these flagnames for their own purposes, if they want.
DEFINE_flag(HelpFlag())
DEFINE_flag(HelpshortFlag())
DEFINE_flag(HelpXMLFlag())

# Define special flags here so that help may be generated for them.
# NOTE: Please do NOT use _SPECIAL_FLAGS from outside this module.
_SPECIAL_FLAGS = FlagValues()


DEFINE_string(
    'flagfile', "",
    "Insert flag definitions from the given file into the command line.",
    _SPECIAL_FLAGS)

DEFINE_string(
    'undefok', "",
    "comma-separated list of flag names that it is okay to specify "
    "on the command line even if the program does not define a flag "
    "with that name.  IMPORTANT: flags in this list that have "
    "arguments MUST use the --flag=value format.", _SPECIAL_FLAGS)

########NEW FILE########
__FILENAME__ = gflags2man
#!/usr/bin/env python

# Copyright (c) 2006, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


"""gflags2man runs a Google flags base program and generates a man page.

Run the program, parse the output, and then format that into a man
page.

Usage:
  gflags2man <program> [program] ...
"""

# TODO(csilvers): work with windows paths (\) as well as unix (/)

# This may seem a bit of an end run, but it:  doesn't bloat flags, can
# support python/java/C++, supports older executables, and can be
# extended to other document formats.
# Inspired by help2man.



import os
import re
import sys
import stat
import time

import gflags

_VERSION = '0.1'


def _GetDefaultDestDir():
  home = os.environ.get('HOME', '')
  homeman = os.path.join(home, 'man', 'man1')
  if home and os.path.exists(homeman):
    return homeman
  else:
    return os.environ.get('TMPDIR', '/tmp')

FLAGS = gflags.FLAGS
gflags.DEFINE_string('dest_dir', _GetDefaultDestDir(),
                    'Directory to write resulting manpage to.'
                    ' Specify \'-\' for stdout')
gflags.DEFINE_string('help_flag', '--help',
                    'Option to pass to target program in to get help')
gflags.DEFINE_integer('v', 0, 'verbosity level to use for output')


_MIN_VALID_USAGE_MSG = 9         # if fewer lines than this, help is suspect


class Logging:
  """A super-simple logging class"""
  def error(self, msg): print >>sys.stderr, "ERROR: ", msg
  def warn(self, msg): print >>sys.stderr, "WARNING: ", msg
  def info(self, msg): print msg
  def debug(self, msg): self.vlog(1, msg)
  def vlog(self, level, msg):
    if FLAGS.v >= level: print msg
logging = Logging()
class App:
  def usage(self, shorthelp=0):
    print >>sys.stderr, __doc__
    print >>sys.stderr, "flags:"
    print >>sys.stderr, str(FLAGS)
  def run(self):
    main(sys.argv)
app = App()


def GetRealPath(filename):
  """Given an executable filename, find in the PATH or find absolute path.
  Args:
    filename  An executable filename (string)
  Returns:
    Absolute version of filename.
    None if filename could not be found locally, absolutely, or in PATH
  """
  if os.path.isabs(filename):                # already absolute
    return filename

  if filename.startswith('./') or  filename.startswith('../'): # relative
    return os.path.abspath(filename)

  path = os.getenv('PATH', '')
  for directory in path.split(':'):
    tryname = os.path.join(directory, filename)
    if os.path.exists(tryname):
      if not os.path.isabs(directory):  # relative directory
        return os.path.abspath(tryname)
      return tryname
  if os.path.exists(filename):
    return os.path.abspath(filename)
  return None                         # could not determine

class Flag(object):
  """The information about a single flag."""

  def __init__(self, flag_desc, help):
    """Create the flag object.
    Args:
      flag_desc  The command line forms this could take. (string)
      help       The help text (string)
    """
    self.desc = flag_desc               # the command line forms
    self.help = help                    # the help text
    self.default = ''                   # default value
    self.tips = ''                      # parsing/syntax tips


class ProgramInfo(object):
  """All the information gleaned from running a program with --help."""

  # Match a module block start, for python scripts --help
  # "goopy.logging:"
  module_py_re = re.compile(r'(\S.+):$')
  # match the start of a flag listing
  # " -v,--verbosity:  Logging verbosity"
  flag_py_re         = re.compile(r'\s+(-\S+):\s+(.*)$')
  # "   (default: '0')"
  flag_default_py_re = re.compile(r'\s+\(default:\s+\'(.*)\'\)$')
  # "   (an integer)"
  flag_tips_py_re    = re.compile(r'\s+\((.*)\)$')

  # Match a module block start, for c++ programs --help
  # "google/base/commandlineflags":
  module_c_re = re.compile(r'\s+Flags from (\S.+):$')
  # match the start of a flag listing
  # " -v,--verbosity:  Logging verbosity"
  flag_c_re         = re.compile(r'\s+(-\S+)\s+(.*)$')

  # Match a module block start, for java programs --help
  # "com.google.common.flags"
  module_java_re = re.compile(r'\s+Flags for (\S.+):$')
  # match the start of a flag listing
  # " -v,--verbosity:  Logging verbosity"
  flag_java_re         = re.compile(r'\s+(-\S+)\s+(.*)$')

  def __init__(self, executable):
    """Create object with executable.
    Args:
      executable  Program to execute (string)
    """
    self.long_name = executable
    self.name = os.path.basename(executable)  # name
    # Get name without extension (PAR files)
    (self.short_name, self.ext) = os.path.splitext(self.name)
    self.executable = GetRealPath(executable)  # name of the program
    self.output = []          # output from the program.  List of lines.
    self.desc = []            # top level description.  List of lines
    self.modules = {}         # { section_name(string), [ flags ] }
    self.module_list = []     # list of module names in their original order
    self.date = time.localtime(time.time())   # default date info

  def Run(self):
    """Run it and collect output.

    Returns:
      1 (true)   If everything went well.
      0 (false)  If there were problems.
    """
    if not self.executable:
      logging.error('Could not locate "%s"' % self.long_name)
      return 0

    finfo = os.stat(self.executable)
    self.date = time.localtime(finfo[stat.ST_MTIME])

    logging.info('Running: %s %s </dev/null 2>&1'
                 % (self.executable, FLAGS.help_flag))
    # --help output is often routed to stderr, so we combine with stdout.
    # Re-direct stdin to /dev/null to encourage programs that
    # don't understand --help to exit.
    (child_stdin, child_stdout_and_stderr) = os.popen4(
      [self.executable, FLAGS.help_flag])
    child_stdin.close()       # '</dev/null'
    self.output = child_stdout_and_stderr.readlines()
    child_stdout_and_stderr.close()
    if len(self.output) < _MIN_VALID_USAGE_MSG:
      logging.error('Error: "%s %s" returned only %d lines: %s'
                    % (self.name, FLAGS.help_flag,
                       len(self.output), self.output))
      return 0
    return 1

  def Parse(self):
    """Parse program output."""
    (start_line, lang) = self.ParseDesc()
    if start_line < 0:
      return
    if 'python' == lang:
      self.ParsePythonFlags(start_line)
    elif 'c' == lang:
      self.ParseCFlags(start_line)
    elif 'java' == lang:
      self.ParseJavaFlags(start_line)

  def ParseDesc(self, start_line=0):
    """Parse the initial description.

    This could be Python or C++.

    Returns:
      (start_line, lang_type)
        start_line  Line to start parsing flags on (int)
        lang_type   Either 'python' or 'c'
       (-1, '')  if the flags start could not be found
    """
    exec_mod_start = self.executable + ':'

    after_blank = 0
    start_line = 0             # ignore the passed-in arg for now (?)
    for start_line in range(start_line, len(self.output)): # collect top description
      line = self.output[start_line].rstrip()
      # Python flags start with 'flags:\n'
      if ('flags:' == line
          and len(self.output) > start_line+1
          and '' == self.output[start_line+1].rstrip()):
        start_line += 2
        logging.debug('Flags start (python): %s' % line)
        return (start_line, 'python')
      # SWIG flags just have the module name followed by colon.
      if exec_mod_start == line:
        logging.debug('Flags start (swig): %s' % line)
        return (start_line, 'python')
      # C++ flags begin after a blank line and with a constant string
      if after_blank and line.startswith('  Flags from '):
        logging.debug('Flags start (c): %s' % line)
        return (start_line, 'c')
      # java flags begin with a constant string
      if line == 'where flags are':
        logging.debug('Flags start (java): %s' % line)
        start_line += 2                        # skip "Standard flags:"
        return (start_line, 'java')

      logging.debug('Desc: %s' % line)
      self.desc.append(line)
      after_blank = (line == '')
    else:
      logging.warn('Never found the start of the flags section for "%s"!'
                   % self.long_name)
      return (-1, '')

  def ParsePythonFlags(self, start_line=0):
    """Parse python/swig style flags."""
    modname = None                      # name of current module
    modlist = []
    flag = None
    for line_num in range(start_line, len(self.output)): # collect flags
      line = self.output[line_num].rstrip()
      if not line:                      # blank
        continue

      mobj = self.module_py_re.match(line)
      if mobj:                          # start of a new module
        modname = mobj.group(1)
        logging.debug('Module: %s' % line)
        if flag:
          modlist.append(flag)
        self.module_list.append(modname)
        self.modules.setdefault(modname, [])
        modlist = self.modules[modname]
        flag = None
        continue

      mobj = self.flag_py_re.match(line)
      if mobj:                          # start of a new flag
        if flag:
          modlist.append(flag)
        logging.debug('Flag: %s' % line)
        flag = Flag(mobj.group(1),  mobj.group(2))
        continue

      if not flag:                    # continuation of a flag
        logging.error('Flag info, but no current flag "%s"' % line)
      mobj = self.flag_default_py_re.match(line)
      if mobj:                          # (default: '...')
        flag.default = mobj.group(1)
        logging.debug('Fdef: %s' % line)
        continue
      mobj = self.flag_tips_py_re.match(line)
      if mobj:                          # (tips)
        flag.tips = mobj.group(1)
        logging.debug('Ftip: %s' % line)
        continue
      if flag and flag.help:
        flag.help += line              # multiflags tack on an extra line
      else:
        logging.info('Extra: %s' % line)
    if flag:
      modlist.append(flag)

  def ParseCFlags(self, start_line=0):
    """Parse C style flags."""
    modname = None                      # name of current module
    modlist = []
    flag = None
    for line_num in range(start_line, len(self.output)):  # collect flags
      line = self.output[line_num].rstrip()
      if not line:                      # blank lines terminate flags
        if flag:                        # save last flag
          modlist.append(flag)
          flag = None
        continue

      mobj = self.module_c_re.match(line)
      if mobj:                          # start of a new module
        modname = mobj.group(1)
        logging.debug('Module: %s' % line)
        if flag:
          modlist.append(flag)
        self.module_list.append(modname)
        self.modules.setdefault(modname, [])
        modlist = self.modules[modname]
        flag = None
        continue

      mobj = self.flag_c_re.match(line)
      if mobj:                          # start of a new flag
        if flag:                        # save last flag
          modlist.append(flag)
        logging.debug('Flag: %s' % line)
        flag = Flag(mobj.group(1),  mobj.group(2))
        continue

      # append to flag help.  type and default are part of the main text
      if flag:
        flag.help += ' ' + line.strip()
      else:
        logging.info('Extra: %s' % line)
    if flag:
      modlist.append(flag)

  def ParseJavaFlags(self, start_line=0):
    """Parse Java style flags (com.google.common.flags)."""
    # The java flags prints starts with a "Standard flags" "module"
    # that doesn't follow the standard module syntax.
    modname = 'Standard flags'          # name of current module
    self.module_list.append(modname)
    self.modules.setdefault(modname, [])
    modlist = self.modules[modname]
    flag = None

    for line_num in range(start_line, len(self.output)): # collect flags
      line = self.output[line_num].rstrip()
      logging.vlog(2, 'Line: "%s"' % line)
      if not line:                      # blank lines terminate module
        if flag:                        # save last flag
          modlist.append(flag)
          flag = None
        continue

      mobj = self.module_java_re.match(line)
      if mobj:                          # start of a new module
        modname = mobj.group(1)
        logging.debug('Module: %s' % line)
        if flag:
          modlist.append(flag)
        self.module_list.append(modname)
        self.modules.setdefault(modname, [])
        modlist = self.modules[modname]
        flag = None
        continue

      mobj = self.flag_java_re.match(line)
      if mobj:                          # start of a new flag
        if flag:                        # save last flag
          modlist.append(flag)
        logging.debug('Flag: %s' % line)
        flag = Flag(mobj.group(1),  mobj.group(2))
        continue

      # append to flag help.  type and default are part of the main text
      if flag:
        flag.help += ' ' + line.strip()
      else:
        logging.info('Extra: %s' % line)
    if flag:
      modlist.append(flag)

  def Filter(self):
    """Filter parsed data to create derived fields."""
    if not self.desc:
      self.short_desc = ''
      return

    for i in range(len(self.desc)):   # replace full path with name
      if self.desc[i].find(self.executable) >= 0:
        self.desc[i] = self.desc[i].replace(self.executable, self.name)

    self.short_desc = self.desc[0]
    word_list = self.short_desc.split(' ')
    all_names = [ self.name, self.short_name, ]
    # Since the short_desc is always listed right after the name,
    #  trim it from the short_desc
    while word_list and (word_list[0] in all_names
                         or word_list[0].lower() in all_names):
      del word_list[0]
      self.short_desc = ''              # signal need to reconstruct
    if not self.short_desc and word_list:
      self.short_desc = ' '.join(word_list)


class GenerateDoc(object):
  """Base class to output flags information."""

  def __init__(self, proginfo, directory='.'):
    """Create base object.
    Args:
      proginfo   A ProgramInfo object
      directory  Directory to write output into
    """
    self.info = proginfo
    self.dirname = directory

  def Output(self):
    """Output all sections of the page."""
    self.Open()
    self.Header()
    self.Body()
    self.Footer()

  def Open(self): raise NotImplementedError    # define in subclass
  def Header(self): raise NotImplementedError  # define in subclass
  def Body(self): raise NotImplementedError    # define in subclass
  def Footer(self): raise NotImplementedError  # define in subclass


class GenerateMan(GenerateDoc):
  """Output a man page."""

  def __init__(self, proginfo, directory='.'):
    """Create base object.
    Args:
      proginfo   A ProgramInfo object
      directory  Directory to write output into
    """
    GenerateDoc.__init__(self, proginfo, directory)

  def Open(self):
    if self.dirname == '-':
      logging.info('Writing to stdout')
      self.fp = sys.stdout
    else:
      self.file_path = '%s.1' % os.path.join(self.dirname, self.info.name)
      logging.info('Writing: %s' % self.file_path)
      self.fp = open(self.file_path, 'w')

  def Header(self):
    self.fp.write(
      '.\\" DO NOT MODIFY THIS FILE!  It was generated by gflags2man %s\n'
      % _VERSION)
    self.fp.write(
      '.TH %s "1" "%s" "%s" "User Commands"\n'
      % (self.info.name, time.strftime('%x', self.info.date), self.info.name))
    self.fp.write(
      '.SH NAME\n%s \\- %s\n' % (self.info.name, self.info.short_desc))
    self.fp.write(
      '.SH SYNOPSIS\n.B %s\n[\\fIFLAGS\\fR]...\n' % self.info.name)

  def Body(self):
    self.fp.write(
      '.SH DESCRIPTION\n.\\" Add any additional description here\n.PP\n')
    for ln in self.info.desc:
      self.fp.write('%s\n' % ln)
    self.fp.write(
      '.SH OPTIONS\n')
    # This shows flags in the original order
    for modname in self.info.module_list:
      if modname.find(self.info.executable) >= 0:
        mod = modname.replace(self.info.executable, self.info.name)
      else:
        mod = modname
      self.fp.write('\n.P\n.I %s\n' % mod)
      for flag in self.info.modules[modname]:
        help_string = flag.help
        if flag.default or flag.tips:
          help_string += '\n.br\n'
        if flag.default:
          help_string += '  (default: \'%s\')' % flag.default
        if flag.tips:
          help_string += '  (%s)' % flag.tips
        self.fp.write(
          '.TP\n%s\n%s\n' % (flag.desc, help_string))

  def Footer(self):
    self.fp.write(
      '.SH COPYRIGHT\nCopyright \(co %s Google.\n'
      % time.strftime('%Y', self.info.date))
    self.fp.write('Gflags2man created this page from "%s %s" output.\n'
                  % (self.info.name, FLAGS.help_flag))
    self.fp.write('\nGflags2man was written by Dan Christian. '
                  ' Note that the date on this'
                  ' page is the modification date of %s.\n' % self.info.name)


def main(argv):
  argv = FLAGS(argv)           # handles help as well
  if len(argv) <= 1:
    app.usage(shorthelp=1)
    return 1

  for arg in argv[1:]:
    prog = ProgramInfo(arg)
    if not prog.Run():
      continue
    prog.Parse()
    prog.Filter()
    doc = GenerateMan(prog, FLAGS.dest_dir)
    doc.Output()
  return 0

if __name__ == '__main__':
  app.run()

########NEW FILE########
__FILENAME__ = gflags_validators
#!/usr/bin/env python

# Copyright (c) 2010, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Module to enforce different constraints on flags.

A validator represents an invariant, enforced over a one or more flags.
See 'FLAGS VALIDATORS' in gflags.py's docstring for a usage manual.
"""

__author__ = 'olexiy@google.com (Olexiy Oryeshko)'


class Error(Exception):
  """Thrown If validator constraint is not satisfied."""


class Validator(object):
  """Base class for flags validators.

  Users should NOT overload these classes, and use gflags.Register...
  methods instead.
  """

  # Used to assign each validator an unique insertion_index
  validators_count = 0

  def __init__(self, checker, message):
    """Constructor to create all validators.

    Args:
      checker: function to verify the constraint.
        Input of this method varies, see SimpleValidator and
          DictionaryValidator for a detailed description.
      message: string, error message to be shown to the user
    """
    self.checker = checker
    self.message = message
    Validator.validators_count += 1
    # Used to assert validators in the order they were registered (CL/18694236)
    self.insertion_index = Validator.validators_count

  def Verify(self, flag_values):
    """Verify that constraint is satisfied.

    flags library calls this method to verify Validator's constraint.
    Args:
      flag_values: gflags.FlagValues, containing all flags
    Raises:
      Error: if constraint is not satisfied.
    """
    param = self._GetInputToCheckerFunction(flag_values)
    if not self.checker(param):
      raise Error(self.message)

  def GetFlagsNames(self):
    """Return the names of the flags checked by this validator.

    Returns:
      [string], names of the flags
    """
    raise NotImplementedError('This method should be overloaded')

  def PrintFlagsWithValues(self, flag_values):
    raise NotImplementedError('This method should be overloaded')

  def _GetInputToCheckerFunction(self, flag_values):
    """Given flag values, construct the input to be given to checker.

    Args:
      flag_values: gflags.FlagValues, containing all flags.
    Returns:
      Return type depends on the specific validator.
    """
    raise NotImplementedError('This method should be overloaded')


class SimpleValidator(Validator):
  """Validator behind RegisterValidator() method.

  Validates that a single flag passes its checker function. The checker function
  takes the flag value and returns True (if value looks fine) or, if flag value
  is not valid, either returns False or raises an Exception."""
  def __init__(self, flag_name, checker, message):
    """Constructor.

    Args:
      flag_name: string, name of the flag.
      checker: function to verify the validator.
        input  - value of the corresponding flag (string, boolean, etc).
        output - Boolean. Must return True if validator constraint is satisfied.
          If constraint is not satisfied, it should either return False or
          raise Error.
      message: string, error message to be shown to the user if validator's
        condition is not satisfied
    """
    super(SimpleValidator, self).__init__(checker, message)
    self.flag_name = flag_name

  def GetFlagsNames(self):
    return [self.flag_name]

  def PrintFlagsWithValues(self, flag_values):
    return 'flag --%s=%s' % (self.flag_name, flag_values[self.flag_name].value)

  def _GetInputToCheckerFunction(self, flag_values):
    """Given flag values, construct the input to be given to checker.

    Args:
      flag_values: gflags.FlagValues
    Returns:
      value of the corresponding flag.
    """
    return flag_values[self.flag_name].value


class DictionaryValidator(Validator):
  """Validator behind RegisterDictionaryValidator method.

  Validates that flag values pass their common checker function. The checker
  function takes flag values and returns True (if values look fine) or,
  if values are not valid, either returns False or raises an Exception.
  """
  def __init__(self, flag_names, checker, message):
    """Constructor.

    Args:
      flag_names: [string], containing names of the flags used by checker.
      checker: function to verify the validator.
        input  - dictionary, with keys() being flag_names, and value for each
          key being the value of the corresponding flag (string, boolean, etc).
        output - Boolean. Must return True if validator constraint is satisfied.
          If constraint is not satisfied, it should either return False or
          raise Error.
      message: string, error message to be shown to the user if validator's
        condition is not satisfied
    """
    super(DictionaryValidator, self).__init__(checker, message)
    self.flag_names = flag_names

  def _GetInputToCheckerFunction(self, flag_values):
    """Given flag values, construct the input to be given to checker.

    Args:
      flag_values: gflags.FlagValues
    Returns:
      dictionary, with keys() being self.lag_names, and value for each key
        being the value of the corresponding flag (string, boolean, etc).
    """
    return dict([key, flag_values[key].value] for key in self.flag_names)

  def PrintFlagsWithValues(self, flag_values):
    prefix = 'flags '
    flags_with_values = []
    for key in self.flag_names:
      flags_with_values.append('%s=%s' % (key, flag_values[key].value))
    return prefix + ', '.join(flags_with_values)

  def GetFlagsNames(self):
    return self.flag_names

########NEW FILE########
__FILENAME__ = module_bar
#!/usr/bin/env python

# Copyright (c) 2009, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


"""Auxiliary module for testing gflags.py.

The purpose of this module is to define a few flags.  We want to make
sure the unit tests for gflags.py involve more than one module.
"""

__author__ = 'salcianu@google.com (Alex Salcianu)'

__pychecker__ = 'no-local'  # for unittest

import gflags

FLAGS = gflags.FLAGS


def DefineFlags(flag_values=FLAGS):
  """Defines some flags.

  Args:
    flag_values: The FlagValues object we want to register the flags
      with.
  """
  # The 'tmod_bar_' prefix (short for 'test_module_bar') ensures there
  # is no name clash with the existing flags.
  gflags.DEFINE_boolean('tmod_bar_x', True, 'Boolean flag.',
                       flag_values=flag_values)
  gflags.DEFINE_string('tmod_bar_y', 'default', 'String flag.',
                      flag_values=flag_values)
  gflags.DEFINE_boolean('tmod_bar_z', False,
                       'Another boolean flag from module bar.',
                       flag_values=flag_values)
  gflags.DEFINE_integer('tmod_bar_t', 4, 'Sample int flag.',
                       flag_values=flag_values)
  gflags.DEFINE_integer('tmod_bar_u', 5, 'Sample int flag.',
                       flag_values=flag_values)
  gflags.DEFINE_integer('tmod_bar_v', 6, 'Sample int flag.',
                       flag_values=flag_values)


def RemoveOneFlag(flag_name, flag_values=FLAGS):
  """Removes the definition of one flag from gflags.FLAGS.

  Note: if the flag is not defined in gflags.FLAGS, this function does
  not do anything (in particular, it does not raise any exception).

  Motivation: We use this function for cleanup *after* a test: if
  there was a failure during a test and not all flags were declared,
  we do not want the cleanup code to crash.

  Args:
    flag_name: A string, the name of the flag to delete.
    flag_values: The FlagValues object we remove the flag from.
  """
  if flag_name in flag_values.FlagDict():
    flag_values.__delattr__(flag_name)


def NamesOfDefinedFlags():
  """Returns: List of names of the flags declared in this module."""
  return ['tmod_bar_x',
          'tmod_bar_y',
          'tmod_bar_z',
          'tmod_bar_t',
          'tmod_bar_u',
          'tmod_bar_v']


def RemoveFlags(flag_values=FLAGS):
  """Deletes the flag definitions done by the above DefineFlags().

  Args:
    flag_values: The FlagValues object we remove the flags from.
  """
  for flag_name in NamesOfDefinedFlags():
    RemoveOneFlag(flag_name, flag_values=flag_values)


def GetModuleName():
  """Uses gflags._GetCallingModule() to return the name of this module.

  For checking that _GetCallingModule works as expected.

  Returns:
    A string, the name of this module.
  """
  # Calling the protected _GetCallingModule generates a lint warning,
  # but we do not have any other alternative to test that function.
  return gflags._GetCallingModule()


def ExecuteCode(code, global_dict):
  """Executes some code in a given global environment.

  For testing of _GetCallingModule.

  Args:
    code: A string, the code to be executed.
    global_dict: A dictionary, the global environment that code should
      be executed in.
  """
  # Indeed, using exec generates a lint warning.  But some user code
  # actually uses exec, and we have to test for it ...
  exec code in global_dict

########NEW FILE########
__FILENAME__ = module_baz
#!/usr/bin/env python

# Copyright (c) 2009, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Auxiliary module for testing gflags.py.

The purpose of this module is to test the behavior of flags that are defined
before main() executes.
"""




import gflags

FLAGS = gflags.FLAGS

gflags.DEFINE_boolean('tmod_baz_x', True, 'Boolean flag.')

########NEW FILE########
__FILENAME__ = module_foo
#!/usr/bin/env python
#
# Copyright (c) 2009, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Auxiliary module for testing gflags.py.

The purpose of this module is to define a few flags, and declare some
other flags as being important.  We want to make sure the unit tests
for gflags.py involve more than one module.
"""

__author__ = 'salcianu@google.com (Alex Salcianu)'

__pychecker__ = 'no-local'  # for unittest

import gflags
from flags_modules_for_testing import module_bar

FLAGS = gflags.FLAGS


DECLARED_KEY_FLAGS = ['tmod_bar_x', 'tmod_bar_z', 'tmod_bar_t',
                      # Special (not user-defined) flag:
                      'flagfile']


def DefineFlags(flag_values=FLAGS):
  """Defines a few flags."""
  module_bar.DefineFlags(flag_values=flag_values)
  # The 'tmod_foo_' prefix (short for 'test_module_foo') ensures that we
  # have no name clash with existing flags.
  gflags.DEFINE_boolean('tmod_foo_bool', True, 'Boolean flag from module foo.',
                       flag_values=flag_values)
  gflags.DEFINE_string('tmod_foo_str', 'default', 'String flag.',
                      flag_values=flag_values)
  gflags.DEFINE_integer('tmod_foo_int', 3, 'Sample int flag.',
                       flag_values=flag_values)


def DeclareKeyFlags(flag_values=FLAGS):
  """Declares a few key flags."""
  for flag_name in DECLARED_KEY_FLAGS:
    gflags.DECLARE_key_flag(flag_name, flag_values=flag_values)


def DeclareExtraKeyFlags(flag_values=FLAGS):
  """Declares some extra key flags."""
  gflags.ADOPT_module_key_flags(module_bar, flag_values=flag_values)


def NamesOfDefinedFlags():
  """Returns: list of names of flags defined by this module."""
  return ['tmod_foo_bool', 'tmod_foo_str', 'tmod_foo_int']


def NamesOfDeclaredKeyFlags():
  """Returns: list of names of key flags for this module."""
  return NamesOfDefinedFlags() + DECLARED_KEY_FLAGS


def NamesOfDeclaredExtraKeyFlags():
  """Returns the list of names of additional key flags for this module.

  These are the flags that became key for this module only as a result
  of a call to DeclareExtraKeyFlags() above.  I.e., the flags declared
  by module_bar, that were not already declared as key for this
  module.

  Returns:
    The list of names of additional key flags for this module.
  """
  names_of_extra_key_flags = list(module_bar.NamesOfDefinedFlags())
  for flag_name in NamesOfDeclaredKeyFlags():
    while flag_name in names_of_extra_key_flags:
      names_of_extra_key_flags.remove(flag_name)
  return names_of_extra_key_flags


def RemoveFlags(flag_values=FLAGS):
  """Deletes the flag definitions done by the above DefineFlags()."""
  for flag_name in NamesOfDefinedFlags():
    module_bar.RemoveOneFlag(flag_name, flag_values=flag_values)
  module_bar.RemoveFlags(flag_values=flag_values)


def GetModuleName():
  """Uses gflags._GetCallingModule() to return the name of this module.

  For checking that _GetCallingModule works as expected.

  Returns:
    A string, the name of this module.
  """
  # Calling the protected _GetCallingModule generates a lint warning,
  # but we do not have any other alternative to test that function.
  return gflags._GetCallingModule()


def DuplicateFlags(flagnames=None):
  """Returns a new FlagValues object with the requested flagnames.

  Used to test DuplicateFlagError detection.

  Args:
    flagnames: str, A list of flag names to create.

  Returns:
    A FlagValues object with one boolean flag for each name in flagnames.
  """
  flag_values = gflags.FlagValues()
  for name in flagnames:
    gflags.DEFINE_boolean(name, False, 'Flag named %s' % (name,),
                         flag_values=flag_values)
  return flag_values

########NEW FILE########
__FILENAME__ = gflags_googletest
#!/usr/bin/env python

# Copyright (c) 2011, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Some simple additions to the unittest framework useful for gflags testing."""



import re
import unittest


def Sorted(lst):
  """Equivalent of sorted(), but not dependent on python version."""
  sorted_list = lst[:]
  sorted_list.sort()
  return sorted_list


def MultiLineEqual(expected, actual):
  """Returns True if expected == actual, or returns False and logs."""
  if actual == expected:
    return True

  print "Error: FLAGS.MainModuleHelp() didn't return the expected result."
  print "Got:"
  print actual
  print "[End of got]"

  actual_lines = actual.split("\n")
  expected_lines = expected.split("\n")

  num_actual_lines = len(actual_lines)
  num_expected_lines = len(expected_lines)

  if num_actual_lines != num_expected_lines:
    print "Number of actual lines = %d, expected %d" % (
        num_actual_lines, num_expected_lines)

  num_to_match = min(num_actual_lines, num_expected_lines)

  for i in range(num_to_match):
    if actual_lines[i] != expected_lines[i]:
      print "One discrepancy: Got:"
      print actual_lines[i]
      print "Expected:"
      print expected_lines[i]
      break
  else:
    # If we got here, found no discrepancy, print first new line.
    if num_actual_lines > num_expected_lines:
      print "New help line:"
      print actual_lines[num_expected_lines]
    elif num_expected_lines > num_actual_lines:
      print "Missing expected help line:"
      print expected_lines[num_actual_lines]
    else:
      print "Bug in this test -- discrepancy detected but not found."

  return False


class TestCase(unittest.TestCase):
  def assertListEqual(self, list1, list2):
    """Asserts that, when sorted, list1 and list2 are identical."""
    # This exists in python 2.7, but not previous versions.  Use the
    # built-in version if possible.
    if hasattr(unittest.TestCase, "assertListEqual"):
      unittest.TestCase.assertListEqual(self, Sorted(list1), Sorted(list2))
    else:
      self.assertEqual(Sorted(list1), Sorted(list2))

  def assertMultiLineEqual(self, expected, actual):
    # This exists in python 2.7, but not previous versions.  Use the
    # built-in version if possible.
    if hasattr(unittest.TestCase, "assertMultiLineEqual"):
      unittest.TestCase.assertMultiLineEqual(self, expected, actual)
    else:
      self.assertTrue(MultiLineEqual(expected, actual))

  def assertRaisesWithRegexpMatch(self, exception, regexp, fn, *args, **kwargs):
    try:
      fn(*args, **kwargs)
    except exception, why:
      self.assertTrue(re.search(regexp, str(why)),
                      "'%s' does not match '%s'" % (regexp, why))
      return
    self.fail(exception.__name__ + " not raised")


def main():
  unittest.main()

########NEW FILE########
__FILENAME__ = gflags_helpxml_test
#!/usr/bin/env python

# Copyright (c) 2009, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Unit tests for the XML-format help generated by the gflags.py module."""

__author__ = 'salcianu@google.com (Alex Salcianu)'


import string
import StringIO
import sys
import xml.dom.minidom
import xml.sax.saxutils
import gflags_googletest as googletest
import gflags
from flags_modules_for_testing import module_bar


class _MakeXMLSafeTest(googletest.TestCase):

  def _Check(self, s, expected_output):
    self.assertEqual(gflags._MakeXMLSafe(s), expected_output)

  def testMakeXMLSafe(self):
    self._Check('plain text', 'plain text')
    self._Check('(x < y) && (a >= b)',
                '(x &lt; y) &amp;&amp; (a &gt;= b)')
    # Some characters with ASCII code < 32 are illegal in XML 1.0 and
    # are removed by us.  However, '\n', '\t', and '\r' are legal.
    self._Check('\x09\x0btext \x02 with\x0dsome \x08 good & bad chars',
                '\ttext  with\rsome  good &amp; bad chars')


def _ListSeparatorsInXMLFormat(separators, indent=''):
  """Generates XML encoding of a list of list separators.

  Args:
    separators: A list of list separators.  Usually, this should be a
      string whose characters are the valid list separators, e.g., ','
      means that both comma (',') and space (' ') are valid list
      separators.
    indent: A string that is added at the beginning of each generated
      XML element.

  Returns:
    A string.
  """
  result = ''
  separators = list(separators)
  separators.sort()
  for sep_char in separators:
    result += ('%s<list_separator>%s</list_separator>\n' %
               (indent, repr(sep_char)))
  return result


class WriteFlagHelpInXMLFormatTest(googletest.TestCase):
  """Test the XML-format help for a single flag at a time.

  There is one test* method for each kind of DEFINE_* declaration.
  """

  def setUp(self):
    # self.fv is a FlagValues object, just like gflags.FLAGS.  Each
    # test registers one flag with this FlagValues.
    self.fv = gflags.FlagValues()

  def _CheckFlagHelpInXML(self, flag_name, module_name,
                          expected_output, is_key=False):
    # StringIO.StringIO is a file object that writes into a memory string.
    sio = StringIO.StringIO()
    flag_obj = self.fv[flag_name]
    flag_obj.WriteInfoInXMLFormat(sio, module_name, is_key=is_key, indent=' ')
    self.assertMultiLineEqual(sio.getvalue(), expected_output)
    sio.close()

  def testFlagHelpInXML_Int(self):
    gflags.DEFINE_integer('index', 17, 'An integer flag', flag_values=self.fv)
    expected_output_pattern = (
        ' <flag>\n'
        '   <file>module.name</file>\n'
        '   <name>index</name>\n'
        '   <meaning>An integer flag</meaning>\n'
        '   <default>17</default>\n'
        '   <current>%d</current>\n'
        '   <type>int</type>\n'
        ' </flag>\n')
    self._CheckFlagHelpInXML('index', 'module.name',
                             expected_output_pattern % 17)
    # Check that the output is correct even when the current value of
    # a flag is different from the default one.
    self.fv['index'].value = 20
    self._CheckFlagHelpInXML('index', 'module.name',
                             expected_output_pattern % 20)

  def testFlagHelpInXML_IntWithBounds(self):
    gflags.DEFINE_integer('nb_iters', 17, 'An integer flag',
                         lower_bound=5, upper_bound=27,
                         flag_values=self.fv)
    expected_output = (
        ' <flag>\n'
        '   <key>yes</key>\n'
        '   <file>module.name</file>\n'
        '   <name>nb_iters</name>\n'
        '   <meaning>An integer flag</meaning>\n'
        '   <default>17</default>\n'
        '   <current>17</current>\n'
        '   <type>int</type>\n'
        '   <lower_bound>5</lower_bound>\n'
        '   <upper_bound>27</upper_bound>\n'
        ' </flag>\n')
    self._CheckFlagHelpInXML('nb_iters', 'module.name',
                             expected_output, is_key=True)

  def testFlagHelpInXML_String(self):
    gflags.DEFINE_string('file_path', '/path/to/my/dir', 'A test string flag.',
                        flag_values=self.fv)
    expected_output = (
        ' <flag>\n'
        '   <file>simple_module</file>\n'
        '   <name>file_path</name>\n'
        '   <meaning>A test string flag.</meaning>\n'
        '   <default>/path/to/my/dir</default>\n'
        '   <current>/path/to/my/dir</current>\n'
        '   <type>string</type>\n'
        ' </flag>\n')
    self._CheckFlagHelpInXML('file_path', 'simple_module',
                             expected_output)

  def testFlagHelpInXML_StringWithXMLIllegalChars(self):
    gflags.DEFINE_string('file_path', '/path/to/\x08my/dir',
                        'A test string flag.', flag_values=self.fv)
    # '\x08' is not a legal character in XML 1.0 documents.  Our
    # current code purges such characters from the generated XML.
    expected_output = (
        ' <flag>\n'
        '   <file>simple_module</file>\n'
        '   <name>file_path</name>\n'
        '   <meaning>A test string flag.</meaning>\n'
        '   <default>/path/to/my/dir</default>\n'
        '   <current>/path/to/my/dir</current>\n'
        '   <type>string</type>\n'
        ' </flag>\n')
    self._CheckFlagHelpInXML('file_path', 'simple_module',
                             expected_output)

  def testFlagHelpInXML_Boolean(self):
    gflags.DEFINE_boolean('use_hack', False, 'Use performance hack',
                         flag_values=self.fv)
    expected_output = (
        ' <flag>\n'
        '   <key>yes</key>\n'
        '   <file>a_module</file>\n'
        '   <name>use_hack</name>\n'
        '   <meaning>Use performance hack</meaning>\n'
        '   <default>false</default>\n'
        '   <current>false</current>\n'
        '   <type>bool</type>\n'
        ' </flag>\n')
    self._CheckFlagHelpInXML('use_hack', 'a_module',
                             expected_output, is_key=True)

  def testFlagHelpInXML_Enum(self):
    gflags.DEFINE_enum('cc_version', 'stable', ['stable', 'experimental'],
                      'Compiler version to use.', flag_values=self.fv)
    expected_output = (
        ' <flag>\n'
        '   <file>tool</file>\n'
        '   <name>cc_version</name>\n'
        '   <meaning>&lt;stable|experimental&gt;: '
        'Compiler version to use.</meaning>\n'
        '   <default>stable</default>\n'
        '   <current>stable</current>\n'
        '   <type>string enum</type>\n'
        '   <enum_value>stable</enum_value>\n'
        '   <enum_value>experimental</enum_value>\n'
        ' </flag>\n')
    self._CheckFlagHelpInXML('cc_version', 'tool', expected_output)

  def testFlagHelpInXML_CommaSeparatedList(self):
    gflags.DEFINE_list('files', 'a.cc,a.h,archive/old.zip',
                      'Files to process.', flag_values=self.fv)
    expected_output = (
        ' <flag>\n'
        '   <file>tool</file>\n'
        '   <name>files</name>\n'
        '   <meaning>Files to process.</meaning>\n'
        '   <default>a.cc,a.h,archive/old.zip</default>\n'
        '   <current>[\'a.cc\', \'a.h\', \'archive/old.zip\']</current>\n'
        '   <type>comma separated list of strings</type>\n'
        '   <list_separator>\',\'</list_separator>\n'
        ' </flag>\n')
    self._CheckFlagHelpInXML('files', 'tool', expected_output)

  def testListAsDefaultArgument_CommaSeparatedList(self):
    gflags.DEFINE_list('allow_users', ['alice', 'bob'],
                      'Users with access.', flag_values=self.fv)
    expected_output = (
        ' <flag>\n'
        '   <file>tool</file>\n'
        '   <name>allow_users</name>\n'
        '   <meaning>Users with access.</meaning>\n'
        '   <default>alice,bob</default>\n'
        '   <current>[\'alice\', \'bob\']</current>\n'
        '   <type>comma separated list of strings</type>\n'
        '   <list_separator>\',\'</list_separator>\n'
        ' </flag>\n')
    self._CheckFlagHelpInXML('allow_users', 'tool', expected_output)

  def testFlagHelpInXML_SpaceSeparatedList(self):
    gflags.DEFINE_spaceseplist('dirs', 'src libs bin',
                              'Directories to search.', flag_values=self.fv)
    expected_output = (
        ' <flag>\n'
        '   <file>tool</file>\n'
        '   <name>dirs</name>\n'
        '   <meaning>Directories to search.</meaning>\n'
        '   <default>src libs bin</default>\n'
        '   <current>[\'src\', \'libs\', \'bin\']</current>\n'
        '   <type>whitespace separated list of strings</type>\n'
        'LIST_SEPARATORS'
        ' </flag>\n').replace('LIST_SEPARATORS',
                              _ListSeparatorsInXMLFormat(string.whitespace,
                                                         indent='   '))
    self._CheckFlagHelpInXML('dirs', 'tool', expected_output)

  def testFlagHelpInXML_MultiString(self):
    gflags.DEFINE_multistring('to_delete', ['a.cc', 'b.h'],
                             'Files to delete', flag_values=self.fv)
    expected_output = (
        ' <flag>\n'
        '   <file>tool</file>\n'
        '   <name>to_delete</name>\n'
        '   <meaning>Files to delete;\n    '
        'repeat this option to specify a list of values</meaning>\n'
        '   <default>[\'a.cc\', \'b.h\']</default>\n'
        '   <current>[\'a.cc\', \'b.h\']</current>\n'
        '   <type>multi string</type>\n'
        ' </flag>\n')
    self._CheckFlagHelpInXML('to_delete', 'tool', expected_output)

  def testFlagHelpInXML_MultiInt(self):
    gflags.DEFINE_multi_int('cols', [5, 7, 23],
                           'Columns to select', flag_values=self.fv)
    expected_output = (
        ' <flag>\n'
        '   <file>tool</file>\n'
        '   <name>cols</name>\n'
        '   <meaning>Columns to select;\n    '
        'repeat this option to specify a list of values</meaning>\n'
        '   <default>[5, 7, 23]</default>\n'
        '   <current>[5, 7, 23]</current>\n'
        '   <type>multi int</type>\n'
        ' </flag>\n')
    self._CheckFlagHelpInXML('cols', 'tool', expected_output)


# The next EXPECTED_HELP_XML_* constants are parts of a template for
# the expected XML output from WriteHelpInXMLFormatTest below.  When
# we assemble these parts into a single big string, we'll take into
# account the ordering between the name of the main module and the
# name of module_bar.  Next, we'll fill in the docstring for this
# module (%(usage_doc)s), the name of the main module
# (%(main_module_name)s) and the name of the module module_bar
# (%(module_bar_name)s).  See WriteHelpInXMLFormatTest below.
#
# NOTE: given the current implementation of _GetMainModule(), we
# already know the ordering between the main module and module_bar.
# However, there is no guarantee that _GetMainModule will never be
# changed in the future (especially since it's far from perfect).
EXPECTED_HELP_XML_START = """\
<?xml version="1.0"?>
<AllFlags>
  <program>gflags_helpxml_test.py</program>
  <usage>%(usage_doc)s</usage>
"""

EXPECTED_HELP_XML_FOR_FLAGS_FROM_MAIN_MODULE = """\
  <flag>
    <key>yes</key>
    <file>%(main_module_name)s</file>
    <name>allow_users</name>
    <meaning>Users with access.</meaning>
    <default>alice,bob</default>
    <current>['alice', 'bob']</current>
    <type>comma separated list of strings</type>
    <list_separator>','</list_separator>
  </flag>
  <flag>
    <key>yes</key>
    <file>%(main_module_name)s</file>
    <name>cc_version</name>
    <meaning>&lt;stable|experimental&gt;: Compiler version to use.</meaning>
    <default>stable</default>
    <current>stable</current>
    <type>string enum</type>
    <enum_value>stable</enum_value>
    <enum_value>experimental</enum_value>
  </flag>
  <flag>
    <key>yes</key>
    <file>%(main_module_name)s</file>
    <name>cols</name>
    <meaning>Columns to select;
    repeat this option to specify a list of values</meaning>
    <default>[5, 7, 23]</default>
    <current>[5, 7, 23]</current>
    <type>multi int</type>
  </flag>
  <flag>
    <key>yes</key>
    <file>%(main_module_name)s</file>
    <name>dirs</name>
    <meaning>Directories to create.</meaning>
    <default>src libs bins</default>
    <current>['src', 'libs', 'bins']</current>
    <type>whitespace separated list of strings</type>
%(whitespace_separators)s  </flag>
  <flag>
    <key>yes</key>
    <file>%(main_module_name)s</file>
    <name>file_path</name>
    <meaning>A test string flag.</meaning>
    <default>/path/to/my/dir</default>
    <current>/path/to/my/dir</current>
    <type>string</type>
  </flag>
  <flag>
    <key>yes</key>
    <file>%(main_module_name)s</file>
    <name>files</name>
    <meaning>Files to process.</meaning>
    <default>a.cc,a.h,archive/old.zip</default>
    <current>['a.cc', 'a.h', 'archive/old.zip']</current>
    <type>comma separated list of strings</type>
    <list_separator>\',\'</list_separator>
  </flag>
  <flag>
    <key>yes</key>
    <file>%(main_module_name)s</file>
    <name>index</name>
    <meaning>An integer flag</meaning>
    <default>17</default>
    <current>17</current>
    <type>int</type>
  </flag>
  <flag>
    <key>yes</key>
    <file>%(main_module_name)s</file>
    <name>nb_iters</name>
    <meaning>An integer flag</meaning>
    <default>17</default>
    <current>17</current>
    <type>int</type>
    <lower_bound>5</lower_bound>
    <upper_bound>27</upper_bound>
  </flag>
  <flag>
    <key>yes</key>
    <file>%(main_module_name)s</file>
    <name>to_delete</name>
    <meaning>Files to delete;
    repeat this option to specify a list of values</meaning>
    <default>['a.cc', 'b.h']</default>
    <current>['a.cc', 'b.h']</current>
    <type>multi string</type>
  </flag>
  <flag>
    <key>yes</key>
    <file>%(main_module_name)s</file>
    <name>use_hack</name>
    <meaning>Use performance hack</meaning>
    <default>false</default>
    <current>false</current>
    <type>bool</type>
  </flag>
"""

EXPECTED_HELP_XML_FOR_FLAGS_FROM_MODULE_BAR = """\
  <flag>
    <file>%(module_bar_name)s</file>
    <name>tmod_bar_t</name>
    <meaning>Sample int flag.</meaning>
    <default>4</default>
    <current>4</current>
    <type>int</type>
  </flag>
  <flag>
    <key>yes</key>
    <file>%(module_bar_name)s</file>
    <name>tmod_bar_u</name>
    <meaning>Sample int flag.</meaning>
    <default>5</default>
    <current>5</current>
    <type>int</type>
  </flag>
  <flag>
    <file>%(module_bar_name)s</file>
    <name>tmod_bar_v</name>
    <meaning>Sample int flag.</meaning>
    <default>6</default>
    <current>6</current>
    <type>int</type>
  </flag>
  <flag>
    <file>%(module_bar_name)s</file>
    <name>tmod_bar_x</name>
    <meaning>Boolean flag.</meaning>
    <default>true</default>
    <current>true</current>
    <type>bool</type>
  </flag>
  <flag>
    <file>%(module_bar_name)s</file>
    <name>tmod_bar_y</name>
    <meaning>String flag.</meaning>
    <default>default</default>
    <current>default</current>
    <type>string</type>
  </flag>
  <flag>
    <key>yes</key>
    <file>%(module_bar_name)s</file>
    <name>tmod_bar_z</name>
    <meaning>Another boolean flag from module bar.</meaning>
    <default>false</default>
    <current>false</current>
    <type>bool</type>
  </flag>
"""

EXPECTED_HELP_XML_END = """\
</AllFlags>
"""


class WriteHelpInXMLFormatTest(googletest.TestCase):
  """Big test of FlagValues.WriteHelpInXMLFormat, with several flags."""

  def testWriteHelpInXMLFormat(self):
    fv = gflags.FlagValues()
    # Since these flags are defined by the top module, they are all key.
    gflags.DEFINE_integer('index', 17, 'An integer flag', flag_values=fv)
    gflags.DEFINE_integer('nb_iters', 17, 'An integer flag',
                         lower_bound=5, upper_bound=27, flag_values=fv)
    gflags.DEFINE_string('file_path', '/path/to/my/dir', 'A test string flag.',
                        flag_values=fv)
    gflags.DEFINE_boolean('use_hack', False, 'Use performance hack',
                         flag_values=fv)
    gflags.DEFINE_enum('cc_version', 'stable', ['stable', 'experimental'],
                      'Compiler version to use.', flag_values=fv)
    gflags.DEFINE_list('files', 'a.cc,a.h,archive/old.zip',
                      'Files to process.', flag_values=fv)
    gflags.DEFINE_list('allow_users', ['alice', 'bob'],
                      'Users with access.', flag_values=fv)
    gflags.DEFINE_spaceseplist('dirs', 'src libs bins',
                              'Directories to create.', flag_values=fv)
    gflags.DEFINE_multistring('to_delete', ['a.cc', 'b.h'],
                             'Files to delete', flag_values=fv)
    gflags.DEFINE_multi_int('cols', [5, 7, 23],
                           'Columns to select', flag_values=fv)
    # Define a few flags in a different module.
    module_bar.DefineFlags(flag_values=fv)
    # And declare only a few of them to be key.  This way, we have
    # different kinds of flags, defined in different modules, and not
    # all of them are key flags.
    gflags.DECLARE_key_flag('tmod_bar_z', flag_values=fv)
    gflags.DECLARE_key_flag('tmod_bar_u', flag_values=fv)

    # Generate flag help in XML format in the StringIO sio.
    sio = StringIO.StringIO()
    fv.WriteHelpInXMLFormat(sio)

    # Check that we got the expected result.
    expected_output_template = EXPECTED_HELP_XML_START
    main_module_name = gflags._GetMainModule()
    module_bar_name = module_bar.__name__

    if main_module_name < module_bar_name:
      expected_output_template += EXPECTED_HELP_XML_FOR_FLAGS_FROM_MAIN_MODULE
      expected_output_template += EXPECTED_HELP_XML_FOR_FLAGS_FROM_MODULE_BAR
    else:
      expected_output_template += EXPECTED_HELP_XML_FOR_FLAGS_FROM_MODULE_BAR
      expected_output_template += EXPECTED_HELP_XML_FOR_FLAGS_FROM_MAIN_MODULE

    expected_output_template += EXPECTED_HELP_XML_END

    # XML representation of the whitespace list separators.
    whitespace_separators = _ListSeparatorsInXMLFormat(string.whitespace,
                                                       indent='    ')
    expected_output = (
        expected_output_template %
        {'usage_doc': sys.modules['__main__'].__doc__,
         'main_module_name': main_module_name,
         'module_bar_name': module_bar_name,
         'whitespace_separators': whitespace_separators})

    actual_output = sio.getvalue()
    self.assertMultiLineEqual(actual_output, expected_output)

    # Also check that our result is valid XML.  minidom.parseString
    # throws an xml.parsers.expat.ExpatError in case of an error.
    xml.dom.minidom.parseString(actual_output)


if __name__ == '__main__':
  googletest.main()

########NEW FILE########
__FILENAME__ = gflags_unittest
#!/usr/bin/env python

# Copyright (c) 2007, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"Unittest for gflags.py module"

__pychecker__ = "no-local" # for unittest


import cStringIO
import sys
import os
import shutil

import gflags
from flags_modules_for_testing import module_foo
from flags_modules_for_testing import module_bar
from flags_modules_for_testing import module_baz

FLAGS=gflags.FLAGS

import gflags_googletest as googletest

# TODO(csilvers): add a wrapper function around FLAGS(argv) that
# verifies the input is a list or tuple.  This avoids bugs where we
# make argv a string instead of a list, by mistake.

class FlagsUnitTest(googletest.TestCase):
  "Flags Unit Test"

  def setUp(self):
    # make sure we are using the old, stupid way of parsing flags.
    FLAGS.UseGnuGetOpt(False)

  def test_flags(self):

    ##############################################
    # Test normal usage with no (expected) errors.

    # Define flags
    number_test_framework_flags = len(FLAGS.RegisteredFlags())
    repeatHelp = "how many times to repeat (0-5)"
    gflags.DEFINE_integer("repeat", 4, repeatHelp,
                         lower_bound=0, short_name='r')
    gflags.DEFINE_string("name", "Bob", "namehelp")
    gflags.DEFINE_boolean("debug", 0, "debughelp")
    gflags.DEFINE_boolean("q", 1, "quiet mode")
    gflags.DEFINE_boolean("quack", 0, "superstring of 'q'")
    gflags.DEFINE_boolean("noexec", 1, "boolean flag with no as prefix")
    gflags.DEFINE_integer("x", 3, "how eXtreme to be")
    gflags.DEFINE_integer("l", 0x7fffffff00000000, "how long to be")
    gflags.DEFINE_list('letters', 'a,b,c', "a list of letters")
    gflags.DEFINE_list('numbers', [1, 2, 3], "a list of numbers")
    gflags.DEFINE_enum("kwery", None, ['who', 'what', 'why', 'where', 'when'],
                      "?")

    # Specify number of flags defined above.  The short_name defined
    # for 'repeat' counts as an extra flag.
    number_defined_flags = 11 + 1
    self.assertEqual(len(FLAGS.RegisteredFlags()),
                         number_defined_flags + number_test_framework_flags)

    assert FLAGS.repeat == 4, "integer default values not set:" + FLAGS.repeat
    assert FLAGS.name == 'Bob', "default values not set:" + FLAGS.name
    assert FLAGS.debug == 0, "boolean default values not set:" + FLAGS.debug
    assert FLAGS.q == 1, "boolean default values not set:" + FLAGS.q
    assert FLAGS.x == 3, "integer default values not set:" + FLAGS.x
    assert FLAGS.l == 0x7fffffff00000000, ("integer default values not set:"
                                           + FLAGS.l)
    assert FLAGS.letters == ['a', 'b', 'c'], ("list default values not set:"
                                              + FLAGS.letters)
    assert FLAGS.numbers == [1, 2, 3], ("list default values not set:"
                                        + FLAGS.numbers)
    assert FLAGS.kwery is None, ("enum default None value not set:"
                                  + FLAGS.kwery)

    flag_values = FLAGS.FlagValuesDict()
    assert flag_values['repeat'] == 4
    assert flag_values['name'] == 'Bob'
    assert flag_values['debug'] == 0
    assert flag_values['r'] == 4       # short for repeat
    assert flag_values['q'] == 1
    assert flag_values['quack'] == 0
    assert flag_values['x'] == 3
    assert flag_values['l'] == 0x7fffffff00000000
    assert flag_values['letters'] == ['a', 'b', 'c']
    assert flag_values['numbers'] == [1, 2, 3]
    assert flag_values['kwery'] is None

    # Verify string form of defaults
    assert FLAGS['repeat'].default_as_str == "'4'"
    assert FLAGS['name'].default_as_str == "'Bob'"
    assert FLAGS['debug'].default_as_str == "'false'"
    assert FLAGS['q'].default_as_str == "'true'"
    assert FLAGS['quack'].default_as_str == "'false'"
    assert FLAGS['noexec'].default_as_str == "'true'"
    assert FLAGS['x'].default_as_str == "'3'"
    assert FLAGS['l'].default_as_str == "'9223372032559808512'"
    assert FLAGS['letters'].default_as_str == "'a,b,c'"
    assert FLAGS['numbers'].default_as_str == "'1,2,3'"

    # Verify that the iterator for flags yields all the keys
    keys = list(FLAGS)
    keys.sort()
    reg_flags = FLAGS.RegisteredFlags()
    reg_flags.sort()
    self.assertEqual(keys, reg_flags)

    # Parse flags
    # .. empty command line
    argv = ('./program',)
    argv = FLAGS(argv)
    assert len(argv) == 1, "wrong number of arguments pulled"
    assert argv[0]=='./program', "program name not preserved"

    # .. non-empty command line
    argv = ('./program', '--debug', '--name=Bob', '-q', '--x=8')
    argv = FLAGS(argv)
    assert len(argv) == 1, "wrong number of arguments pulled"
    assert argv[0]=='./program', "program name not preserved"
    assert FLAGS['debug'].present == 1
    FLAGS['debug'].present = 0 # Reset
    assert FLAGS['name'].present == 1
    FLAGS['name'].present = 0 # Reset
    assert FLAGS['q'].present == 1
    FLAGS['q'].present = 0 # Reset
    assert FLAGS['x'].present == 1
    FLAGS['x'].present = 0 # Reset

    # Flags list
    self.assertEqual(len(FLAGS.RegisteredFlags()),
                     number_defined_flags + number_test_framework_flags)
    assert 'name' in FLAGS.RegisteredFlags()
    assert 'debug' in FLAGS.RegisteredFlags()
    assert 'repeat' in FLAGS.RegisteredFlags()
    assert 'r' in FLAGS.RegisteredFlags()
    assert 'q' in FLAGS.RegisteredFlags()
    assert 'quack' in FLAGS.RegisteredFlags()
    assert 'x' in FLAGS.RegisteredFlags()
    assert 'l' in FLAGS.RegisteredFlags()
    assert 'letters' in FLAGS.RegisteredFlags()
    assert 'numbers' in FLAGS.RegisteredFlags()

    # has_key
    assert FLAGS.has_key('name')
    assert not FLAGS.has_key('name2')
    assert 'name' in FLAGS
    assert 'name2' not in FLAGS

    # try deleting a flag
    del FLAGS.r
    self.assertEqual(len(FLAGS.RegisteredFlags()),
                     number_defined_flags - 1 + number_test_framework_flags)
    assert not 'r' in FLAGS.RegisteredFlags()

    # .. command line with extra stuff
    argv = ('./program', '--debug', '--name=Bob', 'extra')
    argv = FLAGS(argv)
    assert len(argv) == 2, "wrong number of arguments pulled"
    assert argv[0]=='./program', "program name not preserved"
    assert argv[1]=='extra', "extra argument not preserved"
    assert FLAGS['debug'].present == 1
    FLAGS['debug'].present = 0 # Reset
    assert FLAGS['name'].present == 1
    FLAGS['name'].present = 0 # Reset

    # Test reset
    argv = ('./program', '--debug')
    argv = FLAGS(argv)
    assert len(argv) == 1, "wrong number of arguments pulled"
    assert argv[0] == './program', "program name not preserved"
    assert FLAGS['debug'].present == 1
    assert FLAGS['debug'].value
    FLAGS.Reset()
    assert FLAGS['debug'].present == 0
    assert not FLAGS['debug'].value

    # Test that reset restores default value when default value is None.
    argv = ('./program', '--kwery=who')
    argv = FLAGS(argv)
    assert len(argv) == 1, "wrong number of arguments pulled"
    assert argv[0] == './program', "program name not preserved"
    assert FLAGS['kwery'].present == 1
    assert FLAGS['kwery'].value == 'who'
    FLAGS.Reset()
    assert FLAGS['kwery'].present == 0
    assert FLAGS['kwery'].value == None

    # Test integer argument passing
    argv = ('./program', '--x', '0x12345')
    argv = FLAGS(argv)
    self.assertEquals(FLAGS.x, 0x12345)
    self.assertEquals(type(FLAGS.x), int)

    argv = ('./program', '--x', '0x1234567890ABCDEF1234567890ABCDEF')
    argv = FLAGS(argv)
    self.assertEquals(FLAGS.x, 0x1234567890ABCDEF1234567890ABCDEF)
    self.assertEquals(type(FLAGS.x), long)

    # Treat 0-prefixed parameters as base-10, not base-8
    argv = ('./program', '--x', '012345')
    argv = FLAGS(argv)
    self.assertEquals(FLAGS.x, 12345)
    self.assertEquals(type(FLAGS.x), int)

    argv = ('./program', '--x', '0123459')
    argv = FLAGS(argv)
    self.assertEquals(FLAGS.x, 123459)
    self.assertEquals(type(FLAGS.x), int)

    argv = ('./program', '--x', '0x123efg')
    try:
      argv = FLAGS(argv)
      raise AssertionError("failed to detect invalid hex argument")
    except gflags.IllegalFlagValue:
      pass

    # Test boolean argument parsing
    gflags.DEFINE_boolean("test0", None, "test boolean parsing")
    argv = ('./program', '--notest0')
    argv = FLAGS(argv)
    assert FLAGS.test0 == 0

    gflags.DEFINE_boolean("test1", None, "test boolean parsing")
    argv = ('./program', '--test1')
    argv = FLAGS(argv)
    assert FLAGS.test1 == 1

    FLAGS.test0 = None
    argv = ('./program', '--test0=false')
    argv = FLAGS(argv)
    assert FLAGS.test0 == 0

    FLAGS.test1 = None
    argv = ('./program', '--test1=true')
    argv = FLAGS(argv)
    assert FLAGS.test1 == 1

    FLAGS.test0 = None
    argv = ('./program', '--test0=0')
    argv = FLAGS(argv)
    assert FLAGS.test0 == 0

    FLAGS.test1 = None
    argv = ('./program', '--test1=1')
    argv = FLAGS(argv)
    assert FLAGS.test1 == 1

    # Test booleans that already have 'no' as a prefix
    FLAGS.noexec = None
    argv = ('./program', '--nonoexec', '--name', 'Bob')
    argv = FLAGS(argv)
    assert FLAGS.noexec == 0

    FLAGS.noexec = None
    argv = ('./program', '--name', 'Bob', '--noexec')
    argv = FLAGS(argv)
    assert FLAGS.noexec == 1

    # Test unassigned booleans
    gflags.DEFINE_boolean("testnone", None, "test boolean parsing")
    argv = ('./program',)
    argv = FLAGS(argv)
    assert FLAGS.testnone == None

    # Test get with default
    gflags.DEFINE_boolean("testget1", None, "test parsing with defaults")
    gflags.DEFINE_boolean("testget2", None, "test parsing with defaults")
    gflags.DEFINE_boolean("testget3", None, "test parsing with defaults")
    gflags.DEFINE_integer("testget4", None, "test parsing with defaults")
    argv = ('./program','--testget1','--notestget2')
    argv = FLAGS(argv)
    assert FLAGS.get('testget1', 'foo') == 1
    assert FLAGS.get('testget2', 'foo') == 0
    assert FLAGS.get('testget3', 'foo') == 'foo'
    assert FLAGS.get('testget4', 'foo') == 'foo'

    # test list code
    lists = [['hello','moo','boo','1'],
             [],]

    gflags.DEFINE_list('testlist', '', 'test lists parsing')
    gflags.DEFINE_spaceseplist('testspacelist', '', 'tests space lists parsing')

    for name, sep in (('testlist', ','), ('testspacelist', ' '),
                      ('testspacelist', '\n')):
      for lst in lists:
        argv = ('./program', '--%s=%s' % (name, sep.join(lst)))
        argv = FLAGS(argv)
        self.assertEquals(getattr(FLAGS, name), lst)

    # Test help text
    flagsHelp = str(FLAGS)
    assert flagsHelp.find("repeat") != -1, "cannot find flag in help"
    assert flagsHelp.find(repeatHelp) != -1, "cannot find help string in help"

    # Test flag specified twice
    argv = ('./program', '--repeat=4', '--repeat=2', '--debug', '--nodebug')
    argv = FLAGS(argv)
    self.assertEqual(FLAGS.get('repeat', None), 2)
    self.assertEqual(FLAGS.get('debug', None), 0)

    # Test MultiFlag with single default value
    gflags.DEFINE_multistring('s_str', 'sing1',
                             'string option that can occur multiple times',
                             short_name='s')
    self.assertEqual(FLAGS.get('s_str', None), [ 'sing1', ])

    # Test MultiFlag with list of default values
    multi_string_defs = [ 'def1', 'def2', ]
    gflags.DEFINE_multistring('m_str', multi_string_defs,
                             'string option that can occur multiple times',
                             short_name='m')
    self.assertEqual(FLAGS.get('m_str', None), multi_string_defs)

    # Test flag specified multiple times with a MultiFlag
    argv = ('./program', '--m_str=str1', '-m', 'str2')
    argv = FLAGS(argv)
    self.assertEqual(FLAGS.get('m_str', None), [ 'str1', 'str2', ])

    # Test single-letter flags; should support both single and double dash
    argv = ('./program', '-q', '-x8')
    argv = FLAGS(argv)
    self.assertEqual(FLAGS.get('q', None), 1)
    self.assertEqual(FLAGS.get('x', None), 8)

    argv = ('./program', '--q', '--x', '9', '--noqu')
    argv = FLAGS(argv)
    self.assertEqual(FLAGS.get('q', None), 1)
    self.assertEqual(FLAGS.get('x', None), 9)
    # --noqu should match '--noquack since it's a unique prefix
    self.assertEqual(FLAGS.get('quack', None), 0)

    argv = ('./program', '--noq', '--x=10', '--qu')
    argv = FLAGS(argv)
    self.assertEqual(FLAGS.get('q', None), 0)
    self.assertEqual(FLAGS.get('x', None), 10)
    self.assertEqual(FLAGS.get('quack', None), 1)

    ####################################
    # Test flag serialization code:

    oldtestlist = FLAGS.testlist
    oldtestspacelist = FLAGS.testspacelist

    argv = ('./program',
            FLAGS['test0'].Serialize(),
            FLAGS['test1'].Serialize(),
            FLAGS['testnone'].Serialize(),
            FLAGS['s_str'].Serialize())
    argv = FLAGS(argv)
    self.assertEqual(FLAGS['test0'].Serialize(), '--notest0')
    self.assertEqual(FLAGS['test1'].Serialize(), '--test1')
    self.assertEqual(FLAGS['testnone'].Serialize(), '')
    self.assertEqual(FLAGS['s_str'].Serialize(), '--s_str=sing1')

    testlist1 = ['aa', 'bb']
    testspacelist1 = ['aa', 'bb', 'cc']
    FLAGS.testlist = list(testlist1)
    FLAGS.testspacelist = list(testspacelist1)
    argv = ('./program',
            FLAGS['testlist'].Serialize(),
            FLAGS['testspacelist'].Serialize())
    argv = FLAGS(argv)
    self.assertEqual(FLAGS.testlist, testlist1)
    self.assertEqual(FLAGS.testspacelist, testspacelist1)

    testlist1 = ['aa some spaces', 'bb']
    testspacelist1 = ['aa', 'bb,some,commas,', 'cc']
    FLAGS.testlist = list(testlist1)
    FLAGS.testspacelist = list(testspacelist1)
    argv = ('./program',
            FLAGS['testlist'].Serialize(),
            FLAGS['testspacelist'].Serialize())
    argv = FLAGS(argv)
    self.assertEqual(FLAGS.testlist, testlist1)
    self.assertEqual(FLAGS.testspacelist, testspacelist1)

    FLAGS.testlist = oldtestlist
    FLAGS.testspacelist = oldtestspacelist

    ####################################
    # Test flag-update:

    def ArgsString():
      flagnames = FLAGS.RegisteredFlags()

      flagnames.sort()
      nonbool_flags = ['--%s %s' % (name, FLAGS.get(name, None))
                       for name in flagnames
                       if not isinstance(FLAGS[name], gflags.BooleanFlag)]

      truebool_flags = ['--%s' % (name)
                        for name in flagnames
                        if isinstance(FLAGS[name], gflags.BooleanFlag) and
                          FLAGS.get(name, None)]
      falsebool_flags = ['--no%s' % (name)
                         for name in flagnames
                         if isinstance(FLAGS[name], gflags.BooleanFlag) and
                           not FLAGS.get(name, None)]
      return ' '.join(nonbool_flags + truebool_flags + falsebool_flags)

    argv = ('./program', '--repeat=3', '--name=giants', '--nodebug')

    FLAGS(argv)
    self.assertEqual(FLAGS.get('repeat', None), 3)
    self.assertEqual(FLAGS.get('name', None), 'giants')
    self.assertEqual(FLAGS.get('debug', None), 0)
    self.assertEqual(ArgsString(),
      "--kwery None "
      "--l 9223372032559808512 "
      "--letters ['a', 'b', 'c'] "
      "--m ['str1', 'str2'] --m_str ['str1', 'str2'] "
      "--name giants "
      "--numbers [1, 2, 3] "
      "--repeat 3 "
      "--s ['sing1'] --s_str ['sing1'] "
      ""
      ""
      "--testget4 None --testlist [] "
      "--testspacelist [] --x 10 "
      "--noexec --quack "
      "--test1 "
      "--testget1 --tmod_baz_x "
      "--no? --nodebug --nohelp --nohelpshort --nohelpxml --noq "
      ""
      "--notest0 --notestget2 --notestget3 --notestnone")

    argv = ('./program', '--debug', '--m_str=upd1', '-s', 'upd2')
    FLAGS(argv)
    self.assertEqual(FLAGS.get('repeat', None), 3)
    self.assertEqual(FLAGS.get('name', None), 'giants')
    self.assertEqual(FLAGS.get('debug', None), 1)

    # items appended to existing non-default value lists for --m/--m_str
    # new value overwrites default value (not appended to it) for --s/--s_str
    self.assertEqual(ArgsString(),
      "--kwery None "
      "--l 9223372032559808512 "
      "--letters ['a', 'b', 'c'] "
      "--m ['str1', 'str2', 'upd1'] "
      "--m_str ['str1', 'str2', 'upd1'] "
      "--name giants "
      "--numbers [1, 2, 3] "
      "--repeat 3 "
      "--s ['upd2'] --s_str ['upd2'] "
      ""
      ""
      "--testget4 None --testlist [] "
      "--testspacelist [] --x 10 "
      "--debug --noexec --quack "
      "--test1 "
      "--testget1 --tmod_baz_x "
      "--no? --nohelp --nohelpshort --nohelpxml --noq "
      ""
      "--notest0 --notestget2 --notestget3 --notestnone")

    ####################################
    # Test all kind of error conditions.

    # Duplicate flag detection
    try:
      gflags.DEFINE_boolean("run", 0, "runhelp", short_name='q')
      raise AssertionError("duplicate flag detection failed")
    except gflags.DuplicateFlag:
      pass

    # Duplicate short flag detection
    try:
      gflags.DEFINE_boolean("zoom1", 0, "runhelp z1", short_name='z')
      gflags.DEFINE_boolean("zoom2", 0, "runhelp z2", short_name='z')
      raise AssertionError("duplicate short flag detection failed")
    except gflags.DuplicateFlag, e:
      self.assertTrue("The flag 'z' is defined twice. " in e.args[0])
      self.assertTrue("First from" in e.args[0])
      self.assertTrue(", Second from" in e.args[0])

    # Duplicate mixed flag detection
    try:
      gflags.DEFINE_boolean("short1", 0, "runhelp s1", short_name='s')
      gflags.DEFINE_boolean("s", 0, "runhelp s2")
      raise AssertionError("duplicate mixed flag detection failed")
    except gflags.DuplicateFlag, e:
      self.assertTrue("The flag 's' is defined twice. " in e.args[0])
      self.assertTrue("First from" in e.args[0])
      self.assertTrue(", Second from" in e.args[0])

    # Check that duplicate flag detection detects definition sites
    # correctly.
    flagnames = ["repeated"]
    original_flags = gflags.FlagValues()
    gflags.DEFINE_boolean(flagnames[0], False, "Flag about to be repeated.",
                         flag_values=original_flags)
    duplicate_flags = module_foo.DuplicateFlags(flagnames)
    try:
      original_flags.AppendFlagValues(duplicate_flags)
    except gflags.DuplicateFlagError, e:
      self.assertTrue("flags_unittest" in str(e))
      self.assertTrue("module_foo" in str(e))

    # Make sure allow_override works
    try:
      gflags.DEFINE_boolean("dup1", 0, "runhelp d11", short_name='u',
                           allow_override=0)
      flag = FLAGS.FlagDict()['dup1']
      self.assertEqual(flag.default, 0)

      gflags.DEFINE_boolean("dup1", 1, "runhelp d12", short_name='u',
                           allow_override=1)
      flag = FLAGS.FlagDict()['dup1']
      self.assertEqual(flag.default, 1)
    except gflags.DuplicateFlag:
      raise AssertionError("allow_override did not permit a flag duplication")

    # Make sure allow_override works
    try:
      gflags.DEFINE_boolean("dup2", 0, "runhelp d21", short_name='u',
                           allow_override=1)
      flag = FLAGS.FlagDict()['dup2']
      self.assertEqual(flag.default, 0)

      gflags.DEFINE_boolean("dup2", 1, "runhelp d22", short_name='u',
                           allow_override=0)
      flag = FLAGS.FlagDict()['dup2']
      self.assertEqual(flag.default, 1)
    except gflags.DuplicateFlag:
      raise AssertionError("allow_override did not permit a flag duplication")

    # Make sure allow_override doesn't work with None default
    try:
      gflags.DEFINE_boolean("dup3", 0, "runhelp d31", short_name='u3',
                           allow_override=0)
      flag = FLAGS.FlagDict()['dup3']
      self.assertEqual(flag.default, 0)

      gflags.DEFINE_boolean("dup3", None, "runhelp d32", short_name='u3',
                           allow_override=1)
      raise AssertionError('Cannot override a flag with a default of None')
    except gflags.DuplicateFlagCannotPropagateNoneToSwig:
      pass

    # Make sure that re-importing a module does not cause a DuplicateFlagError
    # to be raised.
    try:
      sys.modules.pop(
          "flags_modules_for_testing.module_baz")
      import flags_modules_for_testing.module_baz
    except gflags.DuplicateFlagError:
      raise AssertionError("Module reimport caused flag duplication error")

    # Make sure that when we override, the help string gets updated correctly
    gflags.DEFINE_boolean("dup3", 0, "runhelp d31", short_name='u',
                         allow_override=1)
    gflags.DEFINE_boolean("dup3", 1, "runhelp d32", short_name='u',
                         allow_override=1)
    self.assert_(str(FLAGS).find('runhelp d31') == -1)
    self.assert_(str(FLAGS).find('runhelp d32') != -1)

    # Make sure AppendFlagValues works
    new_flags = gflags.FlagValues()
    gflags.DEFINE_boolean("new1", 0, "runhelp n1", flag_values=new_flags)
    gflags.DEFINE_boolean("new2", 0, "runhelp n2", flag_values=new_flags)
    self.assertEqual(len(new_flags.FlagDict()), 2)
    old_len = len(FLAGS.FlagDict())
    FLAGS.AppendFlagValues(new_flags)
    self.assertEqual(len(FLAGS.FlagDict())-old_len, 2)
    self.assertEqual("new1" in FLAGS.FlagDict(), True)
    self.assertEqual("new2" in FLAGS.FlagDict(), True)

    # Then test that removing those flags works
    FLAGS.RemoveFlagValues(new_flags)
    self.assertEqual(len(FLAGS.FlagDict()), old_len)
    self.assertFalse("new1" in FLAGS.FlagDict())
    self.assertFalse("new2" in FLAGS.FlagDict())

    # Make sure AppendFlagValues works with flags with shortnames.
    new_flags = gflags.FlagValues()
    gflags.DEFINE_boolean("new3", 0, "runhelp n3", flag_values=new_flags)
    gflags.DEFINE_boolean("new4", 0, "runhelp n4", flag_values=new_flags,
                         short_name="n4")
    self.assertEqual(len(new_flags.FlagDict()), 3)
    old_len = len(FLAGS.FlagDict())
    FLAGS.AppendFlagValues(new_flags)
    self.assertEqual(len(FLAGS.FlagDict())-old_len, 3)
    self.assertTrue("new3" in FLAGS.FlagDict())
    self.assertTrue("new4" in FLAGS.FlagDict())
    self.assertTrue("n4" in FLAGS.FlagDict())
    self.assertEqual(FLAGS.FlagDict()['n4'], FLAGS.FlagDict()['new4'])

    # Then test removing them
    FLAGS.RemoveFlagValues(new_flags)
    self.assertEqual(len(FLAGS.FlagDict()), old_len)
    self.assertFalse("new3" in FLAGS.FlagDict())
    self.assertFalse("new4" in FLAGS.FlagDict())
    self.assertFalse("n4" in FLAGS.FlagDict())

    # Make sure AppendFlagValues fails on duplicates
    gflags.DEFINE_boolean("dup4", 0, "runhelp d41")
    new_flags = gflags.FlagValues()
    gflags.DEFINE_boolean("dup4", 0, "runhelp d42", flag_values=new_flags)
    try:
      FLAGS.AppendFlagValues(new_flags)
      raise AssertionError("ignore_copy was not set but caused no exception")
    except gflags.DuplicateFlag:
      pass

    # Integer out of bounds
    try:
      argv = ('./program', '--repeat=-4')
      FLAGS(argv)
      raise AssertionError('integer bounds exception not raised:'
                           + str(FLAGS.repeat))
    except gflags.IllegalFlagValue:
      pass

    # Non-integer
    try:
      argv = ('./program', '--repeat=2.5')
      FLAGS(argv)
      raise AssertionError("malformed integer value exception not raised")
    except gflags.IllegalFlagValue:
      pass

    # Missing required arugment
    try:
      argv = ('./program', '--name')
      FLAGS(argv)
      raise AssertionError("Flag argument required exception not raised")
    except gflags.FlagsError:
      pass

    # Non-boolean arguments for boolean
    try:
      argv = ('./program', '--debug=goofup')
      FLAGS(argv)
      raise AssertionError("Illegal flag value exception not raised")
    except gflags.IllegalFlagValue:
      pass

    try:
      argv = ('./program', '--debug=42')
      FLAGS(argv)
      raise AssertionError("Illegal flag value exception not raised")
    except gflags.IllegalFlagValue:
      pass


    # Non-numeric argument for integer flag --repeat
    try:
      argv = ('./program', '--repeat', 'Bob', 'extra')
      FLAGS(argv)
      raise AssertionError("Illegal flag value exception not raised")
    except gflags.IllegalFlagValue:
      pass

    # Test ModuleHelp().
    helpstr = FLAGS.ModuleHelp(module_baz)

    expected_help = "\n" + module_baz.__name__ + ":" + """
  --[no]tmod_baz_x: Boolean flag.
    (default: 'true')"""

    self.assertMultiLineEqual(expected_help, helpstr)

    # Test MainModuleHelp().  This must be part of test_flags because
    # it dpeends on dup1/2/3/etc being introduced first.
    helpstr = FLAGS.MainModuleHelp()

    expected_help = "\n" + sys.argv[0] + ':' + """
  --[no]debug: debughelp
    (default: 'false')
  -u,--[no]dup1: runhelp d12
    (default: 'true')
  -u,--[no]dup2: runhelp d22
    (default: 'true')
  -u,--[no]dup3: runhelp d32
    (default: 'true')
  --[no]dup4: runhelp d41
    (default: 'false')
  --kwery: <who|what|why|where|when>: ?
  --l: how long to be
    (default: '9223372032559808512')
    (an integer)
  --letters: a list of letters
    (default: 'a,b,c')
    (a comma separated list)
  -m,--m_str: string option that can occur multiple times;
    repeat this option to specify a list of values
    (default: "['def1', 'def2']")
  --name: namehelp
    (default: 'Bob')
  --[no]noexec: boolean flag with no as prefix
    (default: 'true')
  --numbers: a list of numbers
    (default: '1,2,3')
    (a comma separated list)
  --[no]q: quiet mode
    (default: 'true')
  --[no]quack: superstring of 'q'
    (default: 'false')
  -r,--repeat: how many times to repeat (0-5)
    (default: '4')
    (a non-negative integer)
  -s,--s_str: string option that can occur multiple times;
    repeat this option to specify a list of values
    (default: "['sing1']")
  --[no]test0: test boolean parsing
  --[no]test1: test boolean parsing
  --[no]testget1: test parsing with defaults
  --[no]testget2: test parsing with defaults
  --[no]testget3: test parsing with defaults
  --testget4: test parsing with defaults
    (an integer)
  --testlist: test lists parsing
    (default: '')
    (a comma separated list)
  --[no]testnone: test boolean parsing
  --testspacelist: tests space lists parsing
    (default: '')
    (a whitespace separated list)
  --x: how eXtreme to be
    (default: '3')
    (an integer)
  -z,--[no]zoom1: runhelp z1
    (default: 'false')"""

    # Insert the --help flags in their proper place.
    help_help = """\
  -?,--[no]help: show this help
  --[no]helpshort: show usage only for this module
  --[no]helpxml: like --help, but generates XML output
"""
    expected_help = expected_help.replace('  --kwery',
                                          help_help + '  --kwery')

    self.assertMultiLineEqual(expected_help, helpstr)


class MultiNumericalFlagsTest(googletest.TestCase):

  def testMultiNumericalFlags(self):
    """Test multi_int and multi_float flags."""

    int_defaults = [77, 88,]
    gflags.DEFINE_multi_int('m_int', int_defaults,
                           'integer option that can occur multiple times',
                           short_name='mi')
    self.assertListEqual(FLAGS.get('m_int', None), int_defaults)
    argv = ('./program', '--m_int=-99', '--mi=101')
    FLAGS(argv)
    self.assertListEqual(FLAGS.get('m_int', None), [-99, 101,])

    float_defaults = [2.2, 3]
    gflags.DEFINE_multi_float('m_float', float_defaults,
                             'float option that can occur multiple times',
                             short_name='mf')
    for (expected, actual) in zip(float_defaults, FLAGS.get('m_float', None)):
      self.assertAlmostEquals(expected, actual)
    argv = ('./program', '--m_float=-17', '--mf=2.78e9')
    FLAGS(argv)
    expected_floats = [-17.0, 2.78e9]
    for (expected, actual) in zip(expected_floats, FLAGS.get('m_float', None)):
      self.assertAlmostEquals(expected, actual)

  def testSingleValueDefault(self):
    """Test multi_int and multi_float flags with a single default value."""
    int_default = 77
    gflags.DEFINE_multi_int('m_int1', int_default,
                           'integer option that can occur multiple times')
    self.assertListEqual(FLAGS.get('m_int1', None), [int_default])

    float_default = 2.2
    gflags.DEFINE_multi_float('m_float1', float_default,
                             'float option that can occur multiple times')
    actual = FLAGS.get('m_float1', None)
    self.assertEquals(1, len(actual))
    self.assertAlmostEquals(actual[0], float_default)

  def testBadMultiNumericalFlags(self):
    """Test multi_int and multi_float flags with non-parseable values."""

    # Test non-parseable defaults.
    self.assertRaisesWithRegexpMatch(
        gflags.IllegalFlagValue,
        'flag --m_int2=abc: invalid literal for int\(\) with base 10: \'abc\'',
        gflags.DEFINE_multi_int, 'm_int2', ['abc'], 'desc')

    self.assertRaisesWithRegexpMatch(
        gflags.IllegalFlagValue,
        'flag --m_float2=abc: invalid literal for float\(\): abc',
        gflags.DEFINE_multi_float, 'm_float2', ['abc'], 'desc')

    # Test non-parseable command line values.
    gflags.DEFINE_multi_int('m_int2', '77',
                           'integer option that can occur multiple times')
    argv = ('./program', '--m_int2=def')
    self.assertRaisesWithRegexpMatch(
        gflags.IllegalFlagValue,
        'flag --m_int2=def: invalid literal for int\(\) with base 10: \'def\'',
        FLAGS, argv)

    gflags.DEFINE_multi_float('m_float2', 2.2,
                             'float option that can occur multiple times')
    argv = ('./program', '--m_float2=def')
    self.assertRaisesWithRegexpMatch(
        gflags.IllegalFlagValue,
        'flag --m_float2=def: invalid literal for float\(\): def',
        FLAGS, argv)


class UnicodeFlagsTest(googletest.TestCase):
  """Testing proper unicode support for flags."""

  def testUnicodeDefaultAndHelpstring(self):
    gflags.DEFINE_string("unicode_str", "\xC3\x80\xC3\xBD".decode("utf-8"),
                        "help:\xC3\xAA".decode("utf-8"))
    argv = ("./program",)
    FLAGS(argv)   # should not raise any exceptions

    argv = ("./program", "--unicode_str=foo")
    FLAGS(argv)   # should not raise any exceptions

  def testUnicodeInList(self):
    gflags.DEFINE_list("unicode_list", ["abc", "\xC3\x80".decode("utf-8"),
                                       "\xC3\xBD".decode("utf-8")],
                      "help:\xC3\xAB".decode("utf-8"))
    argv = ("./program",)
    FLAGS(argv)   # should not raise any exceptions

    argv = ("./program", "--unicode_list=hello,there")
    FLAGS(argv)   # should not raise any exceptions

  def testXMLOutput(self):
    gflags.DEFINE_string("unicode1", "\xC3\x80\xC3\xBD".decode("utf-8"),
                        "help:\xC3\xAC".decode("utf-8"))
    gflags.DEFINE_list("unicode2", ["abc", "\xC3\x80".decode("utf-8"),
                                   "\xC3\xBD".decode("utf-8")],
                      "help:\xC3\xAD".decode("utf-8"))
    gflags.DEFINE_list("non_unicode", ["abc", "def", "ghi"],
                      "help:\xC3\xAD".decode("utf-8"))

    outfile = cStringIO.StringIO()
    FLAGS.WriteHelpInXMLFormat(outfile)
    actual_output = outfile.getvalue()

    # The xml output is large, so we just check parts of it.
    self.assertTrue("<name>unicode1</name>\n"
                    "    <meaning>help:&#236;</meaning>\n"
                    "    <default>&#192;&#253;</default>\n"
                    "    <current>&#192;&#253;</current>"
                    in actual_output)
    self.assertTrue("<name>unicode2</name>\n"
                    "    <meaning>help:&#237;</meaning>\n"
                    "    <default>abc,&#192;,&#253;</default>\n"
                    "    <current>[\'abc\', u\'\\xc0\', u\'\\xfd\']</current>"
                    in actual_output)
    self.assertTrue("<name>non_unicode</name>\n"
                    "    <meaning>help:&#237;</meaning>\n"
                    "    <default>abc,def,ghi</default>\n"
                    "    <current>[\'abc\', \'def\', \'ghi\']</current>"
                    in actual_output)


class LoadFromFlagFileTest(googletest.TestCase):
  """Testing loading flags from a file and parsing them."""

  def setUp(self):
    self.flag_values = gflags.FlagValues()
    # make sure we are using the old, stupid way of parsing flags.
    self.flag_values.UseGnuGetOpt(False)
    gflags.DEFINE_string('UnitTestMessage1', 'Foo!', 'You Add Here.',
                        flag_values=self.flag_values)
    gflags.DEFINE_string('UnitTestMessage2', 'Bar!', 'Hello, Sailor!',
                        flag_values=self.flag_values)
    gflags.DEFINE_boolean('UnitTestBoolFlag', 0, 'Some Boolean thing',
                         flag_values=self.flag_values)
    gflags.DEFINE_integer('UnitTestNumber', 12345, 'Some integer',
                         lower_bound=0, flag_values=self.flag_values)
    gflags.DEFINE_list('UnitTestList', "1,2,3", 'Some list',
                      flag_values=self.flag_values)
    self.files_to_delete = []

  def tearDown(self):
    self._RemoveTestFiles()

  def _SetupTestFiles(self):
    """ Creates and sets up some dummy flagfile files with bogus flags"""

    # Figure out where to create temporary files
    tmp_path = '/tmp/flags_unittest'
    if os.path.exists(tmp_path):
      shutil.rmtree(tmp_path)
    os.makedirs(tmp_path)

    try:
      tmp_flag_file_1 = open(tmp_path + '/UnitTestFile1.tst', 'w')
      tmp_flag_file_2 = open(tmp_path + '/UnitTestFile2.tst', 'w')
      tmp_flag_file_3 = open(tmp_path + '/UnitTestFile3.tst', 'w')
      tmp_flag_file_4 = open(tmp_path + '/UnitTestFile4.tst', 'w')
    except IOError, e_msg:
      print e_msg
      print 'FAIL\n File Creation problem in Unit Test'
      sys.exit(1)

    # put some dummy flags in our test files
    tmp_flag_file_1.write('#A Fake Comment\n')
    tmp_flag_file_1.write('--UnitTestMessage1=tempFile1!\n')
    tmp_flag_file_1.write('\n')
    tmp_flag_file_1.write('--UnitTestNumber=54321\n')
    tmp_flag_file_1.write('--noUnitTestBoolFlag\n')
    file_list = [tmp_flag_file_1.name]
    # this one includes test file 1
    tmp_flag_file_2.write('//A Different Fake Comment\n')
    tmp_flag_file_2.write('--flagfile=%s\n' % tmp_flag_file_1.name)
    tmp_flag_file_2.write('--UnitTestMessage2=setFromTempFile2\n')
    tmp_flag_file_2.write('\t\t\n')
    tmp_flag_file_2.write('--UnitTestNumber=6789a\n')
    file_list.append(tmp_flag_file_2.name)
    # this file points to itself
    tmp_flag_file_3.write('--flagfile=%s\n' % tmp_flag_file_3.name)
    tmp_flag_file_3.write('--UnitTestMessage1=setFromTempFile3\n')
    tmp_flag_file_3.write('#YAFC\n')
    tmp_flag_file_3.write('--UnitTestBoolFlag\n')
    file_list.append(tmp_flag_file_3.name)
    # this file is unreadable
    tmp_flag_file_4.write('--flagfile=%s\n' % tmp_flag_file_3.name)
    tmp_flag_file_4.write('--UnitTestMessage1=setFromTempFile3\n')
    tmp_flag_file_4.write('--UnitTestMessage1=setFromTempFile3\n')
    os.chmod(tmp_path + '/UnitTestFile4.tst', 0)
    file_list.append(tmp_flag_file_4.name)

    tmp_flag_file_1.close()
    tmp_flag_file_2.close()
    tmp_flag_file_3.close()
    tmp_flag_file_4.close()

    self.files_to_delete = file_list

    return file_list # these are just the file names
  # end SetupFiles def

  def _RemoveTestFiles(self):
    """Closes the files we just created.  tempfile deletes them for us """
    for file_name in self.files_to_delete:
      try:
        os.remove(file_name)
      except OSError, e_msg:
        print '%s\n, Problem deleting test file' % e_msg
  #end RemoveTestFiles def

  def _ReadFlagsFromFiles(self, argv, force_gnu):
    return argv[:1] + self.flag_values.ReadFlagsFromFiles(argv[1:],
                                                          force_gnu=force_gnu)

  #### Flagfile Unit Tests ####
  def testMethod_flagfiles_1(self):
    """ Test trivial case with no flagfile based options. """
    fake_cmd_line = 'fooScript --UnitTestBoolFlag'
    fake_argv = fake_cmd_line.split(' ')
    self.flag_values(fake_argv)
    self.assertEqual( self.flag_values.UnitTestBoolFlag, 1)
    self.assertEqual( fake_argv, self._ReadFlagsFromFiles(fake_argv, False))

  # end testMethodOne

  def testMethod_flagfiles_2(self):
    """Tests parsing one file + arguments off simulated argv"""
    tmp_files = self._SetupTestFiles()
    # specify our temp file on the fake cmd line
    fake_cmd_line = 'fooScript --q --flagfile=%s' % tmp_files[0]
    fake_argv = fake_cmd_line.split(' ')

    # We should see the original cmd line with the file's contents spliced in.
    # Flags from the file will appear in the order order they are sepcified
    # in the file, in the same position as the flagfile argument.
    expected_results = ['fooScript',
                          '--q',
                          '--UnitTestMessage1=tempFile1!',
                          '--UnitTestNumber=54321',
                          '--noUnitTestBoolFlag']
    test_results = self._ReadFlagsFromFiles(fake_argv, False)
    self.assertEqual(expected_results, test_results)
  # end testTwo def

  def testMethod_flagfiles_3(self):
    """Tests parsing nested files + arguments of simulated argv"""
    tmp_files = self._SetupTestFiles()
    # specify our temp file on the fake cmd line
    fake_cmd_line = ('fooScript --UnitTestNumber=77 --flagfile=%s'
                     % tmp_files[1])
    fake_argv = fake_cmd_line.split(' ')

    expected_results = ['fooScript',
                          '--UnitTestNumber=77',
                          '--UnitTestMessage1=tempFile1!',
                          '--UnitTestNumber=54321',
                          '--noUnitTestBoolFlag',
                          '--UnitTestMessage2=setFromTempFile2',
                          '--UnitTestNumber=6789a']
    test_results = self._ReadFlagsFromFiles(fake_argv, False)
    self.assertEqual(expected_results, test_results)
  # end testThree def

  def testMethod_flagfiles_4(self):
    """Tests parsing self-referential files + arguments of simulated argv.
      This test should print a warning to stderr of some sort.
    """
    tmp_files = self._SetupTestFiles()
    # specify our temp file on the fake cmd line
    fake_cmd_line = ('fooScript --flagfile=%s --noUnitTestBoolFlag'
                     % tmp_files[2])
    fake_argv = fake_cmd_line.split(' ')
    expected_results = ['fooScript',
                          '--UnitTestMessage1=setFromTempFile3',
                          '--UnitTestBoolFlag',
                          '--noUnitTestBoolFlag' ]

    test_results = self._ReadFlagsFromFiles(fake_argv, False)
    self.assertEqual(expected_results, test_results)

  def testMethod_flagfiles_5(self):
    """Test that --flagfile parsing respects the '--' end-of-options marker."""
    tmp_files = self._SetupTestFiles()
    # specify our temp file on the fake cmd line
    fake_cmd_line = 'fooScript --SomeFlag -- --flagfile=%s' % tmp_files[0]
    fake_argv = fake_cmd_line.split(' ')
    expected_results = ['fooScript',
                        '--SomeFlag',
                        '--',
                        '--flagfile=%s' % tmp_files[0]]

    test_results = self._ReadFlagsFromFiles(fake_argv, False)
    self.assertEqual(expected_results, test_results)

  def testMethod_flagfiles_6(self):
    """Test that --flagfile parsing stops at non-options (non-GNU behavior)."""
    tmp_files = self._SetupTestFiles()
    # specify our temp file on the fake cmd line
    fake_cmd_line = ('fooScript --SomeFlag some_arg --flagfile=%s'
                     % tmp_files[0])
    fake_argv = fake_cmd_line.split(' ')
    expected_results = ['fooScript',
                        '--SomeFlag',
                        'some_arg',
                        '--flagfile=%s' % tmp_files[0]]

    test_results = self._ReadFlagsFromFiles(fake_argv, False)
    self.assertEqual(expected_results, test_results)

  def testMethod_flagfiles_7(self):
    """Test that --flagfile parsing skips over a non-option (GNU behavior)."""
    self.flag_values.UseGnuGetOpt()
    tmp_files = self._SetupTestFiles()
    # specify our temp file on the fake cmd line
    fake_cmd_line = ('fooScript --SomeFlag some_arg --flagfile=%s'
                     % tmp_files[0])
    fake_argv = fake_cmd_line.split(' ')
    expected_results = ['fooScript',
                        '--SomeFlag',
                        'some_arg',
                        '--UnitTestMessage1=tempFile1!',
                        '--UnitTestNumber=54321',
                        '--noUnitTestBoolFlag']

    test_results = self._ReadFlagsFromFiles(fake_argv, False)
    self.assertEqual(expected_results, test_results)

  def testMethod_flagfiles_8(self):
    """Test that --flagfile parsing respects force_gnu=True."""
    tmp_files = self._SetupTestFiles()
    # specify our temp file on the fake cmd line
    fake_cmd_line = ('fooScript --SomeFlag some_arg --flagfile=%s'
                     % tmp_files[0])
    fake_argv = fake_cmd_line.split(' ')
    expected_results = ['fooScript',
                        '--SomeFlag',
                        'some_arg',
                        '--UnitTestMessage1=tempFile1!',
                        '--UnitTestNumber=54321',
                        '--noUnitTestBoolFlag']

    test_results = self._ReadFlagsFromFiles(fake_argv, True)
    self.assertEqual(expected_results, test_results)

  def testMethod_flagfiles_NoPermissions(self):
    """Test that --flagfile raises except on file that is unreadable."""
    tmp_files = self._SetupTestFiles()
    # specify our temp file on the fake cmd line
    fake_cmd_line = ('fooScript --SomeFlag some_arg --flagfile=%s'
                     % tmp_files[3])
    fake_argv = fake_cmd_line.split(' ')
    self.assertRaises(gflags.CantOpenFlagFileError,
                      self._ReadFlagsFromFiles, fake_argv, True)

  def testMethod_flagfiles_NotFound(self):
    """Test that --flagfile raises except on file that does not exist."""
    tmp_files = self._SetupTestFiles()
    # specify our temp file on the fake cmd line
    fake_cmd_line = ('fooScript --SomeFlag some_arg --flagfile=%sNOTEXIST'
                     % tmp_files[3])
    fake_argv = fake_cmd_line.split(' ')
    self.assertRaises(gflags.CantOpenFlagFileError,
                      self._ReadFlagsFromFiles, fake_argv, True)

  def test_flagfiles_user_path_expansion(self):
    """Test that user directory referenced paths (ie. ~/foo) are correctly
      expanded.  This test depends on whatever account's running the unit test
      to have read/write access to their own home directory, otherwise it'll
      FAIL.
    """
    fake_flagfile_item_style_1 = '--flagfile=~/foo.file'
    fake_flagfile_item_style_2 = '-flagfile=~/foo.file'

    expected_results = os.path.expanduser('~/foo.file')

    test_results = self.flag_values.ExtractFilename(fake_flagfile_item_style_1)
    self.assertEqual(expected_results, test_results)

    test_results = self.flag_values.ExtractFilename(fake_flagfile_item_style_2)
    self.assertEqual(expected_results, test_results)

  # end testFour def

  def test_no_touchy_non_flags(self):
    """
    Test that the flags parser does not mutilate arguments which are
    not supposed to be flags
    """
    fake_argv = ['fooScript', '--UnitTestBoolFlag',
                 'command', '--command_arg1', '--UnitTestBoom', '--UnitTestB']
    argv = self.flag_values(fake_argv)
    self.assertEqual(argv, fake_argv[:1] + fake_argv[2:])

  def test_parse_flags_after_args_if_using_gnu_getopt(self):
    """
    Test that flags given after arguments are parsed if using gnu_getopt.
    """
    self.flag_values.UseGnuGetOpt()
    fake_argv = ['fooScript', '--UnitTestBoolFlag',
                 'command', '--UnitTestB']
    argv = self.flag_values(fake_argv)
    self.assertEqual(argv, ['fooScript', 'command'])

  def test_SetDefault(self):
    """
    Test changing flag defaults.
    """
    # Test that SetDefault changes both the default and the value,
    # and that the value is changed when one is given as an option.
    self.flag_values['UnitTestMessage1'].SetDefault('New value')
    self.assertEqual(self.flag_values.UnitTestMessage1, 'New value')
    self.assertEqual(self.flag_values['UnitTestMessage1'].default_as_str,
                     "'New value'")
    self.flag_values([ 'dummyscript', '--UnitTestMessage1=Newer value' ])
    self.assertEqual(self.flag_values.UnitTestMessage1, 'Newer value')

    # Test that setting the default to None works correctly.
    self.flag_values['UnitTestNumber'].SetDefault(None)
    self.assertEqual(self.flag_values.UnitTestNumber, None)
    self.assertEqual(self.flag_values['UnitTestNumber'].default_as_str, None)
    self.flag_values([ 'dummyscript', '--UnitTestNumber=56' ])
    self.assertEqual(self.flag_values.UnitTestNumber, 56)

    # Test that setting the default to zero works correctly.
    self.flag_values['UnitTestNumber'].SetDefault(0)
    self.assertEqual(self.flag_values.UnitTestNumber, 0)
    self.assertEqual(self.flag_values['UnitTestNumber'].default_as_str, "'0'")
    self.flag_values([ 'dummyscript', '--UnitTestNumber=56' ])
    self.assertEqual(self.flag_values.UnitTestNumber, 56)

    # Test that setting the default to "" works correctly.
    self.flag_values['UnitTestMessage1'].SetDefault("")
    self.assertEqual(self.flag_values.UnitTestMessage1, "")
    self.assertEqual(self.flag_values['UnitTestMessage1'].default_as_str, "''")
    self.flag_values([ 'dummyscript', '--UnitTestMessage1=fifty-six' ])
    self.assertEqual(self.flag_values.UnitTestMessage1, "fifty-six")

    # Test that setting the default to false works correctly.
    self.flag_values['UnitTestBoolFlag'].SetDefault(False)
    self.assertEqual(self.flag_values.UnitTestBoolFlag, False)
    self.assertEqual(self.flag_values['UnitTestBoolFlag'].default_as_str,
                     "'false'")
    self.flag_values([ 'dummyscript', '--UnitTestBoolFlag=true' ])
    self.assertEqual(self.flag_values.UnitTestBoolFlag, True)

    # Test that setting a list default works correctly.
    self.flag_values['UnitTestList'].SetDefault('4,5,6')
    self.assertEqual(self.flag_values.UnitTestList, ['4', '5', '6'])
    self.assertEqual(self.flag_values['UnitTestList'].default_as_str, "'4,5,6'")
    self.flag_values([ 'dummyscript', '--UnitTestList=7,8,9' ])
    self.assertEqual(self.flag_values.UnitTestList, ['7', '8', '9'])

    # Test that setting invalid defaults raises exceptions
    self.assertRaises(gflags.IllegalFlagValue,
                      self.flag_values['UnitTestNumber'].SetDefault, 'oops')
    self.assertRaises(gflags.IllegalFlagValue,
                      self.flag_values.SetDefault, 'UnitTestNumber', -1)


class FlagsParsingTest(googletest.TestCase):
  """Testing different aspects of parsing: '-f' vs '--flag', etc."""

  def setUp(self):
    self.flag_values = gflags.FlagValues()

  def testMethod_ShortestUniquePrefixes(self):
    """Test FlagValues.ShortestUniquePrefixes"""

    gflags.DEFINE_string('a', '', '', flag_values=self.flag_values)
    gflags.DEFINE_string('abc', '', '', flag_values=self.flag_values)
    gflags.DEFINE_string('common_a_string', '', '', flag_values=self.flag_values)
    gflags.DEFINE_boolean('common_b_boolean', 0, '',
                         flag_values=self.flag_values)
    gflags.DEFINE_boolean('common_c_boolean', 0, '',
                         flag_values=self.flag_values)
    gflags.DEFINE_boolean('common', 0, '', flag_values=self.flag_values)
    gflags.DEFINE_integer('commonly', 0, '', flag_values=self.flag_values)
    gflags.DEFINE_boolean('zz', 0, '', flag_values=self.flag_values)
    gflags.DEFINE_integer('nozz', 0, '', flag_values=self.flag_values)

    shorter_flags = self.flag_values.ShortestUniquePrefixes(
        self.flag_values.FlagDict())

    expected_results = {'nocommon_b_boolean': 'nocommon_b',
                        'common_c_boolean': 'common_c',
                        'common_b_boolean': 'common_b',
                        'a': 'a',
                        'abc': 'ab',
                        'zz': 'z',
                        'nozz': 'nozz',
                        'common_a_string': 'common_a',
                        'commonly': 'commonl',
                        'nocommon_c_boolean': 'nocommon_c',
                        'nocommon': 'nocommon',
                        'common': 'common'}

    for name, shorter in expected_results.iteritems():
      self.assertEquals(shorter_flags[name], shorter)

    self.flag_values.__delattr__('a')
    self.flag_values.__delattr__('abc')
    self.flag_values.__delattr__('common_a_string')
    self.flag_values.__delattr__('common_b_boolean')
    self.flag_values.__delattr__('common_c_boolean')
    self.flag_values.__delattr__('common')
    self.flag_values.__delattr__('commonly')
    self.flag_values.__delattr__('zz')
    self.flag_values.__delattr__('nozz')

  def test_twodasharg_first(self):
    gflags.DEFINE_string("twodash_name", "Bob", "namehelp",
                        flag_values=self.flag_values)
    gflags.DEFINE_string("twodash_blame", "Rob", "blamehelp",
                        flag_values=self.flag_values)
    argv = ('./program',
            '--',
            '--twodash_name=Harry')
    argv = self.flag_values(argv)
    self.assertEqual('Bob', self.flag_values.twodash_name)
    self.assertEqual(argv[1], '--twodash_name=Harry')

  def test_twodasharg_middle(self):
    gflags.DEFINE_string("twodash2_name", "Bob", "namehelp",
                        flag_values=self.flag_values)
    gflags.DEFINE_string("twodash2_blame", "Rob", "blamehelp",
                        flag_values=self.flag_values)
    argv = ('./program',
            '--twodash2_blame=Larry',
            '--',
            '--twodash2_name=Harry')
    argv = self.flag_values(argv)
    self.assertEqual('Bob', self.flag_values.twodash2_name)
    self.assertEqual('Larry', self.flag_values.twodash2_blame)
    self.assertEqual(argv[1], '--twodash2_name=Harry')

  def test_onedasharg_first(self):
    gflags.DEFINE_string("onedash_name", "Bob", "namehelp",
                        flag_values=self.flag_values)
    gflags.DEFINE_string("onedash_blame", "Rob", "blamehelp",
                        flag_values=self.flag_values)
    argv = ('./program',
            '-',
            '--onedash_name=Harry')
    argv = self.flag_values(argv)
    self.assertEqual(argv[1], '-')
    # TODO(csilvers): we should still parse --onedash_name=Harry as a
    # flag, but currently we don't (we stop flag processing as soon as
    # we see the first non-flag).
    # - This requires gnu_getopt from Python 2.3+ see FLAGS.UseGnuGetOpt()

  def test_unrecognized_flags(self):
    gflags.DEFINE_string("name", "Bob", "namehelp", flag_values=self.flag_values)
    # Unknown flag --nosuchflag
    try:
      argv = ('./program', '--nosuchflag', '--name=Bob', 'extra')
      self.flag_values(argv)
      raise AssertionError("Unknown flag exception not raised")
    except gflags.UnrecognizedFlag, e:
      assert e.flagname == 'nosuchflag'
      assert e.flagvalue == '--nosuchflag'

    # Unknown flag -w (short option)
    try:
      argv = ('./program', '-w', '--name=Bob', 'extra')
      self.flag_values(argv)
      raise AssertionError("Unknown flag exception not raised")
    except gflags.UnrecognizedFlag, e:
      assert e.flagname == 'w'
      assert e.flagvalue == '-w'

    # Unknown flag --nosuchflagwithparam=foo
    try:
      argv = ('./program', '--nosuchflagwithparam=foo', '--name=Bob', 'extra')
      self.flag_values(argv)
      raise AssertionError("Unknown flag exception not raised")
    except gflags.UnrecognizedFlag, e:
      assert e.flagname == 'nosuchflagwithparam'
      assert e.flagvalue == '--nosuchflagwithparam=foo'

    # Allow unknown flag --nosuchflag if specified with undefok
    argv = ('./program', '--nosuchflag', '--name=Bob',
            '--undefok=nosuchflag', 'extra')
    argv = self.flag_values(argv)
    assert len(argv) == 2, "wrong number of arguments pulled"
    assert argv[0]=='./program', "program name not preserved"
    assert argv[1]=='extra', "extra argument not preserved"

    # Allow unknown flag --noboolflag if undefok=boolflag is specified
    argv = ('./program', '--noboolflag', '--name=Bob',
            '--undefok=boolflag', 'extra')
    argv = self.flag_values(argv)
    assert len(argv) == 2, "wrong number of arguments pulled"
    assert argv[0]=='./program', "program name not preserved"
    assert argv[1]=='extra', "extra argument not preserved"

    # But not if the flagname is misspelled:
    try:
      argv = ('./program', '--nosuchflag', '--name=Bob',
              '--undefok=nosuchfla', 'extra')
      self.flag_values(argv)
      raise AssertionError("Unknown flag exception not raised")
    except gflags.UnrecognizedFlag, e:
      assert e.flagname == 'nosuchflag'

    try:
      argv = ('./program', '--nosuchflag', '--name=Bob',
              '--undefok=nosuchflagg', 'extra')
      self.flag_values(argv)
      raise AssertionError("Unknown flag exception not raised")
    except gflags.UnrecognizedFlag, e:
      assert e.flagname == 'nosuchflag'

    # Allow unknown short flag -w if specified with undefok
    argv = ('./program', '-w', '--name=Bob', '--undefok=w', 'extra')
    argv = self.flag_values(argv)
    assert len(argv) == 2, "wrong number of arguments pulled"
    assert argv[0]=='./program', "program name not preserved"
    assert argv[1]=='extra', "extra argument not preserved"

    # Allow unknown flag --nosuchflagwithparam=foo if specified
    # with undefok
    argv = ('./program', '--nosuchflagwithparam=foo', '--name=Bob',
            '--undefok=nosuchflagwithparam', 'extra')
    argv = self.flag_values(argv)
    assert len(argv) == 2, "wrong number of arguments pulled"
    assert argv[0]=='./program', "program name not preserved"
    assert argv[1]=='extra', "extra argument not preserved"

    # Even if undefok specifies multiple flags
    argv = ('./program', '--nosuchflag', '-w', '--nosuchflagwithparam=foo',
            '--name=Bob',
            '--undefok=nosuchflag,w,nosuchflagwithparam',
            'extra')
    argv = self.flag_values(argv)
    assert len(argv) == 2, "wrong number of arguments pulled"
    assert argv[0]=='./program', "program name not preserved"
    assert argv[1]=='extra', "extra argument not preserved"

    # However, not if undefok doesn't specify the flag
    try:
      argv = ('./program', '--nosuchflag', '--name=Bob',
              '--undefok=another_such', 'extra')
      self.flag_values(argv)
      raise AssertionError("Unknown flag exception not raised")
    except gflags.UnrecognizedFlag, e:
      assert e.flagname == 'nosuchflag'

    # Make sure --undefok doesn't mask other option errors.
    try:
      # Provide an option requiring a parameter but not giving it one.
      argv = ('./program', '--undefok=name', '--name')
      self.flag_values(argv)
      raise AssertionError("Missing option parameter exception not raised")
    except gflags.UnrecognizedFlag:
      raise AssertionError("Wrong kind of error exception raised")
    except gflags.FlagsError:
      pass

    # Test --undefok <list>
    argv = ('./program', '--nosuchflag', '-w', '--nosuchflagwithparam=foo',
            '--name=Bob',
            '--undefok',
            'nosuchflag,w,nosuchflagwithparam',
            'extra')
    argv = self.flag_values(argv)
    assert len(argv) == 2, "wrong number of arguments pulled"
    assert argv[0]=='./program', "program name not preserved"
    assert argv[1]=='extra', "extra argument not preserved"


class NonGlobalFlagsTest(googletest.TestCase):

  def test_nonglobal_flags(self):
    """Test use of non-global FlagValues"""
    nonglobal_flags = gflags.FlagValues()
    gflags.DEFINE_string("nonglobal_flag", "Bob", "flaghelp", nonglobal_flags)
    argv = ('./program',
            '--nonglobal_flag=Mary',
            'extra')
    argv = nonglobal_flags(argv)
    assert len(argv) == 2, "wrong number of arguments pulled"
    assert argv[0]=='./program', "program name not preserved"
    assert argv[1]=='extra', "extra argument not preserved"
    assert nonglobal_flags['nonglobal_flag'].value == 'Mary'

  def test_unrecognized_nonglobal_flags(self):
    """Test unrecognized non-global flags"""
    nonglobal_flags = gflags.FlagValues()
    argv = ('./program',
            '--nosuchflag')
    try:
      argv = nonglobal_flags(argv)
      raise AssertionError("Unknown flag exception not raised")
    except gflags.UnrecognizedFlag, e:
      assert e.flagname == 'nosuchflag'
      pass

    argv = ('./program',
            '--nosuchflag',
            '--undefok=nosuchflag')

    argv = nonglobal_flags(argv)
    assert len(argv) == 1, "wrong number of arguments pulled"
    assert argv[0]=='./program', "program name not preserved"

  def test_create_flag_errors(self):
    # Since the exception classes are exposed, nothing stops users
    # from creating their own instances. This test makes sure that
    # people modifying the flags module understand that the external
    # mechanisms for creating the exceptions should continue to work.
    e = gflags.FlagsError()
    e = gflags.FlagsError("message")
    e = gflags.DuplicateFlag()
    e = gflags.DuplicateFlag("message")
    e = gflags.IllegalFlagValue()
    e = gflags.IllegalFlagValue("message")
    e = gflags.UnrecognizedFlag()
    e = gflags.UnrecognizedFlag("message")

  def testFlagValuesDelAttr(self):
    """Checks that del self.flag_values.flag_id works."""
    default_value = 'default value for testFlagValuesDelAttr'
    # 1. Declare and delete a flag with no short name.
    flag_values = gflags.FlagValues()
    gflags.DEFINE_string('delattr_foo', default_value, 'A simple flag.',
                        flag_values=flag_values)
    self.assertEquals(flag_values.delattr_foo, default_value)
    flag_obj = flag_values['delattr_foo']
    # We also check that _FlagIsRegistered works as expected :)
    self.assertTrue(flag_values._FlagIsRegistered(flag_obj))
    del flag_values.delattr_foo
    self.assertFalse('delattr_foo' in flag_values.FlagDict())
    self.assertFalse(flag_values._FlagIsRegistered(flag_obj))
    # If the previous del FLAGS.delattr_foo did not work properly, the
    # next definition will trigger a redefinition error.
    gflags.DEFINE_integer('delattr_foo', 3, 'A simple flag.',
                         flag_values=flag_values)
    del flag_values.delattr_foo

    self.assertFalse('delattr_foo' in flag_values.RegisteredFlags())

    # 2. Declare and delete a flag with a short name.
    gflags.DEFINE_string('delattr_bar', default_value, 'flag with short name',
                        short_name='x5', flag_values=flag_values)
    flag_obj = flag_values['delattr_bar']
    self.assertTrue(flag_values._FlagIsRegistered(flag_obj))
    del flag_values.x5
    self.assertTrue(flag_values._FlagIsRegistered(flag_obj))
    del flag_values.delattr_bar
    self.assertFalse(flag_values._FlagIsRegistered(flag_obj))

    # 3. Just like 2, but del flag_values.name last
    gflags.DEFINE_string('delattr_bar', default_value, 'flag with short name',
                        short_name='x5', flag_values=flag_values)
    flag_obj = flag_values['delattr_bar']
    self.assertTrue(flag_values._FlagIsRegistered(flag_obj))
    del flag_values.delattr_bar
    self.assertTrue(flag_values._FlagIsRegistered(flag_obj))
    del flag_values.x5
    self.assertFalse(flag_values._FlagIsRegistered(flag_obj))

    self.assertFalse('delattr_bar' in flag_values.RegisteredFlags())
    self.assertFalse('x5' in flag_values.RegisteredFlags())


class KeyFlagsTest(googletest.TestCase):

  def setUp(self):
    self.flag_values = gflags.FlagValues()

  def _GetNamesOfDefinedFlags(self, module, flag_values):
    """Returns the list of names of flags defined by a module.

    Auxiliary for the testKeyFlags* methods.

    Args:
      module: A module object or a string module name.
      flag_values: A FlagValues object.

    Returns:
      A list of strings.
    """
    return [f.name for f in flag_values._GetFlagsDefinedByModule(module)]

  def _GetNamesOfKeyFlags(self, module, flag_values):
    """Returns the list of names of key flags for a module.

    Auxiliary for the testKeyFlags* methods.

    Args:
      module: A module object or a string module name.
      flag_values: A FlagValues object.

    Returns:
      A list of strings.
    """
    return [f.name for f in flag_values._GetKeyFlagsForModule(module)]

  def _AssertListsHaveSameElements(self, list_1, list_2):
    # Checks that two lists have the same elements with the same
    # multiplicity, in possibly different order.
    list_1 = list(list_1)
    list_1.sort()
    list_2 = list(list_2)
    list_2.sort()
    self.assertListEqual(list_1, list_2)

  def testKeyFlags(self):
    # Before starting any testing, make sure no flags are already
    # defined for module_foo and module_bar.
    self.assertListEqual(self._GetNamesOfKeyFlags(module_foo, self.flag_values),
                         [])
    self.assertListEqual(self._GetNamesOfKeyFlags(module_bar, self.flag_values),
                         [])
    self.assertListEqual(self._GetNamesOfDefinedFlags(module_foo,
                                                      self.flag_values),
                         [])
    self.assertListEqual(self._GetNamesOfDefinedFlags(module_bar,
                                                      self.flag_values),
                         [])

    # Defines a few flags in module_foo and module_bar.
    module_foo.DefineFlags(flag_values=self.flag_values)

    try:
      # Part 1. Check that all flags defined by module_foo are key for
      # that module, and similarly for module_bar.
      for module in [module_foo, module_bar]:
        self._AssertListsHaveSameElements(
            self.flag_values._GetFlagsDefinedByModule(module),
            self.flag_values._GetKeyFlagsForModule(module))
        # Also check that each module defined the expected flags.
        self._AssertListsHaveSameElements(
            self._GetNamesOfDefinedFlags(module, self.flag_values),
            module.NamesOfDefinedFlags())

      # Part 2. Check that gflags.DECLARE_key_flag works fine.
      # Declare that some flags from module_bar are key for
      # module_foo.
      module_foo.DeclareKeyFlags(flag_values=self.flag_values)

      # Check that module_foo has the expected list of defined flags.
      self._AssertListsHaveSameElements(
          self._GetNamesOfDefinedFlags(module_foo, self.flag_values),
          module_foo.NamesOfDefinedFlags())

      # Check that module_foo has the expected list of key flags.
      self._AssertListsHaveSameElements(
          self._GetNamesOfKeyFlags(module_foo, self.flag_values),
          module_foo.NamesOfDeclaredKeyFlags())

      # Part 3. Check that gflags.ADOPT_module_key_flags works fine.
      # Trigger a call to gflags.ADOPT_module_key_flags(module_bar)
      # inside module_foo.  This should declare a few more key
      # flags in module_foo.
      module_foo.DeclareExtraKeyFlags(flag_values=self.flag_values)

      # Check that module_foo has the expected list of key flags.
      self._AssertListsHaveSameElements(
          self._GetNamesOfKeyFlags(module_foo, self.flag_values),
          module_foo.NamesOfDeclaredKeyFlags() +
          module_foo.NamesOfDeclaredExtraKeyFlags())
    finally:
      module_foo.RemoveFlags(flag_values=self.flag_values)

  def testKeyFlagsWithNonDefaultFlagValuesObject(self):
    # Check that key flags work even when we use a FlagValues object
    # that is not the default gflags.self.flag_values object.  Otherwise, this
    # test is similar to testKeyFlags, but it uses only module_bar.
    # The other test module (module_foo) uses only the default values
    # for the flag_values keyword arguments.  This way, testKeyFlags
    # and this method test both the default FlagValues, the explicitly
    # specified one, and a mixed usage of the two.

    # A brand-new FlagValues object, to use instead of gflags.self.flag_values.
    fv = gflags.FlagValues()

    # Before starting any testing, make sure no flags are already
    # defined for module_foo and module_bar.
    self.assertListEqual(
        self._GetNamesOfKeyFlags(module_bar, fv),
        [])
    self.assertListEqual(
        self._GetNamesOfDefinedFlags(module_bar, fv),
        [])

    module_bar.DefineFlags(flag_values=fv)

    # Check that all flags defined by module_bar are key for that
    # module, and that module_bar defined the expected flags.
    self._AssertListsHaveSameElements(
        fv._GetFlagsDefinedByModule(module_bar),
        fv._GetKeyFlagsForModule(module_bar))
    self._AssertListsHaveSameElements(
        self._GetNamesOfDefinedFlags(module_bar, fv),
        module_bar.NamesOfDefinedFlags())

    # Pick two flags from module_bar, declare them as key for the
    # current (i.e., main) module (via gflags.DECLARE_key_flag), and
    # check that we get the expected effect.  The important thing is
    # that we always use flags_values=fv (instead of the default
    # self.flag_values).
    main_module = gflags._GetMainModule()
    names_of_flags_defined_by_bar = module_bar.NamesOfDefinedFlags()
    flag_name_0 = names_of_flags_defined_by_bar[0]
    flag_name_2 = names_of_flags_defined_by_bar[2]

    gflags.DECLARE_key_flag(flag_name_0, flag_values=fv)
    self._AssertListsHaveSameElements(
        self._GetNamesOfKeyFlags(main_module, fv),
        [flag_name_0])

    gflags.DECLARE_key_flag(flag_name_2, flag_values=fv)
    self._AssertListsHaveSameElements(
        self._GetNamesOfKeyFlags(main_module, fv),
        [flag_name_0, flag_name_2])

    # Try with a special (not user-defined) flag too:
    gflags.DECLARE_key_flag('undefok', flag_values=fv)
    self._AssertListsHaveSameElements(
        self._GetNamesOfKeyFlags(main_module, fv),
        [flag_name_0, flag_name_2, 'undefok'])

    gflags.ADOPT_module_key_flags(module_bar, fv)
    self._AssertListsHaveSameElements(
        self._GetNamesOfKeyFlags(main_module, fv),
        names_of_flags_defined_by_bar + ['undefok'])

    # Adopt key flags from the flags module itself.
    gflags.ADOPT_module_key_flags(gflags, flag_values=fv)
    self._AssertListsHaveSameElements(
        self._GetNamesOfKeyFlags(main_module, fv),
        names_of_flags_defined_by_bar + ['flagfile', 'undefok'])

  def testMainModuleHelpWithKeyFlags(self):
    # Similar to test_main_module_help, but this time we make sure to
    # declare some key flags.

    # Safety check that the main module does not declare any flags
    # at the beginning of this test.
    expected_help = ''
    self.assertMultiLineEqual(expected_help, self.flag_values.MainModuleHelp())

    # Define one flag in this main module and some flags in modules
    # a and b.  Also declare one flag from module a and one flag
    # from module b as key flags for the main module.
    gflags.DEFINE_integer('main_module_int_fg', 1,
                         'Integer flag in the main module.',
                         flag_values=self.flag_values)

    try:
      main_module_int_fg_help = (
          "  --main_module_int_fg: Integer flag in the main module.\n"
          "    (default: '1')\n"
          "    (an integer)")

      expected_help += "\n%s:\n%s" % (sys.argv[0], main_module_int_fg_help)
      self.assertMultiLineEqual(expected_help,
                                self.flag_values.MainModuleHelp())

      # The following call should be a no-op: any flag declared by a
      # module is automatically key for that module.
      gflags.DECLARE_key_flag('main_module_int_fg', flag_values=self.flag_values)
      self.assertMultiLineEqual(expected_help,
                                self.flag_values.MainModuleHelp())

      # The definition of a few flags in an imported module should not
      # change the main module help.
      module_foo.DefineFlags(flag_values=self.flag_values)
      self.assertMultiLineEqual(expected_help,
                                self.flag_values.MainModuleHelp())

      gflags.DECLARE_key_flag('tmod_foo_bool', flag_values=self.flag_values)
      tmod_foo_bool_help = (
          "  --[no]tmod_foo_bool: Boolean flag from module foo.\n"
          "    (default: 'true')")
      expected_help += "\n" + tmod_foo_bool_help
      self.assertMultiLineEqual(expected_help,
                                self.flag_values.MainModuleHelp())

      gflags.DECLARE_key_flag('tmod_bar_z', flag_values=self.flag_values)
      tmod_bar_z_help = (
          "  --[no]tmod_bar_z: Another boolean flag from module bar.\n"
          "    (default: 'false')")
      # Unfortunately, there is some flag sorting inside
      # MainModuleHelp, so we can't keep incrementally extending
      # the expected_help string ...
      expected_help = ("\n%s:\n%s\n%s\n%s" %
                       (sys.argv[0],
                        main_module_int_fg_help,
                        tmod_bar_z_help,
                        tmod_foo_bool_help))
      self.assertMultiLineEqual(self.flag_values.MainModuleHelp(),
                                expected_help)

    finally:
      # At the end, delete all the flag information we created.
      self.flag_values.__delattr__('main_module_int_fg')
      module_foo.RemoveFlags(flag_values=self.flag_values)

  def test_ADOPT_module_key_flags(self):
    # Check that ADOPT_module_key_flags raises an exception when
    # called with a module name (as opposed to a module object).
    self.assertRaises(gflags.FlagsError,
                      gflags.ADOPT_module_key_flags,
                      'pyglib.app')


class GetCallingModuleTest(googletest.TestCase):
  """Test whether we correctly determine the module which defines the flag."""

  def test_GetCallingModule(self):
    self.assertEqual(gflags._GetCallingModule(), sys.argv[0])
    self.assertEqual(
        module_foo.GetModuleName(),
        'flags_modules_for_testing.module_foo')
    self.assertEqual(
        module_bar.GetModuleName(),
        'flags_modules_for_testing.module_bar')

    # We execute the following exec statements for their side-effect
    # (i.e., not raising an error).  They emphasize the case that not
    # all code resides in one of the imported modules: Python is a
    # really dynamic language, where we can dynamically construct some
    # code and execute it.
    code = ("import gflags\n"
            "module_name = gflags._GetCallingModule()")
    exec(code)

    # Next two exec statements executes code with a global environment
    # that is different from the global environment of any imported
    # module.
    exec(code, {})
    # vars(self) returns a dictionary corresponding to the symbol
    # table of the self object.  dict(...) makes a distinct copy of
    # this dictionary, such that any new symbol definition by the
    # exec-ed code (e.g., import flags, module_name = ...) does not
    # affect the symbol table of self.
    exec(code, dict(vars(self)))

    # Next test is actually more involved: it checks not only that
    # _GetCallingModule does not crash inside exec code, it also checks
    # that it returns the expected value: the code executed via exec
    # code is treated as being executed by the current module.  We
    # check it twice: first time by executing exec from the main
    # module, second time by executing it from module_bar.
    global_dict = {}
    exec(code, global_dict)
    self.assertEqual(global_dict['module_name'],
                     sys.argv[0])

    global_dict = {}
    module_bar.ExecuteCode(code, global_dict)
    self.assertEqual(
        global_dict['module_name'],
        'flags_modules_for_testing.module_bar')

  def test_GetCallingModuleWithIteritemsError(self):
    # This test checks that _GetCallingModule is using
    # sys.modules.items(), instead of .iteritems().
    orig_sys_modules = sys.modules

    # Mock sys.modules: simulates error produced by importing a module
    # in paralel with our iteration over sys.modules.iteritems().
    class SysModulesMock(dict):
      def __init__(self, original_content):
        dict.__init__(self, original_content)

      def iteritems(self):
        # Any dictionary method is fine, but not .iteritems().
        raise RuntimeError('dictionary changed size during iteration')

    sys.modules = SysModulesMock(orig_sys_modules)
    try:
      # _GetCallingModule should still work as expected:
      self.assertEqual(gflags._GetCallingModule(), sys.argv[0])
      self.assertEqual(
          module_foo.GetModuleName(),
          'flags_modules_for_testing.module_foo')
    finally:
      sys.modules = orig_sys_modules


class FindModuleTest(googletest.TestCase):
  """Testing methods that find a module that defines a given flag."""

  def testFindModuleDefiningFlag(self):
    self.assertEqual('default', FLAGS.FindModuleDefiningFlag(
        '__NON_EXISTENT_FLAG__', 'default'))
    self.assertEqual(
        module_baz.__name__, FLAGS.FindModuleDefiningFlag('tmod_baz_x'))

  def testFindModuleIdDefiningFlag(self):
    self.assertEqual('default', FLAGS.FindModuleIdDefiningFlag(
        '__NON_EXISTENT_FLAG__', 'default'))
    self.assertEqual(
        id(module_baz), FLAGS.FindModuleIdDefiningFlag('tmod_baz_x'))


class FlagsErrorMessagesTest(googletest.TestCase):
  """Testing special cases for integer and float flags error messages."""

  def setUp(self):
    # make sure we are using the old, stupid way of parsing flags.
    self.flag_values = gflags.FlagValues()
    self.flag_values.UseGnuGetOpt(False)

  def testIntegerErrorText(self):
    # Make sure we get proper error text
    gflags.DEFINE_integer('positive', 4, 'non-negative flag', lower_bound=1,
                         flag_values=self.flag_values)
    gflags.DEFINE_integer('non_negative', 4, 'positive flag', lower_bound=0,
                         flag_values=self.flag_values)
    gflags.DEFINE_integer('negative', -4, 'negative flag', upper_bound=-1,
                         flag_values=self.flag_values)
    gflags.DEFINE_integer('non_positive', -4, 'non-positive flag', upper_bound=0,
                         flag_values=self.flag_values)
    gflags.DEFINE_integer('greater', 19, 'greater-than flag', lower_bound=4,
                         flag_values=self.flag_values)
    gflags.DEFINE_integer('smaller', -19, 'smaller-than flag', upper_bound=4,
                         flag_values=self.flag_values)
    gflags.DEFINE_integer('usual', 4, 'usual flag', lower_bound=0,
                         upper_bound=10000, flag_values=self.flag_values)
    gflags.DEFINE_integer('another_usual', 0, 'usual flag', lower_bound=-1,
                         upper_bound=1, flag_values=self.flag_values)

    self._CheckErrorMessage('positive', -4, 'a positive integer')
    self._CheckErrorMessage('non_negative', -4, 'a non-negative integer')
    self._CheckErrorMessage('negative', 0, 'a negative integer')
    self._CheckErrorMessage('non_positive', 4, 'a non-positive integer')
    self._CheckErrorMessage('usual', -4, 'an integer in the range [0, 10000]')
    self._CheckErrorMessage('another_usual', 4,
                            'an integer in the range [-1, 1]')
    self._CheckErrorMessage('greater', -5, 'integer >= 4')
    self._CheckErrorMessage('smaller', 5, 'integer <= 4')

  def testFloatErrorText(self):
    gflags.DEFINE_float('positive', 4, 'non-negative flag', lower_bound=1,
                       flag_values=self.flag_values)
    gflags.DEFINE_float('non_negative', 4, 'positive flag', lower_bound=0,
                       flag_values=self.flag_values)
    gflags.DEFINE_float('negative', -4, 'negative flag', upper_bound=-1,
                       flag_values=self.flag_values)
    gflags.DEFINE_float('non_positive', -4, 'non-positive flag', upper_bound=0,
                       flag_values=self.flag_values)
    gflags.DEFINE_float('greater', 19, 'greater-than flag', lower_bound=4,
                       flag_values=self.flag_values)
    gflags.DEFINE_float('smaller', -19, 'smaller-than flag', upper_bound=4,
                       flag_values=self.flag_values)
    gflags.DEFINE_float('usual', 4, 'usual flag', lower_bound=0,
                       upper_bound=10000, flag_values=self.flag_values)
    gflags.DEFINE_float('another_usual', 0, 'usual flag', lower_bound=-1,
                       upper_bound=1, flag_values=self.flag_values)

    self._CheckErrorMessage('positive', 0.5, 'number >= 1')
    self._CheckErrorMessage('non_negative', -4.0, 'a non-negative number')
    self._CheckErrorMessage('negative', 0.5, 'number <= -1')
    self._CheckErrorMessage('non_positive', 4.0, 'a non-positive number')
    self._CheckErrorMessage('usual', -4.0, 'a number in the range [0, 10000]')
    self._CheckErrorMessage('another_usual', 4.0,
                            'a number in the range [-1, 1]')
    self._CheckErrorMessage('smaller', 5.0, 'number <= 4')

  def _CheckErrorMessage(self, flag_name, flag_value, expected_message_suffix):
    """Set a flag to a given value and make sure we get expected message."""

    try:
      self.flag_values.__setattr__(flag_name, flag_value)
      raise AssertionError('Bounds exception not raised!')
    except gflags.IllegalFlagValue, e:
      expected = ('flag --%(name)s=%(value)s: %(value)s is not %(suffix)s' %
                  {'name': flag_name, 'value': flag_value,
                   'suffix': expected_message_suffix})
      self.assertEquals(str(e), expected)


def main():
  googletest.main()


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = gflags_validators_test
#!/usr/bin/env python

# Copyright (c) 2010, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Testing that flags validators framework does work.

This file tests that each flag validator called when it should be, and that
failed validator will throw an exception, etc.
"""

__author__ = 'olexiy@google.com (Olexiy Oryeshko)'

import gflags_googletest as googletest
import gflags
import gflags_validators


class SimpleValidatorTest(googletest.TestCase):
  """Testing gflags.RegisterValidator() method."""

  def setUp(self):
    super(SimpleValidatorTest, self).setUp()
    self.flag_values = gflags.FlagValues()
    self.call_args = []

  def testSuccess(self):
    def Checker(x):
      self.call_args.append(x)
      return True
    gflags.DEFINE_integer('test_flag', None, 'Usual integer flag',
                         flag_values=self.flag_values)
    gflags.RegisterValidator('test_flag',
                            Checker,
                            message='Errors happen',
                            flag_values=self.flag_values)

    argv = ('./program')
    self.flag_values(argv)
    self.assertEquals(None, self.flag_values.test_flag)
    self.flag_values.test_flag = 2
    self.assertEquals(2, self.flag_values.test_flag)
    self.assertEquals([None, 2], self.call_args)

  def testDefaultValueNotUsedSuccess(self):
    def Checker(x):
      self.call_args.append(x)
      return True
    gflags.DEFINE_integer('test_flag', None, 'Usual integer flag',
                         flag_values=self.flag_values)
    gflags.RegisterValidator('test_flag',
                            Checker,
                            message='Errors happen',
                            flag_values=self.flag_values)

    argv = ('./program', '--test_flag=1')
    self.flag_values(argv)
    self.assertEquals(1, self.flag_values.test_flag)
    self.assertEquals([1], self.call_args)

  def testValidatorNotCalledWhenOtherFlagIsChanged(self):
    def Checker(x):
      self.call_args.append(x)
      return True
    gflags.DEFINE_integer('test_flag', 1, 'Usual integer flag',
                         flag_values=self.flag_values)
    gflags.DEFINE_integer('other_flag', 2, 'Other integer flag',
                         flag_values=self.flag_values)
    gflags.RegisterValidator('test_flag',
                            Checker,
                            message='Errors happen',
                            flag_values=self.flag_values)

    argv = ('./program')
    self.flag_values(argv)
    self.assertEquals(1, self.flag_values.test_flag)
    self.flag_values.other_flag = 3
    self.assertEquals([1], self.call_args)

  def testExceptionRaisedIfCheckerFails(self):
    def Checker(x):
      self.call_args.append(x)
      return x == 1
    gflags.DEFINE_integer('test_flag', None, 'Usual integer flag',
                         flag_values=self.flag_values)
    gflags.RegisterValidator('test_flag',
                            Checker,
                            message='Errors happen',
                            flag_values=self.flag_values)

    argv = ('./program', '--test_flag=1')
    self.flag_values(argv)
    try:
      self.flag_values.test_flag = 2
      raise AssertionError('gflags.IllegalFlagValue expected')
    except gflags.IllegalFlagValue, e:
      self.assertEquals('flag --test_flag=2: Errors happen', str(e))
    self.assertEquals([1, 2], self.call_args)

  def testExceptionRaisedIfCheckerRaisesException(self):
    def Checker(x):
      self.call_args.append(x)
      if x == 1:
        return True
      raise gflags_validators.Error('Specific message')
    gflags.DEFINE_integer('test_flag', None, 'Usual integer flag',
                         flag_values=self.flag_values)
    gflags.RegisterValidator('test_flag',
                            Checker,
                            message='Errors happen',
                            flag_values=self.flag_values)

    argv = ('./program', '--test_flag=1')
    self.flag_values(argv)
    try:
      self.flag_values.test_flag = 2
      raise AssertionError('gflags.IllegalFlagValue expected')
    except gflags.IllegalFlagValue, e:
      self.assertEquals('flag --test_flag=2: Specific message', str(e))
    self.assertEquals([1, 2], self.call_args)

  def testErrorMessageWhenCheckerReturnsFalseOnStart(self):
    def Checker(x):
      self.call_args.append(x)
      return False
    gflags.DEFINE_integer('test_flag', None, 'Usual integer flag',
                         flag_values=self.flag_values)
    gflags.RegisterValidator('test_flag',
                            Checker,
                            message='Errors happen',
                            flag_values=self.flag_values)

    argv = ('./program', '--test_flag=1')
    try:
      self.flag_values(argv)
      raise AssertionError('gflags.IllegalFlagValue expected')
    except gflags.IllegalFlagValue, e:
      self.assertEquals('flag --test_flag=1: Errors happen', str(e))
    self.assertEquals([1], self.call_args)

  def testErrorMessageWhenCheckerRaisesExceptionOnStart(self):
    def Checker(x):
      self.call_args.append(x)
      raise gflags_validators.Error('Specific message')
    gflags.DEFINE_integer('test_flag', None, 'Usual integer flag',
                         flag_values=self.flag_values)
    gflags.RegisterValidator('test_flag',
                            Checker,
                            message='Errors happen',
                            flag_values=self.flag_values)

    argv = ('./program', '--test_flag=1')
    try:
      self.flag_values(argv)
      raise AssertionError('IllegalFlagValue expected')
    except gflags.IllegalFlagValue, e:
      self.assertEquals('flag --test_flag=1: Specific message', str(e))
    self.assertEquals([1], self.call_args)

  def testValidatorsCheckedInOrder(self):

    def Required(x):
      self.calls.append('Required')
      return x is not None

    def Even(x):
      self.calls.append('Even')
      return x % 2 == 0

    self.calls = []
    self._DefineFlagAndValidators(Required, Even)
    self.assertEquals(['Required', 'Even'], self.calls)

    self.calls = []
    self._DefineFlagAndValidators(Even, Required)
    self.assertEquals(['Even', 'Required'], self.calls)

  def _DefineFlagAndValidators(self, first_validator, second_validator):
    local_flags = gflags.FlagValues()
    gflags.DEFINE_integer('test_flag', 2, 'test flag', flag_values=local_flags)
    gflags.RegisterValidator('test_flag',
                            first_validator,
                            message='',
                            flag_values=local_flags)
    gflags.RegisterValidator('test_flag',
                            second_validator,
                            message='',
                            flag_values=local_flags)
    argv = ('./program')
    local_flags(argv)


if __name__ == '__main__':
  googletest.main()

########NEW FILE########
__FILENAME__ = iri2uri
"""
iri2uri

Converts an IRI to a URI.

"""
__author__ = "Joe Gregorio (joe@bitworking.org)"
__copyright__ = "Copyright 2006, Joe Gregorio"
__contributors__ = []
__version__ = "1.0.0"
__license__ = "MIT"
__history__ = """
"""

import urlparse


# Convert an IRI to a URI following the rules in RFC 3987
#
# The characters we need to enocde and escape are defined in the spec:
#
# iprivate =  %xE000-F8FF / %xF0000-FFFFD / %x100000-10FFFD
# ucschar = %xA0-D7FF / %xF900-FDCF / %xFDF0-FFEF
#         / %x10000-1FFFD / %x20000-2FFFD / %x30000-3FFFD
#         / %x40000-4FFFD / %x50000-5FFFD / %x60000-6FFFD
#         / %x70000-7FFFD / %x80000-8FFFD / %x90000-9FFFD
#         / %xA0000-AFFFD / %xB0000-BFFFD / %xC0000-CFFFD
#         / %xD0000-DFFFD / %xE1000-EFFFD

escape_range = [
    (0xA0, 0xD7FF),
    (0xE000, 0xF8FF),
    (0xF900, 0xFDCF),
    (0xFDF0, 0xFFEF),
    (0x10000, 0x1FFFD),
    (0x20000, 0x2FFFD),
    (0x30000, 0x3FFFD),
    (0x40000, 0x4FFFD),
    (0x50000, 0x5FFFD),
    (0x60000, 0x6FFFD),
    (0x70000, 0x7FFFD),
    (0x80000, 0x8FFFD),
    (0x90000, 0x9FFFD),
    (0xA0000, 0xAFFFD),
    (0xB0000, 0xBFFFD),
    (0xC0000, 0xCFFFD),
    (0xD0000, 0xDFFFD),
    (0xE1000, 0xEFFFD),
    (0xF0000, 0xFFFFD),
    (0x100000, 0x10FFFD),
]

def encode(c):
    retval = c
    i = ord(c)
    for low, high in escape_range:
        if i < low:
            break
        if i >= low and i <= high:
            retval = "".join(["%%%2X" % ord(o) for o in c.encode('utf-8')])
            break
    return retval


def iri2uri(uri):
    """Convert an IRI to a URI. Note that IRIs must be
    passed in a unicode strings. That is, do not utf-8 encode
    the IRI before passing it into the function."""
    if isinstance(uri ,unicode):
        (scheme, authority, path, query, fragment) = urlparse.urlsplit(uri)
        authority = authority.encode('idna')
        # For each character in 'ucschar' or 'iprivate'
        #  1. encode as utf-8
        #  2. then %-encode each octet of that utf-8
        uri = urlparse.urlunsplit((scheme, authority, path, query, fragment))
        uri = "".join([encode(c) for c in uri])
    return uri

if __name__ == "__main__":
    import unittest

    class Test(unittest.TestCase):

        def test_uris(self):
            """Test that URIs are invariant under the transformation."""
            invariant = [
                u"ftp://ftp.is.co.za/rfc/rfc1808.txt",
                u"http://www.ietf.org/rfc/rfc2396.txt",
                u"ldap://[2001:db8::7]/c=GB?objectClass?one",
                u"mailto:John.Doe@example.com",
                u"news:comp.infosystems.www.servers.unix",
                u"tel:+1-816-555-1212",
                u"telnet://192.0.2.16:80/",
                u"urn:oasis:names:specification:docbook:dtd:xml:4.1.2" ]
            for uri in invariant:
                self.assertEqual(uri, iri2uri(uri))

        def test_iri(self):
            """ Test that the right type of escaping is done for each part of the URI."""
            self.assertEqual("http://xn--o3h.com/%E2%98%84", iri2uri(u"http://\N{COMET}.com/\N{COMET}"))
            self.assertEqual("http://bitworking.org/?fred=%E2%98%84", iri2uri(u"http://bitworking.org/?fred=\N{COMET}"))
            self.assertEqual("http://bitworking.org/#%E2%98%84", iri2uri(u"http://bitworking.org/#\N{COMET}"))
            self.assertEqual("#%E2%98%84", iri2uri(u"#\N{COMET}"))
            self.assertEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}"))
            self.assertEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}")))
            self.assertNotEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}".encode('utf-8')))

    unittest.main()



########NEW FILE########
__FILENAME__ = socks
"""SocksiPy - Python SOCKS module.
Version 1.00

Copyright 2006 Dan-Haim. All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of Dan Haim nor the names of his contributors may be used
   to endorse or promote products derived from this software without specific
   prior written permission.

THIS SOFTWARE IS PROVIDED BY DAN HAIM "AS IS" AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL DAN HAIM OR HIS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA
OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMANGE.


This module provides a standard socket-like interface for Python
for tunneling connections through SOCKS proxies.

"""

"""

Minor modifications made by Christopher Gilbert (http://motomastyle.com/)
for use in PyLoris (http://pyloris.sourceforge.net/)

Minor modifications made by Mario Vilas (http://breakingcode.wordpress.com/)
mainly to merge bug fixes found in Sourceforge

"""

import base64
import socket
import struct
import sys

if getattr(socket, 'socket', None) is None:
    raise ImportError('socket.socket missing, proxy support unusable')

PROXY_TYPE_SOCKS4 = 1
PROXY_TYPE_SOCKS5 = 2
PROXY_TYPE_HTTP = 3
PROXY_TYPE_HTTP_NO_TUNNEL = 4

_defaultproxy = None
_orgsocket = socket.socket

class ProxyError(Exception): pass
class GeneralProxyError(ProxyError): pass
class Socks5AuthError(ProxyError): pass
class Socks5Error(ProxyError): pass
class Socks4Error(ProxyError): pass
class HTTPError(ProxyError): pass

_generalerrors = ("success",
    "invalid data",
    "not connected",
    "not available",
    "bad proxy type",
    "bad input")

_socks5errors = ("succeeded",
    "general SOCKS server failure",
    "connection not allowed by ruleset",
    "Network unreachable",
    "Host unreachable",
    "Connection refused",
    "TTL expired",
    "Command not supported",
    "Address type not supported",
    "Unknown error")

_socks5autherrors = ("succeeded",
    "authentication is required",
    "all offered authentication methods were rejected",
    "unknown username or invalid password",
    "unknown error")

_socks4errors = ("request granted",
    "request rejected or failed",
    "request rejected because SOCKS server cannot connect to identd on the client",
    "request rejected because the client program and identd report different user-ids",
    "unknown error")

def setdefaultproxy(proxytype=None, addr=None, port=None, rdns=True, username=None, password=None):
    """setdefaultproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
    Sets a default proxy which all further socksocket objects will use,
    unless explicitly changed.
    """
    global _defaultproxy
    _defaultproxy = (proxytype, addr, port, rdns, username, password)

def wrapmodule(module):
    """wrapmodule(module)
    Attempts to replace a module's socket library with a SOCKS socket. Must set
    a default proxy using setdefaultproxy(...) first.
    This will only work on modules that import socket directly into the namespace;
    most of the Python Standard Library falls into this category.
    """
    if _defaultproxy != None:
        module.socket.socket = socksocket
    else:
        raise GeneralProxyError((4, "no proxy specified"))

class socksocket(socket.socket):
    """socksocket([family[, type[, proto]]]) -> socket object
    Open a SOCKS enabled socket. The parameters are the same as
    those of the standard socket init. In order for SOCKS to work,
    you must specify family=AF_INET, type=SOCK_STREAM and proto=0.
    """

    def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, _sock=None):
        _orgsocket.__init__(self, family, type, proto, _sock)
        if _defaultproxy != None:
            self.__proxy = _defaultproxy
        else:
            self.__proxy = (None, None, None, None, None, None)
        self.__proxysockname = None
        self.__proxypeername = None
        self.__httptunnel = True

    def __recvall(self, count):
        """__recvall(count) -> data
        Receive EXACTLY the number of bytes requested from the socket.
        Blocks until the required number of bytes have been received.
        """
        data = self.recv(count)
        while len(data) < count:
            d = self.recv(count-len(data))
            if not d: raise GeneralProxyError((0, "connection closed unexpectedly"))
            data = data + d
        return data

    def sendall(self, content, *args):
        """ override socket.socket.sendall method to rewrite the header
        for non-tunneling proxies if needed
        """
        if not self.__httptunnel:
            content = self.__rewriteproxy(content)
        return super(socksocket, self).sendall(content, *args)

    def __rewriteproxy(self, header):
        """ rewrite HTTP request headers to support non-tunneling proxies
        (i.e. those which do not support the CONNECT method).
        This only works for HTTP (not HTTPS) since HTTPS requires tunneling.
        """
        host, endpt = None, None
        hdrs = header.split("\r\n")
        for hdr in hdrs:
            if hdr.lower().startswith("host:"):
                host = hdr
            elif hdr.lower().startswith("get") or hdr.lower().startswith("post"):
                endpt = hdr
        if host and endpt:
            hdrs.remove(host)
            hdrs.remove(endpt)
            host = host.split(" ")[1]
            endpt = endpt.split(" ")
            if (self.__proxy[4] != None and self.__proxy[5] != None):
                hdrs.insert(0, self.__getauthheader())
            hdrs.insert(0, "Host: %s" % host)
            hdrs.insert(0, "%s http://%s%s %s" % (endpt[0], host, endpt[1], endpt[2]))
        return "\r\n".join(hdrs)

    def __getauthheader(self):
        auth = self.__proxy[4] + ":" + self.__proxy[5]
        return "Proxy-Authorization: Basic " + base64.b64encode(auth)

    def setproxy(self, proxytype=None, addr=None, port=None, rdns=True, username=None, password=None):
        """setproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
        Sets the proxy to be used.
        proxytype -    The type of the proxy to be used. Three types
                are supported: PROXY_TYPE_SOCKS4 (including socks4a),
                PROXY_TYPE_SOCKS5 and PROXY_TYPE_HTTP
        addr -        The address of the server (IP or DNS).
        port -        The port of the server. Defaults to 1080 for SOCKS
                servers and 8080 for HTTP proxy servers.
        rdns -        Should DNS queries be preformed on the remote side
                (rather than the local side). The default is True.
                Note: This has no effect with SOCKS4 servers.
        username -    Username to authenticate with to the server.
                The default is no authentication.
        password -    Password to authenticate with to the server.
                Only relevant when username is also provided.
        """
        self.__proxy = (proxytype, addr, port, rdns, username, password)

    def __negotiatesocks5(self, destaddr, destport):
        """__negotiatesocks5(self,destaddr,destport)
        Negotiates a connection through a SOCKS5 server.
        """
        # First we'll send the authentication packages we support.
        if (self.__proxy[4]!=None) and (self.__proxy[5]!=None):
            # The username/password details were supplied to the
            # setproxy method so we support the USERNAME/PASSWORD
            # authentication (in addition to the standard none).
            self.sendall(struct.pack('BBBB', 0x05, 0x02, 0x00, 0x02))
        else:
            # No username/password were entered, therefore we
            # only support connections with no authentication.
            self.sendall(struct.pack('BBB', 0x05, 0x01, 0x00))
        # We'll receive the server's response to determine which
        # method was selected
        chosenauth = self.__recvall(2)
        if chosenauth[0:1] != chr(0x05).encode():
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        # Check the chosen authentication method
        if chosenauth[1:2] == chr(0x00).encode():
            # No authentication is required
            pass
        elif chosenauth[1:2] == chr(0x02).encode():
            # Okay, we need to perform a basic username/password
            # authentication.
            self.sendall(chr(0x01).encode() + chr(len(self.__proxy[4])) + self.__proxy[4] + chr(len(self.__proxy[5])) + self.__proxy[5])
            authstat = self.__recvall(2)
            if authstat[0:1] != chr(0x01).encode():
                # Bad response
                self.close()
                raise GeneralProxyError((1, _generalerrors[1]))
            if authstat[1:2] != chr(0x00).encode():
                # Authentication failed
                self.close()
                raise Socks5AuthError((3, _socks5autherrors[3]))
            # Authentication succeeded
        else:
            # Reaching here is always bad
            self.close()
            if chosenauth[1] == chr(0xFF).encode():
                raise Socks5AuthError((2, _socks5autherrors[2]))
            else:
                raise GeneralProxyError((1, _generalerrors[1]))
        # Now we can request the actual connection
        req = struct.pack('BBB', 0x05, 0x01, 0x00)
        # If the given destination address is an IP address, we'll
        # use the IPv4 address request even if remote resolving was specified.
        try:
            ipaddr = socket.inet_aton(destaddr)
            req = req + chr(0x01).encode() + ipaddr
        except socket.error:
            # Well it's not an IP number,  so it's probably a DNS name.
            if self.__proxy[3]:
                # Resolve remotely
                ipaddr = None
                req = req + chr(0x03).encode() + chr(len(destaddr)).encode() + destaddr
            else:
                # Resolve locally
                ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
                req = req + chr(0x01).encode() + ipaddr
        req = req + struct.pack(">H", destport)
        self.sendall(req)
        # Get the response
        resp = self.__recvall(4)
        if resp[0:1] != chr(0x05).encode():
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        elif resp[1:2] != chr(0x00).encode():
            # Connection failed
            self.close()
            if ord(resp[1:2])<=8:
                raise Socks5Error((ord(resp[1:2]), _socks5errors[ord(resp[1:2])]))
            else:
                raise Socks5Error((9, _socks5errors[9]))
        # Get the bound address/port
        elif resp[3:4] == chr(0x01).encode():
            boundaddr = self.__recvall(4)
        elif resp[3:4] == chr(0x03).encode():
            resp = resp + self.recv(1)
            boundaddr = self.__recvall(ord(resp[4:5]))
        else:
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        boundport = struct.unpack(">H", self.__recvall(2))[0]
        self.__proxysockname = (boundaddr, boundport)
        if ipaddr != None:
            self.__proxypeername = (socket.inet_ntoa(ipaddr), destport)
        else:
            self.__proxypeername = (destaddr, destport)

    def getproxysockname(self):
        """getsockname() -> address info
        Returns the bound IP address and port number at the proxy.
        """
        return self.__proxysockname

    def getproxypeername(self):
        """getproxypeername() -> address info
        Returns the IP and port number of the proxy.
        """
        return _orgsocket.getpeername(self)

    def getpeername(self):
        """getpeername() -> address info
        Returns the IP address and port number of the destination
        machine (note: getproxypeername returns the proxy)
        """
        return self.__proxypeername

    def __negotiatesocks4(self,destaddr,destport):
        """__negotiatesocks4(self,destaddr,destport)
        Negotiates a connection through a SOCKS4 server.
        """
        # Check if the destination address provided is an IP address
        rmtrslv = False
        try:
            ipaddr = socket.inet_aton(destaddr)
        except socket.error:
            # It's a DNS name. Check where it should be resolved.
            if self.__proxy[3]:
                ipaddr = struct.pack("BBBB", 0x00, 0x00, 0x00, 0x01)
                rmtrslv = True
            else:
                ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
        # Construct the request packet
        req = struct.pack(">BBH", 0x04, 0x01, destport) + ipaddr
        # The username parameter is considered userid for SOCKS4
        if self.__proxy[4] != None:
            req = req + self.__proxy[4]
        req = req + chr(0x00).encode()
        # DNS name if remote resolving is required
        # NOTE: This is actually an extension to the SOCKS4 protocol
        # called SOCKS4A and may not be supported in all cases.
        if rmtrslv:
            req = req + destaddr + chr(0x00).encode()
        self.sendall(req)
        # Get the response from the server
        resp = self.__recvall(8)
        if resp[0:1] != chr(0x00).encode():
            # Bad data
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        if resp[1:2] != chr(0x5A).encode():
            # Server returned an error
            self.close()
            if ord(resp[1:2]) in (91, 92, 93):
                self.close()
                raise Socks4Error((ord(resp[1:2]), _socks4errors[ord(resp[1:2]) - 90]))
            else:
                raise Socks4Error((94, _socks4errors[4]))
        # Get the bound address/port
        self.__proxysockname = (socket.inet_ntoa(resp[4:]), struct.unpack(">H", resp[2:4])[0])
        if rmtrslv != None:
            self.__proxypeername = (socket.inet_ntoa(ipaddr), destport)
        else:
            self.__proxypeername = (destaddr, destport)

    def __negotiatehttp(self, destaddr, destport):
        """__negotiatehttp(self,destaddr,destport)
        Negotiates a connection through an HTTP server.
        """
        # If we need to resolve locally, we do this now
        if not self.__proxy[3]:
            addr = socket.gethostbyname(destaddr)
        else:
            addr = destaddr
        headers =  ["CONNECT ", addr, ":", str(destport), " HTTP/1.1\r\n"]
        headers += ["Host: ", destaddr, "\r\n"]
        if (self.__proxy[4] != None and self.__proxy[5] != None):
                headers += [self.__getauthheader(), "\r\n"]
        headers.append("\r\n")
        self.sendall("".join(headers).encode())
        # We read the response until we get the string "\r\n\r\n"
        resp = self.recv(1)
        while resp.find("\r\n\r\n".encode()) == -1:
            resp = resp + self.recv(1)
        # We just need the first line to check if the connection
        # was successful
        statusline = resp.splitlines()[0].split(" ".encode(), 2)
        if statusline[0] not in ("HTTP/1.0".encode(), "HTTP/1.1".encode()):
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        try:
            statuscode = int(statusline[1])
        except ValueError:
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        if statuscode != 200:
            self.close()
            raise HTTPError((statuscode, statusline[2]))
        self.__proxysockname = ("0.0.0.0", 0)
        self.__proxypeername = (addr, destport)

    def connect(self, destpair):
        """connect(self, despair)
        Connects to the specified destination through a proxy.
        destpar - A tuple of the IP/DNS address and the port number.
        (identical to socket's connect).
        To select the proxy server use setproxy().
        """
        # Do a minimal input check first
        if (not type(destpair) in (list,tuple)) or (len(destpair) < 2) or (not isinstance(destpair[0], basestring)) or (type(destpair[1]) != int):
            raise GeneralProxyError((5, _generalerrors[5]))
        if self.__proxy[0] == PROXY_TYPE_SOCKS5:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 1080
            _orgsocket.connect(self, (self.__proxy[1], portnum))
            self.__negotiatesocks5(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_SOCKS4:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 1080
            _orgsocket.connect(self,(self.__proxy[1], portnum))
            self.__negotiatesocks4(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_HTTP:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 8080
            _orgsocket.connect(self,(self.__proxy[1], portnum))
            self.__negotiatehttp(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_HTTP_NO_TUNNEL:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 8080
            _orgsocket.connect(self,(self.__proxy[1],portnum))
            if destpair[1] == 443:
                self.__negotiatehttp(destpair[0],destpair[1])
            else:
                self.__httptunnel = False
        elif self.__proxy[0] == None:
            _orgsocket.connect(self, (destpair[0], destpair[1]))
        else:
            raise GeneralProxyError((4, _generalerrors[4]))

########NEW FILE########
__FILENAME__ = socket
from realsocket import gaierror, error, getaddrinfo, SOCK_STREAM

########NEW FILE########
__FILENAME__ = test_proxies
import unittest
import errno
import os
import signal
import subprocess
import tempfile

import nose

import httplib2
from httplib2 import socks
from httplib2.test import miniserver

tinyproxy_cfg = """
User "%(user)s"
Port %(port)s
Listen 127.0.0.1
PidFile "%(pidfile)s"
LogFile "%(logfile)s"
MaxClients 2
StartServers 1
LogLevel Info
"""


class FunctionalProxyHttpTest(unittest.TestCase):
    def setUp(self):
        if not socks:
            raise nose.SkipTest('socks module unavailable')
        if not subprocess:
            raise nose.SkipTest('subprocess module unavailable')

        # start a short-lived miniserver so we can get a likely port
        # for the proxy
        self.httpd, self.proxyport = miniserver.start_server(
            miniserver.ThisDirHandler)
        self.httpd.shutdown()
        self.httpd, self.port = miniserver.start_server(
            miniserver.ThisDirHandler)

        self.pidfile = tempfile.mktemp()
        self.logfile = tempfile.mktemp()
        fd, self.conffile = tempfile.mkstemp()
        f = os.fdopen(fd, 'w')
        our_cfg = tinyproxy_cfg % {'user': os.getlogin(),
                                   'pidfile': self.pidfile,
                                   'port': self.proxyport,
                                   'logfile': self.logfile}
        f.write(our_cfg)
        f.close()
        try:
            # TODO use subprocess.check_call when 2.4 is dropped
            ret = subprocess.call(['tinyproxy', '-c', self.conffile])
            self.assertEqual(0, ret)
        except OSError, e:
            if e.errno == errno.ENOENT:
                raise nose.SkipTest('tinyproxy not available')
            raise

    def tearDown(self):
        self.httpd.shutdown()
        try:
            pid = int(open(self.pidfile).read())
            os.kill(pid, signal.SIGTERM)
        except OSError, e:
            if e.errno == errno.ESRCH:
                print '\n\n\nTinyProxy Failed to start, log follows:'
                print open(self.logfile).read()
                print 'end tinyproxy log\n\n\n'
            raise
        map(os.unlink, (self.pidfile,
                        self.logfile,
                        self.conffile))

    def testSimpleProxy(self):
        proxy_info = httplib2.ProxyInfo(socks.PROXY_TYPE_HTTP,
                                        'localhost', self.proxyport)
        client = httplib2.Http(proxy_info=proxy_info)
        src = 'miniserver.py'
        response, body = client.request('http://localhost:%d/%s' %
                                        (self.port, src))
        self.assertEqual(response.status, 200)
        self.assertEqual(body, open(os.path.join(miniserver.HERE, src)).read())
        lf = open(self.logfile).read()
        expect = ('Established connection to host "127.0.0.1" '
                  'using file descriptor')
        self.assertTrue(expect in lf,
                        'tinyproxy did not proxy a request for miniserver')

########NEW FILE########
__FILENAME__ = miniserver
import logging
import os
import select
import SimpleHTTPServer
import SocketServer
import threading

HERE = os.path.dirname(__file__)
logger = logging.getLogger(__name__)


class ThisDirHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = path.split('?', 1)[0].split('#', 1)[0]
        return os.path.join(HERE, *filter(None, path.split('/')))

    def log_message(self, s, *args):
        # output via logging so nose can catch it
        logger.info(s, *args)


class ShutdownServer(SocketServer.TCPServer):
    """Mixin that allows serve_forever to be shut down.

    The methods in this mixin are backported from SocketServer.py in the Python
    2.6.4 standard library. The mixin is unnecessary in 2.6 and later, when
    BaseServer supports the shutdown method directly.
    """

    def __init__(self, *args, **kwargs):
        SocketServer.TCPServer.__init__(self, *args, **kwargs)
        self.__is_shut_down = threading.Event()
        self.__serving = False

    def serve_forever(self, poll_interval=0.1):
        """Handle one request at a time until shutdown.

        Polls for shutdown every poll_interval seconds. Ignores
        self.timeout. If you need to do periodic tasks, do them in
        another thread.
        """
        self.__serving = True
        self.__is_shut_down.clear()
        while self.__serving:
            r, w, e = select.select([self.socket], [], [], poll_interval)
            if r:
                self._handle_request_noblock()
        self.__is_shut_down.set()

    def shutdown(self):
        """Stops the serve_forever loop.

        Blocks until the loop has finished. This must be called while
        serve_forever() is running in another thread, or it will deadlock.
        """
        self.__serving = False
        self.__is_shut_down.wait()

    def handle_request(self):
        """Handle one request, possibly blocking.

        Respects self.timeout.
        """
        # Support people who used socket.settimeout() to escape
        # handle_request before self.timeout was available.
        timeout = self.socket.gettimeout()
        if timeout is None:
            timeout = self.timeout
        elif self.timeout is not None:
            timeout = min(timeout, self.timeout)
        fd_sets = select.select([self], [], [], timeout)
        if not fd_sets[0]:
            self.handle_timeout()
            return
        self._handle_request_noblock()

    def _handle_request_noblock(self):
        """Handle one request, without blocking.

        I assume that select.select has returned that the socket is
        readable before this function was called, so there should be
        no risk of blocking in get_request().
        """
        try:
            request, client_address = self.get_request()
        except socket.error:
            return
        if self.verify_request(request, client_address):
            try:
                self.process_request(request, client_address)
            except:
                self.handle_error(request, client_address)
                self.close_request(request)


def start_server(handler):
    httpd = ShutdownServer(("", 0), handler)
    threading.Thread(target=httpd.serve_forever).start()
    _, port = httpd.socket.getsockname()
    return httpd, port

########NEW FILE########
__FILENAME__ = smoke_test
import os
import unittest

import httplib2

from httplib2.test import miniserver


class HttpSmokeTest(unittest.TestCase):
    def setUp(self):
        self.httpd, self.port = miniserver.start_server(
            miniserver.ThisDirHandler)

    def tearDown(self):
        self.httpd.shutdown()

    def testGetFile(self):
        client = httplib2.Http()
        src = 'miniserver.py'
        response, body = client.request('http://localhost:%d/%s' %
                                        (self.port, src))
        self.assertEqual(response.status, 200)
        self.assertEqual(body, open(os.path.join(miniserver.HERE, src)).read())

########NEW FILE########
__FILENAME__ = test_no_socket
"""Tests for httplib2 when the socket module is missing.

This helps ensure compatibility with environments such as AppEngine.
"""
import os
import sys
import unittest

import httplib2

class MissingSocketTest(unittest.TestCase):
    def setUp(self):
        self._oldsocks = httplib2.socks
        httplib2.socks = None

    def tearDown(self):
        httplib2.socks = self._oldsocks

    def testProxyDisabled(self):
        proxy_info = httplib2.ProxyInfo('blah',
                                        'localhost', 0)
        client = httplib2.Http(proxy_info=proxy_info)
        self.assertRaises(httplib2.ProxiesUnavailableError,
                          client.request, 'http://localhost:-1/')

########NEW FILE########
__FILENAME__ = anyjson
# Copyright (C) 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility module to import a JSON module

Hides all the messy details of exactly where
we get a simplejson module from.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'


try: # pragma: no cover
  # Should work for Python2.6 and higher.
  import json as simplejson
except ImportError: # pragma: no cover
  try:
    import simplejson
  except ImportError:
    # Try to import from django, should work on App Engine
    from django.utils import simplejson

########NEW FILE########
__FILENAME__ = appengine
# Copyright (C) 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utilities for Google App Engine

Utilities for making it easier to use OAuth 2.0 on Google App Engine.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import base64
import cgi
import httplib2
import logging
import os
import pickle
import time

from google.appengine.api import app_identity
from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import login_required
from google.appengine.ext.webapp.util import run_wsgi_app
from oauth2client import GOOGLE_AUTH_URI
from oauth2client import GOOGLE_REVOKE_URI
from oauth2client import GOOGLE_TOKEN_URI
from oauth2client import clientsecrets
from oauth2client import util
from oauth2client import xsrfutil
from oauth2client.anyjson import simplejson
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import AssertionCredentials
from oauth2client.client import Credentials
from oauth2client.client import Flow
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.client import Storage

# TODO(dhermes): Resolve import issue.
# This is a temporary fix for a Google internal issue.
try:
  from google.appengine.ext import ndb
except ImportError:
  ndb = None


logger = logging.getLogger(__name__)

OAUTH2CLIENT_NAMESPACE = 'oauth2client#ns'

XSRF_MEMCACHE_ID = 'xsrf_secret_key'


def _safe_html(s):
  """Escape text to make it safe to display.

  Args:
    s: string, The text to escape.

  Returns:
    The escaped text as a string.
  """
  return cgi.escape(s, quote=1).replace("'", '&#39;')


class InvalidClientSecretsError(Exception):
  """The client_secrets.json file is malformed or missing required fields."""


class InvalidXsrfTokenError(Exception):
  """The XSRF token is invalid or expired."""


class SiteXsrfSecretKey(db.Model):
  """Storage for the sites XSRF secret key.

  There will only be one instance stored of this model, the one used for the
  site.
  """
  secret = db.StringProperty()

if ndb is not None:
  class SiteXsrfSecretKeyNDB(ndb.Model):
    """NDB Model for storage for the sites XSRF secret key.

    Since this model uses the same kind as SiteXsrfSecretKey, it can be used
    interchangeably. This simply provides an NDB model for interacting with the
    same data the DB model interacts with.

    There should only be one instance stored of this model, the one used for the
    site.
    """
    secret = ndb.StringProperty()

    @classmethod
    def _get_kind(cls):
      """Return the kind name for this class."""
      return 'SiteXsrfSecretKey'


def _generate_new_xsrf_secret_key():
  """Returns a random XSRF secret key.
  """
  return os.urandom(16).encode("hex")


def xsrf_secret_key():
  """Return the secret key for use for XSRF protection.

  If the Site entity does not have a secret key, this method will also create
  one and persist it.

  Returns:
    The secret key.
  """
  secret = memcache.get(XSRF_MEMCACHE_ID, namespace=OAUTH2CLIENT_NAMESPACE)
  if not secret:
    # Load the one and only instance of SiteXsrfSecretKey.
    model = SiteXsrfSecretKey.get_or_insert(key_name='site')
    if not model.secret:
      model.secret = _generate_new_xsrf_secret_key()
      model.put()
    secret = model.secret
    memcache.add(XSRF_MEMCACHE_ID, secret, namespace=OAUTH2CLIENT_NAMESPACE)

  return str(secret)


class AppAssertionCredentials(AssertionCredentials):
  """Credentials object for App Engine Assertion Grants

  This object will allow an App Engine application to identify itself to Google
  and other OAuth 2.0 servers that can verify assertions. It can be used for the
  purpose of accessing data stored under an account assigned to the App Engine
  application itself.

  This credential does not require a flow to instantiate because it represents
  a two legged flow, and therefore has all of the required information to
  generate and refresh its own access tokens.
  """

  @util.positional(2)
  def __init__(self, scope, **kwargs):
    """Constructor for AppAssertionCredentials

    Args:
      scope: string or iterable of strings, scope(s) of the credentials being
        requested.
    """
    self.scope = util.scopes_to_string(scope)

    # Assertion type is no longer used, but still in the parent class signature.
    super(AppAssertionCredentials, self).__init__(None)

  @classmethod
  def from_json(cls, json):
    data = simplejson.loads(json)
    return AppAssertionCredentials(data['scope'])

  def _refresh(self, http_request):
    """Refreshes the access_token.

    Since the underlying App Engine app_identity implementation does its own
    caching we can skip all the storage hoops and just to a refresh using the
    API.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the refresh request.

    Raises:
      AccessTokenRefreshError: When the refresh fails.
    """
    try:
      scopes = self.scope.split()
      (token, _) = app_identity.get_access_token(scopes)
    except app_identity.Error, e:
      raise AccessTokenRefreshError(str(e))
    self.access_token = token


class FlowProperty(db.Property):
  """App Engine datastore Property for Flow.

  Utility property that allows easy storage and retrieval of an
  oauth2client.Flow"""

  # Tell what the user type is.
  data_type = Flow

  # For writing to datastore.
  def get_value_for_datastore(self, model_instance):
    flow = super(FlowProperty,
                 self).get_value_for_datastore(model_instance)
    return db.Blob(pickle.dumps(flow))

  # For reading from datastore.
  def make_value_from_datastore(self, value):
    if value is None:
      return None
    return pickle.loads(value)

  def validate(self, value):
    if value is not None and not isinstance(value, Flow):
      raise db.BadValueError('Property %s must be convertible '
                          'to a FlowThreeLegged instance (%s)' %
                          (self.name, value))
    return super(FlowProperty, self).validate(value)

  def empty(self, value):
    return not value


if ndb is not None:
  class FlowNDBProperty(ndb.PickleProperty):
    """App Engine NDB datastore Property for Flow.

    Serves the same purpose as the DB FlowProperty, but for NDB models. Since
    PickleProperty inherits from BlobProperty, the underlying representation of
    the data in the datastore will be the same as in the DB case.

    Utility property that allows easy storage and retrieval of an
    oauth2client.Flow
    """

    def _validate(self, value):
      """Validates a value as a proper Flow object.

      Args:
        value: A value to be set on the property.

      Raises:
        TypeError if the value is not an instance of Flow.
      """
      logger.info('validate: Got type %s', type(value))
      if value is not None and not isinstance(value, Flow):
        raise TypeError('Property %s must be convertible to a flow '
                        'instance; received: %s.' % (self._name, value))


class CredentialsProperty(db.Property):
  """App Engine datastore Property for Credentials.

  Utility property that allows easy storage and retrieval of
  oath2client.Credentials
  """

  # Tell what the user type is.
  data_type = Credentials

  # For writing to datastore.
  def get_value_for_datastore(self, model_instance):
    logger.info("get: Got type " + str(type(model_instance)))
    cred = super(CredentialsProperty,
                 self).get_value_for_datastore(model_instance)
    if cred is None:
      cred = ''
    else:
      cred = cred.to_json()
    return db.Blob(cred)

  # For reading from datastore.
  def make_value_from_datastore(self, value):
    logger.info("make: Got type " + str(type(value)))
    if value is None:
      return None
    if len(value) == 0:
      return None
    try:
      credentials = Credentials.new_from_json(value)
    except ValueError:
      credentials = None
    return credentials

  def validate(self, value):
    value = super(CredentialsProperty, self).validate(value)
    logger.info("validate: Got type " + str(type(value)))
    if value is not None and not isinstance(value, Credentials):
      raise db.BadValueError('Property %s must be convertible '
                          'to a Credentials instance (%s)' %
                            (self.name, value))
    #if value is not None and not isinstance(value, Credentials):
    #  return None
    return value


if ndb is not None:
  # TODO(dhermes): Turn this into a JsonProperty and overhaul the Credentials
  #                and subclass mechanics to use new_from_dict, to_dict,
  #                from_dict, etc.
  class CredentialsNDBProperty(ndb.BlobProperty):
    """App Engine NDB datastore Property for Credentials.

    Serves the same purpose as the DB CredentialsProperty, but for NDB models.
    Since CredentialsProperty stores data as a blob and this inherits from
    BlobProperty, the data in the datastore will be the same as in the DB case.

    Utility property that allows easy storage and retrieval of Credentials and
    subclasses.
    """
    def _validate(self, value):
      """Validates a value as a proper credentials object.

      Args:
        value: A value to be set on the property.

      Raises:
        TypeError if the value is not an instance of Credentials.
      """
      logger.info('validate: Got type %s', type(value))
      if value is not None and not isinstance(value, Credentials):
        raise TypeError('Property %s must be convertible to a credentials '
                        'instance; received: %s.' % (self._name, value))

    def _to_base_type(self, value):
      """Converts our validated value to a JSON serialized string.

      Args:
        value: A value to be set in the datastore.

      Returns:
        A JSON serialized version of the credential, else '' if value is None.
      """
      if value is None:
        return ''
      else:
        return value.to_json()

    def _from_base_type(self, value):
      """Converts our stored JSON string back to the desired type.

      Args:
        value: A value from the datastore to be converted to the desired type.

      Returns:
        A deserialized Credentials (or subclass) object, else None if the
            value can't be parsed.
      """
      if not value:
        return None
      try:
        # Uses the from_json method of the implied class of value
        credentials = Credentials.new_from_json(value)
      except ValueError:
        credentials = None
      return credentials


class StorageByKeyName(Storage):
  """Store and retrieve a credential to and from the App Engine datastore.

  This Storage helper presumes the Credentials have been stored as a
  CredentialsProperty or CredentialsNDBProperty on a datastore model class, and
  that entities are stored by key_name.
  """

  @util.positional(4)
  def __init__(self, model, key_name, property_name, cache=None):
    """Constructor for Storage.

    Args:
      model: db.Model or ndb.Model, model class
      key_name: string, key name for the entity that has the credentials
      property_name: string, name of the property that is a CredentialsProperty
        or CredentialsNDBProperty.
      cache: memcache, a write-through cache to put in front of the datastore.
        If the model you are using is an NDB model, using a cache will be
        redundant since the model uses an instance cache and memcache for you.
    """
    self._model = model
    self._key_name = key_name
    self._property_name = property_name
    self._cache = cache

  def _is_ndb(self):
    """Determine whether the model of the instance is an NDB model.

    Returns:
      Boolean indicating whether or not the model is an NDB or DB model.
    """
    # issubclass will fail if one of the arguments is not a class, only need
    # worry about new-style classes since ndb and db models are new-style
    if isinstance(self._model, type):
      if ndb is not None and issubclass(self._model, ndb.Model):
        return True
      elif issubclass(self._model, db.Model):
        return False

    raise TypeError('Model class not an NDB or DB model: %s.' % (self._model,))

  def _get_entity(self):
    """Retrieve entity from datastore.

    Uses a different model method for db or ndb models.

    Returns:
      Instance of the model corresponding to the current storage object
          and stored using the key name of the storage object.
    """
    if self._is_ndb():
      return self._model.get_by_id(self._key_name)
    else:
      return self._model.get_by_key_name(self._key_name)

  def _delete_entity(self):
    """Delete entity from datastore.

    Attempts to delete using the key_name stored on the object, whether or not
    the given key is in the datastore.
    """
    if self._is_ndb():
      ndb.Key(self._model, self._key_name).delete()
    else:
      entity_key = db.Key.from_path(self._model.kind(), self._key_name)
      db.delete(entity_key)

  def locked_get(self):
    """Retrieve Credential from datastore.

    Returns:
      oauth2client.Credentials
    """
    if self._cache:
      json = self._cache.get(self._key_name)
      if json:
        return Credentials.new_from_json(json)

    credentials = None
    entity = self._get_entity()
    if entity is not None:
      credentials = getattr(entity, self._property_name)
      if credentials and hasattr(credentials, 'set_store'):
        credentials.set_store(self)
        if self._cache:
          self._cache.set(self._key_name, credentials.to_json())

    return credentials

  def locked_put(self, credentials):
    """Write a Credentials to the datastore.

    Args:
      credentials: Credentials, the credentials to store.
    """
    entity = self._model.get_or_insert(self._key_name)
    setattr(entity, self._property_name, credentials)
    entity.put()
    if self._cache:
      self._cache.set(self._key_name, credentials.to_json())

  def locked_delete(self):
    """Delete Credential from datastore."""

    if self._cache:
      self._cache.delete(self._key_name)

    self._delete_entity()


class CredentialsModel(db.Model):
  """Storage for OAuth 2.0 Credentials

  Storage of the model is keyed by the user.user_id().
  """
  credentials = CredentialsProperty()


if ndb is not None:
  class CredentialsNDBModel(ndb.Model):
    """NDB Model for storage of OAuth 2.0 Credentials

    Since this model uses the same kind as CredentialsModel and has a property
    which can serialize and deserialize Credentials correctly, it can be used
    interchangeably with a CredentialsModel to access, insert and delete the
    same entities. This simply provides an NDB model for interacting with the
    same data the DB model interacts with.

    Storage of the model is keyed by the user.user_id().
    """
    credentials = CredentialsNDBProperty()

    @classmethod
    def _get_kind(cls):
      """Return the kind name for this class."""
      return 'CredentialsModel'


def _build_state_value(request_handler, user):
  """Composes the value for the 'state' parameter.

  Packs the current request URI and an XSRF token into an opaque string that
  can be passed to the authentication server via the 'state' parameter.

  Args:
    request_handler: webapp.RequestHandler, The request.
    user: google.appengine.api.users.User, The current user.

  Returns:
    The state value as a string.
  """
  uri = request_handler.request.url
  token = xsrfutil.generate_token(xsrf_secret_key(), user.user_id(),
                                  action_id=str(uri))
  return  uri + ':' + token


def _parse_state_value(state, user):
  """Parse the value of the 'state' parameter.

  Parses the value and validates the XSRF token in the state parameter.

  Args:
    state: string, The value of the state parameter.
    user: google.appengine.api.users.User, The current user.

  Raises:
    InvalidXsrfTokenError: if the XSRF token is invalid.

  Returns:
    The redirect URI.
  """
  uri, token = state.rsplit(':', 1)
  if not xsrfutil.validate_token(xsrf_secret_key(), token, user.user_id(),
                                 action_id=uri):
    raise InvalidXsrfTokenError()

  return uri


class OAuth2Decorator(object):
  """Utility for making OAuth 2.0 easier.

  Instantiate and then use with oauth_required or oauth_aware
  as decorators on webapp.RequestHandler methods.

  Example:

    decorator = OAuth2Decorator(
        client_id='837...ent.com',
        client_secret='Qh...wwI',
        scope='https://www.googleapis.com/auth/plus')


    class MainHandler(webapp.RequestHandler):

      @decorator.oauth_required
      def get(self):
        http = decorator.http()
        # http is authorized with the user's Credentials and can be used
        # in API calls

  """

  @util.positional(4)
  def __init__(self, client_id, client_secret, scope,
               auth_uri=GOOGLE_AUTH_URI,
               token_uri=GOOGLE_TOKEN_URI,
               revoke_uri=GOOGLE_REVOKE_URI,
               user_agent=None,
               message=None,
               callback_path='/oauth2callback',
               token_response_param=None,
               **kwargs):

    """Constructor for OAuth2Decorator

    Args:
      client_id: string, client identifier.
      client_secret: string client secret.
      scope: string or iterable of strings, scope(s) of the credentials being
        requested.
      auth_uri: string, URI for authorization endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      token_uri: string, URI for token endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      revoke_uri: string, URI for revoke endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      user_agent: string, User agent of your application, default to None.
      message: Message to display if there are problems with the OAuth 2.0
        configuration. The message may contain HTML and will be presented on the
        web interface for any method that uses the decorator.
      callback_path: string, The absolute path to use as the callback URI. Note
        that this must match up with the URI given when registering the
        application in the APIs Console.
      token_response_param: string. If provided, the full JSON response
        to the access token request will be encoded and included in this query
        parameter in the callback URI. This is useful with providers (e.g.
        wordpress.com) that include extra fields that the client may want.
      **kwargs: dict, Keyword arguments are be passed along as kwargs to the
        OAuth2WebServerFlow constructor.
    """
    self.flow = None
    self.credentials = None
    self._client_id = client_id
    self._client_secret = client_secret
    self._scope = util.scopes_to_string(scope)
    self._auth_uri = auth_uri
    self._token_uri = token_uri
    self._revoke_uri = revoke_uri
    self._user_agent = user_agent
    self._kwargs = kwargs
    self._message = message
    self._in_error = False
    self._callback_path = callback_path
    self._token_response_param = token_response_param

  def _display_error_message(self, request_handler):
    request_handler.response.out.write('<html><body>')
    request_handler.response.out.write(_safe_html(self._message))
    request_handler.response.out.write('</body></html>')

  def oauth_required(self, method):
    """Decorator that starts the OAuth 2.0 dance.

    Starts the OAuth dance for the logged in user if they haven't already
    granted access for this application.

    Args:
      method: callable, to be decorated method of a webapp.RequestHandler
        instance.
    """

    def check_oauth(request_handler, *args, **kwargs):
      if self._in_error:
        self._display_error_message(request_handler)
        return

      user = users.get_current_user()
      # Don't use @login_decorator as this could be used in a POST request.
      if not user:
        request_handler.redirect(users.create_login_url(
            request_handler.request.uri))
        return

      self._create_flow(request_handler)

      # Store the request URI in 'state' so we can use it later
      self.flow.params['state'] = _build_state_value(request_handler, user)
      self.credentials = StorageByKeyName(
          CredentialsModel, user.user_id(), 'credentials').get()

      if not self.has_credentials():
        return request_handler.redirect(self.authorize_url())
      try:
        return method(request_handler, *args, **kwargs)
      except AccessTokenRefreshError:
        return request_handler.redirect(self.authorize_url())

    return check_oauth

  def _create_flow(self, request_handler):
    """Create the Flow object.

    The Flow is calculated lazily since we don't know where this app is
    running until it receives a request, at which point redirect_uri can be
    calculated and then the Flow object can be constructed.

    Args:
      request_handler: webapp.RequestHandler, the request handler.
    """
    if self.flow is None:
      redirect_uri = request_handler.request.relative_url(
          self._callback_path) # Usually /oauth2callback
      self.flow = OAuth2WebServerFlow(self._client_id, self._client_secret,
                                      self._scope, redirect_uri=redirect_uri,
                                      user_agent=self._user_agent,
                                      auth_uri=self._auth_uri,
                                      token_uri=self._token_uri,
                                      revoke_uri=self._revoke_uri,
                                      **self._kwargs)

  def oauth_aware(self, method):
    """Decorator that sets up for OAuth 2.0 dance, but doesn't do it.

    Does all the setup for the OAuth dance, but doesn't initiate it.
    This decorator is useful if you want to create a page that knows
    whether or not the user has granted access to this application.
    From within a method decorated with @oauth_aware the has_credentials()
    and authorize_url() methods can be called.

    Args:
      method: callable, to be decorated method of a webapp.RequestHandler
        instance.
    """

    def setup_oauth(request_handler, *args, **kwargs):
      if self._in_error:
        self._display_error_message(request_handler)
        return

      user = users.get_current_user()
      # Don't use @login_decorator as this could be used in a POST request.
      if not user:
        request_handler.redirect(users.create_login_url(
            request_handler.request.uri))
        return

      self._create_flow(request_handler)

      self.flow.params['state'] = _build_state_value(request_handler, user)
      self.credentials = StorageByKeyName(
          CredentialsModel, user.user_id(), 'credentials').get()
      return method(request_handler, *args, **kwargs)
    return setup_oauth

  def has_credentials(self):
    """True if for the logged in user there are valid access Credentials.

    Must only be called from with a webapp.RequestHandler subclassed method
    that had been decorated with either @oauth_required or @oauth_aware.
    """
    return self.credentials is not None and not self.credentials.invalid

  def authorize_url(self):
    """Returns the URL to start the OAuth dance.

    Must only be called from with a webapp.RequestHandler subclassed method
    that had been decorated with either @oauth_required or @oauth_aware.
    """
    url = self.flow.step1_get_authorize_url()
    return str(url)

  def http(self):
    """Returns an authorized http instance.

    Must only be called from within an @oauth_required decorated method, or
    from within an @oauth_aware decorated method where has_credentials()
    returns True.
    """
    return self.credentials.authorize(httplib2.Http())

  @property
  def callback_path(self):
    """The absolute path where the callback will occur.

    Note this is the absolute path, not the absolute URI, that will be
    calculated by the decorator at runtime. See callback_handler() for how this
    should be used.

    Returns:
      The callback path as a string.
    """
    return self._callback_path


  def callback_handler(self):
    """RequestHandler for the OAuth 2.0 redirect callback.

    Usage:
       app = webapp.WSGIApplication([
         ('/index', MyIndexHandler),
         ...,
         (decorator.callback_path, decorator.callback_handler())
       ])

    Returns:
      A webapp.RequestHandler that handles the redirect back from the
      server during the OAuth 2.0 dance.
    """
    decorator = self

    class OAuth2Handler(webapp.RequestHandler):
      """Handler for the redirect_uri of the OAuth 2.0 dance."""

      @login_required
      def get(self):
        error = self.request.get('error')
        if error:
          errormsg = self.request.get('error_description', error)
          self.response.out.write(
              'The authorization request failed: %s' % _safe_html(errormsg))
        else:
          user = users.get_current_user()
          decorator._create_flow(self)
          credentials = decorator.flow.step2_exchange(self.request.params)
          StorageByKeyName(
              CredentialsModel, user.user_id(), 'credentials').put(credentials)
          redirect_uri = _parse_state_value(str(self.request.get('state')),
                                            user)

          if decorator._token_response_param and credentials.token_response:
            resp_json = simplejson.dumps(credentials.token_response)
            redirect_uri = util._add_query_parameter(
                redirect_uri, decorator._token_response_param, resp_json)

          self.redirect(redirect_uri)

    return OAuth2Handler

  def callback_application(self):
    """WSGI application for handling the OAuth 2.0 redirect callback.

    If you need finer grained control use `callback_handler` which returns just
    the webapp.RequestHandler.

    Returns:
      A webapp.WSGIApplication that handles the redirect back from the
      server during the OAuth 2.0 dance.
    """
    return webapp.WSGIApplication([
        (self.callback_path, self.callback_handler())
        ])


class OAuth2DecoratorFromClientSecrets(OAuth2Decorator):
  """An OAuth2Decorator that builds from a clientsecrets file.

  Uses a clientsecrets file as the source for all the information when
  constructing an OAuth2Decorator.

  Example:

    decorator = OAuth2DecoratorFromClientSecrets(
      os.path.join(os.path.dirname(__file__), 'client_secrets.json')
      scope='https://www.googleapis.com/auth/plus')


    class MainHandler(webapp.RequestHandler):

      @decorator.oauth_required
      def get(self):
        http = decorator.http()
        # http is authorized with the user's Credentials and can be used
        # in API calls
  """

  @util.positional(3)
  def __init__(self, filename, scope, message=None, cache=None):
    """Constructor

    Args:
      filename: string, File name of client secrets.
      scope: string or iterable of strings, scope(s) of the credentials being
        requested.
      message: string, A friendly string to display to the user if the
        clientsecrets file is missing or invalid. The message may contain HTML
        and will be presented on the web interface for any method that uses the
        decorator.
      cache: An optional cache service client that implements get() and set()
        methods. See clientsecrets.loadfile() for details.
    """
    client_type, client_info = clientsecrets.loadfile(filename, cache=cache)
    if client_type not in [
        clientsecrets.TYPE_WEB, clientsecrets.TYPE_INSTALLED]:
      raise InvalidClientSecretsError(
          'OAuth2Decorator doesn\'t support this OAuth 2.0 flow.')
    constructor_kwargs = {
      'auth_uri': client_info['auth_uri'],
      'token_uri': client_info['token_uri'],
      'message': message,
    }
    revoke_uri = client_info.get('revoke_uri')
    if revoke_uri is not None:
      constructor_kwargs['revoke_uri'] = revoke_uri
    super(OAuth2DecoratorFromClientSecrets, self).__init__(
        client_info['client_id'], client_info['client_secret'],
        scope, **constructor_kwargs)
    if message is not None:
      self._message = message
    else:
      self._message = 'Please configure your application for OAuth 2.0.'


@util.positional(2)
def oauth2decorator_from_clientsecrets(filename, scope,
                                       message=None, cache=None):
  """Creates an OAuth2Decorator populated from a clientsecrets file.

  Args:
    filename: string, File name of client secrets.
    scope: string or list of strings, scope(s) of the credentials being
      requested.
    message: string, A friendly string to display to the user if the
      clientsecrets file is missing or invalid. The message may contain HTML and
      will be presented on the web interface for any method that uses the
      decorator.
    cache: An optional cache service client that implements get() and set()
      methods. See clientsecrets.loadfile() for details.

  Returns: An OAuth2Decorator

  """
  return OAuth2DecoratorFromClientSecrets(filename, scope,
                                          message=message, cache=cache)

########NEW FILE########
__FILENAME__ = client
# Copyright (C) 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""An OAuth 2.0 client.

Tools for interacting with OAuth 2.0 protected resources.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import base64
import clientsecrets
import copy
import datetime
import httplib2
import logging
import os
import sys
import time
import urllib
import urlparse

from oauth2client import GOOGLE_AUTH_URI
from oauth2client import GOOGLE_REVOKE_URI
from oauth2client import GOOGLE_TOKEN_URI
from oauth2client import util
from oauth2client.anyjson import simplejson

HAS_OPENSSL = False
HAS_CRYPTO = False
try:
  from oauth2client import crypt
  HAS_CRYPTO = True
  if crypt.OpenSSLVerifier is not None:
    HAS_OPENSSL = True
except ImportError:
  pass

try:
  from urlparse import parse_qsl
except ImportError:
  from cgi import parse_qsl

logger = logging.getLogger(__name__)

# Expiry is stored in RFC3339 UTC format
EXPIRY_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

# Which certs to use to validate id_tokens received.
ID_TOKEN_VERIFICATON_CERTS = 'https://www.googleapis.com/oauth2/v1/certs'

# Constant to use for the out of band OAuth 2.0 flow.
OOB_CALLBACK_URN = 'urn:ietf:wg:oauth:2.0:oob'

# Google Data client libraries may need to set this to [401, 403].
REFRESH_STATUS_CODES = [401]


class Error(Exception):
  """Base error for this module."""


class FlowExchangeError(Error):
  """Error trying to exchange an authorization grant for an access token."""


class AccessTokenRefreshError(Error):
  """Error trying to refresh an expired access token."""


class TokenRevokeError(Error):
  """Error trying to revoke a token."""


class UnknownClientSecretsFlowError(Error):
  """The client secrets file called for an unknown type of OAuth 2.0 flow. """


class AccessTokenCredentialsError(Error):
  """Having only the access_token means no refresh is possible."""


class VerifyJwtTokenError(Error):
  """Could on retrieve certificates for validation."""


class NonAsciiHeaderError(Error):
  """Header names and values must be ASCII strings."""


def _abstract():
  raise NotImplementedError('You need to override this function')


class MemoryCache(object):
  """httplib2 Cache implementation which only caches locally."""

  def __init__(self):
    self.cache = {}

  def get(self, key):
    return self.cache.get(key)

  def set(self, key, value):
    self.cache[key] = value

  def delete(self, key):
    self.cache.pop(key, None)


class Credentials(object):
  """Base class for all Credentials objects.

  Subclasses must define an authorize() method that applies the credentials to
  an HTTP transport.

  Subclasses must also specify a classmethod named 'from_json' that takes a JSON
  string as input and returns an instaniated Credentials object.
  """

  NON_SERIALIZED_MEMBERS = ['store']

  def authorize(self, http):
    """Take an httplib2.Http instance (or equivalent) and authorizes it.

    Authorizes it for the set of credentials, usually by replacing
    http.request() with a method that adds in the appropriate headers and then
    delegates to the original Http.request() method.

    Args:
      http: httplib2.Http, an http object to be used to make the refresh
        request.
    """
    _abstract()

  def refresh(self, http):
    """Forces a refresh of the access_token.

    Args:
      http: httplib2.Http, an http object to be used to make the refresh
        request.
    """
    _abstract()

  def revoke(self, http):
    """Revokes a refresh_token and makes the credentials void.

    Args:
      http: httplib2.Http, an http object to be used to make the revoke
        request.
    """
    _abstract()

  def apply(self, headers):
    """Add the authorization to the headers.

    Args:
      headers: dict, the headers to add the Authorization header to.
    """
    _abstract()

  def _to_json(self, strip):
    """Utility function that creates JSON repr. of a Credentials object.

    Args:
      strip: array, An array of names of members to not include in the JSON.

    Returns:
       string, a JSON representation of this instance, suitable to pass to
       from_json().
    """
    t = type(self)
    d = copy.copy(self.__dict__)
    for member in strip:
      if member in d:
        del d[member]
    if 'token_expiry' in d and isinstance(d['token_expiry'], datetime.datetime):
      d['token_expiry'] = d['token_expiry'].strftime(EXPIRY_FORMAT)
    # Add in information we will need later to reconsistitue this instance.
    d['_class'] = t.__name__
    d['_module'] = t.__module__
    return simplejson.dumps(d)

  def to_json(self):
    """Creating a JSON representation of an instance of Credentials.

    Returns:
       string, a JSON representation of this instance, suitable to pass to
       from_json().
    """
    return self._to_json(Credentials.NON_SERIALIZED_MEMBERS)

  @classmethod
  def new_from_json(cls, s):
    """Utility class method to instantiate a Credentials subclass from a JSON
    representation produced by to_json().

    Args:
      s: string, JSON from to_json().

    Returns:
      An instance of the subclass of Credentials that was serialized with
      to_json().
    """
    data = simplejson.loads(s)
    # Find and call the right classmethod from_json() to restore the object.
    module = data['_module']
    try:
      m = __import__(module)
    except ImportError:
      # In case there's an object from the old package structure, update it
      module = module.replace('.apiclient', '')
      m = __import__(module)

    m = __import__(module, fromlist=module.split('.')[:-1])
    kls = getattr(m, data['_class'])
    from_json = getattr(kls, 'from_json')
    return from_json(s)

  @classmethod
  def from_json(cls, s):
    """Instantiate a Credentials object from a JSON description of it.

    The JSON should have been produced by calling .to_json() on the object.

    Args:
      data: dict, A deserialized JSON object.

    Returns:
      An instance of a Credentials subclass.
    """
    return Credentials()


class Flow(object):
  """Base class for all Flow objects."""
  pass


class Storage(object):
  """Base class for all Storage objects.

  Store and retrieve a single credential. This class supports locking
  such that multiple processes and threads can operate on a single
  store.
  """

  def acquire_lock(self):
    """Acquires any lock necessary to access this Storage.

    This lock is not reentrant.
    """
    pass

  def release_lock(self):
    """Release the Storage lock.

    Trying to release a lock that isn't held will result in a
    RuntimeError.
    """
    pass

  def locked_get(self):
    """Retrieve credential.

    The Storage lock must be held when this is called.

    Returns:
      oauth2client.client.Credentials
    """
    _abstract()

  def locked_put(self, credentials):
    """Write a credential.

    The Storage lock must be held when this is called.

    Args:
      credentials: Credentials, the credentials to store.
    """
    _abstract()

  def locked_delete(self):
    """Delete a credential.

    The Storage lock must be held when this is called.
    """
    _abstract()

  def get(self):
    """Retrieve credential.

    The Storage lock must *not* be held when this is called.

    Returns:
      oauth2client.client.Credentials
    """
    self.acquire_lock()
    try:
      return self.locked_get()
    finally:
      self.release_lock()

  def put(self, credentials):
    """Write a credential.

    The Storage lock must be held when this is called.

    Args:
      credentials: Credentials, the credentials to store.
    """
    self.acquire_lock()
    try:
      self.locked_put(credentials)
    finally:
      self.release_lock()

  def delete(self):
    """Delete credential.

    Frees any resources associated with storing the credential.
    The Storage lock must *not* be held when this is called.

    Returns:
      None
    """
    self.acquire_lock()
    try:
      return self.locked_delete()
    finally:
      self.release_lock()


def clean_headers(headers):
  """Forces header keys and values to be strings, i.e not unicode.

  The httplib module just concats the header keys and values in a way that may
  make the message header a unicode string, which, if it then tries to
  contatenate to a binary request body may result in a unicode decode error.

  Args:
    headers: dict, A dictionary of headers.

  Returns:
    The same dictionary but with all the keys converted to strings.
  """
  clean = {}
  try:
    for k, v in headers.iteritems():
      clean[str(k)] = str(v)
  except UnicodeEncodeError:
    raise NonAsciiHeaderError(k + ': ' + v)
  return clean


def _update_query_params(uri, params):
  """Updates a URI with new query parameters.

  Args:
    uri: string, A valid URI, with potential existing query parameters.
    params: dict, A dictionary of query parameters.

  Returns:
    The same URI but with the new query parameters added.
  """
  parts = list(urlparse.urlparse(uri))
  query_params = dict(parse_qsl(parts[4])) # 4 is the index of the query part
  query_params.update(params)
  parts[4] = urllib.urlencode(query_params)
  return urlparse.urlunparse(parts)


class OAuth2Credentials(Credentials):
  """Credentials object for OAuth 2.0.

  Credentials can be applied to an httplib2.Http object using the authorize()
  method, which then adds the OAuth 2.0 access token to each request.

  OAuth2Credentials objects may be safely pickled and unpickled.
  """

  @util.positional(8)
  def __init__(self, access_token, client_id, client_secret, refresh_token,
               token_expiry, token_uri, user_agent, revoke_uri=None,
               id_token=None, token_response=None):
    """Create an instance of OAuth2Credentials.

    This constructor is not usually called by the user, instead
    OAuth2Credentials objects are instantiated by the OAuth2WebServerFlow.

    Args:
      access_token: string, access token.
      client_id: string, client identifier.
      client_secret: string, client secret.
      refresh_token: string, refresh token.
      token_expiry: datetime, when the access_token expires.
      token_uri: string, URI of token endpoint.
      user_agent: string, The HTTP User-Agent to provide for this application.
      revoke_uri: string, URI for revoke endpoint. Defaults to None; a token
        can't be revoked if this is None.
      id_token: object, The identity of the resource owner.
      token_response: dict, the decoded response to the token request. None
        if a token hasn't been requested yet. Stored because some providers
        (e.g. wordpress.com) include extra fields that clients may want.

    Notes:
      store: callable, A callable that when passed a Credential
        will store the credential back to where it came from.
        This is needed to store the latest access_token if it
        has expired and been refreshed.
    """
    self.access_token = access_token
    self.client_id = client_id
    self.client_secret = client_secret
    self.refresh_token = refresh_token
    self.store = None
    self.token_expiry = token_expiry
    self.token_uri = token_uri
    self.user_agent = user_agent
    self.revoke_uri = revoke_uri
    self.id_token = id_token
    self.token_response = token_response

    # True if the credentials have been revoked or expired and can't be
    # refreshed.
    self.invalid = False

  def authorize(self, http):
    """Authorize an httplib2.Http instance with these credentials.

    The modified http.request method will add authentication headers to each
    request and will refresh access_tokens when a 401 is received on a
    request. In addition the http.request method has a credentials property,
    http.request.credentials, which is the Credentials object that authorized
    it.

    Args:
       http: An instance of httplib2.Http
         or something that acts like it.

    Returns:
       A modified instance of http that was passed in.

    Example:

      h = httplib2.Http()
      h = credentials.authorize(h)

    You can't create a new OAuth subclass of httplib2.Authenication
    because it never gets passed the absolute URI, which is needed for
    signing. So instead we have to overload 'request' with a closure
    that adds in the Authorization header and then calls the original
    version of 'request()'.
    """
    request_orig = http.request

    # The closure that will replace 'httplib2.Http.request'.
    @util.positional(1)
    def new_request(uri, method='GET', body=None, headers=None,
                    redirections=httplib2.DEFAULT_MAX_REDIRECTS,
                    connection_type=None):
      if not self.access_token:
        logger.info('Attempting refresh to obtain initial access_token')
        self._refresh(request_orig)

      # Modify the request headers to add the appropriate
      # Authorization header.
      if headers is None:
        headers = {}
      self.apply(headers)

      if self.user_agent is not None:
        if 'user-agent' in headers:
          headers['user-agent'] = self.user_agent + ' ' + headers['user-agent']
        else:
          headers['user-agent'] = self.user_agent

      resp, content = request_orig(uri, method, body, clean_headers(headers),
                                   redirections, connection_type)

      if resp.status in REFRESH_STATUS_CODES:
        logger.info('Refreshing due to a %s' % str(resp.status))
        self._refresh(request_orig)
        self.apply(headers)
        return request_orig(uri, method, body, clean_headers(headers),
                            redirections, connection_type)
      else:
        return (resp, content)

    # Replace the request method with our own closure.
    http.request = new_request

    # Set credentials as a property of the request method.
    setattr(http.request, 'credentials', self)

    return http

  def refresh(self, http):
    """Forces a refresh of the access_token.

    Args:
      http: httplib2.Http, an http object to be used to make the refresh
        request.
    """
    self._refresh(http.request)

  def revoke(self, http):
    """Revokes a refresh_token and makes the credentials void.

    Args:
      http: httplib2.Http, an http object to be used to make the revoke
        request.
    """
    self._revoke(http.request)

  def apply(self, headers):
    """Add the authorization to the headers.

    Args:
      headers: dict, the headers to add the Authorization header to.
    """
    headers['Authorization'] = 'Bearer ' + self.access_token

  def to_json(self):
    return self._to_json(Credentials.NON_SERIALIZED_MEMBERS)

  @classmethod
  def from_json(cls, s):
    """Instantiate a Credentials object from a JSON description of it. The JSON
    should have been produced by calling .to_json() on the object.

    Args:
      data: dict, A deserialized JSON object.

    Returns:
      An instance of a Credentials subclass.
    """
    data = simplejson.loads(s)
    if 'token_expiry' in data and not isinstance(data['token_expiry'],
        datetime.datetime):
      try:
        data['token_expiry'] = datetime.datetime.strptime(
            data['token_expiry'], EXPIRY_FORMAT)
      except:
        data['token_expiry'] = None
    retval = cls(
        data['access_token'],
        data['client_id'],
        data['client_secret'],
        data['refresh_token'],
        data['token_expiry'],
        data['token_uri'],
        data['user_agent'],
        revoke_uri=data.get('revoke_uri', None),
        id_token=data.get('id_token', None),
        token_response=data.get('token_response', None))
    retval.invalid = data['invalid']
    return retval

  @property
  def access_token_expired(self):
    """True if the credential is expired or invalid.

    If the token_expiry isn't set, we assume the token doesn't expire.
    """
    if self.invalid:
      return True

    if not self.token_expiry:
      return False

    now = datetime.datetime.utcnow()
    if now >= self.token_expiry:
      logger.info('access_token is expired. Now: %s, token_expiry: %s',
                  now, self.token_expiry)
      return True
    return False

  def set_store(self, store):
    """Set the Storage for the credential.

    Args:
      store: Storage, an implementation of Stroage object.
        This is needed to store the latest access_token if it
        has expired and been refreshed. This implementation uses
        locking to check for updates before updating the
        access_token.
    """
    self.store = store

  def _updateFromCredential(self, other):
    """Update this Credential from another instance."""
    self.__dict__.update(other.__getstate__())

  def __getstate__(self):
    """Trim the state down to something that can be pickled."""
    d = copy.copy(self.__dict__)
    del d['store']
    return d

  def __setstate__(self, state):
    """Reconstitute the state of the object from being pickled."""
    self.__dict__.update(state)
    self.store = None

  def _generate_refresh_request_body(self):
    """Generate the body that will be used in the refresh request."""
    body = urllib.urlencode({
        'grant_type': 'refresh_token',
        'client_id': self.client_id,
        'client_secret': self.client_secret,
        'refresh_token': self.refresh_token,
        })
    return body

  def _generate_refresh_request_headers(self):
    """Generate the headers that will be used in the refresh request."""
    headers = {
        'content-type': 'application/x-www-form-urlencoded',
    }

    if self.user_agent is not None:
      headers['user-agent'] = self.user_agent

    return headers

  def _refresh(self, http_request):
    """Refreshes the access_token.

    This method first checks by reading the Storage object if available.
    If a refresh is still needed, it holds the Storage lock until the
    refresh is completed.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the refresh request.

    Raises:
      AccessTokenRefreshError: When the refresh fails.
    """
    if not self.store:
      self._do_refresh_request(http_request)
    else:
      self.store.acquire_lock()
      try:
        new_cred = self.store.locked_get()
        if (new_cred and not new_cred.invalid and
            new_cred.access_token != self.access_token):
          logger.info('Updated access_token read from Storage')
          self._updateFromCredential(new_cred)
        else:
          self._do_refresh_request(http_request)
      finally:
        self.store.release_lock()

  def _do_refresh_request(self, http_request):
    """Refresh the access_token using the refresh_token.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the refresh request.

    Raises:
      AccessTokenRefreshError: When the refresh fails.
    """
    body = self._generate_refresh_request_body()
    headers = self._generate_refresh_request_headers()

    logger.info('Refreshing access_token')
    resp, content = http_request(
        self.token_uri, method='POST', body=body, headers=headers)
    if resp.status == 200:
      # TODO(jcgregorio) Raise an error if loads fails?
      d = simplejson.loads(content)
      self.token_response = d
      self.access_token = d['access_token']
      self.refresh_token = d.get('refresh_token', self.refresh_token)
      if 'expires_in' in d:
        self.token_expiry = datetime.timedelta(
            seconds=int(d['expires_in'])) + datetime.datetime.utcnow()
      else:
        self.token_expiry = None
      if self.store:
        self.store.locked_put(self)
    else:
      # An {'error':...} response body means the token is expired or revoked,
      # so we flag the credentials as such.
      logger.info('Failed to retrieve access token: %s' % content)
      error_msg = 'Invalid response %s.' % resp['status']
      try:
        d = simplejson.loads(content)
        if 'error' in d:
          error_msg = d['error']
          self.invalid = True
          if self.store:
            self.store.locked_put(self)
      except StandardError:
        pass
      raise AccessTokenRefreshError(error_msg)

  def _revoke(self, http_request):
    """Revokes the refresh_token and deletes the store if available.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the revoke request.
    """
    self._do_revoke(http_request, self.refresh_token)

  def _do_revoke(self, http_request, token):
    """Revokes the credentials and deletes the store if available.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the refresh request.
      token: A string used as the token to be revoked. Can be either an
        access_token or refresh_token.

    Raises:
      TokenRevokeError: If the revoke request does not return with a 200 OK.
    """
    logger.info('Revoking token')
    query_params = {'token': token}
    token_revoke_uri = _update_query_params(self.revoke_uri, query_params)
    resp, content = http_request(token_revoke_uri)
    if resp.status == 200:
      self.invalid = True
    else:
      error_msg = 'Invalid response %s.' % resp.status
      try:
        d = simplejson.loads(content)
        if 'error' in d:
          error_msg = d['error']
      except StandardError:
        pass
      raise TokenRevokeError(error_msg)

    if self.store:
      self.store.delete()


class AccessTokenCredentials(OAuth2Credentials):
  """Credentials object for OAuth 2.0.

  Credentials can be applied to an httplib2.Http object using the
  authorize() method, which then signs each request from that object
  with the OAuth 2.0 access token. This set of credentials is for the
  use case where you have acquired an OAuth 2.0 access_token from
  another place such as a JavaScript client or another web
  application, and wish to use it from Python. Because only the
  access_token is present it can not be refreshed and will in time
  expire.

  AccessTokenCredentials objects may be safely pickled and unpickled.

  Usage:
    credentials = AccessTokenCredentials('<an access token>',
      'my-user-agent/1.0')
    http = httplib2.Http()
    http = credentials.authorize(http)

  Exceptions:
    AccessTokenCredentialsExpired: raised when the access_token expires or is
      revoked.
  """

  def __init__(self, access_token, user_agent, revoke_uri=None):
    """Create an instance of OAuth2Credentials

    This is one of the few types if Credentials that you should contrust,
    Credentials objects are usually instantiated by a Flow.

    Args:
      access_token: string, access token.
      user_agent: string, The HTTP User-Agent to provide for this application.
      revoke_uri: string, URI for revoke endpoint. Defaults to None; a token
        can't be revoked if this is None.
    """
    super(AccessTokenCredentials, self).__init__(
        access_token,
        None,
        None,
        None,
        None,
        None,
        user_agent,
        revoke_uri=revoke_uri)


  @classmethod
  def from_json(cls, s):
    data = simplejson.loads(s)
    retval = AccessTokenCredentials(
        data['access_token'],
        data['user_agent'])
    return retval

  def _refresh(self, http_request):
    raise AccessTokenCredentialsError(
        'The access_token is expired or invalid and can\'t be refreshed.')

  def _revoke(self, http_request):
    """Revokes the access_token and deletes the store if available.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the revoke request.
    """
    self._do_revoke(http_request, self.access_token)


class AssertionCredentials(OAuth2Credentials):
  """Abstract Credentials object used for OAuth 2.0 assertion grants.

  This credential does not require a flow to instantiate because it
  represents a two legged flow, and therefore has all of the required
  information to generate and refresh its own access tokens. It must
  be subclassed to generate the appropriate assertion string.

  AssertionCredentials objects may be safely pickled and unpickled.
  """

  @util.positional(2)
  def __init__(self, assertion_type, user_agent=None,
               token_uri=GOOGLE_TOKEN_URI,
               revoke_uri=GOOGLE_REVOKE_URI,
               **unused_kwargs):
    """Constructor for AssertionFlowCredentials.

    Args:
      assertion_type: string, assertion type that will be declared to the auth
        server
      user_agent: string, The HTTP User-Agent to provide for this application.
      token_uri: string, URI for token endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      revoke_uri: string, URI for revoke endpoint.
    """
    super(AssertionCredentials, self).__init__(
        None,
        None,
        None,
        None,
        None,
        token_uri,
        user_agent,
        revoke_uri=revoke_uri)
    self.assertion_type = assertion_type

  def _generate_refresh_request_body(self):
    assertion = self._generate_assertion()

    body = urllib.urlencode({
        'assertion': assertion,
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        })

    return body

  def _generate_assertion(self):
    """Generate the assertion string that will be used in the access token
    request.
    """
    _abstract()

  def _revoke(self, http_request):
    """Revokes the access_token and deletes the store if available.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the revoke request.
    """
    self._do_revoke(http_request, self.access_token)


if HAS_CRYPTO:
  # PyOpenSSL and PyCrypto are not prerequisites for oauth2client, so if it is
  # missing then don't create the SignedJwtAssertionCredentials or the
  # verify_id_token() method.

  class SignedJwtAssertionCredentials(AssertionCredentials):
    """Credentials object used for OAuth 2.0 Signed JWT assertion grants.

    This credential does not require a flow to instantiate because it represents
    a two legged flow, and therefore has all of the required information to
    generate and refresh its own access tokens.

    SignedJwtAssertionCredentials requires either PyOpenSSL, or PyCrypto 2.6 or
    later. For App Engine you may also consider using AppAssertionCredentials.
    """

    MAX_TOKEN_LIFETIME_SECS = 3600 # 1 hour in seconds

    @util.positional(4)
    def __init__(self,
        service_account_name,
        private_key,
        scope,
        private_key_password='notasecret',
        user_agent=None,
        token_uri=GOOGLE_TOKEN_URI,
        revoke_uri=GOOGLE_REVOKE_URI,
        **kwargs):
      """Constructor for SignedJwtAssertionCredentials.

      Args:
        service_account_name: string, id for account, usually an email address.
        private_key: string, private key in PKCS12 or PEM format.
        scope: string or iterable of strings, scope(s) of the credentials being
          requested.
        private_key_password: string, password for private_key, unused if
          private_key is in PEM format.
        user_agent: string, HTTP User-Agent to provide for this application.
        token_uri: string, URI for token endpoint. For convenience
          defaults to Google's endpoints but any OAuth 2.0 provider can be used.
        revoke_uri: string, URI for revoke endpoint.
        kwargs: kwargs, Additional parameters to add to the JWT token, for
          example prn=joe@xample.org."""

      super(SignedJwtAssertionCredentials, self).__init__(
          None,
          user_agent=user_agent,
          token_uri=token_uri,
          revoke_uri=revoke_uri,
          )

      self.scope = util.scopes_to_string(scope)

      # Keep base64 encoded so it can be stored in JSON.
      self.private_key = base64.b64encode(private_key)

      self.private_key_password = private_key_password
      self.service_account_name = service_account_name
      self.kwargs = kwargs

    @classmethod
    def from_json(cls, s):
      data = simplejson.loads(s)
      retval = SignedJwtAssertionCredentials(
          data['service_account_name'],
          base64.b64decode(data['private_key']),
          data['scope'],
          private_key_password=data['private_key_password'],
          user_agent=data['user_agent'],
          token_uri=data['token_uri'],
          **data['kwargs']
          )
      retval.invalid = data['invalid']
      retval.access_token = data['access_token']
      return retval

    def _generate_assertion(self):
      """Generate the assertion that will be used in the request."""
      now = long(time.time())
      payload = {
          'aud': self.token_uri,
          'scope': self.scope,
          'iat': now,
          'exp': now + SignedJwtAssertionCredentials.MAX_TOKEN_LIFETIME_SECS,
          'iss': self.service_account_name
      }
      payload.update(self.kwargs)
      logger.debug(str(payload))

      private_key = base64.b64decode(self.private_key)
      return crypt.make_signed_jwt(crypt.Signer.from_string(
          private_key, self.private_key_password), payload)

  # Only used in verify_id_token(), which is always calling to the same URI
  # for the certs.
  _cached_http = httplib2.Http(MemoryCache())

  @util.positional(2)
  def verify_id_token(id_token, audience, http=None,
      cert_uri=ID_TOKEN_VERIFICATON_CERTS):
    """Verifies a signed JWT id_token.

    This function requires PyOpenSSL and because of that it does not work on
    App Engine.

    Args:
      id_token: string, A Signed JWT.
      audience: string, The audience 'aud' that the token should be for.
      http: httplib2.Http, instance to use to make the HTTP request. Callers
        should supply an instance that has caching enabled.
      cert_uri: string, URI of the certificates in JSON format to
        verify the JWT against.

    Returns:
      The deserialized JSON in the JWT.

    Raises:
      oauth2client.crypt.AppIdentityError if the JWT fails to verify.
    """
    if http is None:
      http = _cached_http

    resp, content = http.request(cert_uri)

    if resp.status == 200:
      certs = simplejson.loads(content)
      return crypt.verify_signed_jwt_with_certs(id_token, certs, audience)
    else:
      raise VerifyJwtTokenError('Status code: %d' % resp.status)


def _urlsafe_b64decode(b64string):
  # Guard against unicode strings, which base64 can't handle.
  b64string = b64string.encode('ascii')
  padded = b64string + '=' * (4 - len(b64string) % 4)
  return base64.urlsafe_b64decode(padded)


def _extract_id_token(id_token):
  """Extract the JSON payload from a JWT.

  Does the extraction w/o checking the signature.

  Args:
    id_token: string, OAuth 2.0 id_token.

  Returns:
    object, The deserialized JSON payload.
  """
  segments = id_token.split('.')

  if (len(segments) != 3):
    raise VerifyJwtTokenError(
      'Wrong number of segments in token: %s' % id_token)

  return simplejson.loads(_urlsafe_b64decode(segments[1]))


def _parse_exchange_token_response(content):
  """Parses response of an exchange token request.

  Most providers return JSON but some (e.g. Facebook) return a
  url-encoded string.

  Args:
    content: The body of a response

  Returns:
    Content as a dictionary object. Note that the dict could be empty,
    i.e. {}. That basically indicates a failure.
  """
  resp = {}
  try:
    resp = simplejson.loads(content)
  except StandardError:
    # different JSON libs raise different exceptions,
    # so we just do a catch-all here
    resp = dict(parse_qsl(content))

  # some providers respond with 'expires', others with 'expires_in'
  if resp and 'expires' in resp:
    resp['expires_in'] = resp.pop('expires')

  return resp


@util.positional(4)
def credentials_from_code(client_id, client_secret, scope, code,
                          redirect_uri='postmessage', http=None,
                          user_agent=None, token_uri=GOOGLE_TOKEN_URI,
                          auth_uri=GOOGLE_AUTH_URI,
                          revoke_uri=GOOGLE_REVOKE_URI):
  """Exchanges an authorization code for an OAuth2Credentials object.

  Args:
    client_id: string, client identifier.
    client_secret: string, client secret.
    scope: string or iterable of strings, scope(s) to request.
    code: string, An authroization code, most likely passed down from
      the client
    redirect_uri: string, this is generally set to 'postmessage' to match the
      redirect_uri that the client specified
    http: httplib2.Http, optional http instance to use to do the fetch
    token_uri: string, URI for token endpoint. For convenience
      defaults to Google's endpoints but any OAuth 2.0 provider can be used.
    auth_uri: string, URI for authorization endpoint. For convenience
      defaults to Google's endpoints but any OAuth 2.0 provider can be used.
    revoke_uri: string, URI for revoke endpoint. For convenience
      defaults to Google's endpoints but any OAuth 2.0 provider can be used.

  Returns:
    An OAuth2Credentials object.

  Raises:
    FlowExchangeError if the authorization code cannot be exchanged for an
     access token
  """
  flow = OAuth2WebServerFlow(client_id, client_secret, scope,
                             redirect_uri=redirect_uri, user_agent=user_agent,
                             auth_uri=auth_uri, token_uri=token_uri,
                             revoke_uri=revoke_uri)

  credentials = flow.step2_exchange(code, http=http)
  return credentials


@util.positional(3)
def credentials_from_clientsecrets_and_code(filename, scope, code,
                                            message = None,
                                            redirect_uri='postmessage',
                                            http=None,
                                            cache=None):
  """Returns OAuth2Credentials from a clientsecrets file and an auth code.

  Will create the right kind of Flow based on the contents of the clientsecrets
  file or will raise InvalidClientSecretsError for unknown types of Flows.

  Args:
    filename: string, File name of clientsecrets.
    scope: string or iterable of strings, scope(s) to request.
    code: string, An authorization code, most likely passed down from
      the client
    message: string, A friendly string to display to the user if the
      clientsecrets file is missing or invalid. If message is provided then
      sys.exit will be called in the case of an error. If message in not
      provided then clientsecrets.InvalidClientSecretsError will be raised.
    redirect_uri: string, this is generally set to 'postmessage' to match the
      redirect_uri that the client specified
    http: httplib2.Http, optional http instance to use to do the fetch
    cache: An optional cache service client that implements get() and set()
      methods. See clientsecrets.loadfile() for details.

  Returns:
    An OAuth2Credentials object.

  Raises:
    FlowExchangeError if the authorization code cannot be exchanged for an
     access token
    UnknownClientSecretsFlowError if the file describes an unknown kind of Flow.
    clientsecrets.InvalidClientSecretsError if the clientsecrets file is
      invalid.
  """
  flow = flow_from_clientsecrets(filename, scope, message=message, cache=cache,
                                 redirect_uri=redirect_uri)
  credentials = flow.step2_exchange(code, http=http)
  return credentials


class OAuth2WebServerFlow(Flow):
  """Does the Web Server Flow for OAuth 2.0.

  OAuth2WebServerFlow objects may be safely pickled and unpickled.
  """

  @util.positional(4)
  def __init__(self, client_id, client_secret, scope,
               redirect_uri=None,
               user_agent=None,
               auth_uri=GOOGLE_AUTH_URI,
               token_uri=GOOGLE_TOKEN_URI,
               revoke_uri=GOOGLE_REVOKE_URI,
               **kwargs):
    """Constructor for OAuth2WebServerFlow.

    The kwargs argument is used to set extra query parameters on the
    auth_uri. For example, the access_type and approval_prompt
    query parameters can be set via kwargs.

    Args:
      client_id: string, client identifier.
      client_secret: string client secret.
      scope: string or iterable of strings, scope(s) of the credentials being
        requested.
      redirect_uri: string, Either the string 'urn:ietf:wg:oauth:2.0:oob' for
        a non-web-based application, or a URI that handles the callback from
        the authorization server.
      user_agent: string, HTTP User-Agent to provide for this application.
      auth_uri: string, URI for authorization endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      token_uri: string, URI for token endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      revoke_uri: string, URI for revoke endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      **kwargs: dict, The keyword arguments are all optional and required
                        parameters for the OAuth calls.
    """
    self.client_id = client_id
    self.client_secret = client_secret
    self.scope = util.scopes_to_string(scope)
    self.redirect_uri = redirect_uri
    self.user_agent = user_agent
    self.auth_uri = auth_uri
    self.token_uri = token_uri
    self.revoke_uri = revoke_uri
    self.params = {
        'access_type': 'offline',
        'response_type': 'code',
    }
    self.params.update(kwargs)

  @util.positional(1)
  def step1_get_authorize_url(self, redirect_uri=None):
    """Returns a URI to redirect to the provider.

    Args:
      redirect_uri: string, Either the string 'urn:ietf:wg:oauth:2.0:oob' for
        a non-web-based application, or a URI that handles the callback from
        the authorization server. This parameter is deprecated, please move to
        passing the redirect_uri in via the constructor.

    Returns:
      A URI as a string to redirect the user to begin the authorization flow.
    """
    if redirect_uri is not None:
      logger.warning(('The redirect_uri parameter for'
          'OAuth2WebServerFlow.step1_get_authorize_url is deprecated. Please'
          'move to passing the redirect_uri in via the constructor.'))
      self.redirect_uri = redirect_uri

    if self.redirect_uri is None:
      raise ValueError('The value of redirect_uri must not be None.')

    query_params = {
        'client_id': self.client_id,
        'redirect_uri': self.redirect_uri,
        'scope': self.scope,
    }
    query_params.update(self.params)
    return _update_query_params(self.auth_uri, query_params)

  @util.positional(2)
  def step2_exchange(self, code, http=None):
    """Exhanges a code for OAuth2Credentials.

    Args:
      code: string or dict, either the code as a string, or a dictionary
        of the query parameters to the redirect_uri, which contains
        the code.
      http: httplib2.Http, optional http instance to use to do the fetch

    Returns:
      An OAuth2Credentials object that can be used to authorize requests.

    Raises:
      FlowExchangeError if a problem occured exchanging the code for a
      refresh_token.
    """

    if not (isinstance(code, str) or isinstance(code, unicode)):
      if 'code' not in code:
        if 'error' in code:
          error_msg = code['error']
        else:
          error_msg = 'No code was supplied in the query parameters.'
        raise FlowExchangeError(error_msg)
      else:
        code = code['code']

    body = urllib.urlencode({
        'grant_type': 'authorization_code',
        'client_id': self.client_id,
        'client_secret': self.client_secret,
        'code': code,
        'redirect_uri': self.redirect_uri,
        'scope': self.scope,
        })
    headers = {
        'content-type': 'application/x-www-form-urlencoded',
    }

    if self.user_agent is not None:
      headers['user-agent'] = self.user_agent

    if http is None:
      http = httplib2.Http()

    resp, content = http.request(self.token_uri, method='POST', body=body,
                                 headers=headers)
    d = _parse_exchange_token_response(content)
    if resp.status == 200 and 'access_token' in d:
      access_token = d['access_token']
      refresh_token = d.get('refresh_token', None)
      token_expiry = None
      if 'expires_in' in d:
        token_expiry = datetime.datetime.utcnow() + datetime.timedelta(
            seconds=int(d['expires_in']))

      if 'id_token' in d:
        d['id_token'] = _extract_id_token(d['id_token'])

      logger.info('Successfully retrieved access token')
      return OAuth2Credentials(access_token, self.client_id,
                               self.client_secret, refresh_token, token_expiry,
                               self.token_uri, self.user_agent,
                               revoke_uri=self.revoke_uri,
                               id_token=d.get('id_token', None),
                               token_response=d)
    else:
      logger.info('Failed to retrieve access token: %s' % content)
      if 'error' in d:
        # you never know what those providers got to say
        error_msg = unicode(d['error'])
      else:
        error_msg = 'Invalid response: %s.' % str(resp.status)
      raise FlowExchangeError(error_msg)


@util.positional(2)
def flow_from_clientsecrets(filename, scope, redirect_uri=None,
                            message=None, cache=None):
  """Create a Flow from a clientsecrets file.

  Will create the right kind of Flow based on the contents of the clientsecrets
  file or will raise InvalidClientSecretsError for unknown types of Flows.

  Args:
    filename: string, File name of client secrets.
    scope: string or iterable of strings, scope(s) to request.
    redirect_uri: string, Either the string 'urn:ietf:wg:oauth:2.0:oob' for
      a non-web-based application, or a URI that handles the callback from
      the authorization server.
    message: string, A friendly string to display to the user if the
      clientsecrets file is missing or invalid. If message is provided then
      sys.exit will be called in the case of an error. If message in not
      provided then clientsecrets.InvalidClientSecretsError will be raised.
    cache: An optional cache service client that implements get() and set()
      methods. See clientsecrets.loadfile() for details.

  Returns:
    A Flow object.

  Raises:
    UnknownClientSecretsFlowError if the file describes an unknown kind of Flow.
    clientsecrets.InvalidClientSecretsError if the clientsecrets file is
      invalid.
  """
  try:
    client_type, client_info = clientsecrets.loadfile(filename, cache=cache)
    if client_type in (clientsecrets.TYPE_WEB, clientsecrets.TYPE_INSTALLED):
      constructor_kwargs = {
          'redirect_uri': redirect_uri,
          'auth_uri': client_info['auth_uri'],
          'token_uri': client_info['token_uri'],
      }
      revoke_uri = client_info.get('revoke_uri')
      if revoke_uri is not None:
        constructor_kwargs['revoke_uri'] = revoke_uri
      return OAuth2WebServerFlow(
          client_info['client_id'], client_info['client_secret'],
          scope, **constructor_kwargs)

  except clientsecrets.InvalidClientSecretsError:
    if message:
      sys.exit(message)
    else:
      raise
  else:
    raise UnknownClientSecretsFlowError(
        'This OAuth 2.0 flow is unsupported: %r' % client_type)

########NEW FILE########
__FILENAME__ = clientsecrets
# Copyright (C) 2011 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utilities for reading OAuth 2.0 client secret files.

A client_secrets.json file contains all the information needed to interact with
an OAuth 2.0 protected service.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'


from anyjson import simplejson

# Properties that make a client_secrets.json file valid.
TYPE_WEB = 'web'
TYPE_INSTALLED = 'installed'

VALID_CLIENT = {
    TYPE_WEB: {
        'required': [
            'client_id',
            'client_secret',
            'redirect_uris',
            'auth_uri',
            'token_uri',
        ],
        'string': [
            'client_id',
            'client_secret',
        ],
    },
    TYPE_INSTALLED: {
        'required': [
            'client_id',
            'client_secret',
            'redirect_uris',
            'auth_uri',
            'token_uri',
        ],
        'string': [
            'client_id',
            'client_secret',
        ],
    },
}


class Error(Exception):
  """Base error for this module."""
  pass


class InvalidClientSecretsError(Error):
  """Format of ClientSecrets file is invalid."""
  pass


def _validate_clientsecrets(obj):
  if obj is None or len(obj) != 1:
    raise InvalidClientSecretsError('Invalid file format.')
  client_type = obj.keys()[0]
  if client_type not in VALID_CLIENT.keys():
    raise InvalidClientSecretsError('Unknown client type: %s.' % client_type)
  client_info = obj[client_type]
  for prop_name in VALID_CLIENT[client_type]['required']:
    if prop_name not in client_info:
      raise InvalidClientSecretsError(
        'Missing property "%s" in a client type of "%s".' % (prop_name,
                                                           client_type))
  for prop_name in VALID_CLIENT[client_type]['string']:
    if client_info[prop_name].startswith('[['):
      raise InvalidClientSecretsError(
        'Property "%s" is not configured.' % prop_name)
  return client_type, client_info


def load(fp):
  obj = simplejson.load(fp)
  return _validate_clientsecrets(obj)


def loads(s):
  obj = simplejson.loads(s)
  return _validate_clientsecrets(obj)


def _loadfile(filename):
  try:
    fp = file(filename, 'r')
    try:
      obj = simplejson.load(fp)
    finally:
      fp.close()
  except IOError:
    raise InvalidClientSecretsError('File not found: "%s"' % filename)
  return _validate_clientsecrets(obj)


def loadfile(filename, cache=None):
  """Loading of client_secrets JSON file, optionally backed by a cache.

  Typical cache storage would be App Engine memcache service,
  but you can pass in any other cache client that implements
  these methods:
    - get(key, namespace=ns)
    - set(key, value, namespace=ns)

  Usage:
    # without caching
    client_type, client_info = loadfile('secrets.json')
    # using App Engine memcache service
    from google.appengine.api import memcache
    client_type, client_info = loadfile('secrets.json', cache=memcache)

  Args:
    filename: string, Path to a client_secrets.json file on a filesystem.
    cache: An optional cache service client that implements get() and set()
      methods. If not specified, the file is always being loaded from
      a filesystem.

  Raises:
    InvalidClientSecretsError: In case of a validation error or some
      I/O failure. Can happen only on cache miss.

  Returns:
    (client_type, client_info) tuple, as _loadfile() normally would.
    JSON contents is validated only during first load. Cache hits are not
    validated.
  """
  _SECRET_NAMESPACE = 'oauth2client:secrets#ns'

  if not cache:
    return _loadfile(filename)

  obj = cache.get(filename, namespace=_SECRET_NAMESPACE)
  if obj is None:
    client_type, client_info = _loadfile(filename)
    obj = {client_type: client_info}
    cache.set(filename, obj, namespace=_SECRET_NAMESPACE)

  return obj.iteritems().next()

########NEW FILE########
__FILENAME__ = crypt
#!/usr/bin/python2.4
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import hashlib
import logging
import time

from anyjson import simplejson


CLOCK_SKEW_SECS = 300  # 5 minutes in seconds
AUTH_TOKEN_LIFETIME_SECS = 300  # 5 minutes in seconds
MAX_TOKEN_LIFETIME_SECS = 86400  # 1 day in seconds


logger = logging.getLogger(__name__)


class AppIdentityError(Exception):
  pass


try:
  from OpenSSL import crypto


  class OpenSSLVerifier(object):
    """Verifies the signature on a message."""

    def __init__(self, pubkey):
      """Constructor.

      Args:
        pubkey, OpenSSL.crypto.PKey, The public key to verify with.
      """
      self._pubkey = pubkey

    def verify(self, message, signature):
      """Verifies a message against a signature.

      Args:
        message: string, The message to verify.
        signature: string, The signature on the message.

      Returns:
        True if message was signed by the private key associated with the public
        key that this object was constructed with.
      """
      try:
        crypto.verify(self._pubkey, signature, message, 'sha256')
        return True
      except:
        return False

    @staticmethod
    def from_string(key_pem, is_x509_cert):
      """Construct a Verified instance from a string.

      Args:
        key_pem: string, public key in PEM format.
        is_x509_cert: bool, True if key_pem is an X509 cert, otherwise it is
          expected to be an RSA key in PEM format.

      Returns:
        Verifier instance.

      Raises:
        OpenSSL.crypto.Error if the key_pem can't be parsed.
      """
      if is_x509_cert:
        pubkey = crypto.load_certificate(crypto.FILETYPE_PEM, key_pem)
      else:
        pubkey = crypto.load_privatekey(crypto.FILETYPE_PEM, key_pem)
      return OpenSSLVerifier(pubkey)


  class OpenSSLSigner(object):
    """Signs messages with a private key."""

    def __init__(self, pkey):
      """Constructor.

      Args:
        pkey, OpenSSL.crypto.PKey (or equiv), The private key to sign with.
      """
      self._key = pkey

    def sign(self, message):
      """Signs a message.

      Args:
        message: string, Message to be signed.

      Returns:
        string, The signature of the message for the given key.
      """
      return crypto.sign(self._key, message, 'sha256')

    @staticmethod
    def from_string(key, password='notasecret'):
      """Construct a Signer instance from a string.

      Args:
        key: string, private key in PKCS12 or PEM format.
        password: string, password for the private key file.

      Returns:
        Signer instance.

      Raises:
        OpenSSL.crypto.Error if the key can't be parsed.
      """
      if key.startswith('-----BEGIN '):
        pkey = crypto.load_privatekey(crypto.FILETYPE_PEM, key)
      else:
        pkey = crypto.load_pkcs12(key, password).get_privatekey()
      return OpenSSLSigner(pkey)

except ImportError:
  OpenSSLVerifier = None
  OpenSSLSigner = None


try:
  from Crypto.PublicKey import RSA
  from Crypto.Hash import SHA256
  from Crypto.Signature import PKCS1_v1_5


  class PyCryptoVerifier(object):
    """Verifies the signature on a message."""

    def __init__(self, pubkey):
      """Constructor.

      Args:
        pubkey, OpenSSL.crypto.PKey (or equiv), The public key to verify with.
      """
      self._pubkey = pubkey

    def verify(self, message, signature):
      """Verifies a message against a signature.

      Args:
        message: string, The message to verify.
        signature: string, The signature on the message.

      Returns:
        True if message was signed by the private key associated with the public
        key that this object was constructed with.
      """
      try:
        return PKCS1_v1_5.new(self._pubkey).verify(
            SHA256.new(message), signature)
      except:
        return False

    @staticmethod
    def from_string(key_pem, is_x509_cert):
      """Construct a Verified instance from a string.

      Args:
        key_pem: string, public key in PEM format.
        is_x509_cert: bool, True if key_pem is an X509 cert, otherwise it is
          expected to be an RSA key in PEM format.

      Returns:
        Verifier instance.

      Raises:
        NotImplementedError if is_x509_cert is true.
      """
      if is_x509_cert:
        raise NotImplementedError(
            'X509 certs are not supported by the PyCrypto library. '
            'Try using PyOpenSSL if native code is an option.')
      else:
        pubkey = RSA.importKey(key_pem)
      return PyCryptoVerifier(pubkey)


  class PyCryptoSigner(object):
    """Signs messages with a private key."""

    def __init__(self, pkey):
      """Constructor.

      Args:
        pkey, OpenSSL.crypto.PKey (or equiv), The private key to sign with.
      """
      self._key = pkey

    def sign(self, message):
      """Signs a message.

      Args:
        message: string, Message to be signed.

      Returns:
        string, The signature of the message for the given key.
      """
      return PKCS1_v1_5.new(self._key).sign(SHA256.new(message))

    @staticmethod
    def from_string(key, password='notasecret'):
      """Construct a Signer instance from a string.

      Args:
        key: string, private key in PEM format.
        password: string, password for private key file. Unused for PEM files.

      Returns:
        Signer instance.

      Raises:
        NotImplementedError if they key isn't in PEM format.
      """
      if key.startswith('-----BEGIN '):
        pkey = RSA.importKey(key)
      else:
        raise NotImplementedError(
            'PKCS12 format is not supported by the PyCrpto library. '
            'Try converting to a "PEM" '
            '(openssl pkcs12 -in xxxxx.p12 -nodes -nocerts > privatekey.pem) '
            'or using PyOpenSSL if native code is an option.')
      return PyCryptoSigner(pkey)

except ImportError:
  PyCryptoVerifier = None
  PyCryptoSigner = None


if OpenSSLSigner:
  Signer = OpenSSLSigner
  Verifier = OpenSSLVerifier
elif PyCryptoSigner:
  Signer = PyCryptoSigner
  Verifier = PyCryptoVerifier
else:
  raise ImportError('No encryption library found. Please install either '
                    'PyOpenSSL, or PyCrypto 2.6 or later')


def _urlsafe_b64encode(raw_bytes):
  return base64.urlsafe_b64encode(raw_bytes).rstrip('=')


def _urlsafe_b64decode(b64string):
  # Guard against unicode strings, which base64 can't handle.
  b64string = b64string.encode('ascii')
  padded = b64string + '=' * (4 - len(b64string) % 4)
  return base64.urlsafe_b64decode(padded)


def _json_encode(data):
  return simplejson.dumps(data, separators = (',', ':'))


def make_signed_jwt(signer, payload):
  """Make a signed JWT.

  See http://self-issued.info/docs/draft-jones-json-web-token.html.

  Args:
    signer: crypt.Signer, Cryptographic signer.
    payload: dict, Dictionary of data to convert to JSON and then sign.

  Returns:
    string, The JWT for the payload.
  """
  header = {'typ': 'JWT', 'alg': 'RS256'}

  segments = [
          _urlsafe_b64encode(_json_encode(header)),
          _urlsafe_b64encode(_json_encode(payload)),
  ]
  signing_input = '.'.join(segments)

  signature = signer.sign(signing_input)
  segments.append(_urlsafe_b64encode(signature))

  logger.debug(str(segments))

  return '.'.join(segments)


def verify_signed_jwt_with_certs(jwt, certs, audience):
  """Verify a JWT against public certs.

  See http://self-issued.info/docs/draft-jones-json-web-token.html.

  Args:
    jwt: string, A JWT.
    certs: dict, Dictionary where values of public keys in PEM format.
    audience: string, The audience, 'aud', that this JWT should contain. If
      None then the JWT's 'aud' parameter is not verified.

  Returns:
    dict, The deserialized JSON payload in the JWT.

  Raises:
    AppIdentityError if any checks are failed.
  """
  segments = jwt.split('.')

  if (len(segments) != 3):
    raise AppIdentityError(
      'Wrong number of segments in token: %s' % jwt)
  signed = '%s.%s' % (segments[0], segments[1])

  signature = _urlsafe_b64decode(segments[2])

  # Parse token.
  json_body = _urlsafe_b64decode(segments[1])
  try:
    parsed = simplejson.loads(json_body)
  except:
    raise AppIdentityError('Can\'t parse token: %s' % json_body)

  # Check signature.
  verified = False
  for (keyname, pem) in certs.items():
    verifier = Verifier.from_string(pem, True)
    if (verifier.verify(signed, signature)):
      verified = True
      break
  if not verified:
    raise AppIdentityError('Invalid token signature: %s' % jwt)

  # Check creation timestamp.
  iat = parsed.get('iat')
  if iat is None:
    raise AppIdentityError('No iat field in token: %s' % json_body)
  earliest = iat - CLOCK_SKEW_SECS

  # Check expiration timestamp.
  now = long(time.time())
  exp = parsed.get('exp')
  if exp is None:
    raise AppIdentityError('No exp field in token: %s' % json_body)
  if exp >= now + MAX_TOKEN_LIFETIME_SECS:
    raise AppIdentityError(
      'exp field too far in future: %s' % json_body)
  latest = exp + CLOCK_SKEW_SECS

  if now < earliest:
    raise AppIdentityError('Token used too early, %d < %d: %s' %
      (now, earliest, json_body))
  if now > latest:
    raise AppIdentityError('Token used too late, %d > %d: %s' %
      (now, latest, json_body))

  # Check audience.
  if audience is not None:
    aud = parsed.get('aud')
    if aud is None:
      raise AppIdentityError('No aud field in token: %s' % json_body)
    if aud != audience:
      raise AppIdentityError('Wrong recipient, %s != %s: %s' %
          (aud, audience, json_body))

  return parsed

########NEW FILE########
__FILENAME__ = django_orm
# Copyright (C) 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""OAuth 2.0 utilities for Django.

Utilities for using OAuth 2.0 in conjunction with
the Django datastore.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import oauth2client
import base64
import pickle

from django.db import models
from oauth2client.client import Storage as BaseStorage

class CredentialsField(models.Field):

  __metaclass__ = models.SubfieldBase

  def __init__(self, *args, **kwargs):
    if 'null' not in kwargs:
      kwargs['null'] = True
    super(CredentialsField, self).__init__(*args, **kwargs)

  def get_internal_type(self):
    return "TextField"

  def to_python(self, value):
    if value is None:
      return None
    if isinstance(value, oauth2client.client.Credentials):
      return value
    return pickle.loads(base64.b64decode(value))

  def get_db_prep_value(self, value, connection, prepared=False):
    if value is None:
      return None
    return base64.b64encode(pickle.dumps(value))


class FlowField(models.Field):

  __metaclass__ = models.SubfieldBase

  def __init__(self, *args, **kwargs):
    if 'null' not in kwargs:
      kwargs['null'] = True
    super(FlowField, self).__init__(*args, **kwargs)

  def get_internal_type(self):
    return "TextField"

  def to_python(self, value):
    if value is None:
      return None
    if isinstance(value, oauth2client.client.Flow):
      return value
    return pickle.loads(base64.b64decode(value))

  def get_db_prep_value(self, value, connection, prepared=False):
    if value is None:
      return None
    return base64.b64encode(pickle.dumps(value))


class Storage(BaseStorage):
  """Store and retrieve a single credential to and from
  the datastore.

  This Storage helper presumes the Credentials
  have been stored as a CredenialsField
  on a db model class.
  """

  def __init__(self, model_class, key_name, key_value, property_name):
    """Constructor for Storage.

    Args:
      model: db.Model, model class
      key_name: string, key name for the entity that has the credentials
      key_value: string, key value for the entity that has the credentials
      property_name: string, name of the property that is an CredentialsProperty
    """
    self.model_class = model_class
    self.key_name = key_name
    self.key_value = key_value
    self.property_name = property_name

  def locked_get(self):
    """Retrieve Credential from datastore.

    Returns:
      oauth2client.Credentials
    """
    credential = None

    query = {self.key_name: self.key_value}
    entities = self.model_class.objects.filter(**query)
    if len(entities) > 0:
      credential = getattr(entities[0], self.property_name)
      if credential and hasattr(credential, 'set_store'):
        credential.set_store(self)
    return credential

  def locked_put(self, credentials):
    """Write a Credentials to the datastore.

    Args:
      credentials: Credentials, the credentials to store.
    """
    args = {self.key_name: self.key_value}
    entity = self.model_class(**args)
    setattr(entity, self.property_name, credentials)
    entity.save()

  def locked_delete(self):
    """Delete Credentials from the datastore."""

    query = {self.key_name: self.key_value}
    entities = self.model_class.objects.filter(**query).delete()

########NEW FILE########
__FILENAME__ = file
# Copyright (C) 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utilities for OAuth.

Utilities for making it easier to work with OAuth 2.0
credentials.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import os
import stat
import threading

from anyjson import simplejson
from client import Storage as BaseStorage
from client import Credentials


class CredentialsFileSymbolicLinkError(Exception):
  """Credentials files must not be symbolic links."""


class Storage(BaseStorage):
  """Store and retrieve a single credential to and from a file."""

  def __init__(self, filename):
    self._filename = filename
    self._lock = threading.Lock()

  def _validate_file(self):
    if os.path.islink(self._filename):
      raise CredentialsFileSymbolicLinkError(
          'File: %s is a symbolic link.' % self._filename)

  def acquire_lock(self):
    """Acquires any lock necessary to access this Storage.

    This lock is not reentrant."""
    self._lock.acquire()

  def release_lock(self):
    """Release the Storage lock.

    Trying to release a lock that isn't held will result in a
    RuntimeError.
    """
    self._lock.release()

  def locked_get(self):
    """Retrieve Credential from file.

    Returns:
      oauth2client.client.Credentials

    Raises:
      CredentialsFileSymbolicLinkError if the file is a symbolic link.
    """
    credentials = None
    self._validate_file()
    try:
      f = open(self._filename, 'rb')
      content = f.read()
      f.close()
    except IOError:
      return credentials

    try:
      credentials = Credentials.new_from_json(content)
      credentials.set_store(self)
    except ValueError:
      pass

    return credentials

  def _create_file_if_needed(self):
    """Create an empty file if necessary.

    This method will not initialize the file. Instead it implements a
    simple version of "touch" to ensure the file has been created.
    """
    if not os.path.exists(self._filename):
      old_umask = os.umask(0177)
      try:
        open(self._filename, 'a+b').close()
      finally:
        os.umask(old_umask)

  def locked_put(self, credentials):
    """Write Credentials to file.

    Args:
      credentials: Credentials, the credentials to store.

    Raises:
      CredentialsFileSymbolicLinkError if the file is a symbolic link.
    """

    self._create_file_if_needed()
    self._validate_file()
    f = open(self._filename, 'wb')
    f.write(credentials.to_json())
    f.close()

  def locked_delete(self):
    """Delete Credentials file.

    Args:
      credentials: Credentials, the credentials to store.
    """

    os.unlink(self._filename)

########NEW FILE########
__FILENAME__ = gce
# Copyright (C) 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utilities for Google Compute Engine

Utilities for making it easier to use OAuth 2.0 on Google Compute Engine.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import httplib2
import logging
import uritemplate

from oauth2client import util
from oauth2client.anyjson import simplejson
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import AssertionCredentials

logger = logging.getLogger(__name__)

# URI Template for the endpoint that returns access_tokens.
META = ('http://metadata.google.internal/0.1/meta-data/service-accounts/'
        'default/acquire{?scope}')


class AppAssertionCredentials(AssertionCredentials):
  """Credentials object for Compute Engine Assertion Grants

  This object will allow a Compute Engine instance to identify itself to
  Google and other OAuth 2.0 servers that can verify assertions. It can be used
  for the purpose of accessing data stored under an account assigned to the
  Compute Engine instance itself.

  This credential does not require a flow to instantiate because it represents
  a two legged flow, and therefore has all of the required information to
  generate and refresh its own access tokens.
  """

  @util.positional(2)
  def __init__(self, scope, **kwargs):
    """Constructor for AppAssertionCredentials

    Args:
      scope: string or iterable of strings, scope(s) of the credentials being
        requested.
    """
    self.scope = util.scopes_to_string(scope)

    # Assertion type is no longer used, but still in the parent class signature.
    super(AppAssertionCredentials, self).__init__(None)

  @classmethod
  def from_json(cls, json):
    data = simplejson.loads(json)
    return AppAssertionCredentials(data['scope'])

  def _refresh(self, http_request):
    """Refreshes the access_token.

    Skip all the storage hoops and just refresh using the API.

    Args:
      http_request: callable, a callable that matches the method signature of
        httplib2.Http.request, used to make the refresh request.

    Raises:
      AccessTokenRefreshError: When the refresh fails.
    """
    uri = uritemplate.expand(META, {'scope': self.scope})
    response, content = http_request(uri)
    if response.status == 200:
      try:
        d = simplejson.loads(content)
      except StandardError, e:
        raise AccessTokenRefreshError(str(e))
      self.access_token = d['accessToken']
    else:
      raise AccessTokenRefreshError(content)

########NEW FILE########
__FILENAME__ = keyring_storage
# Copyright (C) 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A keyring based Storage.

A Storage for Credentials that uses the keyring module.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'

import keyring
import threading

from client import Storage as BaseStorage
from client import Credentials


class Storage(BaseStorage):
  """Store and retrieve a single credential to and from the keyring.

  To use this module you must have the keyring module installed. See
  <http://pypi.python.org/pypi/keyring/>. This is an optional module and is not
  installed with oauth2client by default because it does not work on all the
  platforms that oauth2client supports, such as Google App Engine.

  The keyring module <http://pypi.python.org/pypi/keyring/> is a cross-platform
  library for access the keyring capabilities of the local system. The user will
  be prompted for their keyring password when this module is used, and the
  manner in which the user is prompted will vary per platform.

  Usage:
    from oauth2client.keyring_storage import Storage

    s = Storage('name_of_application', 'user1')
    credentials = s.get()

  """

  def __init__(self, service_name, user_name):
    """Constructor.

    Args:
      service_name: string, The name of the service under which the credentials
        are stored.
      user_name: string, The name of the user to store credentials for.
    """
    self._service_name = service_name
    self._user_name = user_name
    self._lock = threading.Lock()

  def acquire_lock(self):
    """Acquires any lock necessary to access this Storage.

    This lock is not reentrant."""
    self._lock.acquire()

  def release_lock(self):
    """Release the Storage lock.

    Trying to release a lock that isn't held will result in a
    RuntimeError.
    """
    self._lock.release()

  def locked_get(self):
    """Retrieve Credential from file.

    Returns:
      oauth2client.client.Credentials
    """
    credentials = None
    content = keyring.get_password(self._service_name, self._user_name)

    if content is not None:
      try:
        credentials = Credentials.new_from_json(content)
        credentials.set_store(self)
      except ValueError:
        pass

    return credentials

  def locked_put(self, credentials):
    """Write Credentials to file.

    Args:
      credentials: Credentials, the credentials to store.
    """
    keyring.set_password(self._service_name, self._user_name,
                         credentials.to_json())

  def locked_delete(self):
    """Delete Credentials file.

    Args:
      credentials: Credentials, the credentials to store.
    """
    keyring.set_password(self._service_name, self._user_name, '')

########NEW FILE########
__FILENAME__ = locked_file
# Copyright 2011 Google Inc. All Rights Reserved.

"""Locked file interface that should work on Unix and Windows pythons.

This module first tries to use fcntl locking to ensure serialized access
to a file, then falls back on a lock file if that is unavialable.

Usage:
    f = LockedFile('filename', 'r+b', 'rb')
    f.open_and_lock()
    if f.is_locked():
      print 'Acquired filename with r+b mode'
      f.file_handle().write('locked data')
    else:
      print 'Aquired filename with rb mode'
    f.unlock_and_close()
"""

__author__ = 'cache@google.com (David T McWherter)'

import errno
import logging
import os
import time

from oauth2client import util

logger = logging.getLogger(__name__)


class CredentialsFileSymbolicLinkError(Exception):
  """Credentials files must not be symbolic links."""


class AlreadyLockedException(Exception):
  """Trying to lock a file that has already been locked by the LockedFile."""
  pass


def validate_file(filename):
  if os.path.islink(filename):
    raise CredentialsFileSymbolicLinkError(
        'File: %s is a symbolic link.' % filename)

class _Opener(object):
  """Base class for different locking primitives."""

  def __init__(self, filename, mode, fallback_mode):
    """Create an Opener.

    Args:
      filename: string, The pathname of the file.
      mode: string, The preferred mode to access the file with.
      fallback_mode: string, The mode to use if locking fails.
    """
    self._locked = False
    self._filename = filename
    self._mode = mode
    self._fallback_mode = fallback_mode
    self._fh = None

  def is_locked(self):
    """Was the file locked."""
    return self._locked

  def file_handle(self):
    """The file handle to the file. Valid only after opened."""
    return self._fh

  def filename(self):
    """The filename that is being locked."""
    return self._filename

  def open_and_lock(self, timeout, delay):
    """Open the file and lock it.

    Args:
      timeout: float, How long to try to lock for.
      delay: float, How long to wait between retries.
    """
    pass

  def unlock_and_close(self):
    """Unlock and close the file."""
    pass


class _PosixOpener(_Opener):
  """Lock files using Posix advisory lock files."""

  def open_and_lock(self, timeout, delay):
    """Open the file and lock it.

    Tries to create a .lock file next to the file we're trying to open.

    Args:
      timeout: float, How long to try to lock for.
      delay: float, How long to wait between retries.

    Raises:
      AlreadyLockedException: if the lock is already acquired.
      IOError: if the open fails.
      CredentialsFileSymbolicLinkError if the file is a symbolic link.
    """
    if self._locked:
      raise AlreadyLockedException('File %s is already locked' %
                                   self._filename)
    self._locked = False

    validate_file(self._filename)
    try:
      self._fh = open(self._filename, self._mode)
    except IOError, e:
      # If we can't access with _mode, try _fallback_mode and don't lock.
      if e.errno == errno.EACCES:
        self._fh = open(self._filename, self._fallback_mode)
        return

    lock_filename = self._posix_lockfile(self._filename)
    start_time = time.time()
    while True:
      try:
        self._lock_fd = os.open(lock_filename,
                                os.O_CREAT|os.O_EXCL|os.O_RDWR)
        self._locked = True
        break

      except OSError, e:
        if e.errno != errno.EEXIST:
          raise
        if (time.time() - start_time) >= timeout:
          logger.warn('Could not acquire lock %s in %s seconds' % (
              lock_filename, timeout))
          # Close the file and open in fallback_mode.
          if self._fh:
            self._fh.close()
          self._fh = open(self._filename, self._fallback_mode)
          return
        time.sleep(delay)

  def unlock_and_close(self):
    """Unlock a file by removing the .lock file, and close the handle."""
    if self._locked:
      lock_filename = self._posix_lockfile(self._filename)
      os.close(self._lock_fd)
      os.unlink(lock_filename)
      self._locked = False
      self._lock_fd = None
    if self._fh:
      self._fh.close()

  def _posix_lockfile(self, filename):
    """The name of the lock file to use for posix locking."""
    return '%s.lock' % filename


try:
  import fcntl

  class _FcntlOpener(_Opener):
    """Open, lock, and unlock a file using fcntl.lockf."""

    def open_and_lock(self, timeout, delay):
      """Open the file and lock it.

      Args:
        timeout: float, How long to try to lock for.
        delay: float, How long to wait between retries

      Raises:
        AlreadyLockedException: if the lock is already acquired.
        IOError: if the open fails.
        CredentialsFileSymbolicLinkError if the file is a symbolic link.
      """
      if self._locked:
        raise AlreadyLockedException('File %s is already locked' %
                                     self._filename)
      start_time = time.time()

      validate_file(self._filename)
      try:
        self._fh = open(self._filename, self._mode)
      except IOError, e:
        # If we can't access with _mode, try _fallback_mode and don't lock.
        if e.errno == errno.EACCES:
          self._fh = open(self._filename, self._fallback_mode)
          return

      # We opened in _mode, try to lock the file.
      while True:
        try:
          fcntl.lockf(self._fh.fileno(), fcntl.LOCK_EX)
          self._locked = True
          return
        except IOError, e:
          # If not retrying, then just pass on the error.
          if timeout == 0:
            raise e
          if e.errno != errno.EACCES:
            raise e
          # We could not acquire the lock. Try again.
          if (time.time() - start_time) >= timeout:
            logger.warn('Could not lock %s in %s seconds' % (
                self._filename, timeout))
            if self._fh:
              self._fh.close()
            self._fh = open(self._filename, self._fallback_mode)
            return
          time.sleep(delay)

    def unlock_and_close(self):
      """Close and unlock the file using the fcntl.lockf primitive."""
      if self._locked:
        fcntl.lockf(self._fh.fileno(), fcntl.LOCK_UN)
      self._locked = False
      if self._fh:
        self._fh.close()
except ImportError:
  _FcntlOpener = None


try:
  import pywintypes
  import win32con
  import win32file

  class _Win32Opener(_Opener):
    """Open, lock, and unlock a file using windows primitives."""

    # Error #33:
    #  'The process cannot access the file because another process'
    FILE_IN_USE_ERROR = 33

    # Error #158:
    #  'The segment is already unlocked.'
    FILE_ALREADY_UNLOCKED_ERROR = 158

    def open_and_lock(self, timeout, delay):
      """Open the file and lock it.

      Args:
        timeout: float, How long to try to lock for.
        delay: float, How long to wait between retries

      Raises:
        AlreadyLockedException: if the lock is already acquired.
        IOError: if the open fails.
        CredentialsFileSymbolicLinkError if the file is a symbolic link.
      """
      if self._locked:
        raise AlreadyLockedException('File %s is already locked' %
                                     self._filename)
      start_time = time.time()

      validate_file(self._filename)
      try:
        self._fh = open(self._filename, self._mode)
      except IOError, e:
        # If we can't access with _mode, try _fallback_mode and don't lock.
        if e.errno == errno.EACCES:
          self._fh = open(self._filename, self._fallback_mode)
          return

      # We opened in _mode, try to lock the file.
      while True:
        try:
          hfile = win32file._get_osfhandle(self._fh.fileno())
          win32file.LockFileEx(
              hfile,
              (win32con.LOCKFILE_FAIL_IMMEDIATELY|
               win32con.LOCKFILE_EXCLUSIVE_LOCK), 0, -0x10000,
              pywintypes.OVERLAPPED())
          self._locked = True
          return
        except pywintypes.error, e:
          if timeout == 0:
            raise e

          # If the error is not that the file is already in use, raise.
          if e[0] != _Win32Opener.FILE_IN_USE_ERROR:
            raise

          # We could not acquire the lock. Try again.
          if (time.time() - start_time) >= timeout:
            logger.warn('Could not lock %s in %s seconds' % (
                self._filename, timeout))
            if self._fh:
              self._fh.close()
            self._fh = open(self._filename, self._fallback_mode)
            return
          time.sleep(delay)

    def unlock_and_close(self):
      """Close and unlock the file using the win32 primitive."""
      if self._locked:
        try:
          hfile = win32file._get_osfhandle(self._fh.fileno())
          win32file.UnlockFileEx(hfile, 0, -0x10000, pywintypes.OVERLAPPED())
        except pywintypes.error, e:
          if e[0] != _Win32Opener.FILE_ALREADY_UNLOCKED_ERROR:
            raise
      self._locked = False
      if self._fh:
        self._fh.close()
except ImportError:
  _Win32Opener = None


class LockedFile(object):
  """Represent a file that has exclusive access."""

  @util.positional(4)
  def __init__(self, filename, mode, fallback_mode, use_native_locking=True):
    """Construct a LockedFile.

    Args:
      filename: string, The path of the file to open.
      mode: string, The mode to try to open the file with.
      fallback_mode: string, The mode to use if locking fails.
      use_native_locking: bool, Whether or not fcntl/win32 locking is used.
    """
    opener = None
    if not opener and use_native_locking:
      if _Win32Opener:
        opener = _Win32Opener(filename, mode, fallback_mode)
      if _FcntlOpener:
        opener = _FcntlOpener(filename, mode, fallback_mode)

    if not opener:
      opener = _PosixOpener(filename, mode, fallback_mode)

    self._opener = opener

  def filename(self):
    """Return the filename we were constructed with."""
    return self._opener._filename

  def file_handle(self):
    """Return the file_handle to the opened file."""
    return self._opener.file_handle()

  def is_locked(self):
    """Return whether we successfully locked the file."""
    return self._opener.is_locked()

  def open_and_lock(self, timeout=0, delay=0.05):
    """Open the file, trying to lock it.

    Args:
      timeout: float, The number of seconds to try to acquire the lock.
      delay: float, The number of seconds to wait between retry attempts.

    Raises:
      AlreadyLockedException: if the lock is already acquired.
      IOError: if the open fails.
    """
    self._opener.open_and_lock(timeout, delay)

  def unlock_and_close(self):
    """Unlock and close a file."""
    self._opener.unlock_and_close()

########NEW FILE########
__FILENAME__ = multistore_file
# Copyright 2011 Google Inc. All Rights Reserved.

"""Multi-credential file store with lock support.

This module implements a JSON credential store where multiple
credentials can be stored in one file. That file supports locking
both in a single process and across processes.

The credential themselves are keyed off of:
* client_id
* user_agent
* scope

The format of the stored data is like so:
{
  'file_version': 1,
  'data': [
    {
      'key': {
        'clientId': '<client id>',
        'userAgent': '<user agent>',
        'scope': '<scope>'
      },
      'credential': {
        # JSON serialized Credentials.
      }
    }
  ]
}
"""

__author__ = 'jbeda@google.com (Joe Beda)'

import base64
import errno
import logging
import os
import threading

from anyjson import simplejson
from oauth2client.client import Storage as BaseStorage
from oauth2client.client import Credentials
from oauth2client import util
from locked_file import LockedFile

logger = logging.getLogger(__name__)

# A dict from 'filename'->_MultiStore instances
_multistores = {}
_multistores_lock = threading.Lock()


class Error(Exception):
  """Base error for this module."""
  pass


class NewerCredentialStoreError(Error):
  """The credential store is a newer version that supported."""
  pass


@util.positional(4)
def get_credential_storage(filename, client_id, user_agent, scope,
                           warn_on_readonly=True):
  """Get a Storage instance for a credential.

  Args:
    filename: The JSON file storing a set of credentials
    client_id: The client_id for the credential
    user_agent: The user agent for the credential
    scope: string or iterable of strings, Scope(s) being requested
    warn_on_readonly: if True, log a warning if the store is readonly

  Returns:
    An object derived from client.Storage for getting/setting the
    credential.
  """
  # Recreate the legacy key with these specific parameters
  key = {'clientId': client_id, 'userAgent': user_agent,
         'scope': util.scopes_to_string(scope)}
  return get_credential_storage_custom_key(
      filename, key, warn_on_readonly=warn_on_readonly)


@util.positional(2)
def get_credential_storage_custom_string_key(
    filename, key_string, warn_on_readonly=True):
  """Get a Storage instance for a credential using a single string as a key.

  Allows you to provide a string as a custom key that will be used for
  credential storage and retrieval.

  Args:
    filename: The JSON file storing a set of credentials
    key_string: A string to use as the key for storing this credential.
    warn_on_readonly: if True, log a warning if the store is readonly

  Returns:
    An object derived from client.Storage for getting/setting the
    credential.
  """
  # Create a key dictionary that can be used
  key_dict = {'key': key_string}
  return get_credential_storage_custom_key(
      filename, key_dict, warn_on_readonly=warn_on_readonly)


@util.positional(2)
def get_credential_storage_custom_key(
    filename, key_dict, warn_on_readonly=True):
  """Get a Storage instance for a credential using a dictionary as a key.

  Allows you to provide a dictionary as a custom key that will be used for
  credential storage and retrieval.

  Args:
    filename: The JSON file storing a set of credentials
    key_dict: A dictionary to use as the key for storing this credential. There
      is no ordering of the keys in the dictionary. Logically equivalent
      dictionaries will produce equivalent storage keys.
    warn_on_readonly: if True, log a warning if the store is readonly

  Returns:
    An object derived from client.Storage for getting/setting the
    credential.
  """
  filename = os.path.expanduser(filename)
  _multistores_lock.acquire()
  try:
    multistore = _multistores.setdefault(
        filename, _MultiStore(filename, warn_on_readonly=warn_on_readonly))
  finally:
    _multistores_lock.release()
  key = util.dict_to_tuple_key(key_dict)
  return multistore._get_storage(key)


class _MultiStore(object):
  """A file backed store for multiple credentials."""

  @util.positional(2)
  def __init__(self, filename, warn_on_readonly=True):
    """Initialize the class.

    This will create the file if necessary.
    """
    self._file = LockedFile(filename, 'r+b', 'rb')
    self._thread_lock = threading.Lock()
    self._read_only = False
    self._warn_on_readonly = warn_on_readonly

    self._create_file_if_needed()

    # Cache of deserialized store. This is only valid after the
    # _MultiStore is locked or _refresh_data_cache is called. This is
    # of the form of:
    #
    # ((key, value), (key, value)...) -> OAuth2Credential
    #
    # If this is None, then the store hasn't been read yet.
    self._data = None

  class _Storage(BaseStorage):
    """A Storage object that knows how to read/write a single credential."""

    def __init__(self, multistore, key):
      self._multistore = multistore
      self._key = key

    def acquire_lock(self):
      """Acquires any lock necessary to access this Storage.

      This lock is not reentrant.
      """
      self._multistore._lock()

    def release_lock(self):
      """Release the Storage lock.

      Trying to release a lock that isn't held will result in a
      RuntimeError.
      """
      self._multistore._unlock()

    def locked_get(self):
      """Retrieve credential.

      The Storage lock must be held when this is called.

      Returns:
        oauth2client.client.Credentials
      """
      credential = self._multistore._get_credential(self._key)
      if credential:
        credential.set_store(self)
      return credential

    def locked_put(self, credentials):
      """Write a credential.

      The Storage lock must be held when this is called.

      Args:
        credentials: Credentials, the credentials to store.
      """
      self._multistore._update_credential(self._key, credentials)

    def locked_delete(self):
      """Delete a credential.

      The Storage lock must be held when this is called.

      Args:
        credentials: Credentials, the credentials to store.
      """
      self._multistore._delete_credential(self._key)

  def _create_file_if_needed(self):
    """Create an empty file if necessary.

    This method will not initialize the file. Instead it implements a
    simple version of "touch" to ensure the file has been created.
    """
    if not os.path.exists(self._file.filename()):
      old_umask = os.umask(0177)
      try:
        open(self._file.filename(), 'a+b').close()
      finally:
        os.umask(old_umask)

  def _lock(self):
    """Lock the entire multistore."""
    self._thread_lock.acquire()
    self._file.open_and_lock()
    if not self._file.is_locked():
      self._read_only = True
      if self._warn_on_readonly:
        logger.warn('The credentials file (%s) is not writable. Opening in '
                    'read-only mode. Any refreshed credentials will only be '
                    'valid for this run.' % self._file.filename())
    if os.path.getsize(self._file.filename()) == 0:
      logger.debug('Initializing empty multistore file')
      # The multistore is empty so write out an empty file.
      self._data = {}
      self._write()
    elif not self._read_only or self._data is None:
      # Only refresh the data if we are read/write or we haven't
      # cached the data yet. If we are readonly, we assume is isn't
      # changing out from under us and that we only have to read it
      # once. This prevents us from whacking any new access keys that
      # we have cached in memory but were unable to write out.
      self._refresh_data_cache()

  def _unlock(self):
    """Release the lock on the multistore."""
    self._file.unlock_and_close()
    self._thread_lock.release()

  def _locked_json_read(self):
    """Get the raw content of the multistore file.

    The multistore must be locked when this is called.

    Returns:
      The contents of the multistore decoded as JSON.
    """
    assert self._thread_lock.locked()
    self._file.file_handle().seek(0)
    return simplejson.load(self._file.file_handle())

  def _locked_json_write(self, data):
    """Write a JSON serializable data structure to the multistore.

    The multistore must be locked when this is called.

    Args:
      data: The data to be serialized and written.
    """
    assert self._thread_lock.locked()
    if self._read_only:
      return
    self._file.file_handle().seek(0)
    simplejson.dump(data, self._file.file_handle(), sort_keys=True, indent=2)
    self._file.file_handle().truncate()

  def _refresh_data_cache(self):
    """Refresh the contents of the multistore.

    The multistore must be locked when this is called.

    Raises:
      NewerCredentialStoreError: Raised when a newer client has written the
        store.
    """
    self._data = {}
    try:
      raw_data = self._locked_json_read()
    except Exception:
      logger.warn('Credential data store could not be loaded. '
                  'Will ignore and overwrite.')
      return

    version = 0
    try:
      version = raw_data['file_version']
    except Exception:
      logger.warn('Missing version for credential data store. It may be '
                  'corrupt or an old version. Overwriting.')
    if version > 1:
      raise NewerCredentialStoreError(
          'Credential file has file_version of %d. '
          'Only file_version of 1 is supported.' % version)

    credentials = []
    try:
      credentials = raw_data['data']
    except (TypeError, KeyError):
      pass

    for cred_entry in credentials:
      try:
        (key, credential) = self._decode_credential_from_json(cred_entry)
        self._data[key] = credential
      except:
        # If something goes wrong loading a credential, just ignore it
        logger.info('Error decoding credential, skipping', exc_info=True)

  def _decode_credential_from_json(self, cred_entry):
    """Load a credential from our JSON serialization.

    Args:
      cred_entry: A dict entry from the data member of our format

    Returns:
      (key, cred) where the key is the key tuple and the cred is the
        OAuth2Credential object.
    """
    raw_key = cred_entry['key']
    key = util.dict_to_tuple_key(raw_key)
    credential = None
    credential = Credentials.new_from_json(simplejson.dumps(cred_entry['credential']))
    return (key, credential)

  def _write(self):
    """Write the cached data back out.

    The multistore must be locked.
    """
    raw_data = {'file_version': 1}
    raw_creds = []
    raw_data['data'] = raw_creds
    for (cred_key, cred) in self._data.items():
      raw_key = dict(cred_key)
      raw_cred = simplejson.loads(cred.to_json())
      raw_creds.append({'key': raw_key, 'credential': raw_cred})
    self._locked_json_write(raw_data)

  def _get_credential(self, key):
    """Get a credential from the multistore.

    The multistore must be locked.

    Args:
      key: The key used to retrieve the credential

    Returns:
      The credential specified or None if not present
    """
    return self._data.get(key, None)

  def _update_credential(self, key, cred):
    """Update a credential and write the multistore.

    This must be called when the multistore is locked.

    Args:
      key: The key used to retrieve the credential
      cred: The OAuth2Credential to update/set
    """
    self._data[key] = cred
    self._write()

  def _delete_credential(self, key):
    """Delete a credential and write the multistore.

    This must be called when the multistore is locked.

    Args:
      key: The key used to retrieve the credential
    """
    try:
      del self._data[key]
    except KeyError:
      pass
    self._write()

  def _get_storage(self, key):
    """Get a Storage object to get/set a credential.

    This Storage is a 'view' into the multistore.

    Args:
      key: The key used to retrieve the credential

    Returns:
      A Storage object that can be used to get/set this cred
    """
    return self._Storage(self, key)

########NEW FILE########
__FILENAME__ = tools
# Copyright (C) 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Command-line tools for authenticating via OAuth 2.0

Do the OAuth 2.0 Web Server dance for a command line application. Stores the
generated credentials in a common file that is used by other example apps in
the same directory.
"""

__author__ = 'jcgregorio@google.com (Joe Gregorio)'
__all__ = ['run']


import BaseHTTPServer
from gflags import gflags
import socket
import sys
import webbrowser

from oauth2client.client import FlowExchangeError
from oauth2client.client import OOB_CALLBACK_URN
from oauth2client import util

try:
  from urlparse import parse_qsl
except ImportError:
  from cgi import parse_qsl


FLAGS = gflags.FLAGS

gflags.DEFINE_boolean('auth_local_webserver', True,
                      ('Run a local web server to handle redirects during '
                       'OAuth authorization.'))

gflags.DEFINE_string('auth_host_name', 'localhost',
                     ('Host name to use when running a local web server to '
                      'handle redirects during OAuth authorization.'))

gflags.DEFINE_multi_int('auth_host_port', [8080, 8090],
                        ('Port to use when running a local web server to '
                         'handle redirects during OAuth authorization.'))


class ClientRedirectServer(BaseHTTPServer.HTTPServer):
  """A server to handle OAuth 2.0 redirects back to localhost.

  Waits for a single request and parses the query parameters
  into query_params and then stops serving.
  """
  query_params = {}


class ClientRedirectHandler(BaseHTTPServer.BaseHTTPRequestHandler):
  """A handler for OAuth 2.0 redirects back to localhost.

  Waits for a single request and parses the query parameters
  into the servers query_params and then stops serving.
  """

  def do_GET(s):
    """Handle a GET request.

    Parses the query parameters and prints a message
    if the flow has completed. Note that we can't detect
    if an error occurred.
    """
    s.send_response(200)
    s.send_header("Content-type", "text/html")
    s.end_headers()
    query = s.path.split('?', 1)[-1]
    query = dict(parse_qsl(query))
    s.server.query_params = query
    s.wfile.write("<html><head><title>Authentication Status</title></head>")
    s.wfile.write("<body><p>The authentication flow has completed.</p>")
    s.wfile.write("</body></html>")

  def log_message(self, format, *args):
    """Do not log messages to stdout while running as command line program."""
    pass


@util.positional(2)
def run(flow, storage, http=None):
  """Core code for a command-line application.

  The run() function is called from your application and runs through all the
  steps to obtain credentials. It takes a Flow argument and attempts to open an
  authorization server page in the user's default web browser. The server asks
  the user to grant your application access to the user's data. If the user
  grants access, the run() function returns new credentials. The new credentials
  are also stored in the Storage argument, which updates the file associated
  with the Storage object.

  It presumes it is run from a command-line application and supports the
  following flags:

    --auth_host_name: Host name to use when running a local web server
      to handle redirects during OAuth authorization.
      (default: 'localhost')

    --auth_host_port: Port to use when running a local web server to handle
      redirects during OAuth authorization.;
      repeat this option to specify a list of values
      (default: '[8080, 8090]')
      (an integer)

    --[no]auth_local_webserver: Run a local web server to handle redirects
      during OAuth authorization.
      (default: 'true')

  Since it uses flags make sure to initialize the gflags module before calling
  run().

  Args:
    flow: Flow, an OAuth 2.0 Flow to step through.
    storage: Storage, a Storage to store the credential in.
    http: An instance of httplib2.Http.request
         or something that acts like it.

  Returns:
    Credentials, the obtained credential.
  """
  if FLAGS.auth_local_webserver:
    success = False
    port_number = 0
    for port in FLAGS.auth_host_port:
      port_number = port
      try:
        httpd = ClientRedirectServer((FLAGS.auth_host_name, port),
                                     ClientRedirectHandler)
      except socket.error, e:
        pass
      else:
        success = True
        break
    FLAGS.auth_local_webserver = success
    if not success:
      print 'Failed to start a local webserver listening on either port 8080'
      print 'or port 9090. Please check your firewall settings and locally'
      print 'running programs that may be blocking or using those ports.'
      print
      print 'Falling back to --noauth_local_webserver and continuing with',
      print 'authorization.'
      print

  if FLAGS.auth_local_webserver:
    oauth_callback = 'http://%s:%s/' % (FLAGS.auth_host_name, port_number)
  else:
    oauth_callback = OOB_CALLBACK_URN
  flow.redirect_uri = oauth_callback
  authorize_url = flow.step1_get_authorize_url()

  if FLAGS.auth_local_webserver:
    webbrowser.open(authorize_url, new=1, autoraise=True)
    print 'Your browser has been opened to visit:'
    print
    print '    ' + authorize_url
    print
    print 'If your browser is on a different machine then exit and re-run this'
    print 'application with the command-line parameter '
    print
    print '  --noauth_local_webserver'
    print
  else:
    print 'Go to the following link in your browser:'
    print
    print '    ' + authorize_url
    print

  code = None
  if FLAGS.auth_local_webserver:
    httpd.handle_request()
    if 'error' in httpd.query_params:
      sys.exit('Authentication request was rejected.')
    if 'code' in httpd.query_params:
      code = httpd.query_params['code']
    else:
      print 'Failed to find "code" in the query parameters of the redirect.'
      sys.exit('Try running with --noauth_local_webserver.')
  else:
    code = raw_input('Enter verification code: ').strip()

  try:
    credential = flow.step2_exchange(code, http=http)
  except FlowExchangeError, e:
    sys.exit('Authentication has failed: %s' % e)

  storage.put(credential)
  credential.set_store(storage)
  print 'Authentication successful.'

  return credential

########NEW FILE########
__FILENAME__ = util
#!/usr/bin/env python
#
# Copyright 2010 Google Inc.
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
#

"""Common utility library."""

__author__ = ['rafek@google.com (Rafe Kaplan)',
              'guido@google.com (Guido van Rossum)',
]
__all__ = [
  'positional',
]

from gflags import gflags
import inspect
import logging
import types
import urllib
import urlparse

try:
  from urlparse import parse_qsl
except ImportError:
  from cgi import parse_qsl

logger = logging.getLogger(__name__)

FLAGS = gflags.FLAGS

gflags.DEFINE_enum('positional_parameters_enforcement', 'WARNING',
    ['EXCEPTION', 'WARNING', 'IGNORE'],
    'The action when an oauth2client.util.positional declaration is violated.')


def positional(max_positional_args):
  """A decorator to declare that only the first N arguments my be positional.

  This decorator makes it easy to support Python 3 style key-word only
  parameters. For example, in Python 3 it is possible to write:

    def fn(pos1, *, kwonly1=None, kwonly1=None):
      ...

  All named parameters after * must be a keyword:

    fn(10, 'kw1', 'kw2')  # Raises exception.
    fn(10, kwonly1='kw1')  # Ok.

  Example:
    To define a function like above, do:

      @positional(1)
      def fn(pos1, kwonly1=None, kwonly2=None):
        ...

    If no default value is provided to a keyword argument, it becomes a required
    keyword argument:

      @positional(0)
      def fn(required_kw):
        ...

    This must be called with the keyword parameter:

      fn()  # Raises exception.
      fn(10)  # Raises exception.
      fn(required_kw=10)  # Ok.

    When defining instance or class methods always remember to account for
    'self' and 'cls':

      class MyClass(object):

        @positional(2)
        def my_method(self, pos1, kwonly1=None):
          ...

        @classmethod
        @positional(2)
        def my_method(cls, pos1, kwonly1=None):
          ...

  The positional decorator behavior is controlled by the
  --positional_parameters_enforcement flag. The flag may be set to 'EXCEPTION',
  'WARNING' or 'IGNORE' to raise an exception, log a warning, or do nothing,
  respectively, if a declaration is violated.

  Args:
    max_positional_arguments: Maximum number of positional arguments. All
      parameters after the this index must be keyword only.

  Returns:
    A decorator that prevents using arguments after max_positional_args from
    being used as positional parameters.

  Raises:
    TypeError if a key-word only argument is provided as a positional parameter,
    but only if the --positional_parameters_enforcement flag is set to
    'EXCEPTION'.
  """
  def positional_decorator(wrapped):
    def positional_wrapper(*args, **kwargs):
      if len(args) > max_positional_args:
        plural_s = ''
        if max_positional_args != 1:
          plural_s = 's'
        message = '%s() takes at most %d positional argument%s (%d given)' % (
            wrapped.__name__, max_positional_args, plural_s, len(args))
        if FLAGS.positional_parameters_enforcement == 'EXCEPTION':
          raise TypeError(message)
        elif FLAGS.positional_parameters_enforcement == 'WARNING':
          logger.warning(message)
        else: # IGNORE
          pass
      return wrapped(*args, **kwargs)
    return positional_wrapper

  if isinstance(max_positional_args, (int, long)):
    return positional_decorator
  else:
    args, _, _, defaults = inspect.getargspec(max_positional_args)
    return positional(len(args) - len(defaults))(max_positional_args)


def scopes_to_string(scopes):
  """Converts scope value to a string.

  If scopes is a string then it is simply passed through. If scopes is an
  iterable then a string is returned that is all the individual scopes
  concatenated with spaces.

  Args:
    scopes: string or iterable of strings, the scopes.

  Returns:
    The scopes formatted as a single string.
  """
  if isinstance(scopes, types.StringTypes):
    return scopes
  else:
    return ' '.join(scopes)


def dict_to_tuple_key(dictionary):
  """Converts a dictionary to a tuple that can be used as an immutable key.

  The resulting key is always sorted so that logically equivalent dictionaries
  always produce an identical tuple for a key.

  Args:
    dictionary: the dictionary to use as the key.

  Returns:
    A tuple representing the dictionary in it's naturally sorted ordering.
  """
  return tuple(sorted(dictionary.items()))


def _add_query_parameter(url, name, value):
  """Adds a query parameter to a url.

  Replaces the current value if it already exists in the URL.

  Args:
    url: string, url to add the query parameter to.
    name: string, query parameter name.
    value: string, query parameter value.

  Returns:
    Updated query parameter. Does not update the url if value is None.
  """
  if value is None:
    return url
  else:
    parsed = list(urlparse.urlparse(url))
    q = dict(parse_qsl(parsed[4]))
    q[name] = value
    parsed[4] = urllib.urlencode(q)
    return urlparse.urlunparse(parsed)

########NEW FILE########
__FILENAME__ = xsrfutil
#!/usr/bin/python2.5
#
# Copyright 2010 the Melange authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Helper methods for creating & verifying XSRF tokens."""

__authors__ = [
  '"Doug Coker" <dcoker@google.com>',
  '"Joe Gregorio" <jcgregorio@google.com>',
]


import base64
import hmac
import os  # for urandom
import time

from oauth2client import util


# Delimiter character
DELIMITER = ':'

# 1 hour in seconds
DEFAULT_TIMEOUT_SECS = 1*60*60

@util.positional(2)
def generate_token(key, user_id, action_id="", when=None):
  """Generates a URL-safe token for the given user, action, time tuple.

  Args:
    key: secret key to use.
    user_id: the user ID of the authenticated user.
    action_id: a string identifier of the action they requested
      authorization for.
    when: the time in seconds since the epoch at which the user was
      authorized for this action. If not set the current time is used.

  Returns:
    A string XSRF protection token.
  """
  when = when or int(time.time())
  digester = hmac.new(key)
  digester.update(str(user_id))
  digester.update(DELIMITER)
  digester.update(action_id)
  digester.update(DELIMITER)
  digester.update(str(when))
  digest = digester.digest()

  token = base64.urlsafe_b64encode('%s%s%d' % (digest,
                                               DELIMITER,
                                               when))
  return token


@util.positional(3)
def validate_token(key, token, user_id, action_id="", current_time=None):
  """Validates that the given token authorizes the user for the action.

  Tokens are invalid if the time of issue is too old or if the token
  does not match what generateToken outputs (i.e. the token was forged).

  Args:
    key: secret key to use.
    token: a string of the token generated by generateToken.
    user_id: the user ID of the authenticated user.
    action_id: a string identifier of the action they requested
      authorization for.

  Returns:
    A boolean - True if the user is authorized for the action, False
    otherwise.
  """
  if not token:
    return False
  try:
    decoded = base64.urlsafe_b64decode(str(token))
    token_time = long(decoded.split(DELIMITER)[-1])
  except (TypeError, ValueError):
    return False
  if current_time is None:
    current_time = time.time()
  # If the token is too old it's not valid.
  if current_time - token_time > DEFAULT_TIMEOUT_SECS:
    return False

  # The given token should match the generated one with the same time.
  expected_token = generate_token(key, user_id, action_id=action_id,
                                  when=token_time)
  if len(token) != len(expected_token):
    return False

  # Perform constant time comparison to avoid timing attacks
  different = 0
  for x, y in zip(token, expected_token):
    different |= ord(x) ^ ord(y)
  if different:
    return False

  return True

########NEW FILE########
__FILENAME__ = server
# -*- coding: utf-8 -*-
# Copyright 2013 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License")
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

__author__ = 'ericbidelman@chromium.org (Eric Bidelman)'

import json
import logging
import os
import webapp2

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import users

import common
import models
import settings
import uma


def normalized_name(val):
  return val.lower().replace(' ', '').replace('/', '')

def first_of_milestone(feature_list, milestone, start=0):
  for i in xrange(start, len(feature_list)):
    f = feature_list[i]
    if (str(f['shipped_milestone']) == str(milestone) or
        f['impl_status_chrome'] == str(milestone)):
      return i
  return -1

  
class MainHandler(common.ContentHandler, common.JSONHandler):

  def __get_omaha_data(self):
    omaha_data = memcache.get('omaha_data')
    if omaha_data is None:
      result = urlfetch.fetch('http://omahaproxy.appspot.com/all.json')
      if result.status_code == 200:
        omaha_data = json.loads(result.content)
        memcache.set('omaha_data', omaha_data, time=86400) # cache for 24hrs.

    return omaha_data

  def __annotate_first_of_milestones(self, feature_list):
    try:
      omaha_data = self.__get_omaha_data()

      win_versions = omaha_data[0]['versions']
      for v in win_versions:
        s = v.get('version') or v.get('prev_version')
        LATEST_VERSION = int(s.split('.')[0])
        break

      # TODO(ericbidelman) - memcache this calculation as part of models.py
      milestones = range(1, LATEST_VERSION + 1)
      milestones.reverse()
      versions = [
        models.IMPLEMENATION_STATUS[models.NO_ACTIVE_DEV],
        models.IMPLEMENATION_STATUS[models.PROPOSED],
        models.IMPLEMENATION_STATUS[models.IN_DEVELOPMENT],
        ]
      versions.extend(milestones)
      versions.append(models.IMPLEMENATION_STATUS[models.NO_LONGER_PURSUING])

      last_good_idx = 0
      for i, version in enumerate(versions):
        idx = first_of_milestone(feature_list, version, start=last_good_idx)
        if idx != -1:
          feature_list[idx]['first_of_milestone'] = True
          last_good_idx = idx
    except Exception as e:
      logging.error(e)

  def __get_feature_list(self):
    feature_list = models.Feature.get_chronological() # Memcached
    self.__annotate_first_of_milestones(feature_list)
    return feature_list

  def get(self, path, feature_id=None):
    # Default to features page.
    # TODO: remove later when we want an index.html
    if not path:
      return self.redirect('/features')

    # Default /metrics to CSS ranking.
    # TODO: remove later when we want /metrics/index.html
    if path == 'metrics' or path == 'metrics/css':
      return self.redirect('/metrics/css/popularity')

    # Remove trailing slash from URL and redirect. e.g. /metrics/ -> /metrics
    if feature_id == '':
      return self.redirect(self.request.path.rstrip('/'))

    template_data = {}

    if path.startswith('features'):
      if path.endswith('.json'): # JSON request.
        feature_list = self.__get_feature_list()
        return common.JSONHandler.get(self, feature_list, formatted=True)
      elif path.endswith('.xml'): # Atom feed request.
        filterby = None

        category = self.request.get('category', None)
        if category is not None:
          for k,v in models.FEATURE_CATEGORIES.iteritems():
            normalized = normalized_name(v)
            if category == normalized:
              filterby = ('category =', k)
              break

        feature_list = models.Feature.get_all( # Memcached
            limit=settings.RSS_FEED_LIMIT,
            filterby=filterby,
            order='-updated')

        return self.render_atom_feed('Features', feature_list)
      else:
        # if settings.PROD: 
        #   feature_list = self.__get_feature_list()
        # else:
        #   result = urlfetch.fetch(
        #     self.request.scheme + '://' + self.request.host +
        #     '/static/js/mockdata.json')
        #   feature_list = json.loads(result.content)

        # template_data['features'] = json.dumps(
        #     feature_list, separators=(',',':'))

        template_data['categories'] = [
          (v, normalized_name(v)) for k,v in
          models.FEATURE_CATEGORIES.iteritems()]
        template_data['IMPLEMENATION_STATUSES'] = [
          {'key': k, 'val': v} for k,v in
          models.IMPLEMENATION_STATUS.iteritems()]
        template_data['VENDOR_VIEWS'] = [
          {'key': k, 'val': v} for k,v in
          models.VENDOR_VIEWS.iteritems()]
        template_data['WEB_DEV_VIEWS'] = [
          {'key': k, 'val': v} for k,v in
          models.WEB_DEV_VIEWS.iteritems()]
        template_data['STANDARDS_VALS'] = [
          {'key': k, 'val': v} for k,v in
          models.STANDARDIZATION.iteritems()]

    elif path.startswith('metrics/css/timeline'):
      properties = sorted(uma.CSS_PROPERTY_BUCKETS.items(), key=lambda x:x[1])
      template_data['CSS_PROPERTY_BUCKETS'] = json.dumps(
          properties, separators=(',',':'))
    elif path.startswith('metrics/feature/timeline'):
      properties = sorted(uma.FEATUREOBSERVER_BUCKETS.items(), key=lambda x:x[1])
      template_data['FEATUREOBSERVER_BUCKETS'] = json.dumps(
          properties, separators=(',',':'))

    self.render(data=template_data, template_path=os.path.join(path + '.html'))


# Main URL routes.
routes = [
  ('/(.*)/([0-9]*)', MainHandler),
  ('/(.*)', MainHandler),
]

app = webapp2.WSGIApplication(routes, debug=settings.DEBUG)
app.error_handlers[404] = common.handle_404
if settings.PROD and not settings.DEBUG:
  app.error_handlers[500] = common.handle_500

########NEW FILE########
__FILENAME__ = settings
import os

#Hack to get custom tags working django 1.3 + python27.
INSTALLED_APPS = (
  #'nothing',
  'customtags',
)

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))

TEMPLATE_DIRS = (
  os.path.join(ROOT_DIR, 'templates')
)
################################################################################

if (os.getenv('SERVER_SOFTWARE', '').startswith('Google App Engine') or
    os.getenv('SETTINGS_MODE') == 'prod'):
  PROD = True
else:
  PROD = False

DEBUG = not PROD
TEMPLATE_DEBUG = DEBUG

APP_TITLE = 'Chromium Dashboard'

APP_VERSION = os.environ['CURRENT_VERSION_ID'].split('.')[0]
MEMCACHE_KEY_PREFIX = APP_VERSION # For memcache busting on new version

RSS_FEED_LIMIT = 15

VULCANIZE = True #PROD

########NEW FILE########
__FILENAME__ = uma
# TODO(ericbidelman): generate this file from

# http://src.chromium.org/viewvc/blink/trunk/Source/core/frame/UseCounter.cpp
CSS_PROPERTY_BUCKETS = {
  # 1 was reserved for number of CSS Pages Visited
  2: 'color',
  3: 'direction',
  4: 'display',
  5: 'font',
  6: 'font-family',
  7: 'font-size',
  8: 'font-style',
  9: 'font-variant',
  10: 'font-weight',
  11: 'text-rendering',
  12: 'webkit-font-feature-settings',
  13: 'webkit-font-kerning',
  14: 'webkit-font-smoothing',
  15: 'webkit-font-variant-ligatures',
  16: 'webkit-locale',
  17: 'webkit-text-orientation',
  18: 'webkit-writing-mode',
  19: 'zoom',
  20: 'line-height',
  21: 'background',
  22: 'background-attachment',
  23: 'background-clip',
  24: 'background-color',
  25: 'background-image',
  26: 'background-origin',
  27: 'background-position',
  28: 'background-position-x',
  29: 'background-position-y',
  30: 'background-repeat',
  31: 'background-repeat-x',
  32: 'background-repeat-y',
  33: 'background-size',
  34: 'border',
  35: 'border-bottom',
  36: 'border-bottom-color',
  37: 'border-bottom-left-radius',
  38: 'border-bottom-right-radius',
  39: 'border-bottom-style',
  40: 'border-bottom-width',
  41: 'border-collapse',
  42: 'border-color',
  43: 'border-image',
  44: 'border-image-outset',
  45: 'border-image-repeat',
  46: 'border-image-slice',
  47: 'border-image-source',
  48: 'border-image-width',
  49: 'border-left',
  50: 'border-left-color',
  51: 'border-left-style',
  52: 'border-left-width',
  53: 'border-radius',
  54: 'border-right',
  55: 'border-right-color',
  56: 'border-right-style',
  57: 'border-right-width',
  58: 'border-spacing',
  59: 'border-style',
  60: 'border-top',
  61: 'border-top-color',
  62: 'border-top-left-radius',
  63: 'border-top-right-radius',
  64: 'border-top-style',
  65: 'border-top-width',
  66: 'border-width',
  67: 'bottom',
  68: 'box-shadow',
  69: 'box-sizing',
  70: 'caption-side',
  71: 'clear',
  72: 'clip',
  73: 'webkit-clip-path',
  74: 'content',
  75: 'counter-increment',
  76: 'counter-reset',
  77: 'cursor',
  78: 'empty-cells',
  79: 'float',
  80: 'font-stretch',
  81: 'height',
  82: 'image-rendering',
  83: 'left',
  84: 'letter-spacing',
  85: 'list-style',
  86: 'list-style-image',
  87: 'list-style-position',
  88: 'list-style-type',
  89: 'margin',
  90: 'margin-bottom',
  91: 'margin-left',
  92: 'margin-right',
  93: 'margin-top',
  94: 'max-height',
  95: 'max-width',
  96: 'min-height',
  97: 'min-width',
  98: 'opacity',
  99: 'orphans',
  100: 'outline',
  101: 'outline-color',
  102: 'outline-offset',
  103: 'outline-style',
  104: 'outline-width',
  105: 'overflow',
  106: 'overflow-wrap',
  107: 'overflow-x',
  108: 'overflow-y',
  109: 'padding',
  110: 'padding-bottom',
  111: 'padding-left',
  112: 'padding-right',
  113: 'padding-top',
  114: 'page',
  115: 'page-break-after',
  116: 'page-break-before',
  117: 'page-break-inside',
  118: 'pointer-events',
  119: 'position',
  120: 'quotes',
  121: 'resize',
  122: 'right',
  123: 'size',
  124: 'src',
  125: 'speak',
  126: 'table-layout',
  127: 'tab-size',
  128: 'text-align',
  129: 'text-decoration',
  130: 'text-indent',
  131: 'text-line-through',
  132: 'text-line-through-color',
  133: 'text-line-through-mode',
  134: 'text-line-through-style',
  135: 'text-line-through-width',
  136: 'text-overflow',
  137: 'text-overline',
  138: 'text-overline-color',
  139: 'text-overline-mode',
  140: 'text-overline-style',
  141: 'text-overline-width',
  142: 'text-shadow',
  143: 'text-transform',
  144: 'text-underline',
  145: 'text-underline-color',
  146: 'text-underline-mode',
  147: 'text-underline-style',
  148: 'text-underline-width',
  149: 'top',
  150: 'transition',
  151: 'transition-delay',
  152: 'transition-duration',
  153: 'transition-property',
  154: 'transition-timing-function',
  155: 'unicode-bidi',
  156: 'unicode-range',
  157: 'vertical-align',
  158: 'visibility',
  159: 'white-space',
  160: 'widows',
  161: 'width',
  162: 'word-break',
  163: 'word-spacing',
  164: 'word-wrap',
  165: 'z-index',
  166: 'webkit-animation',
  167: 'webkit-animation-delay',
  168: 'webkit-animation-direction',
  169: 'webkit-animation-duration',
  170: 'webkit-animation-fill-mode',
  171: 'webkit-animation-iteration-count',
  172: 'webkit-animation-name',
  173: 'webkit-animation-play-state',
  174: 'webkit-animation-timing-function',
  175: 'webkit-appearance',
  176: 'webkit-aspect-ratio',
  177: 'webkit-backface-visibility',
  178: 'webkit-background-clip',
  179: 'webkit-background-composite',
  180: 'webkit-background-origin',
  181: 'webkit-background-size',
  182: 'webkit-border-after',
  183: 'webkit-border-after-color',
  184: 'webkit-border-after-style',
  185: 'webkit-border-after-width',
  186: 'webkit-border-before',
  187: 'webkit-border-before-color',
  188: 'webkit-border-before-style',
  189: 'webkit-border-before-width',
  190: 'webkit-border-end',
  191: 'webkit-border-end-color',
  192: 'webkit-border-end-style',
  193: 'webkit-border-end-width',
  194: 'webkit-border-fit',
  195: 'webkit-border-horizontal-spacing',
  196: 'webkit-border-image',
  197: 'webkit-border-radius',
  198: 'webkit-border-start',
  199: 'webkit-border-start-color',
  200: 'webkit-border-start-style',
  201: 'webkit-border-start-width',
  202: 'webkit-border-vertical-spacing',
  203: 'webkit-box-align',
  204: 'webkit-box-direction',
  205: 'webkit-box-flex',
  206: 'webkit-box-flex-group',
  207: 'webkit-box-lines',
  208: 'webkit-box-ordinal-group',
  209: 'webkit-box-orient',
  210: 'webkit-box-pack',
  211: 'webkit-box-reflect',
  212: 'webkit-box-shadow',
  213: 'webkit-color-correction',
  214: 'webkit-column-axis',
  215: 'webkit-column-break-after',
  216: 'webkit-column-break-before',
  217: 'webkit-column-break-inside',
  218: 'webkit-column-count',
  219: 'webkit-column-gap',
  220: 'webkit-column-progression',
  221: 'webkit-column-rule',
  222: 'webkit-column-rule-color',
  223: 'webkit-column-rule-style',
  224: 'webkit-column-rule-width',
  225: 'webkit-column-span',
  226: 'webkit-column-width',
  227: 'webkit-columns',
  228: 'webkit-box-decoration-break',
  229: 'webkit-filter',
  230: 'webkit-align-content',
  231: 'webkit-align-items',
  232: 'webkit-align-self',
  233: 'webkit-flex',
  234: 'webkit-flex-basis',
  235: 'webkit-flex-direction',
  236: 'webkit-flex-flow',
  237: 'webkit-flex-grow',
  238: 'webkit-flex-shrink',
  239: 'webkit-flex-wrap',
  240: 'webkit-justify-content',
  241: 'webkit-font-size-delta',
  242: 'webkit-grid-columns',
  243: 'webkit-grid-rows',
  244: 'webkit-grid-start',
  245: 'webkit-grid-end',
  246: 'webkit-grid-before',
  247: 'webkit-grid-after',
  248: 'webkit-grid-column',
  249: 'webkit-grid-row',
  250: 'webkit-grid-auto-flow',
  251: 'webkit-highlight',
  252: 'webkit-hyphenate-character',
  253: 'webkit-hyphenate-limit-after',
  254: 'webkit-hyphenate-limit-before',
  255: 'webkit-hyphenate-limit-lines',
  256: 'webkit-hyphens',
  257: 'webkit-line-box-contain',
  258: 'webkit-line-align',
  259: 'webkit-line-break',
  260: 'webkit-line-clamp',
  261: 'webkit-line-grid',
  262: 'webkit-line-snap',
  263: 'webkit-logical-width',
  264: 'webkit-logical-height',
  265: 'webkit-margin-after-collapse',
  266: 'webkit-margin-before-collapse',
  267: 'webkit-margin-bottom-collapse',
  268: 'webkit-margin-top-collapse',
  269: 'webkit-margin-collapse',
  270: 'webkit-margin-after',
  271: 'webkit-margin-before',
  272: 'webkit-margin-end',
  273: 'webkit-margin-start',
  274: 'webkit-marquee',
  275: 'webkit-marquee-direction',
  276: 'webkit-marquee-increment',
  277: 'webkit-marquee-repetition',
  278: 'webkit-marquee-speed',
  279: 'webkit-marquee-style',
  280: 'webkit-mask',
  281: 'webkit-mask-box-image',
  282: 'webkit-mask-box-image-outset',
  283: 'webkit-mask-box-image-repeat',
  284: 'webkit-mask-box-image-slice',
  285: 'webkit-mask-box-image-source',
  286: 'webkit-mask-box-image-width',
  287: 'webkit-mask-clip',
  288: 'webkit-mask-composite',
  289: 'webkit-mask-image',
  290: 'webkit-mask-origin',
  291: 'webkit-mask-position',
  292: 'webkit-mask-position-x',
  293: 'webkit-mask-position-y',
  294: 'webkit-mask-repeat',
  295: 'webkit-mask-repeat-x',
  296: 'webkit-mask-repeat-y',
  297: 'webkit-mask-size',
  298: 'webkit-max-logical-width',
  299: 'webkit-max-logical-height',
  300: 'webkit-min-logical-width',
  301: 'webkit-min-logical-height',
  302: 'webkit-nbsp-mode',
  303: 'webkit-order',
  304: 'webkit-padding-after',
  305: 'webkit-padding-before',
  306: 'webkit-padding-end',
  307: 'webkit-padding-start',
  308: 'webkit-perspective',
  309: 'webkit-perspective-origin',
  310: 'webkit-perspective-origin-x',
  311: 'webkit-perspective-origin-y',
  312: 'webkit-print-color-adjust',
  313: 'webkit-rtl-ordering',
  314: 'webkit-ruby-position',
  315: 'webkit-text-combine',
  316: 'webkit-text-decorations-in-effect',
  317: 'webkit-text-emphasis',
  318: 'webkit-text-emphasis-color',
  319: 'webkit-text-emphasis-position',
  320: 'webkit-text-emphasis-style',
  321: 'webkit-text-fill-color',
  322: 'webkit-text-security',
  323: 'webkit-text-stroke',
  324: 'webkit-text-stroke-color',
  325: 'webkit-text-stroke-width',
  326: 'webkit-transform',
  327: 'webkit-transform-origin',
  328: 'webkit-transform-origin-x',
  329: 'webkit-transform-origin-y',
  330: 'webkit-transform-origin-z',
  331: 'webkit-transform-style',
  332: 'webkit-transition',
  333: 'webkit-transition-delay',
  334: 'webkit-transition-duration',
  335: 'webkit-transition-property',
  336: 'webkit-transition-timing-function',
  337: 'webkit-user-drag',
  338: 'webkit-user-modify',
  339: 'webkit-user-select',
  340: 'webkit-flow-into',
  341: 'webkit-flow-from',
  342: 'webkit-region-overflow',
  343: 'webkit-region-break-after',
  344: 'webkit-region-break-before',
  345: 'webkit-region-break-inside',
  346: 'webkit-shape-inside',
  347: 'webkit-shape-outside',
  348: 'webkit-shape-margin',
  349: 'webkit-shape-padding',
  350: 'webkit-wrap-flow',
  351: 'webkit-wrap-through',
  352: 'webkit-wrap',
  353: 'webkit-tap-highlight-color',
  354: 'webkit-app-region',
  355: 'clip-path',
  356: 'clip-rule',
  357: 'mask',
  358: 'enable-background',
  359: 'filter',
  360: 'flood-color',
  361: 'flood-opacity',
  362: 'lighting-color',
  363: 'stop-color',
  364: 'stop-opacity',
  365: 'color-interpolation',
  366: 'color-interpolation-filters',
  367: 'color-profile',
  368: 'color-rendering',
  369: 'fill',
  370: 'fill-opacity',
  371: 'fill-rule',
  372: 'marker',
  373: 'marker-end',
  374: 'marker-mid',
  375: 'marker-start',
  376: 'mask-type',
  377: 'shape-rendering',
  378: 'stroke',
  379: 'stroke-dasharray',
  380: 'stroke-dashoffset',
  381: 'stroke-linecap',
  382: 'stroke-linejoin',
  383: 'stroke-miterlimit',
  384: 'stroke-opacity',
  385: 'stroke-width',
  386: 'alignment-baseline',
  387: 'baseline-shift',
  388: 'dominant-baseline',
  389: 'glyph-orientation-horizontal',
  390: 'glyph-orientation-vertical',
  391: 'kerning',
  392: 'text-anchor',
  393: 'vector-effect',
  394: 'writing-mode',
  395: 'webkit-svg-shadow',
  396: 'webkit-cursor-visibility',
  397: 'image-orientation',
  398: 'image-resolution',
  399: 'webkit-blend-mode',
  400: 'webkit-background-blend-mode',
  401: 'webkit-text-decoration-line',
  402: 'webkit-text-decoration-style',
  403: 'webkit-text-decoration-color',
  404: 'webkit-text-align-last',
  405: 'webkit-text-underline-position',
  406: 'max-zoom',
  407: 'min-zoom',
  408: 'orientation',
  409: 'user-zoom',
  410: 'webkit-dashboard-region',
  411: 'webkit-overflow-scrolling',
  412: 'webkit-app-region',
  413: 'webkit-filter',
  414: 'webkit-box-decoration-break',
  415: 'webkit-tap-highlight-color',
  416: 'buffered-rendering',
  417: 'grid-auto-rows',
  418: 'grid-auto-columns',
  419: 'background-blend-mode',
  420: 'mix-blend-mode',
  421: 'touch-action',
  422: 'grid-area',
  423: 'grid-template-areas',
  424: 'animation',
  425: 'animation-delay',
  426: 'animation-direction',
  427: 'animation-duration',
  428: 'animation-fill-mode',
  429: 'animation-iteration-count',
  430: 'animation-name',
  431: 'animation-play-state',
  432: 'animation-timing-function',
  433: 'object-fit',
  434: 'paint-order',
  435: 'mask-source-type',
  436: 'isolation',
  437: 'object-position',
  438: 'internal-callback',
  439: 'shape-image-threshold',
  440: 'column-fill',
  441: 'text-justify',
  442: 'touch-action-delay',
  443: 'justify-self',
  444: 'scroll-behavior',
  445: 'will-change',
  446: 'transform',
  447: 'transform-origin',
  448: 'transform-style',
  449: 'perspective',
  450: 'perspective-origin',
  451: 'backface-visibility',
  452: 'grid-template',
  453: 'grid',
}

PAGE_VISITS_BUCKET_ID = 52 # corresponds to the property below.

# http://src.chromium.org/viewvc/blink/trunk/Source/core/frame/UseCounter.h
FEATUREOBSERVER_BUCKETS = {
  0: 'PageDestruction',
  1: 'LegacyNotifications',
  2: 'MultipartMainResource',
  3: 'PrefixedIndexedDB',
  4: 'WorkerStart',
  5: 'SharedWorkerStart',
  6: 'LegacyWebAudio',
  7: 'WebAudioStart',
  9: 'UnprefixedIndexedDB',
  10: 'OpenWebDatabase',
  12: 'LegacyTextNotifications',
  13: 'UnprefixedRequestAnimationFrame',
  14: 'PrefixedRequestAnimationFrame',
  15: 'ContentSecurityPolicy',
  16: 'ContentSecurityPolicyReportOnly',
  18: 'PrefixedTransitionEndEvent',
  19: 'UnprefixedTransitionEndEvent',
  20: 'PrefixedAndUnprefixedTransitionEndEvent',
  21: 'AutoFocusAttribute',
  23: 'DataListElement',
  24: 'FormAttribute',
  25: 'IncrementalAttribute',
  26: 'InputTypeColor',
  27: 'InputTypeDate',
  28: 'InputTypeDateTime',
  29: 'InputTypeDateTimeFallback',
  30: 'InputTypeDateTimeLocal',
  31: 'InputTypeEmail',
  32: 'InputTypeMonth',
  33: 'InputTypeNumber',
  34: 'InputTypeRange',
  35: 'InputTypeSearch',
  36: 'InputTypeTel',
  37: 'InputTypeTime',
  38: 'InputTypeURL',
  39: 'InputTypeWeek',
  40: 'InputTypeWeekFallback',
  41: 'ListAttribute',
  42: 'MaxAttribute',
  43: 'MinAttribute',
  44: 'PatternAttribute',
  45: 'PlaceholderAttribute',
  46: 'PrecisionAttribute',
  47: 'PrefixedDirectoryAttribute',
  48: 'PrefixedSpeechAttribute',
  49: 'RequiredAttribute',
  50: 'ResultsAttribute',
  51: 'StepAttribute',
  52: 'PageVisits', # counts are divided by this number for actual %
  53: 'HTMLMarqueeElement',
  55: 'Reflection',
  57: 'PrefixedStorageInfo',
  58: 'XFrameOptions',
  59: 'XFrameOptionsSameOrigin',
  60: 'XFrameOptionsSameOriginWithBadAncestorChain',
  61: 'DeprecatedFlexboxWebContent',
  62: 'DeprecatedFlexboxChrome',
  63: 'DeprecatedFlexboxChromeExtension',
  65: 'UnprefixedPerformanceTimeline',
  66: 'PrefixedPerformanceTimeline',
  67: 'UnprefixedUserTiming',
  69: 'WindowEvent',
  70: 'ContentSecurityPolicyWithBaseElement',
  71: 'PrefixedMediaAddKey',
  72: 'PrefixedMediaGenerateKeyRequest',
  74: 'DocumentClear',
  76: 'SVGFontElement',
  77: 'XMLDocument',
  78: 'XSLProcessingInstruction',
  79: 'XSLTProcessor',
  80: 'SVGSwitchElement',
  82: 'HTMLShadowElementOlderShadowRoot',
  83: 'DocumentAll',
  84: 'FormElement',
  85: 'DemotedFormElement',
  86: 'CaptureAttributeAsEnum',
  87: 'ShadowDOMPrefixedPseudo',
  88: 'ShadowDOMPrefixedCreateShadowRoot',
  89: 'ShadowDOMPrefixedShadowRoot',
  90: 'SVGAnimationElement',
  91: 'KeyboardEventKeyLocation',
  92: 'CaptureEvents',
  93: 'ReleaseEvents',
  94: 'CSSDisplayRunIn',
  95: 'CSSDisplayCompact',
  96: 'LineClamp',
  97: 'SubFrameBeforeUnloadRegistered',
  98: 'SubFrameBeforeUnloadFired',
  99: 'CSSPseudoElementPrefixedDistributed',
  100: 'TextReplaceWholeText',
  101: 'PrefixedShadowRootConstructor',
  102: 'ConsoleMarkTimeline',
  103: 'CSSPseudoElementUserAgentCustomPseudo',
  104: 'DocumentTypeEntities',
  105: 'DocumentTypeInternalSubset',
  106: 'DocumentTypeNotations',
  107: 'ElementGetAttributeNode',
  108: 'ElementSetAttributeNode',
  109: 'ElementRemoveAttributeNode',
  110: 'ElementGetAttributeNodeNS',
  111: 'DocumentCreateAttribute',
  112: 'DocumentCreateAttributeNS',
  113: 'DocumentCreateCDATASection',
  114: 'DocumentInputEncoding',
  115: 'DocumentXMLEncoding',
  116: 'DocumentXMLStandalone',
  117: 'DocumentXMLVersion',
  118: 'NodeIsSameNode',
  119: 'NodeIsSupported',
  120: 'NodeNamespaceURI',
  122: 'NodeLocalName',
  123: 'NavigatorProductSub',
  124: 'NavigatorVendor',
  125: 'NavigatorVendorSub',
  126: 'FileError',
  127: 'DocumentCharset',
  128: 'PrefixedAnimationEndEvent',
  129: 'UnprefixedAnimationEndEvent',
  130: 'PrefixedAndUnprefixedAnimationEndEvent',
  131: 'PrefixedAnimationStartEvent',
  132: 'UnprefixedAnimationStartEvent',
  133: 'PrefixedAndUnprefixedAnimationStartEvent',
  134: 'PrefixedAnimationIterationEvent',
  135: 'UnprefixedAnimationIterationEvent',
  136: 'PrefixedAndUnprefixedAnimationIterationEvent',
  137: 'EventReturnValue',
  138: 'SVGSVGElement',
  139: 'SVGAnimateColorElement',
  140: 'InsertAdjacentText',
  141: 'InsertAdjacentElement',
  142: 'HasAttributes',
  143: 'DOMSubtreeModifiedEvent',
  144: 'DOMNodeInsertedEvent',
  145: 'DOMNodeRemovedEvent',
  146: 'DOMNodeRemovedFromDocumentEvent',
  147: 'DOMNodeInsertedIntoDocumentEvent',
  148: 'DOMCharacterDataModifiedEvent',
  150: 'DocumentAllLegacyCall',
  151: 'HTMLAppletElementLegacyCall',
  152: 'HTMLEmbedElementLegacyCall',
  153: 'HTMLObjectElementLegacyCall',
  154: 'BeforeLoadEvent',
  155: 'GetMatchedCSSRules',
  156: 'SVGFontInCSS',
  157: 'ScrollTopBodyNotQuirksMode',
  158: 'ScrollLeftBodyNotQuirksMode',
  160: 'AttributeOwnerElement',
  162: 'AttributeSpecified',
  163: 'BeforeLoadEventInIsolatedWorld',
  164: 'PrefixedAudioDecodedByteCount',
  165: 'PrefixedVideoDecodedByteCount',
  166: 'PrefixedVideoSupportsFullscreen',
  167: 'PrefixedVideoDisplayingFullscreen',
  168: 'PrefixedVideoEnterFullscreen',
  169: 'PrefixedVideoExitFullscreen',
  170: 'PrefixedVideoEnterFullScreen',
  171: 'PrefixedVideoExitFullScreen',
  172: 'PrefixedVideoDecodedFrameCount',
  173: 'PrefixedVideoDroppedFrameCount',
  176: 'PrefixedElementRequestFullscreen',
  177: 'PrefixedElementRequestFullScreen',
  178: 'BarPropLocationbar',
  179: 'BarPropMenubar',
  180: 'BarPropPersonalbar',
  181: 'BarPropScrollbars',
  182: 'BarPropStatusbar',
  183: 'BarPropToolbar',
  184: 'InputTypeEmailMultiple',
  185: 'InputTypeEmailMaxLength',
  186: 'InputTypeEmailMultipleMaxLength',
  187: 'TextTrackCueConstructor',
  188: 'CSSStyleDeclarationPropertyName',
  189: 'CSSStyleDeclarationFloatPropertyName',
  190: 'InputTypeText',
  191: 'InputTypeTextMaxLength',
  192: 'InputTypePassword',
  193: 'InputTypePasswordMaxLength',
  194: 'SVGInstanceRoot',
  195: 'ShowModalDialog',
  196: 'PrefixedPageVisibility',
  197: 'HTMLFrameElementLocation',
  198: 'CSSStyleSheetInsertRuleOptionalArg',
  199: 'CSSWebkitRegionAtRule',
  200: 'DocumentBeforeUnloadRegistered',
  201: 'DocumentBeforeUnloadFired',
  202: 'DocumentUnloadRegistered',
  203: 'DocumentUnloadFired',
  204: 'SVGLocatableNearestViewportElement',
  205: 'SVGLocatableFarthestViewportElement',
  206: 'IsIndexElement',
  207: 'HTMLHeadElementProfile',
  208: 'OverflowChangedEvent',
  209: 'SVGPointMatrixTransform',
  210: 'HTMLHtmlElementManifest',
  211: 'DOMFocusInOutEvent',
  212: 'FileGetLastModifiedDate',
  213: 'HTMLElementInnerText',
  214: 'HTMLElementOuterText',
  215: 'ReplaceDocumentViaJavaScriptURL',
  216: 'ElementSetAttributeNodeNS',
  217: 'ElementPrefixedMatchesSelector',
  218: 'DOMImplementationCreateCSSStyleSheet',
  219: 'CSSStyleSheetRules',
  220: 'CSSStyleSheetAddRule',
  221: 'CSSStyleSheetRemoveRule',
  222: 'InitMessageEvent',
  223: 'PrefixedInitMessageEvent',
  224: 'ElementSetPrefix',
  225: 'CSSStyleDeclarationGetPropertyCSSValue',
  226: 'SVGElementGetPresentationAttribute',
  229: 'PrefixedMediaCancelKeyRequest',
  230: 'DOMImplementationHasFeature',
  231: 'DOMImplementationHasFeatureReturnFalse',
  232: 'CanPlayTypeKeySystem',
  233: 'PrefixedDevicePixelRatioMediaFeature',
  234: 'PrefixedMaxDevicePixelRatioMediaFeature',
  235: 'PrefixedMinDevicePixelRatioMediaFeature',
  236: 'PrefixedTransform2dMediaFeature',
  237: 'PrefixedTransform3dMediaFeature',
  238: 'PrefixedAnimationMediaFeature',
  239: 'PrefixedViewModeMediaFeature',
  240: 'PrefixedStorageQuota',
  241: 'ContentSecurityPolicyReportOnlyInMeta',
  242: 'PrefixedMediaSourceOpen',
  243: 'ResetReferrerPolicy',
  244: 'CaseInsensitiveAttrSelectorMatch',
  245: 'CaptureAttributeAsBoolean',
  246: 'FormNameAccessForImageElement',
  247: 'FormNameAccessForPastNamesMap',
  248: 'FormAssociationByParser',
  249: 'HTMLSourceElementMedia',
  250: 'SVGSVGElementInDocument',
  251: 'SVGDocumentRootElement',
  252: 'DocumentCreateEventOptionalArgument',
  253: 'MediaErrorEncrypted',
  254: 'EventSourceURL',
  255: 'WebSocketURL',
  256: 'UnsafeEvalBlocksCSSOM',
  257: 'WorkerSubjectToCSP',
  258: 'WorkerAllowedByChildBlockedByScript',
  259: 'HTMLMediaElementControllerNotNull',
  260: 'DeprecatedWebKitGradient',
  261: 'DeprecatedWebKitLinearGradient',
  262: 'DeprecatedWebKitRepeatingLinearGradient',
  263: 'DeprecatedWebKitRadialGradient',
  264: 'DeprecatedWebKitRepeatingRadialGradient',
  265: 'PrefixedGetImageDataHD',
  266: 'PrefixedPutImageDataHD',
  267: 'PrefixedImageSmoothingEnabled',
  268: 'UnprefixedImageSmoothingEnabled',
  269: 'ShadowRootApplyAuthorStyles',
  270: 'PromiseConstructor',
  271: 'PromiseCast',
  272: 'PromiseReject',
  273: 'PromiseResolve',
  274: 'TextAutosizing',
  275: 'TextAutosizingLayout',
  276: 'HTMLAnchorElementPingAttribute',
  277: 'JavascriptExhaustedMemory',
  278: 'InsertAdjacentHTML',
  279: 'SVGClassName',
  280: 'HTMLAppletElement',
  281: 'HTMLMediaElementSeekToFragmentStart',
  282: 'HTMLMediaElementPauseAtFragmentEnd',
  283: 'PrefixedWindowURL',
  284: 'PrefixedWorkerURL',
  285: 'WindowOrientation',
  286: 'DOMStringListContains',
  287: 'DocumentCaptureEvents',
  288: 'DocumentReleaseEvents',
  289: 'WindowCaptureEvents',
  290: 'WindowReleaseEvents',
  291: 'PrefixedGamepad',
  292: 'ElementAnimateKeyframeListEffectObjectTiming',
  293: 'ElementAnimateKeyframeListEffectDoubleTiming',
  294: 'ElementAnimateKeyframeListEffectNoTiming',
  295: 'DocumentXPathCreateExpression',
  296: 'DocumentXPathCreateNSResolver',
  297: 'DocumentXPathEvaluate',
  298: 'AttrGetValue',
  299: 'AttrSetValue',
  300: 'AnimationConstructorKeyframeListEffectObjectTiming',
  301: 'AnimationConstructorKeyframeListEffectDoubleTiming',
  302: 'AnimationConstructorKeyframeListEffectNoTiming',
  303: 'AttrSetValueWithElement',
  304: 'PrefixedCancelAnimationFrame',
  305: 'PrefixedCancelRequestAnimationFrame',
  306: 'NamedNodeMapGetNamedItem',
  307: 'NamedNodeMapSetNamedItem',
  308: 'NamedNodeMapRemoveNamedItem',
  309: 'NamedNodeMapItem',
  310: 'NamedNodeMapGetNamedItemNS',
  311: 'NamedNodeMapSetNamedItemNS',
  312: 'NamedNodeMapRemoveNamedItemNS',
  313: 'OpenWebDatabaseInWorker',
  314: 'OpenWebDatabaseSyncInWorker',
  315: 'PrefixedAllowFullscreenAttribute',
  316: 'XHRProgressEventPosition',
  317: 'XHRProgressEventTotalSize',
  318: 'PrefixedDocumentIsFullscreen',
  319: 'PrefixedDocumentFullScreenKeyboardInputAllowed',
  320: 'PrefixedDocumentCurrentFullScreenElement',
  321: 'PrefixedDocumentCancelFullScreen',
  322: 'PrefixedDocumentFullscreenEnabled',
  323: 'PrefixedDocumentFullscreenElement',
  324: 'PrefixedDocumentExitFullscreen',
  325: 'SVGForeignObjectElement',
  326: 'PrefixedElementRequestPointerLock',
  327: 'SelectionSetPosition',
  328: 'AnimationPlayerFinishEvent',
  329: 'SVGSVGElementInXMLDocument',
  330: 'CanvasRenderingContext2DSetAlpha',
  331: 'CanvasRenderingContext2DSetCompositeOperation',
  332: 'CanvasRenderingContext2DSetLineWidth',
  333: 'CanvasRenderingContext2DSetLineCap',
  334: 'CanvasRenderingContext2DSetLineJoin',
  335: 'CanvasRenderingContext2DSetMiterLimit',
  336: 'CanvasRenderingContext2DClearShadow',
  337: 'CanvasRenderingContext2DSetStrokeColor',
  338: 'CanvasRenderingContext2DSetFillColor',
  339: 'CanvasRenderingContext2DDrawImageFromRect',
  340: 'CanvasRenderingContext2DSetShadow',
  341: 'PrefixedPerformanceClearResourceTimings',
  342: 'PrefixedPerformanceSetResourceTimingBufferSize',
  343: 'EventSrcElement',
  344: 'EventCancelBubble',
  345: 'EventPath',
  346: 'EventClipboardData',
  347: 'NodeIteratorDetach',
  348: 'AttrNodeValue',
  349: 'AttrTextContent',
  350: 'EventGetReturnValueTrue',
  351: 'EventGetReturnValueFalse',
  352: 'EventSetReturnValueTrue',
  353: 'EventSetReturnValueFalse',
  354: 'NodeIteratorExpandEntityReferences',
  355: 'TreeWalkerExpandEntityReferences',
  356: 'WindowOffscreenBuffering',
  357: 'WindowDefaultStatus',
  358: 'WindowDefaultstatus',
  359: 'PrefixedConvertPointFromPageToNode',
  360: 'PrefixedConvertPointFromNodeToPage',
  361: 'PrefixedTransitionEventConstructor',
  362: 'PrefixedMutationObserverConstructor',
  363: 'PrefixedIDBCursorConstructor',
  364: 'PrefixedIDBDatabaseConstructor',
  365: 'PrefixedIDBFactoryConstructor',
  366: 'PrefixedIDBIndexConstructor',
  367: 'PrefixedIDBKeyRangeConstructor',
  368: 'PrefixedIDBObjectStoreConstructor',
  369: 'PrefixedIDBRequestConstructor',
  370: 'PrefixedIDBTransactionConstructor',
  371: 'NotificationPermission',
  372: 'RangeDetach',
  373: 'DocumentImportNodeOptionalArgument',
  374: 'HTMLTableElementVspace',
  375: 'HTMLTableElementHspace',
  376: 'PrefixedDocumentExitPointerLock',
  377: 'PrefixedDocumentPointerLockElement',
  378: 'PrefixedTouchRadiusX',
  379: 'PrefixedTouchRadiusY',
  380: 'PrefixedTouchRotationAngle',
  381: 'PrefixedTouchForce',
  382: 'PrefixedMouseEventMovementX',
  383: 'PrefixedMouseEventMovementY',
  384: 'PrefixedWheelEventDirectionInvertedFromDevice',
  385: 'PrefixedWheelEventInit',
  386: 'PrefixedFileRelativePath',
  387: 'DocumentCaretRangeFromPoint',
  388: 'DocumentGetCSSCanvasContext',
  389: 'ElementScrollIntoViewIfNeeded',
  390: 'ElementScrollByLines',
  391: 'ElementScrollByPages',
  392: 'RangeCompareNode',
  393: 'RangeExpand',
  394: 'HTMLFrameElementWidth',
  395: 'HTMLFrameElementHeight',
  396: 'HTMLImageElementX',
  397: 'HTMLImageElementY',
  398: 'HTMLOptionsCollectionRemoveElement',
  399: 'HTMLPreElementWrap',
  400: 'SelectionBaseNode',
  401: 'SelectionBaseOffset',
  402: 'SelectionExtentNode',
  403: 'SelectionExtentOffset',
  404: 'SelectionType',
  405: 'SelectionModify',
  406: 'SelectionSetBaseAndExtent',
  407: 'SelectionEmpty',
  408: 'SVGFEMorphologyElementSetRadius',
  409: 'VTTCue',
  410: 'VTTCueRender',
  411: 'VTTCueRenderVertical',
  412: 'VTTCueRenderSnapToLinesFalse',
  413: 'VTTCueRenderLineNotAuto',
  414: 'VTTCueRenderPositionNot50',
  415: 'VTTCueRenderSizeNot100',
  416: 'VTTCueRenderAlignNotMiddle',
  417: 'ElementRequestPointerLock',
  418: 'VTTCueRenderRtl',
}

########NEW FILE########
__FILENAME__ = users
# -*- coding: utf-8 -*-
# Copyright 2013 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License")
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

__author__ = 'ericbidelman@chromium.org (Eric Bidelman)'


#import datetime
import json
import logging
import os
import webapp2

# App Engine imports.
from google.appengine.api import users
from google.appengine.ext import db

import common
import models
import settings


class UserHandler(common.ContentHandler):

  def get(self, path):
    # Remove trailing slash from URL and redirect. e.g. /users/ -> /users
    if path[-1] == '/':
      return self.redirect(self.request.path.rstrip('/'))

    users = models.AppUser.all().fetch(None) # TODO(ericbidelman): memcache this.

    user_list = [user.format_for_template() for user in users]

    template_data = {
      'users': json.dumps(user_list)
    }

    self.render(data=template_data, template_path=os.path.join(path + '.html'))

  def post(self, path, user_id=None):
    if user_id:
      self._delete(user_id)
      self.redirect('/admin/users/new')
      return

    email = self.request.get('email')

    # Don't add a duplicate email address.
    user = models.AppUser.all(keys_only=True).filter('email = ', email).get()
    if not user:
      user = models.AppUser(email=db.Email(email))
      user.put()

      self.response.set_status(201, message='Created user')
      self.response.headers['Content-Type'] = 'application/json;charset=utf-8'
      return self.response.write(json.dumps(user.format_for_template()))
    else:
      self.response.set_status(200, message='User already exists')
      self.response.write(json.dumps({'id': user.id()}))

  def _delete(self, user_id):
    if user_id:
      found_user = models.AppUser.get_by_id(long(user_id))
      if found_user:
        found_user.delete()


app = webapp2.WSGIApplication([
  ('/(.*)/([0-9]*)', UserHandler),
  ('/(.*)', UserHandler),
], debug=settings.DEBUG)


########NEW FILE########
