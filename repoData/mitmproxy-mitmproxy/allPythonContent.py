__FILENAME__ = index
from countershape import Page

pages = [
    Page("webapp.html", "Using the Web App"),
    Page("firefox.html", "Firefox"),
    Page("osx.html", "OSX"),
    Page("windows7.html", "Windows 7"),
    Page("ios.html", "IOS"),
    Page("ios-simulator.html", "IOS Simulator"),
    Page("android.html", "Android"),
    Page("java.html", "Java"),
]

########NEW FILE########
__FILENAME__ = index
from countershape import Page

pages = [
     Page("testing.html", "Testing"),
#    Page("addingviews.html", "Writing Content Views"),
]

########NEW FILE########
__FILENAME__ = index
from countershape import Page

pages = [
    Page("anticache.html", "Anticache"),
    Page("clientreplay.html", "Client-side replay"),
    Page("filters.html", "Filter expressions"),
    Page("upstreamproxy.html", "Upstream proxy mode"),
    Page("setheaders.html", "Set Headers"),
    Page("serverreplay.html", "Server-side replay"),
    Page("sticky.html", "Sticky cookies and auth"),
    Page("proxyauth.html", "Proxy Authentication"),
    Page("replacements.html", "Replacements"),
    Page("reverseproxy.html", "Reverse proxy mode"),
    Page("upstreamcerts.html", "Upstream Certs"),
]

########NEW FILE########
__FILENAME__ = index
import os, sys, datetime
import countershape
from countershape import Page, Directory, PythonModule, markup, model
import countershape.template
sys.path.insert(0, "..")
from libmproxy import filt, version

MITMPROXY_SRC = os.environ.get("MITMPROXY_SRC", os.path.abspath(".."))
ns.VERSION = version.VERSION

if ns.options.website:
    ns.idxpath = "doc/index.html"
    this.layout = countershape.Layout("_websitelayout.html")
else:
    ns.idxpath = "index.html"
    this.layout = countershape.Layout("_layout.html")

ns.title = countershape.template.Template(None, "<h1>@!this.title!@</h1>")
this.titlePrefix = "%s - " % version.NAMEVERSION
this.markup = markup.Markdown(extras=["footnotes"])

ns.docMaintainer = "Aldo Cortesi"
ns.docMaintainerEmail = "aldo@corte.si"
ns.copyright = u"\u00a9 mitmproxy project, %s" % datetime.date.today().year

def mpath(p):
    p = os.path.join(MITMPROXY_SRC, p)
    return os.path.expanduser(p)

with open(mpath("README.mkd")) as f:
        readme = f.read()
        ns.index_contents = readme.split("\n", 1)[1] #remove first line (contains build status)

def example(s):
    d = file(mpath(s)).read().rstrip()
    extemp = """<div class="example">%s<div class="example_legend">(%s)</div></div>"""
    return extemp%(countershape.template.Syntax("py")(d), s)
ns.example = example


filt_help = []
for i in filt.filt_unary:
    filt_help.append(
        ("~%s"%i.code, i.help)
    )
for i in filt.filt_rex:
    filt_help.append(
        ("~%s regex"%i.code, i.help)
    )
for i in filt.filt_int:
    filt_help.append(
        ("~%s int"%i.code, i.help)
    )
filt_help.sort()
filt_help.extend(
    [
        ("!", "unary not"),
        ("&", "and"),
        ("|", "or"),
        ("(...)", "grouping"),
    ]
)
ns.filt_help = filt_help


def nav(page, current, state):
    if current.match(page, False):
        pre = '<li class="active">'
    else:
        pre = "<li>"
    p = state.application.getPage(page)
    return pre + '<a href="%s">%s</a></li>'%(model.UrlTo(page), p.title)
ns.nav = nav
ns.navbar = countershape.template.File(None, "_nav.html")

pages = [
    Page("index.html", "Introduction"),
    Page("install.html", "Installation"),
    Page("mitmproxy.html", "mitmproxy"),
    Page("mitmdump.html", "mitmdump"),
    Page("howmitmproxy.html", "How mitmproxy works"),

    Page("ssl.html", "Overview"),
    Directory("certinstall"),
    Directory("scripting"),
    Directory("tutorials"),
    Page("transparent.html", "Overview"),
    Directory("transparent"),
]

########NEW FILE########
__FILENAME__ = index
from countershape import Page

pages = [
    Page("inlinescripts.html", "Inline Scripts"),
    Page("libmproxy.html", "libmproxy"),
]

########NEW FILE########
__FILENAME__ = index
from countershape import Page

pages = [
    Page("osx.html", "OSX"),
    Page("linux.html", "Linux"),
]

########NEW FILE########
__FILENAME__ = index
from countershape import Page

pages = [
    Page("30second.html", "Client playback: a 30 second example"),
    Page("gamecenter.html", "Setting highscores on Apple's GameCenter"),
    Page("transparent-dhcp.html", "Transparently proxify virtual machines")
]
########NEW FILE########
__FILENAME__ = add_header
def response(context, flow):
    flow.response.headers["newheader"] = ["foo"]

########NEW FILE########
__FILENAME__ = dup_and_replay
def request(ctx, flow):
   f = ctx.duplicate_flow(flow)
   f.request.path = "/changed"
   ctx.replay_request(f)

########NEW FILE########
__FILENAME__ = mitmproxywrapper
#!/usr/bin/env python
#
# Helper tool to enable/disable OS X proxy and wrap mitmproxy
#
# Get usage information with:
#
# mitmproxywrapper.py -h
#

import subprocess
import re
import argparse
import contextlib
import os
import sys

class Wrapper(object):
    
    def __init__(self, port, extra_arguments=None):
        self.port = port
        self.extra_arguments = extra_arguments

    def run_networksetup_command(self, *arguments):
        return subprocess.check_output(['sudo', 'networksetup'] + list(arguments))

    def proxy_state_for_service(self, service):
        state = self.run_networksetup_command('-getwebproxy', service).splitlines()
        return dict([re.findall(r'([^:]+): (.*)', line)[0] for line in state])

    def enable_proxy_for_service(self, service):
        print 'Enabling proxy on {}...'.format(service)
        for subcommand in ['-setwebproxy', '-setsecurewebproxy']:
            self.run_networksetup_command(subcommand, service, '127.0.0.1', str(self.port))

    def disable_proxy_for_service(self, service):
        print 'Disabling proxy on {}...'.format(service)
        for subcommand in ['-setwebproxystate', '-setsecurewebproxystate']:
            self.run_networksetup_command(subcommand, service, 'Off')

    def interface_name_to_service_name_map(self):
        order = self.run_networksetup_command('-listnetworkserviceorder')
        mapping = re.findall(r'\(\d+\)\s(.*)$\n\(.*Device: (.+)\)$', order, re.MULTILINE)
        return dict([(b, a) for (a, b) in mapping])

    def run_command_with_input(self, command, input):
        popen = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        (stdout, stderr) = popen.communicate(input)
        return stdout
    
    def primary_interace_name(self):
        scutil_script = 'get State:/Network/Global/IPv4\nd.show\n'
        stdout = self.run_command_with_input('/usr/sbin/scutil', scutil_script)
        interface, = re.findall(r'PrimaryInterface\s*:\s*(.+)', stdout)
        return interface

    def primary_service_name(self):
        return self.interface_name_to_service_name_map()[self.primary_interace_name()]

    def proxy_enabled_for_service(self, service):
        return self.proxy_state_for_service(service)['Enabled'] == 'Yes'

    def toggle_proxy(self):
        new_state = not self.proxy_enabled_for_service(self.primary_service_name())
        for service_name in self.connected_service_names():
            if self.proxy_enabled_for_service(service_name) and not new_state:
                self.disable_proxy_for_service(service_name)
            elif not self.proxy_enabled_for_service(service_name) and new_state:
                self.enable_proxy_for_service(service_name)

    def connected_service_names(self):
        scutil_script = 'list\n'
        stdout = self.run_command_with_input('/usr/sbin/scutil', scutil_script)
        service_ids = re.findall(r'State:/Network/Service/(.+)/IPv4', stdout)

        service_names = []
        for service_id in service_ids:
            scutil_script = 'show Setup:/Network/Service/{}\n'.format(service_id)
            stdout = self.run_command_with_input('/usr/sbin/scutil', scutil_script)
            service_name, = re.findall(r'UserDefinedName\s*:\s*(.+)', stdout)
            service_names.append(service_name)

        return service_names

    def wrap_mitmproxy(self):
        with self.wrap_proxy():
            cmd = ['mitmproxy', '-p', str(self.port)]
            if self.extra_arguments:
                cmd.extend(self.extra_arguments)
            subprocess.check_call(cmd)

    def wrap_honeyproxy(self):
        with self.wrap_proxy():
            popen = subprocess.Popen('honeyproxy.sh')
            try:
                popen.wait()
            except KeyboardInterrupt:
                popen.terminate()

    @contextlib.contextmanager
    def wrap_proxy(self):
        connected_service_names = self.connected_service_names()
        for service_name in connected_service_names:
            if not self.proxy_enabled_for_service(service_name):
                self.enable_proxy_for_service(service_name)
        
        yield

        for service_name in connected_service_names:
            if self.proxy_enabled_for_service(service_name):
                self.disable_proxy_for_service(service_name)

    @classmethod
    def ensure_superuser(cls):
        if os.getuid() != 0:
            print 'Relaunching with sudo...'
            os.execv('/usr/bin/sudo', ['/usr/bin/sudo'] + sys.argv)

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(
            description='Helper tool for OS X proxy configuration and mitmproxy.',
            epilog='Any additional arguments will be passed on unchanged to mitmproxy.'
        )
        parser.add_argument('-t', '--toggle', action='store_true', help='just toggle the proxy configuration')
#         parser.add_argument('--honeyproxy', action='store_true', help='run honeyproxy instead of mitmproxy')
        parser.add_argument('-p', '--port', type=int, help='override the default port of 8080', default=8080)
        args, extra_arguments = parser.parse_known_args()

        wrapper = cls(port=args.port, extra_arguments=extra_arguments)
        
        if args.toggle:
            wrapper.toggle_proxy()
#         elif args.honeyproxy:
#             wrapper.wrap_honeyproxy()
        else:
            wrapper.wrap_mitmproxy()


if __name__ == '__main__':
    Wrapper.ensure_superuser()
    Wrapper.main()


########NEW FILE########
__FILENAME__ = modify_form

def request(context, flow):
    if "application/x-www-form-urlencoded" in flow.request.headers["content-type"]:
        frm = flow.request.get_form_urlencoded()
        frm["mitmproxy"] = ["rocks"]
        flow.request.set_form_urlencoded(frm)



########NEW FILE########
__FILENAME__ = modify_querystring

def request(context, flow):
    q = flow.request.get_query()
    if q:
        q["mitmproxy"] = ["rocks"]
        flow.request.set_query(q)


########NEW FILE########
__FILENAME__ = nonblocking
import time
from libmproxy.script import concurrent

@concurrent
def request(context, flow):
    print "handle request: %s%s" % (flow.request.host, flow.request.path)
    time.sleep(5)
    print "start  request: %s%s" % (flow.request.host, flow.request.path)

########NEW FILE########
__FILENAME__ = redirect_requests
from libmproxy.protocol.http import HTTPResponse
from netlib.odict import ODictCaseless

"""
This example shows two ways to redirect flows to other destinations.
"""


def request(context, flow):
    if flow.request.host.endswith("example.com"):
        resp = HTTPResponse(
            [1, 1], 200, "OK",
            ODictCaseless([["Content-Type", "text/html"]]),
            "helloworld")
        flow.request.reply(resp)
    if flow.request.host.endswith("example.org"):
        flow.request.host = "mitmproxy.org"
        flow.request.headers["Host"] = ["mitmproxy.org"]

########NEW FILE########
__FILENAME__ = stub
"""
    This is a script stub, with definitions for all events.
"""
def start(ctx, argv):
    """
        Called once on script startup, before any other events.
    """
    ctx.log("start")

def clientconnect(ctx, client_connect):
    """
        Called when a client initiates a connection to the proxy. Note that a
        connection can correspond to multiple HTTP requests
    """
    ctx.log("clientconnect")

def serverconnect(ctx, server_connection):
    """
        Called when the proxy initiates a connection to the target server. Note that a
        connection can correspond to multiple HTTP requests
    """
    ctx.log("serverconnect")

def request(ctx, flow):
    """
        Called when a client request has been received.
    """
    ctx.log("request")

def response(ctx, flow):
    """
       Called when a server response has been received.
    """
    ctx.log("response")

def error(ctx, flow):
    """
        Called when a flow error has occured, e.g. invalid server responses, or
        interrupted connections. This is distinct from a valid server HTTP error
        response, which is simply a response with an HTTP error code.
    """
    ctx.log("error")

def clientdisconnect(ctx, client_disconnect):
    """
        Called when a client disconnects from the proxy.
    """
    ctx.log("clientdisconnect")

def done(ctx):
    """
        Called once on script shutdown, after any other events.
    """
    ctx.log("done")

########NEW FILE########
__FILENAME__ = upsidedownternet
import cStringIO
from PIL import Image

def response(context, flow):
    if flow.response.headers["content-type"] == ["image/png"]:
        s = cStringIO.StringIO(flow.response.content)
        img = Image.open(s).rotate(180)
        s2 = cStringIO.StringIO()
        img.save(s2, "png")
        flow.response.content = s2.getvalue()

########NEW FILE########
__FILENAME__ = app
from __future__ import absolute_import
import flask
import os.path, os
from . import proxy

mapp = flask.Flask(__name__)
mapp.debug = True


def master():
    return flask.request.environ["mitmproxy.master"]


@mapp.route("/")
def index():
    return flask.render_template("index.html", section="home")


@mapp.route("/cert/pem")
def certs_pem():
    p = os.path.join(master().server.config.confdir, proxy.config.CONF_BASENAME + "-ca-cert.pem")
    return flask.Response(open(p, "rb").read(), mimetype='application/x-x509-ca-cert')


@mapp.route("/cert/p12")
def certs_p12():
    p = os.path.join(master().server.config.confdir, proxy.config.CONF_BASENAME + "-ca-cert.p12")
    return flask.Response(open(p, "rb").read(), mimetype='application/x-pkcs12')


########NEW FILE########
__FILENAME__ = cmdline
from __future__ import absolute_import
import re
import argparse
from argparse import ArgumentTypeError
from netlib import http
from . import proxy, filt
from .proxy import config

APP_HOST = "mitm.it"
APP_PORT = 80


class ParseException(Exception):
    pass


def _parse_hook(s):
    sep, rem = s[0], s[1:]
    parts = rem.split(sep, 2)
    if len(parts) == 2:
        patt = ".*"
        a, b = parts
    elif len(parts) == 3:
        patt, a, b = parts
    else:
        raise ParseException("Malformed hook specifier - too few clauses: %s"%s)

    if not a:
        raise ParseException("Empty clause: %s"%str(patt))

    if not filt.parse(patt):
        raise ParseException("Malformed filter pattern: %s"%patt)

    return patt, a, b


def parse_replace_hook(s):
    """
        Returns a (pattern, regex, replacement) tuple.

        The general form for a replacement hook is as follows:

            /patt/regex/replacement

        The first character specifies the separator. Example:

            :~q:foo:bar

        If only two clauses are specified, the pattern is set to match
        universally (i.e. ".*"). Example:

            /foo/bar/

        Clauses are parsed from left to right. Extra separators are taken to be
        part of the final clause. For instance, the replacement clause below is
        "foo/bar/":

            /one/two/foo/bar/

        Checks that pattern and regex are both well-formed. Raises
        ParseException on error.
    """
    patt, regex, replacement = _parse_hook(s)
    try:
        re.compile(regex)
    except re.error, e:
        raise ParseException("Malformed replacement regex: %s"%str(e.message))
    return patt, regex, replacement


def parse_setheader(s):
    """
        Returns a (pattern, header, value) tuple.

        The general form for a replacement hook is as follows:

            /patt/header/value

        The first character specifies the separator. Example:

            :~q:foo:bar

        If only two clauses are specified, the pattern is set to match
        universally (i.e. ".*"). Example:

            /foo/bar/

        Clauses are parsed from left to right. Extra separators are taken to be
        part of the final clause. For instance, the value clause below is
        "foo/bar/":

            /one/two/foo/bar/

        Checks that pattern and regex are both well-formed. Raises
        ParseException on error.
    """
    return _parse_hook(s)


def parse_server_spec(url):

    normalized_url = re.sub("^https?2", "", url)

    p = http.parse_url(normalized_url)
    if not p or not p[1]:
        raise ArgumentTypeError("Invalid server specification: %s" % url)

    if url.lower().startswith("https2http"):
        ssl = [True, False]
    elif url.lower().startswith("http2https"):
        ssl = [False, True]
    elif url.lower().startswith("https"):
        ssl = [True, True]
    else:
        ssl = [False, False]

    return ssl + list(p[1:3])


def get_common_options(options):
    stickycookie, stickyauth = None, None
    if options.stickycookie_filt:
        stickycookie = options.stickycookie_filt

    if options.stickyauth_filt:
        stickyauth = options.stickyauth_filt

    reps = []
    for i in options.replace:
        try:
            p = parse_replace_hook(i)
        except ParseException, e:
            raise ArgumentTypeError(e.message)
        reps.append(p)
    for i in options.replace_file:
        try:
            patt, rex, path = parse_replace_hook(i)
        except ParseException, e:
            raise ArgumentTypeError(e.message)
        try:
            v = open(path, "rb").read()
        except IOError, e:
            raise ArgumentTypeError("Could not read replace file: %s"%path)
        reps.append((patt, rex, v))


    setheaders = []
    for i in options.setheader:
        try:
            p = parse_setheader(i)
        except ParseException, e:
            raise ArgumentTypeError(e.message)
        setheaders.append(p)

    return dict(
        app = options.app,
        app_host = options.app_host,
        app_port = options.app_port,
        app_external = options.app_external,

        anticache = options.anticache,
        anticomp = options.anticomp,
        client_replay = options.client_replay,
        kill = options.kill,
        no_server = options.no_server,
        refresh_server_playback = not options.norefresh,
        rheaders = options.rheaders,
        rfile = options.rfile,
        replacements = reps,
        setheaders = setheaders,
        server_replay = options.server_replay,
        scripts = options.scripts,
        stickycookie = stickycookie,
        stickyauth = stickyauth,
        showhost = options.showhost,
        wfile = options.wfile,
        verbosity = options.verbose,
        nopop = options.nopop,
    )


def common_options(parser):
    parser.add_argument(
        "--anticache",
        action="store_true", dest="anticache", default=False,
        help="Strip out request headers that might cause the server to return 304-not-modified."
    )
    parser.add_argument(
        "--confdir",
        action="store", type = str, dest="confdir", default='~/.mitmproxy',
        help = "Configuration directory. (~/.mitmproxy)"
    )
    parser.add_argument(
        "--host",
        action="store_true", dest="showhost", default=False,
        help="Use the Host header to construct URLs for display."
    )
    parser.add_argument(
        "-q",
        action="store_true", dest="quiet",
        help="Quiet."
    )
    parser.add_argument(
        "-r",
        action="store", dest="rfile", default=None,
        help="Read flows from file."
    )
    parser.add_argument(
        "-s",
        action="append", type=str, dest="scripts", default=[],
        metavar='"script.py --bar"',
        help="Run a script. Surround with quotes to pass script arguments. Can be passed multiple times."
    )
    parser.add_argument(
        "-t",
        action="store", dest="stickycookie_filt", default=None, metavar="FILTER",
        help="Set sticky cookie filter. Matched against requests."
    )
    parser.add_argument(
        "-u",
        action="store", dest="stickyauth_filt", default=None, metavar="FILTER",
        help="Set sticky auth filter. Matched against requests."
    )
    parser.add_argument(
        "-v",
        action="store_const", dest="verbose", default=1, const=2,
        help="Increase event log verbosity."
    )
    parser.add_argument(
        "-w",
        action="store", dest="wfile", default=None,
        help="Write flows to file."
    )
    parser.add_argument(
        "-z",
        action="store_true", dest="anticomp", default=False,
        help="Try to convince servers to send us un-compressed data."
    )
    parser.add_argument(
        "-Z",
        action="store", dest="body_size_limit", default=None,
        metavar="SIZE",
        help="Byte size limit of HTTP request and response bodies."\
             " Understands k/m/g suffixes, i.e. 3m for 3 megabytes."
    )


    group = parser.add_argument_group("Proxy Options")
    # We could make a mutually exclusive group out of -R, -F, -T, but we don't do that because
    #  - --upstream-server should be in that group as well, but it's already in a different group.
    #  - our own error messages are more helpful
    group.add_argument(
        "-b",
        action="store", type = str, dest="addr", default='',
        help = "Address to bind proxy to (defaults to all interfaces)"
    )
    group.add_argument(
        "-U",
        action="store", type=parse_server_spec, dest="upstream_proxy", default=None,
        help="Forward all requests to upstream proxy server: http[s]://host[:port]"
    )
    group.add_argument(
        "-n",
        action="store_true", dest="no_server",
        help="Don't start a proxy server."
    )
    group.add_argument(
        "-p",
        action="store", type = int, dest="port", default=8080,
        help = "Proxy service port."
    )
    group.add_argument(
        "-R",
        action="store", type=parse_server_spec, dest="reverse_proxy", default=None,
        help="Forward all requests to upstream HTTP server: http[s][2http[s]]://host[:port]"
    )
    group.add_argument(
        "-T",
        action="store_true", dest="transparent_proxy", default=False,
        help="Set transparent proxy mode."
    )


    group = parser.add_argument_group(
        "Advanced Proxy Options",
        """
            The following options allow a custom adjustment of the proxy behavior.
            Normally, you don't want to use these options directly and use the provided wrappers instead (-R, -F, -T).
        """.strip()
    )
    group.add_argument(
        "--http-form-in", dest="http_form_in", default=None,
        action="store", choices=("relative", "absolute"),
        help="Override the HTTP request form accepted by the proxy"
    )
    group.add_argument(
        "--http-form-out", dest="http_form_out", default=None,
        action="store", choices=("relative", "absolute"),
        help="Override the HTTP request form sent upstream by the proxy"
    )
    group.add_argument(
        "--destination-server", dest="manual_destination_server", default=None,
        action="store", type=parse_server_spec,
        help="Override the destination server all requests are sent to: http[s][2http[s]]://host[:port]"
    )


    group = parser.add_argument_group("Web App")
    group.add_argument(
        "-a",
        action="store_false", dest="app", default=True,
        help="Disable the mitmproxy web app."
    )
    group.add_argument(
        "--app-host",
        action="store", dest="app_host", default=APP_HOST, metavar="host",
        help="Domain to serve the app from. For transparent mode, use an IP when\
                a DNS entry for the app domain is not present. Default: %s"%APP_HOST

    )
    group.add_argument(
        "--app-port",
        action="store", dest="app_port", default=APP_PORT, type=int, metavar="80",
        help="Port to serve the app from."
    )
    group.add_argument(
        "--app-external",
        action="store_true", dest="app_external",
        help="Serve the app outside of the proxy."
    )


    group = parser.add_argument_group("Client Replay")
    group.add_argument(
        "-c",
        action="store", dest="client_replay", default=None, metavar="PATH",
        help="Replay client requests from a saved file."
    )

    group = parser.add_argument_group("Server Replay")
    group.add_argument(
        "-S",
        action="store", dest="server_replay", default=None, metavar="PATH",
        help="Replay server responses from a saved file."
    )
    group.add_argument(
        "-k",
        action="store_true", dest="kill", default=False,
        help="Kill extra requests during replay."
    )
    group.add_argument(
        "--rheader",
        action="append", dest="rheaders", type=str,
        help="Request headers to be considered during replay. "
           "Can be passed multiple times."
    )
    group.add_argument(
        "--norefresh",
        action="store_true", dest="norefresh", default=False,
        help= "Disable response refresh, "
        "which updates times in cookies and headers for replayed responses."
    )
    group.add_argument(
        "--no-pop",
        action="store_true", dest="nopop", default=False,
        help="Disable response pop from response flow. "
        "This makes it possible to replay same response multiple times."
    )


    group = parser.add_argument_group(
        "Replacements",
        """
            Replacements are of the form "/pattern/regex/replacement", where
            the separator can be any character. Please see the documentation
            for more information.
        """.strip()
    )
    group.add_argument(
        "--replace",
        action="append", type=str, dest="replace", default=[],
        metavar="PATTERN",
        help="Replacement pattern."
    )
    group.add_argument(
        "--replace-from-file",
        action="append", type=str, dest="replace_file", default=[],
        metavar="PATH",
        help="Replacement pattern, where the replacement clause is a path to a file."
    )


    group = parser.add_argument_group(
        "Set Headers",
        """
            Header specifications are of the form "/pattern/header/value",
            where the separator can be any character. Please see the
            documentation for more information.
        """.strip()
    )
    group.add_argument(
        "--setheader",
        action="append", type=str, dest="setheader", default=[],
        metavar="PATTERN",
        help="Header set pattern."
    )


    group = parser.add_argument_group(
        "Proxy Authentication",
        """
            Specify which users are allowed to access the proxy and the method
            used for authenticating them. These options are ignored if the
            proxy is in transparent or reverse proxy mode.
        """
    )
    user_specification_group = group.add_mutually_exclusive_group()
    user_specification_group.add_argument(
        "--nonanonymous",
        action="store_true", dest="auth_nonanonymous",
        help="Allow access to any user long as a credentials are specified."
    )

    user_specification_group.add_argument(
        "--singleuser",
        action="store", dest="auth_singleuser", type=str,
        metavar="USER",
        help="Allows access to a a single user, specified in the form username:password."
    )
    user_specification_group.add_argument(
        "--htpasswd",
        action="store", dest="auth_htpasswd", type=argparse.FileType('r'),
        metavar="PATH",
        help="Allow access to users specified in an Apache htpasswd file."
    )


    config.ssl_option_group(parser)

########NEW FILE########
__FILENAME__ = common
from __future__ import absolute_import
import urwid
import urwid.util
from .. import utils
from ..protocol.http import CONTENT_MISSING


VIEW_LIST = 0
VIEW_FLOW = 1


VIEW_FLOW_REQUEST = 0
VIEW_FLOW_RESPONSE = 1


def highlight_key(s, k):
    l = []
    parts = s.split(k, 1)
    if parts[0]:
        l.append(("text", parts[0]))
    l.append(("key", k))
    if parts[1]:
        l.append(("text", parts[1]))
    return l


KEY_MAX = 30
def format_keyvals(lst, key="key", val="text", indent=0):
    """
        Format a list of (key, value) tuples.

        If key is None, it's treated specially:
            - We assume a sub-value, and add an extra indent.
            - The value is treated as a pre-formatted list of directives.
    """
    ret = []
    if lst:
        maxk = min(max(len(i[0]) for i in lst if i and i[0]), KEY_MAX)
        for i, kv in enumerate(lst):
            if kv is None:
                ret.append(urwid.Text(""))
            else:
                cols = []
                # This cumbersome construction process is here for a reason:
                # Urwid < 1.0 barfs if given a fixed size column of size zero.
                if indent:
                    cols.append(("fixed", indent, urwid.Text("")))
                cols.extend([
                    (
                        "fixed",
                        maxk,
                        urwid.Text([(key, kv[0] or "")])
                    ),
                    kv[1] if isinstance(kv[1], urwid.Widget) else urwid.Text([(val, kv[1])])
               ])
                ret.append(urwid.Columns(cols, dividechars = 2))
    return ret


def shortcuts(k):
    if k == " ":
        k = "page down"
    elif k == "j":
        k = "down"
    elif k == "k":
        k = "up"
    return k


def fcol(s, attr):
    s = unicode(s)
    return (
        "fixed",
        len(s),
        urwid.Text(
            [
                (attr, s)
            ]
        )
    )

if urwid.util.detected_encoding:
    SYMBOL_REPLAY = u"\u21ba"
    SYMBOL_RETURN = u"\u2190"
else:
    SYMBOL_REPLAY = u"[r]"
    SYMBOL_RETURN = u"<-"



def raw_format_flow(f, focus, extended, padding):
    f = dict(f)

    pile = []
    req = []
    if extended:
        req.append(
            fcol(
                utils.format_timestamp(f["req_timestamp"]),
                "highlight"
            )
        )
    else:
        req.append(fcol(">>" if focus else "  ", "focus"))
    if f["req_is_replay"]:
        req.append(fcol(SYMBOL_REPLAY, "replay"))
    req.append(fcol(f["req_method"], "method"))

    preamble = sum(i[1] for i in req) + len(req) -1

    if f["intercepting"] and not f["req_acked"]:
        uc = "intercept"
    elif f["resp_code"] or f["err_msg"]:
        uc = "text"
    else:
        uc = "title"

    req.append(
        urwid.Text([(uc, f["req_url"])])
    )

    pile.append(urwid.Columns(req, dividechars=1))

    resp = []
    resp.append(
        ("fixed", preamble, urwid.Text(""))
    )

    if f["resp_code"]:
        codes = {
            2: "code_200",
            3: "code_300",
            4: "code_400",
            5: "code_500",
        }
        ccol = codes.get(f["resp_code"]/100, "code_other")
        resp.append(fcol(SYMBOL_RETURN, ccol))
        if f["resp_is_replay"]:
            resp.append(fcol(SYMBOL_REPLAY, "replay"))
        resp.append(fcol(f["resp_code"], ccol))
        if f["intercepting"] and f["resp_code"] and not f["resp_acked"]:
            rc = "intercept"
        else:
            rc = "text"

        if f["resp_ctype"]:
            resp.append(fcol(f["resp_ctype"], rc))
        resp.append(fcol(f["resp_clen"], rc))
        resp.append(fcol(f["resp_rate"], rc))

    elif f["err_msg"]:
        resp.append(fcol(SYMBOL_RETURN, "error"))
        resp.append(
            urwid.Text([
                (
                    "error",
                    f["err_msg"]
                )
            ])
        )
    pile.append(urwid.Columns(resp, dividechars=1))
    return urwid.Pile(pile)


class FlowCache:
    @utils.LRUCache(200)
    def format_flow(self, *args):
        return raw_format_flow(*args)
flowcache = FlowCache()


def format_flow(f, focus, extended=False, hostheader=False, padding=2):
    d = dict(
        intercepting = f.intercepting,

        req_timestamp = f.request.timestamp_start,
        req_is_replay = f.request.is_replay,
        req_method = f.request.method,
        req_acked = f.request.reply.acked,
        req_url = f.request.get_url(hostheader=hostheader),

        err_msg = f.error.msg if f.error else None,
        resp_code = f.response.code if f.response else None,
    )
    if f.response:
        if f.response.content:
            contentdesc = utils.pretty_size(len(f.response.content))
        elif f.response.content == CONTENT_MISSING:
            contentdesc = "[content missing]"
        else:
            contentdesc = "[no content]"

        delta = f.response.timestamp_end - f.response.timestamp_start
        size = f.response.size()
        rate = utils.pretty_size(size / ( delta if delta > 0 else 1 ) )

        d.update(dict(
            resp_code = f.response.code,
            resp_is_replay = f.response.is_replay,
            resp_acked = f.response.reply.acked,
            resp_clen = contentdesc,
            resp_rate = "{0}/s".format(rate),
        ))
        t = f.response.headers["content-type"]
        if t:
            d["resp_ctype"] = t[0].split(";")[0]
        else:
            d["resp_ctype"] = ""
    return flowcache.format_flow(tuple(sorted(d.items())), focus, extended, padding)



def int_version(v):
    SIG = 3
    v = urwid.__version__.split("-")[0].split(".")
    x = 0
    for i in range(min(SIG, len(v))):
        x += int(v[i]) * 10**(SIG-i)
    return x


# We have to do this to be portable over 0.9.8 and 0.9.9 If compatibility
# becomes a pain to maintain, we'll just mandate 0.9.9 or newer.
class WWrap(urwid.WidgetWrap):
    if int_version(urwid.__version__) >= 990:
        def set_w(self, x):
            self._w = x
        def get_w(self):
            return self._w
        w = property(get_w, set_w)



########NEW FILE########
__FILENAME__ = contentview
from __future__ import absolute_import
import logging, subprocess, re, cStringIO, traceback, json, urwid
from PIL import Image
from PIL.ExifTags import TAGS

import lxml.html, lxml.etree
import netlib.utils
from . import common
from .. import utils, encoding, flow
from ..contrib import jsbeautifier, html2text
from ..contrib.wbxml.ASCommandResponse import ASCommandResponse
try:
    import pyamf
    from pyamf import remoting, flex
except ImportError: # pragma nocover
    pyamf = None

try:
    import cssutils
except ImportError: # pragma nocover
    cssutils = None
else:
    cssutils.log.setLevel(logging.CRITICAL)

    cssutils.ser.prefs.keepComments = True
    cssutils.ser.prefs.omitLastSemicolon = False
    cssutils.ser.prefs.indentClosingBrace = False
    cssutils.ser.prefs.validOnly = False

VIEW_CUTOFF = 1024*50


def _view_text(content, total, limit):
    """
        Generates a body for a chunk of text.
    """
    txt = []
    for i in netlib.utils.cleanBin(content).splitlines():
        txt.append(
            urwid.Text(("text", i), wrap="any")
        )
    trailer(total, txt, limit)
    return txt


def trailer(clen, txt, limit):
    rem = clen - limit
    if rem > 0:
        txt.append(urwid.Text(""))
        txt.append(
            urwid.Text(
                [
                    ("highlight", "... %s of data not shown. Press "%utils.pretty_size(rem)),
                    ("key", "f"),
                    ("highlight", " to load all data.")
                ]
            )
        )


class ViewAuto:
    name = "Auto"
    prompt = ("auto", "a")
    content_types = []
    def __call__(self, hdrs, content, limit):
        ctype = hdrs.get_first("content-type")
        if ctype:
            ct = utils.parse_content_type(ctype) if ctype else None
            ct = "%s/%s"%(ct[0], ct[1])
            if ct in content_types_map:
                return content_types_map[ct][0](hdrs, content, limit)
            elif utils.isXML(content):
                return get("XML")(hdrs, content, limit)
        return get("Raw")(hdrs, content, limit)


class ViewRaw:
    name = "Raw"
    prompt = ("raw", "r")
    content_types = []
    def __call__(self, hdrs, content, limit):
        txt = _view_text(content[:limit], len(content), limit)
        return "Raw", txt


class ViewHex:
    name = "Hex"
    prompt = ("hex", "e")
    content_types = []
    def __call__(self, hdrs, content, limit):
        txt = []
        for offset, hexa, s in netlib.utils.hexdump(content[:limit]):
            txt.append(urwid.Text([
                ("offset", offset),
                " ",
                ("text", hexa),
                "   ",
                ("text", s),
            ]))
        trailer(len(content), txt, limit)
        return "Hex", txt


class ViewXML:
    name = "XML"
    prompt = ("xml", "x")
    content_types = ["text/xml"]
    def __call__(self, hdrs, content, limit):
        parser = lxml.etree.XMLParser(remove_blank_text=True, resolve_entities=False, strip_cdata=False, recover=False)
        try:
            document = lxml.etree.fromstring(content, parser)
        except lxml.etree.XMLSyntaxError:
            return None
        docinfo = document.getroottree().docinfo

        prev = []
        p = document.getroottree().getroot().getprevious()
        while p is not None:
            prev.insert(
                0,
                lxml.etree.tostring(p)
            )
            p = p.getprevious()
        doctype=docinfo.doctype
        if prev:
            doctype += "\n".join(prev).strip()
        doctype = doctype.strip()

        s = lxml.etree.tostring(
                document,
                pretty_print=True,
                xml_declaration=True,
                doctype=doctype or None,
                encoding = docinfo.encoding
            )

        txt = []
        for i in s[:limit].strip().split("\n"):
            txt.append(
                urwid.Text(("text", i)),
            )
        trailer(len(content), txt, limit)
        return "XML-like data", txt


class ViewJSON:
    name = "JSON"
    prompt = ("json", "s")
    content_types = ["application/json"]
    def __call__(self, hdrs, content, limit):
        lines = utils.pretty_json(content)
        if lines:
            txt = []
            sofar = 0
            for i in lines:
                sofar += len(i)
                txt.append(
                    urwid.Text(("text", i)),
                )
                if sofar > limit:
                    break
            trailer(sum(len(i) for i in lines), txt, limit)
            return "JSON", txt


class ViewHTML:
    name = "HTML"
    prompt = ("html", "h")
    content_types = ["text/html"]
    def __call__(self, hdrs, content, limit):
        if utils.isXML(content):
            parser = lxml.etree.HTMLParser(strip_cdata=True, remove_blank_text=True)
            d = lxml.html.fromstring(content, parser=parser)
            docinfo = d.getroottree().docinfo
            s = lxml.etree.tostring(d, pretty_print=True, doctype=docinfo.doctype)
            return "HTML", _view_text(s[:limit], len(s), limit)


class ViewHTMLOutline:
    name = "HTML Outline"
    prompt = ("html outline", "o")
    content_types = ["text/html"]
    def __call__(self, hdrs, content, limit):
        content = content.decode("utf-8")
        h = html2text.HTML2Text(baseurl="")
        h.ignore_images = True
        h.body_width = 0
        content = h.handle(content)
        txt = _view_text(content[:limit], len(content), limit)
        return "HTML Outline", txt


class ViewURLEncoded:
    name = "URL-encoded"
    prompt = ("urlencoded", "u")
    content_types = ["application/x-www-form-urlencoded"]
    def __call__(self, hdrs, content, limit):
        lines = utils.urldecode(content)
        if lines:
            body = common.format_keyvals(
                        [(k+":", v) for (k, v) in lines],
                        key = "header",
                        val = "text"
                   )
            return "URLEncoded form", body


class ViewMultipart:
    name = "Multipart Form"
    prompt = ("multipart", "m")
    content_types = ["multipart/form-data"]
    def __call__(self, hdrs, content, limit):
        v = hdrs.get_first("content-type")
        if v:
            v = utils.parse_content_type(v)
            if not v:
                return
            boundary = v[2].get("boundary")
            if not boundary:
                return

            rx = re.compile(r'\bname="([^"]+)"')
            keys = []
            vals = []

            for i in content.split("--" + boundary):
                parts = i.splitlines()
                if len(parts) > 1 and parts[0][0:2] != "--":
                    match = rx.search(parts[1])
                    if match:
                        keys.append(match.group(1) + ":")
                        vals.append(netlib.utils.cleanBin(
                            "\n".join(parts[3+parts[2:].index(""):])
                        ))
            r = [
                urwid.Text(("highlight", "Form data:\n")),
            ]
            r.extend(common.format_keyvals(
                zip(keys, vals),
                key = "header",
                val = "text"
            ))
            return "Multipart form", r


if pyamf:
    class DummyObject(dict):
        def __init__(self, alias):
            dict.__init__(self)

        def __readamf__(self, input):
            data = input.readObject()
            self["data"] = data

    def pyamf_class_loader(s):
        for i in pyamf.CLASS_LOADERS:
            if i != pyamf_class_loader:
                v = i(s)
                if v:
                    return v
        return DummyObject

    pyamf.register_class_loader(pyamf_class_loader)

    class ViewAMF:
        name = "AMF"
        prompt = ("amf", "f")
        content_types = ["application/x-amf"]

        def unpack(self, b, seen=set([])):
            if hasattr(b, "body"):
                return self.unpack(b.body, seen)
            if isinstance(b, DummyObject):
                if id(b) in seen:
                    return "<recursion>"
                else:
                    seen.add(id(b))
                    for k, v in b.items():
                        b[k] = self.unpack(v, seen)
                    return b
            elif isinstance(b, dict):
                for k, v in b.items():
                    b[k] = self.unpack(v, seen)
                return b
            elif isinstance(b, list):
                return [self.unpack(i) for i in b]
            elif isinstance(b, flex.ArrayCollection):
                return [self.unpack(i, seen) for i in b]
            else:
                return b

        def __call__(self, hdrs, content, limit):
            envelope = remoting.decode(content, strict=False)
            if not envelope:
                return None


            txt = []
            for target, message in iter(envelope):
                if isinstance(message, pyamf.remoting.Request):
                    txt.append(urwid.Text([
                        ("header", "Request: "),
                        ("text", str(target)),
                    ]))
                else:
                    txt.append(urwid.Text([
                        ("header", "Response: "),
                        ("text", "%s, code %s"%(target, message.status)),
                    ]))

                s = json.dumps(self.unpack(message), indent=4)
                txt.extend(_view_text(s[:limit], len(s), limit))

            return "AMF v%s"%envelope.amfVersion, txt


class ViewJavaScript:
    name = "JavaScript"
    prompt = ("javascript", "j")
    content_types = [
        "application/x-javascript",
        "application/javascript",
        "text/javascript"
    ]
    def __call__(self, hdrs, content, limit):
        opts = jsbeautifier.default_options()
        opts.indent_size = 2
        res = jsbeautifier.beautify(content[:limit], opts)
        return "JavaScript", _view_text(res, len(res), limit)

class ViewCSS:
    name = "CSS"
    prompt = ("css", "c")
    content_types = [
        "text/css"
    ]

    def __call__(self, hdrs, content, limit):
        if cssutils:
            sheet = cssutils.parseString(content)
            beautified = sheet.cssText
        else:
            beautified = content

        return "CSS", _view_text(beautified, len(beautified), limit)


class ViewImage:
    name = "Image"
    prompt = ("image", "i")
    content_types = [
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/vnd.microsoft.icon",
        "image/x-icon",
    ]
    def __call__(self, hdrs, content, limit):
        try:
            img = Image.open(cStringIO.StringIO(content))
        except IOError:
            return None
        parts = [
            ("Format", str(img.format_description)),
            ("Size", "%s x %s px"%img.size),
            ("Mode", str(img.mode)),
        ]
        for i in sorted(img.info.keys()):
            if i != "exif":
                parts.append(
                    (str(i), str(img.info[i]))
                )
        if hasattr(img, "_getexif"):
            ex = img._getexif()
            if ex:
                for i in sorted(ex.keys()):
                    tag = TAGS.get(i, i)
                    parts.append(
                        (str(tag), str(ex[i]))
                    )
        clean = []
        for i in parts:
            clean.append([netlib.utils.cleanBin(i[0]), netlib.utils.cleanBin(i[1])])
        fmt = common.format_keyvals(
                clean,
                key = "header",
                val = "text"
            )
        return "%s image"%img.format, fmt

class ViewProtobuf:
    """Human friendly view of protocol buffers
    The view uses the protoc compiler to decode the binary
    """

    name = "Protocol Buffer"
    prompt = ("protobuf", "p")
    content_types = [
        "application/x-protobuf",
        "application/x-protobuffer",
    ]

    @staticmethod
    def is_available():
        try:
            p = subprocess.Popen(["protoc", "--version"], stdout=subprocess.PIPE)
            out, _ = p.communicate()
            return out.startswith("libprotoc")
        except:
            return False

    def decode_protobuf(self, content):
        # if Popen raises OSError, it will be caught in
        # get_content_view and fall back to Raw
        p = subprocess.Popen(['protoc', '--decode_raw'],
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        out, err = p.communicate(input=content)
        if out:
            return out
        else:
            return err

    def __call__(self, hdrs, content, limit):
        decoded = self.decode_protobuf(content)
        txt = _view_text(decoded[:limit], len(decoded), limit)
        return "Protobuf", txt

class ViewWBXML:
    name = "WBXML"
    prompt = ("wbxml", "w")
    content_types = [
        "application/vnd.wap.wbxml",
        "application/vnd.ms-sync.wbxml"
    ]

    def __call__(self, hdrs, content, limit):
        
        try:
            parser = ASCommandResponse(content)
            parsedContent = parser.xmlString
            txt = _view_text(parsedContent, len(parsedContent), limit)
            return "WBXML", txt
        except:
        	return None

views = [
    ViewAuto(),
    ViewRaw(),
    ViewHex(),
    ViewJSON(),
    ViewXML(),
    ViewWBXML(),
    ViewHTML(),
    ViewHTMLOutline(),
    ViewJavaScript(),
    ViewCSS(),
    ViewURLEncoded(),
    ViewMultipart(),
    ViewImage(),
]
if pyamf:
    views.append(ViewAMF())

if ViewProtobuf.is_available():
    views.append(ViewProtobuf())

content_types_map = {}
for i in views:
    for ct in i.content_types:
        l = content_types_map.setdefault(ct, [])
        l.append(i)


view_prompts = [i.prompt for i in views]


def get_by_shortcut(c):
    for i in views:
        if i.prompt[1] == c:
            return i


def get(name):
    for i in views:
        if i.name == name:
            return i


def get_content_view(viewmode, hdrItems, content, limit, logfunc):
    """
        Returns a (msg, body) tuple.
    """
    if not content:
        return ("No content", "")
    msg = []

    hdrs = flow.ODictCaseless([list(i) for i in hdrItems])

    enc = hdrs.get_first("content-encoding")
    if enc and enc != "identity":
        decoded = encoding.decode(enc, content)
        if decoded:
            content = decoded
            msg.append("[decoded %s]"%enc)
    try:
        ret = viewmode(hdrs, content, limit)
    # Third-party viewers can fail in unexpected ways...
    except Exception:
        s = traceback.format_exc()
        s = "Content viewer failed: \n"  + s
        logfunc(s, "error")
        ret = None
    if not ret:
        ret = get("Raw")(hdrs, content, limit)
        msg.append("Couldn't parse: falling back to Raw")
    else:
        msg.append(ret[0])
    return " ".join(msg), ret[1]

########NEW FILE########
__FILENAME__ = flowdetailview
from __future__ import absolute_import
import urwid
from . import common
from .. import utils

footer = [
    ('heading_key', "q"), ":back ",
]

class FlowDetailsView(urwid.ListBox):
    def __init__(self, master, flow, state):
        self.master, self.flow, self.state = master, flow, state
        urwid.ListBox.__init__(
            self,
            self.flowtext()
        )

    def keypress(self, size, key):
        key = common.shortcuts(key)
        if key == "q":
            self.master.statusbar = self.state[0]
            self.master.body = self.state[1]
            self.master.header = self.state[2]
            self.master.make_view()
            return None
        elif key == "?":
            key = None
        return urwid.ListBox.keypress(self, size, key)

    def flowtext(self):
        text = []

        title = urwid.Text("Flow details")
        title = urwid.Padding(title, align="left", width=("relative", 100))
        title = urwid.AttrWrap(title, "heading")
        text.append(title)

        if self.flow.server_conn:
            text.append(urwid.Text([("head", "Server Connection:")]))
            sc = self.flow.server_conn
            parts = [
                ["Address", "%s:%s" % sc.peername],
                ["Start time", utils.format_timestamp(sc.timestamp_start)],
                ["End time", utils.format_timestamp(sc.timestamp_end) if sc.timestamp_end else "active"],
            ]
            text.extend(common.format_keyvals(parts, key="key", val="text", indent=4))

            c = self.flow.server_conn.cert
            if c:
                text.append(urwid.Text([("head", "Server Certificate:")]))
                parts = [
                    ["Type", "%s, %s bits"%c.keyinfo],
                    ["SHA1 digest", c.digest("sha1")],
                    ["Valid to", str(c.notafter)],
                    ["Valid from", str(c.notbefore)],
                    ["Serial", str(c.serial)],
                    [
                        "Subject",
                        urwid.BoxAdapter(
                            urwid.ListBox(common.format_keyvals(c.subject, key="highlight", val="text")),
                            len(c.subject)
                        )
                    ],
                    [
                        "Issuer",
                        urwid.BoxAdapter(
                            urwid.ListBox(common.format_keyvals(c.issuer, key="highlight", val="text")),
                            len(c.issuer)
                        )
                    ]
                ]

                if c.altnames:
                    parts.append(
                        [
                            "Alt names",
                            ", ".join(c.altnames)
                        ]
                    )
                text.extend(common.format_keyvals(parts, key="key", val="text", indent=4))

        if self.flow.client_conn:
            text.append(urwid.Text([("head", "Client Connection:")]))
            cc = self.flow.client_conn
            parts = [
                ["Address", "%s:%s" % cc.address()],
                ["Start time", utils.format_timestamp(cc.timestamp_start)],
                # ["Requests", "%s"%cc.requestcount],
                ["End time", utils.format_timestamp(cc.timestamp_end) if cc.timestamp_end else "active"],
            ]
            text.extend(common.format_keyvals(parts, key="key", val="text", indent=4))

        return text

########NEW FILE########
__FILENAME__ = flowlist
from __future__ import absolute_import
import urwid
from . import common

def _mkhelp():
    text = []
    keys = [
        ("A", "accept all intercepted flows"),
        ("a", "accept this intercepted flow"),
        ("C", "clear flow list or eventlog"),
        ("d", "delete flow"),
        ("D", "duplicate flow"),
        ("e", "toggle eventlog"),
        ("F", "toggle follow flow list"),
        ("l", "set limit filter pattern"),
        ("L", "load saved flows"),
        ("r", "replay request"),
        ("V", "revert changes to request"),
        ("w", "save flows "),
        ("W", "stream flows to file"),
        ("X", "kill and delete flow, even if it's mid-intercept"),
        ("tab", "tab between eventlog and flow list"),
        ("enter", "view flow"),
        ("|", "run script on this flow"),
    ]
    text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))
    return text
help_context = _mkhelp()

footer = [
    ('heading_key', "?"), ":help ",
]

class EventListBox(urwid.ListBox):
    def __init__(self, master):
        self.master = master
        urwid.ListBox.__init__(self, master.eventlist)

    def keypress(self, size, key):
        key = common.shortcuts(key)
        if key == "C":
            self.master.clear_events()
            key = None
        return urwid.ListBox.keypress(self, size, key)


class BodyPile(urwid.Pile):
    def __init__(self, master):
        h = urwid.Text("Event log")
        h = urwid.Padding(h, align="left", width=("relative", 100))

        self.inactive_header = urwid.AttrWrap(h, "heading_inactive")
        self.active_header = urwid.AttrWrap(h, "heading")

        urwid.Pile.__init__(
            self,
            [
                FlowListBox(master),
                urwid.Frame(EventListBox(master), header = self.inactive_header)
            ]
        )
        self.master = master

    def keypress(self, size, key):
        if key == "tab":
            self.focus_position = (self.focus_position + 1)%len(self.widget_list)
            if self.focus_position == 1:
                self.widget_list[1].header = self.active_header
            else:
                self.widget_list[1].header = self.inactive_header
            key = None
        elif key == "e":
            self.master.toggle_eventlog()
            key = None

        # This is essentially a copypasta from urwid.Pile's keypress handler.
        # So much for "closed for modification, but open for extension".
        item_rows = None
        if len(size)==2:
            item_rows = self.get_item_rows( size, focus=True )
        i = self.widget_list.index(self.focus_item)
        tsize = self.get_item_size(size,i,True,item_rows)
        return self.focus_item.keypress( tsize, key )


class ConnectionItem(common.WWrap):
    def __init__(self, master, state, flow, focus):
        self.master, self.state, self.flow = master, state, flow
        self.f = focus
        w = self.get_text()
        common.WWrap.__init__(self, w)

    def get_text(self):
        return common.format_flow(self.flow, self.f, hostheader=self.master.showhost)

    def selectable(self):
        return True

    def save_flows_prompt(self, k):
        if k == "a":
            self.master.path_prompt(
                "Save all flows to: ",
                self.state.last_saveload,
                self.master.save_flows
            )
        else:
            self.master.path_prompt(
                "Save this flow to: ",
                self.state.last_saveload,
                self.master.save_one_flow,
                self.flow
            )

    def stop_server_playback_prompt(self, a):
        if a != "n":
            self.master.stop_server_playback()

    def server_replay_prompt(self, k):
        if k == "a":
            self.master.start_server_playback(
                [i.copy() for i in self.master.state.view],
                self.master.killextra, self.master.rheaders,
                False, self.master.nopop
            )
        elif k == "t":
            self.master.start_server_playback(
                [self.flow.copy()],
                self.master.killextra, self.master.rheaders,
                False, self.master.nopop
            )
        else:
            self.master.path_prompt(
                "Server replay path: ",
                self.state.last_saveload,
                self.master.server_playback_path
            )

    def keypress(self, (maxcol,), key):
        key = common.shortcuts(key)
        if key == "a":
            self.flow.accept_intercept()
            self.master.sync_list_view()
        elif key == "d":
            self.flow.kill(self.master)
            self.state.delete_flow(self.flow)
            self.master.sync_list_view()
        elif key == "D":
            f = self.master.duplicate_flow(self.flow)
            self.master.view_flow(f)
        elif key == "r":
            self.flow.backup()
            r = self.master.replay_request(self.flow)
            if r:
                self.master.statusbar.message(r)
            self.master.sync_list_view()
        elif key == "S":
            if not self.master.server_playback:
                self.master.prompt_onekey(
                    "Server Replay",
                    (
                        ("all flows", "a"),
                        ("this flow", "t"),
                        ("file", "f"),
                    ),
                    self.server_replay_prompt,
                )
            else:
                self.master.prompt_onekey(
                    "Stop current server replay?",
                    (
                        ("yes", "y"),
                        ("no", "n"),
                    ),
                    self.stop_server_playback_prompt,
                )
        elif key == "V":
            if not self.flow.modified():
                self.master.statusbar.message("Flow not modified.")
                return
            self.state.revert(self.flow)
            self.master.sync_list_view()
            self.master.statusbar.message("Reverted.")
        elif key == "w":
            self.master.prompt_onekey(
                "Save",
                (
                    ("all flows", "a"),
                    ("this flow", "t"),
                ),
                self.save_flows_prompt,
            )
        elif key == "X":
            self.flow.kill(self.master)
        elif key == "enter":
            if self.flow.request:
                self.master.view_flow(self.flow)
        elif key == "|":
            self.master.path_prompt(
                "Send flow to script: ",
                self.state.last_script,
                self.master.run_script_once,
                self.flow
            )
        else:
            return key


class FlowListWalker(urwid.ListWalker):
    def __init__(self, master, state):
        self.master, self.state = master, state
        if self.state.flow_count():
            self.set_focus(0)

    def get_focus(self):
        f, i = self.state.get_focus()
        f = ConnectionItem(self.master, self.state, f, True) if f else None
        return f, i

    def set_focus(self, focus):
        ret = self.state.set_focus(focus)
        return ret

    def get_next(self, pos):
        f, i = self.state.get_next(pos)
        f = ConnectionItem(self.master, self.state, f, False) if f else None
        return f, i

    def get_prev(self, pos):
        f, i = self.state.get_prev(pos)
        f = ConnectionItem(self.master, self.state, f, False) if f else None
        return f, i


class FlowListBox(urwid.ListBox):
    def __init__(self, master):
        self.master = master
        urwid.ListBox.__init__(self, master.flow_list_walker)

    def keypress(self, size, key):
        key = common.shortcuts(key)
        if key == "A":
            self.master.accept_all()
            self.master.sync_list_view()
        elif key == "C":
            self.master.clear_flows()
        elif key == "e":
            self.master.toggle_eventlog()
        elif key == "l":
            self.master.prompt("Limit: ", self.master.state.limit_txt, self.master.set_limit)
        elif key == "L":
            self.master.path_prompt(
                "Load flows: ",
                self.master.state.last_saveload,
                self.master.load_flows_callback
            )
        elif key == "F":
            self.master.toggle_follow_flows()
        elif key == "W":
            if self.master.stream:
                self.master.stop_stream()
            else:
                self.master.path_prompt(
                    "Stream flows to: ",
                    self.master.state.last_saveload,
                    self.master.start_stream
                )
        else:
            return urwid.ListBox.keypress(self, size, key)

########NEW FILE########
__FILENAME__ = flowview
from __future__ import absolute_import
import os, sys, copy
import urwid
from . import common, grideditor, contentview
from .. import utils, flow, controller
from ..protocol.http import HTTPResponse, CONTENT_MISSING


class SearchError(Exception): pass


def _mkhelp():
    text = []
    keys = [
        ("A", "accept all intercepted flows"),
        ("a", "accept this intercepted flow"),
        ("b", "save request/response body"),
        ("d", "delete flow"),
        ("D", "duplicate flow"),
        ("e", "edit request/response"),
        ("f", "load full body data"),
        ("m", "change body display mode for this entity"),
            (None,
                common.highlight_key("automatic", "a") +
                [("text", ": automatic detection")]
            ),
            (None,
                common.highlight_key("hex", "e") +
                [("text", ": Hex")]
            ),
            (None,
                common.highlight_key("html", "h") +
                [("text", ": HTML")]
            ),
            (None,
                common.highlight_key("image", "i") +
                [("text", ": Image")]
            ),
            (None,
                common.highlight_key("javascript", "j") +
                [("text", ": JavaScript")]
            ),
            (None,
                common.highlight_key("json", "s") +
                [("text", ": JSON")]
            ),
            (None,
                common.highlight_key("urlencoded", "u") +
                [("text", ": URL-encoded data")]
            ),
            (None,
                common.highlight_key("raw", "r") +
                [("text", ": raw data")]
            ),
            (None,
                common.highlight_key("xml", "x") +
                [("text", ": XML")]
            ),
        ("M", "change default body display mode"),
        ("p", "previous flow"),
        ("r", "replay request"),
        ("V", "revert changes to request"),
        ("v", "view body in external viewer"),
        ("w", "save all flows matching current limit"),
        ("W", "save this flow"),
        ("x", "delete body"),
        ("X", "view flow details"),
        ("z", "encode/decode a request/response"),
        ("tab", "toggle request/response view"),
        ("space", "next flow"),
        ("|", "run script on this flow"),
        ("/", "search in response body (case sensitive)"),
        ("n", "repeat search forward"),
        ("N", "repeat search backwards"),
    ]
    text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))
    return text
help_context = _mkhelp()

footer = [
    ('heading_key', "?"), ":help ",
    ('heading_key', "q"), ":back ",
]


class FlowViewHeader(common.WWrap):
    def __init__(self, master, f):
        self.master, self.flow = master, f
        self.w = common.format_flow(f, False, extended=True, padding=0, hostheader=self.master.showhost)

    def refresh_flow(self, f):
        if f == self.flow:
            self.w = common.format_flow(f, False, extended=True, padding=0, hostheader=self.master.showhost)


class CallbackCache:
    @utils.LRUCache(200)
    def _callback(self, method, *args, **kwargs):
        return getattr(self.obj, method)(*args, **kwargs)

    def callback(self, obj, method, *args, **kwargs):
        # obj varies!
        self.obj = obj
        return self._callback(method, *args, **kwargs)
cache = CallbackCache()


class FlowView(common.WWrap):
    REQ = 0
    RESP = 1
    method_options = [
        ("get", "g"),
        ("post", "p"),
        ("put", "u"),
        ("head", "h"),
        ("trace", "t"),
        ("delete", "d"),
        ("options", "o"),
        ("edit raw", "e"),
    ]

    highlight_color = "focusfield"

    def __init__(self, master, state, flow):
        self.master, self.state, self.flow = master, state, flow
        self.last_displayed_body = None
        if self.state.view_flow_mode == common.VIEW_FLOW_RESPONSE:
            self.view_response()
        else:
            self.view_request()

    def _cached_content_view(self, viewmode, hdrItems, content, limit):
        return contentview.get_content_view(viewmode, hdrItems, content, limit, self.master.add_event)

    def content_view(self, viewmode, conn):
        full = self.state.get_flow_setting(
            self.flow,
            (self.state.view_flow_mode, "fullcontents"),
            False
        )
        if full:
            limit = sys.maxint
        else:
            limit = contentview.VIEW_CUTOFF
        description, text_objects = cache.callback(
                    self, "_cached_content_view",
                    viewmode,
                    tuple(tuple(i) for i in conn.headers.lst),
                    conn.content,
                    limit
                )
        return (description, text_objects)

    def cont_view_handle_missing(self, conn, viewmode):
            if conn.content == CONTENT_MISSING:
                msg, body = "", [urwid.Text([("error", "[content missing]")])], 0
            else:
                msg, body = self.content_view(viewmode, conn)

            return (msg, body)

    def viewmode_get(self, override):
        return self.state.default_body_view if override is None else override

    def override_get(self):
        return self.state.get_flow_setting(self.flow,
                (self.state.view_flow_mode, "prettyview"))

    def conn_text_raw(self, conn):
        """
            Based on a request/response, conn, returns the elements for
            display.
        """
        headers = common.format_keyvals(
                [(h+":", v) for (h, v) in conn.headers.lst],
                key = "header",
                val = "text"
            )
        if conn.content is not None:
            override = self.override_get()
            viewmode = self.viewmode_get(override)
            msg, body = self.cont_view_handle_missing(conn, viewmode)
        elif conn.content == CONTENT_MISSING:
            pass
        return headers, msg, body

    def conn_text_merge(self, headers, msg, body):
        """
            Grabs what is returned by conn_text_raw and merges them all
            toghether, mainly used by conn_text and search
        """
        override = self.override_get()
        viewmode = self.viewmode_get(override)

        cols = [urwid.Text(
                [
                    ("heading", msg),
                ]
            )
        ]

        if override is not None:
            cols.append(urwid.Text([
                        " ",
                        ('heading', "["),
                        ('heading_key', "m"),
                        ('heading', (":%s]"%viewmode.name)),
                    ],
                    align="right"
                )
            )

        title = urwid.AttrWrap(urwid.Columns(cols), "heading")
        headers.append(title)
        headers.extend(body)

        return headers

    def conn_text(self, conn):
        """
        Same as conn_text_raw, but returns result wrapped in a listbox ready for usage.
        """
        headers, msg, body = self.conn_text_raw(conn)
        merged = self.conn_text_merge(headers, msg, body)
        return urwid.ListBox(merged)

    def _tab(self, content, attr):
        p = urwid.Text(content)
        p = urwid.Padding(p, align="left", width=("relative", 100))
        p = urwid.AttrWrap(p, attr)
        return p

    def wrap_body(self, active, body):
        parts = []

        if self.flow.intercepting and not self.flow.request.reply.acked:
            qt = "Request intercepted"
        else:
            qt = "Request"
        if active == common.VIEW_FLOW_REQUEST:
            parts.append(self._tab(qt, "heading"))
        else:
            parts.append(self._tab(qt, "heading_inactive"))

        if self.flow.intercepting and self.flow.response and not self.flow.response.reply.acked:
            st = "Response intercepted"
        else:
            st = "Response"
        if active == common.VIEW_FLOW_RESPONSE:
            parts.append(self._tab(st, "heading"))
        else:
            parts.append(self._tab(st, "heading_inactive"))

        h = urwid.Columns(parts)
        f = urwid.Frame(
                    body,
                    header=h
                )
        return f

    def search_wrapped_around(self, last_find_line, last_search_index, backwards):
        """
            returns true if search wrapped around the bottom.
        """

        current_find_line = self.state.get_flow_setting(self.flow,
                "last_find_line")
        current_search_index = self.state.get_flow_setting(self.flow,
                "last_search_index")

        if not backwards:
            message = "search hit BOTTOM, continuing at TOP"
            if current_find_line <= last_find_line:
                return True, message
            elif current_find_line == last_find_line:
                if current_search_index <= last_search_index:
                    return True, message
        else:
            message = "search hit TOP, continuing at BOTTOM"
            if current_find_line >= last_find_line:
                return True, message
            elif current_find_line == last_find_line:
                if current_search_index >= last_search_index:
                    return True, message

        return False, ""

    def search_again(self, backwards=False):
        """
            runs the previous search again, forwards or backwards.
        """
        last_search_string = self.state.get_flow_setting(self.flow, "last_search_string")
        if last_search_string:
            message = self.search(last_search_string, backwards)
            if message:
                self.master.statusbar.message(message)
        else:
            message = "no previous searches have been made"
            self.master.statusbar.message(message)

        return message

    def search(self, search_string, backwards=False):
        """
            similar to view_response or view_request, but instead of just
            displaying the conn, it highlights a word that the user is
            searching for and handles all the logic surrounding that.
        """

        if not search_string:
            search_string = self.state.get_flow_setting(self.flow,
                    "last_search_string")
            if not search_string:
                return

        if self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
            text = self.flow.request
            const = common.VIEW_FLOW_REQUEST
        else:
            text = self.flow.response
            const = common.VIEW_FLOW_RESPONSE
            if not self.flow.response:
                return "no response to search in"

        last_find_line = self.state.get_flow_setting(self.flow,
                "last_find_line")
        last_search_index = self.state.get_flow_setting(self.flow,
                "last_search_index")

        # generate the body, highlight the words and get focus
        headers, msg, body = self.conn_text_raw(text)
        try:
            body, focus_position = self.search_highlight_text(body, search_string, backwards=backwards)
        except SearchError:
            return "Search not supported in this view."

        if focus_position == None:
            # no results found.
            return "no matches for '%s'" % search_string

        # UI stuff.
        merged = self.conn_text_merge(headers, msg, body)
        list_box = urwid.ListBox(merged)
        list_box.set_focus(focus_position + 2)
        self.w = self.wrap_body(const, list_box)
        self.master.statusbar.redraw()

        self.last_displayed_body = list_box

        wrapped, wrapped_message = self.search_wrapped_around(last_find_line, last_search_index, backwards)

        if wrapped:
            return wrapped_message

    def search_get_start(self, search_string):
        start_line = 0
        start_index = 0
        last_search_string = self.state.get_flow_setting(self.flow, "last_search_string")
        if search_string == last_search_string:
            start_line = self.state.get_flow_setting(self.flow, "last_find_line")
            start_index = self.state.get_flow_setting(self.flow,
                    "last_search_index")

            if start_index == None:
                start_index = 0
            else:
                start_index += len(search_string)

            if start_line == None:
                start_line = 0

        else:
            self.state.add_flow_setting(self.flow, "last_search_string",
                    search_string)

        return (start_line, start_index)

    def search_get_range(self, len_text_objects, start_line, backwards):
        if not backwards:
            loop_range = xrange(start_line, len_text_objects)
        else:
            loop_range = xrange(start_line, -1, -1)

        return loop_range

    def search_find(self, text, search_string, start_index, backwards):
            if backwards == False:
                find_index = text.find(search_string, start_index)
            else:
                if start_index != 0:
                    start_index -= len(search_string)
                else:
                    start_index = None

                find_index = text.rfind(search_string, 0, start_index)

            return find_index

    def search_highlight_text(self, text_objects, search_string, looping = False, backwards = False):
        start_line, start_index = self.search_get_start(search_string)
        i = start_line

        found = False
        text_objects = copy.deepcopy(text_objects)
        loop_range = self.search_get_range(len(text_objects), start_line, backwards)
        for i in loop_range:
            text_object = text_objects[i]

            try:
                text, style = text_object.get_text()
            except AttributeError:
                raise SearchError()

            if i != start_line:
                start_index = 0

            find_index = self.search_find(text, search_string, start_index, backwards)

            if find_index != -1:
                new_text = self.search_highlight_object(text, find_index, search_string)
                text_objects[i] = new_text

                found = True
                self.state.add_flow_setting(self.flow, "last_search_index",
                        find_index)
                self.state.add_flow_setting(self.flow, "last_find_line", i)

                break

        # handle search WRAP
        if found:
            focus_pos = i
        else :
            if looping:
                focus_pos = None
            else:
                if not backwards:
                    self.state.add_flow_setting(self.flow, "last_search_index", 0)
                    self.state.add_flow_setting(self.flow, "last_find_line", 0)
                else:
                    self.state.add_flow_setting(self.flow, "last_search_index", None)
                    self.state.add_flow_setting(self.flow, "last_find_line", len(text_objects) - 1)

                text_objects, focus_pos = self.search_highlight_text(text_objects,
                        search_string, looping=True, backwards=backwards)

        return text_objects, focus_pos

    def search_highlight_object(self, text_object, find_index, search_string):
        """
            just a little abstraction
        """
        before = text_object[:find_index]
        after = text_object[find_index+len(search_string):]

        new_text = urwid.Text(
            [
                before,
                (self.highlight_color, search_string),
                after,
            ]
        )

        return new_text

    def view_request(self):
        self.state.view_flow_mode = common.VIEW_FLOW_REQUEST
        body = self.conn_text(self.flow.request)
        self.w = self.wrap_body(common.VIEW_FLOW_REQUEST, body)
        self.master.statusbar.redraw()

    def view_response(self):
        self.state.view_flow_mode = common.VIEW_FLOW_RESPONSE
        if self.flow.response:
            body = self.conn_text(self.flow.response)
        else:
            body = urwid.ListBox(
                        [
                            urwid.Text(""),
                            urwid.Text(
                                [
                                    ("highlight", "No response. Press "),
                                    ("key", "e"),
                                    ("highlight", " and edit any aspect to add one."),
                                ]
                            )
                        ]
                   )
        self.w = self.wrap_body(common.VIEW_FLOW_RESPONSE, body)
        self.master.statusbar.redraw()

    def refresh_flow(self, c=None):
        if c == self.flow:
            if self.state.view_flow_mode == common.VIEW_FLOW_RESPONSE and self.flow.response:
                self.view_response()
            else:
                self.view_request()

    def set_method_raw(self, m):
        if m:
            self.flow.request.method = m
            self.master.refresh_flow(self.flow)

    def edit_method(self, m):
        if m == "e":
            self.master.prompt_edit("Method", self.flow.request.method, self.set_method_raw)
        else:
            for i in self.method_options:
                if i[1] == m:
                    self.flow.request.method = i[0].upper()
            self.master.refresh_flow(self.flow)

    def save_body(self, path):
        if not path:
            return
        self.state.last_saveload = path
        if self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
            c = self.flow.request
        else:
            c = self.flow.response
        path = os.path.expanduser(path)
        try:
            f = file(path, "wb")
            f.write(str(c.content))
            f.close()
        except IOError, v:
            self.master.statusbar.message(v.strerror)

    def set_url(self, url):
        request = self.flow.request
        if not request.set_url(str(url)):
            return "Invalid URL."
        self.master.refresh_flow(self.flow)

    def set_resp_code(self, code):
        response = self.flow.response
        try:
            response.code = int(code)
        except ValueError:
            return None
        import BaseHTTPServer
        if BaseHTTPServer.BaseHTTPRequestHandler.responses.has_key(int(code)):
            response.msg = BaseHTTPServer.BaseHTTPRequestHandler.responses[int(code)][0]
        self.master.refresh_flow(self.flow)

    def set_resp_msg(self, msg):
        response = self.flow.response
        response.msg = msg
        self.master.refresh_flow(self.flow)

    def set_headers(self, lst, conn):
        conn.headers = flow.ODictCaseless(lst)

    def set_query(self, lst, conn):
        conn.set_query(flow.ODict(lst))

    def set_path_components(self, lst, conn):
        conn.set_path_components([i[0] for i in lst])

    def set_form(self, lst, conn):
        conn.set_form_urlencoded(flow.ODict(lst))

    def edit_form(self, conn):
        self.master.view_grideditor(
            grideditor.URLEncodedFormEditor(self.master, conn.get_form_urlencoded().lst, self.set_form, conn)
        )

    def edit_form_confirm(self, key, conn):
        if key == "y":
            self.edit_form(conn)

    def edit(self, part):
        if self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
            conn = self.flow.request
        else:
            if not self.flow.response:
                self.flow.response = HTTPResponse(
                    self.flow.request,
                    self.flow.request.httpversion,
                    200, "OK", flow.ODictCaseless(), "", None
                )
                self.flow.response.reply = controller.DummyReply()
            conn = self.flow.response

        self.flow.backup()
        if part == "r":
            c = self.master.spawn_editor(conn.content or "")
            conn.content = c.rstrip("\n") # what?
        elif part == "f":
            if not conn.get_form_urlencoded() and conn.content:
                self.master.prompt_onekey(
                    "Existing body is not a URL-encoded form. Clear and edit?",
                    [
                        ("yes", "y"),
                        ("no", "n"),
                    ],
                    self.edit_form_confirm,
                    conn
                )
            else:
                self.edit_form(conn)
        elif part == "h":
            self.master.view_grideditor(grideditor.HeaderEditor(self.master, conn.headers.lst, self.set_headers, conn))
        elif part == "p":
            p = conn.get_path_components()
            p = [[i] for i in p]
            self.master.view_grideditor(grideditor.PathEditor(self.master, p, self.set_path_components, conn))
        elif part == "q":
            self.master.view_grideditor(grideditor.QueryEditor(self.master, conn.get_query().lst, self.set_query, conn))
        elif part == "u" and self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
            self.master.prompt_edit("URL", conn.get_url(), self.set_url)
        elif part == "m" and self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
            self.master.prompt_onekey("Method", self.method_options, self.edit_method)
        elif part == "c" and self.state.view_flow_mode == common.VIEW_FLOW_RESPONSE:
            self.master.prompt_edit("Code", str(conn.code), self.set_resp_code)
        elif part == "m" and self.state.view_flow_mode == common.VIEW_FLOW_RESPONSE:
            self.master.prompt_edit("Message", conn.msg, self.set_resp_msg)
        self.master.refresh_flow(self.flow)

    def _view_nextprev_flow(self, np, flow):
        try:
            idx = self.state.view.index(flow)
        except IndexError:
            return
        if np == "next":
            new_flow, new_idx = self.state.get_next(idx)
        else:
            new_flow, new_idx = self.state.get_prev(idx)
        if new_flow is None:
            self.master.statusbar.message("No more flows!")
            return
        self.master.view_flow(new_flow)

    def view_next_flow(self, flow):
        return self._view_nextprev_flow("next", flow)

    def view_prev_flow(self, flow):
        return self._view_nextprev_flow("prev", flow)

    def change_this_display_mode(self, t):
        self.state.add_flow_setting(
            self.flow,
            (self.state.view_flow_mode, "prettyview"),
            contentview.get_by_shortcut(t)
        )
        self.master.refresh_flow(self.flow)

    def delete_body(self, t):
        if t == "m":
            val = CONTENT_MISSING
        else:
            val = None
        if self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
            self.flow.request.content = val
        else:
            self.flow.response.content = val
        self.master.refresh_flow(self.flow)

    def keypress(self, size, key):
        if key == " ":
            self.view_next_flow(self.flow)
            return

        key = common.shortcuts(key)
        if self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
            conn = self.flow.request
        else:
            conn = self.flow.response

        if key == "q":
            self.master.view_flowlist()
            key = None
        elif key == "tab":
            if self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
                self.view_response()
            else:
                self.view_request()
        elif key in ("up", "down", "page up", "page down"):
            # Why doesn't this just work??
            self.w.keypress(size, key)
        elif key == "a":
            self.flow.accept_intercept()
            self.master.view_flow(self.flow)
        elif key == "A":
            self.master.accept_all()
            self.master.view_flow(self.flow)
        elif key == "b":
            if conn:
                if self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
                    self.master.path_prompt(
                        "Save request body: ",
                        self.state.last_saveload,
                        self.save_body
                    )
                else:
                    self.master.path_prompt(
                        "Save response body: ",
                        self.state.last_saveload,
                        self.save_body
                    )
        elif key == "d":
            if self.state.flow_count() == 1:
                self.master.view_flowlist()
            elif self.state.view.index(self.flow) == len(self.state.view)-1:
                self.view_prev_flow(self.flow)
            else:
                self.view_next_flow(self.flow)
            f = self.flow
            f.kill(self.master)
            self.state.delete_flow(f)
        elif key == "D":
            f = self.master.duplicate_flow(self.flow)
            self.master.view_flow(f)
            self.master.statusbar.message("Duplicated.")
        elif key == "e":
            if self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
                self.master.prompt_onekey(
                    "Edit request",
                    (
                        ("query", "q"),
                        ("path", "p"),
                        ("url", "u"),
                        ("header", "h"),
                        ("form", "f"),
                        ("raw body", "r"),
                        ("method", "m"),
                    ),
                    self.edit
                )
            else:
                self.master.prompt_onekey(
                    "Edit response",
                    (
                        ("code", "c"),
                        ("message", "m"),
                        ("header", "h"),
                        ("raw body", "r"),
                    ),
                    self.edit
                )
            key = None
        elif key == "f":
            self.master.statusbar.message("Loading all body data...")
            self.state.add_flow_setting(
                self.flow,
                (self.state.view_flow_mode, "fullcontents"),
                True
            )
            self.master.refresh_flow(self.flow)
            self.master.statusbar.message("")
        elif key == "m":
            p = list(contentview.view_prompts)
            p.insert(0, ("clear", "c"))
            self.master.prompt_onekey(
                "Display mode",
                p,
                self.change_this_display_mode
            )
            key = None
        elif key == "p":
            self.view_prev_flow(self.flow)
        elif key == "r":
            self.flow.backup()
            r = self.master.replay_request(self.flow)
            if r:
                self.master.statusbar.message(r)
            self.master.refresh_flow(self.flow)
        elif key == "V":
            if not self.flow.modified():
                self.master.statusbar.message("Flow not modified.")
                return
            self.state.revert(self.flow)
            self.master.refresh_flow(self.flow)
            self.master.statusbar.message("Reverted.")
        elif key == "W":
            self.master.path_prompt(
                "Save this flow: ",
                self.state.last_saveload,
                self.master.save_one_flow,
                self.flow
            )
        elif key == "v":
            if conn and conn.content:
                t = conn.headers["content-type"] or [None]
                t = t[0]
                if os.environ.has_key("EDITOR") or os.environ.has_key("PAGER"):
                    self.master.spawn_external_viewer(conn.content, t)
                else:
                    self.master.statusbar.message("Error! Set $EDITOR or $PAGER.")
        elif key == "|":
            self.master.path_prompt(
                "Send flow to script: ", self.state.last_script,
                self.master.run_script_once, self.flow
            )
        elif key == "x":
            self.master.prompt_onekey(
                "Delete body",
                (
                    ("completely", "c"),
                    ("mark as missing", "m"),
                ),
                self.delete_body
            )
            key = None
        elif key == "X":
            self.master.view_flowdetails(self.flow)
        elif key == "z":
            if conn:
                self.flow.backup()
                e = conn.headers.get_first("content-encoding", "identity")
                if e != "identity":
                    if not conn.decode():
                        self.master.statusbar.message("Could not decode - invalid data?")
                else:
                    self.master.prompt_onekey(
                        "Select encoding: ",
                        (
                            ("gzip", "z"),
                            ("deflate", "d"),
                        ),
                        self.encode_callback,
                        conn
                    )
                self.master.refresh_flow(self.flow)
        elif key == "/":
            last_search_string = self.state.get_flow_setting(self.flow, "last_search_string")
            search_prompt = "Search body ["+last_search_string+"]: " if last_search_string else "Search body: "
            self.master.prompt(search_prompt,
                    None,
                    self.search)
        elif key == "n":
            self.search_again(backwards=False)
        elif key == "N":
            self.search_again(backwards=True)
        else:
            return key

    def encode_callback(self, key, conn):
        encoding_map = {
            "z": "gzip",
            "d": "deflate",
        }
        conn.encode(encoding_map[key])
        self.master.refresh_flow(self.flow)

########NEW FILE########
__FILENAME__ = grideditor
from __future__ import absolute_import
import copy, re, os
import urwid
from . import common
from .. import utils, filt, script
from netlib import http_uastrings


footer = [
    ('heading_key', "enter"), ":edit ",
    ('heading_key', "q"), ":back ",
]
footer_editing = [
    ('heading_key', "esc"), ":stop editing ",
]


class SText(common.WWrap):
    def __init__(self, txt, focused, error):
        txt = txt.encode("string-escape")
        w = urwid.Text(txt, wrap="any")
        if focused:
            if error:
                w = urwid.AttrWrap(w, "focusfield_error")
            else:
                w = urwid.AttrWrap(w, "focusfield")
        elif error:
            w = urwid.AttrWrap(w, "field_error")
        common.WWrap.__init__(self, w)

    def get_text(self):
        return self.w.get_text()[0]

    def keypress(self, size, key):
        return key

    def selectable(self):
        return True


class SEdit(common.WWrap):
    def __init__(self, txt):
        txt = txt.encode("string-escape")
        w = urwid.Edit(edit_text=txt, wrap="any", multiline=True)
        w = urwid.AttrWrap(w, "editfield")
        common.WWrap.__init__(self, w)

    def get_text(self):
        return self.w.get_text()[0]

    def selectable(self):
        return True


class GridRow(common.WWrap):
    def __init__(self, focused, editing, editor, values):
        self.focused, self.editing, self.editor = focused, editing, editor

        errors = values[1]
        self.fields = []
        for i, v in enumerate(values[0]):
            if focused == i and editing:
                self.editing = SEdit(v)
                self.fields.append(self.editing)
            else:
                self.fields.append(
                    SText(v, True if focused == i else False, i in errors)
                )

        fspecs = self.fields[:]
        if len(self.fields) > 1:
            fspecs[0] = ("fixed", self.editor.first_width + 2, fspecs[0])
        w = urwid.Columns(
            fspecs,
            dividechars = 2
        )
        if focused is not None:
            w.set_focus_column(focused)
        common.WWrap.__init__(self, w)

    def get_edit_value(self):
        return self.editing.get_text()

    def keypress(self, s, k):
        if self.editing:
            w = self.w.column_widths(s)[self.focused]
            k = self.editing.keypress((w,), k)
        return k

    def selectable(self):
        return True


class GridWalker(urwid.ListWalker):
    """
        Stores rows as a list of (rows, errors) tuples, where rows is a list
        and errors is a set with an entry of each offset in rows that is an
        error.
    """
    def __init__(self, lst, editor):
        self.lst = [(i, set([])) for i in lst]
        self.editor = editor
        self.focus = 0
        self.focus_col = 0
        self.editing = False

    def _modified(self):
        self.editor.show_empty_msg()
        return urwid.ListWalker._modified(self)

    def add_value(self, lst):
        self.lst.append((lst[:], set([])))
        self._modified()

    def get_current_value(self):
        if self.lst:
            return self.lst[self.focus][0][self.focus_col]

    def set_current_value(self, val, unescaped):
        if not unescaped:
            try:
                val = val.decode("string-escape")
            except ValueError:
                self.editor.master.statusbar.message("Invalid Python-style string encoding.", 1000)
                return

        errors = self.lst[self.focus][1]
        emsg = self.editor.is_error(self.focus_col, val)
        if emsg:
            self.editor.master.statusbar.message(emsg, 1000)
            errors.add(self.focus_col)

        row = list(self.lst[self.focus][0])
        row[self.focus_col] = val
        self.lst[self.focus] = [tuple(row), errors]

    def delete_focus(self):
        if self.lst:
            del self.lst[self.focus]
            self.focus = min(len(self.lst)-1, self.focus)
            self._modified()

    def _insert(self, pos):
        self.focus = pos
        self.lst.insert(self.focus, [[""]*self.editor.columns, set([])])
        self.focus_col = 0
        self.start_edit()

    def insert(self):
        return self._insert(self.focus)

    def add(self):
        return self._insert(min(self.focus + 1, len(self.lst)))

    def start_edit(self):
        if self.lst:
            self.editing = GridRow(self.focus_col, True, self.editor, self.lst[self.focus])
            self.editor.master.statusbar.update(footer_editing)
            self._modified()

    def stop_edit(self):
        if self.editing:
            self.editor.master.statusbar.update(footer)
            self.set_current_value(self.editing.get_edit_value(), False)
            self.editing = False
            self._modified()

    def left(self):
        self.focus_col = max(self.focus_col - 1, 0)
        self._modified()

    def right(self):
        self.focus_col = min(self.focus_col + 1, self.editor.columns-1)
        self._modified()

    def tab_next(self):
        self.stop_edit()
        if self.focus_col < self.editor.columns-1:
            self.focus_col += 1
        elif self.focus != len(self.lst)-1:
            self.focus_col = 0
            self.focus += 1
        self._modified()

    def get_focus(self):
        if self.editing:
            return self.editing, self.focus
        elif self.lst:
            return GridRow(self.focus_col, False, self.editor, self.lst[self.focus]), self.focus
        else:
            return None, None

    def set_focus(self, focus):
        self.stop_edit()
        self.focus = focus

    def get_next(self, pos):
        if pos+1 >= len(self.lst):
            return None, None
        return GridRow(None, False, self.editor, self.lst[pos+1]), pos+1

    def get_prev(self, pos):
        if pos-1 < 0:
            return None, None
        return GridRow(None, False, self.editor, self.lst[pos-1]), pos-1


class GridListBox(urwid.ListBox):
    def __init__(self, lw):
        urwid.ListBox.__init__(self, lw)


FIRST_WIDTH_MAX = 40
FIRST_WIDTH_MIN = 20
class GridEditor(common.WWrap):
    title = None
    columns = None
    headings = None
    def __init__(self, master, value, callback, *cb_args, **cb_kwargs):
        value = copy.deepcopy(value)
        self.master, self.value, self.callback = master, value, callback
        self.cb_args, self.cb_kwargs = cb_args, cb_kwargs

        first_width = 20
        if value:
            for r in value:
                assert len(r) == self.columns
                first_width = max(len(r), first_width)
        self.first_width = min(first_width, FIRST_WIDTH_MAX)

        title = urwid.Text(self.title)
        title = urwid.Padding(title, align="left", width=("relative", 100))
        title = urwid.AttrWrap(title, "heading")

        headings = []
        for i, h in enumerate(self.headings):
            c = urwid.Text(h)
            if i == 0 and len(self.headings) > 1:
                headings.append(("fixed", first_width + 2, c))
            else:
                headings.append(c)
        h = urwid.Columns(
            headings,
            dividechars = 2
        )
        h = urwid.AttrWrap(h, "heading")

        self.walker = GridWalker(self.value, self)
        self.lb = GridListBox(self.walker)
        self.w = urwid.Frame(
            self.lb,
            header = urwid.Pile([title, h])
        )
        self.master.statusbar.update("")
        self.show_empty_msg()

    def show_empty_msg(self):
        if self.walker.lst:
            self.w.set_footer(None)
        else:
            self.w.set_footer(
                urwid.Text(
                    [
                        ("highlight", "No values. Press "),
                        ("key", "a"),
                        ("highlight", " to add some."),
                    ]
                )
            )

    def encode(self, s):
        if not self.encoding:
            return s
        try:
            return s.encode(self.encoding)
        except ValueError:
            return None

    def read_file(self, p, unescaped=False):
        if p:
            try:
                p = os.path.expanduser(p)
                d = file(p, "rb").read()
                self.walker.set_current_value(d, unescaped)
                self.walker._modified()
            except IOError, v:
                return str(v)

    def keypress(self, size, key):
        if self.walker.editing:
            if key in ["esc"]:
                self.walker.stop_edit()
            elif key == "tab":
                pf, pfc = self.walker.focus, self.walker.focus_col
                self.walker.tab_next()
                if self.walker.focus == pf and self.walker.focus_col != pfc:
                    self.walker.start_edit()
            else:
                self.w.keypress(size, key)
            return None

        key = common.shortcuts(key)
        if key in ["q", "esc"]:
            res = []
            for i in self.walker.lst:
                if not i[1] and any([x.strip() for x in i[0]]):
                    res.append(i[0])
            self.callback(res, *self.cb_args, **self.cb_kwargs)
            self.master.pop_view()
        elif key in ["h", "left"]:
            self.walker.left()
        elif key in ["l", "right"]:
            self.walker.right()
        elif key == "tab":
            self.walker.tab_next()
        elif key == "a":
            self.walker.add()
        elif key == "A":
            self.walker.insert()
        elif key == "d":
            self.walker.delete_focus()
        elif key == "r":
            self.master.path_prompt("Read file: ", "", self.read_file)
        elif key == "R":
            self.master.path_prompt("Read unescaped file: ", "", self.read_file, True)
        elif key == "e":
            o = self.walker.get_current_value()
            if o is not None:
                n = self.master.spawn_editor(o.encode("string-escape"))
                n = utils.clean_hanging_newline(n)
                self.walker.set_current_value(n, False)
                self.walker._modified()
        elif key in ["enter"]:
            self.walker.start_edit()
        elif not self.handle_key(key):
            return self.w.keypress(size, key)

    def is_error(self, col, val):
        """
            Return False, or a string error message.
        """
        return False

    def handle_key(self, key):
        return False

    def make_help(self):
        text = []
        text.append(urwid.Text([("text", "Editor control:\n")]))
        keys = [
            ("A", "insert row before cursor"),
            ("a", "add row after cursor"),
            ("d", "delete row"),
            ("e", "spawn external editor on current field"),
            ("q", "return to flow view"),
            ("r", "read value from file"),
            ("R", "read unescaped value from file"),
            ("esc", "return to flow view/exit field edit mode"),
            ("tab", "next field"),
            ("enter", "edit field"),
        ]
        text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))
        text.append(
            urwid.Text(
                [
                    "\n",
                    ("text", "Values are escaped Python-style strings.\n"),
                ]
            )
        )
        return text


class QueryEditor(GridEditor):
    title = "Editing query"
    columns = 2
    headings = ("Key", "Value")


class HeaderEditor(GridEditor):
    title = "Editing headers"
    columns = 2
    headings = ("Key", "Value")
    def make_help(self):
        h = GridEditor.make_help(self)
        text = []
        text.append(urwid.Text([("text", "Special keys:\n")]))
        keys = [
            ("U", "add User-Agent header"),
        ]
        text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))
        text.append(urwid.Text([("text", "\n")]))
        text.extend(h)
        return text

    def set_user_agent(self, k):
        ua = http_uastrings.get_by_shortcut(k)
        if ua:
            self.walker.add_value(
                [
                    "User-Agent",
                    ua[2]
                ]
            )

    def handle_key(self, key):
        if key == "U":
            self.master.prompt_onekey(
                "Add User-Agent header:",
                [(i[0], i[1]) for i in http_uastrings.UASTRINGS],
                self.set_user_agent,
            )
            return True


class URLEncodedFormEditor(GridEditor):
    title = "Editing URL-encoded form"
    columns = 2
    headings = ("Key", "Value")


class ReplaceEditor(GridEditor):
    title = "Editing replacement patterns"
    columns = 3
    headings = ("Filter", "Regex", "Replacement")
    def is_error(self, col, val):
        if col == 0:
            if not filt.parse(val):
                return "Invalid filter specification."
        elif col == 1:
            try:
                re.compile(val)
            except re.error:
                return "Invalid regular expression."
        return False


class SetHeadersEditor(GridEditor):
    title = "Editing header set patterns"
    columns = 3
    headings = ("Filter", "Header", "Value")
    def is_error(self, col, val):
        if col == 0:
            if not filt.parse(val):
                return "Invalid filter specification"
        return False

    def make_help(self):
        h = GridEditor.make_help(self)
        text = []
        text.append(urwid.Text([("text", "Special keys:\n")]))
        keys = [
            ("U", "add User-Agent header"),
        ]
        text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))
        text.append(urwid.Text([("text", "\n")]))
        text.extend(h)
        return text

    def set_user_agent(self, k):
        ua = http_uastrings.get_by_shortcut(k)
        if ua:
            self.walker.add_value(
                [
                    ".*",
                    "User-Agent",
                    ua[2]
                ]
            )

    def handle_key(self, key):
        if key == "U":
            self.master.prompt_onekey(
                "Add User-Agent header:",
                [(i[0], i[1]) for i in http_uastrings.UASTRINGS],
                self.set_user_agent,
            )
            return True


class PathEditor(GridEditor):
    title = "Editing URL path components"
    columns = 1
    headings = ("Component",)


class ScriptEditor(GridEditor):
    title = "Editing scripts"
    columns = 1
    headings = ("Command",)
    def is_error(self, col, val):
        try:
            script.Script.parse_command(val)
        except script.ScriptError, v:
            return str(v)

########NEW FILE########
__FILENAME__ = help
from __future__ import absolute_import
import urwid
from . import common
from .. import filt, version

footer = [
    ("heading", 'mitmproxy v%s '%version.VERSION),
    ('heading_key', "q"), ":back ",
]

class HelpView(urwid.ListBox):
    def __init__(self, master, help_context, state):
        self.master, self.state = master, state
        self.help_context = help_context or []
        urwid.ListBox.__init__(
            self,
            self.helptext()
        )

    def helptext(self):
        text = []
        text.append(urwid.Text([("head", "This view:\n")]))
        text.extend(self.help_context)

        text.append(urwid.Text([("head", "\n\nMovement:\n")]))
        keys = [
            ("j, k", "up, down"),
            ("h, l", "left, right (in some contexts)"),
            ("space", "page down"),
            ("pg up/down", "page up/down"),
            ("arrows", "up, down, left, right"),
        ]
        text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))

        text.append(urwid.Text([("head", "\n\nGlobal keys:\n")]))
        keys = [
            ("c", "client replay"),
            ("H", "edit global header set patterns"),
            ("i", "set interception pattern"),
            ("M", "change global default display mode"),
                (None,
                    common.highlight_key("automatic", "a") +
                    [("text", ": automatic detection")]
                ),
                (None,
                    common.highlight_key("hex", "e") +
                    [("text", ": Hex")]
                ),
                (None,
                    common.highlight_key("html", "h") +
                    [("text", ": HTML")]
                ),
                (None,
                    common.highlight_key("image", "i") +
                    [("text", ": Image")]
                ),
                (None,
                    common.highlight_key("javascript", "j") +
                    [("text", ": JavaScript")]
                ),
                (None,
                    common.highlight_key("json", "s") +
                    [("text", ": JSON")]
                ),
                (None,
                    common.highlight_key("css", "c") +
                    [("text", ": CSS")]
                ),
                (None,
                    common.highlight_key("urlencoded", "u") +
                    [("text", ": URL-encoded data")]
                ),
                (None,
                    common.highlight_key("raw", "r") +
                    [("text", ": raw data")]
                ),
                (None,
                    common.highlight_key("xml", "x") +
                    [("text", ": XML")]
                ),
                (None,
                    common.highlight_key("wbxml", "w") +
                    [("text", ": WBXML")]
                ),
                (None,
                    common.highlight_key("amf", "f") +
                    [("text", ": AMF (requires PyAMF)")]
                ),
            ("o", "toggle options:"),
                (None,
                    common.highlight_key("anticache", "a") +
                    [("text", ": prevent cached responses")]
                ),
                (None,
                    common.highlight_key("anticomp", "c") +
                    [("text", ": prevent compressed responses")]
                ),
                (None,
                    common.highlight_key("showhost", "h") +
                    [("text", ": use Host header for URL display")]
                ),
                (None,
                    common.highlight_key("killextra", "k") +
                    [("text", ": kill requests not part of server replay")]
                ),
                (None,
                    common.highlight_key("norefresh", "n") +
                    [("text", ": disable server replay response refresh")]
                ),
                (None,
                    common.highlight_key("upstream certs", "u") +
                    [("text", ": sniff cert info from upstream server")]
                ),

            ("q", "quit / return to flow list"),
            ("Q", "quit without confirm prompt"),
            ("R", "edit replacement patterns"),
            ("s", "set/unset script"),
            ("S", "server replay"),
            ("t", "set sticky cookie expression"),
            ("u", "set sticky auth expression"),
        ]
        text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))

        text.append(urwid.Text([("head", "\n\nFilter expressions:\n")]))
        f = []
        for i in filt.filt_unary:
            f.append(
                ("~%s"%i.code, i.help)
            )
        for i in filt.filt_rex:
            f.append(
                ("~%s regex"%i.code, i.help)
            )
        for i in filt.filt_int:
            f.append(
                ("~%s int"%i.code, i.help)
            )
        f.sort()
        f.extend(
            [
                ("!", "unary not"),
                ("&", "and"),
                ("|", "or"),
                ("(...)", "grouping"),
            ]
        )
        text.extend(common.format_keyvals(f, key="key", val="text", indent=4))

        text.append(
            urwid.Text(
               [
                    "\n",
                    ("text", "    Regexes are Python-style.\n"),
                    ("text", "    Regexes can be specified as quoted strings.\n"),
                    ("text", "    Header matching (~h, ~hq, ~hs) is against a string of the form \"name: value\".\n"),
                    ("text", "    Expressions with no operators are regex matches against URL.\n"),
                    ("text", "    Default binary operator is &.\n"),
                    ("head", "\n    Examples:\n"),
               ]
            )
        )
        examples = [
                ("google\.com", "Url containing \"google.com"),
                ("~q ~b test", "Requests where body contains \"test\""),
                ("!(~q & ~t \"text/html\")", "Anything but requests with a text/html content type."),
        ]
        text.extend(common.format_keyvals(examples, key="key", val="text", indent=4))
        return text

    def keypress(self, size, key):
        key = common.shortcuts(key)
        if key == "q":
            self.master.statusbar = self.state[0]
            self.master.body = self.state[1]
            self.master.header = self.state[2]
            self.master.make_view()
            return None
        elif key == "?":
            key = None
        return urwid.ListBox.keypress(self, size, key)

########NEW FILE########
__FILENAME__ = palettes
palettes = {

# Default palette for dark background
  'dark': [
    # name, foreground, background, mono, foreground_high, background_high
    # For details on the meaning of the elements refer to
    # http://excess.org/urwid/reference.html#Screen-register_palette

    ('body', 'black', 'dark cyan'),
    ('foot', 'light gray', 'default'),
    ('title', 'white,bold', 'default',),
    ('editline', 'white', 'default',),

    # Status bar & heading
    ('heading', 'light gray', 'dark blue', None, 'g85', 'dark blue'),
    ('heading_key', 'light cyan', 'dark blue', None, 'light cyan', 'dark blue'),
    ('heading_inactive', 'white', 'dark gray', None, 'g58', 'g11'),

    # Help
    ('key', 'light cyan', 'default'),
    ('head', 'white,bold', 'default'),
    ('text', 'light gray', 'default'),

    # List and Connections
    ('method', 'dark cyan', 'default'),
    ('focus', 'yellow', 'default'),

    ('code_200', 'light green', 'default'),
    ('code_300', 'light blue', 'default'),
    ('code_400', 'light red', 'default', None, '#f60', 'default'),
    ('code_500', 'light red', 'default'),
    ('code_other', 'dark red', 'default'),

    ('error', 'light red', 'default'),

    ('header', 'dark cyan', 'default'),
    ('highlight', 'white,bold', 'default'),
    ('intercept', 'brown', 'default', None, '#f60', 'default'),
    ('replay', 'light green', 'default', None, '#0f0', 'default'),
    ('ack', 'light red', 'default'),

    # Hex view
    ('offset', 'dark cyan', 'default'),

    # Grid Editor
    ('focusfield', 'black', 'light gray'),
    ('focusfield_error', 'dark red', 'light gray'),
    ('field_error', 'dark red', 'black'),
    ('editfield', 'black', 'light cyan'),
  ],

# Palette for light background
  'light': [
    ('body', 'black', 'dark cyan'),
    ('foot', 'dark gray', 'default'),
    ('title', 'white,bold', 'light blue',),
    ('editline', 'white', 'default',),

    # Status bar & heading
    ('heading', 'white', 'light gray', None, 'g85', 'dark blue'),
    ('heading_key', 'dark blue', 'light gray', None, 'light cyan', 'dark blue'),
    ('heading_inactive', 'light gray', 'dark gray', None, 'dark gray', 'dark blue'),

    # Help
    ('key', 'dark blue,bold', 'default'),
    ('head', 'black,bold', 'default'),
    ('text', 'dark gray', 'default'),

    # List and Connections
    ('method', 'dark cyan', 'default'),
    ('focus', 'black', 'default'),

    ('code_200', 'dark green', 'default'),
    ('code_300', 'light blue', 'default'),
    ('code_400', 'dark red', 'default', None, '#f60', 'default'),
    ('code_500', 'dark red', 'default'),
    ('code_other', 'light red', 'default'),

    ('error', 'light red', 'default'),

    ('header', 'dark blue', 'default'),
    ('highlight', 'black,bold', 'default'),
    ('intercept', 'brown', 'default', None, '#f60', 'default'),
    ('replay', 'dark green', 'default', None, '#0f0', 'default'),
    ('ack', 'dark red', 'default'),

    # Hex view
    ('offset', 'dark blue', 'default'),

    # Grid Editor
    ('focusfield', 'black', 'light gray'),
    ('focusfield_error', 'dark red', 'light gray'),
    ('field_error', 'dark red', 'black'),
    ('editfield', 'black', 'light cyan'),
  ],

# Palettes for terminals that use the Solarized precision colors
# (http://ethanschoonover.com/solarized#the-values)

# For dark backgrounds
  'solarized_dark': [
    ('body', 'dark cyan', 'default'),
    ('foot', 'dark gray', 'default'),
    ('title', 'white,bold', 'default',),
    ('editline', 'white', 'default',),

    # Status bar & heading
    ('heading', 'light gray', 'light cyan',),
    ('heading_key', 'dark blue', 'white',),
    ('heading_inactive', 'light cyan', 'light gray',),

    # Help
    ('key', 'dark blue', 'default',),
    ('head', 'white,underline', 'default'),
    ('text', 'light cyan', 'default'),

    # List and Connections
    ('method', 'dark cyan', 'default'),
    ('focus', 'white', 'default'),

    ('code_200', 'dark green', 'default'),
    ('code_300', 'light blue', 'default'),
    ('code_400', 'dark red', 'default',),
    ('code_500', 'dark red', 'default'),
    ('code_other', 'light red', 'default'),

    ('error', 'light red', 'default'),

    ('header', 'yellow', 'default'),
    ('highlight', 'white', 'default'),
    ('intercept', 'brown', 'default',),
    ('replay', 'dark green', 'default',),
    ('ack', 'dark red', 'default'),

    # Hex view
    ('offset', 'yellow', 'default'),
    ('text', 'light cyan', 'default'),

    # Grid Editor
    ('focusfield', 'white', 'light cyan'),
    ('focusfield_error', 'dark red', 'light gray'),
    ('field_error', 'dark red', 'black'),
    ('editfield', 'black', 'light gray'),
  ],

# For light backgrounds
  'solarized_light': [
    ('body', 'dark cyan', 'default'),
    ('foot', 'dark gray', 'default'),
    ('title', 'white,bold', 'light cyan',),
    ('editline', 'white', 'default',),

    # Status bar & heading
    ('heading', 'light cyan', 'light gray',),
    ('heading_key', 'dark blue', 'white',),
    ('heading_inactive', 'white', 'light gray',),

    # Help
    ('key', 'dark blue', 'default',),
    ('head', 'black,underline', 'default'),
    ('text', 'light cyan', 'default'),

    # List and Connections
    ('method', 'dark cyan', 'default'),
    ('focus', 'black', 'default'),

    ('code_200', 'dark green', 'default'),
    ('code_300', 'light blue', 'default'),
    ('code_400', 'dark red', 'default',),
    ('code_500', 'dark red', 'default'),
    ('code_other', 'light red', 'default'),

    ('error', 'light red', 'default'),

    ('header', 'light cyan', 'default'),
    ('highlight', 'black,bold', 'default'),
    ('intercept', 'brown', 'default',),
    ('replay', 'dark green', 'default',),
    ('ack', 'dark red', 'default'),

    # Hex view
    ('offset', 'light cyan', 'default'),
    ('text', 'yellow', 'default'),

    # Grid Editor
    ('focusfield', 'black', 'light gray'),
    ('focusfield_error', 'dark red', 'light gray'),
    ('field_error', 'dark red', 'black'),
    ('editfield', 'white', 'light cyan'),
  ],

}

########NEW FILE########
__FILENAME__ = html2text
#!/usr/bin/env python
"""html2text: Turn HTML into equivalent Markdown-structured text."""
__version__ = "3.200.3"
__author__ = "Aaron Swartz (me@aaronsw.com)"
__copyright__ = "(C) 2004-2008 Aaron Swartz. GNU GPL 3."
__contributors__ = ["Martin 'Joey' Schulze", "Ricardo Reyes", "Kevin Jay North"]

# TODO:
#   Support decoded entities with unifiable.

try:
    True
except NameError:
    setattr(__builtins__, 'True', 1)
    setattr(__builtins__, 'False', 0)

def has_key(x, y):
    if hasattr(x, 'has_key'): return x.has_key(y)
    else: return y in x

try:
    import htmlentitydefs
    import urlparse
    import HTMLParser
except ImportError: #Python3
    import html.entities as htmlentitydefs
    import urllib.parse as urlparse
    import html.parser as HTMLParser
try: #Python3
    import urllib.request as urllib
except:
    import urllib
import optparse, re, sys, codecs, types

try: from textwrap import wrap
except: pass

# Use Unicode characters instead of their ascii psuedo-replacements
UNICODE_SNOB = 0

# Put the links after each paragraph instead of at the end.
LINKS_EACH_PARAGRAPH = 0

# Wrap long lines at position. 0 for no wrapping. (Requires Python 2.3.)
BODY_WIDTH = 78

# Don't show internal links (href="#local-anchor") -- corresponding link targets
# won't be visible in the plain text file anyway.
SKIP_INTERNAL_LINKS = True

# Use inline, rather than reference, formatting for images and links
INLINE_LINKS = True

# Number of pixels Google indents nested lists
GOOGLE_LIST_INDENT = 36

IGNORE_ANCHORS = False
IGNORE_IMAGES = False
IGNORE_EMPHASIS = False

### Entity Nonsense ###

def name2cp(k):
    if k == 'apos': return ord("'")
    if hasattr(htmlentitydefs, "name2codepoint"): # requires Python 2.3
        return htmlentitydefs.name2codepoint[k]
    else:
        k = htmlentitydefs.entitydefs[k]
        if k.startswith("&#") and k.endswith(";"): return int(k[2:-1]) # not in latin-1
        return ord(codecs.latin_1_decode(k)[0])

unifiable = {'rsquo':"'", 'lsquo':"'", 'rdquo':'"', 'ldquo':'"',
'copy':'(C)', 'mdash':'--', 'nbsp':' ', 'rarr':'->', 'larr':'<-', 'middot':'*',
'ndash':'-', 'oelig':'oe', 'aelig':'ae',
'agrave':'a', 'aacute':'a', 'acirc':'a', 'atilde':'a', 'auml':'a', 'aring':'a',
'egrave':'e', 'eacute':'e', 'ecirc':'e', 'euml':'e',
'igrave':'i', 'iacute':'i', 'icirc':'i', 'iuml':'i',
'ograve':'o', 'oacute':'o', 'ocirc':'o', 'otilde':'o', 'ouml':'o',
'ugrave':'u', 'uacute':'u', 'ucirc':'u', 'uuml':'u',
'lrm':'', 'rlm':''}

unifiable_n = {}

for k in unifiable.keys():
    unifiable_n[name2cp(k)] = unifiable[k]

### End Entity Nonsense ###

def onlywhite(line):
    """Return true if the line does only consist of whitespace characters."""
    for c in line:
        if c is not ' ' and c is not '  ':
            return c is ' '
    return line

def hn(tag):
    if tag[0] == 'h' and len(tag) == 2:
        try:
            n = int(tag[1])
            if n in range(1, 10): return n
        except ValueError: return 0

def dumb_property_dict(style):
    """returns a hash of css attributes"""
    return dict([(x.strip(), y.strip()) for x, y in [z.split(':', 1) for z in style.split(';') if ':' in z]]);

def dumb_css_parser(data):
    """returns a hash of css selectors, each of which contains a hash of css attributes"""
    # remove @import sentences
    importIndex = data.find('@import')
    while importIndex != -1:
        data = data[0:importIndex] + data[data.find(';', importIndex) + 1:]
        importIndex = data.find('@import')

    # parse the css. reverted from dictionary compehension in order to support older pythons
    elements =  [x.split('{') for x in data.split('}') if '{' in x.strip()]
    try:
        elements = dict([(a.strip(), dumb_property_dict(b)) for a, b in elements])
    except ValueError:
        elements = {} # not that important

    return elements

def element_style(attrs, style_def, parent_style):
    """returns a hash of the 'final' style attributes of the element"""
    style = parent_style.copy()
    if 'class' in attrs:
        for css_class in attrs['class'].split():
            css_style = style_def['.' + css_class]
            style.update(css_style)
    if 'style' in attrs:
        immediate_style = dumb_property_dict(attrs['style'])
        style.update(immediate_style)
    return style

def google_list_style(style):
    """finds out whether this is an ordered or unordered list"""
    if 'list-style-type' in style:
        list_style = style['list-style-type']
        if list_style in ['disc', 'circle', 'square', 'none']:
            return 'ul'
    return 'ol'

def google_has_height(style):
    """check if the style of the element has the 'height' attribute explicitly defined"""
    if 'height' in style:
        return True
    return False

def google_text_emphasis(style):
    """return a list of all emphasis modifiers of the element"""
    emphasis = []
    if 'text-decoration' in style:
        emphasis.append(style['text-decoration'])
    if 'font-style' in style:
        emphasis.append(style['font-style'])
    if 'font-weight' in style:
        emphasis.append(style['font-weight'])
    return emphasis

def google_fixed_width_font(style):
    """check if the css of the current element defines a fixed width font"""
    font_family = ''
    if 'font-family' in style:
        font_family = style['font-family']
    if 'Courier New' == font_family or 'Consolas' == font_family:
        return True
    return False

def list_numbering_start(attrs):
    """extract numbering from list element attributes"""
    if 'start' in attrs:
        return int(attrs['start']) - 1
    else:
        return 0

class HTML2Text(HTMLParser.HTMLParser):
    def __init__(self, out=None, baseurl=''):
        HTMLParser.HTMLParser.__init__(self)

        # Config options
        self.unicode_snob = UNICODE_SNOB
        self.links_each_paragraph = LINKS_EACH_PARAGRAPH
        self.body_width = BODY_WIDTH
        self.skip_internal_links = SKIP_INTERNAL_LINKS
        self.inline_links = INLINE_LINKS
        self.google_list_indent = GOOGLE_LIST_INDENT
        self.ignore_links = IGNORE_ANCHORS
        self.ignore_images = IGNORE_IMAGES
        self.ignore_emphasis = IGNORE_EMPHASIS
        self.google_doc = False
        self.ul_item_mark = '*'

        if out is None:
            self.out = self.outtextf
        else:
            self.out = out

        self.outtextlist = []  # empty list to store output characters before they are "joined"

        try:
            self.outtext = unicode()
        except NameError:  # Python3
            self.outtext = str()

        self.quiet = 0
        self.p_p = 0  # number of newline character to print before next output
        self.outcount = 0
        self.start = 1
        self.space = 0
        self.a = []
        self.astack = []
        self.acount = 0
        self.list = []
        self.blockquote = 0
        self.pre = 0
        self.startpre = 0
        self.code = False
        self.br_toggle = ''
        self.lastWasNL = 0
        self.lastWasList = False
        self.style = 0
        self.style_def = {}
        self.tag_stack = []
        self.emphasis = 0
        self.drop_white_space = 0
        self.inheader = False
        self.abbr_title = None  # current abbreviation definition
        self.abbr_data = None  # last inner HTML (for abbr being defined)
        self.abbr_list = {}  # stack of abbreviations to write later
        self.baseurl = baseurl

        try: del unifiable_n[name2cp('nbsp')]
        except KeyError: pass
        unifiable['nbsp'] = '&nbsp_place_holder;'


    def feed(self, data):
        data = data.replace("</' + 'script>", "</ignore>")
        HTMLParser.HTMLParser.feed(self, data)

    def handle(self, data):
        self.feed(data)
        self.feed("")
        return self.optwrap(self.close())

    def outtextf(self, s):
        self.outtextlist.append(s)
        if s: self.lastWasNL = s[-1] == '\n'

    def close(self):
        HTMLParser.HTMLParser.close(self)

        self.pbr()
        self.o('', 0, 'end')

        self.outtext = self.outtext.join(self.outtextlist)
        if self.unicode_snob:
            nbsp = unichr(name2cp('nbsp'))
        else:
            nbsp = u' '
        self.outtext = self.outtext.replace(u'&nbsp_place_holder;', nbsp)

        return self.outtext

    def handle_charref(self, c):
        self.o(self.charref(c), 1)

    def handle_entityref(self, c):
        self.o(self.entityref(c), 1)

    def handle_starttag(self, tag, attrs):
        self.handle_tag(tag, attrs, 1)

    def handle_endtag(self, tag):
        self.handle_tag(tag, None, 0)

    def previousIndex(self, attrs):
        """ returns the index of certain set of attributes (of a link) in the
            self.a list

            If the set of attributes is not found, returns None
        """
        if not has_key(attrs, 'href'): return None

        i = -1
        for a in self.a:
            i += 1
            match = 0

            if has_key(a, 'href') and a['href'] == attrs['href']:
                if has_key(a, 'title') or has_key(attrs, 'title'):
                        if (has_key(a, 'title') and has_key(attrs, 'title') and
                            a['title'] == attrs['title']):
                            match = True
                else:
                    match = True

            if match: return i

    def drop_last(self, nLetters):
        if not self.quiet:
            self.outtext = self.outtext[:-nLetters]

    def handle_emphasis(self, start, tag_style, parent_style):
        """handles various text emphases"""
        tag_emphasis = google_text_emphasis(tag_style)
        parent_emphasis = google_text_emphasis(parent_style)

        # handle Google's text emphasis
        strikethrough =  'line-through' in tag_emphasis and self.hide_strikethrough
        bold = 'bold' in tag_emphasis and not 'bold' in parent_emphasis
        italic = 'italic' in tag_emphasis and not 'italic' in parent_emphasis
        fixed = google_fixed_width_font(tag_style) and not \
                google_fixed_width_font(parent_style) and not self.pre

        if start:
            # crossed-out text must be handled before other attributes
            # in order not to output qualifiers unnecessarily
            if bold or italic or fixed:
                self.emphasis += 1
            if strikethrough:
                self.quiet += 1
            if italic:
                self.o("_")
                self.drop_white_space += 1
            if bold:
                self.o("**")
                self.drop_white_space += 1
            if fixed:
                self.o('`')
                self.drop_white_space += 1
                self.code = True
        else:
            if bold or italic or fixed:
                # there must not be whitespace before closing emphasis mark
                self.emphasis -= 1
                self.space = 0
                self.outtext = self.outtext.rstrip()
            if fixed:
                if self.drop_white_space:
                    # empty emphasis, drop it
                    self.drop_last(1)
                    self.drop_white_space -= 1
                else:
                    self.o('`')
                self.code = False
            if bold:
                if self.drop_white_space:
                    # empty emphasis, drop it
                    self.drop_last(2)
                    self.drop_white_space -= 1
                else:
                    self.o("**")
            if italic:
                if self.drop_white_space:
                    # empty emphasis, drop it
                    self.drop_last(1)
                    self.drop_white_space -= 1
                else:
                    self.o("_")
            # space is only allowed after *all* emphasis marks
            if (bold or italic) and not self.emphasis:
                    self.o(" ")
            if strikethrough:
                self.quiet -= 1

    def handle_tag(self, tag, attrs, start):
        #attrs = fixattrs(attrs)
        if attrs is None:
            attrs = {}
        else:
            attrs = dict(attrs)

        if self.google_doc:
            # the attrs parameter is empty for a closing tag. in addition, we
            # need the attributes of the parent nodes in order to get a
            # complete style description for the current element. we assume
            # that google docs export well formed html.
            parent_style = {}
            if start:
                if self.tag_stack:
                  parent_style = self.tag_stack[-1][2]
                tag_style = element_style(attrs, self.style_def, parent_style)
                self.tag_stack.append((tag, attrs, tag_style))
            else:
                dummy, attrs, tag_style = self.tag_stack.pop()
                if self.tag_stack:
                    parent_style = self.tag_stack[-1][2]

        if hn(tag):
            self.p()
            if start:
                self.inheader = True
                self.o(hn(tag)*"#" + ' ')
            else:
                self.inheader = False
                return # prevent redundant emphasis marks on headers

        if tag in ['p', 'div']:
            if self.google_doc:
                if start and google_has_height(tag_style):
                    self.p()
                else:
                    self.soft_br()
            else:
                self.p()

        if tag == "br" and start: self.o("  \n")

        if tag == "hr" and start:
            self.p()
            self.o("* * *")
            self.p()

        if tag in ["head", "style", 'script']:
            if start: self.quiet += 1
            else: self.quiet -= 1

        if tag == "style":
            if start: self.style += 1
            else: self.style -= 1

        if tag in ["body"]:
            self.quiet = 0 # sites like 9rules.com never close <head>

        if tag == "blockquote":
            if start:
                self.p(); self.o('> ', 0, 1); self.start = 1
                self.blockquote += 1
            else:
                self.blockquote -= 1
                self.p()

        if tag in ['em', 'i', 'u'] and not self.ignore_emphasis: self.o("_")
        if tag in ['strong', 'b'] and not self.ignore_emphasis: self.o("**")
        if tag in ['del', 'strike', 's']:
            if start:
                self.o("<"+tag+">")
            else:
                self.o("</"+tag+">")

        if self.google_doc:
            if not self.inheader:
                # handle some font attributes, but leave headers clean
                self.handle_emphasis(start, tag_style, parent_style)

        if tag in ["code", "tt"] and not self.pre: self.o('`') #TODO: `` `this` ``
        if tag == "abbr":
            if start:
                self.abbr_title = None
                self.abbr_data = ''
                if has_key(attrs, 'title'):
                    self.abbr_title = attrs['title']
            else:
                if self.abbr_title != None:
                    self.abbr_list[self.abbr_data] = self.abbr_title
                    self.abbr_title = None
                self.abbr_data = ''

        if tag == "a" and not self.ignore_links:
            if start:
                if has_key(attrs, 'href') and not (self.skip_internal_links and attrs['href'].startswith('#')):
                    self.astack.append(attrs)
                    self.o("[")
                else:
                    self.astack.append(None)
            else:
                if self.astack:
                    a = self.astack.pop()
                    if a:
                        if self.inline_links:
                            self.o("](" + escape_md(a['href']) + ")")
                        else:
                            i = self.previousIndex(a)
                            if i is not None:
                                a = self.a[i]
                            else:
                                self.acount += 1
                                a['count'] = self.acount
                                a['outcount'] = self.outcount
                                self.a.append(a)
                            self.o("][" + str(a['count']) + "]")

        if tag == "img" and start and not self.ignore_images:
            if has_key(attrs, 'src'):
                attrs['href'] = attrs['src']
                alt = attrs.get('alt', '')
                self.o("![" + escape_md(alt) + "]")

                if self.inline_links:
                    self.o("(" + escape_md(attrs['href']) + ")")
                else:
                    i = self.previousIndex(attrs)
                    if i is not None:
                        attrs = self.a[i]
                    else:
                        self.acount += 1
                        attrs['count'] = self.acount
                        attrs['outcount'] = self.outcount
                        self.a.append(attrs)
                    self.o("[" + str(attrs['count']) + "]")

        if tag == 'dl' and start: self.p()
        if tag == 'dt' and not start: self.pbr()
        if tag == 'dd' and start: self.o('    ')
        if tag == 'dd' and not start: self.pbr()

        if tag in ["ol", "ul"]:
            # Google Docs create sub lists as top level lists
            if (not self.list) and (not self.lastWasList):
                self.p()
            if start:
                if self.google_doc:
                    list_style = google_list_style(tag_style)
                else:
                    list_style = tag
                numbering_start = list_numbering_start(attrs)
                self.list.append({'name':list_style, 'num':numbering_start})
            else:
                if self.list: self.list.pop()
            self.lastWasList = True
        else:
            self.lastWasList = False

        if tag == 'li':
            self.pbr()
            if start:
                if self.list: li = self.list[-1]
                else: li = {'name':'ul', 'num':0}
                if self.google_doc:
                    nest_count = self.google_nest_count(tag_style)
                else:
                    nest_count = len(self.list)
                self.o("  " * nest_count) #TODO: line up <ol><li>s > 9 correctly.
                if li['name'] == "ul": self.o(self.ul_item_mark + " ")
                elif li['name'] == "ol":
                    li['num'] += 1
                    self.o(str(li['num'])+". ")
                self.start = 1

        if tag in ["table", "tr"] and start: self.p()
        if tag == 'td': self.pbr()

        if tag == "pre":
            if start:
                self.startpre = 1
                self.pre = 1
            else:
                self.pre = 0
            self.p()

    def pbr(self):
        if self.p_p == 0:
            self.p_p = 1

    def p(self):
        self.p_p = 2

    def soft_br(self):
        self.pbr()
        self.br_toggle = '  '

    def o(self, data, puredata=0, force=0):
        if self.abbr_data is not None:
            self.abbr_data += data

        if not self.quiet:
            if self.google_doc:
                # prevent white space immediately after 'begin emphasis' marks ('**' and '_')
                lstripped_data = data.lstrip()
                if self.drop_white_space and not (self.pre or self.code):
                    data = lstripped_data
                if lstripped_data != '':
                    self.drop_white_space = 0

            if puredata and not self.pre:
                data = re.sub('\s+', ' ', data)
                if data and data[0] == ' ':
                    self.space = 1
                    data = data[1:]
            if not data and not force: return

            if self.startpre:
                #self.out(" :") #TODO: not output when already one there
                self.startpre = 0

            bq = (">" * self.blockquote)
            if not (force and data and data[0] == ">") and self.blockquote: bq += " "

            if self.pre:
                bq += "    "
                data = data.replace("\n", "\n"+bq)

            if self.start:
                self.space = 0
                self.p_p = 0
                self.start = 0

            if force == 'end':
                # It's the end.
                self.p_p = 0
                self.out("\n")
                self.space = 0

            if self.p_p:
                self.out((self.br_toggle+'\n'+bq)*self.p_p)
                self.space = 0
                self.br_toggle = ''

            if self.space:
                if not self.lastWasNL: self.out(' ')
                self.space = 0

            if self.a and ((self.p_p == 2 and self.links_each_paragraph) or force == "end"):
                if force == "end": self.out("\n")

                newa = []
                for link in self.a:
                    if self.outcount > link['outcount']:
                        self.out("   ["+ str(link['count']) +"]: " + urlparse.urljoin(self.baseurl, link['href']))
                        if has_key(link, 'title'): self.out(" ("+link['title']+")")
                        self.out("\n")
                    else:
                        newa.append(link)

                if self.a != newa: self.out("\n") # Don't need an extra line when nothing was done.

                self.a = newa

            if self.abbr_list and force == "end":
                for abbr, definition in self.abbr_list.items():
                    self.out("  *[" + abbr + "]: " + definition + "\n")

            self.p_p = 0
            self.out(data)
            self.outcount += 1

    def handle_data(self, data):
        if r'\/script>' in data: self.quiet -= 1

        if self.style:
            self.style_def.update(dumb_css_parser(data))

        self.o(data, 1)

    def unknown_decl(self, data): pass

    def charref(self, name):
        if name[0] in ['x','X']:
            c = int(name[1:], 16)
        else:
            c = int(name)

        if not self.unicode_snob and c in unifiable_n.keys():
            return unifiable_n[c]
        else:
            try:
                return unichr(c)
            except NameError: #Python3
                return chr(c)

    def entityref(self, c):
        if not self.unicode_snob and c in unifiable.keys():
            return unifiable[c]
        else:
            try: name2cp(c)
            except KeyError: return "&" + c + ';'
            else:
                try:
                    return unichr(name2cp(c))
                except NameError: #Python3
                    return chr(name2cp(c))

    def replaceEntities(self, s):
        s = s.group(1)
        if s[0] == "#":
            return self.charref(s[1:])
        else: return self.entityref(s)

    r_unescape = re.compile(r"&(#?[xX]?(?:[0-9a-fA-F]+|\w{1,8}));")
    def unescape(self, s):
        return self.r_unescape.sub(self.replaceEntities, s)

    def google_nest_count(self, style):
        """calculate the nesting count of google doc lists"""
        nest_count = 0
        if 'margin-left' in style:
            nest_count = int(style['margin-left'][:-2]) / self.google_list_indent
        return nest_count


    def optwrap(self, text):
        """Wrap all paragraphs in the provided text."""
        if not self.body_width:
            return text

        assert wrap, "Requires Python 2.3."
        result = ''
        newlines = 0
        for para in text.split("\n"):
            if len(para) > 0:
                if not skipwrap(para):
                    for line in wrap(para, self.body_width):
                        result += line + "\n"
                    result += "\n"
                    newlines = 2
                else:
                    if not onlywhite(para):
                        result += para + "\n"
                        newlines = 1
            else:
                if newlines < 2:
                    result += "\n"
                    newlines += 1
        return result

ordered_list_matcher = re.compile(r'\d+\.\s')
unordered_list_matcher = re.compile(r'[-\*\+]\s')
md_chars_matcher = re.compile(r"([\\\[\]\(\)])")

def skipwrap(para):
    # If the text begins with four spaces or one tab, it's a code block; don't wrap
    if para[0:4] == '    ' or para[0] == '\t':
        return True
    # If the text begins with only two "--", possibly preceded by whitespace, that's
    # an emdash; so wrap.
    stripped = para.lstrip()
    if stripped[0:2] == "--" and stripped[2] != "-":
        return False
    # I'm not sure what this is for; I thought it was to detect lists, but there's
    # a <br>-inside-<span> case in one of the tests that also depends upon it.
    if stripped[0:1] == '-' or stripped[0:1] == '*':
        return True
    # If the text begins with a single -, *, or +, followed by a space, or an integer,
    # followed by a ., followed by a space (in either case optionally preceeded by
    # whitespace), it's a list; don't wrap.
    if ordered_list_matcher.match(stripped) or unordered_list_matcher.match(stripped):
        return True
    return False

def wrapwrite(text):
    text = text.encode('utf-8')
    try: #Python3
        sys.stdout.buffer.write(text)
    except AttributeError:
        sys.stdout.write(text)

def html2text(html, baseurl=''):
    h = HTML2Text(baseurl=baseurl)
    return h.handle(html)

def unescape(s, unicode_snob=False):
    h = HTML2Text()
    h.unicode_snob = unicode_snob
    return h.unescape(s)

def escape_md(text):
    """Escapes markdown-sensitive characters."""
    return md_chars_matcher.sub(r"\\\1", text)

def main():
    baseurl = ''

    p = optparse.OptionParser('%prog [(filename|url) [encoding]]',
                              version='%prog ' + __version__)
    p.add_option("--ignore-emphasis", dest="ignore_emphasis", action="store_true",
        default=IGNORE_EMPHASIS, help="don't include any formatting for emphasis")
    p.add_option("--ignore-links", dest="ignore_links", action="store_true",
        default=IGNORE_ANCHORS, help="don't include any formatting for links")
    p.add_option("--ignore-images", dest="ignore_images", action="store_true",
        default=IGNORE_IMAGES, help="don't include any formatting for images")
    p.add_option("-g", "--google-doc", action="store_true", dest="google_doc",
        default=False, help="convert an html-exported Google Document")
    p.add_option("-d", "--dash-unordered-list", action="store_true", dest="ul_style_dash",
        default=False, help="use a dash rather than a star for unordered list items")
    p.add_option("-b", "--body-width", dest="body_width", action="store", type="int",
        default=BODY_WIDTH, help="number of characters per output line, 0 for no wrap")
    p.add_option("-i", "--google-list-indent", dest="list_indent", action="store", type="int",
        default=GOOGLE_LIST_INDENT, help="number of pixels Google indents nested lists")
    p.add_option("-s", "--hide-strikethrough", action="store_true", dest="hide_strikethrough",
        default=False, help="hide strike-through text. only relevent when -g is specified as well")
    (options, args) = p.parse_args()

    # process input
    encoding = "utf-8"
    if len(args) > 0:
        file_ = args[0]
        if len(args) == 2:
            encoding = args[1]
        if len(args) > 2:
            p.error('Too many arguments')

        if file_.startswith('http://') or file_.startswith('https://'):
            baseurl = file_
            j = urllib.urlopen(baseurl)
            data = j.read()
            if encoding is None:
                try:
                    from feedparser import _getCharacterEncoding as enc
                except ImportError:
                    enc = lambda x, y: ('utf-8', 1)
                encoding = enc(j.headers, data)[0]
                if encoding == 'us-ascii':
                    encoding = 'utf-8'
        else:
            data = open(file_, 'rb').read()
            if encoding is None:
                try:
                    from chardet import detect
                except ImportError:
                    detect = lambda x: {'encoding': 'utf-8'}
                encoding = detect(data)['encoding']
    else:
        data = sys.stdin.read()

    data = data.decode(encoding)
    h = HTML2Text(baseurl=baseurl)
    # handle options
    if options.ul_style_dash: h.ul_item_mark = '-'

    h.body_width = options.body_width
    h.list_indent = options.list_indent
    h.ignore_emphasis = options.ignore_emphasis
    h.ignore_links = options.ignore_links
    h.ignore_images = options.ignore_images
    h.google_doc = options.google_doc
    h.hide_strikethrough = options.hide_strikethrough

    wrapwrite(h.handle(data))


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = evalbased
#
# Unpacker for eval() based packers, a part of javascript beautifier
# by Einar Lielmanis <einar@jsbeautifier.org>
#
#     written by Stefano Sanfilippo <a.little.coder@gmail.com>
#
# usage:
#
# if detect(some_string):
#     unpacked = unpack(some_string)
#

"""Unpacker for eval() based packers: runs JS code and returns result.
Works only if a JS interpreter (e.g. Mozilla's Rhino) is installed and
properly set up on host."""

from subprocess import PIPE, Popen

PRIORITY = 3

def detect(source):
    """Detects if source is likely to be eval() packed."""
    return source.strip().lower().startswith('eval(function(')

def unpack(source):
    """Runs source and return resulting code."""
    return jseval('print %s;' % source[4:]) if detect(source) else source

# In case of failure, we'll just return the original, without crashing on user.
def jseval(script):
    """Run code in the JS interpreter and return output."""
    try:
        interpreter = Popen(['js'], stdin=PIPE, stdout=PIPE)
    except OSError:
        return script
    result, errors = interpreter.communicate(script)
    if interpreter.poll() or errors:
        return script
    return result

########NEW FILE########
__FILENAME__ = javascriptobfuscator
#
# simple unpacker/deobfuscator for scripts messed up with
# javascriptobfuscator.com
#
#     written by Einar Lielmanis <einar@jsbeautifier.org>
#     rewritten in Python by Stefano Sanfilippo <a.little.coder@gmail.com>
#
# Will always return valid javascript: if `detect()` is false, `code` is
# returned, unmodified.
#
# usage:
#
# if javascriptobfuscator.detect(some_string):
#     some_string = javascriptobfuscator.unpack(some_string)
#

"""deobfuscator for scripts messed up with JavascriptObfuscator.com"""

import re

PRIORITY = 1

def smartsplit(code):
    """Split `code` at " symbol, only if it is not escaped."""
    strings = []
    pos = 0
    while pos < len(code):
        if code[pos] == '"':
            word = '' # new word
            pos += 1
            while pos < len(code):
                if code[pos] == '"':
                    break
                if code[pos] == '\\':
                    word += '\\'
                    pos += 1
                word += code[pos]
                pos += 1
            strings.append('"%s"' % word)
        pos += 1
    return strings

def detect(code):
    """Detects if `code` is JavascriptObfuscator.com packed."""
    # prefer `is not` idiom, so that a true boolean is returned
    return (re.search(r'^var _0x[a-f0-9]+ ?\= ?\[', code) is not None)

def unpack(code):
    """Unpacks JavascriptObfuscator.com packed code."""
    if detect(code):
        matches = re.search(r'var (_0x[a-f\d]+) ?\= ?\[(.*?)\];', code)
        if matches:
            variable = matches.group(1)
            dictionary = smartsplit(matches.group(2))
            code = code[len(matches.group(0)):]
            for key, value in enumerate(dictionary):
                code = code.replace(r'%s[%s]' % (variable, key), value)
    return code

########NEW FILE########
__FILENAME__ = myobfuscate
#
# deobfuscator for scripts messed up with myobfuscate.com
# by Einar Lielmanis <einar@jsbeautifier.org>
#
#     written by Stefano Sanfilippo <a.little.coder@gmail.com>
#
# usage:
#
# if detect(some_string):
#     unpacked = unpack(some_string)
#

# CAVEAT by Einar Lielmanis

#
# You really don't want to obfuscate your scripts there: they're tracking
# your unpackings, your script gets turned into something like this,
# as of 2011-08-26:
#
#   var _escape = 'your_script_escaped';
#   var _111 = document.createElement('script');
#   _111.src = 'http://api.www.myobfuscate.com/?getsrc=ok' +
#              '&ref=' + encodeURIComponent(document.referrer) +
#              '&url=' + encodeURIComponent(document.URL);
#   var 000 = document.getElementsByTagName('head')[0];
#   000.appendChild(_111);
#   document.write(unescape(_escape));
#

"""Deobfuscator for scripts messed up with MyObfuscate.com"""

import re
import base64

# Python 2 retrocompatibility
# pylint: disable=F0401
# pylint: disable=E0611
try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote

from jsbeautifier.unpackers import UnpackingError

PRIORITY = 1

CAVEAT = """//
// Unpacker warning: be careful when using myobfuscate.com for your projects:
// scripts obfuscated by the free online version call back home.
//

"""

SIGNATURE = (r'["\x41\x42\x43\x44\x45\x46\x47\x48\x49\x4A\x4B\x4C\x4D\x4E\x4F'
             r'\x50\x51\x52\x53\x54\x55\x56\x57\x58\x59\x5A\x61\x62\x63\x64\x65'
             r'\x66\x67\x68\x69\x6A\x6B\x6C\x6D\x6E\x6F\x70\x71\x72\x73\x74\x75'
             r'\x76\x77\x78\x79\x7A\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39\x2B'
             r'\x2F\x3D","","\x63\x68\x61\x72\x41\x74","\x69\x6E\x64\x65\x78'
             r'\x4F\x66","\x66\x72\x6F\x6D\x43\x68\x61\x72\x43\x6F\x64\x65","'
             r'\x6C\x65\x6E\x67\x74\x68"]')

def detect(source):
    """Detects MyObfuscate.com packer."""
    return SIGNATURE in source

def unpack(source):
    """Unpacks js code packed with MyObfuscate.com"""
    if not detect(source):
        return source
    payload = unquote(_filter(source))
    match = re.search(r"^var _escape\='<script>(.*)<\/script>'",
                      payload, re.DOTALL)
    polished = match.group(1) if match else source
    return CAVEAT + polished

def _filter(source):
    """Extracts and decode payload (original file) from `source`"""
    try:
        varname = re.search(r'eval\(\w+\(\w+\((\w+)\)\)\);', source).group(1)
        reverse = re.search(r"var +%s *\= *'(.*)';" % varname, source).group(1)
    except AttributeError:
        raise UnpackingError('Malformed MyObfuscate data.')
    try:
        return base64.b64decode(reverse[::-1].encode('utf8')).decode('utf8')
    except TypeError:
        raise UnpackingError('MyObfuscate payload is not base64-encoded.')

########NEW FILE########
__FILENAME__ = packer
#
# Unpacker for Dean Edward's p.a.c.k.e.r, a part of javascript beautifier
# by Einar Lielmanis <einar@jsbeautifier.org>
#
#     written by Stefano Sanfilippo <a.little.coder@gmail.com>
#
# usage:
#
# if detect(some_string):
#     unpacked = unpack(some_string)
#

"""Unpacker for Dean Edward's p.a.c.k.e.r"""

import re
import string
from jsbeautifier.unpackers import UnpackingError

PRIORITY = 1

def detect(source):
    """Detects whether `source` is P.A.C.K.E.R. coded."""
    return source.replace(' ', '').startswith('eval(function(p,a,c,k,e,r')

def unpack(source):
    """Unpacks P.A.C.K.E.R. packed js code."""
    payload, symtab, radix, count = _filterargs(source)

    if count != len(symtab):
        raise UnpackingError('Malformed p.a.c.k.e.r. symtab.')

    try:
        unbase = Unbaser(radix)
    except TypeError:
        raise UnpackingError('Unknown p.a.c.k.e.r. encoding.')

    def lookup(match):
        """Look up symbols in the synthetic symtab."""
        word  = match.group(0)
        return symtab[unbase(word)] or word

    source = re.sub(r'\b\w+\b', lookup, payload)
    return _replacestrings(source)

def _filterargs(source):
    """Juice from a source file the four args needed by decoder."""
    argsregex = (r"}\('(.*)', *(\d+), *(\d+), *'(.*)'\."
                 r"split\('\|'\), *(\d+), *(.*)\)\)")
    args = re.search(argsregex, source, re.DOTALL).groups()

    try:
        return args[0], args[3].split('|'), int(args[1]), int(args[2])
    except ValueError:
        raise UnpackingError('Corrupted p.a.c.k.e.r. data.')

def _replacestrings(source):
    """Strip string lookup table (list) and replace values in source."""
    match = re.search(r'var *(_\w+)\=\["(.*?)"\];', source, re.DOTALL)

    if match:
        varname, strings = match.groups()
        startpoint = len(match.group(0))
        lookup = strings.split('","')
        variable = '%s[%%d]' % varname
        for index, value in enumerate(lookup):
            source = source.replace(variable % index, '"%s"' % value)
        return source[startpoint:]
    return source


class Unbaser(object):
    """Functor for a given base. Will efficiently convert
    strings to natural numbers."""
    ALPHABET  = {
        62 : '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',
        95 : (' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ'
              '[\]^_`abcdefghijklmnopqrstuvwxyz{|}~')
    }

    def __init__(self, base):
        self.base = base

        # If base can be handled by int() builtin, let it do it for us
        if 2 <= base <= 36:
            self.unbase = lambda string: int(string, base)
        else:
            # Build conversion dictionary cache
            try:
                self.dictionary = dict((cipher, index) for
                    index, cipher in enumerate(self.ALPHABET[base]))
            except KeyError:
                raise TypeError('Unsupported base encoding.')

            self.unbase = self._dictunbaser

    def __call__(self, string):
        return self.unbase(string)

    def _dictunbaser(self, string):
        """Decodes a  value to an integer."""
        ret = 0
        for index, cipher in enumerate(string[::-1]):
            ret += (self.base ** index) * self.dictionary[cipher]
        return ret

########NEW FILE########
__FILENAME__ = urlencode
#
# Trivial bookmarklet/escaped script detector for the javascript beautifier
#     written by Einar Lielmanis <einar@jsbeautifier.org>
#     rewritten in Python by Stefano Sanfilippo <a.little.coder@gmail.com>
#
# Will always return valid javascript: if `detect()` is false, `code` is
# returned, unmodified.
#
# usage:
#
# some_string = urlencode.unpack(some_string)
#

"""Bookmarklet/escaped script unpacker."""

# Python 2 retrocompatibility
# pylint: disable=F0401
# pylint: disable=E0611
try:
    from urllib import unquote_plus
except ImportError:
    from urllib.parse import unquote_plus

PRIORITY = 0

def detect(code):
    """Detects if a scriptlet is urlencoded."""
    # the fact that script doesn't contain any space, but has %20 instead
    # should be sufficient check for now.
    return ' ' not in code and ('%20' in code or code.count('%') > 3)

def unpack(code):
    """URL decode `code` source string."""
    return unquote_plus(code) if detect(code) else code

########NEW FILE########
__FILENAME__ = pyparsing
# module pyparsing.py
#
# Copyright (c) 2003-2009  Paul T. McGuire
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
#from __future__ import generators

__doc__ = \
"""
pyparsing module - Classes and methods to define and execute parsing grammars

The pyparsing module is an alternative approach to creating and executing simple grammars,
vs. the traditional lex/yacc approach, or the use of regular expressions.  With pyparsing, you
don't need to learn a new syntax for defining grammars or matching expressions - the parsing module
provides a library of classes that you use to construct the grammar directly in Python.

Here is a program to parse "Hello, World!" (or any greeting of the form "<salutation>, <addressee>!")::

    from pyparsing import Word, alphas

    # define grammar of a greeting
    greet = Word( alphas ) + "," + Word( alphas ) + "!"

    hello = "Hello, World!"
    print hello, "->", greet.parseString( hello )

The program outputs the following::

    Hello, World! -> ['Hello', ',', 'World', '!']

The Python representation of the grammar is quite readable, owing to the self-explanatory
class names, and the use of '+', '|' and '^' operators.

The parsed results returned from parseString() can be accessed as a nested list, a dictionary, or an
object with named attributes.

The pyparsing module handles some of the problems that are typically vexing when writing text parsers:
 - extra or missing whitespace (the above program will also handle "Hello,World!", "Hello  ,  World  !", etc.)
 - quoted strings
 - embedded comments
"""

__version__ = "1.5.2"
__versionTime__ = "17 February 2009 19:45"
__author__ = "Paul McGuire <ptmcg@users.sourceforge.net>"

import string
from weakref import ref as wkref
import copy
import sys
import warnings
import re
import sre_constants
#~ sys.stderr.write( "testing pyparsing module, version %s, %s\n" % (__version__,__versionTime__ ) )

__all__ = [
'And', 'CaselessKeyword', 'CaselessLiteral', 'CharsNotIn', 'Combine', 'Dict', 'Each', 'Empty',
'FollowedBy', 'Forward', 'GoToColumn', 'Group', 'Keyword', 'LineEnd', 'LineStart', 'Literal',
'MatchFirst', 'NoMatch', 'NotAny', 'OneOrMore', 'OnlyOnce', 'Optional', 'Or',
'ParseBaseException', 'ParseElementEnhance', 'ParseException', 'ParseExpression', 'ParseFatalException',
'ParseResults', 'ParseSyntaxException', 'ParserElement', 'QuotedString', 'RecursiveGrammarException',
'Regex', 'SkipTo', 'StringEnd', 'StringStart', 'Suppress', 'Token', 'TokenConverter', 'Upcase',
'White', 'Word', 'WordEnd', 'WordStart', 'ZeroOrMore',
'alphanums', 'alphas', 'alphas8bit', 'anyCloseTag', 'anyOpenTag', 'cStyleComment', 'col',
'commaSeparatedList', 'commonHTMLEntity', 'countedArray', 'cppStyleComment', 'dblQuotedString',
'dblSlashComment', 'delimitedList', 'dictOf', 'downcaseTokens', 'empty', 'getTokensEndLoc', 'hexnums',
'htmlComment', 'javaStyleComment', 'keepOriginalText', 'line', 'lineEnd', 'lineStart', 'lineno',
'makeHTMLTags', 'makeXMLTags', 'matchOnlyAtCol', 'matchPreviousExpr', 'matchPreviousLiteral',
'nestedExpr', 'nullDebugAction', 'nums', 'oneOf', 'opAssoc', 'operatorPrecedence', 'printables',
'punc8bit', 'pythonStyleComment', 'quotedString', 'removeQuotes', 'replaceHTMLEntity', 
'replaceWith', 'restOfLine', 'sglQuotedString', 'srange', 'stringEnd',
'stringStart', 'traceParseAction', 'unicodeString', 'upcaseTokens', 'withAttribute',
'indentedBlock', 'originalTextFor',
]


"""
Detect if we are running version 3.X and make appropriate changes
Robert A. Clark
"""
if sys.version_info[0] > 2:
    _PY3K = True
    _MAX_INT = sys.maxsize
    basestring = str
else:
    _PY3K = False
    _MAX_INT = sys.maxint

if not _PY3K:
    def _ustr(obj):
        """Drop-in replacement for str(obj) that tries to be Unicode friendly. It first tries
           str(obj). If that fails with a UnicodeEncodeError, then it tries unicode(obj). It
           then < returns the unicode object | encodes it with the default encoding | ... >.
        """
        if isinstance(obj,unicode):
            return obj

        try:
            # If this works, then _ustr(obj) has the same behaviour as str(obj), so
            # it won't break any existing code.
            return str(obj)

        except UnicodeEncodeError:
            # The Python docs (http://docs.python.org/ref/customization.html#l2h-182)
            # state that "The return value must be a string object". However, does a
            # unicode object (being a subclass of basestring) count as a "string
            # object"?
            # If so, then return a unicode object:
            return unicode(obj)
            # Else encode it... but how? There are many choices... :)
            # Replace unprintables with escape codes?
            #return unicode(obj).encode(sys.getdefaultencoding(), 'backslashreplace_errors')
            # Replace unprintables with question marks?
            #return unicode(obj).encode(sys.getdefaultencoding(), 'replace')
            # ...
else:
    _ustr = str
    unichr = chr

if not _PY3K:
	def _str2dict(strg):
	    return dict( [(c,0) for c in strg] )
else:
	_str2dict = set

def _xml_escape(data):
    """Escape &, <, >, ", ', etc. in a string of data."""

    # ampersand must be replaced first
    from_symbols = '&><"\''
    to_symbols = ['&'+s+';' for s in "amp gt lt quot apos".split()]
    for from_,to_ in zip(from_symbols, to_symbols):
        data = data.replace(from_, to_)
    return data

class _Constants(object):
    pass

if not _PY3K:
    alphas     = string.lowercase + string.uppercase
else:
    alphas     = string.ascii_lowercase + string.ascii_uppercase
nums       = string.digits
hexnums    = nums + "ABCDEFabcdef"
alphanums  = alphas + nums
_bslash = chr(92)
printables = "".join( [ c for c in string.printable if c not in string.whitespace ] )

class ParseBaseException(Exception):
    """base exception class for all parsing runtime exceptions"""
    # Performance tuning: we construct a *lot* of these, so keep this
    # constructor as small and fast as possible
    def __init__( self, pstr, loc=0, msg=None, elem=None ):
        self.loc = loc
        if msg is None:
            self.msg = pstr
            self.pstr = ""
        else:
            self.msg = msg
            self.pstr = pstr
        self.parserElement = elem

    def __getattr__( self, aname ):
        """supported attributes by name are:
            - lineno - returns the line number of the exception text
            - col - returns the column number of the exception text
            - line - returns the line containing the exception text
        """
        if( aname == "lineno" ):
            return lineno( self.loc, self.pstr )
        elif( aname in ("col", "column") ):
            return col( self.loc, self.pstr )
        elif( aname == "line" ):
            return line( self.loc, self.pstr )
        else:
            raise AttributeError(aname)

    def __str__( self ):
        return "%s (at char %d), (line:%d, col:%d)" % \
                ( self.msg, self.loc, self.lineno, self.column )
    def __repr__( self ):
        return _ustr(self)
    def markInputline( self, markerString = ">!<" ):
        """Extracts the exception line from the input string, and marks
           the location of the exception with a special symbol.
        """
        line_str = self.line
        line_column = self.column - 1
        if markerString:
            line_str = "".join( [line_str[:line_column],
                                markerString, line_str[line_column:]])
        return line_str.strip()
    def __dir__(self):
        return "loc msg pstr parserElement lineno col line " \
               "markInputLine __str__ __repr__".split()

class ParseException(ParseBaseException):
    """exception thrown when parse expressions don't match class;
       supported attributes by name are:
        - lineno - returns the line number of the exception text
        - col - returns the column number of the exception text
        - line - returns the line containing the exception text
    """
    pass

class ParseFatalException(ParseBaseException):
    """user-throwable exception thrown when inconsistent parse content
       is found; stops all parsing immediately"""
    pass

class ParseSyntaxException(ParseFatalException):
    """just like ParseFatalException, but thrown internally when an
       ErrorStop indicates that parsing is to stop immediately because
       an unbacktrackable syntax error has been found"""
    def __init__(self, pe):
        super(ParseSyntaxException, self).__init__(
                                    pe.pstr, pe.loc, pe.msg, pe.parserElement)

#~ class ReparseException(ParseBaseException):
    #~ """Experimental class - parse actions can raise this exception to cause
       #~ pyparsing to reparse the input string:
        #~ - with a modified input string, and/or
        #~ - with a modified start location
       #~ Set the values of the ReparseException in the constructor, and raise the
       #~ exception in a parse action to cause pyparsing to use the new string/location.
       #~ Setting the values as None causes no change to be made.
       #~ """
    #~ def __init_( self, newstring, restartLoc ):
        #~ self.newParseText = newstring
        #~ self.reparseLoc = restartLoc

class RecursiveGrammarException(Exception):
    """exception thrown by validate() if the grammar could be improperly recursive"""
    def __init__( self, parseElementList ):
        self.parseElementTrace = parseElementList

    def __str__( self ):
        return "RecursiveGrammarException: %s" % self.parseElementTrace

class _ParseResultsWithOffset(object):
    def __init__(self,p1,p2):
        self.tup = (p1,p2)
    def __getitem__(self,i):
        return self.tup[i]
    def __repr__(self):
        return repr(self.tup)
    def setOffset(self,i):
        self.tup = (self.tup[0],i)

class ParseResults(object):
    """Structured parse results, to provide multiple means of access to the parsed data:
       - as a list (len(results))
       - by list index (results[0], results[1], etc.)
       - by attribute (results.<resultsName>)
       """
    __slots__ = ( "__toklist", "__tokdict", "__doinit", "__name", "__parent", "__accumNames", "__weakref__" )
    def __new__(cls, toklist, name=None, asList=True, modal=True ):
        if isinstance(toklist, cls):
            return toklist
        retobj = object.__new__(cls)
        retobj.__doinit = True
        return retobj

    # Performance tuning: we construct a *lot* of these, so keep this
    # constructor as small and fast as possible
    def __init__( self, toklist, name=None, asList=True, modal=True ):
        if self.__doinit:
            self.__doinit = False
            self.__name = None
            self.__parent = None
            self.__accumNames = {}
            if isinstance(toklist, list):
                self.__toklist = toklist[:]
            else:
                self.__toklist = [toklist]
            self.__tokdict = dict()

        if name:
            if not modal:
                self.__accumNames[name] = 0
            if isinstance(name,int):
                name = _ustr(name) # will always return a str, but use _ustr for consistency
            self.__name = name
            if not toklist in (None,'',[]):
                if isinstance(toklist,basestring):
                    toklist = [ toklist ]
                if asList:
                    if isinstance(toklist,ParseResults):
                        self[name] = _ParseResultsWithOffset(toklist.copy(),0)
                    else:
                        self[name] = _ParseResultsWithOffset(ParseResults(toklist[0]),0)
                    self[name].__name = name
                else:
                    try:
                        self[name] = toklist[0]
                    except (KeyError,TypeError,IndexError):
                        self[name] = toklist

    def __getitem__( self, i ):
        if isinstance( i, (int,slice) ):
            return self.__toklist[i]
        else:
            if i not in self.__accumNames:
                return self.__tokdict[i][-1][0]
            else:
                return ParseResults([ v[0] for v in self.__tokdict[i] ])

    def __setitem__( self, k, v ):
        if isinstance(v,_ParseResultsWithOffset):
            self.__tokdict[k] = self.__tokdict.get(k,list()) + [v]
            sub = v[0]
        elif isinstance(k,int):
            self.__toklist[k] = v
            sub = v
        else:
            self.__tokdict[k] = self.__tokdict.get(k,list()) + [_ParseResultsWithOffset(v,0)]
            sub = v
        if isinstance(sub,ParseResults):
            sub.__parent = wkref(self)

    def __delitem__( self, i ):
        if isinstance(i,(int,slice)):
            mylen = len( self.__toklist )
            del self.__toklist[i]

            # convert int to slice
            if isinstance(i, int):
                if i < 0:
                    i += mylen
                i = slice(i, i+1)
            # get removed indices
            removed = list(range(*i.indices(mylen)))
            removed.reverse()
            # fixup indices in token dictionary
            for name in self.__tokdict:
                occurrences = self.__tokdict[name]
                for j in removed:
                    for k, (value, position) in enumerate(occurrences):
                        occurrences[k] = _ParseResultsWithOffset(value, position - (position > j))
        else:
            del self.__tokdict[i]

    def __contains__( self, k ):
        return k in self.__tokdict

    def __len__( self ): return len( self.__toklist )
    def __bool__(self): return len( self.__toklist ) > 0
    __nonzero__ = __bool__
    def __iter__( self ): return iter( self.__toklist )
    def __reversed__( self ): return iter( reversed(self.__toklist) )
    def keys( self ):
        """Returns all named result keys."""
        return self.__tokdict.keys()

    def pop( self, index=-1 ):
        """Removes and returns item at specified index (default=last).
           Will work with either numeric indices or dict-key indicies."""
        ret = self[index]
        del self[index]
        return ret

    def get(self, key, defaultValue=None):
        """Returns named result matching the given key, or if there is no
           such name, then returns the given defaultValue or None if no
           defaultValue is specified."""
        if key in self:
            return self[key]
        else:
            return defaultValue

    def insert( self, index, insStr ):
        self.__toklist.insert(index, insStr)
        # fixup indices in token dictionary
        for name in self.__tokdict:
            occurrences = self.__tokdict[name]
            for k, (value, position) in enumerate(occurrences):
                occurrences[k] = _ParseResultsWithOffset(value, position + (position > index))

    def items( self ):
        """Returns all named result keys and values as a list of tuples."""
        return [(k,self[k]) for k in self.__tokdict]

    def values( self ):
        """Returns all named result values."""
        return [ v[-1][0] for v in self.__tokdict.values() ]

    def __getattr__( self, name ):
        if name not in self.__slots__:
            if name in self.__tokdict:
                if name not in self.__accumNames:
                    return self.__tokdict[name][-1][0]
                else:
                    return ParseResults([ v[0] for v in self.__tokdict[name] ])
            else:
                return ""
        return None

    def __add__( self, other ):
        ret = self.copy()
        ret += other
        return ret

    def __iadd__( self, other ):
        if other.__tokdict:
            offset = len(self.__toklist)
            addoffset = ( lambda a: (a<0 and offset) or (a+offset) )
            otheritems = other.__tokdict.items()
            otherdictitems = [(k, _ParseResultsWithOffset(v[0],addoffset(v[1])) )
                                for (k,vlist) in otheritems for v in vlist]
            for k,v in otherdictitems:
                self[k] = v
                if isinstance(v[0],ParseResults):
                    v[0].__parent = wkref(self)
            
        self.__toklist += other.__toklist
        self.__accumNames.update( other.__accumNames )
        del other
        return self

    def __repr__( self ):
        return "(%s, %s)" % ( repr( self.__toklist ), repr( self.__tokdict ) )

    def __str__( self ):
        out = "["
        sep = ""
        for i in self.__toklist:
            if isinstance(i, ParseResults):
                out += sep + _ustr(i)
            else:
                out += sep + repr(i)
            sep = ", "
        out += "]"
        return out

    def _asStringList( self, sep='' ):
        out = []
        for item in self.__toklist:
            if out and sep:
                out.append(sep)
            if isinstance( item, ParseResults ):
                out += item._asStringList()
            else:
                out.append( _ustr(item) )
        return out

    def asList( self ):
        """Returns the parse results as a nested list of matching tokens, all converted to strings."""
        out = []
        for res in self.__toklist:
            if isinstance(res,ParseResults):
                out.append( res.asList() )
            else:
                out.append( res )
        return out

    def asDict( self ):
        """Returns the named parse results as dictionary."""
        return dict( self.items() )

    def copy( self ):
        """Returns a new copy of a ParseResults object."""
        ret = ParseResults( self.__toklist )
        ret.__tokdict = self.__tokdict.copy()
        ret.__parent = self.__parent
        ret.__accumNames.update( self.__accumNames )
        ret.__name = self.__name
        return ret

    def asXML( self, doctag=None, namedItemsOnly=False, indent="", formatted=True ):
        """Returns the parse results as XML. Tags are created for tokens and lists that have defined results names."""
        nl = "\n"
        out = []
        namedItems = dict( [ (v[1],k) for (k,vlist) in self.__tokdict.items()
                                                            for v in vlist ] )
        nextLevelIndent = indent + "  "

        # collapse out indents if formatting is not desired
        if not formatted:
            indent = ""
            nextLevelIndent = ""
            nl = ""

        selfTag = None
        if doctag is not None:
            selfTag = doctag
        else:
            if self.__name:
                selfTag = self.__name

        if not selfTag:
            if namedItemsOnly:
                return ""
            else:
                selfTag = "ITEM"

        out += [ nl, indent, "<", selfTag, ">" ]

        worklist = self.__toklist
        for i,res in enumerate(worklist):
            if isinstance(res,ParseResults):
                if i in namedItems:
                    out += [ res.asXML(namedItems[i],
                                        namedItemsOnly and doctag is None,
                                        nextLevelIndent,
                                        formatted)]
                else:
                    out += [ res.asXML(None,
                                        namedItemsOnly and doctag is None,
                                        nextLevelIndent,
                                        formatted)]
            else:
                # individual token, see if there is a name for it
                resTag = None
                if i in namedItems:
                    resTag = namedItems[i]
                if not resTag:
                    if namedItemsOnly:
                        continue
                    else:
                        resTag = "ITEM"
                xmlBodyText = _xml_escape(_ustr(res))
                out += [ nl, nextLevelIndent, "<", resTag, ">",
                                                xmlBodyText,
                                                "</", resTag, ">" ]

        out += [ nl, indent, "</", selfTag, ">" ]
        return "".join(out)

    def __lookup(self,sub):
        for k,vlist in self.__tokdict.items():
            for v,loc in vlist:
                if sub is v:
                    return k
        return None

    def getName(self):
        """Returns the results name for this token expression."""
        if self.__name:
            return self.__name
        elif self.__parent:
            par = self.__parent()
            if par:
                return par.__lookup(self)
            else:
                return None
        elif (len(self) == 1 and
               len(self.__tokdict) == 1 and
               self.__tokdict.values()[0][0][1] in (0,-1)):
            return self.__tokdict.keys()[0]
        else:
            return None

    def dump(self,indent='',depth=0):
        """Diagnostic method for listing out the contents of a ParseResults.
           Accepts an optional indent argument so that this string can be embedded
           in a nested display of other data."""
        out = []
        out.append( indent+_ustr(self.asList()) )
        keys = self.items()
        keys.sort()
        for k,v in keys:
            if out:
                out.append('\n')
            out.append( "%s%s- %s: " % (indent,('  '*depth), k) )
            if isinstance(v,ParseResults):
                if v.keys():
                    #~ out.append('\n')
                    out.append( v.dump(indent,depth+1) )
                    #~ out.append('\n')
                else:
                    out.append(_ustr(v))
            else:
                out.append(_ustr(v))
        #~ out.append('\n')
        return "".join(out)

    # add support for pickle protocol
    def __getstate__(self):
        return ( self.__toklist,
                 ( self.__tokdict.copy(),
                   self.__parent is not None and self.__parent() or None,
                   self.__accumNames,
                   self.__name ) )

    def __setstate__(self,state):
        self.__toklist = state[0]
        self.__tokdict, \
        par, \
        inAccumNames, \
        self.__name = state[1]
        self.__accumNames = {}
        self.__accumNames.update(inAccumNames)
        if par is not None:
            self.__parent = wkref(par)
        else:
            self.__parent = None

    def __dir__(self):
        return dir(super(ParseResults,self)) + self.keys()

def col (loc,strg):
    """Returns current column within a string, counting newlines as line separators.
   The first column is number 1.

   Note: the default parsing behavior is to expand tabs in the input string
   before starting the parsing process.  See L{I{ParserElement.parseString}<ParserElement.parseString>} for more information
   on parsing strings containing <TAB>s, and suggested methods to maintain a
   consistent view of the parsed string, the parse location, and line and column
   positions within the parsed string.
   """
    return (loc<len(strg) and strg[loc] == '\n') and 1 or loc - strg.rfind("\n", 0, loc)

def lineno(loc,strg):
    """Returns current line number within a string, counting newlines as line separators.
   The first line is number 1.

   Note: the default parsing behavior is to expand tabs in the input string
   before starting the parsing process.  See L{I{ParserElement.parseString}<ParserElement.parseString>} for more information
   on parsing strings containing <TAB>s, and suggested methods to maintain a
   consistent view of the parsed string, the parse location, and line and column
   positions within the parsed string.
   """
    return strg.count("\n",0,loc) + 1

def line( loc, strg ):
    """Returns the line of text containing loc within a string, counting newlines as line separators.
       """
    lastCR = strg.rfind("\n", 0, loc)
    nextCR = strg.find("\n", loc)
    if nextCR > 0:
        return strg[lastCR+1:nextCR]
    else:
        return strg[lastCR+1:]

def _defaultStartDebugAction( instring, loc, expr ):
    print ("Match " + _ustr(expr) + " at loc " + _ustr(loc) + "(%d,%d)" % ( lineno(loc,instring), col(loc,instring) ))

def _defaultSuccessDebugAction( instring, startloc, endloc, expr, toks ):
    print ("Matched " + _ustr(expr) + " -> " + str(toks.asList()))

def _defaultExceptionDebugAction( instring, loc, expr, exc ):
    print ("Exception raised:" + _ustr(exc))

def nullDebugAction(*args):
    """'Do-nothing' debug action, to suppress debugging output during parsing."""
    pass

class ParserElement(object):
    """Abstract base level parser element class."""
    DEFAULT_WHITE_CHARS = " \n\t\r"

    def setDefaultWhitespaceChars( chars ):
        """Overrides the default whitespace chars
        """
        ParserElement.DEFAULT_WHITE_CHARS = chars
    setDefaultWhitespaceChars = staticmethod(setDefaultWhitespaceChars)

    def __init__( self, savelist=False ):
        self.parseAction = list()
        self.failAction = None
        #~ self.name = "<unknown>"  # don't define self.name, let subclasses try/except upcall
        self.strRepr = None
        self.resultsName = None
        self.saveAsList = savelist
        self.skipWhitespace = True
        self.whiteChars = ParserElement.DEFAULT_WHITE_CHARS
        self.copyDefaultWhiteChars = True
        self.mayReturnEmpty = False # used when checking for left-recursion
        self.keepTabs = False
        self.ignoreExprs = list()
        self.debug = False
        self.streamlined = False
        self.mayIndexError = True # used to optimize exception handling for subclasses that don't advance parse index
        self.errmsg = ""
        self.modalResults = True # used to mark results names as modal (report only last) or cumulative (list all)
        self.debugActions = ( None, None, None ) #custom debug actions
        self.re = None
        self.callPreparse = True # used to avoid redundant calls to preParse
        self.callDuringTry = False

    def copy( self ):
        """Make a copy of this ParserElement.  Useful for defining different parse actions
           for the same parsing pattern, using copies of the original parse element."""
        cpy = copy.copy( self )
        cpy.parseAction = self.parseAction[:]
        cpy.ignoreExprs = self.ignoreExprs[:]
        if self.copyDefaultWhiteChars:
            cpy.whiteChars = ParserElement.DEFAULT_WHITE_CHARS
        return cpy

    def setName( self, name ):
        """Define name for this expression, for use in debugging."""
        self.name = name
        self.errmsg = "Expected " + self.name
        if hasattr(self,"exception"):
            self.exception.msg = self.errmsg
        return self

    def setResultsName( self, name, listAllMatches=False ):
        """Define name for referencing matching tokens as a nested attribute
           of the returned parse results.
           NOTE: this returns a *copy* of the original ParserElement object;
           this is so that the client can define a basic element, such as an
           integer, and reference it in multiple places with different names.
        """
        newself = self.copy()
        newself.resultsName = name
        newself.modalResults = not listAllMatches
        return newself

    def setBreak(self,breakFlag = True):
        """Method to invoke the Python pdb debugger when this element is
           about to be parsed. Set breakFlag to True to enable, False to
           disable.
        """
        if breakFlag:
            _parseMethod = self._parse
            def breaker(instring, loc, doActions=True, callPreParse=True):
                import pdb
                pdb.set_trace()
                return _parseMethod( instring, loc, doActions, callPreParse )
            breaker._originalParseMethod = _parseMethod
            self._parse = breaker
        else:
            if hasattr(self._parse,"_originalParseMethod"):
                self._parse = self._parse._originalParseMethod
        return self

    def _normalizeParseActionArgs( f ):
        """Internal method used to decorate parse actions that take fewer than 3 arguments,
           so that all parse actions can be called as f(s,l,t)."""
        STAR_ARGS = 4

        try:
            restore = None
            if isinstance(f,type):
                restore = f
                f = f.__init__
            if not _PY3K:
                codeObj = f.func_code
            else:
                codeObj = f.code
            if codeObj.co_flags & STAR_ARGS:
                return f
            numargs = codeObj.co_argcount
            if not _PY3K:
                if hasattr(f,"im_self"):
                    numargs -= 1
            else:
                if hasattr(f,"__self__"):
                    numargs -= 1
            if restore:
                f = restore
        except AttributeError:
            try:
                if not _PY3K:
                    call_im_func_code = f.__call__.im_func.func_code
                else:
                    call_im_func_code = f.__code__

                # not a function, must be a callable object, get info from the
                # im_func binding of its bound __call__ method
                if call_im_func_code.co_flags & STAR_ARGS:
                    return f
                numargs = call_im_func_code.co_argcount
                if not _PY3K:
                    if hasattr(f.__call__,"im_self"):
                        numargs -= 1
                else:
                    if hasattr(f.__call__,"__self__"):
                        numargs -= 0
            except AttributeError:
                if not _PY3K:
                    call_func_code = f.__call__.func_code
                else:
                    call_func_code = f.__call__.__code__
                # not a bound method, get info directly from __call__ method
                if call_func_code.co_flags & STAR_ARGS:
                    return f
                numargs = call_func_code.co_argcount
                if not _PY3K:
                    if hasattr(f.__call__,"im_self"):
                        numargs -= 1
                else:
                    if hasattr(f.__call__,"__self__"):
                        numargs -= 1


        #~ print ("adding function %s with %d args" % (f.func_name,numargs))
        if numargs == 3:
            return f
        else:
            if numargs > 3:
                def tmp(s,l,t):
                    return f(f.__call__.__self__, s,l,t)
            if numargs == 2:
                def tmp(s,l,t):
                    return f(l,t)
            elif numargs == 1:
                def tmp(s,l,t):
                    return f(t)
            else: #~ numargs == 0:
                def tmp(s,l,t):
                    return f()
            try:
                tmp.__name__ = f.__name__
            except (AttributeError,TypeError):
                # no need for special handling if attribute doesnt exist
                pass
            try:
                tmp.__doc__ = f.__doc__
            except (AttributeError,TypeError):
                # no need for special handling if attribute doesnt exist
                pass
            try:
                tmp.__dict__.update(f.__dict__)
            except (AttributeError,TypeError):
                # no need for special handling if attribute doesnt exist
                pass
            return tmp
    _normalizeParseActionArgs = staticmethod(_normalizeParseActionArgs)

    def setParseAction( self, *fns, **kwargs ):
        """Define action to perform when successfully matching parse element definition.
           Parse action fn is a callable method with 0-3 arguments, called as fn(s,loc,toks),
           fn(loc,toks), fn(toks), or just fn(), where:
            - s   = the original string being parsed (see note below)
            - loc = the location of the matching substring
            - toks = a list of the matched tokens, packaged as a ParseResults object
           If the functions in fns modify the tokens, they can return them as the return
           value from fn, and the modified list of tokens will replace the original.
           Otherwise, fn does not need to return any value.

           Note: the default parsing behavior is to expand tabs in the input string
           before starting the parsing process.  See L{I{parseString}<parseString>} for more information
           on parsing strings containing <TAB>s, and suggested methods to maintain a
           consistent view of the parsed string, the parse location, and line and column
           positions within the parsed string.
           """
        self.parseAction = list(map(self._normalizeParseActionArgs, list(fns)))
        self.callDuringTry = ("callDuringTry" in kwargs and kwargs["callDuringTry"])
        return self

    def addParseAction( self, *fns, **kwargs ):
        """Add parse action to expression's list of parse actions. See L{I{setParseAction}<setParseAction>}."""
        self.parseAction += list(map(self._normalizeParseActionArgs, list(fns)))
        self.callDuringTry = self.callDuringTry or ("callDuringTry" in kwargs and kwargs["callDuringTry"])
        return self

    def setFailAction( self, fn ):
        """Define action to perform if parsing fails at this expression.
           Fail acton fn is a callable function that takes the arguments
           fn(s,loc,expr,err) where:
            - s = string being parsed
            - loc = location where expression match was attempted and failed
            - expr = the parse expression that failed
            - err = the exception thrown
           The function returns no value.  It may throw ParseFatalException
           if it is desired to stop parsing immediately."""
        self.failAction = fn
        return self

    def _skipIgnorables( self, instring, loc ):
        exprsFound = True
        while exprsFound:
            exprsFound = False
            for e in self.ignoreExprs:
                try:
                    while 1:
                        loc,dummy = e._parse( instring, loc )
                        exprsFound = True
                except ParseException:
                    pass
        return loc

    def preParse( self, instring, loc ):
        if self.ignoreExprs:
            loc = self._skipIgnorables( instring, loc )

        if self.skipWhitespace:
            wt = self.whiteChars
            instrlen = len(instring)
            while loc < instrlen and instring[loc] in wt:
                loc += 1

        return loc

    def parseImpl( self, instring, loc, doActions=True ):
        return loc, []

    def postParse( self, instring, loc, tokenlist ):
        return tokenlist

    #~ @profile
    def _parseNoCache( self, instring, loc, doActions=True, callPreParse=True ):
        debugging = ( self.debug ) #and doActions )

        if debugging or self.failAction:
            #~ print ("Match",self,"at loc",loc,"(%d,%d)" % ( lineno(loc,instring), col(loc,instring) ))
            if (self.debugActions[0] ):
                self.debugActions[0]( instring, loc, self )
            if callPreParse and self.callPreparse:
                preloc = self.preParse( instring, loc )
            else:
                preloc = loc
            tokensStart = loc
            try:
                try:
                    loc,tokens = self.parseImpl( instring, preloc, doActions )
                except IndexError:
                    raise ParseException( instring, len(instring), self.errmsg, self )
            except ParseBaseException, err:
                #~ print ("Exception raised:", err)
                if self.debugActions[2]:
                    self.debugActions[2]( instring, tokensStart, self, err )
                if self.failAction:
                    self.failAction( instring, tokensStart, self, err )
                raise
        else:
            if callPreParse and self.callPreparse:
                preloc = self.preParse( instring, loc )
            else:
                preloc = loc
            tokensStart = loc
            if self.mayIndexError or loc >= len(instring):
                try:
                    loc,tokens = self.parseImpl( instring, preloc, doActions )
                except IndexError:
                    raise ParseException( instring, len(instring), self.errmsg, self )
            else:
                loc,tokens = self.parseImpl( instring, preloc, doActions )

        tokens = self.postParse( instring, loc, tokens )

        retTokens = ParseResults( tokens, self.resultsName, asList=self.saveAsList, modal=self.modalResults )
        if self.parseAction and (doActions or self.callDuringTry):
            if debugging:
                try:
                    for fn in self.parseAction:
                        tokens = fn( instring, tokensStart, retTokens )
                        if tokens is not None:
                            retTokens = ParseResults( tokens,
                                                      self.resultsName,
                                                      asList=self.saveAsList and isinstance(tokens,(ParseResults,list)),
                                                      modal=self.modalResults )
                except ParseBaseException, err:
                    #~ print "Exception raised in user parse action:", err
                    if (self.debugActions[2] ):
                        self.debugActions[2]( instring, tokensStart, self, err )
                    raise
            else:
                for fn in self.parseAction:
                    tokens = fn( instring, tokensStart, retTokens )
                    if tokens is not None:
                        retTokens = ParseResults( tokens,
                                                  self.resultsName,
                                                  asList=self.saveAsList and isinstance(tokens,(ParseResults,list)),
                                                  modal=self.modalResults )

        if debugging:
            #~ print ("Matched",self,"->",retTokens.asList())
            if (self.debugActions[1] ):
                self.debugActions[1]( instring, tokensStart, loc, self, retTokens )

        return loc, retTokens

    def tryParse( self, instring, loc ):
        try:
            return self._parse( instring, loc, doActions=False )[0]
        except ParseFatalException:
            raise ParseException( instring, loc, self.errmsg, self)

    # this method gets repeatedly called during backtracking with the same arguments -
    # we can cache these arguments and save ourselves the trouble of re-parsing the contained expression
    def _parseCache( self, instring, loc, doActions=True, callPreParse=True ):
        lookup = (self,instring,loc,callPreParse,doActions)
        if lookup in ParserElement._exprArgCache:
            value = ParserElement._exprArgCache[ lookup ]
            if isinstance(value,Exception):
                raise value
            return value
        else:
            try:
                value = self._parseNoCache( instring, loc, doActions, callPreParse )
                ParserElement._exprArgCache[ lookup ] = (value[0],value[1].copy())
                return value
            except ParseBaseException, pe:
                ParserElement._exprArgCache[ lookup ] = pe
                raise

    _parse = _parseNoCache

    # argument cache for optimizing repeated calls when backtracking through recursive expressions
    _exprArgCache = {}
    def resetCache():
        ParserElement._exprArgCache.clear()
    resetCache = staticmethod(resetCache)

    _packratEnabled = False
    def enablePackrat():
        """Enables "packrat" parsing, which adds memoizing to the parsing logic.
           Repeated parse attempts at the same string location (which happens
           often in many complex grammars) can immediately return a cached value,
           instead of re-executing parsing/validating code.  Memoizing is done of
           both valid results and parsing exceptions.

           This speedup may break existing programs that use parse actions that
           have side-effects.  For this reason, packrat parsing is disabled when
           you first import pyparsing.  To activate the packrat feature, your
           program must call the class method ParserElement.enablePackrat().  If
           your program uses psyco to "compile as you go", you must call
           enablePackrat before calling psyco.full().  If you do not do this,
           Python will crash.  For best results, call enablePackrat() immediately
           after importing pyparsing.
        """
        if not ParserElement._packratEnabled:
            ParserElement._packratEnabled = True
            ParserElement._parse = ParserElement._parseCache
    enablePackrat = staticmethod(enablePackrat)

    def parseString( self, instring, parseAll=False ):
        """Execute the parse expression with the given string.
           This is the main interface to the client code, once the complete
           expression has been built.

           If you want the grammar to require that the entire input string be
           successfully parsed, then set parseAll to True (equivalent to ending
           the grammar with StringEnd()).

           Note: parseString implicitly calls expandtabs() on the input string,
           in order to report proper column numbers in parse actions.
           If the input string contains tabs and
           the grammar uses parse actions that use the loc argument to index into the
           string being parsed, you can ensure you have a consistent view of the input
           string by:
            - calling parseWithTabs on your grammar before calling parseString
              (see L{I{parseWithTabs}<parseWithTabs>})
            - define your parse action using the full (s,loc,toks) signature, and
              reference the input string using the parse action's s argument
            - explictly expand the tabs in your input string before calling
              parseString
        """
        ParserElement.resetCache()
        if not self.streamlined:
            self.streamline()
            #~ self.saveAsList = True
        for e in self.ignoreExprs:
            e.streamline()
        if not self.keepTabs:
            instring = instring.expandtabs()
        try:
            loc, tokens = self._parse( instring, 0 )
            if parseAll:
                loc = self.preParse( instring, loc )
                StringEnd()._parse( instring, loc )
        except ParseBaseException, exc:
            # catch and re-raise exception from here, clears out pyparsing internal stack trace
            raise exc
        else:
            return tokens

    def scanString( self, instring, maxMatches=_MAX_INT ):
        """Scan the input string for expression matches.  Each match will return the
           matching tokens, start location, and end location.  May be called with optional
           maxMatches argument, to clip scanning after 'n' matches are found.

           Note that the start and end locations are reported relative to the string
           being parsed.  See L{I{parseString}<parseString>} for more information on parsing
           strings with embedded tabs."""
        if not self.streamlined:
            self.streamline()
        for e in self.ignoreExprs:
            e.streamline()

        if not self.keepTabs:
            instring = _ustr(instring).expandtabs()
        instrlen = len(instring)
        loc = 0
        preparseFn = self.preParse
        parseFn = self._parse
        ParserElement.resetCache()
        matches = 0
        try:
            while loc <= instrlen and matches < maxMatches:
                try:
                    preloc = preparseFn( instring, loc )
                    nextLoc,tokens = parseFn( instring, preloc, callPreParse=False )
                except ParseException:
                    loc = preloc+1
                else:
                    matches += 1
                    yield tokens, preloc, nextLoc
                    loc = nextLoc
        except ParseBaseException, pe:
            raise pe

    def transformString( self, instring ):
        """Extension to scanString, to modify matching text with modified tokens that may
           be returned from a parse action.  To use transformString, define a grammar and
           attach a parse action to it that modifies the returned token list.
           Invoking transformString() on a target string will then scan for matches,
           and replace the matched text patterns according to the logic in the parse
           action.  transformString() returns the resulting transformed string."""
        out = []
        lastE = 0
        # force preservation of <TAB>s, to minimize unwanted transformation of string, and to
        # keep string locs straight between transformString and scanString
        self.keepTabs = True
        try:
            for t,s,e in self.scanString( instring ):
                out.append( instring[lastE:s] )
                if t:
                    if isinstance(t,ParseResults):
                        out += t.asList()
                    elif isinstance(t,list):
                        out += t
                    else:
                        out.append(t)
                lastE = e
            out.append(instring[lastE:])
            return "".join(map(_ustr,out))
        except ParseBaseException, pe:
            raise pe

    def searchString( self, instring, maxMatches=_MAX_INT ):
        """Another extension to scanString, simplifying the access to the tokens found
           to match the given parse expression.  May be called with optional
           maxMatches argument, to clip searching after 'n' matches are found.
        """
        try:
            return ParseResults([ t for t,s,e in self.scanString( instring, maxMatches ) ])
        except ParseBaseException, pe:
            raise pe

    def __add__(self, other ):
        """Implementation of + operator - returns And"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return And( [ self, other ] )

    def __radd__(self, other ):
        """Implementation of + operator when left operand is not a ParserElement"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other + self

    def __sub__(self, other):
        """Implementation of - operator, returns And with error stop"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return And( [ self, And._ErrorStop(), other ] )

    def __rsub__(self, other ):
        """Implementation of - operator when left operand is not a ParserElement"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other - self

    def __mul__(self,other):
        if isinstance(other,int):
            minElements, optElements = other,0
        elif isinstance(other,tuple):
            other = (other + (None, None))[:2]
            if other[0] is None:
                other = (0, other[1])
            if isinstance(other[0],int) and other[1] is None:
                if other[0] == 0:
                    return ZeroOrMore(self)
                if other[0] == 1:
                    return OneOrMore(self)
                else:
                    return self*other[0] + ZeroOrMore(self)
            elif isinstance(other[0],int) and isinstance(other[1],int):
                minElements, optElements = other
                optElements -= minElements
            else:
                raise TypeError("cannot multiply 'ParserElement' and ('%s','%s') objects", type(other[0]),type(other[1]))
        else:
            raise TypeError("cannot multiply 'ParserElement' and '%s' objects", type(other))

        if minElements < 0:
            raise ValueError("cannot multiply ParserElement by negative value")
        if optElements < 0:
            raise ValueError("second tuple value must be greater or equal to first tuple value")
        if minElements == optElements == 0:
            raise ValueError("cannot multiply ParserElement by 0 or (0,0)")

        if (optElements):
            def makeOptionalList(n):
                if n>1:
                    return Optional(self + makeOptionalList(n-1))
                else:
                    return Optional(self)
            if minElements:
                if minElements == 1:
                    ret = self + makeOptionalList(optElements)
                else:
                    ret = And([self]*minElements) + makeOptionalList(optElements)
            else:
                ret = makeOptionalList(optElements)
        else:
            if minElements == 1:
                ret = self
            else:
                ret = And([self]*minElements)
        return ret

    def __rmul__(self, other):
        return self.__mul__(other)

    def __or__(self, other ):
        """Implementation of | operator - returns MatchFirst"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return MatchFirst( [ self, other ] )

    def __ror__(self, other ):
        """Implementation of | operator when left operand is not a ParserElement"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other | self

    def __xor__(self, other ):
        """Implementation of ^ operator - returns Or"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return Or( [ self, other ] )

    def __rxor__(self, other ):
        """Implementation of ^ operator when left operand is not a ParserElement"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other ^ self

    def __and__(self, other ):
        """Implementation of & operator - returns Each"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return Each( [ self, other ] )

    def __rand__(self, other ):
        """Implementation of & operator when left operand is not a ParserElement"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other & self

    def __invert__( self ):
        """Implementation of ~ operator - returns NotAny"""
        return NotAny( self )

    def __call__(self, name):
        """Shortcut for setResultsName, with listAllMatches=default::
             userdata = Word(alphas).setResultsName("name") + Word(nums+"-").setResultsName("socsecno")
           could be written as::
             userdata = Word(alphas)("name") + Word(nums+"-")("socsecno")
           """
        return self.setResultsName(name)

    def suppress( self ):
        """Suppresses the output of this ParserElement; useful to keep punctuation from
           cluttering up returned output.
        """
        return Suppress( self )

    def leaveWhitespace( self ):
        """Disables the skipping of whitespace before matching the characters in the
           ParserElement's defined pattern.  This is normally only used internally by
           the pyparsing module, but may be needed in some whitespace-sensitive grammars.
        """
        self.skipWhitespace = False
        return self

    def setWhitespaceChars( self, chars ):
        """Overrides the default whitespace chars
        """
        self.skipWhitespace = True
        self.whiteChars = chars
        self.copyDefaultWhiteChars = False
        return self

    def parseWithTabs( self ):
        """Overrides default behavior to expand <TAB>s to spaces before parsing the input string.
           Must be called before parseString when the input grammar contains elements that
           match <TAB> characters."""
        self.keepTabs = True
        return self

    def ignore( self, other ):
        """Define expression to be ignored (e.g., comments) while doing pattern
           matching; may be called repeatedly, to define multiple comment or other
           ignorable patterns.
        """
        if isinstance( other, Suppress ):
            if other not in self.ignoreExprs:
                self.ignoreExprs.append( other )
        else:
            self.ignoreExprs.append( Suppress( other ) )
        return self

    def setDebugActions( self, startAction, successAction, exceptionAction ):
        """Enable display of debugging messages while doing pattern matching."""
        self.debugActions = (startAction or _defaultStartDebugAction,
                             successAction or _defaultSuccessDebugAction,
                             exceptionAction or _defaultExceptionDebugAction)
        self.debug = True
        return self

    def setDebug( self, flag=True ):
        """Enable display of debugging messages while doing pattern matching.
           Set flag to True to enable, False to disable."""
        if flag:
            self.setDebugActions( _defaultStartDebugAction, _defaultSuccessDebugAction, _defaultExceptionDebugAction )
        else:
            self.debug = False
        return self

    def __str__( self ):
        return self.name

    def __repr__( self ):
        return _ustr(self)

    def streamline( self ):
        self.streamlined = True
        self.strRepr = None
        return self

    def checkRecursion( self, parseElementList ):
        pass

    def validate( self, validateTrace=[] ):
        """Check defined expressions for valid structure, check for infinite recursive definitions."""
        self.checkRecursion( [] )

    def parseFile( self, file_or_filename, parseAll=False ):
        """Execute the parse expression on the given file or filename.
           If a filename is specified (instead of a file object),
           the entire file is opened, read, and closed before parsing.
        """
        try:
            file_contents = file_or_filename.read()
        except AttributeError:
            f = open(file_or_filename, "rb")
            file_contents = f.read()
            f.close()
        try:
            return self.parseString(file_contents, parseAll)
        except ParseBaseException, exc:
            # catch and re-raise exception from here, clears out pyparsing internal stack trace
            raise exc

    def getException(self):
        return ParseException("",0,self.errmsg,self)

    def __getattr__(self,aname):
        if aname == "myException":
            self.myException = ret = self.getException();
            return ret;
        else:
            raise AttributeError("no such attribute " + aname)

    def __eq__(self,other):
        if isinstance(other, ParserElement):
            return self is other or self.__dict__ == other.__dict__
        elif isinstance(other, basestring):
            try:
                self.parseString(_ustr(other), parseAll=True)
                return True
            except ParseBaseException:
                return False
        else:
            return super(ParserElement,self)==other

    def __ne__(self,other):
        return not (self == other)

    def __hash__(self):
        return hash(id(self))

    def __req__(self,other):
        return self == other

    def __rne__(self,other):
        return not (self == other)


class Token(ParserElement):
    """Abstract ParserElement subclass, for defining atomic matching patterns."""
    def __init__( self ):
        super(Token,self).__init__( savelist=False )
        #self.myException = ParseException("",0,"",self)

    def setName(self, name):
        s = super(Token,self).setName(name)
        self.errmsg = "Expected " + self.name
        #s.myException.msg = self.errmsg
        return s


class Empty(Token):
    """An empty token, will always match."""
    def __init__( self ):
        super(Empty,self).__init__()
        self.name = "Empty"
        self.mayReturnEmpty = True
        self.mayIndexError = False


class NoMatch(Token):
    """A token that will never match."""
    def __init__( self ):
        super(NoMatch,self).__init__()
        self.name = "NoMatch"
        self.mayReturnEmpty = True
        self.mayIndexError = False
        self.errmsg = "Unmatchable token"
        #self.myException.msg = self.errmsg

    def parseImpl( self, instring, loc, doActions=True ):
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc


class Literal(Token):
    """Token to exactly match a specified string."""
    def __init__( self, matchString ):
        super(Literal,self).__init__()
        self.match = matchString
        self.matchLen = len(matchString)
        try:
            self.firstMatchChar = matchString[0]
        except IndexError:
            warnings.warn("null string passed to Literal; use Empty() instead",
                            SyntaxWarning, stacklevel=2)
            self.__class__ = Empty
        self.name = '"%s"' % _ustr(self.match)
        self.errmsg = "Expected " + self.name
        self.mayReturnEmpty = False
        #self.myException.msg = self.errmsg
        self.mayIndexError = False

    # Performance tuning: this routine gets called a *lot*
    # if this is a single character match string  and the first character matches,
    # short-circuit as quickly as possible, and avoid calling startswith
    #~ @profile
    def parseImpl( self, instring, loc, doActions=True ):
        if (instring[loc] == self.firstMatchChar and
            (self.matchLen==1 or instring.startswith(self.match,loc)) ):
            return loc+self.matchLen, self.match
        #~ raise ParseException( instring, loc, self.errmsg )
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc
_L = Literal

class Keyword(Token):
    """Token to exactly match a specified string as a keyword, that is, it must be
       immediately followed by a non-keyword character.  Compare with Literal::
         Literal("if") will match the leading 'if' in 'ifAndOnlyIf'.
         Keyword("if") will not; it will only match the leading 'if in 'if x=1', or 'if(y==2)'
       Accepts two optional constructor arguments in addition to the keyword string:
       identChars is a string of characters that would be valid identifier characters,
       defaulting to all alphanumerics + "_" and "$"; caseless allows case-insensitive
       matching, default is False.
    """
    DEFAULT_KEYWORD_CHARS = alphanums+"_$"

    def __init__( self, matchString, identChars=DEFAULT_KEYWORD_CHARS, caseless=False ):
        super(Keyword,self).__init__()
        self.match = matchString
        self.matchLen = len(matchString)
        try:
            self.firstMatchChar = matchString[0]
        except IndexError:
            warnings.warn("null string passed to Keyword; use Empty() instead",
                            SyntaxWarning, stacklevel=2)
        self.name = '"%s"' % self.match
        self.errmsg = "Expected " + self.name
        self.mayReturnEmpty = False
        #self.myException.msg = self.errmsg
        self.mayIndexError = False
        self.caseless = caseless
        if caseless:
            self.caselessmatch = matchString.upper()
            identChars = identChars.upper()
        self.identChars = _str2dict(identChars)

    def parseImpl( self, instring, loc, doActions=True ):
        if self.caseless:
            if ( (instring[ loc:loc+self.matchLen ].upper() == self.caselessmatch) and
                 (loc >= len(instring)-self.matchLen or instring[loc+self.matchLen].upper() not in self.identChars) and
                 (loc == 0 or instring[loc-1].upper() not in self.identChars) ):
                return loc+self.matchLen, self.match
        else:
            if (instring[loc] == self.firstMatchChar and
                (self.matchLen==1 or instring.startswith(self.match,loc)) and
                (loc >= len(instring)-self.matchLen or instring[loc+self.matchLen] not in self.identChars) and
                (loc == 0 or instring[loc-1] not in self.identChars) ):
                return loc+self.matchLen, self.match
        #~ raise ParseException( instring, loc, self.errmsg )
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc

    def copy(self):
        c = super(Keyword,self).copy()
        c.identChars = Keyword.DEFAULT_KEYWORD_CHARS
        return c

    def setDefaultKeywordChars( chars ):
        """Overrides the default Keyword chars
        """
        Keyword.DEFAULT_KEYWORD_CHARS = chars
    setDefaultKeywordChars = staticmethod(setDefaultKeywordChars)

class CaselessLiteral(Literal):
    """Token to match a specified string, ignoring case of letters.
       Note: the matched results will always be in the case of the given
       match string, NOT the case of the input text.
    """
    def __init__( self, matchString ):
        super(CaselessLiteral,self).__init__( matchString.upper() )
        # Preserve the defining literal.
        self.returnString = matchString
        self.name = "'%s'" % self.returnString
        self.errmsg = "Expected " + self.name
        #self.myException.msg = self.errmsg

    def parseImpl( self, instring, loc, doActions=True ):
        if instring[ loc:loc+self.matchLen ].upper() == self.match:
            return loc+self.matchLen, self.returnString
        #~ raise ParseException( instring, loc, self.errmsg )
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc

class CaselessKeyword(Keyword):
    def __init__( self, matchString, identChars=Keyword.DEFAULT_KEYWORD_CHARS ):
        super(CaselessKeyword,self).__init__( matchString, identChars, caseless=True )

    def parseImpl( self, instring, loc, doActions=True ):
        if ( (instring[ loc:loc+self.matchLen ].upper() == self.caselessmatch) and
             (loc >= len(instring)-self.matchLen or instring[loc+self.matchLen].upper() not in self.identChars) ):
            return loc+self.matchLen, self.match
        #~ raise ParseException( instring, loc, self.errmsg )
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc

class Word(Token):
    """Token for matching words composed of allowed character sets.
       Defined with string containing all allowed initial characters,
       an optional string containing allowed body characters (if omitted,
       defaults to the initial character set), and an optional minimum,
       maximum, and/or exact length.  The default value for min is 1 (a
       minimum value < 1 is not valid); the default values for max and exact
       are 0, meaning no maximum or exact length restriction.
    """
    def __init__( self, initChars, bodyChars=None, min=1, max=0, exact=0, asKeyword=False ):
        super(Word,self).__init__()
        self.initCharsOrig = initChars
        self.initChars = _str2dict(initChars)
        if bodyChars :
            self.bodyCharsOrig = bodyChars
            self.bodyChars = _str2dict(bodyChars)
        else:
            self.bodyCharsOrig = initChars
            self.bodyChars = _str2dict(initChars)

        self.maxSpecified = max > 0

        if min < 1:
            raise ValueError("cannot specify a minimum length < 1; use Optional(Word()) if zero-length word is permitted")

        self.minLen = min

        if max > 0:
            self.maxLen = max
        else:
            self.maxLen = _MAX_INT

        if exact > 0:
            self.maxLen = exact
            self.minLen = exact

        self.name = _ustr(self)
        self.errmsg = "Expected " + self.name
        #self.myException.msg = self.errmsg
        self.mayIndexError = False
        self.asKeyword = asKeyword

        if ' ' not in self.initCharsOrig+self.bodyCharsOrig and (min==1 and max==0 and exact==0):
            if self.bodyCharsOrig == self.initCharsOrig:
                self.reString = "[%s]+" % _escapeRegexRangeChars(self.initCharsOrig)
            elif len(self.bodyCharsOrig) == 1:
                self.reString = "%s[%s]*" % \
                                      (re.escape(self.initCharsOrig),
                                      _escapeRegexRangeChars(self.bodyCharsOrig),)
            else:
                self.reString = "[%s][%s]*" % \
                                      (_escapeRegexRangeChars(self.initCharsOrig),
                                      _escapeRegexRangeChars(self.bodyCharsOrig),)
            if self.asKeyword:
                self.reString = r"\b"+self.reString+r"\b"
            try:
                self.re = re.compile( self.reString )
            except:
                self.re = None

    def parseImpl( self, instring, loc, doActions=True ):
        if self.re:
            result = self.re.match(instring,loc)
            if not result:
                exc = self.myException
                exc.loc = loc
                exc.pstr = instring
                raise exc

            loc = result.end()
            return loc,result.group()

        if not(instring[ loc ] in self.initChars):
            #~ raise ParseException( instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc
        start = loc
        loc += 1
        instrlen = len(instring)
        bodychars = self.bodyChars
        maxloc = start + self.maxLen
        maxloc = min( maxloc, instrlen )
        while loc < maxloc and instring[loc] in bodychars:
            loc += 1

        throwException = False
        if loc - start < self.minLen:
            throwException = True
        if self.maxSpecified and loc < instrlen and instring[loc] in bodychars:
            throwException = True
        if self.asKeyword:
            if (start>0 and instring[start-1] in bodychars) or (loc<instrlen and instring[loc] in bodychars):
                throwException = True

        if throwException:
            #~ raise ParseException( instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

        return loc, instring[start:loc]

    def __str__( self ):
        try:
            return super(Word,self).__str__()
        except:
            pass


        if self.strRepr is None:

            def charsAsStr(s):
                if len(s)>4:
                    return s[:4]+"..."
                else:
                    return s

            if ( self.initCharsOrig != self.bodyCharsOrig ):
                self.strRepr = "W:(%s,%s)" % ( charsAsStr(self.initCharsOrig), charsAsStr(self.bodyCharsOrig) )
            else:
                self.strRepr = "W:(%s)" % charsAsStr(self.initCharsOrig)

        return self.strRepr


class Regex(Token):
    """Token for matching strings that match a given regular expression.
       Defined with string specifying the regular expression in a form recognized by the inbuilt Python re module.
    """
    def __init__( self, pattern, flags=0):
        """The parameters pattern and flags are passed to the re.compile() function as-is. See the Python re module for an explanation of the acceptable patterns and flags."""
        super(Regex,self).__init__()

        if len(pattern) == 0:
            warnings.warn("null string passed to Regex; use Empty() instead",
                    SyntaxWarning, stacklevel=2)

        self.pattern = pattern
        self.flags = flags

        try:
            self.re = re.compile(self.pattern, self.flags)
            self.reString = self.pattern
        except sre_constants.error:
            warnings.warn("invalid pattern (%s) passed to Regex" % pattern,
                SyntaxWarning, stacklevel=2)
            raise

        self.name = _ustr(self)
        self.errmsg = "Expected " + self.name
        #self.myException.msg = self.errmsg
        self.mayIndexError = False
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        result = self.re.match(instring,loc)
        if not result:
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

        loc = result.end()
        d = result.groupdict()
        ret = ParseResults(result.group())
        if d:
            for k in d:
                ret[k] = d[k]
        return loc,ret

    def __str__( self ):
        try:
            return super(Regex,self).__str__()
        except:
            pass

        if self.strRepr is None:
            self.strRepr = "Re:(%s)" % repr(self.pattern)

        return self.strRepr


class QuotedString(Token):
    """Token for matching strings that are delimited by quoting characters.
    """
    def __init__( self, quoteChar, escChar=None, escQuote=None, multiline=False, unquoteResults=True, endQuoteChar=None):
        """
           Defined with the following parameters:
            - quoteChar - string of one or more characters defining the quote delimiting string
            - escChar - character to escape quotes, typically backslash (default=None)
            - escQuote - special quote sequence to escape an embedded quote string (such as SQL's "" to escape an embedded ") (default=None)
            - multiline - boolean indicating whether quotes can span multiple lines (default=False)
            - unquoteResults - boolean indicating whether the matched text should be unquoted (default=True)
            - endQuoteChar - string of one or more characters defining the end of the quote delimited string (default=None => same as quoteChar)
        """
        super(QuotedString,self).__init__()

        # remove white space from quote chars - wont work anyway
        quoteChar = quoteChar.strip()
        if len(quoteChar) == 0:
            warnings.warn("quoteChar cannot be the empty string",SyntaxWarning,stacklevel=2)
            raise SyntaxError()

        if endQuoteChar is None:
            endQuoteChar = quoteChar
        else:
            endQuoteChar = endQuoteChar.strip()
            if len(endQuoteChar) == 0:
                warnings.warn("endQuoteChar cannot be the empty string",SyntaxWarning,stacklevel=2)
                raise SyntaxError()

        self.quoteChar = quoteChar
        self.quoteCharLen = len(quoteChar)
        self.firstQuoteChar = quoteChar[0]
        self.endQuoteChar = endQuoteChar
        self.endQuoteCharLen = len(endQuoteChar)
        self.escChar = escChar
        self.escQuote = escQuote
        self.unquoteResults = unquoteResults

        if multiline:
            self.flags = re.MULTILINE | re.DOTALL
            self.pattern = r'%s(?:[^%s%s]' % \
                ( re.escape(self.quoteChar),
                  _escapeRegexRangeChars(self.endQuoteChar[0]),
                  (escChar is not None and _escapeRegexRangeChars(escChar) or '') )
        else:
            self.flags = 0
            self.pattern = r'%s(?:[^%s\n\r%s]' % \
                ( re.escape(self.quoteChar),
                  _escapeRegexRangeChars(self.endQuoteChar[0]),
                  (escChar is not None and _escapeRegexRangeChars(escChar) or '') )
        if len(self.endQuoteChar) > 1:
            self.pattern += (
                '|(?:' + ')|(?:'.join(["%s[^%s]" % (re.escape(self.endQuoteChar[:i]),
                                               _escapeRegexRangeChars(self.endQuoteChar[i]))
                                    for i in range(len(self.endQuoteChar)-1,0,-1)]) + ')'
                )
        if escQuote:
            self.pattern += (r'|(?:%s)' % re.escape(escQuote))
        if escChar:
            self.pattern += (r'|(?:%s.)' % re.escape(escChar))
            self.escCharReplacePattern = re.escape(self.escChar)+"(.)"
        self.pattern += (r')*%s' % re.escape(self.endQuoteChar))

        try:
            self.re = re.compile(self.pattern, self.flags)
            self.reString = self.pattern
        except sre_constants.error:
            warnings.warn("invalid pattern (%s) passed to Regex" % self.pattern,
                SyntaxWarning, stacklevel=2)
            raise

        self.name = _ustr(self)
        self.errmsg = "Expected " + self.name
        #self.myException.msg = self.errmsg
        self.mayIndexError = False
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        result = instring[loc] == self.firstQuoteChar and self.re.match(instring,loc) or None
        if not result:
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

        loc = result.end()
        ret = result.group()

        if self.unquoteResults:

            # strip off quotes
            ret = ret[self.quoteCharLen:-self.endQuoteCharLen]

            if isinstance(ret,basestring):
                # replace escaped characters
                if self.escChar:
                    ret = re.sub(self.escCharReplacePattern,"\g<1>",ret)

                # replace escaped quotes
                if self.escQuote:
                    ret = ret.replace(self.escQuote, self.endQuoteChar)

        return loc, ret

    def __str__( self ):
        try:
            return super(QuotedString,self).__str__()
        except:
            pass

        if self.strRepr is None:
            self.strRepr = "quoted string, starting with %s ending with %s" % (self.quoteChar, self.endQuoteChar)

        return self.strRepr


class CharsNotIn(Token):
    """Token for matching words composed of characters *not* in a given set.
       Defined with string containing all disallowed characters, and an optional
       minimum, maximum, and/or exact length.  The default value for min is 1 (a
       minimum value < 1 is not valid); the default values for max and exact
       are 0, meaning no maximum or exact length restriction.
    """
    def __init__( self, notChars, min=1, max=0, exact=0 ):
        super(CharsNotIn,self).__init__()
        self.skipWhitespace = False
        self.notChars = notChars

        if min < 1:
            raise ValueError("cannot specify a minimum length < 1; use Optional(CharsNotIn()) if zero-length char group is permitted")

        self.minLen = min

        if max > 0:
            self.maxLen = max
        else:
            self.maxLen = _MAX_INT

        if exact > 0:
            self.maxLen = exact
            self.minLen = exact

        self.name = _ustr(self)
        self.errmsg = "Expected " + self.name
        self.mayReturnEmpty = ( self.minLen == 0 )
        #self.myException.msg = self.errmsg
        self.mayIndexError = False

    def parseImpl( self, instring, loc, doActions=True ):
        if instring[loc] in self.notChars:
            #~ raise ParseException( instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

        start = loc
        loc += 1
        notchars = self.notChars
        maxlen = min( start+self.maxLen, len(instring) )
        while loc < maxlen and \
              (instring[loc] not in notchars):
            loc += 1

        if loc - start < self.minLen:
            #~ raise ParseException( instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

        return loc, instring[start:loc]

    def __str__( self ):
        try:
            return super(CharsNotIn, self).__str__()
        except:
            pass

        if self.strRepr is None:
            if len(self.notChars) > 4:
                self.strRepr = "!W:(%s...)" % self.notChars[:4]
            else:
                self.strRepr = "!W:(%s)" % self.notChars

        return self.strRepr

class White(Token):
    """Special matching class for matching whitespace.  Normally, whitespace is ignored
       by pyparsing grammars.  This class is included when some whitespace structures
       are significant.  Define with a string containing the whitespace characters to be
       matched; default is " \\t\\r\\n".  Also takes optional min, max, and exact arguments,
       as defined for the Word class."""
    whiteStrs = {
        " " : "<SPC>",
        "\t": "<TAB>",
        "\n": "<LF>",
        "\r": "<CR>",
        "\f": "<FF>",
        }
    def __init__(self, ws=" \t\r\n", min=1, max=0, exact=0):
        super(White,self).__init__()
        self.matchWhite = ws
        self.setWhitespaceChars( "".join([c for c in self.whiteChars if c not in self.matchWhite]) )
        #~ self.leaveWhitespace()
        self.name = ("".join([White.whiteStrs[c] for c in self.matchWhite]))
        self.mayReturnEmpty = True
        self.errmsg = "Expected " + self.name
        #self.myException.msg = self.errmsg

        self.minLen = min

        if max > 0:
            self.maxLen = max
        else:
            self.maxLen = _MAX_INT

        if exact > 0:
            self.maxLen = exact
            self.minLen = exact

    def parseImpl( self, instring, loc, doActions=True ):
        if not(instring[ loc ] in self.matchWhite):
            #~ raise ParseException( instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc
        start = loc
        loc += 1
        maxloc = start + self.maxLen
        maxloc = min( maxloc, len(instring) )
        while loc < maxloc and instring[loc] in self.matchWhite:
            loc += 1

        if loc - start < self.minLen:
            #~ raise ParseException( instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

        return loc, instring[start:loc]


class _PositionToken(Token):
    def __init__( self ):
        super(_PositionToken,self).__init__()
        self.name=self.__class__.__name__
        self.mayReturnEmpty = True
        self.mayIndexError = False

class GoToColumn(_PositionToken):
    """Token to advance to a specific column of input text; useful for tabular report scraping."""
    def __init__( self, colno ):
        super(GoToColumn,self).__init__()
        self.col = colno

    def preParse( self, instring, loc ):
        if col(loc,instring) != self.col:
            instrlen = len(instring)
            if self.ignoreExprs:
                loc = self._skipIgnorables( instring, loc )
            while loc < instrlen and instring[loc].isspace() and col( loc, instring ) != self.col :
                loc += 1
        return loc

    def parseImpl( self, instring, loc, doActions=True ):
        thiscol = col( loc, instring )
        if thiscol > self.col:
            raise ParseException( instring, loc, "Text not in expected column", self )
        newloc = loc + self.col - thiscol
        ret = instring[ loc: newloc ]
        return newloc, ret

class LineStart(_PositionToken):
    """Matches if current position is at the beginning of a line within the parse string"""
    def __init__( self ):
        super(LineStart,self).__init__()
        self.setWhitespaceChars( ParserElement.DEFAULT_WHITE_CHARS.replace("\n","") )
        self.errmsg = "Expected start of line"
        #self.myException.msg = self.errmsg

    def preParse( self, instring, loc ):
        preloc = super(LineStart,self).preParse(instring,loc)
        if instring[preloc] == "\n":
            loc += 1
        return loc

    def parseImpl( self, instring, loc, doActions=True ):
        if not( loc==0 or
            (loc == self.preParse( instring, 0 )) or
            (instring[loc-1] == "\n") ): #col(loc, instring) != 1:
            #~ raise ParseException( instring, loc, "Expected start of line" )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc
        return loc, []

class LineEnd(_PositionToken):
    """Matches if current position is at the end of a line within the parse string"""
    def __init__( self ):
        super(LineEnd,self).__init__()
        self.setWhitespaceChars( ParserElement.DEFAULT_WHITE_CHARS.replace("\n","") )
        self.errmsg = "Expected end of line"
        #self.myException.msg = self.errmsg

    def parseImpl( self, instring, loc, doActions=True ):
        if loc<len(instring):
            if instring[loc] == "\n":
                return loc+1, "\n"
            else:
                #~ raise ParseException( instring, loc, "Expected end of line" )
                exc = self.myException
                exc.loc = loc
                exc.pstr = instring
                raise exc
        elif loc == len(instring):
            return loc+1, []
        else:
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

class StringStart(_PositionToken):
    """Matches if current position is at the beginning of the parse string"""
    def __init__( self ):
        super(StringStart,self).__init__()
        self.errmsg = "Expected start of text"
        #self.myException.msg = self.errmsg

    def parseImpl( self, instring, loc, doActions=True ):
        if loc != 0:
            # see if entire string up to here is just whitespace and ignoreables
            if loc != self.preParse( instring, 0 ):
                #~ raise ParseException( instring, loc, "Expected start of text" )
                exc = self.myException
                exc.loc = loc
                exc.pstr = instring
                raise exc
        return loc, []

class StringEnd(_PositionToken):
    """Matches if current position is at the end of the parse string"""
    def __init__( self ):
        super(StringEnd,self).__init__()
        self.errmsg = "Expected end of text"
        #self.myException.msg = self.errmsg

    def parseImpl( self, instring, loc, doActions=True ):
        if loc < len(instring):
            #~ raise ParseException( instring, loc, "Expected end of text" )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc
        elif loc == len(instring):
            return loc+1, []
        elif loc > len(instring):
            return loc, []
        else:
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

class WordStart(_PositionToken):
    """Matches if the current position is at the beginning of a Word, and
       is not preceded by any character in a given set of wordChars
       (default=printables). To emulate the \b behavior of regular expressions,
       use WordStart(alphanums). WordStart will also match at the beginning of
       the string being parsed, or at the beginning of a line.
    """
    def __init__(self, wordChars = printables):
        super(WordStart,self).__init__()
        self.wordChars = _str2dict(wordChars)
        self.errmsg = "Not at the start of a word"

    def parseImpl(self, instring, loc, doActions=True ):
        if loc != 0:
            if (instring[loc-1] in self.wordChars or
                instring[loc] not in self.wordChars):
                exc = self.myException
                exc.loc = loc
                exc.pstr = instring
                raise exc
        return loc, []

class WordEnd(_PositionToken):
    """Matches if the current position is at the end of a Word, and
       is not followed by any character in a given set of wordChars
       (default=printables). To emulate the \b behavior of regular expressions,
       use WordEnd(alphanums). WordEnd will also match at the end of
       the string being parsed, or at the end of a line.
    """
    def __init__(self, wordChars = printables):
        super(WordEnd,self).__init__()
        self.wordChars = _str2dict(wordChars)
        self.skipWhitespace = False
        self.errmsg = "Not at the end of a word"

    def parseImpl(self, instring, loc, doActions=True ):
        instrlen = len(instring)
        if instrlen>0 and loc<instrlen:
            if (instring[loc] in self.wordChars or
                instring[loc-1] not in self.wordChars):
                #~ raise ParseException( instring, loc, "Expected end of word" )
                exc = self.myException
                exc.loc = loc
                exc.pstr = instring
                raise exc
        return loc, []


class ParseExpression(ParserElement):
    """Abstract subclass of ParserElement, for combining and post-processing parsed tokens."""
    def __init__( self, exprs, savelist = False ):
        super(ParseExpression,self).__init__(savelist)
        if isinstance( exprs, list ):
            self.exprs = exprs
        elif isinstance( exprs, basestring ):
            self.exprs = [ Literal( exprs ) ]
        else:
            try:
                self.exprs = list( exprs )
            except TypeError:
                self.exprs = [ exprs ]
        self.callPreparse = False

    def __getitem__( self, i ):
        return self.exprs[i]

    def append( self, other ):
        self.exprs.append( other )
        self.strRepr = None
        return self

    def leaveWhitespace( self ):
        """Extends leaveWhitespace defined in base class, and also invokes leaveWhitespace on
           all contained expressions."""
        self.skipWhitespace = False
        self.exprs = [ e.copy() for e in self.exprs ]
        for e in self.exprs:
            e.leaveWhitespace()
        return self

    def ignore( self, other ):
        if isinstance( other, Suppress ):
            if other not in self.ignoreExprs:
                super( ParseExpression, self).ignore( other )
                for e in self.exprs:
                    e.ignore( self.ignoreExprs[-1] )
        else:
            super( ParseExpression, self).ignore( other )
            for e in self.exprs:
                e.ignore( self.ignoreExprs[-1] )
        return self

    def __str__( self ):
        try:
            return super(ParseExpression,self).__str__()
        except:
            pass

        if self.strRepr is None:
            self.strRepr = "%s:(%s)" % ( self.__class__.__name__, _ustr(self.exprs) )
        return self.strRepr

    def streamline( self ):
        super(ParseExpression,self).streamline()

        for e in self.exprs:
            e.streamline()

        # collapse nested And's of the form And( And( And( a,b), c), d) to And( a,b,c,d )
        # but only if there are no parse actions or resultsNames on the nested And's
        # (likewise for Or's and MatchFirst's)
        if ( len(self.exprs) == 2 ):
            other = self.exprs[0]
            if ( isinstance( other, self.__class__ ) and
                  not(other.parseAction) and
                  other.resultsName is None and
                  not other.debug ):
                self.exprs = other.exprs[:] + [ self.exprs[1] ]
                self.strRepr = None
                self.mayReturnEmpty |= other.mayReturnEmpty
                self.mayIndexError  |= other.mayIndexError

            other = self.exprs[-1]
            if ( isinstance( other, self.__class__ ) and
                  not(other.parseAction) and
                  other.resultsName is None and
                  not other.debug ):
                self.exprs = self.exprs[:-1] + other.exprs[:]
                self.strRepr = None
                self.mayReturnEmpty |= other.mayReturnEmpty
                self.mayIndexError  |= other.mayIndexError

        return self

    def setResultsName( self, name, listAllMatches=False ):
        ret = super(ParseExpression,self).setResultsName(name,listAllMatches)
        return ret

    def validate( self, validateTrace=[] ):
        tmp = validateTrace[:]+[self]
        for e in self.exprs:
            e.validate(tmp)
        self.checkRecursion( [] )

class And(ParseExpression):
    """Requires all given ParseExpressions to be found in the given order.
       Expressions may be separated by whitespace.
       May be constructed using the '+' operator.
    """

    class _ErrorStop(Empty):
        def __init__(self, *args, **kwargs):
            super(Empty,self).__init__(*args, **kwargs)
            self.leaveWhitespace()

    def __init__( self, exprs, savelist = True ):
        super(And,self).__init__(exprs, savelist)
        self.mayReturnEmpty = True
        for e in self.exprs:
            if not e.mayReturnEmpty:
                self.mayReturnEmpty = False
                break
        self.setWhitespaceChars( exprs[0].whiteChars )
        self.skipWhitespace = exprs[0].skipWhitespace
        self.callPreparse = True

    def parseImpl( self, instring, loc, doActions=True ):
        # pass False as last arg to _parse for first element, since we already
        # pre-parsed the string as part of our And pre-parsing
        loc, resultlist = self.exprs[0]._parse( instring, loc, doActions, callPreParse=False )
        errorStop = False
        for e in self.exprs[1:]:
            if isinstance(e, And._ErrorStop):
                errorStop = True
                continue
            if errorStop:
                try:
                    loc, exprtokens = e._parse( instring, loc, doActions )
                except ParseSyntaxException:
                    raise
                except ParseBaseException, pe:
                    raise ParseSyntaxException(pe)
                except IndexError, ie:
                    raise ParseSyntaxException( ParseException(instring, len(instring), self.errmsg, self) )
            else:
                loc, exprtokens = e._parse( instring, loc, doActions )
            if exprtokens or exprtokens.keys():
                resultlist += exprtokens
        return loc, resultlist

    def __iadd__(self, other ):
        if isinstance( other, basestring ):
            other = Literal( other )
        return self.append( other ) #And( [ self, other ] )

    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )
            if not e.mayReturnEmpty:
                break

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + " ".join( [ _ustr(e) for e in self.exprs ] ) + "}"

        return self.strRepr


class Or(ParseExpression):
    """Requires that at least one ParseExpression is found.
       If two expressions match, the expression that matches the longest string will be used.
       May be constructed using the '^' operator.
    """
    def __init__( self, exprs, savelist = False ):
        super(Or,self).__init__(exprs, savelist)
        self.mayReturnEmpty = False
        for e in self.exprs:
            if e.mayReturnEmpty:
                self.mayReturnEmpty = True
                break

    def parseImpl( self, instring, loc, doActions=True ):
        maxExcLoc = -1
        maxMatchLoc = -1
        maxException = None
        for e in self.exprs:
            try:
                loc2 = e.tryParse( instring, loc )
            except ParseException, err:
                if err.loc > maxExcLoc:
                    maxException = err
                    maxExcLoc = err.loc
            except IndexError:
                if len(instring) > maxExcLoc:
                    maxException = ParseException(instring,len(instring),e.errmsg,self)
                    maxExcLoc = len(instring)
            else:
                if loc2 > maxMatchLoc:
                    maxMatchLoc = loc2
                    maxMatchExp = e

        if maxMatchLoc < 0:
            if maxException is not None:
                raise maxException
            else:
                raise ParseException(instring, loc, "no defined alternatives to match", self)

        return maxMatchExp._parse( instring, loc, doActions )

    def __ixor__(self, other ):
        if isinstance( other, basestring ):
            other = Literal( other )
        return self.append( other ) #Or( [ self, other ] )

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + " ^ ".join( [ _ustr(e) for e in self.exprs ] ) + "}"

        return self.strRepr

    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )


class MatchFirst(ParseExpression):
    """Requires that at least one ParseExpression is found.
       If two expressions match, the first one listed is the one that will match.
       May be constructed using the '|' operator.
    """
    def __init__( self, exprs, savelist = False ):
        super(MatchFirst,self).__init__(exprs, savelist)
        if exprs:
            self.mayReturnEmpty = False
            for e in self.exprs:
                if e.mayReturnEmpty:
                    self.mayReturnEmpty = True
                    break
        else:
            self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        maxExcLoc = -1
        maxException = None
        for e in self.exprs:
            try:
                ret = e._parse( instring, loc, doActions )
                return ret
            except ParseException, err:
                if err.loc > maxExcLoc:
                    maxException = err
                    maxExcLoc = err.loc
            except IndexError:
                if len(instring) > maxExcLoc:
                    maxException = ParseException(instring,len(instring),e.errmsg,self)
                    maxExcLoc = len(instring)

        # only got here if no expression matched, raise exception for match that made it the furthest
        else:
            if maxException is not None:
                raise maxException
            else:
                raise ParseException(instring, loc, "no defined alternatives to match", self)

    def __ior__(self, other ):
        if isinstance( other, basestring ):
            other = Literal( other )
        return self.append( other ) #MatchFirst( [ self, other ] )

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + " | ".join( [ _ustr(e) for e in self.exprs ] ) + "}"

        return self.strRepr

    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )


class Each(ParseExpression):
    """Requires all given ParseExpressions to be found, but in any order.
       Expressions may be separated by whitespace.
       May be constructed using the '&' operator.
    """
    def __init__( self, exprs, savelist = True ):
        super(Each,self).__init__(exprs, savelist)
        self.mayReturnEmpty = True
        for e in self.exprs:
            if not e.mayReturnEmpty:
                self.mayReturnEmpty = False
                break
        self.skipWhitespace = True
        self.initExprGroups = True

    def parseImpl( self, instring, loc, doActions=True ):
        if self.initExprGroups:
            self.optionals = [ e.expr for e in self.exprs if isinstance(e,Optional) ]
            self.multioptionals = [ e.expr for e in self.exprs if isinstance(e,ZeroOrMore) ]
            self.multirequired = [ e.expr for e in self.exprs if isinstance(e,OneOrMore) ]
            self.required = [ e for e in self.exprs if not isinstance(e,(Optional,ZeroOrMore,OneOrMore)) ]
            self.required += self.multirequired
            self.initExprGroups = False
        tmpLoc = loc
        tmpReqd = self.required[:]
        tmpOpt  = self.optionals[:]
        matchOrder = []

        keepMatching = True
        while keepMatching:
            tmpExprs = tmpReqd + tmpOpt + self.multioptionals + self.multirequired
            failed = []
            for e in tmpExprs:
                try:
                    tmpLoc = e.tryParse( instring, tmpLoc )
                except ParseException:
                    failed.append(e)
                else:
                    matchOrder.append(e)
                    if e in tmpReqd:
                        tmpReqd.remove(e)
                    elif e in tmpOpt:
                        tmpOpt.remove(e)
            if len(failed) == len(tmpExprs):
                keepMatching = False

        if tmpReqd:
            missing = ", ".join( [ _ustr(e) for e in tmpReqd ] )
            raise ParseException(instring,loc,"Missing one or more required elements (%s)" % missing )

        # add any unmatched Optionals, in case they have default values defined
        matchOrder += list(e for e in self.exprs if isinstance(e,Optional) and e.expr in tmpOpt)

        resultlist = []
        for e in matchOrder:
            loc,results = e._parse(instring,loc,doActions)
            resultlist.append(results)

        finalResults = ParseResults([])
        for r in resultlist:
            dups = {}
            for k in r.keys():
                if k in finalResults.keys():
                    tmp = ParseResults(finalResults[k])
                    tmp += ParseResults(r[k])
                    dups[k] = tmp
            finalResults += ParseResults(r)
            for k,v in dups.items():
                finalResults[k] = v
        return loc, finalResults

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + " & ".join( [ _ustr(e) for e in self.exprs ] ) + "}"

        return self.strRepr

    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )


class ParseElementEnhance(ParserElement):
    """Abstract subclass of ParserElement, for combining and post-processing parsed tokens."""
    def __init__( self, expr, savelist=False ):
        super(ParseElementEnhance,self).__init__(savelist)
        if isinstance( expr, basestring ):
            expr = Literal(expr)
        self.expr = expr
        self.strRepr = None
        if expr is not None:
            self.mayIndexError = expr.mayIndexError
            self.mayReturnEmpty = expr.mayReturnEmpty
            self.setWhitespaceChars( expr.whiteChars )
            self.skipWhitespace = expr.skipWhitespace
            self.saveAsList = expr.saveAsList
            self.callPreparse = expr.callPreparse
            self.ignoreExprs.extend(expr.ignoreExprs)

    def parseImpl( self, instring, loc, doActions=True ):
        if self.expr is not None:
            return self.expr._parse( instring, loc, doActions, callPreParse=False )
        else:
            raise ParseException("",loc,self.errmsg,self)

    def leaveWhitespace( self ):
        self.skipWhitespace = False
        self.expr = self.expr.copy()
        if self.expr is not None:
            self.expr.leaveWhitespace()
        return self

    def ignore( self, other ):
        if isinstance( other, Suppress ):
            if other not in self.ignoreExprs:
                super( ParseElementEnhance, self).ignore( other )
                if self.expr is not None:
                    self.expr.ignore( self.ignoreExprs[-1] )
        else:
            super( ParseElementEnhance, self).ignore( other )
            if self.expr is not None:
                self.expr.ignore( self.ignoreExprs[-1] )
        return self

    def streamline( self ):
        super(ParseElementEnhance,self).streamline()
        if self.expr is not None:
            self.expr.streamline()
        return self

    def checkRecursion( self, parseElementList ):
        if self in parseElementList:
            raise RecursiveGrammarException( parseElementList+[self] )
        subRecCheckList = parseElementList[:] + [ self ]
        if self.expr is not None:
            self.expr.checkRecursion( subRecCheckList )

    def validate( self, validateTrace=[] ):
        tmp = validateTrace[:]+[self]
        if self.expr is not None:
            self.expr.validate(tmp)
        self.checkRecursion( [] )

    def __str__( self ):
        try:
            return super(ParseElementEnhance,self).__str__()
        except:
            pass

        if self.strRepr is None and self.expr is not None:
            self.strRepr = "%s:(%s)" % ( self.__class__.__name__, _ustr(self.expr) )
        return self.strRepr


class FollowedBy(ParseElementEnhance):
    """Lookahead matching of the given parse expression.  FollowedBy
    does *not* advance the parsing position within the input string, it only
    verifies that the specified parse expression matches at the current
    position.  FollowedBy always returns a null token list."""
    def __init__( self, expr ):
        super(FollowedBy,self).__init__(expr)
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        self.expr.tryParse( instring, loc )
        return loc, []


class NotAny(ParseElementEnhance):
    """Lookahead to disallow matching with the given parse expression.  NotAny
    does *not* advance the parsing position within the input string, it only
    verifies that the specified parse expression does *not* match at the current
    position.  Also, NotAny does *not* skip over leading whitespace. NotAny
    always returns a null token list.  May be constructed using the '~' operator."""
    def __init__( self, expr ):
        super(NotAny,self).__init__(expr)
        #~ self.leaveWhitespace()
        self.skipWhitespace = False  # do NOT use self.leaveWhitespace(), don't want to propagate to exprs
        self.mayReturnEmpty = True
        self.errmsg = "Found unwanted token, "+_ustr(self.expr)
        #self.myException = ParseException("",0,self.errmsg,self)

    def parseImpl( self, instring, loc, doActions=True ):
        try:
            self.expr.tryParse( instring, loc )
        except (ParseException,IndexError):
            pass
        else:
            #~ raise ParseException(instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc
        return loc, []

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "~{" + _ustr(self.expr) + "}"

        return self.strRepr


class ZeroOrMore(ParseElementEnhance):
    """Optional repetition of zero or more of the given expression."""
    def __init__( self, expr ):
        super(ZeroOrMore,self).__init__(expr)
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        tokens = []
        try:
            loc, tokens = self.expr._parse( instring, loc, doActions, callPreParse=False )
            hasIgnoreExprs = ( len(self.ignoreExprs) > 0 )
            while 1:
                if hasIgnoreExprs:
                    preloc = self._skipIgnorables( instring, loc )
                else:
                    preloc = loc
                loc, tmptokens = self.expr._parse( instring, preloc, doActions )
                if tmptokens or tmptokens.keys():
                    tokens += tmptokens
        except (ParseException,IndexError):
            pass

        return loc, tokens

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "[" + _ustr(self.expr) + "]..."

        return self.strRepr

    def setResultsName( self, name, listAllMatches=False ):
        ret = super(ZeroOrMore,self).setResultsName(name,listAllMatches)
        ret.saveAsList = True
        return ret


class OneOrMore(ParseElementEnhance):
    """Repetition of one or more of the given expression."""
    def parseImpl( self, instring, loc, doActions=True ):
        # must be at least one
        loc, tokens = self.expr._parse( instring, loc, doActions, callPreParse=False )
        try:
            hasIgnoreExprs = ( len(self.ignoreExprs) > 0 )
            while 1:
                if hasIgnoreExprs:
                    preloc = self._skipIgnorables( instring, loc )
                else:
                    preloc = loc
                loc, tmptokens = self.expr._parse( instring, preloc, doActions )
                if tmptokens or tmptokens.keys():
                    tokens += tmptokens
        except (ParseException,IndexError):
            pass

        return loc, tokens

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + _ustr(self.expr) + "}..."

        return self.strRepr

    def setResultsName( self, name, listAllMatches=False ):
        ret = super(OneOrMore,self).setResultsName(name,listAllMatches)
        ret.saveAsList = True
        return ret

class _NullToken(object):
    def __bool__(self):
        return False
    __nonzero__ = __bool__
    def __str__(self):
        return ""

_optionalNotMatched = _NullToken()
class Optional(ParseElementEnhance):
    """Optional matching of the given expression.
       A default return string can also be specified, if the optional expression
       is not found.
    """
    def __init__( self, exprs, default=_optionalNotMatched ):
        super(Optional,self).__init__( exprs, savelist=False )
        self.defaultValue = default
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        try:
            loc, tokens = self.expr._parse( instring, loc, doActions, callPreParse=False )
        except (ParseException,IndexError):
            if self.defaultValue is not _optionalNotMatched:
                if self.expr.resultsName:
                    tokens = ParseResults([ self.defaultValue ])
                    tokens[self.expr.resultsName] = self.defaultValue
                else:
                    tokens = [ self.defaultValue ]
            else:
                tokens = []
        return loc, tokens

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "[" + _ustr(self.expr) + "]"

        return self.strRepr


class SkipTo(ParseElementEnhance):
    """Token for skipping over all undefined text until the matched expression is found.
       If include is set to true, the matched expression is also parsed (the skipped text
       and matched expression are returned as a 2-element list).  The ignore
       argument is used to define grammars (typically quoted strings and comments) that
       might contain false matches.
    """
    def __init__( self, other, include=False, ignore=None, failOn=None ):
        super( SkipTo, self ).__init__( other )
        self.ignoreExpr = ignore
        self.mayReturnEmpty = True
        self.mayIndexError = False
        self.includeMatch = include
        self.asList = False
        if failOn is not None and isinstance(failOn, basestring):
            self.failOn = Literal(failOn)
        else:
            self.failOn = failOn
        self.errmsg = "No match found for "+_ustr(self.expr)
        #self.myException = ParseException("",0,self.errmsg,self)

    def parseImpl( self, instring, loc, doActions=True ):
        startLoc = loc
        instrlen = len(instring)
        expr = self.expr
        failParse = False
        while loc <= instrlen:
            try:
                if self.failOn:
                    try:
                        self.failOn.tryParse(instring, loc)
                    except ParseBaseException:
                        pass
                    else:
                        failParse = True
                        raise ParseException(instring, loc, "Found expression " + str(self.failOn))
                    failParse = False
                if self.ignoreExpr is not None:
                    while 1:
                        try:
                            loc = self.ignoreExpr.tryParse(instring,loc)
                            print "found ignoreExpr, advance to", loc
                        except ParseBaseException:
                            break
                expr._parse( instring, loc, doActions=False, callPreParse=False )
                skipText = instring[startLoc:loc]
                if self.includeMatch:
                    loc,mat = expr._parse(instring,loc,doActions,callPreParse=False)
                    if mat:
                        skipRes = ParseResults( skipText )
                        skipRes += mat
                        return loc, [ skipRes ]
                    else:
                        return loc, [ skipText ]
                else:
                    return loc, [ skipText ]
            except (ParseException,IndexError):
                if failParse:
                    raise
                else:
                    loc += 1
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc

class Forward(ParseElementEnhance):
    """Forward declaration of an expression to be defined later -
       used for recursive grammars, such as algebraic infix notation.
       When the expression is known, it is assigned to the Forward variable using the '<<' operator.

       Note: take care when assigning to Forward not to overlook precedence of operators.
       Specifically, '|' has a lower precedence than '<<', so that::
          fwdExpr << a | b | c
       will actually be evaluated as::
          (fwdExpr << a) | b | c
       thereby leaving b and c out as parseable alternatives.  It is recommended that you
       explicitly group the values inserted into the Forward::
          fwdExpr << (a | b | c)
    """
    def __init__( self, other=None ):
        super(Forward,self).__init__( other, savelist=False )

    def __lshift__( self, other ):
        if isinstance( other, basestring ):
            other = Literal(other)
        self.expr = other
        self.mayReturnEmpty = other.mayReturnEmpty
        self.strRepr = None
        self.mayIndexError = self.expr.mayIndexError
        self.mayReturnEmpty = self.expr.mayReturnEmpty
        self.setWhitespaceChars( self.expr.whiteChars )
        self.skipWhitespace = self.expr.skipWhitespace
        self.saveAsList = self.expr.saveAsList
        self.ignoreExprs.extend(self.expr.ignoreExprs)
        return None

    def leaveWhitespace( self ):
        self.skipWhitespace = False
        return self

    def streamline( self ):
        if not self.streamlined:
            self.streamlined = True
            if self.expr is not None:
                self.expr.streamline()
        return self

    def validate( self, validateTrace=[] ):
        if self not in validateTrace:
            tmp = validateTrace[:]+[self]
            if self.expr is not None:
                self.expr.validate(tmp)
        self.checkRecursion([])

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        self._revertClass = self.__class__
        self.__class__ = _ForwardNoRecurse
        try:
            if self.expr is not None:
                retString = _ustr(self.expr)
            else:
                retString = "None"
        finally:
            self.__class__ = self._revertClass
        return self.__class__.__name__ + ": " + retString

    def copy(self):
        if self.expr is not None:
            return super(Forward,self).copy()
        else:
            ret = Forward()
            ret << self
            return ret

class _ForwardNoRecurse(Forward):
    def __str__( self ):
        return "..."

class TokenConverter(ParseElementEnhance):
    """Abstract subclass of ParseExpression, for converting parsed results."""
    def __init__( self, expr, savelist=False ):
        super(TokenConverter,self).__init__( expr )#, savelist )
        self.saveAsList = False

class Upcase(TokenConverter):
    """Converter to upper case all matching tokens."""
    def __init__(self, *args):
        super(Upcase,self).__init__(*args)
        warnings.warn("Upcase class is deprecated, use upcaseTokens parse action instead",
                       DeprecationWarning,stacklevel=2)

    def postParse( self, instring, loc, tokenlist ):
        return list(map( string.upper, tokenlist ))


class Combine(TokenConverter):
    """Converter to concatenate all matching tokens to a single string.
       By default, the matching patterns must also be contiguous in the input string;
       this can be disabled by specifying 'adjacent=False' in the constructor.
    """
    def __init__( self, expr, joinString="", adjacent=True ):
        super(Combine,self).__init__( expr )
        # suppress whitespace-stripping in contained parse expressions, but re-enable it on the Combine itself
        if adjacent:
            self.leaveWhitespace()
        self.adjacent = adjacent
        self.skipWhitespace = True
        self.joinString = joinString

    def ignore( self, other ):
        if self.adjacent:
            ParserElement.ignore(self, other)
        else:
            super( Combine, self).ignore( other )
        return self

    def postParse( self, instring, loc, tokenlist ):
        retToks = tokenlist.copy()
        del retToks[:]
        retToks += ParseResults([ "".join(tokenlist._asStringList(self.joinString)) ], modal=self.modalResults)

        if self.resultsName and len(retToks.keys())>0:
            return [ retToks ]
        else:
            return retToks

class Group(TokenConverter):
    """Converter to return the matched tokens as a list - useful for returning tokens of ZeroOrMore and OneOrMore expressions."""
    def __init__( self, expr ):
        super(Group,self).__init__( expr )
        self.saveAsList = True

    def postParse( self, instring, loc, tokenlist ):
        return [ tokenlist ]

class Dict(TokenConverter):
    """Converter to return a repetitive expression as a list, but also as a dictionary.
       Each element can also be referenced using the first token in the expression as its key.
       Useful for tabular report scraping when the first column can be used as a item key.
    """
    def __init__( self, exprs ):
        super(Dict,self).__init__( exprs )
        self.saveAsList = True

    def postParse( self, instring, loc, tokenlist ):
        for i,tok in enumerate(tokenlist):
            if len(tok) == 0:
                continue
            ikey = tok[0]
            if isinstance(ikey,int):
                ikey = _ustr(tok[0]).strip()
            if len(tok)==1:
                tokenlist[ikey] = _ParseResultsWithOffset("",i)
            elif len(tok)==2 and not isinstance(tok[1],ParseResults):
                tokenlist[ikey] = _ParseResultsWithOffset(tok[1],i)
            else:
                dictvalue = tok.copy() #ParseResults(i)
                del dictvalue[0]
                if len(dictvalue)!= 1 or (isinstance(dictvalue,ParseResults) and dictvalue.keys()):
                    tokenlist[ikey] = _ParseResultsWithOffset(dictvalue,i)
                else:
                    tokenlist[ikey] = _ParseResultsWithOffset(dictvalue[0],i)

        if self.resultsName:
            return [ tokenlist ]
        else:
            return tokenlist


class Suppress(TokenConverter):
    """Converter for ignoring the results of a parsed expression."""
    def postParse( self, instring, loc, tokenlist ):
        return []

    def suppress( self ):
        return self


class OnlyOnce(object):
    """Wrapper for parse actions, to ensure they are only called once."""
    def __init__(self, methodCall):
        self.callable = ParserElement._normalizeParseActionArgs(methodCall)
        self.called = False
    def __call__(self,s,l,t):
        if not self.called:
            results = self.callable(s,l,t)
            self.called = True
            return results
        raise ParseException(s,l,"")
    def reset(self):
        self.called = False

def traceParseAction(f):
    """Decorator for debugging parse actions."""
    f = ParserElement._normalizeParseActionArgs(f)
    def z(*paArgs):
        thisFunc = f.func_name
        s,l,t = paArgs[-3:]
        if len(paArgs)>3:
            thisFunc = paArgs[0].__class__.__name__ + '.' + thisFunc
        sys.stderr.write( ">>entering %s(line: '%s', %d, %s)\n" % (thisFunc,line(l,s),l,t) )
        try:
            ret = f(*paArgs)
        except Exception, exc:
            sys.stderr.write( "<<leaving %s (exception: %s)\n" % (thisFunc,exc) )
            raise
        sys.stderr.write( "<<leaving %s (ret: %s)\n" % (thisFunc,ret) )
        return ret
    try:
        z.__name__ = f.__name__
    except AttributeError:
        pass
    return z

#
# global helpers
#
def delimitedList( expr, delim=",", combine=False ):
    """Helper to define a delimited list of expressions - the delimiter defaults to ','.
       By default, the list elements and delimiters can have intervening whitespace, and
       comments, but this can be overridden by passing 'combine=True' in the constructor.
       If combine is set to True, the matching tokens are returned as a single token
       string, with the delimiters included; otherwise, the matching tokens are returned
       as a list of tokens, with the delimiters suppressed.
    """
    dlName = _ustr(expr)+" ["+_ustr(delim)+" "+_ustr(expr)+"]..."
    if combine:
        return Combine( expr + ZeroOrMore( delim + expr ) ).setName(dlName)
    else:
        return ( expr + ZeroOrMore( Suppress( delim ) + expr ) ).setName(dlName)

def countedArray( expr ):
    """Helper to define a counted list of expressions.
       This helper defines a pattern of the form::
           integer expr expr expr...
       where the leading integer tells how many expr expressions follow.
       The matched tokens returns the array of expr tokens as a list - the leading count token is suppressed.
    """
    arrayExpr = Forward()
    def countFieldParseAction(s,l,t):
        n = int(t[0])
        arrayExpr << (n and Group(And([expr]*n)) or Group(empty))
        return []
    return ( Word(nums).setName("arrayLen").setParseAction(countFieldParseAction, callDuringTry=True) + arrayExpr )

def _flatten(L):
    if type(L) is not list: return [L]
    if L == []: return L
    return _flatten(L[0]) + _flatten(L[1:])

def matchPreviousLiteral(expr):
    """Helper to define an expression that is indirectly defined from
       the tokens matched in a previous expression, that is, it looks
       for a 'repeat' of a previous expression.  For example::
           first = Word(nums)
           second = matchPreviousLiteral(first)
           matchExpr = first + ":" + second
       will match "1:1", but not "1:2".  Because this matches a
       previous literal, will also match the leading "1:1" in "1:10".
       If this is not desired, use matchPreviousExpr.
       Do *not* use with packrat parsing enabled.
    """
    rep = Forward()
    def copyTokenToRepeater(s,l,t):
        if t:
            if len(t) == 1:
                rep << t[0]
            else:
                # flatten t tokens
                tflat = _flatten(t.asList())
                rep << And( [ Literal(tt) for tt in tflat ] )
        else:
            rep << Empty()
    expr.addParseAction(copyTokenToRepeater, callDuringTry=True)
    return rep

def matchPreviousExpr(expr):
    """Helper to define an expression that is indirectly defined from
       the tokens matched in a previous expression, that is, it looks
       for a 'repeat' of a previous expression.  For example::
           first = Word(nums)
           second = matchPreviousExpr(first)
           matchExpr = first + ":" + second
       will match "1:1", but not "1:2".  Because this matches by
       expressions, will *not* match the leading "1:1" in "1:10";
       the expressions are evaluated first, and then compared, so
       "1" is compared with "10".
       Do *not* use with packrat parsing enabled.
    """
    rep = Forward()
    e2 = expr.copy()
    rep << e2
    def copyTokenToRepeater(s,l,t):
        matchTokens = _flatten(t.asList())
        def mustMatchTheseTokens(s,l,t):
            theseTokens = _flatten(t.asList())
            if  theseTokens != matchTokens:
                raise ParseException("",0,"")
        rep.setParseAction( mustMatchTheseTokens, callDuringTry=True )
    expr.addParseAction(copyTokenToRepeater, callDuringTry=True)
    return rep

def _escapeRegexRangeChars(s):
    #~  escape these chars: ^-]
    for c in r"\^-]":
        s = s.replace(c,_bslash+c)
    s = s.replace("\n",r"\n")
    s = s.replace("\t",r"\t")
    return _ustr(s)

def oneOf( strs, caseless=False, useRegex=True ):
    """Helper to quickly define a set of alternative Literals, and makes sure to do
       longest-first testing when there is a conflict, regardless of the input order,
       but returns a MatchFirst for best performance.

       Parameters:
        - strs - a string of space-delimited literals, or a list of string literals
        - caseless - (default=False) - treat all literals as caseless
        - useRegex - (default=True) - as an optimization, will generate a Regex
          object; otherwise, will generate a MatchFirst object (if caseless=True, or
          if creating a Regex raises an exception)
    """
    if caseless:
        isequal = ( lambda a,b: a.upper() == b.upper() )
        masks = ( lambda a,b: b.upper().startswith(a.upper()) )
        parseElementClass = CaselessLiteral
    else:
        isequal = ( lambda a,b: a == b )
        masks = ( lambda a,b: b.startswith(a) )
        parseElementClass = Literal

    if isinstance(strs,(list,tuple)):
        symbols = list(strs[:])
    elif isinstance(strs,basestring):
        symbols = strs.split()
    else:
        warnings.warn("Invalid argument to oneOf, expected string or list",
                SyntaxWarning, stacklevel=2)

    i = 0
    while i < len(symbols)-1:
        cur = symbols[i]
        for j,other in enumerate(symbols[i+1:]):
            if ( isequal(other, cur) ):
                del symbols[i+j+1]
                break
            elif ( masks(cur, other) ):
                del symbols[i+j+1]
                symbols.insert(i,other)
                cur = other
                break
        else:
            i += 1

    if not caseless and useRegex:
        #~ print (strs,"->", "|".join( [ _escapeRegexChars(sym) for sym in symbols] ))
        try:
            if len(symbols)==len("".join(symbols)):
                return Regex( "[%s]" % "".join( [ _escapeRegexRangeChars(sym) for sym in symbols] ) )
            else:
                return Regex( "|".join( [ re.escape(sym) for sym in symbols] ) )
        except:
            warnings.warn("Exception creating Regex for oneOf, building MatchFirst",
                    SyntaxWarning, stacklevel=2)


    # last resort, just use MatchFirst
    return MatchFirst( [ parseElementClass(sym) for sym in symbols ] )

def dictOf( key, value ):
    """Helper to easily and clearly define a dictionary by specifying the respective patterns
       for the key and value.  Takes care of defining the Dict, ZeroOrMore, and Group tokens
       in the proper order.  The key pattern can include delimiting markers or punctuation,
       as long as they are suppressed, thereby leaving the significant key text.  The value
       pattern can include named results, so that the Dict results can include named token
       fields.
    """
    return Dict( ZeroOrMore( Group ( key + value ) ) )

def originalTextFor(expr, asString=True):
    """Helper to return the original, untokenized text for a given expression.  Useful to
       restore the parsed fields of an HTML start tag into the raw tag text itself, or to
       revert separate tokens with intervening whitespace back to the original matching
       input text. Simpler to use than the parse action keepOriginalText, and does not
       require the inspect module to chase up the call stack.  By default, returns a 
       string containing the original parsed text.  
       
       If the optional asString argument is passed as False, then the return value is a 
       ParseResults containing any results names that were originally matched, and a 
       single token containing the original matched text from the input string.  So if 
       the expression passed to originalTextFor contains expressions with defined
       results names, you must set asString to False if you want to preserve those
       results name values."""
    locMarker = Empty().setParseAction(lambda s,loc,t: loc)
    matchExpr = locMarker("_original_start") + expr + locMarker("_original_end")
    if asString:
        extractText = lambda s,l,t: s[t._original_start:t._original_end]
    else:
        def extractText(s,l,t):
            del t[:]
            t.insert(0, s[t._original_start:t._original_end])
            del t["_original_start"]
            del t["_original_end"]
    matchExpr.setParseAction(extractText)
    return matchExpr
    
# convenience constants for positional expressions
empty       = Empty().setName("empty")
lineStart   = LineStart().setName("lineStart")
lineEnd     = LineEnd().setName("lineEnd")
stringStart = StringStart().setName("stringStart")
stringEnd   = StringEnd().setName("stringEnd")

_escapedPunc = Word( _bslash, r"\[]-*.$+^?()~ ", exact=2 ).setParseAction(lambda s,l,t:t[0][1])
_printables_less_backslash = "".join([ c for c in printables if c not in  r"\]" ])
_escapedHexChar = Combine( Suppress(_bslash + "0x") + Word(hexnums) ).setParseAction(lambda s,l,t:unichr(int(t[0],16)))
_escapedOctChar = Combine( Suppress(_bslash) + Word("0","01234567") ).setParseAction(lambda s,l,t:unichr(int(t[0],8)))
_singleChar = _escapedPunc | _escapedHexChar | _escapedOctChar | Word(_printables_less_backslash,exact=1)
_charRange = Group(_singleChar + Suppress("-") + _singleChar)
_reBracketExpr = Literal("[") + Optional("^").setResultsName("negate") + Group( OneOrMore( _charRange | _singleChar ) ).setResultsName("body") + "]"

_expanded = lambda p: (isinstance(p,ParseResults) and ''.join([ unichr(c) for c in range(ord(p[0]),ord(p[1])+1) ]) or p)

def srange(s):
    r"""Helper to easily define string ranges for use in Word construction.  Borrows
       syntax from regexp '[]' string range definitions::
          srange("[0-9]")   -> "0123456789"
          srange("[a-z]")   -> "abcdefghijklmnopqrstuvwxyz"
          srange("[a-z$_]") -> "abcdefghijklmnopqrstuvwxyz$_"
       The input string must be enclosed in []'s, and the returned string is the expanded
       character set joined into a single string.
       The values enclosed in the []'s may be::
          a single character
          an escaped character with a leading backslash (such as \- or \])
          an escaped hex character with a leading '\0x' (\0x21, which is a '!' character)
          an escaped octal character with a leading '\0' (\041, which is a '!' character)
          a range of any of the above, separated by a dash ('a-z', etc.)
          any combination of the above ('aeiouy', 'a-zA-Z0-9_$', etc.)
    """
    try:
        return "".join([_expanded(part) for part in _reBracketExpr.parseString(s).body])
    except:
        return ""

def matchOnlyAtCol(n):
    """Helper method for defining parse actions that require matching at a specific
       column in the input text.
    """
    def verifyCol(strg,locn,toks):
        if col(locn,strg) != n:
            raise ParseException(strg,locn,"matched token not at column %d" % n)
    return verifyCol

def replaceWith(replStr):
    """Helper method for common parse actions that simply return a literal value.  Especially
       useful when used with transformString().
    """
    def _replFunc(*args):
        return [replStr]
    return _replFunc

def removeQuotes(s,l,t):
    """Helper parse action for removing quotation marks from parsed quoted strings.
       To use, add this parse action to quoted string using::
         quotedString.setParseAction( removeQuotes )
    """
    return t[0][1:-1]

def upcaseTokens(s,l,t):
    """Helper parse action to convert tokens to upper case."""
    return [ tt.upper() for tt in map(_ustr,t) ]

def downcaseTokens(s,l,t):
    """Helper parse action to convert tokens to lower case."""
    return [ tt.lower() for tt in map(_ustr,t) ]

def keepOriginalText(s,startLoc,t):
    """Helper parse action to preserve original parsed text,
       overriding any nested parse actions."""
    try:
        endloc = getTokensEndLoc()
    except ParseException:
        raise ParseFatalException("incorrect usage of keepOriginalText - may only be called as a parse action")
    del t[:]
    t += ParseResults(s[startLoc:endloc])
    return t

def getTokensEndLoc():
    """Method to be called from within a parse action to determine the end
       location of the parsed tokens."""
    import inspect
    fstack = inspect.stack()
    try:
        # search up the stack (through intervening argument normalizers) for correct calling routine
        for f in fstack[2:]:
            if f[3] == "_parseNoCache":
                endloc = f[0].f_locals["loc"]
                return endloc
        else:
            raise ParseFatalException("incorrect usage of getTokensEndLoc - may only be called from within a parse action")
    finally:
        del fstack

def _makeTags(tagStr, xml):
    """Internal helper to construct opening and closing tag expressions, given a tag name"""
    if isinstance(tagStr,basestring):
        resname = tagStr
        tagStr = Keyword(tagStr, caseless=not xml)
    else:
        resname = tagStr.name

    tagAttrName = Word(alphas,alphanums+"_-:")
    if (xml):
        tagAttrValue = dblQuotedString.copy().setParseAction( removeQuotes )
        openTag = Suppress("<") + tagStr + \
                Dict(ZeroOrMore(Group( tagAttrName + Suppress("=") + tagAttrValue ))) + \
                Optional("/",default=[False]).setResultsName("empty").setParseAction(lambda s,l,t:t[0]=='/') + Suppress(">")
    else:
        printablesLessRAbrack = "".join( [ c for c in printables if c not in ">" ] )
        tagAttrValue = quotedString.copy().setParseAction( removeQuotes ) | Word(printablesLessRAbrack)
        openTag = Suppress("<") + tagStr + \
                Dict(ZeroOrMore(Group( tagAttrName.setParseAction(downcaseTokens) + \
                Optional( Suppress("=") + tagAttrValue ) ))) + \
                Optional("/",default=[False]).setResultsName("empty").setParseAction(lambda s,l,t:t[0]=='/') + Suppress(">")
    closeTag = Combine(_L("</") + tagStr + ">")

    openTag = openTag.setResultsName("start"+"".join(resname.replace(":"," ").title().split())).setName("<%s>" % tagStr)
    closeTag = closeTag.setResultsName("end"+"".join(resname.replace(":"," ").title().split())).setName("</%s>" % tagStr)

    return openTag, closeTag

def makeHTMLTags(tagStr):
    """Helper to construct opening and closing tag expressions for HTML, given a tag name"""
    return _makeTags( tagStr, False )

def makeXMLTags(tagStr):
    """Helper to construct opening and closing tag expressions for XML, given a tag name"""
    return _makeTags( tagStr, True )

def withAttribute(*args,**attrDict):
    """Helper to create a validating parse action to be used with start tags created
       with makeXMLTags or makeHTMLTags. Use withAttribute to qualify a starting tag
       with a required attribute value, to avoid false matches on common tags such as
       <TD> or <DIV>.

       Call withAttribute with a series of attribute names and values. Specify the list
       of filter attributes names and values as:
        - keyword arguments, as in (class="Customer",align="right"), or
        - a list of name-value tuples, as in ( ("ns1:class", "Customer"), ("ns2:align","right") )
       For attribute names with a namespace prefix, you must use the second form.  Attribute
       names are matched insensitive to upper/lower case.

       To verify that the attribute exists, but without specifying a value, pass
       withAttribute.ANY_VALUE as the value.
       """
    if args:
        attrs = args[:]
    else:
        attrs = attrDict.items()
    attrs = [(k,v) for k,v in attrs]
    def pa(s,l,tokens):
        for attrName,attrValue in attrs:
            if attrName not in tokens:
                raise ParseException(s,l,"no matching attribute " + attrName)
            if attrValue != withAttribute.ANY_VALUE and tokens[attrName] != attrValue:
                raise ParseException(s,l,"attribute '%s' has value '%s', must be '%s'" %
                                            (attrName, tokens[attrName], attrValue))
    return pa
withAttribute.ANY_VALUE = object()

opAssoc = _Constants()
opAssoc.LEFT = object()
opAssoc.RIGHT = object()

def operatorPrecedence( baseExpr, opList ):
    """Helper method for constructing grammars of expressions made up of
       operators working in a precedence hierarchy.  Operators may be unary or
       binary, left- or right-associative.  Parse actions can also be attached
       to operator expressions.

       Parameters:
        - baseExpr - expression representing the most basic element for the nested
        - opList - list of tuples, one for each operator precedence level in the
          expression grammar; each tuple is of the form
          (opExpr, numTerms, rightLeftAssoc, parseAction), where:
           - opExpr is the pyparsing expression for the operator;
              may also be a string, which will be converted to a Literal;
              if numTerms is 3, opExpr is a tuple of two expressions, for the
              two operators separating the 3 terms
           - numTerms is the number of terms for this operator (must
              be 1, 2, or 3)
           - rightLeftAssoc is the indicator whether the operator is
              right or left associative, using the pyparsing-defined
              constants opAssoc.RIGHT and opAssoc.LEFT.
           - parseAction is the parse action to be associated with
              expressions matching this operator expression (the
              parse action tuple member may be omitted)
    """
    ret = Forward()
    lastExpr = baseExpr | ( Suppress('(') + ret + Suppress(')') )
    for i,operDef in enumerate(opList):
        opExpr,arity,rightLeftAssoc,pa = (operDef + (None,))[:4]
        if arity == 3:
            if opExpr is None or len(opExpr) != 2:
                raise ValueError("if numterms=3, opExpr must be a tuple or list of two expressions")
            opExpr1, opExpr2 = opExpr
        thisExpr = Forward()#.setName("expr%d" % i)
        if rightLeftAssoc == opAssoc.LEFT:
            if arity == 1:
                matchExpr = FollowedBy(lastExpr + opExpr) + Group( lastExpr + OneOrMore( opExpr ) )
            elif arity == 2:
                if opExpr is not None:
                    matchExpr = FollowedBy(lastExpr + opExpr + lastExpr) + Group( lastExpr + OneOrMore( opExpr + lastExpr ) )
                else:
                    matchExpr = FollowedBy(lastExpr+lastExpr) + Group( lastExpr + OneOrMore(lastExpr) )
            elif arity == 3:
                matchExpr = FollowedBy(lastExpr + opExpr1 + lastExpr + opExpr2 + lastExpr) + \
                            Group( lastExpr + opExpr1 + lastExpr + opExpr2 + lastExpr )
            else:
                raise ValueError("operator must be unary (1), binary (2), or ternary (3)")
        elif rightLeftAssoc == opAssoc.RIGHT:
            if arity == 1:
                # try to avoid LR with this extra test
                if not isinstance(opExpr, Optional):
                    opExpr = Optional(opExpr)
                matchExpr = FollowedBy(opExpr.expr + thisExpr) + Group( opExpr + thisExpr )
            elif arity == 2:
                if opExpr is not None:
                    matchExpr = FollowedBy(lastExpr + opExpr + thisExpr) + Group( lastExpr + OneOrMore( opExpr + thisExpr ) )
                else:
                    matchExpr = FollowedBy(lastExpr + thisExpr) + Group( lastExpr + OneOrMore( thisExpr ) )
            elif arity == 3:
                matchExpr = FollowedBy(lastExpr + opExpr1 + thisExpr + opExpr2 + thisExpr) + \
                            Group( lastExpr + opExpr1 + thisExpr + opExpr2 + thisExpr )
            else:
                raise ValueError("operator must be unary (1), binary (2), or ternary (3)")
        else:
            raise ValueError("operator must indicate right or left associativity")
        if pa:
            matchExpr.setParseAction( pa )
        thisExpr << ( matchExpr | lastExpr )
        lastExpr = thisExpr
    ret << lastExpr
    return ret

dblQuotedString = Regex(r'"(?:[^"\n\r\\]|(?:"")|(?:\\x[0-9a-fA-F]+)|(?:\\.))*"').setName("string enclosed in double quotes")
sglQuotedString = Regex(r"'(?:[^'\n\r\\]|(?:'')|(?:\\x[0-9a-fA-F]+)|(?:\\.))*'").setName("string enclosed in single quotes")
quotedString = Regex(r'''(?:"(?:[^"\n\r\\]|(?:"")|(?:\\x[0-9a-fA-F]+)|(?:\\.))*")|(?:'(?:[^'\n\r\\]|(?:'')|(?:\\x[0-9a-fA-F]+)|(?:\\.))*')''').setName("quotedString using single or double quotes")
unicodeString = Combine(_L('u') + quotedString.copy())

def nestedExpr(opener="(", closer=")", content=None, ignoreExpr=quotedString):
    """Helper method for defining nested lists enclosed in opening and closing
       delimiters ("(" and ")" are the default).

       Parameters:
        - opener - opening character for a nested list (default="("); can also be a pyparsing expression
        - closer - closing character for a nested list (default=")"); can also be a pyparsing expression
        - content - expression for items within the nested lists (default=None)
        - ignoreExpr - expression for ignoring opening and closing delimiters (default=quotedString)

       If an expression is not provided for the content argument, the nested
       expression will capture all whitespace-delimited content between delimiters
       as a list of separate values.

       Use the ignoreExpr argument to define expressions that may contain
       opening or closing characters that should not be treated as opening
       or closing characters for nesting, such as quotedString or a comment
       expression.  Specify multiple expressions using an Or or MatchFirst.
       The default is quotedString, but if no expressions are to be ignored,
       then pass None for this argument.
    """
    if opener == closer:
        raise ValueError("opening and closing strings cannot be the same")
    if content is None:
        if isinstance(opener,basestring) and isinstance(closer,basestring):
            if len(opener) == 1 and len(closer)==1:
                if ignoreExpr is not None:
                    content = (Combine(OneOrMore(~ignoreExpr +
                                    CharsNotIn(opener+closer+ParserElement.DEFAULT_WHITE_CHARS,exact=1))
                                ).setParseAction(lambda t:t[0].strip()))
                else:
                    content = (empty+CharsNotIn(opener+closer+ParserElement.DEFAULT_WHITE_CHARS
                                ).setParseAction(lambda t:t[0].strip()))
            else:
                if ignoreExpr is not None:
                    content = (Combine(OneOrMore(~ignoreExpr + 
                                    ~Literal(opener) + ~Literal(closer) +
                                    CharsNotIn(ParserElement.DEFAULT_WHITE_CHARS,exact=1))
                                ).setParseAction(lambda t:t[0].strip()))
                else:
                    content = (Combine(OneOrMore(~Literal(opener) + ~Literal(closer) +
                                    CharsNotIn(ParserElement.DEFAULT_WHITE_CHARS,exact=1))
                                ).setParseAction(lambda t:t[0].strip()))
        else:
            raise ValueError("opening and closing arguments must be strings if no content expression is given")
    ret = Forward()
    if ignoreExpr is not None:
        ret << Group( Suppress(opener) + ZeroOrMore( ignoreExpr | ret | content ) + Suppress(closer) )
    else:
        ret << Group( Suppress(opener) + ZeroOrMore( ret | content )  + Suppress(closer) )
    return ret

def indentedBlock(blockStatementExpr, indentStack, indent=True):
    """Helper method for defining space-delimited indentation blocks, such as
       those used to define block statements in Python source code.

       Parameters:
        - blockStatementExpr - expression defining syntax of statement that
            is repeated within the indented block
        - indentStack - list created by caller to manage indentation stack
            (multiple statementWithIndentedBlock expressions within a single grammar
            should share a common indentStack)
        - indent - boolean indicating whether block must be indented beyond the
            the current level; set to False for block of left-most statements
            (default=True)

       A valid block must contain at least one blockStatement.
    """
    def checkPeerIndent(s,l,t):
        if l >= len(s): return
        curCol = col(l,s)
        if curCol != indentStack[-1]:
            if curCol > indentStack[-1]:
                raise ParseFatalException(s,l,"illegal nesting")
            raise ParseException(s,l,"not a peer entry")

    def checkSubIndent(s,l,t):
        curCol = col(l,s)
        if curCol > indentStack[-1]:
            indentStack.append( curCol )
        else:
            raise ParseException(s,l,"not a subentry")

    def checkUnindent(s,l,t):
        if l >= len(s): return
        curCol = col(l,s)
        if not(indentStack and curCol < indentStack[-1] and curCol <= indentStack[-2]):
            raise ParseException(s,l,"not an unindent")
        indentStack.pop()

    NL = OneOrMore(LineEnd().setWhitespaceChars("\t ").suppress())
    INDENT = Empty() + Empty().setParseAction(checkSubIndent)
    PEER   = Empty().setParseAction(checkPeerIndent)
    UNDENT = Empty().setParseAction(checkUnindent)
    if indent:
        smExpr = Group( Optional(NL) +
            FollowedBy(blockStatementExpr) +
            INDENT + (OneOrMore( PEER + Group(blockStatementExpr) + Optional(NL) )) + UNDENT)
    else:
        smExpr = Group( Optional(NL) +
            (OneOrMore( PEER + Group(blockStatementExpr) + Optional(NL) )) )
    blockStatementExpr.ignore(_bslash + LineEnd())
    return smExpr

alphas8bit = srange(r"[\0xc0-\0xd6\0xd8-\0xf6\0xf8-\0xff]")
punc8bit = srange(r"[\0xa1-\0xbf\0xd7\0xf7]")

anyOpenTag,anyCloseTag = makeHTMLTags(Word(alphas,alphanums+"_:"))
commonHTMLEntity = Combine(_L("&") + oneOf("gt lt amp nbsp quot").setResultsName("entity") +";").streamline()
_htmlEntityMap = dict(zip("gt lt amp nbsp quot".split(),'><& "'))
replaceHTMLEntity = lambda t : t.entity in _htmlEntityMap and _htmlEntityMap[t.entity] or None

# it's easy to get these comment structures wrong - they're very common, so may as well make them available
cStyleComment = Regex(r"/\*(?:[^*]*\*+)+?/").setName("C style comment")

htmlComment = Regex(r"<!--[\s\S]*?-->")
restOfLine = Regex(r".*").leaveWhitespace()
dblSlashComment = Regex(r"\/\/(\\\n|.)*").setName("// comment")
cppStyleComment = Regex(r"/(?:\*(?:[^*]*\*+)+?/|/[^\n]*(?:\n[^\n]*)*?(?:(?<!\\)|\Z))").setName("C++ style comment")

javaStyleComment = cppStyleComment
pythonStyleComment = Regex(r"#.*").setName("Python style comment")
_noncomma = "".join( [ c for c in printables if c != "," ] )
_commasepitem = Combine(OneOrMore(Word(_noncomma) +
                                  Optional( Word(" \t") +
                                            ~Literal(",") + ~LineEnd() ) ) ).streamline().setName("commaItem")
commaSeparatedList = delimitedList( Optional( quotedString | _commasepitem, default="") ).setName("commaSeparatedList")


if __name__ == "__main__":

    def test( teststring ):
        try:
            tokens = simpleSQL.parseString( teststring )
            tokenlist = tokens.asList()
            print (teststring + "->"   + str(tokenlist))
            print ("tokens = "         + str(tokens))
            print ("tokens.columns = " + str(tokens.columns))
            print ("tokens.tables = "  + str(tokens.tables))
            print (tokens.asXML("SQL",True))
        except ParseBaseException,err:
            print (teststring + "->")
            print (err.line)
            print (" "*(err.column-1) + "^")
            print (err)
        print()

    selectToken    = CaselessLiteral( "select" )
    fromToken      = CaselessLiteral( "from" )

    ident          = Word( alphas, alphanums + "_$" )
    columnName     = delimitedList( ident, ".", combine=True ).setParseAction( upcaseTokens )
    columnNameList = Group( delimitedList( columnName ) )#.setName("columns")
    tableName      = delimitedList( ident, ".", combine=True ).setParseAction( upcaseTokens )
    tableNameList  = Group( delimitedList( tableName ) )#.setName("tables")
    simpleSQL      = ( selectToken + \
                     ( '*' | columnNameList ).setResultsName( "columns" ) + \
                     fromToken + \
                     tableNameList.setResultsName( "tables" ) )

    test( "SELECT * from XYZZY, ABC" )
    test( "select * from SYS.XYZZY" )
    test( "Select A from Sys.dual" )
    test( "Select AA,BB,CC from Sys.dual" )
    test( "Select A, B, C from Sys.dual" )
    test( "Select A, B, C from Sys.dual" )
    test( "Xelect A, B, C from Sys.dual" )
    test( "Select A, B, C frox Sys.dual" )
    test( "Select" )
    test( "Select ^^^ frox Sys.dual" )
    test( "Select A, B, C from Sys.dual, Table2   " )

########NEW FILE########
__FILENAME__ = ASCommandResponse
#!/usr/bin/env python
'''
@author: David Shaw, david.shaw.aw@gmail.com

Inspired by EAS Inspector for Fiddler
https://easinspectorforfiddler.codeplex.com

----- The MIT License (MIT) ----- 
Filename: ASCommandResponse.py
Copyright (c) 2014, David P. Shaw

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
'''
from ASWBXML import ASWBXML
import logging

class ASCommandResponse:

	def __init__(self, response):
		self.wbxmlBody = response
		try:
			if ( len(response) > 0):
				self.xmlString = self.decodeWBXML(self.wbxmlBody)
			else:
				logging.error("Empty WBXML body passed")
		except Exception as e:
			logging.error("Error: {0}".format(e.message))
			self.xmlString = None

	def getWBXMLBytes(self):
		return self.wbxmlBytes
	
	def getXMLString(self):
		return self.xmlString
	
	def decodeWBXML(self, body):
		self.instance = ASWBXML()
		self.instance.loadBytes(body)
		return self.instance.getXml()

if __name__ == "__main__":
	import os	
	logging.basicConfig(level=logging.INFO)

	projectDir = os.path.dirname(os.path.realpath("."))
	samplesDir = os.path.join(projectDir, "Samples/")
	listOfSamples = os.listdir(samplesDir)

	for filename in listOfSamples:
		byteWBXML = open(samplesDir + os.sep + filename, "rb").read()
		
		logging.info("-"*100)
		logging.info(filename)
		logging.info("-"*100)
		instance = ASCommandResponse(byteWBXML)
		logging.info(instance.xmlString)
		
########NEW FILE########
__FILENAME__ = ASWBXML
#!/usr/bin/env python
'''
@author: David Shaw, david.shaw.aw@gmail.com

Inspired by EAS Inspector for Fiddler
https://easinspectorforfiddler.codeplex.com

----- The MIT License (MIT) ----- 
Filename: ASWBXML.py
Copyright (c) 2014, David P. Shaw

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
'''
import xml.dom.minidom
import logging

from ASWBXMLCodePage import ASWBXMLCodePage
from ASWBXMLByteQueue import ASWBXMLByteQueue
from GlobalTokens import GlobalTokens
from InvalidDataException import InvalidDataException

class ASWBXML:
	versionByte = 0x03
	publicIdentifierByte = 0x01
	characterSetByte = 0x6A
	stringTableLengthByte = 0x00
	
	def __init__(self):
		
		# empty on init
		self.xmlDoc = xml.dom.minidom.Document()
		self.currentCodePage = 0
		self.defaultCodePage = -1
		
		# Load up code pages
		# Currently there are 25 code pages as per MS-ASWBXML
		self.codePages = []

		# region Code Page Initialization
		# Code Page 0: AirSync
		# region AirSync Code Page
		page = ASWBXMLCodePage()
		page.namespace = "AirSync:"
		page.xmlns = "airsync"

		page.addToken(0x05, "Sync")
		page.addToken(0x06, "Responses")
		page.addToken(0x07, "Add")
		page.addToken(0x08, "Change")
		page.addToken(0x09, "Delete")
		page.addToken(0x0A, "Fetch")
		page.addToken(0x0B, "SyncKey")
		page.addToken(0x0C, "ClientId")
		page.addToken(0x0D, "ServerId")
		page.addToken(0x0E, "Status")
		page.addToken(0x0F, "Collection")
		page.addToken(0x10, "Class")
		page.addToken(0x12, "CollectionId")
		page.addToken(0x13, "GetChanges")
		page.addToken(0x14, "MoreAvailable")
		page.addToken(0x15, "WindowSize")
		page.addToken(0x16, "Commands")
		page.addToken(0x17, "Options")
		page.addToken(0x18, "FilterType")
		page.addToken(0x1B, "Conflict")
		page.addToken(0x1C, "Collections")
		page.addToken(0x1D, "ApplicationData")
		page.addToken(0x1E, "DeletesAsMoves")
		page.addToken(0x20, "Supported")
		page.addToken(0x21, "SoftDelete")
		page.addToken(0x22, "MIMESupport")
		page.addToken(0x23, "MIMETruncation")
		page.addToken(0x24, "Wait")
		page.addToken(0x25, "Limit")
		page.addToken(0x26, "Partial")
		page.addToken(0x27, "ConversationMode")
		page.addToken(0x28, "MaxItems")
		page.addToken(0x29, "HeartbeatInterval")
		self.codePages.append(page)
		# endregion

		# Code Page 1: Contacts
		# region Contacts Code Page
		page = ASWBXMLCodePage()
		page.namespace = "Contacts:"
		page.xmlns = "contacts"

		page.addToken(0x05, "Anniversary")
		page.addToken(0x06, "AssistantName")
		page.addToken(0x07, "AssistantTelephoneNumber")
		page.addToken(0x08, "Birthday")
		page.addToken(0x0C, "Business2PhoneNumber")
		page.addToken(0x0D, "BusinessCity")
		page.addToken(0x0E, "BusinessCountry")
		page.addToken(0x0F, "BusinessPostalCode")
		page.addToken(0x10, "BusinessState")
		page.addToken(0x11, "BusinessStreet")
		page.addToken(0x12, "BusinessFaxNumber")
		page.addToken(0x13, "BusinessPhoneNumber")
		page.addToken(0x14, "CarPhoneNumber")
		page.addToken(0x15, "Categories")
		page.addToken(0x16, "Category")
		page.addToken(0x17, "Children")
		page.addToken(0x18, "Child")
		page.addToken(0x19, "CompanyName")
		page.addToken(0x1A, "Department")
		page.addToken(0x1B, "Email1Address")
		page.addToken(0x1C, "Email2Address")
		page.addToken(0x1D, "Email3Address")
		page.addToken(0x1E, "FileAs")
		page.addToken(0x1F, "FirstName")
		page.addToken(0x20, "Home2PhoneNumber")
		page.addToken(0x21, "HomeCity")
		page.addToken(0x22, "HomeCountry")
		page.addToken(0x23, "HomePostalCode")
		page.addToken(0x24, "HomeState")
		page.addToken(0x25, "HomeStreet")
		page.addToken(0x26, "HomeFaxNumber")
		page.addToken(0x27, "HomePhoneNumber")
		page.addToken(0x28, "JobTitle")
		page.addToken(0x29, "LastName")
		page.addToken(0x2A, "MiddleName")
		page.addToken(0x2B, "MobilePhoneNumber")
		page.addToken(0x2C, "OfficeLocation")
		page.addToken(0x2D, "OtherCity")
		page.addToken(0x2E, "OtherCountry")
		page.addToken(0x2F, "OtherPostalCode")
		page.addToken(0x30, "OtherState")
		page.addToken(0x31, "OtherStreet")
		page.addToken(0x32, "PagerNumber")
		page.addToken(0x33, "RadioPhoneNumber")
		page.addToken(0x34, "Spouse")
		page.addToken(0x35, "Suffix")
		page.addToken(0x36, "Title")
		page.addToken(0x37, "Webpage")
		page.addToken(0x38, "YomiCompanyName")
		page.addToken(0x39, "YomiFirstName")
		page.addToken(0x3A, "YomiLastName")
		page.addToken(0x3C, "Picture")
		page.addToken(0x3D, "Alias")
		page.addToken(0x3E, "WeightedRank")
		self.codePages.append(page)
		# endregion

		# Code Page 2: Email
		# region Email Code Page
		page = ASWBXMLCodePage()
		page.namespace = "Email:"
		page.xmlns = "email"

		page.addToken(0x0F, "DateReceived")
		page.addToken(0x11, "DisplayTo")
		page.addToken(0x12, "Importance")
		page.addToken(0x13, "MessageClass")
		page.addToken(0x14, "Subject")
		page.addToken(0x15, "Read")
		page.addToken(0x16, "To")
		page.addToken(0x17, "CC")
		page.addToken(0x18, "From")
		page.addToken(0x19, "ReplyTo")
		page.addToken(0x1A, "AllDayEvent")
		page.addToken(0x1B, "Categories")
		page.addToken(0x1C, "Category")
		page.addToken(0x1D, "DTStamp")
		page.addToken(0x1E, "EndTime")
		page.addToken(0x1F, "InstanceType")
		page.addToken(0x20, "BusyStatus")
		page.addToken(0x21, "Location")
		page.addToken(0x22, "MeetingRequest")
		page.addToken(0x23, "Organizer")
		page.addToken(0x24, "RecurrenceId")
		page.addToken(0x25, "Reminder")
		page.addToken(0x26, "ResponseRequested")
		page.addToken(0x27, "Recurrences")
		page.addToken(0x28, "Recurrence")
		page.addToken(0x29, "Recurrence_Type")
		page.addToken(0x2A, "Recurrence_Until")
		page.addToken(0x2B, "Recurrence_Occurrences")
		page.addToken(0x2C, "Recurrence_Interval")
		page.addToken(0x2D, "Recurrence_DayOfWeek")
		page.addToken(0x2E, "Recurrence_DayOfMonth")
		page.addToken(0x2F, "Recurrence_WeekOfMonth")
		page.addToken(0x30, "Recurrence_MonthOfYear")
		page.addToken(0x31, "StartTime")
		page.addToken(0x32, "Sensitivity")
		page.addToken(0x33, "TimeZone")
		page.addToken(0x34, "GlobalObjId")
		page.addToken(0x35, "ThreadTopic")
		page.addToken(0x39, "InternetCPID")
		page.addToken(0x3A, "Flag")
		page.addToken(0x3B, "FlagStatus")
		page.addToken(0x3C, "ContentClass")
		page.addToken(0x3D, "FlagType")
		page.addToken(0x3E, "CompleteTime")
		page.addToken(0x3F, "DisallowNewTimeProposal")
		self.codePages.append(page)
		# endregion

		# Code Page 3: AirNotify - retired
		# region AirNotify Code Page
		page = ASWBXMLCodePage()
		page.namespace = ""
		page.xmlns = ""
		self.codePages.append(page)
		# endregion

		# Code Page 4: Calendar
		# region Calendar Code Page
		page = ASWBXMLCodePage()
		page.namespace = "Calendar:"
		page.xmlns = "calendar"

		page.addToken(0x05, "TimeZone")
		page.addToken(0x06, "AllDayEvent")
		page.addToken(0x07, "Attendees")
		page.addToken(0x08, "Attendee")
		page.addToken(0x09, "Attendee_Email")
		page.addToken(0x0A, "Attendee_Name")
		page.addToken(0x0D, "BusyStatus")
		page.addToken(0x0E, "Categories")
		page.addToken(0x0F, "Category")
		page.addToken(0x11, "DTStamp")
		page.addToken(0x12, "EndTime")
		page.addToken(0x13, "Exception")
		page.addToken(0x14, "Exceptions")
		page.addToken(0x15, "Exception_Deleted")
		page.addToken(0x16, "Exception_StartTime")
		page.addToken(0x17, "Location")
		page.addToken(0x18, "MeetingStatus")
		page.addToken(0x19, "Organizer_Email")
		page.addToken(0x1A, "Organizer_Name")
		page.addToken(0x1B, "Recurrence")
		page.addToken(0x1C, "Recurrence_Type")
		page.addToken(0x1D, "Recurrence_Until")
		page.addToken(0x1E, "Recurrence_Occurrences")
		page.addToken(0x1F, "Recurrence_Interval")
		page.addToken(0x20, "Recurrence_DayOfWeek")
		page.addToken(0x21, "Recurrence_DayOfMonth")
		page.addToken(0x22, "Recurrence_WeekOfMonth")
		page.addToken(0x23, "Recurrence_MonthOfYear")
		page.addToken(0x24, "Reminder")
		page.addToken(0x25, "Sensitivity")
		page.addToken(0x26, "Subject")
		page.addToken(0x27, "StartTime")
		page.addToken(0x28, "UID")
		page.addToken(0x29, "Attendee_Status")
		page.addToken(0x2A, "Attendee_Type")
		page.addToken(0x33, "DisallowNewTimeProposal")
		page.addToken(0x34, "ResponseRequested")
		page.addToken(0x35, "AppointmentReplyTime")
		page.addToken(0x36, "ResponseType")
		page.addToken(0x37, "CalendarType")
		page.addToken(0x38, "IsLeapMonth")
		page.addToken(0x39, "FirstDayOfWeek")
		page.addToken(0x3A, "OnlineMeetingConfLink")
		page.addToken(0x3B, "OnlineMeetingExternalLink")
		self.codePages.append(page)
		# endregion

		# Code Page 5: Move
		# region Move Code Page
		page = ASWBXMLCodePage()
		page.namespace = "Move:"
		page.xmlns = "move"

		page.addToken(0x05, "MoveItems")
		page.addToken(0x06, "Move")
		page.addToken(0x07, "SrcMsgId")
		page.addToken(0x08, "SrcFldId")
		page.addToken(0x09, "DstFldId")
		page.addToken(0x0A, "Response")
		page.addToken(0x0B, "Status")
		page.addToken(0x0C, "DstMsgId")
		self.codePages.append(page)
		# endregion

		# Code Page 6: ItemEstimate
		# region ItemEstimate Code Page
		page = ASWBXMLCodePage()
		page.namespace = "GetItemEstimate:"
		page.xmlns = "getitemestimate"

		page.addToken(0x05, "GetItemEstimate")
		page.addToken(0x06, "Version")
		page.addToken(0x07, "Collections")
		page.addToken(0x08, "Collection")
		page.addToken(0x09, "Class")
		page.addToken(0x0A, "CollectionId")
		page.addToken(0x0B, "DateTime")
		page.addToken(0x0C, "Estimate")
		page.addToken(0x0D, "Response")
		page.addToken(0x0E, "Status")
		self.codePages.append(page)
		# endregion

		# Code Page 7: FolderHierarchy
		# region FolderHierarchy Code Page
		page = ASWBXMLCodePage()
		page.namespace = "FolderHierarchy:"
		page.xmlns = "folderhierarchy"

		page.addToken(0x07, "DisplayName")
		page.addToken(0x08, "ServerId")
		page.addToken(0x09, "ParentId")
		page.addToken(0x0A, "Type")
		page.addToken(0x0C, "Status")
		page.addToken(0x0E, "Changes")
		page.addToken(0x0F, "Add")
		page.addToken(0x10, "Delete")
		page.addToken(0x11, "Update")
		page.addToken(0x12, "SyncKey")
		page.addToken(0x13, "FolderCreate")
		page.addToken(0x14, "FolderDelete")
		page.addToken(0x15, "FolderUpdate")
		page.addToken(0x16, "FolderSync")
		page.addToken(0x17, "Count")

		self.codePages.append(page)
		# endregion

		# Code Page 8: MeetingResponse
		# region MeetingResponse Code Page
		page = ASWBXMLCodePage()
		page.namespace = "MeetingResponse:"
		page.xmlns = "meetingresponse"

		page.addToken(0x05, "CalendarId")
		page.addToken(0x06, "CollectionId")
		page.addToken(0x07, "MeetingResponse")
		page.addToken(0x08, "RequestId")
		page.addToken(0x09, "Request")
		page.addToken(0x0A, "Result")
		page.addToken(0x0B, "Status")
		page.addToken(0x0C, "UserResponse")
		page.addToken(0x0E, "InstanceId")
		self.codePages.append(page)
		# endregion

		# Code Page 9: Tasks
		# region Tasks Code Page
		page = ASWBXMLCodePage()
		page.namespace = "Tasks:"
		page.xmlns = "tasks"

		page.addToken(0x08, "Categories")
		page.addToken(0x09, "Category")
		page.addToken(0x0A, "Complete")
		page.addToken(0x0B, "DateCompleted")
		page.addToken(0x0C, "DueDate")
		page.addToken(0x0D, "UTCDueDate")
		page.addToken(0x0E, "Importance")
		page.addToken(0x0F, "Recurrence")
		page.addToken(0x10, "Recurrence_Type")
		page.addToken(0x11, "Recurrence_Start")
		page.addToken(0x12, "Recurrence_Until")
		page.addToken(0x13, "Recurrence_Occurrences")
		page.addToken(0x14, "Recurrence_Interval")
		page.addToken(0x15, "Recurrence_DayOfMonth")
		page.addToken(0x16, "Recurrence_DayOfWeek")
		page.addToken(0x17, "Recurrence_WeekOfMonth")
		page.addToken(0x18, "Recurrence_MonthOfYear")
		page.addToken(0x19, "Recurrence_Regenerate")
		page.addToken(0x1A, "Recurrence_DeadOccur")
		page.addToken(0x1B, "ReminderSet")
		page.addToken(0x1C, "ReminderTime")
		page.addToken(0x1D, "Sensitivity")
		page.addToken(0x1E, "StartDate")
		page.addToken(0x1F, "UTCStartDate")
		page.addToken(0x20, "Subject")
		page.addToken(0x22, "OrdinalDate")
		page.addToken(0x23, "SubOrdinalDate")
		page.addToken(0x24, "CalendarType")
		page.addToken(0x25, "IsLeapMonth")
		page.addToken(0x26, "FirstDayOfWeek")
		self.codePages.append(page)
		# endregion

		# Code Page 10: ResolveRecipients
		# region ResolveRecipients Code Page
		page = ASWBXMLCodePage()
		page.namespace = "ResolveRecipients:"
		page.xmlns = "resolverecipients"

		page.addToken(0x05, "ResolveRecipients")
		page.addToken(0x06, "Response")
		page.addToken(0x07, "Status")
		page.addToken(0x08, "Type")
		page.addToken(0x09, "Recipient")
		page.addToken(0x0A, "DisplayName")
		page.addToken(0x0B, "EmailAddress")
		page.addToken(0x0C, "Certificates")
		page.addToken(0x0D, "Certificate")
		page.addToken(0x0E, "MiniCertificate")
		page.addToken(0x0F, "Options")
		page.addToken(0x10, "To")
		page.addToken(0x11, "CertificateRetrieval")
		page.addToken(0x12, "RecipientCount")
		page.addToken(0x13, "MaxCertificates")
		page.addToken(0x14, "MaxAmbiguousRecipients")
		page.addToken(0x15, "CertificateCount")
		page.addToken(0x16, "Availability")
		page.addToken(0x17, "StartTime")
		page.addToken(0x18, "EndTime")
		page.addToken(0x19, "MergedFreeBusy")
		page.addToken(0x1A, "Picture")
		page.addToken(0x1B, "MaxSize")
		page.addToken(0x1C, "Data")
		page.addToken(0x1D, "MaxPictures")
		self.codePages.append(page)
		# endregion

		# Code Page 11: ValidateCert
		# region ValidateCert Code Page
		page = ASWBXMLCodePage()
		page.namespace = "ValidateCert:"
		page.xmlns = "validatecert"

		page.addToken(0x05, "ValidateCert")
		page.addToken(0x06, "Certificates")
		page.addToken(0x07, "Certificate")
		page.addToken(0x08, "CertificateChain")
		page.addToken(0x09, "CheckCRL")
		page.addToken(0x0A, "Status")
		self.codePages.append(page)
		# endregion

		# Code Page 12: Contacts2
		# region Contacts2 Code Page
		page = ASWBXMLCodePage()
		page.namespace = "Contacts2:"
		page.xmlns = "contacts2"

		page.addToken(0x05, "CustomerId")
		page.addToken(0x06, "GovernmentId")
		page.addToken(0x07, "IMAddress")
		page.addToken(0x08, "IMAddress2")
		page.addToken(0x09, "IMAddress3")
		page.addToken(0x0A, "ManagerName")
		page.addToken(0x0B, "CompanyMainPhone")
		page.addToken(0x0C, "AccountName")
		page.addToken(0x0D, "NickName")
		page.addToken(0x0E, "MMS")
		self.codePages.append(page)
		# endregion

		# Code Page 13: Ping
		# region Ping Code Page
		page = ASWBXMLCodePage()
		page.namespace = "Ping:"
		page.xmlns = "ping"

		page.addToken(0x05, "Ping")
		page.addToken(0x06, "AutdState")  # Per MS-ASWBXML, this tag is not used by protocol
		page.addToken(0x07, "Status")
		page.addToken(0x08, "HeartbeatInterval")
		page.addToken(0x09, "Folders")
		page.addToken(0x0A, "Folder")
		page.addToken(0x0B, "Id")
		page.addToken(0x0C, "Class")
		page.addToken(0x0D, "MaxFolders")
		self.codePages.append(page)
		# endregion

		# Code Page 14: Provision
		# region Provision Code Page
		page = ASWBXMLCodePage()
		page.namespace = "Provision:"
		page.xmlns = "provision"

		page.addToken(0x05, "Provision")
		page.addToken(0x06, "Policies")
		page.addToken(0x07, "Policy")
		page.addToken(0x08, "PolicyType")
		page.addToken(0x09, "PolicyKey")
		page.addToken(0x0A, "Data")
		page.addToken(0x0B, "Status")
		page.addToken(0x0C, "RemoteWipe")
		page.addToken(0x0D, "EASProvisionDoc")
		page.addToken(0x0E, "DevicePasswordEnabled")
		page.addToken(0x0F, "AlphanumericDevicePasswordRequired")
		page.addToken(0x10, "RequireStorageCardEncryption")
		page.addToken(0x11, "PasswordRecoveryEnabled")
		page.addToken(0x13, "AttachmentsEnabled")
		page.addToken(0x14, "MinDevicePasswordLength")
		page.addToken(0x15, "MaxInactivityTimeDeviceLock")
		page.addToken(0x16, "MaxDevicePasswordFailedAttempts")
		page.addToken(0x17, "MaxAttachmentSize")
		page.addToken(0x18, "AllowSimpleDevicePassword")
		page.addToken(0x19, "DevicePasswordExpiration")
		page.addToken(0x1A, "DevicePasswordHistory")
		page.addToken(0x1B, "AllowStorageCard")
		page.addToken(0x1C, "AllowCamera")
		page.addToken(0x1D, "RequireDeviceEncryption")
		page.addToken(0x1E, "AllowUnsignedApplications")
		page.addToken(0x1F, "AllowUnsignedInstallationPackages")
		page.addToken(0x20, "MinDevicePasswordComplexCharacters")
		page.addToken(0x21, "AllowWiFi")
		page.addToken(0x22, "AllowTextMessaging")
		page.addToken(0x23, "AllowPOPIMAPEmail")
		page.addToken(0x24, "AllowBluetooth")
		page.addToken(0x25, "AllowIrDA")
		page.addToken(0x26, "RequireManualSyncWhenRoaming")
		page.addToken(0x27, "AllowDesktopSync")
		page.addToken(0x28, "MaxCalendarAgeFilter")
		page.addToken(0x29, "AllowHTMLEmail")
		page.addToken(0x2A, "MaxEmailAgeFilter")
		page.addToken(0x2B, "MaxEmailBodyTruncationSize")
		page.addToken(0x2C, "MaxEmailHTMLBodyTruncationSize")
		page.addToken(0x2D, "RequireSignedSMIMEMessages")
		page.addToken(0x2E, "RequireEncryptedSMIMEMessages")
		page.addToken(0x2F, "RequireSignedSMIMEAlgorithm")
		page.addToken(0x30, "RequireEncryptionSMIMEAlgorithm")
		page.addToken(0x31, "AllowSMIMEEncryptionAlgorithmNegotiation")
		page.addToken(0x32, "AllowSMIMESoftCerts")
		page.addToken(0x33, "AllowBrowser")
		page.addToken(0x34, "AllowConsumerEmail")
		page.addToken(0x35, "AllowRemoteDesktop")
		page.addToken(0x36, "AllowInternetSharing")
		page.addToken(0x37, "UnapprovedInROMApplicationList")
		page.addToken(0x38, "ApplicationName")
		page.addToken(0x39, "ApprovedApplicationList")
		page.addToken(0x3A, "Hash")
		self.codePages.append(page)
		# endregion

		# Code Page 15: Search
		# region Search Code Page
		page = ASWBXMLCodePage()
		page.namespace = "Search:"
		page.xmlns = "search"

		page.addToken(0x05, "Search")
		page.addToken(0x07, "Store")
		page.addToken(0x08, "Name")
		page.addToken(0x09, "Query")
		page.addToken(0x0A, "Options")
		page.addToken(0x0B, "Range")
		page.addToken(0x0C, "Status")
		page.addToken(0x0D, "Response")
		page.addToken(0x0E, "Result")
		page.addToken(0x0F, "Properties")
		page.addToken(0x10, "Total")
		page.addToken(0x11, "EqualTo")
		page.addToken(0x12, "Value")
		page.addToken(0x13, "And")
		page.addToken(0x14, "Or")
		page.addToken(0x15, "FreeText")
		page.addToken(0x17, "DeepTraversal")
		page.addToken(0x18, "LongId")
		page.addToken(0x19, "RebuildResults")
		page.addToken(0x1A, "LessThan")
		page.addToken(0x1B, "GreaterThan")
		page.addToken(0x1E, "UserName")
		page.addToken(0x1F, "Password")
		page.addToken(0x20, "ConversationId")
		page.addToken(0x21, "Picture")
		page.addToken(0x22, "MaxSize")
		page.addToken(0x23, "MaxPictures")
		self.codePages.append(page)
		# endregion

		# Code Page 16: GAL
		# region GAL Code Page
		page = ASWBXMLCodePage()
		page.namespace = "GAL:"
		page.xmlns = "gal"

		page.addToken(0x05, "DisplayName")
		page.addToken(0x06, "Phone")
		page.addToken(0x07, "Office")
		page.addToken(0x08, "Title")
		page.addToken(0x09, "Company")
		page.addToken(0x0A, "Alias")
		page.addToken(0x0B, "FirstName")
		page.addToken(0x0C, "LastName")
		page.addToken(0x0D, "HomePhone")
		page.addToken(0x0E, "MobilePhone")
		page.addToken(0x0F, "EmailAddress")
		page.addToken(0x10, "Picture")
		page.addToken(0x11, "Status")
		page.addToken(0x12, "Data")
		self.codePages.append(page)
		# endregion

		# Code Page 17: AirSyncBase
		# region AirSyncBase Code Page
		page = ASWBXMLCodePage()
		page.namespace = "AirSyncBase:"
		page.xmlns = "airsyncbase"

		page.addToken(0x05, "BodyPreference")
		page.addToken(0x06, "Type")
		page.addToken(0x07, "TruncationSize")
		page.addToken(0x08, "AllOrNone")
		page.addToken(0x0A, "Body")
		page.addToken(0x0B, "Data")
		page.addToken(0x0C, "EstimatedDataSize")
		page.addToken(0x0D, "Truncated")
		page.addToken(0x0E, "Attachments")
		page.addToken(0x0F, "Attachment")
		page.addToken(0x10, "DisplayName")
		page.addToken(0x11, "FileReference")
		page.addToken(0x12, "Method")
		page.addToken(0x13, "ContentId")
		page.addToken(0x14, "ContentLocation")
		page.addToken(0x15, "IsInline")
		page.addToken(0x16, "NativeBodyType")
		page.addToken(0x17, "ContentType")
		page.addToken(0x18, "Preview")
		page.addToken(0x19, "BodyPartPreference")
		page.addToken(0x1A, "BodyPart")
		page.addToken(0x1B, "Status")
		self.codePages.append(page)
		# endregion

		# Code Page 18: Settings
		# region Settings Code Page
		page = ASWBXMLCodePage()
		page.namespace = "Settings:"
		page.xmlns = "settings"

		page.addToken(0x05, "Settings")
		page.addToken(0x06, "Status")
		page.addToken(0x07, "Get")
		page.addToken(0x08, "Set")
		page.addToken(0x09, "Oof")
		page.addToken(0x0A, "OofState")
		page.addToken(0x0B, "StartTime")
		page.addToken(0x0C, "EndTime")
		page.addToken(0x0D, "OofMessage")
		page.addToken(0x0E, "AppliesToInternal")
		page.addToken(0x0F, "AppliesToExternalKnown")
		page.addToken(0x10, "AppliesToExternalUnknown")
		page.addToken(0x11, "Enabled")
		page.addToken(0x12, "ReplyMessage")
		page.addToken(0x13, "BodyType")
		page.addToken(0x14, "DevicePassword")
		page.addToken(0x15, "Password")
		page.addToken(0x16, "DeviceInformation")
		page.addToken(0x17, "Model")
		page.addToken(0x18, "IMEI")
		page.addToken(0x19, "FriendlyName")
		page.addToken(0x1A, "OS")
		page.addToken(0x1B, "OSLanguage")
		page.addToken(0x1C, "PhoneNumber")
		page.addToken(0x1D, "UserInformation")
		page.addToken(0x1E, "EmailAddresses")
		page.addToken(0x1F, "SmtpAddress")
		page.addToken(0x20, "UserAgent")
		page.addToken(0x21, "EnableOutboundSMS")
		page.addToken(0x22, "MobileOperator")
		page.addToken(0x23, "PrimarySmtpAddress")
		page.addToken(0x24, "Accounts")
		page.addToken(0x25, "Account")
		page.addToken(0x26, "AccountId")
		page.addToken(0x27, "AccountName")
		page.addToken(0x28, "UserDisplayName")
		page.addToken(0x29, "SendDisabled")
		page.addToken(0x2B, "RightsManagementInformation")
		self.codePages.append(page)
		# endregion

		# Code Page 19: DocumentLibrary
		# region DocumentLibrary Code Page
		page = ASWBXMLCodePage()
		page.namespace = "DocumentLibrary:"
		page.xmlns = "documentlibrary"

		page.addToken(0x05, "LinkId")
		page.addToken(0x06, "DisplayName")
		page.addToken(0x07, "IsFolder")
		page.addToken(0x08, "CreationDate")
		page.addToken(0x09, "LastModifiedDate")
		page.addToken(0x0A, "IsHidden")
		page.addToken(0x0B, "ContentLength")
		page.addToken(0x0C, "ContentType")
		self.codePages.append(page)
		# endregion

		# Code Page 20: ItemOperations
		# region ItemOperations Code Page
		page = ASWBXMLCodePage()
		page.namespace = "ItemOperations:"
		page.xmlns = "itemoperations"

		page.addToken(0x05, "ItemOperations")
		page.addToken(0x06, "Fetch")
		page.addToken(0x07, "Store")
		page.addToken(0x08, "Options")
		page.addToken(0x09, "Range")
		page.addToken(0x0A, "Total")
		page.addToken(0x0B, "Properties")
		page.addToken(0x0C, "Data")
		page.addToken(0x0D, "Status")
		page.addToken(0x0E, "Response")
		page.addToken(0x0F, "Version")
		page.addToken(0x10, "Schema")
		page.addToken(0x11, "Part")
		page.addToken(0x12, "EmptyFolderContents")
		page.addToken(0x13, "DeleteSubFolders")
		page.addToken(0x14, "UserName")
		page.addToken(0x15, "Password")
		page.addToken(0x16, "Move")
		page.addToken(0x17, "DstFldId")
		page.addToken(0x18, "ConversationId")
		page.addToken(0x19, "MoveAlways")
		self.codePages.append(page)
		# endregion

		# Code Page 21: ComposeMail
		# region ComposeMail Code Page
		page = ASWBXMLCodePage()
		page.namespace = "ComposeMail:"
		page.xmlns = "composemail"

		page.addToken(0x05, "SendMail")
		page.addToken(0x06, "SmartForward")
		page.addToken(0x07, "SmartReply")
		page.addToken(0x08, "SaveInSentItems")
		page.addToken(0x09, "ReplaceMime")
		page.addToken(0x0B, "Source")
		page.addToken(0x0C, "FolderId")
		page.addToken(0x0D, "ItemId")
		page.addToken(0x0E, "LongId")
		page.addToken(0x0F, "InstanceId")
		page.addToken(0x10, "MIME")
		page.addToken(0x11, "ClientId")
		page.addToken(0x12, "Status")
		page.addToken(0x13, "AccountId")
		self.codePages.append(page)
		# endregion

		# Code Page 22: Email2
		# region Email2 Code Page
		page = ASWBXMLCodePage()
		page.namespace = "Email2:"
		page.xmlns = "email2"

		page.addToken(0x05, "UmCallerID")
		page.addToken(0x06, "UmUserNotes")
		page.addToken(0x07, "UmAttDuration")
		page.addToken(0x08, "UmAttOrder")
		page.addToken(0x09, "ConversationId")
		page.addToken(0x0A, "ConversationIndex")
		page.addToken(0x0B, "LastVerbExecuted")
		page.addToken(0x0C, "LastVerbExecutionTime")
		page.addToken(0x0D, "ReceivedAsBcc")
		page.addToken(0x0E, "Sender")
		page.addToken(0x0F, "CalendarType")
		page.addToken(0x10, "IsLeapMonth")
		page.addToken(0x11, "AccountId")
		page.addToken(0x12, "FirstDayOfWeek")
		page.addToken(0x13, "MeetingMessageType")
		self.codePages.append(page)
		# endregion

		# Code Page 23: Notes
		# region Notes Code Page
		page = ASWBXMLCodePage()
		page.namespace = "Notes:"
		page.xmlns = "notes"

		page.addToken(0x05, "Subject")
		page.addToken(0x06, "MessageClass")
		page.addToken(0x07, "LastModifiedDate")
		page.addToken(0x08, "Categories")
		page.addToken(0x09, "Category")
		self.codePages.append(page)
		# endregion

		# Code Page 24: RightsManagement
		# region RightsManagement Code Page
		page = ASWBXMLCodePage()
		page.namespace = "RightsManagement:"
		page.xmlns = "rightsmanagement"

		page.addToken(0x05, "RightsManagementSupport")
		page.addToken(0x06, "RightsManagementTemplates")
		page.addToken(0x07, "RightsManagementTemplate")
		page.addToken(0x08, "RightsManagementLicense")
		page.addToken(0x09, "EditAllowed")
		page.addToken(0x0A, "ReplyAllowed")
		page.addToken(0x0B, "ReplyAllAllowed")
		page.addToken(0x0C, "ForwardAllowed")
		page.addToken(0x0D, "ModifyRecipientsAllowed")
		page.addToken(0x0E, "ExtractAllowed")
		page.addToken(0x0F, "PrintAllowed")
		page.addToken(0x10, "ExportAllowed")
		page.addToken(0x11, "ProgrammaticAccessAllowed")
		page.addToken(0x12, "RMOwner")
		page.addToken(0x13, "ContentExpiryDate")
		page.addToken(0x14, "TemplateID")
		page.addToken(0x15, "TemplateName")
		page.addToken(0x16, "TemplateDescription")
		page.addToken(0x17, "ContentOwner")
		page.addToken(0x18, "RemoveRightsManagementDistribution")
		self.codePages.append(page)
		# endregion
		# endregion
	
	def loadXml(self, strXML):
		# note xmlDoc has .childNodes and .parentNode
		self.xmlDoc = xml.dom.minidom.parseString(strXML)

	def getXml(self):
		if (self.xmlDoc != None):
			try:
				return self.xmlDoc.toprettyxml(indent="    ", newl="\n")
			except:
				return self.xmlDoc.toxml()
	
	def loadBytes(self, byteWBXML):
		
		currentNode = self.xmlDoc
		
		wbXMLBytes = ASWBXMLByteQueue(byteWBXML)
		# Version is ignored
		version = wbXMLBytes.dequeueAndLog()

		# Public Identifier is ignored
		publicId = wbXMLBytes.dequeueMultibyteInt()
		
		logging.debug("Version: %d, Public Identifier: %d" % (version, publicId))
		
		# Character set
		# Currently only UTF-8 is supported, throw if something else
		charset = wbXMLBytes.dequeueMultibyteInt()
		if (charset != 0x6A):
			raise InvalidDataException("ASWBXML only supports UTF-8 encoded XML.")

		# String table length
		# This should be 0, MS-ASWBXML does not use string tables
		stringTableLength = wbXMLBytes.dequeueMultibyteInt()
		if (stringTableLength != 0):
			raise InvalidDataException("WBXML data contains a string table.")

		# Now we should be at the body of the data.
		# Add the declaration
		unusedArray = [GlobalTokens.ENTITY, GlobalTokens.EXT_0, GlobalTokens.EXT_1, GlobalTokens.EXT_2, GlobalTokens.EXT_I_0, GlobalTokens.EXT_I_1, GlobalTokens.EXT_I_2, GlobalTokens.EXT_T_0, GlobalTokens.EXT_T_1, GlobalTokens.EXT_T_2, GlobalTokens.LITERAL, GlobalTokens.LITERAL_A, GlobalTokens.LITERAL_AC, GlobalTokens.LITERAL_C, GlobalTokens.PI, GlobalTokens.STR_T]
		
		while ( wbXMLBytes.qsize() > 0):
			currentByte = wbXMLBytes.dequeueAndLog()
			if ( currentByte == GlobalTokens.SWITCH_PAGE ):
				newCodePage = wbXMLBytes.dequeueAndLog()
				if (newCodePage >= 0 and newCodePage < 25):
					self.currentCodePage = newCodePage
				else:
					raise InvalidDataException("Unknown code page ID 0x{0:X} encountered in WBXML".format(currentByte))
			elif  ( currentByte == GlobalTokens.END ):
				if (currentNode != None and currentNode.parentNode != None):
					currentNode = currentNode.parentNode
				else:
					raise InvalidDataException("END global token encountered out of sequence")
					break
			elif  ( currentByte == GlobalTokens.OPAQUE ):
				CDATALength = wbXMLBytes.dequeueMultibyteInt()
				newOpaqueNode = self.xmlDoc.createCDATASection(wbXMLBytes.dequeueString(CDATALength))
				currentNode.appendChild(newOpaqueNode)

			elif  ( currentByte == GlobalTokens.STR_I ):
				newTextNode = self.xmlDoc.createTextNode(wbXMLBytes.dequeueString())
				currentNode.appendChild(newTextNode)

			elif ( currentByte in unusedArray):
				raise InvalidDataException("Encountered unknown global token 0x{0:X}.".format(currentByte))
			else:
				hasAttributes = (currentByte & 0x80) > 0
				hasContent = (currentByte & 0x40) > 0

				token = currentByte & 0x3F
				if (hasAttributes):
					raise InvalidDataException("Token 0x{0:X} has attributes.".format(token))

				strTag = self.codePages[self.currentCodePage].getTag(token)
				if (strTag == None):
					strTag = "UNKNOWN_TAG_{0,2:X}".format(token)

				newNode = self.xmlDoc.createElement(strTag)
				# not sure if this should be set on every node or not
				#newNode.setAttribute("xmlns", self.codePages[self.currentCodePage].xmlns)
				
				currentNode.appendChild(newNode)

				if (hasContent):
					currentNode = newNode

		logging.debug("Total bytes dequeued: %d" % wbXMLBytes.bytesDequeued)

########NEW FILE########
__FILENAME__ = ASWBXMLByteQueue
#!/usr/bin/env python
'''
@author: David Shaw, david.shaw.aw@gmail.com

Inspired by EAS Inspector for Fiddler
https://easinspectorforfiddler.codeplex.com

----- The MIT License (MIT) ----- 
Filename: ASWBXMLByteQueue.py
Copyright (c) 2014, David P. Shaw

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
'''
from Queue import Queue
import logging

class ASWBXMLByteQueue(Queue):

    def __init__(self, wbxmlBytes):
        
        self.bytesDequeued = 0
        self.bytesEnqueued = 0
        
        Queue.__init__(self)

        for byte in wbxmlBytes:
            self.put(ord(byte))
            self.bytesEnqueued += 1
        
        
        logging.debug("Array byte count: %d, enqueued: %d" % (self.qsize(), self.bytesEnqueued))
    
    """
    Created to debug the dequeueing of bytes
    """
    def dequeueAndLog(self):
        singleByte = self.get()
        self.bytesDequeued += 1
        logging.debug("Dequeued byte 0x{0:X} ({1} total)".format(singleByte, self.bytesDequeued))
        return singleByte
    
    """
    Return true if the continuation bit is set in the byte
    """
    def checkContinuationBit(self, byteval):
        continuationBitmask = 0x80
        return (continuationBitmask & byteval) != 0
    
    def dequeueMultibyteInt(self):
        iReturn = 0
        singleByte = 0xFF
         
        while True:
            iReturn <<= 7
            if (self.qsize() == 0):
                break
            else:
                singleByte = self.dequeueAndLog()
            iReturn += int(singleByte & 0x7F)
            if not self.checkContinuationBit(singleByte):
                return iReturn

    def dequeueString(self, length=None):
        if ( length != None):
            currentByte = 0x00
            strReturn = ""
            for i in range(0, length):
                # TODO: Improve this handling. We are technically UTF-8, meaning
                # that characters could be more than one byte long. This will fail if we have
                # characters outside of the US-ASCII range
                if ( self.qsize() == 0 ):
                    break
                currentByte = self.dequeueAndLog()
                strReturn += chr(currentByte)

        else:
            currentByte = 0x00
            strReturn = ""
            while True:
                currentByte = self.dequeueAndLog()
                if (currentByte != 0x00):
                    strReturn += chr(currentByte)
                else:
                    break

        return strReturn


########NEW FILE########
__FILENAME__ = ASWBXMLCodePage
#!/usr/bin/env python
'''
@author: David Shaw, david.shaw.aw@gmail.com

Inspired by EAS Inspector for Fiddler
https://easinspectorforfiddler.codeplex.com

----- The MIT License (MIT) ----- 
Filename: ASWBXMLCodePage.py
Copyright (c) 2014, David P. Shaw

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
'''
class ASWBXMLCodePage:
	def __init__(self):
		self.namespace = ""
		self.xmlns = ""
		self.tokenLookup = {}
		self.tagLookup = {}
	
	def addToken(self, token, tag):
		self.tokenLookup[token] = tag
		self.tagLookup[tag] = token
	
	def getToken(self, tag):
		if self.tagLookup.has_key(tag):
			return self.tagLookup[tag]
		return 0xFF
	
	def getTag(self, token):
		if self.tokenLookup.has_key(token):
			return self.tokenLookup[token]
		return None
	
	def __repr__(self):
		return str(self.tokenLookup)
########NEW FILE########
__FILENAME__ = GlobalTokens
#!/usr/bin/env python
'''
@author: David Shaw, david.shaw.aw@gmail.com

Inspired by EAS Inspector for Fiddler
https://easinspectorforfiddler.codeplex.com

----- The MIT License (MIT) ----- 
Filename: GlobalTokens.py
Copyright (c) 2014, David P. Shaw

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
'''
class GlobalTokens:
    SWITCH_PAGE = 0x00
    END = 0x01
    ENTITY = 0x02
    STR_I = 0x03
    LITERAL = 0x04
    EXT_I_0 = 0x40
    EXT_I_1 = 0x41
    EXT_I_2 = 0x42
    PI = 0x43
    LITERAL_C = 0x44
    EXT_T_0 = 0x80
    EXT_T_1 = 0x81
    EXT_T_2 = 0x82
    STR_T = 0x83
    LITERAL_A = 0x84
    EXT_0 = 0xC0
    EXT_1 = 0xC1
    EXT_2 = 0xC2
    OPAQUE = 0xC3
    LITERAL_AC = 0xC4
########NEW FILE########
__FILENAME__ = InvalidDataException
#!/usr/bin/env python
'''
@author: David Shaw, david.shaw.aw@gmail.com

Inspired by EAS Inspector for Fiddler
https://easinspectorforfiddler.codeplex.com

----- The MIT License (MIT) ----- 
Filename: InvalidDataException.py
Copyright (c) 2014, David P. Shaw

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
'''
class InvalidDataException(Exception):
    pass
########NEW FILE########
__FILENAME__ = controller
from __future__ import absolute_import
import Queue, threading

should_exit = False


class DummyReply:
    """
        A reply object that does nothing. Useful when we need an object to seem
        like it has a channel, and during testing.
    """
    def __init__(self):
        self.acked = False

    def __call__(self, msg=False):
        self.acked = True


class Reply:
    """
        Messages sent through a channel are decorated with a "reply" attribute.
        This object is used to respond to the message through the return
        channel.
    """
    def __init__(self, obj):
        self.obj = obj
        self.q = Queue.Queue()
        self.acked = False

    def __call__(self, msg=None):
        if not self.acked:
            self.acked = True
            if msg is None:
                self.q.put(self.obj)
            else:
                self.q.put(msg)


class Channel:
    def __init__(self, q):
        self.q = q

    def ask(self, mtype, m):
        """
            Decorate a message with a reply attribute, and send it to the
            master.  then wait for a response.
        """
        m.reply = Reply(m)
        self.q.put((mtype, m))
        while not should_exit:
            try:
                # The timeout is here so we can handle a should_exit event.
                g = m.reply.q.get(timeout=0.5)
            except Queue.Empty: # pragma: nocover
                continue
            return g

    def tell(self, mtype, m):
        """
            Decorate a message with a dummy reply attribute, send it to the
            master, then return immediately.
        """
        m.reply = DummyReply()
        self.q.put((mtype, m))


class Slave(threading.Thread):
    """
        Slaves get a channel end-point through which they can send messages to
        the master.
    """
    def __init__(self, channel, server):
        self.channel, self.server = channel, server
        self.server.set_channel(channel)
        threading.Thread.__init__(self)
        self.name = "SlaveThread (%s:%s)" % (self.server.address.host, self.server.address.port)

    def run(self):
        self.server.serve_forever()


class Master:
    """
        Masters get and respond to messages from slaves.
    """
    def __init__(self, server):
        """
            server may be None if no server is needed.
        """
        self.server = server
        self.masterq = Queue.Queue()

    def tick(self, q):
        changed = False
        try:
            # This endless loop runs until the 'Queue.Empty'
            # exception is thrown. If more than one request is in
            # the queue, this speeds up every request by 0.1 seconds,
            # because get_input(..) function is not blocking.
            while True:
                # Small timeout to prevent pegging the CPU
                msg = q.get(timeout=0.01)
                self.handle(*msg)
                changed = True
        except Queue.Empty:
            pass
        return changed

    def run(self):
        global should_exit
        should_exit = False
        self.server.start_slave(Slave, Channel(self.masterq))
        while not should_exit:
            self.tick(self.masterq)
        self.shutdown()

    def handle(self, mtype, obj):
        c = "handle_" + mtype
        m = getattr(self, c, None)
        if m:
            m(obj)
        else:
            obj.reply()

    def shutdown(self):
        global should_exit
        if not should_exit:
            should_exit = True
            if self.server:
                self.server.shutdown()

########NEW FILE########
__FILENAME__ = dump
from __future__ import absolute_import
import sys, os
import netlib.utils
from . import flow, filt, utils

class DumpError(Exception): pass


class Options(object):
    attributes = [
        "app",
        "app_external",
        "app_host",
        "app_port",
        "anticache",
        "anticomp",
        "client_replay",
        "flow_detail",
        "keepserving",
        "kill",
        "no_server",
        "nopop",
        "refresh_server_playback",
        "replacements",
        "rfile",
        "rheaders",
        "setheaders",
        "server_replay",
        "scripts",
        "showhost",
        "stickycookie",
        "stickyauth",
        "verbosity",
        "wfile",
    ]
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        for i in self.attributes:
            if not hasattr(self, i):
                setattr(self, i, None)


def str_response(resp):
    r = "%s %s"%(resp.code, resp.msg)
    if resp.is_replay:
        r = "[replay] " + r
    return r


def str_request(req, showhost):
    if req.flow.client_conn:
        c = req.flow.client_conn.address.host
    else:
        c = "[replay]"
    r = "%s %s %s"%(c, req.method, req.get_url(showhost))
    if req.stickycookie:
        r = "[stickycookie] " + r
    return r


class DumpMaster(flow.FlowMaster):
    def __init__(self, server, options, filtstr, outfile=sys.stdout):
        flow.FlowMaster.__init__(self, server, flow.State())
        self.outfile = outfile
        self.o = options
        self.anticache = options.anticache
        self.anticomp = options.anticomp
        self.showhost = options.showhost
        self.refresh_server_playback = options.refresh_server_playback

        if filtstr:
            self.filt = filt.parse(filtstr)
        else:
            self.filt = None

        if options.stickycookie:
            self.set_stickycookie(options.stickycookie)

        if options.stickyauth:
            self.set_stickyauth(options.stickyauth)

        if options.wfile:
            path = os.path.expanduser(options.wfile)
            try:
                f = file(path, "wb")
                self.start_stream(f, self.filt)
            except IOError, v:
                raise DumpError(v.strerror)

        if options.replacements:
            for i in options.replacements:
                self.replacehooks.add(*i)

        if options.setheaders:
            for i in options.setheaders:
                self.setheaders.add(*i)

        if options.server_replay:
            self.start_server_playback(
                self._readflow(options.server_replay),
                options.kill, options.rheaders,
                not options.keepserving,
                options.nopop
            )

        if options.client_replay:
            self.start_client_playback(
                self._readflow(options.client_replay),
                not options.keepserving
            )

        scripts = options.scripts or []
        for command in scripts:
            err = self.load_script(command)
            if err:
                raise DumpError(err)

        if options.rfile:
            path = os.path.expanduser(options.rfile)
            try:
                f = file(path, "rb")
                freader = flow.FlowReader(f)
            except IOError, v:
                raise DumpError(v.strerror)
            try:
                self.load_flows(freader)
            except flow.FlowReadError, v:
                self.add_event("Flow file corrupted. Stopped loading.", "error")

        if self.o.app:
            self.start_app(self.o.app_host, self.o.app_port, self.o.app_external)

    def _readflow(self, path):
        path = os.path.expanduser(path)
        try:
            f = file(path, "rb")
            flows = list(flow.FlowReader(f).stream())
        except (IOError, flow.FlowReadError), v:
            raise DumpError(v.strerror)
        return flows

    def add_event(self, e, level="info"):
        needed = dict(error=1, info=1, debug=2).get(level, 1)
        if self.o.verbosity >= needed:
            print >> self.outfile, e
            self.outfile.flush()

    def indent(self, n, t):
        l = str(t).strip().split("\n")
        return "\n".join(" "*n + i for i in l)

    def _process_flow(self, f):
        self.state.delete_flow(f)
        if self.filt and not f.match(self.filt):
            return

        if f.response:
            if self.o.flow_detail > 0:
                sz = utils.pretty_size(len(f.response.content))
                result = " << %s %s"%(str_response(f.response), sz)
            if self.o.flow_detail > 1:
                result = result + "\n\n" + self.indent(4, f.response.headers)
            if self.o.flow_detail > 2:
                if utils.isBin(f.response.content):
                    d = netlib.utils.hexdump(f.response.content)
                    d = "\n".join("%s\t%s %s"%i for i in d)
                    cont = self.indent(4, d)
                elif f.response.content:
                    cont = self.indent(4, f.response.content)
                else:
                    cont = ""
                result = result + "\n\n" + cont
        elif f.error:
            result = " << %s"%f.error.msg

        if self.o.flow_detail == 1:
            print >> self.outfile, str_request(f.request, self.showhost)
            print >> self.outfile, result
        elif self.o.flow_detail == 2:
            print >> self.outfile, str_request(f.request, self.showhost)
            print >> self.outfile, self.indent(4, f.request.headers)
            print >> self.outfile
            print >> self.outfile, result
            print >> self.outfile, "\n"
        elif self.o.flow_detail >= 3:
            print >> self.outfile, str_request(f.request, self.showhost)
            print >> self.outfile, self.indent(4, f.request.headers)
            if utils.isBin(f.request.content):
                print >> self.outfile, self.indent(4, netlib.utils.hexdump(f.request.content))
            elif f.request.content:
                print >> self.outfile, self.indent(4, f.request.content)
            print >> self.outfile
            print >> self.outfile, result
            print >> self.outfile, "\n"
        if self.o.flow_detail:
            self.outfile.flush()

    def handle_request(self, r):
        f = flow.FlowMaster.handle_request(self, r)
        if f:
            r.reply()
        return f

    def handle_response(self, msg):
        f = flow.FlowMaster.handle_response(self, msg)
        if f:
            msg.reply()
            self._process_flow(f)
        return f

    def handle_error(self, msg):
        f = flow.FlowMaster.handle_error(self, msg)
        if f:
            self._process_flow(f)
        return f

    def shutdown(self):  # pragma: no cover
        return flow.FlowMaster.shutdown(self)

    def run(self):  # pragma: no cover
        if self.o.rfile and not self.o.keepserving:
            self.shutdown()
            return
        try:
            return flow.FlowMaster.run(self)
        except BaseException:
            self.shutdown()
            raise

########NEW FILE########
__FILENAME__ = encoding
"""
    Utility functions for decoding response bodies.
"""
from __future__ import absolute_import
import cStringIO
import gzip, zlib

__ALL__ = ["ENCODINGS"]

ENCODINGS = set(["identity", "gzip", "deflate"])

def decode(e, content):
    encoding_map = {
        "identity": identity,
        "gzip": decode_gzip,
        "deflate": decode_deflate,
    }
    if e not in encoding_map:
        return None
    return encoding_map[e](content)

def encode(e, content):
    encoding_map = {
        "identity": identity,
        "gzip": encode_gzip,
        "deflate": encode_deflate,
    }
    if e not in encoding_map:
        return None
    return encoding_map[e](content)

def identity(content):
    """
        Returns content unchanged. Identity is the default value of
        Accept-Encoding headers.
    """
    return content

def decode_gzip(content):
    gfile = gzip.GzipFile(fileobj=cStringIO.StringIO(content))
    try:
        return gfile.read()
    except (IOError, EOFError):
        return None

def encode_gzip(content):
    s = cStringIO.StringIO()
    gf = gzip.GzipFile(fileobj=s, mode='wb')
    gf.write(content)
    gf.close()
    return s.getvalue()

def decode_deflate(content):
    """
        Returns decompressed data for DEFLATE. Some servers may respond with
        compressed data without a zlib header or checksum. An undocumented
        feature of zlib permits the lenient decompression of data missing both
        values.

        http://bugs.python.org/issue5784
    """
    try:
        try:
            return zlib.decompress(content)
        except zlib.error:
            return zlib.decompress(content, -15)
    except zlib.error:
        return None

def encode_deflate(content):
    """
        Returns compressed content, always including zlib header and checksum.
    """
    return zlib.compress(content)

########NEW FILE########
__FILENAME__ = filt
"""
    The following operators are understood:

        ~q          Request
        ~s          Response

    Headers:

        Patterns are matched against "name: value" strings. Field names are
        all-lowercase.

        ~a          Asset content-type in response. Asset content types are:
                        text/javascript
                        application/x-javascript
                        application/javascript
                        text/css
                        image/*
                        application/x-shockwave-flash
        ~h rex      Header line in either request or response
        ~hq rex     Header in request
        ~hs rex     Header in response

        ~b rex      Expression in the body of either request or response
        ~bq rex     Expression in the body of request
        ~bq rex     Expression in the body of response
        ~t rex      Shortcut for content-type header.

        ~d rex      Request domain
        ~m rex      Method
        ~u rex      URL
        ~c CODE     Response code.
        rex         Equivalent to ~u rex
"""
from __future__ import absolute_import
import re, sys
from .contrib import pyparsing as pp


class _Token:
    def dump(self, indent=0, fp=sys.stdout):
        print >> fp, "\t"*indent, self.__class__.__name__,
        if hasattr(self, "expr"):
            print >> fp, "(%s)"%self.expr,
        print >> fp


class _Action(_Token):
    @classmethod
    def make(klass, s, loc, toks):
        return klass(*toks[1:])


class FErr(_Action):
    code = "e"
    help = "Match error"
    def __call__(self, f):
        return True if f.error else False


class FReq(_Action):
    code = "q"
    help = "Match request with no response"
    def __call__(self, f):
        if not f.response:
            return True


class FResp(_Action):
    code = "s"
    help = "Match response"
    def __call__(self, f):
        return True if f.response else False


class _Rex(_Action):
    def __init__(self, expr):
        self.expr = expr
        try:
            self.re = re.compile(self.expr)
        except:
            raise ValueError, "Cannot compile expression."


def _check_content_type(expr, o):
    val = o.headers["content-type"]
    if val and re.search(expr, val[0]):
        return True
    return False


class FAsset(_Action):
    code = "a"
    help = "Match asset in response: CSS, Javascript, Flash, images."
    ASSET_TYPES = [
        "text/javascript",
        "application/x-javascript",
        "application/javascript",
        "text/css",
        "image/.*",
        "application/x-shockwave-flash"
    ]
    def __call__(self, f):
        if f.response:
            for i in self.ASSET_TYPES:
                if _check_content_type(i, f.response):
                    return True
        return False


class FContentType(_Rex):
    code = "t"
    help = "Content-type header"
    def __call__(self, f):
        if _check_content_type(self.expr, f.request):
            return True
        elif f.response and _check_content_type(self.expr, f.response):
            return True
        return False


class FRequestContentType(_Rex):
    code = "tq"
    help = "Request Content-Type header"
    def __call__(self, f):
        return _check_content_type(self.expr, f.request)


class FResponseContentType(_Rex):
    code = "ts"
    help = "Response Content-Type header"
    def __call__(self, f):
        if f.response:
            return _check_content_type(self.expr, f.response)
        return False


class FHead(_Rex):
    code = "h"
    help = "Header"
    def __call__(self, f):
        if f.request.headers.match_re(self.expr):
            return True
        elif f.response and f.response.headers.match_re(self.expr):
            return True
        return False


class FHeadRequest(_Rex):
    code = "hq"
    help = "Request header"
    def __call__(self, f):
        if f.request.headers.match_re(self.expr):
            return True


class FHeadResponse(_Rex):
    code = "hs"
    help = "Response header"
    def __call__(self, f):
        if f.response and f.response.headers.match_re(self.expr):
            return True


class FBod(_Rex):
    code = "b"
    help = "Body"
    def __call__(self, f):
        if f.request.content and re.search(self.expr, f.request.content):
            return True
        elif f.response and f.response.content and re.search(self.expr, f.response.content):
            return True
        return False


class FBodRequest(_Rex):
    code = "bq"
    help = "Request body"
    def __call__(self, f):
        if f.request.content and re.search(self.expr, f.request.content):
            return True


class FBodResponse(_Rex):
    code = "bs"
    help = "Response body"
    def __call__(self, f):
        if f.response and f.response.content and re.search(self.expr, f.response.content):
            return True


class FMethod(_Rex):
    code = "m"
    help = "Method"
    def __call__(self, f):
        return bool(re.search(self.expr, f.request.method, re.IGNORECASE))


class FDomain(_Rex):
    code = "d"
    help = "Domain"
    def __call__(self, f):
        return bool(re.search(self.expr, f.request.get_host(), re.IGNORECASE))


class FUrl(_Rex):
    code = "u"
    help = "URL"
    # FUrl is special, because it can be "naked".
    @classmethod
    def make(klass, s, loc, toks):
        if len(toks) > 1:
            toks = toks[1:]
        return klass(*toks)

    def __call__(self, f):
        return re.search(self.expr, f.request.get_url())


class _Int(_Action):
    def __init__(self, num):
        self.num = int(num)


class FCode(_Int):
    code = "c"
    help = "HTTP response code"
    def __call__(self, f):
        if f.response and f.response.code == self.num:
            return True


class FAnd(_Token):
    def __init__(self, lst):
        self.lst = lst

    def dump(self, indent=0, fp=sys.stdout):
        print >> fp, "\t"*indent, self.__class__.__name__
        for i in self.lst:
            i.dump(indent+1, fp)

    def __call__(self, f):
        return all(i(f) for i in self.lst)


class FOr(_Token):
    def __init__(self, lst):
        self.lst = lst

    def dump(self, indent=0, fp=sys.stdout):
        print >> fp, "\t"*indent, self.__class__.__name__
        for i in self.lst:
            i.dump(indent+1, fp)

    def __call__(self, f):
        return any(i(f) for i in self.lst)


class FNot(_Token):
    def __init__(self, itm):
        self.itm = itm[0]

    def dump(self, indent=0, fp=sys.stdout):
        print >> fp, "\t"*indent, self.__class__.__name__
        self.itm.dump(indent + 1, fp)

    def __call__(self, f):
        return not self.itm(f)


filt_unary = [
    FReq,
    FResp,
    FAsset,
    FErr
]
filt_rex = [
    FHeadRequest,
    FHeadResponse,
    FHead,
    FBodRequest,
    FBodResponse,
    FBod,
    FMethod,
    FDomain,
    FUrl,
    FRequestContentType,
    FResponseContentType,
    FContentType,
]
filt_int = [
    FCode
]
def _make():
    # Order is important - multi-char expressions need to come before narrow
    # ones.
    parts = []
    for klass in filt_unary:
        f = pp.Literal("~%s"%klass.code)
        f.setParseAction(klass.make)
        parts.append(f)

    simplerex = "".join(c for c in pp.printables if c not in  "()~'\"")
    rex = pp.Word(simplerex) |\
          pp.QuotedString("\"", escChar='\\') |\
          pp.QuotedString("'", escChar='\\')
    for klass in filt_rex:
        f = pp.Literal("~%s"%klass.code) + rex.copy()
        f.setParseAction(klass.make)
        parts.append(f)

    for klass in filt_int:
        f = pp.Literal("~%s"%klass.code) + pp.Word(pp.nums)
        f.setParseAction(klass.make)
        parts.append(f)

    # A naked rex is a URL rex:
    f = rex.copy()
    f.setParseAction(FUrl.make)
    parts.append(f)

    atom = pp.MatchFirst(parts)
    expr = pp.operatorPrecedence(
                atom,
                [
                    (pp.Literal("!").suppress(), 1, pp.opAssoc.RIGHT, lambda x: FNot(*x)),
                    (pp.Literal("&").suppress(), 2, pp.opAssoc.LEFT, lambda x: FAnd(*x)),
                    (pp.Literal("|").suppress(), 2, pp.opAssoc.LEFT, lambda x: FOr(*x)),
                ]
           )
    expr = pp.OneOrMore(expr)
    return expr.setParseAction(lambda x: FAnd(x) if len(x) != 1 else x)
bnf = _make()


def parse(s):
    try:
        return bnf.parseString(s, parseAll=True)[0]
    except pp.ParseException:
        return None
    except ValueError:
        return None


########NEW FILE########
__FILENAME__ = flow
"""
    This module provides more sophisticated flow tracking. These match requests
    with their responses, and provide filtering and interception facilities.
"""
from __future__ import absolute_import
import base64
import hashlib, Cookie, cookielib, re, threading
import os
import flask
import requests
from netlib import odict, wsgi, tcp
import netlib.http
from . import controller, protocol, tnetstring, filt, script, version, app
from .protocol import http
from .proxy.connection import ServerConnection
from .proxy.primitives import ProxyError

ODict = odict.ODict
ODictCaseless = odict.ODictCaseless


class AppRegistry:
    def __init__(self):
        self.apps = {}

    def add(self, app, domain, port):
        """
            Add a WSGI app to the registry, to be served for requests to the
            specified domain, on the specified port.
        """
        self.apps[(domain, port)] = wsgi.WSGIAdaptor(app, domain, port, version.NAMEVERSION)

    def get(self, request):
        """
            Returns an WSGIAdaptor instance if request matches an app, or None.
        """
        if (request.get_host(), request.get_port()) in self.apps:
            return self.apps[(request.get_host(), request.get_port())]
        if "host" in request.headers:
            host = request.headers["host"][0]
            return self.apps.get((host, request.get_port()), None)


class ReplaceHooks:
    def __init__(self):
        self.lst = []

    def set(self, r):
        self.clear()
        for i in r:
            self.add(*i)

    def add(self, fpatt, rex, s):
        """
            add a replacement hook.

            fpatt: a string specifying a filter pattern.
            rex: a regular expression.
            s: the replacement string

            returns true if hook was added, false if the pattern could not be
            parsed.
        """
        cpatt = filt.parse(fpatt)
        if not cpatt:
            return False
        try:
            re.compile(rex)
        except re.error:
            return False
        self.lst.append((fpatt, rex, s, cpatt))
        return True

    def get_specs(self):
        """
            Retrieve the hook specifcations. Returns a list of (fpatt, rex, s) tuples.
        """
        return [i[:3] for i in self.lst]

    def count(self):
        return len(self.lst)

    def run(self, f):
        for _, rex, s, cpatt in self.lst:
            if cpatt(f):
                if f.response:
                    f.response.replace(rex, s)
                else:
                    f.request.replace(rex, s)

    def clear(self):
        self.lst = []


class SetHeaders:
    def __init__(self):
        self.lst = []

    def set(self, r):
        self.clear()
        for i in r:
            self.add(*i)

    def add(self, fpatt, header, value):
        """
            Add a set header hook.

            fpatt: String specifying a filter pattern.
            header: Header name.
            value: Header value string

            Returns True if hook was added, False if the pattern could not be
            parsed.
        """
        cpatt = filt.parse(fpatt)
        if not cpatt:
            return False
        self.lst.append((fpatt, header, value, cpatt))
        return True

    def get_specs(self):
        """
            Retrieve the hook specifcations. Returns a list of (fpatt, rex, s) tuples.
        """
        return [i[:3] for i in self.lst]

    def count(self):
        return len(self.lst)

    def clear(self):
        self.lst = []

    def run(self, f):
        for _, header, value, cpatt in self.lst:
            if cpatt(f):
                if f.response:
                    del f.response.headers[header]
                else:
                    del f.request.headers[header]
        for _, header, value, cpatt in self.lst:
            if cpatt(f):
                if f.response:
                    f.response.headers.add(header, value)
                else:
                    f.request.headers.add(header, value)


class ClientPlaybackState:
    def __init__(self, flows, exit):
        self.flows, self.exit = flows, exit
        self.current = None

    def count(self):
        return len(self.flows)

    def done(self):
        if len(self.flows) == 0 and not self.current:
            return True
        return False

    def clear(self, flow):
        """
           A request has returned in some way - if this is the one we're
           servicing, go to the next flow.
        """
        if flow is self.current:
            self.current = None

    def tick(self, master, testing=False):
        """
            testing: Disables actual replay for testing.
        """
        if self.flows and not self.current:
            n = self.flows.pop(0)
            n.request.reply = controller.DummyReply()
            n.client_conn = None
            self.current = master.handle_request(n.request)
            if not testing and not self.current.response:
                master.replay_request(self.current) # pragma: no cover
            elif self.current.response:
                master.handle_response(self.current.response)


class ServerPlaybackState:
    def __init__(self, headers, flows, exit, nopop):
        """
            headers: Case-insensitive list of request headers that should be
            included in request-response matching.
        """
        self.headers, self.exit, self.nopop = headers, exit, nopop
        self.fmap = {}
        for i in flows:
            if i.response:
                l = self.fmap.setdefault(self._hash(i), [])
                l.append(i)

    def count(self):
        return sum(len(i) for i in self.fmap.values())

    def _hash(self, flow):
        """
            Calculates a loose hash of the flow request.
        """
        r = flow.request
        key = [
            str(r.host),
            str(r.port),
            str(r.scheme),
            str(r.method),
            str(r.path),
            str(r.content),
        ]
        if self.headers:
            hdrs = []
            for i in self.headers:
                v = r.headers[i]
                # Slightly subtle: we need to convert everything to strings
                # to prevent a mismatch between unicode/non-unicode.
                v = [str(x) for x in v]
                hdrs.append((i, v))
            key.append(repr(hdrs))
        return hashlib.sha256(repr(key)).digest()

    def next_flow(self, request):
        """
            Returns the next flow object, or None if no matching flow was
            found.
        """
        l = self.fmap.get(self._hash(request))
        if not l:
            return None

        if self.nopop:
            return l[0]
        else:
            return l.pop(0)


class StickyCookieState:
    def __init__(self, flt):
        """
            flt: Compiled filter.
        """
        self.jar = {}
        self.flt = flt

    def ckey(self, m, f):
        """
            Returns a (domain, port, path) tuple.
        """
        return (
            m["domain"] or f.request.get_host(),
            f.request.get_port(),
            m["path"] or "/"
        )

    def domain_match(self, a, b):
        if cookielib.domain_match(a, b):
            return True
        elif cookielib.domain_match(a, b.strip(".")):
            return True
        return False

    def handle_response(self, f):
        for i in f.response.headers["set-cookie"]:
            # FIXME: We now know that Cookie.py screws up some cookies with
            # valid RFC 822/1123 datetime specifications for expiry. Sigh.
            c = Cookie.SimpleCookie(str(i))
            m = c.values()[0]
            k = self.ckey(m, f)
            if self.domain_match(f.request.get_host(), k[0]):
                self.jar[self.ckey(m, f)] = m

    def handle_request(self, f):
        l = []
        if f.match(self.flt):
            for i in self.jar.keys():
                match = [
                    self.domain_match(f.request.get_host(), i[0]),
                    f.request.get_port() == i[1],
                    f.request.path.startswith(i[2])
                ]
                if all(match):
                    l.append(self.jar[i].output(header="").strip())
        if l:
            f.request.stickycookie = True
            f.request.headers["cookie"] = l


class StickyAuthState:
    def __init__(self, flt):
        """
            flt: Compiled filter.
        """
        self.flt = flt
        self.hosts = {}

    def handle_request(self, f):
        host = f.request.get_host()
        if "authorization" in f.request.headers:
            self.hosts[host] = f.request.headers["authorization"]
        elif f.match(self.flt):
            if host in self.hosts:
                f.request.headers["authorization"] = self.hosts[host]


class State(object):
    def __init__(self):
        self._flow_list = []
        self.view = []

        # These are compiled filt expressions:
        self._limit = None
        self.intercept = None
        self._limit_txt = None

    @property
    def limit_txt(self):
        return self._limit_txt

    def flow_count(self):
        return len(self._flow_list)

    def index(self, f):
        return self._flow_list.index(f)

    def active_flow_count(self):
        c = 0
        for i in self._flow_list:
            if not i.response and not i.error:
                c += 1
        return c

    def add_request(self, req):
        """
            Add a request to the state. Returns the matching flow.
        """
        f = req.flow
        self._flow_list.append(f)
        if f.match(self._limit):
            self.view.append(f)
        return f

    def add_response(self, resp):
        """
            Add a response to the state. Returns the matching flow.
        """
        f = resp.flow
        if not f:
            return False
        if f.match(self._limit) and not f in self.view:
            self.view.append(f)
        return f

    def add_error(self, err):
        """
            Add an error response to the state. Returns the matching flow, or
            None if there isn't one.
        """
        f = err.flow
        if not f:
            return None
        if f.match(self._limit) and not f in self.view:
            self.view.append(f)
        return f

    def load_flows(self, flows):
        self._flow_list.extend(flows)
        self.recalculate_view()

    def set_limit(self, txt):
        if txt:
            f = filt.parse(txt)
            if not f:
                return "Invalid filter expression."
            self._limit = f
            self._limit_txt = txt
        else:
            self._limit = None
            self._limit_txt = None
        self.recalculate_view()

    def set_intercept(self, txt):
        if txt:
            f = filt.parse(txt)
            if not f:
                return "Invalid filter expression."
            self.intercept = f
            self.intercept_txt = txt
        else:
            self.intercept = None
            self.intercept_txt = None

    def recalculate_view(self):
        if self._limit:
            self.view = [i for i in self._flow_list if i.match(self._limit)]
        else:
            self.view = self._flow_list[:]

    def delete_flow(self, f):
        self._flow_list.remove(f)
        if f in self.view:
            self.view.remove(f)
        return True

    def clear(self):
        for i in self._flow_list[:]:
            self.delete_flow(i)

    def accept_all(self):
        for i in self._flow_list[:]:
            i.accept_intercept()

    def revert(self, f):
        f.revert()

    def killall(self, master):
        for i in self._flow_list:
            i.kill(master)


class FlowMaster(controller.Master):
    def __init__(self, server, state):
        controller.Master.__init__(self, server)
        self.state = state
        self.server_playback = None
        self.client_playback = None
        self.kill_nonreplay = False
        self.scripts = []
        self.pause_scripts = False

        self.stickycookie_state = False
        self.stickycookie_txt = None

        self.stickyauth_state = False
        self.stickyauth_txt = None

        self.anticache = False
        self.anticomp = False
        self.refresh_server_playback = False
        self.replacehooks = ReplaceHooks()
        self.setheaders = SetHeaders()

        self.stream = None
        self.apps = AppRegistry()

    def start_app(self, host, port, external):
        if not external:
            self.apps.add(
                app.mapp,
                host,
                port
            )
        else:
            @app.mapp.before_request
            def patch_environ(*args, **kwargs):
                flask.request.environ["mitmproxy.master"] = self

            # the only absurd way to shut down a flask/werkzeug server.
            # http://flask.pocoo.org/snippets/67/
            shutdown_secret = base64.b32encode(os.urandom(30))

            @app.mapp.route('/shutdown/<secret>')
            def shutdown(secret):
                if secret == shutdown_secret:
                    flask.request.environ.get('werkzeug.server.shutdown')()

            # Workaround: Monkey-patch shutdown function to stop the app.
            # Improve this when we switch werkzeugs http server for something useful.
            _shutdown = self.shutdown
            def _shutdownwrap():
                _shutdown()
                requests.get("http://%s:%s/shutdown/%s" % (host, port, shutdown_secret))
            self.shutdown = _shutdownwrap

            threading.Thread(target=app.mapp.run, kwargs={
                "use_reloader": False,
                "host": host,
                "port": port}).start()

    def add_event(self, e, level="info"):
        """
            level: debug, info, error
        """
        pass

    def unload_scripts(self):
        for s in self.scripts[:]:
            s.unload()
            self.scripts.remove(s)

    def load_script(self, command):
        """
            Loads a script. Returns an error description if something went
            wrong.
        """
        try:
            s = script.Script(command, self)
        except script.ScriptError, v:
            return v.args[0]
        self.scripts.append(s)

    def run_single_script_hook(self, script, name, *args, **kwargs):
        if script and not self.pause_scripts:
            ret = script.run(name, *args, **kwargs)
            if not ret[0] and ret[1]:
                e = "Script error:\n" + ret[1][1]
                self.add_event(e, "error")

    def run_script_hook(self, name, *args, **kwargs):
        for script in self.scripts:
            self.run_single_script_hook(script, name, *args, **kwargs)

    def set_stickycookie(self, txt):
        if txt:
            flt = filt.parse(txt)
            if not flt:
                return "Invalid filter expression."
            self.stickycookie_state = StickyCookieState(flt)
            self.stickycookie_txt = txt
        else:
            self.stickycookie_state = None
            self.stickycookie_txt = None

    def set_stickyauth(self, txt):
        if txt:
            flt = filt.parse(txt)
            if not flt:
                return "Invalid filter expression."
            self.stickyauth_state = StickyAuthState(flt)
            self.stickyauth_txt = txt
        else:
            self.stickyauth_state = None
            self.stickyauth_txt = None

    def start_client_playback(self, flows, exit):
        """
            flows: List of flows.
        """
        self.client_playback = ClientPlaybackState(flows, exit)

    def stop_client_playback(self):
        self.client_playback = None

    def start_server_playback(self, flows, kill, headers, exit, nopop):
        """
            flows: List of flows.
            kill: Boolean, should we kill requests not part of the replay?
        """
        self.server_playback = ServerPlaybackState(headers, flows, exit, nopop)
        self.kill_nonreplay = kill

    def stop_server_playback(self):
        if self.server_playback.exit:
            self.shutdown()
        self.server_playback = None

    def do_server_playback(self, flow):
        """
            This method should be called by child classes in the handle_request
            handler. Returns True if playback has taken place, None if not.
        """
        if self.server_playback:
            rflow = self.server_playback.next_flow(flow)
            if not rflow:
                return None
            response = http.HTTPResponse._from_state(rflow.response._get_state())
            response.is_replay = True
            if self.refresh_server_playback:
                response.refresh()
            flow.request.reply(response)
            if self.server_playback.count() == 0:
                self.stop_server_playback()
            return True
        return None

    def tick(self, q):
        if self.client_playback:
            e = [
                self.client_playback.done(),
                self.client_playback.exit,
                self.state.active_flow_count() == 0
            ]
            if all(e):
                self.shutdown()
            self.client_playback.tick(self)

        return controller.Master.tick(self, q)

    def duplicate_flow(self, f):
        return self.load_flow(f.copy())

    def load_flow(self, f):
        """
            Loads a flow, and returns a new flow object.
        """
        if f.request:
            f.request.reply = controller.DummyReply()
            fr = self.handle_request(f.request)
        if f.response:
            f.response.reply = controller.DummyReply()
            self.handle_response(f.response)
        if f.error:
            f.error.reply = controller.DummyReply()
            self.handle_error(f.error)
        return fr

    def load_flows(self, fr):
        """
            Load flows from a FlowReader object.
        """
        for i in fr.stream():
            self.load_flow(i)

    def process_new_request(self, f):
        if self.stickycookie_state:
            self.stickycookie_state.handle_request(f)
        if self.stickyauth_state:
            self.stickyauth_state.handle_request(f)

        if self.anticache:
            f.request.anticache()
        if self.anticomp:
            f.request.anticomp()

        if self.server_playback:
            pb = self.do_server_playback(f)
            if not pb:
                if self.kill_nonreplay:
                    f.kill(self)
                else:
                    f.request.reply()

    def process_new_response(self, f):
        if self.stickycookie_state:
            self.stickycookie_state.handle_response(f)

    def replay_request(self, f, block=False):
        """
            Returns None if successful, or error message if not.
        """
        if f.intercepting:
            return "Can't replay while intercepting..."
        if f.request.content == http.CONTENT_MISSING:
            return "Can't replay request with missing content..."
        if f.request:
            f.request.is_replay = True
            if f.request.content:
                f.request.headers["Content-Length"] = [str(len(f.request.content))]
            f.response = None
            f.error = None
            self.process_new_request(f)
            rt = RequestReplayThread(
                    self.server.config,
                    f,
                    self.masterq,
                )
            rt.start() # pragma: no cover
            if block:
                rt.join()

    def handle_log(self, l):
        self.add_event(l.msg, l.level)
        l.reply()

    def handle_clientconnect(self, cc):
        self.run_script_hook("clientconnect", cc)
        cc.reply()

    def handle_clientdisconnect(self, r):
        self.run_script_hook("clientdisconnect", r)
        r.reply()

    def handle_serverconnection(self, sc):
        # To unify the mitmproxy script API, we call the script hook
        # "serverconnect" rather than "serverconnection".  As things are handled
        # differently in libmproxy (ClientConnect + ClientDisconnect vs
        # ServerConnection class), there is no "serverdisonnect" event at the
        # moment.
        self.run_script_hook("serverconnect", sc)
        sc.reply()

    def handle_error(self, r):
        f = self.state.add_error(r)
        if f:
            self.run_script_hook("error", f)
        if self.client_playback:
            self.client_playback.clear(f)
        r.reply()
        return f

    def handle_request(self, r):
        if r.flow.client_conn and r.flow.client_conn.wfile:
            app = self.apps.get(r)
            if app:
                err = app.serve(r, r.flow.client_conn.wfile, **{"mitmproxy.master": self})
                if err:
                    self.add_event("Error in wsgi app. %s"%err, "error")
                r.reply(protocol.KILL)
                return
        f = self.state.add_request(r)
        self.replacehooks.run(f)
        self.setheaders.run(f)
        self.run_script_hook("request", f)
        self.process_new_request(f)
        return f

    def handle_response(self, r):
        f = self.state.add_response(r)
        if f:
            self.replacehooks.run(f)
            self.setheaders.run(f)
            self.run_script_hook("response", f)
            if self.client_playback:
                self.client_playback.clear(f)
            self.process_new_response(f)
            if self.stream:
                self.stream.add(f)
        else:
            r.reply()
        return f

    def shutdown(self):
        self.unload_scripts()
        controller.Master.shutdown(self)
        if self.stream:
            for i in self.state._flow_list:
                if not i.response:
                    self.stream.add(i)
            self.stop_stream()

    def start_stream(self, fp, filt):
        self.stream = FilteredFlowWriter(fp, filt)

    def stop_stream(self):
        self.stream.fo.close()
        self.stream = None



class FlowWriter:
    def __init__(self, fo):
        self.fo = fo

    def add(self, flow):
        d = flow._get_state()
        tnetstring.dump(d, self.fo)


class FlowReadError(Exception):
    @property
    def strerror(self):
        return self.args[0]


class FlowReader:
    def __init__(self, fo):
        self.fo = fo

    def stream(self):
        """
            Yields Flow objects from the dump.
        """
        off = 0
        try:
            while 1:
                data = tnetstring.load(self.fo)
                if tuple(data["version"][:2]) != version.IVERSION[:2]:
                    v = ".".join(str(i) for i in data["version"])
                    raise FlowReadError("Incompatible serialized data version: %s"%v)
                off = self.fo.tell()
                yield protocol.handle.protocols[data["conntype"]]["flow"]._from_state(data)
        except ValueError, v:
            # Error is due to EOF
            if self.fo.tell() == off and self.fo.read() == '':
                return
            raise FlowReadError("Invalid data format.")


class FilteredFlowWriter:
    def __init__(self, fo, filt):
        self.fo = fo
        self.filt = filt

    def add(self, f):
        if self.filt and not f.match(self.filt):
            return
        d = f._get_state()
        tnetstring.dump(d, self.fo)


class RequestReplayThread(threading.Thread):
    name="RequestReplayThread"

    def __init__(self, config, flow, masterq):
        self.config, self.flow, self.channel = config, flow, controller.Channel(masterq)
        threading.Thread.__init__(self)

    def run(self):
        try:
            r = self.flow.request
            server = ServerConnection(self.flow.server_conn.address(), None)
            server.connect()
            if self.flow.server_conn.ssl_established:
                server.establish_ssl(self.config.clientcerts,
                                     self.flow.server_conn.sni)
            server.send(r._assemble())
            self.flow.response = http.HTTPResponse.from_stream(server.rfile, r.method, body_size_limit=self.config.body_size_limit)
            self.channel.ask("response", self.flow.response)
        except (ProxyError, netlib.http.HttpError, tcp.NetLibError), v:
            self.flow.error = protocol.primitives.Error(str(v))
            self.channel.ask("error", self.flow.error)
########NEW FILE########
__FILENAME__ = linux
import socket, struct

# Python socket module does not have this constant
SO_ORIGINAL_DST = 80

class Resolver:
    def original_addr(self, csock):
        odestdata = csock.getsockopt(socket.SOL_IP, SO_ORIGINAL_DST, 16)
        _, port, a1, a2, a3, a4 = struct.unpack("!HHBBBBxxxxxxxx", odestdata)
        address = "%d.%d.%d.%d" % (a1, a2, a3, a4)
        return address, port

########NEW FILE########
__FILENAME__ = osx
import subprocess
import pf

"""
    Doing this the "right" way by using DIOCNATLOOK on the pf device turns out
    to be a pain. Apple has made a number of modifications to the data
    structures returned, and compiling userspace tools to test and work with
    this turns out to be a pain in the ass. Parsing pfctl output is short,
    simple, and works.
"""

class Resolver:
    STATECMD = ("sudo", "-n", "/sbin/pfctl", "-s", "state")
    def __init__(self):
        pass

    def original_addr(self, csock):
        peer = csock.getpeername()
        try:
            stxt = subprocess.check_output(self.STATECMD, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            return None
        return pf.lookup(peer[0], peer[1], stxt)

########NEW FILE########
__FILENAME__ = pf

def lookup(address, port, s):
    """
        Parse the pfctl state output s, to look up the destination host
        matching the client (address, port).

        Returns an (address, port) tuple, or None.
    """
    spec = "%s:%s"%(address, port)
    for i in s.split("\n"):
        if "ESTABLISHED:ESTABLISHED" in i and spec in i:
            s = i.split()
            if len(s) > 4:
                s = s[4].split(":")
                if len(s) == 2:
                    return s[0], int(s[1])

########NEW FILE########
__FILENAME__ = handle
from __future__ import absolute_import
from . import http, tcp

protocols = {
    'http': dict(handler=http.HTTPHandler, flow=http.HTTPFlow),
    'tcp': dict(handler=tcp.TCPHandler)
}


def _handler(conntype, connection_handler):
    if conntype in protocols:
        return protocols[conntype]["handler"](connection_handler)

    raise NotImplementedError   # pragma: nocover


def handle_messages(conntype, connection_handler):
    return _handler(conntype, connection_handler).handle_messages()


def handle_error(conntype, connection_handler, error):
    return _handler(conntype, connection_handler).handle_error(error)
########NEW FILE########
__FILENAME__ = http
from __future__ import absolute_import
import Cookie, urllib, urlparse, time, copy
from email.utils import parsedate_tz, formatdate, mktime_tz
from netlib import http, tcp, http_status
import netlib.utils
from netlib.odict import ODict, ODictCaseless
from .primitives import KILL, ProtocolHandler, TemporaryServerChangeMixin, Flow, Error
from ..proxy.connection import ServerConnection
from .. import encoding, utils, filt, controller, stateobject, proxy

HDR_FORM_URLENCODED = "application/x-www-form-urlencoded"
CONTENT_MISSING = 0


def get_line(fp):
    """
    Get a line, possibly preceded by a blank.
    """
    line = fp.readline()
    if line == "\r\n" or line == "\n":  # Possible leftover from previous message
        line = fp.readline()
    if line == "":
        raise tcp.NetLibDisconnect
    return line


class decoded(object):
    """
    A context manager that decodes a request or response, and then
    re-encodes it with the same encoding after execution of the block.

    Example:
    with decoded(request):
        request.content = request.content.replace("foo", "bar")
    """

    def __init__(self, o):
        self.o = o
        ce = o.headers.get_first("content-encoding")
        if ce in encoding.ENCODINGS:
            self.ce = ce
        else:
            self.ce = None

    def __enter__(self):
        if self.ce:
            self.o.decode()

    def __exit__(self, type, value, tb):
        if self.ce:
            self.o.encode(self.ce)


class HTTPMessage(stateobject.SimpleStateObject):
    def __init__(self, httpversion, headers, content, timestamp_start=None,
                 timestamp_end=None):
        self.httpversion = httpversion
        self.headers = headers
        """@type: ODictCaseless"""
        self.content = content
        self.timestamp_start = timestamp_start
        self.timestamp_end = timestamp_end

        self.flow = None  # will usually be set by the flow backref mixin
        """@type: HTTPFlow"""

    _stateobject_attributes = dict(
        httpversion=tuple,
        headers=ODictCaseless,
        content=str,
        timestamp_start=float,
        timestamp_end=float
    )

    def get_decoded_content(self):
        """
            Returns the decoded content based on the current Content-Encoding header.
            Doesn't change the message iteself or its headers.
        """
        ce = self.headers.get_first("content-encoding")
        if not self.content or ce not in encoding.ENCODINGS:
            return self.content
        return encoding.decode(ce, self.content)

    def decode(self):
        """
            Decodes content based on the current Content-Encoding header, then
            removes the header. If there is no Content-Encoding header, no
            action is taken.

            Returns True if decoding succeeded, False otherwise.
        """
        ce = self.headers.get_first("content-encoding")
        if not self.content or ce not in encoding.ENCODINGS:
            return False
        data = encoding.decode(ce, self.content)
        if data is None:
            return False
        self.content = data
        del self.headers["content-encoding"]
        return True

    def encode(self, e):
        """
            Encodes content with the encoding e, where e is "gzip", "deflate"
            or "identity".
        """
        # FIXME: Error if there's an existing encoding header?
        self.content = encoding.encode(e, self.content)
        self.headers["content-encoding"] = [e]

    def size(self, **kwargs):
        """
            Size in bytes of a fully rendered message, including headers and
            HTTP lead-in.
        """
        hl = len(self._assemble_head(**kwargs))
        if self.content:
            return hl + len(self.content)
        else:
            return hl

    def copy(self):
        c = copy.copy(self)
        c.headers = self.headers.copy()
        return c

    def replace(self, pattern, repl, *args, **kwargs):
        """
            Replaces a regular expression pattern with repl in both the headers
            and the body of the message. Encoded content will be decoded
            before replacement, and re-encoded afterwards.

            Returns the number of replacements made.
        """
        with decoded(self):
            self.content, c = utils.safe_subn(pattern, repl, self.content, *args, **kwargs)
        c += self.headers.replace(pattern, repl, *args, **kwargs)
        return c

    @classmethod
    def from_stream(cls, rfile, include_content=True, body_size_limit=None):
        """
        Parse an HTTP message from a file stream
        """
        raise NotImplementedError  # pragma: nocover

    def _assemble_first_line(self):
        """
        Returns the assembled request/response line
        """
        raise NotImplementedError  # pragma: nocover

    def _assemble_headers(self):
        """
        Returns the assembled headers
        """
        raise NotImplementedError  # pragma: nocover

    def _assemble_head(self):
        """
        Returns the assembled request/response line plus headers
        """
        raise NotImplementedError  # pragma: nocover

    def _assemble(self):
        """
        Returns the assembled request/response
        """
        raise NotImplementedError  # pragma: nocover


class HTTPRequest(HTTPMessage):
    """
    An HTTP request.

    Exposes the following attributes:

        flow: Flow object the request belongs to

        headers: ODictCaseless object

        content: Content of the request, None, or CONTENT_MISSING if there
        is content associated, but not present. CONTENT_MISSING evaluates
        to False to make checking for the presence of content natural.

        form_in: The request form which mitmproxy has received. The following values are possible:
                 - relative (GET /index.html, OPTIONS *) (covers origin form and asterisk form)
                 - absolute (GET http://example.com:80/index.html)
                 - authority-form (CONNECT example.com:443)
                 Details: http://tools.ietf.org/html/draft-ietf-httpbis-p1-messaging-25#section-5.3

        form_out: The request form which mitmproxy has send out to the destination

        method: HTTP method

        scheme: URL scheme (http/https) (absolute-form only)

        host: Host portion of the URL (absolute-form and authority-form only)

        port: Destination port (absolute-form and authority-form only)

        path: Path portion of the URL (not present in authority-form)

        httpversion: HTTP version tuple

        timestamp_start: Timestamp indicating when request transmission started

        timestamp_end: Timestamp indicating when request transmission ended
    """

    def __init__(self, form_in, method, scheme, host, port, path, httpversion, headers,
                 content, timestamp_start=None, timestamp_end=None, form_out=None):
        assert isinstance(headers, ODictCaseless) or not headers
        HTTPMessage.__init__(self, httpversion, headers, content, timestamp_start,
                             timestamp_end)

        self.form_in = form_in
        self.method = method
        self.scheme = scheme
        self.host = host
        self.port = port
        self.path = path
        self.httpversion = httpversion
        self.form_out = form_out or form_in

        # Have this request's cookies been modified by sticky cookies or auth?
        self.stickycookie = False
        self.stickyauth = False
        # Is this request replayed?
        self.is_replay = False

    _stateobject_attributes = HTTPMessage._stateobject_attributes.copy()
    _stateobject_attributes.update(
        form_in=str,
        method=str,
        scheme=str,
        host=str,
        port=int,
        path=str,
        form_out=str
    )

    @classmethod
    def _from_state(cls, state):
        f = cls(None, None, None, None, None, None, None, None, None, None, None)
        f._load_state(state)
        return f

    @classmethod
    def from_stream(cls, rfile, include_content=True, body_size_limit=None):
        """
        Parse an HTTP request from a file stream
        """
        httpversion, host, port, scheme, method, path, headers, content, timestamp_start, timestamp_end \
            = None, None, None, None, None, None, None, None, None, None

        if hasattr(rfile, "reset_timestamps"):
            rfile.reset_timestamps()

        request_line = get_line(rfile)

        if hasattr(rfile, "first_byte_timestamp"):
            timestamp_start = rfile.first_byte_timestamp
        else:
            timestamp_start = utils.timestamp()

        request_line_parts = http.parse_init(request_line)
        if not request_line_parts:
            raise http.HttpError(400, "Bad HTTP request line: %s" % repr(request_line))
        method, path, httpversion = request_line_parts

        if path == '*' or path.startswith("/"):
            form_in = "relative"
            if not netlib.utils.isascii(path):
                raise http.HttpError(400, "Bad HTTP request line: %s" % repr(request_line))
        elif method.upper() == 'CONNECT':
            form_in = "authority"
            r = http.parse_init_connect(request_line)
            if not r:
                raise http.HttpError(400, "Bad HTTP request line: %s" % repr(request_line))
            host, port, _ = r
            path = None
        else:
            form_in = "absolute"
            r = http.parse_init_proxy(request_line)
            if not r:
                raise http.HttpError(400, "Bad HTTP request line: %s" % repr(request_line))
            _, scheme, host, port, path, _ = r

        headers = http.read_headers(rfile)
        if headers is None:
            raise http.HttpError(400, "Invalid headers")

        if include_content:
            content = http.read_http_body(rfile, headers, body_size_limit, True)
            timestamp_end = utils.timestamp()

        return HTTPRequest(form_in, method, scheme, host, port, path, httpversion, headers,
                           content, timestamp_start, timestamp_end)

    def _assemble_first_line(self, form=None):
        form = form or self.form_out

        if form == "relative":
            path = self.path if self.method != "OPTIONS" else "*"
            request_line = '%s %s HTTP/%s.%s' % \
                (self.method, path, self.httpversion[0], self.httpversion[1])
        elif form == "authority":
            request_line = '%s %s:%s HTTP/%s.%s' % (self.method, self.host, self.port,
                                                    self.httpversion[0], self.httpversion[1])
        elif form == "absolute":
            request_line = '%s %s://%s:%s%s HTTP/%s.%s' % \
                           (self.method, self.scheme, self.host, self.port, self.path,
                            self.httpversion[0], self.httpversion[1])
        else:
            raise http.HttpError(400, "Invalid request form")
        return request_line

    def _assemble_headers(self):
        headers = self.headers.copy()
        utils.del_all(
            headers,
            [
                'Proxy-Connection',
                'Keep-Alive',
                'Connection',
                'Transfer-Encoding'
            ]
        )
        if not 'host' in headers:
            headers["Host"] = [utils.hostport(self.scheme,
                                              self.host or self.flow.server_conn.address.host,
                                              self.port or self.flow.server_conn.address.port)]

        if self.content:
            headers["Content-Length"] = [str(len(self.content))]
        elif 'Transfer-Encoding' in self.headers:  # content-length for e.g. chuncked transfer-encoding with no content
            headers["Content-Length"] = ["0"]

        return str(headers)

    def _assemble_head(self, form=None):
        return "%s\r\n%s\r\n" % (self._assemble_first_line(form), self._assemble_headers())

    def _assemble(self, form=None):
        """
            Assembles the request for transmission to the server. We make some
            modifications to make sure interception works properly.

            Raises an Exception if the request cannot be assembled.
        """
        if self.content == CONTENT_MISSING:
            raise proxy.ProxyError(502, "Cannot assemble flow with CONTENT_MISSING")
        head = self._assemble_head(form)
        if self.content:
            return head + self.content
        else:
            return head

    def __hash__(self):
        return id(self)

    def anticache(self):
        """
            Modifies this request to remove headers that might produce a cached
            response. That is, we remove ETags and If-Modified-Since headers.
        """
        delheaders = [
            "if-modified-since",
            "if-none-match",
        ]
        for i in delheaders:
            del self.headers[i]

    def anticomp(self):
        """
            Modifies this request to remove headers that will compress the
            resource's data.
        """
        self.headers["accept-encoding"] = ["identity"]

    def constrain_encoding(self):
        """
            Limits the permissible Accept-Encoding values, based on what we can
            decode appropriately.
        """
        if self.headers["accept-encoding"]:
            self.headers["accept-encoding"] = [', '.join(
                e for e in encoding.ENCODINGS if e in self.headers["accept-encoding"][0]
            )]

    def get_form_urlencoded(self):
        """
            Retrieves the URL-encoded form data, returning an ODict object.
            Returns an empty ODict if there is no data or the content-type
            indicates non-form data.
        """
        if self.content and self.headers.in_any("content-type", HDR_FORM_URLENCODED, True):
            return ODict(utils.urldecode(self.content))
        return ODict([])

    def set_form_urlencoded(self, odict):
        """
            Sets the body to the URL-encoded form data, and adds the
            appropriate content-type header. Note that this will destory the
            existing body if there is one.
        """
        # FIXME: If there's an existing content-type header indicating a
        # url-encoded form, leave it alone.
        self.headers["Content-Type"] = [HDR_FORM_URLENCODED]
        self.content = utils.urlencode(odict.lst)

    def get_path_components(self):
        """
            Returns the path components of the URL as a list of strings.

            Components are unquoted.
        """
        _, _, path, _, _, _ = urlparse.urlparse(self.get_url())
        return [urllib.unquote(i) for i in path.split("/") if i]

    def set_path_components(self, lst):
        """
            Takes a list of strings, and sets the path component of the URL.

            Components are quoted.
        """
        lst = [urllib.quote(i, safe="") for i in lst]
        path = "/" + "/".join(lst)
        scheme, netloc, _, params, query, fragment = urlparse.urlparse(self.get_url())
        self.set_url(urlparse.urlunparse([scheme, netloc, path, params, query, fragment]))

    def get_query(self):
        """
            Gets the request query string. Returns an ODict object.
        """
        _, _, _, _, query, _ = urlparse.urlparse(self.get_url())
        if query:
            return ODict(utils.urldecode(query))
        return ODict([])

    def set_query(self, odict):
        """
            Takes an ODict object, and sets the request query string.
        """
        scheme, netloc, path, params, _, fragment = urlparse.urlparse(self.get_url())
        query = utils.urlencode(odict.lst)
        self.set_url(urlparse.urlunparse([scheme, netloc, path, params, query, fragment]))

    def get_host(self, hostheader=False):
        """
            Heuristic to get the host of the request.
            The host is not necessarily equal to the TCP destination of the request,
            for example on a transparently proxified absolute-form request to an upstream HTTP proxy.
            If hostheader is set to True, the Host: header will be used as additional (and preferred) data source.
        """
        host = None
        if hostheader:
            host = self.headers.get_first("host")
        if not host:
            if self.host:
                host = self.host
            else:
                host = self.flow.server_conn.address.host
        host = host.encode("idna")
        return host

    def get_scheme(self):
        """
        Returns the request port, either from the request itself or from the flow's server connection
        """
        if self.scheme:
            return self.scheme
        return "https" if self.flow.server_conn.ssl_established else "http"

    def get_port(self):
        """
        Returns the request port, either from the request itself or from the flow's server connection
        """
        if self.port:
            return self.port
        return self.flow.server_conn.address.port

    def get_url(self, hostheader=False):
        """
            Returns a URL string, constructed from the Request's URL components.

            If hostheader is True, we use the value specified in the request
            Host header to construct the URL.
        """
        if self.form_out == "authority":  # upstream proxy mode
            return "%s:%s" % (self.get_host(hostheader), self.get_port())
        return utils.unparse_url(self.get_scheme(),
                                 self.get_host(hostheader),
                                 self.get_port(),
                                 self.path).encode('ascii')

    def set_url(self, url):
        """
            Parses a URL specification, and updates the Request's information
            accordingly.

            Returns False if the URL was invalid, True if the request succeeded.
        """
        parts = http.parse_url(url)
        if not parts:
            return False
        scheme, host, port, path = parts
        is_ssl = (True if scheme == "https" else False)

        self.path = path

        if host != self.get_host() or port != self.get_port():
            if self.flow.change_server:
                self.flow.change_server((host, port), ssl=is_ssl)
            else:
                # There's not live server connection, we're just changing the attributes here.
                self.flow.server_conn = ServerConnection((host, port),
                                                         proxy.AddressPriority.MANUALLY_CHANGED)
                self.flow.server_conn.ssl_established = is_ssl

        # If this is an absolute request, replace the attributes on the request object as well.
        if self.host:
            self.host = host
        if self.port:
            self.port = port
        if self.scheme:
            self.scheme = scheme

        return True

    def get_cookies(self):
        cookie_headers = self.headers.get("cookie")
        if not cookie_headers:
            return None

        cookies = []
        for header in cookie_headers:
            pairs = [pair.partition("=") for pair in header.split(';')]
            cookies.extend((pair[0], (pair[2], {})) for pair in pairs)
        return dict(cookies)

    def replace(self, pattern, repl, *args, **kwargs):
        """
            Replaces a regular expression pattern with repl in the headers, the request path
            and the body of the request. Encoded content will be decoded before
            replacement, and re-encoded afterwards.

            Returns the number of replacements made.
        """
        c = HTTPMessage.replace(self, pattern, repl, *args, **kwargs)
        self.path, pc = utils.safe_subn(pattern, repl, self.path, *args, **kwargs)
        c += pc
        return c


class HTTPResponse(HTTPMessage):
    """
    An HTTP response.

    Exposes the following attributes:

        flow: Flow object the request belongs to

        code: HTTP response code

        msg: HTTP response message

        headers: ODict object

        content: Content of the request, None, or CONTENT_MISSING if there
        is content associated, but not present. CONTENT_MISSING evaluates
        to False to make checking for the presence of content natural.

        httpversion: HTTP version tuple

        timestamp_start: Timestamp indicating when request transmission started

        timestamp_end: Timestamp indicating when request transmission ended
    """

    def __init__(self, httpversion, code, msg, headers, content, timestamp_start=None,
                 timestamp_end=None):
        assert isinstance(headers, ODictCaseless) or headers is None
        HTTPMessage.__init__(self, httpversion, headers, content, timestamp_start,
                             timestamp_end)

        self.code = code
        self.msg = msg

        # Is this request replayed?
        self.is_replay = False

    _stateobject_attributes = HTTPMessage._stateobject_attributes.copy()
    _stateobject_attributes.update(
        code=int,
        msg=str
    )

    @classmethod
    def _from_state(cls, state):
        f = cls(None, None, None, None, None)
        f._load_state(state)
        return f

    @classmethod
    def from_stream(cls, rfile, request_method, include_content=True, body_size_limit=None):
        """
        Parse an HTTP response from a file stream
        """
        if not include_content:
            raise NotImplementedError  # pragma: nocover

        if hasattr(rfile, "reset_timestamps"):
            rfile.reset_timestamps()

        httpversion, code, msg, headers, content = http.read_response(
            rfile,
            request_method,
            body_size_limit)

        if hasattr(rfile, "first_byte_timestamp"):
            timestamp_start = rfile.first_byte_timestamp
        else:
            timestamp_start = utils.timestamp()

        timestamp_end = utils.timestamp()
        return HTTPResponse(httpversion, code, msg, headers, content, timestamp_start,
                            timestamp_end)

    def _assemble_first_line(self):
        return 'HTTP/%s.%s %s %s' % \
               (self.httpversion[0], self.httpversion[1], self.code, self.msg)

    def _assemble_headers(self):
        headers = self.headers.copy()
        utils.del_all(
            headers,
            [
                'Proxy-Connection',
                'Transfer-Encoding'
            ]
        )
        if self.content:
            headers["Content-Length"] = [str(len(self.content))]
        elif 'Transfer-Encoding' in self.headers:  # add content-length for chuncked transfer-encoding with no content
            headers["Content-Length"] = ["0"]

        return str(headers)

    def _assemble_head(self):
        return '%s\r\n%s\r\n' % (self._assemble_first_line(), self._assemble_headers())

    def _assemble(self):
        """
            Assembles the response for transmission to the client. We make some
            modifications to make sure interception works properly.

            Raises an Exception if the request cannot be assembled.
        """
        if self.content == CONTENT_MISSING:
            raise proxy.ProxyError(502, "Cannot assemble flow with CONTENT_MISSING")
        head = self._assemble_head()
        if self.content:
            return head + self.content
        else:
            return head

    def _refresh_cookie(self, c, delta):
        """
            Takes a cookie string c and a time delta in seconds, and returns
            a refreshed cookie string.
        """
        c = Cookie.SimpleCookie(str(c))
        for i in c.values():
            if "expires" in i:
                d = parsedate_tz(i["expires"])
                if d:
                    d = mktime_tz(d) + delta
                    i["expires"] = formatdate(d)
                else:
                    # This can happen when the expires tag is invalid.
                    # reddit.com sends a an expires tag like this: "Thu, 31 Dec
                    # 2037 23:59:59 GMT", which is valid RFC 1123, but not
                    # strictly correct according to the cookie spec. Browsers
                    # appear to parse this tolerantly - maybe we should too.
                    # For now, we just ignore this.
                    del i["expires"]
        return c.output(header="").strip()

    def refresh(self, now=None):
        """
            This fairly complex and heuristic function refreshes a server
            response for replay.

                - It adjusts date, expires and last-modified headers.
                - It adjusts cookie expiration.
        """
        if not now:
            now = time.time()
        delta = now - self.timestamp_start
        refresh_headers = [
            "date",
            "expires",
            "last-modified",
        ]
        for i in refresh_headers:
            if i in self.headers:
                d = parsedate_tz(self.headers[i][0])
                if d:
                    new = mktime_tz(d) + delta
                    self.headers[i] = [formatdate(new)]
        c = []
        for i in self.headers["set-cookie"]:
            c.append(self._refresh_cookie(i, delta))
        if c:
            self.headers["set-cookie"] = c

    def get_cookies(self):
        cookie_headers = self.headers.get("set-cookie")
        if not cookie_headers:
            return None

        cookies = []
        for header in cookie_headers:
            pairs = [pair.partition("=") for pair in header.split(';')]
            cookie_name = pairs[0][0]  # the key of the first key/value pairs
            cookie_value = pairs[0][2]  # the value of the first key/value pairs
            cookie_parameters = {key.strip().lower(): value.strip() for key, sep, value in
                                 pairs[1:]}
            cookies.append((cookie_name, (cookie_value, cookie_parameters)))
        return dict(cookies)


class HTTPFlow(Flow):
    """
    A Flow is a collection of objects representing a single HTTP
    transaction. The main attributes are:

        request: HTTPRequest object
        response: HTTPResponse object
        error: Error object

    Note that it's possible for a Flow to have both a response and an error
    object. This might happen, for instance, when a response was received
    from the server, but there was an error sending it back to the client.

    The following additional attributes are exposed:

        intercepting: Is this flow currently being intercepted?
    """

    def __init__(self, client_conn, server_conn, change_server=None):
        Flow.__init__(self, "http", client_conn, server_conn)
        self.request = None
        """@type: HTTPRequest"""
        self.response = None
        """@type: HTTPResponse"""
        self.change_server = change_server  # Used by flow.request.set_url to change the server address

        self.intercepting = False  # FIXME: Should that rather be an attribute of Flow?

    _backrefattr = Flow._backrefattr + ("request", "response")

    _stateobject_attributes = Flow._stateobject_attributes.copy()
    _stateobject_attributes.update(
        request=HTTPRequest,
        response=HTTPResponse
    )

    @classmethod
    def _from_state(cls, state):
        f = cls(None, None)
        f._load_state(state)
        return f

    def copy(self):
        f = super(HTTPFlow, self).copy()
        if self.request:
            f.request = self.request.copy()
        if self.response:
            f.response = self.response.copy()
        return f

    def match(self, f):
        """
            Match this flow against a compiled filter expression. Returns True
            if matched, False if not.

            If f is a string, it will be compiled as a filter expression. If
            the expression is invalid, ValueError is raised.
        """
        if isinstance(f, basestring):
            f = filt.parse(f)
            if not f:
                raise ValueError("Invalid filter expression.")
        if f:
            return f(self)
        return True

    def kill(self, master):
        """
            Kill this request.
        """
        self.error = Error("Connection killed")
        self.error.reply = controller.DummyReply()
        if self.request and not self.request.reply.acked:
            self.request.reply(KILL)
        elif self.response and not self.response.reply.acked:
            self.response.reply(KILL)
        master.handle_error(self.error)
        self.intercepting = False

    def intercept(self):
        """
            Intercept this Flow. Processing will stop until accept_intercept is
            called.
        """
        self.intercepting = True

    def accept_intercept(self):
        """
            Continue with the flow - called after an intercept().
        """
        if self.request:
            if not self.request.reply.acked:
                self.request.reply()
            elif self.response and not self.response.reply.acked:
                self.response.reply()
            self.intercepting = False

    def replace(self, pattern, repl, *args, **kwargs):
        """
            Replaces a regular expression pattern with repl in both request and response of the
            flow. Encoded content will be decoded before replacement, and
            re-encoded afterwards.

            Returns the number of replacements made.
        """
        c = self.request.replace(pattern, repl, *args, **kwargs)
        if self.response:
            c += self.response.replace(pattern, repl, *args, **kwargs)
        return c


class HttpAuthenticationError(Exception):
    def __init__(self, auth_headers=None):
        super(HttpAuthenticationError, self).__init__("Proxy Authentication Required")
        self.headers = auth_headers
        self.code = 407

    def __repr__(self):
        return "Proxy Authentication Required"


class HTTPHandler(ProtocolHandler, TemporaryServerChangeMixin):
    def __init__(self, c):
        super(HTTPHandler, self).__init__(c)
        self.expected_form_in = c.config.http_form_in
        self.expected_form_out = c.config.http_form_out
        self.skip_authentication = False

    def handle_messages(self):
        while self.handle_flow():
            pass
        self.c.close = True

    def get_response_from_server(self, request):
        self.c.establish_server_connection()
        request_raw = request._assemble()

        for i in range(2):
            try:
                self.c.server_conn.send(request_raw)
                return HTTPResponse.from_stream(self.c.server_conn.rfile, request.method,
                                                body_size_limit=self.c.config.body_size_limit)
            except (tcp.NetLibDisconnect, http.HttpErrorConnClosed), v:
                self.c.log("error in server communication: %s" % str(v), level="debug")
                if i < 1:
                    # In any case, we try to reconnect at least once.
                    # This is necessary because it might be possible that we already initiated an upstream connection
                    # after clientconnect that has already been expired, e.g consider the following event log:
                    # > clientconnect (transparent mode destination known)
                    # > serverconnect
                    # > read n% of large request
                    # > server detects timeout, disconnects
                    # > read (100-n)% of large request
                    # > send large request upstream
                    self.c.server_reconnect()
                else:
                    raise v

    def handle_flow(self):
        flow = HTTPFlow(self.c.client_conn, self.c.server_conn, self.change_server)
        try:
            req = HTTPRequest.from_stream(self.c.client_conn.rfile,
                                          body_size_limit=self.c.config.body_size_limit)
            self.c.log("request", "debug", [req._assemble_first_line(req.form_in)])
            send_upstream = self.process_request(flow, req)
            if not send_upstream:
                return True

            # Be careful NOT to assign the request to the flow before
            # process_request completes. This is because the call can raise an
            # exception. If the request object is already attached, this results
            # in an Error object that has an attached request that has not been
            # sent through to the Master.
            flow.request = req
            request_reply = self.c.channel.ask("request", flow.request)
            flow.server_conn = self.c.server_conn

            if request_reply is None or request_reply == KILL:
                return False

            if isinstance(request_reply, HTTPResponse):
                flow.response = request_reply
            else:
                flow.response = self.get_response_from_server(flow.request)

            flow.server_conn = self.c.server_conn  # no further manipulation of self.c.server_conn beyond this point
            # we can safely set it as the final attribute value here.

            self.c.log("response", "debug", [flow.response._assemble_first_line()])
            response_reply = self.c.channel.ask("response", flow.response)
            if response_reply is None or response_reply == KILL:
                return False

            self.c.client_conn.send(flow.response._assemble())
            flow.timestamp_end = utils.timestamp()

            if (http.connection_close(flow.request.httpversion, flow.request.headers) or
                    http.connection_close(flow.response.httpversion, flow.response.headers)):
                return False

            if flow.request.form_in == "authority":
                self.ssl_upgrade()

            # If the user has changed the target server on this connection,
            # restore the original target server
            self.restore_server()
            return True
        except (HttpAuthenticationError, http.HttpError, proxy.ProxyError, tcp.NetLibError), e:
            self.handle_error(e, flow)
        return False

    def handle_error(self, error, flow=None):

        message = repr(error)
        code = getattr(error, "code", 502)
        headers = getattr(error, "headers", None)

        if "tlsv1 alert unknown ca" in message:
            message = message + " \nThe client does not trust the proxy's certificate."

        self.c.log("error: %s" % message, level="info")

        if flow:
            flow.error = Error(message)
            # FIXME: no flows without request or with both request and response at the moement.
            if flow.request and not flow.response:
                self.c.channel.ask("error", flow.error)
        else:
            pass  #  FIXME: Do we want to persist errors without flows?

        try:
            self.send_error(code, message, headers)
        except:
            pass

    def send_error(self, code, message, headers):
        response = http_status.RESPONSES.get(code, "Unknown")
        html_content = '<html><head>\n<title>%d %s</title>\n</head>\n<body>\n%s\n</body>\n</html>' % \
                       (code, response, message)
        self.c.client_conn.wfile.write("HTTP/1.1 %s %s\r\n" % (code, response))
        self.c.client_conn.wfile.write("Server: %s\r\n" % self.c.server_version)
        self.c.client_conn.wfile.write("Content-type: text/html\r\n")
        self.c.client_conn.wfile.write("Content-Length: %d\r\n" % len(html_content))
        if headers:
            for key, value in headers.items():
                self.c.client_conn.wfile.write("%s: %s\r\n" % (key, value))
        self.c.client_conn.wfile.write("Connection: close\r\n")
        self.c.client_conn.wfile.write("\r\n")
        self.c.client_conn.wfile.write(html_content)
        self.c.client_conn.wfile.flush()

    def hook_reconnect(self, upstream_request):
        """
        If the authority request has been forwarded upstream (because we have another proxy server there),
        money-patch the ConnectionHandler.server_reconnect function to resend the CONNECT request on reconnect.
        Hooking code isn't particulary beautiful, but it isolates this edge-case from
        the protocol-agnostic ConnectionHandler
        """
        self.c.log("Hook reconnect function", level="debug")
        original_reconnect_func = self.c.server_reconnect

        def reconnect_http_proxy():
            self.c.log("Hooked reconnect function", "debug")
            self.c.log("Hook: Run original reconnect", "debug")
            original_reconnect_func(no_ssl=True)
            self.c.log("Hook: Write CONNECT request to upstream proxy", "debug",
                       [upstream_request._assemble_first_line()])
            self.c.server_conn.send(upstream_request._assemble())
            self.c.log("Hook: Read answer to CONNECT request from proxy", "debug")
            resp = HTTPResponse.from_stream(self.c.server_conn.rfile, upstream_request.method)
            if resp.code != 200:
                raise proxy.ProxyError(resp.code,
                                       "Cannot reestablish SSL " +
                                       "connection with upstream proxy: \r\n" +
                                       str(resp.headers))
            self.c.log("Hook: Establish SSL with upstream proxy", "debug")
            self.c.establish_ssl(server=True)

        self.c.server_reconnect = reconnect_http_proxy

    def ssl_upgrade(self):
        """
        Upgrade the connection to SSL after an authority (CONNECT) request has been made.
        """
        self.c.log("Received CONNECT request. Upgrading to SSL...", "debug")
        self.expected_form_in = "relative"
        self.expected_form_out = "relative"
        self.c.establish_ssl(server=True, client=True)
        self.c.log("Upgrade to SSL completed.", "debug")

    def process_request(self, flow, request):

        if not self.skip_authentication:
            self.authenticate(request)

        if request.form_in == "authority":
            if self.c.client_conn.ssl_established:
                raise http.HttpError(400, "Must not CONNECT on already encrypted connection")

            if self.expected_form_in == "absolute":
                if not self.c.config.get_upstream_server:
                    self.c.set_server_address((request.host, request.port),
                                              proxy.AddressPriority.FROM_PROTOCOL)
                    flow.server_conn = self.c.server_conn  # Update server_conn attribute on the flow
                    self.c.client_conn.send(
                        'HTTP/1.1 200 Connection established\r\n' +
                        ('Proxy-agent: %s\r\n' % self.c.server_version) +
                        '\r\n'
                    )
                    self.ssl_upgrade()
                    self.skip_authentication = True
                    return False
                else:
                    self.hook_reconnect(request)
                    return True
        elif request.form_in == self.expected_form_in:
            if request.form_in == "absolute":
                if request.scheme != "http":
                    raise http.HttpError(400, "Invalid request scheme: %s" % request.scheme)

                self.c.set_server_address((request.host, request.port),
                                          proxy.AddressPriority.FROM_PROTOCOL)
                flow.server_conn = self.c.server_conn  # Update server_conn attribute on the flow

            request.form_out = self.expected_form_out
            return True

        raise http.HttpError(400, "Invalid HTTP request form (expected: %s, got: %s)" %
                                  (self.expected_form_in, request.form_in))

    def authenticate(self, request):
        if self.c.config.authenticator:
            if self.c.config.authenticator.authenticate(request.headers):
                self.c.config.authenticator.clean(request.headers)
            else:
                raise HttpAuthenticationError(
                    self.c.config.authenticator.auth_challenge_headers())
        return request.headers

########NEW FILE########
__FILENAME__ = primitives
from __future__ import absolute_import
import copy
import netlib.tcp
from .. import stateobject, utils, version
from ..proxy.primitives import AddressPriority
from ..proxy.connection import ClientConnection, ServerConnection


KILL = 0  # const for killed requests


class BackreferenceMixin(object):
    """
    If an attribute from the _backrefattr tuple is set,
    this mixin sets a reference back on the attribute object.
    Example:
        e = Error()
        f = Flow()
        f.error = e
        assert f is e.flow
    """
    _backrefattr = tuple()

    def __setattr__(self, key, value):
        super(BackreferenceMixin, self).__setattr__(key, value)
        if key in self._backrefattr and value is not None:
            setattr(value, self._backrefname, self)


class Error(stateobject.SimpleStateObject):
    """
        An Error.

        This is distinct from an HTTP error response (say, a code 500), which
        is represented by a normal Response object. This class is responsible
        for indicating errors that fall outside of normal HTTP communications,
        like interrupted connections, timeouts, protocol errors.

        Exposes the following attributes:

            flow: Flow object
            msg: Message describing the error
            timestamp: Seconds since the epoch
    """
    def __init__(self, msg, timestamp=None):
        """
        @type msg: str
        @type timestamp: float
        """
        self.flow = None  # will usually be set by the flow backref mixin
        self.msg = msg
        self.timestamp = timestamp or utils.timestamp()

    _stateobject_attributes = dict(
        msg=str,
        timestamp=float
    )

    def __str__(self):
        return self.msg

    @classmethod
    def _from_state(cls, state):
        f = cls(None)  # the default implementation assumes an empty constructor. Override accordingly.
        f._load_state(state)
        return f

    def copy(self):
        c = copy.copy(self)
        return c


class Flow(stateobject.SimpleStateObject, BackreferenceMixin):
    def __init__(self, conntype, client_conn, server_conn):
        self.conntype = conntype
        self.client_conn = client_conn
        """@type: ClientConnection"""
        self.server_conn = server_conn
        """@type: ServerConnection"""

        self.error = None
        """@type: Error"""
        self._backup = None

    _backrefattr = ("error",)
    _backrefname = "flow"

    _stateobject_attributes = dict(
        error=Error,
        client_conn=ClientConnection,
        server_conn=ServerConnection,
        conntype=str
    )

    def _get_state(self):
        d = super(Flow, self)._get_state()
        d.update(version=version.IVERSION)
        return d

    def __eq__(self, other):
        return self is other

    def copy(self):
        f = copy.copy(self)

        f.client_conn = self.client_conn.copy()
        f.server_conn = self.server_conn.copy()

        if self.error:
            f.error = self.error.copy()
        return f

    def modified(self):
        """
            Has this Flow been modified?
        """
        if self._backup:
            return self._backup != self._get_state()
        else:
            return False

    def backup(self, force=False):
        """
            Save a backup of this Flow, which can be reverted to using a
            call to .revert().
        """
        if not self._backup:
            self._backup = self._get_state()

    def revert(self):
        """
            Revert to the last backed up state.
        """
        if self._backup:
            self._load_state(self._backup)
            self._backup = None


class ProtocolHandler(object):
    def __init__(self, c):
        self.c = c
        """@type: libmproxy.proxy.ConnectionHandler"""

    def handle_messages(self):
        """
        This method gets called if a client connection has been made. Depending on the proxy settings,
        a server connection might already exist as well.
        """
        raise NotImplementedError  # pragma: nocover

    def handle_error(self, error):
        """
        This method gets called should there be an uncaught exception during the connection.
        This might happen outside of handle_messages, e.g. if the initial SSL handshake fails in transparent mode.
        """
        raise error  # pragma: nocover


class TemporaryServerChangeMixin(object):
    """
    This mixin allows safe modification of the target server,
    without any need to expose the ConnectionHandler to the Flow.
    """
    def change_server(self, address, ssl):
        address = netlib.tcp.Address.wrap(address)
        if address == self.c.server_conn.address():
            return
        priority = AddressPriority.MANUALLY_CHANGED

        self.c.log("Temporarily change server connection: %s:%s -> %s:%s" % (
            self.c.server_conn.address.host,
            self.c.server_conn.address.port,
            address.host,
            address.port
        ), "debug")

        if not hasattr(self, "_backup_server_conn"):
            self._backup_server_conn = self.c.server_conn
            self.c.server_conn = None
        else:  # This is at least the second temporary change. We can kill the current connection.
            self.c.del_server_connection()

        self.c.set_server_address(address, priority)
        if ssl:
            self.c.establish_ssl(server=True)

    def restore_server(self):
        if not hasattr(self, "_backup_server_conn"):
            return

        self.c.log("Restore original server connection: %s:%s -> %s:%s" % (
            self.c.server_conn.address.host,
            self.c.server_conn.address.port,
            self._backup_server_conn.address.host,
            self._backup_server_conn.address.port
        ), "debug")

        self.c.del_server_connection()
        self.c.server_conn = self._backup_server_conn
        del self._backup_server_conn
########NEW FILE########
__FILENAME__ = tcp
from __future__ import absolute_import
import select, socket
from cStringIO import StringIO
from .primitives import ProtocolHandler


class TCPHandler(ProtocolHandler):
    """
    TCPHandler acts as a generic TCP forwarder.
    Data will be .log()ed, but not stored any further.
    """
    def handle_messages(self):
        self.c.establish_server_connection()
        conns = [self.c.client_conn.rfile, self.c.server_conn.rfile]
        while not self.c.close:
            r, _, _ = select.select(conns, [], [], 10)
            for rfile in r:
                if self.c.client_conn.rfile == rfile:
                    src, dst = self.c.client_conn, self.c.server_conn
                    direction = "-> tcp ->"
                    dst_str = "%s:%s" % self.c.server_conn.address()[:2]
                else:
                    dst, src = self.c.client_conn, self.c.server_conn
                    direction = "<- tcp <-"
                    dst_str = "client"

                data = StringIO()
                while range(4096):
                    # Do non-blocking select() to see if there is further data on in the buffer.
                    r, _, _ = select.select([rfile], [], [], 0)
                    if len(r):
                        d = rfile.read(1)
                        if d == "":  # connection closed
                            break
                        data.write(d)
                        # OpenSSL Connections have an internal buffer that might
                        # contain data altough everything is read from the socket.
                        # Thankfully, connection.pending() returns the amount of
                        # bytes in this buffer, so we can read it completely at
                        # once.
                        if src.ssl_established:
                            data.write(rfile.read(src.connection.pending()))
                    else:  # no data left, but not closed yet
                        break
                data = data.getvalue()

                if data == "":  # no data received, rfile is closed
                    self.c.log("Close writing connection to %s" % dst_str, "debug")
                    conns.remove(rfile)
                    if dst.ssl_established:
                        dst.connection.shutdown()
                    else:
                        dst.connection.shutdown(socket.SHUT_WR)
                    if len(conns) == 0:
                        self.c.close = True
                    break

                self.c.log("%s %s\r\n%s" % (direction, dst_str, data), "debug")
                dst.wfile.write(data)
                dst.wfile.flush()

########NEW FILE########
__FILENAME__ = config
from __future__ import absolute_import
import os
from .. import utils, platform
from netlib import http_auth, certutils
from .primitives import ConstUpstreamServerResolver, TransparentUpstreamServerResolver

TRANSPARENT_SSL_PORTS = [443, 8443]
CONF_BASENAME = "mitmproxy"
CONF_DIR = "~/.mitmproxy"


class ProxyConfig:
    def __init__(self, confdir=CONF_DIR, clientcerts=None,
                       no_upstream_cert=False, body_size_limit=None, get_upstream_server=None,
                       http_form_in="absolute", http_form_out="relative", authenticator=None,
                       ciphers=None, certs=[], certforward = False
                ):
        self.ciphers = ciphers
        self.clientcerts = clientcerts
        self.no_upstream_cert = no_upstream_cert
        self.body_size_limit = body_size_limit
        self.get_upstream_server = get_upstream_server
        self.http_form_in = http_form_in
        self.http_form_out = http_form_out
        self.authenticator = authenticator
        self.confdir = os.path.expanduser(confdir)
        self.certstore = certutils.CertStore.from_store(self.confdir, CONF_BASENAME)
        for spec, cert in certs:
            self.certstore.add_cert_file(spec, cert)
        self.certforward = certforward


def process_proxy_options(parser, options):
    body_size_limit = utils.parse_size(options.body_size_limit)

    c = 0
    http_form_in, http_form_out = "absolute", "relative"
    get_upstream_server = None
    if options.transparent_proxy:
        c += 1
        if not platform.resolver:
            return parser.error("Transparent mode not supported on this platform.")
        get_upstream_server = TransparentUpstreamServerResolver(platform.resolver(), TRANSPARENT_SSL_PORTS)
        http_form_in, http_form_out = "relative", "relative"
    if options.reverse_proxy:
        c += 1
        get_upstream_server = ConstUpstreamServerResolver(options.reverse_proxy)
        http_form_in, http_form_out = "relative", "relative"
    if options.upstream_proxy:
        c += 1
        get_upstream_server = ConstUpstreamServerResolver(options.upstream_proxy)
        http_form_in, http_form_out = "absolute", "absolute"
    if options.manual_destination_server:
        c += 1
        get_upstream_server = ConstUpstreamServerResolver(options.manual_destination_server)
    if c > 1:
        return parser.error("Transparent mode, reverse mode, upstream proxy mode and "
                            "specification of an upstream server are mutually exclusive.")
    if options.http_form_in:
        http_form_in = options.http_form_in
    if options.http_form_out:
        http_form_out = options.http_form_out

    if options.clientcerts:
        options.clientcerts = os.path.expanduser(options.clientcerts)
        if not os.path.exists(options.clientcerts) or not os.path.isdir(options.clientcerts):
            return parser.error(
                "Client certificate directory does not exist or is not a directory: %s" % options.clientcerts
            )

    if (options.auth_nonanonymous or options.auth_singleuser or options.auth_htpasswd):
        if options.auth_singleuser:
            if len(options.auth_singleuser.split(':')) != 2:
                return parser.error("Invalid single-user specification. Please use the format username:password")
            username, password = options.auth_singleuser.split(':')
            password_manager = http_auth.PassManSingleUser(username, password)
        elif options.auth_nonanonymous:
            password_manager = http_auth.PassManNonAnon()
        elif options.auth_htpasswd:
            try:
                password_manager = http_auth.PassManHtpasswd(options.auth_htpasswd)
            except ValueError, v:
                return parser.error(v.message)
        authenticator = http_auth.BasicProxyAuth(password_manager, "mitmproxy")
    else:
        authenticator = http_auth.NullProxyAuth(None)

    certs = []
    for i in options.certs:
        parts = i.split("=", 1)
        if len(parts) == 1:
            parts = ["*", parts[0]]
        parts[1] = os.path.expanduser(parts[1])
        if not os.path.exists(parts[1]):
            parser.error("Certificate file does not exist: %s"%parts[1])
        certs.append(parts)

    return ProxyConfig(
        clientcerts = options.clientcerts,
        body_size_limit = body_size_limit,
        no_upstream_cert = options.no_upstream_cert,
        get_upstream_server = get_upstream_server,
        confdir = options.confdir,
        http_form_in = http_form_in,
        http_form_out = http_form_out,
        authenticator = authenticator,
        ciphers = options.ciphers,
        certs = certs,
        certforward = options.certforward,
    )


def ssl_option_group(parser):
    group = parser.add_argument_group("SSL")
    group.add_argument(
        "--cert", dest='certs', default=[], type=str,
        metavar = "SPEC", action="append",
        help='Add an SSL certificate. SPEC is of the form "[domain=]path". '\
             'The domain may include a wildcard, and is equal to "*" if not specified. '\
             'The file at path is a certificate in PEM format. If a private key is included in the PEM, '\
             'it is used, else the default key in the conf dir is used. Can be passed multiple times.'
    )
    group.add_argument(
        "--client-certs", action="store",
        type=str, dest="clientcerts", default=None,
        help="Client certificate directory."
    )
    group.add_argument(
        "--ciphers", action="store",
        type=str, dest="ciphers", default=None,
        help="SSL cipher specification."
    )
    group.add_argument(
        "--cert-forward", action="store_true",
        dest="certforward", default=False,
        help="Simply forward SSL certificates from upstream."
    )
    group.add_argument(
        "--no-upstream-cert", default=False,
        action="store_true", dest="no_upstream_cert",
        help="Don't connect to upstream server to look up certificate details."
    )
########NEW FILE########
__FILENAME__ = connection
from __future__ import absolute_import
import copy
import os
from netlib import tcp, certutils
from .. import stateobject, utils
from .primitives import ProxyError


class ClientConnection(tcp.BaseHandler, stateobject.SimpleStateObject):
    def __init__(self, client_connection, address, server):
        if client_connection:  # Eventually, this object is restored from state. We don't have a connection then.
            tcp.BaseHandler.__init__(self, client_connection, address, server)
        else:
            self.connection = None
            self.server = None
            self.wfile = None
            self.rfile = None
            self.address = None
            self.clientcert = None

        self.timestamp_start = utils.timestamp()
        self.timestamp_end = None
        self.timestamp_ssl_setup = None

    _stateobject_attributes = dict(
        timestamp_start=float,
        timestamp_end=float,
        timestamp_ssl_setup=float
    )

    def _get_state(self):
        d = super(ClientConnection, self)._get_state()
        d.update(
            address={"address": self.address(), "use_ipv6": self.address.use_ipv6},
            clientcert=self.cert.to_pem() if self.clientcert else None
        )
        return d

    def _load_state(self, state):
        super(ClientConnection, self)._load_state(state)
        self.address = tcp.Address(**state["address"]) if state["address"] else None
        self.clientcert = certutils.SSLCert.from_pem(state["clientcert"]) if state["clientcert"] else None

    def copy(self):
        return copy.copy(self)

    def send(self, message):
        self.wfile.write(message)
        self.wfile.flush()

    @classmethod
    def _from_state(cls, state):
        f = cls(None, tuple(), None)
        f._load_state(state)
        return f

    def convert_to_ssl(self, *args, **kwargs):
        tcp.BaseHandler.convert_to_ssl(self, *args, **kwargs)
        self.timestamp_ssl_setup = utils.timestamp()

    def finish(self):
        tcp.BaseHandler.finish(self)
        self.timestamp_end = utils.timestamp()


class ServerConnection(tcp.TCPClient, stateobject.SimpleStateObject):
    def __init__(self, address, priority):
        tcp.TCPClient.__init__(self, address)
        self.priority = priority

        self.peername = None
        self.timestamp_start = None
        self.timestamp_end = None
        self.timestamp_tcp_setup = None
        self.timestamp_ssl_setup = None

    _stateobject_attributes = dict(
        peername=tuple,
        timestamp_start=float,
        timestamp_end=float,
        timestamp_tcp_setup=float,
        timestamp_ssl_setup=float,
        address=tcp.Address,
        source_address=tcp.Address,
        cert=certutils.SSLCert,
        ssl_established=bool,
        sni=str
    )

    def _get_state(self):
        d = super(ServerConnection, self)._get_state()
        d.update(
            address={"address": self.address(), "use_ipv6": self.address.use_ipv6},
            source_address= {"address": self.source_address(),
                             "use_ipv6": self.source_address.use_ipv6} if self.source_address else None,
            cert=self.cert.to_pem() if self.cert else None
        )
        return d

    def _load_state(self, state):
        super(ServerConnection, self)._load_state(state)

        self.address = tcp.Address(**state["address"]) if state["address"] else None
        self.source_address = tcp.Address(**state["source_address"]) if state["source_address"] else None
        self.cert = certutils.SSLCert.from_pem(state["cert"]) if state["cert"] else None

    @classmethod
    def _from_state(cls, state):
        f = cls(tuple(), None)
        f._load_state(state)
        return f

    def copy(self):
        return copy.copy(self)

    def connect(self):
        self.timestamp_start = utils.timestamp()
        tcp.TCPClient.connect(self)
        self.peername = self.connection.getpeername()
        self.timestamp_tcp_setup = utils.timestamp()

    def send(self, message):
        self.wfile.write(message)
        self.wfile.flush()

    def establish_ssl(self, clientcerts, sni):
        clientcert = None
        if clientcerts:
            path = os.path.join(clientcerts, self.address.host.encode("idna")) + ".pem"
            if os.path.exists(path):
                clientcert = path
        try:
            self.convert_to_ssl(cert=clientcert, sni=sni)
            self.timestamp_ssl_setup = utils.timestamp()
        except tcp.NetLibError, v:
            raise ProxyError(400, str(v))

    def finish(self):
        tcp.TCPClient.finish(self)
        self.timestamp_end = utils.timestamp()
########NEW FILE########
__FILENAME__ = primitives
from __future__ import absolute_import

class ProxyError(Exception):
    def __init__(self, code, msg, headers=None):
        self.code, self.msg, self.headers = code, msg, headers

    def __str__(self):
        return "ProxyError(%s, %s)" % (self.code, self.msg)


class ConnectionTypeChange(Exception):
    """
    Gets raised if the connection type has been changed (e.g. after HTTP/1.1 101 Switching Protocols).
    It's up to the raising ProtocolHandler to specify the new conntype before raising the exception.
    """
    pass


class ProxyServerError(Exception):
    pass


class UpstreamServerResolver(object):
    def __call__(self, conn):
        """
        Returns the address of the server to connect to.
        """
        raise NotImplementedError  # pragma: nocover


class ConstUpstreamServerResolver(UpstreamServerResolver):
    def __init__(self, dst):
        self.dst = dst

    def __call__(self, conn):
        return self.dst


class TransparentUpstreamServerResolver(UpstreamServerResolver):
    def __init__(self, resolver, sslports):
        self.resolver = resolver
        self.sslports = sslports

    def __call__(self, conn):
        dst = self.resolver.original_addr(conn)
        if not dst:
            raise ProxyError(502, "Transparent mode failure: could not resolve original destination.")

        if dst[1] in self.sslports:
            ssl = True
        else:
            ssl = False
        return [ssl, ssl] + list(dst)


class AddressPriority(object):
    """
    Enum that signifies the priority of the given address when choosing the destination host.
    Higher is better (None < i)
    """
    MANUALLY_CHANGED = 3
    """user changed the target address in the ui"""
    FROM_SETTINGS = 2
    """upstream server from arguments (reverse proxy, upstream proxy or from transparent resolver)"""
    FROM_PROTOCOL = 1
    """derived from protocol (e.g. absolute-form http requests)"""


class Log:
    def __init__(self, msg, level="info"):
        self.msg = msg
        self.level = level
########NEW FILE########
__FILENAME__ = server
from __future__ import absolute_import

import socket
from OpenSSL import SSL

from netlib import tcp
from .primitives import ProxyServerError, Log, ProxyError, ConnectionTypeChange, \
    AddressPriority
from .connection import ClientConnection, ServerConnection
from ..protocol.handle import handle_messages, handle_error
from .. import version


class DummyServer:
    bound = False

    def __init__(self, config):
        self.config = config

    def start_slave(self, *args):
        pass

    def shutdown(self):
        pass


class ProxyServer(tcp.TCPServer):
    allow_reuse_address = True
    bound = True

    def __init__(self, config, port, host='', server_version=version.NAMEVERSION):
        """
            Raises ProxyServerError if there's a startup problem.
        """
        self.config = config
        self.server_version = server_version
        try:
            tcp.TCPServer.__init__(self, (host, port))
        except socket.error, v:
            raise ProxyServerError('Error starting proxy server: ' + v.strerror)
        self.channel = None

    def start_slave(self, klass, channel):
        slave = klass(channel, self)
        slave.start()

    def set_channel(self, channel):
        self.channel = channel

    def handle_client_connection(self, conn, client_address):
        h = ConnectionHandler(self.config, conn, client_address, self, self.channel,
                              self.server_version)
        h.handle()
        h.finish()


class ConnectionHandler:
    def __init__(self, config, client_connection, client_address, server, channel,
                 server_version):
        self.config = config
        """@type: libmproxy.proxy.config.ProxyConfig"""
        self.client_conn = ClientConnection(client_connection, client_address, server)
        """@type: libmproxy.proxy.connection.ClientConnection"""
        self.server_conn = None
        """@type: libmproxy.proxy.connection.ServerConnection"""
        self.channel, self.server_version = channel, server_version

        self.close = False
        self.conntype = None
        self.sni = None

    def handle(self):
        self.log("clientconnect", "info")
        self.channel.ask("clientconnect", self)

        self.determine_conntype()

        try:
            # Can we already identify the target server and connect to it?
            if self.config.get_upstream_server:
                upstream_info = self.config.get_upstream_server(
                    self.client_conn.connection)
                self.set_server_address(upstream_info[2:], AddressPriority.FROM_SETTINGS)
                client_ssl, server_ssl = upstream_info[:2]
                if client_ssl or server_ssl:
                    self.establish_server_connection()
                    self.establish_ssl(client=client_ssl, server=server_ssl)

            while not self.close:
                try:
                    handle_messages(self.conntype, self)
                except ConnectionTypeChange:
                    self.log("Connection Type Changed: %s" % self.conntype, "info")
                    continue

        except (ProxyError, tcp.NetLibError), e:
            handle_error(self.conntype, self, e)
        except Exception, e:
            import traceback, sys

            self.log(traceback.format_exc(), "error")
            print >> sys.stderr, traceback.format_exc()
            print >> sys.stderr, "mitmproxy has crashed!"
            print >> sys.stderr, "Please lodge a bug report at: https://github.com/mitmproxy/mitmproxy"
            raise e

        self.del_server_connection()
        self.log("clientdisconnect", "info")
        self.channel.tell("clientdisconnect", self)

    def del_server_connection(self):
        """
        Deletes (and closes) an existing server connection.
        """
        if self.server_conn and self.server_conn.connection:
            self.server_conn.finish()
            self.log("serverdisconnect", "debug", ["%s:%s" % (self.server_conn.address.host,
                                                              self.server_conn.address.port)])
            self.channel.tell("serverdisconnect", self)
        self.server_conn = None
        self.sni = None

    def determine_conntype(self):
        #TODO: Add ruleset to select correct protocol depending on mode/target port etc.
        self.conntype = "http"

    def set_server_address(self, address, priority):
        """
        Sets a new server address with the given priority.
        Does not re-establish either connection or SSL handshake.
        """
        address = tcp.Address.wrap(address)

        if self.server_conn:
            if self.server_conn.priority > priority:
                self.log("Attempt to change server address, "
                         "but priority is too low (is: %s, got: %s)" % (
                             self.server_conn.priority, priority), "info")
                return
            if self.server_conn.address == address:
                self.server_conn.priority = priority  # Possibly increase priority
                return

            self.del_server_connection()

        self.log("Set new server address: %s:%s" % (address.host, address.port), "debug")
        self.server_conn = ServerConnection(address, priority)

    def establish_server_connection(self):
        """
        Establishes a new server connection.
        If there is already an existing server connection, the function returns immediately.
        """
        if self.server_conn.connection:
            return
        self.log("serverconnect", "debug", ["%s:%s" % self.server_conn.address()[:2]])
        self.channel.tell("serverconnect", self)
        try:
            self.server_conn.connect()
        except tcp.NetLibError, v:
            raise ProxyError(502, v)

    def establish_ssl(self, client=False, server=False):
        """
        Establishes SSL on the existing connection(s) to the server or the client,
        as specified by the parameters. If the target server is on the pass-through list,
        the conntype attribute will be changed and a ConnTypeChanged exception will be raised.
        """
        # TODO: Implement SSL pass-through handling and change conntype
        passthrough = [
            # "echo.websocket.org",
            # "174.129.224.73"  # echo.websocket.org, transparent mode
        ]
        if self.server_conn.address.host in passthrough or self.sni in passthrough:
            self.conntype = "tcp"
            raise ConnectionTypeChange

        # Logging
        if client or server:
            subs = []
            if client:
                subs.append("with client")
            if server:
                subs.append("with server (sni: %s)" % self.sni)
            self.log("Establish SSL", "debug", subs)

        if server:
            if self.server_conn.ssl_established:
                raise ProxyError(502, "SSL to Server already established.")
            self.establish_server_connection()  # make sure there is a server connection.
            self.server_conn.establish_ssl(self.config.clientcerts, self.sni)
        if client:
            if self.client_conn.ssl_established:
                raise ProxyError(502, "SSL to Client already established.")
            cert, key = self.find_cert()
            self.client_conn.convert_to_ssl(
                cert, key,
                handle_sni=self.handle_sni,
                cipher_list=self.config.ciphers,
                dhparams=self.config.certstore.dhparams
            )

    def server_reconnect(self, no_ssl=False):
        address = self.server_conn.address
        had_ssl = self.server_conn.ssl_established
        priority = self.server_conn.priority
        sni = self.sni
        self.log("(server reconnect follows)", "debug")
        self.del_server_connection()
        self.set_server_address(address, priority)
        self.establish_server_connection()
        if had_ssl and not no_ssl:
            self.sni = sni
            self.establish_ssl(server=True)

    def finish(self):
        self.client_conn.finish()

    def log(self, msg, level, subs=()):
        msg = [
            "%s:%s: %s" % (self.client_conn.address.host, self.client_conn.address.port, msg)
        ]
        for i in subs:
            msg.append("  -> " + i)
        msg = "\n".join(msg)
        self.channel.tell("log", Log(msg, level))

    def find_cert(self):
        if self.config.certforward and self.server_conn.ssl_established:
            return self.server_conn.cert, self.config.certstore.gen_pkey(self.server_conn.cert)
        else:
            host = self.server_conn.address.host
            sans = []
            if not self.config.no_upstream_cert and self.server_conn.ssl_established:
                upstream_cert = self.server_conn.cert
                if upstream_cert.cn:
                    host = upstream_cert.cn.decode("utf8").encode("idna")
                sans = upstream_cert.altnames

            ret = self.config.certstore.get_cert(host, sans)
            if not ret:
                raise ProxyError(502, "Unable to generate dummy cert.")
            return ret

    def handle_sni(self, connection):
        """
        This callback gets called during the SSL handshake with the client.
        The client has just sent the Sever Name Indication (SNI). We now connect upstream to
        figure out which certificate needs to be served.
        """
        try:
            sn = connection.get_servername()
            if sn and sn != self.sni:
                self.sni = sn.decode("utf8").encode("idna")
                self.log("SNI received: %s" % self.sni, "debug")
                self.server_reconnect()  # reconnect to upstream server with SNI
                # Now, change client context to reflect changed certificate:
                cert, key = self.find_cert()
                new_context = self.client_conn._create_ssl_context(
                    cert, key,
                    method=SSL.TLSv1_METHOD,
                    cipher_list=self.config.ciphers,
                    dhparams=self.config.certstore.dhparams
                )
                connection.set_context(new_context)
        # An unhandled exception in this method will core dump PyOpenSSL, so
        # make dang sure it doesn't happen.
        except Exception, e:  # pragma: no cover
            import traceback
            self.log("Error in handle_sni:\r\n" + traceback.format_exc(), "error")
########NEW FILE########
__FILENAME__ = script
from __future__ import absolute_import
import os, traceback, threading, shlex
from . import controller

class ScriptError(Exception):
    pass


class ScriptContext:
    def __init__(self, master):
        self._master = master

    def log(self, message, level="info"):
        """
            Logs an event.

            By default, only events with level "error" get displayed. This can be controlled with the "-v" switch.
            How log messages are handled depends on the front-end. mitmdump will print them to stdout,
            mitmproxy sends output to the eventlog for display ("e" keyboard shortcut).
        """
        self._master.add_event(message, level)

    def duplicate_flow(self, f):
        """
            Returns a duplicate of the specified flow. The flow is also
            injected into the current state, and is ready for editing, replay,
            etc.
        """
        self._master.pause_scripts = True
        f = self._master.duplicate_flow(f)
        self._master.pause_scripts = False
        return f

    def replay_request(self, f):
        """
            Replay the request on the current flow. The response will be added
            to the flow object.
        """
        self._master.replay_request(f)


class Script:
    """
        The instantiator should do something along this vein:

            s = Script(argv, master)
            s.load()
    """
    def __init__(self, command, master):
        self.command = command
        self.argv = self.parse_command(command)
        self.ctx = ScriptContext(master)
        self.ns = None
        self.load()

    @classmethod
    def parse_command(klass, command):
        args = shlex.split(command, posix=(os.name != "nt"))
        args[0] = os.path.expanduser(args[0])
        if not os.path.exists(args[0]):
            raise ScriptError("Command not found.")
        elif not os.path.isfile(args[0]):
            raise ScriptError("Not a file: %s" % args[0])
        return args

    def load(self):
        """
            Loads a module.

            Raises ScriptError on failure, with argument equal to an error
            message that may be a formatted traceback.
        """
        ns = {}
        try:
            execfile(self.argv[0], ns, ns)
        except Exception, v:
            raise ScriptError(traceback.format_exc(v))
        self.ns = ns
        r = self.run("start", self.argv)
        if not r[0] and r[1]:
            raise ScriptError(r[1][1])

    def unload(self):
        return self.run("done")

    def run(self, name, *args, **kwargs):
        """
            Runs a plugin method.

            Returns:

                (True, retval) on success.
                (False, None) on nonexistent method.
                (False, (exc, traceback string)) if there was an exception.
        """
        f = self.ns.get(name)
        if f:
            try:
                return (True, f(self.ctx, *args, **kwargs))
            except Exception, v:
                return (False, (v, traceback.format_exc(v)))
        else:
            return (False, None)


def _handle_concurrent_reply(fn, o, args=[], kwargs={}):
    reply = o.reply
    o.reply = controller.DummyReply()
    if hasattr(reply, "q"):
        o.reply.q = reply.q
    def run():
        fn(*args, **kwargs)
        reply()
    threading.Thread(target=run, name="ScriptThread").start()


def concurrent(fn):
    if fn.func_name in ["request", "response", "error"]:
        def _concurrent(ctx, flow):
            r = getattr(flow, fn.func_name)
            _handle_concurrent_reply(fn, r, [ctx, flow])
        return _concurrent
    elif fn.func_name in ["clientconnect", "serverconnect", "clientdisconnect"]:
        def _concurrent(ctx, conn):
            _handle_concurrent_reply(fn, conn, [ctx, conn])
        return _concurrent
    raise NotImplementedError("Concurrent decorator not supported for this method.")

########NEW FILE########
__FILENAME__ = stateobject
from __future__ import absolute_import

class StateObject(object):
    def _get_state(self):
        raise NotImplementedError  # pragma: nocover

    def _load_state(self, state):
        raise NotImplementedError  # pragma: nocover

    @classmethod
    def _from_state(cls, state):
        raise NotImplementedError  # pragma: nocover
        # Usually, this function roughly equals to the following code:
        # f = cls()
        # f._load_state(state)
        # return f

    def __eq__(self, other):
        try:
            return self._get_state() == other._get_state()
        except AttributeError:  # we may compare with something that's not a StateObject
            return False


class SimpleStateObject(StateObject):
    """
    A StateObject with opionated conventions that tries to keep everything DRY.

    Simply put, you agree on a list of attributes and their type.
    Attributes can either be primitive types(str, tuple, bool, ...) or StateObject instances themselves.
    SimpleStateObject uses this information for the default _get_state(), _from_state(s) and _load_state(s) methods.
    Overriding _get_state or _load_state to add custom adjustments is always possible.
    """

    _stateobject_attributes = None  # none by default to raise an exception if definition was forgotten
    """
    An attribute-name -> class-or-type dict containing all attributes that should be serialized
    If the attribute is a class, this class must be a subclass of StateObject.
    """

    def _get_state(self):
        return {attr: self._get_state_attr(attr, cls)
                for attr, cls in self._stateobject_attributes.iteritems()}

    def _get_state_attr(self, attr, cls):
        """
        helper for _get_state.
        returns the value of the given attribute
        """
        val = getattr(self, attr)
        if hasattr(val, "_get_state"):
            return val._get_state()
        else:
            return val

    def _load_state(self, state):
        for attr, cls in self._stateobject_attributes.iteritems():
            self._load_state_attr(attr, cls, state)

    def _load_state_attr(self, attr, cls, state):
        """
        helper for _load_state.
        loads the given attribute from the state.
        """
        if state.get(attr, None) is None:
            setattr(self, attr, None)
            return

        curr = getattr(self, attr)
        if hasattr(curr, "_load_state"):
            curr._load_state(state[attr])
        elif hasattr(cls, "_from_state"):
            setattr(self, attr, cls._from_state(state[attr]))
        else:
            setattr(self, attr, cls(state[attr]))
########NEW FILE########
__FILENAME__ = tnetstring
# imported from the tnetstring project: https://github.com/rfk/tnetstring
#
# Copyright (c) 2011 Ryan Kelly
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
tnetstring:  data serialization using typed netstrings
======================================================


This is a data serialization library. It's a lot like JSON but it uses a
new syntax called "typed netstrings" that Zed has proposed for use in the
Mongrel2 webserver.  It's designed to be simpler and easier to implement
than JSON, with a happy consequence of also being faster in many cases.

An ordinary netstring is a blob of data prefixed with its length and postfixed
with a sanity-checking comma.  The string "hello world" encodes like this::

    11:hello world,

Typed netstrings add other datatypes by replacing the comma with a type tag.
Here's the integer 12345 encoded as a tnetstring::

    5:12345#

And here's the list [12345,True,0] which mixes integers and bools::

    19:5:12345#4:true!1:0#]

Simple enough?  This module gives you the following functions:

    :dump:    dump an object as a tnetstring to a file
    :dumps:   dump an object as a tnetstring to a string
    :load:    load a tnetstring-encoded object from a file
    :loads:   load a tnetstring-encoded object from a string
    :pop:     pop a tnetstring-encoded object from the front of a string

Note that since parsing a tnetstring requires reading all the data into memory
at once, there's no efficiency gain from using the file-based versions of these
functions.  They're only here so you can use load() to read precisely one
item from a file or socket without consuming any extra data.

By default tnetstrings work only with byte strings, not unicode.  If you want
unicode strings then pass an optional encoding to the various functions,
like so::

    >>> print repr(tnetstring.loads("2:\\xce\\xb1,"))
    '\\xce\\xb1'
    >>>
    >>> print repr(tnetstring.loads("2:\\xce\\xb1,","utf8"))
    u'\u03b1'

"""

__ver_major__ = 0
__ver_minor__ = 2
__ver_patch__ = 0
__ver_sub__ = ""
__version__ = "%d.%d.%d%s" % (__ver_major__,__ver_minor__,__ver_patch__,__ver_sub__)


from collections import deque


def dumps(value,encoding=None):
    """dumps(object,encoding=None) -> string

    This function dumps a python object as a tnetstring.
    """
    #  This uses a deque to collect output fragments in reverse order,
    #  then joins them together at the end.  It's measurably faster
    #  than creating all the intermediate strings.
    #  If you're reading this to get a handle on the tnetstring format,
    #  consider the _gdumps() function instead; it's a standard top-down
    #  generator that's simpler to understand but much less efficient.
    q = deque()
    _rdumpq(q,0,value,encoding)
    return "".join(q)


def dump(value,file,encoding=None):
    """dump(object,file,encoding=None)

    This function dumps a python object as a tnetstring and writes it to
    the given file.
    """
    file.write(dumps(value,encoding))
    file.flush()


def _rdumpq(q,size,value,encoding=None):
    """Dump value as a tnetstring, to a deque instance, last chunks first.

    This function generates the tnetstring representation of the given value,
    pushing chunks of the output onto the given deque instance.  It pushes
    the last chunk first, then recursively generates more chunks.

    When passed in the current size of the string in the queue, it will return
    the new size of the string in the queue.

    Operating last-chunk-first makes it easy to calculate the size written
    for recursive structures without having to build their representation as
    a string.  This is measurably faster than generating the intermediate
    strings, especially on deeply nested structures.
    """
    write = q.appendleft
    if value is None:
        write("0:~")
        return size + 3
    if value is True:
        write("4:true!")
        return size + 7
    if value is False:
        write("5:false!")
        return size + 8
    if isinstance(value,(int,long)):
        data = str(value)
        ldata = len(data)
        span = str(ldata)
        write("#")
        write(data)
        write(":")
        write(span)
        return size + 2 + len(span) + ldata
    if isinstance(value,(float,)):
        #  Use repr() for float rather than str().
        #  It round-trips more accurately.
        #  Probably unnecessary in later python versions that
        #  use David Gay's ftoa routines.
        data = repr(value)
        ldata = len(data)
        span = str(ldata)
        write("^")
        write(data)
        write(":")
        write(span)
        return size + 2 + len(span) + ldata
    if isinstance(value,str):
        lvalue = len(value)
        span = str(lvalue)
        write(",")
        write(value)
        write(":")
        write(span)
        return size + 2 + len(span) + lvalue
    if isinstance(value,(list,tuple,)):
        write("]")
        init_size = size = size + 1
        for item in reversed(value):
            size = _rdumpq(q,size,item,encoding)
        span = str(size - init_size)
        write(":")
        write(span)
        return size + 1 + len(span)
    if isinstance(value,dict):
        write("}")
        init_size = size = size + 1
        for (k,v) in value.iteritems():
            size = _rdumpq(q,size,v,encoding)
            size = _rdumpq(q,size,k,encoding)
        span = str(size - init_size)
        write(":")
        write(span)
        return size + 1 + len(span)
    if isinstance(value,unicode):
        if encoding is None:
            raise ValueError("must specify encoding to dump unicode strings")
        value = value.encode(encoding)
        lvalue = len(value)
        span = str(lvalue)
        write(",")
        write(value)
        write(":")
        write(span)
        return size + 2 + len(span) + lvalue
    raise ValueError("unserializable object")


def _gdumps(value,encoding):
    """Generate fragments of value dumped as a tnetstring.

    This is the naive dumping algorithm, implemented as a generator so that
    it's easy to pass to "".join() without building a new list.

    This is mainly here for comparison purposes; the _rdumpq version is
    measurably faster as it doesn't have to build intermediate strins.
    """
    if value is None:
        yield "0:~"
    elif value is True:
        yield "4:true!"
    elif value is False:
        yield "5:false!"
    elif isinstance(value,(int,long)):
        data = str(value)
        yield str(len(data))
        yield ":"
        yield data
        yield "#"
    elif isinstance(value,(float,)):
        data = repr(value)
        yield str(len(data))
        yield ":"
        yield data
        yield "^"
    elif isinstance(value,(str,)):
        yield str(len(value))
        yield ":"
        yield value
        yield ","
    elif isinstance(value,(list,tuple,)):
        sub = []
        for item in value:
            sub.extend(_gdumps(item))
        sub = "".join(sub)
        yield str(len(sub))
        yield ":"
        yield sub
        yield "]"
    elif isinstance(value,(dict,)):
        sub = []
        for (k,v) in value.iteritems():
            sub.extend(_gdumps(k))
            sub.extend(_gdumps(v))
        sub = "".join(sub)
        yield str(len(sub))
        yield ":"
        yield sub
        yield "}"
    elif isinstance(value,(unicode,)):
        if encoding is None:
            raise ValueError("must specify encoding to dump unicode strings")
        value = value.encode(encoding)
        yield str(len(value))
        yield ":"
        yield value
        yield ","
    else:
        raise ValueError("unserializable object")


def loads(string,encoding=None):
    """loads(string,encoding=None) -> object

    This function parses a tnetstring into a python object.
    """
    #  No point duplicating effort here.  In the C-extension version,
    #  loads() is measurably faster then pop() since it can avoid
    #  the overhead of building a second string.
    return pop(string,encoding)[0]


def load(file,encoding=None):
    """load(file,encoding=None) -> object

    This function reads a tnetstring from a file and parses it into a
    python object.  The file must support the read() method, and this
    function promises not to read more data than necessary.
    """
    #  Read the length prefix one char at a time.
    #  Note that the netstring spec explicitly forbids padding zeros.
    c = file.read(1)
    if not c.isdigit():
        raise ValueError("not a tnetstring: missing or invalid length prefix")
    datalen = ord(c) - ord("0")
    c = file.read(1)
    if datalen != 0:
        while c.isdigit():
            datalen = (10 * datalen) + (ord(c) - ord("0"))
            if datalen > 999999999:
                errmsg = "not a tnetstring: absurdly large length prefix"
                raise ValueError(errmsg)
            c = file.read(1)
    if c != ":":
        raise ValueError("not a tnetstring: missing or invalid length prefix")
    #  Now we can read and parse the payload.
    #  This repeats the dispatch logic of pop() so we can avoid
    #  re-constructing the outermost tnetstring.
    data = file.read(datalen)
    if len(data) != datalen:
        raise ValueError("not a tnetstring: length prefix too big")
    type = file.read(1)
    if type == ",":
        if encoding is not None:
            return data.decode(encoding)
        return data
    if type == "#":
        try:
            return int(data)
        except ValueError:
            raise ValueError("not a tnetstring: invalid integer literal")
    if type == "^":
        try:
            return float(data)
        except ValueError:
            raise ValueError("not a tnetstring: invalid float literal")
    if type == "!":
        if data == "true":
            return True
        elif data == "false":
            return False
        else:
            raise ValueError("not a tnetstring: invalid boolean literal")
    if type == "~":
        if data:
            raise ValueError("not a tnetstring: invalid null literal")
        return None
    if type == "]":
        l = []
        while data:
            (item,data) = pop(data,encoding)
            l.append(item)
        return l
    if type == "}":
        d = {}
        while data:
            (key,data) = pop(data,encoding)
            (val,data) = pop(data,encoding)
            d[key] = val
        return d
    raise ValueError("unknown type tag")



def pop(string,encoding=None):
    """pop(string,encoding=None) -> (object, remain)

    This function parses a tnetstring into a python object.
    It returns a tuple giving the parsed object and a string
    containing any unparsed data from the end of the string.
    """
    #  Parse out data length, type and remaining string.
    try:
        (dlen,rest) = string.split(":",1)
        dlen = int(dlen)
    except ValueError:
        raise ValueError("not a tnetstring: missing or invalid length prefix")
    try:
        (data,type,remain) = (rest[:dlen],rest[dlen],rest[dlen+1:])
    except IndexError:
        #  This fires if len(rest) < dlen, meaning we don't need
        #  to further validate that data is the right length.
        raise ValueError("not a tnetstring: invalid length prefix")
    #  Parse the data based on the type tag.
    if type == ",":
        if encoding is not None:
            return (data.decode(encoding),remain)
        return (data,remain)
    if type == "#":
        try:
            return (int(data),remain)
        except ValueError:
            raise ValueError("not a tnetstring: invalid integer literal")
    if type == "^":
        try:
            return (float(data),remain)
        except ValueError:
            raise ValueError("not a tnetstring: invalid float literal")
    if type == "!":
        if data == "true":
            return (True,remain)
        elif data == "false":
            return (False,remain)
        else:
            raise ValueError("not a tnetstring: invalid boolean literal")
    if type == "~":
        if data:
            raise ValueError("not a tnetstring: invalid null literal")
        return (None,remain)
    if type == "]":
        l = []
        while data:
            (item,data) = pop(data,encoding)
            l.append(item)
        return (l,remain)
    if type == "}":
        d = {}
        while data:
            (key,data) = pop(data,encoding)
            (val,data) = pop(data,encoding)
            d[key] = val
        return (d,remain)
    raise ValueError("unknown type tag")

########NEW FILE########
__FILENAME__ = utils
from __future__ import absolute_import
import os, datetime, urllib, re
import time, functools, cgi
import json

def timestamp():
    """
        Returns a serializable UTC timestamp.
    """
    return time.time()


def format_timestamp(s):
    s = time.localtime(s)
    d = datetime.datetime.fromtimestamp(time.mktime(s))
    return d.strftime("%Y-%m-%d %H:%M:%S")


def isBin(s):
    """
        Does this string have any non-ASCII characters?
    """
    for i in s:
        i = ord(i)
        if i < 9:
            return True
        elif i > 13 and i < 32:
            return True
        elif i > 126:
            return True
    return False


def isXML(s):
    for i in s:
        if i in "\n \t":
            continue
        elif i == "<":
            return True
        else:
            return False


def pretty_json(s):
    try:
        p = json.loads(s)
    except ValueError:
        return None
    return json.dumps(p, sort_keys=True, indent=4).split("\n")


def urldecode(s):
    """
        Takes a urlencoded string and returns a list of (key, value) tuples.
    """
    return cgi.parse_qsl(s, keep_blank_values=True)


def urlencode(s):
    """
        Takes a list of (key, value) tuples and returns a urlencoded string.
    """
    s = [tuple(i) for i in s]
    return urllib.urlencode(s, False)


def del_all(dict, keys):
    for key in keys:
        if key in dict:
            del dict[key]


def pretty_size(size):
    suffixes = [
        ("B",   2**10),
        ("kB",   2**20),
        ("MB",   2**30),
    ]
    for suf, lim in suffixes:
        if size >= lim:
            continue
        else:
            x = round(size/float(lim/2**10), 2)
            if x == int(x):
                x = int(x)
            return str(x) + suf


class Data:
    def __init__(self, name):
        m = __import__(name)
        dirname, _ = os.path.split(m.__file__)
        self.dirname = os.path.abspath(dirname)

    def path(self, path):
        """
            Returns a path to the package data housed at 'path' under this
            module.Path can be a path to a file, or to a directory.

            This function will raise ValueError if the path does not exist.
        """
        fullpath = os.path.join(self.dirname, path)
        if not os.path.exists(fullpath):
            raise ValueError, "dataPath: %s does not exist."%fullpath
        return fullpath
pkg_data = Data(__name__)


class LRUCache:
    """
        A decorator that implements a self-expiring LRU cache for class
        methods (not functions!).

        Cache data is tracked as attributes on the object itself. There is
        therefore a separate cache for each object instance.
    """
    def __init__(self, size=100):
        self.size = size

    def __call__(self, f):
        cacheName = "_cached_%s"%f.__name__
        cacheListName = "_cachelist_%s"%f.__name__
        size = self.size

        @functools.wraps(f)
        def wrap(self, *args):
            if not hasattr(self, cacheName):
                setattr(self, cacheName, {})
                setattr(self, cacheListName, [])
            cache = getattr(self, cacheName)
            cacheList = getattr(self, cacheListName)
            if cache.has_key(args):
                cacheList.remove(args)
                cacheList.insert(0, args)
                return cache[args]
            else:
                ret = f(self, *args)
                cacheList.insert(0, args)
                cache[args] = ret
                if len(cacheList) > size:
                    d = cacheList.pop()
                    cache.pop(d)
                return ret
        return wrap

def parse_content_type(c):
    """
        A simple parser for content-type values. Returns a (type, subtype,
        parameters) tuple, where type and subtype are strings, and parameters
        is a dict. If the string could not be parsed, return None.

        E.g. the following string:

            text/html; charset=UTF-8

        Returns:

            ("text", "html", {"charset": "UTF-8"})
    """
    parts = c.split(";", 1)
    ts = parts[0].split("/", 1)
    if len(ts) != 2:
        return None
    d = {}
    if len(parts) == 2:
        for i in parts[1].split(";"):
            clause = i.split("=", 1)
            if len(clause) == 2:
                d[clause[0].strip()] = clause[1].strip()
    return ts[0].lower(), ts[1].lower(), d


def hostport(scheme, host, port):
    """
        Returns the host component, with a port specifcation if needed.
    """
    if (port, scheme) in [(80, "http"), (443, "https")]:
        return host
    else:
        return "%s:%s"%(host, port)


def unparse_url(scheme, host, port, path=""):
    """
        Returns a URL string, constructed from the specified compnents.
    """
    return "%s://%s%s"%(scheme, hostport(scheme, host, port), path)


def clean_hanging_newline(t):
    """
        Many editors will silently add a newline to the final line of a
        document (I'm looking at you, Vim). This function fixes this common
        problem at the risk of removing a hanging newline in the rare cases
        where the user actually intends it.
    """
    if t and t[-1] == "\n":
        return t[:-1]
    return t


def parse_size(s):
    """
        Parses a size specification. Valid specifications are:

            123: bytes
            123k: kilobytes
            123m: megabytes
            123g: gigabytes
    """
    if not s:
        return None
    mult = None
    if s[-1].lower() == "k":
        mult = 1024**1
    elif s[-1].lower() == "m":
        mult = 1024**2
    elif s[-1].lower() == "g":
        mult = 1024**3

    if mult:
        s = s[:-1]
    else:
        mult = 1
    try:
        return int(s) * mult
    except ValueError:
        raise ValueError("Invalid size specification: %s"%s)


def safe_subn(pattern, repl, target, *args, **kwargs):
    """
        There are Unicode conversion problems with re.subn. We try to smooth
        that over by casting the pattern and replacement to strings. We really
        need a better solution that is aware of the actual content ecoding.
    """
    return re.subn(str(pattern), str(repl), target, *args, **kwargs)

########NEW FILE########
__FILENAME__ = version
IVERSION = (0, 11)
VERSION = ".".join(str(i) for i in IVERSION)
MINORVERSION = ".".join(str(i) for i in IVERSION[:2])
NAME = "mitmproxy"
NAMEVERSION = NAME + " " + VERSION

########NEW FILE########
__FILENAME__ = mock_urwid
import os, sys, mock
if os.name == "nt":
    m = mock.Mock()
    m.__version__ = "1.1.1"
    m.Widget = mock.Mock
    m.WidgetWrap = mock.Mock
    sys.modules['urwid'] = m
    sys.modules['urwid.util'] = mock.Mock()
########NEW FILE########
__FILENAME__ = a
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--var', type=int)

var = 0
def start(ctx, argv):
    global var
    var = parser.parse_args(argv[1:]).var

def here(ctx):
    global var
    var += 1
    return var

def errargs():
    pass

########NEW FILE########
__FILENAME__ = all
log = []
def clientconnect(ctx, cc):
    ctx.log("XCLIENTCONNECT")
    log.append("clientconnect")

def serverconnect(ctx, cc):
    ctx.log("XSERVERCONNECT")
    log.append("serverconnect")

def request(ctx, r):
    ctx.log("XREQUEST")
    log.append("request")

def response(ctx, r):
    ctx.log("XRESPONSE")
    log.append("response")

def clientdisconnect(ctx, cc):
    ctx.log("XCLIENTDISCONNECT")
    log.append("clientdisconnect")

def error(ctx, cc):
    ctx.log("XERROR")
    log.append("error")

########NEW FILE########
__FILENAME__ = concurrent_decorator
import time
from libmproxy.script import concurrent


@concurrent
def clientconnect(context, cc):
    context.log("clientconnect")


@concurrent
def serverconnect(context, sc):
    context.log("serverconnect")


@concurrent
def request(context, flow):
    time.sleep(0.1)


@concurrent
def response(context, flow):
    context.log("response")


@concurrent
def error(context, err):
    context.log("error")


@concurrent
def clientdisconnect(context, dc):
    context.log("clientdisconnect")
########NEW FILE########
__FILENAME__ = concurrent_decorator_err
from libmproxy.script import concurrent

@concurrent
def start(context, argv):
    pass
########NEW FILE########
__FILENAME__ = duplicate_flow

def request(ctx, f):
    f = ctx.duplicate_flow(f)
    ctx.replay_request(f)


########NEW FILE########
__FILENAME__ = loaderr


a = x

########NEW FILE########
__FILENAME__ = reqerr
def request(ctx, r):
    raise ValueError

########NEW FILE########
__FILENAME__ = starterr

def start(ctx, argv):
    raise ValueError

########NEW FILE########
__FILENAME__ = syntaxerr


a +

########NEW FILE########
__FILENAME__ = test_app
import mock, socket, os, time
from libmproxy import dump
from netlib import certutils, tcp
from libpathod.pathoc import Pathoc
import tutils, tservers

class TestApp(tservers.HTTPProxTest):
    def test_basic(self):
        assert self.app("/").status_code == 200

    def test_cert(self):
        with tutils.tmpdir() as d:
            for ext in ["pem", "p12"]:
                resp = self.app("/cert/%s" % ext)
                assert resp.status_code == 200
                assert resp.content

########NEW FILE########
__FILENAME__ = test_cmdline
import argparse
from libmproxy import cmdline
import tutils
import os.path


def test_parse_replace_hook():
    x = cmdline.parse_replace_hook("/foo/bar/voing")
    assert x == ("foo", "bar", "voing")

    x = cmdline.parse_replace_hook("/foo/bar/vo/ing/")
    assert x == ("foo", "bar", "vo/ing/")

    x = cmdline.parse_replace_hook("/bar/voing")
    assert x == (".*", "bar", "voing")

    tutils.raises(
        cmdline.ParseException,
        cmdline.parse_replace_hook,
        "/foo"
    )
    tutils.raises(
        "replacement regex",
        cmdline.parse_replace_hook,
        "patt/[/rep"
    )
    tutils.raises(
        "filter pattern",
        cmdline.parse_replace_hook,
        "/~/foo/rep"
    )
    tutils.raises(
        "empty clause",
        cmdline.parse_replace_hook,
        "//"
    )


def test_parse_server_spec():
    tutils.raises("Invalid server specification", cmdline.parse_server_spec, "")
    assert cmdline.parse_server_spec("http://foo.com:88") == [False, False, "foo.com", 88]
    assert cmdline.parse_server_spec("http://foo.com") == [False, False, "foo.com", 80]
    assert cmdline.parse_server_spec("https://foo.com") == [True, True, "foo.com", 443]
    assert cmdline.parse_server_spec("https2http://foo.com") == [True, False, "foo.com", 80]
    assert cmdline.parse_server_spec("http2https://foo.com") == [False, True, "foo.com", 443]
    tutils.raises("Invalid server specification", cmdline.parse_server_spec, "foo.com")
    tutils.raises("Invalid server specification", cmdline.parse_server_spec, "http://")


def test_parse_setheaders():
    x = cmdline.parse_setheader("/foo/bar/voing")
    assert x == ("foo", "bar", "voing")

def test_common():
    parser = argparse.ArgumentParser()
    cmdline.common_options(parser)
    opts = parser.parse_args(args=[])

    assert cmdline.get_common_options(opts)

    opts.stickycookie_filt = "foo"
    opts.stickyauth_filt = "foo"
    v = cmdline.get_common_options(opts)
    assert v["stickycookie"] == "foo"
    assert v["stickyauth"] == "foo"

    opts.setheader = ["/foo/bar/voing"]
    v = cmdline.get_common_options(opts)
    assert v["setheaders"] == [("foo", "bar", "voing")]

    opts.setheader = ["//"]
    tutils.raises(
        "empty clause",
        cmdline.get_common_options,
        opts
    )
    opts.setheader = []

    opts.replace = ["/foo/bar/voing"]
    v = cmdline.get_common_options(opts)
    assert v["replacements"] == [("foo", "bar", "voing")]

    opts.replace = ["//"]
    tutils.raises(
        "empty clause",
        cmdline.get_common_options,
        opts
    )

    opts.replace = []
    opts.replace_file = [("/foo/bar/nonexistent")]
    tutils.raises(
        "could not read replace file",
        cmdline.get_common_options,
        opts
    )

    opts.replace_file = [("/~/bar/nonexistent")]
    tutils.raises(
        "filter pattern",
        cmdline.get_common_options,
        opts
    )

    p = tutils.test_data.path("data/replace")
    opts.replace_file = [("/foo/bar/%s"%p)]
    v = cmdline.get_common_options(opts)["replacements"]
    assert len(v) == 1
    assert v[0][2].strip() == "replacecontents"


########NEW FILE########
__FILENAME__ = test_console
import os, sys, mock, gc
from os.path import normpath
import mock_urwid
from libmproxy import console
from libmproxy.console import common

import tutils

class TestConsoleState:
    def test_flow(self):
        """
            normal flow:

                connect -> request -> response
        """
        c = console.ConsoleState()
        f = self._add_request(c)
        assert f in c._flow_list
        assert c.get_focus() == (f, 0)

    def test_focus(self):
        """
            normal flow:

                connect -> request -> response
        """
        c = console.ConsoleState()
        f = self._add_request(c)

        assert c.get_focus() == (f, 0)
        assert c.get_from_pos(0) == (f, 0)
        assert c.get_from_pos(1) == (None, None)
        assert c.get_next(0) == (None, None)

        f2 = self._add_request(c)
        assert c.get_focus() == (f, 0)
        assert c.get_next(0) == (f2, 1)
        assert c.get_prev(1) == (f, 0)
        assert c.get_next(1) == (None, None)

        c.set_focus(0)
        assert c.get_focus() == (f, 0)
        c.set_focus(-1)
        assert c.get_focus() == (f, 0)
        c.set_focus(2)
        assert c.get_focus() == (f2, 1)

        c.delete_flow(f2)
        assert c.get_focus() == (f, 0)
        c.delete_flow(f)
        assert c.get_focus() == (None, None)

    def _add_request(self, state):
        r = tutils.treq()
        return state.add_request(r)

    def _add_response(self, state):
        f = self._add_request(state)
        r = tutils.tresp(f.request)
        state.add_response(r)

    def test_add_response(self):
        c = console.ConsoleState()
        f = self._add_request(c)
        r = tutils.tresp(f.request)
        c.focus = None
        c.add_response(r)

    def test_focus_view(self):
        c = console.ConsoleState()
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        self._add_response(c)
        assert not c.set_limit("~s")
        assert len(c.view) == 3
        assert c.focus == 0

    def test_settings(self):
        c = console.ConsoleState()
        f = self._add_request(c)
        c.add_flow_setting(f, "foo", "bar")
        assert c.get_flow_setting(f, "foo") == "bar"
        assert c.get_flow_setting(f, "oink") == None
        assert c.get_flow_setting(f, "oink", "foo") == "foo"
        assert len(c.flowsettings) == 1
        c.delete_flow(f)
        del f
        gc.collect()
        assert len(c.flowsettings) == 0


def test_format_keyvals():
    assert common.format_keyvals(
        [
            ("aa", "bb"),
            None,
            ("cc", "dd"),
            (None, "dd"),
            (None, "dd"),
        ]
    )


class TestPathCompleter:
    def test_lookup_construction(self):
        c = console._PathCompleter()

        cd = tutils.test_data.path("completion")
        ca = os.path.join(cd, "a")
        assert c.complete(ca).endswith(normpath("/completion/aaa"))
        assert c.complete(ca).endswith(normpath("/completion/aab"))
        c.reset()
        ca = os.path.join(cd, "aaa")
        assert c.complete(ca).endswith(normpath("/completion/aaa"))
        assert c.complete(ca).endswith(normpath("/completion/aaa"))
        c.reset()
        assert c.complete(cd).endswith(normpath("/completion/aaa"))

    def test_completion(self):
        c = console._PathCompleter(True)
        c.reset()
        c.lookup = [
            ("a", "x/a"),
            ("aa", "x/aa"),
        ]
        assert c.complete("a") == "a"
        assert c.final == "x/a"
        assert c.complete("a") == "aa"
        assert c.complete("a") == "a"

        c = console._PathCompleter(True)
        r = c.complete("l")
        assert c.final.endswith(r)

        c.reset()
        assert c.complete("/nonexistent") == "/nonexistent"
        assert c.final == "/nonexistent"
        c.reset()
        assert c.complete("~") != "~"

        c.reset()
        s = "thisisatotallynonexistantpathforsure"
        assert c.complete(s) == s
        assert c.final == s


def test_options():
    assert console.Options(kill=True)

########NEW FILE########
__FILENAME__ = test_console_common
import os
from nose.plugins.skip import SkipTest
if os.name == "nt":
    raise SkipTest("Skipped on Windows.")

import libmproxy.console.common as common
from libmproxy import utils, flow, encoding
import tutils


def test_format_flow():
    f = tutils.tflow_full()
    assert common.format_flow(f, True)
    assert common.format_flow(f, True, hostheader=True)
    assert common.format_flow(f, True, extended=True)

########NEW FILE########
__FILENAME__ = test_console_contentview
import os
from nose.plugins.skip import SkipTest
if os.name == "nt":
    raise SkipTest("Skipped on Windows.")

import sys
import libmproxy.console.contentview as cv
from libmproxy import utils, flow, encoding
import tutils

try:
    import pyamf
except ImportError:
    pyamf = None

try:
    import cssutils
except:
    cssutils = None


class TestContentView:
    def test_trailer(self):
        txt = []
        cv.trailer(5, txt, 1000)
        assert not txt
        cv.trailer(cv.VIEW_CUTOFF + 10, txt, cv.VIEW_CUTOFF)
        assert txt

    def test_view_auto(self):
        v = cv.ViewAuto()
        f = v(
                flow.ODictCaseless(),
                "foo",
                1000
              )
        assert f[0] == "Raw"

        f = v(
                flow.ODictCaseless(
                    [["content-type", "text/html"]],
                ),
                "<html></html>",
                1000
              )
        assert f[0] == "HTML"

        f = v(
                flow.ODictCaseless(
                    [["content-type", "text/flibble"]],
                ),
                "foo",
                1000
              )
        assert f[0] == "Raw"

        f = v(
                flow.ODictCaseless(
                    [["content-type", "text/flibble"]],
                ),
                "<xml></xml>",
                1000
              )
        assert f[0].startswith("XML")


    def test_view_urlencoded(self):
        d = utils.urlencode([("one", "two"), ("three", "four")])
        v = cv.ViewURLEncoded()
        assert v([], d, 100)
        d = utils.urlencode([("adsfa", "")])
        v = cv.ViewURLEncoded()
        assert v([], d, 100)

    def test_view_html(self):
        v = cv.ViewHTML()
        s = "<html><br><br></br><p>one</p></html>"
        assert v([], s, 1000)

        s = "gobbledygook"
        assert not v([], s, 1000)

    def test_view_html_outline(self):
        v = cv.ViewHTMLOutline()
        s = "<html><br><br></br><p>one</p></html>"
        assert v([], s, 1000)

    def test_view_json(self):
        cv.VIEW_CUTOFF = 100
        v = cv.ViewJSON()
        assert v([], "{}", 1000)
        assert not v([], "{", 1000)
        assert v([], "[" + ",".join(["0"]*cv.VIEW_CUTOFF) + "]", 1000)
        assert v([], "[1, 2, 3, 4, 5]", 5)

    def test_view_xml(self):
        v = cv.ViewXML()
        assert v([], "<foo></foo>", 1000)
        assert not v([], "<foo>", 1000)
        s = """<?xml version="1.0" encoding="UTF-8"?>
            <?xml-stylesheet title="XSL_formatting"?>
            <rss
                xmlns:media="http://search.yahoo.com/mrss/"
                xmlns:atom="http://www.w3.org/2005/Atom"
                version="2.0">
            </rss>
        """
        assert v([], s, 1000)

    def test_view_raw(self):
        v = cv.ViewRaw()
        assert v([], "foo", 1000)

    def test_view_javascript(self):
        v = cv.ViewJavaScript()
        assert v([], "[1, 2, 3]", 100)
        assert v([], "[1, 2, 3", 100)
        assert v([], "function(a){[1, 2, 3]}", 100)

    def test_view_css(self):
        v = cv.ViewCSS()

        with open(tutils.test_data.path('data/1.css'), 'r') as fp:
            fixture_1 = fp.read()

        result = v([], 'a', 100)

        if cssutils:
            assert len(result[1]) == 0
        else:
            assert len(result[1]) == 1

        result = v([], fixture_1, 100)

        if cssutils:
            assert len(result[1]) > 1
        else:
            assert len(result[1]) == 1

    def test_view_hex(self):
        v = cv.ViewHex()
        assert v([], "foo", 1000)

    def test_view_image(self):
        v = cv.ViewImage()
        p = tutils.test_data.path("data/image.png")
        assert v([], file(p,"rb").read(), sys.maxint)

        p = tutils.test_data.path("data/image.gif")
        assert v([], file(p,"rb").read(), sys.maxint)

        p = tutils.test_data.path("data/image-err1.jpg")
        assert v([], file(p,"rb").read(), sys.maxint)

        p = tutils.test_data.path("data/image.ico")
        assert v([], file(p,"rb").read(), sys.maxint)

        assert not v([], "flibble", sys.maxint)

    def test_view_multipart(self):
        view = cv.ViewMultipart()
        v = """
--AaB03x
Content-Disposition: form-data; name="submit-name"

Larry
--AaB03x
        """.strip()
        h = flow.ODictCaseless(
            [("Content-Type", "multipart/form-data; boundary=AaB03x")]
        )
        assert view(h, v, 1000)

        h = flow.ODictCaseless()
        assert not view(h, v, 1000)

        h = flow.ODictCaseless(
            [("Content-Type", "multipart/form-data")]
        )
        assert not view(h, v, 1000)

        h = flow.ODictCaseless(
            [("Content-Type", "unparseable")]
        )
        assert not view(h, v, 1000)

    def test_get_content_view(self):
        r = cv.get_content_view(
                cv.get("Raw"),
                [["content-type", "application/json"]],
                "[1, 2, 3]",
                1000,
                lambda x, l: None
              )
        assert "Raw" in r[0]

        r = cv.get_content_view(
                cv.get("Auto"),
                [["content-type", "application/json"]],
                "[1, 2, 3]",
                1000,
                lambda x, l: None
              )
        assert r[0] == "JSON"

        r = cv.get_content_view(
                cv.get("Auto"),
                [["content-type", "application/json"]],
                "[1, 2",
                1000,
                lambda x, l: None
              )
        assert "Raw" in r[0]

        r = cv.get_content_view(
                cv.get("AMF"),
                [],
                "[1, 2",
                1000,
                lambda x, l: None
              )
        assert "Raw" in r[0]


        r = cv.get_content_view(
                cv.get("Auto"),
                [
                    ["content-type", "application/json"],
                    ["content-encoding", "gzip"]
                ],
                encoding.encode('gzip', "[1, 2, 3]"),
                1000,
                lambda x, l: None
              )
        assert "decoded gzip" in r[0]
        assert "JSON" in r[0]

        r = cv.get_content_view(
                cv.get("XML"),
                [
                    ["content-type", "application/json"],
                    ["content-encoding", "gzip"]
                ],
                encoding.encode('gzip', "[1, 2, 3]"),
                1000,
                lambda x, l: None
              )
        assert "decoded gzip" in r[0]
        assert "Raw" in r[0]


if pyamf:
    def test_view_amf_request():
        v = cv.ViewAMF()

        p = tutils.test_data.path("data/amf01")
        assert v([], file(p,"rb").read(), sys.maxint)

        p = tutils.test_data.path("data/amf02")
        assert v([], file(p,"rb").read(), sys.maxint)

    def test_view_amf_response():
        v = cv.ViewAMF()
        p = tutils.test_data.path("data/amf03")
        assert v([], file(p,"rb").read(), sys.maxint)

if cv.ViewProtobuf.is_available():
    def test_view_protobuf_request():
        v = cv.ViewProtobuf()

        p = tutils.test_data.path("data/protobuf01")
        content_type, output = v([], file(p,"rb").read(), sys.maxint)
        assert content_type == "Protobuf"
        assert output[0].text == '1: "3bbc333c-e61c-433b-819a-0b9a8cc103b8"'

def test_get_by_shortcut():
    assert cv.get_by_shortcut("h")


########NEW FILE########
__FILENAME__ = test_console_help
import os
from nose.plugins.skip import SkipTest
if os.name == "nt":
    raise SkipTest("Skipped on Windows.")

import libmproxy.console.help as help

class DummyMaster:
    def make_view(self):
        pass


class TestHelp:
    def test_helptext(self):
        h = help.HelpView(None, "foo", None)
        assert h.helptext()

    def test_keypress(self):
        h = help.HelpView(DummyMaster(), "foo", [1, 2, 3])
        assert not h.keypress((0, 0), "q")
        assert not h.keypress((0, 0), "?")
        assert h.keypress((0, 0), "o") == "o"

########NEW FILE########
__FILENAME__ = test_console_search
import os
from nose.plugins.skip import SkipTest
if os.name == "nt":
    raise SkipTest("Skipped on Windows.")

import tutils
import libmproxy.console.contentview as cv

def test_search_highlights():
    # Default text in requests is content. We will search for nt once, and
    # expect the first bit to be highlighted. We will do it again and expect the
    # second to be.
    f = tutils.tflowview()

    f.search("nt")
    text_object = tutils.get_body_line(f.last_displayed_body, 0)
    assert text_object.get_text() == ('content', [(None, 2), (f.highlight_color, 2)])

    f.search("nt")
    text_object = tutils.get_body_line(f.last_displayed_body, 1)
    assert text_object.get_text() == ('content', [(None, 5), (f.highlight_color, 2)])

def test_search_returns_useful_messages():
    f = tutils.tflowview()

    # original string is content. this string should not be in there.
    test_string = "oranges and other fruit."
    response = f.search(test_string)
    assert response == "no matches for '%s'" % test_string

def test_search_highlights_clears_prev():
    f = tutils.tflowview(request_contents="this is string\nstring is string")

    f.search("string")
    text_object = tutils.get_body_line(f.last_displayed_body, 0)
    assert text_object.get_text() == ('this is string', [(None, 8), (f.highlight_color, 6)])

    # search again, it should not be highlighted again.
    f.search("string")
    text_object = tutils.get_body_line(f.last_displayed_body, 0)
    assert text_object.get_text() != ('this is string', [(None, 8), (f.highlight_color, 6)])

def test_search_highlights_multi_line(flow=None):
    f = flow if flow else tutils.tflowview(request_contents="this is string\nstring is string")

    # should highlight the first line.
    f.search("string")
    text_object = tutils.get_body_line(f.last_displayed_body, 0)
    assert text_object.get_text() == ('this is string', [(None, 8), (f.highlight_color, 6)])

    # should highlight second line, first appearance of string.
    f.search("string")
    text_object = tutils.get_body_line(f.last_displayed_body, 1)
    assert text_object.get_text() == ('string is string', [(None, 0), (f.highlight_color, 6)])

    # should highlight third line, second appearance of string.
    f.search("string")
    text_object = tutils.get_body_line(f.last_displayed_body, 1)
    assert text_object.get_text() == ('string is string', [(None, 10), (f.highlight_color, 6)])

def test_search_loops():
    f = tutils.tflowview(request_contents="this is string\nstring is string")

    # get to the end.
    f.search("string")
    f.search("string")
    f.search("string")

    # should highlight the first line.
    message = f.search("string")
    text_object = tutils.get_body_line(f.last_displayed_body, 0)
    assert text_object.get_text() == ('this is string', [(None, 8), (f.highlight_color, 6)])
    assert message == "search hit BOTTOM, continuing at TOP"

def test_search_focuses():
    f = tutils.tflowview(request_contents="this is string\nstring is string")

    # should highlight the first line.
    f.search("string")

    # should be focusing on the 2nd text line.
    f.search("string")
    text_object = tutils.get_body_line(f.last_displayed_body, 1)
    assert f.last_displayed_body.focus == text_object

def test_search_does_not_crash_on_bad():
    """
        this used to crash, kept for reference.
    """

    f = tutils.tflowview(request_contents="this is string\nstring is string\n"+("A" * cv.VIEW_CUTOFF)+"AFTERCUTOFF")
    f.search("AFTERCUTOFF")

    # pretend F
    f.state.add_flow_setting(
        f.flow,
        (f.state.view_flow_mode, "fullcontents"),
        True
    )
    f.master.refresh_flow(f.flow)

    # text changed, now this string will exist. can happen when user presses F
    # for full text view
    f.search("AFTERCUTOFF")

def test_search_backwards():
    f = tutils.tflowview(request_contents="content, content")

    first_match = ('content, content', [(None, 2), (f.highlight_color, 2)])

    f.search("nt")
    text_object = tutils.get_body_line(f.last_displayed_body, 0)
    assert text_object.get_text() == first_match

    f.search("nt")
    text_object = tutils.get_body_line(f.last_displayed_body, 1)
    assert text_object.get_text() == ('content, content', [(None, 5), (f.highlight_color, 2)])

    f.search_again(backwards=True)
    text_object = tutils.get_body_line(f.last_displayed_body, 0)
    assert text_object.get_text() == first_match

def test_search_back_multiline():
    f = tutils.tflowview(request_contents="this is string\nstring is string")

    # shared assertions. highlight and pointers should now be on the third
    # 'string' appearance
    test_search_highlights_multi_line(f)

    # should highlight second line, first appearance of string.
    f.search_again(backwards=True)
    text_object = tutils.get_body_line(f.last_displayed_body, 1)
    assert text_object.get_text() == ('string is string', [(None, 0), (f.highlight_color, 6)])

    # should highlight the first line again.
    f.search_again(backwards=True)
    text_object = tutils.get_body_line(f.last_displayed_body, 0)
    assert text_object.get_text() == ('this is string', [(None, 8), (f.highlight_color, 6)])

def test_search_back_multi_multi_line():
    """
        same as above for some bugs the above won't catch.
    """
    f = tutils.tflowview(request_contents="this is string\nthis is string\nthis is string")

    f.search("string")
    f.search_again()
    f.search_again()

    # should be on second line
    f.search_again(backwards=True)
    text_object = tutils.get_body_line(f.last_displayed_body, 1)
    assert text_object.get_text() == ('this is string', [(None, 8), (f.highlight_color, 6)])

    # first line now
    f.search_again(backwards=True)
    text_object = tutils.get_body_line(f.last_displayed_body, 0)
    assert text_object.get_text() == ('this is string', [(None, 8), (f.highlight_color, 6)])

def test_search_backwards_wraps():
    """
        when searching past line 0, it should loop.
    """
    f = tutils.tflowview(request_contents="this is string\nthis is string\nthis is string")

    # should be on second line
    f.search("string")
    f.search_again()
    text_object = tutils.get_body_line(f.last_displayed_body, 1)
    assert text_object.get_text() == ('this is string', [(None, 8), (f.highlight_color, 6)])

    # should be on third now.
    f.search_again(backwards=True)
    message = f.search_again(backwards=True)
    text_object = tutils.get_body_line(f.last_displayed_body, 2)
    assert text_object.get_text() == ('this is string', [(None, 8), (f.highlight_color, 6)])
    assert message == "search hit TOP, continuing at BOTTOM"


########NEW FILE########
__FILENAME__ = test_controller
import mock
from libmproxy import controller


class TestMaster:
    def test_default_handler(self):
        m = controller.Master(None)
        msg = mock.MagicMock()
        m.handle("type", msg)
        assert msg.reply.call_count == 1



########NEW FILE########
__FILENAME__ = test_dump
import os
from cStringIO import StringIO
from libmproxy import dump, flow, proxy
from libmproxy.proxy.primitives import Log
import tutils
import mock

def test_strfuncs():
    t = tutils.tresp()
    t.is_replay = True
    dump.str_response(t)

    t = tutils.treq()
    t.flow.client_conn = None
    t.stickycookie = True
    assert "stickycookie" in dump.str_request(t, False)
    assert "stickycookie" in dump.str_request(t, True)
    assert "replay" in dump.str_request(t, False)
    assert "replay" in dump.str_request(t, True)


class TestDumpMaster:
    def _cycle(self, m, content):
        req = tutils.treq(content=content)
        l = Log("connect")
        l.reply = mock.MagicMock()
        m.handle_log(l)
        cc = req.flow.client_conn
        cc.reply = mock.MagicMock()
        m.handle_clientconnect(cc)
        sc = proxy.connection.ServerConnection((req.get_host(), req.get_port()), None)
        sc.reply = mock.MagicMock()
        m.handle_serverconnection(sc)
        m.handle_request(req)
        resp = tutils.tresp(req, content=content)
        f = m.handle_response(resp)
        m.handle_clientdisconnect(cc)
        return f

    def _dummy_cycle(self, n, filt, content, **options):
        cs = StringIO()
        o = dump.Options(**options)
        m = dump.DumpMaster(None, o, filt, outfile=cs)
        for i in range(n):
            self._cycle(m, content)
        m.shutdown()
        return cs.getvalue()

    def _flowfile(self, path):
        f = open(path, "wb")
        fw = flow.FlowWriter(f)
        t = tutils.tflow_full()
        t.response = tutils.tresp(t.request)
        fw.add(t)
        f.close()

    def test_error(self):
        cs = StringIO()
        o = dump.Options(flow_detail=1)
        m = dump.DumpMaster(None, o, None, outfile=cs)
        f = tutils.tflow_err()
        m.handle_request(f.request)
        assert m.handle_error(f.error)
        assert "error" in cs.getvalue()

    def test_replay(self):
        cs = StringIO()

        o = dump.Options(server_replay="nonexistent", kill=True)
        tutils.raises(dump.DumpError, dump.DumpMaster, None, o, None, outfile=cs)

        with tutils.tmpdir() as t:
            p = os.path.join(t, "rep")
            self._flowfile(p)

            o = dump.Options(server_replay=p, kill=True)
            m = dump.DumpMaster(None, o, None, outfile=cs)

            self._cycle(m, "content")
            self._cycle(m, "content")

            o = dump.Options(server_replay=p, kill=False)
            m = dump.DumpMaster(None, o, None, outfile=cs)
            self._cycle(m, "nonexistent")

            o = dump.Options(client_replay=p, kill=False)
            m = dump.DumpMaster(None, o, None, outfile=cs)

    def test_read(self):
        with tutils.tmpdir() as t:
            p = os.path.join(t, "read")
            self._flowfile(p)
            assert "GET" in self._dummy_cycle(0, None, "", flow_detail=1, rfile=p)

            tutils.raises(
                dump.DumpError, self._dummy_cycle,
                0, None, "", verbosity=1, rfile="/nonexistent"
            )

            # We now just ignore errors
            self._dummy_cycle(0, None, "", verbosity=1, rfile=tutils.test_data.path("test_dump.py"))

    def test_options(self):
        o = dump.Options(verbosity = 2)
        assert o.verbosity == 2

    def test_filter(self):
        assert not "GET" in self._dummy_cycle(1, "~u foo", "", verbosity=1)

    def test_app(self):
        o = dump.Options(app=True)
        s = mock.MagicMock()
        m = dump.DumpMaster(s, o, None)
        assert len(m.apps.apps) == 1

    def test_replacements(self):
        o = dump.Options(replacements=[(".*", "content", "foo")])
        m = dump.DumpMaster(None, o, None)
        f = self._cycle(m, "content")
        assert f.request.content == "foo"

    def test_setheader(self):
        o = dump.Options(setheaders=[(".*", "one", "two")])
        m = dump.DumpMaster(None, o, None)
        f = self._cycle(m, "content")
        assert f.request.headers["one"] == ["two"]

    def test_basic(self):
        for i in (1, 2, 3):
            assert "GET" in self._dummy_cycle(1, "~s", "", flow_detail=i)
            assert "GET" in self._dummy_cycle(1, "~s", "\x00\x00\x00", flow_detail=i)
            assert "GET" in self._dummy_cycle(1, "~s", "ascii", flow_detail=i)

    def test_write(self):
        with tutils.tmpdir() as d:
            p = os.path.join(d, "a")
            self._dummy_cycle(1, None, "", wfile=p, verbosity=0)
            assert len(list(flow.FlowReader(open(p,"rb")).stream())) == 1

    def test_write_err(self):
        tutils.raises(
            dump.DumpError,
            self._dummy_cycle,
            1,
            None,
            "",
            wfile = "nonexistentdir/foo"
        )

    def test_script(self):
        ret = self._dummy_cycle(
            1, None, "",
            scripts=[tutils.test_data.path("scripts/all.py")], verbosity=1
        )
        assert "XCLIENTCONNECT" in ret
        assert "XSERVERCONNECT" in ret
        assert "XREQUEST" in ret
        assert "XRESPONSE" in ret
        assert "XCLIENTDISCONNECT" in ret
        tutils.raises(
            dump.DumpError,
            self._dummy_cycle, 1, None, "", scripts=["nonexistent"]
        )
        tutils.raises(
            dump.DumpError,
            self._dummy_cycle, 1, None, "", scripts=["starterr.py"]
        )

    def test_stickycookie(self):
        self._dummy_cycle(1, None, "", stickycookie = ".*")

    def test_stickyauth(self):
        self._dummy_cycle(1, None, "", stickyauth = ".*")


########NEW FILE########
__FILENAME__ = test_encoding
from libmproxy import encoding

def test_identity():
    assert "string" == encoding.decode("identity", "string")
    assert "string" == encoding.encode("identity", "string")
    assert not encoding.encode("nonexistent", "string")
    assert None == encoding.decode("nonexistent encoding", "string")


def test_gzip():
    assert "string" == encoding.decode("gzip", encoding.encode("gzip", "string"))
    assert None == encoding.decode("gzip", "bogus")


def test_deflate():
    assert "string" == encoding.decode("deflate", encoding.encode("deflate", "string"))
    assert "string" == encoding.decode("deflate", encoding.encode("deflate", "string")[2:-4])
    assert None == encoding.decode("deflate", "bogus")


########NEW FILE########
__FILENAME__ = test_examples
from libmproxy import utils, script
import glob
from libmproxy.proxy import config
import tservers

example_dir = utils.Data("libmproxy").path("../examples")
scripts = glob.glob("%s/*.py" % example_dir)

tmaster = tservers.TestMaster(config.ProxyConfig())

for f in scripts:
    script.Script(f, tmaster)  # Loads the script file.
########NEW FILE########
__FILENAME__ = test_filt
import cStringIO
from libmproxy import filt, flow
from libmproxy.protocol import http
from libmproxy.protocol.primitives import Error
import tutils

class TestParsing:
    def _dump(self, x):
        c = cStringIO.StringIO()
        x.dump(fp=c)
        assert c.getvalue()

    def test_parse_err(self):
        assert filt.parse("~h [") is None

    def test_simple(self):
        assert not filt.parse("~b")
        assert filt.parse("~q")
        assert filt.parse("~c 10")
        assert filt.parse("~m foobar")
        assert filt.parse("~u foobar")
        assert filt.parse("~q ~c 10")
        p = filt.parse("~q ~c 10")
        self._dump(p)
        assert len(p.lst) == 2

    def test_naked_url(self):
        a = filt.parse("foobar ~h rex")
        assert a.lst[0].expr == "foobar"
        assert a.lst[1].expr == "rex"
        self._dump(a)

    def test_quoting(self):
        a = filt.parse("~u 'foo ~u bar' ~u voing")
        assert a.lst[0].expr == "foo ~u bar"
        assert a.lst[1].expr == "voing"
        self._dump(a)

        a = filt.parse("~u foobar")
        assert a.expr == "foobar"

        a = filt.parse(r"~u 'foobar\"\''")
        assert a.expr == "foobar\"'"

        a = filt.parse(r'~u "foo \'bar"')
        assert a.expr == "foo 'bar"

    def test_nesting(self):
        a = filt.parse("(~u foobar & ~h voing)")
        assert a.lst[0].expr == "foobar"
        self._dump(a)

    def test_not(self):
        a = filt.parse("!~h test")
        assert a.itm.expr == "test"
        a = filt.parse("!(~u test & ~h bar)")
        assert a.itm.lst[0].expr == "test"
        self._dump(a)

    def test_binaryops(self):
        a = filt.parse("~u foobar | ~h voing")
        isinstance(a, filt.FOr)
        self._dump(a)

        a = filt.parse("~u foobar & ~h voing")
        isinstance(a, filt.FAnd)
        self._dump(a)

    def test_wideops(self):
        a = filt.parse("~hq 'header: qvalue'")
        assert isinstance(a, filt.FHeadRequest)
        self._dump(a)


class TestMatching:
    def req(self):
        headers = flow.ODictCaseless()
        headers["header"] = ["qvalue"]
        req = http.HTTPRequest(
            "absolute",
            "GET",
            "http",
            "host",
            80,
            "/path",
            (1, 1),
            headers,
            "content_request",
            None,
            None
        )
        f = http.HTTPFlow(tutils.tclient_conn(), None)
        f.request = req
        return f

    def resp(self):
        f = self.req()

        headers = flow.ODictCaseless()
        headers["header_response"] = ["svalue"]
        f.response = http.HTTPResponse((1, 1), 200, "OK", headers, "content_response", None, None)

        return f

    def err(self):
        f = self.req()
        f.error = Error("msg")
        return f

    def q(self, q, o):
        return filt.parse(q)(o)

    def test_asset(self):
        s = self.resp()
        assert not self.q("~a", s)
        s.response.headers["content-type"] = ["text/javascript"]
        assert self.q("~a", s)

    def test_fcontenttype(self):
        q = self.req()
        s = self.resp()
        assert not self.q("~t content", q)
        assert not self.q("~t content", s)

        q.request.headers["content-type"] = ["text/json"]
        assert self.q("~t json", q)
        assert self.q("~tq json", q)
        assert not self.q("~ts json", q)

        s.response.headers["content-type"] = ["text/json"]
        assert self.q("~t json", s)

        del s.response.headers["content-type"]
        s.request.headers["content-type"] = ["text/json"]
        assert self.q("~t json", s)
        assert self.q("~tq json", s)
        assert not self.q("~ts json", s)

    def test_freq_fresp(self):
        q = self.req()
        s = self.resp()

        assert self.q("~q", q)
        assert not self.q("~q", s)

        assert not self.q("~s", q)
        assert self.q("~s", s)

    def test_ferr(self):
        e = self.err()
        assert self.q("~e", e)

    def test_head(self):
        q = self.req()
        s = self.resp()
        assert not self.q("~h nonexistent", q)
        assert self.q("~h qvalue", q)
        assert self.q("~h header", q)
        assert self.q("~h 'header: qvalue'", q)

        assert self.q("~h 'header: qvalue'", s)
        assert self.q("~h 'header_response: svalue'", s)

        assert self.q("~hq 'header: qvalue'", s)
        assert not self.q("~hq 'header_response: svalue'", s)

        assert self.q("~hq 'header: qvalue'", q)
        assert not self.q("~hq 'header_request: svalue'", q)

        assert not self.q("~hs 'header: qvalue'", s)
        assert self.q("~hs 'header_response: svalue'", s)
        assert not self.q("~hs 'header: qvalue'", q)

    def test_body(self):
        q = self.req()
        s = self.resp()
        assert not self.q("~b nonexistent", q)
        assert self.q("~b content", q)
        assert self.q("~b response", s)
        assert self.q("~b content_request", s)

        assert self.q("~bq content", q)
        assert self.q("~bq content", s)
        assert not self.q("~bq response", q)
        assert not self.q("~bq response", s)

        assert not self.q("~bs content", q)
        assert self.q("~bs content", s)
        assert not self.q("~bs nomatch", s)
        assert not self.q("~bs response", q)
        assert self.q("~bs response", s)

    def test_method(self):
        q = self.req()
        s = self.resp()
        assert self.q("~m get", q)
        assert not self.q("~m post", q)

        q.request.method = "oink"
        assert not self.q("~m get", q)

    def test_domain(self):
        q = self.req()
        s = self.resp()
        assert self.q("~d host", q)
        assert not self.q("~d none", q)

    def test_url(self):
        q = self.req()
        s = self.resp()
        assert self.q("~u host", q)
        assert self.q("~u host/path", q)
        assert not self.q("~u moo/path", q)

        assert self.q("~u host", s)
        assert self.q("~u host/path", s)
        assert not self.q("~u moo/path", s)

    def test_code(self):
        q = self.req()
        s = self.resp()
        assert not self.q("~c 200", q)
        assert self.q("~c 200", s)
        assert not self.q("~c 201", s)

    def test_and(self):
        s = self.resp()
        assert self.q("~c 200 & ~h head", s)
        assert self.q("~c 200 & ~h head", s)
        assert not self.q("~c 200 & ~h nohead", s)
        assert self.q("(~c 200 & ~h head) & ~b content", s)
        assert not self.q("(~c 200 & ~h head) & ~b nonexistent", s)
        assert not self.q("(~c 200 & ~h nohead) & ~b content", s)

    def test_or(self):
        s = self.resp()
        assert self.q("~c 200 | ~h nohead", s)
        assert self.q("~c 201 | ~h head", s)
        assert not self.q("~c 201 | ~h nohead", s)
        assert self.q("(~c 201 | ~h nohead) | ~s", s)

    def test_not(self):
        s = self.resp()
        assert not self.q("! ~c 200", s)
        assert self.q("! ~c 201", s)
        assert self.q("!~c 201 !~c 202", s)
        assert not self.q("!~c 201 !~c 200", s)


########NEW FILE########
__FILENAME__ = test_flow
import Queue, time, os.path
from cStringIO import StringIO
import email.utils
from libmproxy import filt, protocol, controller, utils, tnetstring, flow
from libmproxy.protocol.primitives import Error, Flow
from libmproxy.protocol.http import decoded, CONTENT_MISSING
from libmproxy.proxy.connection import ClientConnection, ServerConnection
from netlib import tcp
import tutils


def test_app_registry():
    ar = flow.AppRegistry()
    ar.add("foo", "domain", 80)

    r = tutils.treq()
    r.set_url("http://domain:80/")
    assert ar.get(r)

    r.port = 81
    assert not ar.get(r)

    r = tutils.treq()
    r.host = "domain2"
    r.port = 80
    assert not ar.get(r)
    r.headers["host"] = ["domain"]
    assert ar.get(r)



class TestStickyCookieState:
    def _response(self, cookie, host):
        s = flow.StickyCookieState(filt.parse(".*"))
        f = tutils.tflow_full()
        f.server_conn.address = tcp.Address((host, 80))
        f.response.headers["Set-Cookie"] = [cookie]
        s.handle_response(f)
        return s, f

    def test_domain_match(self):
        s = flow.StickyCookieState(filt.parse(".*"))
        assert s.domain_match("www.google.com", ".google.com")
        assert s.domain_match("google.com", ".google.com")

    def test_handle_response(self):
        c = "SSID=mooo, FOO=bar; Domain=.google.com; Path=/; "\
            "Expires=Wed, 13-Jan-2021 22:23:01 GMT; Secure; "

        s, f = self._response(c, "host")
        assert not s.jar.keys()

        s, f = self._response(c, "www.google.com")
        assert s.jar.keys()

        s, f = self._response("SSID=mooo", "www.google.com")
        assert s.jar.keys()[0] == ('www.google.com', 80, '/')

    def test_handle_request(self):
        s, f = self._response("SSID=mooo", "www.google.com")
        assert "cookie" not in f.request.headers
        s.handle_request(f)
        assert "cookie" in f.request.headers


class TestStickyAuthState:
    def test_handle_response(self):
        s = flow.StickyAuthState(filt.parse(".*"))
        f = tutils.tflow_full()
        f.request.headers["authorization"] = ["foo"]
        s.handle_request(f)
        assert "address" in s.hosts

        f = tutils.tflow_full()
        s.handle_request(f)
        assert f.request.headers["authorization"] == ["foo"]


class TestClientPlaybackState:
    def test_tick(self):
        first = tutils.tflow()
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        fm.start_client_playback([first, tutils.tflow()], True)
        c = fm.client_playback

        assert not c.done()
        assert not s.flow_count()
        assert c.count() == 2
        c.tick(fm, testing=True)
        assert s.flow_count()
        assert c.count() == 1

        c.tick(fm, testing=True)
        assert c.count() == 1

        c.clear(c.current)
        c.tick(fm, testing=True)
        assert c.count() == 0
        c.clear(c.current)
        assert c.done()

        q = Queue.Queue()
        fm.state.clear()
        fm.tick(q)

        fm.stop_client_playback()
        assert not fm.client_playback


class TestServerPlaybackState:
    def test_hash(self):
        s = flow.ServerPlaybackState(None, [], False, False)
        r = tutils.tflow()
        r2 = tutils.tflow()

        assert s._hash(r)
        assert s._hash(r) == s._hash(r2)
        r.request.headers["foo"] = ["bar"]
        assert s._hash(r) == s._hash(r2)
        r.request.path = "voing"
        assert s._hash(r) != s._hash(r2)

    def test_headers(self):
        s = flow.ServerPlaybackState(["foo"], [], False, False)
        r = tutils.tflow_full()
        r.request.headers["foo"] = ["bar"]
        r2 = tutils.tflow_full()
        assert not s._hash(r) == s._hash(r2)
        r2.request.headers["foo"] = ["bar"]
        assert s._hash(r) == s._hash(r2)
        r2.request.headers["oink"] = ["bar"]
        assert s._hash(r) == s._hash(r2)

        r = tutils.tflow_full()
        r2 = tutils.tflow_full()
        assert s._hash(r) == s._hash(r2)

    def test_load(self):
        r = tutils.tflow_full()
        r.request.headers["key"] = ["one"]

        r2 = tutils.tflow_full()
        r2.request.headers["key"] = ["two"]

        s = flow.ServerPlaybackState(None, [r, r2], False, False)
        assert s.count() == 2
        assert len(s.fmap.keys()) == 1

        n = s.next_flow(r)
        assert n.request.headers["key"] == ["one"]
        assert s.count() == 1

        n = s.next_flow(r)
        assert n.request.headers["key"] == ["two"]
        assert s.count() == 0

        assert not s.next_flow(r)

    def test_load_with_nopop(self):
        r = tutils.tflow_full()
        r.request.headers["key"] = ["one"]

        r2 = tutils.tflow_full()
        r2.request.headers["key"] = ["two"]

        s = flow.ServerPlaybackState(None, [r, r2], False, True)

        assert s.count() == 2
        s.next_flow(r)
        assert s.count() == 2


class TestFlow:
    def test_copy(self):
        f = tutils.tflow_full()
        a0 = f._get_state()
        f2 = f.copy()
        a = f._get_state()
        b = f2._get_state()
        assert f._get_state() == f2._get_state()
        assert not f == f2
        assert not f is f2
        assert f.request == f2.request
        assert not f.request is f2.request
        assert f.request.headers == f2.request.headers
        assert not f.request.headers is f2.request.headers
        assert f.response == f2.response
        assert not f.response is f2.response

        f = tutils.tflow_err()
        f2 = f.copy()
        assert not f is f2
        assert not f.request is f2.request
        assert f.request.headers == f2.request.headers
        assert not f.request.headers is f2.request.headers
        assert f.error == f2.error
        assert not f.error is f2.error

    def test_match(self):
        f = tutils.tflow_full()
        assert not f.match("~b test")
        assert f.match(None)
        assert not f.match("~b test")

        f = tutils.tflow_err()
        assert f.match("~e")

        tutils.raises(ValueError, f.match, "~")

    def test_backup(self):
        f = tutils.tflow()
        f.response = tutils.tresp()
        f.request.content = "foo"
        assert not f.modified()
        f.backup()
        f.request.content = "bar"
        assert f.modified()
        f.revert()
        assert f.request.content == "foo"

    def test_backup_idempotence(self):
        f = tutils.tflow_full()
        f.backup()
        f.revert()
        f.backup()
        f.revert()

    def test_getset_state(self):
        f = tutils.tflow_full()
        state = f._get_state()
        assert f._get_state() == protocol.http.HTTPFlow._from_state(state)._get_state()

        f.response = None
        f.error = Error("error")
        state = f._get_state()
        assert f._get_state() == protocol.http.HTTPFlow._from_state(state)._get_state()

        f2 = f.copy()
        assert f._get_state() == f2._get_state()
        assert not f == f2
        f2.error = Error("e2")
        assert not f == f2
        f._load_state(f2._get_state())
        assert f._get_state() == f2._get_state()

    def test_kill(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        f = tutils.tflow()
        f.request = tutils.treq()
        f.intercept()
        assert not f.request.reply.acked
        f.kill(fm)
        assert f.request.reply.acked
        f.intercept()
        f.response = tutils.tresp()
        f.request.reply()
        assert not f.response.reply.acked
        f.kill(fm)
        assert f.response.reply.acked

    def test_killall(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)

        r = tutils.treq()
        fm.handle_request(r)

        r = tutils.treq()
        fm.handle_request(r)

        for i in s.view:
            assert not i.request.reply.acked
        s.killall(fm)
        for i in s.view:
            assert i.request.reply.acked

    def test_accept_intercept(self):
        f = tutils.tflow()
        f.request = tutils.treq()
        f.intercept()
        assert not f.request.reply.acked
        f.accept_intercept()
        assert f.request.reply.acked
        f.response = tutils.tresp()
        f.intercept()
        f.request.reply()
        assert not f.response.reply.acked
        f.accept_intercept()
        assert f.response.reply.acked

    def test_replace_unicode(self):
        f = tutils.tflow_full()
        f.response.content = "\xc2foo"
        f.replace("foo", u"bar")

    def test_replace(self):
        f = tutils.tflow_full()
        f.request.headers["foo"] = ["foo"]
        f.request.content = "afoob"

        f.response.headers["foo"] = ["foo"]
        f.response.content = "afoob"

        assert f.replace("foo", "bar") == 6

        assert f.request.headers["bar"] == ["bar"]
        assert f.request.content == "abarb"
        assert f.response.headers["bar"] == ["bar"]
        assert f.response.content == "abarb"

    def test_replace_encoded(self):
        f = tutils.tflow_full()
        f.request.content = "afoob"
        f.request.encode("gzip")
        f.response.content = "afoob"
        f.response.encode("gzip")

        f.replace("foo", "bar")

        assert f.request.content != "abarb"
        f.request.decode()
        assert f.request.content == "abarb"

        assert f.response.content != "abarb"
        f.response.decode()
        assert f.response.content == "abarb"



class TestState:
    def test_backup(self):
        c = flow.State()
        req = tutils.treq()
        f = c.add_request(req)

        f.backup()
        c.revert(f)

    def test_flow(self):
        """
            normal flow:

                connect -> request -> response
        """
        bc = tutils.tclient_conn()
        c = flow.State()

        req = tutils.treq(bc)
        f = c.add_request(req)
        assert f
        assert c.flow_count() == 1
        assert c.active_flow_count() == 1

        newreq = tutils.treq()
        assert c.add_request(newreq)
        assert c.active_flow_count() == 2

        resp = tutils.tresp(req)
        assert c.add_response(resp)
        assert c.flow_count() == 2
        assert c.active_flow_count() == 1

        unseen_resp = tutils.tresp()
        unseen_resp.flow = None
        assert not c.add_response(unseen_resp)
        assert c.active_flow_count() == 1

        resp = tutils.tresp(newreq)
        assert c.add_response(resp)
        assert c.active_flow_count() == 0

    def test_err(self):
        c = flow.State()
        req = tutils.treq()
        f = c.add_request(req)
        f.error = Error("message")
        assert c.add_error(f.error)

        e = Error("message")
        assert not c.add_error(e)

        c = flow.State()
        req = tutils.treq()
        f = c.add_request(req)
        e = tutils.terr()
        c.set_limit("~e")
        assert not c.view
        assert c.add_error(e)
        assert c.view

    def test_set_limit(self):
        c = flow.State()

        req = tutils.treq()
        assert len(c.view) == 0

        c.add_request(req)
        assert len(c.view) == 1

        c.set_limit("~s")
        assert c.limit_txt == "~s"
        assert len(c.view) == 0
        resp = tutils.tresp(req)
        c.add_response(resp)
        assert len(c.view) == 1
        c.set_limit(None)
        assert len(c.view) == 1

        req = tutils.treq()
        c.add_request(req)
        assert len(c.view) == 2
        c.set_limit("~q")
        assert len(c.view) == 1
        c.set_limit("~s")
        assert len(c.view) == 1

        assert "Invalid" in c.set_limit("~")

    def test_set_intercept(self):
        c = flow.State()
        assert not c.set_intercept("~q")
        assert c.intercept_txt == "~q"
        assert "Invalid" in c.set_intercept("~")
        assert not c.set_intercept(None)
        assert c.intercept_txt == None

    def _add_request(self, state):
        req = tutils.treq()
        f = state.add_request(req)
        return f

    def _add_response(self, state):
        req = tutils.treq()
        state.add_request(req)
        resp = tutils.tresp(req)
        state.add_response(resp)

    def _add_error(self, state):
        req = tutils.treq()
        f = state.add_request(req)
        f.error = Error("msg")

    def test_clear(self):
        c = flow.State()
        f = self._add_request(c)
        f.intercepting = True

        c.clear()
        assert c.flow_count() == 0

    def test_dump_flows(self):
        c = flow.State()
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        self._add_response(c)
        self._add_error(c)

        flows = c.view[:]
        c.clear()

        c.load_flows(flows)
        assert isinstance(c._flow_list[0], Flow)

    def test_accept_all(self):
        c = flow.State()
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        c.accept_all()


class TestSerialize:
    def _treader(self):
        sio = StringIO()
        w = flow.FlowWriter(sio)
        for i in range(3):
            f = tutils.tflow_full()
            w.add(f)
        for i in range(3):
            f = tutils.tflow_err()
            w.add(f)

        sio.seek(0)
        return flow.FlowReader(sio)

    def test_roundtrip(self):
        sio = StringIO()
        f = tutils.tflow()
        f.request.content = "".join(chr(i) for i in range(255))
        w = flow.FlowWriter(sio)
        w.add(f)

        sio.seek(0)
        r = flow.FlowReader(sio)
        l = list(r.stream())
        assert len(l) == 1

        f2 = l[0]
        assert f2._get_state() == f._get_state()
        assert f2.request._assemble() == f.request._assemble()

    def test_load_flows(self):
        r = self._treader()
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        fm.load_flows(r)
        assert len(s._flow_list) == 6

    def test_filter(self):
        sio = StringIO()
        fl = filt.parse("~c 200")
        w = flow.FilteredFlowWriter(sio, fl)

        f = tutils.tflow_full()
        f.response.code = 200
        w.add(f)

        f = tutils.tflow_full()
        f.response.code = 201
        w.add(f)

        sio.seek(0)
        r = flow.FlowReader(sio)
        assert len(list(r.stream()))


    def test_error(self):
        sio = StringIO()
        sio.write("bogus")
        sio.seek(0)
        r = flow.FlowReader(sio)
        tutils.raises(flow.FlowReadError, list, r.stream())

        f = flow.FlowReadError("foo")
        assert f.strerror == "foo"

    def test_versioncheck(self):
        f = tutils.tflow()
        d = f._get_state()
        d["version"] = (0, 0)
        sio = StringIO()
        tnetstring.dump(d, sio)
        sio.seek(0)

        r = flow.FlowReader(sio)
        tutils.raises("version", list, r.stream())


class TestFlowMaster:
    def test_load_script(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        assert not fm.load_script(tutils.test_data.path("scripts/a.py"))
        assert not fm.load_script(tutils.test_data.path("scripts/a.py"))
        assert not fm.unload_scripts()
        assert fm.load_script("nonexistent")
        assert "ValueError" in fm.load_script(tutils.test_data.path("scripts/starterr.py"))
        assert len(fm.scripts) == 0

    def test_replay(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        f = tutils.tflow_full()
        f.request.content = CONTENT_MISSING
        assert "missing" in fm.replay_request(f)

        f.intercepting = True
        assert "intercepting" in fm.replay_request(f)

    def test_script_reqerr(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        assert not fm.load_script(tutils.test_data.path("scripts/reqerr.py"))
        req = tutils.treq()
        fm.handle_clientconnect(req.flow.client_conn)
        assert fm.handle_request(req)

    def test_script(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        assert not fm.load_script(tutils.test_data.path("scripts/all.py"))
        req = tutils.treq()
        fm.handle_clientconnect(req.flow.client_conn)
        assert fm.scripts[0].ns["log"][-1] == "clientconnect"
        sc = ServerConnection((req.get_host(), req.get_port()), None)
        sc.reply = controller.DummyReply()
        fm.handle_serverconnection(sc)
        assert fm.scripts[0].ns["log"][-1] == "serverconnect"
        f = fm.handle_request(req)
        assert fm.scripts[0].ns["log"][-1] == "request"
        resp = tutils.tresp(req)
        fm.handle_response(resp)
        assert fm.scripts[0].ns["log"][-1] == "response"
        #load second script
        assert not fm.load_script(tutils.test_data.path("scripts/all.py"))
        assert len(fm.scripts) == 2
        fm.handle_clientdisconnect(sc)
        assert fm.scripts[0].ns["log"][-1] == "clientdisconnect"
        assert fm.scripts[1].ns["log"][-1] == "clientdisconnect"


        #unload first script
        fm.unload_scripts()
        assert len(fm.scripts) == 0

        assert not fm.load_script(tutils.test_data.path("scripts/all.py"))
        err = tutils.terr()
        err.reply = controller.DummyReply()
        fm.handle_error(err)
        assert fm.scripts[0].ns["log"][-1] == "error"

    def test_duplicate_flow(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        f = tutils.tflow_full()
        f = fm.load_flow(f)
        assert s.flow_count() == 1
        f2 = fm.duplicate_flow(f)
        assert f2.response
        assert s.flow_count() == 2
        assert s.index(f2) == 1

    def test_all(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        fm.anticache = True
        fm.anticomp = True
        req = tutils.treq()
        fm.handle_clientconnect(req.flow.client_conn)

        f = fm.handle_request(req)
        assert s.flow_count() == 1

        resp = tutils.tresp(req)
        fm.handle_response(resp)
        assert s.flow_count() == 1

        rx = tutils.tresp()
        rx.flow = None
        assert not fm.handle_response(rx)

        fm.handle_clientdisconnect(req.flow.client_conn)

        f.error = Error("msg")
        f.error.reply = controller.DummyReply()
        fm.handle_error(f.error)

        fm.load_script(tutils.test_data.path("scripts/a.py"))
        fm.shutdown()

    def test_client_playback(self):
        s = flow.State()

        f = tutils.tflow_full()
        pb = [tutils.tflow_full(), f]
        fm = flow.FlowMaster(None, s)
        assert not fm.start_server_playback(pb, False, [], False, False)
        assert not fm.start_client_playback(pb, False)

        q = Queue.Queue()
        assert not fm.state.flow_count()
        fm.tick(q)
        assert fm.state.flow_count()

        f.error = Error("error")
        f.error.reply = controller.DummyReply()
        fm.handle_error(f.error)

    def test_server_playback(self):
        controller.should_exit = False
        s = flow.State()

        f = tutils.tflow()
        f.response = tutils.tresp(f.request)
        pb = [f]

        fm = flow.FlowMaster(None, s)
        fm.refresh_server_playback = True
        assert not fm.do_server_playback(tutils.tflow())

        fm.start_server_playback(pb, False, [], False, False)
        assert fm.do_server_playback(tutils.tflow())

        fm.start_server_playback(pb, False, [], True, False)
        r = tutils.tflow()
        r.request.content = "gibble"
        assert not fm.do_server_playback(r)
        assert fm.do_server_playback(tutils.tflow())

        fm.start_server_playback(pb, False, [], True, False)
        q = Queue.Queue()
        fm.tick(q)
        assert controller.should_exit

        fm.stop_server_playback()
        assert not fm.server_playback

    def test_server_playback_kill(self):
        s = flow.State()
        f = tutils.tflow()
        f.response = tutils.tresp(f.request)
        pb = [f]
        fm = flow.FlowMaster(None, s)
        fm.refresh_server_playback = True
        fm.start_server_playback(pb, True, [], False, False)

        f = tutils.tflow()
        f.request.host = "nonexistent"
        fm.process_new_request(f)
        assert "killed" in f.error.msg

    def test_stickycookie(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        assert "Invalid" in fm.set_stickycookie("~h")
        fm.set_stickycookie(".*")
        assert fm.stickycookie_state
        fm.set_stickycookie(None)
        assert not fm.stickycookie_state

        fm.set_stickycookie(".*")
        tf = tutils.tflow_full()
        tf.response.headers["set-cookie"] = ["foo=bar"]
        fm.handle_request(tf.request)
        fm.handle_response(tf.response)
        assert fm.stickycookie_state.jar
        assert not "cookie" in tf.request.headers
        tf = tf.copy()
        fm.handle_request(tf.request)
        assert tf.request.headers["cookie"] == ["foo=bar"]

    def test_stickyauth(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        assert "Invalid" in fm.set_stickyauth("~h")
        fm.set_stickyauth(".*")
        assert fm.stickyauth_state
        fm.set_stickyauth(None)
        assert not fm.stickyauth_state

        fm.set_stickyauth(".*")
        tf = tutils.tflow_full()
        tf.request.headers["authorization"] = ["foo"]
        fm.handle_request(tf.request)

        f = tutils.tflow_full()
        assert fm.stickyauth_state.hosts
        assert not "authorization" in f.request.headers
        fm.handle_request(f.request)
        assert f.request.headers["authorization"] == ["foo"]

    def test_stream(self):
        with tutils.tmpdir() as tdir:
            p = os.path.join(tdir, "foo")
            def r():
                r = flow.FlowReader(open(p,"rb"))
                return list(r.stream())

            s = flow.State()
            fm = flow.FlowMaster(None, s)
            tf = tutils.tflow_full()

            fm.start_stream(file(p, "ab"), None)
            fm.handle_request(tf.request)
            fm.handle_response(tf.response)
            fm.stop_stream()

            assert r()[0].response

            tf = tutils.tflow()
            fm.start_stream(file(p, "ab"), None)
            fm.handle_request(tf.request)
            fm.shutdown()

            assert not r()[1].response

class TestRequest:
    def test_simple(self):
        r = tutils.treq()
        u = r.get_url()
        assert r.set_url(u)
        assert not r.set_url("")
        assert r.get_url() == u
        assert r._assemble()
        assert r.size() == len(r._assemble())

        r2 = r.copy()
        assert r == r2

        r.content = None
        assert r._assemble()
        assert r.size() == len(r._assemble())

        r.content = CONTENT_MISSING
        tutils.raises("Cannot assemble flow with CONTENT_MISSING", r._assemble)

    def test_get_url(self):
        r = tutils.tflow().request

        assert r.get_url() == "http://address:22/path"

        r.flow.server_conn.ssl_established = True
        assert r.get_url() == "https://address:22/path"

        r.flow.server_conn.address = tcp.Address(("host", 42))
        assert r.get_url() == "https://host:42/path"

        r.host = "address"
        r.port = 22
        assert r.get_url() == "https://address:22/path"

        assert r.get_url(hostheader=True) == "https://address:22/path"
        r.headers["Host"] = ["foo.com"]
        assert r.get_url() == "https://address:22/path"
        assert r.get_url(hostheader=True) == "https://foo.com:22/path"

    def test_path_components(self):
        r = tutils.treq()
        r.path = "/"
        assert r.get_path_components() == []
        r.path = "/foo/bar"
        assert r.get_path_components() == ["foo", "bar"]
        q = flow.ODict()
        q["test"] = ["123"]
        r.set_query(q)
        assert r.get_path_components() == ["foo", "bar"]

        r.set_path_components([])
        assert r.get_path_components() == []
        r.set_path_components(["foo"])
        assert r.get_path_components() == ["foo"]
        r.set_path_components(["/oo"])
        assert r.get_path_components() == ["/oo"]
        assert "%2F" in r.path

    def test_getset_form_urlencoded(self):
        d = flow.ODict([("one", "two"), ("three", "four")])
        r = tutils.treq(content=utils.urlencode(d.lst))
        r.headers["content-type"] = [protocol.http.HDR_FORM_URLENCODED]
        assert r.get_form_urlencoded() == d

        d = flow.ODict([("x", "y")])
        r.set_form_urlencoded(d)
        assert r.get_form_urlencoded() == d

        r.headers["content-type"] = ["foo"]
        assert not r.get_form_urlencoded()

    def test_getset_query(self):
        h = flow.ODictCaseless()

        r = tutils.treq()
        r.path = "/foo?x=y&a=b"
        q = r.get_query()
        assert q.lst == [("x", "y"), ("a", "b")]

        r.path = "/"
        q = r.get_query()
        assert not q

        r.path = "/?adsfa"
        q = r.get_query()
        assert q.lst == [("adsfa", "")]

        r.path = "/foo?x=y&a=b"
        assert r.get_query()
        r.set_query(flow.ODict([]))
        assert not r.get_query()
        qv = flow.ODict([("a", "b"), ("c", "d")])
        r.set_query(qv)
        assert r.get_query() == qv

    def test_anticache(self):
        h = flow.ODictCaseless()
        r = tutils.treq()
        r.headers = h
        h["if-modified-since"] = ["test"]
        h["if-none-match"] = ["test"]
        r.anticache()
        assert not "if-modified-since" in r.headers
        assert not "if-none-match" in r.headers

    def test_replace(self):
        r = tutils.treq()
        r.path = "path/foo"
        r.headers["Foo"] = ["fOo"]
        r.content = "afoob"
        assert r.replace("foo(?i)", "boo") == 4
        assert r.path == "path/boo"
        assert not "foo" in r.content
        assert r.headers["boo"] == ["boo"]

    def test_constrain_encoding(self):
        r = tutils.treq()
        r.headers["accept-encoding"] = ["gzip", "oink"]
        r.constrain_encoding()
        assert "oink" not in r.headers["accept-encoding"]

    def test_decodeencode(self):
        r = tutils.treq()
        r.headers["content-encoding"] = ["identity"]
        r.content = "falafel"
        r.decode()
        assert not r.headers["content-encoding"]
        assert r.content == "falafel"

        r = tutils.treq()
        r.content = "falafel"
        assert not r.decode()

        r = tutils.treq()
        r.headers["content-encoding"] = ["identity"]
        r.content = "falafel"
        r.encode("identity")
        assert r.headers["content-encoding"] == ["identity"]
        assert r.content == "falafel"

        r = tutils.treq()
        r.headers["content-encoding"] = ["identity"]
        r.content = "falafel"
        r.encode("gzip")
        assert r.headers["content-encoding"] == ["gzip"]
        assert r.content != "falafel"
        r.decode()
        assert not r.headers["content-encoding"]
        assert r.content == "falafel"

    def test_get_decoded_content(self):
        r = tutils.treq()
        r.content = None
        r.headers["content-encoding"] = ["identity"]
        assert r.get_decoded_content() == None

        r.content = "falafel"
        r.encode("gzip")
        assert r.get_decoded_content() == "falafel"

    def test_get_cookies_none(self):
        h = flow.ODictCaseless()
        r = tutils.treq()
        r.headers = h
        assert r.get_cookies() is None

    def test_get_cookies_single(self):
        h = flow.ODictCaseless()
        h["Cookie"] = ["cookiename=cookievalue"]
        r = tutils.treq()
        r.headers = h
        result = r.get_cookies()
        assert len(result)==1
        assert result['cookiename']==('cookievalue',{})

    def test_get_cookies_double(self):
        h = flow.ODictCaseless()
        h["Cookie"] = ["cookiename=cookievalue;othercookiename=othercookievalue"]
        r = tutils.treq()
        r.headers = h
        result = r.get_cookies()
        assert len(result)==2
        assert result['cookiename']==('cookievalue',{})
        assert result['othercookiename']==('othercookievalue',{})

    def test_get_cookies_withequalsign(self):
        h = flow.ODictCaseless()
        h["Cookie"] = ["cookiename=coo=kievalue;othercookiename=othercookievalue"]
        r = tutils.treq()
        r.headers = h
        result = r.get_cookies()
        assert len(result)==2
        assert result['cookiename']==('coo=kievalue',{})
        assert result['othercookiename']==('othercookievalue',{})

    def test_header_size(self):
        h = flow.ODictCaseless()
        h["headername"] = ["headervalue"]
        r = tutils.treq()
        r.headers = h
        result = len(r._assemble_headers())
        assert result == 62

    def test_get_content_type(self):
        h = flow.ODictCaseless()
        h["Content-Type"] = ["text/plain"]
        resp = tutils.tresp()
        resp.headers = h
        assert resp.headers.get_first("content-type") == "text/plain"

class TestResponse:
    def test_simple(self):
        f = tutils.tflow_full()
        resp = f.response
        assert resp._assemble()
        assert resp.size() == len(resp._assemble())

        resp2 = resp.copy()
        assert resp2 == resp

        resp.content = None
        assert resp._assemble()
        assert resp.size() == len(resp._assemble())

        resp.content = CONTENT_MISSING
        tutils.raises("Cannot assemble flow with CONTENT_MISSING", resp._assemble)

    def test_refresh(self):
        r = tutils.tresp()
        n = time.time()
        r.headers["date"] = [email.utils.formatdate(n)]
        pre = r.headers["date"]
        r.refresh(n)
        assert pre == r.headers["date"]
        r.refresh(n+60)

        d = email.utils.parsedate_tz(r.headers["date"][0])
        d = email.utils.mktime_tz(d)
        # Weird that this is not exact...
        assert abs(60-(d-n)) <= 1

        r.headers["set-cookie"] = ["MOO=BAR; Expires=Tue, 08-Mar-2011 00:20:38 GMT; Path=foo.com; Secure"]
        r.refresh()

    def test_refresh_cookie(self):
        r = tutils.tresp()

        # Invalid expires format, sent to us by Reddit.
        c = "rfoo=bar; Domain=reddit.com; expires=Thu, 31 Dec 2037 23:59:59 GMT; Path=/"
        assert r._refresh_cookie(c, 60)

        c = "MOO=BAR; Expires=Tue, 08-Mar-2011 00:20:38 GMT; Path=foo.com; Secure"
        assert "00:21:38" in r._refresh_cookie(c, 60)

    def test_replace(self):
        r = tutils.tresp()
        r.headers["Foo"] = ["fOo"]
        r.content = "afoob"
        assert r.replace("foo(?i)", "boo") == 3
        assert not "foo" in r.content
        assert r.headers["boo"] == ["boo"]

    def test_decodeencode(self):
        r = tutils.tresp()
        r.headers["content-encoding"] = ["identity"]
        r.content = "falafel"
        assert r.decode()
        assert not r.headers["content-encoding"]
        assert r.content == "falafel"

        r = tutils.tresp()
        r.headers["content-encoding"] = ["identity"]
        r.content = "falafel"
        r.encode("identity")
        assert r.headers["content-encoding"] == ["identity"]
        assert r.content == "falafel"

        r = tutils.tresp()
        r.headers["content-encoding"] = ["identity"]
        r.content = "falafel"
        r.encode("gzip")
        assert r.headers["content-encoding"] == ["gzip"]
        assert r.content != "falafel"
        assert r.decode()
        assert not r.headers["content-encoding"]
        assert r.content == "falafel"

        r.headers["content-encoding"] = ["gzip"]
        assert not r.decode()
        assert r.content == "falafel"

    def test_header_size(self):
        r = tutils.tresp()
        result = len(r._assemble_headers())
        assert result==44

    def test_get_cookies_none(self):
        h = flow.ODictCaseless()
        resp = tutils.tresp()
        resp.headers = h
        assert not resp.get_cookies()

    def test_get_cookies_simple(self):
        h = flow.ODictCaseless()
        h["Set-Cookie"] = ["cookiename=cookievalue"]
        resp = tutils.tresp()
        resp.headers = h
        result = resp.get_cookies()
        assert len(result)==1
        assert "cookiename" in result
        assert result["cookiename"] == ("cookievalue", {})

    def test_get_cookies_with_parameters(self):
        h = flow.ODictCaseless()
        h["Set-Cookie"] = ["cookiename=cookievalue;domain=example.com;expires=Wed Oct  21 16:29:41 2015;path=/; HttpOnly"]
        resp = tutils.tresp()
        resp.headers = h
        result = resp.get_cookies()
        assert len(result)==1
        assert "cookiename" in result
        assert result["cookiename"][0] == "cookievalue"
        assert len(result["cookiename"][1])==4
        assert result["cookiename"][1]["domain"]=="example.com"
        assert result["cookiename"][1]["expires"]=="Wed Oct  21 16:29:41 2015"
        assert result["cookiename"][1]["path"]=="/"
        assert result["cookiename"][1]["httponly"]==""

    def test_get_cookies_no_value(self):
        h = flow.ODictCaseless()
        h["Set-Cookie"] = ["cookiename=; Expires=Thu, 01-Jan-1970 00:00:01 GMT; path=/"]
        resp = tutils.tresp()
        resp.headers = h
        result = resp.get_cookies()
        assert len(result)==1
        assert "cookiename" in result
        assert result["cookiename"][0] == ""
        assert len(result["cookiename"][1])==2

    def test_get_cookies_twocookies(self):
        h = flow.ODictCaseless()
        h["Set-Cookie"] = ["cookiename=cookievalue","othercookie=othervalue"]
        resp = tutils.tresp()
        resp.headers = h
        result = resp.get_cookies()
        assert len(result)==2
        assert "cookiename" in result
        assert result["cookiename"] == ("cookievalue", {})
        assert "othercookie" in result
        assert result["othercookie"] == ("othervalue", {})

    def test_get_content_type(self):
        h = flow.ODictCaseless()
        h["Content-Type"] = ["text/plain"]
        resp = tutils.tresp()
        resp.headers = h
        assert resp.headers.get_first("content-type") == "text/plain"


class TestError:
    def test_getset_state(self):
        e = Error("Error")
        state = e._get_state()
        assert Error._from_state(state) == e

        assert e.copy()

        e2 = Error("bar")
        assert not e == e2
        e._load_state(e2._get_state())
        assert e == e2


        e3 = e.copy()
        assert e3 == e


class TestClientConnection:
    def test_state(self):

        c = tutils.tclient_conn()
        assert ClientConnection._from_state(c._get_state()) == c

        c2 = tutils.tclient_conn()
        c2.address.address = (c2.address.host, 4242)
        assert not c == c2

        c2.timestamp_start = 42
        c._load_state(c2._get_state())
        assert c.timestamp_start == 42

        c3 = c.copy()
        assert c3 == c

        assert str(c)


def test_decoded():
    r = tutils.treq()
    assert r.content == "content"
    assert not r.headers["content-encoding"]
    r.encode("gzip")
    assert r.headers["content-encoding"]
    assert r.content != "content"
    with decoded(r):
        assert not r.headers["content-encoding"]
        assert r.content == "content"
    assert r.headers["content-encoding"]
    assert r.content != "content"

    with decoded(r):
        r.content = "foo"

    assert r.content != "foo"
    r.decode()
    assert r.content == "foo"


def test_replacehooks():
    h = flow.ReplaceHooks()
    h.add("~q", "foo", "bar")
    assert h.lst

    h.set(
        [
            (".*", "one", "two"),
            (".*", "three", "four"),
        ]
    )
    assert h.count() == 2

    h.clear()
    assert not h.lst

    h.add("~q", "foo", "bar")
    h.add("~s", "foo", "bar")

    v = h.get_specs()
    assert v == [('~q', 'foo', 'bar'), ('~s', 'foo', 'bar')]
    assert h.count() == 2
    h.clear()
    assert h.count() == 0

    f = tutils.tflow()
    f.request.content = "foo"
    h.add("~s", "foo", "bar")
    h.run(f)
    assert f.request.content == "foo"

    f = tutils.tflow_full()
    f.request.content = "foo"
    f.response.content = "foo"
    h.run(f)
    assert f.response.content == "bar"
    assert f.request.content == "foo"

    f = tutils.tflow()
    h.clear()
    h.add("~q", "foo", "bar")
    f.request.content = "foo"
    h.run(f)
    assert f.request.content == "bar"

    assert not h.add("~", "foo", "bar")
    assert not h.add("foo", "*", "bar")


def test_setheaders():
    h = flow.SetHeaders()
    h.add("~q", "foo", "bar")
    assert h.lst

    h.set(
        [
            (".*", "one", "two"),
            (".*", "three", "four"),
        ]
    )
    assert h.count() == 2

    h.clear()
    assert not h.lst

    h.add("~q", "foo", "bar")
    h.add("~s", "foo", "bar")

    v = h.get_specs()
    assert v == [('~q', 'foo', 'bar'), ('~s', 'foo', 'bar')]
    assert h.count() == 2
    h.clear()
    assert h.count() == 0

    f = tutils.tflow()
    f.request.content = "foo"
    h.add("~s", "foo", "bar")
    h.run(f)
    assert f.request.content == "foo"


    h.clear()
    h.add("~s", "one", "two")
    h.add("~s", "one", "three")
    f = tutils.tflow_full()
    f.request.headers["one"] = ["xxx"]
    f.response.headers["one"] = ["xxx"]
    h.run(f)
    assert f.request.headers["one"] == ["xxx"]
    assert f.response.headers["one"] == ["two", "three"]

    h.clear()
    h.add("~q", "one", "two")
    h.add("~q", "one", "three")
    f = tutils.tflow()
    f.request.headers["one"] = ["xxx"]
    h.run(f)
    assert f.request.headers["one"] == ["two", "three"]

    assert not h.add("~", "foo", "bar")

########NEW FILE########
__FILENAME__ = test_fuzzing
import tservers

"""
    A collection of errors turned up by fuzzing. Errors are integrated here
    after being fixed to check for regressions.
"""

class TestFuzzy(tservers.HTTPProxTest):
    def test_idna_err(self):
        req = r'get:"http://localhost:%s":i10,"\xc6"'
        p = self.pathoc()
        assert p.request(req%self.server.port).status_code == 400

    def test_nullbytes(self):
        req = r'get:"http://localhost:%s":i19,"\x00"'
        p = self.pathoc()
        assert p.request(req%self.server.port).status_code == 400

    def test_invalid_ports(self):
        req = 'get:"http://localhost:999999"'
        p = self.pathoc()
        assert p.request(req).status_code == 400

    def test_invalid_ipv6_url(self):
        req = 'get:"http://localhost:%s":i13,"["'
        p = self.pathoc()
        assert p.request(req%self.server.port).status_code == 400

    def test_invalid_upstream(self):
        req = r"get:'http://localhost:%s/p/200:i10,\'+\''"
        p = self.pathoc()
        assert p.request(req%self.server.port).status_code == 502

    def test_upstream_disconnect(self):
        req = r'200:d0'
        p = self.pathod(req)
        assert p.status_code == 502



########NEW FILE########
__FILENAME__ = test_platform_pf
import tutils
from libmproxy.platform import pf


class TestLookup:
    def test_simple(self):
        p = tutils.test_data.path("data/pf01")
        d = open(p,"rb").read()
        assert pf.lookup("192.168.1.111", 40000, d) == ("5.5.5.5", 80)
        assert not pf.lookup("192.168.1.112", 40000, d)
        assert not pf.lookup("192.168.1.111", 40001, d)



########NEW FILE########
__FILENAME__ = test_protocol_http
from libmproxy.protocol.http import *
from libmproxy.protocol import KILL
from cStringIO import StringIO
import tutils, tservers


def test_HttpAuthenticationError():
    x = HttpAuthenticationError({"foo": "bar"})
    assert str(x)
    assert "foo" in x.headers


def test_stripped_chunked_encoding_no_content():
    """
    https://github.com/mitmproxy/mitmproxy/issues/186
    """
    r = tutils.tresp(content="")
    r.headers["Transfer-Encoding"] = ["chunked"]
    assert "Content-Length" in r._assemble_headers()

    r = tutils.treq(content="")
    r.headers["Transfer-Encoding"] = ["chunked"]
    assert "Content-Length" in r._assemble_headers()


class TestHTTPRequest:
    def test_asterisk_form(self):
        s = StringIO("OPTIONS * HTTP/1.1")
        f = tutils.tflow_noreq()
        f.request = HTTPRequest.from_stream(s)
        assert f.request.form_in == "relative"
        x = f.request._assemble()
        assert f.request._assemble() == "OPTIONS * HTTP/1.1\r\nHost: address:22\r\n\r\n"

    def test_origin_form(self):
        s = StringIO("GET /foo\xff HTTP/1.1")
        tutils.raises("Bad HTTP request line", HTTPRequest.from_stream, s)

    def test_authority_form(self):
        s = StringIO("CONNECT oops-no-port.com HTTP/1.1")
        tutils.raises("Bad HTTP request line", HTTPRequest.from_stream, s)
        s = StringIO("CONNECT address:22 HTTP/1.1")
        r = HTTPRequest.from_stream(s)
        assert r._assemble() == "CONNECT address:22 HTTP/1.1\r\nHost: address:22\r\n\r\n"

    def test_absolute_form(self):
        s = StringIO("GET oops-no-protocol.com HTTP/1.1")
        tutils.raises("Bad HTTP request line", HTTPRequest.from_stream, s)
        s = StringIO("GET http://address:22/ HTTP/1.1")
        r = HTTPRequest.from_stream(s)
        assert r._assemble() == "GET http://address:22/ HTTP/1.1\r\nHost: address:22\r\n\r\n"

    def test_assemble_unknown_form(self):
        r = tutils.treq()
        tutils.raises("Invalid request form", r._assemble, "antiauthority")


    def test_set_url(self):
        r = tutils.treq_absolute()
        r.set_url("https://otheraddress:42/ORLY")
        assert r.scheme == "https"
        assert r.host == "otheraddress"
        assert r.port == 42
        assert r.path == "/ORLY"


class TestHTTPResponse:
    def test_read_from_stringio(self):
        _s = "HTTP/1.1 200 OK\r\n" \
             "Content-Length: 7\r\n" \
             "\r\n"\
             "content\r\n" \
             "HTTP/1.1 204 OK\r\n" \
             "\r\n"
        s = StringIO(_s)
        r = HTTPResponse.from_stream(s, "GET")
        assert r.code == 200
        assert r.content == "content"
        assert HTTPResponse.from_stream(s, "GET").code == 204

        s = StringIO(_s)
        r = HTTPResponse.from_stream(s, "HEAD")  # HEAD must not have content by spec. We should leave it on the pipe.
        assert r.code == 200
        assert r.content == ""
        tutils.raises("Invalid server response: 'content", HTTPResponse.from_stream, s, "GET")


class TestInvalidRequests(tservers.HTTPProxTest):
    ssl = True
    def test_double_connect(self):
        p = self.pathoc()
        r = p.request("connect:'%s:%s'" % ("127.0.0.1", self.server2.port))
        assert r.status_code == 400
        assert "Must not CONNECT on already encrypted connection" in r.content

    def test_relative_request(self):
        p = self.pathoc_raw()
        p.connect()
        r = p.request("get:/p/200")
        assert r.status_code == 400
        assert "Invalid HTTP request form" in r.content


class TestProxyChaining(tservers.HTTPChainProxyTest):
    def test_all(self):
        self.chain[1].tmaster.replacehooks.add("~q", "foo", "bar") # replace in request
        self.chain[0].tmaster.replacehooks.add("~q", "foo", "oh noes!")
        self.proxy.tmaster.replacehooks.add("~q", "bar", "baz")
        self.chain[0].tmaster.replacehooks.add("~s", "baz", "ORLY")  # replace in response

        p = self.pathoc()
        req = p.request("get:'%s/p/418:b\"foo\"'" % self.server.urlbase)
        assert req.content == "ORLY"
        assert req.status_code == 418

class TestProxyChainingSSL(tservers.HTTPChainProxyTest):
    ssl = True
    def test_simple(self):
        p = self.pathoc()
        req = p.request("get:'/p/418:b\"content\"'")
        assert req.content == "content"
        assert req.status_code == 418

        assert self.chain[1].tmaster.state.flow_count() == 2  # CONNECT from pathoc to chain[0],
                                                              # request from pathoc to chain[0]
        assert self.chain[0].tmaster.state.flow_count() == 2  # CONNECT from chain[1] to proxy,
                                                              # request from chain[1] to proxy
        assert self.proxy.tmaster.state.flow_count() == 1  # request from chain[0] (regular proxy doesn't store CONNECTs)

class TestProxyChainingSSLReconnect(tservers.HTTPChainProxyTest):
    ssl = True

    def test_reconnect(self):
        """
        Tests proper functionality of ConnectionHandler.server_reconnect mock.
        If we have a disconnect on a secure connection that's transparently proxified to
        an upstream http proxy, we need to send the CONNECT request again.
        """
        def kill_requests(master, attr, exclude):
            k = [0]  # variable scope workaround: put into array
            _func = getattr(master, attr)
            def handler(r):
                k[0] += 1
                if not (k[0] in exclude):
                    r.flow.client_conn.finish()
                    r.flow.error = Error("terminated")
                    r.reply(KILL)
                return _func(r)
            setattr(master, attr, handler)

        kill_requests(self.proxy.tmaster, "handle_request",
                      exclude=[
                              # fail first request
                          2,  # allow second request
                      ])

        kill_requests(self.chain[0].tmaster, "handle_request",
                      exclude=[
                          1,  # CONNECT
                              # fail first request
                          3,  # reCONNECT
                          4,  # request
                      ])

        p = self.pathoc()
        req = p.request("get:'/p/418:b\"content\"'")
        assert self.chain[1].tmaster.state.flow_count() == 2  # CONNECT and request
        assert self.chain[0].tmaster.state.flow_count() == 4  # CONNECT, failing request,
                                                              # reCONNECT, request
        assert self.proxy.tmaster.state.flow_count() == 2  # failing request, request
                                                           # (doesn't store (repeated) CONNECTs from chain[0]
                                                           #  as it is a regular proxy)
        assert req.content == "content"
        assert req.status_code == 418

        assert not self.proxy.tmaster.state._flow_list[0].response  # killed
        assert self.proxy.tmaster.state._flow_list[1].response

        assert self.chain[1].tmaster.state._flow_list[0].request.form_in == "authority"
        assert self.chain[1].tmaster.state._flow_list[1].request.form_in == "relative"

        assert self.chain[0].tmaster.state._flow_list[0].request.form_in == "authority"
        assert self.chain[0].tmaster.state._flow_list[1].request.form_in == "relative"
        assert self.chain[0].tmaster.state._flow_list[2].request.form_in == "authority"
        assert self.chain[0].tmaster.state._flow_list[3].request.form_in == "relative"

        assert self.proxy.tmaster.state._flow_list[0].request.form_in == "relative"
        assert self.proxy.tmaster.state._flow_list[1].request.form_in == "relative"

        req = p.request("get:'/p/418:b\"content2\"'")

        assert req.status_code == 502
        assert self.chain[1].tmaster.state.flow_count() == 3  # + new request
        assert self.chain[0].tmaster.state.flow_count() == 6  # + new request, repeated CONNECT from chain[1]
                                                              # (both terminated)
        assert self.proxy.tmaster.state.flow_count() == 2  # nothing happened here

########NEW FILE########
__FILENAME__ = test_proxy
import argparse
from libmproxy import cmdline
from libmproxy.proxy.config import process_proxy_options
from libmproxy.proxy.connection import ServerConnection
from libmproxy.proxy.primitives import ProxyError
from libmproxy.proxy.server import DummyServer, ProxyServer
import tutils
from libpathod import test
from netlib import http, tcp
import mock


def test_proxy_error():
    p = ProxyError(111, "msg")
    assert str(p)


class TestServerConnection:
    def setUp(self):
        self.d = test.Daemon()

    def tearDown(self):
        self.d.shutdown()

    def test_simple(self):
        sc = ServerConnection((self.d.IFACE, self.d.port), None)
        sc.connect()
        r = tutils.treq()
        r.flow.server_conn = sc
        r.path = "/p/200:da"
        sc.send(r._assemble())
        assert http.read_response(sc.rfile, r.method, 1000)
        assert self.d.last_log()

        sc.finish()

    def test_terminate_error(self):
        sc = ServerConnection((self.d.IFACE, self.d.port), None)
        sc.connect()
        sc.connection = mock.Mock()
        sc.connection.recv = mock.Mock(return_value=False)
        sc.connection.flush = mock.Mock(side_effect=tcp.NetLibDisconnect)
        sc.finish()


class TestProcessProxyOptions:
    def p(self, *args):
        parser = tutils.MockParser()
        cmdline.common_options(parser)
        opts = parser.parse_args(args=args)
        return parser, process_proxy_options(parser, opts)

    def assert_err(self, err, *args):
        tutils.raises(err, self.p, *args)

    def assert_noerr(self, *args):
        m, p = self.p(*args)
        assert p
        return p

    def test_simple(self):
        assert self.p()

    def test_confdir(self):
        with tutils.tmpdir() as confdir:
            self.assert_noerr("--confdir", confdir)

    @mock.patch("libmproxy.platform.resolver", None)
    def test_no_transparent(self):
        self.assert_err("transparent mode not supported", "-T")

    @mock.patch("libmproxy.platform.resolver")
    def test_transparent_reverse(self, o):
        self.assert_err("mutually exclusive", "-R", "http://localhost", "-T")
        self.assert_noerr("-T")
        self.assert_err("Invalid server specification", "-R", "reverse")
        self.assert_noerr("-R", "http://localhost")

    def test_client_certs(self):
        with tutils.tmpdir() as confdir:
            self.assert_noerr("--client-certs", confdir)
            self.assert_err("directory does not exist", "--client-certs", "nonexistent")

    def test_certs(self):
        with tutils.tmpdir() as confdir:
            self.assert_noerr("--cert", tutils.test_data.path("data/testkey.pem"))
            self.assert_err("does not exist", "--cert", "nonexistent")

    def test_auth(self):
        p = self.assert_noerr("--nonanonymous")
        assert p.authenticator

        p = self.assert_noerr("--htpasswd", tutils.test_data.path("data/htpasswd"))
        assert p.authenticator
        self.assert_err("invalid htpasswd file", "--htpasswd", tutils.test_data.path("data/htpasswd.invalid"))

        p = self.assert_noerr("--singleuser", "test:test")
        assert p.authenticator
        self.assert_err("invalid single-user specification", "--singleuser", "test")


class TestProxyServer:
    @tutils.SkipWindows # binding to 0.0.0.0:1 works without special permissions on Windows
    def test_err(self):
        parser = argparse.ArgumentParser()
        cmdline.common_options(parser)
        opts = parser.parse_args(args=[])
        tutils.raises("error starting proxy server", ProxyServer, opts, 1)


class TestDummyServer:
    def test_simple(self):
        d = DummyServer(None)
        d.start_slave()
        d.shutdown()


########NEW FILE########
__FILENAME__ = test_script
from libmproxy import script, flow
import tutils
import shlex
import os
import time
import mock


class TestScript:
    def test_simple(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        sp = tutils.test_data.path("scripts/a.py")
        p = script.Script("%s --var 40"%sp, fm)

        assert "here" in p.ns
        assert p.run("here") == (True, 41)
        assert p.run("here") == (True, 42)

        ret = p.run("errargs")
        assert not ret[0]
        assert len(ret[1]) == 2

        # Check reload
        p.load()
        assert p.run("here") == (True, 41)

    def test_duplicate_flow(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        fm.load_script(tutils.test_data.path("scripts/duplicate_flow.py"))
        r = tutils.treq()
        fm.handle_request(r)
        assert fm.state.flow_count() == 2
        assert not fm.state.view[0].request.is_replay
        assert fm.state.view[1].request.is_replay

    def test_err(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)

        tutils.raises(
            "not found",
            script.Script, "nonexistent", fm
        )

        tutils.raises(
            "not a file",
            script.Script, tutils.test_data.path("scripts"), fm
        )

        tutils.raises(
            script.ScriptError,
            script.Script, tutils.test_data.path("scripts/syntaxerr.py"), fm
        )

        tutils.raises(
            script.ScriptError,
            script.Script, tutils.test_data.path("scripts/loaderr.py"), fm
        )

    def test_concurrent(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        fm.load_script(tutils.test_data.path("scripts/concurrent_decorator.py"))

        with mock.patch("libmproxy.controller.DummyReply.__call__") as m:
            r1, r2 = tutils.treq(), tutils.treq()
            t_start = time.time()
            fm.handle_request(r1)
            r1.reply()
            fm.handle_request(r2)
            r2.reply()

            # Two instantiations
            assert m.call_count == 2
            assert (time.time() - t_start) < 0.09

    def test_concurrent2(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        s = script.Script(tutils.test_data.path("scripts/concurrent_decorator.py"), fm)
        s.load()
        f = tutils.tflow_full()
        f.error = tutils.terr(f.request)
        f.reply = f.request.reply

        with mock.patch("libmproxy.controller.DummyReply.__call__") as m:
            t_start = time.time()
            s.run("clientconnect", f)
            s.run("serverconnect", f)
            s.run("response", f)
            s.run("error", f)
            s.run("clientdisconnect", f)
            while (time.time() - t_start) < 1 and m.call_count <= 5:
                if m.call_count == 5:
                    return
                time.sleep(0.001)
            assert False

    def test_concurrent_err(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        tutils.raises(
            "decorator not supported for this method",
            script.Script, tutils.test_data.path("scripts/concurrent_decorator_err.py"), fm
        )


def test_command_parsing():
    s = flow.State()
    fm = flow.FlowMaster(None, s)
    absfilepath = os.path.normcase(tutils.test_data.path("scripts/a.py"))
    s = script.Script(absfilepath, fm)
    assert os.path.isfile(s.argv[0])



########NEW FILE########
__FILENAME__ = test_server
import socket, time
import mock
from netlib import tcp, http_auth, http
from libpathod import pathoc, pathod
import tutils, tservers
from libmproxy import flow
from libmproxy.protocol import KILL
from libmproxy.protocol.http import CONTENT_MISSING

"""
    Note that the choice of response code in these tests matters more than you
    might think. libcurl treats a 304 response code differently from, say, a
    200 response code - it will correctly terminate a 304 response with no
    content-length header, whereas it will block forever waiting for content
    for a 200 response.
"""

class CommonMixin:
    def test_large(self):
        assert len(self.pathod("200:b@50k").content) == 1024*50

    def test_replay(self):
        assert self.pathod("304").status_code == 304
        assert len(self.master.state.view) == 1
        l = self.master.state.view[0]
        assert l.response.code == 304
        l.request.path = "/p/305"
        rt = self.master.replay_request(l, block=True)
        assert l.response.code == 305

        # Disconnect error
        l.request.path = "/p/305:d0"
        rt = self.master.replay_request(l, block=True)
        assert l.error

        # Port error
        l.request.port = 1
        self.master.replay_request(l, block=True)
        assert l.error

    def test_http(self):
        f = self.pathod("304")
        assert f.status_code == 304

        l = self.master.state.view[0]
        assert l.client_conn.address
        assert "host" in l.request.headers
        assert l.response.code == 304

    def test_invalid_http(self):
        t = tcp.TCPClient(("127.0.0.1", self.proxy.port))
        t.connect()
        t.wfile.write("invalid\r\n\r\n")
        t.wfile.flush()
        line = t.rfile.readline()
        assert ("Bad Request" in line) or ("Bad Gateway" in line)



class AppMixin:
    def test_app(self):
        ret = self.app("/")
        assert ret.status_code == 200
        assert "mitmproxy" in ret.content



class TestHTTP(tservers.HTTPProxTest, CommonMixin, AppMixin):
    def test_app_err(self):
        p = self.pathoc()
        ret = p.request("get:'http://errapp/'")
        assert ret.status_code == 500
        assert "ValueError" in ret.content

    def test_invalid_connect(self):
        t = tcp.TCPClient(("127.0.0.1", self.proxy.port))
        t.connect()
        t.wfile.write("CONNECT invalid\n\n")
        t.wfile.flush()
        assert "Bad Request" in t.rfile.readline()

    def test_upstream_ssl_error(self):
        p = self.pathoc()
        ret = p.request("get:'https://localhost:%s/'"%self.server.port)
        assert ret.status_code == 400

    def test_connection_close(self):
        # Add a body, so we have a content-length header, which combined with
        # HTTP1.1 means the connection is kept alive.
        response = '%s/p/200:b@1'%self.server.urlbase

        # Lets sanity check that the connection does indeed stay open by
        # issuing two requests over the same connection
        p = self.pathoc()
        assert p.request("get:'%s'"%response)
        assert p.request("get:'%s'"%response)

        # Now check that the connection is closed as the client specifies
        p = self.pathoc()
        assert p.request("get:'%s':h'Connection'='close'"%response)
        tutils.raises("disconnect", p.request, "get:'%s'"%response)

    def test_reconnect(self):
        req = "get:'%s/p/200:b@1:da'"%self.server.urlbase
        p = self.pathoc()
        assert p.request(req)
        # Server has disconnected. Mitmproxy should detect this, and reconnect.
        assert p.request(req)
        assert p.request(req)

    def test_proxy_ioerror(self):
        # Tests a difficult-to-trigger condition, where an IOError is raised
        # within our read loop.
        with mock.patch("libmproxy.protocol.http.HTTPRequest.from_stream") as m:
            m.side_effect = IOError("error!")
            tutils.raises("server disconnect", self.pathod, "304")

    def test_get_connection_switching(self):
        def switched(l):
            for i in l:
                if "serverdisconnect" in i:
                    return True
        req = "get:'%s/p/200:b@1'"
        p = self.pathoc()
        assert p.request(req%self.server.urlbase)
        assert p.request(req%self.server2.urlbase)
        assert switched(self.proxy.log)

    def test_get_connection_err(self):
        p = self.pathoc()
        ret = p.request("get:'http://localhost:0'")
        assert ret.status_code == 502

    def test_blank_leading_line(self):
        p = self.pathoc()
        req = "get:'%s/p/201':i0,'\r\n'"
        assert p.request(req%self.server.urlbase).status_code == 201

    def test_invalid_headers(self):
        p = self.pathoc()
        req = p.request("get:'http://foo':h':foo'='bar'")
        assert req.status_code == 400

    def test_empty_chunked_content(self):
        """
        https://github.com/mitmproxy/mitmproxy/issues/186
        """
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.connect(("127.0.0.1", self.proxy.port))
        spec = '301:h"Transfer-Encoding"="chunked":r:b"0\\r\\n\\r\\n"'
        connection.send("GET http://localhost:%d/p/%s HTTP/1.1\r\n"%(self.server.port, spec))
        connection.send("\r\n");
        resp = connection.recv(50000)
        connection.close()
        assert "content-length" in resp.lower()


class TestHTTPAuth(tservers.HTTPProxTest):
    authenticator = http_auth.BasicProxyAuth(http_auth.PassManSingleUser("test", "test"), "realm")
    def test_auth(self):
        assert self.pathod("202").status_code == 407
        p = self.pathoc()
        ret = p.request("""
            get
            'http://localhost:%s/p/202'
            h'%s'='%s'
        """%(
            self.server.port,
            http_auth.BasicProxyAuth.AUTH_HEADER,
            http.assemble_http_basic_auth("basic", "test", "test")
        ))
        assert ret.status_code == 202


class TestHTTPConnectSSLError(tservers.HTTPProxTest):
    certfile = True
    def test_go(self):
        p = self.pathoc_raw()
        dst = ("localhost", self.proxy.port)
        p.connect(connect_to=dst)
        tutils.raises("400 - Bad Request", p.http_connect, dst)


class TestHTTPS(tservers.HTTPProxTest, CommonMixin):
    ssl = True
    ssloptions = pathod.SSLOptions(request_client_cert=True)
    clientcerts = True
    def test_clientcert(self):
        f = self.pathod("304")
        assert f.status_code == 304
        assert self.server.last_log()["request"]["clientcert"]["keyinfo"]

    def test_sni(self):
        f = self.pathod("304", sni="testserver.com")
        assert f.status_code == 304
        l = self.server.last_log()
        assert self.server.last_log()["request"]["sni"] == "testserver.com"

    def test_error_post_connect(self):
        p = self.pathoc()
        assert p.request("get:/:i0,'invalid\r\n\r\n'").status_code == 400


class TestHTTPSCertfile(tservers.HTTPProxTest, CommonMixin):
    ssl = True
    certfile = True
    def test_certfile(self):
        assert self.pathod("304")


class TestHTTPSNoCommonName(tservers.HTTPProxTest):
    """
    Test what happens if we get a cert without common name back.
    """
    ssl = True
    ssloptions=pathod.SSLOptions(
            certs = [
                ("*", tutils.test_data.path("data/no_common_name.pem"))
            ]
        )
    def test_http(self):
        f = self.pathod("202")
        assert f.sslinfo.certchain[0].get_subject().CN == "127.0.0.1"


class TestReverse(tservers.ReverseProxTest, CommonMixin):
    reverse = True


class TestTransparent(tservers.TransparentProxTest, CommonMixin):
    ssl = False


class TestTransparentSSL(tservers.TransparentProxTest, CommonMixin):
    ssl = True
    def test_sni(self):
        f = self.pathod("304", sni="testserver.com")
        assert f.status_code == 304
        l = self.server.last_log()
        assert l["request"]["sni"] == "testserver.com"

    def test_sslerr(self):
        p = pathoc.Pathoc(("localhost", self.proxy.port))
        p.connect()
        r = p.request("get:/")
        assert r.status_code == 502


class TestProxy(tservers.HTTPProxTest):
    def test_http(self):
        f = self.pathod("304")
        assert f.status_code == 304

        f = self.master.state.view[0]
        assert f.client_conn.address
        assert "host" in f.request.headers
        assert f.response.code == 304

    def test_response_timestamps(self):
        # test that we notice at least 2 sec delay between timestamps
        # in response object
        f = self.pathod("304:b@1k:p50,1")
        assert f.status_code == 304

        response = self.master.state.view[0].response
        assert 1 <= response.timestamp_end - response.timestamp_start <= 1.2

    def test_request_timestamps(self):
        # test that we notice a delay between timestamps in request object
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.connect(("127.0.0.1", self.proxy.port))

        # call pathod server, wait a second to complete the request
        connection.send("GET http://localhost:%d/p/304:b@1k HTTP/1.1\r\n"%self.server.port)
        time.sleep(1)
        connection.send("\r\n");
        connection.recv(50000)
        connection.close()

        request, response = self.master.state.view[0].request, self.master.state.view[0].response
        assert response.code == 304  # sanity test for our low level request
        assert 0.95 < (request.timestamp_end - request.timestamp_start) < 1.2 #time.sleep might be a little bit shorter than a second

    def test_request_timestamps_not_affected_by_client_time(self):
        # test that don't include user wait time in request's timestamps

        f = self.pathod("304:b@10k")
        assert f.status_code == 304
        f = self.pathod("304:b@10k")
        assert f.status_code == 304

        request = self.master.state.view[0].request
        assert request.timestamp_end - request.timestamp_start <= 0.1

        request = self.master.state.view[1].request
        assert request.timestamp_end - request.timestamp_start <= 0.1

    def test_request_tcp_setup_timestamp_presence(self):
        # tests that the client_conn a tcp connection has a tcp_setup_timestamp
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.connect(("localhost", self.proxy.port))
        connection.send("GET http://localhost:%d/p/304:b@1k HTTP/1.1\r\n"%self.server.port)
        connection.send("\r\n");
        connection.recv(5000)
        connection.send("GET http://localhost:%d/p/304:b@1k HTTP/1.1\r\n"%self.server.port)
        connection.send("\r\n");
        connection.recv(5000)
        connection.close()

        first_flow = self.master.state.view[0]
        second_flow = self.master.state.view[1]
        assert first_flow.server_conn.timestamp_tcp_setup
        assert first_flow.server_conn.timestamp_ssl_setup is None
        assert second_flow.server_conn.timestamp_tcp_setup
        assert first_flow.server_conn.timestamp_tcp_setup == second_flow.server_conn.timestamp_tcp_setup

    def test_request_ip(self):
        f = self.pathod("200:b@100")
        assert f.status_code == 200
        f = self.master.state.view[0]
        assert f.server_conn.peername == ("127.0.0.1", self.server.port)

class TestProxySSL(tservers.HTTPProxTest):
    ssl=True
    def test_request_ssl_setup_timestamp_presence(self):
        # tests that the ssl timestamp is present when ssl is used
        f = self.pathod("304:b@10k")
        assert f.status_code == 304
        first_request = self.master.state.view[0].request
        assert first_request.flow.server_conn.timestamp_ssl_setup


class MasterRedirectRequest(tservers.TestMaster):
    def handle_request(self, request):
        if request.path == "/p/201":
            url = request.get_url()
            new = "http://127.0.0.1:%s/p/201" % self.redirect_port

            request.set_url(new)
            request.set_url(new)
            request.flow.change_server(("127.0.0.1", self.redirect_port), False)
            request.set_url(url)
            tutils.raises("SSL handshake error", request.flow.change_server, ("127.0.0.1", self.redirect_port), True)
            request.set_url(new)
            request.set_url(url)
            request.set_url(new)
        tservers.TestMaster.handle_request(self, request)

    def handle_response(self, response):
        response.content = str(response.flow.client_conn.address.port)
        tservers.TestMaster.handle_response(self, response)


class TestRedirectRequest(tservers.HTTPProxTest):
    masterclass = MasterRedirectRequest

    def test_redirect(self):
        self.master.redirect_port = self.server2.port

        p = self.pathoc()

        self.server.clear_log()
        self.server2.clear_log()
        r1 = p.request("get:'%s/p/200'"%self.server.urlbase)
        assert r1.status_code == 200
        assert self.server.last_log()
        assert not self.server2.last_log()

        self.server.clear_log()
        self.server2.clear_log()
        r2 = p.request("get:'%s/p/201'"%self.server.urlbase)
        assert r2.status_code == 201
        assert not self.server.last_log()
        assert self.server2.last_log()

        self.server.clear_log()
        self.server2.clear_log()
        r3 = p.request("get:'%s/p/202'"%self.server.urlbase)
        assert r3.status_code == 202
        assert self.server.last_log()
        assert not self.server2.last_log()

        assert r3.content == r2.content == r1.content
        # Make sure that we actually use the same connection in this test case


class MasterFakeResponse(tservers.TestMaster):
    def handle_request(self, m):
        resp = tutils.tresp()
        m.reply(resp)


class TestFakeResponse(tservers.HTTPProxTest):
    masterclass = MasterFakeResponse
    def test_fake(self):
        f = self.pathod("200")
        assert "header_response" in f.headers.keys()


class MasterKillRequest(tservers.TestMaster):
    def handle_request(self, m):
        m.reply(KILL)


class TestKillRequest(tservers.HTTPProxTest):
    masterclass = MasterKillRequest
    def test_kill(self):
        tutils.raises("server disconnect", self.pathod, "200")
        # Nothing should have hit the server
        assert not self.server.last_log()


class MasterKillResponse(tservers.TestMaster):
    def handle_response(self, m):
        m.reply(KILL)


class TestKillResponse(tservers.HTTPProxTest):
    masterclass = MasterKillResponse
    def test_kill(self):
        tutils.raises("server disconnect", self.pathod, "200")
        # The server should have seen a request
        assert self.server.last_log()


class EResolver(tservers.TResolver):
    def original_addr(self, sock):
        return None


class TestTransparentResolveError(tservers.TransparentProxTest):
    resolver = EResolver
    def test_resolve_error(self):
        assert self.pathod("304").status_code == 502


class MasterIncomplete(tservers.TestMaster):
    def handle_request(self, m):
        resp = tutils.tresp()
        resp.content = CONTENT_MISSING
        m.reply(resp)


class TestIncompleteResponse(tservers.HTTPProxTest):
    masterclass = MasterIncomplete
    def test_incomplete(self):
        assert self.pathod("200").status_code == 502


class TestCertForward(tservers.HTTPProxTest):
    certforward = True
    ssl = True
    def test_app_err(self):
        tutils.raises("handshake error", self.pathod, "200:b@100")


########NEW FILE########
__FILENAME__ = test_utils
import json
from libmproxy import utils
import tutils

utils.CERT_SLEEP_TIME = 0


def test_format_timestamp():
    assert utils.format_timestamp(utils.timestamp())


def test_isBin():
    assert not utils.isBin("testing\n\r")
    assert utils.isBin("testing\x01")
    assert utils.isBin("testing\x0e")
    assert utils.isBin("testing\x7f")


def test_isXml():
    assert not utils.isXML("foo")
    assert utils.isXML("<foo")
    assert utils.isXML("  \n<foo")


def test_del_all():
    d = dict(a=1, b=2, c=3)
    utils.del_all(d, ["a", "x", "b"])
    assert d.keys() == ["c"]


def test_clean_hanging_newline():
    s = "foo\n"
    assert utils.clean_hanging_newline(s) == "foo"
    assert utils.clean_hanging_newline("foo") == "foo"


def test_pretty_size():
    assert utils.pretty_size(100) == "100B"
    assert utils.pretty_size(1024) == "1kB"
    assert utils.pretty_size(1024 + (1024/2.0)) == "1.5kB"
    assert utils.pretty_size(1024*1024) == "1MB"


def test_pkg_data():
    assert utils.pkg_data.path("console")
    tutils.raises("does not exist", utils.pkg_data.path, "nonexistent")


def test_pretty_json():
    s = json.dumps({"foo": 1})
    assert utils.pretty_json(s)
    assert not utils.pretty_json("moo")


def test_urldecode():
    s = "one=two&three=four"
    assert len(utils.urldecode(s)) == 2


def test_LRUCache():
    class Foo:
        ran = False
        @utils.LRUCache(2)
        def one(self, x):
            self.ran = True
            return x

    f = Foo()
    assert f.one(1) == 1
    assert f.ran
    f.ran = False
    assert f.one(1) == 1
    assert not f.ran

    f.ran = False
    assert f.one(1) == 1
    assert not f.ran
    assert f.one(2) == 2
    assert f.one(3) == 3
    assert f.ran

    f.ran = False
    assert f.one(1) == 1
    assert f.ran

    assert len(f._cached_one) == 2
    assert len(f._cachelist_one) == 2


def test_unparse_url():
    assert utils.unparse_url("http", "foo.com", 99, "") == "http://foo.com:99"
    assert utils.unparse_url("http", "foo.com", 80, "") == "http://foo.com"
    assert utils.unparse_url("https", "foo.com", 80, "") == "https://foo.com:80"
    assert utils.unparse_url("https", "foo.com", 443, "") == "https://foo.com"


def test_parse_size():
    assert not utils.parse_size("")
    assert utils.parse_size("1") == 1
    assert utils.parse_size("1k") == 1024
    assert utils.parse_size("1m") == 1024**2
    assert utils.parse_size("1g") == 1024**3
    tutils.raises(ValueError, utils.parse_size, "1f")
    tutils.raises(ValueError, utils.parse_size, "ak")


def test_parse_content_type():
    p = utils.parse_content_type
    assert p("text/html") == ("text", "html", {})
    assert p("text") == None

    v = p("text/html; charset=UTF-8")
    assert v == ('text', 'html', {'charset': 'UTF-8'})


def test_safe_subn():
    assert utils.safe_subn("foo", u"bar", "\xc2foo")


def test_urlencode():
    assert utils.urlencode([('foo','bar')])


########NEW FILE########
__FILENAME__ = tservers
import os.path
import threading, Queue
import shutil, tempfile
import flask
from libmproxy.proxy.config import ProxyConfig
from libmproxy.proxy.server import ProxyServer
from libmproxy.proxy.primitives import TransparentUpstreamServerResolver
import libpathod.test, libpathod.pathoc
from libmproxy import flow, controller
from libmproxy.cmdline import APP_HOST, APP_PORT
import tutils

testapp = flask.Flask(__name__)

@testapp.route("/")
def hello():
    return "testapp"

@testapp.route("/error")
def error():
    raise ValueError("An exception...")


def errapp(environ, start_response):
    raise ValueError("errapp")


class TestMaster(flow.FlowMaster):
    def __init__(self, config):
        s = ProxyServer(config, 0)
        state = flow.State()
        flow.FlowMaster.__init__(self, s, state)
        self.apps.add(testapp, "testapp", 80)
        self.apps.add(errapp, "errapp", 80)
        self.clear_log()

    def handle_request(self, m):
        flow.FlowMaster.handle_request(self, m)
        m.reply()

    def handle_response(self, m):
        flow.FlowMaster.handle_response(self, m)
        m.reply()

    def clear_log(self):
        self.log = []

    def handle_log(self, l):
        self.log.append(l.msg)
        l.reply()


class ProxyThread(threading.Thread):
    def __init__(self, tmaster):
        threading.Thread.__init__(self)
        self.tmaster = tmaster
        self.name = "ProxyThread (%s:%s)" % (tmaster.server.address.host, tmaster.server.address.port)
        controller.should_exit = False

    @property
    def port(self):
        return self.tmaster.server.address.port

    @property
    def log(self):
        return self.tmaster.log

    def run(self):
        self.tmaster.run()

    def shutdown(self):
        self.tmaster.shutdown()


class ProxTestBase(object):
    # Test Configuration
    ssl = None
    ssloptions = False
    clientcerts = False
    no_upstream_cert = False
    authenticator = None
    masterclass = TestMaster
    externalapp = False
    certforward = False
    @classmethod
    def setupAll(cls):
        cls.server = libpathod.test.Daemon(ssl=cls.ssl, ssloptions=cls.ssloptions)
        cls.server2 = libpathod.test.Daemon(ssl=cls.ssl, ssloptions=cls.ssloptions)
        pconf = cls.get_proxy_config()
        cls.confdir = os.path.join(tempfile.gettempdir(), "mitmproxy")
        config = ProxyConfig(
            no_upstream_cert = cls.no_upstream_cert,
            confdir = cls.confdir,
            authenticator = cls.authenticator,
            certforward = cls.certforward,
            **pconf
        )
        tmaster = cls.masterclass(config)
        tmaster.start_app(APP_HOST, APP_PORT, cls.externalapp)
        cls.proxy = ProxyThread(tmaster)
        cls.proxy.start()

    @classmethod
    def tearDownAll(cls):
        shutil.rmtree(cls.confdir)

    @property
    def master(cls):
        return cls.proxy.tmaster

    @classmethod
    def teardownAll(cls):
        cls.proxy.shutdown()
        cls.server.shutdown()
        cls.server2.shutdown()

    def setUp(self):
        self.master.clear_log()
        self.master.state.clear()
        self.server.clear_log()
        self.server2.clear_log()

    @property
    def scheme(self):
        return "https" if self.ssl else "http"

    @property
    def proxies(self):
        """
            The URL base for the server instance.
        """
        return (
            (self.scheme, ("127.0.0.1", self.proxy.port))
        )

    @classmethod
    def get_proxy_config(cls):
        d = dict()
        if cls.clientcerts:
            d["clientcerts"] = tutils.test_data.path("data/clientcert")
        return d


class HTTPProxTest(ProxTestBase):
    def pathoc_raw(self):
        return libpathod.pathoc.Pathoc(("127.0.0.1", self.proxy.port))

    def pathoc(self, sni=None):
        """
            Returns a connected Pathoc instance.
        """
        p = libpathod.pathoc.Pathoc(("localhost", self.proxy.port), ssl=self.ssl, sni=sni)
        if self.ssl:
            p.connect(("127.0.0.1", self.server.port))
        else:
            p.connect()
        return p

    def pathod(self, spec, sni=None):
        """
            Constructs a pathod GET request, with the appropriate base and proxy.
        """
        p = self.pathoc(sni=sni)
        spec = spec.encode("string_escape")
        if self.ssl:
            q = "get:'/p/%s'"%spec
        else:
            q = "get:'%s/p/%s'"%(self.server.urlbase, spec)
        return p.request(q)

    def app(self, page):
        if self.ssl:
            p = libpathod.pathoc.Pathoc(("127.0.0.1", self.proxy.port), True)
            p.connect((APP_HOST, APP_PORT))
            return p.request("get:'/%s'"%page)
        else:
            p = self.pathoc()
            return p.request("get:'http://%s/%s'"%(APP_HOST, page))


class TResolver:
    def __init__(self, port):
        self.port = port

    def original_addr(self, sock):
        return ("127.0.0.1", self.port)


class TransparentProxTest(ProxTestBase):
    ssl = None
    resolver = TResolver
    @classmethod
    def get_proxy_config(cls):
        d = ProxTestBase.get_proxy_config()
        if cls.ssl:
            ports = [cls.server.port, cls.server2.port]
        else:
            ports = []
        d["get_upstream_server"] = TransparentUpstreamServerResolver(cls.resolver(cls.server.port), ports)
        d["http_form_in"] = "relative"
        d["http_form_out"] = "relative"
        return d

    def pathod(self, spec, sni=None):
        """
            Constructs a pathod GET request, with the appropriate base and proxy.
        """
        if self.ssl:
            p = self.pathoc(sni=sni)
            q = "get:'/p/%s'"%spec
        else:
            p = self.pathoc()
            q = "get:'/p/%s'"%spec
        return p.request(q)

    def pathoc(self, sni=None):
        """
            Returns a connected Pathoc instance.
        """
        p = libpathod.pathoc.Pathoc(("localhost", self.proxy.port), ssl=self.ssl, sni=sni)
        p.connect()
        return p


class ReverseProxTest(ProxTestBase):
    ssl = None
    @classmethod
    def get_proxy_config(cls):
        d = ProxTestBase.get_proxy_config()
        d["get_upstream_server"] = lambda c: (
            True if cls.ssl else False,
            True if cls.ssl else False,
            "127.0.0.1",
            cls.server.port
        )
        d["http_form_in"] = "relative"
        d["http_form_out"] = "relative"
        return d

    def pathoc(self, sni=None):
        """
            Returns a connected Pathoc instance.
        """
        p = libpathod.pathoc.Pathoc(("localhost", self.proxy.port), ssl=self.ssl, sni=sni)
        p.connect()
        return p

    def pathod(self, spec, sni=None):
        """
            Constructs a pathod GET request, with the appropriate base and proxy.
        """
        if self.ssl:
            p = self.pathoc(sni=sni)
            q = "get:'/p/%s'"%spec
        else:
            p = self.pathoc()
            q = "get:'/p/%s'"%spec
        return p.request(q)


class ChainProxTest(ProxTestBase):
    """
    Chain n instances of mitmproxy in a row - because we can.
    """
    n = 2
    chain_config = [lambda port: ProxyConfig(
        get_upstream_server = lambda c: (False, False, "127.0.0.1", port),
        http_form_in = "absolute",
        http_form_out = "absolute"
    )] * n
    @classmethod
    def setupAll(cls):
        super(ChainProxTest, cls).setupAll()
        cls.chain = []
        for i in range(cls.n):
            config = cls.chain_config[i](cls.proxy.port if i == 0 else cls.chain[-1].port)
            tmaster = cls.masterclass(config)
            tmaster.start_app(APP_HOST, APP_PORT, cls.externalapp)
            cls.chain.append(ProxyThread(tmaster))
            cls.chain[-1].start()

    @classmethod
    def teardownAll(cls):
        super(ChainProxTest, cls).teardownAll()
        for p in cls.chain:
            p.tmaster.server.shutdown()

    def setUp(self):
        super(ChainProxTest, self).setUp()
        for p in self.chain:
            p.tmaster.clear_log()
            p.tmaster.state.clear()


class HTTPChainProxyTest(ChainProxTest):
    def pathoc(self, sni=None):
        """
            Returns a connected Pathoc instance.
        """
        p = libpathod.pathoc.Pathoc(("localhost", self.chain[-1].port), ssl=self.ssl, sni=sni)
        if self.ssl:
            p.connect(("127.0.0.1", self.server.port))
        else:
            p.connect()
        return p

########NEW FILE########
__FILENAME__ = tutils
import os, shutil, tempfile, argparse
from contextlib import contextmanager
from libmproxy import flow, utils, controller
from libmproxy.protocol import http
from libmproxy.proxy.connection import ClientConnection, ServerConnection
import mock_urwid
from libmproxy.console.flowview import FlowView
from libmproxy.console import ConsoleState
from libmproxy.protocol.primitives import Error
from netlib import certutils
from nose.plugins.skip import SkipTest
from mock import Mock
from time import time

def _SkipWindows():
    raise SkipTest("Skipped on Windows.")
def SkipWindows(fn):
    if os.name == "nt":
        return _SkipWindows
    else:
        return fn


def tclient_conn():
    c = ClientConnection._from_state(dict(
        address=dict(address=("address", 22), use_ipv6=True),
        clientcert=None
    ))
    c.reply = controller.DummyReply()
    return c


def tserver_conn():
    c = ServerConnection._from_state(dict(
        address=dict(address=("address", 22), use_ipv6=True),
        source_address=dict(address=("address", 22), use_ipv6=True),
        cert=None
    ))
    c.reply = controller.DummyReply()
    return c


def treq_absolute(conn=None, content="content"):
    r = treq(conn, content)
    r.form_in = r.form_out = "absolute"
    r.host = "address"
    r.port = 22
    r.scheme = "http"
    return r

def treq(conn=None, content="content"):
    if not conn:
        conn = tclient_conn()
    server_conn = tserver_conn()
    headers = flow.ODictCaseless()
    headers["header"] = ["qvalue"]

    f = http.HTTPFlow(conn, server_conn)
    f.request = http.HTTPRequest("relative", "GET", None, None, None, "/path", (1, 1), headers, content,
                                 None, None, None)
    f.request.reply = controller.DummyReply()
    return f.request


def tresp(req=None, content="message"):
    if not req:
        req = treq()
    f = req.flow

    headers = flow.ODictCaseless()
    headers["header_response"] = ["svalue"]
    cert = certutils.SSLCert.from_der(file(test_data.path("data/dercert"), "rb").read())
    f.server_conn = ServerConnection._from_state(dict(
        address=dict(address=("address", 22), use_ipv6=True),
        source_address=None,
        cert=cert.to_pem()))
    f.response = http.HTTPResponse((1, 1), 200, "OK", headers, content, time(), time())
    f.response.reply = controller.DummyReply()
    return f.response


def terr(req=None):
    if not req:
        req = treq()
    f = req.flow
    f.error = Error("error")
    f.error.reply = controller.DummyReply()
    return f.error

def tflow_noreq():
    f = tflow()
    f.request = None
    return f

def tflow(req=None):
    if not req:
        req = treq()
    return req.flow


def tflow_full():
    f = tflow()
    f.response = tresp(f.request)
    return f


def tflow_err():
    f = tflow()
    f.error = terr(f.request)
    return f

def tflowview(request_contents=None):
    m = Mock()
    cs = ConsoleState()
    if request_contents == None:
        flow = tflow()
    else:
        req = treq(None, request_contents)
        flow = tflow(req)

    fv = FlowView(m, cs, flow)
    return fv

def get_body_line(last_displayed_body, line_nb):
    return last_displayed_body.contents()[line_nb + 2]

@contextmanager
def tmpdir(*args, **kwargs):
    orig_workdir = os.getcwd()
    temp_workdir = tempfile.mkdtemp(*args, **kwargs)
    os.chdir(temp_workdir)

    yield temp_workdir

    os.chdir(orig_workdir)
    shutil.rmtree(temp_workdir)


class MockParser(argparse.ArgumentParser):
    """
    argparse.ArgumentParser sys.exits() by default.
    Make it more testable by throwing an exception instead.
    """
    def error(self, message):
        raise Exception(message)


def raises(exc, obj, *args, **kwargs):
    """
        Assert that a callable raises a specified exception.

        :exc An exception class or a string. If a class, assert that an
        exception of this type is raised. If a string, assert that the string
        occurs in the string representation of the exception, based on a
        case-insenstivie match.

        :obj A callable object.

        :args Arguments to be passsed to the callable.

        :kwargs Arguments to be passed to the callable.
    """
    try:
        apply(obj, args, kwargs)
    except Exception, v:
        if isinstance(exc, basestring):
            if exc.lower() in str(v).lower():
                return
            else:
                raise AssertionError(
                    "Expected %s, but caught %s"%(
                        repr(str(exc)), v
                    )
                )
        else:
            if isinstance(v, exc):
                return
            else:
                raise AssertionError(
                    "Expected %s, but caught %s %s"%(
                        exc.__name__, v.__class__.__name__, str(v)
                    )
                )
    raise AssertionError("No exception raised.")

test_data = utils.Data(__name__)

########NEW FILE########
