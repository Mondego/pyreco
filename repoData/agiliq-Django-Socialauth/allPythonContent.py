__FILENAME__ = models
from django.db import models

class Comment(models.Model):
    comment = models.TextField()

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from commentor.models import Comment
from django.template import RequestContext
from django import forms
from django.shortcuts import render_to_response

@login_required
def leave_comment(request):
    form = CommentForm()
    if request.POST:
        form = CommentForm(data = request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('.')
        
    payload = {'form':form, 'comments':Comment.objects.all()}
    return render_to_response('commentor/index.html', payload, RequestContext(request))
    
class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
########NEW FILE########
__FILENAME__ = admin
from models import Post
from django.contrib import admin

admin.site.register(Post)


########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class Post(models.Model):
    author = models.ForeignKey(User)
    date = models.DateTimeField()
    title = models.CharField(max_length=100)
    post = models.TextField()

    def __unicode__(self):
        return  self.title

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from models import Post

urlpatterns = patterns('',
    url(r'^(?P<post_id>\d+)$', 'example.views.post_detail'),
    url(r'^$', 'django.views.generic.list_detail.object_list',
        { 'queryset' : Post.objects.all() }
    ),
)

########NEW FILE########
__FILENAME__ = views
# Create your views here.
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect
from django.contrib.comments.models import Comment
from models import Post
from django.template import RequestContext

def comment_posted(request):
    comment_id = request.GET['c']
    post_id = Comment.objects.get(id=comment_id).content_object.id
    return HttpResponseRedirect('/blog/'+str(post_id))

def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    return render_to_response('example/post_detail.html', {'post': post}, context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = views
# Create your views here.

from django.contrib.auth.decorators import login_required
from django.contrib.comments.views.comments import post_comment as old_post_comment

@login_required
def post_comment(request):
        return old_post_comment(request)

########NEW FILE########
__FILENAME__ = localsettings.example
OPENID_REDIRECT_NEXT = '/accounts/openid/done/'

OPENID_SREG = {"requred": "nickname, email, fullname",
               "optional":"postcode, country",
               "policy_url": ""}

#example should be something more like the real thing, i think
OPENID_AX = [{"type_uri": "http://axschema.org/contact/email",
              "count": 1,
              "required": True,
              "alias": "email"},
             {"type_uri": "http://axschema.org/schema/fullname",
              "count":1 ,
              "required": False,
              "alias": "fname"}]

OPENID_AX_PROVIDER_MAP = {'Google': {'email': 'http://axschema.org/contact/email',
                                     'firstname': 'http://axschema.org/namePerson/first',
                                     'lastname': 'http://axschema.org/namePerson/last'},
                          'Default': {'email': 'http://axschema.org/contact/email',
                                      'fullname': 'http://axschema.org/namePerson',
                                      'nickname': 'http://axschema.org/namePerson/friendly'}
                          }

TWITTER_CONSUMER_KEY = ''
TWITTER_CONSUMER_SECRET = ''

FACEBOOK_APP_ID = ''
FACEBOOK_API_KEY = ''
FACEBOOK_SECRET_KEY = ''

LINKEDIN_CONSUMER_KEY = ''
LINKEDIN_CONSUMER_SECRET = ''

GITHUB_CLIENT_ID = ''
GITHUB_CLIENT_SECRET = ''

FOURSQUARE_CONSUMER_KEY = ''
FOURSQUARE_CONSUMER_SECRET = ''
FOURSQUARE_REGISTERED_REDIRECT_URI = ''

## if any of this information is desired for your app
FACEBOOK_EXTENDED_PERMISSIONS = (
    #'publish_stream',
    #'create_event',
    #'rsvp_event',
    #'sms',
    #'offline_access',
    #'email',
    #'read_stream',
    #'user_about_me',
    #'user_activites',
    #'user_birthday',
    #'user_education_history',
    #'user_events',
    #'user_groups',
    #'user_hometown',
    #'user_interests',
    #'user_likes',
    #'user_location',
    #'user_notes',
    #'user_online_presence',
    #'user_photo_video_tags',
    #'user_photos',
    #'user_relationships',
    #'user_religion_politics',
    #'user_status',
    #'user_videos',
    #'user_website',
    #'user_work_history',
    #'read_friendlists',
    #'read_requests',
    #'friend_about_me',
    #'friend_activites',
    #'friend_birthday',
    #'friend_education_history',
    #'friend_events',
    #'friend_groups',
    #'friend_hometown',
    #'friend_interests',
    #'friend_likes',
    #'friend_location',
    #'friend_notes',
    #'friend_online_presence',
    #'friend_photo_video_tags',
    #'friend_photos',
    #'friend_relationships',
    #'friend_religion_politics',
    #'friend_status',
    #'friend_videos',
    #'friend_website',
    #'friend_work_history',
)


AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'socialauth.auth_backends.OpenIdBackend',
    'socialauth.auth_backends.TwitterBackend',
    'socialauth.auth_backends.FacebookBackend',
    'socialauth.auth_backends.LinkedInBackend',
    'socialauth.auth_backends.GithubBackend',
    'socialauth.auth_backends.FoursquareBackend',
)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for socialauthdemo project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'data.db'              # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'tnrm*t2b80nu51mgz3kc2%_v6bv8e)8rup$03m)dp7xb0)m8t9'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'openid_consumer.middleware.OpenIDMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    #'socialauth.middleware.FacebookConnectMiddleware'
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "socialauth.context_processors.facebook_api_key",
    'django.core.context_processors.media',
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.request",
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
    'django.contrib.admin',
    'django.contrib.comments',
    'socialauth',
    'openid_consumer',
    'commentor',
    'example',
    'example_comments',
)

COMMENTS_APP = 'example_comments'

LOGIN_REDIRECT_URL = '/'

LOGOUT_REDIRECT_URL = '/'

try:
    from localsettings import *
except ImportError:
    pass

import os
MEDIA_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media'))
MEDIA_URL = '/site_media/'

SITE_NAME = 'foobar'

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from commentor.views import leave_comment

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^blog/', include('example.urls')),
    (r'^accounts/', include('socialauth.urls')),
    (r'^admin/', admin.site.urls), 
    #(r'^$', leave_comment), 
    (r'^$', 'socialauth.views.signin_complete'),
    (r'^comments/post/', 'example_comments.views.post_comment'),
    (r'comments/', include('django.contrib.comments.urls')),
)

from django.conf import settings
if settings.DEBUG:
    
    urlpatterns += patterns('',
        # This is for the CSS and static files:
        (r'^site_media/(?P<path>.*)$', 'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT}),
    )
    

########NEW FILE########
__FILENAME__ = middleware
class OpenIDMiddleware(object):
    """
    Populate request.openid and request.openids with their openid. This comes 
    either from their cookie or from their session, depending on the presence 
    of OPENID_USE_SESSIONS.
    """
    def process_request(self, request):
        request.openids = request.session.get('openids', [])
        if request.openids:
            request.openid = request.openids[-1] # Last authenticated OpenID
        else:
            request.openid = None

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Nonce(models.Model):
    server_url = models.URLField()
    timestamp  = models.IntegerField()
    salt       = models.CharField( max_length=50 )

    def __unicode__(self):
        return "Nonce: %s" % self.nonce

class Association(models.Model):
    server_url = models.TextField(max_length=2047)
    handle = models.CharField(max_length=255)
    secret = models.TextField(max_length=255) # Stored base64 encoded
    issued = models.IntegerField()
    lifetime = models.IntegerField()
    assoc_type = models.TextField(max_length=64)

    def __unicode__(self):
        return "Association: %s, %s" % (self.server_url, self.handle)

########NEW FILE########
__FILENAME__ = util
import openid
if openid.__version__ < '2.1.0':
    from openid.sreg import SRegResponse
else:
    from openid.extensions.sreg import SRegResponse
    from openid.extensions.ax import FetchResponse as AXFetchResponse
    try:
        from openid.extensions.pape import Response as PapeResponse
    except ImportError:
        from openid.extensions import pape as openid_pape
        PapeResponse = openid_pape.Response

from openid.store import nonce as oid_nonce
from openid.store.interface import OpenIDStore
from openid.association import Association as OIDAssociation
from openid.yadis import xri

import time, base64, hashlib

from django.conf import settings
from models import Association, Nonce

class OpenID:
    def __init__(self, openid, issued,
                  attrs=None, sreg=None, pape=None, ax=None):
        self.openid = openid
        self.issued = issued
        self.attrs = attrs or {}
        self.sreg = sreg or {}
        self.pape = pape or {}
        self.ax = ax or {}
        self.is_iname = (xri.identifierScheme(openid) == 'XRI')
    
    def __repr__(self):
        return '<OpenID: %s>' % self.openid
    
    def __str__(self):
        return self.openid

class DjangoOpenIDStore(OpenIDStore):
    def __init__(self):
        self.max_nonce_age = 6 * 60 * 60 # Six hours
    
    def storeAssociation(self, server_url, association):
        assoc = Association(
            server_url = server_url,
            handle = association.handle,
            secret = base64.encodestring(association.secret),
            issued = association.issued,
            lifetime = association.issued,
            assoc_type = association.assoc_type
        )
        assoc.save()
    
    def getAssociation(self, server_url, handle=None):
        assocs = []
        if handle is not None:
            assocs = Association.objects.filter(
                server_url = server_url, handle = handle
            )
        else:
            assocs = Association.objects.filter(
                server_url = server_url
            )
        if not assocs:
            return None
        associations = []
        for assoc in assocs:
            association = OIDAssociation(
                assoc.handle, base64.decodestring(assoc.secret), assoc.issued,
                assoc.lifetime, assoc.assoc_type
            )
            if association.getExpiresIn() == 0:
                self.removeAssociation(server_url, assoc.handle)
            else:
                associations.append((association.issued, association))
        if not associations:
            return None
        return associations[-1][1]
    
    def removeAssociation(self, server_url, handle):
        assocs = list(Association.objects.filter(
            server_url = server_url, handle = handle
        ))
        assocs_exist = len(assocs) > 0
        for assoc in assocs:
            assoc.delete()
        return assocs_exist
    
    def storeNonce(self, nonce):
        nonce, created = Nonce.objects.get_or_create(
            nonce = nonce, defaults={'expires': int(time.time())}
        )
    
    def useNonce(self, server_url, timestamp, salt):
        if abs(timestamp - time.time()) > oid_nonce.SKEW:
            return False
        
        try:
            nonce = Nonce(server_url=server_url,
                          timestamp=timestamp,
                          salt=salt)
            nonce.save()
        except:
            raise
        else:
            return 1
    
    def getAuthKey(self):
        # Use first AUTH_KEY_LEN characters of md5 hash of SECRET_KEY
        return hashlib.md5(settings.SECRET_KEY).hexdigest()[:self.AUTH_KEY_LEN]

def from_openid_response(openid_response):
    issued = int(time.time())

    openid = OpenID(openid_response.identity_url, issued,
                    openid_response.signed_fields)

    if getattr(settings, 'OPENID_PAPE', False):
        openid.pape = PapeResponse.fromSuccessResponse(openid_response)

    if getattr(settings, 'OPENID_SREG', False):
        openid.sreg = SRegResponse.fromSuccessResponse(openid_response)

    if getattr(settings, 'OPENID_AX', False):
        openid.ax = AXFetchResponse.fromSuccessResponse(openid_response)

    return openid

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response as render
from django.template import RequestContext
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

import re, time, urllib

import openid   
if openid.__version__ < '2.0.0':
    raise ImportError, 'You need python-openid 2.0.0 or newer'
elif openid.__version__ < '2.1.0':
    from openid.sreg import SRegRequest
else: 
    from openid.extensions.sreg import SRegRequest
    try:
        from openid.extensions.pape import Request as PapeRequest
    except ImportError:
        from openid.extensions import pape as openid_pape
        PapeRequest =  openid_pape.Request
    from openid.extensions.ax import FetchRequest as AXFetchRequest
    from openid.extensions.ax import AttrInfo

from openid.consumer.consumer import Consumer, \
    SUCCESS, CANCEL, FAILURE, SETUP_NEEDED
from openid.consumer.discover import DiscoveryFailure
from openid.yadis import xri

from util import OpenID, DjangoOpenIDStore, from_openid_response
from middleware import OpenIDMiddleware

from django.utils.html import escape

def get_url_host(request):
    if request.is_secure():
        protocol = 'https'
    else:
        protocol = 'http'
    host = escape(request.get_host())
    return '%s://%s' % (protocol, host)

def get_full_url(request):
    return get_url_host(request) + request.get_full_path()
		
next_url_re = re.compile('^/[-\w/]+$')

def is_valid_next_url(next):
    # When we allow this:
    #   /openid/?next=/welcome/
    # For security reasons we want to restrict the next= bit to being a local 
    # path, not a complete URL.
    return bool(next_url_re.match(next))

def begin(request, redirect_to=None, on_failure=None, user_url=None,
          template_name='openid_consumer/signin.html'):
    on_failure = on_failure or default_on_failure
    trust_root = getattr(
        settings, 'OPENID_TRUST_ROOT', get_url_host(request) + '/'
    )
    
    
    # foo derbis.
    redirect_to = redirect_to or getattr(
        settings, 'OPENID_REDIRECT_TO',
        # If not explicitly set, assume current URL with complete/ appended
        get_full_url(request).split('?')[0] + 'complete/'
    )
    # In case they were lazy...
    if not (
            redirect_to.startswith('http://')
        or
            redirect_to.startswith('https://')):
        redirect_to =  get_url_host(request) + redirect_to
    
    if request.GET.get('next') and is_valid_next_url(request.GET['next']):
        if '?' in redirect_to:
            join = '&'
        else:
            join = '?'
        redirect_to += join + urllib.urlencode({
            'next': request.GET['next']
        })
    if not user_url:
        user_url = request.REQUEST.get('openid_url', None)

    if not user_url:
        request_path = request.path
        if request.GET.get('next'):
            request_path += '?' + urllib.urlencode({
                'next': request.GET['next']
            })
        
        return render(template_name, {
            'action': request_path,
        }, RequestContext(request))
    
    if xri.identifierScheme(user_url) == 'XRI' and getattr(
        settings, 'OPENID_DISALLOW_INAMES', False
        ):
        return on_failure(request, _('i-names are not supported'))
    
    consumer = Consumer(request.session, DjangoOpenIDStore())

    try:
        auth_request = consumer.begin(user_url)
    except DiscoveryFailure:
        return on_failure(request, _('The OpenID was invalid'))
    
    sreg = getattr(settings, 'OPENID_SREG', False)
    
    if sreg:
        s = SRegRequest()        
        for sarg in sreg:
            if sarg.lower().lstrip() == "policy_url":
                s.policy_url = sreg[sarg]
            else:
                for v in sreg[sarg].split(','):
                    s.requestField(field_name=v.lower().lstrip(),
                                   required=(sarg.lower().lstrip() ==
                                             "required"))
        auth_request.addExtension(s)
    
    pape = getattr(settings, 'OPENID_PAPE', False)

    if pape:
        if openid.__version__ <= '2.0.0' and openid.__version__ >= '2.1.0':
            raise (ImportError, 
                   'For pape extension you need python-openid 2.1.0 or newer')
        p = PapeRequest()
        for parg in pape:
            if parg.lower().strip() == 'policy_list':
                for v in pape[parg].split(','):
                    p.addPolicyURI(v)
            elif parg.lower().strip() == 'max_auth_age':
                p.max_auth_age = pape[parg]
        auth_request.addExtension(p)
    
    OPENID_AX_PROVIDER_MAP = getattr(settings, 'OPENID_AX_PROVIDER_MAP', {})
    
    openid_provider = ('Google' if 
                       'google' in request.session.get('openid_provider', '')
                       else 'Default')
    ax = OPENID_AX_PROVIDER_MAP.get(openid_provider)
    
    if ax:
        axr = AXFetchRequest()
        for attr_name, attr_url in ax.items():
            # axr.add(AttrInfo(i['type_uri'], 
            #    i['count'], i['required'], 
            #    i['alias']))
            
            # setting all as required attrs
            axr.add(AttrInfo(attr_url, required=True))
        auth_request.addExtension(axr)
    
    redirect_url = auth_request.redirectURL(trust_root, redirect_to)
    
    return HttpResponseRedirect(redirect_url)

def complete(request, on_success=None, on_failure=None, 
             failure_template='openid_consumer/failure.html'):
    
    on_success = on_success or default_on_success
    on_failure = on_failure or default_on_failure
    
    consumer = Consumer(request.session, DjangoOpenIDStore())
    #dummydebug
    #for r in request.GET.items():
    #    print r

    # JanRain library raises a warning if passed unicode objects as the keys,
    # so we convert to bytestrings before passing to the library
    query_dict = dict([
        (k.encode('utf8'),
         v.encode('utf8')) for k, v in request.REQUEST.items()
    ])

    url = get_url_host(request) + request.path
    openid_response = consumer.complete(query_dict, url)
    if openid_response.status == SUCCESS:
        return on_success(request,
                          openid_response.identity_url,
                          openid_response)
    elif openid_response.status == CANCEL:
        return on_failure(request, 
                          _('The request was cancelled'), failure_template)
    elif openid_response.status == FAILURE:
        return on_failure(request, openid_response.message, failure_template)
    elif openid_response.status == SETUP_NEEDED:
        return on_failure(request, _('Setup needed'), failure_template)
    else:
        assert False, "Bad openid status: %s" % openid_response.status

def default_on_success(request, identity_url, openid_response):
    if 'openids' not in request.session.keys():
        request.session['openids'] = []
    
    # Eliminate any duplicates
    request.session['openids'] = [
        o for o in request.session['openids'] if o.openid != identity_url
    ]
    request.session['openids'].append(from_openid_response(openid_response))
    
    # Set up request.openids and request.openid, reusing middleware logic
    OpenIDMiddleware().process_request(request)
    
    next = request.GET.get('next', '').strip()
    if not next or not is_valid_next_url(next):
        next = getattr(settings, 'OPENID_REDIRECT_NEXT', '/')
    
    return HttpResponseRedirect(next)

def default_on_failure(request, message,
                       template_name='openid_consumer/failure.html'):
    return render(template_name, {
        'message': message
    }, 		RequestContext(request))

def signout(request):
    request.session['openids'] = []
    next = request.GET.get('next', '/')
    if not is_valid_next_url(next):
        next = '/'
    return HttpResponseRedirect(next)

########NEW FILE########
__FILENAME__ = admin
from socialauth.models import AuthMeta, OpenidProfile, TwitterUserProfile, \
FacebookUserProfile, LinkedInUserProfile, GithubUserProfile, FoursquareUserProfile

from django.contrib import admin

admin.site.register(AuthMeta)
admin.site.register(OpenidProfile)
admin.site.register(TwitterUserProfile)
admin.site.register(FacebookUserProfile)
admin.site.register(LinkedInUserProfile)
admin.site.register(GithubUserProfile)
admin.site.register(FoursquareUserProfile)

########NEW FILE########
__FILENAME__ = auth_backends
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.conf import settings
import facebook

import urllib
from socialauth.lib import oauthtwitter2 as oauthtwitter
from socialauth.models import OpenidProfile as UserAssociation, \
TwitterUserProfile, FacebookUserProfile, LinkedInUserProfile, AuthMeta, GithubUserProfile, FoursquareUserProfile
from socialauth.lib.linkedin import *

import random
from cgi import parse_qs

TWITTER_CONSUMER_KEY = getattr(settings, 'TWITTER_CONSUMER_KEY', '')
TWITTER_CONSUMER_SECRET = getattr(settings, 'TWITTER_CONSUMER_SECRET', '')

FACEBOOK_APP_ID = getattr(settings, 'FACEBOOK_APP_ID', '')
FACEBOOK_API_KEY = getattr(settings, 'FACEBOOK_API_KEY', '')
FACEBOOK_SECRET_KEY = getattr(settings, 'FACEBOOK_SECRET_KEY', '')

# Linkedin
LINKEDIN_CONSUMER_KEY = getattr(settings, 'LINKEDIN_CONSUMER_KEY', '')
LINKEDIN_CONSUMER_SECRET = getattr(settings, 'LINKEDIN_CONSUMER_SECRET', '')

# OpenId setting map

OPENID_AX_PROVIDER_MAP = getattr(settings, 'OPENID_AX_PROVIDER_MAP', {})

class OpenIdBackend:
    supports_object_permissions = False
    supports_anonymous_user = False
    supports_inactive_user = False

    def authenticate(self, openid_key, request, provider, user=None):
        try:
            assoc = UserAssociation.objects.get(openid_key=openid_key)
            return assoc.user
        except UserAssociation.DoesNotExist:
            #fetch if openid provider provides any simple registration fields
            nickname = None
            email = None
            firstname = None
            lastname = None
            
            if request.openid and request.openid.sreg:
                email = request.openid.sreg.get('email')
                nickname = request.openid.sreg.get('nickname')
                firstname, lastname = (request.openid.sreg
                                       .get('fullname', ' ')
                                       .split(' ', 1))
            elif request.openid and request.openid.ax:
                email = \
                    (request.openid.ax
                     .getSingle('http://axschema.org/contact/email'))
                if 'google' in provider:
                    ax_schema = OPENID_AX_PROVIDER_MAP['Google']
                    firstname = (request.openid.ax
                                 .getSingle(ax_schema['firstname']))
                    lastname = (request.openid.ax
                                .getSingle(ax_schema['lastname']))
                    nickname = email.split('@')[0]
                else:
                    ax_schema = OPENID_AX_PROVIDER_MAP['Default']
                    try:
                         #should be replaced by correct schema
                        nickname = (request.openid.ax
                                    .getSingle(ax_schema['nickname']))
                        (firstname, 
                            lastname) = (request.openid.ax
                                         .getSingle(ax_schema['fullname'])
                                         .split(' ', 1))
                    except:
                        pass

            if nickname is None :
                nickname =  ''.join(
                                    [random
                                     .choice('abcdefghijklmnopqrstuvwxyz')
                                     for i in xrange(10)])
            
            name_count = (User.objects
                          .filter(username__startswith=nickname)
                          .count())
            if name_count:
                username = '%s%d' % (nickname, name_count + 1)
            else:
                username = '%s' % (nickname)
                
            if email is None :
                valid_username = False
                email =  "%s@socialauth" % (username)
            else:
                valid_username = True
            
            if not user:
                user = User.objects.create_user(username, email)
                
            user.first_name = firstname
            user.last_name = lastname
            user.save()
    
            #create openid association
            assoc = UserAssociation()
            assoc.openid_key = openid_key
            assoc.user = user
            if email:
                assoc.email = email
            if nickname:
                assoc.nickname = nickname
            if valid_username:
                assoc.is_username_valid = True
            assoc.save()
            
            #Create AuthMeta
            # auth_meta = 
            #             AuthMeta(user=user, 
            #                        provider=provider, 
            #                        provider_model='OpenidProfile', 
            #                        provider_id=assoc.pk)
            auth_meta = AuthMeta(user=user, provider=provider)
            auth_meta.save()
            return user
        
    def GooglesAX(self,openid_response):
        email = (openid_response.ax
                 .getSingle('http://axschema.org/contact/email'))
        firstname = (openid_response.ax
                     .getSingle('http://axschema.org/namePerson/first'))
        lastname = (openid_response.ax
                    .getSingle('http://axschema.org/namePerson/last'))
        # country = 
        #    (openid_response.ax
        #        .getSingle('http://axschema.org/contact/country/home'))
        # language = 
        #    openid_response.ax.getSingle('http://axschema.org/pref/language')
        return locals()
  
    def get_user(self, user_id):
        try:
            user = User.objects.get(pk=user_id)
            return user
        except User.DoesNotExist:
            return None

class LinkedInBackend:
    """LinkedInBackend for authentication"""
    def authenticate(self, linkedin_access_token, user=None):
        linkedin = LinkedIn(LINKEDIN_CONSUMER_KEY, LINKEDIN_CONSUMER_SECRET)
        # get their profile
        
        profile = (ProfileApi(linkedin)
                   .getMyProfile(access_token=linkedin_access_token))

        try:
            user_profile = (LinkedInUserProfile.objects
                            .get(linkedin_uid=profile.id))
            user = user_profile.user
            return user
        except LinkedInUserProfile.DoesNotExist:
            # Create a new user
            username = 'LI:%s' % profile.id

            if not user:
                user = User(username=username)
                user.first_name, user.last_name = (profile.firstname
                                                   , profile.lastname)
                user.email = '%s@socialauth' % (username)
                user.save()
                
            userprofile = LinkedInUserProfile(user=user, 
                                              linkedin_uid=profile.id)
            userprofile.save()
            
            auth_meta = AuthMeta(user=user, provider='LinkedIn').save()
            return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except:
            return None

class TwitterBackend:
    """TwitterBackend for authentication"""
    def authenticate(self, twitter_access_token, user=None):
        '''
            authenticates the token by requesting user information
            from twitter
        '''
        # twitter = oauthtwitter.OAuthApi(TWITTER_CONSUMER_KEY,
        #                                  TWITTER_CONSUMER_SECRET,
        #                                  twitter_access_token)
        twitter = oauthtwitter.TwitterOAuthClient(
                                            settings.TWITTER_CONSUMER_KEY,
                                            settings.TWITTER_CONSUMER_SECRET)
        try:
            userinfo = twitter.get_user_info(twitter_access_token)
        except:
            # If we cannot get the user information, 
            # user cannot be authenticated
            raise

        screen_name = userinfo.screen_name
        twitter_id = userinfo.id
        
        try:
            user_profile = (TwitterUserProfile.objects
                            .get(screen_name=screen_name))
            
            # Update Twitter Profile
            user_profile.url = userinfo.url
            user_profile.location = userinfo.location
            user_profile.description = userinfo.description
            user_profile.profile_image_url = userinfo.profile_image_url
            user_profile.save()
            
            user = user_profile.user
            return user
        except TwitterUserProfile.DoesNotExist:
            # Create new user
            if not user:
                same_name_count = (User.objects
                                   .filter(username__startswith=screen_name)
                                   .count())
                if same_name_count:
                    username = '%s%s' % (screen_name, same_name_count + 1)
                else:
                    username = screen_name
                user = User(username=username)
                name_data = userinfo.name.split()
                try:
                    first_name, last_name = (name_data[0], 
                                            ' '.join(name_data[1:]))
                except:
                    first_name, last_name =  screen_name, ''
                user.first_name, user.last_name = first_name, last_name
                #user.email = screen_name + "@socialauth"
                #user.email = '%s@example.twitter.com'%(userinfo.screen_name)
                user.save()
                
            user_profile = TwitterUserProfile(user=user, 
                                              screen_name=screen_name)
            user_profile.access_token = str(twitter_access_token)
            user_profile.url = userinfo.url
            user_profile.location = userinfo.location
            user_profile.description = userinfo.description
            user_profile.profile_image_url = userinfo.profile_image_url
            user_profile.save()
            
            auth_meta = AuthMeta(user=user, provider='Twitter').save()
                
            return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except:
            return None
        
class FacebookBackend:
    def authenticate(self, request, user=None):
        cookie = facebook.get_user_from_cookie(request.COOKIES,
                                               FACEBOOK_APP_ID,
                                               FACEBOOK_SECRET_KEY)
        if cookie:
            uid = cookie['uid']
            access_token = cookie['access_token']
        else:
            # if cookie does not exist
            # assume logging in normal way
            params = {}
            params["client_id"] = FACEBOOK_APP_ID
            params["client_secret"] = FACEBOOK_SECRET_KEY
            params["redirect_uri"] = '%s://%s%s' % (
                         'https' if request.is_secure() else 'http',
                         Site.objects.get_current().domain,
                         reverse("socialauth_facebook_login_done"))
            params["code"] = request.GET.get('code', '')

            url = ("https://graph.facebook.com/oauth/access_token?"
                   + urllib.urlencode(params))
            from cgi import parse_qs
            userdata = urllib.urlopen(url).read()
            res_parse_qs = parse_qs(userdata)
            # Could be a bot query
            if not res_parse_qs.has_key('access_token'):
                return None
                
            access_token = res_parse_qs['access_token'][-1]
            
            graph = facebook.GraphAPI(access_token)
            uid = graph.get_object('me')['id']
            
        try:
            fb_user = FacebookUserProfile.objects.get(facebook_uid=uid)
            return fb_user.user

        except FacebookUserProfile.DoesNotExist:
            
            # create new FacebookUserProfile
            graph = facebook.GraphAPI(access_token) 
            fb_data = graph.get_object("me")

            if not fb_data:
                return None

            username = uid
            if not user:
                user = User.objects.create(username=username)
                user.first_name = fb_data['first_name']
                user.last_name = fb_data['last_name']
                user.save()
                
            fb_profile = FacebookUserProfile(facebook_uid=uid, user=user)
            fb_profile.save()
            
            auth_meta = AuthMeta(user=user, provider='Facebook').save()
                
            return user

    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except:
            return None

class GithubBackend:
    def authenticate(self, github_access_token, user=None):
        response_qs = parse_qs(github_access_token)
        github_access_token = response_qs['access_token'][0]
        try:
            github_user = GithubUserProfile.objects.get(access_token=github_access_token)
            return github_user.user
        except GithubUserProfile.DoesNotExist:
            github_user_count = GithubUserProfile.objects.all().count()
            username = "GithubUser:" + str(github_user_count+1)
            user = User(username=username)
            user.save()
            github_user = GithubUserProfile(user=user, access_token=github_access_token)
            github_user.save()
            AuthMeta(user=user, provider='Github').save() 
            return github_user.user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except:
            return None

class FoursquareBackend:
    def authenticate(self, foursquare_access_token):
        try:
            foursquare_profile = FoursquareUserProfile.objects.get(access_token=foursquare_access_token)
            return foursquare_profile.user 
        except FoursquareUserProfile.DoesNotExist:
            foursquare_user_count = FoursquareUserProfile.objects.all().count()
            username = "FoursquareUser:" + str(foursquare_user_count+1)
            user = User(username=username)
            user.save()
            foursquare_user = FoursquareUserProfile(user=user, access_token=foursquare_access_token)
            foursquare_user.save()
            AuthMeta(user=user, provider='Foursquare').save()
            return foursquare_user.user 

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except:
            return None

########NEW FILE########
__FILENAME__ = context_processors
from django.conf import settings


def facebook_api_key(request):
    FACEBOOK_APP_ID = getattr(settings, 'FACEBOOK_APP_ID', '')
    FACEBOOK_API_KEY = getattr(settings, 'FACEBOOK_API_KEY', '')
    FACEBOOK_EXTENDED_PERMISSIONS = getattr(settings, 
                                            'FACEBOOK_EXTENDED_PERMISSIONS',
                                            '')
    
    if FACEBOOK_APP_ID:
        return {'FACEBOOK_APP_ID': FACEBOOK_APP_ID,
                'FACEBOOK_API_KEY': FACEBOOK_API_KEY, 
                'login_button_perms': ','.join(FACEBOOK_EXTENDED_PERMISSIONS)}
    else:
        return {}

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.conf import settings

from socialauth.models import AuthMeta


ALLOW_MULTIPLE_USERNAME_EDITS = getattr(settings,
                                        'ALLOW_MULTIPLE_USERNAME_EDITS',
                                        False)

class EditProfileForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(max_length=100, widget=forms.PasswordInput,
                               required=False,
                               help_text='If you give a password, you can \
                               login via a login form as well.')
    password2 = forms.CharField(max_length=100, widget=forms.PasswordInput,
                                required=False,
                                label='Repeat password')
    first_name = forms.CharField(max_length=100, required=False)
    last_name = forms.CharField(max_length=100, required=False)
    
    def __init__(self, user=None, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.user = user
        if self.user:
            self.initial = {'email': user.email,  \
                            'first_name':user.first_name,
                            'last_name':user.last_name}
            
    def clean(self):
        cleaned_data = self.cleaned_data
        if 'password' in cleaned_data or 'password2' in cleaned_data:
            if 'password' in cleaned_data and 'password2' in cleaned_data:
                if cleaned_data['password'] != cleaned_data['password2']:
                    raise forms.ValidationError('The passwords do not match.')
            else:
                raise forms.ValidationError('Either ener both or None of the\
                                            password fields')

        return cleaned_data
        
    def save(self):
        user = self.user
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if ('password' in self.cleaned_data 
            and 
            'password2' in self.cleaned_data):
            user.set_password(self.cleaned_data['password'])
        user.save()
        try:
            authmeta = user.authmeta
            authmeta.is_email_filled = True
            authmeta.is_profile_modified = True
            authmeta.save()
        except AuthMeta.DoesNotExist:
            pass
        return user
        
        

########NEW FILE########
__FILENAME__ = facebook
import md5
import urllib
import time
try:
    import json as simplejson
except:
    from django.utils import simplejson

REST_SERVER = 'http://api.facebook.com/restserver.php'


def get_user_info(api_key, api_secret, cookies):
    user_info_params = {
                        'method': 'Users.getInfo',
                        'api_key': api_key,
                        'call_id': time.time(),
                        'v': '1.0',
                        'uids': cookies[api_key + '_user'],
                        'fields': 'uid,first_name,last_name,pic_small, name, current_location',
                        'format': 'json',
                       }

    user_info_hash = get_facebook_signature(api_key, api_secret, user_info_params)
    user_info_params['sig'] = user_info_hash            
    user_info_params = urllib.urlencode(user_info_params)
    user_info_response  = simplejson.load(urllib.urlopen(REST_SERVER, user_info_params))
    return user_info_response

def get_friends(api_key, api_secret, cookies):
    params = {
        'method': 'Friends.get',
        'api_key': api_key,
        'call_id': time.time(),
        'v': '1.0',
        'format': 'json',
    }
    return talk_to_fb(api_key, api_secret, params)

def get_friends_via_fql(api_key, api_secret, cookies):
    query = 'SELECT name, uid, pic_small  FROM user WHERE uid IN (SELECT uid2 FROM friend WHERE uid1 = %s)' % cookies[api_key + '_user']
    params = {
        'method': 'Fql.query',
        'session_key': cookies[api_key + '_session_key'],
        'query': query,
        'api_key': api_key,
        'call_id': time.time(),
        'v': '1.0',
        'uid': cookies[api_key + '_user'],
        'format': 'json',
    }
    return talk_to_fb(api_key, api_secret, params)

    
def talk_to_fb(api_key, api_secret, params):
    sig = get_facebook_signature(api_key, api_secret, params)
    params['sig'] = sig
    data = urllib.urlencode(params)
    response = simplejson.load(urllib.urlopen(REST_SERVER, data))
    return response

    
def get_facebook_signature(api_key, api_secret, values_dict, is_cookie_check=False):
        API_KEY = api_key
        API_SECRET = api_secret
        signature_keys = []
        for key in sorted(values_dict.keys()):
            if (is_cookie_check and key.startswith(API_KEY + '_')):
                signature_keys.append(key)
            elif (is_cookie_check is False):
                signature_keys.append(key)

        if (is_cookie_check):
            signature_string = ''.join(['%s=%s' % (x.replace(API_KEY + '_',''), values_dict[x]) for x in signature_keys])
        else:
            signature_string = ''.join(['%s=%s' % (x, values_dict[x]) for x in signature_keys])
        signature_string = signature_string + API_SECRET

        return md5.new(signature_string).hexdigest()
    
    
    

########NEW FILE########
__FILENAME__ = foursquare
from oauth import oauth
from django.conf import settings
import httplib

FOURSQUARE_AUTHENTICATION_URL = 'https://foursquare.com/oauth2/authenticate'
FOURSQUARE_ACCESS_TOKEN_URL = 'https://foursquare.com/oauth2/access_token'
FOURSQUARE_CONSUMER_KEY = getattr(settings, 'FOURSQUARE_CONSUMER_KEY')
FOURSQUARE_CONSUMER_SECRET = getattr(settings, 'FOURSQUARE_CONSUMER_SECRET')
REGISTERED_REDIRECT_URI = getattr(settings, 'FOURSQUARE_REGISTERED_REDIRECT_URI')

def get_http_connection():
    return httplib.HTTPSConnection('foursquare.com')

def get_response_body(oauth_request):
    http_conn = get_http_connection()
    http_conn.request('GET', oauth_request.to_url())
    response = http_conn.getresponse().read()
    return response
    

class FourSquareClient(object):
    def __init__(self):
        self.consumer = oauth.OAuthConsumer(FOURSQUARE_CONSUMER_KEY, FOURSQUARE_CONSUMER_SECRET)

    def get_authentication_url(self):
        parameters = {}
        parameters['client_id'] = FOURSQUARE_CONSUMER_KEY 
        parameters['response_type'] = 'code'
        parameters['redirect_uri'] = REGISTERED_REDIRECT_URI
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer, http_url=FOURSQUARE_AUTHENTICATION_URL, parameters=parameters)
        return oauth_request.to_url()

    def get_access_token(self, foursquare_code):
        parameters = {}
        parameters['client_id'] = FOURSQUARE_CONSUMER_KEY
        parameters['client_secret'] = FOURSQUARE_CONSUMER_SECRET
        parameters['grant_type'] = 'authorization_code' 
        parameters['redirect_uri'] = REGISTERED_REDIRECT_URI
        parameters['code'] = foursquare_code
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer, http_url=FOURSQUARE_ACCESS_TOKEN_URL, parameters=parameters)
        access_token_response = get_response_body(oauth_request) 
        return access_token_response

########NEW FILE########
__FILENAME__ = github
from django.conf import settings 
from oauth.oauth import OAuthConsumer, OAuthRequest 
import httplib

GITHUB_CLIENT_ID = getattr(settings, 'GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = getattr(settings, 'GITHUB_CLIENT_SECRET')
GITHUB_AUTHORIZE_URL = 'https://github.com/login/oauth/authorize'
GITHUB_ACCESS_TOKEN_URL = 'https://github.com/login/oauth/access_token'

def get_response_from_url(to_url):
    conn = httplib.HTTPSConnection('github.com')
    conn.request('GET', to_url)
    return conn.getresponse().read()

class GithubClient(object):
    def __init__(self):
        self.consumer = OAuthConsumer(GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET)

    def get_authorize_url(self):
        parameters = {'client_id':GITHUB_CLIENT_ID}
        oauth_request = OAuthRequest.from_consumer_and_token(self.consumer, http_url=GITHUB_AUTHORIZE_URL, parameters=parameters)
        return oauth_request.to_url()

    def get_access_token(self, code):
        parameters = {}
        parameters['client_id'] = GITHUB_CLIENT_ID
        parameters['client_secret'] = GITHUB_CLIENT_SECRET
        parameters['code'] = code
        oauth_request = OAuthRequest.from_consumer_and_token(self.consumer, http_url=GITHUB_ACCESS_TOKEN_URL, parameters=parameters)
        access_token = get_response_from_url(oauth_request.to_url())       
        return access_token

########NEW FILE########
__FILENAME__ = linkedin
"""
LinkedIn OAuth Api Access 
Version: 0.01
License: MIT
Author: Max Lynch <max@mendotasoft.com>
Website: http://mendotasoft.com, http://maxlynch.com
Date Release: 11/23/2009

Enjoy!
"""

import hashlib
import urllib2
import httplib

import time

from xml.dom.minidom import parseString

import oauth.oauth as oauth

class LinkedIn():
    LI_SERVER = "api.linkedin.com"
    LI_API_URL = "https://api.linkedin.com"

    REQUEST_TOKEN_URL = LI_API_URL + "/uas/oauth/requestToken"
    AUTHORIZE_URL = LI_API_URL + "/uas/oauth/authorize"
    ACCESS_TOKEN_URL = LI_API_URL + "/uas/oauth/accessToken"



    def __init__(self, api_key, secret_key):
        self.api_key = api_key
        self.secret_key = secret_key

        self.connection = httplib.HTTPSConnection(self.LI_SERVER)
        self.consumer = oauth.OAuthConsumer(api_key, secret_key)
        self.sig_method = oauth.OAuthSignatureMethod_HMAC_SHA1()

        self.status_api = StatusApi(self)
        self.connections_api = ConnectionsApi(self)

    def getRequestToken(self, callback):
        """
        Get a request token from linkedin
        """
        oauth_consumer_key = self.api_key

        oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer,
                        callback=callback,
                        http_url = self.REQUEST_TOKEN_URL)
        oauth_request.sign_request(self.sig_method, self.consumer, None)


        self.connection.request(oauth_request.http_method,
                        self.REQUEST_TOKEN_URL, headers = oauth_request.to_header())
        response = self.connection.getresponse().read()
        
        token = oauth.OAuthToken.from_string(response)
        return token

    def getAuthorizeUrl(self, token):
        """
        Get the URL that we can redirect the user to for authorization of our
        application.
        """
        oauth_request = oauth.OAuthRequest.from_token_and_callback(token=token, http_url = self.AUTHORIZE_URL)
        return oauth_request.to_url()

    def getAccessToken(self, token, verifier):
        """
        Using the verifier we obtained through the user's authorization of
        our application, get an access code.

        Note: token is the request token returned from the call to getRequestToken

        @return an OAuthToken object with the access token.  Use it like this:
                token.key -> Key
                token.secret -> Secret Key
        """
        token.verifier = verifier
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer, token=token, verifier=verifier, http_url=self.ACCESS_TOKEN_URL)
        oauth_request.sign_request(self.sig_method, self.consumer, token)
        
        # self.connection.request(oauth_request.http_method, self.ACCESS_TOKEN_URL, headers=oauth_request.to_header()) 
        self.connection.request(oauth_request.http_method, oauth_request.to_url()) 
        response = self.connection.getresponse().read()
        return oauth.OAuthToken.from_string(response)

    """
    More functionality coming soon...
    """

class LinkedInApi():
    def __init__(self, linkedin):
        self.linkedin = linkedin

    def doApiRequest(self, url, access_token):
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.linkedin.consumer, token=access_token, http_url=url)
        oauth_request.sign_request(self.linkedin.sig_method, self.linkedin.consumer, access_token)
        self.linkedin.connection.request(oauth_request.http_method, url, headers=oauth_request.to_header())
        return self.linkedin.connection.getresponse().read()


class StatusApi(LinkedInApi):
    STATUS_SELF_URL = LinkedIn.LI_API_URL + "/v1/people/~:(current-status)"
    
    def __init__(self, linkedin):
        LinkedInApi.__init__(self, linkedin)
    
    def getMyStatus(self, access_token):
        return self.doApiRequest(self.STATUS_SELF_URL, access_token)

class ProfileApi(LinkedInApi):
    """
    Get a LinkedIn Profile
    """
    PROFILE_SELF = LinkedIn.LI_API_URL + r"/v1/people/~:(id,first-name,last-name,headline,industry,picture-url,site-standard-profile-request)"
    
    def __init__(self, linkedin):
        LinkedInApi.__init__(self, linkedin)

    def getMyProfile(self, access_token):
        xml = self.doApiRequest(self.PROFILE_SELF, access_token)
        dom = parseString(xml)
        personDom = dom.getElementsByTagName('person')

        p = personDom[0]

        fn=ln=picurl=headline=company=industry=profurl=""

        try:
            id = p.getElementsByTagName('id')[0].firstChild.nodeValue
            fn = p.getElementsByTagName('first-name')[0].firstChild.nodeValue
            ln = p.getElementsByTagName('last-name')[0].firstChild.nodeValue
            picurl = p.getElementsByTagName('picture-url')[0].firstChild.nodeValue

            headline = p.getElementsByTagName('headline')[0].firstChild.nodeValue
            if ' at ' in headline:
                company = headline.split(' at ')[1]
            industry = p.getElementsByTagName('industry')[0].firstChild.nodeValue
            #location = p.getElementsByTagName('industry')[0].firstChild.nodeValue
            profurl = p.getElementsByTagName('url')[0].firstChild.nodeValue
        except:
            pass

        person = Person()
        person.id = id
        person.firstname = fn
        person.lastname = ln
        person.headline = headline
        person.company = company
        person.industry = industry
        person.picture_url = picurl
        person.profile_url = profurl

        return person

class ConnectionsApi(LinkedInApi):
    """
    How to get all of a user's connections:

            Note: This should happen after the linkedin redirect.  verifier is passed
            by LinkedIn back to your redirect page

            li = LinkedIn(LINKEDIN_CONSUMER_KEY, LINKEDIN_CONSUMER_SECRET)

            tokenObj = oauth.OAuthToken(requestTokenKey, requestTokenSecret)
            access_token = li.getAccessToken(tokenObj, verifier)

            connections = li.connections_api.getMyConnections(access_token)

            for c in connections:
                    # Access c.firstname, c.lastname, etc.
    """

    CONNECTIONS_SELF = LinkedIn.LI_API_URL + "/v1/people/~/connections"
    def __init__(self, linkedin):
        LinkedInApi.__init__(self, linkedin)
        
    def getMyConnections(self, access_token):
        xml = self.doApiRequest(self.CONNECTIONS_SELF, access_token)
        dom = parseString(xml)
        peopleDom = dom.getElementsByTagName('person')

        people = []

        for p in peopleDom:
            try:
                fn = p.getElementsByTagName('first-name')[0].firstChild.nodeValue
                ln = p.getElementsByTagName('last-name')[0].firstChild.nodeValue
                headline = p.getElementsByTagName('headline')[0].firstChild.nodeValue
                company = headline.split(' at ')[1]
                industry = p.getElementsByTagName('industry')[0].firstChild.nodeValue
                #location = p.getElementsByTagName('industry')[0].firstChild.nodeValue
                person = Person()
                person.firstname = fn
                person.lastname = ln
                person.headline = headline
                person.company = company
                person.industry = industry
                people.append(person)
            except:
                continue
        return people

class Person():
    id = ""
    firstname = ""
    lastname = ""
    headline = ""
    company = ""
    location = None
    industry = ""
    picture_url = ""
    profile_url = ""

    def __str__(self):
        return "%s %s working at %s" % (self.firstname, self.lastname, self.company)

class Location():
    name = ""
    country = ""

########NEW FILE########
__FILENAME__ = oauth1
"""
The MIT License

Copyright (c) 2007 Leah Culver

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import cgi
import urllib
import time
import random
import urlparse
import hmac
import binascii


VERSION = '1.0' # Hi Blaine!
HTTP_METHOD = 'GET'
SIGNATURE_METHOD = 'PLAINTEXT'


class OAuthError(RuntimeError):
    """Generic exception class."""
    def __init__(self, message='OAuth error occured.'):
        self.message = message

def build_authenticate_header(realm=''):
    """Optional WWW-Authenticate header (401 error)"""
    return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

def escape(s):
    """Escape a URL including any /."""
    return urllib.quote(s, safe='~')

def _utf8_str(s):
    """Convert unicode to utf-8."""
    if isinstance(s, unicode):
        return s.encode("utf-8")
    else:
        return str(s)

def generate_timestamp():
    """Get seconds since epoch (UTC)."""
    return int(time.time())

def generate_nonce(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])

def generate_verifier(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


class OAuthConsumer(object):
    """Consumer of OAuth authentication.

    OAuthConsumer is a data type that represents the identity of the Consumer
    via its shared secret with the Service Provider.

    """
    key = None
    secret = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret


class OAuthToken(object):
    """OAuthToken is a data type that represents an End User via either an access
    or request token.
    
    key -- the token
    secret -- the token secret

    """
    key = None
    secret = None
    callback = None
    callback_confirmed = None
    verifier = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

    def set_callback(self, callback):
        self.callback = callback
        self.callback_confirmed = 'true'

    def set_verifier(self, verifier=None):
        if verifier is not None:
            self.verifier = verifier
        else:
            self.verifier = generate_verifier()

    def get_callback_url(self):
        if self.callback and self.verifier:
            # Append the oauth_verifier.
            parts = urlparse.urlparse(self.callback)
            scheme, netloc, path, params, query, fragment = parts[:6]
            if query:
                query = '%s&oauth_verifier=%s' % (query, self.verifier)
            else:
                query = 'oauth_verifier=%s' % self.verifier
            return urlparse.urlunparse((scheme, netloc, path, params,
                query, fragment))
        return self.callback

    def to_string(self):
        data = {
            'oauth_token': self.key,
            'oauth_token_secret': self.secret,
        }
        if self.callback_confirmed is not None:
            data['oauth_callback_confirmed'] = self.callback_confirmed
        return urllib.urlencode(data)
 
    def from_string(s):
        """ Returns a token from something like:
        oauth_token_secret=xxx&oauth_token=xxx
        """
        params = cgi.parse_qs(s, keep_blank_values=False)
        key = params['oauth_token'][0]
        secret = params['oauth_token_secret'][0]
        token = OAuthToken(key, secret)
        try:
            token.callback_confirmed = params['oauth_callback_confirmed'][0]
        except KeyError:
            pass # 1.0, no callback confirmed.
        return token
    from_string = staticmethod(from_string)

    def __str__(self):
        return self.to_string()


class OAuthRequest(object):
    """OAuthRequest represents the request and can be serialized.

    OAuth parameters:
        - oauth_consumer_key 
        - oauth_token
        - oauth_signature_method
        - oauth_signature 
        - oauth_timestamp 
        - oauth_nonce
        - oauth_version
        - oauth_verifier
        ... any additional parameters, as defined by the Service Provider.
    """
    parameters = None # OAuth parameters.
    http_method = HTTP_METHOD
    http_url = None
    version = VERSION

    def __init__(self, http_method=HTTP_METHOD, http_url=None, parameters=None):
        self.http_method = http_method
        self.http_url = http_url
        self.parameters = parameters or {}

    def set_parameter(self, parameter, value):
        self.parameters[parameter] = value

    def get_parameter(self, parameter):
        try:
            return self.parameters[parameter]
        except:
            raise OAuthError('Parameter not found: %s' % parameter)

    def _get_timestamp_nonce(self):
        return self.get_parameter('oauth_timestamp'), self.get_parameter(
            'oauth_nonce')

    def get_nonoauth_parameters(self):
        """Get any non-OAuth parameters."""
        parameters = {}
        for k, v in self.parameters.iteritems():
            # Ignore oauth parameters.
            if k.find('oauth_') < 0:
                parameters[k] = v
        return parameters

    def to_header(self, realm=''):
        """Serialize as a header for an HTTPAuth request."""
        auth_header = 'OAuth realm="%s"' % realm
        # Add the oauth parameters.
        if self.parameters:
            for k, v in self.parameters.iteritems():
                if k[:6] == 'oauth_':
                    auth_header += ', %s="%s"' % (k, escape(str(v)))
        return {'Authorization': auth_header}

    def to_postdata(self):
        """Serialize as post data for a POST request."""
        return '&'.join(['%s=%s' % (escape(str(k)), escape(str(v))) \
            for k, v in self.parameters.iteritems()])

    def to_url(self):
        """Serialize as a URL for a GET request."""
        return '%s?%s' % (self.get_normalized_http_url(), self.to_postdata())

    def get_normalized_parameters(self):
        """Return a string that contains the parameters that must be signed."""
        params = self.parameters
        try:
            # Exclude the signature if it exists.
            del params['oauth_signature']
        except:
            pass
        # Escape key values before sorting.
        key_values = [(escape(_utf8_str(k)), escape(_utf8_str(v))) \
            for k,v in params.items()]
        # Sort lexicographically, first after key, then after value.
        key_values.sort()
        # Combine key value pairs into a string.
        return '&'.join(['%s=%s' % (k, v) for k, v in key_values])

    def get_normalized_http_method(self):
        """Uppercases the http method."""
        return self.http_method.upper()

    def get_normalized_http_url(self):
        """Parses the URL and rebuilds it to be scheme://host/path."""
        parts = urlparse.urlparse(self.http_url)
        scheme, netloc, path = parts[:3]
        # Exclude default port numbers.
        if scheme == 'http' and netloc[-3:] == ':80':
            netloc = netloc[:-3]
        elif scheme == 'https' and netloc[-4:] == ':443':
            netloc = netloc[:-4]
        return '%s://%s%s' % (scheme, netloc, path)

    def sign_request(self, signature_method, consumer, token):
        """Set the signature parameter to the result of build_signature."""
        # Set the signature method.
        self.set_parameter('oauth_signature_method',
            signature_method.get_name())
        # Set the signature.
        self.set_parameter('oauth_signature',
            self.build_signature(signature_method, consumer, token))

    def build_signature(self, signature_method, consumer, token):
        """Calls the build signature method within the signature method."""
        return signature_method.build_signature(self, consumer, token)

    def from_request(http_method, http_url, headers=None, parameters=None,
            query_string=None):
        """Combines multiple parameter sources."""
        if parameters is None:
            parameters = {}

        # Headers
        if headers and 'Authorization' in headers:
            auth_header = headers['Authorization']
            # Check that the authorization header is OAuth.
            if auth_header[:6] == 'OAuth ':
                auth_header = auth_header[6:]
                try:
                    # Get the parameters from the header.
                    header_params = OAuthRequest._split_header(auth_header)
                    parameters.update(header_params)
                except:
                    raise OAuthError('Unable to parse OAuth parameters from '
                        'Authorization header.')

        # GET or POST query string.
        if query_string:
            query_params = OAuthRequest._split_url_string(query_string)
            parameters.update(query_params)

        # URL parameters.
        param_str = urlparse.urlparse(http_url)[4] # query
        url_params = OAuthRequest._split_url_string(param_str)
        parameters.update(url_params)

        if parameters:
            return OAuthRequest(http_method, http_url, parameters)

        return None
    from_request = staticmethod(from_request)

    def from_consumer_and_token(oauth_consumer, token=None,
            callback=None, verifier=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        defaults = {
            'oauth_consumer_key': oauth_consumer.key,
            'oauth_timestamp': generate_timestamp(),
            'oauth_nonce': generate_nonce(),
            'oauth_version': OAuthRequest.version,
        }

        defaults.update(parameters)
        parameters = defaults

        if token:
            parameters['oauth_token'] = token.key
            if token.callback:
                parameters['oauth_callback'] = token.callback
            # 1.0a support for verifier.
            if verifier:
                parameters['oauth_verifier'] = verifier
        elif callback:
            # 1.0a support for callback in the request token request.
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_consumer_and_token = staticmethod(from_consumer_and_token)

    def from_token_and_callback(token, callback=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        parameters['oauth_token'] = token.key

        if callback:
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_token_and_callback = staticmethod(from_token_and_callback)

    def _split_header(header):
        """Turn Authorization: header into parameters."""
        params = {}
        parts = header.split(',')
        for param in parts:
            # Ignore realm parameter.
            if param.find('realm') > -1:
                continue
            # Remove whitespace.
            param = param.strip()
            # Split key-value.
            param_parts = param.split('=', 1)
            # Remove quotes and unescape the value.
            params[param_parts[0]] = urllib.unquote(param_parts[1].strip('\"'))
        return params
    _split_header = staticmethod(_split_header)

    def _split_url_string(param_str):
        """Turn URL string into parameters."""
        parameters = cgi.parse_qs(param_str, keep_blank_values=False)
        for k, v in parameters.iteritems():
            parameters[k] = urllib.unquote(v[0])
        return parameters
    _split_url_string = staticmethod(_split_url_string)

class OAuthServer(object):
    """A worker to check the validity of a request against a data store."""
    timestamp_threshold = 300 # In seconds, five minutes.
    version = VERSION
    signature_methods = None
    data_store = None

    def __init__(self, data_store=None, signature_methods=None):
        self.data_store = data_store
        self.signature_methods = signature_methods or {}

    def set_data_store(self, data_store):
        self.data_store = data_store

    def get_data_store(self):
        return self.data_store

    def add_signature_method(self, signature_method):
        self.signature_methods[signature_method.get_name()] = signature_method
        return self.signature_methods

    def fetch_request_token(self, oauth_request):
        """Processes a request_token request and returns the
        request token on success.
        """
        try:
            # Get the request token for authorization.
            token = self._get_token(oauth_request, 'request')
        except OAuthError:
            # No token required for the initial token request.
            version = self._get_version(oauth_request)
            consumer = self._get_consumer(oauth_request)
            try:
                callback = self.get_callback(oauth_request)
            except OAuthError:
                callback = None # 1.0, no callback specified.
            self._check_signature(oauth_request, consumer, None)
            # Fetch a new token.
            token = self.data_store.fetch_request_token(consumer, callback)
        return token

    def fetch_access_token(self, oauth_request):
        """Processes an access_token request and returns the
        access token on success.
        """
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        try:
            verifier = self._get_verifier(oauth_request)
        except OAuthError:
            verifier = None
        # Get the request token.
        token = self._get_token(oauth_request, 'request')
        self._check_signature(oauth_request, consumer, token)
        new_token = self.data_store.fetch_access_token(consumer, token, verifier)
        return new_token

    def verify_request(self, oauth_request):
        """Verifies an api call and checks all the parameters."""
        # -> consumer and token
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        # Get the access token.
        token = self._get_token(oauth_request, 'access')
        self._check_signature(oauth_request, consumer, token)
        parameters = oauth_request.get_nonoauth_parameters()
        return consumer, token, parameters

    def authorize_token(self, token, user):
        """Authorize a request token."""
        return self.data_store.authorize_request_token(token, user)

    def get_callback(self, oauth_request):
        """Get the callback URL."""
        return oauth_request.get_parameter('oauth_callback')
 
    def build_authenticate_header(self, realm=''):
        """Optional support for the authenticate header."""
        return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

    def _get_version(self, oauth_request):
        """Verify the correct version request for this server."""
        try:
            version = oauth_request.get_parameter('oauth_version')
        except:
            version = VERSION
        if version and version != self.version:
            raise OAuthError('OAuth version %s not supported.' % str(version))
        return version

    def _get_signature_method(self, oauth_request):
        """Figure out the signature with some defaults."""
        try:
            signature_method = oauth_request.get_parameter(
                'oauth_signature_method')
        except:
            signature_method = SIGNATURE_METHOD
        try:
            # Get the signature method object.
            signature_method = self.signature_methods[signature_method]
        except:
            signature_method_names = ', '.join(self.signature_methods.keys())
            raise OAuthError('Signature method %s not supported try one of the '
                'following: %s' % (signature_method, signature_method_names))

        return signature_method

    def _get_consumer(self, oauth_request):
        consumer_key = oauth_request.get_parameter('oauth_consumer_key')
        consumer = self.data_store.lookup_consumer(consumer_key)
        if not consumer:
            raise OAuthError('Invalid consumer.')
        return consumer

    def _get_token(self, oauth_request, token_type='access'):
        """Try to find the token for the provided request token key."""
        token_field = oauth_request.get_parameter('oauth_token')
        token = self.data_store.lookup_token(token_type, token_field)
        if not token:
            raise OAuthError('Invalid %s token: %s' % (token_type, token_field))
        return token
    
    def _get_verifier(self, oauth_request):
        return oauth_request.get_parameter('oauth_verifier')

    def _check_signature(self, oauth_request, consumer, token):
        timestamp, nonce = oauth_request._get_timestamp_nonce()
        self._check_timestamp(timestamp)
        self._check_nonce(consumer, token, nonce)
        signature_method = self._get_signature_method(oauth_request)
        try:
            signature = oauth_request.get_parameter('oauth_signature')
        except:
            raise OAuthError('Missing signature.')
        # Validate the signature.
        valid_sig = signature_method.check_signature(oauth_request, consumer,
            token, signature)
        if not valid_sig:
            key, base = signature_method.build_signature_base_string(
                oauth_request, consumer, token)
            raise OAuthError('Invalid signature. Expected signature base '
                'string: %s' % base)
        built = signature_method.build_signature(oauth_request, consumer, token)

    def _check_timestamp(self, timestamp):
        """Verify that timestamp is recentish."""
        timestamp = int(timestamp)
        now = int(time.time())
        lapsed = abs(now - timestamp)
        if lapsed > self.timestamp_threshold:
            raise OAuthError('Expired timestamp: given %d and now %s has a '
                'greater difference than threshold %d' %
                (timestamp, now, self.timestamp_threshold))

    def _check_nonce(self, consumer, token, nonce):
        """Verify that the nonce is uniqueish."""
        nonce = self.data_store.lookup_nonce(consumer, token, nonce)
        if nonce:
            raise OAuthError('Nonce already used: %s' % str(nonce))


class OAuthClient(object):
    """OAuthClient is a worker to attempt to execute a request."""
    consumer = None
    token = None

    def __init__(self, oauth_consumer, oauth_token):
        self.consumer = oauth_consumer
        self.token = oauth_token

    def get_consumer(self):
        return self.consumer

    def get_token(self):
        return self.token

    def fetch_request_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def access_resource(self, oauth_request):
        """-> Some protected resource."""
        raise NotImplementedError


class OAuthDataStore(object):
    """A database abstraction used to lookup consumers and tokens."""

    def lookup_consumer(self, key):
        """-> OAuthConsumer."""
        raise NotImplementedError

    def lookup_token(self, oauth_consumer, token_type, token_token):
        """-> OAuthToken."""
        raise NotImplementedError

    def lookup_nonce(self, oauth_consumer, oauth_token, nonce):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_request_token(self, oauth_consumer, oauth_callback):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_consumer, oauth_token, oauth_verifier):
        """-> OAuthToken."""
        raise NotImplementedError

    def authorize_request_token(self, oauth_token, user):
        """-> OAuthToken."""
        raise NotImplementedError


class OAuthSignatureMethod(object):
    """A strategy class that implements a signature method."""
    def get_name(self):
        """-> str."""
        raise NotImplementedError

    def build_signature_base_string(self, oauth_request, oauth_consumer, oauth_token):
        """-> str key, str raw."""
        raise NotImplementedError

    def build_signature(self, oauth_request, oauth_consumer, oauth_token):
        """-> str."""
        raise NotImplementedError

    def check_signature(self, oauth_request, consumer, token, signature):
        built = self.build_signature(oauth_request, consumer, token)
        return built == signature


class OAuthSignatureMethod_HMAC_SHA1(OAuthSignatureMethod):

    def get_name(self):
        return 'HMAC-SHA1'
        
    def build_signature_base_string(self, oauth_request, consumer, token):
        sig = (
            escape(oauth_request.get_normalized_http_method()),
            escape(oauth_request.get_normalized_http_url()),
            escape(oauth_request.get_normalized_parameters()),
        )

        key = '%s&' % escape(consumer.secret)
        if token:
            key += escape(token.secret)
        raw = '&'.join(sig)
        return key, raw

    def build_signature(self, oauth_request, consumer, token):
        """Builds the base signature string."""
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)

        # HMAC object.
        try:
            import hashlib # 2.5
            hashed = hmac.new(key, raw, hashlib.sha1)
        except:
            import sha # Deprecated
            hashed = hmac.new(key, raw, sha)

        # Calculate the digest base 64.
        return binascii.b2a_base64(hashed.digest())[:-1]


class OAuthSignatureMethod_PLAINTEXT(OAuthSignatureMethod):

    def get_name(self):
        return 'PLAINTEXT'

    def build_signature_base_string(self, oauth_request, consumer, token):
        """Concatenates the consumer key and secret."""
        sig = '%s&' % escape(consumer.secret)
        if token:
            sig = sig + escape(token.secret)
        return sig, sig

    def build_signature(self, oauth_request, consumer, token):
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)
        return key
########NEW FILE########
__FILENAME__ = oauth2
"""
The MIT License

Copyright (c) 2007 Leah Culver

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import cgi
import urllib
import time
import random
import urlparse
import hmac
import binascii


VERSION = '1.0' # Hi Blaine!
HTTP_METHOD = 'GET'
SIGNATURE_METHOD = 'PLAINTEXT'


class OAuthError(RuntimeError):
    """Generic exception class."""
    def __init__(self, message='OAuth error occured.'):
        self.message = message

def build_authenticate_header(realm=''):
    """Optional WWW-Authenticate header (401 error)"""
    return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

def escape(s):
    """Escape a URL including any /."""
    return urllib.quote(s, safe='~')

def _utf8_str(s):
    """Convert unicode to utf-8."""
    if isinstance(s, unicode):
        return s.encode("utf-8")
    else:
        return str(s)

def generate_timestamp():
    """Get seconds since epoch (UTC)."""
    return int(time.time())

def generate_nonce(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


class OAuthConsumer(object):
    """Consumer of OAuth authentication.

    OAuthConsumer is a data type that represents the identity of the Consumer
    via its shared secret with the Service Provider.

    """
    key = None
    secret = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

   
class OAuthToken(object):
    """OAuthToken is a data type that represents an End User via either an access
    or request token.
    
    key -- the token
    secret -- the token secret

    """
    key = None
    secret = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

    def to_string(self):
        return urllib.urlencode({'oauth_token': self.key,
            'oauth_token_secret': self.secret})
 
    def from_string(s):
        """ Returns a token from something like:
        oauth_token_secret=xxx&oauth_token=xxx
        """
        params = cgi.parse_qs(s, keep_blank_values=False)
        key = params['oauth_token'][0]
        secret = params['oauth_token_secret'][0]
        return OAuthToken(key, secret)
    from_string = staticmethod(from_string)

    def __str__(self):
        return self.to_string()


class OAuthRequest(object):
    """OAuthRequest represents the request and can be serialized.

    OAuth parameters:
        - oauth_consumer_key 
        - oauth_token
        - oauth_signature_method
        - oauth_signature 
        - oauth_timestamp 
        - oauth_nonce
        - oauth_version
        ... any additional parameters, as defined by the Service Provider.
    """
    parameters = None # OAuth parameters.
    http_method = HTTP_METHOD
    http_url = None
    version = VERSION

    def __init__(self, http_method=HTTP_METHOD, http_url=None, parameters=None):
        self.http_method = http_method
        self.http_url = http_url
        self.parameters = parameters or {}

    def set_parameter(self, parameter, value):
        self.parameters[parameter] = value

    def get_parameter(self, parameter):
        try:
            return self.parameters[parameter]
        except:
            raise OAuthError('Parameter not found: %s' % parameter)

    def _get_timestamp_nonce(self):
        return self.get_parameter('oauth_timestamp'), self.get_parameter(
            'oauth_nonce')

    def get_nonoauth_parameters(self):
        """Get any non-OAuth parameters."""
        parameters = {}
        for k, v in self.parameters.iteritems():
            # Ignore oauth parameters.
            if k.find('oauth_') < 0:
                parameters[k] = v
        return parameters

    def to_header(self, realm=''):
        """Serialize as a header for an HTTPAuth request."""
        auth_header = 'OAuth realm="%s"' % realm
        # Add the oauth parameters.
        if self.parameters:
            for k, v in self.parameters.iteritems():
                if k[:6] == 'oauth_':
                    auth_header += ', %s="%s"' % (k, escape(str(v)))
        return {'Authorization': auth_header}

    def to_postdata(self):
        """Serialize as post data for a POST request."""
        return '&'.join(['%s=%s' % (escape(str(k)), escape(str(v))) \
            for k, v in self.parameters.iteritems()])

    def to_url(self):
        """Serialize as a URL for a GET request."""
        return '%s?%s' % (self.get_normalized_http_url(), self.to_postdata())

    def get_normalized_parameters(self):
        """Return a string that contains the parameters that must be signed."""
        params = self.parameters
        try:
            # Exclude the signature if it exists.
            del params['oauth_signature']
        except:
            pass
        # Escape key values before sorting.
        key_values = [(escape(_utf8_str(k)), escape(_utf8_str(v))) \
            for k,v in params.items()]
        # Sort lexicographically, first after key, then after value.
        key_values.sort()
        # Combine key value pairs into a string.
        return '&'.join(['%s=%s' % (k, v) for k, v in key_values])

    def get_normalized_http_method(self):
        """Uppercases the http method."""
        return self.http_method.upper()

    def get_normalized_http_url(self):
        """Parses the URL and rebuilds it to be scheme://host/path."""
        parts = urlparse.urlparse(self.http_url)
        scheme, netloc, path = parts[:3]
        # Exclude default port numbers.
        if scheme == 'http' and netloc[-3:] == ':80':
            netloc = netloc[:-3]
        elif scheme == 'https' and netloc[-4:] == ':443':
            netloc = netloc[:-4]
        return '%s://%s%s' % (scheme, netloc, path)

    def sign_request(self, signature_method, consumer, token):
        """Set the signature parameter to the result of build_signature."""
        # Set the signature method.
        self.set_parameter('oauth_signature_method',
            signature_method.get_name())
        # Set the signature.
        self.set_parameter('oauth_signature',
            self.build_signature(signature_method, consumer, token))

    def build_signature(self, signature_method, consumer, token):
        """Calls the build signature method within the signature method."""
        return signature_method.build_signature(self, consumer, token)

    def from_request(http_method, http_url, headers=None, parameters=None,
            query_string=None):
        """Combines multiple parameter sources."""
        if parameters is None:
            parameters = {}

        # Headers
        if headers and 'Authorization' in headers:
            auth_header = headers['Authorization']
            # Check that the authorization header is OAuth.
            if auth_header.index('OAuth') > -1:
                auth_header = auth_header.lstrip('OAuth ')
                try:
                    # Get the parameters from the header.
                    header_params = OAuthRequest._split_header(auth_header)
                    parameters.update(header_params)
                except:
                    raise OAuthError('Unable to parse OAuth parameters from '
                        'Authorization header.')

        # GET or POST query string.
        if query_string:
            query_params = OAuthRequest._split_url_string(query_string)
            parameters.update(query_params)

        # URL parameters.
        param_str = urlparse.urlparse(http_url)[4] # query
        url_params = OAuthRequest._split_url_string(param_str)
        parameters.update(url_params)

        if parameters:
            return OAuthRequest(http_method, http_url, parameters)

        return None
    from_request = staticmethod(from_request)

    def from_consumer_and_token(oauth_consumer, token=None,
            http_method=HTTP_METHOD, http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        defaults = {
            'oauth_consumer_key': oauth_consumer.key,
            'oauth_timestamp': generate_timestamp(),
            'oauth_nonce': generate_nonce(),
            'oauth_version': OAuthRequest.version,
        }

        defaults.update(parameters)
        parameters = defaults

        if token:
            parameters['oauth_token'] = token.key

        return OAuthRequest(http_method, http_url, parameters)
    from_consumer_and_token = staticmethod(from_consumer_and_token)

    def from_token_and_callback(token, callback=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        parameters['oauth_token'] = token.key

        if callback:
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_token_and_callback = staticmethod(from_token_and_callback)

    def _split_header(header):
        """Turn Authorization: header into parameters."""
        params = {}
        parts = header.split(',')
        for param in parts:
            # Ignore realm parameter.
            if param.find('realm') > -1:
                continue
            # Remove whitespace.
            param = param.strip()
            # Split key-value.
            param_parts = param.split('=', 1)
            # Remove quotes and unescape the value.
            params[param_parts[0]] = urllib.unquote(param_parts[1].strip('\"'))
        return params
    _split_header = staticmethod(_split_header)

    def _split_url_string(param_str):
        """Turn URL string into parameters."""
        parameters = cgi.parse_qs(param_str, keep_blank_values=False)
        for k, v in parameters.iteritems():
            parameters[k] = urllib.unquote(v[0])
        return parameters
    _split_url_string = staticmethod(_split_url_string)

class OAuthServer(object):
    """A worker to check the validity of a request against a data store."""
    timestamp_threshold = 300 # In seconds, five minutes.
    version = VERSION
    signature_methods = None
    data_store = None

    def __init__(self, data_store=None, signature_methods=None):
        self.data_store = data_store
        self.signature_methods = signature_methods or {}

    def set_data_store(self, data_store):
        self.data_store = data_store

    def get_data_store(self):
        return self.data_store

    def add_signature_method(self, signature_method):
        self.signature_methods[signature_method.get_name()] = signature_method
        return self.signature_methods

    def fetch_request_token(self, oauth_request):
        """Processes a request_token request and returns the
        request token on success.
        """
        try:
            # Get the request token for authorization.
            token = self._get_token(oauth_request, 'request')
        except OAuthError:
            # No token required for the initial token request.
            version = self._get_version(oauth_request)
            consumer = self._get_consumer(oauth_request)
            self._check_signature(oauth_request, consumer, None)
            # Fetch a new token.
            token = self.data_store.fetch_request_token(consumer)
        return token

    def fetch_access_token(self, oauth_request):
        """Processes an access_token request and returns the
        access token on success.
        """
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        # Get the request token.
        token = self._get_token(oauth_request, 'request')
        self._check_signature(oauth_request, consumer, token)
        new_token = self.data_store.fetch_access_token(consumer, token)
        return new_token

    def verify_request(self, oauth_request):
        """Verifies an api call and checks all the parameters."""
        # -> consumer and token
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        # Get the access token.
        token = self._get_token(oauth_request, 'access')
        self._check_signature(oauth_request, consumer, token)
        parameters = oauth_request.get_nonoauth_parameters()
        return consumer, token, parameters

    def authorize_token(self, token, user):
        """Authorize a request token."""
        return self.data_store.authorize_request_token(token, user)

    def get_callback(self, oauth_request):
        """Get the callback URL."""
        return oauth_request.get_parameter('oauth_callback')
 
    def build_authenticate_header(self, realm=''):
        """Optional support for the authenticate header."""
        return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

    def _get_version(self, oauth_request):
        """Verify the correct version request for this server."""
        try:
            version = oauth_request.get_parameter('oauth_version')
        except:
            version = VERSION
        if version and version != self.version:
            raise OAuthError('OAuth version %s not supported.' % str(version))
        return version

    def _get_signature_method(self, oauth_request):
        """Figure out the signature with some defaults."""
        try:
            signature_method = oauth_request.get_parameter(
                'oauth_signature_method')
        except:
            signature_method = SIGNATURE_METHOD
        try:
            # Get the signature method object.
            signature_method = self.signature_methods[signature_method]
        except:
            signature_method_names = ', '.join(self.signature_methods.keys())
            raise OAuthError('Signature method %s not supported try one of the '
                'following: %s' % (signature_method, signature_method_names))

        return signature_method

    def _get_consumer(self, oauth_request):
        consumer_key = oauth_request.get_parameter('oauth_consumer_key')
        consumer = self.data_store.lookup_consumer(consumer_key)
        if not consumer:
            raise OAuthError('Invalid consumer.')
        return consumer

    def _get_token(self, oauth_request, token_type='access'):
        """Try to find the token for the provided request token key."""
        token_field = oauth_request.get_parameter('oauth_token')
        token = self.data_store.lookup_token(token_type, token_field)
        if not token:
            raise OAuthError('Invalid %s token: %s' % (token_type, token_field))
        return token

    def _check_signature(self, oauth_request, consumer, token):
        timestamp, nonce = oauth_request._get_timestamp_nonce()
        self._check_timestamp(timestamp)
        self._check_nonce(consumer, token, nonce)
        signature_method = self._get_signature_method(oauth_request)
        try:
            signature = oauth_request.get_parameter('oauth_signature')
        except:
            raise OAuthError('Missing signature.')
        # Validate the signature.
        valid_sig = signature_method.check_signature(oauth_request, consumer,
            token, signature)
        if not valid_sig:
            key, base = signature_method.build_signature_base_string(
                oauth_request, consumer, token)
            raise OAuthError('Invalid signature. Expected signature base '
                'string: %s' % base)
        built = signature_method.build_signature(oauth_request, consumer, token)

    def _check_timestamp(self, timestamp):
        """Verify that timestamp is recentish."""
        timestamp = int(timestamp)
        now = int(time.time())
        lapsed = now - timestamp
        if lapsed > self.timestamp_threshold:
            raise OAuthError('Expired timestamp: given %d and now %s has a '
                'greater difference than threshold %d' %
                (timestamp, now, self.timestamp_threshold))

    def _check_nonce(self, consumer, token, nonce):
        """Verify that the nonce is uniqueish."""
        nonce = self.data_store.lookup_nonce(consumer, token, nonce)
        if nonce:
            raise OAuthError('Nonce already used: %s' % str(nonce))


class OAuthClient(object):
    """OAuthClient is a worker to attempt to execute a request."""
    consumer = None
    token = None

    def __init__(self, oauth_consumer, oauth_token):
        self.consumer = oauth_consumer
        self.token = oauth_token

    def get_consumer(self):
        return self.consumer

    def get_token(self):
        return self.token

    def fetch_request_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def access_resource(self, oauth_request):
        """-> Some protected resource."""
        raise NotImplementedError


class OAuthDataStore(object):
    """A database abstraction used to lookup consumers and tokens."""

    def lookup_consumer(self, key):
        """-> OAuthConsumer."""
        raise NotImplementedError

    def lookup_token(self, oauth_consumer, token_type, token_token):
        """-> OAuthToken."""
        raise NotImplementedError

    def lookup_nonce(self, oauth_consumer, oauth_token, nonce):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_request_token(self, oauth_consumer):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_consumer, oauth_token):
        """-> OAuthToken."""
        raise NotImplementedError

    def authorize_request_token(self, oauth_token, user):
        """-> OAuthToken."""
        raise NotImplementedError


class OAuthSignatureMethod(object):
    """A strategy class that implements a signature method."""
    def get_name(self):
        """-> str."""
        raise NotImplementedError

    def build_signature_base_string(self, oauth_request, oauth_consumer, oauth_token):
        """-> str key, str raw."""
        raise NotImplementedError

    def build_signature(self, oauth_request, oauth_consumer, oauth_token):
        """-> str."""
        raise NotImplementedError

    def check_signature(self, oauth_request, consumer, token, signature):
        built = self.build_signature(oauth_request, consumer, token)
        return built == signature


class OAuthSignatureMethod_HMAC_SHA1(OAuthSignatureMethod):

    def get_name(self):
        return 'HMAC-SHA1'
        
    def build_signature_base_string(self, oauth_request, consumer, token):
        sig = (
            escape(oauth_request.get_normalized_http_method()),
            escape(oauth_request.get_normalized_http_url()),
            escape(oauth_request.get_normalized_parameters()),
        )

        key = '%s&' % escape(consumer.secret)
        if token:
            key += escape(token.secret)
        raw = '&'.join(sig)
        return key, raw

    def build_signature(self, oauth_request, consumer, token):
        """Builds the base signature string."""
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)

        # HMAC object.
        try:
            import hashlib # 2.5
            hashed = hmac.new(key, raw, hashlib.sha1)
        except:
            import sha # Deprecated
            hashed = hmac.new(key, raw, sha)

        # Calculate the digest base 64.
        return binascii.b2a_base64(hashed.digest())[:-1]


class OAuthSignatureMethod_PLAINTEXT(OAuthSignatureMethod):

    def get_name(self):
        return 'PLAINTEXT'

    def build_signature_base_string(self, oauth_request, consumer, token):
        """Concatenates the consumer key and secret."""
        sig = '%s&' % escape(consumer.secret)
        if token:
            sig = sig + escape(token.secret)
        return sig, sig

    def build_signature(self, oauth_request, consumer, token):
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)
        return key
########NEW FILE########
__FILENAME__ = oauthgoogle
import httplib
import urllib2
import urllib
import time
import oauth2 as oauth

from django.conf import settings



REQUEST_TOKEN_URL = 'https://www.google.com/accounts/OAuthGetRequestToken'
ACCESS_TOKEN_URL = 'https://www.google.com/accounts/OAuthGetAccessToken'
AUTHORIZATION_URL = 'https://www.google.com/accounts/OAuthAuthorizeToken'


class GoogleOAuthClient(oauth.OAuthClient):

    def __init__(self, consumer_key, consumer_secret, request_token_url=REQUEST_TOKEN_URL, access_token_url=ACCESS_TOKEN_URL, authorization_url=AUTHORIZATION_URL):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.request_token_url = request_token_url
        self.access_token_url = access_token_url
        self.authorization_url = authorization_url
        self.consumer = oauth.OAuthConsumer(consumer_key, consumer_secret)
        self.signature_method = oauth.OAuthSignatureMethod_HMAC_SHA1()

    def fetch_request_token(self, **kwargs):
        if not 'scope' in kwargs:
            kwargs['scope'] = 'http://www.google.com/m8/feeds'
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer, http_url=self.request_token_url, parameters=kwargs)
        oauth_request.sign_request(self.signature_method, self.consumer, None)
        params = oauth_request.parameters
        data = urllib.urlencode(params)
        full_url='%s?%s'%(self.request_token_url, data)
        response = urllib2.urlopen(full_url)
        return oauth.OAuthToken.from_string(response.read())
    
    def authorize_token_url(self, token, callback_url=None,):
        if not callback_url:
            callback_url = CALLBACK_URL
        oauth_request = oauth.OAuthRequest.from_token_and_callback(token=token, callback=callback_url, http_url=self.authorization_url,)
        params = oauth_request.parameters
        data = urllib.urlencode(params)
        full_url='%s?%s'%(self.authorization_url, data)
        return full_url
        # response = urllib2.urlopen(full_url)
        # return oauth.OAuthToken.from_string(response.read())

    def fetch_access_token(self, token):
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer, token=token, http_url=self.access_token_url)
        oauth_request.sign_request(self.signature_method, self.consumer, token)
        params = oauth_request.parameters
        data = urllib.urlencode(params)
        full_url='%s?%s'%(self.access_token_url, data)
        response = urllib2.urlopen(full_url)
        return oauth.OAuthToken.from_string(response.read())


    def access_resource(self, url, token, **kwargs):
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer, token=token, http_url=url, parameters=kwargs)
        oauth_request.sign_request(self.signature_method, self.consumer, token)
        params = oauth_request.parameters
        data = urllib.urlencode(params)
        full_url='%s?%s'%(url, data)
        #print full_url
        response = urllib2.urlopen(full_url)
        return response

def run_example():

    # setup
    print '** OAuth Python Library Example **'
    client = GoogleOAuthClient(CONSUMER_KEY, CONSUMER_SECRET)
    pause()

    # get request token
    print '* Obtain a request token ...'
    pause()
    
    print 'REQUEST (via headers)'
    print 'parameters: %s' % str(oauth_request.parameters)
    pause()
    token = client.fetch_request_token(oauth_request)
    print 'GOT'
    print 'key: %s' % str(token.key)
    print 'secret: %s' % str(token.secret)
    pause()

    print '* Authorize the request token ...'
    pause()
    
    print 'REQUEST (via url query string)'
    print 'parameters: %s' % str(oauth_request.parameters)
    pause()
    # this will actually occur only on some callback
    url = client.authorize_token(oauth_request, get_url_only=True)
    print 'GOT'
    print url
    pause()

    # get access token
    print '* Obtain an access token ...'
    pause()
    print 'REQUEST (via headers)'
    print 'parameters: %s' % str(oauth_request.parameters)
    pause()
    token = client.fetch_access_token(oauth_request)
    print 'GOT'
    print 'key: %s' % str(token.key)
    print 'secret: %s' % str(token.secret)
    pause()

    # access some protected resources
    print '* Access protected resources ...'
    pause()
    parameters = {'file': 'vacation.jpg', 'size': 'original', 'oauth_callback': CALLBACK_URL} # resource specific params
    print 'REQUEST (via post body)'
    print 'parameters: %s' % str(oauth_request.parameters)
    pause()
    params = client.access_resource(oauth_request)
    print 'GOT'
    print 'non-oauth parameters: %s' % params
    pause()

def pause():
    print ''
    time.sleep(1)

if __name__ == '__main__':
    run_example()
    print 'Done.'
########NEW FILE########
__FILENAME__ = oauthtwitter
#!/usr/bin/env python
# 
# Copyright under GPLv3

'''A class the inherits everything from python-twitter and allows oauth based access

Requires:
  python-twitter
  simplejson
  oauth
'''

__author__ = "Hameedullah Khan <hameed@hameedkhan.net>"
__version__ = "0.1"


from twitter import Api, User
try:
    import json as simplejson
except:
    from django.utils import simplejson

from oauth import oauth



# Taken from oauth implementation at: http://github.com/harperreed/twitteroauth-python/tree/master
REQUEST_TOKEN_URL = 'https://twitter.com/oauth/request_token'
ACCESS_TOKEN_URL = 'https://twitter.com/oauth/access_token'
AUTHORIZATION_URL = 'http://twitter.com/oauth/authorize'
SIGNIN_URL = 'http://twitter.com/oauth/authenticate'


class OAuthApi(Api):
    def __init__(self, consumer_key, consumer_secret, access_token=None):
        if access_token:
            Api.__init__(self,access_token.key, access_token.secret)
        else:
            Api.__init__(self)
        self._Consumer = oauth.OAuthConsumer(consumer_key, consumer_secret)
        self._signature_method = oauth.OAuthSignatureMethod_HMAC_SHA1()
        self._access_token = access_token


    def _GetOpener(self):
        opener = self._urllib.build_opener()
        return opener

    def _FetchUrl(self,
                    url,
                    post_data=None,
                    parameters=None,
                    no_cache=None):
        '''Fetch a URL, optionally caching for a specified time.
    
        Args:
          url: The URL to retrieve
          post_data: 
            A dict of (str, unicode) key/value pairs.  If set, POST will be used.
          parameters:
            A dict whose key/value pairs should encoded and added 
            to the query string. [OPTIONAL]
          no_cache: If true, overrides the cache on the current request
    
        Returns:
          A string containing the body of the response.
        '''
        # Build the extra parameters dict
        extra_params = {}
        try:
            if self._default_params:
                extra_params.update(self._default_params)
        except AttributeError:
            pass
        if parameters:
            extra_params.update(parameters)
    
        # Add key/value parameters to the query string of the url
        #url = self._BuildUrl(url, extra_params=extra_params)
    
        if post_data:
            http_method = "POST"
            extra_params.update(post_data)
        else:
            http_method = "GET"
        
        req = self._makeOAuthRequest(url, parameters=extra_params, 
                                                    http_method=http_method)
        self._signRequest(req, self._signature_method)

        
        # Get a url opener that can handle Oauth basic auth
        opener = self._GetOpener()
        
        #encoded_post_data = self._EncodePostData(post_data)

        if post_data:
            encoded_post_data = req.to_postdata()
            url = req.get_normalized_http_url()
        else:
            url = req.to_url()
            encoded_post_data = ""
            
        no_cache=True
        # Open and return the URL immediately if we're not going to cache
        # OR we are posting data
        if encoded_post_data or no_cache:
            if encoded_post_data:
                url_data = opener.open(url, encoded_post_data).read()
            else:
                url_data = opener.open(url).read()
            opener.close()
        else:
            # Unique keys are a combination of the url and the username
            if self._username:
                key = self._username + ':' + url
            else:
                key = url
    
            # See if it has been cached before
            last_cached = self._cache.GetCachedTime(key)
    
            # If the cached version is outdated then fetch another and store it
            if not last_cached or time.time() >= last_cached + self._cache_timeout:
                url_data = opener.open(url).read()
                opener.close()
                self._cache.Set(key, url_data)
            else:
                url_data = self._cache.Get(key)
    
        # Always return the latest version
        return url_data
    
    def _makeOAuthRequest(self, url, token=None,
                                        parameters=None, http_method="GET"):
        '''Make a OAuth request from url and parameters
        
        Args:
          url: The Url to use for creating OAuth Request
          parameters:
             The URL parameters
          http_method:
             The HTTP method to use
        Returns:
          A OAauthRequest object
        '''
        if not token:
            token = self._access_token
        request = oauth.OAuthRequest.from_consumer_and_token(
                            self._Consumer, token=token, 
                            http_url=url, parameters=parameters, 
                            http_method=http_method)
        return request

    def _signRequest(self, req, signature_method=oauth.OAuthSignatureMethod_HMAC_SHA1()):
        '''Sign a request
        
        Reminder: Created this function so incase
        if I need to add anything to request before signing
        
        Args:
          req: The OAuth request created via _makeOAuthRequest
          signate_method:
             The oauth signature method to use
        '''
        req.sign_request(signature_method, self._Consumer, self._access_token)
    

    def getAuthorizationURL(self, token, url=AUTHORIZATION_URL, callback_url = None):
        '''Create a signed authorization URL
        
        Returns:
          A signed OAuthRequest authorization URL 
        '''
        if callback_url:
            parameters= {'oauth_callback':callback_url}
        else:
            parameters= {}
        req = self._makeOAuthRequest(url, token=token, parameters=parameters)
        self._signRequest(req)
        return req.to_url()

    def getSigninURL(self, token, url=SIGNIN_URL, callback_url = None):
        '''Create a signed Sign-in URL
        
        Returns:
          A signed OAuthRequest Sign-in URL 
        '''
        
        signin_url = self.getAuthorizationURL(token, url, callback_url)
        return signin_url
    
    def getAccessToken(self, url=ACCESS_TOKEN_URL):
        token = self._FetchUrl(url, no_cache=True)
        return oauth.OAuthToken.from_string(token) 

    def getRequestToken(self, url=REQUEST_TOKEN_URL):
        '''Get a Request Token from Twitter
        
        Returns:
          A OAuthToken object containing a request token
        '''
        resp = self._FetchUrl(url, no_cache=True)
        token = oauth.OAuthToken.from_string(resp)
        return token
    
    def GetUserInfo(self, url='https://twitter.com/account/verify_credentials.json'):
        '''Get user information from twitter
        
        Returns:
          Returns the twitter.User object
        '''
        json = self._FetchUrl(url)
        data = simplejson.loads(json)
        self._CheckForTwitterError(data)
        return User.NewFromJsonDict(data)
        

########NEW FILE########
__FILENAME__ = oauthtwitter2
import time
from urllib2 import Request, urlopen

import oauth1 as oauth
from twitter import User

from django.utils import simplejson as json

TWITTER_URL = 'twitter.com'
REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth/request_token'
ACCESS_TOKEN_URL = 'https://api.twitter.com/oauth/access_token'
AUTHORIZATION_URL = 'https://api.twitter.com/oauth/authorize'
TWITTER_CREDENTIALS_URL = 'https://api.twitter.com/1/account/verify_credentials.json'


def oauth_response(req):
    response = urlopen(Request(req.http_url, headers=req.to_header()))
    return response.read()


class TwitterOAuthClient(oauth.OAuthClient):
    def __init__(self, consumer_key, consumer_secret, request_token_url=REQUEST_TOKEN_URL, access_token_url=ACCESS_TOKEN_URL, authorization_url=AUTHORIZATION_URL):
        self.consumer_secret = consumer_secret
        self.consumer_key = consumer_key
        self.consumer = oauth.OAuthConsumer(consumer_key, consumer_secret)
        self.signature_method = oauth.OAuthSignatureMethod_HMAC_SHA1()
        self.request_token_url = request_token_url
        self.access_token_url = access_token_url
        self.authorization_url = authorization_url

    def fetch_request_token(self, callback):
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(
            self.consumer,
            http_url=self.request_token_url,
            callback=callback
        )
        oauth_request.sign_request(self.signature_method, self.consumer, None)
        return oauth.OAuthToken.from_string(oauth_response(oauth_request))

    def authorize_token_url(self, token, callback_url=None):
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(
            self.consumer,
            token=token,
            http_url=self.authorization_url,
            callback=callback_url
        )
        oauth_request.sign_request(self.signature_method, self.consumer, token)
        return oauth_request.to_url()

    def fetch_access_token(self, token, verifier):
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(
            self.consumer,
            token=token,
            verifier=verifier,
            http_url=self.access_token_url
        )
        oauth_request.http_method = 'POST'
        oauth_request.sign_request(self.signature_method, self.consumer, token)
        return oauth.OAuthToken.from_string(oauth_response(oauth_request))

    def get_user_info(self, token):
        try:
            oauth_request = oauth.OAuthRequest.from_consumer_and_token(
                self.consumer,
                token=token,
                http_url=TWITTER_CREDENTIALS_URL
            )
            oauth_request.sign_request(self.signature_method, self.consumer, token)
            return User.NewFromJsonDict(json.loads(oauth_response(oauth_request)))
        except:
            pass
        return None

    def access_resource(self, oauth_request):
        # via post body
        # -> some protected resources
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        connection = get_connection()
        body = oauth_request.to_postdata()
        connection.request('POST', RESOURCE_URL, body=body, headers=headers)
        response = connection.getresponse().read()
        connection.close()
        return response


def run_example():

    # setup
    print '** OAuth Python Library Example **'
    consumer_key = raw_input('Twitter Consumer Key:').strip()
    consumer_secret = raw_input('Twitter Consumer Secret:').strip()
    callback = 'http://example.com/newaccounts/login/done/'

    client = TwitterOAuthClient(consumer_key, consumer_secret)

    pause()

    # get request token
    print '* Obtain a request token ...'
    pause()

    token = client.fetch_request_token(callback)
    print 'GOT'
    print 'key: %s' % str(token.key)
    print 'secret: %s' % str(token.secret)
    pause()

    print '* Authorize the request token ...'
    pause()
    # this will actually occur only on some callback
    url = client.authorize_token_url(token)
    print 'GOT'
    print url
    pause()

    # get access token
    print '* Obtain an access token ...'
    pause()

    access_token = client.fetch_access_token(token)
    print 'GOT'
    print 'key: %s' % str(access_token.key)
    print 'secret: %s' % str(access_token.secret)
    pause()

    # access some protected resources
    print '* Access protected resources ...'
    pause()
    parameters = {
        'file': 'vacation.jpg',
        'size': 'original',
        'oauth_callback': callback,
    }  # resource specific params
    oauth_request = oauth.OAuthRequest.from_consumer_and_token(
        client.consumer,
        token=token,
        http_method='POST',
        http_url=RESOURCE_URL,
        parameters=parameters
    )
    oauth_request.sign_request(client.signature_method, client.consumer, token)
    print 'REQUEST (via post body)'
    print 'parameters: %s' % str(oauth_request.parameters)
    pause()
    params = client.access_resource(oauth_request)
    print 'GOT'
    print 'non-oauth parameters: %s' % params
    pause()


def pause():
    print ''
    time.sleep(1)

if __name__ == '__main__':
    run_example()
    print 'Done.'

########NEW FILE########
__FILENAME__ = oauthyahoo
import httplib
import urllib2
import urllib
import time
import oauth.oauth as oauth

from django.conf import settings



REQUEST_TOKEN_URL = 'https://api.login.yahoo.com/oauth/v2/get_request_token'
ACCESS_TOKEN_URL = 'https://api.login.yahoo.com/oauth/v2/get_token'
AUTHORIZATION_URL = 'https://api.login.yahoo.com/oauth/v2/request_auth'


class YahooOAuthClient(oauth.OAuthClient):

    def __init__(self, consumer_key, consumer_secret, request_token_url=REQUEST_TOKEN_URL, access_token_url=ACCESS_TOKEN_URL, authorization_url=AUTHORIZATION_URL):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.request_token_url = request_token_url
        self.access_token_url = access_token_url
        self.authorization_url = authorization_url
        self.consumer = oauth.OAuthConsumer(consumer_key, consumer_secret)
        self.signature_method = oauth.OAuthSignatureMethod_HMAC_SHA1()

    def fetch_request_token(self, **kwargs):
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer, http_url=self.request_token_url, parameters=kwargs)
        oauth_request.sign_request(self.signature_method, self.consumer, None)
        params = oauth_request.parameters
        data = urllib.urlencode(params)
        full_url='%s?%s'%(self.request_token_url, data)
        response = urllib2.urlopen(full_url)
        return oauth.OAuthToken.from_string(response.read())
    
    def authorize_token_url(self, token, callback_url=None):
        oauth_request = oauth.OAuthRequest.from_token_and_callback(token=token, callback=callback_url, http_url=self.authorization_url)
        params = oauth_request.parameters
        data = urllib.urlencode(params)
        full_url='%s?%s'%(self.authorization_url, data)
        return full_url
        response = urllib2.urlopen(full_url)
        return oauth.OAuthToken.from_string(response.read())

    def fetch_access_token(self, token, **kwargs):
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer, token=token, http_url=self.access_token_url, parameters = kwargs)
        oauth_request.sign_request(self.signature_method, self.consumer, token)
        params = oauth_request.parameters
        data = urllib.urlencode(params)
        full_url='%s?%s'%(self.access_token_url, data)
        response = urllib2.urlopen(full_url)
        return response
        #return oauth.OAuthToken.from_string(response.read())


    def access_resource(self, url, token, **kwargs):
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(self.consumer, token=token, http_url=url, parameters = kwargs)
        oauth_request.sign_request(self.signature_method, self.consumer, token)
        params = oauth_request.parameters
        data = urllib.urlencode(params)
        full_url='%s?%s'%(url, data)
        response = urllib2.urlopen(full_url)
        return response

def run_example():

    # setup
    print '** OAuth Python Library Example **'
    client = GoogleOAuthClient(CONSUMER_KEY, CONSUMER_SECRET)
    pause()

    # get request token
    print '* Obtain a request token ...'
    pause()
    
    print 'REQUEST (via headers)'
    print 'parameters: %s' % str(oauth_request.parameters)
    pause()
    token = client.fetch_request_token(oauth_request)
    print 'GOT'
    print 'key: %s' % str(token.key)
    print 'secret: %s' % str(token.secret)
    pause()

    print '* Authorize the request token ...'
    pause()
    
    print 'REQUEST (via url query string)'
    print 'parameters: %s' % str(oauth_request.parameters)
    pause()
    # this will actually occur only on some callback
    url = client.authorize_token(oauth_request, get_url_only=True)
    print 'GOT'
    print url
    pause()

    # get access token
    print '* Obtain an access token ...'
    pause()
    print 'REQUEST (via headers)'
    print 'parameters: %s' % str(oauth_request.parameters)
    pause()
    token = client.fetch_access_token(oauth_request)
    print 'GOT'
    print 'key: %s' % str(token.key)
    print 'secret: %s' % str(token.secret)
    pause()

    # access some protected resources
    print '* Access protected resources ...'
    pause()
    parameters = {'file': 'vacation.jpg', 'size': 'original', 'oauth_callback': CALLBACK_URL} # resource specific params
    print 'REQUEST (via post body)'
    print 'parameters: %s' % str(oauth_request.parameters)
    pause()
    params = client.access_resource(oauth_request)
    print 'GOT'
    print 'non-oauth parameters: %s' % params
    pause()

def pause():
    print ''
    time.sleep(1)

if __name__ == '__main__':
    run_example()
    print 'Done.'
########NEW FILE########
__FILENAME__ = twitter
#!/usr/bin/python2.4
#
# Copyright 2007 Google Inc. All Rights Reserved.
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

'''A library that provides a python interface to the Twitter API'''

__author__ = 'dewitt@google.com'
__version__ = '0.6-devel'


import base64
import calendar
import os
import rfc822
try:
    import json as simplejson
except:
    from django.utils import simplejson
import sys
import tempfile
import textwrap
import time
import urllib
import urllib2
import urlparse

try:
  from hashlib import md5
except ImportError:
  from md5 import md5


CHARACTER_LIMIT = 140


class TwitterError(Exception):
  '''Base class for Twitter errors'''
  
  @property
  def message(self):
    '''Returns the first argument used to construct this error.'''
    return self.args[0]


class Status(object):
  '''A class representing the Status structure used by the twitter API.

  The Status structure exposes the following properties:

    status.created_at
    status.created_at_in_seconds # read only
    status.favorited
    status.in_reply_to_screen_name
    status.in_reply_to_user_id
    status.in_reply_to_status_id
    status.truncated
    status.source
    status.id
    status.text
    status.relative_created_at # read only
    status.user
  '''
  def __init__(self,
               created_at=None,
               favorited=None,
               id=None,
               text=None,
               user=None,
               in_reply_to_screen_name=None,
               in_reply_to_user_id=None,
               in_reply_to_status_id=None,
               truncated=None,
               source=None,
               now=None):
    '''An object to hold a Twitter status message.

    This class is normally instantiated by the twitter.Api class and
    returned in a sequence.

    Note: Dates are posted in the form "Sat Jan 27 04:17:38 +0000 2007"

    Args:
      created_at: The time this status message was posted
      favorited: Whether this is a favorite of the authenticated user
      id: The unique id of this status message
      text: The text of this status message
      relative_created_at:
        A human readable string representing the posting time
      user:
        A twitter.User instance representing the person posting the message
      now:
        The current time, if the client choses to set it.  Defaults to the
        wall clock time.
    '''
    self.created_at = created_at
    self.favorited = favorited
    self.id = id
    self.text = text
    self.user = user
    self.now = now
    self.in_reply_to_screen_name = in_reply_to_screen_name
    self.in_reply_to_user_id = in_reply_to_user_id
    self.in_reply_to_status_id = in_reply_to_status_id
    self.truncated = truncated
    self.source = source

  def GetCreatedAt(self):
    '''Get the time this status message was posted.

    Returns:
      The time this status message was posted
    '''
    return self._created_at

  def SetCreatedAt(self, created_at):
    '''Set the time this status message was posted.

    Args:
      created_at: The time this status message was created
    '''
    self._created_at = created_at

  created_at = property(GetCreatedAt, SetCreatedAt,
                        doc='The time this status message was posted.')

  def GetCreatedAtInSeconds(self):
    '''Get the time this status message was posted, in seconds since the epoch.

    Returns:
      The time this status message was posted, in seconds since the epoch.
    '''
    return calendar.timegm(rfc822.parsedate(self.created_at))

  created_at_in_seconds = property(GetCreatedAtInSeconds,
                                   doc="The time this status message was "
                                       "posted, in seconds since the epoch")

  def GetFavorited(self):
    '''Get the favorited setting of this status message.

    Returns:
      True if this status message is favorited; False otherwise
    '''
    return self._favorited

  def SetFavorited(self, favorited):
    '''Set the favorited state of this status message.

    Args:
      favorited: boolean True/False favorited state of this status message
    '''
    self._favorited = favorited

  favorited = property(GetFavorited, SetFavorited,
                       doc='The favorited state of this status message.')

  def GetId(self):
    '''Get the unique id of this status message.

    Returns:
      The unique id of this status message
    '''
    return self._id

  def SetId(self, id):
    '''Set the unique id of this status message.

    Args:
      id: The unique id of this status message
    '''
    self._id = id

  id = property(GetId, SetId,
                doc='The unique id of this status message.')

  def GetInReplyToScreenName(self):
    return self._in_reply_to_screen_name

  def SetInReplyToScreenName(self, in_reply_to_screen_name):
    self._in_reply_to_screen_name = in_reply_to_screen_name

  in_reply_to_screen_name = property(GetInReplyToScreenName, SetInReplyToScreenName,
                doc='')

  def GetInReplyToUserId(self):
    return self._in_reply_to_user_id

  def SetInReplyToUserId(self, in_reply_to_user_id):
    self._in_reply_to_user_id = in_reply_to_user_id

  in_reply_to_user_id = property(GetInReplyToUserId, SetInReplyToUserId,
                doc='')

  def GetInReplyToStatusId(self):
    return self._in_reply_to_status_id

  def SetInReplyToStatusId(self, in_reply_to_status_id):
    self._in_reply_to_status_id = in_reply_to_status_id

  in_reply_to_status_id = property(GetInReplyToStatusId, SetInReplyToStatusId,
                doc='')

  def GetTruncated(self):
    return self._truncated

  def SetTruncated(self, truncated):
    self._truncated = truncated

  truncated = property(GetTruncated, SetTruncated,
                doc='')

  def GetSource(self):
    return self._source

  def SetSource(self, source):
    self._source = source

  source = property(GetSource, SetSource,
                doc='')

  def GetText(self):
    '''Get the text of this status message.

    Returns:
      The text of this status message.
    '''
    return self._text

  def SetText(self, text):
    '''Set the text of this status message.

    Args:
      text: The text of this status message
    '''
    self._text = text

  text = property(GetText, SetText,
                  doc='The text of this status message')

  def GetRelativeCreatedAt(self):
    '''Get a human redable string representing the posting time

    Returns:
      A human readable string representing the posting time
    '''
    fudge = 1.25
    delta  = long(self.now) - long(self.created_at_in_seconds)

    if delta < (1 * fudge):
      return 'about a second ago'
    elif delta < (60 * (1/fudge)):
      return 'about %d seconds ago' % (delta)
    elif delta < (60 * fudge):
      return 'about a minute ago'
    elif delta < (60 * 60 * (1/fudge)):
      return 'about %d minutes ago' % (delta / 60)
    elif delta < (60 * 60 * fudge):
      return 'about an hour ago'
    elif delta < (60 * 60 * 24 * (1/fudge)):
      return 'about %d hours ago' % (delta / (60 * 60))
    elif delta < (60 * 60 * 24 * fudge):
      return 'about a day ago'
    else:
      return 'about %d days ago' % (delta / (60 * 60 * 24))

  relative_created_at = property(GetRelativeCreatedAt,
                                 doc='Get a human readable string representing'
                                     'the posting time')

  def GetUser(self):
    '''Get a twitter.User reprenting the entity posting this status message.

    Returns:
      A twitter.User reprenting the entity posting this status message
    '''
    return self._user

  def SetUser(self, user):
    '''Set a twitter.User reprenting the entity posting this status message.

    Args:
      user: A twitter.User reprenting the entity posting this status message
    '''
    self._user = user

  user = property(GetUser, SetUser,
                  doc='A twitter.User reprenting the entity posting this '
                      'status message')

  def GetNow(self):
    '''Get the wallclock time for this status message.

    Used to calculate relative_created_at.  Defaults to the time
    the object was instantiated.

    Returns:
      Whatever the status instance believes the current time to be,
      in seconds since the epoch.
    '''
    if self._now is None:
      self._now = time.time()
    return self._now

  def SetNow(self, now):
    '''Set the wallclock time for this status message.

    Used to calculate relative_created_at.  Defaults to the time
    the object was instantiated.

    Args:
      now: The wallclock time for this instance.
    '''
    self._now = now

  now = property(GetNow, SetNow,
                 doc='The wallclock time for this status instance.')


  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
             self.created_at == other.created_at and \
             self.id == other.id and \
             self.text == other.text and \
             self.user == other.user and \
             self.in_reply_to_screen_name == other.in_reply_to_screen_name and \
             self.in_reply_to_user_id == other.in_reply_to_user_id and \
             self.in_reply_to_status_id == other.in_reply_to_status_id and \
             self.truncated == other.truncated and \
             self.favorited == other.favorited and \
             self.source == other.source
    except AttributeError:
      return False

  def __str__(self):
    '''A string representation of this twitter.Status instance.

    The return value is the same as the JSON string representation.

    Returns:
      A string representation of this twitter.Status instance.
    '''
    return self.AsJsonString()

  def AsJsonString(self):
    '''A JSON string representation of this twitter.Status instance.

    Returns:
      A JSON string representation of this twitter.Status instance
   '''
    return simplejson.dumps(self.AsDict(), sort_keys=True)

  def AsDict(self):
    '''A dict representation of this twitter.Status instance.

    The return value uses the same key names as the JSON representation.

    Return:
      A dict representing this twitter.Status instance
    '''
    data = {}
    if self.created_at:
      data['created_at'] = self.created_at
    if self.favorited:
      data['favorited'] = self.favorited
    if self.id:
      data['id'] = self.id
    if self.text:
      data['text'] = self.text
    if self.user:
      data['user'] = self.user.AsDict()
    if self.in_reply_to_screen_name:
      data['in_reply_to_screen_name'] = self.in_reply_to_screen_name
    if self.in_reply_to_user_id:
      data['in_reply_to_user_id'] = self.in_reply_to_user_id
    if self.in_reply_to_status_id:
      data['in_reply_to_status_id'] = self.in_reply_to_status_id
    if self.truncated is not None:
      data['truncated'] = self.truncated
    if self.favorited is not None:
      data['favorited'] = self.favorited
    if self.source:
      data['source'] = self.source
    return data

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data: A JSON dict, as converted from the JSON in the twitter API
    Returns:
      A twitter.Status instance
    '''
    if 'user' in data:
      user = User.NewFromJsonDict(data['user'])
    else:
      user = None
    return Status(created_at=data.get('created_at', None),
                  favorited=data.get('favorited', None),
                  id=data.get('id', None),
                  text=data.get('text', None),
                  in_reply_to_screen_name=data.get('in_reply_to_screen_name', None),
                  in_reply_to_user_id=data.get('in_reply_to_user_id', None),
                  in_reply_to_status_id=data.get('in_reply_to_status_id', None),
                  truncated=data.get('truncated', None),
                  source=data.get('source', None),
                  user=user)


class User(object):
  '''A class representing the User structure used by the twitter API.

  The User structure exposes the following properties:

    user.id
    user.name
    user.screen_name
    user.location
    user.description
    user.profile_image_url
    user.profile_background_tile
    user.profile_background_image_url
    user.profile_sidebar_fill_color
    user.profile_background_color
    user.profile_link_color
    user.profile_text_color
    user.protected
    user.utc_offset
    user.time_zone
    user.url
    user.status
    user.statuses_count
    user.followers_count
    user.friends_count
    user.favourites_count
  '''
  def __init__(self,
               id=None,
               name=None,
               screen_name=None,
               location=None,
               description=None,
               profile_image_url=None,
               profile_background_tile=None,
               profile_background_image_url=None,
               profile_sidebar_fill_color=None,
               profile_background_color=None,
               profile_link_color=None,
               profile_text_color=None,
               protected=None,
               utc_offset=None,
               time_zone=None,
               followers_count=None,
               friends_count=None,
               statuses_count=None,
               favourites_count=None,
               url=None,
               status=None):
    self.id = id
    self.name = name
    self.screen_name = screen_name
    self.location = location
    self.description = description
    self.profile_image_url = profile_image_url
    self.profile_background_tile = profile_background_tile
    self.profile_background_image_url = profile_background_image_url
    self.profile_sidebar_fill_color = profile_sidebar_fill_color
    self.profile_background_color = profile_background_color
    self.profile_link_color = profile_link_color
    self.profile_text_color = profile_text_color
    self.protected = protected
    self.utc_offset = utc_offset
    self.time_zone = time_zone
    self.followers_count = followers_count
    self.friends_count = friends_count
    self.statuses_count = statuses_count
    self.favourites_count = favourites_count
    self.url = url
    self.status = status


  def GetId(self):
    '''Get the unique id of this user.

    Returns:
      The unique id of this user
    '''
    return self._id

  def SetId(self, id):
    '''Set the unique id of this user.

    Args:
      id: The unique id of this user.
    '''
    self._id = id

  id = property(GetId, SetId,
                doc='The unique id of this user.')

  def GetName(self):
    '''Get the real name of this user.

    Returns:
      The real name of this user
    '''
    return self._name

  def SetName(self, name):
    '''Set the real name of this user.

    Args:
      name: The real name of this user
    '''
    self._name = name

  name = property(GetName, SetName,
                  doc='The real name of this user.')

  def GetScreenName(self):
    '''Get the short username of this user.

    Returns:
      The short username of this user
    '''
    return self._screen_name

  def SetScreenName(self, screen_name):
    '''Set the short username of this user.

    Args:
      screen_name: the short username of this user
    '''
    self._screen_name = screen_name

  screen_name = property(GetScreenName, SetScreenName,
                         doc='The short username of this user.')

  def GetLocation(self):
    '''Get the geographic location of this user.

    Returns:
      The geographic location of this user
    '''
    return self._location

  def SetLocation(self, location):
    '''Set the geographic location of this user.

    Args:
      location: The geographic location of this user
    '''
    self._location = location

  location = property(GetLocation, SetLocation,
                      doc='The geographic location of this user.')

  def GetDescription(self):
    '''Get the short text description of this user.

    Returns:
      The short text description of this user
    '''
    return self._description

  def SetDescription(self, description):
    '''Set the short text description of this user.

    Args:
      description: The short text description of this user
    '''
    self._description = description

  description = property(GetDescription, SetDescription,
                         doc='The short text description of this user.')

  def GetUrl(self):
    '''Get the homepage url of this user.

    Returns:
      The homepage url of this user
    '''
    return self._url

  def SetUrl(self, url):
    '''Set the homepage url of this user.

    Args:
      url: The homepage url of this user
    '''
    self._url = url

  url = property(GetUrl, SetUrl,
                 doc='The homepage url of this user.')

  def GetProfileImageUrl(self):
    '''Get the url of the thumbnail of this user.

    Returns:
      The url of the thumbnail of this user
    '''
    return self._profile_image_url

  def SetProfileImageUrl(self, profile_image_url):
    '''Set the url of the thumbnail of this user.

    Args:
      profile_image_url: The url of the thumbnail of this user
    '''
    self._profile_image_url = profile_image_url

  profile_image_url= property(GetProfileImageUrl, SetProfileImageUrl,
                              doc='The url of the thumbnail of this user.')

  def GetProfileBackgroundTile(self):
    '''Boolean for whether to tile the profile background image.

    Returns:
      True if the background is to be tiled, False if not, None if unset.
    '''
    return self._profile_background_tile

  def SetProfileBackgroundTile(self, profile_background_tile):
    '''Set the boolean flag for whether to tile the profile background image.

    Args:
      profile_background_tile: Boolean flag for whether to tile or not.
    '''
    self._profile_background_tile = profile_background_tile

  profile_background_tile = property(GetProfileBackgroundTile, SetProfileBackgroundTile,
                                     doc='Boolean for whether to tile the background image.')

  def GetProfileBackgroundImageUrl(self):
    return self._profile_background_image_url

  def SetProfileBackgroundImageUrl(self, profile_background_image_url):
    self._profile_background_image_url = profile_background_image_url

  profile_background_image_url = property(GetProfileBackgroundImageUrl, SetProfileBackgroundImageUrl,
                                          doc='The url of the profile background of this user.')

  def GetProfileSidebarFillColor(self):
    return self._profile_sidebar_fill_color

  def SetProfileSidebarFillColor(self, profile_sidebar_fill_color):
    self._profile_sidebar_fill_color = profile_sidebar_fill_color

  profile_sidebar_fill_color = property(GetProfileSidebarFillColor, SetProfileSidebarFillColor)

  def GetProfileBackgroundColor(self):
    return self._profile_background_color

  def SetProfileBackgroundColor(self, profile_background_color):
    self._profile_background_color = profile_background_color

  profile_background_color = property(GetProfileBackgroundColor, SetProfileBackgroundColor)

  def GetProfileLinkColor(self):
    return self._profile_link_color

  def SetProfileLinkColor(self, profile_link_color):
    self._profile_link_color = profile_link_color

  profile_link_color = property(GetProfileLinkColor, SetProfileLinkColor)

  def GetProfileTextColor(self):
    return self._profile_text_color

  def SetProfileTextColor(self, profile_text_color):
    self._profile_text_color = profile_text_color

  profile_text_color = property(GetProfileTextColor, SetProfileTextColor)

  def GetProtected(self):
    return self._protected

  def SetProtected(self, protected):
    self._protected = protected

  protected = property(GetProtected, SetProtected)

  def GetUtcOffset(self):
    return self._utc_offset

  def SetUtcOffset(self, utc_offset):
    self._utc_offset = utc_offset

  utc_offset = property(GetUtcOffset, SetUtcOffset)

  def GetTimeZone(self):
    '''Returns the current time zone string for the user.

    Returns:
      The descriptive time zone string for the user.
    '''
    return self._time_zone

  def SetTimeZone(self, time_zone):
    '''Sets the user's time zone string.

    Args:
      time_zone: The descriptive time zone to assign for the user.
    '''
    self._time_zone = time_zone

  time_zone = property(GetTimeZone, SetTimeZone)

  def GetStatus(self):
    '''Get the latest twitter.Status of this user.

    Returns:
      The latest twitter.Status of this user
    '''
    return self._status

  def SetStatus(self, status):
    '''Set the latest twitter.Status of this user.

    Args:
      status: The latest twitter.Status of this user
    '''
    self._status = status

  status = property(GetStatus, SetStatus,
                  doc='The latest twitter.Status of this user.')

  def GetFriendsCount(self):
    '''Get the friend count for this user.
    
    Returns:
      The number of users this user has befriended.
    '''
    return self._friends_count

  def SetFriendsCount(self, count):
    '''Set the friend count for this user.

    Args:
      count: The number of users this user has befriended.
    '''
    self._friends_count = count

  friends_count = property(GetFriendsCount, SetFriendsCount,
                  doc='The number of friends for this user.')

  def GetFollowersCount(self):
    '''Get the follower count for this user.
    
    Returns:
      The number of users following this user.
    '''
    return self._followers_count

  def SetFollowersCount(self, count):
    '''Set the follower count for this user.

    Args:
      count: The number of users following this user.
    '''
    self._followers_count = count

  followers_count = property(GetFollowersCount, SetFollowersCount,
                  doc='The number of users following this user.')

  def GetStatusesCount(self):
    '''Get the number of status updates for this user.
    
    Returns:
      The number of status updates for this user.
    '''
    return self._statuses_count

  def SetStatusesCount(self, count):
    '''Set the status update count for this user.

    Args:
      count: The number of updates for this user.
    '''
    self._statuses_count = count

  statuses_count = property(GetStatusesCount, SetStatusesCount,
                  doc='The number of updates for this user.')

  def GetFavouritesCount(self):
    '''Get the number of favourites for this user.
    
    Returns:
      The number of favourites for this user.
    '''
    return self._favourites_count

  def SetFavouritesCount(self, count):
    '''Set the favourite count for this user.

    Args:
      count: The number of favourites for this user.
    '''
    self._favourites_count = count

  favourites_count = property(GetFavouritesCount, SetFavouritesCount,
                  doc='The number of favourites for this user.')

  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
             self.id == other.id and \
             self.name == other.name and \
             self.screen_name == other.screen_name and \
             self.location == other.location and \
             self.description == other.description and \
             self.profile_image_url == other.profile_image_url and \
             self.profile_background_tile == other.profile_background_tile and \
             self.profile_background_image_url == other.profile_background_image_url and \
             self.profile_sidebar_fill_color == other.profile_sidebar_fill_color and \
             self.profile_background_color == other.profile_background_color and \
             self.profile_link_color == other.profile_link_color and \
             self.profile_text_color == other.profile_text_color and \
             self.protected == other.protected and \
             self.utc_offset == other.utc_offset and \
             self.time_zone == other.time_zone and \
             self.url == other.url and \
             self.statuses_count == other.statuses_count and \
             self.followers_count == other.followers_count and \
             self.favourites_count == other.favourites_count and \
             self.friends_count == other.friends_count and \
             self.status == other.status
    except AttributeError:
      return False

  def __str__(self):
    '''A string representation of this twitter.User instance.

    The return value is the same as the JSON string representation.

    Returns:
      A string representation of this twitter.User instance.
    '''
    return self.AsJsonString()

  def AsJsonString(self):
    '''A JSON string representation of this twitter.User instance.

    Returns:
      A JSON string representation of this twitter.User instance
   '''
    return simplejson.dumps(self.AsDict(), sort_keys=True)

  def AsDict(self):
    '''A dict representation of this twitter.User instance.

    The return value uses the same key names as the JSON representation.

    Return:
      A dict representing this twitter.User instance
    '''
    data = {}
    if self.id:
      data['id'] = self.id
    if self.name:
      data['name'] = self.name
    if self.screen_name:
      data['screen_name'] = self.screen_name
    if self.location:
      data['location'] = self.location
    if self.description:
      data['description'] = self.description
    if self.profile_image_url:
      data['profile_image_url'] = self.profile_image_url
    if self.profile_background_tile is not None:
      data['profile_background_tile'] = self.profile_background_tile
    if self.profile_background_image_url:
      data['profile_sidebar_fill_color'] = self.profile_background_image_url
    if self.profile_background_color:
      data['profile_background_color'] = self.profile_background_color
    if self.profile_link_color:
      data['profile_link_color'] = self.profile_link_color
    if self.profile_text_color:
      data['profile_text_color'] = self.profile_text_color
    if self.protected is not None:
      data['protected'] = self.protected
    if self.utc_offset:
      data['utc_offset'] = self.utc_offset
    if self.time_zone:
      data['time_zone'] = self.time_zone
    if self.url:
      data['url'] = self.url
    if self.status:
      data['status'] = self.status.AsDict()
    if self.friends_count:
      data['friends_count'] = self.friends_count
    if self.followers_count:
      data['followers_count'] = self.followers_count
    if self.statuses_count:
      data['statuses_count'] = self.statuses_count
    if self.favourites_count:
      data['favourites_count'] = self.favourites_count
    return data

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data: A JSON dict, as converted from the JSON in the twitter API
    Returns:
      A twitter.User instance
    '''
    if 'status' in data:
      status = Status.NewFromJsonDict(data['status'])
    else:
      status = None
    return User(id=data.get('id', None),
                name=data.get('name', None),
                screen_name=data.get('screen_name', None),
                location=data.get('location', None),
                description=data.get('description', None),
                statuses_count=data.get('statuses_count', None),
                followers_count=data.get('followers_count', None),
                favourites_count=data.get('favourites_count', None),
                friends_count=data.get('friends_count', None),
                profile_image_url=data.get('profile_image_url', None),
                profile_background_tile = data.get('profile_background_tile', None),
                profile_background_image_url = data.get('profile_background_image_url', None),
                profile_sidebar_fill_color = data.get('profile_sidebar_fill_color', None),
                profile_background_color = data.get('profile_background_color', None),
                profile_link_color = data.get('profile_link_color', None),
                profile_text_color = data.get('profile_text_color', None),
                protected = data.get('protected', None),
                utc_offset = data.get('utc_offset', None),
                time_zone = data.get('time_zone', None),
                url=data.get('url', None),
                status=status)

class DirectMessage(object):
  '''A class representing the DirectMessage structure used by the twitter API.

  The DirectMessage structure exposes the following properties:

    direct_message.id
    direct_message.created_at
    direct_message.created_at_in_seconds # read only
    direct_message.sender_id
    direct_message.sender_screen_name
    direct_message.recipient_id
    direct_message.recipient_screen_name
    direct_message.text
  '''

  def __init__(self,
               id=None,
               created_at=None,
               sender_id=None,
               sender_screen_name=None,
               recipient_id=None,
               recipient_screen_name=None,
               text=None):
    '''An object to hold a Twitter direct message.

    This class is normally instantiated by the twitter.Api class and
    returned in a sequence.

    Note: Dates are posted in the form "Sat Jan 27 04:17:38 +0000 2007"

    Args:
      id: The unique id of this direct message
      created_at: The time this direct message was posted
      sender_id: The id of the twitter user that sent this message
      sender_screen_name: The name of the twitter user that sent this message
      recipient_id: The id of the twitter that received this message
      recipient_screen_name: The name of the twitter that received this message
      text: The text of this direct message
    '''
    self.id = id
    self.created_at = created_at
    self.sender_id = sender_id
    self.sender_screen_name = sender_screen_name
    self.recipient_id = recipient_id
    self.recipient_screen_name = recipient_screen_name
    self.text = text

  def GetId(self):
    '''Get the unique id of this direct message.

    Returns:
      The unique id of this direct message
    '''
    return self._id

  def SetId(self, id):
    '''Set the unique id of this direct message.

    Args:
      id: The unique id of this direct message
    '''
    self._id = id

  id = property(GetId, SetId,
                doc='The unique id of this direct message.')

  def GetCreatedAt(self):
    '''Get the time this direct message was posted.

    Returns:
      The time this direct message was posted
    '''
    return self._created_at

  def SetCreatedAt(self, created_at):
    '''Set the time this direct message was posted.

    Args:
      created_at: The time this direct message was created
    '''
    self._created_at = created_at

  created_at = property(GetCreatedAt, SetCreatedAt,
                        doc='The time this direct message was posted.')

  def GetCreatedAtInSeconds(self):
    '''Get the time this direct message was posted, in seconds since the epoch.

    Returns:
      The time this direct message was posted, in seconds since the epoch.
    '''
    return calendar.timegm(rfc822.parsedate(self.created_at))

  created_at_in_seconds = property(GetCreatedAtInSeconds,
                                   doc="The time this direct message was "
                                       "posted, in seconds since the epoch")

  def GetSenderId(self):
    '''Get the unique sender id of this direct message.

    Returns:
      The unique sender id of this direct message
    '''
    return self._sender_id

  def SetSenderId(self, sender_id):
    '''Set the unique sender id of this direct message.

    Args:
      sender id: The unique sender id of this direct message
    '''
    self._sender_id = sender_id

  sender_id = property(GetSenderId, SetSenderId,
                doc='The unique sender id of this direct message.')

  def GetSenderScreenName(self):
    '''Get the unique sender screen name of this direct message.

    Returns:
      The unique sender screen name of this direct message
    '''
    return self._sender_screen_name

  def SetSenderScreenName(self, sender_screen_name):
    '''Set the unique sender screen name of this direct message.

    Args:
      sender_screen_name: The unique sender screen name of this direct message
    '''
    self._sender_screen_name = sender_screen_name

  sender_screen_name = property(GetSenderScreenName, SetSenderScreenName,
                doc='The unique sender screen name of this direct message.')

  def GetRecipientId(self):
    '''Get the unique recipient id of this direct message.

    Returns:
      The unique recipient id of this direct message
    '''
    return self._recipient_id

  def SetRecipientId(self, recipient_id):
    '''Set the unique recipient id of this direct message.

    Args:
      recipient id: The unique recipient id of this direct message
    '''
    self._recipient_id = recipient_id

  recipient_id = property(GetRecipientId, SetRecipientId,
                doc='The unique recipient id of this direct message.')

  def GetRecipientScreenName(self):
    '''Get the unique recipient screen name of this direct message.

    Returns:
      The unique recipient screen name of this direct message
    '''
    return self._recipient_screen_name

  def SetRecipientScreenName(self, recipient_screen_name):
    '''Set the unique recipient screen name of this direct message.

    Args:
      recipient_screen_name: The unique recipient screen name of this direct message
    '''
    self._recipient_screen_name = recipient_screen_name

  recipient_screen_name = property(GetRecipientScreenName, SetRecipientScreenName,
                doc='The unique recipient screen name of this direct message.')

  def GetText(self):
    '''Get the text of this direct message.

    Returns:
      The text of this direct message.
    '''
    return self._text

  def SetText(self, text):
    '''Set the text of this direct message.

    Args:
      text: The text of this direct message
    '''
    self._text = text

  text = property(GetText, SetText,
                  doc='The text of this direct message')

  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
          self.id == other.id and \
          self.created_at == other.created_at and \
          self.sender_id == other.sender_id and \
          self.sender_screen_name == other.sender_screen_name and \
          self.recipient_id == other.recipient_id and \
          self.recipient_screen_name == other.recipient_screen_name and \
          self.text == other.text
    except AttributeError:
      return False

  def __str__(self):
    '''A string representation of this twitter.DirectMessage instance.

    The return value is the same as the JSON string representation.

    Returns:
      A string representation of this twitter.DirectMessage instance.
    '''
    return self.AsJsonString()

  def AsJsonString(self):
    '''A JSON string representation of this twitter.DirectMessage instance.

    Returns:
      A JSON string representation of this twitter.DirectMessage instance
   '''
    return simplejson.dumps(self.AsDict(), sort_keys=True)

  def AsDict(self):
    '''A dict representation of this twitter.DirectMessage instance.

    The return value uses the same key names as the JSON representation.

    Return:
      A dict representing this twitter.DirectMessage instance
    '''
    data = {}
    if self.id:
      data['id'] = self.id
    if self.created_at:
      data['created_at'] = self.created_at
    if self.sender_id:
      data['sender_id'] = self.sender_id
    if self.sender_screen_name:
      data['sender_screen_name'] = self.sender_screen_name
    if self.recipient_id:
      data['recipient_id'] = self.recipient_id
    if self.recipient_screen_name:
      data['recipient_screen_name'] = self.recipient_screen_name
    if self.text:
      data['text'] = self.text
    return data

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data: A JSON dict, as converted from the JSON in the twitter API
    Returns:
      A twitter.DirectMessage instance
    '''
    return DirectMessage(created_at=data.get('created_at', None),
                         recipient_id=data.get('recipient_id', None),
                         sender_id=data.get('sender_id', None),
                         text=data.get('text', None),
                         sender_screen_name=data.get('sender_screen_name', None),
                         id=data.get('id', None),
                         recipient_screen_name=data.get('recipient_screen_name', None))

class Api(object):
  '''A python interface into the Twitter API

  By default, the Api caches results for 1 minute.

  Example usage:

    To create an instance of the twitter.Api class, with no authentication:

      >>> import twitter
      >>> api = twitter.Api()

    To fetch the most recently posted public twitter status messages:

      >>> statuses = api.GetPublicTimeline()
      >>> print [s.user.name for s in statuses]
      [u'DeWitt', u'Kesuke Miyagi', u'ev', u'Buzz Andersen', u'Biz Stone'] #...

    To fetch a single user's public status messages, where "user" is either
    a Twitter "short name" or their user id.

      >>> statuses = api.GetUserTimeline(user)
      >>> print [s.text for s in statuses]

    To use authentication, instantiate the twitter.Api class with a
    username and password:

      >>> api = twitter.Api(username='twitter user', password='twitter pass')

    To fetch your friends (after being authenticated):

      >>> users = api.GetFriends()
      >>> print [u.name for u in users]

    To post a twitter status message (after being authenticated):

      >>> status = api.PostUpdate('I love python-twitter!')
      >>> print status.text
      I love python-twitter!

    There are many other methods, including:

      >>> api.PostUpdates(status)
      >>> api.PostDirectMessage(user, text)
      >>> api.GetUser(user)
      >>> api.GetReplies()
      >>> api.GetUserTimeline(user)
      >>> api.GetStatus(id)
      >>> api.DestroyStatus(id)
      >>> api.GetFriendsTimeline(user)
      >>> api.GetFriends(user)
      >>> api.GetFollowers()
      >>> api.GetFeatured()
      >>> api.GetDirectMessages()
      >>> api.PostDirectMessage(user, text)
      >>> api.DestroyDirectMessage(id)
      >>> api.DestroyFriendship(user)
      >>> api.CreateFriendship(user)
      >>> api.GetUserByEmail(email)
  '''

  DEFAULT_CACHE_TIMEOUT = 60 # cache for 1 minute

  _API_REALM = 'Twitter API'

  def __init__(self,
               username=None,
               password=None,
               input_encoding=None,
               request_headers=None):
    '''Instantiate a new twitter.Api object.

    Args:
      username: The username of the twitter account.  [optional]
      password: The password for the twitter account. [optional]
      input_encoding: The encoding used to encode input strings. [optional]
      request_header: A dictionary of additional HTTP request headers. [optional]
    '''
    self._cache = _FileCache()
    self._urllib = urllib2
    self._cache_timeout = Api.DEFAULT_CACHE_TIMEOUT
    self._InitializeRequestHeaders(request_headers)
    self._InitializeUserAgent()
    self._InitializeDefaultParameters()
    self._input_encoding = input_encoding
    self.SetCredentials(username, password)

  def GetPublicTimeline(self, since_id=None):
    '''Fetch the sequnce of public twitter.Status message for all users.

    Args:
      since_id:
        Returns only public statuses with an ID greater than (that is,
        more recent than) the specified ID. [Optional]

    Returns:
      An sequence of twitter.Status instances, one for each message
    '''
    parameters = {}
    if since_id:
      parameters['since_id'] = since_id
    url = 'http://twitter.com/statuses/public_timeline.json'
    json = self._FetchUrl(url,  parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [Status.NewFromJsonDict(x) for x in data]

  def GetFriendsTimeline(self,
                         user=None,
                         count=None,
                         since=None, 
                         since_id=None):
    '''Fetch the sequence of twitter.Status messages for a user's friends

    The twitter.Api instance must be authenticated if the user is private.

    Args:
      user:
        Specifies the ID or screen name of the user for whom to return
        the friends_timeline.  If unspecified, the username and password
        must be set in the twitter.Api instance.  [Optional]
      count: 
        Specifies the number of statuses to retrieve. May not be
        greater than 200. [Optional]
      since:
        Narrows the returned results to just those statuses created
        after the specified HTTP-formatted date. [Optional]
      since_id:
        Returns only public statuses with an ID greater than (that is,
        more recent than) the specified ID. [Optional]

    Returns:
      A sequence of twitter.Status instances, one for each message
    '''
    if user:
      url = 'http://twitter.com/statuses/friends_timeline/%s.json' % user
    elif not user and not self._username:
      raise TwitterError("User must be specified if API is not authenticated.")
    else:
      url = 'http://twitter.com/statuses/friends_timeline.json'
    parameters = {}
    if count is not None:
      try:
        if int(count) > 200:
          raise TwitterError("'count' may not be greater than 200")
      except ValueError:
        raise TwitterError("'count' must be an integer")
      parameters['count'] = count
    if since:
      parameters['since'] = since
    if since_id:
      parameters['since_id'] = since_id
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [Status.NewFromJsonDict(x) for x in data]

  def GetUserTimeline(self, user=None, count=None, since=None, since_id=None):
    '''Fetch the sequence of public twitter.Status messages for a single user.

    The twitter.Api instance must be authenticated if the user is private.

    Args:
      user:
        either the username (short_name) or id of the user to retrieve.  If
        not specified, then the current authenticated user is used. [optional]
      count: the number of status messages to retrieve [optional]
      since:
        Narrows the returned results to just those statuses created
        after the specified HTTP-formatted date. [optional]
      since_id:
        Returns only public statuses with an ID greater than (that is,
        more recent than) the specified ID. [Optional]

    Returns:
      A sequence of twitter.Status instances, one for each message up to count
    '''
    try:
      if count:
        int(count)
    except:
      raise TwitterError("Count must be an integer")
    parameters = {}
    if count:
      parameters['count'] = count
    if since:
      parameters['since'] = since
    if since_id:
      parameters['since_id'] = since_id
    if user:
      url = 'http://twitter.com/statuses/user_timeline/%s.json' % user
    elif not user and not self._username:
      raise TwitterError("User must be specified if API is not authenticated.")
    else:
      url = 'http://twitter.com/statuses/user_timeline.json'
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [Status.NewFromJsonDict(x) for x in data]

  def GetStatus(self, id):
    '''Returns a single status message.

    The twitter.Api instance must be authenticated if the status message is private.

    Args:
      id: The numerical ID of the status you're trying to retrieve.

    Returns:
      A twitter.Status instance representing that status message
    '''
    try:
      if id:
        long(id)
    except:
      raise TwitterError("id must be an long integer")
    url = 'http://twitter.com/statuses/show/%s.json' % id
    json = self._FetchUrl(url)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return Status.NewFromJsonDict(data)

  def DestroyStatus(self, id):
    '''Destroys the status specified by the required ID parameter.

    The twitter.Api instance must be authenticated and thee
    authenticating user must be the author of the specified status.

    Args:
      id: The numerical ID of the status you're trying to destroy.

    Returns:
      A twitter.Status instance representing the destroyed status message
    '''
    try:
      if id:
        long(id)
    except:
      raise TwitterError("id must be an integer")
    url = 'http://twitter.com/statuses/destroy/%s.json' % id
    json = self._FetchUrl(url, post_data={})
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return Status.NewFromJsonDict(data)

  def PostUpdate(self, status, in_reply_to_status_id=None):
    '''Post a twitter status message from the authenticated user.

    The twitter.Api instance must be authenticated.

    Args:
      status:
        The message text to be posted.  Must be less than or equal to
        140 characters.
      in_reply_to_status_id:
        The ID of an existing status that the status to be posted is
        in reply to.  This implicitly sets the in_reply_to_user_id
        attribute of the resulting status to the user ID of the
        message being replied to.  Invalid/missing status IDs will be
        ignored. [Optional]
    Returns:
      A twitter.Status instance representing the message posted.
    '''
    if not self._username:
      raise TwitterError("The twitter.Api instance must be authenticated.")

    url = 'http://twitter.com/statuses/update.json'

    if len(status) > CHARACTER_LIMIT:
      raise TwitterError("Text must be less than or equal to %d characters. "
                         "Consider using PostUpdates." % CHARACTER_LIMIT)

    data = {'status': status}
    if in_reply_to_status_id:
      data['in_reply_to_status_id'] = in_reply_to_status_id
    json = self._FetchUrl(url, post_data=data)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return Status.NewFromJsonDict(data)

  def PostUpdates(self, status, continuation=None, **kwargs):
    '''Post one or more twitter status messages from the authenticated user.

    Unlike api.PostUpdate, this method will post multiple status updates
    if the message is longer than 140 characters.

    The twitter.Api instance must be authenticated.

    Args:
      status:
        The message text to be posted.  May be longer than 140 characters.
      continuation:
        The character string, if any, to be appended to all but the
        last message.  Note that Twitter strips trailing '...' strings
        from messages.  Consider using the unicode \u2026 character
        (horizontal ellipsis) instead. [Defaults to None]
      **kwargs:
        See api.PostUpdate for a list of accepted parameters.
    Returns:
      A of list twitter.Status instance representing the messages posted.
    '''
    results = list()
    if continuation is None:
      continuation = ''
    line_length = CHARACTER_LIMIT - len(continuation)
    lines = textwrap.wrap(status, line_length)
    for line in lines[0:-1]:
      results.append(self.PostUpdate(line + continuation, **kwargs))
    results.append(self.PostUpdate(lines[-1], **kwargs))
    return results

  def GetReplies(self, since=None, since_id=None, page=None): 
    '''Get a sequence of status messages representing the 20 most recent
    replies (status updates prefixed with @username) to the authenticating
    user.

    Args:
      page: 
      since:
        Narrows the returned results to just those statuses created
        after the specified HTTP-formatted date. [optional]
      since_id:
        Returns only public statuses with an ID greater than (that is,
        more recent than) the specified ID. [Optional]

    Returns:
      A sequence of twitter.Status instances, one for each reply to the user.
    '''
    url = 'http://twitter.com/statuses/replies.json'
    if not self._username:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    parameters = {}
    if since:
      parameters['since'] = since
    if since_id:
      parameters['since_id'] = since_id
    if page:
      parameters['page'] = page
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [Status.NewFromJsonDict(x) for x in data]

  def GetFriends(self, user=None, page=None):
    '''Fetch the sequence of twitter.User instances, one for each friend.

    Args:
      user: the username or id of the user whose friends you are fetching.  If
      not specified, defaults to the authenticated user. [optional]

    The twitter.Api instance must be authenticated.

    Returns:
      A sequence of twitter.User instances, one for each friend
    '''
    if not self._username:
      raise TwitterError("twitter.Api instance must be authenticated")
    if user:
      url = 'http://twitter.com/statuses/friends/%s.json' % user 
    else:
      url = 'http://twitter.com/statuses/friends.json'
    parameters = {}
    if page:
      parameters['page'] = page
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [User.NewFromJsonDict(x) for x in data]

  def GetFollowers(self, page=None):
    '''Fetch the sequence of twitter.User instances, one for each follower

    The twitter.Api instance must be authenticated.

    Returns:
      A sequence of twitter.User instances, one for each follower
    '''
    if not self._username:
      raise TwitterError("twitter.Api instance must be authenticated")
    url = 'http://twitter.com/statuses/followers.json'
    parameters = {}
    if page:
      parameters['page'] = page
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [User.NewFromJsonDict(x) for x in data]

  def GetFeatured(self):
    '''Fetch the sequence of twitter.User instances featured on twitter.com

    The twitter.Api instance must be authenticated.

    Returns:
      A sequence of twitter.User instances
    '''
    url = 'http://twitter.com/statuses/featured.json'
    json = self._FetchUrl(url)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [User.NewFromJsonDict(x) for x in data]

  def GetUser(self, user):
    '''Returns a single user.

    The twitter.Api instance must be authenticated.

    Args:
      user: The username or id of the user to retrieve.

    Returns:
      A twitter.User instance representing that user
    '''
    url = 'http://twitter.com/users/show/%s.json' % user
    json = self._FetchUrl(url)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return User.NewFromJsonDict(data)

  def GetDirectMessages(self, since=None, since_id=None, page=None):
    '''Returns a list of the direct messages sent to the authenticating user.

    The twitter.Api instance must be authenticated.

    Args:
      since:
        Narrows the returned results to just those statuses created
        after the specified HTTP-formatted date. [optional]
      since_id:
        Returns only public statuses with an ID greater than (that is,
        more recent than) the specified ID. [Optional]

    Returns:
      A sequence of twitter.DirectMessage instances
    '''
    url = 'http://twitter.com/direct_messages.json'
    if not self._username:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    parameters = {}
    if since:
      parameters['since'] = since
    if since_id:
      parameters['since_id'] = since_id
    if page:
      parameters['page'] = page 
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [DirectMessage.NewFromJsonDict(x) for x in data]

  def PostDirectMessage(self, user, text):
    '''Post a twitter direct message from the authenticated user

    The twitter.Api instance must be authenticated.

    Args:
      user: The ID or screen name of the recipient user.
      text: The message text to be posted.  Must be less than 140 characters.

    Returns:
      A twitter.DirectMessage instance representing the message posted
    '''
    if not self._username:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    url = 'http://twitter.com/direct_messages/new.json'
    data = {'text': text, 'user': user}
    json = self._FetchUrl(url, post_data=data)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return DirectMessage.NewFromJsonDict(data)

  def DestroyDirectMessage(self, id):
    '''Destroys the direct message specified in the required ID parameter.

    The twitter.Api instance must be authenticated, and the
    authenticating user must be the recipient of the specified direct
    message.

    Args:
      id: The id of the direct message to be destroyed

    Returns:
      A twitter.DirectMessage instance representing the message destroyed
    '''
    url = 'http://twitter.com/direct_messages/destroy/%s.json' % id
    json = self._FetchUrl(url, post_data={})
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return DirectMessage.NewFromJsonDict(data)

  def CreateFriendship(self, user):
    '''Befriends the user specified in the user parameter as the authenticating user.

    The twitter.Api instance must be authenticated.

    Args:
      The ID or screen name of the user to befriend.
    Returns:
      A twitter.User instance representing the befriended user.
    '''
    url = 'http://twitter.com/friendships/create/%s.json' % user
    json = self._FetchUrl(url, post_data={})
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return User.NewFromJsonDict(data)

  def DestroyFriendship(self, user):
    '''Discontinues friendship with the user specified in the user parameter.

    The twitter.Api instance must be authenticated.

    Args:
      The ID or screen name of the user  with whom to discontinue friendship.
    Returns:
      A twitter.User instance representing the discontinued friend.
    '''
    url = 'http://twitter.com/friendships/destroy/%s.json' % user
    json = self._FetchUrl(url, post_data={})
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return User.NewFromJsonDict(data)

  def CreateFavorite(self, status):
    '''Favorites the status specified in the status parameter as the authenticating user.
    Returns the favorite status when successful.

    The twitter.Api instance must be authenticated.

    Args:
      The twitter.Status instance to mark as a favorite.
    Returns:
      A twitter.Status instance representing the newly-marked favorite.
    '''
    url = 'http://twitter.com/favorites/create/%s.json' % status.id
    json = self._FetchUrl(url, post_data={})
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return Status.NewFromJsonDict(data)

  def DestroyFavorite(self, status):
    '''Un-favorites the status specified in the ID parameter as the authenticating user.
    Returns the un-favorited status in the requested format when successful.

    The twitter.Api instance must be authenticated.

    Args:
      The twitter.Status to unmark as a favorite.
    Returns:
      A twitter.Status instance representing the newly-unmarked favorite.
    '''
    url = 'http://twitter.com/favorites/destroy/%s.json' % status.id
    json = self._FetchUrl(url, post_data={})
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return Status.NewFromJsonDict(data)

  def GetUserByEmail(self, email):
    '''Returns a single user by email address.

    Args:
      email: The email of the user to retrieve.
    Returns:
      A twitter.User instance representing that user
    '''
    url = 'http://twitter.com/users/show.json?email=%s' % email
    json = self._FetchUrl(url)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return User.NewFromJsonDict(data)

  def SetCredentials(self, username, password):
    '''Set the username and password for this instance

    Args:
      username: The twitter username.
      password: The twitter password.
    '''
    self._username = username
    self._password = password

  def ClearCredentials(self):
    '''Clear the username and password for this instance
    '''
    self._username = None
    self._password = None

  def SetCache(self, cache):
    '''Override the default cache.  Set to None to prevent caching.

    Args:
      cache: an instance that supports the same API as the  twitter._FileCache
    '''
    self._cache = cache

  def SetUrllib(self, urllib):
    '''Override the default urllib implementation.

    Args:
      urllib: an instance that supports the same API as the urllib2 module
    '''
    self._urllib = urllib

  def SetCacheTimeout(self, cache_timeout):
    '''Override the default cache timeout.

    Args:
      cache_timeout: time, in seconds, that responses should be reused.
    '''
    self._cache_timeout = cache_timeout

  def SetUserAgent(self, user_agent):
    '''Override the default user agent

    Args:
      user_agent: a string that should be send to the server as the User-agent
    '''
    self._request_headers['User-Agent'] = user_agent

  def SetXTwitterHeaders(self, client, url, version):
    '''Set the X-Twitter HTTP headers that will be sent to the server.

    Args:
      client:
         The client name as a string.  Will be sent to the server as
         the 'X-Twitter-Client' header.
      url:
         The URL of the meta.xml as a string.  Will be sent to the server
         as the 'X-Twitter-Client-URL' header.
      version:
         The client version as a string.  Will be sent to the server
         as the 'X-Twitter-Client-Version' header.
    '''
    self._request_headers['X-Twitter-Client'] = client
    self._request_headers['X-Twitter-Client-URL'] = url
    self._request_headers['X-Twitter-Client-Version'] = version

  def SetSource(self, source):
    '''Suggest the "from source" value to be displayed on the Twitter web site.

    The value of the 'source' parameter must be first recognized by
    the Twitter server.  New source values are authorized on a case by
    case basis by the Twitter development team.

    Args:
      source:
        The source name as a string.  Will be sent to the server as
        the 'source' parameter.
    '''
    self._default_params['source'] = source

  def _BuildUrl(self, url, path_elements=None, extra_params=None):
    # Break url into consituent parts
    (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(url)

    # Add any additional path elements to the path
    if path_elements:
      # Filter out the path elements that have a value of None
      p = [i for i in path_elements if i]
      if not path.endswith('/'):
        path += '/'
      path += '/'.join(p)

    # Add any additional query parameters to the query string
    if extra_params and len(extra_params) > 0:
      extra_query = self._EncodeParameters(extra_params)
      # Add it to the existing query
      if query:
        query += '&' + extra_query
      else:
        query = extra_query

    # Return the rebuilt URL
    return urlparse.urlunparse((scheme, netloc, path, params, query, fragment))

  def _InitializeRequestHeaders(self, request_headers):
    if request_headers:
      self._request_headers = request_headers
    else:
      self._request_headers = {}

  def _InitializeUserAgent(self):
    user_agent = 'Python-urllib/%s (python-twitter/%s)' % \
                 (self._urllib.__version__, __version__)
    self.SetUserAgent(user_agent)

  def _InitializeDefaultParameters(self):
    self._default_params = {}

  def _AddAuthorizationHeader(self, username, password):
    if username and password:
      basic_auth = base64.encodestring('%s:%s' % (username, password))[:-1]
      self._request_headers['Authorization'] = 'Basic %s' % basic_auth

  def _RemoveAuthorizationHeader(self):
    if self._request_headers and 'Authorization' in self._request_headers:
      del self._request_headers['Authorization']

  def _GetOpener(self, url, username=None, password=None):
    if username and password:
      self._AddAuthorizationHeader(username, password)
      handler = self._urllib.HTTPBasicAuthHandler()
      (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(url)
      handler.add_password(Api._API_REALM, netloc, username, password)
      opener = self._urllib.build_opener(handler)
    else:
      opener = self._urllib.build_opener()
    opener.addheaders = self._request_headers.items()
    return opener

  def _Encode(self, s):
    if self._input_encoding:
      return unicode(s, self._input_encoding).encode('utf-8')
    else:
      return unicode(s).encode('utf-8')

  def _EncodeParameters(self, parameters):
    '''Return a string in key=value&key=value form

    Values of None are not included in the output string.

    Args:
      parameters:
        A dict of (key, value) tuples, where value is encoded as
        specified by self._encoding
    Returns:
      A URL-encoded string in "key=value&key=value" form
    '''
    if parameters is None:
      return None
    else:
      return urllib.urlencode(dict([(k, self._Encode(v)) for k, v in parameters.items() if v is not None]))

  def _EncodePostData(self, post_data):
    '''Return a string in key=value&key=value form

    Values are assumed to be encoded in the format specified by self._encoding,
    and are subsequently URL encoded.

    Args:
      post_data:
        A dict of (key, value) tuples, where value is encoded as
        specified by self._encoding
    Returns:
      A URL-encoded string in "key=value&key=value" form
    '''
    if post_data is None:
      return None
    else:
      return urllib.urlencode(dict([(k, self._Encode(v)) for k, v in post_data.items()]))

  def _CheckForTwitterError(self, data):
    """Raises a TwitterError if twitter returns an error message.

    Args:
      data: A python dict created from the Twitter json response
    Raises:
      TwitterError wrapping the twitter error message if one exists.
    """
    # Twitter errors are relatively unlikely, so it is faster
    # to check first, rather than try and catch the exception
    if 'error' in data:
      raise TwitterError(data['error'])

  def _FetchUrl(self,
                url,
                post_data=None,
                parameters=None,
                no_cache=None):
    '''Fetch a URL, optionally caching for a specified time.

    Args:
      url: The URL to retrieve
      post_data: 
        A dict of (str, unicode) key/value pairs.  If set, POST will be used.
      parameters:
        A dict whose key/value pairs should encoded and added 
        to the query string. [OPTIONAL]
      no_cache: If true, overrides the cache on the current request

    Returns:
      A string containing the body of the response.
    '''
    # Build the extra parameters dict
    extra_params = {}
    if self._default_params:
      extra_params.update(self._default_params)
    if parameters:
      extra_params.update(parameters)

    # Add key/value parameters to the query string of the url
    url = self._BuildUrl(url, extra_params=extra_params)

    # Get a url opener that can handle basic auth
    opener = self._GetOpener(url, username=self._username, password=self._password)

    encoded_post_data = self._EncodePostData(post_data)

    # Open and return the URL immediately if we're not going to cache
    if encoded_post_data or no_cache or not self._cache or not self._cache_timeout:
      url_data = opener.open(url, encoded_post_data).read()
      opener.close()
    else:
      # Unique keys are a combination of the url and the username
      if self._username:
        key = self._username + ':' + url
      else:
        key = url

      # See if it has been cached before
      last_cached = self._cache.GetCachedTime(key)

      # If the cached version is outdated then fetch another and store it
      if not last_cached or time.time() >= last_cached + self._cache_timeout:
        url_data = opener.open(url, encoded_post_data).read()
        opener.close()
        self._cache.Set(key, url_data)
      else:
        url_data = self._cache.Get(key)

    # Always return the latest version
    return url_data


class _FileCacheError(Exception):
  '''Base exception class for FileCache related errors'''

class _FileCache(object):

  DEPTH = 3

  def __init__(self,root_directory=None):
    self._InitializeRootDirectory(root_directory)

  def Get(self,key):
    path = self._GetPath(key)
    if os.path.exists(path):
      return open(path).read()
    else:
      return None

  def Set(self,key,data):
    path = self._GetPath(key)
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
      os.makedirs(directory)
    if not os.path.isdir(directory):
      raise _FileCacheError('%s exists but is not a directory' % directory)
    temp_fd, temp_path = tempfile.mkstemp()
    temp_fp = os.fdopen(temp_fd, 'w')
    temp_fp.write(data)
    temp_fp.close()
    if not path.startswith(self._root_directory):
      raise _FileCacheError('%s does not appear to live under %s' %
                            (path, self._root_directory))
    if os.path.exists(path):
      os.remove(path)
    os.rename(temp_path, path)

  def Remove(self,key):
    path = self._GetPath(key)
    if not path.startswith(self._root_directory):
      raise _FileCacheError('%s does not appear to live under %s' %
                            (path, self._root_directory ))
    if os.path.exists(path):
      os.remove(path)

  def GetCachedTime(self,key):
    path = self._GetPath(key)
    if os.path.exists(path):
      return os.path.getmtime(path)
    else:
      return None

  def _GetUsername(self):
    '''Attempt to find the username in a cross-platform fashion.'''
    try:
      return os.getenv('USER') or \
             os.getenv('LOGNAME') or \
             os.getenv('USERNAME') or \
             os.getlogin() or \
             'nobody'
    except (IOError, OSError), e:
      return 'nobody'

  def _GetTmpCachePath(self):
    username = self._GetUsername()
    cache_directory = 'python.cache_' + username
    return os.path.join(tempfile.gettempdir(), cache_directory)

  def _InitializeRootDirectory(self, root_directory):
    if not root_directory:
      root_directory = self._GetTmpCachePath()
    root_directory = os.path.abspath(root_directory)
    if not os.path.exists(root_directory):
      os.mkdir(root_directory)
    if not os.path.isdir(root_directory):
      raise _FileCacheError('%s exists but is not a directory' %
                            root_directory)
    self._root_directory = root_directory

  def _GetPath(self,key):
    try:
        hashed_key = md5(key).hexdigest()
    except TypeError:
        hashed_key = md5.new(key).hexdigest()
        
    return os.path.join(self._root_directory,
                        self._GetPrefix(hashed_key),
                        hashed_key)

  def _GetPrefix(self,hashed_key):
    return os.path.sep.join(hashed_key[0:_FileCache.DEPTH])

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.auth.models import User

class AuthMeta(models.Model):
    """Metadata for Authentication"""
    def __unicode__(self):
        return '%s - %s' % (self.user, self.provider)
    
    user = models.ForeignKey(User)
    provider = models.CharField(max_length=200)
    is_email_filled = models.BooleanField(default=False)
    is_profile_modified = models.BooleanField(default=False)

class OpenidProfile(models.Model):
    """A class associating an User to a Openid"""
    openid_key = models.CharField(max_length=200, unique=True, db_index=True)
    
    user = models.ForeignKey(User, related_name='openid_profiles')
    is_username_valid = models.BooleanField(default=False)
    #Values which we get from openid.sreg
    email = models.EmailField()
    nickname = models.CharField(max_length=100)
    
    
    def __unicode__(self):
        return unicode(self.openid_key)
    
    def __repr__(self):
        return unicode(self.openid_key)
    
class LinkedInUserProfile(models.Model):
    """
    For users who login via Linkedin.
    """
    linkedin_uid = models.CharField(max_length=50,
                                    unique=True,
                                    db_index=True)

    user = models.ForeignKey(User, related_name='linkedin_profiles')
    headline = models.CharField(max_length=120, blank=True, null=True)
    company = models.CharField(max_length=255, blank=True, null=True)
    location = models.TextField(blank=True, null=True)
    industry = models.CharField(max_length=255, blank=True, null=True)
    profile_image_url = models.URLField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    access_token = models.CharField(max_length=255,
                                    blank=True,
                                    null=True,
                                    editable=False)

    def __unicode__(self):
        return "%s's profile" % self.user

class TwitterUserProfile(models.Model):
    """
    For users who login via Twitter.
    """
    screen_name = models.CharField(max_length=200,
                                   unique=True,
                                   db_index=True)
    
    user = models.ForeignKey(User, related_name='twitter_profiles')
    access_token = models.CharField(max_length=255,
                                    blank=True,
                                    null=True,
                                    editable=False)
    profile_image_url = models.URLField(blank=True, null=True)
    location = models.TextField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    description = models.CharField(max_length=160, blank=True, null=True)

    def __unicode__(self):
        return "%s's profile" % self.user
        

class FacebookUserProfile(models.Model):
    """
    For users who login via Facebook.
    """
    facebook_uid = models.CharField(max_length=20,
                                    unique=True,
                                    db_index=True)
    
    user = models.ForeignKey(User, related_name='facebook_profiles')
    profile_image_url = models.URLField(blank=True, null=True)
    profile_image_url_big = models.URLField(blank=True, null=True)
    profile_image_url_small = models.URLField(blank=True, null=True)
    location = models.TextField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    about_me = models.CharField(max_length=160, blank=True, null=True)
    
    def __unicode__(self):
        return "%s's profile" % self.user

class GithubUserProfile(models.Model):
    user = models.ForeignKey(User)
    access_token = models.CharField(max_length=100, blank=True, null=True, editable=False)

    def __unicode__(self):
        return "%s's profile" % self.user

class FoursquareUserProfile(models.Model):
    user = models.ForeignKey(User)
    access_token = models.CharField(max_length=255, blank=True, null=True, editable=False)

    def __unicode__(self):
        return "%s's profile" % self.user

########NEW FILE########
__FILENAME__ = socialauth_tags
from django import  template

register = template.Library()

@register.simple_tag
def get_calculated_username(user):
    if hasattr(user, 'openidprofile_set') and user.openidprofile_set.filter().count():
        if user.openidprofile_set.filter(is_username_valid = True).count():
            return user.openidprofile_set.filter(is_username_valid = True)[0].user.username
        else:
            from django.core.urlresolvers import  reverse
            editprof_url = reverse('socialauth_editprofile')
            return u'Anonymous User. <a href="%s">Add name</a>'%editprof_url
    else:
        return user.username

########NEW FILE########
__FILENAME__ = tests
from selenium import selenium
import unittest
from django.contrib.auth.models import User

from test_data import *

class TwitterTester(unittest.TestCase):
    def setUp(self):
        self.verificationErrors = []
        self.selenium = selenium("localhost", 4444, "*chrome", test_base_url)
        self.selenium.start()
    
    def testTwitter(self):
        sel = self.selenium
        #Test that a user is created after 
        #    logging in via Twitter for the first time.
        initial_user_count = User.objects.count()
        sel.open("/accounts/login/")
        sel.click("link=Login via twitter")
        sel.wait_for_page_to_load("30000")
        try:
            sel.click("link=Sign out")
            sel.wait_for_page_to_load("30000")
        except:
            pass
        sel.type("username_or_email", twitter_username)
        sel.type("session[password]", twitter_password)
        sel.click("allow")
        sel.wait_for_page_to_load("30000")
        sel.open("/accounts/login/")
        sel.open("/accounts/edit/profile/")
        self.assertEqual(initial_user_count + 1, User.objects.count())
        
    
    def tearDown(self):
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)
        

class OpenIdTester(unittest.TestCase):
    def setUp(self):
        self.verificationErrors = []
        self.selenium = selenium("localhost", 4444, "*chrome", test_base_url)
        self.selenium.start()
    
    def testOpenId(self):
        initial_user_count = User.objects.count()
        sel = self.selenium
        sel.open("/accounts/login/")
        sel.click("openid_login_link")
        sel.wait_for_page_to_load("30000")
        sel.type("openid_url", myopenid_url)
        sel.click("//input[@value='Sign in']")
        sel.wait_for_page_to_load("30000")
        try:
            sel.type("password", myopenid_password)
            sel.click("signin_button")
            sel.wait_for_page_to_load("30000")
        except:
            sel.click("continue-button")
        sel.wait_for_page_to_load("30000")
        sel.open("/accounts/login/")
        self.assertEqual(initial_user_count + 1, User.objects.count())
    
    def tearDown(self):
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)

if __name__ == "__main__":
    unittest.main()



if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from openid_consumer.views import complete, signout
from django.views.generic.base import TemplateView

#Login Views
urlpatterns = patterns('socialauth.views',
    url(r'^facebook_login/xd_receiver.htm$', TemplateView.as_view(template_name='socialauth/xd_receiver.htm'), name='socialauth_xd_receiver'),
    url(r'^facebook_login/$', 'facebook_login', name='socialauth_facebook_login'),
    url(r'^facebook_login/done/$', 'facebook_login_done', name='socialauth_facebook_login_done'),
    url(r'^login/$', 'login_page', name='socialauth_login_page'),
    url(r'^openid_login/$', 'openid_login_page', name='socialauth_openid_login_page'),
    url(r'^twitter_login/$', 'twitter_login', name='socialauth_twitter_login'),
    url(r'^twitter_login/done/$', 'twitter_login_done', name='socialauth_twitter_login_done'),
    url(r'^linkedin_login/$', 'linkedin_login', name='socialauth_linkedin_login'),
    url(r'^linkedin_login/done/$', 'linkedin_login_done', name='socialauth_linkedin_login_done'),
    url(r'^yahoo_login/$', 'yahoo_login', name='socialauth_yahoo_login'),
    url(r'^yahoo_login/complete/$', complete, name='socialauth_yahoo_complete'),
    url(r'^gmail_login/$', 'gmail_login', name='socialauth_google_login'),
    url(r'^gmail_login/complete/$', complete, name='socialauth_google_complete'),
    url(r'^openid/$', 'openid_login', name='socialauth_openid_login'),
    url(r'^openid/complete/$', complete, name='socialauth_openid_complete'),
    url(r'^openid/signout/$', signout, name='openid_signout'),
    url(r'^openid/done/$', 'openid_done', name='openid_openid_done'),
    url(r'^github_login/$', 'github_login', name='github_login'),
    url(r'github_login/done/$', 'github_login_done', name='github_login_done'),
    url(r'^foursquare_login/$', 'foursquare_login', name='foursquare_login'),
    url(r'^foursquare_login/done/$', 'foursquare_login_done', name='foursquare_login_done'),
)

#Other views.
urlpatterns += patterns('socialauth.views',
    url(r'^$', 'login_page', name='socialauth_index'),
    url(r'^done/$', 'signin_complete', name='socialauth_signin_complete'),
    url(r'^edit/profile/$', 'editprofile',  name='socialauth_editprofile'),
    url(r'^logout/$', 'social_logout',  name='socialauth_social_logout'),
)


########NEW FILE########
__FILENAME__ = views
import logging
import urllib
from oauth import oauth

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth import authenticate, login
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import logout

from socialauth.models import AuthMeta
from socialauth.forms import EditProfileForm

from openid_consumer.views import begin
from socialauth.lib import oauthtwitter2 as oauthtwitter

from socialauth.lib.linkedin import *
from socialauth.lib.github import GithubClient
from socialauth.lib import foursquare

LINKEDIN_CONSUMER_KEY = getattr(settings, 'LINKEDIN_CONSUMER_KEY', '')
LINKEDIN_CONSUMER_SECRET = getattr(settings, 'LINKEDIN_CONSUMER_SECRET', '')

ADD_LOGIN_REDIRECT_URL = getattr(settings, 'ADD_LOGIN_REDIRECT_URL', '')
LOGIN_REDIRECT_URL = getattr(settings, 'LOGIN_REDIRECT_URL', '')
LOGIN_URL = getattr(settings, 'LOGIN_URL', '')

TWITTER_CONSUMER_KEY = getattr(settings, 'TWITTER_CONSUMER_KEY', '')
TWITTER_CONSUMER_SECRET = getattr(settings, 'TWITTER_CONSUMER_SECRET', '')

FACEBOOK_APP_ID = getattr(settings, 'FACEBOOK_APP_ID', '')
FACEBOOK_API_KEY = getattr(settings, 'FACEBOOK_API_KEY', '')
FACEBOOK_SECRET_KEY = getattr(settings, 'FACEBOOK_SECRET_KEY', '')



def del_dict_key(src_dict, key):
    if key in src_dict:
        del src_dict[key]

def login_page(request):
    return render_to_response('socialauth/login_page.html', 
                              {'next': request.GET.get('next', LOGIN_REDIRECT_URL)}, 
                              context_instance=RequestContext(request))

def linkedin_login(request):
    linkedin = LinkedIn(LINKEDIN_CONSUMER_KEY, LINKEDIN_CONSUMER_SECRET)
    request_token = linkedin.getRequestToken(callback=request.build_absolute_uri(reverse('socialauth_linkedin_login_done')))
    request.session['linkedin_request_token'] = request_token
    signin_url = linkedin.getAuthorizeUrl(request_token)
    return HttpResponseRedirect(signin_url)

def linkedin_login_done(request):
    request_token = request.session.get('linkedin_request_token', None)

    # If there is no request_token for session
    # Means we didn't redirect user to linkedin
    if not request_token:
        # Send them to the login page
        return HttpResponseRedirect(reverse("socialauth_login_page"))
    try:
        linkedin = LinkedIn(settings.LINKEDIN_CONSUMER_KEY, settings.LINKEDIN_CONSUMER_SECRET)
        verifier = request.GET.get('oauth_verifier', None)
        access_token = linkedin.getAccessToken(request_token,verifier)

        request.session['access_token'] = access_token
        user = authenticate(linkedin_access_token=access_token)
    except:
        user = None

    # if user is authenticated then login user
    if user:
        login(request, user)
    else:
        # We were not able to authenticate user
        # Redirect to login page
        del_dict_key(request.session, 'access_token')
        del_dict_key(request.session, 'request_token')
        return HttpResponseRedirect(reverse('socialauth_login_page'))

    # authentication was successful, user is now logged in
    return HttpResponseRedirect(LOGIN_REDIRECT_URL)

def twitter_login(request):
    next = request.GET.get('next', None)
    if next:
        request.session['twitter_login_next'] = next
    
    twitter = oauthtwitter.TwitterOAuthClient(settings.TWITTER_CONSUMER_KEY, settings.TWITTER_CONSUMER_SECRET)
    request_token = twitter.fetch_request_token(callback=request.build_absolute_uri(reverse('socialauth_twitter_login_done')))
    request.session['request_token'] = request_token.to_string()
    signin_url = twitter.authorize_token_url(request_token)
    return HttpResponseRedirect(signin_url)

def twitter_login_done(request):
    request_token = request.session.get('request_token', None)
    verifier = request.GET.get('oauth_verifier', None)
    denied = request.GET.get('denied', None)
    
    # If we've been denied, put them back to the signin page
    # They probably meant to sign in with facebook >:D
    if denied:
        return HttpResponseRedirect(reverse("socialauth_login_page"))

    # If there is no request_token for session,
    # Means we didn't redirect user to twitter
    if not request_token:
        # Redirect the user to the login page,
        return HttpResponseRedirect(reverse("socialauth_login_page"))

    token = oauth.OAuthToken.from_string(request_token)

    # If the token from session and token from twitter does not match
    # means something bad happened to tokens
    if token.key != request.GET.get('oauth_token', 'no-token'):
        del_dict_key(request.session, 'request_token')
        # Redirect the user to the login page
        return HttpResponseRedirect(reverse("socialauth_login_page"))

    try:
        twitter = oauthtwitter.TwitterOAuthClient(settings.TWITTER_CONSUMER_KEY, settings.TWITTER_CONSUMER_SECRET)
        access_token = twitter.fetch_access_token(token, verifier)

        request.session['access_token'] = access_token.to_string()
        user = authenticate(twitter_access_token=access_token)
    except:
        user = None
  
    # if user is authenticated then login user
    if user:
        login(request, user)
    else:
        # We were not able to authenticate user
        # Redirect to login page
        del_dict_key(request.session, 'access_token')
        del_dict_key(request.session, 'request_token')
        return HttpResponseRedirect(reverse('socialauth_login_page'))

    # authentication was successful, use is now logged in
    next = request.session.get('twitter_login_next', None)
    if next:
        del_dict_key(request.session, 'twitter_login_next')
        return HttpResponseRedirect(next)
    else:
        return HttpResponseRedirect(LOGIN_REDIRECT_URL)

def openid_login(request):
    if 'openid_next' in request.GET:
        request.session['openid_next'] = request.GET.get('openid_next')
    if 'openid_identifier' in request.GET:
        user_url = request.GET.get('openid_identifier')
        request.session['openid_provider'] = user_url
        return begin(request, user_url=user_url)
    else:
        request.session['openid_provider'] = 'Openid'
        return begin(request)

def gmail_login(request):
    request.session['openid_provider'] = 'Google'
    return begin(request, user_url='https://www.google.com/accounts/o8/id')

def gmail_login_complete(request):
    pass


def yahoo_login(request):
    request.session['openid_provider'] = 'Yahoo'
    return begin(request, user_url='https://me.yahoo.com/')

def openid_done(request, provider=None):
    """
    When the request reaches here, the user has completed the Openid
    authentication flow. He has authorised us to login via Openid, so
    request.openid is populated.
    After coming here, we want to check if we are seeing this openid first time.
    If we are, we will create a new Django user for this Openid, else login the
    existing openid.
    """
    
    if not provider:
        provider = request.session.get('openid_provider', '')
    if hasattr(request,'openid') and request.openid:
        #check for already existing associations
        openid_key = str(request.openid)
    
        #authenticate and login
        try:
            user = authenticate(openid_key=openid_key, request=request, provider=provider)
        except:
            user = None
        
        if user:
            login(request, user)
            if 'openid_next' in request.session :
                openid_next = request.session.get('openid_next')
                if len(openid_next.strip()) >  0 :
                    return HttpResponseRedirect(openid_next)
            return HttpResponseRedirect(LOGIN_REDIRECT_URL)
            # redirect_url = reverse('socialauth_editprofile')
            # return HttpResponseRedirect(redirect_url)
        else:
            return HttpResponseRedirect(LOGIN_URL)
    else:
        return HttpResponseRedirect(LOGIN_URL)

def facebook_login(request):
    """
    Facebook login page
    """
    next = request.GET.get('next', None)
    if next:
        request.session['facebook_login_next'] = next
    
    if request.REQUEST.get("device"):
        device = request.REQUEST.get("device")
    else:
        device = "user-agent"

    params = {}
    params["client_id"] = FACEBOOK_APP_ID
    params["redirect_uri"] = request.build_absolute_uri(reverse("socialauth_facebook_login_done"))

    url = "https://graph.facebook.com/oauth/authorize?"+urllib.urlencode(params)

    return HttpResponseRedirect(url)

def facebook_login_done(request):
    user = authenticate(request=request)

    if not user:
        request.COOKIES.pop(FACEBOOK_API_KEY + '_session_key', None)
        request.COOKIES.pop(FACEBOOK_API_KEY + '_user', None)

        # TODO: maybe the project has its own login page?
        logging.debug("SOCIALAUTH: Couldn't authenticate user with Django, redirecting to Login page")
        return HttpResponseRedirect(reverse('socialauth_login_page'))

    login(request, user)
    
    logging.debug("SOCIALAUTH: Successfully logged in with Facebook!")
    
    next = request.GET.get('next')
    if not next:
        next = request.session.get('facebook_login_next')
        del_dict_key(request.session, 'facebook_login_next')
    
    if next:
        return HttpResponseRedirect(next)
    else:
        return HttpResponseRedirect(LOGIN_REDIRECT_URL)

def openid_login_page(request):
    return render_to_response('openid/index.html', context_instance=RequestContext(request))

@login_required
def signin_complete(request):
    return render_to_response('socialauth/signin_complete.html', context_instance=RequestContext(request))

@login_required
def editprofile(request):
    if request.method == 'POST':
        edit_form = EditProfileForm(user=request.user, data=request.POST)
        if edit_form.is_valid():
            user = edit_form.save()
            try:
                user.authmeta.is_profile_modified = True
                user.authmeta.save()
            except AuthMeta.DoesNotExist:
                pass
            if hasattr(user,'openidprofile_set') and user.openidprofile_set.count():
                openid_profile = user.openidprofile_set.all()[0]
                openid_profile.is_valid_username = True
                openid_profile.save()
            try:
                #If there is a profile. notify that we have set the username
                profile = user.get_profile()
                profile.is_valid_username = True
                profile.save()
            except:
                pass
            request.user.message_set.create(message='Your profile has been updated.')
            return HttpResponseRedirect('.')
    if request.method == 'GET':
        edit_form = EditProfileForm(user=request.user)

    payload = {'edit_form':edit_form}
    return render_to_response('socialauth/editprofile.html', payload, RequestContext(request))

def social_logout(request):
    # Todo
    # still need to handle FB cookies, session etc.

    # let the openid_consumer app handle openid-related cleanup
    from openid_consumer.views import signout as oid_signout
    oid_signout(request)

    # normal logout
    logout_response = logout(request)

    if 'next' in request.GET:
        response = HttpResponseRedirect(request.GET.get('next'))
    elif getattr(settings, 'LOGOUT_REDIRECT_URL', None):
        response = HttpResponseRedirect(settings.LOGOUT_REDIRECT_URL)
    else:
        response = logout_response

    # Delete the facebook cookie
    response.delete_cookie("fbs_" + FACEBOOK_APP_ID)

    return response

def github_login(request):
    github_client = GithubClient()
    authorize_url = github_client.get_authorize_url()  
    return HttpResponseRedirect(authorize_url)

def github_login_done(request):
    try:
        code = request.GET['code']
    except:
        """Either github did not respond properly
        or someone is playing with this url"""
        return HttpResponseRedirect(LOGIN_URL)
    github_client = GithubClient()
    access_token = github_client.get_access_token(code)
    try:
        user = authenticate(github_access_token=access_token)
    except:
        user = None
    if user:
        login(request, user)
        return HttpResponseRedirect(LOGIN_REDIRECT_URL)
    return HttpResponseRedirect(LOGIN_URL) 

def foursquare_login(request):
    foursquare_client = foursquare.FourSquareClient()
    return HttpResponseRedirect(foursquare_client.get_authentication_url())

def foursquare_login_done(request):
    try:
        code = request.GET.get('code')
    except:
        """Some error ocurred.
        Rediect to login page"""
        return HttpResponseRedirect(LOGIN_URL)
    request.session['foursquare_code'] = code
    foursquare_client = foursquare.FourSquareClient()
    access_token_response = foursquare_client.get_access_token(request.session['foursquare_code'])
    import json
    access_token = json.loads(access_token_response)['access_token'] 
    try:
        user = authenticate(foursquare_access_token=access_token)
    except:
        user=None
    if user:
        login(request, user)
        return HttpResponseRedirect(LOGIN_REDIRECT_URL)
    return HttpResponseRedirect(LOGIN_URL) 

########NEW FILE########
