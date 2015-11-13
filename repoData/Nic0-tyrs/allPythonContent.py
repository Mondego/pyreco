__FILENAME__ = completion
# -*- coding:utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

class Completion (object):

    def __init__(self):
        self.nicks = []

    def add(self, nick):
        if nick not in self.nicks:
            self.nicks.append(nick)

    def __repr__(self):
        return str(self.nicks)

    def __len__(self):
        return len(self.nicks)

    def complete(self, word):
        nick = []
        for n in self.nicks:
            if word in n:
                nick.append(n)
        if len(nick) is 1:
            return nick[0]
        else:
            return None

    def text_complete(self, text):
        """Return the text to insert"""
        t = text.split(' ')
        last = t[-1]
        if last[0] is '@':
            nick = self.complete(last[1:])
            if nick:
                return nick[len(last)-1:]
        return None

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import curses
import logging
import message
import constant
import ConfigParser
import curses.ascii
import oauth2 as oauth
from utils import encode
try:
    from urlparse import parse_qsl
except ImportError:
    from cgi import parse_qsl

class Config(object):

    def __init__(self, args):
        self.init_config()
        self.home = os.environ['HOME']
        self.get_xdg_config()
        self.get_browser()
        # generate the config file
        if args.generate_config != None:
            self.generate_config_file(args.generate_config)
            sys.exit(0)

        self.set_path(args)
        self.check_for_default_config()
        self.conf = ConfigParser.RawConfigParser()
        self.conf.read(self.config_file)
        if not os.path.isfile(self.token_file):
            self.new_account()
        else:
            self.parse_token()

        self.parse_config()

    def init_config(self):
        self.token     = constant.token
        self.keys      = constant.key
        self.params    = constant.params
        self.filter    = constant.filter
        self.palette   = constant.palette

    def get_xdg_config(self):
        try:
            self.xdg_config = os.environ['XDG_CONFIG_HOME']
        except:
            self.xdg_config = self.home+'/.config'

    def get_browser(self):
        try:
            self.browser    = os.environ['BROWSER']
        except:
            self.browser    = ''

    def check_for_default_config(self):
        default_dir = '/tyrs'
        default_file = '/tyrs/tyrs.cfg'
        if not os.path.isfile(self.xdg_config + default_file):
            if not os.path.exists(self.xdg_config + default_dir):
                try:
                    os.makedirs(self.xdg_config + default_dir)
                except:
                    print encode(_('Couldn\'t create the directory in %s/tyrs')) % self.xdg_config
            self.generate_config_file(self.xdg_config + default_file)


    def generate_config_file(self, config_file):
        conf = ConfigParser.RawConfigParser()
        conf.read(config_file)

        # COLOR
        conf.add_section('colors')
        for c in self.palette:
            conf.set('colors', c[0], c[1])
        # KEYS
        conf.add_section('keys')
        for k in self.keys:
            conf.set('keys', k, self.keys[k])
        # PARAMS
        conf.add_section('params')
        for p in self.params:
            if self.params[p] == True:
                value = 1
            elif self.params[p] == False:
                value = 0
            elif self.params[p] == None:
                continue
            else:
                value = self.params[p]

            conf.set('params', p, value)

        with open(config_file, 'wb') as config:
            conf.write(config)

        print encode(_('Generating configuration file in %s')) % config_file

    def set_path(self, args):
        # Default config path set
        if self.xdg_config != '':
            self.tyrs_path = self.xdg_config + '/tyrs/'
        else:
            self.tyrs_path = self.home + '/.config/tyrs/'
        # Setup the token file
        self.token_file = self.tyrs_path + 'tyrs.tok'
        if args.account != None:
            self.token_file += '.' + args.account
        # Setup the config file
        self.config_file = self.tyrs_path + 'tyrs.cfg'
        if args.config != None:
            self.config_file += '.' + args.config

    def new_account(self):

        choice = self.ask_service()
        if choice == '2':
            self.ask_root_url()

        self.authorization()
        self.createTokenFile()

    def ask_service(self):
        message.print_ask_service(self.token_file)
        choice = raw_input(encode(_('Your choice? > ')))

        if choice == '1':
            self.service = 'twitter'
        elif choice == '2':
            self.service = 'identica'
        else:
            sys.exit(1)
        return choice

    def ask_root_url(self):
        message.print_ask_root_url()
        url = raw_input(encode(_('Your choice? > ')))
        if url == '':
            self.base_url = 'https://identi.ca/api'
        else:
            self.base_url = url

    def parse_token(self):
        token = ConfigParser.RawConfigParser()
        token.read(self.token_file)
        if token.has_option('token', 'service'):
            self.service = token.get('token', 'service')
        else:
            self.service = 'twitter'

        if token.has_option('token', 'base_url'):
            self.base_url = token.get('token', 'base_url')

        self.oauth_token = token.get('token', 'oauth_token')
        self.oauth_token_secret = token.get('token', 'oauth_token_secret')

    def parse_config(self):
        self.parse_color()
        self.parse_keys()
        self.parse_params()
        self.parse_filter()
        self.init_logger()

    def parse_color(self):
        for i, c in enumerate(self.palette):
            if self.conf.has_option('colors', c[0]):
                self.palette[i][1] = (self.conf.get('colors', c[0]))

    def parse_keys(self):
        for key in self.keys:
            if self.conf.has_option('keys', key):
                self.keys[key] = self.conf.get('keys', key)
            else:
                self.keys[key] = self.keys[key]

    def char_value(self, ch):
        if ch[0] == '^':
            i = 0
            while i <= 31:
                if curses.ascii.unctrl(i) == ch.upper():
                    return i
                i +=1
        return ord(ch)

    def parse_params(self):

        # refresh (in minutes)
        if self.conf.has_option('params', 'refresh'):
            self.params['refresh']     = int(self.conf.get('params', 'refresh'))

        if self.conf.has_option('params', 'box_position'):
            self.params['refresh']     = int(self.conf.get('params', 'box_position'))

        # tweet_border
        if self.conf.has_option('params', 'tweet_border'):
            self.params['tweet_border'] = int(self.conf.get('params', 'tweet_border'))

        # Relative_time
        if self.conf.has_option('params', 'relative_time'):
            self.params['relative_time'] = int(self.conf.get('params', 'relative_time'))

        # Retweet_By
        if self.conf.has_option('params', 'retweet_by'):
            self.params['retweet_by'] = int(self.conf.get('params', 'retweet_by'))

        # Openurl_command
        if self.conf.has_option('params', 'openurl_command'):
            self.params['openurl_command'] = self.conf.get('params',
                'openurl_command')
        elif self.browser != '':
            self.params['openurl_command'] = self.browser + ' %s'

        if self.conf.has_option('params', 'open_image_command'):
            self.params['open_image_command'] = self.conf.get('params',
                'open_image_command')

        # Transparency
        if self.conf.has_option('params', 'transparency'):
            if int(self.conf.get('params', 'transparency')) == 0:
                self.params['transparency'] = False
        # Compress display
        if self.conf.has_option('params', 'compact'):
            if int(self.conf.get('params', 'compact')) == 1:
                self.params['compact'] = True
        # Help bar
        if self.conf.has_option('params', 'help'):
            if int(self.conf.get('params', 'help')) == 0:
                self.params['help'] = False

        if self.conf.has_option('params', 'margin'):
            self.params['margin'] = int(self.conf.get('params', 'margin'))

        if self.conf.has_option('params', 'padding'):
            self.params['padding'] = int(self.conf.get('params', 'padding'))

        if self.conf.has_option('params', 'old_skool_border'):
            if int(self.conf.get('params', 'old_skool_border')) == 1:
                self.params['old_skool_border'] = True

        if self.conf.has_option('params', 'consumer_key'):
            self.token['identica']['consumer_key'] = self.conf.get('params', 'consumer_key')

        if self.conf.has_option('params', 'consumer_secret'):
            self.token['identica']['consumer_secret'] = self.conf.get('params', 'consumer_secret')

        if self.conf.has_option('params', 'logging_level'):
            self.params['logging_level'] = self.conf.get('params', 'logging_level')

        if self.conf.has_option('params', 'url_shorter'):
            shortener = self.params['url_shorter'] = self.conf.get('params', 'url_shorter')
            if shortener == 'googl':
                self.check_google_tokens()

        if self.conf.has_option('params', 'header_template'):
            self.params['header_template'] = self.conf.get('params', 'header_template')

        if self.conf.has_option('params', 'proxy'):
            self.params['proxy'] = self.conf.get('params', 'proxy')

        if self.conf.has_option('params', 'beep'):
            self.params['beep'] = self.conf.getboolean('params', 'beep')

    def check_google_tokens(self):
        try:
            from shorter.googl import GooglUrlShorter
        except ImportError:
            print 'please install google-api-python-client and python-gflags'
            sys.exit(1)
        GooglUrlShorter().register_token()


    def parse_filter(self):

        if self.conf.has_option('filter', 'activate'):
            if int(self.conf.get('filter', 'activate')) == 1:
                self.filter['activate'] = True

        if self.conf.has_option('filter', 'myself'):
            if int(self.conf.get('filter', 'myself')) == 1:
                self.filter['myself'] = True

        if self.conf.has_option('filter', 'behavior'):
            self.filter['behavior'] = self.conf.get('filter', 'behavior')

        if self.conf.has_option('filter', 'except'):
            self.filter['except'] = self.conf.get('filter', 'except').split(' ')

    def init_logger(self):
        log_file = self.xdg_config + '/tyrs/tyrs.log'
        lvl = self.init_logger_level()

        logging.basicConfig(
            filename=log_file,
            level=lvl,
            format='%(asctime)s %(levelname)s - %(message)s',
            datefmt='%d/%m/%Y %H:%M:%S',
            )
        logging.info('Tyrs starting...')

    def init_logger_level(self):
        lvl = int(self.params['logging_level'])
        if lvl == 1:
            return logging.DEBUG
        elif lvl == 2:
            return logging.INFO
        elif lvl == 3:
            return logging.WARNING
        elif lvl == 4:
            return logging.ERROR

    def authorization(self):
        ''' This function from python-twitter developers '''
        # Copyright 2007 The Python-Twitter Developers
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

        if self.service == 'twitter':
            base_url = 'https://api.twitter.com'
            self.base_url = base_url
        else:
            base_url = self.base_url

        print 'base_url:{0}'.format(base_url)


        REQUEST_TOKEN_URL          = base_url + '/oauth/request_token'
        if self.service == 'identica':
            if base_url != 'https://identi.ca/api':
                self.parse_config()
            REQUEST_TOKEN_URL += '?oauth_callback=oob'

        ACCESS_TOKEN_URL           = base_url + '/oauth/access_token'
        AUTHORIZATION_URL          = base_url + '/oauth/authorize'
        consumer_key               = self.token[self.service]['consumer_key']
        consumer_secret            = self.token[self.service]['consumer_secret']
        signature_method_hmac_sha1 = oauth.SignatureMethod_HMAC_SHA1()
        oauth_consumer             = oauth.Consumer(key=consumer_key, secret=consumer_secret)
        oauth_client               = oauth.Client(oauth_consumer)

        print encode(_('Requesting temp token from ')) + self.service.capitalize()

        resp, content = oauth_client.request(REQUEST_TOKEN_URL, 'GET')

        if resp['status'] != '200':
            print encode(_('Invalid respond from ')) +self.service.capitalize() + encode(_(' requesting temp token: %s')) % str(resp['status'])
        else:
            request_token = dict(parse_qsl(content))

            print ''
            print encode(_('Please visit the following page to retrieve pin code needed'))
            print encode(_('to obtain an Authentication Token:'))
            print ''
            print '%s?oauth_token=%s' % (AUTHORIZATION_URL, request_token['oauth_token'])
            print ''

            pincode = raw_input('Pin code? ')

            token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
            token.set_verifier(pincode)

            print ''
            print encode(_('Generating and signing request for an access token'))
            print ''

            oauth_client  = oauth.Client(oauth_consumer, token)
            resp, content = oauth_client.request(ACCESS_TOKEN_URL, method='POST', body='oauth_verifier=%s' % pincode)
            access_token  = dict(parse_qsl(content))

            if resp['status'] != '200':
                print 'response:{0}'.format(resp['status'])
                print encode(_('Request for access token failed: %s')) % resp['status']
                print access_token
                sys.exit()
            else:
                self.oauth_token = access_token['oauth_token']
                self.oauth_token_secret = access_token['oauth_token_secret']


    def createTokenFile(self):

        if not os.path.isdir(self.tyrs_path):
            try:
                os.mkdir(self.tyrs_path)
            except:
                print encode(_('Error creating directory .config/tyrs'))

        conf = ConfigParser.RawConfigParser()
        conf.add_section('token')
        conf.set('token', 'service', self.service)
        conf.set('token', 'base_url', self.base_url)
        conf.set('token', 'oauth_token', self.oauth_token)
        conf.set('token', 'oauth_token_secret', self.oauth_token_secret)

        with open(self.token_file, 'wb') as tokens:
            conf.write(tokens)

        print encode(_('your account has been saved'))

    def load_last_read(self):

        try:
            conf = ConfigParser.RawConfigParser()
            conf.read(self.token_file)
            return conf.get('token', 'last_read')
        except:
            return False

    def save_last_read(self, last_read):

        conf = ConfigParser.RawConfigParser()
        conf.read(self.token_file)
        conf.set('token', 'last_read', last_read)

        with open(self.token_file, 'wb') as tokens:
            conf.write(tokens)

########NEW FILE########
__FILENAME__ = constant
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

palette = [
    ['body','default', '', 'standout'],
    ['focus','dark red', '', 'standout'],
    ['header','light blue', ''],
    ['line', 'dark blue', ''],
    ['info_msg', 'dark green', ''],
    ['warn_msg', 'dark red', ''],
    ['current_tab', 'light blue', ''],
    ['other_tab', 'dark blue', ''],
    ['read', 'dark blue', ''],
    ['unread', 'dark red', ''],
    ['hashtag', 'dark green', ''],
    ['attag', 'brown', ''],
    ['highlight', 'dark red', ''],
    ['highlight_nick', 'light red', ''],
    ['help_bar', 'yellow', 'dark blue'],
    ['help_key', 'dark red', ''],
    ]

key = {
    'up':                'k',
    'down':              'j',
    'left':              'J',
    'right':             'K',
    'quit':              'q',
    'tweet':             't',
    'clear':             'c',
    'retweet':           'r',
    'retweet_and_edit':  'R',
    'delete':            'C',
    'update':            'u',
    'follow_selected':   'f',
    'unfollow_selected': 'l',
    'follow':            'F',
    'unfollow':          'L',
    'openurl':           'o',
    'open_image':        'ctrl i',
    'home':              'h',
    'mentions':          'm',
    'reply':             'M',
    'back_on_top':       'g',
    'back_on_bottom':    'G',
    'getDM':             'd',
    'sendDM':            'D',
    'search':            's',
    'search_user':       'U',
    'search_current_user': 'ctrl f',
    'search_myself':     'ctrl u',
    'redraw':            'ctrl l',
    'fav':               'b',
    'get_fav':           'B',
    'delete_fav':        'ctrl b',
    'thread':            'T',
    'waterline':         'w',
    'do_list':           'a',
}

params = {
    'refresh':              2,
    'tweet_border':         1,
    'relative_time':        1,
    'retweet_by':           1,
    'margin':               1,
    'padding':              2,
    'openurl_command':      'firefox %s',
    'open_image_command':   'feh %s',
    'transparency':         True,
    'activities':           True,
    'compact':              False,
    'help':                 True,
    'old_skool_border':     False,
    'box_position':         1,
    'url_shorter':          'ur1ca',
    'logging_level':        3,
    'header_template':      ' {nick}{retweeted}{retweeter} - {time}{reply} {retweet_count} ',
    'proxy':                None,
    'beep':                 False,
}

filter = {
    'activate':         False,
    'myself':           False,
    'behavior':         'all',
    'except':           [],
}

token = {
    'twitter': {
        'consumer_key':     'Eq9KLjwH9sJNcpF4OOYNw',
        'consumer_secret':  '3JoHyvBp3L6hhJo4BJr6H5aFxLhSlR70ZYnM8jBCQ'
    },
    'identica': {
        'consumer_key':     '6b2cf8346a141d530739f72b977b7078',
        'consumer_secret':  '31b342b348502345d4a343a331e00edb'
    }
}

########NEW FILE########
__FILENAME__ = container
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

class Container(object):
    '''
    Contain main classes that we need thought all the programm
    such as conf, api and ui
    '''
    _container = {}

    def __setitem__(self, key, value):
        self._container[key] = value

    def __getitem__(self, key):
        return self._container[key]

    def add(self, name, dependency):
        self[name] = dependency

########NEW FILE########
__FILENAME__ = editor
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import tyrs
import urwid
from utils import encode, get_urls
try:
    from shorter.ur1ca import Ur1caUrlShorter
    from shorter.bitly import BitLyUrlShorter
    from shorter.msudpl import MsudplUrlShorter
    from shorter.custom import CustomUrlShorter
except ImportError:
    pass

try:
    from shorter.googl import GooglUrlShorter
except ImportError:
    pass

class TweetEditor(urwid.WidgetWrap):

    __metaclass__ = urwid.signals.MetaSignals
    signals = ['done']

    def __init__(self, init_content='', prompt=''):
        if init_content:
            init_content += ' '
        self.editor = Editor(u'%s (twice enter key to validate or esc) \n>> ' % prompt, init_content)
        self.counter = urwid.Text('0')
        self.editor.completion = tyrs.container['completion']
        w = urwid.Columns([ ('fixed', 4, self.counter), self.editor])
        urwid.connect_signal(self.editor, 'done', self.send_sigterm)
        urwid.connect_signal(self.editor, 'change', self.update_count)

        self.__super.__init__(w)

    def send_sigterm(self, content):
        urwid.emit_signal(self, 'done', content)

    def update_count(self, edit, new_edit_text):
        self.counter.set_text(str(len(new_edit_text)))

class Editor(urwid.Edit):

    __metaclass__ = urwid.signals.MetaSignals
    signals = ['done']
    last_key = ''

    def keypress(self, size, key):
        if key == 'enter' and self.last_key == 'enter':
            urwid.emit_signal(self, 'done', self.get_edit_text())
            return
        if key == 'esc':
            urwid.emit_signal(self, 'done', None)
        if key == 'tab':
            insert_text = self.completion.text_complete(self.get_edit_text())
            if insert_text:
                self.insert_text(insert_text)
            
        self.last_key = key
        urwid.Edit.keypress(self, size, key)

#FIXME old editor, need to be done for url-shorter

    #def shorter_url(self):
        #self._set_service()
        #long_urls = get_urls(self.content)
        #for long_url in long_urls:
            #short_url = self.shorter.do_shorter(long_url)
            #try:
                #self.content = self.content.replace(long_url, short_url)
            #except UnicodeDecodeError:
                #pass

    #def _set_service(self):
        #service = self.conf.params['url_shorter']
        #if service == 'bitly':
            #self.shorter = BitLyUrlShorter() 
        #elif service == 'googl':
            #self.shorter = GooglUrlShorter()
        #elif service == 'msudpl':
            #self.shorter = MsudplUrlShorter()
        #elif service == 'custom':
            #self.shorter = CustomUrlShorter()
        #else:
            #self.shorter = Ur1caUrlShorter()

########NEW FILE########
__FILENAME__ = filter
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
import tyrs
from utils import get_urls

class FilterStatus(object):

    def __init__(self):
        self.conf = tyrs.container['conf']

    def filter_status(self, status):
        self.setup_exception()
        try:
            if self.conf.filter['activate']:
                self.status = status
                if self.filter_without_url():
                    if self.filter_without_myself():
                        if self.filter_exception():
                            return True
            return False
        except:
            return False

    def filter_without_url(self):
        urls = get_urls(self.status.text)
        if len(urls) == 0:
            return True
        return False

    def filter_without_myself(self):
        if self.conf.filter['myself']:
            return True
        if self.conf.my_nick in self.status.text:
            return False
        else:
            return True


    def filter_exception(self):
        nick = self.status.user.screen_name
        if self.conf.filter['behavior'] == 'all':
            if not nick in self.exception:
                return True
        else:
            if nick in self.exception:
                return True
        return False

    def setup_exception(self):
        self.exception = self.conf.filter['except']
        self.exception.append(self.conf.my_nick)

########NEW FILE########
__FILENAME__ = help
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import tyrs
import urwid

def help_bar():
    conf = tyrs.container['conf']
    if conf.params['help']:
        return urwid.AttrWrap(urwid.Columns([
            urwid.Text(['help:', ('help_key', ' ? ')]),
            urwid.Text(['up:', ('help_key', ' %s ' % conf.keys['up'])]),
            urwid.Text(['down:', ('help_key', ' %s ' % conf.keys['down'])]),
            urwid.Text(['tweet:', ('help_key', ' %s ' % conf.keys['tweet'])]),
            ('fixed', 12, urwid.Text(['retweet:', ('help_key', ' %s ' %
                                                   conf.keys['retweet'])])),
            urwid.Text(['reply:', ('help_key', ' %s ' % conf.keys['reply'])]),
            urwid.Text(['quit:', ('help_key', ' %s ' % conf.keys['quit'])]),
        ]), 'help_bar')
    else:
        return None

class Help(urwid.WidgetWrap):

    col = [20, 7]

    def __init__ (self):
        self.interface = tyrs.container['interface']
        self.conf = tyrs.container['conf']
        self.items = []
        w = urwid.AttrWrap(self.display_help_screen(), 'body')
        self.__super.__init__(w)

    def display_help_screen (self):

        self.display_header()
        # Navigation
        self.display_division(_('Navigation'))
        self.display_help_item('up', _('Go up one tweet'))
        self.display_help_item('down', _('Go down one tweet'))
        self.display_help_item('back_on_top', _('Go to top of screen'))
        self.display_help_item('back_on_bottom', _('Go to bottom of screen'))
        # Timelines
        self.display_division(_('Timelines'))
        self.display_help_item('left', _('Go left on the timeline\'s bar'))
        self.display_help_item('right', _('Go right on the timeline\'s bar'))
        self.display_help_item('update', _('Refresh current timeline'))
        self.display_help_item('clear', _('Clear all but last tweet in timeline'))
        self.display_help_item('home', _('Go to home timeline'))
        self.display_help_item('mentions', _('Go to mentions timeline'))
        self.display_help_item('getDM', _('Go to direct message timeline'))
        self.display_help_item('search', _('Search for term and show resulting timeline'))
        self.display_help_item('search_user', _('Show somebody\'s public timeline'))
        self.display_help_item('search_myself', _('Show your public timeline'))
        # Tweets
        self.display_division(_('Tweets'))
        self.display_help_item('tweet', _('Send a tweet'))
        self.display_help_item('retweet', _('Retweet selected tweet'))
        self.display_help_item('retweet_and_edit', _('Retweet selected tweet, but edit first'))
        self.display_help_item('reply', _('Reply to selected tweet'))
        self.display_help_item('sendDM', _('Send direct message'))
        self.display_help_item('delete', _('Delete selected tweet (must be yours)'))
        # Follow/Unfollow
        self.display_division('Follow/Unfollow')
        self.display_help_item('follow_selected', _('Follow selected twitter'))
        self.display_help_item('unfollow_selected', _('Unfollow selected twitter'))
        self.display_help_item('follow', _('Follow a twitter'))
        self.display_help_item('unfollow', _('Unfollow a twitter'))

        # Favorite
        self.display_division('Favorite')
        self.display_help_item('fav', _('Bookmark selected tweet'))
        self.display_help_item('get_fav', _('Go to favorite timeline'))
        self.display_help_item('delete_fav', _('Delete an favorite tweet'))

        # Others
        self.display_division(_('Others'))
        self.display_help_item('quit', _('Leave Tyrs'))
        self.display_help_item('waterline', _('Move the waterline to the top'))
        self.display_help_item('openurl', _('Open URL in browser'))
        self.display_help_item('open_image', _('Open image in browser'))
        self.display_help_item('redraw', _('Redraw the screen'))
        self.display_help_item('thread', _('Open thread seltected'))
        return urwid.ListBox(urwid.SimpleListWalker(self.items))


    def display_division(self, title):
        self.items.append(urwid.Divider(' '))
        self.items.append(urwid.Padding(urwid.AttrWrap(urwid.Text(title), 'focus'), left=4))
        self.items.append(urwid.Divider(' '))

    def display_header(self):
        self.items.append( urwid.Columns([
            ('fixed', self.col[0], urwid.Text('  Name')),
            ('fixed', self.col[1], urwid.Text('Key')),
            urwid.Text('Description')
        ]))

    def display_help_item(self, key, description):
        self.items.append( urwid.Columns([
            ('fixed', self.col[0], urwid.Text('  '+key)),
            ('fixed', self.col[1], urwid.Text(self.conf.keys[key])),
            urwid.Text(description)
        ]))

########NEW FILE########
__FILENAME__ = interface
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
import os
import tyrs
import urwid
import curses
import logging
from user import User
from keys import Keys
from help import help_bar, Help
from utils import get_urls
from constant import palette
from editor import TweetEditor
from update import UpdateThread
from widget import HeaderWidget
from completion import Completion
import urwid.html_fragment

class Interface(object):

    def __init__(self):
        self.api        = tyrs.container['api']
        self.conf       = tyrs.container['conf']
        self.timelines  = tyrs.container['timelines']
        self.buffers    = tyrs.container['buffers']
        self.completion = tyrs.container['completion']
        self.help = False
        tyrs.container.add('interface', self)
        self.update_last_read_home()
        self.api.set_interface()
        self.regex_retweet     = re.compile('^RT @\w+:')
        self.stoped = False
        self.buffer           = 'home'
        self.first_update()
        self.main_loop()

    def main_loop (self):

        self.header = HeaderWidget()
        foot = help_bar()
        self.listbox = self.select_current_timeline().timeline
        self.main_frame = urwid.Frame(urwid.AttrWrap(self.listbox, 'body'), header=self.header, footer=foot)
        key_handle = Keys()
        urwid.connect_signal(key_handle, 'help_done', self.help_done)
        self.loop = urwid.MainLoop(self.main_frame, palette, unhandled_input=key_handle.keystroke)
        update = UpdateThread()
        update.start()
        self.loop.run()
        update._Thread__stop()
        update.stop()

    def reply(self):
        self.status = self.current_status()
        if hasattr(self.status, 'user'):
            nick = self.status.user.screen_name
        #FIXME: 
        #else:
            #self.direct_message()
        data = '@' + nick
        self.edit_status('reply', data, 'Tweet ')

    def edit_status(self, action, content='', prompt=''):
        self.foot = TweetEditor(content, prompt)
        self.main_frame.set_footer(self.foot)
        self.main_frame.set_focus('footer')
        if action == 'tweet':
            urwid.connect_signal(self.foot, 'done', self.api.tweet_done)
        elif action == 'reply':
            urwid.connect_signal(self.foot, 'done', self.api.reply_done)
        elif action == 'follow':
            urwid.connect_signal(self.foot, 'done', self.api.follow_done)
        elif action == 'unfollow':
            urwid.connect_signal(self.foot, 'done', self.api.unfollow_done)
        elif action == 'search':
            urwid.connect_signal(self.foot, 'done', self.api.search_done)
        elif action == 'public':
            urwid.connect_signal(self.foot, 'done', self.api.public_done)
        elif action == 'list':
            urwid.connect_signal(self.foot, 'done', self.api.list_done)

    def first_update(self):
        updates = ['user_retweet', 'favorite']
        for buff in updates:
            self.api.update_timeline(buff)
            self.timelines[buff].reset()
            self.timelines[buff].all_read()

    def display_timeline (self):
        if not self.help:
            timeline = self.select_current_timeline()
            self.listbox = timeline.timeline
            self.main_frame.set_body(urwid.AttrWrap(self.listbox, 'body'))
            if self.buffer == 'home':
                self.conf.save_last_read(timeline.last_read)
            self.display_flash_message()

    def lazzy_load(self):
        timeline = self.select_current_timeline()
        focus = timeline.timeline.get_focus()[1]
        if timeline.cleared != False:
            return
        if focus is len(timeline.walker)-1:
            timeline.page += 1
            statuses = self.api.retreive_statuses(self.buffer, timeline.page)
            timeline.append_old_statuses(statuses)
            self.display_timeline()

    def redraw_screen (self):
        self.loop.draw_screen()

    def display_flash_message(self):
        if hasattr(self, 'main_frame'):
            header = HeaderWidget()
            self.main_frame.set_header(header)
            self.redraw_screen()
            self.api.flash_message.reset()

    def erase_flash_message(self):
        self.api.flash_message.reset()
        self.display_flash_message()

    def change_buffer(self, buffer):
        self.buffer = buffer
        self.timelines[buffer].reset()

    def navigate_buffer(self, nav):
        '''Navigate with the arrow, mean nav should be -1 or +1'''
        index = self.buffers.index(self.buffer)
        new_index = index + nav
        if new_index >= 0 and new_index < len(self.buffers):
            self.change_buffer(self.buffers[new_index])

    def check_for_last_read(self, id):
        if self.last_read_home == str(id):
            return True
        return False

    def select_current_timeline(self):
        return self.timelines[self.buffer]

    def clear_statuses(self):
        timeline = self.select_current_timeline()
        timeline.count_statuses()
        timeline.reset()
        timeline.clear()

    def current_status(self):
        focus = self.listbox.get_focus()[0]
        return focus.status

    def display_help(self):
        self.help = True
        h = Help()
        self.main_frame.set_body(h)

    def help_done(self):
        self.help = False
        self.display_timeline()

    def back_on_bottom(self):
        timeline = self.select_current_timeline()
        self.listbox.set_focus(timeline.status_count())

    def back_on_top(self):
        self.listbox.set_focus(0)

    def openurl(self):
        urls = get_urls(self.current_status().text)
        for url in urls:
            try:
                os.system(self.conf.params['openurl_command'] % url + '> /dev/null 2>&1')
            except:
                logging.error('openurl error')

    def update_last_read_home(self):
        self.last_read_home = self.conf.load_last_read()

    def current_user_info(self):
        User(self.current_status().user)

    def go_up(self):
        timeline = self.select_current_timeline()
        timeline.go_up()

    def go_down(self):
        timeline = self.select_current_timeline()
        timeline.go_down()

    def beep(self):
        return curses.beep()

########NEW FILE########
__FILENAME__ = keys
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import tyrs
import urwid
from help import Help
from utils import open_image

class Keys(object):

    __metaclass__ = urwid.signals.MetaSignals
    signals = ['help_done']
    '''
    This class handle the main keysbinding, as the main method contain every
    keybinding, every case match a key to a method call, there is no logical
    here
    '''
    def __init__(self):
        self.conf       = tyrs.container['conf']
        self.interface  = tyrs.container['interface']
        self.api        = tyrs.container['api']

    def keystroke (self, ch):
        if not self.interface.help:
# Quit
            if ch == self.conf.keys['quit']:
                self.interface.stoped = True
                raise urwid.ExitMainLoop()
# Right
            elif ch == self.conf.keys['right'] or ch == 'right':
                self.interface.navigate_buffer(+1)
# left
            elif ch == self.conf.keys['left'] or ch == 'left':
                self.interface.navigate_buffer(-1)
            elif ch == self.conf.keys['up']:
                self.interface.go_up()
            elif ch == self.conf.keys['down']:
                self.interface.go_down()
# Update
            elif ch == self.conf.keys['update']:
                self.api.update_timeline(self.interface.buffer)
# Tweet
            elif ch == self.conf.keys['tweet']:
                self.interface.edit_status('tweet', prompt='Tweet ')
# Reply
            elif ch == self.conf.keys['reply']:
                self.interface.reply()
# Retweet
            elif ch == self.conf.keys['retweet']:
                self.api.retweet()
# Retweet and Edit
            elif ch == self.conf.keys['retweet_and_edit']:
                self.api.retweet_and_edit()
# Delete
            elif ch == self.conf.keys['delete']:
                self.api.destroy()
# Mention timeline
            elif ch == self.conf.keys['mentions']:
                self.interface.change_buffer('mentions')
# Home Timeline
            elif ch == self.conf.keys['home']:
                self.interface.change_buffer('home')
# Direct Message Timeline
            elif ch == self.conf.keys['getDM']:
                self.interface.change_buffer('direct')
# Clear statuses
            elif ch == self.conf.keys['clear']:
                self.interface.clear_statuses()
# Follow Selected
            elif ch == self.conf.keys['follow_selected']:
                self.api.follow_selected()
# Unfollow Selected
            elif ch == self.conf.keys['unfollow_selected']:
                self.api.unfollow_selected()
# Follow
            elif ch == self.conf.keys['follow']:
                self.interface.edit_status('follow', prompt='Follow')
# Unfollow
            elif ch == self.conf.keys['unfollow']:
                self.interface.edit_status('unfollow', prompt='Unfollow ')
# Open URL
            elif ch == self.conf.keys['openurl']:
                self.interface.openurl()
# Search
            elif ch == self.conf.keys['search']:
                self.interface.edit_status('search', prompt='Search ')
# Search User
            elif ch == self.conf.keys['search_user']:
                self.interface.edit_status('public', prompt='Nick ')
# Search Myself
            elif ch == self.conf.keys['search_myself']:
                self.api.my_public_timeline()
# Search Current User
            elif ch == self.conf.keys['search_current_user']:
                self.api.find_current_public_timeline()
# Send Direct Message
#FIXME
            #elif ch == self.conf.keys['sendDM']:
                #self.api.direct_message()
# Create favorite
            elif ch == self.conf.keys['fav']:
                self.api.set_favorite()
# Get favorite
            elif ch == self.conf.keys['get_fav']:
                self.api.get_favorites()
# Destroy favorite
            elif ch == self.conf.keys['delete_fav']:
                self.api.destroy_favorite()
# Thread
            elif ch == self.conf.keys['thread']:
                self.api.get_thread()
# Open image
            elif ch == self.conf.keys['open_image']:
                open_image(self.interface.current_status().user)
# User info
            elif ch == 'i':
                self.interface.current_user_info()
# Waterline
            elif ch == self.conf.keys['waterline']:
                self.interface.update_last_read_home()
# Back on Top
            elif ch == self.conf.keys['back_on_top']:
                self.interface.back_on_top()
# Back on Bottom
            elif ch == self.conf.keys['back_on_bottom']:
                self.interface.back_on_bottom()
# Get list
            elif ch == self.conf.keys['do_list']:
                self.interface.edit_status('list', prompt='List ')
# Help
            elif ch == '?':
                self.interface.display_help()

            self.interface.display_timeline()
        
        else:
            if ch in ('q', 'Q', 'esc'):
                urwid.emit_signal(self, 'help_done')


########NEW FILE########
__FILENAME__ = message
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from utils import encode

class FlashMessage(object):

    message = {
        'update': [
            _('Updating timeline...'),
            _('Couldn\'t retrieve tweets')
            ],
        'tweet': [
            _('Your tweet was sent'),
            _('Couldn\'t send tweet'),
            ],
        'retweet': [
            _('Your retweet was sent'),
            _('Couldn\'t send retweet'),
            ],
        'destroy': [
            _('You have deleted the tweet'),
            _('Couldn\'t delete tweet'),
            ],
        'favorite': [
            _('The tweet was added to favorites list'),
            _('Couldn\'t add tweet to favorites list'),
            ],
        'favorite_del': [
            _('Tweet was removed from favorites list'),
            _('Couldn\'t delete tweet on favorites list'),
            ],
        'direct': [
            _('Direct message was sent'),
            _('Couldn\'t send direct message'),
            ],
        'follow': [
            _('You are now following %s'),
            _('Couldn\'t follow %s')
            ],
        'unfollow': [
            _('You are not following %s anymore'),
            _('Couldn\'t stop following %s')
            ],
        'search': [
            _('Search results for %s'),
            _('Couldn\'t search for %s'),
            ],
        'list': [
            _('List results for %s'),
            _('Couldn\'t get list for %s'),
            ],
        'empty': [
            '',''
        ]
        }

    def __init__(self):
        self.reset()

    def reset(self):
        self.level = 0
        self.event = 'empty'
        self.string = ''

    def warning(self):
        self.level = 1

    def get_msg(self):
        return self.compose_msg()

    def compose_msg(self):
        try:
            msg = self.message[self.event][self.level] % self.string
        except TypeError:
            msg = self.message[self.event][self.level]
        return ' ' +msg+ ' '

def print_ask_service(token_file):
    print ''
    print encode(_('Couldn\'t find any profile.'))
    print ''
    print encode(_('It should reside in: %s')) % token_file
    print encode(_('If you want to setup a new account, then follow these steps'))
    print encode(_('If you want to skip this, just press return or ctrl-C.'))
    print ''

    print ''
    print encode(_('Which service do you want to use?'))
    print ''
    print '1. Twitter'
    print '2. Identi.ca'
    print ''

def print_ask_root_url():
    print ''
    print ''
    print encode(_('Which root url do you want? (leave blank for default, https://identi.ca/api)'))
    print ''

########NEW FILE########
__FILENAME__ = bitly
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import urllib2
try:
    import json
except:
    import simplejson as json

from urlshorter import UrlShorter

APIKEY = 'apiKey=R_f806c2011339080ea0b623959bb8ecff'
VERION = 'version=2.0.1'
LOGIN  = 'login=tyrs'

class BitLyUrlShorter(UrlShorter):

    def __init__(self):
        self.base = 'http://api.bit.ly/shorten?%s&%s&%s&longUrl=%s'

    def do_shorter(self, url):
        long_url = self._quote_url(url)
        request = self.base % (VERION, LOGIN, APIKEY, long_url)
        response = json.loads(urllib2.urlopen(request).read())
        return response['results'][url]['shortUrl']

########NEW FILE########
__FILENAME__ = custom
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from urlshorter import UrlShorter

class CustomUrlShorter(UrlShorter):
    def __init__(self):
        pass

    def do_shorter(self, longurl):
        '''You need from the longurl return a short url'''
        pass

########NEW FILE########
__FILENAME__ = googl
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import httplib2
from urlshorter import UrlShorter

from apiclient.discovery import build

from oauth2client.file import Storage
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run

FLOW = OAuth2WebServerFlow(
    client_id='382344260739.apps.googleusercontent.com',
    client_secret='fJwAFxKWyW4rBmzzm6V3TVsZ',
    scope='https://www.googleapis.com/auth/urlshortener',
    user_agent='urlshortener-tyrs/1.0')

googl_token_file = os.environ['HOME'] + '/.config/tyrs/googl.tok'

class GooglUrlShorter(UrlShorter):

    def do_shorter(self, longurl):

        storage = Storage(googl_token_file)
        credentials = storage.get()
        if credentials is None or credentials.invalid:
            return 'need to register to use goog.gl'

        http = httplib2.Http()
        http = credentials.authorize(http)

        service = build("urlshortener", "v1", http=http)

        try:

            url = service.url()

            body = {"longUrl": longurl }
            resp = url.insert(body=body).execute()

            return resp['id']

        except AccessTokenRefreshError:
            pass

    def register_token(self):
        storage = Storage(googl_token_file)
        credentials = storage.get()
        if credentials is None or credentials.invalid:
            print 'There is no token file found for goo.gl'
            print 'A file will be generated for you'
            credentials = run(FLOW, storage)

########NEW FILE########
__FILENAME__ = msudpl
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# Copyright © 2011 Natal Ngétal <hobbestig@cpan.org>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
import urllib
from urlshorter import UrlShorter

class MsudplUrlShorter(UrlShorter):
    def __init__(self):
        self.base = "http://msud.pl"
        self.pt   = re.compile('<p>Whouah ! This a very beautiful url :\) <a href="(.*?)">')
        self.pt_yet_in_base   = re.compile('and whouah! It\'s very beautiful <a href="(.*?)">')

    def do_shorter(self, longurl):
        values = {'submit' : 'Generate my sexy url', 'sexy_url': longurl}

        data = urllib.urlencode(values)
        resp = self._get_request(self.base, data)
        short = self.pt.findall(resp)
        if len(short) == 0:
            short = self.pt_yet_in_base.findall(resp)

        if len(short) > 0:
            return self.base + '/' + short[0]

########NEW FILE########
__FILENAME__ = ur1ca
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import re
import urllib
from urlshorter import UrlShorter

class Ur1caUrlShorter(UrlShorter):
    def __init__(self):
        self.base = "http://ur1.ca"
        self.pt = re.compile('<p class="success">Your ur1 is: <a href="(.*?)">')

    def do_shorter(self, longurl):
        values = {'submit' : 'Make it an ur1!', 'longurl' : longurl}

        data = urllib.urlencode(values)
        resp = self._get_request(self.base, data)
        short = self.pt.findall(resp)

        if len(short) > 0:
            return short[0]

########NEW FILE########
__FILENAME__ = urlshorter
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import urllib2

class UrlShorter(object):

    def _quote_url(self, url):
        long_url = urllib2.quote(url)
        long_url = long_url.replace('/', '%2F')
        return long_url

    def _get_request(self, url, data=None):
        return urllib2.urlopen(url, data).read()

########NEW FILE########
__FILENAME__ = timeline
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import urwid
from widget import StatusWidget
from filter import FilterStatus

class Timeline(object):

    def __init__(self, buffer):
        self.cleared = False
        self.buffer = buffer
        self.walker = []
        self.unread = 0
        self.count = 0
        self.last_read = 0
        self.page = 1
        self.filter = FilterStatus()
        self.timeline = urwid.ListBox(urwid.SimpleListWalker([]))

    def append_new_statuses(self, retreive):
        retreive = self.filter_statuses(retreive)

        if retreive:
            self.last_read = retreive[0].id

            if len(self.walker) == 0 and not self.cleared:
                self.build_new_walker(retreive)
            else:
                self.add_to_walker(retreive)
            self.add_waterline()

    def add_to_walker(self, retreive):
        size = self.interface.loop.screen_size
        on_top = 'top' in self.timeline.ends_visible(size)
        focus_status, pos = self.walker.get_focus()
        for i, status in enumerate(retreive):
            # New statuses are insert
            if status.id == self.cleared:
                return
            while status.id != self.walker[0+i].id:
                self.walker.insert(i, StatusWidget(status.id, status))
                if on_top:
                    self.timeline.set_focus(0)
                    self.timeline.set_focus(pos+i+1)

            # otherwise it just been updated
            self.timeline.set_focus(pos)
            self.walker[i] = StatusWidget(status.id, status)

    def add_waterline(self):
        if self.buffer == 'home' and self.walker[0].id != None:
            div = urwid.Divider('-')
            div.id = None
            self.walker.insert(self.find_waterline(), div)

    def build_new_walker(self, retreive):
        items = []
        for i, status in enumerate(retreive):
            items.append(StatusWidget(status.id, status))
            self.walker = urwid.SimpleListWalker(items)
            self.timeline = urwid.ListBox(self.walker)
            import tyrs
            self.interface = tyrs.container['interface']
            urwid.connect_signal(self.walker, 'modified', self.interface.lazzy_load)

    def find_waterline(self):
        for i, v in enumerate(self.walker):
            if str(v.id) == self.interface.last_read_home:
                return i
        return 0

    def filter_statuses(self, statuses):
        filters = []
        for i, status in enumerate(statuses):
            if self.filter.filter_status(status):
                filters.append(i)
        filters.reverse()
        for f in filters:
            del statuses[f]

        return statuses

    def update_counter(self):
        self.count_statuses()
        self.count_unread()

    def append_old_statuses(self, statuses):
        if statuses == []:
            pass
        else:
            items = []
            for status in statuses:
                items.append(StatusWidget(status.id, status))
            self.walker.extend(items)
            self.count_statuses()
            self.count_unread()

    def count_statuses(self):
        try:
            self.count = len(self.walker)
        except TypeError:
            self.count = 0

    def count_unread(self):
        try:
            self.unread = 0
            for i in range(len(self.walker)):
                if self.walker[i].id == self.last_read:
                    break
                self.unread += 1
        except TypeError:
            self.unread = 0

    def reset(self):
        self.first = 0
        self.unread = 0

    def clear(self):
        urwid.disconnect_signal(self.walker, 'modified', self.interface.lazzy_load)
        while len(self.walker) > 1:
            pop = self.walker.pop()
            self.cleared = pop.id
        if self.cleared == None:
            self.cleared = True

    def empty(self, buffer):
        self.__init__(buffer)

    def all_read(self):
        if self.count > 0:
            self.last_read = self.walker[0].id

    def go_up(self):
        focus_status, pos = self.walker.get_focus()
        if pos > 0:
            self.timeline.set_focus(pos-1)

    def go_down(self):
        focus_status, pos = self.walker.get_focus()
        self.timeline.set_focus(pos+1)

    def status_count(self):
        self.count_statuses()
        return self.count

########NEW FILE########
__FILENAME__ = tweets
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import tyrs
import urwid
import logging
import urllib2
import oauth2 as oauth
from utils import encode
from help import help_bar
from urllib2 import URLError
from message import FlashMessage
from httplib import BadStatusLine
from twitter import Api, TwitterError, Status, _FileCache, List

try:
    import json
except ImportError:
    import simplejson as json

class Tweets(object):

    def __init__(self):
        self.conf = tyrs.container['conf']
        self.timelines = tyrs.container['timelines']
        self.search_user = None
        self.search_word = None
        self.flash_message = FlashMessage()

    def set_interface(self):
        self.interface = tyrs.container['interface']

    def authentication(self):
        url = self.get_base_url()
        proxify = self.get_proxy()
        self.api = ApiPatch(
            self.conf.token[self.conf.service]['consumer_key'],
            self.conf.token[self.conf.service]['consumer_secret'],
            self.conf.oauth_token,
            self.conf.oauth_token_secret,
            base_url=url,
            proxy=proxify
        )
        self.set_myself()

    def get_base_url(self):
        url = None
        if self.conf.service == 'identica':
            url = self.conf.base_url

        return url

    def get_proxy(self):
        proxy = self.conf.params['proxy']
        if proxy:
            return {
                'http': 'http://{0}'.format(proxy),
                'https': 'https://{0}'.format(proxy),
            }
        else:
            return {}

    def set_myself(self):
        self.myself = self.api.VerifyCredentials()
        self.conf.my_nick = self.myself.screen_name

    def post_tweet(self, tweet, reply_to=None):
        self.flash('tweet')
        try:
            return self.api.PostUpdate(tweet, reply_to)
        except TwitterError, e:
            self.error(e)

    def retweet(self):
        self.flash('retweet')
        status = self.interface.current_status()
        try:
            self.api.PostRetweet(status.id)
        except TwitterError, e:
            self.error(e)

    def retweet_and_edit(self):
        status = self.interface.current_status()
        nick = status.user.screen_name
        data = 'RT @%s: %s' % (nick, status.text)
        self.interface.edit_status('tweet', data)

    #def reply(self):
        #status = self.interface.current_status()
        #if hasattr(status, 'user'):
            #nick = status.user.screen_name
        #else:
            #self.direct_message()
        #data = '@' + nick + ' '
        #tweet = TweetEditor(data).content
        #if tweet:
            #self.post_tweet(tweet, status.id)

    def destroy(self):
        self.flash('destroy')
        status = self.interface.current_status()
        try:
            self.api.DestroyStatus(status.id)
        except TwitterError, e:
            self.error(e)

    #FIXME!
    def direct_message(self):
        ''' Two editing box, one for the name, and one for the content'''
        nick = self.nick_for_direct_message()
        tweet = TweetEditor().content
        if tweet:
            self.send_direct_message(nick, tweet)

    #FIXME!
    def nick_for_direct_message(self):
        status = self.interface.current_status()
        if hasattr(status, 'user'):
            nick = status.user.screen_name
        else:
            nick = status.sender_screen_name
        nick = NickEditor(nick).content

        return nick

    def send_direct_message(self, nick, tweet):
        self.flash('direct')
        try:
            return self.api.PostDirectMessage(nick, tweet)
        except TwitterError, e:
            self.error(e)

    def do_list(self):
        self.interface.edit_status('list')

    def follow(self):
        self.interface.edit_status('follow')

    def follow_selected(self):
        status = self.interface.current_status()
        if self.interface.is_retweet(status):
            nick = self.interface.origin_of_retweet(status)
        else:
            nick = status.user.screen_name
        self.create_friendship(nick)

    #def unfollow(self):
        #nick = NickEditor().content
        #if nick:
            #self.destroy_friendship(nick)

    def unfollow_selected(self):
        nick = self.interface.current_status().user.screen_name
        self.destroy_friendship(nick)

    def create_friendship(self, nick):
        self.flash('follow', nick)
        try:
            self.api.CreateFriendship(nick)
        except TwitterError, e:
            self.error(e)

    def destroy_friendship(self, nick):
        self.flash('unfollow', nick)
        try:
            self.api.DestroyFriendship(nick)
        except TwitterError, e:
            self.error(e)

    def set_favorite(self):
        self.flash('favorite')
        status = self.interface.current_status()
        try:
            self.api.CreateFavorite(status)
        except TwitterError, e:
            self.error(e)

    def destroy_favorite(self):
        self.flash('favorite_del')
        status = self.interface.current_status()
        try:
            self.api.DestroyFavorite(status)
        except TwitterError, e:
            self.error(e)

    def get_favorites(self):
        self.interface.change_buffer('favorite')

    def update_timeline(self, timeline):
        '''
        Retrieves tweets, don't display them
        @param the buffer to retreive tweets
        '''

        logging.debug('updating "{0}" timeline'.format(timeline))
        try:
            statuses = self.retreive_statuses(timeline)
            timeline = self.timelines[timeline]
            timeline.append_new_statuses(statuses)
            if timeline.unread and self.conf.params['beep']:
                self.interface.beep()

        except TwitterError, e:
            self.update_error(e)
        except BadStatusLine, e:
            self.update_error(e)
        except ValueError, e:
            self.update_error(e)
        except URLError, e:
            self.update_error(e)

    def update_error(self, err):
        logging.error('Updating issue: {0}'.format(err))
        self.flash_message.event = 'update'
        self.flash_message.level = 1
        self.interface.display_flash_message()

    def retreive_statuses(self, timeline, page=None):
        self.flash_message.event = 'update'
        self.flash_message.level = 0
        self.interface.display_flash_message()
        if timeline == 'home':
            statuses = self.api.GetFriendsTimeline(retweets=True, page=page)
        elif timeline == 'mentions':
            statuses = self.api.GetMentions(page=page)
        elif timeline == 'user_retweet':
            statuses = self.api.GetUserRetweets()
        elif timeline == 'search' and self.search_word != '':
            statuses = self.api.GetSearch(self.search_word, page=page)
        elif timeline == 'direct':
            statuses = self.api.GetDirectMessages(page=page)
        elif timeline == 'user' and self.search_user != '':
            statuses = self.load_user_public_timeline(page=page)
        elif timeline == 'favorite':
            statuses = self.api.GetFavorites(page=page)
        elif timeline == 'thread':
            statuses = self.get_thread()
        elif timeline == 'list':
            statuses = self.api.GetListStatuses(self.myself.screen_name, self.list_slug, per_page='15', page=page)
        self.interface.erase_flash_message()

        return statuses


    def find_public_timeline(self, nick):
        if nick and nick != self.search_user:
            self.change_search_user(nick)
            self.load_user_public_timeline()
            self.interface.change_buffer('user')

    def find_current_public_timeline(self):
        self.change_search_user(self.interface.current_status().user.screen_name)
        self.load_user_public_timeline()
        self.interface.change_buffer('user')

    def change_search_user(self, nick):
        self.search_user = nick
        self.timelines['user'].empty('user')

    def my_public_timeline(self):
        self.change_search_user(self.myself.screen_name)
        self.load_user_public_timeline()

    def load_user_public_timeline(self, page=None):
        if self.search_user:
            return self.api.GetUserTimeline(self.search_user,
                    include_rts=True, page=page)
        else:
            return []

    def get_thread(self):
        try:
            status = self.interface.current_status()
            self.timelines['thread'].empty('thread')
            self.statuses = [status]
            self.build_thread(status)
            self.timelines['thread'].append_new_statuses(self.statuses)
            self.interface.change_buffer('thread')
        except IndexError:
            return []

    def build_thread(self, status):
        if status.in_reply_to_status_id:
            try:
                reply_to = self.api.GetStatus(status.in_reply_to_status_id)
                self.statuses.append(reply_to)
                self.build_thread(reply_to)
            except TwitterError:
                pass

    def search(self, content):
        self.search_word = content
        self.flash('search', self.search_word)
        self.timelines['search'].empty('search')
        try:
            self.timelines['search'].append_new_statuses(self.api.GetSearch(self.search_word))
            self.interface.change_buffer('search')
        except TwitterError, e:
            self.error(e)

    def list(self, content):
        self.list_slug = content
        self.flash('list', self.list_slug)
        self.timelines['list'].empty('list')
        try:
            self.timelines['list'].append_new_statuses(self.api.GetListStatuses(self.myself.screen_name,self.list_slug, per_page='15'))
            self.interface.change_buffer('list')
        except TwitterError, e:
            self.error(e)

    def tweet_done(self, content):
        self.clean_edit()
        urwid.disconnect_signal(self, self.interface.foot, 'done', self.tweet_done)
        if content:
            self.post_tweet(encode(content))

    def reply_done(self, content):
        self.clean_edit()
        urwid.disconnect_signal(self, self.interface.foot, 'done', self.reply_done)
        if content:
            self.post_tweet(encode(content), self.interface.current_status().id)

    def follow_done(self, content):
        self.clean_edit()
        urwid.disconnect_signal(self, self.interface.foot, 'done', self.follow_done)
        if content:
            self.create_friendship(content)

    def unfollow_done(self, content):
        self.clean_edit()
        urwid.disconnect_signal(self, self.interface.foot, 'done', self.unfollow_done)
        if content:
            self.destroy_friendship(content)

    def search_done(self, content):
        self.clean_edit()
        urwid.disconnect_signal(self, self.interface.foot, 'done', self.search_done)
        if content:
            self.search(encode(content))

    def public_done(self, content):
        self.clean_edit()
        urwid.disconnect_signal(self, self.interface.foot, 'done', self.public_done)
        if content:
            self.find_public_timeline(content)

    def list_done(self, content):
        self.clean_edit()
        urwid.disconnect_signal(self, self.interface.foot, 'done', self.list_done)
        if content:
            self.list(encode(content)) 

    def clean_edit(self):
        footer = help_bar()
        self.interface.main_frame.set_focus('body')
        self.interface.main_frame.set_footer(footer)

    def flash(self, event, string=None):
        self.flash_message.event = event
        if string:
            self.flash_message.string = string

    def error(self, err=None):
        logging.warning('Error catch: {0}'.format(err))
        self.flash_message.warning()

DEFAULT_CACHE = object()

class ApiPatch(Api):

    def __init__(self,
               consumer_key=None,
               consumer_secret=None,
               access_token_key=None,
               access_token_secret=None,
               input_encoding=None,
               request_headers=None,
               cache=DEFAULT_CACHE,
               shortner=None,
               base_url=None,
               use_gzip_compression=False,
               debugHTTP=False,
               proxy={}
              ):


        self.SetCache(cache)
        self._urllib         = urllib2
        self._cache_timeout  = Api.DEFAULT_CACHE_TIMEOUT
        self._input_encoding = input_encoding
        self._use_gzip       = use_gzip_compression
        self._debugHTTP      = debugHTTP
        self._oauth_consumer = None
        self._proxy = proxy

        self._InitializeRequestHeaders(request_headers)
        self._InitializeUserAgent()
        self._InitializeDefaultParameters()

        if base_url is None:
            self.base_url = 'https://api.twitter.com/1'
        else:
            self.base_url = base_url

        if consumer_key is not None and (access_token_key is None or
                                         access_token_secret is None):
            print >> sys.stderr, 'Twitter now requires an oAuth Access Token for API calls.'
            print >> sys.stderr, 'If your using this library from a command line utility, please'
            print >> sys.stderr, 'run the the included get_access_token.py tool to generate one.'

            raise TwitterError('Twitter requires oAuth Access Token for all API access')

        self.SetCredentials(consumer_key, consumer_secret, access_token_key, access_token_secret)

    def _FetchUrl(self,
                url,
                post_data=None,
                parameters=None,
                no_cache=None,
                use_gzip_compression=None):


    # Build the extra parameters dict
      extra_params = {}
      if self._default_params:
        extra_params.update(self._default_params)
      if parameters:
        extra_params.update(parameters)

      if post_data:
        http_method = "POST"
      else:
        http_method = "GET"

      if self._debugHTTP:
        _debug = 1
      else:
        _debug = 0

      http_handler = self._urllib.HTTPHandler(debuglevel=_debug)
      https_handler = self._urllib.HTTPSHandler(debuglevel=_debug)
      proxy_handler = self._urllib.ProxyHandler(self._proxy)

      opener = self._urllib.OpenerDirector()
      opener.add_handler(http_handler)
      opener.add_handler(https_handler)

      if self._proxy:
          opener.add_handler(proxy_handler)

      if use_gzip_compression is None:
        use_gzip = self._use_gzip
      else:
        use_gzip = use_gzip_compression

    # Set up compression
      if use_gzip and not post_data:
        opener.addheaders.append(('Accept-Encoding', 'gzip'))

      if self._oauth_consumer is not None:
        if post_data and http_method == "POST":
          parameters = post_data.copy()

        req = oauth.Request.from_consumer_and_token(self._oauth_consumer,
                                                  token=self._oauth_token,
                                                  http_method=http_method,
                                                  http_url=url, parameters=parameters)

        req.sign_request(self._signature_method_hmac_sha1, self._oauth_consumer, self._oauth_token)

        headers = req.to_header()

        if http_method == "POST":
          encoded_post_data = req.to_postdata()
        else:
          encoded_post_data = None
          url = req.to_url()
      else:
        url = self._BuildUrl(url, extra_params=extra_params)
        encoded_post_data = self._EncodePostData(post_data)

      # Open and return the URL immediately if we're not going to cache
      if encoded_post_data or no_cache or not self._cache or not self._cache_timeout:
        response = opener.open(url, encoded_post_data)
        url_data = self._DecompressGzippedResponse(response)
        opener.close()
      else:
      # Unique keys are a combination of the url and the oAuth Consumer Key
        if self._consumer_key:
          key = self._consumer_key + ':' + url
        else:
          key = url

      #TODO I turn off the cache as it bugged all the app,
      #but I need to see what's wrong with that.
      # See if it has been cached before
      #last_cached = self._cache.GetCachedTime(key)

      # If the cached version is outdated then fetch another and store it
      #if not last_cached or time.time() >= last_cached + self._cache_timeout:
        try:
          response = opener.open(url, encoded_post_data)
          url_data = self._DecompressGzippedResponse(response)
        #self._cache.Set(key, url_data)
        except urllib2.HTTPError, e:
          print e
        opener.close()
    #else:
      #url_data = self._cache.Get(key)

    # Always return the latest version
      return url_data

    def PostRetweet(self, id):
        '''This code come from issue #130 on python-twitter tracker'''

        if not self._oauth_consumer:
            raise TwitterError("The twitter.Api instance must be authenticated.")
        try:
            if int(id) <= 0:
                raise TwitterError("'id' must be a positive number")
        except ValueError:
            raise TwitterError("'id' must be an integer")
        url = 'http://api.twitter.com/1/statuses/retweet/%s.json' % id
        json_data = self._FetchUrl(url, post_data={'dummy': None})
        data = json.loads(json_data)
        self._CheckForTwitterError(data)
        return Status.NewFromJsonDict(data)

    def GetCachedTime(self,key):
        path = self._GetPath(key)
        if os.path.exists(path):
            return os.path.getmtime(path)
        else:
            return None

    def SetCache(self, cache):
        '''Override the default cache.  Set to None to prevent caching.

        Args:
          cache:
            An instance that supports the same API as the twitter._FileCache
        '''
        if cache == DEFAULT_CACHE:
            self._cache = _FileCache()
        else:
            self._cache = cache

    def GetListStatuses(self,user,slug, per_page=None,page=None,since_id=None,max_id=None):
        '''Fetch the List statuses for a given user / list.

        Args:
          user: the username or id of the user whose list you are fetching.
          slug: slug of the list to fetch
          since_id: return only statuses with an ID greater than the specified ID
          [optional]
          max_id: return only statuses with an ID less than or equal to the
          specified ID [optional]
          per_page: specifies the maximum number of statuses to retrieve.  Must be
          <= 200 [optional]
          page: specifies the page to retrieve [optional]
          '''
        url = self.base_url
        path_elements = ['lists','statuses.json']
        params = {'slug':slug,
                  'owner_screen_name':user,
                  'include_entities':'true'}
        if since_id:
          params['since_id']=since_id
        if max_id:
          params['max_id']=max_id
        if page:
            params['page']=page
        if per_page:
            params['per_page'] = per_page
        url = self._BuildUrl(url,path_elements,params)
        json_data = self._FetchUrl(url)
        data = json.loads(json_data)
        self._CheckForTwitterError(data)
        return [Status.NewFromJsonDict(x) for x in data]

########NEW FILE########
__FILENAME__ = tyrs
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
   Tyrs

   @author:     Nicolas Paris <nicolas.caen@gmail.com>
   @date:       23/12/2011
   @licence:    GPLv3


'''

__revision__ = "0.6.2"

import sys
import utils
import config
import locale
import tweets
import argparse
import gettext
from urllib2 import URLError
from timeline import Timeline
from container import Container
from interface import Interface
from completion import Completion

locale.setlocale(locale.LC_ALL, '')
container =  Container()

def arguments():
    '''
    Parse all arguments from the CLI
    '''
    parser = argparse.ArgumentParser(
            'Tyrs: a twitter client writen in python with curses.')
    parser.add_argument('-a', '--account',
            help='Use another account, store in a different file.')
    parser.add_argument('-c', '--config',
            help='Use another configuration file.')
    parser.add_argument('-g', '--generate-config',
            help='Generate a default configuration file.')
    parser.add_argument('-v', '--version', action='version', version='Tyrs %s' % __revision__,
            help='Show the current version of Tyrs')
    args = parser.parse_args()
    return args

def main():

    utils.set_console_title()
    init_conf()
    init_tyrs()

def init_tyrs():
    init_timelines()
    init_api()
    init_interface()

def init_conf():
    conf = config.Config(arguments())
    container.add('conf', conf)


def init_api():
    api = tweets.Tweets()
    container.add('api', api)
    try:
        api.authentication()
    except URLError, e:
        print 'error:%s' % e
        sys.exit(1)

def init_interface():
    user_interface = Interface()
    container.add('interface', user_interface)

def init_timelines():
    buffers = (
        'home', 'mentions', 'direct', 'search',
        'user', 'favorite', 'thread', 'user_retweet',
        'list'
    )
    timelines = {}
    for buff in buffers:
        timelines[buff] = Timeline(buff)
    container.add('timelines', timelines)
    container.add('buffers', buffers)
    completion = Completion()
    container.add('completion', completion)

if __name__ == "__main__":
    gettext.install('tyrs', unicode=1)
    main()

########NEW FILE########
__FILENAME__ = update
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import tyrs
import time
import logging
import threading

class UpdateThread(threading.Thread):
    '''
    The only thread that update all timelines
    '''

    def __init__(self):
        self.interface = tyrs.container['interface']
        self.conf = tyrs.container['conf']
        self.api = tyrs.container['api']
        threading.Thread.__init__(self, target=self.run)
        self._stopevent = threading.Event()

    def run(self):
        self.update_timeline()
        logging.info('Thread started')
        for i in range(self.conf.params['refresh'] * 60):
            time.sleep(1)
            if self._stopevent.isSet() or self.interface.stoped:
                logging.info('Thread forced to stop')
                return
        self.start_new_thread()
        logging.info('Thread stoped')
        self._Thread__stop()

    def stop(self):
        self._stopevent.set()

    def start_new_thread(self):
        update = UpdateThread()
        update.start()

    def update_timeline(self):
        while not self.interface.loop.screen._started:
            time.sleep(1)
        timeline = ('home', 'mentions', 'direct')
        for t in timeline:
            self.api.update_timeline(t)
        self.interface.display_timeline()
        self.interface.redraw_screen()

########NEW FILE########
__FILENAME__ = user
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import tyrs
import curses
from utils import encode

class User(object):

    def __init__(self, user):
        self.interface = tyrs.container['interface']
        self.user = user
        self.interface.refresh_token = True
        self._init_screen()
        self._display_header()
        self._display_info()
        self.screen.getch()
        self.screen.erase()
        self.interface.refresh_token = False

    def _init_screen(self):
        maxyx = self.interface.screen.getmaxyx()
        self.screen = self.interface.screen.subwin(30, 80, 3, 10)
        self.screen.border(0)
        self.screen.refresh()

    def _display_header(self):
        self.screen.addstr(2, 10, '%s -- %s' % (self.user.screen_name,
            encode(self.user.name)))

    def _display_info(self):
        info = {
            'location': encode(self.user.location),
            'description': encode(self.user.description),
            'url': encode(self.user.url),
            'time zone': encode(self.user.time_zone),
            'status': self.user.status,
            'friends': self.user.friends_count,
            'follower': self.user.followers_count,
            'tweets': self.user.statuses_count,
            'verified': self.user.verified,
            'created at': self.user.created_at,
            }
        i=0
        for item in info:
            self.screen.addstr(4+i, 5, '%s' % item)
            self.screen.addstr(4+i, 20, '%s' % info[item])
            i += 1



########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
import os
import sys
#import tyrs
import string
from htmlentitydefs import entitydefs

def set_console_title():
    try:
        sys.stdout.write("\x1b]2;Tyrs\x07")
    except:
        pass

def cut_attag(name):
    if name[0] == '@':
        name = name[1:]
    return name

def get_exact_nick(word):
    if word[0] == '@':
        word = word[1:]
    alphanum = string.letters + string.digits
    try:
        while word[-1] not in alphanum:
            word = word[:-1]
    except IndexError:
        pass
    return word

def encode(string):
    try:
        return string.encode(sys.stdout.encoding, 'replace')
    except AttributeError:
        return string

def html_unescape(str):
    """ Unescapes HTML entities """
    def entity_replacer(m):
        entity = m.group(1)
        if entity in entitydefs:
            return entitydefs[entity]
        else:
            return m.group(0)

    return re.sub(r'&([^;]+);', entity_replacer, str)


def get_source(source):
    if source != 'web':
        source = source.split('>')
        source = source[1:]
        source = ' '.join(source)
        source = source.split('<')[:1]
        source = source[:1]
        source = ' '.join(source)
    return source

def open_image(user):
    image = user.profile_image_url
    command = tyrs.container['conf'].params['open_image_command']
    os.system(command % image)


def get_urls(text):
    return re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)

########NEW FILE########
__FILENAME__ = widget
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
import tyrs
import time
import urwid
from utils import html_unescape, encode, get_source, get_urls, get_exact_nick

class HeaderWidget(urwid.WidgetWrap):

    def __init__(self):
        self.api = tyrs.container['api']
        self.interface = tyrs.container['interface']
        self.timelines = tyrs.container['timelines']
        self.buffer = self.interface.buffer
        flash = self.set_flash()
        activities = self.set_activities()
        w = urwid.Columns([flash, ('fixed', 20, activities)])
        self.__super.__init__(w)

    def set_flash(self):
        msg = ''
        level = 0
        msg = self.api.flash_message.get_msg()
        color = {0: 'info_msg', 1: 'warn_msg'}
        level = self.api.flash_message.level
        event_message = urwid.Text(msg)
        flash = urwid.AttrWrap(event_message, color[level])
        return flash

    def set_activities(self):

        buffers = (
            'home', 'mentions', 'direct', 'search',
            'user', 'favorite', 'thread', 'user_retweet',
            'list'
        )
        display = { 
            'home': 'H', 'mentions': 'M', 'direct': 'D', 
            'search': 'S', 'user': 'U', 'favorite': 'F',
            'thread': 'T', 'user_retweet': 'R', 'list': 'L'
        }
        buff_widget = []
        for b in buffers:
            if b == self.buffer:
                buff_widget.append(('current_tab', display[b]))
            else:
                buff_widget.append(('other_tab', display[b]))
            if b in ('home', 'mentions', 'direct'):
                buff_widget.append(self.get_unread(b))

        return urwid.Text(buff_widget)

    def get_unread(self, buff):
        self.select_current_timeline().all_read()
        unread = self.timelines[buff].unread
        if unread == 0:
            color = 'read'
        else:
            color = 'unread'
        return [('read', ':'), (color , str(unread)), ' ']

    def select_current_timeline(self):
        return self.timelines[self.buffer]

class StatusWidget (urwid.WidgetWrap):

    def __init__ (self, id, status):
        self.regex_retweet     = re.compile('^RT @\w+:')
        self.conf       = tyrs.container['conf']
        self.api       = tyrs.container['api']
        self.set_date()
        self.buffer = tyrs.container['interface'].buffer
        self.is_retweet(status)
        self.id = id
        self.status = status
        status_content = urwid.Padding(
            urwid.AttrWrap(urwid.Text(self.get_text(status)), 'body'), left=1, right=1)
        w = urwid.AttrWrap(TitleLineBox(status_content, title=self.get_header(status)), 'line', 'focus')
        self.__super.__init__(w)

    def selectable (self):
        return True

    def keypress(self, size, key):
        return key

    def get_text(self, status):
        result = []
        text = html_unescape(status.text.replace('\n', ' '))
        if status.rt:
            text = text.split(':')[1:]
            text = ':'.join(text)

        if hasattr(status, 'retweeted_status'):
            if hasattr(status.retweeted_status, 'text') \
                    and len(status.retweeted_status.text) > 0:
                text = status.retweeted_status.text

        myself = self.api.myself.screen_name

        words = text.split(' ')
        for word in words:
            if word != '':
                word += ' '
                # The word is an HASHTAG ? '#'
                if word[0] == '#':
                    result.append(('hashtag', word))
                elif word[0] == '@':
                    ## The AT TAG is,  @myself
                    if word == '@%s ' % myself or word == '@%s: ' % myself:
                        result.append(('highlight_nick', word))
                    ## @anyone
                    else:
                        result.append(('attag', word))
                        tyrs.container['completion'].add(get_exact_nick(word))
                        
                else:
                    result.append(word)
        return result

    def get_header(self, status):
        retweeted = ''
        reply = ''
        retweet_count = ''
        retweeter = ''
        source = self.get_source(status)
        nick = self.get_nick(status)
        timer = self.get_time(status)

        if self.is_reply(status):
            reply = u' \u2709'
        if status.rt:
            retweeted = u" \u267b "
            retweeter = nick
            nick = self.origin_of_retweet(status)

        if self.get_retweet_count(status):
            retweet_count = str(self.get_retweet_count(status))
            
        tyrs.container['completion'].add(get_exact_nick(nick))
        header_template = self.conf.params['header_template'] 
        header = unicode(header_template).format(
            time = timer,
            nick = nick,
            reply = reply,
            retweeted = retweeted,
            source = source,
            retweet_count = retweet_count,
            retweeter = retweeter
            )

        return encode(header)

    def set_date(self):
        self.date = time.strftime("%d %b", time.gmtime())

    def get_time(self, status):
        '''Handle the time format given by the api with something more
        readeable
        @param  date: full iso time format
        @return string: readeable time
        '''
        if self.conf.params['relative_time'] == 1 and self.buffer != 'direct':
            try:
                result =  status.GetRelativeCreatedAt()
            except AttributeError:
                return ''
        else:
            hour = time.gmtime(status.GetCreatedAtInSeconds() - time.altzone)
            result = time.strftime('%H:%M', hour)
            if time.strftime('%d %b', hour) != self.date:
                result += time.strftime(' - %d %b', hour)

        return result

    def get_source(self, status):
        source = ''
        if hasattr(status, 'source'):
            source = get_source(status.source)

        return source

    def get_nick(self, status):
        if hasattr(status, 'user'):
            nick = status.user.screen_name
        else:
            #Used for direct messages
            nick = status.sender_screen_name

        return nick

    def get_retweet_count(self, status):
        if hasattr(status, 'retweet_count'):
            return status.retweet_count

    def is_retweet(self, status):
        status.rt = self.regex_retweet.match(status.text)
        return status.rt

    def is_reply(self, status):
        if hasattr(status, 'in_reply_to_screen_name'):
            reply = status.in_reply_to_screen_name
            if reply:
                return True
        return False

    def origin_of_retweet(self, status):
        '''When its a retweet, return the first person who tweet it,
           not the retweeter
        '''
        origin = status.text
        origin = origin[4:]
        origin = origin.split(':')[0]
        origin = str(origin)
        return origin



class TitleLineBox(urwid.WidgetDecoration, urwid.WidgetWrap):
    def __init__(self, original_widget, title=''):
        """Draw a line around original_widget."""


        self.color = 'header'
        if int(urwid.__version__[0]) == 1:
            urwid.utf8decode = self.utf8decode

        tlcorner=None; tline=None; lline=None
        trcorner=None; blcorner=None; rline=None
        bline=None; brcorner=None

        def use_attr( a, t ):
            if a is not None:
                t = urwid.AttrWrap(t, a)
            return t

        tline = use_attr( tline, urwid.Columns([
            ('fixed', 2, urwid.Divider(urwid.utf8decode("─"))),
            ('fixed', len(title), urwid.AttrWrap(urwid.Text(title), self.color)),
            urwid.Divider(urwid.utf8decode("─"))]))
        bline = use_attr( bline, urwid.Divider(urwid.utf8decode("─")))
        lline = use_attr( lline, urwid.SolidFill(urwid.utf8decode("│")))
        rline = use_attr( rline, urwid.SolidFill(urwid.utf8decode("│")))
        tlcorner = use_attr( tlcorner, urwid.Text(urwid.utf8decode("┌")))
        trcorner = use_attr( trcorner, urwid.Text(urwid.utf8decode("┐")))
        blcorner = use_attr( blcorner, urwid.Text(urwid.utf8decode("└")))
        brcorner = use_attr( brcorner, urwid.Text(urwid.utf8decode("┘")))
        top = urwid.Columns([ ('fixed', 1, tlcorner),
            tline, ('fixed', 1, trcorner) ])
        middle = urwid.Columns( [('fixed', 1, lline),
            original_widget, ('fixed', 1, rline)], box_columns = [0,2],
            focus_column = 1)
        bottom = urwid.Columns([ ('fixed', 1, blcorner),
            bline, ('fixed', 1, brcorner) ])
        pile = urwid.Pile([('flow',top),middle,('flow',bottom)],
            focus_item = 1)

        urwid.WidgetDecoration.__init__(self, original_widget)
        urwid.WidgetWrap.__init__(self, pile)

    def utf8decode(self, string):
        return string


########NEW FILE########
__FILENAME__ = test_complete
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import unittest
sys.path.append('../src/tyrs')
from completion import Completion

class TestCompletion(unittest.TestCase):

    def test_class(self):
        nicks = Completion()
        self.assertIsInstance(nicks, Completion)


    def test_add(self):
        nicks = Completion()
        nicks.add('coin')
        self.assertEqual(1, len(nicks))
        nicks.add('pan')
        self.assertEqual(2, len(nicks))

    def test_add_existing(self, ):
        nicks = Completion()
        nicks.add('coin')
        nicks.add('coin')
        self.assertEqual(1, len(nicks))

    def test_return_completion(self):
        nicks = Completion()
        nicks.add('coincoin')
        nicks.add('cooooooo')
        result = nicks.complete('coi')
        self.assertEqual('coincoin', result)
        result = nicks.complete('pan')
        self.assertIsNone(result)
        result = nicks.complete('co')
        self.assertIsNone(result)

    def test_return_text_completed(self):
        nicks = Completion()
        nicks.add('coin')
        nicks.add('pan')
        text = "foo bar @co"
        result = nicks.text_complete(text)
        self.assertEqual(result, 'in')

    def test_return_text_completed_failed(self):
        nicks = Completion()
        nicks.add('coin')
        nicks.add('pan')
        text = ['foo bar co', 'foo @co bar']
        for t in text:
            result =  nicks.text_complete(t)
            self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main ()

########NEW FILE########
__FILENAME__ = test_shortener
#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import unittest
sys.path.append('../src/tyrs')
import random
from shorter.urlshorter  import UrlShorter
from shorter.bitly import BitLyUrlShorter 
#TODO this shortener has dependencies such as `apiclient` and `urllib3`
#from shorter.googl import GooglUrlShorter
#FIXME msud.pl raises 502 HTTP errors very often
#from shorter.msudpl import MsudplUrlShorter
from shorter.ur1ca import Ur1caUrlShorter

url_re = 'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'

class TestShortener(unittest.TestCase):

    shorteners = [BitLyUrlShorter, Ur1caUrlShorter]
    
    def shortener_test(self, cls, url):
        """
        Receives a class descendant of `UrlShorter` and tests it with the
        given url.
        """
        assert issubclass(cls, UrlShorter)
        shortener = cls()
        result = shortener.do_shorter(url)
        self.assertRegexpMatches(result, url_re)

    def test_yet_in_base(self):
        url = 'http://www.nicosphere.net'
        for shortener in self.shorteners:
            self.shortener_test(shortener, url)

    def test_random_url(self):
        number = random.randint(10000, 100000)
        url = 'http://www.nicosphere{0}.net'.format(number)
        for shortener in self.shorteners:
            self.shortener_test(shortener, url)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_twitter_api
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import unittest
import sys
from time import gmtime, strftime
import gettext
gettext.install('tyrs', unicode=1)

sys.path.append('../src')
from tyrs import tyrs, tweets
from twitter import TwitterError, Status, User

class TestTwitterApi(unittest.TestCase):

    def setUp(self):
        self.authenticate()

    def authenticate(self):
        #TODO use twitturse credentials
        tyrs.init_conf()
        tyrs.init_timelines()
        tyrs.init_api()
        self.api = tweets.Tweets()
        self.api.authentication()

    def test_authentication(self):
        myself = self.api.myself
        username = myself.screen_name
        self.assertIsInstance(myself, User)
        self.assertEqual(username, 'twitturse')

    def test_post_update(self):
        tweet = 'test from unittest at ' + self.get_time()
        result = self.api.post_tweet(tweet)
        self.assertEqual(result.text, tweet)
        self.assertIsInstance(result, Status)
    
    def test_post_empty_update(self):
        tweet = ''
        result = self.api.post_tweet(tweet)
        self.assertIsNone(result)

    #FIXME! `Tweets` hasn't got an `update_home_timeline` method
    #def test_update_home_timeline(self):
        #result = self.api.update_home_timeline()
        #self.assertIsInstance(result[0], Status)
        #self.assertIsInstance(result[10], Status)

    def get_time(self):
        return strftime('%H:%M:%S', gmtime())


if __name__ == '__main__':
    unittest.main ()

########NEW FILE########
__FILENAME__ = test_utils
# -*- coding: utf-8 -*-
# Copyright © 2011 Nicolas Paris <nicolas.caen@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import unittest
import sys
sys.path.append('../src/tyrs')
#import gettext
#gettext.install('tyrs', unicode=1)
#import src.utils as utils
import utils

class TestUtils(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_cut_attag(self):
        nick = '@mynick'
        result = utils.cut_attag(nick)
        self.assertEqual(result, 'mynick')

    def test_get_source(self):
        source = '<a href="http://tyrs.nicosphere.net/" rel="nofollow">tyrs</a>'
        result = utils.get_source(source)
        self.assertEqual(result, 'tyrs')

    def test_get_exact_nick(self):
        nick = ['@mynick', '@mynick,', '@mynick!!', 'mynick,']
        for n in nick:
            result = utils.get_exact_nick(n)
            self.assertEqual(result, 'mynick')

if __name__ == '__main__':
    unittest.main ()

########NEW FILE########
