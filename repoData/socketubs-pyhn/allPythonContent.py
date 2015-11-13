__FILENAME__ = cachemanager
# -*- coding: utf-8 -*-
import os
import pickle
import datetime

from pyhn.config import Config
from pyhn.hnapi import HackerNewsAPI


class CacheManager(object):

    def __init__(self, cache_path=None):
        self.cache_path = cache_path
        if cache_path is None:
            self.config = Config()
            self.cache_path = self.config.parser.get('settings', 'cache')

        self.cache_age = int(self.config.parser.get('settings', 'cache_age'))
        self.extra_page = int(self.config.parser.get('settings', 'extra_page'))
        self.api = HackerNewsAPI()

        if not os.path.exists(self.cache_path):
            self.refresh()

    def is_outdated(self, which="top"):
        if not os.path.exists(self.cache_path):
            return True

        try:
            cache = pickle.load(open(self.cache_path, 'rb'))
        except:
            cache = {}
        if not cache.get(which, False):
            return True

        cache_age = datetime.datetime.today() - cache[which]['date']
        if cache_age.seconds > self.cache_age * 60:
            return True
        else:
            return False

    def refresh(self, which="top"):
        if which == "top":
            stories = self.api.getTopStories(extra_page=self.extra_page)
        elif which == "newest":
            stories = self.api.getNewestStories(extra_page=self.extra_page)
        elif which == "best":
            stories = self.api.getBestStories(extra_page=self.extra_page)
        else:
            raise Exception('Bad value: top, newest and best stories')

        cache = {}
        if os.path.exists(self.cache_path):
            try:
                cache = pickle.load(open(self.cache_path, 'rb'))
            except:
                pass

        cache[which] = {'stories': stories, 'date': datetime.datetime.today()}
        pickle.dump(cache, open(self.cache_path, 'wb'))

    def get_stories(self, which="top"):
        cache = []
        if os.path.exists(self.cache_path):
            try:
                cache = pickle.load(open(self.cache_path, 'rb'))
            except:
                cache = {}

        if not cache.get(which, False):
            return []
        else:
            return cache[which]['stories']

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-
import os

try:
    from configparser import SafeConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser


class Config(object):
    def __init__(self, config_dir=None, config_file=None):
        self.config_dir = config_dir
        self.config_file = config_file

        if config_dir is None:
            self.config_dir = os.path.join(
                os.environ.get('HOME', './'),
                '.pyhn')
        if config_file is None:
            self.config_file = "config"

        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)

        self.config_path = os.path.join(self.config_dir, self.config_file)

        self.parser = SafeConfigParser()
        self.read()

    def read(self):
        self.parser.read(self.config_path)

        # Keybindings
        if not self.parser.has_section('keybindings'):
            self.parser.add_section('keybindings')

        if not self.parser.has_option('keybindings', 'page_up'):
            self.parser.set('keybindings', 'page_up', 'ctrl u')
        if not self.parser.has_option('keybindings', 'page_down'):
            self.parser.set('keybindings', 'page_down', 'ctrl d')
        if not self.parser.has_option('keybindings', 'first_story'):
            self.parser.set('keybindings', 'first_story', 'g')
        if not self.parser.has_option('keybindings', 'last_story'):
            self.parser.set('keybindings', 'last_story', 'G')
        if not self.parser.has_option('keybindings', 'up'):
            self.parser.set('keybindings', 'up', 'j')
        if not self.parser.has_option('keybindings', 'down'):
            self.parser.set('keybindings', 'down', 'k')
        if not self.parser.has_option('keybindings', 'refresh'):
            self.parser.set('keybindings', 'refresh', 'r')
        if not self.parser.has_option('keybindings', 'show_comments_link'):
            self.parser.set('keybindings', 'show_comments_link', 'c')
        if not self.parser.has_option('keybindings', 'open_comments_link'):
            self.parser.set('keybindings', 'open_comments_link', 'C')
        if not self.parser.has_option('keybindings', 'show_story_link'):
            self.parser.set('keybindings', 'show_story_link', 's')
        if not self.parser.has_option('keybindings', 'open_story_link'):
            self.parser.set('keybindings', 'open_story_link', 'S,enter')
        if not self.parser.has_option('keybindings', 'show_submitter_link'):
            self.parser.set('keybindings', 'show_submitter_link', 'u')
        if not self.parser.has_option('keybindings', 'open_submitter_link'):
            self.parser.set('keybindings', 'open_submitter_link', 'U')
        if not self.parser.has_option('keybindings', 'reload_config'):
            self.parser.set('keybindings', 'reload_config', 'ctrl R')
        if not self.parser.has_option('keybindings', 'newest_stories'):
            self.parser.set('keybindings', 'newest_stories', 'n')
        if not self.parser.has_option('keybindings', 'top_stories'):
            self.parser.set('keybindings', 'top_stories', 't')
        if not self.parser.has_option('keybindings', 'best_stories'):
            self.parser.set('keybindings', 'best_stories', 'b')

        # Paths
        if not self.parser.has_section('settings'):
            self.parser.add_section('settings')

        if not self.parser.has_option('settings', 'extra_page'):
            self.parser.set('settings', 'extra_page', '1')

        if not self.parser.has_option('settings', 'cache'):
            self.parser.set(
                'settings',
                'cache',
                os.path.join(os.environ.get('HOME', './'), '.pyhn', 'cache'))
        if not self.parser.has_option('settings', 'cache_age'):
            self.parser.set('settings', 'cache_age', "5")
        if not self.parser.has_option('settings', 'browser_cmd'):
            self.parser.set('settings', 'browser_cmd', '__default__')

        # Colors
        if not self.parser.has_section('colors'):
            self.parser.add_section('colors')

        if not self.parser.has_option('colors', 'body'):
            self.parser.set('colors', 'body', 'default||standout')
        if not self.parser.has_option('colors', 'focus'):
            self.parser.set('colors', 'focus', 'black|light green|underline')
        if not self.parser.has_option('colors', 'footer'):
            self.parser.set('colors', 'footer', 'black|light gray')
        if not self.parser.has_option('colors', 'footer-error'):
            self.parser.set('colors', 'footer-error', 'dark red,bold|light gray')
        if not self.parser.has_option('colors', 'header'):
            self.parser.set('colors', 'header', 'dark gray,bold|white|')
        if not self.parser.has_option('colors', 'title'):
            self.parser.set('colors', 'title', 'dark red,bold|light gray')
        if not self.parser.has_option('colors', 'help'):
            self.parser.set('colors', 'help', 'black|dark cyan|standout')

        if not os.path.exists(self.config_path):
            self.parser.write(open(self.config_path, 'w'))

    def get_palette(self):
        palette = []
        for item in self.parser.items('colors'):
            name = item[0]
            settings = item[1]
            foreground = ""
            background = ""
            monochrome = ""
            if len(settings.split('|')) == 3:
                foreground = settings.split('|')[0]
                background = settings.split('|')[1]
                monochrome = settings.split('|')[2]
            elif len(settings.split('|')) == 2:
                foreground = settings.split('|')[0]
                background = settings.split('|')[1]
            elif len(settings.split('|')) == 1:
                foreground = settings.split('|')[0]

            palette.append((name, foreground, background, monochrome))
        return palette

########NEW FILE########
__FILENAME__ = gui
# -*- coding: utf-8 -*-
import sys
import isit
import urwid
import subprocess
import threading

if isit.py3:
    from urllib.parse import urlparse
else:
    from urlparse import urlparse

from pyhn.config import Config
from pyhn.popup import Popup
from pyhn import __version__ as VERSION


class ItemWidget(urwid.WidgetWrap):
    """ Widget of listbox, represent each story """
    def __init__(self, story):
        self.story = story
        self.number = story.number
        self.title = story.title
        self.url = story.URL
        self.domain = urlparse(story.domain).netloc
        self.submitter = story.submitter
        self.submitter_url = story.submitterURL
        self.comment_count = story.commentCount
        self.comments_url = story.commentsURL
        self.score = story.score
        self.published_time = story.publishedTime

        if self.submitter == -1:
            self.submitter = "-"
            self.submitter_url = -1

        if self.score == -1:
            self.score = "-"

        if self.comment_count == -1:
            self.comment_count = "-"
            self.comments_url = -1

        self.item = [
            ('fixed', 4, urwid.Padding(urwid.AttrWrap(
                urwid.Text("%s:" % self.number, align="right"),
                'body',
                'focus'))),
            urwid.AttrWrap(urwid.Text('%s (%s)' % (self.title, self.domain)), 'body', 'focus'),
            ('fixed', 5, urwid.Padding(urwid.AttrWrap(
                urwid.Text(str(self.score), align="right"), 'body', 'focus'))),
            ('fixed', 8, urwid.Padding(urwid.AttrWrap(
                urwid.Text(str(self.comment_count), align="right"),
                'body',
                'focus'))),
        ]
        w = urwid.Columns(self.item, focus_column=1, dividechars=1)
        self.__super.__init__(w)

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class HNGui(object):
    """ The Pyhn Gui object """
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.already_build = False
        self.on_comments = False
        self.which = "top"

        self.config = Config()
        self.palette = self.config.get_palette()

    def main(self):
        """
        Main Gui function which create Ui object,
        build interface and run the loop
        """
        self.ui = urwid.raw_display.Screen()
        self.ui.register_palette(self.palette)
        self.build_interface()
        self.ui.run_wrapper(self.run)

    def build_help(self):
        """ Fetch all key bindings and build help message """
        self.bindings = {}
        self.help_msg = []
        self.help_msg.append(urwid.AttrWrap(urwid.Text('\n Key bindings \n'), 'title'))
        self.help_msg.append(urwid.AttrWrap(urwid.Text(''), 'help'))
        for binding in self.config.parser.items('keybindings'):
            self.bindings[binding[0]] = binding[1]
            line = urwid.AttrWrap(
                urwid.Text(' %s: %s ' % (binding[1], binding[0].replace('_', ' '))),
                'help')
            self.help_msg.append(line)
        self.help_msg.append(urwid.AttrWrap(urwid.Text(''), 'help'))
        self.help_msg.append(urwid.AttrWrap(
            urwid.Text(' Thanks for using Pyhn %s! ' % VERSION, align='center'),
            'title'))
        self.help_msg.append(urwid.AttrWrap(urwid.Text(''), 'help'))
        self.help_msg.append(urwid.AttrWrap(urwid.Text(' Author : socketubs '), 'help'))
        self.help_msg.append(urwid.AttrWrap(
            urwid.Text(' Code   : https://github.com/socketubs/pyhn '),
            'help'))
        self.help_msg.append(urwid.AttrWrap(
            urwid.Text(' Website: http://socketubs.org '),
            'help'))
        self.help_msg.append(urwid.AttrWrap(urwid.Text(''), 'help'))
        self.help_msg.append(urwid.AttrWrap(urwid.Text(''), 'help'))
        self.help_msg.append(urwid.AttrWrap(urwid.Text(''), 'help'))

        self.help = Popup(self.help_msg, ('help', 'help'), (0, 1), self.view)

    def build_interface(self):
        """
        Build interface, refresh cache if needed, update stories listbox, create
        header, footer, view and the loop.
        """
        if self.cache_manager.is_outdated():
            self.cache_manager.refresh()

        self.stories = self.cache_manager.get_stories()
        self.update_stories(self.stories)
        self.header_content = [
            ('fixed', 4, urwid.Padding(urwid.AttrWrap(urwid.Text(' N°'), 'header'))),
            urwid.AttrWrap(urwid.Text('TOP STORIES', align="center"), 'title'),
            ('fixed', 5, urwid.Padding(urwid.AttrWrap(urwid.Text('SCORE'), 'header'))),
            ('fixed', 8, urwid.Padding(urwid.AttrWrap(urwid.Text('COMMENTS'), 'header')))]

        self.header = urwid.Columns(self.header_content, dividechars=1)
        self.footer = urwid.AttrMap(
            urwid.Text(
                'Welcome in pyhn by socketubs (https://github.com/socketubs/pyhn)',
                align='center'),
            'footer')

        self.view = urwid.Frame(
            urwid.AttrWrap(self.listbox, 'body'), header=self.header, footer=self.footer)
        self.loop = urwid.MainLoop(
            self.view,
            self.palette,
            screen=self.ui,
            handle_mouse=False,
            unhandled_input=self.keystroke)

        self.build_help()
        self.already_build = True

    def set_help(self):
        """ Set help msg in footer """
        self.view.set_footer(
            urwid.AttrWrap(urwid.Text(self.help, align="center"), 'help'))

    def set_footer(self, msg, style="normal"):
        """ Set centered footer message """
        if style == "normal":
            self.footer = urwid.AttrWrap(urwid.Text(msg), 'footer')
            self.view.set_footer(self.footer)
        elif style == "error":
            self.footer = urwid.AttrWrap(urwid.Text(msg), 'footer-error')
            self.view.set_footer(self.footer)

    def set_header(self, msg):
        """ Set header story message """
        self.header_content[1] = urwid.AttrWrap(urwid.Text(msg, align="center"), 'title')
        self.view.set_header(urwid.Columns(self.header_content, dividechars=1))

    def keystroke(self, input):
        """ All key bindings are computed here """
        # QUIT
        if input in ('q', 'Q'):
            raise urwid.ExitMainLoop()
        # LINKS
        if input in self.bindings['open_comments_link'].split(','):
            if self.listbox.get_focus()[0].comments_url == -1:
                self.set_footer('No comments')
            else:
                if not self.on_comments:
                    self.show_comments(self.listbox.get_focus()[0])
                    self.on_comments = True
                else:
                    self.update_stories(self.cache_manager.get_stories(self.which))
                    self.on_comments = False
                self.open_webbrowser(self.listbox.get_focus()[0].comments_url)
        if input in self.bindings['show_comments_link'].split(','):
            if self.listbox.get_focus()[0].comments_url == -1:
                self.set_footer('No comments')
            else:
                self.set_footer(self.listbox.get_focus()[0].comments_url)
        if input in self.bindings['open_story_link'].split(','):
            self.open_webbrowser(self.listbox.get_focus()[0].url)
        if input in self.bindings['show_story_link'].split(','):
            self.set_footer(self.listbox.get_focus()[0].url)
        if input in self.bindings['open_submitter_link'].split(','):
            if self.listbox.get_focus()[0].submitter_url == -1:
                self.set_footer('Anonymous submitter')
            else:
                self.open_webbrowser(self.listbox.get_focus()[0].submitter_url)
        if input in self.bindings['show_submitter_link'].split(','):
            if self.listbox.get_focus()[0].submitter_url == -1:
                self.set_footer('Anonymous submitter')
            else:
                self.set_footer(self.listbox.get_focus()[0].submitter_url)
        # MOVEMENTS
        if input in self.bindings['down'].split(','):
            if self.listbox.focus_position - 1 in self.walker.positions():
                self.listbox.set_focus(
                    self.walker.prev_position(self.listbox.focus_position))
        if input in self.bindings['up'].split(','):
            if self.listbox.focus_position + 1 in self.walker.positions():
                self.listbox.set_focus(
                    self.walker.next_position(self.listbox.focus_position))
        if input in self.bindings['page_up'].split(','):
            self.listbox._keypress_page_up(self.ui.get_cols_rows())
        if input in self.bindings['page_down'].split(','):
            self.listbox._keypress_page_down(self.ui.get_cols_rows())
        if input in self.bindings['first_story'].split(','):
            self.listbox.set_focus(self.walker.positions()[0])
        if input in self.bindings['last_story'].split(','):
            self.listbox.set_focus(self.walker.positions()[-1])
        # STORIES
        if input in self.bindings['newest_stories'].split(','):
            threading.Thread(
                None,
                self.async_refresher,
                None,
                ('newest', 'NEWEST STORIES'),
                {}).start()
        if input in self.bindings['top_stories'].split(','):
            threading.Thread(
                None,
                self.async_refresher,
                None,
                ('top', 'TOP STORIES'),
                {}).start()
        if input in self.bindings['best_stories'].split(','):
            self.set_footer('Syncing best stories...')
            threading.Thread(
                None, self.async_refresher, None, ('best', 'BEST STORIES'), {}).start()
        # OTHERS
        if input in self.bindings['refresh'].split(','):
            self.set_footer('Refreshing new stories...')
            threading.Thread(None, self.async_refresher, None, (), {}).start()
        if input in self.bindings['reload_config'].split(','):
            self.reload_config()
        if input in ('h', 'H', '?'):
            keys = True
            while True:
                if keys:
                    self.ui.draw_screen(
                        self.ui.get_cols_rows(),
                        self.help.render(self.ui.get_cols_rows(), True))
                    keys = self.ui.get_input()
                    if 'h' or 'H' or '?' or 'escape' in keys:
                        break

    def async_refresher(self, which=None, header=None):
        if which is None:
            which = self.which
        if self.cache_manager.is_outdated(which):
            self.cache_manager.refresh(which)
        stories = self.cache_manager.get_stories(which)
        self.update_stories(stories)
        if header is not None:
            self.set_header(header)
            self.which = which
        self.loop.draw_screen()

    def update_stories(self, stories):
        """ Reload listbox and walker with new stories """
        items = []
        for story in stories:
            items.append(ItemWidget(story))

        if self.already_build:
            self.walker[:] = items
            self.update()
        else:
            self.walker = urwid.SimpleListWalker(items)
            self.listbox = urwid.ListBox(self.walker)

    def show_comments(self, story):
        #items = []
        pass

    def open_webbrowser(self, url):
        """ Handle url and open sub process with web browser """
        if self.config.parser.get('settings', 'browser_cmd') == "__default__":
            python_bin = sys.executable
            subprocess.Popen(
                [python_bin, '-m', 'webbrowser', '-t', url],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        else:
            cmd = self.config.parser.get('settings', 'browser_cmd')
            try:
                p = subprocess.Popen(
                    cmd.replace('__url__', url),
                    shell=True,
                    close_fds=True,
                    stderr=subprocess.PIPE)

                returncode = p.wait()
            except KeyboardInterrupt:
                stderr = "User keyboard interrupt detected!"
                self.set_footer(stderr, style="error")
                return
            if returncode > 0:
                stderr = p.communicate()[1]
                self.set_footer("%s" % stderr, style="error")

    def update(self):
        """ Update footer about focus story """
        focus = self.listbox.get_focus()[0]
        if focus.submitter == "":
            msg = "submitted %s" % focus.published_time
        else:
            msg = "submitted %s by %s" % (focus.published_time, focus.submitter)

        self.set_footer(msg)

    def reload_config(self):
        """
        Create new Config object, reload colors, refresh cache
        if needed and redraw screen.
        """
        self.set_footer('Reloading configuration')
        self.config = Config()
        self.build_help()
        self.palette = self.config.get_palette()
        self.build_interface()
        self.loop.draw_screen()
        self.set_footer('Configuration file reloaded!')

        if self.config.parser.get('settings', 'cache') != self.cache_manager.cache_path:
            self.cache_manager.cache_path = self.config.parser.get('settings', 'cache')

    def run(self):
        """ Run the loop """
        urwid.connect_signal(self.walker, 'modified', self.update)

        try:
            self.loop.run()
        except KeyboardInterrupt:
            urwid.ExitMainLoop()

########NEW FILE########
__FILENAME__ = hnapi
"""
hn-api is a simple, ad-hoc Python API for Hacker News.
======================================================

hn-api is released under the Simplified BSD License:

Copyright (c) 2010, Scott Jackson
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are
permitted provided that the following conditions are met:

   1. Redistributions of source code must retain the above copyright notice, this list of
      conditions and the following disclaimer.

   2. Redistributions in binary form must reproduce the above copyright notice, this list
      of conditions and the following disclaimer in the documentation and/or other materials
      provided with the distribution.

THIS SOFTWARE IS PROVIDED BY SCOTT JACKSON ``AS IS'' AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL SCOTT JACKSON OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The views and conclusions contained in the software and documentation are those of the
authors and should not be interpreted as representing official policies, either expressed
or implied, of Scott Jackson.


"""
import re
import isit
import json

from bs4 import BeautifulSoup

if isit.py3:
    import urllib.request
    import urllib.parse
    from urllib.error import URLError
    from urllib.parse import urljoin
else:
    import urllib2
    from urllib2 import URLError
    from urlparse import urljoin


class HNException(Exception):
    """
    HNException is exactly the same as a plain Python Exception.

    The HNException class exists solely so that you can identify
    errors that come from HN as opposed to from your application.
    """
    pass


class HackerNewsAPI:
    """
    The class for slicing and dicing the HTML and turning it into HackerNewsStory objects.
    """
    numberOfStoriesOnFrontPage = 0

    def getSource(self, url):
        """
        Returns the HTML source code for a URL.
        """
        headers = {
            'User-Agent': 'Pyhn (Hacker news command line client) - https://github.com/socketubs/pyhn'}
        try:
            if isit.py3:
                r = urllib.request.Request(url, b'', headers)
                f = urllib.request.urlopen(r)
            else:
                r = urllib2.Request(url, '', headers)
                f = urllib2.urlopen(r)

            source = f.read()
            f.close()
            return source.decode('utf-8')
        except URLError:
            raise
            raise HNException("Error getting source from " + url + ". Your internet connection may have something funny going on, or you could be behind a proxy.")

    def getStoryNumber(self, source):
        """
        Parses HTML and returns the number of a story.
        """
        numberStart = source.find('>') + 1
        numberEnd = source.find('.')
        return int(source[numberStart:numberEnd])

    def getStoryURL(self, source):
        """
        Gets the URL of a story.
        """
        URLStart = source.find('href="') + 6
        URLEnd = source.find('">', URLStart)
        url = source[URLStart:URLEnd]
        # Check for "Ask HN" links.
        if url[0:4] == "item":  # "Ask HN" links start with "item".
            url = "https://news.ycombinator.com/" + url

        # Change "&amp;" to "&"
        url = url.replace("&amp;", "&")

        # Remove 'rel="nofollow' from the end of links, since they were causing some bugs.
        if url[len(url) - 13:] == "rel=\"nofollow":
            url = url[:len(url) - 13]

        # Weird hack for URLs that end in '" '. Consider removing later if it causes any problems.
        if url[len(url) - 2:] == "\" ":
            url = url[:len(url) - 2]
        return url

    def getStoryDomain(self, source):
        """
        Gets the domain of a story.
        """
        domainStart = source.find('comhead">') + 10
        domainEnd = source.find('</span>')
        domain = source[domainStart:domainEnd]
        # Check for "Ask HN" links.
        if domain[0] == '=':
            return "https://news.ycombinator.com"
        return "https://" + domain[1:len(domain) - 2]

    def getStoryTitle(self, source):
        """
        Gets the title of a story.
        """
        titleStart = source.find('>', source.find('>') + 1) + 1
        titleEnd = source.find('</a>')
        title = source[titleStart:titleEnd]
        title = title.lstrip()  # Strip trailing whitespace characters.
        return title

    def getStoryScore(self, source):
        """
        Gets the score of a story.
        """
        scoreStart = source.find('>', source.find('>') + 1) + 1
        scoreEnd = source.find(' ', scoreStart)
        score = source[scoreStart:scoreEnd]
        if not score.isdigit():
            return -1
        return int(score)

    def getSubmitter(self, source):
        """
        Gets the HN username of the person that submitted a story.
        """
        submitterStart = source.find('user?id=')
        realSubmitterStart = source.find('=', submitterStart) + 1
        submitterEnd = source.find('"', realSubmitterStart)
        return source[realSubmitterStart:submitterEnd]

    def getCommentCount(self, source):
        """
        Gets the comment count of a story.
        """
        commentStart = source.find('item?id=')
        commentCountStart = source.find('>', commentStart) + 1
        commentEnd = source.find('</a>', commentStart)
        commentCountString = source[commentCountStart:commentEnd]
        if commentCountString == "discuss":
            return 0
        elif commentCountString == "":
            return -1
        else:
            commentCountString = commentCountString.split(' ')[0]
            try:
                return int(commentCountString)
            except ValueError:
                return -1

    def getPublishedTime(self, source):
        """
        Gets the published time ago
        """
        p = re.compile(r'\d{1,} (minutes|minute|hours|hour|day|days) ago')
        results = p.search(source)
        return results.group()

    def getHNID(self, source):
        """
        Gets the Hacker News ID of a story.
        """
        idPrefix = 'score_'
        urlStart = source.find(idPrefix) + len(idPrefix)
        if urlStart <= len(idPrefix):
            return -1
        urlEnd = source.find('"', urlStart)
        return int(source[urlStart:urlEnd])

    def getCommentsURL(self, source):
        """
        Gets the comment URL of a story.
        """
        return "https://news.ycombinator.com/item?id=" + str(self.getHNID(source))

    def getStories(self, source):
        """
        Looks at source, makes stories from it, returns the stories.
        """
        """ <td align=right valign=top class="title">31.</td> """
        #self.numberOfStoriesOnFrontPage = source.count("span id=score")
        self.numberOfStoriesOnFrontPage = 30

        # Create the empty stories.
        newsStories = []
        for i in range(0, self.numberOfStoriesOnFrontPage):
            story = HackerNewsStory()
            newsStories.append(story)

        soup = BeautifulSoup(source)
        # Gives URLs, Domains and titles.
        story_details = soup.findAll("td", {"class": "title"})
        # Gives score, submitter, comment count and comment URL.
        story_other_details = soup.findAll("td", {"class": "subtext"})

        # Get story numbers.
        storyNumbers = []
        for i in range(0, len(story_details) - 1, 2):
            story = str(story_details[i])  # otherwise, story_details[i] is a BeautifulSoup-defined object.
            storyNumber = self.getStoryNumber(story)
            storyNumbers.append(storyNumber)

        storyURLs = []
        storyDomains = []
        storyTitles = []
        storyScores = []
        storySubmitters = []
        storyCommentCounts = []
        storyCommentURLs = []
        storyPublishedTime = []
        storyIDs = []

        for i in range(1, len(story_details), 2):  # Every second cell contains a story.
            story = str(story_details[i])
            storyURLs.append(self.getStoryURL(story))
            storyDomains.append(self.getStoryDomain(story))
            storyTitles.append(self.getStoryTitle(story))

        for s in story_other_details:
            story = str(s)
            storyScores.append(self.getStoryScore(story))
            storySubmitters.append(self.getSubmitter(story))
            storyCommentCounts.append(self.getCommentCount(story))
            storyCommentURLs.append(self.getCommentsURL(story))
            storyPublishedTime.append(self.getPublishedTime(story))
            storyIDs.append(self.getHNID(story))

        # Associate the values with our newsStories.
        for i in range(0, self.numberOfStoriesOnFrontPage):
            newsStories[i].number = storyNumbers[i]
            newsStories[i].URL = storyURLs[i]
            newsStories[i].domain = storyDomains[i]
            newsStories[i].title = storyTitles[i]
            newsStories[i].score = storyScores[i]
            newsStories[i].submitter = storySubmitters[i]
            newsStories[i].submitterURL = "https://news.ycombinator.com/user?id=" + storySubmitters[i]
            newsStories[i].commentCount = storyCommentCounts[i]
            newsStories[i].commentsURL = storyCommentURLs[i]
            newsStories[i].publishedTime = storyPublishedTime[i]
            newsStories[i].id = storyIDs[i]

            if newsStories[i].id < 0:
                newsStories[i].URL.find('item?id=') + 8
                newsStories[i].commentsURL = ''
                newsStories[i].submitter = -1
                newsStories[i].submitterURL = -1

        return newsStories

    ##### End of internal methods. #####

    # The following methods could be turned into one method with
    # an argument that switches which page to get stories from,
    # but I thought it would be simplest if I kept the methods
    # separate.

    def getTopStories(self, extra_page=1):
        """
        Gets the top stories from Hacker News.
        """
        stories = []

        source_new1 = self.getSource("https://news.ycombinator.com/news")
        source_new2 = self.getSource("https://news.ycombinator.com/news2")
        source_latest = source_new2

        stories += self.getStories(source_new1)
        stories += self.getStories(source_new2)

        for i in range(extra_page):
            source_latest = self.getSource(self.getMoreLink(source_latest))
            stories += self.getStories(source_latest)

        return stories

    def getNewestStories(self, extra_page=1):
        """
        Gets the newest stories from Hacker News.
        """
        stories = []

        source_latest = self.getSource("https://news.ycombinator.com/newest")
        stories += self.getStories(source_latest)

        for i in range(extra_page):
            source_latest = self.getSource(self.getMoreLink(source_latest))
            stories += self.getStories(source_latest)

        return stories

    def getBestStories(self, extra_page=1):
        """
        Gets the "best" stories from Hacker News.
        """
        stories = []

        source_latest = self.getSource("https://news.ycombinator.com/best")
        stories += self.getStories(source_latest)

        for i in range(extra_page):
            source_latest = self.getSource(self.getMoreLink(source_latest))
            stories += self.getStories(source_latest)

        return stories

    def getPageStories(self, pageId):
        """
        Gets the pageId stories from Hacker News.
        """
        source = self.getSource("https://news.ycombinator.com/x?fnid=%s" % pageId)
        stories = self.getStories(source)
        return stories

    def getMoreLink(self, source):
        soup = BeautifulSoup(source)
        more_a = soup.findAll("a", {"rel": "nofollow"}, text="More")
        if more_a:
            return urljoin('https://news.ycombinator.com/', more_a[0]['href'])
        return None


class HackerNewsStory:
    """
    A class representing a story on Hacker News.
    """
    id = 0       # The Hacker News ID of a story.
    number = -1  # What rank the story is on HN.
    title = ""   # The title of the story.
    domain = ""  # The website the story is from.
    URL = ""     # The URL of the story.
    score = -1   # Current score of the story.
    submitter = ""       # The person that submitted the story.
    commentCount = -1    # How many comments the story has.
    commentsURL = ""     # The HN link for commenting (and upmodding).
    publishedTime = ""   # The time sinc story was published

    def getComments(self):
        url = 'http://hndroidapi.appspot.com/nestedcomments/format/json/id/%s' % self.id
        try:
            if isit.py3:
                f = urllib.request.urlopen(url)
            else:
                f = urllib2.urlopen(url)

            source = f.read()
            f.close()
            self.comments = json.loads(source.decode('utf-8'))['items']
            return self.comments
        except URLError:
            raise HNException("Error getting source from " + url + ". Your internet connection may have something funny going on, or you could be behind a proxy.")

    def printDetails(self):
        """
        Prints details of the story.
        """
        print(str(self.number) + ": " + self.title)
        print("URL: " + self.URL)
        print("domain: " + self.domain)
        print("score: " + str(self.score) + " points")
        print("submitted by: " + self.submitter)
        print("sinc %s" + self.publishedTime)
        print("of comments: " + str(self.commentCount))
        print("'discuss' URL: " + self.commentsURL)
        print("HN ID: " + str(self.id))
        print(" ")


class HackerNewsUser:
    """
    A class representing a user on Hacker News.
    """
    karma = -10000  # Default value. I don't think anyone really has -10000 karma.
    name = ""       # The user's HN username.
    userPageURL = ""     # The URL of the user's 'user' page.
    threadsPageURL = ""  # The URL of the user's 'threads' page.

    def __init__(self, username):
        """
        Constructor for the user class.
        """
        self.name = username
        self.userPageURL = "https://news.ycombinator.com/user?id=" + self.name
        self.threadsPageURL = "https://news.ycombinator.com/threads?id=" + self.name
        self.refreshKarma()

    def refreshKarma(self):
        """
        Gets the karma count of a user from the source of their 'user' page.
        """
        hn = HackerNewsAPI()
        source = hn.getSource(self.userPageURL)
        karmaStart = source.find('<td valign=top>karma:</td><td>') + 30
        karmaEnd = source.find('</td>', karmaStart)
        karma = source[karmaStart:karmaEnd]
        if karma is not '':
            self.karma = int(karma)
        else:
            raise HNException("Error getting karma for user " + self.name)

########NEW FILE########
__FILENAME__ = popup
# -*- coding: utf-8 -*-
import urwid


class Popup(urwid.WidgetWrap):
    """
    Creates a popup menu on top of another BoxWidget.

    Attributes:

    selected -- Contains the item the user has selected by pressing <RETURN>,
                or None if nothing has been selected.
    """

    selected = None

    def __init__(self, menu_list, attr, pos, body):
        """
        menu_list -- a list of strings with the menu entries
        attr -- a tuple (background, active_item) of attributes
        pos -- a tuple (x, y), position of the menu widget
        body -- widget displayed beneath the message widget
        """

        content = [w for w in menu_list]

        # Calculate width and height of the menu widget:
        height = len(menu_list)
        width = 0
        for entry in menu_list:
            if len(entry.original_widget.text) > width:
                width = len(entry.original_widget.text)

        # Create the ListBox widget and put it on top of body:
        self._listbox = urwid.AttrWrap(urwid.ListBox(content), attr[0])
        overlay = urwid.Overlay(self._listbox, body, 'center',
                                width + 2, 'middle', height)

        urwid.WidgetWrap.__init__(self, overlay)

    def keypress(self, size, key):
        """
        <RETURN> key selects an item, other keys will be passed to
        the ListBox widget.
        """

        if key == "enter":
            (widget, foo) = self._listbox.get_focus()
            (text, foo) = widget.get_text()
            self.selected = text[1:]  # Get rid of the leading space...
        else:
            return self._listbox.keypress(size, key)

########NEW FILE########
__FILENAME__ = get_comments
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import json
from hnapi import HackerNewsAPI

hn = HackerNewsAPI()
stories = hn.getTopStories()

story = stories[0]
if not os.path.exists('comments.data'):
    comments = story.getComments()
    open('comments.data', 'w').write(json.dumps(comments))
else:
    comments = json.load(open('comments.data'))


########NEW FILE########
__FILENAME__ = treesample
#!/usr/bin/python
#
# Trivial data browser
#    This version:
#      Copyright (C) 2010  Rob Lanphier
#    Derived from browse.py in urwid distribution
#      Copyright (C) 2004-2007  Ian Ward
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Urwid web site: http://excess.org/urwid/

"""
Urwid example lazy directory browser / tree view

Features:
- custom selectable widgets for files and directories
- custom message widgets to identify access errors and empty directories
- custom list walker for displaying widgets in a tree fashion
"""

import urwid
import os
import json
from pprint import pprint


class ExampleTreeWidget(urwid.TreeWidget):
    """ Display widget for leaf nodes """
    def get_display_text(self):
        return self.get_node().get_value()['name']


class ExampleNode(urwid.TreeNode):
    """ Data storage object for leaf nodes """
    def load_widget(self):
        return ExampleTreeWidget(self)


class ExampleParentNode(urwid.ParentNode):
    """ Data storage object for interior/parent nodes """
    def load_widget(self):
        return ExampleTreeWidget(self)

    def load_child_keys(self):
        data = self.get_value()
        return range(len(data['children']))

    def load_child_node(self, key):
        """Return either an ExampleNode or ExampleParentNode"""
        childdata = self.get_value()['children'][key]
        childdepth = self.get_depth() + 1
        if 'children' in childdata:
            childclass = ExampleParentNode
        else:
            childclass = ExampleNode
        return childclass(childdata, parent=self, key=key, depth=childdepth)


class ExampleTreeBrowser:
    palette = [
        ('body', 'black', 'light gray'),
        ('focus', 'light gray', 'dark blue', 'standout'),
        ('head', 'yellow', 'black', 'standout'),
        ('foot', 'light gray', 'black'),
        ('key', 'light cyan', 'black','underline'),
        ('title', 'white', 'black', 'bold'),
        ('flag', 'dark gray', 'light gray'),
        ('error', 'dark red', 'light gray'),
        ]
    
    footer_text = [
        ('title', "Example Data Browser"), "    ",
        ('key', "UP"), ",", ('key', "DOWN"), ",",
        ('key', "PAGE UP"), ",", ('key', "PAGE DOWN"),
        "  ",
        ('key', "+"), ",",
        ('key', "-"), "  ",
        ('key', "LEFT"), "  ",
        ('key', "HOME"), "  ", 
        ('key', "END"), "  ",
        ('key', "Q"),
        ]

    def __init__(self, data=None):
        self.topnode = ExampleParentNode(data)
        self.listbox = urwid.TreeListBox(urwid.TreeWalker(self.topnode))
        self.listbox.offset_rows = 1
        self.header = urwid.Text( "" )
        self.footer = urwid.AttrWrap( urwid.Text( self.footer_text ),
            'foot')
        self.view = urwid.Frame( 
            urwid.AttrWrap( self.listbox, 'body' ), 
            header=urwid.AttrWrap(self.header, 'head' ), 
            footer=self.footer )

    def main(self):
        """Run the program."""
        
        self.loop = urwid.MainLoop(self.view, self.palette,
            unhandled_input=self.unhandled_input)
        self.loop.run()

    def unhandled_input(self, k):
        if k in ('q','Q'):
            raise urwid.ExitMainLoop()


def get_example_tree():
    """ generate a quick 100 leaf tree for demo purposes """
    f = open("comments.data", "r").read()
    info = json.loads(f)[0]
    s = "%s %s\n%s\n" % (info["username"], info["time"], info["comment"])    
    retval = {"name":s, "children": []}
    for i in range(len(info["children"])): 
        l = get_example_tree_recursion(info["children"][i])
        retval["children"].append(l)
    return retval

def get_example_tree_recursion(info):
    s = "%s %s\n%s\n" % (info["username"], info["time"], info["comment"])
    n = {"name": s, "children": []}
    for j in range(len(info["children"])):
            l = get_example_tree_recursion(info["children"][j])
            n["children"].append(l)
    return n


def main():
    sample = get_example_tree()
    ExampleTreeBrowser(sample).main()


if __name__=="__main__": 
    main()


########NEW FILE########
