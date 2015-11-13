__FILENAME__ = git_http_backend_winservice
"""
The most basic (working) CherryPy 3.2 WSGI Windows service possible.
Requires Mark Hammond's pywin32 package.

Taken from here: http://tools.cherrypy.org/wiki/WindowsService and modified.
License and copyright unknown. No licence or warranty claimed on my behalf. 
Inquire with source mentioned above regarding either.

To see a list of options for installing, removing, starting, and stopping your service.
    python this_file.py
To install your new service type:
    python this_file.py install
Then type:
    python this_file.py start

If you get "Access Denied" you need to be admin to install, remove, start, stop.
    ( To run cmd as admin: Windows Key > "cmd" > CTRL+SHIFT+ENTER )
"""
import os.path
import shutil
import tempfile
import win32serviceutil
import win32service

import sys
import os
# this allows the winservice.py script to see modules in project's root folder.
# if you get "cannot find 'module name'" errors, change "." to actual
# path where git_http_backend.py is located.
sys.path.append(os.path.abspath("."))

import git_http_backend
import cherrypy as wsgiserver

class GitSmartHTTPServer(win32serviceutil.ServiceFramework):
# class GitSmartHTTPServer(object):
    """NT Service."""

    _svc_name_ = "GitSmartHTTPServer"
    # note: we are defining an extended description lower in the class.

    _server_ip = '0.0.0.0' # '0.0.0.0' means "all address on this server"
    '''Ip or name of the server hosting this git smart http service.'''

    _server_port = 8888
    '''The port on which this Git Smart HTTP server will listen on'''

    _content_path = "CHANGE ME!"
    '''This is the "start" of the physical path that will be exposed as
    the root folder for all repo folder references.

    If you already have a folder on your drive that has all the repo folders,
    this (or some folder above it) is the the folder you would like to 
    set the _content_path to.

    You need to escape backslashes or use Python's "r" marker to declare 
    "read this string liteterally". Examples: "c:\\temp" , r"c:\temp"

    Example:
        if _content_path = c:\our_repos_root
        URI http://server:port/userjoe/joes_repo_one.git
        Would mean to reference an actual folder:
            c:\our_repos_root\userjoe\joes_repo_one.git

    Until you change it to something real, we will be creating repos in
    temp folder of our choice and removing all repos when service stops.
    '''

    _uri_marker = "" # Example: "myprojects"
    '''This is a label that server will look for in the URI to determine
    which portion of the URI refers to the start of actual repo folder structures.

    The marker is not a physical file-system path, and is purely a flag that says
    to the git server "after this, the remaining URI is what you have to care about"

    If this arg is not set, server assumes that the name of the physical path
    to repo folder relative to _content_path starts immediately after first slash.
    Example:
        if _content_path = c:\tmp\our_repos_root
        URI http://server:port/userjoe/joes_repo_one.git
        Would mean to reference an actual phisical folder:
            c:\tmp\our_repos_root\userjoe\joes_repo_one.git

    URI marker is useful in specific cases when it's important to have the git
    server host the app on a non-root folder.
    (Example, _uri_marker was set to "myrepos" vs. "":
        http://server/any/random/pre-path/here/myrepos/repofoler.git
        vs. http://server/repofoler.git)

    This functionality is important for cases when this Git Smart HTTP server
    is hiding behind a reverse proxy (IIS's ApplicationRequestRouting, nginx etc.)
    and you want an easy way to "mount" this git server on top of present site
    structure, while still hosting this server on a separate machine or port.

    One word of caution about reverse proxy, though. This server and the git client
    talk HTTP/1.1, chunked bodies, once the pack size goes up above 1Mb.
    For efficiency of communication, please, try to stick to fully HTTP/1.1
    compliant reverse proxies. NGINX is only HTTP/1.0 on the inside of reverse
    proxy. HTTP/1.0 proxies are not a deal-breaker, but, test and retest them
    before going production.
    '''

    if not _content_path or _content_path == "CHANGE ME!":
        _content_path = tempfile.mkdtemp()
        _using_temporary_folder = ', repo dir will self-destruct'
    else:
        _using_temporary_folder = ''

    if _uri_marker:
        _s = ', URI marker "/%s/"' % _uri_marker
    else:
        _s = ', no URI marker'
    _svc_display_name_ = "Git Smart HTTP Server - port %s%s%s." % (
            _server_port, _s, _using_temporary_folder)

    _server_instance = None

    def SvcDoRun(self):

        app = git_http_backend.assemble_WSGI_git_app(
            content_path = self._content_path,
            uri_marker = self._uri_marker
            # on push, nonexistent repos are autocreated by default.
            # uncomment 3 lines below to stop that.
#            ,repo_auto_create = False
        )
        self._server_instance = wsgiserver.CherryPyWSGIServer(
                (self._server_ip, self._server_port),
                app
            )
        try:
            self._server_instance.start()
        except KeyboardInterrupt:
            # i know this will never happen. That's the point.
            # all other exceptions will bubble up, somewhere... i hope...
            pass
        finally:
            self._server_instance.stop()

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        if self._server_instance:
            self._server_instance.stop()
        if self._using_temporary_folder:
            shutil.rmtree(self._content_path, True)
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)
        # very important for use with py2exe
        # otherwise the Service Controller never knows that it is stopped !

if __name__ == '__main__':
    # s = GitSmartHTTPServer()
    # s.SvcDoRun()
    win32serviceutil.HandleCommandLine(GitSmartHTTPServer)

########NEW FILE########
__FILENAME__ = git_http_backend
#!/usr/bin/env python
'''
Module provides WSGI-based methods for handling HTTP Get and Post requests that
are specific only to git-http-backend's Smart HTTP protocol.

See __version__ statement below for indication of what version of Git's
Smart HTTP server this backend is (designed to be) compatible with.

Copyright (c) 2010  Daniel Dotsenko <dotsa@hotmail.com>
Selected, specifically marked so classes are also
  Copyright (C) 2006 Luke Arno - http://lukearno.com/

This file is part of git_http_backend.py Project.

git_http_backend.py Project is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 2.1 of the License, or
(at your option) any later version.

git_http_backend.py Project is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with git_http_backend.py Project.  If not, see <http://www.gnu.org/licenses/>.
'''
import io
import os
import sys
import gzip
import StringIO

import subprocess
import subprocessio

import tempfile
from wsgiref.headers import Headers

# needed for WSGI Selector
import re
import urlparse
from collections import defaultdict

# needed for static content server
import time
import email.utils
import mimetypes
mimetypes.add_type('application/x-git-packed-objects-toc','.idx')
mimetypes.add_type('application/x-git-packed-objects','.pack')

__version__=(1,7,0,4) # the number has no significance for this code's functionality.
# The number means "I was looking at sources of that version of Git while coding"

class BaseWSGIClass(object):
    bufsize = 65536
    gzip_response = False
    canned_collection = {
        '304': '304 Not Modified',
        'not_modified': '304 Not Modified',
        '301': '301 Moved Permanently',
        'moved': '301 Moved Permanently',
        '400':'400 Bad request',
        'bad_request':'400 Bad request',
        '401':'401 Access denied',
        'access_denied':'401 Access denied',
        '401.4': '401.4 Authorization failed by filter',
        '403':'403 Forbidden',
        'forbidden':'403 Forbidden',
        '404': "404 Not Found",
        'not_found': "404 Not Found",
        '405': "405 Method Not Allowed",
        'method_not_allowed': "405 Method Not Allowed",
        '417':'417 Execution failed',
        'execution_failed':'417 Execution failed',
        '200': "200 OK",
        '501': "501 Not Implemented",
        'not_implemented': "501 Not Implemented"
    }

    def canned_handlers(self, environ, start_response, code = '200', headers = []):
        '''
        We convert an error code into
        certain action over start_response and return a WSGI-compliant payload.
        '''
        headerbase = [('Content-Type', 'text/plain')]
        if headers:
            hObj = Headers(headerbase)
            for header in headers:
                hObj[header[0]] = '; '.join(header[1:])
        start_response(self.canned_collection[code], headerbase)
        return ['']

    def package_response(self, outIO, environ, start_response, headers = []):

        newheaders = headers
        headers = [('Content-type', 'application/octet-stream')] # my understanding of spec. If unknown = binary
        headersIface = Headers(headers)

        for header in newheaders:
            headersIface[header[0]] = '; '.join(header[1:])

        if hasattr(outIO,'fileno') and 'wsgi.file_wrapper' in environ:
            outIO.seek(0)
            retobj = environ['wsgi.file_wrapper']( outIO, self.bufsize )
        elif hasattr(outIO,'read'):
            outIO.seek(0)
            retobj = iter( lambda: outIO.read(self.bufsize), '' )
        else:
            retobj = outIO
        start_response("200 OK", headers)
        return retobj

class WSGIHandlerSelector(BaseWSGIClass):
    """
    WSGI middleware for URL paths and HTTP method based delegation.

    This middleware is commonly called a "selector" or "router."

    Features:

    Regex-based patterns:
    Normally these are implemented as meta-url-language-to-regex
    translators, where you describe a URI matching pattern in
    URI-looking way, with regex-like pattern group name areas.
    These later are converted to plain regex by the selector's code.
    Since you need to learn that meta-URI-matching-language and
    have the usual routers translate those to regex, I have decided
    to cut out the middle-man and just define the URI patterns in
    regex from the start.
    This way a WSGI app programmer needs to learn only one meta-URI-matching
    language - standard Python regex. Thus, the insanity should stop here.

    Support for matching based on HTTP verb:
    Want to handle POSTs and GETs on the same URI by different wsgi app? Sure!

    Support for routing based on URI query parameters:
    Want "host/app?special_arg=value" to be routed to different wsgi app
    compared to "host/app?other_arg=value" or "host/app"? Sure!

    See documentation for .add() method for examples.

    Based on Selector from http://lukearno.com/projects/selector/

    Copyright (c) 2010 Daniel Dotsenko <dotsa@hotmail.com>
    Copyright (C) 2006 Luke Arno - http://lukearno.com/
    """

    def __init__(self, WSGI_env_key = 'WSGIHandlerSelector'):
        """
        WSGIHandlerSelector instance initializer.

        WSGIHandlerSelector(WSGI_env_key = 'WSGIHandlerSelector')

        Inputs:
         WSGI_env_key (optional)
          name of the key selector injects into WSGI's environ.
          The key will be the base for other dicts, like .matches - the key-value pairs of
          name-matchedtext matched groups. Defaults to 'WSGIHandlerSelector'
        """
        self.mappings = []
        self.WSGI_env_key = WSGI_env_key

    def add(self, path, default_handler = None, **http_methods):
        """
        Add a selector mapping.

        add(path, default_handler, **named_handlers)

        Adding order is important. Firt added = first matched.
        If you want to hand special case URI handled by one app and shorter
        version of the same regex string by anoter app,
        .add() special case first.

        Inputs:
         path - A regex string. We will compile it.
          Highly recommend using grouping of type: "(?P<groupname>.+)"
          These will be exposed to WSGI app through environment key
          per http://www.wsgi.org/wsgi/Specifications/routing_args

         default_handler - (optional) A pointer to the function / iterable
          class instance that will handle ALL HTTP methods (verbs)

         **named_handlers - (optional) An unlimited list of named args or
          an unpacked dict of handlers allocated to handle specific HTTP
          methods (HTTP verbs). See "Examples" below.

        Matched named method handlers override default handler.

        If neither default_handler nor named_handlers point to any methods,
        "Method not implemented" is returned for the requests on this URI.

        Examples:
        selectorInstance.add('^(?P<working_path>.*)$',generic_handler,
                              POST=post_handler, HEAD=head_handler)

        custom_assembled_dict = {'GET':wsgi_app_a,'POST':wsgi_app_b}:
        ## note the unpacking - "**" - of the dict in this case.
        selectorInstance.add('^(?P<working_path>.*)$', **custom_assembled_dict)


        If the string contains '\?' (escaped ?, which translates to '?' in
        non-regex strings) we understand that as "do regex matching on
        QUERY_PATH + '?' + QUERY_STRING"

        When lookup matches are met, results are injected into
        environ['wsgiorg.routing_args'] per
        http://www.wsgi.org/wsgi/Specifications/routing_args
        """
        if default_handler:
            methods = defaultdict(lambda: default_handler, http_methods.copy())
        else:
            methods = http_methods.copy()
        self.mappings.append((re.compile(path.decode('utf8')), methods, (path.find(r'\?')>-1) ))

    def __call__(self, environ, start_response):
        """
        Delegate request to the appropriate WSGI app.

        The following keys will be added to the WSGI's environ:

        wsgiorg.routing_args
            It's a tuple of a list and a dict. The structure is per this spec:
            http://www.wsgi.org/wsgi/Specifications/routing_args

        WSGIHandlerSelector.matched_request_methods
            It's a list of strings denoting other HTTP verbs / methods the
            matched URI (not chosen handler!) accepts for processing.
            This matters when

        """

        path = environ.get('PATH_INFO', '').decode('utf8')

        matches = None
        handler = None
        alternate_HTTP_verbs = set()
        query_string = (environ.get('QUERY_STRING') or '')

        # sanitizing the path:
        # turns garbage like this: r'//qwre/asdf/..*/*/*///.././../qwer/./..//../../.././//yuioghkj/../wrt.sdaf'
        # into something like this: /../../wrt.sdaf
        path = urlparse.urljoin(u'/', re.sub('//+','/',path.strip('/')))
        if not path.startswith('/../'): # meaning, if it's not a trash path
            for _regex, _registered_methods, _use_query_string in self.mappings:
                if _use_query_string:
                    matches = _regex.search(path + '?' + query_string)
                else:
                    matches = _regex.search(path)
                if matches:
                    # note, there is a chance that '_registered_methods' is an instance of
                    # collections.defaultdict, which means if default handler was
                    # defined it will be returned for all unmatched HTTP methods.
                    handler = _registered_methods[environ.get('REQUEST_METHOD','')]
                    if handler:
                        break
                    else:
                        alternate_HTTP_verbs.update(_registered_methods.keys())
        if handler:
            environ['PATH_INFO'] = path.encode('utf8')

            mg = list(environ.get('wsgiorg.routing_args') or ([],{}))
            mg[0] = list(mg[0]).append(matches.groups()),
            mg[1].update(matches.groupdict())
            environ['wsgiorg.routing_args'] = tuple(mg)

            return handler(environ, start_response)
        elif alternate_HTTP_verbs:
            # uugh... narrow miss. Regex matched some path, but the method was off.
            # let's advertize what methods we can do with this URI.
            return self.canned_handlers(
                environ,
                start_response,
                'method_not_allowed',
                headers = [('Allow', ', '.join(alternate_HTTP_verbs))]
                )
        else:
            return self.canned_handlers(environ, start_response, 'not_found')

class StaticWSGIServer(BaseWSGIClass):
    """
    Copyright (c) 2010  Daniel Dotsenko <dotsa@hotmail.com>
    Copyright (C) 2006 Luke Arno - http://lukearno.com/

    A simple WSGI-based static content server app.

    Relies on WSGIHandlerSelector for prepopulating some needed environ
    variables, cleaning up the URI, setting up default error handlers.
    """

    def __init__(self, **kw):
        '''
        Inputs:
            content_path (mandatory)
                String containing a file-system level path behaving as served root.

            bufsize (optional)
                File reader's buffer size. Defaults to 65536.

            gzip_response (optional) (must be named arg)
                Specify if we are to detect if gzip compression is supported
                by client and gzip the output. False by default.
        '''
        self.__dict__.update(kw)

    def __call__(self, environ, start_response):
        selector_matches = (environ.get('wsgiorg.routing_args') or ([],{}))[1]
        if 'working_path' in selector_matches:
            # working_path is a custom key that I just happened to decide to use
            # for marking the portion of the URI that is palatable for static serving.
            # 'working_path' is the name of a regex group fed to WSGIHandlerSelector
            path_info = selector_matches['working_path'].decode('utf8')
        else:
            path_info = environ.get('PATH_INFO', '').decode('utf8')

        # this, i hope, safely turns the relative path into OS-specific, absolute.
        full_path = os.path.abspath(os.path.join(self.content_path, path_info.strip('/')))
        _pp = os.path.abspath(self.content_path)

        if not full_path.startswith(_pp):
            return self.canned_handlers(environ, start_response, 'forbidden')
        if not os.path.isfile(full_path):
            return self.canned_handlers(environ, start_response, 'not_found')

        mtime = os.stat(full_path).st_mtime
        etag, last_modified =  str(mtime), email.utils.formatdate(mtime)
        headers = [
            ('Content-type', 'text/plain'),
            ('Date', email.utils.formatdate(time.time())),
            ('Last-Modified', last_modified),
            ('ETag', etag)
        ]
        headersIface = Headers(headers)
        headersIface['Content-Type'] = mimetypes.guess_type(full_path)[0] or 'application/octet-stream'

        if_modified = environ.get('HTTP_IF_MODIFIED_SINCE')
        if if_modified and (email.utils.parsedate(if_modified) >= email.utils.parsedate(last_modified)):
            return self.canned_handlers(environ, start_response, 'not_modified', headers)
        if_none = environ.get('HTTP_IF_NONE_MATCH')
        if if_none and (if_none == '*' or etag in if_none):
            return self.canned_handlers(environ, start_response, 'not_modified', headers)

        file_like = open(full_path, 'rb')
        return self.package_response(file_like, environ, start_response, headers)

class GitHTTPBackendBase(BaseWSGIClass):
    git_folder_signature = set(['config', 'head', 'info', 'objects', 'refs'])
    repo_auto_create = True

    def has_access(self, **kw):
        '''
        User rights verification code.
        (This is NOT an authentication code. The authentication is handled by
        the server that hosts this WSGI app. We just go by the name of the
        already-authenticated user.
        '''
        return True

    def basic_checks(self, dataObj, environ, start_response):
        '''
        This function is shared by GitInfoRefs and SmartHTTPRPCHandler WSGI classes.
        It does the same basic steps - figure out working path, git command etc.

        dataObj - dictionary
        Because the dataObj passed in is mutable, it's a pointer. Once this function returns,
        this object, as created by calling class, will have the free-form updated data.

        Returns non-None object if an error was triggered (and already prepared in start_response).
        '''
        selector_matches = (environ.get('wsgiorg.routing_args') or ([],{}))[1]

        # making sure we have a compatible git command
        git_command = selector_matches.get('git_command') or ''
        if git_command not in ['git-upload-pack', 'git-receive-pack']: # TODO: this is bad for future compatibility. There may be more commands supported then.
            return self.canned_handlers(environ, start_response, 'bad_request')

        # TODO: Add "public" to "dynamic local" path conversion hook ups here.

        #############################################################
        # making sure local path is a valid git repo folder
        #
        repo_path = os.path.abspath(
            os.path.join(
                self.content_path,
                (selector_matches.get('working_path') or '').decode('utf8').strip('/').strip('\\')
                )
            )
        _pp = os.path.abspath(self.content_path)

        # this saves us from "hackers" putting relative paths after repo marker.
        if not repo_path.startswith(_pp):
            return self.canned_handlers(environ, start_response, 'forbidden')

        if not self.has_access(
            environ = environ,
            repo_path = repo_path,
            git_command = git_command
            ):
            return self.canned_handlers(environ, start_response, 'forbidden')

        try:
            files = os.listdir(repo_path)
        except:
            files = []
        if not self.git_folder_signature.issubset([i.lower() for i in files]):
            if not ( self.repo_auto_create and git_command == 'git-receive-pack' ):
                return self.canned_handlers(environ, start_response, 'not_found')
            else:
                # 1. traverse entire post-prefix path and check that each segment
                #    If it is ( a git folder OR a non-dir object ) forbid autocreate
                # 2. Create folderS
                # 3. Activate a bare git repo
                _pf = _pp
                _dirs = repo_path[len(_pp):].strip(os.sep).split(os.sep) or ['']
                for _dir in _dirs:
                    _pf = os.path.join(_pf,_dir)
                    if not os.path.exists(_pf):
                        try:
                            os.makedirs(repo_path)
                        except:
                            return self.canned_handlers(environ, start_response, 'not_found')
                        break
                    elif not os.path.isdir(_pf) or self.git_folder_signature.issubset([i.lower() for i in os.listdir(_pf)]):
                        return self.canned_handlers(environ, start_response, 'forbidden')
                if subprocess.call('git init --quiet --bare "%s"' % repo_path, shell=True):
                    return self.canned_handlers(environ, start_response, 'execution_failed')
        #
        #############################################################

        dataObj['git_command'] = git_command
        dataObj['repo_path'] = repo_path
        return None

class GitHTTPBackendInfoRefs(GitHTTPBackendBase):
    '''
    Implementation of a WSGI handler (app) specifically capable of responding
    to git-http-backend (Git Smart HTTP) /info/refs call over HTTP GET.

    This is the fist step in the RPC dialog. We have to reply with right content
    to show to Git client that we are an "intelligent" server.

    The "right" content is special header and custom top 2 rows of data in the response.
    '''
    def __init__(self, **kw):
        '''
        inputs:
            content_path (Mandatory) - Local file system path = root of served files.
            bufsize (Default = 65536) Chunk size for WSGI file feeding
            gzip_response (Default = False) Compress response body
        '''
        self.__dict__.update(kw)

    def __call__(self, environ, start_response):
        """WSGI Response producer for HTTP GET Git Smart HTTP /info/refs request."""

        dataObj = {}
        answer = self.basic_checks(dataObj, environ, start_response)
        if answer:
            # non-Null answer = there was an issue in basic_checks and it's time to return an HTTP error response
            return answer
        git_command = dataObj['git_command']
        repo_path = dataObj['repo_path']

        # note to self:
        # please, resist the urge to add '\n' to git capture and increment line count by 1.
        # The code in Git client not only does NOT need '\n', but actually blows up
        # if you sprinkle "flush" (0000) as "0001\n".
        # It reads binary, per number of bytes specified.
        # if you do add '\n' as part of data, count it.
        smart_server_advert = '# service=%s' % git_command

        try:
            out = subprocessio.SubprocessIOChunker(
                r'git %s --stateless-rpc --advertise-refs "%s"' % (git_command[4:], repo_path),
                starting_values = [ str(hex(len(smart_server_advert)+4)[2:].rjust(4,'0') + smart_server_advert + '0000') ]
                )
        except (EnvironmentError) as e:
            environ['wsgi.errors'].write(str(e))
            return self.canned_handlers(environ, start_response, 'execution_failed')
#        except Exception as e:
#            environ['wsgi.errors'].write(str(e))
#            return self.canned_handlers(environ, start_response, 'internal_server_error')

        headers = [('Content-type','application/x-%s-advertisement' % str(git_command))]
        return self.package_response(
            out,
            environ,
            start_response,
            headers)

class GitHTTPBackendSmartHTTP(GitHTTPBackendBase):
    '''
    Implementation of a WSGI handler (app) specifically capable of responding
    to git-http-backend (Git Smart HTTP) RPC calls sent over HTTP POST.

    This is a layer that responds to HTTP POSTs to URIs like:
        /repo_folder_name/git-upload-pack?service=upload-pack (or same for receive-pack)

    This is a second step in the RPC dialog. Another handler for HTTP GETs to
    /repo_folder_name/info/refs (as implemented in a separate WSGI handler below)
    must reply in a specific way in order for the Git client to decide to talk here.
    '''
    def __init__(self, **kw):
        '''
        content_path
            Local file system path = root of served files.
        optional parameters may be passed as named arguments
            These include
                bufsize (Default = 65536) Chunk size for WSGI file feeding
                gzip_response (Default = False) Compress response body
        '''
        self.__dict__.update(kw)

    def __call__(self, environ, start_response):
        """
        WSGI Response producer for HTTP POST Git Smart HTTP requests.
        Reads commands and data from HTTP POST's body.
        returns an iterator obj with contents of git command's response to stdout
        """
        # 1. Determine git_command, repo_path
        # 2. Determine IN content (encoding)
        # 3. prepare OUT content (encoding, header)

        dataObj = {}
        answer = self.basic_checks(dataObj, environ, start_response)
        if answer:
            # this is a WSGI "trick". basic_checks have already prepared the headers,
            # and a response body (which is the 'answer') returned here.
            # presense of anything of truthiness in 'answer' = some ERROR have
            # already prepared a response and all I need to do is let go of the response.
            return answer

        git_command = dataObj['git_command']
        repo_path = dataObj['repo_path']

        # Note, depending on the WSGI server, the following handlings of chunked
        # request bodies are possible:
        # 1. This is strict PEP333-only compliant server. wsgi.input.read() is bottomless
        #    and Content-Length is absent.
        #    If WSGI app is assuming no size header = size header is Zero, app will respond with wrong data.
        #    (this code is not assuming None = zero data. We look deeper)
        #    If WSGI app is chunked-aware, but respects WSGI 1.0 only,
        #    it will reply with "501 Not Implemented"
        # 2. This is PEP333-compliant server that tries to accommodate Transfer-Encoding: chunked
        #    requests by caching the body and presenting it as wsgi.input file-like.
        #    Content-Length header is set to captured size and Transfer-Encoding
        #    header is removed. This is not per WSGI 1.0 spec, but is a good thing to do.
        #    All WSGI 1.x apps are happy.
        # 3. This is PEP3333 compliant server that presents Transfer-Encoding: chunked
        #    requests as a file-like that yields an EOF at the end.
        #    Content-Length header is NOT set.
        #    Only WSGI 1.1 apps are happy. WSGI 1.0 apps are confused by lack of
        #    content-length header and blow up. (We are WSGI 1.1 app)

        # any WSGI server that claims to be HTTP/1.1 compliant must deal with chunked
        # If not #3 above, then #2 would be done by a self-respecting HTTP/1.1 server.
        
        # everywhere lower, we just assume we deal with PEP3333-compliant server.
        # there wsgi.input generated EOF, so we don't have to care about content length.

        stdin = environ.get('wsgi.input')

        try:
            # Git's curl client can on occasion be instructed to gzip the contents,
            # when they are not naturally gzipped by git stream generator.
            # in that case, CGI vars will have HTTP_ACCEPT_ENCODING set to 'gzip' (or 'x-gzip')
            # This usually happens when git client asks for "clone" or "fetch" by giving a list
            # of hashes to send to it. That list is binary text and Git's HTTP client code compresses it by hand.
            # If our server did not transparently decode the body yet (and removed the HTTP_ACCEPT_ENCODING)
            # we will do it manually:
            if environ.get('HTTP_CONTENT_ENCODING','') in ['gzip', 'x-gzip']:
                # since we have decoded it, it's no longer true.
                # del environ['HTTP_CONTENT_ENCODING']
                tmpfile = StringIO.StringIO(stdin.read())
                stdin = gzip.GzipFile(fileobj = tmpfile).read()
                tmpfile.close()
                del tmpfile
                # environ['wsgi.errors'].write('stdin is "%s"\n' % stdin)
                # environ['CONTENT_LENGTH'] = str(len(stdin))

            out = subprocessio.SubprocessIOChunker(
                r'git %s --stateless-rpc "%s"' % (git_command[4:], repo_path),
                inputstream = stdin
                )
        except (EnvironmentError) as e:
            environ['wsgi.errors'].write(str(e))
            return self.canned_handlers(environ, start_response, 'execution_failed')
        except (Exception) as e:
            environ['wsgi.errors'].write(str(e))
            raise e

        if git_command == u'git-receive-pack':
            # updating refs manually after each push. Needed for pre-1.7.0.4 git clients using regular HTTP mode.
            subprocess.call(u'git --git-dir "%s" update-server-info' % repo_path, shell=True)

        headers = [('Content-type', 'application/x-%s-result' % git_command.encode('utf8'))]
        return self.package_response(
            out,
            environ,
            start_response,
            headers)

def assemble_WSGI_git_app(*args, **kw):
    '''
    Assembles basic WSGI-compatible application providing functionality of git-http-backend.

    content_path (Defaults to '.' = "current" directory)
        The path to the folder that will be the root of served files. Accepts relative paths.

    uri_marker (Defaults to '')
        Acts as a "virtual folder" separator between decorative URI portion and
        the actual (relative to content_path) path that will be appended to
        content_path and used for pulling an actual file.

        the URI does not have to start with contents of uri_marker. It can
        be preceeded by any number of "virtual" folders. For --uri_marker 'my'
        all of these will take you to the same repo:
            http://localhost/my/HEAD
            http://localhost/admysf/mylar/zxmy/my/HEAD
        This WSGI hanlder will cut and rebase the URI when it's time to read from file system.

        Default of '' means that no cutting marker is used, and whole URI after FQDN is
        used to find file relative to content_path.

    returns WSGI application instance.
    '''

    default_options = [
        ['content_path','.'],
        ['uri_marker','']
    ]
    args = list(args)
    options = dict(default_options)
    options.update(kw)
    while default_options and args:
        _d = default_options.pop(0)
        _a = args.pop(0)
        options[_d[0]] = _a
    options['content_path'] = os.path.abspath(options['content_path'].decode('utf8'))
    options['uri_marker'] = options['uri_marker'].decode('utf8')

    selector = WSGIHandlerSelector()
    generic_handler = StaticWSGIServer(**options)
    git_inforefs_handler = GitHTTPBackendInfoRefs(**options)
    git_rpc_handler = GitHTTPBackendSmartHTTP(**options)

    if options['uri_marker']:
        marker_regex = r'(?P<decorative_path>.*?)(?:/'+ options['uri_marker'] + ')'
    else:
        marker_regex = ''

    selector.add(
        marker_regex + r'(?P<working_path>.*?)/info/refs\?.*?service=(?P<git_command>git-[^&]+).*$',
        GET = git_inforefs_handler,
        HEAD = git_inforefs_handler
        )
    selector.add(
        marker_regex + r'(?P<working_path>.*)/(?P<git_command>git-[^/]+)$',
        POST = git_rpc_handler
        )
    selector.add(
        marker_regex + r'(?P<working_path>.*)$',
        GET = generic_handler,
        HEAD = generic_handler)

    return selector

#class ShowVarsWSGIApp(object):
#    def __init__(self, *args, **kw):
#        pass
#    def __call__(self, environ, start_response):
#        status = '200 OK'
#        response_headers = [('Content-type','text/plain')]
#        start_response(status, response_headers)
#        for key in sorted(environ.keys()):
#            yield '%s = %s\n' % (key, unicode(environ[key]).encode('utf8'))

if __name__ == "__main__":
    _help = r'''
git_http_backend.py - Python-based server supporting regular and "Smart HTTP"
	
Note only the folder that contains folders and object that you normally see
in .git folder is considered a "repo folder." This means that either a
"bare" folder name or a working folder's ".git" folder will be a "repo" folder
discussed in the examples below.

When "repo-auto-create on Push" is used, the server automatically creates "bare"
repo folders.

Note, the folder does NOT have to have ".git" in the name to be a "repo" folder.
You can name bare repo folders whatever you like. If the signature (right files
and folders are found inside) matches a typical git repo, it's a "repo."

Options:
--content_path (Defaults to '.' - current directory)
	Serving contents of folder path passed in. Accepts relative paths,
	including things like "./../" and resolves them agains current path.

	If you set this to actual .git folder, you don't need to specify the
	folder's name on URI.

--uri_marker (Defaults to '')
	Acts as a "virtual folder" - separator between decorative URI portion
	and the actual (relative to content_path) path that will be appended
	to content_path and used for pulling an actual file.

	the URI does not have to start with contents of uri_marker. It can
	be preceeded by any number of "virtual" folders.
	For --uri_marker 'my' all of these will take you to the same repo:
		http://localhost/my/HEAD
		http://localhost/admysf/mylar/zxmy/my/HEAD
	If you are using reverse proxy server, pick the virtual, decorative URI
	prefix / path of your choice. This hanlder will cut and rebase the URI.

	Default of '' means that no cutting marker is used, and whole URI after
	FQDN is used to find file relative to content_path.

--port (Defaults to 8080)

Examples:

cd c:\myproject_workingfolder\.git
c:\tools\git_http_backend\GitHttpBackend.py --port 80
	(Current path is used for serving.)
	This project's repo will be one and only served directly over
	 http://localhost/

cd c:\repos_folder
c:\tools\git_http_backend\GitHttpBackend.py 
	(note, no options are provided. Current path is used for serving.)
	If the c:\repos_folder contains repo1.git, repo2.git folders, they 
	become available as:
	 http://localhost:8080/repo1.git  and  http://localhost:8080/repo2.git

~/myscripts/GitHttpBackend.py --content_path "~/somepath/repofolder" --uri_marker "myrepo"
	Will serve chosen repo folder as http://localhost/myrepo/ or
	http://localhost:8080/does/not/matter/what/you/type/here/myrepo/
	This "repo uri marker" is useful for making a repo server appear as a
	part of some REST web application or make it appear as a part of server
	while serving it from behind a reverse proxy.

./GitHttpBackend.py --content_path ".." --port 80
	Will serve the folder above the "git_http_backend" (in which 
	GitHttpBackend.py happened to be located.) A functional url could be
	 http://localhost/git_http_backend/GitHttpBackend.py
	Let's assume the parent folder of git_http_backend folder has a ".git"
	folder. Then the repo could be accessed as:
	 http://localhost/.git/
	This allows GitHttpBackend.py to be "self-serving" :)
'''
    import sys

    command_options = {
            'content_path' : '.',
            'uri_marker' : '',
            'port' : '8080'
        }
    lastKey = None
    for item in sys.argv:
        if item.startswith('--'):
            command_options[item[2:]] = True
            lastKey = item[2:]
        elif lastKey:
            command_options[lastKey] = item.strip('"').strip("'")
            lastKey = None

    content_path = os.path.abspath( command_options['content_path'] )

    if 'help' in command_options:
        print _help
    else:
        app = assemble_WSGI_git_app(
            content_path = content_path,
            uri_marker = command_options['uri_marker'],
            performance_settings = {
                'repo_auto_create':True
                }
        )

        # default Python's WSGI server. Replace with your choice of WSGI server
        import cherrypy as wsgiserver
        httpd = wsgiserver.CherryPyWSGIServer(('0.0.0.0',int(command_options['port'])),app)

        if command_options['uri_marker']:
            _s = '"/%s/".' % command_options['uri_marker']
            example_URI = '''http://localhost:%s/whatever/you/want/here/%s/myrepo.git
    (Note: "whatever/you/want/here" cannot include the "/%s/" segment)''' % (
            command_options['port'],
            command_options['uri_marker'],
            command_options['uri_marker'])
        else:
            _s = 'not chosen.'
            example_URI = 'http://localhost:%s/myrepo.git' % (command_options['port'])
        print '''
===========================================================================
Run this command with "--help" option to see available command-line options

Starting git-http-backend server...
	Port: %s
	Chosen repo folders' base file system path: %s
	URI segment indicating start of git repo foler name is %s

Example repo url would be:
    %s

Use Keyboard Interrupt key combination (usually CTRL+C) to stop the server
===========================================================================
''' % (command_options['port'], content_path, _s, example_URI)

        try:
            httpd.start()
        except KeyboardInterrupt:
            pass
        finally:
            httpd.stop()

########NEW FILE########
__FILENAME__ = subprocessio
#!/usr/bin/env python
'''
Module provides a class allowing to wrap communication over subprocess.Popen
input, output, error streams into a meaningfull, non-blocking, concurrent stream
processor exposing the output data as an iterator fitting to be a return value
passed by a WSGI applicaiton to a WSGI server per PEP 3333.

Copyright (c) 2011  Daniel Dotsenko <dotsa@hotmail.com>

This file is part of git_http_backend.py Project.

git_http_backend.py Project is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 2.1 of the License, or
(at your option) any later version.

git_http_backend.py Project is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with git_http_backend.py Project.  If not, see <http://www.gnu.org/licenses/>.
'''

from collections import deque
import threading
import subprocess
import os

class StreamFeeder(threading.Thread):
    """
    Normal writing into pipe-like is blocking once the buffer is filled.
    This thread allows a thread to seep data from a file-like into a pipe
    without blocking the main thread.
    We close inpipe once the end of the source stream is reached.
    """
    def __init__(self, source):
        super(StreamFeeder,self).__init__()
        self.daemon = True
        filelike = False
        self.bytes = b''
        if type(source) in (type(''),bytes,bytearray): # string-like
            self.bytes = bytes(source)
        else: # can be either file pointer or file-like
            if type(source) in (int, long): # file pointer it is
                ## converting file descriptor (int) stdin into file-like
                try:
                    source = os.fdopen(source, 'rb', 16384)
                except:
                    pass
            # let's see if source is file-like by now
            try:
                filelike = source.read
            except:
                pass
        if not filelike and not self.bytes:
            raise TypeError("StreamFeeder's source object must be a readable file-like, a file descriptor, or a string-like.")
        self.source = source
        self.readiface, self.writeiface = os.pipe()

    def run(self):
        t = self.writeiface
        if self.bytes:
            os.write(t, self.bytes)
        else:
            s = self.source
            b = s.read(4096)
            while b:
                os.write(t, b)
                b = s.read(4096)
        os.close(t)

    @property
    def output(self):
        return self.readiface

class InputStreamChunker(threading.Thread):
    def __init__(self, source, target, buffer_size, chunk_size):

        super(InputStreamChunker,self).__init__()

        self.daemon = True # die die die.

        self.source = source
        self.target = target
        self.chunk_count_max = int(buffer_size / chunk_size) + 1
        self.chunk_size = chunk_size

        self.data_added = threading.Event()
        self.data_added.clear()

        self.keep_reading = threading.Event()
        self.keep_reading.set()

        self.EOF = threading.Event()
        self.EOF.clear()

        self.go = threading.Event()
        self.go.set()

    def stop(self):
        self.go.clear()
        self.EOF.set()
        try:
            # this is not proper, but is done to force the reader thread let go of
            # the input because, if successful, .close() will send EOF down the pipe.
            self.source.close()
        except:
            pass

    def run(self):
        s = self.source
        t = self.target
        cs = self.chunk_size
        ccm = self.chunk_count_max
        kr = self.keep_reading
        da = self.data_added
        go = self.go
        b = s.read(cs)
        while b and go.is_set():
            if len(t) > ccm:
                kr.clear()
                kr.wait(2)
#                # this only works on 2.7.x and up
#                if not kr.wait(10):
#                    raise Exception("Timed out while waiting for input to be read.")
                # instead we'll use this
                if len(t) > ccm + 3:
                    raise IOError("Timed out while waiting for input from subprocess.")
            t.append(b)
            da.set()
            b = s.read(cs)
        self.EOF.set()
        da.set() # for cases when done but there was no input.

class BufferedGenerator():
    '''
    Class behaves as a non-blocking, buffered pipe reader.
    Reads chunks of data (through a thread)
    from a blocking pipe, and attaches these to an array (Deque) of chunks.
    Reading is halted in the thread when max chunks is internally buffered.
    The .next() may operate in blocking or non-blocking fashion by yielding
    '' if no data is ready
    to be sent or by not returning until there is some data to send
    When we get EOF from underlying source pipe we raise the marker to raise
    StopIteration after the last chunk of data is yielded.
    '''

    def __init__(self, source, buffer_size = 65536, chunk_size = 4096, starting_values = [], bottomless = False):

        if bottomless:
            maxlen = int(buffer_size / chunk_size)
        else:
            maxlen = None

        self.data = deque(starting_values, maxlen)

        self.worker = InputStreamChunker(source, self.data, buffer_size, chunk_size)
        if starting_values:
            self.worker.data_added.set()
        self.worker.start()

    ####################
    # Generator's methods
    ####################

    def __iter__(self):
        return self

    def next(self):
        while not len(self.data) and not self.worker.EOF.is_set():
            self.worker.data_added.clear()
            self.worker.data_added.wait(0.2)
        if len(self.data):
            self.worker.keep_reading.set()
            return bytes(self.data.popleft())
        elif self.worker.EOF.is_set():
            raise StopIteration

    def throw(self, type, value=None, traceback=None):
        if not self.worker.EOF.is_set():
            raise type(value)

    def start(self):
        self.worker.start()

    def stop(self):
        self.worker.stop()

    def close(self):
        try:
            self.worker.stop()
            self.throw(GeneratorExit)
        except (GeneratorExit, StopIteration):
            pass

    def __del__(self):
        self.close()

    ####################
    # Threaded reader's infrastructure.
    ####################
    @property
    def input(self):
        return self.worker.w

    @property
    def data_added_event(self):
        return self.worker.data_added
    @property
    def data_added(self):
        return self.worker.data_added.is_set()

    @property
    def reading_paused(self):
        return not self.worker.keep_reading.is_set()

    @property
    def done_reading_event(self):
        '''
        Done_reding does not mean that the iterator's buffer is empty.
        Iterator might have done reading from underlying source, but the read
        chunks might still be available for serving through .next() method.

        @return An Event class instance.
        '''
        return self.worker.EOF
    @property
    def done_reading(self):
        '''
        Done_reding does not mean that the iterator's buffer is empty.
        Iterator might have done reading from underlying source, but the read
        chunks might still be available for serving through .next() method.

        @return An Bool value.
        '''
        return self.worker.EOF.is_set()

    @property
    def length(self):
        '''
        returns int.

        This is the lenght of the que of chunks, not the length of
        the combined contents in those chunks.

        __len__() cannot be meaningfully implemented because this
        reader is just flying throuh a bottomless pit content and
        can only know the lenght of what it already saw.

        If __len__() on WSGI server per PEP 3333 returns a value,
        the responce's length will be set to that. In order not to
        confuse WSGI PEP3333 servers, we will not implement __len__
        at all.
        '''
        return len(self.data)

    def prepend(self, x):
        self.data.appendleft(x)

    def append(self, x):
        self.data.append(x)

    def extend(self, o):
        self.data.extend(o)

    def __getitem__(self, i):
        return self.data[i]

class SubprocessIOChunker():
    '''
    Processor class wrapping handling of subprocess IO.

    In a way, this is a "communicate()" replacement with a twist.

    - We are multithreaded. Writing in and reading out, err are all sep threads.
    - We support concurrent (in and out) stream processing.
    - The output is not a stream. It's a queue of read string (bytes, not unicode)
      chunks. The object behaves as an iterable. You can "for chunk in obj:" us.
    - We are non-blocking in more respects than communicate()
      (reading from subprocess out pauses when internal buffer is full, but
       does not block the parent calling code. On the flip side, reading from
       slow-yielding subprocess may block the iteration until data shows up. This
       does not block the parallel inpipe reading occurring parallel thread.)

    The purpose of the object is to allow us to wrap subprocess interactions into
    and interable that can be passed to a WSGI server as the application's return
    value. Because of stream-processing-ability, WSGI does not have to read ALL
    of the subprocess's output and buffer it, before handing it to WSGI server for
    HTTP response. Instead, the class initializer reads just a bit of the stream
    to figure out if error ocurred or likely to occur and if not, just hands the
    further iteration over subprocess output to the server for completion of HTTP
    response.

    The real or perceived subprocess error is trapped and raised as one of
    EnvironmentError family of exceptions

    Example usage:
    #    try:
    #        answer = SubprocessIOChunker(
    #            cmd,
    #            input,
    #            buffer_size = 65536,
    #            chunk_size = 4096
    #            )
    #    except (EnvironmentError) as e:
    #        print str(e)
    #        raise e
    #
    #    return answer



    '''
    def __init__(self, cmd, inputstream = None, buffer_size = 65536, chunk_size = 4096, starting_values = []):
        '''
        Initializes SubprocessIOChunker

        @param cmd A Subprocess.Popen style "cmd". Can be string or array of strings
        @param inputstream (Default: None) A file-like, string, or file pointer.
        @param buffer_size (Default: 65536) A size of total buffer per stream in bytes.
        @param chunk_size (Default: 4096) A max size of a chunk. Actual chunk may be smaller.
        @param starting_values (Default: []) An array of strings to put in front of output que.
        '''

        if inputstream:
            input_streamer = StreamFeeder(inputstream)
            input_streamer.start()
            inputstream = input_streamer.output

        _p = subprocess.Popen(cmd,
            bufsize = -1,
            shell = True,
            stdin = inputstream,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE
            )

        bg_out = BufferedGenerator(_p.stdout, buffer_size, chunk_size, starting_values)
        bg_err = BufferedGenerator(_p.stderr, 16000, 1, bottomless = True)

        while not bg_out.done_reading and not bg_out.reading_paused and not bg_err.length:
            # doing this until we reach either end of file, or end of buffer.
            bg_out.data_added_event.wait(1)
            bg_out.data_added_event.clear()

        # at this point it's still ambiguous if we are done reading or just full buffer.
        # Either way, if error (returned by ended process, or implied based on 
        # presence of stuff in stderr output) we error out.
        # Else, we are happy.
        _returncode = _p.poll()
        if _returncode or (_returncode == None and bg_err.length):
            try:
                _p.terminate()
            except:
                pass
            bg_out.stop()
            bg_err.stop()
            raise EnvironmentError("Subprocess exited due to an error.\n" + "".join(bg_err))

        self.process = _p
        self.output = bg_out
        self.error = bg_err

    def __iter__(self):
        return self

    def next(self):
        if self.process.poll():
            raise EnvironmentError("Subprocess exited due to an error:\n" + ''.join(self.error))
        return self.output.next()

    def throw(self, type, value=None, traceback=None):
        if self.output.length or not self.output.done_reading:
            raise type(value)

    def close(self):
        try:
            self.process.terminate()
        except:
            pass
        try:
            self.output.close()
        except:
            pass
        try:
            self.error.close()
        except:
            pass

    def __del__(self):
        self.close()


########NEW FILE########
__FILENAME__ = test_git_http_backend
import os
import sys
import threading
import socket
import tempfile
import shutil
import random
import time
try:
    # 3.x style module
    import urllib.request as urlopenlib
except:
    # 2.x style module
    import urllib as urlopenlib

import git_http_backend
import cherrypy as wsgiserver

import subprocess

def set_up_server(remote_base_path):
    # choosing free port
    s = socket.socket()
    s.bind(('',0))
    ip, port = s.getsockname()
    s.close()
    del s
    print("Chosen URL is http://%s:%s/" % (ip, port))
    # setting up the server.
    server = wsgiserver.CherryPyWSGIServer(
        (ip, port),
        git_http_backend.assemble_WSGI_git_app(remote_base_path)
        )
    ip = 'localhost' # the IP the socket yields is '0.0.0.0' which is not useful for testing.
    return ip, port, server

def test_smarthttp(url, base_path):
    # this tests roundtrip -
    # new repo > push up > clone down > push up > pull to original.
    repo_one_path = os.path.join(base_path, 'repoone')
    repo_two_path = os.path.join(base_path, 'repotwo')
    line_one = 'This is a test\n'
    line_two = 'Another line\n'
    file_name = 'testfile.txt'
    reponame = 'name%sname' % int(time.time())
    large_file_name = 'largetestfile.bin'
    # create local repo
    print("== creating first local repo and adding content ==")
    os.mkdir(repo_one_path)
    os.chdir(repo_one_path)
    subprocess.call('git init', shell=True)
    f = open(file_name, 'w')
    f.write(line_one)
    f.close()
    subprocess.call('git add %s' % file_name, shell=True)
    subprocess.call('git commit -m "Initial import"', shell=True)
    subprocess.call('git push http://%s/%s master' % (url, reponame), shell=True)
    os.chdir('..')
    # second local repo
    print("== cloning to second local repo and verifying content, adding more ==")
    subprocess.call('git clone http://%s/%s repotwo' % (url,reponame), shell=True)
    assert(os.path.isdir(repo_two_path))
    os.chdir(repo_two_path)
    assert(file_name in os.listdir('.'))
    lines = open(file_name).readlines()
    print "lines are %s" % lines
    assert(line_one in lines)
    lines.append(line_two)
    f = open(file_name, 'w')
    f.writelines(lines)
    f.close()
    f = open(large_file_name, 'wb')
    size = 1000000
    while size:
        f.write(chr(random.randrange(0,255)))
        size -= 1
    f.close()
    subprocess.call('git add %s %s' % (file_name, large_file_name), shell=True)
    subprocess.call('git commit -m "Changing the file"', shell=True)
    subprocess.call('git push origin master', shell=True)
    os.chdir('..')
    # back to original local repo
    print("== pulling to first local repo and verifying added content ==")
    os.chdir(repo_one_path)
    subprocess.call('git pull http://%s/%s master' % (url,reponame), shell=True)
    assert(set([file_name,large_file_name]).issubset(os.listdir('.')))
    assert(set([line_one,line_two]).issubset(open(file_name).readlines()))
    print("=============\n== SUCCESS ==\n=============\n")

def server_runner(s):
    try:
        s.start()
    except KeyboardInterrupt:
        pass
    finally:
        s.stop()

def server_and_client(base_path):
    remote_base_path = os.path.join(base_path, 'reporemote')
    ip, port, server = set_up_server(remote_base_path)    
    t = threading.Thread(None, server_runner, None, [server])
    t.daemon = True
    t.start()
    try:
        test_smarthttp('%s:%s' % (ip, port), base_path)
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
        shutil.rmtree(base_path, True)

def server_only(base_path):
    remote_base_path = os.path.join(base_path, 'reporemote')
    ip, port, server = set_up_server(remote_base_path)
    try:
        server.start()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
        shutil.rmtree(base_path, True)

def client_only(base_path, url):
    try:
        test_smarthttp(url, base_path)
    except KeyboardInterrupt:
        pass
    finally:
        shutil.rmtree(base_path, True)

if __name__ == "__main__":
    base_path = tempfile.mkdtemp()
    print("base path is %s" % base_path)
    if '--client' in sys.argv:
        url = sys.argv[-1]
        client_only(base_path, url)
    elif '--server' in sys.argv:
        server_only(base_path)
    elif '--help' in sys.argv:
        print('Options: "--client url", "--server" Send no options for both server and client.')
    else:
        server_and_client(base_path)
########NEW FILE########
__FILENAME__ = test_subprocessio
import random
import unittest
import subprocessio
import tempfile

class MainTestCase(unittest.TestCase):

    def getiter(self, cmd, input):
        try:
            return subprocessio.SubprocessIOChunker(
                cmd,
                input,
                buffer_size = 65536,
                chunk_size = 4096
                )
        except (EnvironmentError) as e:
            # just because.
            print str(e)
            raise e

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_01_string_throughput(self):
        cmd = 'cat'
        input = 'This is a test string'
        _r = self.getiter(
            cmd,
            input
            )
        self.assertEqual(
            "".join(_r),
            input
            )

    def test_02_io_throughput(self):
        cmd = 'cat'
        size = 128000
        i = size
        input = tempfile.TemporaryFile()
        checksum = 0
        while i:
            _r = random.randrange(32,255)
            checksum += _r
            input.write(chr(_r))
            i -= 1
        input.seek(0)

        _r = self.getiter(
            cmd,
            input
            )

        for e in _r:
            size -= len(e)
            for l in e:
                checksum -= ord(l)

        self.assertEqual(
            size,
            0
            )

        self.assertEqual(
            checksum,
            0
            )


if __name__ == "__main__":
    unittest.TextTestRunner(verbosity=2).run(
        unittest.TestSuite([
            unittest.TestLoader().loadTestsFromTestCase(MainTestCase),
        ])
    )
########NEW FILE########
