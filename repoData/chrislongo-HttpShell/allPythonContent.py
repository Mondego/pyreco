__FILENAME__ = ansicolors
# bare bones ANSI color support


class Color(object):
    GREY = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGENTA = 35
    CYAN = 36
    WHITE = 37


class Attribute(object):
    NORMAL = 0
    BRIGHT = 1


def colorize(text, color, attribute=Attribute.NORMAL):
    escape = "\033["
    reset = escape + "0m"

    return "{0}{1};{2}m{3}{4}".format(
        escape,
        attribute,
        color,
        text,
        reset)

########NEW FILE########
__FILENAME__ = formatters
import json
import xml.dom.minidom
from StringIO import StringIO


class Formatter(object):
    def __init__(self, args=None):
        self.args = args

    def format(text):
        pass


class JsonFormatter(Formatter):
    def __init__(self, args=None):
        super(JsonFormatter, self).__init__(args)

    def format(self, text):
        formatted = None

        try:
            o = json.loads(text)
            formatted = json.dumps(o, indent=2)
        except (TypeError, ValueError):
            formatted = text

        return formatted


# under Python <= 2.7.2 the minidom output is gnarly, should be fixed in 2.7.3+
# http://bugs.python.org/issue4147
class XmlFormatter(Formatter):
    def __init__(self, args=None):
        super(XmlFormatter, self).__init__(args)

    # for the time being this big time workaround will do it
    def format_xml(self, node, writer, indent="", addindent="", newl=""):
        # minidom likes to treat whitepace as text nodes
        if node.nodeType == xml.dom.minidom.Node.TEXT_NODE and node.data.strip() == "":
            return

        writer.write(indent + "<" + node.tagName)

        attrs = node.attributes
        keys = sorted(attrs.keys())

        for key in keys:
            writer.write(" %s=\"" % key)
            writer.write(attrs[key].value)
            writer.write("\"")

        if node.childNodes:
            writer.write(">")

            if all(map(lambda n: n.nodeType == xml.dom.minidom.Node.TEXT_NODE,
                       node.childNodes)):
                for child in node.childNodes:
                    child.writexml(writer, "", "", "")
            else:
                writer.write(newl)
                for child in node.childNodes:
                    self.format_xml(child, writer, indent + addindent,
                                    addindent, newl)
                writer.write(indent)
            writer.write("</%s>%s" % (node.tagName, newl))
        else:
            writer.write("/>%s" % (newl))

    def format(self, text):
        formatted = None

        try:
            x = xml.dom.minidom.parseString(text)
            writer = StringIO()
            self.format_xml(x.childNodes[0], writer, addindent="  ", newl="\n")
            formatted = writer.getvalue()
            x.unlink()
        except:
            formatted = text

        return formatted


JSONTYPES = (
    'application/json',
    'application/x-javascript',
    'text/javascript',
    'text/x-javascript',
    'text/x-json')

XMLTYPES = (
    'application/xml',
    'application/atom+xml',
    'application/mathml+xml',
    'application/rss+xml',
    'application/xhtml+xml',
    'text/xml')


def format_by_mimetype(text, mimetype):
    formatter = None

    if mimetype in JSONTYPES:
        formatter = JsonFormatter()
    elif mimetype in XMLTYPES:
        formatter = XmlFormatter()

    if formatter:
        return formatter.format(text)
    else:
        return text

########NEW FILE########
__FILENAME__ = http
import Cookie
import formatters
import httplib2
import json
import oauth2 as oauth
import os
import subprocess
import version


class Http(object):
    def __init__(self, args, logger, verb):
        self.args = args
        self.logger = logger
        self.verb = verb

    def run(self, url, path, pipe=None, headers=None, cookies=None, body=""):
        self.url = url
        host = self.url.netloc

        httpclient = self.init_httpclient()
        httpclient.follow_redirects = False
        httplib2.debuglevel = self.args.debuglevel

        # check for authentication credentials
        if "@" in host:
            split = host.split("@")
            if len(split) > 1:
                host = split[1]
                creds = split[0].split(":")
                httpclient.add_credentials(creds[0], creds[1])
            else:
                host = split[0]

        uri = "{0}://{1}{2}".format(self.url.scheme, host, path)

        if not self.args.disable_cookies:
            self.set_request_cookies(cookies, headers)

        if not "host" in headers:
            headers["host"] = host
        if not "accept-encoding" in headers:
            headers["accept-encoding"] = "gzip, deflate"
        if not "user-agent" in headers:
            headers["user-agent"] = "httpsh/" + version.VERSION

        self.logger.print_text("Connecting to " + uri)

        response, content = httpclient.request(
            uri, method=self.verb, body=body, headers=headers)

        self.handle_response(response, content, headers, cookies, pipe)

    def init_httpclient(self):
        http = None

        keysfile = os.path.join(os.path.expanduser("~"),
                                ".httpshell", self.url.netloc + ".json")

        if os.path.isfile(keysfile):
            try:
                with open(keysfile, "r") as file:
                    keys = json.load(file)
                    token = None

                    consumer = oauth.Consumer(keys["consumer"]["consumer-key"],
                                              keys["consumer"]["consumer-secret"])
                    if "access" in keys:
                        token = oauth.Token(keys["access"]["access-token"],
                                            keys["access"]["access-token-secret"])

                    http = oauth.Client(consumer, token)
                    self.logger.print_text("Using OAuth config in " + keysfile)
            except:
                self.logger.print_error(
                    "Failed reading OAuth data from: " + keysfile)
        else:
            http = httplib2.Http()

        return http

    def set_request_cookies(self, cookies, headers):
        if self.url.netloc in cookies:
            l = []
            cookie = cookies[self.url.netloc]
            #  very basic cookie support atm.  no expiry, etc.
            for morsel in cookie.values():
                l.append(morsel.key + "=" + morsel.coded_value)
            headers["cookie"] = "; ".join(l)

    def handle_response(self, response, content, headers, cookies, pipe=None):
        self.logger.print_response_code(response)
        if self.args.show_headers:
            self.logger.print_headers(headers.items(), True)
            self.logger.print_headers(response.items())

        if not self.args.disable_cookies:
            self.store_response_cookies(response, cookies)

        if self.args.auto_format:
            mimetype = response["content-type"]

            if mimetype:
                content = formatters.format_by_mimetype(
                    content, mimetype.split(";")[0])

        if pipe:
            content = self.pipe_data(pipe, content)

        self.logger.print_data(content)

    def store_response_cookies(self, response, cookies):
        if "set-cookie" in response:
            header = response["set-cookie"]
            cookie = Cookie.SimpleCookie(header)
            cookies[self.url.netloc] = cookie

    # pipes output to external commands like xmllint, tidy for filtering
    def pipe_data(self, command, data):
        result = None

        p = subprocess.Popen(command, shell=True, bufsize=-1,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             stdin=subprocess.PIPE)
        output, error = p.communicate(data)

        if error:
            self.logger.print_text()
            self.logger.print_error(error.decode("utf-8"))
        else:
            result = output.decode("utf-8")

        return result

########NEW FILE########
__FILENAME__ = httpshell
import http
import json
import loggers
import os
import re
import readline
import sys
import Cookie
from urlparse import urlparse
from urllib import urlencode


class HttpShell(object):
    def __init__(self, args):
        self.http_commands = {
            "head": self.head,
            "get": self.get,
            "post": self.post,
            "put": self.put,
            "delete": self.delete,
            "trace": self.trace,
            "options": self.options,
            "cd": self.set_path,
        }

        self.meta_commands = {
            "help": self.help,
            "?": self.help,
            "headers": self.modify_headers,
            "tackons": self.modify_tackons,
            "cookies": self.modify_cookies,
            "open": self.open_host,
            "debuglevel": self.set_debuglevel,
            "quit": self.exit
        }

        # dispatch map is http + meta maps
        self.dispatch = dict(
            self.http_commands.items() + self.meta_commands.items())

        self.url = None
        self.path = None
        self.query = None

        self.args = args
        self.headers = {}
        self.tackons = {}
        self.cookies = {}

        self.args.debuglevel = 0

        # all printing is done via the logger, that way a non-ANSI printer
        # will be a lot easier to add retroactively
        self.logger = loggers.AnsiLogger()

        self.init_readline()

        # setup host and initial path
        self.init_host(self.args.url)

    def init_readline(self):
        httpsh_dir = os.path.join(os.path.expanduser("~"), ".httpshell/")
        if not os.path.isdir(httpsh_dir):
            os.mkdir(httpsh_dir)

        self.history_file = os.path.join(httpsh_dir, ".history")

        try:
            readline.read_history_file(self.history_file)
        except IOError:
            pass

        # sets up tab command completion
        readline.set_completer(self.complete)
        readline.parse_and_bind("tab: complete")

    def init_host(self, url):
        # url parse needs a proceeding "//" for default scheme param to work
        if not "//" in url[:8]:
            url = "//" + url

        self.url = urlparse(url, "http")

        if not self.url.netloc:
            self.logger.print_error("Invalid URL")
            self.exit()

        self.path = self.url.path if self.url.path else "/"
        self.query = self.url.query

    # dispatch methods

    def head(self, path, pipe=None):
        http.Http(self.args, self.logger, "HEAD").run(
            self.url, path, pipe, self.headers, self.cookies)

    def get(self, path, pipe=None):
        http.Http(self.args, self.logger, "GET").run(
            self.url, path, pipe, self.headers, self.cookies)

    def post(self, path, pipe=None):
        body = self.input_body()

        if body:
            http.Http(self.args, self.logger, "POST").run(
                self.url, path, pipe, self.headers, self.cookies, body)

    def put(self, path, pipe=None):
        body = self.input_body()

        if body:
            http.Http(self.args, self.logger, "PUT").run(
                self.url, path, pipe, self.headers, self.cookies, body)

    def delete(self, path, pipe=None):
        http.Http(self.args, self.logger, "DELETE").run(
            self.url, path, pipe, self.headers, self.cookies)

    def trace(self, path, pipe=None):
        http.Http(self.args, self.logger, "TRACE").run(
            self.url, path, pipe, self.headers, self.cookies)

    def options(self, path, pipe=None):
        http.Http(self.args, self.logger, "OPTIONS").run(
            self.url, path, pipe, self.headers, self.cookies)

    def help(self):
        self.logger.print_help()

    # handles .headers meta-command
    def modify_headers(self, header=None):
        if header and len(header) > 0:
            # header will be header:[value]
            a = header.split(":", 1)
            key = a[0]
            if len(a) > 1:
                value = a[1]

                if len(value) > 0:
                    self.headers[key] = value
                elif key in self.headers:
                    del self.headers[key]  # if no value provided, delete
            else:
                self.logger.print_error("Invalid syntax.")
        else:
            # print send headers
            self.logger.print_headers(self.headers.items(), sending=True)

    # handles params meta-command
    def modify_tackons(self, args=None):
        if args and len(args) > 0:
            # args will be param=[value]

            if not "=" in args:  # it's not foo=bar it's just foo
                self.tackons[args] = ""
            else:
                a = args.split("=", 1)
                key = a[0]

                if len(a) > 1:
                    value = a[1]

                if len(value) > 0:
                    self.tackons[key] = value
                elif key in self.tackons:
                    del self.tackons[key]  # if no value provided, delete
        else:
            # print send tackons
            self.logger.print_tackons(self.tackons.items())

    def modify_cookies(self, args=None):
        if args and len(args) > 0:
            # args will be cookie=[value]

            cookie = None

            if not self.url.netloc in self.cookies:
                cookie = Cookie.SimpleCookie()
                self.cookies[self.url.netloc] = cookie
            else:
                cookie = self.cookies[self.url.netloc]

            if args and len(args) > 0:
                # cookie will be cookie=[value]
                a = args.split("=", 1)
                key = a[0]
                if len(a) > 1:
                    value = a[1]

                    if len(value) > 0:
                        cookie[key] = value
                    else:
                        for morsel in cookie.values():
                            if morsel.key == key:
                                del cookie[morsel.key]
                else:
                    self.logger.print_error("Invalid syntax.")
        elif self.url.netloc in self.cookies:
            self.logger.print_cookies(self.cookies[self.url.netloc])

    # changes the current host
    def open_host(self, url=None):
        if url:
            self.init_host(url)

    # handles cd <path> command
    def set_path(self, path):
        path = path.split("?")[0]  # chop off any query params

        if path == "..":
            path = "".join(self.path.rsplit("/", 1)[:1])

        self.path = path if path else "/"

    def set_debuglevel(self, level=None):
        if not level:
            self.logger.print_text(str(self.args.debuglevel))
        else:
            try:
                self.args.debuglevel = int(level)
            except:
                pass

    # converts tackon dict to query params
    def dict_to_query(self, map):
        l = []
        for k, v in sorted(map.items()):
            s = k
            if(v):
                s += "=" + str(v)
            l.append(s)

        return "&".join(l)

    # combine two query strings into one
    def combine_queries(self, a, b):
        s = ""
        if a and len(a) > 0:
            s = a
            if b and len(b) > 0:
                s += "&"
        if b and len(b) > 0:
            s += b

        return s

    # modifies the path for tackon query params
    def mod_path(self, path, query=None):
        q = self.combine_queries(
            query, self.dict_to_query(self.tackons))

        if len(q) > 0:
            return path + "?" + q
        else:
            return path

    # readline complete handler
    def complete(self, text, state):
        match = [s for s in self.dispatch.keys() if s
            and s.startswith(text)] + [None]

        return match[state]

    # read lines of input for POST/PUT
    def input_body(self):
        list = []

        while True:
            line = raw_input("... ")
            if len(line) == 0:
                break
            list.append(line)

        # join list to form string
        params = "".join(list)

        if params[:2] == "@{":  # magic JSON -> urlencode invoke char
            params = self.json_to_urlencode(params[1:])

        return params

    # converts JSON to url encoded for easier posting forms
    def json_to_urlencode(self, json_string):
        params = None

        try:
            o = json.loads(json_string)
            params = urlencode(o)
        except ValueError:
            self.logger.print_error("Malformed JSON.")

        return params

    @property
    def prompt(self):
        host = None

        if "@" in self.url.netloc:  # hide password in prompt
            split = re.split("@|:", self.url.netloc)
            host = split[0] + "@" + split[-1]
        else:
            host = self.url.netloc

        return "{0}:{1}> ".format(host, self.path)

    def input_loop(self):
        command = None

        while True:
            try:
                # a valid command line will be <command> [path] [| filter]
                input = raw_input(self.prompt).split()

                # ignore blank input
                if not input or len(input) == 0:
                    continue

                # command will be element 0 in the array from split
                command = input.pop(0).lower()

                if command in self.dispatch:
                    # push arguments to the stack for command
                    args = self.parse_args(input, command)

                    # invoke command via dispatch table
                    try:
                        self.dispatch[command](*args)
                    except Exception as e:
                        self.logger.print_error("Error: {0}".format(e))
                else:
                    self.logger.print_error("Invalid command.")
            except (EOFError, KeyboardInterrupt):
                break

        print
        self.exit()

    # parses input to set up the call stack for dispatch commands
    def parse_args(self, args, command):
        stack = []

        # ignore meta-commands
        if command not in self.meta_commands:
            path = None
            pipe = None

            if len(args) > 0:
                # element 0 of args array will be the path element
                path = args.pop(0)

                # there's a pipe in my path!
                # user didn't use whitespace between path and pipe character
                # also accounts for if the user did not supply a path
                if "|" in path:
                    s = path.split("|", 1)
                    path = s.pop(0)
                    args.insert(0, "".join(s))

                # pipe, if exists, will be first element in array now
                if len(args) > 0:
                    pipe = " ".join(args).strip()

                    if pipe[0] == "|":
                        pipe = pipe[1:]

                # account for requests from relative dirs
                if path and not path[0] in "/.":
                    path = "{0}{1}{2}".format(
                        self.path,
                        "/" if self.path[-1] != "/" else "",
                        path)

            # push the path on the stack for command method
            # if it's empty the user did not supply one so use self.path
            if path:
                query = None
                a = path.split("?")  # chop query params

                if len(a) > 1:
                    path = a[0]
                    query = a[1]
                stack.append(self.mod_path(path, query))
            else:
                stack.append(self.mod_path(self.path, self.query))

            if pipe:
                stack.append(pipe)
        else:
            if len(args) > 0:
                # meta-commands to their own arg parsing
                stack.append(" ".join(args))

        return stack

    def exit(self, args=None):
        readline.write_history_file(self.history_file)
        sys.exit(0)

########NEW FILE########
__FILENAME__ = loggers
from ansicolors import colorize
from ansicolors import Color
from ansicolors import Attribute
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import guess_lexer


# ANSI color terminal logger
# use color sparingly or the UI looks like a bowl of fruit loops
class AnsiLogger(object):
    def print_text(self, text=None):
        if text:
            print text
        else:
            print

    def print_response_code(self, response):
        colors = [Color.GREY, Color.GREEN, Color.YELLOW, Color.RED, Color.RED]
        print "HTTP/{0} {1} {2}".format(
            response.version / 10.0,
            response.status,
            colorize(response.reason, colors[response.status / 100 - 1],
                     Attribute.BRIGHT))

    def print_headers(self, headers, sending=False):
        for header in headers:
            print "{0}{1}: {2}".format(
                colorize("<" if sending else ">", Color.WHITE),
                colorize(header[0], Color.BLUE, Attribute.BRIGHT),
                header[1])

    def print_tackons(self, params):
        for param in params:
            print "{0}{1}{2}".format(
                colorize(param[0], Color.BLUE, Attribute.BRIGHT),
                "=" if len(param[1]) > 0 else "",
                param[1])

    def print_cookies(self, cookie):
        for morsel in cookie.values():
            print colorize("Name:", Color.BLUE), morsel.key
            print colorize("Value:", Color.BLUE), morsel.value
            print colorize("Expires:", Color.BLUE), morsel["expires"]
            print colorize("Domain:", Color.BLUE), morsel["domain"]
            print colorize("Path:", Color.BLUE), morsel["path"]
            print

    def print_data(self, data):
        if data:
            print
            print highlight(data,
                            guess_lexer(data),
                            TerminalFormatter())

    def print_help(self):
        print "Verbs"
        print "  head", colorize("[</path/to/resource>]", Color.GREY)
        print "  get", colorize("[</path/to/resource>] [| <external command>]", Color.GREY)
        print "  post", colorize("[</path/to/resource>] [| <external command>]", Color.GREY)
        print "  put", colorize("[</path/to/resource>] [| <external command>]", Color.GREY)
        print "  delete", colorize("</path/to/resource>", Color.GREY, Attribute.BRIGHT), colorize(" [| <external command>]", Color.GREY)
        print "  options", colorize("[</path/to/resource>] [| <external command>]", Color.GREY)
        print "  trace", colorize("[</path/to/resource>] [| <external command>]", Color.GREY)
        print "Navigation"
        print "  cd", colorize("</path/to/resource> or ..", Color.GREY, Attribute.BRIGHT)
        print "  open",  colorize("<url>", Color.GREY, Attribute.BRIGHT)
        print "Metacommands"
        print "  headers", colorize("[<name>]:[<value>]", Color.GREY)
        print "  tackons", colorize("[<name>]=[<value>]", Color.GREY)
        print "  cookies", colorize("[<name>]=[<value>]", Color.GREY)
        print "  debuglevel", colorize("[#]", Color.GREY)
        print "  quit"
        print
        print "Full documentation available at https://github.com/chrislongo/HttpShell#readme"

    def print_error(self, text):
        print text

########NEW FILE########
__FILENAME__ = version
VERSION = "0.8.0"

########NEW FILE########
