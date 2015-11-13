__FILENAME__ = authentication
from linkedin.linkedin import (LinkedInAuthentication, LinkedInApplication,
                               PERMISSIONS)


if __name__ == '__main__':
    API_KEY = 'wFNJekVpDCJtRPFX812pQsJee-gt0zO4X5XmG6wcfSOSlLocxodAXNMbl0_hw3Vl'
    API_SECRET = 'daJDa6_8UcnGMw1yuq9TjoO_PMKukXMo8vEMo7Qv5J-G3SPgrAV0FqFCd0TNjQyG'
    RETURN_URL = 'http://localhost:8000'
    authentication = LinkedInAuthentication(API_KEY, API_SECRET, RETURN_URL,
                                            PERMISSIONS.enums.values())
    print authentication.authorization_url
    application = LinkedInApplication(authentication)

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-
class LinkedInError(Exception):
    pass

########NEW FILE########
__FILENAME__ = linkedin
# -*- coding: utf-8 -*-
import requests
import urllib
import random
import hashlib
import contextlib
from requests_oauthlib import OAuth1

from .models import AccessToken, LinkedInInvitation
from .utils import enum, to_utf8, raise_for_error, json, StringIO
from .exceptions import LinkedInError


__all__ = ['LinkedInAuthentication', 'LinkedInApplication', 'PERMISSIONS']

PERMISSIONS = enum('Permission',
                        BASIC_PROFILE='r_basicprofile',
                        FULL_PROFILE='r_fullprofile',
                        EMAIL_ADDRESS='r_emailaddress',
                        NETWORK='r_network',
                        CONTACT_INFO='r_contactinfo',
                        NETWORK_UPDATES='rw_nus',
                        GROUPS='rw_groups',
                        MESSAGES='w_messages')


ENDPOINTS = enum('LinkedInURL',
                      PEOPLE='https://api.linkedin.com/v1/people',
                      PEOPLE_SEARCH='https://api.linkedin.com/v1/people-search',
                      GROUPS='https://api.linkedin.com/v1/groups',
                      POSTS='https://api.linkedin.com/v1/posts',
                      COMPANIES='https://api.linkedin.com/v1/companies',
                      COMPANY_SEARCH='https://api.linkedin.com/v1/company-search',
                      JOBS='https://api.linkedin.com/v1/jobs',
                      JOB_SEARCH='https://api.linkedin.com/v1/job-search')


NETWORK_UPDATES = enum('NetworkUpdate',
                            APPLICATION='APPS',
                            COMPANY='CMPY',
                            CONNECTION='CONN',
                            JOB='JOBS',
                            GROUP='JGRP',
                            PICTURE='PICT',
                            EXTENDED_PROFILE='PRFX',
                            CHANGED_PROFILE='PRFU',
                            SHARED='SHAR',
                            VIRAL='VIRL')


class LinkedInDeveloperAuthentication(object):
    """
    Uses all four credentials provided by LinkedIn as part of an OAuth 1.0a
    flow that provides instant API access with no redirects/approvals required.
    Useful for situations in which users would like to access their own data or
    during the development process.
    """
    def __init__(self, consumer_key, consumer_secret, user_token, user_secret,
                 redirect_uri, permissions=[]):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.user_token = user_token
        self.user_secret = user_secret
        self.redirect_uri = redirect_uri
        self.permissions = permissions


class LinkedInAuthentication(object):
    """
    Implements a standard OAuth 2.0 flow that involves redirection for users to
    authorize the application to access account data.
    """
    AUTHORIZATION_URL = 'https://www.linkedin.com/uas/oauth2/authorization'
    ACCESS_TOKEN_URL = 'https://www.linkedin.com/uas/oauth2/accessToken'

    def __init__(self, key, secret, redirect_uri, permissions=None):
        self.key = key
        self.secret = secret
        self.redirect_uri = redirect_uri
        self.permissions = permissions or []
        self.state = None
        self.authorization_code = None
        self.token = None
        self._error = None

    @property
    def authorization_url(self):
        self.state = self._make_new_state()
        qd = {'response_type': 'code',
              'client_id': self.key,
              'scope': (' '.join(self.permissions)).strip(),
              'state': self.state,
              'redirect_uri': self.redirect_uri}
        # urlencode uses quote_plus when encoding the query string so,
        # we ought to be encoding the qs by on our own.
        qsl = ['%s=%s' % (urllib.quote(k), urllib.quote(v)) for k, v in qd.items()]
        return '%s?%s' % (self.AUTHORIZATION_URL, '&'.join(qsl))

    @property
    def last_error(self):
        return self._error

    def _make_new_state(self):
        return hashlib.md5(
            '%s%s' % (random.randrange(0, 2**63), self.secret)).hexdigest()

    def get_access_token(self, timeout=60):
        assert self.authorization_code, 'You must first get the authorization code'
        qd = {'grant_type': 'authorization_code',
              'code': self.authorization_code,
              'redirect_uri': self.redirect_uri,
              'client_id': self.key,
              'client_secret': self.secret}
        response = requests.post(self.ACCESS_TOKEN_URL, data=qd, timeout=timeout)
        raise_for_error(response)
        response = response.json()
        self.token = AccessToken(response['access_token'], response['expires_in'])
        return self.token


class LinkedInSelector(object):
    @classmethod
    def parse(cls, selector):
        with contextlib.closing(StringIO()) as result:
            if type(selector) == dict:
                for k, v in selector.items():
                    result.write('%s:(%s)' % (to_utf8(k), cls.parse(v)))
            elif type(selector) in (list, tuple):
                result.write(','.join(map(cls.parse, selector)))
            else:
                result.write(to_utf8(selector))
            return result.getvalue()


class LinkedInApplication(object):
    BASE_URL = 'https://api.linkedin.com'

    def __init__(self, authentication=None, token=None):
        assert authentication or token, 'Either authentication instance or access token is required'
        self.authentication = authentication
        if not self.authentication:
            self.authentication = LinkedInAuthentication('', '', '')
            self.authentication.token = AccessToken(token, None)

    def make_request(self, method, url, data=None, params=None, headers=None,
                     timeout=60):
        if headers is None:
            headers = {'x-li-format': 'json', 'Content-Type': 'application/json'}
        else:
            headers.update({'x-li-format': 'json', 'Content-Type': 'application/json'})

        if params is None:
            params = {}
        kw = dict(data=data, params=params,
                  headers=headers, timeout=timeout)

        if isinstance(self.authentication, LinkedInDeveloperAuthentication):
            # Let requests_oauthlib.OAuth1 do *all* of the work here
            auth = OAuth1(self.authentication.consumer_key, self.authentication.consumer_secret,
                          self.authentication.user_token, self.authentication.user_secret)
            kw.update({'auth': auth})
        else:
            params.update({'oauth2_access_token': self.authentication.token.access_token})

        return requests.request(method.upper(), url, **kw)

    def get_profile(self, member_id=None, member_url=None, selectors=None,
                    params=None, headers=None):
        if member_id:
            url = '%s/id=%s' % (ENDPOINTS.PEOPLE, str(member_id))
        elif member_url:
            url = '%s/url=%s' % (ENDPOINTS.PEOPLE, urllib.quote_plus(member_url))
        else:
            url = '%s/~' % ENDPOINTS.PEOPLE
        if selectors:
            url = '%s:(%s)' % (url, LinkedInSelector.parse(selectors))

        response = self.make_request('GET', url, params=params, headers=headers)
        raise_for_error(response)
        return response.json()

    def search_profile(self, selectors=None, params=None, headers=None):
        if selectors:
            url = '%s:(%s)' % (ENDPOINTS.PEOPLE_SEARCH,
                               LinkedInSelector.parse(selectors))
        else:
            url = ENDPOINTS.PEOPLE_SEARCH
        response = self.make_request('GET', url, params=params, headers=headers)
        raise_for_error(response)
        return response.json()

    def get_picture_urls(self, member_id=None, member_url=None,
                    params=None, headers=None):
        if member_id:
                url = '%s/id=%s/picture-urls::(original)' % (ENDPOINTS.PEOPLE, str(member_id))
        elif member_url:
            url = '%s/url=%s/picture-urls::(original)' % (ENDPOINTS.PEOPLE,
                                                          urllib.quote_plus(member_url))
        else:
            url = '%s/~/picture-urls::(original)' % ENDPOINTS.PEOPLE

        response = self.make_request('GET', url, params=params, headers=headers)
        raise_for_error(response)
        return response.json()

    def get_connections(self, member_id=None, member_url=None, selectors=None,
                        params=None, headers=None):
        if member_id:
            url = '%s/id=%s/connections' % (ENDPOINTS.PEOPLE, str(member_id))
        elif member_url:
            url = '%s/url=%s/connections' % (ENDPOINTS.PEOPLE,
                                             urllib.quote_plus(member_url))
        else:
            url = '%s/~/connections' % ENDPOINTS.PEOPLE
        if selectors:
            url = '%s:(%s)' % (url, LinkedInSelector.parse(selectors))

        response = self.make_request('GET', url, params=params, headers=headers)
        raise_for_error(response)
        return response.json()

    def get_memberships(self, member_id=None, member_url=None, group_id=None,
                        selectors=None, params=None, headers=None):
        if member_id:
            url = '%s/id=%s/group-memberships' % (ENDPOINTS.PEOPLE, str(member_id))
        elif member_url:
            url = '%s/url=%s/group-memberships' % (ENDPOINTS.PEOPLE,
                                                   urllib.quote_plus(member_url))
        else:
            url = '%s/~/group-memberships' % ENDPOINTS.PEOPLE

        if group_id:
            url = '%s/%s' % (url, str(group_id))

        if selectors:
            url = '%s:(%s)' % (url, LinkedInSelector.parse(selectors))

        response = self.make_request('GET', url, params=params, headers=headers)
        raise_for_error(response)
        return response.json()

    def get_group(self, group_id, selectors=None, params=None, headers=None):
        url = '%s/%s' % (ENDPOINTS.GROUPS, str(group_id))

        response = self.make_request('GET', url, params=params, headers=headers)
        raise_for_error(response)
        return response.json()

    def get_posts(self, group_id, post_ids=None, selectors=None, params=None,
                  headers=None):
        url = '%s/%s/posts' % (ENDPOINTS.GROUPS, str(group_id))
        if post_ids:
            url = '%s::(%s)' % (url, ','.join(map(str, post_ids)))
        if selectors:
            url = '%s:(%s)' % (url, LinkedInSelector.parse(selectors))

        response = self.make_request('GET', url, params=params, headers=headers)
        raise_for_error(response)
        return response.json()

    def join_group(self, group_id):
        url = '%s/~/group-memberships/%s' % (ENDPOINTS.PEOPLE, str(group_id))
        response = self.make_request('PUT', url,
                    data=json.dumps({'membershipState': {'code': 'member'}}))
        raise_for_error(response)
        return True

    def leave_group(self, group_id):
        url = '%s/~/group-memberships/%s' % (ENDPOINTS.PEOPLE, str(group_id))
        response = self.make_request('DELETE', url)
        raise_for_error(response)
        return True

    def submit_group_post(self, group_id, title, summary, submitted_url,
                          submitted_image_url, content_title, description):
        post = {
            'title': title, 'summary': summary,
            'content': {
                'submitted-url': submitted_url,
                'submitted-image-url': submitted_image_url,
                'title': content_title,
                'description': description
            }
        }
        url = '%s/%s/posts' % (ENDPOINTS.GROUPS, str(group_id))
        response = self.make_request('POST', url, data=json.dumps(post))
        raise_for_error(response)
        return True

    def like_post(self, post_id, action):
        url = '%s/%s/relation-to-viewer/is-liked' % (ENDPOINTS.POSTS, str(post_id))
        try:
            self.make_request('PUT', url, data=json.dumps(action))
        except (requests.ConnectionError, requests.HTTPError), error:
            raise LinkedInError(error.message)
        else:
            return True

    def comment_post(self, post_id, comment):
        post = {
            'text': comment
        }
        url = '%s/%s/comments' % (ENDPOINTS.POSTS, str(post_id))
        try:
            self.make_request('POST', url, data=json.dumps(post))
        except (requests.ConnectionError, requests.HTTPError), error:
            raise LinkedInError(error.message)
        else:
            return True

    def get_company_by_email_domain(self, email_domain, params=None, headers=None):
        url = '%s?email-domain=%s' % (ENDPOINTS.COMPANIES, email_domain)

        response = self.make_request('GET', url, params=params, headers=headers)
        raise_for_error(response)
        return response.json()

    def get_companies(self, company_ids=None, universal_names=None, selectors=None,
                      params=None, headers=None):
        identifiers = []
        url = ENDPOINTS.COMPANIES
        if company_ids:
            identifiers += map(str, company_ids)

        if universal_names:
            identifiers += ['universal-name=%s' % un for un in universal_names]

        if identifiers:
            url = '%s::(%s)' % (url, ','.join(identifiers))

        if selectors:
            url = '%s:(%s)' % (url, LinkedInSelector.parse(selectors))

        response = self.make_request('GET', url, params=params, headers=headers)
        raise_for_error(response)
        return response.json()

    def get_company_updates(self, company_id, params=None, headers=None):
        url = '%s/%s/updates' % (ENDPOINTS.COMPANIES, str(company_id))
        response = self.make_request('GET', url, params=params, headers=headers)
        raise_for_error(response)
        return response.json()

    def get_company_products(self, company_id, selectors=None, params=None,
                             headers=None):
        url = '%s/%s/products' % (ENDPOINTS.COMPANIES, str(company_id))
        if selectors:
            url = '%s:(%s)' % (url, LinkedInSelector.parse(selectors))
        response = self.make_request('GET', url, params=params, headers=headers)
        raise_for_error(response)
        return response.json()

    def follow_company(self, company_id):
        url = '%s/~/following/companies' % ENDPOINTS.PEOPLE
        post = {'id': company_id}
        response = self.make_request('POST', url, data=json.dumps(post))
        raise_for_error(response)
        return True

    def unfollow_company(self, company_id):
        url = '%s/~/following/companies/id=%s' % (ENDPOINTS.PEOPLE, str(company_id))
        response = self.make_request('DELETE', url)
        raise_for_error(response)
        return True

    def search_company(self, selectors=None, params=None, headers=None):
        url = ENDPOINTS.COMPANY_SEARCH
        if selectors:
            url = '%s:(%s)' % (url, LinkedInSelector.parse(selectors))

        response = self.make_request('GET', url, params=params, headers=headers)
        raise_for_error(response)
        return response.json()

    def get_job(self, job_id, selectors=None, params=None, headers=None):
        url = '%s/%s' % (ENDPOINTS.JOBS, str(job_id))
        url = '%s:(%s)' % (url, LinkedInSelector.parse(selectors))
        response = self.make_request('GET', url, params=params, headers=headers)
        raise_for_error(response)
        return response.json()

    def get_job_bookmarks(self, selectors=None, params=None, headers=None):
        url = '%s/~/job-bookmarks' % ENDPOINTS.PEOPLE
        if selectors:
            url = '%s:(%s)' % (url, LinkedInSelector.parse(selectors))

        response = self.make_request('GET', url, params=params, headers=headers)
        raise_for_error(response)
        return response.json()

    def search_job(self, selectors=None, params=None, headers=None):
        url = ENDPOINTS.JOB_SEARCH
        if selectors:
            url = '%s:(%s)' % (url, LinkedInSelector.parse(selectors))

        response = self.make_request('GET', url, params=params, headers=headers)
        raise_for_error(response)
        return response.json()

    def submit_share(self, comment=None, title=None, description=None,
                     submitted_url=None, submitted_image_url=None,
                     visibility_code='anyone'):
        post = {
            'visibility': {
                'code': visibility_code,
            },
        }
        if comment is not None:
            post['comment'] = comment
        if title is not None and submitted_url is not None:
            post['content'] = {
                'title': title,
                'submitted-url': submitted_url,
                'submitted-image-url': submitted_image_url,
                'description': description,
            }

        url = '%s/~/shares' % ENDPOINTS.PEOPLE
        response = self.make_request('POST', url, data=json.dumps(post))
        raise_for_error(response)
        return response.json()

    def get_network_updates(self, types, member_id=None, 
                            self_scope=True, params=None, headers=None):
        if member_id:
            url = '%s/id=%s/network/updates' % (ENDPOINTS.PEOPLE,
                                             str(member_id))
        else:
            url = '%s/~/network/updates' % ENDPOINTS.PEOPLE

        if not params:
            params = {}

        if types:
            params.update({'type': types})

        if self_scope is True:
            params.update({'scope': 'self'})

        response = self.make_request('GET', url, params=params, headers=headers)
        raise_for_error(response)
        return response.json()

    def get_network_status(self, params=None, headers=None):
        url = '%s/~/network/network-stats' % ENDPOINTS.PEOPLE
        response = self.make_request('GET', url, params=params, headers=headers)
        raise_for_error(response)
        return response.json()

    def send_invitation(self, invitation):
        assert type(invitation) == LinkedInInvitation, 'LinkedInInvitation required'
        url = '%s/~/mailbox' % ENDPOINTS.PEOPLE
        response = self.make_request('POST', url,
                                     data=json.dumps(invitation.json))
        raise_for_error(response)
        return True

    def comment_on_update(self, update_key, comment):
        comment = {'comment': comment}
        url = '%s/~/network/updates/key=%s/update-comments' % (ENDPOINTS.PEOPLE, update_key)
        response = self.make_request('POST', url, data=json.dumps(comment))
        raise_for_error(response)
        return True

    def like_update(self, update_key, is_liked=True):
        url = '%s/~/network/updates/key=%s/is-liked' % (ENDPOINTS.PEOPLE, update_key)
        response = self.make_request('PUT', url, data=json.dumps(is_liked))
        raise_for_error(response)
        return True
########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
import collections

AccessToken = collections.namedtuple('AccessToken', ['access_token', 'expires_in'])


class LinkedInRecipient(object):
    def __init__(self, member_id, email, first_name, last_name):
        assert member_id or email, 'Either member ID or email must be given'
        if member_id:
            self.member_id = str(member_id)
        else:
            self.member_id = None
        self.email = email
        self.first_name = first_name
        self.last_name = last_name

    @property
    def json(self):
        result = {'person': None}
        if self.member_id:
            result['person'] = {'_path': '/people/id=%s' % self.member_id}
        else:
            result['person'] = {'_path': '/people/email=%s' % self.email}

        if self.first_name:
            result['person']['first-name'] = self.first_name

        if self.last_name:
            result['person']['last-name'] = self.last_name

        return result


class LinkedInInvitation(object):
    def __init__(self, subject, body, recipients, connect_type, auth_name=None,
                 auth_value=None):
        self.subject = subject
        self.body = body
        self.recipients = recipients
        self.connect_type = connect_type
        self.auth_name = auth_name
        self.auth_value = auth_value

    @property
    def json(self):
        result = {
            'recipients': {
                'values': []
            },
            'subject': self.subject,
            'body': self.body,
            'item-content': {
                'invitation-request': {
                    'connect-type': self.connect_type
                }
            }
        }
        for recipient in self.recipients:
            result['recipients']['values'].append(recipient.json)

        if self.auth_name and self.auth_value:
            auth = {'name': self.auth_name, 'value': self.auth_value}
            result['item-content']['invitation-request']['authorization'] = auth

        return result

########NEW FILE########
__FILENAME__ = server
# -*- coding: utf-8 -*-
import BaseHTTPServer
import urlparse

from .linkedin import LinkedInApplication, LinkedInAuthentication, PERMISSIONS


def quick_api(api_key, secret_key):
    """
    This method helps you get access to linkedin api quickly when using it
    from the interpreter.
    Notice that this method creates http server and wait for a request, so it
    shouldn't be used in real production code - it's just an helper for debugging

    The usage is basically:
    api = quick_api(KEY, SECRET)
    After you do that, it will print a URL to the screen which you must go in
    and allow the access, after you do that, the method will return with the api
    object.
    """
    auth = LinkedInAuthentication(api_key, secret_key, 'http://localhost:8000/',
                                  PERMISSIONS.enums.values())
    app = LinkedInApplication(authentication=auth)
    print auth.authorization_url
    _wait_for_user_to_enter_browser(app)
    return app


def _wait_for_user_to_enter_browser(app):
    class MyHandler(BaseHTTPServer.BaseHTTPRequestHandler):
        def do_GET(self):
            p = self.path.split('?')
            if len(p) > 1:
                params = urlparse.parse_qs(p[1], True, True)
                app.authentication.authorization_code = params['code'][0]
                app.authentication.get_access_token()

    server_address = ('', 8000)
    httpd = BaseHTTPServer.HTTPServer(server_address, MyHandler)
    httpd.handle_request()

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
import requests
from .exceptions import LinkedInError

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

try:
    import simplejson as json
except ImportError:
    try:
        from django.utils import simplejson as json
    except ImportError:
        import json


def enum(enum_type='enum', base_classes=None, methods=None, **attrs):
    """
    Generates a enumeration with the given attributes.
    """
    # Enumerations can not be initalized as a new instance
    def __init__(instance, *args, **kwargs):
        raise RuntimeError('%s types can not be initialized.' % enum_type)

    if base_classes is None:
        base_classes = ()

    if methods is None:
        methods = {}

    base_classes = base_classes + (object,)
    for k, v in methods.iteritems():
        methods[k] = classmethod(v)

    attrs['enums'] = attrs.copy()
    methods.update(attrs)
    methods['__init__'] = __init__
    return type(enum_type, base_classes, methods)


def to_utf8(st):
    if isinstance(st, unicode):
        return st.encode('utf-8')
    else:
        return bytes(st)


def raise_for_error(response):
    try:
        response.raise_for_status()
    except (requests.HTTPError, requests.ConnectionError), error:
        try:
            if len(response.content) == 0:
                # There is nothing we can do here since LinkedIn has neither sent
                # us a 2xx response nor a response content.
                return
            response = response.json()
            if ('error' in response) or ('errorCode' in response):
                message = '%s: %s' % (response.get('error', error.message),
                                      response.get('error_description', 'Unknown Error'))
                raise LinkedInError(message)
            else:
                raise LinkedInError(error.message)
        except (ValueError, TypeError):
            raise LinkedInError(error.message)

HTTP_METHODS = enum('HTTPMethod', GET='GET', POST='POST',
                    PUT='PUT', DELETE='DELETE', PATCH='PATCH')

########NEW FILE########
