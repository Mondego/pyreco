__FILENAME__ = get_access_token
from instagram.client import InstagramAPI
import sys

if len(sys.argv) > 1 and sys.argv[1] == 'local':
    try:
        from test_settings import *

        InstagramAPI.host = test_host
        InstagramAPI.base_path = test_base_path
        InstagramAPI.access_token_field = "access_token"
        InstagramAPI.authorize_url = test_authorize_url
        InstagramAPI.access_token_url = test_access_token_url
        InstagramAPI.protocol = test_protocol
    except Exception:
        pass

client_id = raw_input("Client ID: ").strip()
client_secret = raw_input("Client Secret: ").strip()
redirect_uri = raw_input("Redirect URI: ").strip()
raw_scope = raw_input("Requested scope (separated by spaces, blank for just basic read): ").strip()
scope = raw_scope.split(' ')
# For basic, API seems to need to be set explicitly
if not scope or scope == [""]:
    scope = ["basic"]

api = InstagramAPI(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)
redirect_uri = api.get_authorize_login_url(scope = scope)

print "Visit this page and authorize access in your browser:\n", redirect_uri

code = raw_input("Paste in code in query string after redirect: ").strip()

access_token = api.exchange_code_for_access_token(code)
print "access token:\n", access_token


########NEW FILE########
__FILENAME__ = bind
import urllib
from oauth2 import OAuth2Request
import re
from json_import import simplejson

re_path_template = re.compile('{\w+}')


def encode_string(value):
    return value.encode('utf-8') \
                        if isinstance(value, unicode) else str(value)


class InstagramClientError(Exception):
    def __init__(self, error_message, status_code=None):
        self.status_code = status_code
        self.error_message = error_message

    def __str__(self):
        if self.status_code:
            return "(%s) %s" % (self.status_code, self.error_message)
        else:
            return self.error_message


class InstagramAPIError(Exception):

    def __init__(self, status_code, error_type, error_message, *args, **kwargs):
        self.status_code = status_code
        self.error_type = error_type
        self.error_message = error_message

    def __str__(self):
        return "(%s) %s-%s" % (self.status_code, self.error_type, self.error_message)


def bind_method(**config):

    class InstagramAPIMethod(object):

        path = config['path']
        method = config.get('method', 'GET')
        accepts_parameters = config.get("accepts_parameters", [])
        requires_target_user = config.get('requires_target_user', False)
        paginates = config.get('paginates', False)
        root_class = config.get('root_class', None)
        response_type = config.get("response_type", "list")
        include_secret = config.get("include_secret", False)
        objectify_response = config.get("objectify_response", True)

        def __init__(self, api, *args, **kwargs):
            self.api = api
            self.as_generator = kwargs.pop("as_generator", False)
            if self.as_generator:
                self.pagination_format = 'next_url'
            else:
                self.pagination_format = kwargs.pop('pagination_format', 'next_url')
            self.return_json = kwargs.pop("return_json", False)
            self.max_pages = kwargs.pop("max_pages", 3)
            self.with_next_url = kwargs.pop("with_next_url", None)
            self.parameters = {}
            self._build_parameters(args, kwargs)
            self._build_path()

        def _build_parameters(self, args, kwargs):
            # via tweepy https://github.com/joshthecoder/tweepy/
            for index, value in enumerate(args):
                if value is None:
                    continue

                try:
                    self.parameters[self.accepts_parameters[index]] = encode_string(value)
                except IndexError:
                    raise InstagramClientError("Too many arguments supplied")

            for key, value in kwargs.iteritems():
                if value is None:
                    continue
                if key in self.parameters:
                    raise InstagramClientError("Parameter %s already supplied" % key)
                self.parameters[key] = encode_string(value)
            if 'user_id' in self.accepts_parameters and not 'user_id' in self.parameters \
               and not self.requires_target_user:
                self.parameters['user_id'] = 'self'

        def _build_path(self):
            for variable in re_path_template.findall(self.path):
                name = variable.strip('{}')

                try:
                    value = urllib.quote(self.parameters[name])
                except KeyError:
                    raise Exception('No parameter value found for path variable: %s' % name)
                del self.parameters[name]

                self.path = self.path.replace(variable, value)
            self.path = self.path + '.%s' % self.api.format

        def _build_pagination_info(self, content_obj):
            """Extract pagination information in the desired format."""
            pagination = content_obj.get('pagination', {})
            if self.pagination_format == 'next_url':
                return pagination.get('next_url')
            if self.pagination_format == 'dict':
                return pagination
            raise Exception('Invalid value for pagination_format: %s' % self.pagination_format)

        def _do_api_request(self, url, method="GET", body=None, headers=None):
            headers = headers or {}
            response, content = OAuth2Request(self.api).make_request(url, method=method, body=body, headers=headers)
            if response['status'] == '503':
                raise InstagramAPIError(response['status'], "Rate limited", "Your client is making too many request per second")

            try:
                content_obj = simplejson.loads(content)
            except ValueError:
                raise InstagramClientError('Unable to parse response, not valid JSON.', status_code=response['status'])

            # Handle OAuthRateLimitExceeded from Instagram's Nginx which uses different format to documented api responses
            if not content_obj.has_key('meta'):
                if content_obj.get('code') == 420:
                    error_message = content_obj.get('error_message') or "Your client is making too many request per second"
                    raise InstagramAPIError(420, "Rate limited", error_message)
                raise InstagramAPIError(content_obj.has_key('code'), content_obj.has_key('error_type'), content_obj.has_key('error_message'))

            api_responses = []
            status_code = content_obj['meta']['code']
            self.api.x_ratelimit_remaining = response.get("x-ratelimit-remaining",None)
            self.api.x_ratelimit = response.get("x-ratelimit-limit",None)
            if status_code == 200:
                if not self.objectify_response:
                    return content_obj, None

                if self.response_type == 'list':
                    for entry in content_obj['data']:
                        if self.return_json:
                            api_responses.append(entry)
                        else:
                            obj = self.root_class.object_from_dictionary(entry)
                            api_responses.append(obj)
                elif self.response_type == 'entry':
                    data = content_obj['data']
                    if self.return_json:
                        api_responses = data
                    else:
                        api_responses = self.root_class.object_from_dictionary(data)
                elif self.response_type == 'empty':
                    pass
                return api_responses, self._build_pagination_info(content_obj)
            else:
                raise InstagramAPIError(status_code, content_obj['meta']['error_type'], content_obj['meta']['error_message'])

        def _paginator_with_url(self, url, method="GET", body=None, headers=None):
            headers = headers or {}
            pages_read = 0
            while url and pages_read < self.max_pages:
                api_responses, url = self._do_api_request(url, method, body, headers)
                pages_read += 1
                yield api_responses, url
            return

        def _get_with_next_url(self, url, method="GET", body=None, headers=None):
            headers = headers or {}
            content, next = self._do_api_request(url, method, body, headers)
            return content, next

        def execute(self):
            url, method, body, headers = OAuth2Request(self.api).prepare_request(self.method,
                                                                                 self.path,
                                                                                 self.parameters,
                                                                                 include_secret=self.include_secret)
            if self.with_next_url:
                return self._get_with_next_url(self.with_next_url, method, body, headers)
            if self.as_generator:
                return self._paginator_with_url(url, method, body, headers)
            else:
                content, next = self._do_api_request(url, method, body, headers)
            if self.paginates:
                return content, next
            else:
                return content

    def _call(api, *args, **kwargs):
        method = InstagramAPIMethod(api, *args, **kwargs)
        return method.execute()

    return _call

########NEW FILE########
__FILENAME__ = client
import oauth2
from bind import bind_method
from models import Media, User, Location, Tag, Comment, Relationship

MEDIA_ACCEPT_PARAMETERS = ["count", "max_id"]
SEARCH_ACCEPT_PARAMETERS = ["q", "count"]

SUPPORTED_FORMATS = ['json']


class InstagramAPI(oauth2.OAuth2API):

    host = "api.instagram.com"
    base_path = "/v1"
    access_token_field = "access_token"
    authorize_url = "https://api.instagram.com/oauth/authorize"
    access_token_url = "https://api.instagram.com/oauth/access_token"
    protocol = "https"
    api_name = "Instagram"
    x_ratelimit_remaining  = None
    x_ratelimit = None

    def __init__(self, *args, **kwargs):
        format = kwargs.get('format', 'json')
        if format in SUPPORTED_FORMATS:
            self.format = format
        else:
            raise Exception("Unsupported format")
        super(InstagramAPI, self).__init__(*args, **kwargs)

    media_popular = bind_method(
                path="/media/popular",
                accepts_parameters=MEDIA_ACCEPT_PARAMETERS,
                root_class=Media)

    media_search = bind_method(
                path="/media/search",
                accepts_parameters=SEARCH_ACCEPT_PARAMETERS + ['lat', 'lng', 'min_timestamp', 'max_timestamp', 'distance'],
                root_class=Media)

    media_likes = bind_method(
                path="/media/{media_id}/likes",
                accepts_parameters=['media_id'],
                root_class=User)

    like_media = bind_method(
                path="/media/{media_id}/likes",
                method="POST",
                accepts_parameters=['media_id'],
                response_type="empty")

    unlike_media = bind_method(
                path="/media/{media_id}/likes",
                method="DELETE",
                accepts_parameters=['media_id'],
                response_type="empty")

    create_media_comment = bind_method(
                path="/media/{media_id}/comments",
                method="POST",
                accepts_parameters=['media_id', 'text'],
                response_type="empty",
                root_class=Comment)

    delete_comment = bind_method(
                path="/media/{media_id}/comments/{comment_id}",
                method="DELETE",
                accepts_parameters=['media_id', 'comment_id'],
                response_type="empty")

    media_comments = bind_method(
                path="/media/{media_id}/comments",
                method="GET",
                accepts_parameters=['media_id'],
                response_type="list",
                root_class=Comment)

    media = bind_method(
                path="/media/{media_id}",
                accepts_parameters=['media_id'],
                response_type="entry",
                root_class=Media)

    user_media_feed = bind_method(
                path="/users/self/feed",
                accepts_parameters=MEDIA_ACCEPT_PARAMETERS,
                root_class=Media,
                paginates=True)

    user_liked_media = bind_method(
                path="/users/self/media/liked",
                accepts_parameters=MEDIA_ACCEPT_PARAMETERS,
                root_class=Media,
                paginates=True)

    user_recent_media = bind_method(
                path="/users/{user_id}/media/recent",
                accepts_parameters=MEDIA_ACCEPT_PARAMETERS + ['user_id'],
                root_class=Media,
                paginates=True)

    user_search = bind_method(
                path="/users/search",
                accepts_parameters=SEARCH_ACCEPT_PARAMETERS,
                root_class=User)

    user_follows = bind_method(
                path="/users/{user_id}/follows",
                accepts_parameters=["user_id"],
                paginates=True,
                root_class=User)

    user_followed_by = bind_method(
                path="/users/{user_id}/followed-by",
                accepts_parameters=["user_id"],
                paginates=True,
                root_class=User)

    user = bind_method(
                path="/users/{user_id}",
                accepts_parameters=["user_id"],
                root_class=User,
                response_type="entry")

    location_recent_media = bind_method(
                path="/locations/{location_id}/media/recent",
                accepts_parameters=MEDIA_ACCEPT_PARAMETERS + ['location_id'],
                root_class=Media,
                paginates=True)

    location_search = bind_method(
                path="/locations/search",
                accepts_parameters=SEARCH_ACCEPT_PARAMETERS + ['lat', 'lng', 'foursquare_id', 'foursquare_v2_id'],
                root_class=Location)

    location = bind_method(
                path="/locations/{location_id}",
                accepts_parameters=["location_id"],
                root_class=Location,
                response_type="entry")

    geography_recent_media = bind_method(
                path="/geographies/{geography_id}/media/recent",
                accepts_parameters=MEDIA_ACCEPT_PARAMETERS + ["geography_id"],
                root_class=Media,
                paginates=True)

    tag_recent_media = bind_method(
                path="/tags/{tag_name}/media/recent",
                accepts_parameters=MEDIA_ACCEPT_PARAMETERS + ['tag_name'],
                root_class=Media,
                paginates=True)

    tag_search = bind_method(
                path="/tags/search",
                accepts_parameters=SEARCH_ACCEPT_PARAMETERS,
                root_class=Tag,
                paginates=True)

    tag = bind_method(
                path="/tags/{tag_name}",
                accepts_parameters=["tag_name"],
                root_class=Tag,
                response_type="entry")

    user_incoming_requests = bind_method(
                path="/users/self/requested-by",
                root_class=User)

    change_user_relationship = bind_method(
                method="POST",
                path="/users/{user_id}/relationship",
                root_class=Relationship,
                accepts_parameters=["user_id", "action"],
                paginates=True,
                requires_target_user=True,
                response_type="entry")

    user_relationship = bind_method(
                method="GET",
                path="/users/{user_id}/relationship",
                root_class=Relationship,
                accepts_parameters=["user_id"],
                paginates=False,
                requires_target_user=True,
                response_type="entry")

    def _make_relationship_shortcut(action):
        def _inner(self, *args, **kwargs):
            return self.change_user_relationship(user_id=kwargs.get("user_id"),
                                                 action=action)
        return _inner

    follow_user = _make_relationship_shortcut('follow')
    unfollow_user = _make_relationship_shortcut('unfollow')
    block_user = _make_relationship_shortcut('block')
    unblock_user = _make_relationship_shortcut('unblock')
    approve_user_request = _make_relationship_shortcut('approve')
    ignore_user_request = _make_relationship_shortcut('ignore')

    def _make_subscription_action(method, include=None, exclude=None):
        accepts_parameters = ["object",
                              "aspect",
                              "object_id",  # Optional if subscribing to all users
                              "callback_url",
                              "lat",  # Geography
                              "lng",  # Geography
                              "radius",  # Geography
                              "verify_token"]

        if include:
            accepts_parameters.extend(include)
        if exclude:
            accepts_parameters = [x for x in accepts_parameters if x not in exclude]
        return bind_method(
            path="/subscriptions",
            method=method,
            accepts_parameters=accepts_parameters,
            include_secret=True,
            objectify_response=False
        )

    create_subscription = _make_subscription_action('POST')
    list_subscriptions = _make_subscription_action('GET')
    delete_subscriptions = _make_subscription_action('DELETE', exclude=['object_id'], include=['id'])

########NEW FILE########
__FILENAME__ = helper
import calendar
from datetime import datetime


def timestamp_to_datetime(ts):
    return datetime.utcfromtimestamp(float(ts))


def datetime_to_timestamp(dt):
    return calendar.timegm(dt.timetuple())

########NEW FILE########
__FILENAME__ = json_import
try:
    import simplejson
except ImportError:
    try:
        import json as simplejson
    except ImportError:
        try:
            from django.utils import simplejson
        except ImportError:
            raise ImportError('A json library is required to use this python library')

########NEW FILE########
__FILENAME__ = models
from helper import timestamp_to_datetime


class ApiModel(object):

    @classmethod
    def object_from_dictionary(cls, entry):
        # make dict keys all strings
        if entry is None:
            return ""
        entry_str_dict = dict([(str(key), value) for key, value in entry.items()])
        return cls(**entry_str_dict)

    def __repr__(self):
        return unicode(self).encode('utf8')


class Image(ApiModel):

    def __init__(self, url, width, height):
        self.url = url
        self.height = height
        self.width = width

    def __unicode__(self):
        return "Image: %s" % self.url


class Video(Image):

    def __unicode__(self):
        return "Video: %s" % self.url


class Media(ApiModel):

    def __init__(self, id=None, **kwargs):
        self.id = id
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    def get_standard_resolution_url(self):
        if self.type == 'image':
            return self.images['standard_resolution'].url
        else:
            return self.videos['standard_resolution'].url

    def get_low_resolution_url(self):
        if self.type == 'image':
            return self.images['low_resolution'].url
        else:
            return self.videos['low_resolution'].url


    def get_thumbnail_url(self):
        return self.images['thumbnail'].url


    def __unicode__(self):
        return "Media: %s" % self.id

    @classmethod
    def object_from_dictionary(cls, entry):
        new_media = Media(id=entry['id'])
        new_media.type = entry['type']

        new_media.user = User.object_from_dictionary(entry['user'])

        new_media.images = {}
        for version, version_info in entry['images'].iteritems():
            new_media.images[version] = Image.object_from_dictionary(version_info)

        if new_media.type == 'video':
            new_media.videos = {}
            for version, version_info in entry['videos'].iteritems():
                new_media.videos[version] = Video.object_from_dictionary(version_info)

        if 'user_has_liked' in entry:
            new_media.user_has_liked = entry['user_has_liked']
        new_media.like_count = entry['likes']['count']
        new_media.likes = []
        if 'data' in entry['likes']:
            for like in entry['likes']['data']:
                new_media.likes.append(User.object_from_dictionary(like))

        new_media.comment_count = entry['comments']['count']
        new_media.comments = []
        for comment in entry['comments']['data']:
            new_media.comments.append(Comment.object_from_dictionary(comment))

        new_media.created_time = timestamp_to_datetime(entry['created_time'])

        if entry['location'] and 'id' in entry:
            new_media.location = Location.object_from_dictionary(entry['location'])

        new_media.caption = None
        if entry['caption']:
            new_media.caption = Comment.object_from_dictionary(entry['caption'])

        if entry['tags']:
            new_media.tags = []
            for tag in entry['tags']:
                new_media.tags.append(Tag.object_from_dictionary({'name': tag}))

        new_media.link = entry['link']

        new_media.filter = entry.get('filter')

        return new_media


class Tag(ApiModel):
    def __init__(self, name, **kwargs):
        self.name = name
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    def __unicode__(self):
        return "Tag: %s" % self.name


class Comment(ApiModel):
    def __init__(self, *args, **kwargs):
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    @classmethod
    def object_from_dictionary(cls, entry):
        user = User.object_from_dictionary(entry['from'])
        text = entry['text']
        created_at = timestamp_to_datetime(entry['created_time'])
        id = entry['id']
        return Comment(id=id, user=user, text=text, created_at=created_at)

    def __unicode__(self):
        return "Comment: %s said \"%s\"" % (self.user.username, self.text)


class Point(ApiModel):
    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude

    def __unicode__(self):
        return "Point: (%s, %s)" % (self.latitude, self.longitude)


class Location(ApiModel):
    def __init__(self, id, *args, **kwargs):
        self.id = id
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    @classmethod
    def object_from_dictionary(cls, entry):
        point = None
        if 'latitude' in entry:
            point = Point(entry.get('latitude'),
                          entry.get('longitude'))
        location = Location(entry.get('id', 0),
                       point=point,
                       name=entry.get('name', ''))
        return location

    def __unicode__(self):
        return "Location: %s (%s)" % (self.id, self.point)


class User(ApiModel):

    def __init__(self, id, *args, **kwargs):
        self.id = id
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    def __unicode__(self):
        return "User: %s" % self.username


class Relationship(ApiModel):

    def __init__(self, incoming_status="none", outgoing_status="none", target_user_is_private=False):
        self.incoming_status = incoming_status
        self.outgoing_status = outgoing_status
        self.target_user_is_private = target_user_is_private

    def __unicode__(self):
        follows = False if self.outgoing_status == 'none' else True
        followed = False if self.incoming_status == 'none' else True

        return "Relationship: (Follows: %s, Followed by: %s)" % (follows, followed)

########NEW FILE########
__FILENAME__ = oauth2
from json_import import simplejson
import urllib
from httplib2 import Http
import mimetypes


class OAuth2AuthExchangeError(Exception):
    def __init__(self, description):
        self.description = description

    def __str__(self):
        return self.description


class OAuth2API(object):
    host = None
    base_path = None
    authorize_url = None
    access_token_url = None
    redirect_uri = None
    # some providers use "oauth_token"
    access_token_field = "access_token"
    protocol = "https"
    # override with 'Instagram', etc
    api_name = "Generic API"

    def __init__(self, client_id=None, client_secret=None, access_token=None, redirect_uri=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.redirect_uri = redirect_uri

    def get_authorize_url(self, scope=None):
        req = OAuth2AuthExchangeRequest(self)
        return req.get_authorize_url(scope=scope)

    def get_authorize_login_url(self, scope=None):
        """ scope should be a tuple or list of requested scope access levels """
        req = OAuth2AuthExchangeRequest(self)
        return req.get_authorize_login_url(scope=scope)

    def exchange_code_for_access_token(self, code):
        req = OAuth2AuthExchangeRequest(self)
        return req.exchange_for_access_token(code=code)

    def exchange_user_id_for_access_token(self, user_id):
        req = OAuth2AuthExchangeRequest(self)
        return req.exchange_for_access_token(user_id=user_id)

    def exchange_xauth_login_for_access_token(self, username, password, scope=None):
        """ scope should be a tuple or list of requested scope access levels """
        req = OAuth2AuthExchangeRequest(self)
        return req.exchange_for_access_token(username=username, password=password,
                                             scope=scope)


class OAuth2AuthExchangeRequest(object):
    def __init__(self, api):
        self.api = api

    def _url_for_authorize(self, scope=None):
        client_params = {
            "client_id": self.api.client_id,
            "response_type": "code",
            "redirect_uri": self.api.redirect_uri
        }
        if scope:
            client_params.update(scope=' '.join(scope))
        url_params = urllib.urlencode(client_params)
        return "%s?%s" % (self.api.authorize_url, url_params)

    def _data_for_exchange(self, code=None, username=None, password=None, scope=None, user_id=None):
        client_params = {
            "client_id": self.api.client_id,
            "client_secret": self.api.client_secret,
            "redirect_uri": self.api.redirect_uri,
            "grant_type": "authorization_code"
        }
        if code:
            client_params.update(code=code)
        elif username and password:
            client_params.update(username=username,
                                 password=password,
                                 grant_type="password")
            if scope:
                client_params.update(scope=' '.join(scope))
        elif user_id:
            client_params.update(user_id=user_id)
        return urllib.urlencode(client_params)

    def get_authorize_url(self, scope=None):
        return self._url_for_authorize(scope=scope)

    def get_authorize_login_url(self, scope=None):
        http_object = Http(disable_ssl_certificate_validation=True)

        url = self._url_for_authorize(scope=scope)
        response, content = http_object.request(url)
        if response['status'] != '200':
            raise OAuth2AuthExchangeError("The server returned a non-200 response for URL %s" % url)
        redirected_to = response['content-location']
        return redirected_to

    def exchange_for_access_token(self, code=None, username=None, password=None, scope=None, user_id=None):
        data = self._data_for_exchange(code, username, password, scope=scope, user_id=user_id)
        http_object = Http(disable_ssl_certificate_validation=True)
        url = self.api.access_token_url
        response, content = http_object.request(url, method="POST", body=data)
        parsed_content = simplejson.loads(content)
        if int(response['status']) != 200:
            raise OAuth2AuthExchangeError(parsed_content.get("error_message", ""))
        return parsed_content['access_token'], parsed_content['user']


class OAuth2Request(object):
    def __init__(self, api):
        self.api = api

    def url_for_get(self, path, parameters):
        return self._full_url_with_params(path, parameters)

    def get_request(self, path, **kwargs):
        return self.make_request(self.prepare_request("GET", path, kwargs))

    def post_request(self, path, **kwargs):
        return self.make_request(self.prepare_request("POST", path, kwargs))

    def _full_url(self, path, include_secret=False):
        return "%s://%s%s%s%s" % (self.api.protocol,
                                  self.api.host,
                                  self.api.base_path,
                                  path,
                                  self._auth_query(include_secret))

    def _full_url_with_params(self, path, params, include_secret=False):
        return (self._full_url(path, include_secret) + self._full_query_with_params(params))

    def _full_query_with_params(self, params):
        params = ("&" + urllib.urlencode(params)) if params else ""
        return params

    def _auth_query(self, include_secret=False):
        if self.api.access_token:
            return ("?%s=%s" % (self.api.access_token_field, self.api.access_token))
        elif self.api.client_id:
            base = ("?client_id=%s" % (self.api.client_id))
            if include_secret:
                base += "&client_secret=%s" % (self.api.client_secret)
            return base

    def _post_body(self, params):
        return urllib.urlencode(params)

    def _encode_multipart(params, files):
        boundary = "MuL7Ip4rt80uND4rYF0o"

        def get_content_type(file_name):
            return mimetypes.guess_type(file_name)[0] or "application/octet-stream"

        def encode_field(field_name):
            return ("--" + boundary,
                    'Content-Disposition: form-data; name="%s"' % (field_name),
                    "", str(params[field_name]))

        def encode_file(field_name):
            file_name, file_handle = files[field_name]
            return ("--" + boundary,
                    'Content-Disposition: form-data; name="%s"; filename="%s"' % (field_name, file_name),
                    "Content-Type: " + get_content_type(file_name),
                    "", file_handle.read())

        lines = []
        for field in params:
            lines.extend(encode_field(field))
        for field in files:
            lines.extend(encode_file(field))
        lines.extend(("--%s--" % (boundary), ""))
        body = "\r\n".join(lines)

        headers = {"Content-Type": "multipart/form-data; boundary=" + boundary,
                   "Content-Length": str(len(body))}

        return body, headers

    def prepare_and_make_request(self, method, path, params, include_secret=False):
        url, method, body, headers = self.prepare_request(method, path, params, include_secret)
        return self.make_request(url, method, body, headers)

    def prepare_request(self, method, path, params, include_secret=False):
        url = body = None
        headers = {}

        if not params.get('files'):
            if method == "POST":
                body = self._post_body(params)
                headers = {'Content-type': 'application/x-www-form-urlencoded'}
                url = self._full_url(path, include_secret)
            else:
                url = self._full_url_with_params(path, params, include_secret)
        else:
            body, headers = self._encode_multipart(params, params['files'])
            url = self._full_url(path)

        return url, method, body, headers

    def make_request(self, url, method="GET", body=None, headers=None):
        headers = headers or {}
        if not 'User-Agent' in headers:
            headers.update({"User-Agent": "%s Python Client" % self.api.api_name})
        http_obj = Http(disable_ssl_certificate_validation=True)
        return http_obj.request(url, method, body=body, headers=headers)

########NEW FILE########
__FILENAME__ = subscriptions
import hmac
import hashlib
from json_import import simplejson

class SubscriptionType:
    TAG = 'tag'
    USER = 'user'
    GEOGRAPHY = 'geography'
    LOCATION = 'location'


class SubscriptionError(Exception):
    pass


class SubscriptionVerifyError(SubscriptionError):
    pass


class SubscriptionsReactor(object):

    callbacks = {}

    def _process_update(self, update):
        object_callbacks = self.callbacks.get(update['object'], [])

        for callback in object_callbacks:
            callback(update)

    def process(self, client_secret, raw_response, x_hub_signature):
        if not self._verify_signature(client_secret, raw_response, x_hub_signature):
            raise SubscriptionVerifyError("X-Hub-Signature and hmac digest did not match")

        try:
            response = simplejson.loads(raw_response)
        except ValueError:
            raise SubscriptionError('Unable to parse response, not valid JSON.')

        for update in response:
            self._process_update(update)

    def register_callback(self, object_type, callback):
        cb_list = self.callbacks.get(object_type, [])

        if callback not in cb_list:
            cb_list.append(callback)
            self.callbacks[object_type] = cb_list

    def deregister_callback(self, object_type, callback):
        callbacks = self.callbacks.get(object_type, [])
        callbacks.remove(callback)

    def _verify_signature(self, client_secret, raw_response, x_hub_signature):
        digest = hmac.new(client_secret.encode('utf-8'),
                          msg=raw_response.encode('utf-8'),
                          digestmod=hashlib.sha1
                          ).hexdigest()
        return digest == x_hub_signature

########NEW FILE########
__FILENAME__ = sample_app
import bottle_session
import bottle
from bottle import route, redirect, post, run, request
from instagram import client, subscriptions

bottle.debug(True)

app = bottle.app()
plugin = bottle_session.SessionPlugin(cookie_lifetime=600)
app.install(plugin)

CONFIG = {
    'client_id': '<client_id>',
    'client_secret': '<client_secret>',
    'redirect_uri': 'http://localhost:8515/oauth_callback'
}

unauthenticated_api = client.InstagramAPI(**CONFIG)

def process_tag_update(update):
    print update

reactor = subscriptions.SubscriptionsReactor()
reactor.register_callback(subscriptions.SubscriptionType.TAG, process_tag_update)

@route('/')
def home():
    try:
        url = unauthenticated_api.get_authorize_url(scope=["likes","comments"])
        return '<a href="%s">Connect with Instagram</a>' % url
    except Exception, e:
        print e

def get_nav(): 
    nav_menu = ("<h1>Python Instagram</h1>"
                "<ul>"
                    "<li><a href='/recent'>User Recent Media</a> Calls user_recent_media - Get a list of a user's most recent media</li>"
                    "<li><a href='/user_media_feed'>User Media Feed</a> Calls user_media_feed - Get the currently authenticated user's media feed uses pagination</li>"              
                    "<li><a href='/location_recent_media'>Location Recent Media</a> Calls location_recent_media - Get a list of recent media at a given location, in this case, the Instagram office</li>"
                    "<li><a href='/media_search'>Media Search</a> Calls media_search - Get a list of media close to a given latitude and longitude</li>"
                    "<li><a href='/media_popular'>Popular Media</a> Calls media_popular - Get a list of the overall most popular media items</li>"
                    "<li><a href='/user_search'>User Search</a> Calls user_search - Search for users on instagram, by name or username</li>"
                    "<li><a href='/location_search'>Location Search</a> Calls location_search - Search for a location by lat/lng</li>"      
                    "<li><a href='/tag_search'>Tags</a> Search for tags, view tag info and get media by tag</li>"
                "</ul>")
            
    return nav_menu

@route('/oauth_callback')
def on_callback(session): 
    code = request.GET.get("code")
    if not code:
        return 'Missing code'
    try:
        access_token, user_info = unauthenticated_api.exchange_code_for_access_token(code)
        print "access token= " + access_token
        if not access_token:
            return 'Could not get access token'
        api = client.InstagramAPI(access_token=access_token)
        session['access_token']=access_token
    except Exception, e:
        print e
    return get_nav()

@route('/recent')
def on_recent(session): 
    access_token = session.get('access_token')
    content = "<h2>User Recent Media</h2>"
    if not access_token:
        return 'Missing Access Token'
    try:
        api = client.InstagramAPI(access_token=access_token)
        recent_media, next = api.user_recent_media()
        photos = []
        for media in recent_media:
            if(media.type == 'video'):
                photos.append('<video controls width height="150"><source type="video/mp4" src="%s"/></video>' % (media.get_standard_resolution_url()))
            else:
                photos.append('<img src="%s"/>' % (media.get_low_resolution_url()))
        content += ''.join(photos)
    except Exception, e:
        print e              
    return "%s %s <br/>Remaining API Calls = %s/%s" % (get_nav(),content,api.x_ratelimit_remaining,api.x_ratelimit)

@route('/user_media_feed')
def on_user_media_feed(session): 
    access_token = session.get('access_token')
    content = "<h2>User Media Feed</h2>"
    if not access_token:
        return 'Missing Access Token'
    try:
        api = client.InstagramAPI(access_token=access_token)
        media_feed, next = api.user_media_feed()
        photos = []
        for media in media_feed:
            photos.append('<img src="%s"/>' % media.get_standard_resolution_url())
        counter = 1
        while next and counter < 3:
            media_feed, next = api.user_media_feed(with_next_url=next)
            for media in media_feed:
                photos.append('<img src="%s"/>' % media.get_standard_resolution_url())
            counter += 1
        content += ''.join(photos)
    except Exception, e:
        print e              
    return "%s %s <br/>Remaining API Calls = %s/%s" % (get_nav(),content,api.x_ratelimit_remaining,api.x_ratelimit)

@route('/location_recent_media')
def location_recent_media(session): 
    access_token = session.get('access_token')
    content = "<h2>Location Recent Media</h2>"
    if not access_token:
        return 'Missing Access Token'
    try:
        api = client.InstagramAPI(access_token=access_token)
        recent_media, next = api.location_recent_media(location_id=514276)
        photos = []
        for media in recent_media:
            photos.append('<img src="%s"/>' % media.get_standard_resolution_url())
        content += ''.join(photos)
    except Exception, e:
        print e              
    return "%s %s <br/>Remaining API Calls = %s/%s" % (get_nav(),content,api.x_ratelimit_remaining,api.x_ratelimit)

@route('/media_search')
def media_search(session): 
    access_token = session.get('access_token')
    content = "<h2>Media Search</h2>"
    if not access_token:
        return 'Missing Access Token'
    try:
        api = client.InstagramAPI(access_token=access_token)
        media_search = api.media_search(lat="37.7808851",lng="-122.3948632",distance=1000)
        photos = []
        for media in media_search:
            photos.append('<img src="%s"/>' % media.get_standard_resolution_url())
        content += ''.join(photos)
    except Exception, e:
        print e              
    return "%s %s <br/>Remaining API Calls = %s/%s" % (get_nav(),content,api.x_ratelimit_remaining,api.x_ratelimit)

@route('/media_popular')
def media_popular(session): 
    access_token = session.get('access_token')
    content = "<h2>Popular Media</h2>"
    if not access_token:
        return 'Missing Access Token'
    try:
        api = client.InstagramAPI(access_token=access_token)
        media_search = api.media_popular()
        photos = []
        for media in media_search:
            photos.append('<img src="%s"/>' % media.get_standard_resolution_url())
        content += ''.join(photos)
    except Exception, e:
        print e              
    return "%s %s <br/>Remaining API Calls = %s/%s" % (get_nav(),content,api.x_ratelimit_remaining,api.x_ratelimit)

@route('/user_search')
def user_search(session): 
    access_token = session.get('access_token')
    content = "<h2>User Search</h2>"
    if not access_token:
        return 'Missing Access Token'
    try:
        api = client.InstagramAPI(access_token=access_token)
        user_search = api.user_search(q="Instagram")
        users = []
        for user in user_search:
            users.append('<li><img src="%s">%s</li>' % (user.profile_picture,user.username))
        content += ''.join(users)
    except Exception, e:
        print e              
    return "%s %s <br/>Remaining API Calls = %s/%s" % (get_nav(),content,api.x_ratelimit_remaining,api.x_ratelimit)

@route('/location_search')
def location_search(session): 
    access_token = session.get('access_token')
    content = "<h2>Location Search</h2>"
    if not access_token:
        return 'Missing Access Token'
    try:
        api = client.InstagramAPI(access_token=access_token)
        location_search = api.location_search(lat="37.7808851",lng="-122.3948632",distance=1000)
        locations = []
        for location in location_search:
            locations.append('<li>%s  <a href="https://www.google.com/maps/preview/@%s,%s,19z">Map</a>  </li>' % (location.name,location.point.latitude,location.point.longitude))
        content += ''.join(locations)
    except Exception, e:
        print e              
    return "%s %s <br/>Remaining API Calls = %s/%s" % (get_nav(),content,api.x_ratelimit_remaining,api.x_ratelimit)

@route('/tag_search')
def tag_search(session): 
    access_token = session.get('access_token')
    content = "<h2>Tag Search</h2>"
    if not access_token:
        return 'Missing Access Token'
    try:
        api = client.InstagramAPI(access_token=access_token)
        tag_search, next_tag = api.tag_search(q="catband")
        tag_recent_media, next = api.tag_recent_media(tag_name=tag_search[0].name)
        photos = []
        for tag_media in tag_recent_media:
            photos.append('<img src="%s"/>' % tag_media.get_standard_resolution_url())
        content += ''.join(photos)
    except Exception, e:
        print e              
    return "%s %s <br/>Remaining API Calls = %s/%s" % (get_nav(),content,api.x_ratelimit_remaining,api.x_ratelimit)

@route('/realtime_callback')
@post('/realtime_callback')
def on_realtime_callback():
    mode = request.GET.get("hub.mode")
    challenge = request.GET.get("hub.challenge")
    verify_token = request.GET.get("hub.verify_token")
    if challenge: 
        return challenge
    else:
        x_hub_signature = request.header.get('X-Hub-Signature')
        raw_response = request.body.read()
        try:
            reactor.process(CONFIG['client_secret'], raw_response, x_hub_signature)
        except subscriptions.SubscriptionVerifyError:
            print "Signature mismatch"

run(host='localhost', port=8515, reloader=True)
########NEW FILE########
__FILENAME__ = tests
#!/usr/bin/env python

import types
try:
    import simplejson as json
except ImportError:
    import json
import getpass
import unittest
import urlparse
from instagram import client, oauth2, InstagramAPIError

TEST_AUTH = False
client_id = "DEBUG"
client_secret = "DEBUG"
access_token = "DEBUG"
redirect_uri = "http://example.com"

class MockHttp(object):

    def __init__(self, *args, **kwargs):
        pass

    def request(self, url, method="GET", body=None, headers={}):
        fail_state = {
            'status':'400'
        }, "{}"

        parsed = urlparse.urlparse(url)
        options = urlparse.parse_qs(parsed.query)

        fn_name = str(active_call)
        if fn_name == 'get_authorize_login_url':
            return {
                'status': '200',
                'content-location':'http://example.com/redirect/login'
            }, None

        if not 'access_token' in options and not 'client_id' in options:
            fn_name += '_unauthorized'
        if 'self' in url and not 'access_token' in options:
            fn_name += '_no_auth_user'

        fl = open('fixtures/%s.json' % fn_name)
        content = fl.read()
        json_content = json.loads(content)
        status = json_content['meta']['code']
        return {
            'status': status
        }, content

oauth2.Http = MockHttp

active_call = None
class TestInstagramAPI(client.InstagramAPI):
    def __getattribute__(self, attr):
        global active_call
        actual_val = super(TestInstagramAPI, self).__getattribute__(attr)
        if isinstance(actual_val, types.MethodType):
            active_call = attr
        return actual_val

class InstagramAuthTests(unittest.TestCase):
    def setUp(self):
        self.unauthenticated_api = TestInstagramAPI(client_id=client_id, redirect_uri=redirect_uri, client_secret=client_secret)

    def test_authorize_login_url(self):
        redirect_uri = self.unauthenticated_api.get_authorize_login_url()
        assert redirect_uri
        print "Please visit and authorize at:\n%s" % redirect_uri
        code = raw_input("Paste received code (blank to skip): ").strip()
        if not code:
            return

        access_token = self.unauthenticated_api.exchange_code_for_access_token(code)
        assert access_token

    def test_xauth_exchange(self):
        """ Your client ID must be authorized for xAuth access; email
            xauth@instagram.com for access"""
        username = raw_input("Enter username for XAuth (blank to skip): ").strip()
        if not username:
            return
        password =  getpass.getpass("Enter password for XAuth (blank to skip): ").strip()
        access_token = self.unauthenticated_api.exchange_xauth_login_for_access_token(username, password)
        assert access_token

class InstagramAPITests(unittest.TestCase):

    def setUp(self):
        super(InstagramAPITests, self).setUp()
        self.client_only_api = TestInstagramAPI(client_id=client_id)
        self.api = TestInstagramAPI(access_token=access_token)

    def test_media_popular(self):
        self.api.media_popular(count=10)

    def test_media_search(self):
        self.client_only_api.media_search(lat=37.7,lng=-122.22)
        self.api.media_search(lat=37.7,lng=-122.22)

    def test_media_likes(self):
        self.client_only_api.media_likes(media_id=4)

    def test_like_media(self):
        self.api.like_media(media_id=4)
        self.api.unlike_media(media_id=4)

    """
    TEMP; disabled this test while we add
    a proper response to create_media_comment
    def test_comment_media(self):
        comment = self.api.create_media_comment(media_id=4, text='test')
        self.api.delete_comment(media_id=4, comment_id=comment.id)
    """

    def test_user_feed(self):
        self.api.user_media_feed(count=50)

    def test_generator_user_feed(self):
        generator = self.api.user_media_feed(as_generator=True, max_pages=3, count=2)
        for page in generator:
            str(generator)

    def test_user_liked_media(self):
        self.api.user_liked_media(count=10)

    def test_user_recent_media(self):
        media, url = self.api.user_recent_media(count=10)

        self.assertTrue( all( [hasattr(obj, 'type') for obj in media] ) )

        image = media[0]
        self.assertEquals(
                image.get_standard_resolution_url(),
                "http://distillery-dev.s3.amazonaws.com/media/2011/02/02/1ce5f3f490a640ca9068e6000c91adc5_7.jpg")

        self.assertEquals(
                image.get_low_resolution_url(),
                "http://distillery-dev.s3.amazonaws.com/media/2011/02/02/1ce5f3f490a640ca9068e6000c91adc5_6.jpg")

        self.assertEquals(
                image.get_thumbnail_url(),
                "http://distillery-dev.s3.amazonaws.com/media/2011/02/02/1ce5f3f490a640ca9068e6000c91adc5_5.jpg")

        self.assertEquals( False, hasattr(image, 'videos') )

        video = media[1]
        self.assertEquals(
                video.get_standard_resolution_url(),
                video.videos['standard_resolution'].url)

        self.assertEquals(
                video.get_standard_resolution_url(),
                "http://distilleryvesper9-13.ak.instagram.com/090d06dad9cd11e2aa0912313817975d_101.mp4")

        self.assertEquals(
                video.get_low_resolution_url(),
                "http://distilleryvesper9-13.ak.instagram.com/090d06dad9cd11e2aa0912313817975d_102.mp4")

        self.assertEquals(
                video.get_thumbnail_url(),
                "http://distilleryimage2.ak.instagram.com/11f75f1cd9cc11e2a0fd22000aa8039a_5.jpg")





    def test_user_search(self):
        self.api.user_search('mikeyk', 10)

    def test_user_follows(self):
        for page in self.api.user_followed_by(as_generator=True):
            str(page)

    def test_user_followed_by(self):
        for page in self.api.user_followed_by(as_generator=True):
            str(page)

    def test_other_user_followed_by(self):
        self.api.user_followed_by(user_id=3)

    def test_self_info(self):
        self.api.user()
        self.assertRaises(InstagramAPIError, self.client_only_api.user)

    def test_location_recent_media(self):
        self.api.location_recent_media(location_id=1)

    def test_location_search(self):
        self.api.location_search(lat=37.7,lng=-122.22, distance=2500)

    def test_location(self):
        self.api.location(1)

    def test_tag_recent_media(self):
        self.api.tag_recent_media(tag_name='1', count=5)

    def test_tag_recent_media_paginated(self):
        for page in self.api.tag_recent_media(tag_name='1', count=5, as_generator=True, max_pages=2):
            str(page)

    def test_tag_search(self):
        self.api.tag_search("coff")

    def test_tag(self):
        self.api.tag("coffee")

    def test_user_follows(self):
        self.api.user_follows()

    def test_user_followed_by(self):
        self.api.user_followed_by()

    def test_user_followed_by(self):
        self.api.user_followed_by()

    def test_user_requested_by(self):
        self.api.user_followed_by()

    def test_user_incoming_requests(self):
        self.api.user_incoming_requests()

    def test_change_relationship(self):
        self.api.change_user_relationship(user_id=10, action="follow")
        # test shortcuts as well
        self.api.follow_user(user_id='10')
        self.api.unfollow_user(user_id='10')

    def test_geography_recent_media(self):
        self.api.geography_recent_media(geography_id=1)

if __name__ == '__main__':
    if not TEST_AUTH:
        del InstagramAuthTests

    unittest.main()

########NEW FILE########
