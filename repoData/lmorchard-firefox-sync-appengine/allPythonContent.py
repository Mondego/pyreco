__FILENAME__ = gaeunit
#!/usr/bin/env python
'''
GAEUnit: Google App Engine Unit Test Framework

Usage:

1. Put gaeunit.py into your application directory.  Modify 'app.yaml' by
   adding the following mapping below the 'handlers:' section:

   - url: /test.*
     script: gaeunit.py

2. Write your own test cases by extending unittest.TestCase.

3. Launch the development web server.  To run all tests, point your browser to:

   http://localhost:8080/test     (Modify the port if necessary.)
   
   For plain text output add '?format=plain' to the above URL.
   See README.TXT for information on how to run specific tests.

4. The results are displayed as the tests are run.

Visit http://code.google.com/p/gaeunit for more information and updates.

------------------------------------------------------------------------------
Copyright (c) 2008-2009, George Lei and Steven R. Farley.  All rights reserved.

Distributed under the following BSD license:

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
------------------------------------------------------------------------------
'''

__author__ = "George Lei and Steven R. Farley"
__email__ = "George.Z.Lei@Gmail.com"
__version__ = "#Revision: 1.2.8 $"[11:-2]
__copyright__= "Copyright (c) 2008-2009, George Lei and Steven R. Farley"
__license__ = "BSD"
__url__ = "http://code.google.com/p/gaeunit"

import sys
import os
import unittest
import time
import logging
import cgi
import re
import django.utils.simplejson

from xml.sax.saxutils import unescape
from google.appengine.ext import webapp
from google.appengine.api import apiproxy_stub_map  
from google.appengine.api import datastore_file_stub
from google.appengine.ext.webapp.util import run_wsgi_app

_LOCAL_TEST_DIR = '../test'  # location of files
_WEB_TEST_DIR = '/test'   # how you want to refer to tests on your web server
_LOCAL_DJANGO_TEST_DIR = '../../gaeunit/test'

# or:
# _WEB_TEST_DIR = '/u/test'
# then in app.yaml:
#   - url: /u/test.*
#     script: gaeunit.py

##################################################
## Django support

def django_test_runner(request):
    unknown_args = [arg for (arg, v) in request.REQUEST.items()
                    if arg not in ("format", "package", "name")]
    if len(unknown_args) > 0:
        errors = []
        for arg in unknown_args:
            errors.append(_log_error("The request parameter '%s' is not valid." % arg))
        from django.http import HttpResponseNotFound
        return HttpResponseNotFound(" ".join(errors))

    format = request.REQUEST.get("format", "html")
    package_name = request.REQUEST.get("package")
    test_name = request.REQUEST.get("name")
    if format == "html":
        return _render_html(package_name, test_name)
    elif format == "plain":
        return _render_plain(package_name, test_name)
    else:
        error = _log_error("The format '%s' is not valid." % cgi.escape(format))
        from django.http import HttpResponseServerError
        return HttpResponseServerError(error)

def _render_html(package_name, test_name):
    suite, error = _create_suite(package_name, test_name, _LOCAL_DJANGO_TEST_DIR)
    if not error:
        content = _MAIN_PAGE_CONTENT % (_test_suite_to_json(suite), _WEB_TEST_DIR, __version__)
        from django.http import HttpResponse
        return HttpResponse(content)
    else:
        from django.http import HttpResponseServerError
        return HttpResponseServerError(error)

def _render_plain(package_name, test_name):
    suite, error = _create_suite(package_name, test_name, _LOCAL_DJANGO_TEST_DIR)
    if not error:
        from django.http import HttpResponse
        response = HttpResponse()
        response["Content-Type"] = "text/plain"
        runner = unittest.TextTestRunner(response)
        response.write("====================\n" \
                        "GAEUnit Test Results\n" \
                        "====================\n\n")
        _run_test_suite(runner, suite)
        return response
    else:
        from django.http import HttpResponseServerError
        return HttpResponseServerError(error)

def django_json_test_runner(request):
    from django.http import HttpResponse
    response = HttpResponse()
    response["Content-Type"] = "text/javascript"
    test_name = request.REQUEST.get("name")
    _load_default_test_modules(_LOCAL_DJANGO_TEST_DIR)
    suite = unittest.defaultTestLoader.loadTestsFromName(test_name)
    runner = JsonTestRunner()
    _run_test_suite(runner, suite)
    runner.result.render_to(response)
    return response

########################################################

class GAETestCase(unittest.TestCase):
    """TestCase parent class that provides the following assert functions
        * assertHtmlEqual - compare two HTML string ignoring the 
            out-of-element blanks and other differences acknowledged in standard.
    """
    
    def assertHtmlEqual(self, html1, html2):
        if html1 is None or html2 is None:
            raise self.failureException, "argument is None"
        html1 = self._formalize(html1)
        html2 = self._formalize(html2)
        if not html1 == html2:
            error_msg = self._findHtmlDifference(html1, html2)
            error_msg = "HTML contents are not equal" + error_msg
            raise self.failureException, error_msg

    def _formalize(self, html):
        html = html.replace("\r\n", " ").replace("\n", " ")
        html = re.sub(r"[ \t]+", " ", html)
        html = re.sub(r"[ ]*>[ ]*", ">", html)
        html = re.sub(r"[ ]*<[ ]*", "<", html)
        return unescape(html)
    
    def _findHtmlDifference(self, html1, html2):
        display_window_width = 41
        html1_len = len(html1)
        html2_len = len(html2)
        for i in range(html1_len):
            if i >= html2_len or html1[i] != html2[i]:
                break
            
        if html1_len < html2_len:
            html1 += " " * (html2_len - html1_len)
            length = html2_len
        else:
            html2 += " " * (html1_len - html2_len)
            length = html1_len
            
        if length <= display_window_width:
            return "\n%s\n%s\n%s^" % (html1, html2, "_" * i)
        
        start = i - display_window_width / 2
        end = i + 1 + display_window_width / 2
        
        if start < 0:
            adjust = -start
            start += adjust
            end += adjust
            pointer_pos = i
            leading_dots = ""
            ending_dots = "..."
        elif end > length:
            adjust = end - length
            start -= adjust
            end -= adjust
            pointer_pos = i - start + 3
            leading_dots = "..."
            ending_dots = ""
        else:
            pointer_pos = i - start + 3
            leading_dots = "..."
            ending_dots = "..."
        return '\n%s%s%s\n%s\n%s^' % (leading_dots, html1[start:end], ending_dots, leading_dots+html2[start:end]+ending_dots, "_" * (i - start + len(leading_dots)))
    
    assertHtmlEquals = assertHtmlEqual
        
      
##############################################################################
# Main request handler
##############################################################################


class MainTestPageHandler(webapp.RequestHandler):
    def get(self):
        unknown_args = [arg for arg in self.request.arguments()
                        if arg not in ("format", "package", "name")]
        if len(unknown_args) > 0:
            errors = []
            for arg in unknown_args:
                errors.append(_log_error("The request parameter '%s' is not valid." % arg))
            self.error(404)
            self.response.out.write(" ".join(errors))
            return

        format = self.request.get("format", "html")
        package_name = self.request.get("package")
        test_name = self.request.get("name")
        if format == "html":
            self._render_html(package_name, test_name)
        elif format == "plain":
            self._render_plain(package_name, test_name)
        else:
            error = _log_error("The format '%s' is not valid." % cgi.escape(format))
            self.error(404)
            self.response.out.write(error)
            
    def _render_html(self, package_name, test_name):
        suite, error = _create_suite(package_name, test_name, _LOCAL_TEST_DIR)
        if not error:
            self.response.out.write(_MAIN_PAGE_CONTENT % (_test_suite_to_json(suite), _WEB_TEST_DIR, __version__))
        else:
            self.error(404)
            self.response.out.write(error)
        
    def _render_plain(self, package_name, test_name):
        self.response.headers["Content-Type"] = "text/plain"
        runner = unittest.TextTestRunner(self.response.out)
        suite, error = _create_suite(package_name, test_name, _LOCAL_TEST_DIR)
        if not error:
            self.response.out.write("====================\n" \
                                    "GAEUnit Test Results\n" \
                                    "====================\n\n")
            _run_test_suite(runner, suite)
        else:
            self.error(404)
            self.response.out.write(error)


##############################################################################
# JSON test classes
##############################################################################


class JsonTestResult(unittest.TestResult):
    def __init__(self):
        unittest.TestResult.__init__(self)
        self.testNumber = 0

    def render_to(self, stream):
        result = {
            'runs': self.testsRun,
            'total': self.testNumber,
            'errors': self._list(self.errors),
            'failures': self._list(self.failures),
            }

        stream.write(django.utils.simplejson.dumps(result).replace('},', '},\n'))

    def _list(self, list):
        dict = []
        for test, err in list:
            d = { 
              'desc': test.shortDescription() or str(test), 
              'detail': cgi.escape(err),
            }
            dict.append(d)
        return dict


class JsonTestRunner:
    def run(self, test):
        self.result = JsonTestResult()
        self.result.testNumber = test.countTestCases()
        startTime = time.time()
        test(self.result)
        stopTime = time.time()
        timeTaken = stopTime - startTime
        return self.result


class JsonTestRunHandler(webapp.RequestHandler):
    def get(self):    
        self.response.headers["Content-Type"] = "text/javascript"
        test_name = self.request.get("name")
        _load_default_test_modules(_LOCAL_TEST_DIR)
        suite = unittest.defaultTestLoader.loadTestsFromName(test_name)
        runner = JsonTestRunner()
        _run_test_suite(runner, suite)
        runner.result.render_to(self.response.out)


# This is not used by the HTML page, but it may be useful for other client test runners.
class JsonTestListHandler(webapp.RequestHandler):
    def get(self):
        self.response.headers["Content-Type"] = "text/javascript"
        suite, error = _create_suite(self.request) #TODO
        if not error:
            self.response.out.write(_test_suite_to_json(suite))
        else:
            self.error(404)
            self.response.out.write(error)


##############################################################################
# Module helper functions
##############################################################################


def _create_suite(package_name, test_name, test_dir):
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()

    error = None

    try:
        if not package_name and not test_name:
                modules = _load_default_test_modules(test_dir)
                for module in modules:
                    suite.addTest(loader.loadTestsFromModule(module))
        elif test_name:
                _load_default_test_modules(test_dir)
                suite.addTest(loader.loadTestsFromName(test_name))
        elif package_name:
                package = reload(__import__(package_name))
                module_names = package.__all__
                for module_name in module_names:
                    suite.addTest(loader.loadTestsFromName('%s.%s' % (package_name, module_name)))
    
        if suite.countTestCases() == 0:
            raise Exception("'%s' is not found or does not contain any tests." %  \
                            (test_name or package_name or 'local directory: \"%s\"' % _LOCAL_TEST_DIR))
    except Exception, e:
        print e
        error = str(e)
        _log_error(error)

    return (suite, error)


def _load_default_test_modules(test_dir):
    if not test_dir in sys.path:
        sys.path.append(test_dir)
    module_names = [mf[0:-3] for mf in os.listdir(test_dir) if mf.endswith(".py")]
    return [reload(__import__(name)) for name in module_names]


def _get_tests_from_suite(suite, tests):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            _get_tests_from_suite(test, tests)
        else:
            tests.append(test)


def _test_suite_to_json(suite):
    tests = []
    _get_tests_from_suite(suite, tests)
    test_tuples = [(type(test).__module__, type(test).__name__, test._testMethodName) \
                   for test in tests]
    test_dict = {}
    for test_tuple in test_tuples:
        module_name, class_name, method_name = test_tuple
        if module_name not in test_dict:
            mod_dict = {}
            method_list = []
            method_list.append(method_name)
            mod_dict[class_name] = method_list
            test_dict[module_name] = mod_dict
        else:
            mod_dict = test_dict[module_name]
            if class_name not in mod_dict:
                method_list = []
                method_list.append(method_name)
                mod_dict[class_name] = method_list
            else:
                method_list = mod_dict[class_name]
                method_list.append(method_name)
                
    return django.utils.simplejson.dumps(test_dict)


def _run_test_suite(runner, suite):
    """Run the test suite.

    Preserve the current development apiproxy, create a new apiproxy and
    replace the datastore with a temporary one that will be used for this
    test suite, run the test suite, and restore the development apiproxy.
    This isolates the test datastore from the development datastore.

    """        
    original_apiproxy = apiproxy_stub_map.apiproxy
    try:
       apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap() 
       temp_stub = datastore_file_stub.DatastoreFileStub('GAEUnitDataStore', None, None, trusted=True)  
       apiproxy_stub_map.apiproxy.RegisterStub('datastore', temp_stub)
       # Allow the other services to be used as-is for tests.
       for name in ['user', 'urlfetch', 'mail', 'memcache', 'images', 'blobstore']: 
           apiproxy_stub_map.apiproxy.RegisterStub(name, original_apiproxy.GetStub(name))
       runner.run(suite)
    finally:
       apiproxy_stub_map.apiproxy = original_apiproxy


def _log_error(s):
   logging.warn(s)
   return s

           
################################################
# Browser HTML, CSS, and Javascript
################################################


# This string uses Python string formatting, so be sure to escape percents as %%.
_MAIN_PAGE_CONTENT = """
<html>
<head>
    <style>
        body {font-family:arial,sans-serif; text-align:center}
        #title {font-family:"Times New Roman","Times Roman",TimesNR,times,serif; font-size:28px; font-weight:bold; text-align:center}
        #version {font-size:87%%; text-align:center;}
        #weblink {font-style:italic; text-align:center; padding-top:7px; padding-bottom:7px}
        #results {padding-top:20px; margin:0pt auto; text-align:center; font-weight:bold}
        #testindicator {width:750px; height:16px; border-style:solid; border-width:2px 1px 1px 2px; background-color:#f8f8f8;}
        #footerarea {text-align:center; font-size:83%%; padding-top:25px}
        #errorarea {padding-top:25px}
        .error {border-color: #c3d9ff; border-style: solid; border-width: 2px 1px 2px 1px; width:750px; padding:1px; margin:0pt auto; text-align:left}
        .errtitle {background-color:#c3d9ff; font-weight:bold}
    </style>
    <script language="javascript" type="text/javascript">
        var testsToRun = %s;
        var totalRuns = 0;
        var totalErrors = 0;
        var totalFailures = 0;

        function newXmlHttp() {
          try { return new XMLHttpRequest(); } catch(e) {}
          try { return new ActiveXObject("Msxml2.XMLHTTP"); } catch (e) {}
          try { return new ActiveXObject("Microsoft.XMLHTTP"); } catch (e) {}
          alert("XMLHttpRequest not supported");
          return null;
        }
        
        function requestTestRun(moduleName, className, methodName) {
            var methodSuffix = "";
            if (methodName) {
                methodSuffix = "." + methodName;
            }
            var xmlHttp = newXmlHttp();
            xmlHttp.open("GET", "%s/run?name=" + moduleName + "." + className + methodSuffix, true);
            xmlHttp.onreadystatechange = function() {
                if (xmlHttp.readyState != 4) {
                    return;
                }
                if (xmlHttp.status == 200) {
                    var result = eval("(" + xmlHttp.responseText + ")");
                    totalRuns += parseInt(result.runs);
                    totalErrors += result.errors.length;
                    totalFailures += result.failures.length;
                    document.getElementById("testran").innerHTML = totalRuns;
                    document.getElementById("testerror").innerHTML = totalErrors;
                    document.getElementById("testfailure").innerHTML = totalFailures;
                    if (totalErrors == 0 && totalFailures == 0) {
                        testSucceed();
                    } else {
                        testFailed();
                    }
                    var errors = result.errors;
                    var failures = result.failures;
                    var details = "";
                    for(var i=0; i<errors.length; i++) {
                        details += '<p><div class="error"><div class="errtitle">ERROR ' +
                                   errors[i].desc +
                                   '</div><div class="errdetail"><pre>'+errors[i].detail +
                                   '</pre></div></div></p>';
                    }
                    for(var i=0; i<failures.length; i++) {
                        details += '<p><div class="error"><div class="errtitle">FAILURE ' +
                                    failures[i].desc +
                                    '</div><div class="errdetail"><pre>' +
                                    failures[i].detail +
                                    '</pre></div></div></p>';
                    }
                    var errorArea = document.getElementById("errorarea");
                    errorArea.innerHTML += details;
                } else {
                    document.getElementById("errorarea").innerHTML = xmlHttp.responseText;
                    testFailed();
                }
            };
            xmlHttp.send(null);            
        }

        function testFailed() {
            document.getElementById("testindicator").style.backgroundColor="red";
        }
        
        function testSucceed() {
            document.getElementById("testindicator").style.backgroundColor="green";
        }
        
        function runTests() {
            // Run each test asynchronously (concurrently).
            var totalTests = 0;
            for (var moduleName in testsToRun) {
                var classes = testsToRun[moduleName];
                for (var className in classes) {
                    // TODO: Optimize for the case where tests are run by class so we don't
                    //       have to always execute each method separately.  This should be
                    //       possible when we have a UI that allows the user to select tests
                    //       by module, class, and method.
                    //requestTestRun(moduleName, className);
                    methods = classes[className];
                    for (var i = 0; i < methods.length; i++) {
                        totalTests += 1;
                        var methodName = methods[i];
                        requestTestRun(moduleName, className, methodName);
                    }
                }
            }
            document.getElementById("testtotal").innerHTML = totalTests;
        }

    </script>
    <title>GAEUnit: Google App Engine Unit Test Framework</title>
</head>
<body onload="runTests()">
    <div id="headerarea">
        <div id="title">GAEUnit: Google App Engine Unit Test Framework</div>
        <div id="version">Version %s</div>
    </div>
    <div id="resultarea">
        <table id="results"><tbody>
            <tr><td colspan="3"><div id="testindicator"> </div></td</tr>
            <tr>
                <td>Runs: <span id="testran">0</span>/<span id="testtotal">0</span></td>
                <td>Errors: <span id="testerror">0</span></td>
                <td>Failures: <span id="testfailure">0</span></td>
            </tr>
        </tbody></table>
    </div>
    <div id="errorarea"></div>
    <div id="footerarea">
        <div id="weblink">
        <p>
            Please visit the <a href="http://code.google.com/p/gaeunit">project home page</a>
            for the latest version or to report problems.
        </p>
        <p>
            Copyright 2008-2009 <a href="mailto:George.Z.Lei@Gmail.com">George Lei</a>
            and <a href="mailto:srfarley@gmail.com">Steven R. Farley</a>
        </p>
        </div>
    </div>
</body>
</html>
"""


##############################################################################
# Script setup and execution
##############################################################################


application = webapp.WSGIApplication([('%s'      % _WEB_TEST_DIR, MainTestPageHandler),
                                      ('%s/run'  % _WEB_TEST_DIR, JsonTestRunHandler),
                                      ('%s/list' % _WEB_TEST_DIR, JsonTestListHandler)],
                                      debug=True)

def main():
    run_wsgi_app(application)                                    

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = main
"""
Controller package for basic web UI.
"""
import sys, os, os.path
base_dir = os.path.dirname( os.path.dirname(__file__) )
sys.path.extend([ os.path.join(base_dir, d) for d in ('lib', 'extlib') ])

import random, string, logging, hashlib
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util, template
from fxsync.models import Profile, Collection, WBO

def main():
    """Main entry point for controller"""
    util.run_wsgi_app(application())

def application():
    """Build the WSGI app for this package"""
    return webapp.WSGIApplication([
        ('/start', StartHandler),
    ], debug=True)

class StartHandler(webapp.RequestHandler):
    """Sync start page handler"""

    def initialize(self, req, resp):
        webapp.RequestHandler.initialize(self, req, resp)
        self.log = logging.getLogger()

    def get(self):
        """Display the sync start page"""
        user, profile = Profile.get_user_and_profile()
        return self.render_template('main/start.html', {
            'user': user, 
            'profile': profile,
            'sync_url': '%s/sync/' % self.request.application_url,
            'logout_url': users.create_logout_url(self.request.uri)
        })

    def post(self):
        """Process a POST'd command from the sync start page.

        HACK: This is a little hacky, pivoting on a form field command, but oh well.
        """
        user, profile = Profile.get_user_and_profile()
        action = self.request.get('action', False)

        if not profile and 'create_profile' == action:
            
            # Create a new profile, with auto-generated password
            new_profile = Profile(
                user      = user,
                user_id   = user.user_id(),
                user_name = hashlib.md5(user.user_id()).hexdigest(),
                password  = Profile.generate_password()
            )
            new_profile.put()

        elif profile and 'regenerate_password' == action:
            # Generate and set a new password for the profile
            profile.password = Profile.generate_password()
            profile.put()

        elif profile and 'delete_profile' == action:
            # Delete the profile
            profile.delete()

        return self.redirect('/start')

    def render_template(self, path, data=None):
        """Shortcut for rendering templates"""
        if (data is None): data = {}
        self.response.out.write(template.render(
            '%s/templates/%s' % (base_dir, path), data
        ))

if __name__ == '__main__': main()

########NEW FILE########
__FILENAME__ = sync_api
"""
Controller package for main Sync API

TODO: Issue X-Weave-Backoff when GAE quotas are running out
"""
import sys, os
base_dir = os.path.dirname( os.path.dirname(__file__) )
sys.path.extend([ os.path.join(base_dir, d) for d in ( 'lib', 'extlib' ) ])

import logging, struct
from datetime import datetime
from time import mktime
from google.appengine.api import users
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from django.utils import simplejson 
from fxsync.utils import profile_auth, json_request, json_response
from fxsync.models import Profile, Collection, WBO

WEAVE_ERROR_INVALID_PROTOCOL = 1
WEAVE_ERROR_INCORRECT_CAPTCHA = 2
WEAVE_ERROR_INVALID_USERNAME = 3
WEAVE_ERROR_NO_OVERWRITE = 4
WEAVE_ERROR_USERID_PATH_MISMATCH = 5
WEAVE_ERROR_JSON_PARSE = 6
WEAVE_ERROR_MISSING_PASSWORD = 7
WEAVE_ERROR_INVALID_WBO = 8
WEAVE_ERROR_BAD_PASSWORD_STRENGTH = 9
WEAVE_ERROR_INVALID_RESET_CODE = 10
WEAVE_ERROR_FUNCTION_NOT_SUPPORTED = 11
WEAVE_ERROR_NO_EMAIL = 12
WEAVE_ERROR_INVALID_COLLECTION = 13

def main():
    """Main entry point for controller"""
    util.run_wsgi_app(application())

def application():
    """Build the WSGI app for this package"""
    return webapp.WSGIApplication([
        (r'/sync/1.0/(.*)/info/collections', CollectionsHandler),
        (r'/sync/1.0/(.*)/info/collection_counts', CollectionCountsHandler),
        (r'/sync/1.0/(.*)/info/quota', QuotaHandler),
        (r'/sync/1.0/(.*)/storage/([^\/]*)/?$', StorageCollectionHandler),
        (r'/sync/1.0/(.*)/storage/(.*)/(.*)', StorageItemHandler),
        (r'/sync/1.0/(.*)/storage/', StorageHandler),
    ], debug=True)

class SyncApiBaseRequestHandler(webapp.RequestHandler):
    """Base class for all sync API request handlers"""
    def initialize(self, req, resp):
        webapp.RequestHandler.initialize(self, req, resp)
        self.log = logging.getLogger()
        self.response.headers['X-Weave-Timestamp'] = str(WBO.get_time_now())

class CollectionsHandler(SyncApiBaseRequestHandler):
    """Handler for collection list"""
    @profile_auth
    @json_response
    def get(self, user_name):
        """List user's collections and last modified times"""
        return Collection.get_timestamps(self.request.profile)

class CollectionCountsHandler(SyncApiBaseRequestHandler):
    """Handler for collection counts"""
    @profile_auth
    @json_response
    def get(self, user_name):
        """Get counts for a user's collections"""
        return Collection.get_counts(self.request.profile)

class QuotaHandler(SyncApiBaseRequestHandler):
    """Handler for quota checking"""
    @profile_auth
    @json_response
    def get(self, user_name):
        """Get the quotas for a user's profile"""
        # TODO: Need to actually implement space / quota counting.
        return [ 0, 9999 ]

class StorageItemHandler(SyncApiBaseRequestHandler):
    """Handler for individual collection items"""

    @profile_auth
    @json_response
    def get(self, user_name, collection_name, wbo_id):
        """Get an item from the collection"""
        collection = Collection.get_by_profile_and_name(
            self.request.profile, collection_name
        )
        wbo = WBO.get_by_collection_and_wbo_id(collection, wbo_id)
        if not wbo: return self.error(404)
        return wbo.to_dict()

    @profile_auth
    def delete(self, user_name, collection_name, wbo_id):
        """Delete an item from the collection"""
        collection = Collection.get_by_profile_and_name(
            self.request.profile, collection_name
        )
        wbo = WBO.get_by_collection_and_wbo_id(collection, wbo_id)
        if not wbo: return self.error(404)
        wbo.delete()
        self.response.out.write('%s' % WBO.get_time_now())

    @profile_auth
    @json_request
    @json_response
    def put(self, user_name, collection_name, wbo_id):
        """Insert or update an item in the collection"""
        self.request.body_json.update({
            'profile': self.request.profile, 
            'collection_name': collection_name,
            'wbo_id': wbo_id
        })
        (wbo, errors) = WBO.from_json(self.request.body_json)
        if not wbo:
            self.response.set_status(400, message="Bad Request")
            self.response.out.write(WEAVE_ERROR_INVALID_WBO)
            return None
        else:
            wbo.put()
            return wbo.modified

class StorageCollectionHandler(SyncApiBaseRequestHandler):

    @profile_auth
    def get(self, user_name, collection_name):
        """Filtered retrieval of WBOs from a collection"""
        collection = Collection.get_by_profile_and_name(
            self.request.profile, collection_name
        )

        # TODO: Need a generator here? 
        # TODO: Find out how not to load everything into memory.
        params = self.normalize_retrieval_parameters()
        self.response.headers['X-Weave-Records'] = \
            str(collection.retrieve(count=True, **params))
        out = collection.retrieve(**params)

        accept = ('Accept' not in self.request.headers 
            and 'application/json' or self.request.headers['Accept'])

        if 'application/newlines' == accept:
            self.response.headers['Content-Type'] = 'application/newlines'
            for x in out:
                self.response.out.write("%s\n" % simplejson.dumps(x))

        elif 'application/whoisi' == accept:
            self.response.headers['Content-Type'] = 'application/whoisi'
            for x in out:
                rec = simplejson.dumps(x)
                self.response.out.write('%s%s' % (
                    struct.pack('!I', len(rec)), rec
                ))

        else:
            self.response.headers['Content-Type'] = 'application/json'
            rv = [x for x in out]
            self.response.out.write(simplejson.dumps(rv))

    @profile_auth
    @json_request
    @json_response
    def post(self, user_name, collection_name):
        """Bulk update of WBOs in a collection"""
        out = { 'modified': None, 'success': [], 'failed': {} }

        collection = Collection.get_by_profile_and_name(
            self.request.profile, collection_name
        )

        wbos = []
        for wbo_data in self.request.body_json:
            if 'id' not in wbo_data: continue
            wbo_data['collection'] = collection
            wbo_id = wbo_data['id']
            (wbo, errors) = WBO.from_json(wbo_data)
            if wbo:
                out['modified'] = wbo.modified
                out['success'].append(wbo_id)
                wbos.append(wbo)
            else:
                out['failed'][wbo_id] = errors

        if (len(wbos) > 0):
            db.put(wbos)

        return out

    @profile_auth
    @json_response
    def delete(self, user_name, collection_name):
        """Bulk deletion of WBOs from a collection"""
        collection = Collection.get_by_profile_and_name(
            self.request.profile, collection_name
        )
        params = self.normalize_retrieval_parameters()
        params['wbo'] = True
        out = collection.retrieve(**params)
        db.delete(out)
        return WBO.get_time_now()

    def normalize_retrieval_parameters(self):
        """Massage incoming retrieval parameters into a form acceptable by
        collection.retrieve"""
        params = dict((k,self.request.get(k, None)) for k in (
            'id', 'ids', 'predecessorid', 'parentid', 
            'older', 'newer',
            'index_above', 'index_below', 
            'full', 'wbo', 'limit', 'offset', 'sort'
        ))

        params['full'] = params['full'] is not None

        if params['ids']: params['ids'] = params['ids'].split(',')

        for n in ('index_above', 'index_below', 'limit', 'offset'):
            if params[n]: params[n] = int(params[n])

        for n in ('older', 'newer'):
            if params[n]: params[n] = float(params[n])

        return params

class StorageHandler(SyncApiBaseRequestHandler):

    @profile_auth
    def delete(self, user_name):
        # DELETE EVERYTHING!
        self.response.out.write('StorageHandler %s' % user_name)

if __name__ == '__main__': main()

########NEW FILE########
__FILENAME__ = user_api
"""
Controller package for Sync User API, profile management
"""
import sys, os
base_dir = os.path.dirname( os.path.dirname(__file__) )
sys.path.extend([ os.path.join(base_dir, d) for d in ( 'lib', 'extlib' ) ])

import urllib
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from fxsync.models import *
from fxsync.utils import profile_auth

def main():
    """Main entry point for controller"""
    application = webapp.WSGIApplication([
        (r'/sync/user/1.0/(.*)/node/weave', NodeHandler), # GET (unauth)
        (r'/sync/user/1.0/(.*)/email', EmailHandler), # POST
        (r'/sync/user/1.0/(.*)/password', PasswordHandler), # POST
        (r'/sync/user/1.0/(.*)/password_reset', PasswordResetHandler), # GET
        (r'/sync/user/1.0/(.*)/?', UserHandler), # GET (unauth), PUT, DELETE
    ], debug=True)
    util.run_wsgi_app(application)

class NodeHandler(webapp.RequestHandler):
    """Sync cluster node location"""
    
    def get(self, user_name):
        """Return full URL to the sync cluster node (ie. the sync API)"""
        self.response.out.write('%s/sync/' % self.request.application_url)

class UserHandler(webapp.RequestHandler):
    """User URL handler"""

    def get(self, user_name):
        """Determine whether the user exists"""
        user_name = urllib.unquote(user_name)
        profile = Profile.get_by_user_name(user_name)
        return self.response.out.write(profile and '1' or '0')

    def put(self, user_name):
        """Profile sign up"""
        # This server disallows sign-up
        self.response.set_status(403)

    @profile_auth
    def delete(self, user_name):
        """Allow profile deletion"""
        user_name = urllib.unquote(user_name)
        profile = Profile.get_by_user_name(user_name)
        profile.delete()
        return self.response.out.write('success')

class EmailHandler(webapp.RequestHandler):

    @profile_auth
    def post(self, user_name):
        """Profile email modification"""
        # This server disallows email change
        self.response.set_status(403)

class PasswordHandler(webapp.RequestHandler):
    
    @profile_auth
    def post(self, user_name):
        """Profile password modification"""
        # This server disallows password change (for now)
        self.response.set_status(403)

class PasswordResetHandler(webapp.RequestHandler):
   
    @profile_auth
    def get(self, user_name):
        """Profile password reset trigger"""
        # This server disallows password reset
        self.response.set_status(403)

if __name__ == '__main__': main()

########NEW FILE########
__FILENAME__ = debugapp
from webob import Request
try:
    sorted
except NameError:
    from webtest import sorted

__all__ = ['debug_app']

def debug_app(environ, start_response):
    req = Request(environ)
    if 'error' in req.GET:
        raise Exception('Exception requested')
    status = req.GET.get('status', '200 OK')
    parts = []
    for name, value in sorted(environ.items()):
        if name.upper() != name:
            value = repr(value)
        parts.append('%s: %s\n' % (name, value))
    req_body = req.body
    if req_body:
        parts.append('-- Body ----------\n')
        parts.append(req_body)
    body = ''.join(parts)
    headers = [
        ('Content-Type', 'text/plain'),
        ('Content-Length', str(len(body)))]
    for name, value in req.GET.items():
        if name.startswith('header-'):
            header_name = name[len('header-'):]
            headers.append((header_name, value))
    start_response(status, headers)
    return [body]

def make_debug_app(global_conf):
    """
    An application that displays the request environment, and does
    nothing else (useful for debugging and test purposes).
    """
    return debug_app

########NEW FILE########
__FILENAME__ = lint
# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
# Also licenced under the Apache License, 2.0: http://opensource.org/licenses/apache2.0.php
# Licensed to PSF under a Contributor Agreement
"""
Middleware to check for obedience to the WSGI specification.

Some of the things this checks:

* Signature of the application and start_response (including that
  keyword arguments are not used).

* Environment checks:

  - Environment is a dictionary (and not a subclass).

  - That all the required keys are in the environment: REQUEST_METHOD,
    SERVER_NAME, SERVER_PORT, wsgi.version, wsgi.input, wsgi.errors,
    wsgi.multithread, wsgi.multiprocess, wsgi.run_once

  - That HTTP_CONTENT_TYPE and HTTP_CONTENT_LENGTH are not in the
    environment (these headers should appear as CONTENT_LENGTH and
    CONTENT_TYPE).

  - Warns if QUERY_STRING is missing, as the cgi module acts
    unpredictably in that case.

  - That CGI-style variables (that don't contain a .) have
    (non-unicode) string values

  - That wsgi.version is a tuple

  - That wsgi.url_scheme is 'http' or 'https' (@@: is this too
    restrictive?)

  - Warns if the REQUEST_METHOD is not known (@@: probably too
    restrictive).

  - That SCRIPT_NAME and PATH_INFO are empty or start with /

  - That at least one of SCRIPT_NAME or PATH_INFO are set.

  - That CONTENT_LENGTH is a positive integer.

  - That SCRIPT_NAME is not '/' (it should be '', and PATH_INFO should
    be '/').

  - That wsgi.input has the methods read, readline, readlines, and
    __iter__

  - That wsgi.errors has the methods flush, write, writelines

* The status is a string, contains a space, starts with an integer,
  and that integer is in range (> 100).

* That the headers is a list (not a subclass, not another kind of
  sequence).

* That the items of the headers are tuples of strings.

* That there is no 'status' header (that is used in CGI, but not in
  WSGI).

* That the headers don't contain newlines or colons, end in _ or -, or
  contain characters codes below 037.

* That Content-Type is given if there is content (CGI often has a
  default content type, but WSGI does not).

* That no Content-Type is given when there is no content (@@: is this
  too restrictive?)

* That the exc_info argument to start_response is a tuple or None.

* That all calls to the writer are with strings, and no other methods
  on the writer are accessed.

* That wsgi.input is used properly:

  - .read() is called with zero or one argument

  - That it returns a string

  - That readline, readlines, and __iter__ return strings

  - That .close() is not called

  - No other methods are provided

* That wsgi.errors is used properly:

  - .write() and .writelines() is called with a string

  - That .close() is not called, and no other methods are provided.

* The response iterator:

  - That it is not a string (it should be a list of a single string; a
    string will work, but perform horribly).

  - That .next() returns a string

  - That the iterator is not iterated over until start_response has
    been called (that can signal either a server or application
    error).

  - That .close() is called (doesn't raise exception, only prints to
    sys.stderr, because we only know it isn't called when the object
    is garbage collected).
"""

import re
import sys
from types import DictType, StringType, TupleType, ListType
import warnings

header_re = re.compile(r'^[a-zA-Z][a-zA-Z0-9\-_]*$')
bad_header_value_re = re.compile(r'[\000-\037]')

class WSGIWarning(Warning):
    """
    Raised in response to WSGI-spec-related warnings
    """

def middleware(application, global_conf=None):

    """
    When applied between a WSGI server and a WSGI application, this
    middleware will check for WSGI compliancy on a number of levels.
    This middleware does not modify the request or response in any
    way, but will throw an AssertionError if anything seems off
    (except for a failure to close the application iterator, which
    will be printed to stderr -- there's no way to throw an exception
    at that point).
    """
    
    def lint_app(*args, **kw):
        assert len(args) == 2, "Two arguments required"
        assert not kw, "No keyword arguments allowed"
        environ, start_response = args

        check_environ(environ)

        # We use this to check if the application returns without
        # calling start_response:
        start_response_started = []

        def start_response_wrapper(*args, **kw):
            assert len(args) == 2 or len(args) == 3, (
                "Invalid number of arguments: %s" % args)
            assert not kw, "No keyword arguments allowed"
            status = args[0]
            headers = args[1]
            if len(args) == 3:
                exc_info = args[2]
            else:
                exc_info = None

            check_status(status)
            check_headers(headers)
            check_content_type(status, headers)
            check_exc_info(exc_info)

            start_response_started.append(None)
            return WriteWrapper(start_response(*args))

        environ['wsgi.input'] = InputWrapper(environ['wsgi.input'])
        environ['wsgi.errors'] = ErrorWrapper(environ['wsgi.errors'])

        iterator = application(environ, start_response_wrapper)
        assert iterator is not None and iterator != False, (
            "The application must return an iterator, if only an empty list")

        check_iterator(iterator)

        return IteratorWrapper(iterator, start_response_started)

    return lint_app

class InputWrapper(object):

    def __init__(self, wsgi_input):
        self.input = wsgi_input

    def read(self, *args):
        assert len(args) <= 1
        v = self.input.read(*args)
        assert type(v) is type("")
        return v

    def readline(self, *args):
        v = self.input.readline(*args)
        assert type(v) is type("")
        return v

    def readlines(self, *args):
        assert len(args) <= 1
        lines = self.input.readlines(*args)
        assert type(lines) is type([])
        for line in lines:
            assert type(line) is type("")
        return lines
    
    def __iter__(self):
        while 1:
            line = self.readline()
            if not line:
                return
            yield line

    def close(self):
        assert 0, "input.close() must not be called"

class ErrorWrapper(object):

    def __init__(self, wsgi_errors):
        self.errors = wsgi_errors

    def write(self, s):
        assert type(s) is type("")
        self.errors.write(s)

    def flush(self):
        self.errors.flush()

    def writelines(self, seq):
        for line in seq:
            self.write(line)

    def close(self):
        assert 0, "errors.close() must not be called"

class WriteWrapper(object):

    def __init__(self, wsgi_writer):
        self.writer = wsgi_writer

    def __call__(self, s):
        assert type(s) is type("")
        self.writer(s)

class PartialIteratorWrapper(object):

    def __init__(self, wsgi_iterator):
        self.iterator = wsgi_iterator

    def __iter__(self):
        # We want to make sure __iter__ is called
        return IteratorWrapper(self.iterator)

class IteratorWrapper(object):

    def __init__(self, wsgi_iterator, check_start_response):
        self.original_iterator = wsgi_iterator
        self.iterator = iter(wsgi_iterator)
        self.closed = False
        self.check_start_response = check_start_response

    def __iter__(self):
        return self

    def next(self):
        assert not self.closed, (
            "Iterator read after closed")
        v = self.iterator.next()
        if self.check_start_response is not None:
            assert self.check_start_response, (
                "The application returns and we started iterating over its body, but start_response has not yet been called")
            self.check_start_response = None
        return v
        
    def close(self):
        self.closed = True
        if hasattr(self.original_iterator, 'close'):
            self.original_iterator.close()

    def __del__(self):
        if not self.closed:
            sys.stderr.write(
                "Iterator garbage collected without being closed")
        assert self.closed, (
            "Iterator garbage collected without being closed")

def check_environ(environ):
    assert type(environ) is DictType, (
        "Environment is not of the right type: %r (environment: %r)"
        % (type(environ), environ))
    
    for key in ['REQUEST_METHOD', 'SERVER_NAME', 'SERVER_PORT',
                'wsgi.version', 'wsgi.input', 'wsgi.errors',
                'wsgi.multithread', 'wsgi.multiprocess',
                'wsgi.run_once']:
        assert key in environ, (
            "Environment missing required key: %r" % key)

    for key in ['HTTP_CONTENT_TYPE', 'HTTP_CONTENT_LENGTH']:
        assert key not in environ, (
            "Environment should not have the key: %s "
            "(use %s instead)" % (key, key[5:]))

    if 'QUERY_STRING' not in environ:
        warnings.warn(
            'QUERY_STRING is not in the WSGI environment; the cgi '
            'module will use sys.argv when this variable is missing, '
            'so application errors are more likely',
            WSGIWarning)

    for key in environ.keys():
        if '.' in key:
            # Extension, we don't care about its type
            continue
        assert type(environ[key]) is StringType, (
            "Environmental variable %s is not a string: %r (value: %r)"
            % (key, type(environ[key]), environ[key]))
        
    assert type(environ['wsgi.version']) is TupleType, (
        "wsgi.version should be a tuple (%r)" % environ['wsgi.version'])
    assert environ['wsgi.url_scheme'] in ('http', 'https'), (
        "wsgi.url_scheme unknown: %r" % environ['wsgi.url_scheme'])

    check_input(environ['wsgi.input'])
    check_errors(environ['wsgi.errors'])

    # @@: these need filling out:
    if environ['REQUEST_METHOD'] not in (
        'GET', 'HEAD', 'POST', 'OPTIONS','PUT','DELETE','TRACE'):
        warnings.warn(
            "Unknown REQUEST_METHOD: %r" % environ['REQUEST_METHOD'],
            WSGIWarning)

    assert (not environ.get('SCRIPT_NAME')
            or environ['SCRIPT_NAME'].startswith('/')), (
        "SCRIPT_NAME doesn't start with /: %r" % environ['SCRIPT_NAME'])
    assert (not environ.get('PATH_INFO')
            or environ['PATH_INFO'].startswith('/')), (
        "PATH_INFO doesn't start with /: %r" % environ['PATH_INFO'])
    if environ.get('CONTENT_LENGTH'):
        assert int(environ['CONTENT_LENGTH']) >= 0, (
            "Invalid CONTENT_LENGTH: %r" % environ['CONTENT_LENGTH'])

    if not environ.get('SCRIPT_NAME'):
        assert environ.has_key('PATH_INFO'), (
            "One of SCRIPT_NAME or PATH_INFO are required (PATH_INFO "
            "should at least be '/' if SCRIPT_NAME is empty)")
    assert environ.get('SCRIPT_NAME') != '/', (
        "SCRIPT_NAME cannot be '/'; it should instead be '', and "
        "PATH_INFO should be '/'")

def check_input(wsgi_input):
    for attr in ['read', 'readline', 'readlines', '__iter__']:
        assert hasattr(wsgi_input, attr), (
            "wsgi.input (%r) doesn't have the attribute %s"
            % (wsgi_input, attr))

def check_errors(wsgi_errors):
    for attr in ['flush', 'write', 'writelines']:
        assert hasattr(wsgi_errors, attr), (
            "wsgi.errors (%r) doesn't have the attribute %s"
            % (wsgi_errors, attr))

def check_status(status):
    assert type(status) is StringType, (
        "Status must be a string (not %r)" % status)
    # Implicitly check that we can turn it into an integer:
    status_code = status.split(None, 1)[0]
    assert len(status_code) == 3, (
        "Status codes must be three characters: %r" % status_code)
    status_int = int(status_code)
    assert status_int >= 100, "Status code is invalid: %r" % status_int
    if len(status) < 4 or status[3] != ' ':
        warnings.warn(
            "The status string (%r) should be a three-digit integer "
            "followed by a single space and a status explanation"
            % status, WSGIWarning)

def check_headers(headers):
    assert type(headers) is ListType, (
        "Headers (%r) must be of type list: %r"
        % (headers, type(headers)))
    header_names = {}
    for item in headers:
        assert type(item) is TupleType, (
            "Individual headers (%r) must be of type tuple: %r"
            % (item, type(item)))
        assert len(item) == 2
        name, value = item
        assert name.lower() != 'status', (
            "The Status header cannot be used; it conflicts with CGI "
            "script, and HTTP status is not given through headers "
            "(value: %r)." % value)
        header_names[name.lower()] = None
        assert '\n' not in name and ':' not in name, (
            "Header names may not contain ':' or '\\n': %r" % name)
        assert header_re.search(name), "Bad header name: %r" % name
        assert not name.endswith('-') and not name.endswith('_'), (
            "Names may not end in '-' or '_': %r" % name)
        assert not bad_header_value_re.search(value), (
            "Bad header value: %r (bad char: %r)"
            % (value, bad_header_value_re.search(value).group(0)))

def check_content_type(status, headers):
    code = int(status.split(None, 1)[0])
    # @@: need one more person to verify this interpretation of RFC 2616
    #     http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html
    NO_MESSAGE_BODY = (201, 204, 304)
    NO_MESSAGE_TYPE = (204, 304)
    for name, value in headers:
        if name.lower() == 'content-type':
            if code not in NO_MESSAGE_TYPE:
                return
            assert 0, (("Content-Type header found in a %s response, "
                        "which must not return content.") % code)
    if code not in NO_MESSAGE_BODY:
        assert 0, "No Content-Type header found in headers (%s)" % headers

def check_exc_info(exc_info):
    assert exc_info is None or type(exc_info) is type(()), (
        "exc_info (%r) is not a tuple: %r" % (exc_info, type(exc_info)))
    # More exc_info checks?

def check_iterator(iterator):
    # Technically a string is legal, which is why it's a really bad
    # idea, because it may cause the response to be returned
    # character-by-character
    assert not isinstance(iterator, str), (
        "You should not return a string as your application iterator, "
        "instead return a single-item list containing that string.")

def make_middleware(application, global_conf):
    # @@: global_conf should be taken out of the middleware function,
    # and isolated here
    return middleware(application)

make_middleware.__doc__ = __doc__

__all__ = ['middleware', 'make_middleware']

########NEW FILE########
__FILENAME__ = models
"""
Model classes for fxsync
"""
import sys, os
base_dir = os.path.dirname( os.path.dirname(__file__) )
sys.path.extend([ os.path.join(base_dir, d) for d in ( 'lib', 'extlib' ) ])

import datetime, random, string, hashlib, logging
from google.appengine.ext import db
from google.appengine.api import users
from django.utils import simplejson

from datetime import datetime
from time import mktime

WBO_PAGE_SIZE = 25

def paginate(items, page_len):
    """Paginage a list of items into a list of page lists"""
    total_len = len(items)
    num_pages = total_len / page_len
    (d, m)    = divmod(total_len, page_len)
    if m > 0: 
        num_pages += 1
    return (
        items[ (i * page_len):(i * page_len + page_len) ] 
        for i in xrange(num_pages)
    )

class Profile(db.Model):
    """Sync profile associated with logged in account"""
    user        = db.UserProperty(auto_current_user_add=True)
    user_name   = db.StringProperty(required=True)
    user_id     = db.StringProperty(required=True)
    password    = db.StringProperty(required=True)
    created_at  = db.DateTimeProperty(auto_now_add=True)
    updated_at  = db.DateTimeProperty(auto_now=True)

    @classmethod
    def get_user_and_profile(cls):
        """Try finding a sync profile associated with the current user"""
        user = users.get_current_user()
        profile = Profile.all().filter('user_id =', user.user_id()).get()
        return user, profile

    @classmethod
    def get_by_user_name(cls, user_name):
        """Get a profile by user name"""
        return cls.all().filter('user_name =', user_name).get()        

    @classmethod
    def generate_password(cls):
        """Generate a random alphanumeric password"""
        return ''.join(random.sample(string.letters+string.digits, 16))

    @classmethod
    def authenticate(cls, user_name, password):
        """Attempt to authenticate the given user name and password"""
        profile = cls.get_by_user_name(user_name)
        return ( profile and profile.password == password )

    def delete(self):
        c_keys = []
        cs = Collection.all().ancestor(self)
        for c in cs:
            c_keys.append(c.key())
            while True:
                # HACK: This smells like trouble - switch to Task Queue?
                w_keys = WBO.all(keys_only=True).ancestor(c).fetch(500)
                if not w_keys: break
                db.delete(w_keys)
        db.delete(c_keys)
        db.Model.delete(self)
    
class Collection(db.Model):
    profile = db.ReferenceProperty(Profile, required=True)
    name    = db.StringProperty(required=True)

    builtin_names = (
        'clients', 'crypto', 'forms', 'history', 'keys', 'meta', 
        'bookmarks', 'prefs','tabs','passwords'
    )

    def delete(self):
        while True:
            # HACK: This smells like trouble - switch to Task Queue?
            w_keys = WBO.all(keys_only=True).ancestor(self).fetch(500)
            if not w_keys: break
            db.delete(w_keys)
        db.Model.delete(self)

    def retrieve(self, 
            full=None, wbo=None, count=None, direct_output=None, 
            id=None, ids=None, 
            parentid=None, predecessorid=None, 
            newer=None, older=None, 
            index_above=None, index_below=None,
            sort=None, limit=None, offset=None):

        limit  = (limit is not None) and limit or 1000 #False
        offset = (offset is not None) and offset or 0 #False
        sort   = (sort is not None) and sort or 'index'

        if id:
            w = WBO.all().ancestor(self).filter('wbo_id =', id).get()
            if count: return 1
            if wbo: return [ w ]
            if full: return [ w.to_dict() ]
            return [ w.wbo_id ]

        elif ids:
            if count: return len(ids)
            wbos = []
            id_pages = paginate(ids, WBO_PAGE_SIZE)
            for id_page in id_pages:
                q = WBO.all().ancestor(self).filter('wbo_id IN', id_page)
                wbos.extend(q.fetch(WBO_PAGE_SIZE))
            if wbo: return wbos
            if full: return ( w.to_dict() for w in wbos )
            return ( w.wbo_id for w in wbos )

        final_query = None
        queries = []

        # TODO: Work out how to use keys_only=True here again.

        if parentid is not None:
            queries.append(WBO.all().ancestor(self)
                .filter('parentid =', parentid))
            
        if predecessorid is not None:
            queries.append(WBO.all().ancestor(self)
                .filter('predecessorid =', predecessorid))

        if index_above is not None or index_below is not None:
            q = WBO.all().ancestor(self)
            if index_above: q.filter('sortindex >', index_above)
            if index_below: q.filter('sortindex <', index_below)
            q.order('sortindex')
            queries.append(q)

        if newer is not None or older is not None:
            q = WBO.all().ancestor(self)
            if newer: q.filter('modified >', newer)
            if older: q.filter('modified <', older)
            q.order('modified')
            queries.append(q)

        if len(queries) == 0:
            final_query = WBO.all().ancestor(self)
        elif len(queries) == 1:
            final_query = queries[0]
        else:
            key_set = None
            for q in queries:
                # HACK: I don't think setting _keys_only is kosher
                q._keys_only = True
                keys = set(str(x) for x in q.fetch(limit, offset))
                if key_set is None:
                    key_set = keys
                else:
                    key_set = key_set & keys
            
            keys = [db.Key(x) for x in key_set]
            key_pages = paginate(keys, WBO_PAGE_SIZE)

            # Use the key pages for a combo result here.

            final_query = WBO.all().ancestor(self).filter('__key__ IN', keys)

        # Determine which sort order to use.
        if 'oldest' == sort: order = 'modified'
        elif 'newest' == sort: order = '-modified'
        else: order = '-sortindex'
        final_query.order(order)

        # Return IDs / full objects as appropriate for full option.
        if count:
            return final_query.count()
        if wbo:
            return ( w for w in final_query.fetch(limit, offset) )
        if not full:
            return ( w.wbo_id for w in final_query.fetch(limit, offset) )
        else:
            return ( w.to_dict() for w in final_query.fetch(limit, offset) )

    @classmethod
    def build_key_name(cls, name):
        return name

    @classmethod
    def get_by_profile_and_name(cls, profile, name):
        """Get a collection by name and user"""
        return Collection.get_or_insert(
            parent=profile,
            key_name=cls.build_key_name(name),
            profile=profile,
            name=name
        )

    @classmethod
    def is_builtin(cls, name):
        """Determine whether a named collection is built-in"""
        return name in cls.builtin_names

    @classmethod
    def get_timestamps(cls, profile):
        """Assemble last modified for user's built-in and ad-hoc collections"""
        c_list = dict((n, 0) for n in cls.builtin_names)
        q = Collection.all().ancestor(profile)
        for c in q:
            w = WBO.all().ancestor(c).order('-modified').get()
            c_list[c.name] = w and w.modified or 0
        return c_list 

    @classmethod
    def get_counts(cls, profile):
        """Assemble counts for user's built-in and ad-hoc collections"""
        c_list = dict((n, 0) for n in cls.builtin_names)
        q = Collection.all().ancestor(profile)
        for c in q:
            c_list[c.name] = WBO.all().ancestor(c).count()
        return c_list 

class WBO(db.Model):
    collection      = db.ReferenceProperty(Collection, required=True)
    wbo_id          = db.StringProperty(required=True)
    modified        = db.FloatProperty(required=True)
    parentid        = db.StringProperty()
    predecessorid   = db.StringProperty()
    sortindex       = db.IntegerProperty(default=0)
    payload         = db.TextProperty(required=True)
    payload_size    = db.IntegerProperty(default=0)

    # TODO: Move this to config somewhere
    WEAVE_PAYLOAD_MAX_SIZE = 262144 

    def to_dict(self):
        """Produce a dict representation, usable for JSON response"""
        wbo_data = dict( (k,getattr(self, k)) for k in ( 
            'sortindex', 'parentid', 'predecessorid', 
            'payload', 'payload_size', 'modified'
        ) if getattr(self, k))
        wbo_data['id'] = self.wbo_id
        return wbo_data

    @classmethod
    def build_key_name(cls, wbo_data):
        """Build a collection-unique key name for a WBO"""
        return wbo_data['wbo_id']

    @classmethod
    def from_json(cls, data_in):
        wbo, errors = None, []

        if 'collection' not in data_in:
            if 'user_name' in data_in:
                data_in['profile'] = Profile.get_by_user_name(data_in['user_name'])
                del data_in['user_name']

            if 'collection_name' in data_in:
                data_in['collection'] = Collection.get_by_profile_and_name(
                    data_in['profile'], data_in['collection_name']
                )
                del data_in['profile']
                del data_in['collection_name']

        if 'id' in data_in:
            data_in['wbo_id'] = data_in['id']
            del data_in['id']

        wbo_data = dict((k,data_in[k]) for k in (
            'sortindex',
            'parentid',
            'predecessorid',
            'payload',
        ) if (k in data_in))
        
        wbo_now    = WBO.get_time_now()
        wbo_id     = data_in['wbo_id']
        collection = data_in['collection']

        wbo_data.update({
            'collection': collection,
            'parent': collection,
            'modified': wbo_now,
            'wbo_id': wbo_id,
        })

        if 'payload' in wbo_data:
            wbo_data['payload_size'] = len(wbo_data['payload'])

        errors = cls.validate(wbo_data)
        if len(errors) > 0: return (None, errors)

        wbo_data['key_name'] = cls.build_key_name(wbo_data)
        wbo = WBO(**wbo_data)

        return (wbo, errors)

    @classmethod
    def get_time_now(cls):
        """Get the current time in microseconds"""
        tn = datetime.now()
        tt = tn.timetuple()
        tm = mktime(tt)
        ms = (tn.microsecond/1000000.0)
        st = tm+ms
        return round(st,2)

    @classmethod
    def get_by_collection(cls, collection):
        return cls.all().ancestor(collection)

    @classmethod
    def get_by_collection_and_wbo_id(cls, collection, wbo_id):
        """Get a WBO by wbo_id"""
        return WBO.all().ancestor(collection).filter('wbo_id =', wbo_id).get()

    @classmethod
    def exists_by_collection_and_wbo_id(cls, collection, wbo_id):
        """Get a WBO by wbo_id"""
        return WBO.all().ancestor(collection).filter('wbo_id =', wbo_id).count() > 0

    @classmethod
    def validate(cls, wbo_data):
        """Validate the contents of this WBO"""
        errors = []

        if 'id' in wbo_data:
            wbo_data['wbo_id'] = wbo_data['id']
            del wbo_data['id']

        if ('wbo_id' not in wbo_data or not wbo_data['wbo_id'] or 
                len(wbo_data['wbo_id']) > 64 or '/' in wbo_data['wbo_id']):
            errors.append('invalid id')

        if ('collection' not in wbo_data or not wbo_data['collection'] or 
                len(wbo_data['collection'].name)>64):
            errors.append('invalid collection')

        if ('parentid' in wbo_data):
            if (len(wbo_data['parentid']) > 64):
                errors.append('invalid parentid')
            elif 'collection' in wbo_data:
                if not cls.exists_by_collection_and_wbo_id(wbo_data['collection'], wbo_data['parentid']):
                    errors.append('invalid parentid')

        if ('predecessorid' in wbo_data):
            if (len(wbo_data['predecessorid']) > 64):
                errors.append('invalid predecessorid')
            elif 'collection' in wbo_data:
                if not cls.exists_by_collection_and_wbo_id(wbo_data['collection'], wbo_data['predecessorid']):
                    errors.append('invalid predecessorid')

        if 'modified' not in wbo_data or not wbo_data['modified']:
            errors.append('no modification date')
        else:
            if type(wbo_data['modified']) is not float:
                errors.append('invalid modified date')

        if 'sortindex' in wbo_data:
            if (type(wbo_data['sortindex']) is not int or 
                    wbo_data['sortindex'] > 999999999 or
                    wbo_data['sortindex'] < -999999999):
                errors.append('invalid sortindex')

        if 'payload' in wbo_data:
            if (cls.WEAVE_PAYLOAD_MAX_SIZE and 
                    len(wbo_data['payload']) > cls.WEAVE_PAYLOAD_MAX_SIZE):
                errors.append('payload too large')
            else:
                try:
                    data = simplejson.loads(wbo_data['payload'])
                except ValueError, e:
                    errors.append('payload needs to be json-encoded')

        return errors

########NEW FILE########
__FILENAME__ = utils
"""
Random utilities

TODO: Put these in a better named package, instead of this grab bag
"""
import sys, os, os.path
base_dir = os.path.dirname( os.path.dirname(__file__) )
sys.path.extend([ os.path.join(base_dir, d) for d in ('lib', 'extlib')])

import urllib, base64
from django.utils import simplejson
from fxsync.models import Profile

def json_request(func):
    """Decorator to auto-decode JSON request body"""
    def cb(wh, *args, **kwargs):
        try:
            wh.request.body_json = simplejson.loads(wh.request.body)
        except ValueError:
            wh.response.set_status(400, message="Bad Request")
            wh.response.out.write("Invalid JSON request body")
        else:
            return func(wh, *args, **kwargs)
    return cb

def json_response(func):
    """Decorator to auto-encode return value as JSON response"""
    def cb(wh, *args, **kwargs):
        rv = func(wh, *args, **kwargs)
        if rv is not None:
            wh.response.headers['Content-Type'] = 'application/json'
            wh.response.out.write(simplejson.dumps(rv))
            return rv
    return cb

def profile_auth(func):
    """Decorator to wrap controller methods in profile auth requirement"""
    def cb(wh, *args, **kwargs):
        url_user = urllib.unquote(args[0])

        auth_header = wh.request.headers.get('Authorization')
        if auth_header == None:
            wh.response.set_status(401, message="Authorization Required")
            wh.response.headers['WWW-Authenticate'] = 'Basic realm="firefox-sync"'
            return
        
        auth_parts = auth_header.split(' ')
        user_arg, pass_arg = base64.b64decode(auth_parts[1]).split(':')

        valid_authen = (
            (url_user == user_arg) 
                and 
            Profile.authenticate(user_arg, pass_arg)
        )

        if not valid_authen:
            wh.response.set_status(401, message="Authorization Required")
            wh.response.headers['WWW-Authenticate'] = 'Basic realm="firefox-sync"'
            wh.response.out.write("Unauthorized")
        else:
            wh.request.profile = Profile.get_by_user_name(user_arg)
            return func(wh, *args, **kwargs)

    return cb

########NEW FILE########
__FILENAME__ = sync_api_tests
import sys, os, os.path
base_dir = os.path.dirname( os.path.dirname(__file__) )
sys.path.extend([ os.path.join(base_dir, d) for d in (
    'lib', 'extlib', 'controllers'
)])

import unittest, logging, datetime, time, base64
import webtest, random, string
from google.appengine.ext import webapp, db
from django.utils import simplejson

from fxsync.models import Profile, Collection, WBO
import sync_api

class SyncApiTests(unittest.TestCase):
    """Unit tests for the Sync API controller"""

    USER_NAME = 'tester123'
    PASSWD    = 'QsEdRgTh12345'

    value_keys = (
        'id', 'sortindex', 'parentid', 'predecessorid', 'payload'
    )
    value_sets = (
        ('xx00',  0, 'a1', 'b3', 'payload-xx00'),
        ('xx01',  1, 'a1', 'b3', 'payload-xx01'),
        ('xx02',  2, 'a1', 'b3', 'payload-xx02'),
        ('xx03',  3, 'a1', 'b3', 'payload-xx03'),
        ('xx04',  4, 'a1', 'b3', 'payload-xx04'),
        ('xx05',  5, 'a2', 'b3', 'payload-xx05'),
        ('xx06',  6, 'a2', 'b3', 'payload-xx06'),
        ('xx07',  7, 'a2', 'b3', 'payload-xx07'),
        ('xx08',  8, 'a2', 'b3', 'payload-xx08'),
        ('xx09',  9, 'a2', 'b3', 'payload-xx09'),
        ('xx10', 10, 'a2', 'b3', 'payload-xx10'),
        ('xx11', 11, 'a2', 'b1', 'payload-xx11'),
        ('xx12', 12, 'a2', 'b1', 'payload-xx12'),
        ('xx13', 13, 'a3', 'b1', 'payload-xx13'),
        ('xx14', 14, 'a3', 'b1', 'payload-xx14'),
        ('xx15', 15, 'a3', 'b1', 'payload-xx15'),
        ('xx16', 16, 'xx', 'yy', 'payload-xx16'),
        ('xx17', 17, 'xx', 'yy', 'payload-xx17'),
    )

    def setUp(self):
        """Prepare for unit test"""
        self.log = logging.getLogger()
        self.log.setLevel(logging.DEBUG)
        
        # There shouldn't already be a profile, but just in case...
        profile = Profile.get_by_user_name(self.USER_NAME)
        if profile: profile.delete()

        # Create a new profile for tests.
        self.profile = p = Profile(
            user_name = self.USER_NAME,
            user_id   = '8675309',
            password  = self.PASSWD
        )
        self.profile.put()

        self.auth_header = self.build_auth_header(p.user_name, p.password)

        self.collection = Collection.get_by_profile_and_name(p, 'testing')

        self.wbo_values = [
            dict(zip(self.value_keys, value_set))
            for value_set in self.value_sets
        ]
        for w in self.wbo_values:
            w['payload'] = simplejson.dumps({ 'stuff': w['payload'] })
        
        # Build the app test harness.
        self.app = webtest.TestApp(sync_api.application())

    def tearDown(self):
        """Clean up after unit test"""
        # Is this actually needed, since storage is mocked?
        self.profile.delete()
        q = WBO.all()
        for o in q: o.delete()
        q = Collection.all()
        for o in q: o.delete()

    def test_profile_auth(self):
        """Ensure access to sync API requires profile auth"""
        resp = self.app.get(
            '/sync/1.0/%s/info/collections' % self.USER_NAME,
            status=401
        )
        self.assertEqual('401 Authorization Required', resp.status)
        resp = self.app.get(
            '/sync/1.0/%s/info/collections' % self.USER_NAME,
            headers=self.build_auth_header()
        )
        self.assertEqual('200 OK', resp.status)

    def test_item_validation(self):
        """Exercise WBO data validation"""
        (p, c, ah) = (self.profile, self.collection, self.auth_header)
        too_long_id = ''.join('x' for x in range(100))

        self.assert_('invalid id' in WBO.validate({ 'id': '' }))
        self.assert_('invalid id' in WBO.validate({ 'id': 'foo/bar' }))
        self.assert_('invalid id' in WBO.validate({ 'id': too_long_id }))
        self.assert_('invalid id' not in WBO.validate({ 'id': 'abcd' }))

        self.assert_('invalid collection' in WBO.validate({ }))
        self.assert_('invalid collection' in 
            WBO.validate({ 'collection': Collection(name=too_long_id, profile=p) }))

        self.assert_('invalid predecessorid' in 
            WBO.validate({ 'collection':c, 'predecessorid': too_long_id }))
        self.assert_('invalid predecessorid' in 
            WBO.validate({ 'collection':c, 'predecessorid': 'abcdef' }))

        w = WBO(
            parent=c, collection=c, wbo_id='abcdef', 
            modified=WBO.get_time_now(), payload='test'
        )
        w.put()

        self.assert_('invalid predecessorid' not in 
            WBO.validate({ 'collection':c, 'predecessorid': 'abcdef' }))

        self.assert_('invalid predecessorid' in 
            WBO.validate({ 'collection':c, 'predecessorid': too_long_id }))
        self.assert_('invalid predecessorid' in 
            WBO.validate({ 'collection':c, 'predecessorid': 'defghi' }))

        w = WBO(
            parent=c, collection=c, wbo_id='defghi', 
            modified=WBO.get_time_now(), payload='test'
        )
        w.put()

        self.assert_('invalid predecessorid' not in 
            WBO.validate({ 'collection':c, 'predecessorid': 'abcdef' }))

        self.assert_('invalid modified date' in WBO.validate({ 'modified': 'abc' }))
        self.assert_('no modification date' in WBO.validate({ }))
        self.assert_('no modification date' in WBO.validate({ 'modified': '' }))

        self.assert_('invalid sortindex' in WBO.validate({ 'sortindex': 'abcd' }))
        self.assert_('invalid sortindex' in WBO.validate({ 'sortindex': -1000000000 }))
        self.assert_('invalid sortindex' in WBO.validate({ 'sortindex': 1000000000 }))

        self.assert_('payload needs to be json-encoded' in
            WBO.validate({ 'payload': 'abcd' }))
        self.assert_('payload too large' in 
            WBO.validate({ 'payload': 'x'.join('x' for x in range(500000)) }))

    def test_storage_single_put_get_delete(self):
        """Exercise storing and getting a single object"""
        collection = 'foo'
        wbo_data = { 
            "id": "abcd-1", 
            "sortindex": 1, 
            "payload": simplejson.dumps({ 'foo':1, 'bar':2 }),
            "modified": WBO.get_time_now()
        }
        auth_header = self.build_auth_header()
        storage_url = '/sync/1.0/%s/storage/%s/%s' % ( 
            self.USER_NAME, collection, wbo_data['id'] 
        )

        resp = self.app.get(storage_url, headers=auth_header, status=404)

        resp = self.app.put(storage_url, headers=auth_header, status=400,
            params="THIS IS NOT JSON")
        self.assertEqual('400 Bad Request', resp.status)

        resp = self.app.put(storage_url, headers=auth_header, 
            params=simplejson.dumps(wbo_data))
        self.assertEqual('200 OK', resp.status)
        self.assert_(WBO.get_time_now() >= float(resp.body))

        resp = self.app.get(storage_url, headers=auth_header)
        resp_wbo_data = simplejson.loads(resp.body)
        self.assertEqual(wbo_data['payload'], resp_wbo_data['payload'])

        resp = self.app.delete(storage_url, headers=auth_header)
        self.assertEqual('200 OK', resp.status)
        self.assert_(WBO.get_time_now() >= float(resp.body))

        resp = self.app.get(storage_url, headers=auth_header, status=404)

    def test_collection_counts_and_timestamps(self):
        """Exercise collection counts and timestamps"""
        profile = Profile(user_name = 'tester-1', user_id='8675309', password = 'pass-1')
        profile.put()

        auth_header = self.build_auth_header(
            profile.user_name, profile.password
        )

        expected_count_all = 0
        expected_counts = {
            'clients':2, 'crypto':0, 'forms':6, 'history':0, 'keys':10,
            'meta':12, 'bookmarks':14, 'prefs':16, 'tabs':18, 'passwords':20,
            'foo':12, 'bar':14, 'baz':16
        }
        expected_dates = {}

        # Insert objects with random contents to satisfy the expected counts
        for collection_name, curr_count in expected_counts.items():
            base_url = '/sync/1.0/%s/storage/%s' % (
                profile.user_name, collection_name
            )
            for i in range(curr_count):
                resp = self.put_random_wbo(base_url, auth_header)
                expected_dates[collection_name] = float(resp.body)
                expected_count_all += 1

        # Ensure the counts match expected
        resp = self.app.get(
            '/sync/1.0/%s/info/collection_counts' % (profile.user_name),
            headers=auth_header
        )
        resp_data = simplejson.loads(resp.body)
        self.assertEqual(expected_counts, resp_data)

        # Ensure all timestamps are same or newer than expected.
        resp = self.app.get(
            '/sync/1.0/%s/info/collections' % (profile.user_name),
            headers=auth_header
        )
        resp_data = simplejson.loads(resp.body)
        for k,v in expected_dates.items():
            self.assert_(k in resp_data)
            self.assert_(resp_data[k] >= expected_dates[k])

        # Verify the count of all objects after creating
        result_count = WBO.all().count()
        self.assertEqual(expected_count_all, result_count)

        # Delete each collection and verify the count after
        for collection_name, curr_count in expected_counts.items():
            url = '/sync/1.0/%s/storage/%s' % (
                profile.user_name, collection_name
            )
            resp = self.app.delete(url, headers=auth_header)
            self.assert_(WBO.get_time_now() >= float(resp.body))

            expected_count_all -= curr_count
            result_count = WBO.all().count()
            self.assertEqual(expected_count_all, result_count)

        # No WBOs should be left after all collections deleted.
        result_count = WBO.all().count()
        self.assertEqual(0, result_count)

    def test_multiple_profiles(self):
        """Exercise multiple profiles and collections"""
        expected_count_all = 0
        profiles_count = 5
        collection_names = ( 'testing', 'keys', 'tabs', 'history', 'bookmarks' )
        collection_counts = {}

        # Produce a set of Profiles in the datastore
        profiles = []
        for i in range(profiles_count):
            profile = Profile(user_name='t-%s'%i, user_id='id-%s'%i, password='p-%s'%i)
            profile.put()
            profiles.append(profile)

        # Generate collections for each profile.
        for p in profiles:
            auth_header = self.build_auth_header(p.user_name, p.password)
            collection_counts[p.user_name] = {}

            # Run through several collections and make WBOs
            for cn in collection_names:

                curr_count = random.randint(1,10)
                collection_counts[p.user_name][cn] = curr_count
                expected_count_all += curr_count

                # Generate a bunch of random-content WBOs
                base_url = '/sync/1.0/%s/storage/%s' % (p.user_name, cn)
                for i in range(curr_count):
                    resp = self.put_random_wbo(base_url, auth_header)

        # Ensure the total number of WBOs is correct.
        result_count_all = WBO.all().count()
        self.assertEqual(expected_count_all, result_count_all)

        # Ensure the counts for each profile collection matches inserts.
        for profile in profiles:
            counts = Collection.get_counts(profile)
            for name in collection_names:
                c = Collection.get_by_profile_and_name(profile, name)
                self.assertEqual(
                    collection_counts[profile.user_name][name],
                    WBO.get_by_collection(c).count()
                )

        # Delete each of the collections for each user.
        for profile in profiles:
            auth_header = self.build_auth_header(
                profile.user_name, profile.password
            )
            for name in collection_names:
                url = '/sync/1.0/%s/storage/%s' % (profile.user_name, name)
                resp = self.app.delete(url, headers=auth_header)
                # Ensure the individual collection is now empty.
                c = Collection.get_by_profile_and_name(profile, name)
                self.assertEqual(0, WBO.get_by_collection(c).count())

        # Ensure there are no more WBOs
        result_count_all = WBO.all().count()
        self.assertEqual(0, result_count_all)

    def test_retrieval_by_id(self):
        """Exercise collection retrieval with a single ID"""
        (p, c, ah) = (self.profile, self.collection, self.auth_header)

        wbo_id = '1234'

        w = WBO(wbo_id=wbo_id, parent=c, collection=c,
            modified=WBO.get_time_now(), sortindex=1000, 
            payload='payload-%s' % wbo_id, payload_size=9)
        w.put()

        url = '/sync/1.0/%s/storage/%s?id=%s' % (
            p.user_name, c.name, w.wbo_id
        )

        resp = self.app.get(url, headers=ah)
        result_data = simplejson.loads(resp.body)
        self.log.debug('RESPONSE %s' % resp.body)
        self.assertEqual(w.wbo_id, result_data[0])

        url = '/sync/1.0/%s/storage/%s?id=%s&full=1' % (
            p.user_name, c.name, w.wbo_id
        )

        resp = self.app.get(url, headers=ah)
        result_data = simplejson.loads(resp.body)
        self.log.debug('RESPONSE %s' % resp.body)
        self.assertEqual(w.payload, result_data[0]['payload'])

    def test_deletion_by_multiple_ids(self):
        """Exercise bulk deletion with a set of IDs"""
        (p, c, ah) = (self.profile, self.collection, self.auth_header)
        wbos = self.build_wbo_set()

        wbo_ids = [w.wbo_id for w in wbos]
        to_delete_ids = wbo_ids[0:len(wbo_ids)/2]
        
        url = '/sync/1.0/%s/storage/%s?ids=%s' % (
            p.user_name, c.name, ','.join(to_delete_ids)
        )

        resp = self.app.delete(url, headers=ah)
        self.assertEqual('200 OK', resp.status)
        self.assert_(WBO.get_time_now() >= float(resp.body))

        result_ids = [w.wbo_id for w in WBO.all()]
        for wbo_id in to_delete_ids:
            self.assert_(wbo_id not in result_ids)

    def test_retrieval_by_multiple_ids(self):
        """Exercise collection retrieval with multiple IDs"""
        (p, c, ah) = (self.profile, self.collection, self.auth_header)

        wbos = [ 
            WBO(wbo_id='%s' % wbo_id, parent=c, collection=c,
                modified=WBO.get_time_now(), sortindex=1000, payload='payload-%s' %
                wbo_id, payload_size=9
        ) for wbo_id in range(10) ]

        for w in wbos: w.put()

        wbo_ids = [w.wbo_id for w in wbos]

        url = '/sync/1.0/%s/storage/%s?ids=%s' % (
            p.user_name, c.name, ','.join(wbo_ids)
        )

        resp = self.app.get(url, headers=ah)
        result_data = simplejson.loads(resp.body)
        wbo_ids.sort()
        result_data.sort()
        self.assertEqual(wbo_ids, result_data)
        self.assertEqual(len(wbo_ids), int(resp.headers['X-Weave-Records']))

        url = '/sync/1.0/%s/storage/%s?ids=%s&full=1' % (
            p.user_name, c.name, ','.join(wbo_ids)
        )

        resp = self.app.get(url, headers=ah)
        result_data = simplejson.loads(resp.body)
        result_data.sort(lambda a,b: cmp(a['id'], b['id']))
        for idx in range(len(wbos)):
            self.assertEqual(wbos[idx].payload, result_data[idx]['payload'])
        self.assertEqual(len(wbo_ids), int(resp.headers['X-Weave-Records']))

    def test_retrieval_by_index_above_and_below(self):
        """Exercise collection retrieval on sortindex range"""
        (p, c, ah) = (self.profile, self.collection, self.auth_header)

        wbo_sortindexes = ( -100, -10, -1, 0, 1, 10, 23, 100, 999, 1000, 9999 )

        wbos = [ ]
        for idx in range(len(wbo_sortindexes)):
            sortindex = wbo_sortindexes[idx]
            wbo_id = '%s' % idx
            w = WBO(wbo_id=wbo_id, parent=c, collection=c,
                modified=WBO.get_time_now(), 
                sortindex=sortindex, 
                payload='payload-%s' % wbo_id, payload_size=9)
            w.put()
            self.log.debug("WBO      %s" % simplejson.dumps(w.to_dict()))
            wbos.append(w)

        # TODO: Try a variety of ranges here?
        (index_above, index_below) = (-10, 1000)

        expected_ids = [
            w.wbo_id for w in wbos
            if index_above < w.sortindex and w.sortindex < index_below
        ]

        url = '/sync/1.0/%s/storage/%s?index_above=%s&index_below=%s' % (
            p.user_name, c.name, index_above, index_below
        )
        resp = self.app.get(url, headers=ah)
        result_data = simplejson.loads(resp.body)

        expected_ids.sort()
        result_data.sort()

        self.log.debug("URL      %s" % url)
        self.log.debug("EXPECTED %s" % simplejson.dumps(expected_ids))
        self.log.debug("RESULT   %s" % resp.body)
        self.assertEqual(expected_ids, result_data)

    def test_retrieval_by_newer_and_older(self):
        """Exercise collection retrieval by modified timestamp range"""
        (p, c, ah) = (self.profile, self.collection, self.auth_header)
        wbos = self.build_wbo_set()

        # TODO: Try a variety of ranges here?
        (newer, older) = (wbos[2].modified, wbos[len(wbos)-2].modified)

        expected_ids = [
            w.wbo_id for w in wbos
            if newer < w.modified
        ]

        url = '/sync/1.0/%s/storage/%s?newer=%s' % (
            p.user_name, c.name, newer
        )
        resp = self.app.get(url, headers=ah)
        result_data = simplejson.loads(resp.body)

        expected_ids.sort()
        result_data.sort()

        self.log.debug("URL      %s" % url)
        self.log.debug("EXPECTED %s" % simplejson.dumps(expected_ids))
        self.log.debug("RESULT   %s" % resp.body)
        self.assertEqual(expected_ids, result_data)

        expected_ids = [
            w.wbo_id for w in wbos
            if newer < w.modified and w.modified < older
        ]

        url = '/sync/1.0/%s/storage/%s?newer=%s&older=%s' % (
            p.user_name, c.name, newer, older
        )
        resp = self.app.get(url, headers=ah)
        result_data = simplejson.loads(resp.body)

        expected_ids.sort()
        result_data.sort()

        self.log.debug("URL      %s" % url)
        self.log.debug("EXPECTED %s" % simplejson.dumps(expected_ids))
        self.log.debug("RESULT   %s" % resp.body)
        self.assertEqual(expected_ids, result_data)

    def test_retrieval_by_parent_and_predecessor(self):
        """Exercise collection retrieval by parent and predecessor IDs"""
        (p, c, ah) = (self.profile, self.collection, self.auth_header)
        wbos = self.build_wbo_set()

        id_sets = dict([
            (kind, set([ getattr(w, kind) for w in wbos ]))
            for kind in ('parentid', 'predecessorid')
        ])

        for kind, p_ids in id_sets.items():
            for p_id in set(p_ids):

                expected_ids = [
                    w.wbo_id for w in wbos
                    if getattr(w, kind) == p_id
                ]

                url = '/sync/1.0/%s/storage/%s?%s=%s' % (
                    p.user_name, c.name, kind, p_id
                )
                resp = self.app.get(url, headers=ah)
                result_data = simplejson.loads(resp.body)

                expected_ids.sort()
                result_data.sort()

                self.log.debug("URL      %s" % url)
                self.log.debug("EXPECTED %s" % simplejson.dumps(expected_ids))
                self.log.debug("RESULT   %s" % resp.body)
                self.assertEqual(expected_ids, result_data)

    def test_retrieval_with_sort(self):
        """Exercise collection retrieval with sort options"""
        (p, c, ah) = (self.profile, self.collection, self.auth_header)
        self.build_wbo_set()
        wbos = [ w for w in WBO.all() ]

        sorts = {
            'oldest': lambda a,b: cmp(a.modified,  b.modified),
            'newest': lambda a,b: cmp(b.modified,  a.modified),
            'index':  lambda a,b: cmp(b.sortindex, a.sortindex),
        }

        for sort_option, sort_fn in sorts.items():
            wbos.sort(sort_fn)
            expected_ids = [ w.wbo_id for w in wbos ]

            url = '/sync/1.0/%s/storage/%s?sort=%s' % (
                p.user_name, c.name, sort_option
            )
            resp = self.app.get(url, headers=ah)
            result_data = simplejson.loads(resp.body)

            self.log.debug("URL      %s" % url)
            self.log.debug("EXPECTED %s" % simplejson.dumps(expected_ids))
            self.log.debug("RESULT   %s" % resp.body)
            self.assertEqual(expected_ids, result_data)

    def test_retrieval_with_limit_offset(self):
        """Exercise collection retrieval with limit and offset"""
        (p, c, ah) = (self.profile, self.collection, self.auth_header)
        self.build_wbo_set()
        wbos = [ w for w in WBO.all() ]

        max_limit  = len(wbos) / 2
        max_offset = len(wbos) / 2

        for c_limit in range(1, max_limit):
            for c_offset in range(1, max_offset):

                expected_ids = [ 
                    w.wbo_id for w in 
                    wbos[ (c_offset) : (c_offset+c_limit) ] 
                ]

                url = '/sync/1.0/%s/storage/%s?limit=%s&offset=%s&sort=oldest' % (
                    p.user_name, c.name, c_limit, c_offset
                )
                resp = self.app.get(url, headers=ah)
                result_data = simplejson.loads(resp.body)

                self.log.debug("URL      %s" % url)
                self.log.debug("EXPECTED %s" % simplejson.dumps(expected_ids))
                self.log.debug("RESULT   %s" % resp.body)
                self.assertEqual(expected_ids, result_data)

    def test_retrieval_by_multiple_criteria(self):
        """Exercise retrieval when using multiple criteria"""
        (p, c, ah) = (self.profile, self.collection, self.auth_header)
        wbos = self.build_wbo_set()

        # Criteria set for testing.
        index_above   = 2
        index_below   = 13
        parentid      = 'a2'
        predecessorid = 'b3'

        expected_ids = []
        wbos.sort(lambda b,a: cmp(a.sortindex, b.sortindex))
        for w in wbos:
            if (index_above < w.sortindex and index_below > w.sortindex and
                    parentid == w.parentid and predecessorid == w.predecessorid):
                expected_ids.append(w.wbo_id)
         
        # Build and run a retrieval query using all of the criteria.
        params = 'index_above=%s&index_below=%s&parentid=%s&predecessorid=%s' % (
            index_above, index_below, parentid, predecessorid
        )
        url = '/sync/1.0/%s/storage/%s?%s' % (p.user_name, c.name, params)
        resp = self.app.get(url, headers=ah)
        result_data = simplejson.loads(resp.body)

        self.log.debug("URL      %s" % url)
        self.log.debug("EXPECTED %s" % simplejson.dumps(expected_ids))
        self.log.debug("RESULT   %s" % resp.body)
        self.assertEqual(expected_ids, result_data)

    def test_bulk_update(self):
        """Exercise bulk collection update"""
        (p, c, ah)  = (self.profile, self.collection, self.auth_header)
        auth_header = self.build_auth_header()
        storage_url = '/sync/1.0/%s/storage/%s' % (p.user_name, c.name)

        self.build_wbo_parents_and_predecessors()

        bulk_data = [
            { 'id': '' },
            { 'id': 'foo/bar', 'sortindex': 'abcd' },
            { 'id': 'a-1000',  'sortindex':-1000000000 },
            { 'id': 'a-1001',  'sortindex': 1000000000 },
            { 'id': 'a-1002',  'parentid': 'notfound' },
            { 'id': 'a-1003',  'predecessorid': 'notfound' },
            { 'id': 'a-1004',  'payload': 'invalid' },
        ]
        bulk_data.extend(self.wbo_values)

        self.log.debug("DATA %s" % simplejson.dumps(bulk_data))

        resp = self.app.post(
            storage_url, headers=auth_header, 
            params=simplejson.dumps(bulk_data)
        )
        self.assertEqual('200 OK', resp.status)
        result_data = simplejson.loads(resp.body)

        self.log.debug("RESULT %s" % resp.body)

        self.assert_(WBO.get_time_now() >= float(result_data['modified']))

        expected_ids = [ w['id'] for w in self.wbo_values ]
        self.assertEqual(expected_ids, result_data['success'])
        
        expected_failures = {
            "": ["invalid id"], 
            "a-1004": ["payload needs to be json-encoded"], 
            "a-1003": ["invalid predecessorid"], 
            "a-1002": ["invalid parentid"], 
            "a-1001": ["invalid sortindex"], 
            "a-1000": ["invalid sortindex"], 
            "foo/bar": ["invalid id", "invalid sortindex"]
        }
        self.assertEqual(expected_failures, result_data['failed'])

        stored_ids = [ w.wbo_id for w in WBO.all() ]
        for wbo_id in expected_ids:
            self.assert_(wbo_id in stored_ids)

    def test_alternate_output_formats(self):
        """Exercise alternate output formats"""
        (p, c, ah) = (self.profile, self.collection, self.auth_header)
        self.build_wbo_set()
        wbos = [ w for w in WBO.all() ]
        wbos.sort(lambda b,a: cmp(a.sortindex, b.sortindex))
        expected_ids = [ w.wbo_id for w in wbos ]

        url = '/sync/1.0/%s/storage/%s?full=1' % (p.user_name, c.name)
        resp = self.app.get(url, headers=ah)
        result_data = simplejson.loads(resp.body)
        result_ids = [ x['id'] for x in result_data ]
        self.assertEqual(expected_ids, result_ids)

        url = '/sync/1.0/%s/storage/%s?full=1' % (p.user_name, c.name)
        headers = { 'Accept': 'application/newlines' }
        headers.update(ah)
        resp = self.app.get(url, headers=headers)
        lines = resp.body.splitlines()
        for line in lines:
            data = simplejson.loads(line)
            self.assert_(data['id'] in expected_ids)

        if (False):
            url = '/sync/1.0/%s/storage/%s?full=1' % (p.user_name, c.name)
            headers = { 'Accept': 'application/whoisi' }
            headers.update(ah)
            resp = self.app.get(url, headers=headers)
            lines = "\n".split(resp.body)

            self.log.debug("URL      %s" % url)
            self.log.debug("RESULT   %s" % resp.body)
            self.log.debug("RESULT2  %s" % simplejson.dumps(lines))
            self.log.debug("LINES    %s" % len(lines))

    def test_cascading_profile_delete(self):
        """Ensure that profile deletion cascades down to collections and WBOs"""
        (p, c, ah) = (self.profile, self.collection, self.auth_header)
        wbos = self.build_wbo_set()

        self.assert_(WBO.all().count() > 0)
        self.assert_(Collection.all().count() > 0)
        self.assert_(Profile.all().count() > 0)

        p.delete()

        self.assertEquals(0, WBO.all().count())
        self.assertEquals(0, Collection.all().count())
        self.assertEquals(0, Profile.all().count())

    def test_cascading_collection_delete(self):
        """Ensure that collection deletion cascades down to WBOs"""
        (p, c, ah) = (self.profile, self.collection, self.auth_header)
        wbos = self.build_wbo_set()

        count_all = WBO.all().count()
        collections = [c for c in Collection.all().ancestor(p)]
        for c in collections:
            c_count = len([x for x in c.retrieve()])
            c.delete()
            count_all -= c_count
            self.assertEqual(count_all, WBO.all().count())

        self.assertEqual(0, WBO.all().count())

    def test_header_if_unmodified_since(self):
        """Ensure that X-If-Unmodified-Since header is honored in PUT / POST / DELETE"""
        self.fail("TODO")

    def build_wbo_parents_and_predecessors(self):
        (p, c, ah) = (self.profile, self.collection, self.auth_header)

        id_sets = dict([
            (kind, set([ w[kind] for w in self.wbo_values ]))
            for kind in ('parentid', 'predecessorid')
        ])

        for kind, id_set in id_sets.items():
            for wbo_id in id_set:
                w = WBO(
                    parent=c, collection=c,
                    modified = WBO.get_time_now(), 
                    wbo_id   = wbo_id, 
                    payload  = simplejson.dumps({'random':'xxx'})
                )
                w.put()

    def build_wbo_set(self, num_wbos=15):
        (p, c, ah) = (self.profile, self.collection, self.auth_header)

        self.build_wbo_parents_and_predecessors()

        wbos = []
        for values in self.wbo_values:
            w = WBO(
                parent=c, collection=c,
                modified=WBO.get_time_now(), 
                wbo_id        = values['id'], 
                parentid      = values['parentid'],
                predecessorid = values['predecessorid'],
                sortindex     = values['sortindex'], 
                payload       = values['payload']
            )
            w.put()
            wbos.append(w)
            time.sleep(0.1) # HACK: Delay to ensure modified stamps vary

        return wbos

    def put_random_wbo(self, url, auth_header):
        """PUT a randomized WBO, given a base URL and auth header"""
        wbo_id = random.randint(0, 1000000)
        wbo_json = simplejson.dumps({
            'sortindex': random.randint(0, 1000),
            'payload': simplejson.dumps({
                'random': ''.join(random.sample(string.letters, 16))
            })
        })
        return self.app.put(
            '%s/%s' % (url, wbo_id), 
            headers=auth_header, 
            params=wbo_json
        )

    def build_auth_header(self, user_name=None, passwd=None):
        """Build an HTTP Basic Auth header from user name and password"""
        user_name = user_name or self.USER_NAME
        passwd = passwd or self.PASSWD
        return {
            'Authorization': 'Basic %s' % base64.b64encode(
                '%s:%s' % (user_name, passwd)
            )
        }

########NEW FILE########
