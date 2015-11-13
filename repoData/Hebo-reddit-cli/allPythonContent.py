__FILENAME__ = pages
import urllib, urllib2
import json
import re, htmlentitydefs #html escaping

def smart_truncate(content, length=100, suffix='...'):
    """truncate on word boundaries"""
    if len(content) <= length:
        return content
    else:
        return ' '.join(content[:length+1].split(' ')[0:-1]) + suffix


def unescape(text):
    """Remove HTML or XML character references and entities from a text string"""
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)
        
        
class Story:
    """holds json data of a single reddit story"""
    def __init__(self, object):
        """create story from dict object representation"""
        assert isinstance(object, dict), "json object is not a dict: %s" % type(object)
        self.object = object
        
    def __getattr__(self, name):
        """pull elements directly from the stored object"""
        if self.object.has_key(name):
            return self.object.get(name)
        else:
            raise AttributeError, name

    def format_lines(self, length):
        """prepare story as a two-string tuple of correct length"""
        line1 = "{0}".format(unescape(
                            smart_truncate(self.title.encode('utf-8'), length=length-3)
                            ))
        line2 = "{0} points   {1} comments   {2}   {3}".format(
                                    self.score,
                                    self.num_comments,
                                    self.domain,
                                    "/r/" + self.subreddit,
                                    )
        return (line1, line2[:length])


class BadSubredditError(Exception):
    pass

class Navigation:
    """handles the navigation properties of a single page"""
    def __init__(self, next, count, stack):
        self.next = next
        self.count = count
        self.stack = stack # store id of the last story on each page in a stack

# Cheating by using classmethod decorator to semi-emulate a singleton pattern
class RedditHandler:
    """handles user credentials and downloading a page"""
    # Special thanks to PhillipTaylor's "reddit_monitor" for the login code
    def __init__(self):

        #Because the login is an ajax post before we need cookies.
        #That's what made this code annoying to write.
        #This code should work against either cookielib or ClientCookie depending on
        #which ever one you have.
        try:
            import cookielib

            #Were taking references to functions / objects here
            #so later on we don't need to worry about which actual
            #import we used.
            self.Request = urllib2.Request
            self.urlopen = urllib2.urlopen

            cookie_jar = cookielib.LWPCookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie_jar))
            urllib2.install_opener(opener)

        except ImportError:
            try:
                import ClientCookie

                self.Request = ClientCookie.Request
                self.urlopen = ClientCookie.urlopen

                cookie_jar = ClientCookie.LWPCookieJar()
                opener = ClientCookie.build_opener(ClientCookie.HTTPCookieProcessor(cookie_jar))

            except ImportError:
                raise ImportError("""This code is dependent on either
                         \'cookielib\' or \'ClientCookie\'
                         #and you have neither.
                        """)

        self.user = None

    def login(self, user, passwd):

        params = urllib.urlencode({
            'id' : '#login_login-main',
            'op' : 'login-main',
            'passwd' : passwd,
            'user' : user
        })

        try:
            req = self.Request("http://www.reddit.com/post/login", params)
            result = self.urlopen(req).read()

            if result.find("logged: false") != -1:
                return False
            
        except Exception, e:
            print "Error: %s", e.message
            return False
        
        self.user = user
        return True
            
    def download_stories(self, subreddit, nav=None, direction=None):
        """download json from reddit and return list of stories"""
        if subreddit is None: 
            url = "http://www.reddit.com/.json"
        else: 
            url = "http://www.reddit.com/r/" + subreddit + "/.json"
    
        if nav is None:
            nav = Navigation(None, 0, ["start"])
    
        if not direction is None:
            if direction == "prev":
                # the end of the stack marks the start of the current page,
                # so we discard it and get a reference to the last page
                if not nav.stack[-1] == "start":
                    nav.count -= 25
                    nav.stack.pop()
                    prev = nav.stack[-1]
                    url += "?count={0}&after={1}".format(nav.count, prev)
            elif direction == "next":
                nav.stack.append(nav.next)
                nav.count += 25
                url += "?count={0}&after={1}".format(nav.count, nav.next)
            else:
                raise Exception, "Bad paging direction given"
        
        stream = None
        json_data = None
        try:
            stream = urllib2.urlopen(url)
            json_data = stream.read()
        except urllib2.HTTPError as err:
            if err.getcode() in (400,404):
                raise BadSubredditError
            else:
                raise
        if json_data == "{error: 404}":
            raise BadSubredditError
        elif re.search(r'/search\?q=', stream.url):
            raise BadSubredditError
        
        stories_raw = json.loads(json_data)
        stories = []
        for i in stories_raw['data']['children']:
            stories.append(Story(i['data']))
    
        # Identifier for last/first story on the page for pagination
        nav.next = stories_raw['data']['after']
        return ( stories, nav )
########NEW FILE########
__FILENAME__ = reddit
import urwid
import webbrowser
import os
from pages import Story, RedditHandler, BadSubredditError, Navigation
from optparse import OptionParser # argparse is 2.7-only

# Main loop is global so MainWindow can update the screen asynchronously
main_loop = None

class Listing(urwid.FlowWidget):
    """contains a single story and manages its events"""
    def __init__(self, story):
        self.story = story
        
    def selectable(self):
        return True
        
    def rows(self, size, focus=False):
        return 2

    def render(self, size, focus=False):
        (maxcol,) = size
        lines = self.story.format_lines(maxcol)
        if focus:
            pass
        # pad lines to column width
        fill = lambda x: x.ljust(maxcol)
        return urwid.TextCanvas(text=list(map(fill, lines)))

    def keypress(self, size, key):
        if key in ('o', 'enter'):
            webbrowser.open(self.story.url)
        elif key == 'O':
            if self.story.domain[:5] == "self.":
                # Lynx renders mobile reddit better
                url = "http://m.reddit.com" + self.story.permalink
            else:
                url = self.story.url
            os.system("lynx -accept_all_cookies " + url)
        elif key == 'h':
            webbrowser.open("http://www.reddit.com" + self.story.permalink)
        elif key == 'l':
            url = "http://m.reddit.com" + self.story.permalink
            os.system("lynx -accept_all_cookies " + url)
        else:
            return key


class MainWindow(object):
    """manages main window elements"""
    def __init__(self):
        # Handles page downloads and cookies                            
        self.handler = RedditHandler()
        self.listings = []
        self.__subreddit = None
        self.nav = None
        self.__load_stories()
        
        # Prep header and footer ui widgets 
        self.__update_header()
        self.footer_content = urwid.Text(('footer', ""), wrap='clip') 
        self.footer = urwid.Padding(self.footer_content, left=1, right=1)
        
        self.frame = urwid.Frame(   self.__get_widget(),
                                    header=self.header, 
                                    footer=self.footer )

    
    def login(self, username, password):
        """attempt to login"""
        login_result = self.handler.login(username, password)
        if login_result:
            self.__update_header()
        return login_result
      
        
    def set_subreddit(self, subreddit):
        """switch subreddits"""
        self.nav = None
        old_subreddit = self.__subreddit
        if subreddit == "fp":
            self.__subreddit = None
        else:
            self.set_status("Loading subreddit: /r/{0}".format(subreddit))
            self.__subreddit = subreddit
        try:
            self.__load_stories()
        except BadSubredditError:
            self.set_status("Error loading subreddit /r/{0}!".format(subreddit))
            self.__subreddit = old_subreddit
            self.__load_stories()
        main_widget = self.__get_widget()
        self.frame.set_body(main_widget)
        self.set_status()
    
    def __update_header(self):
        """set the titlebar to the currently logged in user"""
        if self.handler.user:
            header_text = "[{0}] - reddit-cli - github.com/cev/reddit-cli".format(self.handler.user)
        else:
            header_text = "reddit-cli - github.com/cev/reddit-cli"
        self.header = urwid.Text(('header',
                                header_text),
                                align='center')
        if hasattr(self, 'frame'):
            self.frame.set_header(self.header)                                   
 
    def __load_stories(self, direction=None):
        """load stories from (sub)reddit and store Listings"""
        self.listings = []
        data = self.handler.download_stories(self.__subreddit, self.nav, direction)
        
        self.nav = data[1]
        for s in data[0]:
            current = Listing(s)
            self.listings.append(urwid.Padding(current, left=1, right=1))
        
    def __get_widget(self):
        """return TextBox widget containing all Listings"""
        listings_formatted = self.listings[:]
            
        # Separate stories with blank line & highlight on focus
        for (i, l) in enumerate(listings_formatted):
            filled = urwid.Filler(urwid.AttrMap(l, None, 'focus'))
            listings_formatted[i] = urwid.BoxAdapter(filled, 3)
        listings_formatted.append(urwid.Divider("*"))
        
        self.listings_active = urwid.ListBox(urwid.SimpleListWalker(listings_formatted))
        return self.listings_active
        
    def __format_status(self):
        """format status text for use in footer"""
        if self.__subreddit is None:
            subreddit_text = "/r/front_page"
        else:
            subreddit_text = "/r/" + self.__subreddit
        status = "[{0}] ({1}) ?: help n/m:pagination".format(self.nav.count/25+1, subreddit_text)
        return status
    
    def switch_page(self, direction):
        """load stories from the previous or next page"""
        if direction == "prev":
            self.set_status("(<) Loading...")
            self.__load_stories(direction=direction)
        elif direction == "next":
            self.set_status("(>) Loading...")
            self.__load_stories(direction=direction)
        else:
            raise Exception, "Direction must be 'prev' or 'next'"
        main_widget = self.__get_widget()
        self.frame.set_body(main_widget)
        self.set_status()
    
    def set_status(self, message=None):
        """write message on footer or else default status string"""
        if message is None:
            status = self.__format_status()
        else:
            status = message
        self.footer_content.set_text(('footer', status))
        
        global main_loop
        if not main_loop is None:
            main_loop.draw_screen()
        
    def refresh(self):
        """reload stories in main window"""
        self.set_status("Reloading...")
        self.nav = None
        try:
            self.__load_stories()
        except BadSubredditError:
            self.set_status("Error loading subreddit!")
            return
        main_widget = self.__get_widget()
        self.frame.set_body(main_widget)
        self.set_status()
        
            

def main():
    palette =   [
                ('header', 'dark magenta,bold', 'default'),
                ('footer', 'black', 'light gray'),
                ('textentry', 'white,bold', 'dark red'),
                ('body', 'light gray', 'default'),
                ('focus', 'black', 'dark cyan', 'standout')
                ]

    textentry = urwid.Edit()
    assert textentry.get_text() == ('', []), textentry.get_text()   
    
    parser = OptionParser()
    parser.add_option("-u", "--username")
    parser.add_option("-p", "--password")
    (options, args) = parser.parse_args()
    
    if options.username and not options.password:
        print "If you specify a username, you must also specify a password"
        exit()
        
    print "Loading..."
    
    body = MainWindow()
    if options.username:
        print "[Logging in]"
        if body.login(options.username, options.password):
            print "[Login Successful]"
        else:
            print "[Login Failed]"
            exit()
            
    body.refresh()
        
    def edit_handler(keys, raw):
        """respond to keys while user is editing text"""      
        if keys in (['enter'],[]):
            if keys == ['enter']:
                if textentry.get_text()[0] != '':
                    # We set the footer twice because the first time we
                    # want the updated status text (loading...) to show 
                    # immediately, and the second time as a catch-all
                    body.frame.set_footer(body.footer)
                    body.set_subreddit(textentry.edit_text)
                    textentry.set_edit_text('')
            # Restore original status footer
            body.frame.set_footer(body.footer)
            body.frame.set_focus('body')
            global main_loop
            main_loop.input_filter = input_handler
            return
        return keys
        
    def input_handler(keys, raw):
        """respond to keys not handled by a specific widget"""
        for key in keys:
            if key == 's':
                # Replace status footer wth edit widget
                textentry.set_caption(('textentry', ' [subreddit?] ("fp" for the front page) :>'))
                body.frame.set_footer(urwid.Padding(textentry, left=4))
                body.frame.set_focus('footer')
                global main_loop
                main_loop.input_filter = edit_handler
                return
            elif key in ('j','k'):
                direction = 'down' if key == 'j' else 'up'
                return [direction]
            elif key in ('n','m'):
                direction = 'prev' if key == 'n' else 'next'
                body.switch_page(direction)
            elif key == 'u':
                body.refresh()
            elif key == 'b': # boss mode
                os.system("man python")
            elif key == '?': # help mode
                os.system("less -Ce README.markdown")
            elif key == 'q': # quit
                raise urwid.ExitMainLoop()
            return keys

    # Start ui 
    global main_loop
    main_loop = urwid.MainLoop(body.frame, palette, input_filter=input_handler)
    main_loop.run()

if __name__ == "__main__":
    main()
########NEW FILE########
__FILENAME__ = tests
import unittest
import reddit, pages

class TestMainWindow(unittest.TestCase):
    
    def setUp(self):
        self.main_window = reddit.MainWindow()
        self.main_window.listings = []
        
    def testLoadStories(self):
        """tests type of loaded stories"""
        self.main_window._MainWindow__load_stories()
        self.assertIsInstance(self.main_window.listings, list)
        
    def testSetStatus(self):
        """should create a status of the word 'firefly'"""
        self.main_window.set_status("firefly")
        self.assertEquals(self.main_window.footer_content.text, "firefly")
    
    def testRefresh(self):
        """should populate listings"""
        self.main_window.refresh()
        self.assertNotEquals(self.main_window.listings, [])
    
    def testSubreddit(self):
        """should switch subreddits"""
        self.main_window.refresh()
        before = self.main_window.listings
        self.main_window.set_subreddit("gaming")
        after = self.main_window.listings
        self.assertNotEquals(before, after)
        self.assertEquals(self.main_window._MainWindow__subreddit, "gaming")

        
class TestStory(unittest.TestCase):

    def setUp(self):
        self.main_window = reddit.MainWindow()

    def testFormatLineSize(self):
        """format_lines should adjust line width"""
        self.main_window.listings[0].original_widget.story.object['title'] = "123456789 " * 10
        lines = self.main_window.listings[0].original_widget.story.format_lines(70)
        self.assertLessEqual( len(lines[0]), 70, lines[0])
        lines = self.main_window.listings[0].original_widget.story.format_lines(40)
        self.assertLessEqual( len(lines[0]), 40, lines[0])
        self.assertLessEqual( len(lines[1]), 40, lines[1])
        
class TestNavigation(unittest.TestCase):
    def testNavigationCreation(self):
        """Navigation.__init__() should set attributes properly"""
        nav = pages.Navigation("abc", 0, ["start"])
        self.assertEquals(nav.next, "abc")
        self.assertEquals(nav.count, 0)
        

class TestDownloadStories(unittest.TestCase):
    
    def testBadSubredditError(self):
        """should raise a BadSubredditError"""
        handler = pages.RedditHandler()
        self.assertRaises(pages.BadSubredditError, handler.download_stories, "qwer345g63")
        self.assertRaises(pages.BadSubredditError, handler.download_stories, "qwer3 45g 63")
        self.assertRaises(pages.BadSubredditError, handler.download_stories, "78b@$@#$@#   @ 42 4 7cs")

    def testReturnList(self):
        """should return a list"""
        handler = pages.RedditHandler()
        self.assertIsInstance(handler.download_stories(None)[0], list)

    def testReturnStories(self):
        """should return a list of stories"""
        handler = pages.RedditHandler()
        for s in handler.download_stories(None, None, None)[0]:
            self.assertIsInstance(s, pages.Story)

class TestLogin(unittest.TestCase):

    def testInvalidLogin(self):
        """login attempt should fail"""
        handler = pages.RedditHandler()
        self.assertFalse(handler.login("gsdfgsdfg", "sdfgsfgsgf"))
             
        
if __name__ == "__main__":
    unittest.main()
########NEW FILE########
__FILENAME__ = canvas
#!/usr/bin/python
#
# Urwid canvas class and functions
#    Copyright (C) 2004-2007  Ian Ward
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

from __future__ import generators
import weakref

from util import *
from escape import * 
from text_layout import *

import sys

class CanvasCache(object):
    """
    Cache for rendered canvases.  Automatically populated and
    accessed by Widget render() MetaClass magic, cleared by 
    Widget._invalidate().

    Stores weakrefs to the canvas objects, so an external class
    must maintain a reference for this cache to be effective.
    At present the Screen classes store the last topmost canvas 
    after redrawing the screen, keeping the canvases from being 
    garbage collected.

    _widgets[widget] = {(wcls, size, focus): weakref.ref(canvas), ...}
    _refs[weakref.ref(canvas)] = (widget, wcls, size, focus)
    _deps[widget} = [dependent_widget, ...]
    """
    _widgets = {}
    _refs = {}
    _deps = {}
    hits = 0
    fetches = 0
    cleanups = 0

    def store(cls, wcls, canvas):
        """
        Store a weakref to canvas in the cache.

        wcls -- widget class that contains render() function
        canvas -- rendered canvas with widget_info (widget, size, focus)
        """
        assert canvas.widget_info, "Can't store canvas without widget_info"
        widget, size, focus = canvas.widget_info
        def walk_depends(canv):
            """
            Collect all child widgets for determining who we
            depend on.
            """
            # FIXME: is this recursion necessary?  The cache 
            # invalidating might work with only one level.
            depends = []
            for x, y, c, pos in canv.children:
                if c.widget_info:
                    depends.append(c.widget_info[0])
                elif hasattr(c, 'children'):
                    depends.extend(walk_depends(c))
            return depends

        # use explicit depends_on if available from the canvas
        depends_on = getattr(canvas, 'depends_on', None)
        if depends_on is None and hasattr(canvas, 'children'):
            depends_on = walk_depends(canvas)
        if depends_on:
            for w in depends_on:
                if w not in cls._widgets:
                    return
            for w in depends_on:
                cls._deps.setdefault(w,[]).append(widget)

        ref = weakref.ref(canvas, cls.cleanup)
        cls._refs[ref] = (widget, wcls, size, focus)
        cls._widgets.setdefault(widget, {})[(wcls, size, focus)] = ref
    store = classmethod(store)

    def fetch(cls, widget, wcls, size, focus):
        """
        Return the cached canvas or None.

        widget -- widget object requested
        wcls -- widget class that contains render() function
        size, focus -- render() parameters
        """
        cls.fetches += 1 # collect stats

        sizes = cls._widgets.get(widget, None)
        if not sizes:
            return None
        ref = sizes.get((wcls, size, focus), None)
        if not ref:
            return None
        canv = ref()
        if canv:
            cls.hits += 1 # more stats
        return canv
    fetch = classmethod(fetch)
    
    def invalidate(cls, widget):
        """
        Remove all canvases cached for widget.
        """
        try:
            for ref in cls._widgets[widget].values():
                try:
                    del cls._refs[ref]
                except KeyError:
                    pass
            del cls._widgets[widget]
        except KeyError:
            pass
        if widget not in cls._deps:
            return
        dependants = cls._deps.get(widget, [])
        try:
            del cls._deps[widget]
        except KeyError:
            pass
        for w in dependants:
            cls.invalidate(w)
    invalidate = classmethod(invalidate)

    def cleanup(cls, ref):
        cls.cleanups += 1 # collect stats

        w = cls._refs.get(ref, None)
        del cls._refs[ref]
        if not w:
            return
        widget, wcls, size, focus = w
        sizes = cls._widgets.get(widget, None)
        if not sizes:
            return
        try:
            del sizes[(wcls, size, focus)]
        except KeyError:
            pass
        if not sizes:
            try:
                del cls._widgets[widget]
                del cls._deps[widget]
            except KeyError:
                pass
    cleanup = classmethod(cleanup)

    def clear(cls):
        """
        Empty the cache.
        """
        cls._widgets = {}
        cls._refs = {}
        cls._deps = {}
    clear = classmethod(clear)


        
class CanvasError(Exception):
    pass

class Canvas(object):
    """
    base class for canvases
    """
    _finalized_error = CanvasError("This canvas has been finalized. "
        "Use CompositeCanvas to wrap this canvas if "
        "you need to make changes.")
    _renamed_error = CanvasError("The old Canvas class is now called "
        "TextCanvas. Canvas is now the base class for all canvas "
        "classes.")
    _old_repr_error = CanvasError("The internal representation of "
        "canvases is no longer stored as .text, .attr, and .cs "
        "lists, please see the TextCanvas class for the new "
        "representation of canvas content.")

    def __init__(self, value1=None, value2=None, value3=None):
        """
        value1, value2, value3 -- if not None, raise a helpful error:
            the old Canvas class is now called TextCanvas.
        """
        if value1 is not None: 
            raise _renamed_error
        self._widget_info = None
        self.coords = {}
        self.shortcuts = {}
    
    def finalize(self, widget, size, focus):
        """
        Mark this canvas as finalized (should not be any future
        changes to its content). This is required before caching
        the canvas.  This happens automatically after a widget's
        'render call returns the canvas thanks to some metaclass
        magic.

        widget -- widget that rendered this canvas
        size -- size parameter passed to widget's render method
        focus -- focus parameter passed to widget's render method
        """
        if self.widget_info:
            raise self._finalized_error
        self._widget_info = widget, size, focus

    def _get_widget_info(self):
        return self._widget_info
    widget_info = property(_get_widget_info)

    def _raise_old_repr_error(self, val=None):
        raise self._old_repr_error
    
    def _text_content(self):
        """
        Return the text content of the canvas as a list of strings,
        one for each row.
        """
        return ["".join([text for (attr, cs, text) in row])
            for row in self.content()]

    text = property(_text_content, _raise_old_repr_error)
    attr = property(_raise_old_repr_error, _raise_old_repr_error)
    cs = property(_raise_old_repr_error, _raise_old_repr_error)
    
    def content(self, trim_left=0, trim_top=0, cols=None, rows=None, 
            attr=None):
        raise NotImplementedError()

    def cols(self):
        raise NotImplementedError()

    def rows(self):
        raise NotImplementedError()
    
    def content_delta(self):
        raise NotImplementedError()

    def get_cursor(self):
        c = self.coords.get("cursor", None)
        if not c:
            return
        return c[:2] # trim off data part
    def set_cursor(self, c):
        if self.widget_info:
            raise self._finalized_error
        if c is None:
            try:
                del self.coords["cursor"]
            except KeyError:
                pass
            return
        self.coords["cursor"] = c + (None,) # data part
    cursor = property(get_cursor, set_cursor)

    def translate_coords(self, dx, dy):
        """
        Return coords shifted by (dx, dy).
        """
        d = {}
        for name, (x, y, data) in self.coords.items():
            d[name] = (x+dx, y+dy, data)
        return d



class TextCanvas(Canvas):
    """
    class for storing rendered text and attributes
    """
    def __init__(self, text=None, attr=None, cs=None, 
        cursor=None, maxcol=None, check_width=True):
        """
        text -- list of strings, one for each line
        attr -- list of run length encoded attributes for text
        cs -- list of run length encoded character set for text
        cursor -- (x,y) of cursor or None
        maxcol -- screen columns taken by this canvas
        check_width -- check and fix width of all lines in text
        """
        Canvas.__init__(self)
        if text == None: 
            text = []

        if check_width:
            widths = []
            for t in text:
                if type(t) != type(""):
                    raise CanvasError("Canvas text must be plain strings encoded in the screen's encoding", `text`)
                widths.append( calc_width( t, 0, len(t)) )
        else:
            assert type(maxcol) == type(0)
            widths = [maxcol] * len(text)

        if maxcol is None:
            if widths:
                # find maxcol ourselves
                maxcol = max(widths)
            else:
                maxcol = 0

        if attr == None: 
            attr = [[] for x in range(len(text))]
        if cs == None:
            cs = [[] for x in range(len(text))]
        
        # pad text and attr to maxcol
        for i in range(len(text)):
            w = widths[i]
            if w > maxcol: 
                raise CanvasError("Canvas text is wider than the maxcol specified \n%s\n%s\n%s"%(`maxcol`,`widths`,`text`))
            if w < maxcol:
                text[i] = text[i] + " "*(maxcol-w)
            a_gap = len(text[i]) - rle_len( attr[i] )
            if a_gap < 0:
                raise CanvasError("Attribute extends beyond text \n%s\n%s" % (`text[i]`,`attr[i]`) )
            if a_gap:
                rle_append_modify( attr[i], (None, a_gap))
            
            cs_gap = len(text[i]) - rle_len( cs[i] )
            if cs_gap < 0:
                raise CanvasError("Character Set extends beyond text \n%s\n%s" % (`text[i]`,`cs[i]`) )
            if cs_gap:
                rle_append_modify( cs[i], (None, cs_gap))
            
        self._attr = attr
        self._cs = cs
        self.cursor = cursor
        self._text = text
        self._maxcol = maxcol

    def rows(self):
        """Return the number of rows in this canvas."""
        return len(self._text)

    def cols(self):
        """Return the screen column width of this canvas."""
        return self._maxcol
    
    def translated_coords(self,dx,dy):
        """
        Return cursor coords shifted by (dx, dy), or None if there
        is no cursor.
        """
        if self.cursor:
            x, y = self.cursor
            return x+dx, y+dy
        return None

    def content(self, trim_left=0, trim_top=0, cols=None, rows=None,
            attr_map=None):
        """
        Return the canvas content as a list of rows where each row
        is a list of (attr, cs, text) tuples.

        trim_left, trim_top, cols, rows may be set by 
        CompositeCanvas when rendering a partially obscured
        canvas.
        """
        maxcol, maxrow = self.cols(), self.rows()
        if not cols: 
            cols = maxcol - trim_left
        if not rows:
            rows = maxrow - trim_top
            
        assert trim_left >= 0 and trim_left < maxcol
        assert cols > 0 and trim_left + cols <= maxcol
        assert trim_top >=0 and trim_top < maxrow
        assert rows > 0 and trim_top + rows <= maxrow
        
        if trim_top or rows < maxrow:
            text_attr_cs = zip(
                self._text[trim_top:trim_top+rows],
                self._attr[trim_top:trim_top+rows], 
                self._cs[trim_top:trim_top+rows])
        else:
            text_attr_cs = zip(self._text, self._attr, self._cs)
        
        for text, a_row, cs_row in text_attr_cs:
            if trim_left or cols < self._maxcol:
                text, a_row, cs_row = trim_text_attr_cs(
                    text, a_row, cs_row, trim_left, 
                    trim_left + cols)
            attr_cs = util.rle_product(a_row, cs_row)
            i = 0
            row = []
            for (a, cs), run in attr_cs:
                if attr_map and a in attr_map:
                    a = attr_map[a]
                row.append((a, cs, text[i:i+run]))
                i += run
            yield row
            

    def content_delta(self, other):
        """
        Return the differences between other and this canvas.

        If other is the same object as self this will return no 
        differences, otherwise this is the same as calling 
        content().
        """
        if other is self:
            return [self.cols()]*self.rows()
        return self.content()
    


class BlankCanvas(Canvas):
    """
    a canvas with nothing on it, only works as part of a composite canvas
    since it doesn't know its own size
    """
    def __init__(self):
        Canvas.__init__(self, None)

    def content(self, trim_left, trim_top, cols, rows, attr):
        """
        return (cols, rows) of spaces with default attributes.
        """
        def_attr = None
        if attr and None in attr:
            def_attr = attr[None]
        line = [(def_attr, None, " "*cols)]
        for i in range(rows):
            yield line

    def cols(self):
        raise NotImplementedError("BlankCanvas doesn't know its own size!")

    def rows(self):
        raise NotImplementedError("BlankCanvas doesn't know its own size!")
    
    def content_delta(self):
        raise NotImplementedError("BlankCanvas doesn't know its own size!")
        
blank_canvas = BlankCanvas()


class SolidCanvas(Canvas):
    """
    A canvas filled completely with a single character.
    """
    def __init__(self, fill_char, cols, rows):
        Canvas.__init__(self)
        end, col = calc_text_pos(fill_char, 0, len(fill_char), 1)
        assert col == 1, "Invalid fill_char: %r" % fill_char
        self._text, cs = apply_target_encoding(fill_char[:end])
        self._cs = cs[0][0]
        self.size = cols, rows
        self.cursor = None
    
    def cols(self):
        return self.size[0]
    
    def rows(self):
        return self.size[1]

    def content(self, trim_left=0, trim_top=0, cols=None, rows=None, 
            attr=None):
        if cols is None:
            cols = self.size[0]
        if rows is None:
            rows = self.size[1]
        def_attr = None
        if attr and None in attr:
            def_attr = attr[None]

        line = [(def_attr, self._cs, self._text*cols)]
        for i in range(rows):
            yield line

    def content_delta(self, other):
        """
        Return the differences between other and this canvas.
        """
        if other is self:
            return [self.cols()]*self.rows()
        return self.content()
        



class CompositeCanvas(Canvas):
    """
    class for storing a combination of canvases
    """
    def __init__(self, canv=None):
        """
        canv -- a Canvas object to wrap this CompositeCanvas around.

        if canv is a CompositeCanvas, make a copy of its contents
        """
        # a "shard" is a (num_rows, list of cviews) tuple, one for 
        # each cview starting in this shard

        # a "cview" is a tuple that defines a view of a canvas:
        # (trim_left, trim_top, cols, rows, attr_map, canv)

        # a "shard tail" is a list of tuples:
        # (col_gap, done_rows, content_iter, cview) 
        
        # tuples that define the unfinished cviews that are part of
        # shards following the first shard.
        Canvas.__init__(self)

        if canv is None:
            self.shards = []
            self.children = []
        else:
            if hasattr(canv, "shards"):
                self.shards = canv.shards
            else:
                self.shards = [(canv.rows(), [
                    (0, 0, canv.cols(), canv.rows(), 
                    None, canv)])]
            self.children = [(0, 0, canv, None)]
            self.coords.update(canv.coords)
            for shortcut in canv.shortcuts:
                self.shortcuts[shortcut] = "wrap"

    def rows(self):
        return sum([r for r,cv in self.shards])

    def cols(self):
        if not self.shards:
            return 0
        return sum([cv[2] for cv in self.shards[0][1]])

        
    def content(self):
        """
        Return the canvas content as a list of rows where each row
        is a list of (attr, cs, text) tuples.
        """
        shard_tail = []
        for num_rows, cviews in self.shards:
            # combine shard and shard tail
            sbody = shard_body(cviews, shard_tail)

            # output rows
            for i in range(num_rows):
                yield shard_body_row(sbody)

            # prepare next shard tail            
            shard_tail = shard_body_tail(num_rows, sbody)

                    
    
    def content_delta(self, other):
        """
        Return the differences between other and this canvas.
        """
        if not hasattr(other, 'shards'):
            for row in self.content():
                yield row
            return

        shard_tail = []
        for num_rows, cviews in shards_delta(
                self.shards, other.shards):
            # combine shard and shard tail
            sbody = shard_body(cviews, shard_tail)

            # output rows
            row = []
            for i in range(num_rows):
                # if whole shard is unchanged, don't keep 
                # calling shard_body_row
                if len(row) != 1 or type(row[0]) != type(0):
                    row = shard_body_row(sbody)
                yield row

            # prepare next shard tail
            shard_tail = shard_body_tail(num_rows, sbody)
                
    
    def trim(self, top, count=None):
        """Trim lines from the top and/or bottom of canvas.

        top -- number of lines to remove from top
        count -- number of lines to keep, or None for all the rest
        """
        assert top >= 0, "invalid trim amount %d!"%top
        assert top < self.rows(), "cannot trim %d lines from %d!"%(
            top, self.rows())
        if self.widget_info:
            raise self._finalized_error
        
        if top:
            self.shards = shards_trim_top(self.shards, top)

        if count == 0:
            self.shards = []
        elif count is not None:
            self.shards = shards_trim_rows(self.shards, count)

        self.coords = self.translate_coords(0, -top)

        
    def trim_end(self, end):
        """Trim lines from the bottom of the canvas.
        
        end -- number of lines to remove from the end
        """
        assert end > 0, "invalid trim amount %d!"%end
        assert end <= self.rows(), "cannot trim %d lines from %d!"%(
            end, self.rows())
        if self.widget_info:
            raise self._finalized_error
        
        self.shards = shards_trim_rows(self.shards, self.rows() - end)

            
    def pad_trim_left_right(self, left, right):
        """
        Pad or trim this canvas on the left and right
        
        values > 0 indicate screen columns to pad
        values < 0 indicate screen columns to trim
        """
        if self.widget_info:
            raise self._finalized_error
        shards = self.shards
        if left < 0 or right < 0:
            trim_left = max(0, -left)
            cols = self.cols() - trim_left - max(0, -right)
            shards = shards_trim_sides(shards, trim_left, cols)

        rows = self.rows()
        if left > 0 or right > 0:
            top_rows, top_cviews = shards[0]
            if left > 0:
                new_top_cviews = (
                    [(0,0,left,rows,None,blank_canvas)] +
                    top_cviews)
            else:
                new_top_cviews = top_cviews[:] #copy

            if right > 0:
                new_top_cviews.append(
                    (0,0,right,rows,None,blank_canvas))
            shards = [(top_rows, new_top_cviews)] + shards[1:]

        self.coords = self.translate_coords(left, 0)
        self.shards = shards


    def pad_trim_top_bottom(self, top, bottom):
        """
        Pad or trim this canvas on the top and bottom.
        """
        if self.widget_info:
            raise self._finalized_error
        orig_shards = self.shards

        if top < 0 or bottom < 0:
            trim_top = max(0, -top)
            rows = self.rows() - trim_top - max(0, -bottom)
            self.trim(trim_top, rows)

        cols = self.cols()
        if top > 0:
            self.shards = [(top,
                [(0,0,cols,top,None,blank_canvas)])] + \
                self.shards
            self.coords = self.translate_coords(0, top)
        
        if bottom > 0:
            if orig_shards is self.shards:
                self.shards = self.shards[:]
            self.shards.append((bottom,
                [(0,0,cols,bottom,None,blank_canvas)]))

        
    def overlay(self, other, left, top ):
        """Overlay other onto this canvas."""
        if self.widget_info:
            raise self._finalized_error
        
        width = other.cols()
        height = other.rows()
        right = self.cols() - left - width
        bottom = self.rows() - top - height
        
        assert right >= 0, "top canvas of overlay not the size expected!" + `other.cols(),left,right,width`
        assert bottom >= 0, "top canvas of overlay not the size expected!" + `other.rows(),top,bottom,height`

        shards = self.shards
        top_shards = []
        side_shards = self.shards
        bottom_shards = []
        if top:
            side_shards = shards_trim_top(shards, top)
            top_shards = shards_trim_rows(shards, top)
        if bottom:
            bottom_shards = shards_trim_top(side_shards, height)
            side_shards = shards_trim_rows(side_shards, height)

        left_shards = []
        right_shards = []
        if left:
            left_shards = [shards_trim_sides(side_shards, 0, left)]
        if right:
            right_shards = [shards_trim_sides(side_shards, 
                left + width, right)]
        
        if not self.rows():
            middle_shards = []
        elif left or right:
            middle_shards = shards_join(left_shards + 
                [other.shards] + right_shards)
        else:
            middle_shards = other.shards

        self.shards = top_shards + middle_shards + bottom_shards
        
        self.coords.update(other.translate_coords(left, top))


    def fill_attr(self, a):
        """
        Apply attribute a to all areas of this canvas with default
        attribute currently set to None, leaving other attributes
        intact."""
        self.fill_attr_apply({None:a})
    
    def fill_attr_apply(self, mapping):
        """
        Apply an attribute-mapping dictionary to the canvas.

        mapping -- dictionary of original-attribute:new-attribute items
        """
        if self.widget_info:
            raise self._finalized_error

        shards = []
        for num_rows, original_cviews in self.shards:
            new_cviews = []
            for cv in original_cviews:
                # cv[4] == attr_map
                if cv[4] is None:
                    new_cviews.append(cv[:4] + 
                        (mapping,) + cv[5:])
                else:
                    combined = dict(mapping)
                    combined.update([
                        (k, mapping.get(v, v)) for k,v in cv[4].items()])
                    new_cviews.append(cv[:4] +
                        (combined,) + cv[5:])
            shards.append((num_rows, new_cviews))
        self.shards = shards

    def set_depends(self, widget_list):
        """
        Explicitly specify the list of widgets that this canvas
        depends on.  If any of these widgets change this canvas
        will have to be updated.
        """
        if self.widget_info:
            raise self._finalized_error

        self.depends_on = widget_list


def shard_body_row(sbody):
    """
    Return one row, advancing the iterators in sbody.

    ** MODIFIES sbody by calling next() on its iterators **
    """
    row = []
    for done_rows, content_iter, cview in sbody:
        if content_iter:
            row.extend(content_iter.next())
        else:
            # need to skip this unchanged canvas
            if row and type(row[-1]) == type(0):
                row[-1] = row[-1] + cview[2]
            else:
                row.append(cview[2])

    return row


def shard_body_tail(num_rows, sbody):
    """
    Return a new shard tail that follows this shard body.
    """
    shard_tail = []
    col_gap = 0
    done_rows = 0
    for done_rows, content_iter, cview in sbody:
        cols, rows = cview[2:4]
        done_rows += num_rows
        if done_rows == rows:
            col_gap += cols
            continue
        shard_tail.append((col_gap, done_rows, content_iter, cview))
        col_gap = 0
    return shard_tail


def shards_delta(shards, other_shards):
    """
    Yield shards1 with cviews that are the same as shards2 
    having canv = None.
    """
    other_shards_iter = iter(other_shards)
    other_num_rows = other_cviews = None
    done = other_done = 0
    for num_rows, cviews in shards:
        if other_num_rows is None:
            other_num_rows, other_cviews = other_shards_iter.next()
        while other_done < done:
            other_done += other_num_rows
            other_num_rows, other_cviews = other_shards_iter.next()
        if other_done > done:
            yield (num_rows, cviews)
            done += num_rows
            continue
        # top-aligned shards, compare each cview
        yield (num_rows, shard_cviews_delta(cviews, other_cviews))
        other_done += other_num_rows
        other_num_rows = None
        done += num_rows

def shard_cviews_delta(cviews, other_cviews):
    """
    """
    other_cviews_iter = iter(other_cviews)
    other_cv = None
    cols = other_cols = 0
    for cv in cviews:
        if other_cv is None:
            other_cv = other_cviews_iter.next()
        while other_cols < cols:
            other_cols += other_cv[2]
            other_cv = other_cviews_iter.next()
        if other_cols > cols:
            yield cv
            cols += cv[2]
            continue
        # top-left-aligned cviews, compare them
        if cv[5] is other_cv[5] and cv[:5] == other_cv[:5]:
            yield cv[:5]+(None,)+cv[6:]
        else:
            yield cv
        other_cols += other_cv[2]
        other_cv = None
        cols += cv[2]



def shard_body(cviews, shard_tail, create_iter=True, iter_default=None):
    """
    Return a list of (done_rows, content_iter, cview) tuples for 
    this shard and shard tail.

    If a canvas in cviews is None (eg. when unchanged from 
    shard_cviews_delta()) or if create_iter is False then no 
    iterator is created for content_iter.

    iter_default is the value used for content_iter when no iterator
    is created.
    """
    col = 0
    body = [] # build the next shard tail
    cviews_iter = iter(cviews)
    for col_gap, done_rows, content_iter, tail_cview in shard_tail:
        while col_gap:
            try:
                cview = cviews_iter.next()
            except StopIteration:
                raise CanvasError("cviews do not fill gaps in"
                    " shard_tail!")
            (trim_left, trim_top, cols, rows, attr_map, canv) = \
                cview[:6]
            col += cols
            col_gap -= cols
            if col_gap < 0:
                raise CanvasError("cviews overflow gaps in"
                    " shard_tail!")
            if create_iter and canv:
                new_iter = canv.content(trim_left, trim_top, 
                    cols, rows, attr_map)
            else:
                new_iter = iter_default
            body.append((0, new_iter, cview))
        body.append((done_rows, content_iter, tail_cview))
    for cview in cviews_iter:
        (trim_left, trim_top, cols, rows, attr_map, canv) = \
            cview[:6]
        if create_iter and canv:
            new_iter = canv.content(trim_left, trim_top, cols, rows, 
                attr_map)
        else:
            new_iter = iter_default
        body.append((0, new_iter, cview))
    return body


def shards_trim_top(shards, top):
    """
    Return shards with top rows removed.
    """
    assert top > 0

    shard_iter = iter(shards)
    shard_tail = []
    # skip over shards that are completely removed
    for num_rows, cviews in shard_iter:
        if top < num_rows:
            break
        sbody = shard_body(cviews, shard_tail, False)
        shard_tail = shard_body_tail(num_rows, sbody)
        top -= num_rows
    else:
        raise CanvasError("tried to trim shards out of existance")
    
    sbody = shard_body(cviews, shard_tail, False)
    shard_tail = shard_body_tail(num_rows, sbody)
    # trim the top of this shard
    new_sbody = []
    for done_rows, content_iter, cv in sbody:
        new_sbody.append((0, content_iter, 
            cview_trim_top(cv, done_rows+top)))
    sbody = new_sbody
    
    new_shards = [(num_rows-top, 
        [cv for done_rows, content_iter, cv in sbody])]
    
    # write out the rest of the shards
    new_shards.extend(shard_iter)

    return new_shards

def shards_trim_rows(shards, keep_rows):
    """
    Return the topmost keep_rows rows from shards.
    """
    assert keep_rows >= 0, keep_rows

    shard_tail = []
    new_shards = []
    done_rows = 0
    for num_rows, cviews in shards:
        if done_rows >= keep_rows:
            break
        new_cviews = []
        for cv in cviews:
            if cv[3] + done_rows > keep_rows:
                new_cviews.append(cview_trim_rows(cv, 
                    keep_rows - done_rows))
            else:
                new_cviews.append(cv)

        if num_rows + done_rows > keep_rows:
            new_shards.append((keep_rows - done_rows, new_cviews))
        else:
            new_shards.append((num_rows, new_cviews))
        done_rows += num_rows

    return new_shards

def shards_trim_sides(shards, left, cols):
    """
    Return shards with starting from column left and cols total width.
    """
    assert left >= 0 and cols > 0
    shard_tail = []
    new_shards = []
    right = left + cols
    for num_rows, cviews in shards:
        sbody = shard_body(cviews, shard_tail, False)
        shard_tail = shard_body_tail(num_rows, sbody)
        new_cviews = []
        col = 0
        for done_rows, content_iter, cv in sbody:
            cv_cols = cv[2]
            next_col = col + cv_cols
            if done_rows or next_col <= left or col >= right:
                col = next_col
                continue
            if col < left:
                cv = cview_trim_left(cv, left - col)
                col = left
            if next_col > right:
                cv = cview_trim_cols(cv, right - col)
            new_cviews.append(cv)
            col = next_col
        if not new_cviews:
            prev_num_rows, prev_cviews = new_shards[-1]
            new_shards[-1] = (prev_num_rows+num_rows, prev_cviews)
        else:
            new_shards.append((num_rows, new_cviews))
    return new_shards

def shards_join(shard_lists):
    """
    Return the result of joining shard lists horizontally.
    All shards lists must have the same number of rows.
    """
    shards_iters = [iter(sl) for sl in shard_lists]
    shards_current = [i.next() for i in shards_iters]

    new_shards = []
    while True:
        new_cviews = []
        num_rows = min([r for r,cv in shards_current])

        shards_next = []
        for rows, cviews in shards_current:
            if cviews:
                new_cviews.extend(cviews)
            shards_next.append((rows - num_rows, None))

        shards_current = shards_next
        new_shards.append((num_rows, new_cviews))

        # advance to next shards
        try:
            for i in range(len(shards_current)):
                if shards_current[i][0] > 0:
                    continue
                shards_current[i] = shards_iters[i].next()
        except StopIteration:
            break
    return new_shards


def cview_trim_rows(cv, rows):
    return cv[:3] + (rows,) + cv[4:]
    
def cview_trim_top(cv, trim):
    return (cv[0], trim + cv[1], cv[2], cv[3] - trim) + cv[4:]

def cview_trim_left(cv, trim):
    return (cv[0] + trim, cv[1], cv[2] - trim,) + cv[3:]

def cview_trim_cols(cv, cols):
    return cv[:2] + (cols,) + cv[3:]


        

def CanvasCombine(l):
    """Stack canvases in l vertically and return resulting canvas.

    l -- list of (canvas, position, focus) tuples.  position is a value
         that widget.set_focus will accept, or None if not allowed.
         focus is True if this canvas is the one that would be in focus
         if the whole widget is in focus.
    """
    clist = [(CompositeCanvas(c),p,f) for c,p,f in l]

    combined_canvas = CompositeCanvas()
    shards = []
    children = []
    row = 0
    focus_index = 0
    n = 0
    for canv, pos, focus in clist:
        if focus: 
            focus_index = n
        children.append((0, row, canv, pos))
        shards.extend(canv.shards)
        combined_canvas.coords.update(canv.translate_coords(0, row))
        for shortcut in canv.shortcuts.keys():
            combined_canvas.shortcuts[shortcut] = pos
        row += canv.rows()
        n += 1
    
    if focus_index:
        children = [children[focus_index]] + children[:focus_index] + \
            children[focus_index+1:]

    combined_canvas.shards = shards
    combined_canvas.children = children
    return combined_canvas


def CanvasOverlay(top_c, bottom_c, left, top):
    """
    Overlay canvas top_c onto bottom_c at position (left, top).
    """
    overlayed_canvas = CompositeCanvas(bottom_c)
    overlayed_canvas.overlay(top_c, left, top)
    overlayed_canvas.children = [(left, top, top_c, None), 
        (0, 0, bottom_c, None)]
    overlayed_canvas.shortcuts = {} # disable background shortcuts
    for shortcut in top_c.shortcuts.keys():
        overlayed_canvas.shortcuts[shortcut]="fg"
    return overlayed_canvas


def CanvasJoin(l):
    """
    Join canvases in l horizontally. Return result.
    l -- list of (canvas, position, focus, cols) tuples.  position is a 
         value that widget.set_focus will accept,  or None if not allowed.
         focus is True if this canvas is the one that would be in focus if
         the whole widget is in focus.  cols is the number of screen
         columns that this widget will require, if larger than the actual
         canvas.cols() value then this widget will be padded on the right.
    """
    
    l2 = []
    focus_item = 0
    maxrow = 0
    n = 0 
    for canv, pos, focus, cols in l:
        rows = canv.rows()
        pad_right = cols - canv.cols()
        if focus:
            focus_item = n
        if rows > maxrow:
            maxrow = rows
        l2.append((canv, pos, pad_right, rows))
        n += 1
    
    shard_lists = []
    children = []
    joined_canvas = CompositeCanvas()
    col = 0
    for canv, pos, pad_right, rows in l2:
        canv = CompositeCanvas(canv)
        if pad_right:
            canv.pad_trim_left_right(0, pad_right)
        if rows < maxrow:
            canv.pad_trim_top_bottom(0, maxrow - rows)
        joined_canvas.coords.update(canv.translate_coords(col, 0))
        for shortcut in canv.shortcuts.keys():
            joined_canvas.shortcuts[shortcut] = pos
        shard_lists.append(canv.shards)
        children.append((col, 0, canv, pos))
        col += canv.cols()

    if focus_item:
        children = [children[focus_item]] + children[:focus_item] + \
            children[focus_item+1:]

    joined_canvas.shards = shards_join(shard_lists)
    joined_canvas.children = children
    return joined_canvas


def apply_text_layout(text, attr, ls, maxcol):
    utext = type(text)==type(u"")
    t = []
    a = []
    c = []
    
    class AttrWalk:
        pass
    aw = AttrWalk
    aw.k = 0 # counter for moving through elements of a
    aw.off = 0 # current offset into text of attr[ak]
    
    def arange( start_offs, end_offs ):
        """Return an attribute list for the range of text specified."""
        if start_offs < aw.off:
            aw.k = 0
            aw.off = 0
        o = []
        while aw.off < end_offs:
            if len(attr)<=aw.k:
                # run out of attributes
                o.append((None,end_offs-max(start_offs,aw.off)))
                break
            at,run = attr[aw.k]
            if aw.off+run <= start_offs:
                # move forward through attr to find start_offs
                aw.k += 1
                aw.off += run
                continue
            if end_offs <= aw.off+run:
                o.append((at, end_offs-max(start_offs,aw.off)))
                break
            o.append((at, aw.off+run-max(start_offs, aw.off)))
            aw.k += 1
            aw.off += run
        return o

    
    for line_layout in ls:
        # trim the line to fit within maxcol
        line_layout = trim_line( line_layout, text, 0, maxcol )
        
        line = []
        linea = []
        linec = []
            
        def attrrange( start_offs, end_offs, destw ):
            """
            Add attributes based on attributes between
            start_offs and end_offs. 
            """
            if start_offs == end_offs:
                [(at,run)] = arange(start_offs,end_offs)
                rle_append_modify( linea, ( at, destw ))
                return
            if destw == end_offs-start_offs:
                for at, run in arange(start_offs,end_offs):
                    rle_append_modify( linea, ( at, run ))
                return
            # encoded version has different width
            o = start_offs
            for at, run in arange(start_offs, end_offs):
                if o+run == end_offs:
                    rle_append_modify( linea, ( at, destw ))
                    return
                tseg = text[o:o+run]
                tseg, cs = apply_target_encoding( tseg )
                segw = rle_len(cs)
                
                rle_append_modify( linea, ( at, segw ))
                o += run
                destw -= segw
            
            
        for seg in line_layout:
            #if seg is None: assert 0, ls
            s = LayoutSegment(seg)
            if s.end:
                tseg, cs = apply_target_encoding(
                    text[s.offs:s.end])
                line.append(tseg)
                attrrange(s.offs, s.end, rle_len(cs))
                rle_join_modify( linec, cs )
            elif s.text:
                tseg, cs = apply_target_encoding( s.text )
                line.append(tseg)
                attrrange( s.offs, s.offs, len(tseg) )
                rle_join_modify( linec, cs )
            elif s.offs:
                if s.sc:
                    line.append(" "*s.sc)
                    attrrange( s.offs, s.offs, s.sc )
            else:
                line.append(" "*s.sc)
                linea.append((None, s.sc))
                linec.append((None, s.sc))
            
        t.append("".join(line))
        a.append(linea)
        c.append(linec)
        
    return TextCanvas(t, a, c, maxcol=maxcol)





########NEW FILE########
__FILENAME__ = command_map
#!/usr/bin/python
#
# Urwid CommandMap class
#    Copyright (C) 2004-2007  Ian Ward
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



class CommandMap:
    _command_defaults = {
        'tab': 'next selectable',
        'ctrl n': 'next selectable',
        'shift tab': 'prev selectable',
        'ctrl p': 'prev selectable',
        'ctrl l': 'redraw screen',
        'esc': 'menu',
        'up': 'cursor up',
        'down': 'cursor down',
        'left': 'cursor left',
        'right': 'cursor right',
        'page up': 'cursor page up',
        'page down': 'cursor page down',
        'home': 'cursor max left',
        'end': 'cursor max right', 
        ' ': 'activate',
        'enter': 'activate',
    }

    def __init__(self):
        self.restore_defaults()

    def restore_defaults(self):
        self._command = dict(self._command_defaults)
    
    def __getitem__(self, key):
        return self._command.get(key, None)
    
    def __setitem__(self, key, command):
        self._command[key] = command

    def __delitem__(self, key):
        del self._command[key]
    
    def clear_command(self, command):
        dk = [k for k, v in self._command.items() if v == command]
        for k in dk:
            del self._command[key]
command_map = CommandMap() # shared command mappings

########NEW FILE########
__FILENAME__ = container
#!/usr/bin/python
#
# Urwid container widget classes
#    Copyright (C) 2004-2008  Ian Ward
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

from util import *
from widget import *
from decoration import *
from command_map import command_map


class WidgetContainer(Widget):
    def __init__(self, widget_list):
        self.__super.__init__()
        self._widget_list = MonitoredList([])
        self._set_widget_list(widget_list)
        self._widget_list.set_modified_callback(self._invalidate)


    def _get_widget_list(self):
        return self._widget_list
    def _set_widget_list(self, widget_list):
        """
        widget_list -- iterable containing widgets

        Copy the values from widget_list into self.widget_list 
        """
    widget_list = property(_get_widget_list, _set_widget_list)

    def __getitem__(self, index):
        """
        Return the base widget of the widget at self.widget_list[index].
        """
        w = self._widget_list[index]
        if hasattr(w, 'base_widget'):
            w = w.base_widget
        return w

    def __len__(self):
        return len(self._widget_list)

    def __iter__(self):
        i = 0
        try:
            while True:
                v = self[i]
                yield v
                i += 1
        except IndexError:
            return

    def __contains__(self, value):
        for v in self:
            if v == value:
                return True
        return False

    def __reversed__(self):
        for i in reversed(range(len(self))):
            yield self[i]

    def index(self, value):
        for i, v in enumerate(self):
            if v == value:
                return i
        raise ValueError

    def count(self, value):
        return sum(1 for v in self if v == value)




class GridFlow(FlowWidget):

    def selectable(self): 
        """Return True if the cell in focus is selectable."""
        return self.focus_cell and self.focus_cell.selectable()
        
    def __init__(self, cells, cell_width, h_sep, v_sep, align):
        """
        cells -- list of flow widgets to display
        cell_width -- column width for each cell
        h_sep -- blank columns between each cell horizontally
        v_sep -- blank rows between cells vertically (if more than
                 one row is required to display all the cells)
        align -- horizontal alignment of cells, see "align" parameter
                 of Padding widget for available options
        """
        self.__super.__init__()
        self.cells = cells
        self.cell_width = cell_width
        self.h_sep = h_sep
        self.v_sep = v_sep
        self.align = align
        self.focus_cell = None
        if cells:
            self.focus_cell = cells[0]
        self._cache_maxcol = None

    def set_focus(self, cell):
        """Set the cell in focus.  
        
        cell -- widget or integer index into self.cells"""
        if type(cell) == type(0):
            assert cell>=0 and cell<len(self.cells)
            self.focus_cell = self.cells[cell]
        else:
            assert cell in self.cells
            self.focus_cell = cell
        self._cache_maxcol = None
        self._invalidate()
        

    def get_display_widget(self, size):
        """
        Arrange the cells into columns (and possibly a pile) for 
        display, input or to calculate rows. 
        """
        (maxcol,) = size
        # use cache if possible
        if self._cache_maxcol == maxcol:
            return self._cache_display_widget

        self._cache_maxcol = maxcol
        self._cache_display_widget = self.generate_display_widget(
            size)

        return self._cache_display_widget

    def generate_display_widget(self, size):
        """
        Actually generate display widget (ignoring cache)
        """
        (maxcol,) = size
        d = Divider()
        if len(self.cells) == 0: # how dull
            return d
        
        if self.v_sep > 1:
            # increase size of divider
            d.top = self.v_sep-1
        
        # cells per row
        bpr = (maxcol+self.h_sep) / (self.cell_width+self.h_sep)
        
        if bpr == 0: # too narrow, pile them on top of eachother
            l = [self.cells[0]]
            f = 0
            for b in self.cells[1:]:
                if b is self.focus_cell:
                    f = len(l)
                if self.v_sep:
                    l.append(d)
                l.append(b)
            return Pile(l, f)
        
        if bpr >= len(self.cells): # all fit on one row
            k = len(self.cells)
            f = self.cells.index(self.focus_cell)
            cols = Columns(self.cells, self.h_sep, f)
            rwidth = (self.cell_width+self.h_sep)*k - self.h_sep
            row = Padding(cols, self.align, rwidth)
            return row

        
        out = []
        s = 0
        f = 0
        while s < len(self.cells):
            if out and self.v_sep:
                out.append(d)
            k = min( len(self.cells), s+bpr )
            cells = self.cells[s:k]
            if self.focus_cell in cells:
                f = len(out)
                fcol = cells.index(self.focus_cell)
                cols = Columns(cells, self.h_sep, fcol)
            else:
                cols = Columns(cells, self.h_sep)
            rwidth = (self.cell_width+self.h_sep)*(k-s)-self.h_sep
            row = Padding(cols, self.align, rwidth)
            out.append(row)
            s += bpr
        return Pile(out, f)    
    
    def _set_focus_from_display_widget(self, w):
        """Set the focus to the item in focus in the display widget."""
        if isinstance(w, Padding):
            # unwrap padding
            w = w._original_widget
        w = w.get_focus()
        if w in self.cells:
            self.set_focus(w)
            return
        if isinstance(w, Padding):
            # unwrap padding
            w = w._original_widget
        w = w.get_focus()
        #assert w == self.cells[0], `w, self.cells`
        self.set_focus(w)

    def keypress(self, size, key):
        """
        Pass keypress to display widget for handling.  
        Capture    focus changes."""
        
        d = self.get_display_widget(size)
        if not d.selectable():
            return key
        key = d.keypress(size, key)
        if key is None:
            self._set_focus_from_display_widget(d)
        return key

    def rows(self, size, focus=False):
        """Return rows used by this widget."""
        d = self.get_display_widget(size)
        return d.rows(size, focus=focus)
    
    def render(self, size, focus=False ):
        """Use display widget to render."""
        d = self.get_display_widget(size)
        return d.render(size, focus)

    def get_cursor_coords(self, size):
        """Get cursor from display widget."""
        d = self.get_display_widget(size)
        if not d.selectable():
            return None
        return d.get_cursor_coords(size)
    
    def move_cursor_to_coords(self, size, col, row ):
        """Set the widget in focus based on the col + row."""
        d = self.get_display_widget(size)
        if not d.selectable():
            # happy is the default
            return True
        
        r =  d.move_cursor_to_coords(size, col, row)
        if not r:
            return False
        
        self._set_focus_from_display_widget(d)
        self._invalidate()
        return True
    
    def mouse_event(self, size, event, button, col, row, focus):
        """Send mouse event to contained widget."""
        d = self.get_display_widget(size)
        
        r = d.mouse_event(size, event, button, col, row, focus)
        if not r:
            return False
        
        self._set_focus_from_display_widget(d)
        self._invalidate()
        return True
        
    
    def get_pref_col(self, size):
        """Return pref col from display widget."""
        d = self.get_display_widget(size)
        if not d.selectable():
            return None
        return d.get_pref_col(size)
    

        
class OverlayError(Exception):
    pass

class Overlay(BoxWidget):
    def __init__(self, top_w, bottom_w, align, width, valign, height,
            min_width=None, min_height=None ):
        """
        top_w -- a flow, box or fixed widget to overlay "on top"
        bottom_w -- a box widget to appear "below" previous widget
        align -- one of:
            'left', 'center', 'right'
            ('fixed left', columns)
            ('fixed right', columns)
            ('relative', percentage 0=left 100=right)
        width -- one of:
            None if top_w is a fixed widget
            number of columns wide
            ('fixed right', columns)  Only if align is 'fixed left'
            ('fixed left', columns)  Only if align is 'fixed right'
            ('relative', percentage of total width)
        valign -- one of:
            'top', 'middle', 'bottom'
            ('fixed top', rows)
            ('fixed bottom', rows)
            ('relative', percentage 0=top 100=bottom)
        height -- one of:
            None if top_w is a flow or fixed widget
            number of rows high 
            ('fixed bottom', rows)  Only if valign is 'fixed top'
            ('fixed top', rows)  Only if valign is 'fixed bottom'
            ('relative', percentage of total height)
        min_width -- the minimum number of columns for top_w
            when width is not fixed
        min_height -- one of:
            minimum number of rows for the widget when height not fixed
        
        Overlay widgets behave similarly to Padding and Filler widgets
        when determining the size and position of top_w.  bottom_w is
        always rendered the full size available "below" top_w.
        """
        self.__super.__init__()

        at,aa,wt,wa=decompose_align_width(align, width, OverlayError)
        vt,va,ht,ha=decompose_valign_height(valign,height,OverlayError)
        
        self.top_w = top_w
        self.bottom_w = bottom_w
        
        self.align_type, self.align_amount = at, aa
        self.width_type, self.width_amount = wt, wa
        if self.width_type and self.width_type != 'fixed':
            self.min_width = min_width
        else:
            self.min_width = None
        
        self.valign_type, self.valign_amount = vt, va
        self.height_type, self.height_amount = ht, ha
        if self.height_type not in ('fixed', None):
            self.min_height = min_height
        else:
            self.min_height = None

    def selectable(self):
        """Return selectable from top_w."""
        return self.top_w.selectable()
    
    def keypress(self, size, key):
        """Pass keypress to top_w."""
        return self.top_w.keypress(self.top_w_size(size,
                       *self.calculate_padding_filler(size, True)), key)
    
    def get_cursor_coords(self, size):
        """Return cursor coords from top_w, if any."""
        if not hasattr(self.body, 'get_cursor_coords'):
            return None
        left, right, top, bottom = self.calculate_padding_filler(size,
            True)
        x, y = self.top_w.get_cursor_coords(
            (maxcol-left-right, maxrow-top-bottom) )
        if y >= maxrow:  # required??
            y = maxrow-1
        return x+left, y+top
    
    def calculate_padding_filler(self, size, focus):
        """Return (padding left, right, filler top, bottom)."""
        (maxcol, maxrow) = size
        height = None
        if self.width_type is None:
            # top_w is a fixed widget
            width, height = self.top_w.pack((),focus=focus)
            assert height, "fixed widget must have a height"
            left, right = calculate_padding(self.align_type,
                self.align_amount, 'fixed', width, 
                None, maxcol, clip=True )
        else:
            left, right = calculate_padding(self.align_type,
                self.align_amount, self.width_type,
                self.width_amount, self.min_width, maxcol)

        if height:
            # top_w is a fixed widget
            top, bottom = calculate_filler(self.valign_type, 
                self.valign_amount, 'fixed', height,
                None, maxrow)
            if maxrow-top-bottom < height:
                bottom = maxrow-top-height
        elif self.height_type is None:
            # top_w is a flow widget
            height = self.top_w.rows((maxcol,),focus=focus)
            top, bottom =  calculate_filler( self.valign_type,
                self.valign_amount, 'fixed', height, 
                None, maxrow )
        else:    
            top, bottom = calculate_filler(self.valign_type, 
                self.valign_amount, self.height_type, 
                self.height_amount, self.min_height, maxrow)
        return left, right, top, bottom
    
    def top_w_size(self, size, left, right, top, bottom):
        """Return the size to pass to top_w."""
        if self.width_type is None:
            # top_w is a fixed widget
            return ()
        maxcol, maxrow = size
        if self.width_type is not None and self.height_type is None:
            # top_w is a flow widget
            return (maxcol-left-right,)
        return (maxcol-left-right, maxrow-top-bottom)
            
    
    def render(self, size, focus=False):
        """Render top_w overlayed on bottom_w."""
        left, right, top, bottom = self.calculate_padding_filler(size,
            focus)
        bottom_c = self.bottom_w.render(size)
        top_c = self.top_w.render(
            self.top_w_size(size, left, right, top, bottom), focus)
        if left<0 or right<0:
            top_c = CompositeCanvas(top_c)
            top_c.pad_trim_left_right(min(0,left), min(0,right))
        if top<0 or bottom<0:
            top_c = CompositeCanvas(top_c)
            top_c.pad_trim_top_bottom(min(0,top), min(0,bottom))
        
        return CanvasOverlay(top_c, bottom_c, max(0,left), top)


    def mouse_event(self, size, event, button, col, row, focus):
        """Pass event to top_w, ignore if outside of top_w."""
        if not hasattr(self.top_w, 'mouse_event'):
            return False
        
        left, right, top, bottom = self.calculate_padding_filler(size,
            focus)
        maxcol, maxrow = size
        if ( col<left or col>=maxcol-right or
            row<top or row>=maxrow-bottom ):
            return False
            
        return self.top_w.mouse_event(
            self.top_w_size(size, left, right, top, bottom),
            event, button, col-left, row-top, focus )
    

class Frame(BoxWidget):
    def __init__(self, body, header=None, footer=None, focus_part='body'):
        """
        body -- a box widget for the body of the frame
        header -- a flow widget for above the body (or None)
        footer -- a flow widget for below the body (or None)
        focus_part -- 'header', 'footer' or 'body'
        """
        self.__super.__init__()

        self._header = header
        self._body = body
        self._footer = footer
        self.focus_part = focus_part
    
    def get_header(self):
        return self._header
    def set_header(self, header):
        self._header = header
        self._invalidate()
    header = property(get_header, set_header)
        
    def get_body(self):
        return self._body
    def set_body(self, body):
        self._body = body
        self._invalidate()
    body = property(get_body, set_body)

    def get_footer(self):
        return self._footer
    def set_footer(self, footer):
        self._footer = footer
        self._invalidate()
    footer = property(get_footer, set_footer)

    def set_focus(self, part):
        """Set the part of the frame that is in focus.

        part -- 'header', 'footer' or 'body'
        """
        assert part in ('header', 'footer', 'body')
        self.focus_part = part
        self._invalidate()

    def frame_top_bottom(self, size, focus):
        """Calculate the number of rows for the header and footer.

        Returns (head rows, foot rows),(orig head, orig foot).
        orig head/foot are from rows() calls.
        """
        (maxcol, maxrow) = size
        frows = hrows = 0
        
        if self.header:
            hrows = self.header.rows((maxcol,),
                self.focus_part=='header' and focus)
        
        if self.footer:
            frows = self.footer.rows((maxcol,),
                self.focus_part=='footer' and focus)
        
        remaining = maxrow
        
        if self.focus_part == 'footer':
            if frows >= remaining:
                return (0, remaining),(hrows, frows)
                
            remaining -= frows
            if hrows >= remaining:
                return (remaining, frows),(hrows, frows)

        elif self.focus_part == 'header':
            if hrows >= maxrow:
                return (remaining, 0),(hrows, frows)
            
            remaining -= hrows
            if frows >= remaining:
                return (hrows, remaining),(hrows, frows)

        elif hrows + frows >= remaining:
            # self.focus_part == 'body'
            rless1 = max(0, remaining-1)
            if frows >= remaining-1:
                return (0, rless1),(hrows, frows)
            
            remaining -= frows
            rless1 = max(0, remaining-1)
            return (rless1,frows),(hrows, frows)
        
        return (hrows, frows),(hrows, frows)
        
    

    def render(self, size, focus=False):
        """Render frame and return it."""
        (maxcol, maxrow) = size
        (htrim, ftrim),(hrows, frows) = self.frame_top_bottom(
            (maxcol, maxrow), focus)
        
        combinelist = []
        depends_on = []
        
        head = None
        if htrim and htrim < hrows:
            head = Filler(self.header, 'top').render(
                (maxcol, htrim), 
                focus and self.focus_part == 'header')
        elif htrim:
            head = self.header.render((maxcol,),
                focus and self.focus_part == 'header')
            assert head.rows() == hrows, "rows, render mismatch"
        if head:
            combinelist.append((head, 'header', 
                self.focus_part == 'header'))
            depends_on.append(self.header)

        if ftrim+htrim < maxrow:
            body = self.body.render((maxcol, maxrow-ftrim-htrim),
                focus and self.focus_part == 'body')
            combinelist.append((body, 'body', 
                self.focus_part == 'body'))
            depends_on.append(self.body)
        
        foot = None    
        if ftrim and ftrim < frows:
            foot = Filler(self.footer, 'bottom').render(
                (maxcol, ftrim), 
                focus and self.focus_part == 'footer')
        elif ftrim:
            foot = self.footer.render((maxcol,),
                focus and self.focus_part == 'footer')
            assert foot.rows() == frows, "rows, render mismatch"
        if foot:
            combinelist.append((foot, 'footer', 
                self.focus_part == 'footer'))
            depends_on.append(self.footer)

        return CanvasCombine(combinelist)


    def keypress(self, size, key):
        """Pass keypress to widget in focus."""
        (maxcol, maxrow) = size
        
        if self.focus_part == 'header' and self.header is not None:
            if not self.header.selectable():
                return key
            return self.header.keypress((maxcol,),key) 
        if self.focus_part == 'footer' and self.footer is not None:
            if not self.footer.selectable():
                return key
            return self.footer.keypress((maxcol,),key)
        if self.focus_part != 'body':
            return key
        remaining = maxrow
        if self.header is not None:
            remaining -= self.header.rows((maxcol,))
        if self.footer is not None:
            remaining -= self.footer.rows((maxcol,))
        if remaining <= 0: return key
    
        if not self.body.selectable():
            return key
        return self.body.keypress( (maxcol, remaining), key )


    def mouse_event(self, size, event, button, col, row, focus):
        """
        Pass mouse event to appropriate part of frame.
        Focus may be changed on button 1 press.
        """
        (maxcol, maxrow) = size
        (htrim, ftrim),(hrows, frows) = self.frame_top_bottom(
            (maxcol, maxrow), focus)
        
        if row < htrim: # within header
            focus = focus and self.focus_part == 'header'
            if is_mouse_press(event) and button==1:
                if self.header.selectable():
                    self.set_focus('header')
            if not hasattr(self.header, 'mouse_event'):
                return False
            return self.header.mouse_event( (maxcol,), event,
                button, col, row, focus )
        
        if row >= maxrow-ftrim: # within footer
            focus = focus and self.focus_part == 'footer'
            if is_mouse_press(event) and button==1:
                if self.footer.selectable():
                    self.set_focus('footer')
            if not hasattr(self.footer, 'mouse_event'):
                return False
            return self.footer.mouse_event( (maxcol,), event,
                button, col, row-maxrow+frows, focus )
        
        # within body
        focus = focus and self.focus_part == 'body'
        if is_mouse_press(event) and button==1:
            if self.body.selectable():
                self.set_focus('body')
        
        if not hasattr(self.body, 'mouse_event'):
            return False
        return self.body.mouse_event( (maxcol, maxrow-htrim-ftrim),
            event, button, col, row-htrim, focus )

        

class PileError(Exception):
    pass
        
class Pile(Widget): # either FlowWidget or BoxWidget
    def __init__(self, widget_list, focus_item=None):
        """
        widget_list -- list of widgets
        focus_item -- widget or integer index, if None the first
            selectable widget will be chosen.

        widget_list may also contain tuples such as:
        ('flow', widget) always treat widget as a flow widget
        ('fixed', height, widget) give this box widget a fixed height
        ('weight', weight, widget) if the pile is treated as a box
            widget then treat widget as a box widget with a
            height based on its relative weight value, otherwise
            treat widget as a flow widget
        
        widgets not in a tuple are the same as ('weight', 1, widget)

        If the pile is treated as a box widget there must be at least
        one 'weight' tuple in widget_list.
        """
        self.__super.__init__()
        self.widget_list = MonitoredList(widget_list)
        self.item_types = []
        for i in range(len(widget_list)):
            w = widget_list[i]
            if type(w) != type(()):
                self.item_types.append(('weight',1))
            elif w[0] == 'flow':
                f, widget = w
                self.widget_list[i] = widget
                self.item_types.append((f,None))
                w = widget
            elif w[0] in ('fixed', 'weight'):
                f, height, widget = w
                self.widget_list[i] = widget
                self.item_types.append((f,height))
                w = widget
            else:
                raise PileError, "widget list item invalid %s" % `w`
            if focus_item is None and w.selectable():
                focus_item = i
        self.widget_list.set_modified_callback(self._invalidate)
        
        if focus_item is None:
            focus_item = 0
        self.set_focus(focus_item)
        self.pref_col = 0

    def selectable(self):
        """Return True if the focus item is selectable."""
        return self.focus_item.selectable()

    def set_focus(self, item):
        """Set the item in focus.  
        
        item -- widget or integer index"""
        if type(item) == type(0):
            assert item>=0 and item<len(self.widget_list)
            self.focus_item = self.widget_list[item]
        else:
            assert item in self.widget_list
            self.focus_item = item
        self._invalidate()

    def get_focus(self):
        """Return the widget in focus."""
        return self.focus_item

    def get_pref_col(self, size):
        """Return the preferred column for the cursor, or None."""
        if not self.selectable():
            return None
        self._update_pref_col_from_focus(size)
        return self.pref_col
        
    def get_item_size(self, size, i, focus, item_rows=None):
        """
        Return a size appropriate for passing to self.widget_list[i]
        """
        maxcol = size[0]
        f, height = self.item_types[i]
        if f=='fixed':
            return (maxcol, height)
        elif f=='weight' and len(size)==2:
            if not item_rows:
                item_rows = self.get_item_rows(size, focus)
            return (maxcol, item_rows[i])
        else:
            return (maxcol,)
                    
    def get_item_rows(self, size, focus):
        """
        Return a list of the number of rows used by each widget
        in self.item_list.
        """
        remaining = None
        maxcol = size[0]
        if len(size)==2:
            remaining = size[1]
        
        l = []
        
        if remaining is None:
            # pile is a flow widget
            for (f, height), w in zip(
                self.item_types, self.widget_list):
                if f == 'fixed':
                    l.append( height )
                else:
                    l.append( w.rows( (maxcol,), focus=focus
                        and self.focus_item == w ))
            return l
            
        # pile is a box widget
        # do an extra pass to calculate rows for each widget
        wtotal = 0
        for (f, height), w in zip(self.item_types, self.widget_list):
            if f == 'flow':
                rows = w.rows((maxcol,), focus=focus and
                    self.focus_item == w )
                l.append(rows)
                remaining -= rows
            elif f == 'fixed':
                l.append(height)
                remaining -= height
            else:
                l.append(None)
                wtotal += height

        if wtotal == 0:
            raise PileError, "No weighted widgets found for Pile treated as a box widget"

        if remaining < 0: 
            remaining = 0

        i = 0
        for (f, height), li in zip(self.item_types, l):
            if li is None:
                rows = int(float(remaining)*height
                    /wtotal+0.5)
                l[i] = rows
                remaining -= rows
                wtotal -= height
            i += 1
        return l
        
    
    def render(self, size, focus=False):
        """
        Render all widgets in self.widget_list and return the results
        stacked one on top of the next.
        """
        maxcol = size[0]
        item_rows = None
        
        combinelist = []
        i = 0
        for (f, height), w in zip(self.item_types, self.widget_list):
            item_focus = self.focus_item == w
            canv = None
            if f == 'fixed':
                canv = w.render( (maxcol, height),
                    focus=focus and item_focus)
            elif f == 'flow' or len(size)==1:
                canv = w.render( (maxcol,), 
                    focus=focus and    item_focus)
            else:    
                if item_rows is None:
                    item_rows = self.get_item_rows(size, 
                        focus)
                rows = item_rows[i]
                if rows>0:
                    canv = w.render( (maxcol, rows),
                        focus=focus and    item_focus )
            if canv:
                combinelist.append((canv, i, item_focus))
            i+=1

        return CanvasCombine(combinelist)
    
    def get_cursor_coords(self, size):
        """Return the cursor coordinates of the focus widget."""
        if not self.focus_item.selectable():
            return None
        if not hasattr(self.focus_item,'get_cursor_coords'):
            return None
        
        i = self.widget_list.index(self.focus_item)
        f, height = self.item_types[i]
        item_rows = None
        maxcol = size[0]
        if f == 'fixed' or (f=='weight' and len(size)==2):
            if f == 'fixed':
                maxrow = height
            else:
                if item_rows is None:
                    item_rows = self.get_item_rows(size, 
                    focus=True)
                maxrow = item_rows[i]
            coords = self.focus_item.get_cursor_coords(
                (maxcol,maxrow))
        else:
            coords = self.focus_item.get_cursor_coords((maxcol,))

        if coords is None:
            return None
        x,y = coords
        if i > 0:
            if item_rows is None:
                item_rows = self.get_item_rows(size, focus=True)
            for r in item_rows[:i]:
                y += r
        return x, y
        
    
    def rows(self, size, focus=False ):
        """Return the number of rows required for this widget."""
        return sum(self.get_item_rows(size, focus))


    def keypress(self, size, key ):
        """Pass the keypress to the widget in focus.
        Unhandled 'up' and 'down' keys may cause a focus change."""

        maxcol = size[0]
        item_rows = None
        if len(size)==2:
            item_rows = self.get_item_rows( size, focus=True )

        i = self.widget_list.index(self.focus_item)
        f, height = self.item_types[i]
        if self.focus_item.selectable():
            tsize = self.get_item_size(size,i,True,item_rows)
            key = self.focus_item.keypress( tsize, key )
            if command_map[key] not in ('cursor up', 'cursor down'):
                return key

        if command_map[key] == 'cursor up':
            candidates = range(i-1, -1, -1) # count backwards to 0
        else: # command_map[key] == 'cursor down'
            candidates = range(i+1, len(self.widget_list))
        
        if not item_rows:
            item_rows = self.get_item_rows( size, focus=True )
    
        for j in candidates:
            if not self.widget_list[j].selectable():
                continue
            
            self._update_pref_col_from_focus(size)
            old_focus = self.focus_item
            self.set_focus(j)
            if not hasattr(self.focus_item,'move_cursor_to_coords'):
                return

            f, height = self.item_types[j]
            rows = item_rows[j]
            if command_map[key] == 'cursor up':
                rowlist = range(rows-1, -1, -1)
            else: # command_map[key] == 'cursor down'
                rowlist = range(rows)
            for row in rowlist:
                tsize=self.get_item_size(size,j,True,item_rows)
                if self.focus_item.move_cursor_to_coords(
                        tsize,self.pref_col,row):
                    break
            return                    
                
        # nothing to select
        return key


    def _update_pref_col_from_focus(self, size ):
        """Update self.pref_col from the focus widget."""
        
        widget = self.focus_item

        if not hasattr(widget,'get_pref_col'):
            return
        i = self.widget_list.index(widget)
        tsize = self.get_item_size(size,i,True)
        pref_col = widget.get_pref_col(tsize)
        if pref_col is not None: 
            self.pref_col = pref_col

    def move_cursor_to_coords(self, size, col, row):
        """Capture pref col and set new focus."""
        self.pref_col = col
        
        #FIXME guessing focus==True
        focus=True
        wrow = 0 
        item_rows = self.get_item_rows(size,focus)
        for r,w in zip(item_rows, self.widget_list):
            if wrow+r > row:
                break
            wrow += r

        if not w.selectable():
            return False
        
        if hasattr(w,'move_cursor_to_coords'):
            i = self.widget_list.index(w)
            tsize = self.get_item_size(size, i, focus, item_rows)
            rval = w.move_cursor_to_coords(tsize,col,row-wrow)
            if rval is False:
                return False
            
        self.set_focus(w)
        return True
    
    def mouse_event(self, size, event, button, col, row, focus):
        """
        Pass the event to the contained widget.
        May change focus on button 1 press.
        """
        wrow = 0
        item_rows = self.get_item_rows(size,focus)
        for r,w in zip(item_rows, self.widget_list):
            if wrow+r > row:
                break
            wrow += r

        focus = focus and self.focus_item == w
        if is_mouse_press(event) and button==1:
            if w.selectable():
                self.set_focus(w)
        
        if not hasattr(w,'mouse_event'):
            return False

        i = self.widget_list.index(w)
        tsize = self.get_item_size(size, i, focus, item_rows)
        return w.mouse_event(tsize, event, button, col, row-wrow,
            focus)



class ColumnsError(Exception):
    pass

        
class Columns(Widget): # either FlowWidget or BoxWidget
    def __init__(self, widget_list, dividechars=0, focus_column=None,
        min_width=1, box_columns=None):
        """
        widget_list -- list of flow widgets or list of box widgets
        dividechars -- blank characters between columns
        focus_column -- index into widget_list of column in focus,
            if None the first selectable widget will be chosen.
        min_width -- minimum width for each column before it is hidden
        box_columns -- a list of column indexes containing box widgets
            whose maxrow is set to the maximum of the rows 
            required by columns not listed in box_columns.

        widget_list may also contain tuples such as:
        ('fixed', width, widget) give this column a fixed width
        ('weight', weight, widget) give this column a relative weight

        widgets not in a tuple are the same as ('weight', 1, widget)    

        box_columns is ignored when this widget is being used as a
        box widget because in that case all columns are treated as box
        widgets.
        """
        self.__super.__init__()
        self.widget_list = MonitoredList(widget_list)
        self.column_types = []
        for i in range(len(widget_list)):
            w = widget_list[i]
            if type(w) != type(()):
                self.column_types.append(('weight',1))
            elif w[0] in ('fixed', 'weight'):
                f,width,widget = w
                self.widget_list[i] = widget
                self.column_types.append((f,width))
                w = widget
            else:
                raise ColumnsError, "widget list item invalid: %s" % `w`
            if focus_column is None and w.selectable():
                focus_column = i
                
        self.widget_list.set_modified_callback(self._invalidate)
        
        self.dividechars = dividechars
        if focus_column is None:
            focus_column = 0
        self.focus_col = focus_column
        self.pref_col = None
        self.min_width = min_width
        self.box_columns = box_columns
        self._cache_maxcol = None
    
    def _invalidate(self):
        self._cache_maxcol = None
        self.__super._invalidate()

    def set_focus_column( self, num ):
        """Set the column in focus by its index in self.widget_list."""
        self.focus_col = num
        self._invalidate()
    
    def get_focus_column( self ):
        """Return the focus column index."""
        return self.focus_col

    def set_focus(self, item):
        """Set the item in focus.  
        
        item -- widget or integer index"""
        if type(item) == type(0):
            assert item>=0 and item<len(self.widget_list)
            position = item
        else:
            position = self.widget_list.index(item)
        self.focus_col = position
        self._invalidate()
    
    def get_focus(self):
        """Return the widget in focus."""
        return self.widget_list[self.focus_col]

    def column_widths( self, size ):
        """Return a list of column widths.

        size -- (maxcol,) if self.widget_list contains flow widgets or
            (maxcol, maxrow) if it contains box widgets.
        """
        maxcol = size[0]
        if maxcol == self._cache_maxcol:
            return self._cache_column_widths

        col_types = self.column_types
        # hack to support old practice of editing self.widget_list
        # directly
        lwl, lct = len(self.widget_list), len(self.column_types)
        if lwl > lct:
            col_types = col_types + [('weight',1)] * (lwl-lct)
            
        widths=[]
        
        weighted = []
        shared = maxcol + self.dividechars
        growable = 0
        
        i = 0
        for t, width in col_types:
            if t == 'fixed':
                static_w = width
            else:
                static_w = self.min_width
                
            if shared < static_w + self.dividechars:
                break
        
            widths.append( static_w )    
            shared -= static_w + self.dividechars
            if t != 'fixed':
                weighted.append( (width,i) )
        
            i += 1
        
        if shared:
            # divide up the remaining space between weighted cols
            weighted.sort()
            wtotal = sum([weight for weight,i in weighted])
            grow = shared + len(weighted)*self.min_width
            for weight, i in weighted:
                width = int(float(grow) * weight / wtotal + 0.5)
                width = max(self.min_width, width)
                widths[i] = width
                grow -= width
                wtotal -= weight
        
        self._cache_maxcol = maxcol
        self._cache_column_widths = widths
        return widths
    
    def render(self, size, focus=False):
        """Render columns and return canvas.

        size -- (maxcol,) if self.widget_list contains flow widgets or
            (maxcol, maxrow) if it contains box widgets.
        """
        widths = self.column_widths( size )
        if not widths:
            return SolidCanvas(" ", size[0], (size[1:]+(1,))[0])
        
        box_maxrow = None
        if len(size)==1 and self.box_columns:
            box_maxrow = 1
            # two-pass mode to determine maxrow for box columns
            for i in range(len(widths)):
                if i in self.box_columns:
                    continue
                mc = widths[i]
                w = self.widget_list[i]
                rows = w.rows( (mc,), 
                    focus = focus and self.focus_col == i )
                box_maxrow = max(box_maxrow, rows)
        
        l = []
        for i in range(len(widths)):
            mc = widths[i]
            w = self.widget_list[i]
            if box_maxrow and i in self.box_columns:
                sub_size = (mc, box_maxrow)
            else:
                sub_size = (mc,) + size[1:]
            
            canv = w.render(sub_size, 
                focus = focus and self.focus_col == i)

            if i < len(widths)-1:
                mc += self.dividechars
            l.append((canv, i, self.focus_col == i, mc))
                
        canv = CanvasJoin(l)
        if canv.cols() < size[0]:
            canv.pad_trim_left_right(0, size[0]-canv.cols())
        return canv

    def get_cursor_coords(self, size):
        """Return the cursor coordinates from the focus widget."""
        w = self.widget_list[self.focus_col]

        if not w.selectable():
            return None
        if not hasattr(w, 'get_cursor_coords'):
            return None

        widths = self.column_widths( size )
        if len(widths) < self.focus_col+1:
            return None
        colw = widths[self.focus_col]

        coords = w.get_cursor_coords( (colw,)+size[1:] )
        if coords is None:
            return None
        x,y = coords
        x += self.focus_col * self.dividechars
        x += sum( widths[:self.focus_col] )
        return x, y

    def move_cursor_to_coords(self, size, col, row):
        """Choose a selectable column to focus based on the coords."""
        widths = self.column_widths(size)
        
        best = None
        x = 0
        for i in range(len(widths)):
            w = self.widget_list[i]
            end = x + widths[i]
            if w.selectable():
                if x > col and best is None:
                    # no other choice
                    best = i, x, end
                    break
                if x > col and col-best[2] < x-col:
                    # choose one on left
                    break
                best = i, x, end
                if col < end:
                    # choose this one
                    break
            x = end + self.dividechars
            
        if best is None:
            return False
        i, x, end = best
        w = self.widget_list[i]
        if hasattr(w,'move_cursor_to_coords'):
            if type(col)==type(0):
                move_x = min(max(0,col-x),end-x-1)
            else:
                move_x = col
            rval = w.move_cursor_to_coords((end-x,)+size[1:],
                move_x, row)
            if rval is False:
                return False
                
        self.focus_col = i
        self.pref_col = col
        self._invalidate()
        return True

    def mouse_event(self, size, event, button, col, row, focus):
        """
        Send event to appropriate column.
        May change focus on button 1 press.
        """
        widths = self.column_widths(size)
        
        x = 0
        for i in range(len(widths)):
            if col < x:
                return False
            w = self.widget_list[i]
            end = x + widths[i]
            
            if col >= end:
                x = end + self.dividechars
                continue

            focus = focus and self.focus_col == i
            if is_mouse_press(event) and button == 1:
                if w.selectable():
                    self.set_focus(w)

            if not hasattr(w,'mouse_event'):
                return False

            return w.mouse_event((end-x,)+size[1:], event, button, 
                col - x, row, focus)
        return False
        
    def get_pref_col(self, size):
        """Return the pref col from the column in focus."""
        maxcol = size[0]
        widths = self.column_widths( (maxcol,) )
    
        w = self.widget_list[self.focus_col]
        if len(widths) < self.focus_col+1:
            return 0
        col = None
        if hasattr(w,'get_pref_col'):
            col = w.get_pref_col((widths[self.focus_col],)+size[1:])
            if type(col)==type(0):
                col += self.focus_col * self.dividechars
                col += sum( widths[:self.focus_col] )
        if col is None:
            col = self.pref_col
        if col is None and w.selectable():
            col = widths[self.focus_col]/2
            col += self.focus_col * self.dividechars
            col += sum( widths[:self.focus_col] )
        return col

    def rows(self, size, focus=0 ):
        """Return the number of rows required by the columns.
        Only makes sense if self.widget_list contains flow widgets."""
        widths = self.column_widths(size)
    
        rows = 1
        for i in range(len(widths)):
            if self.box_columns and i in self.box_columns:
                continue
            mc = widths[i]
            w = self.widget_list[i]
            rows = max( rows, w.rows( (mc,), 
                focus = focus and self.focus_col == i ) )
        return rows
            
    def keypress(self, size, key):
        """Pass keypress to the focus column.

        size -- (maxcol,) if self.widget_list contains flow widgets or
            (maxcol, maxrow) if it contains box widgets.
        """
        if self.focus_col is None: return key
        
        widths = self.column_widths( size )
        if self.focus_col < 0 or self.focus_col >= len(widths):
            return key

        i = self.focus_col
        mc = widths[i]
        w = self.widget_list[i]
        if command_map[key] not in ('cursor up', 'cursor down',
            'cursor page up', 'cursor page down'):
            self.pref_col = None
        key = w.keypress( (mc,)+size[1:], key )
        
        if command_map[key] not in ('cursor left', 'cursor right'):
            return key

        if command_map[key] == 'cursor left':
            candidates = range(i-1, -1, -1) # count backwards to 0
        else: # key == 'right'
            candidates = range(i+1, len(widths))

        for j in candidates:
            if not self.widget_list[j].selectable():
                continue

            self.set_focus_column( j )
            return
        return key
            

    def selectable(self):
        """Return the selectable value of the focus column."""
        return self.widget_list[self.focus_col].selectable()






def _test():
    import doctest
    doctest.testmod()

if __name__=='__main__':
    _test()

########NEW FILE########
__FILENAME__ = curses_display
#!/usr/bin/python
#
# Urwid curses output wrapper.. the horror..
#    Copyright (C) 2004-2007  Ian Ward
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
Curses-based UI implementation
"""

from __future__ import nested_scopes

import curses
import _curses
import sys

import util
import escape

from display_common import RealTerminal

KEY_RESIZE = 410 # curses.KEY_RESIZE (sometimes not defined)
KEY_MOUSE = 409 # curses.KEY_MOUSE

_curses_colours = {
    'default':        (-1,                    0),
    'black':          (curses.COLOR_BLACK,    0),
    'dark red':       (curses.COLOR_RED,      0),
    'dark green':     (curses.COLOR_GREEN,    0),
    'brown':          (curses.COLOR_YELLOW,   0),
    'dark blue':      (curses.COLOR_BLUE,     0),
    'dark magenta':   (curses.COLOR_MAGENTA,  0),
    'dark cyan':      (curses.COLOR_CYAN,     0),
    'light gray':     (curses.COLOR_WHITE,    0),
    'dark gray':      (curses.COLOR_BLACK,    1),
    'light red':      (curses.COLOR_RED,      1),
    'light green':    (curses.COLOR_GREEN,    1),
    'yellow':         (curses.COLOR_YELLOW,   1),
    'light blue':     (curses.COLOR_BLUE,     1),
    'light magenta':  (curses.COLOR_MAGENTA,  1),
    'light cyan':     (curses.COLOR_CYAN,     1),
    'white':          (curses.COLOR_WHITE,    1),
}


# replace control characters with ?'s
_trans_table = "?"*32+"".join([chr(x) for x in range(32,256)])


class Screen(RealTerminal):
    def __init__(self):
        super(Screen,self).__init__()
        self.curses_pairs = [
            (None,None), # Can't be sure what pair 0 will default to
        ]
        self.palette = {}
        self.has_color = False
        self.s = None
        self.cursor_state = None
        self._keyqueue = []
        self.prev_input_resize = 0
        self.set_input_timeouts()
        self.last_bstate = 0
        self._started = False
    
    started = property(lambda self: self._started)

    def register_palette( self, l ):
        """Register a list of palette entries.

        l -- list of (name, foreground, background, mono),
             (name, foreground, background) or
             (name, same_as_other_name) palette entries.

        calls self.register_palette_entry for each item in l
        """
        
        for item in l:
            if len(item) in (3,4):
                self.register_palette_entry( *item )
                continue
            assert len(item) == 2, "Invalid register_palette usage"
            name, like_name = item
            if not self.palette.has_key(like_name):
                raise Exception("palette entry '%s' doesn't exist"%like_name)
            self.palette[name] = self.palette[like_name]

    def register_palette_entry( self, name, foreground, background,
        mono=None):
        """Register a single palette entry.

        name -- new entry/attribute name
        foreground -- foreground colour, one of: 'black', 'dark red',
            'dark green', 'brown', 'dark blue', 'dark magenta',
            'dark cyan', 'light gray', 'dark gray', 'light red',
            'light green', 'yellow', 'light blue', 'light magenta',
            'light cyan', 'white', 'default' (black if unable to
            use terminal's default)
        background -- background colour, one of: 'black', 'dark red',
            'dark green', 'brown', 'dark blue', 'dark magenta',
            'dark cyan', 'light gray', 'default' (light gray if
            unable to use terminal's default)
        mono -- monochrome terminal attribute, one of: None (default),
            'bold',    'underline', 'standout', or a tuple containing
            a combination eg. ('bold','underline')
            
        """
        assert not self._started

        fg_a, fg_b = _curses_colours[foreground]
        bg_a, bg_b = _curses_colours[background]
        if bg_b: # can't do bold backgrounds
            raise Exception("%s is not a supported background colour"%background )
        assert (mono is None or 
            mono in (None, 'bold', 'underline', 'standout') or
            type(mono)==type(()))
    
        for i in range(len(self.curses_pairs)):
            pair = self.curses_pairs[i]
            if pair == (fg_a, bg_a): break
        else:
            i = len(self.curses_pairs)
            self.curses_pairs.append( (fg_a, bg_a) )
        
        self.palette[name] = (i, fg_b, mono)
        
    
    def set_mouse_tracking(self):
        """
        Enable mouse tracking.  
        
        After calling this function get_input will include mouse
        click events along with keystrokes.
        """
        rval = curses.mousemask( 0 
            | curses.BUTTON1_PRESSED | curses.BUTTON1_RELEASED
            | curses.BUTTON2_PRESSED | curses.BUTTON2_RELEASED
            | curses.BUTTON3_PRESSED | curses.BUTTON3_RELEASED
            | curses.BUTTON4_PRESSED | curses.BUTTON4_RELEASED
            | curses.BUTTON_SHIFT | curses.BUTTON_ALT
            | curses.BUTTON_CTRL )

    def start(self):
        """
        Initialize the screen and input mode.
        """
        assert self._started == False

        self.s = curses.initscr()
        self._started = True
        self.has_color = curses.has_colors()
        if self.has_color:
            curses.start_color()
            if curses.COLORS < 8:
                # not colourful enough
                self.has_color = False
        if self.has_color:
            try:
                curses.use_default_colors()
                self.has_default_colors=True
            except _curses.error:
                self.has_default_colors=False
        self._setup_colour_pairs()
        curses.noecho()
        curses.meta(1)
        curses.halfdelay(10) # use set_input_timeouts to adjust
        self.s.keypad(0)
        
        if not self._signal_keys_set:
            self._old_signal_keys = self.tty_signal_keys()

    
    def stop(self):
        """
        Restore the screen.
        """
        if self._started == False:
            return
        curses.echo()
        self._curs_set(1)
        try:
            curses.endwin()
        except _curses.error:
            pass # don't block original error with curses error
        
        self._started = False
        
        if self._old_signal_keys:
            self.tty_signal_keys(*self._old_signal_keys)
    
    def run_wrapper(self,fn):
        """Call fn in fullscreen mode.  Return to normal on exit.
        
        This function should be called to wrap your main program loop.
        Exception tracebacks will be displayed in normal mode.
        """
    
        try:
            self.start()
            return fn()
        finally:
            self.stop()

    def _setup_colour_pairs(self):
    
        k = 1
        if self.has_color:
            if len(self.curses_pairs) > curses.COLOR_PAIRS:
                raise Exception("Too many colour pairs!  Use fewer combinations.")
        
            for fg,bg in self.curses_pairs[1:]:
                if not self.has_default_colors and fg == -1:
                    fg = _curses_colours["black"][0]
                if not self.has_default_colors and bg == -1:
                    bg = _curses_colours["light gray"][0]
                curses.init_pair(k,fg,bg)
                k+=1
        else:
            wh, bl = curses.COLOR_WHITE, curses.COLOR_BLACK
        
        self.attrconv = {}
        for name, (cp, a, mono) in self.palette.items():
            if self.has_color:
                self.attrconv[name] = curses.color_pair(cp)
                if a: self.attrconv[name] |= curses.A_BOLD
            elif type(mono)==type(()):
                attr = 0
                for m in mono:
                    attr |= self._curses_attr(m)
                self.attrconv[name] = attr
            else:
                attr = self._curses_attr(mono)
                self.attrconv[name] = attr
    
    def _curses_attr(self, a):
        if a == 'bold':
            return curses.A_BOLD
        elif a == 'standout':
            return curses.A_STANDOUT
        elif a == 'underline':
            return curses.A_UNDERLINE
        else:
            return 0
                
                


    def _curs_set(self,x):
        if self.cursor_state== "fixed" or x == self.cursor_state: 
            return
        try:
            curses.curs_set(x)
            self.cursor_state = x
        except _curses.error:
            self.cursor_state = "fixed"

    
    def _clear(self):
        self.s.clear()
        self.s.refresh()
    
    
    def _getch(self, wait_tenths):
        if wait_tenths==0:
            return self._getch_nodelay()
        if wait_tenths is None:
            curses.cbreak()
        else:
            curses.halfdelay(wait_tenths)
        self.s.nodelay(0)
        return self.s.getch()
    
    def _getch_nodelay(self):
        self.s.nodelay(1)
        while 1:
            # this call fails sometimes, but seems to work when I try again
            try:
                curses.cbreak()
                break
            except _curses.error:
                pass
            
        return self.s.getch()

    def set_input_timeouts(self, max_wait=None, complete_wait=0.1, 
        resize_wait=0.1):
        """
        Set the get_input timeout values.  All values have a granularity
        of 0.1s, ie. any value between 0.15 and 0.05 will be treated as
        0.1 and any value less than 0.05 will be treated as 0.  The
        maximum timeout value for this module is 25.5 seconds.
    
        max_wait -- amount of time in seconds to wait for input when
            there is no input pending, wait forever if None
        complete_wait -- amount of time in seconds to wait when
            get_input detects an incomplete escape sequence at the
            end of the available input
        resize_wait -- amount of time in seconds to wait for more input
            after receiving two screen resize requests in a row to
            stop urwid from consuming 100% cpu during a gradual
            window resize operation
        """

        def convert_to_tenths( s ):
            if s is None:
                return None
            return int( (s+0.05)*10 )

        self.max_tenths = convert_to_tenths(max_wait)
        self.complete_tenths = convert_to_tenths(complete_wait)
        self.resize_tenths = convert_to_tenths(resize_wait)
    
    def get_input(self, raw_keys=False):
        """Return pending input as a list.

        raw_keys -- return raw keycodes as well as translated versions

        This function will immediately return all the input since the
        last time it was called.  If there is no input pending it will
        wait before returning an empty list.  The wait time may be
        configured with the set_input_timeouts function.

        If raw_keys is False (default) this function will return a list
        of keys pressed.  If raw_keys is True this function will return
        a ( keys pressed, raw keycodes ) tuple instead.
        
        Examples of keys returned
        -------------------------
        ASCII printable characters:  " ", "a", "0", "A", "-", "/" 
        ASCII control characters:  "tab", "enter"
        Escape sequences:  "up", "page up", "home", "insert", "f1"
        Key combinations:  "shift f1", "meta a", "ctrl b"
        Window events:  "window resize"
        
        When a narrow encoding is not enabled
        "Extended ASCII" characters:  "\\xa1", "\\xb2", "\\xfe"

        When a wide encoding is enabled
        Double-byte characters:  "\\xa1\\xea", "\\xb2\\xd4"

        When utf8 encoding is enabled
        Unicode characters: u"\\u00a5", u'\\u253c"

        Examples of mouse events returned
        ---------------------------------
        Mouse button press: ('mouse press', 1, 15, 13), 
                            ('meta mouse press', 2, 17, 23)
        Mouse button release: ('mouse release', 0, 18, 13),
                              ('ctrl mouse release', 0, 17, 23)
        """
        assert self._started
        
        keys, raw = self._get_input( self.max_tenths )
        
        # Avoid pegging CPU at 100% when slowly resizing, and work
        # around a bug with some braindead curses implementations that 
        # return "no key" between "window resize" commands 
        if keys==['window resize'] and self.prev_input_resize:
            while True:
                keys, raw2 = self._get_input(self.resize_tenths)
                raw += raw2
                if not keys:
                    keys, raw2 = self._get_input( 
                        self.resize_tenths)
                    raw += raw2
                if keys!=['window resize']:
                    break
            if keys[-1:]!=['window resize']:
                keys.append('window resize')

                
        if keys==['window resize']:
            self.prev_input_resize = 2
        elif self.prev_input_resize == 2 and not keys:
            self.prev_input_resize = 1
        else:
            self.prev_input_resize = 0
        
        if raw_keys:
            return keys, raw
        return keys
        
        
    def _get_input(self, wait_tenths):
        # this works around a strange curses bug with window resizing 
        # not being reported correctly with repeated calls to this
        # function without a doupdate call in between
        curses.doupdate() 
        
        key = self._getch(wait_tenths)
        resize = False
        raw = []
        keys = []
        
        while key >= 0:
            raw.append(key)
            if key==KEY_RESIZE: 
                resize = True
            elif key==KEY_MOUSE:
                keys += self._encode_mouse_event()
            else:
                keys.append(key)
            key = self._getch_nodelay()

        processed = []
        
        try:
            while keys:
                run, keys = escape.process_keyqueue(keys, True)
                processed += run
        except escape.MoreInputRequired:
            key = self._getch(self.complete_tenths)
            while key >= 0:
                raw.append(key)
                if key==KEY_RESIZE: 
                    resize = True
                elif key==KEY_MOUSE:
                    keys += self._encode_mouse_event()
                else:
                    keys.append(key)
                key = self._getch_nodelay()
            while keys:
                run, keys = escape.process_keyqueue(keys, False)
                processed += run

        if resize:
            processed.append('window resize')

        return processed, raw
        
        
    def _encode_mouse_event(self):
        # convert to escape sequence
        last = next = self.last_bstate
        (id,x,y,z,bstate) = curses.getmouse()
        
        mod = 0
        if bstate & curses.BUTTON_SHIFT:    mod |= 4
        if bstate & curses.BUTTON_ALT:        mod |= 8
        if bstate & curses.BUTTON_CTRL:        mod |= 16
        
        l = []
        def append_button( b ):
            b |= mod
            l.extend([ 27, ord('['), ord('M'), b+32, x+33, y+33 ])
        
        if bstate & curses.BUTTON1_PRESSED and last & 1 == 0:
            append_button( 0 )
            next |= 1
        if bstate & curses.BUTTON2_PRESSED and last & 2 == 0:
            append_button( 1 )
            next |= 2
        if bstate & curses.BUTTON3_PRESSED and last & 4 == 0:
            append_button( 2 )
            next |= 4
        if bstate & curses.BUTTON4_PRESSED and last & 8 == 0:
            append_button( 64 )
            next |= 8
        if bstate & curses.BUTTON1_RELEASED and last & 1:
            append_button( 0 + escape.MOUSE_RELEASE_FLAG )
            next &= ~ 1
        if bstate & curses.BUTTON2_RELEASED and last & 2:
            append_button( 1 + escape.MOUSE_RELEASE_FLAG )
            next &= ~ 2
        if bstate & curses.BUTTON3_RELEASED and last & 4:
            append_button( 2 + escape.MOUSE_RELEASE_FLAG )
            next &= ~ 4
        if bstate & curses.BUTTON4_RELEASED and last & 8:
            append_button( 64 + escape.MOUSE_RELEASE_FLAG )
            next &= ~ 8
        
        self.last_bstate = next
        return l
            

    def _dbg_instr(self): # messy input string (intended for debugging)
        curses.echo()
        self.s.nodelay(0)
        curses.halfdelay(100)
        str = self.s.getstr()
        curses.noecho()
        return str
        
    def _dbg_out(self,str): # messy output function (intended for debugging)
        self.s.clrtoeol()
        self.s.addstr(str)
        self.s.refresh()
        self._curs_set(1)
        
    def _dbg_query(self,question): # messy query (intended for debugging)
        self._dbg_out(question)
        return self._dbg_instr()
    
    def _dbg_refresh(self):
        self.s.refresh()



    def get_cols_rows(self):
        """Return the terminal dimensions (num columns, num rows)."""
        rows,cols = self.s.getmaxyx()
        return cols,rows
        

    def _setattr(self, a):
        if a is None:
            self.s.attrset( 0 )
            return
        if not self.attrconv.has_key(a):
            raise Exception, "Attribute %s not registered!"%`a`
        self.s.attrset( self.attrconv[a] )
                
            
            
    def draw_screen(self, (cols, rows), r ):
        """Paint screen with rendered canvas."""
        assert self._started
        
        assert r.rows() == rows, "canvas size and passed size don't match"
    
        y = -1
        for row in r.content():
            y += 1
            try:
                self.s.move( y, 0 )
            except _curses.error:
                # terminal shrunk? 
                # move failed so stop rendering.
                return
            
            first = True
            lasta = None
            nr = 0
            for a, cs, seg in row:
                seg = seg.translate( _trans_table )
                if first or lasta != a:
                    self._setattr(a)
                    lasta = a
                try:
                    if cs == "0":
                        for i in range(len(seg)):
                            self.s.addch( 0x400000 +
                                ord(seg[i]) )
                    else:
                        assert cs is None
                        self.s.addstr( seg )
                except _curses.error:
                    # it's ok to get out of the
                    # screen on the lower right
                    if (y == rows-1 and nr == len(row)-1):
                        pass
                    else:
                        # perhaps screen size changed
                        # quietly abort.
                        return
                nr += 1
        if r.cursor is not None:
            x,y = r.cursor
            self._curs_set(1)
            try:
                self.s.move(y,x)
            except _curses.error:
                pass
        else:
            self._curs_set(0)
            self.s.move(0,0)
        
        self.s.refresh()
        self.keep_cache_alive_link = r


    def clear(self):
        """
        Force the screen to be completely repainted on the next
        call to draw_screen().
        """
        self.s.clear()




class _test:
    def __init__(self):
        self.ui = Screen()
        self.l = _curses_colours.keys()
        self.l.sort()
        for c in self.l:
            self.ui.register_palette( [
                (c+" on black", c, 'black', 'underline'),
                (c+" on dark blue",c, 'dark blue', 'bold'),
                (c+" on light gray",c,'light gray', 'standout'),
                ])
        self.ui.run_wrapper(self.run)
        
    def run(self):
        class FakeRender: pass
        r = FakeRender()
        text = ["  has_color = "+`self.ui.has_color`,""]
        attr = [[],[]]
        r.coords = {}
        r.cursor = None
        
        for c in self.l:
            t = ""
            a = []
            for p in c+" on black",c+" on dark blue",c+" on light gray":
                
                a.append((p,27))
                t=t+ (p+27*" ")[:27]
            text.append( t )
            attr.append( a )

        text += ["","return values from get_input(): (q exits)", ""]
        attr += [[],[],[]]
        cols,rows = self.ui.get_cols_rows()
        keys = None
        while keys!=['q']:
            r.text=([t.ljust(cols) for t in text]+[""]*rows)[:rows]
            r.attr=(attr+[[]]*rows) [:rows]
            self.ui.draw_screen((cols,rows),r)
            keys, raw = self.ui.get_input( raw_keys = True )
            if 'window resize' in keys:
                cols, rows = self.ui.get_cols_rows()
            if not keys:
                continue
            t = ""
            a = []
            for k in keys:
                if type(k) == type(u""): k = k.encode("utf-8")
                t += "'"+k + "' "
                a += [(None,1), ('yellow on dark blue',len(k)),
                    (None,2)]
            
            text.append(t + ": "+ `raw`)
            attr.append(a)
            text = text[-rows:]
            attr = attr[-rows:]
                
                


if '__main__'==__name__:
    _test()

########NEW FILE########
__FILENAME__ = decoration
#!/usr/bin/python
#
# Urwid widget decoration classes
#    Copyright (C) 2004-2010  Ian Ward
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


from util import *
from widget import *
from split_repr import remove_defaults


class WidgetDecoration(Widget):  # "decorator" was already taken
    def __init__(self, original_widget):
        """
        original_widget -- the widget being decorated

        This is a base class for decoration widgets, widgets
        that contain one or more widgets and only ever have
        a single focus.  This type of widget will affect the
        display or behaviour of the original_widget but it is
        not part of determining a chain of focus.

        Don't actually do this -- use a WidgetDecoration subclass
        instead, these are not real widgets:
        >>> WidgetDecoration(Text("hi"))
        <WidgetDecoration flow widget <Text flow widget 'hi'>>
        """
        self._original_widget = original_widget
    def _repr_words(self):
        return self.__super._repr_words() + [repr(self._original_widget)]
    
    def _get_original_widget(self):
        return self._original_widget
    def _set_original_widget(self, original_widget):
        self._original_widget = original_widget
        self._invalidate()
    original_widget = property(_get_original_widget, _set_original_widget)

    def _get_base_widget(self):
        """
        Return the widget without decorations.  If there is only one
        Decoration then this is the same as original_widget.

        >>> t = Text('hello')
        >>> wd1 = WidgetDecoration(t)
        >>> wd2 = WidgetDecoration(wd1)
        >>> wd3 = WidgetDecoration(wd2)
        >>> wd3.original_widget is wd2
        True
        >>> wd3.base_widget is t
        True
        """
        w = self
        while hasattr(w, '_original_widget'):
            w = w._original_widget
        return w
    
    base_widget = property(_get_base_widget)

    def selectable(self):
        return self._original_widget.selectable()

    def sizing(self):
        return self._original_widget.sizing()


class AttrMapError(WidgetError):
    pass

class AttrMap(WidgetDecoration):
    """
    AttrMap is a decoration that maps one set of attributes to another for
    a FlowWidget or BoxWidget
    """
    no_cache = ["rows"]

    def __init__(self, w, attr_map, focus_map=None):
        """
        w -- widget to wrap (stored as self.original_widget)
        attr_map -- attribute to apply to w, or dictionary of attribute mappings
        focus_map -- attribute to apply when in focus or dictionary of
            attribute mappings, if None use attr
        
        This object will pass all function calls and variable references
        to the wrapped widget.

        >>> AttrMap(Divider("!"), 'bright')
        <AttrMap flow widget <Divider flow widget div_char='!'> attr_map={None: 'bright'}>
        >>> AttrMap(Edit(), 'notfocus', 'focus')
        <AttrMap selectable flow widget <Edit selectable flow widget '' edit_pos=0> attr_map={None: 'notfocus'} focus_map={None: 'focus'}>
        >>> size = (5,)
        >>> am = AttrMap(Text("hi"), 'greeting', 'fgreet')
        >>> am.render(size, focus=False).content().next()
        [('greeting', None, 'hi   ')]
        >>> am.render(size, focus=True).content().next()
        [('fgreet', None, 'hi   ')]
        >>> am2 = AttrMap(Text(('word', "hi")), {None:'bg', 'word':'greeting'})
        >>> am2
        <AttrMap flow widget <Text flow widget 'hi'> attr_map={None: 'bg', 'word': 'greeting'}>
        >>> am2.render(size).content().next()
        [('greeting', None, 'hi'), ('bg', None, '   ')]
        """
        self.__super.__init__(w)

        if type(attr_map) != dict:
            self.set_attr_map({None: attr_map})
        else:
            self.set_attr_map(attr_map)

        if focus_map is not None and type(focus_map) != dict:
            self.set_focus_map({None: focus_map})
        else:
            self.set_focus_map(focus_map)
    
    def _repr_attrs(self):
        # only include the focus_attr when it takes effect (not None)
        d = dict(self.__super._repr_attrs(), attr_map=self._attr_map)
        if self._focus_map is not None:
            d['focus_map'] = self._focus_map
        return d
    
    def get_attr_map(self):
        # make a copy so ours is not accidentally modified
        # FIXME: a dictionary that detects modifications would be better
        return dict(self._attr_map)
    def set_attr_map(self, attr_map):
        """
        Set the attribute mapping dictionary {from_attr: to_attr, ...}

        Note this function does not accept a single attribute the way the
        constructor does.  You must specify {None: attribute} instead.

        >> w = AttrMap(Text("hi"), None)
        >> w.set_attr({'a':'b'})
        >> w
        <AttrMap flow widget <Text flow widget 'hi'> attr_map={'a': 'b'}>
        """
        for from_attr, to_attr in attr_map.items():
            if not from_attr.__hash__ or not to_attr.__hash__:
                raise AttrMapError("%r:%r attribute mapping is invalid.  "
                    "Attributes must be hashable" % (from_attr, to_attr))
        self._attr_map = attr_map
        self._invalidate()
    attr_map = property(get_attr_map, set_attr_map)
    
    def get_focus_map(self):
        # make a copy so ours is not accidentally modified
        # FIXME: a dictionary that detects modifications would be better
        if self._focus_map:
            return dict(self._focus_map)
    def set_focus_map(self, focus_map):
        """
        Set the focus attribute mapping dictionary 
        {from_attr: to_attr, ...}
        
        If None this widget will use the attr mapping instead (no change 
        when in focus).
        
        Note this function does not accept a single attribute the way the
        constructor does.  You must specify {None: attribute} instead.

        >> w = AttrMap(Text("hi"), {})
        >> w.set_focus_map({'a':'b'})
        >> w
        <AttrMap flow widget <Text flow widget 'hi'> attr_map={} focus_map={'a': 'b'}>
        >> w.set_focus_map(None)
        >> w
        <AttrMap flow widget <Text flow widget 'hi'> attr_map={}>
        """
        if focus_map is not None:
            for from_attr, to_attr in focus_map.items():
                if not from_attr.__hash__ or not to_attr.__hash__:
                    raise AttrMapError("%r:%r attribute mapping is invalid.  "
                        "Attributes must be hashable" % (from_attr, to_attr))
        self._focus_map = focus_map
        self._invalidate()
    focus_map = property(get_focus_map, set_focus_map)
        
    def render(self, size, focus=False):
        """
        Render wrapped widget and apply attribute. Return canvas.
        """
        attr_map = self._attr_map
        if focus and self._focus_map is not None:
            attr_map = self._focus_map
        canv = self._original_widget.render(size, focus=focus)
        canv = CompositeCanvas(canv)
        canv.fill_attr_apply(attr_map)
        return canv
    
    # just use our original widget's methods
    selectable = property(lambda self:self._original_widget.selectable)
    get_cursor_coords = property(lambda self:self._original_widget.get_cursor_coords)
    get_pref_col = property(lambda self:self._original_widget.get_pref_col)
    keypress = property(lambda self:self._original_widget.keypress)
    move_cursor_to_coords = property(lambda self:self._original_widget.move_cursor_to_coords)
    rows = property(lambda self:self._original_widget.rows)
    mouse_event = property(lambda self:self._original_widget.mouse_event)
    sizing = property(lambda self:self._original_widget.sizing)



class AttrWrap(AttrMap):
    def __init__(self, w, attr, focus_attr=None):
        """
        w -- widget to wrap (stored as self.original_widget)
        attr -- attribute to apply to w
        focus_attr -- attribute to apply when in focus, if None use attr
        
        This widget is a special case of the new AttrMap widget, and it
        will pass all function calls and variable references to the wrapped 
        widget.  This class is maintained for backwards compatibility only,
        new code should use AttrMap instead.

        >>> AttrWrap(Divider("!"), 'bright')
        <AttrWrap flow widget <Divider flow widget div_char='!'> attr='bright'>
        >>> AttrWrap(Edit(), 'notfocus', 'focus')
        <AttrWrap selectable flow widget <Edit selectable flow widget '' edit_pos=0> attr='notfocus' focus_attr='focus'>
        >>> size = (5,)
        >>> aw = AttrWrap(Text("hi"), 'greeting', 'fgreet')
        >>> aw.render(size, focus=False).content().next()
        [('greeting', None, 'hi   ')]
        >>> aw.render(size, focus=True).content().next()
        [('fgreet', None, 'hi   ')]
        """
        self.__super.__init__(w, attr, focus_attr)
    
    def _repr_attrs(self):
        # only include the focus_attr when it takes effect (not None)
        d = dict(self.__super._repr_attrs(), attr=self.attr)
        del d['attr_map']
        if 'focus_map' in d:
            del d['focus_map']
        if self.focus_attr is not None:
            d['focus_attr'] = self.focus_attr
        return d
    
    # backwards compatibility, widget used to be stored as w
    get_w = WidgetDecoration._get_original_widget
    set_w = WidgetDecoration._set_original_widget
    w = property(get_w, set_w)
    
    def get_attr(self):
        return self.attr_map[None]
    def set_attr(self, attr):
        """
        Set the attribute to apply to the wrapped widget

        >> w = AttrWrap(Divider("-"), None)
        >> w.set_attr('new_attr')
        >> w
        <AttrWrap flow widget <Divider flow widget '-'> attr='new_attr'>
        """
        self.set_attr_map({None: attr})
    attr = property(get_attr, set_attr)
    
    def get_focus_attr(self):
        focus_map = self.focus_map
        if focus_map:
            return focus_map[None]
    def set_focus_attr(self, focus_attr):
        """
        Set the attribute to apply to the wapped widget when it is in
        focus
        
        If None this widget will use the attr instead (no change when in 
        focus).

        >> w = AttrWrap(Divider("-"), 'old')
        >> w.set_focus_attr('new_attr')
        >> w
        <AttrWrap flow widget <Divider flow widget '-'> attr='old' focus_attr='new_attr'>
        >> w.set_focus_attr(None)
        >> w
        <AttrWrap flow widget <Divider flow widget '-'> attr='old'>
        """
        self.set_focus_map({None: focus_attr})
    focus_attr = property(get_focus_attr, set_focus_attr)

    def __getattr__(self,name):
        """
        Call getattr on wrapped widget.  This has been the longstanding
        behaviour of AttrWrap, but is discouraged.  New code should be
        using AttrMap and .base_widget or .original_widget instad.
        """
        return getattr(self._original_widget, name)


    def sizing(self):
        return self._original_widget.sizing()


class BoxAdapterError(Exception):
    pass

class BoxAdapter(WidgetDecoration):
    """
    Adapter for using a box widget where a flow widget would usually go
    """
    no_cache = ["rows"]

    def __init__(self, box_widget, height):
        """
        Create a flow widget that contains a box widget

        box_widget -- box widget (stored as self.original_widget)
        height -- number of rows for box widget

        >>> BoxAdapter(SolidFill("x"), 5) # 5-rows of x's
        <BoxAdapter flow widget <SolidFill box widget 'x'> height=5>
        """
        if hasattr(box_widget, 'sizing') and BOX not in box_widget.sizing():
            raise BoxAdapterError("%r is not a box widget" % 
                box_widget)
        WidgetDecoration.__init__(self,box_widget)
        
        self.height = height
    
    def _repr_attrs(self):
        return dict(self.__super._repr_attrs(), height=self.height)

    # originally stored as box_widget, keep for compatibility
    box_widget = property(WidgetDecoration._get_original_widget, 
        WidgetDecoration._set_original_widget)

    def sizing(self):
        return set([FLOW])

    def rows(self, size, focus=False):
        """
        Return the predetermined height (behave like a flow widget)
        
        >>> BoxAdapter(SolidFill("x"), 5).rows((20,))
        5
        """
        return self.height

    # The next few functions simply tack-on our height and pass through
    # to self._original_widget
    def get_cursor_coords(self, size):
        (maxcol,) = size
        if not hasattr(self._original_widget,'get_cursor_coords'):
            return None
        return self._original_widget.get_cursor_coords((maxcol, self.height))
    
    def get_pref_col(self, size):
        (maxcol,) = size
        if not hasattr(self._original_widget,'get_pref_col'):
            return None
        return self._original_widget.get_pref_col((maxcol, self.height))
    
    def keypress(self, size, key):
        (maxcol,) = size
        return self._original_widget.keypress((maxcol, self.height), key)
    
    def move_cursor_to_coords(self, size, col, row):
        (maxcol,) = size
        if not hasattr(self._original_widget,'move_cursor_to_coords'):
            return True
        return self._original_widget.move_cursor_to_coords((maxcol,
            self.height), col, row )
    
    def mouse_event(self, size, event, button, col, row, focus):
        (maxcol,) = size
        if not hasattr(self._original_widget,'mouse_event'):
            return False
        return self._original_widget.mouse_event((maxcol, self.height),
            event, button, col, row, focus)
    
    def render(self, size, focus=False):
        (maxcol,) = size
        canv = self._original_widget.render((maxcol, self.height), focus)
        canv = CompositeCanvas(canv)
        return canv
    
    def __getattr__(self, name):
        """
        Pass calls to box widget.
        """
        return getattr(self.box_widget, name)



class PaddingError(Exception):
    pass

class Padding(WidgetDecoration):
    def __init__(self, w, align=LEFT, width=PACK, min_width=None, 
        left=0, right=0):
        r"""
        w -- a box, flow or fixed widget to pad on the left and/or right
            this widget is stored as self.original_widget
        align -- one of:
            'left', 'center', 'right'
            ('relative', percentage 0=left 100=right)
        width -- one of:
            fixed number of columns for self.original_widget 
            'pack'   try to pack self.original_widget to its ideal size
            ('relative', percentage of total width)
            'clip'   to enable clipping mode for a fixed widget
        min_width -- the minimum number of columns for 
            self.original_widget or None
        left -- a fixed number of columns to pad on the left
        right -- a fixed number of columns to pad on thr right
            
        Clipping Mode: (width='clip')
        In clipping mode this padding widget will behave as a flow
        widget and self.original_widget will be treated as a fixed 
        widget.  self.original_widget will will be clipped to fit
        the available number of columns.  For example if align is 
        'left' then self.original_widget may be clipped on the right.

        >>> size = (7,)
        >>> Padding(Text("Head"), ('relative', 20)).render(size).text
        [' Head  ']
        >>> Padding(Divider("-"), left=2, right=1).render(size).text
        ['  ---- ']
        >>> Padding(Divider("*"), 'center', 3).render(size).text
        ['  ***  ']
        >>> p=Padding(Text("1234"), 'left', 2, None, 1, 1)
        >>> p
        <Padding flow widget <Text flow widget '1234'> left=1 right=1 width=2>
        >>> p.render(size).text   # align against left
        [' 12    ', ' 34    ']
        >>> p.align = 'right'
        >>> p.render(size).text   # align against right
        ['    12 ', '    34 ']
        >>> Padding(Text("hi\nthere"), 'right').render(size).text
        ['  hi   ', '  there']

        """
        self.__super.__init__(w)

        # convert obsolete parameters 'fixed left' and 'fixed right':
        if type(align) == type(()) and align[0] in ('fixed left', 
            'fixed right'):
            if align[0]=='fixed left':
                left = align[1]
                align = LEFT
            else:
                right = align[1]
                align = RIGHT
        if type(width) == type(()) and width[0] in ('fixed left', 
            'fixed right'):
            if width[0]=='fixed left':
                left = width[1]
            else:
                right = width[1]
            width = RELATIVE_100

        # convert old clipping mode width=None to width='clip'
        if width is None:
            width = CLIP

        self.left = left
        self.right = right
        self._align_type, self._align_amount = normalize_align(align,
            PaddingError)
        self._width_type, self._width_amount = normalize_width(width,
            PaddingError)
        self.min_width = min_width
    
    def sizing(self):
        if self._width_type == CLIP:
            return set([FLOW])
        return self.original_widget.sizing()

    def _repr_attrs(self):
        attrs = dict(self.__super._repr_attrs(),
            align=self.align,
            width=self.width,
            left=self.left,
            right=self.right,
            min_width=self.min_width)
        return remove_defaults(attrs, Padding.__init__)
    
    def _get_align(self):
        """
        Return the padding alignment setting.
        """
        return simplify_align(self._align_type, self._align_amount)
    def _set_align(self, align):
        """
        Set the padding alignment.
        """
        self._align_type, self._align_amount = normalize_align(align,
            PaddingError)
    align = property(_get_align, _set_align)

    def _get_width(self):
        """
        Return the padding widthment setting.
        """
        return simplify_width(self._width_type, self._width_amount)
    def _set_width(self, width):
        """
        Set the padding width.
        """
        self._width_type, self._width_amount = normalize_width(width,
            PaddingError)
    width = property(_get_width, _set_width)
        
    def render(self, size, focus=False):    
        left, right = self.padding_values(size, focus)
        
        maxcol = size[0]
        maxcol -= left+right

        if self._width_type == CLIP:
            canv = self._original_widget.render((), focus)
        else:
            canv = self._original_widget.render((maxcol,)+size[1:], focus)
        if canv.cols() == 0:
            canv = SolidCanvas(' ', size[0], canv.rows())
            canv = CompositeCanvas(canv)
            canv.set_depends([self._original_widget])
            return canv
        canv = CompositeCanvas(canv)
        canv.set_depends([self._original_widget])
        if left != 0 or right != 0:
            canv.pad_trim_left_right(left, right)

        return canv

    def padding_values(self, size, focus):
        """Return the number of columns to pad on the left and right.
        
        Override this method to define custom padding behaviour."""
        maxcol = size[0]
        if self._width_type == CLIP:
            width, ignore = self._original_widget.pack(focus=focus)
            return calculate_left_right_padding(maxcol,
                self._align_type, self._align_amount, 
                CLIP, width, None, self.left, self.right)
        if self._width_type == PACK:
            maxwidth = max(maxcol - self.left - self.right, 
                self.min_width or 0)
            (width, ignore) = self._original_widget.pack((maxwidth,),
                focus=focus)
            return calculate_left_right_padding(maxcol,
                self._align_type, self._align_amount, 
                GIVEN, width, self.min_width, 
                self.left, self.right) 
        return calculate_left_right_padding(maxcol, 
            self._align_type, self._align_amount,
            self._width_type, self._width_amount,
            self.min_width, self.left, self.right)

    def rows(self, size, focus=False):
        """Return the rows needed for self.original_widget."""
        if self._width_type == PACK:
            pcols, prows = self._original_widget.pack(size, focus)
            return prows
        if self._width_type == CLIP:
            fcols, frows = self._original_widget.pack((), focus)
            return frows
        (maxcol,) = size
        left, right = self.padding_values(size, focus)
        return self._original_widget.rows((maxcol-left-right,), focus=focus)
    
    def keypress(self, size, key):
        """Pass keypress to self._original_widget."""
        maxcol = size[0]
        left, right = self.padding_values(size, True)
        maxvals = (maxcol-left-right,)+size[1:] 
        return self._original_widget.keypress(maxvals, key)

    def get_cursor_coords(self,size):
        """Return the (x,y) coordinates of cursor within self._original_widget."""
        if not hasattr(self._original_widget,'get_cursor_coords'):
            return None
        left, right = self.padding_values(size, True)
        maxcol = size[0]
        maxvals = (maxcol-left-right,)+size[1:] 
        coords = self._original_widget.get_cursor_coords(maxvals)
        if coords is None: 
            return None
        x, y = coords
        return x+left, y

    def move_cursor_to_coords(self, size, x, y):
        """Set the cursor position with (x,y) coordinates of self._original_widget.

        Returns True if move succeeded, False otherwise.
        """
        if not hasattr(self._original_widget,'move_cursor_to_coords'):
            return True
        left, right = self.padding_values(size, True)
        maxcol = size[0]
        maxvals = (maxcol-left-right,)+size[1:] 
        if type(x)==type(0):
            if x < left: 
                x = left
            elif x >= maxcol-right: 
                x = maxcol-right-1
            x -= left
        return self._original_widget.move_cursor_to_coords(maxvals, x, y)
    
    def mouse_event(self, size, event, button, x, y, focus):
        """Send mouse event if position is within self._original_widget."""
        if not hasattr(self._original_widget,'mouse_event'):
            return False
        left, right = self.padding_values(size, focus)
        maxcol = size[0]
        if x < left or x >= maxcol-right: 
            return False
        maxvals = (maxcol-left-right,)+size[1:] 
        return self._original_widget.mouse_event(maxvals, event, button, x-left, y,
            focus)
        

    def get_pref_col(self, size):
        """Return the preferred column from self._original_widget, or None."""
        if not hasattr(self._original_widget,'get_pref_col'):
            return None
        left, right = self.padding_values(size, True)
        maxcol = size[0]
        maxvals = (maxcol-left-right,)+size[1:] 
        x = self._original_widget.get_pref_col(maxvals)
        if type(x) == type(0):
            return x+left
        return x
        

class FillerError(Exception):
    pass

class Filler(WidgetDecoration):

    def __init__(self, body, valign="middle", height=None, min_height=None):
        """
        body -- a flow widget or box widget to be filled around (stored 
            as self.original_widget)
        valign -- one of:
            'top', 'middle', 'bottom'
            ('fixed top', rows)
            ('fixed bottom', rows)
            ('relative', percentage 0=top 100=bottom)
        height -- one of:
            None if body is a flow widget
            number of rows high 
            ('fixed bottom', rows)  Only if valign is 'fixed top'
            ('fixed top', rows)  Only if valign is 'fixed bottom'
            ('relative', percentage of total height)
        min_height -- one of:
            None if no minimum or if body is a flow widget
            minimum number of rows for the widget when height not fixed
        
        If body is a flow widget then height and min_height must be set
        to None.
        
        Filler widgets will try to satisfy height argument first by
        reducing the valign amount when necessary.  If height still 
        cannot be satisfied it will also be reduced.
        """
        self.__super.__init__(body)
        vt,va,ht,ha=decompose_valign_height(valign,height,FillerError)
        
        self.valign_type, self.valign_amount = vt, va
        self.height_type, self.height_amount = ht, ha
        if self.height_type not in ('fixed', None):
            self.min_height = min_height
        else:
            self.min_height = None
    
    def sizing(self):
        return set([BOX]) # always a box widget

    # backwards compatibility, widget used to be stored as body
    get_body = WidgetDecoration._get_original_widget
    set_body = WidgetDecoration._set_original_widget
    body = property(get_body, set_body)
    
    def selectable(self):
        """Return selectable from body."""
        return self._original_widget.selectable()
    
    def filler_values(self, size, focus):
        """Return the number of rows to pad on the top and bottom.
        
        Override this method to define custom padding behaviour."""
        (maxcol, maxrow) = size
        
        if self.height_type is None:
            height = self._original_widget.rows((maxcol,),focus=focus)
            return calculate_filler( self.valign_type,
                self.valign_amount, 'fixed', height, 
                None, maxrow )
            
        return calculate_filler( self.valign_type, self.valign_amount,
            self.height_type, self.height_amount,
            self.min_height, maxrow)

    
    def render(self, size, focus=False):
        """Render self.original_widget with space above and/or below."""
        (maxcol, maxrow) = size
        top, bottom = self.filler_values(size, focus)
        
        if self.height_type is None:
            canv = self._original_widget.render((maxcol,), focus)
        else:
            canv = self._original_widget.render((maxcol,maxrow-top-bottom),focus)
        canv = CompositeCanvas(canv)
        
        if maxrow and canv.rows() > maxrow and canv.cursor is not None:
            cx, cy = canv.cursor
            if cy >= maxrow:
                canv.trim(cy-maxrow+1,maxrow-top-bottom)
        if canv.rows() > maxrow:
            canv.trim(0, maxrow)
            return canv
        canv.pad_trim_top_bottom(top, bottom)
        return canv


    def keypress(self, size, key):
        """Pass keypress to self.original_widget."""
        (maxcol, maxrow) = size
        if self.height_type is None:
            return self._original_widget.keypress((maxcol,), key)

        top, bottom = self.filler_values((maxcol,maxrow), True)
        return self._original_widget.keypress((maxcol,maxrow-top-bottom), key)

    def get_cursor_coords(self, size):
        """Return cursor coords from self.original_widget if any."""
        (maxcol, maxrow) = size
        if not hasattr(self._original_widget, 'get_cursor_coords'):
            return None
            
        top, bottom = self.filler_values(size, True)
        if self.height_type is None:
            coords = self._original_widget.get_cursor_coords((maxcol,))
        else:
            coords = self._original_widget.get_cursor_coords(
                (maxcol,maxrow-top-bottom))
        if not coords:
            return None
        x, y = coords
        if y >= maxrow:
            y = maxrow-1
        return x, y+top

    def get_pref_col(self, size):
        """Return pref_col from self.original_widget if any."""
        (maxcol, maxrow) = size
        if not hasattr(self._original_widget, 'get_pref_col'):
            return None
        
        if self.height_type is None:
            x = self._original_widget.get_pref_col((maxcol,))
        else:
            top, bottom = self.filler_values(size, True)
            x = self._original_widget.get_pref_col(
                (maxcol, maxrow-top-bottom))

        return x
    
    def move_cursor_to_coords(self, size, col, row):
        """Pass to self.original_widget."""
        (maxcol, maxrow) = size
        if not hasattr(self._original_widget, 'move_cursor_to_coords'):
            return True
        
        top, bottom = self.filler_values(size, True)
        if row < top or row >= maxcol-bottom:
            return False

        if self.height_type is None:
            return self._original_widget.move_cursor_to_coords((maxcol,),
                col, row-top)
        return self._original_widget.move_cursor_to_coords(
            (maxcol, maxrow-top-bottom), col, row-top)
    
    def mouse_event(self, size, event, button, col, row, focus):
        """Pass to self.original_widget."""
        (maxcol, maxrow) = size
        if not hasattr(self._original_widget, 'mouse_event'):
            return False
        
        top, bottom = self.filler_values(size, True)
        if row < top or row >= maxcol-bottom:
            return False

        if self.height_type is None:
            return self._original_widget.mouse_event((maxcol,),
                event, button, col, row-top, focus)
        return self._original_widget.mouse_event((maxcol, maxrow-top-bottom), 
            event, button,col, row-top, focus)

        
def normalize_align(align, err):
    """
    Split align into (align_type, align_amount).  Raise exception err
    if align doesn't match a valid alignment.
    """
    if align in (LEFT, CENTER, RIGHT):
        return (align, 0)
    elif type(align) == type(()) and len(align) == 2 and align[0] == RELATIVE:
        return align
    raise err("align value %s is not one of 'left', 'center', "
        "'right', ('relative', percentage 0=left 100=right)" 
        % `align`)

def simplify_align(align_type, align_amount):
    """
    Recombine (align_type, align_amount) into an align value.
    Inverse of normalize_align.
    """
    if align_type == RELATIVE:
        return (align_type, align_amount)
    return align_type

def normalize_width(width, err):
    """
    Split width into (width_type, width_amount).  Raise exception err
    if width doesn't match a valid alignment.
    """
    if width in (CLIP, PACK):
        return (width, 0)
    elif type(width) == type(0):
        return (GIVEN, width)
    elif type(width) == type(()) and len(width) == 2 and width[0] == RELATIVE:
        return width
    raise err("width value %s is not one of fixed number of columns, "
        "'pack', ('relative', percentage of total width), 'clip'" 
        % `width`)

def simplify_width(width_type, width_amount):
    """
    Recombine (width_type, width_amount) into an width value.
    Inverse of normalize_width.
    """
    if width_type in (CLIP, PACK):
        return width_type
    elif width_type == GIVEN:
        return width_amount
    return (width_type, width_amount)
        
def decompose_align_width( align, width, err ):
    # FIXME: remove this once it is no longer called from Overlay
    try:
        if align in ('left','center','right'):
            align = (align,0)
        align_type, align_amount = align
        assert align_type in ('left','center','right','fixed left',
            'fixed right','relative')
    except:
        raise err("align value %s is not one of 'left', 'center', "
            "'right', ('fixed left', columns), ('fixed right', "
            "columns), ('relative', percentage 0=left 100=right)" 
            % `align`)

    try:
        if width is None:
            width = None, None
        elif type(width) == type(0):
            width = 'fixed', width
        width_type, width_amount = width
        assert width_type in ('fixed','fixed right','fixed left',
            'relative', None)
    except:
        raise err("width value %s is not one of ('fixed', columns "
            "width), ('fixed right', columns), ('relative', "
            "percentage of total width), None" % `width`)
        
    if width_type == 'fixed left' and align_type != 'fixed right':
        raise err("fixed left width may only be used with fixed "
            "right align")
    if width_type == 'fixed right' and align_type != 'fixed left':
        raise err("fixed right width may only be used with fixed "
            "left align")

    return align_type, align_amount, width_type, width_amount


def decompose_valign_height( valign, height, err ):
    try:
        if valign in ('top','middle','bottom'):
            valign = (valign,0)
        valign_type, valign_amount = valign
        assert valign_type in ('top','middle','bottom','fixed top','fixed bottom','relative')
    except:
        raise err, "Invalid valign: %s" % `valign`

    try:
        if height is None:
            height = None, None
        elif type(height) == type(0):
            height=('fixed',height)
        height_type, height_amount = height
        assert height_type in (None, 'fixed','fixed bottom','fixed top','relative')
    except:
        raise err, "Invalid height: %s"%`height`
        
    if height_type == 'fixed top' and valign_type != 'fixed bottom':
        raise err, "fixed top height may only be used with fixed bottom valign"
    if height_type == 'fixed bottom' and valign_type != 'fixed top':
        raise err, "fixed bottom height may only be used with fixed top valign"
        
    return valign_type, valign_amount, height_type, height_amount


def calculate_filler( valign_type, valign_amount, height_type, height_amount, 
              min_height, maxrow ):
    if height_type == 'fixed':
        height = height_amount
    elif height_type == 'relative':
        height = int(height_amount*maxrow/100+.5)
        if min_height is not None:
                height = max(height, min_height)
    else:
        assert height_type in ('fixed bottom','fixed top')
        height = maxrow-height_amount-valign_amount
        if min_height is not None:
                height = max(height, min_height)
    
    if height >= maxrow:
        # use the full space (no padding)
        return 0, 0
        
    if valign_type == 'fixed top':
        top = valign_amount
        if top+height <= maxrow:
            return top, maxrow-top-height
        # need to shrink top
        return maxrow-height, 0
    elif valign_type == 'fixed bottom':
        bottom = valign_amount
        if bottom+height <= maxrow:
            return maxrow-bottom-height, bottom
        # need to shrink bottom
        return 0, maxrow-height        
    elif valign_type == 'relative':
        top = int( (maxrow-height)*valign_amount/100+.5 )
    elif valign_type == 'bottom':
        top = maxrow-height    
    elif valign_type == 'middle':
        top = int( (maxrow-height)/2 )
    else: #self.valign_type == 'top'
        top = 0
    
    if top+height > maxrow: top = maxrow-height
    if top < 0: top = 0
    
    bottom = maxrow-height-top
    return top, bottom     


def calculate_left_right_padding(maxcol, align_type, align_amount, 
    width_type, width_amount, min_width, left, right):
    """
    Return the amount of padding (or clipping) on the left and
    right part of maxcol columns to satisfy the following:

    align_type -- 'left', 'center', 'right', 'relative'
    align_amount -- a percentage when align_type=='relative'
    width_type -- 'fixed', 'relative', 'clip'
    width_amount -- a percentage when width_type=='relative'
        otherwise equal to the width of the widget
    min_width -- a desired minimum width for the widget or None
    left -- a fixed number of columns to pad on the left
    right -- a fixed number of columns to pad on the right

    >>> clrp = calculate_left_right_padding
    >>> clrp(15, 'left', 0, 'fixed', 10, None, 2, 0)
    (2, 3)
    >>> clrp(15, 'relative', 0, 'fixed', 10, None, 2, 0)
    (2, 3)
    >>> clrp(15, 'relative', 100, 'fixed', 10, None, 2, 0)
    (5, 0)
    >>> clrp(15, 'center', 0, 'fixed', 4, None, 2, 0)
    (6, 5)
    >>> clrp(15, 'left', 0, 'clip', 18, None, 0, 0)
    (0, -3)
    >>> clrp(15, 'right', 0, 'clip', 18, None, 0, -1)
    (-2, -1)
    >>> clrp(15, 'center', 0, 'fixed', 18, None, 2, 0)
    (0, 0)
    >>> clrp(20, 'left', 0, 'relative', 60, None, 0, 0)
    (0, 8)
    >>> clrp(20, 'relative', 30, 'relative', 60, None, 0, 0)
    (2, 6)
    >>> clrp(20, 'relative', 30, 'relative', 60, 14, 0, 0)
    (2, 4)
    """
    if width_type == RELATIVE:
        maxwidth = max(maxcol - left - right, 0)
        width = int_scale(width_amount, 101, maxwidth + 1)
        if min_width is not None:
            width = max(width, min_width)
    else:
        width = width_amount
    
    standard_alignments = {LEFT:0, CENTER:50, RIGHT:100}
    align = standard_alignments.get(align_type, align_amount)

    # add the remainder of left/right the padding
    padding = maxcol - width - left - right
    right += int_scale(100 - align, 101, padding + 1) 
    left = maxcol - width - right

    # reduce padding if we are clipping an edge
    if right < 0 and left > 0:
        shift = min(left, -right)
        left -= shift
        right += shift
    elif left < 0 and right > 0:
        shift = min(right, -left)
        right -= shift
        left += shift
    
    # only clip if width_type == 'clip'
    if width_type != CLIP and (left < 0 or right < 0):
        left = max(left, 0)
        right = max(right, 0)
    
    return left, right


def calculate_padding( align_type, align_amount, width_type, width_amount,
        min_width, maxcol, clip=False ):
    # FIXME: remove this when Overlay is no longer calling it
    if width_type == 'fixed':
        width = width_amount
    elif width_type == 'relative':
        width = int(width_amount*maxcol/100+.5)
        if min_width is not None:
                width = max(width, min_width)
    else: 
        assert width_type in ('fixed right', 'fixed left')
        width = maxcol-width_amount-align_amount
        if min_width is not None:
                width = max(width, min_width)
    
    if width == maxcol or (width > maxcol and not clip):
        # use the full space (no padding)
        return 0, 0
        
    if align_type == 'fixed left':
        left = align_amount
        if left+width <= maxcol:
            return left, maxcol-left-width
        # need to shrink left
        return maxcol-width, 0
    elif align_type == 'fixed right':
        right = align_amount
        if right+width <= maxcol:
            return maxcol-right-width, right
        # need to shrink right
        return 0, maxcol-width        
    elif align_type == 'relative':
        left = int( (maxcol-width)*align_amount/100+.5 )
    elif align_type == 'right':
        left = maxcol-width    
    elif align_type == 'center':
        left = int( (maxcol-width)/2 )
    else: 
        assert align_type == 'left'
        left = 0
    
    if width < maxcol:
        if left+width > maxcol: left = maxcol-width
        if left < 0: left = 0
    
    right = maxcol-width-left
    return left, right     


def _test():
    import doctest
    doctest.testmod()

if __name__=='__main__':
    _test()

########NEW FILE########
__FILENAME__ = display_common
#!/usr/bin/python
# Urwid common display code
#    Copyright (C) 2004-2007  Ian Ward
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

import sys
import termios

from util import int_scale
import signals

# signals sent by BaseScreen
UPDATE_PALETTE_ENTRY = "update palette entry"


# AttrSpec internal values
_BASIC_START = 0 # first index of basic color aliases
_CUBE_START = 16 # first index of color cube
_CUBE_SIZE_256 = 6 # one side of the color cube
_GRAY_SIZE_256 = 24
_GRAY_START_256 = _CUBE_SIZE_256 ** 3 + _CUBE_START
_CUBE_WHITE_256 = _GRAY_START_256 -1
_CUBE_SIZE_88 = 4
_GRAY_SIZE_88 = 8
_GRAY_START_88 = _CUBE_SIZE_88 ** 3 + _CUBE_START
_CUBE_WHITE_88 = _GRAY_START_88 -1
_CUBE_BLACK = _CUBE_START

# values copied from xterm 256colres.h:
_CUBE_STEPS_256 = [0x00, 0x5f, 0x87, 0xaf, 0xd7, 0xff]
_GRAY_STEPS_256 = [0x08, 0x12, 0x1c, 0x26, 0x30, 0x3a, 0x44, 0x4e, 0x58, 0x62,
    0x6c, 0x76, 0x80, 0x84, 0x94, 0x9e, 0xa8, 0xb2, 0xbc, 0xc6, 0xd0,
    0xda, 0xe4, 0xee]
# values copied from xterm 88colres.h:
_CUBE_STEPS_88 = [0x00, 0x8b, 0xcd, 0xff]
_GRAY_STEPS_88 = [0x2e, 0x5c, 0x73, 0x8b, 0xa2, 0xb9, 0xd0, 0xe7]
# values copied from X11/rgb.txt and XTerm-col.ad:
_BASIC_COLOR_VALUES = [(0,0,0), (205, 0, 0), (0, 205, 0), (205, 205, 0),
    (0, 0, 238), (205, 0, 205), (0, 205, 205), (229, 229, 229),
    (127, 127, 127), (255, 0, 0), (0, 255, 0), (255, 255, 0),
    (0x5c, 0x5c, 0xff), (255, 0, 255), (0, 255, 255), (255, 255, 255)]

_COLOR_VALUES_256 = (_BASIC_COLOR_VALUES +
    [(r, g, b) for r in _CUBE_STEPS_256 for g in _CUBE_STEPS_256 
    for b in _CUBE_STEPS_256] +
    [(gr, gr, gr) for gr in _GRAY_STEPS_256])
_COLOR_VALUES_88 = (_BASIC_COLOR_VALUES +
    [(r, g, b) for r in _CUBE_STEPS_88 for g in _CUBE_STEPS_88 
    for b in _CUBE_STEPS_88] +
    [(gr, gr, gr) for gr in _GRAY_STEPS_88])

assert len(_COLOR_VALUES_256) == 256
assert len(_COLOR_VALUES_88) == 88

_FG_COLOR_MASK = 0x000000ff
_BG_COLOR_MASK = 0x0000ff00
_FG_BASIC_COLOR = 0x00010000
_FG_HIGH_COLOR = 0x00020000
_BG_BASIC_COLOR = 0x00040000
_BG_HIGH_COLOR = 0x00080000
_BG_SHIFT = 8
_HIGH_88_COLOR = 0x00100000
_STANDOUT = 0x02000000
_UNDERLINE = 0x04000000
_BOLD = 0x08000000
_FG_MASK = (_FG_COLOR_MASK | _FG_BASIC_COLOR | _FG_HIGH_COLOR |
    _STANDOUT | _UNDERLINE | _BOLD)
_BG_MASK = _BG_COLOR_MASK | _BG_BASIC_COLOR | _BG_HIGH_COLOR

DEFAULT = 'default'
BLACK = 'black'
DARK_RED = 'dark red'
DARK_GREEN = 'dark green'
BROWN = 'brown'
DARK_BLUE = 'dark blue'
DARK_MAGENTA = 'dark magenta'
DARK_CYAN = 'dark cyan'
LIGHT_GRAY = 'light gray'
DARK_GRAY = 'dark gray'
LIGHT_RED = 'light red'
LIGHT_GREEN = 'light green'
YELLOW = 'yellow'
LIGHT_BLUE = 'light blue'
LIGHT_MAGENTA = 'light magenta'
LIGHT_CYAN = 'light cyan'
WHITE = 'white'

_BASIC_COLORS = [
    BLACK,
    DARK_RED,
    DARK_GREEN,
    BROWN,
    DARK_BLUE,
    DARK_MAGENTA,
    DARK_CYAN,
    LIGHT_GRAY,
    DARK_GRAY,
    LIGHT_RED,
    LIGHT_GREEN,
    YELLOW,
    LIGHT_BLUE,
    LIGHT_MAGENTA,
    LIGHT_CYAN,
    WHITE,
]

_ATTRIBUTES = {
    'bold': _BOLD,
    'underline': _UNDERLINE,
    'standout': _STANDOUT,
}

def _value_lookup_table(values, size):
    """
    Generate a lookup table for finding the closest item in values.
    Lookup returns (index into values)+1
    
    values -- list of values in ascending order, all < size
    size -- size of lookup table and maximum value
    
    >>> _value_lookup_table([0, 7, 9], 10)
    [0, 0, 0, 0, 1, 1, 1, 1, 2, 2]
    """

    middle_values = [0] + [(values[i] + values[i + 1] + 1) / 2 
        for i in range(len(values) - 1)] + [size]
    lookup_table = []
    for i in range(len(middle_values)-1):
        count = middle_values[i + 1] - middle_values[i]
        lookup_table.extend([i] * count)
    return lookup_table

_CUBE_256_LOOKUP = _value_lookup_table(_CUBE_STEPS_256, 256)
_GRAY_256_LOOKUP = _value_lookup_table([0] + _GRAY_STEPS_256 + [0xff], 256)
_CUBE_88_LOOKUP = _value_lookup_table(_CUBE_STEPS_88, 256)
_GRAY_88_LOOKUP = _value_lookup_table([0] + _GRAY_STEPS_88 + [0xff], 256)

# convert steps to values that will be used by string versions of the colors
# 1 hex digit for rgb and 0..100 for grayscale
_CUBE_STEPS_256_16 = [int_scale(n, 0x100, 0x10) for n in _CUBE_STEPS_256]
_GRAY_STEPS_256_101 = [int_scale(n, 0x100, 101) for n in _GRAY_STEPS_256]
_CUBE_STEPS_88_16 = [int_scale(n, 0x100, 0x10) for n in _CUBE_STEPS_88]
_GRAY_STEPS_88_101 = [int_scale(n, 0x100, 101) for n in _GRAY_STEPS_88]

# create lookup tables for 1 hex digit rgb and 0..100 for grayscale values
_CUBE_256_LOOKUP_16 = [_CUBE_256_LOOKUP[int_scale(n, 16, 0x100)]
    for n in range(16)]
_GRAY_256_LOOKUP_101 = [_GRAY_256_LOOKUP[int_scale(n, 101, 0x100)]
    for n in range(101)]
_CUBE_88_LOOKUP_16 = [_CUBE_88_LOOKUP[int_scale(n, 16, 0x100)]
    for n in range(16)]
_GRAY_88_LOOKUP_101 = [_GRAY_88_LOOKUP[int_scale(n, 101, 0x100)]
    for n in range(101)]


# The functions _gray_num_256() and _gray_num_88() do not include the gray 
# values from the color cube so that the gray steps are an even width.  
# The color cube grays are available by using the rgb functions.  Pure 
# white and black are taken from the color cube, since the gray range does 
# not include them, and the basic colors are more likely to have been 
# customized by an end-user.


def _gray_num_256(gnum):
    """Return ths color number for gray number gnum.

    Color cube black and white are returned for 0 and %d respectively
    since those values aren't included in the gray scale.

    """ % (_GRAY_SIZE_256+1)
    # grays start from index 1
    gnum -= 1

    if gnum < 0:
        return _CUBE_BLACK
    if gnum >= _GRAY_SIZE_256:
        return _CUBE_WHITE_256
    return _GRAY_START_256 + gnum


def _gray_num_88(gnum):
    """Return ths color number for gray number gnum.

    Color cube black and white are returned for 0 and %d respectively
    since those values aren't included in the gray scale.

    """ % (_GRAY_SIZE_88+1)
    # gnums start from index 1
    gnum -= 1

    if gnum < 0:
        return _CUBE_BLACK
    if gnum >= _GRAY_SIZE_88:
        return _CUBE_WHITE_88
    return _GRAY_START_88 + gnum


def _color_desc_256(num):
    """
    Return a string description of color number num.
    0..15 -> 'h0'..'h15' basic colors (as high-colors)
    16..231 -> '#000'..'#fff' color cube colors
    232..255 -> 'g3'..'g93' grays

    >>> _color_desc_256(15)
    'h15'
    >>> _color_desc_256(16)
    '#000'
    >>> _color_desc_256(17)
    '#006'
    >>> _color_desc_256(230)
    '#ffd'
    >>> _color_desc_256(233)
    'g7'
    >>> _color_desc_256(234)
    'g11'

    """
    assert num >= 0 and num < 256, num
    if num < _CUBE_START:
        return 'h%d' % num
    if num < _GRAY_START_256:
        num -= _CUBE_START
        b, num = num % _CUBE_SIZE_256, num / _CUBE_SIZE_256
        g, num = num % _CUBE_SIZE_256, num / _CUBE_SIZE_256
        r = num % _CUBE_SIZE_256
        return '#%x%x%x' % (_CUBE_STEPS_256_16[r], _CUBE_STEPS_256_16[g],
            _CUBE_STEPS_256_16[b])
    return 'g%d' % _GRAY_STEPS_256_101[num - _GRAY_START_256]

def _color_desc_88(num):
    """
    Return a string description of color number num.
    0..15 -> 'h0'..'h15' basic colors (as high-colors)
    16..79 -> '#000'..'#fff' color cube colors
    80..87 -> 'g18'..'g90' grays
    
    >>> _color_desc_88(15)
    'h15'
    >>> _color_desc_88(16)
    '#000'
    >>> _color_desc_88(17)
    '#008'
    >>> _color_desc_88(78)
    '#ffc'
    >>> _color_desc_88(81)
    'g36'
    >>> _color_desc_88(82)
    'g45'

    """
    assert num > 0 and num < 88
    if num < _CUBE_START:
        return 'h%d' % num
    if num < _GRAY_START_88:
        num -= _CUBE_START
        b, num = num % _CUBE_SIZE_88, num / _CUBE_SIZE_88
        g, r= num % _CUBE_SIZE_88, num / _CUBE_SIZE_88
        return '#%x%x%x' % (_CUBE_STEPS_88_16[r], _CUBE_STEPS_88_16[g],
            _CUBE_STEPS_88_16[b])
    return 'g%d' % _GRAY_STEPS_88_101[num - _GRAY_START_88]

def _parse_color_256(desc):
    """
    Return a color number for the description desc.
    'h0'..'h255' -> 0..255 actual color number
    '#000'..'#fff' -> 16..231 color cube colors
    'g0'..'g100' -> 16, 232..255, 231 grays and color cube black/white
    'g#00'..'g#ff' -> 16, 232...255, 231 gray and color cube black/white
    
    Returns None if desc is invalid.

    >>> _parse_color_256('h142')
    142
    >>> _parse_color_256('#f00')
    196
    >>> _parse_color_256('g100')
    231
    >>> _parse_color_256('g#80')
    244
    """
    if len(desc) > 4:
        # keep the length within reason before parsing
        return None
    try:
        if desc.startswith('h'):
            # high-color number
            num = int(desc[1:], 10)
            if num < 0 or num > 255:
                return None
            return num

        if desc.startswith('#') and len(desc) == 4:
            # color-cube coordinates
            rgb = int(desc[1:], 16)
            if rgb < 0:
                return None
            b, rgb = rgb % 16, rgb / 16
            g, r = rgb % 16, rgb / 16
            # find the closest rgb values
            r = _CUBE_256_LOOKUP_16[r]
            g = _CUBE_256_LOOKUP_16[g]
            b = _CUBE_256_LOOKUP_16[b]
            return _CUBE_START + (r * _CUBE_SIZE_256 + g) * _CUBE_SIZE_256 + b

        # Only remaining possibility is gray value
        if desc.startswith('g#'):
            # hex value 00..ff
            gray = int(desc[2:], 16)
            if gray < 0 or gray > 255:
                return None
            gray = _GRAY_256_LOOKUP[gray]
        elif desc.startswith('g'):
            # decimal value 0..100
            gray = int(desc[1:], 10)
            if gray < 0 or gray > 100:
                return None
            gray = _GRAY_256_LOOKUP_101[gray]
        else:
            return None
        if gray == 0:
            return _CUBE_BLACK
        gray -= 1
        if gray == _GRAY_SIZE_256:
            return _CUBE_WHITE_256
        return _GRAY_START_256 + gray

    except ValueError:
        return None

def _parse_color_88(desc):
    """
    Return a color number for the description desc.
    'h0'..'h87' -> 0..87 actual color number
    '#000'..'#fff' -> 16..79 color cube colors
    'g0'..'g100' -> 16, 80..87, 79 grays and color cube black/white
    'g#00'..'g#ff' -> 16, 80...87, 79 gray and color cube black/white
    
    Returns None if desc is invalid.
    
    >>> _parse_color_88('h142')
    >>> _parse_color_88('h42')
    42
    >>> _parse_color_88('#f00')
    64
    >>> _parse_color_88('g100')
    79
    >>> _parse_color_88('g#80')
    83
    """
    if len(desc) > 4:
        # keep the length within reason before parsing
        return None
    try:
        if desc.startswith('h'):
            # high-color number
            num = int(desc[1:], 10)
            if num < 0 or num > 87:
                return None
            return num

        if desc.startswith('#') and len(desc) == 4:
            # color-cube coordinates
            rgb = int(desc[1:], 16)
            if rgb < 0:
                return None
            b, rgb = rgb % 16, rgb / 16
            g, r = rgb % 16, rgb / 16
            # find the closest rgb values
            r = _CUBE_88_LOOKUP_16[r]
            g = _CUBE_88_LOOKUP_16[g]
            b = _CUBE_88_LOOKUP_16[b]
            return _CUBE_START + (r * _CUBE_SIZE_88 + g) * _CUBE_SIZE_88 + b

        # Only remaining possibility is gray value
        if desc.startswith('g#'):
            # hex value 00..ff
            gray = int(desc[2:], 16)
            if gray < 0 or gray > 255:
                return None
            gray = _GRAY_88_LOOKUP[gray]
        elif desc.startswith('g'):
            # decimal value 0..100
            gray = int(desc[1:], 10)
            if gray < 0 or gray > 100:
                return None
            gray = _GRAY_88_LOOKUP_101[gray]
        else:
            return None
        if gray == 0:
            return _CUBE_BLACK
        gray -= 1
        if gray == _GRAY_SIZE_88:
            return _CUBE_WHITE_88
        return _GRAY_START_88 + gray

    except ValueError:
        return None

class AttrSpecError(Exception):
    pass

class AttrSpec(object):
    def __init__(self, fg, bg, colors=256):
        """
        fg -- a string containing a comma-separated foreground color
              and settings

              Color values:
              'default' (use the terminal's default foreground),
              'black', 'dark red', 'dark green', 'brown', 'dark blue',
              'dark magenta', 'dark cyan', 'light gray', 'dark gray',
              'light red', 'light green', 'yellow', 'light blue', 
              'light magenta', 'light cyan', 'white'

              High-color example values:
              '#009' (0% red, 0% green, 60% red, like HTML colors)
              '#fcc' (100% red, 80% green, 80% blue)
              'g40' (40% gray, decimal), 'g#cc' (80% gray, hex),
              '#000', 'g0', 'g#00' (black),
              '#fff', 'g100', 'g#ff' (white)
              'h8' (color number 8), 'h255' (color number 255)

              Setting:
              'bold', 'underline', 'blink', 'standout'

              Some terminals use 'bold' for bright colors.  Most terminals
              ignore the 'blink' setting.  If the color is not given then
              'default' will be assumed.

        bg -- a string containing the background color

              Color values:
              'default' (use the terminal's default background),
              'black', 'dark red', 'dark green', 'brown', 'dark blue',
              'dark magenta', 'dark cyan', 'light gray'

              High-color exaples:
              see fg examples above

              An empty string will be treated the same as 'default'.

        colors -- the maximum colors available for the specification

                   Valid values include: 1, 16, 88 and 256.  High-color 
                   values are only usable with 88 or 256 colors.  With
                   1 color only the foreground settings may be used.

        >>> AttrSpec('dark red', 'light gray', 16)
        AttrSpec('dark red', 'light gray')
        >>> AttrSpec('yellow, underline, bold', 'dark blue')
        AttrSpec('yellow,bold,underline', 'dark blue')
        >>> AttrSpec('#ddb', '#004', 256) # closest colors will be found
        AttrSpec('#dda', '#006')
        >>> AttrSpec('#ddb', '#004', 88)
        AttrSpec('#ccc', '#000', colors=88)
        """
        if colors not in (1, 16, 88, 256):
            raise AttrSpecError('invalid number of colors (%d).' % colors)
        self._value = 0 | _HIGH_88_COLOR * (colors == 88)
        self.foreground = fg
        self.background = bg
        if self.colors > colors:
            raise AttrSpecError(('foreground/background (%s/%s) require ' +
                'more colors than have been specified (%d).') %
                (repr(fg), repr(bg), colors))

    foreground_basic = property(lambda s: s._value & _FG_BASIC_COLOR != 0)
    foreground_high = property(lambda s: s._value & _FG_HIGH_COLOR != 0)
    foreground_number = property(lambda s: s._value & _FG_COLOR_MASK)
    background_basic = property(lambda s: s._value & _BG_BASIC_COLOR != 0)
    background_high = property(lambda s: s._value & _BG_HIGH_COLOR != 0)
    background_number = property(lambda s: (s._value & _BG_COLOR_MASK) 
        >> _BG_SHIFT)
    bold = property(lambda s: s._value & _BOLD != 0)
    underline = property(lambda s: s._value & _UNDERLINE != 0)
    standout = property(lambda s: s._value & _STANDOUT != 0)

    def _colors(self):
        """
        Return the maximum colors required for this object.

        Returns 256, 88, 16 or 1.
        """
        if self._value & _HIGH_88_COLOR:
            return 88
        if self._value & (_BG_HIGH_COLOR | _FG_HIGH_COLOR):
            return 256
        if self._value & (_BG_BASIC_COLOR | _BG_BASIC_COLOR):
            return 16
        return 1
    colors = property(_colors)

    def __repr__(self):
        """
        Return an executable python representation of the AttrSpec
        object.
        """
        args = "%r, %r" % (self.foreground, self.background)
        if self.colors == 88:
            # 88-color mode is the only one that is handled differently
            args = args + ", colors=88"
        return "%s(%s)" % (self.__class__.__name__, args)

    def _foreground_color(self):
        """Return only the color component of the foreground."""
        if not (self.foreground_basic or self.foreground_high):
            return 'default'
        if self.foreground_basic:
            return _BASIC_COLORS[self.foreground_number]
        if self.colors == 88:
            return _color_desc_88(self.foreground_number)
        return _color_desc_256(self.foreground_number)

    def _foreground(self):
        return (self._foreground_color() +
            ',bold' * self.bold + ',standout' * self.standout +
            ',underline' * self.underline)

    def _set_foreground(self, foreground):
        color = None
        flags = 0
        # handle comma-separated foreground
        for part in foreground.split(','):
            part = part.strip()
            if part in _ATTRIBUTES:
                # parse and store "settings"/attributes in flags
                if flags & _ATTRIBUTES[part]:
                    raise AttrSpecError(("Setting %s specified more than" +
                        "once in foreground (%s)") % (repr(part), 
                        repr(foreground)))
                flags |= _ATTRIBUTES[part]
                continue
            # past this point we must be specifying a color
            if part in ('', 'default'):
                scolor = 0
            elif part in _BASIC_COLORS:
                scolor = _BASIC_COLORS.index(part)
                flags |= _FG_BASIC_COLOR
            elif self._value & _HIGH_88_COLOR:
                scolor = _parse_color_88(part)
                flags |= _FG_HIGH_COLOR
            else:
                scolor = _parse_color_256(part)
                flags |= _FG_HIGH_COLOR
            # _parse_color_*() return None for unrecognised colors
            if scolor is None:
                raise AttrSpecError(("Unrecognised color specification %s" +
                    "in foreground (%s)") % (repr(part), repr(foreground)))
            if color is not None:
                raise AttrSpecError(("More than one color given for " +
                    "foreground (%s)") % (repr(foreground),))
            color = scolor
        if color is None:
            color = 0
        self._value = (self._value & ~_FG_MASK) | color | flags

    foreground = property(_foreground, _set_foreground)

    def _background(self):
        """Return the background color."""
        if not (self.background_basic or self.background_high):
            return 'default'
        if self.background_basic:
            return _BASIC_COLORS[self.background_number]
        if self._value & _HIGH_88_COLOR:
            return _color_desc_88(self.background_number)
        return _color_desc_256(self.background_number)
        
    def _set_background(self, background):
        flags = 0
        if background in ('', 'default'):
            color = 0
        elif background in _BASIC_COLORS:
            color = _BASIC_COLORS.index(background)
            flags |= _BG_BASIC_COLOR
        elif self._value & _HIGH_88_COLOR:
            color = _parse_color_88(background)
            flags |= _BG_HIGH_COLOR
        else:
            color = _parse_color_256(background)
            flags |= _BG_HIGH_COLOR
        if color is None:
            raise AttrSpecError(("Unrecognised color specification " +
                "in background (%s)") % (repr(background),))
        self._value = (self._value & ~_BG_MASK) | (color << _BG_SHIFT) | flags

    background = property(_background, _set_background)

    def get_rgb_values(self):
        """
        Return (fg_red, fg_green, fg_blue, bg_red, bg_green, bg_blue) color
        components.  Each component is in the range 0-255.  Values are taken
        from the XTerm defaults and may not exactly match the user's terminal.
        
        If the foreground or background is 'default' then all their compenents
        will be returned as None.

        >>> AttrSpec('yellow', '#ccf', colors=88).get_rgb_values()
        (255, 255, 0, 205, 205, 255)
        >>> AttrSpec('default', 'g92').get_rgb_values()
        (None, None, None, 238, 238, 238)
        """
        if not (self.foreground_basic or self.foreground_high):
            vals = (None, None, None)
        elif self.colors == 88:
            assert self.foreground_number < 88, "Invalid AttrSpec _value"
            vals = _COLOR_VALUES_88[self.foreground_number]
        else:
            vals = _COLOR_VALUES_256[self.foreground_number]

        if not (self.background_basic or self.background_high):
            return vals + (None, None, None)
        elif self.colors == 88:
            assert self.background_number < 88, "Invalid AttrSpec _value"
            return vals + _COLOR_VALUES_88[self.background_number]
        else:
            return vals + _COLOR_VALUES_256[self.background_number]



class RealTerminal(object):
    def __init__(self):
        super(RealTerminal,self).__init__()
        self._signal_keys_set = False
        self._old_signal_keys = None
        
    def tty_signal_keys(self, intr=None, quit=None, start=None, 
        stop=None, susp=None):
        """
        Read and/or set the tty's signal charater settings.
        This function returns the current settings as a tuple.

        Use the string 'undefined' to unmap keys from their signals.
        The value None is used when no change is being made.
        Setting signal keys is done using the integer ascii
        code for the key, eg.  3 for CTRL+C.

        If this function is called after start() has been called
        then the original settings will be restored when stop()
        is called.
        """
        fd = sys.stdin.fileno()
        tattr = termios.tcgetattr(fd)
        sattr = tattr[6]
        skeys = (sattr[termios.VINTR], sattr[termios.VQUIT],
            sattr[termios.VSTART], sattr[termios.VSTOP],
            sattr[termios.VSUSP])
        
        if intr == 'undefined': intr = 0
        if quit == 'undefined': quit = 0
        if start == 'undefined': start = 0
        if stop == 'undefined': stop = 0
        if susp == 'undefined': susp = 0
        
        if intr is not None: tattr[6][termios.VINTR] = intr
        if quit is not None: tattr[6][termios.VQUIT] = quit
        if start is not None: tattr[6][termios.VSTART] = start
        if stop is not None: tattr[6][termios.VSTOP] = stop
        if susp is not None: tattr[6][termios.VSUSP] = susp
        
        if intr is not None or quit is not None or \
            start is not None or stop is not None or \
            susp is not None:
            termios.tcsetattr(fd, termios.TCSADRAIN, tattr)
            self._signal_keys_set = True
        
        return skeys


class ScreenError(Exception):
    pass

class BaseScreen(object):
    """
    Base class for Screen classes (raw_display.Screen, .. etc)
    """
    __metaclass__ = signals.MetaSignals
    signals = [UPDATE_PALETTE_ENTRY]

    def __init__(self):
        super(BaseScreen,self).__init__()
        self._palette = {}

    def register_palette(self, palette):
        """Register a set of palette entries.

        palette -- a list of (name, like_other_name) or 
            (name, foreground, background, mono, foreground_high, 
            background_high) tuples

            The (name, like_other_name) format will copy the settings
            from the palette entry like_other_name, which must appear
            before this tuple in the list.
            
            The mono and foreground/background_high values are 
            optional ie. the second tuple format may have 3, 4 or 6 
            values.  See register_palette_entry() for a description 
            of the tuple values.
        """
        
        for item in palette:
            if len(item) in (3,4,6):
                self.register_palette_entry(*item)
                continue
            if len(item) != 2:
                raise ScreenError("Invalid register_palette entry: %s" % 
                    repr(item))
            name, like_name = item
            if not self._palette.has_key(like_name):
                raise ScreenError("palette entry '%s' doesn't exist"%like_name)
            self._palette[name] = self._palette[like_name]

    def register_palette_entry(self, name, foreground, background,
        mono=None, foreground_high=None, background_high=None):
        """Register a single palette entry.

        name -- new entry/attribute name
        foreground -- a string containing a comma-separated foreground 
            color and settings

            Color values:
            'default' (use the terminal's default foreground),
            'black', 'dark red', 'dark green', 'brown', 'dark blue',
            'dark magenta', 'dark cyan', 'light gray', 'dark gray',
            'light red', 'light green', 'yellow', 'light blue', 
            'light magenta', 'light cyan', 'white'

            Settings:
            'bold', 'underline', 'blink', 'standout'

            Some terminals use 'bold' for bright colors.  Most terminals
            ignore the 'blink' setting.  If the color is not given then
            'default' will be assumed. 

        background -- a string containing the background color

            Background color values:
            'default' (use the terminal's default background),
            'black', 'dark red', 'dark green', 'brown', 'dark blue',
            'dark magenta', 'dark cyan', 'light gray'
        
        mono -- a comma-separated string containing monochrome terminal 
            settings (see "Settings" above.)

            None = no terminal settings (same as 'default')

        foreground_high -- a string containing a comma-separated 
            foreground color and settings, standard foreground
            colors (see "Color values" above) or high-colors may 
            be used

            High-color example values:
            '#009' (0% red, 0% green, 60% red, like HTML colors)
            '#fcc' (100% red, 80% green, 80% blue)
            'g40' (40% gray, decimal), 'g#cc' (80% gray, hex),
            '#000', 'g0', 'g#00' (black),
            '#fff', 'g100', 'g#ff' (white)
            'h8' (color number 8), 'h255' (color number 255)

            None = use foreground parameter value

        background_high -- a string containing the background color,
            standard background colors (see "Background colors" above)
            or high-colors (see "High-color example values" above)
            may be used

            None = use background parameter value
        """
        basic = AttrSpec(foreground, background, 16)

        if type(mono) == type(()):
            # old style of specifying mono attributes was to put them
            # in a tuple.  convert to comma-separated string
            mono = ",".join(mono)
        if mono is None:
            mono = DEFAULT
        mono = AttrSpec(mono, DEFAULT, 1)
        
        if foreground_high is None:
            foreground_high = foreground
        if background_high is None:
            background_high = background
        high_88 = AttrSpec(foreground_high, background_high, 88)
        high_256 = AttrSpec(foreground_high, background_high, 256)

        signals.emit_signal(self, UPDATE_PALETTE_ENTRY,
            name, basic, mono, high_88, high_256)
        self._palette[name] = (basic, mono, high_88, high_256)
        


def _test():
    import doctest
    doctest.testmod()

if __name__=='__main__':
    _test()

########NEW FILE########
__FILENAME__ = escape
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Urwid escape sequences common to curses_display and raw_display
#    Copyright (C) 2004-2006  Ian Ward
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
Terminal Escape Sequences for input and display
"""

import util
import os
import re

import encodings
utf8decode = lambda s: encodings.codecs.utf_8_decode(s)[0]

SO = "\x0e"
SI = "\x0f"

DEC_TAG = "0"
DEC_SPECIAL_CHARS = utf8decode("◆▒°±┘┐┌└┼⎺⎻─⎼⎽├┤┴┬│≤≥π≠£·")
ALT_DEC_SPECIAL_CHARS = u"`afgjklmnopqrstuvwxyz{|}~"

DEC_SPECIAL_CHARMAP = {}
assert len(DEC_SPECIAL_CHARS) == len(ALT_DEC_SPECIAL_CHARS), `DEC_SPECIAL_CHARS, ALT_DEC_SPECIAL_CHARS`
for c, alt in zip(DEC_SPECIAL_CHARS, ALT_DEC_SPECIAL_CHARS):
    DEC_SPECIAL_CHARMAP[ord(c)] = SO + alt + SI

SAFE_ASCII_DEC_SPECIAL_RE = re.compile(u"^[ -~%s]*$" % DEC_SPECIAL_CHARS)
DEC_SPECIAL_RE = re.compile(u"[%s]" % DEC_SPECIAL_CHARS)


###################
## Input sequences
###################

class MoreInputRequired(Exception):
    pass

def escape_modifier( digit ):
    mode = ord(digit) - ord("1")
    return "shift "*(mode&1) + "meta "*((mode&2)/2) + "ctrl "*((mode&4)/4)
    

input_sequences = [
    ('[A','up'),('[B','down'),('[C','right'),('[D','left'),
    ('[E','5'),('[F','end'),('[G','5'),('[H','home'),

    ('[1~','home'),('[2~','insert'),('[3~','delete'),('[4~','end'),
    ('[5~','page up'),('[6~','page down'),
    ('[7~','home'),('[8~','end'),

    ('[[A','f1'),('[[B','f2'),('[[C','f3'),('[[D','f4'),('[[E','f5'),
    
    ('[11~','f1'),('[12~','f2'),('[13~','f3'),('[14~','f4'),
    ('[15~','f5'),('[17~','f6'),('[18~','f7'),('[19~','f8'),
    ('[20~','f9'),('[21~','f10'),('[23~','f11'),('[24~','f12'),
    ('[25~','f13'),('[26~','f14'),('[28~','f15'),('[29~','f16'),
    ('[31~','f17'),('[32~','f18'),('[33~','f19'),('[34~','f20'),

    ('OA','up'),('OB','down'),('OC','right'),('OD','left'),
    ('OH','home'),('OF','end'),
    ('OP','f1'),('OQ','f2'),('OR','f3'),('OS','f4'),
    ('Oo','/'),('Oj','*'),('Om','-'),('Ok','+'),

    ('[Z','shift tab'),
] + [ 
    # modified cursor keys + home, end, 5 -- [#X and [1;#X forms
    (prefix+digit+letter, escape_modifier(digit) + key)
    for prefix in "[","[1;"
    for digit in "12345678"
    for letter,key in zip("ABCDEFGH",
        ('up','down','right','left','5','end','5','home'))
] + [ 
    # modified F1-F4 keys -- O#X form
    ("O"+digit+letter, escape_modifier(digit) + key)
    for digit in "12345678"
    for letter,key in zip("PQRS",('f1','f2','f3','f4'))
] + [ 
    # modified F1-F13 keys -- [XX;#~ form
    ("["+str(num)+";"+digit+"~", escape_modifier(digit) + key)
    for digit in "12345678"
    for num,key in zip(
        (11,12,13,14,15,17,18,19,20,21,23,24,25,26,28,29,31,32,33,34),
        ('f1','f2','f3','f4','f5','f6','f7','f8','f9','f10','f11',
        'f12','f13','f14','f15','f16','f17','f18','f19','f20'))
] + [
    # mouse reporting (special handling done in KeyqueueTrie)
    ('[M', 'mouse'),
    # report status response
    ('[0n', 'status ok')
]

class KeyqueueTrie(object):
    def __init__( self, sequences ):
        self.data = {}
        for s, result in sequences:
            assert type(result) != type({})
            self.add(self.data, s, result)
    
    def add(self, root, s, result):
        assert type(root) == type({}), "trie conflict detected"
        assert len(s) > 0, "trie conflict detected"
        
        if root.has_key(ord(s[0])):
            return self.add(root[ord(s[0])], s[1:], result)
        if len(s)>1:
            d = {}
            root[ord(s[0])] = d
            return self.add(d, s[1:], result)
        root[ord(s)] = result
    
    def get(self, keys, more_available):
        result = self.get_recurse(self.data, keys, more_available)
        if not result:
            result = self.read_cursor_position(keys, more_available)
        return result
    
    def get_recurse(self, root, keys, more_available):
        if type(root) != type({}):
            if root == "mouse":
                return self.read_mouse_info(keys, 
                    more_available)
            return (root, keys)
        if not keys:
            # get more keys
            if more_available:
                raise MoreInputRequired()
            return None
        if not root.has_key(keys[0]):
            return None
        return self.get_recurse(root[keys[0]], keys[1:], more_available)
    
    def read_mouse_info(self, keys, more_available):
        if len(keys) < 3:
            if more_available:
                raise MoreInputRequired()
            return None
        
        b = keys[0] - 32
        x, y = keys[1] - 33, keys[2] - 33  # start from 0
        
        prefix = ""
        if b & 4:    prefix = prefix + "shift "
        if b & 8:    prefix = prefix + "meta "
        if b & 16:    prefix = prefix + "ctrl "

        # 0->1, 1->2, 2->3, 64->4, 65->5
        button = ((b&64)/64*3) + (b & 3) + 1

        if b & 3 == 3:    
            action = "release"
            button = 0
        elif b & MOUSE_RELEASE_FLAG:
            action = "release"
        elif b & MOUSE_DRAG_FLAG:
            action = "drag"
        else:
            action = "press"

        return ( (prefix + "mouse " + action, button, x, y), keys[3:] )
    
    def read_cursor_position(self, keys, more_available):
        """
        Interpret cursor position information being sent by the
        user's terminal.  Returned as ('cursor position', x, y)
        where (x, y) == (0, 0) is the top left of the screen.
        """
        if not keys:
            if more_available:
                raise MoreInputRequired()
            return None
        if keys[0] != ord('['):
            return None
        # read y value
        y = 0
        i = 1
        for k in keys[i:]:
            i += 1
            if k == ord(';'):
                if not y:
                    return None
                break
            if k < ord('0') or k > ord('9'):
                return None
            if not y and k == ord('0'):
                return None
            y = y * 10 + k - ord('0')
        if not keys[i:]:
            if more_available:
                raise MoreInputRequired()
            return None
        # read x value
        x = 0
        for k in keys[i:]:
            i += 1
            if k == ord('R'):
                if not x:
                    return None
                return (("cursor position", x-1, y-1), keys[i:])
            if k < ord('0') or k > ord('9'):
                return None
            if not x and k == ord('0'):
                return None
            x = x * 10 + k - ord('0')
        if not keys[i:]:
            if more_available:
                raise MoreInputRequired()
        return None




# This is added to button value to signal mouse release by curses_display
# and raw_display when we know which button was released.  NON-STANDARD 
MOUSE_RELEASE_FLAG = 2048  

# xterm adds this to the button value to signal a mouse drag event
MOUSE_DRAG_FLAG = 32


#################################################
# Build the input trie from input_sequences list
input_trie = KeyqueueTrie(input_sequences)
#################################################

_keyconv = {
    -1:None,
    8:'backspace',
    9:'tab',
    10:'enter',
    13:'enter',
    127:'backspace',
    # curses-only keycodes follow..  (XXX: are these used anymore?)
    258:'down',
    259:'up',
    260:'left',
    261:'right',
    262:'home',
    263:'backspace',
    265:'f1', 266:'f2', 267:'f3', 268:'f4',
    269:'f5', 270:'f6', 271:'f7', 272:'f8',
    273:'f9', 274:'f10', 275:'f11', 276:'f12',
    277:'shift f1', 278:'shift f2', 279:'shift f3', 280:'shift f4',
    281:'shift f5', 282:'shift f6', 283:'shift f7', 284:'shift f8',
    285:'shift f9', 286:'shift f10', 287:'shift f11', 288:'shift f12',
    330:'delete',
    331:'insert',
    338:'page down',
    339:'page up',
    343:'enter',    # on numpad
    350:'5',        # on numpad
    360:'end',
}



def process_keyqueue(codes, more_available):
    """
    codes -- list of key codes
    more_available -- if True then raise MoreInputRequired when in the 
        middle of a character sequence (escape/utf8/wide) and caller 
        will attempt to send more key codes on the next call.
    
    returns (list of input, list of remaining key codes).
    """
    code = codes[0]
    if code >= 32 and code <= 126:
        key = chr(code)
        return [key], codes[1:]
    if _keyconv.has_key(code):
        return [_keyconv[code]], codes[1:]
    if code >0 and code <27:
        return ["ctrl %s" % chr(ord('a')+code-1)], codes[1:]
    if code >27 and code <32:
        return ["ctrl %s" % chr(ord('A')+code-1)], codes[1:]
    
    em = util.get_encoding_mode()
    
    if (em == 'wide' and code < 256 and  
        util.within_double_byte(chr(code),0,0)):
        if not codes[1:]:
            if more_available:
                raise MoreInputRequired()
        if codes[1:] and codes[1] < 256:
            db = chr(code)+chr(codes[1])
            if util.within_double_byte(db, 0, 1):
                return [db], codes[2:]
    if em == 'utf8' and code>127 and code<256:
        if code & 0xe0 == 0xc0: # 2-byte form
            need_more = 1
        elif code & 0xf0 == 0xe0: # 3-byte form
            need_more = 2
        elif code & 0xf8 == 0xf0: # 4-byte form
            need_more = 3
        else:
            return ["<%d>"%code], codes[1:]

        for i in range(need_more):
            if len(codes)-1 <= i:
                if more_available:
                    raise MoreInputRequired()
                else:
                    return ["<%d>"%code], codes[1:]
            k = codes[i+1]
            if k>256 or k&0xc0 != 0x80:
                return ["<%d>"%code], codes[1:]
        
        s = "".join([chr(c)for c in codes[:need_more+1]])
        try:
            return [s.decode("utf-8")], codes[need_more+1:]
        except UnicodeDecodeError:
            return ["<%d>"%code], codes[1:]
        
    if code >127 and code <256:
        key = chr(code)
        return [key], codes[1:]
    if code != 27:
        return ["<%d>"%code], codes[1:]

    result = input_trie.get(codes[1:], more_available)
    
    if result is not None:
        result, remaining_codes = result
        return [result], remaining_codes
    
    if codes[1:]:
        # Meta keys -- ESC+Key form
        run, remaining_codes = process_keyqueue(codes[1:], 
            more_available)
        if run[0] == "esc" or run[0].find("meta ") >= 0:
            return ['esc']+run, remaining_codes
        return ['meta '+run[0]]+run[1:], remaining_codes
        
    return ['esc'], codes[1:]


####################
## Output sequences
####################

ESC = "\x1b"

CURSOR_HOME = ESC+"[H"
CURSOR_HOME_COL = "\r"

APP_KEYPAD_MODE = ESC+"="
NUM_KEYPAD_MODE = ESC+">"

SWITCH_TO_ALTERNATE_BUFFER = ESC+"7"+ESC+"[?47h"
RESTORE_NORMAL_BUFFER = ESC+"[?47l"+ESC+"8"

#RESET_SCROLL_REGION = ESC+"[;r"
#RESET = ESC+"c"

REPORT_STATUS = ESC + "[5n"
REPORT_CURSOR_POSITION = ESC+"[6n"

INSERT_ON = ESC + "[4h"
INSERT_OFF = ESC + "[4l"

def set_cursor_position( x, y ):
    assert type(x) == type(0)
    assert type(y) == type(0)
    return ESC+"[%d;%dH" %(y+1, x+1)

def move_cursor_right(x):
    if x < 1: return ""
    return ESC+"[%dC" % x

def move_cursor_up(x):
    if x < 1: return ""
    return ESC+"[%dA" % x

def move_cursor_down(x):
    if x < 1: return ""
    return ESC+"[%dB" % x

HIDE_CURSOR = ESC+"[?25l"
SHOW_CURSOR = ESC+"[?25h"

MOUSE_TRACKING_ON = ESC+"[?1000h"+ESC+"[?1002h"
MOUSE_TRACKING_OFF = ESC+"[?1002l"+ESC+"[?1000l"

DESIGNATE_G1_SPECIAL = ESC+")0"



########NEW FILE########
__FILENAME__ = font
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Urwid BigText fonts
#    Copyright (C) 2004-2006  Ian Ward
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

from __future__ import nested_scopes

import re

from escape import utf8decode, SAFE_ASCII_DEC_SPECIAL_RE
from util import apply_target_encoding, str_util
from canvas import TextCanvas

try: True # old python?
except: False, True = 0, 1

def separate_glyphs(gdata, height):
    """return (dictionary of glyphs, utf8 required)"""
    gl = gdata.split("\n")
    del gl[0]
    del gl[-1]
    for g in gl:
        assert "\t" not in g
    assert len(gl) == height+1, `gdata`
    key_line = gl[0]
    del gl[0]
    c = None # current character
    key_index = 0 # index into character key line
    end_col = 0 # column position at end of glyph
    start_col = 0 # column position at start of glyph
    jl = [0]*height # indexes into lines of gdata (gl)
    dout = {}
    utf8_required = False
    while True:
        if c is None:
            if key_index >= len(key_line):
                break
            c = key_line[key_index]
        if key_index < len(key_line) and key_line[key_index] == c:
            end_col += str_util.get_width(ord(c))
            key_index += 1
            continue
        out = []
        for k in range(height):
            l = gl[k]
            j = jl[k]
            y = 0
            fill = 0
            while y < end_col - start_col:
                if j >= len(l):
                    fill = end_col - start_col - y
                    break
                y += str_util.get_width(ord(l[j]))
                j += 1
            assert y + fill == end_col - start_col, \
                `y, fill, end_col`
            
            segment = l[jl[k]:j]
            if not SAFE_ASCII_DEC_SPECIAL_RE.match(segment):
                utf8_required = True
            
            out.append(segment + " " * fill)
            jl[k] = j

        start_col = end_col
        dout[c] = (y + fill, out)
        c = None
    return dout, utf8_required

_all_fonts = []
def get_all_fonts():
    """
    Return a list of (font name, font class) tuples.
    """
    return _all_fonts[:]

def add_font(name, cls):
    _all_fonts.append((name, cls))


class Font(object):
    def __init__(self):
        assert self.height
        assert self.data
        self.char = {}
        self.canvas = {}
        self.utf8_required = False
        for gdata in self.data:
            self.add_glyphs(gdata)
        

    def add_glyphs(self, gdata):
        d, utf8_required = separate_glyphs(gdata, self.height)
        self.char.update(d)
        self.utf8_required |= utf8_required

    def characters(self):
        l = self.char.keys()
        l.sort()
        return "".join(l)

    def char_width(self, c):
        if self.char.has_key(c):
            return self.char[c][0]
        return 0
    
    def char_data(self, c):
        return self.char[c][1]

    def render(self, c):
        if c in self.canvas:
            return self.canvas[c]
        width, l = self.char[c]
        tl = []
        csl = []
        for d in l:
            t, cs = apply_target_encoding(d)
            tl.append(t)
            csl.append(cs)
        canv = TextCanvas(tl, None, csl, maxcol=width, 
            check_width=False)
        self.canvas[c] = canv
        return canv
    

        
#safe_palette = utf8decode("┘┐┌└┼─├┤┴┬│")
#more_palette = utf8decode("═║╒╓╔╕╖╗╘╙╚╛╜╝╞╟╠╡╢╣╤╥╦╧╨╩╪╫╬○")
#block_palette = utf8decode("▄#█#▀#▌#▐#▖#▗#▘#▙#▚#▛#▜#▝#▞#▟")


class Thin3x3Font(Font):
    height = 3
    data = [utf8decode("""
000111222333444555666777888999  !
┌─┐ ┐ ┌─┐┌─┐  ┐┌─ ┌─ ┌─┐┌─┐┌─┐  │
│ │ │ ┌─┘ ─┤└─┼└─┐├─┐  ┼├─┤└─┤  │
└─┘ ┴ └─ └─┘  ┴ ─┘└─┘  ┴└─┘ ─┘  .
"""), utf8decode(r"""
"###$$$%%%'*++,--.///:;==???[[\\\]]^__`
" ┼┼┌┼┐O /'         /.. _┌─┐┌ \   ┐^  `
  ┼┼└┼┐ /  * ┼  ─  / ., _ ┌┘│  \  │     
    └┼┘/ O    ,  ./       . └   \ ┘ ──
""")]
add_font("Thin 3x3",Thin3x3Font)

class Thin4x3Font(Font):
    height = 3
    data = Thin3x3Font.data + [utf8decode("""
0000111122223333444455556666777788889999  ####$$$$
┌──┐  ┐ ┌──┐┌──┐   ┐┌── ┌── ┌──┐┌──┐┌──┐   ┼─┼┌┼┼┐
│  │  │ ┌──┘  ─┤└──┼└──┐├──┐   ┼├──┤└──┤   ┼─┼└┼┼┐
└──┘  ┴ └── └──┘   ┴ ──┘└──┘   ┴└──┘ ──┘      └┼┼┘
""")]
add_font("Thin 4x3",Thin4x3Font)

class HalfBlock5x4Font(Font):
    height = 4
    data = [utf8decode("""
00000111112222233333444445555566666777778888899999  !!
▄▀▀▄  ▄█  ▄▀▀▄ ▄▀▀▄ ▄  █ █▀▀▀ ▄▀▀  ▀▀▀█ ▄▀▀▄ ▄▀▀▄   █ 
█  █   █    ▄▀   ▄▀ █▄▄█ █▄▄  █▄▄    ▐▌ ▀▄▄▀ ▀▄▄█   █ 
█  █   █  ▄▀   ▄  █    █    █ █  █   █  █  █    █   ▀ 
 ▀▀   ▀▀▀ ▀▀▀▀  ▀▀     ▀ ▀▀▀   ▀▀    ▀   ▀▀   ▀▀    ▀ 
"""), utf8decode('''
"""######$$$$$$%%%%%&&&&&((()))******++++++,,,-----..////:::;;
█▐▌ █ █  ▄▀█▀▄ ▐▌▐▌ ▄▀▄   █ █   ▄ ▄    ▄              ▐▌      
   ▀█▀█▀ ▀▄█▄    █  ▀▄▀  ▐▌ ▐▌ ▄▄█▄▄ ▄▄█▄▄    ▄▄▄▄    █  ▀  ▀ 
   ▀█▀█▀ ▄ █ █  ▐▌▄ █ ▀▄▌▐▌ ▐▌  ▄▀▄    █             ▐▌  ▀ ▄▀ 
    ▀ ▀   ▀▀▀   ▀ ▀  ▀▀   ▀ ▀              ▄▀      ▀ ▀        
'''), utf8decode(r"""
<<<<<=====>>>>>?????@@@@@@[[[[\\\\]]]]^^^^____```{{{{||}}}}~~~~''´´´
  ▄▀      ▀▄   ▄▀▀▄ ▄▀▀▀▄ █▀▀ ▐▌  ▀▀█ ▄▀▄     ▀▄  ▄▀ █ ▀▄   ▄  █ ▄▀ 
▄▀   ▀▀▀▀   ▀▄   ▄▀ █ █▀█ █    █    █            ▄▀  █  ▀▄ ▐▐▌▌     
 ▀▄  ▀▀▀▀  ▄▀    ▀  █ ▀▀▀ █    ▐▌   █             █  █  █    ▀      
   ▀      ▀      ▀   ▀▀▀  ▀▀▀   ▀ ▀▀▀     ▀▀▀▀     ▀ ▀ ▀            
"""), utf8decode('''
AAAAABBBBBCCCCCDDDDDEEEEEFFFFFGGGGGHHHHHIIJJJJJKKKKK
▄▀▀▄ █▀▀▄ ▄▀▀▄ █▀▀▄ █▀▀▀ █▀▀▀ ▄▀▀▄ █  █ █    █ █  █  
█▄▄█ █▄▄▀ █    █  █ █▄▄  █▄▄  █    █▄▄█ █    █ █▄▀    
█  █ █  █ █  ▄ █  █ █    █    █ ▀█ █  █ █ ▄  █ █ ▀▄  
▀  ▀ ▀▀▀   ▀▀  ▀▀▀  ▀▀▀▀ ▀     ▀▀  ▀  ▀ ▀  ▀▀  ▀  ▀  
'''), utf8decode('''
LLLLLMMMMMMNNNNNOOOOOPPPPPQQQQQRRRRRSSSSSTTTTT
█    █▄ ▄█ ██ █ ▄▀▀▄ █▀▀▄ ▄▀▀▄ █▀▀▄ ▄▀▀▄ ▀▀█▀▀
█    █ ▀ █ █▐▌█ █  █ █▄▄▀ █  █ █▄▄▀ ▀▄▄    █  
█    █   █ █ ██ █  █ █    █ ▌█ █  █ ▄  █   █
▀▀▀▀ ▀   ▀ ▀  ▀  ▀▀  ▀     ▀▀▌ ▀  ▀  ▀▀    ▀
'''), utf8decode('''
UUUUUVVVVVVWWWWWWXXXXXXYYYYYYZZZZZ
█  █ █   █ █   █ █   █ █   █ ▀▀▀█      
█  █ ▐▌ ▐▌ █ ▄ █  ▀▄▀   ▀▄▀   ▄▀  
█  █  █ █  ▐▌█▐▌ ▄▀ ▀▄   █   █    
 ▀▀    ▀    ▀ ▀  ▀   ▀   ▀   ▀▀▀▀     
'''), utf8decode('''
aaaaabbbbbcccccdddddeeeeeffffggggghhhhhiijjjjkkkkk
     █            █       ▄▀▀     █    ▄   ▄ █
 ▀▀▄ █▀▀▄ ▄▀▀▄ ▄▀▀█ ▄▀▀▄ ▀█▀ ▄▀▀▄ █▀▀▄ ▄   ▄ █ ▄▀    
▄▀▀█ █  █ █  ▄ █  █ █▀▀   █  ▀▄▄█ █  █ █   █ █▀▄   
 ▀▀▀ ▀▀▀   ▀▀   ▀▀▀  ▀▀   ▀   ▄▄▀ ▀  ▀ ▀ ▄▄▀ ▀  ▀  
'''), utf8decode('''
llmmmmmmnnnnnooooopppppqqqqqrrrrssssstttt
█                                     █  
█ █▀▄▀▄ █▀▀▄ ▄▀▀▄ █▀▀▄ ▄▀▀█ █▀▀ ▄▀▀▀ ▀█▀  
█ █ █ █ █  █ █  █ █  █ █  █ █    ▀▀▄  █
▀ ▀   ▀ ▀  ▀  ▀▀  █▀▀   ▀▀█ ▀   ▀▀▀    ▀
'''), utf8decode('''
uuuuuvvvvvwwwwwwxxxxxxyyyyyzzzzz
                           
█  █ █  █ █ ▄ █ ▀▄ ▄▀ █  █ ▀▀█▀
█  █ ▐▌▐▌ ▐▌█▐▌  ▄▀▄  ▀▄▄█ ▄▀   
 ▀▀   ▀▀   ▀ ▀  ▀   ▀  ▄▄▀ ▀▀▀▀
''')]
add_font("Half Block 5x4",HalfBlock5x4Font)

class HalfBlock6x5Font(Font):
    height = 5
    data = [utf8decode("""
000000111111222222333333444444555555666666777777888888999999  ..::////
▄▀▀▀▄  ▄█   ▄▀▀▀▄ ▄▀▀▀▄ ▄  █  █▀▀▀▀ ▄▀▀▀  ▀▀▀▀█ ▄▀▀▀▄ ▄▀▀▀▄         █
█   █   █       █     █ █  █  █     █        ▐▌ █   █ █   █     ▀  ▐▌
█   █   █     ▄▀    ▀▀▄ ▀▀▀█▀ ▀▀▀▀▄ █▀▀▀▄    █  ▄▀▀▀▄  ▀▀▀█     ▄  █
█   █   █   ▄▀    ▄   █    █      █ █   █   ▐▌  █   █     █       ▐▌
 ▀▀▀   ▀▀▀  ▀▀▀▀▀  ▀▀▀     ▀  ▀▀▀▀   ▀▀▀    ▀    ▀▀▀   ▀▀▀    ▀   ▀
""")]
add_font("Half Block 6x5",HalfBlock6x5Font)

class HalfBlockHeavy6x5Font(Font):
    height = 5
    data = [utf8decode("""
000000111111222222333333444444555555666666777777888888999999  ..::////
▄███▄  ▐█▌  ▄███▄ ▄███▄    █▌ █████ ▄███▄ █████ ▄███▄ ▄███▄         █▌
█▌ ▐█  ▀█▌  ▀  ▐█ ▀  ▐█ █▌ █▌ █▌    █▌       █▌ █▌ ▐█ █▌ ▐█     █▌ ▐█
█▌ ▐█   █▌    ▄█▀   ██▌ █████ ████▄ ████▄   ▐█  ▐███▌ ▀████        █▌
█▌ ▐█   █▌  ▄█▀   ▄  ▐█    █▌    ▐█ █▌ ▐█   █▌  █▌ ▐█    ▐█     █▌▐█
▀███▀  ███▌ █████ ▀███▀    █▌ ████▀ ▀███▀  ▐█   ▀███▀ ▀███▀   █▌  █▌
""")]
add_font("Half Block Heavy 6x5",HalfBlockHeavy6x5Font)

class Thin6x6Font(Font):
    height = 6
    data = [utf8decode("""
000000111111222222333333444444555555666666777777888888999999''
┌───┐   ┐   ┌───┐ ┌───┐    ┐  ┌───  ┌───  ┌───┐ ┌───┐ ┌───┐ │
│   │   │       │     │ ┌  │  │     │         │ │   │ │   │  
│ / │   │   ┌───┘    ─┤ └──┼─ └───┐ ├───┐     ┼ ├───┤ └───┤ 
│   │   │   │         │    │      │ │   │     │ │   │     │ 
└───┘   ┴   └───  └───┘    ┴   ───┘ └───┘     ┴ └───┘  ───┘ 

"""),utf8decode(r'''
!!   """######$$$$$$%%%%%%&&&&&&((()))******++++++
│    ││  ┌ ┌  ┌─┼─┐ ┌┐  /  ┌─┐   / \      
│       ─┼─┼─ │ │   └┘ /   │ │  │   │  \ /    │
│        │ │  └─┼─┐   /   ┌─\┘  │   │ ──X── ──┼── 
│       ─┼─┼─   │ │  / ┌┐ │  \, │   │  / \    │
.        ┘ ┘  └─┼─┘ /  └┘ └───\  \ /  

'''),utf8decode(r"""
,,-----..//////::;;<<<<=====>>>>??????@@@@@@
             /                  ┌───┐ ┌───┐
            /  . .   / ──── \       │ │┌──┤
  ────     /        /        \    ┌─┘ ││  │ 
          /    . ,  \  ────  /    │   │└──┘
,      . /           \      /     .   └───┘

"""),utf8decode(r"""
[[\\\\\\]]^^^____``{{||}}~~~~~~
┌ \     ┐ /\     \ ┌ │ ┐ 
│  \    │          │ │ │ ┌─┐
│   \   │          ┤ │ ├   └─┘
│    \  │          │ │ │ 
└     \ ┘    ────  └ │ ┘ 

"""),utf8decode("""
AAAAAABBBBBBCCCCCCDDDDDDEEEEEEFFFFFFGGGGGGHHHHHHIIJJJJJJ
┌───┐ ┬───┐ ┌───┐ ┬───┐ ┬───┐ ┬───┐ ┌───┐ ┬   ┬ ┬     ┬
│   │ │   │ │     │   │ │     │     │     │   │ │     │
├───┤ ├───┤ │     │   │ ├──   ├──   │ ──┬ ├───┤ │     │
│   │ │   │ │     │   │ │     │     │   │ │   │ │ ┬   │
┴   ┴ ┴───┘ └───┘ ┴───┘ ┴───┘ ┴     └───┘ ┴   ┴ ┴ └───┘

"""),utf8decode("""
KKKKKKLLLLLLMMMMMMNNNNNNOOOOOOPPPPPPQQQQQQRRRRRRSSSSSS
┬   ┬ ┬     ┌─┬─┐ ┬─┐ ┬ ┌───┐ ┬───┐ ┌───┐ ┬───┐ ┌───┐
│ ┌─┘ │     │ │ │ │ │ │ │   │ │   │ │   │ │   │ │
├─┴┐  │     │ │ │ │ │ │ │   │ ├───┘ │   │ ├─┬─┘ └───┐
│  └┐ │     │   │ │ │ │ │   │ │     │  ┐│ │ └─┐     │
┴   ┴ ┴───┘ ┴   ┴ ┴ └─┴ └───┘ ┴     └──┼┘ ┴   ┴ └───┘
                                       └
"""),utf8decode("""
TTTTTTUUUUUUVVVVVVWWWWWWXXXXXXYYYYYYZZZZZZ
┌─┬─┐ ┬   ┬ ┬   ┬ ┬   ┬ ┬   ┬ ┬   ┬ ┌───┐ 
  │   │   │ │   │ │   │ └┐ ┌┘ │   │   ┌─┘ 
  │   │   │ │   │ │ │ │  ├─┤  └─┬─┘  ┌┘  
  │   │   │ └┐ ┌┘ │ │ │ ┌┘ └┐   │   ┌┘    
  ┴   └───┘  └─┘  └─┴─┘ ┴   ┴   ┴   └───┘ 
                                        
"""),utf8decode("""
aaaaaabbbbbbccccccddddddeeeeeefffgggggghhhhhhiijjj
                              ┌─┐      
      │               │       │        │     .  .
┌───┐ ├───┐ ┌───┐ ┌───┤ ┌───┐ ┼  ┌───┐ ├───┐ ┐  ┐
┌───┤ │   │ │     │   │ ├───┘ │  │   │ │   │ │  │
└───┴ └───┘ └───┘ └───┘ └───┘ ┴  └───┤ ┴   ┴ ┴  │
                                 └───┘         ─┘
"""),utf8decode("""
kkkkkkllmmmmmmnnnnnnooooooppppppqqqqqqrrrrrssssss
                                
│     │                                   
│ ┌─  │ ┬─┬─┐ ┬───┐ ┌───┐ ┌───┐ ┌───┐ ┬──┐ ┌───┐
├─┴┐  │ │ │ │ │   │ │   │ │   │ │   │ │    └───┐
┴  └─ └ ┴   ┴ ┴   ┴ └───┘ ├───┘ └───┤ ┴    └───┘
                          │         │     
"""),utf8decode("""
ttttuuuuuuvvvvvvwwwwwwxxxxxxyyyyyyzzzzzz
                
 │                        
─┼─ ┬   ┬ ┬   ┬ ┬   ┬ ─┐ ┌─ ┬   ┬ ────┬
 │  │   │ └┐ ┌┘ │ │ │  ├─┤  │   │ ┌───┘
 └─ └───┴  └─┘  └─┴─┘ ─┘ └─ └───┤ ┴────
                            └───┘
""")]
add_font("Thin 6x6",Thin6x6Font)


class HalfBlock7x7Font(Font):
    height = 7
    data = [utf8decode("""
0000000111111122222223333333444444455555556666666777777788888889999999'''
 ▄███▄   ▐█▌   ▄███▄  ▄███▄     █▌ ▐█████▌ ▄███▄ ▐█████▌ ▄███▄  ▄███▄ ▐█
▐█   █▌  ▀█▌  ▐█   █▌▐█   █▌▐█  █▌ ▐█     ▐█         ▐█ ▐█   █▌▐█   █▌▐█
▐█ ▐ █▌   █▌       █▌   ▐██ ▐█████▌▐████▄ ▐████▄     █▌  █████  ▀████▌  
▐█ ▌ █▌   █▌     ▄█▀      █▌    █▌      █▌▐█   █▌   ▐█  ▐█   █▌     █▌  
▐█   █▌   █▌   ▄█▀   ▐█   █▌    █▌      █▌▐█   █▌   █▌  ▐█   █▌     █▌  
 ▀███▀   ███▌ ▐█████▌ ▀███▀     █▌ ▐████▀  ▀███▀   ▐█    ▀███▀  ▀███▀ 

"""),utf8decode('''
!!!   """""#######$$$$$$$%%%%%%%&&&&&&&(((())))*******++++++
▐█    ▐█ █▌ ▐█ █▌    █    ▄  █▌   ▄█▄    █▌▐█   ▄▄ ▄▄    
▐█    ▐█ █▌▐█████▌ ▄███▄ ▐█▌▐█   ▐█ █▌  ▐█  █▌  ▀█▄█▀   ▐█
▐█          ▐█ █▌ ▐█▄█▄▄  ▀ █▌    ███   █▌  ▐█ ▐█████▌ ████▌
▐█         ▐█████▌ ▀▀█▀█▌  ▐█ ▄  ███▌▄  █▌  ▐█  ▄█▀█▄   ▐█ 
            ▐█ █▌  ▀███▀   █▌▐█▌▐█  █▌  ▐█  █▌  ▀▀ ▀▀    
▐█                   █    ▐█  ▀  ▀██▀█▌  █▌▐█ 
                   
'''),utf8decode("""
,,,------.../////:::;;;<<<<<<<======>>>>>>>???????@@@@@@@
               █▌          ▄█▌      ▐█▄     ▄███▄  ▄███▄       
              ▐█ ▐█ ▐█   ▄█▀  ▐████▌  ▀█▄  ▐█   █▌▐█ ▄▄█▌   
   ▐████▌     █▌       ▐██              ██▌    █▌ ▐█▐█▀█▌
             ▐█  ▐█ ▐█   ▀█▄  ▐████▌  ▄█▀     █▌  ▐█▐█▄█▌
             █▌     ▀      ▀█▌      ▐█▀           ▐█ ▀▀▀    
▐█       ▐█ ▐█                                █▌   ▀███▀ 
▀                          
"""),utf8decode(r"""
[[[[\\\\\]]]]^^^^^^^_____```{{{{{|||}}}}}~~~~~~~´´´
▐██▌▐█   ▐██▌  ▐█▌       ▐█    █▌▐█ ▐█           █▌  
▐█   █▌    █▌ ▐█ █▌       █▌  █▌ ▐█  ▐█   ▄▄    ▐█ 
▐█   ▐█    █▌▐█   █▌         ▄█▌ ▐█  ▐█▄ ▐▀▀█▄▄▌
▐█    █▌   █▌                ▀█▌ ▐█  ▐█▀     ▀▀
▐█    ▐█   █▌                 █▌ ▐█  ▐█ 
▐██▌   █▌▐██▌       █████      █▌▐█ ▐█  
                                      
"""),utf8decode("""
AAAAAAABBBBBBBCCCCCCCDDDDDDDEEEEEEEFFFFFFFGGGGGGGHHHHHHHIIIIJJJJJJJ
 ▄███▄ ▐████▄  ▄███▄ ▐████▄ ▐█████▌▐█████▌ ▄███▄ ▐█   █▌ ██▌     █▌ 
▐█   █▌▐█   █▌▐█     ▐█   █▌▐█     ▐█     ▐█     ▐█   █▌ ▐█      █▌  
▐█████▌▐█████ ▐█     ▐█   █▌▐████  ▐████  ▐█     ▐█████▌ ▐█      █▌
▐█   █▌▐█   █▌▐█     ▐█   █▌▐█     ▐█     ▐█  ██▌▐█   █▌ ▐█      █▌
▐█   █▌▐█   █▌▐█     ▐█   █▌▐█     ▐█     ▐█   █▌▐█   █▌ ▐█ ▐█   █▌
▐█   █▌▐████▀  ▀███▀ ▐████▀ ▐█████▌▐█      ▀███▀ ▐█   █▌ ██▌ ▀███▀ 
                     
"""),utf8decode("""
KKKKKKKLLLLLLLMMMMMMMMNNNNNNNOOOOOOOPPPPPPPQQQQQQQRRRRRRRSSSSSSS
▐█   █▌▐█      ▄█▌▐█▄ ▐██  █▌ ▄███▄ ▐████▄  ▄███▄ ▐████▄  ▄███▄ 
▐█  █▌ ▐█     ▐█ ▐▌ █▌▐██▌ █▌▐█   █▌▐█   █▌▐█   █▌▐█   █▌▐█     
▐█▄█▌  ▐█     ▐█ ▐▌ █▌▐█▐█ █▌▐█   █▌▐████▀ ▐█   █▌▐█████  ▀███▄ 
▐█▀█▌  ▐█     ▐█    █▌▐█ █▌█▌▐█   █▌▐█     ▐█   █▌▐█   █▌     █▌
▐█  █▌ ▐█     ▐█    █▌▐█ ▐██▌▐█   █▌▐█     ▐█ █▌█▌▐█   █▌     █▌
▐█   █▌▐█████▌▐█    █▌▐█  ██▌ ▀███▀ ▐█      ▀███▀ ▐█   █▌ ▀███▀ 
                                               ▀▀ 
"""),utf8decode("""
TTTTTTTUUUUUUUVVVVVVVWWWWWWWWXXXXXXXYYYYYYYZZZZZZZ
 █████▌▐█   █▌▐█   █▌▐█    █▌▐█   █▌ █▌  █▌▐█████▌ 
   █▌  ▐█   █▌ █▌ ▐█ ▐█    █▌ ▐█ █▌  ▐█ ▐█     █▌    
   █▌  ▐█   █▌ ▐█ █▌ ▐█    █▌  ▐█▌    ▐██     █▌        
   █▌  ▐█   █▌  ███  ▐█ ▐▌ █▌  ███     █▌    █▌
   █▌  ▐█   █▌  ▐█▌  ▐█ ▐▌ █▌ █▌ ▐█    █▌   █▌
   █▌   ▀███▀    █    ▀█▌▐█▀ ▐█   █▌   █▌  ▐█████▌       
                                               
"""),utf8decode("""
aaaaaaabbbbbbbcccccccdddddddeeeeeeefffffggggggghhhhhhhiiijjjj
       ▐█                 █▌         ▄█▌       ▐█      █▌  █▌
       ▐█                 █▌        ▐█         ▐█            
 ▄███▄ ▐████▄  ▄███▄  ▄████▌ ▄███▄ ▐███  ▄███▄ ▐████▄ ▐█▌ ▐█▌
  ▄▄▄█▌▐█   █▌▐█     ▐█   █▌▐█▄▄▄█▌ ▐█  ▐█   █▌▐█   █▌ █▌  █▌   
▐█▀▀▀█▌▐█   █▌▐█     ▐█   █▌▐█▀▀▀   ▐█  ▐█▄▄▄█▌▐█   █▌ █▌  █▌
 ▀████▌▐████▀  ▀███▀  ▀████▌ ▀███▀  ▐█    ▀▀▀█▌▐█   █▌ █▌  █▌
                                         ▀███▀           ▐██ 
"""),utf8decode("""
kkkkkkkllllmmmmmmmmnnnnnnnooooooopppppppqqqqqqqrrrrrrsssssss
▐█      ██                                                  
▐█      ▐█                                                  
▐█  ▄█▌ ▐█  ▄█▌▐█▄ ▐████▄  ▄███▄ ▐████▄  ▄████▌ ▄███▌ ▄███▄ 
▐█▄█▀   ▐█ ▐█ ▐▌ █▌▐█   █▌▐█   █▌▐█   █▌▐█   █▌▐█    ▐█▄▄▄  
▐█▀▀█▄  ▐█ ▐█ ▐▌ █▌▐█   █▌▐█   █▌▐█   █▌▐█   █▌▐█      ▀▀▀█▌
▐█   █▌ ▐█▌▐█    █▌▐█   █▌ ▀███▀ ▐████▀  ▀████▌▐█     ▀███▀ 
                                 ▐█          █▌
"""),utf8decode("""
tttttuuuuuuuvvvvvvvwwwwwwwwxxxxxxxyyyyyyyzzzzzzz
  █▌
  █▌
 ███▌▐█   █▌▐█   █▌▐█    █▌▐█   █▌▐█   █▌▐█████▌  
  █▌ ▐█   █▌ █▌ ▐█ ▐█    █▌ ▀█▄█▀ ▐█   █▌   ▄█▀ 
  █▌ ▐█   █▌  ███  ▐█ ▐▌ █▌ ▄█▀█▄ ▐█▄▄▄█▌ ▄█▀
  █▌  ▀███▀   ▐█▌   ▀█▌▐█▀ ▐█   █▌  ▀▀▀█▌▐█████▌
                                   ▀███▀ 
""")]
add_font("Half Block 7x7",HalfBlock7x7Font)


if __name__ == "__main__":
    l = get_all_fonts()
    all_ascii = "".join([chr(x) for x in range(32, 127)])
    print "Available Fonts:     (U) = UTF-8 required"
    print "----------------"
    for n,cls in l:
        f = cls()
        u = ""
        if f.utf8_required:
            u = "(U)"
        print ("%-20s %3s " % (n,u)),
        c = f.characters()
        if c == all_ascii:
            print "Full ASCII"
        elif c.startswith(all_ascii):
            print "Full ASCII + " + c[len(all_ascii):]
        else:
            print "Characters: " + c

########NEW FILE########
__FILENAME__ = graphics
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Urwid graphics widgets
#    Copyright (C) 2004-2007  Ian Ward
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

from __future__ import nested_scopes

from util import *
from canvas import *
from widget import *
from container import *
from escape import utf8decode
from display_common import AttrSpec

class BigText(FixedWidget):
    def __init__(self, markup, font):
        """
        markup -- same as Text widget markup
        font -- instance of a Font class
        """
        self.set_font(font)
        self.set_text(markup)
    
    def set_text(self, markup):
        self.text, self.attrib = decompose_tagmarkup(markup)
        self._invalidate()
    
    def get_text(self):
        """
        Returns (text, attributes).
        """
        return self.text, self.attrib
    
    def set_font(self, font):
        self.font = font
        self._invalidate()
    
    def pack(self, size=None, focus=False):
        rows = self.font.height
        cols = 0
        for c in self.text:
            cols += self.font.char_width(c)
        return cols, rows
    
    def render(self, size, focus=False):
        fixed_size(size) # complain if parameter is wrong
        a = None
        ai = ak = 0
        o = []
        rows = self.font.height
        attrib = self.attrib+[(None,len(self.text))]
        for ch in self.text:
            if not ak:
                a, ak = attrib[ai]
                ai += 1
            ak -= 1
            width = self.font.char_width(ch)
            if not width: 
                # ignore invalid characters
                continue
            c = self.font.render(ch)
            if a is not None:
                c = CompositeCanvas(c)
                c.fill_attr(a)
            o.append((c, None, False, width))
        if o:
            canv = CanvasJoin(o)
        else:
            canv = TextCanvas([""]*rows, maxcol=0, 
                check_width=False)
            canv = CompositeCanvas(canv)
        canv.set_depends([])
        return canv
        

class LineBox(WidgetDecoration, WidgetWrap):
    def __init__(self, original_widget):
        """Draw a line around original_widget."""
        
        tlcorner=None; tline=None; lline=None
        trcorner=None; blcorner=None; rline=None
        bline=None; brcorner=None
        
        def use_attr( a, t ):
            if a is not None:
                t = urwid.AttrWrap(t, a)
            return t
            
        tline = use_attr( tline, Divider(utf8decode("─")))
        bline = use_attr( bline, Divider(utf8decode("─")))
        lline = use_attr( lline, SolidFill(utf8decode("│")))
        rline = use_attr( rline, SolidFill(utf8decode("│")))
        tlcorner = use_attr( tlcorner, Text(utf8decode("┌")))
        trcorner = use_attr( trcorner, Text(utf8decode("┐")))
        blcorner = use_attr( blcorner, Text(utf8decode("└")))
        brcorner = use_attr( brcorner, Text(utf8decode("┘")))
        top = Columns([ ('fixed', 1, tlcorner),
            tline, ('fixed', 1, trcorner) ])
        middle = Columns( [('fixed', 1, lline),
            original_widget, ('fixed', 1, rline)], box_columns = [0,2],
            focus_column = 1)
        bottom = Columns([ ('fixed', 1, blcorner),
            bline, ('fixed', 1, brcorner) ])
        pile = Pile([('flow',top),middle,('flow',bottom)],
            focus_item = 1)
        
        WidgetDecoration.__init__(self, original_widget)
        WidgetWrap.__init__(self, pile)


class BarGraphMeta(WidgetMeta):
    """
    Detect subclass get_data() method and dynamic change to
    get_data() method and disable caching in these cases.

    This is for backwards compatibility only, new programs
    should use set_data() instead of overriding get_data().
    """
    def __init__(cls, name, bases, d):
        super(BarGraphMeta, cls).__init__(name, bases, d)

        if "get_data" in d:
            cls.render = nocache_widget_render(cls)
            cls._get_data = cls.get_data
        cls.get_data = property(
            lambda self: self._get_data,
            nocache_bargraph_get_data)

def nocache_bargraph_get_data(self, get_data_fn):
    """
    Disable caching on this bargraph because get_data_fn needs
    to be polled to get the latest data.
    """
    self.render = nocache_widget_render_instance(self)
    self._get_data = get_data_fn

class BarGraphError(Exception):
    pass

class BarGraph(BoxWidget):
    __metaclass__ = BarGraphMeta
    ignore_focus = True

    eighths = utf8decode(" ▁▂▃▄▅▆▇")
    hlines =  utf8decode("_⎺⎻─⎼⎽")
    
    def __init__(self, attlist, hatt=None, satt=None):
        """
        Create a bar graph with the passed display characteristics.
        see set_segment_attributes for a description of the parameters.
        """
        
        self.set_segment_attributes( attlist, hatt, satt )
        self.set_data([], 1, None)
        self.set_bar_width(None)
        
    def set_segment_attributes(self, attlist, hatt=None, satt=None ):
        """
        attlist -- list containing attribute or (attribute, character)
            tuple for background, first segment, and optionally
            following segments. ie. len(attlist) == num segments+1
            character defaults to ' ' if not specified.
        hatt -- list containing attributes for horizontal lines. First 
            lement is for lines on background, second is for lines
                   on first segment, third is for lines on second segment
            etc..
        satt -- dictionary containing attributes for smoothed 
            transitions of bars in UTF-8 display mode. The values
            are in the form:
                (fg,bg) : attr
            fg and bg are integers where 0 is the graph background,
            1 is the first segment, 2 is the second, ...  
            fg > bg in all values.  attr is an attribute with a 
            foreground corresponding to fg and a background 
            corresponding to bg.
            
        If satt is not None and the bar graph is being displayed in
        a terminal using the UTF-8 encoding then the character cell
        that is shared between the segments specified will be smoothed
        with using the UTF-8 vertical eighth characters.
        
        eg: set_segment_attributes( ['no', ('unsure',"?"), 'yes'] )
        will use the attribute 'no' for the background (the area from
        the top of the graph to the top of the bar), question marks 
        with the attribute 'unsure' will be used for the topmost 
        segment of the bar, and the attribute 'yes' will be used for
        the bottom segment of the bar.
        """
        self.attr = []
        self.char = []
        if len(attlist) < 2:
            raise BarGraphError, "attlist must include at least background and seg1: %s" % `attlist`
        assert len(attlist) >= 2, 'must at least specify bg and fg!'
        for a in attlist:
            if type(a)!=type(()):
                self.attr.append(a)
                self.char.append(' ')
            else:
                attr, ch = a
                self.attr.append(attr)
                self.char.append(ch)

        self.hatt = []
        if hatt is None:
            hatt = [self.attr[0]]
        elif type(hatt)!=type([]):
            hatt = [hatt]
        self.hatt = hatt
        
        if satt is None:
            satt = {}
        for i in satt.items():
            try:
                (fg,bg), attr = i
            except:
                raise BarGraphError, "satt not in (fg,bg:attr) form: %s"%`i`
            if type(fg) != type(0) or fg >= len(attlist):
                raise BarGraphError, "fg not valid integer: %s"%`fg`
            if type(bg) != type(0) or bg >= len(attlist):
                raise BarGraphError, "bg not valid integer: %s"%`fg`
            if fg<=bg:
                raise BarGraphError, "fg (%s) not > bg (%s)" %(fg,bg)
        self.satt = satt
            
            
        
    
    def set_data(self, bardata, top, hlines=None):
        """
        Store bar data, bargraph top and horizontal line positions.
        
        bardata -- a list of bar values.
        top -- maximum value for segments within bardata
        hlines -- None or a bar value marking horizontal line positions

        bar values are [ segment1, segment2, ... ] lists where top is 
        the maximal value corresponding to the top of the bar graph and
        segment1, segment2, ... are the values for the top of each 
        segment of this bar.  Simple bar graphs will only have one
        segment in each bar value.

        Eg: if top is 100 and there is a bar value of [ 80, 30 ] then
        the top of this bar will be at 80% of full height of the graph
        and it will have a second segment that starts at 30%.
        """
        if hlines is not None:
            hlines = hlines[:] # shallow copy
            hlines.sort()
        self.data = bardata, top, hlines
        self._invalidate()
    
    def _get_data(self, size):
        """
        Return (bardata, top, hlines)
        
        This function is called by render to retrieve the data for
        the graph. It may be overloaded to create a dynamic bar graph.
        
        This implementation will truncate the bardata list returned 
        if not all bars will fit within maxcol.
        """
        (maxcol, maxrow) = size
        bardata, top, hlines = self.data
        widths = self.calculate_bar_widths((maxcol,maxrow),bardata)
        
        if len(bardata) > len(widths):
            return bardata[:len(widths)], top, hlines

        return bardata, top, hlines
    
    def set_bar_width(self, width):
        """
        Set a preferred bar width for calculate_bar_widths to use.

        width -- width of bar or None for automatic width adjustment
        """
        assert width is None or width > 0
        self.bar_width = width
        self._invalidate()
    
    def calculate_bar_widths(self, size, bardata):
        """
        Return a list of bar widths, one for each bar in data.
        
        If self.bar_width is None this implementation will stretch 
        the bars across the available space specified by maxcol.
        """
        (maxcol, maxrow) = size
        
        if self.bar_width is not None:
            return [self.bar_width] * min(
                len(bardata), maxcol/self.bar_width )
        
        if len(bardata) >= maxcol:
            return [1] * maxcol
        
        widths = []
        grow = maxcol
        remain = len(bardata)
        for row in bardata:
            w = int(float(grow) / remain + 0.5)
            widths.append(w)
            grow -= w
            remain -= 1
        return widths
        

    def selectable(self):
        """
        Return False.
        """
        return False
    
    def use_smoothed(self):
        return self.satt and get_encoding_mode()=="utf8"
        
    def calculate_display(self, size):
        """
        Calculate display data.
        """
        (maxcol, maxrow) = size
        bardata, top, hlines = self.get_data( (maxcol, maxrow) )
        widths = self.calculate_bar_widths( (maxcol, maxrow), bardata )

        if self.use_smoothed():
            disp = calculate_bargraph_display(bardata, top, widths,
                maxrow * 8 )
            disp = self.smooth_display( disp )
    
        else:
            disp = calculate_bargraph_display(bardata, top, widths,
                maxrow )

        if hlines:
            disp = self.hlines_display( disp, top, hlines, maxrow )
        
        return disp

    def hlines_display(self, disp, top, hlines, maxrow ):
        """
        Add hlines to display structure represented as bar_type tuple
        values:
        (bg, 0-5)
        bg is the segment that has the hline on it
        0-5 is the hline graphic to use where 0 is a regular underscore
        and 1-5 are the UTF-8 horizontal scan line characters.
        """
        if self.use_smoothed():
            shiftr = 0
            r = [    (0.2, 1),
                (0.4, 2),
                (0.6, 3),
                (0.8, 4),
                (1.0, 5),]
        else:
            shiftr = 0.5
            r = [    (1.0, 0), ]

        # reverse the hlines to match screen ordering
        rhl = []
        for h in hlines:
            rh = float(top-h) * maxrow / top - shiftr
            if rh < 0:
                continue
            rhl.append(rh)
    
        # build a list of rows that will have hlines
        hrows = []
        last_i = -1
        for rh in rhl:
            i = int(rh)
            if i == last_i:
                continue
            f = rh-i
            for spl, chnum in r:
                if f < spl:
                    hrows.append( (i, chnum) )
                    break
            last_i = i

        # fill hlines into disp data
        def fill_row( row, chnum ):
            rout = []
            for bar_type, width in row:
                if (type(bar_type) == type(0) and 
                        len(self.hatt) > bar_type ):
                    rout.append( ((bar_type, chnum), width))
                    continue
                rout.append( (bar_type, width))
            return rout
            
        o = []
        k = 0
        rnum = 0
        for y_count, row in disp:
            if k >= len(hrows):
                o.append( (y_count, row) )
                continue
            end_block = rnum + y_count
            while k < len(hrows) and hrows[k][0] < end_block:
                i, chnum = hrows[k]
                if i-rnum > 0:
                    o.append( (i-rnum, row) )
                o.append( (1, fill_row( row, chnum ) ) )
                rnum = i+1
                k += 1
            if rnum < end_block:
                o.append( (end_block-rnum, row) )
                rnum = end_block
        
        #assert 0, o
        return o

        
    def smooth_display(self, disp):
        """
        smooth (col, row*8) display into (col, row) display using
        UTF vertical eighth characters represented as bar_type
        tuple values:
        ( fg, bg, 1-7 )
        where fg is the lower segment, bg is the upper segment and
        1-7 is the vertical eighth character to use.
        """
        o = []
        r = 0 # row remainder
        def seg_combine( (bt1,w1), (bt2,w2) ):
            if (bt1,w1) == (bt2,w2):
                return (bt1,w1), None, None
            wmin = min(w1,w2)
            l1 = l2 = None
            if w1>w2:
                l1 = (bt1, w1-w2)
            elif w2>w1:
                l2 = (bt2, w2-w1)
            if type(bt1)==type(()):
                return (bt1,wmin), l1, l2
            if not self.satt.has_key( (bt2, bt1) ):
                if r<4:
                    return (bt2,wmin), l1, l2
                return (bt1,wmin), l1, l2
            return ((bt2, bt1, 8-r), wmin), l1, l2
                    
        def row_combine_last( count, row ):
            o_count, o_row = o[-1]
            row = row[:] # shallow copy, so we don't destroy orig.
            o_row = o_row[:]
            l = []
            while row:
                (bt, w), l1, l2 = seg_combine(
                    o_row.pop(0), row.pop(0) )
                if l and l[-1][0] == bt:
                    l[-1] = (bt, l[-1][1]+w)
                else:
                    l.append((bt, w))
                if l1:
                    o_row = [l1]+o_row
                if l2:
                    row = [l2]+row
            
            assert not o_row
            o[-1] = ( o_count + count, l )
            
        
        # regroup into actual rows (8 disp rows == 1 actual row)
        for y_count, row in disp:
            if r:
                count = min( 8-r, y_count )
                row_combine_last( count, row )
                y_count -= count
                r += count
                r = r % 8
                if not y_count:
                    continue
            assert r == 0
            # copy whole blocks
            if y_count > 7:
                o.append( (y_count/8*8 , row) )
                y_count = y_count %8
                if not y_count:
                    continue
            o.append( (y_count, row) )
            r = y_count
        return [(y/8, row) for (y,row) in o]
            
            
    def render(self, size, focus=False):
        """
        Render BarGraph.
        """
        (maxcol, maxrow) = size
        disp = self.calculate_display( (maxcol,maxrow) )
        
        combinelist = []
        for y_count, row in disp:
            l = []
            for bar_type, width in row:
                if type(bar_type) == type(()):
                    if len(bar_type) == 3:
                        # vertical eighths
                        fg,bg,k = bar_type
                        a = self.satt[(fg,bg)]
                        t = self.eighths[k] * width
                    else:
                        # horizontal lines
                        bg,k = bar_type
                        a = self.hatt[bg]
                        t = self.hlines[k] * width
                else:
                    a = self.attr[bar_type]
                    t = self.char[bar_type] * width
                l.append( (a, t) )
            c = Text(l).render( (maxcol,) )
            assert c.rows() == 1, "Invalid characters in BarGraph!"
            combinelist += [(c, None, False)] * y_count
            
        canv = CanvasCombine(combinelist)
        return canv



def calculate_bargraph_display( bardata, top, bar_widths, maxrow ):
    """
    Calculate a rendering of the bar graph described by data, bar_widths
    and height.
    
    bardata -- bar information with same structure as BarGraph.data
    top -- maximal value for bardata segments
    bar_widths -- list of integer column widths for each bar
    maxrow -- rows for display of bargraph
    
    Returns a structure as follows:
      [ ( y_count, [ ( bar_type, width), ... ] ), ... ]

    The outer tuples represent a set of identical rows. y_count is
    the number of rows in this set, the list contains the data to be
    displayed in the row repeated through the set.

    The inner tuple describes a run of width characters of bar_type.
    bar_type is an integer starting from 0 for the background, 1 for
    the 1st segment, 2 for the 2nd segment etc..

    This function should complete in approximately O(n+m) time, where
    n is the number of bars displayed and m is the number of rows.
    """

    assert len(bardata) == len(bar_widths)

    maxcol = sum(bar_widths)

    # build intermediate data structure
    bars = len(bardata)
    rows = [None]*maxrow
    def add_segment( seg_num, col, row, width, rows=rows ):
        if rows[row]:
            last_seg, last_col, last_end = rows[row][-1]
            if last_end > col:
                if last_col >= col:
                    del rows[row][-1]
                else:
                    rows[row][-1] = ( last_seg, 
                        last_col, col)
            elif last_seg == seg_num and last_end == col:
                rows[row][-1] = ( last_seg, last_col, 
                    last_end+width)
                return
        elif rows[row] is None:
            rows[row] = []
        rows[row].append( (seg_num, col, col+width) )
    
    col = 0
    barnum = 0
    for bar in bardata:
        width = bar_widths[barnum]
        if width < 1:
            continue
        # loop through in reverse order
        tallest = maxrow
        segments = scale_bar_values( bar, top, maxrow )
        for k in range(len(bar)-1,-1,-1): 
            s = segments[k]
            
            if s >= maxrow: 
                continue
            if s < 0:
                s = 0
            if s < tallest:
                # add only properly-overlapped bars
                tallest = s
                add_segment( k+1, col, s, width )
        col += width
        barnum += 1
    
    #print `rows`
    # build rowsets data structure
    rowsets = []
    y_count = 0
    last = [(0,maxcol)]
    
    for r in rows:
        if r is None:
            y_count = y_count + 1
            continue
        if y_count:
            rowsets.append((y_count, last))
            y_count = 0
        
        i = 0 # index into "last"
        la, ln = last[i] # last attribute, last run length
        c = 0 # current column
        o = [] # output list to be added to rowsets
        for seg_num, start, end in r:
            while start > c+ln:
                o.append( (la, ln) )
                i += 1
                c += ln
                la, ln = last[i]
                
            if la == seg_num:
                # same attribute, can combine
                o.append( (la, end-c) )
            else:
                if start-c > 0:
                    o.append( (la, start-c) )
                o.append( (seg_num, end-start) )
            
            if end == maxcol:
                i = len(last)
                break
            
            # skip past old segments covered by new one
            while end >= c+ln:
                i += 1
                c += ln
                la, ln = last[i]

            if la != seg_num:
                ln = c+ln-end
                c = end
                continue
            
            # same attribute, can extend
            oa, on = o[-1]
            on += c+ln-end
            o[-1] = oa, on

            i += 1
            c += ln
            if c == maxcol:
                break
            assert i<len(last), `on, maxcol`
            la, ln = last[i]
    
        if i < len(last): 
            o += [(la,ln)]+last[i+1:]    
        last = o
        y_count += 1
    
    if y_count:
        rowsets.append((y_count, last))

    
    return rowsets
            

class GraphVScale(BoxWidget):
    def __init__(self, labels, top):
        """
        GraphVScale( [(label1 position, label1 markup),...], top )
        label position -- 0 < position < top for the y position
        label markup -- text markup for this label
        top -- top y position

        This widget is a vertical scale for the BarGraph widget that
        can correspond to the BarGraph's horizontal lines
        """
        self.set_scale( labels, top )
    
    def set_scale(self, labels, top):
        """
        set_scale( [(label1 position, label1 markup),...], top )
        label position -- 0 < position < top for the y position
        label markup -- text markup for this label
        top -- top y position
        """
        
        labels = labels[:] # shallow copy
        labels.sort()
        labels.reverse()
        self.pos = []
        self.txt = []
        for y, markup in labels:
            self.pos.append(y)
            self.txt.append( Text(markup) )
        self.top = top
        
    def selectable(self):
        """
        Return False.
        """
        return False
    
    def render(self, size, focus=False):
        """
        Render GraphVScale.
        """
        (maxcol, maxrow) = size
        pl = scale_bar_values( self.pos, self.top, maxrow )

        combinelist = []
        rows = 0
        for p, t in zip(pl, self.txt):
            p -= 1
            if p >= maxrow: break
            if p < rows: continue
            c = t.render((maxcol,))
            if p > rows:
                run = p-rows
                c = CompositeCanvas(c)
                c.pad_trim_top_bottom(run, 0)
            rows += c.rows()
            combinelist.append((c, None, False))
        c = CanvasCombine(combinelist)
        if maxrow - rows:
            c.pad_trim_top_bottom(0, maxrow - rows)
        return c
            
            
    
def scale_bar_values( bar, top, maxrow ):
    """
    Return a list of bar values aliased to integer values of maxrow.
    """
    return [maxrow - int(float(v) * maxrow / top + 0.5) for v in bar]


class ProgressBar( FlowWidget ):
    eighths = utf8decode(" ▏▎▍▌▋▊▉")
    def __init__(self, normal, complete, current=0, done=100, satt=None):
        """
        normal -- attribute for uncomplete part of progress bar
        complete -- attribute for complete part of progress bar
        current -- current progress
        done -- progress amount at 100%
        satt -- attribute for smoothed part of bar where the foreground
            of satt corresponds to the normal part and the
            background corresponds to the complete part.  If satt
            is None then no smoothing will be done.
        """
        self.normal = normal
        self.complete = complete
        self.current = current
        self.done = done
        self.satt = satt
    
    def set_completion(self, current ):
        """
        current -- current progress
        """
        self.current = current
        self._invalidate()
    
    def rows(self, size, focus=False):
        """
        Return 1.
        """
        return 1

    def render(self, size, focus=False):
        """
        Render the progress bar.
        """
        (maxcol,) = size
        percent = int( self.current*100/self.done )
        if percent < 0: percent = 0
        if percent > 100: percent = 100
            
        txt=Text( str(percent)+" %", 'center', 'clip' )
        c = txt.render((maxcol,))

        cf = float( self.current ) * maxcol / self.done
        ccol = int( cf )
        cs = 0
        if self.satt is not None:
            cs = int((cf - ccol) * 8)
        if ccol < 0 or (ccol == 0 and cs == 0):
            c._attr = [[(self.normal,maxcol)]]
        elif ccol >= maxcol:
            c._attr = [[(self.complete,maxcol)]]
        elif cs and c._text[0][ccol] == " ":
            t = c._text[0]
            cenc = self.eighths[cs].encode("utf-8")
            c._text[0] = t[:ccol]+cenc+t[ccol+1:]
            a = []
            if ccol > 0:
                a.append( (self.complete, ccol) )
            a.append((self.satt,len(cenc)))
            if maxcol-ccol-1 > 0:
                a.append( (self.normal, maxcol-ccol-1) )
            c._attr = [a]
            c._cs = [[(None, len(c._text[0]))]]
        else:
            c._attr = [[(self.complete,ccol),
                (self.normal,maxcol-ccol)]]
        return c
    
class PythonLogo(FixedWidget):
    def __init__(self):
        """
        Create canvas containing an ASCII version of the Python
        Logo and store it.
        """
        blu = AttrSpec('light blue', 'default')
        yel = AttrSpec('yellow', 'default')
        width = 17
        self._canvas = Text([
            (blu, "     ______\n"),
            (blu, "   _|_o__  |"), (yel, "__\n"),
            (blu, "  |   _____|"), (yel, "  |\n"),
            (blu, "  |__|  "), (yel, "______|\n"),
            (yel, "     |____o_|")]).render((width,))

    def pack(self, size=None, focus=False):
        """
        Return the size from our pre-rendered canvas.
        """
        return self._canvas.cols(), self._canvas.rows()

    def render(self, size, focus=False):
        """
        Return the pre-rendered canvas.
        """
        fixed_size(size)
        return self._canvas




########NEW FILE########
__FILENAME__ = html_fragment
#!/usr/bin/python
#
# Urwid html fragment output wrapper for "screen shots"
#    Copyright (C) 2004-2007  Ian Ward
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
HTML PRE-based UI implementation
"""

import util
from main_loop import ExitMainLoop
from display_common import AttrSpec, BaseScreen


# replace control characters with ?'s
_trans_table = "?" * 32 + "".join([chr(x) for x in range(32, 256)])

_default_foreground = 'black'
_default_background = 'light gray'

class HtmlGeneratorSimulationError(Exception):
    pass

class HtmlGenerator(BaseScreen):
    # class variables
    fragments = []
    sizes = []
    keys = []
    started = True

    def __init__(self):
        super(HtmlGenerator, self).__init__()
        self.colors = 16
        self.bright_is_bold = False # ignored
        self.has_underline = True # ignored
        self.register_palette_entry(None, 
            _default_foreground, _default_background)

    def set_terminal_properties(self, colors=None, bright_is_bold=None,
        has_underline=None):
        
        if colors is None:
            colors = self.colors
        if bright_is_bold is None:
            bright_is_bold = self.bright_is_bold
        if has_underline is None:
            has_unerline = self.has_underline

        self.colors = colors
        self.bright_is_bold = bright_is_bold
        self.has_underline = has_underline

    def set_mouse_tracking(self):
        """Not yet implemented"""
        pass

    def start(self):
        pass
    
    def stop(self):
        pass
    
    def set_input_timeouts(self, *args):
        pass

    def reset_default_terminal_palette(self, *args):
        pass

    def run_wrapper(self,fn):
        """Call fn."""
        return fn()

    def draw_screen(self, (cols, rows), r ):
        """Create an html fragment from the render object. 
        Append it to HtmlGenerator.fragments list.
        """
        # collect output in l
        l = []
        
        assert r.rows() == rows
    
        if r.cursor is not None:
            cx, cy = r.cursor
        else:
            cx = cy = None
        
        y = -1
        for row in r.content():
            y += 1
            col = 0
            
            for a, cs, run in row:
                run = run.translate(_trans_table)
                if isinstance(a, AttrSpec):
                    aspec = a
                else:
                    aspec = self._palette[a][
                        {1: 1, 16: 0, 88:2, 256:3}[self.colors]]

                if y == cy and col <= cx:
                    run_width = util.calc_width(run, 0,
                        len(run))
                    if col+run_width > cx:
                        l.append(html_span(run,
                            aspec, cx-col))
                    else:
                        l.append(html_span(run, aspec))
                    col += run_width
                else:
                    l.append(html_span(run, aspec))

            l.append("\n")
                        
        # add the fragment to the list
        self.fragments.append( "<pre>%s</pre>" % "".join(l) )
            
    def clear(self):
        """
        Force the screen to be completely repainted on the next
        call to draw_screen().

        (does nothing for html_fragment)
        """
        pass
            
    def get_cols_rows(self):
        """Return the next screen size in HtmlGenerator.sizes."""
        if not self.sizes:
            raise HtmlGeneratorSimulationError, "Ran out of screen sizes to return!"
        return self.sizes.pop(0)

    def get_input(self, raw_keys=False):
        """Return the next list of keypresses in HtmlGenerator.keys."""
        if not self.keys:
            raise ExitMainLoop()
        if raw_keys:
            return (self.keys.pop(0), [])
        return self.keys.pop(0)

_default_aspec = AttrSpec(_default_foreground, _default_background)
(_d_fg_r, _d_fg_g, _d_fg_b, _d_bg_r, _d_bg_g, _d_bg_b) = (
    _default_aspec.get_rgb_values())

def html_span(s, aspec, cursor = -1):
    fg_r, fg_g, fg_b, bg_r, bg_g, bg_b = aspec.get_rgb_values()
    # use real colours instead of default fg/bg
    if fg_r is None:
        fg_r, fg_g, fg_b = _d_fg_r, _d_fg_g, _d_fg_b
    if bg_r is None:
        bg_r, bg_g, bg_b = _d_bg_r, _d_bg_g, _d_bg_b
    html_fg = "#%02x%02x%02x" % (fg_r, fg_g, fg_b)
    html_bg = "#%02x%02x%02x" % (bg_r, bg_g, bg_b)
    if aspec.standout:
        html_fg, html_bg = html_bg, html_fg
    extra = (";text-decoration:underline" * aspec.underline +
        ";font-weight:bold" * aspec.bold)
    def html_span(fg, bg, s):
        if not s: return ""
        return ('<span style="color:%s;'
            'background:%s%s">%s</span>' % 
            (fg, bg, extra, html_escape(s)))
    
    if cursor >= 0:
        c_off, _ign = util.calc_text_pos(s, 0, len(s), cursor)
        c2_off = util.move_next_char(s, c_off, len(s))
        return (html_span(html_fg, html_bg, s[:c_off]) +
            html_span(html_bg, html_fg, s[c_off:c2_off]) +
            html_span(html_fg, html_bg, s[c2_off:]))
    else:
        return html_span(html_fg, html_bg, s)


def html_escape(text):
    """Escape text so that it will be displayed safely within HTML"""
    text = text.replace('&','&amp;')
    text = text.replace('<','&lt;')
    text = text.replace('>','&gt;')
    return text

def screenshot_init( sizes, keys ):
    """
    Replace curses_display.Screen and raw_display.Screen class with 
    HtmlGenerator.
    
    Call this function before executing an application that uses 
    curses_display.Screen to have that code use HtmlGenerator instead.
    
    sizes -- list of ( columns, rows ) tuples to be returned by each call
             to HtmlGenerator.get_cols_rows()
    keys -- list of lists of keys to be returned by each call to
            HtmlGenerator.get_input()
    
    Lists of keys may include "window resize" to force the application to
    call get_cols_rows and read a new screen size.

    For example, the following call will prepare an application to:
     1. start in 80x25 with its first call to get_cols_rows()
     2. take a screenshot when it calls draw_screen(..)
     3. simulate 5 "down" keys from get_input()
     4. take a screenshot when it calls draw_screen(..)
     5. simulate keys "a", "b", "c" and a "window resize"
     6. resize to 20x10 on its second call to get_cols_rows()
     7. take a screenshot when it calls draw_screen(..)
     8. simulate a "Q" keypress to quit the application

    screenshot_init( [ (80,25), (20,10) ],
        [ ["down"]*5, ["a","b","c","window resize"], ["Q"] ] )
    """
    try:
        for (row,col) in sizes:
            assert type(row) == type(0)
            assert row>0 and col>0
    except:
        raise Exception, "sizes must be in the form [ (col1,row1), (col2,row2), ...]"
    
    try:
        for l in keys:
            assert type(l) == type([])
            for k in l:
                assert type(k) == type("")
    except:
        raise Exception, "keys must be in the form [ [keyA1, keyA2, ..], [keyB1, ..], ...]"
    
    import curses_display
    curses_display.Screen = HtmlGenerator
    import raw_display
    raw_display.Screen = HtmlGenerator
    
    HtmlGenerator.sizes = sizes
    HtmlGenerator.keys = keys


def screenshot_collect():
    """Return screenshots as a list of HTML fragments."""
    l = HtmlGenerator.fragments
    HtmlGenerator.fragments = []
    return l

    

########NEW FILE########
__FILENAME__ = listbox
#!/usr/bin/python
#
# Urwid listbox class
#    Copyright (C) 2004-2010  Ian Ward
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

from util import *
from canvas import *
from widget import *
from decoration import calculate_filler, decompose_valign_height
import signals
from monitored_list import MonitoredList
from command_map import command_map


class ListWalkerError(Exception):
    pass

class ListWalker(object):
    __metaclass__ = signals.MetaSignals
    
    signals = ["modified"]

    def __hash__(self): return id(self)

    def _modified(self):
        signals.emit_signal(self, "modified")
    

class PollingListWalker(object):  # NOT ListWalker subclass
    def __init__(self, contents):
        """
        contents -- list to poll for changes
        """
        self.contents = contents
        if not type(contents) == type([]) and not hasattr( 
            contents, '__getitem__' ):
            raise ListWalkerError, "SimpleListWalker expecting list like object, got: "+`contents`
        self.focus = 0
    
    def _clamp_focus(self):
        if self.focus >= len(self.contents):
            self.focus = len(self.contents)-1
    
    def get_focus(self):
        """Return (focus widget, focus position)."""
        if len(self.contents) == 0: return None, None
        self._clamp_focus()
        return self.contents[self.focus], self.focus

    def set_focus(self, position):
        """Set focus position."""
        assert type(position) == type(1)
        self.focus = position

    def get_next(self, start_from):
        """
        Return (widget after start_from, position after start_from).
        """
        pos = start_from + 1
        if len(self.contents) <= pos: return None, None
        return self.contents[pos],pos

    def get_prev(self, start_from):
        """
        Return (widget before start_from, position before start_from).
        """
        pos = start_from - 1
        if pos < 0: return None, None
        return self.contents[pos],pos


class SimpleListWalker(MonitoredList, ListWalker):
    def __init__(self, contents):
        """
        contents -- list to copy into this object

        Changes made to this object (when it is treated as a list) are
        detected automatically and will cause ListBox objects using
        this list walker to be updated.
        """
        if not type(contents) == type([]) and not hasattr(contents, '__getitem__'):
            raise ListWalkerError, "SimpleListWalker expecting list like object, got: "+`contents`
        MonitoredList.__init__(self, contents)
        self.focus = 0

    def __hash__(self): return id(self)
    
    def _get_contents(self):
        """
        Return self.

        Provides compatibility with old SimpleListWalker class.
        """
        return self
    contents = property(_get_contents)

    def _modified(self):
        if self.focus >= len(self):
            self.focus = max(0, len(self)-1)
        ListWalker._modified(self)
    
    def set_modified_callback(self, callback):
        """
        This function inherited from MonitoredList is not 
        implemented in SimleListWalker.
        
        Use connect_signal(list_walker, "modified", ...) instead.
        """
        raise NotImplementedError('Use connect_signal('
            'list_walker, "modified", ...) instead.')
    
    def get_focus(self):
        """Return (focus widget, focus position)."""
        if len(self) == 0: return None, None
        return self[self.focus], self.focus

    def set_focus(self, position):
        """Set focus position."""
        assert type(position) == type(1)
        self.focus = position
        self._modified()

    def get_next(self, start_from):
        """
        Return (widget after start_from, position after start_from).
        """
        pos = start_from + 1
        if len(self) <= pos: return None, None
        return self[pos],pos

    def get_prev(self, start_from):
        """
        Return (widget before start_from, position before start_from).
        """
        pos = start_from - 1
        if pos < 0: return None, None
        return self[pos],pos
        

class ListBoxError(Exception):
    pass

class ListBox(BoxWidget):

    def __init__(self, body):
        """
        body -- a ListWalker-like object that contains
            widgets to be displayed inside the list box
        """
        if hasattr(body,'get_focus'):
            self.body = body
        else:
            self.body = PollingListWalker(body)

        try:
            connect_signal(self.body, "modified", self._invalidate)
        except NameError:
            # our list walker has no modified signal so we must not
            # cache our canvases because we don't know when our
            # content has changed
            self.render = nocache_widget_render_instance(self)

        # offset_rows is the number of rows between the top of the view
        # and the top of the focused item
        self.offset_rows = 0
        # inset_fraction is used when the focused widget is off the 
        # top of the view.  it is the fraction of the widget cut off 
        # at the top.  (numerator, denominator)
        self.inset_fraction = (0,1)

        # pref_col is the preferred column for the cursor when moving
        # between widgets that use the cursor (edit boxes etc.)
        self.pref_col = 'left'

        # variable for delayed focus change used by set_focus
        self.set_focus_pending = 'first selectable'
        
        # variable for delayed valign change used by set_focus_valign
        self.set_focus_valign_pending = None
        
    
    def calculate_visible(self, size, focus=False ):
        """ Return (middle,top,bottom) or None,None,None.

        middle -- ( row offset(when +ve) or inset(when -ve),
            focus widget, focus position, focus rows, 
            cursor coords or None )
        top -- ( # lines to trim off top, 
            list of (widget, position, rows) tuples above focus
            in order from bottom to top )
        bottom -- ( # lines to trim off bottom, 
            list of (widget, position, rows) tuples below focus
            in order from top to bottom )
        """
        (maxcol, maxrow) = size

        # 0. set the focus if a change is pending
        if self.set_focus_pending or self.set_focus_valign_pending:
            self._set_focus_complete( (maxcol, maxrow), focus )

        # 1. start with the focus widget
        focus_widget, focus_pos = self.body.get_focus()
        if focus_widget is None: #list box is empty?
            return None,None,None
        top_pos = bottom_pos = focus_pos
        
        offset_rows, inset_rows = self.get_focus_offset_inset(
            (maxcol,maxrow))
        #    force at least one line of focus to be visible
        if maxrow and offset_rows >= maxrow:
            offset_rows = maxrow -1
        
        #    adjust position so cursor remains visible
        cursor = None
        if maxrow and focus_widget.selectable() and focus:
            if hasattr(focus_widget,'get_cursor_coords'):
                cursor=focus_widget.get_cursor_coords((maxcol,))
        
        if cursor is not None:
            cx, cy = cursor
            effective_cy = cy + offset_rows - inset_rows
            
            if effective_cy < 0: # cursor above top?
                inset_rows = cy
            elif effective_cy >= maxrow: # cursor below bottom?
                offset_rows = maxrow - cy -1
        
        #    set trim_top by focus trimmimg
        trim_top = inset_rows
        focus_rows = focus_widget.rows((maxcol,),True)
        
        # 2. collect the widgets above the focus
        pos = focus_pos
        fill_lines = offset_rows
        fill_above = []
        top_pos = pos
        while fill_lines > 0:
            prev, pos = self.body.get_prev( pos )
            if prev is None: # run out of widgets above?
                offset_rows -= fill_lines
                break
            top_pos = pos
    
            p_rows = prev.rows( (maxcol,) )
            fill_above.append( (prev, pos, p_rows) )
            if p_rows > fill_lines: # crosses top edge?
                trim_top = p_rows-fill_lines
                break
            fill_lines -= p_rows
        
        trim_bottom = focus_rows + offset_rows - inset_rows - maxrow
        if trim_bottom < 0: trim_bottom = 0

        # 3. collect the widgets below the focus
        pos = focus_pos
        fill_lines = maxrow - focus_rows - offset_rows + inset_rows
        fill_below = []
        while fill_lines > 0:
            next, pos = self.body.get_next( pos )
            if next is None: # run out of widgets below?
                break
            bottom_pos = pos
                
            n_rows = next.rows( (maxcol,) )
            fill_below.append( (next, pos, n_rows) )
            if n_rows > fill_lines: # crosses bottom edge?
                trim_bottom = n_rows-fill_lines
                fill_lines -= n_rows
                break
            fill_lines -= n_rows

        # 4. fill from top again if necessary & possible
        fill_lines = max(0, fill_lines)
        
        if fill_lines >0 and trim_top >0:
            if fill_lines <= trim_top:
                trim_top -= fill_lines
                offset_rows += fill_lines
                fill_lines = 0
            else:
                fill_lines -= trim_top
                offset_rows += trim_top
                trim_top = 0
        pos = top_pos
        while fill_lines > 0:
            prev, pos = self.body.get_prev( pos )
            if prev is None:
                break

            p_rows = prev.rows( (maxcol,) )
            fill_above.append( (prev, pos, p_rows) )
            if p_rows > fill_lines: # more than required
                trim_top = p_rows-fill_lines
                offset_rows += fill_lines
                break
            fill_lines -= p_rows
            offset_rows += p_rows
        
        # 5. return the interesting bits
        return ((offset_rows - inset_rows, focus_widget, 
                focus_pos, focus_rows, cursor ),
            (trim_top, fill_above), (trim_bottom, fill_below))

    
    def render(self, size, focus=False ):
        """
        Render listbox and return canvas.
        """
        (maxcol, maxrow) = size

        middle, top, bottom = self.calculate_visible( 
            (maxcol, maxrow), focus=focus)
        if middle is None:
            return SolidCanvas(" ", maxcol, maxrow)
        
        _ignore, focus_widget, focus_pos, focus_rows, cursor = middle
        trim_top, fill_above = top
        trim_bottom, fill_below = bottom

        combinelist = []
        rows = 0
        fill_above.reverse() # fill_above is in bottom-up order
        for widget,w_pos,w_rows in fill_above:
            canvas = widget.render((maxcol,))
            if w_rows != canvas.rows():
                raise ListBoxError, "Widget %s at position %s within listbox calculated %d rows but rendered %d!"% (`widget`,`w_pos`,w_rows, canvas.rows())
            rows += w_rows
            combinelist.append((canvas, w_pos, False))
        
        focus_canvas = focus_widget.render((maxcol,), focus=focus)

        if focus_canvas.rows() != focus_rows:
            raise ListBoxError, "Focus Widget %s at position %s within listbox calculated %d rows but rendered %d!"% (`focus_widget`,`focus_pos`,focus_rows, focus_canvas.rows())
        c_cursor = focus_canvas.cursor
        if cursor != c_cursor:
            raise ListBoxError, "Focus Widget %s at position %s within listbox calculated cursor coords %s but rendered cursor coords %s!" %(`focus_widget`,`focus_pos`,`cursor`,`c_cursor`)
            
        rows += focus_rows
        combinelist.append((focus_canvas, focus_pos, True))
        
        for widget,w_pos,w_rows in fill_below:
            canvas = widget.render((maxcol,))
            if w_rows != canvas.rows():
                raise ListBoxError, "Widget %s at position %s within listbox calculated %d rows but rendered %d!"% (`widget`,`w_pos`,w_rows, canvas.rows())
            rows += w_rows
            combinelist.append((canvas, w_pos, False))
        
        final_canvas = CanvasCombine(combinelist)
        
        if trim_top:    
            final_canvas.trim(trim_top)
            rows -= trim_top
        if trim_bottom:    
            final_canvas.trim_end(trim_bottom)
            rows -= trim_bottom
        
        assert rows <= maxrow, "Listbox contents too long!  Probably urwid's fault (please report): %s" % `top,middle,bottom`
        
        if rows < maxrow:
            bottom_pos = focus_pos
            if fill_below: bottom_pos = fill_below[-1][1]
            assert trim_bottom==0 and self.body.get_next(bottom_pos) == (None,None), "Listbox contents too short!  Probably urwid's fault (please report): %s" % `top,middle,bottom`
            final_canvas.pad_trim_top_bottom(0, maxrow - rows)

        return final_canvas


    def set_focus_valign(self, valign):
        """Set the focus widget's display offset and inset.

        valign -- one of:
            'top', 'middle', 'bottom'
            ('fixed top', rows)
            ('fixed bottom', rows)
            ('relative', percentage 0=top 100=bottom)
        """
        vt,va,ht,ha=decompose_valign_height(valign,None,ListBoxError)
        self.set_focus_valign_pending = vt,va


    def set_focus(self, position, coming_from=None):
        """
        Set the focus position and try to keep the old focus in view.

        position -- a position compatible with self.body.set_focus
        coming_from -- set to 'above' or 'below' if you know that
                       old position is above or below the new position.
        """
        assert coming_from in ('above', 'below', None)
        focus_widget, focus_pos = self.body.get_focus()
        
        self.set_focus_pending = coming_from, focus_widget, focus_pos
        self.body.set_focus( position )

    def get_focus(self):
        """
        Return a (focus widget, focus position) tuple.
        """
        return self.body.get_focus()

    def _set_focus_valign_complete(self, size, focus):
        """
        Finish setting the offset and inset now that we have have a 
        maxcol & maxrow.
        """
        (maxcol, maxrow) = size
        vt,va = self.set_focus_valign_pending
        self.set_focus_valign_pending = None
        self.set_focus_pending = None

        focus_widget, focus_pos = self.body.get_focus()
        if focus_widget is None:
            return
        
        rows = focus_widget.rows((maxcol,), focus)
        rtop, rbot = calculate_filler( vt, va, 'fixed', rows, 
            None, maxrow )

        self.shift_focus((maxcol, maxrow), rtop)
        
    def _set_focus_first_selectable(self, size, focus):
        """
        Choose the first visible, selectable widget below the
        current focus as the focus widget.
        """
        (maxcol, maxrow) = size
        self.set_focus_valign_pending = None
        self.set_focus_pending = None
        middle, top, bottom = self.calculate_visible( 
            (maxcol, maxrow), focus=focus)
        if middle is None:
            return
        
        row_offset, focus_widget, focus_pos, focus_rows, cursor = middle
        trim_top, fill_above = top
        trim_bottom, fill_below = bottom

        if focus_widget.selectable():
            return

        if trim_bottom:
            fill_below = fill_below[:-1]
        new_row_offset = row_offset + focus_rows
        for widget, pos, rows in fill_below:
            if widget.selectable():
                self.body.set_focus(pos)
                self.shift_focus((maxcol, maxrow), 
                    new_row_offset)
                return
            new_row_offset += rows

    def _set_focus_complete(self, size, focus):
        """
        Finish setting the position now that we have maxcol & maxrow.
        """
        (maxcol, maxrow) = size
        self._invalidate()
        if self.set_focus_pending == "first selectable":
            return self._set_focus_first_selectable(
                (maxcol,maxrow), focus)
        if self.set_focus_valign_pending is not None:
            return self._set_focus_valign_complete(
                (maxcol,maxrow), focus)
        coming_from, focus_widget, focus_pos = self.set_focus_pending
        self.set_focus_pending = None
        
        # new position
        new_focus_widget, position = self.body.get_focus()
        if focus_pos == position:
            # do nothing
            return
            
        # restore old focus temporarily
        self.body.set_focus(focus_pos)
                
        middle,top,bottom=self.calculate_visible((maxcol,maxrow),focus)
        focus_offset, focus_widget, focus_pos, focus_rows, cursor=middle
        trim_top, fill_above = top
        trim_bottom, fill_below = bottom
        
        offset = focus_offset
        for widget, pos, rows in fill_above:
            offset -= rows
            if pos == position:
                self.change_focus((maxcol, maxrow), pos,
                    offset, 'below' )
                return

        offset = focus_offset + focus_rows
        for widget, pos, rows in fill_below:
            if pos == position:
                self.change_focus((maxcol, maxrow), pos,
                    offset, 'above' )
                return
            offset += rows

        # failed to find widget among visible widgets
        self.body.set_focus( position )
        widget, position = self.body.get_focus()
        rows = widget.rows((maxcol,), focus)

        if coming_from=='below':
            offset = 0
        elif coming_from=='above':
            offset = maxrow-rows
        else:
            offset = (maxrow-rows)/2
        self.shift_focus((maxcol, maxrow), offset)
    

    def shift_focus(self, size, offset_inset):
        """Move the location of the current focus relative to the top.
        
        offset_inset -- either the number of rows between the 
          top of the listbox and the start of the focus widget (+ve
          value) or the number of lines of the focus widget hidden off 
          the top edge of the listbox (-ve value) or 0 if the top edge
          of the focus widget is aligned with the top edge of the
          listbox
        """
        (maxcol, maxrow) = size
        
        if offset_inset >= 0:
            if offset_inset >= maxrow:
                raise ListBoxError, "Invalid offset_inset: %s, only %s rows in list box"% (`offset_inset`, `maxrow`)
            self.offset_rows = offset_inset
            self.inset_fraction = (0,1)
        else:
            target, _ignore = self.body.get_focus()
            tgt_rows = target.rows( (maxcol,), True )
            if offset_inset + tgt_rows <= 0:
                raise ListBoxError, "Invalid offset_inset: %s, only %s rows in target!" %(`offset_inset`, `tgt_rows`)
            self.offset_rows = 0
            self.inset_fraction = (-offset_inset,tgt_rows)
        self._invalidate()
                
    def update_pref_col_from_focus(self, size):
        """Update self.pref_col from the focus widget."""
        (maxcol, maxrow) = size
        
        widget, old_pos = self.body.get_focus()
        if widget is None: return

        pref_col = None
        if hasattr(widget,'get_pref_col'):
            pref_col = widget.get_pref_col((maxcol,))
        if pref_col is None and hasattr(widget,'get_cursor_coords'):
            coords = widget.get_cursor_coords((maxcol,))
            if type(coords) == type(()):
                pref_col,y = coords
        if pref_col is not None: 
            self.pref_col = pref_col


    def change_focus(self, size, position, 
            offset_inset = 0, coming_from = None, 
            cursor_coords = None, snap_rows = None):
        """Change the current focus widget.
        
        position -- a position compatible with self.body.set_focus
        offset_inset -- either the number of rows between the 
          top of the listbox and the start of the focus widget (+ve
          value) or the number of lines of the focus widget hidden off 
          the top edge of the listbox (-ve value) or 0 if the top edge
          of the focus widget is aligned with the top edge of the
          listbox (default if unspecified)
        coming_from -- eiter 'above', 'below' or unspecified (None)
        cursor_coords -- (x, y) tuple indicating the desired
          column and row for the cursor, a (x,) tuple indicating only
          the column for the cursor, or unspecified (None)
        snap_rows -- the maximum number of extra rows to scroll
          when trying to "snap" a selectable focus into the view
        """
        (maxcol, maxrow) = size
        
        # update pref_col before change
        if cursor_coords:
            self.pref_col = cursor_coords[0]
        else:
            self.update_pref_col_from_focus((maxcol,maxrow))

        self._invalidate()
        self.body.set_focus(position)
        target, _ignore = self.body.get_focus()
        tgt_rows = target.rows( (maxcol,), True)
        if snap_rows is None:
            snap_rows = maxrow - 1

        # "snap" to selectable widgets
        align_top = 0
        align_bottom = maxrow - tgt_rows
        
        if ( coming_from == 'above' 
                and target.selectable()
                and offset_inset > align_bottom ):
            if snap_rows >= offset_inset - align_bottom:
                offset_inset = align_bottom
            elif snap_rows >= offset_inset - align_top:
                offset_inset = align_top
            else:
                offset_inset -= snap_rows
            
        if ( coming_from == 'below' 
                and target.selectable() 
                and offset_inset < align_top ):
            if snap_rows >= align_top - offset_inset:
                offset_inset = align_top
            elif snap_rows >= align_bottom - offset_inset:
                offset_inset = align_bottom
            else:
                offset_inset += snap_rows
        
        # convert offset_inset to offset_rows or inset_fraction
        if offset_inset >= 0:
            self.offset_rows = offset_inset
            self.inset_fraction = (0,1)
        else:
            if offset_inset + tgt_rows <= 0:
                raise ListBoxError, "Invalid offset_inset: %s, only %s rows in target!" %(offset_inset, tgt_rows)
            self.offset_rows = 0
            self.inset_fraction = (-offset_inset,tgt_rows)
        
        if cursor_coords is None:
            if coming_from is None: 
                return # must either know row or coming_from
            cursor_coords = (self.pref_col,)
        
        if not hasattr(target,'move_cursor_to_coords'):
            return
            
        attempt_rows = []
        
        if len(cursor_coords) == 1:
            # only column (not row) specified
            # start from closest edge and move inwards
            (pref_col,) = cursor_coords
            if coming_from=='above':
                attempt_rows = range( 0, tgt_rows )
            else:
                assert coming_from == 'below', "must specify coming_from ('above' or 'below') if cursor row is not specified"
                attempt_rows = range( tgt_rows, -1, -1)
        else:
            # both column and row specified
            # start from preferred row and move back to closest edge
            (pref_col, pref_row) = cursor_coords
            if pref_row < 0 or pref_row >= tgt_rows:
                raise ListBoxError, "cursor_coords row outside valid range for target. pref_row:%s target_rows:%s"%(`pref_row`,`tgt_rows`)

            if coming_from=='above':
                attempt_rows = range( pref_row, -1, -1 )
            elif coming_from=='below':
                attempt_rows = range( pref_row, tgt_rows )
            else:
                attempt_rows = [pref_row]

        for row in attempt_rows:
            if target.move_cursor_to_coords((maxcol,),pref_col,row):
                break

    def get_focus_offset_inset(self, size):
        """Return (offset rows, inset rows) for focus widget."""
        (maxcol, maxrow) = size
        focus_widget, pos = self.body.get_focus()
        focus_rows = focus_widget.rows((maxcol,), True)
        offset_rows = self.offset_rows
        inset_rows = 0
        if offset_rows == 0:
            inum, iden = self.inset_fraction
            if inum < 0 or iden < 0 or inum >= iden:
                raise ListBoxError, "Invalid inset_fraction: %s"%`self.inset_fraction`
            inset_rows = focus_rows * inum / iden
            assert inset_rows < focus_rows, "urwid inset_fraction error (please report)"
        return offset_rows, inset_rows


    def make_cursor_visible(self, size):
        """Shift the focus widget so that its cursor is visible."""
        (maxcol, maxrow) = size
        
        focus_widget, pos = self.body.get_focus()
        if focus_widget is None:
            return
        if not focus_widget.selectable(): 
            return
        if not hasattr(focus_widget,'get_cursor_coords'): 
            return
        cursor = focus_widget.get_cursor_coords((maxcol,))
        if cursor is None: 
            return
        cx, cy = cursor
        offset_rows, inset_rows = self.get_focus_offset_inset(
            (maxcol, maxrow))
        
        if cy < inset_rows:
            self.shift_focus( (maxcol,maxrow), - (cy) )
            return
            
        if offset_rows - inset_rows + cy >= maxrow:
            self.shift_focus( (maxcol,maxrow), maxrow-cy-1 )
            return


    def keypress(self, size, key):
        """Move selection through the list elements scrolling when 
        necessary. 'up' and 'down' are first passed to widget in focus
        in case that widget can handle them. 'page up' and 'page down'
        are always handled by the ListBox.
        
        Keystrokes handled by this widget are:
         'up'        up one line (or widget)
         'down'      down one line (or widget)
         'page up'   move cursor up one listbox length
         'page down' move cursor down one listbox length
        """
        (maxcol, maxrow) = size

        if self.set_focus_pending or self.set_focus_valign_pending:
            self._set_focus_complete( (maxcol,maxrow), focus=True )
            
        focus_widget, pos = self.body.get_focus()
        if focus_widget is None: # empty listbox, can't do anything
            return key
            
        if key not in ['page up','page down']:
            if focus_widget.selectable():
                key = focus_widget.keypress((maxcol,),key)
            if key is None: 
                self.make_cursor_visible((maxcol,maxrow))
                return
        
        # pass off the heavy lifting
        if command_map[key] == 'cursor up':
            return self._keypress_up((maxcol, maxrow))
            
        if command_map[key] == 'cursor down':
            return self._keypress_down((maxcol, maxrow))

        if command_map[key] == 'cursor page up':
            return self._keypress_page_up((maxcol, maxrow))
            
        if command_map[key] == 'cursor page down':
            return self._keypress_page_down((maxcol, maxrow))

        return key
        
    
    def _keypress_up(self, size):
        (maxcol, maxrow) = size
    
        middle, top, bottom = self.calculate_visible(
            (maxcol,maxrow), True)
        if middle is None: return 'up'
        
        focus_row_offset,focus_widget,focus_pos,_ignore,cursor = middle
        trim_top, fill_above = top
        
        row_offset = focus_row_offset
        
        # look for selectable widget above
        pos = focus_pos
        widget = None
        for widget, pos, rows in fill_above:
            row_offset -= rows
            if widget.selectable():
                # this one will do
                self.change_focus((maxcol,maxrow), pos,
                    row_offset, 'below')
                return
        
        # at this point we must scroll
        row_offset += 1
        self._invalidate()
        
        if row_offset > 0:
            # need to scroll in another candidate widget
            widget, pos = self.body.get_prev(pos)
            if widget is None:
                # cannot scroll any further
                return 'up' # keypress not handled
            rows = widget.rows((maxcol,), True)
            row_offset -= rows
            if widget.selectable():
                # this one will do
                self.change_focus((maxcol,maxrow), pos,
                    row_offset, 'below')
                return
        
        if not focus_widget.selectable() or focus_row_offset+1>=maxrow:
            # just take top one if focus is not selectable
            # or if focus has moved out of view
            if widget is None:
                self.shift_focus((maxcol,maxrow), row_offset)
                return
            self.change_focus((maxcol,maxrow), pos,
                row_offset, 'below')
            return

        # check if cursor will stop scroll from taking effect
        if cursor is not None:
            x,y = cursor
            if y+focus_row_offset+1 >= maxrow:
                # cursor position is a problem, 
                # choose another focus
                if widget is None:
                    # try harder to get prev widget
                    widget, pos = self.body.get_prev(pos)
                    if widget is None:
                        return # can't do anything
                    rows = widget.rows((maxcol,), True)
                    row_offset -= rows
                
                if -row_offset >= rows:
                    # must scroll further than 1 line
                    row_offset = - (rows-1)
                
                self.change_focus((maxcol,maxrow),pos,
                    row_offset, 'below')
                return

        # if all else fails, just shift the current focus.
        self.shift_focus((maxcol,maxrow), focus_row_offset+1)
            
            
                
    def _keypress_down(self, size):
        (maxcol, maxrow) = size
    
        middle, top, bottom = self.calculate_visible(
            (maxcol,maxrow), True)
        if middle is None: return 'down'
            
        focus_row_offset,focus_widget,focus_pos,focus_rows,cursor=middle
        trim_bottom, fill_below = bottom
        
        row_offset = focus_row_offset + focus_rows
        rows = focus_rows
    
        # look for selectable widget below
        pos = focus_pos
        widget = None
        for widget, pos, rows in fill_below:
            if widget.selectable():
                # this one will do
                self.change_focus((maxcol,maxrow), pos,
                    row_offset, 'above')
                return
            row_offset += rows
        
        # at this point we must scroll
        row_offset -= 1
        self._invalidate()
        
        if row_offset < maxrow:
            # need to scroll in another candidate widget
            widget, pos = self.body.get_next(pos)
            if widget is None:
                # cannot scroll any further
                return 'down' # keypress not handled
            if widget.selectable():
                # this one will do
                self.change_focus((maxcol,maxrow), pos,
                    row_offset, 'above')
                return
            rows = widget.rows((maxcol,))
            row_offset += rows
        
        if not focus_widget.selectable() or focus_row_offset+focus_rows-1 <= 0:
            # just take bottom one if current is not selectable
            # or if focus has moved out of view
            if widget is None:
                self.shift_focus((maxcol,maxrow), 
                    row_offset-rows)
                return
            # FIXME: catch this bug in testcase
            #self.change_focus((maxcol,maxrow), pos,
            #    row_offset+rows, 'above')
            self.change_focus((maxcol,maxrow), pos,
                row_offset-rows, 'above')
            return

        # check if cursor will stop scroll from taking effect
        if cursor is not None:
            x,y = cursor
            if y+focus_row_offset-1 < 0:
                # cursor position is a problem,
                # choose another focus
                if widget is None:
                    # try harder to get next widget
                    widget, pos = self.body.get_next(pos)
                    if widget is None:
                        return # can't do anything
                else:
                    row_offset -= rows

                if row_offset >= maxrow:
                    # must scroll further than 1 line
                    row_offset = maxrow-1
                    
                self.change_focus((maxcol,maxrow),pos,
                    row_offset, 'above', )
                return

        # if all else fails, keep the current focus.
        self.shift_focus((maxcol,maxrow), focus_row_offset-1)
                
                
            
    def _keypress_page_up(self, size):
        (maxcol, maxrow) = size
        
        middle, top, bottom = self.calculate_visible(
            (maxcol,maxrow), True)
        if middle is None: return 'page up'
            
        row_offset, focus_widget, focus_pos, focus_rows, cursor = middle
        trim_top, fill_above = top

        # topmost_visible is row_offset rows above top row of 
        # focus (+ve) or -row_offset rows below top row of focus (-ve)
        topmost_visible = row_offset
        
        # scroll_from_row is (first match)
        # 1. topmost visible row if focus is not selectable
        # 2. row containing cursor if focus has a cursor
        # 3. top row of focus widget if it is visible
        # 4. topmost visible row otherwise
        if not focus_widget.selectable():
            scroll_from_row = topmost_visible
        elif cursor is not None:
            x,y = cursor
            scroll_from_row = -y
        elif row_offset >= 0:
            scroll_from_row = 0
        else:
            scroll_from_row = topmost_visible
        
        # snap_rows is maximum extra rows to scroll when
        # snapping to new a focus
        snap_rows = topmost_visible - scroll_from_row

        # move row_offset to the new desired value (1 "page" up)
        row_offset = scroll_from_row + maxrow
        
        # not used below:
        scroll_from_row = topmost_visible = None
        
        
        # gather potential target widgets
        t = []
        # add current focus
        t.append((row_offset,focus_widget,focus_pos,focus_rows))
        pos = focus_pos
        # include widgets from calculate_visible(..)
        for widget, pos, rows in fill_above:
            row_offset -= rows
            t.append( (row_offset, widget, pos, rows) )
        # add newly visible ones, including within snap_rows
        snap_region_start = len(t)
        while row_offset > -snap_rows:
            widget, pos = self.body.get_prev(pos)
            if widget is None: break
            rows = widget.rows((maxcol,))
            row_offset -= rows
            # determine if one below puts current one into snap rgn
            if row_offset > 0:
                snap_region_start += 1
            t.append( (row_offset, widget, pos, rows) ) 

        # if we can't fill the top we need to adjust the row offsets
        row_offset, w, p, r = t[-1]
        if row_offset > 0:
            adjust = - row_offset
            t = [(ro+adjust, w, p, r) for (ro,w,p,r) in t]    

        # if focus_widget (first in t) is off edge, remove it
        row_offset, w, p, r = t[0]
        if row_offset >= maxrow:
            del t[0]
            snap_region_start -= 1
        
        # we'll need this soon
        self.update_pref_col_from_focus((maxcol,maxrow))
            
        # choose the topmost selectable and (newly) visible widget
        # search within snap_rows then visible region
        search_order = ( range( snap_region_start, len(t))
                + range( snap_region_start-1, -1, -1 ) )
        #assert 0, `t, search_order`
        bad_choices = []
        cut_off_selectable_chosen = 0
        for i in search_order:
            row_offset, widget, pos, rows = t[i]
            if not widget.selectable(): 
                continue

            # try selecting this widget
            pref_row = max(0, -row_offset)
            
            # if completely within snap region, adjust row_offset
            if rows + row_offset <= 0:
                self.change_focus( (maxcol,maxrow), pos,
                    -(rows-1), 'below',
                    (self.pref_col, rows-1),
                    snap_rows-((-row_offset)-(rows-1)))
            else:
                self.change_focus( (maxcol,maxrow), pos,
                    row_offset, 'below', 
                    (self.pref_col, pref_row), snap_rows )
            
            # if we're as far up as we can scroll, take this one
            if (fill_above and self.body.get_prev(fill_above[-1][1])
                == (None,None) ):
                pass #return
            
            # find out where that actually puts us
            middle, top, bottom = self.calculate_visible(
                (maxcol,maxrow), True)
            act_row_offset, _ign1, _ign2, _ign3, _ign4 = middle
            
            # discard chosen widget if it will reduce scroll amount
            # because of a fixed cursor (absolute last resort)
            if act_row_offset > row_offset+snap_rows:
                bad_choices.append(i)
                continue
            if act_row_offset < row_offset:
                bad_choices.append(i)
                continue
            
            # also discard if off top edge (second last resort)
            if act_row_offset < 0:
                bad_choices.append(i)
                cut_off_selectable_chosen = 1
                continue
            
            return
            
        # anything selectable is better than what follows:
        if cut_off_selectable_chosen:
            return
                
        if fill_above and focus_widget.selectable():
            # if we're at the top and have a selectable, return
            if self.body.get_prev(fill_above[-1][1]) == (None,None):
                pass #return
                
        # if still none found choose the topmost widget
        good_choices = [j for j in search_order if j not in bad_choices]
        for i in good_choices + search_order:
            row_offset, widget, pos, rows = t[i]
            if pos == focus_pos: continue
            
            # if completely within snap region, adjust row_offset
            if rows + row_offset <= 0:
                snap_rows -= (-row_offset) - (rows-1)
                row_offset = -(rows-1)
                
            self.change_focus( (maxcol,maxrow), pos,
                row_offset, 'below', None,
                snap_rows )
            return
            
        # no choices available, just shift current one
        self.shift_focus((maxcol, maxrow), min(maxrow-1,row_offset))
        
        # final check for pathological case where we may fall short
        middle, top, bottom = self.calculate_visible(
            (maxcol,maxrow), True)
        act_row_offset, _ign1, pos, _ign2, _ign3 = middle
        if act_row_offset >= row_offset:
            # no problem
            return
            
        # fell short, try to select anything else above
        if not t:
            return
        _ign1, _ign2, pos, _ign3 = t[-1]
        widget, pos = self.body.get_prev(pos)
        if widget is None:
            # no dice, we're stuck here
            return
        # bring in only one row if possible
        rows = widget.rows((maxcol,), True)
        self.change_focus((maxcol,maxrow), pos, -(rows-1),
            'below', (self.pref_col, rows-1), 0 )
        
            
        
        
        
        
    def _keypress_page_down(self, size):
        (maxcol, maxrow) = size
        
        middle, top, bottom = self.calculate_visible(
            (maxcol,maxrow), True)
        if middle is None: return 'page down'
            
        row_offset, focus_widget, focus_pos, focus_rows, cursor = middle
        trim_bottom, fill_below = bottom

        # bottom_edge is maxrow-focus_pos rows below top row of focus
        bottom_edge = maxrow - row_offset
        
        # scroll_from_row is (first match)
        # 1. bottom edge if focus is not selectable
        # 2. row containing cursor + 1 if focus has a cursor
        # 3. bottom edge of focus widget if it is visible
        # 4. bottom edge otherwise
        if not focus_widget.selectable():
            scroll_from_row = bottom_edge
        elif cursor is not None:
            x,y = cursor
            scroll_from_row = y + 1
        elif bottom_edge >= focus_rows:
            scroll_from_row = focus_rows
        else:
            scroll_from_row = bottom_edge
        
        # snap_rows is maximum extra rows to scroll when
        # snapping to new a focus
        snap_rows = bottom_edge - scroll_from_row

        # move row_offset to the new desired value (1 "page" down)
        row_offset = -scroll_from_row
        
        # not used below:
        scroll_from_row = bottom_edge = None
        
        
        # gather potential target widgets
        t = []
        # add current focus
        t.append((row_offset,focus_widget,focus_pos,focus_rows))
        pos = focus_pos
        row_offset += focus_rows
        # include widgets from calculate_visible(..)
        for widget, pos, rows in fill_below:
            t.append( (row_offset, widget, pos, rows) )
            row_offset += rows
        # add newly visible ones, including within snap_rows
        snap_region_start = len(t)
        while row_offset < maxrow+snap_rows:
            widget, pos = self.body.get_next(pos)
            if widget is None: break
            rows = widget.rows((maxcol,))
            t.append( (row_offset, widget, pos, rows) ) 
            row_offset += rows
            # determine if one above puts current one into snap rgn
            if row_offset < maxrow:
                snap_region_start += 1
        
        # if we can't fill the bottom we need to adjust the row offsets
        row_offset, w, p, rows = t[-1]
        if row_offset + rows < maxrow:
            adjust = maxrow - (row_offset + rows)
            t = [(ro+adjust, w, p, r) for (ro,w,p,r) in t]    

        # if focus_widget (first in t) is off edge, remove it
        row_offset, w, p, rows = t[0]
        if row_offset+rows <= 0:
            del t[0]
            snap_region_start -= 1

        # we'll need this soon
        self.update_pref_col_from_focus((maxcol,maxrow))
            
        # choose the bottommost selectable and (newly) visible widget
        # search within snap_rows then visible region
        search_order = ( range( snap_region_start, len(t))
                + range( snap_region_start-1, -1, -1 ) )
        #assert 0, `t, search_order`
        bad_choices = []
        cut_off_selectable_chosen = 0
        for i in search_order:
            row_offset, widget, pos, rows = t[i]
            if not widget.selectable(): 
                continue

            # try selecting this widget
            pref_row = min(maxrow-row_offset-1, rows-1)
            
            # if completely within snap region, adjust row_offset
            if row_offset >= maxrow:
                self.change_focus( (maxcol,maxrow), pos,
                    maxrow-1, 'above',
                    (self.pref_col, 0),
                    snap_rows+maxrow-row_offset-1 )
            else:
                self.change_focus( (maxcol,maxrow), pos,
                    row_offset, 'above', 
                    (self.pref_col, pref_row), snap_rows )
            
            # find out where that actually puts us
            middle, top, bottom = self.calculate_visible(
                (maxcol,maxrow), True)
            act_row_offset, _ign1, _ign2, _ign3, _ign4 = middle

            # discard chosen widget if it will reduce scroll amount
            # because of a fixed cursor (absolute last resort)
            if act_row_offset < row_offset-snap_rows:
                bad_choices.append(i)
                continue
            if act_row_offset > row_offset:
                bad_choices.append(i)
                continue
            
            # also discard if off top edge (second last resort)
            if act_row_offset+rows > maxrow:
                bad_choices.append(i)
                cut_off_selectable_chosen = 1
                continue
            
            return
            
        # anything selectable is better than what follows:
        if cut_off_selectable_chosen:
            return

        # if still none found choose the bottommost widget
        good_choices = [j for j in search_order if j not in bad_choices]
        for i in good_choices + search_order:
            row_offset, widget, pos, rows = t[i]
            if pos == focus_pos: continue
            
            # if completely within snap region, adjust row_offset
            if row_offset >= maxrow:
                snap_rows -= snap_rows+maxrow-row_offset-1
                row_offset = maxrow-1
                
            self.change_focus( (maxcol,maxrow), pos,
                row_offset, 'above', None,
                snap_rows )
            return
        
            
        # no choices available, just shift current one
        self.shift_focus((maxcol, maxrow), max(1-focus_rows,row_offset))
        
        # final check for pathological case where we may fall short
        middle, top, bottom = self.calculate_visible(
            (maxcol,maxrow), True)
        act_row_offset, _ign1, pos, _ign2, _ign3 = middle
        if act_row_offset <= row_offset:
            # no problem
            return
            
        # fell short, try to select anything else below
        if not t:
            return
        _ign1, _ign2, pos, _ign3 = t[-1]
        widget, pos = self.body.get_next(pos)
        if widget is None:
            # no dice, we're stuck here
            return
        # bring in only one row if possible
        rows = widget.rows((maxcol,), True)
        self.change_focus((maxcol,maxrow), pos, maxrow-1,
            'above', (self.pref_col, 0), 0 )

    def mouse_event(self, size, event, button, col, row, focus):
        """
        Pass the event to the contained widgets.
        May change focus on button 1 press.
        """
        (maxcol, maxrow) = size
        middle, top, bottom = self.calculate_visible((maxcol, maxrow),
            focus=True)
        if middle is None:
            return False
        
        _ignore, focus_widget, focus_pos, focus_rows, cursor = middle
        trim_top, fill_above = top
        _ignore, fill_below = bottom

        fill_above.reverse() # fill_above is in bottom-up order
        w_list = ( fill_above + 
            [ (focus_widget, focus_pos, focus_rows) ] +
            fill_below )

        wrow = -trim_top
        for w, w_pos, w_rows in w_list:
            if wrow + w_rows > row:
                break
            wrow += w_rows
        else:
            return False

        focus = focus and w == focus_widget
        if is_mouse_press(event) and button==1:
            if w.selectable():
                self.change_focus((maxcol,maxrow), w_pos, wrow)
        
        if not hasattr(w,'mouse_event'):
            return False

        return w.mouse_event((maxcol,), event, button, col, row-wrow,
            focus)


    def ends_visible(self, size, focus=False):
        """Return a list that may contain 'top' and/or 'bottom'.
        
        convenience function for checking whether the top and bottom
        of the list are visible
        """
        (maxcol, maxrow) = size
        l = []
        middle,top,bottom = self.calculate_visible( (maxcol,maxrow), 
            focus=focus )
        if middle is None: # empty listbox
            return ['top','bottom']
        trim_top, above = top
        trim_bottom, below = bottom

        if trim_bottom == 0:
            row_offset, w, pos, rows, c = middle
            row_offset += rows
            for w, pos, rows in below:
                row_offset += rows
            if row_offset < maxrow:
                l.append( 'bottom' )
            elif self.body.get_next(pos) == (None,None):
                l.append( 'bottom' )

        if trim_top == 0:
            row_offset, w, pos, rows, c = middle
            for w, pos, rows in above:
                row_offset -= rows
            if self.body.get_prev(pos) == (None,None):
                l.append( 'top' )

        return l



########NEW FILE########
__FILENAME__ = main_loop
#!/usr/bin/python
#
# Urwid main loop code
#    Copyright (C) 2004-2009  Ian Ward
#    Copyright (C) 2008 Walter Mundt
#    Copyright (C) 2009 Andrew Psaltis
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


import time
import heapq
import select

from util import *
from command_map import command_map


class ExitMainLoop(Exception):
    pass

class MainLoop(object):
    def __init__(self, widget, palette=[], screen=None, 
        handle_mouse=True, input_filter=None, unhandled_input=None,
        event_loop=None):
        """
        Simple main loop implementation.

        widget -- topmost widget used for painting the screen, 
            stored as self.widget, may be modified
        palette -- initial palette for screen
        screen -- screen object or None to use raw_display.Screen,
            stored as self.screen
        handle_mouse -- True to process mouse events, passed to
            self.screen
        input_filter -- a function to filter input before sending
            it to self.widget, called from self.input_filter
        unhandled_input -- a function called when input is not
            handled by self.widget, called from self.unhandled_input
        event_loop -- if screen supports external an event loop it
            may be given here, or leave as None to use 
            SelectEventLoop, stored as self.event_loop

        This is a standard main loop implementation with a single
        screen. 
        
        The widget passed must be a box widget.

        raw_display.Screen is the only screen type that currently
        supports external event loops.  Other screen types include
        curses_display.Screen, web_display.Screen and
        html_fragment.HtmlGenerator.
        """
        self.widget = widget
        self.handle_mouse = handle_mouse
        
        if not screen:
            import raw_display
            screen = raw_display.Screen()

        if palette:
            screen.register_palette(palette)

        self.screen = screen
        self.screen_size = None

        self._unhandled_input = unhandled_input
        self._input_filter = input_filter

        if not hasattr(screen, 'get_input_descriptors'
                ) and event_loop is not None:
            raise NotImplementedError("screen object passed "
                "%r does not support external event loops" % (screen,))
        if event_loop is None:
            event_loop = SelectEventLoop()
        self.event_loop = event_loop

        self._input_timeout = None


    def set_alarm_in(self, sec, callback, user_data=None):
        """
        Schedule an alarm in sec seconds that will call
        callback(main_loop, user_data) from the within the run()
        function.

        sec -- floating point seconds until alarm
        callback -- callback(main_loop, user_data) callback function
        user_data -- object to pass to callback
        """
        def cb():
            callback(self, user_data)
            self.draw_screen()
        return self.event_loop.alarm(sec, cb)

    def set_alarm_at(self, tm, callback, user_data=None):
        """
        Schedule at tm time that will call 
        callback(main_loop, user_data) from the within the run()
        function.

        Returns a handle that may be passed to remove_alarm()

        tm -- floating point local time of alarm
        callback -- callback(main_loop, user_data) callback function
        user_data -- object to pass to callback
        """
        def cb():
            callback(self, user_data)
            self.draw_screen()
        return self.event_loop.alarm(tm - time.time(), cb)

    def remove_alarm(self, handle):
        """
        Remove an alarm. 
        
        Return True if the handle was found, False otherwise.
        """
        return self.event_loop.remove_alarm(handle)


    
    def run(self):
        """
        Start the main loop handling input events and updating 
        the screen.  The loop will continue until an ExitMainLoop 
        exception is raised.  
        
        This function will call screen.run_wrapper() if screen.start() 
        has not already been called.

        >>> w = _refl("widget")   # _refl prints out function calls
        >>> w.render_rval = "fake canvas"  # *_rval is used for return values
        >>> scr = _refl("screen")
        >>> scr.get_input_descriptors_rval = [42]
        >>> scr.get_cols_rows_rval = (20, 10)
        >>> scr.started = True
        >>> evl = _refl("event_loop")
        >>> ml = MainLoop(w, [], scr, event_loop=evl)
        >>> ml.run()    # doctest:+ELLIPSIS
        screen.set_mouse_tracking()
        screen.get_cols_rows()
        widget.render((20, 10), focus=True)
        screen.draw_screen((20, 10), 'fake canvas')
        screen.get_input_descriptors()
        event_loop.watch_file(42, <bound method ...>)
        event_loop.run()
        >>> scr.started = False
        >>> ml.run()    # doctest:+ELLIPSIS
        screen.run_wrapper(<bound method ...>)
        """
        try:
            if self.screen.started:
                self._run()
            else:
                self.screen.run_wrapper(self._run)
        except ExitMainLoop:
            pass
    
    def _run(self):
        if self.handle_mouse:
            self.screen.set_mouse_tracking()

        if not hasattr(self.screen, 'get_input_descriptors'):
            return self._run_screen_event_loop()

        self.draw_screen()

        # insert our input descriptors
        fds = self.screen.get_input_descriptors()
        for fd in fds:
            self.event_loop.watch_file(fd, self._update)

        self.event_loop.run()

    def _update(self, timeout=False):
        """
        >>> w = _refl("widget")
        >>> w.render_rval = "fake canvas"
        >>> w.selectable_rval = True
        >>> scr = _refl("screen")
        >>> scr.get_cols_rows_rval = (15, 5)
        >>> scr.get_input_nonblocking_rval = 1, ['y'], [121]
        >>> evl = _refl("event_loop")
        >>> ml = MainLoop(w, [], scr, event_loop=evl)
        >>> ml._input_timeout = "old timeout"
        >>> ml._update()    # doctest:+ELLIPSIS
        event_loop.remove_alarm('old timeout')
        screen.get_input_nonblocking()
        event_loop.alarm(1, <function ...>)
        screen.get_cols_rows()
        widget.selectable()
        widget.keypress((15, 5), 'y')
        widget.render((15, 5), focus=True)
        screen.draw_screen((15, 5), 'fake canvas')
        >>> scr.get_input_nonblocking_rval = None, [("mouse press", 1, 5, 4)
        ... ], []
        >>> ml._update()
        screen.get_input_nonblocking()
        widget.mouse_event((15, 5), 'mouse press', 1, 5, 4, focus=True)
        widget.render((15, 5), focus=True)
        screen.draw_screen((15, 5), 'fake canvas')
        """
        if self._input_timeout is not None and not timeout:
            # cancel the timeout, something else triggered the update
            self.event_loop.remove_alarm(self._input_timeout)
        self._input_timeout = None

        max_wait, keys, raw = self.screen.get_input_nonblocking()
        
        if max_wait is not None:
            # if get_input_nonblocking wants to be called back
            # make sure it happens with an alarm
            self._input_timeout = self.event_loop.alarm(max_wait, 
                lambda: self._update(timeout=True)) 

        keys = self.input_filter(keys, raw)

        if keys:
            self.process_input(keys)
            if 'window resize' in keys:
                self.screen_size = None

        self.draw_screen()

    def _run_screen_event_loop(self):
        """
        This method is used when the screen does not support using
        external event loops.

        The alarms stored in the SelectEventLoop in self.event_loop 
        are modified by this method.
        """
        next_alarm = None

        while True:
            self.draw_screen()

            if not next_alarm and self.event_loop._alarms:
                next_alarm = heapq.heappop(self.event_loop._alarms)

            keys = None
            while not keys:
                if next_alarm:
                    sec = max(0, next_alarm[0] - time.time())
                    self.screen.set_input_timeouts(sec)
                else:
                    self.screen.set_input_timeouts(None)
                keys, raw = self.screen.get_input(True)
                if not keys and next_alarm: 
                    sec = next_alarm[0] - time.time()
                    if sec <= 0:
                        break

            keys = self.input_filter(keys, raw)
            
            if keys:
                self.process_input(keys)
            
            while next_alarm:
                sec = next_alarm[0] - time.time()
                if sec > 0:
                    break
                tm, callback, user_data = next_alarm
                callback(self, user_data)
                
                if self._alarms:
                    next_alarm = heapq.heappop(self.event_loop._alarms)
                else:
                    next_alarm = None
            
            if 'window resize' in keys:
                self.screen_size = None

    def process_input(self, keys):
        """
        This function will pass keyboard input and mouse events
        to self.widget.  This function is called automatically
        from the run() method when there is input, but may also be
        called to simulate input from the user.

        keys -- list of input returned from self.screen.get_input()
        
        >>> w = _refl("widget")
        >>> w.selectable_rval = True
        >>> scr = _refl("screen")
        >>> scr.get_cols_rows_rval = (10, 5)
        >>> ml = MainLoop(w, [], scr)
        >>> ml.process_input(['enter', ('mouse drag', 1, 14, 20)])
        screen.get_cols_rows()
        widget.selectable()
        widget.keypress((10, 5), 'enter')
        widget.mouse_event((10, 5), 'mouse drag', 1, 14, 20, focus=True)
        """
        if not self.screen_size:
            self.screen_size = self.screen.get_cols_rows()

        for k in keys:
            if is_mouse_event(k):
                event, button, col, row = k
                if self.widget.mouse_event(self.screen_size, 
                    event, button, col, row, focus=True ):
                    k = None
            elif self.widget.selectable():
                k = self.widget.keypress(self.screen_size, k)
            if k and command_map[k] == 'redraw screen':
                self.screen.clear()
            elif k:
                self.unhandled_input(k)

    def input_filter(self, keys, raw):
        """
        This function is passed each all the input events and raw
        keystroke values.  These values are passed to the
        input_filter function passed to the constructor.  That
        function must return a list of keys to be passed to the
        widgets to handle.  If no input_filter was defined this
        implementation will return all the input events.

        input -- keyboard or mouse input
        """
        if self._input_filter:
            return self._input_filter(keys, raw)
        return keys

    def unhandled_input(self, input):
        """
        This function is called with any input that was not handled
        by the widgets, and calls the unhandled_input function passed
        to the constructor.  If no unhandled_input was defined then
        the input will be ignored.

        input -- keyboard or mouse input
        """
        if self._unhandled_input:
            return self._unhandled_input(input)

    def draw_screen(self):
        """
        Renter the widgets and paint the screen.  This function is
        called automatically from run() but may be called additional 
        times if repainting is required without also processing input.
        """
        if not self.screen_size:
            self.screen_size = self.screen.get_cols_rows()

        canvas = self.widget.render(self.screen_size, focus=True)
        self.screen.draw_screen(self.screen_size, canvas)



        


class SelectEventLoop(object):
    def __init__(self):
        """
        Event loop based on select.select()

        >>> import os
        >>> rd, wr = os.pipe()
        >>> evl = SelectEventLoop()
        >>> def step1():
        ...     print "writing"
        ...     os.write(wr, "hi")
        >>> def step2():
        ...     print os.read(rd, 2)
        ...     raise ExitMainLoop
        >>> handle = evl.alarm(0, step1)
        >>> handle = evl.watch_file(rd, step2)
        >>> evl.run()
        writing
        hi
        """
        self._alarms = []
        self._watch_files = {}

    def alarm(self, seconds, callback):
        """
        Call callback() given time from from now.  No parameters are
        passed to callback.

        Returns a handle that may be passed to remove_alarm()

        seconds -- floating point time to wait before calling callback
        callback -- function to call from event loop
        """ 
        tm = time.time() + seconds
        heapq.heappush(self._alarms, (tm, callback))
        return (tm, callback)

    def remove_alarm(self, handle):
        """
        Remove an alarm.

        Returns True if the alarm exists, False otherwise

        >>> evl = SelectEventLoop()
        >>> handle = evl.alarm(50, lambda: None)
        >>> evl.remove_alarm(handle)
        True
        >>> evl.remove_alarm(handle)
        False
        """
        try:
            self._alarms.remove(handle)
            heapq.heapify(self._alarms)
            return True
        except ValueError:
            return False

    def watch_file(self, fd, callback):
        """
        Call callback() when fd has some data to read.  No parameters
        are passed to callback.

        Returns a handle that may be passed to remove_watch_file()

        fd -- file descriptor to watch for input
        callback -- function to call when input is available
        """
        self._watch_files[fd] = callback
        return fd

    def remove_watch_file(self, handle):
        """
        Remove an input file.

        Returns True if the input file exists, False otherwise

        >>> evl = SelectEventLoop()
        >>> handle = evl.watch_file(5, lambda: None)
        >>> evl.remove_watch_file(handle)
        True
        >>> evl.remove_watch_file(handle)
        False
        """
        if handle in self._watch_files:
            del self._watch_files[handle]
            return True
        return False

    def run(self):
        """
        Start the event loop.  Exit the loop when any callback raises
        an exception.  If ExitMainLoop is raised, exit cleanly.

        >>> import os
        >>> rd, wr = os.pipe()
        >>> os.write(wr, "data") # something to read from rd
        4
        >>> evl = SelectEventLoop()
        >>> def say_hello():
        ...     print "hello"
        >>> def exit_clean():
        ...     print "clean exit"
        ...     raise ExitMainLoop
        >>> def exit_error():
        ...     1/0
        >>> handle = evl.alarm(0.0625, exit_clean)
        >>> handle = evl.alarm(0, say_hello)
        >>> evl.run()
        hello
        clean exit
        >>> handle = evl.watch_file(rd, exit_clean)
        >>> evl.run()
        clean exit
        >>> evl.remove_watch_file(handle)
        True
        >>> handle = evl.alarm(0, exit_error)
        >>> evl.run()
        Traceback (most recent call last):
           ...
        ZeroDivisionError: integer division or modulo by zero
        >>> handle = evl.watch_file(rd, exit_error)
        >>> evl.run()
        Traceback (most recent call last):
           ...
        ZeroDivisionError: integer division or modulo by zero
        """
        try:
            while True:
                try:
                    self._loop()
                except select.error, e:
                    if e.args[0] != 4:
                        # not just something we need to retry
                        raise
        except ExitMainLoop:
            pass
        

    def _loop(self):
        fds = self._watch_files.keys()
        if self._alarms:
            tm = self._alarms[0][0]
            timeout = max(0, tm - time.time())
            ready, w, err = select.select(fds, [], fds, timeout)
        else:
            tm = None
            ready, w, err = select.select(fds, [], fds)

        if not ready and tm is not None:
            # must have been a timeout
            tm, alarm_callback = self._alarms.pop(0)
            alarm_callback()

        for fd in ready:
            self._watch_files[fd]()


class GLibEventLoop(object):
    def __init__(self):
        """
        Event loop based on gobject.MainLoop

        >>> import os
        >>> rd, wr = os.pipe()
        >>> evl = GLibEventLoop()
        >>> def step1():
        ...     print "writing"
        ...     os.write(wr, "hi")
        >>> def step2():
        ...     print os.read(rd, 2)
        ...     raise ExitMainLoop
        >>> handle = evl.alarm(0, step1)
        >>> handle = evl.watch_file(rd, step2)
        >>> evl.run()
        writing
        hi
        """
        import gobject
        self.gobject = gobject
        self._alarms = []
        self._watch_files = {}
        self._loop = self.gobject.MainLoop()
        self._exc_info = None

    def alarm(self, seconds, callback):
        """
        Call callback() given time from from now.  No parameters are
        passed to callback.

        Returns a handle that may be passed to remove_alarm()

        seconds -- floating point time to wait before calling callback
        callback -- function to call from event loop
        """
        @self.handle_exit
        def ret_false():
            callback()
            return False
        fd = self.gobject.timeout_add(int(seconds*1000), ret_false)
        self._alarms.append(fd)
        return (fd, callback)

    def remove_alarm(self, handle):
        """
        Remove an alarm.

        Returns True if the alarm exists, False otherwise

        >>> evl = GLibEventLoop()
        >>> handle = evl.alarm(50, lambda: None)
        >>> evl.remove_alarm(handle)
        True
        >>> evl.remove_alarm(handle)
        False
        """
        try:
            self._alarms.remove(handle[0])
            self.gobject.source_remove(handle[0])
            return True
        except ValueError:
            return False

    def watch_file(self, fd, callback):
        """
        Call callback() when fd has some data to read.  No parameters
        are passed to callback.

        Returns a handle that may be passed to remove_watch_file()

        fd -- file descriptor to watch for input
        callback -- function to call when input is available
        """
        @self.handle_exit
        def io_callback(source, cb_condition):
            callback()
            return True
        self._watch_files[fd] = \
             self.gobject.io_add_watch(fd,self.gobject.IO_IN,io_callback)
        return fd

    def remove_watch_file(self, handle):
        """
        Remove an input file.

        Returns True if the input file exists, False otherwise

        >>> evl = GLibEventLoop()
        >>> handle = evl.watch_file(1, lambda: None)
        >>> evl.remove_watch_file(handle)
        True
        >>> evl.remove_watch_file(handle)
        False
        """
        if handle in self._watch_files:
            self.gobject.source_remove(self._watch_files[handle])
            del self._watch_files[handle]
            return True
        return False

    def run(self):
        """
        Start the event loop.  Exit the loop when any callback raises
        an exception.  If ExitMainLoop is raised, exit cleanly.
        
        >>> import os
        >>> rd, wr = os.pipe()
        >>> os.write(wr, "data") # something to read from rd
        4
        >>> evl = GLibEventLoop()
        >>> def say_hello():
        ...     print "hello"
        >>> def exit_clean():
        ...     print "clean exit"
        ...     raise ExitMainLoop
        >>> def exit_error():
        ...     1/0
        >>> handle = evl.alarm(0.0625, exit_clean)
        >>> handle = evl.alarm(0, say_hello)
        >>> evl.run()
        hello
        clean exit
        >>> handle = evl.watch_file(rd, exit_clean)
        >>> evl.run()
        clean exit
        >>> evl.remove_watch_file(handle)
        True
        >>> handle = evl.alarm(0, exit_error)
        >>> evl.run()
        Traceback (most recent call last):
           ...
        ZeroDivisionError: integer division or modulo by zero
        >>> handle = evl.watch_file(rd, exit_error)
        >>> evl.run()
        Traceback (most recent call last):
           ...
        ZeroDivisionError: integer division or modulo by zero
        """
        context = self._loop.get_context()
        try:
            self._loop.run()
        finally:
            if self._loop.is_running():
                self._loop.quit()
        if self._exc_info:
            # An exception caused us to exit, raise it now
            exc_info = self._exc_info
            self._exc_info = None
            raise exc_info[0], exc_info[1], exc_info[2]

    def handle_exit(self,f):
        """
        Decorator that cleanly exits the GLibEventLoop if ExitMainLoop is
        thrown inside of the wrapped function.  Store the exception info if 
        some other exception occurs, it will be reraised after the loop quits.
        f -- function to be wrapped

        """
        def wrapper(*args,**kargs):
            try:
                return f(*args,**kargs)
            except ExitMainLoop:
                self._loop.quit()
            except:
                import sys
                self._exc_info = sys.exc_info()
                if self._loop.is_running():
                    self._loop.quit()
            return False
        return wrapper


try:
    from twisted.internet.abstract import FileDescriptor
except:
    FileDescriptor = object

class TwistedInputDescriptor(FileDescriptor):
    def __init__(self, reactor, fd, cb):
        self._fileno = fd
        self.cb = cb
        FileDescriptor.__init__(self, reactor)

    def fileno(self):
        return self._fileno

    def doRead(self):
        return self.cb()



class TwistedEventLoop(object):
    def __init__(self, reactor=None):
        """
        Event loop based on Twisted

        >>> import os
        >>> rd, wr = os.pipe()
        >>> evl = TwistedEventLoop()
        >>> def step1():
        ...     print "writing"
        ...     os.write(wr, "hi")
        >>> def step2():
        ...     print os.read(rd, 2)
        ...     raise ExitMainLoop
        >>> handle = evl.alarm(0, step1)
        >>> handle = evl.watch_file(rd, step2)
        >>> evl.run()
        writing
        hi
        """
        if reactor is None:
            import twisted.internet.reactor
            reactor = twisted.internet.reactor
        self.reactor = reactor
        self._alarms = []
        self._watch_files = {}
        self._exc_info = None

    def alarm(self, seconds, callback):
        """
        Call callback() given time from from now.  No parameters are
        passed to callback.

        Returns a handle that may be passed to remove_alarm()

        seconds -- floating point time to wait before calling callback
        callback -- function to call from event loop
        """
        handle = self.reactor.callLater(seconds, self.handle_exit(callback))
        return handle

    def remove_alarm(self, handle):
        """
        Remove an alarm.

        Returns True if the alarm exists, False otherwise

        >>> evl = TwistedEventLoop()
        >>> handle = evl.alarm(50, lambda: None)
        >>> evl.remove_alarm(handle)
        True
        >>> evl.remove_alarm(handle)
        False
        """
        from twisted.internet.error import AlreadyCancelled, AlreadyCalled
        try:
            handle.cancel()
            return True
        except AlreadyCancelled:
            return False
        except AlreadyCalled:
            return False

    def watch_file(self, fd, callback):
        """
        Call callback() when fd has some data to read.  No parameters
        are passed to callback.

        Returns a handle that may be passed to remove_watch_file()

        fd -- file descriptor to watch for input
        callback -- function to call when input is available
        """
        ind = TwistedInputDescriptor(self.reactor, fd,
            self.handle_exit(callback))
        self._watch_files[fd] = ind
        self.reactor.addReader(ind)
        return fd

    def remove_watch_file(self, handle):
        """
        Remove an input file.

        Returns True if the input file exists, False otherwise

        >>> evl = TwistedEventLoop()
        >>> handle = evl.watch_file(1, lambda: None)
        >>> evl.remove_watch_file(handle)
        True
        >>> evl.remove_watch_file(handle)
        False
        """
        if handle in self._watch_files:
            self.reactor.removeReader(self._watch_files[handle])
            del self._watch_files[handle]
            return True
        return False

    def run(self):
        """
        Start the event loop.  Exit the loop when any callback raises
        an exception.  If ExitMainLoop is raised, exit cleanly.
        
        >>> import os
        >>> rd, wr = os.pipe()
        >>> os.write(wr, "data") # something to read from rd
        4
        >>> evl = TwistedEventLoop()
        >>> def say_hello():
        ...     print "hello"
        >>> def exit_clean():
        ...     print "clean exit"
        ...     raise ExitMainLoop
        >>> def exit_error():
        ...     1/0
        >>> handle = evl.alarm(0.0625, exit_clean)
        >>> handle = evl.alarm(0, say_hello)
        >>> evl.run()
        hello
        clean exit
        >>> handle = evl.watch_file(rd, exit_clean)
        >>> evl.run()
        clean exit
        >>> evl.remove_watch_file(handle)
        True
        >>> handle = evl.alarm(0, exit_error)
        >>> evl.run()
        Traceback (most recent call last):
           ...
        ZeroDivisionError: integer division or modulo by zero
        >>> handle = evl.watch_file(rd, exit_error)
        >>> evl.run()
        Traceback (most recent call last):
           ...
        ZeroDivisionError: integer division or modulo by zero
        """
        self.reactor.run()
        if self._exc_info:
            # An exception caused us to exit, raise it now
            exc_info = self._exc_info
            self._exc_info = None
            raise exc_info[0], exc_info[1], exc_info[2]

    def handle_exit(self,f):
        """
        Decorator that cleanly exits the TwistedEventLoop if ExitMainLoop is
        thrown inside of the wrapped function.  Store the exception info if 
        some other exception occurs, it will be reraised after the loop quits.
        f -- function to be wrapped

        """
        def wrapper(*args,**kargs):
            try:
                return f(*args,**kargs)
            except ExitMainLoop:
                self.reactor.crash()
            except:
                import sys
                print sys.exc_info()
                self._exc_info = sys.exc_info()
                self.reactor.crash()
        return wrapper
    


def _refl(name, rval=None, exit=False):
    """
    This function is used to test the main loop classes.

    >>> scr = _refl("screen")
    >>> scr.function("argument")
    screen.function('argument')
    >>> scr.callme(when="now")
    screen.callme(when='now')
    >>> scr.want_something_rval = 42
    >>> x = scr.want_something()
    screen.want_something()
    >>> x
    42
    """
    class Reflect(object):
        def __init__(self, name, rval=None):
            self._name = name
            self._rval = rval
        def __call__(self, *argl, **argd):
            args = ", ".join([repr(a) for a in argl])
            if args and argd:
                args = args + ", "
            args = args + ", ".join([k+"="+repr(v) for k,v in argd.items()])
            print self._name+"("+args+")"
            if exit: 
                raise ExitMainLoop()
            return self._rval
        def __getattr__(self, attr):
            if attr.endswith("_rval"):
                raise AttributeError()
            #print self._name+"."+attr
            if hasattr(self, attr+"_rval"):
                return Reflect(self._name+"."+attr, getattr(self, attr+"_rval"))
            return Reflect(self._name+"."+attr)
    return Reflect(name)

def _test():
    import doctest
    doctest.testmod()

if __name__=='__main__':
    _test()

########NEW FILE########
__FILENAME__ = monitored_list
#!/usr/bin/python
#
# Urwid MonitoredList class
#    Copyright (C) 2004-2009  Ian Ward
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



def _call_modified(fn):
    def call_modified_wrapper(self, *args, **kwargs):
        rval = fn(self, *args, **kwargs)
        self._modified()
        return rval
    return call_modified_wrapper

class MonitoredList(list):
    """
    This class can trigger a callback any time its contents are changed
    with the usual list operations append, extend, etc.
    """
    def _modified(self):
        pass
    
    def set_modified_callback(self, callback):
        """
        Assign a callback function in with no parameters.
        Callback's return value is ignored.

        >>> import sys
        >>> ml = MonitoredList([1,2,3])
        >>> ml.set_modified_callback(lambda: sys.stdout.write("modified\\n"))
        >>> ml
        MonitoredList([1, 2, 3])
        >>> ml.append(10)
        modified
        >>> len(ml)
        4
        >>> ml += [11, 12, 13]
        modified
        >>> ml[:] = ml[:2] + ml[-2:]
        modified
        >>> ml
        MonitoredList([1, 2, 12, 13])
        """
        self._modified = callback

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, list(self))

    __add__ = _call_modified(list.__add__)
    __delitem__ = _call_modified(list.__delitem__)
    __delslice__ = _call_modified(list.__delslice__)
    __iadd__ = _call_modified(list.__iadd__)
    __imul__ = _call_modified(list.__imul__)
    __rmul__ = _call_modified(list.__rmul__)
    __setitem__ = _call_modified(list.__setitem__)
    __setslice__ = _call_modified(list.__setslice__)
    append = _call_modified(list.append)
    extend = _call_modified(list.extend)
    insert = _call_modified(list.insert)
    pop = _call_modified(list.pop)
    remove = _call_modified(list.remove)
    reverse = _call_modified(list.reverse)
    sort = _call_modified(list.sort)


class MonitoredFocusList(MonitoredList):
    """
    This class can trigger a callback any time its contents are changed
    and any time the item "in focus" is modified or removed
    """
    def __init__(self, *argl, **argd):
        """
        This is a list that tracks one item as the focus item.  If items
        are inserted or removed it will update the focus.

        >>> ml = MonitoredFocusList([10, 11, 12, 13, 14], focus=3)
        >>> ml
        MonitoredFocusList([10, 11, 12, 13, 14], focus=3)
        >>> del(ml[1])
        >>> ml
        MonitoredFocusList([10, 12, 13, 14], focus=2)
        >>> ml[:2] = [50, 51, 52, 53]
        >>> ml
        MonitoredFocusList([50, 51, 52, 53, 13, 14], focus=4)
        >>> ml[4] = 99
        >>> ml
        MonitoredFocusList([50, 51, 52, 53, 99, 14], focus=4)
        >>> ml[:] = []
        >>> ml
        MonitoredFocusList([], focus=None)
        """
        focus = 0
        if 'focus' in argd:
            focus = argd['focus']
            del argd['focus']

        super(MonitoredFocusList, self).__init__(*argl, **argd)

        self.set_focus(focus)
        self._focus_modified = lambda ml, indices, new_items: None

    def __repr__(self):
        return "%s(%r, focus=%r)" % (
            self.__class__.__name__, list(self), self.get_focus())

    def get_focus(self):
        """
        Return the index of the item "in focus" or None if
        the list is empty.  May also be accessed as .focus

        >>> MonitoredFocusList([1,2,3], focus=2).get_focus()
        2
        >>> MonitoredFocusList().get_focus()
        >>> MonitoredFocusList([1,2,3], focus=1).focus
        1
        """
        if not self:
            return None
        if self._focus >= len(self):
            # should't happen.. but just in case
            return len(self)-1
        return self._focus

    def set_focus(self, index):
        """
        index -- index into self.widget_list, negative indexes count from
            the end, any index out of range will raise an IndexError
        
        Negative indexes work the same way they do in slicing.

        May also be set using .focus
        
        >>> ml = MonitoredFocusList([9, 10, 11])
        >>> ml.set_focus(2); ml.get_focus()
        2
        >>> ml.set_focus(-2); ml.get_focus()
        1
        >>> ml.focus = 0; ml.get_focus()
        0
        """
        if not self:
            self._focus = 0
            return
        if index < 0:
            index += len(self)
        if index < 0 or index >= len(self):
            raise IndexError('list index out of range')
        self._focus = int(index)

    focus = property(get_focus, set_focus)

    def set_focus_modified_callback(self, callback):
        """
        Assign a function to handle updating the focus when the item
        in focus is about to be changed.  The callback is in the form:

        callback(monitored_list, slc, new_items)
        indices -- a (start, stop, step) tuple whose range covers the 
            items being modified
        new_items -- a list of items replacing those at range(*indices)
        
        The only valid action for the callback is to call set_focus().
        Modifying the list in the callback has undefined behaviour.
        """
        self._focus_modified = callback

    def _handle_possible_focus_modified(self, slc, new_items=[]):
        """
        Default behaviour is to move the focus to the item following
        any removed items, or the last item in the list if that doesn't
        exist.
        """
        num_new_items = len(new_items)
        start, stop, step = indices = slc.indices(len(self))
        if step == 1:
            if start <= self._focus < stop:
                # call user handler, which might modify focus
                self._focus_modified(self, indices, new_items)

            if start + num_new_items <= self._focus < stop:
                self._focus = stop
            # adjust for added/removed items
            if stop <= self._focus:
                self._focus += num_new_items - (stop - start)

        else:
            removed = range(start, stop, step)
            if self._focus in removed:
                # call user handler, which might modify focus
                self._focus_modified(self, indices, new_items)

            if not num_new_items:
                # extended slice being removed
                if self._focus in removed:
                    self._focus += 1

                # adjust for removed items
                self._focus -= len(range(start, self._focus, step))

    def _clamp_focus(self):
        """
        adjust the focus if it is out of range
        """
        if self._focus >= len(self):
            self._focus = len(self)-1
        if self._focus < 0:
            self._focus = 0

    # override all the list methods that might affect our focus
    
    def __delitem__(self, y):
        """
        >>> ml = MonitoredFocusList([0,1,2,3], focus=2)
        >>> del ml[3]; ml
        MonitoredFocusList([0, 1, 2], focus=2)
        >>> del ml[0]; ml
        MonitoredFocusList([1, 2], focus=1)
        >>> del ml[1]; ml
        MonitoredFocusList([1], focus=0)
        >>> del ml[0]; ml
        MonitoredFocusList([], focus=None)
        >>> ml = MonitoredFocusList([5,4,6,4,5,4,6,4,5], focus=4)
        >>> del ml[1::2]; ml
        MonitoredFocusList([5, 6, 5, 6, 5], focus=2)
        >>> del ml[::2]; ml
        MonitoredFocusList([6, 6], focus=1)
        """
        if isinstance(y, slice):
            self._handle_possible_focus_modified(y)
        else:
            self._handle_possible_focus_modified(slice(y, y+1))
        rval = super(MonitoredFocusList, self).__delitem__(y)
        self._clamp_focus()
        return rval

    def __setitem__(self, i, y):
        """
        >>> def modified(monitored_list, indices, new_items):
        ...     print "range%r <- %r" % (indices, new_items)
        >>> ml = MonitoredFocusList([0,1,2,3], focus=2)
        >>> ml.set_focus_modified_callback(modified)
        >>> ml[0] = 9
        >>> ml[2] = 6
        range(2, 3, 1) <- [6]
        >>> ml[-1] = 8; ml
        MonitoredFocusList([9, 1, 6, 8], focus=2)
        >>> ml[1::2] = [12, 13]
        >>> ml[::2] = [10, 11]
        range(0, 4, 2) <- [10, 11]
        """
        if isinstance(i, slice):
            self._handle_possible_focus_modified(i, y)
        else:
            self._handle_possible_focus_modified(slice(i, i+1 or None), [y])
        return super(MonitoredFocusList, self).__setitem__(i, y)

    def __delslice__(self, i, j):
        """
        >>> def modified(monitored_list, indices, new_items):
        ...     print "range%r <- %r" % (indices, new_items)
        >>> ml = MonitoredFocusList([0,1,2,3,4], focus=2)
        >>> ml.set_focus_modified_callback(modified)
        >>> del ml[3:5]; ml
        MonitoredFocusList([0, 1, 2], focus=2)
        >>> del ml[:1]; ml
        MonitoredFocusList([1, 2], focus=1)
        >>> del ml[1:]; ml
        range(1, 2, 1) <- []
        MonitoredFocusList([1], focus=0)
        >>> del ml[:]; ml
        range(0, 1, 1) <- []
        MonitoredFocusList([], focus=None)
        """
        self._handle_possible_focus_modified(slice(i, j))
        rval = super(MonitoredFocusList, self).__delslice__(i, j)
        self._clamp_focus()
        return rval

    def __setslice__(self, i, j, y):
        """
        >>> ml = MonitoredFocusList([0,1,2,3,4], focus=2)
        >>> ml[3:5] = [-1]; ml
        MonitoredFocusList([0, 1, 2, -1], focus=2)
        >>> ml[0:1] = []; ml
        MonitoredFocusList([1, 2, -1], focus=1)
        >>> ml[1:] = [3, 4]; ml
        MonitoredFocusList([1, 3, 4], focus=1)
        >>> ml[1:] = [2]; ml
        MonitoredFocusList([1, 2], focus=1)
        >>> ml[0:1] = [9,9,9]; ml
        MonitoredFocusList([9, 9, 9, 2], focus=3)
        >>> ml[:] = []; ml
        MonitoredFocusList([], focus=None)
        """
        self._handle_possible_focus_modified(slice(i, j), y)
        rval = super(MonitoredFocusList, self).__setslice__(i, j, y)
        self._clamp_focus()
        return rval
    
    def insert(self, index, object):
        """
        >>> ml = MonitoredFocusList([0,1,2,3], focus=2)
        >>> ml.insert(-1, -1); ml
        MonitoredFocusList([0, 1, 2, -1, 3], focus=2)
        >>> ml.insert(0, -2); ml
        MonitoredFocusList([-2, 0, 1, 2, -1, 3], focus=3)
        >>> ml.insert(3, -3); ml
        MonitoredFocusList([-2, 0, 1, -3, 2, -1, 3], focus=4)
        """
        self._handle_possible_focus_modified(slice(index, index), [object])
        return super(MonitoredFocusList, self).insert(index, object)

    def pop(self, index=-1):
        """
        >>> ml = MonitoredFocusList([-2,0,1,-3,2,3], focus=4)
        >>> ml.pop(3); ml
        -3
        MonitoredFocusList([-2, 0, 1, 2, 3], focus=3)
        >>> ml.pop(0); ml
        -2
        MonitoredFocusList([0, 1, 2, 3], focus=2)
        >>> ml.pop(-1); ml
        3
        MonitoredFocusList([0, 1, 2], focus=2)
        >>> ml.pop(2); ml
        2
        MonitoredFocusList([0, 1], focus=1)
        """
        self._handle_possible_focus_modified(slice(index, index+1 or None))
        return super(MonitoredFocusList, self).pop(index)

    def remove(self, value):
        """
        >>> ml = MonitoredFocusList([-2,0,1,-3,2,-1,3], focus=4)
        >>> ml.remove(-3); ml
        MonitoredFocusList([-2, 0, 1, 2, -1, 3], focus=3)
        >>> ml.remove(-2); ml
        MonitoredFocusList([0, 1, 2, -1, 3], focus=2)
        >>> ml.remove(3); ml
        MonitoredFocusList([0, 1, 2, -1], focus=2)
        """
        index = self.index(value)
        self._handle_possible_focus_modified(slice(index, index+1 or None))
        return super(MonitoredFocusList, self).remove(value)

    def reverse(self):
        """
        >>> ml = MonitoredFocusList([0,1,2,3,4], focus=1)
        >>> ml.reverse(); ml
        MonitoredFocusList([4, 3, 2, 1, 0], focus=3)
        """
        self._focus = max(0, len(self) - self._focus - 1)
        return super(MonitoredFocusList, self).reverse()

    def sort(self):
        """
        >>> ml = MonitoredFocusList([-2,0,1,-3,2,-1,3], focus=4)
        >>> ml.sort(); ml
        MonitoredFocusList([-3, -2, -1, 0, 1, 2, 3], focus=5)
        """
        if not self:
            return
        value = self[self._focus]
        rval = super(MonitoredFocusList, self).sort()
        self._focus = self.index(value)
        return rval





def _test():
    import doctest
    doctest.testmod()

if __name__=='__main__':
    _test()


########NEW FILE########
__FILENAME__ = old_str_util
#!/usr/bin/python
#
# Urwid unicode character processing tables
#    Copyright (C) 2004-2006  Ian Ward
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

import re
SAFE_ASCII_RE = re.compile("^[ -~]*$")

_byte_encoding = None

# GENERATED DATA
# generated from 
# http://www.unicode.org/Public/4.0-Update/EastAsianWidth-4.0.0.txt

widths = [
    (126, 1),
    (159, 0),
    (687, 1),
    (710, 0),
    (711, 1),
    (727, 0),
    (733, 1),
    (879, 0),
    (1154, 1),
    (1161, 0),
    (4347, 1),
    (4447, 2),
    (7467, 1),
    (7521, 0),
    (8369, 1),
    (8426, 0),
    (9000, 1),
    (9002, 2),
    (11021, 1),
    (12350, 2),
    (12351, 1),
    (12438, 2),
    (12442, 0),
    (19893, 2),
    (19967, 1),
    (55203, 2),
    (63743, 1),
    (64106, 2),
    (65039, 1),
    (65059, 0),
    (65131, 2),
    (65279, 1),
    (65376, 2),
    (65500, 1),
    (65510, 2),
    (120831, 1),
    (262141, 2),
    (1114109, 1),
]

# ACCESSOR FUNCTIONS

def get_width( o ):
    """Return the screen column width for unicode ordinal o."""
    global widths
    if o == 0xe or o == 0xf:
        return 0
    for num, wid in widths:
        if o <= num:
            return wid
    return 1

def decode_one( text, pos ):
    """Return (ordinal at pos, next position) for UTF-8 encoded text."""
    b1 = ord(text[pos])
    if not b1 & 0x80: 
        return b1, pos+1
    error = ord("?"), pos+1
    lt = len(text)
    lt = lt-pos
    if lt < 2:
        return error
    if b1 & 0xe0 == 0xc0:
        b2 = ord(text[pos+1])
        if b2 & 0xc0 != 0x80:
            return error
        o = ((b1&0x1f)<<6)|(b2&0x3f)
        if o < 0x80:
            return error
        return o, pos+2
    if lt < 3:
        return error
    if b1 & 0xf0 == 0xe0:
        b2 = ord(text[pos+1])
        if b2 & 0xc0 != 0x80:
            return error
        b3 = ord(text[pos+2])
        if b3 & 0xc0 != 0x80:
            return error
        o = ((b1&0x0f)<<12)|((b2&0x3f)<<6)|(b3&0x3f)
        if o < 0x800:
            return error
        return o, pos+3
    if lt < 4:
        return error
    if b1 & 0xf8 == 0xf0:
        b2 = ord(text[pos+1])
        if b2 & 0xc0 != 0x80:
            return error
        b3 = ord(text[pos+2])
        if b3 & 0xc0 != 0x80:
            return error
        b4 = ord(text[pos+2])
        if b4 & 0xc0 != 0x80:
            return error
        o = ((b1&0x07)<<18)|((b2&0x3f)<<12)|((b3&0x3f)<<6)|(b4&0x3f)
        if o < 0x10000:
            return error
        return o, pos+4
    return error

def decode_one_right( text, pos):
    """
    Return (ordinal at pos, next position) for UTF-8 encoded text.
    pos is assumed to be on the trailing byte of a utf-8 sequence."""
    error = ord("?"), pos-1
    p = pos
    while p >= 0:
        if ord(text[p])&0xc0 != 0x80:
            o, next = decode_one( text, p )
            return o, p-1
        p -=1
        if p == p-4:
            return error

def set_byte_encoding(enc):
    assert enc in ('utf8', 'narrow', 'wide')
    global _byte_encoding
    _byte_encoding = enc

def get_byte_encoding():
    return _byte_encoding

def calc_text_pos( text, start_offs, end_offs, pref_col ):
    """
    Calculate the closest position to the screen column pref_col in text
    where start_offs is the offset into text assumed to be screen column 0
    and end_offs is the end of the range to search.
    
    Returns (position, actual_col).
    """
    assert start_offs <= end_offs, `start_offs, end_offs`
    utfs = (type(text) == type("") and _byte_encoding == "utf8")
    if type(text) == type(u"") or utfs:
        i = start_offs
        sc = 0
        n = 1 # number to advance by
        while i < end_offs:
            if utfs:
                o, n = decode_one(text, i)
            else:
                o = ord(text[i])
                n = i + 1
            w = get_width(o)
            if w+sc > pref_col: 
                return i, sc
            i = n
            sc += w
        return i, sc
    assert type(text) == type(""), `text`
    # "wide" and "narrow"
    i = start_offs+pref_col
    if i >= end_offs:
        return end_offs, end_offs-start_offs
    if _byte_encoding == "wide":
        if within_double_byte( text, start_offs, i ) == 2:
            i -= 1
    return i, i-start_offs

def calc_width( text, start_offs, end_offs ):
    """
    Return the screen column width of text between start_offs and end_offs.
    """
    assert start_offs <= end_offs, `start_offs, end_offs`
    utfs = (type(text) == type("") and _byte_encoding == "utf8")
    if (type(text) == type(u"") or utfs) and not SAFE_ASCII_RE.match(text):
        i = start_offs
        sc = 0
        n = 1 # number to advance by
        while i < end_offs:
            if utfs:
                o, n = decode_one(text, i)
            else:
                o = ord(text[i])
                n = i + 1
            w = get_width(o)
            i = n
            sc += w
        return sc
    # "wide" and "narrow"
    return end_offs - start_offs
    
def is_wide_char( text, offs ):
    """
    Test if the character at offs within text is wide.
    """
    if type(text) == type(u""):
        o = ord(text[offs])
        return get_width(o) == 2
    assert type(text) == type("")
    if _byte_encoding == "utf8":
        o, n = decode_one(text, offs)
        return get_width(o) == 2
    if _byte_encoding == "wide":
        return within_double_byte(text, offs, offs) == 1
    return False

def move_prev_char( text, start_offs, end_offs ):
    """
    Return the position of the character before end_offs.
    """
    assert start_offs < end_offs
    if type(text) == type(u""):
        return end_offs-1
    assert type(text) == type("")
    if _byte_encoding == "utf8":
        o = end_offs-1
        while ord(text[o])&0xc0 == 0x80:
            o -= 1
        return o
    if _byte_encoding == "wide" and within_double_byte( text,
        start_offs, end_offs-1) == 2:
        return end_offs-2
    return end_offs-1

def move_next_char( text, start_offs, end_offs ):
    """
    Return the position of the character after start_offs.
    """
    assert start_offs < end_offs
    if type(text) == type(u""):
        return start_offs+1
    assert type(text) == type("")
    if _byte_encoding == "utf8":
        o = start_offs+1
        while o<end_offs and ord(text[o])&0xc0 == 0x80:
            o += 1
        return o
    if _byte_encoding == "wide" and within_double_byte(text, 
        start_offs, start_offs) == 1:
        return start_offs +2
    return start_offs+1

def within_double_byte(str, line_start, pos):
    """Return whether pos is within a double-byte encoded character.
    
    str -- string in question
    line_start -- offset of beginning of line (< pos)
    pos -- offset in question

    Return values:
    0 -- not within dbe char, or double_byte_encoding == False
    1 -- pos is on the 1st half of a dbe char
    2 -- pos is on the 2nd half og a dbe char
    """
    v = ord(str[pos])

    if v >= 0x40 and v < 0x7f:
        # might be second half of big5, uhc or gbk encoding
        if pos == line_start: return 0
        
        if ord(str[pos-1]) >= 0x81:
            if within_double_byte(str, line_start, pos-1) == 1:
                return 2
        return 0

    if v < 0x80: return 0

    i = pos -1
    while i >= line_start:
        if ord(str[i]) < 0x80:
            break
        i -= 1
    
    if (pos - i) & 1:
        return 1
    return 2

# TABLE GENERATION CODE

def process_east_asian_width():
    import sys
    out = []
    last = None
    for line in sys.stdin.readlines():
        if line[:1] == "#": continue
        line = line.strip()
        hex,rest = line.split(";",1)
        wid,rest = rest.split(" # ",1)
        word1 = rest.split(" ",1)[0]

        if "." in hex:
            hex = hex.split("..")[1]
        num = int(hex, 16)

        if word1 in ("COMBINING","MODIFIER","<control>"):
            l = 0
        elif wid in ("W", "F"):
            l = 2
        else:
            l = 1

        if last is None:
            out.append((0, l))
            last = l
        
        if last == l:
            out[-1] = (num, l)
        else:
            out.append( (num, l) )
            last = l

    print "widths = ["
    for o in out[1:]:  # treat control characters same as ascii
        print "\t"+`o`+","
    print "]"
        
if __name__ == "__main__":
    process_east_asian_width()


########NEW FILE########
__FILENAME__ = raw_display
#!/usr/bin/python
#
# Urwid raw display module
#    Copyright (C) 2004-2009  Ian Ward
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
Direct terminal UI implementation
"""

import fcntl
import termios
import os
import select
import struct
import sys
import tty
import signal

import util
import escape
from display_common import *
import signals

try:
    # python >= 2.4
    from subprocess import Popen, PIPE
except ImportError:
    Popen = None

# replace control characters with ?'s
_trans_table = "?"*32+"".join([chr(x) for x in range(32,256)])

class Screen(BaseScreen, RealTerminal):
    def __init__(self):
        """Initialize a screen that directly prints escape codes to an output
        terminal.
        """
        super(Screen, self).__init__()
        self._pal_escape = {}
        signals.connect_signal(self, UPDATE_PALETTE_ENTRY, 
            self._on_update_palette_entry)
        self.colors = 16 # FIXME: detect this
        self.has_underline = True # FIXME: detect this
        self.register_palette_entry( None, 'default','default')
        self._keyqueue = []
        self.prev_input_resize = 0
        self.set_input_timeouts()
        self.screen_buf = None
        self._resized = False
        self.maxrow = None
        self.gpm_mev = None
        self.gpm_event_pending = False
        self.last_bstate = 0
        self._setup_G1_done = False
        self._rows_used = None
        self._cy = 0
        self._started = False
        self.bright_is_bold = os.environ.get('TERM',None) != "xterm"
        self._next_timeout = None
        self._term_output_file = sys.stdout
        self._term_input_file = sys.stdin
        # pipe for signalling external event loops about resize events
        self._resize_pipe_rd, self._resize_pipe_wr = os.pipe()
        fcntl.fcntl(self._resize_pipe_rd, fcntl.F_SETFL, os.O_NONBLOCK)

    started = property(lambda self: self._started)

    def _on_update_palette_entry(self, name, *attrspecs):
        # copy the attribute to a dictionary containing the escape seqences
        self._pal_escape[name] = self._attrspec_to_escape(
            attrspecs[{16:0,1:1,88:2,256:3}[self.colors]])

    def set_input_timeouts(self, max_wait=None, complete_wait=0.125, 
        resize_wait=0.125):
        """
        Set the get_input timeout values.  All values are in floating
        point numbers of seconds.
        
        max_wait -- amount of time in seconds to wait for input when
            there is no input pending, wait forever if None
        complete_wait -- amount of time in seconds to wait when
            get_input detects an incomplete escape sequence at the
            end of the available input
        resize_wait -- amount of time in seconds to wait for more input
            after receiving two screen resize requests in a row to
            stop Urwid from consuming 100% cpu during a gradual
            window resize operation
        """
        self.max_wait = max_wait
        if max_wait is not None:
            if self._next_timeout is None:
                self._next_timeout = max_wait
            else:
                self._next_timeout = min(self._next_timeout, self.max_wait)
        self.complete_wait = complete_wait
        self.resize_wait = resize_wait

    def _sigwinch_handler(self, signum, frame):
        if not self._resized:
            os.write(self._resize_pipe_wr, 'R')
        self._resized = True
        self.screen_buf = None
      
    def signal_init(self):
        """
        Called in the startup of run wrapper to set the SIGWINCH 
        signal handler to self._sigwinch_handler.

        Override this function to call from main thread in threaded
        applications.
        """
        signal.signal(signal.SIGWINCH, self._sigwinch_handler)
    
    def signal_restore(self):
        """
        Called in the finally block of run wrapper to restore the
        SIGWINCH handler to the default handler.

        Override this function to call from main thread in threaded
        applications.
        """
        signal.signal(signal.SIGWINCH, signal.SIG_DFL)
      
    def set_mouse_tracking(self):
        """
        Enable mouse tracking.  
        
        After calling this function get_input will include mouse
        click events along with keystrokes.
        """
        self._term_output_file.write(escape.MOUSE_TRACKING_ON)

        self._start_gpm_tracking()
    
    def _start_gpm_tracking(self):
        if not os.path.isfile("/usr/bin/mev"):
            return
        if not os.environ.get('TERM',"").lower().startswith("linux"):
            return
        if not Popen:
            return
        m = Popen(["/usr/bin/mev","-e","158"], stdin=PIPE, stdout=PIPE,
            close_fds=True)
        fcntl.fcntl(m.stdout.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)
        self.gpm_mev = m
    
    def _stop_gpm_tracking(self):
        os.kill(self.gpm_mev.pid, signal.SIGINT)
        os.waitpid(self.gpm_mev.pid, 0)
        self.gpm_mev = None
    
    def start(self, alternate_buffer=True):
        """
        Initialize the screen and input mode.
        
        alternate_buffer -- use alternate screen buffer
        """
        assert not self._started
        if alternate_buffer:
            self._term_output_file.write(escape.SWITCH_TO_ALTERNATE_BUFFER)
            self._rows_used = None
        else:
            self._rows_used = 0
        self._old_termios_settings = termios.tcgetattr(0)
        self.signal_init()
        tty.setcbreak(self._term_input_file.fileno())
        self._alternate_buffer = alternate_buffer
        self._input_iter = self._run_input_iter()
        self._next_timeout = self.max_wait
        
        if not self._signal_keys_set:
            self._old_signal_keys = self.tty_signal_keys()

        self._started = True

    
    def stop(self):
        """
        Restore the screen.
        """
        self.clear()
        if not self._started:
            return
        self.signal_restore()
        termios.tcsetattr(0, termios.TCSADRAIN, 
            self._old_termios_settings)
        move_cursor = ""
        if self.gpm_mev:
            self._stop_gpm_tracking()
        if self._alternate_buffer:
            move_cursor = escape.RESTORE_NORMAL_BUFFER
        elif self.maxrow is not None:
            move_cursor = escape.set_cursor_position( 
                0, self.maxrow)
        self._term_output_file.write(self._attrspec_to_escape(AttrSpec('','')) 
            + escape.SI
            + escape.MOUSE_TRACKING_OFF
            + escape.SHOW_CURSOR
            + move_cursor + "\n" + escape.SHOW_CURSOR )
        self._input_iter = self._fake_input_iter()

        if self._old_signal_keys:
            self.tty_signal_keys(*self._old_signal_keys)
        
        self._started = False
        

    def run_wrapper(self, fn, alternate_buffer=True):
        """
        Call start to initialize screen, then call fn.  
        When fn exits call stop to restore the screen to normal.

        alternate_buffer -- use alternate screen buffer and restore
            normal screen buffer on exit
        """
        try:
            self.start(alternate_buffer)
            return fn()
        finally:
            self.stop()
            
    def get_input(self, raw_keys=False):
        """Return pending input as a list.

        raw_keys -- return raw keycodes as well as translated versions

        This function will immediately return all the input since the
        last time it was called.  If there is no input pending it will
        wait before returning an empty list.  The wait time may be
        configured with the set_input_timeouts function.

        If raw_keys is False (default) this function will return a list
        of keys pressed.  If raw_keys is True this function will return
        a ( keys pressed, raw keycodes ) tuple instead.
        
        Examples of keys returned
        -------------------------
        ASCII printable characters:  " ", "a", "0", "A", "-", "/" 
        ASCII control characters:  "tab", "enter"
        Escape sequences:  "up", "page up", "home", "insert", "f1"
        Key combinations:  "shift f1", "meta a", "ctrl b"
        Window events:  "window resize"
        
        When a narrow encoding is not enabled
        "Extended ASCII" characters:  "\\xa1", "\\xb2", "\\xfe"

        When a wide encoding is enabled
        Double-byte characters:  "\\xa1\\xea", "\\xb2\\xd4"

        When utf8 encoding is enabled
        Unicode characters: u"\\u00a5", u'\\u253c"
        
        Examples of mouse events returned
        ---------------------------------
        Mouse button press: ('mouse press', 1, 15, 13), 
                            ('meta mouse press', 2, 17, 23)
        Mouse drag: ('mouse drag', 1, 16, 13),
                    ('mouse drag', 1, 17, 13),
                ('ctrl mouse drag', 1, 18, 13)
        Mouse button release: ('mouse release', 0, 18, 13),
                              ('ctrl mouse release', 0, 17, 23)
        """
        assert self._started
        
        self._wait_for_input_ready(self._next_timeout)
        self._next_timeout, keys, raw = self._input_iter.next()
        
        # Avoid pegging CPU at 100% when slowly resizing
        if keys==['window resize'] and self.prev_input_resize:
            while True:
                self._wait_for_input_ready(self.resize_wait)
                self._next_timeout, keys, raw2 = \
                    self._input_iter.next()
                raw += raw2
                #if not keys:
                #    keys, raw2 = self._get_input( 
                #        self.resize_wait)
                #    raw += raw2
                if keys!=['window resize']:
                    break
            if keys[-1:]!=['window resize']:
                keys.append('window resize')
                
        if keys==['window resize']:
            self.prev_input_resize = 2
        elif self.prev_input_resize == 2 and not keys:
            self.prev_input_resize = 1
        else:
            self.prev_input_resize = 0
        
        if raw_keys:
            return keys, raw
        return keys

    def get_input_descriptors(self):
        """
        Return a list of integer file descriptors that should be
        polled in external event loops to check for user input.

        Use this method if you are implementing yout own event loop.
        """
        fd_list = [self._term_input_file.fileno(), self._resize_pipe_rd]
        if self.gpm_mev is not None:
            fd_list.append(self.gpm_mev.stdout.fileno())
        return fd_list
        
    def get_input_nonblocking(self):
        """
        Return a (next_input_timeout, keys_pressed, raw_keycodes) 
        tuple.

        Use this method if you are implementing your own event loop.
        
        When there is input waiting on one of the descriptors returned
        by get_input_descriptors() this method should be called to
        read and process the input.

        This method expects to be called in next_input_timeout seconds
        (a floating point number) if there is no input waiting.
        """
        assert self._started

        return self._input_iter.next()

    def _run_input_iter(self):
        def empty_resize_pipe():
            # clean out the pipe used to signal external event loops
            # that a resize has occured
            try:
                while True: os.read(self._resize_pipe_rd, 1)
            except OSError:
                pass

        while True:
            processed = []
            codes = self._get_gpm_codes() + \
                self._get_keyboard_codes()

            original_codes = codes
            try:
                while codes:
                    run, codes = escape.process_keyqueue(
                        codes, True)
                    processed.extend(run)
            except escape.MoreInputRequired:
                k = len(original_codes) - len(codes)
                yield (self.complete_wait, processed,
                    original_codes[:k])
                empty_resize_pipe()
                original_codes = codes
                processed = []

                codes += self._get_keyboard_codes() + \
                    self._get_gpm_codes()
                while codes:
                    run, codes = escape.process_keyqueue(
                        codes, False)
                    processed.extend(run)
            
            if self._resized:
                processed.append('window resize')
                self._resized = False

            yield (self.max_wait, processed, original_codes)
            empty_resize_pipe()

    def _fake_input_iter(self):
        """
        This generator is a placeholder for when the screen is stopped
        to always return that no input is available.
        """
        while True:
            yield (self.max_wait, [], [])

    def _get_keyboard_codes(self):
        codes = []
        while True:
            code = self._getch_nodelay()
            if code < 0:
                break
            codes.append(code)
        return codes

    def _get_gpm_codes(self):
        codes = []
        try:
            while self.gpm_mev is not None:
                codes.extend(self._encode_gpm_event())
        except IOError, e:
            if e.args[0] != 11:
                raise
        return codes

    def _wait_for_input_ready(self, timeout):
        ready = None
        fd_list = [self._term_input_file.fileno()]
        if self.gpm_mev is not None:
            fd_list += [ self.gpm_mev.stdout ]
        while True:
            try:
                if timeout is None:
                    ready,w,err = select.select(
                        fd_list, [], fd_list)
                else:
                    ready,w,err = select.select(
                        fd_list,[],fd_list, timeout)
                break
            except select.error, e:
                if e.args[0] != 4: 
                    raise
                if self._resized:
                    ready = []
                    break
        return ready    
        
    def _getch(self, timeout):
        ready = self._wait_for_input_ready(timeout)
        if self.gpm_mev is not None:
            if self.gpm_mev.stdout.fileno() in ready:
                self.gpm_event_pending = True
        if self._term_input_file.fileno() in ready:
            return ord(os.read(self._term_input_file.fileno(), 1))
        return -1
    
    def _encode_gpm_event( self ):
        self.gpm_event_pending = False
        s = self.gpm_mev.stdout.readline()
        l = s.split(",")
        if len(l) != 6:
            # unexpected output, stop tracking
            self._stop_gpm_tracking()
            return []
        ev, x, y, ign, b, m = s.split(",")
        ev = int( ev.split("x")[-1], 16)
        x = int( x.split(" ")[-1] )
        y = int( y.lstrip().split(" ")[0] )
        b = int( b.split(" ")[-1] )
        m = int( m.split("x")[-1].rstrip(), 16 )

        # convert to xterm-like escape sequence

        last = next = self.last_bstate
        l = []
        
        mod = 0
        if m & 1:    mod |= 4 # shift
        if m & 10:    mod |= 8 # alt
        if m & 4:    mod |= 16 # ctrl

        def append_button( b ):
            b |= mod
            l.extend([ 27, ord('['), ord('M'), b+32, x+32, y+32 ])

        if ev == 20: # press
            if b & 4 and last & 1 == 0:
                append_button( 0 )
                next |= 1
            if b & 2 and last & 2 == 0:
                append_button( 1 )
                next |= 2
            if b & 1 and last & 4 == 0:
                append_button( 2 )
                next |= 4
        elif ev == 146: # drag
            if b & 4:
                append_button( 0 + escape.MOUSE_DRAG_FLAG )
            elif b & 2:
                append_button( 1 + escape.MOUSE_DRAG_FLAG )
            elif b & 1:
                append_button( 2 + escape.MOUSE_DRAG_FLAG )
        else: # release
            if b & 4 and last & 1:
                append_button( 0 + escape.MOUSE_RELEASE_FLAG )
                next &= ~ 1
            if b & 2 and last & 2:
                append_button( 1 + escape.MOUSE_RELEASE_FLAG )
                next &= ~ 2
            if b & 1 and last & 4:
                append_button( 2 + escape.MOUSE_RELEASE_FLAG )
                next &= ~ 4
            
        self.last_bstate = next
        return l
    
    def _getch_nodelay(self):
        return self._getch(0)
    
    
    def get_cols_rows(self):
        """Return the terminal dimensions (num columns, num rows)."""
        buf = fcntl.ioctl(0, termios.TIOCGWINSZ, ' '*4)
        y, x = struct.unpack('hh', buf)
        self.maxrow = y
        return x, y

    def _setup_G1(self):
        """
        Initialize the G1 character set to graphics mode if required.
        """
        if self._setup_G1_done:
            return
        
        while True:
            try:
                self._term_output_file.write(escape.DESIGNATE_G1_SPECIAL)
                self._term_output_file.flush()
                break
            except IOError, e:
                pass
        self._setup_G1_done = True

    
    def draw_screen(self, (maxcol, maxrow), r ):
        """Paint screen with rendered canvas."""
        assert self._started

        assert maxrow == r.rows()

        self._setup_G1()
        
        if self._resized: 
            # handle resize before trying to draw screen
            return
        
        o = [escape.HIDE_CURSOR, self._attrspec_to_escape(AttrSpec('',''))]
        
        def partial_display():
            # returns True if the screen is in partial display mode
            # ie. only some rows belong to the display
            return self._rows_used is not None

        if not partial_display():
            o.append(escape.CURSOR_HOME)

        if self.screen_buf:
            osb = self.screen_buf
        else:
            osb = []
        sb = []
        cy = self._cy
        y = -1

        def set_cursor_home():
            if not partial_display():
                return escape.set_cursor_position(0, 0)
            return (escape.CURSOR_HOME_COL + 
                escape.move_cursor_up(cy))
        
        def set_cursor_row(y):
            if not partial_display():
                return escape.set_cursor_position(0, y)
            return escape.move_cursor_down(y - cy)

        def set_cursor_position(x, y):
            if not partial_display():
                return escape.set_cursor_position(x, y)
            if cy > y:
                return ('\b' + escape.CURSOR_HOME_COL +
                    escape.move_cursor_up(cy - y) +
                    escape.move_cursor_right(x))
            return ('\b' + escape.CURSOR_HOME_COL +
                escape.move_cursor_down(y - cy) +
                escape.move_cursor_right(x))
        
        def is_blank_row(row):
            if len(row) > 1:
                return False
            if row[0][2].strip():
                return False
            return True

        def attr_to_escape(a):
            if a in self._pal_escape:
                return self._pal_escape[a]
            elif isinstance(a, AttrSpec):
                return self._attrspec_to_escape(a)
            # undefined attributes use default/default
            # TODO: track and report these
            return self._attrspec_to_escape(
                AttrSpec('default','default'))

        ins = None
        o.append(set_cursor_home())
        cy = 0
        for row in r.content():
            y += 1
            if False and osb and osb[y] == row:
                # this row of the screen buffer matches what is
                # currently displayed, so we can skip this line
                sb.append( osb[y] )
                continue

            sb.append(row)
            
            # leave blank lines off display when we are using
            # the default screen buffer (allows partial screen)
            if partial_display() and y > self._rows_used:
                if is_blank_row(row):
                    continue
                self._rows_used = y
            
            if y or partial_display():
                o.append(set_cursor_position(0, y))
            # after updating the line we will be just over the
            # edge, but terminals still treat this as being
            # on the same line
            cy = y 
            
            if y == maxrow-1:
                row, back, ins = self._last_row(row)

            first = True
            lasta = lastcs = None
            for (a,cs, run) in row:
                run = run.translate( _trans_table )
                if first or lasta != a:
                    o.append(attr_to_escape(a))
                    lasta = a
                if first or lastcs != cs:
                    assert cs in [None, "0"], `cs`
                    if cs is None:
                        o.append( escape.SI )
                    else:
                        o.append( escape.SO )
                    lastcs = cs
                o.append( run )
                first = False
            if ins:
                (inserta, insertcs, inserttext) = ins
                ias = attr_to_escape(inserta)
                assert insertcs in [None, "0"], `insertcs`
                if cs is None:
                    icss = escape.SI
                else:
                    icss = escape.SO
                o += [    "\x08"*back, 
                    ias, icss,
                    escape.INSERT_ON, inserttext,
                    escape.INSERT_OFF ]

        if r.cursor is not None:
            x,y = r.cursor
            o += [set_cursor_position(x, y), 
                escape.SHOW_CURSOR  ]
            self._cy = y
        
        if self._resized: 
            # handle resize before trying to draw screen
            return
        try:
            k = 0
            for l in o:
                self._term_output_file.write( l )
                k += len(l)
                if k > 1024:
                    self._term_output_file.flush()
                    k = 0
            self._term_output_file.flush()
        except IOError, e:
            # ignore interrupted syscall
            if e.args[0] != 4:
                raise

        self.screen_buf = sb
        self.keep_cache_alive_link = r
                
    
    def _last_row(self, row):
        """On the last row we need to slide the bottom right character
        into place. Calculate the new line, attr and an insert sequence
        to do that.
        
        eg. last row:
        XXXXXXXXXXXXXXXXXXXXYZ
        
        Y will be drawn after Z, shifting Z into position.
        """
        
        new_row = row[:-1]
        z_attr, z_cs, last_text = row[-1]
        last_cols = util.calc_width(last_text, 0, len(last_text))
        last_offs, z_col = util.calc_text_pos(last_text, 0, 
            len(last_text), last_cols-1)
        if last_offs == 0:
            z_text = last_text
            del new_row[-1]
            # we need another segment
            y_attr, y_cs, nlast_text = row[-2]
            nlast_cols = util.calc_width(nlast_text, 0, 
                len(nlast_text))
            z_col += nlast_cols
            nlast_offs, y_col = util.calc_text_pos(nlast_text, 0,
                len(nlast_text), nlast_cols-1)
            y_text = nlast_text[nlast_offs:]
            if nlast_offs:
                new_row.append((y_attr, y_cs, 
                    nlast_text[:nlast_offs]))
        else:
            z_text = last_text[last_offs:]
            y_attr, y_cs = z_attr, z_cs
            nlast_cols = util.calc_width(last_text, 0,
                last_offs)
            nlast_offs, y_col = util.calc_text_pos(last_text, 0,
                last_offs, nlast_cols-1)
            y_text = last_text[nlast_offs:last_offs]
            if nlast_offs:
                new_row.append((y_attr, y_cs,
                    last_text[:nlast_offs]))
        
        new_row.append((z_attr, z_cs, z_text))
        return new_row, z_col-y_col, (y_attr, y_cs, y_text)

            
    
    def clear(self):
        """
        Force the screen to be completely repainted on the next
        call to draw_screen().
        """
        self.screen_buf = None
        self.setup_G1 = True

        
    def _attrspec_to_escape(self, a):
        """
        Convert AttrSpec instance a to an escape sequence for the terminal

        >>> s = Screen()
        >>> s.set_terminal_properties(colors=256)
        >>> a2e = s._attrspec_to_escape
        >>> a2e(s.AttrSpec('brown', 'dark green'))
        '\\x1b[0;33;42m'
        >>> a2e(s.AttrSpec('#fea,underline', '#d0d'))
        '\\x1b[0;38;5;229;4;48;5;164m'
        """
        if a.foreground_high:
            fg = "38;5;%d" % a.foreground_number
        elif a.foreground_basic:
            if a.foreground_number > 7:
                if self.bright_is_bold:
                    fg = "1;%d" % (a.foreground_number - 8 + 30)
                else:
                    fg = "%d" % (a.foreground_number - 8 + 90)
            else:
                fg = "%d" % (a.foreground_number + 30)
        else:
            fg = "39"
        st = "1;" * a.bold + "4;" * a.underline + "7;" * a.standout
        if a.background_high:
            bg = "48;5;%d" % a.background_number
        elif a.background_basic:
            if a.background_number > 7:
                # this doesn't work on most terminals
                bg = "%d" % (a.background_number - 8 + 100)
            else:
                bg = "%d" % (a.background_number + 40)
        else:
            bg = "49"
        return escape.ESC + "[0;%s;%s%sm" % (fg, st, bg)


    def set_terminal_properties(self, colors=None, bright_is_bold=None,
        has_underline=None):
        """
        colors -- number of colors terminal supports (1, 16, 88 or 256)
            or None to leave unchanged
        bright_is_bold -- set to True if this terminal uses the bold 
            setting to create bright colors (numbers 8-15), set to False
            if this Terminal can create bright colors without bold or
            None to leave unchanged
        has_underline -- set to True if this terminal can use the
            underline setting, False if it cannot or None to leave
            unchanged
        """
        if colors is None:
            colors = self.colors
        if bright_is_bold is None:
            bright_is_bold = self.bright_is_bold
        if has_underline is None:
            has_unerline = self.has_underline

        if colors == self.colors and bright_is_bold == self.bright_is_bold \
            and has_underline == self.has_underline:
            return

        self.colors = colors
        self.bright_is_bold = bright_is_bold
        self.has_underline = has_underline
            
        self.clear()
        self._pal_escape = {}
        for p,v in self._palette.items():
            self._on_update_palette_entry(p, *v)



    def reset_default_terminal_palette(self):
        """
        Attempt to set the terminal palette to default values as taken
        from xterm.  Uses number of colors from current 
        set_terminal_properties() screen setting.
        """
        if self.colors == 1:
            return

        def rgb_values(n):
            if self.colors == 16:
                aspec = AttrSpec("h%d"%n, "", 256)
            else:
                aspec = AttrSpec("h%d"%n, "", self.colors)
            return aspec.get_rgb_values()[:3]

        entries = [(n,) + rgb_values(n) for n in range(self.colors)]
        self.modify_terminal_palette(entries)


    def modify_terminal_palette(self, entries):
        """
        entries - list of (index, red, green, blue) tuples.

        Attempt to set part of the terminal pallette (this does not work
        on all terminals.)  The changes are sent as a single escape
        sequence so they should all take effect at the same time.
        
        0 <= index < 256 (some terminals will only have 16 or 88 colors)
        0 <= red, green, blue < 256
        """

        modify = ["%d;rgb:%02x/%02x/%02x" % (index, red, green, blue)
            for index, red, green, blue in entries]
        seq = self._term_output_file.write("\x1b]4;"+";".join(modify)+"\x1b\\")
        self._term_output_file.flush()


    # shortcut for creating an AttrSpec with this screen object's
    # number of colors
    AttrSpec = lambda self, fg, bg: AttrSpec(fg, bg, self.colors)
    

def _test():
    import doctest
    doctest.testmod()

if __name__=='__main__':
    _test()

########NEW FILE########
__FILENAME__ = signals
#!/usr/bin/python
#
# Urwid signal dispatching
#    Copyright (C) 2004-2009  Ian Ward
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




class MetaSignals(type):
    """
    register the list of signals in the class varable signals,
    including signals in superclasses.
    """
    def __init__(cls, name, bases, d):
        signals = d.get("signals", [])
        for superclass in cls.__bases__:
            signals.extend(getattr(superclass, 'signals', []))
        signals = dict([(x,None) for x in signals]).keys()
        d["signals"] = signals
        register_signal(cls, signals)
        super(MetaSignals, cls).__init__(name, bases, d)

def setdefaultattr(obj, name, value):
    # like dict.setdefault() for object attributes
    if hasattr(obj, name):
        return getattr(obj, name)
    setattr(obj, name, value)
    return value


class Signals(object):
    _signal_attr = '_urwid_signals' # attribute to attach to signal senders

    def __init__(self):
        self._supported = {}

    def register(self, sig_cls, signals):
        """
        Available as:
        urwid.regsiter_signal(sig_cls, signals)

        sig_class -- the class of an object that will be sending signals
        signals -- a list of signals that may be sent, typically each
            signal is represented by a string

        This function must be called for a class before connecting any
        signal callbacks or emiting any signals from that class' objects
        """
        self._supported[sig_cls] = signals

    def connect(self, obj, name, callback, user_arg=None):
        """
        Available as:
        urwid.connect_signal(obj, name, callback, user_arg=None)

        obj -- the object sending a signal
        name -- the name of the signal, typically a string
        callback -- the function to call when that signal is sent
        user_arg -- optional additional argument to callback, if None
            no arguments will be added
        
        When a matching signal is sent, callback will be called with
        all the positional parameters sent with the signal.  If user_arg
        is not None it will be sent added to the end of the positional
        parameters sent to callback.
        """
        sig_cls = obj.__class__
        if not name in self._supported.get(sig_cls, []):
            raise NameError, "No such signal %r for object %r" % \
                (name, obj)
        d = setdefaultattr(obj, self._signal_attr, {})
        d.setdefault(name, []).append((callback, user_arg))
        
    def disconnect(self, obj, name, callback, user_arg=None):
        """
        Available as:
        urwid.disconnect_signal(obj, name, callback, user_arg=None)

        This function will remove a callback from the list connected
        to a signal with connect_signal().
        """
        d = setdefaultattr(obj, self._signal_attr, {})
        if name not in d:
            return
        if (callback, user_arg) not in d[name]:
            return
        d[name].remove((callback, user_arg))
 
    def emit(self, obj, name, *args):
        """
        Available as:
        urwid.emit_signal(obj, name, *args)

        obj -- the object sending a signal
        name -- the name of the signal, typically a string
        *args -- zero or more positional arguments to pass to the signal
            callback functions

        This function calls each of the callbacks connected to this signal
        with the args arguments as positional parameters.

        This function returns True if any of the callbacks returned True.
        """
        result = False
        d = getattr(obj, self._signal_attr, {})
        for callback, user_arg in d.get(name, []):
            args_copy = args
            if user_arg is not None:
                args_copy = args + (user_arg,)
            result |= bool(callback(*args_copy))
        return result

_signals = Signals()
emit_signal = _signals.emit
register_signal = _signals.register
connect_signal = _signals.connect
disconnect_signal = _signals.disconnect


########NEW FILE########
__FILENAME__ = split_repr
#!/usr/bin/python
#
# Urwid split_repr helper functions
#    Copyright (C) 2004-2008  Ian Ward
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

from inspect import getargspec 

def split_repr(self):
    """
    Return a helpful description of the object using
    self._repr_words() and self._repr_attrs() to add
    to the description.  This function may be used by
    adding code to your class like this:

    >>> class Foo(object):
    ...     __repr__ = split_repr
    ...     def _repr_words(self):
    ...         return ["words", "here"]
    ...     def _repr_attrs(self):
    ...         return {'attrs': "appear too"}
    >>> Foo()
    <Foo words here attrs='appear too'>
    >>> class Bar(Foo):
    ...     def _repr_words(self):
    ...         return Foo._repr_words(self) + ["too"]
    ...     def _repr_attrs(self):
    ...         return dict(Foo._repr_attrs(self), barttr=42)
    >>> Bar()
    <Bar words here too attrs='appear too' barttr=42>
    """
    alist = self._repr_attrs().items()
    alist.sort()
    words = self._repr_words()
    if not words and not alist:
        # if we're just going to print the classname fall back
        # to the previous __repr__ implementation instead
        return super(self.__class__, self).__repr__()
    if words and alist: words.append("")
    return "<%s %s>" % (self.__class__.__name__,
        " ".join(words) +
        " ".join(["%s=%s" % (k,normalize_repr(v)) for k,v in alist]))
    
def normalize_repr(v):
    """
    Return dictionary repr sorted by keys, leave others unchanged

    >>> normalize_repr({1:2,3:4,5:6,7:8})
    '{1: 2, 3: 4, 5: 6, 7: 8}'
    >>> normalize_repr('foo')
    "'foo'"
    """
    if isinstance(v, dict):
        items = v.items()
        items.sort()
        return "{" + ", ".join([
            repr(k) + ": " + repr(v) for k, v in items]) + "}"

    return repr(v)

    
def remove_defaults(d, fn):
    """
    Remove keys in d that are set to the default values from
    fn.  This method is used to unclutter the _repr_attrs() 
    return value.
    
    d will be modified by this function.

    Returns d.

    >>> class Foo(object):
    ...     def __init__(self, a=1, b=2):
    ...         self.values = a, b
    ...     __repr__ = split_repr
    ...     def _repr_words(self):
    ...         return ["object"]
    ...     def _repr_attrs(self):
    ...         d = dict(a=self.values[0], b=self.values[1])
    ...         return remove_defaults(d, Foo.__init__)
    >>> Foo(42, 100)
    <Foo object a=42 b=100>
    >>> Foo(10, 2)
    <Foo object a=10>
    >>> Foo()
    <Foo object>
    """
    args, varargs, varkw, defaults = getargspec(fn)

    # ignore *varargs and **kwargs
    if varkw:
        del args[-1]
    if varargs:
        del args[-1]

    # create adictionary of args with default values
    ddict = dict(zip(args[len(args) - len(defaults):], defaults))

    for k, v in d.items():
        if k in ddict:
            # remove values that match their defaults
            if ddict[k] == v:
                del d[k]

    return d



def _test():
    import doctest
    doctest.testmod()

if __name__=='__main__':
    _test()

########NEW FILE########
__FILENAME__ = text_layout
#!/usr/bin/python
#
# Urwid Text Layout classes
#    Copyright (C) 2004-2007  Ian Ward
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

from util import *

class TextLayout:
    def supports_align_mode(self, align):
        """Return True if align is a supported align mode."""
        return True
    def supports_wrap_mode(self, wrap):
        """Return True if wrap is a supported wrap mode."""
        return True
    def layout(self, text, width, align, wrap ):
        """
        Return a layout structure for text.
        
        text -- string in current encoding or unicode string
        width -- number of screen columns available
        align -- align mode for text
        wrap -- wrap mode for text

        Layout structure is a list of line layouts, one per output line.
        Line layouts are lists than may contain the following tuples:
          ( column width of text segment, start offset, end offset )
          ( number of space characters to insert, offset or None)
          ( column width of insert text, offset, "insert text" )

        The offset in the last two tuples is used to determine the
        attribute used for the inserted spaces or text respectively.  
        The attribute used will be the same as the attribute at that 
        text offset.  If the offset is None when inserting spaces
        then no attribute will be used.
        """
        assert 0, ("This function must be overridden by a real"
            " text layout class. (see StandardTextLayout)")
        return [[]]

class StandardTextLayout(TextLayout):
    def __init__(self):#, tab_stops=(), tab_stop_every=8):
        pass
        #"""
        #tab_stops -- list of screen column indexes for tab stops
        #tab_stop_every -- repeated interval for following tab stops
        #"""
        #assert tab_stop_every is None or type(tab_stop_every)==type(0)
        #if not tab_stops and tab_stop_every:
        #    self.tab_stops = (tab_stop_every,)
        #self.tab_stops = tab_stops
        #self.tab_stop_every = tab_stop_every
    def supports_align_mode(self, align):
        """Return True if align is 'left', 'center' or 'right'."""
        return align in ('left', 'center', 'right')
    def supports_wrap_mode(self, wrap):
        """Return True if wrap is 'any', 'space' or 'clip'."""
        return wrap in ('any', 'space', 'clip')
    def layout(self, text, width, align, wrap ):
        """Return a layout structure for text."""
        segs = self.calculate_text_segments( text, width, wrap )
        return self.align_layout( text, width, segs, wrap, align )

    def pack(self, maxcol, layout):
        """
        Return a minimal maxcol value that would result in the same
        number of lines for layout.  layout must be a layout structure
        returned by self.layout().
        """
        maxwidth = 0
        assert layout, "huh? empty layout?: "+`layout`
        for l in layout:
            lw = line_width(l)
            if lw >= maxcol:
                return maxcol
            maxwidth = max(maxwidth, lw)
        return maxwidth            

    def align_layout( self, text, width, segs, wrap, align ):
        """Convert the layout segs to an aligned layout."""
        out = []
        for l in segs:
            sc = line_width(l)
            if sc == width or align=='left':
                out.append(l)
                continue

            if align == 'right':
                out.append([(width-sc, None)] + l)
                continue
            assert align == 'center'
            out.append([((width-sc+1)/2, None)] + l)
        return out
        

    def calculate_text_segments( self, text, width, wrap ):
        """
        Calculate the segments of text to display given width screen 
        columns to display them.  
        
        text - text to display
        width - number of available screen columns
        wrap - wrapping mode used
        
        Returns a layout structure without aligmnent applied.
        """
        b = []
        p = 0
        if wrap == 'clip':
            # no wrapping to calculate, so it's easy.
            while p<=len(text):
                n_cr = text.find("\n", p)
                if n_cr == -1: 
                    n_cr = len(text)
                sc = calc_width(text, p, n_cr)
                l = [(0,n_cr)]
                if p!=n_cr:
                    l = [(sc, p, n_cr)] + l
                b.append(l)
                p = n_cr+1
            return b

        
        while p<=len(text):
            # look for next eligible line break
            n_cr = text.find("\n", p)
            if n_cr == -1: 
                n_cr = len(text)
            sc = calc_width(text, p, n_cr)
            if sc == 0:
                # removed character hint
                b.append([(0,n_cr)])
                p = n_cr+1
                continue
            if sc <= width:
                # this segment fits
                b.append([(sc,p,n_cr),
                    # removed character hint
                    (0,n_cr)])
                
                p = n_cr+1
                continue
            pos, sc = calc_text_pos( text, p, n_cr, width )
            # FIXME: handle pathological width=1 double-byte case
            if wrap == 'any':
                b.append([(sc,p,pos)])
                p = pos
                continue
            assert wrap == 'space'
            if text[pos] == " ":
                # perfect space wrap
                b.append([(sc,p,pos),
                    # removed character hint
                    (0,pos)])
                p = pos+1
                continue
            if is_wide_char(text, pos):
                # perfect next wide
                b.append([(sc,p,pos)])
                p = pos
                continue
            prev = pos    
            while prev > p:
                prev = move_prev_char(text, p, prev)
                if text[prev] == " ":
                    sc = calc_width(text,p,prev)
                    l = [(0,prev)]
                    if p!=prev:
                        l = [(sc,p,prev)] + l
                    b.append(l)
                    p = prev+1 
                    break
                if is_wide_char(text,prev):
                    # wrap after wide char
                    next = move_next_char(text, prev, pos)
                    sc = calc_width(text,p,next)
                    b.append([(sc,p,next)])
                    p = next
                    break
            else:
                # unwrap previous line space if possible to
                # fit more text (we're breaking a word anyway)
                if b and (len(b[-1]) == 2 or ( len(b[-1])==1 
                        and len(b[-1][0])==2 )):
                    # look for removed space above
                    if len(b[-1]) == 1:
                        [(h_sc, h_off)] = b[-1]
                        p_sc = 0
                        p_off = p_end = h_off
                    else:
                        [(p_sc, p_off, p_end),
                               (h_sc, h_off)] = b[-1]
                    if (p_sc < width and h_sc==0 and
                        text[h_off] == " "):
                        # combine with previous line
                        del b[-1]
                        p = p_off
                        pos, sc = calc_text_pos( 
                            text, p, n_cr, width )
                        b.append([(sc,p,pos)])
                        # check for trailing " " or "\n"
                        p = pos
                        if p < len(text) and (
                            text[p] in (" ","\n")):
                            # removed character hint
                            b[-1].append((0,p))
                            p += 1
                        continue
                        
                        
                # force any char wrap
                b.append([(sc,p,pos)])
                p = pos
        return b



######################################
# default layout object to use
default_layout = StandardTextLayout()
######################################

    
class LayoutSegment:
    def __init__(self, seg):
        """Create object from line layout segment structure"""
        
        assert type(seg) == type(()), `seg`
        assert len(seg) in (2,3), `seg`
        
        self.sc, self.offs = seg[:2]
        
        assert type(self.sc) == type(0), `self.sc`
        
        if len(seg)==3:
            assert type(self.offs) == type(0), `self.offs`
            assert self.sc > 0, `seg`
            t = seg[2]
            if type(t) == type(""):
                self.text = t
                self.end = None
            else:
                assert type(t) == type(0), `t`
                self.text = None
                self.end = t
        else:
            assert len(seg) == 2, `seg`
            if self.offs is not None:
                assert self.sc >= 0, `seg`
                assert type(self.offs)==type(0)
            self.text = self.end = None
            
    def subseg(self, text, start, end):
        """
        Return a "sub-segment" list containing segment structures 
        that make up a portion of this segment.

        A list is returned to handle cases where wide characters
        need to be replaced with a space character at either edge
        so two or three segments will be returned.
        """
        if start < 0: start = 0
        if end > self.sc: end = self.sc
        if start >= end:
            return [] # completely gone
        if self.text:
            # use text stored in segment (self.text)
            spos, epos, pad_left, pad_right = calc_trim_text(
                self.text, 0, len(self.text), start, end )
            return [ (end-start, self.offs, " "*pad_left + 
                self.text[spos:epos] + " "*pad_right) ]
        elif self.end:
            # use text passed as parameter (text)
            spos, epos, pad_left, pad_right = calc_trim_text(
                text, self.offs, self.end, start, end )
            l = []
            if pad_left:
                l.append((1,spos-1))
            l.append((end-start-pad_left-pad_right, spos, epos))
            if pad_right:
                l.append((1,epos))
            return l
        else:
            # simple padding adjustment
            return [(end-start,self.offs)]


def line_width( segs ):
    """
    Return the screen column width of one line of a text layout structure.

    This function ignores any existing shift applied to the line,
    represended by an (amount, None) tuple at the start of the line.
    """
    sc = 0
    seglist = segs
    if segs and len(segs[0])==2 and segs[0][1]==None:
        seglist = segs[1:]
    for s in seglist:
        sc += s[0]
    return sc

def shift_line( segs, amount ):
    """
    Return a shifted line from a layout structure to the left or right.
    segs -- line of a layout structure
    amount -- screen columns to shift right (+ve) or left (-ve)
    """
    assert type(amount)==type(0), `amount`
    
    if segs and len(segs[0])==2 and segs[0][1]==None:
        # existing shift
        amount += segs[0][0]
        if amount:
            return [(amount,None)]+segs[1:]
        return segs[1:]
            
    if amount:
        return [(amount,None)]+segs
    return segs
    

def trim_line( segs, text, start, end ):
    """
    Return a trimmed line of a text layout structure.
    text -- text to which this layout structre applies
    start -- starting screen column
    end -- ending screen column
    """
    l = []
    x = 0
    for seg in segs:
        sc = seg[0]
        if start or sc < 0:
            if start >= sc:
                start -= sc
                x += sc
                continue
            s = LayoutSegment(seg)
            if x+sc >= end:
                # can all be done at once
                return s.subseg( text, start, end-x )
            l += s.subseg( text, start, sc )
            start = 0
            x += sc
            continue
        if x >= end:
            break
        if x+sc > end:
            s = LayoutSegment(seg)
            l += s.subseg( text, 0, end-x )
            break
        l.append( seg )
    return l



def calc_line_pos( text, line_layout, pref_col ):
    """
    Calculate the closest linear position to pref_col given a
    line layout structure.  Returns None if no position found.
    """
    closest_sc = None
    closest_pos = None
    current_sc = 0

    if pref_col == 'left':
        for seg in line_layout:
            s = LayoutSegment(seg)
            if s.offs is not None:
                return s.offs
        return
    elif pref_col == 'right':
        for seg in line_layout:
            s = LayoutSegment(seg)
            if s.offs is not None:
                closest_pos = s
        s = closest_pos
        if s is None:
            return
        if s.end is None:
            return s.offs
        return calc_text_pos( text, s.offs, s.end, s.sc-1)[0]

    for seg in line_layout:
        s = LayoutSegment(seg)
        if s.offs is not None:
            if s.end is not None:
                if (current_sc <= pref_col and 
                    pref_col < current_sc + s.sc):
                    # exact match within this segment
                    return calc_text_pos( text, 
                        s.offs, s.end,
                        pref_col - current_sc )[0]
                elif current_sc <= pref_col:
                    closest_sc = current_sc + s.sc - 1
                    closest_pos = s
                    
            if closest_sc is None or ( abs(pref_col-current_sc)
                    < abs(pref_col-closest_sc) ):
                # this screen column is closer
                closest_sc = current_sc
                closest_pos = s.offs
            if current_sc > closest_sc:
                # we're moving past
                break
        current_sc += s.sc
    
    if closest_pos is None or type(closest_pos) == type(0):
        return closest_pos

    # return the last positions in the segment "closest_pos"
    s = closest_pos
    return calc_text_pos( text, s.offs, s.end, s.sc-1)[0]

def calc_pos( text, layout, pref_col, row ):
    """
    Calculate the closest linear position to pref_col and row given a
    layout structure.
    """

    if row < 0 or row >= len(layout):
        raise Exception("calculate_pos: out of layout row range")
    
    pos = calc_line_pos( text, layout[row], pref_col )
    if pos is not None:
        return pos
    
    rows_above = range(row-1,-1,-1)
    rows_below = range(row+1,len(layout))
    while rows_above and rows_below:
        if rows_above: 
            r = rows_above.pop(0)
            pos = calc_line_pos(text, layout[r], pref_col)
            if pos is not None: return pos
        if rows_below: 
            r = rows_below.pop(0)
            pos = calc_line_pos(text, layout[r], pref_col)
            if pos is not None: return pos
    return 0


def calc_coords( text, layout, pos, clamp=1 ):
    """
    Calculate the coordinates closest to position pos in text with layout.
    
    text -- raw string or unicode string
    layout -- layout structure applied to text
    pos -- integer position into text
    clamp -- ignored right now
    """
    closest = None
    y = 0
    for line_layout in layout:
        x = 0
        for seg in line_layout:
            s = LayoutSegment(seg)
            if s.offs is None:
                x += s.sc
                continue
            if s.offs == pos:
                return x,y
            if s.end is not None and s.offs<=pos and s.end>pos:
                x += calc_width( text, s.offs, pos )
                return x,y
            distance = abs(s.offs - pos)
            if s.end is not None and s.end<pos:
                distance = pos - (s.end-1)
            if closest is None or distance < closest[0]:
                closest = distance, (x,y)
            x += s.sc
        y += 1
    
    if closest:
        return closest[1]
    return 0,0

########NEW FILE########
__FILENAME__ = util
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Urwid utility functions
#    Copyright (C) 2004-2007  Ian Ward
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

from __future__ import nested_scopes

import escape

import encodings

try:
    import str_util
except ImportError:
    import old_str_util as str_util

# bring str_util functions into our namespace
calc_text_pos = str_util.calc_text_pos
calc_width = str_util.calc_width
is_wide_char = str_util.is_wide_char
move_next_char = str_util.move_next_char
move_prev_char = str_util.move_prev_char
within_double_byte = str_util.within_double_byte


try: enumerate
except: enumerate = lambda x: zip(range(len(x)),x) # old python


# Try to determine if using a supported double-byte encoding
import locale
try:
    try:
        locale.setlocale( locale.LC_ALL, "" )
    except locale.Error:
        pass
    detected_encoding = locale.getlocale()[1]
    if not detected_encoding:
        detected_encoding = ""
except ValueError, e:
    # with invalid LANG value python will throw ValueError
    if e.args and e.args[0].startswith("unknown locale"):
        detected_encoding = ""
    else:
        raise

_target_encoding = None
_use_dec_special = True


def set_encoding( encoding ):
    """
    Set the byte encoding to assume when processing strings and the
    encoding to use when converting unicode strings.
    """
    encoding = encoding.lower()

    global _target_encoding, _use_dec_special

    if encoding in ( 'utf-8', 'utf8', 'utf' ):
        str_util.set_byte_encoding("utf8")
            
        _use_dec_special = False
    elif encoding in ( 'euc-jp' # JISX 0208 only
            , 'euc-kr', 'euc-cn', 'euc-tw' # CNS 11643 plain 1 only
            , 'gb2312', 'gbk', 'big5', 'cn-gb', 'uhc'
            # these shouldn't happen, should they?
            , 'eucjp', 'euckr', 'euccn', 'euctw', 'cncb' ):
        str_util.set_byte_encoding("wide")
            
        _use_dec_special = True
    else:
        str_util.set_byte_encoding("narrow")
        _use_dec_special = True

    # if encoding is valid for conversion from unicode, remember it
    _target_encoding = 'ascii'
    try:    
        if encoding:
            u"".encode(encoding)
            _target_encoding = encoding
    except LookupError: pass


def get_encoding_mode():
    """
    Get the mode Urwid is using when processing text strings.
    Returns 'narrow' for 8-bit encodings, 'wide' for CJK encodings
    or 'utf8' for UTF-8 encodings.
    """
    return str_util.get_byte_encoding()


def apply_target_encoding( s ):
    """
    Return (encoded byte string, character set rle).
    """
    if _use_dec_special and type(s) == type(u""):
        # first convert drawing characters
        try:
            s = s.translate( escape.DEC_SPECIAL_CHARMAP )
        except NotImplementedError:
            # python < 2.4 needs to do this the hard way..
            for c, alt in zip(escape.DEC_SPECIAL_CHARS, 
                    escape.ALT_DEC_SPECIAL_CHARS):
                s = s.replace( c, escape.SO+alt+escape.SI )
    
    if type(s) == type(u""):
        s = s.replace( escape.SI+escape.SO, u"" ) # remove redundant shifts
        s = s.encode( _target_encoding )

    sis = s.split( escape.SO )

    sis0 = sis[0].replace( escape.SI, "" )
    sout = []
    cout = []
    if sis0:
        sout.append( sis0 )
        cout.append( (None,len(sis0)) )
    
    if len(sis)==1:
        return sis0, cout
    
    for sn in sis[1:]:
        sl = sn.split( escape.SI, 1 ) 
        if len(sl) == 1:
            sin = sl[0]
            sout.append(sin)
            rle_append_modify(cout, (escape.DEC_TAG, len(sin)))
            continue
        sin, son = sl
        son = son.replace( escape.SI, "" )
        if sin:
            sout.append(sin)
            rle_append_modify(cout, (escape.DEC_TAG, len(sin)))
        if son:
            sout.append(son)
            rle_append_modify(cout, (None, len(son)))
    
    return "".join(sout), cout
    
    
######################################################################
# Try to set the encoding using the one detected by the locale module
set_encoding( detected_encoding )
######################################################################


def supports_unicode():
    """
    Return True if python is able to convert non-ascii unicode strings
    to the current encoding.
    """
    return _target_encoding and _target_encoding != 'ascii'





def calc_trim_text( text, start_offs, end_offs, start_col, end_col ):
    """
    Calculate the result of trimming text.
    start_offs -- offset into text to treat as screen column 0
    end_offs -- offset into text to treat as the end of the line
    start_col -- screen column to trim at the left
    end_col -- screen column to trim at the right

    Returns (start, end, pad_left, pad_right), where:
    start -- resulting start offset
    end -- resulting end offset
    pad_left -- 0 for no pad or 1 for one space to be added
    pad_right -- 0 for no pad or 1 for one space to be added
    """
    l = []
    spos = start_offs
    pad_left = pad_right = 0
    if start_col > 0:
        spos, sc = calc_text_pos( text, spos, end_offs, start_col )
        if sc < start_col:
            pad_left = 1
            spos, sc = calc_text_pos( text, start_offs, 
                end_offs, start_col+1 )
    run = end_col - start_col - pad_left
    pos, sc = calc_text_pos( text, spos, end_offs, run )
    if sc < run:
        pad_right = 1
    return ( spos, pos, pad_left, pad_right )




def trim_text_attr_cs( text, attr, cs, start_col, end_col ):
    """
    Return ( trimmed text, trimmed attr, trimmed cs ).
    """
    spos, epos, pad_left, pad_right = calc_trim_text( 
        text, 0, len(text), start_col, end_col )
    attrtr = rle_subseg( attr, spos, epos )
    cstr = rle_subseg( cs, spos, epos )
    if pad_left:
        al = rle_get_at( attr, spos-1 )
        rle_append_beginning_modify( attrtr, (al, 1) )
        rle_append_beginning_modify( cstr, (None, 1) )
    if pad_right:
        al = rle_get_at( attr, epos )
        rle_append_modify( attrtr, (al, 1) )
        rle_append_modify( cstr, (None, 1) )
    
    return " "*pad_left + text[spos:epos] + " "*pad_right, attrtr, cstr
    
        
def rle_get_at( rle, pos ):
    """
    Return the attribute at offset pos.
    """
    x = 0
    if pos < 0:
        return None
    for a, run in rle:
        if x+run > pos:
            return a
        x += run
    return None


def rle_subseg( rle, start, end ):
    """Return a sub segment of an rle list."""
    l = []
    x = 0
    for a, run in rle:
        if start:
            if start >= run:
                start -= run
                x += run
                continue
            x += start
            run -= start
            start = 0
        if x >= end:
            break
        if x+run > end:
            run = end-x
        x += run    
        l.append( (a, run) )
    return l


def rle_len( rle ):
    """
    Return the number of characters covered by a run length
    encoded attribute list.
    """
    
    run = 0
    for v in rle:
        assert type(v) == type(()), `rle`
        a, r = v
        run += r
    return run

def rle_append_beginning_modify( rle, (a, r) ):
    """
    Append (a, r) to BEGINNING of rle.
    Merge with first run when possible

    MODIFIES rle parameter contents. Returns None.
    """
    if not rle:
        rle[:] = [(a, r)]
    else:    
        al, run = rle[0]
        if a == al:
            rle[0] = (a,run+r)
        else:
            rle[0:0] = [(al, r)]
            
            
def rle_append_modify( rle, (a, r) ):
    """
    Append (a,r) to the rle list rle.
    Merge with last run when possible.
    
    MODIFIES rle parameter contents. Returns None.
    """
    if not rle or rle[-1][0] != a:
        rle.append( (a,r) )
        return
    la,lr = rle[-1]
    rle[-1] = (a, lr+r)

def rle_join_modify( rle, rle2 ):
    """
    Append attribute list rle2 to rle.
    Merge last run of rle with first run of rle2 when possible.

    MODIFIES attr parameter contents. Returns None.
    """
    if not rle2:
        return
    rle_append_modify(rle, rle2[0])
    rle += rle2[1:]
        
def rle_product( rle1, rle2 ):
    """
    Merge the runs of rle1 and rle2 like this:
    eg.
    rle1 = [ ("a", 10), ("b", 5) ]
    rle2 = [ ("Q", 5), ("P", 10) ]
    rle_product: [ (("a","Q"), 5), (("a","P"), 5), (("b","P"), 5) ]

    rle1 and rle2 are assumed to cover the same total run.
    """
    i1 = i2 = 1 # rle1, rle2 indexes
    if not rle1 or not rle2: return []
    a1, r1 = rle1[0]
    a2, r2 = rle2[0]
    
    l = []
    while r1 and r2:
        r = min(r1, r2)
        rle_append_modify( l, ((a1,a2),r) )
        r1 -= r
        if r1 == 0 and i1< len(rle1):
            a1, r1 = rle1[i1]
            i1 += 1
        r2 -= r
        if r2 == 0 and i2< len(rle2):
            a2, r2 = rle2[i2]
            i2 += 1
    return l    


def rle_factor( rle ):
    """
    Inverse of rle_product.
    """
    rle1 = []
    rle2 = []
    for (a1, a2), r in rle:
        rle_append_modify( rle1, (a1, r) )
        rle_append_modify( rle2, (a2, r) )
    return rle1, rle2


class TagMarkupException( Exception ): pass

def decompose_tagmarkup( tm ):
    """Return (text string, attribute list) for tagmarkup passed."""
    
    tl, al = _tagmarkup_recurse( tm, None )
    text = "".join(tl)
    
    if al and al[-1][0] is None:
        del al[-1]
        
    return text, al
    
def _tagmarkup_recurse( tm, attr ):
    """Return (text list, attribute list) for tagmarkup passed.
    
    tm -- tagmarkup
    attr -- current attribute or None"""
    
    if type(tm) == list:
        # for lists recurse to process each subelement
        rtl = [] 
        ral = []
        for element in tm:
            tl, al = _tagmarkup_recurse( element, attr )
            if ral:
                # merge attributes when possible
                last_attr, last_run = ral[-1]
                top_attr, top_run = al[0]
                if last_attr == top_attr:
                    ral[-1] = (top_attr, last_run + top_run)
                    del al[-1]
            rtl += tl
            ral += al
        return rtl, ral
        
    if type(tm) == type(()):
        # tuples mark a new attribute boundary
        if len(tm) != 2: 
            raise TagMarkupException, "Tuples must be in the form (attribute, tagmarkup): %s" % `tm`

        attr, element = tm
        return _tagmarkup_recurse( element, attr )
    
    if type(tm) not in (str, unicode):
        # last ditch, try converting the object to unicode
        try:
            tm = uncode(tm)
        except:
            raise TagMarkupException, "Invalid markup element: %r" % tm
    
    # text
    return [tm], [(attr, len(tm))]



def is_mouse_event( ev ):
    return type(ev) == type(()) and len(ev)==4 and ev[0].find("mouse")>=0

def is_mouse_press( ev ):
    return ev.find("press")>=0



class MetaSuper(type):
    """adding .__super"""
    def __init__(cls, name, bases, d):
        super(MetaSuper, cls).__init__(name, bases, d)
        if hasattr(cls, "_%s__super" % name):
            raise AttributeError, "Class has same name as one of its super classes"
        setattr(cls, "_%s__super" % name, super(cls))


    
def int_scale(val, val_range, out_range):
    """
    Scale val in the range [0, val_range-1] to an integer in the range 
    [0, out_range-1].  This implementaton uses the "round-half-up" rounding 
    method.

    >>> "%x" % int_scale(0x7, 0x10, 0x10000)
    '7777'
    >>> "%x" % int_scale(0x5f, 0x100, 0x10)
    '6'
    >>> int_scale(2, 6, 101)
    40
    >>> int_scale(1, 3, 4)
    2
    """
    num = int(val * (out_range-1) * 2 + (val_range-1))
    dem = ((val_range-1) * 2)
    # if num % dem == 0 then we are exactly half-way and have rounded up.
    return num / dem


########NEW FILE########
__FILENAME__ = web_display
#!/usr/bin/python
#
# Urwid web (CGI/Asynchronous Javascript) display module
#    Copyright (C) 2004-2007  Ian Ward
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
Urwid web application display module
"""
import os
import sys
import signal
import random
import select
import util
import socket
import glob
_js_code = r"""
// Urwid web (CGI/Asynchronous Javascript) display module
//    Copyright (C) 2004-2005  Ian Ward
//
//    This library is free software; you can redistribute it and/or
//    modify it under the terms of the GNU Lesser General Public
//    License as published by the Free Software Foundation; either
//    version 2.1 of the License, or (at your option) any later version.
//
//    This library is distributed in the hope that it will be useful,
//    but WITHOUT ANY WARRANTY; without even the implied warranty of
//    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
//    Lesser General Public License for more details.
//
//    You should have received a copy of the GNU Lesser General Public
//    License along with this library; if not, write to the Free Software
//    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
//
// Urwid web site: http://excess.org/urwid/

colours = new Object();
colours = {
    '0': "black",
    '1': "#c00000",
    '2': "green",
    '3': "#804000",
    '4': "#0000c0",
    '5': "#c000c0",
    '6': "teal",
    '7': "silver",
    '8': "gray",
    '9': "#ff6060",
    'A': "lime",
    'B': "yellow",
    'C': "#8080ff",
    'D': "#ff40ff",
    'E': "aqua",
    'F': "white"
};

keycodes = new Object();
keycodes = {
    8: "backspace", 9: "tab", 13: "enter", 27: "esc",
    33: "page up", 34: "page down", 35: "end", 36: "home",
    37: "left", 38: "up", 39: "right", 40: "down",
    45: "insert", 46: "delete",
    112: "f1", 113: "f2", 114: "f3", 115: "f4", 
    116: "f5", 117: "f6", 118: "f7", 119: "f8", 
    120: "f9", 121: "f10", 122: "f11", 123: "f12"
    };

var conn = null;
var char_width = null;
var char_height = null;
var screen_x = null;
var screen_y = null;

var urwid_id = null;
var send_conn = null;
var send_queue_max = 32;
var send_queue = new Array(send_queue_max);
var send_queue_in = 0;
var send_queue_out = 0;

var check_font_delay = 1000;
var send_more_delay = 100;
var poll_again_delay = 500;

var document_location = null;

var update_method = "multipart";

var sending = false;
var lastkeydown = null;

function setup_connection() {
    if (window.XMLHttpRequest) {
        conn = new XMLHttpRequest();
    } else if (window.ActiveXObject) {
        conn = new ActiveXObject("Microsoft.XMLHTTP");
    }

    if (conn == null) {
        set_status("Connection Failed");
        alert( "Can't figure out how to send request." );
        return;
    }
    try{
        conn.multipart = true;
    }catch(e){
        update_method = "polling";
    }
    conn.onreadystatechange = handle_recv;
    conn.open("POST", document_location, true);
    conn.setRequestHeader("X-Urwid-Method",update_method);
    conn.setRequestHeader("Content-type","text/plain");
    conn.send("window resize " +screen_x+" "+screen_y+"\n");
}

function do_poll() {
    if (urwid_id == null){
        alert("that's unpossible!");
        return;
    }
    if (window.XMLHttpRequest) {
        conn = new XMLHttpRequest();
    } else if (window.ActiveXObject) {
        conn = new ActiveXObject("Microsoft.XMLHTTP");
    }
    conn.onreadystatechange = handle_recv;
    conn.open("POST", document_location, true);
    conn.setRequestHeader("X-Urwid-Method","polling");
    conn.setRequestHeader("X-Urwid-ID",urwid_id);
    conn.setRequestHeader("Content-type","text/plain");
    conn.send("eh?");
}

function handle_recv() {
    if( ! conn ){ return;}
    if( conn.readyState != 4) {
        return;
    }
    if( conn.status == 404 && urwid_id != null) {
        set_status("Connection Closed");
        return;
    }
    if( conn.status == 403 && update_method == "polling" ) {
        set_status("Server Refused Connection");
        alert("This server does not allow polling clients.\n\n" +
            "Please use a web browser with multipart support " +
            "such as Mozilla Firefox");
        return;
    }
    if( conn.status == 503 ) {
        set_status("Connection Failed");
        alert("The server has reached its maximum number of "+
            "connections.\n\nPlease try again later.");
        return;
    }
    if( conn.status != 200) {
        set_status("Connection Failed");
        alert("Error from server: "+conn.statusText);
        return;
    }
    if( urwid_id == null ){
        urwid_id = conn.getResponseHeader("X-Urwid-ID");
        if( send_queue_in != send_queue_out ){
            // keys waiting
            do_send(); 
        }
        if(update_method=="polling"){
            set_status("Polling");
        }else if(update_method=="multipart"){
            set_status("Connected");
        }
    
    }
    
    if( conn.responseText == "" ){
        if(update_method=="polling"){
            poll_again();
        }
        return; // keepalive
    }
    if( conn.responseText == "Z" ){
        set_status("Connection Closed");
        update_method = null;
        return;
    }
    
    var text = document.getElementById('text');
    
    var last_screen = Array(text.childNodes.length);
    for( var i=0; i<text.childNodes.length; i++ ){
        last_screen[i] = text.childNodes[i];
    }
    
    var frags = conn.responseText.split("\n");
    var ln = document.createElement('span');
    var k = 0;
    for( var i=0; i<frags.length; i++ ){
        var f = frags[i];
        if( f == "" ){
            var br = document.getElementById('br').cloneNode(true);
            ln.appendChild( br );
            if( text.childNodes.length > k ){
                text.replaceChild(ln, text.childNodes[k]);
            }else{
                text.appendChild(ln);
            }
            k = k+1;
            ln = document.createElement('span');
        }else if( f.charAt(0) == "<" ){
            line_number = parseInt(f.substr(1));
            if( line_number == k ){
                k = k +1;
                continue;
            }
            var clone = last_screen[line_number].cloneNode(true);
            if( text.childNodes.length > k ){
                text.replaceChild(clone, text.childNodes[k]);
            }else{
                text.appendChild(clone);
            }
            k = k+1;
        }else{
            var span=make_span(f.substr(2),f.charAt(0),f.charAt(1));
            ln.appendChild( span );
        }
    }
    for( var i=k; i < text.childNodes.length; i++ ){
        text.removeChild(last_screen[i]);
    }
    
    if(update_method=="polling"){
        poll_again();
    }
}

function poll_again(){
    if(conn.status == 200){
        setTimeout("do_poll();",poll_again_delay);
    }
}


function load_web_display(){
    if( document.documentURI ){
        document_location = document.documentURI;
    }else{
        document_location = document.location;
    }
    
    document.onkeypress = body_keypress;
    document.onkeydown = body_keydown;
    document.onresize = body_resize;
    
    body_resize();
    send_queue_out = send_queue_in; // don't queue the first resize

    set_status("Connecting");
    setup_connection();
    
    setTimeout("check_fontsize();",check_font_delay);
}

function set_status( status ){
    var s = document.getElementById('status');
    var t = document.createTextNode(status);
    s.replaceChild(t, s.firstChild);
}

function make_span(s, fg, bg){
    d = document.createElement('span');
    d.style.backgroundColor = colours[bg];
    d.style.color = colours[fg];
    d.appendChild(document.createTextNode(s));
    
    return d;
}

function body_keydown(e){
    if (conn == null){
        return;
    }
    if (!e) var e = window.event;
    if (e.keyCode) code = e.keyCode;
    else if (e.which) code = e.which;

    var mod = "";
    var key;

    if( e.ctrlKey ){ mod = "ctrl " + mod; }
    if( e.altKey || e.metaKey ){ mod = "meta " + mod; }
    if( e.shiftKey && e.charCode == 0 ){ mod = "shift " + mod; }

    key = keycodes[code];
    
    if( key != undefined ){
        lastkeydown = key;
        send_key( mod + key );
        stop_key_event(e);
        return false;
    }
}

function body_keypress(e){
    if (conn == null){
        return;
    }

    if (!e) var e = window.event;
    if (e.keyCode) code = e.keyCode;
    else if (e.which) code = e.which;

    var mod = "";
    var key;

    if( e.ctrlKey ){ mod = "ctrl " + mod; }
    if( e.altKey || e.metaKey ){ mod = "meta " + mod; }
    if( e.shiftKey && e.charCode == 0 ){ mod = "shift " + mod; }
    
    if( e.charCode != null && e.charCode != 0 ){
        key = String.fromCharCode(e.charCode);
    }else if( e.charCode == null ){
        key = String.fromCharCode(code);
    }else{
        key = keycodes[code];
        if( key == undefined || lastkeydown == key ){
            lastkeydown = null;
            stop_key_event(e);
            return false;
        }
    }
    
    send_key( mod + key );
    stop_key_event(e);
    return false;
}

function stop_key_event(e){
    e.cancelBubble = true;
    if( e.stopPropagation ){
        e.stopPropagation();
    }
    if( e.preventDefault  ){
        e.preventDefault();
    }
}

function send_key( key ){
    if( (send_queue_in+1)%send_queue_max == send_queue_out ){
        // buffer overrun
        return;
    }
    send_queue[send_queue_in] = key;
    send_queue_in = (send_queue_in+1)%send_queue_max;

    if( urwid_id != null ){
        if (send_conn == undefined || send_conn.ready_state != 4 ){
            send_more();
            return;
        }
        do_send();
    }
}

function do_send() {
    if( ! urwid_id ){ return; }
    if( ! update_method ){ return; } // connection closed
    if( send_queue_in == send_queue_out ){ return; }
    if( sending ){ 
        //var queue_delta = send_queue_in - send_queue_out;
        //if( queue_delta < 0 ){ queue_delta += send_queue_max; }
        //set_status("Sending (queued "+queue_delta+")"); 
        return; 
    }
    try{
        sending = true;
        //set_status("starting send");
        if( send_conn == null ){
            if (window.XMLHttpRequest) {
                send_conn = new XMLHttpRequest();
            } else if (window.ActiveXObject) {
                send_conn = new ActiveXObject("Microsoft.XMLHTTP");
            }
        }else if( send_conn.status != 200) {
            alert("Error from server: "+send_conn.statusText);
            return;
        }else if(send_conn.readyState != 4 ){
            alert("not ready on send connection");
            return;
        }
    } catch(e) {
        alert(e);
        sending = false;
        return;
    }
    send_conn.open("POST", document_location, true);
    send_conn.onreadystatechange = send_handle_recv;
    send_conn.setRequestHeader("Content-type","text/plain");
    send_conn.setRequestHeader("X-Urwid-ID",urwid_id);
    var tmp_send_queue_in = send_queue_in;
    var out = null;
    if( send_queue_out > tmp_send_queue_in ){
        out = send_queue.slice(send_queue_out).join("\n")
        if( tmp_send_queue_in > 0 ){
            out += "\n"  + send_queue.slice(0,tmp_send_queue_in).join("\n");
        }
    }else{
        out = send_queue.slice(send_queue_out,
             tmp_send_queue_in).join("\n");
    }
    send_queue_out = tmp_send_queue_in;
    //set_status("Sending");
    send_conn.send( out +"\n" );
}

function send_handle_recv() {
    if( send_conn.readyState != 4) {
        return;
    }
    if( send_conn.status == 404) {
        set_status("Connection Closed");
        update_method = null;
        return;
    }
    if( send_conn.status != 200) {
        alert("Error from server: "+send_conn.statusText);
        return;
    }
    
    sending = false;
    
    if( send_queue_out != send_queue_in ){
        send_more();
    }
}

function send_more(){
    setTimeout("do_send();",send_more_delay);
}

function check_fontsize(){
    body_resize()
    setTimeout("check_fontsize();",check_font_delay);
}

function body_resize(){
    var t = document.getElementById('testchar');
    var t2 = document.getElementById('testchar2');
    var text = document.getElementById('text');

    var window_width;
    var window_height;
    if (window.innerHeight) {
        window_width = window.innerWidth;
        window_height = window.innerHeight;
    }else{
        window_width = document.documentElement.clientWidth;
        window_height = document.documentElement.clientHeight;
        //var z = "CI:"; for(var i in bod){z = z + " " + i;} alert(z);
    }

    char_width = t.offsetLeft / 44;
    var avail_width = window_width-18;
    var avail_width_mod = avail_width % char_width;
    var x_size = (avail_width - avail_width_mod)/char_width;
    
    char_height = t2.offsetTop - t.offsetTop;
    var avail_height = window_height-text.offsetTop-10;
    var avail_height_mod = avail_height % char_height;
    var y_size = (avail_height - avail_height_mod)/char_height;
    
    text.style.width = x_size*char_width+"px";
    text.style.height = y_size*char_height+"px";

    if( screen_x != x_size || screen_y != y_size ){
        send_key("window resize "+x_size+" "+y_size);
    }
    screen_x = x_size;
    screen_y = y_size;
}

"""

ALARM_DELAY = 60
POLL_CONNECT = 3
MAX_COLS = 200
MAX_ROWS = 100
MAX_READ = 4096
BUF_SZ = 16384

_code_colours = {
    'black':        "0",
    'dark red':        "1",
    'dark green':        "2",
    'brown':        "3",
    'dark blue':        "4",
    'dark magenta':        "5",
    'dark cyan':        "6",
    'light gray':        "7",
    'dark gray':        "8",
    'light red':        "9",
    'light green':        "A",
    'yellow':        "B",
    'light blue':        "C",
    'light magenta':    "D",
    'light cyan':        "E",
    'white':        "F",
}

# replace control characters with ?'s
_trans_table = "?" * 32 + "".join([chr(x) for x in range(32, 256)])

_css_style = """
body {    margin: 8px 8px 8px 8px; border: 0; 
    color: black; background-color: silver;
    font-family: fixed; overflow: hidden; }

form { margin: 0 0 8px 0; }

#text { position: relative;
    background-color: silver;
    width: 100%; height: 100%;
    margin: 3px 0 0 0; border: 1px solid #999; }

#page { position: relative;  width: 100%;height: 100%;}
"""

# HTML Initial Page
_html_page = [
"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
 "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<title>Urwid Web Display - ""","""</title>
<style type="text/css">
""" + _css_style + """
</style>
</head>
<body id="body" onload="load_web_display()">
<div style="position:absolute; visibility:hidden;">
<br id="br"\> 
<pre>The quick brown fox jumps over the lazy dog.<span id="testchar">X</span>
<span id="testchar2">Y</span></pre>
</div>
Urwid Web Display - <b>""","""</b> -
Status: <span id="status">Set up</span>
<script type="text/javascript">
//<![CDATA[
""" + _js_code +"""
//]]>
</script>
<pre id="text"></pre>
</body>
</html>
"""]

class Screen:
    def __init__(self):
        self.palette = {}
        self.has_color = True
        self._started = False
    
    started = property(lambda self: self._started)
    
    def register_palette( self, l ):
        """Register a list of palette entries.

        l -- list of (name, foreground, background) or
             (name, same_as_other_name) palette entries.

        calls self.register_palette_entry for each item in l
        """
        
        for item in l:
            if len(item) in (3,4):
                self.register_palette_entry( *item )
                continue
            assert len(item) == 2, "Invalid register_palette usage"
            name, like_name = item
            if not self.palette.has_key(like_name):
                raise Exception("palette entry '%s' doesn't exist"%like_name)
            self.palette[name] = self.palette[like_name]

    def register_palette_entry( self, name, foreground, background, 
        mono=None):
        """Register a single palette entry.

        name -- new entry/attribute name
        foreground -- foreground colour
        background -- background colour
        mono -- monochrome terminal attribute

        See curses_display.register_palette_entry for more info.
        """
        if foreground == "default":
            foreground = "black"
        if background == "default":
            background = "light gray"
        self.palette[name] = (foreground, background, mono)

    def set_mouse_tracking(self):
        """Not yet implemented"""
        pass

    def tty_signal_keys(self, *args, **vargs):
        """Do nothing."""
        pass

    def start(self):
        """    
        This function reads the initial screen size, generates a
        unique id and handles cleanup when fn exits.
        
        web_display.set_preferences(..) must be called before calling
        this function for the preferences to take effect
        """
        global _prefs

        assert not self._started
        
        client_init = sys.stdin.read(50)
        assert client_init.startswith("window resize "),client_init
        ignore1,ignore2,x,y = client_init.split(" ",3)
        x = int(x)
        y = int(y)
        self._set_screen_size( x, y )
        self.last_screen = {}
        self.last_screen_width = 0
    
        self.update_method = os.environ["HTTP_X_URWID_METHOD"]
        assert self.update_method in ("multipart","polling")
    
        if self.update_method == "polling" and not _prefs.allow_polling:
            sys.stdout.write("Status: 403 Forbidden\r\n\r\n")
            sys.exit(0)
        
        clients = glob.glob(os.path.join(_prefs.pipe_dir,"urwid*.in"))
        if len(clients) >= _prefs.max_clients:
            sys.stdout.write("Status: 503 Sever Busy\r\n\r\n")
            sys.exit(0)
        
        urwid_id = "%09d%09d"%(random.randrange(10**9),
            random.randrange(10**9))
        self.pipe_name = os.path.join(_prefs.pipe_dir,"urwid"+urwid_id)
        os.mkfifo(self.pipe_name+".in",0600)
        signal.signal(signal.SIGTERM,self._cleanup_pipe)
        
        self.input_fd = os.open(self.pipe_name+".in", 
            os.O_NONBLOCK | os.O_RDONLY)
        self.input_tail = ""
        self.content_head = ("Content-type: "
            "multipart/x-mixed-replace;boundary=ZZ\r\n"
            "X-Urwid-ID: "+urwid_id+"\r\n"
            "\r\n\r\n"
            "--ZZ\r\n")
        if self.update_method=="polling":
            self.content_head = (
                "Content-type: text/plain\r\n"
                "X-Urwid-ID: "+urwid_id+"\r\n"
                "\r\n\r\n")
        
        signal.signal(signal.SIGALRM,self._handle_alarm)
        signal.alarm( ALARM_DELAY )
        self._started = True

    def stop(self):
        """
        Restore settings and clean up.  
        """
        assert self._started
        try:
            self._close_connection()
        except:
            pass
        signal.signal(signal.SIGTERM,signal.SIG_DFL)
        self._cleanup_pipe()
        self._started = False
        
    def set_input_timeouts(self, *args):
        pass

    def run_wrapper(self,fn):
        """
        Run the application main loop, calling start() first
        and stop() on exit.
        """
        try:
            self.start()
            return fn()
        finally:
            self.stop()
            

    def _close_connection(self):
        if self.update_method == "polling child":
            self.server_socket.settimeout(0)
            socket, addr = self.server_socket.accept()
            socket.sendall("Z")
            socket.close()
        
        if self.update_method == "multipart":
            sys.stdout.write("\r\nZ"
                "\r\n--ZZ--\r\n")
            sys.stdout.flush()
                
    def _cleanup_pipe(self, *args):
        if not self.pipe_name: return
        try:
            os.remove(self.pipe_name+".in")
            os.remove(self.pipe_name+".update")
        except:
            pass

    def _set_screen_size(self, cols, rows ):
        """Set the screen size (within max size)."""
        
        if cols > MAX_COLS:
            cols = MAX_COLS
        if rows > MAX_ROWS:
            rows = MAX_ROWS
        self.screen_size = cols, rows
        
    def draw_screen(self, (cols, rows), r ):
        """Send a screen update to the client."""
        
        if cols != self.last_screen_width:
            self.last_screen = {}
    
        sendq = [self.content_head]
        
        if self.update_method == "polling":
            send = sendq.append
        elif self.update_method == "polling child":
            signal.alarm( 0 )
            try:
                s, addr = self.server_socket.accept()
            except socket.timeout, e:
                sys.exit(0)
            send = s.sendall
        else:
            signal.alarm( 0 )
            send = sendq.append
            send("\r\n")
            self.content_head = ""
        
        assert r.rows() == rows
    
        if r.cursor is not None:
            cx, cy = r.cursor
        else:
            cx = cy = None
        
        new_screen = {}
        
        y = -1
        for row in r.content():
            y += 1
            row = list(row)
            
            l = []
            
            sig = tuple(row)
            if y == cy: sig = sig + (cx,)
            new_screen[sig] = new_screen.get(sig,[]) + [y]
            old_line_numbers = self.last_screen.get(sig, None)
            if old_line_numbers is not None:
                if y in old_line_numbers:
                    old_line = y
                else:
                    old_line = old_line_numbers[0]
                send( "<%d\n"%old_line )
                continue
            
            col = 0
            for (a, cs, run) in row:
                run = run.translate(_trans_table)
                if a is None:
                    fg,bg,mono = "black", "light gray", None
                else:
                    fg,bg,mono = self.palette[a]
                if y == cy and col <= cx:
                    run_width = util.calc_width(run, 0, 
                        len(run))
                    if col+run_width > cx:
                        l.append(code_span(run, fg, bg,
                            cx-col))
                    else:
                        l.append(code_span(run, fg, bg))
                    col += run_width
                else:
                    l.append(code_span(run, fg, bg))

            send("".join(l)+"\n")
        self.last_screen = new_screen
        self.last_screen_width = cols
        
        if self.update_method == "polling":
            sys.stdout.write("".join(sendq))
            sys.stdout.flush()
            sys.stdout.close()
            self._fork_child()
        elif self.update_method == "polling child":
            s.close()
        else: # update_method == "multipart"
            send("\r\n--ZZ\r\n")
            sys.stdout.write("".join(sendq))
            sys.stdout.flush()
        
        signal.alarm( ALARM_DELAY )
    

    def clear(self):
        """
        Force the screen to be completely repainted on the next
        call to draw_screen().

        (does nothing for web_display)
        """
        pass


    def _fork_child(self):
        """
        Fork a child to run CGI disconnected for polling update method.
        Force parent process to exit.
        """
        daemonize( self.pipe_name +".err" )
        self.input_fd = os.open(self.pipe_name+".in", 
            os.O_NONBLOCK | os.O_RDONLY)
        self.update_method = "polling child"
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.bind( self.pipe_name+".update" )
        s.listen(1)
        s.settimeout(POLL_CONNECT)
        self.server_socket = s
    
    def _handle_alarm(self, sig, frame):
        assert self.update_method in ("multipart","polling child")
        if self.update_method == "polling child":
            # send empty update
            try:
                s, addr = self.server_socket.accept()
                s.close()
            except socket.timeout, e:
                sys.exit(0)
        else:
            # send empty update
            sys.stdout.write("\r\n\r\n--ZZ\r\n")
            sys.stdout.flush()
        signal.alarm( ALARM_DELAY )
        
            
    def get_cols_rows(self):
        """Return the screen size."""
        return self.screen_size

    def get_input(self, raw_keys=False):
        """Return pending input as a list."""
        l = []
        resized = False
        
        try:
            iready,oready,eready = select.select(
                [self.input_fd],[],[],0.5)
        except select.error, e:
            # return on interruptions
            if e.args[0] == 4: 
                if raw_keys:
                    return [],[]
                return []
            raise

        if not iready:
            if raw_keys:
                return [],[]
            return []
        
        keydata = os.read(self.input_fd, MAX_READ)
        os.close(self.input_fd)
        self.input_fd = os.open(self.pipe_name+".in", 
            os.O_NONBLOCK | os.O_RDONLY)
        #sys.stderr.write( `keydata,self.input_tail`+"\n" )
        keys = keydata.split("\n")
        keys[0] = self.input_tail + keys[0]
        self.input_tail = keys[-1]
        
        for k in keys[:-1]:
            if k.startswith("window resize "):
                ign1,ign2,x,y = k.split(" ",3)
                x = int(x)
                y = int(y)
                self._set_screen_size(x, y)
                resized = True
            else:
                l.append(k)
        if resized:
            l.append("window resize")
        
        if raw_keys:
            return l, []
        return l
    

def code_span( s, fg, bg, cursor = -1):
    code_fg = _code_colours[ fg ]
    code_bg = _code_colours[ bg ]
    
    if cursor >= 0:
        c_off, _ign = util.calc_text_pos(s, 0, len(s), cursor)
        c2_off = util.move_next_char(s, c_off, len(s))

        return ( code_fg + code_bg + s[:c_off] + "\n" +
             code_bg + code_fg + s[c_off:c2_off] + "\n" +
             code_fg + code_bg + s[c2_off:] + "\n")
    else:
        return code_fg + code_bg + s + "\n"


def html_escape(text):
    """Escape text so that it will be displayed safely within HTML"""
    text = text.replace('&','&amp;')
    text = text.replace('<','&lt;')
    text = text.replace('>','&gt;')
    return text

    
def is_web_request():
    """
    Return True if this is a CGI web request.
    """
    return os.environ.has_key('REQUEST_METHOD')

def handle_short_request():
    """
    Handle short requests such as passing keystrokes to the application
    or sending the initial html page.  If returns True, then this
    function recognised and handled a short request, and the calling
    script should immediately exit.

    web_display.set_preferences(..) should be called before calling this
    function for the preferences to take effect
    """
    global _prefs
    
    if not is_web_request():
        return False
        
    if os.environ['REQUEST_METHOD'] == "GET":
        # Initial request, send the HTML and javascript.
        sys.stdout.write("Content-type: text/html\r\n\r\n" +
            html_escape(_prefs.app_name).join(_html_page))
        return True
    
    if os.environ['REQUEST_METHOD'] != "POST":
        # Don't know what to do with head requests etc.
        return False
    
    if not os.environ.has_key('HTTP_X_URWID_ID'):
        # If no urwid id, then the application should be started.
        return False

    urwid_id = os.environ['HTTP_X_URWID_ID']
    if len(urwid_id)>20:
        #invalid. handle by ignoring
        #assert 0, "urwid id too long!"
        sys.stdout.write("Status: 414 URI Too Long\r\n\r\n")
        return True
    for c in urwid_id:
        if c not in "0123456789":
            # invald. handle by ignoring
            #assert 0, "invalid chars in id!"
            sys.stdout.write("Status: 403 Forbidden\r\n\r\n")
            return True
    
    if os.environ.get('HTTP_X_URWID_METHOD',None) == "polling":
        # this is a screen update request
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            s.connect( os.path.join(_prefs.pipe_dir,
                "urwid"+urwid_id+".update") )
            data = "Content-type: text/plain\r\n\r\n"+s.recv(BUF_SZ)
            while data:
                sys.stdout.write(data)
                data = s.recv(BUF_SZ)
            return True
        except socket.error,e:
            sys.stdout.write("Status: 404 Not Found\r\n\r\n")
            return True
        
        
    
    # this is a keyboard input request
    try:
        fd = os.open((os.path.join(_prefs.pipe_dir,
            "urwid"+urwid_id+".in")), os.O_WRONLY)
    except OSError,e:
        sys.stdout.write("Status: 404 Not Found\r\n\r\n")
        return True
        
    keydata = sys.stdin.read(MAX_READ)
    os.write(fd,keydata)
    os.close(fd)
    sys.stdout.write("Content-type: text/plain\r\n\r\n")
    
    return True


class _Preferences:
    app_name = "Unnamed Application"
    pipe_dir = "/tmp"
    allow_polling = True
    max_clients = 20

_prefs = _Preferences()

def set_preferences( app_name, pipe_dir="/tmp", allow_polling=True, 
    max_clients=20 ):
    """
    Set web_display preferences.
    
    app_name -- application name to appear in html interface
    pipe_dir -- directory for input pipes, daemon update sockets 
                and daemon error logs
    allow_polling -- allow creation of daemon processes for 
                     browsers without multipart support 
    max_clients -- maximum concurrent client connections. This
               pool is shared by all urwid applications
               using the same pipe_dir
    """
    global _prefs
    _prefs.app_name = app_name
    _prefs.pipe_dir = pipe_dir
    _prefs.allow_polling = allow_polling
    _prefs.max_clients = max_clients


class ErrorLog:
    def __init__(self, errfile ):
        self.errfile = errfile
    def write(self, err):
        open(self.errfile,"a").write(err)


def daemonize( errfile ):
    """
    Detach process and become a daemon.
    """
    pid = os.fork()
    if pid:
        os._exit(0)

    os.setsid()
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    os.umask(0)

    pid = os.fork()
    if pid:
        os._exit(0)

    os.chdir("/")
    for fd in range(0,20):
        try:
            os.close(fd)
        except OSError:
            pass

    sys.stdin = open("/dev/null","r")
    sys.stdout = open("/dev/null","w")
    sys.stderr = ErrorLog( errfile )


########NEW FILE########
__FILENAME__ = widget
#!/usr/bin/python
#
# Urwid basic widget classes
#    Copyright (C) 2004-2007  Ian Ward
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

from util import *
import signals
import text_layout
from canvas import *
from monitored_list import MonitoredList
from command_map import command_map
from signals import connect_signal, connect_signal, disconnect_signal
from split_repr import split_repr, remove_defaults

try: sum # old python?
except: sum = lambda l: reduce(lambda a,b: a+b, l, 0)

try: set
except: set = list # not perfect, but should be good enough for python2.2


# Widget sizing methods
# (use the same string objects to make some comparisons faster)
FLOW = 'flow'
BOX = 'box'
FIXED = 'fixed'

# Text alignment modes 
LEFT = 'left'
RIGHT = 'right'
CENTER = 'center'

# Filler alignment modes 
TOP = 'top'
MIDDLE = 'middle'
BOTTOM = 'bottom'

# Text wrapping modes
SPACE = 'space'
ANY = 'any'
CLIP = 'clip'

# Extras for Padding
PACK = 'pack'
GIVEN = 'given'
RELATIVE = 'relative'
RELATIVE_100 = (RELATIVE, 100)
CLIP = 'clip'


class WidgetMeta(MetaSuper, signals.MetaSignals):
    """
    Automatic caching of render and rows methods.

    Class variable no_cache is a list of names of methods to not cache.
    Class variable ignore_focus if defined and True indicates that this
    widget is not affected by the focus parameter, so it may be ignored
    when caching.
    """
    def __init__(cls, name, bases, d):
        no_cache = d.get("no_cache", [])
        
        super(WidgetMeta, cls).__init__(name, bases, d)

        if "render" in d:
            if "render" not in no_cache:
                render_fn = cache_widget_render(cls)
            else:
                render_fn = nocache_widget_render(cls)
            cls.render = render_fn

        if "rows" in d and "rows" not in no_cache:
            cls.rows = cache_widget_rows(cls)
        if "no_cache" in d:
            del cls.no_cache
        if "ignore_focus" in d:
            del cls.ignore_focus

class WidgetError(Exception):
    pass

def validate_size(widget, size, canv):
    """
    Raise a WidgetError if a canv does not match size size.
    """
    if (size and size[1:] != (0,) and size[0] != canv.cols()) or \
        (len(size)>1 and size[1] != canv.rows()):
        raise WidgetError("Widget %r rendered (%d x %d) canvas"
            " when passed size %r!" % (widget, canv.cols(),
            canv.rows(), size))

def update_wrapper(new_fn, fn):
    """
    Copy as much of the function detail from fn to new_fn
    as we can.
    """
    try:
        new_fn.__name__ = fn.__name__
        new_fn.__dict__.update(fn.__dict__)
        new_fn.__doc__ = fn.__doc__
        new_fn.__module__ = fn.__module__
    except TypeError:
        pass # python2.3 ignore read-only attributes


def cache_widget_render(cls):
    """
    Return a function that wraps the cls.render() method
    and fetches and stores canvases with CanvasCache.
    """
    ignore_focus = bool(getattr(cls, "ignore_focus", False))
    fn = cls.render
    def cached_render(self, size, focus=False):
        focus = focus and not ignore_focus
        canv = CanvasCache.fetch(self, cls, size, focus)
        if canv:
            return canv

        canv = fn(self, size, focus=focus)
        validate_size(self, size, canv)
        if canv.widget_info:
            canv = CompositeCanvas(canv)
        canv.finalize(self, size, focus)
        CanvasCache.store(cls, canv)
        return canv
    cached_render.original_fn = fn
    update_wrapper(cached_render, fn)
    return cached_render

def nocache_widget_render(cls):
    """
    Return a function that wraps the cls.render() method
    and finalizes the canvas that it returns.
    """
    fn = cls.render
    if hasattr(fn, "original_fn"):
        fn = fn.original_fn
    def finalize_render(self, size, focus=False):
        canv = fn(self, size, focus=focus)
        if canv.widget_info:
            canv = CompositeCanvas(canv)
        validate_size(self, size, canv)
        canv.finalize(self, size, focus)
        return canv
    finalize_render.original_fn = fn
    update_wrapper(finalize_render, fn)
    return finalize_render

def nocache_widget_render_instance(self):
    """
    Return a function that wraps the cls.render() method
    and finalizes the canvas that it returns, but does not 
    cache the canvas.
    """
    fn = self.render.original_fn
    def finalize_render(size, focus=False):
        canv = fn(self, size, focus=focus)
        if canv.widget_info:
            canv = CompositeCanvas(canv)
        canv.finalize(self, size, focus)
        return canv
    finalize_render.original_fn = fn
    update_wrapper(finalize_render, fn)
    return finalize_render

def cache_widget_rows(cls):
    """
    Return a function that wraps the cls.rows() method
    and returns rows from the CanvasCache if available.
    """
    ignore_focus = bool(getattr(cls, "ignore_focus", False))
    fn = cls.rows
    def cached_rows(self, size, focus=False):
        focus = focus and not ignore_focus
        canv = CanvasCache.fetch(self, cls, size, focus)
        if canv:
            return canv.rows()

        return fn(self, size, focus)
    update_wrapper(cached_rows, fn)
    return cached_rows


class Widget(object):
    """
    base class of widgets
    """
    __metaclass__ = WidgetMeta
    _selectable = False
    _sizing = set([])

    def _invalidate(self):
        CanvasCache.invalidate(self)

    def _emit(self, name, *args):
        """
        Convenience function to emit signals with self as first
        argument.
        """
        signals.emit_signal(self, name, self, *args)
    
    def selectable(self):
        """
        Return True if this widget should take focus.  Default
        implementation returns the value of self._selectable.
        """
        return self._selectable
    
    def sizing(self):
        """
        Return a set including one or more of 'box', 'flow' and
        'fixed'.  Default implementation returns the value of
        self._sizing.
        """
        return self._sizing

    def pack(self, size, focus=False):
        """
        Return a 'packed' (maxcol, maxrow) for this widget.  Default 
        implementation (no packing defined) returns size, and
        calculates maxrow if not given.
        """
        if size == ():
            if FIXED in self.sizing():
                raise NotImplementedError('Fixed widgets must override'
                    ' Widget.size()')
            raise WidgetError('Cannot pack () size, this is not a fixed'
                ' widget: %s' % repr(self))
        elif len(size) == 1:
            if FLOW in self.sizing():
                return size + (self.rows(size, focus),)
            raise WidgetError('Cannot pack (maxcol,) size, this is not a'
                ' flow widget: %s' % repr(self))
        return size

    # this property returns the widget without any decorations, default
    # implementation returns self.
    base_widget = property(lambda self:self)
    

    # Use the split_repr module to create __repr__ from _repr_words
    # and _repr_attrs
    __repr__ = split_repr

    def _repr_words(self):
        words = []
        if self.selectable():
            words = ["selectable"] + words
        if self.sizing():
            sizing_modes = list(self.sizing())
            sizing_modes.sort()
            words.append("/".join(sizing_modes))
        return words + ["widget"]

    def _repr_attrs(self):
        return {}
    

class FlowWidget(Widget):
    """
    base class of widgets that determine their rows from the number of
    columns available.
    """
    _sizing = set([FLOW])
    
    def rows(self, size, focus=False):
        """
        All flow widgets must implement this function.
        """
        raise NotImplementedError()

    def render(self, size, focus=False):
        """
        All widgets must implement this function.
        """
        raise NotImplementedError()


class BoxWidget(Widget):
    """
    base class of width and height constrained widgets such as
    the top level widget attached to the display object
    """
    _selectable = True
    _sizing = set([BOX])
    
    def render(self, size, focus=False):
        """
        All widgets must implement this function.
        """
        raise NotImplementedError()
    

def fixed_size(size):
    """
    raise ValueError if size != ().
    
    Used by FixedWidgets to test size parameter.
    """
    if size != ():
        raise ValueError("FixedWidget takes only () for size." \
            "passed: %s" % `size`)

class FixedWidget(Widget):
    """
    base class of widgets that know their width and height and
    cannot be resized
    """
    _sizing = set([FIXED])
    
    def render(self, size, focus=False):
        """
        All widgets must implement this function.
        """
        raise NotImplementedError()
    
    def pack(self, size=None, focus=False):
        """
        All fixed widgets must implement this function.
        """
        raise NotImplementedError()


class Divider(FlowWidget):
    """
    Horizontal divider widget
    """
    ignore_focus = True

    def __init__(self,div_char=" ",top=0,bottom=0):
        """
        Create a horizontal divider widget.
        
        div_char -- character to repeat across line
        top -- number of blank lines above
        bottom -- number of blank lines below

        >>> Divider()
        <Divider flow widget div_char=' '>
        >>> Divider('-')
        <Divider flow widget div_char='-'>
        >>> Divider('x', 1, 2)
        <Divider flow widget bottom=2 div_char='x' top=1>
        """
        self.__super.__init__()
        self.div_char = div_char
        self.top = top
        self.bottom = bottom
        
    def _repr_attrs(self):
        attrs = dict(self.__super._repr_attrs(),
            div_char=self.div_char)
        if self.top: attrs['top'] = self.top
        if self.bottom: attrs['bottom'] = self.bottom
        return attrs
    
    def rows(self, size, focus=False):
        """
        Return the number of lines that will be rendered.

        >>> Divider().rows((10,))
        1
        >>> Divider('x', 1, 2).rows((10,))
        4
        """
        (maxcol,) = size
        return self.top + 1 + self.bottom
    
    def render(self, size, focus=False):
        """
        Render the divider as a canvas and return it.
        
        >>> Divider().render((10,)).text 
        ['          ']
        >>> Divider('-', top=1).render((10,)).text
        ['          ', '----------']
        >>> Divider('x', bottom=2).render((5,)).text
        ['xxxxx', '     ', '     ']
        """
        (maxcol,) = size
        canv = SolidCanvas(self.div_char, maxcol, 1)
        canv = CompositeCanvas(canv)
        if self.top or self.bottom:
            canv.pad_trim_top_bottom(self.top, self.bottom)
        return canv
    

class SolidFill(BoxWidget):
    _selectable = False
    ignore_focus = True

    def __init__(self, fill_char=" "):
        """
        Create a box widget that will fill an area with a single 
        character.
        
        fill_char -- character to fill area with

        >>> SolidFill('8')
        <SolidFill box widget '8'>
        """
        self.__super.__init__()
        self.fill_char = fill_char
    
    def _repr_words(self):
        return self.__super._repr_words() + [repr(self.fill_char)]
    
    def render(self, size, focus=False ):
        """
        Render the Fill as a canvas and return it.

        >>> SolidFill().render((4,2)).text
        ['    ', '    ']
        >>> SolidFill('#').render((5,3)).text
        ['#####', '#####', '#####']
        """
        maxcol, maxrow = size
        return SolidCanvas(self.fill_char, maxcol, maxrow)
    
class TextError(Exception):
    pass

class Text(FlowWidget):
    """
    a horizontally resizeable text widget
    """
    ignore_focus = True

    def __init__(self, markup, align=LEFT, wrap=SPACE, layout=None):
        """
        markup -- content of text widget, one of:
            plain string -- string is displayed
            ( attr, markup2 ) -- markup2 is given attribute attr
            [ markupA, markupB, ... ] -- list items joined together
        align -- align mode for text layout
        wrap -- wrap mode for text layout
        layout -- layout object to use, defaults to StandardTextLayout

        >>> Text("Hello")
        <Text flow widget 'Hello'>
        >>> t = Text(('bold', "stuff"), 'right', 'any')
        >>> t
        <Text flow widget 'stuff' align='right' wrap='any'>
        >>> t.text
        'stuff'
        >>> t.attrib
        [('bold', 5)]
        """
        self.__super.__init__()
        self._cache_maxcol = None
        self.set_text(markup)
        self.set_layout(align, wrap, layout)
    
    def _repr_words(self):
        return self.__super._repr_words() + [
            repr(self.get_text()[0])]
    
    def _repr_attrs(self):
        attrs = dict(self.__super._repr_attrs(),
            align=self._align_mode, 
            wrap=self._wrap_mode)
        return remove_defaults(attrs, Text.__init__)
    
    def _invalidate(self):
        self._cache_maxcol = None
        self.__super._invalidate()

    def set_text(self,markup):
        """
        Set content of text widget.

        markup -- see __init__() for description.

        >>> t = Text("foo")
        >>> t.text
        'foo'
        >>> t.set_text("bar")
        >>> t.text
        'bar'
        >>> t.text = "baz"  # not supported because text stores text but set_text() takes markup
        Traceback (most recent call last):
            ...  
        AttributeError: can't set attribute
        """
        self._text, self._attrib = decompose_tagmarkup(markup)
        self._invalidate()

    def get_text(self):
        """
        Returns (text, attributes).
        
        text -- complete string content of text widget
        attributes -- run length encoded attributes for text

        >>> Text("Hello").get_text()
        ('Hello', [])
        >>> Text(('bright', "Headline")).get_text()
        ('Headline', [('bright', 8)])
        >>> Text([('a', "one"), "two", ('b', "three")]).get_text()
        ('onetwothree', [('a', 3), (None, 3), ('b', 5)])
        """
        return self._text, self._attrib

    text = property(lambda self:self.get_text()[0])
    attrib = property(lambda self:self.get_text()[1])

    def set_align_mode(self, mode):
        """
        Set text alignment / justification.  
        
        Valid modes for StandardTextLayout are: 
            'left', 'center' and 'right'

        >>> t = Text("word")
        >>> t.set_align_mode('right')
        >>> t.align
        'right'
        >>> t.render((10,)).text
        ['      word']
        >>> t.align = 'center'
        >>> t.render((10,)).text
        ['   word   ']
        >>> t.align = 'somewhere'
        Traceback (most recent call last):
            ...
        TextError: Alignment mode 'somewhere' not supported.
        """
        if not self.layout.supports_align_mode(mode):
            raise TextError("Alignment mode %s not supported."%
                `mode`)
        self._align_mode = mode
        self._invalidate()

    def set_wrap_mode(self, mode):
        """
        Set wrap mode.  
        
        Valid modes for StandardTextLayout are :
            'any'    : wrap at any character
            'space'    : wrap on space character
            'clip'    : truncate lines instead of wrapping
        
        >>> t = Text("some words")
        >>> t.render((6,)).text
        ['some  ', 'words ']
        >>> t.set_wrap_mode('clip')
        >>> t.wrap
        'clip'
        >>> t.render((6,)).text
        ['some w']
        >>> t.wrap = 'any'  # Urwid 0.9.9 or later
        >>> t.render((6,)).text
        ['some w', 'ords  ']
        >>> t.wrap = 'somehow'
        Traceback (most recent call last):
            ...
        TextError: Wrap mode 'somehow' not supported.
        """
        if not self.layout.supports_wrap_mode(mode):
            raise TextError("Wrap mode %s not supported."%`mode`)
        self._wrap_mode = mode
        self._invalidate()

    def set_layout(self, align, wrap, layout=None):
        """
        Set layout object, align and wrap modes.
        
        align -- align mode for text layout
        wrap -- wrap mode for text layout
        layout -- layout object to use, defaults to StandardTextLayout

        >>> t = Text("hi")
        >>> t.set_layout('right', 'clip')
        >>> t
        <Text flow widget 'hi' align='right' wrap='clip'>
        """
        if layout is None:
            layout = text_layout.default_layout
        self._layout = layout
        self.set_align_mode(align)
        self.set_wrap_mode(wrap)

    align = property(lambda self:self._align_mode, set_align_mode)
    wrap = property(lambda self:self._wrap_mode, set_wrap_mode)
    layout = property(lambda self:self._layout)

    def render(self, size, focus=False):
        """
        Render contents with wrapping and alignment.  Return canvas.

        >>> Text("important things").render((18,)).text
        ['important things  ']
        >>> Text("important things").render((11,)).text
        ['important  ', 'things     ']
        """
        (maxcol,) = size
        text, attr = self.get_text()
        trans = self.get_line_translation( maxcol, (text,attr) )
        return apply_text_layout(text, attr, trans, maxcol)

    def rows(self, size, focus=False):
        """
        Return the number of rows the rendered text spans.
        
        >>> Text("important things").rows((18,))
        1
        >>> Text("important things").rows((11,))
        2
        """
        (maxcol,) = size
        return len(self.get_line_translation(maxcol))

    def get_line_translation(self, maxcol, ta=None):
        """
        Return layout structure used to map self.text to a canvas.
        This method is used internally, but may be useful for
        debugging custom layout classes.

        maxcol -- columns available for display
        ta -- None or the (text, attr) tuple returned from
              self.get_text()
        """
        if not self._cache_maxcol or self._cache_maxcol != maxcol:
            self._update_cache_translation(maxcol, ta)
        return self._cache_translation

    def _update_cache_translation(self,maxcol, ta):
        if ta:
            text, attr = ta
        else:
            text, attr = self.get_text()
        self._cache_maxcol = maxcol
        self._cache_translation = self._calc_line_translation(
            text, maxcol )
    
    def _calc_line_translation(self, text, maxcol ):
        return self.layout.layout(
            text, self._cache_maxcol, 
            self._align_mode, self._wrap_mode )
    
    def pack(self, size=None, focus=False):
        """
        Return the number of screen columns and rows required for
        this Text widget to be displayed without wrapping or 
        clipping, as a single element tuple.

        size -- None for unlimited screen columns or (maxcol,) to
                specify a maximum column size

        >>> Text("important things").pack()
        (16, 1)
        >>> Text("important things").pack((15,))
        (9, 2)
        >>> Text("important things").pack((8,))
        (8, 2)
        """
        text, attr = self.get_text()
        
        if size is not None:
            (maxcol,) = size
            if not hasattr(self.layout, "pack"):
                return size
            trans = self.get_line_translation( maxcol, (text,attr))
            cols = self.layout.pack( maxcol, trans )
            return (cols, len(trans))
    
        i = 0
        cols = 0
        while i < len(text):
            j = text.find('\n', i)
            if j == -1:
                j = len(text)
            c = calc_width(text, i, j)
            if c>cols:
                cols = c
            i = j+1
        return (cols, text.count('\n') + 1)


class EditError(TextError):
    pass
            

class Edit(Text):
    """
    Text editing widget implements cursor movement, text insertion and 
    deletion.  A caption may prefix the editing area.  Uses text class 
    for text layout.
    """
    
    # allow users of this class to listen for change events
    # sent when the value of edit_text changes
    # (this variable is picked up by the MetaSignals metaclass)
    signals = ["change"]
    
    def valid_char(self, ch):
        """Return true for printable characters."""
        return is_wide_char(ch,0) or (len(ch)==1 and ord(ch) >= 32)
    
    def selectable(self): return True

    def __init__(self, caption="", edit_text="", multiline=False,
            align=LEFT, wrap=SPACE, allow_tab=False,
            edit_pos=None, layout=None):
        """
        caption -- markup for caption preceeding edit_text
        edit_text -- text string for editing
        multiline -- True: 'enter' inserts newline  False: return it
        align -- align mode
        wrap -- wrap mode
        allow_tab -- True: 'tab' inserts 1-8 spaces  False: return it
        edit_pos -- initial position for cursor, None:at end
        layout -- layout object

        >>> Edit()
        <Edit selectable flow widget '' edit_pos=0>
        >>> Edit("Y/n? ", "yes")
        <Edit selectable flow widget 'yes' caption='Y/n? ' edit_pos=3>
        >>> Edit("Name ", "Smith", edit_pos=1)
        <Edit selectable flow widget 'Smith' caption='Name ' edit_pos=1>
        >>> Edit("", "3.14", align='right')
        <Edit selectable flow widget '3.14' align='right' edit_pos=4>
        """
        
        self.__super.__init__("", align, wrap, layout)
        self.multiline = multiline
        self.allow_tab = allow_tab
        self._edit_pos = 0
        self.set_caption(caption)
        self.set_edit_text(edit_text)
        if edit_pos is None:
            edit_pos = len(edit_text)
        self.set_edit_pos(edit_pos)
        self._shift_view_to_cursor = False
    
    def _repr_words(self):
        return self.__super._repr_words()[:-1] + [
            repr(self._edit_text)] + [
            'multiline'] * (self.multiline is True)

    def _repr_attrs(self):
        attrs = dict(self.__super._repr_attrs(),
            edit_pos=self._edit_pos,
            caption=self._caption)
        return remove_defaults(attrs, Edit.__init__)
    
    def get_text(self):
        """
        Returns (text, attributes).
        
        text -- complete text of caption and edit_text
        attributes -- run length encoded attributes for text

        >>> Edit("What? ","oh, nothing.").get_text()
        ('What? oh, nothing.', [])
        >>> Edit(('bright',"user@host:~$ "),"ls").get_text()
        ('user@host:~$ ls', [('bright', 13)])
        """
        return self._caption + self._edit_text, self._attrib
    
    def set_text(self, markup):
        """
        Not supported by Edit widget.

        >>> Edit().set_text("test")
        Traceback (most recent call last):
            ...
        EditError: set_text() not supported.  Use set_caption() or set_edit_text() instead.
        """
        # hack to let Text.__init__() work
        if not hasattr(self, '_text') and markup == "":
            self._text = None
            return

        raise EditError("set_text() not supported.  Use set_caption()"
            " or set_edit_text() instead.")

    def get_pref_col(self, size):
        """
        Return the preferred column for the cursor, or the
        current cursor x value.  May also return 'left' or 'right'
        to indicate the leftmost or rightmost column available.

        This method is used internally and by other widgets when
        moving the cursor up or down between widgets so that the 
        column selected is one that the user would expect.

        >>> size = (10,)
        >>> Edit().get_pref_col(size)
        0
        >>> e = Edit("","word")
        >>> e.get_pref_col(size)
        4
        >>> e.keypress(size, 'left')
        >>> e.get_pref_col(size)
        3
        >>> e.keypress(size, 'end')
        >>> e.get_pref_col(size)
        'right'
        >>> e = Edit("","2\\nwords")
        >>> e.keypress(size, 'left')
        >>> e.keypress(size, 'up')
        >>> e.get_pref_col(size)
        4
        >>> e.keypress(size, 'left')
        >>> e.get_pref_col(size)
        0
        """
        (maxcol,) = size
        pref_col, then_maxcol = self.pref_col_maxcol
        if then_maxcol != maxcol:
            return self.get_cursor_coords((maxcol,))[0]
        else:
            return pref_col
    
    def update_text(self):
        """
        No longer supported.
        
        >>> Edit().update_text()
        Traceback (most recent call last):
            ...
        EditError: update_text() has been removed.  Use set_caption() or set_edit_text() instead.
        """
        raise EditError("update_text() has been removed.  Use "
            "set_caption() or set_edit_text() instead.")

    def set_caption(self, caption):
        """
        Set the caption markup for this widget.

        caption -- see Text.__init__() for description of markup
        
        >>> e = Edit("")
        >>> e.set_caption("cap1")
        >>> e.caption
        'cap1'
        >>> e.set_caption(('bold', "cap2"))
        >>> e.caption
        'cap2'
        >>> e.attrib
        [('bold', 4)]
        >>> e.caption = "cap3"  # not supported because caption stores text but set_caption() takes markup
        Traceback (most recent call last):
            ...  
        AttributeError: can't set attribute
        """
        self._caption, self._attrib = decompose_tagmarkup(caption)
        self._invalidate()
    
    caption = property(lambda self:self._caption)

    def set_edit_pos(self, pos):
        """
        Set the cursor position with a self.edit_text offset.  
        Clips pos to [0, len(edit_text)].

        >>> e = Edit("", "word")
        >>> e.edit_pos
        4
        >>> e.set_edit_pos(2)
        >>> e.edit_pos
        2
        >>> e.edit_pos = -1  # Urwid 0.9.9 or later
        >>> e.edit_pos
        0
        >>> e.edit_pos = 20
        >>> e.edit_pos
        4
        """
        if pos < 0:
            pos = 0
        if pos > len(self._edit_text):
            pos = len(self._edit_text)
        self.highlight = None
        self.pref_col_maxcol = None, None
        self._edit_pos = pos
        self._invalidate()
    
    edit_pos = property(lambda self:self._edit_pos, set_edit_pos)
    
    def set_edit_text(self, text):
        """
        Set the edit text for this widget.
        
        >>> e = Edit()
        >>> e.set_edit_text("yes")
        >>> e.edit_text
        'yes'
        >>> e
        <Edit selectable flow widget 'yes' edit_pos=0>
        >>> e.edit_text = "no"  # Urwid 0.9.9 or later
        >>> e.edit_text
        'no'
        """
        if type(text) not in (str, unicode):
            try:
                text = unicode(text)
            except:
                raise EditError("Can't convert edit text to a string!")
        self.highlight = None
        self._emit("change", text)
        self._edit_text = text
        if self.edit_pos > len(text):
            self.edit_pos = len(text)
        self._invalidate()

    def get_edit_text(self):
        """
        Return the edit text for this widget.

        >>> e = Edit("What? ", "oh, nothing.")
        >>> e.get_edit_text()
        'oh, nothing.'
        >>> e.edit_text
        'oh, nothing.'
        """
        return self._edit_text
    
    edit_text = property(get_edit_text, set_edit_text)

    def insert_text(self, text):
        """
        Insert text at the cursor position and update cursor.
        This method is used by the keypress() method when inserting
        one or more characters into edit_text.

        >>> e = Edit("", "42")
        >>> e.insert_text(".5")
        >>> e
        <Edit selectable flow widget '42.5' edit_pos=4>
        >>> e.set_edit_pos(2)
        >>> e.insert_text("a")
        >>> e.edit_text
        '42a.5'
        """
        p = self.edit_pos
        self.set_edit_text(self._edit_text[:p] + text + 
            self._edit_text[p:])
        self.set_edit_pos(self.edit_pos + len(text))
    
    def keypress(self, size, key):
        """
        Handle editing keystrokes, return others.
        
        >>> e, size = Edit(), (20,)
        >>> e.keypress(size, 'x')
        >>> e.keypress(size, 'left')
        >>> e.keypress(size, '1')
        >>> e.edit_text
        '1x'
        >>> e.keypress(size, 'backspace')
        >>> e.keypress(size, 'end')
        >>> e.keypress(size, '2')
        >>> e.edit_text
        'x2'
        >>> e.keypress(size, 'shift f1')
        'shift f1'
        """
        (maxcol,) = size

        p = self.edit_pos
        if self.valid_char(key):
            self._delete_highlighted()
            self.insert_text( key )
            
        elif key=="tab" and self.allow_tab:
            self._delete_highlighted() 
            key = " "*(8-(self.edit_pos%8))
            self.insert_text( key )

        elif key=="enter" and self.multiline:
            self._delete_highlighted() 
            key = "\n"
            self.insert_text( key )

        elif command_map[key] == 'cursor left':
            if p==0: return key
            p = move_prev_char(self.edit_text,0,p)
            self.set_edit_pos(p)
        
        elif command_map[key] == 'cursor right':
            if p >= len(self.edit_text): return key
            p = move_next_char(self.edit_text,p,len(self.edit_text))
            self.set_edit_pos(p)
        
        elif command_map[key] in ('cursor up', 'cursor down'):
            self.highlight = None
            
            x,y = self.get_cursor_coords((maxcol,))
            pref_col = self.get_pref_col((maxcol,))
            assert pref_col is not None
            #if pref_col is None: 
            #    pref_col = x

            if command_map[key] == 'cursor up': y -= 1
            else: y += 1

            if not self.move_cursor_to_coords((maxcol,),pref_col,y):
                return key
        
        elif key=="backspace":
            self._delete_highlighted()
            self.pref_col_maxcol = None, None
            if p == 0: return key
            p = move_prev_char(self.edit_text,0,p)
            self.set_edit_text( self.edit_text[:p] + 
                self.edit_text[self.edit_pos:] )
            self.set_edit_pos( p )

        elif key=="delete":
            self._delete_highlighted()
            self.pref_col_maxcol = None, None
            if p >= len(self.edit_text):
                return key
            p = move_next_char(self.edit_text,p,len(self.edit_text))
            self.set_edit_text( self.edit_text[:self.edit_pos] + 
                self.edit_text[p:] )
        
        elif command_map[key] in ('cursor max left', 'cursor max right'):
            self.highlight = None
            self.pref_col_maxcol = None, None
            
            x,y = self.get_cursor_coords((maxcol,))
            
            if command_map[key] == 'cursor max left':
                self.move_cursor_to_coords((maxcol,), LEFT, y)
            else:
                self.move_cursor_to_coords((maxcol,), RIGHT, y)
            return
            
            
        else:
            # key wasn't handled
            return key

    def move_cursor_to_coords(self, size, x, y):
        """
        Set the cursor position with (x,y) coordinates.
        Returns True if move succeeded, False otherwise.
        
        >>> size = (10,)
        >>> e = Edit("","edit\\ntext")
        >>> e.move_cursor_to_coords(size, 5, 0)
        True
        >>> e.edit_pos
        4
        >>> e.move_cursor_to_coords(size, 5, 3)
        False
        >>> e.move_cursor_to_coords(size, 0, 1)
        True
        >>> e.edit_pos
        5
        """
        (maxcol,) = size
        trans = self.get_line_translation(maxcol)
        top_x, top_y = self.position_coords(maxcol, 0)
        if y < top_y or y >= len(trans):
            return False

        pos = calc_pos( self.get_text()[0], trans, x, y )
        e_pos = pos - len(self.caption)
        if e_pos < 0: e_pos = 0
        if e_pos > len(self.edit_text): e_pos = len(self.edit_text)
        self.edit_pos = e_pos
        self.pref_col_maxcol = x, maxcol
        self._invalidate()
        return True

    def mouse_event(self, size, event, button, x, y, focus):
        """
        Move the cursor to the location clicked for button 1.

        >>> size = (20,)
        >>> e = Edit("","words here")
        >>> e.mouse_event(size, 'mouse press', 1, 2, 0, True)
        True
        >>> e.edit_pos
        2
        """
        (maxcol,) = size
        if button==1:
            return self.move_cursor_to_coords( (maxcol,), x, y )


    def _delete_highlighted(self):
        """
        Delete all highlighted text and update cursor position, if any
        text is highlighted.
        """
        if not self.highlight: return
        start, stop = self.highlight
        btext, etext = self.edit_text[:start], self.edit_text[stop:]
        self.set_edit_text( btext + etext )
        self.edit_pos = start
        self.highlight = None
        
        
    def render(self, size, focus=False):
        """ 
        Render edit widget and return canvas.  Include cursor when in
        focus.

        >>> c = Edit("? ","yes").render((10,), focus=True)
        >>> c.text
        ['? yes     ']
        >>> c.cursor
        (5, 0)
        """
        (maxcol,) = size
        self._shift_view_to_cursor = bool(focus)
        
        canv = Text.render(self,(maxcol,))
        if focus:
            canv = CompositeCanvas(canv)
            canv.cursor = self.get_cursor_coords((maxcol,))

        # .. will need to FIXME if I want highlight to work again
        #if self.highlight:
        #    hstart, hstop = self.highlight_coords()
        #    d.coords['highlight'] = [ hstart, hstop ]
        return canv

    
    def get_line_translation(self, maxcol, ta=None ):
        trans = Text.get_line_translation(self, maxcol, ta)
        if not self._shift_view_to_cursor: 
            return trans
        
        text, ignore = self.get_text()
        x,y = calc_coords( text, trans, 
            self.edit_pos + len(self.caption) )
        if x < 0:
            return ( trans[:y]
                + [shift_line(trans[y],-x)]
                + trans[y+1:] )
        elif x >= maxcol:
            return ( trans[:y] 
                + [shift_line(trans[y],-(x-maxcol+1))]
                + trans[y+1:] )
        return trans
            

    def get_cursor_coords(self, size):
        """
        Return the (x,y) coordinates of cursor within widget.
        
        >>> Edit("? ","yes").get_cursor_coords((10,))
        (5, 0)
        """
        (maxcol,) = size

        self._shift_view_to_cursor = True
        return self.position_coords(maxcol,self.edit_pos)
    
    
    def position_coords(self,maxcol,pos):
        """
        Return (x,y) coordinates for an offset into self.edit_text.
        """
        
        p = pos + len(self.caption)
        trans = self.get_line_translation(maxcol)
        x,y = calc_coords(self.get_text()[0], trans,p)
        return x,y

        




class IntEdit(Edit):
    """Edit widget for integer values"""

    def valid_char(self, ch):
        """
        Return true for decimal digits.
        """
        return len(ch)==1 and ch in "0123456789"
    
    def __init__(self,caption="",default=None):
        """
        caption -- caption markup
        default -- default edit value

        >>> IntEdit("", 42)
        <IntEdit selectable flow widget '42' edit_pos=2>
        """
        if default is not None: val = str(default)
        else: val = ""
        self.__super.__init__(caption,val)

    def keypress(self, size, key):
        """
        Handle editing keystrokes.  Remove leading zeros.
        
        >>> e, size = IntEdit("", 5002), (10,)
        >>> e.keypress(size, 'home')
        >>> e.keypress(size, 'delete')
        >>> e.edit_text
        '002'
        >>> e.keypress(size, 'end')
        >>> e.edit_text
        '2'
        """
        (maxcol,) = size
        unhandled = Edit.keypress(self,(maxcol,),key)

        if not unhandled:
        # trim leading zeros
            while self.edit_pos > 0 and self.edit_text[:1] == "0":
                self.set_edit_pos( self.edit_pos - 1)
                self.set_edit_text(self.edit_text[1:])

        return unhandled

    def value(self):
        """
        Return the numeric value of self.edit_text.
        
        >>> e, size = IntEdit(), (10,)
        >>> e.keypress(size, '5')
        >>> e.keypress(size, '1')
        >>> e.value() == 51
        True
        """
        if self.edit_text:
            return long(self.edit_text)
        else:
            return 0


class WidgetWrapError(Exception):
    pass

class WidgetWrap(Widget):
    no_cache = ["rows"]

    def __init__(self, w):
        """
        w -- widget to wrap, stored as self._w

        This object will pass the functions defined in Widget interface
        definition to self._w.

        The purpose of this widget is to provide a base class for
        widgets that compose other widgets for their display and
        behaviour.  The details of that composition should not affect
        users of the subclass.  The subclass may decide to expose some
        of the wrapped widgets by behaving like a ContainerWidget or
        WidgetDecoration, or it may hide them from outside access.
        """
        self.__w = w

    def _set_w(self, w):
        """
        Change the wrapped widget.  This is meant to be called
        only by subclasses.

        >>> size = (10,)
        >>> ww = WidgetWrap(Edit("hello? ","hi"))
        >>> ww.render(size).text
        ['hello? hi ']
        >>> ww.selectable()
        True
        >>> ww._w = Text("goodbye") # calls _set_w()
        >>> ww.render(size).text
        ['goodbye   ']
        >>> ww.selectable()
        False
        """
        self.__w = w
        self._invalidate()
    _w = property(lambda self:self.__w, _set_w)

    def _raise_old_name_error(self, val=None):
        raise WidgetWrapError("The WidgetWrap.w member variable has "
            "been renamed to WidgetWrap._w (not intended for use "
            "outside the class and its subclasses).  "
            "Please update your code to use self._w "
            "instead of self.w.")
    w = property(_raise_old_name_error, _raise_old_name_error)

    def render(self, size, focus=False):
        """Render self._w."""
        canv = self._w.render(size, focus=focus)
        return CompositeCanvas(canv)

    selectable = property(lambda self:self.__w.selectable)
    get_cursor_coords = property(lambda self:self.__w.get_cursor_coords)
    get_pref_col = property(lambda self:self.__w.get_pref_col)
    keypress = property(lambda self:self.__w.keypress)
    move_cursor_to_coords = property(lambda self:self.__w.move_cursor_to_coords)
    rows = property(lambda self:self.__w.rows)
    mouse_event = property(lambda self:self.__w.mouse_event)
    sizing = property(lambda self:self.__w.sizing)


def _test():
    import doctest
    doctest.testmod()

if __name__=='__main__':
    _test()

########NEW FILE########
__FILENAME__ = wimp
#!/usr/bin/python
#
# Urwid Window-Icon-Menu-Pointer-style widget classes
#    Copyright (C) 2004-2008  Ian Ward
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

from widget import *
from container import *
from command_map import command_map


class SelectableIcon(Text):
    _selectable = True
    def __init__(self, text, cursor_position=1):
        """
        text -- markup for this widget
        cursor_position -- position the cursor will appear in when this
            widget is in focus

        This is a text widget that is selectable with a cursor
        displayed at a fixed location in the text when in focus
        """
        self.__super.__init__(text)
        self._cursor_position = cursor_position
    
    def render(self, size, focus=False):
        """
        Render the text content of this widget with a cursor when
        in focus.

        >>> si = SelectableIcon("[!]")
        >>> si
        <SelectableIcon selectable flow widget '[!]'>
        >>> si.render((4,), focus=True).cursor
        (1, 0)
        >>> si = SelectableIcon("((*))", 2)
        >>> si.render((8,), focus=True).cursor
        (2, 0)
        >>> si.render((2,), focus=True).cursor
        (0, 1)
        """
        c = self.__super.render(size, focus)
        if focus:
            # create a new canvas so we can add a cursor
            c = CompositeCanvas(c)
            c.cursor = self.get_cursor_coords(size)
        return c
    
    def get_cursor_coords(self, size):
        """
        Return the position of the cursor if visible.  This method
        is required for widgets that display a cursor.
        """
        if self._cursor_position > len(self.text):
            return None
        # find out where the cursor will be displayed based on
        # the text layout
        (maxcol,) = size
        trans = self.get_line_translation(maxcol)
        x, y = calc_coords(self.text, trans, self._cursor_position)
        return x, y

    def keypress(self, size, key):
        """
        No keys are handled by this widget.  This method is
        required for selectable widgets.
        """
        return key

class CheckBoxError(Exception):
    pass

class CheckBox(WidgetWrap):
    states = { 
        True: SelectableIcon("[X]"),
        False: SelectableIcon("[ ]"),
        'mixed': SelectableIcon("[#]") }
    reserve_columns = 4

    # allow users of this class to listen for change events
    # sent when the state of this widget is modified
    # (this variable is picked up by the MetaSignals metaclass)
    signals = ["change"]
    
    def __init__(self, label, state=False, has_mixed=False,
             on_state_change=None, user_data=None):
        """
        label -- markup for check box label
        state -- False, True or "mixed"
        has_mixed -- True if "mixed" is a state to cycle through
        on_state_change, user_data -- shorthand for connect_signal()
            function call for a single callback
        
        Signals supported: 'change'
        Register signal handler with:
          connect_signal(check_box, 'change', callback [,user_data])
        where callback is callback(check_box, new_state [,user_data])
        Unregister signal handlers with:
          disconnect_signal(check_box, 'change', callback [,user_data])

        >>> CheckBox("Confirm")
        <CheckBox selectable widget 'Confirm' state=False>
        >>> CheckBox("Yogourt", "mixed", True)
        <CheckBox selectable widget 'Yogourt' state='mixed'>
        >>> cb = CheckBox("Extra onions", True)
        >>> cb
        <CheckBox selectable widget 'Extra onions' state=True>
        >>> cb.render((20,), focus=True).text  # preview CheckBox
        ['[X] Extra onions    ']
        """
        self.__super.__init__(None) # self.w set by set_state below
        self._label = Text("")
        self.has_mixed = has_mixed
        self._state = None
        # The old way of listening for a change was to pass the callback
        # in to the constructor.  Just convert it to the new way:
        if on_state_change:
            connect_signal(self, 'change', on_state_change, user_data)
        self.set_label(label)
        self.set_state(state)
    
    def _repr_words(self):
        return self.__super._repr_words() + [
            repr(self.label)]
    
    def _repr_attrs(self):
        return dict(self.__super._repr_attrs(),
            state=self.state)
    
    def set_label(self, label):
        """
        Change the check box label.

        label -- markup for label.  See Text widget for description
        of text markup.

        >>> cb = CheckBox("foo")
        >>> cb
        <CheckBox selectable widget 'foo' state=False>
        >>> cb.set_label(('bright_attr', "bar"))
        >>> cb
        <CheckBox selectable widget 'bar' state=False>
        """
        self._label.set_text(label)
        # no need to call self._invalidate(). WidgetWrap takes care of
        # that when self.w changes
    
    def get_label(self):
        """
        Return label text.

        >>> cb = CheckBox("Seriously")
        >>> cb.get_label()
        'Seriously'
        >>> cb.label  # Urwid 0.9.9 or later
        'Seriously'
        >>> cb.set_label([('bright_attr', "flashy"), " normal"])
        >>> cb.label  #  only text is returned 
        'flashy normal'
        """
        return self._label.text
    label = property(get_label)
    
    def set_state(self, state, do_callback=True):
        """
        Set the CheckBox state.

        state -- True, False or "mixed"
        do_callback -- False to supress signal from this change
        
        >>> changes = []
        >>> def callback_a(cb, state, user_data): 
        ...     changes.append("A %r %r" % (state, user_data))
        >>> def callback_b(cb, state): 
        ...     changes.append("B %r" % state)
        >>> cb = CheckBox('test', False, False)
        >>> connect_signal(cb, 'change', callback_a, "user_a")
        >>> connect_signal(cb, 'change', callback_b)
        >>> cb.set_state(True) # both callbacks will be triggered
        >>> cb.state
        True
        >>> disconnect_signal(cb, 'change', callback_a, "user_a")
        >>> cb.state = False  # Urwid 0.9.9 or later
        >>> cb.state
        False
        >>> cb.set_state(True)
        >>> cb.state
        True
        >>> cb.set_state(False, False) # don't send signal
        >>> changes
        ["A True 'user_a'", 'B True', 'B False', 'B True']
        """
        if self._state == state:
            return

        if state not in self.states:
            raise CheckBoxError("%s Invalid state: %s" % (
                repr(self), repr(state)))

        # self._state is None is a special case when the CheckBox
        # has just been created
        if do_callback and self._state is not None:
            self._emit('change', state)
        self._state = state
        # rebuild the display widget with the new state
        self._w = Columns( [
            ('fixed', self.reserve_columns, self.states[state] ),
            self._label ] )
        self._w.focus_col = 0
        
    def get_state(self):
        """Return the state of the checkbox."""
        return self._state
    state = property(get_state, set_state)
        
    def keypress(self, size, key):
        """
        Toggle state on 'activate' command.  

        >>> assert command_map[' '] == 'activate'
        >>> assert command_map['enter'] == 'activate'
        >>> size = (10,)
        >>> cb = CheckBox('press me')
        >>> cb.state
        False
        >>> cb.keypress(size, ' ')
        >>> cb.state
        True
        >>> cb.keypress(size, ' ')
        >>> cb.state
        False
        """
        if command_map[key] != 'activate':
            return key
        
        self.toggle_state()
        
    def toggle_state(self):
        """
        Cycle to the next valid state.
        
        >>> cb = CheckBox("3-state", has_mixed=True)
        >>> cb.state
        False
        >>> cb.toggle_state()
        >>> cb.state
        True
        >>> cb.toggle_state()
        >>> cb.state
        'mixed'
        >>> cb.toggle_state()
        >>> cb.state
        False
        """
        if self.state == False:
            self.set_state(True)
        elif self.state == True:
            if self.has_mixed:
                self.set_state('mixed')
            else:
                self.set_state(False)
        elif self.state == 'mixed':
            self.set_state(False)

    def mouse_event(self, size, event, button, x, y, focus):
        """
        Toggle state on button 1 press.
        
        >>> size = (20,)
        >>> cb = CheckBox("clickme")
        >>> cb.state
        False
        >>> cb.mouse_event(size, 'mouse press', 1, 2, 0, True)
        True
        >>> cb.state
        True
        """
        if button != 1 or not is_mouse_press(event):
            return False
        self.toggle_state()
        return True
    
        
class RadioButton(CheckBox):
    states = { 
        True: SelectableIcon("(X)"),
        False: SelectableIcon("( )"),
        'mixed': SelectableIcon("(#)") }
    reserve_columns = 4

    def __init__(self, group, label, state="first True",
             on_state_change=None, user_data=None):
        """
        group -- list for radio buttons in same group
        label -- markup for radio button label
        state -- False, True, "mixed" or "first True"
        on_state_change, user_data -- shorthand for connect_signal()
            function call for a single 'change' callback

        This function will append the new radio button to group.
        "first True" will set to True if group is empty.
        
        Signals supported: 'change'
        Register signal handler with:
          connect_signal(radio_button, 'change', callback [,user_data])
        where callback is callback(radio_button, new_state [,user_data])
        Unregister signal handlers with:
          disconnect_signal(radio_button, 'change', callback [,user_data])

        >>> bgroup = [] # button group
        >>> b1 = RadioButton(bgroup, "Agree")
        >>> b2 = RadioButton(bgroup, "Disagree")
        >>> len(bgroup)
        2
        >>> b1
        <RadioButton selectable widget 'Agree' state=True>
        >>> b2
        <RadioButton selectable widget 'Disagree' state=False>
        >>> b2.render((15,), focus=True).text  # preview RadioButton
        ['( ) Disagree   ']
        """
        if state=="first True":
            state = not group
        
        self.group = group
        self.__super.__init__(label, state, False, on_state_change, 
            user_data)
        group.append(self)
    

    
    def set_state(self, state, do_callback=True):
        """
        Set the RadioButton state.

        state -- True, False or "mixed"
        do_callback -- False to supress signal from this change

        If state is True all other radio buttons in the same button
        group will be set to False.

        >>> bgroup = [] # button group
        >>> b1 = RadioButton(bgroup, "Agree")
        >>> b2 = RadioButton(bgroup, "Disagree")
        >>> b3 = RadioButton(bgroup, "Unsure")
        >>> b1.state, b2.state, b3.state
        (True, False, False)
        >>> b2.set_state(True)
        >>> b1.state, b2.state, b3.state
        (False, True, False)
        >>> def relabel_button(radio_button, new_state):
        ...     radio_button.set_label("Think Harder!")
        >>> connect_signal(b3, 'change', relabel_button)
        >>> b3
        <RadioButton selectable widget 'Unsure' state=False>
        >>> b3.set_state(True) # this will trigger the callback
        >>> b3
        <RadioButton selectable widget 'Think Harder!' state=True>
        """
        if self._state == state:
            return

        self.__super.set_state(state, do_callback)

        # if we're clearing the state we don't have to worry about
        # other buttons in the button group
        if state is not True:
            return

        # clear the state of each other radio button
        for cb in self.group:
            if cb is self: continue
            if cb._state:
                cb.set_state(False)
    
    
    def toggle_state(self):
        """
        Set state to True.
        
        >>> bgroup = [] # button group
        >>> b1 = RadioButton(bgroup, "Agree")
        >>> b2 = RadioButton(bgroup, "Disagree")
        >>> b1.state, b2.state
        (True, False)
        >>> b2.toggle_state()
        >>> b1.state, b2.state
        (False, True)
        >>> b2.toggle_state()
        >>> b1.state, b2.state
        (False, True)
        """
        self.set_state(True)

            

class Button(WidgetWrap):
    button_left = Text("<")
    button_right = Text(">")

    signals = ["click"]
    
    def __init__(self, label, on_press=None, user_data=None):
        """
        label -- markup for button label
        on_press, user_data -- shorthand for connect_signal()
            function call for a single callback
        
        Signals supported: 'click'
        Register signal handler with:
          connect_signal(button, 'click', callback [,user_data])
        where callback is callback(button [,user_data])
        Unregister signal handlers with:
          disconnect_signal(button, 'click', callback [,user_data])

        >>> Button("Ok")
        <Button selectable widget 'Ok'>
        >>> b = Button("Cancel")
        >>> b.render((15,), focus=True).text  # preview Button
        ['< Cancel      >']
        """
        self._label = SelectableIcon("", 0)    
        cols = Columns([
            ('fixed', 1, self.button_left),
            self._label,
            ('fixed', 1, self.button_right)],
            dividechars=1)
        self.__super.__init__(cols) 
        
        # The old way of listening for a change was to pass the callback
        # in to the constructor.  Just convert it to the new way:
        if on_press:
            connect_signal(self, 'click', on_press, user_data)

        self.set_label(label)
    
    def _repr_words(self):
        # include button.label in repr(button)
        return self.__super._repr_words() + [
            repr(self.label)]

    def set_label(self, label):
        """
        Change the button label.

        label -- markup for button label

        >>> b = Button("Ok")
        >>> b.set_label("Yup yup")
        >>> b
        <Button selectable widget 'Yup yup'>
        """
        self._label.set_text(label)
    
    def get_label(self):
        """
        Return label text.

        >>> b = Button("Ok")
        >>> b.get_label()
        'Ok'
        >>> b.label  # Urwid 0.9.9 or later
        'Ok'
        """
        return self._label.text
    label = property(get_label)
    
    def keypress(self, size, key):
        """
        Send 'click' signal on 'activate' command.
        
        >>> assert command_map[' '] == 'activate'
        >>> assert command_map['enter'] == 'activate'
        >>> size = (15,)
        >>> b = Button("Cancel")
        >>> clicked_buttons = []
        >>> def handle_click(button):
        ...     clicked_buttons.append(button.label)
        >>> connect_signal(b, 'click', handle_click)
        >>> b.keypress(size, 'enter')
        >>> b.keypress(size, ' ')
        >>> clicked_buttons
        ['Cancel', 'Cancel']
        """
        if command_map[key] != 'activate':
            return key

        self._emit('click')

    def mouse_event(self, size, event, button, x, y, focus):
        """
        Send 'click' signal on button 1 press.

        >>> size = (15,)
        >>> b = Button("Ok")
        >>> clicked_buttons = []
        >>> def handle_click(button):
        ...     clicked_buttons.append(button.label)
        >>> connect_signal(b, 'click', handle_click)
        >>> b.mouse_event(size, 'mouse press', 1, 4, 0, True)
        True
        >>> b.mouse_event(size, 'mouse press', 2, 4, 0, True) # ignored
        False
        >>> clicked_buttons
        ['Ok']
        """
        if button != 1 or not is_mouse_press(event):
            return False
            
        self._emit('click')
        return True


def _test():
    import doctest
    doctest.testmod()

if __name__=='__main__':
    _test()

########NEW FILE########
