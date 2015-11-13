__FILENAME__ = b1_barebones
#!/usr/bin/python

__author__ = "ccheever"
__doc__ = """
A barebones bunny1 server that should be easy to modify for your own use
"""
__date__ = "Thu Feb 12 09:05:40 PST 2009"

import urlparse

import bunny1
from bunny1 import cherrypy
from bunny1 import Content
from bunny1 import q
from bunny1 import qp
from bunny1 import expose
from bunny1 import dont_expose
from bunny1 import escape
from bunny1 import HTML

class MyCommands(bunny1.Bunny1Commands):

    def your_command_here(self, arg):
        """this is where a description of your command goes"""
        return "http://www.example.com/?" % qp(arg)

    def another_command(self, arg):
        """this example will send content to the browser rather than redirecting"""
        raise HTML("some <u>html</u> " + escape("with some <angle brackets>"))


    # ... and you can add other commands by just defining more methods
    # in this class here

class MyBunny(bunny1.Bunny1):
    def __init__(self):
        bunny1.Bunny1.__init__(self, MyCommands(), bunny1.Bunny1Decorators())

if __name__ == "__main__":
    bunny1.main(MyBunny())



########NEW FILE########
__FILENAME__ = b1_example
#!/usr/bin/python

__author__ = "ccheever"
__doc__ = """
An example bunny1 server with some common commands that you might want to use.
"""
__version__ = "1.1"

import urlparse
import subprocess

import bunny1
from bunny1 import cherrypy
from bunny1 import Content
from bunny1 import q
from bunny1 import qp
from bunny1 import expose
from bunny1 import dont_expose
from bunny1 import escape

def is_int(x):
    """tells whether something can be turned into an int or not"""
    try:
        int(x)
        return True
    except ValueError:
        return False

class ExampleCommands(bunny1.Bunny1Commands):

    def lol(self, arg):
        """a random lolcat"""
        return "http://icanhascheezburger.com/?random"

    def hoo(self, arg):
        """a hoogle (haskell + google) search"""
        return "http://haskell.org/hoogle/?q=%s" % q(arg)

    def rickroll(self, arg):
        """You Just Got Rick Roll'd By bunny1!"""
        return "http://tinyurl.com/djddqw"

    def _meta(self, arg):
        """an example of the convention of prefixing meta commands with an underscore"""
        raise Content("if you make a meta command, the convention is to use an underscore at the beginning of the name.")

    def fb(self, arg):
        """search www.facebook.com or go there"""
        if arg:
            return "http://www.facebook.com/s.php?q=%s&init=q" % qp(arg)
        else:
            return "http://www.facebook.com/"

    def fbapp(self, arg):
        """go to a particular Facebook app's default canvas page"""
        return "http://apps.facebook.com/%s" % arg

    # an example involving slightly more complciated logic
    def fbappabout(self, arg):
        """go to the about page for an app given a canvas name, app id, or api key"""
        if is_int(arg):
            return "http://www.facebook.com/apps/application.php?id=%s" % qp(arg)
        else:
            try:
                # check to see if this is a valid API key
                if len(arg) == 32:
                    int(arg, 16)
                    return "http://www.facebook.com/apps/application.php?api_key=%s" % qp(arg)
            except ValueError:
                pass
            return "http://www.facebook.com/app_about.php?app_name=%s" % qp(arg)

    def fbdevforum(self, arg):
        """goes to the developers discussion forum.  still need to add search to this :/"""
        return "http://forum.developers.facebook.com/"

    def jmirc(self, arg):
        """goes to dreiss' version of jmIrc"""
        return "http://www.cdc03.com/jmIrc.jar"

    def fblucky(self, arg):
        """facebook i'm feeling lucky search, i.e. go directly to a person's profile"""
        return "http://www.facebook.com/s.php?jtf&q=" + q(arg)
    fbs = fblucky

    def yt(self, arg):
        """Searches YouTube or goes to it"""
        if arg:
            return "http://www.youtube.com/results?search_query=%s&search_type=&aq=-1&oq=" % qp(arg)
        else:
            return "http://www.youtube.com/"

    def yts(self, arg):
        """goes to your YouTube subscription center"""
        return "http://www.youtube.com/subscription_center"

    def ytd(self, arg):
        """Searches YouTube by date added instead of by relevance, or goes to youtube.com"""
        if arg:
            return "http://www.youtube.com/results?search_query=%s&search_sort=video_date_uploaded" % qp(arg)
        else:
            return "http://www.youtube.com/"

    def bugcongress(self, arg):
        """looks up your senator or congressperson based on a zip code you give it"""
        # similar to the ubiquity command found here:
        # http://people.mozilla.com/~jdicarlo/ubiquity-tutorial-1.mov
        if arg:
            return "http://www.congress.org/congressorg/officials/congress/?lvl=C&azip=%s" % arg
        else:
            return "http://www.congress.org/congressorg/officials/congress/"

    def wa(self, arg):
        """Searches Wolfram Alpha or goes there"""
        if arg:
            return "http://www.wolframalpha.com/input/?i=%s" % qp(arg)
        else:
            return "http://www.wolframalpha.com/"

    def wikinvest(self, arg):
        """Searches Wikinvest or goes there"""
        if arg:
            return "http://www.wikinvest.com/Special/Search?search=%s" % qp(arg)
        else:
            return "http://www.wikinvest.com/"
    # make wi and wv be aliasses for wikinvest
    wi = wikinvest
    wv = wikinvest

    # unlisted makes it so this command won't show up when listing all
    # commands, but the command can still be used
    @bunny1.unlisted
    def _finger(self, arg):
        """run finger on the host that this is running on"""
        p = subprocess.Popen(["finger", arg], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return PRE("<span style='color: red;'>" + escape(p.stderr.read()) + "</span><hr />" + escape(p.stdout.read()))

    # this is dangerous to expose if you are running a public instance
    # of bunny1, but it might be useful if you are running bunny1 on localhost
    # behind a firewall
    # uncomment "dont_expose" if you want to use it (but only if you are
    # confident that you know what you are doing)
    @dont_expose
    def eval(self, arg):
        try:
            return PRE(eval(arg))
        except Content:
            raise
        except Exception, e:
            return PRE("<span style='color: red;'>" + escape(str(e)) + "</span>")

    def time(self, arg):
        """shows the current time in US time zones"""
        return "http://tycho.usno.navy.mil/cgi-bin/timer.pl"

    def ya(self, arg):
        """searches Yahoo! Answers for an answer to your question"""
        if arg:
            return "http://answers.yahoo.com/search/search_result?p=%s" % qp(arg)
        else:
            return "http://answers.yahoo.com/"

    def tlpd(self, arg):
        """goes to the spoilerless gamelist in the teamliquid programing database"""
        return "http://www.teamliquid.net/tlpd/games/nospoiler"

    def fbpbz(self, arg):
        """goes to Facebook Platform Bugzilla bugs"""
        if arg:
            return "http://bugs.developers.facebook.com/buglist.cgi?quicksearch=%s" % qp(arg)
        else:
            # if no arg, go to the main page of bugzilla
            return "http://bugs.developers.facebook.com/"

    def _author(self, arg):
        """goes to the author of bunny1's homepage"""
        return "http://www.ccheever.com/"""

    # an example of a redirect that goes to a non-HTTP URL
    # also, an example of a command that requires an argument
    def aim(self, arg):
        """use AOL Instant Messenger to IM a given screenname"""
        return "aim:goim?screenname=%s" % qp(arg)

    # an example of showing content instead of redirecting and also
    # using content from the filesystem
    def readme(self, arg):
        """shows the contents of the README file for this software"""
        raise bunny1.PRE(bunny1.bunny1_file("README"))

    @dont_expose
    def _help_html(self, examples=None, name="bunny1"):
        """the help page that gets shown if no command or 'help' is entered"""

        import random

        def bookmarklet(name):
            return """<a href="javascript:bunny1_url='""" + self._base_url() + """?';cmd=prompt('bunny1.  type &quot;help&quot; to get help or &quot;list&quot; to see commands you can use.',window.location);if(cmd){window.location=bunny1_url+escape(cmd);}else{void(0);}">""" + name + """</a>"""

        if not examples:
            examples = [
                    "g phpsh",
                    "fbpbz 1737",
                    "wikinvest 2008 Financial Crisis",
                    "popular",
                    "ya what is the meaning of life?",
                    "list Facebook",
                    "fbs john",
                    "php array_merge",
                    "wp FBML",
                    "fb mark zuckerberg",
                    "gmaps 285 Hamilton Ave, Palo Alto, CA 94301",
                    "gimg bisu",
                    "rickroll",
                    "yt i'm cool sushi654 yeah",
                    "y osteria palo alto",
                    "live james harrison",
                    ]

        return """
<html>
<head>
<title>bunny1</title>
""" + self._opensearch_link() + """
<style>
BODY {
    font-family: Sans-serif;
    width: 800px;
}

code {
    color: darkgreen;
}

A {
    color: #3B5998;
}

small {
    width: 800px;
    text-align: center;
}

.header {
    position: absolute;
    top: 0px;
    left: 0px;
}

.test-query-input {
    width: 487px;
    font-size: 20px;
}

.header-placeholder {
    height: 45px;
}

</style>
</head>
<body>
<h1 class="header-placeholder"><img class="header" src="header.gif" /></h1>

<p>""" + name + """ is a tool that lets you write smart bookmarks in python and then share them across all your browsers and with a group of people or the whole world.  It was developed at <a href="http://www.facebook.com/">Facebook</a> and is widely used there.</p>

<form method="GET">
<p style="width: 820px; text-align: center;"><input class="test-query-input" id="b1cmd" type="text" name="___" value=""" + '"' + escape(random.choice(examples)) + '"' + """/> <input type="submit" value=" try me "/></p>

<p>Type something like """ + " or ".join(["""<a href="#" onclick="return false;"><code onclick="document.getElementById('b1cmd').value = this.innerHTML; return true;">""" + x + "</code></a>" for x in examples]) + """.</p>

<p>Or you can see <a href="?list">a list of shortcuts you can use</a> with this example server.</p>

<h3>Running Your Own bunny1 Server</h3>
<ul>Download the <a href="http://github.com/ccheever/bunny1/">source code</a> for the project.  Or if you use setuptools, you can just <code>easy_install bunny1</code>.</ul>

<ul>To run an example server, just run <code>b1_example.py --port=8080</code>.</ul>

<ul>More detailed instructions for configuring and running your own server can be found in the <a href=""" + '"' + self._base_url() + """?readme">README</a>.  You can add your own commands with just a few lines of python.</ul>

<h3>Installing on Firefox</h3>
<ul>Type <code>about:config</code> into your location bar in Firefox.</ul>
<ul>Set the value of keyword.URL to be <code>""" + self._base_url() + """?</code></ul>
<ul>Make sure you include the <code>http://</code> at the beginning and the <code>?</code> at the end.</ul>
<ul>Now, type <code>list</code> or <code>wp FBML</code> into your location bar and hit enter.</ul>
<ul>Also, if you are a Firefox user and find bunny1 useful, you should check out <a href="http://labs.mozilla.com/projects/ubiquity/">Ubiquity</a>.</ul>

<h3>Installing on Safari</h3>
<ul>Drag this bookmarklet [""" + bookmarklet(name) + """] to your bookmarks bar.</ul>
<ul>Now, visit the bookmarklet, and in the box that pops up, type <code>list</code> or <code>g facebook comments widget video</code> and hit enter.</ul>
<ul>In Safari, one thing you can do is make the bookmarklet the leftmost bookmark in your bookmarks bar, and then use <code>Command-1</code> to get to it.</ul>
<ul>Alternatively, you can get the location bar behavior of Firefox in Safari 3 by using the <a href="http://purefiction.net/keywurl/">keywurl</a> extension.</ul>

<h3>Installing on Google Chrome</h3>
<ul>Choose <code>Options</code> from the wrench menu to the right of the location bar in Chrome, then under the section <code>Default Search</code>, click the <code>Manage</code> button.  Click the <code>Add</code> button and then fill in the fields name, keyword, and URL with <code>""" + name + """</code>, <code>b1</code>, and <code>""" + self._base_url() + """?</code>.  Hit <code>OK</code> and then select """ + name + """ from the list of search engines and hit the <code>Make Default</code> button to make """ + name + """ your default search engine.  Type <code>list</code> into your location bar to see a list of commands you can use.</ul>

<h3>Installing on Internet Explorer</h3>
<ul>There aren't any great solutions for installing """ + name + """ on IE, but two OK solutions are:</ul>
<ul>You can use this bookmarklet [""" + bookmarklet(name) + """] by dragging into your bookmarks bar and then clicking on it when you want to use """ + name + """.</ul>
<ul>Or, in IE7+, you can click the down arrow on the search bar to the right of your location bar and choose the starred """ + name + """ option there.  This will install the bunny OpenSearch plugin in your search bar.</ul>

<hr />
<small>bunny1 was originally written by <a href="http://www.facebook.com/people/Charlie-Cheever/1160">Charlie Cheever</a> at <a href="http://developers.facebook.com/opensource.php">Facebook</a> and is maintained by him, <a href="http://www.facebook.com/people/David-Reiss/626221207">David Reiss</a>, Eugene Letuchy, and <a href="http://www.facebook.com/people/Daniel-Corson/708561">Dan Corson</a>.  Julie Zhuo drew the bunny logo.</small>


</body>
</html>
        """

    # fallback is special method that is called if a command isn't found
    # by default, bunny1 falls back to yubnub.org which has a pretty good
    # database of commands that you would want to use, but you can configure
    # it to point anywhere you'd like.  ex. you could run a personal instance
    # of bunny1 that falls back to a company-wide instance of bunny1 which
    # falls back to yubnub or some other global redirector.  yubnub similarly
    # falls back to doing a google search, which is often what a user wants.

    @dont_expose
    def fallback(self, raw, *a, **k):

        # this code makes it so that if you put a command in angle brackets
        # (so it looks like an HTML tag), then the command will get executed.
        # doing something like this is useful when there is a server on your 
        # LAN with the same name as a command that you want to use without 
        # any arguments.  ex. at facebook, there is an 'svn' command and
        # the svn(.facebook.com) server, so if you type 'svn' into the 
        # location bar of a browser, it goes to the server first even though
        # that's not usually what you want.  this provides a workaround for 
        # that problem.
        if raw.startswith("<") and raw.endswith(">"):
            return self._b1.do_command(raw[1:-1])

        # meta-fallback
        return bunny1.Bunny1Commands.fallback(self, raw, *a, **k)


def rewrite_tld(url, new_tld):
    """changes the last thing after the dot in the netloc in a URL"""
    (scheme, netloc, path, query, fragment) = urlparse.urlsplit(url)
    domain = netloc.split(".")

    # this is just an example so we naievely assume the TLD doesn't
    # include any dots (so this breaks if you try to rewrite .co.jp
    # URLs for example)...
    domain[-1] = new_tld
    new_domain = ".".join(domain)
    return urlparse.urlunsplit((scheme, new_domain, path, query, fragment))

def tld_rewriter(new_tld):
    """returns a function that rewrites the TLD of a URL to be new_tld"""
    return expose(lambda url: rewrite_tld(url, new_tld))


class ExampleDecorators(bunny1.Bunny1Decorators):
    """decorators that show switching between TLDs"""

    # we don't really need to hardcode these since they should get handled
    # by the default case below, but we'll include them just as examples.
    com = tld_rewriter("com")
    net = tld_rewriter("net")
    org = tld_rewriter("org")
    edu = tld_rewriter("edu")

    # make it so that you can do @co.uk -- the default decorator rewrites the TLD
    def __getattr__(self, attr):
        return tld_rewriter(attr)

    @expose
    def archive(self, url):
        """shows a list of older versions of the page using the wayback machine at archive.org"""
        return "http://web.archive.org/web/*/%s" % url

    @expose
    def identity(self, url):
        """a no-op decorator"""
        return url

    @expose
    def tinyurl(self, url):
        """creates a tinyurl of the URL"""
        # we need to leave url raw here since tinyurl will actually
        # break if we send it a quoted url
        return "http://tinyurl.com/create.php?url=%s" % url

class ExampleBunny(bunny1.Bunny1):
    """An example"""
    def __init__(self):
        bunny1.Bunny1.__init__(self, ExampleCommands(), ExampleDecorators())

    # an example showing how you can handle URLs that happen before 
    # the querystring by adding methods to the Bunny class instead of 
    # the commands class
    @cherrypy.expose
    def header_gif(self):
        """the banner GIF for the bunny1 homepage"""
        cherrypy.response.headers["Content-Type"] = "image/gif"
        return bunny1.bunny1_file("header.gif")


if __name__ == "__main__":
    bunny1.main(ExampleBunny())



########NEW FILE########
__FILENAME__ = bunny1
#!/usr/bin/env python

import sys
import os
import re
import cgi
import urllib
import urlparse
import optparse
import socket

from urllib import quote as q
from urllib import quote_plus as qp
from xml.sax.saxutils import escape

import cherrypy
from cherrypy import HTTPRedirect
from cherrypy import expose

from itertools import imap, izip, ifilter

__doc__ = """
    bunny1 is a tool that lets you write smart bookmarks in python and then
    share them across all your browsers and with a group of people or the
    whole world. It was developed at Facebook and is widely used there.
"""
__author__ = "ccheever" # Charlie Cheever <ccheever@gmail.com>
__date__ = "Mon Oct 22 02:27:47 PDT 2007"

# these are three good choices for default fallbacks
YUBNUB_URL = "http://yubnub.org/parser/parse?command="
GOOGLE_SEARCH_URL = "http://www.google.com/search?q="
GOOGLE_LUCKY_SEARCH_URL = "http://www.google.com/search?btnI&q="

DEFAULT_FALLBACK_URL = YUBNUB_URL
DEFAULT_COMMAND = "help"
DEFAULT_PORT = 9084

BUNNY1_HOME_URL = "http://www.bunny1.org/"

# a list of commands that we shouldn't list as popular because
# they sometimes get invoked behind the scenes but not usually
# directly, and we want to avoid confusing users who look at the 
# list of most popular commands.
DONT_LIST_AS_POPULAR = ("echo", "url", "_setpasswd")

# a query stirng var that you can use instead of specifying your
# command as the querystring.  this is useful when the user is 
# submitting forms.  we choose the triple underscore since no
# commands can start with any more than two underscores.
COMMAND_QUERY_STRING_VAR = "___"

class ServerModes(object):
    """enum for different modes that the server can operate in"""
    CHERRYPY = "CHERRYPY"
    CGI = "CGI"
    COMMAND_LINE = "COMMAND_LINE"

class Bunny1Decorators(object):
    """bunny1 decorators manipulate URLs after they are returned"""

    def default_url(self):
        """the default URL to go to if nothing is entered except a decorator"""
        return BUNNY1_HOME_URL

class Bunny1(object):

    def __init__(self, commands, decorators=None, server_mode=ServerModes.CHERRYPY):
        commands._b1 = self
        decorators._b1 = self
        self.commands = commands
        if decorators:
            self.decorators = decorators
        else:
            self.decorators = Bunny1Decorators()

        # this is just a placeholder... maybe it should be set to None
        # or "UNKNOWN"?
        self.base_url = BUNNY1_HOME_URL

        self._server_mode = server_mode

    def server_mode(self):
        """returns what mode the server is in (CHERRYPY or CGI)"""
        return self._server_mode

    def auth(self):
        """returns True if the user is authorized to use this bunny1 instance"""
        return True

    def unauthorized(self):
        """what to show when the user isn't authorized to use this instance"""
        # we pretend like this site doesn't exist
        raise cherrypy.HTTPError(404)


    def error(self, error_message):
        """call this when there is an error"""
        return "<span style='color: red; font-family: Courier New, Courier, Fixed-width; font-weight: bold;'>%s</span>" % error_message

    @expose
    def default(self, *a, **k):

        raw = None
        for raw in k:
            break
        if raw == COMMAND_QUERY_STRING_VAR:
            raw = k[COMMAND_QUERY_STRING_VAR]

        return self.do_command(raw, a, k)

    def do_command(self, raw, a=(), k={}):
        """does the specified command"""

        self.commands.history.append(raw)
        if not raw:
            raw = DEFAULT_COMMAND

        # setup a namespace in the request for bunny1 stuff
        cherrypy.request.bunny1 = {"decorators": []}

        while True:
            try:
                (method, arg) = raw.split(None, 1)
            except ValueError:
                method = raw
                arg = ""
            if method.startswith("@") and method != "@":
                try:
                    d = getattr(self.decorators, method[1:])
                    if d.exposed:
                        cherrypy.request.bunny1["decorators"].append(d)
                    else:
                        # shold really use a different kind of exception
                        # and raise that here, but this works for now
                        raise DoesNotExist(method)
                    raw = arg
                except (AttributeError, DoesNotExist):
                    return self.error("no decorator named %s %s" % (escape(method), repr(self.decorators)))
            else:
                break

        # use aliases
        try:
            method = cherrypy.request.cookie["alias." + method].value
        except KeyError:
            pass

        # @ is a symbol that works if you have a server on your LAN
        # with the same name as a command you want to use
        if method == "@":
            try:
                (method, arg) = arg.split(None, 1)
            except ValueError:
                method = arg
                arg = ""

        # go to the default URL if there is just a decorator given
        if method == "":
            method = "url"
            arg = self.decorators.default_url()

        # if you type in a URL, just go there
        if urlparse.urlsplit(method)[0]:
            method = "url"
            arg = raw

        # debug mode: gives the URLs of redirects rather than redirecting
        if method == "_debug":
            try:
                return self.do_command(arg)
            except HTTPRedirect, redir:
                url = escape(redir.urls[0])
                return "<code><b>bunny1</b> DEBUG: redirect to <a href='%s'>%s</a></code>" % (url, url)

        # we don't want people calling things like __str__, etc.
        # it seems likely to lead to exploits
        if method.startswith("__"):
            return self.error("commands can't start with a double underscore")


        try:
            try:
                cmd = getattr(self.commands, method)
                if hasattr(cmd, "dont_expose") and cmd.dont_expose:
                    raise Fallback("method not exposed")
                if not callable(cmd):
                    raise Fallback("method not callable")
            except AttributeError:
                raise Fallback("no method")


            # check whether the user is authorized
            if not self.auth() and not getattr(cmd, "no_auth_required", False):
                return self.unauthorized()

            # Tell the user what host we are on for easier troubleshooting.
            cherrypy.response.headers['X-Bunny1-Host'] = cherrypy.server.socket_host

            # we invert the normal cherrypy paradigm here
            # since the common case is that we want to redirect
            # and the exceptional case is that we want to send content
            # to the browser
            try:

                # keep track of which are the most popular commands
                # to use so we can surface those
                if method:
                    popularity = self.commands.popularity
                    popularity[method] = popularity.get(method, 0) + 1

                # do any transformations that we want to do
                preprocessor = getattr(cmd, "preprocessor", None)
                if callable(preprocessor):
                    arg = preprocessor(arg)

                url = cmd(arg)

                # if the command doesn't do anything, just say "done."
                if url is None:
                    return "done."

                for decorator_method in cherrypy.request.bunny1["decorators"][::-1]:
                    url = decorator_method(url)

                raise HTTPRedirect(url)
            except Content, content:
                cherrypy.response.headers['Content-Type'] = content.content_type
                return content.html

        except Fallback:
            return self.fallback(raw, *a, **k)

    def fallback(self, raw, *a, **k):
        return self.commands.fallback(raw)

    @expose
    def favicon_ico(self, *args, **kwargs):
        """favicon.ico file.  blobbunny made by julie zhuo :)"""
        cherrypy.response.headers["Content-Type"] = "image/x-icon"
        return bunny1_file("favicon.ico")

    @expose
    def blobbunny_gif(self, *args, **kwargs):
        """blobbunny.gif logo, made by julie zhuo"""
        cherrypy.response.headers["Content-Type"] = "image/gif"
        return bunny1_file("blobbunny.gif")

    def start(self, port=None, host=None, errorlogfile=None, accesslogfile=None):
        if port:
            cherrypy.server.socket_port = port
        if errorlogfile:
            cherrypy.config["log.error_file"] = errorlogfile
        if accesslogfile:
            cherrypy.config["log.access_file"] = accesslogfile
        if host:
            cherrypy.server.socket_host = host
        else:
            from socket import gethostname
            cherrypy.server.socket_host = gethostname()
        return cherrypy.quickstart(self)

class Content(Exception):
    """raise when returning content instead of redirecting"""
    def __init__(self, html="", content_type="text/html"):
        self.content_type = content_type
        self.html = html

class HTML(Content):
    """raise when returning an HTML repsonse instead of redirecting"""
    def __init__(self, html=""):
        self.content_type = "text/html"
        self.html = html

class PRE(HTML):
    """preformatted HTML"""
    def __init__(self, html):
        HTML.__init__(self, "<pre>%s</pre>" % html)

class ErrorMesage(Content):
    """raise when returning an error"""
    def __init__(self, error_message):
        Content.__init__(self)
        self.html = "<span style='color: red; font-family: Courier New, Courier, Fixed-width; font-weight: bold;'>%s</span>" % escape(error_message)

class Fallback(Exception):
    """raise when we want to go to the fallback"""
    pass

def dont_expose(fun):
    """decorator for methods that shouldn't be exposed to the web"""
    fun.dont_expose = True
    return fun

def preprocessor(fun):
    """decorator that defines a preprocessor"""
    def decorator(cmd):
        cmd.preprocessor = fun
        return cmd
    return decorator

def unlisted(fun):
    """decorator for methods that shouldn't be listed with list"""
    fun.unlisted = True
    return fun

def no_auth_required(fun):
    """decorator for methods that don't require auth"""
    fun.no_auth_required = True
    return fun

class Bunny1Commands(object):
    """the default commands used by bunny1"""

    def __init__(self):
        self.history = []
        self.fallback_url = YUBNUB_URL
        self.popularity = {}

    @dont_expose
    def _base_url(self):
        if hasattr(self, "_b1"):
            return self._b1.base_url
        else:
            return BUNNY1_HOME_URL

    @dont_expose
    def _opensearch_link(self):
        m = self._opensearch_metadata()
        return """<link rel="search" type="application/opensearchdescription+xml" title="%s" href="/?_opensearch" />""" % m["short_name"]

    @dont_expose
    def _help_html(self):
        # this won't work unless bunny1 is imported as a module.
        # at some point, it might be good to deal with that
        return "<html><head><title>bunny1</title>" + self._opensearch_link() + "</head><body><form><input type='text' name='" + COMMAND_QUERY_STRING_VAR + "' value='list'><input type='submit' value='try me'></form><pre>" + escape(bunny1_file("README")) + "</pre></body></html>"

    def help(self, arg):
        """gets help with a specific command or shows the README for general help"""
        if arg:
            raise Content("<b>" + escape(arg) + "</b><br />" + str(getattr(self, arg).__doc__))
        else:
            raise Content(self._help_html())
    man = help

    def readme(self, arg):
        """shows the README for this tool"""
        raise Content(self._help_html())

    # _info provides some useful debugging information but this information
    # may be sensitive so we don't expose this command by default
    #@dont_expose
    def _info(self, arg):
        """shows some info about this instance of bunny1"""
        raise Content("<code>" + repr({
            "_info": {
                "base_url": self._b1.base_url,
            },

            "os_env": os.environ,
            }) + "</code>")


    # the history could be dangerous / embarassing to expose !
    @dont_expose
    def history(self, arg):
        """show the history of queries made to this server"""

        html = "<pre><b>history</b>\n"
        for entry in self.history[:-50:-1]:
            html += '<a href="/?%(url)s">%(label)s</a>\n' % {
                "url": entry,
                "label": entry,
                }
        html += "</pre>"
        raise Content(html)
    h = history

    # since command history is only stored in memory and not persisted,
    # history and popularity data won't be available when running 
    # in cgi mode.

    def popular(self, arg):
        """shows the most popular commands"""
        raise Content(self._popularity_html())

    @dont_expose
    def _popularity_html(self, num=None):
        p = self.popularity
        pairs = [(val, key) for (key, val) in p.items() if key not in DONT_LIST_AS_POPULAR]
        pairs.sort()
        pairs.reverse()
        html = "<b><i>"
        if num:
            html += "%d " % num
        html += "Most Popular Commands</i></b><br />"
        if num:
            pairs = pairs[:num]
        for (times, method) in pairs:
            m = getattr(self, method)
            doc = m.__doc__
            if not getattr(m, "unlisted", False):
                if doc:
                    doc_str = " (%s)" % escape(doc)
                else:
                    doc_str = ""
                html += "<b>%s</b> used %d times%s<br />\n" % (escape(method), times, doc_str)
        return html

    def list(self, arg):
        """show the list of methods you can use or search that list"""

        def is_exposed_method( (name, method) ):
            return not name.startswith("__") and callable(method) \
                       and method.__doc__ and not getattr(method, "dont_expose", False) \
                       and not getattr(method, "unlisted", False)

        arg_lower = None
        if arg:
            arg_lower = arg.lower()
            html = ""
            search_predicate = lambda (name, method): is_exposed_method((name,method)) and \
                               (arg_lower in name.lower() or arg_lower in method.__doc__)
        else:
            html = self._popularity_html(10) + "<hr ><b><i>All Commands</i></b><br />"
            search_predicate = is_exposed_method

        attr_names = dir(self)

        def attr_getter(name): return getattr(self, name)

        html += '<table>'
        html += ''.join(
            ['<tr><td><b>%s</b></td><td>%s</td></tr>' % (name, escape(method.__doc__)) for
             name, method in ifilter(search_predicate,
                                     izip(attr_names, imap(attr_getter, attr_names)))])
        html += '<table>'

        raise Content(html)
    ls = list
    commands = list

    def echo(self, arg):
        """returns back what you give to it"""
        raise Content(escape(arg))

    def g(self, arg):
        """does a google search.  we could fallback to yubnub, but why do an unnecessary roundtrip for something as common as a google search?"""
        return GOOGLE_SEARCH_URL + q(arg)

    @unlisted
    def _hostname(self, arg):
        """shows the hostname of this server"""
        import socket
        raise Content(socket.gethostname())

    def _cookies(self, arg):
        """show the cookies set on this server or search through them"""
        cookie = cherrypy.request.cookie
        html = ""
        for name in cookie.keys():
            val = cookie[name].value
            if not arg or (arg in name or arg in val):
                html += "<b>%s</b><br />%s<br /><br />" % (escape(str(name)), escape(str(val)))
        raise Content(html)

    def alias(self, arg):
        """aliases one shortcut to another.  ex: alias p profile.  alias p will show what p is aliased to.  alias with no args will show all aliases."""
        words = arg.split()
        cookie = cherrypy.response.cookie
        try:
            alias = words[0]
            real = words[1]
            cookie["alias." + alias] = real
            raise Content("aliased <b>%s</b> to <b>%s</b>" % (escape(alias), escape(real)))
        except IndexError:
            try:
                alias = words[0]
                try:
                    raise Content("<b>%s</b> is aliased to <b>%s</b>" % (escape(alias), escape(cherrypy.request.cookie["alias." + alias].value)))
                except KeyError:
                    raise Content("<b>%s</b> is not aliased to anything." % escape(arg))
            except IndexError:
                html = "usage:<br />alias <i>alias</i> <i>real-command</i><br />or<br />alias <i>alias</i><br /><hr />"
                cookie = cherrypy.request.cookie
                for name in cookie.keys():
                    if str(name).startswith("alias."):
                        html += "<b>%s</b> is aliased to <b>%s</b><br />" % (escape(name[6:]), escape(cookie[name].value))
                raise Content(html)

    def unalias(self, arg):
        """unaliases an alias.  ex: unalias p"""
        if not arg:
            raise Content("usage:<br />unalias <i>alias</i>")
        cherrypy.response.cookie["alias." + arg] = ""
        cherrypy.response.cookie["alias." + arg]["expires"] = 0
        raise Content("unaliased <b>%s</b>" % escape(arg))

    def _source(self, arg):
        """goes to the source code for bunny1 (this utility)"""
        return "http://github.com/ccheever/bunny1/tree/master"

    def _test(self, arg):
        """tests a command on a different bunny1 host.  usage: _test [fully-qualified-bunny1-url] [command]"""
        (bunny1_url, arg) = arg.split(None, 1)
        if not bunny1_url.endswith("?"):
            bunny1_url += "?"
        save("bunny1testurl", bunny1_url)
        raise HTTPRedirect(bunny1_url + q(arg))

    def _t(self, arg):
        """tests a command on the most recently used bunny1 host.  usage: _t [command]"""
        bunny1_url = load("bunny1testurl")
        raise HTTPRedirect(bunny1_url + q(arg))

    def url(self, arg):
        """goes to the URL that is specified"""
        if arg:
            if ":" not in arg:
                return "http://%s" % arg
            else:
                return arg
        else:
            raise Content("no url specified")

    @dont_expose
    def _my_url(self):
        """the URL of this server"""

        # if a server is running, we try to get the URL of it
        # from the current request, but if not, we want to have a
        # sensible default
        if cherrypy.request.base:
            return cherrypy.request.base + cherrypy.request.path_info
        else:
            return self._my_home_url()

    @dont_expose
    def _my_home_url(self):
        """the configured URL of this server"""
        return BUNNY1_HOME_URL
    @dont_expose
    def _opensearch_metadata(self):
        """metadata about this server"""
        return {
                "short_name": "bunny1",
                "description": "bunny1",
                "template": self._my_url() + "?{searchTerms}",
            }

    def _opensearch(self, arg):
        """returns the OpenSearch description for this server"""
        m = self._opensearch_metadata()
        raise Content("""<?xml version="1.0" encoding="UTF-8" ?>
    <OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/">
    <ShortName>""" + m["short_name"] + """</ShortName>
    <Description>""" + m["description"] + """</Description>
    <InputEncoding>UTF-8</InputEncoding>
    <Url type="text/html" template=\"""" + escape(m["template"]) + """\" />
  </OpenSearchDescription>
  """, "application/xml")

    def keywurl(self, arg):
        """goes to the Keywurl Safari extension homepage"""
        return "http://purefiction.net/keywurl/"

    @dont_expose
    def fallback(self, raw):
        raise HTTPRedirect(self.fallback_url + q(raw))

class DoesNotExist(Exception):
    pass

def save(key, val):
    cherrypy.response.cookie[key] = val
    # save for 50 years
    cherrypy.response.cookie[key]["path"] = "/"
    cherrypy.response.cookie[key]["max-age"] = 50 * 365 * 24 * 60 * 60

def load(key):
    return cherrypy.request.cookie[key].value

def bunny1_file(name):
    """the binary contents of a file in the same directory as bunny1"""
    return file(os.path.dirname(__file__) + os.path.sep + name).read()

class Bunny1OptionParser(optparse.OptionParser):
    """a class for getting bunny1 options"""
    def __init__(self):
        optparse.OptionParser.__init__(self)
        self.add_basic_options()

    def add_basic_options(self):
        """adds the basic bunny1 options to the parser"""
        self.add_option("--daemonize", "-d", dest="daemonize", action="store_true", help="run this as a daemon")
        self.add_option("--host", dest="host", help="host to run on (default is the result of socket.gethostname())")
        self.add_option("--port", "-p", dest="port", help="port to run on (default %s)" % DEFAULT_PORT)
        self.add_option("--pidfile", dest="pidfile", help="pidfile to write to")
        self.add_option("--errorlogfile", dest="errorlogfile", help="file to write error logs to (defaults to stdout)")
        self.add_option("--accesslogfile", dest="accesslogfile", help="file to write access logs to (defaults to stdout)")
        self.add_option("--test-command", "-t", dest="test_command", help="test some command at the command line")
        self.add_option("--base-url", "-u", dest="base_url", help="the base URL of the bunny1 server")

class PasswordProtectionCommands(object):
    """commands for password protection"""

    @no_auth_required
    def _setpasswd(self, arg):
        """sets the password for password protected instances of bunny1"""
        args = arg.split()
        passwd = args[0]
        if not arg:
            return None

        if len(args) > 1:
            next = " ".join(args[1:])
        else:
            next = None
            
        save("b1passwd", passwd)

        if next:
            return next

        raise Content("password set.")

class PasswordProtectedBunny1(Bunny1):
    """a password protected instance of bunny1"""

    def auth(self):

        # we don't check auth for tests from the command line
        if self.server_mode() == ServerModes.COMMAND_LINE:
            return True

        try:
            password = cherrypy.request.cookie["b1passwd"].value
        except (AttributeError, KeyError), e:
            return False

        return (password == self.password())

    def password(self):
        # make sure you override this password if you are using one
        # http://www.rickadams.org/adventure/c_xyzzy.html
        return "xyzzy"

def main(b1, b1op=Bunny1OptionParser()):
    """uses command line options and runs the server given an instance of the Bunny1 class"""

    # guess if this is running in CGI mode
    if os.environ.get("GATEWAY_INTERFACE", "").startswith("CGI"):
        main_cgi(b1)
    else:
        (options, args) = b1op.parse_args()

        if options.test_command is not None:
            try:
                b1._server_mode = "COMMAND_LINE"
                print b1.do_command(options.test_command)
            except HTTPRedirect, redir:
                # the escape sequences make the output show up yellow on terminals
                # in the case of a redirect to distinguish from content output
                print "\033[33m%s:\033[0m %s" % (redir.__class__.__name__, redir)
        else:

            if options.port:
                port = int(options.port)
            else:
                port = DEFAULT_PORT

            if options.host:
                host = options.host
            else:
                host = socket.gethostname()

            if options.base_url:
                b1.base_url = options.base_url
            else:
                protocol = "http"
                b1.base_url = "%s://%s:%s/" % (protocol, host, port)

            if options.daemonize:
                import daemonize
                daemonize.daemonize(options.pidfile)

            # start the server
            b1.start(port=port, host=options.host, errorlogfile=options.errorlogfile, accesslogfile=options.accesslogfile)


def main_cgi(b1):
    """for running bunny1 as a cgi"""

    # this mostly works, but it has problems serving images andother
    # static content

    try:
        form = cgi.FieldStorage()
        cmd = form.getvalue(COMMAND_QUERY_STRING_VAR)
        if not cmd:
            try:
                cmd = urllib.unquote_plus(os.environ["QUERY_STRING"])
            except KeyError:
                cmd = DEFAULT_COMMAND
        response = b1.do_command(cmd)
        if cherrypy.response.headers['Content-type']:
            content_type = cherrypy.response.headers['Content-type']
        else:
            content_type = "text/html"
        print "Content-type: %s\n" % content_type
        print response
    except cherrypy.HTTPRedirect, redir:
        url = redir.urls[0]
        print "Location: " + url + "\n\n"

# it doesn't really make sense to run this module as a standalone program
# but it may be useful for testing in some rare cases
if __name__ == "__main__":
    main(Bunny1(Bunny1Commands(), Bunny1Decorators()))



########NEW FILE########
