__FILENAME__ = google
# import the Bot object from IrcTK
from irctk import Bot

# we'll use these later, install Requests if you don't have it already
import requests
import json

# initlize the bot object
bot = Bot()

# an object container for our configuration values
class Config:
    SERVER = 'irc.voxinfinitus.net'
    PORT = 6697
    SSL = True
    TIMEOUT = 300
    NICK = 'kaa'
    REALNAME = 'kaa the python'
    CHANNELS = ['#testing']

# populate the configuration with our Config object
bot.config.from_object(Config)

# the Google search API URL
search_url = 'http://ajax.googleapis.com/ajax/services/search/web'


@bot.command('g')  # also bind this function to '.g'
@bot.command  # register the wrapped function as a plugin
def google(context):
    # notice that we provide one arg, context: this is optional but if you
    # want access to the IRC line that triggered the plugin you need to
    # pass in some variable; we'll use context for this

    query = context.args  # args are parsed automatically by IrcTK

    # make the request, should give us back some JSON
    r = requests.get(search_url, params=dict(v='1.0', safe='off', q=query))

    # load the JSON
    data = json.loads(r.content)

    # if we don't have results, bail out of the plugin
    if not data['responseData']['results']:
        return 'no results found'

    # otherwise grab the first result
    first_result = data['responseData']['results'][0]

    # build our return string
    ret = first_result['titleNoFormatting'] + ' - ' \
            + first_result['unescapedUrl']

    # finally return the result to the channel or user the plugin was called
    # from
    return ret


if __name__ == '__main__':
    bot.run()

########NEW FILE########
__FILENAME__ = config
class Config(object):
    SERVER = 'irc.voxinfinitus.net'
    PORT = 6697
    SSL = True
    TIMEOUT = 300
    NICK = 'kaa'
    REALNAME = 'kaa the python'
    CHANNELS = ['#voxinfinitus', '#testing']

    # admin list
    ADMINS = ['doraemon!~max@staff.voxinfinitus']

    # bitly credentials
    BITLY_LOGIN = 'voxinfinitus'
    BITLY_KEY = 'R_d3664470e5404623b5c0e3a25a873286'

########NEW FILE########
__FILENAME__ = google
from kaa import bot
from kaa.utils import shortener
from kaa.wikipedia import wiki_re, wiki_search
from kaa.youtube import youtube_re, get_video_description

from urllib import quote
from HTMLParser import HTMLParser

import re
import json
import requests

URL = ('http://ajax.googleapis.com/ajax/services/search/'
       '{0}?v=1.0&safe=off&q={1}')


def search(query, kind='web'):
    r = requests.get(URL.format(kind, quote(query)))
    data = json.loads(r.content)
    return data


@bot.command('g')
@bot.command
def google(context):
    data = search(context.args)

    if not data['responseData']['results']:
        return 'no results found'
    first_result = data['responseData']['results'][0]

    url = first_result['unescapedUrl']

    # special handling for Wikipedia
    wiki = re.search(wiki_re, url)
    if wiki:
        desc, url = wiki_search(wiki.groups()[-1])
        return '{0} -- {1}'.format(desc, url)

    # special handling for YouTube
    youtube = re.search(youtube_re, url)
    if youtube:
        vid_id = youtube.groups()[-1]
        desc = get_video_description(vid_id)
        return '{0} -- {1}'.format(desc, url)

    title = first_result['titleNoFormatting'].encode('utf-8', 'replace')
    title = HTMLParser.unescape.__func__(HTMLParser, title)

    ret = title + ' - ' + shortener(url)

    return ret


@bot.command
def gis(context):
    data = search(context.args, 'images')['responseData']['results']
    if not data:
        return 'no images found'
    return data[0]['unescapedUrl']

########NEW FILE########
__FILENAME__ = imdb
# ported from skybot

from kaa import bot

from urllib import quote

import json

import requests


@bot.command('i')
@bot.command
def imdb(context):
    '''.imdb <movie> -- gets information about <movie> from IMDb'''

    r = requests.get('http://www.imdbapi.com/?t=' + quote(context.args))
    content = json.loads(r.content)

    if content['Response'] == 'Movie Not Found':
        return 'movie not found'
    elif content['Response'] == 'True':
        content['URL'] = 'http://www.imdb.com/title/{imdbID}'.format(**content)

        out = '\x02{Title}\x02 ({Year}) ({Genre}): {Plot}'
        if content['Runtime'] != 'N/A':
            out += ' \x02{Runtime}\x02.'
        if content['imdbRating'] != 'N/A' and content['imdbVotes'] != 'N/A':
            out += ' \x02{imdbRating}/10\x02 with \x02{imdbVotes}\x02 votes.'
        out += ' {URL}'
        return out.format(**content)
    else:
        return 'unknown error'

########NEW FILE########
__FILENAME__ = python
from kaa import bot

from urllib import quote

import requests

URL = 'http://eval.appspot.com/eval?statement={0}'


@bot.command('p')
@bot.command
def python(context):
    '.python <exp>'

    query = quote(context.args)

    try:
        r = requests.get(URL.format(query))
    except Exception, e:
        return str(e)

    data = r.text

    if data.startswith('Traceback (most recent call last):'):
        data = data.splitlines()[-1]
    return data

########NEW FILE########
__FILENAME__ = remember
# ported from skybot

from kaa import bot
from kaa.utils import get_db_connection


def db_init(db):
    db.execute('create table if not exists '
               'remember(chan, token, text)')
    db.commit()


def add_remember_token(db, chan, token, text):
    match = db.cursor().execute('select * from remember where '
                                'lower(token)=lower(?) and chan=?',
                                (token, chan)).fetchall()

    append = text.startswith('+')

    if match:
        old_text = get_remember_token(db, chan, token)
        if append:
            text = old_text + ' ' + text.split('+')[1]
        db.execute('update remember set text=? where token=? and chan=?',
                   (text, token, chan))
        db.commit()
        if not append:
            return 'overwrote: ' + old_text
        else:
            return 'appended to record'

    db.execute('replace into remember(chan, token, text) values(?,?,?)',
               (chan, token, text))
    db.commit()
    return 'remember record for {0} added'.format(token)


def get_remember_token(db, chan, token):
    return db.execute('select text from remember where lower(token)=lower(?) '
                      'and chan=? order by lower(token)',
                      (token, chan)).fetchall()[0][0]


@bot.command('r')
@bot.command
def remember(context):
    '.remember <token> <string>, .remember <token> +<string> (append)'
    chan = context.line['sender']

    db = get_db_connection()
    db_init(db)

    args = context.args.split(' ', 1)

    if not len(args) == 2:
        return 'not enough args given'

    token = args[0]
    text = args[1][:1024]

    return add_remember_token(db, chan, token, text)


@bot.regex('([\?])([^\s]+)')
def recall(context):
    db = get_db_connection()
    db_init(db)

    chan = context.line['sender']
    token = context.line['regex_search'].groups()[1]

    return get_remember_token(db, chan, token)

########NEW FILE########
__FILENAME__ = repost
# ported from skybot

from kaa import bot
from kaa.utils import get_db_connection
from kaa.timesince import timesince

import math
import time

expiration_period = 60 * 60 * 24 * 7  # 1 week


def db_init(db):
    db.execute('create table if not exists urlhistory'
               '(chan, url, nick, time)')
    db.commit()


def insert_history(db, chan, url, nick):
    db.execute('insert into urlhistory(chan, url, nick, time) '
               'values(?,?,?,?)', (chan, url, nick, time.time()))
    db.commit()


def get_history(db, chan, url):
    db.execute('delete from urlhistory where time < ?',
               (time.time() - expiration_period,))
    return db.execute('select nick, time from urlhistory where '
                      'chan=? and url=? order by time desc',
                      (chan, url)).fetchall()


def nicklist(nicks):
    nicks = sorted(dict(nicks), key=unicode.lower)
    if len(nicks) <= 2:
        return ' and '.join(nicks)
    else:
        return ', and '.join((', '.join(nicks[:-1]), nicks[-1]))


def format_reply(history):
    if not history:
        return

    last_nick, recent_time = history[0]
    last_time = timesince.timesince(recent_time)

    if len(history) == 1:
        return '{0} linked that {1} ago.'.format(last_nick, last_time)

    hour_span = math.ceil((time.time() - history[-1][1]) / 3600)
    hour_span = '{0:.0f} hours'.format(hour_span if hour_span > 1 else 'hour')

    history_len = len(history)
    ordinal = ['once', 'twice', '%d times'.format(history_len)]
    ordinal[min(history_len, 3) - 1]

    if len(dict(history)) == 1:
        last = 'last linked {0} ago'.format(last_time)
    else:
        last = 'last linked by {0} {1} ago'.format(last_nick, last_time)

    out = 'that url has been posted {0} in the past {1} by {2} ({3}).'
    out = out.format(ordinal, hour_span, nicklist(history), last)

    return out


@bot.regex('([a-zA-Z]+://|www\.)[^ ]+')
def urlinput(context):
    match = context.line['regex_search']
    chan = context.line['sender']
    nick = context.line['sender']

    db = get_db_connection()

    db_init(db)

    url = match.group().encode('utf-8', 'ignore')
    url = url.decode('utf-8')
    history = get_history(db, chan, url)
    insert_history(db, chan, url, nick)

    inp = match.string.lower()

    for name in dict(history):
        if name.lower() in inp:  # person was probably quoting a line
            return               # that had a link. don't remind them.

    if nick not in dict(history):
        return format_reply(history)

########NEW FILE########
__FILENAME__ = tell
# ported from skybot

from kaa import bot
from kaa.utils import get_db_connection
from kaa.timesince import timesince

import time


def db_init(db):
    db.execute('create table if not exists tell'
               '(user_to, user_from, message, chan, time,'
               'primary key(user_to, message))')
    db.commit()


def get_tells(db, user_to):
    return db.execute('select user_from, message, time, chan from tell where'
                      ' user_to=lower(?) order by time',
                      (user_to.lower(),)).fetchall()


@bot.event('PRIVMSG')
def tellinput(context):
    if 'showtells' in context.line['message'].lower():
        return

    nick = context.line['user']

    db = get_db_connection()
    db_init(db)

    tells = get_tells(db, nick)

    if tells:
        user_from, message, time, chan = tells[0]
        past = timesince(time)
        reply = '{0} said {1} ago in {2}: {3}'.format(user_from,
                                                      past,
                                                      chan,
                                                      message)
        if len(tells) > 1:
            reply += \
                    ' (+{0} more, .showtells to view)'.format((len(tells) - 1))

        db.execute('delete from tell where user_to=lower(?) and message=?',
                   (nick, message))
        db.commit()
        return reply


@bot.command
def showtells(context):
    '.showtells -- view all pending tell messages (sent in PM).'

    nick = context.line['user']

    db = get_db_connection()
    db_init(db)

    tells = get_tells(db, nick)

    if not tells:
        bot.reply('You have no pending tells.',
                  context,
                  recipient=nick,
                  notice=True)
        return

    for tell in tells:
        user_from, message, time, chan = tell
        past = timesince(time)
        bot.reply('{0} said {1} ago in {2}: {3}'.format(user_from,
                                                        past,
                                                        chan,
                                                        message),
                  context, recipient=nick, notice=True)

    db.execute('delete from tell where user_to=lower(?)', (nick,))
    db.commit()


@bot.command
def tell(context):
    '.tell <nick> <message>'

    db = get_db_connection()
    db_init(db)

    query = context.args.split(' ', 1)
    nick = context.line['user']
    chan = context.line['sender']

    if len(query) != 2:
        return tell.__doc__

    user_to = query[0].lower()
    message = query[1].strip()
    user_from = nick

    if chan.lower() == user_from.lower():
        chan = 'a pm'

    if user_to == user_from.lower():
        return 'No.'

    if db.execute('select count() from tell where user_to=?',
                  (user_to,)).fetchone()[0] >= 5:
        return 'That person has too many things queued.'

    try:
        db.execute('insert into tell(user_to, user_from, message, chan, '
                   'time) values(?,?,?,?,?)', (user_to,
                                               user_from,
                                               message,
                                               chan,
                                               time.time()))
        db.commit()
    except db.IntegrityError:
        return 'Message has already been queued.'
    return 'I\'ll pass that along.'

########NEW FILE########
__FILENAME__ = timesince
# Copyright (c) Django Software Foundation and individual contributors.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  1. Redistributions of source code must retain the above copyright notice,
#     this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
#  3. Neither the name of Django nor the names of its contributors may be used
#     to endorse or promote products derived from this software without
#     specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"AND
#ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#DISCLAIMED.IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
#ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import datetime


def timesince(d, now=None):
    """
    Takes two datetime objects and returns the time between d and now
    as a nicely formatted string, e.g. "10 minutes".  If d occurs after now,
    then "0 minutes" is returned.

    Units used are years, months, weeks, days, hours, and minutes.
    Seconds and microseconds are ignored.  Up to two adjacent units will be
    displayed.  For example, "2 weeks, 3 days" and "1 year, 3 months" are
    possible outputs, but "2 weeks, 3 hours" and "1 year, 5 days" are not.

    Adapted from http://blog.natbat.co.uk/archive/2003/Jun/14/time_since
    """
    chunks = (
      (60 * 60 * 24 * 365, ('year', 'years')),
      (60 * 60 * 24 * 30, ('month', 'months')),
      (60 * 60 * 24 * 7, ('week', 'weeks')),
      (60 * 60 * 24, ('day', 'days')),
      (60 * 60, ('hour', 'hours')),
      (60, ('minute', 'minutes'))
    )

    # Convert int or float (unix epoch) to datetime.datetime for comparison
    if isinstance(d, int) or isinstance(d, float):
        d = datetime.datetime.fromtimestamp(d)

    # Convert datetime.date to datetime.datetime for comparison.
    if not isinstance(d, datetime.datetime):
        d = datetime.datetime(d.year, d.month, d.day)
    if now and not isinstance(now, datetime.datetime):
        now = datetime.datetime(now.year, now.month, now.day)

    if not now:
        now = datetime.datetime.now()

    # ignore microsecond part of 'd' since we removed it from 'now'
    delta = now - (d - datetime.timedelta(0, 0, d.microsecond))
    since = delta.days * 24 * 60 * 60 + delta.seconds
    if since <= 0:
        # d is in the future compared to now, stop processing.
        return u'0 ' + 'minutes'
    for i, (seconds, name) in enumerate(chunks):
        count = since // seconds
        if count != 0:
            break

    if count == 1:
        s = '%(number)d %(type)s' % {'number': count, 'type': name[0]}
    else:
        s = '%(number)d %(type)s' % {'number': count, 'type': name[1]}

    if i + 1 < len(chunks):
        # Now get the second item
        seconds2, name2 = chunks[i + 1]
        count2 = (since - (seconds * count)) // seconds2
        if count2 != 0:
            if count2 == 1:
                s += ', %d %s' % (count2, name2[0])
            else:
                s += ', %d %s' % (count2, name2[1])
    return s


def timeuntil(d, now=None):
    """
    Like timesince, but returns a string measuring the time until
    the given time.
    """
    if not now:
        now = datetime.datetime.now()
    return timesince(now, d)

########NEW FILE########
__FILENAME__ = urbandict
from kaa import bot

from urllib import quote

import json

import requests

LINE_LIMIT = 1000


@bot.command('u')
@bot.command
def urbandict(context):
    url ='http://www.urbandictionary.com/iphone/search/define?term={0}'
    url = url.format(quote(context.args))
    r = requests.get(url)
    data = json.loads(r.content)
    if not data['list'][0].get('definition'):
        return 'no results found'
    data = data['list'][0]['definition'].splitlines()
    data = ' '.join(data)
    return data[:LINE_LIMIT]

########NEW FILE########
__FILENAME__ = utils
from kaa import bot
from kaa.wikipedia import wiki_re
from kaa.youtube import youtube_re

from StringIO import StringIO
from itertools import groupby
from lxml import html

import json
import sqlite3
import re

import requests

BITLY_LOGIN = bot.config['BITLY_LOGIN']
BITLY_KEY = bot.config['BITLY_KEY']


def get_db_connection(name=None):
    if name is None:
        name = '{0}.{1}.db'.format(bot.config['NICK'], bot.config['SERVER'])
    return sqlite3.connect(name, timeout=10)


def shortener(url):
    api_url = 'https://api-ssl.bitly.com/v3/shorten'
    r = requests.get(api_url, params=dict(longUrl=url,
                                      format='json',
                                      login=BITLY_LOGIN,
                                      apiKey=BITLY_KEY))
    data = json.loads(r.content)['data']
    if data:
        return data['url']
    return 'error shortening url'


def find_urls(message, urls=None):
    message = message + ' '
    extra = None

    if urls is None:
        urls = []

    if 'http' in message:
        url, extra = message[message.index('http'):].split(' ', 1)
        urls.append(url)
    elif 'www.' in message:
        url, extra = message[message.index('www.'):].split(' ', 1)
        urls.append(url)

    if extra:
        find_urls(extra)

    return urls


@bot.command('.')
@bot.command('help')
@bot.command
def usage(context):
    '''.usage <plugin>'''
    plugin = context.args
    if plugin:
        for p in bot.config['PLUGINS']:
            if plugin == p['hook']:
                return p['funcs'][0].__doc__
    else:
        p = [(p['hook'], p['funcs']) for p in bot.config['PLUGINS']]
        p.sort(key=lambda t: t[1])
        result = []
        # group by function
        for k, v in groupby(p, key=lambda t: t[1]):
            grouped = [v[0] for v in v]
            grouped[0] = '\x02' + grouped[0] + '\x02'
            if len(grouped) > 1:
                # shortcuts/secondary
                for i, hook in enumerate(grouped[1:]):
                    grouped[i+1] = '[' + grouped[i+1] + ']'
            result.append(' '.join(grouped))
        result.sort()
        p = ', '.join(result)
        return 'Plugins currently loaded: ' + p


@bot.command
def raw(context):
    '''.raw <command>'''
    if not context.line['prefix'] in bot.config.get('ADMINS', []):
        return
    if context.args:
        command = context.args.split(' ', 1)[0]
        args = list(context.args.split(' ', 1)[-1])
        bot.irc.send_command(command, args)
    else:
        return raw.__doc__


@bot.event('PRIVMSG')
def shorten(context):
    message = context.line['message']
    schemes = ('http://', 'https://', 'www.')
    contains_url = True in map(lambda scheme: scheme in message, schemes)

    if not contains_url:
        return

    wiki = re.search(wiki_re, context.line['message'])
    if wiki:
        return

    youtube = re.search(youtube_re, context.line['message'])
    if youtube:
        return

    urls = find_urls(message)

    titles_and_urls = []
    for url in urls:
        try:
            r = requests.get(url)
        except Exception:
            return 'unable to open url: ' + url

        parsed_page = html.parse(StringIO(r.content))
        title = parsed_page.find('.//title')
        url = shortener(url)

        if title is not None:
            title = title.text
            titles_and_urls.append(title + ' - ' + url)
        else:
            titles_and_urls.append(url)

    for result in titles_and_urls:
        bot.reply(result, context.line)

########NEW FILE########
__FILENAME__ = weather
# ported from skybot

from kaa import bot
from kaa.utils import get_db_connection

from urllib import quote
from lxml import etree

import requests


@bot.command('w')
@bot.command
def weather(context):
    '.weather <location>'

    db = get_db_connection()

    location = context.args
    hostmask = context.line['prefix'].split('!', 1)[-1]

    db.cursor().execute('create table if not exists ' \
                        'weather(host primary key, loc)')

    if not location:
        location = \
            db.cursor().execute('select loc from weather where host=lower(?)',
                                (hostmask,)).fetchone()[0]
        if not location:
            return weather.__doc__

    url = 'http://www.google.com/ig/api?weather=' + quote(location)
    r = etree.fromstring(requests.get(url).content)
    r = r.find('weather')

    if r.find('problem_cause') is not None:
        return ('Couldn\'t retrieve weather for {0}.'.format(location))

    info = dict((e.tag, e.get('data')) for e in r.find('current_conditions'))
    info['city'] = r.find('forecast_information/city').get('data')
    info['high'] = r.find('forecast_conditions/high').get('data')
    info['low'] = r.find('forecast_conditions/low').get('data')

    if location:
        db.execute('insert or replace into weather(host, loc) values (?,?)',
                   (hostmask, location))
        db.commit()

    return ('{city}: {condition}, {temp_f}F/{temp_c}C (H:{high}F, L:{low}), '
            '{humidity}, {wind_condition}.'.format(**info))

########NEW FILE########
__FILENAME__ = wikipedia
# ported from skybot

from kaa import bot

from urllib import quote

from lxml import etree

import re

import requests

api_prefix = 'http://en.wikipedia.org/w/api.php'
search_url = api_prefix + '?action=opensearch&format=xml'

paren_re = re.compile('\s*\(.*\)$')

wiki_re = '(\http|\https)(\://*.[a-zA-Z]{0,1}\.*wikipedia.+?)' \
     '(\com/wiki/|\org/wiki/)([^\s]+)'
wiki_re = re.compile(wiki_re)


def wiki_search(query):
    r = requests.get(search_url, params=dict(search=query))
    data = etree.fromstring(r.content)

    ns = '{http://opensearch.org/searchsuggest2}'
    items = data.findall(ns + 'Section/' + ns + 'Item')

    if items == []:
        if data.find('error') is not None:
            return 'error: {code}: {info}'.format(data.find('error').attrib)
        else:
            return 'no results found'

    def extract(item):
        return [item.find(ns + e).text for e in ('Text', 'Description', 'Url')]

    title, desc, url = extract(items[0])

    if 'may refer to' in desc:
        title, desc, url = extract(items[1])

    title = '\x02' + paren_re.sub('', title) + '\x02 -- '

    if title.lower() not in desc.lower():
        desc = title + desc

    desc = re.sub('\s+', ' ', desc).strip()  # remove excess spaces

    if len(desc) > 300:
        desc = desc[:300].rsplit(' ', 1)[0] + '...'

    desc = desc.encode('utf-8', 'replace')
    return desc, url


@bot.regex(wiki_re)
def wiki_find(context):
    query = context.line['regex_search'].groups()[-1]
    desc, _ = wiki_search(query)
    return desc


@bot.command('wi')
@bot.command('wiki')
@bot.command
def wikipedia(context):
    '''.wikipedia <query>'''
    desc, url = wiki_search(context.args)
    return '{0} -- {1}'.format(desc, quote(url, ':/'))

########NEW FILE########
__FILENAME__ = youtube
# ported from skybot

from kaa import bot

import re
import json
import time
import locale

import requests

youtube_re = (r'(?:youtube.*?(?:v=|/v/)|youtu\.be/|yooouuutuuube.*?id=)'
              '([-_a-z0-9]+)',
              re.I)
youtube_re = re.compile(*youtube_re)

base_url = 'http://gdata.youtube.com/feeds/api/'
url = base_url + 'videos/{0}?v=2&alt=jsonc'
search_api_url = base_url + 'videos?v=2&alt=jsonc&max-results=1'
video_url = "http://youtube.com/watch?v={0}"


def get_video_description(vid_id):
    r = requests.get(url.format(vid_id))
    data = json.loads(r.content)

    if data.get('error'):
        return

    data = data['data']
    data['title'] = data['title'].encode('utf-8', 'replace')

    out = '\x02{title}\x02'.format(**data)

    if not data.get('duration'):
        return out

    out += ' - length \x02'
    length = data['duration']
    if length / 3600:  # > 1 hour
        out += '{0}h '.format(length / 3600)
    if length / 60:
        out += '{0}m '.format(length / 60 % 60)
    out +='"{0}s\x02'.format(length % 60)

    if 'rating' in data:
        out += \
            ' - rated \x02{rating:.2f}/5.0\x02 ({ratingCount})'.format(**data)

    # The use of str.decode() prevents UnicodeDecodeError with some locales
    # See http://stackoverflow.com/questions/4082645/
    if 'viewCount' in data:
        formated_locale = locale.format('%d', data['viewCount'], 1)
        formated_locale = formated_locale.decode('utf-8')
        out += ' - \x02{0}\x02 views'.format(formated_locale)

    upload_time = time.strptime(data['uploaded'], '%Y-%m-%dT%H:%M:%S.000Z')
    out += ' - \x02{0}\x02 on \x02{1}\x02'.format(data['uploader'],
                time.strftime('%Y.%m.%d', upload_time))

    if 'contentRating' in data:
        out += ' - \x034NSFW\x02'

    return out


@bot.regex(youtube_re)
def youtube_url(context):
    vid_id = context.line['regex_search'].groups()[0]
    return get_video_description(vid_id)


@bot.command('y')
@bot.command
def youtube(context):
    '.youtube <query>'

    r = requests.get(search_api_url, params=dict(q=context.args))

    data = json.loads(r.content)

    if 'error' in data:
        return 'error performing search'

    if data['data']['totalItems'] == 0:
        return 'no results found'

    vid_id = data['data']['items'][0]['id']

    return get_video_description(vid_id) + ' - ' + video_url.format(vid_id)

########NEW FILE########
__FILENAME__ = runner
from kaa import bot


if __name__ == '__main__':
    bot.run()

########NEW FILE########
__FILENAME__ = bot
# -*- coding: utf-8 -*-
'''
    irctk.bot
    ---------

    This defines the main class, `Bot`, for use in creating new IRC bot apps.
'''

import os
import re
import time
import inspect
import thread

from irctk.logging import create_logger
from irctk.config import Config
from irctk.reloader import ReloadHandler
from irctk.plugins import PluginHandler
from irctk.ircclient import TcpClient, IrcWrapper


class Bot(object):
    # used to track the instance of the Bot class
    __shared_state = {}

    # initialize the logger as None
    logger = None

    # initlialize the config as None
    config = None

    # initalize the plugin as None
    plugin = None

    # initalize the reloader as None
    reloader = None

    # set our root path
    root_path = os.path.abspath('')

    # base configuration
    default_config = {'SERVER': '',
                      'PORT': 6667,
                      'PASSWORD': None,
                      'SSL': False,
                      'TIMEOUT': 300,
                      'NICK': '',
                      'USER': None,
                      'REALNAME': '',
                      'CHANNELS': [],
                      'PLUGINS': [],
                      'EVENTS': [],
                      'REGEX': [],
                      'MAX_WORKERS': 7,
                      'MIN_WORKERS': 3,
                      'CMD_PREFIX': '.'}

    def __init__(self):
        self.__dict__ = self.__shared_state

        if self.logger is None:
            self.logger = create_logger()

        # configure the bot instance
        if self.config is None:
            self.config = Config(self, self.root_path, self.default_config)
        else:
            # make sure we clear these upon reloads
            self.config['PLUGINS'] = []
            self.config['EVENTS'] = []
            self.config['REGEX'] = []

        # initialize the plugin handler
        if self.plugin is None:
            self.plugin = PluginHandler(self)

        # initalize the reload handler
        if self.reloader is None:
            self.reloader = ReloadHandler(self)

    def _create_connection(self):
        self.connection = TcpClient(self.config['SERVER'],
                                    self.config['PORT'],
                                    self.config['SSL'],
                                    self.config['TIMEOUT'],
                                    logger=self.logger)

        self.irc = IrcWrapper(self.connection,
                              self.config['NICK'],
                              self.config['REALNAME'],
                              self.config['PASSWORD'],
                              self.config['CHANNELS'],
                              logger=self.logger,
                              user=self.config['USER'])

    def _parse_input(self, wait=0.01):
        '''This internal method handles the parsing of commands and events.
        Hooks for commands are prefixed with a character, by default `.`. This
        may be overriden by specifying `prefix`.

        A context is maintained by our IRC wrapper, `IrcWrapper`; referenced
        as `self.irc`. In order to prevent a single line from being parsed
        repeatedly a variable `stale` is set to either True or False.

        If the context is fresh, i.e. not `stale`, we loop over the line
        looking for matches to plugins.

        Once the context is consumed, we set the context variable `stale` to
        True.
        '''
        prefix = self.config['CMD_PREFIX']

        while True:
            time.sleep(wait)

            with self.irc.lock:
                args = self.irc.context.get('args')
                command = self.irc.context.get('command')
                message = self.irc.context.get('message')
                raw = self.irc.context.get('raw')

                while not self.context_stale and args:

                    # process regex
                    for regex in self.config['REGEX']:
                        hook = regex['hook']
                        search = re.search(hook, raw)
                        if not search:
                            continue
                        regex['context'] = dict(self.irc.context)
                        regex['context']['regex_search'] = search
                        self.plugin.enqueue_plugin(regex,
                                                   hook,
                                                   raw,
                                                   regex=True)

                    # process for a message
                    if message.startswith(prefix):
                        for plugin in self.config['PLUGINS']:
                            plugin['context'] = dict(self.irc.context)
                            hook = prefix + plugin['hook']
                            self.plugin.enqueue_plugin(plugin, hook, message)

                    # process for a command
                    if command and command.isupper():
                        for event in self.config['EVENTS']:
                            event['context'] = dict(self.irc.context)
                            hook = event['hook']
                            self.plugin.enqueue_plugin(event, hook, command)

                    # irc context consumed; mark it as such
                    self.irc.context['stale'] = True

    @property
    def context_stale(self):
        return self.irc.context.get('stale', True)

    def command(self, hook=None, **kwargs):
        '''This method provides a decorator that can be used to load a
        function into the global plugins list.

        If the `hook` parameter is provided the decorator will assign the hook
        key to the value of `hook`, update the `plugin` dict, and then return
        the wrapped function to the wrapper.

        Therein the plugin dictionary is updated with the `func` key whose
        value is set to the wrapped function.

        Otherwise if no `hook` parameter is passed the, `hook` is assumed to
        be the wrapped function and handled accordingly.
        '''
        plugin = {}

        def wrapper(func):
            plugin.setdefault('hook', func.func_name)
            plugin['funcs'] = [func]
            self.plugin._update_plugin(plugin, 'PLUGINS')
            return func

        if kwargs or not inspect.isfunction(hook):
            if hook:
                plugin['hook'] = hook
            plugin.update(kwargs)
            return wrapper
        else:
            return wrapper(hook)

    def event(self, hook, **kwargs):
        '''This method provides a decorator that can be used to load a
        function into the global events list.

        It assumes one parameter, `hook`, i.e. the event you wish to bind
        this wrapped function to. For example, JOIN, which would call the
        function on all JOIN events.
        '''
        plugin = {}

        def wrapper(func):
            plugin['funcs'] = [func]
            self.plugin._update_plugin(plugin, 'EVENTS')
            return func

        plugin['hook'] = hook
        plugin.update(kwargs)
        return wrapper

    def regex(self, hook, **kwargs):
        '''Takes a regular expression as a hook.'''
        plugin = {}

        def wrapper(func):
            plugin['funcs'] = [func]
            self.plugin._update_plugin(plugin, 'REGEX')
            return func

        plugin['hook'] = hook
        plugin.update(kwargs)
        return wrapper

    def add_command(self, hook, func):
        self.plugin._add_plugin(hook, func, command=True)

    def add_event(self, hook, func):
        self.plugin._add_plugin(hook, func, event=True)

    def add_regex(self, hook, func):
        self.plugin._add_plugin(hook, func, regex=True)

    def remove_command(self, hook, func):
        self.plugin._remove_plugin(hook, func, command=True)

    def remove_event(self, hook, func):
        self.plugin._remove_plugin(hook, func, event=True)

    def remove_regex(self, hook, func):
        self.plugin._remove_plugin(hook, func, regex=True)

    def reply(self, message, context, action=False, notice=False,
            recipient=None, line_limit=400):

        # conditionally set the recipient automatically
        if recipient is None:
            if context['sender'].startswith('#'):
                recipient = context['sender']
            else:
                recipient = context['user']

        def messages(message):
            message, extra = message[:line_limit], message[line_limit:]
            yield message
            if extra:
                for message in messages(extra):
                    yield message

        for message in messages(message):
            self.irc.send_message(recipient, message, action, notice)

    def run(self, wait=0.1):
        # create connection
        self._create_connection()

        # connect
        self.connection.connect()

        # start the irc wrapper
        self.irc.run()

        # start the input parsing loop in a new thread
        thread.start_new_thread(self._parse_input, ())

        while True:
            time.sleep(wait)

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-
'''
    irctk.config
    ------------

    Sets up the configuration object.
'''

import imp
import os


class Config(dict):
    def __init__(self, bot, root_path, defaults=None):
        dict.__init__(self, defaults or {})
        self.root_path = root_path

    def from_pyfile(self, filename):
        filename = os.path.join(self.root_path, filename)
        d = imp.new_module('config')
        d.__file__ = filename
        execfile(filename, d.__dict__)
        self.from_object(d)
        return True

    def from_object(self, obj):
        for key in dir(obj):
            if key.isupper():
                self[key] = getattr(obj, key)

    def __repr__(self):
        return '<{0!r} {0!r}>'.format(self.__class__.__name__,
                                      dict.__repr__(self))

########NEW FILE########
__FILENAME__ = ircclient
# -*- coding: utf-8 -*-
'''
    irctk.ircclient
    ---------------

    Provides two classes, `TcpClient` and `IrcWrapper`.

    `TcpClient` is a TCP client tailored for IRC connections. It provides
    processing for the data received by and sent to the server.

    `IrcWrapper` is a wrapper for some of the IRC protocol. This API is
    incomplete but covers much of the core functionality needed to make and
    sustain connections.
'''

import socket
import thread
import Queue
import time

from ssl import wrap_socket, SSLError


class TcpClient(object):
    '''This is a TCP client that has been adapted for IRC connections. The
    recieving and sending methods, `_recv` and `_send`, are wrapped in threads
    to allow for asynchronous communication.

    The `run` method is used to start the server and initiate the recieving
    and sending threads. Before doing so a default socket timeout is set,
    using the value of `self.timeout`. If self.ssl is True the socket is
    wrapped accordingly.

    The `close` method is used to close a connection. In order to exit loops a
    switch `self.shutdown` is used. Initially this is set to False but when
    `close()` is called this attribute is set to True.

    TODO: In order to prevent the server from disconnecting us for flooding,
    some kind of timed, rate-limiter should be implemented in the send loop.

    Also a logger should be implemented that would replace any print
    statements that are currently being used for debug functionality. However
    this is likely better as a project-wide implementation so for now it
    remains on the TODO list.

    An instance of this class might look like this:

        client = TcpClient('irc.voxinfinitus.net', 6697, True)

        # start the client-connection to the server
        client.connect()

        # close the client-connection to the server
        client.close()
    '''

    def __init__(self, host, port, ssl=False, timeout=300.0, logger=None):
        self.host = host
        self.port = port
        self.ssl = ssl
        self.inp = Queue.Queue()
        self.out = Queue.Queue()
        self.inp_buffer = ''
        self.out_buffer = ''
        self.shutdown = False
        self.timeout = timeout
        self.reconnect_on_error = True
        socket.setdefaulttimeout(self.timeout)
        self.logger = logger

    def connect(self, reconnect=False):
        '''This method initiates the socket connection by passing a tuple,
        `server` containing the host and port, to the socket object and then
        wraps our `_recv` and `_send` methods in threads.

        Necessarily `self.shutdown` is set to False in the event that it might
        have been reset, e.g. in the case of a disconnect and reconnect.

        The default socket timeout is also set here. Our value here is
        provided by `self.timeout`.

        Finally the two primary loops, `_send()` and `_recv()` are invoked as
        threads.
        '''

        self.shutdown = False

        self.socket = socket.socket()
        if self.ssl:
            self.socket = wrap_socket(self.socket)

        server = (self.host, self.port)
        self.socket.connect(server)
        if not reconnect:
            thread.start_new_thread(self._recv, ())
            thread.start_new_thread(self._send, ())

    def close(self, wait=1.0):
        '''This method closes an open socket. As per the original UNIX spec,
        the socket is first alerted of an imminent shutdown by calling
        `shutdown()`. We then wait for `wait`-number of seconds. Finally we
        call `close()` on the socket.
        '''

        self.shutdown = True

        self.socket.shutdown(1)
        time.sleep(wait)
        try:
            self.socket.close()  # seems to cause a problem: errno 9
        except Exception:
            pass

    def reconnect(self, wait=1.0):
        '''This method will attempt to reconnect to a server. It should be
        called contextually after some failure perhaps. If the reconnection
        fails the error will be reported and execution will carry on.

        The `wait` parameter indicates the time in seconds to wait before
        trying to reconnect. Default is 30.

        Before attempting to connect this method will try to terminate an
        existing socket connection if one exists.
        '''

        try:
            self.close()
        except Exception, e:
            self.logger.debug('Exception while closing old socket: ' + str(e))

        time.sleep(wait)
        self.connect(reconnect=True)

    def _recv(self, reconnect_wait=5.0, byte_size=4096):
        while True:

            try:
                if not self.shutdown:
                    data = self.socket.recv(byte_size)
            except (SSLError, socket.error, socket.timeout):
                if self.reconnect_on_error:
                    self.logger.error('Connection lost, reconnecting.')
                    self.reconnect(reconnect_wait)
                    self.inp.put('Error :Closing Link:\r\n')
                    reconnect_wait *= reconnect_wait
                    continue
                else:
                    self.close()

            self.inp_buffer += data

            while '\r\n' in self.inp_buffer and not self.shutdown:

                line, self.inp_buffer = self.inp_buffer.split('\r\n', 1)
                self.inp.put(line + '\r\n')
                self.logger.info(line)

    def _send(self):
        '''Internal method that processes outgoing data.'''

        while True:
            line = self.out.get(True).splitlines()
            if line:
                line = line[0]
                self.out_buffer += line + '\r\n'
                self.logger.info(line)

            while self.out_buffer and not self.shutdown:
                sent = self.socket.send(self.out_buffer)
                self.out_buffer = self.out_buffer[sent:]


class IrcWrapper(object):
    '''This class is a wrapper object for the modified TCP client,
    `TcpClient`, which provides various convenience methods that wrap some
    IRC functionality.

    An existing TCP connection of `TcpClient` is anticipated by this class. In
    this way we can decouple the connection and wrapper in the event that we
    want to reload or otherwise alter the wrapper logic.

    An instance of this class might look like:

        # setup a client-connection with SSL
        client = TcpClient('irc.voxinfinitus.net', 6697, True)

        # connect to the server
        client.connect()

        # define some channels to join
        channels = ['#voxinfinitus', '#testing']

        irc = IrcWrapper(client, 'Kaa', 'Kaa the Python', None, channels)
    '''

    def __init__(self, connection, nick, realname, password, channels, logger, user=None):
        if user is None:
            user = nick

        self.connection = connection
        self.nick = nick
        self.realname = realname
        self.password = password
        self.user = 'USER ' + user + ' 3 * :' + realname
        self.channels = channels
        self.inp_buffer = ''
        self.out_buffer = ''
        self.lock = thread.allocate_lock()

        self.context = {}

    def _register(self):
        '''This internal method attempts to register the connection with the
        server by sending the NICK and then USER commands as soon as the
        connection object is received.
        '''

        lines = []
        if self.password != None:
            lines.append('PASS ' + self.password)
        lines += ['NICK ' + self.nick, self.user]
        self._send_lines(lines)

    def _send(self, wait=0.1, wait_time=1.0, wait_base=1.0, byte_size=8192):
        '''This internal method reads off of `self.out_buffer`, sending the
        contents to the connection object's output queue.

        Here we use `time.sleep` to sleep `wait`-number of seconds. This
        prevents the threads from running all the time and consequently
        maxing out the CPU.

        TODO: rate limiter does not yet work. Perhaps a proper implementation
        of the leaky bucket?
        '''

        while True:
            time.sleep(wait)
            while '\r\n' in self.out_buffer and not self.connection.shutdown:
                line, self.out_buffer = self.out_buffer.split('\r\n', 1)
                if len(self.out_buffer) >= byte_size:
                    wait_time *= wait_time
                    time.sleep(wait_time)
                elif wait_time > wait_base:
                    wait_time /= wait_time
                elif wait_time < wait_base:
                    wait_time = wait_base
                self.connection.out.put(line)

    def _recv(self, reconnect_wait=5.0):
        '''This internal method pulls data from the connection's input queue.
        It then places this information in a local input buffer and loops over
        this buffer, line by line, parsing it via `_parse_line()`.

        Parsed lines are stored in `self.prefix`, 'self.command', and
        'self.args'.

        In this loop we check to see if the connection has been properly
        registered with the server and if so loop through the channels defined
        in `self.channels`, sending a JOIN command for each respectively.

        Here we use `time.sleep` to sleep `wait`-number of seconds. This
        prevents the threads from running all the time and consequently
        maxing out the CPU.
        '''

        while True:
            self.inp_buffer += self.connection.inp.get()
            while '\r\n' in self.inp_buffer and not self.connection.shutdown:
                with self.lock:
                    self.line, self.inp_buffer = \
                            self.inp_buffer.split('\r\n', 1)

                    self.prefix, self.command, self.args = \
                            self._parse_line(self.line)

                    self.sender = self.args[0]
                    self.message = self.args[-1]

                    self.context = \
                            {'prefix': self.prefix,
                             'command': self.command,
                             'args': self.args,
                             'sender': self.sender if self.args else '',
                             'user': self.prefix.rsplit('!', 1)[0],
                             'hostmask': self.prefix.rsplit('!', 1)[-1],
                             'message': self.message if self.args else '',
                             'raw': self.line,
                             'stale': False}

                    if 'ERROR :Closing link:' in self.line:
                        error = 'Connection lost, reconnecting.'
                        self.connection.logger.error(error)
                        self.connection.reconnect(reconnect_wait)
                        self.connection.inp.put('RECONNECT :server\r\n')
                        reconnect_wait *= reconnect_wait

                    if self.command == 'PING':
                        self._send_line('PONG ' + ''.join(self.args))
                    elif self.command == '001' and self.channels:
                        for channel in self.channels:
                            self._send_line('JOIN ' + channel)
                    elif self.command == '433':
                        self.nick = self.nick + '_'
                        self._send_line('NICK ' + self.nick)
                    elif self.command == 'RECONNECT':
                        self._register()

    def _parse_line(self, line):
        '''This internal method takes a line as recieved from the IRC server
        and parses it appropriately.

        Returns `prefix`, `command`, `args`.
        '''

        prefix = ''
        trailing = []
        if not line:
            raise Exception('Received an empty line from the server.')

        if line[0] == ':':
            prefix, line = line[1:].split(' ', 1)

        if line.find(' :') != -1:
            line, trailing = line.split(' :', 1)
            args = line.split()
            args.append(trailing)
        else:
            args = line.split()

        command = args.pop(0)

        return prefix, command, args

    def _send_line(self, line):
        '''This internal method takes one parameter, `lines`, loops over it
        and sends each element directly to the `_send()` loop. This is used
        for sending raw messages to the server. Not for use outside of the
        scope of this class!

        This method is not rate-limited. Use with caution.
        '''
        self.out_buffer += line + '\r\n'

    def _send_lines(self, lines):
        '''This internal method takes one parameter, `lines`, loops over it
        and sends each element directly to the `_send()` loop. This is used
        for sending raw messages to the server. Not for use outside of the
        scope of this class!

        The a `rate` of lines to send may be specified, defaults to 5.0. This
        corresponds to the `per` parameter, which detauls to 20.0. So a rate
        of 5 lines per 20 seconds is the default, i.e. no more than 5 lines
        in 20 seconds.
        '''
        for line in lines:
            self.out_buffer += line + '\r\n'

    def run(self):
        '''This method sets up the connection by sending the USER command to
        the server we are connecting to. Once our client is acknowledged and
        properly registered with the server we can loop through
        `self.channels` and join the respective channels therein.
        '''
        self._register()
        thread.start_new_thread(self._recv, ())
        thread.start_new_thread(self._send, ())

    def send_command(self, command, args=[], prefix=None):
        '''This method provides a wrapper to an IRC command. It takes two
        parameters, `command` and `args` which relate to their respective IRC
        equivalents.

        The arguments are concatenated to the command and then sent along to
        the connection queue.
        '''
        command = command + ' ' + ''.join(args)
        if prefix:
            command = prefix + command

        self._send_lines([command])

    def send_message(self, recipient, message, action=False, notice=False):
        if action:
            self.send_action(recipient, message)
        elif notice:
            self.send_notice(recipient, message)
        else:
            self.send_command('PRIVMSG', [recipient + ' :' + message])

    def send_notice(self, recipient, message):
        self.send_command('NOTICE', [recipient + ' :' + message])

    def send_action(self, recipient, message):
        message = chr(1) + 'ACTION ' + message + chr(1)
        self.send_message(recipient, message)

    def quit(self, message='kaa', wait=1.0):
        self.send_command('QUIT', ':' + message)
        self.connection.close()
        time.sleep(wait)

########NEW FILE########
__FILENAME__ = logging
'''
    irctk.logger
    ------------

    Creates the logging object `logger`.
'''

from __future__ import absolute_import

import logging

FORMAT = ('%(asctime)s %(name)s - %(filename)s:%(lineno)d - %(levelname)s'
          '- %(message)s')


def create_logger():
    logger = logging.getLogger('irctk')
    logger.setLevel(logging.DEBUG)

    #fh = logging.FileHandler('kaa.log')
    #fh.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter(FORMAT, datefmt='%Y-%m-%d %H:%M:%S')

    ch.setFormatter(formatter)
    #fh.setFormatter(formatter)

    logger.addHandler(ch)
    #logger.addHandler(fh)

    return logger

########NEW FILE########
__FILENAME__ = plugins
# -*- coding: utf-8 -*-
'''
    irctk.plugins
    -------------

    Logic for handling plugin registration and processing.
'''

import inspect
import re

from irctk.threadpool import ThreadPool
from irctk.utils import cached_property


class Context(object):
    def __init__(self, line, args):
        self.line = line
        self.args = args


class PluginHandler(object):
    def __init__(self, bot):
        self.bot = bot
        self.config = self.bot.config
        self.logger = self.bot.logger
        self._reply = self.bot.reply

    @cached_property
    def thread_pool(self):
        thread_pool = \
                ThreadPool(self.config['MIN_WORKERS'], logger=self.logger)
        return thread_pool

    def _add_plugin(self, hook, func, command=True, event=False, regex=False):
        '''Allows plugins to be added in the scope of a function.'''
        plugin = {}

        plugin.setdefault('hook', hook)
        plugin.setdefault('funcs', [])

        self.logger.debug(str(plugin['funcs']))

        # add plugin functions
        for i, f in enumerate(plugin['funcs']):
            if f.name == func.name:
                plugin['funcs'][i] = func
            else:
                plugin['funcs'] += [func]

        if command:
            plugin_list = 'PLUGINS'

        if event:
            command = False  # don't process as a command and an event
            plugin_list = 'EVENTS'

        if regex:
            command = False
            plugin_list = 'REGEX'

        self.update_plugin(plugin, plugin_list)

    def _remove_plugin(self, hook, func, command=True, event=False,
            regex=False):
        '''Allows plugins to be removed in the scope of a function.'''
        if command:
            plugin_list = 'PLUGINS'

        if event:
            command = False  # don't process as a command and an event
            plugin_list = 'EVENTS'

        if regex:
            command = False
            plugin_list = 'REGEX'

        plugin_list = self.config[plugin_list]

        hook_found = lambda: hook == existing_plugin['hook']
        func_found = lambda: func in existing_plugin['funcs']

        for existing_plugin in plugin_list:
            if hook_found() and func_found():
                existing_plugin['funcs'].remove(func)

                if not existing_plugin['funcs']:
                    plugin_list.remove(existing_plugin)

    def _update_plugin(self, plugin, plugin_list):
        # contruct plugin list on bot config object if necessary
        if not self.config.get(plugin_list):
            self.config[plugin_list] = []

        # retrive the specified plugin list
        plugin_list = self.config[plugin_list]

        for i, existing_plugin in enumerate(plugin_list):
            if plugin['hook'] == existing_plugin['hook']:
                plugin_list[i]['funcs'] += plugin['funcs']

        def iter_list_hooks():
            for existing_plugin in plugin_list:
                yield existing_plugin['hook']

        if not plugin['hook'] in iter_list_hooks():
            plugin_list.append(plugin)

    def enqueue_plugin(self, plugin, hook, context, regex=False):
        search = None
        if regex:
            search = re.search(hook, context)
            plugin_args = plugin['context']['message']
            plugin['context']['regex_search'] = search
        elif not regex and (context == hook or context.startswith(hook + ' ')):
            plugin_args = \
                    plugin['context']['message'].split(hook, 1)[-1].strip()
        else:
            return

        plugin_context = Context(plugin['context'], plugin_args)
        task = (self.dequeue_plugin, plugin, plugin_context)
        self.thread_pool.enqueue_task(*task)

    def dequeue_plugin(self, plugin, plugin_context):
        '''This method assumes that a plugin and plugin context are
        passed to it as `plugin` and `plugin_context`. It is intended to be
        called as a plugin is being dequeued, i.e. from a thread pool as
        called by a worker thread thereof.

        The plugin and plugin context are checked against several conditions
        that will ultimately affect the formatting of the final message.

        if the plugin function does return a message, that message is
        formatted and sent back to the server via `cls.reply`.
        '''
        for func in plugin['funcs']:
            takes_args = inspect.getargspec(func).args

            action = False
            if plugin.get('action') == True:
                action = True

            notice = False
            if plugin.get('notice') == True:
                notice = True

            if takes_args:
                message = func(plugin_context)
            else:
                message = func()

            if message:
                self._reply(message, plugin_context.line, action, notice)

########NEW FILE########
__FILENAME__ = reloader
# -*- coding: utf-8 -*-
'''
    irctk.reloader
    --------------

    Logic for dyanmic reloading upon file changes.
'''

import os
import sys
import time
import threading
import imp
import inspect


class ReloadHandler(threading.Thread):
    def __init__(self, bot):
        threading.Thread.__init__(self)

        self.bot = bot
        self.plugin = self.bot.plugin
        self.logger = self.bot.logger

        self.daemon = True
        self.start()

    def _iter_module_files(self):
        for module in sys.modules.values():
            filename = getattr(module, '__file__', None)
            if filename:
                old = None
                while not os.path.isfile(filename):
                    old = filename
                    filename = os.path.dirname(filename)
                    if filename == old:
                        break
                else:
                    if filename[-4:] in ('.pyc', '.pyo'):
                        filename = filename[:-1]
                    yield filename

    def _reloader(self, wait=1.0):
        '''This reloader is based off of the Flask reloader which in turn is
        based off of the CherryPy reloader.
        '''

        mtimes = {}
        root_path = self.bot.root_path

        while True:
            fnames = []
            fnames.extend(self._iter_module_files())

            for filename in fnames:
                try:
                    mtime = os.stat(filename).st_mtime
                except OSError, e:
                    self.logger.error('Reloader error: ' + str(e))
                    continue

                old_time = mtimes.get(filename)

                mtimes[filename] = mtime

                if old_time is None:
                    continue
                elif mtime > old_time:
                    self.logger.info('Changes detected; reloading')

                    local_fnames = \
                        set([fname for fname in fnames if root_path in fname])

                    # WARNING: here be dragons

                    # get the ID of the main thread
                    all_threads = dict([(th.name, th.ident)
                                        for th in threading.enumerate()])

                    main_thread_frame = \
                            sys._current_frames()[all_threads['MainThread']]

                    # the main thread stack should contain the frame containing
                    # the filename of the module the bot instance was
                    # instantiated in
                    bot_fname = \
                            inspect.getouterframes(main_thread_frame)[-1][1]

                    local_fnames.add(bot_fname)

                    # make sure we load __init__ first
                    local_fnames = sorted(list(local_fnames))

                    # reload local modules
                    for fname in local_fnames:
                        f = os.path.split(fname)[-1]
                        f = os.path.splitext(f)[0]

                        try:
                            imp.load_source(f, fname)
                        except Exception, e:
                            self.logger.error('Reload failed: ' + str(e))
                            continue

            time.sleep(wait)

    def run(self):
        self._reloader()

########NEW FILE########
__FILENAME__ = threadpool
# -*- coding: utf-8 -*-
'''
    irctk.threadpool
    ----------------

    A thread pool to be used with plugin dispatching.
'''

import threading
import Queue
import time

DEFAULT_SLEEP = 0.01


class Worker(threading.Thread):
    '''Provides a worker object.

    This class provides a thread worker object which is used by the ThreadPool
    object to execute tasks, i.e. functions.
    '''

    def __init__(self, tasks, logger):
        threading.Thread.__init__(self)
        self.tasks = tasks
        self.logger = logger
        self.daemon = True
        self.start()

    def run(self):  # pragma: no cover
        while True:
            func, args, kwargs = self.tasks.get()
            try:
                # try to execute the function
                func(*args, **kwargs)
            except Exception, e:
                # if we fail, raise the exception and log it
                error = 'Error while executing function in worker: {0} - {1}'
                self.logger.error(error.format(func.__name__, e),
                                  exc_info=True)
            finally:
                # no matter what, we need to set the task to done
                self.tasks.task_done()


class ThreadPool(threading.Thread):
    '''This class provides an interface to a thread pool mechanism. Tasks may
    be enqueued via :class:`enqueue_task`. Worker threads are added via
    :class:`spawn_worker`.

    A given number, i.e. `min_workers`, of workers will be spawned upon
    instantiation.

    Inherits from `threading.Thread`.

    Example usage might go something like this::

        def square(n):
            return n * 2

        thread_pool = ThreadPool(3, logger=logger)
        thread_pool.enqueue_task(square, 2)  # enqueue a func with args

    This will enqueue the above function and call it. In practical usage the
    function should serve as some kind of callback.
    '''

    def __init__(self, min_workers, logger=None, wait=DEFAULT_SLEEP):
        threading.Thread.__init__(self)
        self.tasks = Queue.Queue()
        self.min_workers = min_workers
        self.workers = 0
        self.logger = logger
        self.wait = wait
        self.daemon = True
        self.start()

    def _spawn_worker(self):
        self.workers += 1
        Worker(self.tasks, self.logger)

    def enqueue_task(self, func, *args, **kwargs):
        self.tasks.put((func, args, kwargs))

    @property
    def too_few_workers(self):
        return self.workers < self.min_workers

    def run(self):
        while True:
            time.sleep(self.wait)

            if self.workers < self.min_workers:
                self._spawn_worker()

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
'''
    irctk.utils
    ---------

    Utility functions.
'''


class cached_property(object):
    def __init__(self, func):
        self._func = func
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__

    def __get__(self, obj, cls=None):
        if obj is None:
            return None
        result = obj.__dict__[self.__name__] = self._func(obj)
        return result

########NEW FILE########
__FILENAME__ = base
from irctk import Bot

import unittest


class IrcTkTestCase(unittest.TestCase):
    def setUp(self):
        self.bot = Bot()

########NEW FILE########
__FILENAME__ = test_bot
import unittest

from irctk.bot import Bot


class BotTestCase(unittest.TestCase):
    '''This test case is used to test the Bot class methods.'''

    def setUp(self):
        self.bot = Bot()
        self.assertNotEqual(self.bot._instance, None)
        self.assertTrue(self.bot.root_path)
        self.assertTrue(self.bot.logger)
        self.assertTrue(self.bot.default_config)
        self.assertTrue(self.bot.config)
        self.assertTrue(self.bot.plugin)

    def test_create_connection(self):
        self.bot._create_connection()
        self.assertTrue(self.bot.connection)
        self.assertTrue(self.bot.irc)

    def test_parse_input(self):
        pass

    def test_reloader_loop(self):
        pass

    def test_reloader(self):
        pass

    def test_command(self):
        @self.bot.command
        def foo():
            return 'bar'

        func = foo
        self.assertEqual(self.bot.config['PLUGINS'][0],
                         {'funcs': [func], 'hook': 'foo'})

    def test_event(self):
        @self.bot.event('JOIN')
        def foo():
            return 'bar'

        func = foo
        self.assertEqual(self.bot.config['EVENTS'][0],
                         {'funcs': [func], 'hook': 'JOIN'})

    def test_reply(self):
        pass

    def test_run(self):
        pass


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_config
from base import IrcTkTestCase
from mock import Mock


class ConfigTestCase(IrcTkTestCase):
    def setUp(self):
        IrcTkTestCase.setUp(self)
        obj = Mock()
        obj.SERVER = 'irc.voxinfinitus.net'
        obj.PORT = 6667
        obj.SSL = False
        obj.TIMEOUT = 300
        obj.NICK = 'hax0r'
        obj.REALNAME = 'A Python Bot'
        obj.CHANNELS = ['#voxinfinitus']
        self.obj = obj

    def test_from_pyfile(self):
        self.bot.config.from_pyfile('tests/data/settings.cfg')
        self.assertEqual(self.bot.config['SERVER'], 'irc.voxinfinitus.net')
        self.assertEqual(self.bot.config['PORT'], 6667)
        self.assertEqual(self.bot.config['SSL'], False)
        self.assertEqual(self.bot.config['NICK'], 'hax0r')
        self.assertEqual(self.bot.config['REALNAME'], 'A Python Bot')
        self.assertEqual(self.bot.config['CHANNELS'], ['#voxinfinitus'])

    def test_from_pyfile_bad_filepath(self):
        self.assertRaises(IOError,
                          self.bot.config.from_pyfile,
                          ('some/bad/path/settings.cfg'))

    def test_from_object(self):
        self.bot.config.from_object(self.obj)
        self.assertEqual(self.bot.config['SERVER'], 'irc.voxinfinitus.net')
        self.assertEqual(self.bot.config['PORT'], 6667)
        self.assertEqual(self.bot.config['SSL'], False)
        self.assertEqual(self.bot.config['NICK'], 'hax0r')
        self.assertEqual(self.bot.config['REALNAME'], 'A Python Bot')
        self.assertEqual(self.bot.config['CHANNELS'], ['#voxinfinitus'])

########NEW FILE########
__FILENAME__ = test_ircclient
import unittest
import Queue

from irctk.ircclient import TcpClient, IrcWrapper


class TcpClientTestCase(unittest.TestCase):
    def setUp(self):
        self.conn = TcpClient('127.0.0.1', '6697', True, logger=None)
        self.assertEqual(self.conn.host, '127.0.0.1')
        self.assertEqual(self.conn.port, '6697')
        self.assertTrue(self.conn.ssl)
        self.assertFalse(self.conn.shutdown)


class IrcWrapperTestCase(unittest.TestCase):
    def setUp(self):
        self.conn = Queue.Queue()
        self.conn.out = ''
        self.wrapper = IrcWrapper(self.conn,
                                  'test',
                                   'tester',
                                   None,
                                   ['#test'],
                                   None)
        self.assertTrue(self.wrapper.nick == 'test')
        self.assertTrue(self.wrapper.realname == 'tester')
        self.assertTrue(self.wrapper.channels == ['#test'])

    def test_register(self):
        self.wrapper._register()
        nick = 'NICK test\r\n'
        user = 'USER test 3 * tester\r\n'
        self.assertIn(nick, self.wrapper.out_buffer)
        self.assertIn(user, self.wrapper.out_buffer)
        self.assertEqual(nick,
                         self.wrapper.out_buffer.split('\r\n')[0] + '\r\n')
        self.assertEqual(user,
                         self.wrapper.out_buffer.split('\r\n')[1] + '\r\n')

    def test_send(self):
        pass

    def test_recv(self):
        pass

    def test_parse_line(self):
        line = 'PRIVMSG #testing :test message'
        prefix, command, args = self.wrapper._parse_line(line)
        self.assertEqual(prefix, '')
        self.assertEqual(command, 'PRIVMSG')
        self.assertEqual(args, ['#testing', 'test message'])

        line = \
            ':server.example.net NOTICE Auth :*** Looking up your hostname...'
        prefix, command, args = self.wrapper._parse_line(line)
        self.assertEqual(prefix, 'server.example.net')
        self.assertEqual(command, 'NOTICE')
        self.assertEqual(args, ['Auth', '*** Looking up your hostname...'])

    def test_send_line(self):
        line = 'test'
        self.wrapper._send_line(line)
        self.assertEqual('test\r\n', self.wrapper.out_buffer)

    def test_send_lines(self):
        lines = ['foo', 'bar', 'baz']
        expected_result = 'foo\r\nbar\r\nbaz\r\n'
        self.wrapper._send_lines(lines)
        self.assertEqual(expected_result, self.wrapper.out_buffer)

    def test_send_command(self):
        command = 'PRIVMSG'
        args = ['#test' + ' :' + 'test']
        expected_result = 'PRIVMSG #test :test\r\n'
        self.wrapper.send_command(command, args)
        self.assertEqual(expected_result, self.wrapper.out_buffer)

    def test_send_message(self):
        recipient = '#test'
        message = 'test'
        expected_result = 'PRIVMSG #test :test\r\n'
        self.wrapper.send_message(recipient, message)
        self.assertEqual(expected_result, self.wrapper.out_buffer)
        self.wrapper.out_buffer = ''

        recipient = '#test'
        message = 'dances'
        expected_result = 'PRIVMSG #test :\x01ACTION dances\x01\r\n'
        self.wrapper.send_message(recipient, message, action=True)
        self.assertEqual(expected_result, self.wrapper.out_buffer)
        self.wrapper.out_buffer = ''

        recipient = '#test'
        message = 'attention!'
        expected_result = 'NOTICE #test :attention!\r\n'
        self.wrapper.send_message(recipient, message, notice=True)
        self.assertEqual(expected_result, self.wrapper.out_buffer)

    def test_send_notice(self):
        pass

    def test_send_action(self):
        pass


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_plugins
import unittest

from irctk.plugins import Context, PluginHandler


class ContextTestCase(unittest.TestCase):
    def setUp(self):
        line = {'line': 'foo'}
        args = {'args': 'bar'}
        self.context = Context(line, args)

    def test_context(self):
        self.assertEqual(self.context.line, {'line': 'foo'})
        self.assertEqual(self.context.args, {'args': 'bar'})


class PluginHandlerTestCase(unittest.TestCase):
    def setUp(self):
        self.config = {'PLUGINS': [], 'EVENTS': [], 'MIN_WORKERS': 3}
        self.logger = None
        self.thread_pool = None
        self.plugins = \
                PluginHandler(self.config, self.logger, self.thread_pool)

    def flush_plugin_lists(self):
        self.config['PLUGINS'] = ['foo', 'bar']
        self.config['EVENTS'] = ['foo', 'bar']
        self.assertEqual(self.config['PLUGINS'], ['foo', 'bar'])
        self.assertEqual(self.config['EVENTS'], ['foo', 'bar'])

        self.plugins.flush_plugin_lists()
        self.assertEqual(self.config['PLUGINS'], [])
        self.assertEqual(self.config['EVENTS'], [])

    def test_add_plugin(self):
        self.plugins.add_plugin('hook', 'func1')
        self.plugins.add_plugin('hook', 'func2')
        self.assertEqual(self.config['PLUGINS'][0]['hook'], 'hook')
        self.assertEqual(self.config['PLUGINS'][0]['funcs'],
                         ['func1', 'func2'])

        self.plugins.add_plugin('hook', 'func', event=True)
        self.assertEqual(self.config['EVENTS'][0]['hook'], 'hook')
        self.assertEqual(self.config['EVENTS'][0]['funcs'], ['func'])

    def test_remove_plugin(self):
        self.plugins.add_plugin('hook', 'func1')
        self.plugins.add_plugin('hook', 'func2')
        self.plugins.remove_plugin('hook', 'func1')
        self.assertEqual(self.config['PLUGINS'][0]['hook'], 'hook')
        self.assertEqual(self.config['PLUGINS'][0]['funcs'], ['func2'])

        self.plugins.remove_plugin('hook', 'func2')
        self.assertEqual(self.config['PLUGINS'], [])

    def test_update_plugins(self):
        plugin = {'hook': 'foo', 'funcs': 'bar'}
        self.plugins.update_plugins(plugin, 'PLUGINS')
        self.assertEqual(self.config['PLUGINS'][0], plugin)

    def test_enqueue_plugin(self):
        pass

    def test_dequeue_plugin(self):
        pass


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_reloader
from base import IrcTkTestCase


class ReloaderTestCase(IrcTkTestCase):
    pass

########NEW FILE########
__FILENAME__ = test_threadpool
from irctk.threadpool import ThreadPool, Worker
from base import IrcTkTestCase


class ThreadPoolTestCase(IrcTkTestCase):
    def setUp(self):
        IrcTkTestCase.setUp(self)

        self.min_workers = 3
        self.tp = ThreadPool(self.min_workers)
        self.assertEqual(self.tp.min_workers, 3)
        self.assertEqual(self.tp.logger, None)
        self.assertEqual(self.tp.wait, 0.01)
        self.assertTrue(self.tp.daemon is not None)

        self.worker = Worker(self.tp.tasks, None)
        self.assertEqual(self.tp.tasks, self.worker.tasks)
        self.assertEqual(None, self.worker.logger)

    def foo(self, *args, **kwargs):
        return args or kwargs or 'bar'

    def bad_foo(self):
        raise Exception

    def test_enqueue_task(self):
        self.tp.enqueue_task('foo', 'bar')
        task = self.tp.tasks.get()
        self.assertEqual(('foo', ('bar',), {}), task)

        self.tp.enqueue_task('foo', 'bar', test=True)
        task = self.tp.tasks.get()
        self.assertEqual(('foo', ('bar',), {'test': True}), task)

    def test_spawn_worker(self):
        self.tp._spawn_worker()
        self.assertTrue(self.tp.too_few_workers)

        # spawn enough workers to surpass too_few_workers
        for i in range(3):
            self.tp._spawn_worker()
        self.assertFalse(self.tp.too_few_workers)

########NEW FILE########
