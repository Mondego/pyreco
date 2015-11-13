__FILENAME__ = webui
#!/usr/bin/env python

"""
A Web UI for RED, the Resource Expert Droid.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""

import cgi
import cPickle as pickle
import gzip
import locale
import os
from robotparser import RobotFileParser
import sys
import tempfile
import time
from urlparse import urlsplit
import zlib

assert sys.version_info[0] == 2 and sys.version_info[1] >= 6, \
    "Please use Python 2.6 or greater"

import thor
from redbot import __version__
from redbot.cache_file import CacheFile
from redbot.resource import HttpResource, RedFetcher, UA_STRING
from redbot.formatter import *
from redbot.formatter import find_formatter, html

### Configuration ##########################################################

# TODO: make language configurable/dynamic
lang = "en"
charset = "utf-8"

# Where to store exceptions; set to None to disable traceback logging
logdir = 'exceptions'

# how many seconds to allow it to run for
max_runtime = 60

# Where to keep files for future reference, when users save them. None
# to disable saving.
save_dir = '/var/state/redbot/'

# how long to store things when users save them, in days.
save_days = 30

# URI root for static assets (absolute or relative, but no trailing '/')
html.static_root = 'static'

# directory containing files to append to the front page; None to disable
html.extra_dir = "extra"

# show errors in the browser; boolean
debug = False  # DEBUG_CONTROL

# domains which we reject requests for when they're in the referer.
referer_spam_domains = ['www.youtube.com']

RedFetcher.robot_cache_dir = "/var/state/robots-txt/" if not debug else False

### End configuration ######################################################


# HTML template for error bodies
error_template = u"""\

<p class="error">
 %s
</p>
"""

try:
    locale.setlocale(locale.LC_ALL, locale.normalize(lang))
except:
    locale.setlocale(locale.LC_ALL, '')


class RedWebUi(object):
    """
    A Web UI for RED.

    Given a URI, run RED on it and present the results to output as HTML.
    If descend is true, spider the links and present a summary.
    """
    def __init__(self, base_uri, method, query_string,
      response_start, response_body, response_done):
        self.base_uri = base_uri
        self.method = method
        self.response_start = response_start
        self.response_body = response_body
        self._response_done = response_done

        self.test_uri = None
        self.req_hdrs = None # tuple of unicode K,V
        self.format = None
        self.test_id = None
        self.check_type = None
        self.descend = None
        self.save = None
        self.parse_qs(method, query_string)

        self.start = time.time()
        self.timeout = thor.schedule(max_runtime, self.timeoutError)
        if self.save and save_dir and self.test_id:
            self.save_test()
        elif self.test_id:
            self.load_saved_test()
        elif self.test_uri:
            self.run_test()
        else:
            self.show_default()

    def response_done(self, trailers):
        if self.timeout:
            self.timeout.delete()
            self.timeout = None
        self._response_done(trailers)

    def output_hdrs(self, *rgs):
        self._output_hdrs(*rgs)
        def remove_timeout():
            self.timeout.delete()
        self.body_done = remove_timeout

    def save_test(self):
        """Save a previously run test_id."""
        try:
            # touch the save file so it isn't deleted.
            os.utime(
                os.path.join(save_dir, self.test_id),
                (
                    thor.time(),
                    thor.time() + (save_days * 24 * 60 * 60)
                )
            )
            location = "?id=%s" % self.test_id
            if self.descend:
                location = "%s&descend=True" % location
            self.response_start(
                "303", "See Other", [
                ("Location", location)
            ])
            self.response_body("Redirecting to the saved test page...")
        except (OSError, IOError):
            self.response_start(
                "500", "Internal Server Error", [
                ("Content-Type", "text/html; charset=%s" % charset),
            ])
            # TODO: better error message (through formatter?)
            self.response_body(
                error_template % "Sorry, I couldn't save that."
            )
        self.response_done([])

    def load_saved_test(self):
        """Load a saved test by test_id."""
        try:
            fd = gzip.open(os.path.join(
                save_dir, os.path.basename(self.test_id)
            ))
            mtime = os.fstat(fd.fileno()).st_mtime
        except (OSError, IOError, TypeError, zlib.error):
            self.response_start(
                "404", "Not Found", [
                ("Content-Type", "text/html; charset=%s" % charset),
                ("Cache-Control", "max-age=600, must-revalidate")
            ])
            # TODO: better error page (through formatter?)
            self.response_body(error_template %
                "I'm sorry, I can't find that saved response."
            )
            self.response_done([])
            return
        is_saved = mtime > thor.time()
        try:
            state = pickle.load(fd)
        except (pickle.PickleError, IOError, EOFError):
            self.response_start(
                "500", "Internal Server Error", [
                ("Content-Type", "text/html; charset=%s" % charset),
                ("Cache-Control", "max-age=600, must-revalidate")
            ])
            # TODO: better error page (through formatter?)
            self.response_body(error_template %
                "I'm sorry, I had a problem reading that response."
            )
            self.response_done([])
            return
        finally:
            fd.close()

        formatter = find_formatter(self.format, 'html', self.descend)(
            self.base_uri, state.request.uri, state.orig_req_hdrs, lang,
            self.output, allow_save=(not is_saved), is_saved=True,
            test_id=self.test_id
        )
        self.response_start(
            "200", "OK", [
            ("Content-Type", "%s; charset=%s" % (
                formatter.media_type, charset)),
            ("Cache-Control", "max-age=3600, must-revalidate")
        ])
        if self.check_type:
        # TODO: catch errors
            state = state.subreqs.get(self.check_type, None)

        formatter.start_output()
        formatter.set_state(state)
        formatter.finish_output()
        self.response_done([])

    def run_test(self):
        """Test a URI."""
        if save_dir and os.path.exists(save_dir):
            try:
                fd, path = tempfile.mkstemp(prefix='', dir=save_dir)
                test_id = os.path.split(path)[1]
            except (OSError, IOError):
                # Don't try to store it.
                test_id = None
        else:
            test_id = None

        formatter = find_formatter(self.format, 'html', self.descend)(
            self.base_uri, self.test_uri, self.req_hdrs, lang,
            self.output, allow_save=test_id, is_saved=False,
            test_id=test_id, descend=self.descend
        )

        referers = []
        for hdr, value in self.req_hdrs:
            if hdr.lower() == 'referer':
                referers.append(value)
        referer_error = None
        if len(referers) > 1:
            referer_error = "Multiple referers not allowed."
        if referers and urlsplit(referers[0]).hostname in referer_spam_domains:
            referer_error = "Referer now allowed."
        if referer_error:
            self.response_start(
                "403", "Forbidden", [
                ("Content-Type", "%s; charset=%s" % (
                    formatter.media_type, charset)),
                ("Cache-Control", "max-age=360, must-revalidate")
            ])
            formatter.start_output()
            self.output(error_template % referer_error)
            self.response_done([])
            return

        if not self.robots_precheck(self.test_uri):
            self.response_start(
                "502", "Gateway Error", [
                ("Content-Type", "%s; charset=%s" % (
                    formatter.media_type, charset)),
                ("Cache-Control", "max-age=60, must-revalidate")
            ])
            formatter.start_output()
            self.output(error_template % "Forbidden by robots.txt.")
            self.response_done([])
            return

        self.response_start(
            "200", "OK", [
            ("Content-Type", "%s; charset=%s" % (
                formatter.media_type, charset)),
            ("Cache-Control", "max-age=60, must-revalidate")
        ])

        ired = HttpResource(
            self.test_uri,
            req_hdrs=self.req_hdrs,
            status_cb=formatter.status,
            body_procs=[formatter.feed],
            descend=self.descend
        )
#        sys.stdout.write(pickle.dumps(ired))
        formatter.start_output()

        def done():
            if self.check_type:
            # TODO: catch errors
                state = ired.subreqs.get(self.check_type, None)
            else:
                state = ired
            formatter.set_state(state)
            formatter.finish_output()
            self.response_done([])
            if test_id:
                try:
                    tmp_file = gzip.open(path, 'w')
                    pickle.dump(ired, tmp_file)
                    tmp_file.close()
                except (IOError, zlib.error, pickle.PickleError):
                    pass # we don't cry if we can't store it.
#            objgraph.show_growth()
        ired.run(done)

    def show_default(self):
        """Show the default page."""
        formatter = html.BaseHtmlFormatter(
            self.base_uri, self.test_uri, self.req_hdrs,
            lang, self.output, is_blank=True
        )
        self.response_start(
            "200", "OK", [
            ("Content-Type", "%s; charset=%s" % (
                formatter.media_type, charset)
            ),
            ("Cache-Control", "max-age=300")
        ])
        formatter.start_output()
        formatter.finish_output()
        self.response_done([])

    def parse_qs(self, method, qs):
        """Given an method and a query-string dict, set attributes."""
        self.test_uri = qs.get('uri', [''])[0].decode(charset, 'replace')
        self.req_hdrs = [tuple(rh.decode(charset, 'replace').split(":", 1))
                            for rh in qs.get("req_hdr", [])
                            if rh.find(":") > 0
                        ]
        self.format = qs.get('format', ['html'])[0]
        self.check_type = qs.get('request', [None])[0]
        self.test_id = qs.get('id', [None])[0]
        self.descend = qs.get('descend', [False])[0]
        if method == "POST":
            self.save = qs.get('save', [False])[0]
        else:
            self.save = False

    def output(self, chunk):
        self.response_body(chunk.encode(charset, 'replace'))

    def timeoutError(self):
        """ Max runtime reached."""
        self.output(error_template % ("RED timeout."))
        self.response_done([])
        
        
    def robots_precheck(self, url):
        """
        If we have the robots.txt file available, check it to see if the
        request is permissible.
        
        This does not fetch robots.txt.
        """
        
        fetcher = RedFetcher(url)
        robots_txt = fetcher.fetch_robots_txt(url, lambda a:a, network=False)
        if robots_txt == "":
            return True
        checker = RobotFileParser()
        checker.parse(robots_txt.splitlines())
        return checker.can_fetch(UA_STRING, url)


# adapted from cgitb.Hook
def except_handler_factory(out=None):
    if not out:
        out = sys.stdout.write

    def except_handler(etype=None, evalue=None, etb=None):
        """
        Log uncaught exceptions and display a friendly error.
        """
        if not etype or not evalue or not etb:
            etype, evalue, etb = sys.exc_info()
        import cgitb
        out(cgitb.reset())
        if logdir is None:
            out(error_template % """
    A problem has occurred, but it probably isn't your fault.
    """)
        else:
            import stat
            import traceback
            try:
                doc = cgitb.html((etype, evalue, etb), 5)
            except:                  # just in case something goes wrong
                doc = ''.join(traceback.format_exception(etype, evalue, etb))
            if debug:
                out(doc)
                return
            try:
                while etb.tb_next != None:
                    etb = etb.tb_next
                e_file = etb.tb_frame.f_code.co_filename
                e_line = etb.tb_frame.f_lineno
                ldir = os.path.join(logdir, os.path.split(e_file)[-1])
                if not os.path.exists(ldir):
                    os.umask(0000)
                    os.makedirs(ldir)
                (fd, path) = tempfile.mkstemp(
                    prefix="%s_" % e_line, suffix='.html', dir=ldir
                )
                fh = os.fdopen(fd, 'w')
                fh.write(doc)
                fh.close()
                os.chmod(path, stat.S_IROTH)
                out(error_template % """\
A problem has occurred, but it probably isn't your fault.
RED has remembered it, and we'll try to fix it soon.""")
            except:
                out(error_template % """\
A problem has occurred, but it probably isn't your fault.
RED tried to save it, but it couldn't! Oops.<br>
Please e-mail the information below to
<a href='mailto:red@redbot.org'>red@redbot.org</a>
and we'll look into it.""")
                out("<h3>Original Error</h3>")
                out("<pre>")
                out(''.join(traceback.format_exception(etype, evalue, etb)))
                out("</pre>")
                out("<h3>Write Error</h3>")
                out("<pre>")
                etype, value, tb = sys.exc_info()
                out(''.join(traceback.format_exception(etype, value, tb)))
                out("</pre>")
        sys.exit(1) # We're in an uncertain state, so we must die horribly.

    return except_handler



def mod_python_handler(r):
    """Run RED as a mod_python handler."""
    from mod_python import apache
    status_lookup = {
     100: apache.HTTP_CONTINUE                     ,
     101: apache.HTTP_SWITCHING_PROTOCOLS          ,
     102: apache.HTTP_PROCESSING                   ,
     200: apache.HTTP_OK                           ,
     201: apache.HTTP_CREATED                      ,
     202: apache.HTTP_ACCEPTED                     ,
     200: apache.HTTP_OK                           ,
     200: apache.HTTP_OK                           ,
     201: apache.HTTP_CREATED                      ,
     202: apache.HTTP_ACCEPTED                     ,
     203: apache.HTTP_NON_AUTHORITATIVE            ,
     204: apache.HTTP_NO_CONTENT                   ,
     205: apache.HTTP_RESET_CONTENT                ,
     206: apache.HTTP_PARTIAL_CONTENT              ,
     207: apache.HTTP_MULTI_STATUS                 ,
     300: apache.HTTP_MULTIPLE_CHOICES             ,
     301: apache.HTTP_MOVED_PERMANENTLY            ,
     302: apache.HTTP_MOVED_TEMPORARILY            ,
     303: apache.HTTP_SEE_OTHER                    ,
     304: apache.HTTP_NOT_MODIFIED                 ,
     305: apache.HTTP_USE_PROXY                    ,
     307: apache.HTTP_TEMPORARY_REDIRECT           ,
     400: apache.HTTP_BAD_REQUEST                  ,
     401: apache.HTTP_UNAUTHORIZED                 ,
     402: apache.HTTP_PAYMENT_REQUIRED             ,
     403: apache.HTTP_FORBIDDEN                    ,
     404: apache.HTTP_NOT_FOUND                    ,
     405: apache.HTTP_METHOD_NOT_ALLOWED           ,
     406: apache.HTTP_NOT_ACCEPTABLE               ,
     407: apache.HTTP_PROXY_AUTHENTICATION_REQUIRED,
     408: apache.HTTP_REQUEST_TIME_OUT             ,
     409: apache.HTTP_CONFLICT                     ,
     410: apache.HTTP_GONE                         ,
     411: apache.HTTP_LENGTH_REQUIRED              ,
     412: apache.HTTP_PRECONDITION_FAILED          ,
     413: apache.HTTP_REQUEST_ENTITY_TOO_LARGE     ,
     414: apache.HTTP_REQUEST_URI_TOO_LARGE        ,
     415: apache.HTTP_UNSUPPORTED_MEDIA_TYPE       ,
     416: apache.HTTP_RANGE_NOT_SATISFIABLE        ,
     417: apache.HTTP_EXPECTATION_FAILED           ,
     422: apache.HTTP_UNPROCESSABLE_ENTITY         ,
     423: apache.HTTP_LOCKED                       ,
     424: apache.HTTP_FAILED_DEPENDENCY            ,
     426: apache.HTTP_UPGRADE_REQUIRED             ,
     500: apache.HTTP_INTERNAL_SERVER_ERROR        ,
     501: apache.HTTP_NOT_IMPLEMENTED              ,
     502: apache.HTTP_BAD_GATEWAY                  ,
     503: apache.HTTP_SERVICE_UNAVAILABLE          ,
     504: apache.HTTP_GATEWAY_TIME_OUT             ,
     505: apache.HTTP_VERSION_NOT_SUPPORTED        ,
     506: apache.HTTP_VARIANT_ALSO_VARIES          ,
     507: apache.HTTP_INSUFFICIENT_STORAGE         ,
     510: apache.HTTP_NOT_EXTENDED                 ,
    }

    r.content_type = "text/html"
    def response_start(code, phrase, hdrs):
        r.status = status_lookup.get(
            int(code),
            apache.HTTP_INTERNAL_SERVER_ERROR
        )
        for hdr in hdrs:
            r.headers_out[hdr[0]] = hdr[1]
    def response_done(trailers):
        thor.schedule(thor.stop)
    query_string = cgi.parse_qs(r.args or "")
    try:
        RedWebUi(r.unparsed_uri, r.method, query_string,
                 response_start, r.write, response_done)
        thor.run()
    except:
        except_handler_factory(r.write)()
    return apache.OK


def cgi_main():
    """Run RED as a CGI Script."""
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
    base_uri = "%s://%s%s%s" % (
      os.environ.has_key('HTTPS') and "https" or "http",
      os.environ.get('HTTP_HOST'),
      os.environ.get('SCRIPT_NAME'),
      os.environ.get('PATH_INFO', '')
    )
    method = os.environ.get('REQUEST_METHOD')
    query_string = cgi.parse_qs(os.environ.get('QUERY_STRING', ""))

    def response_start(code, phrase, res_hdrs):
        sys.stdout.write("Status: %s %s\n" % (code, phrase))
        for k, v in res_hdrs:
            sys.stdout.write("%s: %s\n" % (k, v))
        sys.stdout.write("\n")
        return sys.stdout.write, thor.stop
    def response_done(trailers):
        thor.schedule(0, thor.stop)
    try:
        RedWebUi(base_uri, method, query_string,
                 response_start, sys.stdout.write, response_done)
        thor.run()
    except:
        except_handler_factory(sys.stdout.write)()


def standalone_main(host, port, static_dir):
    """Run RED as a standalone Web server."""

    # load static files
    static_files = {}
    def static_walker(arg, dirname, names):
        for name in names:
            try:
                path = os.path.join(dirname, name)
                if os.path.isdir(path):
                    continue
                uri = os.path.relpath(path, static_dir)
                static_files["/static/%s" % uri] = open(path).read()
            except IOError:
                sys.stderr.write(
                  "* Problem loading %s\n" % path
                )
    os.path.walk(static_dir, static_walker, "")

    def red_handler(x):
        @thor.events.on(x)
        def request_start(method, uri, req_hdrs):
            p_uri = urlsplit(uri)
            if static_files.has_key(p_uri.path):
                x.response_start("200", "OK", []) # TODO: headers
                x.response_body(static_files[p_uri.path])
                x.response_done([])
            elif p_uri.path == "/":
                query_string = cgi.parse_qs(p_uri.query)
                try:
                    RedWebUi('/', method, query_string,
                             x.response_start,
                             x.response_body,
                             x.response_done
                            )
                except RuntimeError:
                    raise
                    sys.stderr.write("""

*** FATAL ERROR
RED has encountered a fatal error which it really, really can't recover from
in standalone server mode. Details follow.

""")
                    except_handler_factory(sys.stderr.write)()
                    sys.stderr.write("\n")
                    thor.stop()
                    sys.exit(1)
            else:
                x.response_start("404", "Not Found", [])
                x.response_done([])

    server = thor.http.HttpServer(host, port)
    server.on('exchange', red_handler)

    try:
        thor.run()
    except KeyboardInterrupt:
        sys.stderr.write("Stopping...\n")
        thor.stop()
    # TODO: logging
    # TODO: extra resources

def standalone_monitor (host, port, static_dir):
    """Fork a process as a standalone Web server and watch it."""
    from multiprocessing import Process
    while True:
        p = Process(target=standalone_main, args=(host, port, static_dir))
        sys.stderr.write("* Starting RED server...\n")
        p.start()
        p.join()
        # TODO: listen to socket and drop privs


if __name__ == "__main__":
    if os.environ.has_key('GATEWAY_INTERFACE'):  # CGI
        cgi_main()
    else:
        # standalone server
        from optparse import OptionParser
        usage = "Usage: %prog [options] port static_dir"
        version = "RED version %s" % __version__
        option_parser = OptionParser(usage=usage, version=version)
        (options, args) = option_parser.parse_args()
        if len(args) < 2:
            option_parser.error(
                "Please specify a port and a static directory."
            )
        try:
            port = int(args[0])
        except ValueError:
            option_parser.error(
                "Port is not an integer."
            )

        static_dir = args[1]
        sys.stderr.write(
            "Starting standalone server on PID %s...\n" % os.getpid() + \
            "http://localhost:%s/\n" % port
        )

#       import pdb
#       pdb.run('standalone_main("", port, static_dir)')
        standalone_main("", port, static_dir)
#       standalone_monitor("", port, static_dir)

########NEW FILE########
__FILENAME__ = cache_file
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2014 Mark Nottingham

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
"""

import gzip
import os
from os import path
import zlib

import thor

class CacheFile(object):
    """
    A gzipped cache file whose unix modification time indicates how long it
    is fresh for. No locking, so errors are discarded.
    """

    def __init__(self, my_path):
        self.path = my_path

    def read(self):
        """
        Read the file, returning its contents. If it does not exist or
        cannot be read, returns None.
        """
        if not path.exists(self.path):
            return None

        try:
            fd = gzip.open(self.path)
        except (OSError, IOError, zlib.error):
            self.delete()
            return None

        try:
            mtime = os.fstat(fd.fileno()).st_mtime
            is_fresh = mtime > thor.time()
            if not is_fresh:
                self.delete()
                return None
            content = fd.read()
        except IOError:
            self.delete()
            return None
        finally:
            fd.close()
        return content


    def write(self, content, lifetime):
        """
        Write content to the file, marking it fresh for lifetime seconds.
        Discard errors silently.
        """
        try:
            fd = gzip.open(self.path, 'w')
            fd.write(content)
        except (OSError, IOError, zlib.error):
            return
        finally:
            fd.close()
        os.utime(self.path, (
                thor.time(),
                thor.time() + lifetime
            )
        )

    def delete(self):
        "Remove the file, discarding errors silently."
        try:
            os.remove(self.path)
        except:
            pass

########NEW FILE########
__FILENAME__ = defns
"""
Header- and Status-specific detail / definitions

Each should be in the form:

  HDR_HEADER_NAME = {'lang': u'message'}
or
  STATUS_NNN = {'lang': u'message'}

where HEADER_NAME is the header's field name in all capitals and with hyphens
replace with underscores, NNN is the three-digit status code, lang' is a
language tag, and 'message' is a description of the header that may
contain HTML.

The following %(var)s style variable interpolations are available:
  field_name - the name of the header

PLEASE NOTE: the description IS NOT ESCAPED, and therefore all variables to be
interpolated into it need to be escaped.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2009-2013 Mark Nottingham

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
"""

HDR_KEEP_ALIVE = {
    'en': u"""The <code>Keep-Alive</code> header is completely optional; it
    is defined primarily because the <code>keep-alive</code> connection token
    implies that such a header exists, not because anyone actually uses it.<p>
    Some implementations (e.g., <a href="http://httpd.apache.org/">Apache</a>)
    do generate a <code>Keep-Alive</code> header to convey how many requests
    they're willing to serve on a single connection, what the connection
    timeout is and other information. However, this isn't usually used by
    clients.<p>
    It's safe to remove this header if you wish to save a few bytes in the
    response."""
}

HDR_NNCOECTION = \
HDR_CNEONCTION = \
HDR_YYYYYYYYYY = \
HDR_XXXXXXXXXX = \
HDR_X_CNECTION = \
HDR__ONNECTION = {
     'en': u"""
     The <code>%(field_name)s</code> field usually means that a HTTP load
     balancer, proxy or other intermediary in front of the server has
     rewritten the <code>Connection</code> header, to allow it to insert its
     own.<p>
     Usually, this is done so that clients won't see <code>Connection:
     close</code> so that the connection can be reused.<p>
     It takes this form because the most efficient way of assuring that
     clients don't see the header is to rearrange or change individual
     characters in its name.
     """
}

HDR_CTEONNT_LENGTH = {
     'en': u"""
     The <code>%(field_name)s</code> field usually means that a HTTP load
     balancer, proxy or other intermediary in front of the server has
     rewritten the <code>Content-Length</code> header, to allow it to insert
     its own.<p> Usually, this is done because an intermediary has dynamically
     compressed the response.<p>
     It takes this form because the most efficient way of assuring that
     clients don't see the header is to rearrange or change individual
     characters in its name.
     """
}


HDR_X_PAD_FOR_NETSCRAPE_BUG = \
HDR_X_PAD = \
HDR_XX_PAD = \
HDR_X_BROWSERALIGNMENT = {
     'en': u"""The <code>%(field_name)s</code> header is used to "pad" the
     response header size.<p>
     Very old versions of the Netscape browser had a
     bug whereby a response whose headers were exactly 256 or 257 bytes long,
     the browser would consider the response (e.g., an image) invalid.<p>
     Since the affected browsers (specifically, Netscape 2.x, 3.x and 4.0 up 
     to beta 2) are no longer widely used, it's probably safe to omit this 
     header.
     """
}

HDR_CONNECTION = {
    'en': u"""The <code>Connection</code> header allows senders to specify
        which headers are hop-by-hop; that is, those that are not forwarded
        by intermediaries. <p>It also indicates options that are
        desired for this particular connection; e.g., <code>close</code> means
        that it should not be reused."""
}

HDR_CONTENT_DISPOSITION = {
    'en': u"""The <code>Content-Disposition</code> header suggests a name
    to use when saving the file.<p>
    When the disposition (the first value) is set to <code>attachment</code>,
    it also prompts browsers to download the file, rather than display it.<p>
    See <a href="http://tools.ietf.org/html/rfc6266">RFC6266</a> for
    details."""
}

HDR_CONTENT_LENGTH = {
    'en': u"""The <code>Content-Length</code> header indicates the size
        of the body, in number of bytes. In responses to the HEAD
        method, it indicates the size of the body that would have been sent
        had the request been a GET.<p>
        If Content-Length is incorrect, persistent connections will not work,
        and caches may not store the response (since they can't be sure if
        they have the whole response)."""
}

HDR_DATE = {
    'en': u"""The <code>Date</code> header represents the time
        when the message was generated, regardless of caching that
        happened since.<p>
        It is used by caches as input to expiration calculations, and to
        detect clock drift."""
}

HDR_HOST = {
    'en': u"""The <code>Host</code> header specifies the host
        and port number (if it's not the default) of the resource
        being requested.<p>
        HTTP/1.1 requires servers to reject requests without a 
        <code>Host</code> header."""
}

HDR_TE = {
    'en': u"""The <code>TE</code> header indicates what
        transfer-codings the client is willing to accept in the
        response, and whether or not it is willing to accept
        trailer fields after the body when the response uses chunked
        transfer-coding.<p>
        The most common transfer-coding, <code>chunked</code>, doesn't need
        to be listed in <code>TE</code>."""
}

HDR_TRAILER = {
    'en': u"""The <code>Trailer</code> header indicates that the given set of
        header fields will be present in the trailer of the message, after the 
        body."""
}

HDR_TRANSFER_ENCODING = {
    'en': u"""The <code>Transfer-Encoding</code> header indicates what
        (if any) type of transformation has been applied to
        the message body.<p>
        This differs from <code>Content-Encoding</code> in that
        transfer-codings are a property of the message, not of the
        representation; i.e., it will be removed by the next "hop", whereas
        content-codings are end-to-end.<p> 
        The most commonly used transfer-coding is <code>chunked</code>, which
        allows persistent connections to be used without knowing the entire
        body's length."""
}

HDR_UPGRADE = {
    'en': u"""The <code>Upgrade</code> header allows the client to
        specify what additional communication protocols it
        supports and would like to use if the server finds
        it appropriate to switch protocols. Servers use it to confirm
        upgrade to a specific protocol."""
}

HDR_VIA = {
    'en': u"""The <code>Via</code> header is added to requests and responses
    by proxies and other HTTP intermediaries.
        It can
        be used to help avoid request loops and identify the protocol
        capabilities of all senders along the request/response chain."""
}

HDR_ALLOW = {
    'en': u"""The <code>Allow</code> header advertises the set of methods
        that are supported by the resource."""
}

HDR_EXPECT = {
    'en': u"""The <code>Expect</code> header is used to indicate that
        particular server behaviors are required by the client.<p>
        Currently, it has one use; the <code>100-continue</code> directive,
        which indicates that the client wants the server to indicate that the
        request is acceptable before the request body is sent.<p>
        If the expectation isn't met, the server will generate a
        <code>417 Expectation Failed</code> response."""
}

HDR_FROM = {
    'en': u"""The <code>From</code> header contains an
        e-mail address for the user.<p>
        It is not commonly used, because servers don't often record or
        otherwise use it."""
}

HDR_LOCATION = {
    'en': u"""The <code>Location</code> header is used in <code>3xx</code>
        responses to redirect the recipient to a different location to
        complete the request.<p>In <code>201 Created</code> responses, it
        identifies a newly created resource.<p>
"""
}

HDR_MAX_FORWARDS = {
    'en': u"""The <code>Max-Forwards</code> header allows
        for the TRACE and OPTIONS methods to limit the
        number of times the message can be forwarded the
        request to the next server (e.g., proxy or gateway).<p>
        This can be useful when the client is attempting to trace a
        request which appears to be looping."""
}

HDR_REFERER = {
    'en': u"""The <code>Referer</code> [sic] header allows the client to
        specify the address of the resource from where the request URI was
        obtained (the "referrer", albeit misspelled)."""
}

HDR_RETRY_AFTER = {
    'en': u"""The <code>Retry-After</code> header can be used with a
        <code>503 Service Unavailable</code> response to indicate how long
        the service is expected to be unavailable to the
        requesting client.<p>
        The value of this field can be either a date or an integer
        number of seconds."""
}

HDR_SERVER = {
    'en': u"""The <code>Server</code> header contains information about
        the software used by the origin server to handle the
        request."""
}

HDR_USER_AGENT = {
    'en': u"""The <code>User-Agent</code> header contains information
        about the user agent originating the request. """
}

HDR_ACCEPT = {
    'en': u"""The <code>Accept</code> header can be used to specify
        the media types which are acceptable for the
        response."""
}

HDR_ACCEPT_CHARSET = {
    'en': u"""The <code>Accept-Charset</code> header can be used to
        indicate what character sets are acceptable for the
        response."""
}

HDR_ACCEPT_ENCODING = {
    'en': u"""The <code>Accept-Encoding</code> header can be used to
        restrict the content-codings that are
        acceptable in the response."""
}

HDR_ACCEPT_LANGUAGE = {
    'en': u"""The <code>Accept-Language</code> header can be used to
        restrict the set of natural languages
        that are preferred as a response to the request."""
}

HDR_CONTENT_ENCODING = {
    'en': u"""The <code>Content-Encoding</code> header's value
        indicates what additional content codings have been
        applied to the body, and thus what decoding
        mechanisms must be applied in order to obtain the
        media-type referenced by the Content-Type header
        field.<p>
        Content-Encoding is primarily used to allow a
        document to be compressed without losing the
        identity of its underlying media type; e.g.,
        <code>gzip</code> and <code>deflate</code>."""
}

HDR_CONTENT_LANGUAGE = {
    'en': u"""The <code>Content-Language</code> header describes the
        natural language(s) of the intended audience.
        Note that this might not convey all of the
        languages used within the body."""
}

HDR_CONTENT_LOCATION = {
    'en': u"""The <code>Content-Location</code> header can used to
        supply an address for the representation when it is accessible from a
        location separate from the request URI."""
}

HDR_CONTENT_MD5 = {
    'en': u"""The <code>Content-MD5</code> header is
        an MD5 digest of the body, and  provides an end-to-end
        message integrity check (MIC).<p>
        Note that while a MIC is good for
        detecting accidental modification of the body
        in transit, it is not proof against malicious
        attacks."""
}

HDR_CONTENT_TYPE = {
    'en': u"""The <code>Content-Type</code> header indicates the media
        type of the body sent to the recipient or, in
        the case of responses to the HEAD method, the media type that
        would have been sent had the request been a GET."""
}

HDR_MIME_VERSION = {
    'en': u"""HTTP is not a MIME-compliant protocol. However, HTTP/1.1
        messages can include a single MIME-Version general-
        header field to indicate what version of the MIME
        protocol was used to construct the message. Use of
        the MIME-Version header field indicates that the
        message is in full compliance with the MIME
        protocol."""
}

HDR_ETAG = {
    'en': u"""The <code>ETag</code> header provides an opaque identifier
    for the representation."""
}

HDR_IF_MATCH = {
    'en': u"""The <code>If-Match</code> header makes a request
        conditional. A client that has one or more
        representations previously obtained from the resource can
        verify that one of them is current by
        including a list of their associated entity tags in
        the If-Match header field.<p>
        This allows
        efficient updates of cached information with a
        minimum amount of transaction overhead. It is also
        used, on updating requests, to prevent inadvertent
        modification of the wrong version of a resource. As
        a special case, the value "*" matches any current
        representation of the resource."""
}

HDR_IF_MODIFIED_SINCE = {
    'en': u"""The <code>If-Modified-Since</code> header is used with a
        method to make it conditional: if the requested
        variant has not been modified since the time
        specified in this field, a representation will not be
        returned from the server; instead, a 304 (Not
        Modified) response will be returned without any
        body."""
}

HDR_IF_NONE_MATCH = {
    'en': u"""The <code>If-None-Match</code> header makes a request
        conditional. A client that has one or
        more representations previously obtained from the resource
        can verify that none of them is current by
        including a list of their associated entity tags in
        the If-None-Match header field.<p>
        This allows efficient updates of cached
        information with a minimum amount of transaction
        overhead. It is also used to prevent a method (e.g.
        PUT) from inadvertently modifying an existing
        resource when the client believes that the resource
        does not exist."""
}

HDR_IF_UNMODIFIED_SINCE = {
    'en': u"""The <code>If-Unmodified-Since</code> header makes a request
        conditional."""
}

HDR_LAST_MODIFIED = {
    'en': u"""The <code>Last-Modified</code> header indicates the time
        that the origin server believes the
        representation was last modified."""
}

HDR_ACCEPT_RANGES = {
    'en': u"""The <code>Accept-Ranges</code> header allows the server to
        indicate that it accepts range requests for a
        resource."""
}

HDR_CONTENT_RANGE = {
    'en': u"""The <code>Content-Range</code> header is sent with a
        partial body to specify where in the full
        body the partial body should be applied."""
}

HDR_AGE = {
    'en': u"""The <code>Age</code> header conveys the sender's estimate
        of the amount of time since the response (or its
        validation) was generated at the origin server."""
}

HDR_CACHE_CONTROL = {
    'en': u"""The <code>Cache-Control</code> header is used to specify
        directives that must be obeyed by all caches along
        the request/response chain. Cache
        directives are unidirectional in that the presence
        of a directive in a request does not imply that the
        same directive is in effect in the response."""
}

HDR_EXPIRES = {
    'en': u"""The <code>Expires</code> header gives a time after
        which the response is considered stale."""
}

HDR_PRAGMA = {
    'en': u"""The <code>Pragma</code> header is used to include
        implementation-specific directives that might apply
        to any recipient along the request/response chain.<p>
        This header is deprecated, in favour of <code>Cache-Control</code>.
"""
}

HDR_VARY = {
    'en': u"""The <code>Vary</code> header indicates the set
        of request headers that determines whether a cache is permitted to
        use the response to reply to a subsequent request
        without validation.<p>
        In uncacheable or stale responses, the Vary field value advises the
        user agent about the criteria that were used to select the
        representation."""
}

HDR_WARNING = {
    'en': u"""The <code>Warning</code> header is used to carry additional
        information about the status or transformation of a
        message that might not be reflected in it.
        This information is typically used to warn about
        possible incorrectness introduced by caching
        operations or transformations applied to the
        body of the message."""
}

HDR_AUTHORIZATION = {
    'en': u"""The <code>Authorization</code> request header
        contains authentication information
        for the user agent to the origin server."""
}

HDR_PROXY_AUTHENTICATE = {
    'en': u"""The <code>Proxy-Authenticate</code> response header
        consists of a challenge
        that indicates the authentication scheme and
        parameters applicable to the proxy for this request-
        target."""
}

HDR_PROXY_AUTHORIZATION = {
    'en': u"""The <code>Proxy-Authorization</code> request header
        contains authentication information for the
        user agent to the proxy and/or realm of the
        resource being requested."""
}

HDR_WWW_AUTHENTICATE = {
    'en': u"""The <code>WWW-Authenticate</code> response header
        consists of at least one challenge that
        indicates the authentication scheme(s) and
        parameters applicable."""
}

HDR_SET_COOKIE = {
    'en': u"""The <code>Set-Cookie</code> response header sets
    a stateful "cookie" on the client, to be included in future
    requests to the server."""
}

HDR_SET_COOKIE2 = {
    'en': u"""The <code>Set-Cookie2</code> header has been 
        deprecated; use <code>Set-Cookie</code> instead."""
}

HDR_X_CACHE = {
    'en': u"""The <code>X-Cache</code> header is used by some caches to
    indicate whether or not the response was served from cache; if it
    contains <code>HIT</code>, it was."""
}

HDR_X_CACHE_LOOKUP = {
    'en': u"""The <code>X-Cache-Lookup</code> header is used by some caches
    to show whether there was a response in cache for this URL; if it
    contains <code>HIT</code>, it was in cache (but not necessarily used).    
    """
}
########NEW FILE########
__FILENAME__ = har
#!/usr/bin/env python

"""
HAR Formatter for REDbot.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""

import datetime
try:
    import json
except ImportError:
    import simplejson as json 

import redbot.speak as rs
from thor.http import get_header
from redbot import __version__
from redbot.formatter import Formatter


class HarFormatter(Formatter):
    """
    Format a RED object (and any descendants) as HAR.
    """
    can_multiple = True
    name = "har"
    media_type = "application/json"
    
    def __init__(self, *args, **kw):
        Formatter.__init__(self, *args, **kw)
        self.har = {
            'log': {
                "version": "1.1",
                "creator": {
                    "name": "REDbot",
                    "version": __version__,
                },
                "browser": {
                    "name": "REDbot",
                    "version": __version__,
                },
                "pages": [],
                "entries": [],
            },
        }
        self.last_id = 0

    def start_output(self):
        pass
        
    def status(self, msg):
        pass

    def feed(self, state, sample):
        pass

    def finish_output(self):
        "Fill in the template with RED's results."
        if self.state.response.complete:
            page_id = self.add_page(self.state)
            self.add_entry(self.state, page_id)
            for linked_state in [d[0] for d in self.state.linked]:
                # filter out incomplete responses
                if linked_state.response.complete:
                    self.add_entry(linked_state, page_id)
        self.output(json.dumps(self.har, indent=4))
        self.done()
        
    def add_entry(self, state, page_ref=None):
        entry = {
            "startedDateTime": isoformat(state.request.start_time),
            "time": int((state.response.complete_time - \
                         state.request.start_time) * 1000),
            "_red_messages": self.format_notes(state)
        }
        if page_ref:
            entry['pageref'] = "page%s" % page_ref
        
        request = {
            'method': state.request.method,
            'url': state.request.uri,
            'httpVersion': "HTTP/1.1",
            'cookies': [],
            'headers': self.format_headers(state.request.headers),
            'queryString': [],
            'headersSize': -1,
            'bodySize': -1,
        }
        
        response = {
            'status': state.response.status_code,
            'statusText': state.response.status_phrase,
            'httpVersion': "HTTP/%s" % state.response.version, 
            'cookies': [],
            'headers': self.format_headers(state.response.headers),
            'content': {
                'size': state.response.decoded_len,
                'compression': state.response.decoded_len - \
                               state.response.payload_len,
                'mimeType': (
                    get_header(state.response.headers, 'content-type') \
                    or [""])[0],
            },
            'redirectURL': (
                    get_header(state.response.headers, 'location') \
                    or [""])[0],
            'headersSize': state.response.header_length,
            'bodySize': state.response.payload_len,
        }
        
        cache = {}
        timings = {
            'dns': -1,
            'connect': -1,
            'blocked': 0,
            'send': 0, 
            'wait': int((state.response.start_time - \
                         state.request.start_time) * 1000),
            'receive': int((state.response.complete_time - \
                            state.response.start_time) * 1000),
        }

        entry.update({
            'request': request,
            'response': response,
            'cache': cache,
            'timings': timings,
        })
        self.har['log']['entries'].append(entry)

        
    def add_page(self, state):
        page_id = self.last_id + 1
        page = {
            "startedDateTime": isoformat(state.request.start_time),
            "id": "page%s" % page_id,
            "title": "",
            "pageTimings": {
                "onContentLoad": -1,
                "onLoad": -1,
            },
        }
        self.har['log']['pages'].append(page)
        return page_id

    def format_headers(self, hdrs):
        return [ {'name': n, 'value': v} for n, v in hdrs ]

    def format_notes(self, state):
        out = []
        for m in state.notes:
            msg = {
                "subject": m.subject,
                "category": m.category,
                "level": m.level,
                "summary": m.show_summary(self.lang)
            }
            smsgs = [i for i in getattr(
                m.subrequest, "notes", []) if i.level in [rs.l.BAD]]
            msg["subrequests"] = \
            [{
                "subject": sm.subject,
                "category": sm.category,
                "level": sm.level,
                "summary": m.show_summary(self.lang)
            } for sm in smsgs]
            out.append(msg)
        return out

def isoformat(timestamp):
    class TZ(datetime.tzinfo):
        def utcoffset(self, dt): 
            return datetime.timedelta(minutes=0)
    return "%sZ" % datetime.datetime.utcfromtimestamp(timestamp).isoformat()
      
########NEW FILE########
__FILENAME__ = html
#!/usr/bin/env python

"""
HTML Formatter for REDbot.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""

import codecs
import json
import operator
import os
import re
import textwrap
import urllib

from cgi import escape as e_html
from functools import partial
from urlparse import urljoin

import thor
import thor.http.error as httperr

import redbot.speak as rs
from redbot import defns, __version__
from redbot.formatter import Formatter, html_header, relative_time, f_num

nl = u"\n"

# Configuration; override to change.
static_root = u'static' # where status resources are located
extra_dir = u'extra' # where extra resources are located

# TODO: make subrequests explorable

class BaseHtmlFormatter(Formatter):
    """
    Base class for HTML formatters."""
    media_type = "text/html"
    
    def __init__(self, *args, **kw):
        Formatter.__init__(self, *args, **kw)
        self.hidden_text = []
        self.start = thor.time()

    def feed(self, state, chunk):
        pass

    def start_output(self):
        if self.kw.get('is_saved', None):
            extra_title = u" <span class='save'>saved results for...</span>"
        else:
            extra_title = u""
        if self.kw.get('is_blank', None):
            extra_body_class = u"blank"
        else:
            extra_body_class = u""
        if self.kw.get('descend', False):
            descend = u"&descend=True"
        else:
            descend = u''
        self.output(html_header.__doc__ % {
            u'static': static_root,
            u'version': __version__,
            u'html_uri': e_html(self.uri),
            u'js_uri': e_js(self.uri),
            u'config': urllib.quote(json.dumps({
              u'redbot_uri': self.uri,
              u'redbot_req_hdrs': self.req_hdrs,
              u'redbot_version': __version__
            }, ensure_ascii=False)),
            u'js_req_hdrs': u", ".join([u'["%s", "%s"]' % (
                e_js(n), e_js(v)) for n,v in self.req_hdrs]),
            u'extra_js': self.format_extra(u'.js'),
            u'test_id': self.kw.get('test_id', u""),
            u'extra_title': extra_title,
            u'extra_body_class': extra_body_class,
            u'descend': descend
        })

    def finish_output(self):
        """
        Default to no input. 
        """
        self.output(self.format_extra())
        self.output(self.format_footer())
        self.output(u"</body></html>\n")
        self.done()

 
    def status(self, message):
        "Update the status bar of the browser"
        self.output(u"""
<script>
<!-- %3.3f
window.status="%s";
-->
</script>
        """ % (thor.time() - self.start, e_html(message)))

    def final_status(self):
#        See issue #51
#        self.status("RED made %(reqs)s requests in %(elapse)2.3f seconds." % {
#            'reqs': fetch.total_requests,
        self.status(u"RED finished in %(elapse)2.3f seconds." % {
           u'elapse': thor.time() - self.start
        })

    def format_extra(self, etype='.html'):
        """
        Show extra content from the extra_dir, if any. MUST be UTF-8.
        Type controls the extension included; currently supported:
          - '.html': shown only on start page, after input block
          - '.js': javascript block (with script tag surrounding)
            included on every page view. 
        """
        o = []
        if extra_dir and os.path.isdir(extra_dir):
            extra_files = [
                p for p in os.listdir(extra_dir) if \
                os.path.splitext(p)[1] == etype
            ]
            for extra_file in extra_files:
                extra_path = os.path.join(extra_dir, extra_file)
                try:
                    o.append(
                        codecs.open(extra_path, mode='r', 
                            encoding='utf-8', errors='replace').read()
                    )
                except IOError, why:
                    o.append("<!-- error opening %s: %s -->" % (
                        extra_file, why))
        return nl.join(o)

    def format_hidden_list(self):
        "return a list of hidden items to be used by the UI"
        return u"<ul>" + u"\n".join([u"<li id='%s'>%s</li>" % (lid, text) for \
            (lid, text) in self.hidden_text]) + u"</ul>"

    def format_footer(self):
        "page footer"
        return u"""\
<br />
<div class="footer">
<p class="version">this is RED %(version)s.</p>
<p class="navigation">
<a href="http://REDbot.org/about/">about</a> |
<script type="text/javascript">
   document.write('<a href="#help" id="help"><strong>help</strong></a> |')
</script>
<a href="http://REDbot.org/project">project</a> |
<span class="help">Drag the bookmarklet to your bookmark bar - it makes
checking easy!</span>
<a href="javascript:location%%20=%%20'%(baseuri)s?uri='+encodeURIComponent(location);%%20void%%200"
title="drag me to your toolbar to use RED any time.">RED</a> bookmarklet
</p>
</div>

""" % {
       'baseuri': self.ui_uri,
       'version': __version__,
       }

    def req_qs(self, link):
        """
        Format a query string referring to the link.
        """
        out = []
        out.append(u"uri=%s" % e_query_arg(urljoin(self.uri, link)))
        if self.req_hdrs:
            for k,v in self.req_hdrs:
                out.append(u"req_hdr=%s%%3A%s" % (
                    e_query_arg(k), 
                    e_query_arg(v)
                ))
        return "&".join(out)
       

class SingleEntryHtmlFormatter(BaseHtmlFormatter):
    """
    Present a single RED response in detail.
    """
    # the order of note categories to display
    note_categories = [
        rs.c.GENERAL, rs.c.SECURITY, rs.c.CONNECTION, rs.c.CONNEG, 
        rs.c.CACHING, rs.c.VALIDATION, rs.c.RANGE
    ]

    # Media types that browsers can view natively
    viewable_types = [
        'text/plain',
        'text/html',
        'application/xhtml+xml',
        'application/pdf',
        'image/gif',
        'image/jpeg',
        'image/jpg',
        'image/png',
        'application/javascript',
        'application/x-javascript',
        'text/javascript',
        'text/x-javascript',
        'text/css',
    ]

    # Validator uris, by media type
    validators = {
        'text/html': "http://validator.w3.org/check?uri=%s",
        'text/css': "http://jigsaw.w3.org/css-validator/validator?uri=%s&",
        'application/xhtml+xml': "http://validator.w3.org/check?uri=%s",
        'application/atom+xml': "http://feedvalidator.org/check.cgi?url=%s",
        'application/rss+xml': "http://feedvalidator.org/check.cgi?url=%s",
    }

    # HTML template for the main response body
    template = u"""\
    <div id="left_column">
    <span class="help">These are the response headers; hover over each one
    for an explanation of what it does.</span>
    <pre id='response'>%(response)s</pre>

    <p class="options">
        <span class='help'>Here, you can see the response body, a HAR document for the request, and when appropriate, validate the response or check its assets (such as referenced images, stylesheets and scripts).</span>
        %(options)s
    </p>
    </div>

    <div id="right_column">
    <div id='details'>
    <span class='help right'>These notes explain what REDbot has found
    about your URL; hover over each one for a detailed explanation.</span>
    %(notes)s
    </div>
    </div>

    <br />
    
    <div id='body'>
    %(body)s
    </div>
    
    %(footer)s

    <div class='hidden' id='hidden_list'>%(hidden_list)s</div>
    </body></html>
    """

    error_template = u"""\

    <p class="error">
     %s
    </p>
    """    
    
    name = "html"

    def __init__(self, *args, **kw):
        BaseHtmlFormatter.__init__(self, *args, **kw)
        self.body_sample = ""  # uncompressed
        self.body_sample_size = 1024 * 128 # how big to allow the sample to be
        self.sample_seen = 0
        self.sample_complete = True

    def feed(self, msg, chunk):
        """
        Store the first self.sample_size bytes of the 
        uncompressed response.
        """
        if self.sample_seen + len(chunk) < self.body_sample_size:
            self.body_sample += chunk
            self.sample_seen += len(chunk)
        elif self.sample_seen < self.body_sample_size:
            max_chunk = self.body_sample_size - self.sample_seen
            self.body_sample += chunk[:max_chunk]
            self.sample_seen += len(chunk)
            self.sample_complete = False
        else:
            self.sample_complete = False
        
    def finish_output(self):
        self.final_status()
        if self.state.response.complete:
            self.header_presenter = HeaderPresenter(self.state.request.uri)
            self.output(self.template % {
                'response': self.format_response(self.state),
                'options': self.format_options(self.state),
                'notes': nl.join([self.format_category(cat, self.state) \
                    for cat in self.note_categories]),
                'body': self.format_body_sample(self.state),
                'footer': self.format_footer(),
                'hidden_list': self.format_hidden_list(),
            })
        else:
            if self.state.response.http_error == None:
                pass # usually a global timeout...
            elif isinstance(self.state.response.http_error, httperr.HttpError):
                if self.state.response.http_error.detail:
                    self.output(self.error_template % u"%s (%s)" % (
                        self.state.response.http_error.desc,
                        unicode(
                          self.state.response.http_error.detail,
                          'utf-8',
                          'replace'
                        )
                    )
                )
                else:
                    self.output(self.error_template % (
                      self.state.response.http_error.desc
                    ))
            else:
                raise AssertionError, \
                  "Unknown incomplete response error %s" % (
                     self.state.response.http_error
                )
        self.done()

    def format_response(self, state):
        "Return the HTTP response line and headers as HTML"
        offset = 0
        headers = []
        for (name, value) in state.response.headers:
            offset += 1
            headers.append(self.format_header(name, value, offset))
            
        return \
        u"    <span class='status'>HTTP/%s %s %s</span>\n" % (
            e_html(state.response.version),
            e_html(state.response.status_code),
            e_html(state.response.status_phrase)
        ) + \
        nl.join(headers)

    def format_header(self, name, value, offset):
        "Return an individual HTML header as HTML"
        token_name = "header-%s" % name.lower()
        py_name = "HDR_" + name.upper().replace("-", "_").encode('ascii', 'ignore')
        if hasattr(defns, py_name) and token_name not in \
          [i[0] for i in self.hidden_text]:
            defn = getattr(defns, py_name)[self.lang] % {
                'field_name': name,
            }
            self.hidden_text.append((token_name, defn))
        return u"""\
    <span data-offset='%s' data-name='%s' class='hdr'>%s:%s</span>""" % (
            offset, 
            e_html(name.lower()), 
            e_html(name), 
            self.header_presenter.Show(name, value)
        )

    def format_body_sample(self, state):
        """show the stored body sample"""
        try:
            uni_sample = unicode(self.body_sample,
                                 state.response.character_encoding, 
                                 'ignore'
            )
        except LookupError:
            uni_sample = unicode(self.body_sample, 'utf-8', 'ignore')
        safe_sample = e_html(uni_sample)
        message = ""
        for tag, link_set in state.links.items():
            for link in link_set:
                def link_to(matchobj):
                    try:
                        qlink = urljoin(state.response.base_uri, link)
                    except ValueError, why:
                        pass # TODO: pass link problem upstream?
                             # e.g., ValueError("Invalid IPv6 URL")
                    return r"%s<a href='%s' class='nocode'>%s</a>%s" % (
                        matchobj.group(1),
                        u"?uri=%s&req_hdr=Referer%%3A%s" % (
                            e_query_arg(qlink),
                            e_query_arg(state.response.base_uri)
                        ),
                        e_html(link),
                        matchobj.group(1)
                    )
                safe_sample = re.sub(r"(['\"])%s\1" % \
                    re.escape(link), link_to, safe_sample)
        if not self.sample_complete:
            message = \
"<p class='btw'>RED isn't showing the whole body, because it's so big!</p>"
        return """<pre class="prettyprint">%s</pre>\n%s""" % (
            safe_sample, message)

    def format_category(self, category, state):
        """
        For a given category, return all of the non-detail 
        notes in it as an HTML list.
        """
        notes = [note for note in state.notes if note.category == category]
        if not notes:
            return nl
        out = []
        if [note for note in notes]:
            out.append(u"<h3>%s</h3>\n<ul>\n" % category)
        for note in notes:
            out.append(
             u"""\
    <li class='%s note' data-subject='%s' data-name='noteid-%s'>
        <span>%s</span>
    </li>"""
            % (
                note.level, 
                e_html(note.subject), 
                id(note), 
                e_html(note.show_summary(self.lang))
             )
            )
            self.hidden_text.append(
                ("noteid-%s" % id(note), note.show_text(self.lang))
            )
            subreq = state.subreqs.get(note.subrequest, None)
            smsgs = [note for note in getattr(subreq, "notes", []) if \
                note.level in [rs.l.BAD]]
            if smsgs:
                out.append(u"<ul>")
                for sm in smsgs:
                    out.append(u"""\
    <li class='%s note' data-subject='%s' name='msgid-%s'>
        <span>%s</span>
    </li>""" % (
                            sm.level, 
                            e_html(sm.subject), 
                            id(sm), 
                            e_html(sm.show_summary(self.lang))
                        )
                    )
                    self.hidden_text.append(
                        (u"msgid-%s" % id(sm), sm.show_text(self.lang))
                    )
                out.append(u"</ul>")
        out.append(u"</ul>\n")
        return nl.join(out)

    def format_options(self, state):
        "Return things that the user can do with the URI as HTML links"
        options = []
        media_type = state.response.parsed_headers.get('content-type', [""])[0]
        options.append(
            (u"response headers: %s bytes" % \
             f_num(state.response.header_length), 
             u"how large the response headers are, including the status line"
            )
        )
        options.append((u"body: %s bytes" % f_num(state.response.payload_len),
            u"how large the response body is"))
        transfer_overhead = state.response.transfer_length - \
            state.response.payload_len
        if transfer_overhead > 0:
            options.append(
                (
                 u"transfer overhead: %s bytes" % f_num(transfer_overhead),
                 u"how much using chunked encoding adds to the response size"
                )
            )
        options.append(None)
        options.append((u"""\
<script type="text/javascript">
   document.write("<a href='#' id='body_view' accesskey='b'>view body</a>")
</script>""", 
    "View this response body (with any gzip compression removed)"
        ))
        if self.kw.get('test_id', None):
            har_locator = u"id=%s" % self.kw['test_id']
        else:
            har_locator = self.req_qs(state.request.uri)
        options.append(
            (u"""\
    <a href='?%s&format=har' accesskey='h'>view har</a>""" % har_locator, 
            "View a HAR (HTTP ARchive, a JSON format) file for this response"
        ))
        if not self.kw.get('is_saved', False):
            if self.kw.get('allow_save', False):
                options.append((
                    u"<a href='#' id='save' accesskey='s'>save</a>", 
                    "Save these results for future reference"
                ))
            if self.validators.has_key(media_type):
                options.append(
                    (
                    u"<a href='%s' accesskey='v'>validate body</a>" %
                        self.validators[media_type] % 
                        e_query_arg(state.request.uri), 
                     ""
                    )
                )
            if hasattr(state, "link_count") and state.link_count > 0:
                options.append((
                    u"<a href='?descend=True&%s' accesskey='a'>" \
                    u"check embedded</a>" % self.req_qs(state.request.uri), 
                    "run RED on images, frames and embedded links"
                ))
        return nl.join(
            [o and u"<span class='option' title='%s'>%s</span>" % (o[1], o[0])
             or u"<br>" for o in options]
        )


class HeaderPresenter(object):
    """
    Present a HTTP header in the Web UI. By default, it will:
       - Escape HTML sequences to avoid XSS attacks
       - Wrap long lines
    However if a method is present that corresponds to the header's
    field-name, that method will be run instead to represent the value.
    """

    def __init__(self, uri):
        self.URI = uri

    def Show(self, name, value):
        """
        Return the given header name/value pair after 
        presentation processing.
        """
        name = name.lower()
        name_token = name.replace('-', '_').encode('ascii', 'ignore')
        if name_token[0] != "_" and hasattr(self, name_token):
            return getattr(self, name_token)(name, value)
        else:
            return self.I(e_html(value), len(name))

    def BARE_URI(self, name, value):
        "Present a bare URI header value"
        value = value.rstrip()
        svalue = value.lstrip()
        space = len(value) - len(svalue)
        return u"%s<a href='?uri=%s&req_hdr=Referer%%3A%s'>%s</a>" % (
            " " * space,
            e_query_arg(urljoin(self.URI, svalue)), 
            e_query_arg(self.URI),
            self.I(e_html(svalue), len(name))
        )
    content_location = \
    location = \
    x_xrds_location = \
    BARE_URI

    @staticmethod
    def I(value, sub_width):
        "wrap a line to fit in the header box"
        hdr_sz = 75
        sw = hdr_sz - min(hdr_sz-1, sub_width)
        tr = textwrap.TextWrapper(
            width=sw, subsequent_indent=" "*8, break_long_words=True
        )
        return tr.fill(value)



class TableHtmlFormatter(BaseHtmlFormatter):
    """
    Present a summary of multiple RED responses.
    """
    # HTML template for the main response body
    template = u"""\
    <table id='summary'>
    %(table)s
    </table>
    <p class="options">
        %(options)s
    </p>

    <div id='details'>
    %(problems)s
    </div>

    <div class='hidden' id='hidden_list'>%(hidden_list)s</div>

    %(footer)s

    </body></html>
    """
    can_multiple = True
    name = "html"

    
    def __init__(self, *args, **kw):
        BaseHtmlFormatter.__init__(self, *args, **kw)
        self.problems = []

    def finish_output(self):
        self.final_status()
        self.output(self.template % {
            'table': self.format_tables(self.state),
            'problems': self.format_problems(),
            'options': self.format_options(self.state),
            'footer': self.format_footer(),
            'hidden_list': self.format_hidden_list(),
        })
        self.done()

    link_order = [
          ('link', u'Head Links'),
          ('script', u'Script Links'),
          ('frame', u'Frame Links'),
          ('iframe', u'IFrame Links'),
          ('img', u'Image Links'),
    ]
    def format_tables(self, state):
        out = [self.format_table_header()]
        out.append(self.format_droid(state))
        for hdr_tag, heading in self.link_order:
            droids = [d[0] for d in state.linked if d[1] == hdr_tag]
            if droids:
                droids.sort(key=operator.attrgetter('response.base_uri'))
                out.append(
                    self.format_table_header(heading + u" (%s)" % len(droids))
                )
                out += [self.format_droid(d) for d in droids]
        return nl.join(out)

    def format_droid(self, state):
        out = [u'<tr class="droid %s">']
        m = 50
        ct = state.response.parsed_headers.get('content-type', [""])
        if ct[0][:6] == 'image/':
            cl = u" class='preview'"
        else:
            cl = u""
        if len(state.request.uri) > m:
            out.append(u"""\
    <td class="uri">
        <a href="%s" title="%s"%s>%s<span class="fade1">%s</span><span class="fade2">%s</span><span class="fade3">%s</span>
        </a>
    </td>""" % (
                    u"?%s" % self.req_qs(state.request.uri), 
                    e_html(state.request.uri), 
                    cl, 
                    e_html(state.request.uri[:m-2]),
                    e_html(state.request.uri[m-2]), 
                    e_html(state.request.uri[m-1]), 
                    e_html(state.request.uri[m]),
                )
            )
        else:
            out.append(
                u'<td class="uri"><a href="%s" title="%s"%s>%s</a></td>' % (
                    u"?%s" % self.req_qs(state.request.uri), 
                    e_html(state.request.uri), 
                    cl, 
                    e_html(state.request.uri)
                )
            )
        if state.response.complete:
            if state.response.status_code in ['301', '302', '303', '307'] and \
              state.response.parsed_headers.has_key('location'):
                out.append(
                    u'<td><a href="?descend=True&%s">%s</a></td>' % (
                        self.req_qs(state.response.parsed_headers['location']),
                        state.response.status_code
                    )
                )
            elif state.response.status_code in ['400', '404', '410']:
                out.append(u'<td class="bad">%s</td>' % (
                    state.response.status_code
                ))
            else:
                out.append(u'<td>%s</td>' % state.response.status_code)
    # pconn
            out.append(self.format_size(state.response.payload_len))
            out.append(self.format_yes_no(state.response.store_shared))
            out.append(self.format_yes_no(state.response.store_private))
            out.append(self.format_time(state.response.age))
            out.append(self.format_time(state.response.freshness_lifetime))
            out.append(self.format_yes_no(state.ims_support))
            out.append(self.format_yes_no(state.inm_support))
            if state.gzip_support:
                out.append(u"<td>%s%%</td>" % state.gzip_savings)
            else:
                out.append(self.format_yes_no(state.gzip_support))
            out.append(self.format_yes_no(state.partial_support))
            problems = [m for m in state.notes if \
                m.level in [rs.l.WARN, rs.l.BAD]]
    # TODO:        problems += sum([m[2].notes for m in state.notes if  
    # m[2] != None], [])
            out.append(u"<td>")
            pr_enum = []
            for problem in problems:
                if problem not in self.problems:
                    self.problems.append(problem)
                pr_enum.append(self.problems.index(problem))
            # add the problem number to the <tr> so we can highlight
            out[0] = out[0] % u" ".join([u"%d" % p for p in pr_enum])
            # append the actual problem numbers to the final <td>
            for p in pr_enum:
                m = self.problems[p]
                out.append(u"<span class='prob_num'>" \
                           u" %s <span class='hidden'>%s</span></span>" % (
                    p + 1, e_html(m.show_summary(self.lang))
                    )
                )
        else:
            if state.response.http_error == None:
                err = u"response incomplete"
            else:
                err = state.response.http_error.desc or u'unknown problem'
            out.append(u'<td colspan="11">%s' % err)
        out.append(u"</td>")
        out.append(u'</tr>')
        return nl.join(out)

    def format_table_header(self, heading=None):
        return u"""
        <tr>
        <th title="The URI tested. Click to run a detailed analysis.">%s</th>
        <th title="The HTTP status code returned.">status</th>
        <th title="The size of the response body, in bytes.">size</th>
        <th title="Whether a shared (e.g., proxy) cache can store the
          response.">shared</th>
        <th title="Whether a private (e.g., browser) cache can store the
          response.">private</th>
        <th title="How long the response had been cached before RED got
          it.">age</th>
        <th title="How long a cache can treat the response as
          fresh.">freshness</th>
        <th title="Whether If-Modified-Since validation is supported, using
          Last-Modified.">IMS</th>
        <th title="Whether If-None-Match validation is supported, using
          ETags.">INM</th>
        <th title="Whether negotiation for gzip compression is supported; if
          so, the percent of the original size saved.">gzip</th>
        <th title="Whether partial responses are supported.">partial</th>
        <th title="Issues encountered.">notes</th>
        </tr>
        """ % (heading or "URI")

    def format_time(self, value):
        if value is None:
            return u'<td>-</td>'
        else:
            return u'<td>%s</td>' % relative_time(value, 0, 0)

    def format_size(self, value):
        if value is None:
            return u'<td>-</td>'
        else:
            return u'<td>%s</td>' % f_num(value, by1024=True)

    def format_yes_no(self, value):
        icon_tpl = u'<td><img src="%s/icon/%%s" alt="%%s"/></td>' % \
            static_root
        if value is True:
            return icon_tpl % (u"accept1.png", u"yes")
        elif value is False:
            return icon_tpl % (u"remove-16.png", u"no")
        elif value is None:
            return icon_tpl % (u"help1.png", u"unknown")
        else:
            raise AssertionError, 'unknown value'

    def format_options(self, state):
        "Return things that the user can do with the URI as HTML links"
        options = []
        media_type = state.response.parsed_headers.get('content-type', [""])[0]
        if self.kw.get('test_id', None):
            har_locator = u"id=%s" % self.kw['test_id']
        else:
            har_locator = u"%s" % self.req_qs(state.request.uri)
        options.append((
          u"<a href='?%s&descend=True&format=har'>view har</a>" % har_locator,
          u"View a HAR (HTTP ARchive) file for this response"
        ))
        if not self.kw.get('is_saved', False):
            if self.kw.get('allow_save', False):
                options.append((
                    u"<a href='#' id='save'>save</a>", 
                    u"Save these results for future reference"
                ))
        return nl.join(
            [o and u"<span class='option' title='%s'>%s</span>" % (o[1], o[0])
             or u"<br>" for o in options]
        )

    def format_problems(self):
        out = [u'<br /><h2>Notes</h2><ol>']
        for m in self.problems:
            out.append(u"""\
    <li class='%s %s note' name='msgid-%s'><span>%s</span></li>""" % (
                    m.level, 
                    e_html(m.subject), 
                    id(m), 
                    e_html(m.summary[self.lang] % m.vars)
                )
            )
            self.hidden_text.append(
                (u"msgid-%s" % id(m), m.text[self.lang] % m.vars)
            )
        out.append(u"</ol>\n")
        return nl.join(out)


# Escaping functions. 
uri_gen_delims = r":/?#[]@"
uri_sub_delims = r"!$&'()*+,;="
def unicode_url_escape(url, safe):
    """
    URL esape a unicode string. Assume that anything already encoded 
    is to be left alone.
    """
    # also include "~" because it doesn't need to be encoded, 
    # but Python does anyway :/
    return urllib.quote(url.encode('utf-8', 'replace'), safe + '%~')
e_url = partial(unicode_url_escape, safe=uri_gen_delims + uri_sub_delims)
e_authority = partial(unicode_url_escape, safe=uri_sub_delims + r"[]:@")
e_path = partial(unicode_url_escape, safe=uri_sub_delims + r":@/")
e_path_seg = partial(unicode_url_escape, safe=uri_sub_delims + r":@") 
e_query = partial(unicode_url_escape, safe=uri_sub_delims + r":@/?")
e_query_arg = partial(unicode_url_escape, safe=r"!$'()*+,:@/?")

def e_js(instr):
    """
    Make sure instr is safe for writing into a double-quoted 
    JavaScript string.
    """
    if not instr: 
        return u""
    instr = instr.replace(u'\\', u'\\\\')
    instr = instr.replace(u'"', ur'\"')
    instr = instr.replace(u'<', ur'\x3c')
    return instr

########NEW FILE########
__FILENAME__ = html_header
u"""\
<!DOCTYPE html>
<html>
<head>
	<title>REDbot: &lt;%(html_uri)s&gt;</title>
	<meta http-equiv="content-type" content="text/html; charset=utf-8" />
	<meta name="ROBOTS" content="INDEX, NOFOLLOW" />
    <link rel="stylesheet" type="text/css" href="%(static)s/style.css">
	<!--[if IE]> 
    <style type="text/css">
        #right_column {
        	width: 650px;
            float: left;
    </style>
    <![endif]-->
    <script src='%(static)s/script.js#%(config)s' type="text/javascript"></script>
    %(extra_js)s
</head>

<body class="%(extra_body_class)s">

<div id="popup"></div>
<form method="POST" id="save_form"
 action="?id=%(test_id)s&save=True%(descend)s">
</form>

<div id="request">
    <h1><a href="?"><span class="hilight"><abbr title="Resource Expert Droid">RED</abbr></span>bot</a>%(extra_title)s</h1>

    <form method="GET" id="request_form">
        <span class="help right">Type in a URI here and press 'return' to
        check it. You can also specify request headers by clicking 'add a
        request header.'</span>
        <input type="url" name="uri" value="%(html_uri)s" 
         id="uri" autocomplete="off"/><br />
        <div id="req_hdrs"></div>
        <script type="text/javascript">
            document.write(
                '<div class="add_req_hdr">' +
                '<a href="#" id="add_req_hdr">add a request header</a>' +
                '</div>'
            )
        </script>
    </form>
</div>
"""
########NEW FILE########
__FILENAME__ = text
#!/usr/bin/env python

"""
HAR Formatter for REDbot.
"""

__author__ = "Jerome Renard <jerome.renard@gmail.com>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""

from HTMLParser import HTMLParser
import operator
import re
import textwrap

import thor.http.error as httperr
import redbot.speak as rs

from redbot.formatter import Formatter

nl = u"\n"

# TODO: errors and status on stderr with CLI?

class BaseTextFormatter(Formatter):
    """
    Base class for text formatters."""
    media_type = "text/plain"

    note_categories = [
        rs.c.GENERAL, rs.c.SECURITY, rs.c.CONNECTION, rs.c.CONNEG,
        rs.c.CACHING, rs.c.VALIDATION, rs.c.RANGE
    ]

    link_order = [
          ('link', 'Head Links'),
          ('script', 'Script Links'),
          ('frame', 'Frame Links'),
          ('iframe', 'IFrame Links'),
          ('img', 'Image Links'),
    ]

    error_template = "Error: %s\n"

    def __init__(self, *args, **kw):
        Formatter.__init__(self, *args, **kw)
        self.verbose = False

    def start_output(self):
        pass

    def feed(self, state, chunk):
        pass

    def status(self, msg):
        pass

    def finish_output(self):
        "Fill in the template with RED's results."
        if self.state.response.complete:
            self.output(self.format_headers(self.state) + nl + nl)
            self.output(self.format_recommendations(self.state) + nl)
        else:
            if self.state.response.http_error == None:
                pass
            elif isinstance(self.state.response.http_error, httperr.HttpError):
                self.output(self.error_template % \
                            self.state.response.http_error.desc)
            else:
                raise AssertionError, "Unknown incomplete response error."

    def format_headers(self, state):
        out = [u"HTTP/%s %s %s" % (
                state.response.version, 
                state.response.status_code, 
                state.response.status_phrase
        )]
        return nl.join(out + [u"%s:%s" % h for h in state.response.headers])

    def format_recommendations(self, state):
        return "".join([self.format_recommendation(state, category) \
            for category in self.note_categories])

    def format_recommendation(self, state, category):
        notes = [note for note in state.notes if note.category == category]
        if not notes:
            return ""
        out = []
        if [note for note in notes]:
            out.append(u"* %s:" % category)
        for m in notes:
            out.append(
                u"  * %s" % (self.colorize(m.level, m.show_summary("en")))
            )
            if self.verbose:
                out.append('')
                out.extend('    ' + line for line in self.format_text(m))
                out.append('')
            smsgs = [note for note in getattr(m.subrequest, "notes", []) 
                     if note.level in [rs.l.BAD]]
            if smsgs:
                out.append("")
                for sm in smsgs:
                    out.append(
                        u"    * %s" %
                        (self.colorize(sm.level, sm.show_summary("en")))
                    )
                    if self.verbose:
                        out.append('')
                        out.extend('     ' + ln for ln in self.format_text(sm))
                        out.append('')
                out.append(nl)
        out.append(nl)
        return nl.join(out)

    def format_text(self, m):
        return textwrap.wrap(
            strip_tags(
                re.sub(
                    r"(?m)\s\s+", 
                    " ", 
                    m.show_text("en")
                )
            )
        )

    def colorize(self, level, string):
        if self.kw.get('tty_out', False):
            # info
            color_start = u"\033[0;32m"
            color_end   = u"\033[0;39m"
            if level == "good":
                color_start = u"\033[1;32m"
                color_end   = u"\033[0;39m"
            if level == "bad":
                color_start = u"\033[1;31m"
                color_end   = u"\033[0;39m"
            if level == "warning":
                color_start = u"\033[1;33m"
                color_end   = u"\033[0;39m"
            if level == "uri":
                color_start = u"\033[1;34m"
                color_end   = u"\033[0;39m"
            return color_start + string + color_end
        else:
            return string



class TextFormatter(BaseTextFormatter):
    """
    Format a RED object as text.
    """
    name = "txt"
    media_type = "text/plain"

    def __init__(self, *args, **kw):
        BaseTextFormatter.__init__(self, *args, **kw)

    def finish_output(self):
        BaseTextFormatter.finish_output(self)
        self.done()


class VerboseTextFormatter(TextFormatter):
    name = 'txt_verbose'

    def __init__(self, *args, **kw):
        TextFormatter.__init__(self, *args, **kw)
        self.verbose = True


class TextListFormatter(BaseTextFormatter):
    """
    Format multiple RED responses as a textual list.
    """
    name = "txt"
    media_type = "text/plain"
    can_multiple = True

    def __init__(self, *args, **kw):
        BaseTextFormatter.__init__(self, *args, **kw)

    def finish_output(self):
        "Fill in the template with RED's results."
        BaseTextFormatter.finish_output(self)
        sep = "=" * 78
        for hdr_tag, heading in self.link_order:
            droids = [d[0] for d in self.state.linked if d[1] == hdr_tag]
            self.output("%s\n%s (%d)\n%s\n" % (
                sep, heading, len(droids), sep
            ))
            if droids:
                droids.sort(key=operator.attrgetter('uri'))
                for droid in droids:
                    self.output(self.format_uri(droid) + nl + nl)
                    self.output(self.format_headers(droid) + nl + nl)
                    self.output(self.format_recommendations(droid) + nl + nl)
        self.done()

    def format_uri(self, state):
        return self.colorize("uri", state.request.uri)


class VerboseTextListFormatter(TextListFormatter):
    name = "txt_verbose"

    def __init__(self, *args, **kw):
        TextListFormatter.__init__(self, *args, **kw)
        self.verbose = True


class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

########NEW FILE########
__FILENAME__ = cache
#!/usr/bin/env python

"""
Cacheability checking function.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""

from redbot.formatter import relative_time, f_num
import headers as rh
import redbot.speak as rs

### configuration
cacheable_methods = ['GET']
heuristic_cacheable_status = ['200', '203', '206', '300', '301', '410']
max_clock_skew = 5  # seconds


def checkCaching(response, request=None):
    "Examine HTTP caching characteristics."
    
    # TODO: check URI for query string, message about HTTP/1.0 if so

    # get header values
    lm = response.parsed_headers.get('last-modified', None)
    date = response.parsed_headers.get('date', None)
    cc_set = response.parsed_headers.get('cache-control', [])
    cc_list = [k for (k, v) in cc_set]
    cc_dict = dict(cc_set)
    cc_keys = cc_dict.keys()
    
    # Last-Modified
    if lm:
        serv_date = date or response.start_time
        if lm > (date or serv_date):
            response.add_note('header-last-modified', rs.LM_FUTURE)
        else:
            response.add_note('header-last-modified', rs.LM_PRESENT,
            last_modified_string=relative_time(lm, serv_date))
    
    # known Cache-Control directives that don't allow duplicates
    known_cc = ["max-age", "no-store", "s-maxage", "public",
                "private", "pre-check", "post-check",
                "stale-while-revalidate", "stale-if-error",
    ]

    # check for mis-capitalised directives /
    # assure there aren't any dup directives with different values
    for cc in cc_keys:
        if cc.lower() in known_cc and cc != cc.lower():
            response.add_note('header-cache-control', rs.CC_MISCAP,
                cc_lower = cc.lower(), cc=cc
            )
        if cc in known_cc and cc_list.count(cc) > 1:
            response.add_note('header-cache-control', rs.CC_DUP,
                cc=cc
            )

    # Who can store this?
    if request and request.method not in cacheable_methods:
        response.store_shared = response.store_private = False
        request.add_note('method', 
            rs.METHOD_UNCACHEABLE,
            method=request.method
        )
        return # bail; nothing else to see here
    elif 'no-store' in cc_keys:
        response.store_shared = response.store_private = False
        response.add_note('header-cache-control', rs.NO_STORE)
        return # bail; nothing else to see here
    elif 'private' in cc_keys:
        response.store_shared = False
        response.store_private = True
        response.add_note('header-cache-control', rs.PRIVATE_CC)
    elif request \
    and 'authorization' in [k.lower() for k, v in request.headers] \
    and not 'public' in cc_keys:
        response.store_shared = False
        response.store_private = True
        response.add_note('header-cache-control', rs.PRIVATE_AUTH)
    else:
        response.store_shared = response.store_private = True
        response.add_note('header-cache-control', rs.STOREABLE)

    # no-cache?
    if 'no-cache' in cc_keys:
        if "last-modified" not in response.parsed_headers.keys() \
           and "etag" not in response.parsed_headers.keys():
            response.add_note('header-cache-control',
                rs.NO_CACHE_NO_VALIDATOR
            )
        else:
            response.add_note('header-cache-control', rs.NO_CACHE)
        return

    # pre-check / post-check
    if 'pre-check' in cc_keys or 'post-check' in cc_keys:
        if 'pre-check' not in cc_keys or 'post-check' not in cc_keys:
            response.add_note('header-cache-control', rs.CHECK_SINGLE)
        else:
            pre_check = post_check = None
            try:
                pre_check = int(cc_dict['pre-check'])
                post_check = int(cc_dict['post-check'])
            except ValueError:
                response.add_note('header-cache-control',
                    rs.CHECK_NOT_INTEGER
                )
            if pre_check is not None and post_check is not None:
                if pre_check == 0 and post_check == 0:
                    response.add_note('header-cache-control',
                        rs.CHECK_ALL_ZERO
                    )
                elif post_check > pre_check:
                    response.add_note('header-cache-control',
                        rs.CHECK_POST_BIGGER
                    )
                    post_check = pre_check
                elif post_check == 0:
                    response.add_note('header-cache-control',
                        rs.CHECK_POST_ZERO
                    )
                else:
                    response.add_note('header-cache-control',
                        rs.CHECK_POST_PRE,
                        pre_check=pre_check,
                        post_check=post_check
                    )

    # vary?
    vary = response.parsed_headers.get('vary', set())
    if "*" in vary:
        response.add_note('header-vary', rs.VARY_ASTERISK)
        return # bail; nothing else to see here
    elif len(vary) > 3:
        response.add_note('header-vary', 
            rs.VARY_COMPLEX, 
            vary_count=f_num(len(vary))
        )
    else:
        if "user-agent" in vary:
            response.add_note('header-vary', rs.VARY_USER_AGENT)
        if "host" in vary:
            response.add_note('header-vary', rs.VARY_HOST)
        # TODO: enumerate the axes in a message

    # calculate age
    age_hdr = response.parsed_headers.get('age', 0)
    date_hdr = response.parsed_headers.get('date', 0)
    if date_hdr > 0:
        apparent_age = max(0,
          int(response.start_time - date_hdr))
    else:
        apparent_age = 0
    current_age = max(apparent_age, age_hdr)
    current_age_str = relative_time(current_age, 0, 0)        
    age_str = relative_time(age_hdr, 0, 0)
    response.age = age_hdr
    if age_hdr >= 1:
        response.add_note('header-age header-date', 
            rs.CURRENT_AGE,
            age=age_str
        )

    # Check for clock skew and dateless origin server.
    skew = date_hdr - response.start_time + age_hdr
    if not date_hdr:
        response.add_note('', rs.DATE_CLOCKLESS)
        if response.parsed_headers.has_key('expires') or \
          response.parsed_headers.has_key('last-modified'):
            response.add_note('header-expires header-last-modified', 
                            rs.DATE_CLOCKLESS_BAD_HDR)
    elif age_hdr > max_clock_skew and current_age - skew < max_clock_skew:
        response.add_note('header-date header-age', rs.AGE_PENALTY)
    elif abs(skew) > max_clock_skew:
        response.add_note('header-date', rs.DATE_INCORRECT,
           clock_skew_string=relative_time(skew, 0, 2)
        )
    else:
        response.add_note('header-date', rs.DATE_CORRECT)

    # calculate freshness
    freshness_lifetime = 0
    has_explicit_freshness = False
    has_cc_freshness = False
    freshness_hdrs = ['header-date']
    if 's-maxage' in cc_keys: # TODO: differentiate message for s-maxage
        freshness_lifetime = cc_dict['s-maxage']
        freshness_hdrs.append('header-cache-control')
        has_explicit_freshness = True
        has_cc_freshness = True
    elif 'max-age' in cc_keys:
        freshness_lifetime = cc_dict['max-age']
        freshness_hdrs.append('header-cache-control')
        has_explicit_freshness = True
        has_cc_freshness = True
    elif response.parsed_headers.has_key('expires'):
        has_explicit_freshness = True
        freshness_hdrs.append('header-expires')
        if response.parsed_headers.has_key('date'):
            freshness_lifetime = response.parsed_headers['expires'] - \
                response.parsed_headers['date']
        else:
            freshness_lifetime = response.parsed_headers['expires'] - \
                response.start_time # ?

    freshness_left = freshness_lifetime - current_age
    freshness_left_str = relative_time(abs(int(freshness_left)), 0, 0)
    freshness_lifetime_str = relative_time(int(freshness_lifetime), 0, 0)

    response.freshness_lifetime = freshness_lifetime
    fresh = freshness_left > 0
    if has_explicit_freshness:
        if fresh:
            response.add_note(" ".join(freshness_hdrs), rs.FRESHNESS_FRESH,
                 freshness_lifetime=freshness_lifetime_str,
                 freshness_left=freshness_left_str,
                 current_age = current_age_str
            )
        elif has_cc_freshness and response.age > freshness_lifetime:
            response.add_note(" ".join(freshness_hdrs),
                rs.FRESHNESS_STALE_CACHE,
                freshness_lifetime=freshness_lifetime_str,
                freshness_left=freshness_left_str,
                current_age = current_age_str
            )
        else:
            response.add_note(" ".join(freshness_hdrs),
                rs.FRESHNESS_STALE_ALREADY,
                freshness_lifetime=freshness_lifetime_str,
                freshness_left=freshness_left_str,
                current_age = current_age_str
            )

    # can heuristic freshness be used?
    elif response.status_code in heuristic_cacheable_status:
        response.add_note('header-last-modified', rs.FRESHNESS_HEURISTIC)
    else:
        response.add_note('', rs.FRESHNESS_NONE)

    # can stale responses be served?
    if 'must-revalidate' in cc_keys:
        if fresh:
            response.add_note('header-cache-control',
                rs.FRESH_MUST_REVALIDATE
        )
        elif has_explicit_freshness:
            response.add_note('header-cache-control',
                rs.STALE_MUST_REVALIDATE
            )
    elif 'proxy-revalidate' in cc_keys or 's-maxage' in cc_keys:
        if fresh:
            response.add_note('header-cache-control',
                rs.FRESH_PROXY_REVALIDATE
            )
        elif has_explicit_freshness:
            response.add_note('header-cache-control',
                rs.STALE_PROXY_REVALIDATE
            )
    else:
        if fresh:
            response.add_note('header-cache-control', rs.FRESH_SERVABLE)
        elif has_explicit_freshness:
            response.add_note('header-cache-control', rs.STALE_SERVABLE)

    # public?
    if 'public' in cc_keys: # TODO: check for authentication in request
        response.add_note('header-cache-control', rs.PUBLIC)

########NEW FILE########
__FILENAME__ = accept_ranges
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
@rh.ResponseHeader
def parse(subject, value, red):
    value = value.lower()
    if value not in ['bytes', 'none']:
        red.add_note(subject, rs.UNKNOWN_RANGE, range=value)
    return value
    
def join(subject, values, red):
    return values


class AcceptRangeTest(rh.HeaderTest):
    name = 'Accept-Ranges'
    inputs = ['bytes']
    expected_out = (['bytes'])
    expected_err = []

class NoneAcceptRangeTest(rh.HeaderTest):
    name = 'Accept-Ranges'
    inputs = ['none']
    expected_out = (['none'])
    expected_err = []

class BothAcceptRangeTest(rh.HeaderTest):
    name = 'Accept-Ranges'
    inputs = ['bytes, none']
    expected_out = (['bytes', 'none'])
    expected_err = []
    
class BadAcceptRangeTest(rh.HeaderTest):
    name = 'Accept-Ranges'
    inputs = ['foo']
    expected_out = (['foo'])
    expected_err = [rs.UNKNOWN_RANGE] 
    
class CaseAcceptRangeTest(rh.HeaderTest):
    name = 'Accept-Ranges'
    inputs = ['Bytes, NONE']
    expected_out = (['bytes', 'none'])
    expected_err = []

########NEW FILE########
__FILENAME__ = age
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
@rh.ResponseHeader
def parse(subject, value, red):
    try:
        age = int(value)
    except ValueError:
        red.add_note(subject, rs.AGE_NOT_INT)
        return None
    if age < 0:
        red.add_note(subject, rs.AGE_NEGATIVE)
        return None
    return age

@rh.SingleFieldValue
def join(subject, values, red):
    return values[-1]
    
    
class AgeTest(rh.HeaderTest):
    name = 'Age'
    inputs = ['10']
    expected_out = 10
    expected_err = []

class MultipleAgeTest(rh.HeaderTest):
    name = 'Age'
    inputs = ['20', '10']
    expected_out = 10
    expected_err = [rs.SINGLE_HEADER_REPEAT]

class CharAgeTest(rh.HeaderTest):
    name = 'Age'
    inputs = ['foo']
    expected_out = None
    expected_err = [rs.AGE_NOT_INT]

class NegAgeTest(rh.HeaderTest):
    name = "Age"
    inputs = ["-20"]
    expected_out = None
    expected_err = [rs.AGE_NEGATIVE]

########NEW FILE########
__FILENAME__ = allow
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
@rh.ResponseHeader
@rh.CheckFieldSyntax(syntax.TOKEN, rh.rfc2616 % "sec-14.7")
def parse(subject, value, red):
    return value
    
def join(subject, values, red):
    return values
########NEW FILE########
__FILENAME__ = cache_control
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
@rh.CheckFieldSyntax(syntax.PARAMETER, rh.rfc2616 % "sec-14.9")
def parse(subject, value, red):
    try:
        directive_name, directive_val = value.split("=", 1)
        directive_val = rh.unquote_string(directive_val)
    except ValueError:
        directive_name = value
        directive_val = None
    directive_name = directive_name.lower()
    # TODO: warn on upper-cased directives?
    if directive_name in ['max-age', 's-maxage']:
        try:
            directive_val = int(directive_val)
        except (ValueError, TypeError):
            red.add_note(subject, rs.BAD_CC_SYNTAX,
                            bad_cc_attr=directive_name
            )
            return None
    return (directive_name, directive_val)

def join(subject, values, red):
    return set(values)

    
class CacheControlTest(rh.HeaderTest):
    name = 'Cache-Control'
    inputs = ['a=b, c=d', 'e=f', 'g']
    expected_out = set([('a', 'b'), ('c', 'd'), ('e', 'f'), ('g', None)])
    expected_err = []

class CacheControlCaseTest(rh.HeaderTest):
    name = 'Cache-Control'
    inputs = ['A=b, c=D']
    expected_out = set([('a', 'b'), ('c', 'D')])
    expected_err = []

class CacheControlQuotedTest(rh.HeaderTest):
    name = 'Cache-Control'
    inputs = ['a="b,c", c=d']
    expected_out = set([('a', 'b,c'), ('c', 'd')])
    expected_err = []

class CacheControlMaxAgeTest(rh.HeaderTest):
    name = 'Cache-Control'
    inputs = ['max-age=5']
    expected_out = set([('max-age', 5)])
    expected_err = []

class CacheControlBadMaxAgeTest(rh.HeaderTest):
    name = 'Cache-Control'
    inputs = ['max-age=foo']
    expected_out = set([])
    expected_err = [rs.BAD_CC_SYNTAX]

########NEW FILE########
__FILENAME__ = content_base
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


def parse(subject, value, red):
    red.add_note(subject, 
                    rs.HEADER_DEPRECATED, 
                    header_name="Content-Base",
                    ref=rh.rfc2616 % "sec-19.6.3"
    )
    return value
    
@rh.SingleFieldValue
def join(subject, values, red):
    return values[-1]
########NEW FILE########
__FILENAME__ = content_disposition
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
@rh.CheckFieldSyntax(
    r'(?:%(TOKEN)s(?:\s*;\s*%(PARAMETER)s)*)' % syntax.__dict__,
    rh.rfc6266
)
def parse(subject, value, red):
    try:
        disposition, params = value.split(";", 1)
    except ValueError:
        disposition, params = value, ''
    disposition = disposition.lower()
    param_dict = rh.parse_params(red, subject, params)
    if disposition not in ['inline', 'attachment']:
        red.add_note(subject,
            rs.DISPOSITION_UNKNOWN,
            disposition=disposition
        )
    if not param_dict.has_key('filename'):
        red.add_note(subject, rs.DISPOSITION_OMITS_FILENAME)
    if "%" in param_dict.get('filename', ''):
        red.add_note(subject, rs.DISPOSITION_FILENAME_PERCENT)
    if "/" in param_dict.get('filename', '') or \
       r"\\" in param_dict.get('filename*', ''):
        red.add_note(subject, rs.DISPOSITION_FILENAME_PATH_CHAR)
    return disposition, param_dict

@rh.SingleFieldValue
def join(subject, values, red):
    return values[-1]
    

class QuotedCDTest(rh.HeaderTest):
    name = 'Content-Disposition'
    inputs = ['attachment; filename="foo.txt"']
    expected_out = ('attachment', {'filename': 'foo.txt'})
    expected_err = [] 
    
class TokenCDTest(rh.HeaderTest):
    name = 'Content-Disposition'
    inputs = ['attachment; filename=foo.txt']
    expected_out = ('attachment', {'filename': 'foo.txt'})
    expected_err = [] 

class InlineCDTest(rh.HeaderTest):
    name = 'Content-Disposition'
    inputs = ['inline; filename=foo.txt']
    expected_out = ('inline', {'filename': 'foo.txt'})
    expected_err = [] 

class RepeatCDTest(rh.HeaderTest):
    name = 'Content-Disposition'
    inputs = ['attachment; filename=foo.txt, inline; filename=bar.txt']
    expected_out = ('inline', {'filename': 'bar.txt'})
    expected_err = [rs.SINGLE_HEADER_REPEAT]

class FilenameStarCDTest(rh.HeaderTest):
    name = 'Content-Disposition'
    inputs = ["attachment; filename=foo.txt; filename*=UTF-8''a%cc%88.txt"]
    expected_out = ('attachment', {
            'filename': 'foo.txt', 
            'filename*': u'a\u0308.txt'})
    expected_err = []

class FilenameStarQuotedCDTest(rh.HeaderTest):    
    name = 'Content-Disposition'
    inputs = ["attachment; filename=foo.txt; filename*=\"UTF-8''a%cc%88.txt\""]
    expected_out = ('attachment', {
            'filename': 'foo.txt', 
            'filename*': u'a\u0308.txt'})
    expected_err = [rs.PARAM_STAR_QUOTED]

class FilenamePercentCDTest(rh.HeaderTest):
    name = 'Content-Disposition'
    inputs = ["attachment; filename=fo%22o.txt"]
    expected_out = ('attachment', {'filename': 'fo%22o.txt', })
    expected_err = [rs.DISPOSITION_FILENAME_PERCENT]
    
class FilenamePathCharCDTest(rh.HeaderTest):
    name = 'Content-Disposition'
    inputs = ['"attachment; filename="/foo.txt"']
    expected_out = ('attachment', {'filename': '/foo.txt',})
    expected_err = [rs.DISPOSITION_FILENAME_PATH_CHAR]


########NEW FILE########
__FILENAME__ = content_encoding
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
@rh.CheckFieldSyntax(syntax.TOKEN, rh.rfc2616 % "sec-14.11")
def parse(subject, value, red):
    # check to see if there are any non-gzip encodings, because
    # that's the only one we ask for.
    if value.lower() != 'gzip':
        red.add_note(subject, 
            rs.ENCODING_UNWANTED, 
            unwanted_codings=value
        )
    return value.lower()
    
def join(subject, values, red):
    return values

    
class ContentEncodingTest(rh.HeaderTest):
    name = 'Content-Encoding'
    inputs = ['gzip']
    expected_out = ['gzip']
    expected_err = []

class ContentEncodingCaseTest(rh.HeaderTest):
    name = 'Content-Encoding'
    inputs = ['GZip']
    expected_out = ['gzip']
    expected_err = []

class UnwantedContentEncodingTest(rh.HeaderTest):
    name = 'Content-Encoding'
    inputs = ['gzip', 'foo']
    expected_out = ['gzip', 'foo']
    expected_err = [rs.ENCODING_UNWANTED]


########NEW FILE########
__FILENAME__ = content_length
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
@rh.CheckFieldSyntax(syntax.DIGITS, rh.rfc2616 % "sec-14.13")
def parse(subject, value, red):
    return int(value)

@rh.SingleFieldValue
def join(subject, values, red):
    return values[-1]

    
class ContentLengthTest(rh.HeaderTest):
    name = 'Content-Length'
    inputs = ['1']
    expected_out = 1
    expected_err = []

class ContentLengthTextTest(rh.HeaderTest):
    name = 'Content-Length'
    inputs = ['a']
    expected_out = None
    expected_err = [rs.BAD_SYNTAX]

class ContentLengthSemiTest(rh.HeaderTest):
    name = 'Content-Length'
    inputs = ['1;']
    expected_out = None
    expected_err = [rs.BAD_SYNTAX]

class ContentLengthSpaceTest(rh.HeaderTest):
    name = 'Content-Length'
    inputs = [' 1 ']
    expected_out = 1
    expected_err = []

class ContentLengthBigTest(rh.HeaderTest):
    name = 'Content-Length'
    inputs = ['9' * 999]
    expected_out = long('9' * 999)
    expected_err = []

########NEW FILE########
__FILENAME__ = content_md5
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


def parse(subject, value, red):
    # TODO: constrain value, tests
    return value
    
@rh.SingleFieldValue
def join(subject, values, red):
    return values[-1]
########NEW FILE########
__FILENAME__ = content_range
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.ResponseHeader
def parse(subject, value, red):
    # #53: check syntax, values?
    if red.status_code not in ["206", "416"]:
        red.add_note(subject, rs.CONTENT_RANGE_MEANINGLESS)
    return value

@rh.SingleFieldValue    
def join(subject, values, red):
    return values
########NEW FILE########
__FILENAME__ = content_transfer_encoding
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


def parse(subject, value, red):
    red.add_note(subject, rs.CONTENT_TRANSFER_ENCODING)
    return value
    
def join(subject, values, red):
    return values
########NEW FILE########
__FILENAME__ = content_type
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
@rh.CheckFieldSyntax(
    r'(?:%(TOKEN)s/%(TOKEN)s(?:\s*;\s*%(PARAMETER)s)*)' % syntax.__dict__,
    rh.rfc2616 % "sec-14.17"
)
def parse(subject, value, red):
    try:
        media_type, params = value.split(";", 1)
    except ValueError:
        media_type, params = value, ''
    media_type = media_type.lower()
    param_dict = rh.parse_params(red, subject, params, ['charset'])
    # TODO: check charset to see if it's known
    return (media_type, param_dict)
    
@rh.SingleFieldValue
def join(subject, values, red):
    return values[-1]
    
class BasicCTTest(rh.HeaderTest):
    name = 'Content-Type'
    inputs = ['text/plain; charset=utf-8']
    expected_out = ("text/plain", {"charset": "utf-8"})
    expected_err = []
########NEW FILE########
__FILENAME__ = date
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


def parse(subject, value, red):
    try:
        date = rh.parse_date(value)
    except ValueError:
        red.add_note(subject, rs.BAD_DATE_SYNTAX)
        return None
    return date
    
@rh.SingleFieldValue
def join(subject, values, red):
    return values[-1]

class BasicDateTest(rh.HeaderTest):
    name = 'Date'
    inputs = ['Mon, 04 Jul 2011 09:08:06 GMT']
    expected_out = 1309770486
    expected_err = []

class BadDateTest(rh.HeaderTest):
    name = 'Date'
    inputs = ['0']
    expected_out = None
    expected_err = [rs.BAD_DATE_SYNTAX]

class BlankDateTest(rh.HeaderTest):
    name = 'Date'
    inputs = ['']
    expected_out = None
    expected_err = [rs.BAD_DATE_SYNTAX]

########NEW FILE########
__FILENAME__ = etag
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
@rh.CheckFieldSyntax(
  r'\*|(?:W/)?%s' % syntax.QUOTED_STRING, rh.rfc2616 % "sec-14.19")
def parse(subject, value, red):
    if value[:2] == 'W/':
        return (True, rh.unquote_string(value[2:]))
    else:
        return (False, rh.unquote_string(value))

@rh.SingleFieldValue
def join(subject, values, red):
    return values[-1]
        
class ETagTest(rh.HeaderTest):
    name = 'ETag'
    inputs = ['"foo"']
    expected_out = (False, 'foo')
    expected_err = []

class WeakETagTest(rh.HeaderTest):
    name = 'ETag'
    inputs = ['W/"foo"']
    expected_out = (True, 'foo')
    expected_err = []

class UnquotedETagTest(rh.HeaderTest):
    name = 'ETag'
    inputs = ['foo']
    expected_out = None
    expected_err = [rs.BAD_SYNTAX]

########NEW FILE########
__FILENAME__ = expires
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


def parse(subject, value, red):
    try:
        date = rh.parse_date(value)
    except ValueError:
        red.add_note(subject, rs.BAD_DATE_SYNTAX)
        return None
    return date
    
@rh.SingleFieldValue
def join(subject, values, red):
    return values[-1]

    
class BasicExpiresTest(rh.HeaderTest):
    name = 'Expires'
    inputs = ['Mon, 04 Jul 2011 09:08:06 GMT']
    expected_out = 1309770486
    expected_err = []

class BadExpiresTest(rh.HeaderTest):
    name = 'Expires'
    inputs = ['0']
    expected_out = None
    expected_err = [rs.BAD_DATE_SYNTAX]

class BlankExpiresTest(rh.HeaderTest):
    name = 'Expires'
    inputs = ['']
    expected_out = None
    expected_err = [rs.BAD_DATE_SYNTAX]
########NEW FILE########
__FILENAME__ = keep_alive
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
def parse(subject, value, red):
    try:
        attr, attr_val = value.split("=", 1)
        attr_val = rh.unquote_string(attr_val)
    except ValueError:
        attr = value
        attr_val = None
    return (attr.lower(), attr_val)
    
def join(subject, values, red):
    return set(values)
########NEW FILE########
__FILENAME__ = last_modified
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


def parse(subject, value, red):
    try:
        date = rh.parse_date(value)
    except ValueError:
        red.add_note(subject, rs.BAD_DATE_SYNTAX)
        return None
    return date

@rh.SingleFieldValue
def join(subject, values, red):
    return values[-1]


class BasicLMTest(rh.HeaderTest):
    name = 'Last-Modified'
    inputs = ['Mon, 04 Jul 2011 09:08:06 GMT']
    expected_out = 1309770486
    expected_err = []

class BadLMTest(rh.HeaderTest):
    name = 'Last-Modified'
    inputs = ['0']
    expected_out = None
    expected_err = [rs.BAD_DATE_SYNTAX]

class BlankLMTest(rh.HeaderTest):
    name = 'Last-Modified'
    inputs = ['']
    expected_out = None
    expected_err = [rs.BAD_DATE_SYNTAX]
########NEW FILE########
__FILENAME__ = link
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""

import re

import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
@rh.CheckFieldSyntax(
    r'(?:<%(URI_reference)s>(?:\s*;\s*%(PARAMETER)s)*)' % syntax.__dict__,
    rh.rfc5988
)
def parse(subject, value, red):
    try:
        link, params = value.split(";", 1)
    except ValueError:
        link, params = value, ''
    link = link[1:-1] # trim the angle brackets
    param_dict = rh.parse_params(red, subject, params, 
      ['rel', 'rev', 'anchor', 'hreflang', 'type', 'media'])
    if param_dict.has_key('rel'): # relation_types
        pass # TODO: check relation type
    if param_dict.has_key('rev'):
        red.add_note(subject, rs.LINK_REV,
                        link=link, rev=param_dict['rev'])
    if param_dict.has_key('anchor'): # URI-Reference
        if not re.match(r"^\s*%s\s*$" % syntax.URI_reference, 
                        param_dict['anchor'], re.VERBOSE):
            red.add_note(subject, rs.LINK_BAD_ANCHOR,
                            link=link,
                            anchor=param_dict['anchor'])
    # TODO: check media-type in 'type'
    # TODO: check language tag in 'hreflang'            
    return link, param_dict
    
def join(subject, values, red):
    return values

    
class BasicLinkTest(rh.HeaderTest):
    name = 'Link'
    inputs = ['<http://www.example.com/>; rel=example']
    expected_out = [('http://www.example.com/', {'rel': 'example'})]
    expected_err = []

class QuotedLinkTest(rh.HeaderTest):
    name = 'Link'
    inputs = ['"http://www.example.com/"; rel=example']
    expected_out = []
    expected_err = [rs.BAD_SYNTAX]

class QuotedRelationLinkTest(rh.HeaderTest):
    name = 'Link'
    inputs = ['<http://www.example.com/>; rel="example"']
    expected_out = [('http://www.example.com/', {'rel': 'example'})]
    expected_err = []    

class RelativeLinkTest(rh.HeaderTest):
    name = 'Link'
    inputs = ['</foo>; rel="example"']
    expected_out = [('/foo', {'rel': 'example'})]
    expected_err = []    
    
class RepeatingRelationLinkTest(rh.HeaderTest):
    name = 'Link'
    inputs = ['</foo>; rel="example"; rel="another"']
    expected_out = [('/foo', {'rel': 'another'})]
    expected_err = [rs.PARAM_REPEATS]

class RevLinkTest(rh.HeaderTest):
    name = 'Link'
    inputs = ['</foo>; rev="bar"']
    expected_out = [('/foo', {'rev': 'bar'})]
    expected_err = [rs.LINK_REV]

class BadAnchorLinkTest(rh.HeaderTest):
    name = 'Link'
    inputs = ['</foo>; rel="bar"; anchor="{blah}"']
    expected_out = [('/foo', {'rel': 'bar', 'anchor': '{blah}'})]
    expected_err = [rs.LINK_BAD_ANCHOR]

########NEW FILE########
__FILENAME__ = location
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""

import re
from urlparse import urljoin

import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


# The most common problem with Location is a non-absolute URI, 
# so we separate that from the syntax check.
@rh.CheckFieldSyntax(syntax.URI_reference, rh.rfc2616 % "sec-14.30")
@rh.ResponseHeader
def parse(subject, value, msg):
    if msg.status_code not in [
        "201", "300", "301", "302", "303", "305", "307"
    ]:
        msg.add_note(subject, rs.LOCATION_UNDEFINED)
    if not re.match(r"^\s*%s\s*$" % syntax.URI, value, re.VERBOSE):
        msg.add_note(subject, rs.LOCATION_NOT_ABSOLUTE,
                        full_uri=urljoin(msg.base_uri, value))
    return value

@rh.SingleFieldValue
def join(subject, values, msg):
    return values[-1]
########NEW FILE########
__FILENAME__ = mime_version
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


def parse(subject, value, red):
    red.add_note(subject, rs.MIME_VERSION)
    return value
    
def join(subject, values, red):
    return values
########NEW FILE########
__FILENAME__ = p3p
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
def parse(subject, value, red):
    # See #55
    pass

def join(subject, values, red):
    return values
########NEW FILE########
__FILENAME__ = pragma
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax

@rh.GenericHeaderSyntax
def parse(subject, value, red):
    return value.lower()
    
def join(subject, values, red):
    if "no-cache" in values:
        red.add_note(subject, rs.PRAGMA_NO_CACHE)
    others = [True for v in values if v != "no-cache"]
    if others:
        red.add_note(subject, rs.PRAGMA_OTHER)
    return set(values)
########NEW FILE########
__FILENAME__ = retry_after
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
@rh.CheckFieldSyntax(
  r"(?:%s|%s)" % (syntax.DIGITS, syntax.DATE), rh.rfc2616 % "sec-14.37")
def parse(subject, value, red):
    pass
    
@rh.SingleFieldValue
def join(subject, values, red):
    return values
########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax

@rh.ResponseHeader
def parse(subject, value, red):
    # TODO: check syntax, flag servers?
    pass
    
def join(subject, values, red):
    return values
########NEW FILE########
__FILENAME__ = set_cookie
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""

from calendar import timegm
from re import match, split
from urlparse import urlsplit

import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax

@rh.ResponseHeader
def parse(subject, value, red):
    path = urlsplit(red.base_uri).path # pylint: disable=E1103
    try:
        set_cookie = loose_parse(value, path, red.start_time, subject, red)
    except ValueError:
        set_cookie = None
    return set_cookie

def join(subject, values, red):
    return values


# TODO: properly escape note
def loose_parse(set_cookie_string, uri_path, current_time, subject, red):
    """
    Parse a Set-Cookie string, as per RFC6265, Section 5.2.
    """
    name = "Set-Cookie"
    if ';' in set_cookie_string:
        name_value_pair, unparsed_attributes = set_cookie_string.split(";", 1)
    else:
        name_value_pair, unparsed_attributes = set_cookie_string, ""
    try:
        name, value = name_value_pair.split("=", 1)
    except ValueError:
        red.add_note(subject, rs.SET_COOKIE_NO_VAL,
            name_value_pair.strip()
        )
        raise ValueError, "Cookie doesn't have a value"
    name, value = name.strip(), value.strip()
    if name == "":
        red.add_note(subject, rs.SET_COOKIE_NO_NAME)
        raise ValueError, "Cookie doesn't have a name"
    cookie_name, cookie_value = name, value
    cookie_attribute_list = []
    while unparsed_attributes != "":
        if ";" in unparsed_attributes:
            cookie_av, unparsed_attributes = unparsed_attributes.split(";", 1)
        else:
            cookie_av, unparsed_attributes = unparsed_attributes, ""
        if "=" in cookie_av:
            attribute_name, attribute_value = cookie_av.split("=", 1)
        else:
            attribute_name, attribute_value = cookie_av, ""
        attribute_name = attribute_name.strip()
        attribute_value = attribute_value.strip()
        case_norm_attribute_name = attribute_name.lower()
        if case_norm_attribute_name == "expires":
            try:
                expiry_time = loose_date_parse(attribute_value)
            except ValueError, why:
                red.add_note(subject, rs.SET_COOKIE_BAD_DATE, why=why,
                    cookie_name=cookie_name
                )
                continue
            cookie_attribute_list.append(("Expires", expiry_time))
        elif case_norm_attribute_name == "max-age":
            if attribute_value == "":
                red.add_note(subject, rs.SET_COOKIE_EMPTY_MAX_AGE,
                    cookie_name=cookie_name
                )
                continue
            if attribute_value[0] == "0":
                red.add_note(subject, rs.SET_COOKIE_LEADING_ZERO_MAX_AGE,
                    cookie_name=cookie_name
                )
                continue
            if not attribute_value.isdigit():
                red.add_note(subject, rs.SET_COOKIE_NON_DIGIT_MAX_AGE,
                    cookie_name=cookie_name
                )
                continue
            delta_seconds = int(attribute_value)
            cookie_attribute_list.append(("Max-Age", delta_seconds))
        elif case_norm_attribute_name == "domain":
            if attribute_value == "":
                red.add_note(subject, rs.SET_COOKIE_EMPTY_DOMAIN,
                    cookie_name=cookie_name
                )
                continue
            elif attribute_value[0] == ".":
                cookie_domain = attribute_value[1:]
            else:
                cookie_domain = attribute_value
            cookie_attribute_list.append(("Domain", cookie_domain))
        elif case_norm_attribute_name == "path":
            if attribute_value == "" or attribute_value[0] != "/":
                # use default path
                if uri_path == "" or uri_path[0] != "/":
                    cookie_path = "/"
                if uri_path.count("/") < 2:
                    cookie_path = "/"
                else:
                    cookie_path = uri_path[:uri_path.rindex("/")]
            else:
                cookie_path = attribute_value
            cookie_attribute_list.append(("Path", cookie_path))
        elif case_norm_attribute_name == "secure":
            cookie_attribute_list.append(("Secure", ""))
        elif case_norm_attribute_name == "httponly":
            cookie_attribute_list.append(("HttpOnly", ""))
        else:
            red.add_note(subject, rs.SET_COOKIE_UNKNOWN_ATTRIBUTE,
                cookie_name=cookie_name,
                attribute=attribute_name
            )
    return (cookie_name, cookie_value, cookie_attribute_list)


DELIMITER = r'(?:[\x09\x20-\x2F\x3B-\x40\x5B-\x60\x7B-\x7E])'
NON_DELIMTER = r'(?:[\x00-\x08\x0A-\x1F0-0\:a-zA-Z\x7F-\xFF])'
MONTHS = {
    'jan': 1,
    'feb': 2,
    'mar': 3,
    'apr': 4,
    'may': 5,
    'jun': 6,
    'jul': 7,
    'aug': 8,
    'sep': 9,
    'oct': 10,
    'nov': 11,
    'dec': 12
}
def loose_date_parse(cookie_date):
    """
    Parse a date, as per RFC 6265, Section 5.1.1.
    """
    found_time = found_day_of_month = found_month = found_year = False
    hour_value = minute_value = second_value = None
    day_of_month_value = month_value = year_value = None
    date_tokens = split(DELIMITER, cookie_date)
    for date_token in date_tokens:
        re_match = None
        if not found_time:
            re_match = match(r'^(\d{2}:\d{2}:\d{2})(?:\D)?', date_token)
            if re_match:
                found_time = True
                hour_value, minute_value, second_value = [
                    int(v) for v in re_match.group(1).split(":")
                ]
                continue
        if not found_day_of_month:
            re_match = match(r'^(\d\d?)(?:\D)?', date_token)
            if re_match:
                found_day_of_month = True
                day_of_month_value = int(re_match.group(1))
                continue
        # TODO: shorter than three chars
        if not found_month and date_token[:3].lower() in MONTHS.keys():
            found_month = True
            month_value = MONTHS[date_token[:3].lower()]
            continue
        if not found_year:
            re_match = match(r'^(\d{2,4})(?:\D)?', date_token)
            if re_match:
                found_year = True
                year_value = int(re_match.group(1))
                continue
    if 99 >= year_value >= 70:
        year_value += 1900
    if 69 >= year_value >= 0:
        year_value += 2000
    if False in [found_time, found_day_of_month, found_month, found_year]:
        missing = []
        if not found_time: missing.append("time")
        if not found_day_of_month: missing.append("day")
        if not found_month: missing.append("month")
        if not found_year: missing.append("year")
        raise ValueError, "didn't have a: %s" % ",".join(missing)
    if day_of_month_value < 1 or day_of_month_value > 31:
        raise ValueError, "%s is out of range for day_of_month" % \
            day_of_month_value
    if year_value < 1601:
        raise ValueError, "%s is out of range for year" % year_value
    if hour_value > 23:
        raise ValueError, "%s is out of range for hour" % hour_value
    if minute_value > 59:
        raise ValueError, "%s is out of range for minute" % minute_value
    if second_value > 59:
        raise ValueError, "%s is out of range for second" % second_value
    parsed_cookie_date = timegm((
        year_value,
        month_value,
        day_of_month_value,
        hour_value,
        minute_value,
        second_value
    ))
    return parsed_cookie_date


class BasicSCTest(rh.HeaderTest):
    name = 'Set-Cookie'
    inputs = ['SID=31d4d96e407aad42']
    expected_out = [("SID", "31d4d96e407aad42", [])]
    expected_err = []

class ParameterSCTest(rh.HeaderTest):
    name = 'Set-Cookie'
    inputs = ['SID=31d4d96e407aad42; Path=/; Domain=example.com']
    expected_out = [("SID", "31d4d96e407aad42",
        [("Path", "/"), ("Domain", "example.com")])]
    expected_err = []

class TwoSCTest(rh.HeaderTest):
    name = 'Set-Cookie'
    inputs = [
        "SID=31d4d96e407aad42; Path=/; Secure; HttpOnly",
        "lang=en-US; Path=/; Domain=example.com"
    ]
    expected_out = [
        ("SID", "31d4d96e407aad42", [("Path", "/"), ("Secure", ""), ("HttpOnly", "")]),
        ("lang", "en-US", [("Path", "/"), ("Domain", "example.com")])
    ]
    expected_err = []

class ExpiresScTest(rh.HeaderTest):
    name = "Set-Cookie"
    inputs = ["lang=en-US; Expires=Wed, 09 Jun 2021 10:18:14 GMT"]
    expected_out = [("lang", "en-US", [("Expires", 1623233894)])]
    expected_err = []

class ExpiresSingleScTest(rh.HeaderTest):
    name = "Set-Cookie"
    inputs = ["lang=en-US; Expires=Wed, 9 Jun 2021 10:18:14 GMT"]
    expected_out = [("lang", "en-US", [("Expires", 1623233894)])]
    expected_err = []

class MaxAgeScTest(rh.HeaderTest):
    name = "Set-Cookie"
    inputs = ["lang=en-US; Max-Age=123"]
    expected_out = [("lang", "en-US", [("Max-Age", 123)])]
    expected_err = []

class MaxAgeLeadingZeroScTest(rh.HeaderTest):
    name = "Set-Cookie"
    inputs = ["lang=en-US; Max-Age=0123"]
    expected_out = [("lang", "en-US", [])]
    expected_err = [rs.SET_COOKIE_LEADING_ZERO_MAX_AGE]

class RemoveSCTest(rh.HeaderTest):
    name = "Set-Cookie"
    inputs = ["lang=; Expires=Sun, 06 Nov 1994 08:49:37 GMT"]
    expected_out = [("lang", "", [("Expires", 784111777)])]
    expected_err = []

class WolframSCTest(rh.HeaderTest):
    name = "Set-Cookie"
    inputs = ["WR_SID=50.56.234.188.1393830943825054; path=/; max-age=315360000; domain=.wolframalpha.com"]
    expected_out = [("WR_SID","50.56.234.188.1393830943825054", [('Path', '/'), ('Max-Age', 315360000), ('Domain', 'wolframalpha.com')])]
    expected_err = []
########NEW FILE########
__FILENAME__ = set_cookie2
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax

@rh.ResponseHeader
def parse(subject, value, red):
    red.add_note(subject, 
                    rs.HEADER_DEPRECATED, 
                    header_name="Set-Cookie2",
                    ref=rh.rfc6265 % "section-9.4"
    )
    return value
    
@rh.SingleFieldValue
def join(subject, values, red):
    return values[-1]
########NEW FILE########
__FILENAME__ = soapaction
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


def parse(subject, value, red):
    return value
    
@rh.SingleFieldValue
def join(subject, values, red):
    return values[-1]
########NEW FILE########
__FILENAME__ = tcn
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
def parse(subject, value, red):
    # See #57
    pass
    
def join(subject, values, red):
    return values
########NEW FILE########
__FILENAME__ = transfer_encoding
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
@rh.CheckFieldSyntax(syntax.TOK_PARAM, rh.rfc2616 % "sec-14.41")
def parse(subject, value, red):
    try:
        coding, params = value.split(";", 1)
    except ValueError:
        coding, params = value, ""
    coding = coding.lower()
    param_dict = rh.parse_params(red, subject, params, True)
    if param_dict:
        red.add_note(subject, rs.TRANSFER_CODING_PARAM)
    return coding

def join(subject, values, red):
    unwanted = set([c for c in values if c not in
        ['chunked', 'identity']]
    ) or False
    if unwanted:
        red.add_note(subject, rs.TRANSFER_CODING_UNWANTED,
                unwanted_codings=", ".join(unwanted))
    if 'identity' in values:
        red.add_note(subject, rs.TRANSFER_CODING_IDENTITY)
    return values


class TransferEncodingTest(rh.HeaderTest):
    name = 'Transfer-Encoding'
    inputs = ['chunked']
    expected_out = (['chunked'])
    expected_err = []

class TransferEncodingParamTest(rh.HeaderTest):
    name = 'Transfer-Encoding'
    inputs = ['chunked; foo=bar']
    expected_out = (['chunked'])
    expected_err = [rs.TRANSFER_CODING_PARAM]

class BadTransferEncodingTest(rh.HeaderTest):
    name = 'Transfer-Encoding'
    inputs = ['chunked=foo']
    expected_out = []
    expected_err = [rs.BAD_SYNTAX]

class TransferEncodingCaseTest(rh.HeaderTest):
    name = 'Transfer-Encoding'
    inputs = ['chUNked']
    expected_out = (['chunked'])
    expected_err = []

class TransferEncodingIdentityTest(rh.HeaderTest):
    name = 'Transfer-Encoding'
    inputs = ['identity']
    expected_out = (['identity'])
    expected_err = [rs.TRANSFER_CODING_IDENTITY]

class TransferEncodingUnwantedTest(rh.HeaderTest):
    name = 'Transfer-Encoding'
    inputs = ['foo']
    expected_out = (['foo'])
    expected_err = [rs.TRANSFER_CODING_UNWANTED]
    
class TransferEncodingMultTest(rh.HeaderTest):
    name = 'Transfer-Encoding'
    inputs = ['chunked', 'identity']
    expected_out = (['chunked', 'identity'])
    expected_err = [rs.TRANSFER_CODING_IDENTITY]

class TransferEncodingMultUnwantedTest(rh.HeaderTest):
    name = 'Transfer-Encoding'
    inputs = ['chunked', 'foo', 'bar']
    expected_out = (['chunked', 'foo', 'bar'])
    expected_err = [rs.TRANSFER_CODING_UNWANTED]

########NEW FILE########
__FILENAME__ = vary
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
@rh.ResponseHeader
@rh.CheckFieldSyntax(syntax.TOKEN, rh.rfc2616 % "sec-14.44")
def parse(subject, value, red):
    return value.lower()
    
def join(subject, values, red):
    return set(values)
########NEW FILE########
__FILENAME__ = via
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
@rh.CheckFieldSyntax(
    r'(?:%s/)?%s\s+[^,\s]+(?:\s+%s)?' % (
      syntax.TOKEN, syntax.TOKEN, syntax.COMMENT),
    rh.rfc2616 % "sec-14.45")
def parse(subject, value, red):
    return value
    
def join(subject, values, red):
    via_list = u"<ul>" + u"\n".join(
           [u"<li><code>%s</code></li>" % v for v in values]
                       ) + u"</ul>"
    red.add_note(subject, rs.VIA_PRESENT, via_list=via_list)
    
########NEW FILE########
__FILENAME__ = warning
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
@rh.ResponseHeader
def parse(subject, value, red):
    # See #58
    return value
    
def join(subject, values, red):
    return values
########NEW FILE########
__FILENAME__ = x_cache
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
def parse(subject, value, red):
    # see #63
    return value
    
def join(subject, values, red):
    return values
########NEW FILE########
__FILENAME__ = x_content_type_options
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
def parse(subject, value, red):
    return value
    
def join(subject, values, red):
    if 'nosniff' in values:
        red.add_note(subject, rs.CONTENT_TYPE_OPTIONS)
    else:
        red.add_note(subject, rs.CONTENT_TYPE_OPTIONS_UNKNOWN)
    return values

########NEW FILE########
__FILENAME__ = x_download_options
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
def parse(subject, value, red):
    return value
    
def join(subject, values, red):
    if 'noopen' in values:
        red.add_note(subject, rs.DOWNLOAD_OPTIONS)
    else:
        red.add_note(subject, rs.DOWNLOAD_OPTIONS_UNKNOWN)
    return values

########NEW FILE########
__FILENAME__ = x_frame_options
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
def parse(subject, value, red):
    return value.lower()
    
def join(subject, values, red):
    if 'deny' in values:
        red.add_note(subject, rs.FRAME_OPTIONS_DENY)
    elif 'sameorigin' in values:
        red.add_note(subject, rs.FRAME_OPTIONS_SAMEORIGIN)
    else:
        red.add_note(subject, rs.FRAME_OPTIONS_UNKNOWN)
    return values


class DenyXFOTest(rh.HeaderTest):
    name = 'X-Frame-Options'
    inputs = ['deny']
    expected_out = ['deny']
    expected_err = [rs.FRAME_OPTIONS_DENY]
    
class DenyXFOCaseTest(rh.HeaderTest):
    name = 'X-Frame-Options'
    inputs = ['DENY']
    expected_out = ['deny']
    expected_err = [rs.FRAME_OPTIONS_DENY]
    
class SameOriginXFOTest(rh.HeaderTest):
    name = 'X-Frame-Options'
    inputs = ['sameorigin']
    expected_out = ['sameorigin']
    expected_err = [rs.FRAME_OPTIONS_SAMEORIGIN]

class UnknownXFOTest(rh.HeaderTest):
    name = 'X-Frame-Options'
    inputs = ['foO']
    expected_out = ['foo']
    expected_err = [rs.FRAME_OPTIONS_UNKNOWN]


########NEW FILE########
__FILENAME__ = x_meta_mssmarttagspreventparsing
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
def parse(subject, value, red):
    return value

def join(subject, values, red):
    red.add_note(subject, rs.SMART_TAG_NO_WORK)
    return values
########NEW FILE########
__FILENAME__ = x_pingback
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


def parse(subject, value, red):
    return value

@rh.SingleFieldValue
def join(subject, values, red):
    return values[-1]
########NEW FILE########
__FILENAME__ = x_ua_compatible
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
@rh.CheckFieldSyntax(
    syntax.PARAMETER,
    "http://msdn.microsoft.com/en-us/library/cc288325(VS.85).aspx")
def parse(subject, value, red):
    try:
        attr, attr_value = value.split("=", 1)
    except ValueError:
        attr = value
        attr_value = None
    return attr, attr_value


def join(subject, values, red):
    directives = {}
    warned = False
    for (attr, attr_value) in values:
        if directives.has_key(attr) and not warned:
            red.add_note(subject, rs.UA_COMPATIBLE_REPEAT)
            warned = True
        directives[attr] = attr_value
    red.add_note(subject, rs.UA_COMPATIBLE)
    return directives
    
class BasicUACTest(rh.HeaderTest):
    name = 'X-UA-Compatible'
    inputs = ['foo=bar']
    expected_out = {"foo": "bar"}
    expected_err = [rs.UA_COMPATIBLE]
########NEW FILE########
__FILENAME__ = x_xrds_location
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
def parse(subject, value, red):
    return value
    
@rh.SingleFieldValue
def join(subject, values, red):
    return values[-1]
########NEW FILE########
__FILENAME__ = x_xss_protection
#!/usr/bin/env python

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


import redbot.speak as rs
from redbot.message import headers as rh
from redbot.message import http_syntax as syntax


@rh.GenericHeaderSyntax
@rh.CheckFieldSyntax(
    r'(?:[10](?:\s*;\s*%(PARAMETER)s)*)' % syntax.__dict__, 'http://blogs.msdn.com/b/ieinternals/archive/2011/01/31/controlling-the-internet-explorer-xss-filter-with-the-x-xss-protection-http-header.aspx'
)
def parse(subject, value, red):
    try:
        protect, param_str = value.split(';', 1)
    except ValueError:
        protect, param_str = value, ""
    protect = int(protect)
    params = rh.parse_params(red, subject, param_str, True)
    if protect == 0:
        red.add_note(subject, rs.XSS_PROTECTION_OFF)
    else: # 1
        if params.get('mode', None) == "block":
            red.add_note(subject, rs.XSS_PROTECTION_BLOCK)
        else:
            red.add_note(subject, rs.XSS_PROTECTION_ON)
    return protect, params

@rh.SingleFieldValue
def join(subject, values, red):
    return values[-1]


class OneXXSSTest(rh.HeaderTest):
    name = 'X-XSS-Protection'
    inputs = ['1']
    expected_out = (1, {})
    expected_err = [rs.XSS_PROTECTION_ON]

class ZeroXXSSTest(rh.HeaderTest):
    name = 'X-XSS-Protection'
    inputs = ['0']
    expected_out = (0, {})
    expected_err = [rs.XSS_PROTECTION_OFF]

class OneBlockXXSSTest(rh.HeaderTest):
    name = 'X-XSS-Protection'
    inputs = ['1; mode=block']
    expected_out = (1, {'mode': 'block'})
    expected_err = [rs.XSS_PROTECTION_BLOCK]
    
class BadXXSSTest(rh.HeaderTest):
    name = 'X-XSS-Protection'
    inputs = ['foo']
    expected_out = None
    expected_err = [rs.BAD_SYNTAX]

########NEW FILE########
__FILENAME__ = http_syntax
#!/usr/bin/env python

"""
HTTP Syntax
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""

# URI syntax
from redbot.message.uri_syntax import URI, URI_reference, absolute_URI

# generic syntax regexen (assume processing with re.VERBOSE)
TOKEN = r'(?:[!#\$%&\'\*\+\-\.\^_`|~A-Za-z0-9]+?)'
QUOTED_STRING = r'(?:"(?:[ \t\x21\x23-\x5B\x5D-\x7E]|\\[ \t\x21-\x7E])*")'
PARAMETER = r'(?:%(TOKEN)s(?:\s*=\s*(?:%(TOKEN)s|%(QUOTED_STRING)s))?)' % locals()
TOK_PARAM = r'(?:%(TOKEN)s(?:\s*;\s*%(PARAMETER)s)*)' % locals()
PRODUCT = r'(?:%(TOKEN)s(?:/%(TOKEN)s)?)' % locals()
COMMENT = r"""(?:
    \((?:
        [^\(\)] |
        \\\( |
        \\\) |
        (?:
            \((?:
                [^\(\)] |
                \\\( |
                \\\) |
                (?:
                    \((?:
                        [^\(\)] |
                        \\\( |
                        \\\)
                    )*\)
                )
            )*\)
        )
    )*\)
)""" # only handles two levels of nested comments; does not check chars
COMMA = r'(?:\s*(?:,\s*)+)'
DIGITS = r'(?:[0-9]+)'
DATE = r"""(?:\w{3},\ [0-9]{2}\ \w{3}\ [0-9]{4}\ [0-9]{2}:[0-9]{2}:[0-9]{2}\ GMT |
         \w{6,9},\ [0-9]{2}\-\w{3}\-[0-9]{2}\ [0-9]{2}:[0-9]{2}:[0-9]{2}\ GMT |
         \w{3}\ \w{3}\ [0-9 ][0-9]\ [0-9]{2}:[0-9]{2}:[0-9]{2}\ [0-9]{4})
        """
########NEW FILE########
__FILENAME__ = link_parse
#!/usr/bin/env python

"""
Parsing links from streams of data.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""

from htmlentitydefs import entitydefs
from HTMLParser import HTMLParser

from redbot.message import headers as rh
from redbot.message import http_syntax as syntax

class HTMLLinkParser(HTMLParser):
    """
    Parse the links out of an HTML document in a very forgiving way.

    feed() accepts a HttpResponse object and a chunk of the document at a
    time.

    When links are found, link_procs will be called for each with the
    following arguments;
      - base (base URI for the link, in a unicode string)
      - link (URI as it appeared in document, in a unicode string)
      - tag (name of the element that contained it)
      - title (title attribute as a unicode string, if any)
    """

    link_parseable_types = [
        'text/html',
        'application/xhtml+xml',
        'application/atom+xml'
    ]

    def __init__(self, base_uri, link_procs, err=None):
        self.base = base_uri
        self.link_procs = link_procs
        self.err = err
        self.doc_enc = None
        self.link_types = {
            'link': ['href', ['stylesheet']],
            'a': ['href', None],
            'img': ['src', None],
            'script': ['src', None],
            'frame': ['src', None],
            'iframe': ['src', None],
        }
        self.errors = 0
        self.last_err_pos = None
        self.ok = True
        HTMLParser.__init__(self)

    def __getstate__(self):
        return {
            'base': self.base,
            'doc_enc': self.doc_enc,
            'errors': self.errors,
            'last_err_pos': self.last_err_pos,
            'ok': self.ok,
        }

    def feed(self, msg, chunk):
        "Feed a given chunk of HTML data to the parser"
        if not self.ok:
            return
        if msg.parsed_headers.get('content-type', [None])[0] in \
          self.link_parseable_types:
            try:
                if chunk.__class__.__name__ != 'unicode':
                    try:
                        chunk = unicode(
                            chunk, 
                            self.doc_enc or msg.character_encoding, 
                            'ignore'
                        )
                    except LookupError:
                        pass
                HTMLParser.feed(self, chunk)
            except BadErrorIReallyMeanIt:
                pass
            except Exception, why: # oh, well...
                if self.err:
                    self.err("feed problem: %s" % why)
                self.errors += 1
        else:
            self.ok = False

    def handle_starttag(self, tag, attrs):
        attr_d = dict(attrs)
        title = attr_d.get('title', '').strip()
        if tag in self.link_types.keys():
            url_attr, rels = self.link_types[tag]
            if not rels or attr_d.get("rel", None) in rels:
                target = attr_d.get(url_attr, "")
                if target:
                    if "#" in target:
                        target = target[:target.index('#')]
                    for proc in self.link_procs:
                        proc(self.base, target, tag, title)
        elif tag == 'base':
            self.base = attr_d.get('href', self.base)
        elif tag == 'meta' and \
          attr_d.get('http-equiv', '').lower() == 'content-type':
            ct = attr_d.get('content', None)
            if ct:
                try:
                    media_type, params = ct.split(";", 1)
                except ValueError:
                    media_type, params = ct, ''
                media_type = media_type.lower()
                param_dict = {}
                for param in rh.split_string(
                    params, syntax.PARAMETER, "\s*;\s*"
                ):
                    try:
                        a, v = param.split("=", 1)
                        param_dict[a.lower()] = rh.unquote_string(v)
                    except ValueError:
                        param_dict[param.lower()] = None
                self.doc_enc = param_dict.get('charset', self.doc_enc)

    def handle_charref(self, name):
        return entitydefs.get(name, '')

    def handle_entityref(self, name):
        return entitydefs.get(name, '')

    def error(self, message):
        self.errors += 1
        if self.getpos() == self.last_err_pos:
            # we're in a loop; give up.
            if self.err:
                self.err(
                    "giving up on link parsing after %s errors" % self.errors
                )
            self.ok = False
            raise BadErrorIReallyMeanIt()
        else:
            self.last_err_pos = self.getpos()
            if self.err:
                self.err(message)

class BadErrorIReallyMeanIt(Exception):
    """See http://bugs.python.org/issue8885 for why this is necessary."""
    pass

if "__main__" == __name__:
    import sys
    from redbot.resource.fetch import RedFetcher
    uri = sys.argv[1]
    req_hdrs = [(u'Accept-Encoding', u'gzip')]
    class TestFetcher(RedFetcher):
        count = 0
        def done(self):
            pass
        @staticmethod
        def err(mesg):
            sys.stderr.write("ERROR: %s\n" % mesg)        
        @staticmethod
        def show_link(link, tag, title):
            TestFetcher.count += 1
            out = "%.3d) [%s] %s" % (TestFetcher.count, tag, link)
            print out.encode('utf-8', 'strict')
    p = HTMLLinkParser(uri, TestFetcher.show_link, TestFetcher.err)
    TestFetcher(uri, req_hdrs=req_hdrs, body_procs=[p.feed])

########NEW FILE########
__FILENAME__ = status
#!/usr/bin/env python

"""
The Resource Expert Droid Status Code Checker.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


from thor.http import header_dict, get_header, safe_methods
import redbot.speak as rs


class StatusChecker:
    """
    Given a response, check out the status code and perform 
    appropriate tests on it.
    
    Additional tests will be performed if the request is available.
    """
    def __init__(self, response, request=None):
        assert response.is_request is False
        self.request = request
        self.response = response
        try:
            status_m = getattr(self, "status%s" % response.status_code.encode('ascii', 'ignore'))
        except AttributeError:
            self.add_note('status', rs.STATUS_NONSTANDARD)
            return
        status_m()

    def add_note(self, name, note, **kw):
        if name:
            subject = 'status %s' % name
        else:
            subject = 'status'
        self.response.add_note(
            subject, 
            note,
            status=self.response.status_code,
            **kw
        )

    def status100(self):        # Continue
        if self.request and not "100-continue" in get_header(
            self.request.headers, 'expect'):
            self.add_note('', rs.UNEXPECTED_CONTINUE)
    def status101(self):        # Switching Protocols
        if self.request \
        and not 'upgrade' in header_dict(self.request.headers).keys():
            self.add_note('', rs.UPGRADE_NOT_REQUESTED)
    def status102(self):        # Processing
        pass
    def status200(self):        # OK
        pass
    def status201(self):        # Created
        if self.request and self.request.method in safe_methods:
            self.add_note('status', 
                rs.CREATED_SAFE_METHOD, 
                method=self.request.method
            )
        if not self.response.parsed_headers.has_key('location'):
            self.add_note('header-location', rs.CREATED_WITHOUT_LOCATION)
    def status202(self):        # Accepted
        pass
    def status203(self):        # Non-Authoritative Information
        pass
    def status204(self):        # No Content
        pass
    def status205(self):        # Reset Content
        pass
    def status206(self):        # Partial Content
        if self.request \
        and not "range" in header_dict(self.request.headers).keys():
            self.add_note('', rs.PARTIAL_NOT_REQUESTED)
        if not self.response.parsed_headers.has_key('content-range'):
            self.add_note('header-location', rs.PARTIAL_WITHOUT_RANGE)
    def status207(self):        # Multi-Status
        pass
    def status226(self):        # IM Used
        pass
    def status300(self):        # Multiple Choices
        pass
    def status301(self):        # Moved Permanently
        if not self.response.parsed_headers.has_key('location'):
            self.add_note('header-location', rs.REDIRECT_WITHOUT_LOCATION)
    def status302(self):        # Found
        if not self.response.parsed_headers.has_key('location'):
            self.add_note('header-location', rs.REDIRECT_WITHOUT_LOCATION)
    def status303(self):        # See Other
        if not self.response.parsed_headers.has_key('location'):
            self.add_note('header-location', rs.REDIRECT_WITHOUT_LOCATION)
    def status304(self):        # Not Modified
        if not self.response.parsed_headers.has_key('date'):
            self.add_note('status', rs.NO_DATE_304)
    def status305(self):        # Use Proxy
        self.add_note('', rs.STATUS_DEPRECATED)
    def status306(self):        # Reserved
        self.add_note('', rs.STATUS_RESERVED)
    def status307(self):        # Temporary Redirect
        if not self.response.parsed_headers.has_key('location'):
            self.add_note('header-location', rs.REDIRECT_WITHOUT_LOCATION)
    def status400(self):        # Bad Request
        self.add_note('', rs.STATUS_BAD_REQUEST)
    def status401(self):        # Unauthorized
        pass
    def status402(self):        # Payment Required
        pass
    def status403(self):        # Forbidden
        self.add_note('', rs.STATUS_FORBIDDEN)
    def status404(self):        # Not Found
        self.add_note('', rs.STATUS_NOT_FOUND)
    def status405(self):        # Method Not Allowed
        pass # TODO: show allowed methods?
    def status406(self):        # Not Acceptable
        self.add_note('', rs.STATUS_NOT_ACCEPTABLE)
    def status407(self):        # Proxy Authentication Required
        pass
    def status408(self):        # Request Timeout
        pass
    def status409(self):        # Conflict
        self.add_note('', rs.STATUS_CONFLICT)
    def status410(self):        # Gone
        self.add_note('', rs.STATUS_GONE)
    def status411(self):        # Length Required
        pass
    def status412(self):        # Precondition Failed
        pass # TODO: test to see if it's true, alert if not
    def status413(self):        # Request Entity Too Large
        self.add_note('', rs.STATUS_REQUEST_ENTITY_TOO_LARGE)
    def status414(self):        # Request-URI Too Long
        if self.request:
            uri_len = "(%s characters)" % len(self.request.uri)
        else:
            uri_len = ""
        self.add_note('uri', rs.STATUS_URI_TOO_LONG, uri_len=uri_len)
    def status415(self):        # Unsupported Media Type
        self.add_note('', rs.STATUS_UNSUPPORTED_MEDIA_TYPE)
    def status416(self):        # Requested Range Not Satisfiable
        pass # TODO: test to see if it's true, alter if not
    def status417(self):        # Expectation Failed
        pass # TODO: explain, alert if it's 100-continue
    def status422(self):        # Unprocessable Entity
        pass
    def status423(self):        # Locked
        pass
    def status424(self):        # Failed Dependency
        pass
    def status426(self):        # Upgrade Required
        pass
    def status500(self):        # Internal Server Error
        self.add_note('', rs.STATUS_INTERNAL_SERVICE_ERROR)
    def status501(self):        # Not Implemented
        self.add_note('', rs.STATUS_NOT_IMPLEMENTED)
    def status502(self):        # Bad Gateway
        self.add_note('', rs.STATUS_BAD_GATEWAY)
    def status503(self):        # Service Unavailable
        self.add_note('', rs.STATUS_SERVICE_UNAVAILABLE)
    def status504(self):        # Gateway Timeout
        self.add_note('', rs.STATUS_GATEWAY_TIMEOUT)
    def status505(self):        # HTTP Version Not Supported
        self.add_note('', rs.STATUS_VERSION_NOT_SUPPORTED)
    def status506(self):        # Variant Also Negotiates
        pass
    def status507(self):        # Insufficient Storage
        pass
    def status510(self):        # Not Extended
        pass

########NEW FILE########
__FILENAME__ = uri_syntax
#!/usr/bin/env python

"""
Regex for URIs

These regex are directly derived from the collected ABNF in RFC3986
(except for DIGIT, ALPHA and HEXDIG, defined by RFC2234).

They should be processed with re.VERBOSE.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__license__ = """
Copyright (c) 2009-2013 Mark Nottingham (code portions)

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
"""

### basics

DIGIT = r"[\x30-\x39]"

ALPHA = r"[\x41-\x5A\x61-\x7A]"

HEXDIG = r"[\x30-\x39A-Fa-f]"

#   pct-encoded   = "%" HEXDIG HEXDIG
pct_encoded = r" %% %(HEXDIG)s %(HEXDIG)s"  % locals()

#   unreserved    = ALPHA / DIGIT / "-" / "." / "_" / "~"
unreserved = r"(?: %(ALPHA)s | %(DIGIT)s | \- | \. | _ | ~ )"  % locals()

#   gen-delims    = ":" / "/" / "?" / "#" / "[" / "]" / "@"
gen_delims = r"(?: : | / | \? | \# | \[ | \] | @ )"

#   sub-delims    = "!" / "$" / "&" / "'" / "(" / ")"
#                 / "*" / "+" / "," / ";" / "="
sub_delims = r"""(?: ! | \$ | & | ' | \( | \) |
                     \* | \+ | , | ; | = )"""

#   pchar         = unreserved / pct-encoded / sub-delims / ":" / "@"
pchar = r"(?: %(unreserved)s | %(pct_encoded)s | %(sub_delims)s | : | @ )" % locals()

#   reserved      = gen-delims / sub-delims
reserved = r"(?: %(gen_delims)s | %(sub_delims)s )" % locals()


### scheme

#   scheme        = ALPHA *( ALPHA / DIGIT / "+" / "-" / "." )
scheme = r"%(ALPHA)s (?: %(ALPHA)s | %(DIGIT)s | \+ | \- | \. )*" % locals()


### authority

#   dec-octet     = DIGIT                 ; 0-9
#                 / %x31-39 DIGIT         ; 10-99
#                 / "1" 2DIGIT            ; 100-199
#                 / "2" %x30-34 DIGIT     ; 200-249
#                 / "25" %x30-35          ; 250-255
dec_octet = r"""(?: %(DIGIT)s |
                    [\x31-\x39] %(DIGIT)s |
                    1 %(DIGIT)s{2} |
                    2 [\x30-\x34] %(DIGIT)s |
                    25 [\x30-\x35]
                )
""" % locals()

#  IPv4address   = dec-octet "." dec-octet "." dec-octet "." dec-octet
IPv4address = r"%(dec_octet)s \. %(dec_octet)s \. %(dec_octet)s \. %(dec_octet)s" % locals()

#  h16           = 1*4HEXDIG
h16 = r"(?: %(HEXDIG)s ){1,4}" % locals()

#  ls32          = ( h16 ":" h16 ) / IPv4address
ls32 = r"(?: (?: %(h16)s : %(h16)s ) | %(IPv4address)s )" % locals()

#   IPv6address   =                            6( h16 ":" ) ls32
#                 /                       "::" 5( h16 ":" ) ls32
#                 / [               h16 ] "::" 4( h16 ":" ) ls32
#                 / [ *1( h16 ":" ) h16 ] "::" 3( h16 ":" ) ls32
#                 / [ *2( h16 ":" ) h16 ] "::" 2( h16 ":" ) ls32
#                 / [ *3( h16 ":" ) h16 ] "::"    h16 ":"   ls32
#                 / [ *4( h16 ":" ) h16 ] "::"              ls32
#                 / [ *5( h16 ":" ) h16 ] "::"              h16
#                 / [ *6( h16 ":" ) h16 ] "::"
IPv6address = r"""(?:                                  (?: %(h16)s : ){6} %(ls32)s |
                                                    :: (?: %(h16)s : ){5} %(ls32)s |
                                            %(h16)s :: (?: %(h16)s : ){4} %(ls32)s |
                         (?: %(h16)s : )    %(h16)s :: (?: %(h16)s : ){3} %(ls32)s |
                         (?: %(h16)s : ){2} %(h16)s :: (?: %(h16)s : ){2} %(ls32)s |
                         (?: %(h16)s : ){3} %(h16)s ::     %(h16)s :      %(ls32)s |
                         (?: %(h16)s : ){4} %(h16)s ::                    %(ls32)s |
                         (?: %(h16)s : ){5} %(h16)s ::                    %(h16)s  |
                         (?: %(h16)s : ){6} %(h16)s ::
                  )
""" % locals()

#   IPvFuture     = "v" 1*HEXDIG "." 1*( unreserved / sub-delims / ":" )
IPvFuture = r"v %(HEXDIG)s+ \. (?: %(unreserved)s | %(sub_delims)s | : )+" % locals()

#   IP-literal    = "[" ( IPv6address / IPvFuture  ) "]"
IP_literal = r"\[ (?: %(IPv6address)s | %(IPvFuture)s ) \]" % locals()

#   reg-name      = *( unreserved / pct-encoded / sub-delims )
reg_name = r"(?: %(unreserved)s | %(pct_encoded)s | %(sub_delims)s )*" % locals()

#   userinfo      = *( unreserved / pct-encoded / sub-delims / ":" )
userinfo = r"(?: %(unreserved)s | %(pct_encoded)s | %(sub_delims)s | : )" % locals()

#   host          = IP-literal / IPv4address / reg-name
host = r"(?: %(IP_literal)s | %(IPv4address)s | %(reg_name)s )" % locals()

#   port          = *DIGIT
port = r"(?: %(DIGIT)s )*" % locals()

#   authority     = [ userinfo "@" ] host [ ":" port ]
authority = r"(?: %(userinfo)s @)? %(host)s (?: : %(port)s)?" % locals()



### Path

#   segment       = *pchar
segment = r"%(pchar)s*" % locals()

#   segment-nz    = 1*pchar
segment_nz = r"%(pchar)s+" % locals()

#   segment-nz-nc = 1*( unreserved / pct-encoded / sub-delims / "@" )
#                 ; non-zero-length segment without any colon ":"
segment_nz_nc = r"(?: %(unreserved)s | %(pct_encoded)s | %(sub_delims)s | @ )+" % locals()

#   path-abempty  = *( "/" segment )
path_abempty = r"(?: / %(segment)s )*" % locals()

#   path-absolute = "/" [ segment-nz *( "/" segment ) ]
path_absolute = r"/ (?: %(segment_nz)s (?: / %(segment)s )* )?" % locals()

#   path-noscheme = segment-nz-nc *( "/" segment )
path_noscheme = r"%(segment_nz_nc)s (?: / %(segment)s )*" % locals()

#   path-rootless = segment-nz *( "/" segment )
path_rootless = r"%(segment_nz)s (?: / %(segment)s )*" % locals()

#   path-empty    = 0<pchar>
path_empty = r"%(pchar)s{0}"

#   path          = path-abempty    ; begins with "/" or is empty
#                 / path-absolute   ; begins with "/" but not "//"
#                 / path-noscheme   ; begins with a non-colon segment
#                 / path-rootless   ; begins with a segment
#                 / path-empty      ; zero characters
path = r"""(?: %(path_abempty)s |
               %(path_absolute)s |
               %(path_noscheme)s |
               %(path_rootless)s |
               %(path_empty)s
            )
""" % locals()



### Query and Fragment

#   query         = *( pchar / "/" / "?" )
query = r"(?: %(pchar)s | / | \? )*" % locals()

#   fragment      = *( pchar / "/" / "?" )
fragment = r"(?: %(pchar)s | / | \? )*" % locals()



### URIs

#   hier-part     = "//" authority path-abempty
#                 / path-absolute
#                 / path-rootless
#                 / path-empty
hier_part = r"""(?: (?: // %(authority)s %(path_abempty)s ) |
                    %(path_absolute)s |
                    %(path_rootless)s |
                    %(path_empty)s
                )
""" % locals()

#   relative-part = "//" authority path-abempty
#                 / path-absolute
#                 / path-noscheme
#                 / path-empty
relative_part = r"""(?: (?: // %(authority)s %(path_abempty)s ) |
                        %(path_absolute)s |
                        %(path_noscheme)s |
                        %(path_empty)s
                    )
""" % locals()

#   relative-ref  = relative-part [ "?" query ] [ "#" fragment ]
relative_ref = r"%(relative_part)s (?: \? %(query)s)? (?: \# %(fragment)s)?" % locals()

#   URI           = scheme ":" hier-part [ "?" query ] [ "#" fragment ]
URI = r"(?: %(scheme)s : %(hier_part)s (?: \? %(query)s )? (?: \# %(fragment)s )? )" % locals()

#   URI-reference = URI / relative-ref
URI_reference = r"(?: %(URI)s | %(relative_ref)s )" % locals()

#   absolute-URI  = scheme ":" hier-part [ "?" query ]
absolute_URI = r"(?: %(scheme)s : %(hier_part)s (?: \? %(query)s )? )" % locals()


if "__main__" == __name__:
    import re
    import sys
    try:
        instr = sys.argv[1]
    except IndexError:
        print "usage: %s test-string" % sys.argv[0]
        sys.exit(1)

    print 'testing: "%s"' % instr

    print "URI:",
    if re.match("^%s$" % URI, instr, re.VERBOSE):
        print "yes"
    else:
        print "no"

    print "URI reference:",
    if re.match("^%s$" % URI_reference, instr, re.VERBOSE):
        print "yes"
    else:
        print "no"

    print "Absolute URI:",
    if re.match("^%s$" % absolute_URI, instr, re.VERBOSE):
        print "yes"
    else:
        print "no"

########NEW FILE########
__FILENAME__ = base
#!/usr/bin/env python

"""
Subrequests to do things like range requests, content negotiation checks,
and validation.

This is the base class for all subrequests.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""

from redbot.resource.fetch import RedFetcher


class SubRequest(RedFetcher):
    """
    Base class for a subrequest of a "main" HttpResource, made to perform
    additional behavioural tests on the resource.
    """
    def __init__(self, base_resource, name):
        self.base = base_resource
        req_hdrs = self.modify_req_hdrs()
        RedFetcher.__init__(self, 
                            self.base.request.uri, 
                            self.base.request.method, 
                            req_hdrs,
                            self.base.request.payload, 
                            self.base.status_cb, 
                            [], 
                            name
        )
        self.base.subreqs[name] = self
    
    def modify_req_hdrs(self):
        """
        Usually overidden; modifies the request's headers.
        
        Make sure it returns a copy of the orignals, not them.
        """
        return list(self.base.orig_req_hdrs)

    def add_note(self, subject, note, subreq=None, **kw):
        self.base.add_note(subject, note, self.name, **kw)
        
    def check_missing_hdrs(self, hdrs, note, subreq_type):
        """
        See if the listed headers are missing in the subrequest; if so,
        set the specified note.
        """
        missing_hdrs = []
        for hdr in hdrs:
            if self.base.response.parsed_headers.has_key(hdr) \
            and not self.response.parsed_headers.has_key(hdr):
                missing_hdrs.append(hdr)
        if missing_hdrs:
            self.add_note('headers', note,
                missing_hdrs=", ".join(missing_hdrs),
                subreq_type=subreq_type
            )

########NEW FILE########
__FILENAME__ = conneg
#!/usr/bin/env python

"""
Subrequest for content negotiation checks.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


from redbot.resource.active_check.base import SubRequest
from redbot.formatter import f_num
import redbot.speak as rs

class ConnegCheck(SubRequest):
    """
    See if content negotiation for compression is supported, and how.

    Note that this depends on the "main" request being sent with
    Accept-Encoding: gzip
    """
    def modify_req_hdrs(self):
        return [h for h in self.base.orig_req_hdrs 
                  if h[0].lower() != 'accept-encoding'] + \
               [(u'accept-encoding', u'identity')]

    def preflight(self):
        if "gzip" in \
          self.base.response.parsed_headers.get('content-encoding', []):
            return True
        else:
            self.base.gzip_support = False
            return False

    def done(self):
        if not self.response.complete:
            self.add_note('', rs.CONNEG_SUBREQ_PROBLEM,
                problem=self.response.http_error.desc
            )
            return
            
        # see if it was compressed when not negotiated
        no_conneg_vary_headers = \
          self.response.parsed_headers.get('vary', [])
        if 'gzip' in \
          self.response.parsed_headers.get('content-encoding', []) \
          or 'x-gzip' in \
          self.response.parsed_headers.get('content-encoding', []):
            self.add_note('header-vary header-content-encoding',
                            rs.CONNEG_GZIP_WITHOUT_ASKING)
        else: # Apparently, content negotiation is happening.

            # check status
            if self.base.response.status_code != \
               self.response.status_code:
                self.add_note('status', rs.VARY_STATUS_MISMATCH, 
                  neg_status=self.base.response.status_code,
                  noneg_status=self.response.status_code)
                return  # Can't be sure what's going on...

            # check headers that should be invariant
            for hdr in ['content-type']:
                if self.base.response.parsed_headers.get(hdr) != \
                  self.response.parsed_headers.get(hdr, None):
                    self.add_note('header-%s' % hdr,
                      rs.VARY_HEADER_MISMATCH, 
                      header=hdr)
                    # TODO: expose on-the-wire values.

            # check Vary headers
            vary_headers = self.base.response.parsed_headers.get('vary', [])
            if (not "accept-encoding" in vary_headers) and \
               (not "*" in vary_headers):
                self.add_note('header-vary', rs.CONNEG_NO_VARY)
            if no_conneg_vary_headers != vary_headers:
                self.add_note('header-vary', 
                    rs.VARY_INCONSISTENT,
                    conneg_vary=", ".join(vary_headers),
                    no_conneg_vary=", ".join(no_conneg_vary_headers)
                )

            # check body
            if self.base.response.decoded_md5 != \
               self.response.payload_md5:
                self.add_note('body', rs.VARY_BODY_MISMATCH)

            # check ETag
            if (self.response.parsed_headers.get('etag', 1) == \
              self.base.response.parsed_headers.get('etag', 2)):
                if not self.base.response.parsed_headers['etag'][0]: # strong
                    self.add_note('header-etag',
                        rs.VARY_ETAG_DOESNT_CHANGE
                    ) 

            # check compression efficiency
            if self.response.payload_len > 0:
                savings = int(100 * 
                    (
                        (float(self.response.payload_len) - \
                        self.base.response.payload_len
                        ) / self.response.payload_len
                    )
                )
            else:
                savings = 0
            self.base.gzip_support = True
            self.base.gzip_savings = savings
            if savings >= 0:
                self.add_note('header-content-encoding',
                    rs.CONNEG_GZIP_GOOD,
                    savings=savings,
                    orig_size=f_num(self.response.payload_len),
                    gzip_size=f_num(self.base.response.payload_len)
                )
            else:
                self.add_note('header-content-encoding',
                    rs.CONNEG_GZIP_BAD,
                    savings=abs(savings),
                    orig_size=f_num(self.response.payload_len),
                    gzip_size=f_num(self.base.response.payload_len)
                )
########NEW FILE########
__FILENAME__ = etag_validate
#!/usr/bin/env python

"""
Subrequest for ETag validation checks.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""


from redbot.resource.active_check.base import SubRequest
import redbot.speak as rs

class ETagValidate(SubRequest):
    "If an ETag is present, see if it will validate."

    def modify_req_hdrs(self):
        req_hdrs = list(self.base.request.headers)
        if self.base.response.parsed_headers.has_key('etag'):
            weak, etag = self.base.response.parsed_headers['etag']
            if weak:
                weak_str = u"W/"
                # #65: note on weak etag
            else:
                weak_str = u""
            etag_str = u'%s"%s"' % (weak_str, etag)
            req_hdrs += [
                (u'If-None-Match', etag_str),
            ]
        return req_hdrs
            
    def preflight(self):
        if self.base.response.parsed_headers.has_key('etag'):
            return True
        else:
            self.base.inm_support = False
            return False

    def done(self):
        if not self.response.complete:
            self.add_note('', rs.ETAG_SUBREQ_PROBLEM,
                problem=self.response.http_error.desc
            )
            return
            
        if self.response.status_code == '304':
            self.base.inm_support = True
            self.add_note('header-etag', rs.INM_304)
            self.check_missing_hdrs([
                    'cache-control', 'content-location', 'etag', 
                    'expires', 'vary'
                ], rs.MISSING_HDRS_304, 'If-None-Match'
            )
        elif self.response.status_code \
          == self.base.response.status_code:
            if self.response.payload_md5 \
              == self.base.response.payload_md5:
                self.base.inm_support = False
                self.add_note('header-etag', rs.INM_FULL)
            else: # bodies are different
                if self.base.response.parsed_headers['etag'] == \
                  self.response.parsed_headers.get('etag', 1):
                    if self.base.response.parsed_headers['etag'][0]: # weak
                        self.add_note('header-etag', rs.INM_DUP_ETAG_WEAK)
                    else: # strong
                        self.add_note('header-etag',
                            rs.INM_DUP_ETAG_STRONG,
                            etag=self.base.response.parsed_headers['etag']
                        )
                else:
                    self.add_note('header-etag', rs.INM_UNKNOWN)
        else:
            self.add_note('header-etag', 
                rs.INM_STATUS, 
                inm_status = self.response.status_code,
                enc_inm_status = self.response.status_code \
                  or '(unknown)'
            )
        # TODO: check entity headers
########NEW FILE########
__FILENAME__ = lm_validate
#!/usr/bin/env python

"""
Subrequest for Last-Modified validation checks.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""

from datetime import datetime

from redbot.resource.active_check.base import SubRequest
import redbot.speak as rs

class LmValidate(SubRequest):
    "If Last-Modified is present, see if it will validate."

    _weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    _months = [None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 
                     'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    def modify_req_hdrs(self):
        req_hdrs = list(self.base.request.headers)
        if self.base.response.parsed_headers.has_key('last-modified'):
            try:
                l_m = datetime.utcfromtimestamp(
                    self.base.response.parsed_headers['last-modified']
                )
            except ValueError:
                return req_hdrs # TODO: sensible error message.
            date_str = u"%s, %.2d %s %.4d %.2d:%.2d:%.2d GMT" % (
                self._weekdays[l_m.weekday()],
                l_m.day,
                self._months[l_m.month],
                l_m.year,
                l_m.hour,
                l_m.minute,
                l_m.second
            )
            req_hdrs += [
                (u'If-Modified-Since', date_str),
            ]
        return req_hdrs

    def preflight(self):
        if self.base.response.parsed_headers.has_key('last-modified'):
            return True
        else:
            self.base.ims_support = False
            return False

    def done(self):
        if not self.response.complete:
            self.add_note('', rs.LM_SUBREQ_PROBLEM,
                problem=self.response.http_error.desc
            )
            return
            
        if self.response.status_code == '304':
            self.base.ims_support = True
            self.add_note('header-last-modified', rs.IMS_304)
            self.check_missing_hdrs([
                    'cache-control', 'content-location', 'etag', 
                    'expires', 'vary'
                ], rs.MISSING_HDRS_304, 'If-Modified-Since'
            )
        elif self.response.status_code \
          == self.base.response.status_code:
            if self.response.payload_md5 \
              == self.base.response.payload_md5:
                self.base.ims_support = False
                self.add_note('header-last-modified', rs.IMS_FULL)
            else:
                self.add_note('header-last-modified', rs.IMS_UNKNOWN)
        else:
            self.add_note('header-last-modified', 
                rs.IMS_STATUS, 
                ims_status = self.response.status_code,
                enc_ims_status = self.response.status_code \
                  or '(unknown)'
            )
        # TODO: check entity headers

########NEW FILE########
__FILENAME__ = range
#!/usr/bin/env python

"""
Subrequest for partial content checks.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""

import random

from redbot.resource.active_check.base import SubRequest
from redbot.formatter import f_num
import redbot.speak as rs

class RangeRequest(SubRequest):
    "Check for partial content support (if advertised)"

    def __init__(self, red, name):
        self.range_start = None
        self.range_end = None
        self.range_target = None
        SubRequest.__init__(self, red, name)
        
    def modify_req_hdrs(self):
        req_hdrs = list(self.base.request.headers)
        if len(self.base.response.payload_sample) != 0:
            sample_num = random.randint(
                0, 
                len(self.base.response.payload_sample) - 1
            )
            sample_len = min(
                96, 
                len(self.base.response.payload_sample[sample_num][1])
            )
            self.range_start = \
              self.base.response.payload_sample[sample_num][0]
            self.range_end = self.range_start + sample_len
            self.range_target = \
              self.base.response.payload_sample[sample_num][1] \
                [:sample_len + 1]
            # TODO: uses the compressed version (if available). Revisit.
            req_hdrs += [
                (u'Range', u"bytes=%s-%s" % (
                    self.range_start, self.range_end
                ))
            ]
        return req_hdrs
        
    def preflight(self):
        if 'bytes' in \
          self.base.response.parsed_headers.get('accept-ranges', []):
            if len(self.base.response.payload_sample) == 0:
                return False
            if self.range_start == self.range_end: 
                # wow, that's a small body.
                return False
            return True
        else:
            self.base.partial_support = False
            return False

    def done(self):
        if not self.response.complete:
            self.add_note('', rs.RANGE_SUBREQ_PROBLEM,
                problem=self.response.http_error.desc
            )
            return
            
        if self.response.status_code == '206':
            c_e = 'content-encoding'
            if 'gzip' in self.base.response.parsed_headers.get(c_e, []) == \
               'gzip' not in self.response.parsed_headers.get(c_e, []):
                self.add_note(
                    'header-accept-ranges header-content-encoding',
                    rs.RANGE_NEG_MISMATCH
                )
                return
            if not [True for h in self.base.orig_req_hdrs 
                if h[0].lower() == 'if-range']:
                self.check_missing_hdrs([
                        'date', 'cache-control', 'content-location', 'etag', 
                        'expires', 'vary'
                    ], rs.MISSING_HDRS_206, 'Range'
                )
            if self.response.parsed_headers.get('etag', 1) == \
              self.base.response.parsed_headers.get('etag', 2):
                if self.response.payload == self.range_target:
                    self.base.partial_support = True
                    self.add_note('header-accept-ranges', rs.RANGE_CORRECT)
                else:
                    # the body samples are just bags of bits
                    self.base.partial_support = False
                    self.add_note('header-accept-ranges',
                        rs.RANGE_INCORRECT,
                        range="bytes=%s-%s" % (
                            self.range_start, self.range_end
                        ),
                        range_expected = \
                          self.range_target.encode('string_escape'),
                        range_expected_bytes = f_num(len(self.range_target)),
                        range_received = \
                          self.response.payload.encode('string_escape'),
                        range_received_bytes = \
                          f_num(self.response.payload_len)
                    )
            else:
                self.add_note('header-accept-ranges', rs.RANGE_CHANGED)

        # TODO: address 416 directly
        elif self.response.status_code == \
          self.base.response.status_code:
            self.base.partial_support = False
            self.add_note('header-accept-ranges', rs.RANGE_FULL)
        else:
            self.add_note('header-accept-ranges', 
                rs.RANGE_STATUS,
                range_status=self.response.status_code,
                enc_range_status=self.response.status_code or \
                  '(unknown)'
            )
########NEW FILE########
__FILENAME__ = fetch
#!/usr/bin/env python

"""
The Resource Expert Droid Fetcher.

RedFetcher fetches a single URI and analyses that response for common
problems and other interesting characteristics. It only makes one request,
based upon the provided headers.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""

import hashlib
import os
from os import path
from robotparser import RobotFileParser
from urlparse import urlsplit

import thor
import thor.http.error as httperr

from redbot import __version__
from redbot.cache_file import CacheFile
import redbot.speak as rs
from redbot.state import RedState
from redbot.message import HttpRequest, HttpResponse
from redbot.message.status import StatusChecker
from redbot.message.cache import checkCaching


UA_STRING = u"RED/%s (http://redbot.org/)" % __version__

class RedHttpClient(thor.http.HttpClient):
    "Thor HttpClient for RedFetcher"
    connect_timeout = 10
    read_timeout = 15


class RedFetcher(RedState):
    """
    Abstract class for a fetcher.

    Fetches the given URI (with the provided method, headers and body) and
    calls:
      - status_cb as it progresses, and
      - every function in the body_procs list with each chunk of the body, and
      - done_cb when all tasks are done.
    If provided, type indicates the type of the request, and is used to
    help set notes and status_cb appropriately.

    The done() method is called when the response is done, NOT when all
    tasks are done. It can add tasks by calling add_task().

    """
    client = RedHttpClient()
    robot_files = {} # cache of robots.txt
    robot_cache_dir = None
    robot_lookups = {}

    def __init__(self, iri, method="GET", req_hdrs=None, req_body=None,
                 status_cb=None, body_procs=None, name=None):
        RedState.__init__(self, name)
        self.request = HttpRequest(self.notes, self.name)
        self.request.method = method
        self.request.set_iri(iri)
        self.request.headers = req_hdrs or []
        self.request.payload = req_body
        self.response = HttpResponse(self.notes, self.name)
        self.response.is_head_response = (method == "HEAD")
        self.response.base_uri = self.request.uri
        self.response.set_decoded_procs(body_procs or [])
        self.exchange = None
        self.status_cb = status_cb
        self.done_cb = None # really should be "all tasks done"
        self.outstanding_tasks = 0
        self.follow_robots_txt = True # Should we pay attention to robots file?
        self._st = [] # FIXME: this is temporary, for debugging thor

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['exchange']
        del state['status_cb']
        del state['done_cb']
        return state

    def add_task(self, task, *args):
        "Remeber that we've started a task."
        self.outstanding_tasks += 1
        self._st.append('add_task(%s)' % str(task))
        task(*args, done_cb=self.finish_task)

    def finish_task(self):
        "Note that we've finished a task, and see if we're done."
        self.outstanding_tasks -= 1
        self._st.append('finish_task()')
        assert self.outstanding_tasks >= 0, self._st
        if self.outstanding_tasks == 0:
            if self.done_cb:
                self.done_cb()
                self.done_cb = None
            # clean up potentially cyclic references
            self.status_cb = None

    def done(self):
        "Callback for when the response is complete and analysed."
        raise NotImplementedError

    def preflight(self):
        """
        Callback to check to see if we should bother running. Return True
        if so; False if not.
        """
        return True

    def fetch_robots_txt(self, url, cb, network=True):
        """
        Fetch the robots.txt URL and then feed the response to cb.
        If the status code is not 200, send a blank doc back.

        If network is False, we won't use the network, will return the result
        immediately if cached, and will assume it's OK if we don't have a
        cached file.
        """

        origin = url_to_origin(self.request.uri)
        if origin == None:
            cb("")
            return ""
        origin_hash = hashlib.sha1(origin).hexdigest()

        if self.robot_files.has_key(origin):
            # FIXME: freshness lifetime
            cb(self.robot_files[origin])
            return self.robot_files[origin]

        if self.robot_cache_dir:
            robot_fd = CacheFile(path.join(self.robot_cache_dir, origin_hash))
            cached_robots_txt = robot_fd.read()
            if cached_robots_txt != None:
                cb(cached_robots_txt)
                return cached_robots_txt

        if not network:
            cb("")
            return ""

        if self.robot_lookups.has_key(origin):
            self.robot_lookups[origin].append(cb)
        else:
            self.robot_lookups[origin] = [cb]
            exchange = self.client.exchange()
            @thor.on(exchange)
            def response_start(status, phrase, headers):
                exchange.status = status

            exchange.res_body = ""
            @thor.on(exchange)
            def response_body(chunk):
                exchange.res_body += chunk

            @thor.on(exchange)
            def response_done(trailers):
                if not exchange.status.startswith("2"):
                    robots_txt = ""
                else:
                    robots_txt = exchange.res_body

                self.robot_files[origin] = robots_txt
                if self.robot_cache_dir:
                    robot_fd = CacheFile(
                        path.join(self.robot_cache_dir, origin_hash))
                    robot_fd.write(robots_txt, 60*30)

                for _cb in self.robot_lookups[origin]:
                    _cb(robots_txt)
                del self.robot_lookups[origin]

            p_url = urlsplit(url)
            robots_url = "%s://%s/robots.txt" % (p_url.scheme, p_url.netloc)
            exchange.request_start("GET", robots_url,
                [('User-Agent', UA_STRING)])
            exchange.request_done([])

    def run(self, done_cb=None):
        """
        Make an asynchronous HTTP request to uri, calling status_cb as it's
        updated and done_cb when it's done. Reason is used to explain what the
        request is in the status callback.
        """
        self.outstanding_tasks += 1
        self._st.append('run(%s)' % str(done_cb))
        self.done_cb = done_cb
        if not self.preflight() or self.request.uri == None:
            # generally a good sign that we're not going much further.
            self.finish_task()
            return

        if self.follow_robots_txt:
            self.fetch_robots_txt(self.request.uri, self.run_continue)
        else:
            self.run_continue("")

    def run_continue(self, robots_txt):
        """
        Continue after getting the robots file.
        TODO: refactor callback style into events.
        """
        if robots_txt == "": # empty or non-200
            pass
        else:
            checker = RobotFileParser()
            checker.parse(robots_txt.splitlines())
            if not checker.can_fetch(UA_STRING, self.request.uri):
                self.response.http_error = RobotsTxtError()
                self.finish_task()
                return # TODO: show error?

        if 'user-agent' not in [i[0].lower() for i in self.request.headers]:
            self.request.headers.append(
                (u"User-Agent", UA_STRING))
        self.exchange = self.client.exchange()
        self.exchange.on('response_start', self._response_start)
        self.exchange.on('response_body', self._response_body)
        self.exchange.on('response_done', self._response_done)
        self.exchange.on('error', self._response_error)
        if self.status_cb and self.name:
            self.status_cb("fetching %s (%s)" % (
                self.request.uri, self.name
            ))
        req_hdrs = [
            (k.encode('ascii', 'replace'), v.encode('latin-1', 'replace')) \
            for (k, v) in self.request.headers
        ]
        self.exchange.request_start(
            self.request.method, self.request.uri, req_hdrs
        )
        self.request.start_time = thor.time()
        if self.request.payload != None:
            self.exchange.request_body(self.request.payload)
        self.exchange.request_done([])

    def _response_start(self, status, phrase, res_headers):
        "Process the response start-line and headers."
        self._st.append('_response_start(%s, %s)' % (status, phrase))
        self.response.start_time = thor.time()
        self.response.version = self.exchange.res_version
        self.response.status_code = status.decode('iso-8859-1', 'replace')
        self.response.status_phrase = phrase.decode('iso-8859-1', 'replace')
        self.response.set_headers(res_headers)
        StatusChecker(self.response, self.request)
        checkCaching(self.response, self.request)

    def _response_body(self, chunk):
        "Process a chunk of the response body."
        self.response.feed_body(chunk)

    def _response_done(self, trailers):
        "Finish analysing the response, handling any parse errors."
        self._st.append('_response_done()')
        self.response.complete_time = thor.time()
        self.response.transfer_length = self.exchange.input_transfer_length
        self.response.header_length = self.exchange.input_header_length
        self.response.body_done(True, trailers)
        if self.status_cb and self.name:
            self.status_cb("fetched %s (%s)" % (
                self.request.uri, self.name
            ))
        self.done()
        self.finish_task()

    def _response_error(self, error):
        "Handle an error encountered while fetching the response."
        self._st.append('_response_error(%s)' % (str(error)))
        self.response.complete_time = thor.time()
        self.response.http_error = error
        if isinstance(error, httperr.BodyForbiddenError):
            self.add_note('header-none', rs.BODY_NOT_ALLOWED)
#        elif isinstance(error, httperr.ExtraDataErr):
#            res.payload_len += len(err.get('detail', ''))
        elif isinstance(error, httperr.ChunkError):
            err_msg = error.detail[:20] or ""
            self.add_note('header-transfer-encoding', rs.BAD_CHUNK,
                chunk_sample=err_msg.encode('string_escape')
            )
        self.done()
        self.finish_task()


def url_to_origin(url):
    "Convert an URL to an RFC6454 Origin."
    default_port = {
    	'http': 80,
    	'https': 443
    }
    try:
        p_url = urlsplit(url)
        origin = "%s://%s:%s" % (p_url.scheme.lower(),
                                 p_url.hostname.lower(),
                                 p_url.port or default_port.get(p_url.scheme, 0)
        )
    except AttributeError:
        origin = None
    return origin


class RobotsTxtError(httperr.HttpError):
    desc = "Forbidden by robots.txt"
    server_status = ("502", "Gateway Error")


if "__main__" == __name__:
    import sys
    def status_p(msg):
        "Print status"
        print msg
    class TestFetcher(RedFetcher):
        "Test a fetcher."
        def done(self):
            print self.notes
    T = TestFetcher(
         sys.argv[1],
         req_hdrs=[(u'Accept-Encoding', u'gzip')],
         status_cb=status_p,
         name='test'
    )
    T.run()
    thor.run()

########NEW FILE########
__FILENAME__ = speak
"""
A collection of notes that the RED can emit.

PLEASE NOTE: the summary field is automatically HTML escaped in webui.py, so
it can contain arbitrary text (as long as it's unicode). However, the longer
text IS NOT ESCAPED, and therefore all variables to be interpolated into
it (but not the short version) need to be escaped.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2009-2013 Mark Nottingham

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
"""

from cgi import escape as e_html

class _Classifications:
    "Note classifications."
    GENERAL = u"General"
    SECURITY = u"Security"
    CONNEG = u"Content Negotiation"
    CACHING = u"Caching"
    VALIDATION = u"Validation"
    CONNECTION = u"Connection"
    RANGE = u"Partial Content"
c = _Classifications()

class _Levels:
    "Note levels."
    GOOD = u'good'
    WARN = u'warning'
    BAD = u'bad'
    INFO = u'info'
l = _Levels()

class Note:
    """
    A note about an HTTP resource, representation, or other component
    related to the URI under test.
    """
    category = None
    level = None
    summary = {}
    text = {}
    def __init__(self, subject, subrequest=None, vrs=None):
        self.subject = subject
        self.subrequest = subrequest
        self.vars = vrs or {}

    def __eq__(self, other):
        if self.__class__ == other.__class__ \
           and self.vars == other.vars \
           and self.subject == other.subject:
            return True
        else:
            return False

    def show_summary(self, lang):
        """
        Output a textual summary of the message as a Unicode string.
        
        Note that if it is displayed in an environment that needs 
        encoding (e.g., HTML), that is *NOT* done.
        """
        return self.summary[lang] % self.vars
        
    def show_text(self, lang):
        """
        Show the HTML text for the message as a Unicode string.
        
        The resulting string is already HTML-encoded.
        """
        return self.text[lang] % dict(
            [(k, e_html(unicode(v))) for k, v in self.vars.items()]
        )


response = {
    'this': {'en': 'This response'},
    'conneg': {'en': 'The uncompressed response'},
    'LM validation': {'en': 'The 304 response'},
    'ETag validation': {'en': 'The 304 response'},
    'range': {'en': 'The partial response'},
}

class URI_TOO_LONG(Note):
    category = c.GENERAL
    level = l.WARN
    summary = {
    'en': u"The URI is very long (%(uri_len)s characters)."
    }
    text = {
    'en': u"""Long URIs aren't supported by some implementations, including
    proxies. A reasonable upper size limit is 8192 characters."""
    }

class URI_BAD_SYNTAX(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
    'en': u"The URI's syntax isn't valid."
    }
    text = {
    'en': u"""This isn't a valid URI. Look for illegal characters and other
    problems; see <a href='http://www.ietf.org/rfc/rfc3986.txt'>RFC3986</a>
    for more information."""
    }

class REQUEST_HDR_IN_RESPONSE(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
     'en': u'"%(field_name)s" is a request header.'
    }
    text = {
    'en': u"""%(field_name)s is only defined to have meaning in requests;
    in responses, it doesn't have any meaning, so RED has ignored it."""
    }

class RESPONSE_HDR_IN_REQUEST(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
     'en': u'"%(field_name)s" is a request header.'
    }
    text = {
    'en': u"""%(field_name)s is only defined to have meaning in responses;
    in requests, it doesn't have any meaning, so RED has ignored it."""
    }

class FIELD_NAME_BAD_SYNTAX(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
     'en': u'"%(field_name)s" is not a valid header field-name.'
    }
    text = {
    'en': u"""Header names are limited to the TOKEN production in HTTP; i.e., 
    they can't contain parenthesis, angle brackes (&lt;&gt;), ampersands (@), 
    commas, semicolons, colons, backslashes (\\), forward slashes (/), quotes, 
    square brackets ([]), question marks, equals signs (=), curly brackets 
    ({}) spaces or tabs."""
    }

class HEADER_BLOCK_TOO_LARGE(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
    'en': u"%(response)s's headers are very large (%(header_block_size)s)."
    }
    text = {
    'en': u"""Some implementations have limits on the total size of headers
    that they'll accept. For example, Squid's default configuration limits
    header blocks to 20k."""
    }

class HEADER_TOO_LARGE(Note):
    category = c.GENERAL
    level = l.WARN
    summary = {
    'en': u"The %(header_name)s header is very large (%(header_size)s)."
    }
    text = {
    'en': u"""Some implementations limit the size of any single header
    line."""
    }

class HEADER_NAME_ENCODING(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
     'en': u"The %(header_name)s header's name contains non-ASCII characters."
    }
    text = {
     'en': u"""HTTP header field-names can only contain ASCII characters. RED
     has detected (and possibly removed) non-ASCII characters in this header
     name."""
    }

class HEADER_VALUE_ENCODING(Note):
    category = c.GENERAL
    level = l.WARN
    summary = {
     'en': u"The %(header_name)s header's value contains non-ASCII characters."
    }
    text = {
     'en': u"""HTTP headers use the ISO-8859-1 character set, but in most
     cases are pure ASCII (a subset of this encoding).<p>
     This header has non-ASCII characters, which RED has interpreted as
     being encoded in ISO-8859-1. If another encoding is used (e.g., UTF-8),
     the results may be unpredictable."""
    }

class HEADER_DEPRECATED(Note):
    category = c.GENERAL
    level = l.WARN
    summary = {
    'en': u"The %(header_name)s header is deprecated."
    }
    text = {
    'en': u"""This header field is no longer recommended for use, because of
    interoperability problems and/or lack of use. See
    <a href="%(ref)s">its documentation</a> for more information."""
    }

class SINGLE_HEADER_REPEAT(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
    'en': u"Only one %(field_name)s header is allowed in a response."
    }
    text = {
    'en': u"""This header is designed to only occur once in a message. When it
    occurs more than once, a receiver needs to choose the one to use, which
    can lead to interoperability problems, since different implementations may
    make different choices.<p>
    For the purposes of its tests, RED uses the last instance of the header
    that is present; other implementations may behave differently."""
    }

class BODY_NOT_ALLOWED(Note):
    category = c.CONNECTION
    level = l.BAD
    summary = {
     'en': u"%(response)s is not allowed to have a body."
    }
    text = {
     'en': u"""HTTP defines a few special situations where a response does not
     allow a body. This includes 101, 204 and 304 responses, as well as
     responses to the <code>HEAD</code> method.<p>
     %(response)s had a body, despite it being disallowed. Clients receiving
     it may treat the body as the next response in the connection, leading to
     interoperability and security issues."""
    }

class BAD_SYNTAX(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
    'en': u"The %(field_name)s header's syntax isn't valid."
    }
    text = {
    'en': u"""The value for this header doesn't conform to its specified 
    syntax; see <a href="%(ref_uri)s">its definition</a> for more information.
    """
    }

# Specific headers

class BAD_CC_SYNTAX(Note):
    category = c.CACHING
    level = l.BAD
    summary = {
     'en': u"The %(bad_cc_attr)s Cache-Control directive's syntax is \
incorrect."
    }
    text = {
     'en': u"This value must be an integer."
    }

class AGE_NOT_INT(Note):
    category = c.CACHING
    level = l.BAD
    summary = {
    'en': u"The Age header's value should be an integer."
    }
    text = {
    'en': u"""The <code>Age</code> header indicates the age of the response;
    i.e., how long it has been cached since it was generated. The value given 
    was not an integer, so it is not a valid age."""
    }

class AGE_NEGATIVE(Note):
    category = c.CACHING
    level = l.BAD
    summary = {
    'en': u"The Age headers' value must be a positive integer."
    }
    text = {
    'en': u"""The <code>Age</code> header indicates the age of the response;
    i.e., how long it has been cached since it was generated. The value given 
    was negative, so it is not a valid age."""
    }

class BAD_CHUNK(Note):
    category = c.CONNECTION
    level = l.BAD
    summary = {
     'en': u"%(response)s had chunked encoding errors."
    }
    text = {
     'en': u"""The response indicates it uses HTTP chunked encoding, but there
     was a problem decoding the chunking.<p>
     A valid chunk looks something like this:<p>
     <code>[chunk-size in hex]\\r\\n[chunk-data]\\r\\n</code><p>
     However, the chunk sent started like this:<p>
     <code>%(chunk_sample)s</code><p>
     This is a serious problem, because HTTP uses chunking to delimit one
     response from the next one; incorrect chunking can lead to 
     interoperability and security problems.<p>
     This issue is often caused by sending an integer chunk size instead of 
     one in hex, or by sending <code>Transfer-Encoding: chunked</code> without
     actually chunking the response body."""
    }

class BAD_GZIP(Note):
    category = c.CONNEG
    level = l.BAD
    summary = {
    'en': u"%(response)s was compressed using GZip, but the header wasn't \
valid."
    }
    text = {
    'en': u"""GZip-compressed responses have a header that contains metadata.
    %(response)s's header wasn't valid; the error encountered was
    "<code>%(gzip_error)s</code>"."""
    }

class BAD_ZLIB(Note):
    category = c.CONNEG
    level = l.BAD
    summary = {
    'en': u"%(response)s was compressed using GZip, but the data was corrupt."
    }
    text = {
    'en': u"""GZip-compressed responses use zlib compression to reduce the 
    number of bytes transferred on the wire. However, this response could not 
    be decompressed; the error encountered was 
    "<code>%(zlib_error)s</code>".<p>
    %(ok_zlib_len)s bytes were decompressed successfully before this; the 
    erroneous chunk starts with "<code>%(chunk_sample)s</code>"."""
    }

class ENCODING_UNWANTED(Note):
    category = c.CONNEG
    level = l.WARN
    summary = {
     'en': u"%(response)s contained unwanted content-codings."
    }
    text = {
     'en': u"""%(response)s's <code>Content-Encoding</code> header indicates 
     it has content-codings applied (<code>%(unwanted_codings)s</code>) that
     RED didn't ask for.<p>
     Normally, clients ask for the encodings they want in the
     <code>Accept-Encoding</code> request header. Using encodings that the
     client doesn't explicitly request can lead to interoperability 
     problems."""
    }

class TRANSFER_CODING_IDENTITY(Note):
    category = c.CONNECTION
    level = l.INFO
    summary = {
    'en': u"The identity transfer-coding isn't necessary."
    }
    text = {
    'en': u"""HTTP defines <em>transfer-codings</em> as a hop-by-hop encoding
    of the message body. The <code>identity</code> tranfer-coding was defined
    as the absence of encoding; it doesn't do anything, so it's necessary.<p>
    You can remove this token to save a few bytes."""
    }

class TRANSFER_CODING_UNWANTED(Note):
    category = c.CONNECTION
    level = l.BAD
    summary = {
     'en': u"%(response)s has unsupported transfer-coding."
    }
    text = {
     'en': u"""%(response)s's <code>Transfer-Encoding</code> header indicates 
     it has transfer-codings applied, but RED didn't ask for 
     it (or them) to be.<p>
     They are: <code>%(unwanted_codings)s</code><p>
     Normally, clients ask for the encodings they want in the
     <code>TE</code> request header. Using codings that the
     client doesn't explicitly request can lead to interoperability 
     problems."""
    }

class TRANSFER_CODING_PARAM(Note):
    category = c.CONNECTION
    level = l.WARN
    summary = {
     'en': u"%(response)s had parameters on its transfer-codings."
    }
    text = {
     'en': u"""HTTP allows transfer-codings in the
     <code>Transfer-Encoding</code> header to have optional parameters,
     but it doesn't define what they mean.<p>
     %(response)s has encodings with such paramters;
     although they're technically allowed, they may cause interoperability
     problems. They should be removed."""
    }

class BAD_DATE_SYNTAX(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
    'en': u"The %(field_name)s header's value isn't a valid date."
    }
    text = {
    'en': u"""HTTP dates have very specific syntax, and sending an invalid 
    date can cause a number of problems, especially around caching. Common 
    problems include sending "1 May" instead of "01 May" (the month is a 
    fixed-width field), and sending a date in a timezone other than GMT. See
    <a href="http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.3">the
    HTTP specification</a> for more information."""
    }

class LM_FUTURE(Note):
    category = c.CACHING
    level = l.BAD
    summary = {
    'en': u"The Last-Modified time is in the future."
    }
    text = {
    'en': u"""The <code>Last-Modified</code> header indicates the last point 
    in time that the resource has changed. %(response)s's
    <code>Last-Modified</code> time is in the future, which doesn't have any
    defined meaning in HTTP."""
    }

class LM_PRESENT(Note):
    category = c.CACHING
    level = l.INFO
    summary = {
    'en': u"The resource last changed %(last_modified_string)s."
    }
    text = {
    'en': u"""The <code>Last-Modified</code> header indicates the last point 
    in time that the resource has changed. It is used in HTTP for validating 
    cached responses, and for calculating heuristic freshness in caches.<p>
    This resource last changed %(last_modified_string)s."""
    }

class CONTENT_TRANSFER_ENCODING(Note):
    category = c.GENERAL
    level = l.WARN
    summary = {
    'en': u"The Content-Transfer-Encoding header isn't necessary in HTTP."
    }
    text = {
    'en': u"""<code>Content-Transfer-Encoding</code> is a MIME header, not
    a HTTP header; it's only used when HTTP messages are moved over
    MIME-based protocols (e.g., SMTP), which is uncommon.<p>
    You can safely remove this header.
    """
    }

class MIME_VERSION(Note):
    category = c.GENERAL
    level = l.WARN
    summary = {
    'en': u"The MIME-Version header isn't necessary in HTTP."
    }
    text = {
    'en': u"""<code>MIME_Version</code> is a MIME header, not a HTTP header; 
    it's only used when HTTP messages are moved over MIME-based protocols
    (e.g., SMTP), which is uncommon.<p>
    You can safely remove this header.
    """
    }

class PRAGMA_NO_CACHE(Note):
    category = c.CACHING
    level = l.WARN
    summary = {
    'en': u"Pragma: no-cache is a request directive, not a response \
directive."
    }
    text = {
    'en': u"""<code>Pragma</code> is a very old request header that is 
    sometimes used as a response header, even though this is not specified 
    behaviour. <code>Cache-Control: no-cache</code> is more appropriate."""
    }

class PRAGMA_OTHER(Note):
    category = c.GENERAL
    level = l.WARN
    summary = {
    'en': u"""The Pragma header is being used in an undefined way."""
    }
    text = {
    'en': u"""HTTP only defines <code>Pragma: no-cache</code>; other uses of
    this header are deprecated."""
    }

class VIA_PRESENT(Note):
    category = c.GENERAL
    level = l.INFO
    summary = {
    'en': u"One or more intermediaries are present."
    }
    text = {
    'en': u"""The <code>Via</code> header indicates that one or more
    intermediaries are present between RED and the origin server for the
    resource.<p>
    This may indicate that a proxy is in between RED and the server, or that
    the server uses a "reverse proxy" or CDN in front of it.<p>
    <p>
    There field has three space-separated components; first, the HTTP version
    of the message that the intermediary received, then the identity of the
    intermediary (usually but not always its hostname), and then optionally a
    product identifier or comment (usually used to identify the software being
    used)."""
    }

class LOCATION_UNDEFINED(Note):
    category = c.GENERAL
    level = l.WARN
    summary = {
     'en': u"%(response)s doesn't define any meaning for the Location header."
    }
    text = {
     'en': u"""The <code>Location</code> header is used for specific purposes
     in HTTP; mostly to indicate the URI of another resource (e.g., in
     redirection, or when a new resource is created).<p>
     In other status codes (such as this one) it doesn't have a defined 
     meaning, so any use of it won't be interoperable.<p>
     Sometimes <code>Location</code> is confused with 
     <code>Content-Location</code>, which indicates a URI for the payload 
     of the message that it appears in."""
    }

class LOCATION_NOT_ABSOLUTE(Note):
    category = c.GENERAL
    level = l.INFO
    summary = {
     'en': u"The Location header contains a relative URI."
    }
    text = {
     'en': u"""<code>Location</code> was originally specified to contain 
     an absolute, not relative, URI.<p>
     It is in the process of being updated, and most clients will work 
     around this.</p>
     The correct absolute URI is (probably):<br>
     <code>%(full_uri)s</code>"""
    }

class CONTENT_TYPE_OPTIONS(Note):
    category = c.SECURITY
    level = l.INFO
    summary = {
     'en': u"%(response)s instructs Internet Explorer not to 'sniff' its \
media type."
    }
    text = {
     'en': u"""Many Web browers "sniff" the media type of responses to figure
     out whether they're HTML, RSS or another format, no matter what the
     <code>Content-Type</code> header says.<p>
     This header instructs Microsoft's Internet Explorer not to do this, but
     to always respect the Content-Type header. It probably won't have any
     effect in other clients.<p>
     See <a href="http://bit.ly/t1UHW2">this blog entry</a>
     for more information about this header."""
    }

class CONTENT_TYPE_OPTIONS_UNKNOWN(Note):
    category = c.SECURITY
    level = l.WARN
    summary = {
     'en': u"%(response)s contains an X-Content-Type-Options header with an \
unknown value."
    }
    text = {
     'en': u"""Only one value is currently defined for this header,
     <code>nosniff</code>. Using other values here won't necessarily cause
     problems, but they probably won't have any effect either.<p>
     See <a href="http://bit.ly/t1UHW2">this blog entry</a> for more
     information about this header."""
    }

class DOWNLOAD_OPTIONS(Note):
    category = c.SECURITY
    level = l.INFO
    summary = {
     'en': u"%(response)s can't be directly opened directly by Internet \
Explorer when downloaded."
    }
    text = {
     'en': u"""When the <code>X-Download-Options</code> header is present
     with the value <code>noopen</code>, Internet Explorer users are prevented
     from directly opening a file download; instead, they must first save the
     file locally. When the locally saved file is later opened, it no longer
     executes in the security context of your site, helping to prevent script
     injection.<p>
     This header probably won't have any effect in other clients.<p>
     See <a href="http://bit.ly/sfuxWE">this blog article</a> for more
     details."""
    }

class DOWNLOAD_OPTIONS_UNKNOWN(Note):
    category = c.SECURITY
    level = l.WARN
    summary = {
     'en': u"%(response)s contains an X-Download-Options header with an \
unknown value."
    }
    text = {
     'en': u"""Only one value is currently defined for this header,
     <code>noopen</code>. Using other values here won't necessarily cause
     problems, but they probably won't have any effect either.<p>
     See <a href="http://bit.ly/sfuxWE">this blog article</a> for more
     details."""
    }

class FRAME_OPTIONS_DENY(Note):
    category = c.SECURITY
    level = l.INFO
    summary = {
     'en': u"%(response)s prevents some browsers from rendering it if it \
will be contained within a frame."
    }
    text = {
     'en': u"""The <code>X-Frame-Options</code> response header controls how
     IE8 handles HTML frames; the <code>DENY</code> value prevents this
     content from being rendered within a frame, which defends against certain
     types of attacks.<p>
     Currently this is supported by IE8 and Safari 4.<p>
     See <a href="http://bit.ly/v5Bh5Q">this blog entry</a> for more
     information.
     """
    }

class FRAME_OPTIONS_SAMEORIGIN(Note):
    category = c.SECURITY
    level = l.INFO
    summary = {
     'en': u"%(response)s prevents some browsers from rendering it if it \
will be contained within a frame on another site."
    }
    text = {
     'en': u"""The <code>X-Frame-Options</code> response header controls how
     IE8 handles HTML frames; the <code>DENY</code> value prevents this
     content from being rendered within a frame on another site, which defends
     against certain types of attacks.<p>
     Currently this is supported by IE8 and Safari 4.<p>
     See <a href="http://bit.ly/v5Bh5Q">this blog entry</a> for more
     information.
     """
    }

class FRAME_OPTIONS_UNKNOWN(Note):
    category = c.SECURITY
    level = l.WARN
    summary = {
     'en': u"%(response)s contains an X-Frame-Options header with an unknown \
value."
    }
    text = {
     'en': u"""Only two values are currently defined for this header,
     <code>DENY</code> and <code>SAMEORIGIN</code>. Using other values here
     won't necessarily cause problems, but they probably won't have any effect
     either.<p>
     See <a href="http://bit.ly/v5Bh5Q">this blog entry</a> for more
     information.
     """
    }

class SMART_TAG_NO_WORK(Note):
    category = c.GENERAL
    level = l.WARN
    summary = {
     'en': u"The %(field_name)s header doesn't have any effect on smart tags."
    }
    text = {
     'en': u"""This header doesn't have any effect on Microsoft Smart Tags,
     except in certain beta versions of IE6. To turn them off, you'll need
     to make changes in the HTML content it"""
    }

class UA_COMPATIBLE(Note):
    category = c.GENERAL
    level = l.INFO
    summary = {
     'en': u"%(response)s explicitly sets a rendering mode for Internet \
Explorer 8."
    }
    text = {
     'en': u"""Internet Explorer 8 allows responses to explicitly set the
     rendering mode used for a given page (known a the "compatibility
     mode").<p>
     See 
     <a href="http://msdn.microsoft.com/en-us/library/cc288325(VS.85).aspx">
     Microsoft's documentation</a> for more information."""
    }

class UA_COMPATIBLE_REPEAT(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
     'en': u"%(response)s has multiple X-UA-Compatible directives targeted \
at the same UA."
    }
    text = {
     'en': u"""Internet Explorer 8 allows responses to explicitly set the
     rendering mode used for a page.<p>
     This response has more than one such directive targetted at one browser;
     this may cause unpredictable results.<p>
     See 
     <a href="http://msdn.microsoft.com/en-us/library/cc288325(VS.85).aspx">
     this blog entry</a> for more information."""
    }

class XSS_PROTECTION_ON(Note):
    category = c.SECURITY
    level = l.INFO
    summary = {
     'en': u"%(response)s enables XSS filtering in IE8+."
    }
    text = {
     'en': u"""Recent versions of Internet Explorer have built-in Cross-Site
     Scripting (XSS) attack protection; they try to automatically filter
     requests that fit a particular profile.<p>
     %(response)s has explicitly enabled this protection. If IE detects a
     Cross-site scripting attack, it will "sanitise" the page to prevent
     the attack. In other words, the page will still render.<p>
     This header probably won't have any effect on other clients.<p>
     See <a href="http://bit.ly/tJbICH">this blog entry</a> for more 
     information.
     """
    }

class XSS_PROTECTION_OFF(Note):
    category = c.SECURITY
    level = l.INFO
    summary = {
     'en': u"%(response)s disables XSS filtering in IE8+."
    }
    text = {
     'en': u"""Recent versions of Internet Explorer have built-in Cross-Site
     Scripting (XSS) attack protection; they try to automatically filter
     requests that fit a particular profile.<p>
     %(response)s has explicitly disabled this protection. In some scenarios,
     this is useful to do, if the protection interferes with the
     application.<p>
     This header probably won't have any effect on other clients.<p>
     See <a href="http://bit.ly/tJbICH">this blog entry</a> for more 
     information.
     """
    }

class XSS_PROTECTION_BLOCK(Note):
    category = c.SECURITY
    level = l.INFO
    summary = {
     'en': u"%(response)s blocks XSS attacks in IE8+."
    }
    text = {
     'en': u"""Recent versions of Internet Explorer have built-in Cross-Site
     Scripting (XSS) attack protection; they try to automatically filter
     requests that fit a particular profile.<p>
     Usually, IE will rewrite the attacking HTML, so that the attack is
     neutralised, but the content can still be seen. %(response)s instructs IE
     to not show such pages at all, but rather to display an error.<p>
     This header probably won't have any effect on other clients.<p>
     See <a href="http://bit.ly/tJbICH">this blog entry</a> for more 
     information.
     """
    }


### Ranges

class RANGE_SUBREQ_PROBLEM(Note):
    category = c.RANGE
    level = l.BAD
    summary = {
    'en': u"There was a problem checking for Partial Content support."
    }
    text = {
    'en': u"""When RED tried to check the resource for partial content
    support, there was a problem:<p>
    <code>%(problem)s</code><p>
    Trying again might fix it."""
    }

class UNKNOWN_RANGE(Note):
    category = c.RANGE
    level = l.WARN
    summary = {
     'en': u"%(response)s advertises support for non-standard range-units."
    }
    text = {
     'en': u"""The <code>Accept-Ranges</code> response header tells clients
     what <code>range-unit</code>s a resource is willing to process in future
     requests. HTTP only defines two: <code>bytes</code> and
     <code>none</code>.
     <p>
     Clients who don't know about the non-standard range-unit will not be
     able to use it."""
    }

class RANGE_CORRECT(Note):
    category = c.RANGE
    level = l.GOOD
    summary = {
    'en': u"A ranged request returned the correct partial content."
    }
    text = {
    'en': u"""This resource advertises support for ranged requests with
    <code>Accept-Ranges</code>; that is, it allows clients to specify that
    only part of it should be sent. RED has tested this by requesting part of
    this response, which was returned correctly."""
    }

class RANGE_INCORRECT(Note):
    category = c.RANGE
    level = l.BAD
    summary = {
    'en': u'A ranged request returned partial content, but it was incorrect.'
    }
    text = {
    'en': u"""This resource advertises support for ranged requests with
    <code>Accept-Ranges</code>; that is, it allows clients to specify that
    only part of the response should be sent. RED has tested this by
    requesting part of this response, but the partial response doesn't
    correspond with the full response retrieved at the same time. This could
    indicate that the range implementation isn't working properly.
    <p>RED sent<br/>
    <code>Range: %(range)s</code>
    <p>RED expected %(range_expected_bytes)s bytes:<br/>
    <code>%(range_expected).100s</code>
    <p>RED received %(range_received_bytes)s bytes:<br/>
    <code>%(range_received).100s</code>
    <p><em>(showing samples of up to 100 characters)</em></p>"""
    }

class RANGE_CHANGED(Note):
    category = c.RANGE
    level = l.WARN
    summary = {
    'en' : u"A ranged request returned another representation."
    }
    text = {
    'en' : u"""A new representation was retrieved when checking support of
    ranged request. This is not an error, it just indicates that RED
    cannot draw any conclusion at this time."""
    }

class RANGE_FULL(Note):
    category = c.RANGE
    level = l.WARN
    summary = {
    'en': u"A ranged request returned the full rather than partial content."
    }
    text = {
    'en': u"""This resource advertises support for ranged requests with
    <code>Accept-Ranges</code>; that is, it allows clients to specify that
    only part of the response should be sent. RED has tested this by
    requesting part of this response, but the entire response was returned. In
    other words, although the resource advertises support for partial content,
    it doesn't appear to actually do so."""
    }

class RANGE_STATUS(Note):
    category = c.RANGE
    level = l.INFO
    summary = {
    'en': u"A ranged request returned a %(range_status)s status."
    }
    text = {
    'en': u"""This resource advertises support for ranged requests; that is,
    it allows clients to specify that only part of the response should be
    sent. RED has tested this by requesting part of this response, but a
    %(enc_range_status)s response code was returned, which RED was not
    expecting."""
    }

class RANGE_NEG_MISMATCH(Note):
    category = c.RANGE
    level = l.BAD
    summary = {
     'en': u"Partial responses don't have the same support for compression \
that full ones do."
    }
    text = {
     'en': u"""This resource supports ranged requests and also supports
     negotiation for gzip compression, but doesn't support compression for
     both full and partial responses.<p>
     This can cause problems for clients when they compare the partial and
     full responses, since the partial response is expressed as a byte range,
     and compression changes the bytes."""
    }

class MISSING_HDRS_206(Note):
    category = c.VALIDATION
    level = l.WARN
    summary = {
    'en': u"The %(subreq_type)s response is missing required headers."
    }
    text = {
    'en': u"""HTTP requires <code>206 Parital Content</code> responses to 
    have certain headers, if they are also present in a normal (e.g.,
    <code>200 OK</code> response).<p>
    %(response)s is missing the following headers:
    <code>%(missing_hdrs)s</code>.<p>
    This can affect cache operation; because the headers are missing,
    caches might remove them from their stored copies."""
    }

### Body

class CL_CORRECT(Note):
    category = c.GENERAL
    level = l.GOOD
    summary = {
    'en': u'The Content-Length header is correct.'
    }
    text = {
    'en': u"""<code>Content-Length</code> is used by HTTP to delimit messages;
    that is, to mark the end of one message and the beginning of the next. RED
    has checked the length of the body and found the
    <code>Content-Length</code> to be correct."""
    }

class CL_INCORRECT(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
    'en': u"%(response)s's Content-Length header is incorrect."
    }
    text = {
    'en': u"""<code>Content-Length</code> is used by HTTP to delimit messages;
    that is, to mark the end of one message and the beginning of the next. RED
    has checked the length of the body and found the
    <code>Content-Length</code> is not correct. This can cause problems not
    only with connection handling, but also caching, since an incomplete
    response is considered uncacheable.<p>
    The actual body size sent was %(body_length)s bytes."""
    }

class CMD5_CORRECT(Note):
    category = c.GENERAL
    level = l.GOOD
    summary = {
    'en': u'The Content-MD5 header is correct.'
    }
    text = {
    'en': u"""<code>Content-MD5</code> is a hash of the body, and can be used
    to ensure integrity of the response. RED has checked its value and found
    it to be correct."""
    }

class CMD5_INCORRECT(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
    'en': u'The Content-MD5 header is incorrect.'
    }
    text = {
    'en': u"""<code>Content-MD5</code> is a hash of the body, and can be used
    to ensure integrity of the response. RED has checked its value and found
    it to be incorrect; i.e., the given <code>Content-MD5</code> does not
    match what RED thinks it should be (%(calc_md5)s)."""
    }

### Conneg

class CONNEG_SUBREQ_PROBLEM(Note):
    category = c.CONNEG
    level = l.BAD
    summary = {
    'en': u"There was a problem checking for Content Negotiation support."
    }
    text = {
    'en': u"""When RED tried to check the resource for content negotiation
    support, there was a problem:<p>
    <code>%(problem)s</code><p>
    Trying again might fix it."""
    }

class CONNEG_GZIP_GOOD(Note):
    category = c.CONNEG
    level = l.GOOD
    summary = {
    'en': u'Content negotiation for gzip compression is supported, saving \
%(savings)s%%.'
    }
    text = {
    'en': u"""HTTP supports compression of responses by negotiating for
    <code>Content-Encoding</code>. When RED asked for a compressed response,
    the resource provided one, saving %(savings)s%% of its original size
    (from %(orig_size)s to %(gzip_size)s bytes).<p>
    The compressed response's headers are displayed."""
    }

class CONNEG_GZIP_BAD(Note):
    category = c.CONNEG
    level = l.WARN
    summary = {
    'en': u'Content negotiation for gzip compression makes the response \
%(savings)s%% larger.'
    }
    text = {
    'en': u"""HTTP supports compression of responses by negotiating for
    <code>Content-Encoding</code>. When RED asked for a compressed response,
    the resource provided one, but it was %(savings)s%% <em>larger</em> than
    the original response; from %(orig_size)s to %(gzip_size)s bytes.<p>
    Often, this happens when the uncompressed response is very small, or can't
    be compressed more; since gzip compression has some overhead, it can make
    the response larger. Turning compression <strong>off</strong> for this
    resource may slightly improve response times and save bandwidth.<p>
    The compressed response's headers are displayed."""
    }

class CONNEG_NO_GZIP(Note):
    category = c.CONNEG
    level = l.INFO
    summary = {
    'en': u'Content negotiation for gzip compression isn\'t supported.'
    }
    text = {
    'en': u"""HTTP supports compression of responses by negotiating for
    <code>Content-Encoding</code>. When RED asked for a compressed response,
    the resource did not provide one."""
    }

class CONNEG_NO_VARY(Note):
    category = c.CONNEG
    level = l.BAD
    summary = {
    'en': u"%(response)s is negotiated, but doesn't have an appropriate \
Vary header."
    }
    text = {
    'en': u"""All content negotiated responses need to have a
    <code>Vary</code> header that reflects the header(s) used to select the
    response.<p>
    %(response)s was negotiated for <code>gzip</code> content encoding, so the
    <code>Vary</code> header needs to contain <code>Accept-Encoding</code>,
    the request header used."""
    }

class CONNEG_GZIP_WITHOUT_ASKING(Note):
    category = c.CONNEG
    level = l.WARN
    summary = {
    'en': u"A gzip-compressed response was sent when it wasn't asked for."
    }
    text = {
    'en': u"""HTTP supports compression of responses by negotiating for
    <code>Content-Encoding</code>. Even though RED didn't ask for a compressed
    response, the resource provided one anyway.<p>
    It could be that the response is always compressed, but doing so can 
    break clients that aren't expecting a compressed response."""
    }

class VARY_INCONSISTENT(Note):
    category = c.CONNEG
    level = l.BAD
    summary = {
    'en': u"The resource doesn't send Vary consistently."
    }
    text = {
    'en': u"""HTTP requires that the <code>Vary</code> response header be sent
    consistently for all responses if they change based upon different aspects
    of the request.<p>
    This resource has both compressed and uncompressed variants
    available, negotiated by the <code>Accept-Encoding</code> request header,
    but it sends different Vary headers for each;<p>
    <ul>
      <li>"<code>%(conneg_vary)s</code>" when the response is compressed,
       and</li>
      <li>"<code>%(no_conneg_vary)s</code>" when it is not.</li>
    </ul>
    <p>This can cause problems for downstream caches, because they
    cannot consistently determine what the cache key for a given URI is."""
    }

class VARY_STATUS_MISMATCH(Note):
    category = c.CONNEG
    level = l.WARN
    summary = {
     'en': u"The response status is different when content negotiation \
happens."
    }
    text = {
     'en': u"""When content negotiation is used, the response status
     shouldn't change between negotiated and non-negotiated responses.<p>
     When RED send asked for a negotiated response, it got a
     <code>%(neg_status)s</code> status code; when it didn't, it got 
     <code>%(noneg_status)s</code>.<p>
     RED hasn't checked other aspects of content negotiation because of
     this."""
    }
    
class VARY_HEADER_MISMATCH(Note):
    category = c.CONNEG
    level = l.BAD
    summary = {
     'en': u"The %(header)s header is different when content negotiation \
happens."
    }
    text = {
     'en': u"""When content negotiation is used, the %(header)s response
     header shouldn't change between negotiated and non-negotiated
     responses."""
    }

class VARY_BODY_MISMATCH(Note):
    category = c.CONNEG
    level = l.INFO
    summary = {
     'en': u"The response body is different when content negotiation happens."
    }
    text = {
     'en': u"""When content negotiation is used, the response body typically
     shouldn't change between negotiated and non-negotiated
     responses.<p>
     There might be legitimate reasons for this; e.g., because different
     servers handled the two requests. However, RED's output may be skewed as
     a result.<p>"""
    }

class VARY_ETAG_DOESNT_CHANGE(Note):
    category = c.CONNEG
    level = l.BAD
    summary = {
    'en': u"The ETag doesn't change between negotiated representations."
    }
    text = {
    'en': u"""HTTP requires that the <code>ETag</code>s for two different
    responses associated with the same URI be different as well, to help
    caches and other receivers disambiguate them.<p>
    This resource, however, sent the same strong ETag for both its compressed
    and uncompressed versions (negotiated by <code>Accept-Encoding</code>).
    This can cause interoperability problems, especially with caches."""
    }

### Clock

class DATE_CORRECT(Note):
    category = c.GENERAL
    level = l.GOOD
    summary = {
    'en': u"The server's clock is correct."
    }
    text = {
    'en': u"""HTTP's caching model assumes reasonable synchronisation between
    clocks on the server and client; using RED's local clock, the server's
    clock appears to be well-synchronised."""
    }

class DATE_INCORRECT(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
    'en': u"The server's clock is %(clock_skew_string)s."
    }
    text = {
    'en': u"""Using RED's local clock, the server's clock does not appear to 
    be well-synchronised.<p>
    HTTP's caching model assumes reasonable synchronisation between clocks on
    the server and client; clock skew can cause responses that should be
    cacheable to be considered uncacheable (especially if their freshness
    lifetime is short).<p>
    Ask your server administrator to synchronise the clock, e.g., using <a
    href="http://en.wikipedia.org/wiki/Network_Time_Protocol" title="Network
    Time Protocol">NTP</a>.</p>
    Apparent clock skew can also be caused by caching the response without
    adjusting the <code>Age</code> header; e.g., in a reverse proxy or <abbr
    title="Content Delivery Network">CDN</abbr>. See <a
    href="http://www2.research.att.com/~edith/Papers/HTML/usits01/index.html">
    this paper</a> for more information. """
    }

class AGE_PENALTY(Note):
    category = c.GENERAL
    level = l.WARN
    summary = {
     'en': u"It appears that the Date header has been changed by an \
intermediary."
    }
    text = {
     'en': u"""It appears that this response has been cached by a reverse
     proxy or <abbr title="Content Delivery Network">CDN</abbr>, because the
     <code>Age</code> header is present, but the <code>Date</code> header is
     more recent than it indicates.<p>
     Generally, reverse proxies should either omit the <code>Age</code> header
     (if they have another means of determining how fresh the response is), or
     leave the <code>Date</code> header alone (i.e., act as a normal HTTP
     cache).<p>
     See <a href="http://j.mp/S7lPL4">this paper</a> for more
     information."""
    }

class DATE_CLOCKLESS(Note):
    category = c.GENERAL
    level = l.WARN
    summary = {
     'en': u"%(response)s doesn't have a Date header."
    }
    text = {
     'en': u"""Although HTTP allowes a server not to send a <code>Date</code>
     header if it doesn't have a local clock, this can make calculation of the
     response's age inexact."""
    }

class DATE_CLOCKLESS_BAD_HDR(Note):
    category = c.CACHING
    level = l.BAD
    summary = {
     'en': u"Responses without a Date aren't allowed to have Expires or \
Last-Modified values."
    }
    text = {
     'en': u"""Because both the <code>Expires</code> and
     <code>Last-Modified</code> headers are date-based, it's necessary to know
     when the message was generated for them to be useful; otherwise, clock
     drift, transit times between nodes as well as caching could skew their
     application."""
    }

### Caching

class METHOD_UNCACHEABLE(Note):
    category = c.CACHING
    level = l.INFO
    summary = {
     'en': u"Responses to the %(method)s method can't be stored by caches."
    }
    text = {
    'en': u""""""
    }

class CC_MISCAP(Note):
    category = c.CACHING
    level = l.WARN
    summary = {
     'en': u"The %(cc)s Cache-Control directive appears to have incorrect \
capitalisation."
    }
    text = {
     'en': u"""Cache-Control directive names are case-sensitive, and will not
     be recognised by most implementations if the capitalisation is wrong.<p>
     Did you mean to use %(cc_lower)s instead of %(cc)s?"""
    }

class CC_DUP(Note):
    category = c.CACHING
    level = l.WARN
    summary = {
     'en': u"The %(cc)s Cache-Control directive appears more than once."
    }
    text = {
     'en': u"""The %(cc)s Cache-Control directive is only defined to appear
     once; it is used more than once here, so implementations may use
     different instances (e.g., the first, or the last), making their
     behaviour unpredictable."""
    }

class NO_STORE(Note):
    category = c.CACHING
    level = l.INFO
    summary = {
     'en': u"%(response)s can't be stored by a cache."
    }
    text = {
    'en': u"""The <code>Cache-Control: no-store</code> directive indicates
    that this response can't be stored by a cache."""
    }

class PRIVATE_CC(Note):
    category = c.CACHING
    level = l.INFO
    summary = {
     'en': u"%(response)s only allows a private cache to store it."
    }
    text = {
    'en': u"""The <code>Cache-Control: private</code> directive indicates that
    the response can only be stored by caches that are specific to a single
    user; for example, a browser cache. Shared caches, such as those in
    proxies, cannot store it."""
    }

class PRIVATE_AUTH(Note):
    category = c.CACHING
    level = l.INFO
    summary = {
     'en': u"%(response)s only allows a private cache to store it."
    }
    text = {
    'en': u"""Because the request was authenticated and this response doesn't
    contain a <code>Cache-Control: public</code> directive, this response can
    only be stored by caches that are specific to a single user; for example,
    a browser cache. Shared caches, such as those in proxies, cannot store
    it."""
    }

class STOREABLE(Note):
    category = c.CACHING
    level = l.INFO
    summary = {
     'en': u"""%(response)s allows all caches to store it."""
    }
    text = {
     'en': u"""A cache can store this response; it may or may not be able to
     use it to satisfy a particular request."""
    }

class NO_CACHE(Note):
    category = c.CACHING
    level = l.INFO
    summary = {
     'en': u"%(response)s cannot be served from cache without validation."
    }
    text = {
     'en': u"""The <code>Cache-Control: no-cache</code> directive means that
     while caches <strong>can</strong> store this response, they cannot use
     it to satisfy a request unless it has been validated (either with an
     <code>If-None-Match</code> or <code>If-Modified-Since</code> conditional)
     for that request.<p>"""
    }

class NO_CACHE_NO_VALIDATOR(Note):
    category = c.CACHING
    level = l.INFO
    summary = {
     'en': u"%(response)s cannot be served from cache without validation."
    }
    text = {
     'en': u"""The <code>Cache-Control: no-cache</code> directive means that
     while caches <strong>can</strong> store this response, they cannot use
     it to satisfy a request unless it has been validated (either with an
     <code>If-None-Match</code> or <code>If-Modified-Since</code> conditional)
     for that request.<p>
     %(response)s doesn't have a <code>Last-Modified</code> or
     <code>ETag</code> header, so it effectively can't be used by a cache."""
    }

class VARY_ASTERISK(Note):
    category = c.CACHING
    level = l.WARN
    summary = {
    'en': u"Vary: * effectively makes this response uncacheable."
    }
    text = {
    'en': u"""<code>Vary *</code> indicates that responses for this resource
    vary by some aspect that can't (or won't) be described by the server. This
    makes this response effectively uncacheable."""
    }

class VARY_USER_AGENT(Note):
    category = c.CACHING
    level = l.INFO
    summary = {
     'en': u"Vary: User-Agent can cause cache inefficiency."
    }
    text = {
    'en': u"""Sending <code>Vary: User-Agent</code> requires caches to store
    a separate copy of the response for every <code>User-Agent</code> request
    header they see.<p>
    Since there are so many different <code>User-Agent</code>s, this can
    "bloat" caches with many copies of the same thing, or cause them to give
    up on storing these responses at all.<p>
    Consider having different URIs for the various versions of your content 
    instead; this will give finer control over caching without sacrificing
    efficiency."""
    }

class VARY_HOST(Note):
    category = c.CACHING
    level = l.WARN
    summary = {
     'en': u"Vary: Host is not necessary."
    }
    text = {
    'en': u"""Some servers (e.g., <a
    href="http://httpd.apache.org/">Apache</a> with <a
    href="http://httpd.apache.org/docs/2.0/mod/mod_rewrite.html">mod_rewrite</a>)
    will send <code>Host</code> in the <code>Vary</code> header, in the belief
    that since it affects how the server selects what to send back, this is
    necessary.<p>
    This is not the case; HTTP specifies that the URI is the basis of the
    cache key, and the URI incorporates the <code>Host</code> header.<p>
    The presence of <code>Vary: Host</code> may make some caches not store an
    otherwise cacheable response (since some cache implementations will not
    store anything that has a <code>Vary</code> header)."""
    }

class VARY_COMPLEX(Note):
    category = c.CACHING
    level = l.WARN
    summary = {
     'en': u"This resource varies in %(vary_count)s ways."
    }
    text = {
     'en': u"""The <code>Vary</code> mechanism allows a resource to describe
     the dimensions that its responses vary, or change, over; each listed
     header is another dimension.<p>
     Varying by too many dimensions makes using this information
     impractical."""
    }

class PUBLIC(Note):
    category = c.CACHING
    level = l.WARN
    summary = {
     'en': u"Cache-Control: public is rarely necessary."
    }
    text = {
     'en': u"""The <code>Cache-Control: public</code> directive makes a
     response cacheable even when the request had an
     <code>Authorization</code> header (i.e., HTTP authentication was in
     use).<p>
     <p>Therefore, HTTP-authenticated (NOT cookie-authenticated) resources
     <em>may</em> have use for <code>public</code> to improve cacheability, if
     used judiciously.<p> However, other responses <strong>do not need to
     contain <code>public</code></strong>; it does not make the response
     "more cacheable", and only makes the response headers larger."""
    }

class CURRENT_AGE(Note):
    category = c.CACHING
    level = l.INFO
    summary = {
     'en': u"%(response)s has been cached for %(age)s."
    }
    text = {
    'en': u"""The <code>Age</code> header indicates the age of the response;
    i.e., how long it has been cached since it was generated. HTTP takes this
    as well as any apparent clock skew into account in computing how old the
    response already is."""
    }

class FRESHNESS_FRESH(Note):
    category = c.CACHING
    level = l.GOOD
    summary = {
     'en': u"%(response)s is fresh until %(freshness_left)s from now."
    }
    text = {
    'en': u"""A response can be considered fresh when its age (here,
    %(current_age)s) is less than its freshness lifetime (in this case,
    %(freshness_lifetime)s)."""
    }

class FRESHNESS_STALE_CACHE(Note):
    category = c.CACHING
    level = l.WARN
    summary = {
     'en': u"%(response)s has been served stale by a cache."
    }
    text = {
    'en': u"""An HTTP response is stale when its age (here, %(current_age)s)
    is equal to or exceeds its freshness lifetime (in this case,
    %(freshness_lifetime)s).<p>
    HTTP allows caches to use stale responses to satisfy requests only under
    exceptional circumstances; e.g., when they lose contact with the origin
    server. Either that has happened here, or the cache has ignored the
    response's freshness directives."""
    }

class FRESHNESS_STALE_ALREADY(Note):
    category = c.CACHING
    level = l.INFO
    summary = {
     'en': u"%(response)s is already stale."
    }
    text = {
    'en': u"""A cache considers a HTTP response stale when its age (here,
    %(current_age)s) is equal to or exceeds its freshness lifetime (in this
    case, %(freshness_lifetime)s).<p> HTTP allows caches to use stale
    responses to satisfy requests only under exceptional circumstances; e.g.,
    when they lose contact with the origin server."""
    }

class FRESHNESS_HEURISTIC(Note):
    category = c.CACHING
    level = l.WARN
    summary = {
     'en': u"%(response)s allows a cache to assign its own freshness \
lifetime."
    }
    text = {
     'en': u"""When responses with certain status codes don't have explicit
     freshness information (like a <code> Cache-Control: max-age</code>
     directive, or <code>Expires</code> header), caches are allowed to
     estimate how fresh it is using a heuristic.<p>
     Usually, but not always, this is done using the
     <code>Last-Modified</code> header. For example, if your response was last
     modified a week ago, a cache might decide to consider the response fresh
     for a day.<p>
     Consider adding a <code>Cache-Control</code> header; otherwise, it may be
     cached for longer or shorter than you'd like."""
    }

class FRESHNESS_NONE(Note):
    category = c.CACHING
    level = l.INFO
    summary = {
     'en': u"%(response)s can only be served by a cache under exceptional \
circumstances."
    }
    text = {
     'en': u"""%(response)s doesn't have explicit freshness information (like
     a <code> Cache-Control: max-age</code> directive, or <code>Expires</code>
     header), and this status code doesn't allow caches to calculate their
     own.<p>
     Therefore, while caches may be allowed to store it, they can't use it,
     except in unusual cirucumstances, such a when the origin server can't be
     contacted.<p> This behaviour can be prevented by using the
     <code>Cache-Control: must-revalidate</code> response directive.<p>
     Note that many caches will not store the response at all, because it is
     not generally useful to do so.
     """
    }

class FRESH_SERVABLE(Note):
    category = c.CACHING
    level = l.INFO
    summary = {
     'en': u"%(response)s may still be served by a cache once it becomes stale."
    }
    text = {
    'en': u"""HTTP allows stale responses to be served under some
    circumstances; for example, if the origin server can't be contacted, a
    stale response can be used (even if it doesn't have explicit freshness
    information).<p>
    This behaviour can be prevented by using the <code>Cache-Control:
    must-revalidate</code> response directive."""
    }

class STALE_SERVABLE(Note):
    category = c.CACHING
    level = l.INFO
    summary = {
     'en': u"%(response)s might be served by a cache, even though it is stale."
    }
    text = {
    'en': u"""HTTP allows stale responses to be served under some
    circumstances; for example, if the origin server can't be contacted, a
    stale response can be used (even if it doesn't have explicit freshness
    information).<p>
    This behaviour can be prevented by using the <code>Cache-Control:
    must-revalidate</code> response directive."""
    }

class FRESH_MUST_REVALIDATE(Note):
    category = c.CACHING
    level = l.INFO
    summary = {
     'en': u"%(response)s cannot be served by a cache once it becomes stale."
    }
    text = {
    'en': u"""The <code>Cache-Control: must-revalidate</code> directive
    forbids caches from using stale responses to satisfy requests.<p>For
    example, caches often use stale responses when they cannot connect to the
    origin server; when this directive is present, they will return an error
    rather than a stale response."""
    }

class STALE_MUST_REVALIDATE(Note):
    category = c.CACHING
    level = l.INFO
    summary = {
     'en': u"%(response)s cannot be served by a cache, because it is stale."
    }
    text = {
    'en': u"""The <code>Cache-Control: must-revalidate</code> directive
    forbids caches from using stale responses to satisfy requests.<p>For
    example, caches often use stale responses when they cannot connect to the
    origin server; when this directive is present, they will return an error
    rather than a stale response."""
    }

class FRESH_PROXY_REVALIDATE(Note):
    category = c.CACHING
    level = l.INFO
    summary = {
     'en': u"%(response)s cannot be served by a shared cache once it becomes \
stale."
    }
    text = {
    'en': u"""The presence of the <code>Cache-Control: proxy-revalidate</code>
    and/or <code>s-maxage</code> directives forbids shared caches (e.g., proxy
    caches) from using stale responses to satisfy requests.<p>For example,
    caches often use stale responses when they cannot connect to the origin
    server; when this directive is present, they will return an error rather
    than a stale response.<p>These directives do not affect private caches;
    for example, those in browsers."""
    }

class STALE_PROXY_REVALIDATE(Note):
    category = c.CACHING
    level = l.INFO
    summary = {
     'en': u"%(response)s cannot be served by a shared cache, because it is \
stale."
    }
    text = {
    'en': u"""The presence of the <code>Cache-Control: proxy-revalidate</code>
    and/or <code>s-maxage</code> directives forbids shared caches (e.g., proxy
    caches) from using stale responses to satisfy requests.<p>For example,
    caches often use stale responses when they cannot connect to the origin
    server; when this directive is present, they will return an error rather
    than a stale response.<p>These directives do not affect private caches;
    for example, those in browsers."""
    }

class CHECK_SINGLE(Note):
    category = c.CACHING
    level = l.WARN
    summary = {
     'en': u"Only one of the pre-check and post-check Cache-Control \
directives is present."
    }
    text = {
     'en': u"""Microsoft Internet Explorer implements two
     <code>Cache-Control</code> extensions, <code>pre-check</code> and
     <code>post-check</code>, to give more control over how its cache stores
     responses.<p> %(response)s uses only one of these directives; as a
     result, Internet Explorer will ignore the directive, since it requires
     both to be present.<p>
     See <a href="http://bit.ly/rzT0um">this blog entry</a> for more
     information.
     """
    }

class CHECK_NOT_INTEGER(Note):
    category = c.CACHING
    level = l.WARN
    summary = {
     'en': u"One of the pre-check/post-check Cache-Control directives has \
a non-integer value."
    }
    text = {
     'en': u"""Microsoft Internet Explorer implements two
     <code>Cache-Control</code> extensions, <code>pre-check</code> and
     <code>post-check</code>, to give more control over how its cache stores
     responses.<p> Their values are required to be integers, but here at least
     one is not. As a result, Internet Explorer will ignore the directive.<p>
     See <a href="http://bit.ly/rzT0um">this blog entry</a> for more
     information.
     """
    }

class CHECK_ALL_ZERO(Note):
    category = c.CACHING
    level = l.WARN
    summary = {
     'en': u"The pre-check and post-check Cache-Control directives are both \
'0'."
    }
    text = {
     'en': u"""Microsoft Internet Explorer implements two
     <code>Cache-Control</code> extensions, <code>pre-check</code> and
     <code>post-check</code>, to give more control over how its cache stores
     responses.<p> %(response)s gives a value of "0" for both; as a result,
     Internet Explorer will ignore the directive, since it requires both to be
     present.<p>
     In other words, setting these to zero has <strong>no effect</strong>
     (besides wasting bandwidth), and may trigger bugs in some beta versions
     of IE.<p>
     See <a href="http://bit.ly/rzT0um">this blog entry</a> for more
     information.
     """
    }

class CHECK_POST_BIGGER(Note):
    category = c.CACHING
    level = l.WARN
    summary = {
     'en': u"The post-check Cache-control directive's value is larger \
than pre-check's."
    }
    text = {
     'en': u"""Microsoft Internet Explorer implements two
     <code>Cache-Control</code> extensions, <code>pre-check</code> and
     <code>post-check</code>, to give more control over how its cache stores
     responses.<p> %(response)s assigns a higher value to
     <code>post-check</code> than to <code>pre-check</code>; this means that
     Internet Explorer will treat <code>post-check</code> as if its value is
     the same as <code>pre-check</code>'s.<p>
     See <a href="http://bit.ly/rzT0um">this blog entry</a> for more
     information.
     """
    }

class CHECK_POST_ZERO(Note):
    category = c.CACHING
    level = l.BAD
    summary = {
     'en': u"The post-check Cache-control directive's value is '0'."
    }
    text = {
     'en': u"""Microsoft Internet Explorer implements two
     <code>Cache-Control</code> extensions, <code>pre-check</code> and
     <code>post-check</code>, to give more control over how its cache stores
     responses.<p> %(response)s assigns a value of "0" to
     <code>post-check</code>, which means that Internet Explorer will reload
     the content as soon as it enters the browser cache, effectively
     <strong>doubling the load on the server</strong>.<p>
     See <a href="http://bit.ly/rzT0um">this blog entry</a> for more
     information.
     """
    }

class CHECK_POST_PRE(Note):
    category = c.CACHING
    level = l.INFO
    summary = {
     'en': u"%(response)s may be refreshed in the background by Internet \
Explorer."
    }
    text = {
     'en': u"""Microsoft Internet Explorer implements two
     <code>Cache-Control</code> extensions, <code>pre-check</code> and
     <code>post-check</code>, to give more control over how its cache stores
     responses.<p> Once it has been cached for more than %(post_check)s
     seconds, a new request will result in the cached response being served
     while it is refreshed in the background. However, if it has been cached
     for more than %(pre_check)s seconds, the browser will download a fresh
     response before showing it to the user.<p> Note that these directives do
     not have any effect on other clients or caches.<p>
     See <a href="http://bit.ly/rzT0um">this blog entry</a> for more
     information.
     """
    }


### General Validation

class NO_DATE_304(Note):
    category = c.VALIDATION
    level = l.WARN
    summary = {
    'en': u"304 responses need to have a Date header."
    }
    text = {
    'en': u"""HTTP requires <code>304 Not Modified</code> responses to 
    have a <code>Date</code> header in all but the most unusual 
    circumstances."""
    }

class MISSING_HDRS_304(Note):
    category = c.VALIDATION
    level = l.WARN
    summary = {
    'en': u"The %(subreq_type)s response is missing required headers."
    }
    text = {
    'en': u"""HTTP requires <code>304 Not Modified</code> responses to 
    have certain headers, if they are also present in a normal (e.g.,
    <code>200 OK</code> response).<p>
    %(response)s is missing the following headers:
    <code>%(missing_hdrs)s</code>.<p>
    This can affect cache operation; because the headers are missing,
    caches might remove them from their cached copies."""
    }

### ETag Validation

class ETAG_SUBREQ_PROBLEM(Note):
    category = c.VALIDATION
    level = l.BAD
    summary = {
    'en': u"There was a problem checking for ETag validation support."
    }
    text = {
    'en': u"""When RED tried to check the resource for ETag validation
    support, there was a problem:<p>
    <code>%(problem)s</code><p>
    Trying again might fix it."""
    }
    
class INM_304(Note):
    category = c.VALIDATION
    level = l.GOOD
    summary = {
    'en': u"If-None-Match conditional requests are supported."
    }
    text = {
    'en': u"""HTTP allows clients to make conditional requests to see if a 
    copy that they hold is still valid. Since this response has an 
    <code>ETag</code>, clients should be able to use an 
    <code>If-None-Match</code> request header for validation. RED has done 
    this and found that the resource sends a <code>304 Not Modified</code> 
    response, indicating that it supports <code>ETag</code> validation."""
    }

class INM_FULL(Note):
    category = c.VALIDATION
    level = l.WARN
    summary = {
    'en': u"An If-None-Match conditional request returned the full content \
unchanged."
    }
    text = {
    'en': u"""HTTP allows clients to make conditional requests to see if a 
    copy that they hold is still valid. Since this response has an 
    <code>ETag</code>, clients should be able to use an 
    <code>If-None-Match</code> request header for validation.<p>
    RED has done this and found that the resource sends the same, full
    response even though it hadn't changed, indicating that it doesn't support
    <code>ETag</code> validation."""
    }

class INM_DUP_ETAG_WEAK(Note):
    category = c.VALIDATION
    level = l.INFO
    summary = {
    'en': u"During validation, the ETag didn't change, even though the \
response body did."
    }
    text = {
    'en': u"""<code>ETag</code>s are supposed to uniquely identify the
    response representation; if the content changes, so should the ETag.<p>
    However, HTTP allows reuse of an <code>ETag</code> if it's "weak", as long
    as the server is OK with the two different responses being considered
    as interchangeable by clients.<p>
    For example, if a small detail of a Web page changes, and it doesn't
    affect the overall meaning of the page, you can use the same weak 
    <code>ETag</code> to identify both versions.<p>
    If the changes are important, a different <code>ETag</code> should be 
    used.
    """
    }
    
class INM_DUP_ETAG_STRONG(Note):
    category = c.VALIDATION
    level = l.BAD
    summary = {
    'en': u"During validation, the ETag didn't change, even though the \
response body did."
    }
    text = {
    'en': u"""<code>ETag</code>s are supposed to uniquely identify the
    response representation; if the content changes, so should the ETag.<p>
    Here, the same <code>ETag</code> was used for two different responses
    during validation, which means that downstream clients and caches might
    confuse them.<p>
    If the changes between the two versions aren't important, and they can
    be used interchangeably, a "weak" ETag should be used; to do that, just
    prepend <code>W/</code>, to make it <code>W/%(etag)s</code>. Otherwise,
    a different <code>ETag</code> needs to be used.
    """
    }

class INM_UNKNOWN(Note):
    category = c.VALIDATION
    level = l.INFO
    summary = {
     'en': u"An If-None-Match conditional request returned the full \
content, but it had changed."
    }
    text = {
    'en': u"""HTTP allows clients to make conditional requests to see if a 
    copy that they hold is still valid. Since this response has an 
    <code>ETag</code>, clients should be able to use an 
    <code>If-None-Match</code> request header for validation.<p>
    RED has done this, but the response changed between the original request
    and the validating request, so RED can't tell whether or not
    <code>ETag</code> validation is supported."""
    }

class INM_STATUS(Note):
    category = c.VALIDATION
    level = l.INFO
    summary = {
    'en': u"An If-None-Match conditional request returned a %(inm_status)s \
status."
    }
    text = {
    'en': u"""HTTP allows clients to make conditional requests to see if a 
    copy that they hold is still valid. Since this response has an 
    <code>ETag</code>, clients should be able to use an 
    <code>If-None-Match</code> request header
    for validation. RED has done this, but the response had a 
    %(enc_inm_status)s status code, so RED can't tell whether or not 
    <code>ETag</code> validation is supported."""
    }

### Last-Modified Validation

class LM_SUBREQ_PROBLEM(Note):
    category = c.VALIDATION
    level = l.BAD
    summary = {
    'en': u"There was a problem checking for Last-Modified validation support."
    }
    text = {
    'en': u"""When RED tried to check the resource for Last-Modified validation
    support, there was a problem:<p>
    <code>%(problem)s</code><p>
    Trying again might fix it."""
    }
class IMS_304(Note):
    category = c.VALIDATION
    level = l.GOOD
    summary = {
    'en': u"If-Modified-Since conditional requests are supported."
    }
    text = {
    'en': u"""HTTP allows clients to make conditional requests to see if a 
    copy that they hold is still valid. Since this response has a
    <code>Last-Modified</code> header, clients should be able to use an
    <code>If-Modified-Since</code> request header for validation.<p>
    RED has done this and found that the resource sends a
    <code>304 Not Modified</code> response, indicating that it supports
    <code>Last-Modified</code> validation."""
    }

class IMS_FULL(Note):
    category = c.VALIDATION
    level = l.WARN
    summary = {
    'en': u"An If-Modified-Since conditional request returned the full \
content unchanged."
    }
    text = {
    'en': u"""HTTP allows clients to make conditional requests to see if a 
    copy that they hold is still valid. Since this response has a
    <code>Last-Modified</code> header, clients should be able to use an
    <code>If-Modified-Since</code> request header for validation.<p>
    RED has done this and found that the resource sends a full response even
    though it hadn't changed, indicating that it doesn't support
    <code>Last-Modified</code> validation."""
    }

class IMS_UNKNOWN(Note):
    category = c.VALIDATION
    level = l.INFO
    summary = {
     'en': u"An If-Modified-Since conditional request returned the full \
content, but it had changed."
    }
    text = {
    'en': u"""HTTP allows clients to make conditional requests to see if a 
    copy that they hold is still valid. Since this response has a
    <code>Last-Modified</code> header, clients should be able to use an
    <code>If-Modified-Since</code> request header for validation.<p>
    RED has done this, but the response changed between the original request 
    and the validating request, so RED can't tell whether or not
    <code>Last-Modified</code> validation is supported."""
    }

class IMS_STATUS(Note):
    category = c.VALIDATION
    level = l.INFO
    summary = {
    'en': u"An If-Modified-Since conditional request returned a \
%(ims_status)s status."
    }
    text = {
    'en': u"""HTTP allows clients to make conditional requests to see if a 
    copy that they hold is still valid. Since this response has a
    <code>Last-Modified</code> header, clients should be able to use an
    <code>If-Modified-Since</code> request header for validation.<p>
    RED has done this, but the response had a %(enc_ims_status)s status code, 
    so RED can't tell whether or not <code>Last-Modified</code> validation is
    supported."""
    }

### Status checks

class UNEXPECTED_CONTINUE(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
     'en': u"A 100 Continue response was sent when it wasn't asked for."
    }
    text = {
     'en': u"""HTTP allows clients to ask a server if a request with a body
     (e.g., uploading a large file) will succeed before sending it, using
     a mechanism called "Expect/continue".<p>
     When used, the client sends an <code>Expect: 100-continue</code>, in
     the request headers, and if the server is willing to process it, it
     will send a <code> 100 Continue</code> status code to indicte that the
     request should continue.<p>
     This response has a <code>100 Continue</code> status code, but RED
     did not ask for it (with the <code>Expect</code> request header). Sending
     this status code without it being requested can cause interoperability
     problems."""
    }

class UPGRADE_NOT_REQUESTED(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
     'en': u"The protocol was upgraded without being requested."
    }
    text = {
     'en': u"""HTTP defines the <code>Upgrade</code> header as a means
     of negotiating a change of protocol; i.e., it allows you to switch
     the protocol on a given connection from HTTP to something else.<p>
     However, it must be first requested by the client; this response
     contains an <code>Upgrade</code> header, even though RED did not
     ask for it.<p>
     Trying to upgrade the connection without the client's participation
     obviously won't work."""
    }

class CREATED_SAFE_METHOD(Note):
    category = c.GENERAL
    level = l.WARN
    summary = {
     'en': u"A new resource was created in response to a safe request."
    }
    text = {
     'en': u"""The <code>201 Created</code> status code indicates that
     processing the request had the side effect of creating a new resource.<p>
     However, the request method that RED used (%(method)s) is defined as
     a "safe" method; that is, it should not have any side effects.<p>
     Creating resources as a side effect of a safe method can have unintended
     consequences; for example, search engine spiders and similar automated
     agents often follow links, and intermediaries sometimes re-try safe
     methods when they fail."""
    }

class CREATED_WITHOUT_LOCATION(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
     'en': u"A new resource was created without its location being sent."
    }
    text = {
     'en': u"""The <code>201 Created</code> status code indicates that
     processing the request had the side effect of creating a new resource.<p>
     HTTP specifies that the URL of the new resource is to be indicated in the
     <code>Location</code> header, but it isn't present in this response."""
    }

class CONTENT_RANGE_MEANINGLESS(Note):
    category = c.RANGE
    level = l.WARN
    summary = {
      'en': u"%(response)s shouldn't have a Content-Range header."
    }
    text = {
      'en': u"""HTTP only defines meaning for the <code>Content-Range</code>
      header in responses with a <code>206 Partial Content</code> or
      <code>416 Requested Range Not Satisfiable</code> status code.<p>
      Putting a <code>Content-Range</code> header in this response may
      confuse caches and clients."""
    }

class PARTIAL_WITHOUT_RANGE(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
     'en': u"%(response)s doesn't have a Content-Range header."
    }
    text = {
     'en': u"""The <code>206 Partial Response</code> status code indicates
     that the response body is only partial.<p> 
     However, for a response to be partial, it needs to have a
     <code>Content-Range</code> header to indicate what part of the full
     response it carries. This response does not have one, and as a result
     clients won't be able to process it."""
    }

class PARTIAL_NOT_REQUESTED(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
     'en': u"A partial response was sent when it wasn't requested."
    }
    text = {
     'en': u"""The <code>206 Partial Response</code> status code indicates 
     that the response body is only partial.<p>
     However, the client needs to ask for it with the <code>Range</code> 
     header.<p>
     RED did not request a partial response; sending one without the client
     requesting it leads to interoperability problems."""
    }

class REDIRECT_WITHOUT_LOCATION(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
     'en': u"Redirects need to have a Location header."
    }
    text = {
     'en': u"""The %(status)s status code redirects users to another URI. 
     The <code>Location</code> header is used to convey this URI, but a valid 
     one isn't present in this response."""
    }

class STATUS_DEPRECATED(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
     'en': u"The %(status)s status code is deprecated."
    }
    text = {
     'en': u"""When a status code is deprecated, it should not be used,
     because its meaning is not well-defined enough to ensure 
     interoperability."""
    }

class STATUS_RESERVED(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
     'en': u"The %(status)s status code is reserved."
    }
    text = {
     'en': u"""Reserved status codes can only be used by future, standard 
     protocol extensions; they are not for private use."""
    }

class STATUS_NONSTANDARD(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
     'en': u"%(status)s is not a standard HTTP status code."
    }
    text = {
     'en': u"""Non-standard status codes are not well-defined and 
     interoperable. Instead of defining your own status code, you should reuse 
     one of the more generic ones; for example, 400 for a client-side problem, 
     or 500 for a server-side problem."""
    }

class STATUS_BAD_REQUEST(Note):
    category = c.GENERAL
    level = l.WARN
    summary = {
     'en': u"The server didn't understand the request."
    }
    text = {
     'en': u""" """
    }

class STATUS_FORBIDDEN(Note):
    category = c.GENERAL
    level = l.INFO
    summary = {
     'en': u"The server has forbidden this request."
    }
    text = {
     'en': u""" """
    }

class STATUS_NOT_FOUND(Note):
    category = c.GENERAL
    level = l.INFO
    summary = {
     'en': u"The resource could not be found."
    }
    text = {
     'en': u"""The server couldn't find any resource to serve for the
     given URI."""
    }

class STATUS_NOT_ACCEPTABLE(Note):
    category = c.GENERAL
    level = l.INFO
    summary = {
     'en': u"The resource could not be found."
    }
    text = {
     'en': u""""""
    }

class STATUS_CONFLICT(Note):
    category = c.GENERAL
    level = l.INFO
    summary = {
     'en': u"The request conflicted with the state of the resource."
    }
    text = {
     'en': u""" """
    }

class STATUS_GONE(Note):
    category = c.GENERAL
    level = l.INFO
    summary = {
     'en': u"The resource is gone."
    }
    text = {
     'en': u"""The server previously had a resource at the given URI, but it
     is no longer there."""
    }

class STATUS_REQUEST_ENTITY_TOO_LARGE(Note):
    category = c.GENERAL
    level = l.INFO
    summary = {
     'en': u"The request body was too large for the server."
    }
    text = {
     'en': u"""The server rejected the request because the request body sent
     was too large."""
    }

class STATUS_URI_TOO_LONG(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
    'en': u"The server won't accept a URI this long %(uri_len)s."
    }
    text = {
    'en': u"""The %(status)s status code means that the server can't or 
    won't accept a request-uri this long."""
    }

class STATUS_UNSUPPORTED_MEDIA_TYPE(Note):
    category = c.GENERAL
    level = l.INFO
    summary = {
     'en': u"The resource doesn't support this media type in requests."
    }
    text = {
     'en': u""" """
    }

class STATUS_INTERNAL_SERVICE_ERROR(Note):
    category = c.GENERAL
    level = l.INFO
    summary = {
     'en': u"There was a general server error."
    }
    text = {
     'en': u""" """
    }

class STATUS_NOT_IMPLEMENTED(Note):
    category = c.GENERAL
    level = l.INFO
    summary = {
     'en': u"The server doesn't implement the request method."
    }
    text = {
     'en': u""" """
    }

class STATUS_BAD_GATEWAY(Note):
    category = c.GENERAL
    level = l.INFO
    summary = {
     'en': u"An intermediary encountered an error."
    }
    text = {
     'en': u""" """
    }

class STATUS_SERVICE_UNAVAILABLE(Note):
    category = c.GENERAL
    level = l.INFO
    summary = {
     'en': u"The server is temporarily unavailable."
    }
    text = {
     'en': u""" """
    }

class STATUS_GATEWAY_TIMEOUT(Note):
    category = c.GENERAL
    level = l.INFO
    summary = {
     'en': u"An intermediary timed out."
    }
    text = {
     'en': u""" """
    }

class STATUS_VERSION_NOT_SUPPORTED(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
     'en': u"The request HTTP version isn't supported."
    }
    text = {
     'en': u""" """
    }

class PARAM_STAR_QUOTED(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
     'en': u"The '%(param)s' parameter's value cannot be quoted."
    }
    text = {
     'en': u"""Parameter values that end in '*' have a specific format,
     defined in <a href="http://tools.ietf.org/html/rfc5987">RFC5987</a>,
     to allow non-ASCII text.<p>
     The <code>%(param)s</code> parameter on the <code>%(field_name)s</code>
     header has double-quotes around it, which is not valid."""
    }

class PARAM_STAR_ERROR(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
     'en': u"The %(param)s parameter's value is invalid."
    }
    text = {
     'en': u"""Parameter values that end in '*' have a specific format,
     defined in <a href="http://tools.ietf.org/html/rfc5987">RFC5987</a>,
     to allow non-ASCII text.<p>. 
     The <code>%(param)s</code> parameter on the <code>%(field_name)s</code>
     header is not valid; it needs to have three parts, separated by single
     quotes (')."""
    }

class PARAM_STAR_BAD(Note):
    category = c.GENERAL
    level = l.BAD
    summary = {
     'en': u"The %(param)s* parameter isn't allowed on the %(field_name)s \
header."
    }
    text = {
     'en': u"""Parameter values that end in '*' are reserved for 
     non-ascii text, as explained in <a 
     href="http://tools.ietf.org/html/rfc5987">RFC5987</a>.<p>
     The <code>%(param)s</code> parameter on the <code>%(field_name)s</code>
     does not allow this; you should use %(param)s without the "*" on the end (and without the associated encoding).<p>
     RED ignores the content of this parameter. 
     """
    }

class PARAM_STAR_NOCHARSET(Note):
    category = c.GENERAL
    level = l.WARN
    summary = {
     'en': u"The %(param)s parameter's value doesn't define an encoding."
    }
    text = {
     'en': u"""Parameter values that end in '*' have a specific format,
     defined in <a href="http://tools.ietf.org/html/rfc5987">RFC5987</a>,
     to allow non-ASCII text.<p>. 
     The <code>%(param)s<code> parameter on the <code>%(field_name)s</code>
     header doesn't declare its character encoding, which means that
     recipients can't understand it. It should be <code>UTF-8</code>."""
    }

class PARAM_STAR_CHARSET(Note):
    category = c.GENERAL
    level = l.WARN
    summary = {
     'en': u"The %(param)s parameter's value uses an encoding other than \
UTF-8."
    }
    text = {
     'en': u"""Parameter values that end in '*' have a specific format,
     defined in <a href="http://tools.ietf.org/html/rfc5987">RFC5987</a>,
     to allow non-ASCII text.<p>. 
     The <code>%(param)s</code> parameter on the <code>%(field_name)s</code>
     header uses the <code>'%(enc)s</code> encoding, which has
     interoperability issues on some browsers. It should be
     <code>UTF-8</code>."""
    }

class PARAM_REPEATS(Note):
    category = c.GENERAL
    level = l.WARN
    summary = {
     'en': u"The '%(param)s' parameter repeats in the %(field_name)s header."
    }
    text = {
     'en': u"""Parameters on the %(field_name)s header should not repeat; 
     implementations may handle them differently."""
    }

class PARAM_SINGLE_QUOTED(Note):
    category = c.GENERAL
    level = l.WARN
    summary = {
     'en': u"The '%(param)s' parameter on the %(field_name)s header is \
single-quoted."
    }
    text = {
     'en': u"""The <code>%(param)s</code>'s value on the %(field_name)s 
     header start and ends with a single quote ('). However, single quotes
     don't mean anything there.<p>
     This means that the value will be interpreted as
     <code>%(param_val)s</code>, <strong>not</strong>
     <code>%(param_val_unquoted)s</code>. If you intend the latter, drop
     the single quotes."""
    }

class DISPOSITION_UNKNOWN(Note):
    category = c.GENERAL
    level = l.WARN
    summary = {
     'en': u"The '%(disposition)s' Content-Disposition isn't known."
    }
    text = {
     'en': u"""The <code>Content-Disposition<code> header has two 
     widely-known values; <code>inline</code> and <code>attachment</code>.
     <code>%(disposition)s</code>  isn't recognised, and most implementations
     will default to handling it like <code>attachment</code>."""
    }

class DISPOSITION_OMITS_FILENAME(Note):
    category = c.GENERAL
    level = l.WARN
    summary = {
     'en': u"The Content-Disposition header doesn't have a 'filename' \
parameter."
    }
    text = {
     'en': u"""The <code>Content-Disposition</code> header suggests a 
     filename for clients to use when saving the file locally.<p>
     It should always contain a <code>filename</code> parameter, even when 
     the <code>filename*</code> parameter is used to carry an
     internationalised filename, so that browsers can fall back to an
     ASCII-only filename."""
    }

class DISPOSITION_FILENAME_PERCENT(Note):
    category = c.GENERAL
    level = l.WARN
    summary = {
     'en': u"The 'filename' parameter on the Content-Disposition header \
contains a '%%' character."
    }
    text = {
     'en': u"""The <code>Content-Disposition</code> header suggests a 
     filename for clients to use when saving the file locally, using 
     the <code>filename</code> parameter.<p>
     <a href="http://tools.ietf.org/html/rfc6266">RFC6266</a>
     specifies how to carry non-ASCII characters in this parameter. However,
     historically some (but not all) browsers have also decoded %%-encoded
     characters in the <code>filename</code> parameter, which means that
     they'll be treated differently depending on the browser you're using.<p>
     As a result, it's not interoperable to use percent characters in the
     <code>filename</code> parameter. Use the correct encoding in the 
     <code>filename*</code> parameter instead.
     """
    }

class DISPOSITION_FILENAME_PATH_CHAR(Note):
    category = c.GENERAL
    level = l.WARN
    summary = {
     'en': u"The filename in the Content-Disposition header contains a \
path character."
    }
    text = {
     'en': u"""The <code>Content-Disposition</code> header suggests a 
     filename for clients to use when saving the file locally, using 
     the <code>filename</code> and <code>filename*</code> parameters.<p>
     One of these parameters contains a path character ("\" or "/"), used
     to navigate between directories on common operating systems.<p>
     Because this can be used to attach the browser's host operating system
     (e.g., by saving a file to a system directory), browsers will usually
     ignore these paramters, or remove path information.<p>
     You should remove these characters.
     """
    }
    
class LINK_REV(Note):
    category = c.GENERAL
    level=l.WARN
    summary = {
     'en': u"The 'rev' parameter on the Link header is deprecated."
    }
    text = {
     'en': u"""The <code>Link</code> header, defined by 
     <a href="http://tools.ietf.org/html/rfc5988#section-5">RFC5988</a>, 
     uses the <code>rel</code> parameter to communicate the type of a link.
     <code>rev</code> is deprecated by that specification because it is 
     often confusing.<p>
     Use <code>rel</code> and an appropriate relation.
     """
    }

class LINK_BAD_ANCHOR(Note):
    category = c.GENERAL
    level=l.WARN
    summary = {
     'en': u"The 'anchor' parameter on the %(link)s Link header isn't a URI."
    }
    text = {
     'en': u"""The <code>Link</code> header, defined by 
     <a href="http://tools.ietf.org/html/rfc5988#section-5">RFC5988</a>, 
     uses the <code>anchor</code> parameter to define the context URI for 
     the link.<p>
     This parameter can be an absolute or relative URI; however, 
     <code>%(anchor)s</code> is neither.
     """
    }

class SET_COOKIE_NO_VAL(Note):
    category = c.GENERAL
    level=l.BAD
    summary = {
     'en': u"%(response)s has a Set-Cookie header that can't be parsed."
    }
    text = {
     'en': u"""This <code>Set-Cookie</code> header can't be parsed into a 
     name and a value; it must start with a <code>name=value</code>
     structure.<p>
     <p>Browsers will ignore this cookie."""
    }

class SET_COOKIE_NO_NAME(Note):
    category = c.GENERAL
    level=l.BAD
    summary = {
     'en': u"%(response)s has a Set-Cookie header without a cookie-name."
    }
    text = {
     'en': u"""This <code>Set-Cookie</code> header has an empty name; there
     needs to be a name before the <code>=</code>.<p>
     <p>Browsers will ignore this cookie."""
    }

class SET_COOKIE_BAD_DATE(Note):
    category = c.GENERAL
    level=l.WARN
    summary = {
     'en': u"The %(cookie_name)s Set-Cookie header has an invalid Expires \
date."
    }
    text = {
     'en': u"""The <code>expires</code> date on this <code>Set-Cookie</code>
     header isn't valid; see 
     <a href="http://tools.ietf.org/html/rfc6265">RFC6265</a> for details 
     of the correct format.
     """
    }

class SET_COOKIE_EMPTY_MAX_AGE(Note):
    category = c.GENERAL
    level=l.WARN
    summary = {
     'en': u"The %(cookie_name)s Set-Cookie header has an empty Max-Age."
    }
    text = {
     'en': u"""The <code>max-age</code> parameter on this
     <code>Set-Cookie</code> header doesn't have a value.<p>
     Browsers will ignore the <code>max-age</code> value as a result."""
    }

class SET_COOKIE_LEADING_ZERO_MAX_AGE(Note):
    category = c.GENERAL
    level=l.WARN
    summary = {
     'en': u"The %(cookie_name)s Set-Cookie header has a Max-Age with a leading zero."
    }
    text = {
     'en': u"""The <code>max-age</code> parameter on this
     <code>Set-Cookie</code> header has a leading zero.<p>
     Browsers will ignore the <code>max-age</code> value as a result."""
    }

class SET_COOKIE_NON_DIGIT_MAX_AGE(Note):
    category = c.GENERAL
    level=l.WARN
    summary = {
     'en': u"The %(cookie_name)s Set-Cookie header has a non-numeric Max-Age."
    }
    text = {
     'en': u"""The <code>max-age</code> parameter on this
     <code>Set-Cookie</code> header isn't numeric.<p>
     Browsers will ignore the <code>max-age</code> value as a result."""
    }

class SET_COOKIE_EMPTY_DOMAIN(Note):
    category = c.GENERAL
    level=l.WARN
    summary = {
     'en': u"The %(cookie_name)s Set-Cookie header has an empty domain."
    }
    text = {
     'en': u"""The <code>domain</code> parameter on this
     <code>Set-Cookie</code> header is empty.<p>
     Browsers will probably ignore it as a result."""
    }

class SET_COOKIE_UNKNOWN_ATTRIBUTE(Note):
    category = c.GENERAL
    level=l.WARN
    summary = {
     'en': u"The %(cookie_name)s Set-Cookie header has an unknown attribute, \
'%(attribute)s'."
    }
    text = {
     'en': u"""This <code>Set-Cookie</code> header has an extra parameter,
     "%(attribute)s".<p>
     Browsers will ignore it.
     """
    }


if __name__ == '__main__':
    # do a sanity check on all of the defined messages
    import re, types
    for n, v in locals().items():
        if type(v) is types.ClassType and issubclass(v, Note) \
          and n != "Note":
            print "checking", n
            assert v.category in c.__class__.__dict__.values(), n
            assert v.level in l.__class__.__dict__.values(), n
            assert type(v.summary) is types.DictType, n
            assert v.summary != {}, n
            assert v.summary.has_key('en'), n
            assert not re.search("\s{2,}", v.summary['en']), n
            assert type(v.text) is types.DictType, n
            assert v.text != {}, n
            assert v.text.has_key('en'), n

########NEW FILE########
__FILENAME__ = state
#!/usr/bin/env python

"""
The Resource Expert Droid State container.

RedState holds all test-related state that's useful for analysis; ephemeral
objects (e.g., the HTTP client machinery) are kept elsewhere.
"""

__author__ = "Mark Nottingham <mnot@mnot.net>"
__copyright__ = """\
Copyright (c) 2008-2013 Mark Nottingham

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
"""

import types

import redbot.speak as rs

class RedState(object):
    "Base class for things that have test state."

    def __init__(self, name):
        self.name = name
        self.notes = []

    def __repr__(self):
        status = [self.__class__.__module__ + "." + self.__class__.__name__]
        status.append("'%s'" % self.name)
        return "<%s at %#x>" % (", ".join(status), id(self))

    def __getstate__(self):
        state = self.__dict__.copy()
        return dict([(k, v) for k, v in state.items() \
                      if not isinstance(v, types.MethodType)])

    def add_note(self, subject, note, subreq=None, **kw):
        "Set a note."
        kw['response'] = rs.response.get(
            self.name, rs.response['this']
        )['en']
        self.notes.append(note(subject, subreq, kw))

########NEW FILE########
__FILENAME__ = ascii_with_complaints
"""
'ascii' codec, plus warnings. Suitable for use as the default encoding in
`site.py`.
Copyright Allen Short, 2010.

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


Based on ASCII codec from Python 2.7, made available under the Python license
(http://docs.python.org/license.html):

 Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010
Python Software Foundation; All Rights Reserved

 Python 'ascii' Codec


Written by Marc-Andre Lemburg (mal@lemburg.com).

(c) Copyright CNRI, All Rights Reserved. NO WARRANTY.

"""
import codecs, warnings

def encode(input, errors='strict'):
    warnings.warn("Implicit conversion of unicode to str", UnicodeWarning, 2)
    return codecs.ascii_encode(input, errors)


def decode(input, errors='strict'):
#    warnings.warn("Implicit conversion of str to unicode", UnicodeWarning, 2)
    return codecs.ascii_decode(input, errors)



class Codec(codecs.Codec):

    def encode(self, input,errors='strict'):
        return encode(input,errors)
    def decode(self, input,errors='strict'):
        return decode(input,errors)


class IncrementalEncoder(codecs.IncrementalEncoder):
    def encode(self, input, final=False):
        return encode(input, self.errors)[0]

class IncrementalDecoder(codecs.IncrementalDecoder):
    def decode(self, input, final=False):
        return decode(input, self.errors)[0]

class StreamWriter(Codec,codecs.StreamWriter):
    pass

class StreamReader(Codec,codecs.StreamReader):
    pass


### encodings module API

def getregentry():
    return codecs.CodecInfo(
        name='ascii_with_complaints',
        encode=encode,
        decode=decode,
        incrementalencoder=IncrementalEncoder,
        incrementaldecoder=IncrementalDecoder,
        streamwriter=StreamWriter,
        streamreader=StreamReader,
    )

def search_function(encoding):
    if encoding == 'ascii_with_complaints':
        return getregentry()

codecs.register(search_function)

########NEW FILE########
__FILENAME__ = sitecustomize
#!/usr/bin/env python

import ascii_with_complaints
import sys

sys.setdefaultencoding('ascii_with_complaints')
########NEW FILE########
__FILENAME__ = test_webui
#!/usr/bin/env python
# coding=UTF-8

import os
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
import time
import unittest


class BasicWebUiTest(unittest.TestCase):
    test_uri = "http://www.mnot.net/"
    
    def setUp(self):
        self.browser = webdriver.PhantomJS()
        self.browser.get(redbot_uri)
        self.uri = self.browser.find_element_by_id("uri")
        self.uri.send_keys(self.test_uri)
        self.uri.submit()
        time.sleep(1.0)
        self.check_complete()
        
    def test_multi(self):
        check = self.browser.find_element_by_css_selector('a[accesskey="a"]')
        check.click()
        time.sleep(0.5)
    
    def check_complete(self):
        try:
            self.browser.find_element_by_css_selector("div.footer")
        except NoSuchElementException:
            raise Exception, "Page not complete."
            self.browser.save_screenshot('dump.png')
    
    def tearDown(self):
        self.check_complete()
        self.browser.close()

class CnnWebUiTest(BasicWebUiTest):
    test_uri = 'http://edition.cnn.com/'


if __name__ == "__main__":
    test_host = "localhost"
    test_port = 8080
    redbot_uri = "http://%s:%s/" % (test_host, test_port)
    import sys
    sys.path.insert(0, "deploy")
    def redbot_run():
        import webui
        webui.standalone_main(test_host, test_port, "deploy/static")
    from multiprocessing import Process
    p = Process(target=redbot_run)
    p.start()
    unittest.main(exit=False, verbosity=2)
    print "done webui test..."
    p.terminate()
    

########NEW FILE########
__FILENAME__ = unit_tests
#!/usr/bin/env python
# coding=UTF-8

import sys
import unittest
sys.path.insert(0, "..")

import redbot.message.headers as headers
from redbot.message import http_syntax as syntax
import redbot.speak as rs
from redbot.message import DummyMsg

class GeneralHeaderTesters(unittest.TestCase):
    def setUp(self):
        self.red = DummyMsg()
    
    def test_unquote_string(self):
        i = 0
        for (instr, expected_str, expected_notes) in [
            ('foo', 'foo', []),
            ('"foo"', 'foo', []),
            (r'"fo\"o"', 'fo"o', []),
            (r'"f\"o\"o"', 'f"o"o', []),
            (r'"fo\\o"', r'fo\o', []),
            (r'"f\\o\\o"', r'f\o\o', []),
            (r'"fo\o"', 'foo', []),
        ]:
            self.red.__init__()
            out_str = headers.unquote_string(unicode(instr))
            diff = set(
                [n.__name__ for n in expected_notes]).symmetric_difference(
                set(self.red.note_classes)
            )
            self.assertEqual(len(diff), 0, 
                "[%s] Mismatched notes: %s" % (i, diff)
            )
            self.assertEqual(expected_str, out_str, 
                "[%s] %s != %s" % (i, str(expected_str), str(out_str)))
            i += 1
    
    def test_split_string(self):
        i = 0
        for (instr, expected_outlist, item, split) in [
            ('"abc", "def"', 
             ['"abc"', '"def"'], 
             syntax.QUOTED_STRING, 
             r"\s*,\s*"
            ),
            (r'"\"ab", "c\d"', 
             [r'"\"ab"', r'"c\d"'], 
             syntax.QUOTED_STRING, 
             r"\s*,\s*"
            )
        ]:
            self.red.__init__()
            outlist = headers.split_string(unicode(instr), item, split)
            self.assertEqual(expected_outlist, outlist, 
                "[%s] %s != %s" % (i, str(expected_outlist), str(outlist)))
            i += 1
    
    def test_parse_params(self):
        i = 0
        for (instr, expected_pd, expected_notes, delim) in [
            ('foo=bar', {'foo': 'bar'}, [], ';'),
            ('foo="bar"', {'foo': 'bar'}, [], ';'),
            ('foo="bar"; baz=bat', {'foo': 'bar', 'baz': 'bat'}, [], ';'),
            ('foo="bar"; baz="b=t"; bam="boom"',
             {'foo': 'bar', 'baz': 'b=t', 'bam': 'boom'}, [], ';'
            ),
            (r'foo="b\"ar"', {'foo': 'b"ar'}, [], ';'),
            (r'foo=bar; foo=baz', 
             {'foo': 'baz'}, 
             [rs.PARAM_REPEATS], 
             ';'
            ),
            ('foo=bar; baz="b;at"', 
             {'foo': 'bar', 'baz': "b;at"}, 
             [],
             ';'
            ),
            ('foo=bar, baz="bat"', 
             {'foo': 'bar', 'baz': "bat"}, 
             [],
             ','
            ),
            ('foo=bar, baz="b,at"', 
             {'foo': 'bar', 'baz': "b,at"}, 
             [],
             ','
            ),
            ("foo=bar; baz='bat'", 
             {'foo': 'bar', 'baz': "'bat'"}, 
             [rs.PARAM_SINGLE_QUOTED], 
             ';'
            ),
            ("foo*=\"UTF-8''a%cc%88.txt\"", 
             {'foo*': u'a\u0308.txt'},
             [rs.PARAM_STAR_QUOTED], 
             ';'
            ),
            ("foo*=''a%cc%88.txt", 
             {},
             [rs.PARAM_STAR_NOCHARSET], 
             ';'
            ),
            ("foo*=utf-16''a%cc%88.txt", 
             {},
             [rs.PARAM_STAR_CHARSET], 
             ';'
            ),
            ("nostar*=utf-8''a%cc%88.txt",
             {},
             [rs.PARAM_STAR_BAD], 
             ';'
            ),
            ("NOstar*=utf-8''a%cc%88.txt",
             {},
             [rs.PARAM_STAR_BAD], 
             ';'
            )
        ]:
            self.red.__init__()
            param_dict = headers.parse_params(
              self.red, 'test', instr, ['nostar'], delim
            )
            diff = set(
                [n.__name__ for n in expected_notes]).symmetric_difference(
                set(self.red.note_classes)
            )
            self.assertEqual(len(diff), 0, 
                "[%s] Mismatched notes: %s" % (i, diff)
            )
            self.assertEqual(expected_pd, param_dict, 
                "[%s] %s != %s" % (i, str(expected_pd), str(param_dict)))
            i += 1
                
if __name__ == "__main__":
    # requires Python 2.7
    import sys
    loader = unittest.TestLoader()
    if len(sys.argv) == 2:
        auto_suite = loader.discover("../redbot/message/headers", 
                                    "%s.py" % sys.argv[1],  
                                    "../redbot"
        )
        all_tests = unittest.TestSuite([auto_suite])
    else:
        auto_suite = loader.discover(
            "../redbot", "*.py", '../redbot'
        )
        local_suite = loader.loadTestsFromTestCase(GeneralHeaderTesters)
        all_tests = unittest.TestSuite([local_suite, auto_suite])
    result = unittest.TextTestRunner().run(all_tests)
    if result.errors or result.failures:
        sys.exit(1)

########NEW FILE########
__FILENAME__ = unicorn_ui
# -*- coding: utf-8 -*-

"""

Unicorn Interface for Red Cacheability Checker

Created on Jun 30, 2010
@author: Hirotaka Nakajima <hiro@w3.org>

"""
import sys
import os
from redbot.resource import HttpResource
from redbot.speak import _Classifications
from xml.dom import minidom
from xml.dom.minidom import parseString
import re
import cgi
import logging
import urllib
import nbhttp
from string import Template

__date__ = "Jun 30, 2010"
__author__ = "Hirotaka Nakajima <hiro@w3.org>"

class UnicornUi(object):
    """
    Unicorn Interface of Red Cacheability checker
    """
    def __init__(self, test_uri):
        """
        Constractor
        @param test_uri: Test Uri
        """
        self.test_uri = test_uri
        try:
            self.red = HttpResource(self.test_uri)
            self.result = ""
            self.done = False
            self.groups = []
            logger = logging.getLogger()
            logger.setLevel(logging.DEBUG)
            if self.red.response.complete:
                self.result = self._generate_output_xml(test_uri).toprettyxml()
            else:
                error_string = ""
                if self.red.response.http_error['desc'] == nbhttp.error.ERR_CONNECT['desc']:
                    error_string = "Could not connect to the server (%s)" % self.red.response.http_error.get('detail', "unknown")
                elif self.red.response.http_error['desc'] == nbhttp.error.ERR_URL['desc']:
                    error_string = self.red.response.http_error.get('detail', "RED can't fetch that URL.")
                elif self.red.response.http_error['desc'] == nbhttp.error.ERR_READ_TIMEOUT['desc']:
                    error_string = self.red.response.http_error['desc']
                elif self.red.response.http_error['desc'] == nbhttp.error.ERR_HTTP_VERSION['desc']:
                    error_string = "<code>%s</code> isn't HTTP." % e(self.red.response.http_error.get('detail', '')[:20])
                else:
                    raise AssertionError, "Unidentified incomplete response error."
                self.result = self._generate_error_xml(error_string).toprettyxml()
        except:
            import traceback
            logging.error(traceback.format_exc())
            self.result = """<?xml version="1.0" ?>
<observationresponse ref="None" xml:lang="en" xmlns="http://www.w3.org/2009/10/unicorn/observationresponse">
    <message type="error">
        <title>
            Internal Server Error
        </title>
        <description>
            Internal Server Error occured.
        </description>
    </message>
</observationresponse>"""
        
    def get_result(self):
        """
        Return result if cacheability check was finished.
        If not, return None
        @return: Result of cacheablity checker.
        """
        return str(self.result)
        
    def _get_response_document(self):
        """
        Generate response document
        @return: Root response document DOM object
        """
        doc = minidom.Document()
        rootDoc = doc.createElement("observationresponse")
        rootDoc.setAttribute("xmlns", "http://www.w3.org/2009/10/unicorn/observationresponse")
        rootDoc.setAttribute("xml:lang", "en")
        rootDoc.setAttribute("ref", self.test_uri)
        doc.appendChild(rootDoc)
        return rootDoc, doc
    
    def _output_response_header(self, doc, rootDoc):
        """
        Generate HTTP Response Header to Outputs
        """
        m = doc.createElement("message")
        m.setAttribute("type", "info")
        m.setAttribute("group", "response_header")
        title = doc.createElement("title")
        title.appendChild(doc.createTextNode("HTTP Response Header"))
        description = doc.createElement("description")
        ul = doc.createElement("ul")
        ul.setAttribute("class", "headers")
        description.appendChild(ul)
        for i in self.red.response.headers:
            li = doc.createElement("li")
            li.appendChild(doc.createTextNode(i[0] + ":" + i[1]))
            ul.appendChild(li)
        m.appendChild(title)
        m.appendChild(description)
        rootDoc.appendChild(m)
    
    def _handle_category(self, category_value):
        """
        Getting Classification key from values
        """
        category = _Classifications.__dict__.keys()[_Classifications.__dict__.values().index(category_value)]
        self.groups.append(category)
        return str(category).lower()
    
    def _add_group_elements(self, doc, rootDoc):
        """
        Getting group informations from _Classifications class
        This implimentation is little a bit hack :)
        """
        #Header group
        h_group_element = doc.createElement("group")
        h_group_element.setAttribute("name", "response_header")
        h_title_element = doc.createElement("title")
        h_title_element.appendChild(doc.createTextNode("HTTP Response Header"))
        h_group_element.appendChild(h_title_element)
        rootDoc.appendChild(h_group_element)
        
        for k in set(self.groups):
            group_element = doc.createElement("group")
            group_element.setAttribute("name", str(k).lower())
            title_element = doc.createElement("title")
            title_text = doc.createTextNode(getattr(_Classifications, k))
            title_element.appendChild(title_text)
            group_element.appendChild(title_element)
            rootDoc.appendChild(group_element)        

    def _generate_output_xml(self, test_uri):
        """
        Generate Output XML Document
        @return: Output XML Document
        """
        rootDoc, doc = self._get_response_document()
        for i in self.red.notes:
            m = doc.createElement("message")
            m.setAttribute("type", self._convert_level(i.level))

            """
            Hack
            TODO: clean up this code
            """            
            category = self._handle_category(i.category)
            m.setAttribute("group", category)
            
            title = doc.createElement("title")
            title.appendChild(doc.createTextNode(i.summary['en'] % i.vars))
            text = "<description>" + (i.text['en'] % i.vars) + "</description>"
            try:
                text_dom = parseString(self._convert_html_tags(text))
            except:
                logging.error(text)
                text_dom = parseString("<description>Internal Error</description>")
            text_element = text_dom.getElementsByTagName("description")
            m.appendChild(title)
            m.appendChild(text_element[0])
            rootDoc.appendChild(m)
        
        self._output_response_header(doc, rootDoc)
        self._add_group_elements(doc, rootDoc)
        
        return doc
        
    def _generate_error_xml(self, error_message):
        '''
        Return Error XML Document
        @return: Error XML Document
        '''
        rootDoc, doc = self._get_response_document()
        m = doc.createElement("message")
        m.setAttribute("type", "error")
        title = doc.createElement("title")
        title.appendChild(doc.createTextNode("Checker Error"))
        text = "<description>" + error_message + "</description>"
        try:
            text_dom = parseString(self._convert_html_tags(text))
        except:
            logging.error(text)
            text_dom = parseString("<description>Internal Error</description>")
        text_element = text_dom.getElementsByTagName("description")
        m.appendChild(title)
        m.appendChild(text_element[0])
        rootDoc.appendChild(m)
        return doc
    
    def _convert_level(self, level):
        '''
        Convert verbose level string from Redbot style to unicorn style
        '''
        level = re.sub("good", "info", level)
        level = re.sub("bad", "error", level)
        return level
    
    def _convert_html_tags(self, string):
        string = re.sub("<p>", "<br />", string)
        string = re.sub("</p>", "<br />", string)
        string = re.sub("<br/>", "<br />", string)
        string = re.sub("<br>", "<br />", string)
        return string
        

def application(environ, start_response):
    method = environ.get('REQUEST_METHOD')
    test_uri = None
    result = None
    run_engine = False
    response_headers = None
    if method == "GET":
        query = cgi.parse_qsl(environ.get('QUERY_STRING'))
        for q in query:
            if len(q) == 2:
                if q[0] == "ca_uri":
                    uri = q[1]
                    test_uri = cgi.escape(uri, True) 
                if q[0] == "output":
                    if q[1] == "ucn":
                        run_engine = True
                    
    
    if test_uri != None:
        if run_engine == True:
            red = UnicornUi(test_uri)
            result = red.get_result()
            status = '200 OK'
            response_headers = [('Content-type', 'application/xml'), ('Content-Length', str(len(result)))]
        else:
            status = '200 OK'
            logging.error(os.path.abspath("."))
            t = Template(open(os.path.join(os.path.dirname(__file__), "redirect_template.html")).read())
            d = dict(uri="http://redbot.org/?uri=" + test_uri)
            result = t.safe_substitute(d)
            response_headers = [('Content-type', 'application/xhtml+xml'), ('Content-Length', str(len(result)))]
    if result == None:
        status = '200 OK'
        result = """<?xml version="1.0" ?>
<observationresponse ref="None" xml:lang="en" xmlns="http://www.w3.org/2009/10/unicorn/observationresponse">
    <message type="error">
        <title>
            No URI provided
        </title>
        <description>
            URI isn't provided
        </description>
    </message>
</observationresponse>"""
        response_headers = [('Content-type', 'application/xml'), ('Content-Length', str(len(result)))]

    start_response(status, response_headers)    
    return [result]

def standalone_main(test_uri):
    test_uri = cgi.escape(test_uri, True) 
    red = UnicornUi(test_uri) 
    print red.get_result()

if __name__ == "__main__":
    import sys
    test_uri = sys.argv[1]   
    standalone_main(test_uri)


########NEW FILE########
