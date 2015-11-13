__FILENAME__ = moves_cli
"""\
This implements a command line interpreter (CLI) for the moves API.

OAuth data is kept in a JSON file, for easy portability between different
programming languages.

Currently, the initialization of OAuth requires the user to copy a URL
into a web browser, then copy the URL of the resulting page back to this
script.
"""

copyright = """
Copyright (c) 2013 Sam Denton <samwyse@gmail.com>
All Rights Reserved.

Licensed under the Academic Free License (AFL 3.0)
http://opensource.org/licenses/afl-3.0
"""

from cmd import Cmd as _Cmd
from pprint import pprint as _pprint
import json as _json

try:
    from moves import MovesClient
except ImportError:
    import sys
    from os.path import join, normpath
    # Try looking in the parent of this script's directory.
    sys.path.insert(0, normpath(join(sys.path[0], '..')))
    from moves import MovesClient
    

def _parse_line(f):
    import itertools
    from functools import wraps
    def partition(pred, iterable,
                  filter=itertools.ifilter,
                  filterfalse=itertools.ifilterfalse,
                  tee=itertools.tee):
        'Use a predicate to partition entries into false entries and true entries'
        t1, t2 = tee(iterable)
        return filterfalse(pred, t1), filter(pred, t2)

    @wraps(f)
    def wrapper(self, line):
        args, kwds = partition(
            lambda s: '=' in s,
            line.split())
        kwds = dict(item.split('=') for item in kwds)
        return f(self, *args, **kwds)
    return wrapper

class MovesCmd(_Cmd):

    cache_file = 'moves_cli.json'

    def default(self, line):
        '''Echos the arguments and exits the interpreter.'''
        print `argv`

    def do_quit(self, line):
        '''Exits the interpreter.'''
        return True

    def do_copyright(self, line):
        '''Displays copyright and licensing information.'''
        print copyright

    def do_client_id(self, line):
        '''Displays or sets the value.'''
        if line:
            self.mc.client_id = line
        elif self.mc.client_id:
            print 'client_id =', self.mc.client_id
        else:
            print 'The client id is not set.'

    def do_client_secret(self, line):
        '''Displays or sets the value.'''
        if line:
            self.mc.client_secret = line
        elif self.mc.client_secret:
            print 'client_secret =', self.mc.client_secret
        else:
            print 'The client secret is not set.'

    def do_access_token(self, line):
        '''Displays or sets the value.'''
        from urlparse import urlparse, parse_qs
        mc = self.mc
        if line:
            parts = urlparse(line)
            code = parse_qs(parts.query)['code'][0]
            mc.access_token = mc.get_oauth_token(code)
            mc.access_token = line
        elif mc.access_token:
            print 'access_token =', mc.access_token
        else:
            print 'The access token is not set.'
            print 'Enter the URL below in a web browser and follow the instructions.'
            print ' ', mc.build_oauth_url()
            print 'Once the web browser redirects, copy the complete URL and'
            print 'use it to re-run this command.'

    def do_load(self, filename):
        '''Loads the API state from a JSON file.'''
        if not filename:
            filename = self.cache_file
        with open(filename, 'rb') as fp:
            self.mc.__dict__.update(_json.load(fp))

    def do_save(self, filename):
        '''Saves the API state into a JSON file.'''
        if not filename:
            filename = self.cache_file
        with open(filename, 'wb') as fp:
            _json.dump(self.mc.__dict__, fp)

    @_parse_line
    def do_get(self, *path, **params):
        '''Issues an HTTP GET request
Syntax:
\tget path... [key=value]...
'''
        _pprint(self.mc.get('/'.join(path), **params))

    @_parse_line
    def do_post(self, *path, **params):
        '''Issues an HTTP POST request
Syntax:
\tpost path... [key=value]...
'''
        _pprint(self.mc.post('/'.join(path), **params))

    def do_tokeninfo(self, line):
        '''Displays information about the access token.'''
        _pprint(self.mc.tokeninfo())

    def do_examples(self, line):
        '''Displays example commands.'''
        print '''\
These are some commands to try.
 get user profile
 get user summary daily pastDays=7
 get user activities daily pastDays=5
 get user places daily pastDays=3
 get user storyline daily pastDays=2
'''

    def onecmd(self, line):
        try:
            return _Cmd.onecmd(self, line)
        except Exception as error:
            print "%s: %s" % (type(error).__name__, error)

    def preloop(self):
        self.mc = MovesClient()

def main(argv):
    MovesCmd().cmdloop()

if __name__ == '__main__':
    import sys
    main(sys.argv)
    

########NEW FILE########
__FILENAME__ = oauth-update
from flask import Flask, url_for, request, session, redirect
from moves import MovesClient
from datetime import datetime, timedelta
import _keys

app = Flask(__name__)

Moves = MovesClient(_keys.client_id, _keys.client_secret)

@app.route("/")
def index():
    if 'token' not in session:
        oauth_return_url = url_for('oauth_return', _external=True)
        auth_url = Moves.build_oauth_url(oauth_return_url)
        return 'Authorize this application: <a href="%s">%s</a>' % \
            (auth_url, auth_url)
    return redirect(url_for('show_info'))


@app.route("/oauth_return")
def oauth_return():
    error = request.values.get('error', None)
    if error is not None:
        return error
    oauth_return_url = url_for('oauth_return', _external=True)
    code = request.args.get("code")
    token = Moves.get_oauth_token(code, redirect_uri=oauth_return_url)
    session['token'] = token
    return redirect(url_for('show_info'))


@app.route('/logout')
def logout():
    if 'token' in session:
        del(session['token'])
    return redirect(url_for('index'))


@app.route("/info")
def show_info():
    profile = Moves.user_profile(access_token=session['token'])
    response = 'User ID: %s<br />First day using Moves: %s' % \
        (profile['userId'], profile['profile']['firstDate'])
    return response + "<br /><a href=\"%s\">Info for today</a>" % url_for('today') + \
        "<br /><a href=\"%s\">Logout</a>" % url_for('logout')


@app.route("/today")
def today():
    today = datetime.now().strftime('%Y%m%d')
    info = Moves.user_summary_daily(today, access_token=session['token'])
    res = ''
    for activity in info[0]['summary']:
        if activity['activity'] == 'wlk':
            res += 'Walking: %d steps<br />' % activity['steps']
        elif activity['activity'] == 'run':
            res += 'Running: %d steps<br />' % activity['steps']
        elif activity['activity'] == 'cyc':
            res += 'Cycling: %dm' % activity['distance']
    return res


@app.route("/expanded-summary")
def expanded_summary():
    today = datetime.now().strftime('%Y%m%d')
    info = Moves.user_summary_daily(today, access_token=session['token'])
    res = ''
    for activity in info[0]['summary']:
        res = activities_block(activity, res)
        if activity['activity'] == 'wlk':
            res += 'Walking: %d steps<br />' % activity['steps']
            res += 'Walking: %d calories<br />' % activity['calories']
            res += 'Walking: %d distance<br />' % activity['distance']
            res += 'Walking: %d duration<br /><br />' % activity['duration']
        elif activity['activity'] == 'run':
            res += 'Running: %d steps<br />' % activity['steps']
            res += 'Running: %d calories<br />' % activity['calories']
            res += 'Running: %d distance<br />' % activity['distance']
            res += 'Running: %d duration<br /><br />' % activity['duration']
        elif activity['activity'] == 'cyc':
            res += 'Cycling: %dm<br />' % activity['distance']
            res += 'Cycling: %d calories<br />' % activity['calories']
            res += 'Cycling: %d distance<br />' % activity['distance']
            res += 'Cycling: %d duration<br />' % activity['duration']
    return res


@app.route("/activities")
def activities():
    today = datetime.now().strftime('%Y%m%d')
    info = Moves.user_activities_daily(today, access_token=session['token'])
    res = ''
    for segment in info[0]['segments']:
        if segment['type'] == 'move':
            res += 'Move<br />'
            res = segment_start_end(segment, res)
            for activity in segment['activities']:
                res += 'Activity %s<br />' % activity['activity']
                res = activity_start_end(activity, res)
                res += 'Duration: %d<br />' % activity['duration']
                res += 'Distance: %dm<br />' % activity['distance']
            res += '<br />'
        elif segment['type'] == 'place':
            res += 'Place<br />'
            res = segment_start_end(segment, res)
            for activity in segment['activities']:
                res += 'Activity %s<br />' % activity['activity']
                res = activity_start_end(activity, res)
                res += 'Duration: %d<br />' % activity['duration']
                res += 'Distance: %dm<br />' % activity['distance']
            res += '<br />'
    return res


@app.route("/places")
def places():
    today = datetime.now().strftime('%Y%m%d')
    info = Moves.user_places_daily(today, access_token=session['token'])
    res = ''
    for segment in info[0]['segments']:
        res = place(segment, res)
    return res


@app.route("/storyline")
def storyline():
    today = datetime.now().strftime('%Y%m%d')
    info = Moves.user_storyline_daily(today, trackPoints={'true'}, access_token=session['token'])
    res = ''
    for segment in info[0]['segments']:
        if segment['type'] == 'place':
            res = place(segment, res)
        elif segment['type'] == 'move':
            res = move(segment, res)
        res += '<hr>'
    return res


def segment_start_end(segment, res):
    res += 'Start Time: %s<br />' % segment['startTime']
    res += 'End Time: %s<br />' % segment['endTime']
    return res


def activity_start_end(activity, res):
    res += 'Start Time: %s<br />' % activity['startTime']
    res += 'End Time: %s<br />' % activity['endTime']
    return res


def place_block(segment, res):
    res += 'ID: %d<br />' % segment['place']['id']
    res += 'Name: %s<br />' % segment['place']['name']
    res += 'Type: %s<br />' % segment['place']['type']
    if segment['place']['type'] == 'foursquare':
        res += 'Foursquare ID: %s<br />' % segment['place']['foursquareId']
    res += 'Location<br />'
    res += 'Latitude: %f<br />' % segment['place']['location']['lat']
    res += 'Longitude: %f<br />' % segment['place']['location']['lon']
    return res


def trackPoint(track_point, res):
    res += 'Latitude: %f<br />' % track_point['lat']
    res += 'Longitude: %f<br />' % track_point['lon']
    res += 'Time: %s<br />' % track_point['time']
    return res


def activities_block(activity, res):
    res += 'Activity: %s<br />' % activity['activity']
    res = activity_start_end(activity, res)
    res += 'Duration: %d<br />' % activity['duration']
    res += 'Distance: %dm<br />' % activity['distance']
    if activity['activity'] == 'wlk' or activity['activity'] == 'run':
        res += 'Steps: %d<br />' % activity['steps']
    if activity['activity'] != 'trp':
        res += 'Calories: %d<br />' % activity['calories']
    if 'trackPoints' in activity:
        for track_point in activity['trackPoints']:
            res = trackPoint(track_point, res)
    return res


def place(segment, res):
    res += 'Place<br />'
    res = segment_start_end(segment, res)
    res = place_block(segment, res)
    if 'activities' in segment:
        for activity in segment['activities']:
            res = activities_block(activity, res)
    res += '<br />'
    return res


def move(segment, res):
    res += 'Move<br />'
    res = segment_start_end(segment, res)
    for activity in segment['activities']:
        res = activities_block(activity, res)
    res += '<br />'
    return res

app.secret_key = _keys.secret_key

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)

########NEW FILE########
__FILENAME__ = oauth
from flask import Flask, url_for, request, session, redirect
from moves import MovesClient
from datetime import datetime, timedelta
import _keys

app = Flask(__name__)

Moves = MovesClient(_keys.client_id, _keys.client_secret)


@app.route("/")
def index():
    if 'token' not in session:
        oauth_return_url = url_for('oauth_return', _external=True)
        auth_url = Moves.build_oauth_url(oauth_return_url)
        return 'Authorize this application: <a href="%s">%s</a>' % \
            (auth_url, auth_url)
    return redirect(url_for('show_info'))


@app.route("/oauth_return")
def oauth_return():
    error = request.values.get('error', None)
    if error is not None:
        return error
    oauth_return_url = url_for('oauth_return', _external=True)
    code = request.args.get("code")
    token = Moves.get_oauth_token(code, redirect_uri=oauth_return_url)
    session['token'] = token
    return redirect(url_for('show_info'))


@app.route('/logout')
def logout():
    if 'token' in session:
        del(session['token'])
    return redirect(url_for('index'))


@app.route("/info")
def show_info():
    profile = Moves.user_profile(access_token=session['token'])
    response = 'User ID: %s<br />First day using Moves: %s' % \
        (profile['userId'], profile['profile']['firstDate'])
    return response + "<br /><a href=\"%s\">Info for today</a>" % url_for('today') + \
        "<br /><a href=\"%s\">Logout</a>" % url_for('logout')


@app.route("/today")
def today():
    today = datetime.now().strftime('%Y%m%d')
    info = Moves.user_summary_daily(today, access_token=session['token'])
    res = ''
    for activity in info[0]['summary']:
        if activity['activity'] == 'wlk':
            res += 'Walking: %d steps<br />' % activity['steps']
        elif activity['activity'] == 'run':
            res += 'Running: %d steps<br />' % activity['steps']
        elif activity['activity'] == 'cyc':
            res += 'Cycling: %dm' % activity['distance']
    return res

app.secret_key = _keys.secret_key

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)

########NEW FILE########
__FILENAME__ = _moves
import json
import urllib
import requests
import types


class MovesAPIError(Exception):
    """Raised if the Moves API returns an error."""
    pass

class MovesAPINotModifed(Exception):
    """Raised if the document requested is unmodified. Need the use of etag header"""
    pass

class MovesClient(object):
    """OAuth client for the Moves API"""
    api_url = "https://api.moves-app.com/api/1.1"
    app_auth_url = "moves://app/authorize"
    web_auth_uri = "https://api.moves-app.com/oauth/v1/authorize"
    token_url = "https://api.moves-app.com/oauth/v1/access_token"
    tokeninfo_url = "https://api.moves-app.com/oauth/v1/tokeninfo"
    
    
    
    def __init__(self, client_id=None, client_secret=None,
                 access_token=None, use_app=False):

        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.auth_url = self.app_auth_url if use_app else self.web_auth_uri
        self.use_app = use_app
        self._last_headers = None

    def parse_response(self, response):
        """Parse JSON API responses."""

        return json.loads(response.text)

    def build_oauth_url(self, redirect_uri=None, scope="activity location"):
        params = {
            'client_id': self.client_id,
            'scope': scope
        }

        if not self.use_app:
            params['response_type'] = 'code'

        if redirect_uri:
            params['redirect_uri'] = redirect_uri

        # Moves hates +s for spaces, so use %20 instead.
        encoded = urllib.urlencode(params).replace('+', '%20')
        return "%s?%s" % (self.auth_url, encoded)

    def get_oauth_token(self, code, **kwargs):

        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': kwargs.get('grant_type', 'authorization_code')
        }

        if 'redirect_uri' in kwargs:
            params['redirect_uri'] = kwargs['redirect_uri']
        response = requests.post(self.token_url, params=params)
        response = json.loads(response.content)
        try:
            return response['access_token']
        except:
            error = "<%(error)s>: %(error_description)s" % response
            raise MovesAPIError(error)

    def tokeninfo(self):
        
        params = {
            'access_token': self.access_token
        }

        response = requests.get(self.tokeninfo_url, params=params)
        response = json.loads(response.content)
        try:
            return response
        except:
            error = "<%(error)s>: %(error_description)s" % response
            raise MovesAPIError(error)


    def api(self, path, method='GET', **kwargs):

        params = kwargs['params'] if 'params' in kwargs else {}
        data = kwargs['data'] if 'data' in kwargs else {}

        if not self.access_token and 'access_token' not in params:
            raise MovesAPIError("You must provide a valid access token.")

        url = "%s/%s" % (self.api_url, path)
        if 'access_token' in params:
            access_token = params['access_token']
            del(params['access_token'])
        else:
            access_token = self.access_token

        headers = {
            "Authorization": 'Bearer ' + access_token
        }

        if 'etag' in params:
            headers['If-None-Match'] = params['etag']
            del(params['etag'])
        
        resp = requests.request(method, url,
                                data=data,
                                params=params,
                                headers=headers)
        if str(resp.status_code)[0] not in ('2', '3'):
            raise MovesAPIError("Error returned via the API with status code (%s):" %
                                resp.status_code, resp.text)
        if resp.status_code == 304:
            raise MovesAPINotModifed("Unmodified")
        
        self._last_headers = resp.headers
        return resp

    def get(self, path, **params):
        return self.parse_response(
            self.api(path, 'GET', params=params))

    def post(self, path, **data):
        return self.parse_response(
            self.api(path, 'POST', data=data))

    def set_first_date(self):
        if not self.first_date:
            response = self.user_profile()
            self.first_date = response['profile']['firstDate']

    def __getattr__(self, name):
        '''\
Turns method calls such as "moves.foo_bar(...)" into
a call to "moves.api('/foo/bar', 'GET', params={...})"
and then parses the response.
'''
        base_path = name.replace('_', '/')

        # Define a function that does what we want.
        def closure(*path, **params):
            'Accesses the /%s API endpoints.'
            path = list(path)
            path.insert(0, base_path)
            return self.parse_response(
                self.api('/'.join(path), 'GET', params=params)
                )

        # Clone a new method with the correct name and doc string.
        retval = types.FunctionType(
            closure.func_code,
            closure.func_globals,
            name,
            closure.func_defaults,
            closure.func_closure)
        retval.func_doc =  closure.func_doc % base_path

        # Cache it to avoid additional calls to __getattr__.
        setattr(self, name, retval)
        return retval

# Give Access to last attribute
_move_client_status = ['etag', 'x-ratelimit-hourlimit', 'x-ratelimit-hourremaining',
                       'x-ratelimit-minutelimit', 'x-ratelimit-minuteremaining']
for att in _move_client_status:
    att = att.replace('-', '_')
    setattr(MovesClient, att, property(lambda self,att=att: self._last_headers.get(att, None)
                                       if self._last_headers else att))
    

########NEW FILE########
