__FILENAME__ = api
import collections
import json
import logging
import re
import urllib
import urllib2

import base.cache
import base.paths
import base.url_fetcher

FEED_STREAM_ID_PREFIX = 'feed/'
EXPLORE_STREAM_ID = 'pop/topic/top/language/en'

_ITEM_ID_ATOM_FORM_PREFIX = 'tag:google.com,2005:reader/item/'

# The explore stream lists a bunch of item IDs that can't be found, ignore them
# instead of worrying people.
not_found_items_ids_to_ignore = set()

class Api(object):
  def __init__(self,
      authenticated_url_fetcher, http_retry_count=None, cache_directory=None):
    self._direct_url_fetcher = base.url_fetcher.DirectUrlFetcher()
    self._authenticated_url_fetcher = authenticated_url_fetcher
    if http_retry_count > 1:
      self._direct_url_fetcher = base.url_fetcher.RetryingUrlFetcher(
          http_retry_count, self._direct_url_fetcher)
      self._authenticated_url_fetcher = base.url_fetcher.RetryingUrlFetcher(
          http_retry_count, self._authenticated_url_fetcher)

    self._cache = \
      base.cache.DirectoryCache(cache_directory) if cache_directory else None

  def fetch_user_info(self):
    user_info_json = self._fetch_json('user-info')
    return UserInfo(
      user_id=user_info_json['userId'],
      email=user_info_json['userEmail'],
      profile_id=user_info_json['userProfileId'],
      user_name=user_info_json['userName'],
      public_user_name=user_info_json.get('publicUserName'),
      is_blogger_user=user_info_json['isBloggerUser'],
      signup_time_sec=user_info_json['signupTimeSec'],
      is_multi_login_enabled=user_info_json['isMultiLoginEnabled'])

  def fetch_tags(self):
    tags_json = self._fetch_json('tag/list')
    result = []
    for tag_json in tags_json['tags']:
      result.append(Tag(
        stream_id=tag_json['id'],
        sort_id=tag_json['sortid']
      ))
    return result

  def fetch_subscriptions(self):
    subscriptions_json = self._fetch_json('subscription/list')
    result = []
    for subscription_json in subscriptions_json['subscriptions']:
      insert_stream_ids = []
      for category_json in subscription_json.get('categories', []):
        insert_stream_ids.append(category_json['id'])
      result.append(Subscription(
        stream_id=subscription_json['id'],
        sort_id=subscription_json['sortid'],
        title=subscription_json.get('title'),
        first_item_usec=int(subscription_json.get('firstitemmsec', 0)) * 1000,
        html_url=subscription_json.get('htmlUrl'),
        insert_stream_ids=insert_stream_ids,
      ))
    return result

  def fetch_friends(self):
    friends_json = self._fetch_json('friend/list', {'lookup': 'ALL'})
    result = []
    for friend_json in friends_json['friends']:
      flags = friend_json.get('flags', 0)
      types = friend_json.get('types', [])
      websites=[
        Website(w['title'], w['url']) for w in friend_json.get('websites', [])]
      result.append(Friend(
        stream_id=friend_json.get('stream'),

        user_ids=friend_json.get('userIds', []),
        profile_ids=friend_json.get('profileIds', []),
        contact_id=friend_json['contactId'],
        group_ids=friend_json.get('groupIds', []),

        display_name=friend_json['displayName'],
        given_name=friend_json['givenName'],
        occupation=friend_json.get('occupation'),
        websites=websites,
        location=friend_json.get('location'),
        photo_url=friend_json.get('photoUrl'),
        email_addresses=friend_json.get('emailAddresses', []),

        is_current_user= flags & 1 << 0 != 0,
        is_hidden=       flags & 1 << 1 != 0,
        is_new=          flags & 1 << 2 != 0,
        uses_reader=     flags & 1 << 3 != 0,
        is_blocked=      flags & 1 << 4 != 0,
        has_profile=     flags & 1 << 5 != 0,
        is_ignored=      flags & 1 << 6 != 0,
        is_new_follower= flags & 1 << 7 != 0,
        is_anonymous=    flags & 1 << 8 != 0,
        has_shared_items=flags & 1 << 9 != 0,

        is_follower=          0 in types,
        is_following=         1 in types,
        is_contact=           3 in types,
        is_pending_following= 4 in types,
        is_pending_follower=  5 in types,
        is_allowed_following= 6 in types,
        is_allowed_commenting=7 in types,
      ))
    return result

  def fetch_encoded_sharers(self):
    friends_json = self._fetch_json('friend/list', {'lookup': 'ALL'})
    return friends_json.get('encodedSharersList', '')

  def fetch_sharing_groups(self):
    sharing_groups_json = self._fetch_json('friend/groups')
    result = []
    for sharing_group_json in sharing_groups_json['sharingGroups']:
      result.append(SharingGroup(
        group_id=sharing_group_json['groupId'],
        is_read_only=sharing_group_json['isReadOnly'],
        name=sharing_group_json['name'],
        is_sharing=sharing_group_json['isSharing'],
      ))
    return result

  def fetch_sharing_acl(self):
    sharing_acl_json = self._fetch_json('friend/acl')
    return SharingAcl(
        type=sharing_acl_json['type'],
        member_user_ids=sharing_acl_json['memberId'],
        is_editing_disabled=sharing_acl_json['isEditingDisabled'])

  def fetch_bundles(self):
    bundles_json = self._fetch_json('list-user-bundle')
    result = []
    for bundle_json in bundles_json['bundles']:
      feeds = []
      for feed_json in bundle_json['feeds']:
        feeds.append(BundleFeed(
            stream_id=feed_json['id'], title=feed_json['title']))
      result.append(Bundle(
        bundle_id=bundle_json['id'],
        title=bundle_json['title'],
        description=bundle_json.get('description'),
        subscriber_count=bundle_json['subscriberCount'],
        feeds=feeds))
    return result

  def fetch_recommendations(self, count=20):
    recommendations_json = self._fetch_json(
        'recommendation/list', {'n': count})
    result = []
    for recommendation_json in recommendations_json['recs']:
      result.append(Recommendation(
          stream_id=recommendation_json['streamId'],
          title=recommendation_json['title']))
    return result

  def fetch_preferences(self):
    prefs_json = self._fetch_json('preference/list')
    result = {}
    for pref_json in prefs_json['prefs']:
      result[pref_json['id']] = pref_json['value']
    return result

  def fetch_stream_preferences(self):
    prefs_json = self._fetch_json('preference/stream/list')
    result = {}
    for stream_id, stream_prefs_json in prefs_json['streamprefs'].iteritems():
      stream_prefs = {}
      for pref_json in stream_prefs_json:
        stream_prefs[pref_json['id']] = pref_json['value']
      result[stream_id] = stream_prefs
    return result

  def fetch_item_refs(self, stream_id, count=10, continuation_token=None):
    query_params = {'s': stream_id, 'n': count}
    if continuation_token:
      query_params['c'] = continuation_token
    item_refs_json = self._fetch_json(
        'stream/items/ids',
        query_params,
        authenticated=not stream_id.startswith(FEED_STREAM_ID_PREFIX))
    result = []
    for item_ref_json in item_refs_json['itemRefs']:
      result.append(ItemRef(
        item_id=item_id_from_decimal_form(item_ref_json['id']),
        timestamp_usec=int(item_ref_json['timestampUsec'])
      ))
    return result, item_refs_json.get('continuation')

  def fetch_comments(
      self, stream_id, encoded_sharers, count=10, continuation_token=None):
    query_params = {
      'comments': 'true',
      'sharers': encoded_sharers,
      'n': count,
    }
    if continuation_token:
      query_params['c'] = continuation_token
    stream_contents_json = self._fetch_json(
        'stream/contents/%s' % urllib.quote(stream_id),
        query_params)
    result = {}
    for item_json in stream_contents_json['items']:
      comments_json = item_json.get('comments', [])
      if not comments_json:
          continue
      item_id = item_id_from_atom_form(item_json['id'])
      comments = []
      for comment_json in comments_json:
        comments.append(Comment(
          comment_id=comment_json['id'],
          plain_content=comment_json['plainContent'],
          html_content=comment_json['htmlContent'],
          author_name=comment_json.get('author'),
          author_user_id=comment_json['userId'],
          author_profile_id=comment_json['profileId'],
          venue_stream_id=comment_json['venueStreamId'],
          created_time_usec=comment_json['createdTime'] * 1000000,
          modified_time_usec=comment_json['modifiedTime'] * 1000000,
          is_spam=comment_json['isSpam'],
        ))
      result[item_id] = comments
    return result, stream_contents_json.get('continuation')

  def fetch_item_bodies(
      self, item_ids, format='json', media_rss=False, authenticated=True):
    query_params = {
        'output': format,
        # Don't render annotations inline (so that the item body is left alone).
        # Instead we'll parse them from the <gr:annotation> namespaced entry.
        'ann': 'false',
        # Likes are public data, and thus work even if we don't use
        # authentication.
        'likes': 'true',
      }
    if media_rss:
      query_params['mediaRss'] = 'true'
    post_params = {'i': [i.decimal_form for i in item_ids]}

    result_text = self._fetch(
        'stream/items/contents',
        query_params,
        post_params,
        authenticated=authenticated)

    result = {}
    if format.startswith('atom'):
      feed = base.atom.parse(result_text)
      for entry in feed.entries:
        result[entry.item_id] = entry
    else:
      item_bodies_json = json.loads(result_text)
      for item_body_json in item_bodies_json['items']:
        # TODO: parse the JSON
        item_id = item_id_from_atom_form(item_body_json['id'])
        result[item_id] = item_body_json

    for item_id in item_ids:
      if item_id not in result and item_id not in not_found_items_ids_to_ignore:
        logging.warning(
            'Requested item id %s (%s), but it was not found in the result',
            item_id.atom_form, item_id.decimal_form)

    return result

  def _fetch_json(
      self,
      api_path,
      query_params={},
      post_params={},
      authenticated=True):
    query_params = dict(query_params)
    query_params['output'] = 'json'
    response_text = self._fetch(
        api_path, query_params, post_params, authenticated)
    return json.loads(response_text)

  def _fetch(self,
      api_path,
      query_params={},
      post_params={},
      authenticated=True):
    url = 'https://www.google.com/reader/api/0/%s' % api_path

    if self._cache:
      cache_key = base.paths.url_to_file_name(url, query_params, post_params)
      cache_value = self._cache.get(cache_key)
      if cache_value:
        return cache_value

    def urlencode(params):
      def encode(s):
        return isinstance(s, unicode) and s.encode('utf-8') or s

      encoded_params = {}
      for key, value in params.items():
        if isinstance(value, list):
          value = [encode(v) for v in value]
        else:
          value = encode(value)
        encoded_params[encode(key)] = value
      return urllib.urlencode(encoded_params, doseq=True)

    request_url = '%s?%s' % (url, urlencode(query_params))
    url_fetcher = self._authenticated_url_fetcher if authenticated \
        else self._direct_url_fetcher
    response_text = url_fetcher.fetch(
        request_url,
        post_data=urlencode(post_params) if post_params else None)
    if self._cache:
      self._cache.set(cache_key, response_text)
    return response_text

class Tag(collections.namedtuple('Tag', ['stream_id', 'sort_id'])):
  def to_json(self):
    return self._asdict()

  @staticmethod
  def from_json(tag_json):
    return Tag(**tag_json)

class Subscription(collections.namedtuple(
    'Subscription',
    ['stream_id', 'title', 'sort_id', 'first_item_usec', 'html_url',
    'insert_stream_ids'])):
  def to_json(self):
    return self._asdict()

  @staticmethod
  def from_json(subscription_json):
    return Subscription(**subscription_json)

class Friend(collections.namedtuple(
    'Friend',
    [
      # Shared items stream
      'stream_id',

      # Ids
      'user_ids', 'profile_ids', 'contact_id', 'group_ids',

      # Profile data
      'display_name', 'given_name', 'occupation', 'websites', 'location',
      'photo_url', 'email_addresses',

      # Flags
      'is_current_user', # Represents the requesting user.
      'is_hidden', # User has hidden this person from the broadcast-friends stream.
      'is_new', # Person is a new addition to the user's list of followed people.
      'uses_reader', # Person uses reader
      'is_blocked', # User has blocked this person.
      'has_profile', #  Person has created a Google Profile
      'is_ignored', # Person has requested to follow the user, but the user has ignored the request.
      'is_new_follower', # Person has just begun to follow the user.
      'is_anonymous', # Person doesn't have a display name set.
      'has_shared_items', # Person has shared items in reader

      'is_follower', # Person is following the user.
      'is_following', # The user is following this person.
      'is_contact', # This person is in the user's contacts list.
      'is_pending_following', # The user is attempting to follow this person.
      'is_pending_follower', # This person is attempting to follow this user.
      'is_allowed_following', # The user is allowed to follow this person.
      'is_allowed_commenting', # The user is allowed to comment on this person's shared items
    ])):
  def to_json(self):
    result = self._asdict()
    result['websites'] = [w.to_json() for w in self.websites]
    return result

  @staticmethod
  def from_json(friend_json):
    return Friend(**friend_json)


class Website(collections.namedtuple('Website', ['title', 'url'])):
  def to_json(self):
    return self._asdict()

class SharingGroup(collections.namedtuple('SharingGroup',
    ['group_id', 'is_read_only', 'name', 'is_sharing'])):
  def to_json(self):
    return self._asdict()

class SharingAcl(collections.namedtuple('SharingAcl',
    ['type', 'member_user_ids', 'is_editing_disabled'])):
  def to_json(self):
    return self._asdict()

class Bundle(collections.namedtuple('Bundle',
    ['bundle_id', 'title', 'description', 'subscriber_count', 'feeds'])):
  def to_json(self):
    result = self._asdict()
    result['feeds'] = [f.to_json() for f in self.feeds]
    return result

class BundleFeed(collections.namedtuple('BundleFeed', ['stream_id', 'title'])):
  def to_json(self):
    return self._asdict()

class Recommendation(collections.namedtuple('Recommendation',
    ['stream_id', 'title'])):
  def to_json(self):
    return self._asdict()

  @staticmethod
  def from_json(recommendation_json):
    return Recommendation(**recommendation_json)

class Comment(collections.namedtuple(
    'Comment',
    [
      'comment_id',
      'plain_content',
      'html_content',
      'author_name',
      'author_user_id',
      'author_profile_id',
      'venue_stream_id',
      'created_time_usec',
      'modified_time_usec',
      'is_spam',
    ])):
  def to_json(self):
    return self._asdict()

  @staticmethod
  def from_json(comment_json):
    return Comment(**comment_json)

class UserInfo(collections.namedtuple(
    'UserInfo',
    [
      'user_id',
      'email',
      'profile_id',
      'user_name',
      'public_user_name',
      'is_blogger_user',
      'signup_time_sec',
      'is_multi_login_enabled'
    ])):
  def to_json(self):
    return self._asdict()

  @staticmethod
  def from_json(user_info_json):
    return UserInfo(**user_info_json)

class ItemRef(collections.namedtuple('ItemRef', ['item_id', 'timestamp_usec'])):
  def to_json(self):
    return {
      'item_id': self.item_id.to_json(),
      'timestamp_usec': self.timestamp_usec,
    }

class Stream(collections.namedtuple('Stream', ['stream_id', 'item_refs'])):
  def to_json(self):
    return {
      'stream_id': self.stream_id,
      'item_refs': {
        item_ref.item_id.to_json() : item_ref.timestamp_usec
            for item_ref in self.item_refs
      },
    }

  @staticmethod
  def from_json(stream_json):
    item_refs = [
      ItemRef(
          item_id=ItemId.from_json(item_id_json),
          timestamp_usec=timestamp_usec
      ) for item_id_json, timestamp_usec
      in stream_json['item_refs'].iteritems()
    ]
    item_refs = sorted(item_refs, key=lambda i: i.timestamp_usec, reverse=True)
    return Stream(stream_id=stream_json['stream_id'], item_refs=item_refs)

class ItemId(collections.namedtuple('ItemId', ['int_form'])):
  def to_json(self):
    return self.compact_form()

  def compact_form(self):
    compact_form = hex(self.int_form)[2:]
    if compact_form.endswith('L'):
      compact_form = compact_form[:-1]
    compact_form = (16 - len(compact_form)) * '0' + compact_form
    return compact_form

  # See https://code.google.com/p/google-reader-api/wiki/ItemId for the two forms
  # item IDs.
  @property
  def decimal_form(self):
    if self.int_form > 1 << 63:
      return str(self.int_form - (1 << 64))
    else:
      return str(self.int_form)

  @property
  def atom_form(self):
    return _ITEM_ID_ATOM_FORM_PREFIX + self.compact_form()

  @staticmethod
  def from_json(item_id_json):
    return item_id_from_compact_form(item_id_json)

def item_id_from_decimal_form(decimal_form):
  int_form = int(decimal_form)
  if int_form < 0:
    int_form += 1 << 64
  return ItemId(int_form=int_form)

def item_id_from_atom_form(atom_form):
  return item_id_from_compact_form(atom_form[len(_ITEM_ID_ATOM_FORM_PREFIX):])

def item_id_from_compact_form(compact_form):
  return ItemId(int_form=int(compact_form, 16))

def item_id_from_any_form(form):
  if form.startswith(_ITEM_ID_ATOM_FORM_PREFIX):
    return item_id_from_atom_form(form)

  if form.startswith('0x'):
    return item_id_from_compact_form(form[2:])

  if re.match('^[0-9a-f]+$', form, re.I):
    return item_id_from_compact_form(form)

  if re.match('^-?[0-9]+$', form):
    return item_id_from_decimal_form(form)

  return None

_TEST_DATA = [
  ('tag:google.com,2005:reader/item/5d0cfa30041d4348', '6705009029382226760'),
  ('tag:google.com,2005:reader/item/024025978b5e50d2', '162170919393841362'),
  ('tag:google.com,2005:reader/item/fb115bd6d34a8e9f', '-355401917359550817'),
]

def _test_ids():
  for atom_form, decimal_form in _TEST_DATA:
    item_id = item_id_from_decimal_form(decimal_form)
    assert item_id.atom_form == atom_form, \
        '%s != %s' % (item_id.atom_form, atom_form)
    item_id = item_id_from_atom_form(atom_form)
    assert item_id.decimal_form == decimal_form, \
        '%s != %s' % (item_id.decimal_form, decimal_form)

########NEW FILE########
__FILENAME__ = atom
import calendar
import collections
import logging
import os.path
import re
import time
import xml.etree.cElementTree as ET

import base.api

ATOM_NS = 'http://www.w3.org/2005/Atom'
READER_NS = 'http://www.google.com/schemas/reader/atom/'

_HTML_TAG_RE = re.compile('<[^<]+?>')

def init():
  ET.register_namespace('gr', READER_NS)
  ET.register_namespace('atom', ATOM_NS)
  ET.register_namespace('coop', 'http://www.google.com/coop/namespace')
  ET.register_namespace('gd', 'http://schemas.google.com/g/2005')
  ET.register_namespace('idx', 'urn:atom-extension:indexing')
  ET.register_namespace('media', 'http://search.yahoo.com/mrss/')
  ET.register_namespace('thr', 'http://purl.org/syndication/thread/1.0')

def parse(xml_text_or_file):
  if hasattr(xml_text_or_file, 'read'):
    feed_element = ET.parse(xml_text_or_file)
  else:
    feed_element = ET.fromstring(xml_text_or_file)
  entry_elements = feed_element.findall('{%s}entry' % ATOM_NS)
  entries = []
  for entry_element in entry_elements:
    item_id = base.api.item_id_from_atom_form(
        entry_element.find('{%s}id' % ATOM_NS).text)
    title = entry_element.find('{%s}title' % ATOM_NS).text

    content_element = entry_element.find('{%s}content' % ATOM_NS)
    if content_element is None:
      content_element = entry_element.find('{%s}summary' % ATOM_NS)
    content = content_element.text if content_element is not None else ''
    content = content.replace(
        'http://reader.googleusercontent.com/reader/embediframe',
        '/reader/embediframe')

    source_element = entry_element.find('{%s}source' % ATOM_NS)
    source_link_element = source_element.find('{%s}link' % ATOM_NS)
    origin_html_url = source_link_element.attrib['href'] \
        if source_link_element is not None else None
    origin = Origin(
      stream_id=source_element.attrib['{%s}stream-id' % READER_NS],
      title=source_element.find('{%s}title' % ATOM_NS).text,
      html_url=origin_html_url,
    )

    author_name = None
    author_element = entry_element.find('{%s}author' % ATOM_NS)
    if author_element is not None and \
        '{%s}unknown-author' % READER_NS not in author_element.attrib:
      author_name_element = author_element.find('{%s}name' % ATOM_NS)
      if author_name_element is not None:
        author_name = author_name_element.text

    links = []
    link_elements = entry_element.findall('{%s}link' % ATOM_NS)
    for link_element in link_elements:
      a = link_element.attrib
      links.append(Link(
         relation=a.get('rel'),
         href=a.get('href'),
         type=a.get('type'),
         title=a.get('title'),
         length=a.get('length'),
      ))

    # Dates
    crawl_time_msec = int(
        entry_element.attrib['{%s}crawl-timestamp-msec' % READER_NS])
    def parse_iso_8601(s):
      return int(calendar.timegm(time.strptime(s, '%Y-%m-%dT%H:%M:%SZ')))
    published_element = entry_element.find('{%s}published' % ATOM_NS)
    published_sec = parse_iso_8601(published_element.text) \
        if published_element is not None else crawl_time_msec/1000
    updated_element = entry_element.find('{%s}updated' % ATOM_NS)
    updated_sec = parse_iso_8601(updated_element.text) \
        if updated_element is not None else crawl_time_msec/1000

    annotations = []
    annotation_elements = entry_element.findall('{%s}annotation' % READER_NS)
    for annotation_element in annotation_elements:
      content_element = annotation_element.find('{%s}content' % ATOM_NS)
      author_element = annotation_element.find('{%s}author' % ATOM_NS)
      author_name_element = author_element.find('{%s}name' % ATOM_NS)
      author_attrib = author_element.attrib
      annotations.append(Annotation(
        content=content_element.text,
        author_name=author_name_element.text,
        author_user_id=author_attrib['{%s}user-id' % READER_NS],
        author_profile_id=author_attrib['{%s}profile-id' % READER_NS],
      ))

    entries.append(Entry(
      item_id=item_id,
      title=title,
      content=content,
      element=entry_element,
      origin=origin,
      links=links,
      crawl_time_msec=crawl_time_msec,
      published_sec=published_sec,
      updated_sec=updated_sec,
      annotations=annotations,
      author_name=author_name,
    ))
  return Feed(entries=entries)

def load_item_entry(archive_directory, item_id):
  item_body_path = base.paths.item_id_to_file_path(
      os.path.join(archive_directory, 'items'), item_id)
  if os.path.exists(item_body_path):
    with open(item_body_path) as item_body_file:
      try:
        feed = base.atom.parse(item_body_file)
      except ET.ParseError as e:
        logging.warning('Could not parse file %s to load item entry %s',
            item_body_path, item_id)
        return None
      for entry in feed.entries:
        if entry.item_id == item_id:
          return entry
    logging.warning('Did not find item entry for %s', item_id)
  else:
    logging.warning('No item body file entry for %s', item_id)

  return None

Feed = collections.namedtuple('Feed', ['entries'])

class Entry(collections.namedtuple('Entry', [
    # Extracted attributes
    'item_id',
    'title',
    'content',
    'origin',
    'links',
    'crawl_time_msec',
    'published_sec',
    'updated_sec',
    'annotations',
    'author_name',

    # ElementTree element
    'element'])):

  @property
  def content_snippet(self):
    snippet = self.content
    snippet = _HTML_TAG_RE.sub('', snippet)
    if len(snippet) > 256:
      snippet = snippet[:256] + '&hellip;'
    return snippet

Origin = collections.namedtuple('Origin', ['stream_id', 'title', 'html_url'])

Link = collections.namedtuple('Link',
    ['relation', 'href', 'type', 'title', 'length'])

Annotation = collections.namedtuple('Annotation',
    ['content', 'author_name', 'author_user_id', 'author_profile_id'])

########NEW FILE########
__FILENAME__ = cache
import os
import os.path

import base.paths

class DirectoryCache(object):
  def __init__(self, directory):
    self._directory = directory
    base.paths.ensure_exists(directory)

  def get(self, key):
    path = self._path(key)
    if not os.path.exists(path):
      return None
    with open(path, "r") as file:
      return file.read()

  def set(self, key, value):
    with open(self._path(key), "w") as file:
      file.write(value)

  def _path(self, key):
    return os.path.join(self._directory, key)

########NEW FILE########
__FILENAME__ = log
import logging
import sys
import time

try:
    import curses
except ImportError:
    curses = None

def _stderr_supports_color():
    color = False
    if curses and sys.stderr.isatty():
        try:
            curses.setupterm()
            if curses.tigetnum("colors") > 0:
                color = True
        except Exception:
            pass
    return color

# From https://github.com/facebook/tornado/blob/master/tornado/log.py

class LogFormatter(logging.Formatter):
    """Log formatter used in Tornado.

    Key features of this formatter are:

    * Color support when logging to a terminal that supports it.
    * Timestamps on every log line.
    * Robust against str/bytes encoding problems.

    This formatter is enabled automatically by
    `tornado.options.parse_command_line` (unless ``--logging=none`` is
    used).
    """
    def __init__(self, color=True, *args, **kwargs):
        logging.Formatter.__init__(self, *args, **kwargs)
        self._color = color and _stderr_supports_color()
        if self._color:
            fg_color = (curses.tigetstr("setaf") or
                        curses.tigetstr("setf") or "")
            self._colors = {
                logging.DEBUG: curses.tparm(fg_color, 4),  # Blue
                logging.INFO: curses.tparm(fg_color, 2),  # Green
                logging.WARNING: curses.tparm(fg_color, 3),  # Yellow
                logging.ERROR: curses.tparm(fg_color, 1),  # Red
                logging.CRITICAL: curses.tparm(fg_color, 5),  # Magenta
            }
            self._normal = curses.tigetstr("sgr0")

    def format(self, record):
        try:
            record.message = record.getMessage()
        except Exception as e:
            record.message = "Bad message (%r): %r" % (e, record.__dict__)
        record.asctime = time.strftime(
            "%y%m%d %H:%M:%S", self.converter(record.created))
        prefix = '[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d]' % \
            record.__dict__
        if self._color:
            prefix = (self._colors.get(record.levelno, self._normal) +
                      prefix + self._normal)

        # Encoding notes:  The logging module prefers to work with character
        # strings, but only enforces that log messages are instances of
        # basestring.  In python 2, non-ascii bytestrings will make
        # their way through the logging framework until they blow up with
        # an unhelpful decoding error (with this formatter it happens
        # when we attach the prefix, but there are other opportunities for
        # exceptions further along in the framework).
        #
        # If a byte string makes it this far, convert it to unicode to
        # ensure it will make it out to the logs.  Use repr() as a fallback
        # to ensure that all byte strings can be converted successfully,
        # but don't do it by default so we don't add extra quotes to ascii
        # bytestrings.  This is a bit of a hacky place to do this, but
        # it's worth it since the encoding errors that would otherwise
        # result are so useless (and tornado is fond of using utf8-encoded
        # byte strings whereever possible).
        def safe_unicode(s):
            try:
                return unicode(s)
            except UnicodeDecodeError:
                return repr(s)

        formatted = prefix + " " + safe_unicode(record.message)
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            # exc_text contains multiple lines.  We need to safe_unicode
            # each line separately so that non-utf8 bytes don't cause
            # all the newlines to turn into '\n'.
            lines = [formatted.rstrip()]
            lines.extend(safe_unicode(ln) for ln in record.exc_text.split('\n'))
            formatted = '\n'.join(lines)
        return formatted.replace("\n", "\n    ")

def init():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    channel = logging.StreamHandler()
    channel.setFormatter(LogFormatter())
    logger.addHandler(channel)

########NEW FILE########
__FILENAME__ = middleware
import logging
import os.path
import posixpath
import time
import urllib

import third_party.web as web

class LogMiddleware:
  """WSGI middleware for logging the HTTP requests. Based on web.httpserver.
  LogMiddleware, but simplified for our needs."""
  def __init__(self, app):
    self._app = app

  def __call__(self, environ, start_response):
    start_time = time.time()
    def logging_start_response(status, response_headers, *args):
        out = start_response(status, response_headers, *args)
        server_time = time.time() - start_time
        self._log(status, server_time, environ)
        return out

    return self._app(environ, logging_start_response)

  def _log(self, status, server_time, environ):
    req = environ.get('PATH_INFO', '_')
    if environ.get('QUERY_STRING'):
      req += '?%s' % environ['QUERY_STRING']
    method = environ.get('REQUEST_METHOD', '-')

    logging.debug('%s %s - %s (%gms)', method, req, status, server_time * 1000)

class StaticMiddleware:
  """WSGI middleware for serving static files. Based on web.httpserver.
  StaticMiddleware, but allows the prefix and on-disk directory to be
  different."""
  def __init__(self, app, url_path_prefix, static_directory):
    self._app = app
    self._url_path_prefix = url_path_prefix
    self._static_directory = static_directory

  def __call__(self, environ, start_response):
    path = environ.get('PATH_INFO', '')
    path = self._normalize_path(path)

    if path.startswith(self._url_path_prefix):
      return _StaticApp(
          environ,
          start_response,
          self._url_path_prefix,
          self._static_directory)
    else:
      return self._app(environ, start_response)

  def _normalize_path(self, path):
    normalized_path = posixpath.normpath(urllib.unquote(path))
    if path.endswith("/"):
      normalized_path += "/"
    return normalized_path

class _StaticApp(web.httpserver.StaticApp):
  def __init__(
        self, environ, start_response, url_path_prefix, static_directory):
    web.httpserver.StaticApp.__init__(self, environ, start_response)
    self._url_path_prefix = url_path_prefix
    self._static_directory = static_directory

  def translate_path(self, path):
    static_file_path = os.path.abspath(os.path.join(
        self._static_directory, path[len(self._url_path_prefix):]))
    if static_file_path.startswith(self._static_directory):
      return static_file_path

    return None

########NEW FILE########
__FILENAME__ = paths
import base64
import hashlib
import os.path
import re

import base.api

def ensure_exists(directory_path):
  if os.path.exists(directory_path):
    return
  os.makedirs(directory_path)

def normalize(path):
  return os.path.abspath(os.path.expanduser(path))

_ESCAPE_CHARACTERS_RE = re.compile(r'([/:?&]+|%20)')
_STREAM_ID_DISALLOWED_CHARACTERS_RE = re.compile(r'([^A-Za-z0-9\-._/ :?&]+)')
_TRIM_TRAILING_DASHES_RE = re.compile(r'-+$')

def url_to_file_name(url, query_params=None, post_params=None):
  file_name = url
  if file_name.startswith('http://'):
    file_name = file_name[7:]
  if file_name.startswith('https://'):
    file_name = file_name[8:]
  file_name = _ESCAPE_CHARACTERS_RE.sub('-', file_name)
  file_name = _TRIM_TRAILING_DASHES_RE.sub('', file_name)

  signature_data = []

  if len(file_name) > 64:
    signature_data.append(file_name[64:])
    file_name = file_name[:64]
  if query_params:
    signature_data.append(str(query_params))
  if post_params:
    signature_data.append(str(post_params))

  if signature_data:
    signature = hashlib.md5('-'.join(signature_data)).digest()
    signature = base64.urlsafe_b64encode(signature)
    signature = re.sub(r'=+$', '', signature)
    file_name += '-' + signature

  return file_name

def stream_id_to_file_name(stream_id):
  if stream_id.startswith(base.api.FEED_STREAM_ID_PREFIX):
    feed_url = stream_id[len(base.api.FEED_STREAM_ID_PREFIX):]
    if "?" in feed_url:
      feed_url, query_params = feed_url.split("?", 1)
    else:
      query_params = None
    return "%s-%s" % (url_to_file_name(base.api.FEED_STREAM_ID_PREFIX),
      url_to_file_name(feed_url, query_params))

  # Replace non-ASCII characters with dashes, but keep track of them, so that a
  # unique filename can still be generated for each
  disallowed_character_data = []
  for d in _STREAM_ID_DISALLOWED_CHARACTERS_RE.findall(stream_id):
    disallowed_character_data.append(d)
  stream_id = _STREAM_ID_DISALLOWED_CHARACTERS_RE.sub('-', stream_id)
  return url_to_file_name(stream_id, query_params=disallowed_character_data)


def item_id_to_file_path(items_directory, item_id):
  item_file_name = item_id.compact_form()
  # Keep number of files per directory reasonable.
  return os.path.join(
      items_directory, item_file_name[0:2], item_file_name[2:4])

########NEW FILE########
__FILENAME__ = tag_helper
import base.api

class TagHelper(object):
  def __init__(self, user_id):
    self._user_id = user_id

  def system_tags(self):
    return [
      # Item state tags
      self.state_tag('broadcast'),
      self.state_tag('starred'),
      self.state_tag('like'),
      self.state_tag('dislike'),
      self.state_tag('read'),
      self.state_tag('kept-unread'),
      self.state_tag('muted'),
      self.state_tag('skimmed'),
      self.state_tag('itemrecs/en'),
      self.state_tag('tracking-body-link-used'),
      self.state_tag('tracking-emailed'),
      self.state_tag('tracking-item-link-used'),
      self.state_tag('tracking-kept-unread'),
      self.state_tag('tracking-custom-item-link'),
      self.state_tag('tracking-mobile-read'),
      self.state_tag('tracking-explore-read'),
      self.state_tag('tracking-igoogle-module-read'),

      # Note-in-Reader
      self._source_tag('post'),
      self._source_tag('link'),
      self.state_tag('created'),

      # Subscription level tags
      self.state_tag('reading-list'),
      self.state_tag('broadcast-friends'),
      self._user_tag('state', 'com.blogger', 'blogger-following'),
    ]

  def state_tag(self, state):
    return self._internal_tag('state', state)

  def _source_tag(self, source):
    return self._internal_tag('source', source)

  def _internal_tag(self, type, name):
    return self._user_tag(type, 'com.google', name)

  def _user_tag(self, *args):
    return base.api.Tag(
        stream_id='user/%s/%s' % (self._user_id, '/'.join(args)),
        sort_id=None)


########NEW FILE########
__FILENAME__ = url_fetcher
import getpass
import json
import logging
import sys
import time
import urllib
import urllib2
import webbrowser

class UrlFetcher(object):
  def fetch(self, url, post_data=None):
    raise NotImplementedError()

class RetryingUrlFetcher(UrlFetcher):
  def __init__(self, retry_count, url_fetcher):
    self._retry_count = retry_count
    self._url_fetcher = url_fetcher

  def fetch(self, url, post_data=None):
    for i in xrange(0, self._retry_count):
      try:
        return self._url_fetcher.fetch(url, post_data)
      except urllib2.URLError as e:
        if i == self._retry_count - 1:
          raise
        else:
          logging.info("Ignoring URL error %s, %d retries remaining.",
              e, self._retry_count - i - 1)

class DirectUrlFetcher(UrlFetcher):
  def fetch(self, url, post_data=None):
    request = urllib2.Request(url)
    response = urllib2.urlopen(request, data=post_data)
    response_text = response.read()
    response.close()
    return response_text

class ClientLoginUrlFetcher(UrlFetcher):
  def __init__(self, account, password):
    account = account or raw_input('Google Account username: ')
    if not account:
      logging.critical("Username was not provided.")
      sys.exit(1)
    password = password or getpass.getpass('Password: ')
    if not password:
      logging.critical("Password was not provided.")
      sys.exit(1)

    self._auth_token = None
    credentials_data = urllib.urlencode({
      'Email': account,
      'Passwd': password,
      'service': 'reader',
      'accountType': 'GOOGLE',
    })
    try:
      auth_response = urllib2.urlopen(
          'https://www.google.com/accounts/ClientLogin', credentials_data)
      for line in auth_response.readlines():
        key, value = line.strip().split('=', 1)
        if key == 'Auth':
          self._auth_token = value
          break
      auth_response.close()
    except urllib2.HTTPError as e:
      logging.error(
          'Error response while fetching authentication token: %s %s',
          e.code, e.message)
    assert self._auth_token

  def fetch(self, url, post_data=None):
    request = urllib2.Request(
        url, headers={'Authorization': 'GoogleLogin auth=%s' % self._auth_token})
    response = urllib2.urlopen(request, data=post_data)
    response_text = response.read()
    response.close()
    return response_text

_OAUTH_CLIENT_ID = '710067677727.apps.googleusercontent.com'
_OAUTH_CLIENT_SECRET = '3152N3ORUhdIgYX4LwCcs9Ix'

class OAuthUrlFetcher(UrlFetcher):
  def __init__(self, refresh_token):
    if refresh_token:
      self._refresh_token = refresh_token
      self._fetch_access_token()
    else:
      self._request_authorization()

  def fetch(self, url, post_data=None):
    if time.time() > self._access_token_expiration_time:
      logging.info("Access token has expired, requesting a new one.")
      self._fetch_access_token()

    request = urllib2.Request(
        url, headers={'Authorization': 'Bearer %s' % self._access_token})
    response = urllib2.urlopen(request, data=post_data)
    response_text = response.read()
    response.close()
    return response_text

  def _request_authorization(self):
    query_params = {
      'response_type': 'code',
      'client_id': _OAUTH_CLIENT_ID,
      'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
      'scope': 'https://www.google.com/reader/api'
    }
    initial_url = 'https://accounts.google.com/o/oauth2/auth?%s' % \
        urllib.urlencode(query_params)

    logging.info("Opening the OAuth authorization page...")
    logging.info("If you do not see a browser tab appear, you should open the "
        "following URL:\n%s\n", initial_url)
    webbrowser.open_new_tab(initial_url)

    logging.info("Once you complete the approval, you will be given a code. "
        "Please copy and paste it below and press return.")
    authorization_code = raw_input('Authorization code: ')
    if not authorization_code:
      logging.critical("Authorization code was not provided.")
      sys.exit(1)

    token_request = \
        urllib2.Request('https://accounts.google.com/o/oauth2/token')
    token_response = urllib2.urlopen(token_request, data=urllib.urlencode({
      'code': authorization_code,
      'client_id': _OAUTH_CLIENT_ID,
      'client_secret': _OAUTH_CLIENT_SECRET,
      'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
      'grant_type': 'authorization_code',
    }))

    token_response_json = json.load(token_response)
    token_response.close()

    self._refresh_token = token_response_json['refresh_token']
    self._access_token = token_response_json['access_token']
    self._access_token_expiration_time = \
        time.time() + token_response_json['expires_in'] - 60

    logging.info('If you\'d like to use the tool again without having to go '
        'through OAuth authorization, you can add the following flag to the '
        'invocation:\n\n  --oauth_refresh_token="%s"', self._refresh_token)

  def _fetch_access_token(self):
    token_request = \
        urllib2.Request('https://accounts.google.com/o/oauth2/token')
    token_response = urllib2.urlopen(token_request, data=urllib.urlencode({
      'refresh_token': self._refresh_token,
      'client_id': _OAUTH_CLIENT_ID,
      'client_secret': _OAUTH_CLIENT_SECRET,
      'grant_type': 'refresh_token',
    }))

    token_response_json = json.load(token_response)
    token_response.close()

    self._access_token = token_response_json['access_token']
    self._access_token_expiration_time = \
        time.time() + token_response_json['expires_in'] - 60


########NEW FILE########
__FILENAME__ = worker
import logging
import threading
import Queue

def do_work(worker_creator, requests, parallelism, report_progress=None):
  request_queue = Queue.Queue()
  response_queue = Queue.Queue()
  for i in xrange(parallelism):
    thread = WorkerThread(request_queue, response_queue, worker_creator())
    thread.start()

  for request_index, request in enumerate(requests):
    request_queue.put((request, request_index, False))

  responses = [None] * len(requests)
  for i in xrange(len(requests)):
    response, request_index = response_queue.get()
    responses[request_index] = response
    response_queue.task_done()
    if report_progress:
      report_progress(requests[request_index], response)

  for i in xrange(parallelism):
    request_queue.put((None, -1, True))

  return responses

class Worker(object):
  def work(self, request):
    raise NotImplementedError()

class WorkerThread(threading.Thread):
  def __init__(self, request_queue, response_queue, worker):
    threading.Thread.__init__(self)
    self._request_queue = request_queue
    self._response_queue = response_queue
    self._worker = worker
    self.daemon = True
    self._stopped = False

  def run(self):
    while not self._stopped:
      self._service_request()

  def _service_request(self):
      request, request_index, should_stop = self._request_queue.get()
      if should_stop:
        self._stopped = True
        return
      try:
        response = self._worker.work(request)
      except:
        logging.error('Exception when running worker', exc_info=True)
        response = None
      self._request_queue.task_done()
      self._response_queue.put((response, request_index))

########NEW FILE########
__FILENAME__ = feed_archive
import argparse
import datetime
import logging
import os.path
import sys
import urllib
import urllib2
import urlparse
import xml.etree.cElementTree as ET

import base.atom
import base.log
import base.paths
import base.url_fetcher
import base.worker

_BASE_PARAMETERS = {
  'client': 'reader-feed-archive'
}

_READER_SHARED_TAG_FEED_URL_PATH_PREFIX = '/reader/public/atom/'

def main():
  base.log.init()
  base.atom.init()

  parser = argparse.ArgumentParser(
      description='Fetch archived feed data from Google Reader')
  # Which feeds to fetch data for
  feed_group = parser.add_mutually_exclusive_group()
  feed_group.add_argument('feed_urls', metavar='feed_url', nargs='*',
                          default=[],
                          help='Feed URL to fetch archived data for')
  feed_group.add_argument('--opml_file', default='',
                          help='OPML file listing feed URLs to fetch archived '
                          'data for')

  # Output options
  parser.add_argument('--output_directory', default='./',
                      help='Directory where to place feed archive data. Use '
                            '"-" to output archive data to stdout.')
  # Fetching options
  parser.add_argument('--chunk_size', type=int, default=1000,
                      help='Number of items to request per Google Reader API '
                           'call (higher is more efficient)')
  parser.add_argument('--max_items', type=int, default=0,
                      help='Maxmium number of items to fetch per feed (0 for '
                           'no limit)')
  parser.add_argument('--oldest_item_timestamp_sec', type=int, default=0,
                      help='Timestamp (in seconds since the epoch) of the '
                           'oldest item that should be returned (0 for no '
                           'timestamp restriction)')
  parser.add_argument('--newest_item_timestamp_sec', type=int, default=0,
                      help='Timestamp (in seconds since the epoch) of the '
                           'newest item that should be returned (0 for no '
                           'timestamp restriction)')
  parser.add_argument('--parallelism', type=int, default=10,
                      help='Number of feeds to fetch in parallel.')
  parser.add_argument('--http_retry_count', type=int, default=1,
                      help='Number of retries to make in the case of HTTP '
                           'request errors.')

  args = parser.parse_args()
  if args.opml_file:
    feed_urls = extract_feed_urls_from_opml_file(
      base.paths.normalize(args.opml_file))
  else:
    feed_urls = args.feed_urls
  init_base_parameters(args)
  output_directory = args.output_directory
  if output_directory != '-':
    output_directory = base.paths.normalize(output_directory)
    base.paths.ensure_exists(output_directory)

  url_fetcher = base.url_fetcher.DirectUrlFetcher()
  if args.http_retry_count > 1:
    url_fetcher = base.url_fetcher.RetryingUrlFetcher(
        args.http_retry_count, url_fetcher)

  logging.info('Fetching archived data for %d feed%s',
      len(feed_urls), len(feed_urls) == 1 and '' or 's')

  feed_fetch_requests = []
  for feed_url in feed_urls:
    if output_directory != '-':
      output_path = get_output_path(output_directory, feed_url)
    else:
      output_path = None
    feed_fetch_requests.append(FeedFetchRequest(feed_url, output_path))

  feed_fetch_responses = base.worker.do_work(
      lambda: FeedFetchWorker(url_fetcher, args.max_items),
      feed_fetch_requests,
      args.parallelism)

  success_count = 0
  failures = []

  for response in feed_fetch_responses:
    if response.is_success:
      success_count += 1
    else:
      failures.append(response.feed_url)

  logging.info('Fetched data for %d feeds', success_count)
  if failures:
    logging.warning('Could not fetch %d feeds:', len(failures))
    for feed_url in failures:
      logging.warning('  %s', feed_url)

class FeedFetchWorker(base.worker.Worker):
  def __init__(self, url_fetcher, max_items):
    self._url_fetcher = url_fetcher
    self._max_items = max_items

  def work(self, request):
    response = FeedFetchResponse(request.feed_url, is_success=True)
    try:
      try:
        try:
          self._fetch(request)
        except urllib2.HTTPError as e:
          # Reader's MediaRSS reconstruction code appears to have a bug for some
          # feeds (it causes an exception to be thrown), so we retry with
          # MediaRSS turned off before giving up.
          if e.code == 500:
            logging.warn('500 response when fetching %s, '
              'retrying with MediaRSS turned off', request.feed_url)
            self._fetch(request, media_rss=False)
          else:
            response.is_success = False
        except ET.ParseError as e:
            logging.warn('XML parse error when fetching %s, '
              'retrying with MediaRSS turned off', request.feed_url)
            self._fetch(request, media_rss=False)
      except ET.ParseError as e:
            logging.warn('XML parse error when fetching %s, retrying with '
                'MediaRSS and high-fidelity turned off', request.feed_url)
            self._fetch(request, media_rss=False, hifi=False)
    except:
      logging.error(
          'Exception when fetching %s', request.feed_url, exc_info=True)
      response.is_success = False
    finally:
      return response

  def _fetch(self, request, media_rss=True, hifi=True):
    continuation_token = None
    combined_feed = None
    total_entries = 0
    while True:
      parameters = _BASE_PARAMETERS.copy()
      if continuation_token:
        parameters['c'] = continuation_token
      if media_rss:
        parameters['mediaRss'] = 'true'
      stream_id = get_stream_id(request.feed_url)
      reader_url = (
        'http://www.google.com/reader/public/atom/%s%s?%s' %
        ('hifi/' if hifi else '', urllib.quote(stream_id),
            urllib.urlencode(parameters)))
      logging.debug('Fetching %s', reader_url)
      url_response_text = self._url_fetcher.fetch(reader_url)
      response_root = ET.fromstring(url_response_text)
      entries = response_root.findall('{%s}entry' % base.atom.ATOM_NS)
      oldest_message = ''
      if entries:
        last_crawl_timestamp_msec = \
            entries[-1].attrib['{%s}crawl-timestamp-msec' % base.atom.READER_NS]
        last_crawl_timestamp = datetime.datetime.utcfromtimestamp(
            float(last_crawl_timestamp_msec)/1000)
        oldest_message = ' (oldest is from %s)' % last_crawl_timestamp
      logging.info('Loaded %d items%s', len(entries), oldest_message)
      if combined_feed:
        combined_feed.extend(entries)
      else:
        combined_feed = response_root

      total_entries += len(entries)
      if self._max_items and total_entries >= self._max_items:
        break

      continuation_element = response_root.find(
          '{%s}continuation' % base.atom.READER_NS)
      if continuation_element is not None:
        # Strip the continuation token from the combined feed, it's only
        # applicable to the first chunk.
        response_root.remove(continuation_element)
        continuation_token = continuation_element.text
      else:
        break
    combined_feed_tree = ET.ElementTree(combined_feed)

    if request.output_path:
      output_file = open(request.output_path, 'w')
      logging.info('Writing %d items to %s' % (total_entries, request.output_path))
    else:
      output_file = sys.stdout
      logging.info('Writing %d items to stdout' % total_entries)
    combined_feed_tree.write(
        output_file,
        xml_declaration=True,
        encoding='utf-8')
    if request.output_path:
      output_file.close()

class FeedFetchRequest(object):
  def __init__(self, feed_url, output_path):
    self.feed_url = feed_url
    self.output_path = output_path

class FeedFetchResponse(object):
  def __init__(self, feed_url, is_success):
    self.feed_url = feed_url
    self.is_success = is_success

def extract_feed_urls_from_opml_file(opml_file_path):
  tree = ET.parse(opml_file_path)
  feed_urls = []
  seen_feed_urls = set()
  for outline in tree.iter(tag='outline'):
    if 'xmlUrl' in outline.attrib:
      feed_url = outline.attrib['xmlUrl']
      if feed_url in seen_feed_urls:
        continue
      feed_urls.append(feed_url)
      seen_feed_urls.add(feed_url)
  return feed_urls

def init_base_parameters(args):
  _BASE_PARAMETERS['n'] = args.chunk_size
  if args.oldest_item_timestamp_sec:
    _BASE_PARAMETERS['ot'] = args.oldest_item_timestamp_sec
  if args.newest_item_timestamp_sec:
    _BASE_PARAMETERS['nt'] = args.newest_item_timestamp_sec

def get_output_path(base_path, feed_url):
  file_name = base.paths.url_to_file_name(feed_url)
  return os.path.join(base_path, file_name)

def get_stream_id(feed_url):
  try:
    parsed = urlparse.urlparse(feed_url)
    # If the feed is generated by Reader itself, turn it into the underlying
    # stream ID.
    if parsed.hostname.startswith('www.google.') and \
        parsed.path.startswith(_READER_SHARED_TAG_FEED_URL_PATH_PREFIX):
      reader_url_prefix = '%s://%s%s' % (
        parsed.scheme, parsed.hostname, _READER_SHARED_TAG_FEED_URL_PATH_PREFIX)
      return feed_url[len(reader_url_prefix):]
  except:
    # Ignore malformed URLs
    pass
  return 'feed/%s' % feed_url

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = item_lookup
import argparse
import datetime
import json
import logging
import os
import os.path
import sys
import xml.etree.cElementTree as ET

import base.api
import base.atom
import base.paths
import base.log

def main():
  global archive_directory
  base.atom.init()
  base.log.init()

  parser = argparse.ArgumentParser(
      description='HTTP server that allows the browsing of an archive of a'
                  'Google Reader account')

  parser.add_argument('item_ids', metavar='item_id', nargs='*', default=[],
                      help='Item ID(s) to look up.')
  parser.add_argument('--archive_directory',
                      help='Path to archive directory generated by '
                           'reader_archive to look up the item in.')

  args = parser.parse_args()

  if not args.archive_directory:
    logging.error('--archive_directory was not specified')
    sys.exit(1)
  archive_directory = base.paths.normalize(args.archive_directory)
  if not os.path.exists(archive_directory):
    logging.error('Could not find archive directory %s', archive_directory)
    syst.exit(1)

  item_ids = []
  for raw_item_id in args.item_ids:
    item_id = base.api.item_id_from_any_form(raw_item_id)
    if not item_id:
      logging.error('%s is not a valid ID', raw_item_id)
      sys.exit(1)
    item_ids.append(item_id)
  if not item_ids:
      logging.error('No item IDs were specified.')
      sys.exit(1)

  logging.info('Looking up streams for items.')
  streams_directory = os.path.join(archive_directory, 'streams')
  item_ids_to_stream_ids_and_timestamps = {}
  for stream_file_name in os.listdir(streams_directory):
    with open(os.path.join(streams_directory, stream_file_name)) as stream_file:
      stream_json = json.load(stream_file)
      for item_id in item_ids:
        timestamp_usec = stream_json['item_refs'].get(item_id.to_json())
        if not timestamp_usec:
          continue
        item_ids_to_stream_ids_and_timestamps.setdefault(item_id, []).append(
            (stream_json['stream_id'], timestamp_usec))

  for item_id in item_ids:
    logging.info('Item ID %s:', item_id)
    stream_ids_and_timestamps = \
        item_ids_to_stream_ids_and_timestamps.get(item_id)
    if stream_ids_and_timestamps:
      for stream_id, timestamp_usec in stream_ids_and_timestamps:
        timestamp_date = datetime.datetime.utcfromtimestamp(
            timestamp_usec/1000000.0)
        logging.info('  In the stream %s with timestamp %d (%s)',
            stream_id, timestamp_usec, timestamp_date.isoformat())
    else:
      logging.warn('  Not found in any streams')

  logging.info('Looking up bodies for items.')
  for item_id in item_ids:
    item_body_path = base.paths.item_id_to_file_path(
        os.path.join(archive_directory, 'items'), item_id)
    if os.path.exists(item_body_path):
      with open(item_body_path) as item_body_file:
        feed = base.atom.parse(item_body_file)
        found_entry = False
        for entry in feed.entries:
          if entry.item_id == item_id:
            logging.info('Body for item %s:', item_id)
            logging.info('  %s', ET.tostring(entry.element))
            found_entry = True
            break
        if not found_entry:
          logging.warning('Did not find item body for %s', item_id)
    else:
      logging.warning('No item body file found for %s', item_id)

  logging.info('Looking up comments for items')
  for item_id in item_ids:
    item_comments_path = os.path.join(base.paths.item_id_to_file_path(
        os.path.join(archive_directory, 'comments'), item_id),
        item_id.compact_form())
    if os.path.exists(item_comments_path):
      logging.info('Comments on item %s:', item_id)
      with open(item_comments_path) as item_comments_file:
        comments_json = json.load(item_comments_file)
        comments_by_venue = {}
        for comment_json in comments_json:
          comment = base.api.Comment.from_json(comment_json)
          comments_by_venue.setdefault(comment.venue_stream_id, []).append(comment)

        for venue_stream_id, comments in comments_by_venue.iteritems():
          logging.info('  Venue %s', venue_stream_id)
          for comment in comments:
            logging.info('    "%s" by %s',
                         comment.plain_content, comment.author_name)
    else:
      logging.info('No comments for item %s', item_id)



if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = reader_archive
import argparse
import itertools
import json
import logging
import os.path
import urllib
import urllib2
import sys
import xml.etree.cElementTree as ET

import base.api
import base.atom
import base.log
import base.tag_helper
import base.url_fetcher
import base.worker

def main():
  base.log.init()
  base.atom.init()

  parser = argparse.ArgumentParser(
      description='Comprehensive archive of a Google Reader account')

  # Credentials
  parser.add_argument('--use_client_login' ,action='store_true',
                      help='Instead of OAuth, use ClientLogin for '
                            'authentication. You will be prompted for a '
                            'username and password')
  parser.add_argument('--oauth_refresh_token', default='',
                      help='A previously obtained refresh token (used to bypass '
                            'OAuth setup')
  parser.add_argument('--account', default='',
                      help='Google Account to save the archive for. Omit to '
                          'specify via standard input')
  parser.add_argument('--password', default='',
                      help='Password for the account. Omit to specify via '
                          'standard input')

  # Output options
  parser.add_argument('--output_directory', default='./',
                      help='Directory where to place archive data.')

  # Fetching options
  parser.add_argument('--stream_items_chunk_size', type=int, default=10000,
                      help='Number of items refs to request per stream items '
                           'API call (higher is more efficient)')
  parser.add_argument('--max_items_per_stream', type=int, default=0,
                      help='If non-zero, will cap the number of items that are '
                            'fetched per feed or tag')
  parser.add_argument('--item_bodies_chunk_size', type=int, default=250,
                      help='Number of items refs per request for fetching their '
                           'bodies (higher is more efficient)')
  parser.add_argument('--comments_chunk_size', type=int, default=250,
                      help='Number of items per request for fetching comments '
                           'on shared items (higher is more efficient)')
  parser.add_argument('--max_streams', type=int, default=0,
                      help='Maxmium number of streams to archive (0 for no'
                           'limit, only mean to be used for development)')
  parser.add_argument('--parallelism', type=int, default=10,
                      help='Number of requests to make in parallel.')
  parser.add_argument('--http_retry_count', type=int, default=1,
                      help='Number of retries to make in the case of HTTP '
                           'request errors.')

  # Miscellaneous.
  parser.add_argument('--additional_item_refs_file_path', default='',
                      help='Path to JSON file listing additional tag item refs '
                           'to fetch')

  args = parser.parse_args()

  output_directory = base.paths.normalize(args.output_directory)
  base.paths.ensure_exists(output_directory)
  def output_sub_directory(name):
    directory_path = os.path.join(output_directory, name)
    base.paths.ensure_exists(directory_path)
    return directory_path
  api_responses_directory = output_sub_directory('_raw_data')
  streams_directory = output_sub_directory('streams')
  data_directory = output_sub_directory('data')
  items_directory = output_sub_directory('items')
  comments_directory = output_sub_directory('comments')

  if args.use_client_login:
    authenticated_url_fetcher = base.url_fetcher.ClientLoginUrlFetcher(
        args.account, args.password)
  else:
    authenticated_url_fetcher = base.url_fetcher.OAuthUrlFetcher(
        args.oauth_refresh_token)
  api = base.api.Api(
      authenticated_url_fetcher=authenticated_url_fetcher,
      http_retry_count=args.http_retry_count,
      cache_directory=api_responses_directory)

  user_info = api.fetch_user_info()
  logging.info(
    'Created API instance for %s (%s)', user_info.user_id, user_info.email)

  logging.info('Saving preferences')
  _save_preferences(api, data_directory)

  logging.info('Gathering streams to fetch')
  stream_ids = _get_stream_ids(api, user_info.user_id, data_directory)
  if args.max_streams and len(stream_ids) > args.max_streams:
    stream_ids = stream_ids[:args.max_streams]
  logging.info('%d streams to fetch, gathering item refs:', len(stream_ids))

  item_ids, item_refs_total = _fetch_and_save_item_refs(
      stream_ids, api, args, streams_directory, user_info.user_id)
  logging.info('%s unique items refs (%s total), grouping by chunk.',
      '{:,}'.format(len(item_ids)),
      '{:,}'.format(item_refs_total))

  logging.info('Grouped item refs, getting item bodies:')

  item_ids_chunks = _chunk_item_ids(item_ids, args.item_bodies_chunk_size)

  item_bodies_to_fetch = len(item_ids)
  fetched_item_bodies = [0]
  missing_item_bodies = set()
  def report_item_bodies_progress(requested_item_ids, found_item_ids):
    if found_item_ids is None:
      missing_item_bodies.update(set(requested_item_ids).difference(
          base.api.not_found_items_ids_to_ignore))
      return
    fetched_item_bodies[0] += len(found_item_ids)
    missing_item_bodies.update(
        set(requested_item_ids).difference(set(found_item_ids)).difference(
            base.api.not_found_items_ids_to_ignore))
    logging.info('  Fetched %s/%s item bodies (%s could not be loaded)',
        '{:,}'.format(fetched_item_bodies[0]),
        '{:,}'.format(item_bodies_to_fetch),
        '{:,}'.format(len(missing_item_bodies)))
  base.worker.do_work(
      lambda: FetchWriteItemBodiesWorker(api, items_directory),
      item_ids_chunks,
      args.parallelism,
      report_progress=report_item_bodies_progress)

  if missing_item_bodies:
    logging.warn('Item bodies could not be loaded for: %s',
        ', '.join([i.compact_form() for i in missing_item_bodies]))

  broadcast_stream_ids = [
      stream_id for stream_id in stream_ids
      if stream_id.startswith('user/') and
          stream_id.endswith('/state/com.google/broadcast')
  ]
  logging.info(
      'Fetching comments from %d shared item streams.',
      len(broadcast_stream_ids))
  encoded_sharers = api.fetch_encoded_sharers()
  remaining_broadcast_stream_ids = [len(broadcast_stream_ids)]
  def report_comments_progress(_, comments_by_item_id):
    if comments_by_item_id is None:
      return
    remaining_broadcast_stream_ids[0] -= 1
    comment_count = sum((len(c) for c in comments_by_item_id.values()), 0)
    logging.info('  Fetched %s comments, %s shared items streams left.',
        '{:,}'.format(comment_count),
        '{:,}'.format(remaining_broadcast_stream_ids[0]))
  all_comments = {}
  comments_for_broadcast_streams = base.worker.do_work(
      lambda: FetchCommentsWorker(
          api, encoded_sharers, args.comments_chunk_size),
      broadcast_stream_ids,
      args.parallelism,
      report_progress=report_comments_progress)
  total_comment_count = 0
  for comments_for_broadcast_stream in comments_for_broadcast_streams:
    if not comments_for_broadcast_stream:
      continue
    for item_id, comments in comments_for_broadcast_stream.iteritems():
      total_comment_count += len(comments)
      all_comments.setdefault(item_id, []).extend(comments)

  logging.info('Writing %s comments from %s items.',
      '{:,}'.format(total_comment_count),
      '{:,}'.format(len(all_comments)))
  for item_id, comments in all_comments.items():
    item_comments_file_path = os.path.join(base.paths.item_id_to_file_path(
        comments_directory, item_id), item_id.compact_form())
    base.paths.ensure_exists(os.path.dirname(item_comments_file_path))
    with open(item_comments_file_path, 'w') as item_comments_file:
      item_comments_file.write(json.dumps([c.to_json() for c in comments]))

  with open(os.path.join(output_directory, 'README'), 'w') as readme_file:
    readme_file.write('See https://github.com/mihaip/readerisdead/'
        'wiki/reader_archive-Format.\n')

def _save_preferences(api, data_directory):
  def save(preferences_json, file_name):
    file_path = os.path.join(data_directory, file_name)
    with open(file_path, 'w') as file:
      file.write(json.dumps(preferences_json))

  save(api.fetch_preferences(), 'preferences.json')
  save(api.fetch_stream_preferences(), 'stream-preferences.json')
  save(
      [g.to_json() for g in api.fetch_sharing_groups()], 'sharing-groups.json')
  save(api.fetch_sharing_acl().to_json(), 'sharing-acl.json')
  save(api.fetch_user_info().to_json(), 'user-info.json')

def _get_stream_ids(api, user_id, data_directory):
  def save_items(items, file_name):
    file_path = os.path.join(data_directory, file_name)
    with open(file_path, 'w') as file:
      file.write(json.dumps([i.to_json() for i in items]))

  stream_ids = set()

  tags = api.fetch_tags()
  tag_stream_ids = set([t.stream_id for t in tags])
  for system_tag in base.tag_helper.TagHelper(user_id).system_tags():
    if system_tag.stream_id not in tag_stream_ids:
      tags.append(system_tag)
      tag_stream_ids.add(system_tag.stream_id)
  stream_ids.update([tag.stream_id for tag in tags])
  save_items(tags, 'tags.json')

  subscriptions = api.fetch_subscriptions()
  stream_ids.update([sub.stream_id for sub in subscriptions])
  save_items(subscriptions, 'subscriptions.json')

  friends = api.fetch_friends()
  stream_ids.update([
      f.stream_id for f in friends if f.stream_id and f.is_following])
  save_items(friends, 'friends.json')

  bundles = api.fetch_bundles()
  for bundle in bundles:
    stream_ids.update([f.stream_id for f in bundle.feeds])
  save_items(bundles, 'bundles.json')

  recommendations = api.fetch_recommendations()
  stream_ids.update([r.stream_id for r in recommendations])
  save_items(recommendations, 'recommendations.json')

  stream_ids.add(base.api.EXPLORE_STREAM_ID)

  stream_ids = list(stream_ids)
  # Start the fetch with user streams, since those tend to have more items and
  # are thus the long pole.
  stream_ids.sort(reverse=True)
  return stream_ids

def _load_additional_item_refs(
    additional_item_refs_file_path, stream_ids, item_refs_responses, user_id):
  logging.info('Adding additional item refs.')
  compact_item_ids_by_stream_id = {}
  item_refs_responses_by_stream_id = {}
  for stream_id, item_refs in itertools.izip(stream_ids, item_refs_responses):
    compact_item_ids_by_stream_id[stream_id] = set(
      item_ref.item_id.compact_form() for item_ref in item_refs)
    item_refs_responses_by_stream_id[stream_id] = item_refs

  # The JSON file stores item IDs in hex, but with a leading 0x. Additionally,
  # timestamps are in microseconds, but they're stored as strings.
  def item_ref_from_json(item_ref_json):
      return base.api.ItemRef(
        item_id=base.api.item_id_from_compact_form(item_ref_json['id'][2:]),
        timestamp_usec=int(item_ref_json['timestampUsec']))

  with open(additional_item_refs_file_path) as additional_item_refs_file:
    additional_item_refs = json.load(additional_item_refs_file)
    for stream_id, item_refs_json in additional_item_refs.iteritems():
      if not stream_id.startswith('user/%s/' % user_id) or \
          'state/com.google/touch' in stream_id or \
          'state/com.google/recommendations-' in stream_id:
        # Ignore tags from other users and those added by
        # https://github.com/mihaip/google-reader-touch. Also ignore the
        # recommendations tags, the items that they refer to aren't actually
        # items in the Reader backend.
        continue

      if stream_id not in item_refs_responses_by_stream_id:
        logging.info('  Stream %s (%s items) is new.',
          stream_id, '{:,}'.format(len(item_refs_json)))
        stream_ids.append(stream_id)
        item_refs_responses.append(
            [item_ref_from_json(i) for i in item_refs_json])
      else:
        new_item_refs = []
        alread_known_item_ref_count = 0
        known_item_ids = compact_item_ids_by_stream_id[stream_id]
        for item_ref_json in item_refs_json:
          if item_ref_json['id'] == '0x859df8b8d14b566e':
            # Skip this item, it seems to cause persistent 500s
            continue
          if item_ref_json['id'][2:] not in known_item_ids:
            new_item_refs.append(item_ref_from_json(item_ref_json))
          else:
            alread_known_item_ref_count += 1
        if new_item_refs:
          logging.info('  Got an additional %s item refs for %s '
              '(%s were already known)',
              '{:,}'.format(len(new_item_refs)),
              stream_id,
              '{:,}'.format(alread_known_item_ref_count))
          item_refs_responses_by_stream_id[stream_id].extend(new_item_refs)

def _fetch_and_save_item_refs(
    stream_ids, api, args, streams_directory, user_id):
  fetched_stream_ids = [0]
  def report_item_refs_progress(stream_id, item_refs):
    if item_refs is None:
      logging.error('  Could not load item refs from %s', stream_id)
      return
    fetched_stream_ids[0] += 1
    logging.info('  Loaded %s item refs from %s, %d streams left.',
        '{:,}'.format(len(item_refs)),
        stream_id,
        len(stream_ids) - fetched_stream_ids[0])
  item_refs_responses = base.worker.do_work(
      lambda: FetchItemRefsWorker(
          api, args.stream_items_chunk_size, args.max_items_per_stream),
      stream_ids,
      args.parallelism,
      report_progress=report_item_refs_progress)

  if args.additional_item_refs_file_path:
    _load_additional_item_refs(
        base.paths.normalize(args.additional_item_refs_file_path),
        stream_ids,
        item_refs_responses,
        user_id)

  logging.info('Saving item refs for %d streams',
      len([i for i in item_refs_responses if i is not None]))

  item_ids = set()
  item_refs_total = 0
  for stream_id, item_refs in itertools.izip(stream_ids, item_refs_responses):
    if not item_refs:
      continue
    item_ids.update([item_ref.item_id for item_ref in item_refs])
    item_refs_total += len(item_refs)

    if stream_id == base.api.EXPLORE_STREAM_ID:
      base.api.not_found_items_ids_to_ignore.update(
          [i.item_id for i in item_refs])

    stream = base.api.Stream(stream_id=stream_id, item_refs=item_refs)
    stream_file_name = base.paths.stream_id_to_file_name(stream_id) + '.json'
    stream_file_path = os.path.join(streams_directory, stream_file_name)
    with open(stream_file_path, 'w') as stream_file:
      stream_file.write(json.dumps(stream.to_json()))

  return list(item_ids), item_refs_total

def _chunk_item_ids(item_ids, chunk_size):
  # We have two different chunking goals:
  # - Fetch items in large-ish chunks (ideally 250), to minimize HTTP request
  #   overhead per item
  # - Write items in small-ish chunks (ideally around 10) per file, since having
  #   a file per item is too annoying to deal with from a file-system
  #   perspective. We also need the chunking into files to be deterministic, so
  #   that from an item ID we know what file to look for it in.
  # We therefore first chunk the IDs by file path, and then group those chunks
  # into ID chunks that we fetch.
  # We write the file chunks immediately after fetching to decrease the
  # in-memory working set of the script.
  item_ids_by_path = {}
  for item_id in item_ids:
    item_id_file_path = base.paths.item_id_to_file_path('', item_id)
    item_ids_by_path.setdefault(item_id_file_path, []).append(item_id)

  current_item_ids_chunk = []
  item_ids_chunks = [current_item_ids_chunk]
  for item_ids_for_file_path in item_ids_by_path.values():
    if len(current_item_ids_chunk) + len(item_ids_for_file_path) > chunk_size:
      current_item_ids_chunk = []
      item_ids_chunks.append(current_item_ids_chunk)
    current_item_ids_chunk.extend(item_ids_for_file_path)

  return item_ids_chunks

class FetchItemRefsWorker(base.worker.Worker):
  _PROGRESS_REPORT_INTERVAL = 50000
  def __init__(self, api, chunk_size, max_items_per_stream):
    self._api = api
    self._chunk_size = chunk_size
    self._max_items_per_stream = max_items_per_stream

  def work(self, stream_id):
    result = []
    continuation_token = None
    next_progress_report = FetchItemRefsWorker._PROGRESS_REPORT_INTERVAL
    while True:
      try:
        item_refs, continuation_token = self._api.fetch_item_refs(
            stream_id,
            count=self._chunk_size,
            continuation_token=continuation_token)
      except urllib2.HTTPError as e:
        if e.code == 400 and 'Permission denied' in e.read():
          logging.warn('  Permission denied when getting items for the stream '
              '%s, it\'s most likely private now.', stream_id)
          return None
        else:
          raise
      result.extend(item_refs)
      if len(result) >= next_progress_report:
        logging.debug('  %s item refs fetched so far from %s',
            '{:,}'.format(len(result)), stream_id)
        next_progress_report += FetchItemRefsWorker._PROGRESS_REPORT_INTERVAL
      if not continuation_token or (self._max_items_per_stream and
          len(result) >= self._max_items_per_stream):
        break
    return result

class FetchWriteItemBodiesWorker(base.worker.Worker):
  def __init__(self, api, items_directory):
    self._api = api
    self._items_directory = items_directory

  def work(self, item_ids):
    if not item_ids:
      return 0

    item_bodies_by_id = self._fetch_item_bodies(item_ids)
    if not item_bodies_by_id:
      return []

    item_bodies_by_file_path = self._group_item_bodies(
      item_bodies_by_id.values())
    for file_path, item_bodies in item_bodies_by_file_path.items():
      self._write_item_bodies(file_path, item_bodies)
    return item_bodies_by_id.keys()

  def _fetch_item_bodies(self, item_ids):
    def fetch(hifi=True):
      result = self._api.fetch_item_bodies(
              item_ids,
              format='atom-hifi' if hifi else 'atom',
              # Turn off authentication in order to make the request cheaper/
              # faster. Item bodies are not ACLed, we already have per-user tags
              # via the stream item ref fetches, and will be fetching comments
              # for shared items separately.
              authenticated=False)
      return result

    try:
      try:
        return fetch()
      except urllib2.HTTPError as e:
        if e.code == 500:
          logging.info('  500 response when fetching %d items, retrying with '
              'high-fidelity output turned off', len(item_ids))
          return fetch(hifi=False)
        else:
          logging.error('  HTTP error %d when fetching items: %s',
              e.code, ','.join([i.compact_form() for i in item_ids]), e.read())
          return None
      except ET.ParseError as e:
          logging.info('  XML parse error when fetching %d items, retrying '
              'with high-fidelity turned off', len(item_ids))
          return fetch(hifi=False)
    except urllib2.HTTPError as e:
      if e.code == 500 and len(item_ids) > 1:
        logging.info('  500 response even with high-fidelity output turned '
            'off, splitting %d chunk into two to find problematic items',
            len(item_ids))
        return self._fetch_item_bodies_split(item_ids)
      else:
        logging.error('  HTTP error %d when fetching %s items%s',
            e.code, ','.join([i.compact_form() for i in item_ids]),
            (': %s' % e.read()) if e.code != 500 else '')
        return None
    except:
      logging.error('  Exception when fetching items %s',
          ','.join([i.compact_form() for i in item_ids]), exc_info=True)
      return None

  def _fetch_item_bodies_split(self, item_ids):
    split_point = int(len(item_ids)/2)
    first_chunk = item_ids[0:split_point]
    second_chunk = item_ids[split_point:]

    result = {}
    if first_chunk:
      first_chunk_result = self._fetch_item_bodies(first_chunk)
      if first_chunk_result:
        result.update(first_chunk_result)
    if second_chunk:
      second_chunk_result = self._fetch_item_bodies(second_chunk)
      if second_chunk_result:
        result.update(second_chunk_result)
    return result

  def _group_item_bodies(self, item_bodies):
    item_bodies_by_path = {}
    for entry in item_bodies:
      item_id_file_path = base.paths.item_id_to_file_path(
          self._items_directory, entry.item_id)
      item_bodies_by_path.setdefault(item_id_file_path, []).append(entry)
    return item_bodies_by_path

  def _write_item_bodies(self, file_path, item_bodies):
    base.paths.ensure_exists(os.path.dirname(file_path))
    feed_element = ET.Element('{%s}feed' % base.atom.ATOM_NS)
    for entry in item_bodies:
      feed_element.append(entry.element)

    with open(file_path, 'w') as items_file:
        ET.ElementTree(feed_element).write(
            items_file,
            xml_declaration=True,
            encoding='utf-8')

class FetchCommentsWorker(base.worker.Worker):
  def __init__(self, api, encoded_sharers, chunk_size):
    self._api = api
    self._encoded_sharers = encoded_sharers
    self._chunk_size = chunk_size

  def work(self, broadcast_stream_id):
    result = {}
    continuation_token = None
    while True:
      comments_by_item_id, continuation_token = self._api.fetch_comments(
          broadcast_stream_id,
          encoded_sharers=self._encoded_sharers,
          count=self._chunk_size,
          continuation_token=continuation_token)
      result.update(comments_by_item_id)
      if not continuation_token:
        break
    return result

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = reader_browser
import argparse
import logging
import os.path
import socket
import sys
import webbrowser
import SimpleHTTPServer
import SocketServer

import base.paths
import base.log

static_directory = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "static"))
archive_directory = None

_STATIC_PATH_PREFIX = '/static/'
_ARCHIVE_PATH_PREFIX = '/archive/'

def main():
  global archive_directory
  base.log.init()

  parser = argparse.ArgumentParser(
      description='HTTP server that allows the browsing of an archive of a'
                  'Google Reader account')

  parser.add_argument('archive_directory',
                      help='Directory to load archive data from.')
  parser.add_argument('--port', type=int, default=8071,
                      help='Port that the HTTP server will run on.')

  args = parser.parse_args()

  archive_directory = base.paths.normalize(args.archive_directory)
  if not os.path.exists(archive_directory):
    logging.error("Could not find archive directory %s", archive_directory)
    syst.exit(1)

  httpd = Server(("", args.port), Handler)

  homepage_url = "http://%s:%d/" % (socket.gethostname(), args.port)
  logging.info("Serving at %s", homepage_url)
  webbrowser.open_new_tab(homepage_url)
  httpd.serve_forever()


class Server(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    # Ctrl-C will cleanly kill all spawned threads.
    daemon_threads = True
    # Much faster rebinding.
    allow_reuse_address = True

    def __init__(self, server_address, handler_class):
        SocketServer.TCPServer.__init__(self, server_address, handler_class)


class Handler(SimpleHTTPServer.SimpleHTTPRequestHandler):
  def translate_path(self, path):
    if path == '/':
      return os.path.join(static_directory, "index.html")

    if path.startswith(_STATIC_PATH_PREFIX):
      static_file_path = os.path.abspath(
          os.path.join(static_directory, path[len(_STATIC_PATH_PREFIX):]))
      if static_file_path.startswith(static_directory):
        return static_file_path

    if path.startswith(_ARCHIVE_PATH_PREFIX):
      archive_file_path = os.path.abspath(
          os.path.join(archive_directory, path[len(_ARCHIVE_PATH_PREFIX):]))
      if archive_file_path.startswith(archive_directory):
        return archive_file_path

    # Fallthrough
    return os.path.join(static_directory, "404.html")

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = application
"""
Web application
(from web.py)
"""
import webapi as web
import webapi, wsgi, utils
import debugerror
import httpserver

from utils import lstrips, safeunicode
import sys

import urllib
import traceback
import itertools
import os
import types
from exceptions import SystemExit

try:
    import wsgiref.handlers
except ImportError:
    pass # don't break people with old Pythons

__all__ = [
    "application", "auto_application",
    "subdir_application", "subdomain_application", 
    "loadhook", "unloadhook",
    "autodelegate"
]

class application:
    """
    Application to delegate requests based on path.
    
        >>> urls = ("/hello", "hello")
        >>> app = application(urls, globals())
        >>> class hello:
        ...     def GET(self): return "hello"
        >>>
        >>> app.request("/hello").data
        'hello'
    """
    def __init__(self, mapping=(), fvars={}, autoreload=None):
        if autoreload is None:
            autoreload = web.config.get('debug', False)
        self.init_mapping(mapping)
        self.fvars = fvars
        self.processors = []
        
        self.add_processor(loadhook(self._load))
        self.add_processor(unloadhook(self._unload))
        
        if autoreload:
            def main_module_name():
                mod = sys.modules['__main__']
                file = getattr(mod, '__file__', None) # make sure this works even from python interpreter
                return file and os.path.splitext(os.path.basename(file))[0]

            def modname(fvars):
                """find name of the module name from fvars."""
                file, name = fvars.get('__file__'), fvars.get('__name__')
                if file is None or name is None:
                    return None

                if name == '__main__':
                    # Since the __main__ module can't be reloaded, the module has 
                    # to be imported using its file name.                    
                    name = main_module_name()
                return name
                
            mapping_name = utils.dictfind(fvars, mapping)
            module_name = modname(fvars)
            
            def reload_mapping():
                """loadhook to reload mapping and fvars."""
                mod = __import__(module_name, None, None, [''])
                mapping = getattr(mod, mapping_name, None)
                if mapping:
                    self.fvars = mod.__dict__
                    self.init_mapping(mapping)

            self.add_processor(loadhook(Reloader()))
            if mapping_name and module_name:
                self.add_processor(loadhook(reload_mapping))

            # load __main__ module usings its filename, so that it can be reloaded.
            if main_module_name() and '__main__' in sys.argv:
                try:
                    __import__(main_module_name())
                except ImportError:
                    pass
                    
    def _load(self):
        web.ctx.app_stack.append(self)
        
    def _unload(self):
        web.ctx.app_stack = web.ctx.app_stack[:-1]
        
        if web.ctx.app_stack:
            # this is a sub-application, revert ctx to earlier state.
            oldctx = web.ctx.get('_oldctx')
            if oldctx:
                web.ctx.home = oldctx.home
                web.ctx.homepath = oldctx.homepath
                web.ctx.path = oldctx.path
                web.ctx.fullpath = oldctx.fullpath
                
    def _cleanup(self):
        # Threads can be recycled by WSGI servers.
        # Clearing up all thread-local state to avoid interefereing with subsequent requests.
        utils.ThreadedDict.clear_all()

    def init_mapping(self, mapping):
        self.mapping = list(utils.group(mapping, 2))

    def add_mapping(self, pattern, classname):
        self.mapping.append((pattern, classname))

    def add_processor(self, processor):
        """
        Adds a processor to the application. 
        
            >>> urls = ("/(.*)", "echo")
            >>> app = application(urls, globals())
            >>> class echo:
            ...     def GET(self, name): return name
            ...
            >>>
            >>> def hello(handler): return "hello, " +  handler()
            ...
            >>> app.add_processor(hello)
            >>> app.request("/web.py").data
            'hello, web.py'
        """
        self.processors.append(processor)

    def request(self, localpart='/', method='GET', data=None,
                host="0.0.0.0:8080", headers=None, https=False, **kw):
        """Makes request to this application for the specified path and method.
        Response will be a storage object with data, status and headers.

            >>> urls = ("/hello", "hello")
            >>> app = application(urls, globals())
            >>> class hello:
            ...     def GET(self): 
            ...         web.header('Content-Type', 'text/plain')
            ...         return "hello"
            ...
            >>> response = app.request("/hello")
            >>> response.data
            'hello'
            >>> response.status
            '200 OK'
            >>> response.headers['Content-Type']
            'text/plain'

        To use https, use https=True.

            >>> urls = ("/redirect", "redirect")
            >>> app = application(urls, globals())
            >>> class redirect:
            ...     def GET(self): raise web.seeother("/foo")
            ...
            >>> response = app.request("/redirect")
            >>> response.headers['Location']
            'http://0.0.0.0:8080/foo'
            >>> response = app.request("/redirect", https=True)
            >>> response.headers['Location']
            'https://0.0.0.0:8080/foo'

        The headers argument specifies HTTP headers as a mapping object
        such as a dict.

            >>> urls = ('/ua', 'uaprinter')
            >>> class uaprinter:
            ...     def GET(self):
            ...         return 'your user-agent is ' + web.ctx.env['HTTP_USER_AGENT']
            ... 
            >>> app = application(urls, globals())
            >>> app.request('/ua', headers = {
            ...      'User-Agent': 'a small jumping bean/1.0 (compatible)'
            ... }).data
            'your user-agent is a small jumping bean/1.0 (compatible)'

        """
        path, maybe_query = urllib.splitquery(localpart)
        query = maybe_query or ""
        
        if 'env' in kw:
            env = kw['env']
        else:
            env = {}
        env = dict(env, HTTP_HOST=host, REQUEST_METHOD=method, PATH_INFO=path, QUERY_STRING=query, HTTPS=str(https))
        headers = headers or {}

        for k, v in headers.items():
            env['HTTP_' + k.upper().replace('-', '_')] = v

        if 'HTTP_CONTENT_LENGTH' in env:
            env['CONTENT_LENGTH'] = env.pop('HTTP_CONTENT_LENGTH')

        if 'HTTP_CONTENT_TYPE' in env:
            env['CONTENT_TYPE'] = env.pop('HTTP_CONTENT_TYPE')

        if method not in ["HEAD", "GET"]:
            data = data or ''
            import StringIO
            if isinstance(data, dict):
                q = urllib.urlencode(data)
            else:
                q = data
            env['wsgi.input'] = StringIO.StringIO(q)
            if not env.get('CONTENT_TYPE', '').lower().startswith('multipart/') and 'CONTENT_LENGTH' not in env:
                env['CONTENT_LENGTH'] = len(q)
        response = web.storage()
        def start_response(status, headers):
            response.status = status
            response.headers = dict(headers)
            response.header_items = headers
        response.data = "".join(self.wsgifunc()(env, start_response))
        return response

    def browser(self):
        import browser
        return browser.AppBrowser(self)

    def handle(self):
        fn, args = self._match(self.mapping, web.ctx.path)
        return self._delegate(fn, self.fvars, args)
        
    def handle_with_processors(self):
        def process(processors):
            try:
                if processors:
                    p, processors = processors[0], processors[1:]
                    return p(lambda: process(processors))
                else:
                    return self.handle()
            except web.HTTPError:
                raise
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                print >> web.debug, traceback.format_exc()
                raise self.internalerror()
        
        # processors must be applied in the resvere order. (??)
        return process(self.processors)
                        
    def wsgifunc(self, *middleware):
        """Returns a WSGI-compatible function for this application."""
        def peep(iterator):
            """Peeps into an iterator by doing an iteration
            and returns an equivalent iterator.
            """
            # wsgi requires the headers first
            # so we need to do an iteration
            # and save the result for later
            try:
                firstchunk = iterator.next()
            except StopIteration:
                firstchunk = ''

            return itertools.chain([firstchunk], iterator)    
                                
        def is_generator(x): return x and hasattr(x, 'next')
        
        def wsgi(env, start_resp):
            # clear threadlocal to avoid inteference of previous requests
            self._cleanup()

            self.load(env)
            try:
                # allow uppercase methods only
                if web.ctx.method.upper() != web.ctx.method:
                    raise web.nomethod()

                result = self.handle_with_processors()
                if is_generator(result):
                    result = peep(result)
                else:
                    result = [result]
            except web.HTTPError, e:
                result = [e.data]

            result = web.safestr(iter(result))

            status, headers = web.ctx.status, web.ctx.headers
            start_resp(status, headers)
            
            def cleanup():
                self._cleanup()
                yield '' # force this function to be a generator
                            
            return itertools.chain(result, cleanup())

        for m in middleware: 
            wsgi = m(wsgi)

        return wsgi

    def run(self, *middleware):
        """
        Starts handling requests. If called in a CGI or FastCGI context, it will follow
        that protocol. If called from the command line, it will start an HTTP
        server on the port named in the first command line argument, or, if there
        is no argument, on port 8080.
        
        `middleware` is a list of WSGI middleware which is applied to the resulting WSGI
        function.
        """
        return wsgi.runwsgi(self.wsgifunc(*middleware))

    def stop(self):
        """Stops the http server started by run.
        """
        if httpserver.server:
            httpserver.server.stop()
            httpserver.server = None
    
    def cgirun(self, *middleware):
        """
        Return a CGI handler. This is mostly useful with Google App Engine.
        There you can just do:
        
            main = app.cgirun()
        """
        wsgiapp = self.wsgifunc(*middleware)

        try:
            from google.appengine.ext.webapp.util import run_wsgi_app
            return run_wsgi_app(wsgiapp)
        except ImportError:
            # we're not running from within Google App Engine
            return wsgiref.handlers.CGIHandler().run(wsgiapp)
    
    def load(self, env):
        """Initializes ctx using env."""
        ctx = web.ctx
        ctx.clear()
        ctx.status = '200 OK'
        ctx.headers = []
        ctx.output = ''
        ctx.environ = ctx.env = env
        ctx.host = env.get('HTTP_HOST')

        if env.get('wsgi.url_scheme') in ['http', 'https']:
            ctx.protocol = env['wsgi.url_scheme']
        elif env.get('HTTPS', '').lower() in ['on', 'true', '1']:
            ctx.protocol = 'https'
        else:
            ctx.protocol = 'http'
        ctx.homedomain = ctx.protocol + '://' + env.get('HTTP_HOST', '[unknown]')
        ctx.homepath = os.environ.get('REAL_SCRIPT_NAME', env.get('SCRIPT_NAME', ''))
        ctx.home = ctx.homedomain + ctx.homepath
        #@@ home is changed when the request is handled to a sub-application.
        #@@ but the real home is required for doing absolute redirects.
        ctx.realhome = ctx.home
        ctx.ip = env.get('REMOTE_ADDR')
        ctx.method = env.get('REQUEST_METHOD')
        ctx.path = env.get('PATH_INFO')
        # http://trac.lighttpd.net/trac/ticket/406 requires:
        if env.get('SERVER_SOFTWARE', '').startswith('lighttpd/'):
            ctx.path = lstrips(env.get('REQUEST_URI').split('?')[0], ctx.homepath)
            # Apache and CherryPy webservers unquote the url but lighttpd doesn't. 
            # unquote explicitly for lighttpd to make ctx.path uniform across all servers.
            ctx.path = urllib.unquote(ctx.path)

        if env.get('QUERY_STRING'):
            ctx.query = '?' + env.get('QUERY_STRING', '')
        else:
            ctx.query = ''

        ctx.fullpath = ctx.path + ctx.query
        
        for k, v in ctx.iteritems():
            # convert all string values to unicode values and replace 
            # malformed data with a suitable replacement marker.
            if isinstance(v, str):
                ctx[k] = v.decode('utf-8', 'replace') 

        # status must always be str
        ctx.status = '200 OK'
        
        ctx.app_stack = []

    def _delegate(self, f, fvars, args=[]):
        def handle_class(cls):
            meth = web.ctx.method
            if meth == 'HEAD' and not hasattr(cls, meth):
                meth = 'GET'
            if not hasattr(cls, meth):
                raise web.nomethod(cls)
            tocall = getattr(cls(), meth)
            return tocall(*args)
            
        def is_class(o): return isinstance(o, (types.ClassType, type))
            
        if f is None:
            raise web.notfound()
        elif isinstance(f, application):
            return f.handle_with_processors()
        elif is_class(f):
            return handle_class(f)
        elif isinstance(f, basestring):
            if f.startswith('redirect '):
                url = f.split(' ', 1)[1]
                if web.ctx.method == "GET":
                    x = web.ctx.env.get('QUERY_STRING', '')
                    if x:
                        url += '?' + x
                raise web.redirect(url)
            elif '.' in f:
                mod, cls = f.rsplit('.', 1)
                mod = __import__(mod, None, None, [''])
                cls = getattr(mod, cls)
            else:
                cls = fvars[f]
            return handle_class(cls)
        elif hasattr(f, '__call__'):
            return f()
        else:
            return web.notfound()

    def _match(self, mapping, value):
        for pat, what in mapping:
            if isinstance(what, application):
                if value.startswith(pat):
                    f = lambda: self._delegate_sub_application(pat, what)
                    return f, None
                else:
                    continue
            elif isinstance(what, basestring):
                what, result = utils.re_subm('^' + pat + '$', what, value)
            else:
                result = utils.re_compile('^' + pat + '$').match(value)
                
            if result: # it's a match
                return what, [x for x in result.groups()]
        return None, None
        
    def _delegate_sub_application(self, dir, app):
        """Deletes request to sub application `app` rooted at the directory `dir`.
        The home, homepath, path and fullpath values in web.ctx are updated to mimic request
        to the subapp and are restored after it is handled. 
        
        @@Any issues with when used with yield?
        """
        web.ctx._oldctx = web.storage(web.ctx)
        web.ctx.home += dir
        web.ctx.homepath += dir
        web.ctx.path = web.ctx.path[len(dir):]
        web.ctx.fullpath = web.ctx.fullpath[len(dir):]
        return app.handle_with_processors()
            
    def get_parent_app(self):
        if self in web.ctx.app_stack:
            index = web.ctx.app_stack.index(self)
            if index > 0:
                return web.ctx.app_stack[index-1]
        
    def notfound(self):
        """Returns HTTPError with '404 not found' message"""
        parent = self.get_parent_app()
        if parent:
            return parent.notfound()
        else:
            return web._NotFound()
            
    def internalerror(self):
        """Returns HTTPError with '500 internal error' message"""
        parent = self.get_parent_app()
        if parent:
            return parent.internalerror()
        elif web.config.get('debug'):
            import debugerror
            return debugerror.debugerror()
        else:
            return web._InternalError()

class auto_application(application):
    """Application similar to `application` but urls are constructed 
    automatiacally using metaclass.

        >>> app = auto_application()
        >>> class hello(app.page):
        ...     def GET(self): return "hello, world"
        ...
        >>> class foo(app.page):
        ...     path = '/foo/.*'
        ...     def GET(self): return "foo"
        >>> app.request("/hello").data
        'hello, world'
        >>> app.request('/foo/bar').data
        'foo'
    """
    def __init__(self):
        application.__init__(self)

        class metapage(type):
            def __init__(klass, name, bases, attrs):
                type.__init__(klass, name, bases, attrs)
                path = attrs.get('path', '/' + name)

                # path can be specified as None to ignore that class
                # typically required to create a abstract base class.
                if path is not None:
                    self.add_mapping(path, klass)

        class page:
            path = None
            __metaclass__ = metapage

        self.page = page

# The application class already has the required functionality of subdir_application
subdir_application = application
                
class subdomain_application(application):
    """
    Application to delegate requests based on the host.

        >>> urls = ("/hello", "hello")
        >>> app = application(urls, globals())
        >>> class hello:
        ...     def GET(self): return "hello"
        >>>
        >>> mapping = (r"hello\.example\.com", app)
        >>> app2 = subdomain_application(mapping)
        >>> app2.request("/hello", host="hello.example.com").data
        'hello'
        >>> response = app2.request("/hello", host="something.example.com")
        >>> response.status
        '404 Not Found'
        >>> response.data
        'not found'
    """
    def handle(self):
        host = web.ctx.host.split(':')[0] #strip port
        fn, args = self._match(self.mapping, host)
        return self._delegate(fn, self.fvars, args)
        
    def _match(self, mapping, value):
        for pat, what in mapping:
            if isinstance(what, basestring):
                what, result = utils.re_subm('^' + pat + '$', what, value)
            else:
                result = utils.re_compile('^' + pat + '$').match(value)

            if result: # it's a match
                return what, [x for x in result.groups()]
        return None, None
        
def loadhook(h):
    """
    Converts a load hook into an application processor.
    
        >>> app = auto_application()
        >>> def f(): "something done before handling request"
        ...
        >>> app.add_processor(loadhook(f))
    """
    def processor(handler):
        h()
        return handler()
        
    return processor
    
def unloadhook(h):
    """
    Converts an unload hook into an application processor.
    
        >>> app = auto_application()
        >>> def f(): "something done after handling request"
        ...
        >>> app.add_processor(unloadhook(f))    
    """
    def processor(handler):
        try:
            result = handler()
            is_generator = result and hasattr(result, 'next')
        except:
            # run the hook even when handler raises some exception
            h()
            raise

        if is_generator:
            return wrap(result)
        else:
            h()
            return result
            
    def wrap(result):
        def next():
            try:
                return result.next()
            except:
                # call the hook at the and of iterator
                h()
                raise

        result = iter(result)
        while True:
            yield next()
            
    return processor

def autodelegate(prefix=''):
    """
    Returns a method that takes one argument and calls the method named prefix+arg,
    calling `notfound()` if there isn't one. Example:

        urls = ('/prefs/(.*)', 'prefs')

        class prefs:
            GET = autodelegate('GET_')
            def GET_password(self): pass
            def GET_privacy(self): pass

    `GET_password` would get called for `/prefs/password` while `GET_privacy` for 
    `GET_privacy` gets called for `/prefs/privacy`.
    
    If a user visits `/prefs/password/change` then `GET_password(self, '/change')`
    is called.
    """
    def internal(self, arg):
        if '/' in arg:
            first, rest = arg.split('/', 1)
            func = prefix + first
            args = ['/' + rest]
        else:
            func = prefix + arg
            args = []
        
        if hasattr(self, func):
            try:
                return getattr(self, func)(*args)
            except TypeError:
                raise web.notfound()
        else:
            raise web.notfound()
    return internal

class Reloader:
    """Checks to see if any loaded modules have changed on disk and, 
    if so, reloads them.
    """

    """File suffix of compiled modules."""
    if sys.platform.startswith('java'):
        SUFFIX = '$py.class'
    else:
        SUFFIX = '.pyc'
    
    def __init__(self):
        self.mtimes = {}

    def __call__(self):
        for mod in sys.modules.values():
            self.check(mod)

    def check(self, mod):
        # jython registers java packages as modules but they either
        # don't have a __file__ attribute or its value is None
        if not (mod and hasattr(mod, '__file__') and mod.__file__):
            return

        try: 
            mtime = os.stat(mod.__file__).st_mtime
        except (OSError, IOError):
            return
        if mod.__file__.endswith(self.__class__.SUFFIX) and os.path.exists(mod.__file__[:-1]):
            mtime = max(os.stat(mod.__file__[:-1]).st_mtime, mtime)
            
        if mod not in self.mtimes:
            self.mtimes[mod] = mtime
        elif self.mtimes[mod] < mtime:
            try: 
                reload(mod)
                self.mtimes[mod] = mtime
            except ImportError: 
                pass
                
if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = browser
"""Browser to test web applications.
(from web.py)
"""
from utils import re_compile
from net import htmlunquote

import httplib, urllib, urllib2
import copy
from StringIO import StringIO

DEBUG = False

__all__ = [
    "BrowserError",
    "Browser", "AppBrowser",
    "AppHandler"
]

class BrowserError(Exception):
    pass

class Browser:
    def __init__(self):
        import cookielib
        self.cookiejar = cookielib.CookieJar()
        self._cookie_processor = urllib2.HTTPCookieProcessor(self.cookiejar)
        self.form = None

        self.url = "http://0.0.0.0:8080/"
        self.path = "/"
        
        self.status = None
        self.data = None
        self._response = None
        self._forms = None

    def reset(self):
        """Clears all cookies and history."""
        self.cookiejar.clear()

    def build_opener(self):
        """Builds the opener using urllib2.build_opener. 
        Subclasses can override this function to prodive custom openers.
        """
        return urllib2.build_opener()

    def do_request(self, req):
        if DEBUG:
            print 'requesting', req.get_method(), req.get_full_url()
        opener = self.build_opener()
        opener.add_handler(self._cookie_processor)
        try:
            self._response = opener.open(req)
        except urllib2.HTTPError, e:
            self._response = e

        self.url = self._response.geturl()
        self.path = urllib2.Request(self.url).get_selector()
        self.data = self._response.read()
        self.status = self._response.code
        self._forms = None
        self.form = None
        return self.get_response()

    def open(self, url, data=None, headers={}):
        """Opens the specified url."""
        url = urllib.basejoin(self.url, url)
        req = urllib2.Request(url, data, headers)
        return self.do_request(req)

    def show(self):
        """Opens the current page in real web browser."""
        f = open('page.html', 'w')
        f.write(self.data)
        f.close()

        import webbrowser, os
        url = 'file://' + os.path.abspath('page.html')
        webbrowser.open(url)

    def get_response(self):
        """Returns a copy of the current response."""
        return urllib.addinfourl(StringIO(self.data), self._response.info(), self._response.geturl())

    def get_soup(self):
        """Returns beautiful soup of the current document."""
        import BeautifulSoup
        return BeautifulSoup.BeautifulSoup(self.data)

    def get_text(self, e=None):
        """Returns content of e or the current document as plain text."""
        e = e or self.get_soup()
        return ''.join([htmlunquote(c) for c in e.recursiveChildGenerator() if isinstance(c, unicode)])

    def _get_links(self):
        soup = self.get_soup()
        return [a for a in soup.findAll(name='a')]
        
    def get_links(self, text=None, text_regex=None, url=None, url_regex=None, predicate=None):
        """Returns all links in the document."""
        return self._filter_links(self._get_links(),
            text=text, text_regex=text_regex, url=url, url_regex=url_regex, predicate=predicate)

    def follow_link(self, link=None, text=None, text_regex=None, url=None, url_regex=None, predicate=None):
        if link is None:
            links = self._filter_links(self.get_links(),
                text=text, text_regex=text_regex, url=url, url_regex=url_regex, predicate=predicate)
            link = links and links[0]
            
        if link:
            return self.open(link['href'])
        else:
            raise BrowserError("No link found")
            
    def find_link(self, text=None, text_regex=None, url=None, url_regex=None, predicate=None):
        links = self._filter_links(self.get_links(), 
            text=text, text_regex=text_regex, url=url, url_regex=url_regex, predicate=predicate)
        return links and links[0] or None
            
    def _filter_links(self, links, 
            text=None, text_regex=None,
            url=None, url_regex=None,
            predicate=None):
        predicates = []
        if text is not None:
            predicates.append(lambda link: link.string == text)
        if text_regex is not None:
            predicates.append(lambda link: re_compile(text_regex).search(link.string or ''))
        if url is not None:
            predicates.append(lambda link: link.get('href') == url)
        if url_regex is not None:
            predicates.append(lambda link: re_compile(url_regex).search(link.get('href', '')))
        if predicate:
            predicate.append(predicate)

        def f(link):
            for p in predicates:
                if not p(link):
                    return False
            return True

        return [link for link in links if f(link)]

    def get_forms(self):
        """Returns all forms in the current document.
        The returned form objects implement the ClientForm.HTMLForm interface.
        """
        if self._forms is None:
            import ClientForm
            self._forms = ClientForm.ParseResponse(self.get_response(), backwards_compat=False)
        return self._forms

    def select_form(self, name=None, predicate=None, index=0):
        """Selects the specified form."""
        forms = self.get_forms()

        if name is not None:
            forms = [f for f in forms if f.name == name]
        if predicate:
            forms = [f for f in forms if predicate(f)]
            
        if forms:
            self.form = forms[index]
            return self.form
        else:
            raise BrowserError("No form selected.")
        
    def submit(self, **kw):
        """submits the currently selected form."""
        if self.form is None:
            raise BrowserError("No form selected.")
        req = self.form.click(**kw)
        return self.do_request(req)

    def __getitem__(self, key):
        return self.form[key]

    def __setitem__(self, key, value):
        self.form[key] = value

class AppBrowser(Browser):
    """Browser interface to test web.py apps.
    
        b = AppBrowser(app)
        b.open('/')
        b.follow_link(text='Login')
        
        b.select_form(name='login')
        b['username'] = 'joe'
        b['password'] = 'secret'
        b.submit()

        assert b.path == '/'
        assert 'Welcome joe' in b.get_text()
    """
    def __init__(self, app):
        Browser.__init__(self)
        self.app = app

    def build_opener(self):
        return urllib2.build_opener(AppHandler(self.app))

class AppHandler(urllib2.HTTPHandler):
    """urllib2 handler to handle requests using web.py application."""
    handler_order = 100

    def __init__(self, app):
        self.app = app

    def http_open(self, req):
        result = self.app.request(
            localpart=req.get_selector(),
            method=req.get_method(),
            host=req.get_host(),
            data=req.get_data(),
            headers=dict(req.header_items()),
            https=req.get_type() == "https"
        )
        return self._make_response(result, req.get_full_url())

    def https_open(self, req):
        return self.http_open(req)
    
    try:
        https_request = urllib2.HTTPHandler.do_request_
    except AttributeError:
        # for python 2.3
        pass

    def _make_response(self, result, url):
        data = "\r\n".join(["%s: %s" % (k, v) for k, v in result.header_items])
        headers = httplib.HTTPMessage(StringIO(data))
        response = urllib.addinfourl(StringIO(result.data), headers, url)
        code, msg = result.status.split(None, 1)
        response.code, response.msg = int(code), msg
        return response

########NEW FILE########
__FILENAME__ = template
"""
Interface to various templating engines.
"""
import os.path

__all__ = [
    "render_cheetah", "render_genshi", "render_mako",
    "cache", 
]

class render_cheetah:
    """Rendering interface to Cheetah Templates.

    Example:

        render = render_cheetah('templates')
        render.hello(name="cheetah")
    """
    def __init__(self, path):
        # give error if Chetah is not installed
        from Cheetah.Template import Template
        self.path = path

    def __getattr__(self, name):
        from Cheetah.Template import Template
        path = os.path.join(self.path, name + ".html")
        
        def template(**kw):
            t = Template(file=path, searchList=[kw])
            return t.respond()

        return template
    
class render_genshi:
    """Rendering interface genshi templates.
    Example:

    for xml/html templates.

        render = render_genshi(['templates/'])
        render.hello(name='genshi')

    For text templates:

        render = render_genshi(['templates/'], type='text')
        render.hello(name='genshi')
    """

    def __init__(self, *a, **kwargs):
        from genshi.template import TemplateLoader

        self._type = kwargs.pop('type', None)
        self._loader = TemplateLoader(*a, **kwargs)

    def __getattr__(self, name):
        # Assuming all templates are html
        path = name + ".html"

        if self._type == "text":
            from genshi.template import TextTemplate
            cls = TextTemplate
            type = "text"
        else:
            cls = None
            type = None

        t = self._loader.load(path, cls=cls)
        def template(**kw):
            stream = t.generate(**kw)
            if type:
                return stream.render(type)
            else:
                return stream.render()
        return template

class render_jinja:
    """Rendering interface to Jinja2 Templates
    
    Example:

        render= render_jinja('templates')
        render.hello(name='jinja2')
    """
    def __init__(self, *a, **kwargs):
        extensions = kwargs.pop('extensions', [])
        globals = kwargs.pop('globals', {})

        from jinja2 import Environment,FileSystemLoader
        self._lookup = Environment(loader=FileSystemLoader(*a, **kwargs), extensions=extensions)
        self._lookup.globals.update(globals)
        
    def __getattr__(self, name):
        # Assuming all templates end with .html
        path = name + '.html'
        t = self._lookup.get_template(path)
        return t.render
        
class render_mako:
    """Rendering interface to Mako Templates.

    Example:

        render = render_mako(directories=['templates'])
        render.hello(name="mako")
    """
    def __init__(self, *a, **kwargs):
        from mako.lookup import TemplateLookup
        self._lookup = TemplateLookup(*a, **kwargs)

    def __getattr__(self, name):
        # Assuming all templates are html
        path = name + ".html"
        t = self._lookup.get_template(path)
        return t.render

class cache:
    """Cache for any rendering interface.
    
    Example:

        render = cache(render_cheetah("templates/"))
        render.hello(name='cache')
    """
    def __init__(self, render):
        self._render = render
        self._cache = {}

    def __getattr__(self, name):
        if name not in self._cache:
            self._cache[name] = getattr(self._render, name)
        return self._cache[name]

########NEW FILE########
__FILENAME__ = db
"""
Database API
(part of web.py)
"""

__all__ = [
  "UnknownParamstyle", "UnknownDB", "TransactionError", 
  "sqllist", "sqlors", "reparam", "sqlquote",
  "SQLQuery", "SQLParam", "sqlparam",
  "SQLLiteral", "sqlliteral",
  "database", 'DB',
]

import time
try:
    import datetime
except ImportError:
    datetime = None

try: set
except NameError:
    from sets import Set as set
    
from utils import threadeddict, storage, iters, iterbetter, safestr, safeunicode

try:
    # db module can work independent of web.py
    from webapi import debug, config
except:
    import sys
    debug = sys.stderr
    config = storage()

class UnknownDB(Exception):
    """raised for unsupported dbms"""
    pass

class _ItplError(ValueError): 
    def __init__(self, text, pos):
        ValueError.__init__(self)
        self.text = text
        self.pos = pos
    def __str__(self):
        return "unfinished expression in %s at char %d" % (
            repr(self.text), self.pos)

class TransactionError(Exception): pass

class UnknownParamstyle(Exception): 
    """
    raised for unsupported db paramstyles

    (currently supported: qmark, numeric, format, pyformat)
    """
    pass
    
class SQLParam(object):
    """
    Parameter in SQLQuery.
    
        >>> q = SQLQuery(["SELECT * FROM test WHERE name=", SQLParam("joe")])
        >>> q
        <sql: "SELECT * FROM test WHERE name='joe'">
        >>> q.query()
        'SELECT * FROM test WHERE name=%s'
        >>> q.values()
        ['joe']
    """
    __slots__ = ["value"]

    def __init__(self, value):
        self.value = value
        
    def get_marker(self, paramstyle='pyformat'):
        if paramstyle == 'qmark':
            return '?'
        elif paramstyle == 'numeric':
            return ':1'
        elif paramstyle is None or paramstyle in ['format', 'pyformat']:
            return '%s'
        raise UnknownParamstyle, paramstyle
        
    def sqlquery(self): 
        return SQLQuery([self])
        
    def __add__(self, other):
        return self.sqlquery() + other
        
    def __radd__(self, other):
        return other + self.sqlquery() 
            
    def __str__(self): 
        return str(self.value)
    
    def __repr__(self):
        return '<param: %s>' % repr(self.value)

sqlparam =  SQLParam

class SQLQuery(object):
    """
    You can pass this sort of thing as a clause in any db function.
    Otherwise, you can pass a dictionary to the keyword argument `vars`
    and the function will call reparam for you.

    Internally, consists of `items`, which is a list of strings and
    SQLParams, which get concatenated to produce the actual query.
    """
    __slots__ = ["items"]

    # tested in sqlquote's docstring
    def __init__(self, items=None):
        r"""Creates a new SQLQuery.
        
            >>> SQLQuery("x")
            <sql: 'x'>
            >>> q = SQLQuery(['SELECT * FROM ', 'test', ' WHERE x=', SQLParam(1)])
            >>> q
            <sql: 'SELECT * FROM test WHERE x=1'>
            >>> q.query(), q.values()
            ('SELECT * FROM test WHERE x=%s', [1])
            >>> SQLQuery(SQLParam(1))
            <sql: '1'>
        """
        if items is None:
            self.items = []
        elif isinstance(items, list):
            self.items = items
        elif isinstance(items, SQLParam):
            self.items = [items]
        elif isinstance(items, SQLQuery):
            self.items = list(items.items)
        else:
            self.items = [items]
            
        # Take care of SQLLiterals
        for i, item in enumerate(self.items):
            if isinstance(item, SQLParam) and isinstance(item.value, SQLLiteral):
                self.items[i] = item.value.v

    def append(self, value):
        self.items.append(value)

    def __add__(self, other):
        if isinstance(other, basestring):
            items = [other]
        elif isinstance(other, SQLQuery):
            items = other.items
        else:
            return NotImplemented
        return SQLQuery(self.items + items)

    def __radd__(self, other):
        if isinstance(other, basestring):
            items = [other]
        else:
            return NotImplemented
            
        return SQLQuery(items + self.items)

    def __iadd__(self, other):
        if isinstance(other, (basestring, SQLParam)):
            self.items.append(other)
        elif isinstance(other, SQLQuery):
            self.items.extend(other.items)
        else:
            return NotImplemented
        return self

    def __len__(self):
        return len(self.query())
        
    def query(self, paramstyle=None):
        """
        Returns the query part of the sql query.
            >>> q = SQLQuery(["SELECT * FROM test WHERE name=", SQLParam('joe')])
            >>> q.query()
            'SELECT * FROM test WHERE name=%s'
            >>> q.query(paramstyle='qmark')
            'SELECT * FROM test WHERE name=?'
        """
        s = []
        for x in self.items:
            if isinstance(x, SQLParam):
                x = x.get_marker(paramstyle)
                s.append(safestr(x))
            else:
                x = safestr(x)
                # automatically escape % characters in the query
                # For backward compatability, ignore escaping when the query looks already escaped
                if paramstyle in ['format', 'pyformat']:
                    if '%' in x and '%%' not in x:
                        x = x.replace('%', '%%')
                s.append(x)
        return "".join(s)
    
    def values(self):
        """
        Returns the values of the parameters used in the sql query.
            >>> q = SQLQuery(["SELECT * FROM test WHERE name=", SQLParam('joe')])
            >>> q.values()
            ['joe']
        """
        return [i.value for i in self.items if isinstance(i, SQLParam)]
        
    def join(items, sep=' ', prefix=None, suffix=None, target=None):
        """
        Joins multiple queries.
        
        >>> SQLQuery.join(['a', 'b'], ', ')
        <sql: 'a, b'>

        Optinally, prefix and suffix arguments can be provided.

        >>> SQLQuery.join(['a', 'b'], ', ', prefix='(', suffix=')')
        <sql: '(a, b)'>

        If target argument is provided, the items are appended to target instead of creating a new SQLQuery.
        """
        if target is None:
            target = SQLQuery()

        target_items = target.items

        if prefix:
            target_items.append(prefix)

        for i, item in enumerate(items):
            if i != 0:
                target_items.append(sep)
            if isinstance(item, SQLQuery):
                target_items.extend(item.items)
            else:
                target_items.append(item)

        if suffix:
            target_items.append(suffix)
        return target
    
    join = staticmethod(join)
    
    def _str(self):
        try:
            return self.query() % tuple([sqlify(x) for x in self.values()])            
        except (ValueError, TypeError):
            return self.query()
        
    def __str__(self):
        return safestr(self._str())
        
    def __unicode__(self):
        return safeunicode(self._str())

    def __repr__(self):
        return '<sql: %s>' % repr(str(self))

class SQLLiteral: 
    """
    Protects a string from `sqlquote`.

        >>> sqlquote('NOW()')
        <sql: "'NOW()'">
        >>> sqlquote(SQLLiteral('NOW()'))
        <sql: 'NOW()'>
    """
    def __init__(self, v): 
        self.v = v

    def __repr__(self): 
        return self.v

sqlliteral = SQLLiteral

def _sqllist(values):
    """
        >>> _sqllist([1, 2, 3])
        <sql: '(1, 2, 3)'>
    """
    items = []
    items.append('(')
    for i, v in enumerate(values):
        if i != 0:
            items.append(', ')
        items.append(sqlparam(v))
    items.append(')')
    return SQLQuery(items)

def reparam(string_, dictionary): 
    """
    Takes a string and a dictionary and interpolates the string
    using values from the dictionary. Returns an `SQLQuery` for the result.

        >>> reparam("s = $s", dict(s=True))
        <sql: "s = 't'">
        >>> reparam("s IN $s", dict(s=[1, 2]))
        <sql: 's IN (1, 2)'>
    """
    dictionary = dictionary.copy() # eval mucks with it
    vals = []
    result = []
    for live, chunk in _interpolate(string_):
        if live:
            v = eval(chunk, dictionary)
            result.append(sqlquote(v))
        else: 
            result.append(chunk)
    return SQLQuery.join(result, '')

def sqlify(obj): 
    """
    converts `obj` to its proper SQL version

        >>> sqlify(None)
        'NULL'
        >>> sqlify(True)
        "'t'"
        >>> sqlify(3)
        '3'
    """
    # because `1 == True and hash(1) == hash(True)`
    # we have to do this the hard way...

    if obj is None:
        return 'NULL'
    elif obj is True:
        return "'t'"
    elif obj is False:
        return "'f'"
    elif datetime and isinstance(obj, datetime.datetime):
        return repr(obj.isoformat())
    else:
        if isinstance(obj, unicode): obj = obj.encode('utf8')
        return repr(obj)

def sqllist(lst): 
    """
    Converts the arguments for use in something like a WHERE clause.
    
        >>> sqllist(['a', 'b'])
        'a, b'
        >>> sqllist('a')
        'a'
        >>> sqllist(u'abc')
        u'abc'
    """
    if isinstance(lst, basestring): 
        return lst
    else:
        return ', '.join(lst)

def sqlors(left, lst):
    """
    `left is a SQL clause like `tablename.arg = ` 
    and `lst` is a list of values. Returns a reparam-style
    pair featuring the SQL that ORs together the clause
    for each item in the lst.

        >>> sqlors('foo = ', [])
        <sql: '1=2'>
        >>> sqlors('foo = ', [1])
        <sql: 'foo = 1'>
        >>> sqlors('foo = ', 1)
        <sql: 'foo = 1'>
        >>> sqlors('foo = ', [1,2,3])
        <sql: '(foo = 1 OR foo = 2 OR foo = 3 OR 1=2)'>
    """
    if isinstance(lst, iters):
        lst = list(lst)
        ln = len(lst)
        if ln == 0:
            return SQLQuery("1=2")
        if ln == 1:
            lst = lst[0]

    if isinstance(lst, iters):
        return SQLQuery(['('] + 
          sum([[left, sqlparam(x), ' OR '] for x in lst], []) +
          ['1=2)']
        )
    else:
        return left + sqlparam(lst)
        
def sqlwhere(dictionary, grouping=' AND '): 
    """
    Converts a `dictionary` to an SQL WHERE clause `SQLQuery`.
    
        >>> sqlwhere({'cust_id': 2, 'order_id':3})
        <sql: 'order_id = 3 AND cust_id = 2'>
        >>> sqlwhere({'cust_id': 2, 'order_id':3}, grouping=', ')
        <sql: 'order_id = 3, cust_id = 2'>
        >>> sqlwhere({'a': 'a', 'b': 'b'}).query()
        'a = %s AND b = %s'
    """
    return SQLQuery.join([k + ' = ' + sqlparam(v) for k, v in dictionary.items()], grouping)

def sqlquote(a): 
    """
    Ensures `a` is quoted properly for use in a SQL query.

        >>> 'WHERE x = ' + sqlquote(True) + ' AND y = ' + sqlquote(3)
        <sql: "WHERE x = 't' AND y = 3">
        >>> 'WHERE x = ' + sqlquote(True) + ' AND y IN ' + sqlquote([2, 3])
        <sql: "WHERE x = 't' AND y IN (2, 3)">
    """
    if isinstance(a, list):
        return _sqllist(a)
    else:
        return sqlparam(a).sqlquery()

class Transaction:
    """Database transaction."""
    def __init__(self, ctx):
        self.ctx = ctx
        self.transaction_count = transaction_count = len(ctx.transactions)

        class transaction_engine:
            """Transaction Engine used in top level transactions."""
            def do_transact(self):
                ctx.commit(unload=False)

            def do_commit(self):
                ctx.commit()

            def do_rollback(self):
                ctx.rollback()

        class subtransaction_engine:
            """Transaction Engine used in sub transactions."""
            def query(self, q):
                db_cursor = ctx.db.cursor()
                ctx.db_execute(db_cursor, SQLQuery(q % transaction_count))

            def do_transact(self):
                self.query('SAVEPOINT webpy_sp_%s')

            def do_commit(self):
                self.query('RELEASE SAVEPOINT webpy_sp_%s')

            def do_rollback(self):
                self.query('ROLLBACK TO SAVEPOINT webpy_sp_%s')

        class dummy_engine:
            """Transaction Engine used instead of subtransaction_engine 
            when sub transactions are not supported."""
            do_transact = do_commit = do_rollback = lambda self: None

        if self.transaction_count:
            # nested transactions are not supported in some databases
            if self.ctx.get('ignore_nested_transactions'):
                self.engine = dummy_engine()
            else:
                self.engine = subtransaction_engine()
        else:
            self.engine = transaction_engine()

        self.engine.do_transact()
        self.ctx.transactions.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exctype, excvalue, traceback):
        if exctype is not None:
            self.rollback()
        else:
            self.commit()

    def commit(self):
        if len(self.ctx.transactions) > self.transaction_count:
            self.engine.do_commit()
            self.ctx.transactions = self.ctx.transactions[:self.transaction_count]

    def rollback(self):
        if len(self.ctx.transactions) > self.transaction_count:
            self.engine.do_rollback()
            self.ctx.transactions = self.ctx.transactions[:self.transaction_count]

class DB: 
    """Database"""
    def __init__(self, db_module, keywords):
        """Creates a database.
        """
        # some DB implementaions take optional paramater `driver` to use a specific driver modue
        # but it should not be passed to connect
        keywords.pop('driver', None)

        self.db_module = db_module
        self.keywords = keywords

        self._ctx = threadeddict()
        # flag to enable/disable printing queries
        self.printing = config.get('debug_sql', config.get('debug', False))
        self.supports_multiple_insert = False
        
        try:
            import DBUtils
            # enable pooling if DBUtils module is available.
            self.has_pooling = True
        except ImportError:
            self.has_pooling = False
            
        # Pooling can be disabled by passing pooling=False in the keywords.
        self.has_pooling = self.keywords.pop('pooling', True) and self.has_pooling
            
    def _getctx(self): 
        if not self._ctx.get('db'):
            self._load_context(self._ctx)
        return self._ctx
    ctx = property(_getctx)
    
    def _load_context(self, ctx):
        ctx.dbq_count = 0
        ctx.transactions = [] # stack of transactions
        
        if self.has_pooling:
            ctx.db = self._connect_with_pooling(self.keywords)
        else:
            ctx.db = self._connect(self.keywords)
        ctx.db_execute = self._db_execute
        
        if not hasattr(ctx.db, 'commit'):
            ctx.db.commit = lambda: None

        if not hasattr(ctx.db, 'rollback'):
            ctx.db.rollback = lambda: None
            
        def commit(unload=True):
            # do db commit and release the connection if pooling is enabled.            
            ctx.db.commit()
            if unload and self.has_pooling:
                self._unload_context(self._ctx)
                
        def rollback():
            # do db rollback and release the connection if pooling is enabled.
            ctx.db.rollback()
            if self.has_pooling:
                self._unload_context(self._ctx)
                
        ctx.commit = commit
        ctx.rollback = rollback
            
    def _unload_context(self, ctx):
        del ctx.db
            
    def _connect(self, keywords):
        return self.db_module.connect(**keywords)
        
    def _connect_with_pooling(self, keywords):
        def get_pooled_db():
            from DBUtils import PooledDB

            # In DBUtils 0.9.3, `dbapi` argument is renamed as `creator`
            # see Bug#122112
            
            if PooledDB.__version__.split('.') < '0.9.3'.split('.'):
                return PooledDB.PooledDB(dbapi=self.db_module, **keywords)
            else:
                return PooledDB.PooledDB(creator=self.db_module, **keywords)
        
        if getattr(self, '_pooleddb', None) is None:
            self._pooleddb = get_pooled_db()
        
        return self._pooleddb.connection()
        
    def _db_cursor(self):
        return self.ctx.db.cursor()

    def _param_marker(self):
        """Returns parameter marker based on paramstyle attribute if this database."""
        style = getattr(self, 'paramstyle', 'pyformat')

        if style == 'qmark':
            return '?'
        elif style == 'numeric':
            return ':1'
        elif style in ['format', 'pyformat']:
            return '%s'
        raise UnknownParamstyle, style

    def _db_execute(self, cur, sql_query): 
        """executes an sql query"""
        self.ctx.dbq_count += 1
        
        try:
            a = time.time()
            query, params = self._process_query(sql_query)
            out = cur.execute(query, params)
            b = time.time()
        except:
            if self.printing:
                print >> debug, 'ERR:', str(sql_query)
            if self.ctx.transactions:
                self.ctx.transactions[-1].rollback()
            else:
                self.ctx.rollback()
            raise

        if self.printing:
            print >> debug, '%s (%s): %s' % (round(b-a, 2), self.ctx.dbq_count, str(sql_query))
        return out

    def _process_query(self, sql_query):
        """Takes the SQLQuery object and returns query string and parameters.
        """
        paramstyle = getattr(self, 'paramstyle', 'pyformat')
        query = sql_query.query(paramstyle)
        params = sql_query.values()
        return query, params
    
    def _where(self, where, vars): 
        if isinstance(where, (int, long)):
            where = "id = " + sqlparam(where)
        #@@@ for backward-compatibility
        elif isinstance(where, (list, tuple)) and len(where) == 2:
            where = SQLQuery(where[0], where[1])
        elif isinstance(where, SQLQuery):
            pass
        else:
            where = reparam(where, vars)        
        return where
    
    def query(self, sql_query, vars=None, processed=False, _test=False): 
        """
        Execute SQL query `sql_query` using dictionary `vars` to interpolate it.
        If `processed=True`, `vars` is a `reparam`-style list to use 
        instead of interpolating.
        
            >>> db = DB(None, {})
            >>> db.query("SELECT * FROM foo", _test=True)
            <sql: 'SELECT * FROM foo'>
            >>> db.query("SELECT * FROM foo WHERE x = $x", vars=dict(x='f'), _test=True)
            <sql: "SELECT * FROM foo WHERE x = 'f'">
            >>> db.query("SELECT * FROM foo WHERE x = " + sqlquote('f'), _test=True)
            <sql: "SELECT * FROM foo WHERE x = 'f'">
        """
        if vars is None: vars = {}
        
        if not processed and not isinstance(sql_query, SQLQuery):
            sql_query = reparam(sql_query, vars)
        
        if _test: return sql_query
        
        db_cursor = self._db_cursor()
        self._db_execute(db_cursor, sql_query)
        
        if db_cursor.description:
            names = [x[0] for x in db_cursor.description]
            def iterwrapper():
                row = db_cursor.fetchone()
                while row:
                    yield storage(dict(zip(names, row)))
                    row = db_cursor.fetchone()
            out = iterbetter(iterwrapper())
            out.__len__ = lambda: int(db_cursor.rowcount)
            out.list = lambda: [storage(dict(zip(names, x))) \
                               for x in db_cursor.fetchall()]
        else:
            out = db_cursor.rowcount
        
        if not self.ctx.transactions: 
            self.ctx.commit()
        return out
    
    def select(self, tables, vars=None, what='*', where=None, order=None, group=None, 
               limit=None, offset=None, _test=False): 
        """
        Selects `what` from `tables` with clauses `where`, `order`, 
        `group`, `limit`, and `offset`. Uses vars to interpolate. 
        Otherwise, each clause can be a SQLQuery.
        
            >>> db = DB(None, {})
            >>> db.select('foo', _test=True)
            <sql: 'SELECT * FROM foo'>
            >>> db.select(['foo', 'bar'], where="foo.bar_id = bar.id", limit=5, _test=True)
            <sql: 'SELECT * FROM foo, bar WHERE foo.bar_id = bar.id LIMIT 5'>
        """
        if vars is None: vars = {}
        sql_clauses = self.sql_clauses(what, tables, where, group, order, limit, offset)
        clauses = [self.gen_clause(sql, val, vars) for sql, val in sql_clauses if val is not None]
        qout = SQLQuery.join(clauses)
        if _test: return qout
        return self.query(qout, processed=True)
    
    def where(self, table, what='*', order=None, group=None, limit=None, 
              offset=None, _test=False, **kwargs):
        """
        Selects from `table` where keys are equal to values in `kwargs`.
        
            >>> db = DB(None, {})
            >>> db.where('foo', bar_id=3, _test=True)
            <sql: 'SELECT * FROM foo WHERE bar_id = 3'>
            >>> db.where('foo', source=2, crust='dewey', _test=True)
            <sql: "SELECT * FROM foo WHERE source = 2 AND crust = 'dewey'">
            >>> db.where('foo', _test=True)
            <sql: 'SELECT * FROM foo'>
        """
        where_clauses = []
        for k, v in kwargs.iteritems():
            where_clauses.append(k + ' = ' + sqlquote(v))
            
        if where_clauses:
            where = SQLQuery.join(where_clauses, " AND ")
        else:
            where = None
            
        return self.select(table, what=what, order=order, 
               group=group, limit=limit, offset=offset, _test=_test, 
               where=where)
    
    def sql_clauses(self, what, tables, where, group, order, limit, offset): 
        return (
            ('SELECT', what),
            ('FROM', sqllist(tables)),
            ('WHERE', where),
            ('GROUP BY', group),
            ('ORDER BY', order),
            ('LIMIT', limit),
            ('OFFSET', offset))
    
    def gen_clause(self, sql, val, vars): 
        if isinstance(val, (int, long)):
            if sql == 'WHERE':
                nout = 'id = ' + sqlquote(val)
            else:
                nout = SQLQuery(val)
        #@@@
        elif isinstance(val, (list, tuple)) and len(val) == 2:
            nout = SQLQuery(val[0], val[1]) # backwards-compatibility
        elif isinstance(val, SQLQuery):
            nout = val
        else:
            nout = reparam(val, vars)

        def xjoin(a, b):
            if a and b: return a + ' ' + b
            else: return a or b

        return xjoin(sql, nout)

    def insert(self, tablename, seqname=None, _test=False, **values): 
        """
        Inserts `values` into `tablename`. Returns current sequence ID.
        Set `seqname` to the ID if it's not the default, or to `False`
        if there isn't one.
        
            >>> db = DB(None, {})
            >>> q = db.insert('foo', name='bob', age=2, created=SQLLiteral('NOW()'), _test=True)
            >>> q
            <sql: "INSERT INTO foo (age, name, created) VALUES (2, 'bob', NOW())">
            >>> q.query()
            'INSERT INTO foo (age, name, created) VALUES (%s, %s, NOW())'
            >>> q.values()
            [2, 'bob']
        """
        def q(x): return "(" + x + ")"
        
        if values:
            _keys = SQLQuery.join(values.keys(), ', ')
            _values = SQLQuery.join([sqlparam(v) for v in values.values()], ', ')
            sql_query = "INSERT INTO %s " % tablename + q(_keys) + ' VALUES ' + q(_values)
        else:
            sql_query = SQLQuery(self._get_insert_default_values_query(tablename))

        if _test: return sql_query
        
        db_cursor = self._db_cursor()
        if seqname is not False: 
            sql_query = self._process_insert_query(sql_query, tablename, seqname)

        if isinstance(sql_query, tuple):
            # for some databases, a separate query has to be made to find 
            # the id of the inserted row.
            q1, q2 = sql_query
            self._db_execute(db_cursor, q1)
            self._db_execute(db_cursor, q2)
        else:
            self._db_execute(db_cursor, sql_query)

        try: 
            out = db_cursor.fetchone()[0]
        except Exception: 
            out = None
        
        if not self.ctx.transactions: 
            self.ctx.commit()
        return out
        
    def _get_insert_default_values_query(self, table):
        return "INSERT INTO %s DEFAULT VALUES" % table

    def multiple_insert(self, tablename, values, seqname=None, _test=False):
        """
        Inserts multiple rows into `tablename`. The `values` must be a list of dictioanries, 
        one for each row to be inserted, each with the same set of keys.
        Returns the list of ids of the inserted rows.        
        Set `seqname` to the ID if it's not the default, or to `False`
        if there isn't one.
        
            >>> db = DB(None, {})
            >>> db.supports_multiple_insert = True
            >>> values = [{"name": "foo", "email": "foo@example.com"}, {"name": "bar", "email": "bar@example.com"}]
            >>> db.multiple_insert('person', values=values, _test=True)
            <sql: "INSERT INTO person (name, email) VALUES ('foo', 'foo@example.com'), ('bar', 'bar@example.com')">
        """        
        if not values:
            return []
            
        if not self.supports_multiple_insert:
            out = [self.insert(tablename, seqname=seqname, _test=_test, **v) for v in values]
            if seqname is False:
                return None
            else:
                return out
                
        keys = values[0].keys()
        #@@ make sure all keys are valid

        # make sure all rows have same keys.
        for v in values:
            if v.keys() != keys:
                raise ValueError, 'Bad data'

        sql_query = SQLQuery('INSERT INTO %s (%s) VALUES ' % (tablename, ', '.join(keys)))

        for i, row in enumerate(values):
            if i != 0:
                sql_query.append(", ")
            SQLQuery.join([SQLParam(row[k]) for k in keys], sep=", ", target=sql_query, prefix="(", suffix=")")
        
        if _test: return sql_query

        db_cursor = self._db_cursor()
        if seqname is not False: 
            sql_query = self._process_insert_query(sql_query, tablename, seqname)

        if isinstance(sql_query, tuple):
            # for some databases, a separate query has to be made to find 
            # the id of the inserted row.
            q1, q2 = sql_query
            self._db_execute(db_cursor, q1)
            self._db_execute(db_cursor, q2)
        else:
            self._db_execute(db_cursor, sql_query)

        try: 
            out = db_cursor.fetchone()[0]
            out = range(out-len(values)+1, out+1)        
        except Exception: 
            out = None

        if not self.ctx.transactions: 
            self.ctx.commit()
        return out

    
    def update(self, tables, where, vars=None, _test=False, **values): 
        """
        Update `tables` with clause `where` (interpolated using `vars`)
        and setting `values`.

            >>> db = DB(None, {})
            >>> name = 'Joseph'
            >>> q = db.update('foo', where='name = $name', name='bob', age=2,
            ...     created=SQLLiteral('NOW()'), vars=locals(), _test=True)
            >>> q
            <sql: "UPDATE foo SET age = 2, name = 'bob', created = NOW() WHERE name = 'Joseph'">
            >>> q.query()
            'UPDATE foo SET age = %s, name = %s, created = NOW() WHERE name = %s'
            >>> q.values()
            [2, 'bob', 'Joseph']
        """
        if vars is None: vars = {}
        where = self._where(where, vars)

        query = (
          "UPDATE " + sqllist(tables) + 
          " SET " + sqlwhere(values, ', ') + 
          " WHERE " + where)

        if _test: return query
        
        db_cursor = self._db_cursor()
        self._db_execute(db_cursor, query)
        if not self.ctx.transactions: 
            self.ctx.commit()
        return db_cursor.rowcount
    
    def delete(self, table, where, using=None, vars=None, _test=False): 
        """
        Deletes from `table` with clauses `where` and `using`.

            >>> db = DB(None, {})
            >>> name = 'Joe'
            >>> db.delete('foo', where='name = $name', vars=locals(), _test=True)
            <sql: "DELETE FROM foo WHERE name = 'Joe'">
        """
        if vars is None: vars = {}
        where = self._where(where, vars)

        q = 'DELETE FROM ' + table
        if using: q += ' USING ' + sqllist(using)
        if where: q += ' WHERE ' + where

        if _test: return q

        db_cursor = self._db_cursor()
        self._db_execute(db_cursor, q)
        if not self.ctx.transactions: 
            self.ctx.commit()
        return db_cursor.rowcount

    def _process_insert_query(self, query, tablename, seqname):
        return query

    def transaction(self): 
        """Start a transaction."""
        return Transaction(self.ctx)
    
class PostgresDB(DB): 
    """Postgres driver."""
    def __init__(self, **keywords):
        if 'pw' in keywords:
            keywords['password'] = keywords.pop('pw')
            
        db_module = import_driver(["psycopg2", "psycopg", "pgdb"], preferred=keywords.pop('driver', None))
        if db_module.__name__ == "psycopg2":
            import psycopg2.extensions
            psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)

        # if db is not provided postgres driver will take it from PGDATABASE environment variable
        if 'db' in keywords:
            keywords['database'] = keywords.pop('db')
        
        self.dbname = "postgres"
        self.paramstyle = db_module.paramstyle
        DB.__init__(self, db_module, keywords)
        self.supports_multiple_insert = True
        self._sequences = None
        
    def _process_insert_query(self, query, tablename, seqname):
        if seqname is None:
            # when seqname is not provided guess the seqname and make sure it exists
            seqname = tablename + "_id_seq"
            if seqname not in self._get_all_sequences():
                seqname = None
        
        if seqname:
            query += "; SELECT currval('%s')" % seqname
            
        return query
    
    def _get_all_sequences(self):
        """Query postgres to find names of all sequences used in this database."""
        if self._sequences is None:
            q = "SELECT c.relname FROM pg_class c WHERE c.relkind = 'S'"
            self._sequences = set([c.relname for c in self.query(q)])
        return self._sequences

    def _connect(self, keywords):
        conn = DB._connect(self, keywords)
        try:
            conn.set_client_encoding('UTF8')
        except AttributeError:
            # fallback for pgdb driver
            conn.cursor().execute("set client_encoding to 'UTF-8'")
        return conn
        
    def _connect_with_pooling(self, keywords):
        conn = DB._connect_with_pooling(self, keywords)
        conn._con._con.set_client_encoding('UTF8')
        return conn

class MySQLDB(DB): 
    def __init__(self, **keywords):
        import MySQLdb as db
        if 'pw' in keywords:
            keywords['passwd'] = keywords['pw']
            del keywords['pw']

        if 'charset' not in keywords:
            keywords['charset'] = 'utf8'
        elif keywords['charset'] is None:
            del keywords['charset']

        self.paramstyle = db.paramstyle = 'pyformat' # it's both, like psycopg
        self.dbname = "mysql"
        DB.__init__(self, db, keywords)
        self.supports_multiple_insert = True
        
    def _process_insert_query(self, query, tablename, seqname):
        return query, SQLQuery('SELECT last_insert_id();')
        
    def _get_insert_default_values_query(self, table):
        return "INSERT INTO %s () VALUES()" % table

def import_driver(drivers, preferred=None):
    """Import the first available driver or preferred driver.
    """
    if preferred:
        drivers = [preferred]

    for d in drivers:
        try:
            return __import__(d, None, None, ['x'])
        except ImportError:
            pass
    raise ImportError("Unable to import " + " or ".join(drivers))

class SqliteDB(DB): 
    def __init__(self, **keywords):
        db = import_driver(["sqlite3", "pysqlite2.dbapi2", "sqlite"], preferred=keywords.pop('driver', None))

        if db.__name__ in ["sqlite3", "pysqlite2.dbapi2"]:
            db.paramstyle = 'qmark'
            
        # sqlite driver doesn't create datatime objects for timestamp columns unless `detect_types` option is passed.
        # It seems to be supported in sqlite3 and pysqlite2 drivers, not surte about sqlite.
        keywords.setdefault('detect_types', db.PARSE_DECLTYPES)

        self.paramstyle = db.paramstyle
        keywords['database'] = keywords.pop('db')
        keywords['pooling'] = False # sqlite don't allows connections to be shared by threads
        self.dbname = "sqlite"        
        DB.__init__(self, db, keywords)

    def _process_insert_query(self, query, tablename, seqname):
        return query, SQLQuery('SELECT last_insert_rowid();')
    
    def query(self, *a, **kw):
        out = DB.query(self, *a, **kw)
        if isinstance(out, iterbetter):
            del out.__len__
        return out

class FirebirdDB(DB):
    """Firebird Database.
    """
    def __init__(self, **keywords):
        try:
            import kinterbasdb as db
        except Exception:
            db = None
            pass
        if 'pw' in keywords:
            keywords['passwd'] = keywords['pw']
            del keywords['pw']
        keywords['database'] = keywords['db']
        del keywords['db']
        DB.__init__(self, db, keywords)
        
    def delete(self, table, where=None, using=None, vars=None, _test=False):
        # firebird doesn't support using clause
        using=None
        return DB.delete(self, table, where, using, vars, _test)

    def sql_clauses(self, what, tables, where, group, order, limit, offset):
        return (
            ('SELECT', ''),
            ('FIRST', limit),
            ('SKIP', offset),
            ('', what),
            ('FROM', sqllist(tables)),
            ('WHERE', where),
            ('GROUP BY', group),
            ('ORDER BY', order)
        )

class MSSQLDB(DB):
    def __init__(self, **keywords):
        import pymssql as db    
        if 'pw' in keywords:
            keywords['password'] = keywords.pop('pw')
        keywords['database'] = keywords.pop('db')
        self.dbname = "mssql"
        DB.__init__(self, db, keywords)

    def _process_query(self, sql_query):
        """Takes the SQLQuery object and returns query string and parameters.
        """
        # MSSQLDB expects params to be a tuple. 
        # Overwriting the default implementation to convert params to tuple.
        paramstyle = getattr(self, 'paramstyle', 'pyformat')
        query = sql_query.query(paramstyle)
        params = sql_query.values()
        return query, tuple(params)

    def sql_clauses(self, what, tables, where, group, order, limit, offset): 
        return (
            ('SELECT', what),
            ('TOP', limit),
            ('FROM', sqllist(tables)),
            ('WHERE', where),
            ('GROUP BY', group),
            ('ORDER BY', order),
            ('OFFSET', offset))
            
    def _test(self):
        """Test LIMIT.

            Fake presence of pymssql module for running tests.
            >>> import sys
            >>> sys.modules['pymssql'] = sys.modules['sys']
            
            MSSQL has TOP clause instead of LIMIT clause.
            >>> db = MSSQLDB(db='test', user='joe', pw='secret')
            >>> db.select('foo', limit=4, _test=True)
            <sql: 'SELECT * TOP 4 FROM foo'>
        """
        pass

class OracleDB(DB): 
    def __init__(self, **keywords): 
        import cx_Oracle as db 
        if 'pw' in keywords: 
            keywords['password'] = keywords.pop('pw') 

        #@@ TODO: use db.makedsn if host, port is specified 
        keywords['dsn'] = keywords.pop('db') 
        self.dbname = 'oracle' 
        db.paramstyle = 'numeric' 
        self.paramstyle = db.paramstyle

        # oracle doesn't support pooling 
        keywords.pop('pooling', None) 
        DB.__init__(self, db, keywords) 

    def _process_insert_query(self, query, tablename, seqname): 
        if seqname is None: 
            # It is not possible to get seq name from table name in Oracle
            return query
        else:
            return query + "; SELECT %s.currval FROM dual" % seqname 

_databases = {}
def database(dburl=None, **params):
    """Creates appropriate database using params.
    
    Pooling will be enabled if DBUtils module is available. 
    Pooling can be disabled by passing pooling=False in params.
    """
    dbn = params.pop('dbn')
    if dbn in _databases:
        return _databases[dbn](**params)
    else:
        raise UnknownDB, dbn

def register_database(name, clazz):
    """
    Register a database.

        >>> class LegacyDB(DB): 
        ...     def __init__(self, **params): 
        ...        pass 
        ...
        >>> register_database('legacy', LegacyDB)
        >>> db = database(dbn='legacy', db='test', user='joe', passwd='secret') 
    """
    _databases[name] = clazz

register_database('mysql', MySQLDB)
register_database('postgres', PostgresDB)
register_database('sqlite', SqliteDB)
register_database('firebird', FirebirdDB)
register_database('mssql', MSSQLDB)
register_database('oracle', OracleDB)

def _interpolate(format): 
    """
    Takes a format string and returns a list of 2-tuples of the form
    (boolean, string) where boolean says whether string should be evaled
    or not.

    from <http://lfw.org/python/Itpl.py> (public domain, Ka-Ping Yee)
    """
    from tokenize import tokenprog

    def matchorfail(text, pos):
        match = tokenprog.match(text, pos)
        if match is None:
            raise _ItplError(text, pos)
        return match, match.end()

    namechars = "abcdefghijklmnopqrstuvwxyz" \
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_";
    chunks = []
    pos = 0

    while 1:
        dollar = format.find("$", pos)
        if dollar < 0: 
            break
        nextchar = format[dollar + 1]

        if nextchar == "{":
            chunks.append((0, format[pos:dollar]))
            pos, level = dollar + 2, 1
            while level:
                match, pos = matchorfail(format, pos)
                tstart, tend = match.regs[3]
                token = format[tstart:tend]
                if token == "{": 
                    level = level + 1
                elif token == "}":  
                    level = level - 1
            chunks.append((1, format[dollar + 2:pos - 1]))

        elif nextchar in namechars:
            chunks.append((0, format[pos:dollar]))
            match, pos = matchorfail(format, dollar + 1)
            while pos < len(format):
                if format[pos] == "." and \
                    pos + 1 < len(format) and format[pos + 1] in namechars:
                    match, pos = matchorfail(format, pos + 1)
                elif format[pos] in "([":
                    pos, level = pos + 1, 1
                    while level:
                        match, pos = matchorfail(format, pos)
                        tstart, tend = match.regs[3]
                        token = format[tstart:tend]
                        if token[0] in "([": 
                            level = level + 1
                        elif token[0] in ")]":  
                            level = level - 1
                else: 
                    break
            chunks.append((1, format[dollar + 1:pos]))
        else:
            chunks.append((0, format[pos:dollar + 1]))
            pos = dollar + 1 + (nextchar == "$")

    if pos < len(format): 
        chunks.append((0, format[pos:]))
    return chunks

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = debugerror
"""
pretty debug errors
(part of web.py)

portions adapted from Django <djangoproject.com> 
Copyright (c) 2005, the Lawrence Journal-World
Used under the modified BSD license:
http://www.xfree86.org/3.3.6/COPYRIGHT2.html#5
"""

__all__ = ["debugerror", "djangoerror", "emailerrors"]

import sys, urlparse, pprint, traceback
from template import Template
from net import websafe
from utils import sendmail, safestr
import webapi as web

import os, os.path
whereami = os.path.join(os.getcwd(), __file__)
whereami = os.path.sep.join(whereami.split(os.path.sep)[:-1])
djangoerror_t = """\
$def with (exception_type, exception_value, frames)
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html lang="en">
<head>
  <meta http-equiv="content-type" content="text/html; charset=utf-8" />
  <meta name="robots" content="NONE,NOARCHIVE" />
  <title>$exception_type at $ctx.path</title>
  <style type="text/css">
    html * { padding:0; margin:0; }
    body * { padding:10px 20px; }
    body * * { padding:0; }
    body { font:small sans-serif; }
    body>div { border-bottom:1px solid #ddd; }
    h1 { font-weight:normal; }
    h2 { margin-bottom:.8em; }
    h2 span { font-size:80%; color:#666; font-weight:normal; }
    h3 { margin:1em 0 .5em 0; }
    h4 { margin:0 0 .5em 0; font-weight: normal; }
    table { 
        border:1px solid #ccc; border-collapse: collapse; background:white; }
    tbody td, tbody th { vertical-align:top; padding:2px 3px; }
    thead th { 
        padding:1px 6px 1px 3px; background:#fefefe; text-align:left; 
        font-weight:normal; font-size:11px; border:1px solid #ddd; }
    tbody th { text-align:right; color:#666; padding-right:.5em; }
    table.vars { margin:5px 0 2px 40px; }
    table.vars td, table.req td { font-family:monospace; }
    table td.code { width:100%;}
    table td.code div { overflow:hidden; }
    table.source th { color:#666; }
    table.source td { 
        font-family:monospace; white-space:pre; border-bottom:1px solid #eee; }
    ul.traceback { list-style-type:none; }
    ul.traceback li.frame { margin-bottom:1em; }
    div.context { margin: 10px 0; }
    div.context ol { 
        padding-left:30px; margin:0 10px; list-style-position: inside; }
    div.context ol li { 
        font-family:monospace; white-space:pre; color:#666; cursor:pointer; }
    div.context ol.context-line li { color:black; background-color:#ccc; }
    div.context ol.context-line li span { float: right; }
    div.commands { margin-left: 40px; }
    div.commands a { color:black; text-decoration:none; }
    #summary { background: #ffc; }
    #summary h2 { font-weight: normal; color: #666; }
    #explanation { background:#eee; }
    #template, #template-not-exist { background:#f6f6f6; }
    #template-not-exist ul { margin: 0 0 0 20px; }
    #traceback { background:#eee; }
    #requestinfo { background:#f6f6f6; padding-left:120px; }
    #summary table { border:none; background:transparent; }
    #requestinfo h2, #requestinfo h3 { position:relative; margin-left:-100px; }
    #requestinfo h3 { margin-bottom:-1em; }
    .error { background: #ffc; }
    .specific { color:#cc3300; font-weight:bold; }
  </style>
  <script type="text/javascript">
  //<!--
    function getElementsByClassName(oElm, strTagName, strClassName){
        // Written by Jonathan Snook, http://www.snook.ca/jon; 
        // Add-ons by Robert Nyman, http://www.robertnyman.com
        var arrElements = (strTagName == "*" && document.all)? document.all :
        oElm.getElementsByTagName(strTagName);
        var arrReturnElements = new Array();
        strClassName = strClassName.replace(/\-/g, "\\-");
        var oRegExp = new RegExp("(^|\\s)" + strClassName + "(\\s|$$)");
        var oElement;
        for(var i=0; i<arrElements.length; i++){
            oElement = arrElements[i];
            if(oRegExp.test(oElement.className)){
                arrReturnElements.push(oElement);
            }
        }
        return (arrReturnElements)
    }
    function hideAll(elems) {
      for (var e = 0; e < elems.length; e++) {
        elems[e].style.display = 'none';
      }
    }
    window.onload = function() {
      hideAll(getElementsByClassName(document, 'table', 'vars'));
      hideAll(getElementsByClassName(document, 'ol', 'pre-context'));
      hideAll(getElementsByClassName(document, 'ol', 'post-context'));
    }
    function toggle() {
      for (var i = 0; i < arguments.length; i++) {
        var e = document.getElementById(arguments[i]);
        if (e) {
          e.style.display = e.style.display == 'none' ? 'block' : 'none';
        }
      }
      return false;
    }
    function varToggle(link, id) {
      toggle('v' + id);
      var s = link.getElementsByTagName('span')[0];
      var uarr = String.fromCharCode(0x25b6);
      var darr = String.fromCharCode(0x25bc);
      s.innerHTML = s.innerHTML == uarr ? darr : uarr;
      return false;
    }
    //-->
  </script>
</head>
<body>

$def dicttable (d, kls='req', id=None):
    $ items = d and d.items() or []
    $items.sort()
    $:dicttable_items(items, kls, id)
        
$def dicttable_items(items, kls='req', id=None):
    $if items:
        <table class="$kls"
        $if id: id="$id"
        ><thead><tr><th>Variable</th><th>Value</th></tr></thead>
        <tbody>
        $for k, v in items:
            <tr><td>$k</td><td class="code"><div>$prettify(v)</div></td></tr>
        </tbody>
        </table>
    $else:
        <p>No data.</p>

<div id="summary">
  <h1>$exception_type at $ctx.path</h1>
  <h2>$exception_value</h2>
  <table><tr>
    <th>Python</th>
    <td>$frames[0].filename in $frames[0].function, line $frames[0].lineno</td>
  </tr><tr>
    <th>Web</th>
    <td>$ctx.method $ctx.home$ctx.path</td>
  </tr></table>
</div>
<div id="traceback">
<h2>Traceback <span>(innermost first)</span></h2>
<ul class="traceback">
$for frame in frames:
    <li class="frame">
    <code>$frame.filename</code> in <code>$frame.function</code>
    $if frame.context_line is not None:
        <div class="context" id="c$frame.id">
        $if frame.pre_context:
            <ol start="$frame.pre_context_lineno" class="pre-context" id="pre$frame.id">
            $for line in frame.pre_context:
                <li onclick="toggle('pre$frame.id', 'post$frame.id')">$line</li>
            </ol>
            <ol start="$frame.lineno" class="context-line"><li onclick="toggle('pre$frame.id', 'post$frame.id')">$frame.context_line <span>...</span></li></ol>
        $if frame.post_context:
            <ol start='${frame.lineno + 1}' class="post-context" id="post$frame.id">
            $for line in frame.post_context:
                <li onclick="toggle('pre$frame.id', 'post$frame.id')">$line</li>
            </ol>
      </div>
    
    $if frame.vars:
        <div class="commands">
        <a href='#' onclick="return varToggle(this, '$frame.id')"><span>&#x25b6;</span> Local vars</a>
        $# $inspect.formatargvalues(*inspect.getargvalues(frame['tb'].tb_frame))
        </div>
        $:dicttable(frame.vars, kls='vars', id=('v' + str(frame.id)))
      </li>
  </ul>
</div>

<div id="requestinfo">
$if ctx.output or ctx.headers:
    <h2>Response so far</h2>
    <h3>HEADERS</h3>
    $:dicttable_items(ctx.headers)

    <h3>BODY</h3>
    <p class="req" style="padding-bottom: 2em"><code>
    $ctx.output
    </code></p>
  
<h2>Request information</h2>

<h3>INPUT</h3>
$:dicttable(web.input(_unicode=False))

<h3 id="cookie-info">COOKIES</h3>
$:dicttable(web.cookies())

<h3 id="meta-info">META</h3>
$ newctx = [(k, v) for (k, v) in ctx.iteritems() if not k.startswith('_') and not isinstance(v, dict)]
$:dicttable(dict(newctx))

<h3 id="meta-info">ENVIRONMENT</h3>
$:dicttable(ctx.env)
</div>

<div id="explanation">
  <p>
    You're seeing this error because you have <code>web.config.debug</code>
    set to <code>True</code>. Set that to <code>False</code> if you don't want to see this.
  </p>
</div>

</body>
</html>
"""

djangoerror_r = None

def djangoerror():
    def _get_lines_from_file(filename, lineno, context_lines):
        """
        Returns context_lines before and after lineno from file.
        Returns (pre_context_lineno, pre_context, context_line, post_context).
        """
        try:
            source = open(filename).readlines()
            lower_bound = max(0, lineno - context_lines)
            upper_bound = lineno + context_lines

            pre_context = \
                [line.strip('\n') for line in source[lower_bound:lineno]]
            context_line = source[lineno].strip('\n')
            post_context = \
                [line.strip('\n') for line in source[lineno + 1:upper_bound]]

            return lower_bound, pre_context, context_line, post_context
        except (OSError, IOError, IndexError):
            return None, [], None, []    
    
    exception_type, exception_value, tback = sys.exc_info()
    frames = []
    while tback is not None:
        filename = tback.tb_frame.f_code.co_filename
        function = tback.tb_frame.f_code.co_name
        lineno = tback.tb_lineno - 1

        # hack to get correct line number for templates
        lineno += tback.tb_frame.f_locals.get("__lineoffset__", 0)
        
        pre_context_lineno, pre_context, context_line, post_context = \
            _get_lines_from_file(filename, lineno, 7)

        if '__hidetraceback__' not in tback.tb_frame.f_locals:
            frames.append(web.storage({
                'tback': tback,
                'filename': filename,
                'function': function,
                'lineno': lineno,
                'vars': tback.tb_frame.f_locals,
                'id': id(tback),
                'pre_context': pre_context,
                'context_line': context_line,
                'post_context': post_context,
                'pre_context_lineno': pre_context_lineno,
            }))
        tback = tback.tb_next
    frames.reverse()
    urljoin = urlparse.urljoin
    def prettify(x):
        try: 
            out = pprint.pformat(x)
        except Exception, e: 
            out = '[could not display: <' + e.__class__.__name__ + \
                  ': '+str(e)+'>]'
        return out
        
    global djangoerror_r
    if djangoerror_r is None:
        djangoerror_r = Template(djangoerror_t, filename=__file__, filter=websafe)
        
    t = djangoerror_r
    globals = {'ctx': web.ctx, 'web':web, 'dict':dict, 'str':str, 'prettify': prettify}
    t.t.func_globals.update(globals)
    return t(exception_type, exception_value, frames)

def debugerror():
    """
    A replacement for `internalerror` that presents a nice page with lots
    of debug information for the programmer.

    (Based on the beautiful 500 page from [Django](http://djangoproject.com/), 
    designed by [Wilson Miner](http://wilsonminer.com/).)
    """
    return web._InternalError(djangoerror())

def emailerrors(to_address, olderror, from_address=None):
    """
    Wraps the old `internalerror` handler (pass as `olderror`) to 
    additionally email all errors to `to_address`, to aid in
    debugging production websites.
    
    Emails contain a normal text traceback as well as an
    attachment containing the nice `debugerror` page.
    """
    from_address = from_address or to_address

    def emailerrors_internal():
        error = olderror()
        tb = sys.exc_info()
        error_name = tb[0]
        error_value = tb[1]
        tb_txt = ''.join(traceback.format_exception(*tb))
        path = web.ctx.path
        request = web.ctx.method + ' ' + web.ctx.home + web.ctx.fullpath
        
        message = "\n%s\n\n%s\n\n" % (request, tb_txt)
        
        sendmail(
            "your buggy site <%s>" % from_address,
            "the bugfixer <%s>" % to_address,
            "bug: %(error_name)s: %(error_value)s (%(path)s)" % locals(),
            message,
            attachments=[
                dict(filename="bug.html", content=safestr(djangoerror()))
            ],
        )
        return error
    
    return emailerrors_internal

if __name__ == "__main__":
    urls = (
        '/', 'index'
    )
    from application import application
    app = application(urls, globals())
    app.internalerror = debugerror
    
    class index:
        def GET(self):
            thisdoesnotexist

    app.run()

########NEW FILE########
__FILENAME__ = form
"""
HTML forms
(part of web.py)
"""

import copy, re
import webapi as web
import utils, net

def attrget(obj, attr, value=None):
    try:
        if hasattr(obj, 'has_key') and obj.has_key(attr): 
            return obj[attr]
    except TypeError:
        # Handle the case where has_key takes different number of arguments.
        # This is the case with Model objects on appengine. See #134
        pass
    if hasattr(obj, attr):
        return getattr(obj, attr)
    return value

class Form(object):
    r"""
    HTML form.
    
        >>> f = Form(Textbox("x"))
        >>> f.render()
        u'<table>\n    <tr><th><label for="x">x</label></th><td><input type="text" id="x" name="x"/></td></tr>\n</table>'
    """
    def __init__(self, *inputs, **kw):
        self.inputs = inputs
        self.valid = True
        self.note = None
        self.validators = kw.pop('validators', [])

    def __call__(self, x=None):
        o = copy.deepcopy(self)
        if x: o.validates(x)
        return o
    
    def render(self):
        out = ''
        out += self.rendernote(self.note)
        out += '<table>\n'
        
        for i in self.inputs:
            html = utils.safeunicode(i.pre) + i.render() + self.rendernote(i.note) + utils.safeunicode(i.post)
            if i.is_hidden():
                out += '    <tr style="display: none;"><th></th><td>%s</td></tr>\n' % (html)
            else:
                out += '    <tr><th><label for="%s">%s</label></th><td>%s</td></tr>\n' % (i.id, net.websafe(i.description), html)
        out += "</table>"
        return out
        
    def render_css(self): 
        out = [] 
        out.append(self.rendernote(self.note)) 
        for i in self.inputs:
            if not i.is_hidden():
                out.append('<label for="%s">%s</label>' % (i.id, net.websafe(i.description))) 
            out.append(i.pre)
            out.append(i.render()) 
            out.append(self.rendernote(i.note))
            out.append(i.post) 
            out.append('\n')
        return ''.join(out) 
        
    def rendernote(self, note):
        if note: return '<strong class="wrong">%s</strong>' % net.websafe(note)
        else: return ""
    
    def validates(self, source=None, _validate=True, **kw):
        source = source or kw or web.input()
        out = True
        for i in self.inputs:
            v = attrget(source, i.name)
            if _validate:
                out = i.validate(v) and out
            else:
                i.set_value(v)
        if _validate:
            out = out and self._validate(source)
            self.valid = out
        return out

    def _validate(self, value):
        self.value = value
        for v in self.validators:
            if not v.valid(value):
                self.note = v.msg
                return False
        return True

    def fill(self, source=None, **kw):
        return self.validates(source, _validate=False, **kw)
    
    def __getitem__(self, i):
        for x in self.inputs:
            if x.name == i: return x
        raise KeyError, i

    def __getattr__(self, name):
        # don't interfere with deepcopy
        inputs = self.__dict__.get('inputs') or []
        for x in inputs:
            if x.name == name: return x
        raise AttributeError, name
    
    def get(self, i, default=None):
        try:
            return self[i]
        except KeyError:
            return default
            
    def _get_d(self): #@@ should really be form.attr, no?
        return utils.storage([(i.name, i.get_value()) for i in self.inputs])
    d = property(_get_d)

class Input(object):
    def __init__(self, name, *validators, **attrs):
        self.name = name
        self.validators = validators
        self.attrs = attrs = AttributeList(attrs)
        
        self.description = attrs.pop('description', name)
        self.value = attrs.pop('value', None)
        self.pre = attrs.pop('pre', "")
        self.post = attrs.pop('post', "")
        self.note = None
        
        self.id = attrs.setdefault('id', self.get_default_id())
        
        if 'class_' in attrs:
            attrs['class'] = attrs['class_']
            del attrs['class_']
        
    def is_hidden(self):
        return False
        
    def get_type(self):
        raise NotImplementedError
        
    def get_default_id(self):
        return self.name

    def validate(self, value):
        self.set_value(value)

        for v in self.validators:
            if not v.valid(value):
                self.note = v.msg
                return False
        return True

    def set_value(self, value):
        self.value = value

    def get_value(self):
        return self.value

    def render(self):
        attrs = self.attrs.copy()
        attrs['type'] = self.get_type()
        if self.value is not None:
            attrs['value'] = self.value
        attrs['name'] = self.name
        return '<input %s/>' % attrs

    def rendernote(self, note):
        if note: return '<strong class="wrong">%s</strong>' % net.websafe(note)
        else: return ""
        
    def addatts(self):
        # add leading space for backward-compatibility
        return " " + str(self.attrs)

class AttributeList(dict):
    """List of atributes of input.
    
    >>> a = AttributeList(type='text', name='x', value=20)
    >>> a
    <attrs: 'type="text" name="x" value="20"'>
    """
    def copy(self):
        return AttributeList(self)
        
    def __str__(self):
        return " ".join(['%s="%s"' % (k, net.websafe(v)) for k, v in self.items()])
        
    def __repr__(self):
        return '<attrs: %s>' % repr(str(self))

class Textbox(Input):
    """Textbox input.
    
        >>> Textbox(name='foo', value='bar').render()
        u'<input type="text" id="foo" value="bar" name="foo"/>'
        >>> Textbox(name='foo', value=0).render()
        u'<input type="text" id="foo" value="0" name="foo"/>'
    """        
    def get_type(self):
        return 'text'

class Password(Input):
    """Password input.

        >>> Password(name='password', value='secret').render()
        u'<input type="password" id="password" value="secret" name="password"/>'
    """
    
    def get_type(self):
        return 'password'

class Textarea(Input):
    """Textarea input.
    
        >>> Textarea(name='foo', value='bar').render()
        u'<textarea id="foo" name="foo">bar</textarea>'
    """
    def render(self):
        attrs = self.attrs.copy()
        attrs['name'] = self.name
        value = net.websafe(self.value or '')
        return '<textarea %s>%s</textarea>' % (attrs, value)

class Dropdown(Input):
    r"""Dropdown/select input.
    
        >>> Dropdown(name='foo', args=['a', 'b', 'c'], value='b').render()
        u'<select id="foo" name="foo">\n  <option value="a">a</option>\n  <option selected="selected" value="b">b</option>\n  <option value="c">c</option>\n</select>\n'
        >>> Dropdown(name='foo', args=[('a', 'aa'), ('b', 'bb'), ('c', 'cc')], value='b').render()
        u'<select id="foo" name="foo">\n  <option value="a">aa</option>\n  <option selected="selected" value="b">bb</option>\n  <option value="c">cc</option>\n</select>\n'
    """
    def __init__(self, name, args, *validators, **attrs):
        self.args = args
        super(Dropdown, self).__init__(name, *validators, **attrs)

    def render(self):
        attrs = self.attrs.copy()
        attrs['name'] = self.name
        
        x = '<select %s>\n' % attrs
        
        for arg in self.args:
            x += self._render_option(arg)

        x += '</select>\n'
        return x

    def _render_option(self, arg, indent='  '):
        if isinstance(arg, (tuple, list)):
            value, desc= arg
        else:
            value, desc = arg, arg 

        if self.value == value or (isinstance(self.value, list) and value in self.value):
            select_p = ' selected="selected"'
        else:
            select_p = ''
        return indent + '<option%s value="%s">%s</option>\n' % (select_p, net.websafe(value), net.websafe(desc))
        

class GroupedDropdown(Dropdown):
    r"""Grouped Dropdown/select input.
    
        >>> GroupedDropdown(name='car_type', args=(('Swedish Cars', ('Volvo', 'Saab')), ('German Cars', ('Mercedes', 'Audi'))), value='Audi').render()
        u'<select id="car_type" name="car_type">\n  <optgroup label="Swedish Cars">\n    <option value="Volvo">Volvo</option>\n    <option value="Saab">Saab</option>\n  </optgroup>\n  <optgroup label="German Cars">\n    <option value="Mercedes">Mercedes</option>\n    <option selected="selected" value="Audi">Audi</option>\n  </optgroup>\n</select>\n'
        >>> GroupedDropdown(name='car_type', args=(('Swedish Cars', (('v', 'Volvo'), ('s', 'Saab'))), ('German Cars', (('m', 'Mercedes'), ('a', 'Audi')))), value='a').render()
        u'<select id="car_type" name="car_type">\n  <optgroup label="Swedish Cars">\n    <option value="v">Volvo</option>\n    <option value="s">Saab</option>\n  </optgroup>\n  <optgroup label="German Cars">\n    <option value="m">Mercedes</option>\n    <option selected="selected" value="a">Audi</option>\n  </optgroup>\n</select>\n'

    """
    def __init__(self, name, args, *validators, **attrs):
        self.args = args
        super(Dropdown, self).__init__(name, *validators, **attrs)

    def render(self):
        attrs = self.attrs.copy()
        attrs['name'] = self.name
        
        x = '<select %s>\n' % attrs
        
        for label, options in self.args:
            x += '  <optgroup label="%s">\n' % net.websafe(label)
            for arg in options:
                x += self._render_option(arg, indent = '    ')
            x +=  '  </optgroup>\n'
            
        x += '</select>\n'
        return x

class Radio(Input):
    def __init__(self, name, args, *validators, **attrs):
        self.args = args
        super(Radio, self).__init__(name, *validators, **attrs)

    def render(self):
        x = '<span>'
        for arg in self.args:
            if isinstance(arg, (tuple, list)):
                value, desc= arg
            else:
                value, desc = arg, arg 
            attrs = self.attrs.copy()
            attrs['name'] = self.name
            attrs['type'] = 'radio'
            attrs['value'] = value
            if self.value == value:
                attrs['checked'] = 'checked'
            x += '<input %s/> %s' % (attrs, net.websafe(desc))
        x += '</span>'
        return x

class Checkbox(Input):
    """Checkbox input.

    >>> Checkbox('foo', value='bar', checked=True).render()
    u'<input checked="checked" type="checkbox" id="foo_bar" value="bar" name="foo"/>'
    >>> Checkbox('foo', value='bar').render()
    u'<input type="checkbox" id="foo_bar" value="bar" name="foo"/>'
    >>> c = Checkbox('foo', value='bar')
    >>> c.validate('on')
    True
    >>> c.render()
    u'<input checked="checked" type="checkbox" id="foo_bar" value="bar" name="foo"/>'
    """
    def __init__(self, name, *validators, **attrs):
        self.checked = attrs.pop('checked', False)
        Input.__init__(self, name, *validators, **attrs)
        
    def get_default_id(self):
        value = utils.safestr(self.value or "")
        return self.name + '_' + value.replace(' ', '_')

    def render(self):
        attrs = self.attrs.copy()
        attrs['type'] = 'checkbox'
        attrs['name'] = self.name
        attrs['value'] = self.value

        if self.checked:
            attrs['checked'] = 'checked'            
        return '<input %s/>' % attrs

    def set_value(self, value):
        self.checked = bool(value)

    def get_value(self):
        return self.checked

class Button(Input):
    """HTML Button.
    
    >>> Button("save").render()
    u'<button id="save" name="save">save</button>'
    >>> Button("action", value="save", html="<b>Save Changes</b>").render()
    u'<button id="action" value="save" name="action"><b>Save Changes</b></button>'
    """
    def __init__(self, name, *validators, **attrs):
        super(Button, self).__init__(name, *validators, **attrs)
        self.description = ""

    def render(self):
        attrs = self.attrs.copy()
        attrs['name'] = self.name
        if self.value is not None:
            attrs['value'] = self.value
        html = attrs.pop('html', None) or net.websafe(self.name)
        return '<button %s>%s</button>' % (attrs, html)

class Hidden(Input):
    """Hidden Input.
    
        >>> Hidden(name='foo', value='bar').render()
        u'<input type="hidden" id="foo" value="bar" name="foo"/>'
    """
    def is_hidden(self):
        return True
        
    def get_type(self):
        return 'hidden'

class File(Input):
    """File input.
    
        >>> File(name='f').render()
        u'<input type="file" id="f" name="f"/>'
    """
    def get_type(self):
        return 'file'
    
class Validator:
    def __deepcopy__(self, memo): return copy.copy(self)
    def __init__(self, msg, test, jstest=None): utils.autoassign(self, locals())
    def valid(self, value): 
        try: return self.test(value)
        except: return False

notnull = Validator("Required", bool)

class regexp(Validator):
    def __init__(self, rexp, msg):
        self.rexp = re.compile(rexp)
        self.msg = msg
    
    def valid(self, value):
        return bool(self.rexp.match(value))

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = http
"""
HTTP Utilities
(from web.py)
"""

__all__ = [
  "expires", "lastmodified", 
  "prefixurl", "modified", 
  "changequery", "url",
  "profiler",
]

import sys, os, threading, urllib, urlparse
try: import datetime
except ImportError: pass
import net, utils, webapi as web

def prefixurl(base=''):
    """
    Sorry, this function is really difficult to explain.
    Maybe some other time.
    """
    url = web.ctx.path.lstrip('/')
    for i in xrange(url.count('/')): 
        base += '../'
    if not base: 
        base = './'
    return base

def expires(delta):
    """
    Outputs an `Expires` header for `delta` from now. 
    `delta` is a `timedelta` object or a number of seconds.
    """
    if isinstance(delta, (int, long)):
        delta = datetime.timedelta(seconds=delta)
    date_obj = datetime.datetime.utcnow() + delta
    web.header('Expires', net.httpdate(date_obj))

def lastmodified(date_obj):
    """Outputs a `Last-Modified` header for `datetime`."""
    web.header('Last-Modified', net.httpdate(date_obj))

def modified(date=None, etag=None):
    """
    Checks to see if the page has been modified since the version in the
    requester's cache.
    
    When you publish pages, you can include `Last-Modified` and `ETag`
    with the date the page was last modified and an opaque token for
    the particular version, respectively. When readers reload the page, 
    the browser sends along the modification date and etag value for
    the version it has in its cache. If the page hasn't changed, 
    the server can just return `304 Not Modified` and not have to 
    send the whole page again.
    
    This function takes the last-modified date `date` and the ETag `etag`
    and checks the headers to see if they match. If they do, it returns 
    `True`, or otherwise it raises NotModified error. It also sets 
    `Last-Modified` and `ETag` output headers.
    """
    try:
        from __builtin__ import set
    except ImportError:
        # for python 2.3
        from sets import Set as set

    n = set([x.strip('" ') for x in web.ctx.env.get('HTTP_IF_NONE_MATCH', '').split(',')])
    m = net.parsehttpdate(web.ctx.env.get('HTTP_IF_MODIFIED_SINCE', '').split(';')[0])
    validate = False
    if etag:
        if '*' in n or etag in n:
            validate = True
    if date and m:
        # we subtract a second because 
        # HTTP dates don't have sub-second precision
        if date-datetime.timedelta(seconds=1) <= m:
            validate = True
    
    if date: lastmodified(date)
    if etag: web.header('ETag', '"' + etag + '"')
    if validate:
        raise web.notmodified()
    else:
        return True

def urlencode(query, doseq=0):
    """
    Same as urllib.urlencode, but supports unicode strings.
    
        >>> urlencode({'text':'foo bar'})
        'text=foo+bar'
        >>> urlencode({'x': [1, 2]}, doseq=True)
        'x=1&x=2'
    """
    def convert(value, doseq=False):
        if doseq and isinstance(value, list):
            return [convert(v) for v in value]
        else:
            return utils.safestr(value)
        
    query = dict([(k, convert(v, doseq)) for k, v in query.items()])
    return urllib.urlencode(query, doseq=doseq)

def changequery(query=None, **kw):
    """
    Imagine you're at `/foo?a=1&b=2`. Then `changequery(a=3)` will return
    `/foo?a=3&b=2` -- the same URL but with the arguments you requested
    changed.
    """
    if query is None:
        query = web.rawinput(method='get')
    for k, v in kw.iteritems():
        if v is None:
            query.pop(k, None)
        else:
            query[k] = v
    out = web.ctx.path
    if query:
        out += '?' + urlencode(query, doseq=True)
    return out

def url(path=None, doseq=False, **kw):
    """
    Makes url by concatenating web.ctx.homepath and path and the 
    query string created using the arguments.
    """
    if path is None:
        path = web.ctx.path
    if path.startswith("/"):
        out = web.ctx.homepath + path
    else:
        out = path

    if kw:
        out += '?' + urlencode(kw, doseq=doseq)
    
    return out

def profiler(app):
    """Outputs basic profiling information at the bottom of each response."""
    from utils import profile
    def profile_internal(e, o):
        out, result = profile(app)(e, o)
        return list(out) + ['<pre>' + net.websafe(result) + '</pre>']
    return profile_internal

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = httpserver
__all__ = ["runsimple"]

import sys, os
from SimpleHTTPServer import SimpleHTTPRequestHandler
import urllib
import posixpath

import webapi as web
import net
import utils

def runbasic(func, server_address=("0.0.0.0", 8080)):
    """
    Runs a simple HTTP server hosting WSGI app `func`. The directory `static/` 
    is hosted statically.

    Based on [WsgiServer][ws] from [Colin Stewart][cs].
    
  [ws]: http://www.owlfish.com/software/wsgiutils/documentation/wsgi-server-api.html
  [cs]: http://www.owlfish.com/
    """
    # Copyright (c) 2004 Colin Stewart (http://www.owlfish.com/)
    # Modified somewhat for simplicity
    # Used under the modified BSD license:
    # http://www.xfree86.org/3.3.6/COPYRIGHT2.html#5

    import SimpleHTTPServer, SocketServer, BaseHTTPServer, urlparse
    import socket, errno
    import traceback

    class WSGIHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
        def run_wsgi_app(self):
            protocol, host, path, parameters, query, fragment = \
                urlparse.urlparse('http://dummyhost%s' % self.path)

            # we only use path, query
            env = {'wsgi.version': (1, 0)
                   ,'wsgi.url_scheme': 'http'
                   ,'wsgi.input': self.rfile
                   ,'wsgi.errors': sys.stderr
                   ,'wsgi.multithread': 1
                   ,'wsgi.multiprocess': 0
                   ,'wsgi.run_once': 0
                   ,'REQUEST_METHOD': self.command
                   ,'REQUEST_URI': self.path
                   ,'PATH_INFO': path
                   ,'QUERY_STRING': query
                   ,'CONTENT_TYPE': self.headers.get('Content-Type', '')
                   ,'CONTENT_LENGTH': self.headers.get('Content-Length', '')
                   ,'REMOTE_ADDR': self.client_address[0]
                   ,'SERVER_NAME': self.server.server_address[0]
                   ,'SERVER_PORT': str(self.server.server_address[1])
                   ,'SERVER_PROTOCOL': self.request_version
                   }

            for http_header, http_value in self.headers.items():
                env ['HTTP_%s' % http_header.replace('-', '_').upper()] = \
                    http_value

            # Setup the state
            self.wsgi_sent_headers = 0
            self.wsgi_headers = []

            try:
                # We have there environment, now invoke the application
                result = self.server.app(env, self.wsgi_start_response)
                try:
                    try:
                        for data in result:
                            if data: 
                                self.wsgi_write_data(data)
                    finally:
                        if hasattr(result, 'close'): 
                            result.close()
                except socket.error, socket_err:
                    # Catch common network errors and suppress them
                    if (socket_err.args[0] in \
                       (errno.ECONNABORTED, errno.EPIPE)): 
                        return
                except socket.timeout, socket_timeout: 
                    return
            except:
                print >> web.debug, traceback.format_exc(),

            if (not self.wsgi_sent_headers):
                # We must write out something!
                self.wsgi_write_data(" ")
            return

        do_POST = run_wsgi_app
        do_PUT = run_wsgi_app
        do_DELETE = run_wsgi_app

        def do_GET(self):
            if self.path.startswith('/static/'):
                SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)
            else:
                self.run_wsgi_app()

        def wsgi_start_response(self, response_status, response_headers, 
                              exc_info=None):
            if (self.wsgi_sent_headers):
                raise Exception \
                      ("Headers already sent and start_response called again!")
            # Should really take a copy to avoid changes in the application....
            self.wsgi_headers = (response_status, response_headers)
            return self.wsgi_write_data

        def wsgi_write_data(self, data):
            if (not self.wsgi_sent_headers):
                status, headers = self.wsgi_headers
                # Need to send header prior to data
                status_code = status[:status.find(' ')]
                status_msg = status[status.find(' ') + 1:]
                self.send_response(int(status_code), status_msg)
                for header, value in headers:
                    self.send_header(header, value)
                self.end_headers()
                self.wsgi_sent_headers = 1
            # Send the data
            self.wfile.write(data)

    class WSGIServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
        def __init__(self, func, server_address):
            BaseHTTPServer.HTTPServer.__init__(self, 
                                               server_address, 
                                               WSGIHandler)
            self.app = func
            self.serverShuttingDown = 0

    print "http://%s:%d/" % server_address
    WSGIServer(func, server_address).serve_forever()

# The WSGIServer instance. 
# Made global so that it can be stopped in embedded mode.
server = None

def runsimple(func, server_address=("0.0.0.0", 8080)):
    """
    Runs [CherryPy][cp] WSGI server hosting WSGI app `func`. 
    The directory `static/` is hosted statically.

    [cp]: http://www.cherrypy.org
    """
    global server
    func = StaticMiddleware(func)
    func = LogMiddleware(func)
    
    server = WSGIServer(server_address, func)

    if server.ssl_adapter:
        print "https://%s:%d/" % server_address
    else:
        print "http://%s:%d/" % server_address

    try:
        server.start()
    except (KeyboardInterrupt, SystemExit):
        server.stop()
        server = None

def WSGIServer(server_address, wsgi_app):
    """Creates CherryPy WSGI server listening at `server_address` to serve `wsgi_app`.
    This function can be overwritten to customize the webserver or use a different webserver.
    """
    import wsgiserver
    
    # Default values of wsgiserver.ssl_adapters uses cherrypy.wsgiserver
    # prefix. Overwriting it make it work with web.wsgiserver.
    wsgiserver.ssl_adapters = {
        'builtin': 'web.wsgiserver.ssl_builtin.BuiltinSSLAdapter',
        'pyopenssl': 'web.wsgiserver.ssl_pyopenssl.pyOpenSSLAdapter',
    }
    
    server = wsgiserver.CherryPyWSGIServer(server_address, wsgi_app, server_name="localhost")
        
    def create_ssl_adapter(cert, key):
        # wsgiserver tries to import submodules as cherrypy.wsgiserver.foo.
        # That doesn't work as not it is web.wsgiserver. 
        # Patching sys.modules temporarily to make it work.
        import types
        cherrypy = types.ModuleType('cherrypy')
        cherrypy.wsgiserver = wsgiserver
        sys.modules['cherrypy'] = cherrypy
        sys.modules['cherrypy.wsgiserver'] = wsgiserver
        
        from wsgiserver.ssl_pyopenssl import pyOpenSSLAdapter
        adapter = pyOpenSSLAdapter(cert, key)
        
        # We are done with our work. Cleanup the patches.
        del sys.modules['cherrypy']
        del sys.modules['cherrypy.wsgiserver']

        return adapter

    # SSL backward compatibility
    if (server.ssl_adapter is None and
        getattr(server, 'ssl_certificate', None) and
        getattr(server, 'ssl_private_key', None)):
        server.ssl_adapter = create_ssl_adapter(server.ssl_certificate, server.ssl_private_key)

    server.nodelay = not sys.platform.startswith('java') # TCP_NODELAY isn't supported on the JVM
    return server

class StaticApp(SimpleHTTPRequestHandler):
    """WSGI application for serving static files."""
    def __init__(self, environ, start_response):
        self.headers = []
        self.environ = environ
        self.start_response = start_response

    def send_response(self, status, msg=""):
        self.status = str(status) + " " + msg

    def send_header(self, name, value):
        self.headers.append((name, value))

    def end_headers(self):
        pass

    def log_message(*a): pass

    def __iter__(self):
        environ = self.environ

        self.path = environ.get('PATH_INFO', '')
        self.client_address = environ.get('REMOTE_ADDR','-'), \
                              environ.get('REMOTE_PORT','-')
        self.command = environ.get('REQUEST_METHOD', '-')

        from cStringIO import StringIO
        self.wfile = StringIO() # for capturing error

        try:
            path = self.translate_path(self.path)
            etag = '"%s"' % os.path.getmtime(path)
            client_etag = environ.get('HTTP_IF_NONE_MATCH')
            self.send_header('ETag', etag)
            if etag == client_etag:
                self.send_response(304, "Not Modified")
                self.start_response(self.status, self.headers)
                raise StopIteration
        except OSError:
            pass # Probably a 404

        f = self.send_head()
        self.start_response(self.status, self.headers)

        if f:
            block_size = 16 * 1024
            while True:
                buf = f.read(block_size)
                if not buf:
                    break
                yield buf
            f.close()
        else:
            value = self.wfile.getvalue()
            yield value

class StaticMiddleware:
    """WSGI middleware for serving static files."""
    def __init__(self, app, prefix='/static/'):
        self.app = app
        self.prefix = prefix
        
    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        path = self.normpath(path)

        if path.startswith(self.prefix):
            return StaticApp(environ, start_response)
        else:
            return self.app(environ, start_response)

    def normpath(self, path):
        path2 = posixpath.normpath(urllib.unquote(path))
        if path.endswith("/"):
            path2 += "/"
        return path2

    
class LogMiddleware:
    """WSGI middleware for logging the status."""
    def __init__(self, app):
        self.app = app
        self.format = '%s - - [%s] "%s %s %s" - %s'
    
        from BaseHTTPServer import BaseHTTPRequestHandler
        import StringIO
        f = StringIO.StringIO()
        
        class FakeSocket:
            def makefile(self, *a):
                return f
        
        # take log_date_time_string method from BaseHTTPRequestHandler
        self.log_date_time_string = BaseHTTPRequestHandler(FakeSocket(), None, None).log_date_time_string
        
    def __call__(self, environ, start_response):
        def xstart_response(status, response_headers, *args):
            out = start_response(status, response_headers, *args)
            self.log(status, environ)
            return out

        return self.app(environ, xstart_response)
             
    def log(self, status, environ):
        outfile = environ.get('wsgi.errors', web.debug)
        req = environ.get('PATH_INFO', '_')
        protocol = environ.get('ACTUAL_SERVER_PROTOCOL', '-')
        method = environ.get('REQUEST_METHOD', '-')
        host = "%s:%s" % (environ.get('REMOTE_ADDR','-'), 
                          environ.get('REMOTE_PORT','-'))

        time = self.log_date_time_string()

        msg = self.format % (host, time, protocol, method, req, status)
        print >> outfile, utils.safestr(msg)

########NEW FILE########
__FILENAME__ = net
"""
Network Utilities
(from web.py)
"""

__all__ = [
  "validipaddr", "validipport", "validip", "validaddr", 
  "urlquote",
  "httpdate", "parsehttpdate", 
  "htmlquote", "htmlunquote", "websafe",
]

import urllib, time
try: import datetime
except ImportError: pass

def validipaddr(address):
    """
    Returns True if `address` is a valid IPv4 address.
    
        >>> validipaddr('192.168.1.1')
        True
        >>> validipaddr('192.168.1.800')
        False
        >>> validipaddr('192.168.1')
        False
    """
    try:
        octets = address.split('.')
        if len(octets) != 4:
            return False
        for x in octets:
            if not (0 <= int(x) <= 255):
                return False
    except ValueError:
        return False
    return True

def validipport(port):
    """
    Returns True if `port` is a valid IPv4 port.
    
        >>> validipport('9000')
        True
        >>> validipport('foo')
        False
        >>> validipport('1000000')
        False
    """
    try:
        if not (0 <= int(port) <= 65535):
            return False
    except ValueError:
        return False
    return True

def validip(ip, defaultaddr="0.0.0.0", defaultport=8080):
    """Returns `(ip_address, port)` from string `ip_addr_port`"""
    addr = defaultaddr
    port = defaultport
    
    ip = ip.split(":", 1)
    if len(ip) == 1:
        if not ip[0]:
            pass
        elif validipaddr(ip[0]):
            addr = ip[0]
        elif validipport(ip[0]):
            port = int(ip[0])
        else:
            raise ValueError, ':'.join(ip) + ' is not a valid IP address/port'
    elif len(ip) == 2:
        addr, port = ip
        if not validipaddr(addr) and validipport(port):
            raise ValueError, ':'.join(ip) + ' is not a valid IP address/port'
        port = int(port)
    else:
        raise ValueError, ':'.join(ip) + ' is not a valid IP address/port'
    return (addr, port)

def validaddr(string_):
    """
    Returns either (ip_address, port) or "/path/to/socket" from string_
    
        >>> validaddr('/path/to/socket')
        '/path/to/socket'
        >>> validaddr('8000')
        ('0.0.0.0', 8000)
        >>> validaddr('127.0.0.1')
        ('127.0.0.1', 8080)
        >>> validaddr('127.0.0.1:8000')
        ('127.0.0.1', 8000)
        >>> validaddr('fff')
        Traceback (most recent call last):
            ...
        ValueError: fff is not a valid IP address/port
    """
    if '/' in string_:
        return string_
    else:
        return validip(string_)

def urlquote(val):
    """
    Quotes a string for use in a URL.
    
        >>> urlquote('://?f=1&j=1')
        '%3A//%3Ff%3D1%26j%3D1'
        >>> urlquote(None)
        ''
        >>> urlquote(u'\u203d')
        '%E2%80%BD'
    """
    if val is None: return ''
    if not isinstance(val, unicode): val = str(val)
    else: val = val.encode('utf-8')
    return urllib.quote(val)

def httpdate(date_obj):
    """
    Formats a datetime object for use in HTTP headers.
    
        >>> import datetime
        >>> httpdate(datetime.datetime(1970, 1, 1, 1, 1, 1))
        'Thu, 01 Jan 1970 01:01:01 GMT'
    """
    return date_obj.strftime("%a, %d %b %Y %H:%M:%S GMT")

def parsehttpdate(string_):
    """
    Parses an HTTP date into a datetime object.

        >>> parsehttpdate('Thu, 01 Jan 1970 01:01:01 GMT')
        datetime.datetime(1970, 1, 1, 1, 1, 1)
    """
    try:
        t = time.strptime(string_, "%a, %d %b %Y %H:%M:%S %Z")
    except ValueError:
        return None
    return datetime.datetime(*t[:6])

def htmlquote(text):
    r"""
    Encodes `text` for raw use in HTML.
    
        >>> htmlquote(u"<'&\">")
        u'&lt;&#39;&amp;&quot;&gt;'
    """
    text = text.replace(u"&", u"&amp;") # Must be done first!
    text = text.replace(u"<", u"&lt;")
    text = text.replace(u">", u"&gt;")
    text = text.replace(u"'", u"&#39;")
    text = text.replace(u'"', u"&quot;")
    return text

def htmlunquote(text):
    r"""
    Decodes `text` that's HTML quoted.

        >>> htmlunquote(u'&lt;&#39;&amp;&quot;&gt;')
        u'<\'&">'
    """
    text = text.replace(u"&quot;", u'"')
    text = text.replace(u"&#39;", u"'")
    text = text.replace(u"&gt;", u">")
    text = text.replace(u"&lt;", u"<")
    text = text.replace(u"&amp;", u"&") # Must be done last!
    return text
    
def websafe(val):
    r"""Converts `val` so that it is safe for use in Unicode HTML.

        >>> websafe("<'&\">")
        u'&lt;&#39;&amp;&quot;&gt;'
        >>> websafe(None)
        u''
        >>> websafe(u'\u203d')
        u'\u203d'
        >>> websafe('\xe2\x80\xbd')
        u'\u203d'
    """
    if val is None:
        return u''
    elif isinstance(val, str):
        val = val.decode('utf-8')
    elif not isinstance(val, unicode):
        val = unicode(val)
        
    return htmlquote(val)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = python23
"""Python 2.3 compatabilty"""
import threading

class threadlocal(object):
    """Implementation of threading.local for python2.3.
    """
    def __getattribute__(self, name):
        if name == "__dict__":
            return threadlocal._getd(self)
        else:
            try:
                return object.__getattribute__(self, name)
            except AttributeError:
                try:
                    return self.__dict__[name]
                except KeyError:
                    raise AttributeError, name
            
    def __setattr__(self, name, value):
        self.__dict__[name] = value
        
    def __delattr__(self, name):
        try:
            del self.__dict__[name]
        except KeyError:
            raise AttributeError, name
    
    def _getd(self):
        t = threading.currentThread()
        if not hasattr(t, '_d'):
            # using __dict__ of thread as thread local storage
            t._d = {}
        
        _id = id(self)
        # there could be multiple instances of threadlocal.
        # use id(self) as key
        if _id not in t._d:
            t._d[_id] = {}
        return t._d[_id]
        
if __name__ == '__main__':
     d = threadlocal()
     d.x = 1
     print d.__dict__
     print d.x
     
########NEW FILE########
__FILENAME__ = session
"""
Session Management
(from web.py)
"""

import os, time, datetime, random, base64
import os.path
from copy import deepcopy
try:
    import cPickle as pickle
except ImportError:
    import pickle
try:
    import hashlib
    sha1 = hashlib.sha1
except ImportError:
    import sha
    sha1 = sha.new

import utils
import webapi as web

__all__ = [
    'Session', 'SessionExpired',
    'Store', 'DiskStore', 'DBStore',
]

web.config.session_parameters = utils.storage({
    'cookie_name': 'webpy_session_id',
    'cookie_domain': None,
    'cookie_path' : None,
    'timeout': 86400, #24 * 60 * 60, # 24 hours in seconds
    'ignore_expiry': True,
    'ignore_change_ip': True,
    'secret_key': 'fLjUfxqXtfNoIldA0A0J',
    'expired_message': 'Session expired',
    'httponly': True,
    'secure': False
})

class SessionExpired(web.HTTPError): 
    def __init__(self, message):
        web.HTTPError.__init__(self, '200 OK', {}, data=message)

class Session(object):
    """Session management for web.py
    """
    __slots__ = [
        "store", "_initializer", "_last_cleanup_time", "_config", "_data", 
        "__getitem__", "__setitem__", "__delitem__"
    ]

    def __init__(self, app, store, initializer=None):
        self.store = store
        self._initializer = initializer
        self._last_cleanup_time = 0
        self._config = utils.storage(web.config.session_parameters)
        self._data = utils.threadeddict()
        
        self.__getitem__ = self._data.__getitem__
        self.__setitem__ = self._data.__setitem__
        self.__delitem__ = self._data.__delitem__

        if app:
            app.add_processor(self._processor)

    def __contains__(self, name):
        return name in self._data

    def __getattr__(self, name):
        return getattr(self._data, name)
    
    def __setattr__(self, name, value):
        if name in self.__slots__:
            object.__setattr__(self, name, value)
        else:
            setattr(self._data, name, value)
        
    def __delattr__(self, name):
        delattr(self._data, name)

    def _processor(self, handler):
        """Application processor to setup session for every request"""
        self._cleanup()
        self._load()

        try:
            return handler()
        finally:
            self._save()

    def _load(self):
        """Load the session from the store, by the id from cookie"""
        cookie_name = self._config.cookie_name
        cookie_domain = self._config.cookie_domain
        cookie_path = self._config.cookie_path
        httponly = self._config.httponly
        self.session_id = web.cookies().get(cookie_name)

        # protection against session_id tampering
        if self.session_id and not self._valid_session_id(self.session_id):
            self.session_id = None

        self._check_expiry()
        if self.session_id:
            d = self.store[self.session_id]
            self.update(d)
            self._validate_ip()
        
        if not self.session_id:
            self.session_id = self._generate_session_id()

            if self._initializer:
                if isinstance(self._initializer, dict):
                    self.update(deepcopy(self._initializer))
                elif hasattr(self._initializer, '__call__'):
                    self._initializer()
 
        self.ip = web.ctx.ip

    def _check_expiry(self):
        # check for expiry
        if self.session_id and self.session_id not in self.store:
            if self._config.ignore_expiry:
                self.session_id = None
            else:
                return self.expired()

    def _validate_ip(self):
        # check for change of IP
        if self.session_id and self.get('ip', None) != web.ctx.ip:
            if not self._config.ignore_change_ip:
               return self.expired() 
    
    def _save(self):
        if not self.get('_killed'):
            self._setcookie(self.session_id)
            self.store[self.session_id] = dict(self._data)
        else:
            self._setcookie(self.session_id, expires=-1)
            
    def _setcookie(self, session_id, expires='', **kw):
        cookie_name = self._config.cookie_name
        cookie_domain = self._config.cookie_domain
        cookie_path = self._config.cookie_path
        httponly = self._config.httponly
        secure = self._config.secure
        web.setcookie(cookie_name, session_id, expires=expires, domain=cookie_domain, httponly=httponly, secure=secure, path=cookie_path)
    
    def _generate_session_id(self):
        """Generate a random id for session"""

        while True:
            rand = os.urandom(16)
            now = time.time()
            secret_key = self._config.secret_key
            session_id = sha1("%s%s%s%s" %(rand, now, utils.safestr(web.ctx.ip), secret_key))
            session_id = session_id.hexdigest()
            if session_id not in self.store:
                break
        return session_id

    def _valid_session_id(self, session_id):
        rx = utils.re_compile('^[0-9a-fA-F]+$')
        return rx.match(session_id)
        
    def _cleanup(self):
        """Cleanup the stored sessions"""
        current_time = time.time()
        timeout = self._config.timeout
        if current_time - self._last_cleanup_time > timeout:
            self.store.cleanup(timeout)
            self._last_cleanup_time = current_time

    def expired(self):
        """Called when an expired session is atime"""
        self._killed = True
        self._save()
        raise SessionExpired(self._config.expired_message)
 
    def kill(self):
        """Kill the session, make it no longer available"""
        del self.store[self.session_id]
        self._killed = True

class Store:
    """Base class for session stores"""

    def __contains__(self, key):
        raise NotImplementedError

    def __getitem__(self, key):
        raise NotImplementedError

    def __setitem__(self, key, value):
        raise NotImplementedError

    def cleanup(self, timeout):
        """removes all the expired sessions"""
        raise NotImplementedError

    def encode(self, session_dict):
        """encodes session dict as a string"""
        pickled = pickle.dumps(session_dict)
        return base64.encodestring(pickled)

    def decode(self, session_data):
        """decodes the data to get back the session dict """
        pickled = base64.decodestring(session_data)
        return pickle.loads(pickled)

class DiskStore(Store):
    """
    Store for saving a session on disk.

        >>> import tempfile
        >>> root = tempfile.mkdtemp()
        >>> s = DiskStore(root)
        >>> s['a'] = 'foo'
        >>> s['a']
        'foo'
        >>> time.sleep(0.01)
        >>> s.cleanup(0.01)
        >>> s['a']
        Traceback (most recent call last):
            ...
        KeyError: 'a'
    """
    def __init__(self, root):
        # if the storage root doesn't exists, create it.
        if not os.path.exists(root):
            os.makedirs(
                    os.path.abspath(root)
                    )
        self.root = root

    def _get_path(self, key):
        if os.path.sep in key: 
            raise ValueError, "Bad key: %s" % repr(key)
        return os.path.join(self.root, key)
    
    def __contains__(self, key):
        path = self._get_path(key)
        return os.path.exists(path)

    def __getitem__(self, key):
        path = self._get_path(key)
        if os.path.exists(path): 
            pickled = open(path).read()
            return self.decode(pickled)
        else:
            raise KeyError, key

    def __setitem__(self, key, value):
        path = self._get_path(key)
        pickled = self.encode(value)    
        try:
            f = open(path, 'w')
            try:
                f.write(pickled)
            finally: 
                f.close()
        except IOError:
            pass

    def __delitem__(self, key):
        path = self._get_path(key)
        if os.path.exists(path):
            os.remove(path)
    
    def cleanup(self, timeout):
        now = time.time()
        for f in os.listdir(self.root):
            path = self._get_path(f)
            atime = os.stat(path).st_atime
            if now - atime > timeout :
                os.remove(path)

class DBStore(Store):
    """Store for saving a session in database
    Needs a table with the following columns:

        session_id CHAR(128) UNIQUE NOT NULL,
        atime DATETIME NOT NULL default current_timestamp,
        data TEXT
    """
    def __init__(self, db, table_name):
        self.db = db
        self.table = table_name
    
    def __contains__(self, key):
        data = self.db.select(self.table, where="session_id=$key", vars=locals())
        return bool(list(data)) 

    def __getitem__(self, key):
        now = datetime.datetime.now()
        try:
            s = self.db.select(self.table, where="session_id=$key", vars=locals())[0]
            self.db.update(self.table, where="session_id=$key", atime=now, vars=locals())
        except IndexError:
            raise KeyError
        else:
            return self.decode(s.data)

    def __setitem__(self, key, value):
        pickled = self.encode(value)
        now = datetime.datetime.now()
        if key in self:
            self.db.update(self.table, where="session_id=$key", data=pickled, vars=locals())
        else:
            self.db.insert(self.table, False, session_id=key, data=pickled )
                
    def __delitem__(self, key):
        self.db.delete(self.table, where="session_id=$key", vars=locals())

    def cleanup(self, timeout):
        timeout = datetime.timedelta(timeout/(24.0*60*60)) #timedelta takes numdays as arg
        last_allowed_time = datetime.datetime.now() - timeout
        self.db.delete(self.table, where="$last_allowed_time > atime", vars=locals())

class ShelfStore:
    """Store for saving session using `shelve` module.

        import shelve
        store = ShelfStore(shelve.open('session.shelf'))

    XXX: is shelve thread-safe?
    """
    def __init__(self, shelf):
        self.shelf = shelf

    def __contains__(self, key):
        return key in self.shelf

    def __getitem__(self, key):
        atime, v = self.shelf[key]
        self[key] = v # update atime
        return v

    def __setitem__(self, key, value):
        self.shelf[key] = time.time(), value
        
    def __delitem__(self, key):
        try:
            del self.shelf[key]
        except KeyError:
            pass

    def cleanup(self, timeout):
        now = time.time()
        for k in self.shelf.keys():
            atime, v = self.shelf[k]
            if now - atime > timeout :
                del self[k]

if __name__ == '__main__' :
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = template
"""
simple, elegant templating
(part of web.py)

Template design:

Template string is split into tokens and the tokens are combined into nodes. 
Parse tree is a nodelist. TextNode and ExpressionNode are simple nodes and 
for-loop, if-loop etc are block nodes, which contain multiple child nodes. 

Each node can emit some python string. python string emitted by the 
root node is validated for safeeval and executed using python in the given environment.

Enough care is taken to make sure the generated code and the template has line to line match, 
so that the error messages can point to exact line number in template. (It doesn't work in some cases still.)

Grammar:

    template -> defwith sections 
    defwith -> '$def with (' arguments ')' | ''
    sections -> section*
    section -> block | assignment | line

    assignment -> '$ ' <assignment expression>
    line -> (text|expr)*
    text -> <any characters other than $>
    expr -> '$' pyexpr | '$(' pyexpr ')' | '${' pyexpr '}'
    pyexpr -> <python expression>
"""

__all__ = [
    "Template",
    "Render", "render", "frender",
    "ParseError", "SecurityError",
    "test"
]

import tokenize
import os
import sys
import glob
import re
from UserDict import DictMixin
import warnings

from utils import storage, safeunicode, safestr, re_compile
from webapi import config
from net import websafe

def splitline(text):
    r"""
    Splits the given text at newline.
    
        >>> splitline('foo\nbar')
        ('foo\n', 'bar')
        >>> splitline('foo')
        ('foo', '')
        >>> splitline('')
        ('', '')
    """
    index = text.find('\n') + 1
    if index:
        return text[:index], text[index:]
    else:
        return text, ''

class Parser:
    """Parser Base.
    """
    def __init__(self):
        self.statement_nodes = STATEMENT_NODES
        self.keywords = KEYWORDS

    def parse(self, text, name="<template>"):
        self.text = text
        self.name = name
        
        defwith, text = self.read_defwith(text)
        suite = self.read_suite(text)
        return DefwithNode(defwith, suite)

    def read_defwith(self, text):
        if text.startswith('$def with'):
            defwith, text = splitline(text)
            defwith = defwith[1:].strip() # strip $ and spaces
            return defwith, text
        else:
            return '', text
    
    def read_section(self, text):
        r"""Reads one section from the given text.
        
        section -> block | assignment | line
        
            >>> read_section = Parser().read_section
            >>> read_section('foo\nbar\n')
            (<line: [t'foo\n']>, 'bar\n')
            >>> read_section('$ a = b + 1\nfoo\n')
            (<assignment: 'a = b + 1'>, 'foo\n')
            
        read_section('$for in range(10):\n    hello $i\nfoo)
        """
        if text.lstrip(' ').startswith('$'):
            index = text.index('$')
            begin_indent, text2 = text[:index], text[index+1:]
            ahead = self.python_lookahead(text2)
            
            if ahead == 'var':
                return self.read_var(text2)
            elif ahead in self.statement_nodes:
                return self.read_block_section(text2, begin_indent)
            elif ahead in self.keywords:
                return self.read_keyword(text2)
            elif ahead.strip() == '':
                # assignments starts with a space after $
                # ex: $ a = b + 2
                return self.read_assignment(text2)
        return self.readline(text)
        
    def read_var(self, text):
        r"""Reads a var statement.
        
            >>> read_var = Parser().read_var
            >>> read_var('var x=10\nfoo')
            (<var: x = 10>, 'foo')
            >>> read_var('var x: hello $name\nfoo')
            (<var: x = join_(u'hello ', escape_(name, True))>, 'foo')
        """
        line, text = splitline(text)
        tokens = self.python_tokens(line)
        if len(tokens) < 4:
            raise SyntaxError('Invalid var statement')
            
        name = tokens[1]
        sep = tokens[2]
        value = line.split(sep, 1)[1].strip()
        
        if sep == '=':
            pass # no need to process value
        elif sep == ':': 
            #@@ Hack for backward-compatability
            if tokens[3] == '\n': # multi-line var statement
                block, text = self.read_indented_block(text, '    ')
                lines = [self.readline(x)[0] for x in block.splitlines()]
                nodes = []
                for x in lines:
                    nodes.extend(x.nodes)
                    nodes.append(TextNode('\n'))         
            else: # single-line var statement
                linenode, _ = self.readline(value)
                nodes = linenode.nodes                
            parts = [node.emit('') for node in nodes]
            value = "join_(%s)" % ", ".join(parts)
        else:
            raise SyntaxError('Invalid var statement')
        return VarNode(name, value), text
                    
    def read_suite(self, text):
        r"""Reads section by section till end of text.
        
            >>> read_suite = Parser().read_suite
            >>> read_suite('hello $name\nfoo\n')
            [<line: [t'hello ', $name, t'\n']>, <line: [t'foo\n']>]
        """
        sections = []
        while text:
            section, text = self.read_section(text)
            sections.append(section)
        return SuiteNode(sections)
    
    def readline(self, text):
        r"""Reads one line from the text. Newline is supressed if the line ends with \.
        
            >>> readline = Parser().readline
            >>> readline('hello $name!\nbye!')
            (<line: [t'hello ', $name, t'!\n']>, 'bye!')
            >>> readline('hello $name!\\\nbye!')
            (<line: [t'hello ', $name, t'!']>, 'bye!')
            >>> readline('$f()\n\n')
            (<line: [$f(), t'\n']>, '\n')
        """
        line, text = splitline(text)

        # supress new line if line ends with \
        if line.endswith('\\\n'):
            line = line[:-2]
                
        nodes = []
        while line:
            node, line = self.read_node(line)
            nodes.append(node)
            
        return LineNode(nodes), text

    def read_node(self, text):
        r"""Reads a node from the given text and returns the node and remaining text.

            >>> read_node = Parser().read_node
            >>> read_node('hello $name')
            (t'hello ', '$name')
            >>> read_node('$name')
            ($name, '')
        """
        if text.startswith('$$'):
            return TextNode('$'), text[2:]
        elif text.startswith('$#'): # comment
            line, text = splitline(text)
            return TextNode('\n'), text
        elif text.startswith('$'):
            text = text[1:] # strip $
            if text.startswith(':'):
                escape = False
                text = text[1:] # strip :
            else:
                escape = True
            return self.read_expr(text, escape=escape)
        else:
            return self.read_text(text)
    
    def read_text(self, text):
        r"""Reads a text node from the given text.
        
            >>> read_text = Parser().read_text
            >>> read_text('hello $name')
            (t'hello ', '$name')
        """
        index = text.find('$')
        if index < 0:
            return TextNode(text), ''
        else:
            return TextNode(text[:index]), text[index:]
            
    def read_keyword(self, text):
        line, text = splitline(text)
        return StatementNode(line.strip() + "\n"), text

    def read_expr(self, text, escape=True):
        """Reads a python expression from the text and returns the expression and remaining text.

        expr -> simple_expr | paren_expr
        simple_expr -> id extended_expr
        extended_expr -> attr_access | paren_expr extended_expr | ''
        attr_access -> dot id extended_expr
        paren_expr -> [ tokens ] | ( tokens ) | { tokens }
     
            >>> read_expr = Parser().read_expr
            >>> read_expr("name")
            ($name, '')
            >>> read_expr("a.b and c")
            ($a.b, ' and c')
            >>> read_expr("a. b")
            ($a, '. b')
            >>> read_expr("name</h1>")
            ($name, '</h1>')
            >>> read_expr("(limit)ing")
            ($(limit), 'ing')
            >>> read_expr('a[1, 2][:3].f(1+2, "weird string[).", 3 + 4) done.')
            ($a[1, 2][:3].f(1+2, "weird string[).", 3 + 4), ' done.')
        """
        def simple_expr():
            identifier()
            extended_expr()
        
        def identifier():
            tokens.next()
        
        def extended_expr():
            lookahead = tokens.lookahead()
            if lookahead is None:
                return
            elif lookahead.value == '.':
                attr_access()
            elif lookahead.value in parens:
                paren_expr()
                extended_expr()
            else:
                return
        
        def attr_access():
            from token import NAME # python token constants
            dot = tokens.lookahead()
            if tokens.lookahead2().type == NAME:
                tokens.next() # consume dot
                identifier()
                extended_expr()
        
        def paren_expr():
            begin = tokens.next().value
            end = parens[begin]
            while True:
                if tokens.lookahead().value in parens:
                    paren_expr()
                else:
                    t = tokens.next()
                    if t.value == end:
                        break
            return

        parens = {
            "(": ")",
            "[": "]",
            "{": "}"
        }
        
        def get_tokens(text):
            """tokenize text using python tokenizer.
            Python tokenizer ignores spaces, but they might be important in some cases. 
            This function introduces dummy space tokens when it identifies any ignored space.
            Each token is a storage object containing type, value, begin and end.
            """
            readline = iter([text]).next
            end = None
            for t in tokenize.generate_tokens(readline):
                t = storage(type=t[0], value=t[1], begin=t[2], end=t[3])
                if end is not None and end != t.begin:
                    _, x1 = end
                    _, x2 = t.begin
                    yield storage(type=-1, value=text[x1:x2], begin=end, end=t.begin)
                end = t.end
                yield t
                
        class BetterIter:
            """Iterator like object with 2 support for 2 look aheads."""
            def __init__(self, items):
                self.iteritems = iter(items)
                self.items = []
                self.position = 0
                self.current_item = None
            
            def lookahead(self):
                if len(self.items) <= self.position:
                    self.items.append(self._next())
                return self.items[self.position]

            def _next(self):
                try:
                    return self.iteritems.next()
                except StopIteration:
                    return None
                
            def lookahead2(self):
                if len(self.items) <= self.position+1:
                    self.items.append(self._next())
                return self.items[self.position+1]
                    
            def next(self):
                self.current_item = self.lookahead()
                self.position += 1
                return self.current_item

        tokens = BetterIter(get_tokens(text))
                
        if tokens.lookahead().value in parens:
            paren_expr()
        else:
            simple_expr()
        row, col = tokens.current_item.end
        return ExpressionNode(text[:col], escape=escape), text[col:]    

    def read_assignment(self, text):
        r"""Reads assignment statement from text.
    
            >>> read_assignment = Parser().read_assignment
            >>> read_assignment('a = b + 1\nfoo')
            (<assignment: 'a = b + 1'>, 'foo')
        """
        line, text = splitline(text)
        return AssignmentNode(line.strip()), text
    
    def python_lookahead(self, text):
        """Returns the first python token from the given text.
        
            >>> python_lookahead = Parser().python_lookahead
            >>> python_lookahead('for i in range(10):')
            'for'
            >>> python_lookahead('else:')
            'else'
            >>> python_lookahead(' x = 1')
            ' '
        """
        readline = iter([text]).next
        tokens = tokenize.generate_tokens(readline)
        return tokens.next()[1]
        
    def python_tokens(self, text):
        readline = iter([text]).next
        tokens = tokenize.generate_tokens(readline)
        return [t[1] for t in tokens]
        
    def read_indented_block(self, text, indent):
        r"""Read a block of text. A block is what typically follows a for or it statement.
        It can be in the same line as that of the statement or an indented block.

            >>> read_indented_block = Parser().read_indented_block
            >>> read_indented_block('  a\n  b\nc', '  ')
            ('a\nb\n', 'c')
            >>> read_indented_block('  a\n    b\n  c\nd', '  ')
            ('a\n  b\nc\n', 'd')
            >>> read_indented_block('  a\n\n    b\nc', '  ')
            ('a\n\n  b\n', 'c')
        """
        if indent == '':
            return '', text
            
        block = ""
        while text:
            line, text2 = splitline(text)
            if line.strip() == "":
                block += '\n'
            elif line.startswith(indent):
                block += line[len(indent):]
            else:
                break
            text = text2
        return block, text

    def read_statement(self, text):
        r"""Reads a python statement.
        
            >>> read_statement = Parser().read_statement
            >>> read_statement('for i in range(10): hello $name')
            ('for i in range(10):', ' hello $name')
        """
        tok = PythonTokenizer(text)
        tok.consume_till(':')
        return text[:tok.index], text[tok.index:]
        
    def read_block_section(self, text, begin_indent=''):
        r"""
            >>> read_block_section = Parser().read_block_section
            >>> read_block_section('for i in range(10): hello $i\nfoo')
            (<block: 'for i in range(10):', [<line: [t'hello ', $i, t'\n']>]>, 'foo')
            >>> read_block_section('for i in range(10):\n        hello $i\n    foo', begin_indent='    ')
            (<block: 'for i in range(10):', [<line: [t'hello ', $i, t'\n']>]>, '    foo')
            >>> read_block_section('for i in range(10):\n  hello $i\nfoo')
            (<block: 'for i in range(10):', [<line: [t'hello ', $i, t'\n']>]>, 'foo')
        """
        line, text = splitline(text)
        stmt, line = self.read_statement(line)
        keyword = self.python_lookahead(stmt)
        
        # if there is some thing left in the line
        if line.strip():
            block = line.lstrip()
        else:
            def find_indent(text):
                rx = re_compile('  +')
                match = rx.match(text)    
                first_indent = match and match.group(0)
                return first_indent or ""

            # find the indentation of the block by looking at the first line
            first_indent = find_indent(text)[len(begin_indent):]

            #TODO: fix this special case
            if keyword == "code":
                indent = begin_indent + first_indent
            else:
                indent = begin_indent + min(first_indent, INDENT)
            
            block, text = self.read_indented_block(text, indent)
            
        return self.create_block_node(keyword, stmt, block, begin_indent), text
        
    def create_block_node(self, keyword, stmt, block, begin_indent):
        if keyword in self.statement_nodes:
            return self.statement_nodes[keyword](stmt, block, begin_indent)
        else:
            raise ParseError, 'Unknown statement: %s' % repr(keyword)
        
class PythonTokenizer:
    """Utility wrapper over python tokenizer."""
    def __init__(self, text):
        self.text = text
        readline = iter([text]).next
        self.tokens = tokenize.generate_tokens(readline)
        self.index = 0
        
    def consume_till(self, delim):        
        """Consumes tokens till colon.
        
            >>> tok = PythonTokenizer('for i in range(10): hello $i')
            >>> tok.consume_till(':')
            >>> tok.text[:tok.index]
            'for i in range(10):'
            >>> tok.text[tok.index:]
            ' hello $i'
        """
        try:
            while True:
                t = self.next()
                if t.value == delim:
                    break
                elif t.value == '(':
                    self.consume_till(')')
                elif t.value == '[':
                    self.consume_till(']')
                elif t.value == '{':
                    self.consume_till('}')

                # if end of line is found, it is an exception.
                # Since there is no easy way to report the line number,
                # leave the error reporting to the python parser later  
                #@@ This should be fixed.
                if t.value == '\n':
                    break
        except:
            #raise ParseError, "Expected %s, found end of line." % repr(delim)

            # raising ParseError doesn't show the line number. 
            # if this error is ignored, then it will be caught when compiling the python code.
            return
    
    def next(self):
        type, t, begin, end, line = self.tokens.next()
        row, col = end
        self.index = col
        return storage(type=type, value=t, begin=begin, end=end)
        
class DefwithNode:
    def __init__(self, defwith, suite):
        if defwith:
            self.defwith = defwith.replace('with', '__template__') + ':'
            # offset 4 lines. for encoding, __lineoffset__, loop and self.
            self.defwith += "\n    __lineoffset__ = -4"
        else:
            self.defwith = 'def __template__():'
            # offset 4 lines for encoding, __template__, __lineoffset__, loop and self.
            self.defwith += "\n    __lineoffset__ = -5"

        self.defwith += "\n    loop = ForLoop()"
        self.defwith += "\n    self = TemplateResult(); extend_ = self.extend"
        self.suite = suite
        self.end = "\n    return self"

    def emit(self, indent):
        encoding = "# coding: utf-8\n"
        return encoding + self.defwith + self.suite.emit(indent + INDENT) + self.end

    def __repr__(self):
        return "<defwith: %s, %s>" % (self.defwith, self.suite)

class TextNode:
    def __init__(self, value):
        self.value = value

    def emit(self, indent, begin_indent=''):
        return repr(safeunicode(self.value))
        
    def __repr__(self):
        return 't' + repr(self.value)

class ExpressionNode:
    def __init__(self, value, escape=True):
        self.value = value.strip()
        
        # convert ${...} to $(...)
        if value.startswith('{') and value.endswith('}'):
            self.value = '(' + self.value[1:-1] + ')'
            
        self.escape = escape

    def emit(self, indent, begin_indent=''):
        return 'escape_(%s, %s)' % (self.value, bool(self.escape))
        
    def __repr__(self):
        if self.escape:
            escape = ''
        else:
            escape = ':'
        return "$%s%s" % (escape, self.value)
        
class AssignmentNode:
    def __init__(self, code):
        self.code = code
        
    def emit(self, indent, begin_indent=''):
        return indent + self.code + "\n"
        
    def __repr__(self):
        return "<assignment: %s>" % repr(self.code)
        
class LineNode:
    def __init__(self, nodes):
        self.nodes = nodes
        
    def emit(self, indent, text_indent='', name=''):
        text = [node.emit('') for node in self.nodes]
        if text_indent:
            text = [repr(text_indent)] + text

        return indent + "extend_([%s])\n" % ", ".join(text)        
    
    def __repr__(self):
        return "<line: %s>" % repr(self.nodes)

INDENT = '    ' # 4 spaces
        
class BlockNode:
    def __init__(self, stmt, block, begin_indent=''):
        self.stmt = stmt
        self.suite = Parser().read_suite(block)
        self.begin_indent = begin_indent

    def emit(self, indent, text_indent=''):
        text_indent = self.begin_indent + text_indent
        out = indent + self.stmt + self.suite.emit(indent + INDENT, text_indent)
        return out
        
    def __repr__(self):
        return "<block: %s, %s>" % (repr(self.stmt), repr(self.suite))

class ForNode(BlockNode):
    def __init__(self, stmt, block, begin_indent=''):
        self.original_stmt = stmt
        tok = PythonTokenizer(stmt)
        tok.consume_till('in')
        a = stmt[:tok.index] # for i in
        b = stmt[tok.index:-1] # rest of for stmt excluding :
        stmt = a + ' loop.setup(' + b.strip() + '):'
        BlockNode.__init__(self, stmt, block, begin_indent)
        
    def __repr__(self):
        return "<block: %s, %s>" % (repr(self.original_stmt), repr(self.suite))

class CodeNode:
    def __init__(self, stmt, block, begin_indent=''):
        # compensate one line for $code:
        self.code = "\n" + block
        
    def emit(self, indent, text_indent=''):
        import re
        rx = re.compile('^', re.M)
        return rx.sub(indent, self.code).rstrip(' ')
        
    def __repr__(self):
        return "<code: %s>" % repr(self.code)
        
class StatementNode:
    def __init__(self, stmt):
        self.stmt = stmt
        
    def emit(self, indent, begin_indent=''):
        return indent + self.stmt
        
    def __repr__(self):
        return "<stmt: %s>" % repr(self.stmt)
        
class IfNode(BlockNode):
    pass

class ElseNode(BlockNode):
    pass

class ElifNode(BlockNode):
    pass

class DefNode(BlockNode):
    def __init__(self, *a, **kw):
        BlockNode.__init__(self, *a, **kw)

        code = CodeNode("", "")
        code.code = "self = TemplateResult(); extend_ = self.extend\n"
        self.suite.sections.insert(0, code)

        code = CodeNode("", "")
        code.code = "return self\n"
        self.suite.sections.append(code)
        
    def emit(self, indent, text_indent=''):
        text_indent = self.begin_indent + text_indent
        out = indent + self.stmt + self.suite.emit(indent + INDENT, text_indent)
        return indent + "__lineoffset__ -= 3\n" + out

class VarNode:
    def __init__(self, name, value):
        self.name = name
        self.value = value
        
    def emit(self, indent, text_indent):
        return indent + "self[%s] = %s\n" % (repr(self.name), self.value)
        
    def __repr__(self):
        return "<var: %s = %s>" % (self.name, self.value)

class SuiteNode:
    """Suite is a list of sections."""
    def __init__(self, sections):
        self.sections = sections
        
    def emit(self, indent, text_indent=''):
        return "\n" + "".join([s.emit(indent, text_indent) for s in self.sections])
        
    def __repr__(self):
        return repr(self.sections)

STATEMENT_NODES = {
    'for': ForNode,
    'while': BlockNode,
    'if': IfNode,
    'elif': ElifNode,
    'else': ElseNode,
    'def': DefNode,
    'code': CodeNode
}

KEYWORDS = [
    "pass",
    "break",
    "continue",
    "return"
]

TEMPLATE_BUILTIN_NAMES = [
    "dict", "enumerate", "float", "int", "bool", "list", "long", "reversed", 
    "set", "slice", "tuple", "xrange",
    "abs", "all", "any", "callable", "chr", "cmp", "divmod", "filter", "hex", 
    "id", "isinstance", "iter", "len", "max", "min", "oct", "ord", "pow", "range",
    "True", "False",
    "None",
    "__import__", # some c-libraries like datetime requires __import__ to present in the namespace
]

import __builtin__
TEMPLATE_BUILTINS = dict([(name, getattr(__builtin__, name)) for name in TEMPLATE_BUILTIN_NAMES if name in __builtin__.__dict__])

class ForLoop:
    """
    Wrapper for expression in for stament to support loop.xxx helpers.
    
        >>> loop = ForLoop()
        >>> for x in loop.setup(['a', 'b', 'c']):
        ...     print loop.index, loop.revindex, loop.parity, x
        ...
        1 3 odd a
        2 2 even b
        3 1 odd c
        >>> loop.index
        Traceback (most recent call last):
            ...
        AttributeError: index
    """
    def __init__(self):
        self._ctx = None
        
    def __getattr__(self, name):
        if self._ctx is None:
            raise AttributeError, name
        else:
            return getattr(self._ctx, name)
        
    def setup(self, seq):        
        self._push()
        return self._ctx.setup(seq)
        
    def _push(self):
        self._ctx = ForLoopContext(self, self._ctx)
        
    def _pop(self):
        self._ctx = self._ctx.parent
                
class ForLoopContext:
    """Stackable context for ForLoop to support nested for loops.
    """
    def __init__(self, forloop, parent):
        self._forloop = forloop
        self.parent = parent
        
    def setup(self, seq):
        try:
            self.length = len(seq)
        except:
            self.length = 0

        self.index = 0
        for a in seq:
            self.index += 1
            yield a
        self._forloop._pop()
            
    index0 = property(lambda self: self.index-1)
    first = property(lambda self: self.index == 1)
    last = property(lambda self: self.index == self.length)
    odd = property(lambda self: self.index % 2 == 1)
    even = property(lambda self: self.index % 2 == 0)
    parity = property(lambda self: ['odd', 'even'][self.even])
    revindex0 = property(lambda self: self.length - self.index)
    revindex = property(lambda self: self.length - self.index + 1)
        
class BaseTemplate:
    def __init__(self, code, filename, filter, globals, builtins):
        self.filename = filename
        self.filter = filter
        self._globals = globals
        self._builtins = builtins
        if code:
            self.t = self._compile(code)
        else:
            self.t = lambda: ''
        
    def _compile(self, code):
        env = self.make_env(self._globals or {}, self._builtins)
        exec(code, env)
        return env['__template__']

    def __call__(self, *a, **kw):
        __hidetraceback__ = True
        return self.t(*a, **kw)

    def make_env(self, globals, builtins):
        return dict(globals,
            __builtins__=builtins, 
            ForLoop=ForLoop,
            TemplateResult=TemplateResult,
            escape_=self._escape,
            join_=self._join
        )
    def _join(self, *items):
        return u"".join(items)
            
    def _escape(self, value, escape=False):
        if value is None: 
            value = ''
            
        value = safeunicode(value)
        if escape and self.filter:
            value = self.filter(value)
        return value

class Template(BaseTemplate):
    CONTENT_TYPES = {
        '.html' : 'text/html; charset=utf-8',
        '.xhtml' : 'application/xhtml+xml; charset=utf-8',
        '.txt' : 'text/plain',
    }
    FILTERS = {
        '.html': websafe,
        '.xhtml': websafe,
        '.xml': websafe
    }
    globals = {}
    
    def __init__(self, text, filename='<template>', filter=None, globals=None, builtins=None, extensions=None):
        self.extensions = extensions or []
        text = Template.normalize_text(text)
        code = self.compile_template(text, filename)
                
        _, ext = os.path.splitext(filename)
        filter = filter or self.FILTERS.get(ext, None)
        self.content_type = self.CONTENT_TYPES.get(ext, None)

        if globals is None:
            globals = self.globals
        if builtins is None:
            builtins = TEMPLATE_BUILTINS
                
        BaseTemplate.__init__(self, code=code, filename=filename, filter=filter, globals=globals, builtins=builtins)
        
    def normalize_text(text):
        """Normalizes template text by correcting \r\n, tabs and BOM chars."""
        text = text.replace('\r\n', '\n').replace('\r', '\n').expandtabs()
        if not text.endswith('\n'):
            text += '\n'

        # ignore BOM chars at the begining of template
        BOM = '\xef\xbb\xbf'
        if isinstance(text, str) and text.startswith(BOM):
            text = text[len(BOM):]
        
        # support fort \$ for backward-compatibility 
        text = text.replace(r'\$', '$$')
        return text
    normalize_text = staticmethod(normalize_text)
                
    def __call__(self, *a, **kw):
        __hidetraceback__ = True
        import webapi as web
        if 'headers' in web.ctx and self.content_type:
            web.header('Content-Type', self.content_type, unique=True)
            
        return BaseTemplate.__call__(self, *a, **kw)
        
    def generate_code(text, filename, parser=None):
        # parse the text
        parser = parser or Parser()
        rootnode = parser.parse(text, filename)
                
        # generate python code from the parse tree
        code = rootnode.emit(indent="").strip()
        return safestr(code)
        
    generate_code = staticmethod(generate_code)
    
    def create_parser(self):
        p = Parser()
        for ext in self.extensions:
            p = ext(p)
        return p
                
    def compile_template(self, template_string, filename):
        code = Template.generate_code(template_string, filename, parser=self.create_parser())

        def get_source_line(filename, lineno):
            try:
                lines = open(filename).read().splitlines()
                return lines[lineno]
            except:
                return None
        
        try:
            # compile the code first to report the errors, if any, with the filename
            compiled_code = compile(code, filename, 'exec')
        except SyntaxError, e:
            # display template line that caused the error along with the traceback.
            try:
                e.msg += '\n\nTemplate traceback:\n    File %s, line %s\n        %s' % \
                    (repr(e.filename), e.lineno, get_source_line(e.filename, e.lineno-1))
            except: 
                pass
            raise
        
        # make sure code is safe - but not with jython, it doesn't have a working compiler module
        if not sys.platform.startswith('java'):
            try:
                import compiler
                ast = compiler.parse(code)
                SafeVisitor().walk(ast, filename)
            except ImportError:
                warnings.warn("Unabled to import compiler module. Unable to check templates for safety.")
        else:
            warnings.warn("SECURITY ISSUE: You are using Jython, which does not support checking templates for safety. Your templates can execute arbitrary code.")

        return compiled_code
        
class CompiledTemplate(Template):
    def __init__(self, f, filename):
        Template.__init__(self, '', filename)
        self.t = f
        
    def compile_template(self, *a):
        return None
    
    def _compile(self, *a):
        return None
                
class Render:
    """The most preferred way of using templates.
    
        render = web.template.render('templates')
        print render.foo()
        
    Optional parameter can be `base` can be used to pass output of 
    every template through the base template.
    
        render = web.template.render('templates', base='layout')
    """
    def __init__(self, loc='templates', cache=None, base=None, **keywords):
        self._loc = loc
        self._keywords = keywords

        if cache is None:
            cache = not config.get('debug', False)
        
        if cache:
            self._cache = {}
        else:
            self._cache = None
        
        if base and not hasattr(base, '__call__'):
            # make base a function, so that it can be passed to sub-renders
            self._base = lambda page: self._template(base)(page)
        else:
            self._base = base
    
    def _add_global(self, obj, name=None):
        """Add a global to this rendering instance."""
        if 'globals' not in self._keywords: self._keywords['globals'] = {}
        if not name:
            name = obj.__name__
        self._keywords['globals'][name] = obj
    
    def _lookup(self, name):
        path = os.path.join(self._loc, name)
        if os.path.isdir(path):
            return 'dir', path
        else:
            path = self._findfile(path)
            if path:
                return 'file', path
            else:
                return 'none', None
        
    def _load_template(self, name):
        kind, path = self._lookup(name)
        
        if kind == 'dir':
            return Render(path, cache=self._cache is not None, base=self._base, **self._keywords)
        elif kind == 'file':
            return Template(open(path).read(), filename=path, **self._keywords)
        else:
            raise AttributeError, "No template named " + name            

    def _findfile(self, path_prefix): 
        p = [f for f in glob.glob(path_prefix + '.*') if not f.endswith('~')] # skip backup files
        p.sort() # sort the matches for deterministic order
        return p and p[0]
            
    def _template(self, name):
        if self._cache is not None:
            if name not in self._cache:
                self._cache[name] = self._load_template(name)
            return self._cache[name]
        else:
            return self._load_template(name)
        
    def __getattr__(self, name):
        t = self._template(name)
        if self._base and isinstance(t, Template):
            def template(*a, **kw):
                return self._base(t(*a, **kw))
            return template
        else:
            return self._template(name)

class GAE_Render(Render):
    # Render gets over-written. make a copy here.
    super = Render
    def __init__(self, loc, *a, **kw):
        GAE_Render.super.__init__(self, loc, *a, **kw)
        
        import types
        if isinstance(loc, types.ModuleType):
            self.mod = loc
        else:
            name = loc.rstrip('/').replace('/', '.')
            self.mod = __import__(name, None, None, ['x'])

        self.mod.__dict__.update(kw.get('builtins', TEMPLATE_BUILTINS))
        self.mod.__dict__.update(Template.globals)
        self.mod.__dict__.update(kw.get('globals', {}))

    def _load_template(self, name):
        t = getattr(self.mod, name)
        import types
        if isinstance(t, types.ModuleType):
            return GAE_Render(t, cache=self._cache is not None, base=self._base, **self._keywords)
        else:
            return t

render = Render
# setup render for Google App Engine.
try:
    from google import appengine
    render = Render = GAE_Render
except ImportError:
    pass
        
def frender(path, **keywords):
    """Creates a template from the given file path.
    """
    return Template(open(path).read(), filename=path, **keywords)
    
def compile_templates(root):
    """Compiles templates to python code."""
    re_start = re_compile('^', re.M)
    
    for dirpath, dirnames, filenames in os.walk(root):
        filenames = [f for f in filenames if not f.startswith('.') and not f.endswith('~') and not f.startswith('__init__.py')]

        for d in dirnames[:]:
            if d.startswith('.'):
                dirnames.remove(d) # don't visit this dir

        out = open(os.path.join(dirpath, '__init__.py'), 'w')
        out.write('from web.template import CompiledTemplate, ForLoop, TemplateResult\n\n')
        if dirnames:
            out.write("import " + ", ".join(dirnames))
        out.write("\n")

        for f in filenames:
            path = os.path.join(dirpath, f)

            if '.' in f:
                name, _ = f.split('.', 1)
            else:
                name = f
                
            text = open(path).read()
            text = Template.normalize_text(text)
            code = Template.generate_code(text, path)

            code = code.replace("__template__", name, 1)
            
            out.write(code)

            out.write('\n\n')
            out.write('%s = CompiledTemplate(%s, %s)\n' % (name, name, repr(path)))
            out.write("join_ = %s._join; escape_ = %s._escape\n\n" % (name, name))

            # create template to make sure it compiles
            t = Template(open(path).read(), path)
        out.close()
                
class ParseError(Exception):
    pass
    
class SecurityError(Exception):
    """The template seems to be trying to do something naughty."""
    pass

# Enumerate all the allowed AST nodes
ALLOWED_AST_NODES = [
    "Add", "And",
#   "AssAttr",
    "AssList", "AssName", "AssTuple",
#   "Assert",
    "Assign", "AugAssign",
#   "Backquote",
    "Bitand", "Bitor", "Bitxor", "Break",
    "CallFunc","Class", "Compare", "Const", "Continue",
    "Decorators", "Dict", "Discard", "Div",
    "Ellipsis", "EmptyNode",
#   "Exec",
    "Expression", "FloorDiv", "For",
#   "From",
    "Function", 
    "GenExpr", "GenExprFor", "GenExprIf", "GenExprInner",
    "Getattr", 
#   "Global", 
    "If", "IfExp",
#   "Import",
    "Invert", "Keyword", "Lambda", "LeftShift",
    "List", "ListComp", "ListCompFor", "ListCompIf", "Mod",
    "Module",
    "Mul", "Name", "Not", "Or", "Pass", "Power",
#   "Print", "Printnl", "Raise",
    "Return", "RightShift", "Slice", "Sliceobj",
    "Stmt", "Sub", "Subscript",
#   "TryExcept", "TryFinally",
    "Tuple", "UnaryAdd", "UnarySub",
    "While", "With", "Yield",
]

class SafeVisitor(object):
    """
    Make sure code is safe by walking through the AST.
    
    Code considered unsafe if:
        * it has restricted AST nodes
        * it is trying to access resricted attributes   
        
    Adopted from http://www.zafar.se/bkz/uploads/safe.txt (public domain, Babar K. Zafar)
    """
    def __init__(self):
        "Initialize visitor by generating callbacks for all AST node types."
        self.errors = []

    def walk(self, ast, filename):
        "Validate each node in AST and raise SecurityError if the code is not safe."
        self.filename = filename
        self.visit(ast)
        
        if self.errors:        
            raise SecurityError, '\n'.join([str(err) for err in self.errors])
        
    def visit(self, node, *args):
        "Recursively validate node and all of its children."
        def classname(obj):
            return obj.__class__.__name__
        nodename = classname(node)
        fn = getattr(self, 'visit' + nodename, None)
        
        if fn:
            fn(node, *args)
        else:
            if nodename not in ALLOWED_AST_NODES:
                self.fail(node, *args)
            
        for child in node.getChildNodes():
            self.visit(child, *args)

    def visitName(self, node, *args):
        "Disallow any attempts to access a restricted attr."
        #self.assert_attr(node.getChildren()[0], node)
        pass
        
    def visitGetattr(self, node, *args):
        "Disallow any attempts to access a restricted attribute."
        self.assert_attr(node.attrname, node)
            
    def assert_attr(self, attrname, node):
        if self.is_unallowed_attr(attrname):
            lineno = self.get_node_lineno(node)
            e = SecurityError("%s:%d - access to attribute '%s' is denied" % (self.filename, lineno, attrname))
            self.errors.append(e)

    def is_unallowed_attr(self, name):
        return name.startswith('_') \
            or name.startswith('func_') \
            or name.startswith('im_')
            
    def get_node_lineno(self, node):
        return (node.lineno) and node.lineno or 0
        
    def fail(self, node, *args):
        "Default callback for unallowed AST nodes."
        lineno = self.get_node_lineno(node)
        nodename = node.__class__.__name__
        e = SecurityError("%s:%d - execution of '%s' statements is denied" % (self.filename, lineno, nodename))
        self.errors.append(e)

class TemplateResult(object, DictMixin):
    """Dictionary like object for storing template output.
    
    The result of a template execution is usally a string, but sometimes it
    contains attributes set using $var. This class provides a simple
    dictionary like interface for storing the output of the template and the
    attributes. The output is stored with a special key __body__. Convering
    the the TemplateResult to string or unicode returns the value of __body__.
    
    When the template is in execution, the output is generated part by part
    and those parts are combined at the end. Parts are added to the
    TemplateResult by calling the `extend` method and the parts are combined
    seemlessly when __body__ is accessed.
    
        >>> d = TemplateResult(__body__='hello, world', x='foo')
        >>> d
        <TemplateResult: {'__body__': 'hello, world', 'x': 'foo'}>
        >>> print d
        hello, world
        >>> d.x
        'foo'
        >>> d = TemplateResult()
        >>> d.extend([u'hello', u'world'])
        >>> d
        <TemplateResult: {'__body__': u'helloworld'}>
    """
    def __init__(self, *a, **kw):
        self.__dict__["_d"] = dict(*a, **kw)
        self._d.setdefault("__body__", u'')
        
        self.__dict__['_parts'] = []
        self.__dict__["extend"] = self._parts.extend
        
        self._d.setdefault("__body__", None)
    
    def keys(self):
        return self._d.keys()
        
    def _prepare_body(self):
        """Prepare value of __body__ by joining parts.
        """
        if self._parts:
            value = u"".join(self._parts)
            self._parts[:] = []
            body = self._d.get('__body__')
            if body:
                self._d['__body__'] = body + value
            else:
                self._d['__body__'] = value
                
    def __getitem__(self, name):
        if name == "__body__":
            self._prepare_body()
        return self._d[name]
        
    def __setitem__(self, name, value):
        if name == "__body__":
            self._prepare_body()
        return self._d.__setitem__(name, value)
        
    def __delitem__(self, name):
        if name == "__body__":
            self._prepare_body()
        return self._d.__delitem__(name)

    def __getattr__(self, key): 
        try:
            return self[key]
        except KeyError, k:
            raise AttributeError, k

    def __setattr__(self, key, value): 
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError, k:
            raise AttributeError, k
        
    def __unicode__(self):
        self._prepare_body()
        return self["__body__"]
    
    def __str__(self):
        self._prepare_body()
        return self["__body__"].encode('utf-8')
        
    def __repr__(self):
        self._prepare_body()
        return "<TemplateResult: %s>" % self._d

def test():
    r"""Doctest for testing template module.

    Define a utility function to run template test.
    
        >>> class TestResult:
        ...     def __init__(self, t): self.t = t
        ...     def __getattr__(self, name): return getattr(self.t, name)
        ...     def __repr__(self): return repr(unicode(self))
        ...
        >>> def t(code, **keywords):
        ...     tmpl = Template(code, **keywords)
        ...     return lambda *a, **kw: TestResult(tmpl(*a, **kw))
        ...
    
    Simple tests.
    
        >>> t('1')()
        u'1\n'
        >>> t('$def with ()\n1')()
        u'1\n'
        >>> t('$def with (a)\n$a')(1)
        u'1\n'
        >>> t('$def with (a=0)\n$a')(1)
        u'1\n'
        >>> t('$def with (a=0)\n$a')(a=1)
        u'1\n'
    
    Test complicated expressions.
        
        >>> t('$def with (x)\n$x.upper()')('hello')
        u'HELLO\n'
        >>> t('$(2 * 3 + 4 * 5)')()
        u'26\n'
        >>> t('${2 * 3 + 4 * 5}')()
        u'26\n'
        >>> t('$def with (limit)\nkeep $(limit)ing.')('go')
        u'keep going.\n'
        >>> t('$def with (a)\n$a.b[0]')(storage(b=[1]))
        u'1\n'
        
    Test html escaping.
    
        >>> t('$def with (x)\n$x', filename='a.html')('<html>')
        u'&lt;html&gt;\n'
        >>> t('$def with (x)\n$x', filename='a.txt')('<html>')
        u'<html>\n'
                
    Test if, for and while.
    
        >>> t('$if 1: 1')()
        u'1\n'
        >>> t('$if 1:\n    1')()
        u'1\n'
        >>> t('$if 1:\n    1\\')()
        u'1'
        >>> t('$if 0: 0\n$elif 1: 1')()
        u'1\n'
        >>> t('$if 0: 0\n$elif None: 0\n$else: 1')()
        u'1\n'
        >>> t('$if 0 < 1 and 1 < 2: 1')()
        u'1\n'
        >>> t('$for x in [1, 2, 3]: $x')()
        u'1\n2\n3\n'
        >>> t('$def with (d)\n$for k, v in d.iteritems(): $k')({1: 1})
        u'1\n'
        >>> t('$for x in [1, 2, 3]:\n\t$x')()
        u'    1\n    2\n    3\n'
        >>> t('$def with (a)\n$while a and a.pop():1')([1, 2, 3])
        u'1\n1\n1\n'

    The space after : must be ignored.
    
        >>> t('$if True: foo')()
        u'foo\n'
    
    Test loop.xxx.

        >>> t("$for i in range(5):$loop.index, $loop.parity")()
        u'1, odd\n2, even\n3, odd\n4, even\n5, odd\n'
        >>> t("$for i in range(2):\n    $for j in range(2):$loop.parent.parity $loop.parity")()
        u'odd odd\nodd even\neven odd\neven even\n'
        
    Test assignment.
    
        >>> t('$ a = 1\n$a')()
        u'1\n'
        >>> t('$ a = [1]\n$a[0]')()
        u'1\n'
        >>> t('$ a = {1: 1}\n$a.keys()[0]')()
        u'1\n'
        >>> t('$ a = []\n$if not a: 1')()
        u'1\n'
        >>> t('$ a = {}\n$if not a: 1')()
        u'1\n'
        >>> t('$ a = -1\n$a')()
        u'-1\n'
        >>> t('$ a = "1"\n$a')()
        u'1\n'

    Test comments.
    
        >>> t('$# 0')()
        u'\n'
        >>> t('hello$#comment1\nhello$#comment2')()
        u'hello\nhello\n'
        >>> t('$#comment0\nhello$#comment1\nhello$#comment2')()
        u'\nhello\nhello\n'
        
    Test unicode.
    
        >>> t('$def with (a)\n$a')(u'\u203d')
        u'\u203d\n'
        >>> t('$def with (a)\n$a')(u'\u203d'.encode('utf-8'))
        u'\u203d\n'
        >>> t(u'$def with (a)\n$a $:a')(u'\u203d')
        u'\u203d \u203d\n'
        >>> t(u'$def with ()\nfoo')()
        u'foo\n'
        >>> def f(x): return x
        ...
        >>> t(u'$def with (f)\n$:f("x")')(f)
        u'x\n'
        >>> t('$def with (f)\n$:f("x")')(f)
        u'x\n'
    
    Test dollar escaping.
    
        >>> t("Stop, $$money isn't evaluated.")()
        u"Stop, $money isn't evaluated.\n"
        >>> t("Stop, \$money isn't evaluated.")()
        u"Stop, $money isn't evaluated.\n"
        
    Test space sensitivity.
    
        >>> t('$def with (x)\n$x')(1)
        u'1\n'
        >>> t('$def with(x ,y)\n$x')(1, 1)
        u'1\n'
        >>> t('$(1 + 2*3 + 4)')()
        u'11\n'
        
    Make sure globals are working.
            
        >>> t('$x')()
        Traceback (most recent call last):
            ...
        NameError: global name 'x' is not defined
        >>> t('$x', globals={'x': 1})()
        u'1\n'
        
    Can't change globals.
    
        >>> t('$ x = 2\n$x', globals={'x': 1})()
        u'2\n'
        >>> t('$ x = x + 1\n$x', globals={'x': 1})()
        Traceback (most recent call last):
            ...
        UnboundLocalError: local variable 'x' referenced before assignment
    
    Make sure builtins are customizable.
    
        >>> t('$min(1, 2)')()
        u'1\n'
        >>> t('$min(1, 2)', builtins={})()
        Traceback (most recent call last):
            ...
        NameError: global name 'min' is not defined
        
    Test vars.
    
        >>> x = t('$var x: 1')()
        >>> x.x
        u'1'
        >>> x = t('$var x = 1')()
        >>> x.x
        1
        >>> x = t('$var x:  \n    foo\n    bar')()
        >>> x.x
        u'foo\nbar\n'

    Test BOM chars.

        >>> t('\xef\xbb\xbf$def with(x)\n$x')('foo')
        u'foo\n'

    Test for with weird cases.

        >>> t('$for i in range(10)[1:5]:\n    $i')()
        u'1\n2\n3\n4\n'
        >>> t("$for k, v in {'a': 1, 'b': 2}.items():\n    $k $v")()
        u'a 1\nb 2\n'
        >>> t("$for k, v in ({'a': 1, 'b': 2}.items():\n    $k $v")()
        Traceback (most recent call last):
            ...
        SyntaxError: invalid syntax

    Test datetime.

        >>> import datetime
        >>> t("$def with (date)\n$date.strftime('%m %Y')")(datetime.datetime(2009, 1, 1))
        u'01 2009\n'
    """
    pass
            
if __name__ == "__main__":
    import sys
    if '--compile' in sys.argv:
        compile_templates(sys.argv[2])
    else:
        import doctest
        doctest.testmod()

########NEW FILE########
__FILENAME__ = test
"""test utilities
(part of web.py)
"""
import unittest
import sys, os
import web

TestCase = unittest.TestCase
TestSuite = unittest.TestSuite

def load_modules(names):
    return [__import__(name, None, None, "x") for name in names]

def module_suite(module, classnames=None):
    """Makes a suite from a module."""
    if classnames:
        return unittest.TestLoader().loadTestsFromNames(classnames, module)
    elif hasattr(module, 'suite'):
        return module.suite()
    else:
        return unittest.TestLoader().loadTestsFromModule(module)

def doctest_suite(module_names):
    """Makes a test suite from doctests."""
    import doctest
    suite = TestSuite()
    for mod in load_modules(module_names):
        suite.addTest(doctest.DocTestSuite(mod))
    return suite
    
def suite(module_names):
    """Creates a suite from multiple modules."""
    suite = TestSuite()
    for mod in load_modules(module_names):
        suite.addTest(module_suite(mod))
    return suite

def runTests(suite):
    runner = unittest.TextTestRunner()
    return runner.run(suite)

def main(suite=None):
    if not suite:
        main_module = __import__('__main__')
        # allow command line switches
        args = [a for a in sys.argv[1:] if not a.startswith('-')]
        suite = module_suite(main_module, args or None)

    result = runTests(suite)
    sys.exit(not result.wasSuccessful())


########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
"""
General Utilities
(part of web.py)
"""

__all__ = [
  "Storage", "storage", "storify", 
  "Counter", "counter",
  "iters", 
  "rstrips", "lstrips", "strips", 
  "safeunicode", "safestr", "utf8",
  "TimeoutError", "timelimit",
  "Memoize", "memoize",
  "re_compile", "re_subm",
  "group", "uniq", "iterview",
  "IterBetter", "iterbetter",
  "safeiter", "safewrite",
  "dictreverse", "dictfind", "dictfindall", "dictincr", "dictadd",
  "requeue", "restack",
  "listget", "intget", "datestr",
  "numify", "denumify", "commify", "dateify",
  "nthstr", "cond",
  "CaptureStdout", "capturestdout", "Profile", "profile",
  "tryall",
  "ThreadedDict", "threadeddict",
  "autoassign",
  "to36",
  "safemarkdown",
  "sendmail"
]

import re, sys, time, threading, itertools, traceback, os

try:
    import subprocess
except ImportError: 
    subprocess = None

try: import datetime
except ImportError: pass

try: set
except NameError:
    from sets import Set as set
    
try:
    from threading import local as threadlocal
except ImportError:
    from python23 import threadlocal

class Storage(dict):
    """
    A Storage object is like a dictionary except `obj.foo` can be used
    in addition to `obj['foo']`.
    
        >>> o = storage(a=1)
        >>> o.a
        1
        >>> o['a']
        1
        >>> o.a = 2
        >>> o['a']
        2
        >>> del o.a
        >>> o.a
        Traceback (most recent call last):
            ...
        AttributeError: 'a'
    
    """
    def __getattr__(self, key): 
        try:
            return self[key]
        except KeyError, k:
            raise AttributeError, k
    
    def __setattr__(self, key, value): 
        self[key] = value
    
    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError, k:
            raise AttributeError, k
    
    def __repr__(self):     
        return '<Storage ' + dict.__repr__(self) + '>'

storage = Storage

def storify(mapping, *requireds, **defaults):
    """
    Creates a `storage` object from dictionary `mapping`, raising `KeyError` if
    d doesn't have all of the keys in `requireds` and using the default 
    values for keys found in `defaults`.

    For example, `storify({'a':1, 'c':3}, b=2, c=0)` will return the equivalent of
    `storage({'a':1, 'b':2, 'c':3})`.
    
    If a `storify` value is a list (e.g. multiple values in a form submission), 
    `storify` returns the last element of the list, unless the key appears in 
    `defaults` as a list. Thus:
    
        >>> storify({'a':[1, 2]}).a
        2
        >>> storify({'a':[1, 2]}, a=[]).a
        [1, 2]
        >>> storify({'a':1}, a=[]).a
        [1]
        >>> storify({}, a=[]).a
        []
    
    Similarly, if the value has a `value` attribute, `storify will return _its_
    value, unless the key appears in `defaults` as a dictionary.
    
        >>> storify({'a':storage(value=1)}).a
        1
        >>> storify({'a':storage(value=1)}, a={}).a
        <Storage {'value': 1}>
        >>> storify({}, a={}).a
        {}
        
    Optionally, keyword parameter `_unicode` can be passed to convert all values to unicode.
    
        >>> storify({'x': 'a'}, _unicode=True)
        <Storage {'x': u'a'}>
        >>> storify({'x': storage(value='a')}, x={}, _unicode=True)
        <Storage {'x': <Storage {'value': 'a'}>}>
        >>> storify({'x': storage(value='a')}, _unicode=True)
        <Storage {'x': u'a'}>
    """
    _unicode = defaults.pop('_unicode', False)

    # if _unicode is callable object, use it convert a string to unicode.
    to_unicode = safeunicode
    if _unicode is not False and hasattr(_unicode, "__call__"):
        to_unicode = _unicode
    
    def unicodify(s):
        if _unicode and isinstance(s, str): return to_unicode(s)
        else: return s
        
    def getvalue(x):
        if hasattr(x, 'file') and hasattr(x, 'value'):
            return x.value
        elif hasattr(x, 'value'):
            return unicodify(x.value)
        else:
            return unicodify(x)
    
    stor = Storage()
    for key in requireds + tuple(mapping.keys()):
        value = mapping[key]
        if isinstance(value, list):
            if isinstance(defaults.get(key), list):
                value = [getvalue(x) for x in value]
            else:
                value = value[-1]
        if not isinstance(defaults.get(key), dict):
            value = getvalue(value)
        if isinstance(defaults.get(key), list) and not isinstance(value, list):
            value = [value]
        setattr(stor, key, value)

    for (key, value) in defaults.iteritems():
        result = value
        if hasattr(stor, key): 
            result = stor[key]
        if value == () and not isinstance(result, tuple): 
            result = (result,)
        setattr(stor, key, result)
    
    return stor

class Counter(storage):
    """Keeps count of how many times something is added.
        
        >>> c = counter()
        >>> c.add('x')
        >>> c.add('x')
        >>> c.add('x')
        >>> c.add('x')
        >>> c.add('x')
        >>> c.add('y')
        >>> c
        <Counter {'y': 1, 'x': 5}>
        >>> c.most()
        ['x']
    """
    def add(self, n):
        self.setdefault(n, 0)
        self[n] += 1
    
    def most(self):
        """Returns the keys with maximum count."""
        m = max(self.itervalues())
        return [k for k, v in self.iteritems() if v == m]
        
    def least(self):
        """Returns the keys with mininum count."""
        m = min(self.itervalues())
        return [k for k, v in self.iteritems() if v == m]

    def percent(self, key):
       """Returns what percentage a certain key is of all entries.

           >>> c = counter()
           >>> c.add('x')
           >>> c.add('x')
           >>> c.add('x')
           >>> c.add('y')
           >>> c.percent('x')
           0.75
           >>> c.percent('y')
           0.25
       """
       return float(self[key])/sum(self.values())
             
    def sorted_keys(self):
        """Returns keys sorted by value.
             
             >>> c = counter()
             >>> c.add('x')
             >>> c.add('x')
             >>> c.add('y')
             >>> c.sorted_keys()
             ['x', 'y']
        """
        return sorted(self.keys(), key=lambda k: self[k], reverse=True)
    
    def sorted_values(self):
        """Returns values sorted by value.
            
            >>> c = counter()
            >>> c.add('x')
            >>> c.add('x')
            >>> c.add('y')
            >>> c.sorted_values()
            [2, 1]
        """
        return [self[k] for k in self.sorted_keys()]
    
    def sorted_items(self):
        """Returns items sorted by value.
            
            >>> c = counter()
            >>> c.add('x')
            >>> c.add('x')
            >>> c.add('y')
            >>> c.sorted_items()
            [('x', 2), ('y', 1)]
        """
        return [(k, self[k]) for k in self.sorted_keys()]
    
    def __repr__(self):
        return '<Counter ' + dict.__repr__(self) + '>'
       
counter = Counter

iters = [list, tuple]
import __builtin__
if hasattr(__builtin__, 'set'):
    iters.append(set)
if hasattr(__builtin__, 'frozenset'):
    iters.append(set)
if sys.version_info < (2,6): # sets module deprecated in 2.6
    try:
        from sets import Set
        iters.append(Set)
    except ImportError: 
        pass
    
class _hack(tuple): pass
iters = _hack(iters)
iters.__doc__ = """
A list of iterable items (like lists, but not strings). Includes whichever
of lists, tuples, sets, and Sets are available in this version of Python.
"""

def _strips(direction, text, remove):
    if isinstance(remove, iters):
        for subr in remove:
            text = _strips(direction, text, subr)
        return text
    
    if direction == 'l': 
        if text.startswith(remove): 
            return text[len(remove):]
    elif direction == 'r':
        if text.endswith(remove):   
            return text[:-len(remove)]
    else: 
        raise ValueError, "Direction needs to be r or l."
    return text

def rstrips(text, remove):
    """
    removes the string `remove` from the right of `text`

        >>> rstrips("foobar", "bar")
        'foo'
    
    """
    return _strips('r', text, remove)

def lstrips(text, remove):
    """
    removes the string `remove` from the left of `text`
    
        >>> lstrips("foobar", "foo")
        'bar'
        >>> lstrips('http://foo.org/', ['http://', 'https://'])
        'foo.org/'
        >>> lstrips('FOOBARBAZ', ['FOO', 'BAR'])
        'BAZ'
        >>> lstrips('FOOBARBAZ', ['BAR', 'FOO'])
        'BARBAZ'
    
    """
    return _strips('l', text, remove)

def strips(text, remove):
    """
    removes the string `remove` from the both sides of `text`

        >>> strips("foobarfoo", "foo")
        'bar'
    
    """
    return rstrips(lstrips(text, remove), remove)

def safeunicode(obj, encoding='utf-8'):
    r"""
    Converts any given object to unicode string.
    
        >>> safeunicode('hello')
        u'hello'
        >>> safeunicode(2)
        u'2'
        >>> safeunicode('\xe1\x88\xb4')
        u'\u1234'
    """
    t = type(obj)
    if t is unicode:
        return obj
    elif t is str:
        return obj.decode(encoding)
    elif t in [int, float, bool]:
        return unicode(obj)
    elif hasattr(obj, '__unicode__') or isinstance(obj, unicode):
        return unicode(obj)
    else:
        return str(obj).decode(encoding)
    
def safestr(obj, encoding='utf-8'):
    r"""
    Converts any given object to utf-8 encoded string. 
    
        >>> safestr('hello')
        'hello'
        >>> safestr(u'\u1234')
        '\xe1\x88\xb4'
        >>> safestr(2)
        '2'
    """
    if isinstance(obj, unicode):
        return obj.encode(encoding)
    elif isinstance(obj, str):
        return obj
    elif hasattr(obj, 'next'): # iterator
        return itertools.imap(safestr, obj)
    else:
        return str(obj)

# for backward-compatibility
utf8 = safestr
    
class TimeoutError(Exception): pass
def timelimit(timeout):
    """
    A decorator to limit a function to `timeout` seconds, raising `TimeoutError`
    if it takes longer.
    
        >>> import time
        >>> def meaningoflife():
        ...     time.sleep(.2)
        ...     return 42
        >>> 
        >>> timelimit(.1)(meaningoflife)()
        Traceback (most recent call last):
            ...
        TimeoutError: took too long
        >>> timelimit(1)(meaningoflife)()
        42

    _Caveat:_ The function isn't stopped after `timeout` seconds but continues 
    executing in a separate thread. (There seems to be no way to kill a thread.)

    inspired by <http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/473878>
    """
    def _1(function):
        def _2(*args, **kw):
            class Dispatch(threading.Thread):
                def __init__(self):
                    threading.Thread.__init__(self)
                    self.result = None
                    self.error = None

                    self.setDaemon(True)
                    self.start()

                def run(self):
                    try:
                        self.result = function(*args, **kw)
                    except:
                        self.error = sys.exc_info()

            c = Dispatch()
            c.join(timeout)
            if c.isAlive():
                raise TimeoutError, 'took too long'
            if c.error:
                raise c.error[0], c.error[1]
            return c.result
        return _2
    return _1

class Memoize:
    """
    'Memoizes' a function, caching its return values for each input.
    If `expires` is specified, values are recalculated after `expires` seconds.
    If `background` is specified, values are recalculated in a separate thread.
    
        >>> calls = 0
        >>> def howmanytimeshaveibeencalled():
        ...     global calls
        ...     calls += 1
        ...     return calls
        >>> fastcalls = memoize(howmanytimeshaveibeencalled)
        >>> howmanytimeshaveibeencalled()
        1
        >>> howmanytimeshaveibeencalled()
        2
        >>> fastcalls()
        3
        >>> fastcalls()
        3
        >>> import time
        >>> fastcalls = memoize(howmanytimeshaveibeencalled, .1, background=False)
        >>> fastcalls()
        4
        >>> fastcalls()
        4
        >>> time.sleep(.2)
        >>> fastcalls()
        5
        >>> def slowfunc():
        ...     time.sleep(.1)
        ...     return howmanytimeshaveibeencalled()
        >>> fastcalls = memoize(slowfunc, .2, background=True)
        >>> fastcalls()
        6
        >>> timelimit(.05)(fastcalls)()
        6
        >>> time.sleep(.2)
        >>> timelimit(.05)(fastcalls)()
        6
        >>> timelimit(.05)(fastcalls)()
        6
        >>> time.sleep(.2)
        >>> timelimit(.05)(fastcalls)()
        7
        >>> fastcalls = memoize(slowfunc, None, background=True)
        >>> threading.Thread(target=fastcalls).start()
        >>> time.sleep(.01)
        >>> fastcalls()
        9
    """
    def __init__(self, func, expires=None, background=True): 
        self.func = func
        self.cache = {}
        self.expires = expires
        self.background = background
        self.running = {}
    
    def __call__(self, *args, **keywords):
        key = (args, tuple(keywords.items()))
        if not self.running.get(key):
            self.running[key] = threading.Lock()
        def update(block=False):
            if self.running[key].acquire(block):
                try:
                    self.cache[key] = (self.func(*args, **keywords), time.time())
                finally:
                    self.running[key].release()
        
        if key not in self.cache: 
            update(block=True)
        elif self.expires and (time.time() - self.cache[key][1]) > self.expires:
            if self.background:
                threading.Thread(target=update).start()
            else:
                update()
        return self.cache[key][0]

memoize = Memoize

re_compile = memoize(re.compile) #@@ threadsafe?
re_compile.__doc__ = """
A memoized version of re.compile.
"""

class _re_subm_proxy:
    def __init__(self): 
        self.match = None
    def __call__(self, match): 
        self.match = match
        return ''

def re_subm(pat, repl, string):
    """
    Like re.sub, but returns the replacement _and_ the match object.
    
        >>> t, m = re_subm('g(oo+)fball', r'f\\1lish', 'goooooofball')
        >>> t
        'foooooolish'
        >>> m.groups()
        ('oooooo',)
    """
    compiled_pat = re_compile(pat)
    proxy = _re_subm_proxy()
    compiled_pat.sub(proxy.__call__, string)
    return compiled_pat.sub(repl, string), proxy.match

def group(seq, size): 
    """
    Returns an iterator over a series of lists of length size from iterable.

        >>> list(group([1,2,3,4], 2))
        [[1, 2], [3, 4]]
        >>> list(group([1,2,3,4,5], 2))
        [[1, 2], [3, 4], [5]]
    """
    def take(seq, n):
        for i in xrange(n):
            yield seq.next()

    if not hasattr(seq, 'next'):  
        seq = iter(seq)
    while True: 
        x = list(take(seq, size))
        if x:
            yield x
        else:
            break

def uniq(seq, key=None):
    """
    Removes duplicate elements from a list while preserving the order of the rest.

        >>> uniq([9,0,2,1,0])
        [9, 0, 2, 1]

    The value of the optional `key` parameter should be a function that
    takes a single argument and returns a key to test the uniqueness.

        >>> uniq(["Foo", "foo", "bar"], key=lambda s: s.lower())
        ['Foo', 'bar']
    """
    key = key or (lambda x: x)
    seen = set()
    result = []
    for v in seq:
        k = key(v)
        if k in seen:
            continue
        seen.add(k)
        result.append(v)
    return result

def iterview(x):
   """
   Takes an iterable `x` and returns an iterator over it
   which prints its progress to stderr as it iterates through.
   """
   WIDTH = 70

   def plainformat(n, lenx):
       return '%5.1f%% (%*d/%d)' % ((float(n)/lenx)*100, len(str(lenx)), n, lenx)

   def bars(size, n, lenx):
       val = int((float(n)*size)/lenx + 0.5)
       if size - val:
           spacing = ">" + (" "*(size-val))[1:]
       else:
           spacing = ""
       return "[%s%s]" % ("="*val, spacing)

   def eta(elapsed, n, lenx):
       if n == 0:
           return '--:--:--'
       if n == lenx:
           secs = int(elapsed)
       else:
           secs = int((elapsed/n) * (lenx-n))
       mins, secs = divmod(secs, 60)
       hrs, mins = divmod(mins, 60)

       return '%02d:%02d:%02d' % (hrs, mins, secs)

   def format(starttime, n, lenx):
       out = plainformat(n, lenx) + ' '
       if n == lenx:
           end = '     '
       else:
           end = ' ETA '
       end += eta(time.time() - starttime, n, lenx)
       out += bars(WIDTH - len(out) - len(end), n, lenx)
       out += end
       return out

   starttime = time.time()
   lenx = len(x)
   for n, y in enumerate(x):
       sys.stderr.write('\r' + format(starttime, n, lenx))
       yield y
   sys.stderr.write('\r' + format(starttime, n+1, lenx) + '\n')

class IterBetter:
    """
    Returns an object that can be used as an iterator 
    but can also be used via __getitem__ (although it 
    cannot go backwards -- that is, you cannot request 
    `iterbetter[0]` after requesting `iterbetter[1]`).
    
        >>> import itertools
        >>> c = iterbetter(itertools.count())
        >>> c[1]
        1
        >>> c[5]
        5
        >>> c[3]
        Traceback (most recent call last):
            ...
        IndexError: already passed 3

    For boolean test, IterBetter peeps at first value in the itertor without effecting the iteration.

        >>> c = iterbetter(iter(range(5)))
        >>> bool(c)
        True
        >>> list(c)
        [0, 1, 2, 3, 4]
        >>> c = iterbetter(iter([]))
        >>> bool(c)
        False
        >>> list(c)
        []
    """
    def __init__(self, iterator): 
        self.i, self.c = iterator, 0

    def __iter__(self): 
        if hasattr(self, "_head"):
            yield self._head

        while 1:    
            yield self.i.next()
            self.c += 1

    def __getitem__(self, i):
        #todo: slices
        if i < self.c: 
            raise IndexError, "already passed "+str(i)
        try:
            while i > self.c: 
                self.i.next()
                self.c += 1
            # now self.c == i
            self.c += 1
            return self.i.next()
        except StopIteration: 
            raise IndexError, str(i)
            
    def __nonzero__(self):
        if hasattr(self, "__len__"):
            return len(self) != 0
        elif hasattr(self, "_head"):
            return True
        else:
            try:
                self._head = self.i.next()
            except StopIteration:
                return False
            else:
                return True

iterbetter = IterBetter

def safeiter(it, cleanup=None, ignore_errors=True):
    """Makes an iterator safe by ignoring the exceptions occured during the iteration.
    """
    def next():
        while True:
            try:
                return it.next()
            except StopIteration:
                raise
            except:
                traceback.print_exc()

    it = iter(it)
    while True:
        yield next()

def safewrite(filename, content):
    """Writes the content to a temp file and then moves the temp file to 
    given filename to avoid overwriting the existing file in case of errors.
    """
    f = file(filename + '.tmp', 'w')
    f.write(content)
    f.close()
    os.rename(f.name, filename)

def dictreverse(mapping):
    """
    Returns a new dictionary with keys and values swapped.
    
        >>> dictreverse({1: 2, 3: 4})
        {2: 1, 4: 3}
    """
    return dict([(value, key) for (key, value) in mapping.iteritems()])

def dictfind(dictionary, element):
    """
    Returns a key whose value in `dictionary` is `element` 
    or, if none exists, None.
    
        >>> d = {1:2, 3:4}
        >>> dictfind(d, 4)
        3
        >>> dictfind(d, 5)
    """
    for (key, value) in dictionary.iteritems():
        if element is value: 
            return key

def dictfindall(dictionary, element):
    """
    Returns the keys whose values in `dictionary` are `element`
    or, if none exists, [].
    
        >>> d = {1:4, 3:4}
        >>> dictfindall(d, 4)
        [1, 3]
        >>> dictfindall(d, 5)
        []
    """
    res = []
    for (key, value) in dictionary.iteritems():
        if element is value:
            res.append(key)
    return res

def dictincr(dictionary, element):
    """
    Increments `element` in `dictionary`, 
    setting it to one if it doesn't exist.
    
        >>> d = {1:2, 3:4}
        >>> dictincr(d, 1)
        3
        >>> d[1]
        3
        >>> dictincr(d, 5)
        1
        >>> d[5]
        1
    """
    dictionary.setdefault(element, 0)
    dictionary[element] += 1
    return dictionary[element]

def dictadd(*dicts):
    """
    Returns a dictionary consisting of the keys in the argument dictionaries.
    If they share a key, the value from the last argument is used.
    
        >>> dictadd({1: 0, 2: 0}, {2: 1, 3: 1})
        {1: 0, 2: 1, 3: 1}
    """
    result = {}
    for dct in dicts:
        result.update(dct)
    return result

def requeue(queue, index=-1):
    """Returns the element at index after moving it to the beginning of the queue.

        >>> x = [1, 2, 3, 4]
        >>> requeue(x)
        4
        >>> x
        [4, 1, 2, 3]
    """
    x = queue.pop(index)
    queue.insert(0, x)
    return x

def restack(stack, index=0):
    """Returns the element at index after moving it to the top of stack.

           >>> x = [1, 2, 3, 4]
           >>> restack(x)
           1
           >>> x
           [2, 3, 4, 1]
    """
    x = stack.pop(index)
    stack.append(x)
    return x

def listget(lst, ind, default=None):
    """
    Returns `lst[ind]` if it exists, `default` otherwise.
    
        >>> listget(['a'], 0)
        'a'
        >>> listget(['a'], 1)
        >>> listget(['a'], 1, 'b')
        'b'
    """
    if len(lst)-1 < ind: 
        return default
    return lst[ind]

def intget(integer, default=None):
    """
    Returns `integer` as an int or `default` if it can't.
    
        >>> intget('3')
        3
        >>> intget('3a')
        >>> intget('3a', 0)
        0
    """
    try:
        return int(integer)
    except (TypeError, ValueError):
        return default

def datestr(then, now=None):
    """
    Converts a (UTC) datetime object to a nice string representation.
    
        >>> from datetime import datetime, timedelta
        >>> d = datetime(1970, 5, 1)
        >>> datestr(d, now=d)
        '0 microseconds ago'
        >>> for t, v in {
        ...   timedelta(microseconds=1): '1 microsecond ago',
        ...   timedelta(microseconds=2): '2 microseconds ago',
        ...   -timedelta(microseconds=1): '1 microsecond from now',
        ...   -timedelta(microseconds=2): '2 microseconds from now',
        ...   timedelta(microseconds=2000): '2 milliseconds ago',
        ...   timedelta(seconds=2): '2 seconds ago',
        ...   timedelta(seconds=2*60): '2 minutes ago',
        ...   timedelta(seconds=2*60*60): '2 hours ago',
        ...   timedelta(days=2): '2 days ago',
        ... }.iteritems():
        ...     assert datestr(d, now=d+t) == v
        >>> datestr(datetime(1970, 1, 1), now=d)
        'January  1'
        >>> datestr(datetime(1969, 1, 1), now=d)
        'January  1, 1969'
        >>> datestr(datetime(1970, 6, 1), now=d)
        'June  1, 1970'
        >>> datestr(None)
        ''
    """
    def agohence(n, what, divisor=None):
        if divisor: n = n // divisor

        out = str(abs(n)) + ' ' + what       # '2 day'
        if abs(n) != 1: out += 's'           # '2 days'
        out += ' '                           # '2 days '
        if n < 0:
            out += 'from now'
        else:
            out += 'ago'
        return out                           # '2 days ago'

    oneday = 24 * 60 * 60

    if not then: return ""
    if not now: now = datetime.datetime.utcnow()
    if type(now).__name__ == "DateTime":
        now = datetime.datetime.fromtimestamp(now)
    if type(then).__name__ == "DateTime":
        then = datetime.datetime.fromtimestamp(then)
    elif type(then).__name__ == "date":
        then = datetime.datetime(then.year, then.month, then.day)

    delta = now - then
    deltaseconds = int(delta.days * oneday + delta.seconds + delta.microseconds * 1e-06)
    deltadays = abs(deltaseconds) // oneday
    if deltaseconds < 0: deltadays *= -1 # fix for oddity of floor

    if deltadays:
        if abs(deltadays) < 4:
            return agohence(deltadays, 'day')

        try:
            out = then.strftime('%B %e') # e.g. 'June  3'
        except ValueError:
            # %e doesn't work on Windows.
            out = then.strftime('%B %d') # e.g. 'June 03'

        if then.year != now.year or deltadays < 0:
            out += ', %s' % then.year
        return out

    if int(deltaseconds):
        if abs(deltaseconds) > (60 * 60):
            return agohence(deltaseconds, 'hour', 60 * 60)
        elif abs(deltaseconds) > 60:
            return agohence(deltaseconds, 'minute', 60)
        else:
            return agohence(deltaseconds, 'second')

    deltamicroseconds = delta.microseconds
    if delta.days: deltamicroseconds = int(delta.microseconds - 1e6) # datetime oddity
    if abs(deltamicroseconds) > 1000:
        return agohence(deltamicroseconds, 'millisecond', 1000)

    return agohence(deltamicroseconds, 'microsecond')

def numify(string):
    """
    Removes all non-digit characters from `string`.
    
        >>> numify('800-555-1212')
        '8005551212'
        >>> numify('800.555.1212')
        '8005551212'
    
    """
    return ''.join([c for c in str(string) if c.isdigit()])

def denumify(string, pattern):
    """
    Formats `string` according to `pattern`, where the letter X gets replaced
    by characters from `string`.
    
        >>> denumify("8005551212", "(XXX) XXX-XXXX")
        '(800) 555-1212'
    
    """
    out = []
    for c in pattern:
        if c == "X":
            out.append(string[0])
            string = string[1:]
        else:
            out.append(c)
    return ''.join(out)

def commify(n):
    """
    Add commas to an integer `n`.

        >>> commify(1)
        '1'
        >>> commify(123)
        '123'
        >>> commify(1234)
        '1,234'
        >>> commify(1234567890)
        '1,234,567,890'
        >>> commify(123.0)
        '123.0'
        >>> commify(1234.5)
        '1,234.5'
        >>> commify(1234.56789)
        '1,234.56789'
        >>> commify('%.2f' % 1234.5)
        '1,234.50'
        >>> commify(None)
        >>>

    """
    if n is None: return None
    n = str(n)
    if '.' in n:
        dollars, cents = n.split('.')
    else:
        dollars, cents = n, None

    r = []
    for i, c in enumerate(str(dollars)[::-1]):
        if i and (not (i % 3)):
            r.insert(0, ',')
        r.insert(0, c)
    out = ''.join(r)
    if cents:
        out += '.' + cents
    return out

def dateify(datestring):
    """
    Formats a numified `datestring` properly.
    """
    return denumify(datestring, "XXXX-XX-XX XX:XX:XX")


def nthstr(n):
    """
    Formats an ordinal.
    Doesn't handle negative numbers.

        >>> nthstr(1)
        '1st'
        >>> nthstr(0)
        '0th'
        >>> [nthstr(x) for x in [2, 3, 4, 5, 10, 11, 12, 13, 14, 15]]
        ['2nd', '3rd', '4th', '5th', '10th', '11th', '12th', '13th', '14th', '15th']
        >>> [nthstr(x) for x in [91, 92, 93, 94, 99, 100, 101, 102]]
        ['91st', '92nd', '93rd', '94th', '99th', '100th', '101st', '102nd']
        >>> [nthstr(x) for x in [111, 112, 113, 114, 115]]
        ['111th', '112th', '113th', '114th', '115th']

    """
    
    assert n >= 0
    if n % 100 in [11, 12, 13]: return '%sth' % n
    return {1: '%sst', 2: '%snd', 3: '%srd'}.get(n % 10, '%sth') % n

def cond(predicate, consequence, alternative=None):
    """
    Function replacement for if-else to use in expressions.
        
        >>> x = 2
        >>> cond(x % 2 == 0, "even", "odd")
        'even'
        >>> cond(x % 2 == 0, "even", "odd") + '_row'
        'even_row'
    """
    if predicate:
        return consequence
    else:
        return alternative

class CaptureStdout:
    """
    Captures everything `func` prints to stdout and returns it instead.
    
        >>> def idiot():
        ...     print "foo"
        >>> capturestdout(idiot)()
        'foo\\n'
    
    **WARNING:** Not threadsafe!
    """
    def __init__(self, func): 
        self.func = func
    def __call__(self, *args, **keywords):
        from cStringIO import StringIO
        # Not threadsafe!
        out = StringIO()
        oldstdout = sys.stdout
        sys.stdout = out
        try: 
            self.func(*args, **keywords)
        finally: 
            sys.stdout = oldstdout
        return out.getvalue()

capturestdout = CaptureStdout

class Profile:
    """
    Profiles `func` and returns a tuple containing its output
    and a string with human-readable profiling information.
        
        >>> import time
        >>> out, inf = profile(time.sleep)(.001)
        >>> out
        >>> inf[:10].strip()
        'took 0.0'
    """
    def __init__(self, func): 
        self.func = func
    def __call__(self, *args): ##, **kw):   kw unused
        import hotshot, hotshot.stats, os, tempfile ##, time already imported
        f, filename = tempfile.mkstemp()
        os.close(f)
        
        prof = hotshot.Profile(filename)

        stime = time.time()
        result = prof.runcall(self.func, *args)
        stime = time.time() - stime
        prof.close()

        import cStringIO
        out = cStringIO.StringIO()
        stats = hotshot.stats.load(filename)
        stats.stream = out
        stats.strip_dirs()
        stats.sort_stats('time', 'calls')
        stats.print_stats(40)
        stats.print_callers()

        x =  '\n\ntook '+ str(stime) + ' seconds\n'
        x += out.getvalue()

        # remove the tempfile
        try:
            os.remove(filename)
        except IOError:
            pass
            
        return result, x

profile = Profile


import traceback
# hack for compatibility with Python 2.3:
if not hasattr(traceback, 'format_exc'):
    from cStringIO import StringIO
    def format_exc(limit=None):
        strbuf = StringIO()
        traceback.print_exc(limit, strbuf)
        return strbuf.getvalue()
    traceback.format_exc = format_exc

def tryall(context, prefix=None):
    """
    Tries a series of functions and prints their results. 
    `context` is a dictionary mapping names to values; 
    the value will only be tried if it's callable.
    
        >>> tryall(dict(j=lambda: True))
        j: True
        ----------------------------------------
        results:
           True: 1

    For example, you might have a file `test/stuff.py` 
    with a series of functions testing various things in it. 
    At the bottom, have a line:

        if __name__ == "__main__": tryall(globals())

    Then you can run `python test/stuff.py` and get the results of 
    all the tests.
    """
    context = context.copy() # vars() would update
    results = {}
    for (key, value) in context.iteritems():
        if not hasattr(value, '__call__'): 
            continue
        if prefix and not key.startswith(prefix): 
            continue
        print key + ':',
        try:
            r = value()
            dictincr(results, r)
            print r
        except:
            print 'ERROR'
            dictincr(results, 'ERROR')
            print '   ' + '\n   '.join(traceback.format_exc().split('\n'))
        
    print '-'*40
    print 'results:'
    for (key, value) in results.iteritems():
        print ' '*2, str(key)+':', value
        
class ThreadedDict(threadlocal):
    """
    Thread local storage.
    
        >>> d = ThreadedDict()
        >>> d.x = 1
        >>> d.x
        1
        >>> import threading
        >>> def f(): d.x = 2
        ...
        >>> t = threading.Thread(target=f)
        >>> t.start()
        >>> t.join()
        >>> d.x
        1
    """
    _instances = set()
    
    def __init__(self):
        ThreadedDict._instances.add(self)
        
    def __del__(self):
        ThreadedDict._instances.remove(self)
        
    def __hash__(self):
        return id(self)
    
    def clear_all():
        """Clears all ThreadedDict instances.
        """
        for t in list(ThreadedDict._instances):
            t.clear()
    clear_all = staticmethod(clear_all)
    
    # Define all these methods to more or less fully emulate dict -- attribute access
    # is built into threading.local.

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __delitem__(self, key):
        del self.__dict__[key]

    def __contains__(self, key):
        return key in self.__dict__

    has_key = __contains__
        
    def clear(self):
        self.__dict__.clear()

    def copy(self):
        return self.__dict__.copy()

    def get(self, key, default=None):
        return self.__dict__.get(key, default)

    def items(self):
        return self.__dict__.items()

    def iteritems(self):
        return self.__dict__.iteritems()

    def keys(self):
        return self.__dict__.keys()

    def iterkeys(self):
        return self.__dict__.iterkeys()

    iter = iterkeys

    def values(self):
        return self.__dict__.values()

    def itervalues(self):
        return self.__dict__.itervalues()

    def pop(self, key, *args):
        return self.__dict__.pop(key, *args)

    def popitem(self):
        return self.__dict__.popitem()

    def setdefault(self, key, default=None):
        return self.__dict__.setdefault(key, default)

    def update(self, *args, **kwargs):
        self.__dict__.update(*args, **kwargs)

    def __repr__(self):
        return '<ThreadedDict %r>' % self.__dict__

    __str__ = __repr__
    
threadeddict = ThreadedDict

def autoassign(self, locals):
    """
    Automatically assigns local variables to `self`.
    
        >>> self = storage()
        >>> autoassign(self, dict(a=1, b=2))
        >>> self
        <Storage {'a': 1, 'b': 2}>
    
    Generally used in `__init__` methods, as in:

        def __init__(self, foo, bar, baz=1): autoassign(self, locals())
    """
    for (key, value) in locals.iteritems():
        if key == 'self': 
            continue
        setattr(self, key, value)

def to36(q):
    """
    Converts an integer to base 36 (a useful scheme for human-sayable IDs).
    
        >>> to36(35)
        'z'
        >>> to36(119292)
        '2k1o'
        >>> int(to36(939387374), 36)
        939387374
        >>> to36(0)
        '0'
        >>> to36(-393)
        Traceback (most recent call last):
            ... 
        ValueError: must supply a positive integer
    
    """
    if q < 0: raise ValueError, "must supply a positive integer"
    letters = "0123456789abcdefghijklmnopqrstuvwxyz"
    converted = []
    while q != 0:
        q, r = divmod(q, 36)
        converted.insert(0, letters[r])
    return "".join(converted) or '0'


r_url = re_compile('(?<!\()(http://(\S+))')
def safemarkdown(text):
    """
    Converts text to HTML following the rules of Markdown, but blocking any
    outside HTML input, so that only the things supported by Markdown
    can be used. Also converts raw URLs to links.

    (requires [markdown.py](http://webpy.org/markdown.py))
    """
    from markdown import markdown
    if text:
        text = text.replace('<', '&lt;')
        # TODO: automatically get page title?
        text = r_url.sub(r'<\1>', text)
        text = markdown(text)
        return text

def sendmail(from_address, to_address, subject, message, headers=None, **kw):
    """
    Sends the email message `message` with mail and envelope headers
    for from `from_address_` to `to_address` with `subject`. 
    Additional email headers can be specified with the dictionary 
    `headers.
    
    Optionally cc, bcc and attachments can be specified as keyword arguments.
    Attachments must be an iterable and each attachment can be either a 
    filename or a file object or a dictionary with filename, content and 
    optionally content_type keys.

    If `web.config.smtp_server` is set, it will send the message
    to that SMTP server. Otherwise it will look for 
    `/usr/sbin/sendmail`, the typical location for the sendmail-style
    binary. To use sendmail from a different path, set `web.config.sendmail_path`.
    """
    attachments = kw.pop("attachments", [])
    mail = _EmailMessage(from_address, to_address, subject, message, headers, **kw)

    for a in attachments:
        if isinstance(a, dict):
            mail.attach(a['filename'], a['content'], a.get('content_type'))
        elif hasattr(a, 'read'): # file
            filename = os.path.basename(getattr(a, "name", ""))
            content_type = getattr(a, 'content_type', None)
            mail.attach(filename, a.read(), content_type)
        elif isinstance(a, basestring):
            f = open(a, 'rb')
            content = f.read()
            f.close()
            filename = os.path.basename(a)
            mail.attach(filename, content, None)
        else:
            raise ValueError, "Invalid attachment: %s" % repr(a)
            
    mail.send()

class _EmailMessage:
    def __init__(self, from_address, to_address, subject, message, headers=None, **kw):
        def listify(x):
            if not isinstance(x, list):
                return [safestr(x)]
            else:
                return [safestr(a) for a in x]
    
        subject = safestr(subject)
        message = safestr(message)

        from_address = safestr(from_address)
        to_address = listify(to_address)    
        cc = listify(kw.get('cc', []))
        bcc = listify(kw.get('bcc', []))
        recipients = to_address + cc + bcc

        import email.Utils
        self.from_address = email.Utils.parseaddr(from_address)[1]
        self.recipients = [email.Utils.parseaddr(r)[1] for r in recipients]        
    
        self.headers = dictadd({
          'From': from_address,
          'To': ", ".join(to_address),
          'Subject': subject
        }, headers or {})

        if cc:
            self.headers['Cc'] = ", ".join(cc)
    
        self.message = self.new_message()
        self.message.add_header("Content-Transfer-Encoding", "7bit")
        self.message.add_header("Content-Disposition", "inline")
        self.message.add_header("MIME-Version", "1.0")
        self.message.set_payload(message, 'utf-8')
        self.multipart = False
        
    def new_message(self):
        from email.Message import Message
        return Message()
        
    def attach(self, filename, content, content_type=None):
        if not self.multipart:
            msg = self.new_message()
            msg.add_header("Content-Type", "multipart/mixed")
            msg.attach(self.message)
            self.message = msg
            self.multipart = True
                        
        import mimetypes
        try:
            from email import encoders
        except:
            from email import Encoders as encoders
            
        content_type = content_type or mimetypes.guess_type(filename)[0] or "applcation/octet-stream"
        
        msg = self.new_message()
        msg.set_payload(content)
        msg.add_header('Content-Type', content_type)
        msg.add_header('Content-Disposition', 'attachment', filename=filename)
        
        if not content_type.startswith("text/"):
            encoders.encode_base64(msg)
            
        self.message.attach(msg)

    def prepare_message(self):
        for k, v in self.headers.iteritems():
            if k.lower() == "content-type":
                self.message.set_type(v)
            else:
                self.message.add_header(k, v)

        self.headers = {}

    def send(self):
        try:
            import webapi
        except ImportError:
            webapi = Storage(config=Storage())

        self.prepare_message()
        message_text = self.message.as_string()
    
        if webapi.config.get('smtp_server'):
            server = webapi.config.get('smtp_server')
            port = webapi.config.get('smtp_port', 0)
            username = webapi.config.get('smtp_username') 
            password = webapi.config.get('smtp_password')
            debug_level = webapi.config.get('smtp_debuglevel', None)
            starttls = webapi.config.get('smtp_starttls', False)

            import smtplib
            smtpserver = smtplib.SMTP(server, port)

            if debug_level:
                smtpserver.set_debuglevel(debug_level)

            if starttls:
                smtpserver.ehlo()
                smtpserver.starttls()
                smtpserver.ehlo()

            if username and password:
                smtpserver.login(username, password)

            smtpserver.sendmail(self.from_address, self.recipients, message_text)
            smtpserver.quit()
        elif webapi.config.get('email_engine') == 'aws':
            import boto.ses
            c = boto.ses.SESConnection(
              aws_access_key_id=webapi.config.get('aws_access_key_id'),
              aws_secret_access_key=web.api.config.get('aws_secret_access_key'))
            c.send_raw_email(self.from_address, message_text, self.from_recipients)
        else:
            sendmail = webapi.config.get('sendmail_path', '/usr/sbin/sendmail')
        
            assert not self.from_address.startswith('-'), 'security'
            for r in self.recipients:
                assert not r.startswith('-'), 'security'
                
            cmd = [sendmail, '-f', self.from_address] + self.recipients

            if subprocess:
                p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                p.stdin.write(message_text)
                p.stdin.close()
                p.wait()
            else:
                i, o = os.popen2(cmd)
                i.write(message)
                i.close()
                o.close()
                del i, o
                
    def __repr__(self):
        return "<EmailMessage>"
    
    def __str__(self):
        return self.message.as_string()

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = webapi
"""
Web API (wrapper around WSGI)
(from web.py)
"""

__all__ = [
    "config",
    "header", "debug",
    "input", "data",
    "setcookie", "cookies",
    "ctx", 
    "HTTPError", 

    # 200, 201, 202
    "OK", "Created", "Accepted",    
    "ok", "created", "accepted",
    
    # 301, 302, 303, 304, 307
    "Redirect", "Found", "SeeOther", "NotModified", "TempRedirect", 
    "redirect", "found", "seeother", "notmodified", "tempredirect",

    # 400, 401, 403, 404, 405, 406, 409, 410, 412, 415
    "BadRequest", "Unauthorized", "Forbidden", "NotFound", "NoMethod", "NotAcceptable", "Conflict", "Gone", "PreconditionFailed", "UnsupportedMediaType",
    "badrequest", "unauthorized", "forbidden", "notfound", "nomethod", "notacceptable", "conflict", "gone", "preconditionfailed", "unsupportedmediatype",

    # 500
    "InternalError", 
    "internalerror",
]

import sys, cgi, Cookie, pprint, urlparse, urllib
from utils import storage, storify, threadeddict, dictadd, intget, safestr

config = storage()
config.__doc__ = """
A configuration object for various aspects of web.py.

`debug`
   : when True, enables reloading, disabled template caching and sets internalerror to debugerror.
"""

class HTTPError(Exception):
    def __init__(self, status, headers={}, data=""):
        ctx.status = status
        for k, v in headers.items():
            header(k, v)
        self.data = data
        Exception.__init__(self, status)
        
def _status_code(status, data=None, classname=None, docstring=None):
    if data is None:
        data = status.split(" ", 1)[1]
    classname = status.split(" ", 1)[1].replace(' ', '') # 304 Not Modified -> NotModified    
    docstring = docstring or '`%s` status' % status

    def __init__(self, data=data, headers={}):
        HTTPError.__init__(self, status, headers, data)
        
    # trick to create class dynamically with dynamic docstring.
    return type(classname, (HTTPError, object), {
        '__doc__': docstring,
        '__init__': __init__
    })

ok = OK = _status_code("200 OK", data="")
created = Created = _status_code("201 Created")
accepted = Accepted = _status_code("202 Accepted")

class Redirect(HTTPError):
    """A `301 Moved Permanently` redirect."""
    def __init__(self, url, status='301 Moved Permanently', absolute=False):
        """
        Returns a `status` redirect to the new URL. 
        `url` is joined with the base URL so that things like 
        `redirect("about") will work properly.
        """
        newloc = urlparse.urljoin(ctx.path, url)

        if newloc.startswith('/'):
            if absolute:
                home = ctx.realhome
            else:
                home = ctx.home
            newloc = home + newloc

        headers = {
            'Content-Type': 'text/html',
            'Location': newloc
        }
        HTTPError.__init__(self, status, headers, "")

redirect = Redirect

class Found(Redirect):
    """A `302 Found` redirect."""
    def __init__(self, url, absolute=False):
        Redirect.__init__(self, url, '302 Found', absolute=absolute)

found = Found

class SeeOther(Redirect):
    """A `303 See Other` redirect."""
    def __init__(self, url, absolute=False):
        Redirect.__init__(self, url, '303 See Other', absolute=absolute)
    
seeother = SeeOther

class NotModified(HTTPError):
    """A `304 Not Modified` status."""
    def __init__(self):
        HTTPError.__init__(self, "304 Not Modified")

notmodified = NotModified

class TempRedirect(Redirect):
    """A `307 Temporary Redirect` redirect."""
    def __init__(self, url, absolute=False):
        Redirect.__init__(self, url, '307 Temporary Redirect', absolute=absolute)

tempredirect = TempRedirect

class BadRequest(HTTPError):
    """`400 Bad Request` error."""
    message = "bad request"
    def __init__(self, message=None):
        status = "400 Bad Request"
        headers = {'Content-Type': 'text/html'}
        HTTPError.__init__(self, status, headers, message or self.message)

badrequest = BadRequest

class Unauthorized(HTTPError):
    """`401 Unauthorized` error."""
    message = "unauthorized"
    def __init__(self):
        status = "401 Unauthorized"
        headers = {'Content-Type': 'text/html'}
        HTTPError.__init__(self, status, headers, self.message)

unauthorized = Unauthorized

class Forbidden(HTTPError):
    """`403 Forbidden` error."""
    message = "forbidden"
    def __init__(self):
        status = "403 Forbidden"
        headers = {'Content-Type': 'text/html'}
        HTTPError.__init__(self, status, headers, self.message)

forbidden = Forbidden

class _NotFound(HTTPError):
    """`404 Not Found` error."""
    message = "not found"
    def __init__(self, message=None):
        status = '404 Not Found'
        headers = {'Content-Type': 'text/html'}
        HTTPError.__init__(self, status, headers, message or self.message)

def NotFound(message=None):
    """Returns HTTPError with '404 Not Found' error from the active application.
    """
    if message:
        return _NotFound(message)
    elif ctx.get('app_stack'):
        return ctx.app_stack[-1].notfound()
    else:
        return _NotFound()

notfound = NotFound

class NoMethod(HTTPError):
    """A `405 Method Not Allowed` error."""
    def __init__(self, cls=None):
        status = '405 Method Not Allowed'
        headers = {}
        headers['Content-Type'] = 'text/html'
        
        methods = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE']
        if cls:
            methods = [method for method in methods if hasattr(cls, method)]

        headers['Allow'] = ', '.join(methods)
        data = None
        HTTPError.__init__(self, status, headers, data)
        
nomethod = NoMethod

class NotAcceptable(HTTPError):
    """`406 Not Acceptable` error."""
    message = "not acceptable"
    def __init__(self):
        status = "406 Not Acceptable"
        headers = {'Content-Type': 'text/html'}
        HTTPError.__init__(self, status, headers, self.message)

notacceptable = NotAcceptable

class Conflict(HTTPError):
    """`409 Conflict` error."""
    message = "conflict"
    def __init__(self):
        status = "409 Conflict"
        headers = {'Content-Type': 'text/html'}
        HTTPError.__init__(self, status, headers, self.message)

conflict = Conflict

class Gone(HTTPError):
    """`410 Gone` error."""
    message = "gone"
    def __init__(self):
        status = '410 Gone'
        headers = {'Content-Type': 'text/html'}
        HTTPError.__init__(self, status, headers, self.message)

gone = Gone

class PreconditionFailed(HTTPError):
    """`412 Precondition Failed` error."""
    message = "precondition failed"
    def __init__(self):
        status = "412 Precondition Failed"
        headers = {'Content-Type': 'text/html'}
        HTTPError.__init__(self, status, headers, self.message)

preconditionfailed = PreconditionFailed

class UnsupportedMediaType(HTTPError):
    """`415 Unsupported Media Type` error."""
    message = "unsupported media type"
    def __init__(self):
        status = "415 Unsupported Media Type"
        headers = {'Content-Type': 'text/html'}
        HTTPError.__init__(self, status, headers, self.message)

unsupportedmediatype = UnsupportedMediaType

class _InternalError(HTTPError):
    """500 Internal Server Error`."""
    message = "internal server error"
    
    def __init__(self, message=None):
        status = '500 Internal Server Error'
        headers = {'Content-Type': 'text/html'}
        HTTPError.__init__(self, status, headers, message or self.message)

def InternalError(message=None):
    """Returns HTTPError with '500 internal error' error from the active application.
    """
    if message:
        return _InternalError(message)
    elif ctx.get('app_stack'):
        return ctx.app_stack[-1].internalerror()
    else:
        return _InternalError()

internalerror = InternalError

def header(hdr, value, unique=False):
    """
    Adds the header `hdr: value` with the response.
    
    If `unique` is True and a header with that name already exists,
    it doesn't add a new one. 
    """
    hdr, value = safestr(hdr), safestr(value)
    # protection against HTTP response splitting attack
    if '\n' in hdr or '\r' in hdr or '\n' in value or '\r' in value:
        raise ValueError, 'invalid characters in header'
        
    if unique is True:
        for h, v in ctx.headers:
            if h.lower() == hdr.lower(): return
    
    ctx.headers.append((hdr, value))
    
def rawinput(method=None):
    """Returns storage object with GET or POST arguments.
    """
    method = method or "both"
    from cStringIO import StringIO

    def dictify(fs): 
        # hack to make web.input work with enctype='text/plain.
        if fs.list is None:
            fs.list = [] 

        return dict([(k, fs[k]) for k in fs.keys()])
    
    e = ctx.env.copy()
    a = b = {}
    
    if method.lower() in ['both', 'post', 'put']:
        if e['REQUEST_METHOD'] in ['POST', 'PUT']:
            if e.get('CONTENT_TYPE', '').lower().startswith('multipart/'):
                # since wsgi.input is directly passed to cgi.FieldStorage, 
                # it can not be called multiple times. Saving the FieldStorage
                # object in ctx to allow calling web.input multiple times.
                a = ctx.get('_fieldstorage')
                if not a:
                    fp = e['wsgi.input']
                    a = cgi.FieldStorage(fp=fp, environ=e, keep_blank_values=1)
                    ctx._fieldstorage = a
            else:
                fp = StringIO(data())
                a = cgi.FieldStorage(fp=fp, environ=e, keep_blank_values=1)
            a = dictify(a)

    if method.lower() in ['both', 'get']:
        e['REQUEST_METHOD'] = 'GET'
        b = dictify(cgi.FieldStorage(environ=e, keep_blank_values=1))

    def process_fieldstorage(fs):
        if isinstance(fs, list):
            return [process_fieldstorage(x) for x in fs]
        elif fs.filename is None:
            return fs.value
        else:
            return fs

    return storage([(k, process_fieldstorage(v)) for k, v in dictadd(b, a).items()])

def input(*requireds, **defaults):
    """
    Returns a `storage` object with the GET and POST arguments. 
    See `storify` for how `requireds` and `defaults` work.
    """
    _method = defaults.pop('_method', 'both')
    out = rawinput(_method)
    try:
        defaults.setdefault('_unicode', True) # force unicode conversion by default.
        return storify(out, *requireds, **defaults)
    except KeyError:
        raise badrequest()

def data():
    """Returns the data sent with the request."""
    if 'data' not in ctx:
        cl = intget(ctx.env.get('CONTENT_LENGTH'), 0)
        ctx.data = ctx.env['wsgi.input'].read(cl)
    return ctx.data

def setcookie(name, value, expires='', domain=None,
              secure=False, httponly=False, path=None):
    """Sets a cookie."""
    morsel = Cookie.Morsel()
    name, value = safestr(name), safestr(value)
    morsel.set(name, value, urllib.quote(value))
    if expires < 0:
        expires = -1000000000
    morsel['expires'] = expires
    morsel['path'] = path or ctx.homepath+'/'
    if domain:
        morsel['domain'] = domain
    if secure:
        morsel['secure'] = secure
    value = morsel.OutputString()
    if httponly:
        value += '; httponly'
    header('Set-Cookie', value)
        
def decode_cookie(value):
    r"""Safely decodes a cookie value to unicode. 
    
    Tries us-ascii, utf-8 and io8859 encodings, in that order.

    >>> decode_cookie('')
    u''
    >>> decode_cookie('asdf')
    u'asdf'
    >>> decode_cookie('foo \xC3\xA9 bar')
    u'foo \xe9 bar'
    >>> decode_cookie('foo \xE9 bar')
    u'foo \xe9 bar'
    """
    try:
        # First try plain ASCII encoding
        return unicode(value, 'us-ascii')
    except UnicodeError:
        # Then try UTF-8, and if that fails, ISO8859
        try:
            return unicode(value, 'utf-8')
        except UnicodeError:
            return unicode(value, 'iso8859', 'ignore')

def parse_cookies(http_cookie):
    r"""Parse a HTTP_COOKIE header and return dict of cookie names and decoded values.
        
    >>> sorted(parse_cookies('').items())
    []
    >>> sorted(parse_cookies('a=1').items())
    [('a', '1')]
    >>> sorted(parse_cookies('a=1%202').items())
    [('a', '1 2')]
    >>> sorted(parse_cookies('a=Z%C3%A9Z').items())
    [('a', 'Z\xc3\xa9Z')]
    >>> sorted(parse_cookies('a=1; b=2; c=3').items())
    [('a', '1'), ('b', '2'), ('c', '3')]
    >>> sorted(parse_cookies('a=1; b=w("x")|y=z; c=3').items())
    [('a', '1'), ('b', 'w('), ('c', '3')]
    >>> sorted(parse_cookies('a=1; b=w(%22x%22)|y=z; c=3').items())
    [('a', '1'), ('b', 'w("x")|y=z'), ('c', '3')]

    >>> sorted(parse_cookies('keebler=E=mc2').items())
    [('keebler', 'E=mc2')]
    >>> sorted(parse_cookies(r'keebler="E=mc2; L=\"Loves\"; fudge=\012;"').items())
    [('keebler', 'E=mc2; L="Loves"; fudge=\n;')]
    """
    #print "parse_cookies"
    if '"' in http_cookie:
        # HTTP_COOKIE has quotes in it, use slow but correct cookie parsing
        cookie = Cookie.SimpleCookie()
        try:
            cookie.load(http_cookie)
        except Cookie.CookieError:
            # If HTTP_COOKIE header is malformed, try at least to load the cookies we can by
            # first splitting on ';' and loading each attr=value pair separately
            cookie = Cookie.SimpleCookie()
            for attr_value in http_cookie.split(';'):
                try:
                    cookie.load(attr_value)
                except Cookie.CookieError:
                    pass
        cookies = dict((k, urllib.unquote(v.value)) for k, v in cookie.iteritems())
    else:
        # HTTP_COOKIE doesn't have quotes, use fast cookie parsing
        cookies = {}
        for key_value in http_cookie.split(';'):
            key_value = key_value.split('=', 1)
            if len(key_value) == 2:
                key, value = key_value
                cookies[key.strip()] = urllib.unquote(value.strip())
    return cookies

def cookies(*requireds, **defaults):
    r"""Returns a `storage` object with all the request cookies in it.
    
    See `storify` for how `requireds` and `defaults` work.

    This is forgiving on bad HTTP_COOKIE input, it tries to parse at least
    the cookies it can.
    
    The values are converted to unicode if _unicode=True is passed.
    """
    # If _unicode=True is specified, use decode_cookie to convert cookie value to unicode 
    if defaults.get("_unicode") is True:
        defaults['_unicode'] = decode_cookie
        
    # parse cookie string and cache the result for next time.
    if '_parsed_cookies' not in ctx:
        http_cookie = ctx.env.get("HTTP_COOKIE", "")
        ctx._parsed_cookies = parse_cookies(http_cookie)

    try:
        return storify(ctx._parsed_cookies, *requireds, **defaults)
    except KeyError:
        badrequest()
        raise StopIteration

def debug(*args):
    """
    Prints a prettyprinted version of `args` to stderr.
    """
    try: 
        out = ctx.environ['wsgi.errors']
    except: 
        out = sys.stderr
    for arg in args:
        print >> out, pprint.pformat(arg)
    return ''

def _debugwrite(x):
    try: 
        out = ctx.environ['wsgi.errors']
    except: 
        out = sys.stderr
    out.write(x)
debug.write = _debugwrite

ctx = context = threadeddict()

ctx.__doc__ = """
A `storage` object containing various information about the request:
  
`environ` (aka `env`)
   : A dictionary containing the standard WSGI environment variables.

`host`
   : The domain (`Host` header) requested by the user.

`home`
   : The base path for the application.

`ip`
   : The IP address of the requester.

`method`
   : The HTTP method used.

`path`
   : The path request.
   
`query`
   : If there are no query arguments, the empty string. Otherwise, a `?` followed
     by the query string.

`fullpath`
   : The full path requested, including query arguments (`== path + query`).

### Response Data

`status` (default: "200 OK")
   : The status code to be used in the response.

`headers`
   : A list of 2-tuples to be used in the response.

`output`
   : A string to be used as the response.
"""

if __name__ == "__main__":
    import doctest
    doctest.testmod()
########NEW FILE########
__FILENAME__ = webopenid
"""openid.py: an openid library for web.py

Notes:

 - This will create a file called .openid_secret_key in the 
   current directory with your secret key in it. If someone 
   has access to this file they can log in as any user. And 
   if the app can't find this file for any reason (e.g. you 
   moved the app somewhere else) then each currently logged 
   in user will get logged out.

 - State must be maintained through the entire auth process 
   -- this means that if you have multiple web.py processes 
   serving one set of URLs or if you restart your app often 
   then log ins will fail. You have to replace sessions and 
   store for things to work.

 - We set cookies starting with "openid_".

"""

import os
import random
import hmac
import __init__ as web
import openid.consumer.consumer
import openid.store.memstore

sessions = {}
store = openid.store.memstore.MemoryStore()

def _secret():
    try:
        secret = file('.openid_secret_key').read()
    except IOError:
        # file doesn't exist
        secret = os.urandom(20)
        file('.openid_secret_key', 'w').write(secret)
    return secret

def _hmac(identity_url):
    return hmac.new(_secret(), identity_url).hexdigest()

def _random_session():
    n = random.random()
    while n in sessions:
        n = random.random()
    n = str(n)
    return n

def status():
    oid_hash = web.cookies().get('openid_identity_hash', '').split(',', 1)
    if len(oid_hash) > 1:
        oid_hash, identity_url = oid_hash
        if oid_hash == _hmac(identity_url):
            return identity_url
    return None

def form(openid_loc):
    oid = status()
    if oid:
        return '''
        <form method="post" action="%s">
          <img src="http://openid.net/login-bg.gif" alt="OpenID" />
          <strong>%s</strong>
          <input type="hidden" name="action" value="logout" />
          <input type="hidden" name="return_to" value="%s" />
          <button type="submit">log out</button>
        </form>''' % (openid_loc, oid, web.ctx.fullpath)
    else:
        return '''
        <form method="post" action="%s">
          <input type="text" name="openid" value="" 
            style="background: url(http://openid.net/login-bg.gif) no-repeat; padding-left: 18px; background-position: 0 50%%;" />
          <input type="hidden" name="return_to" value="%s" />
          <button type="submit">log in</button>
        </form>''' % (openid_loc, web.ctx.fullpath)

def logout():
    web.setcookie('openid_identity_hash', '', expires=-1)

class host:
    def POST(self):
        # unlike the usual scheme of things, the POST is actually called
        # first here
        i = web.input(return_to='/')
        if i.get('action') == 'logout':
            logout()
            return web.redirect(i.return_to)

        i = web.input('openid', return_to='/')

        n = _random_session()
        sessions[n] = {'webpy_return_to': i.return_to}
        
        c = openid.consumer.consumer.Consumer(sessions[n], store)
        a = c.begin(i.openid)
        f = a.redirectURL(web.ctx.home, web.ctx.home + web.ctx.fullpath)

        web.setcookie('openid_session_id', n)
        return web.redirect(f)

    def GET(self):
        n = web.cookies('openid_session_id').openid_session_id
        web.setcookie('openid_session_id', '', expires=-1)
        return_to = sessions[n]['webpy_return_to']

        c = openid.consumer.consumer.Consumer(sessions[n], store)
        a = c.complete(web.input(), web.ctx.home + web.ctx.fullpath)

        if a.status.lower() == 'success':
            web.setcookie('openid_identity_hash', _hmac(a.identity_url) + ',' + a.identity_url)

        del sessions[n]
        return web.redirect(return_to)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI Utilities
(from web.py)
"""

import os, sys

import http
import webapi as web
from utils import listget
from net import validaddr, validip
import httpserver
    
def runfcgi(func, addr=('localhost', 8000)):
    """Runs a WSGI function as a FastCGI server."""
    import flup.server.fcgi as flups
    return flups.WSGIServer(func, multiplexed=True, bindAddress=addr, debug=False).run()

def runscgi(func, addr=('localhost', 4000)):
    """Runs a WSGI function as an SCGI server."""
    import flup.server.scgi as flups
    return flups.WSGIServer(func, bindAddress=addr, debug=False).run()

def runwsgi(func):
    """
    Runs a WSGI-compatible `func` using FCGI, SCGI, or a simple web server,
    as appropriate based on context and `sys.argv`.
    """
    
    if os.environ.has_key('SERVER_SOFTWARE'): # cgi
        os.environ['FCGI_FORCE_CGI'] = 'Y'

    if (os.environ.has_key('PHP_FCGI_CHILDREN') #lighttpd fastcgi
      or os.environ.has_key('SERVER_SOFTWARE')):
        return runfcgi(func, None)
    
    if 'fcgi' in sys.argv or 'fastcgi' in sys.argv:
        args = sys.argv[1:]
        if 'fastcgi' in args: args.remove('fastcgi')
        elif 'fcgi' in args: args.remove('fcgi')
        if args:
            return runfcgi(func, validaddr(args[0]))
        else:
            return runfcgi(func, None)
    
    if 'scgi' in sys.argv:
        args = sys.argv[1:]
        args.remove('scgi')
        if args:
            return runscgi(func, validaddr(args[0]))
        else:
            return runscgi(func)
    
    return httpserver.runsimple(func, validip(listget(sys.argv, 1, '')))
    
def _is_dev_mode():
    # Some embedded python interpreters won't have sys.arv
    # For details, see https://github.com/webpy/webpy/issues/87
    argv = getattr(sys, "argv", [])

    # quick hack to check if the program is running in dev mode.
    if os.environ.has_key('SERVER_SOFTWARE') \
        or os.environ.has_key('PHP_FCGI_CHILDREN') \
        or 'fcgi' in argv or 'fastcgi' in argv \
        or 'mod_wsgi' in argv:
            return False
    return True

# When running the builtin-server, enable debug mode if not already set.
web.config.setdefault('debug', _is_dev_mode())

########NEW FILE########
__FILENAME__ = ssl_builtin
"""A library for integrating Python's builtin ``ssl`` library with CherryPy.

The ssl module must be importable for SSL functionality.

To use this module, set ``CherryPyWSGIServer.ssl_adapter`` to an instance of
``BuiltinSSLAdapter``.
"""

try:
    import ssl
except ImportError:
    ssl = None

from cherrypy import wsgiserver


class BuiltinSSLAdapter(wsgiserver.SSLAdapter):
    """A wrapper for integrating Python's builtin ssl module with CherryPy."""
    
    certificate = None
    """The filename of the server SSL certificate."""
    
    private_key = None
    """The filename of the server's private key file."""
    
    def __init__(self, certificate, private_key, certificate_chain=None):
        if ssl is None:
            raise ImportError("You must install the ssl module to use HTTPS.")
        self.certificate = certificate
        self.private_key = private_key
        self.certificate_chain = certificate_chain
    
    def bind(self, sock):
        """Wrap and return the given socket."""
        return sock
    
    def wrap(self, sock):
        """Wrap and return the given socket, plus WSGI environ entries."""
        try:
            s = ssl.wrap_socket(sock, do_handshake_on_connect=True,
                    server_side=True, certfile=self.certificate,
                    keyfile=self.private_key, ssl_version=ssl.PROTOCOL_SSLv23)
        except ssl.SSLError, e:
            if e.errno == ssl.SSL_ERROR_EOF:
                # This is almost certainly due to the cherrypy engine
                # 'pinging' the socket to assert it's connectable;
                # the 'ping' isn't SSL.
                return None, {}
            elif e.errno == ssl.SSL_ERROR_SSL:
                if e.args[1].endswith('http request'):
                    # The client is speaking HTTP to an HTTPS server.
                    raise wsgiserver.NoSSLError
            raise
        return s, self.get_environ(s)
    
    # TODO: fill this out more with mod ssl env
    def get_environ(self, sock):
        """Create WSGI environ entries to be merged into each request."""
        cipher = sock.cipher()
        ssl_environ = {
            "wsgi.url_scheme": "https",
            "HTTPS": "on",
            'SSL_PROTOCOL': cipher[1],
            'SSL_CIPHER': cipher[0]
##            SSL_VERSION_INTERFACE 	string 	The mod_ssl program version
##            SSL_VERSION_LIBRARY 	string 	The OpenSSL program version
            }
        return ssl_environ
    
    def makefile(self, sock, mode='r', bufsize=-1):
        return wsgiserver.CP_fileobject(sock, mode, bufsize)


########NEW FILE########
__FILENAME__ = ssl_pyopenssl
"""A library for integrating pyOpenSSL with CherryPy.

The OpenSSL module must be importable for SSL functionality.
You can obtain it from http://pyopenssl.sourceforge.net/

To use this module, set CherryPyWSGIServer.ssl_adapter to an instance of
SSLAdapter. There are two ways to use SSL:

Method One
----------

 * ``ssl_adapter.context``: an instance of SSL.Context.

If this is not None, it is assumed to be an SSL.Context instance,
and will be passed to SSL.Connection on bind(). The developer is
responsible for forming a valid Context object. This approach is
to be preferred for more flexibility, e.g. if the cert and key are
streams instead of files, or need decryption, or SSL.SSLv3_METHOD
is desired instead of the default SSL.SSLv23_METHOD, etc. Consult
the pyOpenSSL documentation for complete options.

Method Two (shortcut)
---------------------

 * ``ssl_adapter.certificate``: the filename of the server SSL certificate.
 * ``ssl_adapter.private_key``: the filename of the server's private key file.

Both are None by default. If ssl_adapter.context is None, but .private_key
and .certificate are both given and valid, they will be read, and the
context will be automatically created from them.
"""

import socket
import threading
import time

from cherrypy import wsgiserver

try:
    from OpenSSL import SSL
    from OpenSSL import crypto
except ImportError:
    SSL = None


class SSL_fileobject(wsgiserver.CP_fileobject):
    """SSL file object attached to a socket object."""
    
    ssl_timeout = 3
    ssl_retry = .01
    
    def _safe_call(self, is_reader, call, *args, **kwargs):
        """Wrap the given call with SSL error-trapping.
        
        is_reader: if False EOF errors will be raised. If True, EOF errors
        will return "" (to emulate normal sockets).
        """
        start = time.time()
        while True:
            try:
                return call(*args, **kwargs)
            except SSL.WantReadError:
                # Sleep and try again. This is dangerous, because it means
                # the rest of the stack has no way of differentiating
                # between a "new handshake" error and "client dropped".
                # Note this isn't an endless loop: there's a timeout below.
                time.sleep(self.ssl_retry)
            except SSL.WantWriteError:
                time.sleep(self.ssl_retry)
            except SSL.SysCallError, e:
                if is_reader and e.args == (-1, 'Unexpected EOF'):
                    return ""
                
                errnum = e.args[0]
                if is_reader and errnum in wsgiserver.socket_errors_to_ignore:
                    return ""
                raise socket.error(errnum)
            except SSL.Error, e:
                if is_reader and e.args == (-1, 'Unexpected EOF'):
                    return ""
                
                thirdarg = None
                try:
                    thirdarg = e.args[0][0][2]
                except IndexError:
                    pass
                
                if thirdarg == 'http request':
                    # The client is talking HTTP to an HTTPS server.
                    raise wsgiserver.NoSSLError()
                
                raise wsgiserver.FatalSSLAlert(*e.args)
            except:
                raise
            
            if time.time() - start > self.ssl_timeout:
                raise socket.timeout("timed out")
    
    def recv(self, *args, **kwargs):
        buf = []
        r = super(SSL_fileobject, self).recv
        while True:
            data = self._safe_call(True, r, *args, **kwargs)
            buf.append(data)
            p = self._sock.pending()
            if not p:
                return "".join(buf)
    
    def sendall(self, *args, **kwargs):
        return self._safe_call(False, super(SSL_fileobject, self).sendall,
                               *args, **kwargs)

    def send(self, *args, **kwargs):
        return self._safe_call(False, super(SSL_fileobject, self).send,
                               *args, **kwargs)


class SSLConnection:
    """A thread-safe wrapper for an SSL.Connection.
    
    ``*args``: the arguments to create the wrapped ``SSL.Connection(*args)``.
    """
    
    def __init__(self, *args):
        self._ssl_conn = SSL.Connection(*args)
        self._lock = threading.RLock()
    
    for f in ('get_context', 'pending', 'send', 'write', 'recv', 'read',
              'renegotiate', 'bind', 'listen', 'connect', 'accept',
              'setblocking', 'fileno', 'close', 'get_cipher_list',
              'getpeername', 'getsockname', 'getsockopt', 'setsockopt',
              'makefile', 'get_app_data', 'set_app_data', 'state_string',
              'sock_shutdown', 'get_peer_certificate', 'want_read',
              'want_write', 'set_connect_state', 'set_accept_state',
              'connect_ex', 'sendall', 'settimeout', 'gettimeout'):
        exec("""def %s(self, *args):
        self._lock.acquire()
        try:
            return self._ssl_conn.%s(*args)
        finally:
            self._lock.release()
""" % (f, f))
    
    def shutdown(self, *args):
        self._lock.acquire()
        try:
            # pyOpenSSL.socket.shutdown takes no args
            return self._ssl_conn.shutdown()
        finally:
            self._lock.release()


class pyOpenSSLAdapter(wsgiserver.SSLAdapter):
    """A wrapper for integrating pyOpenSSL with CherryPy."""
    
    context = None
    """An instance of SSL.Context."""
    
    certificate = None
    """The filename of the server SSL certificate."""
    
    private_key = None
    """The filename of the server's private key file."""
    
    certificate_chain = None
    """Optional. The filename of CA's intermediate certificate bundle.
    
    This is needed for cheaper "chained root" SSL certificates, and should be
    left as None if not required."""
    
    def __init__(self, certificate, private_key, certificate_chain=None):
        if SSL is None:
            raise ImportError("You must install pyOpenSSL to use HTTPS.")
        
        self.context = None
        self.certificate = certificate
        self.private_key = private_key
        self.certificate_chain = certificate_chain
        self._environ = None
    
    def bind(self, sock):
        """Wrap and return the given socket."""
        if self.context is None:
            self.context = self.get_context()
        conn = SSLConnection(self.context, sock)
        self._environ = self.get_environ()
        return conn
    
    def wrap(self, sock):
        """Wrap and return the given socket, plus WSGI environ entries."""
        return sock, self._environ.copy()
    
    def get_context(self):
        """Return an SSL.Context from self attributes."""
        # See http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/442473
        c = SSL.Context(SSL.SSLv23_METHOD)
        c.use_privatekey_file(self.private_key)
        if self.certificate_chain:
            c.load_verify_locations(self.certificate_chain)
        c.use_certificate_file(self.certificate)
        return c
    
    def get_environ(self):
        """Return WSGI environ entries to be merged into each request."""
        ssl_environ = {
            "HTTPS": "on",
            # pyOpenSSL doesn't provide access to any of these AFAICT
##            'SSL_PROTOCOL': 'SSLv2',
##            SSL_CIPHER 	string 	The cipher specification name
##            SSL_VERSION_INTERFACE 	string 	The mod_ssl program version
##            SSL_VERSION_LIBRARY 	string 	The OpenSSL program version
            }
        
        if self.certificate:
            # Server certificate attributes
            cert = open(self.certificate, 'rb').read()
            cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert)
            ssl_environ.update({
                'SSL_SERVER_M_VERSION': cert.get_version(),
                'SSL_SERVER_M_SERIAL': cert.get_serial_number(),
##                'SSL_SERVER_V_START': Validity of server's certificate (start time),
##                'SSL_SERVER_V_END': Validity of server's certificate (end time),
                })
            
            for prefix, dn in [("I", cert.get_issuer()),
                               ("S", cert.get_subject())]:
                # X509Name objects don't seem to have a way to get the
                # complete DN string. Use str() and slice it instead,
                # because str(dn) == "<X509Name object '/C=US/ST=...'>"
                dnstr = str(dn)[18:-2]
                
                wsgikey = 'SSL_SERVER_%s_DN' % prefix
                ssl_environ[wsgikey] = dnstr
                
                # The DN should be of the form: /k1=v1/k2=v2, but we must allow
                # for any value to contain slashes itself (in a URL).
                while dnstr:
                    pos = dnstr.rfind("=")
                    dnstr, value = dnstr[:pos], dnstr[pos + 1:]
                    pos = dnstr.rfind("/")
                    dnstr, key = dnstr[:pos], dnstr[pos + 1:]
                    if key and value:
                        wsgikey = 'SSL_SERVER_%s_DN_%s' % (prefix, key)
                        ssl_environ[wsgikey] = value
        
        return ssl_environ
    
    def makefile(self, sock, mode='r', bufsize=-1):
        if SSL and isinstance(sock, SSL.ConnectionType):
            timeout = sock.gettimeout()
            f = SSL_fileobject(sock, mode, bufsize)
            f.ssl_timeout = timeout
            return f
        else:
            return wsgiserver.CP_fileobject(sock, mode, bufsize)


########NEW FILE########
__FILENAME__ = api_handlers
import itertools
import json
import logging
import os.path
import urllib
import xml.etree.cElementTree as ET

import third_party.web as web

import base.api
import base.atom
import base.paths

class ApiHandler:
  def _read_json_data_file(self, data_file_name):
    data_path = os.path.join(
        web.config.reader_archive_directory, 'data', data_file_name)
    with open(data_path) as data_file:
      return json.load(data_file)

class ItemContentsHandler(ApiHandler):
  def _fetch_render_item_refs(self, stream_id, item_refs, continuation):
    item_entries = []
    for item_ref in item_refs:
      item_entry = base.atom.load_item_entry(
          web.config.reader_archive_directory, item_ref.item_id)
      if item_entry:
        item_entries.append(item_entry)

    item_refs_by_item_id = {i.item_id: i for i in item_refs}
    stream_ids_by_item_id = web.config.reader_stream_ids_by_item_id
    friends_by_stream_id = web.config.reader_friends_by_stream_id

    items_json = []
    for e in item_entries:
      item_stream_ids = stream_ids_by_item_id.get(e.item_id.int_form, [])
      timestamp_usec = item_refs_by_item_id[e.item_id].timestamp_usec
      if not timestamp_usec:
        # We don't have timestamps in the item ref when doing a separate item
        # contents request.
        timestamp_usec = e.crawl_time_msec * 1000
      item_json = {
        'id': e.item_id.atom_form,
        'crawlTimeMsec': str(int(timestamp_usec/1000)),
        'timestampUsec': str(timestamp_usec),
        'published': e.published_sec,
        'updated': e.updated_sec,
        'title': e.title,
        'content': {
          # Unfortunately Atom output did not appear to contain writing
          # direction.
          'direction': 'ltr',
          'content': e.content,
        },
        'categories': item_stream_ids,
        'origin': {
          'streamId': e.origin.stream_id,
          'title': e.origin.title,
          'htmlUrl': e.origin.html_url,
        },
        'annotations': [
          {
            'content': a.content,
            'author': a.author_name,
            'userId': a.author_user_id,
            'profileId': a.author_profile_id,
          } for a in e.annotations
        ],
        # We have comment data, but the Reader JS can't show it, so there's no
        # point in outputting it.
        'comments': [],
        # Ditto for likers
        'likingUsers': [],
        # Prevents the keep unread item action from showing up.
        'isReadStateLocked': True,
      }

      vias_json = []
      for item_stream_id in item_stream_ids:
        if item_stream_id in friends_by_stream_id:
          friend = friends_by_stream_id[item_stream_id]
          if friend.is_current_user:
            continue
          vias_json.append({
            'href': 'http://www.google.com/reader/public/atom/%s' % item_stream_id,
            'title': '%s\'s shared items' % friend.display_name,
          })
      if vias_json:
        item_json['via'] = vias_json

      for link in e.links:
        if not link.relation:
          continue
        link_json = {}
        if link.href:
          link_json['href'] = link.href
        if link.type:
          link_json['type'] = link.type
        if link.title:
          link_json['title'] = link.title
        if link.length:
          link_json['length'] = link.length
        if link_json:
          item_json.setdefault(link.relation, []).append(link_json)

      if e.author_name:
        item_json['author'] = e.author_name

      items_json.append(item_json)

    response_json = {
      'direction': 'ltr',
      'id': stream_id,
      'title': '', # TODO
      'items': items_json,
    }

    if stream_id in friends_by_stream_id:
      response_json['author'] = friends_by_stream_id[stream_id].display_name
    if continuation:
      response_json['continuation'] = continuation

    return json.dumps(response_json)

class SubscriptionList(ApiHandler):
  def GET(self):
    subscriptions_json = self._read_json_data_file('subscriptions.json')
    subscriptions = [
        base.api.Subscription.from_json(s) for s in subscriptions_json]

    return json.dumps({
      'subscriptions': [
        {
          'id': s.stream_id,
          'title': s.title,
          'categories': [
            {
              'id': si,
              'label': si[si.rfind('/') + 1:],
            } for si in s.insert_stream_ids
          ],
          'sortid': s.sort_id,
          'firstitemmsec': str(int(s.first_item_usec/1000)),
          'htmlUrl': s.html_url,
        } for s in subscriptions
      ]
    })


class TagList(ApiHandler):
  def GET(self):
    tags_json = self._read_json_data_file('tags.json')
    tags = [base.api.Tag.from_json(t) for t in tags_json]

    return json.dumps({
      'tags': [
        {
          'id': t.stream_id,
          'sortid': t.sort_id,
        } for t in tags
      ]
    })


class RecommendationList(ApiHandler):
  def GET(self):
    try:
      recommendations_json = self._read_json_data_file('recommendations.json')
    except:
      logging.warning('Could not load preferences, using empty list',
          exc_info=True)
      recommendations_json = []

    recommendations = [
        base.api.Recommendation.from_json(r) for r in recommendations_json]
    count = int(web.input(n=4).n)
    if count < len(recommendations):
      recommendations = recommendations[:count]

    return json.dumps({
      'recs': [
        {
          'streamId': r.stream_id,
          'title': r.title,
          'snippet': '',
          'impressionTime': 0,
        } for r in recommendations
      ]
    })


class PreferenceList(ApiHandler):
  def GET(self):
    try:
      preferences_json = self._read_json_data_file('preferences.json')
    except:
      logging.warning('Could not load preferences, using defaults',
          exc_info=True)
      preferences_json = {}

    # Disable G+ share and email actions, since they won't work. Abdulla: your
    # feature finally gets some use!
    preferences_json['item-actions'] = json.dumps({
      'plusone-action': True,
      'share-action': False,
      'email-action': False,
      'tags-action': True
    })

    # Oldest first is no longer limited to the last 30 days, don't show the
    # interruption that warns about that.
    preferences_json['show-oldest-interrupt'] = 'false'

    # We want to show all archived items by default.
    preferences_json['read-items-visible'] = 'true'

    # Always start with the overview page, since that shows some explanatory
    # text.
    preferences_json['start-page'] = 'home'

    # Turn off more "helpful" interruptions.
    preferences_json['show-scroll-help'] = 'false'
    preferences_json['show-search-clarification'] = 'false'
    preferences_json['show-blogger-following-intro'] = 'false'

    if 'lhn-prefs' in preferences_json:
      # Make sure that we show all unread counts for the LHN sections, since
      # they're not really unread counts anymore.
      lhn_prefs = json.loads(preferences_json['lhn-prefs'])
      for section_json in lhn_prefs.values():
        section_json['suc'] = 'true'
      # Collapse the recommendations/explore section by default, it's not really
      # the user's data.
      if 'recommendations' in lhn_prefs:
        lhn_prefs['recommendations']['ism'] = 'true'
      preferences_json['lhn-prefs'] = json.dumps(lhn_prefs)

    return json.dumps({
      'prefs': [
        {
          'id': id,
          'value': value,
        } for id, value in preferences_json.iteritems()
      ]
    })


class StreamPreferenceList(ApiHandler):
  def GET(self):
    try:
      stream_preferences_json = self._read_json_data_file(
          'stream-preferences.json')
    except:
      logging.warning('Could not load stream preferences, using defaults',
          exc_info=True)
      stream_preferences_json = {}

    return json.dumps({
      'streamprefs': {
        stream_id: [
          {
            'id': id,
            'value': value,
          } for id, value in prefs.iteritems()
        ] for stream_id, prefs in stream_preferences_json.iteritems()
      }
    })


class UnreadCount(ApiHandler):
  def GET(self):
    return json.dumps({
      'max': 1000000,
      'unreadcounts': [
        {
          'id': stream_id,
          'count': len(stream_items[0]),
        } for stream_id, stream_items in
            web.config.reader_stream_items_by_stream_id.iteritems()
      ]
    })


class StreamContents(ItemContentsHandler):
  def GET(self, stream_id):
    stream_id = urllib.unquote_plus(stream_id)
    input = web.input(n=20, c=0, r='d')
    count = int(input.n)
    continuation = int(input.c)
    ranking = input.r

    # The read and starred items stream don't display a sorting UI, so they'll
    # always be requested in the newest-first order. We instead support
    # generating a URL that will include the desired sorting in the stream ID
    if stream_id.endswith('-oldest-first'):
      stream_id = stream_id[:-13]
      ranking = 'o'

    if stream_id.startswith('user/-/'):
      stream_id = 'user/' + web.config.reader_user_info.user_id + stream_id[6:]

    stream_items = web.config.reader_stream_items_by_stream_id.get(stream_id)
    if not stream_items:
      return web.notfound('Stream ID %s was not archived' % stream_id)

    item_refs = []
    if ranking != 'o':
      start_index = continuation
      end_index = continuation + count
    else:
      start_index = -continuation - count
      end_index = -continuation if continuation else None
    chunk_stream_item_ids = stream_items[0][start_index:end_index]
    chunk_stream_item_timestamps = stream_items[1][start_index:end_index]
    if ranking == 'o':
      chunk_stream_item_ids = tuple(reversed(chunk_stream_item_ids))
      chunk_stream_item_timestamps = tuple(reversed(chunk_stream_item_timestamps))

    for item_id_int_form, timestamp_usec in itertools.izip(
        chunk_stream_item_ids, chunk_stream_item_timestamps):
      item_id = base.api.ItemId(int_form=item_id_int_form)
      item_refs.append(
          base.api.ItemRef(item_id=item_id, timestamp_usec=timestamp_usec))

    next_continuation = continuation + count \
        if continuation + count < len(stream_items[0]) else None
    return self._fetch_render_item_refs(stream_id, item_refs, next_continuation)

class StreamItemsIds(ApiHandler):
  def GET(self):
    input = web.input(r='d')
    stream_id = input.s
    count = int(input.n)
    ranking = input.r

    stream_items = web.config.reader_stream_items_by_stream_id.get(stream_id)
    if not stream_items:
      return web.notfound('Stream ID %s was not archived' % stream_id)

    item_refs = [
      base.api.ItemRef(base.api.ItemId(item_id_int_form), timestamp_usec)
      for item_id_int_form, timestamp_usec in itertools.izip(*stream_items)
    ]

    return json.dumps({
      'itemRefs': [
        {
          'id': item_ref.item_id.decimal_form,
          'timestampUsec': item_ref.timestamp_usec,
          'directStreamIds': [],
        } for item_ref in item_refs
      ]
    })

class StreamItemsContents(ItemContentsHandler):
  def POST(self):
    input = web.input(i=[])

    item_refs = []
    for item_id_decimal_form in input.i:
      item_refs.append(base.api.ItemRef(
          base.api.item_id_from_decimal_form(item_id_decimal_form),
          timestamp_usec=0))

    return self._fetch_render_item_refs(input.rs, item_refs, continuation=None)

########NEW FILE########
__FILENAME__ = zombie_reader
import argparse
import datetime
import itertools
import json
import logging
import operator
import os.path
import socket
import sys
import time
import webbrowser

import third_party.web as web

import api_handlers
import base.api
import base.log
import base.middleware
import base.paths
import base.tag_helper

_READER_STATIC_PATH_PREFIX = '/reader/ui/'
_BASE_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
_STATIC_DIRECTORY = os.path.abspath(os.path.join(_BASE_DIRECTORY, 'static'))

urls = (
    '/', 'RedirectToMain',
    '/reader/view', 'RedirectToMain',
    '/reader/view/', 'Main',

    # HTML handlers
    '/reader/overview', 'Overview',
    '/reader/embediframe', 'EmbedIframe',
    '/reader/trends', 'Trends',

    # API handlers
    '/reader/api/0/subscription/list', 'api_handlers.SubscriptionList',
    '/reader/api/0/tag/list', 'api_handlers.TagList',
    '/reader/api/0/recommendation/list', 'api_handlers.RecommendationList',
    '/reader/api/0/preference/list', 'api_handlers.PreferenceList',
    '/reader/api/0/preference/stream/list', 'api_handlers.StreamPreferenceList',
    '/reader/api/0/unread-count', 'api_handlers.UnreadCount',
    '/reader/api/0/stream/contents/(.+)', 'api_handlers.StreamContents',
    '/reader/api/0/stream/items/ids', 'api_handlers.StreamItemsIds',
    '/reader/api/0/stream/items/contents', 'api_handlers.StreamItemsContents',

    # Stubbed-out handlers
    '/reader/directory', 'StubbedOut',
    '/reader/logging', 'StubbedOut',
    '/reader/js-load-error', 'StubbedOut',
    '/reader/api/0/edit-tag', 'StubbedOut',
    '/reader/api/0/preference/stream/set', 'StubbedOut',
    '/reader/api/0/preference/stream/set', 'StubbedOut',
    '/reader/api/0/preference/set', 'StubbedOut',
    '/reader/api/0/token', 'StubbedOut',
)

render = web.template.render(
    os.path.join(_BASE_DIRECTORY, 'templates'),
    globals={
      'js_escape': json.dumps,
    })

class RedirectToMain:
  def GET(self):
    raise web.redirect('/reader/view/')

class Main:
  def GET(self):
    return render.main(user_info=web.config.reader_user_info)

class Overview:
  def GET(self):
    user_id = web.config.reader_user_info.user_id
    stream_items_by_stream_id = web.config.reader_stream_items_by_stream_id

    def state_stream_id(state_tag_name):
      return base.tag_helper.TagHelper(
          user_id).state_tag(state_tag_name).stream_id

    def load_item_entries(state_tag_name, start_index, end_index):
      stream_id = state_stream_id(state_tag_name)
      if not stream_id in stream_items_by_stream_id:
        logging.info('%s %s had no entries', state_tag_name, stream_id)
        return []

      stream_item_ids = stream_items_by_stream_id[stream_id][0]
      item_ids = [
          base.api.ItemId(int_form=i)
          for i in stream_item_ids[start_index:end_index]
      ]
      item_timestamps = stream_items_by_stream_id[stream_id][1][start_index:end_index]
      item_entries = []
      for item_id, item_timestamp_usec in \
          itertools.izip(item_ids, item_timestamps):
        item_entry = base.atom.load_item_entry(
            web.config.reader_archive_directory, item_id)
        if item_entry:
          item_entry.display_timestamp = datetime.datetime.utcfromtimestamp(
              item_timestamp_usec/1000000).strftime('%B %d, %Y')
          item_entries.append(item_entry)
      return item_entries

    def load_recent_item_entries(state_tag_name):
      return load_item_entries(state_tag_name, 0, 2)

    def load_first_item_entry(state_tag_name):
      entries = load_item_entries(state_tag_name, -1, None)
      return entries[0] if entries else None

    def item_count(state_tag_name):
      stream_id = state_stream_id(state_tag_name)
      if stream_id in stream_items_by_stream_id:
        return len(stream_items_by_stream_id[stream_id][0])
      return 0

    followed_friends = [
        f for f in web.config.reader_friends
        if f.is_following and not f.is_current_user and
            stream_items_by_stream_id.get(f.stream_id, ([], []))[0]
    ]
    for friend in followed_friends:
      friend.item_count = len(stream_items_by_stream_id[friend.stream_id][0])
    followed_friends.sort(key=lambda f: f.display_name)

    return render.overview(
      user_id=user_id,
      recent_read_items=load_recent_item_entries('read'),
      recent_kept_unread_items=load_recent_item_entries('kept-unread'),
      recent_starred_items=load_recent_item_entries('starred'),
      recent_broadcast_items=load_recent_item_entries('broadcast'),

      first_read_item=load_first_item_entry('read'),
      read_item_count=item_count('read'),
      first_starred_item=load_first_item_entry('starred'),
      starred_item_count=item_count('starred'),
      first_broadcast_item=load_first_item_entry('broadcast'),
      broadcast_item_count=item_count('broadcast'),

      followed_friends=followed_friends,
      broadcast_friends_item_count=item_count('broadcast-friends'))

class EmbedIframe:
  def GET(self):
    input = web.input()
    return render.embed_iframe(
        src=input.src, width=input.width, height=input.height)

class Trends:
  def GET(self):
    return render.trends()

class StubbedOut:
  '''No-op handler, just avoids a 404.'''
  def GET(self):
    return 'Not implemented.'

  def POST(self):
    return 'Not implemented.'

def main():
  base.log.init()

  parser = argparse.ArgumentParser(
      description='Reanimated Google Reader\'s corpse to allow the Reader UI '
                  'to be used to browse a reader_archive-generated directory')

  parser.add_argument('archive_directory',
                      help='Directory to load archive data from.')
  parser.add_argument('--port', type=int, default=8074,
                      help='Port that the HTTP server will run on.')
  parser.add_argument('--disable_launch_in_browser' ,action='store_true',
                      help='Don\'t open the server in the local browser. Mainly '
                            'meant for use during development')

  args = parser.parse_args()

  archive_directory = base.paths.normalize(args.archive_directory)
  if not os.path.exists(archive_directory):
    logging.error('Could not find archive directory %s', archive_directory)
    syst.exit(1)
  web.config.reader_archive_directory = archive_directory

  _load_archive_data(archive_directory)

  app = web.application(urls, globals())

  homepage_url = 'http://%s:%d/reader/view/' % (socket.gethostname(), args.port)
  logging.info('Serving at %s', homepage_url)
  if not args.disable_launch_in_browser:
    webbrowser.open_new_tab(homepage_url)

  _run_app(app, args.port)

def _load_archive_data(archive_directory):
  _load_user_info()
  user_info = web.config.reader_user_info
  logging.info('Loading archive for %s', user_info.email or user_info.user_name)
  _load_friends()
  _load_streams(archive_directory)

def _load_friends():
  friends = [base.api.Friend.from_json(t) for t in _data_json('friends.json')]
  friends_by_stream_id = {f.stream_id: f for f in friends}
  web.config.reader_friends = friends
  web.config.reader_friends_by_stream_id = friends_by_stream_id

def _load_streams(archive_directory):
  stream_items_by_stream_id = {}
  stream_ids_by_item_id = {}
  streams_directory = os.path.join(archive_directory, 'streams')
  stream_file_names = os.listdir(streams_directory)
  logging.info('Loading item refs for %d streams', len(stream_file_names))
  start_time = time.time()
  for i, stream_file_name in enumerate(stream_file_names):
    with open(os.path.join(streams_directory, stream_file_name)) as stream_file:
      try:
        stream_json = json.load(stream_file)
      except ValueError, e:
        logging.warning(
            'Could not parse JSON in stream file %s: %s', stream_file_name, e)
        continue
      stream_id = stream_json['stream_id']
      stream_items = tuple(
          (timestamp_usec, int(item_id_json, 16))
          for item_id_json, timestamp_usec
              in stream_json['item_refs'].iteritems()
      )
      stream_items = sorted(
          stream_items, key=operator.itemgetter(0), reverse=True)

      # We store the timestamps and item IDs in parallel tuples to reduce the
      # overhead of having a tuple per item.
      stream_items_by_stream_id[stream_id] = (
          tuple(si[1] for si in stream_items),
          tuple(si[0] for si in stream_items)
      )
      # Don't care about non-user streams (for labeling as categories), or
      # about the reading-list stream (applied to most items, not used by the
      # UI).
      if stream_id.startswith('user/') and \
          not stream_id.endswith('/reading-list'):
        for _, item_id_int_form in stream_items:
          stream_ids_by_item_id.setdefault(
              item_id_int_form, []).append(stream_id)
      if i % 25 == 0:
        logging.debug('  %d/%d streams loaded', i + 1, len(stream_file_names))
  web.config.reader_stream_items_by_stream_id= stream_items_by_stream_id
  web.config.reader_stream_ids_by_item_id = stream_ids_by_item_id
  logging.info('Loaded item refs from %d streams in %g seconds',
      len(stream_items_by_stream_id), time.time() - start_time)

def _data_json(file_name):
  file_path = os.path.join(
      web.config.reader_archive_directory, 'data', file_name)
  with open(file_path) as data_file:
    return json.load(data_file)

def _load_user_info():
  try:
      web.config.reader_user_info = \
          base.api.UserInfo.from_json(_data_json('user-info.json'))
      return
  except:
    pass

  # Synthesize a UserInfo object for the archives created before
  # b7993c5f91c1856d98d4dd702d09424e099b47a7.
  user_id = None
  email = None
  profile_id = None
  user_name = None
  public_user_name = None
  is_blogger_user = False
  signup_time_sec = 0
  is_multi_login_enabled = False

  tags = [base.api.Tag.from_json(t) for t in _data_json('tags.json')]
  for tag in tags:
    stream_id = tag.stream_id
    stream_id_pieces = tag.stream_id.split('/', 2)
    if len(stream_id_pieces) == 3 and \
        stream_id_pieces[0] == 'user' and \
        stream_id_pieces[2] == 'state/com.google/reading-list':
      user_id = stream_id_pieces[1]

  friends = [base.api.Friend.from_json(t) for t in _data_json('friends.json')]
  for friend in friends:
    if friend.is_current_user:
      if friend.email_addresses:
        email = friend.email_addresses[0]
      for i, friend_user_id in enumerate(friend.user_ids):
        if friend_user_id == user_id:
          profile_id = friend.profile_ids[i]
          break
      user_name = friend.given_name
      break

  web.config.reader_user_info = base.api.UserInfo(
      user_id=user_id, email=email, profile_id=profile_id, user_name=user_name,
      public_user_name=public_user_name, is_blogger_user=is_blogger_user,
      signup_time_sec=signup_time_sec,
      is_multi_login_enabled=is_multi_login_enabled)


def _run_app(app, port):
    func = app.wsgifunc()
    func = base.middleware.StaticMiddleware(
        func,
        url_path_prefix=_READER_STATIC_PATH_PREFIX,
        static_directory=_STATIC_DIRECTORY)
    func = base.middleware.LogMiddleware(func)

    web.httpserver.server = web.httpserver.WSGIServer(('0.0.0.0', port), func)

    try:
        web.httpserver.server.start()
    except (KeyboardInterrupt, SystemExit):
        logging.info('Shutting down the server')
        web.httpserver.server.stop()
        web.httpserver.server = None

if __name__ == '__main__':
  main()

########NEW FILE########
