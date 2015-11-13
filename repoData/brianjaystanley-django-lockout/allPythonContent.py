__FILENAME__ = decorators
"""
Lockout Decorators
"""

########################################################################

from django.utils.functional import wraps
from django.core.cache import cache
from middleware import thread_namespace
from exceptions import LockedOut
from utils import generate_base_key
import settings

########################################################################

def enforce_lockout(function):
    """Wraps the provided ``function`` (django.contrib.auth.authenticate) to
    enforce lockout if the max attempts is exceeded.
    """

    def wrapper(*args, **kwargs):
        # Get request details from thread local
        request = getattr(thread_namespace, 'lockoutrequest', None)
        
        if request is None:
            # The call to authenticate must not have come via an HttpRequest, so
            # lockout is not enforced.
            return function(*args, **kwargs)

        params = []
        ip = request.META.get('HTTP_X_FORWARDED_FOR', None)
        if ip:
            # X_FORWARDED_FOR returns client1, proxy1, proxy2,...
            ip = ip.split(', ')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        params.append(ip)
        if settings.USE_USER_AGENT:
            useragent = request.META.get('HTTP_USER_AGENT', '')
            params.append(useragent)
        
        key = generate_base_key(*params)
        attempts = cache.get(key) or 0
        
        if attempts >= settings.MAX_ATTEMPTS:
            raise LockedOut()
        
        result = function(*args, **kwargs)
        
        if result is None:
            try:
                attempts = cache.incr(key)
            except ValueError:
                # No such key, so set it
                cache.set(key, 1, settings.ENFORCEMENT_WINDOW)
            
            # If attempts is max allowed, set a new key with that
            # value so that the lockout time will be based on the most
            # recent login attempt.
            if attempts >= settings.MAX_ATTEMPTS:
                cache.set(key, attempts, settings.LOCKOUT_TIME)
        
        return result
    
    return wraps(function)(wrapper)

########################################################################
########NEW FILE########
__FILENAME__ = exceptions
"""
Lockout Exceptions
"""

class LockedOut(Exception):
    pass

########NEW FILE########
__FILENAME__ = middleware
"""
Lockout Middleware
"""

########################################################################

from threading import local
thread_namespace = local()

class LockoutMiddleware(object):
    """Decorates django.contrib.auth.authenticate with enforce_lockout, and
    adds the request to thread local so the decorator can access request
    details.
    """
    
    __state = {} # Borg pattern
    
    def __init__(self):
        self.__dict__ = self.__state
        self.installed = getattr(self, 'installed', False)
        if not self.installed:
            # Import here to avoid circular import.
            from decorators import enforce_lockout
            from django.contrib import auth
            auth.authenticate = enforce_lockout(auth.authenticate)
            self.installed = True

    ####################################################################
    
    def process_request(self, request):
        thread_namespace.lockoutrequest = request
        
    def process_response(self, request, response):
        # If a previous middleware returned a response or raised an exception,
        # our process_request won't have gotten called, so check before
        # deleting.
        if hasattr(thread_namespace, 'lockoutrequest'):
            delattr(thread_namespace, 'lockoutrequest')
        return response
        
########################################################################

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

MAX_ATTEMPTS = getattr(settings, 'LOCKOUT_MAX_ATTEMPTS', 5)
LOCKOUT_TIME = getattr(settings, 'LOCKOUT_TIME', 60 * 10) # 10 minutes
ENFORCEMENT_WINDOW = getattr(settings, 'LOCKOUT_ENFORCEMENT_WINDOW', 60 * 5) # 5 minutes
USE_USER_AGENT = getattr(settings, 'LOCKOUT_USE_USER_AGENT', False)
CACHE_PREFIX = getattr(settings, 'LOCKOUT_CACHE_PREFIX', 'lockout')
########NEW FILE########
__FILENAME__ = tests
"""
Lockout Tests
"""

########################################################################

from django.test import TestCase
from django.test.client import RequestFactory
from django.contrib.auth.models import User
from django.contrib import auth
from django.conf import settings
import settings as lockout_settings
from middleware import LockoutMiddleware
from exceptions import LockedOut
from utils import reset_attempts
import time

########################################################################

class LockoutTestCase(TestCase):
    """Test case for lockout functionality. Requires django.contrib.auth.
    """
    
    username = 'testlockoutuser'
    password = 'testpassword'
    badpassword = 'badpassword'
    ip1 = '64.147.222.137'
    ip2 = '168.212.226.204'
    useragent1 = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:6.0a2) Gecko/20110613 Firefox/6.0a2'
    useragent2 = 'Mozilla/5.0 (compatible; MSIE 8.0; Windows NT 5.2; Trident/4.0; Media Center PC 4.0; SLCC1; .NET CLR 3.0.04320)'
    
    ####################################################################
    
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = LockoutMiddleware()
        self.user = User.objects.create_user(
            self.username, 'testlockoutuser@email.com', self.password)
        self.badcredentials = dict(username=self.username, password=self.badpassword)
        self.goodcredentials = dict(username=self.username, password=self.password)
        
        self.MAX_ATTEMPTS_ORIG = lockout_settings.MAX_ATTEMPTS
        self.USE_USER_AGENT_ORIG = lockout_settings.USE_USER_AGENT
        self.LOCKOUT_TIME_ORIG = lockout_settings.LOCKOUT_TIME
        self.ENFORCEMENT_WINDOW_ORIG = lockout_settings.ENFORCEMENT_WINDOW
        lockout_settings.MAX_ATTEMPTS = 2
        lockout_settings.USE_USER_AGENT = True
        lockout_settings.LOCKOUT_TIME = 2
        lockout_settings.ENFORCEMENT_WINDOW = 3
    
    ####################################################################
    
    def tearDown(self):
        # Clear the lockout keys from the cache and restore lockout settings
        for ip in (self.ip1, self.ip2):
            for useragent in (self.useragent1, self.useragent2):
                request = self.factory.post(settings.LOGIN_URL, REMOTE_ADDR=ip, 
                                            HTTP_USER_AGENT=useragent)
                reset_attempts(request)
        
        lockout_settings.MAX_ATTEMPTS = self.MAX_ATTEMPTS_ORIG
        lockout_settings.USE_USER_AGENT = self.USE_USER_AGENT_ORIG
        lockout_settings.LOCKOUT_TIME = self.LOCKOUT_TIME_ORIG
        lockout_settings.ENFORCEMENT_WINDOW = self.ENFORCEMENT_WINDOW_ORIG
        
    
    ####################################################################
        
    def authenticate(self, request, **credentials):
        """Wraps auth.authenticate with LockoutMiddleware, since the
        tests do not trigger the middleware.
        """
        self.middleware.process_request(request)
        user = auth.authenticate(**credentials)
        self.middleware.process_response(None, None)
        return user
        
    ####################################################################
    
    def test_valid_login_allowed(self):
        """Sanity check that a valid login is not locked out.
        """
        request = self.factory.post(settings.LOGIN_URL, REMOTE_ADDR=self.ip1, 
                                    HTTP_USER_AGENT=self.useragent1)
        user = self.authenticate(request, **self.goodcredentials)
        self.assertEqual(user, self.user)
    
    ####################################################################
    
    def test_max_attempts(self):
        """Tests that the user is locked out after exceeding the max attempts.
        """
        meta = dict(REMOTE_ADDR=self.ip1, HTTP_USER_AGENT=self.useragent1)
        
        for i in range(lockout_settings.MAX_ATTEMPTS):
            request = self.factory.post(settings.LOGIN_URL, **meta)
            user = self.authenticate(request, **self.badcredentials)
            
        request = self.factory.post(settings.LOGIN_URL, **meta)
        # User should be locked out even with a valid login.
        self.assertRaises(LockedOut, self.authenticate, request, **self.goodcredentials)
    
    ####################################################################
    
    def test_lockout_time(self):
        """Tests that the user is locked out for the appropriate length of time.
        """
        meta = dict(REMOTE_ADDR=self.ip1, HTTP_USER_AGENT=self.useragent1)
        
        for i in range(lockout_settings.MAX_ATTEMPTS):
            request = self.factory.post(settings.LOGIN_URL, **meta)
            user = self.authenticate(request, **self.badcredentials)
           
        request = self.factory.post(settings.LOGIN_URL, **meta)
        self.assertRaises(LockedOut, self.authenticate, request, **self.badcredentials)
        
        # Let the lockout expire and retry.
        time.sleep(lockout_settings.LOCKOUT_TIME)
        
        request = self.factory.post(settings.LOGIN_URL, **meta)
        user = self.authenticate(request, **self.goodcredentials)
        self.assertEqual(user, self.user)
        
    ####################################################################
    
    def test_enforcement_window(self):
        """Tests that, after the enforcement window ends, the user gets a fresh start.
        """          
        meta = dict(REMOTE_ADDR=self.ip1, HTTP_USER_AGENT=self.useragent1)
        
        request = self.factory.post(settings.LOGIN_URL, **meta)
        user = self.authenticate(request, **self.badcredentials)
        
        # Let the enforcement window expire.
        time.sleep(lockout_settings.ENFORCEMENT_WINDOW)
        
        # The user is now allowed the max attempts without a lockout.
        for i in range(lockout_settings.MAX_ATTEMPTS):
            request = self.factory.post(settings.LOGIN_URL, **meta)
            user = self.authenticate(request, **self.badcredentials)
    
    ####################################################################
    
    def test_different_ips(self):
        """Tests that a lockout of one IP does not affect requests from a
        different IP.
        """
        meta = dict(REMOTE_ADDR=self.ip1, HTTP_USER_AGENT=self.useragent1)
        
        for i in range(lockout_settings.MAX_ATTEMPTS):
            request = self.factory.post(settings.LOGIN_URL, **meta)
            user = self.authenticate(request, **self.badcredentials)
        
        # IP2 is not locked out...
        request = self.factory.post(settings.LOGIN_URL, REMOTE_ADDR=self.ip2, 
                                    HTTP_USER_AGENT=self.useragent1)
        user = self.authenticate(request, **self.goodcredentials)
        self.assertEqual(user, self.user)
        
        # ...even though IP1 is.
        request = self.factory.post(settings.LOGIN_URL, **meta)
        self.assertRaises(LockedOut, self.authenticate, request, **self.goodcredentials)
        
    ####################################################################
    
    def test_use_user_agent(self):
        """Tests that a user from the same IP but with a different user agent
        is not locked out, if USE_USER_AGENT is True.
        """
        self.assertTrue(lockout_settings.USE_USER_AGENT)
        
        meta = dict(REMOTE_ADDR=self.ip1, HTTP_USER_AGENT=self.useragent1)
        
        for i in range(lockout_settings.MAX_ATTEMPTS):
            request = self.factory.post(settings.LOGIN_URL, **meta)
            user = self.authenticate(request, **self.badcredentials)
        
        # User agent 2 is not locked out...
        request = self.factory.post(settings.LOGIN_URL, REMOTE_ADDR=self.ip1, 
                                    HTTP_USER_AGENT=self.useragent2)
        user = self.authenticate(request, **self.goodcredentials)
        self.assertEqual(user, self.user)
        
        # ...even though user agent 1 is.
        request = self.factory.post(settings.LOGIN_URL, **meta)
        self.assertRaises(LockedOut, self.authenticate, request, **self.goodcredentials)
        
    ####################################################################
    
    def test_ignore_user_agent(self):
        """Tests that a user from the same IP but with a different user agent
        is locked out, if USE_USER_AGENT is False.
        """
        lockout_settings.USE_USER_AGENT = False
        
        meta = dict(REMOTE_ADDR=self.ip1, HTTP_USER_AGENT=self.useragent1)
        
        for i in range(lockout_settings.MAX_ATTEMPTS):
            request = self.factory.post(settings.LOGIN_URL, **meta)
            user = self.authenticate(request, **self.badcredentials)
        
        # User agent 2 from same IP is locked out
        request = self.factory.post(settings.LOGIN_URL, REMOTE_ADDR=self.ip1, 
                                    HTTP_USER_AGENT=self.useragent2)
        self.assertRaises(LockedOut, self.authenticate, request, **self.goodcredentials)
        
########################################################################
########NEW FILE########
__FILENAME__ = utils
"""
Lockout Utils
"""
########################################################################

try:
    from hashlib import md5
except ImportError:
    from md5 import md5
from django.core.cache import cache
import settings
import re

########################################################################

WHITESPACE = re.compile('\s')

def generate_base_key(*params):
    """Generates a base key to be used for caching, containing the
    CACHE_PREFIX and the request ``params``, plus a hexdigest. The base key
    will later be combined with any required version or prefix.
    """    
    raw_key = ";".join(params)
    digest = md5(raw_key).hexdigest()
    
    # Whitespace is stripped but the hexdigest ensures uniqueness
    key = '%(prefix)s_%(raw_key)s_%(digest)s' % dict(
        prefix=settings.CACHE_PREFIX,
        raw_key=WHITESPACE.sub('', raw_key)[:125], 
        digest=digest)
    
    return key

########################################################################

def reset_attempts(request):
    """Clears the cache key for the specified ``request``.
    """
    params = []
    ip = request.META.get('HTTP_X_FORWARDED_FOR', None)
    if ip:
        # X_FORWARDED_FOR returns client1, proxy1, proxy2,...
        ip = ip.split(', ')[0]
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    params.append(ip)
    if settings.USE_USER_AGENT:
        useragent = request.META.get('HTTP_USER_AGENT', '')
        params.append(useragent)
        
    key = generate_base_key(*params)
    cache.delete(key)
    
########################################################################
########NEW FILE########
