__FILENAME__ = app
from flask import Flask, render_template, redirect
from flask_turbolinks import turbolinks


app = Flask(__name__)
app.secret_key = 'secret'

turbolinks(app)


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/page')
def page():
    return render_template('page.html')


@app.route('/redirect')
def in_redirect():
    return redirect('/page')


@app.route('/x-redirect')
def x_redirect():
    return redirect('http://lepture.com')


if __name__ == '__main__':
    app.debug = True
    app.run()

########NEW FILE########
__FILENAME__ = flask_turbolinks
# coding: utf-8
"""
    flask_turbolinks
    ~~~~~~~~~~~~~~~~

    Turbolinks implementation in Flask.

    :copyright: (c) 2013 by Hsiaoming Yang.
    :license: BSD, see LICENSE for more detail.
"""

try:
    from urlparse import urlparse
except ImportError:
    # python 3
    from urllib.parse import urlparse

__version__ = '0.2.0'
__author__ = 'Hsiaoming Yang <me@lepture.com>'

__all__ = ('turbolinks',)


def turbolinks(app):
    """Enable turbolinks.

    You don't need to do any configuration, wrap your app with turbolinks::

        app = Flask(__name__)
        app.secret_key = 'secret'
        turbolinks(app)

    And everything will be ready. Put turbolinks.js in the ``<head>`` of
    your html templates, it just works.
    """
    from flask import request, session

    app.wsgi_app = TurbolinksMiddleware(app.wsgi_app)

    @app.after_request
    def turbolinks_response(response):
        referrer = request.headers.get('X-XHR-Referer')
        if not referrer:
            # turbolinks not enabled
            return response

        method = request.cookies.get('request_method', None)
        if not method or method != request.method:
            response.set_cookie('request_method', request.method)

        if 'Location' in response.headers:
            # this is a redirect response
            loc = response.headers['Location']
            session['_turbolinks_redirect_to'] = loc

            # cross domain redirect
            if referrer and not same_origin(loc, referrer):
                response.status_code = 200
                response.data = (
                    '<body><script>location.href="%s"</script></body>'
                ) % loc
        else:
            if '_turbolinks_redirect_to' in session:
                loc = session.pop('_turbolinks_redirect_to')
                response.headers['X-XHR-Redirected-To'] = loc
        return response

    return app


class TurbolinksMiddleware(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        referrer = environ.get('HTTP_X_XHR_REFERER')
        if referrer:
            # overwrite referrer
            environ['HTTP_REFERER'] = referrer
        return self.app(environ, start_response)


def same_origin(current_uri, redirect_uri):
    parsed_uri = urlparse(current_uri)
    if not parsed_uri.scheme:
        return True
    parsed_redirect = urlparse(redirect_uri)

    if parsed_uri.scheme != parsed_redirect.scheme:
        return False

    if parsed_uri.hostname != parsed_redirect.hostname:
        return False

    if parsed_uri.port != parsed_redirect.port:
        return False
    return True

########NEW FILE########
__FILENAME__ = test_turbolinks
from flask import Flask, redirect, request
from flask_turbolinks import turbolinks


app = Flask(__name__)
app.secret_key = 'secret'

turbolinks(app)


@app.route('/')
def home():
    return request.referrer or ''


@app.route('/page')
def page():
    return 'page'


@app.route('/redirect')
def in_redirect():
    return redirect('/page')


@app.route('/x-redirect')
def x_redirect():
    return redirect('http://lepture.com')


def test_home():
    client = app.test_client()
    rv = client.get('/', headers={
        'X-XHR-Referer': '/page'
    })
    assert '/page' == rv.data.decode('utf-8')
    assert 'request_method=GET' in rv.headers['Set-Cookie']


def test_redirect():
    client = app.test_client()
    rv = client.get('/redirect', headers={
        'X-XHR-Referer': '/page'
    })
    assert 'X-XHR-Redirected-To' not in rv.headers


def test_cookie():
    client = app.test_client()
    rv = client.get('/', headers={
        'Cookie': 'request_method=GET'
    })
    assert 'Set-Cookie' not in rv.headers


def test_x_redirect():
    client = app.test_client()
    rv = client.get('/x-redirect')
    assert rv.status_code == 302

    rv = client.get('/x-redirect', headers={
        'X-XHR-Referer': '/page'
    })
    assert rv.status_code == 200
    assert b'script' in rv.data

    rv = client.get('/x-redirect', headers={
        'X-XHR-Referer': 'http://example.com/'
    })
    assert rv.status_code == 200
    assert b'script' in rv.data

    rv = client.get('/x-redirect', headers={
        'X-XHR-Referer': 'http://lepture.com:8000/'
    })
    assert rv.status_code == 200
    assert b'script' in rv.data

    rv = client.get('/x-redirect', headers={
        'X-XHR-Referer': 'http://lepture.com/life/'
    })
    assert rv.status_code == 302

########NEW FILE########
