__FILENAME__ = website
"""
aspen.algorithms.website
~~~~~~~~~~~~~~~~~~~~~~~~

These functions comprise the request processing functionality of Aspen.

Per the algorithm.py module, the functions defined in this present module are
executed in the order they're defined here, with dependencies injected as
specified in each function definition. Each function should return None, or a
dictionary that will be used to update the algorithm state in the calling
routine.

The naming convention we've adopted for the functions in this file is:

    verb_object_preposition_object-of-preposition

For example:

    parse_environ_into_request

All four parts are a single word each (there are exactly three underscores in
each function name). This convention is intended to make function names easy to
understand and remember.

It's important that function names remain relatively stable over time, as
downstream applications are expected to insert their own functions into this
algorithm based on the names of our functions here. A change in function names
or ordering here would constitute a backwards-incompatible change.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import traceback

import aspen
from aspen import dispatcher, resources
from aspen.http.request import Request
from aspen.http.response import Response
from aspen import typecasting
from first import first as _first


def parse_environ_into_request(environ):
    return {'request': Request.from_wsgi(environ)}


def tack_website_onto_request(request, website):
    # XXX Why?
    request.website = website


def raise_200_for_OPTIONS(request):
    """A hook to return 200 to an 'OPTIONS *' request"""
    if request.line.method == "OPTIONS" and request.line.uri == "*":
        raise Response(200)


def dispatch_request_to_filesystem(request):
    dispatcher.dispatch(request)


def apply_typecasters_to_path(website, request):
    typecasting.apply_typecasters(website.typecasters, request.line.uri.path)


def get_resource_for_request(request):
    return {'resource': resources.get(request)}


def get_response_for_resource(request, resource=None):
    if resource is not None:
        return {'response': resource.respond(request)}


def get_response_for_exception(website, exception):
    tb = traceback.format_exc()
    if isinstance(exception, Response):
        response = exception
    else:
        response = Response(500)
        if website.show_tracebacks:
            response.body = tb
    return {'response': response, 'traceback': tb, 'exception': None}


def log_traceback_for_5xx(response, traceback=None):
    if response.code >= 500:
        if traceback:
            aspen.log_dammit(traceback)
        else:
            aspen.log_dammit(response.body)
    return {'traceback': None}


def delegate_error_to_simplate(website, request, response, resource=None):
    if response.code < 400:
        return

    code = str(response.code)
    possibles = [code + ".spt", "error.spt"]
    fs = _first(website.ours_or_theirs(errpage) for errpage in possibles)

    if fs is not None:
        request.fs = fs
        request.original_resource = resource
        if resource is not None:
            # Try to return an error that matches the type of the original resource.
            request.headers['Accept'] = resource.media_type + ', text/plain; q=0.1'
        resource = resources.get(request)
        try:
            response = resource.respond(request, response)
        except Response as response:
            if response.code != 406:
                raise

    return {'response': response, 'exception': None}


def log_traceback_for_exception(website, exception):
    tb = traceback.format_exc()
    aspen.log_dammit(tb)
    response = Response(500)
    if website.show_tracebacks:
        response.body = tb
    return {'response': response, 'exception': None}


def log_result_of_request(website, response, request):
    """Log access. With our own format (not Apache's).
    """

    if website.logging_threshold > 0: # short-circuit
        return


    # What was the URL path translated to?
    # ====================================

    fs = getattr(request, 'fs', '')
    if fs.startswith(website.www_root):
        fs = fs[len(website.www_root):]
        if fs:
            fs = '.'+fs
    else:
        fs = '...' + fs[-21:]
    msg = "%-24s %s" % (request.line.uri.path.raw, fs)


    # Where was response raised from?
    # ===============================

    filename, linenum = response.whence_raised()
    if filename is not None:
        response = "%s (%s:%d)" % (response, filename, linenum)
    else:
        response = str(response)

    # Log it.
    # =======

    aspen.log("%-36s %s" % (response, msg))

########NEW FILE########
__FILENAME__ = cookie
"""
aspen.auth.cookie
~~~~~~~~~~~~~~~~~

This is a cookie authentication implementation for Aspen.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import datetime

from aspen import auth
from aspen.utils import to_rfc822, utcnow
from aspen.website import THE_PAST


MINUTE = datetime.timedelta(seconds=60)
HOUR = 60 * MINUTE
DAY  = 24 * HOUR
WEEK = 7 * DAY


TIMEOUT = 2 * HOUR


# Public config knobs
# ===================
# Feel free to set these in, e.g., configure-aspen.py

NAME = "auth"
DOMAIN = None
PATH = "/"
HTTPONLY = "Yes, please."


# Hooks
# =====

def inbound_early(request):
    """Authenticate from a cookie.
    """
    if 'user' not in request.context:
        token = None
        if NAME in request.headers.cookie:
            token = request.headers.cookie[NAME].value
            token = token.decode('US-ASCII')
        request.context['user'] = auth.User(token)


def outbound(response):
    """Set outbound auth cookie.
    """
    if 'user' not in response.request.context:
        # XXX When does this happen? When auth.inbound_early hasn't run, eh?
        raise  # XXX raise what?

    user = response.request.context['user']
    if not isinstance(user, auth.User):
        raise Exception("If you define 'user' in a simplate it has to be an "
                        "instance of an aspen.auth.User.")

    if NAME not in response.request.headers.cookie:
        # no cookie in the request, don't set one on response
        return
    elif user.ANON:
        # user is anonymous, instruct browser to delete any auth cookie
        cookie_value = ''
        cookie_expires = THE_PAST
    else:
        # user is authenticated, keep it rolling for them
        cookie_value = user.token
        cookie_expires = to_rfc822(utcnow() + TIMEOUT)


    # Configure outgoing cookie.
    # ==========================

    response.headers.cookie[NAME] = cookie_value  # creates a cookie object?
    cookie = response.headers.cookie[NAME]          # loads a cookie object?

    cookie['expires'] = cookie_expires

    if DOMAIN is not None:
        # Browser default is the domain of the resource requested.
        # Aspen default is the browser default.
        cookie['domain'] = DOMAIN

    if PATH is not None:
        # XXX What's the browser default? Probably /? Or current dir?
        # Aspen default is "/".
        cookie['path'] = PATH

    if HTTPONLY is not None:
        # Browser default is to allow access from JavaScript.
        # Aspen default is to prevent access from JavaScript.
        cookie['httponly'] = HTTPONLY

########NEW FILE########
__FILENAME__ = httpbasic
"""
aspen.auth.httpbasic
~~~~~~~~~~~~~~~~~~~~

HTTP BASIC Auth module for Aspen.

To use:

    # import it
    from aspen.auth import httpbasic

    # configure it - see the docs on the BasicAuth object for args to inbound_responder()
    auth = httpbasic.inbound_responder(my_password_verifier)

    # install it
    website.algorithm.insert_after('parse_environ_into_request', auth)

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


import base64

from aspen import Response


def inbound_responder(*args, **kwargs):
    """ see BasicAuth object for args; they're passed through """
    auth = BasicAuth(*args, **kwargs)
    def httpbasic_inbound_responder(request):
        """generated request-handling method"""
        request.auth = BAWrapper(auth, request)
        authed, response = auth.authorized(request)
        if not authed:
            raise response
        return request
    return httpbasic_inbound_responder


class BAWrapper(object):
    """A convenience wrapper for BasicAuth handler to put on the request
    object so the user can do 'request.auth.username()'
    instead of 'request.auth.username(request)'
    """

    def __init__(self, basicauth, request):
        self.auth = basicauth
        self.request = request

    def authorized(self):
        return self.auth.authorized(self.request)

    def username(self):
        return self.auth.username(self.request)

    def logout(self):
        return self.auth.logout(self.request)


class BasicAuth(object):
    """An HTTP BASIC AUTH handler for Aspen."""

    def __init__(self, verify_password, html=None, realm='protected'):
        """Constructor for an HTTP BASIC AUTH handler.

        :verify_password - a function that, when passed the args
            (user, password), will return True iff the password is
            correct for the specified user
        :html - The HTML page to return along with a 401 'Not
            Authorized' response. Has a reasonable default
        :realm - the name of the auth realm
        """
        failhtml = html or b'''Not Authorized. <a href="#">Try again.</a>'''
        self.verify_password = verify_password
        fail_header = { 'WWW-Authenticate': 'Basic realm="%s"' % realm }
        self.fail_401 = Response(401, failhtml, fail_header)
        self.fail_400 = Response(400, failhtml, fail_header)
        self.logging_out = set([])

    def authorized(self, request):
        """Returns whether this request passes BASIC auth or not, and
           the Response to raise if not
        """
        header = request.headers.get('Authorization', '')
        if not header:
            #print("no auth header.")
            # no auth header at all
            return False, self.fail_401
        if not header.startswith('Basic'):
            #print("not a Basic auth header.")
            # not a basic auth header at all
            return False, self.fail_400
        try:
            userpass = base64.b64decode(header[len('Basic '):])
        except TypeError:
            # malformed user:pass
            return False, self.fail_400
        if not ':' in userpass:
            # malformed user:pass
            return False, self.fail_400
        user, passwd = userpass.split(':', 1)
        if user in self.logging_out:
            #print("logging out, so failing once.")
            self.logging_out.discard(user)
            return False, self.fail_401
        if not self.verify_password(user, passwd):
            #print("wrong password.")
            # wrong password
            # TODO: add a max attempts per timespan to slow down bot attacks
            return False, self.fail_401
        return True, None

    def username(self, request):
        """Returns the username in the current Auth header"""
        header = request.headers.get('Authorization', '')
        if not header.startswith('Basic'):
            return None
        userpass = base64.b64decode(header[len('Basic '):])
        if not ':' in userpass:
            return None
        user, _ = userpass.split(':', 1)
        return user

    def logout(self, request):
        """Will force the next auth request (ie. HTTP request) to fail,
            thereby prompting the user for their username/password again
        """
        self.logging_out.add(self.username(request))
        return request


########NEW FILE########
__FILENAME__ = httpdigest
"""
aspen.auth.httpdigest
~~~~~~~~~~~~~~~~~~~~~
"""
# Originally by Josh Goldoot
# version 0.01
#  Public domain.
# from http://www.autopond.com/digestauth.py
# modified by Paul Jimenez

import random, time, re

from aspen.backcompat import md5

class MalformedAuthenticationHeader(Exception): pass

## wrapper bits

class AspenHTTPProvider:
    """An abstraction layer between the Auth object and
    http-framework specific code."""

    def __init__(self, request):
        self.request = request

    def _response(self, *args):
        from aspen import Response
        r = Response(*args)
        r.request = self.request
        return r

    def set_request(self, request):
        self.request = request

    def auth_header(self, default):
        return self.request.headers.get('Authorization', default)

    def user_agent(self):
        return self.request.headers.get('User-Agent') or ''

    def request_method(self):
        return self.request.line.method

    def path_and_query(self):
        return self.request.line.uri.raw

    def send_400(self, html, extraheaders):
        return self._response(400, html, extraheaders)

    def send_401(self, html, extraheaders):
        return self._response(401, html, extraheaders)

    def send_403(self, html, extraheaders):
        return self._response(403, html, extraheaders)


## make a generator of containers that aspen will like

def inbound_responder(*args, **kw):
    """ This should be used in your configure-aspen.py like so:

    import aspen.auth.httpdigest as digestauth

    def get_digest(username, realm):
        users = { 'guest':'guest',
                }
        password = users[username]
        return digestauth.digest(':'.join([username, realm, password]))

    auth = digestauth.inbound_responder(get_digest)
    website.algorithm.insert_after('parse_environ_into_request', auth)
    """
    kwargs = kw.copy()
    kwargs['http_provider'] = AspenHTTPProvider
    auth = Auth(*args, **kwargs)
    def httpdigest_inbound_responder(request):
        """generated hook function"""
        request.auth = AspenAuthWrapper(auth, request)
        authed, response = auth.authorized(request)
        if not authed:
            #print "Response: %s" % repr(response.headers)
            raise response
        return request
    return httpdigest_inbound_responder


class AspenAuthWrapper(object):
    """Convenience class to put on a request that
       has a reference to the request its on so accessing
       auth methods doesn't require repeating the request arg.
    """

    def __init__(self, auth, request):
        self.auth = auth
        self.request = request

    def authorized(self):
        """delegates to self.auth object"""
        return self.auth.authorized(self.request)[0]

    def username(self):
        """delegates to self.auth object"""
        return self.auth.username(self.request)

    def logout(self):
        """delegates to self.auth object"""
        return self.auth.logout(self.request)


## Fundamental utilities

class Storage(dict):
    """
    (from web.py)
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


## Actual authentication obj

class Auth(object):
    """A decorator class implementing digest authentication (RFC 2617)"""
    def __init__(self,  get_digest,  realm="Protected",  tolerate_ie = True, redirect_url = '/newuser',  unauth_html = None,  nonce_skip = 0,  lockout_time = 20,  nonce_life = 180,  tries=3,  domain=[], http_provider=None):
        """Creates a decorator specific to a particular web application.
            get_digest: a function taking the arguments (username, realm), and returning digestauth.digest(username:realm:password), or
                            throwing KeyError if no such user
            realm: the authentication "realm"
            tolerate_ie: don't deny requests from Internet Explorer, even though it is standards uncompliant and kind of insecure
            redirect_url:  when user hits "cancel," they are redirected here
            unauth_html:  the HTML that is sent to the user and displayed if they hit cancel (default is a redirect page to redirect_url)
            nonce_skip: tolerate skips in the nonce count, only up to this amount (useful if CSS or JavaScript is being loaded unbeknownst to your code)
            lockout_time: number of seconds a user is locked out if they send a wrong password (tries) times
            nonce_life: number of seconds a nonce remains valid
            tries: number of tries a user gets to enter a correct password before the account is locked for lockout_time seconds
            http_provider: interface to HTTP protocol workings (see above code)
        """
        self.http_provider = http_provider
        if self.http_provider is None:
            raise Exception("no http_provider provided")
        self.get_digest,  self.realm,  self.tolerate_ie  = (get_digest,  realm,  tolerate_ie)
        self.lockout_time,  self.tries,  self.nonce_life,  self.domain = (lockout_time,  tries - 1,  nonce_life,  domain)
        self.unauth_html = unauth_html or self._default_401_html.replace("$redirecturl",  redirect_url)
        self.outstanding_nonces = NonceMemory()
        self.outstanding_nonces.set_nonce_skip(nonce_skip)
        self.user_status = {}
        self.opaque = "%032x" % random.getrandbits(128)

    _default_401_html = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta http-equiv="REFRESH" content="1; URL=$redirecturl" />
  <title></title>
</head>
<body>
</body>
</html>
"""

    def authorized(self, request):
        """ is this request authorized?
            returns a tuple where the first value is true if so and false if not, and the second value is the response to return
        """
        http = self.http_provider(request)
        request_header = http.auth_header(None)
        if not request_header:
            # client has failed to include an authentication header; send a 401 response
            return False, self._send_401_unauth_response(http, "No auth header")
        if request_header[0:7] != "Digest ":
            # client has attempted to use something other than Digest authenication; deny
            return False, self._deny_bad_request(http)
        req_header_dict = parse_auth_header(request_header)
        if not self._directive_proper(http.user_agent(), req_header_dict, http.path_and_query()):
            # Something is wrong with the authentication header
            if req_header_dict.get('opaque', self.opaque) != self.opaque:
                # Didn't send back the correct "opaque;" probably, our server restarted.  Just send
                # them another authentication header with the correct opaque field.
                return False, self._send_401_unauth_response(http, "Incorrect opaque field.")
            else:
                # Their header had a more fundamental problem.  Something is fishy.  Deny access.
                return False, self._deny_bad_request(http, "Authorization Request Header does not conform to RFC 2617 section 3.2.2")
        # if user sent a "logout" nonce, make them type in the password again
        if len(req_header_dict['nonce']) != 34:
            return False, self._send_401_unauth_response(http, "Logged out.")
        nonce_response = self.outstanding_nonces.nonce_state(req_header_dict)
        if nonce_response == NonceMemory.NONCE_INVALID:
            # Client sent a nonce we've never heard of before
            return False, self._deny_bad_request(http)
        if nonce_response == NonceMemory.NONCE_OLD:
            # Client sent an old nonce.  Give the client a new one, and ask to authenticate again before continuing.
            return False, self._send_401_unauth_response(http, "Stale nonce. Try again.", stale=True)
        username = req_header_dict['username']
        status = self.user_status.get(username, (self.tries, 0))
        if status[0] < 1 and time.time() < status[1]:
            # User got the password wrong within the last (self.lockout_time) seconds
            return False, self._deny_forbidden(http)
        if status[0] < 1:
            # User sent the wrong password, but more than (self.lockout_time) seconds have passed, so give
            # them another try.  However, send a 401 header so user's browser prompts for a password
            # again.
            self.user_status[username] = (1, 0)
            return False, self._send_401_unauth_response(http, "Wrong password, try again.")
        if self._request_digest_valid(req_header_dict, http.request_method()):
            # User authenticated; forgive any past incorrect passwords and run the function we're decorating
            self.user_status[username] = (self.tries, 0)
            return True, None
        else:
            # User entered the wrong password.  Deduct one try, and lock account if necessary
            self.user_status[username] = (status[0] - 1, time.time() + self.lockout_time)
            self._log_incorrect_password(username,  req_header_dict)
            return False, self._send_401_unauth_response(http, "Wrong password. One try burned.")

    def _log_incorrect_password(self,  username,  req_header_dict):
        """Hook to log incorrrect password attempts"""
        pass  # Do your own logging here

    def _directive_proper(self,  user_agent, req_header_dict, req_path):
        """Verifies that the client's authentication header contained the required fields"""
        for variable in ['username', 'realm', 'nonce', 'uri', 'response', 'cnonce', 'nc']:
            if variable not in req_header_dict:
                return False
        # IE doesn't send "opaque" and does not include GET parameters in the Digest field
        standards_uncompliant = self.tolerate_ie and ("MSIE" in user_agent)
        return req_header_dict['realm'] == self.realm \
            and (standards_uncompliant or req_header_dict.get('opaque','') == self.opaque) \
            and len(req_header_dict['nc']) == 8 \
            and (req_header_dict['uri'] == req_path or (standards_uncompliant and "?" in req_path and req_path.startswith(req_header_dict['uri'])))

    def _request_digest_valid(self, req_header_dict, req_method):
        """Checks to see if the client's request properly authenticates"""
        # Ask the application for the hash of A1 corresponding to this username and realm
        try:
            HA1 = self.get_digest(req_header_dict['username'], req_header_dict['realm'])
        except KeyError:
            # No such user
            return False
        qop = req_header_dict.get('qop','auth')
        A2 = req_method + ':' + req_header_dict['uri']
        # auth-int stuff would go here, but few browsers support it
        nonce = req_header_dict['nonce']
        # Calculate the response we should have received from the client
        correct_answer = digest(":".join([HA1, nonce, req_header_dict['nc'], req_header_dict['cnonce'], qop, digest(A2) ]))
        # Compare the correct response to what the client sent
        return req_header_dict['response'] == correct_answer

    def _send_401_unauth_response(self, http, why_msg, stale=False):
        """send a 401, optionally with a stale flag"""
        nonce = self.outstanding_nonces.get_new_nonce(self.nonce_life)
        challenge_list = [ "realm=" + quote_it(self.realm),
                           'qop="auth"',
                           'nonce=' + quote_it(nonce),
                           'opaque=' + quote_it(self.opaque)
                         ]
        if self.domain: challenge_list.append( 'domain=' + quote_it(" ".join(self.domain)) )
        if stale: challenge_list.append( 'stale="true"')
        extraheaders = [("WWW-Authenticate", "Digest " + ",".join(challenge_list)),
                        ("Content-Type","text/html"),
                        ("X-Why-Auth-Failed", why_msg)]
        return http.send_401(self.unauth_html, extraheaders)

    def _deny_bad_request(self, http, info=""):
        return http.send_400(info, [('Content-Type', 'text/html')])

    def _deny_forbidden(self, http):
        """Sent when user has entered an incorrect password too many times"""
        return http.send_403(self.unauth_html, [('Content-Type', 'text/html')])

    def _get_valid_auth_header(self, http):
        """returns valid dictionary of authorization header, or None"""
        request_header = http.auth_header(None)
        if not request_header:
            raise MalformedAuthenticationHeader()
        if request_header[0:7] != "Digest ":
            raise MalformedAuthenticationHeader()
        req_header_dict = parse_auth_header(request_header)
        if not self._directive_proper(http.user_agent(), req_header_dict, http.path_and_query()):
            raise MalformedAuthenticationHeader()
        return req_header_dict

    def logout(self, request):
        """Cause user's browser to stop sending correct authentication requests until user re-enters password"""
        http = self.http_provider(request)
        try:
            req_header_dict = self._get_valid_auth_header(http)
        except MalformedAuthenticationHeader:
            return
        if len(req_header_dict['nonce']) == 34:
            # First time: send a 401 giving the user the fake "logout" nonce
            nonce = "%032x" % random.getrandbits(136)
            challenge_list = [ "realm=" + quote_it(self.realm),
                               'qop="auth"',
                               'nonce=' + quote_it(nonce),
                               'opaque=' + quote_it(self.opaque),
                               'stale="true"']
            extraheaders = [("WWW-Authenticate", "Digest " + ",".join(challenge_list))]
            return http.send_401(None, extraheaders)

    def username(self, request):
        """Returns the HTTP username, or None if not logged in."""
        http = self.http_provider(request)
        try:
            req_header_dict = self._get_valid_auth_header(http)
        except MalformedAuthenticationHeader:
            return None
        if len(req_header_dict['nonce']) != 34:
            return None
        nonce_response = self.outstanding_nonces.nonce_state(req_header_dict)
        if nonce_response != NonceMemory.NONCE_VALID:
            # Client sent a nonce we've never heard of before
            # Client sent an old nonce.  Give the client a new one, and ask to authenticate again before continuing.
            return None
        return req_header_dict.username



def digest(data):
    """Return a hex digest MD5 hash of the argument"""
    return md5(data).hexdigest()

def quote_it(s):
    """Return the argument quoted, suitable for a quoted-string"""
    return '"%s"' % (s.replace("\\","\\\\").replace('"','\\"'))

## Code to parse the authentication header
parse_auth_header_re = re.compile(r"""
    (   (?P<varq>[a-z]+)="(?P<valueq>.+?)"(,|$)    )   # match variable="value", (terminated by a comma or end of line)
    |
    (   (?P<var>[a-z]+)=(?P<value>.+?)(,|$)    )          # match variable=value,  (same as above, but no quotes)
    """,  re.VERBOSE | re.IGNORECASE )
def parse_auth_header(header):
    """parse an authentication header into a dict"""
    result = Storage()
    for m in parse_auth_header_re.finditer(header):
        g = m.groupdict()
        if g['varq'] and g['valueq']:
            result[g['varq']] = g['valueq'].replace(r'\"',  '"')
        elif g['var'] and g['value']:
            result[g['var']] = g['value']
    return result

class NonceMemory(dict):
    """
    A dict of in-use nonces, with a couple methods to create new nonces and get the state of a nonce
    """

    NONCE_VALID = 1
    NONCE_INVALID = 2
    NONCE_OLD = 3

    def set_nonce_skip(self, nonce_skip):
        self.nonce_skip = nonce_skip

    def get_new_nonce(self,  lifespan = 180):
        """Generate a new, unused nonce, with a nonce-count set to 1.
            :lifespan - how long (in seconds) the nonce is good for before it's considered 'old'
        """
        is_new = False
        while not is_new:
            nonce = "%034x" % random.getrandbits(136)  # a random 136-bit zero-padded lowercase hex string
            is_new = not nonce in self
        self[nonce] = (time.time() + lifespan, 1)
        return nonce

    def nonce_state(self, req_header_dict):
        """ 1 = nonce valid, proceed; 2 = nonce totally invalid;  3 = nonce requires refreshing """
        nonce = req_header_dict.get('nonce', None)
        exp_time, nCount = self.get(nonce, (0, 0) )
        if exp_time == 0:
            # Client sent some totally unknown nonce -- reject
            return self.NONCE_INVALID
        try:
            incoming_nc = int((req_header_dict['nc']), 16)
        except ValueError:
            return self.NONCE_INVALID # the "nc" field was deformed (not hexadecimal); reject
        # default nonce_skip value
        nonce_skip = getattr(self, 'nonce_skip', 1)
        if exp_time == 1 or nCount > 1000 or exp_time < time.time() or incoming_nc - nCount > nonce_skip:
            # Client sent good nonce, but it is too old, or the count has gotten screwed up; give them a new one
            del self[nonce]
            return self.NONCE_OLD
        self[nonce] = (exp_time, incoming_nc + 1)
        return self.NONCE_VALID


########NEW FILE########
__FILENAME__ = backcompat
"""
aspen.backcompat
++++++++++++++++
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from operator import itemgetter as _itemgetter
from keyword import iskeyword as _iskeyword
import sys as _sys

try:
    from hashlib import md5
except ImportError:
    from md5 import new as md5

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

try:                # Python >= 2.6
    from collections import Callable
    def is_callable(obj):
        return isinstance(obj, Callable)
except ImportError: # Python < 2.6
    from operator import isCallable as is_callable

try:                # 2
    from Cookie import CookieError, SimpleCookie
except ImportError: # 3
    from http.cookies import CookieError, SimpleCookie

try:                # 3
    from html import escape as html_escape
except ImportError: # 2
    from cgi import escape as cgi_escape
    def html_escape(*args,**kwargs):
        # make the defaults match the py3 defaults
        kwargs['quote'] = kwargs.get('quote', True)
        return cgi_escape(*args,**kwargs)


def _namedtuple(typename, field_names, verbose=False, rename=False):
    """Returns a new subclass of tuple with named fields.

    >>> Point = namedtuple('Point', 'x y')
    >>> Point.__doc__                   # docstring for the new class
    'Point(x, y)'
    >>> p = Point(11, y=22)             # instantiate with positional args or keywords
    >>> p[0] + p[1]                     # indexable like a plain tuple
    33
    >>> x, y = p                        # unpack like a regular tuple
    >>> x, y
    (11, 22)
    >>> p.x + p.y                       # fields also accessable by name
    33
    >>> d = p._asdict()                 # convert to a dictionary
    >>> d['x']
    11
    >>> Point(**d)                      # convert from a dictionary
    Point(x=11, y=22)
    >>> p._replace(x=100)               # _replace() is like str.replace() but targets named fields
    Point(x=100, y=22)

    """

    # Parse and validate the field names.  Validation serves two purposes,
    # generating informative error messages and preventing template injection attacks.
    if isinstance(field_names, basestring):
        field_names = field_names.replace(',', ' ').split() # names separated by whitespace and/or commas
    field_names = tuple(map(str, field_names))
    if rename:
        names = list(field_names)
        seen = set()
        for i, name in enumerate(names):
            if (not min(c.isalnum() or c=='_' for c in name) or _iskeyword(name)
                or not name or name[0].isdigit() or name.startswith('_')
                or name in seen):
                    names[i] = '_%d' % i
            seen.add(name)
        field_names = tuple(names)
    for name in (typename,) + field_names:
        if not min(c.isalnum() or c=='_' for c in name):
            raise ValueError('Type names and field names can only contain alphanumeric characters and underscores: %r' % name)
        if _iskeyword(name):
            raise ValueError('Type names and field names cannot be a keyword: %r' % name)
        if name[0].isdigit():
            raise ValueError('Type names and field names cannot start with a number: %r' % name)
    seen_names = set()
    for name in field_names:
        if name.startswith('_') and not rename:
            raise ValueError('Field names cannot start with an underscore: %r' % name)
        if name in seen_names:
            raise ValueError('Encountered duplicate field name: %r' % name)
        seen_names.add(name)

    # Create and fill-in the class template
    numfields = len(field_names)
    argtxt = repr(field_names).replace("'", "")[1:-1]   # tuple repr without parens or quotes
    reprtxt = ', '.join('%s=%%r' % name for name in field_names)
    template = '''class %(typename)s(tuple):
        '%(typename)s(%(argtxt)s)' \n
        __slots__ = () \n
        _fields = %(field_names)r \n
        def __new__(_cls, %(argtxt)s):
            return _tuple.__new__(_cls, (%(argtxt)s)) \n
        @classmethod
        def _make(cls, iterable, new=tuple.__new__, len=len):
            'Make a new %(typename)s object from a sequence or iterable'
            result = new(cls, iterable)
            if len(result) != %(numfields)d:
                raise TypeError('Expected %(numfields)d arguments, got %%d' %% len(result))
            return result \n
        def __repr__(self):
            return '%(typename)s(%(reprtxt)s)' %% self \n
        def _asdict(self):
            'Return a new dict which maps field names to their values'
            return dict(zip(self._fields, self)) \n
        def _replace(_self, **kwds):
            'Return a new %(typename)s object replacing specified fields with new values'
            result = _self._make(map(kwds.pop, %(field_names)r, _self))
            if kwds:
                raise ValueError('Got unexpected field names: %%r' %% kwds.keys())
            return result \n
        def __getnewargs__(self):
            return tuple(self) \n\n''' % locals()
    for i, name in enumerate(field_names):
        template += '        %s = _property(_itemgetter(%d))\n' % (name, i)
    if verbose:
        print(template)

    # Execute the template string in a temporary namespace
    namespace = dict(_itemgetter=_itemgetter, __name__='namedtuple_%s' % typename,
                     _property=property, _tuple=tuple)
    try:
        exec template in namespace
    except SyntaxError, e:
        raise SyntaxError(e.message + ':\n' + template)
    result = namespace[typename]

    # For pickling to work, the __module__ variable needs to be set to the frame
    # where the named tuple is created.  Bypass this step in enviroments where
    # sys._getframe is not defined (Jython for example) or sys._getframe is not
    # defined for arguments greater than 0 (IronPython).
    try:
        result.__module__ = _sys._getframe(1).f_globals.get('__name__', '__main__')
    except (AttributeError, ValueError):
        pass

    return result

def namedtuple_test():
    # verify that instances can be pickled
    from cPickle import loads, dumps
    Point = namedtuple('Point', 'x, y', True)
    p = Point(x=10, y=20)
    assert p == loads(dumps(p, -1))

    # test and demonstrate ability to override methods
    class Point(namedtuple('Point', 'x y')):
        @property
        def hypot(self):
            return (self.x ** 2 + self.y ** 2) ** 0.5
        def __str__(self):
            return 'Point: x=%6.3f y=%6.3f hypot=%6.3f' % (self.x, self.y, self.hypot)

    for p in Point(3,4), Point(14,5), Point(9./7,6):
        print(p)

    class Point(namedtuple('Point', 'x y')):
        'Point class with optimized _make() and _replace() without error-checking'
        _make = classmethod(tuple.__new__)
        def _replace(self, _map=map, **kwds):
            return self._make(_map(kwds.get, ('x', 'y'), self))

    print(Point(11, 22)._replace(x=100))

    import doctest
    TestResults = namedtuple('TestResults', 'failed attempted')
    print(TestResults(*doctest.testmod()))

try:                    # python2.6+
    from collections import namedtuple
except ImportError:     # < python2.6
    namedtuple = _namedtuple



########NEW FILE########
__FILENAME__ = exceptions
"""
aspen.configuration.exceptions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Exceptions used by Aspen's configuration module
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


class ConfigurationError(StandardError):
    """This is an error in any part of our configuration.
    """

    def __init__(self, msg):
        StandardError.__init__(self)
        self.msg = msg

    def __str__(self):
        return self.msg

########NEW FILE########
__FILENAME__ = options
"""
aspen.configuration.options
~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import optparse

import aspen


# OptionParser
# ------------

usage = "aspen [options]"


version = """\
aspen, version %s

(c) 2006-2013 Chad Whitacre and contributors
http://aspen.io/
""" % aspen.__version__


description = """\
Aspen is a Python web framework. By default this program will start serving a
website from the current directory on port 8080. Options are as follows. See
also http://aspen.io/.
"""


class DEFAULT(object):
    def __repr__(self):
        return "<DEFAULT>"
DEFAULT = DEFAULT()


def OptionParser():
    optparser = optparse.OptionParser( usage=usage
                                     , version=version
                                     , description=description
                                      )

    basic = optparse.OptionGroup(optparser, "Basic Options")

    basic.add_option( "-f", "--configuration_scripts"
                    , help=("comma-separated list of paths to configuration "
                            "files in Python syntax to exec in addition to "
                            "$ASPEN_PROJECT_ROOT/configure-aspen.py")
                    , default=DEFAULT
                     )
    basic.add_option( "-l", "--logging_threshold"
                    , help=("a small integer; 1 will suppress most of aspen's "
                            "internal logging, 2 will suppress all it [0]")
                    , default=DEFAULT
                     )
    basic.add_option( "-p", "--project_root"
                    , help=("the filesystem path of the directory in "
                            "which to look for project files like "
                            "template bases and such. []")
                    , default=DEFAULT
                     )
    basic.add_option( "-w", "--www_root"
                    , help=("the filesystem path of the document "
                            "publishing root [.]")
                    , default=DEFAULT
                     )


    extended = optparse.OptionGroup( optparser, "Extended Options"
                                   , "I judge these variables to be less-"
                                     "often configured from the command "
                                     "line. But who knows?"
                                    )
    extended.add_option( "--changes_reload"
                       , help=("if set to yes/true/1, changes to configuration"
                               " files and Python modules will cause aspen to "
                               "re-exec, and template bases won't be cached "
                               "[no]")

                       , default=DEFAULT
                        )
    extended.add_option( "--charset_dynamic"
                       , help=("this is set as the charset for rendered and "
                               "negotiated resources of Content-Type text/* "
                               "[UTF-8]")
                       , default=DEFAULT
                        )
    extended.add_option( "--charset_static"
                       , help=("if set, this will be sent as the charset for "
                               "static resources of Content-Type text/*; if "
                               "you want to punt and let browsers guess, then "
                               "just leave this unset []")
                       , default=DEFAULT
                        )
    extended.add_option( "--indices"
                       , help=("a comma-separated list of filenames to look "
                               "for when a directory is requested directly; "
                               "prefix with + to extend previous "
                               "configuration instead of overriding "
                               "[index.html, index.json]")
                       , default=DEFAULT
                        )
    extended.add_option( "--list_directories"
                       , help=("if set to {yes,true,1}, aspen will serve a "
                               "directory listing when no index is available "
                               "[no]")
                       , default=DEFAULT
                        )
    extended.add_option( "--media_type_default"
                       , help=("this is set as the Content-Type for resources "
                               "of otherwise unknown media type [text/plain]")
                       , default=DEFAULT
                        )
    extended.add_option( "--media_type_json"
                       , help=("this is set as the Content-Type of JSON "
                               "resources [application/json]")
                       , default=DEFAULT
                        )
    extended.add_option( "--renderer_default"
                    , help=( "the renderer to use by default; one of "
                           + "{%s}" % ','.join(aspen.RENDERERS)
                           + " [stdlib_percent]"
                            )
                    , default=DEFAULT
                     )
    extended.add_option( "--show_tracebacks"
                       , help=("if set to {yes,true,1}, 500s will have a "
                               "traceback in the browser [no]")
                       , default=DEFAULT
                        )


    optparser.add_option_group(basic)
    optparser.add_option_group(extended)
    return optparser

########NEW FILE########
__FILENAME__ = parse
"""
aspen.configuration.parse
~~~~~~~~~~~~~~~~~~~~~~~~~

Define parser/validators for configuration system

Each of these is guaranteed to be passed a unicode object as read from the
environment or the command line.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import aspen
from aspen.utils import typecheck
from aspen.http.response import charset_re


def identity(value):
    typecheck(value, unicode)
    return value

def media_type(media_type):
    # XXX for now. Read a spec
    return media_type.encode('US-ASCII')

def charset(value):
    typecheck(value, unicode)
    if charset_re.match(value) is None:
        raise ValueError("charset not to spec")
    return value

def yes_no(s):
    typecheck(s, unicode)
    s = s.lower()
    if s in [u'yes', u'true', u'1']:
        return True
    if s in [u'no', u'false', u'0']:
        return False
    raise ValueError("must be either yes/true/1 or no/false/0")

def list_(value):
    """Return a tuple of (bool, list).

    The bool indicates whether to extend the existing config with the list, or
    replace it.

    """
    typecheck(value, unicode)
    extend = value.startswith('+')
    if extend:
        value = value[1:]

    # populate out with a single copy
    # of each non-empty item, preserving order
    out = []
    for v in value.split(','):
        v = v.strip()
        if v and not v in out:
            out.append(v)

    return (extend, out)

def renderer(value):
    typecheck(value, unicode)
    if value not in aspen.RENDERERS:
        msg = "not one of {%s}" % (','.join(aspen.RENDERERS))
        raise ValueError(msg)
    return value.encode('US-ASCII')

########NEW FILE########
__FILENAME__ = context
"""
aspen.context
+++++++++++++
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


class Context(dict):
    """Model the execution context for a Resource.
    """

    def __init__(self, request):
        """Takes a Request object.
        """
        self.website    = None # set in dynamic_resource.py
        self.body       = request.body
        self.headers    = request.headers
        self.cookie     = request.headers.cookie
        self.path       = request.line.uri.path
        self.qs         = request.line.uri.querystring
        self.request    = request
        self.channel    = None
        self.context    = self

        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html
        for method in ['OPTIONS', 'GET', 'HEAD', 'POST', 'PUT', 'DELETE',
                       'TRACE', 'CONNECT']:
            self[method] = (method == request.line.method)
            setattr(self, method, self[method])

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError("")

    def __setattr__(self, name, value):
        self[name] = value

########NEW FILE########
__FILENAME__ = dispatcher
"""
aspen.dispatcher
++++++++++++++++

Implement Aspen's filesystem dispatch algorithm.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import mimetypes
import os

from aspen import Response
from aspen.utils import typecheck
from .backcompat import namedtuple
from aspen.http.request import PathPart

def debug_noop(*args, **kwargs):
    pass

def debug_stdout(func):
    r = func()
    try:
        print("DEBUG: " + r)
    except Exception:
        print("DEBUG: " + repr(r))

debug = debug_stdout if 'ASPEN_DEBUG' in os.environ else debug_noop


def splitext(name):
    parts = name.rsplit('.',1) + [None]
    return parts[:2]


def strip_matching_ext(a, b):
    """Given two names, strip a trailing extension iff they both have them.
    """
    aparts = splitext(a)
    bparts = splitext(b)
    debug_ext = lambda: ( "exts: " + repr(a) + "( " + repr(aparts[1]) + " ) and "
                        + repr(b) + "( " + repr(bparts[1]) + " )"
                         )
    if aparts[1] == bparts[1]:
        debug(lambda: debug_ext() + " matches")
        return aparts[0], bparts[0]
    debug(lambda: debug_ext() + " don't match")
    return a, b


class DispatchStatus:
    okay, missing, non_leaf = range(3)


DispatchResult = namedtuple( 'DispatchResult'
                           , 'status match wildcards detail'.split()
                            )


def dispatch_abstract(listnodes, is_leaf, traverse, find_index, noext_matched,
        startnode, nodepath):
    """Given a list of nodenames (in 'nodepath'), return a DispatchResult.

    We try to traverse the directed graph rooted at 'startnode' using the
    functions:

       listnodes(joinedpath) - lists the nodes in the specified joined path

       is_leaf(node) - returns true iff the specified node is a leaf node

       traverse(joinedpath, newnode) - returns a new joined path by traversing
        into newnode from the current joinedpath

       find_index(joinedpath) - returns the index file in the specified path if
        it exists, or None if not

       noext_matched(node) - is called iff node is matched with no extension
        instead of fully

    Wildcards nodenames start with %. Non-leaf wildcards are used as keys in
    wildvals and their actual path names are used as their values. In general,
    the rule for matching is 'most specific wins': $foo looks for isfile($foo)
    then isfile($foo-minus-extension) then isfile(virtual-with-extension) then
    isfile(virtual-no-extension) then isdir(virtual)

    """
    # TODO: noext_matched wildleafs are borken
    wildvals, wildleafs = {}, {}
    curnode = startnode
    is_wild = lambda n: n.startswith('%')
    lastnode_ext = splitext(nodepath[-1])[1]

    for depth, node in enumerate(nodepath):

        if not node and depth + 1 == len(nodepath): # empty path segment in
            subnode = traverse(curnode, node)       #  last position, so look
            idx = find_index(subnode)               #  for index or 404
            if idx is None:
                # this makes the resulting path end in /, meaning autoindex or
                # 404 as appropriate
                idx = ""
            curnode = traverse(subnode, idx)
            break

        if is_leaf(curnode):
            # trying to treat a leaf node as a dir
            errmsg = "Node " + repr(curnode) + " is a leaf node and has no children"
            return DispatchResult(DispatchStatus.missing, None, None, errmsg)

        subnodes = listnodes(curnode)
        subnodes.sort()
        node_noext, node_ext = splitext(node)


        # Look for matches, and gather future options.
        # ============================================

        found_direct, found_indirect = None, None
        wildsubs = []
        for n in subnodes:
            if n.startswith('.'):               # don't serve hidden files
                continue
            n_is_spt = n.endswith('.spt')
            n_nospt, _ = splitext(n)
            if (not n_is_spt and node == n) or (n_is_spt and node == n_nospt): # exact name or name.spt
                found_direct = n
                break
            n_is_leaf = is_leaf(traverse(curnode, n))
            if n_is_leaf: # only files
                          # negotiated/indirect filename
                if node_noext == n or (n_is_spt and node_noext == n_nospt):
                    found_indirect = n
                    continue
            if not is_wild(n):
                continue
            if not n_is_leaf:
                debug(lambda: "not is_leaf " + n)
                wildsubs.append(n)
                continue
            if not n_is_spt:
                debug(lambda: "not is_spt " + n)
                # only spts can be wild
                continue

            # if we get here, it's a wild leaf (file)

            # wild leafs are fallbacks if anything goes missing
            # though they still have to match extension

            # Compute and store the wildcard value.
            # =====================================

            wildwildvals = wildvals.copy()
            remaining = reduce(traverse, nodepath[depth:])
            k, v = strip_matching_ext(n_nospt[1:], remaining)
            wildwildvals[k] = v
            n_ext = splitext(n_nospt)[1]
            wildleafs[n_ext] = (traverse(curnode, n), wildwildvals)

        if found_direct:                        # exact match
            debug(lambda: "Exact match " + repr(node))
            curnode = traverse(curnode, found_direct)
            continue

        if found_indirect:                      # matched but no extension
            debug(lambda: "Indirect match " + repr(node))
            noext_matched(node)
            curnode = traverse(curnode, found_indirect)
            continue


        # Now look for wildcard matches.
        # ==============================

        wildleaf_fallback = lastnode_ext in wildleafs or None in wildleafs
        last_pathseg = depth == len(nodepath) - 1

        if wildleaf_fallback and (last_pathseg or not wildsubs):
            ext = lastnode_ext if lastnode_ext in wildleafs else None
            curnode, wildvals = wildleafs[ext]
            debug( lambda: "Wildcard leaf match " + repr(curnode)
                 + " because last_pathseg:" + repr(last_pathseg)
                 + " and ext " + repr(ext)
                  )
            break

        if wildsubs:                            # wildcard subnode matches
            n = wildsubs[0]
            wildvals[n[1:]] = node
            curnode = traverse(curnode, n)
            debug(lambda: "Wildcard subnode match " + repr(n))
            continue

        return DispatchResult( DispatchStatus.missing
                             , None
                             , None
                             , "Node " + repr(node) +" Not Found"
                              )
    else:
        debug(lambda: "else clause tripped; testing is_leaf " + str(curnode))
        if not is_leaf(curnode):
            return DispatchResult( DispatchStatus.non_leaf
                                 , curnode
                                 , None
                                 , "Tried to access non-leaf node as leaf."
                                  )

    return DispatchResult( DispatchStatus.okay
                         , curnode
                         , wildvals
                         , "Found."
                          )

def match_index(indices, indir):
    for filename in indices:
        index = os.path.join(indir, filename)
        if os.path.isfile(index):
            return index
    return None

def is_first_index(indices, basedir, name):
    """is the supplied name the first existing index in the basedir ?"""
    for i in indices:
        if i == name: return True
        if os.path.isfile(os.path.join(basedir, i)):
            return False
    return False

def update_neg_type(request, filename):
    media_type = mimetypes.guess_type(filename, strict=False)[0]
    if media_type is None:
        media_type = request.website.media_type_default
    request.headers['X-Aspen-Accept'] = media_type


def dispatch(request, pure_dispatch=False):
    """Concretize dispatch_abstract.

    This is all side-effecty on the request object, setting, at the least,
    request.fs, and at worst other random contents including but not limited
    to: request.line.uri.path, request.headers.

    """

    # Handle URI path parts
    pathparts = request.line.uri.path.parts

    # Set up the real environment for the dispatcher.
    # ===============================================

    listnodes = os.listdir
    is_leaf = os.path.isfile
    traverse = os.path.join
    find_index = lambda x: match_index(request.website.indices, x)
    noext_matched = lambda x: update_neg_type(request, x)
    startdir = request.website.www_root

    # Dispatch!
    # =========

    result = dispatch_abstract( listnodes
                              , is_leaf
                              , traverse
                              , find_index
                              , noext_matched
                              , startdir
                              , pathparts
                               )

    debug(lambda: "dispatch_abstract returned: " + repr(result))

    if result.match:
        matchbase, matchname = result.match.rsplit(os.path.sep,1)
        if pathparts[-1] != '' and matchname in request.website.indices and \
                is_first_index(request.website.indices, matchbase, matchname):
            # asked for something that maps to a default index file; redirect to / per issue #175
            debug(lambda: "found default index '%s' maps into %r" % (pathparts[-1], request.website.indices))
            uri = request.line.uri
            location = uri.path.raw[:-len(pathparts[-1])]
            if uri.querystring.raw:
                location += '?' + uri.querystring.raw
            raise Response(302, headers={'Location': location})

    if not pure_dispatch:

        # favicon.ico
        # ===========
        # Serve Aspen's favicon if there's not one.

        if request.line.uri.path.raw == '/favicon.ico':
            if result.status != DispatchStatus.okay:
                path = request.line.uri.path.raw[1:]
                request.fs = request.website.find_ours(path)
                return


        # robots.txt
        # ==========
        # Don't let robots.txt be handled by anything other than an actual
        # robots.txt file

        if request.line.uri.path.raw == '/robots.txt':
            if result.status != DispatchStatus.missing:
                if not result.match.endswith('robots.txt'):
                    raise Response(404)


    # Handle returned states.
    # =======================

    if result.status == DispatchStatus.okay:
        if result.match.endswith('/'):              # autoindex
            if not request.website.list_directories:
                raise Response(404)
            autoindex = request.website.ours_or_theirs('autoindex.html.spt')
            assert autoindex is not None # sanity check
            request.headers['X-Aspen-AutoIndexDir'] = result.match
            request.fs = autoindex
            return  # return so we skip the no-escape check
        else:                                       # normal match
            request.fs = result.match
            for k, v in result.wildcards.iteritems():
                request.line.uri.path[k] = v

    elif result.status == DispatchStatus.non_leaf:  # trailing-slash redirect
        uri = request.line.uri
        location = uri.path.raw + '/'
        if uri.querystring.raw:
            location += '?' + uri.querystring.raw
        raise Response(302, headers={'Location': location})

    elif result.status == DispatchStatus.missing:   # 404
        raise Response(404)

    else:
        raise Response(500, "Unknown result status.")


    # Protect against escaping the www_root.
    # ======================================

    if not request.fs.startswith(startdir):
        raise Response(404)


########NEW FILE########
__FILENAME__ = exceptions
"""
aspen.exceptions
++++++++++++++++

Exceptions used by Aspen
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from aspen import Response


class LoadError(Exception):
    """Represent a problem loading a resource.
    """
    # Define this here to avoid import issues when json doesn't exist.


class CRLFInjection(Response):
    """
    A 400 Response (per #249) raised if there's a suspected CRLF Injection attack in the headers
    """
    def __init__(self):
        Response.__init__(self, code=400, body="Possible CRLF Injection detected.")

########NEW FILE########
__FILENAME__ = baseheaders
"""
aspen.http.baseheaders
~~~~~~~~~~~~~~~~~~~~~~
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


from aspen.backcompat import CookieError, SimpleCookie

from aspen.http.mapping import CaseInsensitiveMapping
from aspen.utils import typecheck


class BaseHeaders(CaseInsensitiveMapping):
    """Represent the headers in an HTTP Request or Response message.
       http://stackoverflow.com/questions/5423223/how-to-send-non-english-unicode-string-using-http-header
       has good notes on why we do everything as pure bytes here
    """

    def __init__(self, d):
        """Takes headers as a dict or str.
        """
        typecheck(d, (dict, str))
        if isinstance(d, str):
            def genheaders():
                for line in d.splitlines():
                    k, v = line.split(b':', 1)
                    yield k.strip(), v.strip()
        else:
            genheaders = d.iteritems
        CaseInsensitiveMapping.__init__(self, genheaders)


        # Cookie
        # ======

        self.cookie = SimpleCookie()
        try:
            self.cookie.load(self.get('Cookie', b''))
        except CookieError:
            pass # XXX really?


    def __setitem__(self, name, value):
        """Extend to protect against CRLF injection:

        http://www.acunetix.com/websitesecurity/crlf-injection/

        """
        if '\n' in value:
            from aspen.exceptions import CRLFInjection
            raise CRLFInjection()
        super(BaseHeaders, self).__setitem__(name, value)


    def raw(self):
        """Return the headers as a string, formatted for an HTTP message.
        """
        out = []
        for header, values in self.iteritems():
            for value in values:
                out.append('%s: %s' % (header, value))
        return '\r\n'.join(out)
    raw = property(raw)

########NEW FILE########
__FILENAME__ = mapping
"""
aspen.http.mapping
~~~~~~~~~~~~~~~~~~
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals



NO_DEFAULT = object()


class Mapping(dict):
    """Base class for HTTP mappings: Path, Querystring, Headers, Cookie, Body.

    Mappings in HTTP differ from Python dictionaries in that they may have one
    or more values. This dictionary subclass maintains a list of values for
    each key. However, access semantics are asymetric: subscript assignment
    clobbers to the list, while subscript access returns the last item. Think
    about it.

    """

    def __getitem__(self, name):
        """Given a name, return the last value or raise Response(400).
        """
        try:
            return dict.__getitem__(self, name)[-1]
        except KeyError:
            from aspen import Response
            raise Response(400, "Missing key: %s" % repr(name))

    def __setitem__(self, name, value):
        """Given a name and value, clobber any existing values.
        """
        dict.__setitem__(self, name, [value])

    def pop(self, name, default=NO_DEFAULT):
        """Given a name, return a value.

        This removes the last value from the list for name and returns it. If
        there was only one value in the list then the key is removed from the
        mapping. If name is not present and default is given, that is returned
        instead.

        """
        if name not in self:
            if default is not NO_DEFAULT:
                return default
            else:
                dict.pop(self, name) # KeyError
        values = dict.__getitem__(self, name)
        value = values.pop()
        if not values:
            del self[name]
        return value

    popall = dict.pop

    def all(self, name):
        """Given a name, return a list of values.
        """
        try:
            return dict.__getitem__(self, name)
        except KeyError:
            from aspen import Response
            raise Response(400)

    def get(self, name, default=None):
        """Override to only return the last value.
        """
        return dict.get(self, name, [default])[-1]

    def add(self, name, value):
        """Given a name and value, clobber any existing values with the new one.
        """
        if name in self:
            self.all(name).append(value)
        else:
            dict.__setitem__(self, name, [value])

    def ones(self, *names):
        """Given one or more names of keys, return a list of their values.
        """
        lowered = []
        for name in names:
            n = name.lower()
            if n not in lowered:
                lowered.append(n)
        return [self[name] for name in lowered]


class CaseInsensitiveMapping(Mapping):

    def __init__(self, *a, **kw):
        if a:
            d = a[0]
            items = d.iteritems if hasattr(d, 'iteritems') else d
            for k, v in items():
                self[k] = v
        for k, v in kw.iteritems():
            self[k] = v

    def __contains__(self, name):
        return Mapping.__contains__(self, name.title())

    def __getitem__(self, name):
        return Mapping.__getitem__(self, name.title())

    def __setitem__(self, name, value):
        return Mapping.__setitem__(self, name.title(), value)

    def add(self, name, value):
        return Mapping.add(self, name.title(), value)

    def get(self, name, default=None):
        return Mapping.get(self, name.title(), default)

    def all(self, name):
        return Mapping.all(self, name.title())

    def pop(self, name):
        return Mapping.pop(self, name.title())

    def popall(self, name):
        return Mapping.popall(self, name.title())

########NEW FILE########
__FILENAME__ = request
"""
aspen.http.request
~~~~~~~~~~~~~~~~~~

Define a Request class and child classes.

Here is how we analyze the structure of an HTTP message, along with the objects
we use to model each:

    - request                   Request
        - line                  Line
            - method            Method      ASCII
            - uri               URI
                - path          Path
                  - parts       list of PathPart
                - querystring   Querystring
            - version           Version     ASCII
        - headers               Headers     str
            - cookie            Cookie      str
            - host              unicode     str
            - scheme            unicode     str
        - body                  Body        Content-Type?


XXX TODO
    make URI conform to spec (path, querystring)
    test franken*
    validate Mapping
    clean up headers
    clean up body

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


import cgi
import mimetypes
import re
import sys
import urllib
import urlparse
from cStringIO import StringIO

from aspen import Response
from aspen.http.baseheaders import BaseHeaders
from aspen.http.mapping import Mapping
from aspen.context import Context
from aspen.utils import ascii_dammit, typecheck


# WSGI Do Our Best
# ================
# Aspen is jealous. It wants to pretend that it parsed the HTTP Request itself,
# instead of letting some WSGI server or library do the work for it. Here are
# routines for going from WSGI back to HTTP. Since WSGI is lossy, we end up
# with a Dr. Frankenstein's HTTP message.

quoted_slash_re = re.compile("%2F", re.IGNORECASE)


def make_franken_uri(path, qs):
    """Given two bytestrings, return a bytestring.

    We want to pass ASCII to Request. However, our friendly neighborhood WSGI
    servers do friendly neighborhood things with the Request-URI to compute
    PATH_INFO and QUERY_STRING. In addition, our friendly neighborhood browser
    sends "raw, unescaped UTF-8 bytes in the query during an HTTP request"
    (http://web.lookout.net/2012/03/unicode-normalization-in-urls.html).

    Our strategy is to try decoding to ASCII, and if that fails (we don't have
    ASCII) then we'll quote the value before passing to Request. What encoding
    are those bytes? Good question. The above blog post claims that experiment
    reveals all browsers to send UTF-8, so let's go with that? BUT WHAT ABOUT
    MAXTHON?!?!?!.

    """
    if path:
        try:
            path.decode('ASCII')    # NB: We throw away this unicode!
        except UnicodeDecodeError:

            # XXX How would we get non-ASCII here? The lookout.net post
            # indicates that all browsers send ASCII for the path.

            # Some servers (gevent) clobber %2F inside of paths, such
            # that we see /foo%2Fbar/ as /foo/bar/. The %2F is lost to us.
            parts = [urllib.quote(x) for x in quoted_slash_re.split(path)]
            path = b"%2F".join(parts)

    if qs:
        try:
            qs.decode('ASCII')      # NB: We throw away this unicode!
        except UnicodeDecodeError:
            # Cross our fingers and hope we have UTF-8 bytes from MSIE. Let's
            # perform the percent-encoding that we would expect MSIE to have
            # done for us.
            qs = urllib.quote_plus(qs)
        qs = b'?' + qs

    return path + qs


def make_franken_headers(environ):
    """Takes a WSGI environ, returns a bytestring.
    """

    # There are a couple keys that CherryPyWSGIServer explicitly doesn't
    # include as HTTP_ keys. I'm not sure why, but I believe we want them.
    also = ['CONTENT_TYPE', 'CONTENT_LENGTH']

    headers = []
    for k, v in environ.items():
        val = None
        if k.startswith('HTTP_'):
            k = k[len('HTTP_'):]
            val = v
        elif k in also:
            val = v
        if val is not None:
            k = k.replace('_', '-')
            headers.append(': '.join([k, v]))

    return str('\r\n'.join(headers))  # *sigh*


def kick_against_goad(environ):
    """Kick against the goad. Try to squeeze blood from a stone. Do our best.
    """
    method = environ['REQUEST_METHOD']
    uri = make_franken_uri( environ.get('PATH_INFO', b'')
                          , environ.get('QUERY_STRING', b'')
                          )
    server = environ.get('SERVER_SOFTWARE', b'')
    version = environ['SERVER_PROTOCOL']
    headers = make_franken_headers(environ)
    body = environ['wsgi.input']
    return method, uri, server, version, headers, body


# *WithRaw
# ========
# A few parts of the Request object model use these generic objects.

class IntWithRaw(int):
    """Generic subclass of int to store the underlying raw bytestring.
    """

    __slots__ = ['raw']

    def __new__(cls, i):
        if i is None:
            i = 0
        obj = super(IntWithRaw, cls).__new__(cls, i)
        obj.raw = str(i)
        return obj

class UnicodeWithRaw(unicode):
    """Generic subclass of unicode to store the underlying raw bytestring.
    """

    __slots__ = ['raw']

    def __new__(cls, raw, encoding="UTF-8"):
        obj = super(UnicodeWithRaw, cls).__new__(cls, raw.decode(encoding))
        obj.raw = raw
        return obj

class PathPart(unicode):
    """A string with a mapping for extra data about it."""

    __slots__ = ['params']

    def __new__(cls, value, params):
        obj = super(PathPart, cls).__new__(cls, value)
        obj.params = params
        return obj

###########
# Request #
###########

class Request(str):
    """Represent an HTTP Request message. It's bytes, dammit. But lazy.
    """

    resource = None
    original_resource = None
    server_software = ''
    fs = '' # the file on the filesystem that will handle this request

    # NB: no __slots__ for str:
    #   http://docs.python.org/reference/datamodel.html#__slots__


    def __new__(cls, method=b'GET', uri=b'/', server_software=b'',
                version=b'HTTP/1.1', headers=b'', body=None):
        """Takes five bytestrings and an iterable of bytestrings.
        """
        obj = str.__new__(cls, '') # start with an empty string, see below for
                                   # laziness
        obj.server_software = server_software
        try:
            obj.line = Line(method, uri, version)
            if not headers:
                headers = b'Host: localhost'
            obj.headers = Headers(headers)
            if body is None:
                body = StringIO('')
            obj.body = Body( obj.headers
                           , body
                           , obj.server_software
                            )
            obj.context = Context(obj)
        except UnicodeError:
            # Figure out where the error occurred.
            # ====================================
            # This gives us *something* to go on when we have a Request we
            # can't parse. XXX Make this more nicer. That will require wrapping
            # every point in Request parsing where we decode bytes.

            tb = sys.exc_info()[2]
            while tb.tb_next is not None:
                tb = tb.tb_next
            frame = tb.tb_frame
            filename = tb.tb_frame.f_code.co_filename

            raise Response(400, "Request is undecodable. "
                                "(%s:%d)" % (filename, frame.f_lineno))
        return obj


    @classmethod
    def from_wsgi(cls, environ):
        """Given a WSGI environ, return an instance of cls.

        The conversion from HTTP to WSGI is lossy. This method does its best to
        go the other direction, but we can't guarantee that we've reconstructed
        the bytes as they were on the wire (which is what I want). It would
        also be more efficient to parse directly for our API. But people love
        their gunicorn. :-/

        """
        return cls(*kick_against_goad(environ))


    # Extend str to lazily load bytes.
    # ================================
    # When working with a Request object interactively or in a debugging
    # situation we want it to behave transparently string-like. We don't want
    # to read bytes off the wire if we can avoid it, though, because for mega
    # file uploads and such this could have a big impact.

    _raw = "" # XXX We should reset this when subobjects are mutated.
    def __str__(self):
        """Lazily load the body and return the whole message.
        """
        if not self._raw:
            fmt = "%s\r\n%s\r\n\r\n%s"
            self._raw = fmt % (self.line.raw, self.headers.raw, self.body.raw)
        return self._raw

    def __repr__(self):
        return str.__repr__(str(self))

    # str defines rich comparisons, so we have to extend those and not simply
    # __cmp__ (http://docs.python.org/reference/datamodel.html#object.__lt__)

    def __lt__(self, other): return str.__lt__(str(self), other)
    def __le__(self, other): return str.__le__(str(self), other)
    def __eq__(self, other): return str.__eq__(str(self), other)
    def __ne__(self, other): return str.__ne__(str(self), other)
    def __gt__(self, other): return str.__gt__(str(self), other)
    def __ge__(self, other): return str.__ge__(str(self), other)


    # Public Methods
    # ==============

    def allow(self, *methods):
        """Given method strings, raise 405 if ours is not among them.

        The method names are case insensitive (they are uppercased). If 405
        is raised then the Allow header is set to the methods given.

        """
        methods = [x.upper() for x in methods]
        if self.line.method not in methods:
            raise Response(405, headers={'Allow': ', '.join(methods)})

    def is_xhr(self):
        """Check the value of X-Requested-With.
        """
        val = self.headers.get('X-Requested-With', '')
        return val.lower() == 'xmlhttprequest'

    @staticmethod
    def redirect(location, code=None, permanent=False):
        """Given a string, an int, and a boolean, raise a Response.

        If code is None then it will be set to 301 (Moved Permanently) if
        permanent is True and 302 (Found) if it is False.

        XXX Some day port this:

            http://cherrypy.org/browser/trunk/cherrypy/_cperror.py#L154

        """
        if code is None:
            code = permanent is True and 301 or 302
        raise Response(code, headers={'Location': location})


    def _infer_media_type(self):
        """Guess a media type based on our filesystem path.

        The gauntlet function indirect_negotiation modifies the filesystem
        path, and we want to infer a media type from the path before that
        change. However, we're not ready at that point to infer a media type
        for *all* requests. So we need to perform this inference in a couple
        places, and hence it's factored out here.

        """
        media_type = mimetypes.guess_type(self.fs, strict=False)[0]
        if media_type is None:
            media_type = self.website.media_type_default
        return media_type

# Request -> Line
# ---------------

class Line(unicode):
    """Represent the first line of an HTTP Request message.
    """

    __slots__ = ['method', 'uri', 'version', 'raw']

    def __new__(cls, method, uri, version):
        """Takes three bytestrings.
        """
        raw = " ".join([method, uri, version])
        method = Method(method)
        uri = URI(uri)
        version = Version(version)
        decoded = u" ".join([method, uri, version])

        obj = super(Line, cls).__new__(cls, decoded)
        obj.method = method
        obj.uri = uri
        obj.version = version
        obj.raw = raw
        return obj



# Request -> Method
# -----------------

STANDARD_METHODS = set(["OPTIONS", "GET", "HEAD", "POST", "PUT", "DELETE", "TRACE",
                    "CONNECT"])

SEPARATORS = ("(", ")", "<", ">", "@", ",", ";", ":", "\\", '"', "/", "[", "]",
              "?", "=", "{", "}", " ", "\t")

# NB: No set comprehensions until 2.7.
BYTES_ALLOWED_IN_METHOD = set(chr(i) for i in range(32, 127))
BYTES_ALLOWED_IN_METHOD -= set(SEPARATORS)

class Method(unicode):
    """Represent the HTTP method in the first line of an HTTP Request message.

    Spec sez ASCII subset:

        Method         = "OPTIONS"                ; Section 9.2
                       | "GET"                    ; Section 9.3
                       | "HEAD"                   ; Section 9.4
                       | "POST"                   ; Section 9.5
                       | "PUT"                    ; Section 9.6
                       | "DELETE"                 ; Section 9.7
                       | "TRACE"                  ; Section 9.8
                       | "CONNECT"                ; Section 9.9
                       | extension-method
        extension-method = token

        (http://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html#sec5.1.1)


        CHAR           = <any US-ASCII character (octets 0 - 127)>
        ...
        CTL            = <any US-ASCII control character
                         (octets 0 - 31) and DEL (127)>
        ...
        SP             = <US-ASCII SP, space (32)>
        HT             = <US-ASCII HT, horizontal-tab (9)>
        ...
        token          = 1*<any CHAR except CTLs or separators>
        separators     = "(" | ")" | "<" | ">" | "@"
                       | "," | ";" | ":" | "\" | <">
                       | "/" | "[" | "]" | "?" | "="
                       | "{" | "}" | SP | HT

        (http://www.w3.org/Protocols/rfc2616/rfc2616-sec2.html#sec2.2)

    """

    __slots__ = ['raw']

    def __new__(cls, raw):
        if raw not in STANDARD_METHODS: # fast for 99.999% case
            for i, byte in enumerate(raw):
                if (i == 64) or (byte not in BYTES_ALLOWED_IN_METHOD):

                    # "This is the appropriate response when the server does
                    #  not recognize the request method and is not capable of
                    #  supporting it for any resource."
                    #
                    #  http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html

                    safe = ascii_dammit(raw)
                    raise Response(501, "Your request-method violates RFC "
                                        "2616: %s" % safe)

        obj = super(Method, cls).__new__(cls, raw.decode('ASCII'))
        obj.raw = raw
        return obj


# Request -> Line -> URI
# ......................

class URI(unicode):
    """Represent the Request-URI in the first line of an HTTP Request message.

    XXX spec-ify this

    """

    __slots__ = ['scheme', 'username', 'password', 'host', 'port', 'path',
                 'querystring', 'raw']

    def __new__(cls, raw):

        # split str and not unicode so we can store .raw for each subobj
        uri = urlparse.urlsplit(raw)

        # scheme is going to be ASCII 99.99999999% of the time
        scheme = UnicodeWithRaw(uri.scheme)

        # let's decode username and password as url-encoded UTF-8
        no_None = lambda o: o if o is not None else ""
        parse = lambda o: UnicodeWithRaw(urllib.unquote(no_None(o)))
        username = parse(uri.username)
        password = parse(uri.password)

        # host we will decode as IDNA, which may raise UnicodeError
        host = UnicodeWithRaw(no_None(uri.hostname), 'IDNA')

        # port is IntWithRaw (will be 0 if absent), which is fine
        port = IntWithRaw(uri.port)

        # path and querystring get bytes and do their own parsing
        path = Path(uri.path)  # further populated in gauntlet
        querystring = Querystring(uri.query)

        # we require that the uri as a whole be decodable with ASCII
        decoded = raw.decode('ASCII')
        obj = super(URI, cls).__new__(cls, decoded)
        obj.scheme = scheme
        obj.username = username
        obj.password = password
        obj.host = host
        obj.port = port
        obj.path = path
        obj.querystring = querystring
        obj.raw = raw
        return obj

def extract_rfc2396_params(path):
    """RFC2396 section 3.3 says that path components of a URI can have
    'a sequence of parameters, indicated by the semicolon ";" character.'
    and that ' Within a path segment, the characters "/", ";", "=", and
    "?" are reserved.'  This way you can do
    /frisbee;color=red;size=small/logo;sponsor=w3c;color=black/image.jpg
    and each path segment gets its own params.

    * path should be raw so we don't split or operate on a decoded character
    * output is decoded
    """
    pathsegs = path.lstrip(b'/').split(b'/')
    def decode(input):
        return urllib.unquote(input).decode('UTF-8')

    segments_with_params = []
    for component in pathsegs:
        parts = component.split(b';')
        params = Mapping()
        segment = decode(parts[0])
        for p in parts[1:]:
            if '=' in p:
                k, v = p.split(b'=', 1)
            else:
                k, v = p, b''
            params.add(decode(k), decode(v))
        segments_with_params.append(PathPart(segment, params))
    return segments_with_params


# Request -> Line -> URI -> Path

class Path(Mapping):
    """Represent the path of a resource.

    This is populated by aspen.gauntlet.virtual_paths.

    """

    def __init__(self, raw):
        self.raw = raw
        self.decoded = urllib.unquote(raw).decode('UTF-8')
        self.parts = extract_rfc2396_params(raw)


# Request -> Line -> URI -> Querystring

class Querystring(Mapping):
    """Represent an HTTP querystring.
    """

    def __init__(self, raw):
        """Takes a string of type application/x-www-form-urlencoded.
        """
        self.decoded = urllib.unquote_plus(raw).decode('UTF-8')
        self.raw = raw

        # parse_qs does its own unquote_plus'ing ...
        as_dict = cgi.parse_qs( raw
                              , keep_blank_values = True
                              , strict_parsing = False
                               )

        # ... but doesn't decode to unicode.
        for k, vals in as_dict.items():
            as_dict[k.decode('UTF-8')] = [v.decode('UTF-8') for v in vals]

        Mapping.__init__(self, as_dict)


# Request -> Line -> Version
# ..........................

versions = { 'HTTP/0.9': ((0, 9), u'HTTP/0.9')
           , 'HTTP/1.0': ((1, 0), u'HTTP/1.0')
           , 'HTTP/1.1': ((1, 1), u'HTTP/1.1')
            }  # Go ahead, find me another version.

version_re = re.compile('HTTP/\d+\.\d+')

class Version(unicode):
    """Represent the version in an HTTP status line. HTTP/1.1. Like that.

        HTTP-Version   = "HTTP" "/" 1*DIGIT "." 1*DIGIT

        (http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html)

    """

    __slots__ = ['major', 'minor', 'info', 'raw']

    def __new__(cls, raw):
        version = versions.get(raw, None)
        if version is None: # fast for 99.999999% case
            safe = ascii_dammit(raw)
            if version_re.match(raw) is None:
                raise Response(400, "Bad HTTP version: %s." % safe)
            else:
                raise Response(505, "HTTP Version Not Supported: %s. This "
                                    "server supports HTTP/0.9, HTTP/1.0, and "
                                    "HTTP/1.1." % safe)
        version, decoded = version

        obj = super(Version, cls).__new__(cls, decoded)
        obj.major = version[0]  # 1
        obj.minor = version[1]  # 1
        obj.info = version      # (1, 1)
        obj.raw = raw           # 'HTTP/1.1'
        return obj


# Request -> Headers
# ------------------

class Headers(BaseHeaders):
    """Model headers in an HTTP Request message.
    """

    def __init__(self, raw):
        """Extend BaseHeaders to add extra attributes.
        """
        BaseHeaders.__init__(self, raw)


        # Host
        # ====
        # Per the spec, respond with 400 if no Host header is given. However,
        # we prefer X-Forwarded-For if that is available.

        host = self.get('X-Forwarded-Host', self['Host']) # KeyError raises 400
        self.host = UnicodeWithRaw(host, encoding='idna')


        # Scheme
        # ======
        # http://docs.python.org/library/wsgiref.html#wsgiref.util.guess_scheme

        scheme = 'https' if self.get('HTTPS', False) else 'http'
        self.scheme = UnicodeWithRaw(scheme)


# Request -> Body
# ---------------

class Body(Mapping):
    """Represent the body of an HTTP request.
    """

    def __init__(self, headers, fp, server_software):
        """Takes a str, a file-like object, and another str.

        If the Mapping API is used (in/one/all/has), then the iterable will be
        read and parsed as media of type application/x-www-form-urlencoded or
        multipart/form-data, according to content_type.

        """
        typecheck(headers, Headers, server_software, str)
        raw_len = int(headers.get('Content-length', '') or '0')
        self.raw = self._read_raw(server_software, fp, raw_len)  # XXX lazy!
        parsed = self._parse(headers, self.raw)
        if parsed is None:
            # There was no content-type. Use self.raw.
            pass
        else:
            for k in parsed.keys():
                v = parsed[k]
                if isinstance(v, cgi.MiniFieldStorage):
                    v = v.value.decode("UTF-8")  # XXX Really? Always UTF-8?
                else:
                    assert isinstance(v, cgi.FieldStorage), v
                    if v.filename is None:
                        v = v.value.decode("UTF-8")
                self[k] = v


    def _read_raw(self, server_software, fp, raw_len):
        """Given str, a file-like object, and the number of expected bytes, return a bytestring.
        """
        if not server_software.startswith('Rocket'):  # normal
            raw = fp.read(raw_len)
        else:                                                       # rocket

            # Email from Rocket guy: While HTTP stipulates that you shouldn't
            # read a socket unless you are specifically expecting data to be
            # there, WSGI allows (but doesn't require) for that
            # (http://www.python.org/dev/peps/pep-3333/#id25).  I've started
            # support for this (if you feel like reading the code, its in the
            # connection class) but this feature is not yet production ready
            # (it works but it way too slow on cPython).
            #
            # The hacky solution is to grab the socket from the stream and
            # manually set the timeout to 0 and set it back when you get your
            # data (or not).
            #
            # If you're curious, those HTTP conditions are (it's better to do
            # this anyway to avoid unnecessary and slow OS calls):
            # - You can assume that there will be content in the body if the
            #   request type is "POST" or "PUT"
            # - You can figure how much to read by the "CONTENT_LENGTH" header
            #   existence with a valid integer value
            #   - alternatively "CONTENT_TYPE" can be set with no length and
            #     you can read based on the body content ("content-encoding" =
            #     "chunked" is a good example).
            #
            # Here's the "hacky solution":

            _tmp = fp._sock.timeout
            fp._sock.settimeout(0) # equiv. to non-blocking
            try:
                raw = fp.read(raw_len)
            except Exception, exc:
                if exc.errno != 35:
                    raise
                raw = ""
            fp._sock.settimeout(_tmp)

        return raw


    def _parse(self, headers, raw):
        """Takes a dict and a bytestring.

        http://www.w3.org/TR/html401/interact/forms.html#h-17.13.4

        """
        typecheck(headers, Headers, raw, str)


        # Switch on content type.

        parts = [p.strip() for p in headers.get("Content-Type", "").split(';')]
        content_type = parts.pop(0)

        # XXX Do something with charset.
        params = {}
        for part in parts:
            if '=' in part:
                key, val = part.split('=', 1)
                params[key] = val

        if content_type == "application/x-www-form-urlencoded":
            # Decode.
            pass
        elif content_type == "multipart/form-data":
            # Deal with bytes.
            pass
        else:
            # Bail.
            return None


        # Force the cgi module to parse as we want. If it doesn't find
        # something besides GET or HEAD here then it ignores the fp
        # argument and instead uses environ['QUERY_STRING'] or even
        # sys.stdin(!). We want it to parse request bodies even if the
        # method is GET (we already parsed the querystring elsewhere).

        environ = {"REQUEST_METHOD": "POST"}


        return cgi.FieldStorage( fp = cgi.StringIO(raw)  # Ack.
                               , environ = environ
                               , headers = headers
                               , keep_blank_values = True
                               , strict_parsing = False
                                )

########NEW FILE########
__FILENAME__ = response
"""
aspen.http.response
~~~~~~~~~~~~~~~~~~~
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


import os
import re
import sys

from aspen.utils import ascii_dammit
from aspen.http import status_strings
from aspen.http.baseheaders import BaseHeaders as Headers


class CloseWrapper(object):
    """Conform to WSGI's facility for running code *after* a response is sent.
    """

    def __init__(self, request, body):
        self.request = request
        self.body = body

    def __iter__(self):
        return iter(self.body)

    def close(self):
        # No longer using this since we ripped out Socket.IO support.
        pass


# Define a charset name filter.
# =============================
# "The character set names may be up to 40 characters taken from the
#  printable characters of US-ASCII."
#  (http://www.iana.org/assignments/character-sets)
#
# We're going to be slightly more restrictive. Instead of allowing all
# printable characters, which include whitespace and newlines, we're going to
# only allow punctuation that is actually in use in the current IANA list.

charset_re = re.compile("^[A-Za-z0-9:_()+.-]{1,40}$")


class Response(Exception):
    """Represent an HTTP Response message.
    """

    request = None

    def __init__(self, code=200, body='', headers=None, charset="UTF-8"):
        """Takes an int, a string, a dict, and a basestring.

            - code      an HTTP response code, e.g., 404
            - body      the message body as a string
            - headers   a Headers instance
            - charset   string that will be set in the Content-Type in the future at some point but not now

        Code is first because when you're raising your own Responses, they're
        usually error conditions. Body is second because one more often wants
        to specify a body without headers, than a header without a body.

        """
        if not isinstance(code, int):
            raise TypeError("'code' must be an integer")
        elif not isinstance(body, basestring) and not hasattr(body, '__iter__'):
            raise TypeError("'body' must be a string or iterable of strings")
        elif headers is not None and not isinstance(headers, (dict, list)):
            raise TypeError("'headers' must be a dictionary or a list of " +
                            "2-tuples")
        elif charset_re.match(charset) is None:
            raise TypeError("'charset' must match " + charset_re.pattern)

        Exception.__init__(self)
        self.code = code
        self.body = body
        self.headers = Headers(b'')
        self.charset = charset
        if headers:
            if isinstance(headers, dict):
                headers = headers.items()
            for k, v in headers:
                self.headers[k] = v
        self.headers.cookie.load(self.headers.get('Cookie', b''))

    def __call__(self, environ, start_response):
        wsgi_status = str(self)
        for morsel in self.headers.cookie.values():
            self.headers.add('Set-Cookie', morsel.OutputString())
        wsgi_headers = []
        for k, vals in self.headers.iteritems():
            try:        # XXX This is a hack. It's red hot, baby.
                k = k.encode('US-ASCII')
            except UnicodeEncodeError:
                k = ascii_dammit(k)
                raise ValueError("Header key %s must be US-ASCII.")
            for v in vals:
                try:    # XXX This also is a hack. It is also red hot, baby.
                    v = v.encode('US-ASCII')
                except UnicodeEncodeError:
                    v = ascii_dammit(v)
                    raise ValueError("Header value %s must be US-ASCII.")
                wsgi_headers.append((k, v))

        start_response(wsgi_status, wsgi_headers)
        body = self.body
        if isinstance(body, basestring):
            body = [body]
        body = (x.encode(self.charset) if isinstance(x, unicode) else x for x in body)
        return CloseWrapper(self.request, body)

    def __repr__(self):
        return "<Response: %s>" % str(self)

    def __str__(self):
        return "%d %s" % (self.code, self._status())

    def _status(self):
        return status_strings.get(self.code, 'Unknown HTTP status')

    def _to_http(self, version):
        """Given a version string like 1.1, return an HTTP message, a string.
        """
        status_line = "HTTP/%s" % version
        headers = self.headers.raw
        body = self.body
        if self.headers.get('Content-Type', '').startswith('text/'):
            body = body.replace('\n', '\r\n')
            body = body.replace('\r\r', '\r')
        return '\r\n'.join([status_line, headers, '', body])

    def whence_raised(self):
        """Return a tuple, (filename, linenum) where we were raised from.

        If we're not the exception currently being handled then the return
        value is (None, None).

        """
        tb = filepath = linenum = None
        try:
            cls, response, tb = sys.exc_info()
            if response is self:
                while tb.tb_next is not None:
                    tb = tb.tb_next
                frame = tb.tb_frame

                # filepath
                pathparts = tb.tb_frame.f_code.co_filename.split(os.sep)[-2:]
                # XXX It'd be nice to use www_root and project_root here, but
                # self.request is None at this point afaict, and it's enough to
                # show the last two parts just to differentiate index.html or
                # __init__.py.
                filepath = os.sep.join(pathparts)

                # linenum
                linenum = frame.f_lineno
        finally:
            del tb  # http://docs.python.org/2/library/sys.html#sys.exc_info
        return filepath, linenum

########NEW FILE########
__FILENAME__ = json_
"""
aspen.json
++++++++++
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import datetime


# Find a json module.
# ===================
# The standard library includes simplejson as json since 2.6, but without the
# C speedups. So we prefer simplejson if it is available.

try:
    import simplejson as _json
except ImportError:
    try:
        import json as _json
    except ImportError:
        _json = None


# Allow arbitrary encoders to be registered.
# ==========================================
# One of the difficulties with JSON in Python is that pretty quickly one hits a
# class or type that needs extra work to decode to JSON. For example, support
# for the decimal.Decimal class was added in simplejson 2.1, which isn't in the
# stdlib version as of 2.7/3.2. Support for classes from the datetime module
# isn't in simplejson as of 2.3.2. Since Aspen takes on ownership of JSON
# encoding, we need to give Aspen users a way to register (and unregister, I
# guess) new encoders. You can do this by calling dumps with the cls keyword,
# but we call dumps for you for JSON resources, so we want a way to influence
# decoding that doesn't depend on dumps. And this is that way:

encoders = {}
def register_encoder(cls, encode):
    """Register the encode function for cls.

    An encoder should take an instance of cls and return something basically
    serializable (strings, lists, dictionaries).

    """
    encoders[cls] = encode

def unregister_encoder(cls):
    """Given a class, remove any encoder that has been registered for it.
    """
    if cls in encoders:
        del encoders[cls]

# http://docs.python.org/library/json.html
register_encoder(complex, lambda obj: [obj.real, obj.imag])

# http://stackoverflow.com/questions/455580/
register_encoder(datetime.datetime, lambda obj: obj.isoformat())
register_encoder(datetime.date, lambda obj: obj.isoformat())
register_encoder(datetime.time, lambda obj: obj.isoformat())


# Be lazy.
# ========
# Allow Aspen to run without JSON support. In practice that means that Python
# 2.5 users won't be able to use JSON resources.

if _json is not None:
    class FriendlyEncoder(_json.JSONEncoder):
        """Add support for additional types to the default JSON encoder.
        """
        def default(self, obj):
            cls = obj.__class__ # Use this instead of type(obj) because that
                                # isn't consistent between new- and old-style
                                # classes, and this is.
            encode = encoders.get(cls, _json.JSONEncoder.default)
            return encode(obj)

def lazy_check():
    if _json is None:
        raise ImportError("Neither simplejson nor json was found. Try "
                          "installing simplejson to use dynamic JSON "
                          "simplates. See "
                          "http://aspen.io/simplates/json/#libraries for "
                          "more information.")


# Main public API.
# ================

def load(*a, **kw):
    lazy_check()
    return _json.load(*a, **kw)

def dump(*a, **kw):
    lazy_check()
    if 'cls' not in kw:
        kw['cls'] = FriendlyEncoder
    # Beautify json by default.
    if 'sort_keys' not in kw:
        kw['sort_keys'] = True
    if 'indent' not in kw:
        kw['indent'] = 4
    return _json.dump(*a, **kw)

def loads(*a, **kw):
    lazy_check()
    return _json.loads(*a, **kw)

def dumps(*a, **kw):
    lazy_check()
    if 'cls' not in kw:
        kw['cls'] = FriendlyEncoder
    # Beautify json by default.
    if 'sort_keys' not in kw:
        kw['sort_keys'] = True
    if 'indent' not in kw:
        kw['indent'] = 4
    return _json.dumps(*a, **kw)


########NEW FILE########
__FILENAME__ = logging
"""
aspen.logging
+++++++++++++

Aspen logging. It's simple.

There are log and log_dammit functions that take arbitrary positional
arguments, stringify them, write them to stdout, and flush stdout. Each line
written is prepended with process and thread identifiers. The philosophy is
that additional abstraction layers above Aspen can handle timestamping along
with piping to files, rotation, etc. PID and thread id are best handled inside
the process, however.

The LOGGING_THRESHOLD attribute controls the amount of information that will be
logged. The level kwarg to log must be greater than or equal to the threshold
for the message to get through. Aspen itself logs at levels zero (via log with
the default level value) and one (with the log_dammit wrapper). It's expected
that your application will have its own wrapper(s).

Unicode objects are encoded as UTF-8. Bytestrings are passed through as-is.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from __future__ import with_statement
import os
import pprint
import sys
import thread
import threading


LOGGING_THRESHOLD = -1
PID = os.getpid()
LOCK = threading.Lock()


def stringify(o):
    """Given an object, return a str, never raising ever.
    """
    if isinstance(o, str):
        o = o
    elif isinstance(o, unicode):
        o = o.encode('UTF-8', 'backslashreplace')
    else:
        o = pprint.pformat(o)
    return o


def log(*messages, **kw):
    level = kw.get('level', 0)
    if level >= LOGGING_THRESHOLD:
        # Be sure to use Python 2.5-compatible threading API.
        t = threading.currentThread()
        fmt = "pid-%s thread-%s (%s) %%s" % ( PID
                                            , thread.get_ident()
                                            , t.getName()
                                             )
        for message in messages:
            message = stringify(message)
            for line in message.splitlines():
                with LOCK:
                    # Log lines can get interleaved, but that's okay, because
                    # we prepend lines with thread identifiers that can be used
                    # to reassemble log messages per-thread.
                    print(fmt % line.decode('utf8'))
                    sys.stdout.flush()


def log_dammit(*messages):
    log(*messages, **{'level': 1})
    #log(*messages, level=1)  <-- SyntaxError in Python 2.5

########NEW FILE########
__FILENAME__ = json_dump
"""
aspen.renderers.json_dump
~~~~~~~~~~~~~~~~~~~~~~~~~
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from aspen import renderers
from aspen import json

class Renderer(renderers.Renderer):
    def compile(self, filepath, raw):
        return raw

    def render_content(self, context):
        if 'Content-type' not in context['response'].headers:
            response = context['response']
            website = context['website']
            response.headers['Content-type'] = website.media_type_json
        return json.dumps(eval(self.compiled, globals(), context))


class Factory(renderers.Factory):
    Renderer = Renderer


########NEW FILE########
__FILENAME__ = stdlib_format
"""
aspen.renderers.stdlib_format
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from aspen import renderers


class Renderer(renderers.Renderer):
    def compile(self, filepath, raw):
        return raw

    def render_content(self, context):
        return self.compiled.format(**context)


class Factory(renderers.Factory):
    Renderer = Renderer

########NEW FILE########
__FILENAME__ = stdlib_percent
"""
aspen.renderers.stdlib_percent
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from aspen import renderers


class Renderer(renderers.Renderer):
    def compile(self, filepath, raw):
        return raw

    def render_content(self, context):
        return self.compiled % context


class Factory(renderers.Factory):
    Renderer = Renderer


########NEW FILE########
__FILENAME__ = stdlib_template
"""
aspen.renderers.stdlib_template
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from aspen import renderers
from string import Template

class Renderer(renderers.Renderer):
    def compile(self, filepath, raw):
        return Template(raw)

    def render_content(self, context):
        return self.compiled.substitute(context)


class Factory(renderers.Factory):
    Renderer = Renderer

########NEW FILE########
__FILENAME__ = dynamic_resource
"""
aspen.resources.dynamic_resource
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from aspen import Response
from aspen.resources.pagination import split_and_escape, Page
from aspen.resources.resource import Resource


class StringDefaultingList(list):
    def __getitem__(self, key):
        try:
            return list.__getitem__(self, key)
        except KeyError:
            return str(key)

ORDINALS = StringDefaultingList([ 'zero' , 'one' , 'two', 'three', 'four'
                                , 'five', 'six', 'seven', 'eight', 'nine'
                                 ])


class DynamicResource(Resource):
    """This is the base for negotiating and rendered resources.
    """

    min_pages = None  # set on subclass
    max_pages = None

    def __init__(self, *a, **kw):
        Resource.__init__(self, *a, **kw)
        pages = self.parse_into_pages(self.raw)
        self.pages = self.compile_pages(pages)


    def respond(self, request, response=None):
        """Given a Request and maybe a Response, return or raise a Response.
        """
        response = response or Response(charset=self.website.charset_dynamic)


        # Populate context.
        # =================

        context = self.populate_context(request, response)


        # Exec page two.
        # ==============

        try:
            exec self.pages[1] in context
        except Response, response:
            self.process_raised_response(response)
            raise

        # if __all__ is defined, only pass those variables to templates
        # if __all__ is not defined, pass full context to templates

        if '__all__' in context:
            newcontext = dict([ (k, context[k]) for k in context['__all__'] ])
            context = newcontext

        # Hook.
        # =====

        try:
            response = self.get_response(context)
        except Response, response:
            self.process_raised_response(response)
            raise
        else:
            return response


    def populate_context(self, request, response):
        """Factored out to support testing.
        """
        context = request.context
        context.update(self.pages[0])
        context['request'] = request
        context['response'] = response
        context['resource'] = self
        return context


    def parse_into_pages(self, raw):
        """Given a bytestring, return a list of pages.

        Subclasses extend this to implement additional semantics.

        """

        pages = list(split_and_escape(raw))
        npages = len(pages)

        # Check for too few pages.
        if npages < self.min_pages:
            type_name = self.__class__.__name__[:-len('resource')]
            msg = "%s resources must have at least %s pages; %s has %s."
            msg %= ( type_name
                   , ORDINALS[self.min_pages]
                   , self.fs
                   , ORDINALS[npages]
                    )
            raise SyntaxError(msg)

        # Check for too many pages. This is user error.
        if self.max_pages is not None and npages > self.max_pages:
            type_name = self.__class__.__name__[:-len('resource')]
            msg = "%s resources must have at most %s pages; %s has %s."
            msg %= ( type_name
                   , ORDINALS[self.max_pages]
                   , self.fs
                   , ORDINALS[npages]
                    )
            raise SyntaxError(msg)

        return pages

    def compile_pages(self, pages):
        """Given a list of pages, replace the pages with objects.

        All dynamic resources compile the first two pages the same way. It's
        the third and following pages that differ, so we require subclasses to
        supply a method for that: compile_page.

        """

        # Exec the first page and compile the second.
        # ===========================================

        one, two = pages[:2]

        context = dict()
        context['__file__'] = self.fs
        context['website'] = self.website

        one = compile(one.padded_content, self.fs, 'exec')
        exec one in context    # mutate context
        one = context          # store it

        two = compile(two.padded_content, self.fs, 'exec')

        pages[:2] = (one, two)

        # Subclasses are responsible for the rest.
        # ========================================

        pages[2:] = (self.compile_page(page) for page in pages[2:])

        return pages

    @staticmethod
    def _prepend_empty_pages(pages, min_length):
        """Given a list of pages, and a min length, prepend blank pages to the
        list until it is at least as long as min_length
        """
        num_extra_pages = min_length - len(pages)
        #Note that range(x) returns an empty list if x < 1
        pages[0:0] = (Page('') for _ in range(num_extra_pages))

    # Hooks
    # =====

    def compile_page(self, *a):
        """Given a page, return an object.
        """
        raise NotImplementedError

    def process_raised_response(self, response):
        """Given a response object, mutate it as needed.
        """
        pass

    def get_response(self, context):
        """Given a context dictionary, return a Response object.
        """
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = negotiated_resource
"""
aspen.resources.negotiated_resource
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Implements negotiated resources.

Aspen supports content negotiation. If a file has no file extension, then it
will be handled as a "negotiated resource". The format of the file is like
this:

    import foo, json
    ^L
    data = foo.bar(request)
    ^L text/plain
    {{ data }}
    ^L text/json
    {{ json.dumps(data) }}

We have vendored in Joe Gregorio's content negotiation library to do the heavy
lifting (parallel to how we handle _cherrypy and _tornado vendoring). If a file
*does* have a file extension (foo.html), then it is a rendered resource with a
mimetype computed from the file extension. It is a SyntaxError for a file to
have both an extension *and* multiple content pages.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import re
import sys

from aspen import Response, log
import mimeparse
from aspen.resources.dynamic_resource import DynamicResource
from aspen.resources.pagination import parse_specline

renderer_re = re.compile(r'[a-z0-9.-_]+$')
media_type_re = re.compile(r'[A-Za-z0-9.+*-]+/[A-Za-z0-9.+*-]+$')


class NegotiatedResource(DynamicResource):
    """This is a negotiated resource. It has three or more pages.
    """

    min_pages = 3
    max_pages = None


    def __init__(self, *a, **kw):
        self.renderers = {}         # mapping of media type to render function
        self.available_types = []   # ordered sequence of media types
        DynamicResource.__init__(self, *a, **kw)


    def compile_page(self, page):
        """Given a bytestring, return a (renderer, media type) pair.
        """
        make_renderer, media_type = self._parse_specline(page.header)
        renderer = make_renderer(self.fs, page.content)
        if media_type in self.renderers:
            raise SyntaxError("Two content pages defined for %s." % media_type)

        # update internal data structures
        self.renderers[media_type] = renderer

        self.available_types.append(media_type)

        return (renderer, media_type)  # back to parent class

    def get_response(self, context):
        """Given a context dict, return a response object.
        """
        request = context['request']

        # find an Accept header
        accept = request.headers.get('X-Aspen-Accept', None)
        if accept is not None:      # indirect negotiation
            failure = Response(404)
        else:                       # direct negotiation
            accept = request.headers.get('Accept', None)
            msg = "The following media types are available: %s."
            msg %= ', '.join(self.available_types)
            failure = Response(406, msg.encode('US-ASCII'))

        # negotiate or punt
        render, media_type = self.pages[2]  # default to first content page
        if accept is not None:
            try:
                media_type = mimeparse.best_match(self.available_types, accept)
            except:
                # exception means don't override the defaults
                log("Problem with mimeparse.best_match(%r, %r): %r " % (self.available_types, accept, sys.exc_info()))
            else:
                if media_type == '':    # breakdown in negotiations
                    raise failure
                del failure
                render = self.renderers[media_type] # KeyError is a bug

        response = context['response']
        response.body = render(context)
        if 'Content-Type' not in response.headers:
            response.headers['Content-Type'] = media_type
            if media_type.startswith('text/'):
                charset = response.charset
                if charset is not None:
                    response.headers['Content-Type'] += '; charset=' + charset

        return response

    def _parse_specline(self, specline):
        """Given a bytestring, return a two-tuple.

        The incoming string is expected to be of the form:

            media_type via renderer

        The renderer is optional. It will be computed based on media type if
        absent. The return two-tuple contains a render function and a media
        type (as unicode). SyntaxError is raised if there aren't one or two
        parts or if either of the parts is malformed. If only one part is
        passed in it's interpreted as a media type.

        """
        # Parse into parts
        parts = parse_specline(specline)

        #Assign parts
        media_type, renderer = parts
        if renderer == '':
            renderer = self.website.default_renderers_by_media_type[media_type]

        # Validate media type.
        if media_type_re.match(media_type) is None:
            msg = ("Malformed media type %s in specline %s. It must match "
                   "%s.")
            msg %= (media_type, specline, media_type_re.pattern)
            raise SyntaxError(msg)

        # Hydrate and validate renderer.
        make_renderer = self._get_renderer_factory(media_type, renderer)

        # Return.
        return (make_renderer, media_type)


    def _get_renderer_factory(self, media_type, renderer):
        """Given two bytestrings, return a renderer factory or None.
        """
        if renderer_re.match(renderer) is None:
            possible =', '.join(sorted(self.website.renderer_factories.keys()))
            msg = ("Malformed renderer %s. It must match %s. Possible "
                   "renderers (might need third-party libs): %s.")
            raise SyntaxError(msg % (renderer, renderer_re.pattern, possible))

        renderer = renderer.decode('US-ASCII')

        factories = self.website.renderer_factories
        make_renderer = factories.get(renderer, None)
        if isinstance(make_renderer, ImportError):
            raise make_renderer
        elif make_renderer is None:
            possible = []
            want_legend = False
            for k, v in sorted(factories.iteritems()):
                if isinstance(v, ImportError):
                    k = '*' + k
                    want_legend = True
                possible.append(k)
            possible = ', '.join(possible)
            if want_legend:
                legend = " (starred are missing third-party libraries)"
            else:
                legend = ''
            raise ValueError("Unknown renderer for %s: %s. Possible "
                             "renderers%s: %s."
                             % (media_type, renderer, legend, possible))
        return make_renderer

########NEW FILE########
__FILENAME__ = pagination
"""
aspen.resources.pagination
~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import re


SPLITTER = '^\[---+\](?P<header>.*?)(\n|$)'
ESCAPED_SPLITTER = '^\\\\(\\\\*)(\[---+\].*?(\n|$))'
SPECLINE_SPLIT = '(?:\s+|^)via\s+'

SPLITTER = re.compile(SPLITTER, re.MULTILINE)
ESCAPED_SPLITTER = re.compile(ESCAPED_SPLITTER, re.MULTILINE)
SPECLINE_SPLIT = re.compile(SPECLINE_SPLIT)


class Page(object):
    __slots__ = ('header', 'content', 'offset')

    def __init__(self, content, header='', offset=0):
        self.content = content
        self.header = header.decode('ascii')
        self.offset = offset

    @property
    def padded_content(self):
        return ('\n' * self.offset) + self.content


def split(raw):
    '''Pure split generator. This function defines the plain logic to split a
    string into a list of pages
    '''

    current_index = 0
    line_offset = 0
    header = ''

    for page_break in SPLITTER.finditer(raw):
        content = raw[current_index:page_break.start()]
        yield Page(content, header, line_offset)
        line_offset += content.count('\n') + 1
        header = page_break.group('header').strip()
        current_index = page_break.end()

    # Yield final page. If no page dividers were found, this will be all of it
    content = raw[current_index:]
    yield Page(content, header, line_offset)

def escape(content):
    '''Pure escape method. This function defines the logic to properly convert
    escaped splitter patterns in a string
    '''
    return ESCAPED_SPLITTER.sub(r'\1\2', content)

def split_and_escape(raw):
    '''This function defines the logic to split and escape a string.
    '''
    for page in split(raw):
        page.content = escape(page.content)
        yield page

def parse_specline(header):
    '''Attempt to parse the header in a page returned from split(...) as a
    specline. Returns a tuple (content_type, renderer)
    '''
    parts = SPECLINE_SPLIT.split(header, 1) + ['']
    return parts[0].strip(), parts[1].strip()

def can_split(raw, splitter=SPLITTER):
    '''Determine if a text block would be split by a splitter
    '''
    return bool(SPLITTER.search(raw))


########NEW FILE########
__FILENAME__ = rendered_resource
"""
aspen.resources.rendered_resource
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Implements rendered resources.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from aspen.resources.negotiated_resource import NegotiatedResource
from aspen.utils import typecheck
from aspen.resources.pagination import parse_specline


class RenderedResource(NegotiatedResource):
    """Model a limiting case of negotiated resources.

    A negotiated resource has multiple content pages, one per media type, with
    the media type of each explicitly specified in-line. A rendered resource
    has one content page, and the media type is inferred from the file
    extension. In both cases the rendering machinery is used to transform the
    bytes in each page into output for the wire.

    """

    min_pages = 1
    max_pages = 4


    def parse_into_pages(self, raw):
        """Extend to insert page one if needed.
        """
        pages = NegotiatedResource.parse_into_pages(self, raw)
        self._prepend_empty_pages(pages, 3)
        return pages


    def _parse_specline(self, specline):
        """Override to simplify.

        Rendered resources have a simpler specline than negotiated resources.
        They don't have a media type, and the renderer is optional.

        """
        #parse into parts.
        parts = parse_specline(specline)

        #Assign parts, discard media type
        renderer = parts[1]
        media_type = self.media_type
        if not renderer:
            renderer = self.website.default_renderers_by_media_type[media_type]

        #Hydrate and validate renderer
        make_renderer = self._get_renderer_factory(media_type, renderer)

        return (make_renderer, media_type)

########NEW FILE########
__FILENAME__ = resource
"""
aspen.resources.resource
~~~~~~~~~~~~~~~~~~~~~~~~
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


class Resource(object):
    """This is a base class for both static and dynamic resources.
    """

    def __init__(self, website, fs, raw, media_type, mtime):
        self.website = website
        self.fs = fs
        self.raw = raw
        self.media_type = media_type
        self.mtime = mtime

########NEW FILE########
__FILENAME__ = static_resource
"""
aspen.resource.static_resource
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


from aspen import Response
from aspen.resources.resource import Resource


class StaticResource(Resource):

    def __init__(self, *a, **kw):
        Resource.__init__(self, *a, **kw)
        if self.media_type == 'application/json':
            self.media_type = self.website.media_type_json

    def respond(self, request, response=None):
        """Given a Request and maybe a Response, return or raise a Response.
        """
        response = response or Response()
        # XXX Perform HTTP caching here.
        assert type(self.raw) is str # sanity check
        response.body = self.raw
        response.headers['Content-Type'] = self.media_type
        if self.media_type.startswith('text/'):
            charset = self.website.charset_static
            if charset is None:
                pass # Let the browser guess.
            else:
                response.charset = charset
                response.headers['Content-Type'] += '; charset=' + charset
        return response

########NEW FILE########
__FILENAME__ = client
"""
aspen.testing.client
~~~~~~~~~~~~~~~~~~~~
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from Cookie import SimpleCookie
from StringIO import StringIO

from aspen import Response
from aspen.utils import typecheck
from aspen.website import Website

BOUNDARY = b'BoUnDaRyStRiNg'
MULTIPART_CONTENT = b'multipart/form-data; boundary=%s' % BOUNDARY


class DidntRaiseResponse(Exception): pass


def encode_multipart(boundary, data):
    """
    Encodes multipart POST data from a dictionary of form values.

    Borrowed from Django
    The key will be used as the form data name; the value will be transmitted
    as content. If the value is a file, the contents of the file will be sent
    as an application/octet-stream; otherwise, str(value) will be sent.
    """
    lines = []

    for (key, value) in data.items():
        lines.extend([
            b'--' + boundary,
            b'Content-Disposition: form-data; name="%s"' % str(key),
            b'',
            str(value)
        ])

    lines.extend([
        b'--' + boundary + b'--',
        b'',
    ])
    return b'\r\n'.join(lines)


class Client(object):
    """This is the Aspen test client. It is probably useful to you.
    """

    def __init__(self, www_root=None, project_root=None):
        self.www_root = www_root
        self.project_root = project_root
        self.cookie = SimpleCookie()
        self._website = None


    def hydrate_website(self, argv=None):
        if (self._website is None) or (argv is not None):
            argv = [ '--www_root', self.www_root
                   , '--project_root', self.project_root
                    ] + ([] if argv is None else argv)
            self._website = Website(argv)
        return self._website

    website = property(hydrate_website)


    def load_resource(self, path):
        """Given an URL path, return a Resource instance.
        """
        return self.hit('GET', path=path, return_after='get_resource_for_request', want='resource')


    # HTTP Methods
    # ============

    def GET(self, *a, **kw):    return self.hit('GET', *a, **kw)
    def POST(self, *a, **kw):   return self.hit('POST', *a, **kw)

    def GxT(self, *a, **kw):    return self.hxt('GET', *a, **kw)
    def PxST(self, *a, **kw):   return self.hxt('POST', *a, **kw)

    def hxt(self, *a, **kw):
        try:
            self.hit(*a, **kw)
        except Response as response:
            return response
        else:
            raise DidntRaiseResponse

    def hit(self, method, path='/', data=None, body=b'', content_type=MULTIPART_CONTENT,
            raise_immediately=True, return_after=None, want='response', **headers):

        data = {} if data is None else data
        if content_type is MULTIPART_CONTENT:
            body = encode_multipart(BOUNDARY, data)

        environ = self.build_wsgi_environ(method, path, body, str(content_type), **headers)
        state = self.website.respond( environ
                                    , raise_immediately=raise_immediately
                                    , return_after=return_after
                                     )

        response = state.get('response')
        if response is not None:
            if response.headers.cookie:
                self.cookie.update(response.headers.cookie)

        attr_path = want.split('.')
        base = attr_path[0]
        attr_path = attr_path[1:]

        out = state[base]
        for name in attr_path:
            out = getattr(out, name)

        return out


    def build_wsgi_environ(self, method, path, body, content_type, **kw):

        # NOTE that in Aspen (request.py make_franken_headers) only headers
        # beginning with ``HTTP`` are included in the request - and those are
        # changed to no longer include ``HTTP``. There are currently 2
        # exceptions to this: ``'CONTENT_TYPE'``, ``'CONTENT_LENGTH'`` which
        # are explicitly checked for.

        typecheck(path, (str, unicode), method, unicode, content_type, str, body, str)
        environ = {}
        environ[b'CONTENT_TYPE'] = content_type
        environ[b'HTTP_COOKIE'] = self.cookie.output(header=b'', sep=b'; ')
        environ[b'HTTP_HOST'] = b'localhost'
        environ[b'PATH_INFO'] = path if type(path) is str else path.decode('UTF-8')
        environ[b'REMOTE_ADDR'] = b'0.0.0.0'
        environ[b'REQUEST_METHOD'] = method.decode('ASCII')
        environ[b'SERVER_PROTOCOL'] = b'HTTP/1.1'
        environ[b'wsgi.input'] = StringIO(body)
        environ.update(kw)
        return environ

########NEW FILE########
__FILENAME__ = harness
"""
aspen.testing.harness
~~~~~~~~~~~~~~~~~~~~~
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
from collections import namedtuple

from aspen import resources
from aspen.testing.client import Client
from filesystem_tree import FilesystemTree


CWD = os.getcwd()


def teardown():
    """Standard teardown function.

    - reset the current working directory
    - remove FSFIX = %{tempdir}/fsfix
    - reset Aspen's global state
    - clear out sys.path_importer_cache

    """
    os.chdir(CWD)
    # Reset some process-global caches. Hrm ...
    resources.__cache__ = {}
    sys.path_importer_cache = {} # see test_weird.py

teardown() # start clean


class Harness(object):
    """A harness to be used in the Aspen test suite itself. Probably not useful to you.
    """

    def __init__(self):
        self.fs = namedtuple('fs', 'www project')
        self.fs.www = FilesystemTree()
        self.fs.project = FilesystemTree()
        self.client = Client(self.fs.www.root, self.fs.project.root)

    def teardown(self):
        self.fs.www.remove()
        self.fs.project.remove()


    # Simple API
    # ==========

    def simple(self, contents='Greetings, program!', filepath='index.html.spt', uripath=None,
            argv=None, **kw):
        """A helper to create a file and hit it through our machinery.
        """
        if filepath is not None:
            self.fs.www.mk((filepath, contents))
        if argv is not None:
            self.client.hydrate_website(argv)

        if uripath is None:
            if filepath is None:
                uripath = '/'
            else:
                uripath = '/' + filepath
                if uripath.endswith('.spt'):
                    uripath = uripath[:-len('.spt')]
                for indexname in self.client.website.indices:
                    if uripath.endswith(indexname):
                        uripath = uripath[:-len(indexname)]
                        break

        return self.client.GET(uripath, **kw)

    def make_request(self, *a, **kw):
        kw['return_after'] = 'dispatch_request_to_filesystem'
        kw['want'] = 'request'
        return self.simple(*a, **kw)

########NEW FILE########
__FILENAME__ = pytest_fixtures
"""
aspen.testing.pytest_fixtures
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import sys

import pytest
from aspen.testing.harness import Harness
from filesystem_tree import FilesystemTree


@pytest.yield_fixture
def fs():
    fs = FilesystemTree()
    yield fs
    fs.remove()


@pytest.yield_fixture
def sys_path_scrubber():
    before = set(sys.path)
    yield
    after = set(sys.path)
    for name in after - before:
        sys.path.remove(name)


@pytest.yield_fixture
def sys_path(fs):
    sys.path.insert(0, fs.root)
    yield fs


@pytest.yield_fixture
def harness(sys_path_scrubber):
    harness = Harness()
    yield harness
    harness.teardown()


@pytest.yield_fixture
def client(harness):
    yield harness.client

########NEW FILE########
__FILENAME__ = typecasting
"""
aspen.typecasting
+++++++++++++++++

Pluggable typecasting of virtual path values

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from aspen import Response


class FailedTypecast(Response):
    def __init__(self, extension):
        body = "Failure to typecast extension '{0}'".format(extension)
        Response.__init__(self, code=404, body=body)

"""
   A typecast dict (like 'defaults' below) is a map of
   suffix -> typecasting function.  The functions must take one unicode
   argument, but may return any value.  If they raise an error, the
   typecasted key (the one without the suffix) will not be set, and
   a FailedTypecast (a specialized 404) will be thrown.
"""

defaults = { 'int': int
           , 'float': float
           }

def apply_typecasters(typecasters, path):
    """Perform the typecasts (in-place!) on the supplied path Mapping.
       Note that the supplied mapping has keys with the typecast extensions
       still attached (and unicode values).  This routine adds keys
       *without* those extensions attached anymore, but with typecast values.
       It also then removes the string-value keys (the ones with the extensions).
    """
    for part in path.keys():
        pieces = part.rsplit('.',1)
        if len(pieces) > 1:
            var, ext = pieces
            if ext in typecasters:
                try:
                    # path is a Mapping not a dict, so:
                    for v in path.all(part):
                        path.add(var, typecasters[ext](v))
                    path.popall(part)
                except:
                    raise FailedTypecast(ext)


########NEW FILE########
__FILENAME__ = utils
"""
aspen.utils
+++++++++++
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import codecs
import datetime
import math
import re

import algorithm


# Register a 'repr' error strategy.
# =================================
# Sometimes we want to echo bytestrings back to a user, and we don't know what
# encoding will work. This error strategy replaces non-decodable bytes with
# their Python representation, so that they are human-visible.
#
# See also:
#   - https://github.com/dcrosta/mongo/commit/e1ac732
#   - http://www.crummy.com/software/BeautifulSoup/bs4/doc/#unicode-dammit

def replace_with_repr(unicode_error):
    offender = unicode_error.object[unicode_error.start:unicode_error.end]
    return (unicode(repr(offender).strip("'").strip('"')), unicode_error.end)

codecs.register_error('repr', replace_with_repr)


def unicode_dammit(s, encoding="UTF-8"):
    """Given a bytestring, return a unicode decoded with `encoding`.

    Any bytes not decodable with UTF-8 will be replaced with their Python
    representation, so you'll get something like u"foo\\xefbar".

    """
    if not isinstance(s, str):
        raise TypeError("I got %s, but I want <type 'str'>." % s.__class__)
    errors = 'repr'
    return s.decode(encoding, errors)


def ascii_dammit(s):
    """Given a bytestring, return a bytestring.

    The returned bytestring will have any non-ASCII bytes replaced with
    their Python representation, so it will be pure ASCII.

    """
    return unicode_dammit(s, encoding="ASCII").encode("ASCII")


# datetime helpers
# ================

def total_seconds(td):
    """Python 2.7 adds a total_seconds method to timedelta objects.

    See http://docs.python.org/library/datetime.html#datetime.timedelta.total_seconds

    This function is taken from https://bitbucket.org/jaraco/jaraco.compat/src/e5806e6c1bcb/py26compat/__init__.py#cl-26

    """
    try:
        result = td.total_seconds()
    except AttributeError:
        result = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6
    return result


class UTC(datetime.tzinfo):
    """UTC - http://docs.python.org/library/datetime.html#tzinfo-objects
    """

    def utcoffset(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return datetime.timedelta(0)

utc = UTC()


def utcnow():
    """Return a tz-aware datetime.datetime.
    """
    # For Python < 3, see http://bugs.python.org/issue5094
    return datetime.datetime.now(tz=utc)


def to_age(dt, fmt_past=None, fmt_future=None):
    """Given a timezone-aware datetime object, return an age string.

        range                                       denomination    example
        ======================================================================
        0-1 second                                 "just a moment"
        1-59 seconds                                seconds         13 seconds
        60 sec - 59 min                             minutes         13 minutes
        60 min - 23 hrs, 59 min                     hours           13 hours
        24 hrs - 13 days, 23 hrs, 59 min            days            13 days
        14 days - 27 days, 23 hrs, 59 min           weeks           3 weeks
        28 days - 12 months, 31 days, 23 hrs, 59 mn months          6 months
        1 year -                                    years           1 year

    We'll go up to years for now.

    Times in the future are indicated by "in {age}" and times already passed
    are indicated by "{age} ago". You can pass in custom format strings as
    fmt_past and fmt_future.

    """
    if dt.tzinfo is None:
        raise ValueError("You passed a naive datetime object to to_age.")


    # Define some helpful constants.
    # ==============================

    sec =   1
    min =  60 * sec
    hr  =  60 * min
    day =  24 * hr
    wk  =   7 * day
    mn  =   4 * wk
    yr  = 365 * day


    # Get the raw age in seconds.
    # ===========================

    now = datetime.datetime.now(dt.tzinfo)
    age = total_seconds(abs(now - dt))


    # Convert it to a string.
    # =======================
    # We start with the coarsest unit and filter to the finest. Pluralization
    # is centralized.

    article = "a"

    if age >= yr:           # years
        amount = age / yr
        unit = 'year'
    elif age >= mn:         # months
        amount = age / mn
        unit = 'month'
    elif age >= (2 * wk):   # weeks
        amount = age / wk
        unit = 'week'
    elif age >= day:        # days
        amount = age / day
        unit = 'day'
    elif age >= hr:         # hours
        amount = age / hr
        unit = 'hour'
        article = "an"
    elif age >= min:        # minutes
        amount = age / min
        unit = 'minute'
    elif age >= 1:          # seconds
        amount = age
        unit = 'second'
    else:
        amount = None
        age = 'just a moment'


    # Pluralize, format, and return.
    # ==============================

    if amount is not None:
        amount = int(math.floor(amount))
        if amount != 1:
            unit += 's'
        if amount < 10:
            amount = ['zero', article, 'two', 'three', 'four', 'five', 'six',
                      'seven', 'eight', 'nine'][amount]
        age = ' '.join([str(amount), unit])

    fmt_past = fmt_past if fmt_past is not None else '%(age)s ago'
    fmt_future = fmt_future if fmt_future is not None else 'in %(age)s'
    fmt = fmt_past if dt < now else fmt_future

    return fmt % dict(age=age)


def to_rfc822(dt):
    """Given a datetime.datetime, return an RFC 822-formatted unicode.

        Sun, 06 Nov 1994 08:49:37 GMT

    According to RFC 1123, day and month names must always be in English. If
    not for that, this code could use strftime(). It can't because strftime()
    honors the locale and could generated non-English names.

    """
    t = dt.utctimetuple()
    return '%s, %02d %s %04d %02d:%02d:%02d GMT' % (
        ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')[t[6]],
        t[2],
        ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
         'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')[t[1] - 1],
        t[0], t[3], t[4], t[5]
    )


# Filters
# =======
# These are decorators for algorithm functions.

def by_lambda(filter_lambda):
    """
    """
    def wrap(function):
        def wrapped_function_by_lambda(*args,**kwargs):
            if filter_lambda():
                return function(*args,**kwargs)
        algorithm._transfer_func_name(wrapped_function_by_lambda, function)
        return wrapped_function_by_lambda
    return wrap


def by_regex(regex_tuples, default=True):
    """Only call function if

    regex_tuples is a list of (regex, filter?) where if the regex matches the
    requested URI, then the flow is applied or not based on if filter? is True
    or False.

    For example:

        from aspen.flows.filter import by_regex

        @by_regex( ( ("/secret/agenda", True), ( "/secret.*", False ) ) )
        def use_public_formatting(request):
            ...

    would call the 'use_public_formatting' flow step only on /secret/agenda
    and any other URLs not starting with /secret.

    """
    regex_res = [ (re.compile(regex), disposition) \
                           for regex, disposition in regex_tuples.iteritems() ]
    def filter_function(function):
        def function_filter(request, *args):
            for regex, disposition in regex_res:
                if regex.matches(request.line.uri):
                    if disposition:
                        return function(*args)
            if default:
                return function(*args)
        algorithm._transfer_func_name(function_filter, function)
        return function_filter
    return filter_function


def by_dict(truthdict, default=True):
    """Filter for hooks

    truthdict is a mapping of URI -> filter? where if the requested URI is a
    key in the dict, then the hook is applied based on the filter? value.

    """
    def filter_function(function):
        def function_filter(request, *args):
            do_hook = truthdict.get(request.line.uri, default)
            if do_hook:
                return function(*args)
        algorithm._transfer_func_name(function_filter, function)
        return function_filter
    return filter_function


# Soft type checking
# ==================

def typecheck(*checks):
    """Assert that arguments are of a certain type.

    Checks is a flattened sequence of objects and target types, like this:

        ( {'foo': 2}, dict
        , [1,2,3], list
        , 4, int
        , True, bool
        , 'foo', (basestring, None)
         )

    The target type can be a single type or a tuple of types. None is
    special-cased (you can specify None and it will be interpreted as
    type(None)).

    >>> typecheck()
    >>> typecheck('foo')
    Traceback (most recent call last):
        ...
    AssertionError: typecheck takes an even number of arguments.
    >>> typecheck({'foo': 2}, dict)
    >>> typecheck([1,2,3], list)
    >>> typecheck(4, int)
    >>> typecheck(True, bool)
    >>> typecheck('foo', (str, None))
    >>> typecheck(None, None)
    >>> typecheck(None, type(None))
    >>> typecheck('foo', unicode)
    Traceback (most recent call last):
        ...
    TypeError: Check #1: 'foo' is of type str, but unicode was expected.
    >>> typecheck('foo', (basestring, None))
    Traceback (most recent call last):
        ...
    TypeError: Check #1: 'foo' is of type str, not one of: basestring, NoneType.
    >>> class Foo(object):
    ...   def __repr__(self):
    ...     return "<Foo>"
    ...
    >>> typecheck(Foo(), dict)
    Traceback (most recent call last):
        ...
    TypeError: Check #1: <Foo> is of type __main__.Foo, but dict was expected.
    >>> class Bar:
    ...   def __repr__(self):
    ...     return "<Bar>"
    ...
    >>> typecheck(Bar(), dict)
    Traceback (most recent call last):
        ...
    TypeError: Check #1: <Bar> is of type instance, but dict was expected.
    >>> typecheck('foo', str, 'bar', unicode)
    Traceback (most recent call last):
        ...
    TypeError: Check #2: 'bar' is of type str, but unicode was expected.

    """
    assert type(checks) is tuple, checks
    assert len(checks) % 2 == 0, "typecheck takes an even number of arguments."

    def nice(t):
        found = re.findall("<type '(.+)'>", str(t))
        if found:
            out = found[0]
        else:
            found = re.findall("<class '(.+)'>", str(t))
            if found:
                out = found[0]
            else:
                out = str(t)
        return out

    checks = list(checks)
    checks.reverse()

    nchecks = 0
    while checks:
        nchecks += 1
        obj = checks.pop()
        expected = checks.pop()
        actual = type(obj)

        if isinstance(expected, tuple):
            expected = list(expected)
        elif not isinstance(expected, list):
            expected = [expected]

        for i, t in enumerate(expected):
            if t is None:
                expected[i] = type(t)

        if actual not in expected:
            msg = "Check #%d: %s is of type %s, "
            msg %= (nchecks, repr(obj), nice(actual))
            if len(expected) > 1:
                niced = [nice(t) for t in expected]
                msg += ("not one of: %s." % ', '.join(niced))
            else:
                msg += "but %s was expected." % nice(expected[0])
            raise TypeError(msg)


# Hostname canonicalization
# =========================

def Canonizer(expected):
    """Takes a netloc such as http://localhost:8080 (no path part).
    """

    def noop(request):
        pass

    def canonize(request):
        """Enforce a certain network location.
        """

        scheme = request.headers.get('X-Forwarded-Proto', 'http') # XXX Heroku
        host = request.headers['Host']  # will 400 if missing

        actual = scheme + "://" + host

        if actual != expected:
            uri = expected
            if request.line.method in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
                # Redirect to a particular path for idempotent methods.
                uri += request.line.uri.path.raw
                if request.line.uri.querystring:
                    uri += '?' + request.line.uri.querystring.raw
            else:
                # For non-idempotent methods, redirect to homepage.
                uri += '/'
            request.redirect(uri, permanent=True)

    return expected and canonize or noop


if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = website
"""
aspen.website
+++++++++++++
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import datetime
import os

from algorithm import Algorithm
from aspen.configuration import Configurable
from aspen.utils import to_rfc822, utc

# 2006-11-17 was the first release of aspen - v0.3
THE_PAST = to_rfc822(datetime.datetime(2006, 11, 17, tzinfo=utc))


class Website(Configurable):
    """Represent a website.

    This object holds configuration information, and also knows how to start
    and stop a server, *and* how to handle HTTP requests (per WSGI). It is
    available to user-developers inside of their simplates and hooks.

    """

    def __init__(self, argv=None, server_algorithm=None):
        """Takes an argv list, without the initial executable name.
        """
        self.server_algorithm = server_algorithm
        self.algorithm = Algorithm.from_dotted_name('aspen.algorithms.website')
        self.configure(argv)


    def __call__(self, environ, start_response):
        # back-compatibility for network engines
        return self.wsgi_app(environ, start_response)


    def wsgi_app(self, environ, start_response):
        """WSGI interface.

        Wrap this method (instead of the website object itself) when you want
        to use WSGI middleware::

            website = Website()
            website.wsgi = WSGIMiddleware(website.wsgi)

        """
        wsgi = self.respond(environ)['response']
        return wsgi(environ, start_response)


    def respond(self, environ, raise_immediately=None, return_after=None):
        """Given a WSGI environ, return a state dict.
        """
        return self.algorithm.run( website=self
                                 , environ=environ
                                 , _raise_immediately=raise_immediately
                                 , _return_after=return_after
                                  )


    # File Resolution
    # ===============

    def find_ours(self, filename):
        """Given a filename, return the filepath to aspen's internal version
	   of that filename.  No existence checking is done, this just abstracts
	   away the __file__ reference nastiness.
        """
        return os.path.join(os.path.dirname(__file__), 'www', filename)

    def ours_or_theirs(self, filename):
        """Given a filename, return a filepath or None.
        """
        if self.project_root is not None:
            theirs = os.path.join(self.project_root, filename)
            if os.path.isfile(theirs):
                return theirs

        ours = self.find_ours(filename)
        if os.path.isfile(ours):
            return ours

        return None

########NEW FILE########
__FILENAME__ = wsgi
"""
aspen.wsgi
++++++++++

Provide a WSGI callable.

It would be a little nicer if this was at aspen:wsgi instead of
aspen.wsgi:website, but then Website would be instantiated even if we don't
want it to be. Here, it's only instantiated when someone passes this to
gunicorn, spawning, etc.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from aspen.website import Website

website = Website([])

########NEW FILE########
__FILENAME__ = __main__
"""
python -m aspen
===============

Aspen ships with a server (wsgiref.simple_server) that is
suitable for development and testing.  It can be invoked via:

    python -m aspen

though even for development you'll likely want to specify a
project root, so a more likely incantation is:

    ASPEN_PROJECT_ROOT=/path/to/wherever python -m aspen

For production deployment, you should probably deploy using
a higher performance WSGI server like Gunicorn, uwsgi, Spawning,
or the like.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from aspen import log_dammit
from aspen.website import Website
from wsgiref.simple_server import make_server


if __name__ == '__main__':
    website = Website()
    server = make_server('0.0.0.0', 8080, website)
    log_dammit("Greetings, program! Welcome to port 8080.")
    server.serve_forever()

########NEW FILE########
__FILENAME__ = build
import os
import sys
import os.path
from optparse import make_option
from fabricate import main, run, shell, autoclean

# Core Executables
# ================
# We satisfy dependencies using local tarballs, to ensure that we can build
# without a network connection. They're kept in our repo in ./vendor.

ASPEN_DEPS = [
    'mimeparse>=0.1.3',
    'first>=2.0.1',
    'algorithm>=1.0.0',
    'filesystem_tree>=1.0.1',
    'dependency_injection>=1.1.0',
    ]

TEST_DEPS = [
    'coverage>=3.7.1',
    'cov-core>=1.7',
    'py>=1.4.20',
    'pytest>=2.5.2',
    'pytest-cov>=1.6',
    ]

INSTALL_DIR = './vendor/install'
TEST_DIR = './vendor/test'
BOOTSTRAP_DIR = './vendor/bootstrap'

ENV_ARGS = [
    './vendor/virtualenv-1.11.2.py',
    '--prompt=[aspen]',
    '--extra-search-dir=' + BOOTSTRAP_DIR,
    ]


def _virt(cmd, envdir='env'):
    if os.name == "nt":
        return os.path.join(envdir, 'Scripts', cmd+ '.exe')
    else:
        return os.path.join(envdir, 'bin', cmd)


def _virt_version():
    _env()
    v = shell(_virt('python'), '-c',
              'import sys; print(sys.version_info[:2])')
    return eval(v)


def _env():
    if os.path.exists('env'):
        return
    args = [main.options.python] + ENV_ARGS + ['env']
    run(*args)


def aspen():
    _env()
    v = shell(_virt('python'), '-c', 'import aspen; print("found")', ignore_status=True)
    if "found" in v:
        return
    for dep in ASPEN_DEPS:
        run(_virt('pip'), 'install', '--no-index',
            '--find-links=' + INSTALL_DIR, dep)
    run(_virt('python'), 'setup.py', 'develop')


def dev():
    _env()
    # pytest will need argparse if its running under 2.6
    if _virt_version() < (2, 7):
        TEST_DEPS.insert(0, 'argparse')
    for dep in TEST_DEPS:
        run(_virt('pip'), 'install', '--no-index',
            '--find-links=' + TEST_DIR, dep)


def clean_env():
    shell('rm', '-rf', 'env')


def clean():
    autoclean()
    shell('find', '.', '-name', '*.pyc', '-delete')
    clean_env()
    clean_smoke()
    clean_jenv()
    clean_test()
    clean_build()


# Doc / Smoke
# ===========

smoke_dir = 'smoke-test'


def docs():
    aspen()
    run(_virt('pip'), 'install', 'aspen-tornado')
    run(_virt('pip'), 'install', 'pygments')
    shell(_virt('python'), '-m', 'aspen', '-wdoc', '-pdoc/.aspen', silent=False)


def smoke():
    aspen()
    run('mkdir', smoke_dir)
    open(os.path.join(smoke_dir, "index.html"), "w").write("Greetings, program!")
    run(_virt('python'), '-m', 'aspen', '-w', smoke_dir)


def clean_smoke():
    shell('rm', '-rf', smoke_dir)


# Testing
# =======

def test():
    aspen()
    dev()
    shell(_virt('py.test'), 'tests/', ignore_status=True, silent=False)


def pylint():
    _env()
    run(_virt('pip'), 'install', 'pylint')
    run(_virt('pylint'), '--rcfile=.pylintrc',
        'aspen', '|', 'tee', 'pylint.out', shell=True, ignore_status=True)


def analyse():
    pylint()
    dev()
    aspen()
    run(_virt('py.test'),
        '--junitxml=testresults.xml',
        '--cov-report', 'term',
        '--cov-report', 'xml',
        '--cov', 'aspen',
        'tests/',
        ignore_status=False)
    print('done!')


def clean_test():
    clean_env()
    shell('rm', '-f', '.coverage', 'coverage.xml', 'testresults.xml', 'pylint.out')

# Build
# =====


def build():
    run(main.options.python, 'setup.py', 'bdist_egg')


def wheel():
    run(main.options.python, 'setup.py', 'bdist_wheel')


def clean_build():
    run('python', 'setup.py', 'clean', '-a')
    run('rm', '-rf', 'dist')

# Jython
# ======
JYTHON_URL = "http://search.maven.org/remotecontent?filepath=org/python/jython-installer/2.7-b1/jython-installer-2.7-b1.jar"

def _jython_home():
    if not os.path.exists('jython_home'):
        local_jython = os.path.join('vendor', 'jython-installer.jar')
        run('wget', JYTHON_URL, '-qO', local_jython)
        run('java', '-jar', local_jython, '-s', '-d', 'jython_home')

def _jenv():
    _jython_home()
    jenv = dict(os.environ)
    jenv['PATH'] = os.path.join('.', 'jython_home', 'bin') + ':' + jenv['PATH']
    args = [ 'jython' ] + ENV_ARGS + [ '--python=jython', 'jenv' ]
    run(*args, env=jenv)

def clean_jenv():
    shell('find', '.', '-name', '*.class', '-delete')
    shell('rm', '-rf', 'jenv', 'vendor/jython-installer.jar', 'jython_home')

def jython_test():
    _jenv()
    for dep in ASPEN_DEPS + TEST_DEPS:
        run(_virt('pip', 'jenv'), 'install', os.path.join('vendor', dep))
    run(_virt('jython', 'jenv'), 'setup.py', 'develop')
    run(_virt('jython', 'jenv'), _virt('py.test', 'jenv'),
            '--junitxml=jython-testresults.xml', 'tests',
            '--cov-report', 'term',
            '--cov-report', 'xml',
            '--cov', 'aspen',
            ignore_status=True)

def clean_jtest():
    shell('find', '.', '-name', '*.class', '-delete')
    shell('rm', '-rf', 'jython-testresults.xml')

def show_targets():
    print("""Valid targets:

    show_targets (default) - this
    build - build an aspen egg
    aspen - set up a test aspen environment in env/
    dev - set up an environment able to run tests in env/
    docs - run the doc server
    smoke - run a smoke test
    test - run the unit tests
    analyse - run the unit tests with code coverage enabled
    pylint - run pylint on the source
    clean - remove all build artifacts
    clean_{env,jenv,smoke,test,jtest} - clean some build artifacts

    jython_test - install jython and run unit tests with code coverage.
                  (requires java)
    """)
    sys.exit()

extra_options = [
        make_option('--python', action="store", dest="python", default="python"),
        ]

main( extra_options=extra_options
    , default='show_targets'
    , ignoreprefix="python"  # workaround for gh190
     )

########NEW FILE########
__FILENAME__ = aspen_io
"""Helpers for the http://aspen.io/ website.
"""
from os.path import dirname


opts = {} # populate this in configure-aspen.py


def add_stuff_to_request_context(request):

    # Define some closures for generating image markup.
    # =================================================

    def translate(src):
        if src[0] != '/':
            rel = dirname(request.fs)[len(request.website.www_root):]
            src = '/'.join([rel, src])
        src = opts['base'] + src
        return src

    def img(src):
        src = translate(src)
        html = '<img src="%s" />' % src
        return html

    def screenshot(short, imgtype='png', href=''):
        """Given foo, go with foo.small.png and foo.png.
        """
        small = img(short + '.small.' + imgtype)
        if not href:
            href = translate(short + '.' + imgtype)
        html = ('<a title="Click for full size" href="%s"'
                'class="screencap">%s</a>')
        return html % (href, small)


    # Make these available within simplates.
    # ======================================

    request.context['img'] = img
    request.context['screenshot'] = screenshot
    request.context['translate'] = translate
    request.context['version'] = opts['version']
    request.context['homepage'] = False
    request.context['show_ga'] = opts['show_ga']

########NEW FILE########
__FILENAME__ = configure-aspen
import os
import os.path
from aspen.configuration import parse
from aspen_io import opts, add_stuff_to_request_context

opts['show_ga'] = parse.yes_no(os.environ.get( 'ASPEN_IO_SHOW_GA'
                                             , 'no'
                                              ).decode('US-ASCII'))
opts['base'] = ''

# this is a dirty nasty hack. We should store the version in the aspen module somewhere
opts['version'] = open(os.path.join(website.www_root,'..','version.txt')).read()[:-len('-dev')]

# no idea why this doesn't work
website.renderer_default = 'tornado'
open('/tmp/debugout','a').write('doccnf:' + website.renderer_default + '\n')

website.algorithm.insert_after('parse_environ_into_request', add_stuff_to_request_context)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Aspen documentation build configuration file, created by
# sphinx-quickstart on Mon Feb 24 15:00:43 2014.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.intersphinx', 'sphinx.ext.todo', 'sphinx.ext.coverage', 'sphinx.ext.ifconfig']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Aspen'
copyright = u'2014, Chad Whitacre, Paul Jimenez, and others'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.29'
# The full version, including alpha/beta/rc tags.
release = '0.29'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = []

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Aspendoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Aspen.tex', u'Aspen Documentation',
   u'Chad Whitacre, Paul Jimenez, and others', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'aspen', u'Aspen Documentation',
     [u'Chad Whitacre, Paul Jimenez, and others'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Aspen', u'Aspen Documentation',
   u'Chad Whitacre, Paul Jimenez, and others', 'Aspen', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = fabricate
#!/usr/bin/env python

"""Build tool that finds dependencies automatically for any language.

fabricate is a build tool that finds dependencies automatically for any
language. It's small and just works. No hidden stuff behind your back. It was
inspired by Bill McCloskey's make replacement, memoize, but fabricate works on
Windows as well as Linux.

Read more about how to use it and how it works on the project page:
    http://code.google.com/p/fabricate/

Like memoize, fabricate is released under a "New BSD license". fabricate is
copyright (c) 2009 Brush Technology. Full text of the license is here:
    http://code.google.com/p/fabricate/wiki/License

To get help on fabricate functions:
    from fabricate import *
    help(function)

"""

from __future__ import with_statement

# fabricate version number
__version__ = '1.26'

# if version of .deps file has changed, we know to not use it
deps_version = 2

import atexit
import optparse
import os
import platform
import re
import shlex
import stat
import subprocess
import sys
import tempfile
import time
import threading # NB uses old camelCase names for backward compatibility
# multiprocessing module only exists on Python >= 2.6
try:
    import multiprocessing
except ImportError:
    class MultiprocessingModule(object):
        def __getattr__(self, name):
            raise NotImplementedError("multiprocessing module not available, can't do parallel builds")
    multiprocessing = MultiprocessingModule()

# so you can do "from fabricate import *" to simplify your build script
__all__ = ['setup', 'run', 'autoclean', 'main', 'shell', 'fabricate_version',
           'memoize', 'outofdate', 'parse_options', 'after',
           'ExecutionError', 'md5_hasher', 'mtime_hasher',
           'Runner', 'AtimesRunner', 'StraceRunner', 'AlwaysRunner',
           'SmartRunner', 'Builder']

import textwrap

__doc__ += "Exported functions are:\n" + '  ' + '\n  '.join(textwrap.wrap(', '.join(__all__), 80))



FAT_atime_resolution = 24*60*60     # resolution on FAT filesystems (seconds)
FAT_mtime_resolution = 2

# NTFS resolution is < 1 ms
# We assume this is considerably more than time to run a new process

NTFS_atime_resolution = 0.0002048   # resolution on NTFS filesystems (seconds)
NTFS_mtime_resolution = 0.0002048   #  is actually 0.1us but python's can be
                                    #  as low as 204.8us due to poor
                                    #  float precision when storing numbers
                                    #  as big as NTFS file times can be
                                    #  (float has 52-bit precision and NTFS
                                    #  FILETIME has 63-bit precision, so
                                    #  we've lost 11 bits = 2048)

# So we can use md5func in old and new versions of Python without warnings
try:
    import hashlib
    md5func = hashlib.md5
except ImportError:
    import md5
    md5func = md5.new

# Use json, or pickle on older Python versions if simplejson not installed
try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        import cPickle
        # needed to ignore the indent= argument for pickle's dump()
        class PickleJson:
            def load(self, f):
                return cPickle.load(f)
            def dump(self, obj, f, indent=None, sort_keys=None):
                return cPickle.dump(obj, f)
        json = PickleJson()

def printerr(message):
    """ Print given message to stderr with a line feed. """
    print >>sys.stderr, message

class PathError(Exception):
    pass

class ExecutionError(Exception):
    """ Raised by shell() and run() if command returns non-zero exit code. """
    pass

def args_to_list(args):
    """ Return a flat list of the given arguments for shell(). """
    arglist = []
    for arg in args:
        if arg is None:
            continue
        if hasattr(arg, '__iter__'):
            arglist.extend(args_to_list(arg))
        else:
            if not isinstance(arg, basestring):
                arg = str(arg)
            arglist.append(arg)
    return arglist

def shell(*args, **kwargs):
    r""" Run a command: program name is given in first arg and command line
        arguments in the rest of the args. Iterables (lists and tuples) in args
        are recursively converted to separate arguments, non-string types are
        converted with str(arg), and None is ignored. For example:

        >>> def tail(input, n=3, flags=None):
        >>>     args = ['-n', n]
        >>>     return shell('tail', args, flags, input=input)
        >>> tail('a\nb\nc\nd\ne\n')
        'c\nd\ne\n'
        >>> tail('a\nb\nc\nd\ne\n', 2, ['-v'])
        '==> standard input <==\nd\ne\n'

        Keyword arguments kwargs are interpreted as follows:

        "input" is a string to pass standard input into the process (or the
            default of None to use parent's stdin, eg: the keyboard)
        "silent" is True (default) to return process's standard output as a
            string, or False to print it as it comes out
        "shell" set to True will run the command via the shell (/bin/sh or
            COMSPEC) instead of running the command directly (the default)
        "ignore_status" set to True means ignore command status code -- i.e.,
            don't raise an ExecutionError on nonzero status code
        Any other kwargs are passed directly to subprocess.Popen
        Raises ExecutionError(message, output, status) if the command returns
        a non-zero status code. """
    try:
        return _shell(args, **kwargs)
    finally:
        sys.stderr.flush()
        sys.stdout.flush()

def _shell(args, input=None, silent=True, shell=False, ignore_status=False, **kwargs):
    if input:
        stdin = subprocess.PIPE
    else:
        stdin = None
    if silent:
        stdout = subprocess.PIPE
    else:
        stdout = None
    arglist = args_to_list(args)
    if not arglist:
        raise TypeError('shell() takes at least 1 argument (0 given)')
    if shell:
        # handle subprocess.Popen quirk where subsequent args are passed
        # to bash instead of to our command
        command = subprocess.list2cmdline(arglist)
    else:
        command = arglist
    try:
        proc = subprocess.Popen(command, stdin=stdin, stdout=stdout,
                                stderr=subprocess.STDOUT, shell=shell, **kwargs)
    except OSError, e:
        # Work around the problem that Windows Popen doesn't say what file it couldn't find
        if platform.system() == 'Windows' and e.errno == 2 and e.filename is None:
            e.filename = arglist[0]
        raise e
    output, stderr = proc.communicate(input)
    status = proc.wait()
    if status and not ignore_status:
        raise ExecutionError('%r exited with status %d'
                             % (os.path.basename(arglist[0]), status),
                             output, status)
    if silent:
        return output

def md5_hasher(filename):
    """ Return MD5 hash of given filename if it is a regular file or 
        a symlink with a hashable target, or the MD5 hash of the 
        target_filename if it is a symlink without a hashable target,
        or the MD5 hash of the filename if it is a directory, or None 
        if file doesn't exist. 
        
        Note: Pyhton versions before 3.2 do not support os.readlink on
        Windows so symlinks without a hashable target fall back to
        a hash of the filename if the symlink target is a directory, 
        or None if the symlink is broken"""
    try:
        f = open(filename, 'rb')
        try:
            return md5func(f.read()).hexdigest()
        finally:
            f.close()
    except IOError:
        if hasattr(os, 'readlink') and os.path.islink(filename):
            return md5func(os.readlink(filename)).hexdigest()
        elif os.path.isdir(filename):
            return md5func(filename).hexdigest()
        return None

def mtime_hasher(filename):
    """ Return modification time of file, or None if file doesn't exist. """
    try:
        st = os.stat(filename)
        return repr(st.st_mtime)
    except (IOError, OSError):
        return None

class RunnerUnsupportedException(Exception):
    """ Exception raise by Runner constructor if it is not supported
        on the current platform."""
    pass

class Runner(object):
    def __call__(self, *args, **kwargs):
        """ Run command and return (dependencies, outputs), where
            dependencies is a list of the filenames of files that the
            command depended on, and output is a list of the filenames
            of files that the command modified. The input is passed
            to shell()"""
        raise NotImplementedError("Runner subclass called but subclass didn't define __call__")

    def actual_runner(self):
        """ Return the actual runner object (overriden in SmartRunner). """
        return self
        
    def ignore(self, name):
        return self._builder.ignore.search(name)

class AtimesRunner(Runner):
    def __init__(self, builder):
        self._builder = builder
        self.atimes = AtimesRunner.has_atimes(self._builder.dirs)
        if self.atimes == 0:
            raise RunnerUnsupportedException(
                'atimes are not supported on this platform')

    @staticmethod
    def file_has_atimes(filename):
        """ Return whether the given filesystem supports access time updates for
            this file. Return:
              - 0 if no a/mtimes not updated
              - 1 if the atime resolution is at least one day and
                the mtime resolution at least 2 seconds (as on FAT filesystems)
              - 2 if the atime and mtime resolutions are both < ms
                (NTFS filesystem has 100 ns resolution). """

        def access_file(filename):
            """ Access (read a byte from) file to try to update its access time. """
            f = open(filename)
            f.read(1)
            f.close()

        initial = os.stat(filename)
        os.utime(filename, (
            initial.st_atime-FAT_atime_resolution,
            initial.st_mtime-FAT_mtime_resolution))

        adjusted = os.stat(filename)
        access_file(filename)
        after = os.stat(filename)

        # Check that a/mtimes actually moved back by at least resolution and
        #  updated by a file access.
        #  add NTFS_atime_resolution to account for float resolution factors
        #  Comment on resolution/2 in atimes_runner()
        if initial.st_atime-adjusted.st_atime > FAT_atime_resolution+NTFS_atime_resolution or \
           initial.st_mtime-adjusted.st_mtime > FAT_mtime_resolution+NTFS_atime_resolution or \
           initial.st_atime==adjusted.st_atime or \
           initial.st_mtime==adjusted.st_mtime or \
           not after.st_atime-FAT_atime_resolution/2 > adjusted.st_atime:
            return 0

        os.utime(filename, (
            initial.st_atime-NTFS_atime_resolution,
            initial.st_mtime-NTFS_mtime_resolution))
        adjusted = os.stat(filename)

        # Check that a/mtimes actually moved back by at least resolution
        # Note: != comparison here fails due to float rounding error
        #  double NTFS_atime_resolution to account for float resolution factors
        if initial.st_atime-adjusted.st_atime > NTFS_atime_resolution*2 or \
           initial.st_mtime-adjusted.st_mtime > NTFS_mtime_resolution*2 or \
           initial.st_atime==adjusted.st_atime or \
           initial.st_mtime==adjusted.st_mtime:
            return 1

        return 2

    @staticmethod
    def exists(path):
        if not os.path.exists(path):
            # Note: in linux, error may not occur: strace runner doesn't check
            raise PathError("build dirs specified a non-existant path '%s'" % path)

    @staticmethod
    def has_atimes(paths):
        """ Return whether a file created in each path supports atimes and mtimes.
            Return value is the same as used by file_has_atimes
            Note: for speed, this only tests files created at the top directory
            of each path. A safe assumption in most build environments.
            In the unusual case that any sub-directories are mounted
            on alternate file systems that don't support atimes, the build may
            fail to identify a dependency """

        atimes = 2                  # start by assuming we have best atimes
        for path in paths:
            AtimesRunner.exists(path)
            handle, filename = tempfile.mkstemp(dir=path)
            try:
                try:
                    f = os.fdopen(handle, 'wb')
                except:
                    os.close(handle)
                    raise
                try:
                    f.write('x')    # need a byte in the file for access test
                finally:
                    f.close()
                atimes = min(atimes, AtimesRunner.file_has_atimes(filename))
            finally:
                os.remove(filename)
        return atimes

    def _file_times(self, path, depth):
        """ Helper function for file_times().
            Return a dict of file times, recursing directories that don't
            start with self._builder.ignoreprefix """

        AtimesRunner.exists(path)
        names = os.listdir(path)
        times = {}
        ignoreprefix = self._builder.ignoreprefix
        for name in names:
            if ignoreprefix and name.startswith(ignoreprefix):
                continue
            if path == '.':
                fullname = name
            else:
                fullname = os.path.join(path, name)
            st = os.stat(fullname)
            if stat.S_ISDIR(st.st_mode):
                if depth > 1:
                    times.update(self._file_times(fullname, depth-1))
            elif stat.S_ISREG(st.st_mode):
                times[fullname] = st.st_atime, st.st_mtime
        return times

    def file_times(self):
        """ Return a dict of "filepath: (atime, mtime)" entries for each file
            in self._builder.dirs. "filepath" is the absolute path, "atime" is
            the access time, "mtime" the modification time.
            Recurse directories that don't start with
            self._builder.ignoreprefix and have depth less than
            self._builder.dirdepth. """

        times = {}
        for path in self._builder.dirs:
            times.update(self._file_times(path, self._builder.dirdepth))
        return times

    def _utime(self, filename, atime, mtime):
        """ Call os.utime but ignore permission errors """
        try:
            os.utime(filename, (atime, mtime))
        except OSError, e:
            # ignore permission errors -- we can't build with files
            # that we can't access anyway
            if e.errno != 1:
                raise

    def _age_atimes(self, filetimes):
        """ Age files' atimes and mtimes to be at least FAT_xx_resolution old.
            Only adjust if the given filetimes dict says it isn't that old,
            and return a new dict of filetimes with the ages adjusted. """
        adjusted = {}
        now = time.time()
        for filename, entry in filetimes.iteritems():
            if now-entry[0] < FAT_atime_resolution or now-entry[1] < FAT_mtime_resolution:
                entry = entry[0] - FAT_atime_resolution, entry[1] - FAT_mtime_resolution
                self._utime(filename, entry[0], entry[1])
            adjusted[filename] = entry
        return adjusted

    def __call__(self, *args, **kwargs):
        """ Run command and return its dependencies and outputs, using before
            and after access times to determine dependencies. """

        # For Python pre-2.5, ensure os.stat() returns float atimes
        old_stat_float = os.stat_float_times()
        os.stat_float_times(True)

        originals = self.file_times()
        if self.atimes == 2:
            befores = originals
            atime_resolution = 0
            mtime_resolution = 0
        else:
            befores = self._age_atimes(originals)
            atime_resolution = FAT_atime_resolution
            mtime_resolution = FAT_mtime_resolution
        shell_keywords = dict(silent=False)
        shell_keywords.update(kwargs)
        shell(*args, **shell_keywords)
        afters = self.file_times()
        deps = []
        outputs = []
        for name in afters:
            if name in befores:
                # if file exists before+after && mtime changed, add to outputs
                # Note: Can't just check that atimes > than we think they were
                #       before because os might have rounded them to a later
                #       date than what we think we set them to in befores.
                #       So we make sure they're > by at least 1/2 the
                #       resolution.  This will work for anything with a
                #       resolution better than FAT.
                if afters[name][1]-mtime_resolution/2 > befores[name][1]:
                    if not self.ignore(name):
                        outputs.append(name)
                elif afters[name][0]-atime_resolution/2 > befores[name][0]:
                    # otherwise add to deps if atime changed
                    if not self.ignore(name):
                        deps.append(name)
            else:
                # file created (in afters but not befores), add as output
                if not self.ignore(name):
                    outputs.append(name)

        if self.atimes < 2:
            # Restore atimes of files we didn't access: not for any functional
            # reason -- it's just to preserve the access time for the user's info
            for name in deps:
                originals.pop(name)
            for name in originals:
                original = originals[name]
                if original != afters.get(name, None):
                    self._utime(name, original[0], original[1])

        os.stat_float_times(old_stat_float)  # restore stat_float_times value
        return deps, outputs

class StraceProcess(object):
    def __init__(self, cwd='.', delayed=False):
        self.cwd = cwd
        self.deps = set()
        self.outputs = set()
        self.delayed = delayed
        self.delayed_lines = []

    def add_dep(self, dep):
        self.deps.add(dep)

    def add_output(self, output):
        self.outputs.add(output)

    def add_delayed_line(self, line):
        self.delayed_lines.append(line)
        
    def __str__(self):
        return '<StraceProcess cwd=%s deps=%s outputs=%s>' % \
               (self.cwd, self.deps, self.outputs)

def _call_strace(self, *args, **kwargs):
    """ Top level function call for Strace that can be run in parallel """
    return self(*args, **kwargs)

class StraceRunner(Runner):
    keep_temps = False

    def __init__(self, builder, build_dir=None):
        self.strace_system_calls = StraceRunner.get_strace_system_calls()
        if self.strace_system_calls is None:
            raise RunnerUnsupportedException('strace is not available')
        self._builder = builder
        self.temp_count = 0
        self.build_dir = os.path.abspath(build_dir or os.getcwd())

    @staticmethod
    def get_strace_system_calls():
        """ Return None if this system doesn't have strace, otherwise
            return a comma seperated list of system calls supported by strace. """
        if platform.system() == 'Windows':
            # even if windows has strace, it's probably a dodgy cygwin one
            return None
        possible_system_calls = ['open','stat', 'stat64', 'lstat', 'lstat64',
            'execve','exit_group','chdir','mkdir','rename','clone','vfork',
            'fork','symlink','creat']
        valid_system_calls = []
        try:
            # check strace is installed and if it supports each type of call
            for system_call in possible_system_calls:
                proc = subprocess.Popen(['strace', '-e', 'trace=' + system_call], stderr=subprocess.PIPE)
                stdout, stderr = proc.communicate()
                proc.wait()
                if 'invalid system call' not in stderr:
                   valid_system_calls.append(system_call)
        except OSError:
            return None
        return ','.join(valid_system_calls)

    # Regular expressions for parsing of strace log
    _open_re       = re.compile(r'(?P<pid>\d+)\s+open\("(?P<name>[^"]*)", (?P<mode>[^,)]*)')
    _stat_re       = re.compile(r'(?P<pid>\d+)\s+l?stat(?:64)?\("(?P<name>[^"]*)", .*') # stat,lstat,stat64,lstat64
    _execve_re     = re.compile(r'(?P<pid>\d+)\s+execve\("(?P<name>[^"]*)", .*')
    _creat_re      = re.compile(r'(?P<pid>\d+)\s+creat\("(?P<name>[^"]*)", .*')
    _mkdir_re      = re.compile(r'(?P<pid>\d+)\s+mkdir\("(?P<name>[^"]*)", .*\)\s*=\s(?P<result>-?[0-9]*).*')
    _rename_re     = re.compile(r'(?P<pid>\d+)\s+rename\("[^"]*", "(?P<name>[^"]*)"\)')
    _symlink_re    = re.compile(r'(?P<pid>\d+)\s+symlink\("[^"]*", "(?P<name>[^"]*)"\)')
    _kill_re       = re.compile(r'(?P<pid>\d+)\s+killed by.*')
    _chdir_re      = re.compile(r'(?P<pid>\d+)\s+chdir\("(?P<cwd>[^"]*)"\)')
    _exit_group_re = re.compile(r'(?P<pid>\d+)\s+exit_group\((?P<status>.*)\).*')
    _clone_re      = re.compile(r'(?P<pid_clone>\d+)\s+(clone|fork|vfork)\(.*\)\s*=\s*(?P<pid>\d*)')

    # Regular expressions for detecting interrupted lines in strace log
    # 3618  clone( <unfinished ...>
    # 3618  <... clone resumed> child_stack=0, flags=CLONE, child_tidptr=0x7f83deffa780) = 3622
    _unfinished_start_re = re.compile(r'(?P<pid>\d+)(?P<body>.*)<unfinished ...>$')
    _unfinished_end_re   = re.compile(r'(?P<pid>\d+)\s+\<\.\.\..*\>(?P<body>.*)')

    def _do_strace(self, args, kwargs, outfile, outname):
        """ Run strace on given command args/kwargs, sending output to file.
            Return (status code, list of dependencies, list of outputs). """
        shell_keywords = dict(silent=False)
        shell_keywords.update(kwargs)
        try:
            shell('strace', '-fo', outname, '-e',
                  'trace=' + self.strace_system_calls,
                  args, **shell_keywords)
        except ExecutionError, e:
            # if strace failed to run, re-throw the exception
            # we can tell this happend if the file is empty
            outfile.seek(0, os.SEEK_END)
            if outfile.tell() is 0:
                raise e
            else:
                # reset the file postion for reading
                outfile.seek(0)
			
        self.status = 0
        processes  = {}  # dictionary of processes (key = pid)
        unfinished = {}  # list of interrupted entries in strace log
        for line in outfile:
           self._match_line(line, processes, unfinished)
 
        # collect outputs and dependencies from all processes
        deps = set()
        outputs = set()
        for pid, process in processes.items():
            deps = deps.union(process.deps)
            outputs = outputs.union(process.outputs)

        return self.status, list(deps), list(outputs)
        
    def _match_line(self, line, processes, unfinished):
        # look for split lines
        unfinished_start_match = self._unfinished_start_re.match(line)
        unfinished_end_match = self._unfinished_end_re.match(line)
        if unfinished_start_match:
            pid = unfinished_start_match.group('pid')
            body = unfinished_start_match.group('body')
            unfinished[pid] = pid + ' ' + body
            return
        elif unfinished_end_match:
            pid = unfinished_end_match.group('pid')
            body = unfinished_end_match.group('body')
            line = unfinished[pid] + body
            del unfinished[pid]

        is_output = False
        open_match = self._open_re.match(line)
        stat_match = self._stat_re.match(line)
        execve_match = self._execve_re.match(line)
        creat_match = self._creat_re.match(line)
        mkdir_match = self._mkdir_re.match(line)
        symlink_match = self._symlink_re.match(line)
        rename_match = self._rename_re.match(line)
        clone_match = self._clone_re.match(line)  

        kill_match = self._kill_re.match(line)
        if kill_match:
            return None, None, None

        match = None
        if execve_match:
            pid = execve_match.group('pid')
            match = execve_match # Executables can be dependencies
            if pid not in processes and len(processes) == 0:
                # This is the first process so create dict entry
                processes[pid] = StraceProcess()
        elif clone_match:
            pid = clone_match.group('pid')
            pid_clone = clone_match.group('pid_clone')
            if pid not in processes:
                # Simple case where there are no delayed lines
                processes[pid] = StraceProcess(processes[pid_clone].cwd)
            else:
                # Some line processing was delayed due to an interupted clone_match
                processes[pid].cwd = processes[pid_clone].cwd # Set the correct cwd
                processes[pid].delayed = False # Set that matching is no longer delayed
                for delayed_line in processes[pid].delayed_lines:
                    # Process all the delayed lines
                    self._match_line(delayed_line, processes, unfinished) 
                processes[pid].delayed_lines = [] # Clear the lines
        elif open_match:
            match = open_match
            mode = match.group('mode')
            if 'O_WRONLY' in mode or 'O_RDWR' in mode:
                # it's an output file if opened for writing
                is_output = True
        elif stat_match:
            match = stat_match
        elif creat_match:
            match = creat_match
            # a created file is an output file
            is_output = True
        elif mkdir_match:
            match = mkdir_match
            if match.group('result') == '0':
                # a created directory is an output file
                is_output = True
        elif symlink_match:
            match =  symlink_match                  
            # the created symlink is an output file
            is_output = True
        elif rename_match:
            match = rename_match
            # the destination of a rename is an output file
            is_output = True
            
        if match:
            name = match.group('name')
            pid  = match.group('pid')
            if not self._matching_is_delayed(processes, pid, line):
                cwd = processes[pid].cwd
                if cwd != '.':
                    name = os.path.join(cwd, name)

                # normalise path name to ensure files are only listed once
                name = os.path.normpath(name)

                # if it's an absolute path name under the build directory,
                # make it relative to build_dir before saving to .deps file
                if os.path.isabs(name) and name.startswith(self.build_dir):
                    name = name[len(self.build_dir):]
                    name = name.lstrip(os.path.sep)

                if (self._builder._is_relevant(name) 
                    and not self.ignore(name) 
                    and os.path.lexists(name)):
                    if is_output:
                        processes[pid].add_output(name)
                    else:
                        processes[pid].add_dep(name)

        match = self._chdir_re.match(line)
        if match:
            pid  = match.group('pid')
            if not self._matching_is_delayed(processes, pid, line):
                processes[pid].cwd = os.path.join(processes[pid].cwd, match.group('cwd'))

        match = self._exit_group_re.match(line)
        if match:
            self.status = int(match.group('status'))

    def _matching_is_delayed(self, processes, pid, line):
        # Check if matching is delayed and cache a delayed line
        if pid not in processes:
             processes[pid] = StraceProcess(delayed=True)
        
        process = processes[pid]
        if process.delayed:
            process.add_delayed_line(line)
            return True
        else:
            return False
            
    def __call__(self, *args, **kwargs):
        """ Run command and return its dependencies and outputs, using strace
            to determine dependencies (by looking at what files are opened or
            modified). """
        ignore_status = kwargs.pop('ignore_status', False)
        if self.keep_temps:
            outname = 'strace%03d.txt' % self.temp_count
            self.temp_count += 1
            handle = os.open(outname, os.O_CREAT)
        else:
            handle, outname = tempfile.mkstemp()

        try:
            try:
                outfile = os.fdopen(handle, 'r')
            except:
                os.close(handle)
                raise
            try:
                status, deps, outputs = self._do_strace(args, kwargs, outfile, outname)
                if status is None:
                    raise ExecutionError(
                        '%r was killed unexpectedly' % args[0], '', -1)
            finally:
                outfile.close()
        finally:
            if not self.keep_temps:
                os.remove(outname)

        if status and not ignore_status:
            raise ExecutionError('%r exited with status %d'
                                 % (os.path.basename(args[0]), status),
                                 '', status)
        return list(deps), list(outputs)

class AlwaysRunner(Runner):
    def __init__(self, builder):
        pass

    def __call__(self, *args, **kwargs):
        """ Runner that always runs given command, used as a backup in case
            a system doesn't have strace or atimes. """
        shell_keywords = dict(silent=False)
        shell_keywords.update(kwargs)
        shell(*args, **shell_keywords)
        return None, None

class SmartRunner(Runner):
    """ Smart command runner that uses StraceRunner if it can,
        otherwise AtimesRunner if available, otherwise AlwaysRunner. """
    def __init__(self, builder):
        self._builder = builder
        try:
            self._runner = StraceRunner(self._builder)
        except RunnerUnsupportedException:
            try:
                self._runner = AtimesRunner(self._builder)
            except RunnerUnsupportedException:
                self._runner = AlwaysRunner(self._builder)

    def actual_runner(self):
        return self._runner

    def __call__(self, *args, **kwargs):
        return self._runner(*args, **kwargs)

class _running(object):
    """ Represents a task put on the parallel pool 
        and its results when complete """
    def __init__(self, async, command):
        """ "async" is the AsyncResult object returned from pool.apply_async
            "command" is the command that was run """
        self.async = async
        self.command = command
        self.results = None
        
class _after(object):
    """ Represents something waiting on completion of some previous commands """
    def __init__(self, afters, do):
        """ "afters" is a group id or a iterable of group ids to wait on
            "do" is either a tuple representing a command (group, command, 
                arglist, kwargs) or a threading.Condition to be released """
        self.afters = afters
        self.do = do
        self.done = False
        
class _Groups(object):
    """ Thread safe mapping object whose values are lists of _running
        or _after objects and a count of how many have *not* completed """
    class value(object):
        """ the value type in the map """
        def __init__(self, val=None):
            self.count = 0  # count of items not yet completed.
                            # This also includes count_in_false number
            self.count_in_false = 0  # count of commands which is assigned 
                                     # to False group, but will be moved
                                     # to this group.
            self.items = [] # items in this group
            if val is not None:
                self.items.append(val)
            self.ok = True  # True if no error from any command in group so far
            
    def __init__(self):
        self.groups = {False: self.value()}
        self.lock = threading.Lock()
        
    def item_list(self, id):
        """ Return copy of the value list """
        with self.lock:
            return self.groups[id].items[:]
    
    def remove(self, id):
        """ Remove the group """
        with self.lock:
            del self.groups[id]
    
    def remove_item(self, id, val):
        with self.lock:
            self.groups[id].items.remove(val)
            
    def add(self, id, val):
        with self.lock:
            if id in self.groups:
                self.groups[id].items.append(val)
            else:
                self.groups[id] = self.value(val)
            self.groups[id].count += 1

    def ensure(self, id):
        """if id does not exit, create it without any value"""
        with self.lock:
            if not id in self.groups:
                self.groups[id] = self.value()

    def get_count(self, id):
        with self.lock:
            if id not in self.groups:
                return 0
            return self.groups[id].count

    def dec_count(self, id):
        with self.lock:
            c = self.groups[id].count - 1
            if c < 0:
                raise ValueError
            self.groups[id].count = c
            return c
    
    def get_ok(self, id):
        with self.lock:
            return self.groups[id].ok
    
    def set_ok(self, id, to):
        with self.lock:
            self.groups[id].ok = to
            
    def ids(self):
        with self.lock:
            return self.groups.keys()

    # modification to reserve blocked commands to corresponding groups
    def inc_count_for_blocked(self, id):
        with self.lock:
            if not id in self.groups:
                self.groups[id] = self.value()
            self.groups[id].count += 1
            self.groups[id].count_in_false += 1
    
    def add_for_blocked(self, id, val):
        # modification of add(), in order to move command from False group
        # to actual group
        with self.lock:
            # id must be registered before
            self.groups[id].items.append(val)
            # count does not change (already considered 
            # in inc_count_for_blocked), but decrease count_in_false.
            c = self.groups[id].count_in_false - 1
            if c < 0:
                raise ValueError
            self.groups[id].count_in_false = c

    
# pool of processes to run parallel jobs, must not be part of any object that
# is pickled for transfer to these processes, ie it must be global
_pool = None
# object holding results, must also be global
_groups = _Groups()
# results collecting thread
_results = None
_stop_results = threading.Event()

class _todo(object):
    """ holds the parameters for commands waiting on others """
    def __init__(self, group, command, arglist, kwargs):
        self.group = group      # which group it should run as
        self.command = command  # string command
        self.arglist = arglist  # command arguments
        self.kwargs = kwargs    # keywork args for the runner
        
def _results_handler( builder, delay=0.01):
    """ Body of thread that stores results in .deps and handles 'after'
        conditions
       "builder" the builder used """
    try:
        while not _stop_results.isSet():
            # go through the lists and check any results available
            for id in _groups.ids():
                if id is False: continue # key of False is _afters not _runnings
                for r in _groups.item_list(id):
                    if r.results is None and r.async.ready():
                        try:
                            d, o = r.async.get()
                        except Exception, e:
                            r.results = e
                            _groups.set_ok(id, False)
                            message, data, status = e
                            printerr("fabricate: " + message)
                        else:
                            builder.done(r.command, d, o) # save deps
                            r.results = (r.command, d, o)
                        _groups.dec_count(id)
            # check if can now schedule things waiting on the after queue
            for a in _groups.item_list(False):
                still_to_do = sum(_groups.get_count(g) for g in a.afters)
                no_error = all(_groups.get_ok(g) for g in a.afters)
                if False in a.afters:
                    still_to_do -= 1 # don't count yourself of course
                if still_to_do == 0:
                    if isinstance(a.do, _todo):
                        if no_error:
                            async = _pool.apply_async(_call_strace, a.do.arglist,
                                        a.do.kwargs)
                            _groups.add_for_blocked(a.do.group, _running(async, a.do.command))
                        else:
                            # Mark the command as not done due to errors
                            r = _running(None, a.do.command)
                            _groups.add_for_blocked(a.do.group, r)
                            r.results = False;
                            _groups.set_ok(a.do.group, False)
                            _groups.dec_count(a.do.group)
                    elif isinstance(a.do, threading._Condition):
                        # is this only for threading._Condition in after()?
                        a.do.acquire()
                        # only mark as done if there is no error
                        a.done = no_error 
                        a.do.notify()
                        a.do.release()
                    # else: #are there other cases?
                    _groups.remove_item(False, a)
                    _groups.dec_count(False)
                    
            _stop_results.wait(delay)
    except Exception:
        etype, eval, etb = sys.exc_info()
        printerr("Error: exception " + repr(etype) + " at line " + str(etb.tb_lineno))
    finally:
        if not _stop_results.isSet():
            # oh dear, I am about to die for unexplained reasons, stop the whole
            # app otherwise the main thread hangs waiting on non-existant me, 
            # Note: sys.exit() only kills me
            printerr("Error: unexpected results handler exit")
            os._exit(1)
        
class Builder(object):
    """ The Builder.

        You may supply a "runner" class to change the way commands are run
        or dependencies are determined. For an example, see:
            http://code.google.com/p/fabricate/wiki/HowtoMakeYourOwnRunner

        A "runner" must be a subclass of Runner and must have a __call__()
        function that takes a command as a list of args and returns a tuple of
        (deps, outputs), where deps is a list of rel-path'd dependency files
        and outputs is a list of rel-path'd output files. The default runner
        is SmartRunner, which automatically picks one of StraceRunner,
        AtimesRunner, or AlwaysRunner depending on your system.
        A "runner" class may have an __init__() function that takes the
        builder as a parameter.
    """

    def __init__(self, runner=None, dirs=None, dirdepth=100, ignoreprefix='.',
                 ignore=None, hasher=md5_hasher, depsname='.deps',
                 quiet=False, debug=False, inputs_only=False, parallel_ok=False):
        """ Initialise a Builder with the given options.

        "runner" specifies how programs should be run.  It is either a
            callable compatible with the Runner class, or a string selecting
            one of the standard runners ("atimes_runner", "strace_runner",
            "always_runner", or "smart_runner").
        "dirs" is a list of paths to look for dependencies (or outputs) in
            if using the strace or atimes runners.
        "dirdepth" is the depth to recurse into the paths in "dirs" (default
            essentially means infinitely). Set to 1 to just look at the
            immediate paths in "dirs" and not recurse at all. This can be
            useful to speed up the AtimesRunner if you're building in a large
            tree and you don't care about all of the subdirectories.
        "ignoreprefix" prevents recursion into directories that start with
            prefix.  It defaults to '.' to ignore svn directories.
            Change it to '_svn' if you use _svn hidden directories.
        "ignore" is a regular expression.  Any dependency that contains a
            regex match is ignored and not put into the dependency list.
            Note that the regex may be VERBOSE (spaces are ignored and # line
            comments allowed -- use \ prefix to insert these characters)
        "hasher" is a function which returns a string which changes when
            the contents of its filename argument changes, or None on error.
            Default is md5_hasher, but can also be mtime_hasher.
        "depsname" is the name of the JSON dependency file to load/save.
        "quiet" set to True tells the builder to not display the commands being
            executed (or other non-error output).
        "debug" set to True makes the builder print debug output, such as why
            particular commands are being executed
        "inputs_only" set to True makes builder only re-build if input hashes
            have changed (ignores output hashes); use with tools that touch
            files that shouldn't cause a rebuild; e.g. g++ collect phase
        "parallel_ok" set to True to indicate script is safe for parallel running
        """
        if dirs is None:
            dirs = ['.']
        self.dirs = dirs
        self.dirdepth = dirdepth
        self.ignoreprefix = ignoreprefix
        if ignore is None:
            ignore = r'$x^'         # something that can't match
        self.ignore = re.compile(ignore, re.VERBOSE)
        self.depsname = depsname
        self.hasher = hasher
        self.quiet = quiet
        self.debug = debug
        self.inputs_only = inputs_only
        self.checking = False
        self.hash_cache = {}

        # instantiate runner after the above have been set in case it needs them
        if runner is not None:
            self.set_runner(runner)
        elif hasattr(self, 'runner'):
            # For backwards compatibility, if a derived class has
            # defined a "runner" method then use it:
            pass
        else:
            self.runner = SmartRunner(self)

        is_strace = isinstance(self.runner.actual_runner(), StraceRunner)
        self.parallel_ok = parallel_ok and is_strace and _pool is not None
        if self.parallel_ok:
            global _results
            _results = threading.Thread(target=_results_handler,
                                        args=[self])
            _results.setDaemon(True)
            _results.start()
            atexit.register(self._join_results_handler)
            StraceRunner.keep_temps = False # unsafe for parallel execution
            
    def echo(self, message):
        """ Print message, but only if builder is not in quiet mode. """
        if not self.quiet:
            print message

    def echo_command(self, command, echo=None):
        """ Show a command being executed. Also passed run's "echo" arg
            so you can override what's displayed.
        """
        if echo is not None:
            command = str(echo)
        self.echo(command)

    def echo_delete(self, filename, error=None):
        """ Show a file being deleted. For subclassing Builder and overriding
            this function, the exception is passed in if an OSError occurs
            while deleting a file. """
        if error is None:
            self.echo('deleting %s' % filename)
        else:
            self.echo_debug('error deleting %s: %s' % (filename, error.strerror))

    def echo_debug(self, message):
        """ Print message, but only if builder is in debug mode. """
        if self.debug:
            print 'DEBUG:', message

    def _run(self, *args, **kwargs):
        after = kwargs.pop('after', None)
        group = kwargs.pop('group', True)
        echo = kwargs.pop('echo', None)
        arglist = args_to_list(args)
        if not arglist:
            raise TypeError('run() takes at least 1 argument (0 given)')
        # we want a command line string for the .deps file key and for display
        command = subprocess.list2cmdline(arglist)
        if not self.cmdline_outofdate(command):
            if self.parallel_ok:
                _groups.ensure(group)
            return command, None, None

        # if just checking up-to-date-ness, set flag and do nothing more
        self.outofdate_flag = True
        if self.checking:
            if self.parallel_ok:
                _groups.ensure(group)
            return command, None, None

        # use runner to run command and collect dependencies
        self.echo_command(command, echo=echo)
        if self.parallel_ok:
            arglist.insert(0, self.runner)
            if after is not None:
                if not hasattr(after, '__iter__'):
                    after = [after]
                # This command is registered to False group firstly,
                # but the actual group of this command should 
                # count this blocked command as well as usual commands
                _groups.inc_count_for_blocked(group)
                _groups.add(False,
                            _after(after, _todo(group, command, arglist,
                                                kwargs)))
            else:
                async = _pool.apply_async(_call_strace, arglist, kwargs)
                _groups.add(group, _running(async, command))
            return None
        else:
            deps, outputs = self.runner(*arglist, **kwargs)
            return self.done(command, deps, outputs)
        
    def run(self, *args, **kwargs):
        """ Run command given in args with kwargs per shell(), but only if its
            dependencies or outputs have changed or don't exist. Return tuple
            of (command_line, deps_list, outputs_list) so caller or subclass
            can use them.

            Parallel operation keyword args "after" specifies a group or 
            iterable of groups to wait for after they finish, "group" specifies 
            the group to add this command to.

            Optional "echo" keyword arg is passed to echo_command() so you can
            override its output if you want.
        """
        try:
            return self._run(*args, **kwargs)
        finally:
            sys.stderr.flush()
            sys.stdout.flush()

    def done(self, command, deps, outputs):
        """ Store the results in the .deps file when they are available """
        if deps is not None or outputs is not None:
            deps_dict = {}

            # hash the dependency inputs and outputs
            for dep in deps:
                if dep in self.hash_cache:
                    # already hashed so don't repeat hashing work
                    hashed = self.hash_cache[dep]
                else:
                    hashed = self.hasher(dep)
                if hashed is not None:
                    deps_dict[dep] = "input-" + hashed
                    # store hash in hash cache as it may be a new file
                    self.hash_cache[dep] = hashed

            for output in outputs:
                hashed = self.hasher(output)
                if hashed is not None:
                    deps_dict[output] = "output-" + hashed
                    # update hash cache as this file should already be in
                    # there but has probably changed
                    self.hash_cache[output] = hashed

            self.deps[command] = deps_dict
        
        return command, deps, outputs

    def memoize(self, command, **kwargs):
        """ Run the given command, but only if its dependencies have changed --
            like run(), but returns the status code instead of raising an
            exception on error. If "command" is a string (as per memoize.py)
            it's split into args using shlex.split() in a POSIX/bash style,
            otherwise it's a list of args as per run().

            This function is for compatiblity with memoize.py and is
            deprecated. Use run() instead. """
        if isinstance(command, basestring):
            args = shlex.split(command)
        else:
            args = args_to_list(command)
        try:
            self.run(args, **kwargs)
            return 0
        except ExecutionError, exc:
            message, data, status = exc
            return status

    def outofdate(self, func):
        """ Return True if given build function is out of date. """
        self.checking = True
        self.outofdate_flag = False
        func()
        self.checking = False
        return self.outofdate_flag

    def cmdline_outofdate(self, command):
        """ Return True if given command line is out of date. """
        if command in self.deps:
            # command has been run before, see if deps have changed
            for dep, oldhash in self.deps[command].items():
                assert oldhash.startswith('input-') or \
                       oldhash.startswith('output-'), \
                    "%s file corrupt, do a clean!" % self.depsname
                io_type, oldhash = oldhash.split('-', 1)

                # make sure this dependency or output hasn't changed
                if dep in self.hash_cache:
                    # already hashed so don't repeat hashing work
                    newhash = self.hash_cache[dep]
                else:
                    # not in hash_cache so make sure this dependency or
                    # output hasn't changed
                    newhash = self.hasher(dep)
                    if newhash is not None:
                       # Add newhash to the hash cache
                       self.hash_cache[dep] = newhash

                if newhash is None:
                    self.echo_debug("rebuilding %r, %s %s doesn't exist" %
                                    (command, io_type, dep))
                    break
                if newhash != oldhash and (not self.inputs_only or io_type == 'input'):
                    self.echo_debug("rebuilding %r, hash for %s %s (%s) != old hash (%s)" %
                                    (command, io_type, dep, newhash, oldhash))
                    break
            else:
                # all dependencies are unchanged
                return False
        else:
            self.echo_debug('rebuilding %r, no dependency data' % command)
        # command has never been run, or one of the dependencies didn't
        # exist or had changed
        return True

    def autoclean(self):
        """ Automatically delete all outputs of this build as well as the .deps
            file. """
        # first build a list of all the outputs from the .deps file
        outputs = []
        dirs = []
        for command, deps in self.deps.items():
            outputs.extend(dep for dep, hashed in deps.items()
                           if hashed.startswith('output-'))
        outputs.append(self.depsname)
        self._deps = None
        for output in outputs:
            try:
                os.remove(output)
            except OSError, e:
                if os.path.isdir(output):
                    # cache directories to be removed once all other outputs
                    # have been removed, as they may be content of the dir
                    dirs.append(output)
                else:
                    self.echo_delete(output, e)                
            else:
                self.echo_delete(output)
        # delete the directories in reverse sort order
        # this ensures that parents are removed after children
        for dir in sorted(dirs, reverse=True):
            try:
                os.rmdir(dir)
            except OSError, e:
                self.echo_delete(dir, e)                
            else:
                self.echo_delete(dir)
               

    @property
    def deps(self):
        """ Lazy load .deps file so that instantiating a Builder is "safe". """
        if not hasattr(self, '_deps') or self._deps is None:
            self.read_deps()
            atexit.register(self.write_deps, depsname=os.path.abspath(self.depsname))
        return self._deps

    def read_deps(self):
        """ Read dependency JSON file into deps object. """
        try:
            f = open(self.depsname)
            try:
                self._deps = json.load(f)
                # make sure the version is correct
                if self._deps.get('.deps_version', 0) != deps_version:
                    printerr('Bad %s dependency file version! Rebuilding.'
                             % self.depsname)
                    self._deps = {}
                self._deps.pop('.deps_version', None)
            finally:
                f.close()
        except IOError:
            self._deps = {}

    def write_deps(self, depsname=None):
        """ Write out deps object into JSON dependency file. """
        if self._deps is None:
            return                      # we've cleaned so nothing to save
        self.deps['.deps_version'] = deps_version
        if depsname is None:
            depsname = self.depsname
        f = open(depsname, 'w')
        try:
            json.dump(self.deps, f, indent=4, sort_keys=True)
        finally:
            f.close()
            self._deps.pop('.deps_version', None)

    _runner_map = {
        'atimes_runner' : AtimesRunner,
        'strace_runner' : StraceRunner,
        'always_runner' : AlwaysRunner,
        'smart_runner' : SmartRunner,
        }

    def set_runner(self, runner):
        """Set the runner for this builder.  "runner" is either a Runner
           subclass (e.g. SmartRunner), or a string selecting one of the
           standard runners ("atimes_runner", "strace_runner",
           "always_runner", or "smart_runner")."""
        try:
            self.runner = self._runner_map[runner](self)
        except KeyError:
            if isinstance(runner, basestring):
                # For backwards compatibility, allow runner to be the
                # name of a method in a derived class:
                self.runner = getattr(self, runner)
            else:
                # pass builder to runner class to get a runner instance
                self.runner = runner(self)

    def _is_relevant(self, fullname):
        """ Return True if file is in the dependency search directories. """

        # need to abspath to compare rel paths with abs
        fullname = os.path.abspath(fullname)
        for path in self.dirs:
            path = os.path.abspath(path)
            if fullname.startswith(path):
                rest = fullname[len(path):]
                # files in dirs starting with ignoreprefix are not relevant
                if os.sep+self.ignoreprefix in os.sep+os.path.dirname(rest):
                    continue
                # files deeper than dirdepth are not relevant
                if rest.count(os.sep) > self.dirdepth:
                    continue
                return True
        return False

    def _join_results_handler(self):
        """Stops then joins the results handler thread"""
        _stop_results.set()
        _results.join()

# default Builder instance, used by helper run() and main() helper functions
default_builder = None
default_command = 'build'

# save the setup arguments for use by main()
_setup_builder = None
_setup_default = None
_setup_kwargs = {}

def setup(builder=None, default=None, **kwargs):
    """ NOTE: setup functionality is now in main(), setup() is kept for
        backward compatibility and should not be used in new scripts.

        Setup the default Builder (or an instance of given builder if "builder"
        is not None) with the same keyword arguments as for Builder().
        "default" is the name of the default function to run when the build
        script is run with no command line arguments. """
    global _setup_builder, _setup_default, _setup_kwargs
    _setup_builder = builder
    _setup_default = default
    _setup_kwargs = kwargs
setup.__doc__ += '\n\n' + Builder.__init__.__doc__

def _set_default_builder():
    """ Set default builder to Builder() instance if it's not yet set. """
    global default_builder
    if default_builder is None:
        default_builder = Builder()

def run(*args, **kwargs):
    """ Run the given command, but only if its dependencies have changed. Uses
        the default Builder. Return value as per Builder.run(). If there is
        only one positional argument which is an iterable treat each element
        as a command, returns a list of returns from Builder.run().
    """
    _set_default_builder()
    if len(args) == 1 and hasattr(args[0], '__iter__'):
        return [default_builder.run(*a, **kwargs) for a in args[0]]
    return default_builder.run(*args, **kwargs)

def after(*args):
    """ wait until after the specified command groups complete and return 
        results, or None if not parallel """
    _set_default_builder()
    if getattr(default_builder, 'parallel_ok', False):
        if len(args) == 0:
            args = _groups.ids()  # wait on all
        cond = threading.Condition()
        cond.acquire()
        a = _after(args, cond)
        _groups.add(False, a)
        cond.wait()
        if not a.done:
            sys.exit(1)
        results = []
        ids = _groups.ids()
        for a in args:
            if a in ids and a is not False:
                r = []
                for i in _groups.item_list(a):
                    r.append(i.results)
                results.append((a,r))
        return results
    else:
        return None
    
def autoclean():
    """ Automatically delete all outputs of the default build. """
    _set_default_builder()
    default_builder.autoclean()

def memoize(command, **kwargs):
    _set_default_builder()
    return default_builder.memoize(command, **kwargs)

memoize.__doc__ = Builder.memoize.__doc__

def outofdate(command):
    """ Return True if given command is out of date and needs to be run. """
    _set_default_builder()
    return default_builder.outofdate(command)

# save options for use by main() if parse_options called earlier by user script
_parsed_options = None

# default usage message
_usage = '[options] build script functions to run'

def parse_options(usage=_usage, extra_options=None, command_line=None):
    """ Parse command line options and return (parser, options, args). """
    parser = optparse.OptionParser(usage='Usage: %prog '+usage,
                                   version='%prog '+__version__)
    parser.disable_interspersed_args()
    parser.add_option('-t', '--time', action='store_true',
                      help='use file modification times instead of MD5 sums')
    parser.add_option('-d', '--dir', action='append',
                      help='add DIR to list of relevant directories')
    parser.add_option('-c', '--clean', action='store_true',
                      help='autoclean build outputs before running')
    parser.add_option('-q', '--quiet', action='store_true',
                      help="don't echo commands, only print errors")
    parser.add_option('-D', '--debug', action='store_true',
                      help="show debug info (why commands are rebuilt)")
    parser.add_option('-k', '--keep', action='store_true',
                      help='keep temporary strace output files')
    parser.add_option('-j', '--jobs', type='int',
                      help='maximum number of parallel jobs')
    if extra_options:
        # add any user-specified options passed in via main()
        for option in extra_options:
            parser.add_option(option)
    if command_line is not None:
        options, args = parser.parse_args(command_line)
    else:
        options, args = parser.parse_args()
    _parsed_options = (parser, options, args)
    return _parsed_options

def fabricate_version(min=None, max=None):
    """ If min is given, assert that the running fabricate is at least that
        version or exit with an error message. If max is given, assert that
        the running fabricate is at most that version. Return the current
        fabricate version string. This function was introduced in v1.14;
        for prior versions, the version string is available only as module
        local string fabricate.__version__ """

    if min is not None and float(__version__) < min:
        sys.stderr.write(("fabricate is version %s.  This build script "
            "requires at least version %.2f") % (__version__, min))
        sys.exit()
    if max is not None and float(__version__) > max:
        sys.stderr.write(("fabricate is version %s.  This build script "
            "requires at most version %.2f") % (__version__, max))
        sys.exit()
    return __version__

def main(globals_dict=None, build_dir=None, extra_options=None, builder=None,
         default=None, jobs=1, command_line=None, **kwargs):
    """ Run the default function or the function(s) named in the command line
        arguments. Call this at the end of your build script. If one of the
        functions returns nonzero, main will exit with the last nonzero return
        value as its status code.

        "builder" is the class of builder to create, default (None) is the 
        normal builder
        "command_line" is an optional list of command line arguments that can
        be used to prevent the default parsing of sys.argv. Used to intercept
        and modify the command line passed to the build script.
        "default" is the default user script function to call, None = 'build'
        "extra_options" is an optional list of options created with
        optparse.make_option(). The pseudo-global variable main.options
        is set to the parsed options list.
        "kwargs" is any other keyword arguments to pass to the builder """
    global default_builder, default_command, _pool

    kwargs.update(_setup_kwargs)
    if _parsed_options is not None:
        parser, options, actions = _parsed_options
    else:
        parser, options, actions = parse_options(extra_options=extra_options, command_line=command_line)
    kwargs['quiet'] = options.quiet
    kwargs['debug'] = options.debug
    if options.time:
        kwargs['hasher'] = mtime_hasher
    if options.dir:
        kwargs['dirs'] = options.dir
    if options.keep:
        StraceRunner.keep_temps = options.keep
    main.options = options
    if options.jobs is not None:
        jobs = options.jobs
    if default is not None:
        default_command = default
    if default_command is None:
        default_command = _setup_default
    if not actions:
        actions = [default_command]

    original_path = os.getcwd()
    if None in [globals_dict, build_dir]:
        try:
            frame = sys._getframe(1)
        except:
            printerr("Your Python version doesn't support sys._getframe(1),")
            printerr("call main(globals(), build_dir) explicitly")
            sys.exit(1)
        if globals_dict is None:
            globals_dict = frame.f_globals
        if build_dir is None:
            build_file = frame.f_globals.get('__file__', None)
            if build_file:
                build_dir = os.path.dirname(build_file)
    if build_dir:
        if not options.quiet and os.path.abspath(build_dir) != original_path:
            print "Entering directory '%s'" % build_dir
        os.chdir(build_dir)
    if _pool is None and jobs > 1:
        _pool = multiprocessing.Pool(jobs)

    use_builder = Builder
    if _setup_builder is not None:
        use_builder = _setup_builder
    if builder is not None:
        use_builder = builder
    default_builder = use_builder(**kwargs)

    if options.clean:
        default_builder.autoclean()

    status = 0
    try:
        for action in actions:
            if '(' not in action:
                action = action.strip() + '()'
            name = action.split('(')[0].split('.')[0]
            if name in globals_dict:
                this_status = eval(action, globals_dict)
                if this_status:
                    status = int(this_status)
            else:
                printerr('%r command not defined!' % action)
                sys.exit(1)
        after() # wait till the build commands are finished
    except ExecutionError, exc:
        message, data, status = exc
        printerr('fabricate: ' + message)
    finally:
        _stop_results.set() # stop the results gatherer so I don't hang
        if not options.quiet and os.path.abspath(build_dir) != original_path:
            print "Leaving directory '%s' back to '%s'" % (build_dir, original_path)
        os.chdir(original_path)
    sys.exit(status)

if __name__ == '__main__':
    # if called as a script, emulate memoize.py -- run() command line
    parser, options, args = parse_options('[options] command line to run')
    status = 0
    if args:
        status = memoize(args)
    elif not options.clean:
        parser.print_help()
        status = 1
    # autoclean may have been used
    sys.exit(status)

########NEW FILE########
__FILENAME__ = fcgi_aspen
"""Run the aspen webserver as a FastCGI process.  Requires that you have flup installed.
"""

from aspen.wsgi import website
from flup.server.fcgi import WSGIServer

def main():
    WSGIServer(website).run()


########NEW FILE########
__FILENAME__ = all-utf8
#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import sys

for i in range(2**16):
    u = unichr(i).encode('utf8')
    sys.stdout.write("%5d %s  " % (i, u))
    if i % 6 == 0:
        print


########NEW FILE########
__FILENAME__ = assert_test
#!/usr/bin/env python
"""Benchmark assert

without assert: 0.79 seconds
with assert: 0.95 seconds

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import time

if __name__ == '__main__':
    start = time.time()

    for i in range(10000000):
        #pass
        assert 1 == 1

    end = time.time()
    print("%5.2f" % (end - start))

########NEW FILE########
__FILENAME__ = conftest
from aspen.testing.harness import teardown
from aspen.testing.pytest_fixtures import client, harness, fs
from aspen.testing.pytest_fixtures import sys_path, sys_path_scrubber


def pytest_runtest_teardown():
    teardown()

########NEW FILE########
__FILENAME__ = except_test
#!/usr/bin/env python
"""Benchmark try vs. except

without raise Exception: 0.94 seconds
with raise Exception: 9.26 seconds

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import time

if __name__ == '__main__':
    start = time.time()

    for i in range(10000000):
        try:
            raise Exception
            pass
        except Exception:
            pass

    end = time.time()
    print("%5.2f" % (end - start))

########NEW FILE########
__FILENAME__ = test_charset_re
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from aspen.http.response import charset_re


m = lambda s: charset_re.match(s) is not None


def test_charset_re_works():
    assert m("cheese")

def test_charset_re_disallows_spaces():
    assert not m("cheese head")

def test_charset_re_doesnt_match_empty_string():
    assert not m("")

def test_charset_re_does_match_string_of_one_character():
    assert m("a")

def test_charset_re_does_match_string_of_forty_characters():
    assert m("0123456789012345678901234567890123456789")

def test_charset_re_doesnt_match_string_of_forty_one_characters():
    assert not m("01234567890123456789012345678901234567890")

def test_charset_re_matches_ascii():
    assert m("US-ASCII")

def test_charset_re_matches_utf8():
    assert m("UTF-8")

def test_charset_re_pt():
    assert m("PT")

def test_charset_re_latin1():
    assert m("latin-1")

def test_charset_re_iso88591():
    assert m("ISO-8859-1")

def test_charset_re_windows1252():
    assert m("windows-1252")

def test_charset_re_matches_valid_perl():
    assert m(":_()+.-")

########NEW FILE########
__FILENAME__ = test_configuration
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys

from pytest import raises, mark

from aspen.configuration import Configurable, ConfigurationError, parse
from aspen.configuration.options import OptionParser, DEFAULT
from aspen.website import Website


def test_everything_defaults_to_empty_string():
    o = OptionParser()
    opts, args = o.parse_args([])
    actual = ( opts.configuration_scripts
             , opts.logging_threshold
             , opts.project_root
             , opts.www_root

             , opts.changes_reload
             , opts.charset_dynamic
             , opts.charset_static
             , opts.indices
             , opts.media_type_default
             , opts.media_type_json
             , opts.renderer_default
             , opts.show_tracebacks
              )
    expected = ( DEFAULT, DEFAULT, DEFAULT, DEFAULT, DEFAULT, DEFAULT
               , DEFAULT, DEFAULT, DEFAULT, DEFAULT, DEFAULT, DEFAULT
                )
    assert actual == expected

def test_logging_threshold_goes_to_one():
    o = OptionParser()
    opts, args = o.parse_args(['-l1'])
    actual = opts.logging_threshold
    expected = '1'
    assert actual == expected

def test_logging_threshold_goes_to_eleven():
    o = OptionParser()
    opts, args = o.parse_args(['--logging_threshold=11'])
    actual = opts.logging_threshold
    expected = '11'
    assert actual == expected


def test_configuration_scripts_can_take_one():
    o = OptionParser()
    opts, args = o.parse_args(['--configuration_scripts=startup.py'])
    actual = opts.configuration_scripts
    expected = 'startup.py'
    assert actual == expected

def test_configuration_scripts_can_take_two_doesnt_do_anything_special():
    o = OptionParser()
    opts, args = o.parse_args(['--configuration_scripts=startup.py,uncle.py'])
    actual = opts.configuration_scripts
    expected = 'startup.py,uncle.py'
    assert actual == expected

def test_configuration_scripts_really_doesnt_do_anything_special():
    o = OptionParser()
    opts, args = o.parse_args(['--configuration_scripts=Cheese is lovely.'])
    actual = opts.configuration_scripts
    expected = 'Cheese is lovely.'
    assert actual == expected

def test_configuration_scripts_arent_confused_by_io_errors(harness):
    CONFIG = "open('this file should not exist')\n"
    harness.fs.project.mk(('configure-aspen.py', CONFIG),)
    c = Configurable()
    actual = raises(IOError, c.configure, ['-p', harness.fs.project.resolve('.')]).value
    assert actual.strerror == 'No such file or directory'

def test_www_root_defaults_to_cwd():
    c = Configurable()
    c.configure([])
    expected = os.path.realpath(os.getcwd())
    actual = c.www_root
    assert actual == expected

@mark.skipif(sys.platform == 'win32',
             reason="Windows file locking makes this fail")
def test_ConfigurationError_raised_if_no_cwd(harness):
    FSFIX = harness.fs.project.resolve('')
    os.chdir(FSFIX)
    os.rmdir(FSFIX)
    c = Configurable()
    raises(ConfigurationError, c.configure, [])

@mark.skipif(sys.platform == 'win32',
             reason="Windows file locking makes this fail")
def test_ConfigurationError_NOT_raised_if_no_cwd_but_do_have__www_root(harness):
    foo = os.getcwd()
    os.chdir(harness.fs.project.resolve(''))
    os.rmdir(os.getcwd())
    c = Configurable()
    c.configure(['--www_root', foo])
    assert c.www_root == foo

def test_configurable_sees_root_option(harness):
    c = Configurable()
    c.configure(['--www_root', harness.fs.project.resolve('')])
    expected = harness.fs.project.root
    actual = c.www_root
    assert actual == expected

def test_configuration_scripts_works_at_all():
    o = OptionParser()
    opts, args = o.parse_args(['--configuration_scripts', "foo"])
    expected = "foo"
    actual = opts.configuration_scripts
    assert actual == expected

def assert_body(harness, uripath, expected_body):
    actual = harness.simple(filepath=None, uripath=uripath, want='response.body')
    assert actual == expected_body

def test_configuration_script_can_set_renderer_default(harness):
    CONFIG = """
website.renderer_default="stdlib_format"
    """
    SIMPLATE = """
name="program"
[----]
Greetings, {name}!
    """
    harness.fs.project.mk(('configure-aspen.py', CONFIG),)
    harness.fs.www.mk(('index.html.spt', SIMPLATE),)
    assert_body(harness, '/', 'Greetings, program!\n')

def test_configuration_script_ignores_blank_indexfilenames():
    w = Website(['--indices', 'index.html,, ,default.html'])
    assert w.indices[0] == 'index.html'
    assert w.indices[1] == 'default.html'
    assert len(w.indices) == 2, "Too many indexfile entries"


# Tests of parsing perversities

def test_parse_charset_good():
    actual = parse.charset(u'UTF-8')
    assert actual == 'UTF-8'

def test_parse_charset_bad():
    raises(ValueError, parse.charset, u'')


def test_parse_yes_no_yes_is_True():
    assert parse.yes_no(u'yEs')

def test_parse_yes_no_true_is_True():
    assert parse.yes_no(u'trUe')

def test_parse_yes_no_1_is_True():
    assert parse.yes_no(u'1')

def test_parse_yes_no_no_is_False():
    assert not parse.yes_no(u'nO')

def test_parse_yes_no_true_is_False():
    assert not parse.yes_no(u'FalSe')

def test_parse_yes_no_1_is_False():
    assert not parse.yes_no(u'0')

def test_parse_yes_no_int_is_AttributeError():
    raises(TypeError, parse.yes_no, 1)

def test_parse_yes_no_other_is_ValueError():
    raises(ValueError, parse.yes_no, u'cheese')


def test_parse_list_handles_one():
    actual = parse.list_(u'foo')
    assert actual == (False, ['foo'])

def test_parse_list_handles_two():
    actual = parse.list_(u'foo,bar')
    assert actual == (False, ['foo', 'bar'])

def test_parse_list_handles_spaces():
    actual = parse.list_(u' foo ,   bar ')
    assert actual == (False, ['foo', 'bar'])

def test_parse_list_handles_some_spaces():
    actual = parse.list_(u'foo,   bar, baz , buz ')
    assert actual == (False, ['foo', 'bar', 'baz', 'buz'])

def test_parse_list_uniquifies():
    actual = parse.list_(u'foo,foo,bar')
    assert actual == (False, ['foo', 'bar'])

def test_parse_list_extends():
    actual = parse.list_(u'+foo')
    assert actual == (True, ['foo'])


def test_parse_renderer_good():
    actual = parse.renderer(u'stdlib_percent')
    assert actual == u'stdlib_percent'

def test_parse_renderer_bad():
    raises(ValueError, parse.renderer, u'floober')

########NEW FILE########
__FILENAME__ = test_dispatcher
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
from pytest import raises

import aspen
from aspen import dispatcher, Response
from aspen.http.request import Request


# Helpers
# =======

def assert_fs(harness, ask_uri, expect_fs):
    actual = harness.simple(uripath=ask_uri, filepath=None, want='request.fs')
    assert actual == harness.fs.www.resolve(expect_fs)

def assert_raises_404(*args):
    if len(args) < 3: args += ('',)
    response = raises(Response, assert_fs, *args).value
    assert response.code == 404
    return response

def assert_raises_302(*args):
    if len(args) < 3: args += ('',)
    response = raises(Response, assert_fs, *args).value
    assert response.code == 302
    return response

def assert_virtvals(harness, uripath, expected_vals):
    actual = harness.simple(filepath=None, uripath=uripath, want='request.line.uri.path')
    assert actual == expected_vals

def assert_body(harness, uripath, expected_body):
    actual = harness.simple(filepath=None, uripath=uripath, want='response.body')
    assert actual == expected_body

NEGOTIATED_SIMPLATE="""[-----]\n[-----] text/plain\nGreetings, program!"""

# Indices
# =======

def test_index_is_found(harness):
    expected = harness.fs.www.resolve('index.html')
    actual = harness.make_request('Greetings, program!', 'index.html').fs
    assert actual == expected

def test_negotiated_index_is_found(harness):
    expected = harness.fs.www.resolve('index')
    actual = harness.make_request('''
        [----------] text/html
        <h1>Greetings, program!</h1>
        [----------] text/plain
        Greetings, program!
    ''', 'index').fs
    assert actual == expected

def test_alternate_index_is_not_found(harness):
    assert_raises_404(harness, '/')

def test_alternate_index_is_found(harness):
    harness.fs.project.mk(('configure-aspen.py', 'website.indices += ["default.html"]'),)
    harness.fs.www.mk(('default.html', "Greetings, program!"),)
    assert_fs(harness, '/', 'default.html')

def test_configure_aspen_py_setting_override_works_too(harness):
    harness.fs.project.mk(('configure-aspen.py', 'website.indices = ["default.html"]'),)
    harness.fs.www.mk(('index.html', "Greetings, program!"),)
    assert_raises_404(harness, '/')

def test_configure_aspen_py_setting_takes_first(harness):
    harness.fs.project.mk(('configure-aspen.py', 'website.indices = ["index.html", "default.html"]'),)
    harness.fs.www.mk( ('index.html', "Greetings, program!")
                     , ('default.html', "Greetings, program!")
                      )
    assert_fs(harness, '/', 'index.html')

def test_configure_aspen_py_setting_takes_second_if_first_is_missing(harness):
    harness.fs.project.mk(('configure-aspen.py', 'website.indices = ["index.html", "default.html"]'),)
    harness.fs.www.mk(('default.html', "Greetings, program!"),)
    assert_fs(harness, '/', 'default.html')

def test_configure_aspen_py_setting_strips_commas(harness):
    harness.fs.project.mk(('configure-aspen.py', 'website.indices = ["index.html", "default.html"]'),)
    harness.fs.www.mk(('default.html', "Greetings, program!"),)
    assert_fs(harness, '/', 'default.html')

def test_redirect_indices_to_slash(harness):
    harness.fs.project.mk(('configure-aspen.py', 'website.indices = ["index.html", "default.html"]'),)
    harness.fs.www.mk(('index.html', "Greetings, program!"),)
    assert_raises_302(harness, '/index.html')

def test_redirect_second_index_to_slash(harness):
    harness.fs.project.mk(('configure-aspen.py', 'website.indices = ["index.html", "default.html"]'),)
    harness.fs.www.mk(('default.html', "Greetings, program!"),)
    assert_raises_302(harness, '/default.html')

def test_dont_redirect_second_index_if_first(harness):
    harness.fs.project.mk(('configure-aspen.py', 'website.indices = ["index.html", "default.html"]'),)
    harness.fs.www.mk(('default.html', "Greetings, program!"), ('index.html', "Greetings, program!"),)
    # first index redirects
    assert_raises_302(harness, '/index.html')
    # second shouldn't
    assert_fs(harness, '/default.html', 'default.html')


# Negotiated Fall-through
# =======================

def test_indirect_negotiation_can_passthrough_static(harness):
    harness.fs.www.mk(('foo.html', "Greetings, program!"),)
    assert_fs(harness, 'foo.html', 'foo.html')

def test_indirect_negotiation_can_passthrough_renderered(harness):
    harness.fs.www.mk(('foo.html.spt', "Greetings, program!"),)
    assert_fs(harness, 'foo.html', 'foo.html.spt')

def test_indirect_negotiation_can_passthrough_negotiated(harness):
    harness.fs.www.mk(('foo', "Greetings, program!"),)
    assert_fs(harness, 'foo', 'foo')

def test_indirect_negotiation_modifies_one_dot(harness):
    harness.fs.www.mk(('foo', "Greetings, program!"),)
    assert_fs(harness, 'foo.html', 'foo')

def test_indirect_negotiation_skips_two_dots(harness):
    harness.fs.www.mk(('foo.bar', "Greetings, program!"),)
    assert_fs(harness, 'foo.bar.html', 'foo.bar')

def test_indirect_negotiation_prefers_rendered(harness):
    harness.fs.www.mk( ('foo.html', "Greetings, program!")
          , ('foo', "blah blah blah")
           )
    assert_fs(harness, 'foo.html', 'foo.html')

def test_indirect_negotiation_really_prefers_rendered(harness):
    harness.fs.www.mk( ('foo.html', "Greetings, program!")
          , ('foo.', "blah blah blah")
           )
    assert_fs(harness, 'foo.html', 'foo.html')

def test_indirect_negotiation_really_prefers_rendered_2(harness):
    harness.fs.www.mk( ('foo.html', "Greetings, program!")
          , ('foo', "blah blah blah")
           )
    assert_fs(harness, 'foo.html', 'foo.html')

def test_indirect_negotation_doesnt_do_dirs(harness):
    assert_raises_404(harness, 'foo.html')


# Virtual Paths
# =============

def test_virtual_path_can_passthrough(harness):
    harness.fs.www.mk(('foo.html', "Greetings, program!"),)
    assert_fs(harness, 'foo.html', 'foo.html')

def test_unfound_virtual_path_passes_through(harness):
    harness.fs.www.mk(('%bar/foo.html', "Greetings, program!"),)
    assert_raises_404(harness, '/blah/flah.html')

def test_virtual_path_is_virtual(harness):
    harness.fs.www.mk(('%bar/foo.html', "Greetings, program!"),)
    assert_fs(harness, '/blah/foo.html', '%bar/foo.html')

def test_virtual_path_sets_request_path(harness):
    harness.fs.www.mk(('%bar/foo.html', "Greetings, program!"),)
    assert_virtvals(harness, '/blah/foo.html', {'bar': [u'blah']} )

def test_virtual_path_sets_unicode_request_path(harness):
    harness.fs.www.mk(('%bar/foo.html', "Greetings, program!"),)
    assert_virtvals(harness, b'/%E2%98%83/foo.html', {'bar': [u'\u2603']})

def test_virtual_path_typecasts_to_int(harness):
    harness.fs.www.mk(('%year.int/foo.html', "Greetings, program!"),)
    assert_virtvals(harness, '/1999/foo.html', {'year': [1999]})

def test_virtual_path_raises_on_bad_typecast(harness):
    harness.fs.www.mk(('%year.int/foo.html', "Greetings, program!"),)
    raises(Response, assert_fs, harness, '/I am not a year./foo.html', '')

def test_virtual_path_raises_404_on_bad_typecast(harness):
    harness.fs.www.mk(('%year.int/foo.html', "Greetings, program!"),)
    assert_raises_404(harness, '/I am not a year./foo.html')

def test_virtual_path_raises_on_direct_access(harness):
    raises(Response, assert_fs, harness, '/%name/foo.html', '')

def test_virtual_path_raises_404_on_direct_access(harness):
    assert_raises_404(harness, '/%name/foo.html')

def test_virtual_path_matches_the_first(harness):
    harness.fs.www.mk( ('%first/foo.html', "Greetings, program!")
          , ('%second/foo.html', "WWAAAAAAAAAAAA!!!!!!!!")
           )
    assert_fs(harness, '/1999/foo.html', '%first/foo.html')

def test_virtual_path_directory(harness):
    harness.fs.www.mk(('%first/index.html', "Greetings, program!"),)
    assert_fs(harness, '/foo/', '%first/index.html')

def test_virtual_path_file(harness):
    harness.fs.www.mk(('foo/%bar.html.spt', "Greetings, program!"),)
    assert_fs(harness, '/foo/blah.html', 'foo/%bar.html.spt')

def test_virtual_path_file_only_last_part(harness):
    harness.fs.www.mk(('foo/%bar.html.spt', "Greetings, program!"),)
    assert_fs(harness, '/foo/blah/baz.html', 'foo/%bar.html.spt')

def test_virtual_path_file_only_last_part____no_really(harness):
    harness.fs.www.mk(('foo/%bar.html', "Greetings, program!"),)
    assert_raises_404(harness, '/foo/blah.html/')

def test_virtual_path_file_key_val_set(harness):
    harness.fs.www.mk(('foo/%bar.html.spt', "Greetings, program!"),)
    assert_virtvals(harness, '/foo/blah.html', {'bar': [u'blah']})

def test_virtual_path_file_key_val_not_cast(harness):
    harness.fs.www.mk(('foo/%bar.html.spt', "Greetings, program!"),)
    assert_virtvals(harness, '/foo/537.html', {'bar': [u'537']})

def test_virtual_path_file_key_val_cast(harness):
    harness.fs.www.mk(('foo/%bar.int.html.spt', "Greetings, program!"),)
    assert_virtvals(harness, '/foo/537.html', {'bar': [537]})

def test_virtual_path_file_not_dir(harness):
    harness.fs.www.mk( ('%foo/bar.html', "Greetings from bar!")
          , ('%baz.html.spt', "Greetings from baz!")
           )
    assert_fs(harness, '/bal.html', '%baz.html.spt')

# custom cast

userclassconfigure="""

import aspen.typecasting

class User:

    def __init__(self, name):
        self.username = name

    @classmethod
    def toUser(cls, name):
        return cls(name)

website.typecasters['user'] = User.toUser

"""

def test_virtual_path_file_key_val_cast_custom(harness):
    harness.fs.project.mk(('configure-aspen.py', userclassconfigure),)
    harness.fs.www.mk(('user/%user.user.html.spt', "\nusername=path['user']\n[-----]\nGreetings, %(username)s!"),)
    actual = harness.simple(filepath=None, uripath='/user/chad.html', want='request.line.uri.path',
            run_through='apply_typecasters_to_path')
    assert actual['user'].username == 'chad'

# negotiated *and* virtual paths
# ==============================

def test_virtual_path__and_indirect_neg_file_not_dir(harness):
    harness.fs.www.mk( ('%foo/bar.html', "Greetings from bar!")
          , ('%baz.spt', NEGOTIATED_SIMPLATE)
           )
    assert_fs(harness, '/bal.html', '%baz.spt')

def test_virtual_path_and_indirect_neg_noext(harness):
    harness.fs.www.mk(('%foo/bar', "Greetings program!"),)
    assert_fs(harness, '/greet/bar', '%foo/bar')

def test_virtual_path_and_indirect_neg_ext(harness):
    harness.fs.www.mk(('%foo/bar', "Greetings program!"),)
    assert_fs(harness, '/greet/bar.html', '%foo/bar')


# trailing slash
# ==============

def test_dispatcher_passes_through_files(harness):
    harness.fs.www.mk(('foo/index.html', "Greetings, program!"),)
    assert_raises_404(harness, '/foo/537.html')

def test_trailing_slash_passes_dirs_with_slash_through(harness):
    harness.fs.www.mk(('foo/index.html', "Greetings, program!"),)
    assert_fs(harness, '/foo/', '/foo/index.html')

def test_dispatcher_passes_through_virtual_dir_with_trailing_slash(harness):
    harness.fs.www.mk(('%foo/index.html', "Greetings, program!"),)
    assert_fs(harness, '/foo/', '/%foo/index.html')

def test_dispatcher_redirects_dir_without_trailing_slash(harness):
    harness.fs.www.mk('foo',)
    response = assert_raises_302(harness, '/foo')
    expected = '/foo/'
    actual = response.headers['Location']
    assert actual == expected

def test_dispatcher_redirects_virtual_dir_without_trailing_slash(harness):
    harness.fs.www.mk('%foo',)
    response = assert_raises_302(harness, '/foo')
    expected = '/foo/'
    actual =  response.headers['Location']
    assert actual == expected

def test_trailing_on_virtual_paths_missing(harness):
    harness.fs.www.mk('%foo/%bar/%baz',)
    response = assert_raises_302(harness, '/foo/bar/baz')
    expected = '/foo/bar/baz/'
    actual = response.headers['Location']
    assert actual == expected

def test_trailing_on_virtual_paths(harness):
    harness.fs.www.mk(('%foo/%bar/%baz/index.html', "Greetings program!"),)
    assert_fs(harness, '/foo/bar/baz/', '/%foo/%bar/%baz/index.html')

def test_dont_confuse_files_for_dirs(harness):
    harness.fs.www.mk(('foo.html', 'Greetings, Program!'),)
    assert_raises_404(harness, '/foo.html/bar')


# path part params
# ================

def test_path_part_with_params_works(harness):
    harness.fs.www.mk(('foo/index.html', "Greetings program!"),)
    assert_fs(harness, '/foo;a=1/', '/foo/index.html')

def test_path_part_params_vpath(harness):
    harness.fs.www.mk(('%bar/index.html', "Greetings program!"),)
    assert_fs(harness, '/foo;a=1;b=;a=2;b=3/', '/%bar/index.html')

def test_path_part_params_static_file(harness):
    harness.fs.www.mk(('/foo/bar.html', "Greetings program!"),)
    assert_fs(harness, '/foo/bar.html;a=1;b=;a=2;b=3', '/foo/bar.html')

def test_path_part_params_simplate(harness):
    harness.fs.www.mk(('/foo/bar.html.spt', "Greetings program!"),)
    assert_fs(harness, '/foo/bar.html;a=1;b=;a=2;b=3', '/foo/bar.html.spt')

def test_path_part_params_negotiated_simplate(harness):
    harness.fs.www.mk(('/foo/bar.spt', NEGOTIATED_SIMPLATE),)
    assert_fs(harness, '/foo/bar.txt;a=1;b=;a=2;b=3', '/foo/bar.spt')

def test_path_part_params_greedy_simplate(harness):
    harness.fs.www.mk(('/foo/%bar.spt', NEGOTIATED_SIMPLATE),)
    assert_fs(harness, '/foo/baz/buz;a=1;b=;a=2;b=3/blam.html', '/foo/%bar.spt')


# Docs
# ====

GREETINGS_NAME_SPT = """
[-----]
name = path['name']
[------]
Greetings, %(name)s!"""

def test_virtual_path_docs_1(harness):
    harness.fs.www.mk(('%name/index.html.spt', GREETINGS_NAME_SPT),)
    assert_body(harness, '/aspen/', 'Greetings, aspen!')

def test_virtual_path_docs_2(harness):
    harness.fs.www.mk(('%name/index.html.spt', GREETINGS_NAME_SPT),)
    assert_body(harness, '/python/', 'Greetings, python!')

NAME_LIKES_CHEESE_SPT = """
name = path['name'].title()
cheese = path['cheese']
[---------]
%(name)s likes %(cheese)s cheese."""

def test_virtual_path_docs_3(harness):
    harness.fs.www.mk( ( '%name/index.html.spt', GREETINGS_NAME_SPT)
          , ( '%name/%cheese.txt.spt', NAME_LIKES_CHEESE_SPT)
           )
    assert_body(harness, '/chad/cheddar.txt', "Chad likes cheddar cheese.")

def test_virtual_path_docs_4(harness):
    harness.fs.www.mk( ('%name/index.html.spt', GREETINGS_NAME_SPT)
          , ('%name/%cheese.txt.spt', NAME_LIKES_CHEESE_SPT)
           )
    assert_raises_404(harness, '/chad/cheddar.txt/')

PARTY_LIKE_YEAR_SPT = "year = path['year']\n[----------]\nTonight we're going to party like it's %(year)s!"

def test_virtual_path_docs_5(harness):
    harness.fs.www.mk( ('%name/index.html.spt', GREETINGS_NAME_SPT)
          , ('%name/%cheese.txt.spt', NAME_LIKES_CHEESE_SPT)
          , ('%year.int/index.html.spt', PARTY_LIKE_YEAR_SPT)
           )
    assert_body(harness, '/1999/', 'Greetings, 1999!')

def test_virtual_path_docs_6(harness):
    harness.fs.www.mk(('%year.int/index.html.spt', PARTY_LIKE_YEAR_SPT),)
    assert_body(harness, '/1999/', "Tonight we're going to party like it's 1999!")


# mongs
# =====
# These surfaced when porting mongs from Aspen 0.8.

def test_virtual_path_parts_can_be_empty(harness):
    harness.fs.www.mk(('foo/%bar/index.html.spt', "Greetings, program!"),)
    assert_virtvals(harness, '/foo//' , {u'bar': [u'']})

def test_file_matches_in_face_of_dir(harness):
    harness.fs.www.mk( ('%page/index.html.spt', 'Nothing to see here.')
          , ('%value.txt.spt', "Greetings, program!")
           )
    assert_virtvals(harness, '/baz.txt', {'value': [u'baz']})

def test_file_matches_extension(harness):
    harness.fs.www.mk( ('%value.json.spt', '[-----]\n{"Greetings,": "program!"}')
          , ('%value.txt.spt', "Greetings, program!")
           )
    assert_fs(harness, '/baz.json', "%value.json.spt")

def test_file_matches_other_extension(harness):
    harness.fs.www.mk( ('%value.json.spt', '[-----]\n{"Greetings,": "program!"}')
          , ('%value.txt.spt', "Greetings, program!")
           )
    assert_fs(harness, '/baz.txt', "%value.txt.spt")


def test_virtual_file_with_no_extension_works(harness):
    harness.fs.www.mk(('%value.spt', NEGOTIATED_SIMPLATE),)
    assert_fs(harness, '/baz.txt', '%value.spt')

def test_normal_file_with_no_extension_works(harness):
    harness.fs.www.mk( ('%value.spt', NEGOTIATED_SIMPLATE)
          , ('value', '{"Greetings,": "program!"}')
           )
    assert_fs(harness, '/baz.txt', '%value.spt')

def test_file_with_no_extension_matches(harness):
    harness.fs.www.mk( ('%value.spt', NEGOTIATED_SIMPLATE)
          , ('value', '{"Greetings,": "program!"}')
           )
    assert_fs(harness, '/baz', '%value.spt')
    assert_virtvals(harness, '/baz', {'value': [u'baz']})

def test_aspen_favicon_doesnt_get_clobbered_by_virtual_path(harness):
    harness.fs.www.mk(('%value.html.spt', NEGOTIATED_SIMPLATE),)
    actual = harness.simple(uripath='/favicon.ico', filepath=None, want='request.fs')
    assert actual == os.path.join(os.path.dirname(aspen.__file__), 'www', 'favicon.ico')

def test_robots_txt_also_shouldnt_be_redirected(harness):
    harness.fs.www.mk(('%value.html.spt', ''),)
    assert_raises_404(harness, '/robots.txt')

def test_dont_serve_hidden_files(harness):
    harness.fs.www.mk(('.secret_data', ''),)
    assert_raises_404(harness, '/.secret_data')

def test_dont_serve_spt_file_source(harness):
    harness.fs.www.mk(('foo.html.spt', "Greetings, program!"),)
    assert_raises_404(harness, '/foo.html.spt')


########NEW FILE########
__FILENAME__ = test_httpbasic
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from pytest import raises, yield_fixture

from aspen.http.response import Response
from aspen.auth.httpbasic import inbound_responder

import base64

# convenience functions

def _auth_header(username, password):
    """return the value part of an Authorization: header for basic auth with the specified username and password"""
    return "Basic " + base64.b64encode(username + ":" + password)

# tests

@yield_fixture
def request_with(harness):
    def request_with(authfunc, auth_header):
        harness.client.website.algorithm.insert_after( 'parse_environ_into_request'
                                                     , inbound_responder(authfunc)
                                                      )
        return harness.simple( filepath=None
                             , return_after='httpbasic_inbound_responder'
                             , want='request'
                             , HTTP_AUTHORIZATION=auth_header
                              )
    yield request_with

def test_good_works(request_with):
    request = request_with( lambda u, p: u == "username" and p == "password"
                          , _auth_header("username", "password")
                           )
    success = request.auth.authorized()
    assert success
    assert request.auth.username() == "username", request.auth.username()

def test_hard_passwords(request_with):
    for password in [ 'pass', 'username', ':password', ':password:','::::::' ]:
        request = request_with( lambda u, p: u == "username" and p == password
                              , _auth_header("username"
                              , password)
                               )
        success = request.auth.authorized()
        assert success
        assert request.auth.username() == "username", request.auth.username()

def test_no_auth(request_with):
    auth = lambda u, p: u == "username" and p == "password"
    response = raises(Response, request_with, auth, None).value
    assert response.code == 401, response

def test_bad_fails(request_with):
    auth = lambda u, p: u == "username" and p == "password"
    response = raises(Response, request_with, auth, _auth_header("username", "wrong password")).value
    assert response.code == 401, response

def test_wrong_auth(request_with):
    auth = lambda u, p: u == "username" and p == "password"
    response = raises(Response, request_with, auth, "Wacky xxx").value
    assert response.code == 400

def test_malformed_password(request_with):
    auth = lambda u, p: u == "username" and p == "password"
    response = raises( Response
                     , request_with
                     , auth
                     , "Basic " + base64.b64encode("usernamepassword")
                      ).value
    assert response.code == 400
    response = raises(Response, request_with, auth, "Basic xxx").value
    assert response.code == 400

########NEW FILE########
__FILENAME__ = test_httpdigest
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from pytest import raises, yield_fixture

from aspen.http.response import Response
from aspen.auth.httpdigest import inbound_responder, digest

import base64

# convenience functions

def _auth_func(username, password):
    def _(user, realm):
        if user != username:
            raise KeyError
        return digest(':'.join([username, realm, password]))
    return _

def _auth_header(username, password):
    """return the value part of an Authorization: header for basic auth with the specified username and password"""
    return "Basic " + base64.b64encode(username + ":" + password)

def _auth_headers(response):
    wwwauth = response.headers['WWW-Authenticate']
    assert wwwauth.startswith('Digest')
    assert wwwauth.endswith('"')
    keyvals = wwwauth[len('Digest '):-1].split('",')
    return dict([kval.strip().split('="')  for kval in keyvals])


def _digest_auth_for(headers, username, password):
    fields = { 'qop': 'auth',
               'uri': '/',
               'nc':'00000001',
               'cnonce':'FFFFFFFF',
               'username' : username
             }
    for k in [ 'realm', 'nonce', 'opaque' ]:
        fields[k] = headers[k]
    HA1 = digest( username + ':' + fields['realm'] + ':' + password )
    HA2 = digest( 'GET:' + fields['uri'] )
    fields['response'] = digest( ':'.join([ HA1, fields['nonce'], fields['nc'], fields['cnonce'], fields['qop'], HA2 ]))
    return "Digest " + ','.join([ '%s="%s"' % (k, v) for k, v in fields.items() ])

@yield_fixture
def request_with(harness):
    def request_with(auth_header, inbound_auther):
        harness.client.website.algorithm.insert_after( 'parse_environ_into_request'
                                                     , inbound_auther
                                                      )
        return harness.simple( filepath=None
                             , return_after='httpdigest_inbound_responder'
                             , want='request'
                             , HTTP_AUTHORIZATION=auth_header
                              )
    yield request_with


# tests

def test_good_works(request_with):
    # once to get a WWW-Authenticate header
    auth_func = _auth_func("username", "password")
    auther = inbound_responder(auth_func, realm="testrealm@host.com")
    response = raises(Response, request_with, '', auther).value
    # do something with the header
    auth_headers = _auth_headers(response)
    http_authorization = _digest_auth_for(auth_headers, "username", "password")
    request = request_with(http_authorization, auther)
    assert request.auth.authorized()
    assert request.auth.username() == "username"

#def test_hard_passwords():
#    for password in [ 'pass', 'username', ':password', ':password:','::::::' ]:
#        request = _request_with(_auth_func("username", "password"), _auth_header("username", "password"))
#        success = request.auth.authorized()
#        assert success
#        assert request.auth.username() == "username", request.auth.username()

def test_bad_fails(request_with):
    # once to get a WWW-Authenticate header
    auther = inbound_responder(_auth_func("username", "password"), realm="testrealm@host.com")
    response = raises(Response, request_with, '', auther).value
    # do something with the header
    auth_headers = _auth_headers(response)
    http_authorization = _digest_auth_for(auth_headers, "username", "badpassword")
    response = raises(Response, request_with, http_authorization, auther).value
    assert response.code == 401
    assert not response.request.auth.authorized()

def test_no_auth(request_with):
    auth = lambda u, p: u == "username" and p == "password"
    auther = inbound_responder(auth, realm="testrealm@host.com")
    response = raises(Response, request_with, None, auther).value
    assert response.code == 401, response

def test_wrong_auth(request_with):
    auth = lambda u, p: u == "username" and p == "password"
    auther = inbound_responder(auth, realm="testrealm@host.com")
    response = raises(Response, request_with, "Wacky xxx", auther).value
    assert response.code == 400, response

########NEW FILE########
__FILENAME__ = test_json_resource
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import StringIO

from pytest import raises

from aspen import json


def test_json_basically_works(harness):
    expected = '''{
    "Greetings": "program!"
}'''
    actual = harness.simple( "[---] application/json\n{'Greetings': 'program!'}"
                           , filepath="foo.json.spt"
                            ).body
    assert actual == expected

def test_json_defaults_to_application_json_for_static_json(harness):
    actual = harness.simple( '{"Greetings": "program!"}'
                           , filepath="foo.json"
                            ).headers['Content-Type']
    assert actual == 'application/json'

def test_json_content_type_is_configurable_for_static_json(harness):
    harness.fs.project.mk(('configure-aspen.py', 'website.media_type_json = "floober/blah"'))
    expected = 'floober/blah'
    actual = harness.simple( '{"Greetings": "program!"}'
                           , filepath="foo.json"
                            ).headers['Content-Type']
    assert actual == expected

def test_json_content_type_is_configurable_from_the_command_line(harness):
    actual = harness.simple( '{"Greetings": "program!"}'
                           , filepath="foo.json"
                           , argv=['--media_type_json=floober/blah']
                            ).headers['Content-Type']
    assert actual == 'floober/blah'

def test_json_content_type_is_configurable_for_dynamic_json(harness):
    harness.fs.project.mk(('configure-aspen.py', 'website.media_type_json = "floober/blah"'))
    actual = harness.simple( "[---] floober/blah\n{'Greetings': 'program!'}"
                           , filepath="foo.json.spt"
                            ).headers['Content-Type']
    assert actual == 'floober/blah'

def test_json_content_type_is_per_file_configurable(harness):
    expected = 'floober/blah'
    actual = harness.simple('''
        response.headers['Content-type'] = 'floober/blah'
        [---] floober/blah
        {'Greetings': 'program!'}
    ''', filepath="foo.json.spt").headers['Content-Type']
    assert actual == expected

def test_json_handles_unicode(harness):
    expected = b'''{
    "Greetings": "\u00b5"
}'''
    actual = harness.simple('''
        [---] application/json
        {'Greetings': unichr(181)}
    ''', filepath="foo.json.spt").body
    assert actual == expected

def test_json_doesnt_handle_non_ascii_bytestrings(harness):
    raises( UnicodeDecodeError
          , harness.simple
          , "[---] application/json\n{'Greetings': chr(181)}"
          , filepath="foo.json.spt"
           )

def test_json_handles_time(harness):
    expected = '''{
    "seen": "19:30:00"
}'''
    actual = harness.simple('''
        import datetime
        [---------------] application/json
        {'seen': datetime.time(19, 30)}
    ''', filepath="foo.json.spt").body
    assert actual == expected

def test_json_handles_date(harness):
    expected = '''{
    "created": "2011-05-09"
}'''
    actual = harness.simple('''
        import datetime
        [---------------] application/json
        {'created': datetime.date(2011, 5, 9)}
    ''', filepath='foo.json.spt').body
    assert actual == expected

def test_json_handles_datetime(harness):
    expected = '''{
    "timestamp": "2011-05-09T00:00:00"
}'''
    actual = harness.simple("""
        import datetime
        [---------------] application/json
        {'timestamp': datetime.datetime(2011, 5, 9, 0, 0)}
    """, filepath="foo.json.spt").body
    assert actual == expected

def test_json_handles_complex(harness):
    expected = '''{
    "complex": [
        1.0,
        2.0
    ]
}'''
    actual = harness.simple( "[---] application/json\n{'complex': complex(1,2)}"
                           , filepath="foo.json.spt"
                            ).body
    # The json module puts trailing spaces after commas, but simplejson
    # does not. Normalize the actual input to work around that.
    actual = '\n'.join([line.rstrip() for line in actual.split('\n')])
    assert actual == expected

def test_json_raises_TypeError_on_unknown_types(harness):
    raises( TypeError
          , harness.simple
          , contents='class Foo: pass\n[---] application/json\nFoo()'
          , filepath='foo.json.spt'
           )

def test_aspen_json_load_loads():
    fp = StringIO.StringIO()
    fp.write('{"cheese": "puffs"}')
    fp.seek(0)
    actual = json.load(fp)
    assert actual == {'cheese': 'puffs'}

def test_aspen_json_dump_dumps():
    fp = StringIO.StringIO()
    json.dump({"cheese": "puffs"}, fp)
    fp.seek(0)
    actual = fp.read()
    assert actual == '''{
    "cheese": "puffs"
}'''

def test_aspen_json_loads_loads():
    actual = json.loads('{"cheese": "puffs"}')
    assert actual == {'cheese': 'puffs'}

def test_aspen_json_dumps_dumps():
    actual = json.dumps({'cheese': 'puffs'})
    assert actual == '''{
    "cheese": "puffs"
}'''

########NEW FILE########
__FILENAME__ = test_logging
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import re
import sys
from StringIO import StringIO

import aspen.logging
from aspen.logging import log, log_dammit


pat = re.compile("pid-\d* thread--?\d* \(MainThread\) (.*)")
def capture(*a, **kw):
    """This is a fixture function to capture log output.

    Positional and keyword arguments are passed through to a logging function
    with these exceptions, which are pulled out of kw before that is passed
    through to the logging function:

        func        the logging function to use, defaults to log
        threshold   where to set the logging threshold; it will be reset to its
                     previous value after the output of func is captured

    """
    func = kw.pop('func') if 'func' in kw else log
    try:
        __threshold__ = aspen.logging.LOGGING_THRESHOLD
        if 'threshold' in kw:
            aspen.logging.LOGGING_THRESHOLD = kw.pop('threshold')
        sys.stdout = StringIO()
        func(*a, **kw)
        output = sys.stdout.getvalue()
    finally:
        aspen.logging.LOGGING_THRESHOLD = __threshold__
        sys.stdout = sys.__stdout__
    return pat.findall(output)


def test_log_logs_something():
    actual = capture("oh heck", level=4)
    assert actual == ["oh heck"]

def test_log_logs_several_somethings():
    actual = capture("oh\nheck", u"what?", {}, [], None, level=4)
    assert actual == ["oh", "heck", "what?", "{}", "[]", "None"]

def test_log_dammit_works():
    actual = capture("yes\nrly", {}, [], None, threshold=1, func=log_dammit)
    assert actual == ["yes", "rly", "{}", "[]", "None"]

def test_logging_unicode_works():
    actual = capture("oh \u2614 heck", level=4)
    assert actual == ["oh \u2614 heck"]


########NEW FILE########
__FILENAME__ = test_mappings
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from pytest import raises

from aspen import Response

from aspen.http.mapping import Mapping, CaseInsensitiveMapping

from aspen.http.baseheaders import BaseHeaders
from aspen.http.request import Querystring



def test_mapping_subscript_assignment_clobbers():
    m = Mapping()
    m['foo'] = 'bar'
    m['foo'] = 'baz'
    m['foo'] = 'buz'
    expected = ['buz']
    actual = dict.__getitem__(m, 'foo')
    assert actual == expected

def test_mapping_subscript_access_returns_last():
    m = Mapping()
    m['foo'] = 'bar'
    m['foo'] = 'baz'
    m['foo'] = 'buz'
    expected = 'buz'
    actual = m['foo']
    assert actual == expected

def test_mapping_get_returns_last():
    m = Mapping()
    m['foo'] = 'bar'
    m['foo'] = 'baz'
    m['foo'] = 'buz'
    expected = 'buz'
    actual = m.get('foo')
    assert actual == expected

def test_mapping_get_returns_default():
    m = Mapping()
    expected = 'cheese'
    actual = m.get('foo', 'cheese')
    assert actual == expected

def test_mapping_get_default_default_is_None():
    m = Mapping()
    expected = None
    actual = m.get('foo')
    assert actual is expected

def test_mapping_all_returns_list_of_all_values():
    m = Mapping()
    m['foo'] = 'bar'
    m.add('foo', 'baz')
    m.add('foo', 'buz')
    expected = ['bar', 'baz', 'buz']
    actual = m.all('foo')
    assert actual == expected

def test_mapping_ones_returns_list_of_last_values():
    m = Mapping()
    m['foo'] = 1
    m['foo'] = 2
    m['bar'] = 3
    m['bar'] = 4
    m['bar'] = 5
    m['baz'] = 6
    m['baz'] = 7
    m['baz'] = 8
    m['baz'] = 9
    expected = [2, 5, 9]
    actual = m.ones('foo', 'bar', 'baz')
    assert actual == expected

def test_mapping_deleting_a_key_removes_it_entirely():
    m = Mapping()
    m['foo'] = 1
    m['foo'] = 2
    m['foo'] = 3
    del m['foo']
    assert 'foo' not in m

def test_accessing_missing_key_raises_Response():
    m = Mapping()
    raises(Response, lambda k: m[k], 'foo')

def test_mapping_calling_ones_with_missing_key_raises_Response():
    m = Mapping()
    raises(Response, m.ones, 'foo')

def test_mapping_pop_returns_the_last_item():
    m = Mapping()
    m['foo'] = 1
    m.add('foo', 1)
    m.add('foo', 3)
    expected = 3
    actual = m.pop('foo')
    assert actual == expected

def test_mapping_pop_leaves_the_rest():
    m = Mapping()
    m['foo'] = 1
    m.add('foo', 1)
    m.add('foo', 3)
    m.pop('foo')
    expected = [1, 1]
    actual = m.all('foo')
    assert actual == expected

def test_mapping_pop_removes_the_item_if_that_was_the_last_value():
    m = Mapping()
    m['foo'] = 1
    m.pop('foo')
    expected = []
    actual = m.keys()
    assert actual == expected

def test_mapping_popall_returns_a_list():
    m = Mapping()
    m['foo'] = 1
    m.add('foo', 1)
    m.add('foo', 3)
    expected = [1, 1, 3]
    actual = m.popall('foo')
    assert actual == expected

def test_mapping_popall_removes_the_item():
    m = Mapping()
    m['foo'] = 1
    m['foo'] = 1
    m['foo'] = 3
    m.popall('foo')
    assert 'foo' not in m


def test_default_mapping_is_case_insensitive():
    m = Mapping()
    m['Foo'] = 1
    m['foo'] = 1
    m['fOO'] = 1
    m['FOO'] = 1
    expected = [1]
    actual = m.all('foo')
    assert actual == expected

def test_case_insensitive_mapping_access_is_case_insensitive():
    m = CaseInsensitiveMapping()
    m['Foo'] = 1
    m['foo'] = 1
    m['fOO'] = 1
    m['FOO'] = 11
    expected = 11
    actual = m['foo']
    assert actual == expected

def test_case_insensitive_mapping_get_is_case_insensitive():
    m = CaseInsensitiveMapping()
    m['Foo'] = 1
    m['foo'] = 11
    m['fOO'] = 1
    m['FOO'] = 1
    expected = 1
    actual = m.get('foo')
    assert actual == expected

def test_case_insensitive_mapping_all_is_case_insensitive():
    m = CaseInsensitiveMapping()
    m['Foo'] = 1
    m.add('foo', 1)
    m.add('fOO', 1)
    m.add('FOO', 1)
    expected = [1, 1, 1, 1]
    actual = m.all('foo')
    assert actual == expected

def test_case_insensitive_mapping_pop_is_case_insensitive():
    m = CaseInsensitiveMapping()
    m['Foo'] = 1
    m['foo'] = 99
    m['fOO'] = 1
    m['FOO'] = 11
    expected = 11
    actual = m.pop('foo')
    assert actual == expected

def test_case_insensitive_mapping_popall_is_case_insensitive():
    m = CaseInsensitiveMapping()
    m['Foo'] = 1
    m.add('foo', 99)
    m.add('fOO', 1)
    m.add('FOO', 11)
    expected = [1, 99, 1, 11]
    actual = m.popall('foo')
    assert actual == expected

def test_case_insensitive_mapping_ones_is_case_insensitive():
    m = CaseInsensitiveMapping()
    m['Foo'] = 1
    m.add('foo', 8)
    m.add('fOO', 9)
    m.add('FOO', 12)
    m['bar'] = 2
    m.add('BAR', 200)
    expected = [12, 200]
    actual = m.ones('Foo', 'Bar')
    assert actual == expected


def est_headers_are_case_insensitive():
    headers = BaseHeaders('Foo: bar')
    expected = 'bar'
    actual = headers.one('foo')
    assert actual == expected

def est_querystring_basically_works():
    querystring = Querystring('Foo=bar')
    expected = 'bar'
    actual = querystring.one('Foo', default='missing')
    assert actual == expected

def est_querystring_is_case_sensitive():
    querystring = Querystring('Foo=bar')
    expected = 'missing'
    actual = querystring.one('foo', default='missing')
    assert actual == expected




########NEW FILE########
__FILENAME__ = test_negotiated_resource
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from pytest import raises, yield_fixture

from aspen import resources, Response
from aspen.resources.pagination import Page
from aspen.resources.negotiated_resource import NegotiatedResource
from aspen.renderers.stdlib_template import Factory as TemplateFactory
from aspen.renderers.stdlib_percent import Factory as PercentFactory


@yield_fixture
def get(harness):
    def get(**_kw):
        kw = dict( website = harness.client.website
                 , fs = ''
                 , raw = '[---]\n[---] text/plain via stdlib_template\n'
                 , media_type = ''
                 , mtime = 0
                  )
        kw.update(_kw)
        return NegotiatedResource(**kw)
    yield get


def test_negotiated_resource_is_instantiable(harness):
    website = harness.client.website
    fs = ''
    raw = '[---]\n[---] text/plain via stdlib_template\n'
    media_type = ''
    mtime = 0
    actual = NegotiatedResource(website, fs, raw, media_type, mtime).__class__
    assert actual is NegotiatedResource


# compile_page

def test_compile_page_chokes_on_truly_empty_page(get):
    raises(SyntaxError, get().compile_page, Page(''))

def test_compile_page_compiles_empty_page(get):
    page = get().compile_page(Page('', 'text/html'))
    actual = page[0]({}), page[1]
    assert actual == ('', 'text/html')

def test_compile_page_compiles_page(get):
    page = get().compile_page(Page('foo bar', 'text/html'))
    actual = page[0]({}), page[1]
    assert actual == ('foo bar', 'text/html')


# _parse_specline

def test_parse_specline_parses_specline(get):
    factory, media_type = get()._parse_specline('media/type via stdlib_template')
    actual = (factory.__class__, media_type)
    assert actual == (TemplateFactory, 'media/type')

def test_parse_specline_doesnt_require_renderer(get):
    factory, media_type = get()._parse_specline('media/type')
    actual = (factory.__class__, media_type)
    assert actual == (PercentFactory, 'media/type')

def test_parse_specline_requires_media_type(get):
    raises(SyntaxError, get()._parse_specline, 'via stdlib_template')

def test_parse_specline_raises_SyntaxError_if_renderer_is_malformed(get):
    raises(SyntaxError, get()._parse_specline, 'stdlib_template media/type')

def test_parse_specline_raises_SyntaxError_if_media_type_is_malformed(get):
    raises(SyntaxError, get()._parse_specline, 'media-type via stdlib_template')

def test_parse_specline_cant_mistake_malformed_media_type_for_renderer(get):
    raises(SyntaxError, get()._parse_specline, 'media-type')

def test_parse_specline_cant_mistake_malformed_renderer_for_media_type(get):
    raises(SyntaxError, get()._parse_specline, 'stdlib_template')

def test_parse_specline_enforces_order(get):
    raises(SyntaxError, get()._parse_specline, 'stdlib_template via media/type')

def test_parse_specline_obeys_default_by_media_type(get):
    resource = get()
    resource.website.default_renderers_by_media_type['media/type'] = 'glubber'
    err = raises(ValueError, resource._parse_specline, 'media/type').value
    msg = err.args[0]
    assert msg.startswith("Unknown renderer for media/type: glubber."), msg

def test_parse_specline_obeys_default_by_media_type_default(get):
    resource = get()
    resource.website.default_renderers_by_media_type.default_factory = lambda: 'glubber'
    err = raises(ValueError, resource._parse_specline, 'media/type').value
    msg = err.args[0]
    assert msg.startswith("Unknown renderer for media/type: glubber.")

def test_get_renderer_factory_can_raise_syntax_error(get):
    resource = get()
    resource.website.default_renderers_by_media_type['media/type'] = 'glubber'
    err = raises( SyntaxError
                       , resource._get_renderer_factory
                       , 'media/type'
                       , 'oo*gle'
                        ).value
    msg = err.args[0]
    assert msg.startswith("Malformed renderer oo*gle. It must match")


# get_response

def get_response(request, response):
    context = { 'request': request
              , 'response': response
               }
    resource = resources.load(request, 0)
    return resource.get_response(context)

NEGOTIATED_RESOURCE = """\
[---]
[---] text/plain
Greetings, program!
[---] text/html
<h1>Greetings, program!</h1>
"""

def test_get_response_gets_response(harness):
    harness.fs.www.mk(('index.spt', NEGOTIATED_RESOURCE))
    response = Response()
    request = harness.make_request(filepath='index.spt', contents=NEGOTIATED_RESOURCE)
    actual = get_response(request, response)
    assert actual is response

def test_get_response_is_happy_not_to_negotiate(harness):
    harness.fs.www.mk(('index.spt', NEGOTIATED_RESOURCE))
    request = harness.make_request(filepath='index.spt', contents=NEGOTIATED_RESOURCE)
    actual = get_response(request, Response()).body
    assert actual == "Greetings, program!\n"

def test_get_response_sets_content_type_when_it_doesnt_negotiate(harness):
    harness.fs.www.mk(('index.spt', NEGOTIATED_RESOURCE))
    request = harness.make_request(filepath='index.spt', contents=NEGOTIATED_RESOURCE)
    actual = get_response(request, Response()).headers['Content-Type']
    assert actual == "text/plain; charset=UTF-8"

def test_get_response_doesnt_reset_content_type_when_not_negotiating(harness):
    harness.fs.www.mk(('index.spt', NEGOTIATED_RESOURCE))
    request = harness.make_request(filepath='index.spt', contents=NEGOTIATED_RESOURCE)
    response = Response()
    response.headers['Content-Type'] = 'never/mind'
    actual = get_response(request, response).headers['Content-Type']
    assert actual == "never/mind"

def test_get_response_negotiates(harness):
    harness.fs.www.mk(('index.spt', NEGOTIATED_RESOURCE))
    request = harness.make_request(filepath='index.spt', contents=NEGOTIATED_RESOURCE)
    request.headers['Accept'] = 'text/html'
    actual = get_response(request, Response()).body
    assert actual == "<h1>Greetings, program!</h1>\n"

def test_handles_busted_accept(harness):
    harness.fs.www.mk(('index.spt', NEGOTIATED_RESOURCE))
    request = harness.make_request(filepath='index.spt', contents=NEGOTIATED_RESOURCE)
    # Set an invalid Accept header so it will return default (text/plain)
    request.headers['Accept'] = 'text/html;'
    actual = get_response(request, Response()).body
    assert actual == "Greetings, program!\n"

def test_get_response_sets_content_type_when_it_negotiates(harness):
    harness.fs.www.mk(('index.spt', NEGOTIATED_RESOURCE))
    request = harness.make_request(filepath='index.spt', contents=NEGOTIATED_RESOURCE)
    request.headers['Accept'] = 'text/html'
    actual = get_response(request, Response()).headers['Content-Type']
    assert actual == "text/html; charset=UTF-8"

def test_get_response_doesnt_reset_content_type_when_negotiating(harness):
    harness.fs.www.mk(('index.spt', NEGOTIATED_RESOURCE))
    request = harness.make_request(filepath='index.spt', contents=NEGOTIATED_RESOURCE)
    request.headers['Accept'] = 'text/html'
    response = Response()
    response.headers['Content-Type'] = 'never/mind'
    actual = get_response(request, response).headers['Content-Type']
    response = Response()
    response.headers['Content-Type'] = 'never/mind'
    actual = get_response(request, response).headers['Content-Type']
    assert actual == "never/mind"

def test_get_response_raises_406_if_need_be(harness):
    harness.fs.www.mk(('index.spt', NEGOTIATED_RESOURCE))
    request = harness.make_request(filepath='index.spt', contents=NEGOTIATED_RESOURCE)
    request.headers['Accept'] = 'cheese/head'
    actual = raises(Response, get_response, request, Response()).value.code
    assert actual == 406

def test_get_response_406_gives_list_of_acceptable_types(harness):
    harness.fs.www.mk(('index.spt', NEGOTIATED_RESOURCE))
    request = harness.make_request(filepath='index.spt', contents=NEGOTIATED_RESOURCE)
    request.headers['Accept'] = 'cheese/head'
    actual = raises(Response, get_response, request, Response()).value.body
    expected = "The following media types are available: text/plain, text/html."
    assert actual == expected


OVERRIDE_SIMPLATE = """\
from aspen.renderers import Renderer, Factory

class Glubber(Renderer):
    def render_content(self, context):
        return "glubber"

class GlubberFactory(Factory):
    Renderer = Glubber

website.renderer_factories['glubber'] = GlubberFactory(website)
website.default_renderers_by_media_type['text/plain'] = 'glubber'

"""


def test_can_override_default_renderers_by_mimetype(harness):
    harness.fs.project.mk(('configure-aspen.py', OVERRIDE_SIMPLATE),)
    harness.fs.www.mk(('index.spt', NEGOTIATED_RESOURCE),)
    request = harness.make_request(filepath='index.spt', contents=NEGOTIATED_RESOURCE)
    request.headers['Accept'] = 'text/plain'
    actual = get_response(request, Response()).body
    assert actual == "glubber"

def test_can_override_default_renderer_entirely(harness):
    harness.fs.project.mk(('configure-aspen.py', OVERRIDE_SIMPLATE))
    request = harness.make_request(filepath='index.spt', contents=NEGOTIATED_RESOURCE)
    request.headers['Accept'] = 'text/plain'
    actual = get_response(request, Response()).body
    assert actual == "glubber"


# indirect

INDIRECTLY_NEGOTIATED_RESOURCE = """\
[-------]
foo = "program"
[-------] text/html
<h1>Greetings, %(foo)s!</h1>
[-------] text/plain
Greetings, %(foo)s!"""

def test_indirect_negotiation_sets_media_type(harness):
    harness.fs.www.mk(('/foo.spt', INDIRECTLY_NEGOTIATED_RESOURCE))
    response = harness.client.GET('/foo.html')
    expected = "<h1>Greetings, program!</h1>\n"
    actual = response.body
    assert actual == expected

def test_indirect_negotiation_sets_media_type_to_secondary(harness):
    harness.fs.www.mk(('/foo.spt', INDIRECTLY_NEGOTIATED_RESOURCE))
    response = harness.client.GET('/foo.txt')
    expected = "Greetings, program!"
    actual = response.body
    assert actual == expected

def test_indirect_negotiation_with_unsupported_media_type_is_404(harness):
    harness.fs.www.mk(('/foo.spt', INDIRECTLY_NEGOTIATED_RESOURCE))
    response = harness.client.GxT('/foo.jpg')
    assert response.code == 404


INDIRECTLY_NEGOTIATED_VIRTUAL_RESOURCE = """\
[-------]
foo = path['foo']
[-------] text/html
<h1>Greetings, %(foo)s!</h1>
[-------] text/plain
Greetings, %(foo)s!"""


def test_negotiated_inside_virtual_path(harness):
    harness.fs.www.mk(('/%foo/bar.spt', INDIRECTLY_NEGOTIATED_VIRTUAL_RESOURCE ))
    response = harness.client.GET('/program/bar.txt')
    expected = "Greetings, program!"
    actual = response.body
    assert actual == expected

INDIRECTLY_NEGOTIATED_VIRTUAL_RESOURCE_STARTYPE = """\
[-------]
foo = path['foo']
[-------] */*
Unknown request type, %(foo)s!
[-------] text/html
<h1>Greetings, %(foo)s!</h1>
[-------] text/*
Greetings, %(foo)s!"""

def test_negotiated_inside_virtual_path_with_startypes_present(harness):
    harness.fs.www.mk(('/%foo/bar.spt', INDIRECTLY_NEGOTIATED_VIRTUAL_RESOURCE_STARTYPE ))
    response = harness.client.GET('/program/bar.html')
    actual = response.body
    assert '<h1>' in actual

def test_negotiated_inside_virtual_path_with_startype_partial_match(harness):
    harness.fs.www.mk(('/%foo/bar.spt', INDIRECTLY_NEGOTIATED_VIRTUAL_RESOURCE_STARTYPE ))
    response = harness.client.GET('/program/bar.txt')
    expected = "Greetings, program!"
    actual = response.body
    assert actual == expected

def test_negotiated_inside_virtual_path_with_startype_fallback(harness):
    harness.fs.www.mk(('/%foo/bar.spt', INDIRECTLY_NEGOTIATED_VIRTUAL_RESOURCE_STARTYPE ))
    response = harness.client.GET('/program/bar.jpg')
    expected = "Unknown request type, program!"
    actual = response.body.strip()
    assert actual == expected

########NEW FILE########
__FILENAME__ = test_request
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from pytest import raises

from aspen import Response
from aspen.http.request import kick_against_goad, Request
from aspen.http.baseheaders import BaseHeaders


def test_request_line_raw_works(harness):
    request = harness.make_request()
    actual = request.line.raw
    expected = u"GET / HTTP/1.1"
    assert actual == expected

def test_raw_is_raw():
    request = Request()
    expected = b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"
    actual = request
    assert actual == expected

def test_blank_by_default():
    raises(AttributeError, lambda: Request().version)

def test_request_line_version_defaults_to_HTTP_1_1(harness):
    request = harness.make_request()
    actual = request.line.version.info
    expected = (1, 1)
    assert actual == expected

def test_request_line_version_raw_works(harness):
    request = harness.make_request()
    actual = request.line.version.raw
    expected = u"HTTP/1.1"
    assert actual == expected

def test_allow_default_method_is_GET(harness):
    request = harness.make_request()
    expected = u'GET'
    actual = request.line.method
    assert actual == expected

def test_allow_allows_allowed(harness):
    request = harness.make_request()
    expected = None
    actual = request.allow('GET')
    assert actual is expected

def test_allow_disallows_disallowed(harness):
    request = harness.make_request()
    expected = 405
    actual = raises(Response, request.allow, 'POST').value.code
    assert actual == expected

def test_allow_can_handle_lowercase(harness):
    request = harness.make_request()
    expected = 405
    actual = raises(Response, request.allow, 'post').value.code
    assert actual == expected

def test_methods_start_with_GET(harness):
    request = harness.make_request()
    expected = "GET"
    actual = request.line.method
    assert actual == expected

def test_methods_changing_changes(harness):
    request = harness.make_request()
    request.line.method = 'POST'
    expected = "POST"
    actual = request.line.method
    assert actual == expected

def test_is_xhr_false(harness):
    request = harness.make_request()
    assert not request.is_xhr()

def test_is_xhr_true(harness):
    request = harness.make_request()
    request.headers['X-Requested-With'] = 'XmlHttpRequest'
    assert request.is_xhr()

def test_is_xhr_is_case_insensitive(harness):
    request = harness.make_request()
    request.headers['X-Requested-With'] = 'xMLhTTPrEQUEST'
    assert request.is_xhr()


def test_headers_access_gets_a_value():
    headers = BaseHeaders(b"Foo: Bar")
    expected = b"Bar"
    actual = headers['Foo']
    assert actual == expected

def test_headers_access_gets_last_value():
    headers = BaseHeaders(b"Foo: Bar\r\nFoo: Baz")
    expected = b"Baz"
    actual = headers['Foo']
    assert actual == expected

def test_headers_access_is_case_insensitive():
    headers = BaseHeaders(b"Foo: Bar")
    expected = b"Bar"
    actual = headers['foo']
    assert actual == expected

def test_headers_dont_unicodify_cookie():
    headers = BaseHeaders(b"Cookie: somecookiedata")
    expected = b"somecookiedata"
    actual = headers[b'Cookie']
    assert actual == expected


# kick_against_goad

def test_goad_passes_method_through():
    environ = {}
    environ['REQUEST_METHOD'] = b'\xdead\xbeef'
    environ['SERVER_PROTOCOL'] = b''
    environ['wsgi.input'] = None

    expected = (b'\xdead\xbeef', b'', b'', b'', b'', None)
    actual = kick_against_goad(environ)
    assert actual == expected

def test_goad_makes_franken_uri():
    environ = {}
    environ['REQUEST_METHOD'] = b''
    environ['SERVER_PROTOCOL'] = b''
    environ['PATH_INFO'] = b'/cheese'
    environ['QUERY_STRING'] = b'foo=bar'
    environ['wsgi.input'] = b''

    expected = ('', '/cheese?foo=bar', '', '', '', '')
    actual = kick_against_goad(environ)
    assert actual == expected

def test_goad_passes_version_through():
    environ = {}
    environ['REQUEST_METHOD'] = b''
    environ['SERVER_PROTOCOL'] = b'\xdead\xbeef'
    environ['wsgi.input'] = None

    expected = (b'', b'', b'', b'\xdead\xbeef', b'', None)
    actual = kick_against_goad(environ)
    assert actual == expected

def test_goad_makes_franken_headers():
    environ = {}
    environ['REQUEST_METHOD'] = b''
    environ['SERVER_PROTOCOL'] = b''
    environ['HTTP_FOO_BAR'] = b'baz=buz'
    environ['wsgi.input'] = b''

    expected = (b'', b'', b'', b'', b'FOO-BAR: baz=buz', b'')
    actual = kick_against_goad(environ)
    assert actual == expected

def test_goad_passes_body_through():
    environ = {}
    environ['REQUEST_METHOD'] = b''
    environ['SERVER_PROTOCOL'] = b''
    environ['wsgi.input'] = b'\xdead\xbeef'

    expected = (b'', b'', b'', b'', b'', b'\xdead\xbeef')
    actual = kick_against_goad(environ)
    assert actual == expected


def test_request_redirect_works_on_instance():
    request = Request()
    actual = raises(Response, request.redirect, '/').value.code
    assert actual == 302

def test_request_redirect_works_on_class():
    actual = raises(Response, Request.redirect, '/').value.code
    assert actual == 302

def test_request_redirect_code_is_settable():
    actual = raises(Response, Request.redirect, '/', code=8675309).value.code
    assert actual == 8675309

def test_request_redirect_permanent_convenience():
    actual = raises(Response, Request.redirect, '/', permanent=True).value.code
    assert actual == 301




########NEW FILE########
__FILENAME__ = test_request_body
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from StringIO import StringIO

from aspen.http.request import Body, Headers

FORMDATA = object()
WWWFORM = object()

def make_body(raw, headers=None, content_type=WWWFORM):
    if isinstance(raw, unicode):
        raw = raw.encode('ascii')
    if headers is None:
        if content_type is FORMDATA:
            content_type = "multipart/form-data; boundary=AaB03x"
        elif content_type is WWWFORM:
            content_type = "application/x-www-form-urlencoded"
        headers = {"Content-Type": content_type}
    if not 'content-length' in headers:
        headers['Content-length'] = str(len(raw))
    headers['Host'] = 'Blah'
    return Body( Headers(headers)
               , StringIO(raw)
               , b""
                )


def test_body_is_instantiable():
    body = make_body("cheese=yes")
    actual = body.__class__.__name__
    assert actual == "Body"

def test_body_is_unparsed_for_empty_content_type():
    actual = make_body("cheese=yes", headers={})
    assert actual == {}

def test_body_gives_empty_dict_for_empty_body():
    actual = make_body("")
    assert actual == {}

def test_body_barely_works():
    body = make_body("cheese=yes")
    actual = body['cheese']
    assert actual == "yes"


UPLOAD = """\
--AaB03x
Content-Disposition: form-data; name="submit-name"

Larry
--AaB03x
Content-Disposition: form-data; name="files"; filename="file1.txt"
Content-Type: text/plain

... contents of file1.txt ...
--AaB03x--
"""

def test_body_barely_works_for_form_data():
    body = make_body(UPLOAD, content_type=FORMDATA)
    actual = body['files'].filename
    assert actual == "file1.txt"

def test_simple_values_are_simple():
    body = make_body(UPLOAD, content_type=FORMDATA)
    actual = body['submit-name']
    assert actual == "Larry"

def test_params_doesnt_break_www_form():
    body = make_body("statement=foo"
                    , content_type="application/x-www-form-urlencoded; charset=UTF-8; cheese=yummy"
                     )
    actual = body['statement']
    assert actual == "foo"

########NEW FILE########
__FILENAME__ = test_request_line
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from pytest import raises

from aspen import Response
from aspen.http.request import Request
from aspen.http.mapping import Mapping
from aspen.http.request import Line, Method, URI, Version, Path, Querystring


# Line
# ====

def test_line_works():
    line = Line("GET", "/", "HTTP/0.9")
    assert line == u"GET / HTTP/0.9"

def test_line_has_method():
    line = Line("GET", "/", "HTTP/0.9")
    assert line.method == u"GET"

def test_line_has_uri():
    line = Line("GET", "/", "HTTP/0.9")
    assert line.uri == u"/"

def test_line_has_version():
    line = Line("GET", "/", "HTTP/0.9")
    assert line.version == u"HTTP/0.9"

def test_line_chokes_on_non_ASCII_in_uri():
    raises(UnicodeDecodeError, Line, "GET", chr(128), "HTTP/1.1")


# Method
# ======

def test_method_works():
    method = Method("GET")
    assert method == u"GET"

def test_method_is_unicode_subclass():
    method = Method("GET")
    assert issubclass(method.__class__, unicode)

def test_method_is_unicode_instance():
    method = Method("GET")
    assert isinstance(method, unicode)

def test_method_is_basestring_instance():
    method = Method("GET")
    assert isinstance(method, basestring)

def test_method_raw_works():
    method = Method("GET")
    assert method.raw == "GET"

def test_method_raw_is_bytestring():
    method = Method(b"GET")
    assert isinstance(method.raw, str)

def test_method_cant_have_more_attributes():
    method = Method("GET")
    raises(AttributeError, setattr, method, "foo", "bar")

def test_method_can_be_OPTIONS(): assert Method("OPTIONS") == u"OPTIONS"
def test_method_can_be_GET():     assert Method("GET")     == u"GET"
def test_method_can_be_HEAD():    assert Method("HEAD")    == u"HEAD"
def test_method_can_be_POST():    assert Method("POST")    == u"POST"
def test_method_can_be_PUT():     assert Method("PUT")     == u"PUT"
def test_method_can_be_DELETE():  assert Method("DELETE")  == u"DELETE"
def test_method_can_be_TRACE():   assert Method("TRACE")   == u"TRACE"
def test_method_can_be_CONNECT(): assert Method("CONNECT") == u"CONNECT"

def test_method_can_be_big():
    big = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz--"
    assert Method(big) == big

def test_method_we_cap_it_at_64_bytes_just_cause____I_mean___come_on___right():
    big = b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz--!"
    assert raises(Response, Method, big).value.code == 501

def test_method_cant_be_non_ASCII():
    assert raises(Response, Method, b"\x80").value.code == 501

def test_method_can_be_valid_perl():
    assert Method("!#$%&'*+-.^_`|~") == u"!#$%&'*+-.^_`|~"

def the501(i):
    assert raises(Response, Method, chr(i)).value.code == 501

# 0-31
def test_method_no_chr_0(): the501(0)
def test_method_no_chr_1(): the501(1)
def test_method_no_chr_2(): the501(2)
def test_method_no_chr_3(): the501(3)
def test_method_no_chr_4(): the501(4)
def test_method_no_chr_5(): the501(5)
def test_method_no_chr_6(): the501(6)
def test_method_no_chr_7(): the501(7)
def test_method_no_chr_8(): the501(8)
def test_method_no_chr_9(): the501(9)

def test_method_no_chr_10(): the501(10)
def test_method_no_chr_11(): the501(11)
def test_method_no_chr_12(): the501(12)
def test_method_no_chr_13(): the501(13)
def test_method_no_chr_14(): the501(14)
def test_method_no_chr_15(): the501(15)
def test_method_no_chr_16(): the501(16)
def test_method_no_chr_17(): the501(17)
def test_method_no_chr_18(): the501(18)
def test_method_no_chr_19(): the501(19)

def test_method_no_chr_20(): the501(20)
def test_method_no_chr_21(): the501(21)
def test_method_no_chr_22(): the501(22)
def test_method_no_chr_23(): the501(23)
def test_method_no_chr_24(): the501(24)
def test_method_no_chr_25(): the501(25)
def test_method_no_chr_26(): the501(26)
def test_method_no_chr_27(): the501(27)
def test_method_no_chr_28(): the501(28)
def test_method_no_chr_29(): the501(29)

def test_method_no_chr_30(): the501(30)
def test_method_no_chr_31(): the501(31)
def test_method_no_chr_32(): the501(32) # space
def test_method_no_chr_33(): assert Method(chr(33)) == '!'

# SEPARATORS
def test_method_no_chr_40(): the501(40) # (
def test_method_no_chr_41(): the501(41) # )
def test_method_no_chr_60(): the501(60) # <
def test_method_no_chr_62(): the501(62) # >
def test_method_no_chr_64(): the501(64) # @
def test_method_no_chr_44(): the501(44) # ,
def test_method_no_chr_59(): the501(59) # ;
def test_method_no_chr_58(): the501(58) # :
def test_method_no_chr_92(): the501(92) # \
def test_method_no_chr_34(): the501(34) # "
def test_method_no_chr_47(): the501(47) # /
def test_method_no_chr_91(): the501(91) # [
def test_method_no_chr_93(): the501(93) # ]
def test_method_no_chr_63(): the501(63) # ?
def test_method_no_chr_61(): the501(61) # =
def test_method_no_chr_123(): the501(123) # {
def test_method_no_chr_125(): the501(125) # }
def test_method_no_chr_32(): the501(32) # SP
def test_method_no_chr_9(): the501(9) # HT


# URI
# ===

def test_uri_works_at_all():
    uri = URI("/")
    expected = u"/"
    actual = uri
    assert actual == expected

def test_a_nice_unicode_uri():
    uri = URI(b"http://%E2%98%84:bar@localhost:5370/+%E2%98%84.html?%E2%98%84=%E2%98%84+bar")
    assert uri == "http://%E2%98%84:bar@localhost:5370/+%E2%98%84.html?%E2%98%84=%E2%98%84+bar", uri


def test_uri_sets_scheme():
    uri = URI("http://foobar:secret@www.example.com:8080/baz.html?buz=bloo")
    assert uri.scheme == u"http", uri.scheme

def test_uri_sets_username():
    uri = URI("http://foobar:secret@www.example.com:8080/baz.html?buz=bloo")
    assert uri.username == u"foobar", uri.username

def test_uri_sets_password():
    uri = URI("http://foobar:secret@www.example.com:8080/baz.html?buz=bloo")
    assert uri.password == u"secret", uri.password

def test_uri_sets_host():
    uri = URI("http://foobar:secret@www.example.com:8080/baz.html?buz=bloo")
    assert uri.host == u"www.example.com", uri.host

def test_uri_sets_port():
    uri = URI("http://foobar:secret@www.example.com:8080/baz.html?buz=bloo")
    assert uri.port == 8080, uri.port

def test_uri_sets_path():
    uri = URI("http://foobar:secret@www.example.com:8080/baz.html?buz=bloo")
    assert uri.path.decoded == u"/baz.html", uri.path.decoded

def test_uri_sets_querystring():
    uri = URI("http://foobar:secret@www.example.com:8080/baz.html?buz=bloo")
    assert uri.querystring.decoded == u"buz=bloo", uri.querystring.decoded


def test_uri_scheme_is_unicode():
    uri = URI("http://foobar:secret@www.example.com:8080/baz.html?buz=bloo")
    assert isinstance(uri.scheme, unicode)

def test_uri_username_is_unicode():
    uri = URI("http://foobar:secret@www.example.com:8080/baz.html?buz=bloo")
    assert isinstance(uri.username, unicode)

def test_uri_password_is_unicode():
    uri = URI("http://foobar:secret@www.example.com:8080/baz.html?buz=bloo")
    assert isinstance(uri.password, unicode)

def test_uri_host_is_unicode():
    uri = URI("http://foobar:secret@www.example.com:8080/baz.html?buz=bloo")
    assert isinstance(uri.host, unicode)

def test_uri_port_is_int():
    uri = URI("http://foobar:secret@www.example.com:8080/baz.html?buz=bloo")
    assert isinstance(uri.port, int)

def test_uri_path_is_Mapping():
    uri = URI("http://foobar:secret@www.example.com:8080/baz.html?buz=bloo")
    assert isinstance(uri.path, Mapping)

def test_uri_querystring_is_Mapping():
    uri = URI("http://foobar:secret@www.example.com:8080/baz.html?buz=bloo")
    assert isinstance(uri.querystring, Mapping)


def test_uri_empty_scheme_is_empty_unicode():
    uri = URI("://foobar:secret@www.example.com:8080/baz.html?buz=bloo")
    assert uri.scheme == u"", uri.scheme
    assert isinstance(uri.scheme, unicode), uri.scheme.__class__

def test_uri_empty_username_is_empty_unicode():
    uri = URI("http://:secret@www.example.com:8080/baz.html?buz=bloo")
    assert uri.username == u"", uri.username
    assert isinstance(uri.username, unicode), uri.username.__class__

def test_uri_empty_password_is_empty_unicode():
    uri = URI("http://foobar:@www.example.com:8080/baz.html?buz=bloo")
    assert uri.password == u"", uri.password
    assert isinstance(uri.password, unicode), uri.password.__class__

def test_uri_empty_host_is_empty_unicode():
    uri = URI("http://foobar:secret@:8080/baz.html?buz=bloo")
    assert uri.host == u"", uri.host
    assert isinstance(uri.host, unicode), uri.host.__class__

def test_uri_empty_port_is_0():
    uri = URI("://foobar:secret@www.example.com:8080/baz.html?buz=bloo")
    assert uri.port == 0, uri.port


def test_uri_normal_case_is_normal():
    uri = URI("/baz.html?buz=bloo")
    assert uri.path == Path("/baz.html")
    assert uri.querystring == Querystring("buz=bloo")


def test_uri_ASCII_worketh():
    uri = URI(chr(127))
    assert uri == unichr(127), uri

def test_uri_non_ASCII_worketh_not():
    raises(UnicodeDecodeError, URI, chr(128))

def test_uri_encoded_username_is_unencoded_properly():
    uri = URI(b"http://%e2%98%84:secret@www.example.com/foo.html")
    assert uri.username == u'\u2604', uri.username

def test_uri_encoded_password_is_unencoded_properly():
    uri = URI(b"http://foobar:%e2%98%84@www.example.com/foo.html")
    assert uri.password == u'\u2604', uri.password

def test_uri_international_domain_name_comes_out_properly():
    uri = URI("http://www.xn--cev.tk/foo.html")
    assert uri.host == u'www.\u658b.tk', uri.host

def test_uri_bad_international_domain_name_raises_UnicodeError():
    raises(UnicodeError, URI, "http://www.xn--ced.tk/foo.html")

def test_uri_raw_is_available_on_something():
    uri = URI("http://www.xn--cev.tk/")
    assert uri.host.raw == "www.xn--cev.tk", uri.host.raw



# Version
# =======

def test_version_can_be_HTTP_0_9():
    actual = Version("HTTP/0.9")
    expected = u"HTTP/0.9"
    assert actual == expected

def test_version_can_be_HTTP_1_0():
    actual = Version("HTTP/1.0")
    expected = u"HTTP/1.0"
    assert actual == expected

def test_version_can_be_HTTP_1_1():
    actual = Version("HTTP/1.1")
    expected = u"HTTP/1.1"
    assert actual == expected

def test_version_cant_be_HTTP_1_2():
    assert raises(Response, Version, b"HTTP/1.2").value.code == 505

def test_version_cant_be_junk():
    assert raises(Response, Version, b"http flah flah").value.code == 400

def test_version_cant_even_be_lowercase():
    assert raises(Response, Version, b"http/1.1").value.code == 400

def test_version_cant_even_be_lowercase():
    assert raises(Response, Version, b"http/1.1").value.code == 400

def test_version_with_garbage_is_safe():
    r = raises(Response, Version, b"HTTP\xef/1.1").value
    assert r.code == 400, r.code
    assert r.body == "Bad HTTP version: HTTP\\xef/1.1.", r.body

def test_version_major_is_int():
    version = Version("HTTP/1.0")
    expected = 1
    actual = version.major
    assert actual == expected

def test_version_major_is_int():
    version = Version("HTTP/0.9")
    expected = 9
    actual = version.minor
    assert actual == expected

def test_version_info_is_tuple():
    version = Version("HTTP/0.9")
    expected = (0, 9)
    actual = version.info
    assert actual == expected

def test_version_raw_is_bytestring():
    version = Version(b"HTTP/0.9")
    expected = str
    actual = version.raw.__class__
    assert actual is expected


# Path
# ====

def test_path_starts_empty():
    path = Path("/bar.html")
    assert path == {}, path

def test_path_has_raw_set():
    path = Path("/bar.html")
    assert path.raw == "/bar.html", path.raw

def test_path_raw_is_str():
    path = Path(b"/bar.html")
    assert isinstance(path.raw, str)

def test_path_has_decoded_set():
    path = Path("/bar.html")
    assert path.decoded == u"/bar.html", path.decoded

def test_path_decoded_is_unicode():
    path = Path("/bar.html")
    assert isinstance(path.decoded, unicode)

def test_path_unquotes_and_decodes_UTF_8():
    path = Path(b"/%e2%98%84.html")
    assert path.decoded == u"/\u2604.html", path.decoded

def test_path_doesnt_unquote_plus():
    path = Path("/+%2B.html")
    assert path.decoded == u"/++.html", path.decoded

def test_path_has_parts():
    path = Path("/foo/bar.html")
    assert path.parts == ['foo', 'bar.html']


# Path params
# ===========

def _extract_params(uri):
#    return dispatcher.extract_rfc2396_params(path.lstrip('/').split('/'))
    params = [ segment.params for segment in uri.path.parts ]
    segments = [ unicode(segment) for segment in uri.path.parts ]
    return ( segments, params )

def test_extract_path_params_with_none():
    request = Request(uri="/foo/bar")
    actual = _extract_params(request.line.uri)
    expected = (['foo', 'bar'], [{}, {}])
    assert actual == expected

def test_extract_path_params_simple():
    request = Request(uri="/foo;a=1;b=2;c/bar;a=2;b=1")
    actual = _extract_params(request.line.uri)
    expected = (['foo', 'bar'], [{'a':['1'], 'b':['2'], 'c':['']}, {'a':['2'], 'b':['1']}])
    assert actual == expected

def test_extract_path_params_complex():
    request = Request(uri="/foo;a=1;b=2,3;c;a=2;b=4/bar;a=2,ab;b=1")
    actual = _extract_params(request.line.uri)
    expected = (['foo', 'bar'], [{'a':['1','2'], 'b':['2,3', '4'], 'c':['']}, {'a':[ '2,ab' ], 'b':['1']}])
    assert actual == expected

def test_path_params_api():
    request = Request(uri="/foo;a=1;b=2;b=3;c/bar;a=2,ab;b=1")
    parts, params = (['foo', 'bar'], [{'a':['1'], 'b':['2', '3'], 'c':['']}, {'a':[ '2,ab' ], 'b':['1']}])
    assert request.line.uri.path.parts == parts, request.line.uri.path.parts
    assert request.line.uri.path.parts[0].params == params[0]
    assert request.line.uri.path.parts[1].params == params[1]


# Querystring
# ===========

def test_querystring_starts_full():
    querystring = Querystring(b"baz=buz")
    assert querystring == {'baz': [u'buz']}, querystring

def test_querystring_has_raw_set():
    querystring = Querystring(b"baz=buz")
    assert querystring.raw == "baz=buz", querystring.raw

def test_querystring_raw_is_str():
    querystring = Querystring(b"baz=buz")
    assert isinstance(querystring.raw, str)

def test_querystring_has_decoded_set():
    querystring = Querystring(b"baz=buz")
    assert querystring.decoded == u"baz=buz", querystring.decoded

def test_querystring_decoded_is_unicode():
    querystring = Querystring(b"baz=buz")
    assert isinstance(querystring.decoded, unicode)

def test_querystring_unquotes_and_decodes_UTF_8():
    querystring = Querystring(b"baz=%e2%98%84")
    assert querystring.decoded == u"baz=\u2604", querystring.decoded

def test_querystring_comes_out_UTF_8():
    querystring = Querystring(b"baz=%e2%98%84")
    assert querystring['baz'] == u"\u2604", querystring['baz']

def test_querystring_chokes_on_bad_unicode():
    raises(UnicodeDecodeError, Querystring, b"baz=%e2%98")

def test_querystring_unquotes_plus():
    querystring = Querystring("baz=+%2B")
    assert querystring.decoded == u"baz= +", querystring.decoded
    assert querystring['baz'] == " +"



########NEW FILE########
__FILENAME__ = test_resources
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os

from aspen import Response
from aspen.resources.pagination import split
from pytest import raises


# Tests
# =====

def test_barely_working(harness):
    response = harness.simple('Greetings, program!', 'index.html')

    expected = 'text/html'
    actual = response.headers['Content-Type']
    assert actual == expected

def test_load_resource_loads_resource(harness):
    harness.fs.www.mk(('/index.html.spt', 'bar=0\n[---]\n[---]'))
    resource = harness.client.load_resource('/')
    assert resource.pages[0]['bar'] == 0

def test_charset_static_barely_working(harness):
    response = harness.simple( 'Greetings, program!'
                             , 'index.html'
                             , argv=['--charset_static', 'OOG']
                              )
    expected = 'text/html; charset=OOG'
    actual = response.headers['Content-Type']
    assert actual == expected

def test_charset_dynamic_barely_working(harness):
    response = harness.simple( '[---]\nGreetings, program!'
                             , 'index.html.spt'
                             , argv=['--charset_dynamic', 'CHEESECODE']
                              )
    expected = 'text/html; charset=CHEESECODE'
    actual = response.headers['Content-Type']
    assert actual == expected

def test_resource_pages_work(harness):
    actual = harness.simple("foo = 'bar'\n[--------]\nGreetings, %(foo)s!").body
    assert actual == "Greetings, bar!"

def test_resource_dunder_all_limits_vars(harness):
    actual = raises( KeyError
                            , harness.simple
                            , "foo = 'bar'\n"
                              "__all__ = []\n"
                              "[---------]\n"
                              "Greetings, %(foo)s!"
                             ).value
    # in production, KeyError is turned into a 500 by an outer wrapper
    assert type(actual) == KeyError

def test_path_part_params_are_available(harness):
    response = harness.simple("""
        if 'b' in path.parts[0].params:
            a = path.parts[0].params['a']
        [---]
        %(a)s
    """, '/foo/index.html.spt', '/foo;a=1;b;a=3/')
    assert response.body == "3\n"

def test_resources_dont_leak_whitespace(harness):
    """This aims to resolve https://github.com/whit537/aspen/issues/8.
    """
    actual = harness.simple("""
        [--------------]
        foo = [1,2,3,4]
        [--------------]
        %(foo)r""").body
    assert actual == "[1, 2, 3, 4]"

def test_negotiated_resource_doesnt_break(harness):
    expected = "Greetings, bar!\n"
    actual = harness.simple("""
        [-----------]
        foo = 'bar'
        [-----------] text/plain
        Greetings, %(foo)s!
        [-----------] text/html
        <h1>Greetings, %(foo)s!</h1>
        """
        , filepath='index.spt').body
    assert actual == expected


# raise Response
# ==============

def test_raise_response_works(harness):
    expected = 404
    response = raises( Response
                            , harness.simple
                            , "from aspen import Response\n"
                              "raise Response(404)\n"
                              "[---------]\n"
                             ).value
    actual = response.code
    assert actual == expected

def test_exception_location_preserved_for_response_raised_in_page_2(harness):
    # https://github.com/gittip/aspen-python/issues/153
    expected_path = os.path.join(os.path.basename(harness.fs.www.root), 'index.html.spt')
    expected = (expected_path, 1)
    try:
        harness.simple('from aspen import Response; raise Response(404)\n[---]\n')
    except Response, response:
        actual = response.whence_raised()
    assert actual == expected

def test_website_is_in_context(harness):
    response = harness.simple("""
        assert website.__class__.__name__ == 'Website', website
        [--------]
        [--------]
        It worked.""")
    assert response.body == 'It worked.'

def test_unknown_mimetype_yields_default_mimetype(harness):
    response = harness.simple( 'Greetings, program!'
                             , filepath='foo.flugbaggity'
                              )
    assert response.headers['Content-Type'] == 'text/plain'

def test_templating_without_script_works(harness):
    response = harness.simple('[-----] via stdlib_format\n{request.line.uri.path.raw}')
    assert response.body == '/'


# Test offset calculation

def check_offsets(raw, offsets):
    actual = [page.offset for page in split(raw)]
    assert actual == offsets

def test_offset_calculation_basic(harness):
    check_offsets('\n\n\n[---]\n\n', [0, 4])

def test_offset_calculation_for_empty_file(harness):
    check_offsets('', [0])

def test_offset_calculation_advanced(harness):
    raw = (
        '\n\n\n[---]\n'
        'cheese\n[---]\n'
        '\n\n\n\n\n\n[---]\n'
        'Monkey\nHead\n') #Be careful: this is implicit concation, not a tuple
    check_offsets(raw, [0, 4, 6, 13])

########NEW FILE########
__FILENAME__ = test_resources_generics
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from aspen.resources import pagination

#SPLIT TESTS
############

def check_page_content(raw, comp_pages):
    '''
    Pattern function. Splits a raw, then checks the number of pages generated,
    and that each page's content matches the contents of comp_pages.
    Interpretation of comp_pages is as follows:
    comp_pages is am item or a list of items. Each item is a string, tuple, or
    None. If it is a string, the page's content is matched; if it is a tuple,
    the page's content and/or header are checked. If any of the items are None,
    that comparison is ignored.
    '''

    #Convert to single-element list
    if not isinstance(comp_pages, list):
        comp_pages = [comp_pages]

    #Convert all non-tuples to tuples
    comp_pages = [item if isinstance(item, tuple) else (item, None)
                  for item in comp_pages]

    #execute resources.split
    pages = list(pagination.split(raw))

    assert len(pages) == len(comp_pages)

    for generated_page, (content, header) in zip(pages, comp_pages):
        if content is not None:
            assert generated_page.content == content, repr(generated_page.content) + " should be " + repr(content)
        if header is not None:
            assert generated_page.header == header, repr(generated_page.header) + " should be " + repr(header)

def test_empty_content():
    check_page_content('', '')

def test_no_page_breaks():
    content = 'this is some content\nwith newlines'
    check_page_content(content, content)

def test_only_page_break():
    check_page_content('[---]\n', ['', ''])

def test_basic_page_break():
    check_page_content('Page 1\n[---]\nPage 2\n',
                       ['Page 1\n', 'Page 2\n'])

def test_two_page_breaks():
    raw = '''\
1
[---]
2
[---]
3
'''
    check_page_content(raw, ['1\n', '2\n', '3\n'])

def test_no_inline_page_break():
    content = 'this is an[---]inline page break'
    check_page_content(content,  [None])

def test_headers():
    raw = '''\
page1
[---] header2
page2
[---] header3
page3
'''
    pages = [
        ('page1\n', ''),
        ('page2\n', 'header2'),
        ('page3\n', 'header3')]

    check_page_content(raw, pages)
#ESCAPE TESTS
#############

def check_escape(content_to_escape, expected):
    actual = pagination.escape(content_to_escape)
    assert actual == expected, repr(actual) + " should be " + repr(expected)

def test_basic_escape_1():
    check_escape('\[---]', '[---]')

def test_basic_escape_2():
    check_escape('\\\\\\[---]', '\\\[---]')

def test_inline_sep_ignored_1():
    check_escape('inline[---]break', 'inline[---]break')

def test_inline_sep_ignored_2():
    check_escape('inline\\\[---]break', 'inline\\\[---]break')

def test_escape_preserves_extra_content():
    check_escape('\\\\[---] content ', '\[---] content ')

def test_multiple_escapes():
    to_escape = '1\n\[---]\n2\n\[---]'
    result = '1\n[---]\n2\n[---]'
    check_escape(to_escape, result)

def test_long_break():
    check_escape('\[----------]', '[----------]')

def test_escaped_pages():
    raw = '''\
1
[---]
2
\[---]
3
'''
    check_page_content(raw, ['1\n', '2\n\\[---]\n3\n'])

#SPECLINE TESTS
###############

def check_specline(header, media_type, renderer):
    assert pagination.parse_specline(header) == (media_type, renderer)

def test_empty_header_1():
    check_specline('', '', '')

def test_empty_header_2():
    check_specline('    ', '', '')

def test_media_only():
    check_specline('text/plain', 'text/plain', '')

def test_renderer_only():
    check_specline('via renderer', '', 'renderer')

def test_basic_specline():
    check_specline('media/type via renderer', 'media/type', 'renderer')

def test_funky_whitespace():
    check_specline( '  media/type    via   renderer  '
                  , 'media/type'
                  , 'renderer'
                   )

def test_whitespace_in_fields():
    check_specline( 'media type via content renderer'
                  , 'media type'
                  , 'content renderer'
                   )

def test_extra_funky_whitespace():
    header = '   this is a  type   via some sort   of renderer    '
    media_type = 'this is a  type'
    renderer = 'some sort   of renderer'
    check_specline(header, media_type, renderer)

########NEW FILE########
__FILENAME__ = test_response
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from pytest import raises

from aspen import Response
from aspen.exceptions import CRLFInjection


def test_response_is_a_wsgi_callable():
    response = Response(body=b"Greetings, program!")
    def start_response(status, headers):
        pass
    expected = ["Greetings, program!"]
    actual = list(response({}, start_response).body)
    assert actual == expected

def test_response_body_can_be_bytestring():
    response = Response(body=b"Greetings, program!")
    expected = "Greetings, program!"
    actual = response.body
    assert actual == expected

def test_response_body_as_bytestring_results_in_an_iterable():
    response = Response(body=b"Greetings, program!")
    def start_response(status, headers):
        pass
    expected = ["Greetings, program!"]
    actual = list(response({}, start_response).body)
    assert actual == expected

def test_response_body_can_be_iterable():
    response = Response(body=["Greetings, ", "program!"])
    expected = ["Greetings, ", "program!"]
    actual = response.body
    assert actual == expected

def test_response_body_as_iterable_comes_through_untouched():
    response = Response(body=["Greetings, ", "program!"])
    def start_response(status, headers):
        pass
    expected = ["Greetings, ", "program!"]
    actual = list(response({}, start_response).body)
    assert actual == expected

def test_response_body_can_be_unicode():
    try:
        Response(body=u'Greetings, program!')
    except:
        assert False, 'expecting no error'

def test_response_headers_protect_against_crlf_injection():
    response = Response()
    def inject():
        response.headers['Location'] = 'foo\r\nbar'
    raises(CRLFInjection, inject)




########NEW FILE########
__FILENAME__ = test_unicode
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from aspen.resources import decode_raw
from aspen.exceptions import LoadError
from pytest import raises


def test_non_ascii_bytes_fail_without_encoding(harness):
    raises(LoadError, harness.simple, b"""
        [------------------]
        text = u'א'
        [------------------]
        %(text)s
    """)

def test_non_ascii_bytes_work_with_encoding(harness):
    expected = u'א'
    actual = harness.simple(b"""
        # encoding=utf8
        [------------------]
        text = u'א'
        [------------------]
        %(text)s
    """).body.strip()
    assert actual == expected

def test_response_as_wsgi_does_something_sane(harness):
    expected = u'א'.encode('utf8')
    wsgi = harness.simple(b"""
        # encoding=utf8
        [------------------]
        text = u'א'
        [------------------]
        %(text)s""")
    actual = b''.join(list(wsgi({}, lambda a,b: None)))
    assert actual == expected

def test_the_exec_machinery_handles_two_encoding_lines_properly(harness):
    expected = u'א'
    actual = harness.simple(b"""\
        # encoding=utf8
        # encoding=ascii
        [------------------]
        text = u'א'
        [------------------]
        %(text)s
    """).body.strip()
    assert actual == expected


# decode_raw

def test_decode_raw_can_take_encoding_from_first_line():
    actual = decode_raw(b"""\
    # -*- coding: utf8 -*-
    text = u'א'
    """)
    expected = """\
    # encoding set to utf8
    text = u'א'
    """
    assert actual == expected

def test_decode_raw_can_take_encoding_from_second_line():
    actual = decode_raw(b"""\
    #!/blah/blah
    # -*- coding: utf8 -*-
    text = u'א'
    """)
    expected = """\
    #!/blah/blah
    # encoding set to utf8
    text = u'א'
    """
    assert actual == expected

def test_decode_raw_prefers_first_line_to_second():
    actual = decode_raw(b"""\
    # -*- coding: utf8 -*-
    # -*- coding: ascii -*-
    text = u'א'
    """)
    expected = """\
    # encoding set to utf8
    # encoding NOT set to ascii
    text = u'א'
    """
    assert actual == expected

def test_decode_raw_ignores_third_line():
    actual = decode_raw(b"""\
    # -*- coding: utf8 -*-
    # -*- coding: ascii -*-
    # -*- coding: cornnuts -*-
    text = u'א'
    """)
    expected = """\
    # encoding set to utf8
    # encoding NOT set to ascii
    # -*- coding: cornnuts -*-
    text = u'א'
    """
    assert actual == expected

def test_decode_raw_can_take_encoding_from_various_line_formats():
    formats = [ b'-*- coding: utf8 -*-'
              , b'-*- encoding: utf8 -*-'
              , b'coding: utf8'
              , b'  coding: utf8'
              , b'\tencoding: utf8'
              , b'\t flubcoding=utf8'
               ]
    for fmt in formats:
        def test():
            actual = decode_raw(b"""\
            # {0}
            text = u'א'
            """.format(fmt))
            expected = """\
            # encoding set to utf8
            text = u'א'
            """
            assert actual == expected
        yield test

def test_decode_raw_cant_take_encoding_from_bad_line_formats():
    formats = [ b'-*- coding : utf8 -*-'
              , b'foo = 0 -*- encoding: utf8 -*-'
              , b'  coding : utf8'
              , b'encoding : utf8'
              , b'  flubcoding =utf8'
              , b'coding: '
               ]
    for fmt in formats:
        def test():
            raw = b"""\
            # {0}
            text = u'א'
            """.format(fmt)
            raises(UnicodeDecodeError, decode_raw, raw)
        yield test

########NEW FILE########
__FILENAME__ = test_utils
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from pytest import raises

import aspen.utils # this happens to install the 'repr' error strategy
from aspen.utils import ascii_dammit, unicode_dammit, to_age, to_rfc822, utcnow
from datetime import datetime

GARBAGE = b"\xef\xf9"


def test_garbage_is_garbage():
    raises(UnicodeDecodeError, lambda s: s.decode('utf8'), GARBAGE)

def test_repr_error_strategy_works():
    errors = 'repr'
    actual = GARBAGE.decode('utf8', errors)
    assert actual == r"\xef\xf9"

def test_unicode_dammit_works():
    actual = unicode_dammit(b"foo\xef\xfar")
    assert actual == r"foo\xef\xfar"

def test_unicode_dammit_fails():
    raises(TypeError, unicode_dammit, 1)
    raises(TypeError, unicode_dammit, [])
    raises(TypeError, unicode_dammit, {})

def test_unicode_dammit_decodes_utf8():
    actual = unicode_dammit(b"comet: \xe2\x98\x84")
    assert actual == u"comet: \u2604"

def test_unicode_dammit_takes_encoding():
    actual = unicode_dammit(b"comet: \xe2\x98\x84", encoding="ASCII")
    assert actual == r"comet: \xe2\x98\x84"

def test_ascii_dammit_works():
    actual = ascii_dammit(b"comet: \xe2\x98\x84")
    assert actual == r"comet: \xe2\x98\x84"

def test_to_age_barely_works():
    actual = to_age(utcnow())
    assert actual == "just a moment ago"

def test_to_age_fails():
    raises(ValueError, to_age, datetime.utcnow())

def test_to_age_formatting_works():
    actual = to_age(utcnow(), fmt_past="Cheese, for %(age)s!")
    assert actual == "Cheese, for just a moment!"

def test_to_rfc822():
    expected = 'Thu, 01 Jan 1970 00:00:00 GMT'
    actual = to_rfc822(datetime(1970, 1, 1))
    assert actual == expected

########NEW FILE########
__FILENAME__ = test_website
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import StringIO

from aspen.website import Website


simple_error_spt = """
[---]
[---] text/plain via stdlib_format
{response.body}
"""


# Tests
# =====

def test_basic():
    website = Website([])
    expected = os.getcwd()
    actual = website.www_root
    assert actual == expected

def test_normal_response_is_returned(harness):
    harness.fs.www.mk(('index.html', "Greetings, program!"))
    expected = '\r\n'.join("""\
HTTP/1.1
Content-Type: text/html

Greetings, program!
""".splitlines())
    actual = harness.client.GET()._to_http('1.1')
    assert actual == expected

def test_fatal_error_response_is_returned(harness):
    harness.fs.www.mk(('index.html.spt', "raise heck\n[---]\n"))
    expected = 500
    actual = harness.client.GET(raise_immediately=False).code
    assert actual == expected

def test_redirect_has_only_location(harness):
    harness.fs.www.mk(('index.html.spt', """
from aspen import Response
[---]
request.redirect('http://elsewhere', code=304)
[---]"""))
    actual = harness.client.GET(raise_immediately=False)
    assert actual.code == 304
    headers = actual.headers
    assert headers.keys() == ['Location']

def test_nice_error_response_is_returned(harness):
    harness.short_circuit = False
    harness.fs.www.mk(('index.html.spt', """
from aspen import Response
[---]
raise Response(500)
[---]"""))
    assert harness.client.GET(raise_immediately=False).code == 500

def test_nice_error_response_is_returned_for_404(harness):
    harness.fs.www.mk(('index.html.spt', """
from aspen import Response
[---]
raise Response(404)
[---]"""))
    assert harness.client.GET(raise_immediately=False).code == 404

def test_response_body_doesnt_expose_traceback_by_default(harness):
    harness.fs.project.mk(('error.spt', simple_error_spt))
    harness.fs.www.mk(('index.html.spt', """
[---]
raise Exception("Can I haz traceback ?")
[---]"""))
    response = harness.client.GET(raise_immediately=False)
    assert response.code == 500
    assert "Can I haz traceback ?" not in response.body

def test_response_body_exposes_traceback_for_show_tracebacks(harness):
    harness.client.website.show_tracebacks = True
    harness.fs.project.mk(('error.spt', simple_error_spt))
    harness.fs.www.mk(('index.html.spt', """
[---]
raise Exception("Can I haz traceback ?")
[---]"""))
    response = harness.client.GET(raise_immediately=False)
    assert response.code == 500
    assert "Can I haz traceback ?" in response.body

def test_default_error_simplate_doesnt_expose_raised_body_by_default(harness):
    harness.fs.www.mk(('index.html.spt', """
from aspen import Response
[---]
raise Response(404, "Um, yeah.")
[---]"""))
    response = harness.client.GET(raise_immediately=False)
    assert response.code == 404
    assert "Um, yeah." not in response.body

def test_default_error_simplate_exposes_raised_body_for_show_tracebacks(harness):
    harness.client.website.show_tracebacks = True
    harness.fs.www.mk(('index.html.spt', """
from aspen import Response
[---]
raise Response(404, "Um, yeah.")
[---]"""))
    response = harness.client.GET(raise_immediately=False)
    assert response.code == 404
    assert "Um, yeah." in response.body

def test_nice_error_response_can_come_from_user_error_spt(harness):
    harness.fs.project.mk(('error.spt', '[---]\n[---] text/plain\nTold ya.'))
    harness.fs.www.mk(('index.html.spt', """
from aspen import Response
[---]
raise Response(420)
[---]"""))
    response = harness.client.GET(raise_immediately=False)
    assert response.code == 420
    assert response.body == 'Told ya.'

def test_nice_error_response_can_come_from_user_420_spt(harness):
    harness.fs.project.mk(('420.spt', """
[---]
msg = "Enhance your calm." if response.code == 420 else "Ok."
[---] text/plain
%(msg)s"""))
    harness.fs.www.mk(('index.html.spt', """
from aspen import Response
[---]
raise Response(420)
[---]"""))
    response = harness.client.GET(raise_immediately=False)
    assert response.code == 420
    assert response.body == 'Enhance your calm.'

def test_default_error_spt_handles_text_html(harness):
    harness.fs.www.mk(('foo.html.spt',"""
from aspen import Response
[---]
raise Response(404)
[---]
    """))
    response = harness.client.GET('/foo.html', raise_immediately=False)
    assert response.code == 404
    assert 'text/html' in response.headers['Content-Type']

def test_default_error_spt_handles_application_json(harness):
    harness.fs.www.mk(('foo.json.spt',"""
from aspen import Response
[---]
raise Response(404)
[---]
    """))
    response = harness.client.GET('/foo.json', raise_immediately=False)
    assert response.code == 404
    assert response.headers['Content-Type'] == 'application/json'
    assert response.body == '''\
{ "error_code": 404
, "error_message_short": "Not Found"
, "error_message_long": ""
 }
'''

def test_default_error_spt_application_json_includes_msg_for_show_tracebacks(harness):
    harness.client.website.show_tracebacks = True
    harness.fs.www.mk(('foo.json.spt',"""
from aspen import Response
[---]
raise Response(404, "Right, sooo...")
[---]
    """))
    response = harness.client.GET('/foo.json', raise_immediately=False)
    assert response.code == 404
    assert response.headers['Content-Type'] == 'application/json'
    assert response.body == '''\
{ "error_code": 404
, "error_message_short": "Not Found"
, "error_message_long": "Right, sooo..."
 }
'''

def test_default_error_spt_falls_through_to_text_plain(harness):
    harness.fs.www.mk(('foo.xml.spt',"""
from aspen import Response
[---]
raise Response(404)
[---]
    """))
    response = harness.client.GET('/foo.xml', raise_immediately=False)
    assert response.code == 404
    assert response.headers['Content-Type'] == 'text/plain; charset=UTF-8'
    assert response.body == "Not found, program!\n\n"

def test_default_error_spt_fall_through_includes_msg_for_show_tracebacks(harness):
    harness.client.website.show_tracebacks = True
    harness.fs.www.mk(('foo.xml.spt',"""
from aspen import Response
[---]
raise Response(404, "Try again!")
[---]
    """))
    response = harness.client.GET('/foo.xml', raise_immediately=False)
    assert response.code == 404
    assert response.headers['Content-Type'] == 'text/plain; charset=UTF-8'
    assert response.body == "Not found, program!\nTry again!\n"

def test_custom_error_spt_without_text_plain_results_in_406(harness):
    harness.fs.project.mk(('error.spt', """
[---]
[---] text/html
<h1>Oh no!</h1>
    """))
    harness.fs.www.mk(('foo.xml.spt',"""
from aspen import Response
[---]
raise Response(404)
[---]
    """))
    response = harness.client.GET('/foo.xml', raise_immediately=False)
    assert response.code == 406

def test_custom_error_spt_with_text_plain_works(harness):
    harness.fs.project.mk(('error.spt', """
[---]
[---] text/plain
Oh no!
    """))
    harness.fs.www.mk(('foo.xml.spt',"""
from aspen import Response
[---]
raise Response(404)
[---]
    """))
    response = harness.client.GET('/foo.xml', raise_immediately=False)
    assert response.code == 404
    assert response.headers['Content-Type'] == 'text/plain; charset=UTF-8'
    assert response.body == "Oh no!\n"


def test_autoindex_response_is_404_by_default(harness):
    harness.fs.www.mk(('README', "Greetings, program!"))
    assert harness.client.GET(raise_immediately=False).code == 404

def test_autoindex_response_is_returned(harness):
    harness.fs.www.mk(('README', "Greetings, program!"))
    harness.client.website.list_directories = True
    body = harness.client.GET(raise_immediately=False).body
    assert 'README' in body

def test_resources_can_import_from_project_root(harness):
    harness.fs.project.mk(('foo.py', 'bar = "baz"'))
    harness.fs.www.mk(('index.html.spt', "from foo import bar\n[---]\nGreetings, %(bar)s!"))
    assert harness.client.GET(raise_immediately=False).body == "Greetings, baz!"

def test_non_500_response_exceptions_dont_get_folded_to_500(harness):
    harness.fs.www.mk(('index.html.spt', '''
from aspen import Response
raise Response(400)
[---]
'''))
    response = harness.client.GET(raise_immediately=False)
    assert response.code == 400

def test_errors_show_tracebacks(harness):
    harness.fs.www.mk(('index.html.spt', '''
from aspen import Response
website.show_tracebacks = 1
raise Response(400,1,2,3,4,5,6,7,8,9)
[---]
'''))
    response = harness.client.GET(raise_immediately=False)
    assert response.code == 500
    assert 'Response(400,1,2,3,4,5,6,7,8,9)' in response.body


class TestMiddleware(object):
    """Simple WSGI middleware for testing."""

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        if environ['PATH_INFO'] == '/middleware':
            start_response('200 OK', [('Content-Type', 'text/plain')])
            return ['TestMiddleware']
        return self.app(environ, start_response)

def build_environ(path):
    """Build WSGI environ for testing."""
    return {
        'REQUEST_METHOD': b'GET',
        'PATH_INFO': path,
        'QUERY_STRING': b'',
        'SERVER_SOFTWARE': b'build_environ/1.0',
        'SERVER_PROTOCOL': b'HTTP/1.1',
        'wsgi.input': StringIO.StringIO()
    }

def test_call_wraps_wsgi_middleware(client):
    client.website.algorithm.default_short_circuit = False
    client.website.wsgi_app = TestMiddleware(client.website.wsgi_app)
    respond = [False, False]
    def start_response_should_404(status, headers):
        assert status.lower().strip() == '404 not found'
        respond[0] = True
    client.website(build_environ('/'), start_response_should_404)
    assert respond[0]
    def start_response_should_200(status, headers):
        assert status.lower().strip() == '200 ok'
        respond[1] = True
    client.website(build_environ('/middleware'), start_response_should_200)
    assert respond[1]

########NEW FILE########
__FILENAME__ = test_website_flow
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


def test_website_can_respond(harness):
    harness.fs.www.mk(('index.html.spt', 'Greetings, program!'))
    assert harness.client.GET().body == 'Greetings, program!'


def test_404_comes_out_404(harness):
    harness.fs.project.mk(('404.spt', '[---]\n[---] text/plain\nEep!'))
    assert harness.client.GET(raise_immediately=False).code == 404

########NEW FILE########
__FILENAME__ = test_weird
"""Wherein our hero learns about sys.path_importer_cache.

Python caches some of its import machinery, and if you try really hard, you can
shoot yourself in the foot with that.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
from pprint import pformat


FIX_VIA_IMPORT = 1
FIX_VIA_PROJ = 0
FSFIX = os.path.realpath('fsfix')


def log(a, *b):
    return  # turn off logging now that this works
    if not b:
        print(a.rjust(30))
    else:
        for line in b:
            print(a.rjust(30)+": ", line)


def rm():
    root = FSFIX
    if os.path.isdir(root):
        for root, dirs, files in os.walk(root, topdown=False):
            for name in dirs:
                _ = os.path.join(root, name)
                log("removing  dir", _)
                os.rmdir(_)
            for name in files:
                _ = os.path.join(root, name)
                log("removing file", _)
                os.remove(_)
        log("removing root", root)
        os.rmdir(root)
    sys.path_importer_cache = {}

def __dump():
    log("sys.path_importer_cache", pformat(sys.path_importer_cache).splitlines())

def test_weirdness():
    try:
        #print
        foo = os.path.join(FSFIX, 'foo')
        foo = os.path.realpath(foo)
        if foo not in sys.path:
            log("inserting into sys.path", foo )
            sys.path.insert(0, foo)

        log("making directory", FSFIX)
        os.mkdir(FSFIX)
        if FIX_VIA_PROJ:
            log("making directory", FSFIX + '/foo')
            os.mkdir(FSFIX + '/foo')

        log("importing a thing")
        old = set(sys.path_importer_cache.keys())
        import aspen
        now = set(sys.path_importer_cache.keys())
        log("diff", now - old)

        rm()

        log("making directory", FSFIX)
        os.mkdir(FSFIX)
        log("making directory", FSFIX + '/foo')
        os.mkdir(FSFIX + '/foo')
        log("making file", FSFIX + '/foo' + '/bar.py')
        open(FSFIX + '/foo/bar.py', 'w+').write('baz = "buz"')

        log("contents of fsfix/foo/bar.py", open('fsfix/foo/bar.py').read())
        log("contents of sys.path", *sys.path)

        log("importing bar")
        __dump()
        try:
            import bar
            log("succeeded")
        except:
            log("failed")
            raise
    finally:
        rm()

    #print

if __name__ == '__main__':
    test_weirdness()

########NEW FILE########
__FILENAME__ = thrash
"""This is a simple tool to restart a process when it dies.

It's designed to restart aspen in development when it dies because files
have changed and you set changes_reload to 'yes'.

    http://aspen.io/thrash/

"""

def foo():

    # Import in here to capture KeyboardInterrupt during imports.
    import os
    import subprocess
    import sys
    import time

    # set unbuffered - http://stackoverflow.com/a/181654/253309
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'wb', 0)

    if len(sys.argv) < 2:
        print ("usage: %s <child> [child opts and args]"
               % os.path.basename(sys.argv[0]))
        sys.exit(1)

    BACKOFF_MIN = 0.10  # Start looping here.
    BACKOFF_MAX = 3.20  # Throttle back to here.
    PROMPT_AFTER = 60   # Give the user this much time to fix the error.
    INITIAL_WAIT = 15   # Give the user this much time to read the error.

    n = 0
    backoff = BACKOFF_MIN
    cumulative_time = 0

    while 1:

        # The child process exited.
        # =========================
        # Log restart attempts after the initial launch.

        n += 1
        backoff = min(backoff * 2, BACKOFF_MAX)
        if n > 1:
            m = "---- Restart #%s " % n
            print
            print m + ('-' * (79-len(m)))


        # Execute the child process.
        # ==========================
        # Then wait for it to return, dealing with INT.

        proc = subprocess.Popen( sys.argv[1:]
                               , stdout=sys.stdout
                               , stderr=sys.stderr
                                )
        try:
            status = proc.wait()
        except KeyboardInterrupt:
            status = proc.wait()

        if status == 75:
            print ("Received INT in child.")


        # Decide how to proceed.
        # ======================

        if n == 1:
            # This is the first time we've thrashed. Give the user time to
            # parse the (presumed) traceback.
            cumulative_time += INITIAL_WAIT
            try:
                time.sleep(INITIAL_WAIT)
            except KeyboardInterrupt:
                # Allow user to fast-track this step.

                # reset
                n = 0
                backoff = BACKOFF_MIN
                cumulative_time = 0

        elif cumulative_time < PROMPT_AFTER:
            # We've given the user time to parse the traceback. Now thrash
            # for a while.
            cumulative_time += backoff
            time.sleep(backoff)

        else:
            # We've been thrashing for a while. Pause.
            print
            try:
                raw_input("Press any key to start thrashing again. ")
            except KeyboardInterrupt:
                print

            # reset
            n = 0
            backoff = BACKOFF_MIN
            cumulative_time = 0


def main():
    try:
        foo()
    except KeyboardInterrupt:
        import time
        time.sleep(0.1)  # give child stdio time to flush
        print "Received INT in thrash, exiting."

########NEW FILE########
__FILENAME__ = virtualenv-1.11.2
#!/usr/bin/env python
"""Create a "virtual" Python installation
"""

__version__ = "1.11.2"
virtualenv_version = __version__  # legacy

import base64
import sys
import os
import codecs
import optparse
import re
import shutil
import logging
import tempfile
import zlib
import errno
import glob
import distutils.sysconfig
from distutils.util import strtobool
import struct
import subprocess
import tarfile

if sys.version_info < (2, 6):
    print('ERROR: %s' % sys.exc_info()[1])
    print('ERROR: this script requires Python 2.6 or greater.')
    sys.exit(101)

try:
    set
except NameError:
    from sets import Set as set
try:
    basestring
except NameError:
    basestring = str

try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser

join = os.path.join
py_version = 'python%s.%s' % (sys.version_info[0], sys.version_info[1])

is_jython = sys.platform.startswith('java')
is_pypy = hasattr(sys, 'pypy_version_info')
is_win = (sys.platform == 'win32')
is_cygwin = (sys.platform == 'cygwin')
is_darwin = (sys.platform == 'darwin')
abiflags = getattr(sys, 'abiflags', '')

user_dir = os.path.expanduser('~')
if is_win:
    default_storage_dir = os.path.join(user_dir, 'virtualenv')
else:
    default_storage_dir = os.path.join(user_dir, '.virtualenv')
default_config_file = os.path.join(default_storage_dir, 'virtualenv.ini')

if is_pypy:
    expected_exe = 'pypy'
elif is_jython:
    expected_exe = 'jython'
else:
    expected_exe = 'python'

# Return a mapping of version -> Python executable
# Only provided for Windows, where the information in the registry is used
if not is_win:
    def get_installed_pythons():
        return {}
else:
    try:
        import winreg
    except ImportError:
        import _winreg as winreg

    def get_installed_pythons():
        python_core = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE,
                "Software\\Python\\PythonCore")
        i = 0
        versions = []
        while True:
            try:
                versions.append(winreg.EnumKey(python_core, i))
                i = i + 1
            except WindowsError:
                break
        exes = dict()
        for ver in versions:
            path = winreg.QueryValue(python_core, "%s\\InstallPath" % ver)
            exes[ver] = join(path, "python.exe")

        winreg.CloseKey(python_core)

        # Add the major versions
        # Sort the keys, then repeatedly update the major version entry
        # Last executable (i.e., highest version) wins with this approach
        for ver in sorted(exes):
            exes[ver[0]] = exes[ver]

        return exes

REQUIRED_MODULES = ['os', 'posix', 'posixpath', 'nt', 'ntpath', 'genericpath',
                    'fnmatch', 'locale', 'encodings', 'codecs',
                    'stat', 'UserDict', 'readline', 'copy_reg', 'types',
                    're', 'sre', 'sre_parse', 'sre_constants', 'sre_compile',
                    'zlib']

REQUIRED_FILES = ['lib-dynload', 'config']

majver, minver = sys.version_info[:2]
if majver == 2:
    if minver >= 6:
        REQUIRED_MODULES.extend(['warnings', 'linecache', '_abcoll', 'abc'])
    if minver >= 7:
        REQUIRED_MODULES.extend(['_weakrefset'])
    if minver <= 3:
        REQUIRED_MODULES.extend(['sets', '__future__'])
elif majver == 3:
    # Some extra modules are needed for Python 3, but different ones
    # for different versions.
    REQUIRED_MODULES.extend(['_abcoll', 'warnings', 'linecache', 'abc', 'io',
                             '_weakrefset', 'copyreg', 'tempfile', 'random',
                             '__future__', 'collections', 'keyword', 'tarfile',
                             'shutil', 'struct', 'copy', 'tokenize', 'token',
                             'functools', 'heapq', 'bisect', 'weakref',
                             'reprlib'])
    if minver >= 2:
        REQUIRED_FILES[-1] = 'config-%s' % majver
    if minver >= 3:
        import sysconfig
        platdir = sysconfig.get_config_var('PLATDIR')
        REQUIRED_FILES.append(platdir)
        # The whole list of 3.3 modules is reproduced below - the current
        # uncommented ones are required for 3.3 as of now, but more may be
        # added as 3.3 development continues.
        REQUIRED_MODULES.extend([
            #"aifc",
            #"antigravity",
            #"argparse",
            #"ast",
            #"asynchat",
            #"asyncore",
            "base64",
            #"bdb",
            #"binhex",
            #"bisect",
            #"calendar",
            #"cgi",
            #"cgitb",
            #"chunk",
            #"cmd",
            #"codeop",
            #"code",
            #"colorsys",
            #"_compat_pickle",
            #"compileall",
            #"concurrent",
            #"configparser",
            #"contextlib",
            #"cProfile",
            #"crypt",
            #"csv",
            #"ctypes",
            #"curses",
            #"datetime",
            #"dbm",
            #"decimal",
            #"difflib",
            #"dis",
            #"doctest",
            #"dummy_threading",
            "_dummy_thread",
            #"email",
            #"filecmp",
            #"fileinput",
            #"formatter",
            #"fractions",
            #"ftplib",
            #"functools",
            #"getopt",
            #"getpass",
            #"gettext",
            #"glob",
            #"gzip",
            "hashlib",
            #"heapq",
            "hmac",
            #"html",
            #"http",
            #"idlelib",
            #"imaplib",
            #"imghdr",
            "imp",
            "importlib",
            #"inspect",
            #"json",
            #"lib2to3",
            #"logging",
            #"macpath",
            #"macurl2path",
            #"mailbox",
            #"mailcap",
            #"_markupbase",
            #"mimetypes",
            #"modulefinder",
            #"multiprocessing",
            #"netrc",
            #"nntplib",
            #"nturl2path",
            #"numbers",
            #"opcode",
            #"optparse",
            #"os2emxpath",
            #"pdb",
            #"pickle",
            #"pickletools",
            #"pipes",
            #"pkgutil",
            #"platform",
            #"plat-linux2",
            #"plistlib",
            #"poplib",
            #"pprint",
            #"profile",
            #"pstats",
            #"pty",
            #"pyclbr",
            #"py_compile",
            #"pydoc_data",
            #"pydoc",
            #"_pyio",
            #"queue",
            #"quopri",
            #"reprlib",
            "rlcompleter",
            #"runpy",
            #"sched",
            #"shelve",
            #"shlex",
            #"smtpd",
            #"smtplib",
            #"sndhdr",
            #"socket",
            #"socketserver",
            #"sqlite3",
            #"ssl",
            #"stringprep",
            #"string",
            #"_strptime",
            #"subprocess",
            #"sunau",
            #"symbol",
            #"symtable",
            #"sysconfig",
            #"tabnanny",
            #"telnetlib",
            #"test",
            #"textwrap",
            #"this",
            #"_threading_local",
            #"threading",
            #"timeit",
            #"tkinter",
            #"tokenize",
            #"token",
            #"traceback",
            #"trace",
            #"tty",
            #"turtledemo",
            #"turtle",
            #"unittest",
            #"urllib",
            #"uuid",
            #"uu",
            #"wave",
            #"weakref",
            #"webbrowser",
            #"wsgiref",
            #"xdrlib",
            #"xml",
            #"xmlrpc",
            #"zipfile",
        ])
    if minver >= 4:
        REQUIRED_MODULES.extend([
            'operator',
            '_collections_abc',
            '_bootlocale',
        ])

if is_pypy:
    # these are needed to correctly display the exceptions that may happen
    # during the bootstrap
    REQUIRED_MODULES.extend(['traceback', 'linecache'])

class Logger(object):

    """
    Logging object for use in command-line script.  Allows ranges of
    levels, to avoid some redundancy of displayed information.
    """

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    NOTIFY = (logging.INFO+logging.WARN)/2
    WARN = WARNING = logging.WARN
    ERROR = logging.ERROR
    FATAL = logging.FATAL

    LEVELS = [DEBUG, INFO, NOTIFY, WARN, ERROR, FATAL]

    def __init__(self, consumers):
        self.consumers = consumers
        self.indent = 0
        self.in_progress = None
        self.in_progress_hanging = False

    def debug(self, msg, *args, **kw):
        self.log(self.DEBUG, msg, *args, **kw)
    def info(self, msg, *args, **kw):
        self.log(self.INFO, msg, *args, **kw)
    def notify(self, msg, *args, **kw):
        self.log(self.NOTIFY, msg, *args, **kw)
    def warn(self, msg, *args, **kw):
        self.log(self.WARN, msg, *args, **kw)
    def error(self, msg, *args, **kw):
        self.log(self.ERROR, msg, *args, **kw)
    def fatal(self, msg, *args, **kw):
        self.log(self.FATAL, msg, *args, **kw)
    def log(self, level, msg, *args, **kw):
        if args:
            if kw:
                raise TypeError(
                    "You may give positional or keyword arguments, not both")
        args = args or kw
        rendered = None
        for consumer_level, consumer in self.consumers:
            if self.level_matches(level, consumer_level):
                if (self.in_progress_hanging
                    and consumer in (sys.stdout, sys.stderr)):
                    self.in_progress_hanging = False
                    sys.stdout.write('\n')
                    sys.stdout.flush()
                if rendered is None:
                    if args:
                        rendered = msg % args
                    else:
                        rendered = msg
                    rendered = ' '*self.indent + rendered
                if hasattr(consumer, 'write'):
                    consumer.write(rendered+'\n')
                else:
                    consumer(rendered)

    def start_progress(self, msg):
        assert not self.in_progress, (
            "Tried to start_progress(%r) while in_progress %r"
            % (msg, self.in_progress))
        if self.level_matches(self.NOTIFY, self._stdout_level()):
            sys.stdout.write(msg)
            sys.stdout.flush()
            self.in_progress_hanging = True
        else:
            self.in_progress_hanging = False
        self.in_progress = msg

    def end_progress(self, msg='done.'):
        assert self.in_progress, (
            "Tried to end_progress without start_progress")
        if self.stdout_level_matches(self.NOTIFY):
            if not self.in_progress_hanging:
                # Some message has been printed out since start_progress
                sys.stdout.write('...' + self.in_progress + msg + '\n')
                sys.stdout.flush()
            else:
                sys.stdout.write(msg + '\n')
                sys.stdout.flush()
        self.in_progress = None
        self.in_progress_hanging = False

    def show_progress(self):
        """If we are in a progress scope, and no log messages have been
        shown, write out another '.'"""
        if self.in_progress_hanging:
            sys.stdout.write('.')
            sys.stdout.flush()

    def stdout_level_matches(self, level):
        """Returns true if a message at this level will go to stdout"""
        return self.level_matches(level, self._stdout_level())

    def _stdout_level(self):
        """Returns the level that stdout runs at"""
        for level, consumer in self.consumers:
            if consumer is sys.stdout:
                return level
        return self.FATAL

    def level_matches(self, level, consumer_level):
        """
        >>> l = Logger([])
        >>> l.level_matches(3, 4)
        False
        >>> l.level_matches(3, 2)
        True
        >>> l.level_matches(slice(None, 3), 3)
        False
        >>> l.level_matches(slice(None, 3), 2)
        True
        >>> l.level_matches(slice(1, 3), 1)
        True
        >>> l.level_matches(slice(2, 3), 1)
        False
        """
        if isinstance(level, slice):
            start, stop = level.start, level.stop
            if start is not None and start > consumer_level:
                return False
            if stop is not None and stop <= consumer_level:
                return False
            return True
        else:
            return level >= consumer_level

    #@classmethod
    def level_for_integer(cls, level):
        levels = cls.LEVELS
        if level < 0:
            return levels[0]
        if level >= len(levels):
            return levels[-1]
        return levels[level]

    level_for_integer = classmethod(level_for_integer)

# create a silent logger just to prevent this from being undefined
# will be overridden with requested verbosity main() is called.
logger = Logger([(Logger.LEVELS[-1], sys.stdout)])

def mkdir(path):
    if not os.path.exists(path):
        logger.info('Creating %s', path)
        os.makedirs(path)
    else:
        logger.info('Directory %s already exists', path)

def copyfileordir(src, dest, symlink=True):
    if os.path.isdir(src):
        shutil.copytree(src, dest, symlink)
    else:
        shutil.copy2(src, dest)

def copyfile(src, dest, symlink=True):
    if not os.path.exists(src):
        # Some bad symlink in the src
        logger.warn('Cannot find file %s (bad symlink)', src)
        return
    if os.path.exists(dest):
        logger.debug('File %s already exists', dest)
        return
    if not os.path.exists(os.path.dirname(dest)):
        logger.info('Creating parent directories for %s', os.path.dirname(dest))
        os.makedirs(os.path.dirname(dest))
    if not os.path.islink(src):
        srcpath = os.path.abspath(src)
    else:
        srcpath = os.readlink(src)
    if symlink and hasattr(os, 'symlink') and not is_win:
        logger.info('Symlinking %s', dest)
        try:
            os.symlink(srcpath, dest)
        except (OSError, NotImplementedError):
            logger.info('Symlinking failed, copying to %s', dest)
            copyfileordir(src, dest, symlink)
    else:
        logger.info('Copying to %s', dest)
        copyfileordir(src, dest, symlink)

def writefile(dest, content, overwrite=True):
    if not os.path.exists(dest):
        logger.info('Writing %s', dest)
        f = open(dest, 'wb')
        f.write(content.encode('utf-8'))
        f.close()
        return
    else:
        f = open(dest, 'rb')
        c = f.read()
        f.close()
        if c != content.encode("utf-8"):
            if not overwrite:
                logger.notify('File %s exists with different content; not overwriting', dest)
                return
            logger.notify('Overwriting %s with new content', dest)
            f = open(dest, 'wb')
            f.write(content.encode('utf-8'))
            f.close()
        else:
            logger.info('Content %s already in place', dest)

def rmtree(dir):
    if os.path.exists(dir):
        logger.notify('Deleting tree %s', dir)
        shutil.rmtree(dir)
    else:
        logger.info('Do not need to delete %s; already gone', dir)

def make_exe(fn):
    if hasattr(os, 'chmod'):
        oldmode = os.stat(fn).st_mode & 0xFFF # 0o7777
        newmode = (oldmode | 0x16D) & 0xFFF # 0o555, 0o7777
        os.chmod(fn, newmode)
        logger.info('Changed mode of %s to %s', fn, oct(newmode))

def _find_file(filename, dirs):
    for dir in reversed(dirs):
        files = glob.glob(os.path.join(dir, filename))
        if files and os.path.isfile(files[0]):
            return True, files[0]
    return False, filename

def file_search_dirs():
    here = os.path.dirname(os.path.abspath(__file__))
    dirs = ['.', here,
            join(here, 'virtualenv_support')]
    if os.path.splitext(os.path.dirname(__file__))[0] != 'virtualenv':
        # Probably some boot script; just in case virtualenv is installed...
        try:
            import virtualenv
        except ImportError:
            pass
        else:
            dirs.append(os.path.join(os.path.dirname(virtualenv.__file__), 'virtualenv_support'))
    return [d for d in dirs if os.path.isdir(d)]


class UpdatingDefaultsHelpFormatter(optparse.IndentedHelpFormatter):
    """
    Custom help formatter for use in ConfigOptionParser that updates
    the defaults before expanding them, allowing them to show up correctly
    in the help listing
    """
    def expand_default(self, option):
        if self.parser is not None:
            self.parser.update_defaults(self.parser.defaults)
        return optparse.IndentedHelpFormatter.expand_default(self, option)


class ConfigOptionParser(optparse.OptionParser):
    """
    Custom option parser which updates its defaults by checking the
    configuration files and environmental variables
    """
    def __init__(self, *args, **kwargs):
        self.config = ConfigParser.RawConfigParser()
        self.files = self.get_config_files()
        self.config.read(self.files)
        optparse.OptionParser.__init__(self, *args, **kwargs)

    def get_config_files(self):
        config_file = os.environ.get('VIRTUALENV_CONFIG_FILE', False)
        if config_file and os.path.exists(config_file):
            return [config_file]
        return [default_config_file]

    def update_defaults(self, defaults):
        """
        Updates the given defaults with values from the config files and
        the environ. Does a little special handling for certain types of
        options (lists).
        """
        # Then go and look for the other sources of configuration:
        config = {}
        # 1. config files
        config.update(dict(self.get_config_section('virtualenv')))
        # 2. environmental variables
        config.update(dict(self.get_environ_vars()))
        # Then set the options with those values
        for key, val in config.items():
            key = key.replace('_', '-')
            if not key.startswith('--'):
                key = '--%s' % key  # only prefer long opts
            option = self.get_option(key)
            if option is not None:
                # ignore empty values
                if not val:
                    continue
                # handle multiline configs
                if option.action == 'append':
                    val = val.split()
                else:
                    option.nargs = 1
                if option.action == 'store_false':
                    val = not strtobool(val)
                elif option.action in ('store_true', 'count'):
                    val = strtobool(val)
                try:
                    val = option.convert_value(key, val)
                except optparse.OptionValueError:
                    e = sys.exc_info()[1]
                    print("An error occured during configuration: %s" % e)
                    sys.exit(3)
                defaults[option.dest] = val
        return defaults

    def get_config_section(self, name):
        """
        Get a section of a configuration
        """
        if self.config.has_section(name):
            return self.config.items(name)
        return []

    def get_environ_vars(self, prefix='VIRTUALENV_'):
        """
        Returns a generator with all environmental vars with prefix VIRTUALENV
        """
        for key, val in os.environ.items():
            if key.startswith(prefix):
                yield (key.replace(prefix, '').lower(), val)

    def get_default_values(self):
        """
        Overridding to make updating the defaults after instantiation of
        the option parser possible, update_defaults() does the dirty work.
        """
        if not self.process_default_values:
            # Old, pre-Optik 1.5 behaviour.
            return optparse.Values(self.defaults)

        defaults = self.update_defaults(self.defaults.copy())  # ours
        for option in self._get_all_options():
            default = defaults.get(option.dest)
            if isinstance(default, basestring):
                opt_str = option.get_opt_string()
                defaults[option.dest] = option.check_value(opt_str, default)
        return optparse.Values(defaults)


def main():
    parser = ConfigOptionParser(
        version=virtualenv_version,
        usage="%prog [OPTIONS] DEST_DIR",
        formatter=UpdatingDefaultsHelpFormatter())

    parser.add_option(
        '-v', '--verbose',
        action='count',
        dest='verbose',
        default=0,
        help="Increase verbosity.")

    parser.add_option(
        '-q', '--quiet',
        action='count',
        dest='quiet',
        default=0,
        help='Decrease verbosity.')

    parser.add_option(
        '-p', '--python',
        dest='python',
        metavar='PYTHON_EXE',
        help='The Python interpreter to use, e.g., --python=python2.5 will use the python2.5 '
        'interpreter to create the new environment.  The default is the interpreter that '
        'virtualenv was installed with (%s)' % sys.executable)

    parser.add_option(
        '--clear',
        dest='clear',
        action='store_true',
        help="Clear out the non-root install and start from scratch.")

    parser.set_defaults(system_site_packages=False)
    parser.add_option(
        '--no-site-packages',
        dest='system_site_packages',
        action='store_false',
        help="DEPRECATED. Retained only for backward compatibility. "
             "Not having access to global site-packages is now the default behavior.")

    parser.add_option(
        '--system-site-packages',
        dest='system_site_packages',
        action='store_true',
        help="Give the virtual environment access to the global site-packages.")

    parser.add_option(
        '--always-copy',
        dest='symlink',
        action='store_false',
        default=True,
        help="Always copy files rather than symlinking.")

    parser.add_option(
        '--unzip-setuptools',
        dest='unzip_setuptools',
        action='store_true',
        help="Unzip Setuptools when installing it.")

    parser.add_option(
        '--relocatable',
        dest='relocatable',
        action='store_true',
        help='Make an EXISTING virtualenv environment relocatable. '
             'This fixes up scripts and makes all .pth files relative.')

    parser.add_option(
        '--no-setuptools',
        dest='no_setuptools',
        action='store_true',
        help='Do not install setuptools (or pip) in the new virtualenv.')

    parser.add_option(
        '--no-pip',
        dest='no_pip',
        action='store_true',
        help='Do not install pip in the new virtualenv.')

    default_search_dirs = file_search_dirs()
    parser.add_option(
        '--extra-search-dir',
        dest="search_dirs",
        action="append",
        metavar='DIR',
        default=default_search_dirs,
        help="Directory to look for setuptools/pip distributions in. "
              "This option can be used multiple times.")

    parser.add_option(
        '--never-download',
        dest="never_download",
        action="store_true",
        default=True,
        help="DEPRECATED. Retained only for backward compatibility. This option has no effect. "
              "Virtualenv never downloads pip or setuptools.")

    parser.add_option(
        '--prompt',
        dest='prompt',
        help='Provides an alternative prompt prefix for this environment.')

    parser.add_option(
        '--setuptools',
        dest='setuptools',
        action='store_true',
        help="DEPRECATED. Retained only for backward compatibility. This option has no effect.")

    parser.add_option(
        '--distribute',
        dest='distribute',
        action='store_true',
        help="DEPRECATED. Retained only for backward compatibility. This option has no effect.")

    if 'extend_parser' in globals():
        extend_parser(parser)

    options, args = parser.parse_args()

    global logger

    if 'adjust_options' in globals():
        adjust_options(options, args)

    verbosity = options.verbose - options.quiet
    logger = Logger([(Logger.level_for_integer(2 - verbosity), sys.stdout)])

    if options.python and not os.environ.get('VIRTUALENV_INTERPRETER_RUNNING'):
        env = os.environ.copy()
        interpreter = resolve_interpreter(options.python)
        if interpreter == sys.executable:
            logger.warn('Already using interpreter %s' % interpreter)
        else:
            logger.notify('Running virtualenv with interpreter %s' % interpreter)
            env['VIRTUALENV_INTERPRETER_RUNNING'] = 'true'
            file = __file__
            if file.endswith('.pyc'):
                file = file[:-1]
            popen = subprocess.Popen([interpreter, file] + sys.argv[1:], env=env)
            raise SystemExit(popen.wait())

    if not args:
        print('You must provide a DEST_DIR')
        parser.print_help()
        sys.exit(2)
    if len(args) > 1:
        print('There must be only one argument: DEST_DIR (you gave %s)' % (
            ' '.join(args)))
        parser.print_help()
        sys.exit(2)

    home_dir = args[0]

    if os.environ.get('WORKING_ENV'):
        logger.fatal('ERROR: you cannot run virtualenv while in a workingenv')
        logger.fatal('Please deactivate your workingenv, then re-run this script')
        sys.exit(3)

    if 'PYTHONHOME' in os.environ:
        logger.warn('PYTHONHOME is set.  You *must* activate the virtualenv before using it')
        del os.environ['PYTHONHOME']

    if options.relocatable:
        make_environment_relocatable(home_dir)
        return

    if not options.never_download:
        logger.warn('The --never-download option is for backward compatibility only.')
        logger.warn('Setting it to false is no longer supported, and will be ignored.')

    create_environment(home_dir,
                       site_packages=options.system_site_packages,
                       clear=options.clear,
                       unzip_setuptools=options.unzip_setuptools,
                       prompt=options.prompt,
                       search_dirs=options.search_dirs,
                       never_download=True,
                       no_setuptools=options.no_setuptools,
                       no_pip=options.no_pip,
                       symlink=options.symlink)
    if 'after_install' in globals():
        after_install(options, home_dir)

def call_subprocess(cmd, show_stdout=True,
                    filter_stdout=None, cwd=None,
                    raise_on_returncode=True, extra_env=None,
                    remove_from_env=None):
    cmd_parts = []
    for part in cmd:
        if len(part) > 45:
            part = part[:20]+"..."+part[-20:]
        if ' ' in part or '\n' in part or '"' in part or "'" in part:
            part = '"%s"' % part.replace('"', '\\"')
        if hasattr(part, 'decode'):
            try:
                part = part.decode(sys.getdefaultencoding())
            except UnicodeDecodeError:
                part = part.decode(sys.getfilesystemencoding())
        cmd_parts.append(part)
    cmd_desc = ' '.join(cmd_parts)
    if show_stdout:
        stdout = None
    else:
        stdout = subprocess.PIPE
    logger.debug("Running command %s" % cmd_desc)
    if extra_env or remove_from_env:
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        if remove_from_env:
            for varname in remove_from_env:
                env.pop(varname, None)
    else:
        env = None
    try:
        proc = subprocess.Popen(
            cmd, stderr=subprocess.STDOUT, stdin=None, stdout=stdout,
            cwd=cwd, env=env)
    except Exception:
        e = sys.exc_info()[1]
        logger.fatal(
            "Error %s while executing command %s" % (e, cmd_desc))
        raise
    all_output = []
    if stdout is not None:
        stdout = proc.stdout
        encoding = sys.getdefaultencoding()
        fs_encoding = sys.getfilesystemencoding()
        while 1:
            line = stdout.readline()
            try:
                line = line.decode(encoding)
            except UnicodeDecodeError:
                line = line.decode(fs_encoding)
            if not line:
                break
            line = line.rstrip()
            all_output.append(line)
            if filter_stdout:
                level = filter_stdout(line)
                if isinstance(level, tuple):
                    level, line = level
                logger.log(level, line)
                if not logger.stdout_level_matches(level):
                    logger.show_progress()
            else:
                logger.info(line)
    else:
        proc.communicate()
    proc.wait()
    if proc.returncode:
        if raise_on_returncode:
            if all_output:
                logger.notify('Complete output from command %s:' % cmd_desc)
                logger.notify('\n'.join(all_output) + '\n----------------------------------------')
            raise OSError(
                "Command %s failed with error code %s"
                % (cmd_desc, proc.returncode))
        else:
            logger.warn(
                "Command %s had error code %s"
                % (cmd_desc, proc.returncode))

def filter_install_output(line):
    if line.strip().startswith('running'):
        return Logger.INFO
    return Logger.DEBUG

def find_wheels(projects, search_dirs):
    """Find wheels from which we can import PROJECTS.

    Scan through SEARCH_DIRS for a wheel for each PROJECT in turn. Return
    a list of the first wheel found for each PROJECT
    """

    wheels = []

    # Look through SEARCH_DIRS for the first suitable wheel. Don't bother
    # about version checking here, as this is simply to get something we can
    # then use to install the correct version.
    for project in projects:
        for dirname in search_dirs:
            # This relies on only having "universal" wheels available.
            # The pattern could be tightened to require -py2.py3-none-any.whl.
            files = glob.glob(os.path.join(dirname, project + '-*.whl'))
            if files:
                wheels.append(os.path.abspath(files[0]))
                break
        else:
            # We're out of luck, so quit with a suitable error
            logger.fatal('Cannot find a wheel for %s' % (project,))

    return wheels

def install_wheel(project_names, py_executable, search_dirs=None):
    if search_dirs is None:
        search_dirs = file_search_dirs()

    wheels = find_wheels(['setuptools', 'pip'], search_dirs)
    pythonpath = os.pathsep.join(wheels)
    findlinks = ' '.join(search_dirs)

    cmd = [
        py_executable, '-c',
        'import sys, pip; sys.exit(pip.main(["install", "--ignore-installed"] + sys.argv[1:]))',
    ] + project_names
    logger.start_progress('Installing %s...' % (', '.join(project_names)))
    logger.indent += 2
    try:
        call_subprocess(cmd, show_stdout=False,
            extra_env = {
                'PYTHONPATH': pythonpath,
                'PIP_FIND_LINKS': findlinks,
                'PIP_USE_WHEEL': '1',
                'PIP_PRE': '1',
                'PIP_NO_INDEX': '1'
            }
        )
    finally:
        logger.indent -= 2
        logger.end_progress()

def create_environment(home_dir, site_packages=False, clear=False,
                       unzip_setuptools=False,
                       prompt=None, search_dirs=None, never_download=False,
                       no_setuptools=False, no_pip=False, symlink=True):
    """
    Creates a new environment in ``home_dir``.

    If ``site_packages`` is true, then the global ``site-packages/``
    directory will be on the path.

    If ``clear`` is true (default False) then the environment will
    first be cleared.
    """
    home_dir, lib_dir, inc_dir, bin_dir = path_locations(home_dir)

    py_executable = os.path.abspath(install_python(
        home_dir, lib_dir, inc_dir, bin_dir,
        site_packages=site_packages, clear=clear, symlink=symlink))

    install_distutils(home_dir)

    if not no_setuptools:
        to_install = ['setuptools']
        if not no_pip:
            to_install.append('pip')
        install_wheel(to_install, py_executable, search_dirs)

    install_activate(home_dir, bin_dir, prompt)

def is_executable_file(fpath):
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

def path_locations(home_dir):
    """Return the path locations for the environment (where libraries are,
    where scripts go, etc)"""
    # XXX: We'd use distutils.sysconfig.get_python_inc/lib but its
    # prefix arg is broken: http://bugs.python.org/issue3386
    if is_win:
        # Windows has lots of problems with executables with spaces in
        # the name; this function will remove them (using the ~1
        # format):
        mkdir(home_dir)
        if ' ' in home_dir:
            import ctypes
            GetShortPathName = ctypes.windll.kernel32.GetShortPathNameW
            size = max(len(home_dir)+1, 256)
            buf = ctypes.create_unicode_buffer(size)
            try:
                u = unicode
            except NameError:
                u = str
            ret = GetShortPathName(u(home_dir), buf, size)
            if not ret:
                print('Error: the path "%s" has a space in it' % home_dir)
                print('We could not determine the short pathname for it.')
                print('Exiting.')
                sys.exit(3)
            home_dir = str(buf.value)
        lib_dir = join(home_dir, 'Lib')
        inc_dir = join(home_dir, 'Include')
        bin_dir = join(home_dir, 'Scripts')
    if is_jython:
        lib_dir = join(home_dir, 'Lib')
        inc_dir = join(home_dir, 'Include')
        bin_dir = join(home_dir, 'bin')
    elif is_pypy:
        lib_dir = home_dir
        inc_dir = join(home_dir, 'include')
        bin_dir = join(home_dir, 'bin')
    elif not is_win:
        lib_dir = join(home_dir, 'lib', py_version)
        multiarch_exec = '/usr/bin/multiarch-platform'
        if is_executable_file(multiarch_exec):
            # In Mageia (2) and Mandriva distros the include dir must be like:
            # virtualenv/include/multiarch-x86_64-linux/python2.7
            # instead of being virtualenv/include/python2.7
            p = subprocess.Popen(multiarch_exec, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()
            # stdout.strip is needed to remove newline character
            inc_dir = join(home_dir, 'include', stdout.strip(), py_version + abiflags)
        else:
            inc_dir = join(home_dir, 'include', py_version + abiflags)
        bin_dir = join(home_dir, 'bin')
    return home_dir, lib_dir, inc_dir, bin_dir


def change_prefix(filename, dst_prefix):
    prefixes = [sys.prefix]

    if is_darwin:
        prefixes.extend((
            os.path.join("/Library/Python", sys.version[:3], "site-packages"),
            os.path.join(sys.prefix, "Extras", "lib", "python"),
            os.path.join("~", "Library", "Python", sys.version[:3], "site-packages"),
            # Python 2.6 no-frameworks
            os.path.join("~", ".local", "lib","python", sys.version[:3], "site-packages"),
            # System Python 2.7 on OSX Mountain Lion
            os.path.join("~", "Library", "Python", sys.version[:3], "lib", "python", "site-packages")))

    if hasattr(sys, 'real_prefix'):
        prefixes.append(sys.real_prefix)
    if hasattr(sys, 'base_prefix'):
        prefixes.append(sys.base_prefix)
    prefixes = list(map(os.path.expanduser, prefixes))
    prefixes = list(map(os.path.abspath, prefixes))
    # Check longer prefixes first so we don't split in the middle of a filename
    prefixes = sorted(prefixes, key=len, reverse=True)
    filename = os.path.abspath(filename)
    for src_prefix in prefixes:
        if filename.startswith(src_prefix):
            _, relpath = filename.split(src_prefix, 1)
            if src_prefix != os.sep: # sys.prefix == "/"
                assert relpath[0] == os.sep
                relpath = relpath[1:]
            return join(dst_prefix, relpath)
    assert False, "Filename %s does not start with any of these prefixes: %s" % \
        (filename, prefixes)

def copy_required_modules(dst_prefix, symlink):
    import imp
    # If we are running under -p, we need to remove the current
    # directory from sys.path temporarily here, so that we
    # definitely get the modules from the site directory of
    # the interpreter we are running under, not the one
    # virtualenv.py is installed under (which might lead to py2/py3
    # incompatibility issues)
    _prev_sys_path = sys.path
    if os.environ.get('VIRTUALENV_INTERPRETER_RUNNING'):
        sys.path = sys.path[1:]
    try:
        for modname in REQUIRED_MODULES:
            if modname in sys.builtin_module_names:
                logger.info("Ignoring built-in bootstrap module: %s" % modname)
                continue
            try:
                f, filename, _ = imp.find_module(modname)
            except ImportError:
                logger.info("Cannot import bootstrap module: %s" % modname)
            else:
                if f is not None:
                    f.close()
                # special-case custom readline.so on OS X, but not for pypy:
                if modname == 'readline' and sys.platform == 'darwin' and not (
                        is_pypy or filename.endswith(join('lib-dynload', 'readline.so'))):
                    dst_filename = join(dst_prefix, 'lib', 'python%s' % sys.version[:3], 'readline.so')
                elif modname == 'readline' and sys.platform == 'win32':
                    # special-case for Windows, where readline is not a
                    # standard module, though it may have been installed in
                    # site-packages by a third-party package
                    pass
                else:
                    dst_filename = change_prefix(filename, dst_prefix)
                copyfile(filename, dst_filename, symlink)
                if filename.endswith('.pyc'):
                    pyfile = filename[:-1]
                    if os.path.exists(pyfile):
                        copyfile(pyfile, dst_filename[:-1], symlink)
    finally:
        sys.path = _prev_sys_path


def subst_path(prefix_path, prefix, home_dir):
    prefix_path = os.path.normpath(prefix_path)
    prefix = os.path.normpath(prefix)
    home_dir = os.path.normpath(home_dir)
    if not prefix_path.startswith(prefix):
        logger.warn('Path not in prefix %r %r', prefix_path, prefix)
        return
    return prefix_path.replace(prefix, home_dir, 1)


def install_python(home_dir, lib_dir, inc_dir, bin_dir, site_packages, clear, symlink=True):
    """Install just the base environment, no distutils patches etc"""
    if sys.executable.startswith(bin_dir):
        print('Please use the *system* python to run this script')
        return

    if clear:
        rmtree(lib_dir)
        ## FIXME: why not delete it?
        ## Maybe it should delete everything with #!/path/to/venv/python in it
        logger.notify('Not deleting %s', bin_dir)

    if hasattr(sys, 'real_prefix'):
        logger.notify('Using real prefix %r' % sys.real_prefix)
        prefix = sys.real_prefix
    elif hasattr(sys, 'base_prefix'):
        logger.notify('Using base prefix %r' % sys.base_prefix)
        prefix = sys.base_prefix
    else:
        prefix = sys.prefix
    mkdir(lib_dir)
    fix_lib64(lib_dir, symlink)
    stdlib_dirs = [os.path.dirname(os.__file__)]
    if is_win:
        stdlib_dirs.append(join(os.path.dirname(stdlib_dirs[0]), 'DLLs'))
    elif is_darwin:
        stdlib_dirs.append(join(stdlib_dirs[0], 'site-packages'))
    if hasattr(os, 'symlink'):
        logger.info('Symlinking Python bootstrap modules')
    else:
        logger.info('Copying Python bootstrap modules')
    logger.indent += 2
    try:
        # copy required files...
        for stdlib_dir in stdlib_dirs:
            if not os.path.isdir(stdlib_dir):
                continue
            for fn in os.listdir(stdlib_dir):
                bn = os.path.splitext(fn)[0]
                if fn != 'site-packages' and bn in REQUIRED_FILES:
                    copyfile(join(stdlib_dir, fn), join(lib_dir, fn), symlink)
        # ...and modules
        copy_required_modules(home_dir, symlink)
    finally:
        logger.indent -= 2
    mkdir(join(lib_dir, 'site-packages'))
    import site
    site_filename = site.__file__
    if site_filename.endswith('.pyc'):
        site_filename = site_filename[:-1]
    elif site_filename.endswith('$py.class'):
        site_filename = site_filename.replace('$py.class', '.py')
    site_filename_dst = change_prefix(site_filename, home_dir)
    site_dir = os.path.dirname(site_filename_dst)
    writefile(site_filename_dst, SITE_PY)
    writefile(join(site_dir, 'orig-prefix.txt'), prefix)
    site_packages_filename = join(site_dir, 'no-global-site-packages.txt')
    if not site_packages:
        writefile(site_packages_filename, '')

    if is_pypy or is_win:
        stdinc_dir = join(prefix, 'include')
    else:
        stdinc_dir = join(prefix, 'include', py_version + abiflags)
    if os.path.exists(stdinc_dir):
        copyfile(stdinc_dir, inc_dir, symlink)
    else:
        logger.debug('No include dir %s' % stdinc_dir)

    platinc_dir = distutils.sysconfig.get_python_inc(plat_specific=1)
    if platinc_dir != stdinc_dir:
        platinc_dest = distutils.sysconfig.get_python_inc(
            plat_specific=1, prefix=home_dir)
        if platinc_dir == platinc_dest:
            # Do platinc_dest manually due to a CPython bug;
            # not http://bugs.python.org/issue3386 but a close cousin
            platinc_dest = subst_path(platinc_dir, prefix, home_dir)
        if platinc_dest:
            # PyPy's stdinc_dir and prefix are relative to the original binary
            # (traversing virtualenvs), whereas the platinc_dir is relative to
            # the inner virtualenv and ignores the prefix argument.
            # This seems more evolved than designed.
            copyfile(platinc_dir, platinc_dest, symlink)

    # pypy never uses exec_prefix, just ignore it
    if sys.exec_prefix != prefix and not is_pypy:
        if is_win:
            exec_dir = join(sys.exec_prefix, 'lib')
        elif is_jython:
            exec_dir = join(sys.exec_prefix, 'Lib')
        else:
            exec_dir = join(sys.exec_prefix, 'lib', py_version)
        for fn in os.listdir(exec_dir):
            copyfile(join(exec_dir, fn), join(lib_dir, fn), symlink)

    if is_jython:
        # Jython has either jython-dev.jar and javalib/ dir, or just
        # jython.jar
        for name in 'jython-dev.jar', 'javalib', 'jython.jar':
            src = join(prefix, name)
            if os.path.exists(src):
                copyfile(src, join(home_dir, name), symlink)
        # XXX: registry should always exist after Jython 2.5rc1
        src = join(prefix, 'registry')
        if os.path.exists(src):
            copyfile(src, join(home_dir, 'registry'), symlink=False)
        copyfile(join(prefix, 'cachedir'), join(home_dir, 'cachedir'),
                 symlink=False)

    mkdir(bin_dir)
    py_executable = join(bin_dir, os.path.basename(sys.executable))
    if 'Python.framework' in prefix:
        # OS X framework builds cause validation to break
        # https://github.com/pypa/virtualenv/issues/322
        if os.environ.get('__PYVENV_LAUNCHER__'):
            del os.environ["__PYVENV_LAUNCHER__"]
        if re.search(r'/Python(?:-32|-64)*$', py_executable):
            # The name of the python executable is not quite what
            # we want, rename it.
            py_executable = os.path.join(
                    os.path.dirname(py_executable), 'python')

    logger.notify('New %s executable in %s', expected_exe, py_executable)
    pcbuild_dir = os.path.dirname(sys.executable)
    pyd_pth = os.path.join(lib_dir, 'site-packages', 'virtualenv_builddir_pyd.pth')
    if is_win and os.path.exists(os.path.join(pcbuild_dir, 'build.bat')):
        logger.notify('Detected python running from build directory %s', pcbuild_dir)
        logger.notify('Writing .pth file linking to build directory for *.pyd files')
        writefile(pyd_pth, pcbuild_dir)
    else:
        pcbuild_dir = None
        if os.path.exists(pyd_pth):
            logger.info('Deleting %s (not Windows env or not build directory python)' % pyd_pth)
            os.unlink(pyd_pth)

    if sys.executable != py_executable:
        ## FIXME: could I just hard link?
        executable = sys.executable
        shutil.copyfile(executable, py_executable)
        make_exe(py_executable)
        if is_win or is_cygwin:
            pythonw = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
            if os.path.exists(pythonw):
                logger.info('Also created pythonw.exe')
                shutil.copyfile(pythonw, os.path.join(os.path.dirname(py_executable), 'pythonw.exe'))
            python_d = os.path.join(os.path.dirname(sys.executable), 'python_d.exe')
            python_d_dest = os.path.join(os.path.dirname(py_executable), 'python_d.exe')
            if os.path.exists(python_d):
                logger.info('Also created python_d.exe')
                shutil.copyfile(python_d, python_d_dest)
            elif os.path.exists(python_d_dest):
                logger.info('Removed python_d.exe as it is no longer at the source')
                os.unlink(python_d_dest)
            # we need to copy the DLL to enforce that windows will load the correct one.
            # may not exist if we are cygwin.
            py_executable_dll = 'python%s%s.dll' % (
                sys.version_info[0], sys.version_info[1])
            py_executable_dll_d = 'python%s%s_d.dll' % (
                sys.version_info[0], sys.version_info[1])
            pythondll = os.path.join(os.path.dirname(sys.executable), py_executable_dll)
            pythondll_d = os.path.join(os.path.dirname(sys.executable), py_executable_dll_d)
            pythondll_d_dest = os.path.join(os.path.dirname(py_executable), py_executable_dll_d)
            if os.path.exists(pythondll):
                logger.info('Also created %s' % py_executable_dll)
                shutil.copyfile(pythondll, os.path.join(os.path.dirname(py_executable), py_executable_dll))
            if os.path.exists(pythondll_d):
                logger.info('Also created %s' % py_executable_dll_d)
                shutil.copyfile(pythondll_d, pythondll_d_dest)
            elif os.path.exists(pythondll_d_dest):
                logger.info('Removed %s as the source does not exist' % pythondll_d_dest)
                os.unlink(pythondll_d_dest)
        if is_pypy:
            # make a symlink python --> pypy-c
            python_executable = os.path.join(os.path.dirname(py_executable), 'python')
            if sys.platform in ('win32', 'cygwin'):
                python_executable += '.exe'
            logger.info('Also created executable %s' % python_executable)
            copyfile(py_executable, python_executable, symlink)

            if is_win:
                for name in 'libexpat.dll', 'libpypy.dll', 'libpypy-c.dll', 'libeay32.dll', 'ssleay32.dll', 'sqlite.dll':
                    src = join(prefix, name)
                    if os.path.exists(src):
                        copyfile(src, join(bin_dir, name), symlink)

    if os.path.splitext(os.path.basename(py_executable))[0] != expected_exe:
        secondary_exe = os.path.join(os.path.dirname(py_executable),
                                     expected_exe)
        py_executable_ext = os.path.splitext(py_executable)[1]
        if py_executable_ext.lower() == '.exe':
            # python2.4 gives an extension of '.4' :P
            secondary_exe += py_executable_ext
        if os.path.exists(secondary_exe):
            logger.warn('Not overwriting existing %s script %s (you must use %s)'
                        % (expected_exe, secondary_exe, py_executable))
        else:
            logger.notify('Also creating executable in %s' % secondary_exe)
            shutil.copyfile(sys.executable, secondary_exe)
            make_exe(secondary_exe)

    if '.framework' in prefix:
        if 'Python.framework' in prefix:
            logger.debug('MacOSX Python framework detected')
            # Make sure we use the the embedded interpreter inside
            # the framework, even if sys.executable points to
            # the stub executable in ${sys.prefix}/bin
            # See http://groups.google.com/group/python-virtualenv/
            #                              browse_thread/thread/17cab2f85da75951
            original_python = os.path.join(
                prefix, 'Resources/Python.app/Contents/MacOS/Python')
        if 'EPD' in prefix:
            logger.debug('EPD framework detected')
            original_python = os.path.join(prefix, 'bin/python')
        shutil.copy(original_python, py_executable)

        # Copy the framework's dylib into the virtual
        # environment
        virtual_lib = os.path.join(home_dir, '.Python')

        if os.path.exists(virtual_lib):
            os.unlink(virtual_lib)
        copyfile(
            os.path.join(prefix, 'Python'),
            virtual_lib,
            symlink)

        # And then change the install_name of the copied python executable
        try:
            mach_o_change(py_executable,
                          os.path.join(prefix, 'Python'),
                          '@executable_path/../.Python')
        except:
            e = sys.exc_info()[1]
            logger.warn("Could not call mach_o_change: %s. "
                        "Trying to call install_name_tool instead." % e)
            try:
                call_subprocess(
                    ["install_name_tool", "-change",
                     os.path.join(prefix, 'Python'),
                     '@executable_path/../.Python',
                     py_executable])
            except:
                logger.fatal("Could not call install_name_tool -- you must "
                             "have Apple's development tools installed")
                raise

    if not is_win:
        # Ensure that 'python', 'pythonX' and 'pythonX.Y' all exist
        py_exe_version_major = 'python%s' % sys.version_info[0]
        py_exe_version_major_minor = 'python%s.%s' % (
            sys.version_info[0], sys.version_info[1])
        py_exe_no_version = 'python'
        required_symlinks = [ py_exe_no_version, py_exe_version_major,
                         py_exe_version_major_minor ]

        py_executable_base = os.path.basename(py_executable)

        if py_executable_base in required_symlinks:
            # Don't try to symlink to yourself.
            required_symlinks.remove(py_executable_base)

        for pth in required_symlinks:
            full_pth = join(bin_dir, pth)
            if os.path.exists(full_pth):
                os.unlink(full_pth)
            if symlink:
                os.symlink(py_executable_base, full_pth)
            else:
                copyfile(py_executable, full_pth, symlink)

    if is_win and ' ' in py_executable:
        # There's a bug with subprocess on Windows when using a first
        # argument that has a space in it.  Instead we have to quote
        # the value:
        py_executable = '"%s"' % py_executable
    # NOTE: keep this check as one line, cmd.exe doesn't cope with line breaks
    cmd = [py_executable, '-c', 'import sys;out=sys.stdout;'
        'getattr(out, "buffer", out).write(sys.prefix.encode("utf-8"))']
    logger.info('Testing executable with %s %s "%s"' % tuple(cmd))
    try:
        proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE)
        proc_stdout, proc_stderr = proc.communicate()
    except OSError:
        e = sys.exc_info()[1]
        if e.errno == errno.EACCES:
            logger.fatal('ERROR: The executable %s could not be run: %s' % (py_executable, e))
            sys.exit(100)
        else:
            raise e

    proc_stdout = proc_stdout.strip().decode("utf-8")
    proc_stdout = os.path.normcase(os.path.abspath(proc_stdout))
    norm_home_dir = os.path.normcase(os.path.abspath(home_dir))
    if hasattr(norm_home_dir, 'decode'):
        norm_home_dir = norm_home_dir.decode(sys.getfilesystemencoding())
    if proc_stdout != norm_home_dir:
        logger.fatal(
            'ERROR: The executable %s is not functioning' % py_executable)
        logger.fatal(
            'ERROR: It thinks sys.prefix is %r (should be %r)'
            % (proc_stdout, norm_home_dir))
        logger.fatal(
            'ERROR: virtualenv is not compatible with this system or executable')
        if is_win:
            logger.fatal(
                'Note: some Windows users have reported this error when they '
                'installed Python for "Only this user" or have multiple '
                'versions of Python installed. Copying the appropriate '
                'PythonXX.dll to the virtualenv Scripts/ directory may fix '
                'this problem.')
        sys.exit(100)
    else:
        logger.info('Got sys.prefix result: %r' % proc_stdout)

    pydistutils = os.path.expanduser('~/.pydistutils.cfg')
    if os.path.exists(pydistutils):
        logger.notify('Please make sure you remove any previous custom paths from '
                      'your %s file.' % pydistutils)
    ## FIXME: really this should be calculated earlier

    fix_local_scheme(home_dir, symlink)

    if site_packages:
        if os.path.exists(site_packages_filename):
            logger.info('Deleting %s' % site_packages_filename)
            os.unlink(site_packages_filename)

    return py_executable


def install_activate(home_dir, bin_dir, prompt=None):
    home_dir = os.path.abspath(home_dir)
    if is_win or is_jython and os._name == 'nt':
        files = {
            'activate.bat': ACTIVATE_BAT,
            'deactivate.bat': DEACTIVATE_BAT,
            'activate.ps1': ACTIVATE_PS,
        }

        # MSYS needs paths of the form /c/path/to/file
        drive, tail = os.path.splitdrive(home_dir.replace(os.sep, '/'))
        home_dir_msys = (drive and "/%s%s" or "%s%s") % (drive[:1], tail)

        # Run-time conditional enables (basic) Cygwin compatibility
        home_dir_sh = ("""$(if [ "$OSTYPE" "==" "cygwin" ]; then cygpath -u '%s'; else echo '%s'; fi;)""" %
                       (home_dir, home_dir_msys))
        files['activate'] = ACTIVATE_SH.replace('__VIRTUAL_ENV__', home_dir_sh)

    else:
        files = {'activate': ACTIVATE_SH}

        # suppling activate.fish in addition to, not instead of, the
        # bash script support.
        files['activate.fish'] = ACTIVATE_FISH

        # same for csh/tcsh support...
        files['activate.csh'] = ACTIVATE_CSH

    files['activate_this.py'] = ACTIVATE_THIS
    if hasattr(home_dir, 'decode'):
        home_dir = home_dir.decode(sys.getfilesystemencoding())
    vname = os.path.basename(home_dir)
    for name, content in files.items():
        content = content.replace('__VIRTUAL_PROMPT__', prompt or '')
        content = content.replace('__VIRTUAL_WINPROMPT__', prompt or '(%s)' % vname)
        content = content.replace('__VIRTUAL_ENV__', home_dir)
        content = content.replace('__VIRTUAL_NAME__', vname)
        content = content.replace('__BIN_NAME__', os.path.basename(bin_dir))
        writefile(os.path.join(bin_dir, name), content)

def install_distutils(home_dir):
    distutils_path = change_prefix(distutils.__path__[0], home_dir)
    mkdir(distutils_path)
    ## FIXME: maybe this prefix setting should only be put in place if
    ## there's a local distutils.cfg with a prefix setting?
    home_dir = os.path.abspath(home_dir)
    ## FIXME: this is breaking things, removing for now:
    #distutils_cfg = DISTUTILS_CFG + "\n[install]\nprefix=%s\n" % home_dir
    writefile(os.path.join(distutils_path, '__init__.py'), DISTUTILS_INIT)
    writefile(os.path.join(distutils_path, 'distutils.cfg'), DISTUTILS_CFG, overwrite=False)

def fix_local_scheme(home_dir, symlink=True):
    """
    Platforms that use the "posix_local" install scheme (like Ubuntu with
    Python 2.7) need to be given an additional "local" location, sigh.
    """
    try:
        import sysconfig
    except ImportError:
        pass
    else:
        if sysconfig._get_default_scheme() == 'posix_local':
            local_path = os.path.join(home_dir, 'local')
            if not os.path.exists(local_path):
                os.mkdir(local_path)
                for subdir_name in os.listdir(home_dir):
                    if subdir_name == 'local':
                        continue
                    copyfile(os.path.abspath(os.path.join(home_dir, subdir_name)), \
                                                            os.path.join(local_path, subdir_name), symlink)

def fix_lib64(lib_dir, symlink=True):
    """
    Some platforms (particularly Gentoo on x64) put things in lib64/pythonX.Y
    instead of lib/pythonX.Y.  If this is such a platform we'll just create a
    symlink so lib64 points to lib
    """
    if [p for p in distutils.sysconfig.get_config_vars().values()
        if isinstance(p, basestring) and 'lib64' in p]:
        # PyPy's library path scheme is not affected by this.
        # Return early or we will die on the following assert.
        if is_pypy:
            logger.debug('PyPy detected, skipping lib64 symlinking')
            return

        logger.debug('This system uses lib64; symlinking lib64 to lib')

        assert os.path.basename(lib_dir) == 'python%s' % sys.version[:3], (
            "Unexpected python lib dir: %r" % lib_dir)
        lib_parent = os.path.dirname(lib_dir)
        top_level = os.path.dirname(lib_parent)
        lib_dir = os.path.join(top_level, 'lib')
        lib64_link = os.path.join(top_level, 'lib64')
        assert os.path.basename(lib_parent) == 'lib', (
            "Unexpected parent dir: %r" % lib_parent)
        if os.path.lexists(lib64_link):
            return
        cp_or_ln = (os.symlink if symlink else copyfile)
        cp_or_ln('lib', lib64_link)

def resolve_interpreter(exe):
    """
    If the executable given isn't an absolute path, search $PATH for the interpreter
    """
    # If the "executable" is a version number, get the installed executable for
    # that version
    python_versions = get_installed_pythons()
    if exe in python_versions:
        exe = python_versions[exe]

    if os.path.abspath(exe) != exe:
        paths = os.environ.get('PATH', '').split(os.pathsep)
        for path in paths:
            if os.path.exists(os.path.join(path, exe)):
                exe = os.path.join(path, exe)
                break
    if not os.path.exists(exe):
        logger.fatal('The executable %s (from --python=%s) does not exist' % (exe, exe))
        raise SystemExit(3)
    if not is_executable(exe):
        logger.fatal('The executable %s (from --python=%s) is not executable' % (exe, exe))
        raise SystemExit(3)
    return exe

def is_executable(exe):
    """Checks a file is executable"""
    return os.access(exe, os.X_OK)

############################################################
## Relocating the environment:

def make_environment_relocatable(home_dir):
    """
    Makes the already-existing environment use relative paths, and takes out
    the #!-based environment selection in scripts.
    """
    home_dir, lib_dir, inc_dir, bin_dir = path_locations(home_dir)
    activate_this = os.path.join(bin_dir, 'activate_this.py')
    if not os.path.exists(activate_this):
        logger.fatal(
            'The environment doesn\'t have a file %s -- please re-run virtualenv '
            'on this environment to update it' % activate_this)
    fixup_scripts(home_dir, bin_dir)
    fixup_pth_and_egg_link(home_dir)
    ## FIXME: need to fix up distutils.cfg

OK_ABS_SCRIPTS = ['python', 'python%s' % sys.version[:3],
                  'activate', 'activate.bat', 'activate_this.py',
                  'activate.fish', 'activate.csh']

def fixup_scripts(home_dir, bin_dir):
    if is_win:
        new_shebang_args = (
            '%s /c' % os.path.normcase(os.environ.get('COMSPEC', 'cmd.exe')),
            '', '.exe')
    else:
        new_shebang_args = ('/usr/bin/env', sys.version[:3], '')

    # This is what we expect at the top of scripts:
    shebang = '#!%s' % os.path.normcase(os.path.join(
        os.path.abspath(bin_dir), 'python%s' % new_shebang_args[2]))
    # This is what we'll put:
    new_shebang = '#!%s python%s%s' % new_shebang_args

    for filename in os.listdir(bin_dir):
        filename = os.path.join(bin_dir, filename)
        if not os.path.isfile(filename):
            # ignore subdirs, e.g. .svn ones.
            continue
        f = open(filename, 'rb')
        try:
            try:
                lines = f.read().decode('utf-8').splitlines()
            except UnicodeDecodeError:
                # This is probably a binary program instead
                # of a script, so just ignore it.
                continue
        finally:
            f.close()
        if not lines:
            logger.warn('Script %s is an empty file' % filename)
            continue

        old_shebang = lines[0].strip()
        old_shebang = old_shebang[0:2] + os.path.normcase(old_shebang[2:])

        if not old_shebang.startswith(shebang):
            if os.path.basename(filename) in OK_ABS_SCRIPTS:
                logger.debug('Cannot make script %s relative' % filename)
            elif lines[0].strip() == new_shebang:
                logger.info('Script %s has already been made relative' % filename)
            else:
                logger.warn('Script %s cannot be made relative (it\'s not a normal script that starts with %s)'
                            % (filename, shebang))
            continue
        logger.notify('Making script %s relative' % filename)
        script = relative_script([new_shebang] + lines[1:])
        f = open(filename, 'wb')
        f.write('\n'.join(script).encode('utf-8'))
        f.close()

def relative_script(lines):
    "Return a script that'll work in a relocatable environment."
    activate = "import os; activate_this=os.path.join(os.path.dirname(os.path.realpath(__file__)), 'activate_this.py'); exec(compile(open(activate_this).read(), activate_this, 'exec'), dict(__file__=activate_this)); del os, activate_this"
    # Find the last future statement in the script. If we insert the activation
    # line before a future statement, Python will raise a SyntaxError.
    activate_at = None
    for idx, line in reversed(list(enumerate(lines))):
        if line.split()[:3] == ['from', '__future__', 'import']:
            activate_at = idx + 1
            break
    if activate_at is None:
        # Activate after the shebang.
        activate_at = 1
    return lines[:activate_at] + ['', activate, ''] + lines[activate_at:]

def fixup_pth_and_egg_link(home_dir, sys_path=None):
    """Makes .pth and .egg-link files use relative paths"""
    home_dir = os.path.normcase(os.path.abspath(home_dir))
    if sys_path is None:
        sys_path = sys.path
    for path in sys_path:
        if not path:
            path = '.'
        if not os.path.isdir(path):
            continue
        path = os.path.normcase(os.path.abspath(path))
        if not path.startswith(home_dir):
            logger.debug('Skipping system (non-environment) directory %s' % path)
            continue
        for filename in os.listdir(path):
            filename = os.path.join(path, filename)
            if filename.endswith('.pth'):
                if not os.access(filename, os.W_OK):
                    logger.warn('Cannot write .pth file %s, skipping' % filename)
                else:
                    fixup_pth_file(filename)
            if filename.endswith('.egg-link'):
                if not os.access(filename, os.W_OK):
                    logger.warn('Cannot write .egg-link file %s, skipping' % filename)
                else:
                    fixup_egg_link(filename)

def fixup_pth_file(filename):
    lines = []
    prev_lines = []
    f = open(filename)
    prev_lines = f.readlines()
    f.close()
    for line in prev_lines:
        line = line.strip()
        if (not line or line.startswith('#') or line.startswith('import ')
            or os.path.abspath(line) != line):
            lines.append(line)
        else:
            new_value = make_relative_path(filename, line)
            if line != new_value:
                logger.debug('Rewriting path %s as %s (in %s)' % (line, new_value, filename))
            lines.append(new_value)
    if lines == prev_lines:
        logger.info('No changes to .pth file %s' % filename)
        return
    logger.notify('Making paths in .pth file %s relative' % filename)
    f = open(filename, 'w')
    f.write('\n'.join(lines) + '\n')
    f.close()

def fixup_egg_link(filename):
    f = open(filename)
    link = f.readline().strip()
    f.close()
    if os.path.abspath(link) != link:
        logger.debug('Link in %s already relative' % filename)
        return
    new_link = make_relative_path(filename, link)
    logger.notify('Rewriting link %s in %s as %s' % (link, filename, new_link))
    f = open(filename, 'w')
    f.write(new_link)
    f.close()

def make_relative_path(source, dest, dest_is_directory=True):
    """
    Make a filename relative, where the filename is dest, and it is
    being referred to from the filename source.

        >>> make_relative_path('/usr/share/something/a-file.pth',
        ...                    '/usr/share/another-place/src/Directory')
        '../another-place/src/Directory'
        >>> make_relative_path('/usr/share/something/a-file.pth',
        ...                    '/home/user/src/Directory')
        '../../../home/user/src/Directory'
        >>> make_relative_path('/usr/share/a-file.pth', '/usr/share/')
        './'
    """
    source = os.path.dirname(source)
    if not dest_is_directory:
        dest_filename = os.path.basename(dest)
        dest = os.path.dirname(dest)
    dest = os.path.normpath(os.path.abspath(dest))
    source = os.path.normpath(os.path.abspath(source))
    dest_parts = dest.strip(os.path.sep).split(os.path.sep)
    source_parts = source.strip(os.path.sep).split(os.path.sep)
    while dest_parts and source_parts and dest_parts[0] == source_parts[0]:
        dest_parts.pop(0)
        source_parts.pop(0)
    full_parts = ['..']*len(source_parts) + dest_parts
    if not dest_is_directory:
        full_parts.append(dest_filename)
    if not full_parts:
        # Special case for the current directory (otherwise it'd be '')
        return './'
    return os.path.sep.join(full_parts)



############################################################
## Bootstrap script creation:

def create_bootstrap_script(extra_text, python_version=''):
    """
    Creates a bootstrap script, which is like this script but with
    extend_parser, adjust_options, and after_install hooks.

    This returns a string that (written to disk of course) can be used
    as a bootstrap script with your own customizations.  The script
    will be the standard virtualenv.py script, with your extra text
    added (your extra text should be Python code).

    If you include these functions, they will be called:

    ``extend_parser(optparse_parser)``:
        You can add or remove options from the parser here.

    ``adjust_options(options, args)``:
        You can change options here, or change the args (if you accept
        different kinds of arguments, be sure you modify ``args`` so it is
        only ``[DEST_DIR]``).

    ``after_install(options, home_dir)``:

        After everything is installed, this function is called.  This
        is probably the function you are most likely to use.  An
        example would be::

            def after_install(options, home_dir):
                subprocess.call([join(home_dir, 'bin', 'easy_install'),
                                 'MyPackage'])
                subprocess.call([join(home_dir, 'bin', 'my-package-script'),
                                 'setup', home_dir])

        This example immediately installs a package, and runs a setup
        script from that package.

    If you provide something like ``python_version='2.5'`` then the
    script will start with ``#!/usr/bin/env python2.5`` instead of
    ``#!/usr/bin/env python``.  You can use this when the script must
    be run with a particular Python version.
    """
    filename = __file__
    if filename.endswith('.pyc'):
        filename = filename[:-1]
    f = codecs.open(filename, 'r', encoding='utf-8')
    content = f.read()
    f.close()
    py_exe = 'python%s' % python_version
    content = (('#!/usr/bin/env %s\n' % py_exe)
               + '## WARNING: This file is generated\n'
               + content)
    return content.replace('##EXT' 'END##', extra_text)

##EXTEND##

def convert(s):
    b = base64.b64decode(s.encode('ascii'))
    return zlib.decompress(b).decode('utf-8')

##file site.py
SITE_PY = convert("""
eJzFPf1z2zaWv/OvwMqToZTIdOJ0e3tOnRsncVrvuYm3SWdz63q0lARZrCmSJUjL2pu7v/3eBwAC
JCXbm+6cphNLJPDw8PC+8PAeOhgMTopCZnOxyud1KoWScTlbiiKulkos8lJUy6Sc7xdxWW3g6ewm
vpZKVLlQGxVhqygInn7lJ3gqPi8TZVCAb3Fd5au4SmZxmm5EsiryspJzMa/LJLsWSZZUSZwm/4AW
eRaJp1+PQXCWCZh5mshS3MpSAVwl8oW42FTLPBPDusA5v4j+GL8cjYWalUlRQYNS4wwUWcZVkEk5
BzShZa2AlEkl91UhZ8kimdmG67xO56JI45kUf/87T42ahmGg8pVcL2UpRQbIAEwJsArEA74mpZjl
cxkJ8UbOYhyAnzfEChjaGNdMIRmzXKR5dg1zyuRMKhWXGzGc1hUBIpTFPAecEsCgStI0WOfljRrB
ktJ6rOGRiJk9/Mkwe8A8cfwu5wCOH7Pg5yy5GzNs4B4EVy2ZbUq5SO5EjGDhp7yTs4l+NkwWYp4s
FkCDrBphk4ARUCJNpgcFLcd3eoVeHxBWlitjGEMiytyYX1KPKDirRJwqYNu6QBopwvydnCZxBtTI
bmE4gAgkDfrGmSeqsuPQ7EQOAEpcxwqkZKXEcBUnGTDrj/GM0P5rks3ztRoRBWC1lPi1VpU7/2EP
AaC1Q4BxgItlVrPO0uRGppsRIPAZsC+lqtMKBWKelHJW5WUiFQEA1DZC3gHSYxGXUpOQOdPI7Zjo
TzRJMlxYFDAUeHyJJFkk13VJEiYWCXAucMX7jz+Jd6dvzk4+aB4zwFhmr1eAM0ChhXZwggHEQa3K
gzQHgY6Cc/wj4vkchewaxwe8mgYH9650MIS5F1G7j7PgQHa9uHoYmGMFyoTGCqjff0OXsVoCff7n
nvUOgpNtVKGJ87f1MgeZzOKVFMuY+Qs5I/hOw3kdFdXyFXCDQjgVkErh4iCCCcIDkrg0G+aZFAWw
WJpkchQAhabU1l9FYIUPebZPa93iBIBQBhm8dJ6NaMRMwkS7sF6hvjCNNzQz3SSw67zKS1IcwP/Z
jHRRGmc3hKMihuJvU3mdZBkihLwQhHshDaxuEuDEeSTOqRXpBdNIhKy9uCWKRA28hEwHPCnv4lWR
yjGLL+rW3WqEBpOVMGudMsdBy4rUK61aM9Ve3juMvrS4jtCslqUE4PXUE7pFno/FFHQ2YVPEKxav
ap0T5wQ98kSdkCeoJfTF70DRE6XqlbQvkVdAsxBDBYs8TfM1kOwoCITYw0bGKPvMCW/hHfwLcPHf
VFazZRA4I1nAGhQivw0UAgGTIDPN1RoJj9s0K7eVTJKxpsjLuSxpqIcR+4ARf2BjnGvwIa+0UePp
4irnq6RClTTVJjNhi5eFFevHVzxvmAZYbkU0M00bOq1wemmxjKfSuCRTuUBJ0Iv0yi47jBn0jEm2
uBIrtjLwDsgiE7Yg/YoFlc6ikuQEAAwWvjhLijqlRgoZTMQw0Kog+KsYTXqunSVgbzbLASokNt8z
sD+A2z9AjNbLBOgzAwigYVBLwfJNk6pEB6HRR4Fv9E1/Hh849WyhbRMPuYiTVFv5OAvO6OFpWZL4
zmSBvcaaGApmmFXo2l1nQEcU88FgEATGHdoo8zVXQVVujoAVhBlnMpnWCRq+yQRNvf6hAh5FOAN7
3Ww7Cw80hOn0AajkdFmU+Qpf27l9AmUCY2GPYE9ckJaR7CB7nPgKyeeq9MI0RdvtsLNAPRRc/HT6
/uzL6SdxLC4blTZu67MrGPM0i4GtySIAU7WGbXQZtETFl6DuE+/BvBNTgD2j3iS+Mq5q4F1A/XNZ
02uYxsx7GZx+OHlzfjr5+dPpT5NPZ59PAUGwMzLYoymjeazBYVQRCAdw5VxF2r4GnR704M3JJ/sg
mCRq8u03wG7wZHgtK2DicggzHotwFd8pYNBwTE1HiGOnAVjwcDQSr8Xh06cvDwlasSk2AAzMrtMU
H060RZ8k2SIPR9T4V3bpj1lJaf/t8uibK3F8LMJf49s4DMCHapoyS/xI4vR5U0joWsGfYa5GQTCX
CxC9G4kCOnxKfvGIO8CSQMtc2+lf8yQz75kr3SFIfwypB+AwmczSWClsPJmEQATq0POBDhE71yh1
Q+hYbNyuI40KfkoJC5thlzH+04NiPKV+iAaj6HYxjUBcV7NYSW5F04d+kwnqrMlkqAcEYSaJAYeL
1VAoTBPUWWUCfi1xHuqwqcpT/InwUQuQAOLWCrUkLpLeOkW3cVpLNXQmBUQcDltkREWbKOJHcFGG
YImbpRuN2tQ0PAPNgHxpDlq0bFEOP3vg74C6Mps43Ojx3otphpj+mXcahAO4nCGqe6VaUFg7iovT
C/Hy+eE+ujOw55xb6njN0UInWS3twwWslpEHRph7GXlx6bJAPYtPj3bDXEV2ZbqssNBLXMpVfivn
gC0ysLPK4id6AztzmMcshlUEvU7+AKtQ4zfGuA/l2YO0oO8A1FsRFLP+Zun3OBggMwWKiDfWRGq9
62dTWJT5bYLOxnSjX4KtBGWJFtM4NoGzcB6ToUkEDQFecIaUWssQ1GFZs8NKeCNItBfzRrFGBO4c
NfUVfb3J8nU24Z3wMSrd4ciyLgqWZl5s0CzBnngPVgiQzGFj1xCNoYDLL1C29gF5mD5MFyhLewsA
BIZe0XbNgWW2ejRF3jXisAhj9EqQ8JYS/YVbMwRttQwxHEj0NrIPjJZASDA5q+CsatBMhrJmmsHA
Dkl8rjuPeAvqA2hRMQKzOdTQuJGh3+URKGdx7iolpx9a5C9fvjDbqCXFVxCxKU4aXYgFGcuo2IBh
TUAnGI+MozXEBmtwbgFMrTRriv1PIi/YG4P1vNCyDX4A7O6qqjg6OFiv15GOLuTl9YFaHPzxT99+
+6fnrBPnc+IfmI4jLTrUFh3QO/Roo++MBXptVq7Fj0nmcyPBGkryysgVRfy+r5N5Lo72R1Z/Ihc3
Zhr/Na4MKJCJGZSpDLQdNBg9UftPopdqIJ6QdbZthyP2S7RJtVbMt7rQo8rBEwC/ZZbXaKobTlDi
GVg32KHP5bS+Du3gno00P2CqKKdDywP7L64QA58zDF8ZUzxBLUFsgRbfIf1PzDYxeUdaQyB50UR1
ds+bfi1miDt/uLxbX9MRGjPDRCF3oET4TR4sgLZxV3Lwo11btHuOa2s+niEwlj4wzKsdyyEKDuGC
azF2pc7havR4QZrWrJpBwbiqERQ0OIlTprYGRzYyRJDo3ZjNPi+sbgF0akUOTXzArAK0cMfpWLs2
KzieEPLAsXhBTyS4yEedd895aes0pYBOi0c9qjBgb6HRTufAl0MDYCwG5c8Dbmm2KR9bi8Jr0AMs
5xgQMtiiw0z4xvUBB3uDHnbqWP1tvZnGfSBwkYYci3oQdEL5mEcoFUhTMfR7bmNxS9zuYDstDjGV
WSYSabVFuNrKo1eodhqmRZKh7nUWKZqlOXjFVisSIzXvfWeB9kH4uM+YaQnUZGjI4TQ6Jm/PE8BQ
t8Pw2XWNgQY3DoMYrRJF1g3JtIR/wK2g+AYFo4CWBM2CeaiU+RP7HWTOzld/2cIeltDIEG7TbW5I
x2JoOOb9nkAy6mgMSEEGJOwKI7mOrA5S4DBngTzhhtdyq3QTjEiBnDkWhNQM4E4vvQ0OPonwBIQk
FCHfVUoW4pkYwPK1RfVhuvt35VIThBg6DchV0NGLYzey4UQ1jltRDp+h/fgGnZUUOXDwFFweN9Dv
srlhWht0AWfdV9wWKdDIFIcZjFxUrwxh3GDyH46dFg2xzCCGobyBvCMdM9IosMutQcOCGzDemrfH
0o/diAX2HYa5OpSrO9j/hWWiZrkKKWbSjl24H80VXdpYbM+T6QD+eAswGF15kGSq4xcYZfknBgk9
6GEfdG+yGBaZx+U6yUJSYJp+x/7SdPCwpPSM3MEn2k4dwEQx4nnwvgQBoaPPAxAn1ASwK5eh0m5/
F+zOKQ4sXO4+8Nzmy6OXV13ijrdFeOynf6lO76oyVrhaKS8aCwWuVteAo9KFycXZRh9e6sNt3CaU
uYJdpPj46YtAQnBcdx1vHjf1huERm3vn5H0M6qDX7iVXa3bELoAIakVklIPw8Rz5cGQfO7kdE3sE
kEcxzI5FMZA0n/wzcHYtFIyxP99kGEdrqwz8wOtvv5n0REZdJL/9ZnDPKC1i9In9sOUJ2pE5qWDX
bEsZp+RqOH0oqJg1rGPbFCPW57T90zx21eNzarRs7Lu/BX4MFAypS/ARno8bsnWnih/fndoKT9up
HcA6u1Xz2aNFgL19Pv0VdshKB9Vu4ySlcwWY/P4+Klezued4Rb/28CDtVDAOCfr2X+ryOXBDyNGE
UXc62hk7MQHnnl2w+RSx6qKyp3MImiMwLy/APf7sQtUWzDDucz5eOOxRTd6M+5yJr1Gr+PldNJAF
5tFg0Ef2rez4/zHL5/+aST5wKubk+ne0ho8E9HvNhI0HQ9PGw4fVv+yu3TXAHmCetridO9zC7tB8
Vrkwzh2rJCWeou56KtaUrkCxVTwpAihz9vt64OAy6kPvt3VZ8tE1qcBClvt4HDsWmKllPL9eE7Mn
Dj7ICjGxzWYUq3byevI+NRLq6LOdSdjsG/rlbJmbmJXMbpMS+oLCHYY/fPzxNOw3IRjHhU4PtyIP
9xsQ7iOYNtTECR/Thyn0mC7/vFS1ty4+QU1GgIkIa7L12gc/EGziCP1rcE9EyDuw5WN23KHPlnJ2
M5GUOoBsil2doPhbfI2Y2IwCP/9LxQtKYoOZzNIaacWON2YfLupsRucjlQT/SqcKY+oQJQRw+G+R
xtdiSJ3nGHrS3EjRqdu41N5nUeaYnCrqZH5wncyF/K2OU9zWy8UCcMHDK/0q4uEpAiXecU4DJy0q
OavLpNoACWKV67M/Sn9wGk43PNGhhyQf8zABMSHiSHzCaeN7JtzckMsEB/wTD5wk7ruxg5OsENFz
eJ/lExx1Qjm+Y0aqey5Pj4P2CDkAGABQmP9gpCN3/htJr9wDRlpzl6ioJT1SupGGnJwxhDIcYaSD
f9NPnxFd3tqC5fV2LK93Y3ndxvK6F8trH8vr3Vi6IoELa4NWRhL6AlftY43efBs35sTDnMazJbfD
3E/M8QSIojAbbCNTnALtRbb4fI+AkNp2DpzpYZM/k3BSaZlzCFyDRO7HQyy9mTfJ605nysbRnXkq
xp3dlkPk9z2IIkoVm1J3lrd5XMWRJxfXaT4FsbXojhsAY9FOJ+JYaXY7mXJ0t2WpBhf/9fmHjx+w
OYIamPQG6oaLiIYFpzJ8GpfXqitNzeavAHakln4iDnXTAPceGFnjUfb4n3eU4YGMI9aUoZCLAjwA
yuqyzdzcpzBsPddJUvo5MzkfNh2LQVYNmkltIdLJxcW7k88nAwr5Df534AqMoa0vHS4+poVt0PXf
3OaW4tgHhFrHthrj587Jo3XDEffbWAO248O3Hhw+xGD3hgn8Wf5LKQVLAoSKdPD3MYR68B7oq7YJ
HfoYRuwk/7kna+ys2HeO7DkuiiP6fccO7QH8w07cY0yAANqFGpqdQbOZail9a153UNQB+kBf76u3
YO2tV3sn41PUTqLHAXQoa5ttd/+8cxo2ekpWb06/P/twfvbm4uTzD44LiK7cx08Hh+L0xy+C8kPQ
gLFPFGNqRIWZSGBY3EInMc/hvxojP/O64iAx9Hp3fq5PalZY6oK5z2hzInjOaUwWGgfNOAptH+r8
I8Qo1Rskp6aI0nWo5gj3SyuuZ1G5zo+mUqUpOqu13nrpWjFTU0bn2hFIHzR2ScEgOMUMXlEWe2V2
hSWfAOo6qx6ktI22iSEpBQU76QLO+Zc5XfECpdQZnjSdtaK/DF1cw6tIFWkCO7lXoZUl3Q3TYxrG
0Q/tATfj1acBne4wsm7Is96KBVqtVyHPTfcfNYz2Ww0YNgz2DuadSUoPoQxsTG4TITbik5xQ3sFX
u/R6DRQsGB70VbiIhukSmH0Mm2uxTGADATy5BOuL+wSA0FoJ/0DgyIkOyByzM8K3q/n+X0JNEL/1
L7/0NK/KdP9vooBdkOBUorCHmG7jd7DxiWQkTj++H4WMHKXmir/UWB4ADgkFQB1pp/wlPkGfDJVM
Fzq/xNcH+EL7CfS61b2URam797vGIUrAEzUkr+GJMvQLMd3Lwh7jVEYt0Fj5YDHDCkI3DcF89sSn
pUxTne9+9u78FHxHLMZACeJzt1MYjuMleISuk++4wrEFCg/Y4XWJbFyiC0tJFvPIa9YbtEaRo95e
XoZdJwoMd3t1osBlnCgX7SFOm2GZcoIIWRnWwiwrs3arDVLYbUMUR5lhlphclJTA6vME8DI9jXlL
BHslLPUwEXg+RU6yymQspskM9CioXFCoYxASJC7WMxLn5RnHwPNSmTIoeFhsyuR6WeHpBnSOqAQD
m/948uX87AOVJRy+bLzuHuYc005gzEkkx5giiNEO+OKm/SFXTSZ9PKtfIQzUPvCn/YqzU455gE4/
Dizin/YrrkM7dnaCPANQUHXRFg/cADjd+uSmkQXG1e6D8eOmADaY+WAoFollLzrRw51flxNty5Yp
obiPefmIA5xFYVPSdGc3Ja390XNcFHjONR/2N4K3fbJlPlPoetN5sy35zf10pBBLYgGjbmt/DJMd
1mmqp+Mw2zZuoW2ttrG/ZE6s1Gk3y1CUgYhDt/PIZbJ+JaybMwd6adQdYOI7ja6RxF5VPvglG2gP
w8PEEruzTzEdqYyFjABGMqSu/anBh0KLAAqEsn+HjuSOR08PvTk61uD+OWrdBbbxB1CEOheXajzy
EjgRvvzGjiO/IrRQjx6J0PFUMpnlNk8MP+slepUv/Dn2ygAFMVHsyji7lkOGNTYwn/nE3hKCJW3r
kfoyueozLOIMnNO7LRzelYv+gxODWosROu1u5KatjnzyYIPeUpCdBPPBl/EadH9RV0NeyS3n0L21
dNuh3g8Rsw+hqT59H4YYjvkt3LI+DeBeamhY6OH9tuUUltfGOLLWPraqmkL7QnuwsxK2ZpWiYxmn
ONH4otYLaAzucWPyB/apThSyv3vqxJyYkAXKg7sgvbkNdINWOGHA5UpcOZpQOnxTTaPfzeWtTMFo
gJEdYrXDr7baYRTZcEpvHthXY3exudj040ZvGsyOTDkGIkCFGL2Bnl0INTjgCv+idyJxdkPO8du/
no3F2w8/wb9v5EewoFjzOBZ/g9HF27yEbSUX7dJtCljAUfF+Ma8VFkYSNDqh4Isn0Fu78MiLpyG6
ssQvKbEKUmAybbni204ARZ4gFbI37oGpl4DfpqCr5YQaB7FvLQb6JdJge40L1oUc6JbRslqlaCac
4EiziJeD87O3px8+nUbVHTK2+Tlwgid+HhZORx8Nl3gMNhb2yazGJ1eOv/yDTIsed1nvNU29DO41
RQjbkcLuL/kmjdjuKeISAwai2MzzWYQtgdO5RK9ag/88craV99p3z7girOFIH541Tjw+BmqIX9r6
ZwANqY+eE/UkhOIp1orx42jQb4HHgiLa8OfpzXruBsR10Q9NsI1pM+uh392qwCXTWcOznER4Hdtl
MHWgaRKr1XTm1gd+zIS+CAWUGx1vyEVcp5WQGWylaG9PN1KAgndL+lhCmFXYilGdG0Vn0nW8UU7u
UazEAEcdUFE9nsNQoBC23j/GN2wGsNZQ1FwCDdAJUdo25U5XVc+WLMG8EyLq9eQbrJPspZvGoynM
g/LGeNb4rzBP9BYZo2tZ6fnzg+Ho8kWT4EDB6JlX0DsrwNi5bLIHGrN4+vTpQPzH/U4PoxKleX4D
3hjA7nVWzun1FoOtJ2dXq+vQmzcR8ONsKS/hwRUFze3zOqOI5I6utCDS/jUwQlyb0DKjad8yxxyr
K/l8mVvwOZU2GD9nCV13hBElicpW3xqF0SYjTcSSoBjCWM2SJOToBKzHJq+xFg+ji5pf5B1wfIJg
xvgWD8Z4h71Ex5LyZi33WHSOxYAADyiljEejYmaqRgM8JxcbjebkLEuqpozkuXtmqq8AqOwtRpqv
RLxGyTDzaBHDKev0WLVxrPOdLOptVPLZpRtnbM2SX9+HO7A2SFq+WBhM4aFZpFkuy5kxp7hiySyp
HDCmHcLhznR5E1mfKOhBaQDqnazC3Eq0ffsHuy4uph/p+HjfjKSzhip7IRbHhOKslVcYRc34FH2y
hLR8a76MYJQPFM3WnoA3lviDjqViDYF3b4dbzlhn+j4OTttoLukAOHQHlFWQlh09HeFcPGbhM9Nu
uUUDP7QzJ9xuk7Kq43Sir32YoJ82sefpGk9bBrezwNN6K+Db5+D47uuMfXAcTHIN0hMzbk1FxrFY
6MhE5FaW+UVYRY5e3iH7SuBTIGXmE1MPbWJHl5ZdbaGpTtV0VDyCemaKl7Y45KZqplNw4mI+pvQm
U+6wxXn2M0fp6grxWgxfjsVha+czKzZ4kxMg+2Qe+q4YdYOpOMEAM8f2vRji9bEYvhiLP+6AHm0Z
4OjQHaG9j21B2Ark5dWjyZgmUyJb2JfCfn9fncMImp5xHF21yd8l03dEpX9vUYkrBHWi8ot2onJr
7K371s7HRzJcgeJYJHK+/0QhCTXSjW7ezuCEHxbQ79kcLV073lTUUOHcFDYj60YPOhrRuM12EFOU
rtUX1++irmHDae8cMGkyrVRFe8scpjFq9FpEBQCTvqM0/IZ3u8B7TQrXP9t6xKqLACzYngiCrvTk
A7OmYSOo9zqCj9IA9zCKCPEwtVEUrmQ9QkRCugeHmOhZ6xDb4fjfnXm4xGDbUWgHy2+/2YWnK5i9
RR09C7q70sITWVte0Sy3+fQH5jxG6ev6VQLjQGlEB5xVc1UluZlHmL3Md9DkNot5hZdB0sk0msRU
um4Tb6X51i/0Yyh2QMlksBbgSdULPEi+pbstTxQlveEVNd8cvhibymAGpCfwMnr5TF8BSd3M5Qe+
jz3Wezd4qfsdRv/mAEsqv7d91dnN0LSOW3dB+YOFFD0bRRNLh8Yw3V8H0qxZLPDOxIaY7FvbC0De
g7czBT/HXH6ag8MGG9KoD11XYzTSu021bRHg+03GNsl5UNdGkSLSu4Rtm/LcpTgfLQq6V78FwRAC
cv4y5jfoCtbFkQ2xGZuCJ59DN5sTP9VNb90Z2xM0ttVNuGv63H/X3HWLwM7cJDN05u7Xl7o00H23
W9E+GnB4QxPiQSUSjcbvNyauHRjrHJr+CL3+IPndTjjTLWblPjAmYwfj/cSeGntj9lfxzP2OCWH7
fCGzW07c62y0pt2xGW2Of4inwMkv+NzeMEAZTXPNgbxfohv2JpwjO5HX12oS4+2OE9pkUz5XZ/dk
tm3v6XI+GauN2W3hpUUAwnCTzrx1k+uBMUBX8i3TnA7l3E4jaGhKGnaykFUyZ5Ogt3YALuKIKfU3
gXhOIx6kEgPdqi6LEnbDA30XMefp9KU2N0BNAG8VqxuDuukx1lfTkmKl5DBTgsxx2laSDxCBjXjH
NEwm9h3wyvPmmoVkbJlBZvVKlnHVXDHkZwQksOlqRqCic1xcJzzXSGWLS1zEEssbDlIYILPfn8HG
0ttU77hXYWS13cPZiXrokO9jrmxwjJHh4uTOXi/oXms1p6utXe/QNmu4zl6pBMtg7sojHaljZfxW
39/Fd8xyJB/9S4d/QN7dyks/C92qM/ZuLRrOM1chdC9swhsDyDj33cPY4YDujYutDbAd39cXllE6
HuaWxpaK2ifvVTjNaKMmgoQJo/dEkPyigEdGkDz4D4wg6VszwdBofLQe6C0TuCfUxOrBvYKyYQTo
MwEi4QF26wJDYyqHbtJ9kavkbmAvlGZd6VTyGfOAHNm9m4xA8FWTys1Q9q6C2xVB8qWLHn9//vHN
yTnRYnJx8vY/T76npCw8LmnZqgeH2LJ8n6m976V/u+E2nUjTN3iDbc8NsVzDpCF03ndyEHog9Ner
9S1oW5G5r7d16NT9dDsB4run3YK6TWX3Qu74ZbrGxE2faeVpB/opJ9WaX05mgnlkTupYHJqTOPO+
OTzRMtqJLW9bOCe9tatOtL+qbwHdEvce2SRrWgE8M0H+skcmpmLGBubZQWn/bz4oMxyrDc0NOiCF
M+nc5EiXODKoyv//iZSg7GLc27GjOLZ3c1M7Ph5S9tJ5PPudycgQxCv3G3Tn5wr7XKZbqBAErPD0
PYWMiNF/+kDVph88UeJynwqL91HZXNlfuGbauf1rgkkGlb3vS3GCEh+zQuNFnbqJA7ZPpwM5fXQa
lS+cShbQfAdA50Y8FbA3+kusEKcbEcLGUbtkmBxLdNSX9TnIo910sDe0ei72t5WdumWXQrzY3nDe
quzUPQ65h7qnh6pNcZ9jgTFLc1s9qXhNkPk4U9AFX57zgWfoetsPX28vXxzZwwXkd3ztKBLKJhs4
hv3Sycbceamk052YpRxTuh7u1ZyQsG5x5UBln2Db3qZTkrJl/2PyHBjSwHvfHzIzPbyr9wdtTC3r
HcGUxPCJGtG0nCIejbt9MupOt1FbXSBckPQAIB0VCLAQTEc3OgmiG87yHj7Xu8FpTdfxuidMoSMV
lCzmcwT3ML5fg1+7OxUSP6g7o2j6c4M2B+olB+Fm34FbjbxQyHaT0J56wwdbXACuye7v/+IB/btp
jLb74S6/2rZ62VsHyL4sZr5iZlCLROZxBEYG9OaQtDWWSxhBx2toGjq6DNXMDfkCHT/KpsXLtmmD
Qc7sRHsA1igE/wfVIOdx
""")

##file activate.sh
ACTIVATE_SH = convert("""
eJytVVFvokAQfudXTLEPtTlLeo9tvMSmJpq02hSvl7u2wRUG2QR2DSxSe7n/frOACEVNLlceRHa+
nfl25pvZDswCnoDPQ4QoTRQsENIEPci4CsBMZBq7CAsuLOYqvmYKTTj3YxnBgiXBudGBjUzBZUJI
BXEqgCvweIyuCjeG4eF2F5x14bcB9KQiQQWrjSddI1/oQIx6SYYeoFjzWIoIhYI1izlbhJjkKO7D
M/QEmKfO9O7WeRo/zr4P7pyHwWxkwitcgwpQ5Ej96OX+PmiFwLeVjFUOrNYKaq1Nud3nR2n8nI2m
k9H0friPTGVsUdptaxGrTEfpNVFEskxpXtUkkCkl1UNF9cgLBkx48J4EXyALuBtAwNYIjF5kcmUU
abMKmMq1ULoiRbgsDEkTSsKSGFCJ6Z8vY/2xYiSacmtyAfCDdCNTVZoVF8vSTQOoEwSnOrngBkws
MYGMBMg8/bMBLSYKS7pYEXP0PqT+ZmBT0Xuy+Pplj5yn4aM9nk72JD8/Wi+Gr98sD9eWSMOwkapD
BbUv91XSvmyVkICt2tmXR4tWmrcUCsjWOpw87YidEC8i0gdTSOFhouJUNxR+4NYBG0MftoCTD9F7
2rTtxG3oPwY1b2HncYwhrlmj6Wq924xtGDWqfdNxap+OYxplEurnMVo9RWks+rH8qKEtx7kZT5zJ
4H7oOFclrN6uFe+d+nW2aIUsSgs/42EIPuOhXq+jEo3S6tX6w2ilNkDnIpHCWdEQhFgwj9pkk7FN
l/y5eQvRSIQ5+TrL05lewxWpt/Lbhes5cJF3mLET1MGhcKCF+40tNWnUulxrpojwDo2sObdje3Bz
N3QeHqf3D7OjEXMVV8LN3ZlvuzoWHqiUcNKHtwNd0IbvPGKYYM31nPKCgkUILw3KL+Y8l7aO1ArS
Ad37nIU0fCj5NE5gQCuC5sOSu+UdI2NeXg/lFkQIlFpdWVaWZRfvqGiirC9o6liJ9FXGYrSY9mI1
D/Ncozgn13vJvsznr7DnkJWXsyMH7e42ljdJ+aqNDF1bFnKWFLdj31xtaJYK6EXFgqmV/ymD/ROG
+n8O9H8f5vsGOWXsL1+1k3g=
""")

##file activate.fish
ACTIVATE_FISH = convert("""
eJydVW2P2jgQ/s6vmAZQoVpA9/WkqqJaTou0u6x2uZVOVWWZZEKsS+yc7UDpr+84bziQbauLxEvs
eXnsZ56ZIWwTYSAWKUJWGAs7hMJgBEdhEwiMKnSIsBNywUMrDtziPBYmCeBDrFUG7v8HmCTW5n8u
Fu7NJJim81Bl08EQTqqAkEupLOhCgrAQCY2hTU+DQVxIiqgkRNiEBphFEKy+kd1BaFvwFOUBuIxA
oy20BKtAKp3xFMo0QNtCK5mhtMEA6BmSpUELKo38TThwLfguRVNaiRgs0llnEoIR29zfstf18/bv
5T17Wm7vAiiN3ONCzfbfwC3DtWXXDqHfAGX0q6z/bO82j3ebh1VwnbrduwTQbvwcRtesAfMGor/W
L3fs6Xnz8LRlm9fV8/P61sM0LDNwCZjl9gSpCokJRzpryGQ5t8kNGFUt51QjOZGu0Mj35FlYlXEr
yC09EVOp4lEXfF84Lz1qbhBsgl59vDedXI3rTV03xipduSgt9kLytI3XmBp3aV6MPoMQGNUU62T6
uQdeefTy1Hfj10zVHg2pq8fXDoHBiOv94csfXwN49xECqWREy7pwukKfvxdMY2j23vXDPuuxxeE+
JOdCOhxCE3N44B1ZeSLuZh8Mmkr2wEPAmPfKWHA2uxIRjEopdbQYjDz3BWOf14/scfmwoki1eQvX
ExBdF60Mqh+Y/QcX4uiH4Amwzx79KOVFtbL63sXJbtcvy8/3q5rupmO5CnE91wBviQAhjUUegYpL
vVEbpLt2/W+PklRgq5Ku6mp+rpMhhCo/lXthQTxJ2ysO4Ka0ad97S7VT/n6YXus6fzk3fLnBZW5C
KDC6gSO62QDqgFqLCCtPmjegjnLeAdArtSE8VYGbAJ/aLb+vnQutFhk768E9uRbSxhCMzdgEveYw
IZ5ZqFKl6+kz7UR4U+buqQZXu9SIujrAfD7f0FXpozB4Q0gwp31H9mVTZGGC4b871/wm7lvyDLu1
FUyvTj/yvD66k3UPTs08x1AQQaGziOl0S1qRkPG9COtBTSTWM9NzQ4R64B+Px/l3tDzCgxv5C6Ni
e+QaF9xFWrxx0V/G5uvYQOdiZzvYpQUVQSIsTr1TTghI33GnPbTA7/GCqcE3oE3GZurq4HeQXQD6
32XS1ITj/qLjN72ob0hc5C9bzw8MhfmL
""")

##file activate.csh
ACTIVATE_CSH = convert("""
eJx9VG1P2zAQ/u5fcYQKNgTNPtN1WxlIQ4KCUEGaxuQ6yYVYSuzKdhqVX7+zk3bpy5YPUXL3PPfc
ne98DLNCWshliVDV1kGCUFvMoJGugMjq2qQIiVSxSJ1cCofD1BYRnOVGV0CfZ0N2DD91DalQSjsw
tQLpIJMGU1euvPe7QeJlkKzgWixlhnAt4aoUVsLnLBiy5NtbJWQ5THX1ZciYKKWwkOFaE04dUm6D
r/zh7pq/3D7Nnid3/HEy+wFHY/gEJydg0aFaQrBFgz1c5DG1IhTs+UZgsBC2GMFBlaeH+8dZXwcW
VPvCjXdlAvCfQsE7al0+07XjZvrSCUevR5dnkVeKlFYZmUztG4BdzL2u9KyLVabTU0bdfg7a0hgs
cSmUg6UwUiQl2iHrcbcVGNvPCiLOe7+cRwG13z9qRGgx2z6DHjfm/Op2yqeT+xvOLzs0PTKHDz2V
tkckFHoQfQRXoGJAj9el0FyJCmEMhzgMS4sB7KPOE2ExoLcSieYwDvR+cP8cg11gKkVJc2wRcm1g
QhYFlXiTaTfO2ki0fQoiFM4tLuO4aZrhOzqR4dIPcWx17hphMBY+Srwh7RTyN83XOWkcSPh1Pg/k
TXX/jbJTbMtUmcxZ+/bbqOsy82suFQg/BhdSOTRhMNBHlUarCpU7JzBhmkKmRejKOQzayQe6MWoa
n1wqWmuh6LZAaHxcdeqIlVLhIBJdO9/kbl0It2oEXQj+eGjJOuvOIR/YGRqvFhttUB2XTvLXYN2H
37CBdbW2W7j2r2+VsCn0doVWcFG1/4y1VwBjfwAyoZhD
""")

##file activate.bat
ACTIVATE_BAT = convert("""
eJx9UdEKgjAUfW6wfxjiIH+hEDKUFHSKLCMI7kNOEkIf9P9pTJ3OLJ/03HPPPed4Es9XS9qqwqgT
PbGKKOdXL4aAFS7A4gvAwgijuiKlqOpGlATS2NeMLE+TjJM9RkQ+SmqAXLrBo1LLIeLdiWlD6jZt
r7VNubWkndkXaxg5GO3UaOOKS6drO3luDDiO5my3iA0YAKGzPRV1ack8cOdhysI0CYzIPzjSiH5X
0QcvC8Lfaj0emsVKYF2rhL5L3fCkVjV76kShi59NHwDniAHzkgDgqBcwOgTMx+gDQQqXCw==
""")

##file deactivate.bat
DEACTIVATE_BAT = convert("""
eJxzSE3OyFfIT0vj4ipOLVEI8wwKCXX0iXf1C7Pl4spMU0hJTcvMS01RiPf3cYmHyQYE+fsGhCho
cCkAAUibEkTEVhWLMlUlLk6QGixStlyaeCyJDPHw9/Pw93VFsQguim4ZXAJoIUw5DhX47XUM8UCx
EchHtwsohN1bILUgw61c/Vy4AJYPYm4=
""")

##file activate.ps1
ACTIVATE_PS = convert("""
eJylWdmS40Z2fVeE/oHT6rCloNUEAXDThB6wAyQAEjsB29GBjdgXYiWgmC/zgz/Jv+AEWNVd3S2N
xuOKYEUxM+/Jmzfvcm7W//zXf/+wUMOoXtyi1F9kbd0sHH/hFc2iLtrK9b3FrSqyxaVQwr8uhqJd
uHaeg9mqzRdR8/13Pyy8qPLdJh0+LMhi0QCoXxYfFh9WtttEnd34H8p6/f1300KauwrULws39e18
0ZaLNm9rgN/ZVf3h++/e124Vlc0vKsspHy+Yyi5+XbzPhijvCtduoiL/kA1ukWV27n0o7Sb8LIFj
CvWR5GQgUJdp1Pw8TS9+rPy6SDv/+e3d+0+4qw8f3v20+PliV37efEYBAB9FTKC+RHn/Cfxn3rdv
00Fube5O+iyCtHDs9BfPfz3q4sfFv9d91Ljhfy7ei0VO+nVTtdOkv/jpt0l2AX6iG1jXgKnnDuD4
ke2k/i8fzzz5UedkVcP4pwF+Wvz2FJl+3vt598urXf5Y6LNA5WcFOP7r0sW7b9a+W/xcu0Xpv5zk
Kfq3P9Dz9di/fCxS72MXVU1rpx9L4Bxl85Wmn5a+zP76Zuh3pL9ROWr87PN+//GHIl+oOtvn9XSU
qH+p0gQBFnx1uV+JLH5O5zv+PXW+WepXVVHZT0+oQezkIATcIm+ivPV/z5J/+cYj3ir4w0Lx09vC
e5n/y5/Y5LPPfdrqb88ga/PabxZRVfmp39l588m/6u+/e+OpP+dF7n1WZpJ9//Z4v372fDDz9eHB
7Juvs/BLMHzrxL9+9twXpJfhd1/DrpQ5Euu/vlss3wp9HXC/54C/Ld69m6zwdx3tC0d8daSv0V8B
n4b9YYF53sJelJV/ix6LZspw/sJtqyl5LJ5r/23htA1Imfm/gt9R7dqVB1LjhydAX4Gb+zksQF59
9+P7H//U+376afFuvh2/T6P85Xr/5c8C6OXyFY4BGuN+EE0+GeR201b+wkkLN5mmBY5TfMw8ngqL
CztXxCSXKMCYrRIElWkEJlEPYsSOeKBVZCAQTKBhApMwRFQzmCThE0YQu2CdEhgjbgmk9GluHpfR
/hhwJCZhGI5jt5FsAkOrObVyE6g2y1snyhMGFlDY1x+BoHpCMulTj5JYWNAYJmnKpvLxXgmQ8az1
4fUGxxcitMbbhDFcsiAItg04E+OSBIHTUYD1HI4FHH4kMREPknuYRMyhh3AARWMkfhCketqD1CWJ
mTCo/nhUScoQcInB1hpFhIKoIXLo5jLpwFCgsnLCx1QlEMlz/iFEGqzH3vWYcpRcThgWnEKm0QcS
rA8ek2a2IYYeowUanOZOlrbWSJUC4c7y2EMI3uJPMnMF/SSXdk6E495VLhzkWHps0rOhKwqk+xBI
DhJirhdUCTamMfXz2Hy303hM4DFJ8QL21BcPBULR+gcdYxoeiDqOFSqpi5B5PUISfGg46gFZBPo4
jdh8lueaWuVSMTURfbAUnLINr/QYuuYoMQV6l1aWxuZVTjlaLC14UzqZ+ziTGDzJzhiYoPLrt3uI
tXkVR47kAo09lo5BD76CH51cTt1snVpMOttLhY93yxChCQPI4OBecS7++h4p4Bdn4H97bJongtPk
s9gQnXku1vzsjjmX4/o4YUDkXkjHwDg5FXozU0fW4y5kyeYW0uJWlh536BKr0kMGjtzTkng6Ep62
uTWnQtiIqKnEsx7e1hLtzlXs7Upw9TwEnp0t9yzCGgUJIZConx9OHJArLkRYW0dW42G9OeR5Nzwk
yk1mX7du5RGHT7dka7N3AznmSif7y6tuKe2N1Al/1TUPRqH6E2GLVc27h9IptMLkCKQYRqPQJgzV
2m6WLsSipS3v3b1/WmXEYY1meLEVIU/arOGVkyie7ZsH05ZKpjFW4cpY0YkjySpSExNG2TS8nnJx
nrQmWh2WY3cP1eISP9wbaVK35ZXc60yC3VN/j9n7UFoK6zvjSTE2+Pvz6Mx322rnftfP8Y0XKIdv
Qd7AfK0nexBTMqRiErvCMa3Hegpfjdh58glW2oNMsKeAX8x6YJLZs9K8/ozjJkWL+JmECMvhQ54x
9rsTHwcoGrDi6Y4I+H7yY4/rJVPAbYymUH7C2D3uiUS3KQ1nrCAUkE1dJMneDQIJMQQx5SONxoEO
OEn1/Ig1eBBUeEDRuOT2WGGGE4bNypBLFh2PeIg3bEbg44PHiqNDbGIQm50LW6MJU62JHCGBrmc9
2F7WBJrrj1ssnTAK4sxwRgh5LLblhwNAclv3Gd+jC/etCfyfR8TMhcWQz8TBIbG8IIyAQ81w2n/C
mHWAwRzxd3WoBY7BZnsqGOWrOCKwGkMMNfO0Kci/joZgEocLjNnzgcmdehPHJY0FudXgsr+v44TB
I3jnMGnsK5veAhgi9iXGifkHMOC09Rh9cAw9sQ0asl6wKMk8mpzFYaaDSgG4F0wisQDDBRpjCINg
FIxhlhQ31xdSkkk6odXZFpTYOQpOOgw9ugM2cDQ+2MYa7JsEirGBrOuxsQy5nPMRdYjsTJ/j1iNw
FeSt1jY2+dd5yx1/pzZMOQXUIDcXeAzR7QlDRM8AMkUldXOmGmvYXPABjxqkYKO7VAY6JRU7kpXr
+Epu2BU3qFFXClFi27784LrDZsJwbNlDw0JzhZ6M0SMXE4iBHehCpHVkrQhpTFn2dsvsZYkiPEEB
GSEAwdiur9LS1U6P2U9JhGp4hnFpJo4FfkdJHcwV6Q5dV1Q9uNeeu7rV8PAjwdFg9RLtroifOr0k
uOiRTo/obNPhQIf42Fr4mtThWoSjitEdAmFW66UCe8WFjPk1YVNpL9srFbond7jrLg8tqAasIMpy
zkH0SY/6zVAwJrEc14zt14YRXdY+fcJ4qOd2XKB0/Kghw1ovd11t2o+zjt+txndo1ZDZ2T+uMVHT
VSXhedBAHoJIID9xm6wPQI3cXY+HR7vxtrJuCKh6kbXaW5KkVeJsdsjqsYsOwYSh0w5sMbu7LF8J
5T7U6LJdiTx+ca7RKlulGgS5Z1JSU2Llt32cHFipkaurtBrvNX5UtvNZjkufZ/r1/XyLl6yOpytL
Km8Fn+y4wkhlqZP5db0rooqy7xdL4wxzFVTX+6HaxuQJK5E5B1neSSovZ9ALB8091dDbbjVxhWNY
Ve5hn1VnI9OF0wpvaRm7SZuC1IRczwC7GnkhPt3muHV1YxUJfo+uh1sYnJy+vI0ZwuPV2uqWJYUH
bmBsi1zmFSxHrqwA+WIzLrHkwW4r+bad7xbOzJCnKIa3S3YvrzEBK1Dc0emzJW+SqysQfdEDorQG
9ZJlbQzEHQV8naPaF440YXzJk/7vHGK2xwuP+Gc5xITxyiP+WQ4x18oXHjFzCBy9kir1EFTAm0Zq
LYwS8MpiGhtfxiBRDXpxDWxk9g9Q2fzPPAhS6VFDAc/aiNGatUkPtZIStZFQ1qD0IlJa/5ZPAi5J
ySp1ETDomZMnvgiysZSBfMikrSDte/K5lqV6iwC5q7YN9I1dBZXUytDJNqU74MJsUyNNLAPopWK3
tzmLkCiDyl7WQnj9sm7Kd5kzgpoccdNeMw/6zPVB3pUwMgi4C7hj4AMFAf4G27oXH8NNT9zll/sK
S6wVlQwazjxWKWy20ZzXb9ne8ngGalPBWSUSj9xkc1drsXkZ8oOyvYT3e0rnYsGwx85xZB9wKeKg
cJKZnamYwiaMymZvzk6wtDUkxmdUg0mPad0YHtvzpjEfp2iMxvORhnx0kCVLf5Qa43WJsVoyfEyI
pzmf8ruM6xBr7dnBgzyxpqXuUPYaKahOaz1LrxNkS/Q3Ae5AC+xl6NbxAqXXlzghZBZHmOrM6Y6Y
ctAkltwlF7SKEsShjVh7QHuxMU0a08/eiu3x3M+07OijMcKFFltByXrpk8w+JNnZpnp3CfgjV1Ax
gUYCnWwYow42I5wHCcTzLXK0hMZN2DrPM/zCSqe9jRSlJnr70BPE4+zrwbk/xVIDHy2FAQyHoomT
Tt5jiM68nBQut35Y0qLclLiQrutxt/c0OlSqXAC8VrxW97lGoRWzhOnifE2zbF05W4xuyhg7JTUL
aqJ7SWDywhjlal0b+NLTpERBgnPW0+Nw99X2Ws72gOL27iER9jgzj7Uu09JaZ3n+hmCjjvZpjNst
vOWWTbuLrg+/1ltX8WpPauEDEvcunIgTxuMEHweWKCx2KQ9DU/UKdO/3za4Szm2iHYL+ss9AAttm
gZHq2pkUXFbV+FiJCKrpBms18zH75vax5jSo7FNunrVWY3Chvd8KKnHdaTt/6ealwaA1x17yTlft
8VBle3nAE+7R0MScC3MJofNCCkA9PGKBgGMYEwfB2QO5j8zUqa8F/EkWKCzGQJ5EZ05HTly1B01E
z813G5BY++RZ2sxbQS8ZveGPJNabp5kXAeoign6Tlt5+L8i5ZquY9+S+KEUHkmYMRFBxRrHnbl2X
rVemKnG+oB1yd9+zT+4c43jQ0wWmQRR6mTCkY1q3VG05Y120ZzKOMBe6Vy7I5Vz4ygPB3yY4G0FP
8RxiMx985YJPXsgRU58EuHj75gygTzejP+W/zKGe78UQN3yOJ1aMQV9hFH+GAfLRsza84WlPLAI/
9G/5JdcHftEfH+Y3/fHUG7/o8bv98dzzy3e8S+XCvgqB+VUf7sH0yDHpONdbRE8tAg9NWOzcTJ7q
TuAxe/AJ07c1Rs9okJvl1/0G60qvbdDzz5zO0FuPFQIHNp9y9Bd1CufYVx7dB26mAxwa8GMNrN/U
oGbNZ3EQ7inLzHy5tRg9AXJrN8cB59cCUBeCiVO7zKM0jU0MamhnRThkg/NMmBOGb6StNeD9tDfA
7czsAWopDdnGoXUHtA+s/k0vNPkBcxEI13jVd/axp85va3LpwGggXXWw12Gwr/JGAH0b8CPboiZd
QO1l0mk/UHukud4C+w5uRoNzpCmoW6GbgbMyaQNkga2pQINB18lOXOCJzSWPFOhZcwzdgrsQnne7
nvjBi+7cP2BbtBeDOW5uOLGf3z94FasKIguOqJl+8ss/6Kumns4cuWbqq5592TN/RNIbn5Qo6qbi
O4F0P9txxPAwagqPlftztO8cWBzdN/jz3b7GD6JHYP/Zp4ToAMaA74M+EGSft3hEGMuf8EwjnTk/
nz/P7SLipB/ogQ6xNX0fDqNncMCfHqGLCMM0ZzFa+6lPJYQ5p81vW4HkCvidYf6kb+P/oB965g8K
C6uR0rdjX1DNKc5pOSTquI8uQ6KXxYaKBn+30/09tK4kMpJPgUIQkbENEPbuezNPPje2Um83SgyX
GTCJb6MnGVIpgncdQg1qz2bvPfxYD9fewCXDomx9S+HQJuX6W3VAL+v5WZMudRQZk9ZdOk6GIUtC
PqEb/uwSIrtR7/edzqgEdtpEwq7p2J5OQV+RLrmtTvFwFpf03M/VrRyTZ73qVod7v7Jh2Dwe5J25
JqFOU2qEu1sP+CRotklediycKfLjeIZzjJQsvKmiGSNQhxuJpKa+hoWUizaE1PuIRGzJqropwgVB
oo1hr870MZLgnXF5ZIpr6mF0L8aSy2gVnTAuoB4WEd4d5NPVC9TMotYXERKlTcwQ2KiB/C48AEfH
Qbyq4CN8xTFnTvf/ebOc3isnjD95s0QF0nx9s+y+zMmz782xL0SgEmRpA3x1w1Ff9/74xcxKEPdS
IEFTz6GgU0+BK/UZ5Gwbl4gZwycxEw+Kqa5QmMkh4OzgzEVPnDAiAOGBFaBW4wkDmj1G4RyElKgj
NlLCq8zsp085MNh/+R4t1Q8yxoSv8PUpTt7izZwf2BTHZZ3pIZpUIpuLkL1nNL6sYcHqcKm237wp
T2+RCjgXweXd2Zp7ZM8W6dG5bZsqo0nrJBTx8EC0+CQQdzEGnabTnkzofu1pYkWl4E7XSniECdxy
vLYavPMcL9LW5SToJFNnos+uqweOHriUZ1ntIYZUonc7ltEQ6oTRtwOHNwez2sVREskHN+bqG3ua
eaEbJ8XpyO8CeD9QJc8nbLP2C2R3A437ISUNyt5Yd0TbDNcl11/DSsOzdbi/VhCC0KE6v1vqVNkq
45ZnG6fiV2NwzInxCNth3BwL0+8814jE6+1W1EeWtpWbSZJOJNYXmWRXa7vLnAljE692eHjZ4y5u
y1u63De0IzKca7As48Z3XshVF+3XiLNz0JIMh/JOpbiNLlMi672uO0wYzOCZjRxcxj3D+gVenGIE
MvFUGGXuRps2RzMcgWIRolHXpGUP6sMsQt1hspUBnVKUn/WQj2u6j3SXd9Xz0QtEzoM7qTu5y7gR
q9gNNsrlEMLdikBt9bFvBnfbUIh6voTw7eDsyTmPKUvF0bHqWLbHe3VRHyRZnNeSGKsB73q66Vsk
taxWYmwz1tYVFG/vOQhlM0gUkyvIab3nv2caJ1udU1F3pDMty7stubTE4OJqm0i0ECfrJIkLtraC
HwRWKzlqpfhEIqYH09eT9WrOhQyt8YEoyBlnXtAT37WHIQ03TIuEHbnRxZDdLun0iok9PUC79prU
m5beZzfQUelEXnhzb/pIROKx3F7qCttYIFGh5dXNzFzID7u8vKykA8Uejf7XXz//S4nKvW//ofS/
QastYw==
""")

##file distutils-init.py
DISTUTILS_INIT = convert("""
eJytV1uL4zYUfvevOE0ottuMW9q3gVDa3aUMXXbLMlDKMBiNrSTqOJKRlMxkf33PkXyRbGe7Dw2E
UXTu37lpxLFV2oIyifAncxmOL0xLIfcG+gv80x9VW6maw7o/CANSWWBwFtqeWMPlGY6qPjV8A0bB
C4eKSTgZ5LRgFeyErMEeOBhbN+Ipgeizhjtnhkn7DdyjuNLPoCS0l/ayQTG0djwZC08cLXozeMss
aG5EzQ0IScpnWtHSTXuxByV/QCmxE7y+eS0uxWeoheaVVfqSJHiU7Mhhi6gULbOHorshkrEnKxpT
0n3A8Y8SMpuwZx6aoix3ouFlmW8gHRSkeSJ2g7hU+kiHLDaQw3bmRDaTGfTnty7gPm0FHbIBg9U9
oh1kZzAFLaue2R6htPCtAda2nGlDSUJ4PZBgCJBGVcwKTAMz/vJiLD+Oin5Z5QlvDPdulC6EsiyE
NFzb7McNTKJzbJqzphx92VKRFY1idenzmq3K0emRcbWBD0ryqc4NZGmKOOOX9Pz5x+/l27tP797c
f/z0d+4NruGNai8uAM0bfsYaw8itFk8ny41jsfpyO+BWlpqfhcG4yxLdi/0tQqoT4a8Vby382mt8
p7XSo7aWGdPBc+b6utaBmCQ7rQKQoWtAuthQCiold2KfJIPTT8xwg9blPumc+YDZC/wYGdAyHpJk
vUbHbHWAp5No6pK/WhhLEWrFjUwtPEv1Agf8YmnsuXUQYkeZoHm8ogP16gt2uHoxcEMdf2C6pmbw
hUMsWGhanboh4IzzmsIpWs134jVPqD/c74bZHdY69UKKSn/+KfVhxLgUlToemayLMYQOqfEC61bh
cbhwaqoGUzIyZRFHPmau5juaWqwRn3mpWmoEA5nhzS5gog/5jbcFQqOZvmBasZtwYlG93k5GEiyw
buHhMWLjDarEGpMGB2LFs5nIJkhp/nUmZneFaRth++lieJtHepIvKgx6PJqIlD9X2j6pG1i9x3pZ
5bHuCPFiirGHeO7McvoXkz786GaKVzC9DSpnOxJdc4xm6NSVq7lNEnKdVlnpu9BNYoKX2Iq3wvgh
gGEUM66kK6j4NiyoneuPLSwaCWDxczgaolEWpiMyDVDb7dNuLAbriL8ig8mmeju31oNvQdpnvEPC
1vAXbWacGRVrGt/uXN/gU0CDDwgooKRrHfTBb1/s9lYZ8ZqOBU0yLvpuP6+K9hLFsvIjeNhBi0KL
MlOuWRn3FRwx5oHXjl0YImUx0+gLzjGchrgzca026ETmYJzPD+IpuKzNi8AFn048Thd63OdD86M6
84zE8yQm0VqXdbbgvub2pKVnS76icBGdeTHHXTKspUmr4NYo/furFLKiMdQzFjHJNcdAnMhltBJK
0/IKX3DVFqvPJ2dLE7bDBkH0l/PJ29074+F0CsGYOxsb7U3myTUncYfXqnLLfa6sJybX4g+hmcjO
kMRBfA1JellfRRKJcyRpxdS4rIl6FdmQCWjo/o9Qz7yKffoP4JHjOvABcRn4CZIT2RH4jnxmfpVG
qgLaAvQBNfuO6X0/Ux02nb4FKx3vgP+XnkX0QW9pLy/NsXgdN24dD3LxO2Nwil7Zlc1dqtP3d7/h
kzp1/+7hGBuY4pk0XD/0Ao/oTe/XGrfyM773aB7iUhgkpy+dwAMalxMP0DrBcsVw/6p25+/hobP9
GBknrWExDhLJ1bwt1NcCNblaFbMKCyvmX0PeRaQ=
""")

##file distutils.cfg
DISTUTILS_CFG = convert("""
eJxNj00KwkAMhfc9xYNuxe4Ft57AjYiUtDO1wXSmNJnK3N5pdSEEAu8nH6lxHVlRhtDHMPATA4uH
xJ4EFmGbvfJiicSHFRzUSISMY6hq3GLCRLnIvSTnEefN0FIjw5tF0Hkk9Q5dRunBsVoyFi24aaLg
9FDOlL0FPGluf4QjcInLlxd6f6rqkgPu/5nHLg0cXCscXoozRrP51DRT3j9QNl99AP53T2Q=
""")

##file activate_this.py
ACTIVATE_THIS = convert("""
eJyNU01v2zAMvetXEB4K21jmDOstQA4dMGCHbeihlyEIDMWmG62yJEiKE//7kXKdpN2KzYBt8euR
fKSyLPs8wiEo8wh4wqZTGou4V6Hm0wJa1cSiTkJdr8+GsoTRHuCotBayiWqQEYGtMCgfD1KjGYBe
5a3p0cRKiAe2NtLADikftnDco0ko/SFEVgEZ8aRC5GLux7i3BpSJ6J1H+i7A2CjiHq9z7JRZuuQq
siwTIvpxJYCeuWaBpwZdhB+yxy/eWz+ZvVSU8C4E9FFZkyxFsvCT/ZzL8gcz9aXVE14Yyp2M+2W0
y7n5mp0qN+avKXvbsyyzUqjeWR8hjGE+2iCE1W1tQ82hsCZN9UzlJr+/e/iab8WfqsmPI6pWeUPd
FrMsd4H/55poeO9n54COhUs+sZNEzNtg/wanpjpuqHJaxs76HtZryI/K3H7KJ/KDIhqcbJ7kI4ar
XL+sMgXnX0D+Te2Iy5xdP8yueSlQB/x/ED2BTAtyE3K4SYUN6AMNfbO63f4lBW3bUJPbTL+mjSxS
PyRfJkZRgj+VbFv+EzHFi5pKwUEepa4JslMnwkowSRCXI+m5XvEOvtuBrxHdhLalG0JofYBok6qj
YdN2dEngUlbC4PG60M1WEN0piu7Nq7on0mgyyUw3iV1etLo6r/81biWdQ9MWHFaePWZYaq+nmp+t
s3az+sj7eA0jfgPfeoN1
""")

MH_MAGIC = 0xfeedface
MH_CIGAM = 0xcefaedfe
MH_MAGIC_64 = 0xfeedfacf
MH_CIGAM_64 = 0xcffaedfe
FAT_MAGIC = 0xcafebabe
BIG_ENDIAN = '>'
LITTLE_ENDIAN = '<'
LC_LOAD_DYLIB = 0xc
maxint = majver == 3 and getattr(sys, 'maxsize') or getattr(sys, 'maxint')


class fileview(object):
    """
    A proxy for file-like objects that exposes a given view of a file.
    Modified from macholib.
    """

    def __init__(self, fileobj, start=0, size=maxint):
        if isinstance(fileobj, fileview):
            self._fileobj = fileobj._fileobj
        else:
            self._fileobj = fileobj
        self._start = start
        self._end = start + size
        self._pos = 0

    def __repr__(self):
        return '<fileview [%d, %d] %r>' % (
            self._start, self._end, self._fileobj)

    def tell(self):
        return self._pos

    def _checkwindow(self, seekto, op):
        if not (self._start <= seekto <= self._end):
            raise IOError("%s to offset %d is outside window [%d, %d]" % (
                op, seekto, self._start, self._end))

    def seek(self, offset, whence=0):
        seekto = offset
        if whence == os.SEEK_SET:
            seekto += self._start
        elif whence == os.SEEK_CUR:
            seekto += self._start + self._pos
        elif whence == os.SEEK_END:
            seekto += self._end
        else:
            raise IOError("Invalid whence argument to seek: %r" % (whence,))
        self._checkwindow(seekto, 'seek')
        self._fileobj.seek(seekto)
        self._pos = seekto - self._start

    def write(self, bytes):
        here = self._start + self._pos
        self._checkwindow(here, 'write')
        self._checkwindow(here + len(bytes), 'write')
        self._fileobj.seek(here, os.SEEK_SET)
        self._fileobj.write(bytes)
        self._pos += len(bytes)

    def read(self, size=maxint):
        assert size >= 0
        here = self._start + self._pos
        self._checkwindow(here, 'read')
        size = min(size, self._end - here)
        self._fileobj.seek(here, os.SEEK_SET)
        bytes = self._fileobj.read(size)
        self._pos += len(bytes)
        return bytes


def read_data(file, endian, num=1):
    """
    Read a given number of 32-bits unsigned integers from the given file
    with the given endianness.
    """
    res = struct.unpack(endian + 'L' * num, file.read(num * 4))
    if len(res) == 1:
        return res[0]
    return res


def mach_o_change(path, what, value):
    """
    Replace a given name (what) in any LC_LOAD_DYLIB command found in
    the given binary with a new name (value), provided it's shorter.
    """

    def do_macho(file, bits, endian):
        # Read Mach-O header (the magic number is assumed read by the caller)
        cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags = read_data(file, endian, 6)
        # 64-bits header has one more field.
        if bits == 64:
            read_data(file, endian)
        # The header is followed by ncmds commands
        for n in range(ncmds):
            where = file.tell()
            # Read command header
            cmd, cmdsize = read_data(file, endian, 2)
            if cmd == LC_LOAD_DYLIB:
                # The first data field in LC_LOAD_DYLIB commands is the
                # offset of the name, starting from the beginning of the
                # command.
                name_offset = read_data(file, endian)
                file.seek(where + name_offset, os.SEEK_SET)
                # Read the NUL terminated string
                load = file.read(cmdsize - name_offset).decode()
                load = load[:load.index('\0')]
                # If the string is what is being replaced, overwrite it.
                if load == what:
                    file.seek(where + name_offset, os.SEEK_SET)
                    file.write(value.encode() + '\0'.encode())
            # Seek to the next command
            file.seek(where + cmdsize, os.SEEK_SET)

    def do_file(file, offset=0, size=maxint):
        file = fileview(file, offset, size)
        # Read magic number
        magic = read_data(file, BIG_ENDIAN)
        if magic == FAT_MAGIC:
            # Fat binaries contain nfat_arch Mach-O binaries
            nfat_arch = read_data(file, BIG_ENDIAN)
            for n in range(nfat_arch):
                # Read arch header
                cputype, cpusubtype, offset, size, align = read_data(file, BIG_ENDIAN, 5)
                do_file(file, offset, size)
        elif magic == MH_MAGIC:
            do_macho(file, 32, BIG_ENDIAN)
        elif magic == MH_CIGAM:
            do_macho(file, 32, LITTLE_ENDIAN)
        elif magic == MH_MAGIC_64:
            do_macho(file, 64, BIG_ENDIAN)
        elif magic == MH_CIGAM_64:
            do_macho(file, 64, LITTLE_ENDIAN)

    assert(len(what) >= len(value))
    do_file(open(path, 'r+b'))


if __name__ == '__main__':
    main()

## TODO:
## Copy python.exe.manifest
## Monkeypatch distutils.sysconfig

########NEW FILE########
