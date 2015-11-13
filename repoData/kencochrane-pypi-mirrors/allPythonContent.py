__FILENAME__ = app
from flask import Flask, render_template, Response
from utils import get_page_data, get_json_data

app = Flask(__name__)

@app.route('/')
def index():
    context = get_page_data()
    return render_template('index.html', **context)

@app.route('/data.json')
def json_data():
    return Response(get_json_data(),mimetype='application/json')

if __name__ == '__main__':
    params = {"debug": True,
              "host":"0.0.0.0",}

    app.run(**params)
########NEW FILE########
__FILENAME__ = config
import os
import json

# mirrors listed here
MIRRORS = [
     ('http', 'pypi.douban.com'),
     ('http', 'pypi.hustunique.com'),
     ('http', 'pypi.gocept.com'),
     ('http', 'pypi.tuna.tsinghua.edu.cn'),
     ('http', 'mirror.picosecond.org/pypi'),
]

EMAIL_OVERRIDE = None # None or "blah@example.com"

def load_config():
    # if at dotcloud load the dotcloud settings
    dotcloud_config = '/home/dotcloud/environment.json'
    if os.path.exists(dotcloud_config):
        env = json.load(open(dotcloud_config))
        return {'host': env['DOTCLOUD_CACHE_REDIS_HOST'],
                  'port': env['DOTCLOUD_CACHE_REDIS_PORT'],
                  'password': env['DOTCLOUD_CACHE_REDIS_PASSWORD'],
                  'db': 1,
                  'ip_api_key': env.get('IPLOC_API_KEY', None),
                  'twitter_consumer_key' : env.get('TWITTER_CONSUMER_KEY', None),
                  'twitter_consumer_secret' : env.get('TWITTER_CONSUMER_SECRET', None),
                  'twitter_access_key' : env.get('TWITTER_ACCESS_KEY', None),
                  'twitter_access_secret' : env.get('TWITTER_ACCESS_SECRET', None),
                  'email_host' : env.get('EMAIL_HOST', None),
                  'email_port' : env.get('EMAIL_PORT', None),
                  'email_user' : env.get('EMAIL_USER', None),
                  'email_password' : env.get('EMAIL_PASSWORD', None),
                  'email_from' : env.get('EMAIL_FROM', None),
                  'email_to' : env.get('EMAIL_TO', None),
                  'email_bcc' : env.get('EMAIL_BCC', None),
                  'email_to_admin': env.get('EMAIL_TO_ADMIN', None),
                  }
    else:
        # local config
        dotcloud_config = '/tmp/environment.json'
        if os.path.exists(dotcloud_config):
            env = json.load(open(dotcloud_config))
            return { 'host': 'localhost',
                     'port': 6379,
                     'password': None,
                     'db': 0,
                     'ip_api_key': env.get('IPLOC_API_KEY', None),
                     'twitter_consumer_key' : env.get('TWITTER_CONSUMER_KEY', None),
                     'twitter_consumer_secret' : env.get('TWITTER_CONSUMER_SECRET', None),
                     'twitter_access_key' : env.get('TWITTER_ACCESS_KEY', None),
                     'twitter_access_secret' : env.get('TWITTER_ACCESS_SECRET', None),
                     'email_host' : env.get('EMAIL_HOST', None),
                     'email_port' : env.get('EMAIL_PORT', None),
                     'email_user' : env.get('EMAIL_USER', None),
                     'email_password' : env.get('EMAIL_PASSWORD', None),
                     'email_from' : env.get('EMAIL_FROM', None),
                     'email_to' : env.get('EMAIL_TO', None),
                     'email_bcc' : env.get('EMAIL_BCC', None),
                     'email_to_admin': env.get('EMAIL_TO_ADMIN', None),
                     }
        else:
            print("can't find a local envirornment file here '/tmp/environment.json' ")
            return None #TODO throw exception?

########NEW FILE########
__FILENAME__ = daily
from mirrorlib import find_out_of_date_mirrors
from config import MIRRORS
from notification import (update_twitter_status, send_warning_email,
                         send_status_email)


def __tweet_outofdate(mirror, last_update):
    """ Send a tweet saying we have a mirror out of date """
    status = "{0} is out of date, it was last updated {1}".format(mirror,
                                                           last_update)
    update_twitter_status(status)


def daily_out_of_date_mirror_check():
    """ run everything """
    results = find_out_of_date_mirrors(mirrors=MIRRORS)

    if results:
        email_message = ""
        for res in results:
            email_message += "{0} was last updated {1}\n".format(
                                                res.get('mirror'),
                                                res.get('time_diff_human'))

            print("{0} is out of date. {1}".format(
                    res.get('mirror'), res.get('time_diff_human')))

            # one tweet for each out of date mirror
            __tweet_outofdate(res.get('mirror'), res.get('time_diff_human'))

        # one email for all out of date mirrors
        send_warning_email(email_message)
    else:
        print("All is good, sending Good message!")
        send_status_email("[All Mirrors are up to date]")


def run():
    """ run all of the daily cron jobs."""
    daily_out_of_date_mirror_check()


if __name__ == '__main__':
    run()

########NEW FILE########
__FILENAME__ = iploc
import json, urllib, urllib2


def get_city(apikey, ip):
    """ get city location for an ip """
    base_url = "http://api.ipinfodb.com/v3/ip-city/"
    variables = {"format":"json",
                "key":apikey,
                "ip":ip,}

    urldata = urllib.urlencode(variables)
    url = "{0}?{1}".format(base_url, urldata)
    urlobj = urllib2.urlopen(url)
    data = urlobj.read()
    urlobj.close()
    return json.loads(data)
    
########NEW FILE########
__FILENAME__ = mirrorlib
#!/usr/bin/env python

# -*- coding: utf-8 -*-
# Open Source Initiative OSI - The MIT License (MIT):Licensing
#
# The MIT License (MIT)
# Copyright (c) 2012 Ken Cochrane (KenCochrane@gmail.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

""" This is a simple library that you can use to find out the status of 
PyPI mirrors. It is based on the information that is found at
http://www.python.org/dev/peps/pep-0381/ and
http://pypi.python.org/mirrors

Updated for PEP 449
http://www.python.org/dev/peps/pep-0449/

"""
import datetime
import urllib2
import time
import operator

MIRROR_URL_FORMAT = "{0}://{1}/last-modified"
MASTER_URL_FORMAT = "https://{0}/daytime"
MASTER_SERVER = "pypi.python.org"

STATUSES = {'GREEN':'Green',
            'YELLOW':'Yellow',
            'RED':'Red'}


def ping_mirror(mirror_url):
    """ Given a mirror_url it will ping it and return the contents and
        the response time """
    try:
        start = time.time()
        res = urllib2.urlopen(mirror_url)
        stop = time.time()
        response_time = round((stop - start) * 1000, 2)
        return res.read().strip(), response_time
    except Exception:
        return None, None


def parse_date(date_str):
    """ parse the date the get back from the mirror """

    if len(date_str) == 17:
        # Used on official mirrors
        date_fmt = '%Y%m%dT%H:%M:%S'
    else:
        # Canonical ISO-8601 format (compliant with PEP 381)
        date_fmt = '%Y-%m-%dT%H:%M:%S'
    return datetime.datetime.strptime(date_str, date_fmt)


def humanize_date_difference(now, other_date=None, offset=None, sign="ago"):
    """ This function prints the difference between two python datetime objects
    in a more human readable form
    """

    if other_date:
        dt = abs(now - other_date)
        delta_d, offset = dt.days, dt.seconds
        if now < other_date:
            sign = "ahead"
    elif offset:
        delta_d, offset = divmod(offset, 60 * 60 * 24)
    else:
        raise ValueError("Must supply other_date or offset (from now)")

    offset, delta_s = divmod(offset, 60)
    delta_h, delta_m = divmod(offset, 60)

    if delta_d:
        fmt = "{d:d} days, {h:d} hours, {m:d} minutes {ago}"
    elif delta_h:
        fmt = "{h:d} hours, {m:d} minutes {ago}"
    elif delta_m:
        fmt = "{m:d} minutes, {s:d} seconds {ago}"
    else:
        fmt = "{s:d} seconds {ago}"
    return fmt.format(d=delta_d, h=delta_h, m=delta_m, s=delta_s, ago=sign)


def mirror_status_desc(how_old):
    """ Get the status description of the mirror """

    if how_old < datetime.timedelta(minutes=60):
        return STATUSES.get('GREEN')
    elif how_old < datetime.timedelta(days=1):
        return STATUSES.get('YELLOW')
    else:
        return STATUSES.get('RED')


def ping_master_pypi_server(master_url_format=MASTER_URL_FORMAT):
    """ Ping the master Pypi server, it is a little different
        then the other servers. """
    # a.pypi.python.org is the master server treat it differently
    m_url = master_url_format.format(MASTER_SERVER)
    res, res_time = ping_mirror(m_url)
    return MASTER_SERVER, res, res_time


def mirror_statuses(mirror_url_format=MIRROR_URL_FORMAT,
                    mirrors=None,
                    ping_master_mirror=True):
    """ get the data we need from the mirrors and return a list of 
    dictionaries with information about each mirror

    ``mirror_url_format`` - Change the url format from the standard one

    ``mirrors`` - provided the list if mirrors to check.
    The list needs to contain a tuple, (protocal, domain) for example:
    [('http, 'pypi.example.com'), ('https', 'pypi2.example.com')]

    ``ping_master_mirror`` - Do you want to include the status of the master
    server in the results. Defaults to True.

    """
    if not mirrors:
        return []

    # scan the mirrors and collect data
    ping_results = []
    for protocol, ml in mirrors:
        m_url = mirror_url_format.format(protocol, ml)
        res, res_time = ping_mirror(m_url)
        ping_results.append((ml, res, res_time))

    if ping_master_mirror:
        # pypi.python.org is the master server treat it differently
        master_results = ping_master_pypi_server()
        ping_results.insert(0, master_results)

    now = datetime.datetime.utcnow()
    results = []
    for ml, res, res_time in ping_results:
        if res:
            last_update = parse_date(res)
            time_diff = abs(now - last_update)
            status = mirror_status_desc(time_diff)
            time_diff_human = humanize_date_difference(now, last_update)
            results.append({'mirror': ml,
                'last_update': last_update,
                'time_now': now,
                'time_diff': time_diff,
                'time_diff_human':  time_diff_human,
                'response_time': res_time,
                'status': status}
            )
        else:
            results.append({'mirror': ml,
                'last_update': "Unavailable",
                'time_now': now,
                'time_diff_human':  "Unavailable",
                'time_diff': 'Unavailable',
                'response_time':  "Unavailable",
                'status': 'Unavailable'}
            )
    return results


def is_master_alive():
    """ Check if the Master server is alive """
    server, response, res_time = ping_master_pypi_server()
    if response is None:
        return False
    return True


def find_out_of_date_mirrors(mirrors=None):
    """ Find the mirrors that are out of date """
    results = mirror_statuses(mirrors=mirrors)
    bad_mirrors = []
    for r in results:
        if r.get('status') == STATUSES.get('RED'):
            bad_mirrors.append(r)
    return bad_mirrors


def __find_mirror_sort(sort_field, mirrors=None, reverse=False):
    """ Find the first mirror that is sorted by sort_field """
    results = mirror_statuses(mirrors=mirrors, ping_master_mirror=False)
    new_list = sorted(results, key=operator.itemgetter(sort_field), reverse=reverse)
    return new_list[0]


def find_fastest_mirror(mirrors=None):
    """ Find the fastest mirror (via response time), might not be up to date """
    return __find_mirror_sort('response_time', mirrors=mirrors)


def find_freshest_mirror(mirrors=None):
    """ Find the freshest mirror (via last updated) """
    return __find_mirror_sort('time_diff', mirrors=mirrors)
########NEW FILE########
__FILENAME__ = notification
import tweepy
import smtplib

from config import load_config, EMAIL_OVERRIDE

CONFIG = load_config()

def prepare_twitter_message(status):
    """ shrink to the right size and add link to site. """
    link = "http://www.pypi-mirrors.org"
    link_len = len(link) + 4
    message_len = 140 - link_len
    status_new = status[:message_len]
    if len(status) > message_len:
        status_new += "..."
    status_new += " {0}".format(link)
    return status_new


def update_twitter_status(status):
    """ update the twitter account's status """

    consumer_key=CONFIG.get('twitter_consumer_key')
    consumer_secret=CONFIG.get('twitter_consumer_secret')

    access_token=CONFIG.get('twitter_access_key')
    access_token_secret=CONFIG.get('twitter_access_secret')

    message = prepare_twitter_message(status)

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)
    api.update_status(message)


def send_warning_email(message):
    """ send a message saying a mirror(s) is out of date. """
    email_to = CONFIG.get('email_to')
    email_from = CONFIG.get('email_from')
    email_template = '''Subject: [pypi-mirrors] Mirror is out of Date Notice

    This is an automated email from http://www.pypi-mirrors.org to let you
    know that the following mirrors are out of date.

    {message}

    --
    This automated message is sent to you by http://www.pypi-mirrors.org If you no
    longer want to receive these emails, please contact Ken Cochrane (@KenCochrane) on twitter
    or reply to this email.
    '''
    email_body = email_template.format(message=message)

    send_email(email_body, email_to, email_from)


def send_status_email(message):
    """ send a daily status message """
    email_to = CONFIG.get('email_to_admin')
    email_from = CONFIG.get('email_from')
    email_template = '''Subject: [pypi-mirrors] Mirrors are all up to date

    This is an automated email from http://www.pypi-mirrors.org to let you
    know that the following mirrors are all up to date.

    {message}
    --
    This automated message is sent to you by http://www.pypi-mirrors.org If you no
    longer want to receive these emails, please contact Ken Cochrane (@KenCochrane) on twitter
    or reply to this email.
    '''

    email_body = email_template.format(message=message)

    send_email(email_body, email_to, email_from)


def send_email(email_body, email_to, email_from):
    """ Send an email using the configuration provided """
    email_host = CONFIG.get('email_host')
    email_port = CONFIG.get('email_port')
    email_user = CONFIG.get('email_user')
    email_password = CONFIG.get('email_password')
    email_bcc = CONFIG.get('email_bcc')

    if EMAIL_OVERRIDE:
        print 'Over-riding email with {0}.'.format(EMAIL_OVERRIDE)
        email = EMAIL_OVERRIDE
    else:
        email = email_to

    print("email to {0} , bcc: {1}; from {2}".format(email, email_bcc, email_from))
    smtp = smtplib.SMTP(email_host, email_port)
    smtp.starttls()
    smtp.login(email_user, email_password)
    smtp.sendmail(email_from, [email, email_bcc], email_body)
    smtp.quit()

    
########NEW FILE########
__FILENAME__ = pypi_mirrors
#!/usr/bin/env python
import json
from mirrorlib import mirror_statuses

from utils import (cache_key, location_name, get_total_seconds, 
                   get_connection, store_page_data, find_number_of_packages,
                   get_location_for_mirror, store_json_data)

from config import MIRRORS

def process_results(results):
    """ process the results and gather data """

    conn = get_connection()
    new_results = []
    for d in results:
        mirror = d.get('mirror')
        status = d.get('status')
        location = get_location_for_mirror(mirror)
        d['location'] = location_name(location)
        if  status != 'Unavailable':
            resp_time = d.get('response_time')
            age = get_total_seconds(d.get('time_diff'))
            conn.rpush(cache_key('RESPTIME', mirror), resp_time )
            conn.rpush(cache_key('AGE', mirror), age)
            resp_list = conn.lrange(cache_key('RESPTIME', mirror), -60, -1)
            age_list = conn.lrange(cache_key('AGE', mirror), -60, -1)
            d['num_packages'] = find_number_of_packages(mirror)
            d['resp_list'] = ",".join(resp_list)
            d['age_list'] = ",".join(age_list)
        new_results.append(d)
    return new_results

def json_results(data):
    results = {}
    for mirror in data:
        results[mirror.get('mirror')] = {
            'status': mirror.get('status', 'n/a'),
            'location': mirror.get('location', 'n/a'),
            'num_packages': mirror.get('num_packages', 'n/a'),
            'last_updated': mirror.get('time_diff_human', 'n/a'),
        }
    return json.dumps(results)

def run():
    """ run everything """
    results = mirror_statuses(mirrors=MIRRORS)
    if results:
        time_now = results[0].get('time_now', None)
    data = process_results(results)
    json_data = json_results(data)

    store_json_data(json_data)
    store_page_data(data, time_now)

if __name__ == '__main__':
    run()

########NEW FILE########
__FILENAME__ = test_run
#!/usr/bin/env python

from jinja2 import Environment, FileSystemLoader
from mirrorlib import mirror_statuses

from utils import (find_number_of_packages)

from config import MIRRORS

def process_results(results):
    """ process the results and gather data """

    new_results = []
    for d in results:
        mirror = d.get('mirror')
        status = d.get('status')
        d['location'] = "n/a"
        if  status != 'Unavailable':
            resp_list = ["1","2","3","4","5","6","7","8","9","10"] # faked out for test
            age_list = ["1","2","3","4","5","6","7","8","9","10"] # faked out for test
            d['num_packages'] = find_number_of_packages(mirror)
            d['resp_list'] = ",".join(resp_list)
            d['age_list'] = ",".join(age_list)
        new_results.append(d)
    return new_results


def url_for(something):
    return something

def run():
    """ run everything """
    results = mirror_statuses(mirrors=MIRRORS)
    if results:
        time_now = results[0].get('time_now', None)
    data = process_results(results)

    env = Environment(loader=FileSystemLoader('templates'))
    # add the dummy url_for so it doesn't throw error.
    env.globals.update(url_for=url_for)
    template = env.get_template('index.html')
    context = {'data': data, 'date_now': time_now}
    print template.render(**context)

if __name__ == '__main__':
    run()

########NEW FILE########
__FILENAME__ = utils
import redis
import socket
from urlparse import urlparse
import requests
import lxml.html

try:
    import cPickle as pickle
except ImportError:
    import pickle

from config import load_config
from iploc import get_city

CONFIG = load_config()

def get_connection():
    """ Get the connection to Redis"""
    return redis.StrictRedis(host=CONFIG.get('host'),
                          port=int(CONFIG.get('port')),
                          db=CONFIG.get('db'),
                          password=CONFIG.get('password'))

def find_number_of_packages(mirror):
    """ Find the number of packages in a mirror """
    html = lxml.html.fromstring(requests.get("http://{0}/simple/".format(mirror)).content)
    return len(html.xpath("//a"))

def ping_ip2loc(ip):
    """ get the location info for the ip
    you need to register for an API key here. http://ipinfodb.com/register.php

    and set it as an envirornment variable called
    PYPI_MIRRORS_API_KEY

    """
    api_key = CONFIG.get('ip_api_key')
    if not api_key:
        return None
    return get_city(api_key, ip)

def get_location_for_mirror(mirror):
    """ get the location for the mirror """
    conn = get_connection()
    loc_key = cache_key('IPLOC', mirror)
    value = conn.get(loc_key)
    if value:
        return pickle.loads(value)

    # if we have a mirror name like mirror.domain.suffix/blah it won't work
    try:
        hostname = urlparse("http://{0}".format(mirror)).netloc
    except Exception as exc:
        # if error, just default to mirror that works most of the time
        print("Error getting location for {0} \n {1}".format(mirror, exc))
        hostname = mirror

    ip = socket.gethostbyname(hostname)
    location = ping_ip2loc(ip)
    if location:
        conn.setex(loc_key, 86400, pickle.dumps(location)) # 1 day cache
        return location
    # if we get here, no good, return None
    return None

def store_page_data(data, time_now):
    """ Store the data in the cache for later use."""
    conn = get_connection()
    context = {'data': data, 'date_now': time_now}
    conn.set('PAGE_DATA', pickle.dumps(context))

def get_page_data():
    """ Get the page data from the cache """
    conn = get_connection()
    data = conn.get('PAGE_DATA')
    if data:
      return pickle.loads(data)
    return {}

def store_json_data(data):
    """ Store the data in the cache for later use."""
    conn = get_connection()
    conn.set('JSON_DATA', data)

def get_json_data():
    """ Get the json data from the cache """
    conn = get_connection()
    data = conn.get('JSON_DATA')
    if not data:
        return {}
    return data

def get_total_seconds(delta):
    """ need this since timedelta.total_seconds() 
    isn't available in python 2.6.x"""
    if delta:
        return delta.seconds + (delta.days * 24 * 3600)
    return 0


def cache_key(token, value):
    """ build a cache key """
    return "{0}_{1}".format(token, value)


def location_name(location):
    """ build out the location name given the location data """
    if not location:
        return "N/A"
    city = location.get('cityName', None)
    region = location.get('regionName', None)
    country = location.get('countryName', None)
    country_code = location.get('countryCode', None)

    # clear out the -'s
    if city and city == '-':
        city = None
    if region and region == '-':
        region = None

    # If we have everything return everything but only use country_code
    if city and region and country_code:
        return "{0}, {1} {2}".format(city, region, country_code)

    # if we just have country, then only return country
    if not city and not region and country:
        return country

    # whatever else we have build it out by dynamically
    name = ""
    if city:
        name += city
    if city and region:
        name += ", "
    if region:
        name += region + " "
    if country:
        name += country
    return name

########NEW FILE########
__FILENAME__ = wsgi
from app import app

application = app

########NEW FILE########
