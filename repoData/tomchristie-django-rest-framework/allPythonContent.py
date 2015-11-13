__FILENAME__ = mkdocs
#!/usr/bin/env python

import markdown
import os
import re
import shutil
import sys

root_dir = os.path.abspath(os.path.dirname(__file__))
docs_dir = os.path.join(root_dir, 'docs')
html_dir = os.path.join(root_dir, 'html')

local = not '--deploy' in sys.argv
preview = '-p' in sys.argv

if local:
    base_url = 'file://%s/' % os.path.normpath(os.path.join(os.getcwd(), html_dir))
    suffix = '.html'
    index = 'index.html'
else:
    base_url = 'http://www.django-rest-framework.org'
    suffix = ''
    index = ''


main_header = '<li class="main"><a href="#{{ anchor }}">{{ title }}</a></li>'
sub_header = '<li><a href="#{{ anchor }}">{{ title }}</a></li>'
code_label = r'<a class="github" href="https://github.com/tomchristie/django-rest-framework/tree/master/rest_framework/\1"><span class="label label-info">\1</span></a>'

page = open(os.path.join(docs_dir, 'template.html'), 'r').read()

# Copy static files
# for static in ['css', 'js', 'img']:
#     source = os.path.join(docs_dir, 'static', static)
#     target = os.path.join(html_dir, static)
#     if os.path.exists(target):
#         shutil.rmtree(target)
#     shutil.copytree(source, target)


# Hacky, but what the hell, it'll do the job
path_list = [
    'index.md',
    'tutorial/quickstart.md',
    'tutorial/1-serialization.md',
    'tutorial/2-requests-and-responses.md',
    'tutorial/3-class-based-views.md',
    'tutorial/4-authentication-and-permissions.md',
    'tutorial/5-relationships-and-hyperlinked-apis.md',
    'tutorial/6-viewsets-and-routers.md',
    'api-guide/requests.md',
    'api-guide/responses.md',
    'api-guide/views.md',
    'api-guide/generic-views.md',
    'api-guide/viewsets.md',
    'api-guide/routers.md',
    'api-guide/parsers.md',
    'api-guide/renderers.md',
    'api-guide/serializers.md',
    'api-guide/fields.md',
    'api-guide/relations.md',
    'api-guide/authentication.md',
    'api-guide/permissions.md',
    'api-guide/throttling.md',
    'api-guide/filtering.md',
    'api-guide/pagination.md',
    'api-guide/content-negotiation.md',
    'api-guide/format-suffixes.md',
    'api-guide/reverse.md',
    'api-guide/exceptions.md',
    'api-guide/status-codes.md',
    'api-guide/testing.md',
    'api-guide/settings.md',
    'topics/documenting-your-api.md',
    'topics/ajax-csrf-cors.md',
    'topics/browser-enhancements.md',
    'topics/browsable-api.md',
    'topics/rest-hypermedia-hateoas.md',
    'topics/contributing.md',
    'topics/rest-framework-2-announcement.md',
    'topics/2.2-announcement.md',
    'topics/2.3-announcement.md',
    'topics/release-notes.md',
    'topics/credits.md',
]

prev_url_map = {}
next_url_map = {}
for idx in range(len(path_list)):
    path = path_list[idx]
    rel = '../' * path.count('/')

    if idx == 1 and not local:
        # Link back to '/', not '/index'
        prev_url_map[path] = '/'
    elif idx > 0:
        prev_url_map[path] = rel + path_list[idx - 1][:-3] + suffix

    if idx < len(path_list) - 1:
        next_url_map[path] = rel + path_list[idx + 1][:-3] + suffix


for (dirpath, dirnames, filenames) in os.walk(docs_dir):
    relative_dir = dirpath.replace(docs_dir, '').lstrip(os.path.sep)
    build_dir = os.path.join(html_dir, relative_dir)

    if not os.path.exists(build_dir):
        os.makedirs(build_dir)

    for filename in filenames:
        path = os.path.join(dirpath, filename)
        relative_path = os.path.join(relative_dir, filename)

        if not filename.endswith('.md'):
            if relative_dir:
                output_path = os.path.join(build_dir, filename)
                shutil.copy(path, output_path)
            continue

        output_path = os.path.join(build_dir, filename[:-3] + '.html')

        toc = ''
        text = open(path, 'r').read().decode('utf-8')
        main_title = None
        description = 'Django, API, REST'
        for line in text.splitlines():
            if line.startswith('# '):
                title = line[2:].strip()
                template = main_header
                description = description + ', ' + title
            elif line.startswith('## '):
                title = line[3:].strip()
                template = sub_header
            else:
                continue

            if not main_title:
                main_title = title
            anchor = title.lower().replace(' ', '-').replace(':-', '-').replace("'", '').replace('?', '').replace('.', '')
            template = template.replace('{{ title }}', title)
            template = template.replace('{{ anchor }}', anchor)
            toc += template + '\n'

        if filename == 'index.md':
            main_title = 'Django REST framework - APIs made easy'
        else:
            main_title = main_title + ' - Django REST framework'

        if relative_path == 'index.md':
            canonical_url = base_url
        else:
            canonical_url = base_url + '/' + relative_path[:-3] + suffix
        prev_url = prev_url_map.get(relative_path)
        next_url = next_url_map.get(relative_path)

        content = markdown.markdown(text, ['headerid'])

        output = page.replace('{{ content }}', content).replace('{{ toc }}', toc).replace('{{ base_url }}', base_url).replace('{{ suffix }}', suffix).replace('{{ index }}', index)
        output = output.replace('{{ title }}', main_title)
        output = output.replace('{{ description }}', description)
        output = output.replace('{{ page_id }}', filename[:-3])
        output = output.replace('{{ canonical_url }}', canonical_url)

        if filename =='index.md':
            output = output.replace('{{ ad_block }}', """<hr><p><strong>The team behind REST framework is launching a new API service.</strong></p>
<p>If you want to be first in line when we start issuing invitations, please <a href="http://brightapi.com">sign up here</a>.</p>""")
        else:
            output = output.replace('{{ ad_block }}', '')

        if prev_url:
            output = output.replace('{{ prev_url }}', prev_url)
            output = output.replace('{{ prev_url_disabled }}', '')
        else:
            output = output.replace('{{ prev_url }}', '#')
            output = output.replace('{{ prev_url_disabled }}', 'disabled')

        if next_url:
            output = output.replace('{{ next_url }}', next_url)
            output = output.replace('{{ next_url_disabled }}', '')
        else:
            output = output.replace('{{ next_url }}', '#')
            output = output.replace('{{ next_url_disabled }}', 'disabled')

        output = re.sub(r'a href="([^"]*)\.md"', r'a href="\1%s"' % suffix, output)
        output = re.sub(r'<pre><code>:::bash', r'<pre class="prettyprint lang-bsh">', output)
        output = re.sub(r'<pre>', r'<pre class="prettyprint lang-py">', output)
        output = re.sub(r'<a class="github" href="([^"]*)"></a>', code_label, output)
        open(output_path, 'w').write(output.encode('utf-8'))

if preview:
    import subprocess

    url = 'html/index.html'

    try:
        subprocess.Popen(["open", url])  # Mac
    except OSError:
        subprocess.Popen(["xdg-open", url])  # Linux
    except:
        os.startfile(url)  # Windows

########NEW FILE########
__FILENAME__ = authentication
"""
Provides various authentication policies.
"""
from __future__ import unicode_literals
import base64

from django.contrib.auth import authenticate
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from rest_framework import exceptions, HTTP_HEADER_ENCODING
from rest_framework.compat import CsrfViewMiddleware
from rest_framework.compat import oauth, oauth_provider, oauth_provider_store
from rest_framework.compat import oauth2_provider, provider_now, check_nonce
from rest_framework.authtoken.models import Token


def get_authorization_header(request):
    """
    Return request's 'Authorization:' header, as a bytestring.

    Hide some test client ickyness where the header can be unicode.
    """
    auth = request.META.get('HTTP_AUTHORIZATION', b'')
    if type(auth) == type(''):
        # Work around django test client oddness
        auth = auth.encode(HTTP_HEADER_ENCODING)
    return auth


class CSRFCheck(CsrfViewMiddleware):
    def _reject(self, request, reason):
        # Return the failure reason instead of an HttpResponse
        return reason


class BaseAuthentication(object):
    """
    All authentication classes should extend BaseAuthentication.
    """

    def authenticate(self, request):
        """
        Authenticate the request and return a two-tuple of (user, token).
        """
        raise NotImplementedError(".authenticate() must be overridden.")

    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response, or `None` if the
        authentication scheme should return `403 Permission Denied` responses.
        """
        pass


class BasicAuthentication(BaseAuthentication):
    """
    HTTP Basic authentication against username/password.
    """
    www_authenticate_realm = 'api'

    def authenticate(self, request):
        """
        Returns a `User` if a correct username and password have been supplied
        using HTTP Basic authentication.  Otherwise returns `None`.
        """
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != b'basic':
            return None

        if len(auth) == 1:
            msg = 'Invalid basic header. No credentials provided.'
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = 'Invalid basic header. Credentials string should not contain spaces.'
            raise exceptions.AuthenticationFailed(msg)

        try:
            auth_parts = base64.b64decode(auth[1]).decode(HTTP_HEADER_ENCODING).partition(':')
        except (TypeError, UnicodeDecodeError):
            msg = 'Invalid basic header. Credentials not correctly base64 encoded'
            raise exceptions.AuthenticationFailed(msg)

        userid, password = auth_parts[0], auth_parts[2]
        return self.authenticate_credentials(userid, password)

    def authenticate_credentials(self, userid, password):
        """
        Authenticate the userid and password against username and password.
        """
        user = authenticate(username=userid, password=password)
        if user is None or not user.is_active:
            raise exceptions.AuthenticationFailed('Invalid username/password')
        return (user, None)

    def authenticate_header(self, request):
        return 'Basic realm="%s"' % self.www_authenticate_realm


class SessionAuthentication(BaseAuthentication):
    """
    Use Django's session framework for authentication.
    """

    def authenticate(self, request):
        """
        Returns a `User` if the request session currently has a logged in user.
        Otherwise returns `None`.
        """

        # Get the underlying HttpRequest object
        request = request._request
        user = getattr(request, 'user', None)

        # Unauthenticated, CSRF validation not required
        if not user or not user.is_active:
            return None

        self.enforce_csrf(request)

        # CSRF passed with authenticated user
        return (user, None)

    def enforce_csrf(self, request):
        """
        Enforce CSRF validation for session based authentication.
        """
        reason = CSRFCheck().process_view(request, None, (), {})
        if reason:
            # CSRF failed, bail with explicit error message
            raise exceptions.AuthenticationFailed('CSRF Failed: %s' % reason)


class TokenAuthentication(BaseAuthentication):
    """
    Simple token based authentication.

    Clients should authenticate by passing the token key in the "Authorization"
    HTTP header, prepended with the string "Token ".  For example:

        Authorization: Token 401f7ac837da42b97f613d789819ff93537bee6a
    """

    model = Token
    """
    A custom token model may be used, but must have the following properties.

    * key -- The string identifying the token
    * user -- The user to which the token belongs
    """

    def authenticate(self, request):
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != b'token':
            return None

        if len(auth) == 1:
            msg = 'Invalid token header. No credentials provided.'
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = 'Invalid token header. Token string should not contain spaces.'
            raise exceptions.AuthenticationFailed(msg)

        return self.authenticate_credentials(auth[1])

    def authenticate_credentials(self, key):
        try:
            token = self.model.objects.get(key=key)
        except self.model.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token')

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted')

        return (token.user, token)

    def authenticate_header(self, request):
        return 'Token'


class OAuthAuthentication(BaseAuthentication):
    """
    OAuth 1.0a authentication backend using `django-oauth-plus` and `oauth2`.

    Note: The `oauth2` package actually provides oauth1.0a support.  Urg.
          We import it from the `compat` module as `oauth`.
    """
    www_authenticate_realm = 'api'

    def __init__(self, *args, **kwargs):
        super(OAuthAuthentication, self).__init__(*args, **kwargs)

        if oauth is None:
            raise ImproperlyConfigured(
                "The 'oauth2' package could not be imported."
                "It is required for use with the 'OAuthAuthentication' class.")

        if oauth_provider is None:
            raise ImproperlyConfigured(
                "The 'django-oauth-plus' package could not be imported."
                "It is required for use with the 'OAuthAuthentication' class.")

    def authenticate(self, request):
        """
        Returns two-tuple of (user, token) if authentication succeeds,
        or None otherwise.
        """
        try:
            oauth_request = oauth_provider.utils.get_oauth_request(request)
        except oauth.Error as err:
            raise exceptions.AuthenticationFailed(err.message)

        if not oauth_request:
            return None

        oauth_params = oauth_provider.consts.OAUTH_PARAMETERS_NAMES

        found = any(param for param in oauth_params if param in oauth_request)
        missing = list(param for param in oauth_params if param not in oauth_request)

        if not found:
            # OAuth authentication was not attempted.
            return None

        if missing:
            # OAuth was attempted but missing parameters.
            msg = 'Missing parameters: %s' % (', '.join(missing))
            raise exceptions.AuthenticationFailed(msg)

        if not self.check_nonce(request, oauth_request):
            msg = 'Nonce check failed'
            raise exceptions.AuthenticationFailed(msg)

        try:
            consumer_key = oauth_request.get_parameter('oauth_consumer_key')
            consumer = oauth_provider_store.get_consumer(request, oauth_request, consumer_key)
        except oauth_provider.store.InvalidConsumerError:
            msg = 'Invalid consumer token: %s' % oauth_request.get_parameter('oauth_consumer_key')
            raise exceptions.AuthenticationFailed(msg)

        if consumer.status != oauth_provider.consts.ACCEPTED:
            msg = 'Invalid consumer key status: %s' % consumer.get_status_display()
            raise exceptions.AuthenticationFailed(msg)

        try:
            token_param = oauth_request.get_parameter('oauth_token')
            token = oauth_provider_store.get_access_token(request, oauth_request, consumer, token_param)
        except oauth_provider.store.InvalidTokenError:
            msg = 'Invalid access token: %s' % oauth_request.get_parameter('oauth_token')
            raise exceptions.AuthenticationFailed(msg)

        try:
            self.validate_token(request, consumer, token)
        except oauth.Error as err:
            raise exceptions.AuthenticationFailed(err.message)

        user = token.user

        if not user.is_active:
            msg = 'User inactive or deleted: %s' % user.username
            raise exceptions.AuthenticationFailed(msg)

        return (token.user, token)

    def authenticate_header(self, request):
        """
        If permission is denied, return a '401 Unauthorized' response,
        with an appropraite 'WWW-Authenticate' header.
        """
        return 'OAuth realm="%s"' % self.www_authenticate_realm

    def validate_token(self, request, consumer, token):
        """
        Check the token and raise an `oauth.Error` exception if invalid.
        """
        oauth_server, oauth_request = oauth_provider.utils.initialize_server_request(request)
        oauth_server.verify_request(oauth_request, consumer, token)

    def check_nonce(self, request, oauth_request):
        """
        Checks nonce of request, and return True if valid.
        """
        oauth_nonce = oauth_request['oauth_nonce']
        oauth_timestamp = oauth_request['oauth_timestamp']
        return check_nonce(request, oauth_request, oauth_nonce, oauth_timestamp)


class OAuth2Authentication(BaseAuthentication):
    """
    OAuth 2 authentication backend using `django-oauth2-provider`
    """
    www_authenticate_realm = 'api'
    allow_query_params_token = settings.DEBUG

    def __init__(self, *args, **kwargs):
        super(OAuth2Authentication, self).__init__(*args, **kwargs)

        if oauth2_provider is None:
            raise ImproperlyConfigured(
                "The 'django-oauth2-provider' package could not be imported. "
                "It is required for use with the 'OAuth2Authentication' class.")

    def authenticate(self, request):
        """
        Returns two-tuple of (user, token) if authentication succeeds,
        or None otherwise.
        """

        auth = get_authorization_header(request).split()

        if auth and auth[0].lower() == b'bearer':
            access_token = auth[1]
        elif 'access_token' in request.POST:
            access_token = request.POST['access_token']
        elif 'access_token' in request.GET and self.allow_query_params_token:
            access_token = request.GET['access_token']
        else:
            return None

        if len(auth) == 1:
            msg = 'Invalid bearer header. No credentials provided.'
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = 'Invalid bearer header. Token string should not contain spaces.'
            raise exceptions.AuthenticationFailed(msg)

        return self.authenticate_credentials(request, access_token)

    def authenticate_credentials(self, request, access_token):
        """
        Authenticate the request, given the access token.
        """

        try:
            token = oauth2_provider.oauth2.models.AccessToken.objects.select_related('user')
            # provider_now switches to timezone aware datetime when
            # the oauth2_provider version supports to it.
            token = token.get(token=access_token, expires__gt=provider_now())
        except oauth2_provider.oauth2.models.AccessToken.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token')

        user = token.user

        if not user.is_active:
            msg = 'User inactive or deleted: %s' % user.username
            raise exceptions.AuthenticationFailed(msg)

        return (user, token)

    def authenticate_header(self, request):
        """
        Bearer is the only finalized type currently

        Check details on the `OAuth2Authentication.authenticate` method
        """
        return 'Bearer realm="%s"' % self.www_authenticate_realm

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from rest_framework.authtoken.models import Token


class TokenAdmin(admin.ModelAdmin):
    list_display = ('key', 'user', 'created')
    fields = ('user',)
    ordering = ('-created',)


admin.site.register(Token, TokenAdmin)

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

from rest_framework.settings import api_settings


try:
    from django.contrib.auth import get_user_model
except ImportError: # django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Token'
        db.create_table('authtoken_token', (
            ('key', self.gf('django.db.models.fields.CharField')(max_length=40, primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(related_name='auth_token', unique=True, to=orm['%s.%s' % (User._meta.app_label, User._meta.object_name)])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('authtoken', ['Token'])


    def backwards(self, orm):
        # Deleting model 'Token'
        db.delete_table('authtoken_token')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        "%s.%s" % (User._meta.app_label, User._meta.module_name): {
            'Meta': {'object_name': User._meta.module_name},
        },
        'authtoken.token': {
            'Meta': {'object_name': 'Token'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '40', 'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'auth_token'", 'unique': 'True', 'to': "orm['%s.%s']" % (User._meta.app_label, User._meta.object_name)})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['authtoken']

########NEW FILE########
__FILENAME__ = models
import binascii
import os
from hashlib import sha1
from django.conf import settings
from django.db import models


# Prior to Django 1.5, the AUTH_USER_MODEL setting does not exist.
# Note that we don't perform this code in the compat module due to
# bug report #1297
# See: https://github.com/tomchristie/django-rest-framework/issues/1297
AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


class Token(models.Model):
    """
    The default authorization token model.
    """
    key = models.CharField(max_length=40, primary_key=True)
    user = models.OneToOneField(AUTH_USER_MODEL, related_name='auth_token')
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Work around for a bug in Django:
        # https://code.djangoproject.com/ticket/19422
        #
        # Also see corresponding ticket:
        # https://github.com/tomchristie/django-rest-framework/issues/705
        abstract = 'rest_framework.authtoken' not in settings.INSTALLED_APPS

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(Token, self).save(*args, **kwargs)

    def generate_key(self):
        return binascii.hexlify(os.urandom(20)).decode()

    def __unicode__(self):
        return self.key

########NEW FILE########
__FILENAME__ = serializers
from django.contrib.auth import authenticate
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers


class AuthTokenSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)

            if user:
                if not user.is_active:
                    msg = _('User account is disabled.')
                    raise serializers.ValidationError(msg)
                attrs['user'] = user
                return attrs
            else:
                msg = _('Unable to login with provided credentials.')
                raise serializers.ValidationError(msg)
        else:
            msg = _('Must include "username" and "password"')
            raise serializers.ValidationError(msg)

########NEW FILE########
__FILENAME__ = views
from rest_framework.views import APIView
from rest_framework import status
from rest_framework import parsers
from rest_framework import renderers
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer


class ObtainAuthToken(APIView):
    throttle_classes = ()
    permission_classes = ()
    parser_classes = (parsers.FormParser, parsers.MultiPartParser, parsers.JSONParser,)
    renderer_classes = (renderers.JSONRenderer,)
    serializer_class = AuthTokenSerializer
    model = Token

    def post(self, request):
        serializer = self.serializer_class(data=request.DATA)
        if serializer.is_valid():
            token, created = Token.objects.get_or_create(user=serializer.object['user'])
            return Response({'token': token.key})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


obtain_auth_token = ObtainAuthToken.as_view()

########NEW FILE########
__FILENAME__ = compat
"""
The `compat` module provides support for backwards compatibility with older
versions of django/python, and compatibility wrappers around optional packages.
"""

# flake8: noqa
from __future__ import unicode_literals

import django
import inspect
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

# Try to import six from Django, fallback to included `six`.
try:
    from django.utils import six
except ImportError:
    from rest_framework import six

# location of patterns, url, include changes in 1.4 onwards
try:
    from django.conf.urls import patterns, url, include
except ImportError:
    from django.conf.urls.defaults import patterns, url, include

# Handle django.utils.encoding rename:
# smart_unicode -> smart_text
# force_unicode -> force_text
try:
    from django.utils.encoding import smart_text
except ImportError:
    from django.utils.encoding import smart_unicode as smart_text
try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text


# HttpResponseBase only exists from 1.5 onwards
try:
    from django.http.response import HttpResponseBase
except ImportError:
    from django.http import HttpResponse as HttpResponseBase

# django-filter is optional
try:
    import django_filters
except ImportError:
    django_filters = None

# guardian is optional
try:
    import guardian
except ImportError:
    guardian = None


# cStringIO only if it's available, otherwise StringIO
try:
    import cStringIO.StringIO as StringIO
except ImportError:
    StringIO = six.StringIO

BytesIO = six.BytesIO


# urlparse compat import (Required because it changed in python 3.x)
try:
    from urllib import parse as urlparse
except ImportError:
    import urlparse

# UserDict moves in Python 3
try:
    from UserDict import UserDict
    from UserDict import DictMixin
except ImportError:
    from collections import UserDict
    from collections import MutableMapping as DictMixin

# Try to import PIL in either of the two ways it can end up installed.
try:
    from PIL import Image
except ImportError:
    try:
        import Image
    except ImportError:
        Image = None


def get_model_name(model_cls):
    try:
        return model_cls._meta.model_name
    except AttributeError:
        # < 1.6 used module_name instead of model_name
        return model_cls._meta.module_name


def get_concrete_model(model_cls):
    try:
        return model_cls._meta.concrete_model
    except AttributeError:
        # 1.3 does not include concrete model
        return model_cls


if django.VERSION >= (1, 5):
    from django.views.generic import View
else:
    from django.views.generic import View as _View
    from django.utils.decorators import classonlymethod
    from django.utils.functional import update_wrapper

    class View(_View):
        # 1.3 does not include head method in base View class
        # See: https://code.djangoproject.com/ticket/15668
        @classonlymethod
        def as_view(cls, **initkwargs):
            """
            Main entry point for a request-response process.
            """
            # sanitize keyword arguments
            for key in initkwargs:
                if key in cls.http_method_names:
                    raise TypeError("You tried to pass in the %s method name as a "
                                    "keyword argument to %s(). Don't do that."
                                    % (key, cls.__name__))
                if not hasattr(cls, key):
                    raise TypeError("%s() received an invalid keyword %r" % (
                        cls.__name__, key))

            def view(request, *args, **kwargs):
                self = cls(**initkwargs)
                if hasattr(self, 'get') and not hasattr(self, 'head'):
                    self.head = self.get
                return self.dispatch(request, *args, **kwargs)

            # take name and docstring from class
            update_wrapper(view, cls, updated=())

            # and possible attributes set by decorators
            # like csrf_exempt from dispatch
            update_wrapper(view, cls.dispatch, assigned=())
            return view

        # _allowed_methods only present from 1.5 onwards
        def _allowed_methods(self):
            return [m.upper() for m in self.http_method_names if hasattr(self, m)]


# PATCH method is not implemented by Django
if 'patch' not in View.http_method_names:
    View.http_method_names = View.http_method_names + ['patch']


# PUT, DELETE do not require CSRF until 1.4.  They should.  Make it better.
if django.VERSION >= (1, 4):
    from django.middleware.csrf import CsrfViewMiddleware
else:
    import hashlib
    import re
    import random
    import logging

    from django.conf import settings
    from django.core.urlresolvers import get_callable

    try:
        from logging import NullHandler
    except ImportError:
        class NullHandler(logging.Handler):
            def emit(self, record):
                pass

    logger = logging.getLogger('django.request')

    if not logger.handlers:
        logger.addHandler(NullHandler())

    def same_origin(url1, url2):
        """
        Checks if two URLs are 'same-origin'
        """
        p1, p2 = urlparse.urlparse(url1), urlparse.urlparse(url2)
        return p1[0:2] == p2[0:2]

    def constant_time_compare(val1, val2):
        """
        Returns True if the two strings are equal, False otherwise.

        The time taken is independent of the number of characters that match.
        """
        if len(val1) != len(val2):
            return False
        result = 0
        for x, y in zip(val1, val2):
            result |= ord(x) ^ ord(y)
        return result == 0

    # Use the system (hardware-based) random number generator if it exists.
    if hasattr(random, 'SystemRandom'):
        randrange = random.SystemRandom().randrange
    else:
        randrange = random.randrange

    _MAX_CSRF_KEY = 18446744073709551616      # 2 << 63

    REASON_NO_REFERER = "Referer checking failed - no Referer."
    REASON_BAD_REFERER = "Referer checking failed - %s does not match %s."
    REASON_NO_CSRF_COOKIE = "CSRF cookie not set."
    REASON_BAD_TOKEN = "CSRF token missing or incorrect."

    def _get_failure_view():
        """
        Returns the view to be used for CSRF rejections
        """
        return get_callable(settings.CSRF_FAILURE_VIEW)

    def _get_new_csrf_key():
        return hashlib.md5("%s%s" % (randrange(0, _MAX_CSRF_KEY), settings.SECRET_KEY)).hexdigest()

    def get_token(request):
        """
        Returns the the CSRF token required for a POST form. The token is an
        alphanumeric value.

        A side effect of calling this function is to make the the csrf_protect
        decorator and the CsrfViewMiddleware add a CSRF cookie and a 'Vary: Cookie'
        header to the outgoing response.  For this reason, you may need to use this
        function lazily, as is done by the csrf context processor.
        """
        request.META["CSRF_COOKIE_USED"] = True
        return request.META.get("CSRF_COOKIE", None)

    def _sanitize_token(token):
        # Allow only alphanum, and ensure we return a 'str' for the sake of the post
        # processing middleware.
        token = re.sub('[^a-zA-Z0-9]', '', str(token.decode('ascii', 'ignore')))
        if token == "":
            # In case the cookie has been truncated to nothing at some point.
            return _get_new_csrf_key()
        else:
            return token

    class CsrfViewMiddleware(object):
        """
        Middleware that requires a present and correct csrfmiddlewaretoken
        for POST requests that have a CSRF cookie, and sets an outgoing
        CSRF cookie.

        This middleware should be used in conjunction with the csrf_token template
        tag.
        """
        # The _accept and _reject methods currently only exist for the sake of the
        # requires_csrf_token decorator.
        def _accept(self, request):
            # Avoid checking the request twice by adding a custom attribute to
            # request.  This will be relevant when both decorator and middleware
            # are used.
            request.csrf_processing_done = True
            return None

        def _reject(self, request, reason):
            return _get_failure_view()(request, reason=reason)

        def process_view(self, request, callback, callback_args, callback_kwargs):

            if getattr(request, 'csrf_processing_done', False):
                return None

            try:
                csrf_token = _sanitize_token(request.COOKIES[settings.CSRF_COOKIE_NAME])
                # Use same token next time
                request.META['CSRF_COOKIE'] = csrf_token
            except KeyError:
                csrf_token = None
                # Generate token and store it in the request, so it's available to the view.
                request.META["CSRF_COOKIE"] = _get_new_csrf_key()

            # Wait until request.META["CSRF_COOKIE"] has been manipulated before
            # bailing out, so that get_token still works
            if getattr(callback, 'csrf_exempt', False):
                return None

            # Assume that anything not defined as 'safe' by RC2616 needs protection.
            if request.method not in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
                if getattr(request, '_dont_enforce_csrf_checks', False):
                    # Mechanism to turn off CSRF checks for test suite.  It comes after
                    # the creation of CSRF cookies, so that everything else continues to
                    # work exactly the same (e.g. cookies are sent etc), but before the
                    # any branches that call reject()
                    return self._accept(request)

                if request.is_secure():
                    # Suppose user visits http://example.com/
                    # An active network attacker,(man-in-the-middle, MITM) sends a
                    # POST form which targets https://example.com/detonate-bomb/ and
                    # submits it via javascript.
                    #
                    # The attacker will need to provide a CSRF cookie and token, but
                    # that is no problem for a MITM and the session independent
                    # nonce we are using. So the MITM can circumvent the CSRF
                    # protection. This is true for any HTTP connection, but anyone
                    # using HTTPS expects better!  For this reason, for
                    # https://example.com/ we need additional protection that treats
                    # http://example.com/ as completely untrusted.  Under HTTPS,
                    # Barth et al. found that the Referer header is missing for
                    # same-domain requests in only about 0.2% of cases or less, so
                    # we can use strict Referer checking.
                    referer = request.META.get('HTTP_REFERER')
                    if referer is None:
                        logger.warning('Forbidden (%s): %s' % (REASON_NO_REFERER, request.path),
                            extra={
                                'status_code': 403,
                                'request': request,
                            }
                        )
                        return self._reject(request, REASON_NO_REFERER)

                    # Note that request.get_host() includes the port
                    good_referer = 'https://%s/' % request.get_host()
                    if not same_origin(referer, good_referer):
                        reason = REASON_BAD_REFERER % (referer, good_referer)
                        logger.warning('Forbidden (%s): %s' % (reason, request.path),
                            extra={
                                'status_code': 403,
                                'request': request,
                            }
                        )
                        return self._reject(request, reason)

                if csrf_token is None:
                    # No CSRF cookie. For POST requests, we insist on a CSRF cookie,
                    # and in this way we can avoid all CSRF attacks, including login
                    # CSRF.
                    logger.warning('Forbidden (%s): %s' % (REASON_NO_CSRF_COOKIE, request.path),
                        extra={
                            'status_code': 403,
                            'request': request,
                        }
                    )
                    return self._reject(request, REASON_NO_CSRF_COOKIE)

                # check non-cookie token for match
                request_csrf_token = ""
                if request.method == "POST":
                    request_csrf_token = request.POST.get('csrfmiddlewaretoken', '')

                if request_csrf_token == "":
                    # Fall back to X-CSRFToken, to make things easier for AJAX,
                    # and possible for PUT/DELETE
                    request_csrf_token = request.META.get('HTTP_X_CSRFTOKEN', '')

                if not constant_time_compare(request_csrf_token, csrf_token):
                    logger.warning('Forbidden (%s): %s' % (REASON_BAD_TOKEN, request.path),
                        extra={
                            'status_code': 403,
                            'request': request,
                        }
                    )
                    return self._reject(request, REASON_BAD_TOKEN)

            return self._accept(request)

# timezone support is new in Django 1.4
try:
    from django.utils import timezone
except ImportError:
    timezone = None

# dateparse is ALSO new in Django 1.4
try:
    from django.utils.dateparse import parse_date, parse_datetime, parse_time
except ImportError:
    import datetime
    import re

    date_re = re.compile(
        r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})$'
    )

    datetime_re = re.compile(
        r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})'
        r'[T ](?P<hour>\d{1,2}):(?P<minute>\d{1,2})'
        r'(?::(?P<second>\d{1,2})(?:\.(?P<microsecond>\d{1,6})\d{0,6})?)?'
        r'(?P<tzinfo>Z|[+-]\d{1,2}:\d{1,2})?$'
    )

    time_re = re.compile(
        r'(?P<hour>\d{1,2}):(?P<minute>\d{1,2})'
        r'(?::(?P<second>\d{1,2})(?:\.(?P<microsecond>\d{1,6})\d{0,6})?)?'
    )

    def parse_date(value):
        match = date_re.match(value)
        if match:
            kw = dict((k, int(v)) for k, v in match.groupdict().iteritems())
            return datetime.date(**kw)

    def parse_time(value):
        match = time_re.match(value)
        if match:
            kw = match.groupdict()
            if kw['microsecond']:
                kw['microsecond'] = kw['microsecond'].ljust(6, '0')
            kw = dict((k, int(v)) for k, v in kw.iteritems() if v is not None)
            return datetime.time(**kw)

    def parse_datetime(value):
        """Parse datetime, but w/o the timezone awareness in 1.4"""
        match = datetime_re.match(value)
        if match:
            kw = match.groupdict()
            if kw['microsecond']:
                kw['microsecond'] = kw['microsecond'].ljust(6, '0')
            kw = dict((k, int(v)) for k, v in kw.iteritems() if v is not None)
            return datetime.datetime(**kw)


# smart_urlquote is new on Django 1.4
try:
    from django.utils.html import smart_urlquote
except ImportError:
    import re
    from django.utils.encoding import smart_str
    try:
        from urllib.parse import quote, urlsplit, urlunsplit
    except ImportError:     # Python 2
        from urllib import quote
        from urlparse import urlsplit, urlunsplit

    unquoted_percents_re = re.compile(r'%(?![0-9A-Fa-f]{2})')

    def smart_urlquote(url):
        "Quotes a URL if it isn't already quoted."
        # Handle IDN before quoting.
        scheme, netloc, path, query, fragment = urlsplit(url)
        try:
            netloc = netloc.encode('idna').decode('ascii')  # IDN -> ACE
        except UnicodeError:  # invalid domain part
            pass
        else:
            url = urlunsplit((scheme, netloc, path, query, fragment))

        # An URL is considered unquoted if it contains no % characters or
        # contains a % not followed by two hexadecimal digits. See #9655.
        if '%' not in url or unquoted_percents_re.search(url):
            # See http://bugs.python.org/issue2637
            url = quote(smart_str(url), safe=b'!*\'();:@&=+$,/?#[]~')

        return force_text(url)


# RequestFactory only provide `generic` from 1.5 onwards

from django.test.client import RequestFactory as DjangoRequestFactory
from django.test.client import FakePayload
try:
    # In 1.5 the test client uses force_bytes
    from django.utils.encoding import force_bytes as force_bytes_or_smart_bytes
except ImportError:
    # In 1.3 and 1.4 the test client just uses smart_str
    from django.utils.encoding import smart_str as force_bytes_or_smart_bytes


class RequestFactory(DjangoRequestFactory):
    def generic(self, method, path,
            data='', content_type='application/octet-stream', **extra):
        parsed = urlparse.urlparse(path)
        data = force_bytes_or_smart_bytes(data, settings.DEFAULT_CHARSET)
        r = {
            'PATH_INFO':      self._get_path(parsed),
            'QUERY_STRING':   force_text(parsed[4]),
            'REQUEST_METHOD': str(method),
        }
        if data:
            r.update({
                'CONTENT_LENGTH': len(data),
                'CONTENT_TYPE':   str(content_type),
                'wsgi.input':     FakePayload(data),
            })
        elif django.VERSION <= (1, 4):
            # For 1.3 we need an empty WSGI payload
            r.update({
                'wsgi.input': FakePayload('')
            })
        r.update(extra)
        return self.request(**r)

# Markdown is optional
try:
    import markdown

    def apply_markdown(text):
        """
        Simple wrapper around :func:`markdown.markdown` to set the base level
        of '#' style headers to <h2>.
        """

        extensions = ['headerid(level=2)']
        safe_mode = False
        md = markdown.Markdown(extensions=extensions, safe_mode=safe_mode)
        return md.convert(text)

except ImportError:
    apply_markdown = None


# Yaml is optional
try:
    import yaml
except ImportError:
    yaml = None


# XML is optional
try:
    import defusedxml.ElementTree as etree
except ImportError:
    etree = None

# OAuth is optional
try:
    # Note: The `oauth2` package actually provides oauth1.0a support.  Urg.
    import oauth2 as oauth
except ImportError:
    oauth = None

# OAuth is optional
try:
    import oauth_provider
    from oauth_provider.store import store as oauth_provider_store

    # check_nonce's calling signature in django-oauth-plus changes sometime
    # between versions 2.0 and 2.2.1
    def check_nonce(request, oauth_request, oauth_nonce, oauth_timestamp):
        check_nonce_args = inspect.getargspec(oauth_provider_store.check_nonce).args
        if 'timestamp' in check_nonce_args:
            return oauth_provider_store.check_nonce(
                request, oauth_request, oauth_nonce, oauth_timestamp
            )
        return oauth_provider_store.check_nonce(
            request, oauth_request, oauth_nonce
        )

except (ImportError, ImproperlyConfigured):
    oauth_provider = None
    oauth_provider_store = None
    check_nonce = None

# OAuth 2 support is optional
try:
    import provider as oauth2_provider
    from provider import scope as oauth2_provider_scope
    from provider import constants as oauth2_constants
    if oauth2_provider.__version__ in ('0.2.3', '0.2.4'):
        # 0.2.3 and 0.2.4 are supported version that do not support
        # timezone aware datetimes
        import datetime
        provider_now = datetime.datetime.now
    else:
        # Any other supported version does use timezone aware datetimes
        from django.utils.timezone import now as provider_now
except ImportError:
    oauth2_provider = None
    oauth2_provider_scope = None
    oauth2_constants = None
    provider_now = None

# Handle lazy strings
from django.utils.functional import Promise

if six.PY3:
    def is_non_str_iterable(obj):
        if (isinstance(obj, str) or
            (isinstance(obj, Promise) and obj._delegate_text)):
            return False
        return hasattr(obj, '__iter__')
else:
    def is_non_str_iterable(obj):
        return hasattr(obj, '__iter__')


try:
    from django.utils.encoding import python_2_unicode_compatible
except ImportError:
    def python_2_unicode_compatible(klass):
        """
        A decorator that defines __unicode__ and __str__ methods under Python 2.
        Under Python 3 it does nothing.

        To support Python 2 and 3 with a single code base, define a __str__ method
        returning text and apply this decorator to the class.
        """
        if '__str__' not in klass.__dict__:
            raise ValueError("@python_2_unicode_compatible cannot be applied "
                             "to %s because it doesn't define __str__()." %
                             klass.__name__)
        klass.__unicode__ = klass.__str__
        klass.__str__ = lambda self: self.__unicode__().encode('utf-8')
        return klass

########NEW FILE########
__FILENAME__ = decorators
"""
The most important decorator in this module is `@api_view`, which is used
for writing function-based views with REST framework.

There are also various decorators for setting the API policies on function
based views, as well as the `@action` and `@link` decorators, which are
used to annotate methods on viewsets that should be included by routers.
"""
from __future__ import unicode_literals
from rest_framework.compat import six
from rest_framework.views import APIView
import types


def api_view(http_method_names):

    """
    Decorator that converts a function-based view into an APIView subclass.
    Takes a list of allowed methods for the view as an argument.
    """

    def decorator(func):

        WrappedAPIView = type(
            six.PY3 and 'WrappedAPIView' or b'WrappedAPIView',
            (APIView,),
            {'__doc__': func.__doc__}
        )

        # Note, the above allows us to set the docstring.
        # It is the equivalent of:
        #
        #     class WrappedAPIView(APIView):
        #         pass
        #     WrappedAPIView.__doc__ = func.doc    <--- Not possible to do this

        # api_view applied without (method_names)
        assert not(isinstance(http_method_names, types.FunctionType)), \
            '@api_view missing list of allowed HTTP methods'

        # api_view applied with eg. string instead of list of strings
        assert isinstance(http_method_names, (list, tuple)), \
            '@api_view expected a list of strings, received %s' % type(http_method_names).__name__

        allowed_methods = set(http_method_names) | set(('options',))
        WrappedAPIView.http_method_names = [method.lower() for method in allowed_methods]

        def handler(self, *args, **kwargs):
            return func(*args, **kwargs)

        for method in http_method_names:
            setattr(WrappedAPIView, method.lower(), handler)

        WrappedAPIView.__name__ = func.__name__

        WrappedAPIView.renderer_classes = getattr(func, 'renderer_classes',
                                                  APIView.renderer_classes)

        WrappedAPIView.parser_classes = getattr(func, 'parser_classes',
                                                APIView.parser_classes)

        WrappedAPIView.authentication_classes = getattr(func, 'authentication_classes',
                                                        APIView.authentication_classes)

        WrappedAPIView.throttle_classes = getattr(func, 'throttle_classes',
                                                  APIView.throttle_classes)

        WrappedAPIView.permission_classes = getattr(func, 'permission_classes',
                                                    APIView.permission_classes)

        return WrappedAPIView.as_view()
    return decorator


def renderer_classes(renderer_classes):
    def decorator(func):
        func.renderer_classes = renderer_classes
        return func
    return decorator


def parser_classes(parser_classes):
    def decorator(func):
        func.parser_classes = parser_classes
        return func
    return decorator


def authentication_classes(authentication_classes):
    def decorator(func):
        func.authentication_classes = authentication_classes
        return func
    return decorator


def throttle_classes(throttle_classes):
    def decorator(func):
        func.throttle_classes = throttle_classes
        return func
    return decorator


def permission_classes(permission_classes):
    def decorator(func):
        func.permission_classes = permission_classes
        return func
    return decorator


def link(**kwargs):
    """
    Used to mark a method on a ViewSet that should be routed for GET requests.
    """
    def decorator(func):
        func.bind_to_methods = ['get']
        func.kwargs = kwargs
        return func
    return decorator


def action(methods=['post'], **kwargs):
    """
    Used to mark a method on a ViewSet that should be routed for POST requests.
    """
    def decorator(func):
        func.bind_to_methods = methods
        func.kwargs = kwargs
        return func
    return decorator

########NEW FILE########
__FILENAME__ = exceptions
"""
Handled exceptions raised by REST framework.

In addition Django's built in 403 and 404 exceptions are handled.
(`django.http.Http404` and `django.core.exceptions.PermissionDenied`)
"""
from __future__ import unicode_literals
from rest_framework import status
import math


class APIException(Exception):
    """
    Base class for REST framework exceptions.
    Subclasses should provide `.status_code` and `.default_detail` properties.
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = ''

    def __init__(self, detail=None):
        self.detail = detail or self.default_detail

    def __str__(self):
        return self.detail

class ParseError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Malformed request.'


class AuthenticationFailed(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Incorrect authentication credentials.'


class NotAuthenticated(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Authentication credentials were not provided.'


class PermissionDenied(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'You do not have permission to perform this action.'


class MethodNotAllowed(APIException):
    status_code = status.HTTP_405_METHOD_NOT_ALLOWED
    default_detail = "Method '%s' not allowed."

    def __init__(self, method, detail=None):
        self.detail = (detail or self.default_detail) % method


class NotAcceptable(APIException):
    status_code = status.HTTP_406_NOT_ACCEPTABLE
    default_detail = "Could not satisfy the request's Accept header"

    def __init__(self, detail=None, available_renderers=None):
        self.detail = detail or self.default_detail
        self.available_renderers = available_renderers


class UnsupportedMediaType(APIException):
    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    default_detail = "Unsupported media type '%s' in request."

    def __init__(self, media_type, detail=None):
        self.detail = (detail or self.default_detail) % media_type


class Throttled(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = 'Request was throttled.'
    extra_detail = "Expected available in %d second%s."

    def __init__(self, wait=None, detail=None):
        if wait is None:
            self.detail = detail or self.default_detail
            self.wait = None
        else:
            format = (detail or self.default_detail) + self.extra_detail
            self.detail = format % (wait, wait != 1 and 's' or '')
            self.wait = math.ceil(wait)

########NEW FILE########
__FILENAME__ = fields
"""
Serializer fields perform validation on incoming data.

They are very similar to Django's form fields.
"""
from __future__ import unicode_literals

import copy
import datetime
import inspect
import re
import warnings
from decimal import Decimal, DecimalException
from django import forms
from django.core import validators
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db.models.fields import BLANK_CHOICE_DASH
from django.http import QueryDict
from django.forms import widgets
from django.utils.encoding import is_protected_type
from django.utils.translation import ugettext_lazy as _
from django.utils.datastructures import SortedDict
from rest_framework import ISO_8601
from rest_framework.compat import (
    timezone, parse_date, parse_datetime, parse_time, BytesIO, six, smart_text,
    force_text, is_non_str_iterable
)
from rest_framework.settings import api_settings


def is_simple_callable(obj):
    """
    True if the object is a callable that takes no arguments.
    """
    function = inspect.isfunction(obj)
    method = inspect.ismethod(obj)

    if not (function or method):
        return False

    args, _, _, defaults = inspect.getargspec(obj)
    len_args = len(args) if function else len(args) - 1
    len_defaults = len(defaults) if defaults else 0
    return len_args <= len_defaults


def get_component(obj, attr_name):
    """
    Given an object, and an attribute name,
    return that attribute on the object.
    """
    if isinstance(obj, dict):
        val = obj.get(attr_name)
    else:
        val = getattr(obj, attr_name)

    if is_simple_callable(val):
        return val()
    return val


def readable_datetime_formats(formats):
    format = ', '.join(formats).replace(ISO_8601,
             'YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z]')
    return humanize_strptime(format)


def readable_date_formats(formats):
    format = ', '.join(formats).replace(ISO_8601, 'YYYY[-MM[-DD]]')
    return humanize_strptime(format)


def readable_time_formats(formats):
    format = ', '.join(formats).replace(ISO_8601, 'hh:mm[:ss[.uuuuuu]]')
    return humanize_strptime(format)


def humanize_strptime(format_string):
    # Note that we're missing some of the locale specific mappings that
    # don't really make sense.
    mapping = {
        "%Y": "YYYY",
        "%y": "YY",
        "%m": "MM",
        "%b": "[Jan-Dec]",
        "%B": "[January-December]",
        "%d": "DD",
        "%H": "hh",
        "%I": "hh",  # Requires '%p' to differentiate from '%H'.
        "%M": "mm",
        "%S": "ss",
        "%f": "uuuuuu",
        "%a": "[Mon-Sun]",
        "%A": "[Monday-Sunday]",
        "%p": "[AM|PM]",
        "%z": "[+HHMM|-HHMM]"
    }
    for key, val in mapping.items():
        format_string = format_string.replace(key, val)
    return format_string


def strip_multiple_choice_msg(help_text):
    """
    Remove the 'Hold down "control" ...' message that is Django enforces in
    select multiple fields on ModelForms.  (Required for 1.5 and earlier)

    See https://code.djangoproject.com/ticket/9321
    """
    multiple_choice_msg = _(' Hold down "Control", or "Command" on a Mac, to select more than one.')
    multiple_choice_msg = force_text(multiple_choice_msg)

    return help_text.replace(multiple_choice_msg, '')


class Field(object):
    read_only = True
    creation_counter = 0
    empty = ''
    type_name = None
    partial = False
    use_files = False
    form_field_class = forms.CharField
    type_label = 'field'
    widget = None

    def __init__(self, source=None, label=None, help_text=None):
        self.parent = None

        self.creation_counter = Field.creation_counter
        Field.creation_counter += 1

        self.source = source

        if label is not None:
            self.label = smart_text(label)
        else:
            self.label = None

        if help_text is not None:
            self.help_text = strip_multiple_choice_msg(smart_text(help_text))
        else:
            self.help_text = None

        self._errors = []
        self._value = None
        self._name = None

    @property
    def errors(self):
        return self._errors

    def widget_html(self):
        if not self.widget:
            return ''

        attrs = {}
        if 'id' not in self.widget.attrs:
            attrs['id'] = self._name

        return self.widget.render(self._name, self._value, attrs=attrs)

    def label_tag(self):
        return '<label for="%s">%s:</label>' % (self._name, self.label)

    def initialize(self, parent, field_name):
        """
        Called to set up a field prior to field_to_native or field_from_native.

        parent - The parent serializer.
        field_name - The name of the field being initialized.
        """
        self.parent = parent
        self.root = parent.root or parent
        self.context = self.root.context
        self.partial = self.root.partial
        if self.partial:
            self.required = False

    def field_from_native(self, data, files, field_name, into):
        """
        Given a dictionary and a field name, updates the dictionary `into`,
        with the field and it's deserialized value.
        """
        return

    def field_to_native(self, obj, field_name):
        """
        Given and object and a field name, returns the value that should be
        serialized for that field.
        """
        if obj is None:
            return self.empty

        if self.source == '*':
            return self.to_native(obj)

        source = self.source or field_name
        value = obj

        for component in source.split('.'):
            value = get_component(value, component)
            if value is None:
                break

        return self.to_native(value)

    def to_native(self, value):
        """
        Converts the field's value into it's simple representation.
        """
        if is_simple_callable(value):
            value = value()

        if is_protected_type(value):
            return value
        elif (is_non_str_iterable(value) and
              not isinstance(value, (dict, six.string_types))):
            return [self.to_native(item) for item in value]
        elif isinstance(value, dict):
            # Make sure we preserve field ordering, if it exists
            ret = SortedDict()
            for key, val in value.items():
                ret[key] = self.to_native(val)
            return ret
        return force_text(value)

    def attributes(self):
        """
        Returns a dictionary of attributes to be used when serializing to xml.
        """
        if self.type_name:
            return {'type': self.type_name}
        return {}

    def metadata(self):
        metadata = SortedDict()
        metadata['type'] = self.type_label
        metadata['required'] = getattr(self, 'required', False)
        optional_attrs = ['read_only', 'label', 'help_text',
                          'min_length', 'max_length']
        for attr in optional_attrs:
            value = getattr(self, attr, None)
            if value is not None and value != '':
                metadata[attr] = force_text(value, strings_only=True)
        return metadata


class WritableField(Field):
    """
    Base for read/write fields.
    """
    write_only = False
    default_validators = []
    default_error_messages = {
        'required': _('This field is required.'),
        'invalid': _('Invalid value.'),
    }
    widget = widgets.TextInput
    default = None

    def __init__(self, source=None, label=None, help_text=None,
                 read_only=False, write_only=False, required=None,
                 validators=[], error_messages=None, widget=None,
                 default=None, blank=None):

        # 'blank' is to be deprecated in favor of 'required'
        if blank is not None:
            warnings.warn('The `blank` keyword argument is deprecated. '
                          'Use the `required` keyword argument instead.',
                          DeprecationWarning, stacklevel=2)
            required = not(blank)

        super(WritableField, self).__init__(source=source, label=label, help_text=help_text)

        self.read_only = read_only
        self.write_only = write_only

        assert not (read_only and write_only), "Cannot set read_only=True and write_only=True"

        if required is None:
            self.required = not(read_only)
        else:
            assert not (read_only and required), "Cannot set required=True and read_only=True"
            self.required = required

        messages = {}
        for c in reversed(self.__class__.__mro__):
            messages.update(getattr(c, 'default_error_messages', {}))
        messages.update(error_messages or {})
        self.error_messages = messages

        self.validators = self.default_validators + validators
        self.default = default if default is not None else self.default

        # Widgets are only used for HTML forms.
        widget = widget or self.widget
        if isinstance(widget, type):
            widget = widget()
        self.widget = widget

    def __deepcopy__(self, memo):
        result = copy.copy(self)
        memo[id(self)] = result
        result.validators = self.validators[:]
        return result

    def get_default_value(self):
        if is_simple_callable(self.default):
            return self.default()
        return self.default

    def validate(self, value):
        if value in validators.EMPTY_VALUES and self.required:
            raise ValidationError(self.error_messages['required'])

    def run_validators(self, value):
        if value in validators.EMPTY_VALUES:
            return
        errors = []
        for v in self.validators:
            try:
                v(value)
            except ValidationError as e:
                if hasattr(e, 'code') and e.code in self.error_messages:
                    message = self.error_messages[e.code]
                    if e.params:
                        message = message % e.params
                    errors.append(message)
                else:
                    errors.extend(e.messages)
        if errors:
            raise ValidationError(errors)

    def field_to_native(self, obj, field_name):
        if self.write_only:
            return None
        return super(WritableField, self).field_to_native(obj, field_name)

    def field_from_native(self, data, files, field_name, into):
        """
        Given a dictionary and a field name, updates the dictionary `into`,
        with the field and it's deserialized value.
        """
        if self.read_only:
            return

        try:
            data = data or {}
            if self.use_files:
                files = files or {}
                try:
                    native = files[field_name]
                except KeyError:
                    native = data[field_name]
            else:
                native = data[field_name]
        except KeyError:
            if self.default is not None and not self.partial:
                # Note: partial updates shouldn't set defaults
                native = self.get_default_value()
            else:
                if self.required:
                    raise ValidationError(self.error_messages['required'])
                return

        value = self.from_native(native)
        if self.source == '*':
            if value:
                into.update(value)
        else:
            self.validate(value)
            self.run_validators(value)
            into[self.source or field_name] = value

    def from_native(self, value):
        """
        Reverts a simple representation back to the field's value.
        """
        return value


class ModelField(WritableField):
    """
    A generic field that can be used against an arbitrary model field.
    """
    def __init__(self, *args, **kwargs):
        try:
            self.model_field = kwargs.pop('model_field')
        except KeyError:
            raise ValueError("ModelField requires 'model_field' kwarg")

        self.min_length = kwargs.pop('min_length',
                                     getattr(self.model_field, 'min_length', None))
        self.max_length = kwargs.pop('max_length',
                                     getattr(self.model_field, 'max_length', None))
        self.min_value = kwargs.pop('min_value',
                                    getattr(self.model_field, 'min_value', None))
        self.max_value = kwargs.pop('max_value',
                                    getattr(self.model_field, 'max_value', None))

        super(ModelField, self).__init__(*args, **kwargs)

        if self.min_length is not None:
            self.validators.append(validators.MinLengthValidator(self.min_length))
        if self.max_length is not None:
            self.validators.append(validators.MaxLengthValidator(self.max_length))
        if self.min_value is not None:
            self.validators.append(validators.MinValueValidator(self.min_value))
        if self.max_value is not None:
            self.validators.append(validators.MaxValueValidator(self.max_value))

    def from_native(self, value):
        rel = getattr(self.model_field, "rel", None)
        if rel is not None:
            return rel.to._meta.get_field(rel.field_name).to_python(value)
        else:
            return self.model_field.to_python(value)

    def field_to_native(self, obj, field_name):
        value = self.model_field._get_val_from_obj(obj)
        if is_protected_type(value):
            return value
        return self.model_field.value_to_string(obj)

    def attributes(self):
        return {
            "type": self.model_field.get_internal_type()
        }


##### Typed Fields #####

class BooleanField(WritableField):
    type_name = 'BooleanField'
    type_label = 'boolean'
    form_field_class = forms.BooleanField
    widget = widgets.CheckboxInput
    default_error_messages = {
        'invalid': _("'%s' value must be either True or False."),
    }
    empty = False

    def field_from_native(self, data, files, field_name, into):
        # HTML checkboxes do not explicitly represent unchecked as `False`
        # we deal with that here...
        if isinstance(data, QueryDict) and self.default is None:
            self.default = False

        return super(BooleanField, self).field_from_native(
            data, files, field_name, into
        )

    def from_native(self, value):
        if value in ('true', 't', 'True', '1'):
            return True
        if value in ('false', 'f', 'False', '0'):
            return False
        return bool(value)


class CharField(WritableField):
    type_name = 'CharField'
    type_label = 'string'
    form_field_class = forms.CharField

    def __init__(self, max_length=None, min_length=None, *args, **kwargs):
        self.max_length, self.min_length = max_length, min_length
        super(CharField, self).__init__(*args, **kwargs)
        if min_length is not None:
            self.validators.append(validators.MinLengthValidator(min_length))
        if max_length is not None:
            self.validators.append(validators.MaxLengthValidator(max_length))

    def from_native(self, value):
        if isinstance(value, six.string_types) or value is None:
            return value
        return smart_text(value)


class URLField(CharField):
    type_name = 'URLField'
    type_label = 'url'

    def __init__(self, **kwargs):
        if not 'validators' in kwargs:
            kwargs['validators'] = [validators.URLValidator()]
        super(URLField, self).__init__(**kwargs)


class SlugField(CharField):
    type_name = 'SlugField'
    type_label = 'slug'
    form_field_class = forms.SlugField

    default_error_messages = {
        'invalid': _("Enter a valid 'slug' consisting of letters, numbers,"
                     " underscores or hyphens."),
    }
    default_validators = [validators.validate_slug]

    def __init__(self, *args, **kwargs):
        super(SlugField, self).__init__(*args, **kwargs)


class ChoiceField(WritableField):
    type_name = 'ChoiceField'
    type_label = 'multiple choice'
    form_field_class = forms.ChoiceField
    widget = widgets.Select
    default_error_messages = {
        'invalid_choice': _('Select a valid choice. %(value)s is not one of '
                            'the available choices.'),
    }

    def __init__(self, choices=(), blank_display_value=None, *args, **kwargs):
        self.empty = kwargs.pop('empty', '')
        super(ChoiceField, self).__init__(*args, **kwargs)
        self.choices = choices
        if not self.required:
            if blank_display_value is None:
                blank_choice = BLANK_CHOICE_DASH
            else:
                blank_choice = [('', blank_display_value)]
            self.choices = blank_choice + self.choices

    def _get_choices(self):
        return self._choices

    def _set_choices(self, value):
        # Setting choices also sets the choices on the widget.
        # choices can be any iterable, but we call list() on it because
        # it will be consumed more than once.
        self._choices = self.widget.choices = list(value)

    choices = property(_get_choices, _set_choices)

    def metadata(self):
        data = super(ChoiceField, self).metadata()
        data['choices'] = [{'value': v, 'display_name': n} for v, n in self.choices]
        return data

    def validate(self, value):
        """
        Validates that the input is in self.choices.
        """
        super(ChoiceField, self).validate(value)
        if value and not self.valid_value(value):
            raise ValidationError(self.error_messages['invalid_choice'] % {'value': value})

    def valid_value(self, value):
        """
        Check to see if the provided value is a valid choice.
        """
        for k, v in self.choices:
            if isinstance(v, (list, tuple)):
                # This is an optgroup, so look inside the group for options
                for k2, v2 in v:
                    if value == smart_text(k2):
                        return True
            else:
                if value == smart_text(k) or value == k:
                    return True
        return False

    def from_native(self, value):
        value = super(ChoiceField, self).from_native(value)
        if value == self.empty or value in validators.EMPTY_VALUES:
            return self.empty
        return value


class EmailField(CharField):
    type_name = 'EmailField'
    type_label = 'email'
    form_field_class = forms.EmailField

    default_error_messages = {
        'invalid': _('Enter a valid email address.'),
    }
    default_validators = [validators.validate_email]

    def from_native(self, value):
        ret = super(EmailField, self).from_native(value)
        if ret is None:
            return None
        return ret.strip()


class RegexField(CharField):
    type_name = 'RegexField'
    type_label = 'regex'
    form_field_class = forms.RegexField

    def __init__(self, regex, max_length=None, min_length=None, *args, **kwargs):
        super(RegexField, self).__init__(max_length, min_length, *args, **kwargs)
        self.regex = regex

    def _get_regex(self):
        return self._regex

    def _set_regex(self, regex):
        if isinstance(regex, six.string_types):
            regex = re.compile(regex)
        self._regex = regex
        if hasattr(self, '_regex_validator') and self._regex_validator in self.validators:
            self.validators.remove(self._regex_validator)
        self._regex_validator = validators.RegexValidator(regex=regex)
        self.validators.append(self._regex_validator)

    regex = property(_get_regex, _set_regex)


class DateField(WritableField):
    type_name = 'DateField'
    type_label = 'date'
    widget = widgets.DateInput
    form_field_class = forms.DateField

    default_error_messages = {
        'invalid': _("Date has wrong format. Use one of these formats instead: %s"),
    }
    empty = None
    input_formats = api_settings.DATE_INPUT_FORMATS
    format = api_settings.DATE_FORMAT

    def __init__(self, input_formats=None, format=None, *args, **kwargs):
        self.input_formats = input_formats if input_formats is not None else self.input_formats
        self.format = format if format is not None else self.format
        super(DateField, self).__init__(*args, **kwargs)

    def from_native(self, value):
        if value in validators.EMPTY_VALUES:
            return None

        if isinstance(value, datetime.datetime):
            if timezone and settings.USE_TZ and timezone.is_aware(value):
                # Convert aware datetimes to the default time zone
                # before casting them to dates (#17742).
                default_timezone = timezone.get_default_timezone()
                value = timezone.make_naive(value, default_timezone)
            return value.date()
        if isinstance(value, datetime.date):
            return value

        for format in self.input_formats:
            if format.lower() == ISO_8601:
                try:
                    parsed = parse_date(value)
                except (ValueError, TypeError):
                    pass
                else:
                    if parsed is not None:
                        return parsed
            else:
                try:
                    parsed = datetime.datetime.strptime(value, format)
                except (ValueError, TypeError):
                    pass
                else:
                    return parsed.date()

        msg = self.error_messages['invalid'] % readable_date_formats(self.input_formats)
        raise ValidationError(msg)

    def to_native(self, value):
        if value is None or self.format is None:
            return value

        if isinstance(value, datetime.datetime):
            value = value.date()

        if self.format.lower() == ISO_8601:
            return value.isoformat()
        return value.strftime(self.format)


class DateTimeField(WritableField):
    type_name = 'DateTimeField'
    type_label = 'datetime'
    widget = widgets.DateTimeInput
    form_field_class = forms.DateTimeField

    default_error_messages = {
        'invalid': _("Datetime has wrong format. Use one of these formats instead: %s"),
    }
    empty = None
    input_formats = api_settings.DATETIME_INPUT_FORMATS
    format = api_settings.DATETIME_FORMAT

    def __init__(self, input_formats=None, format=None, *args, **kwargs):
        self.input_formats = input_formats if input_formats is not None else self.input_formats
        self.format = format if format is not None else self.format
        super(DateTimeField, self).__init__(*args, **kwargs)

    def from_native(self, value):
        if value in validators.EMPTY_VALUES:
            return None

        if isinstance(value, datetime.datetime):
            return value
        if isinstance(value, datetime.date):
            value = datetime.datetime(value.year, value.month, value.day)
            if settings.USE_TZ:
                # For backwards compatibility, interpret naive datetimes in
                # local time. This won't work during DST change, but we can't
                # do much about it, so we let the exceptions percolate up the
                # call stack.
                warnings.warn("DateTimeField received a naive datetime (%s)"
                              " while time zone support is active." % value,
                              RuntimeWarning)
                default_timezone = timezone.get_default_timezone()
                value = timezone.make_aware(value, default_timezone)
            return value

        for format in self.input_formats:
            if format.lower() == ISO_8601:
                try:
                    parsed = parse_datetime(value)
                except (ValueError, TypeError):
                    pass
                else:
                    if parsed is not None:
                        return parsed
            else:
                try:
                    parsed = datetime.datetime.strptime(value, format)
                except (ValueError, TypeError):
                    pass
                else:
                    return parsed

        msg = self.error_messages['invalid'] % readable_datetime_formats(self.input_formats)
        raise ValidationError(msg)

    def to_native(self, value):
        if value is None or self.format is None:
            return value

        if self.format.lower() == ISO_8601:
            ret = value.isoformat()
            if ret.endswith('+00:00'):
                ret = ret[:-6] + 'Z'
            return ret
        return value.strftime(self.format)


class TimeField(WritableField):
    type_name = 'TimeField'
    type_label = 'time'
    widget = widgets.TimeInput
    form_field_class = forms.TimeField

    default_error_messages = {
        'invalid': _("Time has wrong format. Use one of these formats instead: %s"),
    }
    empty = None
    input_formats = api_settings.TIME_INPUT_FORMATS
    format = api_settings.TIME_FORMAT

    def __init__(self, input_formats=None, format=None, *args, **kwargs):
        self.input_formats = input_formats if input_formats is not None else self.input_formats
        self.format = format if format is not None else self.format
        super(TimeField, self).__init__(*args, **kwargs)

    def from_native(self, value):
        if value in validators.EMPTY_VALUES:
            return None

        if isinstance(value, datetime.time):
            return value

        for format in self.input_formats:
            if format.lower() == ISO_8601:
                try:
                    parsed = parse_time(value)
                except (ValueError, TypeError):
                    pass
                else:
                    if parsed is not None:
                        return parsed
            else:
                try:
                    parsed = datetime.datetime.strptime(value, format)
                except (ValueError, TypeError):
                    pass
                else:
                    return parsed.time()

        msg = self.error_messages['invalid'] % readable_time_formats(self.input_formats)
        raise ValidationError(msg)

    def to_native(self, value):
        if value is None or self.format is None:
            return value

        if isinstance(value, datetime.datetime):
            value = value.time()

        if self.format.lower() == ISO_8601:
            return value.isoformat()
        return value.strftime(self.format)


class IntegerField(WritableField):
    type_name = 'IntegerField'
    type_label = 'integer'
    form_field_class = forms.IntegerField
    empty = 0

    default_error_messages = {
        'invalid': _('Enter a whole number.'),
        'max_value': _('Ensure this value is less than or equal to %(limit_value)s.'),
        'min_value': _('Ensure this value is greater than or equal to %(limit_value)s.'),
    }

    def __init__(self, max_value=None, min_value=None, *args, **kwargs):
        self.max_value, self.min_value = max_value, min_value
        super(IntegerField, self).__init__(*args, **kwargs)

        if max_value is not None:
            self.validators.append(validators.MaxValueValidator(max_value))
        if min_value is not None:
            self.validators.append(validators.MinValueValidator(min_value))

    def from_native(self, value):
        if value in validators.EMPTY_VALUES:
            return None

        try:
            value = int(str(value))
        except (ValueError, TypeError):
            raise ValidationError(self.error_messages['invalid'])
        return value


class FloatField(WritableField):
    type_name = 'FloatField'
    type_label = 'float'
    form_field_class = forms.FloatField
    empty = 0

    default_error_messages = {
        'invalid': _("'%s' value must be a float."),
    }

    def from_native(self, value):
        if value in validators.EMPTY_VALUES:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            msg = self.error_messages['invalid'] % value
            raise ValidationError(msg)


class DecimalField(WritableField):
    type_name = 'DecimalField'
    type_label = 'decimal'
    form_field_class = forms.DecimalField
    empty = Decimal('0')

    default_error_messages = {
        'invalid': _('Enter a number.'),
        'max_value': _('Ensure this value is less than or equal to %(limit_value)s.'),
        'min_value': _('Ensure this value is greater than or equal to %(limit_value)s.'),
        'max_digits': _('Ensure that there are no more than %s digits in total.'),
        'max_decimal_places': _('Ensure that there are no more than %s decimal places.'),
        'max_whole_digits': _('Ensure that there are no more than %s digits before the decimal point.')
    }

    def __init__(self, max_value=None, min_value=None, max_digits=None, decimal_places=None, *args, **kwargs):
        self.max_value, self.min_value = max_value, min_value
        self.max_digits, self.decimal_places = max_digits, decimal_places
        super(DecimalField, self).__init__(*args, **kwargs)

        if max_value is not None:
            self.validators.append(validators.MaxValueValidator(max_value))
        if min_value is not None:
            self.validators.append(validators.MinValueValidator(min_value))

    def from_native(self, value):
        """
        Validates that the input is a decimal number. Returns a Decimal
        instance. Returns None for empty values. Ensures that there are no more
        than max_digits in the number, and no more than decimal_places digits
        after the decimal point.
        """
        if value in validators.EMPTY_VALUES:
            return None
        value = smart_text(value).strip()
        try:
            value = Decimal(value)
        except DecimalException:
            raise ValidationError(self.error_messages['invalid'])
        return value

    def validate(self, value):
        super(DecimalField, self).validate(value)
        if value in validators.EMPTY_VALUES:
            return
        # Check for NaN, Inf and -Inf values. We can't compare directly for NaN,
        # since it is never equal to itself. However, NaN is the only value that
        # isn't equal to itself, so we can use this to identify NaN
        if value != value or value == Decimal("Inf") or value == Decimal("-Inf"):
            raise ValidationError(self.error_messages['invalid'])
        sign, digittuple, exponent = value.as_tuple()
        decimals = abs(exponent)
        # digittuple doesn't include any leading zeros.
        digits = len(digittuple)
        if decimals > digits:
            # We have leading zeros up to or past the decimal point.  Count
            # everything past the decimal point as a digit.  We do not count
            # 0 before the decimal point as a digit since that would mean
            # we would not allow max_digits = decimal_places.
            digits = decimals
        whole_digits = digits - decimals

        if self.max_digits is not None and digits > self.max_digits:
            raise ValidationError(self.error_messages['max_digits'] % self.max_digits)
        if self.decimal_places is not None and decimals > self.decimal_places:
            raise ValidationError(self.error_messages['max_decimal_places'] % self.decimal_places)
        if self.max_digits is not None and self.decimal_places is not None and whole_digits > (self.max_digits - self.decimal_places):
            raise ValidationError(self.error_messages['max_whole_digits'] % (self.max_digits - self.decimal_places))
        return value


class FileField(WritableField):
    use_files = True
    type_name = 'FileField'
    type_label = 'file upload'
    form_field_class = forms.FileField
    widget = widgets.FileInput

    default_error_messages = {
        'invalid': _("No file was submitted. Check the encoding type on the form."),
        'missing': _("No file was submitted."),
        'empty': _("The submitted file is empty."),
        'max_length': _('Ensure this filename has at most %(max)d characters (it has %(length)d).'),
        'contradiction': _('Please either submit a file or check the clear checkbox, not both.')
    }

    def __init__(self, *args, **kwargs):
        self.max_length = kwargs.pop('max_length', None)
        self.allow_empty_file = kwargs.pop('allow_empty_file', False)
        super(FileField, self).__init__(*args, **kwargs)

    def from_native(self, data):
        if data in validators.EMPTY_VALUES:
            return None

        # UploadedFile objects should have name and size attributes.
        try:
            file_name = data.name
            file_size = data.size
        except AttributeError:
            raise ValidationError(self.error_messages['invalid'])

        if self.max_length is not None and len(file_name) > self.max_length:
            error_values = {'max': self.max_length, 'length': len(file_name)}
            raise ValidationError(self.error_messages['max_length'] % error_values)
        if not file_name:
            raise ValidationError(self.error_messages['invalid'])
        if not self.allow_empty_file and not file_size:
            raise ValidationError(self.error_messages['empty'])

        return data

    def to_native(self, value):
        return value.name


class ImageField(FileField):
    use_files = True
    type_name = 'ImageField'
    type_label = 'image upload'
    form_field_class = forms.ImageField

    default_error_messages = {
        'invalid_image': _("Upload a valid image. The file you uploaded was "
                           "either not an image or a corrupted image."),
    }

    def from_native(self, data):
        """
        Checks that the file-upload field data contains a valid image (GIF, JPG,
        PNG, possibly others -- whatever the Python Imaging Library supports).
        """
        f = super(ImageField, self).from_native(data)
        if f is None:
            return None

        from rest_framework.compat import Image
        assert Image is not None, 'Either Pillow or PIL must be installed for ImageField support.'

        # We need to get a file object for PIL. We might have a path or we might
        # have to read the data into memory.
        if hasattr(data, 'temporary_file_path'):
            file = data.temporary_file_path()
        else:
            if hasattr(data, 'read'):
                file = BytesIO(data.read())
            else:
                file = BytesIO(data['content'])

        try:
            # load() could spot a truncated JPEG, but it loads the entire
            # image in memory, which is a DoS vector. See #3848 and #18520.
            # verify() must be called immediately after the constructor.
            Image.open(file).verify()
        except ImportError:
            # Under PyPy, it is possible to import PIL. However, the underlying
            # _imaging C module isn't available, so an ImportError will be
            # raised. Catch and re-raise.
            raise
        except Exception:  # Python Imaging Library doesn't recognize it as an image
            raise ValidationError(self.error_messages['invalid_image'])
        if hasattr(f, 'seek') and callable(f.seek):
            f.seek(0)
        return f


class SerializerMethodField(Field):
    """
    A field that gets its value by calling a method on the serializer it's attached to.
    """

    def __init__(self, method_name, *args, **kwargs):
        self.method_name = method_name
        super(SerializerMethodField, self).__init__(*args, **kwargs)

    def field_to_native(self, obj, field_name):
        value = getattr(self.parent, self.method_name)(obj)
        return self.to_native(value)

########NEW FILE########
__FILENAME__ = filters
"""
Provides generic filtering backends that can be used to filter the results
returned by list views.
"""
from __future__ import unicode_literals
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from rest_framework.compat import django_filters, six, guardian, get_model_name
from rest_framework.settings import api_settings
from functools import reduce
import operator

FilterSet = django_filters and django_filters.FilterSet or None


class BaseFilterBackend(object):
    """
    A base class from which all filter backend classes should inherit.
    """

    def filter_queryset(self, request, queryset, view):
        """
        Return a filtered queryset.
        """
        raise NotImplementedError(".filter_queryset() must be overridden.")


class DjangoFilterBackend(BaseFilterBackend):
    """
    A filter backend that uses django-filter.
    """
    default_filter_set = FilterSet

    def __init__(self):
        assert django_filters, 'Using DjangoFilterBackend, but django-filter is not installed'

    def get_filter_class(self, view, queryset=None):
        """
        Return the django-filters `FilterSet` used to filter the queryset.
        """
        filter_class = getattr(view, 'filter_class', None)
        filter_fields = getattr(view, 'filter_fields', None)

        if filter_class:
            filter_model = filter_class.Meta.model

            assert issubclass(filter_model, queryset.model), \
                'FilterSet model %s does not match queryset model %s' % \
                (filter_model, queryset.model)

            return filter_class

        if filter_fields:
            class AutoFilterSet(self.default_filter_set):
                class Meta:
                    model = queryset.model
                    fields = filter_fields
                    order_by = True
            return AutoFilterSet

        return None

    def filter_queryset(self, request, queryset, view):
        filter_class = self.get_filter_class(view, queryset)

        if filter_class:
            return filter_class(request.QUERY_PARAMS, queryset=queryset).qs

        return queryset


class SearchFilter(BaseFilterBackend):
    # The URL query parameter used for the search.
    search_param = api_settings.SEARCH_PARAM

    def get_search_terms(self, request):
        """
        Search terms are set by a ?search=... query parameter,
        and may be comma and/or whitespace delimited.
        """
        params = request.QUERY_PARAMS.get(self.search_param, '')
        return params.replace(',', ' ').split()

    def construct_search(self, field_name):
        if field_name.startswith('^'):
            return "%s__istartswith" % field_name[1:]
        elif field_name.startswith('='):
            return "%s__iexact" % field_name[1:]
        elif field_name.startswith('@'):
            return "%s__search" % field_name[1:]
        else:
            return "%s__icontains" % field_name

    def filter_queryset(self, request, queryset, view):
        search_fields = getattr(view, 'search_fields', None)

        if not search_fields:
            return queryset

        orm_lookups = [self.construct_search(str(search_field))
                       for search_field in search_fields]

        for search_term in self.get_search_terms(request):
            or_queries = [models.Q(**{orm_lookup: search_term})
                          for orm_lookup in orm_lookups]
            queryset = queryset.filter(reduce(operator.or_, or_queries))

        return queryset


class OrderingFilter(BaseFilterBackend):
    # The URL query parameter used for the ordering.
    ordering_param = api_settings.ORDERING_PARAM
    ordering_fields = None

    def get_ordering(self, request):
        """
        Ordering is set by a comma delimited ?ordering=... query parameter.
        """
        params = request.QUERY_PARAMS.get(self.ordering_param)
        if params:
            return [param.strip() for param in params.split(',')]

    def get_default_ordering(self, view):
        ordering = getattr(view, 'ordering', None)
        if isinstance(ordering, six.string_types):
            return (ordering,)
        return ordering

    def remove_invalid_fields(self, queryset, ordering, view):
        valid_fields = getattr(view, 'ordering_fields', self.ordering_fields)

        if valid_fields is None:
            # Default to allowing filtering on serializer fields
            serializer_class = getattr(view, 'serializer_class')
            if serializer_class is None:
                msg = ("Cannot use %s on a view which does not have either a "
                       "'serializer_class' or 'ordering_fields' attribute.")
                raise ImproperlyConfigured(msg % self.__class__.__name__)
            valid_fields = [
                field.source or field_name
                for field_name, field in serializer_class().fields.items()
                if not getattr(field, 'write_only', False)
            ]
        elif valid_fields == '__all__':
            # View explictly allows filtering on any model field
            valid_fields = [field.name for field in queryset.model._meta.fields]
            valid_fields += queryset.query.aggregates.keys()

        return [term for term in ordering if term.lstrip('-') in valid_fields]

    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request)

        if ordering:
            # Skip any incorrect parameters
            ordering = self.remove_invalid_fields(queryset, ordering, view)

        if not ordering:
            # Use 'ordering' attribute by default
            ordering = self.get_default_ordering(view)

        if ordering:
            return queryset.order_by(*ordering)

        return queryset


class DjangoObjectPermissionsFilter(BaseFilterBackend):
    """
    A filter backend that limits results to those where the requesting user
    has read object level permissions.
    """
    def __init__(self):
        assert guardian, 'Using DjangoObjectPermissionsFilter, but django-guardian is not installed'

    perm_format = '%(app_label)s.view_%(model_name)s'

    def filter_queryset(self, request, queryset, view):
        user = request.user
        model_cls = queryset.model
        kwargs = {
            'app_label': model_cls._meta.app_label,
            'model_name': get_model_name(model_cls)
        }
        permission = self.perm_format % kwargs
        return guardian.shortcuts.get_objects_for_user(user, permission, queryset)

########NEW FILE########
__FILENAME__ = generics
"""
Generic views that provide commonly needed behaviour.
"""
from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.core.paginator import Paginator, InvalidPage
from django.http import Http404
from django.shortcuts import get_object_or_404 as _get_object_or_404
from django.utils.translation import ugettext as _
from rest_framework import views, mixins, exceptions
from rest_framework.request import clone_request
from rest_framework.settings import api_settings
import warnings


def strict_positive_int(integer_string, cutoff=None):
    """
    Cast a string to a strictly positive integer.
    """
    ret = int(integer_string)
    if ret <= 0:
        raise ValueError()
    if cutoff:
        ret = min(ret, cutoff)
    return ret

def get_object_or_404(queryset, *filter_args, **filter_kwargs):
    """
    Same as Django's standard shortcut, but make sure to raise 404
    if the filter_kwargs don't match the required types.
    """
    try:
        return _get_object_or_404(queryset, *filter_args, **filter_kwargs)
    except (TypeError, ValueError):
        raise Http404


class GenericAPIView(views.APIView):
    """
    Base class for all other generic views.
    """

    # You'll need to either set these attributes,
    # or override `get_queryset()`/`get_serializer_class()`.
    queryset = None
    serializer_class = None

    # This shortcut may be used instead of setting either or both
    # of the `queryset`/`serializer_class` attributes, although using
    # the explicit style is generally preferred.
    model = None

    # If you want to use object lookups other than pk, set this attribute.
    # For more complex lookup requirements override `get_object()`.
    lookup_field = 'pk'
    lookup_url_kwarg = None

    # Pagination settings
    paginate_by = api_settings.PAGINATE_BY
    paginate_by_param = api_settings.PAGINATE_BY_PARAM
    max_paginate_by = api_settings.MAX_PAGINATE_BY
    pagination_serializer_class = api_settings.DEFAULT_PAGINATION_SERIALIZER_CLASS
    page_kwarg = 'page'

    # The filter backend classes to use for queryset filtering
    filter_backends = api_settings.DEFAULT_FILTER_BACKENDS

    # The following attributes may be subject to change,
    # and should be considered private API.
    model_serializer_class = api_settings.DEFAULT_MODEL_SERIALIZER_CLASS
    paginator_class = Paginator

    ######################################
    # These are pending deprecation...

    pk_url_kwarg = 'pk'
    slug_url_kwarg = 'slug'
    slug_field = 'slug'
    allow_empty = True
    filter_backend = api_settings.FILTER_BACKEND

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }

    def get_serializer(self, instance=None, data=None, files=None, many=False,
                       partial=False, allow_add_remove=False):
        """
        Return the serializer instance that should be used for validating and
        deserializing input, and for serializing output.
        """
        serializer_class = self.get_serializer_class()
        context = self.get_serializer_context()
        return serializer_class(instance, data=data, files=files,
                                many=many, partial=partial,
                                allow_add_remove=allow_add_remove,
                                context=context)

    def get_pagination_serializer(self, page):
        """
        Return a serializer instance to use with paginated data.
        """
        class SerializerClass(self.pagination_serializer_class):
            class Meta:
                object_serializer_class = self.get_serializer_class()

        pagination_serializer_class = SerializerClass
        context = self.get_serializer_context()
        return pagination_serializer_class(instance=page, context=context)

    def paginate_queryset(self, queryset, page_size=None):
        """
        Paginate a queryset if required, either returning a page object,
        or `None` if pagination is not configured for this view.
        """
        deprecated_style = False
        if page_size is not None:
            warnings.warn('The `page_size` parameter to `paginate_queryset()` '
                          'is due to be deprecated. '
                          'Note that the return style of this method is also '
                          'changed, and will simply return a page object '
                          'when called without a `page_size` argument.',
                          PendingDeprecationWarning, stacklevel=2)
            deprecated_style = True
        else:
            # Determine the required page size.
            # If pagination is not configured, simply return None.
            page_size = self.get_paginate_by()
            if not page_size:
                return None

        if not self.allow_empty:
            warnings.warn(
                'The `allow_empty` parameter is due to be deprecated. '
                'To use `allow_empty=False` style behavior, You should override '
                '`get_queryset()` and explicitly raise a 404 on empty querysets.',
                PendingDeprecationWarning, stacklevel=2
            )

        paginator = self.paginator_class(queryset, page_size,
                                         allow_empty_first_page=self.allow_empty)
        page_kwarg = self.kwargs.get(self.page_kwarg)
        page_query_param = self.request.QUERY_PARAMS.get(self.page_kwarg)
        page = page_kwarg or page_query_param or 1
        try:
            page_number = paginator.validate_number(page)
        except InvalidPage:
            if page == 'last':
                page_number = paginator.num_pages
            else:
                raise Http404(_("Page is not 'last', nor can it be converted to an int."))
        try:
            page = paginator.page(page_number)
        except InvalidPage as e:
            raise Http404(_('Invalid page (%(page_number)s): %(message)s') % {
                                'page_number': page_number,
                                'message': str(e)
            })

        if deprecated_style:
            return (paginator, page, page.object_list, page.has_other_pages())
        return page

    def filter_queryset(self, queryset):
        """
        Given a queryset, filter it with whichever filter backend is in use.

        You are unlikely to want to override this method, although you may need
        to call it either from a list view, or from a custom `get_object`
        method if you want to apply the configured filtering backend to the
        default queryset.
        """
        for backend in self.get_filter_backends():
            queryset = backend().filter_queryset(self.request, queryset, self)
        return queryset

    def get_filter_backends(self):
        """
        Returns the list of filter backends that this view requires.
        """
        filter_backends = self.filter_backends or []
        if not filter_backends and self.filter_backend:
            warnings.warn(
                'The `filter_backend` attribute and `FILTER_BACKEND` setting '
                'are due to be deprecated in favor of a `filter_backends` '
                'attribute and `DEFAULT_FILTER_BACKENDS` setting, that take '
                'a *list* of filter backend classes.',
                PendingDeprecationWarning, stacklevel=2
            )
            filter_backends = [self.filter_backend]
        return filter_backends


    ########################
    ### The following methods provide default implementations
    ### that you may want to override for more complex cases.

    def get_paginate_by(self, queryset=None):
        """
        Return the size of pages to use with pagination.

        If `PAGINATE_BY_PARAM` is set it will attempt to get the page size
        from a named query parameter in the url, eg. ?page_size=100

        Otherwise defaults to using `self.paginate_by`.
        """
        if queryset is not None:
            warnings.warn('The `queryset` parameter to `get_paginate_by()` '
                          'is due to be deprecated.',
                          PendingDeprecationWarning, stacklevel=2)

        if self.paginate_by_param:
            try:
                return strict_positive_int(
                    self.request.QUERY_PARAMS[self.paginate_by_param],
                    cutoff=self.max_paginate_by
                )
            except (KeyError, ValueError):
                pass

        return self.paginate_by

    def get_serializer_class(self):
        """
        Return the class to use for the serializer.
        Defaults to using `self.serializer_class`.

        You may want to override this if you need to provide different
        serializations depending on the incoming request.

        (Eg. admins get full serialization, others get basic serialization)
        """
        serializer_class = self.serializer_class
        if serializer_class is not None:
            return serializer_class

        assert self.model is not None, \
            "'%s' should either include a 'serializer_class' attribute, " \
            "or use the 'model' attribute as a shortcut for " \
            "automatically generating a serializer class." \
            % self.__class__.__name__

        class DefaultSerializer(self.model_serializer_class):
            class Meta:
                model = self.model
        return DefaultSerializer

    def get_queryset(self):
        """
        Get the list of items for this view.
        This must be an iterable, and may be a queryset.
        Defaults to using `self.queryset`.

        You may want to override this if you need to provide different
        querysets depending on the incoming request.

        (Eg. return a list of items that is specific to the user)
        """
        if self.queryset is not None:
            return self.queryset._clone()

        if self.model is not None:
            return self.model._default_manager.all()

        raise ImproperlyConfigured("'%s' must define 'queryset' or 'model'"
                                    % self.__class__.__name__)

    def get_object(self, queryset=None):
        """
        Returns the object the view is displaying.

        You may want to override this if you need to provide non-standard
        queryset lookups.  Eg if objects are referenced using multiple
        keyword arguments in the url conf.
        """
        # Determine the base queryset to use.
        if queryset is None:
            queryset = self.filter_queryset(self.get_queryset())
        else:
            pass  # Deprecation warning

        # Perform the lookup filtering.
        # Note that `pk` and `slug` are deprecated styles of lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup = self.kwargs.get(lookup_url_kwarg, None)
        pk = self.kwargs.get(self.pk_url_kwarg, None)
        slug = self.kwargs.get(self.slug_url_kwarg, None)

        if lookup is not None:
            filter_kwargs = {self.lookup_field: lookup}
        elif pk is not None and self.lookup_field == 'pk':
            warnings.warn(
                'The `pk_url_kwarg` attribute is due to be deprecated. '
                'Use the `lookup_field` attribute instead',
                PendingDeprecationWarning
            )
            filter_kwargs = {'pk': pk}
        elif slug is not None and self.lookup_field == 'pk':
            warnings.warn(
                'The `slug_url_kwarg` attribute is due to be deprecated. '
                'Use the `lookup_field` attribute instead',
                PendingDeprecationWarning
            )
            filter_kwargs = {self.slug_field: slug}
        else:
            raise ImproperlyConfigured(
                'Expected view %s to be called with a URL keyword argument '
                'named "%s". Fix your URL conf, or set the `.lookup_field` '
                'attribute on the view correctly.' %
                (self.__class__.__name__, self.lookup_field)
            )

        obj = get_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    ########################
    ### The following are placeholder methods,
    ### and are intended to be overridden.
    ###
    ### The are not called by GenericAPIView directly,
    ### but are used by the mixin methods.

    def pre_save(self, obj):
        """
        Placeholder method for calling before saving an object.

        May be used to set attributes on the object that are implicit
        in either the request, or the url.
        """
        pass

    def post_save(self, obj, created=False):
        """
        Placeholder method for calling after saving an object.
        """
        pass

    def pre_delete(self, obj):
        """
        Placeholder method for calling before deleting an object.
        """
        pass

    def post_delete(self, obj):
        """
        Placeholder method for calling after deleting an object.
        """
        pass

    def metadata(self, request):
        """
        Return a dictionary of metadata about the view.
        Used to return responses for OPTIONS requests.

        We override the default behavior, and add some extra information
        about the required request body for POST and PUT operations.
        """
        ret = super(GenericAPIView, self).metadata(request)

        actions = {}
        for method in ('PUT', 'POST'):
            if method not in self.allowed_methods:
                continue

            cloned_request = clone_request(request, method)
            try:
                # Test global permissions
                self.check_permissions(cloned_request)
                # Test object permissions
                if method == 'PUT':
                    try:
                        self.get_object()
                    except Http404:
                        # Http404 should be acceptable and the serializer
                        # metadata should be populated. Except this so the
                        # outer "else" clause of the try-except-else block
                        # will be executed.
                        pass
            except (exceptions.APIException, PermissionDenied):
                pass
            else:
                # If user has appropriate permissions for the view, include
                # appropriate metadata about the fields that should be supplied.
                serializer = self.get_serializer()
                actions[method] = serializer.metadata()

        if actions:
            ret['actions'] = actions

        return ret


##########################################################
### Concrete view classes that provide method handlers ###
### by composing the mixin classes with the base view. ###
##########################################################

class CreateAPIView(mixins.CreateModelMixin,
                    GenericAPIView):

    """
    Concrete view for creating a model instance.
    """
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class ListAPIView(mixins.ListModelMixin,
                  GenericAPIView):
    """
    Concrete view for listing a queryset.
    """
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class RetrieveAPIView(mixins.RetrieveModelMixin,
                      GenericAPIView):
    """
    Concrete view for retrieving a model instance.
    """
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class DestroyAPIView(mixins.DestroyModelMixin,
                     GenericAPIView):

    """
    Concrete view for deleting a model instance.
    """
    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


class UpdateAPIView(mixins.UpdateModelMixin,
                    GenericAPIView):

    """
    Concrete view for updating a model instance.
    """
    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class ListCreateAPIView(mixins.ListModelMixin,
                        mixins.CreateModelMixin,
                        GenericAPIView):
    """
    Concrete view for listing a queryset or creating a model instance.
    """
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class RetrieveUpdateAPIView(mixins.RetrieveModelMixin,
                            mixins.UpdateModelMixin,
                            GenericAPIView):
    """
    Concrete view for retrieving, updating a model instance.
    """
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class RetrieveDestroyAPIView(mixins.RetrieveModelMixin,
                             mixins.DestroyModelMixin,
                             GenericAPIView):
    """
    Concrete view for retrieving or deleting a model instance.
    """
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


class RetrieveUpdateDestroyAPIView(mixins.RetrieveModelMixin,
                                   mixins.UpdateModelMixin,
                                   mixins.DestroyModelMixin,
                                   GenericAPIView):
    """
    Concrete view for retrieving, updating or deleting a model instance.
    """
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


##########################
### Deprecated classes ###
##########################

class MultipleObjectAPIView(GenericAPIView):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            'Subclassing `MultipleObjectAPIView` is due to be deprecated. '
            'You should simply subclass `GenericAPIView` instead.',
            PendingDeprecationWarning, stacklevel=2
        )
        super(MultipleObjectAPIView, self).__init__(*args, **kwargs)


class SingleObjectAPIView(GenericAPIView):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            'Subclassing `SingleObjectAPIView` is due to be deprecated. '
            'You should simply subclass `GenericAPIView` instead.',
            PendingDeprecationWarning, stacklevel=2
        )
        super(SingleObjectAPIView, self).__init__(*args, **kwargs)

########NEW FILE########
__FILENAME__ = mixins
"""
Basic building blocks for generic class based views.

We don't bind behaviour to http method handlers yet,
which allows mixin classes to be composed in interesting ways.
"""
from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.request import clone_request
from rest_framework.settings import api_settings
import warnings


def _get_validation_exclusions(obj, pk=None, slug_field=None, lookup_field=None):
    """
    Given a model instance, and an optional pk and slug field,
    return the full list of all other field names on that model.

    For use when performing full_clean on a model instance,
    so we only clean the required fields.
    """
    include = []

    if pk:
        # Pending deprecation
        pk_field = obj._meta.pk
        while pk_field.rel:
            pk_field = pk_field.rel.to._meta.pk
        include.append(pk_field.name)

    if slug_field:
        # Pending deprecation
        include.append(slug_field)

    if lookup_field and lookup_field != 'pk':
        include.append(lookup_field)

    return [field.name for field in obj._meta.fields if field.name not in include]


class CreateModelMixin(object):
    """
    Create a model instance.
    """
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.DATA, files=request.FILES)

        if serializer.is_valid():
            self.pre_save(serializer.object)
            self.object = serializer.save(force_insert=True)
            self.post_save(self.object, created=True)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED,
                            headers=headers)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_success_headers(self, data):
        try:
            return {'Location': data[api_settings.URL_FIELD_NAME]}
        except (TypeError, KeyError):
            return {}


class ListModelMixin(object):
    """
    List a queryset.
    """
    empty_error = "Empty list and '%(class_name)s.allow_empty' is False."

    def list(self, request, *args, **kwargs):
        self.object_list = self.filter_queryset(self.get_queryset())

        # Default is to allow empty querysets.  This can be altered by setting
        # `.allow_empty = False`, to raise 404 errors on empty querysets.
        if not self.allow_empty and not self.object_list:
            warnings.warn(
                'The `allow_empty` parameter is due to be deprecated. '
                'To use `allow_empty=False` style behavior, You should override '
                '`get_queryset()` and explicitly raise a 404 on empty querysets.',
                PendingDeprecationWarning
            )
            class_name = self.__class__.__name__
            error_msg = self.empty_error % {'class_name': class_name}
            raise Http404(error_msg)

        # Switch between paginated or standard style responses
        page = self.paginate_queryset(self.object_list)
        if page is not None:
            serializer = self.get_pagination_serializer(page)
        else:
            serializer = self.get_serializer(self.object_list, many=True)

        return Response(serializer.data)


class RetrieveModelMixin(object):
    """
    Retrieve a model instance.
    """
    def retrieve(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(self.object)
        return Response(serializer.data)


class UpdateModelMixin(object):
    """
    Update a model instance.
    """
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        self.object = self.get_object_or_none()

        serializer = self.get_serializer(self.object, data=request.DATA,
                                         files=request.FILES, partial=partial)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.pre_save(serializer.object)
        except ValidationError as err:
            # full_clean on model instance may be called in pre_save,
            # so we have to handle eventual errors.
            return Response(err.message_dict, status=status.HTTP_400_BAD_REQUEST)

        if self.object is None:
            self.object = serializer.save(force_insert=True)
            self.post_save(self.object, created=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        self.object = serializer.save(force_update=True)
        self.post_save(self.object, created=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def get_object_or_none(self):
        try:
            return self.get_object()
        except Http404:
            if self.request.method == 'PUT':
                # For PUT-as-create operation, we need to ensure that we have
                # relevant permissions, as if this was a POST request.  This
                # will either raise a PermissionDenied exception, or simply
                # return None.
                self.check_permissions(clone_request(self.request, 'POST'))
            else:
                # PATCH requests where the object does not exist should still
                # return a 404 response.
                raise

    def pre_save(self, obj):
        """
        Set any attributes on the object that are implicit in the request.
        """
        # pk and/or slug attributes are implicit in the URL.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup = self.kwargs.get(lookup_url_kwarg, None)
        pk = self.kwargs.get(self.pk_url_kwarg, None)
        slug = self.kwargs.get(self.slug_url_kwarg, None)
        slug_field = slug and self.slug_field or None

        if lookup:
            setattr(obj, self.lookup_field, lookup)

        if pk:
            setattr(obj, 'pk', pk)

        if slug:
            setattr(obj, slug_field, slug)

        # Ensure we clean the attributes so that we don't eg return integer
        # pk using a string representation, as provided by the url conf kwarg.
        if hasattr(obj, 'full_clean'):
            exclude = _get_validation_exclusions(obj, pk, slug_field, self.lookup_field)
            obj.full_clean(exclude)


class DestroyModelMixin(object):
    """
    Destroy a model instance.
    """
    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        self.pre_delete(obj)
        obj.delete()
        self.post_delete(obj)
        return Response(status=status.HTTP_204_NO_CONTENT)

########NEW FILE########
__FILENAME__ = models
# Just to keep things like ./manage.py test happy

########NEW FILE########
__FILENAME__ = negotiation
"""
Content negotiation deals with selecting an appropriate renderer given the
incoming request.  Typically this will be based on the request's Accept header.
"""
from __future__ import unicode_literals
from django.http import Http404
from rest_framework import exceptions
from rest_framework.settings import api_settings
from rest_framework.utils.mediatypes import order_by_precedence, media_type_matches
from rest_framework.utils.mediatypes import _MediaType


class BaseContentNegotiation(object):
    def select_parser(self, request, parsers):
        raise NotImplementedError('.select_parser() must be implemented')

    def select_renderer(self, request, renderers, format_suffix=None):
        raise NotImplementedError('.select_renderer() must be implemented')


class DefaultContentNegotiation(BaseContentNegotiation):
    settings = api_settings

    def select_parser(self, request, parsers):
        """
        Given a list of parsers and a media type, return the appropriate
        parser to handle the incoming request.
        """
        for parser in parsers:
            if media_type_matches(parser.media_type, request.content_type):
                return parser
        return None

    def select_renderer(self, request, renderers, format_suffix=None):
        """
        Given a request and a list of renderers, return a two-tuple of:
        (renderer, media type).
        """
        # Allow URL style format override.  eg. "?format=json
        format_query_param = self.settings.URL_FORMAT_OVERRIDE
        format = format_suffix or request.QUERY_PARAMS.get(format_query_param)

        if format:
            renderers = self.filter_renderers(renderers, format)

        accepts = self.get_accept_list(request)

        # Check the acceptable media types against each renderer,
        # attempting more specific media types first
        # NB. The inner loop here isn't as bad as it first looks :)
        #     Worst case is we're looping over len(accept_list) * len(self.renderers)
        for media_type_set in order_by_precedence(accepts):
            for renderer in renderers:
                for media_type in media_type_set:
                    if media_type_matches(renderer.media_type, media_type):
                        # Return the most specific media type as accepted.
                        if (_MediaType(renderer.media_type).precedence >
                            _MediaType(media_type).precedence):
                            # Eg client requests '*/*'
                            # Accepted media type is 'application/json'
                            return renderer, renderer.media_type
                        else:
                            # Eg client requests 'application/json; indent=8'
                            # Accepted media type is 'application/json; indent=8'
                            return renderer, media_type

        raise exceptions.NotAcceptable(available_renderers=renderers)

    def filter_renderers(self, renderers, format):
        """
        If there is a '.json' style format suffix, filter the renderers
        so that we only negotiation against those that accept that format.
        """
        renderers = [renderer for renderer in renderers
                     if renderer.format == format]
        if not renderers:
            raise Http404
        return renderers

    def get_accept_list(self, request):
        """
        Given the incoming request, return a tokenised list of media
        type strings.

        Allows URL style accept override.  eg. "?accept=application/json"
        """
        header = request.META.get('HTTP_ACCEPT', '*/*')
        header = request.QUERY_PARAMS.get(self.settings.URL_ACCEPT_OVERRIDE, header)
        return [token.strip() for token in header.split(',')]

########NEW FILE########
__FILENAME__ = pagination
"""
Pagination serializers determine the structure of the output that should
be used for paginated responses.
"""
from __future__ import unicode_literals
from rest_framework import serializers
from rest_framework.templatetags.rest_framework import replace_query_param


class NextPageField(serializers.Field):
    """
    Field that returns a link to the next page in paginated results.
    """
    page_field = 'page'

    def to_native(self, value):
        if not value.has_next():
            return None
        page = value.next_page_number()
        request = self.context.get('request')
        url = request and request.build_absolute_uri() or ''
        return replace_query_param(url, self.page_field, page)


class PreviousPageField(serializers.Field):
    """
    Field that returns a link to the previous page in paginated results.
    """
    page_field = 'page'

    def to_native(self, value):
        if not value.has_previous():
            return None
        page = value.previous_page_number()
        request = self.context.get('request')
        url = request and request.build_absolute_uri() or ''
        return replace_query_param(url, self.page_field, page)


class DefaultObjectSerializer(serializers.Field):
    """
    If no object serializer is specified, then this serializer will be applied
    as the default.
    """

    def __init__(self, source=None, context=None):
        # Note: Swallow context kwarg - only required for eg. ModelSerializer.
        super(DefaultObjectSerializer, self).__init__(source=source)


class PaginationSerializerOptions(serializers.SerializerOptions):
    """
    An object that stores the options that may be provided to a
    pagination serializer by using the inner `Meta` class.

    Accessible on the instance as `serializer.opts`.
    """
    def __init__(self, meta):
        super(PaginationSerializerOptions, self).__init__(meta)
        self.object_serializer_class = getattr(meta, 'object_serializer_class',
                                               DefaultObjectSerializer)


class BasePaginationSerializer(serializers.Serializer):
    """
    A base class for pagination serializers to inherit from,
    to make implementing custom serializers more easy.
    """
    _options_class = PaginationSerializerOptions
    results_field = 'results'

    def __init__(self, *args, **kwargs):
        """
        Override init to add in the object serializer field on-the-fly.
        """
        super(BasePaginationSerializer, self).__init__(*args, **kwargs)
        results_field = self.results_field
        object_serializer = self.opts.object_serializer_class

        if 'context' in kwargs:
            context_kwarg = {'context': kwargs['context']}
        else:
            context_kwarg = {}

        self.fields[results_field] = object_serializer(source='object_list', **context_kwarg)


class PaginationSerializer(BasePaginationSerializer):
    """
    A default implementation of a pagination serializer.
    """
    count = serializers.Field(source='paginator.count')
    next = NextPageField(source='*')
    previous = PreviousPageField(source='*')

########NEW FILE########
__FILENAME__ = parsers
"""
Parsers are used to parse the content of incoming HTTP requests.

They give us a generic way of being able to handle various media types
on the request, such as form content or json encoded data.
"""
from __future__ import unicode_literals
from django.conf import settings
from django.core.files.uploadhandler import StopFutureHandlers
from django.http import QueryDict
from django.http.multipartparser import MultiPartParser as DjangoMultiPartParser
from django.http.multipartparser import MultiPartParserError, parse_header, ChunkIter
from rest_framework.compat import etree, six, yaml, force_text
from rest_framework.exceptions import ParseError
from rest_framework import renderers
import json
import datetime
import decimal


class DataAndFiles(object):
    def __init__(self, data, files):
        self.data = data
        self.files = files


class BaseParser(object):
    """
    All parsers should extend `BaseParser`, specifying a `media_type`
    attribute, and overriding the `.parse()` method.
    """

    media_type = None

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Given a stream to read from, return the parsed representation.
        Should return parsed data, or a `DataAndFiles` object consisting of the
        parsed data and files.
        """
        raise NotImplementedError(".parse() must be overridden.")


class JSONParser(BaseParser):
    """
    Parses JSON-serialized data.
    """

    media_type = 'application/json'
    renderer_class = renderers.UnicodeJSONRenderer

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parses the incoming bytestream as JSON and returns the resulting data.
        """
        parser_context = parser_context or {}
        encoding = parser_context.get('encoding', settings.DEFAULT_CHARSET)

        try:
            data = stream.read().decode(encoding)
            return json.loads(data)
        except ValueError as exc:
            raise ParseError('JSON parse error - %s' % six.text_type(exc))


class YAMLParser(BaseParser):
    """
    Parses YAML-serialized data.
    """

    media_type = 'application/yaml'

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parses the incoming bytestream as YAML and returns the resulting data.
        """
        assert yaml, 'YAMLParser requires pyyaml to be installed'

        parser_context = parser_context or {}
        encoding = parser_context.get('encoding', settings.DEFAULT_CHARSET)

        try:
            data = stream.read().decode(encoding)
            return yaml.safe_load(data)
        except (ValueError, yaml.parser.ParserError) as exc:
            raise ParseError('YAML parse error - %s' % six.text_type(exc))


class FormParser(BaseParser):
    """
    Parser for form data.
    """

    media_type = 'application/x-www-form-urlencoded'

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parses the incoming bytestream as a URL encoded form,
        and returns the resulting QueryDict.
        """
        parser_context = parser_context or {}
        encoding = parser_context.get('encoding', settings.DEFAULT_CHARSET)
        data = QueryDict(stream.read(), encoding=encoding)
        return data


class MultiPartParser(BaseParser):
    """
    Parser for multipart form data, which may include file data.
    """

    media_type = 'multipart/form-data'

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parses the incoming bytestream as a multipart encoded form,
        and returns a DataAndFiles object.

        `.data` will be a `QueryDict` containing all the form parameters.
        `.files` will be a `QueryDict` containing all the form files.
        """
        parser_context = parser_context or {}
        request = parser_context['request']
        encoding = parser_context.get('encoding', settings.DEFAULT_CHARSET)
        meta = request.META.copy()
        meta['CONTENT_TYPE'] = media_type
        upload_handlers = request.upload_handlers

        try:
            parser = DjangoMultiPartParser(meta, stream, upload_handlers, encoding)
            data, files = parser.parse()
            return DataAndFiles(data, files)
        except MultiPartParserError as exc:
            raise ParseError('Multipart form parse error - %s' % str(exc))


class XMLParser(BaseParser):
    """
    XML parser.
    """

    media_type = 'application/xml'

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parses the incoming bytestream as XML and returns the resulting data.
        """
        assert etree, 'XMLParser requires defusedxml to be installed'

        parser_context = parser_context or {}
        encoding = parser_context.get('encoding', settings.DEFAULT_CHARSET)
        parser = etree.DefusedXMLParser(encoding=encoding)
        try:
            tree = etree.parse(stream, parser=parser, forbid_dtd=True)
        except (etree.ParseError, ValueError) as exc:
            raise ParseError('XML parse error - %s' % six.text_type(exc))
        data = self._xml_convert(tree.getroot())

        return data

    def _xml_convert(self, element):
        """
        convert the xml `element` into the corresponding python object
        """

        children = list(element)

        if len(children) == 0:
            return self._type_convert(element.text)
        else:
            # if the fist child tag is list-item means all children are list-item
            if children[0].tag == "list-item":
                data = []
                for child in children:
                    data.append(self._xml_convert(child))
            else:
                data = {}
                for child in children:
                    data[child.tag] = self._xml_convert(child)

            return data

    def _type_convert(self, value):
        """
        Converts the value returned by the XMl parse into the equivalent
        Python type
        """
        if value is None:
            return value

        try:
            return datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            pass

        try:
            return int(value)
        except ValueError:
            pass

        try:
            return decimal.Decimal(value)
        except decimal.InvalidOperation:
            pass

        return value


class FileUploadParser(BaseParser):
    """
    Parser for file upload data.
    """
    media_type = '*/*'

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Treats the incoming bytestream as a raw file upload and returns
        a `DateAndFiles` object.

        `.data` will be None (we expect request body to be a file content).
        `.files` will be a `QueryDict` containing one 'file' element.
        """

        parser_context = parser_context or {}
        request = parser_context['request']
        encoding = parser_context.get('encoding', settings.DEFAULT_CHARSET)
        meta = request.META
        upload_handlers = request.upload_handlers
        filename = self.get_filename(stream, media_type, parser_context)

        # Note that this code is extracted from Django's handling of
        # file uploads in MultiPartParser.
        content_type = meta.get('HTTP_CONTENT_TYPE',
                                meta.get('CONTENT_TYPE', ''))
        try:
            content_length = int(meta.get('HTTP_CONTENT_LENGTH',
                                          meta.get('CONTENT_LENGTH', 0)))
        except (ValueError, TypeError):
            content_length = None

        # See if the handler will want to take care of the parsing.
        for handler in upload_handlers:
            result = handler.handle_raw_input(None,
                                              meta,
                                              content_length,
                                              None,
                                              encoding)
            if result is not None:
                return DataAndFiles(None, {'file': result[1]})

        # This is the standard case.
        possible_sizes = [x.chunk_size for x in upload_handlers if x.chunk_size]
        chunk_size = min([2 ** 31 - 4] + possible_sizes)
        chunks = ChunkIter(stream, chunk_size)
        counters = [0] * len(upload_handlers)

        for handler in upload_handlers:
            try:
                handler.new_file(None, filename, content_type,
                                 content_length, encoding)
            except StopFutureHandlers:
                break

        for chunk in chunks:
            for i, handler in enumerate(upload_handlers):
                chunk_length = len(chunk)
                chunk = handler.receive_data_chunk(chunk, counters[i])
                counters[i] += chunk_length
                if chunk is None:
                    break

        for i, handler in enumerate(upload_handlers):
            file_obj = handler.file_complete(counters[i])
            if file_obj:
                return DataAndFiles(None, {'file': file_obj})
        raise ParseError("FileUpload parse error - "
                         "none of upload handlers can handle the stream")

    def get_filename(self, stream, media_type, parser_context):
        """
        Detects the uploaded file name. First searches a 'filename' url kwarg.
        Then tries to parse Content-Disposition header.
        """
        try:
            return parser_context['kwargs']['filename']
        except KeyError:
            pass

        try:
            meta = parser_context['request'].META
            disposition = parse_header(meta['HTTP_CONTENT_DISPOSITION'].encode('utf-8'))
            return force_text(disposition[1]['filename'])
        except (AttributeError, KeyError):
            pass

########NEW FILE########
__FILENAME__ = permissions
"""
Provides a set of pluggable permission policies.
"""
from __future__ import unicode_literals
import inspect
import warnings

SAFE_METHODS = ['GET', 'HEAD', 'OPTIONS']

from django.http import Http404
from rest_framework.compat import (get_model_name, oauth2_provider_scope,
                                   oauth2_constants)


class BasePermission(object):
    """
    A base class from which all permission classes should inherit.
    """

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return True

    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if len(inspect.getargspec(self.has_permission).args) == 4:
            warnings.warn(
                'The `obj` argument in `has_permission` is deprecated. '
                'Use `has_object_permission()` instead for object permissions.',
                DeprecationWarning, stacklevel=2
            )
            return self.has_permission(request, view, obj)
        return True


class AllowAny(BasePermission):
    """
    Allow any access.
    This isn't strictly required, since you could use an empty
    permission_classes list, but it's useful because it makes the intention
    more explicit.
    """
    def has_permission(self, request, view):
        return True


class IsAuthenticated(BasePermission):
    """
    Allows access only to authenticated users.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated()


class IsAdminUser(BasePermission):
    """
    Allows access only to admin users.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class IsAuthenticatedOrReadOnly(BasePermission):
    """
    The request is authenticated as a user, or is a read-only request.
    """

    def has_permission(self, request, view):
        return (request.method in SAFE_METHODS or 
            request.user and 
            request.user.is_authenticated())


class DjangoModelPermissions(BasePermission):
    """
    The request is authenticated using `django.contrib.auth` permissions.
    See: https://docs.djangoproject.com/en/dev/topics/auth/#permissions

    It ensures that the user is authenticated, and has the appropriate
    `add`/`change`/`delete` permissions on the model.

    This permission can only be applied against view classes that
    provide a `.model` or `.queryset` attribute.
    """

    # Map methods into required permission codes.
    # Override this if you need to also provide 'view' permissions,
    # or if you want to provide custom permission codes.
    perms_map = {
        'GET': [],
        'OPTIONS': [],
        'HEAD': [],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }

    authenticated_users_only = True

    def get_required_permissions(self, method, model_cls):
        """
        Given a model and an HTTP method, return the list of permission
        codes that the user is required to have.
        """
        kwargs = {
            'app_label': model_cls._meta.app_label,
            'model_name': get_model_name(model_cls)
        }
        return [perm % kwargs for perm in self.perms_map[method]]

    def has_permission(self, request, view):
        model_cls = getattr(view, 'model', None)
        queryset = getattr(view, 'queryset', None)

        if model_cls is None and queryset is not None:
            model_cls = queryset.model

        # Workaround to ensure DjangoModelPermissions are not applied
        # to the root view when using DefaultRouter.
        if model_cls is None and getattr(view, '_ignore_model_permissions', False):
            return True

        assert model_cls, ('Cannot apply DjangoModelPermissions on a view that'
                           ' does not have `.model` or `.queryset` property.')

        perms = self.get_required_permissions(request.method, model_cls)

        return (request.user and
            (request.user.is_authenticated() or not self.authenticated_users_only) and
            request.user.has_perms(perms))


class DjangoModelPermissionsOrAnonReadOnly(DjangoModelPermissions):
    """
    Similar to DjangoModelPermissions, except that anonymous users are
    allowed read-only access.
    """
    authenticated_users_only = False


class DjangoObjectPermissions(DjangoModelPermissions):
    """
    The request is authenticated using Django's object-level permissions.
    It requires an object-permissions-enabled backend, such as Django Guardian.

    It ensures that the user is authenticated, and has the appropriate
    `add`/`change`/`delete` permissions on the object using .has_perms.

    This permission can only be applied against view classes that
    provide a `.model` or `.queryset` attribute.
    """

    perms_map = {
        'GET': [],
        'OPTIONS': [],
        'HEAD': [],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }

    def get_required_object_permissions(self, method, model_cls):
        kwargs = {
            'app_label': model_cls._meta.app_label,
            'model_name': get_model_name(model_cls)
        }
        return [perm % kwargs for perm in self.perms_map[method]]

    def has_object_permission(self, request, view, obj):
        model_cls = getattr(view, 'model', None)
        queryset = getattr(view, 'queryset', None)

        if model_cls is None and queryset is not None:
            model_cls = queryset.model

        perms = self.get_required_object_permissions(request.method, model_cls)
        user = request.user

        if not user.has_perms(perms, obj):
            # If the user does not have permissions we need to determine if
            # they have read permissions to see 403, or not, and simply see
            # a 404 reponse.

            if request.method in ('GET', 'OPTIONS', 'HEAD'):
                # Read permissions already checked and failed, no need
                # to make another lookup.
                raise Http404

            read_perms = self.get_required_object_permissions('GET', model_cls)
            if not user.has_perms(read_perms, obj):
                raise Http404

            # Has read permissions.
            return False

        return True


class TokenHasReadWriteScope(BasePermission):
    """
    The request is authenticated as a user and the token used has the right scope
    """

    def has_permission(self, request, view):
        token = request.auth
        read_only = request.method in SAFE_METHODS

        if not token:
            return False

        if hasattr(token, 'resource'):  # OAuth 1
            return read_only or not request.auth.resource.is_readonly
        elif hasattr(token, 'scope'):  # OAuth 2
            required = oauth2_constants.READ if read_only else oauth2_constants.WRITE
            return oauth2_provider_scope.check(required, request.auth.scope)

        assert False, ('TokenHasReadWriteScope requires either the'
        '`OAuthAuthentication` or `OAuth2Authentication` authentication '
        'class to be used.')

########NEW FILE########
__FILENAME__ = relations
"""
Serializer fields that deal with relationships.

These fields allow you to specify the style that should be used to represent
model relationships, including hyperlinks, primary keys, or slugs.
"""
from __future__ import unicode_literals
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.urlresolvers import resolve, get_script_prefix, NoReverseMatch
from django import forms
from django.db.models.fields import BLANK_CHOICE_DASH
from django.forms import widgets
from django.forms.models import ModelChoiceIterator
from django.utils.translation import ugettext_lazy as _
from rest_framework.fields import Field, WritableField, get_component, is_simple_callable
from rest_framework.reverse import reverse
from rest_framework.compat import urlparse
from rest_framework.compat import smart_text
import warnings


##### Relational fields #####


# Not actually Writable, but subclasses may need to be.
class RelatedField(WritableField):
    """
    Base class for related model fields.

    This represents a relationship using the unicode representation of the target.
    """
    widget = widgets.Select
    many_widget = widgets.SelectMultiple
    form_field_class = forms.ChoiceField
    many_form_field_class = forms.MultipleChoiceField
    null_values = (None, '', 'None')

    cache_choices = False
    empty_label = None
    read_only = True
    many = False

    def __init__(self, *args, **kwargs):

        # 'null' is to be deprecated in favor of 'required'
        if 'null' in kwargs:
            warnings.warn('The `null` keyword argument is deprecated. '
                          'Use the `required` keyword argument instead.',
                          DeprecationWarning, stacklevel=2)
            kwargs['required'] = not kwargs.pop('null')

        queryset = kwargs.pop('queryset', None)
        self.many = kwargs.pop('many', self.many)
        if self.many:
            self.widget = self.many_widget
            self.form_field_class = self.many_form_field_class

        kwargs['read_only'] = kwargs.pop('read_only', self.read_only)
        super(RelatedField, self).__init__(*args, **kwargs)

        if not self.required:
            # Accessed in ModelChoiceIterator django/forms/models.py:1034
            # If set adds empty choice.
            self.empty_label = BLANK_CHOICE_DASH[0][1]

        self.queryset = queryset

    def initialize(self, parent, field_name):
        super(RelatedField, self).initialize(parent, field_name)
        if self.queryset is None and not self.read_only:
            manager = getattr(self.parent.opts.model, self.source or field_name)
            if hasattr(manager, 'related'):  # Forward
                self.queryset = manager.related.model._default_manager.all()
            else:  # Reverse
                self.queryset = manager.field.rel.to._default_manager.all()

    ### We need this stuff to make form choices work...

    def prepare_value(self, obj):
        return self.to_native(obj)

    def label_from_instance(self, obj):
        """
        Return a readable representation for use with eg. select widgets.
        """
        desc = smart_text(obj)
        ident = smart_text(self.to_native(obj))
        if desc == ident:
            return desc
        return "%s - %s" % (desc, ident)

    def _get_queryset(self):
        return self._queryset

    def _set_queryset(self, queryset):
        self._queryset = queryset
        self.widget.choices = self.choices

    queryset = property(_get_queryset, _set_queryset)

    def _get_choices(self):
        # If self._choices is set, then somebody must have manually set
        # the property self.choices. In this case, just return self._choices.
        if hasattr(self, '_choices'):
            return self._choices

        # Otherwise, execute the QuerySet in self.queryset to determine the
        # choices dynamically. Return a fresh ModelChoiceIterator that has not been
        # consumed. Note that we're instantiating a new ModelChoiceIterator *each*
        # time _get_choices() is called (and, thus, each time self.choices is
        # accessed) so that we can ensure the QuerySet has not been consumed. This
        # construct might look complicated but it allows for lazy evaluation of
        # the queryset.
        return ModelChoiceIterator(self)

    def _set_choices(self, value):
        # Setting choices also sets the choices on the widget.
        # choices can be any iterable, but we call list() on it because
        # it will be consumed more than once.
        self._choices = self.widget.choices = list(value)

    choices = property(_get_choices, _set_choices)

    ### Default value handling

    def get_default_value(self):
        default = super(RelatedField, self).get_default_value()
        if self.many and default is None:
            return []
        return default

    ### Regular serializer stuff...

    def field_to_native(self, obj, field_name):
        try:
            if self.source == '*':
                return self.to_native(obj)

            source = self.source or field_name
            value = obj

            for component in source.split('.'):
                if value is None:
                    break
                value = get_component(value, component)
        except ObjectDoesNotExist:
            return None

        if value is None:
            return None

        if self.many:
            if is_simple_callable(getattr(value, 'all', None)):
                return [self.to_native(item) for item in value.all()]
            else:
                # Also support non-queryset iterables.
                # This allows us to also support plain lists of related items.
                return [self.to_native(item) for item in value]
        return self.to_native(value)

    def field_from_native(self, data, files, field_name, into):
        if self.read_only:
            return

        try:
            if self.many:
                try:
                    # Form data
                    value = data.getlist(field_name)
                    if value == [''] or value == []:
                        raise KeyError
                except AttributeError:
                    # Non-form data
                    value = data[field_name]
            else:
                value = data[field_name]
        except KeyError:
            if self.partial:
                return
            value = self.get_default_value()

        if value in self.null_values:
            if self.required:
                raise ValidationError(self.error_messages['required'])
            into[(self.source or field_name)] = None
        elif self.many:
            into[(self.source or field_name)] = [self.from_native(item) for item in value]
        else:
            into[(self.source or field_name)] = self.from_native(value)


### PrimaryKey relationships

class PrimaryKeyRelatedField(RelatedField):
    """
    Represents a relationship as a pk value.
    """
    read_only = False

    default_error_messages = {
        'does_not_exist': _("Invalid pk '%s' - object does not exist."),
        'incorrect_type': _('Incorrect type.  Expected pk value, received %s.'),
    }

    # TODO: Remove these field hacks...
    def prepare_value(self, obj):
        return self.to_native(obj.pk)

    def label_from_instance(self, obj):
        """
        Return a readable representation for use with eg. select widgets.
        """
        desc = smart_text(obj)
        ident = smart_text(self.to_native(obj.pk))
        if desc == ident:
            return desc
        return "%s - %s" % (desc, ident)

    # TODO: Possibly change this to just take `obj`, through prob less performant
    def to_native(self, pk):
        return pk

    def from_native(self, data):
        if self.queryset is None:
            raise Exception('Writable related fields must include a `queryset` argument')

        try:
            return self.queryset.get(pk=data)
        except ObjectDoesNotExist:
            msg = self.error_messages['does_not_exist'] % smart_text(data)
            raise ValidationError(msg)
        except (TypeError, ValueError):
            received = type(data).__name__
            msg = self.error_messages['incorrect_type'] % received
            raise ValidationError(msg)

    def field_to_native(self, obj, field_name):
        if self.many:
            # To-many relationship

            queryset = None
            if not self.source:
                # Prefer obj.serializable_value for performance reasons
                try:
                    queryset = obj.serializable_value(field_name)
                except AttributeError:
                    pass
            if queryset is None:
                # RelatedManager (reverse relationship)
                source = self.source or field_name
                queryset = obj
                for component in source.split('.'):
                    if queryset is None:
                        return []
                    queryset = get_component(queryset, component)

            # Forward relationship
            if is_simple_callable(getattr(queryset, 'all', None)):
                return [self.to_native(item.pk) for item in queryset.all()]
            else:
                # Also support non-queryset iterables.
                # This allows us to also support plain lists of related items.
                return [self.to_native(item.pk) for item in queryset]

        # To-one relationship
        try:
            # Prefer obj.serializable_value for performance reasons
            pk = obj.serializable_value(self.source or field_name)
        except AttributeError:
            # RelatedObject (reverse relationship)
            try:
                pk = getattr(obj, self.source or field_name).pk
            except (ObjectDoesNotExist, AttributeError):
                return None

        # Forward relationship
        return self.to_native(pk)


### Slug relationships


class SlugRelatedField(RelatedField):
    """
    Represents a relationship using a unique field on the target.
    """
    read_only = False

    default_error_messages = {
        'does_not_exist': _("Object with %s=%s does not exist."),
        'invalid': _('Invalid value.'),
    }

    def __init__(self, *args, **kwargs):
        self.slug_field = kwargs.pop('slug_field', None)
        assert self.slug_field, 'slug_field is required'
        super(SlugRelatedField, self).__init__(*args, **kwargs)

    def to_native(self, obj):
        return getattr(obj, self.slug_field)

    def from_native(self, data):
        if self.queryset is None:
            raise Exception('Writable related fields must include a `queryset` argument')

        try:
            return self.queryset.get(**{self.slug_field: data})
        except ObjectDoesNotExist:
            raise ValidationError(self.error_messages['does_not_exist'] %
                                  (self.slug_field, smart_text(data)))
        except (TypeError, ValueError):
            msg = self.error_messages['invalid']
            raise ValidationError(msg)


### Hyperlinked relationships

class HyperlinkedRelatedField(RelatedField):
    """
    Represents a relationship using hyperlinking.
    """
    read_only = False
    lookup_field = 'pk'

    default_error_messages = {
        'no_match': _('Invalid hyperlink - No URL match'),
        'incorrect_match': _('Invalid hyperlink - Incorrect URL match'),
        'configuration_error': _('Invalid hyperlink due to configuration error'),
        'does_not_exist': _("Invalid hyperlink - object does not exist."),
        'incorrect_type': _('Incorrect type.  Expected url string, received %s.'),
    }

    # These are all pending deprecation
    pk_url_kwarg = 'pk'
    slug_field = 'slug'
    slug_url_kwarg = None  # Defaults to same as `slug_field` unless overridden

    def __init__(self, *args, **kwargs):
        try:
            self.view_name = kwargs.pop('view_name')
        except KeyError:
            raise ValueError("Hyperlinked field requires 'view_name' kwarg")

        self.lookup_field = kwargs.pop('lookup_field', self.lookup_field)
        self.format = kwargs.pop('format', None)

        # These are pending deprecation
        if 'pk_url_kwarg' in kwargs:
            msg = 'pk_url_kwarg is pending deprecation. Use lookup_field instead.'
            warnings.warn(msg, PendingDeprecationWarning, stacklevel=2)
        if 'slug_url_kwarg' in kwargs:
            msg = 'slug_url_kwarg is pending deprecation. Use lookup_field instead.'
            warnings.warn(msg, PendingDeprecationWarning, stacklevel=2)
        if 'slug_field' in kwargs:
            msg = 'slug_field is pending deprecation. Use lookup_field instead.'
            warnings.warn(msg, PendingDeprecationWarning, stacklevel=2)

        self.pk_url_kwarg = kwargs.pop('pk_url_kwarg', self.pk_url_kwarg)
        self.slug_field = kwargs.pop('slug_field', self.slug_field)
        default_slug_kwarg = self.slug_url_kwarg or self.slug_field
        self.slug_url_kwarg = kwargs.pop('slug_url_kwarg', default_slug_kwarg)

        super(HyperlinkedRelatedField, self).__init__(*args, **kwargs)

    def get_url(self, obj, view_name, request, format):
        """
        Given an object, return the URL that hyperlinks to the object.

        May raise a `NoReverseMatch` if the `view_name` and `lookup_field`
        attributes are not configured to correctly match the URL conf.
        """
        lookup_field = getattr(obj, self.lookup_field)
        kwargs = {self.lookup_field: lookup_field}
        try:
            return reverse(view_name, kwargs=kwargs, request=request, format=format)
        except NoReverseMatch:
            pass

        if self.pk_url_kwarg != 'pk':
            # Only try pk if it has been explicitly set.
            # Otherwise, the default `lookup_field = 'pk'` has us covered.
            pk = obj.pk
            kwargs = {self.pk_url_kwarg: pk}
            try:
                return reverse(view_name, kwargs=kwargs, request=request, format=format)
            except NoReverseMatch:
                pass

        slug = getattr(obj, self.slug_field, None)
        if slug is not None:
            # Only try slug if it corresponds to an attribute on the object.
            kwargs = {self.slug_url_kwarg: slug}
            try:
                ret = reverse(view_name, kwargs=kwargs, request=request, format=format)
                if self.slug_field == 'slug' and self.slug_url_kwarg == 'slug':
                    # If the lookup succeeds using the default slug params,
                    # then `slug_field` is being used implicitly, and we
                    # we need to warn about the pending deprecation.
                    msg = 'Implicit slug field hyperlinked fields are pending deprecation.' \
                          'You should set `lookup_field=slug` on the HyperlinkedRelatedField.'
                    warnings.warn(msg, PendingDeprecationWarning, stacklevel=2)
                return ret
            except NoReverseMatch:
                pass

        raise NoReverseMatch()

    def get_object(self, queryset, view_name, view_args, view_kwargs):
        """
        Return the object corresponding to a matched URL.

        Takes the matched URL conf arguments, and the queryset, and should
        return an object instance, or raise an `ObjectDoesNotExist` exception.
        """
        lookup = view_kwargs.get(self.lookup_field, None)
        pk = view_kwargs.get(self.pk_url_kwarg, None)
        slug = view_kwargs.get(self.slug_url_kwarg, None)

        if lookup is not None:
            filter_kwargs = {self.lookup_field: lookup}
        elif pk is not None:
            filter_kwargs = {'pk': pk}
        elif slug is not None:
            filter_kwargs = {self.slug_field: slug}
        else:
            raise ObjectDoesNotExist()

        return queryset.get(**filter_kwargs)

    def to_native(self, obj):
        view_name = self.view_name
        request = self.context.get('request', None)
        format = self.format or self.context.get('format', None)

        if request is None:
            msg = (
                "Using `HyperlinkedRelatedField` without including the request "
                "in the serializer context is deprecated. "
                "Add `context={'request': request}` when instantiating "
                "the serializer."
            )
            warnings.warn(msg, DeprecationWarning, stacklevel=4)

        # If the object has not yet been saved then we cannot hyperlink to it.
        if getattr(obj, 'pk', None) is None:
            return

        # Return the hyperlink, or error if incorrectly configured.
        try:
            return self.get_url(obj, view_name, request, format)
        except NoReverseMatch:
            msg = (
                'Could not resolve URL for hyperlinked relationship using '
                'view name "%s". You may have failed to include the related '
                'model in your API, or incorrectly configured the '
                '`lookup_field` attribute on this field.'
            )
            raise Exception(msg % view_name)

    def from_native(self, value):
        # Convert URL -> model instance pk
        # TODO: Use values_list
        queryset = self.queryset
        if queryset is None:
            raise Exception('Writable related fields must include a `queryset` argument')

        try:
            http_prefix = value.startswith(('http:', 'https:'))
        except AttributeError:
            msg = self.error_messages['incorrect_type']
            raise ValidationError(msg % type(value).__name__)

        if http_prefix:
            # If needed convert absolute URLs to relative path
            value = urlparse.urlparse(value).path
            prefix = get_script_prefix()
            if value.startswith(prefix):
                value = '/' + value[len(prefix):]

        try:
            match = resolve(value)
        except Exception:
            raise ValidationError(self.error_messages['no_match'])

        if match.view_name != self.view_name:
            raise ValidationError(self.error_messages['incorrect_match'])

        try:
            return self.get_object(queryset, match.view_name,
                                   match.args, match.kwargs)
        except (ObjectDoesNotExist, TypeError, ValueError):
            raise ValidationError(self.error_messages['does_not_exist'])


class HyperlinkedIdentityField(Field):
    """
    Represents the instance, or a property on the instance, using hyperlinking.
    """
    lookup_field = 'pk'
    read_only = True

    # These are all pending deprecation
    pk_url_kwarg = 'pk'
    slug_field = 'slug'
    slug_url_kwarg = None  # Defaults to same as `slug_field` unless overridden

    def __init__(self, *args, **kwargs):
        try:
            self.view_name = kwargs.pop('view_name')
        except KeyError:
            msg = "HyperlinkedIdentityField requires 'view_name' argument"
            raise ValueError(msg)

        self.format = kwargs.pop('format', None)
        lookup_field = kwargs.pop('lookup_field', None)
        self.lookup_field = lookup_field or self.lookup_field

        # These are pending deprecation
        if 'pk_url_kwarg' in kwargs:
            msg = 'pk_url_kwarg is pending deprecation. Use lookup_field instead.'
            warnings.warn(msg, PendingDeprecationWarning, stacklevel=2)
        if 'slug_url_kwarg' in kwargs:
            msg = 'slug_url_kwarg is pending deprecation. Use lookup_field instead.'
            warnings.warn(msg, PendingDeprecationWarning, stacklevel=2)
        if 'slug_field' in kwargs:
            msg = 'slug_field is pending deprecation. Use lookup_field instead.'
            warnings.warn(msg, PendingDeprecationWarning, stacklevel=2)

        self.slug_field = kwargs.pop('slug_field', self.slug_field)
        default_slug_kwarg = self.slug_url_kwarg or self.slug_field
        self.pk_url_kwarg = kwargs.pop('pk_url_kwarg', self.pk_url_kwarg)
        self.slug_url_kwarg = kwargs.pop('slug_url_kwarg', default_slug_kwarg)

        super(HyperlinkedIdentityField, self).__init__(*args, **kwargs)

    def field_to_native(self, obj, field_name):
        request = self.context.get('request', None)
        format = self.context.get('format', None)
        view_name = self.view_name

        if request is None:
            warnings.warn("Using `HyperlinkedIdentityField` without including the "
                          "request in the serializer context is deprecated. "
                          "Add `context={'request': request}` when instantiating the serializer.",
                          DeprecationWarning, stacklevel=4)

        # By default use whatever format is given for the current context
        # unless the target is a different type to the source.
        #
        # Eg. Consider a HyperlinkedIdentityField pointing from a json
        # representation to an html property of that representation...
        #
        # '/snippets/1/' should link to '/snippets/1/highlight/'
        # ...but...
        # '/snippets/1/.json' should link to '/snippets/1/highlight/.html'
        if format and self.format and self.format != format:
            format = self.format

        # Return the hyperlink, or error if incorrectly configured.
        try:
            return self.get_url(obj, view_name, request, format)
        except NoReverseMatch:
            msg = (
                'Could not resolve URL for hyperlinked relationship using '
                'view name "%s". You may have failed to include the related '
                'model in your API, or incorrectly configured the '
                '`lookup_field` attribute on this field.'
            )
            raise Exception(msg % view_name)

    def get_url(self, obj, view_name, request, format):
        """
        Given an object, return the URL that hyperlinks to the object.

        May raise a `NoReverseMatch` if the `view_name` and `lookup_field`
        attributes are not configured to correctly match the URL conf.
        """
        lookup_field = getattr(obj, self.lookup_field, None)
        kwargs = {self.lookup_field: lookup_field}

        # Handle unsaved object case
        if lookup_field is None:
            return None

        try:
            return reverse(view_name, kwargs=kwargs, request=request, format=format)
        except NoReverseMatch:
            pass

        if self.pk_url_kwarg != 'pk':
            # Only try pk lookup if it has been explicitly set.
            # Otherwise, the default `lookup_field = 'pk'` has us covered.
            kwargs = {self.pk_url_kwarg: obj.pk}
            try:
                return reverse(view_name, kwargs=kwargs, request=request, format=format)
            except NoReverseMatch:
                pass

        slug = getattr(obj, self.slug_field, None)
        if slug:
            # Only use slug lookup if a slug field exists on the model
            kwargs = {self.slug_url_kwarg: slug}
            try:
                return reverse(view_name, kwargs=kwargs, request=request, format=format)
            except NoReverseMatch:
                pass

        raise NoReverseMatch()


### Old-style many classes for backwards compat

class ManyRelatedField(RelatedField):
    def __init__(self, *args, **kwargs):
        warnings.warn('`ManyRelatedField()` is deprecated. '
                      'Use `RelatedField(many=True)` instead.',
                       DeprecationWarning, stacklevel=2)
        kwargs['many'] = True
        super(ManyRelatedField, self).__init__(*args, **kwargs)


class ManyPrimaryKeyRelatedField(PrimaryKeyRelatedField):
    def __init__(self, *args, **kwargs):
        warnings.warn('`ManyPrimaryKeyRelatedField()` is deprecated. '
                      'Use `PrimaryKeyRelatedField(many=True)` instead.',
                       DeprecationWarning, stacklevel=2)
        kwargs['many'] = True
        super(ManyPrimaryKeyRelatedField, self).__init__(*args, **kwargs)


class ManySlugRelatedField(SlugRelatedField):
    def __init__(self, *args, **kwargs):
        warnings.warn('`ManySlugRelatedField()` is deprecated. '
                      'Use `SlugRelatedField(many=True)` instead.',
                       DeprecationWarning, stacklevel=2)
        kwargs['many'] = True
        super(ManySlugRelatedField, self).__init__(*args, **kwargs)


class ManyHyperlinkedRelatedField(HyperlinkedRelatedField):
    def __init__(self, *args, **kwargs):
        warnings.warn('`ManyHyperlinkedRelatedField()` is deprecated. '
                      'Use `HyperlinkedRelatedField(many=True)` instead.',
                       DeprecationWarning, stacklevel=2)
        kwargs['many'] = True
        super(ManyHyperlinkedRelatedField, self).__init__(*args, **kwargs)

########NEW FILE########
__FILENAME__ = renderers
"""
Renderers are used to serialize a response into specific media types.

They give us a generic way of being able to handle various media types
on the response, such as JSON encoded data or HTML output.

REST framework also provides an HTML renderer the renders the browsable API.
"""
from __future__ import unicode_literals

import copy
import json
import django
from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.http.multipartparser import parse_header
from django.template import RequestContext, loader, Template
from django.test.client import encode_multipart
from django.utils.xmlutils import SimplerXMLGenerator
from rest_framework.compat import StringIO
from rest_framework.compat import six
from rest_framework.compat import smart_text
from rest_framework.compat import yaml
from rest_framework.exceptions import ParseError
from rest_framework.settings import api_settings
from rest_framework.request import is_form_media_type, override_method
from rest_framework.utils import encoders
from rest_framework.utils.breadcrumbs import get_breadcrumbs
from rest_framework import exceptions, status, VERSION


class BaseRenderer(object):
    """
    All renderers should extend this class, setting the `media_type`
    and `format` attributes, and override the `.render()` method.
    """

    media_type = None
    format = None
    charset = 'utf-8'
    render_style = 'text'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        raise NotImplemented('Renderer class requires .render() to be implemented')


class JSONRenderer(BaseRenderer):
    """
    Renderer which serializes to JSON.
    Applies JSON's backslash-u character escaping for non-ascii characters.
    """

    media_type = 'application/json'
    format = 'json'
    encoder_class = encoders.JSONEncoder
    ensure_ascii = True
    charset = None
    # JSON is a binary encoding, that can be encoded as utf-8, utf-16 or utf-32.
    # See: http://www.ietf.org/rfc/rfc4627.txt
    # Also: http://lucumr.pocoo.org/2013/7/19/application-mimetypes-and-encodings/

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Render `data` into JSON.
        """
        if data is None:
            return bytes()

        # If 'indent' is provided in the context, then pretty print the result.
        # E.g. If we're being called by the BrowsableAPIRenderer.
        renderer_context = renderer_context or {}
        indent = renderer_context.get('indent', None)

        if accepted_media_type:
            # If the media type looks like 'application/json; indent=4',
            # then pretty print the result.
            base_media_type, params = parse_header(accepted_media_type.encode('ascii'))
            indent = params.get('indent', indent)
            try:
                indent = max(min(int(indent), 8), 0)
            except (ValueError, TypeError):
                indent = None

        ret = json.dumps(data, cls=self.encoder_class,
            indent=indent, ensure_ascii=self.ensure_ascii)

        # On python 2.x json.dumps() returns bytestrings if ensure_ascii=True,
        # but if ensure_ascii=False, the return type is underspecified,
        # and may (or may not) be unicode.
        # On python 3.x json.dumps() returns unicode strings.
        if isinstance(ret, six.text_type):
            return bytes(ret.encode('utf-8'))
        return ret


class UnicodeJSONRenderer(JSONRenderer):
    ensure_ascii = False
    """
    Renderer which serializes to JSON.
    Does *not* apply JSON's character escaping for non-ascii characters.
    """


class JSONPRenderer(JSONRenderer):
    """
    Renderer which serializes to json,
    wrapping the json output in a callback function.
    """

    media_type = 'application/javascript'
    format = 'jsonp'
    callback_parameter = 'callback'
    default_callback = 'callback'
    charset = 'utf-8'

    def get_callback(self, renderer_context):
        """
        Determine the name of the callback to wrap around the json output.
        """
        request = renderer_context.get('request', None)
        params = request and request.QUERY_PARAMS or {}
        return params.get(self.callback_parameter, self.default_callback)

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Renders into jsonp, wrapping the json output in a callback function.

        Clients may set the callback function name using a query parameter
        on the URL, for example: ?callback=exampleCallbackName
        """
        renderer_context = renderer_context or {}
        callback = self.get_callback(renderer_context)
        json = super(JSONPRenderer, self).render(data, accepted_media_type,
                                                 renderer_context)
        return callback.encode(self.charset) + b'(' + json + b');'


class XMLRenderer(BaseRenderer):
    """
    Renderer which serializes to XML.
    """

    media_type = 'application/xml'
    format = 'xml'
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Renders `data` into serialized XML.
        """
        if data is None:
            return ''

        stream = StringIO()

        xml = SimplerXMLGenerator(stream, self.charset)
        xml.startDocument()
        xml.startElement("root", {})

        self._to_xml(xml, data)

        xml.endElement("root")
        xml.endDocument()
        return stream.getvalue()

    def _to_xml(self, xml, data):
        if isinstance(data, (list, tuple)):
            for item in data:
                xml.startElement("list-item", {})
                self._to_xml(xml, item)
                xml.endElement("list-item")

        elif isinstance(data, dict):
            for key, value in six.iteritems(data):
                xml.startElement(key, {})
                self._to_xml(xml, value)
                xml.endElement(key)

        elif data is None:
            # Don't output any value
            pass

        else:
            xml.characters(smart_text(data))


class YAMLRenderer(BaseRenderer):
    """
    Renderer which serializes to YAML.
    """

    media_type = 'application/yaml'
    format = 'yaml'
    encoder = encoders.SafeDumper
    charset = 'utf-8'
    ensure_ascii = True

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Renders `data` into serialized YAML.
        """
        assert yaml, 'YAMLRenderer requires pyyaml to be installed'

        if data is None:
            return ''

        return yaml.dump(data, stream=None, encoding=self.charset, Dumper=self.encoder, allow_unicode=not self.ensure_ascii)


class UnicodeYAMLRenderer(YAMLRenderer):
    """
    Renderer which serializes to YAML.
    Does *not* apply character escaping for non-ascii characters.
    """
    ensure_ascii = False


class TemplateHTMLRenderer(BaseRenderer):
    """
    An HTML renderer for use with templates.

    The data supplied to the Response object should be a dictionary that will
    be used as context for the template.

    The template name is determined by (in order of preference):

    1. An explicit `.template_name` attribute set on the response.
    2. An explicit `.template_name` attribute set on this class.
    3. The return result of calling `view.get_template_names()`.

    For example:
        data = {'users': User.objects.all()}
        return Response(data, template_name='users.html')

    For pre-rendered HTML, see StaticHTMLRenderer.
    """

    media_type = 'text/html'
    format = 'html'
    template_name = None
    exception_template_names = [
        '%(status_code)s.html',
        'api_exception.html'
    ]
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Renders data to HTML, using Django's standard template rendering.

        The template name is determined by (in order of preference):

        1. An explicit .template_name set on the response.
        2. An explicit .template_name set on this class.
        3. The return result of calling view.get_template_names().
        """
        renderer_context = renderer_context or {}
        view = renderer_context['view']
        request = renderer_context['request']
        response = renderer_context['response']

        if response.exception:
            template = self.get_exception_template(response)
        else:
            template_names = self.get_template_names(response, view)
            template = self.resolve_template(template_names)

        context = self.resolve_context(data, request, response)
        return template.render(context)

    def resolve_template(self, template_names):
        return loader.select_template(template_names)

    def resolve_context(self, data, request, response):
        if response.exception:
            data['status_code'] = response.status_code
        return RequestContext(request, data)

    def get_template_names(self, response, view):
        if response.template_name:
            return [response.template_name]
        elif self.template_name:
            return [self.template_name]
        elif hasattr(view, 'get_template_names'):
            return view.get_template_names()
        elif hasattr(view, 'template_name'):
            return [view.template_name]
        raise ImproperlyConfigured('Returned a template response with no `template_name` attribute set on either the view or response')

    def get_exception_template(self, response):
        template_names = [name % {'status_code': response.status_code}
                          for name in self.exception_template_names]

        try:
            # Try to find an appropriate error template
            return self.resolve_template(template_names)
        except Exception:
            # Fall back to using eg '404 Not Found'
            return Template('%d %s' % (response.status_code,
                                       response.status_text.title()))


# Note, subclass TemplateHTMLRenderer simply for the exception behavior
class StaticHTMLRenderer(TemplateHTMLRenderer):
    """
    An HTML renderer class that simply returns pre-rendered HTML.

    The data supplied to the Response object should be a string representing
    the pre-rendered HTML content.

    For example:
        data = '<html><body>example</body></html>'
        return Response(data)

    For template rendered HTML, see TemplateHTMLRenderer.
    """
    media_type = 'text/html'
    format = 'html'
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        renderer_context = renderer_context or {}
        response = renderer_context['response']

        if response and response.exception:
            request = renderer_context['request']
            template = self.get_exception_template(response)
            context = self.resolve_context(data, request, response)
            return template.render(context)

        return data


class HTMLFormRenderer(BaseRenderer):
    """
    Renderers serializer data into an HTML form.

    If the serializer was instantiated without an object then this will
    return an HTML form not bound to any object,
    otherwise it will return an HTML form with the appropriate initial data
    populated from the object.

    Note that rendering of field and form errors is not currently supported.
    """
    media_type = 'text/html'
    format = 'form'
    template = 'rest_framework/form.html'
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Render serializer data and return an HTML form, as a string.
        """
        renderer_context = renderer_context or {}
        request = renderer_context['request']

        template = loader.get_template(self.template)
        context = RequestContext(request, {'form': data})
        return template.render(context)


class BrowsableAPIRenderer(BaseRenderer):
    """
    HTML renderer used to self-document the API.
    """
    media_type = 'text/html'
    format = 'api'
    template = 'rest_framework/api.html'
    charset = 'utf-8'
    form_renderer_class = HTMLFormRenderer

    def get_default_renderer(self, view):
        """
        Return an instance of the first valid renderer.
        (Don't use another documenting renderer.)
        """
        renderers = [renderer for renderer in view.renderer_classes
                     if not issubclass(renderer, BrowsableAPIRenderer)]
        non_template_renderers = [renderer for renderer in renderers
                                  if not hasattr(renderer, 'get_template_names')]

        if not renderers:
            return None
        elif non_template_renderers:
            return non_template_renderers[0]()
        return renderers[0]()

    def get_content(self, renderer, data,
                    accepted_media_type, renderer_context):
        """
        Get the content as if it had been rendered by the default
        non-documenting renderer.
        """
        if not renderer:
            return '[No renderers were found]'

        renderer_context['indent'] = 4
        content = renderer.render(data, accepted_media_type, renderer_context)

        render_style = getattr(renderer, 'render_style', 'text')
        assert render_style in ['text', 'binary'], 'Expected .render_style ' \
            '"text" or "binary", but got "%s"' % render_style
        if render_style == 'binary':
            return '[%d bytes of binary content]' % len(content)

        return content

    def show_form_for_method(self, view, method, request, obj):
        """
        Returns True if a form should be shown for this method.
        """
        if not method in view.allowed_methods:
            return  # Not a valid method

        if not api_settings.FORM_METHOD_OVERRIDE:
            return  # Cannot use form overloading

        try:
            view.check_permissions(request)
            if obj is not None:
                view.check_object_permissions(request, obj)
        except exceptions.APIException:
            return False  # Doesn't have permissions
        return True

    def get_rendered_html_form(self, view, method, request):
        """
        Return a string representing a rendered HTML form, possibly bound to
        either the input or output data.

        In the absence of the View having an associated form then return None.
        """
        if request.method == method:
            try:
                data = request.DATA
                files = request.FILES
            except ParseError:
                data = None
                files = None
        else:
            data = None
            files = None

        with override_method(view, request, method) as request:
            obj = getattr(view, 'object', None)
            if not self.show_form_for_method(view, method, request, obj):
                return

            if method in ('DELETE', 'OPTIONS'):
                return True  # Don't actually need to return a form

            if (not getattr(view, 'get_serializer', None)
                or not any(is_form_media_type(parser.media_type) for parser in view.parser_classes)):
                return

            serializer = view.get_serializer(instance=obj, data=data, files=files)
            serializer.is_valid()
            data = serializer.data

            form_renderer = self.form_renderer_class()
            return form_renderer.render(data, self.accepted_media_type, self.renderer_context)

    def get_raw_data_form(self, view, method, request):
        """
        Returns a form that allows for arbitrary content types to be tunneled
        via standard HTML forms.
        (Which are typically application/x-www-form-urlencoded)
        """
        with override_method(view, request, method) as request:
            # If we're not using content overloading there's no point in
            # supplying a generic form, as the view won't treat the form's
            # value as the content of the request.
            if not (api_settings.FORM_CONTENT_OVERRIDE
                    and api_settings.FORM_CONTENTTYPE_OVERRIDE):
                return None

            # Check permissions
            obj = getattr(view, 'object', None)
            if not self.show_form_for_method(view, method, request, obj):
                return

            # If possible, serialize the initial content for the generic form
            default_parser = view.parser_classes[0]
            renderer_class = getattr(default_parser, 'renderer_class', None)
            if (hasattr(view, 'get_serializer') and renderer_class):
                # View has a serializer defined and parser class has a
                # corresponding renderer that can be used to render the data.

                # Get a read-only version of the serializer
                serializer = view.get_serializer(instance=obj)
                if obj is None:
                    for name, field in serializer.fields.items():
                        if getattr(field, 'read_only', None):
                            del serializer.fields[name]

                # Render the raw data content
                renderer = renderer_class()
                accepted = self.accepted_media_type
                context = self.renderer_context.copy()
                context['indent'] = 4
                content = renderer.render(serializer.data, accepted, context)
            else:
                content = None

            # Generate a generic form that includes a content type field,
            # and a content field.
            content_type_field = api_settings.FORM_CONTENTTYPE_OVERRIDE
            content_field = api_settings.FORM_CONTENT_OVERRIDE

            media_types = [parser.media_type for parser in view.parser_classes]
            choices = [(media_type, media_type) for media_type in media_types]
            initial = media_types[0]

            # NB. http://jacobian.org/writing/dynamic-form-generation/
            class GenericContentForm(forms.Form):
                def __init__(self):
                    super(GenericContentForm, self).__init__()

                    self.fields[content_type_field] = forms.ChoiceField(
                        label='Media type',
                        choices=choices,
                        initial=initial
                    )
                    self.fields[content_field] = forms.CharField(
                        label='Content',
                        widget=forms.Textarea,
                        initial=content
                    )

            return GenericContentForm()

    def get_name(self, view):
        return view.get_view_name()

    def get_description(self, view):
        return view.get_view_description(html=True)

    def get_breadcrumbs(self, request):
        return get_breadcrumbs(request.path)

    def get_context(self, data, accepted_media_type, renderer_context):
        """
        Returns the context used to render.
        """
        view = renderer_context['view']
        request = renderer_context['request']
        response = renderer_context['response']

        renderer = self.get_default_renderer(view)

        raw_data_post_form = self.get_raw_data_form(view, 'POST', request)
        raw_data_put_form = self.get_raw_data_form(view, 'PUT', request)
        raw_data_patch_form = self.get_raw_data_form(view, 'PATCH', request)
        raw_data_put_or_patch_form = raw_data_put_form or raw_data_patch_form

        response_headers = dict(response.items())
        renderer_content_type = ''
        if renderer:
            renderer_content_type = '%s' % renderer.media_type
            if renderer.charset:
                renderer_content_type += ' ;%s' % renderer.charset
        response_headers['Content-Type'] = renderer_content_type

        context = {
            'content': self.get_content(renderer, data, accepted_media_type, renderer_context),
            'view': view,
            'request': request,
            'response': response,
            'description': self.get_description(view),
            'name': self.get_name(view),
            'version': VERSION,
            'breadcrumblist': self.get_breadcrumbs(request),
            'allowed_methods': view.allowed_methods,
            'available_formats': [renderer.format for renderer in view.renderer_classes],
            'response_headers': response_headers,

            'put_form': self.get_rendered_html_form(view, 'PUT', request),
            'post_form': self.get_rendered_html_form(view, 'POST', request),
            'delete_form': self.get_rendered_html_form(view, 'DELETE', request),
            'options_form': self.get_rendered_html_form(view, 'OPTIONS', request),

            'raw_data_put_form': raw_data_put_form,
            'raw_data_post_form': raw_data_post_form,
            'raw_data_patch_form': raw_data_patch_form,
            'raw_data_put_or_patch_form': raw_data_put_or_patch_form,

            'display_edit_forms': bool(response.status_code != 403),

            'api_settings': api_settings
        }
        return context

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Render the HTML for the browsable API representation.
        """
        self.accepted_media_type = accepted_media_type or ''
        self.renderer_context = renderer_context or {}

        template = loader.get_template(self.template)
        context = self.get_context(data, accepted_media_type, renderer_context)
        context = RequestContext(renderer_context['request'], context)
        ret = template.render(context)

        # Munge DELETE Response code to allow us to return content
        # (Do this *after* we've rendered the template so that we include
        # the normal deletion response code in the output)
        response = renderer_context['response']
        if response.status_code == status.HTTP_204_NO_CONTENT:
            response.status_code = status.HTTP_200_OK

        return ret


class MultiPartRenderer(BaseRenderer):
    media_type = 'multipart/form-data; boundary=BoUnDaRyStRiNg'
    format = 'multipart'
    charset = 'utf-8'
    BOUNDARY = 'BoUnDaRyStRiNg' if django.VERSION >= (1, 5) else b'BoUnDaRyStRiNg'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return encode_multipart(self.BOUNDARY, data)


########NEW FILE########
__FILENAME__ = request
"""
The Request class is used as a wrapper around the standard request object.

The wrapped request then offers a richer API, in particular :

    - content automatically parsed according to `Content-Type` header,
      and available as `request.DATA`
    - full support of PUT method, including support for file uploads
    - form overloading of HTTP method, content type and content
"""
from __future__ import unicode_literals
from django.conf import settings
from django.http import QueryDict
from django.http.multipartparser import parse_header
from django.utils.datastructures import MultiValueDict
from rest_framework import HTTP_HEADER_ENCODING
from rest_framework import exceptions
from rest_framework.compat import BytesIO
from rest_framework.settings import api_settings


def is_form_media_type(media_type):
    """
    Return True if the media type is a valid form media type.
    """
    base_media_type, params = parse_header(media_type.encode(HTTP_HEADER_ENCODING))
    return (base_media_type == 'application/x-www-form-urlencoded' or
            base_media_type == 'multipart/form-data')


class override_method(object):
    """
    A context manager that temporarily overrides the method on a request,
    additionally setting the `view.request` attribute.

    Usage:

        with override_method(view, request, 'POST') as request:
            ... # Do stuff with `view` and `request`
    """
    def __init__(self, view, request, method):
        self.view = view
        self.request = request
        self.method = method

    def __enter__(self):
        self.view.request = clone_request(self.request, self.method)
        return self.view.request

    def __exit__(self, *args, **kwarg):
        self.view.request = self.request


class Empty(object):
    """
    Placeholder for unset attributes.
    Cannot use `None`, as that may be a valid value.
    """
    pass


def _hasattr(obj, name):
    return not getattr(obj, name) is Empty


def clone_request(request, method):
    """
    Internal helper method to clone a request, replacing with a different
    HTTP method.  Used for checking permissions against other methods.
    """
    ret = Request(request=request._request,
                  parsers=request.parsers,
                  authenticators=request.authenticators,
                  negotiator=request.negotiator,
                  parser_context=request.parser_context)
    ret._data = request._data
    ret._files = request._files
    ret._content_type = request._content_type
    ret._stream = request._stream
    ret._method = method
    if hasattr(request, '_user'):
        ret._user = request._user
    if hasattr(request, '_auth'):
        ret._auth = request._auth
    if hasattr(request, '_authenticator'):
        ret._authenticator = request._authenticator
    return ret


class ForcedAuthentication(object):
    """
    This authentication class is used if the test client or request factory
    forcibly authenticated the request.
    """

    def __init__(self, force_user, force_token):
        self.force_user = force_user
        self.force_token = force_token

    def authenticate(self, request):
        return (self.force_user, self.force_token)


class Request(object):
    """
    Wrapper allowing to enhance a standard `HttpRequest` instance.

    Kwargs:
        - request(HttpRequest). The original request instance.
        - parsers_classes(list/tuple). The parsers to use for parsing the
          request content.
        - authentication_classes(list/tuple). The authentications used to try
          authenticating the request's user.
    """

    _METHOD_PARAM = api_settings.FORM_METHOD_OVERRIDE
    _CONTENT_PARAM = api_settings.FORM_CONTENT_OVERRIDE
    _CONTENTTYPE_PARAM = api_settings.FORM_CONTENTTYPE_OVERRIDE

    def __init__(self, request, parsers=None, authenticators=None,
                 negotiator=None, parser_context=None):
        self._request = request
        self.parsers = parsers or ()
        self.authenticators = authenticators or ()
        self.negotiator = negotiator or self._default_negotiator()
        self.parser_context = parser_context
        self._data = Empty
        self._files = Empty
        self._method = Empty
        self._content_type = Empty
        self._stream = Empty

        if self.parser_context is None:
            self.parser_context = {}
        self.parser_context['request'] = self
        self.parser_context['encoding'] = request.encoding or settings.DEFAULT_CHARSET

        force_user = getattr(request, '_force_auth_user', None)
        force_token = getattr(request, '_force_auth_token', None)
        if (force_user is not None or force_token is not None):
            forced_auth = ForcedAuthentication(force_user, force_token)
            self.authenticators = (forced_auth,)

    def _default_negotiator(self):
        return api_settings.DEFAULT_CONTENT_NEGOTIATION_CLASS()

    @property
    def method(self):
        """
        Returns the HTTP method.

        This allows the `method` to be overridden by using a hidden `form`
        field on a form POST request.
        """
        if not _hasattr(self, '_method'):
            self._load_method_and_content_type()
        return self._method

    @property
    def content_type(self):
        """
        Returns the content type header.

        This should be used instead of `request.META.get('HTTP_CONTENT_TYPE')`,
        as it allows the content type to be overridden by using a hidden form
        field on a form POST request.
        """
        if not _hasattr(self, '_content_type'):
            self._load_method_and_content_type()
        return self._content_type

    @property
    def stream(self):
        """
        Returns an object that may be used to stream the request content.
        """
        if not _hasattr(self, '_stream'):
            self._load_stream()
        return self._stream

    @property
    def QUERY_PARAMS(self):
        """
        More semantically correct name for request.GET.
        """
        return self._request.GET

    @property
    def DATA(self):
        """
        Parses the request body and returns the data.

        Similar to usual behaviour of `request.POST`, except that it handles
        arbitrary parsers, and also works on methods other than POST (eg PUT).
        """
        if not _hasattr(self, '_data'):
            self._load_data_and_files()
        return self._data

    @property
    def FILES(self):
        """
        Parses the request body and returns any files uploaded in the request.

        Similar to usual behaviour of `request.FILES`, except that it handles
        arbitrary parsers, and also works on methods other than POST (eg PUT).
        """
        if not _hasattr(self, '_files'):
            self._load_data_and_files()
        return self._files

    @property
    def user(self):
        """
        Returns the user associated with the current request, as authenticated
        by the authentication classes provided to the request.
        """
        if not hasattr(self, '_user'):
            self._authenticate()
        return self._user

    @user.setter
    def user(self, value):
        """
        Sets the user on the current request. This is necessary to maintain
        compatibility with django.contrib.auth where the user property is
        set in the login and logout functions.
        """
        self._user = value

    @property
    def auth(self):
        """
        Returns any non-user authentication information associated with the
        request, such as an authentication token.
        """
        if not hasattr(self, '_auth'):
            self._authenticate()
        return self._auth

    @auth.setter
    def auth(self, value):
        """
        Sets any non-user authentication information associated with the
        request, such as an authentication token.
        """
        self._auth = value

    @property
    def successful_authenticator(self):
        """
        Return the instance of the authentication instance class that was used
        to authenticate the request, or `None`.
        """
        if not hasattr(self, '_authenticator'):
            self._authenticate()
        return self._authenticator

    def _load_data_and_files(self):
        """
        Parses the request content into self.DATA and self.FILES.
        """
        if not _hasattr(self, '_content_type'):
            self._load_method_and_content_type()

        if not _hasattr(self, '_data'):
            self._data, self._files = self._parse()

    def _load_method_and_content_type(self):
        """
        Sets the method and content_type, and then check if they've
        been overridden.
        """
        self._content_type = self.META.get('HTTP_CONTENT_TYPE',
                                           self.META.get('CONTENT_TYPE', ''))

        self._perform_form_overloading()

        if not _hasattr(self, '_method'):
            self._method = self._request.method

            # Allow X-HTTP-METHOD-OVERRIDE header
            self._method = self.META.get('HTTP_X_HTTP_METHOD_OVERRIDE',
                                         self._method)

    def _load_stream(self):
        """
        Return the content body of the request, as a stream.
        """
        try:
            content_length = int(self.META.get('CONTENT_LENGTH',
                                    self.META.get('HTTP_CONTENT_LENGTH')))
        except (ValueError, TypeError):
            content_length = 0

        if content_length == 0:
            self._stream = None
        elif hasattr(self._request, 'read'):
            self._stream = self._request
        else:
            self._stream = BytesIO(self.raw_post_data)

    def _perform_form_overloading(self):
        """
        If this is a form POST request, then we need to check if the method and
        content/content_type have been overridden by setting them in hidden
        form fields or not.
        """

        USE_FORM_OVERLOADING = (
            self._METHOD_PARAM or
            (self._CONTENT_PARAM and self._CONTENTTYPE_PARAM)
        )

        # We only need to use form overloading on form POST requests.
        if (not USE_FORM_OVERLOADING
            or self._request.method != 'POST'
            or not is_form_media_type(self._content_type)):
            return

        # At this point we're committed to parsing the request as form data.
        self._data = self._request.POST
        self._files = self._request.FILES

        # Method overloading - change the method and remove the param from the content.
        if (self._METHOD_PARAM and
            self._METHOD_PARAM in self._data):
            self._method = self._data[self._METHOD_PARAM].upper()

        # Content overloading - modify the content type, and force re-parse.
        if (self._CONTENT_PARAM and
            self._CONTENTTYPE_PARAM and
            self._CONTENT_PARAM in self._data and
            self._CONTENTTYPE_PARAM in self._data):
            self._content_type = self._data[self._CONTENTTYPE_PARAM]
            self._stream = BytesIO(self._data[self._CONTENT_PARAM].encode(self.parser_context['encoding']))
            self._data, self._files = (Empty, Empty)

    def _parse(self):
        """
        Parse the request content, returning a two-tuple of (data, files)

        May raise an `UnsupportedMediaType`, or `ParseError` exception.
        """
        stream = self.stream
        media_type = self.content_type

        if stream is None or media_type is None:
            empty_data = QueryDict('', encoding=self._request._encoding)
            empty_files = MultiValueDict()
            return (empty_data, empty_files)

        parser = self.negotiator.select_parser(self, self.parsers)

        if not parser:
            raise exceptions.UnsupportedMediaType(media_type)

        try:
            parsed = parser.parse(stream, media_type, self.parser_context)
        except:
            # If we get an exception during parsing, fill in empty data and
            # re-raise.  Ensures we don't simply repeat the error when
            # attempting to render the browsable renderer response, or when
            # logging the request or similar.
            self._data = QueryDict('', encoding=self._request._encoding)
            self._files = MultiValueDict()
            raise

        # Parser classes may return the raw data, or a
        # DataAndFiles object.  Unpack the result as required.
        try:
            return (parsed.data, parsed.files)
        except AttributeError:
            empty_files = MultiValueDict()
            return (parsed, empty_files)

    def _authenticate(self):
        """
        Attempt to authenticate the request using each authentication instance
        in turn.
        Returns a three-tuple of (authenticator, user, authtoken).
        """
        for authenticator in self.authenticators:
            try:
                user_auth_tuple = authenticator.authenticate(self)
            except exceptions.APIException:
                self._not_authenticated()
                raise

            if not user_auth_tuple is None:
                self._authenticator = authenticator
                self._user, self._auth = user_auth_tuple
                return

        self._not_authenticated()

    def _not_authenticated(self):
        """
        Return a three-tuple of (authenticator, user, authtoken), representing
        an unauthenticated request.

        By default this will be (None, AnonymousUser, None).
        """
        self._authenticator = None

        if api_settings.UNAUTHENTICATED_USER:
            self._user = api_settings.UNAUTHENTICATED_USER()
        else:
            self._user = None

        if api_settings.UNAUTHENTICATED_TOKEN:
            self._auth = api_settings.UNAUTHENTICATED_TOKEN()
        else:
            self._auth = None

    def __getattr__(self, attr):
        """
        Proxy other attributes to the underlying HttpRequest object.
        """
        return getattr(self._request, attr)

########NEW FILE########
__FILENAME__ = response
"""
The Response class in REST framework is similar to HTTPResponse, except that
it is initialized with unrendered data, instead of a pre-rendered string.

The appropriate renderer is called during Django's template response rendering.
"""
from __future__ import unicode_literals
from django.core.handlers.wsgi import STATUS_CODE_TEXT
from django.template.response import SimpleTemplateResponse
from rest_framework.compat import six


class Response(SimpleTemplateResponse):
    """
    An HttpResponse that allows its data to be rendered into
    arbitrary media types.
    """

    def __init__(self, data=None, status=200,
                 template_name=None, headers=None,
                 exception=False, content_type=None):
        """
        Alters the init arguments slightly.
        For example, drop 'template_name', and instead use 'data'.

        Setting 'renderer' and 'media_type' will typically be deferred,
        For example being set automatically by the `APIView`.
        """
        super(Response, self).__init__(None, status=status)
        self.data = data
        self.template_name = template_name
        self.exception = exception
        self.content_type = content_type

        if headers:
            for name, value in six.iteritems(headers):
                self[name] = value

    @property
    def rendered_content(self):
        renderer = getattr(self, 'accepted_renderer', None)
        media_type = getattr(self, 'accepted_media_type', None)
        context = getattr(self, 'renderer_context', None)

        assert renderer, ".accepted_renderer not set on Response"
        assert media_type, ".accepted_media_type not set on Response"
        assert context, ".renderer_context not set on Response"
        context['response'] = self

        charset = renderer.charset
        content_type = self.content_type

        if content_type is None and charset is not None:
            content_type = "{0}; charset={1}".format(media_type, charset)
        elif content_type is None:
            content_type = media_type
        self['Content-Type'] = content_type

        ret = renderer.render(self.data, media_type, context)
        if isinstance(ret, six.text_type):
            assert charset, 'renderer returned unicode, and did not specify ' \
            'a charset value.'
            return bytes(ret.encode(charset))

        if not ret:
            del self['Content-Type']

        return ret

    @property
    def status_text(self):
        """
        Returns reason text corresponding to our HTTP response status code.
        Provided for convenience.
        """
        # TODO: Deprecate and use a template tag instead
        # TODO: Status code text for RFC 6585 status codes
        return STATUS_CODE_TEXT.get(self.status_code, '')

    def __getstate__(self):
        """
        Remove attributes from the response that shouldn't be cached
        """
        state = super(Response, self).__getstate__()
        for key in ('accepted_renderer', 'renderer_context', 'data'):
            if key in state:
                del state[key]
        return state

########NEW FILE########
__FILENAME__ = reverse
"""
Provide reverse functions that return fully qualified URLs
"""
from __future__ import unicode_literals
from django.core.urlresolvers import reverse as django_reverse
from django.utils.functional import lazy


def reverse(viewname, args=None, kwargs=None, request=None, format=None, **extra):
    """
    Same as `django.core.urlresolvers.reverse`, but optionally takes a request
    and returns a fully qualified URL, using the request to get the base URL.
    """
    if format is not None:
        kwargs = kwargs or {}
        kwargs['format'] = format
    url = django_reverse(viewname, args=args, kwargs=kwargs, **extra)
    if request:
        return request.build_absolute_uri(url)
    return url


reverse_lazy = lazy(reverse, str)

########NEW FILE########
__FILENAME__ = routers
"""
Routers provide a convenient and consistent way of automatically
determining the URL conf for your API.

They are used by simply instantiating a Router class, and then registering
all the required ViewSets with that router.

For example, you might have a `urls.py` that looks something like this:

    router = routers.DefaultRouter()
    router.register('users', UserViewSet, 'user')
    router.register('accounts', AccountViewSet, 'account')

    urlpatterns = router.urls
"""
from __future__ import unicode_literals

import itertools
from collections import namedtuple
from django.core.exceptions import ImproperlyConfigured
from rest_framework import views
from rest_framework.compat import patterns, url
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.urlpatterns import format_suffix_patterns


Route = namedtuple('Route', ['url', 'mapping', 'name', 'initkwargs'])


def replace_methodname(format_string, methodname):
    """
    Partially format a format_string, swapping out any
    '{methodname}' or '{methodnamehyphen}' components.
    """
    methodnamehyphen = methodname.replace('_', '-')
    ret = format_string
    ret = ret.replace('{methodname}', methodname)
    ret = ret.replace('{methodnamehyphen}', methodnamehyphen)
    return ret


def flatten(list_of_lists):
    """
    Takes an iterable of iterables, returns a single iterable containing all items
    """
    return itertools.chain(*list_of_lists)


class BaseRouter(object):
    def __init__(self):
        self.registry = []

    def register(self, prefix, viewset, base_name=None):
        if base_name is None:
            base_name = self.get_default_base_name(viewset)
        self.registry.append((prefix, viewset, base_name))

    def get_default_base_name(self, viewset):
        """
        If `base_name` is not specified, attempt to automatically determine
        it from the viewset.
        """
        raise NotImplemented('get_default_base_name must be overridden')

    def get_urls(self):
        """
        Return a list of URL patterns, given the registered viewsets.
        """
        raise NotImplemented('get_urls must be overridden')

    @property
    def urls(self):
        if not hasattr(self, '_urls'):
            self._urls = patterns('', *self.get_urls())
        return self._urls


class SimpleRouter(BaseRouter):
    routes = [
        # List route.
        Route(
            url=r'^{prefix}{trailing_slash}$',
            mapping={
                'get': 'list',
                'post': 'create'
            },
            name='{basename}-list',
            initkwargs={'suffix': 'List'}
        ),
        # Detail route.
        Route(
            url=r'^{prefix}/{lookup}{trailing_slash}$',
            mapping={
                'get': 'retrieve',
                'put': 'update',
                'patch': 'partial_update',
                'delete': 'destroy'
            },
            name='{basename}-detail',
            initkwargs={'suffix': 'Instance'}
        ),
        # Dynamically generated routes.
        # Generated using @action or @link decorators on methods of the viewset.
        Route(
            url=r'^{prefix}/{lookup}/{methodname}{trailing_slash}$',
            mapping={
                '{httpmethod}': '{methodname}',
            },
            name='{basename}-{methodnamehyphen}',
            initkwargs={}
        ),
    ]

    def __init__(self, trailing_slash=True):
        self.trailing_slash = trailing_slash and '/' or ''
        super(SimpleRouter, self).__init__()

    def get_default_base_name(self, viewset):
        """
        If `base_name` is not specified, attempt to automatically determine
        it from the viewset.
        """
        model_cls = getattr(viewset, 'model', None)
        queryset = getattr(viewset, 'queryset', None)
        if model_cls is None and queryset is not None:
            model_cls = queryset.model

        assert model_cls, '`base_name` argument not specified, and could ' \
            'not automatically determine the name from the viewset, as ' \
            'it does not have a `.model` or `.queryset` attribute.'

        return model_cls._meta.object_name.lower()

    def get_routes(self, viewset):
        """
        Augment `self.routes` with any dynamically generated routes.

        Returns a list of the Route namedtuple.
        """

        known_actions = flatten([route.mapping.values() for route in self.routes])

        # Determine any `@action` or `@link` decorated methods on the viewset
        dynamic_routes = []
        for methodname in dir(viewset):
            attr = getattr(viewset, methodname)
            httpmethods = getattr(attr, 'bind_to_methods', None)
            if httpmethods:
                if methodname in known_actions:
                    raise ImproperlyConfigured('Cannot use @action or @link decorator on '
                                               'method "%s" as it is an existing route' % methodname)
                httpmethods = [method.lower() for method in httpmethods]
                dynamic_routes.append((httpmethods, methodname))

        ret = []
        for route in self.routes:
            if route.mapping == {'{httpmethod}': '{methodname}'}:
                # Dynamic routes (@link or @action decorator)
                for httpmethods, methodname in dynamic_routes:
                    initkwargs = route.initkwargs.copy()
                    initkwargs.update(getattr(viewset, methodname).kwargs)
                    ret.append(Route(
                        url=replace_methodname(route.url, methodname),
                        mapping=dict((httpmethod, methodname) for httpmethod in httpmethods),
                        name=replace_methodname(route.name, methodname),
                        initkwargs=initkwargs,
                    ))
            else:
                # Standard route
                ret.append(route)

        return ret

    def get_method_map(self, viewset, method_map):
        """
        Given a viewset, and a mapping of http methods to actions,
        return a new mapping which only includes any mappings that
        are actually implemented by the viewset.
        """
        bound_methods = {}
        for method, action in method_map.items():
            if hasattr(viewset, action):
                bound_methods[method] = action
        return bound_methods

    def get_lookup_regex(self, viewset, lookup_prefix=''):
        """
        Given a viewset, return the portion of URL regex that is used
        to match against a single instance.

        Note that lookup_prefix is not used directly inside REST rest_framework
        itself, but is required in order to nicely support nested router
        implementations, such as drf-nested-routers.

        https://github.com/alanjds/drf-nested-routers
        """
        if self.trailing_slash:
            base_regex = '(?P<{lookup_prefix}{lookup_field}>[^/]+)'
        else:
            # Don't consume `.json` style suffixes
            base_regex = '(?P<{lookup_prefix}{lookup_field}>[^/.]+)'
        lookup_field = getattr(viewset, 'lookup_field', 'pk')
        return base_regex.format(lookup_field=lookup_field, lookup_prefix=lookup_prefix)

    def get_urls(self):
        """
        Use the registered viewsets to generate a list of URL patterns.
        """
        ret = []

        for prefix, viewset, basename in self.registry:
            lookup = self.get_lookup_regex(viewset)
            routes = self.get_routes(viewset)

            for route in routes:

                # Only actions which actually exist on the viewset will be bound
                mapping = self.get_method_map(viewset, route.mapping)
                if not mapping:
                    continue

                # Build the url pattern
                regex = route.url.format(
                    prefix=prefix,
                    lookup=lookup,
                    trailing_slash=self.trailing_slash
                )
                view = viewset.as_view(mapping, **route.initkwargs)
                name = route.name.format(basename=basename)
                ret.append(url(regex, view, name=name))

        return ret


class DefaultRouter(SimpleRouter):
    """
    The default router extends the SimpleRouter, but also adds in a default
    API root view, and adds format suffix patterns to the URLs.
    """
    include_root_view = True
    include_format_suffixes = True
    root_view_name = 'api-root'

    def get_api_root_view(self):
        """
        Return a view to use as the API root.
        """
        api_root_dict = {}
        list_name = self.routes[0].name
        for prefix, viewset, basename in self.registry:
            api_root_dict[prefix] = list_name.format(basename=basename)

        class APIRoot(views.APIView):
            _ignore_model_permissions = True

            def get(self, request, format=None):
                ret = {}
                for key, url_name in api_root_dict.items():
                    ret[key] = reverse(url_name, request=request, format=format)
                return Response(ret)

        return APIRoot.as_view()

    def get_urls(self):
        """
        Generate the list of URL patterns, including a default root view
        for the API, and appending `.json` style format suffixes.
        """
        urls = []

        if self.include_root_view:
            root_url = url(r'^$', self.get_api_root_view(), name=self.root_view_name)
            urls.append(root_url)

        default_urls = super(DefaultRouter, self).get_urls()
        urls.extend(default_urls)

        if self.include_format_suffixes:
            urls = format_suffix_patterns(urls)

        return urls

########NEW FILE########
__FILENAME__ = runcoverage
#!/usr/bin/env python
"""
Useful tool to run the test suite for rest_framework and generate a coverage report.
"""

# http://ericholscher.com/blog/2009/jun/29/enable-setuppy-test-your-django-apps/
# http://www.travisswicegood.com/2010/01/17/django-virtualenv-pip-and-fabric/
# http://code.djangoproject.com/svn/django/trunk/tests/runtests.py
import os
import sys

# fix sys path so we don't need to setup PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
os.environ['DJANGO_SETTINGS_MODULE'] = 'rest_framework.runtests.settings'

from coverage import coverage


def main():
    """Run the tests for rest_framework and generate a coverage report."""

    cov = coverage()
    cov.erase()
    cov.start()

    from django.conf import settings
    from django.test.utils import get_runner
    TestRunner = get_runner(settings)

    if hasattr(TestRunner, 'func_name'):
        # Pre 1.2 test runners were just functions,
        # and did not support the 'failfast' option.
        import warnings
        warnings.warn(
            'Function-based test runners are deprecated. Test runners should be classes with a run_tests() method.',
            DeprecationWarning
        )
        failures = TestRunner(['tests'])
    else:
        test_runner = TestRunner()
        failures = test_runner.run_tests(['tests'])
    cov.stop()

    # Discover the list of all modules that we should test coverage for
    import rest_framework

    project_dir = os.path.dirname(rest_framework.__file__)
    cov_files = []

    for (path, dirs, files) in os.walk(project_dir):
        # Drop tests and runtests directories from the test coverage report
        if os.path.basename(path) in ['tests', 'runtests', 'migrations']:
            continue

        # Drop the compat and six modules from coverage, since we're not interested in the coverage
        # of modules which are specifically for resolving environment dependant imports.
        # (Because we'll end up getting different coverage reports for it for each environment)
        if 'compat.py' in files:
            files.remove('compat.py')

        if 'six.py' in files:
            files.remove('six.py')

        # Same applies to template tags module.
        # This module has to include branching on Django versions,
        # so it's never possible for it to have full coverage.
        if 'rest_framework.py' in files:
            files.remove('rest_framework.py')

        cov_files.extend([os.path.join(path, file) for file in files if file.endswith('.py')])

    cov.report(cov_files)
    if '--html' in sys.argv:
        cov.html_report(cov_files, directory='coverage')
    sys.exit(failures)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python

# http://ericholscher.com/blog/2009/jun/29/enable-setuppy-test-your-django-apps/
# http://www.travisswicegood.com/2010/01/17/django-virtualenv-pip-and-fabric/
# http://code.djangoproject.com/svn/django/trunk/tests/runtests.py
import os
import sys

# fix sys path so we don't need to setup PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
os.environ['DJANGO_SETTINGS_MODULE'] = 'rest_framework.runtests.settings'

import django
from django.conf import settings
from django.test.utils import get_runner


def usage():
    return """
    Usage: python runtests.py [UnitTestClass].[method]

    You can pass the Class name of the `UnitTestClass` you want to test.

    Append a method name if you only want to test a specific method of that class.
    """


def main():
    try:
        django.setup()
    except AttributeError:
        pass
    TestRunner = get_runner(settings)

    test_runner = TestRunner()
    if len(sys.argv) == 2:
        test_case = '.' + sys.argv[1]
    elif len(sys.argv) == 1:
        test_case = ''
    else:
        print(usage())
        sys.exit(1)
    test_module_name = 'rest_framework.tests'
    if django.VERSION[0] == 1 and django.VERSION[1] < 6:
        test_module_name = 'tests'

    failures = test_runner.run_tests([test_module_name + test_case])

    sys.exit(failures)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = settings
# Django settings for testproject project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG
DEBUG_PROPAGATE_EXCEPTIONS = True

ALLOWED_HOSTS = ['*']

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'sqlite.db',                     # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/London'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-uk'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'u@x-aj9(hoh#rb-^ymf#g2jx_hp0vj7u5#b@ag1n^seu9e!%cy'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework.tests',
    'rest_framework.tests.accounts',
    'rest_framework.tests.records',
    'rest_framework.tests.users',
)

# OAuth is optional and won't work if there is no oauth_provider & oauth2
try:
    import oauth_provider
    import oauth2
except ImportError:
    pass
else:
    INSTALLED_APPS += (
        'oauth_provider',
    )

try:
    import provider
except ImportError:
    pass
else:
    INSTALLED_APPS += (
        'provider',
        'provider.oauth2',
    )

# guardian is optional
try:
    import guardian
except ImportError:
    pass
else:
    ANONYMOUS_USER_ID = -1
    AUTHENTICATION_BACKENDS = (
        'django.contrib.auth.backends.ModelBackend', # default
        'guardian.backends.ObjectPermissionBackend',
    )
    INSTALLED_APPS += (
        'guardian',
    )

STATIC_URL = '/static/'

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.SHA1PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptPasswordHasher',
    'django.contrib.auth.hashers.MD5PasswordHasher',
    'django.contrib.auth.hashers.CryptPasswordHasher',
)

AUTH_USER_MODEL = 'auth.User'

import django

if django.VERSION < (1, 3):
    INSTALLED_APPS += ('staticfiles',)


# If we're running on the Jenkins server we want to archive the coverage reports as XML.
import os
if os.environ.get('HUDSON_URL', None):
    TEST_RUNNER = 'xmlrunner.extra.djangotestrunner.XMLTestRunner'
    TEST_OUTPUT_VERBOSE = True
    TEST_OUTPUT_DESCRIPTIONS = True
    TEST_OUTPUT_DIR = 'xmlrunner'

########NEW FILE########
__FILENAME__ = urls
"""
Blank URLConf just to keep runtests.py happy.
"""
from rest_framework.compat import patterns

urlpatterns = patterns('',
)

########NEW FILE########
__FILENAME__ = serializers
"""
Serializers and ModelSerializers are similar to Forms and ModelForms.
Unlike forms, they are not constrained to dealing with HTML output, and
form encoded input.

Serialization in REST framework is a two-phase process:

1. Serializers marshal between complex types like model instances, and
python primitives.
2. The process of marshalling between python primitives and request and
response content is handled by parsers and renderers.
"""
from __future__ import unicode_literals
import copy
import datetime
import inspect
import types
from decimal import Decimal
from django.contrib.contenttypes.generic import GenericForeignKey
from django.core.paginator import Page
from django.db import models
from django.forms import widgets
from django.utils.datastructures import SortedDict
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.compat import get_concrete_model, six
from rest_framework.settings import api_settings


# Note: We do the following so that users of the framework can use this style:
#
#     example_field = serializers.CharField(...)
#
# This helps keep the separation between model fields, form fields, and
# serializer fields more explicit.

from rest_framework.relations import *  # NOQA
from rest_framework.fields import *  # NOQA


def _resolve_model(obj):
    """
    Resolve supplied `obj` to a Django model class.

    `obj` must be a Django model class itself, or a string
    representation of one.  Useful in situtations like GH #1225 where
    Django may not have resolved a string-based reference to a model in
    another model's foreign key definition.

    String representations should have the format:
        'appname.ModelName'
    """
    if isinstance(obj, six.string_types) and len(obj.split('.')) == 2:
        app_name, model_name = obj.split('.')
        return models.get_model(app_name, model_name)
    elif inspect.isclass(obj) and issubclass(obj, models.Model):
        return obj
    else:
        raise ValueError("{0} is not a Django model".format(obj))


def pretty_name(name):
    """Converts 'first_name' to 'First name'"""
    if not name:
        return ''
    return name.replace('_', ' ').capitalize()


class RelationsList(list):
    _deleted = []


class NestedValidationError(ValidationError):
    """
    The default ValidationError behavior is to stringify each item in the list
    if the messages are a list of error messages.

    In the case of nested serializers, where the parent has many children,
    then the child's `serializer.errors` will be a list of dicts.  In the case
    of a single child, the `serializer.errors` will be a dict.

    We need to override the default behavior to get properly nested error dicts.
    """

    def __init__(self, message):
        if isinstance(message, dict):
            self._messages = [message]
        else:
            self._messages = message

    @property
    def messages(self):
        return self._messages


class DictWithMetadata(dict):
    """
    A dict-like object, that can have additional properties attached.
    """
    def __getstate__(self):
        """
        Used by pickle (e.g., caching).
        Overridden to remove the metadata from the dict, since it shouldn't be
        pickled and may in some instances be unpickleable.
        """
        return dict(self)


class SortedDictWithMetadata(SortedDict):
    """
    A sorted dict-like object, that can have additional properties attached.
    """
    def __getstate__(self):
        """
        Used by pickle (e.g., caching).
        Overriden to remove the metadata from the dict, since it shouldn't be
        pickle and may in some instances be unpickleable.
        """
        return SortedDict(self).__dict__


def _is_protected_type(obj):
    """
    True if the object is a native datatype that does not need to
    be serialized further.
    """
    return isinstance(obj, (
        types.NoneType,
        int, long,
        datetime.datetime, datetime.date, datetime.time,
        float, Decimal,
        basestring)
    )


def _get_declared_fields(bases, attrs):
    """
    Create a list of serializer field instances from the passed in 'attrs',
    plus any fields on the base classes (in 'bases').

    Note that all fields from the base classes are used.
    """
    fields = [(field_name, attrs.pop(field_name))
              for field_name, obj in list(six.iteritems(attrs))
              if isinstance(obj, Field)]
    fields.sort(key=lambda x: x[1].creation_counter)

    # If this class is subclassing another Serializer, add that Serializer's
    # fields.  Note that we loop over the bases in *reverse*. This is necessary
    # in order to maintain the correct order of fields.
    for base in bases[::-1]:
        if hasattr(base, 'base_fields'):
            fields = list(base.base_fields.items()) + fields

    return SortedDict(fields)


class SerializerMetaclass(type):
    def __new__(cls, name, bases, attrs):
        attrs['base_fields'] = _get_declared_fields(bases, attrs)
        return super(SerializerMetaclass, cls).__new__(cls, name, bases, attrs)


class SerializerOptions(object):
    """
    Meta class options for Serializer
    """
    def __init__(self, meta):
        self.depth = getattr(meta, 'depth', 0)
        self.fields = getattr(meta, 'fields', ())
        self.exclude = getattr(meta, 'exclude', ())


class BaseSerializer(WritableField):
    """
    This is the Serializer implementation.
    We need to implement it as `BaseSerializer` due to metaclass magicks.
    """
    class Meta(object):
        pass

    _options_class = SerializerOptions
    _dict_class = SortedDictWithMetadata

    def __init__(self, instance=None, data=None, files=None,
                 context=None, partial=False, many=None,
                 allow_add_remove=False, **kwargs):
        super(BaseSerializer, self).__init__(**kwargs)
        self.opts = self._options_class(self.Meta)
        self.parent = None
        self.root = None
        self.partial = partial
        self.many = many
        self.allow_add_remove = allow_add_remove

        self.context = context or {}

        self.init_data = data
        self.init_files = files
        self.object = instance
        self.fields = self.get_fields()

        self._data = None
        self._files = None
        self._errors = None

        if many and instance is not None and not hasattr(instance, '__iter__'):
            raise ValueError('instance should be a queryset or other iterable with many=True')

        if allow_add_remove and not many:
            raise ValueError('allow_add_remove should only be used for bulk updates, but you have not set many=True')

    #####
    # Methods to determine which fields to use when (de)serializing objects.

    def get_default_fields(self):
        """
        Return the complete set of default fields for the object, as a dict.
        """
        return {}

    def get_fields(self):
        """
        Returns the complete set of fields for the object as a dict.

        This will be the set of any explicitly declared fields,
        plus the set of fields returned by get_default_fields().
        """
        ret = SortedDict()

        # Get the explicitly declared fields
        base_fields = copy.deepcopy(self.base_fields)
        for key, field in base_fields.items():
            ret[key] = field

        # Add in the default fields
        default_fields = self.get_default_fields()
        for key, val in default_fields.items():
            if key not in ret:
                ret[key] = val

        # If 'fields' is specified, use those fields, in that order.
        if self.opts.fields:
            assert isinstance(self.opts.fields, (list, tuple)), '`fields` must be a list or tuple'
            new = SortedDict()
            for key in self.opts.fields:
                new[key] = ret[key]
            ret = new

        # Remove anything in 'exclude'
        if self.opts.exclude:
            assert isinstance(self.opts.exclude, (list, tuple)), '`exclude` must be a list or tuple'
            for key in self.opts.exclude:
                ret.pop(key, None)

        for key, field in ret.items():
            field.initialize(parent=self, field_name=key)

        return ret

    #####
    # Methods to convert or revert from objects <--> primitive representations.

    def get_field_key(self, field_name):
        """
        Return the key that should be used for a given field.
        """
        return field_name

    def restore_fields(self, data, files):
        """
        Core of deserialization, together with `restore_object`.
        Converts a dictionary of data into a dictionary of deserialized fields.
        """
        reverted_data = {}

        if data is not None and not isinstance(data, dict):
            self._errors['non_field_errors'] = ['Invalid data']
            return None

        for field_name, field in self.fields.items():
            field.initialize(parent=self, field_name=field_name)
            try:
                field.field_from_native(data, files, field_name, reverted_data)
            except ValidationError as err:
                self._errors[field_name] = list(err.messages)

        return reverted_data

    def perform_validation(self, attrs):
        """
        Run `validate_<fieldname>()` and `validate()` methods on the serializer
        """
        for field_name, field in self.fields.items():
            if field_name in self._errors:
                continue

            source = field.source or field_name
            if self.partial and source not in attrs:
                continue
            try:
                validate_method = getattr(self, 'validate_%s' % field_name, None)
                if validate_method:
                    attrs = validate_method(attrs, source)
            except ValidationError as err:
                self._errors[field_name] = self._errors.get(field_name, []) + list(err.messages)

        # If there are already errors, we don't run .validate() because
        # field-validation failed and thus `attrs` may not be complete.
        # which in turn can cause inconsistent validation errors.
        if not self._errors:
            try:
                attrs = self.validate(attrs)
            except ValidationError as err:
                if hasattr(err, 'message_dict'):
                    for field_name, error_messages in err.message_dict.items():
                        self._errors[field_name] = self._errors.get(field_name, []) + list(error_messages)
                elif hasattr(err, 'messages'):
                    self._errors['non_field_errors'] = err.messages

        return attrs

    def validate(self, attrs):
        """
        Stub method, to be overridden in Serializer subclasses
        """
        return attrs

    def restore_object(self, attrs, instance=None):
        """
        Deserialize a dictionary of attributes into an object instance.
        You should override this method to control how deserialized objects
        are instantiated.
        """
        if instance is not None:
            instance.update(attrs)
            return instance
        return attrs

    def to_native(self, obj):
        """
        Serialize objects -> primitives.
        """
        ret = self._dict_class()
        ret.fields = self._dict_class()

        for field_name, field in self.fields.items():
            if field.read_only and obj is None:
                continue
            field.initialize(parent=self, field_name=field_name)
            key = self.get_field_key(field_name)
            value = field.field_to_native(obj, field_name)
            method = getattr(self, 'transform_%s' % field_name, None)
            if callable(method):
                value = method(obj, value)
            if not getattr(field, 'write_only', False):
                ret[key] = value
            ret.fields[key] = self.augment_field(field, field_name, key, value)

        return ret

    def from_native(self, data, files=None):
        """
        Deserialize primitives -> objects.
        """
        self._errors = {}

        if data is not None or files is not None:
            attrs = self.restore_fields(data, files)
            if attrs is not None:
                attrs = self.perform_validation(attrs)
        else:
            self._errors['non_field_errors'] = ['No input provided']

        if not self._errors:
            return self.restore_object(attrs, instance=getattr(self, 'object', None))

    def augment_field(self, field, field_name, key, value):
        # This horrible stuff is to manage serializers rendering to HTML
        field._errors = self._errors.get(key) if self._errors else None
        field._name = field_name
        field._value = self.init_data.get(key) if self._errors and self.init_data else value
        if not field.label:
            field.label = pretty_name(key)
        return field

    def field_to_native(self, obj, field_name):
        """
        Override default so that the serializer can be used as a nested field
        across relationships.
        """
        if self.write_only:
            return None

        if self.source == '*':
            return self.to_native(obj)

        # Get the raw field value
        try:
            source = self.source or field_name
            value = obj

            for component in source.split('.'):
                if value is None:
                    break
                value = get_component(value, component)
        except ObjectDoesNotExist:
            return None

        if is_simple_callable(getattr(value, 'all', None)):
            return [self.to_native(item) for item in value.all()]

        if value is None:
            return None

        if self.many is not None:
            many = self.many
        else:
            many = hasattr(value, '__iter__') and not isinstance(value, (Page, dict, six.text_type))

        if many:
            return [self.to_native(item) for item in value]
        return self.to_native(value)

    def field_from_native(self, data, files, field_name, into):
        """
        Override default so that the serializer can be used as a writable
        nested field across relationships.
        """
        if self.read_only:
            return

        try:
            value = data[field_name]
        except KeyError:
            if self.default is not None and not self.partial:
                # Note: partial updates shouldn't set defaults
                value = copy.deepcopy(self.default)
            else:
                if self.required:
                    raise ValidationError(self.error_messages['required'])
                return

        if self.source == '*':
            if value:
                reverted_data = self.restore_fields(value, {})
                if not self._errors:
                    into.update(reverted_data)
        else:
            if value in (None, ''):
                into[(self.source or field_name)] = None
            else:
                # Set the serializer object if it exists
                obj = get_component(self.parent.object, self.source or field_name) if self.parent.object else None

                # If we have a model manager or similar object then we need
                # to iterate through each instance.
                if (self.many and
                    not hasattr(obj, '__iter__') and
                    is_simple_callable(getattr(obj, 'all', None))):
                    obj = obj.all()

                kwargs = {
                    'instance': obj,
                    'data': value,
                    'context': self.context,
                    'partial': self.partial,
                    'many': self.many,
                    'allow_add_remove': self.allow_add_remove
                }
                serializer = self.__class__(**kwargs)

                if serializer.is_valid():
                    into[self.source or field_name] = serializer.object
                else:
                    # Propagate errors up to our parent
                    raise NestedValidationError(serializer.errors)

    def get_identity(self, data):
        """
        This hook is required for bulk update.
        It is used to determine the canonical identity of a given object.

        Note that the data has not been validated at this point, so we need
        to make sure that we catch any cases of incorrect datatypes being
        passed to this method.
        """
        try:
            return data.get('id', None)
        except AttributeError:
            return None

    @property
    def errors(self):
        """
        Run deserialization and return error data,
        setting self.object if no errors occurred.
        """
        if self._errors is None:
            data, files = self.init_data, self.init_files

            if self.many is not None:
                many = self.many
            else:
                many = hasattr(data, '__iter__') and not isinstance(data, (Page, dict, six.text_type))
                if many:
                    warnings.warn('Implicit list/queryset serialization is deprecated. '
                                  'Use the `many=True` flag when instantiating the serializer.',
                                  DeprecationWarning, stacklevel=3)

            if many:
                ret = RelationsList()
                errors = []
                update = self.object is not None

                if update:
                    # If this is a bulk update we need to map all the objects
                    # to a canonical identity so we can determine which
                    # individual object is being updated for each item in the
                    # incoming data
                    objects = self.object
                    identities = [self.get_identity(self.to_native(obj)) for obj in objects]
                    identity_to_objects = dict(zip(identities, objects))

                if hasattr(data, '__iter__') and not isinstance(data, (dict, six.text_type)):
                    for item in data:
                        if update:
                            # Determine which object we're updating
                            identity = self.get_identity(item)
                            self.object = identity_to_objects.pop(identity, None)
                            if self.object is None and not self.allow_add_remove:
                                ret.append(None)
                                errors.append({'non_field_errors': ['Cannot create a new item, only existing items may be updated.']})
                                continue

                        ret.append(self.from_native(item, None))
                        errors.append(self._errors)

                    if update and self.allow_add_remove:
                        ret._deleted = identity_to_objects.values()

                    self._errors = any(errors) and errors or []
                else:
                    self._errors = {'non_field_errors': ['Expected a list of items.']}
            else:
                ret = self.from_native(data, files)

            if not self._errors:
                self.object = ret

        return self._errors

    def is_valid(self):
        return not self.errors

    @property
    def data(self):
        """
        Returns the serialized data on the serializer.
        """
        if self._data is None:
            obj = self.object

            if self.many is not None:
                many = self.many
            else:
                many = hasattr(obj, '__iter__') and not isinstance(obj, (Page, dict))
                if many:
                    warnings.warn('Implicit list/queryset serialization is deprecated. '
                                  'Use the `many=True` flag when instantiating the serializer.',
                                  DeprecationWarning, stacklevel=2)

            if many:
                self._data = [self.to_native(item) for item in obj]
            else:
                self._data = self.to_native(obj)

        return self._data

    def save_object(self, obj, **kwargs):
        obj.save(**kwargs)

    def delete_object(self, obj):
        obj.delete()

    def save(self, **kwargs):
        """
        Save the deserialized object and return it.
        """
        # Clear cached _data, which may be invalidated by `save()`
        self._data = None

        if isinstance(self.object, list):
            [self.save_object(item, **kwargs) for item in self.object]

            if self.object._deleted:
                [self.delete_object(item) for item in self.object._deleted]
        else:
            self.save_object(self.object, **kwargs)

        return self.object

    def metadata(self):
        """
        Return a dictionary of metadata about the fields on the serializer.
        Useful for things like responding to OPTIONS requests, or generating
        API schemas for auto-documentation.
        """
        return SortedDict(
            [(field_name, field.metadata())
            for field_name, field in six.iteritems(self.fields)]
        )


class Serializer(six.with_metaclass(SerializerMetaclass, BaseSerializer)):
    pass


class ModelSerializerOptions(SerializerOptions):
    """
    Meta class options for ModelSerializer
    """
    def __init__(self, meta):
        super(ModelSerializerOptions, self).__init__(meta)
        self.model = getattr(meta, 'model', None)
        self.read_only_fields = getattr(meta, 'read_only_fields', ())
        self.write_only_fields = getattr(meta, 'write_only_fields', ())


class ModelSerializer(Serializer):
    """
    A serializer that deals with model instances and querysets.
    """
    _options_class = ModelSerializerOptions

    field_mapping = {
        models.AutoField: IntegerField,
        models.FloatField: FloatField,
        models.IntegerField: IntegerField,
        models.PositiveIntegerField: IntegerField,
        models.SmallIntegerField: IntegerField,
        models.PositiveSmallIntegerField: IntegerField,
        models.DateTimeField: DateTimeField,
        models.DateField: DateField,
        models.TimeField: TimeField,
        models.DecimalField: DecimalField,
        models.EmailField: EmailField,
        models.CharField: CharField,
        models.URLField: URLField,
        models.SlugField: SlugField,
        models.TextField: CharField,
        models.CommaSeparatedIntegerField: CharField,
        models.BooleanField: BooleanField,
        models.NullBooleanField: BooleanField,
        models.FileField: FileField,
        models.ImageField: ImageField,
    }

    def get_default_fields(self):
        """
        Return all the fields that should be serialized for the model.
        """

        cls = self.opts.model
        assert cls is not None, \
                "Serializer class '%s' is missing 'model' Meta option" % self.__class__.__name__
        opts = get_concrete_model(cls)._meta
        ret = SortedDict()
        nested = bool(self.opts.depth)

        # Deal with adding the primary key field
        pk_field = opts.pk
        while pk_field.rel and pk_field.rel.parent_link:
            # If model is a child via multitable inheritance, use parent's pk
            pk_field = pk_field.rel.to._meta.pk

        field = self.get_pk_field(pk_field)
        if field:
            ret[pk_field.name] = field

        # Deal with forward relationships
        forward_rels = [field for field in opts.fields if field.serialize]
        forward_rels += [field for field in opts.many_to_many if field.serialize]

        for model_field in forward_rels:
            has_through_model = False

            if model_field.rel:
                to_many = isinstance(model_field,
                                     models.fields.related.ManyToManyField)
                related_model = _resolve_model(model_field.rel.to)

                if to_many and not model_field.rel.through._meta.auto_created:
                    has_through_model = True

            if model_field.rel and nested:
                if len(inspect.getargspec(self.get_nested_field).args) == 2:
                    warnings.warn(
                        'The `get_nested_field(model_field)` call signature '
                        'is due to be deprecated. '
                        'Use `get_nested_field(model_field, related_model, '
                        'to_many) instead',
                        PendingDeprecationWarning
                    )
                    field = self.get_nested_field(model_field)
                else:
                    field = self.get_nested_field(model_field, related_model, to_many)
            elif model_field.rel:
                if len(inspect.getargspec(self.get_nested_field).args) == 3:
                    warnings.warn(
                        'The `get_related_field(model_field, to_many)` call '
                        'signature is due to be deprecated. '
                        'Use `get_related_field(model_field, related_model, '
                        'to_many) instead',
                        PendingDeprecationWarning
                    )
                    field = self.get_related_field(model_field, to_many=to_many)
                else:
                    field = self.get_related_field(model_field, related_model, to_many)
            else:
                field = self.get_field(model_field)

            if field:
                if has_through_model:
                    field.read_only = True

                ret[model_field.name] = field

        # Deal with reverse relationships
        if not self.opts.fields:
            reverse_rels = []
        else:
            # Reverse relationships are only included if they are explicitly
            # present in the `fields` option on the serializer
            reverse_rels = opts.get_all_related_objects()
            reverse_rels += opts.get_all_related_many_to_many_objects()

        for relation in reverse_rels:
            accessor_name = relation.get_accessor_name()
            if not self.opts.fields or accessor_name not in self.opts.fields:
                continue
            related_model = relation.model
            to_many = relation.field.rel.multiple
            has_through_model = False
            is_m2m = isinstance(relation.field,
                                models.fields.related.ManyToManyField)

            if (is_m2m and
                hasattr(relation.field.rel, 'through') and
                not relation.field.rel.through._meta.auto_created):
                has_through_model = True

            if nested:
                field = self.get_nested_field(None, related_model, to_many)
            else:
                field = self.get_related_field(None, related_model, to_many)

            if field:
                if has_through_model:
                    field.read_only = True

                ret[accessor_name] = field

        # Ensure that 'read_only_fields' is an iterable
        assert isinstance(self.opts.read_only_fields, (list, tuple)), '`read_only_fields` must be a list or tuple'

        # Add the `read_only` flag to any fields that have been specified
        # in the `read_only_fields` option
        for field_name in self.opts.read_only_fields:
            assert field_name not in self.base_fields.keys(), (
                "field '%s' on serializer '%s' specified in "
                "`read_only_fields`, but also added "
                "as an explicit field.  Remove it from `read_only_fields`." %
                (field_name, self.__class__.__name__))
            assert field_name in ret, (
                "Non-existant field '%s' specified in `read_only_fields` "
                "on serializer '%s'." %
                (field_name, self.__class__.__name__))
            ret[field_name].read_only = True

        # Ensure that 'write_only_fields' is an iterable
        assert isinstance(self.opts.write_only_fields, (list, tuple)), '`write_only_fields` must be a list or tuple'

        for field_name in self.opts.write_only_fields:
            assert field_name not in self.base_fields.keys(), (
                "field '%s' on serializer '%s' specified in "
                "`write_only_fields`, but also added "
                "as an explicit field.  Remove it from `write_only_fields`." %
                (field_name, self.__class__.__name__))
            assert field_name in ret, (
                "Non-existant field '%s' specified in `write_only_fields` "
                "on serializer '%s'." %
                (field_name, self.__class__.__name__))
            ret[field_name].write_only = True

        return ret

    def get_pk_field(self, model_field):
        """
        Returns a default instance of the pk field.
        """
        return self.get_field(model_field)

    def get_nested_field(self, model_field, related_model, to_many):
        """
        Creates a default instance of a nested relational field.

        Note that model_field will be `None` for reverse relationships.
        """
        class NestedModelSerializer(ModelSerializer):
            class Meta:
                model = related_model
                depth = self.opts.depth - 1

        return NestedModelSerializer(many=to_many)

    def get_related_field(self, model_field, related_model, to_many):
        """
        Creates a default instance of a flat relational field.

        Note that model_field will be `None` for reverse relationships.
        """
        # TODO: filter queryset using:
        # .using(db).complex_filter(self.rel.limit_choices_to)

        kwargs = {
            'queryset': related_model._default_manager,
            'many': to_many
        }

        if model_field:
            kwargs['required'] = not(model_field.null or model_field.blank)
            if model_field.help_text is not None:
                kwargs['help_text'] = model_field.help_text
            if model_field.verbose_name is not None:
                kwargs['label'] = model_field.verbose_name

            if not model_field.editable:
                kwargs['read_only'] = True

            if model_field.verbose_name is not None:
                kwargs['label'] = model_field.verbose_name

            if model_field.help_text is not None:
                kwargs['help_text'] = model_field.help_text

        return PrimaryKeyRelatedField(**kwargs)

    def get_field(self, model_field):
        """
        Creates a default instance of a basic non-relational field.
        """
        kwargs = {}

        if model_field.null or model_field.blank:
            kwargs['required'] = False

        if isinstance(model_field, models.AutoField) or not model_field.editable:
            kwargs['read_only'] = True

        if model_field.has_default():
            kwargs['default'] = model_field.get_default()

        if issubclass(model_field.__class__, models.TextField):
            kwargs['widget'] = widgets.Textarea

        if model_field.verbose_name is not None:
            kwargs['label'] = model_field.verbose_name

        if model_field.help_text is not None:
            kwargs['help_text'] = model_field.help_text

        # TODO: TypedChoiceField?
        if model_field.flatchoices:  # This ModelField contains choices
            kwargs['choices'] = model_field.flatchoices
            if model_field.null:
                kwargs['empty'] = None
            return ChoiceField(**kwargs)

        # put this below the ChoiceField because min_value isn't a valid initializer
        if issubclass(model_field.__class__, models.PositiveIntegerField) or\
                issubclass(model_field.__class__, models.PositiveSmallIntegerField):
            kwargs['min_value'] = 0

        attribute_dict = {
            models.CharField: ['max_length'],
            models.CommaSeparatedIntegerField: ['max_length'],
            models.DecimalField: ['max_digits', 'decimal_places'],
            models.EmailField: ['max_length'],
            models.FileField: ['max_length'],
            models.ImageField: ['max_length'],
            models.SlugField: ['max_length'],
            models.URLField: ['max_length'],
        }

        if model_field.__class__ in attribute_dict:
            attributes = attribute_dict[model_field.__class__]
            for attribute in attributes:
                kwargs.update({attribute: getattr(model_field, attribute)})

        try:
            return self.field_mapping[model_field.__class__](**kwargs)
        except KeyError:
            return ModelField(model_field=model_field, **kwargs)

    def get_validation_exclusions(self, instance=None):
        """
        Return a list of field names to exclude from model validation.
        """
        cls = self.opts.model
        opts = get_concrete_model(cls)._meta
        exclusions = [field.name for field in opts.fields + opts.many_to_many]

        for field_name, field in self.fields.items():
            field_name = field.source or field_name
            if field_name in exclusions \
                and not field.read_only \
                and (field.required or hasattr(instance, field_name)) \
                and not isinstance(field, Serializer):
                exclusions.remove(field_name)
        return exclusions

    def full_clean(self, instance):
        """
        Perform Django's full_clean, and populate the `errors` dictionary
        if any validation errors occur.

        Note that we don't perform this inside the `.restore_object()` method,
        so that subclasses can override `.restore_object()`, and still get
        the full_clean validation checking.
        """
        try:
            instance.full_clean(exclude=self.get_validation_exclusions(instance))
        except ValidationError as err:
            self._errors = err.message_dict
            return None
        return instance

    def restore_object(self, attrs, instance=None):
        """
        Restore the model instance.
        """
        m2m_data = {}
        related_data = {}
        nested_forward_relations = {}
        meta = self.opts.model._meta

        # Reverse fk or one-to-one relations
        for (obj, model) in meta.get_all_related_objects_with_model():
            field_name = obj.get_accessor_name()
            if field_name in attrs:
                related_data[field_name] = attrs.pop(field_name)

        # Reverse m2m relations
        for (obj, model) in meta.get_all_related_m2m_objects_with_model():
            field_name = obj.get_accessor_name()
            if field_name in attrs:
                m2m_data[field_name] = attrs.pop(field_name)

        # Forward m2m relations
        for field in meta.many_to_many + meta.virtual_fields:
            if isinstance(field, GenericForeignKey):
                continue
            if field.name in attrs:
                m2m_data[field.name] = attrs.pop(field.name)

        # Nested forward relations - These need to be marked so we can save
        # them before saving the parent model instance.
        for field_name in attrs.keys():
            if isinstance(self.fields.get(field_name, None), Serializer):
                nested_forward_relations[field_name] = attrs[field_name]

        # Create an empty instance of the model
        if instance is None:
            instance = self.opts.model()

        for key, val in attrs.items():
            try:
                setattr(instance, key, val)
            except ValueError:
                self._errors[key] = self.error_messages['required']

        # Any relations that cannot be set until we've
        # saved the model get hidden away on these
        # private attributes, so we can deal with them
        # at the point of save.
        instance._related_data = related_data
        instance._m2m_data = m2m_data
        instance._nested_forward_relations = nested_forward_relations

        return instance

    def from_native(self, data, files):
        """
        Override the default method to also include model field validation.
        """
        instance = super(ModelSerializer, self).from_native(data, files)
        if not self._errors:
            return self.full_clean(instance)

    def save_object(self, obj, **kwargs):
        """
        Save the deserialized object.
        """
        if getattr(obj, '_nested_forward_relations', None):
            # Nested relationships need to be saved before we can save the
            # parent instance.
            for field_name, sub_object in obj._nested_forward_relations.items():
                if sub_object:
                    self.save_object(sub_object)
                setattr(obj, field_name, sub_object)

        obj.save(**kwargs)

        if getattr(obj, '_m2m_data', None):
            for accessor_name, object_list in obj._m2m_data.items():
                setattr(obj, accessor_name, object_list)
            del(obj._m2m_data)

        if getattr(obj, '_related_data', None):
            related_fields = dict([
                (field.get_accessor_name(), field)
                for field, model
                in obj._meta.get_all_related_objects_with_model()
            ])
            for accessor_name, related in obj._related_data.items():
                if isinstance(related, RelationsList):
                    # Nested reverse fk relationship
                    for related_item in related:
                        fk_field = related_fields[accessor_name].field.name
                        setattr(related_item, fk_field, obj)
                        self.save_object(related_item)

                    # Delete any removed objects
                    if related._deleted:
                        [self.delete_object(item) for item in related._deleted]

                elif isinstance(related, models.Model):
                    # Nested reverse one-one relationship
                    fk_field = obj._meta.get_field_by_name(accessor_name)[0].field.name
                    setattr(related, fk_field, obj)
                    self.save_object(related)
                else:
                    # Reverse FK or reverse one-one
                    setattr(obj, accessor_name, related)
            del(obj._related_data)


class HyperlinkedModelSerializerOptions(ModelSerializerOptions):
    """
    Options for HyperlinkedModelSerializer
    """
    def __init__(self, meta):
        super(HyperlinkedModelSerializerOptions, self).__init__(meta)
        self.view_name = getattr(meta, 'view_name', None)
        self.lookup_field = getattr(meta, 'lookup_field', None)
        self.url_field_name = getattr(meta, 'url_field_name', api_settings.URL_FIELD_NAME)


class HyperlinkedModelSerializer(ModelSerializer):
    """
    A subclass of ModelSerializer that uses hyperlinked relationships,
    instead of primary key relationships.
    """
    _options_class = HyperlinkedModelSerializerOptions
    _default_view_name = '%(model_name)s-detail'
    _hyperlink_field_class = HyperlinkedRelatedField
    _hyperlink_identify_field_class = HyperlinkedIdentityField

    def get_default_fields(self):
        fields = super(HyperlinkedModelSerializer, self).get_default_fields()

        if self.opts.view_name is None:
            self.opts.view_name = self._get_default_view_name(self.opts.model)

        if self.opts.url_field_name not in fields:
            url_field = self._hyperlink_identify_field_class(
                view_name=self.opts.view_name,
                lookup_field=self.opts.lookup_field
            )
            ret = self._dict_class()
            ret[self.opts.url_field_name] = url_field
            ret.update(fields)
            fields = ret

        return fields

    def get_pk_field(self, model_field):
        if self.opts.fields and model_field.name in self.opts.fields:
            return self.get_field(model_field)

    def get_related_field(self, model_field, related_model, to_many):
        """
        Creates a default instance of a flat relational field.
        """
        # TODO: filter queryset using:
        # .using(db).complex_filter(self.rel.limit_choices_to)
        kwargs = {
            'queryset': related_model._default_manager,
            'view_name': self._get_default_view_name(related_model),
            'many': to_many
        }

        if model_field:
            kwargs['required'] = not(model_field.null or model_field.blank)
            if model_field.help_text is not None:
                kwargs['help_text'] = model_field.help_text
            if model_field.verbose_name is not None:
                kwargs['label'] = model_field.verbose_name

        if self.opts.lookup_field:
            kwargs['lookup_field'] = self.opts.lookup_field

        return self._hyperlink_field_class(**kwargs)

    def get_identity(self, data):
        """
        This hook is required for bulk update.
        We need to override the default, to use the url as the identity.
        """
        try:
            return data.get(self.opts.url_field_name, None)
        except AttributeError:
            return None

    def _get_default_view_name(self, model):
        """
        Return the view name to use if 'view_name' is not specified in 'Meta'
        """
        model_meta = model._meta
        format_kwargs = {
            'app_label': model_meta.app_label,
            'model_name': model_meta.object_name.lower()
        }
        return self._default_view_name % format_kwargs

########NEW FILE########
__FILENAME__ = settings
"""
Settings for REST framework are all namespaced in the REST_FRAMEWORK setting.
For example your project's `settings.py` file might look like this:

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.YAMLRenderer',
    )
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.YAMLParser',
    )
}

This module provides the `api_setting` object, that is used to access
REST framework settings, checking for user settings first, then falling
back to the defaults.
"""
from __future__ import unicode_literals

from django.conf import settings
from django.utils import importlib

from rest_framework import ISO_8601
from rest_framework.compat import six


USER_SETTINGS = getattr(settings, 'REST_FRAMEWORK', None)

DEFAULTS = {
    # Base API policies
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser'
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication'
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
    ),
    'DEFAULT_CONTENT_NEGOTIATION_CLASS':
        'rest_framework.negotiation.DefaultContentNegotiation',

    # Genric view behavior
    'DEFAULT_MODEL_SERIALIZER_CLASS':
        'rest_framework.serializers.ModelSerializer',
    'DEFAULT_PAGINATION_SERIALIZER_CLASS':
        'rest_framework.pagination.PaginationSerializer',
    'DEFAULT_FILTER_BACKENDS': (),

    # Throttling
    'DEFAULT_THROTTLE_RATES': {
        'user': None,
        'anon': None,
    },

    # Pagination
    'PAGINATE_BY': None,
    'PAGINATE_BY_PARAM': None,
    'MAX_PAGINATE_BY': None,

    # Filtering
    'SEARCH_PARAM': 'search',
    'ORDERING_PARAM': 'ordering',

    # Authentication
    'UNAUTHENTICATED_USER': 'django.contrib.auth.models.AnonymousUser',
    'UNAUTHENTICATED_TOKEN': None,

    # View configuration
    'VIEW_NAME_FUNCTION': 'rest_framework.views.get_view_name',
    'VIEW_DESCRIPTION_FUNCTION': 'rest_framework.views.get_view_description',

    # Exception handling
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',

    # Testing
    'TEST_REQUEST_RENDERER_CLASSES': (
        'rest_framework.renderers.MultiPartRenderer',
        'rest_framework.renderers.JSONRenderer'
    ),
    'TEST_REQUEST_DEFAULT_FORMAT': 'multipart',

    # Browser enhancements
    'FORM_METHOD_OVERRIDE': '_method',
    'FORM_CONTENT_OVERRIDE': '_content',
    'FORM_CONTENTTYPE_OVERRIDE': '_content_type',
    'URL_ACCEPT_OVERRIDE': 'accept',
    'URL_FORMAT_OVERRIDE': 'format',

    'FORMAT_SUFFIX_KWARG': 'format',
    'URL_FIELD_NAME': 'url',

    # Input and output formats
    'DATE_INPUT_FORMATS': (
        ISO_8601,
    ),
    'DATE_FORMAT': None,

    'DATETIME_INPUT_FORMATS': (
        ISO_8601,
    ),
    'DATETIME_FORMAT': None,

    'TIME_INPUT_FORMATS': (
        ISO_8601,
    ),
    'TIME_FORMAT': None,

    # Pending deprecation
    'FILTER_BACKEND': None,
}


# List of settings that may be in string import notation.
IMPORT_STRINGS = (
    'DEFAULT_RENDERER_CLASSES',
    'DEFAULT_PARSER_CLASSES',
    'DEFAULT_AUTHENTICATION_CLASSES',
    'DEFAULT_PERMISSION_CLASSES',
    'DEFAULT_THROTTLE_CLASSES',
    'DEFAULT_CONTENT_NEGOTIATION_CLASS',
    'DEFAULT_MODEL_SERIALIZER_CLASS',
    'DEFAULT_PAGINATION_SERIALIZER_CLASS',
    'DEFAULT_FILTER_BACKENDS',
    'EXCEPTION_HANDLER',
    'FILTER_BACKEND',
    'TEST_REQUEST_RENDERER_CLASSES',
    'UNAUTHENTICATED_USER',
    'UNAUTHENTICATED_TOKEN',
    'VIEW_NAME_FUNCTION',
    'VIEW_DESCRIPTION_FUNCTION'
)


def perform_import(val, setting_name):
    """
    If the given setting is a string import notation,
    then perform the necessary import or imports.
    """
    if isinstance(val, six.string_types):
        return import_from_string(val, setting_name)
    elif isinstance(val, (list, tuple)):
        return [import_from_string(item, setting_name) for item in val]
    return val


def import_from_string(val, setting_name):
    """
    Attempt to import a class from a string representation.
    """
    try:
        # Nod to tastypie's use of importlib.
        parts = val.split('.')
        module_path, class_name = '.'.join(parts[:-1]), parts[-1]
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except ImportError as e:
        msg = "Could not import '%s' for API setting '%s'. %s: %s." % (val, setting_name, e.__class__.__name__, e)
        raise ImportError(msg)


class APISettings(object):
    """
    A settings object, that allows API settings to be accessed as properties.
    For example:

        from rest_framework.settings import api_settings
        print api_settings.DEFAULT_RENDERER_CLASSES

    Any setting with string import paths will be automatically resolved
    and return the class, rather than the string literal.
    """
    def __init__(self, user_settings=None, defaults=None, import_strings=None):
        self.user_settings = user_settings or {}
        self.defaults = defaults or {}
        self.import_strings = import_strings or ()

    def __getattr__(self, attr):
        if attr not in self.defaults.keys():
            raise AttributeError("Invalid API setting: '%s'" % attr)

        try:
            # Check if present in user settings
            val = self.user_settings[attr]
        except KeyError:
            # Fall back to defaults
            val = self.defaults[attr]

        # Coerce import strings into classes
        if val and attr in self.import_strings:
            val = perform_import(val, attr)

        self.validate_setting(attr, val)

        # Cache the result
        setattr(self, attr, val)
        return val

    def validate_setting(self, attr, val):
        if attr == 'FILTER_BACKEND' and val is not None:
            # Make sure we can initialize the class
            val()

api_settings = APISettings(USER_SETTINGS, DEFAULTS, IMPORT_STRINGS)

########NEW FILE########
__FILENAME__ = six
"""Utilities for writing code that runs on Python 2 and 3"""

import operator
import sys
import types

__author__ = "Benjamin Peterson <benjamin@python.org>"
__version__ = "1.2.0"


# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str

    if sys.platform == "java":
        # Jython always uses 32 bits.
        MAXSIZE = int((1 << 31) - 1)
    else:
        # It's possible to have sizeof(long) != sizeof(Py_ssize_t).
        class X(object):
            def __len__(self):
                return 1 << 31
        try:
            len(X())
        except OverflowError:
            # 32-bit
            MAXSIZE = int((1 << 31) - 1)
        else:
            # 64-bit
            MAXSIZE = int((1 << 63) - 1)
            del X


def _add_doc(func, doc):
    """Add documentation to a function."""
    func.__doc__ = doc


def _import_module(name):
    """Import module, returning the module after the last dot."""
    __import__(name)
    return sys.modules[name]


class _LazyDescr(object):

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, tp):
        result = self._resolve()
        setattr(obj, self.name, result)
        # This is a bit ugly, but it avoids running this again.
        delattr(tp, self.name)
        return result


class MovedModule(_LazyDescr):

    def __init__(self, name, old, new=None):
        super(MovedModule, self).__init__(name)
        if PY3:
            if new is None:
                new = name
            self.mod = new
        else:
            self.mod = old

    def _resolve(self):
        return _import_module(self.mod)


class MovedAttribute(_LazyDescr):

    def __init__(self, name, old_mod, new_mod, old_attr=None, new_attr=None):
        super(MovedAttribute, self).__init__(name)
        if PY3:
            if new_mod is None:
                new_mod = name
            self.mod = new_mod
            if new_attr is None:
                if old_attr is None:
                    new_attr = name
                else:
                    new_attr = old_attr
            self.attr = new_attr
        else:
            self.mod = old_mod
            if old_attr is None:
                old_attr = name
            self.attr = old_attr

    def _resolve(self):
        module = _import_module(self.mod)
        return getattr(module, self.attr)



class _MovedItems(types.ModuleType):
    """Lazy loading of moved objects"""


_moved_attributes = [
    MovedAttribute("cStringIO", "cStringIO", "io", "StringIO"),
    MovedAttribute("filter", "itertools", "builtins", "ifilter", "filter"),
    MovedAttribute("input", "__builtin__", "builtins", "raw_input", "input"),
    MovedAttribute("map", "itertools", "builtins", "imap", "map"),
    MovedAttribute("reload_module", "__builtin__", "imp", "reload"),
    MovedAttribute("reduce", "__builtin__", "functools"),
    MovedAttribute("StringIO", "StringIO", "io"),
    MovedAttribute("xrange", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("zip", "itertools", "builtins", "izip", "zip"),

    MovedModule("builtins", "__builtin__"),
    MovedModule("configparser", "ConfigParser"),
    MovedModule("copyreg", "copy_reg"),
    MovedModule("http_cookiejar", "cookielib", "http.cookiejar"),
    MovedModule("http_cookies", "Cookie", "http.cookies"),
    MovedModule("html_entities", "htmlentitydefs", "html.entities"),
    MovedModule("html_parser", "HTMLParser", "html.parser"),
    MovedModule("http_client", "httplib", "http.client"),
    MovedModule("BaseHTTPServer", "BaseHTTPServer", "http.server"),
    MovedModule("CGIHTTPServer", "CGIHTTPServer", "http.server"),
    MovedModule("SimpleHTTPServer", "SimpleHTTPServer", "http.server"),
    MovedModule("cPickle", "cPickle", "pickle"),
    MovedModule("queue", "Queue"),
    MovedModule("reprlib", "repr"),
    MovedModule("socketserver", "SocketServer"),
    MovedModule("tkinter", "Tkinter"),
    MovedModule("tkinter_dialog", "Dialog", "tkinter.dialog"),
    MovedModule("tkinter_filedialog", "FileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_scrolledtext", "ScrolledText", "tkinter.scrolledtext"),
    MovedModule("tkinter_simpledialog", "SimpleDialog", "tkinter.simpledialog"),
    MovedModule("tkinter_tix", "Tix", "tkinter.tix"),
    MovedModule("tkinter_constants", "Tkconstants", "tkinter.constants"),
    MovedModule("tkinter_dnd", "Tkdnd", "tkinter.dnd"),
    MovedModule("tkinter_colorchooser", "tkColorChooser",
                "tkinter.colorchooser"),
    MovedModule("tkinter_commondialog", "tkCommonDialog",
                "tkinter.commondialog"),
    MovedModule("tkinter_tkfiledialog", "tkFileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_font", "tkFont", "tkinter.font"),
    MovedModule("tkinter_messagebox", "tkMessageBox", "tkinter.messagebox"),
    MovedModule("tkinter_tksimpledialog", "tkSimpleDialog",
                "tkinter.simpledialog"),
    MovedModule("urllib_robotparser", "robotparser", "urllib.robotparser"),
    MovedModule("winreg", "_winreg"),
]
for attr in _moved_attributes:
    setattr(_MovedItems, attr.name, attr)
del attr

moves = sys.modules["django.utils.six.moves"] = _MovedItems("moves")


def add_move(move):
    """Add an item to six.moves."""
    setattr(_MovedItems, move.name, move)


def remove_move(name):
    """Remove item from six.moves."""
    try:
        delattr(_MovedItems, name)
    except AttributeError:
        try:
            del moves.__dict__[name]
        except KeyError:
            raise AttributeError("no such move, %r" % (name,))


if PY3:
    _meth_func = "__func__"
    _meth_self = "__self__"

    _func_code = "__code__"
    _func_defaults = "__defaults__"

    _iterkeys = "keys"
    _itervalues = "values"
    _iteritems = "items"
else:
    _meth_func = "im_func"
    _meth_self = "im_self"

    _func_code = "func_code"
    _func_defaults = "func_defaults"

    _iterkeys = "iterkeys"
    _itervalues = "itervalues"
    _iteritems = "iteritems"


try:
    advance_iterator = next
except NameError:
    def advance_iterator(it):
        return it.next()
next = advance_iterator


if PY3:
    def get_unbound_function(unbound):
        return unbound

    Iterator = object

    def callable(obj):
        return any("__call__" in klass.__dict__ for klass in type(obj).__mro__)
else:
    def get_unbound_function(unbound):
        return unbound.im_func

    class Iterator(object):

        def next(self):
            return type(self).__next__(self)

    callable = callable
_add_doc(get_unbound_function,
         """Get the function out of a possibly unbound function""")


get_method_function = operator.attrgetter(_meth_func)
get_method_self = operator.attrgetter(_meth_self)
get_function_code = operator.attrgetter(_func_code)
get_function_defaults = operator.attrgetter(_func_defaults)


def iterkeys(d):
    """Return an iterator over the keys of a dictionary."""
    return iter(getattr(d, _iterkeys)())

def itervalues(d):
    """Return an iterator over the values of a dictionary."""
    return iter(getattr(d, _itervalues)())

def iteritems(d):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return iter(getattr(d, _iteritems)())


if PY3:
    def b(s):
        return s.encode("latin-1")
    def u(s):
        return s
    if sys.version_info[1] <= 1:
        def int2byte(i):
            return bytes((i,))
    else:
        # This is about 2x faster than the implementation above on 3.2+
        int2byte = operator.methodcaller("to_bytes", 1, "big")
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
else:
    def b(s):
        return s
    def u(s):
        return unicode(s, "unicode_escape")
    int2byte = chr
    import StringIO
    StringIO = BytesIO = StringIO.StringIO
_add_doc(b, """Byte literal""")
_add_doc(u, """Text literal""")


if PY3:
    import builtins
    exec_ = getattr(builtins, "exec")


    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value


    print_ = getattr(builtins, "print")
    del builtins

else:
    def exec_(code, globs=None, locs=None):
        """Execute code in a namespace."""
        if globs is None:
            frame = sys._getframe(1)
            globs = frame.f_globals
            if locs is None:
                locs = frame.f_locals
            del frame
        elif locs is None:
            locs = globs
        exec("""exec code in globs, locs""")


    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")


    def print_(*args, **kwargs):
        """The new-style print function."""
        fp = kwargs.pop("file", sys.stdout)
        if fp is None:
            return
        def write(data):
            if not isinstance(data, basestring):
                data = str(data)
            fp.write(data)
        want_unicode = False
        sep = kwargs.pop("sep", None)
        if sep is not None:
            if isinstance(sep, unicode):
                want_unicode = True
            elif not isinstance(sep, str):
                raise TypeError("sep must be None or a string")
        end = kwargs.pop("end", None)
        if end is not None:
            if isinstance(end, unicode):
                want_unicode = True
            elif not isinstance(end, str):
                raise TypeError("end must be None or a string")
        if kwargs:
            raise TypeError("invalid keyword arguments to print()")
        if not want_unicode:
            for arg in args:
                if isinstance(arg, unicode):
                    want_unicode = True
                    break
        if want_unicode:
            newline = unicode("\n")
            space = unicode(" ")
        else:
            newline = "\n"
            space = " "
        if sep is None:
            sep = space
        if end is None:
            end = newline
        for i, arg in enumerate(args):
            if i:
                write(sep)
            write(arg)
        write(end)

_add_doc(reraise, """Reraise an exception.""")


def with_metaclass(meta, base=object):
    """Create a base class with a metaclass."""
    return meta("NewBase", (base,), {})


### Additional customizations for Django ###

if PY3:
    _iterlists = "lists"
    _assertRaisesRegex = "assertRaisesRegex"
else:
    _iterlists = "iterlists"
    _assertRaisesRegex = "assertRaisesRegexp"


def iterlists(d):
    """Return an iterator over the values of a MultiValueDict."""
    return getattr(d, _iterlists)()


def assertRaisesRegex(self, *args, **kwargs):
    return getattr(self, _assertRaisesRegex)(*args, **kwargs)


add_move(MovedModule("_dummy_thread", "dummy_thread"))
add_move(MovedModule("_thread", "thread"))

########NEW FILE########
__FILENAME__ = status
"""
Descriptive HTTP status codes, for code readability.

See RFC 2616 - http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html
And RFC 6585 - http://tools.ietf.org/html/rfc6585
"""
from __future__ import unicode_literals


def is_informational(code):
    return code >= 100 and code <= 199

def is_success(code):
    return code >= 200 and code <= 299

def is_redirect(code):
    return code >= 300 and code <= 399

def is_client_error(code):
    return code >= 400 and code <= 499

def is_server_error(code):
    return code >= 500 and code <= 599


HTTP_100_CONTINUE = 100
HTTP_101_SWITCHING_PROTOCOLS = 101
HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_202_ACCEPTED = 202
HTTP_203_NON_AUTHORITATIVE_INFORMATION = 203
HTTP_204_NO_CONTENT = 204
HTTP_205_RESET_CONTENT = 205
HTTP_206_PARTIAL_CONTENT = 206
HTTP_300_MULTIPLE_CHOICES = 300
HTTP_301_MOVED_PERMANENTLY = 301
HTTP_302_FOUND = 302
HTTP_303_SEE_OTHER = 303
HTTP_304_NOT_MODIFIED = 304
HTTP_305_USE_PROXY = 305
HTTP_306_RESERVED = 306
HTTP_307_TEMPORARY_REDIRECT = 307
HTTP_400_BAD_REQUEST = 400
HTTP_401_UNAUTHORIZED = 401
HTTP_402_PAYMENT_REQUIRED = 402
HTTP_403_FORBIDDEN = 403
HTTP_404_NOT_FOUND = 404
HTTP_405_METHOD_NOT_ALLOWED = 405
HTTP_406_NOT_ACCEPTABLE = 406
HTTP_407_PROXY_AUTHENTICATION_REQUIRED = 407
HTTP_408_REQUEST_TIMEOUT = 408
HTTP_409_CONFLICT = 409
HTTP_410_GONE = 410
HTTP_411_LENGTH_REQUIRED = 411
HTTP_412_PRECONDITION_FAILED = 412
HTTP_413_REQUEST_ENTITY_TOO_LARGE = 413
HTTP_414_REQUEST_URI_TOO_LONG = 414
HTTP_415_UNSUPPORTED_MEDIA_TYPE = 415
HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE = 416
HTTP_417_EXPECTATION_FAILED = 417
HTTP_428_PRECONDITION_REQUIRED = 428
HTTP_429_TOO_MANY_REQUESTS = 429
HTTP_431_REQUEST_HEADER_FIELDS_TOO_LARGE = 431
HTTP_500_INTERNAL_SERVER_ERROR = 500
HTTP_501_NOT_IMPLEMENTED = 501
HTTP_502_BAD_GATEWAY = 502
HTTP_503_SERVICE_UNAVAILABLE = 503
HTTP_504_GATEWAY_TIMEOUT = 504
HTTP_505_HTTP_VERSION_NOT_SUPPORTED = 505
HTTP_511_NETWORK_AUTHENTICATION_REQUIRED = 511

########NEW FILE########
__FILENAME__ = rest_framework
from __future__ import unicode_literals, absolute_import
from django import template
from django.core.urlresolvers import reverse, NoReverseMatch
from django.http import QueryDict
from django.utils.encoding import iri_to_uri
from django.utils.html import escape
from django.utils.safestring import SafeData, mark_safe
from rest_framework.compat import urlparse, force_text, six, smart_urlquote
import re

register = template.Library()


# Note we don't use 'load staticfiles', because we need a 1.3 compatible
# version, so instead we include the `static` template tag ourselves.

# When 1.3 becomes unsupported by REST framework, we can instead start to
# use the {% load staticfiles %} tag, remove the following code,
# and add a dependency that `django.contrib.staticfiles` must be installed.

# Note: We can't put this into the `compat` module because the compat import
# from rest_framework.compat import ...
# conflicts with this rest_framework template tag module.

try:  # Django 1.5+
    from django.contrib.staticfiles.templatetags.staticfiles import StaticFilesNode

    @register.tag('static')
    def do_static(parser, token):
        return StaticFilesNode.handle_token(parser, token)

except ImportError:
    try:  # Django 1.4
        from django.contrib.staticfiles.storage import staticfiles_storage

        @register.simple_tag
        def static(path):
            """
            A template tag that returns the URL to a file
            using staticfiles' storage backend
            """
            return staticfiles_storage.url(path)

    except ImportError:  # Django 1.3
        from urlparse import urljoin
        from django import template
        from django.templatetags.static import PrefixNode

        class StaticNode(template.Node):
            def __init__(self, varname=None, path=None):
                if path is None:
                    raise template.TemplateSyntaxError(
                        "Static template nodes must be given a path to return.")
                self.path = path
                self.varname = varname

            def url(self, context):
                path = self.path.resolve(context)
                return self.handle_simple(path)

            def render(self, context):
                url = self.url(context)
                if self.varname is None:
                    return url
                context[self.varname] = url
                return ''

            @classmethod
            def handle_simple(cls, path):
                return urljoin(PrefixNode.handle_simple("STATIC_URL"), path)

            @classmethod
            def handle_token(cls, parser, token):
                """
                Class method to parse prefix node and return a Node.
                """
                bits = token.split_contents()

                if len(bits) < 2:
                    raise template.TemplateSyntaxError(
                        "'%s' takes at least one argument (path to file)" % bits[0])

                path = parser.compile_filter(bits[1])

                if len(bits) >= 2 and bits[-2] == 'as':
                    varname = bits[3]
                else:
                    varname = None

                return cls(varname, path)

        @register.tag('static')
        def do_static_13(parser, token):
            return StaticNode.handle_token(parser, token)


def replace_query_param(url, key, val):
    """
    Given a URL and a key/val pair, set or replace an item in the query
    parameters of the URL, and return the new URL.
    """
    (scheme, netloc, path, query, fragment) = urlparse.urlsplit(url)
    query_dict = QueryDict(query).copy()
    query_dict[key] = val
    query = query_dict.urlencode()
    return urlparse.urlunsplit((scheme, netloc, path, query, fragment))


# Regex for adding classes to html snippets
class_re = re.compile(r'(?<=class=["\'])(.*)(?=["\'])')


# And the template tags themselves...

@register.simple_tag
def optional_login(request):
    """
    Include a login snippet if REST framework's login view is in the URLconf.
    """
    try:
        login_url = reverse('rest_framework:login')
    except NoReverseMatch:
        return ''

    snippet = "<a href='%s?next=%s'>Log in</a>" % (login_url, request.path)
    return snippet


@register.simple_tag
def optional_logout(request):
    """
    Include a logout snippet if REST framework's logout view is in the URLconf.
    """
    try:
        logout_url = reverse('rest_framework:logout')
    except NoReverseMatch:
        return ''

    snippet = "<a href='%s?next=%s'>Log out</a>" % (logout_url, request.path)
    return snippet


@register.simple_tag
def add_query_param(request, key, val):
    """
    Add a query parameter to the current request url, and return the new url.
    """
    iri = request.get_full_path()
    uri = iri_to_uri(iri)
    return replace_query_param(uri, key, val)


@register.filter
def add_class(value, css_class):
    """
    http://stackoverflow.com/questions/4124220/django-adding-css-classes-when-rendering-form-fields-in-a-template

    Inserts classes into template variables that contain HTML tags,
    useful for modifying forms without needing to change the Form objects.

    Usage:

        {{ field.label_tag|add_class:"control-label" }}

    In the case of REST Framework, the filter is used to add Bootstrap-specific
    classes to the forms.
    """
    html = six.text_type(value)
    match = class_re.search(html)
    if match:
        m = re.search(r'^%s$|^%s\s|\s%s\s|\s%s$' % (css_class, css_class,
                                                    css_class, css_class),
                      match.group(1))
        if not m:
            return mark_safe(class_re.sub(match.group(1) + " " + css_class,
                                          html))
    else:
        return mark_safe(html.replace('>', ' class="%s">' % css_class, 1))
    return value


# Bunch of stuff cloned from urlize
TRAILING_PUNCTUATION = ['.', ',', ':', ';', '.)', '"', "']", "'}", "'"]
WRAPPING_PUNCTUATION = [('(', ')'), ('<', '>'), ('[', ']'), ('&lt;', '&gt;'),
                        ('"', '"'), ("'", "'")]
word_split_re = re.compile(r'(\s+)')
simple_url_re = re.compile(r'^https?://\[?\w', re.IGNORECASE)
simple_url_2_re = re.compile(r'^www\.|^(?!http)\w[^@]+\.(com|edu|gov|int|mil|net|org)$', re.IGNORECASE)
simple_email_re = re.compile(r'^\S+@\S+\.\S+$')


def smart_urlquote_wrapper(matched_url):
    """
    Simple wrapper for smart_urlquote. ValueError("Invalid IPv6 URL") can
    be raised here, see issue #1386
    """
    try:
        return smart_urlquote(matched_url)
    except ValueError:
        return None


@register.filter
def urlize_quoted_links(text, trim_url_limit=None, nofollow=True, autoescape=True):
    """
    Converts any URLs in text into clickable links.

    Works on http://, https://, www. links, and also on links ending in one of
    the original seven gTLDs (.com, .edu, .gov, .int, .mil, .net, and .org).
    Links can have trailing punctuation (periods, commas, close-parens) and
    leading punctuation (opening parens) and it'll still do the right thing.

    If trim_url_limit is not None, the URLs in link text longer than this limit
    will truncated to trim_url_limit-3 characters and appended with an elipsis.

    If nofollow is True, the URLs in link text will get a rel="nofollow"
    attribute.

    If autoescape is True, the link text and URLs will get autoescaped.
    """
    trim_url = lambda x, limit=trim_url_limit: limit is not None and (len(x) > limit and ('%s...' % x[:max(0, limit - 3)])) or x
    safe_input = isinstance(text, SafeData)
    words = word_split_re.split(force_text(text))
    for i, word in enumerate(words):
        if '.' in word or '@' in word or ':' in word:
            # Deal with punctuation.
            lead, middle, trail = '', word, ''
            for punctuation in TRAILING_PUNCTUATION:
                if middle.endswith(punctuation):
                    middle = middle[:-len(punctuation)]
                    trail = punctuation + trail
            for opening, closing in WRAPPING_PUNCTUATION:
                if middle.startswith(opening):
                    middle = middle[len(opening):]
                    lead = lead + opening
                # Keep parentheses at the end only if they're balanced.
                if (middle.endswith(closing)
                    and middle.count(closing) == middle.count(opening) + 1):
                    middle = middle[:-len(closing)]
                    trail = closing + trail

            # Make URL we want to point to.
            url = None
            nofollow_attr = ' rel="nofollow"' if nofollow else ''
            if simple_url_re.match(middle):
                url = smart_urlquote_wrapper(middle)
            elif simple_url_2_re.match(middle):
                url = smart_urlquote_wrapper('http://%s' % middle)
            elif not ':' in middle and simple_email_re.match(middle):
                local, domain = middle.rsplit('@', 1)
                try:
                    domain = domain.encode('idna').decode('ascii')
                except UnicodeError:
                    continue
                url = 'mailto:%s@%s' % (local, domain)
                nofollow_attr = ''

            # Make link.
            if url:
                trimmed = trim_url(middle)
                if autoescape and not safe_input:
                    lead, trail = escape(lead), escape(trail)
                    url, trimmed = escape(url), escape(trimmed)
                middle = '<a href="%s"%s>%s</a>' % (url, nofollow_attr, trimmed)
                words[i] = mark_safe('%s%s%s' % (lead, middle, trail))
            else:
                if safe_input:
                    words[i] = mark_safe(word)
                elif autoescape:
                    words[i] = escape(word)
        elif safe_input:
            words[i] = mark_safe(word)
        elif autoescape:
            words[i] = escape(word)
    return ''.join(words)


@register.filter
def break_long_headers(header):
    """
    Breaks headers longer than 160 characters (~page length)
    when possible (are comma separated)
    """
    if len(header) > 160 and ',' in header:
        header = mark_safe('<br> ' + ', <br>'.join(header.split(',')))
    return header

########NEW FILE########
__FILENAME__ = test
# -- coding: utf-8 --

# Note that we import as `DjangoRequestFactory` and `DjangoClient` in order
# to make it harder for the user to import the wrong thing without realizing.
from __future__ import unicode_literals
import django
from django.conf import settings
from django.test.client import Client as DjangoClient
from django.test.client import ClientHandler
from django.test import testcases
from django.utils.http import urlencode
from rest_framework.settings import api_settings
from rest_framework.compat import RequestFactory as DjangoRequestFactory
from rest_framework.compat import force_bytes_or_smart_bytes, six


def force_authenticate(request, user=None, token=None):
    request._force_auth_user = user
    request._force_auth_token = token


class APIRequestFactory(DjangoRequestFactory):
    renderer_classes_list = api_settings.TEST_REQUEST_RENDERER_CLASSES
    default_format = api_settings.TEST_REQUEST_DEFAULT_FORMAT

    def __init__(self, enforce_csrf_checks=False, **defaults):
        self.enforce_csrf_checks = enforce_csrf_checks
        self.renderer_classes = {}
        for cls in self.renderer_classes_list:
            self.renderer_classes[cls.format] = cls
        super(APIRequestFactory, self).__init__(**defaults)

    def _encode_data(self, data, format=None, content_type=None):
        """
        Encode the data returning a two tuple of (bytes, content_type)
        """

        if not data:
            return ('', None)

        assert format is None or content_type is None, (
            'You may not set both `format` and `content_type`.'
        )

        if content_type:
            # Content type specified explicitly, treat data as a raw bytestring
            ret = force_bytes_or_smart_bytes(data, settings.DEFAULT_CHARSET)

        else:
            format = format or self.default_format

            assert format in self.renderer_classes, ("Invalid format '{0}'. "
                "Available formats are {1}.  Set TEST_REQUEST_RENDERER_CLASSES "
                "to enable extra request formats.".format(
                    format,
                    ', '.join(["'" + fmt + "'" for fmt in self.renderer_classes.keys()])
                )
            )

            # Use format and render the data into a bytestring
            renderer = self.renderer_classes[format]()
            ret = renderer.render(data)

            # Determine the content-type header from the renderer
            content_type = "{0}; charset={1}".format(
                renderer.media_type, renderer.charset
            )

            # Coerce text to bytes if required.
            if isinstance(ret, six.text_type):
                ret = bytes(ret.encode(renderer.charset))

        return ret, content_type

    def get(self, path, data=None, **extra):
        r = {
            'QUERY_STRING': urlencode(data or {}, doseq=True),
        }
        # Fix to support old behavior where you have the arguments in the url
        # See #1461
        if not data and '?' in path:
            r['QUERY_STRING'] = path.split('?')[1]
        r.update(extra)
        return self.generic('GET', path, **r)

    def post(self, path, data=None, format=None, content_type=None, **extra):
        data, content_type = self._encode_data(data, format, content_type)
        return self.generic('POST', path, data, content_type, **extra)

    def put(self, path, data=None, format=None, content_type=None, **extra):
        data, content_type = self._encode_data(data, format, content_type)
        return self.generic('PUT', path, data, content_type, **extra)

    def patch(self, path, data=None, format=None, content_type=None, **extra):
        data, content_type = self._encode_data(data, format, content_type)
        return self.generic('PATCH', path, data, content_type, **extra)

    def delete(self, path, data=None, format=None, content_type=None, **extra):
        data, content_type = self._encode_data(data, format, content_type)
        return self.generic('DELETE', path, data, content_type, **extra)

    def options(self, path, data=None, format=None, content_type=None, **extra):
        data, content_type = self._encode_data(data, format, content_type)
        return self.generic('OPTIONS', path, data, content_type, **extra)

    def request(self, **kwargs):
        request = super(APIRequestFactory, self).request(**kwargs)
        request._dont_enforce_csrf_checks = not self.enforce_csrf_checks
        return request


class ForceAuthClientHandler(ClientHandler):
    """
    A patched version of ClientHandler that can enforce authentication
    on the outgoing requests.
    """

    def __init__(self, *args, **kwargs):
        self._force_user = None
        self._force_token = None
        super(ForceAuthClientHandler, self).__init__(*args, **kwargs)

    def get_response(self, request):
        # This is the simplest place we can hook into to patch the
        # request object.
        force_authenticate(request, self._force_user, self._force_token)
        return super(ForceAuthClientHandler, self).get_response(request)


class APIClient(APIRequestFactory, DjangoClient):
    def __init__(self, enforce_csrf_checks=False, **defaults):
        super(APIClient, self).__init__(**defaults)
        self.handler = ForceAuthClientHandler(enforce_csrf_checks)
        self._credentials = {}

    def credentials(self, **kwargs):
        """
        Sets headers that will be used on every outgoing request.
        """
        self._credentials = kwargs

    def force_authenticate(self, user=None, token=None):
        """
        Forcibly authenticates outgoing requests with the given
        user and/or token.
        """
        self.handler._force_user = user
        self.handler._force_token = token
        if user is None:
            self.logout()  # Also clear any possible session info if required

    def request(self, **kwargs):
        # Ensure that any credentials set get added to every request.
        kwargs.update(self._credentials)
        return super(APIClient, self).request(**kwargs)


class APITransactionTestCase(testcases.TransactionTestCase):
    client_class = APIClient


class APITestCase(testcases.TestCase):
    client_class = APIClient


if django.VERSION >= (1, 4):
    class APISimpleTestCase(testcases.SimpleTestCase):
        client_class = APIClient

    class APILiveServerTestCase(testcases.LiveServerTestCase):
        client_class = APIClient

########NEW FILE########
__FILENAME__ = models
from django.db import models

from rest_framework.tests.users.models import User


class Account(models.Model):
    owner = models.ForeignKey(User, related_name='accounts_owned')
    admins = models.ManyToManyField(User, blank=True, null=True, related_name='accounts_administered')

########NEW FILE########
__FILENAME__ = serializers
from rest_framework import serializers

from rest_framework.tests.accounts.models import Account
from rest_framework.tests.users.serializers import UserSerializer


class AccountSerializer(serializers.ModelSerializer):
    admins = UserSerializer(many=True)

    class Meta:
        model = Account

########NEW FILE########
__FILENAME__ = description
# -- coding: utf-8 --

# Apparently there is a python 2.6 issue where docstrings of imported view classes
# do not retain their encoding information even if a module has a proper
# encoding declaration at the top of its source file. Therefore for tests
# to catch unicode related errors, a mock view has to be declared in a separate
# module.

from rest_framework.views import APIView


# test strings snatched from http://www.columbia.edu/~fdc/utf8/,
# http://winrus.com/utf8-jap.htm and memory
UTF8_TEST_DOCSTRING = (
    'zażółć gęślą jaźń'
    'Sîne klâwen durh die wolken sint geslagen'
    'Τη γλώσσα μου έδωσαν ελληνική'
    'யாமறிந்த மொழிகளிலே தமிழ்மொழி'
    'На берегу пустынных волн'
    'てすと'
    'ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃ'
)


class ViewWithNonASCIICharactersInDocstring(APIView):
    __doc__ = UTF8_TEST_DOCSTRING

########NEW FILE########
__FILENAME__ = bad_import
raise ValueError

########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals
from django.db import models
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers


def foobar():
    return 'foobar'


class CustomField(models.CharField):

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 12
        super(CustomField, self).__init__(*args, **kwargs)


class RESTFrameworkModel(models.Model):
    """
    Base for test models that sets app_label, so they play nicely.
    """
    class Meta:
        app_label = 'tests'
        abstract = True


class HasPositiveIntegerAsChoice(RESTFrameworkModel):
    some_choices = ((1, 'A'), (2, 'B'), (3, 'C'))
    some_integer = models.PositiveIntegerField(choices=some_choices)


class Anchor(RESTFrameworkModel):
    text = models.CharField(max_length=100, default='anchor')


class BasicModel(RESTFrameworkModel):
    text = models.CharField(max_length=100, verbose_name=_("Text comes here"), help_text=_("Text description."))


class SlugBasedModel(RESTFrameworkModel):
    text = models.CharField(max_length=100)
    slug = models.SlugField(max_length=32)


class DefaultValueModel(RESTFrameworkModel):
    text = models.CharField(default='foobar', max_length=100)
    extra = models.CharField(blank=True, null=True, max_length=100)


class CallableDefaultValueModel(RESTFrameworkModel):
    text = models.CharField(default=foobar, max_length=100)


class ManyToManyModel(RESTFrameworkModel):
    rel = models.ManyToManyField(Anchor, help_text='Some help text.')


class ReadOnlyManyToManyModel(RESTFrameworkModel):
    text = models.CharField(max_length=100, default='anchor')
    rel = models.ManyToManyField(Anchor)


# Model for regression test for #285

class Comment(RESTFrameworkModel):
    email = models.EmailField()
    content = models.CharField(max_length=200)
    created = models.DateTimeField(auto_now_add=True)


class ActionItem(RESTFrameworkModel):
    title = models.CharField(max_length=200)
    started = models.NullBooleanField(default=False)
    done = models.BooleanField(default=False)
    info = CustomField(default='---', max_length=12)


# Models for reverse relations
class Person(RESTFrameworkModel):
    name = models.CharField(max_length=10)
    age = models.IntegerField(null=True, blank=True)

    @property
    def info(self):
        return {
            'name': self.name,
            'age': self.age,
        }


class BlogPost(RESTFrameworkModel):
    title = models.CharField(max_length=100)
    writer = models.ForeignKey(Person, null=True, blank=True)

    def get_first_comment(self):
        return self.blogpostcomment_set.all()[0]


class BlogPostComment(RESTFrameworkModel):
    text = models.TextField()
    blog_post = models.ForeignKey(BlogPost)


class Album(RESTFrameworkModel):
    title = models.CharField(max_length=100, unique=True)
    ref = models.CharField(max_length=10, unique=True, null=True, blank=True)

class Photo(RESTFrameworkModel):
    description = models.TextField()
    album = models.ForeignKey(Album)


# Model for issue #324
class BlankFieldModel(RESTFrameworkModel):
    title = models.CharField(max_length=100, blank=True, null=False)


# Model for issue #380
class OptionalRelationModel(RESTFrameworkModel):
    other = models.ForeignKey('OptionalRelationModel', blank=True, null=True)


# Model for RegexField
class Book(RESTFrameworkModel):
    isbn = models.CharField(max_length=13)


# Models for relations tests
# ManyToMany
class ManyToManyTarget(RESTFrameworkModel):
    name = models.CharField(max_length=100)


class ManyToManySource(RESTFrameworkModel):
    name = models.CharField(max_length=100)
    targets = models.ManyToManyField(ManyToManyTarget, related_name='sources')


# ForeignKey
class ForeignKeyTarget(RESTFrameworkModel):
    name = models.CharField(max_length=100)


class ForeignKeySource(RESTFrameworkModel):
    name = models.CharField(max_length=100)
    target = models.ForeignKey(ForeignKeyTarget, related_name='sources',
                               help_text='Target', verbose_name='Target')


# Nullable ForeignKey
class NullableForeignKeySource(RESTFrameworkModel):
    name = models.CharField(max_length=100)
    target = models.ForeignKey(ForeignKeyTarget, null=True, blank=True,
                               related_name='nullable_sources',
                               verbose_name='Optional target object')


# OneToOne
class OneToOneTarget(RESTFrameworkModel):
    name = models.CharField(max_length=100)


class NullableOneToOneSource(RESTFrameworkModel):
    name = models.CharField(max_length=100)
    target = models.OneToOneField(OneToOneTarget, null=True, blank=True,
                                  related_name='nullable_source')


# Serializer used to test BasicModel
class BasicModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = BasicModel


# Models to test filters
class FilterableItem(models.Model):
    text = models.CharField(max_length=100)
    decimal = models.DecimalField(max_digits=4, decimal_places=2)
    date = models.DateField()

########NEW FILE########
__FILENAME__ = models
from django.db import models


class Record(models.Model):
    account = models.ForeignKey('accounts.Account', blank=True, null=True)
    owner = models.ForeignKey('users.User', blank=True, null=True)

########NEW FILE########
__FILENAME__ = serializers
from rest_framework import serializers

from rest_framework.tests.models import NullableForeignKeySource


class NullableFKSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NullableForeignKeySource

########NEW FILE########
__FILENAME__ = tests
"""
Force import of all modules in this package in order to get the standard test
runner to pick up the tests.  Yowzers.
"""
from __future__ import unicode_literals
import os
import django

modules = [filename.rsplit('.', 1)[0]
           for filename in os.listdir(os.path.dirname(__file__))
           if filename.endswith('.py') and not filename.startswith('_')]
__test__ = dict()

if django.VERSION < (1, 6):
    for module in modules:
        exec("from rest_framework.tests.%s import *" % module)

########NEW FILE########
__FILENAME__ = test_authentication
from __future__ import unicode_literals
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.test import TestCase
from django.utils import unittest
from django.utils.http import urlencode
from rest_framework import HTTP_HEADER_ENCODING
from rest_framework import exceptions
from rest_framework import permissions
from rest_framework import renderers
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import (
    BaseAuthentication,
    TokenAuthentication,
    BasicAuthentication,
    SessionAuthentication,
    OAuthAuthentication,
    OAuth2Authentication
)
from rest_framework.authtoken.models import Token
from rest_framework.compat import patterns, url, include, six
from rest_framework.compat import oauth2_provider, oauth2_provider_scope
from rest_framework.compat import oauth, oauth_provider
from rest_framework.test import APIRequestFactory, APIClient
from rest_framework.views import APIView
import base64
import time
import datetime

factory = APIRequestFactory()


class MockView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return HttpResponse({'a': 1, 'b': 2, 'c': 3})

    def post(self, request):
        return HttpResponse({'a': 1, 'b': 2, 'c': 3})

    def put(self, request):
        return HttpResponse({'a': 1, 'b': 2, 'c': 3})


urlpatterns = patterns('',
    (r'^session/$', MockView.as_view(authentication_classes=[SessionAuthentication])),
    (r'^basic/$', MockView.as_view(authentication_classes=[BasicAuthentication])),
    (r'^token/$', MockView.as_view(authentication_classes=[TokenAuthentication])),
    (r'^auth-token/$', 'rest_framework.authtoken.views.obtain_auth_token'),
    (r'^oauth/$', MockView.as_view(authentication_classes=[OAuthAuthentication])),
    (r'^oauth-with-scope/$', MockView.as_view(authentication_classes=[OAuthAuthentication],
        permission_classes=[permissions.TokenHasReadWriteScope]))
)

class OAuth2AuthenticationDebug(OAuth2Authentication):
    allow_query_params_token = True

if oauth2_provider is not None:
    urlpatterns += patterns('',
        url(r'^oauth2/', include('provider.oauth2.urls', namespace='oauth2')),
        url(r'^oauth2-test/$', MockView.as_view(authentication_classes=[OAuth2Authentication])),
        url(r'^oauth2-test-debug/$', MockView.as_view(authentication_classes=[OAuth2AuthenticationDebug])),
        url(r'^oauth2-with-scope-test/$', MockView.as_view(authentication_classes=[OAuth2Authentication],
            permission_classes=[permissions.TokenHasReadWriteScope])),
    )


class BasicAuthTests(TestCase):
    """Basic authentication"""
    urls = 'rest_framework.tests.test_authentication'

    def setUp(self):
        self.csrf_client = APIClient(enforce_csrf_checks=True)
        self.username = 'john'
        self.email = 'lennon@thebeatles.com'
        self.password = 'password'
        self.user = User.objects.create_user(self.username, self.email, self.password)

    def test_post_form_passing_basic_auth(self):
        """Ensure POSTing json over basic auth with correct credentials passes and does not require CSRF"""
        credentials = ('%s:%s' % (self.username, self.password))
        base64_credentials = base64.b64encode(credentials.encode(HTTP_HEADER_ENCODING)).decode(HTTP_HEADER_ENCODING)
        auth = 'Basic %s' % base64_credentials
        response = self.csrf_client.post('/basic/', {'example': 'example'}, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_json_passing_basic_auth(self):
        """Ensure POSTing form over basic auth with correct credentials passes and does not require CSRF"""
        credentials = ('%s:%s' % (self.username, self.password))
        base64_credentials = base64.b64encode(credentials.encode(HTTP_HEADER_ENCODING)).decode(HTTP_HEADER_ENCODING)
        auth = 'Basic %s' % base64_credentials
        response = self.csrf_client.post('/basic/', {'example': 'example'}, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_form_failing_basic_auth(self):
        """Ensure POSTing form over basic auth without correct credentials fails"""
        response = self.csrf_client.post('/basic/', {'example': 'example'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_post_json_failing_basic_auth(self):
        """Ensure POSTing json over basic auth without correct credentials fails"""
        response = self.csrf_client.post('/basic/', {'example': 'example'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response['WWW-Authenticate'], 'Basic realm="api"')


class SessionAuthTests(TestCase):
    """User session authentication"""
    urls = 'rest_framework.tests.test_authentication'

    def setUp(self):
        self.csrf_client = APIClient(enforce_csrf_checks=True)
        self.non_csrf_client = APIClient(enforce_csrf_checks=False)
        self.username = 'john'
        self.email = 'lennon@thebeatles.com'
        self.password = 'password'
        self.user = User.objects.create_user(self.username, self.email, self.password)

    def tearDown(self):
        self.csrf_client.logout()

    def test_post_form_session_auth_failing_csrf(self):
        """
        Ensure POSTing form over session authentication without CSRF token fails.
        """
        self.csrf_client.login(username=self.username, password=self.password)
        response = self.csrf_client.post('/session/', {'example': 'example'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_form_session_auth_passing(self):
        """
        Ensure POSTing form over session authentication with logged in user and CSRF token passes.
        """
        self.non_csrf_client.login(username=self.username, password=self.password)
        response = self.non_csrf_client.post('/session/', {'example': 'example'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_put_form_session_auth_passing(self):
        """
        Ensure PUTting form over session authentication with logged in user and CSRF token passes.
        """
        self.non_csrf_client.login(username=self.username, password=self.password)
        response = self.non_csrf_client.put('/session/', {'example': 'example'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_form_session_auth_failing(self):
        """
        Ensure POSTing form over session authentication without logged in user fails.
        """
        response = self.csrf_client.post('/session/', {'example': 'example'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TokenAuthTests(TestCase):
    """Token authentication"""
    urls = 'rest_framework.tests.test_authentication'

    def setUp(self):
        self.csrf_client = APIClient(enforce_csrf_checks=True)
        self.username = 'john'
        self.email = 'lennon@thebeatles.com'
        self.password = 'password'
        self.user = User.objects.create_user(self.username, self.email, self.password)

        self.key = 'abcd1234'
        self.token = Token.objects.create(key=self.key, user=self.user)

    def test_post_form_passing_token_auth(self):
        """Ensure POSTing json over token auth with correct credentials passes and does not require CSRF"""
        auth = 'Token ' + self.key
        response = self.csrf_client.post('/token/', {'example': 'example'}, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_json_passing_token_auth(self):
        """Ensure POSTing form over token auth with correct credentials passes and does not require CSRF"""
        auth = "Token " + self.key
        response = self.csrf_client.post('/token/', {'example': 'example'}, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_form_failing_token_auth(self):
        """Ensure POSTing form over token auth without correct credentials fails"""
        response = self.csrf_client.post('/token/', {'example': 'example'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_post_json_failing_token_auth(self):
        """Ensure POSTing json over token auth without correct credentials fails"""
        response = self.csrf_client.post('/token/', {'example': 'example'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_has_auto_assigned_key_if_none_provided(self):
        """Ensure creating a token with no key will auto-assign a key"""
        self.token.delete()
        token = Token.objects.create(user=self.user)
        self.assertTrue(bool(token.key))

    def test_generate_key_returns_string(self):
        """Ensure generate_key returns a string"""
        token = Token()
        key = token.generate_key()
        self.assertTrue(isinstance(key, six.string_types))

    def test_token_login_json(self):
        """Ensure token login view using JSON POST works."""
        client = APIClient(enforce_csrf_checks=True)
        response = client.post('/auth-token/',
                               {'username': self.username, 'password': self.password}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['token'], self.key)

    def test_token_login_json_bad_creds(self):
        """Ensure token login view using JSON POST fails if bad credentials are used."""
        client = APIClient(enforce_csrf_checks=True)
        response = client.post('/auth-token/',
                               {'username': self.username, 'password': "badpass"}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_token_login_json_missing_fields(self):
        """Ensure token login view using JSON POST fails if missing fields."""
        client = APIClient(enforce_csrf_checks=True)
        response = client.post('/auth-token/',
                               {'username': self.username}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_token_login_form(self):
        """Ensure token login view using form POST works."""
        client = APIClient(enforce_csrf_checks=True)
        response = client.post('/auth-token/',
                               {'username': self.username, 'password': self.password})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['token'], self.key)


class IncorrectCredentialsTests(TestCase):
    def test_incorrect_credentials(self):
        """
        If a request contains bad authentication credentials, then
        authentication should run and error, even if no permissions
        are set on the view.
        """
        class IncorrectCredentialsAuth(BaseAuthentication):
            def authenticate(self, request):
                raise exceptions.AuthenticationFailed('Bad credentials')

        request = factory.get('/')
        view = MockView.as_view(
            authentication_classes=(IncorrectCredentialsAuth,),
            permission_classes=()
        )
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data, {'detail': 'Bad credentials'})


class OAuthTests(TestCase):
    """OAuth 1.0a authentication"""
    urls = 'rest_framework.tests.test_authentication'

    def setUp(self):
        # these imports are here because oauth is optional and hiding them in try..except block or compat
        # could obscure problems if something breaks
        from oauth_provider.models import Consumer, Scope
        from oauth_provider.models import Token as OAuthToken
        from oauth_provider import consts

        self.consts = consts

        self.csrf_client = APIClient(enforce_csrf_checks=True)
        self.username = 'john'
        self.email = 'lennon@thebeatles.com'
        self.password = 'password'
        self.user = User.objects.create_user(self.username, self.email, self.password)

        self.CONSUMER_KEY = 'consumer_key'
        self.CONSUMER_SECRET = 'consumer_secret'
        self.TOKEN_KEY = "token_key"
        self.TOKEN_SECRET = "token_secret"

        self.consumer = Consumer.objects.create(key=self.CONSUMER_KEY, secret=self.CONSUMER_SECRET,
            name='example', user=self.user, status=self.consts.ACCEPTED)

        self.scope = Scope.objects.create(name="resource name", url="api/")
        self.token = OAuthToken.objects.create(user=self.user, consumer=self.consumer, scope=self.scope,
            token_type=OAuthToken.ACCESS, key=self.TOKEN_KEY, secret=self.TOKEN_SECRET, is_approved=True
        )

    def _create_authorization_header(self):
        params = {
            'oauth_version': "1.0",
            'oauth_nonce': oauth.generate_nonce(),
            'oauth_timestamp': int(time.time()),
            'oauth_token': self.token.key,
            'oauth_consumer_key': self.consumer.key
        }

        req = oauth.Request(method="GET", url="http://example.com", parameters=params)

        signature_method = oauth.SignatureMethod_PLAINTEXT()
        req.sign_request(signature_method, self.consumer, self.token)

        return req.to_header()["Authorization"]

    def _create_authorization_url_parameters(self):
        params = {
            'oauth_version': "1.0",
            'oauth_nonce': oauth.generate_nonce(),
            'oauth_timestamp': int(time.time()),
            'oauth_token': self.token.key,
            'oauth_consumer_key': self.consumer.key
        }

        req = oauth.Request(method="GET", url="http://example.com", parameters=params)

        signature_method = oauth.SignatureMethod_PLAINTEXT()
        req.sign_request(signature_method, self.consumer, self.token)
        return dict(req)

    @unittest.skipUnless(oauth_provider, 'django-oauth-plus not installed')
    @unittest.skipUnless(oauth, 'oauth2 not installed')
    def test_post_form_passing_oauth(self):
        """Ensure POSTing form over OAuth with correct credentials passes and does not require CSRF"""
        auth = self._create_authorization_header()
        response = self.csrf_client.post('/oauth/', {'example': 'example'}, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 200)

    @unittest.skipUnless(oauth_provider, 'django-oauth-plus not installed')
    @unittest.skipUnless(oauth, 'oauth2 not installed')
    def test_post_form_repeated_nonce_failing_oauth(self):
        """Ensure POSTing form over OAuth with repeated auth (same nonces and timestamp) credentials fails"""
        auth = self._create_authorization_header()
        response = self.csrf_client.post('/oauth/', {'example': 'example'}, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 200)

        # simulate reply attack auth header containes already used (nonce, timestamp) pair
        response = self.csrf_client.post('/oauth/', {'example': 'example'}, HTTP_AUTHORIZATION=auth)
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    @unittest.skipUnless(oauth_provider, 'django-oauth-plus not installed')
    @unittest.skipUnless(oauth, 'oauth2 not installed')
    def test_post_form_token_removed_failing_oauth(self):
        """Ensure POSTing when there is no OAuth access token in db fails"""
        self.token.delete()
        auth = self._create_authorization_header()
        response = self.csrf_client.post('/oauth/', {'example': 'example'}, HTTP_AUTHORIZATION=auth)
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    @unittest.skipUnless(oauth_provider, 'django-oauth-plus not installed')
    @unittest.skipUnless(oauth, 'oauth2 not installed')
    def test_post_form_consumer_status_not_accepted_failing_oauth(self):
        """Ensure POSTing when consumer status is anything other than ACCEPTED fails"""
        for consumer_status in (self.consts.CANCELED, self.consts.PENDING, self.consts.REJECTED):
            self.consumer.status = consumer_status
            self.consumer.save()

            auth = self._create_authorization_header()
            response = self.csrf_client.post('/oauth/', {'example': 'example'}, HTTP_AUTHORIZATION=auth)
            self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    @unittest.skipUnless(oauth_provider, 'django-oauth-plus not installed')
    @unittest.skipUnless(oauth, 'oauth2 not installed')
    def test_post_form_with_request_token_failing_oauth(self):
        """Ensure POSTing with unauthorized request token instead of access token fails"""
        self.token.token_type = self.token.REQUEST
        self.token.save()

        auth = self._create_authorization_header()
        response = self.csrf_client.post('/oauth/', {'example': 'example'}, HTTP_AUTHORIZATION=auth)
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    @unittest.skipUnless(oauth_provider, 'django-oauth-plus not installed')
    @unittest.skipUnless(oauth, 'oauth2 not installed')
    def test_post_form_with_urlencoded_parameters(self):
        """Ensure POSTing with x-www-form-urlencoded auth parameters passes"""
        params = self._create_authorization_url_parameters()
        auth = self._create_authorization_header()
        response = self.csrf_client.post('/oauth/', params, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 200)

    @unittest.skipUnless(oauth_provider, 'django-oauth-plus not installed')
    @unittest.skipUnless(oauth, 'oauth2 not installed')
    def test_get_form_with_url_parameters(self):
        """Ensure GETing with auth in url parameters passes"""
        params = self._create_authorization_url_parameters()
        response = self.csrf_client.get('/oauth/', params)
        self.assertEqual(response.status_code, 200)

    @unittest.skipUnless(oauth_provider, 'django-oauth-plus not installed')
    @unittest.skipUnless(oauth, 'oauth2 not installed')
    def test_post_hmac_sha1_signature_passes(self):
        """Ensure POSTing using HMAC_SHA1 signature method passes"""
        params = {
            'oauth_version': "1.0",
            'oauth_nonce': oauth.generate_nonce(),
            'oauth_timestamp': int(time.time()),
            'oauth_token': self.token.key,
            'oauth_consumer_key': self.consumer.key
        }

        req = oauth.Request(method="POST", url="http://testserver/oauth/", parameters=params)

        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        req.sign_request(signature_method, self.consumer, self.token)
        auth = req.to_header()["Authorization"]

        response = self.csrf_client.post('/oauth/', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 200)

    @unittest.skipUnless(oauth_provider, 'django-oauth-plus not installed')
    @unittest.skipUnless(oauth, 'oauth2 not installed')
    def test_get_form_with_readonly_resource_passing_auth(self):
        """Ensure POSTing with a readonly scope instead of a write scope fails"""
        read_only_access_token = self.token
        read_only_access_token.scope.is_readonly = True
        read_only_access_token.scope.save()
        params = self._create_authorization_url_parameters()
        response = self.csrf_client.get('/oauth-with-scope/', params)
        self.assertEqual(response.status_code, 200)

    @unittest.skipUnless(oauth_provider, 'django-oauth-plus not installed')
    @unittest.skipUnless(oauth, 'oauth2 not installed')
    def test_post_form_with_readonly_resource_failing_auth(self):
        """Ensure POSTing with a readonly resource instead of a write scope fails"""
        read_only_access_token = self.token
        read_only_access_token.scope.is_readonly = True
        read_only_access_token.scope.save()
        params = self._create_authorization_url_parameters()
        response = self.csrf_client.post('/oauth-with-scope/', params)
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    @unittest.skipUnless(oauth_provider, 'django-oauth-plus not installed')
    @unittest.skipUnless(oauth, 'oauth2 not installed')
    def test_post_form_with_write_resource_passing_auth(self):
        """Ensure POSTing with a write resource succeed"""
        read_write_access_token = self.token
        read_write_access_token.scope.is_readonly = False
        read_write_access_token.scope.save()
        params = self._create_authorization_url_parameters()
        auth = self._create_authorization_header()
        response = self.csrf_client.post('/oauth-with-scope/', params, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 200)

    @unittest.skipUnless(oauth_provider, 'django-oauth-plus not installed')
    @unittest.skipUnless(oauth, 'oauth2 not installed')
    def test_bad_consumer_key(self):
        """Ensure POSTing using HMAC_SHA1 signature method passes"""
        params = {
            'oauth_version': "1.0",
            'oauth_nonce': oauth.generate_nonce(),
            'oauth_timestamp': int(time.time()),
            'oauth_token': self.token.key,
            'oauth_consumer_key': 'badconsumerkey'
        }

        req = oauth.Request(method="POST", url="http://testserver/oauth/", parameters=params)

        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        req.sign_request(signature_method, self.consumer, self.token)
        auth = req.to_header()["Authorization"]

        response = self.csrf_client.post('/oauth/', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 401)

    @unittest.skipUnless(oauth_provider, 'django-oauth-plus not installed')
    @unittest.skipUnless(oauth, 'oauth2 not installed')
    def test_bad_token_key(self):
        """Ensure POSTing using HMAC_SHA1 signature method passes"""
        params = {
            'oauth_version': "1.0",
            'oauth_nonce': oauth.generate_nonce(),
            'oauth_timestamp': int(time.time()),
            'oauth_token': 'badtokenkey',
            'oauth_consumer_key': self.consumer.key
        }

        req = oauth.Request(method="POST", url="http://testserver/oauth/", parameters=params)

        signature_method = oauth.SignatureMethod_HMAC_SHA1()
        req.sign_request(signature_method, self.consumer, self.token)
        auth = req.to_header()["Authorization"]

        response = self.csrf_client.post('/oauth/', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 401)


class OAuth2Tests(TestCase):
    """OAuth 2.0 authentication"""
    urls = 'rest_framework.tests.test_authentication'

    def setUp(self):
        self.csrf_client = APIClient(enforce_csrf_checks=True)
        self.username = 'john'
        self.email = 'lennon@thebeatles.com'
        self.password = 'password'
        self.user = User.objects.create_user(self.username, self.email, self.password)

        self.CLIENT_ID = 'client_key'
        self.CLIENT_SECRET = 'client_secret'
        self.ACCESS_TOKEN = "access_token"
        self.REFRESH_TOKEN = "refresh_token"

        self.oauth2_client = oauth2_provider.oauth2.models.Client.objects.create(
                client_id=self.CLIENT_ID,
                client_secret=self.CLIENT_SECRET,
                redirect_uri='',
                client_type=0,
                name='example',
                user=None,
            )

        self.access_token = oauth2_provider.oauth2.models.AccessToken.objects.create(
                token=self.ACCESS_TOKEN,
                client=self.oauth2_client,
                user=self.user,
            )
        self.refresh_token = oauth2_provider.oauth2.models.RefreshToken.objects.create(
                user=self.user,
                access_token=self.access_token,
                client=self.oauth2_client
            )

    def _create_authorization_header(self, token=None):
        return "Bearer {0}".format(token or self.access_token.token)

    @unittest.skipUnless(oauth2_provider, 'django-oauth2-provider not installed')
    def test_get_form_with_wrong_authorization_header_token_type_failing(self):
        """Ensure that a wrong token type lead to the correct HTTP error status code"""
        auth = "Wrong token-type-obsviously"
        response = self.csrf_client.get('/oauth2-test/', {}, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 401)
        response = self.csrf_client.get('/oauth2-test/', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 401)

    @unittest.skipUnless(oauth2_provider, 'django-oauth2-provider not installed')
    def test_get_form_with_wrong_authorization_header_token_format_failing(self):
        """Ensure that a wrong token format lead to the correct HTTP error status code"""
        auth = "Bearer wrong token format"
        response = self.csrf_client.get('/oauth2-test/', {}, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 401)
        response = self.csrf_client.get('/oauth2-test/', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 401)

    @unittest.skipUnless(oauth2_provider, 'django-oauth2-provider not installed')
    def test_get_form_with_wrong_authorization_header_token_failing(self):
        """Ensure that a wrong token lead to the correct HTTP error status code"""
        auth = "Bearer wrong-token"
        response = self.csrf_client.get('/oauth2-test/', {}, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 401)
        response = self.csrf_client.get('/oauth2-test/', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 401)

    @unittest.skipUnless(oauth2_provider, 'django-oauth2-provider not installed')
    def test_get_form_passing_auth(self):
        """Ensure GETing form over OAuth with correct client credentials succeed"""
        auth = self._create_authorization_header()
        response = self.csrf_client.get('/oauth2-test/', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 200)

    @unittest.skipUnless(oauth2_provider, 'django-oauth2-provider not installed')
    def test_post_form_passing_auth_url_transport(self):
        """Ensure GETing form over OAuth with correct client credentials in form data succeed"""
        response = self.csrf_client.post('/oauth2-test/',
                data={'access_token': self.access_token.token})
        self.assertEqual(response.status_code, 200)

    @unittest.skipUnless(oauth2_provider, 'django-oauth2-provider not installed')
    def test_get_form_passing_auth_url_transport(self):
        """Ensure GETing form over OAuth with correct client credentials in query succeed when DEBUG is True"""
        query = urlencode({'access_token': self.access_token.token})
        response = self.csrf_client.get('/oauth2-test-debug/?%s' % query)
        self.assertEqual(response.status_code, 200)

    @unittest.skipUnless(oauth2_provider, 'django-oauth2-provider not installed')
    def test_get_form_failing_auth_url_transport(self):
        """Ensure GETing form over OAuth with correct client credentials in query fails when DEBUG is False"""
        query = urlencode({'access_token': self.access_token.token})
        response = self.csrf_client.get('/oauth2-test/?%s' % query)
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    @unittest.skipUnless(oauth2_provider, 'django-oauth2-provider not installed')
    def test_post_form_passing_auth(self):
        """Ensure POSTing form over OAuth with correct credentials passes and does not require CSRF"""
        auth = self._create_authorization_header()
        response = self.csrf_client.post('/oauth2-test/', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 200)

    @unittest.skipUnless(oauth2_provider, 'django-oauth2-provider not installed')
    def test_post_form_token_removed_failing_auth(self):
        """Ensure POSTing when there is no OAuth access token in db fails"""
        self.access_token.delete()
        auth = self._create_authorization_header()
        response = self.csrf_client.post('/oauth2-test/', HTTP_AUTHORIZATION=auth)
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    @unittest.skipUnless(oauth2_provider, 'django-oauth2-provider not installed')
    def test_post_form_with_refresh_token_failing_auth(self):
        """Ensure POSTing with refresh token instead of access token fails"""
        auth = self._create_authorization_header(token=self.refresh_token.token)
        response = self.csrf_client.post('/oauth2-test/', HTTP_AUTHORIZATION=auth)
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    @unittest.skipUnless(oauth2_provider, 'django-oauth2-provider not installed')
    def test_post_form_with_expired_access_token_failing_auth(self):
        """Ensure POSTing with expired access token fails with an 'Invalid token' error"""
        self.access_token.expires = datetime.datetime.now() - datetime.timedelta(seconds=10)  # 10 seconds late
        self.access_token.save()
        auth = self._create_authorization_header()
        response = self.csrf_client.post('/oauth2-test/', HTTP_AUTHORIZATION=auth)
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
        self.assertIn('Invalid token', response.content)

    @unittest.skipUnless(oauth2_provider, 'django-oauth2-provider not installed')
    def test_post_form_with_invalid_scope_failing_auth(self):
        """Ensure POSTing with a readonly scope instead of a write scope fails"""
        read_only_access_token = self.access_token
        read_only_access_token.scope = oauth2_provider_scope.SCOPE_NAME_DICT['read']
        read_only_access_token.save()
        auth = self._create_authorization_header(token=read_only_access_token.token)
        response = self.csrf_client.get('/oauth2-with-scope-test/', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 200)
        response = self.csrf_client.post('/oauth2-with-scope-test/', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @unittest.skipUnless(oauth2_provider, 'django-oauth2-provider not installed')
    def test_post_form_with_valid_scope_passing_auth(self):
        """Ensure POSTing with a write scope succeed"""
        read_write_access_token = self.access_token
        read_write_access_token.scope = oauth2_provider_scope.SCOPE_NAME_DICT['write']
        read_write_access_token.save()
        auth = self._create_authorization_header(token=read_write_access_token.token)
        response = self.csrf_client.post('/oauth2-with-scope-test/', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, 200)


class FailingAuthAccessedInRenderer(TestCase):
    def setUp(self):
        class AuthAccessingRenderer(renderers.BaseRenderer):
            media_type = 'text/plain'
            format = 'txt'

            def render(self, data, media_type=None, renderer_context=None):
                request = renderer_context['request']
                if request.user.is_authenticated():
                    return b'authenticated'
                return b'not authenticated'

        class FailingAuth(BaseAuthentication):
            def authenticate(self, request):
                raise exceptions.AuthenticationFailed('authentication failed')

        class ExampleView(APIView):
            authentication_classes = (FailingAuth,)
            renderer_classes = (AuthAccessingRenderer,)

            def get(self, request):
                return Response({'foo': 'bar'})

        self.view = ExampleView.as_view()

    def test_failing_auth_accessed_in_renderer(self):
        """
        When authentication fails the renderer should still be able to access
        `request.user` without raising an exception. Particularly relevant
        to HTML responses that might reasonably access `request.user`.
        """
        request = factory.get('/')
        response = self.view(request)
        content = response.render().content
        self.assertEqual(content, b'not authenticated')

########NEW FILE########
__FILENAME__ = test_breadcrumbs
from __future__ import unicode_literals
from django.test import TestCase
from rest_framework.compat import patterns, url
from rest_framework.utils.breadcrumbs import get_breadcrumbs
from rest_framework.views import APIView


class Root(APIView):
    pass


class ResourceRoot(APIView):
    pass


class ResourceInstance(APIView):
    pass


class NestedResourceRoot(APIView):
    pass


class NestedResourceInstance(APIView):
    pass

urlpatterns = patterns('',
    url(r'^$', Root.as_view()),
    url(r'^resource/$', ResourceRoot.as_view()),
    url(r'^resource/(?P<key>[0-9]+)$', ResourceInstance.as_view()),
    url(r'^resource/(?P<key>[0-9]+)/$', NestedResourceRoot.as_view()),
    url(r'^resource/(?P<key>[0-9]+)/(?P<other>[A-Za-z]+)$', NestedResourceInstance.as_view()),
)


class BreadcrumbTests(TestCase):
    """Tests the breadcrumb functionality used by the HTML renderer."""

    urls = 'rest_framework.tests.test_breadcrumbs'

    def test_root_breadcrumbs(self):
        url = '/'
        self.assertEqual(get_breadcrumbs(url), [('Root', '/')])

    def test_resource_root_breadcrumbs(self):
        url = '/resource/'
        self.assertEqual(get_breadcrumbs(url), [('Root', '/'),
                                            ('Resource Root', '/resource/')])

    def test_resource_instance_breadcrumbs(self):
        url = '/resource/123'
        self.assertEqual(get_breadcrumbs(url), [('Root', '/'),
                                            ('Resource Root', '/resource/'),
                                            ('Resource Instance', '/resource/123')])

    def test_nested_resource_breadcrumbs(self):
        url = '/resource/123/'
        self.assertEqual(get_breadcrumbs(url), [('Root', '/'),
                                            ('Resource Root', '/resource/'),
                                            ('Resource Instance', '/resource/123'),
                                            ('Nested Resource Root', '/resource/123/')])

    def test_nested_resource_instance_breadcrumbs(self):
        url = '/resource/123/abc'
        self.assertEqual(get_breadcrumbs(url), [('Root', '/'),
                                            ('Resource Root', '/resource/'),
                                            ('Resource Instance', '/resource/123'),
                                            ('Nested Resource Root', '/resource/123/'),
                                            ('Nested Resource Instance', '/resource/123/abc')])

    def test_broken_url_breadcrumbs_handled_gracefully(self):
        url = '/foobar'
        self.assertEqual(get_breadcrumbs(url), [('Root', '/')])

########NEW FILE########
__FILENAME__ = test_decorators
from __future__ import unicode_literals
from django.test import TestCase
from rest_framework import status
from rest_framework.authentication import BasicAuthentication
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.test import APIRequestFactory
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView
from rest_framework.decorators import (
    api_view,
    renderer_classes,
    parser_classes,
    authentication_classes,
    throttle_classes,
    permission_classes,
)


class DecoratorTestCase(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()

    def _finalize_response(self, request, response, *args, **kwargs):
        response.request = request
        return APIView.finalize_response(self, request, response, *args, **kwargs)

    def test_api_view_incorrect(self):
        """
        If @api_view is not applied correct, we should raise an assertion.
        """

        @api_view
        def view(request):
            return Response()

        request = self.factory.get('/')
        self.assertRaises(AssertionError, view, request)

    def test_api_view_incorrect_arguments(self):
        """
        If @api_view is missing arguments, we should raise an assertion.
        """

        with self.assertRaises(AssertionError):
            @api_view('GET')
            def view(request):
                return Response()

    def test_calling_method(self):

        @api_view(['GET'])
        def view(request):
            return Response({})

        request = self.factory.get('/')
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        request = self.factory.post('/')
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_calling_put_method(self):

        @api_view(['GET', 'PUT'])
        def view(request):
            return Response({})

        request = self.factory.put('/')
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        request = self.factory.post('/')
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_calling_patch_method(self):

        @api_view(['GET', 'PATCH'])
        def view(request):
            return Response({})

        request = self.factory.patch('/')
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        request = self.factory.post('/')
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_renderer_classes(self):

        @api_view(['GET'])
        @renderer_classes([JSONRenderer])
        def view(request):
            return Response({})

        request = self.factory.get('/')
        response = view(request)
        self.assertTrue(isinstance(response.accepted_renderer, JSONRenderer))

    def test_parser_classes(self):

        @api_view(['GET'])
        @parser_classes([JSONParser])
        def view(request):
            self.assertEqual(len(request.parsers), 1)
            self.assertTrue(isinstance(request.parsers[0],
                                       JSONParser))
            return Response({})

        request = self.factory.get('/')
        view(request)

    def test_authentication_classes(self):

        @api_view(['GET'])
        @authentication_classes([BasicAuthentication])
        def view(request):
            self.assertEqual(len(request.authenticators), 1)
            self.assertTrue(isinstance(request.authenticators[0],
                                       BasicAuthentication))
            return Response({})

        request = self.factory.get('/')
        view(request)

    def test_permission_classes(self):

        @api_view(['GET'])
        @permission_classes([IsAuthenticated])
        def view(request):
            return Response({})

        request = self.factory.get('/')
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_throttle_classes(self):
        class OncePerDayUserThrottle(UserRateThrottle):
            rate = '1/day'

        @api_view(['GET'])
        @throttle_classes([OncePerDayUserThrottle])
        def view(request):
            return Response({})

        request = self.factory.get('/')
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

########NEW FILE########
__FILENAME__ = test_description
# -- coding: utf-8 --

from __future__ import unicode_literals
from django.test import TestCase
from rest_framework.compat import apply_markdown, smart_text
from rest_framework.views import APIView
from rest_framework.tests.description import ViewWithNonASCIICharactersInDocstring
from rest_framework.tests.description import UTF8_TEST_DOCSTRING

# We check that docstrings get nicely un-indented.
DESCRIPTION = """an example docstring
====================

* list
* list

another header
--------------

    code block

indented

# hash style header #"""

# If markdown is installed we also test it's working
# (and that our wrapped forces '=' to h2 and '-' to h3)

# We support markdown < 2.1 and markdown >= 2.1
MARKED_DOWN_lt_21 = """<h2>an example docstring</h2>
<ul>
<li>list</li>
<li>list</li>
</ul>
<h3>another header</h3>
<pre><code>code block
</code></pre>
<p>indented</p>
<h2 id="hash_style_header">hash style header</h2>"""

MARKED_DOWN_gte_21 = """<h2 id="an-example-docstring">an example docstring</h2>
<ul>
<li>list</li>
<li>list</li>
</ul>
<h3 id="another-header">another header</h3>
<pre><code>code block
</code></pre>
<p>indented</p>
<h2 id="hash-style-header">hash style header</h2>"""


class TestViewNamesAndDescriptions(TestCase):
    def test_view_name_uses_class_name(self):
        """
        Ensure view names are based on the class name.
        """
        class MockView(APIView):
            pass
        self.assertEqual(MockView().get_view_name(), 'Mock')

    def test_view_description_uses_docstring(self):
        """Ensure view descriptions are based on the docstring."""
        class MockView(APIView):
            """an example docstring
            ====================

            * list
            * list

            another header
            --------------

                code block

            indented

            # hash style header #"""

        self.assertEqual(MockView().get_view_description(), DESCRIPTION)

    def test_view_description_supports_unicode(self):
        """
        Unicode in docstrings should be respected.
        """

        self.assertEqual(
            ViewWithNonASCIICharactersInDocstring().get_view_description(),
            smart_text(UTF8_TEST_DOCSTRING)
        )

    def test_view_description_can_be_empty(self):
        """
        Ensure that if a view has no docstring,
        then it's description is the empty string.
        """
        class MockView(APIView):
            pass
        self.assertEqual(MockView().get_view_description(), '')

    def test_markdown(self):
        """
        Ensure markdown to HTML works as expected.
        """
        if apply_markdown:
            gte_21_match = apply_markdown(DESCRIPTION) == MARKED_DOWN_gte_21
            lt_21_match = apply_markdown(DESCRIPTION) == MARKED_DOWN_lt_21
            self.assertTrue(gte_21_match or lt_21_match)

########NEW FILE########
__FILENAME__ = test_fields
"""
General serializer field tests.
"""
from __future__ import unicode_literals

import datetime
import re
from decimal import Decimal
from uuid import uuid4
from django.core import validators
from django.db import models
from django.test import TestCase
from django.utils.datastructures import SortedDict
from rest_framework import serializers
from rest_framework.tests.models import RESTFrameworkModel


class TimestampedModel(models.Model):
    added = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)


class CharPrimaryKeyModel(models.Model):
    id = models.CharField(max_length=20, primary_key=True)


class TimestampedModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimestampedModel


class CharPrimaryKeyModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CharPrimaryKeyModel


class TimeFieldModel(models.Model):
    clock = models.TimeField()


class TimeFieldModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeFieldModel


SAMPLE_CHOICES = [
    ('red', 'Red'),
    ('green', 'Green'),
    ('blue', 'Blue'),
]


class ChoiceFieldModel(models.Model):
    choice = models.CharField(choices=SAMPLE_CHOICES, blank=True, max_length=255)


class ChoiceFieldModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChoiceFieldModel


class ChoiceFieldModelWithNull(models.Model):
    choice = models.CharField(choices=SAMPLE_CHOICES, blank=True, null=True, max_length=255)


class ChoiceFieldModelWithNullSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChoiceFieldModelWithNull


class BasicFieldTests(TestCase):
    def test_auto_now_fields_read_only(self):
        """
        auto_now and auto_now_add fields should be read_only by default.
        """
        serializer = TimestampedModelSerializer()
        self.assertEqual(serializer.fields['added'].read_only, True)

    def test_auto_pk_fields_read_only(self):
        """
        AutoField fields should be read_only by default.
        """
        serializer = TimestampedModelSerializer()
        self.assertEqual(serializer.fields['id'].read_only, True)

    def test_non_auto_pk_fields_not_read_only(self):
        """
        PK fields other than AutoField fields should not be read_only by default.
        """
        serializer = CharPrimaryKeyModelSerializer()
        self.assertEqual(serializer.fields['id'].read_only, False)

    def test_dict_field_ordering(self):
        """
        Field should preserve dictionary ordering, if it exists.
        See: https://github.com/tomchristie/django-rest-framework/issues/832
        """
        ret = SortedDict()
        ret['c'] = 1
        ret['b'] = 1
        ret['a'] = 1
        ret['z'] = 1
        field = serializers.Field()
        keys = list(field.to_native(ret).keys())
        self.assertEqual(keys, ['c', 'b', 'a', 'z'])

    def test_widget_html_attributes(self):
        """
        Make sure widget_html() renders the correct attributes
        """
        r = re.compile('(\S+)=["\']?((?:.(?!["\']?\s+(?:\S+)=|[>"\']))+.)["\']?')
        form = TimeFieldModelSerializer().data
        attributes = r.findall(form.fields['clock'].widget_html())
        self.assertIn(('name', 'clock'), attributes)
        self.assertIn(('id', 'clock'), attributes)


class DateFieldTest(TestCase):
    """
    Tests for the DateFieldTest from_native() and to_native() behavior
    """

    def test_from_native_string(self):
        """
        Make sure from_native() accepts default iso input formats.
        """
        f = serializers.DateField()
        result_1 = f.from_native('1984-07-31')

        self.assertEqual(datetime.date(1984, 7, 31), result_1)

    def test_from_native_datetime_date(self):
        """
        Make sure from_native() accepts a datetime.date instance.
        """
        f = serializers.DateField()
        result_1 = f.from_native(datetime.date(1984, 7, 31))

        self.assertEqual(result_1, datetime.date(1984, 7, 31))

    def test_from_native_custom_format(self):
        """
        Make sure from_native() accepts custom input formats.
        """
        f = serializers.DateField(input_formats=['%Y -- %d'])
        result = f.from_native('1984 -- 31')

        self.assertEqual(datetime.date(1984, 1, 31), result)

    def test_from_native_invalid_default_on_custom_format(self):
        """
        Make sure from_native() don't accept default formats if custom format is preset
        """
        f = serializers.DateField(input_formats=['%Y -- %d'])

        try:
            f.from_native('1984-07-31')
        except validators.ValidationError as e:
            self.assertEqual(e.messages, ["Date has wrong format. Use one of these formats instead: YYYY -- DD"])
        else:
            self.fail("ValidationError was not properly raised")

    def test_from_native_empty(self):
        """
        Make sure from_native() returns None on empty param.
        """
        f = serializers.DateField()
        result = f.from_native('')

        self.assertEqual(result, None)

    def test_from_native_none(self):
        """
        Make sure from_native() returns None on None param.
        """
        f = serializers.DateField()
        result = f.from_native(None)

        self.assertEqual(result, None)

    def test_from_native_invalid_date(self):
        """
        Make sure from_native() raises a ValidationError on passing an invalid date.
        """
        f = serializers.DateField()

        try:
            f.from_native('1984-13-31')
        except validators.ValidationError as e:
            self.assertEqual(e.messages, ["Date has wrong format. Use one of these formats instead: YYYY[-MM[-DD]]"])
        else:
            self.fail("ValidationError was not properly raised")

    def test_from_native_invalid_format(self):
        """
        Make sure from_native() raises a ValidationError on passing an invalid format.
        """
        f = serializers.DateField()

        try:
            f.from_native('1984 -- 31')
        except validators.ValidationError as e:
            self.assertEqual(e.messages, ["Date has wrong format. Use one of these formats instead: YYYY[-MM[-DD]]"])
        else:
            self.fail("ValidationError was not properly raised")

    def test_to_native(self):
        """
        Make sure to_native() returns datetime as default.
        """
        f = serializers.DateField()

        result_1 = f.to_native(datetime.date(1984, 7, 31))

        self.assertEqual(datetime.date(1984, 7, 31), result_1)

    def test_to_native_iso(self):
        """
        Make sure to_native() with 'iso-8601' returns iso formated date.
        """
        f = serializers.DateField(format='iso-8601')

        result_1 = f.to_native(datetime.date(1984, 7, 31))

        self.assertEqual('1984-07-31', result_1)

    def test_to_native_custom_format(self):
        """
        Make sure to_native() returns correct custom format.
        """
        f = serializers.DateField(format="%Y - %m.%d")

        result_1 = f.to_native(datetime.date(1984, 7, 31))

        self.assertEqual('1984 - 07.31', result_1)

    def test_to_native_none(self):
        """
        Make sure from_native() returns None on None param.
        """
        f = serializers.DateField(required=False)
        self.assertEqual(None, f.to_native(None))


class DateTimeFieldTest(TestCase):
    """
    Tests for the DateTimeField from_native() and to_native() behavior
    """

    def test_from_native_string(self):
        """
        Make sure from_native() accepts default iso input formats.
        """
        f = serializers.DateTimeField()
        result_1 = f.from_native('1984-07-31 04:31')
        result_2 = f.from_native('1984-07-31 04:31:59')
        result_3 = f.from_native('1984-07-31 04:31:59.000200')

        self.assertEqual(datetime.datetime(1984, 7, 31, 4, 31), result_1)
        self.assertEqual(datetime.datetime(1984, 7, 31, 4, 31, 59), result_2)
        self.assertEqual(datetime.datetime(1984, 7, 31, 4, 31, 59, 200), result_3)

    def test_from_native_datetime_datetime(self):
        """
        Make sure from_native() accepts a datetime.datetime instance.
        """
        f = serializers.DateTimeField()
        result_1 = f.from_native(datetime.datetime(1984, 7, 31, 4, 31))
        result_2 = f.from_native(datetime.datetime(1984, 7, 31, 4, 31, 59))
        result_3 = f.from_native(datetime.datetime(1984, 7, 31, 4, 31, 59, 200))

        self.assertEqual(result_1, datetime.datetime(1984, 7, 31, 4, 31))
        self.assertEqual(result_2, datetime.datetime(1984, 7, 31, 4, 31, 59))
        self.assertEqual(result_3, datetime.datetime(1984, 7, 31, 4, 31, 59, 200))

    def test_from_native_custom_format(self):
        """
        Make sure from_native() accepts custom input formats.
        """
        f = serializers.DateTimeField(input_formats=['%Y -- %H:%M'])
        result = f.from_native('1984 -- 04:59')

        self.assertEqual(datetime.datetime(1984, 1, 1, 4, 59), result)

    def test_from_native_invalid_default_on_custom_format(self):
        """
        Make sure from_native() don't accept default formats if custom format is preset
        """
        f = serializers.DateTimeField(input_formats=['%Y -- %H:%M'])

        try:
            f.from_native('1984-07-31 04:31:59')
        except validators.ValidationError as e:
            self.assertEqual(e.messages, ["Datetime has wrong format. Use one of these formats instead: YYYY -- hh:mm"])
        else:
            self.fail("ValidationError was not properly raised")

    def test_from_native_empty(self):
        """
        Make sure from_native() returns None on empty param.
        """
        f = serializers.DateTimeField()
        result = f.from_native('')

        self.assertEqual(result, None)

    def test_from_native_none(self):
        """
        Make sure from_native() returns None on None param.
        """
        f = serializers.DateTimeField()
        result = f.from_native(None)

        self.assertEqual(result, None)

    def test_from_native_invalid_datetime(self):
        """
        Make sure from_native() raises a ValidationError on passing an invalid datetime.
        """
        f = serializers.DateTimeField()

        try:
            f.from_native('04:61:59')
        except validators.ValidationError as e:
            self.assertEqual(e.messages, ["Datetime has wrong format. Use one of these formats instead: "
                                          "YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z]"])
        else:
            self.fail("ValidationError was not properly raised")

    def test_from_native_invalid_format(self):
        """
        Make sure from_native() raises a ValidationError on passing an invalid format.
        """
        f = serializers.DateTimeField()

        try:
            f.from_native('04 -- 31')
        except validators.ValidationError as e:
            self.assertEqual(e.messages, ["Datetime has wrong format. Use one of these formats instead: "
                                          "YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z]"])
        else:
            self.fail("ValidationError was not properly raised")

    def test_to_native(self):
        """
        Make sure to_native() returns isoformat as default.
        """
        f = serializers.DateTimeField()

        result_1 = f.to_native(datetime.datetime(1984, 7, 31))
        result_2 = f.to_native(datetime.datetime(1984, 7, 31, 4, 31))
        result_3 = f.to_native(datetime.datetime(1984, 7, 31, 4, 31, 59))
        result_4 = f.to_native(datetime.datetime(1984, 7, 31, 4, 31, 59, 200))

        self.assertEqual(datetime.datetime(1984, 7, 31), result_1)
        self.assertEqual(datetime.datetime(1984, 7, 31, 4, 31), result_2)
        self.assertEqual(datetime.datetime(1984, 7, 31, 4, 31, 59), result_3)
        self.assertEqual(datetime.datetime(1984, 7, 31, 4, 31, 59, 200), result_4)

    def test_to_native_iso(self):
        """
        Make sure to_native() with format=iso-8601 returns iso formatted datetime.
        """
        f = serializers.DateTimeField(format='iso-8601')

        result_1 = f.to_native(datetime.datetime(1984, 7, 31))
        result_2 = f.to_native(datetime.datetime(1984, 7, 31, 4, 31))
        result_3 = f.to_native(datetime.datetime(1984, 7, 31, 4, 31, 59))
        result_4 = f.to_native(datetime.datetime(1984, 7, 31, 4, 31, 59, 200))

        self.assertEqual('1984-07-31T00:00:00', result_1)
        self.assertEqual('1984-07-31T04:31:00', result_2)
        self.assertEqual('1984-07-31T04:31:59', result_3)
        self.assertEqual('1984-07-31T04:31:59.000200', result_4)

    def test_to_native_custom_format(self):
        """
        Make sure to_native() returns correct custom format.
        """
        f = serializers.DateTimeField(format="%Y - %H:%M")

        result_1 = f.to_native(datetime.datetime(1984, 7, 31))
        result_2 = f.to_native(datetime.datetime(1984, 7, 31, 4, 31))
        result_3 = f.to_native(datetime.datetime(1984, 7, 31, 4, 31, 59))
        result_4 = f.to_native(datetime.datetime(1984, 7, 31, 4, 31, 59, 200))

        self.assertEqual('1984 - 00:00', result_1)
        self.assertEqual('1984 - 04:31', result_2)
        self.assertEqual('1984 - 04:31', result_3)
        self.assertEqual('1984 - 04:31', result_4)

    def test_to_native_none(self):
        """
        Make sure from_native() returns None on None param.
        """
        f = serializers.DateTimeField(required=False)
        self.assertEqual(None, f.to_native(None))


class TimeFieldTest(TestCase):
    """
    Tests for the TimeField from_native() and to_native() behavior
    """

    def test_from_native_string(self):
        """
        Make sure from_native() accepts default iso input formats.
        """
        f = serializers.TimeField()
        result_1 = f.from_native('04:31')
        result_2 = f.from_native('04:31:59')
        result_3 = f.from_native('04:31:59.000200')

        self.assertEqual(datetime.time(4, 31), result_1)
        self.assertEqual(datetime.time(4, 31, 59), result_2)
        self.assertEqual(datetime.time(4, 31, 59, 200), result_3)

    def test_from_native_datetime_time(self):
        """
        Make sure from_native() accepts a datetime.time instance.
        """
        f = serializers.TimeField()
        result_1 = f.from_native(datetime.time(4, 31))
        result_2 = f.from_native(datetime.time(4, 31, 59))
        result_3 = f.from_native(datetime.time(4, 31, 59, 200))

        self.assertEqual(result_1, datetime.time(4, 31))
        self.assertEqual(result_2, datetime.time(4, 31, 59))
        self.assertEqual(result_3, datetime.time(4, 31, 59, 200))

    def test_from_native_custom_format(self):
        """
        Make sure from_native() accepts custom input formats.
        """
        f = serializers.TimeField(input_formats=['%H -- %M'])
        result = f.from_native('04 -- 31')

        self.assertEqual(datetime.time(4, 31), result)

    def test_from_native_invalid_default_on_custom_format(self):
        """
        Make sure from_native() don't accept default formats if custom format is preset
        """
        f = serializers.TimeField(input_formats=['%H -- %M'])

        try:
            f.from_native('04:31:59')
        except validators.ValidationError as e:
            self.assertEqual(e.messages, ["Time has wrong format. Use one of these formats instead: hh -- mm"])
        else:
            self.fail("ValidationError was not properly raised")

    def test_from_native_empty(self):
        """
        Make sure from_native() returns None on empty param.
        """
        f = serializers.TimeField()
        result = f.from_native('')

        self.assertEqual(result, None)

    def test_from_native_none(self):
        """
        Make sure from_native() returns None on None param.
        """
        f = serializers.TimeField()
        result = f.from_native(None)

        self.assertEqual(result, None)

    def test_from_native_invalid_time(self):
        """
        Make sure from_native() raises a ValidationError on passing an invalid time.
        """
        f = serializers.TimeField()

        try:
            f.from_native('04:61:59')
        except validators.ValidationError as e:
            self.assertEqual(e.messages, ["Time has wrong format. Use one of these formats instead: "
                                          "hh:mm[:ss[.uuuuuu]]"])
        else:
            self.fail("ValidationError was not properly raised")

    def test_from_native_invalid_format(self):
        """
        Make sure from_native() raises a ValidationError on passing an invalid format.
        """
        f = serializers.TimeField()

        try:
            f.from_native('04 -- 31')
        except validators.ValidationError as e:
            self.assertEqual(e.messages, ["Time has wrong format. Use one of these formats instead: "
                                          "hh:mm[:ss[.uuuuuu]]"])
        else:
            self.fail("ValidationError was not properly raised")

    def test_to_native(self):
        """
        Make sure to_native() returns time object as default.
        """
        f = serializers.TimeField()
        result_1 = f.to_native(datetime.time(4, 31))
        result_2 = f.to_native(datetime.time(4, 31, 59))
        result_3 = f.to_native(datetime.time(4, 31, 59, 200))

        self.assertEqual(datetime.time(4, 31), result_1)
        self.assertEqual(datetime.time(4, 31, 59), result_2)
        self.assertEqual(datetime.time(4, 31, 59, 200), result_3)

    def test_to_native_iso(self):
        """
        Make sure to_native() with format='iso-8601' returns iso formatted time.
        """
        f = serializers.TimeField(format='iso-8601')
        result_1 = f.to_native(datetime.time(4, 31))
        result_2 = f.to_native(datetime.time(4, 31, 59))
        result_3 = f.to_native(datetime.time(4, 31, 59, 200))

        self.assertEqual('04:31:00', result_1)
        self.assertEqual('04:31:59', result_2)
        self.assertEqual('04:31:59.000200', result_3)

    def test_to_native_custom_format(self):
        """
        Make sure to_native() returns correct custom format.
        """
        f = serializers.TimeField(format="%H - %S [%f]")
        result_1 = f.to_native(datetime.time(4, 31))
        result_2 = f.to_native(datetime.time(4, 31, 59))
        result_3 = f.to_native(datetime.time(4, 31, 59, 200))

        self.assertEqual('04 - 00 [000000]', result_1)
        self.assertEqual('04 - 59 [000000]', result_2)
        self.assertEqual('04 - 59 [000200]', result_3)


class DecimalFieldTest(TestCase):
    """
    Tests for the DecimalField from_native() and to_native() behavior
    """

    def test_from_native_string(self):
        """
        Make sure from_native() accepts string values
        """
        f = serializers.DecimalField()
        result_1 = f.from_native('9000')
        result_2 = f.from_native('1.00000001')

        self.assertEqual(Decimal('9000'), result_1)
        self.assertEqual(Decimal('1.00000001'), result_2)

    def test_from_native_invalid_string(self):
        """
        Make sure from_native() raises ValidationError on passing invalid string
        """
        f = serializers.DecimalField()

        try:
            f.from_native('123.45.6')
        except validators.ValidationError as e:
            self.assertEqual(e.messages, ["Enter a number."])
        else:
            self.fail("ValidationError was not properly raised")

    def test_from_native_integer(self):
        """
        Make sure from_native() accepts integer values
        """
        f = serializers.DecimalField()
        result = f.from_native(9000)

        self.assertEqual(Decimal('9000'), result)

    def test_from_native_float(self):
        """
        Make sure from_native() accepts float values
        """
        f = serializers.DecimalField()
        result = f.from_native(1.00000001)

        self.assertEqual(Decimal('1.00000001'), result)

    def test_from_native_empty(self):
        """
        Make sure from_native() returns None on empty param.
        """
        f = serializers.DecimalField()
        result = f.from_native('')

        self.assertEqual(result, None)

    def test_from_native_none(self):
        """
        Make sure from_native() returns None on None param.
        """
        f = serializers.DecimalField()
        result = f.from_native(None)

        self.assertEqual(result, None)

    def test_to_native(self):
        """
        Make sure to_native() returns Decimal as string.
        """
        f = serializers.DecimalField()

        result_1 = f.to_native(Decimal('9000'))
        result_2 = f.to_native(Decimal('1.00000001'))

        self.assertEqual(Decimal('9000'), result_1)
        self.assertEqual(Decimal('1.00000001'), result_2)

    def test_to_native_none(self):
        """
        Make sure from_native() returns None on None param.
        """
        f = serializers.DecimalField(required=False)
        self.assertEqual(None, f.to_native(None))

    def test_valid_serialization(self):
        """
        Make sure the serializer works correctly
        """
        class DecimalSerializer(serializers.Serializer):
            decimal_field = serializers.DecimalField(max_value=9010,
                                                     min_value=9000,
                                                     max_digits=6,
                                                     decimal_places=2)

        self.assertTrue(DecimalSerializer(data={'decimal_field': '9001'}).is_valid())
        self.assertTrue(DecimalSerializer(data={'decimal_field': '9001.2'}).is_valid())
        self.assertTrue(DecimalSerializer(data={'decimal_field': '9001.23'}).is_valid())

        self.assertFalse(DecimalSerializer(data={'decimal_field': '8000'}).is_valid())
        self.assertFalse(DecimalSerializer(data={'decimal_field': '9900'}).is_valid())
        self.assertFalse(DecimalSerializer(data={'decimal_field': '9001.234'}).is_valid())

    def test_raise_max_value(self):
        """
        Make sure max_value violations raises ValidationError
        """
        class DecimalSerializer(serializers.Serializer):
            decimal_field = serializers.DecimalField(max_value=100)

        s = DecimalSerializer(data={'decimal_field': '123'})

        self.assertFalse(s.is_valid())
        self.assertEqual(s.errors,  {'decimal_field': ['Ensure this value is less than or equal to 100.']})

    def test_raise_min_value(self):
        """
        Make sure min_value violations raises ValidationError
        """
        class DecimalSerializer(serializers.Serializer):
            decimal_field = serializers.DecimalField(min_value=100)

        s = DecimalSerializer(data={'decimal_field': '99'})

        self.assertFalse(s.is_valid())
        self.assertEqual(s.errors,  {'decimal_field': ['Ensure this value is greater than or equal to 100.']})

    def test_raise_max_digits(self):
        """
        Make sure max_digits violations raises ValidationError
        """
        class DecimalSerializer(serializers.Serializer):
            decimal_field = serializers.DecimalField(max_digits=5)

        s = DecimalSerializer(data={'decimal_field': '123.456'})

        self.assertFalse(s.is_valid())
        self.assertEqual(s.errors,  {'decimal_field': ['Ensure that there are no more than 5 digits in total.']})

    def test_raise_max_decimal_places(self):
        """
        Make sure max_decimal_places violations raises ValidationError
        """
        class DecimalSerializer(serializers.Serializer):
            decimal_field = serializers.DecimalField(decimal_places=3)

        s = DecimalSerializer(data={'decimal_field': '123.4567'})

        self.assertFalse(s.is_valid())
        self.assertEqual(s.errors,  {'decimal_field': ['Ensure that there are no more than 3 decimal places.']})

    def test_raise_max_whole_digits(self):
        """
        Make sure max_whole_digits violations raises ValidationError
        """
        class DecimalSerializer(serializers.Serializer):
            decimal_field = serializers.DecimalField(max_digits=4, decimal_places=3)

        s = DecimalSerializer(data={'decimal_field': '12345.6'})

        self.assertFalse(s.is_valid())
        self.assertEqual(s.errors,  {'decimal_field': ['Ensure that there are no more than 4 digits in total.']})


class ChoiceFieldTests(TestCase):
    """
    Tests for the ChoiceField options generator
    """
    def test_choices_required(self):
        """
        Make sure proper choices are rendered if field is required
        """
        f = serializers.ChoiceField(required=True, choices=SAMPLE_CHOICES)
        self.assertEqual(f.choices, SAMPLE_CHOICES)

    def test_choices_not_required(self):
        """
        Make sure proper choices (plus blank) are rendered if the field isn't required
        """
        f = serializers.ChoiceField(required=False, choices=SAMPLE_CHOICES)
        self.assertEqual(f.choices, models.fields.BLANK_CHOICE_DASH + SAMPLE_CHOICES)

    def test_blank_choice_display(self):
        blank = 'No Preference'
        f = serializers.ChoiceField(
            required=False,
            choices=SAMPLE_CHOICES,
            blank_display_value=blank,
        )
        self.assertEqual(f.choices, [('', blank)] + SAMPLE_CHOICES)

    def test_invalid_choice_model(self):
        s = ChoiceFieldModelSerializer(data={'choice': 'wrong_value'})
        self.assertFalse(s.is_valid())
        self.assertEqual(s.errors,  {'choice': ['Select a valid choice. wrong_value is not one of the available choices.']})
        self.assertEqual(s.data['choice'], '')

    def test_empty_choice_model(self):
        """
        Test that the 'empty' value is correctly passed and used depending on
        the 'null' property on the model field.
        """
        s = ChoiceFieldModelSerializer(data={'choice': ''})
        self.assertTrue(s.is_valid())
        self.assertEqual(s.data['choice'], '')

        s = ChoiceFieldModelWithNullSerializer(data={'choice': ''})
        self.assertTrue(s.is_valid())
        self.assertEqual(s.data['choice'], None)

    def test_from_native_empty(self):
        """
        Make sure from_native() returns an empty string on empty param by default.
        """
        f = serializers.ChoiceField(choices=SAMPLE_CHOICES)
        self.assertEqual(f.from_native(''), '')
        self.assertEqual(f.from_native(None), '')

    def test_from_native_empty_override(self):
        """
        Make sure you can override from_native() behavior regarding empty values.
        """
        f = serializers.ChoiceField(choices=SAMPLE_CHOICES, empty=None)
        self.assertEqual(f.from_native(''), None)
        self.assertEqual(f.from_native(None), None)

    def test_metadata_choices(self):
        """
        Make sure proper choices are included in the field's metadata.
        """
        choices = [{'value': v, 'display_name': n} for v, n in SAMPLE_CHOICES]
        f = serializers.ChoiceField(choices=SAMPLE_CHOICES)
        self.assertEqual(f.metadata()['choices'], choices)

    def test_metadata_choices_not_required(self):
        """
        Make sure proper choices are included in the field's metadata.
        """
        choices = [{'value': v, 'display_name': n}
                   for v, n in models.fields.BLANK_CHOICE_DASH + SAMPLE_CHOICES]
        f = serializers.ChoiceField(required=False, choices=SAMPLE_CHOICES)
        self.assertEqual(f.metadata()['choices'], choices)


class EmailFieldTests(TestCase):
    """
    Tests for EmailField attribute values
    """

    class EmailFieldModel(RESTFrameworkModel):
        email_field = models.EmailField(blank=True)

    class EmailFieldWithGivenMaxLengthModel(RESTFrameworkModel):
        email_field = models.EmailField(max_length=150, blank=True)

    def test_default_model_value(self):
        class EmailFieldSerializer(serializers.ModelSerializer):
            class Meta:
                model = self.EmailFieldModel

        serializer = EmailFieldSerializer(data={})
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(getattr(serializer.fields['email_field'], 'max_length'), 75)

    def test_given_model_value(self):
        class EmailFieldSerializer(serializers.ModelSerializer):
            class Meta:
                model = self.EmailFieldWithGivenMaxLengthModel

        serializer = EmailFieldSerializer(data={})
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(getattr(serializer.fields['email_field'], 'max_length'), 150)

    def test_given_serializer_value(self):
        class EmailFieldSerializer(serializers.ModelSerializer):
            email_field = serializers.EmailField(source='email_field', max_length=20, required=False)

            class Meta:
                model = self.EmailFieldModel

        serializer = EmailFieldSerializer(data={})
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(getattr(serializer.fields['email_field'], 'max_length'), 20)


class SlugFieldTests(TestCase):
    """
    Tests for SlugField attribute values
    """

    class SlugFieldModel(RESTFrameworkModel):
        slug_field = models.SlugField(blank=True)

    class SlugFieldWithGivenMaxLengthModel(RESTFrameworkModel):
        slug_field = models.SlugField(max_length=84, blank=True)

    def test_default_model_value(self):
        class SlugFieldSerializer(serializers.ModelSerializer):
            class Meta:
                model = self.SlugFieldModel

        serializer = SlugFieldSerializer(data={})
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(getattr(serializer.fields['slug_field'], 'max_length'), 50)

    def test_given_model_value(self):
        class SlugFieldSerializer(serializers.ModelSerializer):
            class Meta:
                model = self.SlugFieldWithGivenMaxLengthModel

        serializer = SlugFieldSerializer(data={})
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(getattr(serializer.fields['slug_field'], 'max_length'), 84)

    def test_given_serializer_value(self):
        class SlugFieldSerializer(serializers.ModelSerializer):
            slug_field = serializers.SlugField(source='slug_field',
                                               max_length=20, required=False)

            class Meta:
                model = self.SlugFieldModel

        serializer = SlugFieldSerializer(data={})
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(getattr(serializer.fields['slug_field'],
                                 'max_length'), 20)

    def test_invalid_slug(self):
        """
        Make sure an invalid slug raises ValidationError
        """
        class SlugFieldSerializer(serializers.ModelSerializer):
            slug_field = serializers.SlugField(source='slug_field', max_length=20, required=True)

            class Meta:
                model = self.SlugFieldModel

        s = SlugFieldSerializer(data={'slug_field': 'a b'})

        self.assertEqual(s.is_valid(), False)
        self.assertEqual(s.errors,  {'slug_field': ["Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens."]})


class URLFieldTests(TestCase):
    """
    Tests for URLField attribute values.

    (Includes test for #1210, checking that validators can be overridden.)
    """

    class URLFieldModel(RESTFrameworkModel):
        url_field = models.URLField(blank=True)

    class URLFieldWithGivenMaxLengthModel(RESTFrameworkModel):
        url_field = models.URLField(max_length=128, blank=True)

    def test_default_model_value(self):
        class URLFieldSerializer(serializers.ModelSerializer):
            class Meta:
                model = self.URLFieldModel

        serializer = URLFieldSerializer(data={})
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(getattr(serializer.fields['url_field'],
                                 'max_length'), 200)

    def test_given_model_value(self):
        class URLFieldSerializer(serializers.ModelSerializer):
            class Meta:
                model = self.URLFieldWithGivenMaxLengthModel

        serializer = URLFieldSerializer(data={})
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(getattr(serializer.fields['url_field'],
                                 'max_length'), 128)

    def test_given_serializer_value(self):
        class URLFieldSerializer(serializers.ModelSerializer):
            url_field = serializers.URLField(source='url_field',
                                             max_length=20, required=False)

            class Meta:
                model = self.URLFieldWithGivenMaxLengthModel

        serializer = URLFieldSerializer(data={})
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(getattr(serializer.fields['url_field'],
                         'max_length'), 20)

    def test_validators_can_be_overridden(self):
        url_field = serializers.URLField(validators=[])
        validators = url_field.validators
        self.assertEqual([], validators, 'Passing `validators` kwarg should have overridden default validators')


class FieldMetadata(TestCase):
    def setUp(self):
        self.required_field = serializers.Field()
        self.required_field.label = uuid4().hex
        self.required_field.required = True

        self.optional_field = serializers.Field()
        self.optional_field.label = uuid4().hex
        self.optional_field.required = False

    def test_required(self):
        self.assertEqual(self.required_field.metadata()['required'], True)

    def test_optional(self):
        self.assertEqual(self.optional_field.metadata()['required'], False)

    def test_label(self):
        for field in (self.required_field, self.optional_field):
            self.assertEqual(field.metadata()['label'], field.label)


class FieldCallableDefault(TestCase):
    def setUp(self):
        self.simple_callable = lambda: 'foo bar'

    def test_default_can_be_simple_callable(self):
        """
        Ensure that the 'default' argument can also be a simple callable.
        """
        field = serializers.WritableField(default=self.simple_callable)
        into = {}
        field.field_from_native({}, {}, 'field', into)
        self.assertEqual(into, {'field': 'foo bar'})


class CustomIntegerField(TestCase):
    """
        Test that custom fields apply min_value and max_value constraints
    """
    def test_custom_fields_can_be_validated_for_value(self):

        class MoneyField(models.PositiveIntegerField):
            pass

        class EntryModel(models.Model):
            bank = MoneyField(validators=[validators.MaxValueValidator(100)])

        class EntrySerializer(serializers.ModelSerializer):
            class Meta:
                model = EntryModel

        entry = EntryModel(bank=1)

        serializer = EntrySerializer(entry, data={"bank": 11})
        self.assertTrue(serializer.is_valid())

        serializer = EntrySerializer(entry, data={"bank": -1})
        self.assertFalse(serializer.is_valid())

        serializer = EntrySerializer(entry, data={"bank": 101})
        self.assertFalse(serializer.is_valid())


class BooleanField(TestCase):
    """
        Tests for BooleanField
    """
    def test_boolean_required(self):
        class BooleanRequiredSerializer(serializers.Serializer):
            bool_field = serializers.BooleanField(required=True)

        self.assertFalse(BooleanRequiredSerializer(data={}).is_valid())

########NEW FILE########
__FILENAME__ = test_files
from __future__ import unicode_literals
from django.test import TestCase
from rest_framework import serializers
from rest_framework.compat import BytesIO
from rest_framework.compat import six
import datetime


class UploadedFile(object):
    def __init__(self, file=None, created=None):
        self.file = file
        self.created = created or datetime.datetime.now()


class UploadedFileSerializer(serializers.Serializer):
    file = serializers.FileField(required=False)
    created = serializers.DateTimeField()

    def restore_object(self, attrs, instance=None):
        if instance:
            instance.file = attrs['file']
            instance.created = attrs['created']
            return instance
        return UploadedFile(**attrs)


class FileSerializerTests(TestCase):
    def test_create(self):
        now = datetime.datetime.now()
        file = BytesIO(six.b('stuff'))
        file.name = 'stuff.txt'
        file.size = len(file.getvalue())
        serializer = UploadedFileSerializer(data={'created': now}, files={'file': file})
        uploaded_file = UploadedFile(file=file, created=now)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.object.created, uploaded_file.created)
        self.assertEqual(serializer.object.file, uploaded_file.file)
        self.assertFalse(serializer.object is uploaded_file)

    def test_creation_failure(self):
        """
        Passing files=None should result in an ValidationError

        Regression test for:
        https://github.com/tomchristie/django-rest-framework/issues/542
        """
        now = datetime.datetime.now()

        serializer = UploadedFileSerializer(data={'created': now})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.object.created, now)
        self.assertIsNone(serializer.object.file)

    def test_remove_with_empty_string(self):
        """
        Passing empty string as data should cause file to be removed

        Test for:
        https://github.com/tomchristie/django-rest-framework/issues/937
        """
        now = datetime.datetime.now()
        file = BytesIO(six.b('stuff'))
        file.name = 'stuff.txt'
        file.size = len(file.getvalue())

        uploaded_file = UploadedFile(file=file, created=now)

        serializer = UploadedFileSerializer(instance=uploaded_file, data={'created': now, 'file': ''})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.object.created, uploaded_file.created)
        self.assertIsNone(serializer.object.file)

    def test_validation_error_with_non_file(self):
        """
        Passing non-files should raise a validation error.
        """
        now = datetime.datetime.now()
        errmsg = 'No file was submitted. Check the encoding type on the form.'

        serializer = UploadedFileSerializer(data={'created': now, 'file': 'abc'})
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {'file': [errmsg]})

    def test_validation_with_no_data(self):
        """
        Validation should still function when no data dictionary is provided.
        """
        now = datetime.datetime.now()
        file = BytesIO(six.b('stuff'))
        file.name = 'stuff.txt'
        file.size = len(file.getvalue())
        uploaded_file = UploadedFile(file=file, created=now)

        serializer = UploadedFileSerializer(files={'file': file})
        self.assertFalse(serializer.is_valid())

########NEW FILE########
__FILENAME__ = test_filters
from __future__ import unicode_literals
import datetime
from decimal import Decimal
from django.db import models
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import unittest
from rest_framework import generics, serializers, status, filters
from rest_framework.compat import django_filters, patterns, url
from rest_framework.settings import api_settings
from rest_framework.test import APIRequestFactory
from rest_framework.tests.models import BasicModel
from .models import FilterableItem
from .utils import temporary_setting

factory = APIRequestFactory()


if django_filters:
    # Basic filter on a list view.
    class FilterFieldsRootView(generics.ListCreateAPIView):
        model = FilterableItem
        filter_fields = ['decimal', 'date']
        filter_backends = (filters.DjangoFilterBackend,)

    # These class are used to test a filter class.
    class SeveralFieldsFilter(django_filters.FilterSet):
        text = django_filters.CharFilter(lookup_type='icontains')
        decimal = django_filters.NumberFilter(lookup_type='lt')
        date = django_filters.DateFilter(lookup_type='gt')

        class Meta:
            model = FilterableItem
            fields = ['text', 'decimal', 'date']

    class FilterClassRootView(generics.ListCreateAPIView):
        model = FilterableItem
        filter_class = SeveralFieldsFilter
        filter_backends = (filters.DjangoFilterBackend,)

    # These classes are used to test a misconfigured filter class.
    class MisconfiguredFilter(django_filters.FilterSet):
        text = django_filters.CharFilter(lookup_type='icontains')

        class Meta:
            model = BasicModel
            fields = ['text']

    class IncorrectlyConfiguredRootView(generics.ListCreateAPIView):
        model = FilterableItem
        filter_class = MisconfiguredFilter
        filter_backends = (filters.DjangoFilterBackend,)

    class FilterClassDetailView(generics.RetrieveAPIView):
        model = FilterableItem
        filter_class = SeveralFieldsFilter
        filter_backends = (filters.DjangoFilterBackend,)

    # Regression test for #814
    class FilterableItemSerializer(serializers.ModelSerializer):
        class Meta:
            model = FilterableItem

    class FilterFieldsQuerysetView(generics.ListCreateAPIView):
        queryset = FilterableItem.objects.all()
        serializer_class = FilterableItemSerializer
        filter_fields = ['decimal', 'date']
        filter_backends = (filters.DjangoFilterBackend,)

    class GetQuerysetView(generics.ListCreateAPIView):
        serializer_class = FilterableItemSerializer
        filter_class = SeveralFieldsFilter
        filter_backends = (filters.DjangoFilterBackend,)

        def get_queryset(self):
            return FilterableItem.objects.all()

    urlpatterns = patterns('',
        url(r'^(?P<pk>\d+)/$', FilterClassDetailView.as_view(), name='detail-view'),
        url(r'^$', FilterClassRootView.as_view(), name='root-view'),
        url(r'^get-queryset/$', GetQuerysetView.as_view(),
            name='get-queryset-view'),
    )


class CommonFilteringTestCase(TestCase):
    def _serialize_object(self, obj):
        return {'id': obj.id, 'text': obj.text, 'decimal': obj.decimal, 'date': obj.date}

    def setUp(self):
        """
        Create 10 FilterableItem instances.
        """
        base_data = ('a', Decimal('0.25'), datetime.date(2012, 10, 8))
        for i in range(10):
            text = chr(i + ord(base_data[0])) * 3  # Produces string 'aaa', 'bbb', etc.
            decimal = base_data[1] + i
            date = base_data[2] - datetime.timedelta(days=i * 2)
            FilterableItem(text=text, decimal=decimal, date=date).save()

        self.objects = FilterableItem.objects
        self.data = [
            self._serialize_object(obj)
            for obj in self.objects.all()
        ]


class IntegrationTestFiltering(CommonFilteringTestCase):
    """
    Integration tests for filtered list views.
    """

    @unittest.skipUnless(django_filters, 'django-filter not installed')
    def test_get_filtered_fields_root_view(self):
        """
        GET requests to paginated ListCreateAPIView should return paginated results.
        """
        view = FilterFieldsRootView.as_view()

        # Basic test with no filter.
        request = factory.get('/')
        response = view(request).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, self.data)

        # Tests that the decimal filter works.
        search_decimal = Decimal('2.25')
        request = factory.get('/', {'decimal': '%s' % search_decimal})
        response = view(request).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_data = [f for f in self.data if f['decimal'] == search_decimal]
        self.assertEqual(response.data, expected_data)

        # Tests that the date filter works.
        search_date = datetime.date(2012, 9, 22)
        request = factory.get('/', {'date': '%s' % search_date})  # search_date str: '2012-09-22'
        response = view(request).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_data = [f for f in self.data if f['date'] == search_date]
        self.assertEqual(response.data, expected_data)

    @unittest.skipUnless(django_filters, 'django-filter not installed')
    def test_filter_with_queryset(self):
        """
        Regression test for #814.
        """
        view = FilterFieldsQuerysetView.as_view()

        # Tests that the decimal filter works.
        search_decimal = Decimal('2.25')
        request = factory.get('/', {'decimal': '%s' % search_decimal})
        response = view(request).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_data = [f for f in self.data if f['decimal'] == search_decimal]
        self.assertEqual(response.data, expected_data)

    @unittest.skipUnless(django_filters, 'django-filter not installed')
    def test_filter_with_get_queryset_only(self):
        """
        Regression test for #834.
        """
        view = GetQuerysetView.as_view()
        request = factory.get('/get-queryset/')
        view(request).render()
        # Used to raise "issubclass() arg 2 must be a class or tuple of classes"
        # here when neither `model' nor `queryset' was specified.

    @unittest.skipUnless(django_filters, 'django-filter not installed')
    def test_get_filtered_class_root_view(self):
        """
        GET requests to filtered ListCreateAPIView that have a filter_class set
        should return filtered results.
        """
        view = FilterClassRootView.as_view()

        # Basic test with no filter.
        request = factory.get('/')
        response = view(request).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, self.data)

        # Tests that the decimal filter set with 'lt' in the filter class works.
        search_decimal = Decimal('4.25')
        request = factory.get('/', {'decimal': '%s' % search_decimal})
        response = view(request).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_data = [f for f in self.data if f['decimal'] < search_decimal]
        self.assertEqual(response.data, expected_data)

        # Tests that the date filter set with 'gt' in the filter class works.
        search_date = datetime.date(2012, 10, 2)
        request = factory.get('/', {'date': '%s' % search_date})  # search_date str: '2012-10-02'
        response = view(request).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_data = [f for f in self.data if f['date'] > search_date]
        self.assertEqual(response.data, expected_data)

        # Tests that the text filter set with 'icontains' in the filter class works.
        search_text = 'ff'
        request = factory.get('/', {'text': '%s' % search_text})
        response = view(request).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_data = [f for f in self.data if search_text in f['text'].lower()]
        self.assertEqual(response.data, expected_data)

        # Tests that multiple filters works.
        search_decimal = Decimal('5.25')
        search_date = datetime.date(2012, 10, 2)
        request = factory.get('/', {
            'decimal': '%s' % (search_decimal,),
            'date': '%s' % (search_date,)
        })
        response = view(request).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_data = [f for f in self.data if f['date'] > search_date and
                         f['decimal'] < search_decimal]
        self.assertEqual(response.data, expected_data)

    @unittest.skipUnless(django_filters, 'django-filter not installed')
    def test_incorrectly_configured_filter(self):
        """
        An error should be displayed when the filter class is misconfigured.
        """
        view = IncorrectlyConfiguredRootView.as_view()

        request = factory.get('/')
        self.assertRaises(AssertionError, view, request)

    @unittest.skipUnless(django_filters, 'django-filter not installed')
    def test_unknown_filter(self):
        """
        GET requests with filters that aren't configured should return 200.
        """
        view = FilterFieldsRootView.as_view()

        search_integer = 10
        request = factory.get('/', {'integer': '%s' % search_integer})
        response = view(request).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class IntegrationTestDetailFiltering(CommonFilteringTestCase):
    """
    Integration tests for filtered detail views.
    """
    urls = 'rest_framework.tests.test_filters'

    def _get_url(self, item):
        return reverse('detail-view', kwargs=dict(pk=item.pk))

    @unittest.skipUnless(django_filters, 'django-filter not installed')
    def test_get_filtered_detail_view(self):
        """
        GET requests to filtered RetrieveAPIView that have a filter_class set
        should return filtered results.
        """
        item = self.objects.all()[0]
        data = self._serialize_object(item)

        # Basic test with no filter.
        response = self.client.get(self._get_url(item))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, data)

        # Tests that the decimal filter set that should fail.
        search_decimal = Decimal('4.25')
        high_item = self.objects.filter(decimal__gt=search_decimal)[0]
        response = self.client.get(
            '{url}'.format(url=self._get_url(high_item)),
            {'decimal': '{param}'.format(param=search_decimal)})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Tests that the decimal filter set that should succeed.
        search_decimal = Decimal('4.25')
        low_item = self.objects.filter(decimal__lt=search_decimal)[0]
        low_item_data = self._serialize_object(low_item)
        response = self.client.get(
            '{url}'.format(url=self._get_url(low_item)),
            {'decimal': '{param}'.format(param=search_decimal)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, low_item_data)

        # Tests that multiple filters works.
        search_decimal = Decimal('5.25')
        search_date = datetime.date(2012, 10, 2)
        valid_item = self.objects.filter(decimal__lt=search_decimal, date__gt=search_date)[0]
        valid_item_data = self._serialize_object(valid_item)
        response = self.client.get(
            '{url}'.format(url=self._get_url(valid_item)), {
                'decimal': '{decimal}'.format(decimal=search_decimal),
                'date': '{date}'.format(date=search_date)
            })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, valid_item_data)


class SearchFilterModel(models.Model):
    title = models.CharField(max_length=20)
    text = models.CharField(max_length=100)


class SearchFilterTests(TestCase):
    def setUp(self):
        # Sequence of title/text is:
        #
        # z   abc
        # zz  bcd
        # zzz cde
        # ...
        for idx in range(10):
            title = 'z' * (idx + 1)
            text = (
                chr(idx + ord('a')) +
                chr(idx + ord('b')) +
                chr(idx + ord('c'))
            )
            SearchFilterModel(title=title, text=text).save()

    def test_search(self):
        class SearchListView(generics.ListAPIView):
            model = SearchFilterModel
            filter_backends = (filters.SearchFilter,)
            search_fields = ('title', 'text')

        view = SearchListView.as_view()
        request = factory.get('/', {'search': 'b'})
        response = view(request)
        self.assertEqual(
            response.data,
            [
                {'id': 1, 'title': 'z', 'text': 'abc'},
                {'id': 2, 'title': 'zz', 'text': 'bcd'}
            ]
        )

    def test_exact_search(self):
        class SearchListView(generics.ListAPIView):
            model = SearchFilterModel
            filter_backends = (filters.SearchFilter,)
            search_fields = ('=title', 'text')

        view = SearchListView.as_view()
        request = factory.get('/', {'search': 'zzz'})
        response = view(request)
        self.assertEqual(
            response.data,
            [
                {'id': 3, 'title': 'zzz', 'text': 'cde'}
            ]
        )

    def test_startswith_search(self):
        class SearchListView(generics.ListAPIView):
            model = SearchFilterModel
            filter_backends = (filters.SearchFilter,)
            search_fields = ('title', '^text')

        view = SearchListView.as_view()
        request = factory.get('/', {'search': 'b'})
        response = view(request)
        self.assertEqual(
            response.data,
            [
                {'id': 2, 'title': 'zz', 'text': 'bcd'}
            ]
        )

    def test_search_with_nonstandard_search_param(self):
        with temporary_setting('SEARCH_PARAM', 'query', module=filters):
            class SearchListView(generics.ListAPIView):
                model = SearchFilterModel
                filter_backends = (filters.SearchFilter,)
                search_fields = ('title', 'text')

            view = SearchListView.as_view()
            request = factory.get('/', {'query': 'b'})
            response = view(request)
            self.assertEqual(
                response.data,
                [
                    {'id': 1, 'title': 'z', 'text': 'abc'},
                    {'id': 2, 'title': 'zz', 'text': 'bcd'}
                ]
            )


class OrdringFilterModel(models.Model):
    title = models.CharField(max_length=20)
    text = models.CharField(max_length=100)


class OrderingFilterRelatedModel(models.Model):
    related_object = models.ForeignKey(OrdringFilterModel,
                                       related_name="relateds")


class OrderingFilterTests(TestCase):
    def setUp(self):
        # Sequence of title/text is:
        #
        # zyx abc
        # yxw bcd
        # xwv cde
        for idx in range(3):
            title = (
                chr(ord('z') - idx) +
                chr(ord('y') - idx) +
                chr(ord('x') - idx)
            )
            text = (
                chr(idx + ord('a')) +
                chr(idx + ord('b')) +
                chr(idx + ord('c'))
            )
            OrdringFilterModel(title=title, text=text).save()

    def test_ordering(self):
        class OrderingListView(generics.ListAPIView):
            model = OrdringFilterModel
            filter_backends = (filters.OrderingFilter,)
            ordering = ('title',)
            ordering_fields = ('text',)

        view = OrderingListView.as_view()
        request = factory.get('/', {'ordering': 'text'})
        response = view(request)
        self.assertEqual(
            response.data,
            [
                {'id': 1, 'title': 'zyx', 'text': 'abc'},
                {'id': 2, 'title': 'yxw', 'text': 'bcd'},
                {'id': 3, 'title': 'xwv', 'text': 'cde'},
            ]
        )

    def test_reverse_ordering(self):
        class OrderingListView(generics.ListAPIView):
            model = OrdringFilterModel
            filter_backends = (filters.OrderingFilter,)
            ordering = ('title',)
            ordering_fields = ('text',)

        view = OrderingListView.as_view()
        request = factory.get('/', {'ordering': '-text'})
        response = view(request)
        self.assertEqual(
            response.data,
            [
                {'id': 3, 'title': 'xwv', 'text': 'cde'},
                {'id': 2, 'title': 'yxw', 'text': 'bcd'},
                {'id': 1, 'title': 'zyx', 'text': 'abc'},
            ]
        )

    def test_incorrectfield_ordering(self):
        class OrderingListView(generics.ListAPIView):
            model = OrdringFilterModel
            filter_backends = (filters.OrderingFilter,)
            ordering = ('title',)
            ordering_fields = ('text',)

        view = OrderingListView.as_view()
        request = factory.get('/', {'ordering': 'foobar'})
        response = view(request)
        self.assertEqual(
            response.data,
            [
                {'id': 3, 'title': 'xwv', 'text': 'cde'},
                {'id': 2, 'title': 'yxw', 'text': 'bcd'},
                {'id': 1, 'title': 'zyx', 'text': 'abc'},
            ]
        )

    def test_default_ordering(self):
        class OrderingListView(generics.ListAPIView):
            model = OrdringFilterModel
            filter_backends = (filters.OrderingFilter,)
            ordering = ('title',)
            oredering_fields = ('text',)

        view = OrderingListView.as_view()
        request = factory.get('')
        response = view(request)
        self.assertEqual(
            response.data,
            [
                {'id': 3, 'title': 'xwv', 'text': 'cde'},
                {'id': 2, 'title': 'yxw', 'text': 'bcd'},
                {'id': 1, 'title': 'zyx', 'text': 'abc'},
            ]
        )

    def test_default_ordering_using_string(self):
        class OrderingListView(generics.ListAPIView):
            model = OrdringFilterModel
            filter_backends = (filters.OrderingFilter,)
            ordering = 'title'
            ordering_fields = ('text',)

        view = OrderingListView.as_view()
        request = factory.get('')
        response = view(request)
        self.assertEqual(
            response.data,
            [
                {'id': 3, 'title': 'xwv', 'text': 'cde'},
                {'id': 2, 'title': 'yxw', 'text': 'bcd'},
                {'id': 1, 'title': 'zyx', 'text': 'abc'},
            ]
        )

    def test_ordering_by_aggregate_field(self):
        # create some related models to aggregate order by
        num_objs = [2, 5, 3]
        for obj, num_relateds in zip(OrdringFilterModel.objects.all(),
                                     num_objs):
            for _ in range(num_relateds):
                new_related = OrderingFilterRelatedModel(
                    related_object=obj
                )
                new_related.save()

        class OrderingListView(generics.ListAPIView):
            model = OrdringFilterModel
            filter_backends = (filters.OrderingFilter,)
            ordering = 'title'
            ordering_fields = '__all__'
            queryset = OrdringFilterModel.objects.all().annotate(
                models.Count("relateds"))

        view = OrderingListView.as_view()
        request = factory.get('/', {'ordering': 'relateds__count'})
        response = view(request)
        self.assertEqual(
            response.data,
            [
                {'id': 1, 'title': 'zyx', 'text': 'abc'},
                {'id': 3, 'title': 'xwv', 'text': 'cde'},
                {'id': 2, 'title': 'yxw', 'text': 'bcd'},
            ]
        )

    def test_ordering_with_nonstandard_ordering_param(self):
        with temporary_setting('ORDERING_PARAM', 'order', filters):
            class OrderingListView(generics.ListAPIView):
                model = OrdringFilterModel
                filter_backends = (filters.OrderingFilter,)
                ordering = ('title',)
                ordering_fields = ('text',)

            view = OrderingListView.as_view()
            request = factory.get('/', {'order': 'text'})
            response = view(request)
            self.assertEqual(
                response.data,
                [
                    {'id': 1, 'title': 'zyx', 'text': 'abc'},
                    {'id': 2, 'title': 'yxw', 'text': 'bcd'},
                    {'id': 3, 'title': 'xwv', 'text': 'cde'},
                ]
            )


class SensitiveOrderingFilterModel(models.Model):
    username = models.CharField(max_length=20)
    password = models.CharField(max_length=100)


# Three different styles of serializer.
# All should allow ordering by username, but not by password.
class SensitiveDataSerializer1(serializers.ModelSerializer):
    username = serializers.CharField()

    class Meta:
        model = SensitiveOrderingFilterModel
        fields = ('id', 'username')


class SensitiveDataSerializer2(serializers.ModelSerializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    class Meta:
        model = SensitiveOrderingFilterModel
        fields = ('id', 'username', 'password')


class SensitiveDataSerializer3(serializers.ModelSerializer):
    user = serializers.CharField(source='username')

    class Meta:
        model = SensitiveOrderingFilterModel
        fields = ('id', 'user')


class SensitiveOrderingFilterTests(TestCase):
    def setUp(self):
        for idx in range(3):
            username = {0: 'userA', 1: 'userB', 2: 'userC'}[idx]
            password = {0: 'passA', 1: 'passC', 2: 'passB'}[idx]
            SensitiveOrderingFilterModel(username=username, password=password).save()

    def test_order_by_serializer_fields(self):
        for serializer_cls in [
            SensitiveDataSerializer1,
            SensitiveDataSerializer2,
            SensitiveDataSerializer3
        ]:
            class OrderingListView(generics.ListAPIView):
                queryset = SensitiveOrderingFilterModel.objects.all().order_by('username')
                filter_backends = (filters.OrderingFilter,)
                serializer_class = serializer_cls

            view = OrderingListView.as_view()
            request = factory.get('/', {'ordering': '-username'})
            response = view(request)

            if serializer_cls == SensitiveDataSerializer3:
                username_field = 'user'
            else:
                username_field = 'username'

            # Note: Inverse username ordering correctly applied.
            self.assertEqual(
                response.data,
                [
                    {'id': 3, username_field: 'userC'},
                    {'id': 2, username_field: 'userB'},
                    {'id': 1, username_field: 'userA'},
                ]
            )

    def test_cannot_order_by_non_serializer_fields(self):
        for serializer_cls in [
            SensitiveDataSerializer1,
            SensitiveDataSerializer2,
            SensitiveDataSerializer3
        ]:
            class OrderingListView(generics.ListAPIView):
                queryset = SensitiveOrderingFilterModel.objects.all().order_by('username')
                filter_backends = (filters.OrderingFilter,)
                serializer_class = serializer_cls

            view = OrderingListView.as_view()
            request = factory.get('/', {'ordering': 'password'})
            response = view(request)

            if serializer_cls == SensitiveDataSerializer3:
                username_field = 'user'
            else:
                username_field = 'username'

            # Note: The passwords are not in order.  Default ordering is used.
            self.assertEqual(
                response.data,
                [
                    {'id': 1, username_field: 'userA'}, # PassB
                    {'id': 2, username_field: 'userB'}, # PassC
                    {'id': 3, username_field: 'userC'}, # PassA
                ]
            )

########NEW FILE########
__FILENAME__ = test_genericrelations
from __future__ import unicode_literals
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericRelation, GenericForeignKey
from django.db import models
from django.test import TestCase
from rest_framework import serializers
from rest_framework.compat import python_2_unicode_compatible


@python_2_unicode_compatible
class Tag(models.Model):
    """
    Tags have a descriptive slug, and are attached to an arbitrary object.
    """
    tag = models.SlugField()
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    tagged_item = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return self.tag


@python_2_unicode_compatible
class Bookmark(models.Model):
    """
    A URL bookmark that may have multiple tags attached.
    """
    url = models.URLField()
    tags = GenericRelation(Tag)

    def __str__(self):
        return 'Bookmark: %s' % self.url


@python_2_unicode_compatible
class Note(models.Model):
    """
    A textual note that may have multiple tags attached.
    """
    text = models.TextField()
    tags = GenericRelation(Tag)

    def __str__(self):
        return 'Note: %s' % self.text


class TestGenericRelations(TestCase):
    def setUp(self):
        self.bookmark = Bookmark.objects.create(url='https://www.djangoproject.com/')
        Tag.objects.create(tagged_item=self.bookmark, tag='django')
        Tag.objects.create(tagged_item=self.bookmark, tag='python')
        self.note = Note.objects.create(text='Remember the milk')
        Tag.objects.create(tagged_item=self.note, tag='reminder')

    def test_generic_relation(self):
        """
        Test a relationship that spans a GenericRelation field.
        IE. A reverse generic relationship.
        """

        class BookmarkSerializer(serializers.ModelSerializer):
            tags = serializers.RelatedField(many=True)

            class Meta:
                model = Bookmark
                exclude = ('id',)

        serializer = BookmarkSerializer(self.bookmark)
        expected = {
            'tags': ['django', 'python'],
            'url': 'https://www.djangoproject.com/'
        }
        self.assertEqual(serializer.data, expected)

    def test_generic_nested_relation(self):
        """
        Test saving a GenericRelation field via a nested serializer.
        """

        class TagSerializer(serializers.ModelSerializer):
            class Meta:
                model = Tag
                exclude = ('content_type', 'object_id')

        class BookmarkSerializer(serializers.ModelSerializer):
            tags = TagSerializer()

            class Meta:
                model = Bookmark
                exclude = ('id',)

        data = {
            'url': 'https://docs.djangoproject.com/',
            'tags': [
                {'tag': 'contenttypes'},
                {'tag': 'genericrelations'},
            ]
        }
        serializer = BookmarkSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertEqual(serializer.object.tags.count(), 2)

    def test_generic_fk(self):
        """
        Test a relationship that spans a GenericForeignKey field.
        IE. A forward generic relationship.
        """

        class TagSerializer(serializers.ModelSerializer):
            tagged_item = serializers.RelatedField()

            class Meta:
                model = Tag
                exclude = ('id', 'content_type', 'object_id')

        serializer = TagSerializer(Tag.objects.all(), many=True)
        expected = [
        {
            'tag': 'django',
            'tagged_item': 'Bookmark: https://www.djangoproject.com/'
        },
        {
            'tag': 'python',
            'tagged_item': 'Bookmark: https://www.djangoproject.com/'
        },
        {
            'tag': 'reminder',
            'tagged_item': 'Note: Remember the milk'
        }
        ]
        self.assertEqual(serializer.data, expected)

    def test_restore_object_generic_fk(self):
        """
        Ensure an object with a generic foreign key can be restored.
        """

        class TagSerializer(serializers.ModelSerializer):
            class Meta:
                model = Tag
                exclude = ('content_type', 'object_id')

        serializer = TagSerializer()

        bookmark = Bookmark(url='http://example.com')
        attrs = {'tagged_item': bookmark, 'tag': 'example'}

        tag = serializer.restore_object(attrs)
        self.assertEqual(tag.tagged_item, bookmark)

########NEW FILE########
__FILENAME__ = test_generics
from __future__ import unicode_literals
from django.db import models
from django.shortcuts import get_object_or_404
from django.test import TestCase
from rest_framework import generics, renderers, serializers, status
from rest_framework.test import APIRequestFactory
from rest_framework.tests.models import BasicModel, Comment, SlugBasedModel
from rest_framework.tests.models import ForeignKeySource, ForeignKeyTarget
from rest_framework.compat import six

factory = APIRequestFactory()


class RootView(generics.ListCreateAPIView):
    """
    Example description for OPTIONS.
    """
    model = BasicModel


class InstanceView(generics.RetrieveUpdateDestroyAPIView):
    """
    Example description for OPTIONS.
    """
    model = BasicModel

    def get_queryset(self):
        queryset = super(InstanceView, self).get_queryset()
        return queryset.exclude(text='filtered out')


class FKInstanceView(generics.RetrieveUpdateDestroyAPIView):
    """
    FK: example description for OPTIONS.
    """
    model = ForeignKeySource


class SlugSerializer(serializers.ModelSerializer):
    slug = serializers.Field()  # read only

    class Meta:
        model = SlugBasedModel
        exclude = ('id',)


class SlugBasedInstanceView(InstanceView):
    """
    A model with a slug-field.
    """
    model = SlugBasedModel
    serializer_class = SlugSerializer
    lookup_field = 'slug'


class TestRootView(TestCase):
    def setUp(self):
        """
        Create 3 BasicModel instances.
        """
        items = ['foo', 'bar', 'baz']
        for item in items:
            BasicModel(text=item).save()
        self.objects = BasicModel.objects
        self.data = [
            {'id': obj.id, 'text': obj.text}
            for obj in self.objects.all()
        ]
        self.view = RootView.as_view()

    def test_get_root_view(self):
        """
        GET requests to ListCreateAPIView should return list of objects.
        """
        request = factory.get('/')
        with self.assertNumQueries(1):
            response = self.view(request).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, self.data)

    def test_post_root_view(self):
        """
        POST requests to ListCreateAPIView should create a new object.
        """
        data = {'text': 'foobar'}
        request = factory.post('/', data, format='json')
        with self.assertNumQueries(1):
            response = self.view(request).render()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, {'id': 4, 'text': 'foobar'})
        created = self.objects.get(id=4)
        self.assertEqual(created.text, 'foobar')

    def test_put_root_view(self):
        """
        PUT requests to ListCreateAPIView should not be allowed
        """
        data = {'text': 'foobar'}
        request = factory.put('/', data, format='json')
        with self.assertNumQueries(0):
            response = self.view(request).render()
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.data, {"detail": "Method 'PUT' not allowed."})

    def test_delete_root_view(self):
        """
        DELETE requests to ListCreateAPIView should not be allowed
        """
        request = factory.delete('/')
        with self.assertNumQueries(0):
            response = self.view(request).render()
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.data, {"detail": "Method 'DELETE' not allowed."})

    def test_options_root_view(self):
        """
        OPTIONS requests to ListCreateAPIView should return metadata
        """
        request = factory.options('/')
        with self.assertNumQueries(0):
            response = self.view(request).render()
        expected = {
            'parses': [
                'application/json',
                'application/x-www-form-urlencoded',
                'multipart/form-data'
            ],
            'renders': [
                'application/json',
                'text/html'
            ],
            'name': 'Root',
            'description': 'Example description for OPTIONS.',
            'actions': {
                'POST': {
                    'text': {
                        'max_length': 100,
                        'read_only': False,
                        'required': True,
                        'type': 'string',
                        "label": "Text comes here",
                        "help_text": "Text description."
                    },
                    'id': {
                        'read_only': True,
                        'required': False,
                        'type': 'integer',
                        'label': 'ID',
                    },
                }
            }
        }
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected)

    def test_post_cannot_set_id(self):
        """
        POST requests to create a new object should not be able to set the id.
        """
        data = {'id': 999, 'text': 'foobar'}
        request = factory.post('/', data, format='json')
        with self.assertNumQueries(1):
            response = self.view(request).render()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, {'id': 4, 'text': 'foobar'})
        created = self.objects.get(id=4)
        self.assertEqual(created.text, 'foobar')


class TestInstanceView(TestCase):
    def setUp(self):
        """
        Create 3 BasicModel intances.
        """
        items = ['foo', 'bar', 'baz', 'filtered out']
        for item in items:
            BasicModel(text=item).save()
        self.objects = BasicModel.objects.exclude(text='filtered out')
        self.data = [
            {'id': obj.id, 'text': obj.text}
            for obj in self.objects.all()
        ]
        self.view = InstanceView.as_view()
        self.slug_based_view = SlugBasedInstanceView.as_view()

    def test_get_instance_view(self):
        """
        GET requests to RetrieveUpdateDestroyAPIView should return a single object.
        """
        request = factory.get('/1')
        with self.assertNumQueries(1):
            response = self.view(request, pk=1).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, self.data[0])

    def test_post_instance_view(self):
        """
        POST requests to RetrieveUpdateDestroyAPIView should not be allowed
        """
        data = {'text': 'foobar'}
        request = factory.post('/', data, format='json')
        with self.assertNumQueries(0):
            response = self.view(request).render()
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.data, {"detail": "Method 'POST' not allowed."})

    def test_put_instance_view(self):
        """
        PUT requests to RetrieveUpdateDestroyAPIView should update an object.
        """
        data = {'text': 'foobar'}
        request = factory.put('/1', data, format='json')
        with self.assertNumQueries(2):
            response = self.view(request, pk='1').render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'id': 1, 'text': 'foobar'})
        updated = self.objects.get(id=1)
        self.assertEqual(updated.text, 'foobar')

    def test_patch_instance_view(self):
        """
        PATCH requests to RetrieveUpdateDestroyAPIView should update an object.
        """
        data = {'text': 'foobar'}
        request = factory.patch('/1', data, format='json')

        with self.assertNumQueries(2):
            response = self.view(request, pk=1).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'id': 1, 'text': 'foobar'})
        updated = self.objects.get(id=1)
        self.assertEqual(updated.text, 'foobar')

    def test_delete_instance_view(self):
        """
        DELETE requests to RetrieveUpdateDestroyAPIView should delete an object.
        """
        request = factory.delete('/1')
        with self.assertNumQueries(2):
            response = self.view(request, pk=1).render()
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.content, six.b(''))
        ids = [obj.id for obj in self.objects.all()]
        self.assertEqual(ids, [2, 3])

    def test_options_instance_view(self):
        """
        OPTIONS requests to RetrieveUpdateDestroyAPIView should return metadata
        """
        request = factory.options('/1')
        with self.assertNumQueries(1):
            response = self.view(request, pk=1).render()
        expected = {
            'parses': [
                'application/json',
                'application/x-www-form-urlencoded',
                'multipart/form-data'
            ],
            'renders': [
                'application/json',
                'text/html'
            ],
            'name': 'Instance',
            'description': 'Example description for OPTIONS.',
            'actions': {
                'PUT': {
                    'text': {
                        'max_length': 100,
                        'read_only': False,
                        'required': True,
                        'type': 'string',
                        'label': 'Text comes here',
                        'help_text': 'Text description.'
                    },
                    'id': {
                        'read_only': True,
                        'required': False,
                        'type': 'integer',
                        'label': 'ID',
                    },
                }
            }
        }
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected)

    def test_options_before_instance_create(self):
        """
        OPTIONS requests to RetrieveUpdateDestroyAPIView should return metadata
        before the instance has been created
        """
        request = factory.options('/999')
        with self.assertNumQueries(1):
            response = self.view(request, pk=999).render()
        expected = {
            'parses': [
                'application/json',
                'application/x-www-form-urlencoded',
                'multipart/form-data'
            ],
            'renders': [
                'application/json',
                'text/html'
            ],
            'name': 'Instance',
            'description': 'Example description for OPTIONS.',
            'actions': {
                'PUT': {
                    'text': {
                        'max_length': 100,
                        'read_only': False,
                        'required': True,
                        'type': 'string',
                        'label': 'Text comes here',
                        'help_text': 'Text description.'
                    },
                    'id': {
                        'read_only': True,
                        'required': False,
                        'type': 'integer',
                        'label': 'ID',
                    },
                }
            }
        }
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected)

    def test_get_instance_view_incorrect_arg(self):
        """
        GET requests with an incorrect pk type, should raise 404, not 500.
        Regression test for #890.
        """
        request = factory.get('/a')
        with self.assertNumQueries(0):
            response = self.view(request, pk='a').render()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_cannot_set_id(self):
        """
        PUT requests to create a new object should not be able to set the id.
        """
        data = {'id': 999, 'text': 'foobar'}
        request = factory.put('/1', data, format='json')
        with self.assertNumQueries(2):
            response = self.view(request, pk=1).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'id': 1, 'text': 'foobar'})
        updated = self.objects.get(id=1)
        self.assertEqual(updated.text, 'foobar')

    def test_put_to_deleted_instance(self):
        """
        PUT requests to RetrieveUpdateDestroyAPIView should create an object
        if it does not currently exist.
        """
        self.objects.get(id=1).delete()
        data = {'text': 'foobar'}
        request = factory.put('/1', data, format='json')
        with self.assertNumQueries(3):
            response = self.view(request, pk=1).render()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, {'id': 1, 'text': 'foobar'})
        updated = self.objects.get(id=1)
        self.assertEqual(updated.text, 'foobar')

    def test_put_to_filtered_out_instance(self):
        """
        PUT requests to an URL of instance which is filtered out should not be
        able to create new objects.
        """
        data = {'text': 'foo'}
        filtered_out_pk = BasicModel.objects.filter(text='filtered out')[0].pk
        request = factory.put('/{0}'.format(filtered_out_pk), data, format='json')
        response = self.view(request, pk=filtered_out_pk).render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_as_create_on_id_based_url(self):
        """
        PUT requests to RetrieveUpdateDestroyAPIView should create an object
        at the requested url if it doesn't exist.
        """
        data = {'text': 'foobar'}
        # pk fields can not be created on demand, only the database can set the pk for a new object
        request = factory.put('/5', data, format='json')
        with self.assertNumQueries(3):
            response = self.view(request, pk=5).render()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_obj = self.objects.get(pk=5)
        self.assertEqual(new_obj.text, 'foobar')

    def test_put_as_create_on_slug_based_url(self):
        """
        PUT requests to RetrieveUpdateDestroyAPIView should create an object
        at the requested url if possible, else return HTTP_403_FORBIDDEN error-response.
        """
        data = {'text': 'foobar'}
        request = factory.put('/test_slug', data, format='json')
        with self.assertNumQueries(2):
            response = self.slug_based_view(request, slug='test_slug').render()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, {'slug': 'test_slug', 'text': 'foobar'})
        new_obj = SlugBasedModel.objects.get(slug='test_slug')
        self.assertEqual(new_obj.text, 'foobar')

    def test_patch_cannot_create_an_object(self):
        """
        PATCH requests should not be able to create objects.
        """
        data = {'text': 'foobar'}
        request = factory.patch('/999', data, format='json')
        with self.assertNumQueries(1):
            response = self.view(request, pk=999).render()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(self.objects.filter(id=999).exists())


class TestFKInstanceView(TestCase):
    def setUp(self):
        """
        Create 3 BasicModel instances.
        """
        items = ['foo', 'bar', 'baz']
        for item in items:
            t = ForeignKeyTarget(name=item)
            t.save()
            ForeignKeySource(name='source_' + item, target=t).save()

        self.objects = ForeignKeySource.objects
        self.data = [
            {'id': obj.id, 'name': obj.name}
            for obj in self.objects.all()
        ]
        self.view = FKInstanceView.as_view()

    def test_options_root_view(self):
        """
        OPTIONS requests to ListCreateAPIView should return metadata
        """
        request = factory.options('/999')
        with self.assertNumQueries(1):
            response = self.view(request, pk=999).render()
        expected = {
            'name': 'Fk Instance',
            'description': 'FK: example description for OPTIONS.',
            'renders': [
                'application/json',
                'text/html'
            ],
            'parses': [
                'application/json',
                'application/x-www-form-urlencoded',
                'multipart/form-data'
            ],
            'actions': {
                'PUT': {
                    'id': {
                        'type': 'integer',
                        'required': False,
                        'read_only': True,
                        'label': 'ID'
                    },
                    'name': {
                        'type': 'string',
                        'required': True,
                        'read_only': False,
                        'label': 'name',
                        'max_length': 100
                    },
                    'target': {
                        'type': 'field',
                        'required': True,
                        'read_only': False,
                        'label': 'Target',
                        'help_text': 'Target'
                    }
                }
            }
        }
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected)


class TestOverriddenGetObject(TestCase):
    """
    Test cases for a RetrieveUpdateDestroyAPIView that does NOT use the
    queryset/model mechanism but instead overrides get_object()
    """
    def setUp(self):
        """
        Create 3 BasicModel intances.
        """
        items = ['foo', 'bar', 'baz']
        for item in items:
            BasicModel(text=item).save()
        self.objects = BasicModel.objects
        self.data = [
            {'id': obj.id, 'text': obj.text}
            for obj in self.objects.all()
        ]

        class OverriddenGetObjectView(generics.RetrieveUpdateDestroyAPIView):
            """
            Example detail view for override of get_object().
            """
            model = BasicModel

            def get_object(self):
                pk = int(self.kwargs['pk'])
                return get_object_or_404(BasicModel.objects.all(), id=pk)

        self.view = OverriddenGetObjectView.as_view()

    def test_overridden_get_object_view(self):
        """
        GET requests to RetrieveUpdateDestroyAPIView should return a single object.
        """
        request = factory.get('/1')
        with self.assertNumQueries(1):
            response = self.view(request, pk=1).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, self.data[0])


# Regression test for #285

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        exclude = ('created',)


class CommentView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    model = Comment


class TestCreateModelWithAutoNowAddField(TestCase):
    def setUp(self):
        self.objects = Comment.objects
        self.view = CommentView.as_view()

    def test_create_model_with_auto_now_add_field(self):
        """
        Regression test for #285

        https://github.com/tomchristie/django-rest-framework/issues/285
        """
        data = {'email': 'foobar@example.com', 'content': 'foobar'}
        request = factory.post('/', data, format='json')
        response = self.view(request).render()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = self.objects.get(id=1)
        self.assertEqual(created.content, 'foobar')


# Test for particularly ugly regression with m2m in browsable API
class ClassB(models.Model):
    name = models.CharField(max_length=255)


class ClassA(models.Model):
    name = models.CharField(max_length=255)
    childs = models.ManyToManyField(ClassB, blank=True, null=True)


class ClassASerializer(serializers.ModelSerializer):
    childs = serializers.PrimaryKeyRelatedField(many=True, source='childs')

    class Meta:
        model = ClassA


class ExampleView(generics.ListCreateAPIView):
    serializer_class = ClassASerializer
    model = ClassA


class TestM2MBrowseableAPI(TestCase):
    def test_m2m_in_browseable_api(self):
        """
        Test for particularly ugly regression with m2m in browsable API
        """
        request = factory.get('/', HTTP_ACCEPT='text/html')
        view = ExampleView().as_view()
        response = view(request).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class InclusiveFilterBackend(object):
    def filter_queryset(self, request, queryset, view):
        return queryset.filter(text='foo')


class ExclusiveFilterBackend(object):
    def filter_queryset(self, request, queryset, view):
        return queryset.filter(text='other')


class TwoFieldModel(models.Model):
    field_a = models.CharField(max_length=100)
    field_b = models.CharField(max_length=100)


class DynamicSerializerView(generics.ListCreateAPIView):
    model = TwoFieldModel
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            class DynamicSerializer(serializers.ModelSerializer):
                class Meta:
                    model = TwoFieldModel
                    fields = ('field_b',)
            return DynamicSerializer
        return super(DynamicSerializerView, self).get_serializer_class()


class TestFilterBackendAppliedToViews(TestCase):

    def setUp(self):
        """
        Create 3 BasicModel instances to filter on.
        """
        items = ['foo', 'bar', 'baz']
        for item in items:
            BasicModel(text=item).save()
        self.objects = BasicModel.objects
        self.data = [
            {'id': obj.id, 'text': obj.text}
            for obj in self.objects.all()
        ]

    def test_get_root_view_filters_by_name_with_filter_backend(self):
        """
        GET requests to ListCreateAPIView should return filtered list.
        """
        root_view = RootView.as_view(filter_backends=(InclusiveFilterBackend,))
        request = factory.get('/')
        response = root_view(request).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data, [{'id': 1, 'text': 'foo'}])

    def test_get_root_view_filters_out_all_models_with_exclusive_filter_backend(self):
        """
        GET requests to ListCreateAPIView should return empty list when all models are filtered out.
        """
        root_view = RootView.as_view(filter_backends=(ExclusiveFilterBackend,))
        request = factory.get('/')
        response = root_view(request).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_get_instance_view_filters_out_name_with_filter_backend(self):
        """
        GET requests to RetrieveUpdateDestroyAPIView should raise 404 when model filtered out.
        """
        instance_view = InstanceView.as_view(filter_backends=(ExclusiveFilterBackend,))
        request = factory.get('/1')
        response = instance_view(request, pk=1).render()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {'detail': 'Not found'})

    def test_get_instance_view_will_return_single_object_when_filter_does_not_exclude_it(self):
        """
        GET requests to RetrieveUpdateDestroyAPIView should return a single object when not excluded
        """
        instance_view = InstanceView.as_view(filter_backends=(InclusiveFilterBackend,))
        request = factory.get('/1')
        response = instance_view(request, pk=1).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'id': 1, 'text': 'foo'})

    def test_dynamic_serializer_form_in_browsable_api(self):
        """
        GET requests to ListCreateAPIView should return filtered list.
        """
        view = DynamicSerializerView.as_view()
        request = factory.get('/')
        response = view(request).render()
        self.assertContains(response, 'field_b')
        self.assertNotContains(response, 'field_a')

########NEW FILE########
__FILENAME__ = test_htmlrenderer
from __future__ import unicode_literals
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import TestCase
from django.template import TemplateDoesNotExist, Template
import django.template.loader
from rest_framework import status
from rest_framework.compat import patterns, url
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.compat import six


@api_view(('GET',))
@renderer_classes((TemplateHTMLRenderer,))
def example(request):
    """
    A view that can returns an HTML representation.
    """
    data = {'object': 'foobar'}
    return Response(data, template_name='example.html')


@api_view(('GET',))
@renderer_classes((TemplateHTMLRenderer,))
def permission_denied(request):
    raise PermissionDenied()


@api_view(('GET',))
@renderer_classes((TemplateHTMLRenderer,))
def not_found(request):
    raise Http404()


urlpatterns = patterns('',
    url(r'^$', example),
    url(r'^permission_denied$', permission_denied),
    url(r'^not_found$', not_found),
)


class TemplateHTMLRendererTests(TestCase):
    urls = 'rest_framework.tests.test_htmlrenderer'

    def setUp(self):
        """
        Monkeypatch get_template
        """
        self.get_template = django.template.loader.get_template

        def get_template(template_name, dirs=None):
            if template_name == 'example.html':
                return Template("example: {{ object }}")
            raise TemplateDoesNotExist(template_name)

        django.template.loader.get_template = get_template

    def tearDown(self):
        """
        Revert monkeypatching
        """
        django.template.loader.get_template = self.get_template

    def test_simple_html_view(self):
        response = self.client.get('/')
        self.assertContains(response, "example: foobar")
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')

    def test_not_found_html_view(self):
        response = self.client.get('/not_found')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.content, six.b("404 Not Found"))
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')

    def test_permission_denied_html_view(self):
        response = self.client.get('/permission_denied')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.content, six.b("403 Forbidden"))
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')


class TemplateHTMLRendererExceptionTests(TestCase):
    urls = 'rest_framework.tests.test_htmlrenderer'

    def setUp(self):
        """
        Monkeypatch get_template
        """
        self.get_template = django.template.loader.get_template

        def get_template(template_name):
            if template_name == '404.html':
                return Template("404: {{ detail }}")
            if template_name == '403.html':
                return Template("403: {{ detail }}")
            raise TemplateDoesNotExist(template_name)

        django.template.loader.get_template = get_template

    def tearDown(self):
        """
        Revert monkeypatching
        """
        django.template.loader.get_template = self.get_template

    def test_not_found_html_view_with_template(self):
        response = self.client.get('/not_found')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(response.content in (
            six.b("404: Not found"), six.b("404 Not Found")))
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')

    def test_permission_denied_html_view_with_template(self):
        response = self.client.get('/permission_denied')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(response.content in (
            six.b("403: Permission denied"), six.b("403 Forbidden")))
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')

########NEW FILE########
__FILENAME__ = test_hyperlinkedserializers
from __future__ import unicode_literals
import json
from django.test import TestCase
from rest_framework import generics, status, serializers
from rest_framework.compat import patterns, url
from rest_framework.settings import api_settings
from rest_framework.test import APIRequestFactory
from rest_framework.tests.models import (
    Anchor, BasicModel, ManyToManyModel, BlogPost, BlogPostComment,
    Album, Photo, OptionalRelationModel
)

factory = APIRequestFactory()


class BlogPostCommentSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='blogpostcomment-detail')
    text = serializers.CharField()
    blog_post_url = serializers.HyperlinkedRelatedField(source='blog_post', view_name='blogpost-detail')

    class Meta:
        model = BlogPostComment
        fields = ('text', 'blog_post_url', 'url')


class PhotoSerializer(serializers.Serializer):
    description = serializers.CharField()
    album_url = serializers.HyperlinkedRelatedField(source='album', view_name='album-detail', queryset=Album.objects.all(), lookup_field='title', slug_url_kwarg='title')

    def restore_object(self, attrs, instance=None):
        return Photo(**attrs)


class AlbumSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='album-detail', lookup_field='title')

    class Meta:
        model = Album
        fields = ('title', 'url')


class BasicList(generics.ListCreateAPIView):
    model = BasicModel
    model_serializer_class = serializers.HyperlinkedModelSerializer


class BasicDetail(generics.RetrieveUpdateDestroyAPIView):
    model = BasicModel
    model_serializer_class = serializers.HyperlinkedModelSerializer


class AnchorDetail(generics.RetrieveAPIView):
    model = Anchor
    model_serializer_class = serializers.HyperlinkedModelSerializer


class ManyToManyList(generics.ListAPIView):
    model = ManyToManyModel
    model_serializer_class = serializers.HyperlinkedModelSerializer


class ManyToManyDetail(generics.RetrieveAPIView):
    model = ManyToManyModel
    model_serializer_class = serializers.HyperlinkedModelSerializer


class BlogPostCommentListCreate(generics.ListCreateAPIView):
    model = BlogPostComment
    serializer_class = BlogPostCommentSerializer


class BlogPostCommentDetail(generics.RetrieveAPIView):
    model = BlogPostComment
    serializer_class = BlogPostCommentSerializer


class BlogPostDetail(generics.RetrieveAPIView):
    model = BlogPost


class PhotoListCreate(generics.ListCreateAPIView):
    model = Photo
    model_serializer_class = PhotoSerializer


class AlbumDetail(generics.RetrieveAPIView):
    model = Album
    serializer_class = AlbumSerializer
    lookup_field = 'title'


class OptionalRelationDetail(generics.RetrieveUpdateDestroyAPIView):
    model = OptionalRelationModel
    model_serializer_class = serializers.HyperlinkedModelSerializer


urlpatterns = patterns('',
    url(r'^basic/$', BasicList.as_view(), name='basicmodel-list'),
    url(r'^basic/(?P<pk>\d+)/$', BasicDetail.as_view(), name='basicmodel-detail'),
    url(r'^anchor/(?P<pk>\d+)/$', AnchorDetail.as_view(), name='anchor-detail'),
    url(r'^manytomany/$', ManyToManyList.as_view(), name='manytomanymodel-list'),
    url(r'^manytomany/(?P<pk>\d+)/$', ManyToManyDetail.as_view(), name='manytomanymodel-detail'),
    url(r'^posts/(?P<pk>\d+)/$', BlogPostDetail.as_view(), name='blogpost-detail'),
    url(r'^comments/$', BlogPostCommentListCreate.as_view(), name='blogpostcomment-list'),
    url(r'^comments/(?P<pk>\d+)/$', BlogPostCommentDetail.as_view(), name='blogpostcomment-detail'),
    url(r'^albums/(?P<title>\w[\w-]*)/$', AlbumDetail.as_view(), name='album-detail'),
    url(r'^photos/$', PhotoListCreate.as_view(), name='photo-list'),
    url(r'^optionalrelation/(?P<pk>\d+)/$', OptionalRelationDetail.as_view(), name='optionalrelationmodel-detail'),
)


class TestBasicHyperlinkedView(TestCase):
    urls = 'rest_framework.tests.test_hyperlinkedserializers'

    def setUp(self):
        """
        Create 3 BasicModel instances.
        """
        items = ['foo', 'bar', 'baz']
        for item in items:
            BasicModel(text=item).save()
        self.objects = BasicModel.objects
        self.data = [
            {'url': 'http://testserver/basic/%d/' % obj.id, 'text': obj.text}
            for obj in self.objects.all()
        ]
        self.list_view = BasicList.as_view()
        self.detail_view = BasicDetail.as_view()

    def test_get_list_view(self):
        """
        GET requests to ListCreateAPIView should return list of objects.
        """
        request = factory.get('/basic/')
        response = self.list_view(request).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, self.data)

    def test_get_detail_view(self):
        """
        GET requests to ListCreateAPIView should return list of objects.
        """
        request = factory.get('/basic/1')
        response = self.detail_view(request, pk=1).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, self.data[0])


class TestManyToManyHyperlinkedView(TestCase):
    urls = 'rest_framework.tests.test_hyperlinkedserializers'

    def setUp(self):
        """
        Create 3 BasicModel instances.
        """
        items = ['foo', 'bar', 'baz']
        anchors = []
        for item in items:
            anchor = Anchor(text=item)
            anchor.save()
            anchors.append(anchor)

        manytomany = ManyToManyModel()
        manytomany.save()
        manytomany.rel.add(*anchors)

        self.data = [{
            'url': 'http://testserver/manytomany/1/',
            'rel': [
                'http://testserver/anchor/1/',
                'http://testserver/anchor/2/',
                'http://testserver/anchor/3/',
            ]
        }]
        self.list_view = ManyToManyList.as_view()
        self.detail_view = ManyToManyDetail.as_view()

    def test_get_list_view(self):
        """
        GET requests to ListCreateAPIView should return list of objects.
        """
        request = factory.get('/manytomany/')
        response = self.list_view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, self.data)

    def test_get_detail_view(self):
        """
        GET requests to ListCreateAPIView should return list of objects.
        """
        request = factory.get('/manytomany/1/')
        response = self.detail_view(request, pk=1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, self.data[0])


class TestHyperlinkedIdentityFieldLookup(TestCase):
    urls = 'rest_framework.tests.test_hyperlinkedserializers'

    def setUp(self):
        """
        Create 3 Album instances.
        """
        titles = ['foo', 'bar', 'baz']
        for title in titles:
            album = Album(title=title)
            album.save()
        self.detail_view = AlbumDetail.as_view()
        self.data = {
            'foo': {'title': 'foo', 'url': 'http://testserver/albums/foo/'},
            'bar': {'title': 'bar', 'url': 'http://testserver/albums/bar/'},
            'baz': {'title': 'baz', 'url': 'http://testserver/albums/baz/'}
        }

    def test_lookup_field(self):
        """
        GET requests to AlbumDetail view should return serialized Albums
        with a url field keyed by `title`.
        """
        for album in Album.objects.all():
            request = factory.get('/albums/{0}/'.format(album.title))
            response = self.detail_view(request, title=album.title)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data, self.data[album.title])


class TestCreateWithForeignKeys(TestCase):
    urls = 'rest_framework.tests.test_hyperlinkedserializers'

    def setUp(self):
        """
        Create a blog post
        """
        self.post = BlogPost.objects.create(title="Test post")
        self.create_view = BlogPostCommentListCreate.as_view()

    def test_create_comment(self):

        data = {
            'text': 'A test comment',
            'blog_post_url': 'http://testserver/posts/1/'
        }

        request = factory.post('/comments/', data=data)
        response = self.create_view(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response['Location'], 'http://testserver/comments/1/')
        self.assertEqual(self.post.blogpostcomment_set.count(), 1)
        self.assertEqual(self.post.blogpostcomment_set.all()[0].text, 'A test comment')


class TestCreateWithForeignKeysAndCustomSlug(TestCase):
    urls = 'rest_framework.tests.test_hyperlinkedserializers'

    def setUp(self):
        """
        Create an Album
        """
        self.post = Album.objects.create(title='test-album')
        self.list_create_view = PhotoListCreate.as_view()

    def test_create_photo(self):

        data = {
            'description': 'A test photo',
            'album_url': 'http://testserver/albums/test-album/'
        }

        request = factory.post('/photos/', data=data)
        response = self.list_create_view(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('Location', response, msg='Location should only be included if there is a "url" field on the serializer')
        self.assertEqual(self.post.photo_set.count(), 1)
        self.assertEqual(self.post.photo_set.all()[0].description, 'A test photo')


class TestOptionalRelationHyperlinkedView(TestCase):
    urls = 'rest_framework.tests.test_hyperlinkedserializers'

    def setUp(self):
        """
        Create 1 OptionalRelationModel instances.
        """
        OptionalRelationModel().save()
        self.objects = OptionalRelationModel.objects
        self.detail_view = OptionalRelationDetail.as_view()
        self.data = {"url": "http://testserver/optionalrelation/1/", "other": None}

    def test_get_detail_view(self):
        """
        GET requests to RetrieveAPIView with optional relations should return None
        for non existing relations.
        """
        request = factory.get('/optionalrelationmodel-detail/1')
        response = self.detail_view(request, pk=1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, self.data)

    def test_put_detail_view(self):
        """
        PUT requests to RetrieveUpdateDestroyAPIView with optional relations
        should accept None for non existing relations.
        """
        response = self.client.put('/optionalrelation/1/',
                                   data=json.dumps(self.data),
                                   content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestOverriddenURLField(TestCase):
    def setUp(self):
        class OverriddenURLSerializer(serializers.HyperlinkedModelSerializer):
            url = serializers.SerializerMethodField('get_url')

            class Meta:
                model = BlogPost
                fields = ('title', 'url')

            def get_url(self, obj):
                return 'foo bar'

        self.Serializer = OverriddenURLSerializer
        self.obj = BlogPost.objects.create(title='New blog post')

    def test_overridden_url_field(self):
        """
        The 'url' field should respect overriding.
        Regression test for #936.
        """
        serializer = self.Serializer(self.obj)
        self.assertEqual(
            serializer.data,
            {'title': 'New blog post', 'url': 'foo bar'}
        )


class TestURLFieldNameBySettings(TestCase):
    urls = 'rest_framework.tests.test_hyperlinkedserializers'

    def setUp(self):
        self.saved_url_field_name = api_settings.URL_FIELD_NAME
        api_settings.URL_FIELD_NAME = 'global_url_field'

        class Serializer(serializers.HyperlinkedModelSerializer):

            class Meta:
                model = BlogPost
                fields = ('title', api_settings.URL_FIELD_NAME)

        self.Serializer = Serializer
        self.obj = BlogPost.objects.create(title="New blog post")

    def tearDown(self):
        api_settings.URL_FIELD_NAME = self.saved_url_field_name

    def test_overridden_url_field_name(self):
        request = factory.get('/posts/')
        serializer = self.Serializer(self.obj, context={'request': request})
        self.assertIn(api_settings.URL_FIELD_NAME, serializer.data)


class TestURLFieldNameByOptions(TestCase):
    urls = 'rest_framework.tests.test_hyperlinkedserializers'

    def setUp(self):
        class Serializer(serializers.HyperlinkedModelSerializer):

            class Meta:
                model = BlogPost
                fields = ('title', 'serializer_url_field')
                url_field_name = 'serializer_url_field'

        self.Serializer = Serializer
        self.obj = BlogPost.objects.create(title="New blog post")

    def test_overridden_url_field_name(self):
        request = factory.get('/posts/')
        serializer = self.Serializer(self.obj, context={'request': request})
        self.assertIn(self.Serializer.Meta.url_field_name, serializer.data)

########NEW FILE########
__FILENAME__ = test_multitable_inheritance
from __future__ import unicode_literals
from django.db import models
from django.test import TestCase
from rest_framework import serializers
from rest_framework.tests.models import RESTFrameworkModel


# Models
class ParentModel(RESTFrameworkModel):
    name1 = models.CharField(max_length=100)


class ChildModel(ParentModel):
    name2 = models.CharField(max_length=100)


class AssociatedModel(RESTFrameworkModel):
    ref = models.OneToOneField(ParentModel, primary_key=True)
    name = models.CharField(max_length=100)


# Serializers
class DerivedModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChildModel


class AssociatedModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssociatedModel


# Tests
class IneritedModelSerializationTests(TestCase):

    def test_multitable_inherited_model_fields_as_expected(self):
        """
        Assert that the parent pointer field is not included in the fields
        serialized fields
        """
        child = ChildModel(name1='parent name', name2='child name')
        serializer = DerivedModelSerializer(child)
        self.assertEqual(set(serializer.data.keys()),
                         set(['name1', 'name2', 'id']))

    def test_onetoone_primary_key_model_fields_as_expected(self):
        """
        Assert that a model with a onetoone field that is the primary key is
        not treated like a derived model
        """
        parent = ParentModel(name1='parent name')
        associate = AssociatedModel(name='hello', ref=parent)
        serializer = AssociatedModelSerializer(associate)
        self.assertEqual(set(serializer.data.keys()),
                         set(['name', 'ref']))

    def test_data_is_valid_without_parent_ptr(self):
        """
        Assert that the pointer to the parent table is not a required field
        for input data
        """
        data = {
            'name1': 'parent name',
            'name2': 'child name',
        }
        serializer = DerivedModelSerializer(data=data)
        self.assertEqual(serializer.is_valid(), True)

########NEW FILE########
__FILENAME__ = test_negotiation
from __future__ import unicode_literals
from django.test import TestCase
from rest_framework.negotiation import DefaultContentNegotiation
from rest_framework.request import Request
from rest_framework.renderers import BaseRenderer
from rest_framework.test import APIRequestFactory


factory = APIRequestFactory()


class MockJSONRenderer(BaseRenderer):
    media_type = 'application/json'


class MockHTMLRenderer(BaseRenderer):
    media_type = 'text/html'


class NoCharsetSpecifiedRenderer(BaseRenderer):
    media_type = 'my/media'


class TestAcceptedMediaType(TestCase):
    def setUp(self):
        self.renderers = [MockJSONRenderer(), MockHTMLRenderer()]
        self.negotiator = DefaultContentNegotiation()

    def select_renderer(self, request):
        return self.negotiator.select_renderer(request, self.renderers)

    def test_client_without_accept_use_renderer(self):
        request = Request(factory.get('/'))
        accepted_renderer, accepted_media_type = self.select_renderer(request)
        self.assertEqual(accepted_media_type, 'application/json')

    def test_client_underspecifies_accept_use_renderer(self):
        request = Request(factory.get('/', HTTP_ACCEPT='*/*'))
        accepted_renderer, accepted_media_type = self.select_renderer(request)
        self.assertEqual(accepted_media_type, 'application/json')

    def test_client_overspecifies_accept_use_client(self):
        request = Request(factory.get('/', HTTP_ACCEPT='application/json; indent=8'))
        accepted_renderer, accepted_media_type = self.select_renderer(request)
        self.assertEqual(accepted_media_type, 'application/json; indent=8')

########NEW FILE########
__FILENAME__ = test_nullable_fields
from django.core.urlresolvers import reverse

from rest_framework.compat import patterns, url
from rest_framework.test import APITestCase
from rest_framework.tests.models import NullableForeignKeySource
from rest_framework.tests.serializers import NullableFKSourceSerializer
from rest_framework.tests.views import NullableFKSourceDetail


urlpatterns = patterns(
    '',
    url(r'^objects/(?P<pk>\d+)/$', NullableFKSourceDetail.as_view(), name='object-detail'),
)


class NullableForeignKeyTests(APITestCase):
    """
    DRF should be able to handle nullable foreign keys when a test
    Client POST/PUT request is made with its own serialized object.
    """
    urls = 'rest_framework.tests.test_nullable_fields'

    def test_updating_object_with_null_fk(self):
        obj = NullableForeignKeySource(name='example', target=None)
        obj.save()
        serialized_data = NullableFKSourceSerializer(obj).data

        response = self.client.put(reverse('object-detail', args=[obj.pk]), serialized_data)

        self.assertEqual(response.data, serialized_data)

########NEW FILE########
__FILENAME__ = test_pagination
from __future__ import unicode_literals
import datetime
from decimal import Decimal
from django.db import models
from django.core.paginator import Paginator
from django.test import TestCase
from django.utils import unittest
from rest_framework import generics, status, pagination, filters, serializers
from rest_framework.compat import django_filters
from rest_framework.test import APIRequestFactory
from rest_framework.tests.models import BasicModel
from .models import FilterableItem

factory = APIRequestFactory()

# Helper function to split arguments out of an url
def split_arguments_from_url(url):
    if '?' not in url:
        return url

    path, args = url.split('?')
    args = dict(r.split('=') for r in args.split('&'))
    return path, args


class RootView(generics.ListCreateAPIView):
    """
    Example description for OPTIONS.
    """
    model = BasicModel
    paginate_by = 10


class DefaultPageSizeKwargView(generics.ListAPIView):
    """
    View for testing default paginate_by_param usage
    """
    model = BasicModel


class PaginateByParamView(generics.ListAPIView):
    """
    View for testing custom paginate_by_param usage
    """
    model = BasicModel
    paginate_by_param = 'page_size'


class MaxPaginateByView(generics.ListAPIView):
    """
    View for testing custom max_paginate_by usage
    """
    model = BasicModel
    paginate_by = 3
    max_paginate_by = 5
    paginate_by_param = 'page_size'


class IntegrationTestPagination(TestCase):
    """
    Integration tests for paginated list views.
    """

    def setUp(self):
        """
        Create 26 BasicModel instances.
        """
        for char in 'abcdefghijklmnopqrstuvwxyz':
            BasicModel(text=char * 3).save()
        self.objects = BasicModel.objects
        self.data = [
            {'id': obj.id, 'text': obj.text}
            for obj in self.objects.all()
        ]
        self.view = RootView.as_view()

    def test_get_paginated_root_view(self):
        """
        GET requests to paginated ListCreateAPIView should return paginated results.
        """
        request = factory.get('/')
        # Note: Database queries are a `SELECT COUNT`, and `SELECT <fields>`
        with self.assertNumQueries(2):
            response = self.view(request).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 26)
        self.assertEqual(response.data['results'], self.data[:10])
        self.assertNotEqual(response.data['next'], None)
        self.assertEqual(response.data['previous'], None)

        request = factory.get(*split_arguments_from_url(response.data['next']))
        with self.assertNumQueries(2):
            response = self.view(request).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 26)
        self.assertEqual(response.data['results'], self.data[10:20])
        self.assertNotEqual(response.data['next'], None)
        self.assertNotEqual(response.data['previous'], None)

        request = factory.get(*split_arguments_from_url(response.data['next']))
        with self.assertNumQueries(2):
            response = self.view(request).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 26)
        self.assertEqual(response.data['results'], self.data[20:])
        self.assertEqual(response.data['next'], None)
        self.assertNotEqual(response.data['previous'], None)


class IntegrationTestPaginationAndFiltering(TestCase):

    def setUp(self):
        """
        Create 50 FilterableItem instances.
        """
        base_data = ('a', Decimal('0.25'), datetime.date(2012, 10, 8))
        for i in range(26):
            text = chr(i + ord(base_data[0])) * 3  # Produces string 'aaa', 'bbb', etc.
            decimal = base_data[1] + i
            date = base_data[2] - datetime.timedelta(days=i * 2)
            FilterableItem(text=text, decimal=decimal, date=date).save()

        self.objects = FilterableItem.objects
        self.data = [
            {'id': obj.id, 'text': obj.text, 'decimal': obj.decimal, 'date': obj.date}
            for obj in self.objects.all()
        ]

    @unittest.skipUnless(django_filters, 'django-filter not installed')
    def test_get_django_filter_paginated_filtered_root_view(self):
        """
        GET requests to paginated filtered ListCreateAPIView should return
        paginated results. The next and previous links should preserve the
        filtered parameters.
        """
        class DecimalFilter(django_filters.FilterSet):
            decimal = django_filters.NumberFilter(lookup_type='lt')

            class Meta:
                model = FilterableItem
                fields = ['text', 'decimal', 'date']

        class FilterFieldsRootView(generics.ListCreateAPIView):
            model = FilterableItem
            paginate_by = 10
            filter_class = DecimalFilter
            filter_backends = (filters.DjangoFilterBackend,)

        view = FilterFieldsRootView.as_view()

        EXPECTED_NUM_QUERIES = 2

        request = factory.get('/', {'decimal': '15.20'})
        with self.assertNumQueries(EXPECTED_NUM_QUERIES):
            response = view(request).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 15)
        self.assertEqual(response.data['results'], self.data[:10])
        self.assertNotEqual(response.data['next'], None)
        self.assertEqual(response.data['previous'], None)

        request = factory.get(*split_arguments_from_url(response.data['next']))
        with self.assertNumQueries(EXPECTED_NUM_QUERIES):
            response = view(request).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 15)
        self.assertEqual(response.data['results'], self.data[10:15])
        self.assertEqual(response.data['next'], None)
        self.assertNotEqual(response.data['previous'], None)

        request = factory.get(*split_arguments_from_url(response.data['previous']))
        with self.assertNumQueries(EXPECTED_NUM_QUERIES):
            response = view(request).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 15)
        self.assertEqual(response.data['results'], self.data[:10])
        self.assertNotEqual(response.data['next'], None)
        self.assertEqual(response.data['previous'], None)

    def test_get_basic_paginated_filtered_root_view(self):
        """
        Same as `test_get_django_filter_paginated_filtered_root_view`,
        except using a custom filter backend instead of the django-filter
        backend,
        """

        class DecimalFilterBackend(filters.BaseFilterBackend):
            def filter_queryset(self, request, queryset, view):
                return queryset.filter(decimal__lt=Decimal(request.GET['decimal']))

        class BasicFilterFieldsRootView(generics.ListCreateAPIView):
            model = FilterableItem
            paginate_by = 10
            filter_backends = (DecimalFilterBackend,)

        view = BasicFilterFieldsRootView.as_view()

        request = factory.get('/', {'decimal': '15.20'})
        with self.assertNumQueries(2):
            response = view(request).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 15)
        self.assertEqual(response.data['results'], self.data[:10])
        self.assertNotEqual(response.data['next'], None)
        self.assertEqual(response.data['previous'], None)

        request = factory.get(*split_arguments_from_url(response.data['next']))
        with self.assertNumQueries(2):
            response = view(request).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 15)
        self.assertEqual(response.data['results'], self.data[10:15])
        self.assertEqual(response.data['next'], None)
        self.assertNotEqual(response.data['previous'], None)

        request = factory.get(*split_arguments_from_url(response.data['previous']))
        with self.assertNumQueries(2):
            response = view(request).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 15)
        self.assertEqual(response.data['results'], self.data[:10])
        self.assertNotEqual(response.data['next'], None)
        self.assertEqual(response.data['previous'], None)


class PassOnContextPaginationSerializer(pagination.PaginationSerializer):
    class Meta:
        object_serializer_class = serializers.Serializer


class UnitTestPagination(TestCase):
    """
    Unit tests for pagination of primitive objects.
    """

    def setUp(self):
        self.objects = [char * 3 for char in 'abcdefghijklmnopqrstuvwxyz']
        paginator = Paginator(self.objects, 10)
        self.first_page = paginator.page(1)
        self.last_page = paginator.page(3)

    def test_native_pagination(self):
        serializer = pagination.PaginationSerializer(self.first_page)
        self.assertEqual(serializer.data['count'], 26)
        self.assertEqual(serializer.data['next'], '?page=2')
        self.assertEqual(serializer.data['previous'], None)
        self.assertEqual(serializer.data['results'], self.objects[:10])

        serializer = pagination.PaginationSerializer(self.last_page)
        self.assertEqual(serializer.data['count'], 26)
        self.assertEqual(serializer.data['next'], None)
        self.assertEqual(serializer.data['previous'], '?page=2')
        self.assertEqual(serializer.data['results'], self.objects[20:])

    def test_context_available_in_result(self):
        """
        Ensure context gets passed through to the object serializer.
        """
        serializer = PassOnContextPaginationSerializer(self.first_page, context={'foo': 'bar'})
        serializer.data
        results = serializer.fields[serializer.results_field]
        self.assertEqual(serializer.context, results.context)


class TestUnpaginated(TestCase):
    """
    Tests for list views without pagination.
    """

    def setUp(self):
        """
        Create 13 BasicModel instances.
        """
        for i in range(13):
            BasicModel(text=i).save()
        self.objects = BasicModel.objects
        self.data = [
        {'id': obj.id, 'text': obj.text}
        for obj in self.objects.all()
        ]
        self.view = DefaultPageSizeKwargView.as_view()

    def test_unpaginated(self):
        """
        Tests the default page size for this view.
        no page size --> no limit --> no meta data
        """
        request = factory.get('/')
        response = self.view(request)
        self.assertEqual(response.data, self.data)


class TestCustomPaginateByParam(TestCase):
    """
    Tests for list views with default page size kwarg
    """

    def setUp(self):
        """
        Create 13 BasicModel instances.
        """
        for i in range(13):
            BasicModel(text=i).save()
        self.objects = BasicModel.objects
        self.data = [
        {'id': obj.id, 'text': obj.text}
        for obj in self.objects.all()
        ]
        self.view = PaginateByParamView.as_view()

    def test_default_page_size(self):
        """
        Tests the default page size for this view.
        no page size --> no limit --> no meta data
        """
        request = factory.get('/')
        response = self.view(request).render()
        self.assertEqual(response.data, self.data)

    def test_paginate_by_param(self):
        """
        If paginate_by_param is set, the new kwarg should limit per view requests.
        """
        request = factory.get('/', {'page_size': 5})
        response = self.view(request).render()
        self.assertEqual(response.data['count'], 13)
        self.assertEqual(response.data['results'], self.data[:5])


class TestMaxPaginateByParam(TestCase):
    """
    Tests for list views with max_paginate_by kwarg
    """

    def setUp(self):
        """
        Create 13 BasicModel instances.
        """
        for i in range(13):
            BasicModel(text=i).save()
        self.objects = BasicModel.objects
        self.data = [
            {'id': obj.id, 'text': obj.text}
            for obj in self.objects.all()
        ]
        self.view = MaxPaginateByView.as_view()

    def test_max_paginate_by(self):
        """
        If max_paginate_by is set, it should limit page size for the view.
        """
        request = factory.get('/', data={'page_size': 10})
        response = self.view(request).render()
        self.assertEqual(response.data['count'], 13)
        self.assertEqual(response.data['results'], self.data[:5])

    def test_max_paginate_by_without_page_size_param(self):
        """
        If max_paginate_by is set, but client does not specifiy page_size,
        standard `paginate_by` behavior should be used.
        """
        request = factory.get('/')
        response = self.view(request).render()
        self.assertEqual(response.data['results'], self.data[:3])


### Tests for context in pagination serializers

class CustomField(serializers.Field):
    def to_native(self, value):
        if not 'view' in self.context:
            raise RuntimeError("context isn't getting passed into custom field")
        return "value"


class BasicModelSerializer(serializers.Serializer):
    text = CustomField()

    def __init__(self, *args, **kwargs):
        super(BasicModelSerializer, self).__init__(*args, **kwargs)
        if not 'view' in self.context:
            raise RuntimeError("context isn't getting passed into serializer init")


class TestContextPassedToCustomField(TestCase):
    def setUp(self):
        BasicModel.objects.create(text='ala ma kota')

    def test_with_pagination(self):
        class ListView(generics.ListCreateAPIView):
            model = BasicModel
            serializer_class = BasicModelSerializer
            paginate_by = 1

        self.view = ListView.as_view()
        request = factory.get('/')
        response = self.view(request).render()

        self.assertEqual(response.status_code, status.HTTP_200_OK)


### Tests for custom pagination serializers

class LinksSerializer(serializers.Serializer):
    next = pagination.NextPageField(source='*')
    prev = pagination.PreviousPageField(source='*')


class CustomPaginationSerializer(pagination.BasePaginationSerializer):
    links = LinksSerializer(source='*')  # Takes the page object as the source
    total_results = serializers.Field(source='paginator.count')

    results_field = 'objects'


class TestCustomPaginationSerializer(TestCase):
    def setUp(self):
        objects = ['john', 'paul', 'george', 'ringo']
        paginator = Paginator(objects, 2)
        self.page = paginator.page(1)

    def test_custom_pagination_serializer(self):
        request = APIRequestFactory().get('/foobar')
        serializer = CustomPaginationSerializer(
            instance=self.page,
            context={'request': request}
        )
        expected = {
            'links': {
                'next': 'http://testserver/foobar?page=2',
                'prev': None
            },
            'total_results': 4,
            'objects': ['john', 'paul']
        }
        self.assertEqual(serializer.data, expected)


class NonIntegerPage(object):

    def __init__(self, paginator, object_list, prev_token, token, next_token):
        self.paginator = paginator
        self.object_list = object_list
        self.prev_token = prev_token
        self.token = token
        self.next_token = next_token

    def has_next(self):
        return not not self.next_token

    def next_page_number(self):
        return self.next_token

    def has_previous(self):
        return not not self.prev_token

    def previous_page_number(self):
        return self.prev_token


class NonIntegerPaginator(object):

    def __init__(self, object_list, per_page):
        self.object_list = object_list
        self.per_page = per_page

    def count(self):
        # pretend like we don't know how many pages we have
        return None

    def page(self, token=None):
        if token:
            try:
                first = self.object_list.index(token)
            except ValueError:
                first = 0
        else:
            first = 0
        n = len(self.object_list)
        last = min(first + self.per_page, n)
        prev_token = self.object_list[last - (2 * self.per_page)] if first else None
        next_token = self.object_list[last] if last < n else None
        return NonIntegerPage(self, self.object_list[first:last], prev_token, token, next_token)


class TestNonIntegerPagination(TestCase):


    def test_custom_pagination_serializer(self):
        objects = ['john', 'paul', 'george', 'ringo']
        paginator = NonIntegerPaginator(objects, 2)

        request = APIRequestFactory().get('/foobar')
        serializer = CustomPaginationSerializer(
            instance=paginator.page(),
            context={'request': request}
        )
        expected = {
            'links': {
                'next': 'http://testserver/foobar?page={0}'.format(objects[2]),
                'prev': None
            },
            'total_results': None,
            'objects': objects[:2]
        }
        self.assertEqual(serializer.data, expected)

        request = APIRequestFactory().get('/foobar')
        serializer = CustomPaginationSerializer(
            instance=paginator.page('george'),
            context={'request': request}
        )
        expected = {
            'links': {
                'next': None,
                'prev': 'http://testserver/foobar?page={0}'.format(objects[0]),
            },
            'total_results': None,
            'objects': objects[2:]
        }
        self.assertEqual(serializer.data, expected)

########NEW FILE########
__FILENAME__ = test_parsers
from __future__ import unicode_literals
from rest_framework.compat import StringIO
from django import forms
from django.core.files.uploadhandler import MemoryFileUploadHandler
from django.test import TestCase
from django.utils import unittest
from rest_framework.compat import etree
from rest_framework.parsers import FormParser, FileUploadParser
from rest_framework.parsers import XMLParser
import datetime


class Form(forms.Form):
    field1 = forms.CharField(max_length=3)
    field2 = forms.CharField()


class TestFormParser(TestCase):
    def setUp(self):
        self.string = "field1=abc&field2=defghijk"

    def test_parse(self):
        """ Make sure the `QueryDict` works OK """
        parser = FormParser()

        stream = StringIO(self.string)
        data = parser.parse(stream)

        self.assertEqual(Form(data).is_valid(), True)


class TestXMLParser(TestCase):
    def setUp(self):
        self._input = StringIO(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<root>'
            '<field_a>121.0</field_a>'
            '<field_b>dasd</field_b>'
            '<field_c></field_c>'
            '<field_d>2011-12-25 12:45:00</field_d>'
            '</root>'
        )
        self._data = {
            'field_a': 121,
            'field_b': 'dasd',
            'field_c': None,
            'field_d': datetime.datetime(2011, 12, 25, 12, 45, 00)
        }
        self._complex_data_input = StringIO(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<root>'
            '<creation_date>2011-12-25 12:45:00</creation_date>'
            '<sub_data_list>'
            '<list-item><sub_id>1</sub_id><sub_name>first</sub_name></list-item>'
            '<list-item><sub_id>2</sub_id><sub_name>second</sub_name></list-item>'
            '</sub_data_list>'
            '<name>name</name>'
            '</root>'
        )
        self._complex_data = {
            "creation_date": datetime.datetime(2011, 12, 25, 12, 45, 00),
            "name": "name",
            "sub_data_list": [
                {
                    "sub_id": 1,
                    "sub_name": "first"
                },
                {
                    "sub_id": 2,
                    "sub_name": "second"
                }
            ]
        }

    @unittest.skipUnless(etree, 'defusedxml not installed')
    def test_parse(self):
        parser = XMLParser()
        data = parser.parse(self._input)
        self.assertEqual(data, self._data)

    @unittest.skipUnless(etree, 'defusedxml not installed')
    def test_complex_data_parse(self):
        parser = XMLParser()
        data = parser.parse(self._complex_data_input)
        self.assertEqual(data, self._complex_data)


class TestFileUploadParser(TestCase):
    def setUp(self):
        class MockRequest(object):
            pass
        from io import BytesIO
        self.stream = BytesIO(
            "Test text file".encode('utf-8')
        )
        request = MockRequest()
        request.upload_handlers = (MemoryFileUploadHandler(),)
        request.META = {
            'HTTP_CONTENT_DISPOSITION': 'Content-Disposition: inline; filename=file.txt',
            'HTTP_CONTENT_LENGTH': 14,
        }
        self.parser_context = {'request': request, 'kwargs': {}}

    def test_parse(self):
        """ Make sure the `QueryDict` works OK """
        parser = FileUploadParser()
        self.stream.seek(0)
        data_and_files = parser.parse(self.stream, None, self.parser_context)
        file_obj = data_and_files.files['file']
        self.assertEqual(file_obj._size, 14)

    def test_get_filename(self):
        parser = FileUploadParser()
        filename = parser.get_filename(self.stream, None, self.parser_context)
        self.assertEqual(filename, 'file.txt')

########NEW FILE########
__FILENAME__ = test_permissions
from __future__ import unicode_literals
from django.contrib.auth.models import User, Permission, Group
from django.db import models
from django.test import TestCase
from django.utils import unittest
from rest_framework import generics, status, permissions, authentication, HTTP_HEADER_ENCODING
from rest_framework.compat import guardian, get_model_name
from rest_framework.filters import DjangoObjectPermissionsFilter
from rest_framework.test import APIRequestFactory
from rest_framework.tests.models import BasicModel
import base64

factory = APIRequestFactory()

class RootView(generics.ListCreateAPIView):
    model = BasicModel
    authentication_classes = [authentication.BasicAuthentication]
    permission_classes = [permissions.DjangoModelPermissions]


class InstanceView(generics.RetrieveUpdateDestroyAPIView):
    model = BasicModel
    authentication_classes = [authentication.BasicAuthentication]
    permission_classes = [permissions.DjangoModelPermissions]

root_view = RootView.as_view()
instance_view = InstanceView.as_view()


def basic_auth_header(username, password):
    credentials = ('%s:%s' % (username, password))
    base64_credentials = base64.b64encode(credentials.encode(HTTP_HEADER_ENCODING)).decode(HTTP_HEADER_ENCODING)
    return 'Basic %s' % base64_credentials


class ModelPermissionsIntegrationTests(TestCase):
    def setUp(self):
        User.objects.create_user('disallowed', 'disallowed@example.com', 'password')
        user = User.objects.create_user('permitted', 'permitted@example.com', 'password')
        user.user_permissions = [
            Permission.objects.get(codename='add_basicmodel'),
            Permission.objects.get(codename='change_basicmodel'),
            Permission.objects.get(codename='delete_basicmodel')
        ]
        user = User.objects.create_user('updateonly', 'updateonly@example.com', 'password')
        user.user_permissions = [
            Permission.objects.get(codename='change_basicmodel'),
        ]

        self.permitted_credentials = basic_auth_header('permitted', 'password')
        self.disallowed_credentials = basic_auth_header('disallowed', 'password')
        self.updateonly_credentials = basic_auth_header('updateonly', 'password')

        BasicModel(text='foo').save()

    def test_has_create_permissions(self):
        request = factory.post('/', {'text': 'foobar'}, format='json',
                               HTTP_AUTHORIZATION=self.permitted_credentials)
        response = root_view(request, pk=1)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_has_put_permissions(self):
        request = factory.put('/1', {'text': 'foobar'}, format='json',
                              HTTP_AUTHORIZATION=self.permitted_credentials)
        response = instance_view(request, pk='1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_has_delete_permissions(self):
        request = factory.delete('/1', HTTP_AUTHORIZATION=self.permitted_credentials)
        response = instance_view(request, pk=1)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_does_not_have_create_permissions(self):
        request = factory.post('/', {'text': 'foobar'}, format='json',
                               HTTP_AUTHORIZATION=self.disallowed_credentials)
        response = root_view(request, pk=1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_does_not_have_put_permissions(self):
        request = factory.put('/1', {'text': 'foobar'}, format='json',
                              HTTP_AUTHORIZATION=self.disallowed_credentials)
        response = instance_view(request, pk='1')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_does_not_have_delete_permissions(self):
        request = factory.delete('/1', HTTP_AUTHORIZATION=self.disallowed_credentials)
        response = instance_view(request, pk=1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_put_as_create_permissions(self):
        # User only has update permissions - should be able to update an entity.
        request = factory.put('/1', {'text': 'foobar'}, format='json',
                              HTTP_AUTHORIZATION=self.updateonly_credentials)
        response = instance_view(request, pk='1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # But if PUTing to a new entity, permission should be denied.
        request = factory.put('/2', {'text': 'foobar'}, format='json',
                              HTTP_AUTHORIZATION=self.updateonly_credentials)
        response = instance_view(request, pk='2')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_options_permitted(self):
        request = factory.options('/',
                               HTTP_AUTHORIZATION=self.permitted_credentials)
        response = root_view(request, pk='1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('actions', response.data)
        self.assertEqual(list(response.data['actions'].keys()), ['POST'])

        request = factory.options('/1',
                               HTTP_AUTHORIZATION=self.permitted_credentials)
        response = instance_view(request, pk='1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('actions', response.data)
        self.assertEqual(list(response.data['actions'].keys()), ['PUT'])

    def test_options_disallowed(self):
        request = factory.options('/',
                               HTTP_AUTHORIZATION=self.disallowed_credentials)
        response = root_view(request, pk='1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('actions', response.data)

        request = factory.options('/1',
                               HTTP_AUTHORIZATION=self.disallowed_credentials)
        response = instance_view(request, pk='1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('actions', response.data)

    def test_options_updateonly(self):
        request = factory.options('/',
                               HTTP_AUTHORIZATION=self.updateonly_credentials)
        response = root_view(request, pk='1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('actions', response.data)

        request = factory.options('/1',
                               HTTP_AUTHORIZATION=self.updateonly_credentials)
        response = instance_view(request, pk='1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('actions', response.data)
        self.assertEqual(list(response.data['actions'].keys()), ['PUT'])


class BasicPermModel(models.Model):
    text = models.CharField(max_length=100)

    class Meta:
        app_label = 'tests'
        permissions = (
            ('view_basicpermmodel', 'Can view basic perm model'),
            # add, change, delete built in to django
        )

# Custom object-level permission, that includes 'view' permissions
class ViewObjectPermissions(permissions.DjangoObjectPermissions):
    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': ['%(app_label)s.view_%(model_name)s'],
        'HEAD': ['%(app_label)s.view_%(model_name)s'],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }


class ObjectPermissionInstanceView(generics.RetrieveUpdateDestroyAPIView):
    model = BasicPermModel
    authentication_classes = [authentication.BasicAuthentication]
    permission_classes = [ViewObjectPermissions]

object_permissions_view = ObjectPermissionInstanceView.as_view()


class ObjectPermissionListView(generics.ListAPIView):
    model = BasicPermModel
    authentication_classes = [authentication.BasicAuthentication]
    permission_classes = [ViewObjectPermissions]

object_permissions_list_view = ObjectPermissionListView.as_view()


@unittest.skipUnless(guardian, 'django-guardian not installed')
class ObjectPermissionsIntegrationTests(TestCase):
    """
    Integration tests for the object level permissions API.
    """
    @classmethod
    def setUpClass(cls):
        from guardian.shortcuts import assign_perm

        # create users
        create = User.objects.create_user
        users = {
            'fullaccess': create('fullaccess', 'fullaccess@example.com', 'password'),
            'readonly': create('readonly', 'readonly@example.com', 'password'),
            'writeonly': create('writeonly', 'writeonly@example.com', 'password'),
            'deleteonly': create('deleteonly', 'deleteonly@example.com', 'password'),
        }

        # give everyone model level permissions, as we are not testing those
        everyone = Group.objects.create(name='everyone')
        model_name = get_model_name(BasicPermModel)
        app_label = BasicPermModel._meta.app_label
        f = '{0}_{1}'.format
        perms = {
            'view':   f('view', model_name),
            'change': f('change', model_name),
            'delete': f('delete', model_name)
        }
        for perm in perms.values():
            perm = '{0}.{1}'.format(app_label, perm)
            assign_perm(perm, everyone)
        everyone.user_set.add(*users.values())

        cls.perms = perms
        cls.users = users

    def setUp(self):
        from guardian.shortcuts import assign_perm
        perms = self.perms
        users = self.users

        # appropriate object level permissions
        readers = Group.objects.create(name='readers')
        writers = Group.objects.create(name='writers')
        deleters = Group.objects.create(name='deleters')

        model = BasicPermModel.objects.create(text='foo')
        
        assign_perm(perms['view'], readers, model)
        assign_perm(perms['change'], writers, model)
        assign_perm(perms['delete'], deleters, model)

        readers.user_set.add(users['fullaccess'], users['readonly'])
        writers.user_set.add(users['fullaccess'], users['writeonly'])
        deleters.user_set.add(users['fullaccess'], users['deleteonly'])

        self.credentials = {}
        for user in users.values():
            self.credentials[user.username] = basic_auth_header(user.username, 'password')

    # Delete
    def test_can_delete_permissions(self):
        request = factory.delete('/1', HTTP_AUTHORIZATION=self.credentials['deleteonly'])
        response = object_permissions_view(request, pk='1')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_cannot_delete_permissions(self):
        request = factory.delete('/1', HTTP_AUTHORIZATION=self.credentials['readonly'])
        response = object_permissions_view(request, pk='1')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # Update
    def test_can_update_permissions(self):
        request = factory.patch('/1', {'text': 'foobar'}, format='json',
            HTTP_AUTHORIZATION=self.credentials['writeonly'])
        response = object_permissions_view(request, pk='1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('text'), 'foobar')

    def test_cannot_update_permissions(self):
        request = factory.patch('/1', {'text': 'foobar'}, format='json',
            HTTP_AUTHORIZATION=self.credentials['deleteonly'])
        response = object_permissions_view(request, pk='1')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_update_permissions_non_existing(self):
        request = factory.patch('/999', {'text': 'foobar'}, format='json',
            HTTP_AUTHORIZATION=self.credentials['deleteonly'])
        response = object_permissions_view(request, pk='999')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # Read
    def test_can_read_permissions(self):
        request = factory.get('/1', HTTP_AUTHORIZATION=self.credentials['readonly'])
        response = object_permissions_view(request, pk='1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cannot_read_permissions(self):
        request = factory.get('/1', HTTP_AUTHORIZATION=self.credentials['writeonly'])
        response = object_permissions_view(request, pk='1')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # Read list
    def test_can_read_list_permissions(self):
        request = factory.get('/', HTTP_AUTHORIZATION=self.credentials['readonly'])
        object_permissions_list_view.cls.filter_backends = (DjangoObjectPermissionsFilter,)
        response = object_permissions_list_view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0].get('id'), 1)

    def test_cannot_read_list_permissions(self):
        request = factory.get('/', HTTP_AUTHORIZATION=self.credentials['writeonly'])
        object_permissions_list_view.cls.filter_backends = (DjangoObjectPermissionsFilter,)
        response = object_permissions_list_view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(response.data, [])

########NEW FILE########
__FILENAME__ = test_relations
"""
General tests for relational fields.
"""
from __future__ import unicode_literals
from django import get_version
from django.db import models
from django.test import TestCase
from django.utils import unittest
from rest_framework import serializers
from rest_framework.tests.models import BlogPost


class NullModel(models.Model):
    pass


class FieldTests(TestCase):
    def test_pk_related_field_with_empty_string(self):
        """
        Regression test for #446

        https://github.com/tomchristie/django-rest-framework/issues/446
        """
        field = serializers.PrimaryKeyRelatedField(queryset=NullModel.objects.all())
        self.assertRaises(serializers.ValidationError, field.from_native, '')
        self.assertRaises(serializers.ValidationError, field.from_native, [])

    def test_hyperlinked_related_field_with_empty_string(self):
        field = serializers.HyperlinkedRelatedField(queryset=NullModel.objects.all(), view_name='')
        self.assertRaises(serializers.ValidationError, field.from_native, '')
        self.assertRaises(serializers.ValidationError, field.from_native, [])

    def test_slug_related_field_with_empty_string(self):
        field = serializers.SlugRelatedField(queryset=NullModel.objects.all(), slug_field='pk')
        self.assertRaises(serializers.ValidationError, field.from_native, '')
        self.assertRaises(serializers.ValidationError, field.from_native, [])


class TestManyRelatedMixin(TestCase):
    def test_missing_many_to_many_related_field(self):
        '''
        Regression test for #632

        https://github.com/tomchristie/django-rest-framework/pull/632
        '''
        field = serializers.RelatedField(many=True, read_only=False)

        into = {}
        field.field_from_native({}, None, 'field_name', into)
        self.assertEqual(into['field_name'], [])


# Regression tests for #694 (`source` attribute on related fields)

class RelatedFieldSourceTests(TestCase):
    def test_related_manager_source(self):
        """
        Relational fields should be able to use manager-returning methods as their source.
        """
        BlogPost.objects.create(title='blah')
        field = serializers.RelatedField(many=True, source='get_blogposts_manager')

        class ClassWithManagerMethod(object):
            def get_blogposts_manager(self):
                return BlogPost.objects

        obj = ClassWithManagerMethod()
        value = field.field_to_native(obj, 'field_name')
        self.assertEqual(value, ['BlogPost object'])

    def test_related_queryset_source(self):
        """
        Relational fields should be able to use queryset-returning methods as their source.
        """
        BlogPost.objects.create(title='blah')
        field = serializers.RelatedField(many=True, source='get_blogposts_queryset')

        class ClassWithQuerysetMethod(object):
            def get_blogposts_queryset(self):
                return BlogPost.objects.all()

        obj = ClassWithQuerysetMethod()
        value = field.field_to_native(obj, 'field_name')
        self.assertEqual(value, ['BlogPost object'])

    def test_dotted_source(self):
        """
        Source argument should support dotted.source notation.
        """
        BlogPost.objects.create(title='blah')
        field = serializers.RelatedField(many=True, source='a.b.c')

        class ClassWithQuerysetMethod(object):
            a = {
                'b': {
                    'c': BlogPost.objects.all()
                }
            }

        obj = ClassWithQuerysetMethod()
        value = field.field_to_native(obj, 'field_name')
        self.assertEqual(value, ['BlogPost object'])

    # Regression for #1129
    def test_exception_for_incorect_fk(self):
        """
        Check that the exception message are correct if the source field
        doesn't exist.
        """
        from rest_framework.tests.models import ManyToManySource
        class Meta:
            model = ManyToManySource
        attrs = {
            'name': serializers.SlugRelatedField(
                slug_field='name', source='banzai'),
            'Meta': Meta,
        }

        TestSerializer = type(str('TestSerializer'),
            (serializers.ModelSerializer,), attrs)
        with self.assertRaises(AttributeError):
            TestSerializer(data={'name': 'foo'})

@unittest.skipIf(get_version() < '1.6.0', 'Upstream behaviour changed in v1.6')
class RelatedFieldChoicesTests(TestCase):
    """
    Tests for #1408 "Web browseable API doesn't have blank option on drop down list box"
    https://github.com/tomchristie/django-rest-framework/issues/1408
    """
    def test_blank_option_is_added_to_choice_if_required_equals_false(self):
        """

        """
        post = BlogPost(title="Checking blank option is added")
        post.save()

        queryset = BlogPost.objects.all()
        field = serializers.RelatedField(required=False, queryset=queryset)

        choice_count = BlogPost.objects.count()
        widget_count = len(field.widget.choices)

        self.assertEqual(widget_count, choice_count + 1, 'BLANK_CHOICE_DASH option should have been added')


########NEW FILE########
__FILENAME__ = test_relations_hyperlink
from __future__ import unicode_literals
from django.test import TestCase
from rest_framework import serializers
from rest_framework.compat import patterns, url
from rest_framework.test import APIRequestFactory
from rest_framework.tests.models import (
    BlogPost,
    ManyToManyTarget, ManyToManySource, ForeignKeyTarget, ForeignKeySource,
    NullableForeignKeySource, OneToOneTarget, NullableOneToOneSource
)

factory = APIRequestFactory()
request = factory.get('/')  # Just to ensure we have a request in the serializer context


def dummy_view(request, pk):
    pass

urlpatterns = patterns('',
    url(r'^dummyurl/(?P<pk>[0-9]+)/$', dummy_view, name='dummy-url'),
    url(r'^manytomanysource/(?P<pk>[0-9]+)/$', dummy_view, name='manytomanysource-detail'),
    url(r'^manytomanytarget/(?P<pk>[0-9]+)/$', dummy_view, name='manytomanytarget-detail'),
    url(r'^foreignkeysource/(?P<pk>[0-9]+)/$', dummy_view, name='foreignkeysource-detail'),
    url(r'^foreignkeytarget/(?P<pk>[0-9]+)/$', dummy_view, name='foreignkeytarget-detail'),
    url(r'^nullableforeignkeysource/(?P<pk>[0-9]+)/$', dummy_view, name='nullableforeignkeysource-detail'),
    url(r'^onetoonetarget/(?P<pk>[0-9]+)/$', dummy_view, name='onetoonetarget-detail'),
    url(r'^nullableonetoonesource/(?P<pk>[0-9]+)/$', dummy_view, name='nullableonetoonesource-detail'),
)


# ManyToMany
class ManyToManyTargetSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ManyToManyTarget
        fields = ('url', 'name', 'sources')


class ManyToManySourceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ManyToManySource
        fields = ('url', 'name', 'targets')


# ForeignKey
class ForeignKeyTargetSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ForeignKeyTarget
        fields = ('url', 'name', 'sources')


class ForeignKeySourceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ForeignKeySource
        fields = ('url', 'name', 'target')


# Nullable ForeignKey
class NullableForeignKeySourceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = NullableForeignKeySource
        fields = ('url', 'name', 'target')


# Nullable OneToOne
class NullableOneToOneTargetSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = OneToOneTarget
        fields = ('url', 'name', 'nullable_source')


# TODO: Add test that .data cannot be accessed prior to .is_valid

class HyperlinkedManyToManyTests(TestCase):
    urls = 'rest_framework.tests.test_relations_hyperlink'

    def setUp(self):
        for idx in range(1, 4):
            target = ManyToManyTarget(name='target-%d' % idx)
            target.save()
            source = ManyToManySource(name='source-%d' % idx)
            source.save()
            for target in ManyToManyTarget.objects.all():
                source.targets.add(target)

    def test_many_to_many_retrieve(self):
        queryset = ManyToManySource.objects.all()
        serializer = ManyToManySourceSerializer(queryset, many=True, context={'request': request})
        expected = [
                {'url': 'http://testserver/manytomanysource/1/', 'name': 'source-1', 'targets': ['http://testserver/manytomanytarget/1/']},
                {'url': 'http://testserver/manytomanysource/2/', 'name': 'source-2', 'targets': ['http://testserver/manytomanytarget/1/', 'http://testserver/manytomanytarget/2/']},
                {'url': 'http://testserver/manytomanysource/3/', 'name': 'source-3', 'targets': ['http://testserver/manytomanytarget/1/', 'http://testserver/manytomanytarget/2/', 'http://testserver/manytomanytarget/3/']}
        ]
        self.assertEqual(serializer.data, expected)

    def test_reverse_many_to_many_retrieve(self):
        queryset = ManyToManyTarget.objects.all()
        serializer = ManyToManyTargetSerializer(queryset, many=True, context={'request': request})
        expected = [
            {'url': 'http://testserver/manytomanytarget/1/', 'name': 'target-1', 'sources': ['http://testserver/manytomanysource/1/', 'http://testserver/manytomanysource/2/', 'http://testserver/manytomanysource/3/']},
            {'url': 'http://testserver/manytomanytarget/2/', 'name': 'target-2', 'sources': ['http://testserver/manytomanysource/2/', 'http://testserver/manytomanysource/3/']},
            {'url': 'http://testserver/manytomanytarget/3/', 'name': 'target-3', 'sources': ['http://testserver/manytomanysource/3/']}
        ]
        self.assertEqual(serializer.data, expected)

    def test_many_to_many_update(self):
        data = {'url': 'http://testserver/manytomanysource/1/', 'name': 'source-1', 'targets': ['http://testserver/manytomanytarget/1/', 'http://testserver/manytomanytarget/2/', 'http://testserver/manytomanytarget/3/']}
        instance = ManyToManySource.objects.get(pk=1)
        serializer = ManyToManySourceSerializer(instance, data=data, context={'request': request})
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertEqual(serializer.data, data)

        # Ensure source 1 is updated, and everything else is as expected
        queryset = ManyToManySource.objects.all()
        serializer = ManyToManySourceSerializer(queryset, many=True, context={'request': request})
        expected = [
                {'url': 'http://testserver/manytomanysource/1/', 'name': 'source-1', 'targets': ['http://testserver/manytomanytarget/1/', 'http://testserver/manytomanytarget/2/', 'http://testserver/manytomanytarget/3/']},
                {'url': 'http://testserver/manytomanysource/2/', 'name': 'source-2', 'targets': ['http://testserver/manytomanytarget/1/', 'http://testserver/manytomanytarget/2/']},
                {'url': 'http://testserver/manytomanysource/3/', 'name': 'source-3', 'targets': ['http://testserver/manytomanytarget/1/', 'http://testserver/manytomanytarget/2/', 'http://testserver/manytomanytarget/3/']}
        ]
        self.assertEqual(serializer.data, expected)

    def test_reverse_many_to_many_update(self):
        data = {'url': 'http://testserver/manytomanytarget/1/', 'name': 'target-1', 'sources': ['http://testserver/manytomanysource/1/']}
        instance = ManyToManyTarget.objects.get(pk=1)
        serializer = ManyToManyTargetSerializer(instance, data=data, context={'request': request})
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertEqual(serializer.data, data)

        # Ensure target 1 is updated, and everything else is as expected
        queryset = ManyToManyTarget.objects.all()
        serializer = ManyToManyTargetSerializer(queryset, many=True, context={'request': request})
        expected = [
            {'url': 'http://testserver/manytomanytarget/1/', 'name': 'target-1', 'sources': ['http://testserver/manytomanysource/1/']},
            {'url': 'http://testserver/manytomanytarget/2/', 'name': 'target-2', 'sources': ['http://testserver/manytomanysource/2/', 'http://testserver/manytomanysource/3/']},
            {'url': 'http://testserver/manytomanytarget/3/', 'name': 'target-3', 'sources': ['http://testserver/manytomanysource/3/']}

        ]
        self.assertEqual(serializer.data, expected)

    def test_many_to_many_create(self):
        data = {'url': 'http://testserver/manytomanysource/4/', 'name': 'source-4', 'targets': ['http://testserver/manytomanytarget/1/', 'http://testserver/manytomanytarget/3/']}
        serializer = ManyToManySourceSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, data)
        self.assertEqual(obj.name, 'source-4')

        # Ensure source 4 is added, and everything else is as expected
        queryset = ManyToManySource.objects.all()
        serializer = ManyToManySourceSerializer(queryset, many=True, context={'request': request})
        expected = [
            {'url': 'http://testserver/manytomanysource/1/', 'name': 'source-1', 'targets': ['http://testserver/manytomanytarget/1/']},
            {'url': 'http://testserver/manytomanysource/2/', 'name': 'source-2', 'targets': ['http://testserver/manytomanytarget/1/', 'http://testserver/manytomanytarget/2/']},
            {'url': 'http://testserver/manytomanysource/3/', 'name': 'source-3', 'targets': ['http://testserver/manytomanytarget/1/', 'http://testserver/manytomanytarget/2/', 'http://testserver/manytomanytarget/3/']},
            {'url': 'http://testserver/manytomanysource/4/', 'name': 'source-4', 'targets': ['http://testserver/manytomanytarget/1/', 'http://testserver/manytomanytarget/3/']}
        ]
        self.assertEqual(serializer.data, expected)

    def test_reverse_many_to_many_create(self):
        data = {'url': 'http://testserver/manytomanytarget/4/', 'name': 'target-4', 'sources': ['http://testserver/manytomanysource/1/', 'http://testserver/manytomanysource/3/']}
        serializer = ManyToManyTargetSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, data)
        self.assertEqual(obj.name, 'target-4')

        # Ensure target 4 is added, and everything else is as expected
        queryset = ManyToManyTarget.objects.all()
        serializer = ManyToManyTargetSerializer(queryset, many=True, context={'request': request})
        expected = [
            {'url': 'http://testserver/manytomanytarget/1/', 'name': 'target-1', 'sources': ['http://testserver/manytomanysource/1/', 'http://testserver/manytomanysource/2/', 'http://testserver/manytomanysource/3/']},
            {'url': 'http://testserver/manytomanytarget/2/', 'name': 'target-2', 'sources': ['http://testserver/manytomanysource/2/', 'http://testserver/manytomanysource/3/']},
            {'url': 'http://testserver/manytomanytarget/3/', 'name': 'target-3', 'sources': ['http://testserver/manytomanysource/3/']},
            {'url': 'http://testserver/manytomanytarget/4/', 'name': 'target-4', 'sources': ['http://testserver/manytomanysource/1/', 'http://testserver/manytomanysource/3/']}
        ]
        self.assertEqual(serializer.data, expected)


class HyperlinkedForeignKeyTests(TestCase):
    urls = 'rest_framework.tests.test_relations_hyperlink'

    def setUp(self):
        target = ForeignKeyTarget(name='target-1')
        target.save()
        new_target = ForeignKeyTarget(name='target-2')
        new_target.save()
        for idx in range(1, 4):
            source = ForeignKeySource(name='source-%d' % idx, target=target)
            source.save()

    def test_foreign_key_retrieve(self):
        queryset = ForeignKeySource.objects.all()
        serializer = ForeignKeySourceSerializer(queryset, many=True, context={'request': request})
        expected = [
            {'url': 'http://testserver/foreignkeysource/1/', 'name': 'source-1', 'target': 'http://testserver/foreignkeytarget/1/'},
            {'url': 'http://testserver/foreignkeysource/2/', 'name': 'source-2', 'target': 'http://testserver/foreignkeytarget/1/'},
            {'url': 'http://testserver/foreignkeysource/3/', 'name': 'source-3', 'target': 'http://testserver/foreignkeytarget/1/'}
        ]
        self.assertEqual(serializer.data, expected)

    def test_reverse_foreign_key_retrieve(self):
        queryset = ForeignKeyTarget.objects.all()
        serializer = ForeignKeyTargetSerializer(queryset, many=True, context={'request': request})
        expected = [
            {'url': 'http://testserver/foreignkeytarget/1/', 'name': 'target-1', 'sources': ['http://testserver/foreignkeysource/1/', 'http://testserver/foreignkeysource/2/', 'http://testserver/foreignkeysource/3/']},
            {'url': 'http://testserver/foreignkeytarget/2/', 'name': 'target-2', 'sources': []},
        ]
        self.assertEqual(serializer.data, expected)

    def test_foreign_key_update(self):
        data = {'url': 'http://testserver/foreignkeysource/1/', 'name': 'source-1', 'target': 'http://testserver/foreignkeytarget/2/'}
        instance = ForeignKeySource.objects.get(pk=1)
        serializer = ForeignKeySourceSerializer(instance, data=data, context={'request': request})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.data, data)
        serializer.save()

        # Ensure source 1 is updated, and everything else is as expected
        queryset = ForeignKeySource.objects.all()
        serializer = ForeignKeySourceSerializer(queryset, many=True, context={'request': request})
        expected = [
            {'url': 'http://testserver/foreignkeysource/1/', 'name': 'source-1', 'target': 'http://testserver/foreignkeytarget/2/'},
            {'url': 'http://testserver/foreignkeysource/2/', 'name': 'source-2', 'target': 'http://testserver/foreignkeytarget/1/'},
            {'url': 'http://testserver/foreignkeysource/3/', 'name': 'source-3', 'target': 'http://testserver/foreignkeytarget/1/'}
        ]
        self.assertEqual(serializer.data, expected)

    def test_foreign_key_update_incorrect_type(self):
        data = {'url': 'http://testserver/foreignkeysource/1/', 'name': 'source-1', 'target': 2}
        instance = ForeignKeySource.objects.get(pk=1)
        serializer = ForeignKeySourceSerializer(instance, data=data, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {'target': ['Incorrect type.  Expected url string, received int.']})

    def test_reverse_foreign_key_update(self):
        data = {'url': 'http://testserver/foreignkeytarget/2/', 'name': 'target-2', 'sources': ['http://testserver/foreignkeysource/1/', 'http://testserver/foreignkeysource/3/']}
        instance = ForeignKeyTarget.objects.get(pk=2)
        serializer = ForeignKeyTargetSerializer(instance, data=data, context={'request': request})
        self.assertTrue(serializer.is_valid())
        # We shouldn't have saved anything to the db yet since save
        # hasn't been called.
        queryset = ForeignKeyTarget.objects.all()
        new_serializer = ForeignKeyTargetSerializer(queryset, many=True, context={'request': request})
        expected = [
            {'url': 'http://testserver/foreignkeytarget/1/', 'name': 'target-1', 'sources': ['http://testserver/foreignkeysource/1/', 'http://testserver/foreignkeysource/2/', 'http://testserver/foreignkeysource/3/']},
            {'url': 'http://testserver/foreignkeytarget/2/', 'name': 'target-2', 'sources': []},
        ]
        self.assertEqual(new_serializer.data, expected)

        serializer.save()
        self.assertEqual(serializer.data, data)

        # Ensure target 2 is update, and everything else is as expected
        queryset = ForeignKeyTarget.objects.all()
        serializer = ForeignKeyTargetSerializer(queryset, many=True, context={'request': request})
        expected = [
            {'url': 'http://testserver/foreignkeytarget/1/', 'name': 'target-1', 'sources': ['http://testserver/foreignkeysource/2/']},
            {'url': 'http://testserver/foreignkeytarget/2/', 'name': 'target-2', 'sources': ['http://testserver/foreignkeysource/1/', 'http://testserver/foreignkeysource/3/']},
        ]
        self.assertEqual(serializer.data, expected)

    def test_foreign_key_create(self):
        data = {'url': 'http://testserver/foreignkeysource/4/', 'name': 'source-4', 'target': 'http://testserver/foreignkeytarget/2/'}
        serializer = ForeignKeySourceSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, data)
        self.assertEqual(obj.name, 'source-4')

        # Ensure source 1 is updated, and everything else is as expected
        queryset = ForeignKeySource.objects.all()
        serializer = ForeignKeySourceSerializer(queryset, many=True, context={'request': request})
        expected = [
            {'url': 'http://testserver/foreignkeysource/1/', 'name': 'source-1', 'target': 'http://testserver/foreignkeytarget/1/'},
            {'url': 'http://testserver/foreignkeysource/2/', 'name': 'source-2', 'target': 'http://testserver/foreignkeytarget/1/'},
            {'url': 'http://testserver/foreignkeysource/3/', 'name': 'source-3', 'target': 'http://testserver/foreignkeytarget/1/'},
            {'url': 'http://testserver/foreignkeysource/4/', 'name': 'source-4', 'target': 'http://testserver/foreignkeytarget/2/'},
        ]
        self.assertEqual(serializer.data, expected)

    def test_reverse_foreign_key_create(self):
        data = {'url': 'http://testserver/foreignkeytarget/3/', 'name': 'target-3', 'sources': ['http://testserver/foreignkeysource/1/', 'http://testserver/foreignkeysource/3/']}
        serializer = ForeignKeyTargetSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, data)
        self.assertEqual(obj.name, 'target-3')

        # Ensure target 4 is added, and everything else is as expected
        queryset = ForeignKeyTarget.objects.all()
        serializer = ForeignKeyTargetSerializer(queryset, many=True, context={'request': request})
        expected = [
            {'url': 'http://testserver/foreignkeytarget/1/', 'name': 'target-1', 'sources': ['http://testserver/foreignkeysource/2/']},
            {'url': 'http://testserver/foreignkeytarget/2/', 'name': 'target-2', 'sources': []},
            {'url': 'http://testserver/foreignkeytarget/3/', 'name': 'target-3', 'sources': ['http://testserver/foreignkeysource/1/', 'http://testserver/foreignkeysource/3/']},
        ]
        self.assertEqual(serializer.data, expected)

    def test_foreign_key_update_with_invalid_null(self):
        data = {'url': 'http://testserver/foreignkeysource/1/', 'name': 'source-1', 'target': None}
        instance = ForeignKeySource.objects.get(pk=1)
        serializer = ForeignKeySourceSerializer(instance, data=data, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {'target': ['This field is required.']})


class HyperlinkedNullableForeignKeyTests(TestCase):
    urls = 'rest_framework.tests.test_relations_hyperlink'

    def setUp(self):
        target = ForeignKeyTarget(name='target-1')
        target.save()
        for idx in range(1, 4):
            if idx == 3:
                target = None
            source = NullableForeignKeySource(name='source-%d' % idx, target=target)
            source.save()

    def test_foreign_key_retrieve_with_null(self):
        queryset = NullableForeignKeySource.objects.all()
        serializer = NullableForeignKeySourceSerializer(queryset, many=True, context={'request': request})
        expected = [
            {'url': 'http://testserver/nullableforeignkeysource/1/', 'name': 'source-1', 'target': 'http://testserver/foreignkeytarget/1/'},
            {'url': 'http://testserver/nullableforeignkeysource/2/', 'name': 'source-2', 'target': 'http://testserver/foreignkeytarget/1/'},
            {'url': 'http://testserver/nullableforeignkeysource/3/', 'name': 'source-3', 'target': None},
        ]
        self.assertEqual(serializer.data, expected)

    def test_foreign_key_create_with_valid_null(self):
        data = {'url': 'http://testserver/nullableforeignkeysource/4/', 'name': 'source-4', 'target': None}
        serializer = NullableForeignKeySourceSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, data)
        self.assertEqual(obj.name, 'source-4')

        # Ensure source 4 is created, and everything else is as expected
        queryset = NullableForeignKeySource.objects.all()
        serializer = NullableForeignKeySourceSerializer(queryset, many=True, context={'request': request})
        expected = [
            {'url': 'http://testserver/nullableforeignkeysource/1/', 'name': 'source-1', 'target': 'http://testserver/foreignkeytarget/1/'},
            {'url': 'http://testserver/nullableforeignkeysource/2/', 'name': 'source-2', 'target': 'http://testserver/foreignkeytarget/1/'},
            {'url': 'http://testserver/nullableforeignkeysource/3/', 'name': 'source-3', 'target': None},
            {'url': 'http://testserver/nullableforeignkeysource/4/', 'name': 'source-4', 'target': None}
        ]
        self.assertEqual(serializer.data, expected)

    def test_foreign_key_create_with_valid_emptystring(self):
        """
        The emptystring should be interpreted as null in the context
        of relationships.
        """
        data = {'url': 'http://testserver/nullableforeignkeysource/4/', 'name': 'source-4', 'target': ''}
        expected_data = {'url': 'http://testserver/nullableforeignkeysource/4/', 'name': 'source-4', 'target': None}
        serializer = NullableForeignKeySourceSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, expected_data)
        self.assertEqual(obj.name, 'source-4')

        # Ensure source 4 is created, and everything else is as expected
        queryset = NullableForeignKeySource.objects.all()
        serializer = NullableForeignKeySourceSerializer(queryset, many=True, context={'request': request})
        expected = [
            {'url': 'http://testserver/nullableforeignkeysource/1/', 'name': 'source-1', 'target': 'http://testserver/foreignkeytarget/1/'},
            {'url': 'http://testserver/nullableforeignkeysource/2/', 'name': 'source-2', 'target': 'http://testserver/foreignkeytarget/1/'},
            {'url': 'http://testserver/nullableforeignkeysource/3/', 'name': 'source-3', 'target': None},
            {'url': 'http://testserver/nullableforeignkeysource/4/', 'name': 'source-4', 'target': None}
        ]
        self.assertEqual(serializer.data, expected)

    def test_foreign_key_update_with_valid_null(self):
        data = {'url': 'http://testserver/nullableforeignkeysource/1/', 'name': 'source-1', 'target': None}
        instance = NullableForeignKeySource.objects.get(pk=1)
        serializer = NullableForeignKeySourceSerializer(instance, data=data, context={'request': request})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.data, data)
        serializer.save()

        # Ensure source 1 is updated, and everything else is as expected
        queryset = NullableForeignKeySource.objects.all()
        serializer = NullableForeignKeySourceSerializer(queryset, many=True, context={'request': request})
        expected = [
            {'url': 'http://testserver/nullableforeignkeysource/1/', 'name': 'source-1', 'target': None},
            {'url': 'http://testserver/nullableforeignkeysource/2/', 'name': 'source-2', 'target': 'http://testserver/foreignkeytarget/1/'},
            {'url': 'http://testserver/nullableforeignkeysource/3/', 'name': 'source-3', 'target': None},
        ]
        self.assertEqual(serializer.data, expected)

    def test_foreign_key_update_with_valid_emptystring(self):
        """
        The emptystring should be interpreted as null in the context
        of relationships.
        """
        data = {'url': 'http://testserver/nullableforeignkeysource/1/', 'name': 'source-1', 'target': ''}
        expected_data = {'url': 'http://testserver/nullableforeignkeysource/1/', 'name': 'source-1', 'target': None}
        instance = NullableForeignKeySource.objects.get(pk=1)
        serializer = NullableForeignKeySourceSerializer(instance, data=data, context={'request': request})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.data, expected_data)
        serializer.save()

        # Ensure source 1 is updated, and everything else is as expected
        queryset = NullableForeignKeySource.objects.all()
        serializer = NullableForeignKeySourceSerializer(queryset, many=True, context={'request': request})
        expected = [
            {'url': 'http://testserver/nullableforeignkeysource/1/', 'name': 'source-1', 'target': None},
            {'url': 'http://testserver/nullableforeignkeysource/2/', 'name': 'source-2', 'target': 'http://testserver/foreignkeytarget/1/'},
            {'url': 'http://testserver/nullableforeignkeysource/3/', 'name': 'source-3', 'target': None},
        ]
        self.assertEqual(serializer.data, expected)

    # reverse foreign keys MUST be read_only
    # In the general case they do not provide .remove() or .clear()
    # and cannot be arbitrarily set.

    # def test_reverse_foreign_key_update(self):
    #     data = {'id': 1, 'name': 'target-1', 'sources': [1]}
    #     instance = ForeignKeyTarget.objects.get(pk=1)
    #     serializer = ForeignKeyTargetSerializer(instance, data=data)
    #     self.assertTrue(serializer.is_valid())
    #     self.assertEqual(serializer.data, data)
    #     serializer.save()

    #     # Ensure target 1 is updated, and everything else is as expected
    #     queryset = ForeignKeyTarget.objects.all()
    #     serializer = ForeignKeyTargetSerializer(queryset, many=True)
    #     expected = [
    #         {'id': 1, 'name': 'target-1', 'sources': [1]},
    #         {'id': 2, 'name': 'target-2', 'sources': []},
    #     ]
    #     self.assertEqual(serializer.data, expected)


class HyperlinkedNullableOneToOneTests(TestCase):
    urls = 'rest_framework.tests.test_relations_hyperlink'

    def setUp(self):
        target = OneToOneTarget(name='target-1')
        target.save()
        new_target = OneToOneTarget(name='target-2')
        new_target.save()
        source = NullableOneToOneSource(name='source-1', target=target)
        source.save()

    def test_reverse_foreign_key_retrieve_with_null(self):
        queryset = OneToOneTarget.objects.all()
        serializer = NullableOneToOneTargetSerializer(queryset, many=True, context={'request': request})
        expected = [
            {'url': 'http://testserver/onetoonetarget/1/', 'name': 'target-1', 'nullable_source': 'http://testserver/nullableonetoonesource/1/'},
            {'url': 'http://testserver/onetoonetarget/2/', 'name': 'target-2', 'nullable_source': None},
        ]
        self.assertEqual(serializer.data, expected)


# Regression tests for #694 (`source` attribute on related fields)

class HyperlinkedRelatedFieldSourceTests(TestCase):
    urls = 'rest_framework.tests.test_relations_hyperlink'

    def test_related_manager_source(self):
        """
        Relational fields should be able to use manager-returning methods as their source.
        """
        BlogPost.objects.create(title='blah')
        field = serializers.HyperlinkedRelatedField(
            many=True,
            source='get_blogposts_manager',
            view_name='dummy-url',
        )
        field.context = {'request': request}

        class ClassWithManagerMethod(object):
            def get_blogposts_manager(self):
                return BlogPost.objects

        obj = ClassWithManagerMethod()
        value = field.field_to_native(obj, 'field_name')
        self.assertEqual(value, ['http://testserver/dummyurl/1/'])

    def test_related_queryset_source(self):
        """
        Relational fields should be able to use queryset-returning methods as their source.
        """
        BlogPost.objects.create(title='blah')
        field = serializers.HyperlinkedRelatedField(
            many=True,
            source='get_blogposts_queryset',
            view_name='dummy-url',
        )
        field.context = {'request': request}

        class ClassWithQuerysetMethod(object):
            def get_blogposts_queryset(self):
                return BlogPost.objects.all()

        obj = ClassWithQuerysetMethod()
        value = field.field_to_native(obj, 'field_name')
        self.assertEqual(value, ['http://testserver/dummyurl/1/'])

    def test_dotted_source(self):
        """
        Source argument should support dotted.source notation.
        """
        BlogPost.objects.create(title='blah')
        field = serializers.HyperlinkedRelatedField(
            many=True,
            source='a.b.c',
            view_name='dummy-url',
        )
        field.context = {'request': request}

        class ClassWithQuerysetMethod(object):
            a = {
                'b': {
                    'c': BlogPost.objects.all()
                }
            }

        obj = ClassWithQuerysetMethod()
        value = field.field_to_native(obj, 'field_name')
        self.assertEqual(value, ['http://testserver/dummyurl/1/'])

########NEW FILE########
__FILENAME__ = test_relations_nested
from __future__ import unicode_literals
from django.db import models
from django.test import TestCase
from rest_framework import serializers

from .models import OneToOneTarget


class OneToOneSource(models.Model):
    name = models.CharField(max_length=100)
    target = models.OneToOneField(OneToOneTarget, related_name='source',
                                  null=True, blank=True)


class OneToManyTarget(models.Model):
    name = models.CharField(max_length=100)


class OneToManySource(models.Model):
    name = models.CharField(max_length=100)
    target = models.ForeignKey(OneToManyTarget, related_name='sources')


class ReverseNestedOneToOneTests(TestCase):
    def setUp(self):
        class OneToOneSourceSerializer(serializers.ModelSerializer):
            class Meta:
                model = OneToOneSource
                fields = ('id', 'name')

        class OneToOneTargetSerializer(serializers.ModelSerializer):
            source = OneToOneSourceSerializer()

            class Meta:
                model = OneToOneTarget
                fields = ('id', 'name', 'source')

        self.Serializer = OneToOneTargetSerializer

        for idx in range(1, 4):
            target = OneToOneTarget(name='target-%d' % idx)
            target.save()
            source = OneToOneSource(name='source-%d' % idx, target=target)
            source.save()

    def test_one_to_one_retrieve(self):
        queryset = OneToOneTarget.objects.all()
        serializer = self.Serializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'target-1', 'source': {'id': 1, 'name': 'source-1'}},
            {'id': 2, 'name': 'target-2', 'source': {'id': 2, 'name': 'source-2'}},
            {'id': 3, 'name': 'target-3', 'source': {'id': 3, 'name': 'source-3'}}
        ]
        self.assertEqual(serializer.data, expected)

    def test_one_to_one_create(self):
        data = {'id': 4, 'name': 'target-4', 'source': {'id': 4, 'name': 'source-4'}}
        serializer = self.Serializer(data=data)
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, data)
        self.assertEqual(obj.name, 'target-4')

        # Ensure (target 4, target_source 4, source 4) are added, and
        # everything else is as expected.
        queryset = OneToOneTarget.objects.all()
        serializer = self.Serializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'target-1', 'source': {'id': 1, 'name': 'source-1'}},
            {'id': 2, 'name': 'target-2', 'source': {'id': 2, 'name': 'source-2'}},
            {'id': 3, 'name': 'target-3', 'source': {'id': 3, 'name': 'source-3'}},
            {'id': 4, 'name': 'target-4', 'source': {'id': 4, 'name': 'source-4'}}
        ]
        self.assertEqual(serializer.data, expected)

    def test_one_to_one_create_with_invalid_data(self):
        data = {'id': 4, 'name': 'target-4', 'source': {'id': 4}}
        serializer = self.Serializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {'source': [{'name': ['This field is required.']}]})

    def test_one_to_one_update(self):
        data = {'id': 3, 'name': 'target-3-updated', 'source': {'id': 3, 'name': 'source-3-updated'}}
        instance = OneToOneTarget.objects.get(pk=3)
        serializer = self.Serializer(instance, data=data)
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, data)
        self.assertEqual(obj.name, 'target-3-updated')

        # Ensure (target 3, target_source 3, source 3) are updated,
        # and everything else is as expected.
        queryset = OneToOneTarget.objects.all()
        serializer = self.Serializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'target-1', 'source': {'id': 1, 'name': 'source-1'}},
            {'id': 2, 'name': 'target-2', 'source': {'id': 2, 'name': 'source-2'}},
            {'id': 3, 'name': 'target-3-updated', 'source': {'id': 3, 'name': 'source-3-updated'}}
        ]
        self.assertEqual(serializer.data, expected)


class ForwardNestedOneToOneTests(TestCase):
    def setUp(self):
        class OneToOneTargetSerializer(serializers.ModelSerializer):
            class Meta:
                model = OneToOneTarget
                fields = ('id', 'name')

        class OneToOneSourceSerializer(serializers.ModelSerializer):
            target = OneToOneTargetSerializer()

            class Meta:
                model = OneToOneSource
                fields = ('id', 'name', 'target')

        self.Serializer = OneToOneSourceSerializer

        for idx in range(1, 4):
            target = OneToOneTarget(name='target-%d' % idx)
            target.save()
            source = OneToOneSource(name='source-%d' % idx, target=target)
            source.save()

    def test_one_to_one_retrieve(self):
        queryset = OneToOneSource.objects.all()
        serializer = self.Serializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'source-1', 'target': {'id': 1, 'name': 'target-1'}},
            {'id': 2, 'name': 'source-2', 'target': {'id': 2, 'name': 'target-2'}},
            {'id': 3, 'name': 'source-3', 'target': {'id': 3, 'name': 'target-3'}}
        ]
        self.assertEqual(serializer.data, expected)

    def test_one_to_one_create(self):
        data = {'id': 4, 'name': 'source-4', 'target': {'id': 4, 'name': 'target-4'}}
        serializer = self.Serializer(data=data)
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, data)
        self.assertEqual(obj.name, 'source-4')

        # Ensure (target 4, target_source 4, source 4) are added, and
        # everything else is as expected.
        queryset = OneToOneSource.objects.all()
        serializer = self.Serializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'source-1', 'target': {'id': 1, 'name': 'target-1'}},
            {'id': 2, 'name': 'source-2', 'target': {'id': 2, 'name': 'target-2'}},
            {'id': 3, 'name': 'source-3', 'target': {'id': 3, 'name': 'target-3'}},
            {'id': 4, 'name': 'source-4', 'target': {'id': 4, 'name': 'target-4'}}
        ]
        self.assertEqual(serializer.data, expected)

    def test_one_to_one_create_with_invalid_data(self):
        data = {'id': 4, 'name': 'source-4', 'target': {'id': 4}}
        serializer = self.Serializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {'target': [{'name': ['This field is required.']}]})

    def test_one_to_one_update(self):
        data = {'id': 3, 'name': 'source-3-updated', 'target': {'id': 3, 'name': 'target-3-updated'}}
        instance = OneToOneSource.objects.get(pk=3)
        serializer = self.Serializer(instance, data=data)
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, data)
        self.assertEqual(obj.name, 'source-3-updated')

        # Ensure (target 3, target_source 3, source 3) are updated,
        # and everything else is as expected.
        queryset = OneToOneSource.objects.all()
        serializer = self.Serializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'source-1', 'target': {'id': 1, 'name': 'target-1'}},
            {'id': 2, 'name': 'source-2', 'target': {'id': 2, 'name': 'target-2'}},
            {'id': 3, 'name': 'source-3-updated', 'target': {'id': 3, 'name': 'target-3-updated'}}
        ]
        self.assertEqual(serializer.data, expected)

    def test_one_to_one_update_to_null(self):
        data = {'id': 3, 'name': 'source-3-updated', 'target': None}
        instance = OneToOneSource.objects.get(pk=3)
        serializer = self.Serializer(instance, data=data)
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()

        self.assertEqual(serializer.data, data)
        self.assertEqual(obj.name, 'source-3-updated')
        self.assertEqual(obj.target, None)

        queryset = OneToOneSource.objects.all()
        serializer = self.Serializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'source-1', 'target': {'id': 1, 'name': 'target-1'}},
            {'id': 2, 'name': 'source-2', 'target': {'id': 2, 'name': 'target-2'}},
            {'id': 3, 'name': 'source-3-updated', 'target': None}
        ]
        self.assertEqual(serializer.data, expected)

    # TODO: Nullable 1-1 tests
    # def test_one_to_one_delete(self):
    #     data = {'id': 3, 'name': 'target-3', 'target_source': None}
    #     instance = OneToOneTarget.objects.get(pk=3)
    #     serializer = self.Serializer(instance, data=data)
    #     self.assertTrue(serializer.is_valid())
    #     serializer.save()

    #     # Ensure (target_source 3, source 3) are deleted,
    #     # and everything else is as expected.
    #     queryset = OneToOneTarget.objects.all()
    #     serializer = self.Serializer(queryset)
    #     expected = [
    #         {'id': 1, 'name': 'target-1', 'source': {'id': 1, 'name': 'source-1'}},
    #         {'id': 2, 'name': 'target-2', 'source': {'id': 2, 'name': 'source-2'}},
    #         {'id': 3, 'name': 'target-3', 'source': None}
    #     ]
    #     self.assertEqual(serializer.data, expected)


class ReverseNestedOneToManyTests(TestCase):
    def setUp(self):
        class OneToManySourceSerializer(serializers.ModelSerializer):
            class Meta:
                model = OneToManySource
                fields = ('id', 'name')

        class OneToManyTargetSerializer(serializers.ModelSerializer):
            sources = OneToManySourceSerializer(many=True, allow_add_remove=True)

            class Meta:
                model = OneToManyTarget
                fields = ('id', 'name', 'sources')

        self.Serializer = OneToManyTargetSerializer

        target = OneToManyTarget(name='target-1')
        target.save()
        for idx in range(1, 4):
            source = OneToManySource(name='source-%d' % idx, target=target)
            source.save()

    def test_one_to_many_retrieve(self):
        queryset = OneToManyTarget.objects.all()
        serializer = self.Serializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'target-1', 'sources': [{'id': 1, 'name': 'source-1'},
                                                      {'id': 2, 'name': 'source-2'},
                                                      {'id': 3, 'name': 'source-3'}]},
        ]
        self.assertEqual(serializer.data, expected)

    def test_one_to_many_create(self):
        data = {'id': 1, 'name': 'target-1', 'sources': [{'id': 1, 'name': 'source-1'},
                                                         {'id': 2, 'name': 'source-2'},
                                                         {'id': 3, 'name': 'source-3'},
                                                         {'id': 4, 'name': 'source-4'}]}
        instance = OneToManyTarget.objects.get(pk=1)
        serializer = self.Serializer(instance, data=data)
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, data)
        self.assertEqual(obj.name, 'target-1')

        # Ensure source 4 is added, and everything else is as
        # expected.
        queryset = OneToManyTarget.objects.all()
        serializer = self.Serializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'target-1', 'sources': [{'id': 1, 'name': 'source-1'},
                                                      {'id': 2, 'name': 'source-2'},
                                                      {'id': 3, 'name': 'source-3'},
                                                      {'id': 4, 'name': 'source-4'}]}
        ]
        self.assertEqual(serializer.data, expected)

    def test_one_to_many_create_with_invalid_data(self):
        data = {'id': 1, 'name': 'target-1', 'sources': [{'id': 1, 'name': 'source-1'},
                                                         {'id': 2, 'name': 'source-2'},
                                                         {'id': 3, 'name': 'source-3'},
                                                         {'id': 4}]}
        serializer = self.Serializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {'sources': [{}, {}, {}, {'name': ['This field is required.']}]})

    def test_one_to_many_update(self):
        data = {'id': 1, 'name': 'target-1-updated', 'sources': [{'id': 1, 'name': 'source-1-updated'},
                                                                 {'id': 2, 'name': 'source-2'},
                                                                 {'id': 3, 'name': 'source-3'}]}
        instance = OneToManyTarget.objects.get(pk=1)
        serializer = self.Serializer(instance, data=data)
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, data)
        self.assertEqual(obj.name, 'target-1-updated')

        # Ensure (target 1, source 1) are updated,
        # and everything else is as expected.
        queryset = OneToManyTarget.objects.all()
        serializer = self.Serializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'target-1-updated', 'sources': [{'id': 1, 'name': 'source-1-updated'},
                                                              {'id': 2, 'name': 'source-2'},
                                                              {'id': 3, 'name': 'source-3'}]}

        ]
        self.assertEqual(serializer.data, expected)

    def test_one_to_many_delete(self):
        data = {'id': 1, 'name': 'target-1', 'sources': [{'id': 1, 'name': 'source-1'},
                                                         {'id': 3, 'name': 'source-3'}]}
        instance = OneToManyTarget.objects.get(pk=1)
        serializer = self.Serializer(instance, data=data)
        self.assertTrue(serializer.is_valid())
        serializer.save()

        # Ensure source 2 is deleted, and everything else is as
        # expected.
        queryset = OneToManyTarget.objects.all()
        serializer = self.Serializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'target-1', 'sources': [{'id': 1, 'name': 'source-1'},
                                                      {'id': 3, 'name': 'source-3'}]}

        ]
        self.assertEqual(serializer.data, expected)

########NEW FILE########
__FILENAME__ = test_relations_pk
from __future__ import unicode_literals
from django.db import models
from django.test import TestCase
from rest_framework import serializers
from rest_framework.tests.models import (
    BlogPost, ManyToManyTarget, ManyToManySource, ForeignKeyTarget, ForeignKeySource,
    NullableForeignKeySource, OneToOneTarget, NullableOneToOneSource,
)
from rest_framework.compat import six


# ManyToMany
class ManyToManyTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManyToManyTarget
        fields = ('id', 'name', 'sources')


class ManyToManySourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManyToManySource
        fields = ('id', 'name', 'targets')


# ForeignKey
class ForeignKeyTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ForeignKeyTarget
        fields = ('id', 'name', 'sources')


class ForeignKeySourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ForeignKeySource
        fields = ('id', 'name', 'target')


# Nullable ForeignKey
class NullableForeignKeySourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NullableForeignKeySource
        fields = ('id', 'name', 'target')


# Nullable OneToOne
class NullableOneToOneTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = OneToOneTarget
        fields = ('id', 'name', 'nullable_source')


# TODO: Add test that .data cannot be accessed prior to .is_valid

class PKManyToManyTests(TestCase):
    def setUp(self):
        for idx in range(1, 4):
            target = ManyToManyTarget(name='target-%d' % idx)
            target.save()
            source = ManyToManySource(name='source-%d' % idx)
            source.save()
            for target in ManyToManyTarget.objects.all():
                source.targets.add(target)

    def test_many_to_many_retrieve(self):
        queryset = ManyToManySource.objects.all()
        serializer = ManyToManySourceSerializer(queryset, many=True)
        expected = [
                {'id': 1, 'name': 'source-1', 'targets': [1]},
                {'id': 2, 'name': 'source-2', 'targets': [1, 2]},
                {'id': 3, 'name': 'source-3', 'targets': [1, 2, 3]}
        ]
        self.assertEqual(serializer.data, expected)

    def test_reverse_many_to_many_retrieve(self):
        queryset = ManyToManyTarget.objects.all()
        serializer = ManyToManyTargetSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'target-1', 'sources': [1, 2, 3]},
            {'id': 2, 'name': 'target-2', 'sources': [2, 3]},
            {'id': 3, 'name': 'target-3', 'sources': [3]}
        ]
        self.assertEqual(serializer.data, expected)

    def test_many_to_many_update(self):
        data = {'id': 1, 'name': 'source-1', 'targets': [1, 2, 3]}
        instance = ManyToManySource.objects.get(pk=1)
        serializer = ManyToManySourceSerializer(instance, data=data)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertEqual(serializer.data, data)

        # Ensure source 1 is updated, and everything else is as expected
        queryset = ManyToManySource.objects.all()
        serializer = ManyToManySourceSerializer(queryset, many=True)
        expected = [
                {'id': 1, 'name': 'source-1', 'targets': [1, 2, 3]},
                {'id': 2, 'name': 'source-2', 'targets': [1, 2]},
                {'id': 3, 'name': 'source-3', 'targets': [1, 2, 3]}
        ]
        self.assertEqual(serializer.data, expected)

    def test_reverse_many_to_many_update(self):
        data = {'id': 1, 'name': 'target-1', 'sources': [1]}
        instance = ManyToManyTarget.objects.get(pk=1)
        serializer = ManyToManyTargetSerializer(instance, data=data)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertEqual(serializer.data, data)

        # Ensure target 1 is updated, and everything else is as expected
        queryset = ManyToManyTarget.objects.all()
        serializer = ManyToManyTargetSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'target-1', 'sources': [1]},
            {'id': 2, 'name': 'target-2', 'sources': [2, 3]},
            {'id': 3, 'name': 'target-3', 'sources': [3]}
        ]
        self.assertEqual(serializer.data, expected)

    def test_many_to_many_create(self):
        data = {'id': 4, 'name': 'source-4', 'targets': [1, 3]}
        serializer = ManyToManySourceSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, data)
        self.assertEqual(obj.name, 'source-4')

        # Ensure source 4 is added, and everything else is as expected
        queryset = ManyToManySource.objects.all()
        serializer = ManyToManySourceSerializer(queryset, many=True)
        self.assertFalse(serializer.fields['targets'].read_only)
        expected = [
            {'id': 1, 'name': 'source-1', 'targets': [1]},
            {'id': 2, 'name': 'source-2', 'targets': [1, 2]},
            {'id': 3, 'name': 'source-3', 'targets': [1, 2, 3]},
            {'id': 4, 'name': 'source-4', 'targets': [1, 3]},
        ]
        self.assertEqual(serializer.data, expected)

    def test_reverse_many_to_many_create(self):
        data = {'id': 4, 'name': 'target-4', 'sources': [1, 3]}
        serializer = ManyToManyTargetSerializer(data=data)
        self.assertFalse(serializer.fields['sources'].read_only)
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, data)
        self.assertEqual(obj.name, 'target-4')

        # Ensure target 4 is added, and everything else is as expected
        queryset = ManyToManyTarget.objects.all()
        serializer = ManyToManyTargetSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'target-1', 'sources': [1, 2, 3]},
            {'id': 2, 'name': 'target-2', 'sources': [2, 3]},
            {'id': 3, 'name': 'target-3', 'sources': [3]},
            {'id': 4, 'name': 'target-4', 'sources': [1, 3]}
        ]
        self.assertEqual(serializer.data, expected)


class PKForeignKeyTests(TestCase):
    def setUp(self):
        target = ForeignKeyTarget(name='target-1')
        target.save()
        new_target = ForeignKeyTarget(name='target-2')
        new_target.save()
        for idx in range(1, 4):
            source = ForeignKeySource(name='source-%d' % idx, target=target)
            source.save()

    def test_foreign_key_retrieve(self):
        queryset = ForeignKeySource.objects.all()
        serializer = ForeignKeySourceSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'source-1', 'target': 1},
            {'id': 2, 'name': 'source-2', 'target': 1},
            {'id': 3, 'name': 'source-3', 'target': 1}
        ]
        self.assertEqual(serializer.data, expected)

    def test_reverse_foreign_key_retrieve(self):
        queryset = ForeignKeyTarget.objects.all()
        serializer = ForeignKeyTargetSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'target-1', 'sources': [1, 2, 3]},
            {'id': 2, 'name': 'target-2', 'sources': []},
        ]
        self.assertEqual(serializer.data, expected)

    def test_foreign_key_update(self):
        data = {'id': 1, 'name': 'source-1', 'target': 2}
        instance = ForeignKeySource.objects.get(pk=1)
        serializer = ForeignKeySourceSerializer(instance, data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.data, data)
        serializer.save()

        # Ensure source 1 is updated, and everything else is as expected
        queryset = ForeignKeySource.objects.all()
        serializer = ForeignKeySourceSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'source-1', 'target': 2},
            {'id': 2, 'name': 'source-2', 'target': 1},
            {'id': 3, 'name': 'source-3', 'target': 1}
        ]
        self.assertEqual(serializer.data, expected)

    def test_foreign_key_update_incorrect_type(self):
        data = {'id': 1, 'name': 'source-1', 'target': 'foo'}
        instance = ForeignKeySource.objects.get(pk=1)
        serializer = ForeignKeySourceSerializer(instance, data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {'target': ['Incorrect type.  Expected pk value, received %s.' % six.text_type.__name__]})

    def test_reverse_foreign_key_update(self):
        data = {'id': 2, 'name': 'target-2', 'sources': [1, 3]}
        instance = ForeignKeyTarget.objects.get(pk=2)
        serializer = ForeignKeyTargetSerializer(instance, data=data)
        self.assertTrue(serializer.is_valid())
        # We shouldn't have saved anything to the db yet since save
        # hasn't been called.
        queryset = ForeignKeyTarget.objects.all()
        new_serializer = ForeignKeyTargetSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'target-1', 'sources': [1, 2, 3]},
            {'id': 2, 'name': 'target-2', 'sources': []},
        ]
        self.assertEqual(new_serializer.data, expected)

        serializer.save()
        self.assertEqual(serializer.data, data)

        # Ensure target 2 is update, and everything else is as expected
        queryset = ForeignKeyTarget.objects.all()
        serializer = ForeignKeyTargetSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'target-1', 'sources': [2]},
            {'id': 2, 'name': 'target-2', 'sources': [1, 3]},
        ]
        self.assertEqual(serializer.data, expected)

    def test_foreign_key_create(self):
        data = {'id': 4, 'name': 'source-4', 'target': 2}
        serializer = ForeignKeySourceSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, data)
        self.assertEqual(obj.name, 'source-4')

        # Ensure source 4 is added, and everything else is as expected
        queryset = ForeignKeySource.objects.all()
        serializer = ForeignKeySourceSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'source-1', 'target': 1},
            {'id': 2, 'name': 'source-2', 'target': 1},
            {'id': 3, 'name': 'source-3', 'target': 1},
            {'id': 4, 'name': 'source-4', 'target': 2},
        ]
        self.assertEqual(serializer.data, expected)

    def test_reverse_foreign_key_create(self):
        data = {'id': 3, 'name': 'target-3', 'sources': [1, 3]}
        serializer = ForeignKeyTargetSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, data)
        self.assertEqual(obj.name, 'target-3')

        # Ensure target 3 is added, and everything else is as expected
        queryset = ForeignKeyTarget.objects.all()
        serializer = ForeignKeyTargetSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'target-1', 'sources': [2]},
            {'id': 2, 'name': 'target-2', 'sources': []},
            {'id': 3, 'name': 'target-3', 'sources': [1, 3]},
        ]
        self.assertEqual(serializer.data, expected)

    def test_foreign_key_update_with_invalid_null(self):
        data = {'id': 1, 'name': 'source-1', 'target': None}
        instance = ForeignKeySource.objects.get(pk=1)
        serializer = ForeignKeySourceSerializer(instance, data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {'target': ['This field is required.']})

    def test_foreign_key_with_empty(self):
        """
        Regression test for #1072

        https://github.com/tomchristie/django-rest-framework/issues/1072
        """
        serializer = NullableForeignKeySourceSerializer()
        self.assertEqual(serializer.data['target'], None)


class PKNullableForeignKeyTests(TestCase):
    def setUp(self):
        target = ForeignKeyTarget(name='target-1')
        target.save()
        for idx in range(1, 4):
            if idx == 3:
                target = None
            source = NullableForeignKeySource(name='source-%d' % idx, target=target)
            source.save()

    def test_foreign_key_retrieve_with_null(self):
        queryset = NullableForeignKeySource.objects.all()
        serializer = NullableForeignKeySourceSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'source-1', 'target': 1},
            {'id': 2, 'name': 'source-2', 'target': 1},
            {'id': 3, 'name': 'source-3', 'target': None},
        ]
        self.assertEqual(serializer.data, expected)

    def test_foreign_key_create_with_valid_null(self):
        data = {'id': 4, 'name': 'source-4', 'target': None}
        serializer = NullableForeignKeySourceSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, data)
        self.assertEqual(obj.name, 'source-4')

        # Ensure source 4 is created, and everything else is as expected
        queryset = NullableForeignKeySource.objects.all()
        serializer = NullableForeignKeySourceSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'source-1', 'target': 1},
            {'id': 2, 'name': 'source-2', 'target': 1},
            {'id': 3, 'name': 'source-3', 'target': None},
            {'id': 4, 'name': 'source-4', 'target': None}
        ]
        self.assertEqual(serializer.data, expected)

    def test_foreign_key_create_with_valid_emptystring(self):
        """
        The emptystring should be interpreted as null in the context
        of relationships.
        """
        data = {'id': 4, 'name': 'source-4', 'target': ''}
        expected_data = {'id': 4, 'name': 'source-4', 'target': None}
        serializer = NullableForeignKeySourceSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, expected_data)
        self.assertEqual(obj.name, 'source-4')

        # Ensure source 4 is created, and everything else is as expected
        queryset = NullableForeignKeySource.objects.all()
        serializer = NullableForeignKeySourceSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'source-1', 'target': 1},
            {'id': 2, 'name': 'source-2', 'target': 1},
            {'id': 3, 'name': 'source-3', 'target': None},
            {'id': 4, 'name': 'source-4', 'target': None}
        ]
        self.assertEqual(serializer.data, expected)

    def test_foreign_key_update_with_valid_null(self):
        data = {'id': 1, 'name': 'source-1', 'target': None}
        instance = NullableForeignKeySource.objects.get(pk=1)
        serializer = NullableForeignKeySourceSerializer(instance, data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.data, data)
        serializer.save()

        # Ensure source 1 is updated, and everything else is as expected
        queryset = NullableForeignKeySource.objects.all()
        serializer = NullableForeignKeySourceSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'source-1', 'target': None},
            {'id': 2, 'name': 'source-2', 'target': 1},
            {'id': 3, 'name': 'source-3', 'target': None}
        ]
        self.assertEqual(serializer.data, expected)

    def test_foreign_key_update_with_valid_emptystring(self):
        """
        The emptystring should be interpreted as null in the context
        of relationships.
        """
        data = {'id': 1, 'name': 'source-1', 'target': ''}
        expected_data = {'id': 1, 'name': 'source-1', 'target': None}
        instance = NullableForeignKeySource.objects.get(pk=1)
        serializer = NullableForeignKeySourceSerializer(instance, data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.data, expected_data)
        serializer.save()

        # Ensure source 1 is updated, and everything else is as expected
        queryset = NullableForeignKeySource.objects.all()
        serializer = NullableForeignKeySourceSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'source-1', 'target': None},
            {'id': 2, 'name': 'source-2', 'target': 1},
            {'id': 3, 'name': 'source-3', 'target': None}
        ]
        self.assertEqual(serializer.data, expected)

    # reverse foreign keys MUST be read_only
    # In the general case they do not provide .remove() or .clear()
    # and cannot be arbitrarily set.

    # def test_reverse_foreign_key_update(self):
    #     data = {'id': 1, 'name': 'target-1', 'sources': [1]}
    #     instance = ForeignKeyTarget.objects.get(pk=1)
    #     serializer = ForeignKeyTargetSerializer(instance, data=data)
    #     self.assertTrue(serializer.is_valid())
    #     self.assertEqual(serializer.data, data)
    #     serializer.save()

    #     # Ensure target 1 is updated, and everything else is as expected
    #     queryset = ForeignKeyTarget.objects.all()
    #     serializer = ForeignKeyTargetSerializer(queryset, many=True)
    #     expected = [
    #         {'id': 1, 'name': 'target-1', 'sources': [1]},
    #         {'id': 2, 'name': 'target-2', 'sources': []},
    #     ]
    #     self.assertEqual(serializer.data, expected)


class PKNullableOneToOneTests(TestCase):
    def setUp(self):
        target = OneToOneTarget(name='target-1')
        target.save()
        new_target = OneToOneTarget(name='target-2')
        new_target.save()
        source = NullableOneToOneSource(name='source-1', target=new_target)
        source.save()

    def test_reverse_foreign_key_retrieve_with_null(self):
        queryset = OneToOneTarget.objects.all()
        serializer = NullableOneToOneTargetSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'target-1', 'nullable_source': None},
            {'id': 2, 'name': 'target-2', 'nullable_source': 1},
        ]
        self.assertEqual(serializer.data, expected)


# The below models and tests ensure that serializer fields corresponding
# to a ManyToManyField field with a user-specified ``through`` model are
# set to read only


class ManyToManyThroughTarget(models.Model):
    name = models.CharField(max_length=100)


class ManyToManyThrough(models.Model):
    source = models.ForeignKey('ManyToManyThroughSource')
    target = models.ForeignKey(ManyToManyThroughTarget)


class ManyToManyThroughSource(models.Model):
    name = models.CharField(max_length=100)
    targets = models.ManyToManyField(ManyToManyThroughTarget,
                                     related_name='sources',
                                     through='ManyToManyThrough')


class ManyToManyThroughTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManyToManyThroughTarget
        fields = ('id', 'name', 'sources')


class ManyToManyThroughSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManyToManyThroughSource
        fields = ('id', 'name', 'targets')


class PKManyToManyThroughTests(TestCase):
    def setUp(self):
        self.source = ManyToManyThroughSource.objects.create(
            name='through-source-1')
        self.target = ManyToManyThroughTarget.objects.create(
            name='through-target-1')

    def test_many_to_many_create(self):
        data = {'id': 2, 'name': 'source-2', 'targets': [self.target.pk]}
        serializer = ManyToManyThroughSourceSerializer(data=data)
        self.assertTrue(serializer.fields['targets'].read_only)
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(obj.name, 'source-2')
        self.assertEqual(obj.targets.count(), 0)

    def test_many_to_many_reverse_create(self):
        data = {'id': 2, 'name': 'target-2', 'sources': [self.source.pk]}
        serializer = ManyToManyThroughTargetSerializer(data=data)
        self.assertTrue(serializer.fields['sources'].read_only)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        obj = serializer.save()
        self.assertEqual(obj.name, 'target-2')
        self.assertEqual(obj.sources.count(), 0)


# Regression tests for #694 (`source` attribute on related fields)


class PrimaryKeyRelatedFieldSourceTests(TestCase):
    def test_related_manager_source(self):
        """
        Relational fields should be able to use manager-returning methods as their source.
        """
        BlogPost.objects.create(title='blah')
        field = serializers.PrimaryKeyRelatedField(many=True, source='get_blogposts_manager')

        class ClassWithManagerMethod(object):
            def get_blogposts_manager(self):
                return BlogPost.objects

        obj = ClassWithManagerMethod()
        value = field.field_to_native(obj, 'field_name')
        self.assertEqual(value, [1])

    def test_related_queryset_source(self):
        """
        Relational fields should be able to use queryset-returning methods as their source.
        """
        BlogPost.objects.create(title='blah')
        field = serializers.PrimaryKeyRelatedField(many=True, source='get_blogposts_queryset')

        class ClassWithQuerysetMethod(object):
            def get_blogposts_queryset(self):
                return BlogPost.objects.all()

        obj = ClassWithQuerysetMethod()
        value = field.field_to_native(obj, 'field_name')
        self.assertEqual(value, [1])

    def test_dotted_source(self):
        """
        Source argument should support dotted.source notation.
        """
        BlogPost.objects.create(title='blah')
        field = serializers.PrimaryKeyRelatedField(many=True, source='a.b.c')

        class ClassWithQuerysetMethod(object):
            a = {
                'b': {
                    'c': BlogPost.objects.all()
                }
            }

        obj = ClassWithQuerysetMethod()
        value = field.field_to_native(obj, 'field_name')
        self.assertEqual(value, [1])

########NEW FILE########
__FILENAME__ = test_relations_slug
from django.test import TestCase
from rest_framework import serializers
from rest_framework.tests.models import NullableForeignKeySource, ForeignKeySource, ForeignKeyTarget


class ForeignKeyTargetSerializer(serializers.ModelSerializer):
    sources = serializers.SlugRelatedField(many=True, slug_field='name')

    class Meta:
        model = ForeignKeyTarget


class ForeignKeySourceSerializer(serializers.ModelSerializer):
    target = serializers.SlugRelatedField(slug_field='name')

    class Meta:
        model = ForeignKeySource


class NullableForeignKeySourceSerializer(serializers.ModelSerializer):
    target = serializers.SlugRelatedField(slug_field='name', required=False)

    class Meta:
        model = NullableForeignKeySource


# TODO: M2M Tests, FKTests (Non-nullable), One2One
class SlugForeignKeyTests(TestCase):
    def setUp(self):
        target = ForeignKeyTarget(name='target-1')
        target.save()
        new_target = ForeignKeyTarget(name='target-2')
        new_target.save()
        for idx in range(1, 4):
            source = ForeignKeySource(name='source-%d' % idx, target=target)
            source.save()

    def test_foreign_key_retrieve(self):
        queryset = ForeignKeySource.objects.all()
        serializer = ForeignKeySourceSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'source-1', 'target': 'target-1'},
            {'id': 2, 'name': 'source-2', 'target': 'target-1'},
            {'id': 3, 'name': 'source-3', 'target': 'target-1'}
        ]
        self.assertEqual(serializer.data, expected)

    def test_reverse_foreign_key_retrieve(self):
        queryset = ForeignKeyTarget.objects.all()
        serializer = ForeignKeyTargetSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'target-1', 'sources': ['source-1', 'source-2', 'source-3']},
            {'id': 2, 'name': 'target-2', 'sources': []},
        ]
        self.assertEqual(serializer.data, expected)

    def test_foreign_key_update(self):
        data = {'id': 1, 'name': 'source-1', 'target': 'target-2'}
        instance = ForeignKeySource.objects.get(pk=1)
        serializer = ForeignKeySourceSerializer(instance, data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.data, data)
        serializer.save()

        # Ensure source 1 is updated, and everything else is as expected
        queryset = ForeignKeySource.objects.all()
        serializer = ForeignKeySourceSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'source-1', 'target': 'target-2'},
            {'id': 2, 'name': 'source-2', 'target': 'target-1'},
            {'id': 3, 'name': 'source-3', 'target': 'target-1'}
        ]
        self.assertEqual(serializer.data, expected)

    def test_foreign_key_update_incorrect_type(self):
        data = {'id': 1, 'name': 'source-1', 'target': 123}
        instance = ForeignKeySource.objects.get(pk=1)
        serializer = ForeignKeySourceSerializer(instance, data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {'target': ['Object with name=123 does not exist.']})

    def test_reverse_foreign_key_update(self):
        data = {'id': 2, 'name': 'target-2', 'sources': ['source-1', 'source-3']}
        instance = ForeignKeyTarget.objects.get(pk=2)
        serializer = ForeignKeyTargetSerializer(instance, data=data)
        self.assertTrue(serializer.is_valid())
        # We shouldn't have saved anything to the db yet since save
        # hasn't been called.
        queryset = ForeignKeyTarget.objects.all()
        new_serializer = ForeignKeyTargetSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'target-1', 'sources': ['source-1', 'source-2', 'source-3']},
            {'id': 2, 'name': 'target-2', 'sources': []},
        ]
        self.assertEqual(new_serializer.data, expected)

        serializer.save()
        self.assertEqual(serializer.data, data)

        # Ensure target 2 is update, and everything else is as expected
        queryset = ForeignKeyTarget.objects.all()
        serializer = ForeignKeyTargetSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'target-1', 'sources': ['source-2']},
            {'id': 2, 'name': 'target-2', 'sources': ['source-1', 'source-3']},
        ]
        self.assertEqual(serializer.data, expected)

    def test_foreign_key_create(self):
        data = {'id': 4, 'name': 'source-4', 'target': 'target-2'}
        serializer = ForeignKeySourceSerializer(data=data)
        serializer.is_valid()
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, data)
        self.assertEqual(obj.name, 'source-4')

        # Ensure source 4 is added, and everything else is as expected
        queryset = ForeignKeySource.objects.all()
        serializer = ForeignKeySourceSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'source-1', 'target': 'target-1'},
            {'id': 2, 'name': 'source-2', 'target': 'target-1'},
            {'id': 3, 'name': 'source-3', 'target': 'target-1'},
            {'id': 4, 'name': 'source-4', 'target': 'target-2'},
        ]
        self.assertEqual(serializer.data, expected)

    def test_reverse_foreign_key_create(self):
        data = {'id': 3, 'name': 'target-3', 'sources': ['source-1', 'source-3']}
        serializer = ForeignKeyTargetSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, data)
        self.assertEqual(obj.name, 'target-3')

        # Ensure target 3 is added, and everything else is as expected
        queryset = ForeignKeyTarget.objects.all()
        serializer = ForeignKeyTargetSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'target-1', 'sources': ['source-2']},
            {'id': 2, 'name': 'target-2', 'sources': []},
            {'id': 3, 'name': 'target-3', 'sources': ['source-1', 'source-3']},
        ]
        self.assertEqual(serializer.data, expected)

    def test_foreign_key_update_with_invalid_null(self):
        data = {'id': 1, 'name': 'source-1', 'target': None}
        instance = ForeignKeySource.objects.get(pk=1)
        serializer = ForeignKeySourceSerializer(instance, data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {'target': ['This field is required.']})


class SlugNullableForeignKeyTests(TestCase):
    def setUp(self):
        target = ForeignKeyTarget(name='target-1')
        target.save()
        for idx in range(1, 4):
            if idx == 3:
                target = None
            source = NullableForeignKeySource(name='source-%d' % idx, target=target)
            source.save()

    def test_foreign_key_retrieve_with_null(self):
        queryset = NullableForeignKeySource.objects.all()
        serializer = NullableForeignKeySourceSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'source-1', 'target': 'target-1'},
            {'id': 2, 'name': 'source-2', 'target': 'target-1'},
            {'id': 3, 'name': 'source-3', 'target': None},
        ]
        self.assertEqual(serializer.data, expected)

    def test_foreign_key_create_with_valid_null(self):
        data = {'id': 4, 'name': 'source-4', 'target': None}
        serializer = NullableForeignKeySourceSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, data)
        self.assertEqual(obj.name, 'source-4')

        # Ensure source 4 is created, and everything else is as expected
        queryset = NullableForeignKeySource.objects.all()
        serializer = NullableForeignKeySourceSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'source-1', 'target': 'target-1'},
            {'id': 2, 'name': 'source-2', 'target': 'target-1'},
            {'id': 3, 'name': 'source-3', 'target': None},
            {'id': 4, 'name': 'source-4', 'target': None}
        ]
        self.assertEqual(serializer.data, expected)

    def test_foreign_key_create_with_valid_emptystring(self):
        """
        The emptystring should be interpreted as null in the context
        of relationships.
        """
        data = {'id': 4, 'name': 'source-4', 'target': ''}
        expected_data = {'id': 4, 'name': 'source-4', 'target': None}
        serializer = NullableForeignKeySourceSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, expected_data)
        self.assertEqual(obj.name, 'source-4')

        # Ensure source 4 is created, and everything else is as expected
        queryset = NullableForeignKeySource.objects.all()
        serializer = NullableForeignKeySourceSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'source-1', 'target': 'target-1'},
            {'id': 2, 'name': 'source-2', 'target': 'target-1'},
            {'id': 3, 'name': 'source-3', 'target': None},
            {'id': 4, 'name': 'source-4', 'target': None}
        ]
        self.assertEqual(serializer.data, expected)

    def test_foreign_key_update_with_valid_null(self):
        data = {'id': 1, 'name': 'source-1', 'target': None}
        instance = NullableForeignKeySource.objects.get(pk=1)
        serializer = NullableForeignKeySourceSerializer(instance, data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.data, data)
        serializer.save()

        # Ensure source 1 is updated, and everything else is as expected
        queryset = NullableForeignKeySource.objects.all()
        serializer = NullableForeignKeySourceSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'source-1', 'target': None},
            {'id': 2, 'name': 'source-2', 'target': 'target-1'},
            {'id': 3, 'name': 'source-3', 'target': None}
        ]
        self.assertEqual(serializer.data, expected)

    def test_foreign_key_update_with_valid_emptystring(self):
        """
        The emptystring should be interpreted as null in the context
        of relationships.
        """
        data = {'id': 1, 'name': 'source-1', 'target': ''}
        expected_data = {'id': 1, 'name': 'source-1', 'target': None}
        instance = NullableForeignKeySource.objects.get(pk=1)
        serializer = NullableForeignKeySourceSerializer(instance, data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.data, expected_data)
        serializer.save()

        # Ensure source 1 is updated, and everything else is as expected
        queryset = NullableForeignKeySource.objects.all()
        serializer = NullableForeignKeySourceSerializer(queryset, many=True)
        expected = [
            {'id': 1, 'name': 'source-1', 'target': None},
            {'id': 2, 'name': 'source-2', 'target': 'target-1'},
            {'id': 3, 'name': 'source-3', 'target': None}
        ]
        self.assertEqual(serializer.data, expected)

########NEW FILE########
__FILENAME__ = test_renderers
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal
from django.core.cache import cache
from django.db import models
from django.test import TestCase
from django.utils import unittest
from django.utils.translation import ugettext_lazy as _
from rest_framework import status, permissions
from rest_framework.compat import yaml, etree, patterns, url, include, six, StringIO
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.renderers import BaseRenderer, JSONRenderer, YAMLRenderer, \
    XMLRenderer, JSONPRenderer, BrowsableAPIRenderer, UnicodeJSONRenderer, UnicodeYAMLRenderer
from rest_framework.parsers import YAMLParser, XMLParser
from rest_framework.settings import api_settings
from rest_framework.test import APIRequestFactory
from collections import MutableMapping
import datetime
import json
import pickle
import re


DUMMYSTATUS = status.HTTP_200_OK
DUMMYCONTENT = 'dummycontent'

RENDERER_A_SERIALIZER = lambda x: ('Renderer A: %s' % x).encode('ascii')
RENDERER_B_SERIALIZER = lambda x: ('Renderer B: %s' % x).encode('ascii')


expected_results = [
    ((elem for elem in [1, 2, 3]), JSONRenderer, b'[1, 2, 3]')  # Generator
]


class DummyTestModel(models.Model):
    name = models.CharField(max_length=42, default='')


class BasicRendererTests(TestCase):
    def test_expected_results(self):
        for value, renderer_cls, expected in expected_results:
            output = renderer_cls().render(value)
            self.assertEqual(output, expected)


class RendererA(BaseRenderer):
    media_type = 'mock/renderera'
    format = "formata"

    def render(self, data, media_type=None, renderer_context=None):
        return RENDERER_A_SERIALIZER(data)


class RendererB(BaseRenderer):
    media_type = 'mock/rendererb'
    format = "formatb"

    def render(self, data, media_type=None, renderer_context=None):
        return RENDERER_B_SERIALIZER(data)


class MockView(APIView):
    renderer_classes = (RendererA, RendererB)

    def get(self, request, **kwargs):
        response = Response(DUMMYCONTENT, status=DUMMYSTATUS)
        return response


class MockGETView(APIView):
    def get(self, request, **kwargs):
        return Response({'foo': ['bar', 'baz']})



class MockPOSTView(APIView):
    def post(self, request, **kwargs):
        return Response({'foo': request.DATA})


class EmptyGETView(APIView):
    renderer_classes = (JSONRenderer,)

    def get(self, request, **kwargs):
        return Response(status=status.HTTP_204_NO_CONTENT)


class HTMLView(APIView):
    renderer_classes = (BrowsableAPIRenderer, )

    def get(self, request, **kwargs):
        return Response('text')


class HTMLView1(APIView):
    renderer_classes = (BrowsableAPIRenderer, JSONRenderer)

    def get(self, request, **kwargs):
        return Response('text')

urlpatterns = patterns('',
    url(r'^.*\.(?P<format>.+)$', MockView.as_view(renderer_classes=[RendererA, RendererB])),
    url(r'^$', MockView.as_view(renderer_classes=[RendererA, RendererB])),
    url(r'^cache$', MockGETView.as_view()),
    url(r'^jsonp/jsonrenderer$', MockGETView.as_view(renderer_classes=[JSONRenderer, JSONPRenderer])),
    url(r'^jsonp/nojsonrenderer$', MockGETView.as_view(renderer_classes=[JSONPRenderer])),
    url(r'^parseerror$', MockPOSTView.as_view(renderer_classes=[JSONRenderer, BrowsableAPIRenderer])),
    url(r'^html$', HTMLView.as_view()),
    url(r'^html1$', HTMLView1.as_view()),
    url(r'^empty$', EmptyGETView.as_view()),
    url(r'^api', include('rest_framework.urls', namespace='rest_framework'))
)


class POSTDeniedPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.method != 'POST'


class POSTDeniedView(APIView):
    renderer_classes = (BrowsableAPIRenderer,)
    permission_classes = (POSTDeniedPermission,)

    def get(self, request):
        return Response()

    def post(self, request):
        return Response()

    def put(self, request):
        return Response()

    def patch(self, request):
        return Response()


class DocumentingRendererTests(TestCase):
    def test_only_permitted_forms_are_displayed(self):
        view = POSTDeniedView.as_view()
        request = APIRequestFactory().get('/')
        response = view(request).render()
        self.assertNotContains(response, '>POST<')
        self.assertContains(response, '>PUT<')
        self.assertContains(response, '>PATCH<')


class RendererEndToEndTests(TestCase):
    """
    End-to-end testing of renderers using an RendererMixin on a generic view.
    """

    urls = 'rest_framework.tests.test_renderers'

    def test_default_renderer_serializes_content(self):
        """If the Accept header is not set the default renderer should serialize the response."""
        resp = self.client.get('/')
        self.assertEqual(resp['Content-Type'], RendererA.media_type + '; charset=utf-8')
        self.assertEqual(resp.content, RENDERER_A_SERIALIZER(DUMMYCONTENT))
        self.assertEqual(resp.status_code, DUMMYSTATUS)

    def test_head_method_serializes_no_content(self):
        """No response must be included in HEAD requests."""
        resp = self.client.head('/')
        self.assertEqual(resp.status_code, DUMMYSTATUS)
        self.assertEqual(resp['Content-Type'], RendererA.media_type + '; charset=utf-8')
        self.assertEqual(resp.content, six.b(''))

    def test_default_renderer_serializes_content_on_accept_any(self):
        """If the Accept header is set to */* the default renderer should serialize the response."""
        resp = self.client.get('/', HTTP_ACCEPT='*/*')
        self.assertEqual(resp['Content-Type'], RendererA.media_type + '; charset=utf-8')
        self.assertEqual(resp.content, RENDERER_A_SERIALIZER(DUMMYCONTENT))
        self.assertEqual(resp.status_code, DUMMYSTATUS)

    def test_specified_renderer_serializes_content_default_case(self):
        """If the Accept header is set the specified renderer should serialize the response.
        (In this case we check that works for the default renderer)"""
        resp = self.client.get('/', HTTP_ACCEPT=RendererA.media_type)
        self.assertEqual(resp['Content-Type'], RendererA.media_type + '; charset=utf-8')
        self.assertEqual(resp.content, RENDERER_A_SERIALIZER(DUMMYCONTENT))
        self.assertEqual(resp.status_code, DUMMYSTATUS)

    def test_specified_renderer_serializes_content_non_default_case(self):
        """If the Accept header is set the specified renderer should serialize the response.
        (In this case we check that works for a non-default renderer)"""
        resp = self.client.get('/', HTTP_ACCEPT=RendererB.media_type)
        self.assertEqual(resp['Content-Type'], RendererB.media_type + '; charset=utf-8')
        self.assertEqual(resp.content, RENDERER_B_SERIALIZER(DUMMYCONTENT))
        self.assertEqual(resp.status_code, DUMMYSTATUS)

    def test_specified_renderer_serializes_content_on_accept_query(self):
        """The '_accept' query string should behave in the same way as the Accept header."""
        param = '?%s=%s' % (
            api_settings.URL_ACCEPT_OVERRIDE,
            RendererB.media_type
        )
        resp = self.client.get('/' + param)
        self.assertEqual(resp['Content-Type'], RendererB.media_type + '; charset=utf-8')
        self.assertEqual(resp.content, RENDERER_B_SERIALIZER(DUMMYCONTENT))
        self.assertEqual(resp.status_code, DUMMYSTATUS)

    def test_unsatisfiable_accept_header_on_request_returns_406_status(self):
        """If the Accept header is unsatisfiable we should return a 406 Not Acceptable response."""
        resp = self.client.get('/', HTTP_ACCEPT='foo/bar')
        self.assertEqual(resp.status_code, status.HTTP_406_NOT_ACCEPTABLE)

    def test_specified_renderer_serializes_content_on_format_query(self):
        """If a 'format' query is specified, the renderer with the matching
        format attribute should serialize the response."""
        param = '?%s=%s' % (
            api_settings.URL_FORMAT_OVERRIDE,
            RendererB.format
        )
        resp = self.client.get('/' + param)
        self.assertEqual(resp['Content-Type'], RendererB.media_type + '; charset=utf-8')
        self.assertEqual(resp.content, RENDERER_B_SERIALIZER(DUMMYCONTENT))
        self.assertEqual(resp.status_code, DUMMYSTATUS)

    def test_specified_renderer_serializes_content_on_format_kwargs(self):
        """If a 'format' keyword arg is specified, the renderer with the matching
        format attribute should serialize the response."""
        resp = self.client.get('/something.formatb')
        self.assertEqual(resp['Content-Type'], RendererB.media_type + '; charset=utf-8')
        self.assertEqual(resp.content, RENDERER_B_SERIALIZER(DUMMYCONTENT))
        self.assertEqual(resp.status_code, DUMMYSTATUS)

    def test_specified_renderer_is_used_on_format_query_with_matching_accept(self):
        """If both a 'format' query and a matching Accept header specified,
        the renderer with the matching format attribute should serialize the response."""
        param = '?%s=%s' % (
            api_settings.URL_FORMAT_OVERRIDE,
            RendererB.format
        )
        resp = self.client.get('/' + param,
                               HTTP_ACCEPT=RendererB.media_type)
        self.assertEqual(resp['Content-Type'], RendererB.media_type + '; charset=utf-8')
        self.assertEqual(resp.content, RENDERER_B_SERIALIZER(DUMMYCONTENT))
        self.assertEqual(resp.status_code, DUMMYSTATUS)

    def test_parse_error_renderers_browsable_api(self):
        """Invalid data should still render the browsable API correctly."""
        resp = self.client.post('/parseerror', data='foobar', content_type='application/json', HTTP_ACCEPT='text/html')
        self.assertEqual(resp['Content-Type'], 'text/html; charset=utf-8')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_204_no_content_responses_have_no_content_type_set(self):
        """
        Regression test for #1196

        https://github.com/tomchristie/django-rest-framework/issues/1196
        """
        resp = self.client.get('/empty')
        self.assertEqual(resp.get('Content-Type', None), None)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_contains_headers_of_api_response(self):
        """
        Issue #1437

        Test we display the headers of the API response and not those from the
        HTML response
        """
        resp = self.client.get('/html1')
        self.assertContains(resp, '>GET, HEAD, OPTIONS<')
        self.assertContains(resp, '>application/json<')
        self.assertNotContains(resp, '>text/html; charset=utf-8<')


_flat_repr = '{"foo": ["bar", "baz"]}'
_indented_repr = '{\n  "foo": [\n    "bar",\n    "baz"\n  ]\n}'


def strip_trailing_whitespace(content):
    """
    Seems to be some inconsistencies re. trailing whitespace with
    different versions of the json lib.
    """
    return re.sub(' +\n', '\n', content)


class JSONRendererTests(TestCase):
    """
    Tests specific to the JSON Renderer
    """

    def test_render_lazy_strings(self):
        """
        JSONRenderer should deal with lazy translated strings.
        """
        ret = JSONRenderer().render(_('test'))
        self.assertEqual(ret, b'"test"')

    def test_render_queryset_values(self):
        o = DummyTestModel.objects.create(name='dummy')
        qs = DummyTestModel.objects.values('id', 'name')
        ret = JSONRenderer().render(qs)
        data = json.loads(ret.decode('utf-8'))
        self.assertEquals(data, [{'id': o.id, 'name': o.name}])

    def test_render_queryset_values_list(self):
        o = DummyTestModel.objects.create(name='dummy')
        qs = DummyTestModel.objects.values_list('id', 'name')
        ret = JSONRenderer().render(qs)
        data = json.loads(ret.decode('utf-8'))
        self.assertEquals(data, [[o.id, o.name]])

    def test_render_dict_abc_obj(self):
        class Dict(MutableMapping):
            def __init__(self):
                self._dict = dict()
            def __getitem__(self, key):
                return self._dict.__getitem__(key)
            def __setitem__(self, key, value):
                return self._dict.__setitem__(key, value)
            def __delitem__(self, key):
                return self._dict.__delitem__(key)
            def __iter__(self):
                return self._dict.__iter__()
            def __len__(self):
                return self._dict.__len__()
            def keys(self):
                return self._dict.keys()

        x = Dict()
        x['key'] = 'string value'
        x[2] = 3
        ret = JSONRenderer().render(x)
        data = json.loads(ret.decode('utf-8'))
        self.assertEquals(data, {'key': 'string value', '2': 3})    

    def test_render_obj_with_getitem(self):
        class DictLike(object):
            def __init__(self):
                self._dict = {}
            def set(self, value):
                self._dict = dict(value)
            def __getitem__(self, key):
                return self._dict[key]
            
        x = DictLike()
        x.set({'a': 1, 'b': 'string'})
        with self.assertRaises(TypeError):
            JSONRenderer().render(x)
        
    def test_without_content_type_args(self):
        """
        Test basic JSON rendering.
        """
        obj = {'foo': ['bar', 'baz']}
        renderer = JSONRenderer()
        content = renderer.render(obj, 'application/json')
        # Fix failing test case which depends on version of JSON library.
        self.assertEqual(content.decode('utf-8'), _flat_repr)

    def test_with_content_type_args(self):
        """
        Test JSON rendering with additional content type arguments supplied.
        """
        obj = {'foo': ['bar', 'baz']}
        renderer = JSONRenderer()
        content = renderer.render(obj, 'application/json; indent=2')
        self.assertEqual(strip_trailing_whitespace(content.decode('utf-8')), _indented_repr)

    def test_check_ascii(self):
        obj = {'countries': ['United Kingdom', 'France', 'España']}
        renderer = JSONRenderer()
        content = renderer.render(obj, 'application/json')
        self.assertEqual(content, '{"countries": ["United Kingdom", "France", "Espa\\u00f1a"]}'.encode('utf-8'))


class UnicodeJSONRendererTests(TestCase):
    """
    Tests specific for the Unicode JSON Renderer
    """
    def test_proper_encoding(self):
        obj = {'countries': ['United Kingdom', 'France', 'España']}
        renderer = UnicodeJSONRenderer()
        content = renderer.render(obj, 'application/json')
        self.assertEqual(content, '{"countries": ["United Kingdom", "France", "España"]}'.encode('utf-8'))


class JSONPRendererTests(TestCase):
    """
    Tests specific to the JSONP Renderer
    """

    urls = 'rest_framework.tests.test_renderers'

    def test_without_callback_with_json_renderer(self):
        """
        Test JSONP rendering with View JSON Renderer.
        """
        resp = self.client.get('/jsonp/jsonrenderer',
                               HTTP_ACCEPT='application/javascript')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'application/javascript; charset=utf-8')
        self.assertEqual(resp.content,
            ('callback(%s);' % _flat_repr).encode('ascii'))

    def test_without_callback_without_json_renderer(self):
        """
        Test JSONP rendering without View JSON Renderer.
        """
        resp = self.client.get('/jsonp/nojsonrenderer',
                               HTTP_ACCEPT='application/javascript')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'application/javascript; charset=utf-8')
        self.assertEqual(resp.content,
            ('callback(%s);' % _flat_repr).encode('ascii'))

    def test_with_callback(self):
        """
        Test JSONP rendering with callback function name.
        """
        callback_func = 'myjsonpcallback'
        resp = self.client.get('/jsonp/nojsonrenderer?callback=' + callback_func,
                               HTTP_ACCEPT='application/javascript')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'application/javascript; charset=utf-8')
        self.assertEqual(resp.content,
            ('%s(%s);' % (callback_func, _flat_repr)).encode('ascii'))


if yaml:
    _yaml_repr = 'foo: [bar, baz]\n'

    class YAMLRendererTests(TestCase):
        """
        Tests specific to the YAML Renderer
        """

        def test_render(self):
            """
            Test basic YAML rendering.
            """
            obj = {'foo': ['bar', 'baz']}
            renderer = YAMLRenderer()
            content = renderer.render(obj, 'application/yaml')
            self.assertEqual(content, _yaml_repr)

        def test_render_and_parse(self):
            """
            Test rendering and then parsing returns the original object.
            IE obj -> render -> parse -> obj.
            """
            obj = {'foo': ['bar', 'baz']}

            renderer = YAMLRenderer()
            parser = YAMLParser()

            content = renderer.render(obj, 'application/yaml')
            data = parser.parse(StringIO(content))
            self.assertEqual(obj, data)

        def test_render_decimal(self):
            """
            Test YAML decimal rendering.
            """
            renderer = YAMLRenderer()
            content = renderer.render({'field': Decimal('111.2')}, 'application/yaml')
            self.assertYAMLContains(content, "field: '111.2'")

        def assertYAMLContains(self, content, string):
            self.assertTrue(string in content, '%r not in %r' % (string, content))


    class UnicodeYAMLRendererTests(TestCase):
        """
        Tests specific for the Unicode YAML Renderer
        """
        def test_proper_encoding(self):
            obj = {'countries': ['United Kingdom', 'France', 'España']}
            renderer = UnicodeYAMLRenderer()
            content = renderer.render(obj, 'application/yaml')
            self.assertEqual(content.strip(), 'countries: [United Kingdom, France, España]'.encode('utf-8'))


class XMLRendererTestCase(TestCase):
    """
    Tests specific to the XML Renderer
    """

    _complex_data = {
        "creation_date": datetime.datetime(2011, 12, 25, 12, 45, 00),
        "name": "name",
        "sub_data_list": [
            {
                "sub_id": 1,
                "sub_name": "first"
            },
            {
                "sub_id": 2,
                "sub_name": "second"
            }
        ]
    }

    def test_render_string(self):
        """
        Test XML rendering.
        """
        renderer = XMLRenderer()
        content = renderer.render({'field': 'astring'}, 'application/xml')
        self.assertXMLContains(content, '<field>astring</field>')

    def test_render_integer(self):
        """
        Test XML rendering.
        """
        renderer = XMLRenderer()
        content = renderer.render({'field': 111}, 'application/xml')
        self.assertXMLContains(content, '<field>111</field>')

    def test_render_datetime(self):
        """
        Test XML rendering.
        """
        renderer = XMLRenderer()
        content = renderer.render({
            'field': datetime.datetime(2011, 12, 25, 12, 45, 00)
        }, 'application/xml')
        self.assertXMLContains(content, '<field>2011-12-25 12:45:00</field>')

    def test_render_float(self):
        """
        Test XML rendering.
        """
        renderer = XMLRenderer()
        content = renderer.render({'field': 123.4}, 'application/xml')
        self.assertXMLContains(content, '<field>123.4</field>')

    def test_render_decimal(self):
        """
        Test XML rendering.
        """
        renderer = XMLRenderer()
        content = renderer.render({'field': Decimal('111.2')}, 'application/xml')
        self.assertXMLContains(content, '<field>111.2</field>')

    def test_render_none(self):
        """
        Test XML rendering.
        """
        renderer = XMLRenderer()
        content = renderer.render({'field': None}, 'application/xml')
        self.assertXMLContains(content, '<field></field>')

    def test_render_complex_data(self):
        """
        Test XML rendering.
        """
        renderer = XMLRenderer()
        content = renderer.render(self._complex_data, 'application/xml')
        self.assertXMLContains(content, '<sub_name>first</sub_name>')
        self.assertXMLContains(content, '<sub_name>second</sub_name>')

    @unittest.skipUnless(etree, 'defusedxml not installed')
    def test_render_and_parse_complex_data(self):
        """
        Test XML rendering.
        """
        renderer = XMLRenderer()
        content = StringIO(renderer.render(self._complex_data, 'application/xml'))

        parser = XMLParser()
        complex_data_out = parser.parse(content)
        error_msg = "complex data differs!IN:\n %s \n\n OUT:\n %s" % (repr(self._complex_data), repr(complex_data_out))
        self.assertEqual(self._complex_data, complex_data_out, error_msg)

    def assertXMLContains(self, xml, string):
        self.assertTrue(xml.startswith('<?xml version="1.0" encoding="utf-8"?>\n<root>'))
        self.assertTrue(xml.endswith('</root>'))
        self.assertTrue(string in xml, '%r not in %r' % (string, xml))


# Tests for caching issue, #346
class CacheRenderTest(TestCase):
    """
    Tests specific to caching responses
    """

    urls = 'rest_framework.tests.test_renderers'

    cache_key = 'just_a_cache_key'

    @classmethod
    def _get_pickling_errors(cls, obj, seen=None):
        """ Return any errors that would be raised if `obj' is pickled
        Courtesy of koffie @ http://stackoverflow.com/a/7218986/109897
        """
        if seen == None:
            seen = []
        try:
            state = obj.__getstate__()
        except AttributeError:
            return
        if state == None:
            return
        if isinstance(state, tuple):
            if not isinstance(state[0], dict):
                state = state[1]
            else:
                state = state[0].update(state[1])
        result = {}
        for i in state:
            try:
                pickle.dumps(state[i], protocol=2)
            except pickle.PicklingError:
                if not state[i] in seen:
                    seen.append(state[i])
                    result[i] = cls._get_pickling_errors(state[i], seen)
        return result

    def http_resp(self, http_method, url):
        """
        Simple wrapper for Client http requests
        Removes the `client' and `request' attributes from as they are
        added by django.test.client.Client and not part of caching
        responses outside of tests.
        """
        method = getattr(self.client, http_method)
        resp = method(url)
        del resp.client, resp.request
        try:
            del resp.wsgi_request
        except AttributeError:
            pass
        return resp

    def test_obj_pickling(self):
        """
        Test that responses are properly pickled
        """
        resp = self.http_resp('get', '/cache')

        # Make sure that no pickling errors occurred
        self.assertEqual(self._get_pickling_errors(resp), {})

        # Unfortunately LocMem backend doesn't raise PickleErrors but returns
        # None instead.
        cache.set(self.cache_key, resp)
        self.assertTrue(cache.get(self.cache_key) is not None)

    def test_head_caching(self):
        """
        Test caching of HEAD requests
        """
        resp = self.http_resp('head', '/cache')
        cache.set(self.cache_key, resp)

        cached_resp = cache.get(self.cache_key)
        self.assertIsInstance(cached_resp, Response)

    def test_get_caching(self):
        """
        Test caching of GET requests
        """
        resp = self.http_resp('get', '/cache')
        cache.set(self.cache_key, resp)

        cached_resp = cache.get(self.cache_key)
        self.assertIsInstance(cached_resp, Response)
        self.assertEqual(cached_resp.content, resp.content)

########NEW FILE########
__FILENAME__ = test_request
"""
Tests for content parsing, and form-overloaded content parsing.
"""
from __future__ import unicode_literals
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.handlers.wsgi import WSGIRequest
from django.test import TestCase
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.compat import patterns
from rest_framework.parsers import (
    BaseParser,
    FormParser,
    MultiPartParser,
    JSONParser
)
from rest_framework.request import Request, Empty
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.test import APIRequestFactory, APIClient
from rest_framework.views import APIView
from rest_framework.compat import six
from io import BytesIO
import json


factory = APIRequestFactory()


class PlainTextParser(BaseParser):
    media_type = 'text/plain'

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Returns a 2-tuple of `(data, files)`.

        `data` will simply be a string representing the body of the request.
        `files` will always be `None`.
        """
        return stream.read()


class TestMethodOverloading(TestCase):
    def test_method(self):
        """
        Request methods should be same as underlying request.
        """
        request = Request(factory.get('/'))
        self.assertEqual(request.method, 'GET')
        request = Request(factory.post('/'))
        self.assertEqual(request.method, 'POST')

    def test_overloaded_method(self):
        """
        POST requests can be overloaded to another method by setting a
        reserved form field
        """
        request = Request(factory.post('/', {api_settings.FORM_METHOD_OVERRIDE: 'DELETE'}))
        self.assertEqual(request.method, 'DELETE')

    def test_x_http_method_override_header(self):
        """
        POST requests can also be overloaded to another method by setting
        the X-HTTP-Method-Override header.
        """
        request = Request(factory.post('/', {'foo': 'bar'}, HTTP_X_HTTP_METHOD_OVERRIDE='DELETE'))
        self.assertEqual(request.method, 'DELETE')

        request = Request(factory.get('/', {'foo': 'bar'}, HTTP_X_HTTP_METHOD_OVERRIDE='DELETE'))
        self.assertEqual(request.method, 'DELETE')


class TestContentParsing(TestCase):
    def test_standard_behaviour_determines_no_content_GET(self):
        """
        Ensure request.DATA returns empty QueryDict for GET request.
        """
        request = Request(factory.get('/'))
        self.assertEqual(request.DATA, {})

    def test_standard_behaviour_determines_no_content_HEAD(self):
        """
        Ensure request.DATA returns empty QueryDict for HEAD request.
        """
        request = Request(factory.head('/'))
        self.assertEqual(request.DATA, {})

    def test_request_DATA_with_form_content(self):
        """
        Ensure request.DATA returns content for POST request with form content.
        """
        data = {'qwerty': 'uiop'}
        request = Request(factory.post('/', data))
        request.parsers = (FormParser(), MultiPartParser())
        self.assertEqual(list(request.DATA.items()), list(data.items()))

    def test_request_DATA_with_text_content(self):
        """
        Ensure request.DATA returns content for POST request with
        non-form content.
        """
        content = six.b('qwerty')
        content_type = 'text/plain'
        request = Request(factory.post('/', content, content_type=content_type))
        request.parsers = (PlainTextParser(),)
        self.assertEqual(request.DATA, content)

    def test_request_POST_with_form_content(self):
        """
        Ensure request.POST returns content for POST request with form content.
        """
        data = {'qwerty': 'uiop'}
        request = Request(factory.post('/', data))
        request.parsers = (FormParser(), MultiPartParser())
        self.assertEqual(list(request.POST.items()), list(data.items()))

    def test_standard_behaviour_determines_form_content_PUT(self):
        """
        Ensure request.DATA returns content for PUT request with form content.
        """
        data = {'qwerty': 'uiop'}
        request = Request(factory.put('/', data))
        request.parsers = (FormParser(), MultiPartParser())
        self.assertEqual(list(request.DATA.items()), list(data.items()))

    def test_standard_behaviour_determines_non_form_content_PUT(self):
        """
        Ensure request.DATA returns content for PUT request with
        non-form content.
        """
        content = six.b('qwerty')
        content_type = 'text/plain'
        request = Request(factory.put('/', content, content_type=content_type))
        request.parsers = (PlainTextParser(), )
        self.assertEqual(request.DATA, content)

    def test_overloaded_behaviour_allows_content_tunnelling(self):
        """
        Ensure request.DATA returns content for overloaded POST request.
        """
        json_data = {'foobar': 'qwerty'}
        content = json.dumps(json_data)
        content_type = 'application/json'
        form_data = {
            api_settings.FORM_CONTENT_OVERRIDE: content,
            api_settings.FORM_CONTENTTYPE_OVERRIDE: content_type
        }
        request = Request(factory.post('/', form_data))
        request.parsers = (JSONParser(), )
        self.assertEqual(request.DATA, json_data)

    def test_form_POST_unicode(self):
        """
        JSON POST via default web interface with unicode data
        """
        # Note: environ and other variables here have simplified content compared to real Request
        CONTENT = b'_content_type=application%2Fjson&_content=%7B%22request%22%3A+4%2C+%22firm%22%3A+1%2C+%22text%22%3A+%22%D0%9F%D1%80%D0%B8%D0%B2%D0%B5%D1%82%21%22%7D'
        environ = {
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': 'application/x-www-form-urlencoded',
            'CONTENT_LENGTH': len(CONTENT),
            'wsgi.input': BytesIO(CONTENT),
        }
        wsgi_request = WSGIRequest(environ=environ)
        wsgi_request._load_post_and_files()
        parsers = (JSONParser(), FormParser(), MultiPartParser())
        parser_context = {
            'encoding': 'utf-8',
            'kwargs': {},
            'args': (),
        }
        request = Request(wsgi_request, parsers=parsers, parser_context=parser_context)
        method = request.method
        self.assertEqual(method, 'POST')
        self.assertEqual(request._content_type, 'application/json')
        self.assertEqual(request._stream.getvalue(), b'{"request": 4, "firm": 1, "text": "\xd0\x9f\xd1\x80\xd0\xb8\xd0\xb2\xd0\xb5\xd1\x82!"}')
        self.assertEqual(request._data, Empty)
        self.assertEqual(request._files, Empty)

    # def test_accessing_post_after_data_form(self):
    #     """
    #     Ensures request.POST can be accessed after request.DATA in
    #     form request.
    #     """
    #     data = {'qwerty': 'uiop'}
    #     request = factory.post('/', data=data)
    #     self.assertEqual(request.DATA.items(), data.items())
    #     self.assertEqual(request.POST.items(), data.items())

    # def test_accessing_post_after_data_for_json(self):
    #     """
    #     Ensures request.POST can be accessed after request.DATA in
    #     json request.
    #     """
    #     data = {'qwerty': 'uiop'}
    #     content = json.dumps(data)
    #     content_type = 'application/json'
    #     parsers = (JSONParser, )

    #     request = factory.post('/', content, content_type=content_type,
    #                            parsers=parsers)
    #     self.assertEqual(request.DATA.items(), data.items())
    #     self.assertEqual(request.POST.items(), [])

    # def test_accessing_post_after_data_for_overloaded_json(self):
    #     """
    #     Ensures request.POST can be accessed after request.DATA in overloaded
    #     json request.
    #     """
    #     data = {'qwerty': 'uiop'}
    #     content = json.dumps(data)
    #     content_type = 'application/json'
    #     parsers = (JSONParser, )
    #     form_data = {Request._CONTENT_PARAM: content,
    #                  Request._CONTENTTYPE_PARAM: content_type}

    #     request = factory.post('/', form_data, parsers=parsers)
    #     self.assertEqual(request.DATA.items(), data.items())
    #     self.assertEqual(request.POST.items(), form_data.items())

    # def test_accessing_data_after_post_form(self):
    #     """
    #     Ensures request.DATA can be accessed after request.POST in
    #     form request.
    #     """
    #     data = {'qwerty': 'uiop'}
    #     parsers = (FormParser, MultiPartParser)
    #     request = factory.post('/', data, parsers=parsers)

    #     self.assertEqual(request.POST.items(), data.items())
    #     self.assertEqual(request.DATA.items(), data.items())

    # def test_accessing_data_after_post_for_json(self):
    #     """
    #     Ensures request.DATA can be accessed after request.POST in
    #     json request.
    #     """
    #     data = {'qwerty': 'uiop'}
    #     content = json.dumps(data)
    #     content_type = 'application/json'
    #     parsers = (JSONParser, )
    #     request = factory.post('/', content, content_type=content_type,
    #                            parsers=parsers)
    #     self.assertEqual(request.POST.items(), [])
    #     self.assertEqual(request.DATA.items(), data.items())

    # def test_accessing_data_after_post_for_overloaded_json(self):
    #     """
    #     Ensures request.DATA can be accessed after request.POST in overloaded
    #     json request
    #     """
    #     data = {'qwerty': 'uiop'}
    #     content = json.dumps(data)
    #     content_type = 'application/json'
    #     parsers = (JSONParser, )
    #     form_data = {Request._CONTENT_PARAM: content,
    #                  Request._CONTENTTYPE_PARAM: content_type}

    #     request = factory.post('/', form_data, parsers=parsers)
    #     self.assertEqual(request.POST.items(), form_data.items())
    #     self.assertEqual(request.DATA.items(), data.items())


class MockView(APIView):
    authentication_classes = (SessionAuthentication,)

    def post(self, request):
        if request.POST.get('example') is not None:
            return Response(status=status.HTTP_200_OK)

        return Response(status=status.INTERNAL_SERVER_ERROR)

urlpatterns = patterns('',
    (r'^$', MockView.as_view()),
)


class TestContentParsingWithAuthentication(TestCase):
    urls = 'rest_framework.tests.test_request'

    def setUp(self):
        self.csrf_client = APIClient(enforce_csrf_checks=True)
        self.username = 'john'
        self.email = 'lennon@thebeatles.com'
        self.password = 'password'
        self.user = User.objects.create_user(self.username, self.email, self.password)

    def test_user_logged_in_authentication_has_POST_when_not_logged_in(self):
        """
        Ensures request.POST exists after SessionAuthentication when user
        doesn't log in.
        """
        content = {'example': 'example'}

        response = self.client.post('/', content)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        response = self.csrf_client.post('/', content)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

    # def test_user_logged_in_authentication_has_post_when_logged_in(self):
    #     """Ensures request.POST exists after UserLoggedInAuthentication when user does log in"""
    #     self.client.login(username='john', password='password')
    #     self.csrf_client.login(username='john', password='password')
    #     content = {'example': 'example'}

    #     response = self.client.post('/', content)
    #     self.assertEqual(status.OK, response.status_code, "POST data is malformed")

    #     response = self.csrf_client.post('/', content)
    #     self.assertEqual(status.OK, response.status_code, "POST data is malformed")


class TestUserSetter(TestCase):

    def setUp(self):
        # Pass request object through session middleware so session is
        # available to login and logout functions
        self.request = Request(factory.get('/'))
        SessionMiddleware().process_request(self.request)

        User.objects.create_user('ringo', 'starr@thebeatles.com', 'yellow')
        self.user = authenticate(username='ringo', password='yellow')

    def test_user_can_be_set(self):
        self.request.user = self.user
        self.assertEqual(self.request.user, self.user)

    def test_user_can_login(self):
        login(self.request, self.user)
        self.assertEqual(self.request.user, self.user)

    def test_user_can_logout(self):
        self.request.user = self.user
        self.assertFalse(self.request.user.is_anonymous())
        logout(self.request)
        self.assertTrue(self.request.user.is_anonymous())


class TestAuthSetter(TestCase):

    def test_auth_can_be_set(self):
        request = Request(factory.get('/'))
        request.auth = 'DUMMY'
        self.assertEqual(request.auth, 'DUMMY')

########NEW FILE########
__FILENAME__ = test_response
from __future__ import unicode_literals
from django.test import TestCase
from rest_framework.tests.models import BasicModel, BasicModelSerializer
from rest_framework.compat import patterns, url, include
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework import routers
from rest_framework import status
from rest_framework.renderers import (
    BaseRenderer,
    JSONRenderer,
    BrowsableAPIRenderer
)
from rest_framework import viewsets
from rest_framework.settings import api_settings
from rest_framework.compat import six


class MockPickleRenderer(BaseRenderer):
    media_type = 'application/pickle'


class MockJsonRenderer(BaseRenderer):
    media_type = 'application/json'


class MockTextMediaRenderer(BaseRenderer):
    media_type = 'text/html'

DUMMYSTATUS = status.HTTP_200_OK
DUMMYCONTENT = 'dummycontent'

RENDERER_A_SERIALIZER = lambda x: ('Renderer A: %s' % x).encode('ascii')
RENDERER_B_SERIALIZER = lambda x: ('Renderer B: %s' % x).encode('ascii')


class RendererA(BaseRenderer):
    media_type = 'mock/renderera'
    format = "formata"

    def render(self, data, media_type=None, renderer_context=None):
        return RENDERER_A_SERIALIZER(data)


class RendererB(BaseRenderer):
    media_type = 'mock/rendererb'
    format = "formatb"

    def render(self, data, media_type=None, renderer_context=None):
        return RENDERER_B_SERIALIZER(data)


class RendererC(RendererB):
    media_type = 'mock/rendererc'
    format = 'formatc'
    charset = "rendererc"


class MockView(APIView):
    renderer_classes = (RendererA, RendererB, RendererC)

    def get(self, request, **kwargs):
        return Response(DUMMYCONTENT, status=DUMMYSTATUS)


class MockViewSettingContentType(APIView):
    renderer_classes = (RendererA, RendererB, RendererC)

    def get(self, request, **kwargs):
        return Response(DUMMYCONTENT, status=DUMMYSTATUS, content_type='setbyview')


class HTMLView(APIView):
    renderer_classes = (BrowsableAPIRenderer, )

    def get(self, request, **kwargs):
        return Response('text')


class HTMLView1(APIView):
    renderer_classes = (BrowsableAPIRenderer, JSONRenderer)

    def get(self, request, **kwargs):
        return Response('text')


class HTMLNewModelViewSet(viewsets.ModelViewSet):
    model = BasicModel


class HTMLNewModelView(generics.ListCreateAPIView):
    renderer_classes = (BrowsableAPIRenderer,)
    permission_classes = []
    serializer_class = BasicModelSerializer
    model = BasicModel


new_model_viewset_router = routers.DefaultRouter()
new_model_viewset_router.register(r'', HTMLNewModelViewSet)


urlpatterns = patterns('',
    url(r'^setbyview$', MockViewSettingContentType.as_view(renderer_classes=[RendererA, RendererB, RendererC])),
    url(r'^.*\.(?P<format>.+)$', MockView.as_view(renderer_classes=[RendererA, RendererB, RendererC])),
    url(r'^$', MockView.as_view(renderer_classes=[RendererA, RendererB, RendererC])),
    url(r'^html$', HTMLView.as_view()),
    url(r'^html1$', HTMLView1.as_view()),
    url(r'^html_new_model$', HTMLNewModelView.as_view()),
    url(r'^html_new_model_viewset', include(new_model_viewset_router.urls)),
    url(r'^restframework', include('rest_framework.urls', namespace='rest_framework'))
)


# TODO: Clean tests bellow - remove duplicates with above, better unit testing, ...
class RendererIntegrationTests(TestCase):
    """
    End-to-end testing of renderers using an ResponseMixin on a generic view.
    """

    urls = 'rest_framework.tests.test_response'

    def test_default_renderer_serializes_content(self):
        """If the Accept header is not set the default renderer should serialize the response."""
        resp = self.client.get('/')
        self.assertEqual(resp['Content-Type'], RendererA.media_type + '; charset=utf-8')
        self.assertEqual(resp.content, RENDERER_A_SERIALIZER(DUMMYCONTENT))
        self.assertEqual(resp.status_code, DUMMYSTATUS)

    def test_head_method_serializes_no_content(self):
        """No response must be included in HEAD requests."""
        resp = self.client.head('/')
        self.assertEqual(resp.status_code, DUMMYSTATUS)
        self.assertEqual(resp['Content-Type'], RendererA.media_type + '; charset=utf-8')
        self.assertEqual(resp.content, six.b(''))

    def test_default_renderer_serializes_content_on_accept_any(self):
        """If the Accept header is set to */* the default renderer should serialize the response."""
        resp = self.client.get('/', HTTP_ACCEPT='*/*')
        self.assertEqual(resp['Content-Type'], RendererA.media_type + '; charset=utf-8')
        self.assertEqual(resp.content, RENDERER_A_SERIALIZER(DUMMYCONTENT))
        self.assertEqual(resp.status_code, DUMMYSTATUS)

    def test_specified_renderer_serializes_content_default_case(self):
        """If the Accept header is set the specified renderer should serialize the response.
        (In this case we check that works for the default renderer)"""
        resp = self.client.get('/', HTTP_ACCEPT=RendererA.media_type)
        self.assertEqual(resp['Content-Type'], RendererA.media_type + '; charset=utf-8')
        self.assertEqual(resp.content, RENDERER_A_SERIALIZER(DUMMYCONTENT))
        self.assertEqual(resp.status_code, DUMMYSTATUS)

    def test_specified_renderer_serializes_content_non_default_case(self):
        """If the Accept header is set the specified renderer should serialize the response.
        (In this case we check that works for a non-default renderer)"""
        resp = self.client.get('/', HTTP_ACCEPT=RendererB.media_type)
        self.assertEqual(resp['Content-Type'], RendererB.media_type + '; charset=utf-8')
        self.assertEqual(resp.content, RENDERER_B_SERIALIZER(DUMMYCONTENT))
        self.assertEqual(resp.status_code, DUMMYSTATUS)

    def test_specified_renderer_serializes_content_on_accept_query(self):
        """The '_accept' query string should behave in the same way as the Accept header."""
        param = '?%s=%s' % (
            api_settings.URL_ACCEPT_OVERRIDE,
            RendererB.media_type
        )
        resp = self.client.get('/' + param)
        self.assertEqual(resp['Content-Type'], RendererB.media_type + '; charset=utf-8')
        self.assertEqual(resp.content, RENDERER_B_SERIALIZER(DUMMYCONTENT))
        self.assertEqual(resp.status_code, DUMMYSTATUS)

    def test_specified_renderer_serializes_content_on_format_query(self):
        """If a 'format' query is specified, the renderer with the matching
        format attribute should serialize the response."""
        resp = self.client.get('/?format=%s' % RendererB.format)
        self.assertEqual(resp['Content-Type'], RendererB.media_type + '; charset=utf-8')
        self.assertEqual(resp.content, RENDERER_B_SERIALIZER(DUMMYCONTENT))
        self.assertEqual(resp.status_code, DUMMYSTATUS)

    def test_specified_renderer_serializes_content_on_format_kwargs(self):
        """If a 'format' keyword arg is specified, the renderer with the matching
        format attribute should serialize the response."""
        resp = self.client.get('/something.formatb')
        self.assertEqual(resp['Content-Type'], RendererB.media_type + '; charset=utf-8')
        self.assertEqual(resp.content, RENDERER_B_SERIALIZER(DUMMYCONTENT))
        self.assertEqual(resp.status_code, DUMMYSTATUS)

    def test_specified_renderer_is_used_on_format_query_with_matching_accept(self):
        """If both a 'format' query and a matching Accept header specified,
        the renderer with the matching format attribute should serialize the response."""
        resp = self.client.get('/?format=%s' % RendererB.format,
                               HTTP_ACCEPT=RendererB.media_type)
        self.assertEqual(resp['Content-Type'], RendererB.media_type + '; charset=utf-8')
        self.assertEqual(resp.content, RENDERER_B_SERIALIZER(DUMMYCONTENT))
        self.assertEqual(resp.status_code, DUMMYSTATUS)


class Issue122Tests(TestCase):
    """
    Tests that covers #122.
    """
    urls = 'rest_framework.tests.test_response'

    def test_only_html_renderer(self):
        """
        Test if no infinite recursion occurs.
        """
        self.client.get('/html')

    def test_html_renderer_is_first(self):
        """
        Test if no infinite recursion occurs.
        """
        self.client.get('/html1')


class Issue467Tests(TestCase):
    """
    Tests for #467
    """

    urls = 'rest_framework.tests.test_response'

    def test_form_has_label_and_help_text(self):
        resp = self.client.get('/html_new_model')
        self.assertEqual(resp['Content-Type'], 'text/html; charset=utf-8')
        self.assertContains(resp, 'Text comes here')
        self.assertContains(resp, 'Text description.')


class Issue807Tests(TestCase):
    """
    Covers #807
    """

    urls = 'rest_framework.tests.test_response'

    def test_does_not_append_charset_by_default(self):
        """
        Renderers don't include a charset unless set explicitly.
        """
        headers = {"HTTP_ACCEPT": RendererA.media_type}
        resp = self.client.get('/', **headers)
        expected = "{0}; charset={1}".format(RendererA.media_type, 'utf-8')
        self.assertEqual(expected, resp['Content-Type'])

    def test_if_there_is_charset_specified_on_renderer_it_gets_appended(self):
        """
        If renderer class has charset attribute declared, it gets appended
        to Response's Content-Type
        """
        headers = {"HTTP_ACCEPT": RendererC.media_type}
        resp = self.client.get('/', **headers)
        expected = "{0}; charset={1}".format(RendererC.media_type, RendererC.charset)
        self.assertEqual(expected, resp['Content-Type'])

    def test_content_type_set_explictly_on_response(self):
        """
        The content type may be set explictly on the response.
        """
        headers = {"HTTP_ACCEPT": RendererC.media_type}
        resp = self.client.get('/setbyview', **headers)
        self.assertEqual('setbyview', resp['Content-Type'])

    def test_viewset_label_help_text(self):
        param = '?%s=%s' % (
            api_settings.URL_ACCEPT_OVERRIDE,
            'text/html'
        )
        resp = self.client.get('/html_new_model_viewset/' + param)
        self.assertEqual(resp['Content-Type'], 'text/html; charset=utf-8')
        self.assertContains(resp, 'Text comes here')
        self.assertContains(resp, 'Text description.')

    def test_form_has_label_and_help_text(self):
        resp = self.client.get('/html_new_model')
        self.assertEqual(resp['Content-Type'], 'text/html; charset=utf-8')
        self.assertContains(resp, 'Text comes here')
        self.assertContains(resp, 'Text description.')

########NEW FILE########
__FILENAME__ = test_reverse
from __future__ import unicode_literals
from django.test import TestCase
from rest_framework.compat import patterns, url
from rest_framework.reverse import reverse
from rest_framework.test import APIRequestFactory

factory = APIRequestFactory()


def null_view(request):
    pass

urlpatterns = patterns('',
    url(r'^view$', null_view, name='view'),
)


class ReverseTests(TestCase):
    """
    Tests for fully qualified URLs when using `reverse`.
    """
    urls = 'rest_framework.tests.test_reverse'

    def test_reversed_urls_are_fully_qualified(self):
        request = factory.get('/view')
        url = reverse('view', request=request)
        self.assertEqual(url, 'http://testserver/view')

########NEW FILE########
__FILENAME__ = test_routers
from __future__ import unicode_literals
from django.db import models
from django.test import TestCase
from django.core.exceptions import ImproperlyConfigured
from rest_framework import serializers, viewsets, permissions
from rest_framework.compat import include, patterns, url
from rest_framework.decorators import link, action
from rest_framework.response import Response
from rest_framework.routers import SimpleRouter, DefaultRouter
from rest_framework.test import APIRequestFactory

factory = APIRequestFactory()

urlpatterns = patterns('',)


class BasicViewSet(viewsets.ViewSet):
    def list(self, request, *args, **kwargs):
        return Response({'method': 'list'})

    @action()
    def action1(self, request, *args, **kwargs):
        return Response({'method': 'action1'})

    @action()
    def action2(self, request, *args, **kwargs):
        return Response({'method': 'action2'})

    @action(methods=['post', 'delete'])
    def action3(self, request, *args, **kwargs):
        return Response({'method': 'action2'})

    @link()
    def link1(self, request, *args, **kwargs):
        return Response({'method': 'link1'})

    @link()
    def link2(self, request, *args, **kwargs):
        return Response({'method': 'link2'})


class TestSimpleRouter(TestCase):
    def setUp(self):
        self.router = SimpleRouter()

    def test_link_and_action_decorator(self):
        routes = self.router.get_routes(BasicViewSet)
        decorator_routes = routes[2:]
        # Make sure all these endpoints exist and none have been clobbered
        for i, endpoint in enumerate(['action1', 'action2', 'action3', 'link1', 'link2']):
            route = decorator_routes[i]
            # check url listing
            self.assertEqual(route.url,
                             '^{{prefix}}/{{lookup}}/{0}{{trailing_slash}}$'.format(endpoint))
            # check method to function mapping
            if endpoint == 'action3':
                methods_map = ['post', 'delete']
            elif endpoint.startswith('action'):
                methods_map = ['post']
            else:
                methods_map = ['get']
            for method in methods_map:
                self.assertEqual(route.mapping[method], endpoint)


class RouterTestModel(models.Model):
    uuid = models.CharField(max_length=20)
    text = models.CharField(max_length=200)


class TestCustomLookupFields(TestCase):
    """
    Ensure that custom lookup fields are correctly routed.
    """
    urls = 'rest_framework.tests.test_routers'

    def setUp(self):
        class NoteSerializer(serializers.HyperlinkedModelSerializer):
            class Meta:
                model = RouterTestModel
                lookup_field = 'uuid'
                fields = ('url', 'uuid', 'text')

        class NoteViewSet(viewsets.ModelViewSet):
            queryset = RouterTestModel.objects.all()
            serializer_class = NoteSerializer
            lookup_field = 'uuid'

        RouterTestModel.objects.create(uuid='123', text='foo bar')

        self.router = SimpleRouter()
        self.router.register(r'notes', NoteViewSet)

        from rest_framework.tests import test_routers
        urls = getattr(test_routers, 'urlpatterns')
        urls += patterns('',
            url(r'^', include(self.router.urls)),
        )

    def test_custom_lookup_field_route(self):
        detail_route = self.router.urls[-1]
        detail_url_pattern = detail_route.regex.pattern
        self.assertIn('<uuid>', detail_url_pattern)

    def test_retrieve_lookup_field_list_view(self):
        response = self.client.get('/notes/')
        self.assertEqual(response.data,
            [{
                "url": "http://testserver/notes/123/",
                "uuid": "123", "text": "foo bar"
            }]
        )

    def test_retrieve_lookup_field_detail_view(self):
        response = self.client.get('/notes/123/')
        self.assertEqual(response.data,
            {
                "url": "http://testserver/notes/123/",
                "uuid": "123", "text": "foo bar"
            }
        )


class TestTrailingSlashIncluded(TestCase):
    def setUp(self):
        class NoteViewSet(viewsets.ModelViewSet):
            model = RouterTestModel

        self.router = SimpleRouter()
        self.router.register(r'notes', NoteViewSet)
        self.urls = self.router.urls

    def test_urls_have_trailing_slash_by_default(self):
        expected = ['^notes/$', '^notes/(?P<pk>[^/]+)/$']
        for idx in range(len(expected)):
            self.assertEqual(expected[idx], self.urls[idx].regex.pattern)


class TestTrailingSlashRemoved(TestCase):
    def setUp(self):
        class NoteViewSet(viewsets.ModelViewSet):
            model = RouterTestModel

        self.router = SimpleRouter(trailing_slash=False)
        self.router.register(r'notes', NoteViewSet)
        self.urls = self.router.urls

    def test_urls_can_have_trailing_slash_removed(self):
        expected = ['^notes$', '^notes/(?P<pk>[^/.]+)$']
        for idx in range(len(expected)):
            self.assertEqual(expected[idx], self.urls[idx].regex.pattern)


class TestNameableRoot(TestCase):
    def setUp(self):
        class NoteViewSet(viewsets.ModelViewSet):
            model = RouterTestModel
        self.router = DefaultRouter()
        self.router.root_view_name = 'nameable-root'
        self.router.register(r'notes', NoteViewSet)
        self.urls = self.router.urls

    def test_router_has_custom_name(self):
        expected = 'nameable-root'
        self.assertEqual(expected, self.urls[0].name)


class TestActionKeywordArgs(TestCase):
    """
    Ensure keyword arguments passed in the `@action` decorator
    are properly handled.  Refs #940.
    """

    def setUp(self):
        class TestViewSet(viewsets.ModelViewSet):
            permission_classes = []

            @action(permission_classes=[permissions.AllowAny])
            def custom(self, request, *args, **kwargs):
                return Response({
                    'permission_classes': self.permission_classes
                })

        self.router = SimpleRouter()
        self.router.register(r'test', TestViewSet, base_name='test')
        self.view = self.router.urls[-1].callback

    def test_action_kwargs(self):
        request = factory.post('/test/0/custom/')
        response = self.view(request)
        self.assertEqual(
            response.data,
            {'permission_classes': [permissions.AllowAny]}
        )


class TestActionAppliedToExistingRoute(TestCase):
    """
    Ensure `@action` decorator raises an except when applied
    to an existing route
    """

    def test_exception_raised_when_action_applied_to_existing_route(self):
        class TestViewSet(viewsets.ModelViewSet):

            @action()
            def retrieve(self, request, *args, **kwargs):
                return Response({
                    'hello': 'world'
                })

        self.router = SimpleRouter()
        self.router.register(r'test', TestViewSet, base_name='test')

        with self.assertRaises(ImproperlyConfigured):
            self.router.urls

########NEW FILE########
__FILENAME__ = test_serializer
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models
from django.db.models.fields import BLANK_CHOICE_DASH
from django.test import TestCase
from django.utils import unittest
from django.utils.datastructures import MultiValueDict
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers, fields, relations
from rest_framework.tests.models import (HasPositiveIntegerAsChoice, Album, ActionItem, Anchor, BasicModel,
    BlankFieldModel, BlogPost, BlogPostComment, Book, CallableDefaultValueModel, DefaultValueModel,
    ManyToManyModel, Person, ReadOnlyManyToManyModel, Photo, RESTFrameworkModel,
    ForeignKeySource, ManyToManySource)
from rest_framework.tests.models import BasicModelSerializer
import datetime
import pickle
try:
    import PIL
except:
    PIL = None


if PIL is not None:
    class AMOAFModel(RESTFrameworkModel):
        char_field = models.CharField(max_length=1024, blank=True)
        comma_separated_integer_field = models.CommaSeparatedIntegerField(max_length=1024, blank=True)
        decimal_field = models.DecimalField(max_digits=64, decimal_places=32, blank=True)
        email_field = models.EmailField(max_length=1024, blank=True)
        file_field = models.FileField(upload_to='test', max_length=1024, blank=True)
        image_field = models.ImageField(upload_to='test', max_length=1024, blank=True)
        slug_field = models.SlugField(max_length=1024, blank=True)
        url_field = models.URLField(max_length=1024, blank=True)

    class DVOAFModel(RESTFrameworkModel):
        positive_integer_field = models.PositiveIntegerField(blank=True)
        positive_small_integer_field = models.PositiveSmallIntegerField(blank=True)
        email_field = models.EmailField(blank=True)
        file_field = models.FileField(upload_to='test', blank=True)
        image_field = models.ImageField(upload_to='test', blank=True)
        slug_field = models.SlugField(blank=True)
        url_field = models.URLField(blank=True)


class SubComment(object):
    def __init__(self, sub_comment):
        self.sub_comment = sub_comment


class Comment(object):
    def __init__(self, email, content, created):
        self.email = email
        self.content = content
        self.created = created or datetime.datetime.now()

    def __eq__(self, other):
        return all([getattr(self, attr) == getattr(other, attr)
                    for attr in ('email', 'content', 'created')])

    def get_sub_comment(self):
        sub_comment = SubComment('And Merry Christmas!')
        return sub_comment


class CommentSerializer(serializers.Serializer):
    email = serializers.EmailField()
    content = serializers.CharField(max_length=1000)
    created = serializers.DateTimeField()
    sub_comment = serializers.Field(source='get_sub_comment.sub_comment')

    def restore_object(self, data, instance=None):
        if instance is None:
            return Comment(**data)
        for key, val in data.items():
            setattr(instance, key, val)
        return instance


class NamesSerializer(serializers.Serializer):
    first = serializers.CharField()
    last = serializers.CharField(required=False, default='')
    initials = serializers.CharField(required=False, default='')


class PersonIdentifierSerializer(serializers.Serializer):
    ssn = serializers.CharField()
    names = NamesSerializer(source='names', required=False)


class BookSerializer(serializers.ModelSerializer):
    isbn = serializers.RegexField(regex=r'^[0-9]{13}$', error_messages={'invalid': 'isbn has to be exact 13 numbers'})

    class Meta:
        model = Book


class ActionItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = ActionItem

class ActionItemSerializerOptionalFields(serializers.ModelSerializer):
    """
    Intended to test that fields with `required=False` are excluded from validation.
    """
    title = serializers.CharField(required=False)

    class Meta:
        model = ActionItem
        fields = ('title',)

class ActionItemSerializerCustomRestore(serializers.ModelSerializer):

    class Meta:
        model = ActionItem

    def restore_object(self, data, instance=None):
        if instance is None:
            return ActionItem(**data)
        for key, val in data.items():
            setattr(instance, key, val)
        return instance


class PersonSerializer(serializers.ModelSerializer):
    info = serializers.Field(source='info')

    class Meta:
        model = Person
        fields = ('name', 'age', 'info')
        read_only_fields = ('age',)


class NestedSerializer(serializers.Serializer):
    info = serializers.Field()


class ModelSerializerWithNestedSerializer(serializers.ModelSerializer):
    nested = NestedSerializer(source='*')

    class Meta:
        model = Person


class NestedSerializerWithRenamedField(serializers.Serializer):
    renamed_info = serializers.Field(source='info')


class ModelSerializerWithNestedSerializerWithRenamedField(serializers.ModelSerializer):
    nested = NestedSerializerWithRenamedField(source='*')

    class Meta:
        model = Person


class PersonSerializerInvalidReadOnly(serializers.ModelSerializer):
    """
    Testing for #652.
    """
    info = serializers.Field(source='info')

    class Meta:
        model = Person
        fields = ('name', 'age', 'info')
        read_only_fields = ('age', 'info')


class AlbumsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Album
        fields = ['title', 'ref']  # lists are also valid options


class PositiveIntegerAsChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = HasPositiveIntegerAsChoice
        fields = ['some_integer']


class ForeignKeySourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ForeignKeySource


class HyperlinkedForeignKeySourceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ForeignKeySource


class BasicTests(TestCase):
    def setUp(self):
        self.comment = Comment(
            'tom@example.com',
            'Happy new year!',
            datetime.datetime(2012, 1, 1)
        )
        self.actionitem = ActionItem(title='Some to do item',)
        self.data = {
            'email': 'tom@example.com',
            'content': 'Happy new year!',
            'created': datetime.datetime(2012, 1, 1),
            'sub_comment': 'This wont change'
        }
        self.expected = {
            'email': 'tom@example.com',
            'content': 'Happy new year!',
            'created': datetime.datetime(2012, 1, 1),
            'sub_comment': 'And Merry Christmas!'
        }
        self.person_data = {'name': 'dwight', 'age': 35}
        self.person = Person(**self.person_data)
        self.person.save()

    def test_empty(self):
        serializer = CommentSerializer()
        expected = {
            'email': '',
            'content': '',
            'created': None
        }
        self.assertEqual(serializer.data, expected)

    def test_retrieve(self):
        serializer = CommentSerializer(self.comment)
        self.assertEqual(serializer.data, self.expected)

    def test_create(self):
        serializer = CommentSerializer(data=self.data)
        expected = self.comment
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(serializer.object, expected)
        self.assertFalse(serializer.object is expected)
        self.assertEqual(serializer.data['sub_comment'], 'And Merry Christmas!')

    def test_create_nested(self):
        """Test a serializer with nested data."""
        names = {'first': 'John', 'last': 'Doe', 'initials': 'jd'}
        data = {'ssn': '1234567890', 'names': names}
        serializer = PersonIdentifierSerializer(data=data)

        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(serializer.object, data)
        self.assertFalse(serializer.object is data)
        self.assertEqual(serializer.data['names'], names)

    def test_create_partial_nested(self):
        """Test a serializer with nested data which has missing fields."""
        names = {'first': 'John'}
        data = {'ssn': '1234567890', 'names': names}
        serializer = PersonIdentifierSerializer(data=data)

        expected_names = {'first': 'John', 'last': '', 'initials': ''}
        data['names'] = expected_names

        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(serializer.object, data)
        self.assertFalse(serializer.object is expected_names)
        self.assertEqual(serializer.data['names'], expected_names)

    def test_null_nested(self):
        """Test a serializer with a nonexistent nested field"""
        data = {'ssn': '1234567890'}
        serializer = PersonIdentifierSerializer(data=data)

        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(serializer.object, data)
        self.assertFalse(serializer.object is data)
        expected = {'ssn': '1234567890', 'names': None}
        self.assertEqual(serializer.data, expected)

    def test_update(self):
        serializer = CommentSerializer(self.comment, data=self.data)
        expected = self.comment
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(serializer.object, expected)
        self.assertTrue(serializer.object is expected)
        self.assertEqual(serializer.data['sub_comment'], 'And Merry Christmas!')

    def test_partial_update(self):
        msg = 'Merry New Year!'
        partial_data = {'content': msg}
        serializer = CommentSerializer(self.comment, data=partial_data)
        self.assertEqual(serializer.is_valid(), False)
        serializer = CommentSerializer(self.comment, data=partial_data, partial=True)
        expected = self.comment
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(serializer.object, expected)
        self.assertTrue(serializer.object is expected)
        self.assertEqual(serializer.data['content'], msg)

    def test_model_fields_as_expected(self):
        """
        Make sure that the fields returned are the same as defined
        in the Meta data
        """
        serializer = PersonSerializer(self.person)
        self.assertEqual(set(serializer.data.keys()),
                          set(['name', 'age', 'info']))

    def test_field_with_dictionary(self):
        """
        Make sure that dictionaries from fields are left intact
        """
        serializer = PersonSerializer(self.person)
        expected = self.person_data
        self.assertEqual(serializer.data['info'], expected)

    def test_read_only_fields(self):
        """
        Attempting to update fields set as read_only should have no effect.
        """
        serializer = PersonSerializer(self.person, data={'name': 'dwight', 'age': 99})
        self.assertEqual(serializer.is_valid(), True)
        instance = serializer.save()
        self.assertEqual(serializer.errors, {})
        # Assert age is unchanged (35)
        self.assertEqual(instance.age, self.person_data['age'])

    def test_invalid_read_only_fields(self):
        """
        Regression test for #652.
        """
        self.assertRaises(AssertionError, PersonSerializerInvalidReadOnly, [])

    def test_serializer_data_is_cleared_on_save(self):
        """
        Check _data attribute is cleared on `save()`

        Regression test for #1116
            — id field is not populated if `data` is accessed prior to `save()`
        """
        serializer = ActionItemSerializer(self.actionitem)
        self.assertIsNone(serializer.data.get('id',None), 'New instance. `id` should not be set.')
        serializer.save()
        self.assertIsNotNone(serializer.data.get('id',None), 'Model is saved. `id` should be set.')

    def test_fields_marked_as_not_required_are_excluded_from_validation(self):
        """
        Check that fields with `required=False` are included in list of exclusions.
        """
        serializer = ActionItemSerializerOptionalFields(self.actionitem)
        exclusions = serializer.get_validation_exclusions()
        self.assertTrue('title' in exclusions, '`title` field was marked `required=False` and should be excluded')


class DictStyleSerializer(serializers.Serializer):
    """
    Note that we don't have any `restore_object` method, so the default
    case of simply returning a dict will apply.
    """
    email = serializers.EmailField()


class DictStyleSerializerTests(TestCase):
    def test_dict_style_deserialize(self):
        """
        Ensure serializers can deserialize into a dict.
        """
        data = {'email': 'foo@example.com'}
        serializer = DictStyleSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.data, data)

    def test_dict_style_serialize(self):
        """
        Ensure serializers can serialize dict objects.
        """
        data = {'email': 'foo@example.com'}
        serializer = DictStyleSerializer(data)
        self.assertEqual(serializer.data, data)


class ValidationTests(TestCase):
    def setUp(self):
        self.comment = Comment(
            'tom@example.com',
            'Happy new year!',
            datetime.datetime(2012, 1, 1)
        )
        self.data = {
            'email': 'tom@example.com',
            'content': 'x' * 1001,
            'created': datetime.datetime(2012, 1, 1)
        }
        self.actionitem = ActionItem(title='Some to do item',)

    def test_create(self):
        serializer = CommentSerializer(data=self.data)
        self.assertEqual(serializer.is_valid(), False)
        self.assertEqual(serializer.errors, {'content': ['Ensure this value has at most 1000 characters (it has 1001).']})

    def test_update(self):
        serializer = CommentSerializer(self.comment, data=self.data)
        self.assertEqual(serializer.is_valid(), False)
        self.assertEqual(serializer.errors, {'content': ['Ensure this value has at most 1000 characters (it has 1001).']})

    def test_update_missing_field(self):
        data = {
            'content': 'xxx',
            'created': datetime.datetime(2012, 1, 1)
        }
        serializer = CommentSerializer(self.comment, data=data)
        self.assertEqual(serializer.is_valid(), False)
        self.assertEqual(serializer.errors, {'email': ['This field is required.']})

    def test_missing_bool_with_default(self):
        """Make sure that a boolean value with a 'False' value is not
        mistaken for not having a default."""
        data = {
            'title': 'Some action item',
            #No 'done' value.
        }
        serializer = ActionItemSerializer(self.actionitem, data=data)
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(serializer.errors, {})

    def test_cross_field_validation(self):

        class CommentSerializerWithCrossFieldValidator(CommentSerializer):

            def validate(self, attrs):
                if attrs["email"] not in attrs["content"]:
                    raise serializers.ValidationError("Email address not in content")
                return attrs

        data = {
            'email': 'tom@example.com',
            'content': 'A comment from tom@example.com',
            'created': datetime.datetime(2012, 1, 1)
        }

        serializer = CommentSerializerWithCrossFieldValidator(data=data)
        self.assertTrue(serializer.is_valid())

        data['content'] = 'A comment from foo@bar.com'

        serializer = CommentSerializerWithCrossFieldValidator(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {'non_field_errors': ['Email address not in content']})

    def test_null_is_true_fields(self):
        """
        Omitting a value for null-field should validate.
        """
        serializer = PersonSerializer(data={'name': 'marko'})
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(serializer.errors, {})

    def test_modelserializer_max_length_exceeded(self):
        data = {
            'title': 'x' * 201,
        }
        serializer = ActionItemSerializer(data=data)
        self.assertEqual(serializer.is_valid(), False)
        self.assertEqual(serializer.errors, {'title': ['Ensure this value has at most 200 characters (it has 201).']})

    def test_modelserializer_max_length_exceeded_with_custom_restore(self):
        """
        When overriding ModelSerializer.restore_object, validation tests should still apply.
        Regression test for #623.

        https://github.com/tomchristie/django-rest-framework/pull/623
        """
        data = {
            'title': 'x' * 201,
        }
        serializer = ActionItemSerializerCustomRestore(data=data)
        self.assertEqual(serializer.is_valid(), False)
        self.assertEqual(serializer.errors, {'title': ['Ensure this value has at most 200 characters (it has 201).']})

    def test_default_modelfield_max_length_exceeded(self):
        data = {
            'title': 'Testing "info" field...',
            'info': 'x' * 13,
        }
        serializer = ActionItemSerializer(data=data)
        self.assertEqual(serializer.is_valid(), False)
        self.assertEqual(serializer.errors, {'info': ['Ensure this value has at most 12 characters (it has 13).']})

    def test_datetime_validation_failure(self):
        """
        Test DateTimeField validation errors on non-str values.
        Regression test for #669.

        https://github.com/tomchristie/django-rest-framework/issues/669
        """
        data = self.data
        data['created'] = 0

        serializer = CommentSerializer(data=data)
        self.assertEqual(serializer.is_valid(), False)

        self.assertIn('created', serializer.errors)

    def test_missing_model_field_exception_msg(self):
        """
        Assert that a meaningful exception message is outputted when the model
        field is missing (e.g. when mistyping ``model``).
        """
        class BrokenModelSerializer(serializers.ModelSerializer):
            class Meta:
                fields = ['some_field']

        try:
            BrokenModelSerializer()
        except AssertionError as e:
            self.assertEqual(e.args[0], "Serializer class 'BrokenModelSerializer' is missing 'model' Meta option")
        except:
            self.fail('Wrong exception type thrown.')

    def test_writable_star_source_on_nested_serializer(self):
        """
        Assert that a nested serializer instantiated with source='*' correctly
        expands the data into the outer serializer.
        """
        serializer = ModelSerializerWithNestedSerializer(data={
            'name': 'marko',
            'nested': {'info': 'hi'}},
        )
        self.assertEqual(serializer.is_valid(), True)

    def test_writable_star_source_on_nested_serializer_with_parent_object(self):
        class TitleSerializer(serializers.Serializer):
            title = serializers.WritableField(source='title')

        class AlbumSerializer(serializers.ModelSerializer):
            nested = TitleSerializer(source='*')

            class Meta:
                model = Album
                fields = ('nested',)

        class PhotoSerializer(serializers.ModelSerializer):
            album = AlbumSerializer(source='album')

            class Meta:
                model = Photo
                fields = ('album', )

        photo = Photo(album=Album())

        data = {'album': {'nested': {'title': 'test'}}}

        serializer = PhotoSerializer(photo, data=data)
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(serializer.data, data)

    def test_writable_star_source_with_inner_source_fields(self):
        """
        Tests that a serializer with source="*" correctly expands the
        it's fields into the outer serializer even if they have their
        own 'source' parameters.
        """

        serializer = ModelSerializerWithNestedSerializerWithRenamedField(data={
            'name': 'marko',
            'nested': {'renamed_info': 'hi'}},
        )
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(serializer.errors, {})


class CustomValidationTests(TestCase):
    class CommentSerializerWithFieldValidator(CommentSerializer):

        def validate_email(self, attrs, source):
            attrs[source]
            return attrs

        def validate_content(self, attrs, source):
            value = attrs[source]
            if "test" not in value:
                raise serializers.ValidationError("Test not in value")
            return attrs

    def test_field_validation(self):
        data = {
            'email': 'tom@example.com',
            'content': 'A test comment',
            'created': datetime.datetime(2012, 1, 1)
        }

        serializer = self.CommentSerializerWithFieldValidator(data=data)
        self.assertTrue(serializer.is_valid())

        data['content'] = 'This should not validate'

        serializer = self.CommentSerializerWithFieldValidator(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {'content': ['Test not in value']})

    def test_missing_data(self):
        """
        Make sure that validate_content isn't called if the field is missing
        """
        incomplete_data = {
            'email': 'tom@example.com',
            'created': datetime.datetime(2012, 1, 1)
        }
        serializer = self.CommentSerializerWithFieldValidator(data=incomplete_data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {'content': ['This field is required.']})

    def test_wrong_data(self):
        """
        Make sure that validate_content isn't called if the field input is wrong
        """
        wrong_data = {
            'email': 'not an email',
            'content': 'A test comment',
            'created': datetime.datetime(2012, 1, 1)
        }
        serializer = self.CommentSerializerWithFieldValidator(data=wrong_data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {'email': ['Enter a valid email address.']})

    def test_partial_update(self):
        """
        Make sure that validate_email isn't called when partial=True and email
        isn't found in data.
        """
        initial_data = {
            'email': 'tom@example.com',
            'content': 'A test comment',
            'created': datetime.datetime(2012, 1, 1)
        }

        serializer = self.CommentSerializerWithFieldValidator(data=initial_data)
        self.assertEqual(serializer.is_valid(), True)
        instance = serializer.object

        new_content = 'An *updated* test comment'
        partial_data = {
            'content': new_content
        }

        serializer = self.CommentSerializerWithFieldValidator(instance=instance,
                                                              data=partial_data,
                                                              partial=True)
        self.assertEqual(serializer.is_valid(), True)
        instance = serializer.object
        self.assertEqual(instance.content, new_content)


class PositiveIntegerAsChoiceTests(TestCase):
    def test_positive_integer_in_json_is_correctly_parsed(self):
        data = {'some_integer': 1}
        serializer = PositiveIntegerAsChoiceSerializer(data=data)
        self.assertEqual(serializer.is_valid(), True)


class ModelValidationTests(TestCase):
    def test_validate_unique(self):
        """
        Just check if serializers.ModelSerializer handles unique checks via .full_clean()
        """
        serializer = AlbumsSerializer(data={'title': 'a', 'ref': '1'})
        serializer.is_valid()
        serializer.save()
        second_serializer = AlbumsSerializer(data={'title': 'a'})
        self.assertFalse(second_serializer.is_valid())
        self.assertEqual(second_serializer.errors,  {'title': ['Album with this Title already exists.'],})
        third_serializer = AlbumsSerializer(data=[{'title': 'b', 'ref': '1'}, {'title': 'c'}])
        self.assertFalse(third_serializer.is_valid())
        self.assertEqual(third_serializer.errors,  [{'ref': ['Album with this Ref already exists.']}, {}])

    def test_foreign_key_is_null_with_partial(self):
        """
        Test ModelSerializer validation with partial=True

        Specifically test that a null foreign key does not pass validation
        """
        album = Album(title='test')
        album.save()

        class PhotoSerializer(serializers.ModelSerializer):
            class Meta:
                model = Photo

        photo_serializer = PhotoSerializer(data={'description': 'test', 'album': album.pk})
        self.assertTrue(photo_serializer.is_valid())
        photo = photo_serializer.save()

        # Updating only the album (foreign key)
        photo_serializer = PhotoSerializer(instance=photo, data={'album': ''}, partial=True)
        self.assertFalse(photo_serializer.is_valid())
        self.assertTrue('album' in photo_serializer.errors)
        self.assertEqual(photo_serializer.errors['album'], photo_serializer.error_messages['required'])

    def test_foreign_key_with_partial(self):
        """
        Test ModelSerializer validation with partial=True

        Specifically test foreign key validation.
        """

        album = Album(title='test')
        album.save()

        class PhotoSerializer(serializers.ModelSerializer):
            class Meta:
                model = Photo

        photo_serializer = PhotoSerializer(data={'description': 'test', 'album': album.pk})
        self.assertTrue(photo_serializer.is_valid())
        photo = photo_serializer.save()

        # Updating only the album (foreign key)
        photo_serializer = PhotoSerializer(instance=photo, data={'album': album.pk}, partial=True)
        self.assertTrue(photo_serializer.is_valid())
        self.assertTrue(photo_serializer.save())

        # Updating only the description
        photo_serializer = PhotoSerializer(instance=photo,
                                           data={'description': 'new'},
                                           partial=True)

        self.assertTrue(photo_serializer.is_valid())
        self.assertTrue(photo_serializer.save())


class RegexValidationTest(TestCase):
    def test_create_failed(self):
        serializer = BookSerializer(data={'isbn': '1234567890'})
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {'isbn': ['isbn has to be exact 13 numbers']})

        serializer = BookSerializer(data={'isbn': '12345678901234'})
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {'isbn': ['isbn has to be exact 13 numbers']})

        serializer = BookSerializer(data={'isbn': 'abcdefghijklm'})
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {'isbn': ['isbn has to be exact 13 numbers']})

    def test_create_success(self):
        serializer = BookSerializer(data={'isbn': '1234567890123'})
        self.assertTrue(serializer.is_valid())


class MetadataTests(TestCase):
    def test_empty(self):
        serializer = CommentSerializer()
        expected = {
            'email': serializers.CharField,
            'content': serializers.CharField,
            'created': serializers.DateTimeField
        }
        for field_name, field in expected.items():
            self.assertTrue(isinstance(serializer.data.fields[field_name], field))


class ManyToManyTests(TestCase):
    def setUp(self):
        class ManyToManySerializer(serializers.ModelSerializer):
            class Meta:
                model = ManyToManyModel

        self.serializer_class = ManyToManySerializer

        # An anchor instance to use for the relationship
        self.anchor = Anchor()
        self.anchor.save()

        # A model instance with a many to many relationship to the anchor
        self.instance = ManyToManyModel()
        self.instance.save()
        self.instance.rel.add(self.anchor)

        # A serialized representation of the model instance
        self.data = {'id': 1, 'rel': [self.anchor.id]}

    def test_retrieve(self):
        """
        Serialize an instance of a model with a ManyToMany relationship.
        """
        serializer = self.serializer_class(instance=self.instance)
        expected = self.data
        self.assertEqual(serializer.data, expected)

    def test_create(self):
        """
        Create an instance of a model with a ManyToMany relationship.
        """
        data = {'rel': [self.anchor.id]}
        serializer = self.serializer_class(data=data)
        self.assertEqual(serializer.is_valid(), True)
        instance = serializer.save()
        self.assertEqual(len(ManyToManyModel.objects.all()), 2)
        self.assertEqual(instance.pk, 2)
        self.assertEqual(list(instance.rel.all()), [self.anchor])

    def test_update(self):
        """
        Update an instance of a model with a ManyToMany relationship.
        """
        new_anchor = Anchor()
        new_anchor.save()
        data = {'rel': [self.anchor.id, new_anchor.id]}
        serializer = self.serializer_class(self.instance, data=data)
        self.assertEqual(serializer.is_valid(), True)
        instance = serializer.save()
        self.assertEqual(len(ManyToManyModel.objects.all()), 1)
        self.assertEqual(instance.pk, 1)
        self.assertEqual(list(instance.rel.all()), [self.anchor, new_anchor])

    def test_create_empty_relationship(self):
        """
        Create an instance of a model with a ManyToMany relationship,
        containing no items.
        """
        data = {'rel': []}
        serializer = self.serializer_class(data=data)
        self.assertEqual(serializer.is_valid(), True)
        instance = serializer.save()
        self.assertEqual(len(ManyToManyModel.objects.all()), 2)
        self.assertEqual(instance.pk, 2)
        self.assertEqual(list(instance.rel.all()), [])

    def test_update_empty_relationship(self):
        """
        Update an instance of a model with a ManyToMany relationship,
        containing no items.
        """
        new_anchor = Anchor()
        new_anchor.save()
        data = {'rel': []}
        serializer = self.serializer_class(self.instance, data=data)
        self.assertEqual(serializer.is_valid(), True)
        instance = serializer.save()
        self.assertEqual(len(ManyToManyModel.objects.all()), 1)
        self.assertEqual(instance.pk, 1)
        self.assertEqual(list(instance.rel.all()), [])

    def test_create_empty_relationship_flat_data(self):
        """
        Create an instance of a model with a ManyToMany relationship,
        containing no items, using a representation that does not support
        lists (eg form data).
        """
        data = MultiValueDict()
        data.setlist('rel', [''])
        serializer = self.serializer_class(data=data)
        self.assertEqual(serializer.is_valid(), True)
        instance = serializer.save()
        self.assertEqual(len(ManyToManyModel.objects.all()), 2)
        self.assertEqual(instance.pk, 2)
        self.assertEqual(list(instance.rel.all()), [])


class ReadOnlyManyToManyTests(TestCase):
    def setUp(self):
        class ReadOnlyManyToManySerializer(serializers.ModelSerializer):
            rel = serializers.RelatedField(many=True, read_only=True)

            class Meta:
                model = ReadOnlyManyToManyModel

        self.serializer_class = ReadOnlyManyToManySerializer

        # An anchor instance to use for the relationship
        self.anchor = Anchor()
        self.anchor.save()

        # A model instance with a many to many relationship to the anchor
        self.instance = ReadOnlyManyToManyModel()
        self.instance.save()
        self.instance.rel.add(self.anchor)

        # A serialized representation of the model instance
        self.data = {'rel': [self.anchor.id], 'id': 1, 'text': 'anchor'}

    def test_update(self):
        """
        Attempt to update an instance of a model with a ManyToMany
        relationship.  Not updated due to read_only=True
        """
        new_anchor = Anchor()
        new_anchor.save()
        data = {'rel': [self.anchor.id, new_anchor.id]}
        serializer = self.serializer_class(self.instance, data=data)
        self.assertEqual(serializer.is_valid(), True)
        instance = serializer.save()
        self.assertEqual(len(ReadOnlyManyToManyModel.objects.all()), 1)
        self.assertEqual(instance.pk, 1)
        # rel is still as original (1 entry)
        self.assertEqual(list(instance.rel.all()), [self.anchor])

    def test_update_without_relationship(self):
        """
        Attempt to update an instance of a model where many to ManyToMany
        relationship is not supplied.  Not updated due to read_only=True
        """
        new_anchor = Anchor()
        new_anchor.save()
        data = {}
        serializer = self.serializer_class(self.instance, data=data)
        self.assertEqual(serializer.is_valid(), True)
        instance = serializer.save()
        self.assertEqual(len(ReadOnlyManyToManyModel.objects.all()), 1)
        self.assertEqual(instance.pk, 1)
        # rel is still as original (1 entry)
        self.assertEqual(list(instance.rel.all()), [self.anchor])


class DefaultValueTests(TestCase):
    def setUp(self):
        class DefaultValueSerializer(serializers.ModelSerializer):
            class Meta:
                model = DefaultValueModel

        self.serializer_class = DefaultValueSerializer
        self.objects = DefaultValueModel.objects

    def test_create_using_default(self):
        data = {}
        serializer = self.serializer_class(data=data)
        self.assertEqual(serializer.is_valid(), True)
        instance = serializer.save()
        self.assertEqual(len(self.objects.all()), 1)
        self.assertEqual(instance.pk, 1)
        self.assertEqual(instance.text, 'foobar')

    def test_create_overriding_default(self):
        data = {'text': 'overridden'}
        serializer = self.serializer_class(data=data)
        self.assertEqual(serializer.is_valid(), True)
        instance = serializer.save()
        self.assertEqual(len(self.objects.all()), 1)
        self.assertEqual(instance.pk, 1)
        self.assertEqual(instance.text, 'overridden')

    def test_partial_update_default(self):
        """ Regression test for issue #532 """
        data = {'text': 'overridden'}
        serializer = self.serializer_class(data=data, partial=True)
        self.assertEqual(serializer.is_valid(), True)
        instance = serializer.save()

        data = {'extra': 'extra_value'}
        serializer = self.serializer_class(instance=instance, data=data, partial=True)
        self.assertEqual(serializer.is_valid(), True)
        instance = serializer.save()

        self.assertEqual(instance.extra, 'extra_value')
        self.assertEqual(instance.text, 'overridden')


class WritableFieldDefaultValueTests(TestCase):

    def setUp(self):
        self.expected = {'default': 'value'}
        self.create_field = fields.WritableField

    def test_get_default_value_with_noncallable(self):
        field = self.create_field(default=self.expected)
        got = field.get_default_value()
        self.assertEqual(got, self.expected)

    def test_get_default_value_with_callable(self):
        field = self.create_field(default=lambda : self.expected)
        got = field.get_default_value()
        self.assertEqual(got, self.expected)

    def test_get_default_value_when_not_required(self):
        field = self.create_field(default=self.expected, required=False)
        got = field.get_default_value()
        self.assertEqual(got, self.expected)

    def test_get_default_value_returns_None(self):
        field = self.create_field()
        got = field.get_default_value()
        self.assertIsNone(got)

    def test_get_default_value_returns_non_True_values(self):
        values = [None, '', False, 0, [], (), {}] # values that assumed as 'False' in the 'if' clause
        for expected in values:
            field = self.create_field(default=expected)
            got = field.get_default_value()
            self.assertEqual(got, expected)


class RelatedFieldDefaultValueTests(WritableFieldDefaultValueTests):

    def setUp(self):
        self.expected = {'foo': 'bar'}
        self.create_field = relations.RelatedField

    def test_get_default_value_returns_empty_list(self):
        field = self.create_field(many=True)
        got = field.get_default_value()
        self.assertListEqual(got, [])

    def test_get_default_value_returns_expected(self):
        expected = [1, 2, 3]
        field = self.create_field(many=True, default=expected)
        got = field.get_default_value()
        self.assertListEqual(got, expected)


class CallableDefaultValueTests(TestCase):
    def setUp(self):
        class CallableDefaultValueSerializer(serializers.ModelSerializer):
            class Meta:
                model = CallableDefaultValueModel

        self.serializer_class = CallableDefaultValueSerializer
        self.objects = CallableDefaultValueModel.objects

    def test_create_using_default(self):
        data = {}
        serializer = self.serializer_class(data=data)
        self.assertEqual(serializer.is_valid(), True)
        instance = serializer.save()
        self.assertEqual(len(self.objects.all()), 1)
        self.assertEqual(instance.pk, 1)
        self.assertEqual(instance.text, 'foobar')

    def test_create_overriding_default(self):
        data = {'text': 'overridden'}
        serializer = self.serializer_class(data=data)
        self.assertEqual(serializer.is_valid(), True)
        instance = serializer.save()
        self.assertEqual(len(self.objects.all()), 1)
        self.assertEqual(instance.pk, 1)
        self.assertEqual(instance.text, 'overridden')


class ManyRelatedTests(TestCase):
    def test_reverse_relations(self):
        post = BlogPost.objects.create(title="Test blog post")
        post.blogpostcomment_set.create(text="I hate this blog post")
        post.blogpostcomment_set.create(text="I love this blog post")

        class BlogPostCommentSerializer(serializers.Serializer):
            text = serializers.CharField()

        class BlogPostSerializer(serializers.Serializer):
            title = serializers.CharField()
            comments = BlogPostCommentSerializer(source='blogpostcomment_set')

        serializer = BlogPostSerializer(instance=post)
        expected = {
            'title': 'Test blog post',
            'comments': [
                {'text': 'I hate this blog post'},
                {'text': 'I love this blog post'}
            ]
        }

        self.assertEqual(serializer.data, expected)

    def test_include_reverse_relations(self):
        post = BlogPost.objects.create(title="Test blog post")
        post.blogpostcomment_set.create(text="I hate this blog post")
        post.blogpostcomment_set.create(text="I love this blog post")

        class BlogPostSerializer(serializers.ModelSerializer):
            class Meta:
                model = BlogPost
                fields = ('id', 'title', 'blogpostcomment_set')

        serializer = BlogPostSerializer(instance=post)
        expected = {
            'id': 1, 'title': 'Test blog post', 'blogpostcomment_set': [1, 2]
        }
        self.assertEqual(serializer.data, expected)

    def test_depth_include_reverse_relations(self):
        post = BlogPost.objects.create(title="Test blog post")
        post.blogpostcomment_set.create(text="I hate this blog post")
        post.blogpostcomment_set.create(text="I love this blog post")

        class BlogPostSerializer(serializers.ModelSerializer):
            class Meta:
                model = BlogPost
                fields = ('id', 'title', 'blogpostcomment_set')
                depth = 1

        serializer = BlogPostSerializer(instance=post)
        expected = {
            'id': 1, 'title': 'Test blog post',
            'blogpostcomment_set': [
                {'id': 1, 'text': 'I hate this blog post', 'blog_post': 1},
                {'id': 2, 'text': 'I love this blog post', 'blog_post': 1}
            ]
        }
        self.assertEqual(serializer.data, expected)

    def test_callable_source(self):
        post = BlogPost.objects.create(title="Test blog post")
        post.blogpostcomment_set.create(text="I love this blog post")

        class BlogPostCommentSerializer(serializers.Serializer):
            text = serializers.CharField()

        class BlogPostSerializer(serializers.Serializer):
            title = serializers.CharField()
            first_comment = BlogPostCommentSerializer(source='get_first_comment')

        serializer = BlogPostSerializer(post)

        expected = {
            'title': 'Test blog post',
            'first_comment': {'text': 'I love this blog post'}
        }
        self.assertEqual(serializer.data, expected)


class RelatedTraversalTest(TestCase):
    def test_nested_traversal(self):
        """
        Source argument should support dotted.source notation.
        """
        user = Person.objects.create(name="django")
        post = BlogPost.objects.create(title="Test blog post", writer=user)
        post.blogpostcomment_set.create(text="I love this blog post")

        class PersonSerializer(serializers.ModelSerializer):
            class Meta:
                model = Person
                fields = ("name", "age")

        class BlogPostCommentSerializer(serializers.ModelSerializer):
            class Meta:
                model = BlogPostComment
                fields = ("text", "post_owner")

            text = serializers.CharField()
            post_owner = PersonSerializer(source='blog_post.writer')

        class BlogPostSerializer(serializers.Serializer):
            title = serializers.CharField()
            comments = BlogPostCommentSerializer(source='blogpostcomment_set')

        serializer = BlogPostSerializer(instance=post)

        expected = {
            'title': 'Test blog post',
            'comments': [{
                'text': 'I love this blog post',
                'post_owner': {
                    "name": "django",
                    "age": None
                }
            }]
        }

        self.assertEqual(serializer.data, expected)

    def test_nested_traversal_with_none(self):
        """
        If a component of the dotted.source is None, return None for the field.
        """
        from rest_framework.tests.models import NullableForeignKeySource
        instance = NullableForeignKeySource.objects.create(name='Source with null FK')

        class NullableSourceSerializer(serializers.Serializer):
            target_name = serializers.Field(source='target.name')

        serializer = NullableSourceSerializer(instance=instance)

        expected = {
            'target_name': None,
        }

        self.assertEqual(serializer.data, expected)


class SerializerMethodFieldTests(TestCase):
    def setUp(self):

        class BoopSerializer(serializers.Serializer):
            beep = serializers.SerializerMethodField('get_beep')
            boop = serializers.Field()
            boop_count = serializers.SerializerMethodField('get_boop_count')

            def get_beep(self, obj):
                return 'hello!'

            def get_boop_count(self, obj):
                return len(obj.boop)

        self.serializer_class = BoopSerializer

    def test_serializer_method_field(self):

        class MyModel(object):
            boop = ['a', 'b', 'c']

        source_data = MyModel()

        serializer = self.serializer_class(source_data)

        expected = {
            'beep': 'hello!',
            'boop': ['a', 'b', 'c'],
            'boop_count': 3,
        }

        self.assertEqual(serializer.data, expected)


# Test for issue #324
class BlankFieldTests(TestCase):
    def setUp(self):

        class BlankFieldModelSerializer(serializers.ModelSerializer):
            class Meta:
                model = BlankFieldModel

        class BlankFieldSerializer(serializers.Serializer):
            title = serializers.CharField(required=False)

        class NotBlankFieldModelSerializer(serializers.ModelSerializer):
            class Meta:
                model = BasicModel

        class NotBlankFieldSerializer(serializers.Serializer):
            title = serializers.CharField()

        self.model_serializer_class = BlankFieldModelSerializer
        self.serializer_class = BlankFieldSerializer
        self.not_blank_model_serializer_class = NotBlankFieldModelSerializer
        self.not_blank_serializer_class = NotBlankFieldSerializer
        self.data = {'title': ''}

    def test_create_blank_field(self):
        serializer = self.serializer_class(data=self.data)
        self.assertEqual(serializer.is_valid(), True)

    def test_create_model_blank_field(self):
        serializer = self.model_serializer_class(data=self.data)
        self.assertEqual(serializer.is_valid(), True)

    def test_create_model_null_field(self):
        serializer = self.model_serializer_class(data={'title': None})
        self.assertEqual(serializer.is_valid(), True)

    def test_create_not_blank_field(self):
        """
        Test to ensure blank data in a field not marked as blank=True
        is considered invalid in a non-model serializer
        """
        serializer = self.not_blank_serializer_class(data=self.data)
        self.assertEqual(serializer.is_valid(), False)

    def test_create_model_not_blank_field(self):
        """
        Test to ensure blank data in a field not marked as blank=True
        is considered invalid in a model serializer
        """
        serializer = self.not_blank_model_serializer_class(data=self.data)
        self.assertEqual(serializer.is_valid(), False)

    def test_create_model_empty_field(self):
        serializer = self.model_serializer_class(data={})
        self.assertEqual(serializer.is_valid(), True)


#test for issue #460
class SerializerPickleTests(TestCase):
    """
    Test pickleability of the output of Serializers
    """
    def test_pickle_simple_model_serializer_data(self):
        """
        Test simple serializer
        """
        pickle.dumps(PersonSerializer(Person(name="Methusela", age=969)).data)

    def test_pickle_inner_serializer(self):
        """
        Test pickling a serializer whose resulting .data (a SortedDictWithMetadata) will
        have unpickleable meta data--in order to make sure metadata doesn't get pulled into the pickle.
        See DictWithMetadata.__getstate__
        """
        class InnerPersonSerializer(serializers.ModelSerializer):
            class Meta:
                model = Person
                fields = ('name', 'age')
        pickle.dumps(InnerPersonSerializer(Person(name="Noah", age=950)).data, 0)

    def test_getstate_method_should_not_return_none(self):
        """
        Regression test for #645.
        """
        data = serializers.DictWithMetadata({1: 1})
        self.assertEqual(data.__getstate__(), serializers.SortedDict({1: 1}))

    def test_serializer_data_is_pickleable(self):
        """
        Another regression test for #645.
        """
        data = serializers.SortedDictWithMetadata({1: 1})
        repr(pickle.loads(pickle.dumps(data, 0)))


# test for issue #725
class SeveralChoicesModel(models.Model):
    color = models.CharField(
        max_length=10,
        choices=[('red', 'Red'), ('green', 'Green'), ('blue', 'Blue')],
        blank=False
    )
    drink = models.CharField(
        max_length=10,
        choices=[('beer', 'Beer'), ('wine', 'Wine'), ('cider', 'Cider')],
        blank=False,
        default='beer'
    )
    os = models.CharField(
        max_length=10,
        choices=[('linux', 'Linux'), ('osx', 'OSX'), ('windows', 'Windows')],
        blank=True
    )
    music_genre = models.CharField(
        max_length=10,
        choices=[('rock', 'Rock'), ('metal', 'Metal'), ('grunge', 'Grunge')],
        blank=True,
        default='metal'
    )


class SerializerChoiceFields(TestCase):

    def setUp(self):
        super(SerializerChoiceFields, self).setUp()

        class SeveralChoicesSerializer(serializers.ModelSerializer):
            class Meta:
                model = SeveralChoicesModel
                fields = ('color', 'drink', 'os', 'music_genre')

        self.several_choices_serializer = SeveralChoicesSerializer

    def test_choices_blank_false_not_default(self):
        serializer = self.several_choices_serializer()
        self.assertEqual(
            serializer.fields['color'].choices,
            [('red', 'Red'), ('green', 'Green'), ('blue', 'Blue')]
        )

    def test_choices_blank_false_with_default(self):
        serializer = self.several_choices_serializer()
        self.assertEqual(
            serializer.fields['drink'].choices,
            [('beer', 'Beer'), ('wine', 'Wine'), ('cider', 'Cider')]
        )

    def test_choices_blank_true_not_default(self):
        serializer = self.several_choices_serializer()
        self.assertEqual(
            serializer.fields['os'].choices,
            BLANK_CHOICE_DASH + [('linux', 'Linux'), ('osx', 'OSX'), ('windows', 'Windows')]
        )

    def test_choices_blank_true_with_default(self):
        serializer = self.several_choices_serializer()
        self.assertEqual(
            serializer.fields['music_genre'].choices,
            BLANK_CHOICE_DASH + [('rock', 'Rock'), ('metal', 'Metal'), ('grunge', 'Grunge')]
        )


# Regression tests for #675
class Ticket(models.Model):
    assigned = models.ForeignKey(
        Person, related_name='assigned_tickets')
    reviewer = models.ForeignKey(
        Person, blank=True, null=True, related_name='reviewed_tickets')


class SerializerRelatedChoicesTest(TestCase):

    def setUp(self):
        super(SerializerRelatedChoicesTest, self).setUp()

        class RelatedChoicesSerializer(serializers.ModelSerializer):
            class Meta:
                model = Ticket
                fields = ('assigned', 'reviewer')

        self.related_fields_serializer = RelatedChoicesSerializer

    def test_empty_queryset_required(self):
        serializer = self.related_fields_serializer()
        self.assertEqual(serializer.fields['assigned'].queryset.count(), 0)
        self.assertEqual(
            [x for x in serializer.fields['assigned'].widget.choices],
            []
        )

    def test_empty_queryset_not_required(self):
        serializer = self.related_fields_serializer()
        self.assertEqual(serializer.fields['reviewer'].queryset.count(), 0)
        self.assertEqual(
            [x for x in serializer.fields['reviewer'].widget.choices],
            [('', '---------')]
        )

    def test_with_some_persons_required(self):
        Person.objects.create(name="Lionel Messi")
        Person.objects.create(name="Xavi Hernandez")
        serializer = self.related_fields_serializer()
        self.assertEqual(serializer.fields['assigned'].queryset.count(), 2)
        self.assertEqual(
            [x for x in serializer.fields['assigned'].widget.choices],
            [(1, 'Person object - 1'), (2, 'Person object - 2')]
        )

    def test_with_some_persons_not_required(self):
        Person.objects.create(name="Lionel Messi")
        Person.objects.create(name="Xavi Hernandez")
        serializer = self.related_fields_serializer()
        self.assertEqual(serializer.fields['reviewer'].queryset.count(), 2)
        self.assertEqual(
            [x for x in serializer.fields['reviewer'].widget.choices],
            [('', '---------'), (1, 'Person object - 1'), (2, 'Person object - 2')]
        )


class DepthTest(TestCase):
    def test_implicit_nesting(self):

        writer = Person.objects.create(name="django", age=1)
        post = BlogPost.objects.create(title="Test blog post", writer=writer)
        comment = BlogPostComment.objects.create(text="Test blog post comment", blog_post=post)

        class BlogPostCommentSerializer(serializers.ModelSerializer):
            class Meta:
                model = BlogPostComment
                depth = 2

        serializer = BlogPostCommentSerializer(instance=comment)
        expected = {'id': 1, 'text': 'Test blog post comment', 'blog_post': {'id': 1, 'title': 'Test blog post',
                    'writer': {'id': 1, 'name': 'django', 'age': 1}}}

        self.assertEqual(serializer.data, expected)

    def test_explicit_nesting(self):
        writer = Person.objects.create(name="django", age=1)
        post = BlogPost.objects.create(title="Test blog post", writer=writer)
        comment = BlogPostComment.objects.create(text="Test blog post comment", blog_post=post)

        class PersonSerializer(serializers.ModelSerializer):
            class Meta:
                model = Person

        class BlogPostSerializer(serializers.ModelSerializer):
            writer = PersonSerializer()

            class Meta:
                model = BlogPost

        class BlogPostCommentSerializer(serializers.ModelSerializer):
            blog_post = BlogPostSerializer()

            class Meta:
                model = BlogPostComment

        serializer = BlogPostCommentSerializer(instance=comment)
        expected = {'id': 1, 'text': 'Test blog post comment', 'blog_post': {'id': 1, 'title': 'Test blog post',
                    'writer': {'id': 1, 'name': 'django', 'age': 1}}}

        self.assertEqual(serializer.data, expected)


class NestedSerializerContextTests(TestCase):

    def test_nested_serializer_context(self):
        """
        Regression for #497

        https://github.com/tomchristie/django-rest-framework/issues/497
        """
        class PhotoSerializer(serializers.ModelSerializer):
            class Meta:
                model = Photo
                fields = ("description", "callable")

            callable = serializers.SerializerMethodField('_callable')

            def _callable(self, instance):
                if not 'context_item' in self.context:
                    raise RuntimeError("context isn't getting passed into 2nd level nested serializer")
                return "success"

        class AlbumSerializer(serializers.ModelSerializer):
            class Meta:
                model = Album
                fields = ("photo_set", "callable")

            photo_set = PhotoSerializer(source="photo_set")
            callable = serializers.SerializerMethodField("_callable")

            def _callable(self, instance):
                if not 'context_item' in self.context:
                    raise RuntimeError("context isn't getting passed into 1st level nested serializer")
                return "success"

        class AlbumCollection(object):
            albums = None

        class AlbumCollectionSerializer(serializers.Serializer):
            albums = AlbumSerializer(source="albums")

        album1 = Album.objects.create(title="album 1")
        album2 = Album.objects.create(title="album 2")
        Photo.objects.create(description="Bigfoot", album=album1)
        Photo.objects.create(description="Unicorn", album=album1)
        Photo.objects.create(description="Yeti", album=album2)
        Photo.objects.create(description="Sasquatch", album=album2)
        album_collection = AlbumCollection()
        album_collection.albums = [album1, album2]

        # This will raise RuntimeError if context doesn't get passed correctly to the nested Serializers
        AlbumCollectionSerializer(album_collection, context={'context_item': 'album context'}).data


class DeserializeListTestCase(TestCase):

    def setUp(self):
        self.data = {
            'email': 'nobody@nowhere.com',
            'content': 'This is some test content',
            'created': datetime.datetime(2013, 3, 7),
        }

    def test_no_errors(self):
        data = [self.data.copy() for x in range(0, 3)]
        serializer = CommentSerializer(data=data, many=True)
        self.assertTrue(serializer.is_valid())
        self.assertTrue(isinstance(serializer.object, list))
        self.assertTrue(
            all((isinstance(item, Comment) for item in serializer.object))
        )

    def test_errors_return_as_list(self):
        invalid_item = self.data.copy()
        invalid_item['email'] = ''
        data = [self.data.copy(), invalid_item, self.data.copy()]

        serializer = CommentSerializer(data=data, many=True)
        self.assertFalse(serializer.is_valid())
        expected = [{}, {'email': ['This field is required.']}, {}]
        self.assertEqual(serializer.errors, expected)


# Test for issue 747

class LazyStringModel(object):
    def __init__(self, lazystring):
        self.lazystring = lazystring


class LazyStringSerializer(serializers.Serializer):
    lazystring = serializers.Field()

    def restore_object(self, attrs, instance=None):
        if instance is not None:
            instance.lazystring = attrs.get('lazystring', instance.lazystring)
            return instance
        return LazyStringModel(**attrs)


class LazyStringsTestCase(TestCase):
    def setUp(self):
        self.model = LazyStringModel(lazystring=_('lazystring'))

    def test_lazy_strings_are_translated(self):
        serializer = LazyStringSerializer(self.model)
        self.assertEqual(type(serializer.data['lazystring']),
                         type('lazystring'))


# Test for issue #467

class FieldLabelTest(TestCase):
    def setUp(self):
        self.serializer_class = BasicModelSerializer

    def test_label_from_model(self):
        """
        Validates that label and help_text are correctly copied from the model class.
        """
        serializer = self.serializer_class()
        text_field = serializer.fields['text']

        self.assertEqual('Text comes here', text_field.label)
        self.assertEqual('Text description.', text_field.help_text)

    def test_field_ctor(self):
        """
        This is check that ctor supports both label and help_text.
        """
        self.assertEqual('Label', fields.Field(label='Label', help_text='Help').label)
        self.assertEqual('Help', fields.CharField(label='Label', help_text='Help').help_text)
        self.assertEqual('Label', relations.HyperlinkedRelatedField(view_name='fake', label='Label', help_text='Help', many=True).label)


# Test for issue #961

class ManyFieldHelpTextTest(TestCase):
    def test_help_text_no_hold_down_control_msg(self):
        """
        Validate that help_text doesn't contain the 'Hold down "Control" ...'
        message that Django appends to choice fields.
        """
        rel_field = fields.Field(help_text=ManyToManyModel._meta.get_field('rel').help_text)
        self.assertEqual('Some help text.', rel_field.help_text)


class AttributeMappingOnAutogeneratedRelatedFields(TestCase):

    def test_primary_key_related_field(self):
        serializer = ForeignKeySourceSerializer()
        self.assertEqual(serializer.fields['target'].help_text, 'Target')
        self.assertEqual(serializer.fields['target'].label, 'Target')

    def test_hyperlinked_related_field(self):
        serializer = HyperlinkedForeignKeySourceSerializer()
        self.assertEqual(serializer.fields['target'].help_text, 'Target')
        self.assertEqual(serializer.fields['target'].label, 'Target')


@unittest.skipUnless(PIL is not None, 'PIL is not installed')
class AttributeMappingOnAutogeneratedFieldsTests(TestCase):

    def setUp(self):

        class AMOAFSerializer(serializers.ModelSerializer):
            class Meta:
                model = AMOAFModel

        self.serializer_class = AMOAFSerializer
        self.fields_attributes = {
            'char_field': [
                ('max_length', 1024),
            ],
            'comma_separated_integer_field': [
                ('max_length', 1024),
            ],
            'decimal_field': [
                ('max_digits', 64),
                ('decimal_places', 32),
            ],
            'email_field': [
                ('max_length', 1024),
            ],
            'file_field': [
                ('max_length', 1024),
            ],
            'image_field': [
                ('max_length', 1024),
            ],
            'slug_field': [
                ('max_length', 1024),
            ],
            'url_field': [
                ('max_length', 1024),
            ],
        }

    def field_test(self, field):
        serializer = self.serializer_class(data={})
        self.assertEqual(serializer.is_valid(), True)

        for attribute in self.fields_attributes[field]:
            self.assertEqual(
                getattr(serializer.fields[field], attribute[0]),
                attribute[1]
            )

    def test_char_field(self):
        self.field_test('char_field')

    def test_comma_separated_integer_field(self):
        self.field_test('comma_separated_integer_field')

    def test_decimal_field(self):
        self.field_test('decimal_field')

    def test_email_field(self):
        self.field_test('email_field')

    def test_file_field(self):
        self.field_test('file_field')

    def test_image_field(self):
        self.field_test('image_field')

    def test_slug_field(self):
        self.field_test('slug_field')

    def test_url_field(self):
        self.field_test('url_field')


@unittest.skipUnless(PIL is not None, 'PIL is not installed')
class DefaultValuesOnAutogeneratedFieldsTests(TestCase):

    def setUp(self):

        class DVOAFSerializer(serializers.ModelSerializer):
            class Meta:
                model = DVOAFModel

        self.serializer_class = DVOAFSerializer
        self.fields_attributes = {
            'positive_integer_field': [
                ('min_value', 0),
            ],
            'positive_small_integer_field': [
                ('min_value', 0),
            ],
            'email_field': [
                ('max_length', 75),
            ],
            'file_field': [
                ('max_length', 100),
            ],
            'image_field': [
                ('max_length', 100),
            ],
            'slug_field': [
                ('max_length', 50),
            ],
            'url_field': [
                ('max_length', 200),
            ],
        }

    def field_test(self, field):
        serializer = self.serializer_class(data={})
        self.assertEqual(serializer.is_valid(), True)

        for attribute in self.fields_attributes[field]:
            self.assertEqual(
                getattr(serializer.fields[field], attribute[0]),
                attribute[1]
            )

    def test_positive_integer_field(self):
        self.field_test('positive_integer_field')

    def test_positive_small_integer_field(self):
        self.field_test('positive_small_integer_field')

    def test_email_field(self):
        self.field_test('email_field')

    def test_file_field(self):
        self.field_test('file_field')

    def test_image_field(self):
        self.field_test('image_field')

    def test_slug_field(self):
        self.field_test('slug_field')

    def test_url_field(self):
        self.field_test('url_field')


class MetadataSerializer(serializers.Serializer):
    field1 = serializers.CharField(3, required=True)
    field2 = serializers.CharField(10, required=False)


class MetadataSerializerTestCase(TestCase):
    def setUp(self):
        self.serializer = MetadataSerializer()

    def test_serializer_metadata(self):
        metadata = self.serializer.metadata()
        expected = {
            'field1': {
                'required': True,
                'max_length': 3,
                'type': 'string',
                'read_only': False
            },
            'field2': {
                'required': False,
                'max_length': 10,
                'type': 'string',
                'read_only': False
            }
        }
        self.assertEqual(expected, metadata)


### Regression test for #840

class SimpleModel(models.Model):
    text = models.CharField(max_length=100)


class SimpleModelSerializer(serializers.ModelSerializer):
    text = serializers.CharField()
    other = serializers.CharField()

    class Meta:
        model = SimpleModel

    def validate_other(self, attrs, source):
        del attrs['other']
        return attrs


class FieldValidationRemovingAttr(TestCase):
    def test_removing_non_model_field_in_validation(self):
        """
        Removing an attr during field valiation should ensure that it is not
        passed through when restoring the object.

        This allows additional non-model fields to be supported.

        Regression test for #840.
        """
        serializer = SimpleModelSerializer(data={'text': 'foo', 'other': 'bar'})
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertEqual(serializer.object.text, 'foo')


### Regression test for #878

class SimpleTargetModel(models.Model):
    text = models.CharField(max_length=100)


class SimplePKSourceModelSerializer(serializers.Serializer):
    targets = serializers.PrimaryKeyRelatedField(queryset=SimpleTargetModel.objects.all(), many=True)
    text = serializers.CharField()


class SimpleSlugSourceModelSerializer(serializers.Serializer):
    targets = serializers.SlugRelatedField(queryset=SimpleTargetModel.objects.all(), many=True, slug_field='pk')
    text = serializers.CharField()


class SerializerSupportsManyRelationships(TestCase):
    def setUp(self):
        SimpleTargetModel.objects.create(text='foo')
        SimpleTargetModel.objects.create(text='bar')

    def test_serializer_supports_pk_many_relationships(self):
        """
        Regression test for #878.

        Note that pk behavior has a different code path to usual cases,
        for performance reasons.
        """
        serializer = SimplePKSourceModelSerializer(data={'text': 'foo', 'targets': [1, 2]})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.data, {'text': 'foo', 'targets': [1, 2]})

    def test_serializer_supports_slug_many_relationships(self):
        """
        Regression test for #878.
        """
        serializer = SimpleSlugSourceModelSerializer(data={'text': 'foo', 'targets': [1, 2]})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.data, {'text': 'foo', 'targets': [1, 2]})


class TransformMethodsSerializer(serializers.Serializer):
    a = serializers.CharField()
    b_renamed = serializers.CharField(source='b')

    def transform_a(self, obj, value):
        return value.lower()

    def transform_b_renamed(self, obj, value):
        if value is not None:
            return 'and ' + value


class TestSerializerTransformMethods(TestCase):
    def setUp(self):
        self.s = TransformMethodsSerializer()

    def test_transform_methods(self):
        self.assertEqual(
            self.s.to_native({'a': 'GREEN EGGS', 'b': 'HAM'}),
            {
                'a': 'green eggs',
                'b_renamed': 'and HAM',
            }
        )

    def test_missing_fields(self):
        self.assertEqual(
            self.s.to_native({'a': 'GREEN EGGS'}),
            {
                'a': 'green eggs',
                'b_renamed': None,
            }
        )


class DefaultTrueBooleanModel(models.Model):
    cat = models.BooleanField(default=True)
    dog = models.BooleanField(default=False)


class SerializerDefaultTrueBoolean(TestCase):

    def setUp(self):
        super(SerializerDefaultTrueBoolean, self).setUp()

        class DefaultTrueBooleanSerializer(serializers.ModelSerializer):
            class Meta:
                model = DefaultTrueBooleanModel
                fields = ('cat', 'dog')

        self.default_true_boolean_serializer = DefaultTrueBooleanSerializer

    def test_enabled_as_false(self):
        serializer = self.default_true_boolean_serializer(data={'cat': False,
                                                                'dog': False})
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(serializer.data['cat'], False)
        self.assertEqual(serializer.data['dog'], False)

    def test_enabled_as_true(self):
        serializer = self.default_true_boolean_serializer(data={'cat': True,
                                                                'dog': True})
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(serializer.data['cat'], True)
        self.assertEqual(serializer.data['dog'], True)

    def test_enabled_partial(self):
        serializer = self.default_true_boolean_serializer(data={'cat': False},
                                                          partial=True)
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(serializer.data['cat'], False)
        self.assertEqual(serializer.data['dog'], False)


class BoolenFieldTypeTest(TestCase):
    '''
    Ensure the various Boolean based model fields are rendered as the proper
    field type

    '''

    def setUp(self):
        '''
        Setup an ActionItemSerializer for BooleanTesting
        '''
        data = {
            'title': 'b' * 201,
        }
        self.serializer = ActionItemSerializer(data=data)

    def test_booleanfield_type(self):
        '''
        Test that BooleanField is infered from models.BooleanField
        '''
        bfield = self.serializer.get_fields()['done']
        self.assertEqual(type(bfield), fields.BooleanField)

    def test_nullbooleanfield_type(self):
        '''
        Test that BooleanField is infered from models.NullBooleanField

        https://groups.google.com/forum/#!topic/django-rest-framework/D9mXEftpuQ8
        '''
        bfield = self.serializer.get_fields()['started']
        self.assertEqual(type(bfield), fields.BooleanField)

########NEW FILE########
__FILENAME__ = test_serializers
from django.db import models
from django.test import TestCase

from rest_framework.serializers import _resolve_model
from rest_framework.tests.models import BasicModel
from rest_framework.compat import six


class ResolveModelTests(TestCase):
    """
    `_resolve_model` should return a Django model class given the
    provided argument is a Django model class itself, or a properly
    formatted string representation of one.
    """
    def test_resolve_django_model(self):
        resolved_model = _resolve_model(BasicModel)
        self.assertEqual(resolved_model, BasicModel)

    def test_resolve_string_representation(self):
        resolved_model = _resolve_model('tests.BasicModel')
        self.assertEqual(resolved_model, BasicModel)

    def test_resolve_unicode_representation(self):
        resolved_model = _resolve_model(six.text_type('tests.BasicModel'))
        self.assertEqual(resolved_model, BasicModel)

    def test_resolve_non_django_model(self):
        with self.assertRaises(ValueError):
            _resolve_model(TestCase)

    def test_resolve_improper_string_representation(self):
        with self.assertRaises(ValueError):
            _resolve_model('BasicModel')

########NEW FILE########
__FILENAME__ = test_serializer_bulk_update
"""
Tests to cover bulk create and update using serializers.
"""
from __future__ import unicode_literals
from django.test import TestCase
from rest_framework import serializers


class BulkCreateSerializerTests(TestCase):
    """
    Creating multiple instances using serializers.
    """

    def setUp(self):
        class BookSerializer(serializers.Serializer):
            id = serializers.IntegerField()
            title = serializers.CharField(max_length=100)
            author = serializers.CharField(max_length=100)

        self.BookSerializer = BookSerializer

    def test_bulk_create_success(self):
        """
        Correct bulk update serialization should return the input data.
        """

        data = [
            {
                'id': 0,
                'title': 'The electric kool-aid acid test',
                'author': 'Tom Wolfe'
            }, {
                'id': 1,
                'title': 'If this is a man',
                'author': 'Primo Levi'
            }, {
                'id': 2,
                'title': 'The wind-up bird chronicle',
                'author': 'Haruki Murakami'
            }
        ]

        serializer = self.BookSerializer(data=data, many=True)
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(serializer.object, data)

    def test_bulk_create_errors(self):
        """
        Correct bulk update serialization should return the input data.
        """

        data = [
            {
                'id': 0,
                'title': 'The electric kool-aid acid test',
                'author': 'Tom Wolfe'
            }, {
                'id': 1,
                'title': 'If this is a man',
                'author': 'Primo Levi'
            }, {
                'id': 'foo',
                'title': 'The wind-up bird chronicle',
                'author': 'Haruki Murakami'
            }
        ]
        expected_errors = [
            {},
            {},
            {'id': ['Enter a whole number.']}
        ]

        serializer = self.BookSerializer(data=data, many=True)
        self.assertEqual(serializer.is_valid(), False)
        self.assertEqual(serializer.errors, expected_errors)

    def test_invalid_list_datatype(self):
        """
        Data containing list of incorrect data type should return errors.
        """
        data = ['foo', 'bar', 'baz']
        serializer = self.BookSerializer(data=data, many=True)
        self.assertEqual(serializer.is_valid(), False)

        expected_errors = [
                {'non_field_errors': ['Invalid data']},
                {'non_field_errors': ['Invalid data']},
                {'non_field_errors': ['Invalid data']}
        ]

        self.assertEqual(serializer.errors, expected_errors)

    def test_invalid_single_datatype(self):
        """
        Data containing a single incorrect data type should return errors.
        """
        data = 123
        serializer = self.BookSerializer(data=data, many=True)
        self.assertEqual(serializer.is_valid(), False)

        expected_errors = {'non_field_errors': ['Expected a list of items.']}

        self.assertEqual(serializer.errors, expected_errors)

    def test_invalid_single_object(self):
        """
        Data containing only a single object, instead of a list of objects
        should return errors.
        """
        data = {
            'id': 0,
            'title': 'The electric kool-aid acid test',
            'author': 'Tom Wolfe'
        }
        serializer = self.BookSerializer(data=data, many=True)
        self.assertEqual(serializer.is_valid(), False)

        expected_errors = {'non_field_errors': ['Expected a list of items.']}

        self.assertEqual(serializer.errors, expected_errors)


class BulkUpdateSerializerTests(TestCase):
    """
    Updating multiple instances using serializers.
    """

    def setUp(self):
        class Book(object):
            """
            A data type that can be persisted to a mock storage backend
            with `.save()` and `.delete()`.
            """
            object_map = {}

            def __init__(self, id, title, author):
                self.id = id
                self.title = title
                self.author = author

            def save(self):
                Book.object_map[self.id] = self

            def delete(self):
                del Book.object_map[self.id]

        class BookSerializer(serializers.Serializer):
            id = serializers.IntegerField()
            title = serializers.CharField(max_length=100)
            author = serializers.CharField(max_length=100)

            def restore_object(self, attrs, instance=None):
                if instance:
                    instance.id = attrs['id']
                    instance.title = attrs['title']
                    instance.author = attrs['author']
                    return instance
                return Book(**attrs)

        self.Book = Book
        self.BookSerializer = BookSerializer

        data = [
            {
                'id': 0,
                'title': 'The electric kool-aid acid test',
                'author': 'Tom Wolfe'
            }, {
                'id': 1,
                'title': 'If this is a man',
                'author': 'Primo Levi'
            }, {
                'id': 2,
                'title': 'The wind-up bird chronicle',
                'author': 'Haruki Murakami'
            }
        ]

        for item in data:
            book = Book(item['id'], item['title'], item['author'])
            book.save()

    def books(self):
        """
        Return all the objects in the mock storage backend.
        """
        return self.Book.object_map.values()

    def test_bulk_update_success(self):
        """
        Correct bulk update serialization should return the input data.
        """
        data = [
            {
                'id': 0,
                'title': 'The electric kool-aid acid test',
                'author': 'Tom Wolfe'
            }, {
                'id': 2,
                'title': 'Kafka on the shore',
                'author': 'Haruki Murakami'
            }
        ]
        serializer = self.BookSerializer(self.books(), data=data, many=True, allow_add_remove=True)
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(serializer.data, data)
        serializer.save()
        new_data = self.BookSerializer(self.books(), many=True).data

        self.assertEqual(data, new_data)

    def test_bulk_update_and_create(self):
        """
        Bulk update serialization may also include created items.
        """
        data = [
            {
                'id': 0,
                'title': 'The electric kool-aid acid test',
                'author': 'Tom Wolfe'
            }, {
                'id': 3,
                'title': 'Kafka on the shore',
                'author': 'Haruki Murakami'
            }
        ]
        serializer = self.BookSerializer(self.books(), data=data, many=True, allow_add_remove=True)
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(serializer.data, data)
        serializer.save()
        new_data = self.BookSerializer(self.books(), many=True).data
        self.assertEqual(data, new_data)

    def test_bulk_update_invalid_create(self):
        """
        Bulk update serialization without allow_add_remove may not create items.
        """
        data = [
            {
                'id': 0,
                'title': 'The electric kool-aid acid test',
                'author': 'Tom Wolfe'
            }, {
                'id': 3,
                'title': 'Kafka on the shore',
                'author': 'Haruki Murakami'
            }
        ]
        expected_errors = [
            {},
            {'non_field_errors': ['Cannot create a new item, only existing items may be updated.']}
        ]
        serializer = self.BookSerializer(self.books(), data=data, many=True)
        self.assertEqual(serializer.is_valid(), False)
        self.assertEqual(serializer.errors, expected_errors)

    def test_bulk_update_error(self):
        """
        Incorrect bulk update serialization should return error data.
        """
        data = [
            {
                'id': 0,
                'title': 'The electric kool-aid acid test',
                'author': 'Tom Wolfe'
            }, {
                'id': 'foo',
                'title': 'Kafka on the shore',
                'author': 'Haruki Murakami'
            }
        ]
        expected_errors = [
            {},
            {'id': ['Enter a whole number.']}
        ]
        serializer = self.BookSerializer(self.books(), data=data, many=True, allow_add_remove=True)
        self.assertEqual(serializer.is_valid(), False)
        self.assertEqual(serializer.errors, expected_errors)

########NEW FILE########
__FILENAME__ = test_serializer_empty
from django.test import TestCase
from rest_framework import serializers


class EmptySerializerTestCase(TestCase):
    def test_empty_serializer(self):
        class FooBarSerializer(serializers.Serializer):
            foo = serializers.IntegerField()
            bar = serializers.SerializerMethodField('get_bar')

            def get_bar(self, obj):
                return 'bar'

        serializer = FooBarSerializer()
        self.assertEquals(serializer.data, {'foo': 0})

########NEW FILE########
__FILENAME__ = test_serializer_import
from django.test import TestCase

from rest_framework import serializers
from rest_framework.tests.accounts.serializers import AccountSerializer


class ImportingModelSerializerTests(TestCase):
    """
    In some situations like, GH #1225, it is possible, especially in
    testing, to import a serializer who's related models have not yet
    been resolved by Django. `AccountSerializer` is an example of such
    a serializer (imported at the top of this file).
    """
    def test_import_model_serializer(self):
        """
        The serializer at the top of this file should have been
        imported successfully, and we should be able to instantiate it.
        """
        self.assertIsInstance(AccountSerializer(), serializers.ModelSerializer)

########NEW FILE########
__FILENAME__ = test_serializer_nested
"""
Tests to cover nested serializers.

Doesn't cover model serializers.
"""
from __future__ import unicode_literals
from django.test import TestCase
from rest_framework import serializers
from . import models


class WritableNestedSerializerBasicTests(TestCase):
    """
    Tests for deserializing nested entities.
    Basic tests that use serializers that simply restore to dicts.
    """

    def setUp(self):
        class TrackSerializer(serializers.Serializer):
            order = serializers.IntegerField()
            title = serializers.CharField(max_length=100)
            duration = serializers.IntegerField()

        class AlbumSerializer(serializers.Serializer):
            album_name = serializers.CharField(max_length=100)
            artist = serializers.CharField(max_length=100)
            tracks = TrackSerializer(many=True)

        self.AlbumSerializer = AlbumSerializer

    def test_nested_validation_success(self):
        """
        Correct nested serialization should return the input data.
        """

        data = {
            'album_name': 'Discovery',
            'artist': 'Daft Punk',
            'tracks': [
                {'order': 1, 'title': 'One More Time', 'duration': 235},
                {'order': 2, 'title': 'Aerodynamic', 'duration': 184},
                {'order': 3, 'title': 'Digital Love', 'duration': 239}
            ]
        }

        serializer = self.AlbumSerializer(data=data)
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(serializer.object, data)

    def test_nested_validation_error(self):
        """
        Incorrect nested serialization should return appropriate error data.
        """

        data = {
            'album_name': 'Discovery',
            'artist': 'Daft Punk',
            'tracks': [
                {'order': 1, 'title': 'One More Time', 'duration': 235},
                {'order': 2, 'title': 'Aerodynamic', 'duration': 184},
                {'order': 3, 'title': 'Digital Love', 'duration': 'foobar'}
            ]
        }
        expected_errors = {
            'tracks': [
                {},
                {},
                {'duration': ['Enter a whole number.']}
            ]
        }

        serializer = self.AlbumSerializer(data=data)
        self.assertEqual(serializer.is_valid(), False)
        self.assertEqual(serializer.errors, expected_errors)

    def test_many_nested_validation_error(self):
        """
        Incorrect nested serialization should return appropriate error data
        when multiple entities are being deserialized.
        """

        data = [
            {
                'album_name': 'Russian Red',
                'artist': 'I Love Your Glasses',
                'tracks': [
                    {'order': 1, 'title': 'Cigarettes', 'duration': 121},
                    {'order': 2, 'title': 'No Past Land', 'duration': 198},
                    {'order': 3, 'title': 'They Don\'t Believe', 'duration': 191}
                ]
            },
            {
                'album_name': 'Discovery',
                'artist': 'Daft Punk',
                'tracks': [
                    {'order': 1, 'title': 'One More Time', 'duration': 235},
                    {'order': 2, 'title': 'Aerodynamic', 'duration': 184},
                    {'order': 3, 'title': 'Digital Love', 'duration': 'foobar'}
                ]
            }
        ]
        expected_errors = [
            {},
            {
                'tracks': [
                    {},
                    {},
                    {'duration': ['Enter a whole number.']}
                ]
            }
        ]

        serializer = self.AlbumSerializer(data=data, many=True)
        self.assertEqual(serializer.is_valid(), False)
        self.assertEqual(serializer.errors, expected_errors)


class WritableNestedSerializerObjectTests(TestCase):
    """
    Tests for deserializing nested entities.
    These tests use serializers that restore to concrete objects.
    """

    def setUp(self):
        # Couple of concrete objects that we're going to deserialize into
        class Track(object):
            def __init__(self, order, title, duration):
                self.order, self.title, self.duration = order, title, duration

            def __eq__(self, other):
                return (
                    self.order == other.order and
                    self.title == other.title and
                    self.duration == other.duration
                )

        class Album(object):
            def __init__(self, album_name, artist, tracks):
                self.album_name, self.artist, self.tracks = album_name, artist, tracks

            def __eq__(self, other):
                return (
                    self.album_name == other.album_name and
                    self.artist == other.artist and
                    self.tracks == other.tracks
                )

        # And their corresponding serializers
        class TrackSerializer(serializers.Serializer):
            order = serializers.IntegerField()
            title = serializers.CharField(max_length=100)
            duration = serializers.IntegerField()

            def restore_object(self, attrs, instance=None):
                return Track(attrs['order'], attrs['title'], attrs['duration'])

        class AlbumSerializer(serializers.Serializer):
            album_name = serializers.CharField(max_length=100)
            artist = serializers.CharField(max_length=100)
            tracks = TrackSerializer(many=True)

            def restore_object(self, attrs, instance=None):
                return Album(attrs['album_name'], attrs['artist'], attrs['tracks'])

        self.Album, self.Track = Album, Track
        self.AlbumSerializer = AlbumSerializer

    def test_nested_validation_success(self):
        """
        Correct nested serialization should return a restored object
        that corresponds to the input data.
        """

        data = {
            'album_name': 'Discovery',
            'artist': 'Daft Punk',
            'tracks': [
                {'order': 1, 'title': 'One More Time', 'duration': 235},
                {'order': 2, 'title': 'Aerodynamic', 'duration': 184},
                {'order': 3, 'title': 'Digital Love', 'duration': 239}
            ]
        }
        expected_object = self.Album(
            album_name='Discovery',
            artist='Daft Punk',
            tracks=[
                self.Track(order=1, title='One More Time', duration=235),
                self.Track(order=2, title='Aerodynamic', duration=184),
                self.Track(order=3, title='Digital Love', duration=239),
            ]
        )

        serializer = self.AlbumSerializer(data=data)
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(serializer.object, expected_object)

    def test_many_nested_validation_success(self):
        """
        Correct nested serialization should return multiple restored objects
        that corresponds to the input data when multiple objects are
        being deserialized.
        """

        data = [
            {
                'album_name': 'Russian Red',
                'artist': 'I Love Your Glasses',
                'tracks': [
                    {'order': 1, 'title': 'Cigarettes', 'duration': 121},
                    {'order': 2, 'title': 'No Past Land', 'duration': 198},
                    {'order': 3, 'title': 'They Don\'t Believe', 'duration': 191}
                ]
            },
            {
                'album_name': 'Discovery',
                'artist': 'Daft Punk',
                'tracks': [
                    {'order': 1, 'title': 'One More Time', 'duration': 235},
                    {'order': 2, 'title': 'Aerodynamic', 'duration': 184},
                    {'order': 3, 'title': 'Digital Love', 'duration': 239}
                ]
            }
        ]
        expected_object = [
            self.Album(
                album_name='Russian Red',
                artist='I Love Your Glasses',
                tracks=[
                    self.Track(order=1, title='Cigarettes', duration=121),
                    self.Track(order=2, title='No Past Land', duration=198),
                    self.Track(order=3, title='They Don\'t Believe', duration=191),
                ]
            ),
            self.Album(
                album_name='Discovery',
                artist='Daft Punk',
                tracks=[
                    self.Track(order=1, title='One More Time', duration=235),
                    self.Track(order=2, title='Aerodynamic', duration=184),
                    self.Track(order=3, title='Digital Love', duration=239),
                ]
            )
        ]

        serializer = self.AlbumSerializer(data=data, many=True)
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(serializer.object, expected_object)


class ForeignKeyNestedSerializerUpdateTests(TestCase):
    def setUp(self):
        class Artist(object):
            def __init__(self, name):
                self.name = name

            def __eq__(self, other):
                return self.name == other.name

        class Album(object):
            def __init__(self, name, artist):
                self.name, self.artist = name, artist

            def __eq__(self, other):
                return self.name == other.name and self.artist == other.artist

        class ArtistSerializer(serializers.Serializer):
            name = serializers.CharField()

            def restore_object(self, attrs, instance=None):
                if instance:
                    instance.name = attrs['name']
                else:
                    instance = Artist(attrs['name'])
                return instance

        class AlbumSerializer(serializers.Serializer):
            name = serializers.CharField()
            by = ArtistSerializer(source='artist')

            def restore_object(self, attrs, instance=None):
                if instance:
                    instance.name = attrs['name']
                    instance.artist = attrs['artist']
                else:
                    instance = Album(attrs['name'], attrs['artist'])
                return instance

        self.Artist = Artist
        self.Album = Album
        self.AlbumSerializer = AlbumSerializer

    def test_create_via_foreign_key_with_source(self):
        """
        Check that we can both *create* and *update* into objects across
        ForeignKeys that have a `source` specified.
        Regression test for #1170
        """
        data = {
            'name': 'Discovery',
            'by': {'name': 'Daft Punk'},
        }

        expected = self.Album(artist=self.Artist('Daft Punk'), name='Discovery')

        # create
        serializer = self.AlbumSerializer(data=data)
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(serializer.object, expected)

        # update
        original = self.Album(artist=self.Artist('The Bats'), name='Free All the Monsters')
        serializer = self.AlbumSerializer(instance=original, data=data)
        self.assertEqual(serializer.is_valid(), True)
        self.assertEqual(serializer.object, expected)


class NestedModelSerializerUpdateTests(TestCase):
    def test_second_nested_level(self):
        john = models.Person.objects.create(name="john")

        post = john.blogpost_set.create(title="Test blog post")
        post.blogpostcomment_set.create(text="I hate this blog post")
        post.blogpostcomment_set.create(text="I love this blog post")

        class BlogPostCommentSerializer(serializers.ModelSerializer):
            class Meta:
                model = models.BlogPostComment

        class BlogPostSerializer(serializers.ModelSerializer):
            comments = BlogPostCommentSerializer(many=True, source='blogpostcomment_set')
            class Meta:
                model = models.BlogPost
                fields = ('id', 'title', 'comments')

        class PersonSerializer(serializers.ModelSerializer):
            posts = BlogPostSerializer(many=True, source='blogpost_set')
            class Meta:
                model = models.Person
                fields = ('id', 'name', 'age', 'posts')

        serialize = PersonSerializer(instance=john)
        deserialize = PersonSerializer(data=serialize.data, instance=john)
        self.assertTrue(deserialize.is_valid())

        result = deserialize.object
        result.save()
        self.assertEqual(result.id, john.id)

########NEW FILE########
__FILENAME__ = test_settings
"""Tests for the settings module"""
from __future__ import unicode_literals
from django.test import TestCase

from rest_framework.settings import APISettings, DEFAULTS, IMPORT_STRINGS


class TestSettings(TestCase):
    """Tests relating to the api settings"""

    def test_non_import_errors(self):
        """Make sure other errors aren't suppressed."""
        settings = APISettings({'DEFAULT_MODEL_SERIALIZER_CLASS': 'rest_framework.tests.extras.bad_import.ModelSerializer'}, DEFAULTS, IMPORT_STRINGS)
        with self.assertRaises(ValueError):
            settings.DEFAULT_MODEL_SERIALIZER_CLASS

    def test_import_error_message_maintained(self):
        """Make sure real import errors are captured and raised sensibly."""
        settings = APISettings({'DEFAULT_MODEL_SERIALIZER_CLASS': 'rest_framework.tests.extras.not_here.ModelSerializer'}, DEFAULTS, IMPORT_STRINGS)
        with self.assertRaises(ImportError) as cm:
            settings.DEFAULT_MODEL_SERIALIZER_CLASS
        self.assertTrue('ImportError' in str(cm.exception))

########NEW FILE########
__FILENAME__ = test_status
from __future__ import unicode_literals
from django.test import TestCase
from rest_framework.status import (
    is_informational, is_success, is_redirect, is_client_error, is_server_error
)


class TestStatus(TestCase):
    def test_status_categories(self):
        self.assertFalse(is_informational(99))
        self.assertTrue(is_informational(100))
        self.assertTrue(is_informational(199))
        self.assertFalse(is_informational(200))

        self.assertFalse(is_success(199))
        self.assertTrue(is_success(200))
        self.assertTrue(is_success(299))
        self.assertFalse(is_success(300))

        self.assertFalse(is_redirect(299))
        self.assertTrue(is_redirect(300))
        self.assertTrue(is_redirect(399))
        self.assertFalse(is_redirect(400))

        self.assertFalse(is_client_error(399))
        self.assertTrue(is_client_error(400))
        self.assertTrue(is_client_error(499))
        self.assertFalse(is_client_error(500))

        self.assertFalse(is_server_error(499))
        self.assertTrue(is_server_error(500))
        self.assertTrue(is_server_error(599))
        self.assertFalse(is_server_error(600))
########NEW FILE########
__FILENAME__ = test_templatetags
# encoding: utf-8
from __future__ import unicode_literals
from django.test import TestCase
from rest_framework.test import APIRequestFactory
from rest_framework.templatetags.rest_framework import add_query_param, urlize_quoted_links

factory = APIRequestFactory()


class TemplateTagTests(TestCase):

    def test_add_query_param_with_non_latin_charactor(self):
        # Ensure we don't double-escape non-latin characters
        # that are present in the querystring.
        # See #1314.
        request = factory.get("/", {'q': '查询'})
        json_url = add_query_param(request, "format", "json")
        self.assertIn("q=%E6%9F%A5%E8%AF%A2", json_url)
        self.assertIn("format=json", json_url)


class Issue1386Tests(TestCase):
    """
    Covers #1386
    """

    def test_issue_1386(self):
        """
        Test function urlize_quoted_links with different args
        """
        correct_urls = [
            "asdf.com",
            "asdf.net",
            "www.as_df.org",
            "as.d8f.ghj8.gov",
        ]
        for i in correct_urls:
            res = urlize_quoted_links(i)
            self.assertNotEqual(res, i)
            self.assertIn(i, res)

        incorrect_urls = [
            "mailto://asdf@fdf.com",
            "asdf.netnet",
        ]
        for i in incorrect_urls:
            res = urlize_quoted_links(i)
            self.assertEqual(i, res)

        # example from issue #1386, this shouldn't raise an exception
        _ = urlize_quoted_links("asdf:[/p]zxcv.com")

########NEW FILE########
__FILENAME__ = test_testing
# -- coding: utf-8 --

from __future__ import unicode_literals
from io import BytesIO

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.compat import patterns, url
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate


@api_view(['GET', 'POST'])
def view(request):
    return Response({
        'auth': request.META.get('HTTP_AUTHORIZATION', b''),
        'user': request.user.username
    })


@api_view(['GET', 'POST'])
def session_view(request):
    active_session = request.session.get('active_session', False)
    request.session['active_session'] = True
    return Response({
        'active_session': active_session
    })


urlpatterns = patterns('',
    url(r'^view/$', view),
    url(r'^session-view/$', session_view),
)


class TestAPITestClient(TestCase):
    urls = 'rest_framework.tests.test_testing'

    def setUp(self):
        self.client = APIClient()

    def test_credentials(self):
        """
        Setting `.credentials()` adds the required headers to each request.
        """
        self.client.credentials(HTTP_AUTHORIZATION='example')
        for _ in range(0, 3):
            response = self.client.get('/view/')
            self.assertEqual(response.data['auth'], 'example')

    def test_force_authenticate(self):
        """
        Setting `.force_authenticate()` forcibly authenticates each request.
        """
        user = User.objects.create_user('example', 'example@example.com')
        self.client.force_authenticate(user)
        response = self.client.get('/view/')
        self.assertEqual(response.data['user'], 'example')

    def test_force_authenticate_with_sessions(self):
        """
        Setting `.force_authenticate()` forcibly authenticates each request.
        """
        user = User.objects.create_user('example', 'example@example.com')
        self.client.force_authenticate(user)

        # First request does not yet have an active session
        response = self.client.get('/session-view/')
        self.assertEqual(response.data['active_session'], False)

        # Subsequant requests have an active session
        response = self.client.get('/session-view/')
        self.assertEqual(response.data['active_session'], True)

        # Force authenticating as `None` should also logout the user session.
        self.client.force_authenticate(None)
        response = self.client.get('/session-view/')
        self.assertEqual(response.data['active_session'], False)

    def test_csrf_exempt_by_default(self):
        """
        By default, the test client is CSRF exempt.
        """
        User.objects.create_user('example', 'example@example.com', 'password')
        self.client.login(username='example', password='password')
        response = self.client.post('/view/')
        self.assertEqual(response.status_code, 200)

    def test_explicitly_enforce_csrf_checks(self):
        """
        The test client can enforce CSRF checks.
        """
        client = APIClient(enforce_csrf_checks=True)
        User.objects.create_user('example', 'example@example.com', 'password')
        client.login(username='example', password='password')
        response = client.post('/view/')
        expected = {'detail': 'CSRF Failed: CSRF cookie not set.'}
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data, expected)


class TestAPIRequestFactory(TestCase):
    def test_csrf_exempt_by_default(self):
        """
        By default, the test client is CSRF exempt.
        """
        user = User.objects.create_user('example', 'example@example.com', 'password')
        factory = APIRequestFactory()
        request = factory.post('/view/')
        request.user = user
        response = view(request)
        self.assertEqual(response.status_code, 200)

    def test_explicitly_enforce_csrf_checks(self):
        """
        The test client can enforce CSRF checks.
        """
        user = User.objects.create_user('example', 'example@example.com', 'password')
        factory = APIRequestFactory(enforce_csrf_checks=True)
        request = factory.post('/view/')
        request.user = user
        response = view(request)
        expected = {'detail': 'CSRF Failed: CSRF cookie not set.'}
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data, expected)

    def test_invalid_format(self):
        """
        Attempting to use a format that is not configured will raise an
        assertion error.
        """
        factory = APIRequestFactory()
        self.assertRaises(AssertionError, factory.post,
            path='/view/', data={'example': 1}, format='xml'
        )

    def test_force_authenticate(self):
        """
        Setting `force_authenticate()` forcibly authenticates the request.
        """
        user = User.objects.create_user('example', 'example@example.com')
        factory = APIRequestFactory()
        request = factory.get('/view')
        force_authenticate(request, user=user)
        response = view(request)
        self.assertEqual(response.data['user'], 'example')

    def test_upload_file(self):
        # This is a 1x1 black png
        simple_png = BytesIO(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc````\x00\x00\x00\x05\x00\x01\xa5\xf6E@\x00\x00\x00\x00IEND\xaeB`\x82')
        simple_png.name = 'test.png'
        factory = APIRequestFactory()
        factory.post('/', data={'image': simple_png})

    def test_request_factory_url_arguments(self):
        """
        This is a non regression test against #1461
        """
        factory = APIRequestFactory()
        request = factory.get('/view/?demo=test')
        self.assertEqual(dict(request.GET), {'demo': ['test']})
        request = factory.get('/view/', {'demo': 'test'})
        self.assertEqual(dict(request.GET), {'demo': ['test']})

########NEW FILE########
__FILENAME__ = test_throttling
"""
Tests for the throttling implementations in the permissions module.
"""
from __future__ import unicode_literals
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView
from rest_framework.throttling import BaseThrottle, UserRateThrottle, ScopedRateThrottle
from rest_framework.response import Response


class User3SecRateThrottle(UserRateThrottle):
    rate = '3/sec'
    scope = 'seconds'


class User3MinRateThrottle(UserRateThrottle):
    rate = '3/min'
    scope = 'minutes'


class NonTimeThrottle(BaseThrottle):
    def allow_request(self, request, view):
        if not hasattr(self.__class__, 'called'):
            self.__class__.called = True
            return True
        return False 


class MockView(APIView):
    throttle_classes = (User3SecRateThrottle,)

    def get(self, request):
        return Response('foo')


class MockView_MinuteThrottling(APIView):
    throttle_classes = (User3MinRateThrottle,)

    def get(self, request):
        return Response('foo')


class MockView_NonTimeThrottling(APIView):
    throttle_classes = (NonTimeThrottle,)

    def get(self, request):
        return Response('foo')


class ThrottlingTests(TestCase):
    def setUp(self):
        """
        Reset the cache so that no throttles will be active
        """
        cache.clear()
        self.factory = APIRequestFactory()

    def test_requests_are_throttled(self):
        """
        Ensure request rate is limited
        """
        request = self.factory.get('/')
        for dummy in range(4):
            response = MockView.as_view()(request)
        self.assertEqual(429, response.status_code)

    def set_throttle_timer(self, view, value):
        """
        Explicitly set the timer, overriding time.time()
        """
        view.throttle_classes[0].timer = lambda self: value

    def test_request_throttling_expires(self):
        """
        Ensure request rate is limited for a limited duration only
        """
        self.set_throttle_timer(MockView, 0)

        request = self.factory.get('/')
        for dummy in range(4):
            response = MockView.as_view()(request)
        self.assertEqual(429, response.status_code)

        # Advance the timer by one second
        self.set_throttle_timer(MockView, 1)

        response = MockView.as_view()(request)
        self.assertEqual(200, response.status_code)

    def ensure_is_throttled(self, view, expect):
        request = self.factory.get('/')
        request.user = User.objects.create(username='a')
        for dummy in range(3):
            view.as_view()(request)
        request.user = User.objects.create(username='b')
        response = view.as_view()(request)
        self.assertEqual(expect, response.status_code)

    def test_request_throttling_is_per_user(self):
        """
        Ensure request rate is only limited per user, not globally for
        PerUserThrottles
        """
        self.ensure_is_throttled(MockView, 200)

    def ensure_response_header_contains_proper_throttle_field(self, view, expected_headers):
        """
        Ensure the response returns an X-Throttle field with status and next attributes
        set properly.
        """
        request = self.factory.get('/')
        for timer, expect in expected_headers:
            self.set_throttle_timer(view, timer)
            response = view.as_view()(request)
            if expect is not None:
                self.assertEqual(response['X-Throttle-Wait-Seconds'], expect)
            else:
                self.assertFalse('X-Throttle-Wait-Seconds' in response)

    def test_seconds_fields(self):
        """
        Ensure for second based throttles.
        """
        self.ensure_response_header_contains_proper_throttle_field(MockView,
         ((0, None),
          (0, None),
          (0, None),
          (0, '1')
         ))

    def test_minutes_fields(self):
        """
        Ensure for minute based throttles.
        """
        self.ensure_response_header_contains_proper_throttle_field(MockView_MinuteThrottling,
         ((0, None),
          (0, None),
          (0, None),
          (0, '60')
         ))

    def test_next_rate_remains_constant_if_followed(self):
        """
        If a client follows the recommended next request rate,
        the throttling rate should stay constant.
        """
        self.ensure_response_header_contains_proper_throttle_field(MockView_MinuteThrottling,
         ((0, None),
          (20, None),
          (40, None),
          (60, None),
          (80, None)
         ))

    def test_non_time_throttle(self):
        """
        Ensure for second based throttles.
        """
        request = self.factory.get('/')

        self.assertFalse(hasattr(MockView_NonTimeThrottling.throttle_classes[0], 'called'))

        response = MockView_NonTimeThrottling.as_view()(request)
        self.assertFalse('X-Throttle-Wait-Seconds' in response)

        self.assertTrue(MockView_NonTimeThrottling.throttle_classes[0].called)

        response = MockView_NonTimeThrottling.as_view()(request)
        self.assertFalse('X-Throttle-Wait-Seconds' in response) 


class ScopedRateThrottleTests(TestCase):
    """
    Tests for ScopedRateThrottle.
    """

    def setUp(self):
        class XYScopedRateThrottle(ScopedRateThrottle):
            TIMER_SECONDS = 0
            THROTTLE_RATES = {'x': '3/min', 'y': '1/min'}
            timer = lambda self: self.TIMER_SECONDS

        class XView(APIView):
            throttle_classes = (XYScopedRateThrottle,)
            throttle_scope = 'x'

            def get(self, request):
                return Response('x')

        class YView(APIView):
            throttle_classes = (XYScopedRateThrottle,)
            throttle_scope = 'y'

            def get(self, request):
                return Response('y')

        class UnscopedView(APIView):
            throttle_classes = (XYScopedRateThrottle,)

            def get(self, request):
                return Response('y')

        self.throttle_class = XYScopedRateThrottle
        self.factory = APIRequestFactory()
        self.x_view = XView.as_view()
        self.y_view = YView.as_view()
        self.unscoped_view = UnscopedView.as_view()

    def increment_timer(self, seconds=1):
        self.throttle_class.TIMER_SECONDS += seconds

    def test_scoped_rate_throttle(self):
        request = self.factory.get('/')

        # Should be able to hit x view 3 times per minute.
        response = self.x_view(request)
        self.assertEqual(200, response.status_code)

        self.increment_timer()
        response = self.x_view(request)
        self.assertEqual(200, response.status_code)

        self.increment_timer()
        response = self.x_view(request)
        self.assertEqual(200, response.status_code)

        self.increment_timer()
        response = self.x_view(request)
        self.assertEqual(429, response.status_code)

        # Should be able to hit y view 1 time per minute.
        self.increment_timer()
        response = self.y_view(request)
        self.assertEqual(200, response.status_code)

        self.increment_timer()
        response = self.y_view(request)
        self.assertEqual(429, response.status_code)

        # Ensure throttles properly reset by advancing the rest of the minute
        self.increment_timer(55)

        # Should still be able to hit x view 3 times per minute.
        response = self.x_view(request)
        self.assertEqual(200, response.status_code)

        self.increment_timer()
        response = self.x_view(request)
        self.assertEqual(200, response.status_code)

        self.increment_timer()
        response = self.x_view(request)
        self.assertEqual(200, response.status_code)

        self.increment_timer()
        response = self.x_view(request)
        self.assertEqual(429, response.status_code)

        # Should still be able to hit y view 1 time per minute.
        self.increment_timer()
        response = self.y_view(request)
        self.assertEqual(200, response.status_code)

        self.increment_timer()
        response = self.y_view(request)
        self.assertEqual(429, response.status_code)

    def test_unscoped_view_not_throttled(self):
        request = self.factory.get('/')

        for idx in range(10):
            self.increment_timer()
            response = self.unscoped_view(request)
            self.assertEqual(200, response.status_code)

########NEW FILE########
__FILENAME__ = test_urlizer
from __future__ import unicode_literals
from django.test import TestCase
from rest_framework.templatetags.rest_framework import urlize_quoted_links
import sys


class URLizerTests(TestCase):
    """
    Test if both JSON and YAML URLs are transformed into links well
    """
    def _urlize_dict_check(self, data):
        """
        For all items in dict test assert that the value is urlized key
        """
        for original, urlized in data.items():
            assert urlize_quoted_links(original, nofollow=False) == urlized

    def test_json_with_url(self):
        """
        Test if JSON URLs are transformed into links well
        """
        data = {}
        data['"url": "http://api/users/1/", '] = \
            '&quot;url&quot;: &quot;<a href="http://api/users/1/">http://api/users/1/</a>&quot;, '
        data['"foo_set": [\n    "http://api/foos/1/"\n], '] = \
            '&quot;foo_set&quot;: [\n    &quot;<a href="http://api/foos/1/">http://api/foos/1/</a>&quot;\n], '
        self._urlize_dict_check(data)

    def test_yaml_with_url(self):
        """
        Test if YAML URLs are transformed into links well
        """
        data = {}
        data['''{users: 'http://api/users/'}'''] = \
            '''{users: &#39;<a href="http://api/users/">http://api/users/</a>&#39;}'''
        data['''foo_set: ['http://api/foos/1/']'''] = \
            '''foo_set: [&#39;<a href="http://api/foos/1/">http://api/foos/1/</a>&#39;]'''
        self._urlize_dict_check(data)

########NEW FILE########
__FILENAME__ = test_urlpatterns
from __future__ import unicode_literals
from collections import namedtuple
from django.core import urlresolvers
from django.test import TestCase
from rest_framework.test import APIRequestFactory
from rest_framework.compat import patterns, url, include
from rest_framework.urlpatterns import format_suffix_patterns


# A container class for test paths for the test case
URLTestPath = namedtuple('URLTestPath', ['path', 'args', 'kwargs'])


def dummy_view(request, *args, **kwargs):
    pass


class FormatSuffixTests(TestCase):
    """
    Tests `format_suffix_patterns` against different URLPatterns to ensure the URLs still resolve properly, including any captured parameters.
    """
    def _resolve_urlpatterns(self, urlpatterns, test_paths):
        factory = APIRequestFactory()
        try:
            urlpatterns = format_suffix_patterns(urlpatterns)
        except Exception:
            self.fail("Failed to apply `format_suffix_patterns` on  the supplied urlpatterns")
        resolver = urlresolvers.RegexURLResolver(r'^/', urlpatterns)
        for test_path in test_paths:
            request = factory.get(test_path.path)
            try:
                callback, callback_args, callback_kwargs = resolver.resolve(request.path_info)
            except Exception:
                self.fail("Failed to resolve URL: %s" % request.path_info)
            self.assertEqual(callback_args, test_path.args)
            self.assertEqual(callback_kwargs, test_path.kwargs)

    def test_format_suffix(self):
        urlpatterns = patterns(
            '',
            url(r'^test$', dummy_view),
        )
        test_paths = [
            URLTestPath('/test', (), {}),
            URLTestPath('/test.api', (), {'format': 'api'}),
            URLTestPath('/test.asdf', (), {'format': 'asdf'}),
        ]
        self._resolve_urlpatterns(urlpatterns, test_paths)

    def test_default_args(self):
        urlpatterns = patterns(
            '',
            url(r'^test$', dummy_view, {'foo': 'bar'}),
        )
        test_paths = [
            URLTestPath('/test', (), {'foo': 'bar', }),
            URLTestPath('/test.api', (), {'foo': 'bar', 'format': 'api'}),
            URLTestPath('/test.asdf', (), {'foo': 'bar', 'format': 'asdf'}),
        ]
        self._resolve_urlpatterns(urlpatterns, test_paths)

    def test_included_urls(self):
        nested_patterns = patterns(
            '',
            url(r'^path$', dummy_view)
        )
        urlpatterns = patterns(
            '',
            url(r'^test/', include(nested_patterns), {'foo': 'bar'}),
        )
        test_paths = [
            URLTestPath('/test/path', (), {'foo': 'bar', }),
            URLTestPath('/test/path.api', (), {'foo': 'bar', 'format': 'api'}),
            URLTestPath('/test/path.asdf', (), {'foo': 'bar', 'format': 'asdf'}),
        ]
        self._resolve_urlpatterns(urlpatterns, test_paths)

########NEW FILE########
__FILENAME__ = test_validation
from __future__ import unicode_literals
from django.core.validators import MaxValueValidator
from django.db import models
from django.test import TestCase
from rest_framework import generics, serializers, status
from rest_framework.test import APIRequestFactory

factory = APIRequestFactory()


# Regression for #666

class ValidationModel(models.Model):
    blank_validated_field = models.CharField(max_length=255)


class ValidationModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValidationModel
        fields = ('blank_validated_field',)
        read_only_fields = ('blank_validated_field',)


class UpdateValidationModel(generics.RetrieveUpdateDestroyAPIView):
    model = ValidationModel
    serializer_class = ValidationModelSerializer


class TestPreSaveValidationExclusions(TestCase):
    def test_pre_save_validation_exclusions(self):
        """
        Somewhat weird test case to ensure that we don't perform model
        validation on read only fields.
        """
        obj = ValidationModel.objects.create(blank_validated_field='')
        request = factory.put('/', {}, format='json')
        view = UpdateValidationModel().as_view()
        response = view(request, pk=obj.pk).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# Regression for #653

class ShouldValidateModel(models.Model):
    should_validate_field = models.CharField(max_length=255)


class ShouldValidateModelSerializer(serializers.ModelSerializer):
    renamed = serializers.CharField(source='should_validate_field', required=False)

    def validate_renamed(self, attrs, source):
        value = attrs[source]
        if len(value) < 3:
            raise serializers.ValidationError('Minimum 3 characters.')
        return attrs

    class Meta:
        model = ShouldValidateModel
        fields = ('renamed',)


class TestPreSaveValidationExclusionsSerializer(TestCase):
    def test_renamed_fields_are_model_validated(self):
        """
        Ensure fields with 'source' applied do get still get model validation.
        """
        # We've set `required=False` on the serializer, but the model
        # does not have `blank=True`, so this serializer should not validate.
        serializer = ShouldValidateModelSerializer(data={'renamed': ''})
        self.assertEqual(serializer.is_valid(), False)
        self.assertIn('renamed', serializer.errors)
        self.assertNotIn('should_validate_field', serializer.errors)


class TestCustomValidationMethods(TestCase):
    def test_custom_validation_method_is_executed(self):
        serializer = ShouldValidateModelSerializer(data={'renamed': 'fo'})
        self.assertFalse(serializer.is_valid())
        self.assertIn('renamed', serializer.errors)

    def test_custom_validation_method_passing(self):
        serializer = ShouldValidateModelSerializer(data={'renamed': 'foo'})
        self.assertTrue(serializer.is_valid())


class ValidationSerializer(serializers.Serializer):
    foo = serializers.CharField()

    def validate_foo(self, attrs, source):
        raise serializers.ValidationError("foo invalid")

    def validate(self, attrs):
        raise serializers.ValidationError("serializer invalid")


class TestAvoidValidation(TestCase):
    """
    If serializer was initialized with invalid data (None or non dict-like), it
    should avoid validation layer (validate_<field> and validate methods)
    """
    def test_serializer_errors_has_only_invalid_data_error(self):
        serializer = ValidationSerializer(data='invalid data')
        self.assertFalse(serializer.is_valid())
        self.assertDictEqual(serializer.errors,
                             {'non_field_errors': ['Invalid data']})


# regression tests for issue: 1493

class ValidationMaxValueValidatorModel(models.Model):
    number_value = models.PositiveIntegerField(validators=[MaxValueValidator(100)])


class ValidationMaxValueValidatorModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValidationMaxValueValidatorModel


class UpdateMaxValueValidationModel(generics.RetrieveUpdateDestroyAPIView):
    model = ValidationMaxValueValidatorModel
    serializer_class = ValidationMaxValueValidatorModelSerializer


class TestMaxValueValidatorValidation(TestCase):

    def test_max_value_validation_serializer_success(self):
        serializer = ValidationMaxValueValidatorModelSerializer(data={'number_value': 99})
        self.assertTrue(serializer.is_valid())

    def test_max_value_validation_serializer_fails(self):
        serializer = ValidationMaxValueValidatorModelSerializer(data={'number_value': 101})
        self.assertFalse(serializer.is_valid())
        self.assertDictEqual({'number_value': ['Ensure this value is less than or equal to 100.']}, serializer.errors)

    def test_max_value_validation_success(self):
        obj = ValidationMaxValueValidatorModel.objects.create(number_value=100)
        request = factory.patch('/{0}'.format(obj.pk), {'number_value': 98}, format='json')
        view = UpdateMaxValueValidationModel().as_view()
        response = view(request, pk=obj.pk).render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_max_value_validation_fail(self):
        obj = ValidationMaxValueValidatorModel.objects.create(number_value=100)
        request = factory.patch('/{0}'.format(obj.pk), {'number_value': 101}, format='json')
        view = UpdateMaxValueValidationModel().as_view()
        response = view(request, pk=obj.pk).render()
        self.assertEqual(response.content, b'{"number_value": ["Ensure this value is less than or equal to 100."]}')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

########NEW FILE########
__FILENAME__ = test_views
from __future__ import unicode_literals

import sys
import copy
from django.test import TestCase
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

factory = APIRequestFactory()

if sys.version_info[:2] >= (3, 4):
    JSON_ERROR = 'JSON parse error - Expecting value:'
else:
    JSON_ERROR = 'JSON parse error - No JSON object could be decoded'


class BasicView(APIView):
    def get(self, request, *args, **kwargs):
        return Response({'method': 'GET'})

    def post(self, request, *args, **kwargs):
        return Response({'method': 'POST', 'data': request.DATA})


@api_view(['GET', 'POST', 'PUT', 'PATCH'])
def basic_view(request):
    if request.method == 'GET':
        return {'method': 'GET'}
    elif request.method == 'POST':
        return {'method': 'POST', 'data': request.DATA}
    elif request.method == 'PUT':
        return {'method': 'PUT', 'data': request.DATA}
    elif request.method == 'PATCH':
        return {'method': 'PATCH', 'data': request.DATA}


class ErrorView(APIView):
    def get(self, request, *args, **kwargs):
        raise Exception


@api_view(['GET'])
def error_view(request):
    raise Exception


def sanitise_json_error(error_dict):
    """
    Exact contents of JSON error messages depend on the installed version
    of json.
    """
    ret = copy.copy(error_dict)
    chop = len(JSON_ERROR)
    ret['detail'] = ret['detail'][:chop]
    return ret


class ClassBasedViewIntegrationTests(TestCase):
    def setUp(self):
        self.view = BasicView.as_view()

    def test_400_parse_error(self):
        request = factory.post('/', 'f00bar', content_type='application/json')
        response = self.view(request)
        expected = {
            'detail': JSON_ERROR
        }
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(sanitise_json_error(response.data), expected)

    def test_400_parse_error_tunneled_content(self):
        content = 'f00bar'
        content_type = 'application/json'
        form_data = {
            api_settings.FORM_CONTENT_OVERRIDE: content,
            api_settings.FORM_CONTENTTYPE_OVERRIDE: content_type
        }
        request = factory.post('/', form_data)
        response = self.view(request)
        expected = {
            'detail': JSON_ERROR
        }
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(sanitise_json_error(response.data), expected)


class FunctionBasedViewIntegrationTests(TestCase):
    def setUp(self):
        self.view = basic_view

    def test_400_parse_error(self):
        request = factory.post('/', 'f00bar', content_type='application/json')
        response = self.view(request)
        expected = {
            'detail': JSON_ERROR
        }
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(sanitise_json_error(response.data), expected)

    def test_400_parse_error_tunneled_content(self):
        content = 'f00bar'
        content_type = 'application/json'
        form_data = {
            api_settings.FORM_CONTENT_OVERRIDE: content,
            api_settings.FORM_CONTENTTYPE_OVERRIDE: content_type
        }
        request = factory.post('/', form_data)
        response = self.view(request)
        expected = {
            'detail': JSON_ERROR
        }
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(sanitise_json_error(response.data), expected)


class TestCustomExceptionHandler(TestCase):
    def setUp(self):
        self.DEFAULT_HANDLER = api_settings.EXCEPTION_HANDLER

        def exception_handler(exc):
            return Response('Error!', status=status.HTTP_400_BAD_REQUEST)

        api_settings.EXCEPTION_HANDLER = exception_handler

    def tearDown(self):
        api_settings.EXCEPTION_HANDLER = self.DEFAULT_HANDLER

    def test_class_based_view_exception_handler(self):
        view = ErrorView.as_view()

        request = factory.get('/', content_type='application/json')
        response = view(request)
        expected = 'Error!'
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, expected)

    def test_function_based_view_exception_handler(self):
        view = error_view

        request = factory.get('/', content_type='application/json')
        response = view(request)
        expected = 'Error!'
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, expected)

########NEW FILE########
__FILENAME__ = test_write_only_fields
from django.db import models
from django.test import TestCase
from rest_framework import serializers


class ExampleModel(models.Model):
    email = models.EmailField(max_length=100)
    password = models.CharField(max_length=100)


class WriteOnlyFieldTests(TestCase):
    def test_write_only_fields(self):
        class ExampleSerializer(serializers.Serializer):
            email = serializers.EmailField()
            password = serializers.CharField(write_only=True)

        data = {
            'email': 'foo@example.com',
            'password': '123'
        }
        serializer = ExampleSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEquals(serializer.object, data)
        self.assertEquals(serializer.data, {'email': 'foo@example.com'})

    def test_write_only_fields_meta(self):
        class ExampleSerializer(serializers.ModelSerializer):
            class Meta:
                model = ExampleModel
                fields = ('email', 'password')
                write_only_fields = ('password',)

        data = {
            'email': 'foo@example.com',
            'password': '123'
        }
        serializer = ExampleSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertTrue(isinstance(serializer.object, ExampleModel))
        self.assertEquals(serializer.object.email, data['email'])
        self.assertEquals(serializer.object.password, data['password'])
        self.assertEquals(serializer.data, {'email': 'foo@example.com'})

########NEW FILE########
__FILENAME__ = models
from django.db import models


class User(models.Model):
    account = models.ForeignKey('accounts.Account', blank=True, null=True, related_name='users')
    active_record = models.ForeignKey('records.Record', blank=True, null=True)

########NEW FILE########
__FILENAME__ = serializers
from rest_framework import serializers

from rest_framework.tests.users.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User

########NEW FILE########
__FILENAME__ = utils
from contextlib import contextmanager
from rest_framework.compat import six
from rest_framework.settings import api_settings


@contextmanager
def temporary_setting(setting, value, module=None):
    """
    Temporarily change value of setting for test.

    Optionally reload given module, useful when module uses value of setting on
    import.
    """
    original_value = getattr(api_settings, setting)
    setattr(api_settings, setting, value)

    if module is not None:
        six.moves.reload_module(module)

    yield

    setattr(api_settings, setting, original_value)

    if module is not None:
        six.moves.reload_module(module)

########NEW FILE########
__FILENAME__ = views
from rest_framework import generics
from rest_framework.tests.models import NullableForeignKeySource
from rest_framework.tests.serializers import NullableFKSourceSerializer


class NullableFKSourceDetail(generics.RetrieveUpdateDestroyAPIView):
    model = NullableForeignKeySource
    model_serializer_class = NullableFKSourceSerializer

########NEW FILE########
__FILENAME__ = throttling
"""
Provides various throttling policies.
"""
from __future__ import unicode_literals
from django.core.cache import cache as default_cache
from django.core.exceptions import ImproperlyConfigured
from rest_framework.settings import api_settings
import time


class BaseThrottle(object):
    """
    Rate throttling of requests.
    """
    def allow_request(self, request, view):
        """
        Return `True` if the request should be allowed, `False` otherwise.
        """
        raise NotImplementedError('.allow_request() must be overridden')

    def wait(self):
        """
        Optionally, return a recommended number of seconds to wait before
        the next request.
        """
        return None


class SimpleRateThrottle(BaseThrottle):
    """
    A simple cache implementation, that only requires `.get_cache_key()`
    to be overridden.

    The rate (requests / seconds) is set by a `throttle` attribute on the View
    class.  The attribute is a string of the form 'number_of_requests/period'.

    Period should be one of: ('s', 'sec', 'm', 'min', 'h', 'hour', 'd', 'day')

    Previous request information used for throttling is stored in the cache.
    """

    cache = default_cache
    timer = time.time
    cache_format = 'throtte_%(scope)s_%(ident)s'
    scope = None
    THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES

    def __init__(self):
        if not getattr(self, 'rate', None):
            self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)

    def get_cache_key(self, request, view):
        """
        Should return a unique cache-key which can be used for throttling.
        Must be overridden.

        May return `None` if the request should not be throttled.
        """
        raise NotImplementedError('.get_cache_key() must be overridden')

    def get_rate(self):
        """
        Determine the string representation of the allowed request rate.
        """
        if not getattr(self, 'scope', None):
            msg = ("You must set either `.scope` or `.rate` for '%s' throttle" %
                   self.__class__.__name__)
            raise ImproperlyConfigured(msg)

        try:
            return self.THROTTLE_RATES[self.scope]
        except KeyError:
            msg = "No default throttle rate set for '%s' scope" % self.scope
            raise ImproperlyConfigured(msg)

    def parse_rate(self, rate):
        """
        Given the request rate string, return a two tuple of:
        <allowed number of requests>, <period of time in seconds>
        """
        if rate is None:
            return (None, None)
        num, period = rate.split('/')
        num_requests = int(num)
        duration = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[period[0]]
        return (num_requests, duration)

    def allow_request(self, request, view):
        """
        Implement the check to see if the request should be throttled.

        On success calls `throttle_success`.
        On failure calls `throttle_failure`.
        """
        if self.rate is None:
            return True

        self.key = self.get_cache_key(request, view)
        if self.key is None:
            return True

        self.history = self.cache.get(self.key, [])
        self.now = self.timer()

        # Drop any requests from the history which have now passed the
        # throttle duration
        while self.history and self.history[-1] <= self.now - self.duration:
            self.history.pop()
        if len(self.history) >= self.num_requests:
            return self.throttle_failure()
        return self.throttle_success()

    def throttle_success(self):
        """
        Inserts the current request's timestamp along with the key
        into the cache.
        """
        self.history.insert(0, self.now)
        self.cache.set(self.key, self.history, self.duration)
        return True

    def throttle_failure(self):
        """
        Called when a request to the API has failed due to throttling.
        """
        return False

    def wait(self):
        """
        Returns the recommended next request time in seconds.
        """
        if self.history:
            remaining_duration = self.duration - (self.now - self.history[-1])
        else:
            remaining_duration = self.duration

        available_requests = self.num_requests - len(self.history) + 1
        if available_requests <= 0:
            return None

        return remaining_duration / float(available_requests)


class AnonRateThrottle(SimpleRateThrottle):
    """
    Limits the rate of API calls that may be made by a anonymous users.

    The IP address of the request will be used as the unique cache key.
    """
    scope = 'anon'

    def get_cache_key(self, request, view):
        if request.user.is_authenticated():
            return None  # Only throttle unauthenticated requests.

        ident = request.META.get('HTTP_X_FORWARDED_FOR')
        if ident is None:
            ident = request.META.get('REMOTE_ADDR')
        else:
            ident = ''.join(ident.split())

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class UserRateThrottle(SimpleRateThrottle):
    """
    Limits the rate of API calls that may be made by a given user.

    The user id will be used as a unique cache key if the user is
    authenticated.  For anonymous requests, the IP address of the request will
    be used.
    """
    scope = 'user'

    def get_cache_key(self, request, view):
        if request.user.is_authenticated():
            ident = request.user.id
        else:
            ident = request.META.get('REMOTE_ADDR', None)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class ScopedRateThrottle(SimpleRateThrottle):
    """
    Limits the rate of API calls by different amounts for various parts of
    the API.  Any view that has the `throttle_scope` property set will be
    throttled.  The unique cache key will be generated by concatenating the
    user id of the request, and the scope of the view being accessed.
    """
    scope_attr = 'throttle_scope'

    def __init__(self):
        # Override the usual SimpleRateThrottle, because we can't determine
        # the rate until called by the view.
        pass

    def allow_request(self, request, view):
        # We can only determine the scope once we're called by the view.
        self.scope = getattr(view, self.scope_attr, None)

        # If a view does not have a `throttle_scope` always allow the request
        if not self.scope:
            return True

        # Determine the allowed request rate as we normally would during
        # the `__init__` call.
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)

        # We can now proceed as normal.
        return super(ScopedRateThrottle, self).allow_request(request, view)

    def get_cache_key(self, request, view):
        """
        If `view.throttle_scope` is not set, don't apply this throttle.

        Otherwise generate the unique cache key by concatenating the user id
        with the '.throttle_scope` property of the view.
        """
        if request.user.is_authenticated():
            ident = request.user.id
        else:
            ident = request.META.get('REMOTE_ADDR', None)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }

########NEW FILE########
__FILENAME__ = urlpatterns
from __future__ import unicode_literals
from django.core.urlresolvers import RegexURLResolver
from rest_framework.compat import url, include
from rest_framework.settings import api_settings


def apply_suffix_patterns(urlpatterns, suffix_pattern, suffix_required):
    ret = []
    for urlpattern in urlpatterns:
        if isinstance(urlpattern, RegexURLResolver):
            # Set of included URL patterns
            regex = urlpattern.regex.pattern
            namespace = urlpattern.namespace
            app_name = urlpattern.app_name
            kwargs = urlpattern.default_kwargs
            # Add in the included patterns, after applying the suffixes
            patterns = apply_suffix_patterns(urlpattern.url_patterns,
                                             suffix_pattern,
                                             suffix_required)
            ret.append(url(regex, include(patterns, namespace, app_name), kwargs))

        else:
            # Regular URL pattern
            regex = urlpattern.regex.pattern.rstrip('$') + suffix_pattern
            view = urlpattern._callback or urlpattern._callback_str
            kwargs = urlpattern.default_args
            name = urlpattern.name
            # Add in both the existing and the new urlpattern
            if not suffix_required:
                ret.append(urlpattern)
            ret.append(url(regex, view, kwargs, name))

    return ret


def format_suffix_patterns(urlpatterns, suffix_required=False, allowed=None):
    """
    Supplement existing urlpatterns with corresponding patterns that also
    include a '.format' suffix.  Retains urlpattern ordering.

    urlpatterns:
        A list of URL patterns.

    suffix_required:
        If `True`, only suffixed URLs will be generated, and non-suffixed
        URLs will not be used.  Defaults to `False`.

    allowed:
        An optional tuple/list of allowed suffixes.  eg ['json', 'api']
        Defaults to `None`, which allows any suffix.
    """
    suffix_kwarg = api_settings.FORMAT_SUFFIX_KWARG
    if allowed:
        if len(allowed) == 1:
            allowed_pattern = allowed[0]
        else:
            allowed_pattern = '(%s)' % '|'.join(allowed)
        suffix_pattern = r'\.(?P<%s>%s)$' % (suffix_kwarg, allowed_pattern)
    else:
        suffix_pattern = r'\.(?P<%s>[a-z0-9]+)$' % suffix_kwarg

    return apply_suffix_patterns(urlpatterns, suffix_pattern, suffix_required)

########NEW FILE########
__FILENAME__ = urls
"""
Login and logout views for the browsable API.

Add these to your root URLconf if you're using the browsable API and
your API requires authentication.

The urls must be namespaced as 'rest_framework', and you should make sure
your authentication settings include `SessionAuthentication`.

    urlpatterns = patterns('',
        ...
        url(r'^auth', include('rest_framework.urls', namespace='rest_framework'))
    )
"""
from __future__ import unicode_literals
from rest_framework.compat import patterns, url


template_name = {'template_name': 'rest_framework/login.html'}

urlpatterns = patterns('django.contrib.auth.views',
    url(r'^login/$', 'login', template_name, name='login'),
    url(r'^logout/$', 'logout', template_name, name='logout'),
)

########NEW FILE########
__FILENAME__ = breadcrumbs
from __future__ import unicode_literals
from django.core.urlresolvers import resolve, get_script_prefix


def get_breadcrumbs(url):
    """
    Given a url returns a list of breadcrumbs, which are each a
    tuple of (name, url).
    """

    from rest_framework.settings import api_settings
    from rest_framework.views import APIView

    view_name_func = api_settings.VIEW_NAME_FUNCTION

    def breadcrumbs_recursive(url, breadcrumbs_list, prefix, seen):
        """
        Add tuples of (name, url) to the breadcrumbs list,
        progressively chomping off parts of the url.
        """

        try:
            (view, unused_args, unused_kwargs) = resolve(url)
        except Exception:
            pass
        else:
            # Check if this is a REST framework view,
            # and if so add it to the breadcrumbs
            cls = getattr(view, 'cls', None)
            if cls is not None and issubclass(cls, APIView):
                # Don't list the same view twice in a row.
                # Probably an optional trailing slash.
                if not seen or seen[-1] != view:
                    suffix = getattr(view, 'suffix', None)
                    name = view_name_func(cls, suffix)
                    breadcrumbs_list.insert(0, (name, prefix + url))
                    seen.append(view)

        if url == '':
            # All done
            return breadcrumbs_list

        elif url.endswith('/'):
            # Drop trailing slash off the end and continue to try to
            # resolve more breadcrumbs
            url = url.rstrip('/')
            return breadcrumbs_recursive(url, breadcrumbs_list, prefix, seen)

        # Drop trailing non-slash off the end and continue to try to
        # resolve more breadcrumbs
        url = url[:url.rfind('/') + 1]
        return breadcrumbs_recursive(url, breadcrumbs_list, prefix, seen)

    prefix = get_script_prefix().rstrip('/')
    url = url[len(prefix):]
    return breadcrumbs_recursive(url, [], prefix, [])

########NEW FILE########
__FILENAME__ = encoders
"""
Helper classes for parsers.
"""
from __future__ import unicode_literals
from django.db.models.query import QuerySet
from django.utils.datastructures import SortedDict
from django.utils.functional import Promise
from rest_framework.compat import timezone, force_text
from rest_framework.serializers import DictWithMetadata, SortedDictWithMetadata
import datetime
import decimal
import types
import json


class JSONEncoder(json.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time/timedelta,
    decimal types, and generators.
    """
    def default(self, o):
        # For Date Time string spec, see ECMA 262
        # http://ecma-international.org/ecma-262/5.1/#sec-15.9.1.15
        if isinstance(o, Promise):
            return force_text(o)
        elif isinstance(o, datetime.datetime):
            r = o.isoformat()
            if o.microsecond:
                r = r[:23] + r[26:]
            if r.endswith('+00:00'):
                r = r[:-6] + 'Z'
            return r
        elif isinstance(o, datetime.date):
            return o.isoformat()
        elif isinstance(o, datetime.time):
            if timezone and timezone.is_aware(o):
                raise ValueError("JSON can't represent timezone-aware times.")
            r = o.isoformat()
            if o.microsecond:
                r = r[:12]
            return r
        elif isinstance(o, datetime.timedelta):
            return str(o.total_seconds())
        elif isinstance(o, decimal.Decimal):
            return str(o)
        elif isinstance(o, QuerySet):
            return list(o)
        elif hasattr(o, 'tolist'):
            return o.tolist()
        elif hasattr(o, '__getitem__'):
            try:
                return dict(o)
            except:
                pass
        elif hasattr(o, '__iter__'):
            return [i for i in o]
        return super(JSONEncoder, self).default(o)


try:
    import yaml
except ImportError:
    SafeDumper = None
else:
    # Adapted from http://pyyaml.org/attachment/ticket/161/use_ordered_dict.py
    class SafeDumper(yaml.SafeDumper):
        """
        Handles decimals as strings.
        Handles SortedDicts as usual dicts, but preserves field order, rather
        than the usual behaviour of sorting the keys.
        """
        def represent_decimal(self, data):
            return self.represent_scalar('tag:yaml.org,2002:str', str(data))

        def represent_mapping(self, tag, mapping, flow_style=None):
            value = []
            node = yaml.MappingNode(tag, value, flow_style=flow_style)
            if self.alias_key is not None:
                self.represented_objects[self.alias_key] = node
            best_style = True
            if hasattr(mapping, 'items'):
                mapping = list(mapping.items())
                if not isinstance(mapping, SortedDict):
                    mapping.sort()
            for item_key, item_value in mapping:
                node_key = self.represent_data(item_key)
                node_value = self.represent_data(item_value)
                if not (isinstance(node_key, yaml.ScalarNode) and not node_key.style):
                    best_style = False
                if not (isinstance(node_value, yaml.ScalarNode) and not node_value.style):
                    best_style = False
                value.append((node_key, node_value))
            if flow_style is None:
                if self.default_flow_style is not None:
                    node.flow_style = self.default_flow_style
                else:
                    node.flow_style = best_style
            return node

    SafeDumper.add_representer(decimal.Decimal,
            SafeDumper.represent_decimal)

    SafeDumper.add_representer(SortedDict,
            yaml.representer.SafeRepresenter.represent_dict)
    SafeDumper.add_representer(DictWithMetadata,
            yaml.representer.SafeRepresenter.represent_dict)
    SafeDumper.add_representer(SortedDictWithMetadata,
            yaml.representer.SafeRepresenter.represent_dict)
    SafeDumper.add_representer(types.GeneratorType,
            yaml.representer.SafeRepresenter.represent_list)

########NEW FILE########
__FILENAME__ = formatting
"""
Utility functions to return a formatted name and description for a given view.
"""
from __future__ import unicode_literals

from django.utils.html import escape
from django.utils.safestring import mark_safe
from rest_framework.compat import apply_markdown
from rest_framework.settings import api_settings
from textwrap import dedent
import re


def remove_trailing_string(content, trailing):
    """
    Strip trailing component `trailing` from `content` if it exists.
    Used when generating names from view classes.
    """
    if content.endswith(trailing) and content != trailing:
        return content[:-len(trailing)]
    return content


def dedent(content):
    """
    Remove leading indent from a block of text.
    Used when generating descriptions from docstrings.

    Note that python's `textwrap.dedent` doesn't quite cut it,
    as it fails to dedent multiline docstrings that include
    unindented text on the initial line.
    """
    whitespace_counts = [len(line) - len(line.lstrip(' '))
                         for line in content.splitlines()[1:] if line.lstrip()]

    # unindent the content if needed
    if whitespace_counts:
        whitespace_pattern = '^' + (' ' * min(whitespace_counts))
        content = re.sub(re.compile(whitespace_pattern, re.MULTILINE), '', content)

    return content.strip()

def camelcase_to_spaces(content):
    """
    Translate 'CamelCaseNames' to 'Camel Case Names'.
    Used when generating names from view classes.
    """
    camelcase_boundry = '(((?<=[a-z])[A-Z])|([A-Z](?![A-Z]|$)))'
    content = re.sub(camelcase_boundry, ' \\1', content).strip()
    return ' '.join(content.split('_')).title()

def markup_description(description):
    """
    Apply HTML markup to the given description.
    """
    if apply_markdown:
        description = apply_markdown(description)
    else:
        description = escape(description).replace('\n', '<br />')
    return mark_safe(description)

########NEW FILE########
__FILENAME__ = mediatypes
"""
Handling of media types, as found in HTTP Content-Type and Accept headers.

See http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.7
"""
from __future__ import unicode_literals
from django.http.multipartparser import parse_header
from rest_framework import HTTP_HEADER_ENCODING


def media_type_matches(lhs, rhs):
    """
    Returns ``True`` if the media type in the first argument <= the
    media type in the second argument.  The media types are strings
    as described by the HTTP spec.

    Valid media type strings include:

    'application/json; indent=4'
    'application/json'
    'text/*'
    '*/*'
    """
    lhs = _MediaType(lhs)
    rhs = _MediaType(rhs)
    return lhs.match(rhs)


def order_by_precedence(media_type_lst):
    """
    Returns a list of sets of media type strings, ordered by precedence.
    Precedence is determined by how specific a media type is:

    3. 'type/subtype; param=val'
    2. 'type/subtype'
    1. 'type/*'
    0. '*/*'
    """
    ret = [set(), set(), set(), set()]
    for media_type in media_type_lst:
        precedence = _MediaType(media_type).precedence
        ret[3 - precedence].add(media_type)
    return [media_types for media_types in ret if media_types]


class _MediaType(object):
    def __init__(self, media_type_str):
        if media_type_str is None:
            media_type_str = ''
        self.orig = media_type_str
        self.full_type, self.params = parse_header(media_type_str.encode(HTTP_HEADER_ENCODING))
        self.main_type, sep, self.sub_type = self.full_type.partition('/')

    def match(self, other):
        """Return true if this MediaType satisfies the given MediaType."""
        for key in self.params.keys():
            if key != 'q' and other.params.get(key, None) != self.params.get(key, None):
                return False

        if self.sub_type != '*' and other.sub_type != '*'  and other.sub_type != self.sub_type:
            return False

        if self.main_type != '*' and other.main_type != '*' and other.main_type != self.main_type:
            return False

        return True

    @property
    def precedence(self):
        """
        Return a precedence level from 0-3 for the media type given how specific it is.
        """
        if self.main_type == '*':
            return 0
        elif self.sub_type == '*':
            return 1
        elif not self.params or list(self.params.keys()) == ['q']:
            return 2
        return 3

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        ret = "%s/%s" % (self.main_type, self.sub_type)
        for key, val in self.params.items():
            ret += "; %s=%s" % (key, val)
        return ret

########NEW FILE########
__FILENAME__ = views
"""
Provides an APIView class that is the base of all views in REST framework.
"""
from __future__ import unicode_literals

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils.datastructures import SortedDict
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, exceptions
from rest_framework.compat import smart_text, HttpResponseBase, View
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.utils import formatting


def get_view_name(view_cls, suffix=None):
    """
    Given a view class, return a textual name to represent the view.
    This name is used in the browsable API, and in OPTIONS responses.

    This function is the default for the `VIEW_NAME_FUNCTION` setting.
    """
    name = view_cls.__name__
    name = formatting.remove_trailing_string(name, 'View')
    name = formatting.remove_trailing_string(name, 'ViewSet')
    name = formatting.camelcase_to_spaces(name)
    if suffix:
        name += ' ' + suffix

    return name

def get_view_description(view_cls, html=False):
    """
    Given a view class, return a textual description to represent the view.
    This name is used in the browsable API, and in OPTIONS responses.

    This function is the default for the `VIEW_DESCRIPTION_FUNCTION` setting.
    """
    description = view_cls.__doc__ or ''
    description = formatting.dedent(smart_text(description))
    if html:
        return formatting.markup_description(description)
    return description


def exception_handler(exc):
    """
    Returns the response that should be used for any given exception.

    By default we handle the REST framework `APIException`, and also
    Django's builtin `Http404` and `PermissionDenied` exceptions.

    Any unhandled exceptions may return `None`, which will cause a 500 error
    to be raised.
    """
    if isinstance(exc, exceptions.APIException):
        headers = {}
        if getattr(exc, 'auth_header', None):
            headers['WWW-Authenticate'] = exc.auth_header
        if getattr(exc, 'wait', None):
            headers['X-Throttle-Wait-Seconds'] = '%d' % exc.wait

        return Response({'detail': exc.detail},
                        status=exc.status_code,
                        headers=headers)

    elif isinstance(exc, Http404):
        return Response({'detail': 'Not found'},
                        status=status.HTTP_404_NOT_FOUND)

    elif isinstance(exc, PermissionDenied):
        return Response({'detail': 'Permission denied'},
                        status=status.HTTP_403_FORBIDDEN)

    # Note: Unhandled exceptions will raise a 500 error.
    return None


class APIView(View):

    # The following policies may be set at either globally, or per-view.
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES
    parser_classes = api_settings.DEFAULT_PARSER_CLASSES
    authentication_classes = api_settings.DEFAULT_AUTHENTICATION_CLASSES
    throttle_classes = api_settings.DEFAULT_THROTTLE_CLASSES
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES
    content_negotiation_class = api_settings.DEFAULT_CONTENT_NEGOTIATION_CLASS

    # Allow dependancy injection of other settings to make testing easier.
    settings = api_settings

    @classmethod
    def as_view(cls, **initkwargs):
        """
        Store the original class on the view function.

        This allows us to discover information about the view when we do URL
        reverse lookups.  Used for breadcrumb generation.
        """
        view = super(APIView, cls).as_view(**initkwargs)
        view.cls = cls
        return view

    @property
    def allowed_methods(self):
        """
        Wrap Django's private `_allowed_methods` interface in a public property.
        """
        return self._allowed_methods()

    @property
    def default_response_headers(self):
        headers = {
            'Allow': ', '.join(self.allowed_methods),
        }
        if len(self.renderer_classes) > 1:
            headers['Vary'] = 'Accept'
        return headers


    def http_method_not_allowed(self, request, *args, **kwargs):
        """
        If `request.method` does not correspond to a handler method,
        determine what kind of exception to raise.
        """
        raise exceptions.MethodNotAllowed(request.method)

    def permission_denied(self, request):
        """
        If request is not permitted, determine what kind of exception to raise.
        """
        if not request.successful_authenticator:
            raise exceptions.NotAuthenticated()
        raise exceptions.PermissionDenied()

    def throttled(self, request, wait):
        """
        If request is throttled, determine what kind of exception to raise.
        """
        raise exceptions.Throttled(wait)

    def get_authenticate_header(self, request):
        """
        If a request is unauthenticated, determine the WWW-Authenticate
        header to use for 401 responses, if any.
        """
        authenticators = self.get_authenticators()
        if authenticators:
            return authenticators[0].authenticate_header(request)

    def get_parser_context(self, http_request):
        """
        Returns a dict that is passed through to Parser.parse(),
        as the `parser_context` keyword argument.
        """
        # Note: Additionally `request` and `encoding` will also be added
        #       to the context by the Request object.
        return {
            'view': self,
            'args': getattr(self, 'args', ()),
            'kwargs': getattr(self, 'kwargs', {})
        }

    def get_renderer_context(self):
        """
        Returns a dict that is passed through to Renderer.render(),
        as the `renderer_context` keyword argument.
        """
        # Note: Additionally 'response' will also be added to the context,
        #       by the Response object.
        return {
            'view': self,
            'args': getattr(self, 'args', ()),
            'kwargs': getattr(self, 'kwargs', {}),
            'request': getattr(self, 'request', None)
        }

    def get_view_name(self):
        """
        Return the view name, as used in OPTIONS responses and in the
        browsable API.
        """
        func = self.settings.VIEW_NAME_FUNCTION
        return func(self.__class__, getattr(self, 'suffix', None))

    def get_view_description(self, html=False):
        """
        Return some descriptive text for the view, as used in OPTIONS responses
        and in the browsable API.
        """
        func = self.settings.VIEW_DESCRIPTION_FUNCTION
        return func(self.__class__, html)

    # API policy instantiation methods

    def get_format_suffix(self, **kwargs):
        """
        Determine if the request includes a '.json' style format suffix
        """
        if self.settings.FORMAT_SUFFIX_KWARG:
            return kwargs.get(self.settings.FORMAT_SUFFIX_KWARG)

    def get_renderers(self):
        """
        Instantiates and returns the list of renderers that this view can use.
        """
        return [renderer() for renderer in self.renderer_classes]

    def get_parsers(self):
        """
        Instantiates and returns the list of parsers that this view can use.
        """
        return [parser() for parser in self.parser_classes]

    def get_authenticators(self):
        """
        Instantiates and returns the list of authenticators that this view can use.
        """
        return [auth() for auth in self.authentication_classes]

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        return [permission() for permission in self.permission_classes]

    def get_throttles(self):
        """
        Instantiates and returns the list of throttles that this view uses.
        """
        return [throttle() for throttle in self.throttle_classes]

    def get_content_negotiator(self):
        """
        Instantiate and return the content negotiation class to use.
        """
        if not getattr(self, '_negotiator', None):
            self._negotiator = self.content_negotiation_class()
        return self._negotiator

    # API policy implementation methods

    def perform_content_negotiation(self, request, force=False):
        """
        Determine which renderer and media type to use render the response.
        """
        renderers = self.get_renderers()
        conneg = self.get_content_negotiator()

        try:
            return conneg.select_renderer(request, renderers, self.format_kwarg)
        except Exception:
            if force:
                return (renderers[0], renderers[0].media_type)
            raise

    def perform_authentication(self, request):
        """
        Perform authentication on the incoming request.

        Note that if you override this and simply 'pass', then authentication
        will instead be performed lazily, the first time either
        `request.user` or `request.auth` is accessed.
        """
        request.user

    def check_permissions(self, request):
        """
        Check if the request should be permitted.
        Raises an appropriate exception if the request is not permitted.
        """
        for permission in self.get_permissions():
            if not permission.has_permission(request, self):
                self.permission_denied(request)

    def check_object_permissions(self, request, obj):
        """
        Check if the request should be permitted for a given object.
        Raises an appropriate exception if the request is not permitted.
        """
        for permission in self.get_permissions():
            if not permission.has_object_permission(request, self, obj):
                self.permission_denied(request)

    def check_throttles(self, request):
        """
        Check if request should be throttled.
        Raises an appropriate exception if the request is throttled.
        """
        for throttle in self.get_throttles():
            if not throttle.allow_request(request, self):
                self.throttled(request, throttle.wait())

    # Dispatch methods

    def initialize_request(self, request, *args, **kwargs):
        """
        Returns the initial request object.
        """
        parser_context = self.get_parser_context(request)

        return Request(request,
                       parsers=self.get_parsers(),
                       authenticators=self.get_authenticators(),
                       negotiator=self.get_content_negotiator(),
                       parser_context=parser_context)

    def initial(self, request, *args, **kwargs):
        """
        Runs anything that needs to occur prior to calling the method handler.
        """
        self.format_kwarg = self.get_format_suffix(**kwargs)

        # Ensure that the incoming request is permitted
        self.perform_authentication(request)
        self.check_permissions(request)
        self.check_throttles(request)

        # Perform content negotiation and store the accepted info on the request
        neg = self.perform_content_negotiation(request)
        request.accepted_renderer, request.accepted_media_type = neg

    def finalize_response(self, request, response, *args, **kwargs):
        """
        Returns the final response object.
        """
        # Make the error obvious if a proper response is not returned
        assert isinstance(response, HttpResponseBase), (
            'Expected a `Response`, `HttpResponse` or `HttpStreamingResponse` '
            'to be returned from the view, but received a `%s`'
            % type(response)
        )

        if isinstance(response, Response):
            if not getattr(request, 'accepted_renderer', None):
                neg = self.perform_content_negotiation(request, force=True)
                request.accepted_renderer, request.accepted_media_type = neg

            response.accepted_renderer = request.accepted_renderer
            response.accepted_media_type = request.accepted_media_type
            response.renderer_context = self.get_renderer_context()

        for key, value in self.headers.items():
            response[key] = value

        return response

    def handle_exception(self, exc):
        """
        Handle any exception that occurs, by returning an appropriate response,
        or re-raising the error.
        """
        if isinstance(exc, (exceptions.NotAuthenticated,
                            exceptions.AuthenticationFailed)):
            # WWW-Authenticate header for 401 responses, else coerce to 403
            auth_header = self.get_authenticate_header(self.request)

            if auth_header:
                exc.auth_header = auth_header
            else:
                exc.status_code = status.HTTP_403_FORBIDDEN

        response = self.settings.EXCEPTION_HANDLER(exc)

        if response is None:
            raise

        response.exception = True
        return response

    # Note: session based authentication is explicitly CSRF validated,
    # all other authentication is CSRF exempt.
    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        """
        `.dispatch()` is pretty much the same as Django's regular dispatch,
        but with extra hooks for startup, finalize, and exception handling.
        """
        self.args = args
        self.kwargs = kwargs
        request = self.initialize_request(request, *args, **kwargs)
        self.request = request
        self.headers = self.default_response_headers  # deprecate?

        try:
            self.initial(request, *args, **kwargs)

            # Get the appropriate handler method
            if request.method.lower() in self.http_method_names:
                handler = getattr(self, request.method.lower(),
                                  self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed

            response = handler(request, *args, **kwargs)

        except Exception as exc:
            response = self.handle_exception(exc)

        self.response = self.finalize_response(request, response, *args, **kwargs)
        return self.response

    def options(self, request, *args, **kwargs):
        """
        Handler method for HTTP 'OPTIONS' request.
        We may as well implement this as Django will otherwise provide
        a less useful default implementation.
        """
        return Response(self.metadata(request), status=status.HTTP_200_OK)

    def metadata(self, request):
        """
        Return a dictionary of metadata about the view.
        Used to return responses for OPTIONS requests.
        """
        # By default we can't provide any form-like information, however the
        # generic views override this implementation and add additional
        # information for POST and PUT methods, based on the serializer.
        ret = SortedDict()
        ret['name'] = self.get_view_name()
        ret['description'] = self.get_view_description()
        ret['renders'] = [renderer.media_type for renderer in self.renderer_classes]
        ret['parses'] = [parser.media_type for parser in self.parser_classes]
        return ret

########NEW FILE########
__FILENAME__ = viewsets
"""
ViewSets are essentially just a type of class based view, that doesn't provide
any method handlers, such as `get()`, `post()`, etc... but instead has actions,
such as `list()`, `retrieve()`, `create()`, etc...

Actions are only bound to methods at the point of instantiating the views.

    user_list = UserViewSet.as_view({'get': 'list'})
    user_detail = UserViewSet.as_view({'get': 'retrieve'})

Typically, rather than instantiate views from viewsets directly, you'll
register the viewset with a router and let the URL conf be determined
automatically.

    router = DefaultRouter()
    router.register(r'users', UserViewSet, 'user')
    urlpatterns = router.urls
"""
from __future__ import unicode_literals

from functools import update_wrapper
from django.utils.decorators import classonlymethod
from rest_framework import views, generics, mixins


class ViewSetMixin(object):
    """
    This is the magic.

    Overrides `.as_view()` so that it takes an `actions` keyword that performs
    the binding of HTTP methods to actions on the Resource.

    For example, to create a concrete view binding the 'GET' and 'POST' methods
    to the 'list' and 'create' actions...

    view = MyViewSet.as_view({'get': 'list', 'post': 'create'})
    """

    @classonlymethod
    def as_view(cls, actions=None, **initkwargs):
        """
        Because of the way class based views create a closure around the
        instantiated view, we need to totally reimplement `.as_view`,
        and slightly modify the view function that is created and returned.
        """
        # The suffix initkwarg is reserved for identifing the viewset type
        # eg. 'List' or 'Instance'.
        cls.suffix = None

        # sanitize keyword arguments
        for key in initkwargs:
            if key in cls.http_method_names:
                raise TypeError("You tried to pass in the %s method name as a "
                                "keyword argument to %s(). Don't do that."
                                % (key, cls.__name__))
            if not hasattr(cls, key):
                raise TypeError("%s() received an invalid keyword %r" % (
                    cls.__name__, key))

        def view(request, *args, **kwargs):
            self = cls(**initkwargs)
            # We also store the mapping of request methods to actions,
            # so that we can later set the action attribute.
            # eg. `self.action = 'list'` on an incoming GET request.
            self.action_map = actions

            # Bind methods to actions
            # This is the bit that's different to a standard view
            for method, action in actions.items():
                handler = getattr(self, action)
                setattr(self, method, handler)

            # Patch this in as it's otherwise only present from 1.5 onwards
            if hasattr(self, 'get') and not hasattr(self, 'head'):
                self.head = self.get

            # And continue as usual
            return self.dispatch(request, *args, **kwargs)

        # take name and docstring from class
        update_wrapper(view, cls, updated=())

        # and possible attributes set by decorators
        # like csrf_exempt from dispatch
        update_wrapper(view, cls.dispatch, assigned=())

        # We need to set these on the view function, so that breadcrumb
        # generation can pick out these bits of information from a
        # resolved URL.
        view.cls = cls
        view.suffix = initkwargs.get('suffix', None)
        return view

    def initialize_request(self, request, *args, **kargs):
        """
        Set the `.action` attribute on the view,
        depending on the request method.
        """
        request = super(ViewSetMixin, self).initialize_request(request, *args, **kargs)
        self.action = self.action_map.get(request.method.lower())
        return request


class ViewSet(ViewSetMixin, views.APIView):
    """
    The base ViewSet class does not provide any actions by default.
    """
    pass


class GenericViewSet(ViewSetMixin, generics.GenericAPIView):
    """
    The GenericViewSet class does not provide any actions by default,
    but does include the base set of generic view behavior, such as
    the `get_object` and `get_queryset` methods.
    """
    pass


class ReadOnlyModelViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           GenericViewSet):
    """
    A viewset that provides default `list()` and `retrieve()` actions.
    """
    pass


class ModelViewSet(mixins.CreateModelMixin,
                    mixins.RetrieveModelMixin,
                    mixins.UpdateModelMixin,
                    mixins.DestroyModelMixin,
                    mixins.ListModelMixin,
                    GenericViewSet):
    """
    A viewset that provides default `create()`, `retrieve()`, `update()`,
    `partial_update()`, `destroy()` and `list()` actions.
    """
    pass

########NEW FILE########
