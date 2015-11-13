__FILENAME__ = core
# -*- coding: utf-8 -*-

"""
httpbin.core
~~~~~~~~~~~~

This module provides the core HttpBin experience.
"""

import base64
import json
import os
import time
import uuid
import random
import base64

from flask import Flask, Response, request, render_template, redirect, jsonify, make_response
from werkzeug.datastructures import WWWAuthenticate
from werkzeug.http import http_date
from werkzeug.wrappers import BaseResponse
from six.moves import range as xrange

from . import filters
from .helpers import get_headers, status_code, get_dict, check_basic_auth, check_digest_auth, H, ROBOT_TXT, ANGRY_ASCII
from .utils import weighted_choice
from .structures import CaseInsensitiveDict

ENV_COOKIES = (
    '_gauges_unique',
    '_gauges_unique_year',
    '_gauges_unique_month',
    '_gauges_unique_day',
    '_gauges_unique_hour',
    '__utmz',
    '__utma',
    '__utmb'
)

# Prevent WSGI from correcting the casing of the Location header
BaseResponse.autocorrect_location_header = False

app = Flask(__name__)


# -----------
# Middlewares
# -----------
@app.after_request
def set_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')

    if request.method == 'OPTIONS':
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, PATCH, OPTIONS'
        response.headers['Access-Control-Max-Age'] = '3600'  # 1 hour cache
    return response


# ------
# Routes
# ------

@app.route('/')
def view_landing_page():
    """Generates Landing Page."""

    return render_template('index.html')


@app.route('/html')
def view_html_page():
    """Simple Html Page"""

    return render_template('moby.html')


@app.route('/robots.txt')
def view_robots_page():
    """Simple Html Page"""

    response = make_response()
    response.data = ROBOT_TXT
    response.content_type = "text/plain"
    return response


@app.route('/deny')
def view_deny_page():
    """Simple Html Page"""
    response = make_response()
    response.data = ANGRY_ASCII
    response.content_type = "text/plain"
    return response
    # return "YOU SHOULDN'T BE HERE"


@app.route('/ip')
def view_origin():
    """Returns Origin IP."""

    return jsonify(origin=request.headers.get('X-Forwarded-For', request.remote_addr))


@app.route('/headers')
def view_headers():
    """Returns HTTP HEADERS."""

    return jsonify(get_dict('headers'))


@app.route('/user-agent')
def view_user_agent():
    """Returns User-Agent."""

    headers = get_headers()

    return jsonify({'user-agent': headers['user-agent']})


@app.route('/get', methods=('GET',))
def view_get():
    """Returns GET Data."""

    return jsonify(get_dict('url', 'args', 'headers', 'origin'))


@app.route('/post', methods=('POST',))
def view_post():
    """Returns POST Data."""

    return jsonify(get_dict(
        'url', 'args', 'form', 'data', 'origin', 'headers', 'files', 'json'))


@app.route('/put', methods=('PUT',))
def view_put():
    """Returns PUT Data."""

    return jsonify(get_dict(
        'url', 'args', 'form', 'data', 'origin', 'headers', 'files', 'json'))


@app.route('/patch', methods=('PATCH',))
def view_patch():
    """Returns PATCH Data."""

    return jsonify(get_dict(
        'url', 'args', 'form', 'data', 'origin', 'headers', 'files', 'json'))


@app.route('/delete', methods=('DELETE',))
def view_delete():
    """Returns DETLETE Data."""

    return jsonify(get_dict('url', 'args', 'data', 'origin', 'headers', 'json'))


@app.route('/gzip')
@filters.gzip
def view_gzip_encoded_content():
    """Returns GZip-Encoded Data."""

    return jsonify(get_dict(
        'origin', 'headers', method=request.method, gzipped=True))


@app.route('/deflate')
@filters.deflate
def view_deflate_encoded_content():
    """Returns Deflate-Encoded Data."""

    return jsonify(get_dict(
        'origin', 'headers', method=request.method, deflated=True))


@app.route('/redirect/<int:n>')
def redirect_n_times(n):
    """301 Redirects n times."""

    assert n > 0

    if (n == 1):
        return redirect('/get')

    return redirect('/redirect/{0}'.format(n - 1))


@app.route('/redirect-to')
def redirect_to():
    """302 Redirects to the given URL."""

    args = CaseInsensitiveDict(request.args.items())

    # We need to build the response manually and convert to UTF-8 to prevent
    # werkzeug from "fixing" the URL. This endpoint should set the Location
    # header to the exact string supplied.
    response = app.make_response('')
    response.status_code = 302
    response.headers['Location'] = args['url'].encode('utf-8')

    return response


@app.route('/relative-redirect/<int:n>')
def relative_redirect_n_times(n):
    """301 Redirects n times."""

    assert n > 0

    response = app.make_response('')
    response.status_code = 302

    if (n == 1):
        response.headers['Location'] = '/get'
        return response

    response.headers['Location'] = '/relative-redirect/{0}'.format(n - 1)
    return response


@app.route('/stream/<int:n>')
def stream_n_messages(n):
    """Stream n JSON messages"""
    response = get_dict('url', 'args', 'headers', 'origin')
    n = min(n, 100)

    def generate_stream():
        for i in range(n):
            response['id'] = i
            yield json.dumps(response) + '\n'

    return Response(generate_stream(), headers={
        "Transfer-Encoding": "chunked",
        "Content-Type": "application/json",
        })


@app.route('/status/<codes>')
def view_status_code(codes):
    """Return status code or random status code if more than one are given"""

    if not ',' in codes:
        code = int(codes)
        return status_code(code)

    choices = []
    for choice in codes.split(','):
        if not ':' in choice:
            code = choice
            weight = 1
        else:
            code, weight = choice.split(':')

        choices.append((int(code), float(weight)))

    code = weighted_choice(choices)

    return status_code(code)


@app.route('/response-headers')
def response_headers():
    """Returns a set of response headers from the query string """
    headers = CaseInsensitiveDict(request.args.items())
    response = jsonify(headers.items())

    while True:
        content_len_shown = response.headers['Content-Length']
        response = jsonify(response.headers.items())
        for key, value in headers.items():
            response.headers[key] = value
        if response.headers['Content-Length'] == content_len_shown:
            break
    return response


@app.route('/cookies')
def view_cookies(hide_env=True):
    """Returns cookie data."""

    cookies = dict(request.cookies.items())

    if hide_env and ('show_env' not in request.args):
        for key in ENV_COOKIES:
            try:
                del cookies[key]
            except KeyError:
                pass

    return jsonify(cookies=cookies)


@app.route('/cookies/set/<name>/<value>')
def set_cookie(name, value):
    """Sets a cookie and redirects to cookie list."""

    r = app.make_response(redirect('/cookies'))
    r.set_cookie(key=name, value=value)

    return r


@app.route('/cookies/set')
def set_cookies():
    """Sets cookie(s) as provided by the query string and redirects to cookie list."""

    cookies = dict(request.args.items())
    r = app.make_response(redirect('/cookies'))
    for key, value in cookies.items():
        r.set_cookie(key=key, value=value)

    return r


@app.route('/cookies/delete')
def delete_cookies():
    """Deletes cookie(s) as provided by the query string and redirects to cookie list."""

    cookies = dict(request.args.items())
    r = app.make_response(redirect('/cookies'))
    for key, value in cookies.items():
        r.delete_cookie(key=key)

    return r


@app.route('/basic-auth/<user>/<passwd>')
def basic_auth(user='user', passwd='passwd'):
    """Prompts the user for authorization using HTTP Basic Auth."""

    if not check_basic_auth(user, passwd):
        return status_code(401)

    return jsonify(authenticated=True, user=user)


@app.route('/hidden-basic-auth/<user>/<passwd>')
def hidden_basic_auth(user='user', passwd='passwd'):
    """Prompts the user for authorization using HTTP Basic Auth."""

    if not check_basic_auth(user, passwd):
        return status_code(404)
    return jsonify(authenticated=True, user=user)


@app.route('/digest-auth/<qop>/<user>/<passwd>')
def digest_auth(qop=None, user='user', passwd='passwd'):
    """Prompts the user for authorization using HTTP Digest auth"""
    if qop not in ('auth', 'auth-int'):
        qop = None
    if not request.headers.get('Authorization'):
        response = app.make_response('')
        response.status_code = 401

        # RFC2616 Section4.2: HTTP headers are ASCII.  That means
        # request.remote_addr was originally ASCII, so I should be able to
        # encode it back to ascii.  Also, RFC2617 says about nonces: "The
        # contents of the nonce are implementation dependent"
        nonce = H(b''.join([
            getattr(request,'remote_addr',u'').encode('ascii'),
            b':',
            str(time.time()).encode('ascii'),
            b':',
            os.urandom(10)
        ]))
        opaque = H(os.urandom(10))

        auth = WWWAuthenticate("digest")
        auth.set_digest('me@kennethreitz.com', nonce, opaque=opaque,
                        qop=('auth', 'auth-int') if qop is None else (qop, ))
        response.headers['WWW-Authenticate'] = auth.to_header()
        response.headers['Set-Cookie'] = 'fake=fake_value'
        return response
    elif not (check_digest_auth(user, passwd) and
              request.headers.get('Cookie')):
        return status_code(401)
    return jsonify(authenticated=True, user=user)


@app.route('/delay/<int:delay>')
def delay_response(delay):
    """Returns a delayed response"""
    delay = min(delay, 10)

    time.sleep(delay)

    return jsonify(get_dict(
        'url', 'args', 'form', 'data', 'origin', 'headers', 'files'))

@app.route('/drip')
def drip():
    """Drips data over a duration after an optional initial delay."""
    args = CaseInsensitiveDict(request.args.items())
    duration = float(args.get('duration', 2))
    numbytes = int(args.get('numbytes', 10))
    pause = duration / numbytes

    delay = float(args.get('delay', 0))
    if delay > 0:
        time.sleep(delay)

    def generate_bytes():
        for i in xrange(numbytes):
            yield u"*".encode('utf-8')
            time.sleep(pause)

    return Response(generate_bytes(), headers={
        "Content-Type": "application/octet-stream",
        })

@app.route('/base64/<value>')
def decode_base64(value):
    """Decodes base64url-encoded string"""
    encoded = value.encode('utf-8') # base64 expects binary string as input
    return base64.urlsafe_b64decode(encoded).decode('utf-8')


@app.route('/cache', methods=('GET',))
def cache():
    """Returns a 304 if an If-Modified-Since header or If-None-Match is present. Returns the same as a GET otherwise."""
    is_conditional = request.headers.get('If-Modified-Since') or request.headers.get('If-None-Match')

    if is_conditional is None:
        response = view_get()
        response.headers['Last-Modified'] = http_date()
        response.headers['ETag'] = uuid.uuid4().hex
        return response
    else:
        return status_code(304)


@app.route('/cache/<int:value>')
def cache_control(value):
    """Sets a Cache-Control header."""
    response = view_get()
    response.headers['Cache-Control'] = 'public, max-age={0}'.format(value)
    return response


@app.route('/bytes/<int:n>')
def random_bytes(n):
    """Returns n random bytes generated with given seed."""
    n = min(n, 100 * 1024) # set 100KB limit

    params = CaseInsensitiveDict(request.args.items())
    if 'seed' in params:
        random.seed(int(params['seed']))

    response = make_response()
    response.data = bytes().join(chr(random.randint(0, 255)) for i in xrange(n))
    response.content_type = 'application/octet-stream'
    return response


@app.route('/stream-bytes/<int:n>')
def stream_random_bytes(n):
    """Streams n random bytes generated with given seed, at given chunk size per packet."""
    n = min(n, 100 * 1024) # set 100KB limit

    params = CaseInsensitiveDict(request.args.items())
    if 'seed' in params:
        random.seed(int(params['seed']))

    if 'chunk_size' in params:
        chunk_size = max(1, int(params['chunk_size']))
    else:
        chunk_size = 10 * 1024

    def generate_bytes():
        chunks = []

        for i in xrange(n):
            chunks.append(chr(random.randint(0, 255)))
            if len(chunks) == chunk_size:
                yield(bytes().join(chunks))
                chunks = []

        if chunks:
            yield(bytes().join(chunks))

    headers = {'Transfer-Encoding': 'chunked',
               'Content-Type': 'application/octet-stream'}

    return Response(generate_bytes(), headers=headers)


@app.route('/links/<int:n>/<int:offset>')
def link_page(n, offset):
    """Generate a page containing n links to other pages which do the same."""
    n = min(max(1, n), 200) # limit to between 1 and 200 links

    link = "<a href='/links/{0}/{1}'>{2}</a> "

    html = ['<html><head><title>Links</title></head><body>']
    for i in xrange(n):
        if i == offset:
            html.append("{0} ".format(i))
        else:
            html.append(link.format(n, i, i))
    html.append('</body></html>')

    return ''.join(html)


@app.route('/links/<int:n>')
def links(n):
    """Redirect to first links page."""
    return redirect("/links/{0}/0".format(n))


@app.route('/image')
def image():
    """Returns a simple image of the type suggest by the Accept header."""

    headers = get_headers()
    if headers['accept'].lower() == 'image/png' or headers['accept'].lower() == 'image/*':
        return Response(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACklEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=='), headers={'Content-Type': 'image/png'})
    elif headers['accept'].lower() == 'image/jpeg':
        return Response(base64.b64decode('/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDRENDg8QEBEQCgwSExIQEw8QEBD/yQALCAABAAEBAREA/8wABgAQEAX/2gAIAQEAAD8A0s8g/9k='), headers={'Content-Type': 'image/jpeg'})
    else:
        return status_code(404)


if __name__ == '__main__':
    app.run()

########NEW FILE########
__FILENAME__ = filters
# -*- coding: utf-8 -*-

"""
httpbin.filters
~~~~~~~~~~~~~~~

This module provides response filter decorators.
"""

import gzip as gzip2
import zlib

from six import BytesIO
from decimal import Decimal
from time import time as now

from decorator import decorator
from flask import Flask, Response


app = Flask(__name__)


@decorator
def x_runtime(f, *args, **kwargs):
    """X-Runtime Flask Response Decorator."""

    _t0 = now()
    r = f(*args, **kwargs)
    _t1 = now()
    r.headers['X-Runtime'] = '{0}s'.format(Decimal(str(_t1 - _t0)))

    return r


@decorator
def gzip(f, *args, **kwargs):
    """GZip Flask Response Decorator."""

    data = f(*args, **kwargs)

    if isinstance(data, Response):
        content = data.data
    else:
        content = data

    gzip_buffer = BytesIO()
    gzip_file = gzip2.GzipFile(
        mode='wb',
        compresslevel=4,
        fileobj=gzip_buffer
    )
    gzip_file.write(content)
    gzip_file.close()

    gzip_data = gzip_buffer.getvalue()

    if isinstance(data, Response):
        data.data = gzip_data
        data.headers['Content-Encoding'] = 'gzip'
        data.headers['Content-Length'] = str(len(data.data))

        return data

    return gzip_data


@decorator
def deflate(f, *args, **kwargs):
    """Deflate Flask Response Decorator."""

    data = f(*args, **kwargs)

    if isinstance(data, Response):
        content = data.data
    else:
        content = data

    deflater = zlib.compressobj()
    deflated_data = deflater.compress(content)
    deflated_data += deflater.flush()

    if isinstance(data, Response):
        data.data = deflated_data
        data.headers['Content-Encoding'] = 'deflate'
        data.headers['Content-Length'] = str(len(data.data))

        return data

    return deflated_data

########NEW FILE########
__FILENAME__ = helpers
# -*- coding: utf-8 -*-

"""
httpbin.helpers
~~~~~~~~~~~~~~~

This module provides helper functions for httpbin.
"""

import json
import base64
from hashlib import md5
from werkzeug.http import parse_authorization_header

from flask import request, make_response


from .structures import CaseInsensitiveDict


ASCII_ART = """
    -=[ teapot ]=-

       _...._
     .'  _ _ `.
    | ."` ^ `". _,
    \_;`"---"`|//
      |       ;/
      \_     _/
        `\"\"\"`
"""

REDIRECT_LOCATION = '/redirect/1'

ENV_HEADERS = (
    'X-Varnish',
    'X-Request-Start',
    'X-Heroku-Queue-Depth',
    'X-Real-Ip',
    'X-Forwarded-Proto',
    'X-Heroku-Queue-Wait-Time',
    'X-Forwarded-For',
    'X-Heroku-Dynos-In-Use',
    'X-Forwarded-For',
    'X-Forwarded-Protocol',
    'X-Forwarded-Port'
)

ROBOT_TXT = """User-agent: *
Disallow: /deny
"""

ANGRY_ASCII ="""
          .-''''''-.
        .' _      _ '.
       /   O      O   \\
      :                :
      |                |
      :       __       :
       \  .-"`  `"-.  /
        '.          .'
          '-......-'
      YOU SHOUDN'T BE HERE
"""


def json_safe(string, content_type='application/octet-stream'):
    """Returns JSON-safe version of `string`.

    If `string` is a Unicode string or a valid UTF-8, it is returned unmodified,
    as it can safely be encoded to JSON string.

    If `string` contains raw/binary data, it is Base64-encoded, formatted and
    returned according to "data" URL scheme (RFC2397). Since JSON is not
    suitable for binary data, some additional encoding was necessary; "data"
    URL scheme was chosen for its simplicity.
    """

    try:
        _encoded = json.dumps(string)
        return string
    except (ValueError, TypeError):
        return b''.join([
            b'data:', 
            content_type.encode('utf-8'),
            b';base64,',
            base64.b64encode(string)
        ]).decode('utf-8')


def get_files():
    """Returns files dict from request context."""

    files = dict()

    for k, v in request.files.items():
        val = json_safe(v.read(), request.files[k].content_type)
        if files.get(k):
            if not isinstance(files[k], list):
                files[k] = [files[k]]
            files[k].append(val)
        else:
            files[k] = val

    return files


def get_headers(hide_env=True):
    """Returns headers dict from request context."""

    headers = dict(request.headers.items())

    if hide_env and ('show_env' not in request.args):
        for key in ENV_HEADERS:
            try:
                del headers[key]
            except KeyError:
                pass

    return CaseInsensitiveDict(headers.items())


def semiflatten(multi):
    """Convert a MutiDict into a regular dict. If there are more than one value
    for a key, the result will have a list of values for the key. Otherwise it
    will have the plain value."""
    if multi:
        result = multi.to_dict(flat=False)
        for k, v in result.items():
            if len(v) == 1:
                result[k] = v[0]
        return result
    else:
        return multi


def get_dict(*keys, **extras):
    """Returns request dict of given keys."""

    _keys = ('url', 'args', 'form', 'data', 'origin', 'headers', 'files', 'json')

    assert all(map(_keys.__contains__, keys))

    data = request.data
    form = request.form
    form = semiflatten(request.form)

    try:
        _json = json.loads(data.decode('utf-8'))
    except (ValueError, TypeError):
        _json = None

    d = dict(
        url=request.url,
        args=semiflatten(request.args),
        form=form,
        data=json_safe(data),
        origin=request.headers.get('X-Forwarded-For', request.remote_addr),
        headers=get_headers(),
        files=get_files(),
        json=_json
    )

    out_d = dict()

    for key in keys:
        out_d[key] = d.get(key)

    out_d.update(extras)

    return out_d


def status_code(code):
    """Returns response object of given status code."""

    redirect = dict(headers=dict(location=REDIRECT_LOCATION))

    code_map = {
        301: redirect,
        302: redirect,
        303: redirect,
        304: dict(data=''),
        305: redirect,
        307: redirect,
        401: dict(headers={'WWW-Authenticate': 'Basic realm="Fake Realm"'}),
        402: dict(
            data='Fuck you, pay me!',
            headers={
                'x-more-info': 'http://vimeo.com/22053820'
            }
        ),
        407: dict(headers={'Proxy-Authenticate': 'Basic realm="Fake Realm"'}),
        418: dict(  # I'm a teapot!
            data=ASCII_ART,
            headers={
                'x-more-info': 'http://tools.ietf.org/html/rfc2324'
            }
        ),

    }

    r = make_response()
    r.status_code = code

    if code in code_map:

        m = code_map[code]

        if 'data' in m:
            r.data = m['data']
        if 'headers' in m:
            r.headers = m['headers']

    return r


def check_basic_auth(user, passwd):
    """Checks user authentication using HTTP Basic Auth."""

    auth = request.authorization
    return auth and auth.username == user and auth.password == passwd



# Digest auth helpers
# qop is a quality of protection

def H(data):
    return md5(data).hexdigest()


def HA1(realm, username, password):
    """Create HA1 hash by realm, username, password

    HA1 = md5(A1) = MD5(username:realm:password)
    """
    if not realm:
        realm = u''
    return H(b":".join([username.encode('utf-8'),
                           realm.encode('utf-8'),
                           password.encode('utf-8')]))


def HA2(credentails, request):
    """Create HA2 md5 hash

    If the qop directive's value is "auth" or is unspecified, then HA2:
        HA2 = md5(A2) = MD5(method:digestURI)
    If the qop directive's value is "auth-int" , then HA2 is
        HA2 = md5(A2) = MD5(method:digestURI:MD5(entityBody))
    """
    if credentails.get("qop") == "auth" or credentails.get('qop') is None:
        return H(b":".join([request['method'].encode('utf-8'), request['uri'].encode('utf-8')]))
    elif credentails.get("qop") == "auth-int":
        for k in 'method', 'uri', 'body':
            if k not in request:
                raise ValueError("%s required" % k)
        return H("%s:%s:%s" % (request['method'],
                               request['uri'],
                               H(request['body'])))
    raise ValueError


def response(credentails, password, request):
    """Compile digest auth response

    If the qop directive's value is "auth" or "auth-int" , then compute the response as follows:
       RESPONSE = MD5(HA1:nonce:nonceCount:clienNonce:qop:HA2)
    Else if the qop directive is unspecified, then compute the response as follows:
       RESPONSE = MD5(HA1:nonce:HA2)

    Arguments:
    - `credentails`: credentails dict
    - `password`: request user password
    - `request`: request dict
    """
    response = None
    HA1_value = HA1(
        credentails.get('realm'),
        credentails.get('username'),
        password
    )
    HA2_value = HA2(credentails, request)
    if credentails.get('qop') is None:
        response = H(b":".join([
            HA1_value.encode('utf-8'), 
            credentails.get('nonce').encode('utf-8'), 
            HA2_value.encode('utf-8')
        ]))
    elif credentails.get('qop') == 'auth' or credentails.get('qop') == 'auth-int':
        for k in 'nonce', 'nc', 'cnonce', 'qop':
            if k not in credentails:
                raise ValueError("%s required for response H" % k)
        response = H(b":".join([HA1_value.encode('utf-8'),
                               credentails.get('nonce').encode('utf-8'),
                               credentails.get('nc').encode('utf-8'),
                               credentails.get('cnonce').encode('utf-8'),
                               credentails.get('qop').encode('utf-8'),
                               HA2_value.encode('utf-8')]))
    else:
        raise ValueError("qop value are wrong")

    return response


def check_digest_auth(user, passwd):
    """Check user authentication using HTTP Digest auth"""

    if request.headers.get('Authorization'):
        credentails = parse_authorization_header(request.headers.get('Authorization'))
        if not credentails:
            return
        response_hash = response(credentails, passwd, dict(uri=request.path,
                                                           body=request.data,
                                                           method=request.method))
        if credentails['response'] == response_hash:
            return True
    return False

########NEW FILE########
__FILENAME__ = structures
# -*- coding: utf-8 -*-

"""
httpbin.structures
~~~~~~~~~~~~~~~~~~~

Data structures that power httpbin.
"""


class CaseInsensitiveDict(dict):
    """Case-insensitive Dictionary for headers.

    For example, ``headers['content-encoding']`` will return the
    value of a ``'Content-Encoding'`` response header.
    """

    def _lower_keys(self):
        return [str.lower(k) for k in  self.keys()]

    def __contains__(self, key):
        return key.lower() in self._lower_keys()

    def __getitem__(self, key):
        # We allow fall-through here, so values default to None
        if key in self:
            return list(self.items())[self._lower_keys().index(key.lower())][1]

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

"""
httpbin.utils
~~~~~~~~~~~~~~~

Utility functions.
"""

import random
import bisect


def weighted_choice(choices):
    """Returns a value from choices chosen by weighted random selection

    choices should be a list of (value, weight) tuples.

    eg. weighted_choice([('val1', 5), ('val2', 0.3), ('val3', 1)])

    """
    values, weights = zip(*choices)
    total = 0
    cum_weights = []
    for w in weights:
        total += w
        cum_weights.append(total)
    x = random.uniform(0, total)
    i = bisect.bisect(cum_weights, x)
    return values[i]

########NEW FILE########
__FILENAME__ = test_httpbin
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import base64
import unittest
from werkzeug.http import parse_dict_header
from hashlib import md5

import httpbin


def _string_to_base64(string):
    """Encodes string to utf-8 and then base64"""
    utf8_encoded = string.encode('utf-8')
    return base64.urlsafe_b64encode(utf8_encoded)


class HttpbinTestCase(unittest.TestCase):
    """Httpbin tests"""

    def setUp(self):
        httpbin.app.debug = True
        self.app = httpbin.app.test_client()

    def test_base64(self):
        greeting = u'Здравствуй, мир!'
        b64_encoded = _string_to_base64(greeting)
        response = self.app.get(b'/base64/' + b64_encoded)
        content = response.data.decode('utf-8')
        self.assertEqual(greeting, content)

    def test_post_binary(self):
        response = self.app.post('/post',
                                 data=b'\x01\x02\x03\x81\x82\x83',
                                 content_type='application/octet-stream')
        self.assertEqual(response.status_code, 200)

    def test_post_file_text(self):
        with open('httpbin/core.py') as f:
            response = self.app.post('/post', data={"file": f.read()})
        self.assertEqual(response.status_code, 200)

    def test_post_file_binary(self):
        with open('httpbin/core.pyc','rb') as f:
            response = self.app.post('/post', data={"file": f.read()})
        self.assertEqual(response.status_code, 200)

    def test_set_cors_headers_after_request(self):
        response = self.app.get('/get')
        self.assertEqual(response.headers.get('Access-Control-Allow-Origin'), '*')

    def test_set_cors_headers_after_request_with_request_origin(self):
        response = self.app.get('/get', headers={'Origin': 'origin'})
        self.assertEqual(response.headers.get('Access-Control-Allow-Origin'), 'origin')

    def test_set_cors_headers_with_options_verb(self):
        response = self.app.open('/get', method='OPTIONS')
        self.assertEqual(response.headers.get('Access-Control-Allow-Origin'), '*')
        self.assertEqual(response.headers.get('Access-Control-Allow-Credentials'), 'true')
        self.assertEqual(response.headers.get('Access-Control-Allow-Methods'), 'GET, POST, PUT, DELETE, PATCH, OPTIONS')
        self.assertEqual(response.headers.get('Access-Control-Max-Age'), '3600')
        self.assertNotIn('Access-Control-Allow-Headers', response.headers)  # FIXME should we add any extra headers?

    def test_user_agent(self):
        response = self.app.get('/user-agent', headers={'User-Agent':'test'})
        self.assertIn('test', response.data.decode('utf-8'))
        self.assertEqual(response.status_code, 200)

    def test_gzip(self):
        response = self.app.get('/gzip')
        self.assertEqual(response.status_code, 200)

    def test_digest_auth(self):
        # make first request
        unauthorized_response = self.app.get(
            '/digest-auth/auth/user/passwd',
            environ_base = {
                'REMOTE_ADDR':'127.0.0.1', # digest auth uses the remote addr to build the nonce
        })
        # make sure it returns a 401
        self.assertEqual(unauthorized_response.status_code, 401)
        header = unauthorized_response.headers.get('WWW-Authenticate')
        auth_type, auth_info = header.split(None, 1)

        # Begin crappy digest-auth implementation
        d = parse_dict_header(auth_info)
        a1 = b'user:' + d['realm'].encode('utf-8') + b':passwd'
        ha1 = md5(a1).hexdigest().encode('utf-8')
        a2 = b'GET:/digest-auth/auth/user/passwd'
        ha2 = md5(a2).hexdigest().encode('utf-8')
        a3 = ha1 + b':' + d['nonce'].encode('utf-8') + b':' + ha2
        auth_response = md5(a3).hexdigest()
        auth_header = 'Digest username="user",realm="' + \
            d['realm'] + \
            '",nonce="' + \
            d['nonce'] + \
            '",uri="/digest-auth/auth/user/passwd",response="' + \
            auth_response + \
            '",opaque="' + \
            d['opaque'] + '"'

        # make second request
        authorized_response = self.app.get(
            '/digest-auth/auth/user/passwd',
            environ_base = {
                'REMOTE_ADDR':'127.0.0.1', # httpbin's digest auth implementation uses the remote addr to build the nonce
            },
            headers =  {
                'Authorization': auth_header,
            }
        )

        # done!
        self.assertEqual(authorized_response.status_code, 200)

    def test_drip(self):
        response = self.app.get('/drip?numbytes=400&duration=2&delay=1')
        self.assertEqual(len(response.get_data()), 400)
        self.assertEqual(response.status_code, 200)



if __name__ == '__main__':
    unittest.main()

########NEW FILE########
