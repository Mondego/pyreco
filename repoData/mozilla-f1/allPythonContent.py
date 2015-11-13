__FILENAME__ = build
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Sync Server
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Tarek Ziade (tarek@mozilla.com)
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
import os
import sys
import subprocess


CURDIR = os.path.dirname(__file__)
REPOS = {'github': ('git', 'git://github.com/mozilla/%s.git'),
         'mozilla': ('hg', 'https://hg.mozilla.org/services/%s')}
PYTHON = sys.executable


def _get_tags():
    sub = subprocess.Popen('git tag', shell=True, stdout=subprocess.PIPE)
    tags = [line.strip()
            for line in sub.stdout.read().strip().split('\n')
            if line.strip() != '']
    tags.reverse()
    return tags


def verify_tag(tag):
    if tag == 'tip' or tag.isdigit():
        return True
    return tag in _get_tags()


def get_latest_tag():
    tags = _get_tags()
    if len(tags) == 0:
        raise ValueError('Could not find a tag')
    return tags[0]


def _run(command):
    print(command)
    os.system(command)


def _envname(name):
    return name.upper().replace('-', '_')


def _update_cmd(project, latest_tags=False, repo_type='git'):
    if latest_tags:
        if repo_type == 'hg':
            return 'hg up -r "%s"' % get_latest_tag()
        else:
            return 'git checkout -r "%s"' % get_latest_tag()
    else:
        # looking for an environ with a specific tag or rev
        rev = os.environ.get(_envname(project))
        if rev is not None:
            if not verify_tag(rev):
                print('Unknown tag or revision: %s' % rev)
                sys.exit(1)
            if repo_type == 'git':
                return 'git checkout -r "%s"' % rev
            else:
                return 'hg up -r "%s"' % rev
        if repo_type == 'git':
            return 'git checkout'
        else:
            return 'hg up'


def build_app(name, latest_tags, deps):
    # building deps first
    build_deps(deps, latest_tags)

    # build the app now
    if not _has_spec():
        latest_tags = False

    _run(_update_cmd(name, latest_tags))
    _run('%s setup.py develop' % PYTHON)


def build_deps(deps, latest_tags):
    """Will make sure dependencies are up-to-date"""
    location = os.getcwd()
    # do we want the latest tags ?
    try:
        deps_dir = os.path.abspath(os.path.join(CURDIR, 'deps'))
        if not os.path.exists(deps_dir):
            os.mkdir(deps_dir)

        for dep in deps:
            root, name = dep.split(':')
            repo_type, repo_root = REPOS[root]
            repo = repo_root % name
            target = os.path.join(deps_dir, name)
            if os.path.exists(target):
                os.chdir(target)
                if repo_type == 'git':
                    _run('git pull')
                else:
                    _run('hg pull')
            else:
                if repo_type == 'git':
                    _run('git clone %s %s' % (repo, target))
                else:
                    _run('hg clone %s %s' % (repo, target))

                os.chdir(target)
            update_cmd = _update_cmd(dep, latest_tags, repo_type)
            _run(update_cmd)
            _run('%s setup.py develop' % PYTHON)
    finally:
        os.chdir(location)


def _has_spec():
    specs = [file_ for file_ in os.listdir('.')
             if file_.endswith('.spec')]
    return len(specs)


def main(project_name, deps):
    # check the provided values in the environ
    latest_tags = 'LATEST_TAGS' in os.environ

    if not latest_tags:
        # if we have some tags in the environ, check that they are all defined
        projects = list(deps)

        # is the root a project itself or just a placeholder ?
        if _has_spec():
            projects.append(project_name)

        tags = {}
        missing = 0
        for project in projects:
            tag = _envname(project)
            if tag in os.environ:
                tags[tag] = os.environ[tag]
            else:
                tags[tag] = 'Not provided'
                missing += 1

        # we want all tag or no tag
        if missing > 0 and missing < len(projects):
            print("You did not specify all tags: ")
            for project, tag in tags.items():
                print('    %s: %s' % (project, tag))
            sys.exit(1)

    build_app(project_name, latest_tags, deps)


if __name__ == '__main__':
    project_name = sys.argv[1]
    deps = [dep.strip() for dep in sys.argv[2].split(',')]
    main(project_name, deps)

########NEW FILE########
__FILENAME__ = send
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Raindrop.
#
# The Initial Developer of the Original Code is
# Mozilla Messaging, Inc..
# Portions created by the Initial Developer are Copyright (C) 2009
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#

# The Grinder 3.4
# HTTP script originally recorded by TCPProxy, but then hacked...

from net.grinder.script import Test
from net.grinder.script.Grinder import grinder
from net.grinder.plugin.http import HTTPPluginControl, HTTPRequest
from HTTPClient import NVPair
from HTTPClient import Cookie, CookieModule, CookiePolicyHandler

connectionDefaults = HTTPPluginControl.getConnectionDefaults()

# Decode gzipped responses
connectionDefaults.useContentEncoding = 1
# in ms
connectionDefaults.setTimeout(60000)

httpUtilities = HTTPPluginControl.getHTTPUtilities()

log = grinder.logger.output

# Properties read from the grinder .properties file.
# After how many 'send' requests should we perform oauth?  This is to
# simulate cookie expiry or session timeouts.
sends_per_oauth = grinder.getProperties().getInt("linkdrop.sends_per_oauth", 0)

# The URL of the server we want to hit.
linkdrop_host = grinder.getProperties().getProperty("linkdrop.host", 'http://127.0.0.1:5000')

# Service we want to test
linkdrop_service = grinder.getProperties().getProperty("linkdrop.service", 'twitter.com')

# Static URL we want to hit
linkdrop_static_url = grinder.getProperties().getProperty("linkdrop.static_url", '/share/')

# How often we want to hit the static page per send
linkdrop_static_per_send = grinder.getProperties().getInt("linkdrop.static_per_send", 0)

# *sob* - failed to get json packages working.  Using 're' is an option,
# although it requires you install jython2.5 (which still doesn't have
# json builtin) - so to avoid all that complication, hack 'eval' into
# working for us...
_json_ns = {'null': None}
def json_loads(val):
    return eval(val, _json_ns)

CookieModule.setCookiePolicyHandler(None)
from net.grinder.plugin.http import HTTPPluginControl
HTTPPluginControl.getConnectionDefaults().followRedirects = 1

# To use a proxy server, uncomment the next line and set the host and port.
# connectionDefaults.setProxyServer("localhost", 8001)

# These definitions at the top level of the file are evaluated once,
# when the worker process is started.
connectionDefaults.defaultHeaders = \
  [ NVPair('Accept-Language', 'en-us,en;q=0.5'),
    NVPair('Accept-Charset', 'ISO-8859-1,utf-8;q=0.7,*;q=0.7'),
    NVPair('Accept-Encoding', 'gzip, deflate'),
    NVPair('User-Agent', 'Mozilla/5.0 (Windows NT 6.0; WOW64; rv:2.0b6) Gecko/20100101 Firefox/4.0b6'), ]

request1 = HTTPRequest()

def authService():
    threadContext = HTTPPluginControl.getThreadHTTPClientContext()
    CookieModule.discardAllCookies(threadContext)
    # Call authorize requesting we land back on /account/get - after
    # a couple of redirects for auth, we should wind up with the data from
    # account/get - which should now include our account info.
    result = request1.POST(linkdrop_host + '/api/account/authorize',
      (
        NVPair('domain', linkdrop_service),
        NVPair('end_point_success', '/api/account/get'),
        NVPair('end_point_auth_failure', '/current/send/auth.html#oauth_failure'), ),
      ( NVPair('Content-Type', 'application/x-www-form-urlencoded'), ))
    assert result.getStatusCode()==200, result
    data = json_loads(result.getText())
    assert data, 'account/get failed to return data'
    userid = data[0]['accounts'][0]['userid']
    for cookie in CookieModule.listAllCookies(threadContext):
        if cookie.name == "linkdrop":
            linkdrop_cookie = cookie
    assert linkdrop_cookie
    return userid, linkdrop_cookie

authService = Test(3, "auth %s" % linkdrop_service).wrap(authService)

def send(userid, domain=linkdrop_service, message="take that!"):
    """POST send."""
    assert userid, 'userid id set'
    result = request1.POST(linkdrop_host + '/api/send',
      ( NVPair('domain', domain),
        NVPair('userid', userid),
        # NOTE: no 'link' as we don't want to hit bitly in these tests
        # (and if we ever decide we do, we must not use the bitly production
        # userid and key!)
        # NVPair('link', "http://www.google.com/%s" % grinder.getRunNumber() ),
        NVPair('message', message), ),
      ( NVPair('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8'), ))
    assert result.getStatusCode()==200, result
    assert '"error": null' in result.getText(), result.getText()
    return result

send = Test(4, "Send message").wrap(send)

def getStatic(url="/share/"):
    result = request1.GET(linkdrop_host + url)
    assert result.getStatusCode()==200, result
    return result

getStatic = Test(5, "Static request").wrap(getStatic)

# The test itself.
class TestRunner:
    """A TestRunner instance is created for each worker thread."""
    def __init__(self):
        self.linkdrop_cookie = None
        self.userid = None

    def doit(self):
        if linkdrop_static_per_send:
            for i in range(0,linkdrop_static_per_send):
                getStatic(linkdrop_static_url)
            
        if (sends_per_oauth and grinder.getRunNumber() % sends_per_oauth==0):
            self.linkdrop_cookie = None
            self.userid = None

        if self.userid is None:
            self.userid, self.linkdrop_cookie = authService()
        
        # cookies are reset by the grinder each test run - re-inject the
        # linkdrop session cookie.
        threadContext = HTTPPluginControl.getThreadHTTPClientContext()
        CookieModule.addCookie(self.linkdrop_cookie, threadContext)
        send(self.userid)

    # wrap the work in a grinder 'Test' - the unit where stats are collected.
    doit = Test(1, "send with oauth").wrap(doit)

    def __call__(self):
        """This method is called for every run performed by the worker thread."""
        TestRunner.doit(self)

########NEW FILE########
__FILENAME__ = sendutil
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Raindrop.
#
# The Initial Developer of the Original Code is
# Mozilla Messaging, Inc..
# Portions created by the Initial Developer are Copyright (C) 2009
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#

# The Grinder 3.4
# HTTP script originally recorded by TCPProxy, but then hacked...

from net.grinder.script import Test
from net.grinder.script.Grinder import grinder
from net.grinder.plugin.http import HTTPPluginControl, HTTPRequest
from HTTPClient import NVPair
from HTTPClient import Cookie, CookieModule, CookiePolicyHandler

connectionDefaults = HTTPPluginControl.getConnectionDefaults()
httpUtilities = HTTPPluginControl.getHTTPUtilities()

log = grinder.logger.output

# The URL of the server we want to hit.
url0 = 'http://127.0.0.1:5000'

# *sob* - failed to get json packages working.  Using 're' is an option,
# although it requires you install jython2.5 (which still doesn't have
# json builtin) - so to avoid all that complication, hack 'eval' into
# working for us...
_json_ns = {'null': None}
def json_loads(val):
    return eval(val, _json_ns)
    
CookieModule.setCookiePolicyHandler(None)
from net.grinder.plugin.http import HTTPPluginControl
HTTPPluginControl.getConnectionDefaults().followRedirects = 1

# To use a proxy server, uncomment the next line and set the host and port.
# connectionDefaults.setProxyServer("localhost", 8001)

# These definitions at the top level of the file are evaluated once,
# when the worker process is started.
connectionDefaults.defaultHeaders = \
  [ NVPair('Accept-Language', 'en-us,en;q=0.5'),
    NVPair('Accept-Charset', 'ISO-8859-1,utf-8;q=0.7,*;q=0.7'),
    NVPair('Accept-Encoding', 'gzip, deflate'),
    NVPair('User-Agent', 'Mozilla/5.0 (Windows NT 6.0; WOW64; rv:2.0b6) Gecko/20100101 Firefox/4.0b6'), ]

request1 = HTTPRequest()

def getCSRF():
    threadContext = HTTPPluginControl.getThreadHTTPClientContext()
    CookieModule.discardAllCookies(threadContext)
    result = request1.GET(url0 + '/api/account/get')
    assert result.getStatusCode()==200, result
    csrf = linkdrop = None
    for cookie in CookieModule.listAllCookies(threadContext):
        if cookie.name == "linkdrop":
            linkdrop = cookie
        if cookie.name == "csrf":
            csrf = cookie.value
    assert csrf and linkdrop
    return csrf, linkdrop

def authTwitter(csrf):
    # Call authorize requesting we land back on /account/get - after
    # a couple of redirects for auth, we should wind up with the data from
    # account/get - which should now include our account info.
    result = request1.POST(url0 + '/api/account/authorize',
      ( NVPair('csrftoken', csrf),
        NVPair('domain', 'twitter.com'),
        NVPair('end_point_success', '/api/account/get'),
        NVPair('end_point_auth_failure', '/send/auth.html#oauth_failure'), ),
      ( NVPair('Content-Type', 'application/x-www-form-urlencoded'), ))
    assert result.getStatusCode()==200, result
    data = json_loads(result.getText())
    assert data, 'account/get failed to return data'
    userid = data[0]['accounts'][0]['userid']
    return userid

def send(userid, csrf, domain="twitter.com", message="take that!"):
    """POST send."""
    result = request1.POST(url0 + '/api/send',
      ( NVPair('domain', domain),
        NVPair('userid', userid),
        NVPair('csrftoken', csrf),
        NVPair('message', message), ),
      ( NVPair('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8'), ))
    assert result.getStatusCode()==200, result
    assert '"error": null' in result.getText(), result.getText()
    return result

########NEW FILE########
__FILENAME__ = account
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Raindrop.
#
# The Initial Developer of the Original Code is
# Mozilla Messaging, Inc..
# Portions created by the Initial Developer are Copyright (C) 2009
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Rob Miller (rmiller@mozilla.com)
#

import urllib
import json
from datetime import datetime
from uuid import uuid1
import hashlib

from webob.exc import HTTPException
from webob.exc import HTTPFound

from linkoauth.errors import AccessException
from linkdrop import log
from linkdrop.controllers import get_services
from linkdrop.lib.base import BaseController
from linkdrop.lib.helpers import get_redirect_response
from linkdrop.lib.metrics import metrics


class AccountController(BaseController):
    """
Accounts
========

OAuth authorization api.

"""
    __api_controller__ = True  # for docs

    def _create_account(self, request, domain, userid, username):
        acct_hash = hashlib.sha1(
            "%s#%s" % ((username or '').encode('utf-8'),
                       (userid or '').encode('utf-8'))).hexdigest()
        acct = dict(key=str(uuid1()), domain=domain, userid=userid,
                    username=username)
        metrics.track(request, 'account-create', domain=domain,
                      acct_id=acct_hash)
        return acct

    # this is not a rest api
    def authorize(self, request, *args, **kw):
        provider = request.POST['domain']
        log.info("authorize request for %r", provider)
        services = get_services(self.app.config)
        session = request.environ.get('beaker.session', {})
        return services.request_access(provider, request, request.urlgen,
                                       session)

    # this is not a rest api
    def verify(self, request, *args, **kw):
        provider = request.params.get('provider')
        log.info("verify request for %r", provider)

        acct = dict()
        try:
            services = get_services(self.app.config)
            session = request.environ.get('beaker.session', {})
            user = services.verify(provider, request, request.urlgen, session)

            account = user['profile']['accounts'][0]
            if (not user.get('oauth_token')
                and not user.get('oauth_token_secret')):
                raise Exception('Unable to get OAUTH access')

            acct = self._create_account(request,
                                        provider,
                                        str(account['userid']),
                                        account['username'])
            acct['profile'] = user['profile']
            acct['oauth_token'] = user.get('oauth_token', None)
            if 'oauth_token_secret' in user:
                acct['oauth_token_secret'] = user['oauth_token_secret']
            acct['updated'] = datetime.now().isoformat()
        except AccessException, e:
            self._redirectException(request, e)
        # lib/oauth/*.py throws redirect exceptions in a number of
        # places and we don't want those "exceptions" to be logged as
        # errors.
        except HTTPException, e:
            log.info("account verification for %s caused a redirection: %s",
                     provider, e)
            raise
        except Exception, e:
            log.exception('failed to verify the %s account', provider)
            self._redirectException(request, e)
        resp = get_redirect_response(request.config.get('oauth_success'))
        resp.set_cookie('account_tokens', urllib.quote(json.dumps(acct)))
        raise resp.exception

    def _redirectException(self, request, e):
        err = urllib.urlencode([('error', str(e))])
        url = request.config.get('oauth_failure').split('#')
        raise HTTPFound(location='%s?%s#%s' % (url[0], err, url[1]))

########NEW FILE########
__FILENAME__ = contacts
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Raindrop.
#
# The Initial Developer of the Original Code is
# Mozilla Messaging, Inc..
# Portions created by the Initial Developer are Copyright (C) 2009
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Rob Miller (rmiller@mozilla.com)
#

import json

from linkoauth.errors import (OAuthKeysException, ServiceUnavailableException,
                              DomainNotRegisteredError)

from linkdrop.controllers import get_services
from linkdrop.lib.base import BaseController
from linkdrop.lib.helpers import json_exception_response, api_response
from linkdrop.lib.helpers import api_entry, api_arg, get_passthrough_headers
from linkdrop.lib import constants
from linkdrop.lib.metrics import metrics


class ContactsController(BaseController):
    """
Contacts
========

A proxy for retrieving contacts from a service.

"""
    __api_controller__ = True  # for docs

    @api_response
    @json_exception_response
    @api_entry(
        doc="""
contacts
--------

Get contacts from a service.
""",
        urlargs=[
            api_arg('domain', 'string', True, None, None, """
The domain of the service to get contacts from (e.g. google.com)
"""),
        ],
        queryargs=[
            # name, type, required, default, allowed, doc
            api_arg('username', 'string', False, None, None, """
The user name used by the service. The username or userid is required if more
than one account is setup for the service.
"""),
            api_arg('userid', 'string', False, None, None, """
The user id used by the service. The username or userid is required if more
than one account is setup for the service.
"""),
            api_arg('startindex', 'integer', False, 0, None, """
Start index used for paging results.
"""),
            api_arg('maxresults', 'integer', False, 25, None, """
Max results to be returned per request, used with startindex for paging.
"""),
            api_arg('group', 'string', False, 'Contacts', None, """
Name of the group to return.
"""),
        ],
        response={'type': 'object', 'doc': 'Portable Contacts Collection'})
    def get(self, request):
        domain = str(request.sync_info['domain'])
        page_data = request.POST.get('pageData', None)
        account_data = request.POST.get('account', None)

        acct = None
        if account_data:
            acct = json.loads(account_data)
        if not acct:
            metrics.track(request, 'contacts-noaccount', domain=domain)
            error = {'provider': domain,
                     'message': ("not logged in or no user account "
                                 "for that domain"),
                     'status': 401,
            }
            return {'result': None, 'error': error}

        headers = get_passthrough_headers(request)
        page_data = page_data and json.loads(page_data) or {}
        try:
            services = get_services(self.app.config)
            result, error = services.getcontacts(domain, acct, page_data,
                                                 headers)
        except DomainNotRegisteredError:
            error = {
                'message': "'domain' is invalid",
                'code': constants.INVALID_PARAMS,
            }
            return {'result': None, 'error': error}

        except OAuthKeysException, e:
            # more than likely we're missing oauth tokens for some reason.
            error = {'provider': domain,
                     'message': ("not logged in or no user account "
                                 "for that domain"),
                     'status': 401,
            }
            result = None
            metrics.track(request, 'contacts-oauth-keys-missing',
                          domain=domain)
        except ServiceUnavailableException, e:
            error = {'provider': domain,
                     'message': ("The service is temporarily unavailable "
                                 "- please try again later."),
                     'status': 503,
            }
            if e.debug_message:
                error['debug_message'] = e.debug_message
            result = None
            metrics.track(request, 'contacts-service-unavailable',
                          domain=domain)
        return {'result': result, 'error': error}

########NEW FILE########
__FILENAME__ = docs
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Raindrop.
#
# The Initial Developer of the Original Code is
# Mozilla Messaging, Inc..
# Portions created by the Initial Developer are Copyright (C) 2009
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#

import imp
import sys
import inspect
from docutils import core

from linkdrop.lib.base import BaseController
from linkdrop.lib.helpers import json_exception_response
from linkdrop.lib.helpers import api_response, api_entry


def reST_to_html_fragment(a_str):
    parts = core.publish_parts(
                          source=a_str,
                          writer_name='html')
    return parts['body_pre_docinfo'] + parts['fragment']


def import_module(partname, fqname, parent):
    try:
        return sys.modules[fqname]
    except KeyError:
        pass
    try:
        fp, pathname, stuff = imp.find_module(partname,
                                              parent and parent.__path__)
    except ImportError:
        return None
    try:
        m = imp.load_module(fqname, fp, pathname, stuff)
    finally:
        if fp:
            fp.close()
    if parent:
        setattr(parent, partname, m)
    return m


def getmodule(module_name):
    # XXX this should be generic and be able to auto-discover our controllers
    import linkdrop.controllers
    fqname = "linkdrop.controllers." + module_name
    try:
        return import_module(module_name, fqname, linkdrop.controllers)
    except ImportError, e:
        print "import error %s %r" % (module_name, e)
        return None


def getclass(module, classname):
    if classname not in dir(module):
        return None
    for (name, class_) in inspect.getmembers(module):
        if name == classname:
            break
        class_ = None
    if not class_ or not '__api_controller__' in class_.__dict__:
        return None
    return class_


class DocsController(BaseController):
    """
API Documentation
=================

Returns structured information about the Raindrop API, for use in user
interfaces that want to show an API reference.

"""
    __api_controller__ = True  # for docs

    @api_response
    @json_exception_response
    @api_entry(
        doc="""
docs/index
----------

Returns a json object containing documentation
""",
        response={'type': 'object',
                  'doc': ('An object that describes the API '
                          'methods and parameters.')})
    def index(self, request):
        # iterate through our routes and get the controller classes
        mapper = self.app.mapper
        module_names = {}
        for m in mapper.matchlist:
            module_name = m.defaults.get('controller', None)
            if not module_name:
                continue

            if module_name in module_names:
                # we've already got docs for this controller, just backfill
                # some additional data
                action = module_names[module_name]['methods'].get(
                    m.defaults['action'], None)
                if action:
                    action.setdefault('routes', []).append(m.routepath)
                continue

            # this is the first hit for this controller import the
            # module and create all documentation for the controller,
            # we'll backfill some data from Routes as we process more
            # mappings
            module = getmodule(module_name)
            if not module:
                continue

            classname = module_name.title() + 'Controller'
            class_ = getclass(module, classname)
            if not class_:
                continue

            doc = inspect.getdoc(class_)
            doc = doc and reST_to_html_fragment(doc)
            class_data = {
                'controller': classname,
                'doc': doc,
                'methods': {},
            }
            for (name, method) in inspect.getmembers(class_):
                if name[0] == "_":
                    continue
                f = class_data['methods'][name] = {}
                f.update(getattr(method, '__api', {}))
                if 'doc' in f:
                    f['doc'] = reST_to_html_fragment(f['doc'])
                else:
                    doc = inspect.getdoc(method)
                    f['doc'] = doc and reST_to_html_fragment(doc)

            module_names[module_name] = class_data
            action = class_data['methods'].get(m.defaults['action'], None)
            if action:
                action.setdefault('routes', []).append(m.routepath)

        return module_names

########NEW FILE########
__FILENAME__ = send
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Raindrop.
#
# The Initial Developer of the Original Code is
# Mozilla Messaging, Inc..
# Portions created by the Initial Developer are Copyright (C) 2009
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Rob Miller (rmiller@mozilla.com)
#
# ***** END LICENSE BLOCK *****

import logging
import json
import copy
from urlparse import urlparse
from paste.deploy.converters import asbool
import hashlib

from linkoauth.errors import (OAuthKeysException, ServiceUnavailableException,
                              DomainNotRegisteredError)

from linkdrop.controllers import get_services
from linkdrop.lib.base import BaseController
from linkdrop.lib.helpers import json_exception_response, api_response
from linkdrop.lib.helpers import api_entry, api_arg, get_passthrough_headers
from linkdrop.lib import constants
from linkdrop.lib.metrics import metrics
from linkdrop.lib.shortener import shorten_link

log = logging.getLogger(__name__)


class SendController(BaseController):
    """
Send
====

The 'send' namespace is used to send updates to our supported services.

"""
    __api_controller__ = True  # for docs

    @api_response
    @json_exception_response
    @api_entry(
        doc="""
send
----

Share a link through F1.
""",
        queryargs=[
            # name, type, required, default, allowed, doc
            api_arg('domain', 'string', True, None, None, """
Domain of service to share to (google.com for gmail, facebook.com, twitter.com)
"""),
            api_arg('message', 'string', True, None, None, """
Message entered by user
"""),
            api_arg('username', 'string', False, None, None, """
Optional username, required if more than one account is configured for """
                    """a domain.
"""),
            api_arg('userid', 'string', False, None, None, """
Optional userid, required if more than one account is configured for a domain.
"""),
            api_arg('link', 'string', False, None, None, """
URL to share
"""),
            api_arg('shorturl', 'string', False, None, None, """
Shortened version of URL to share
"""),
            api_arg('shorten', 'boolean', False, None, None, """
Force a shortening of the URL provided
"""),
            api_arg('to', 'string', False, None, None, """
Individual or group to share with, not supported by all services.
"""),
            api_arg('subject', 'string', False, None, None, """
Subject line for emails, not supported by all services.
"""),
            api_arg('picture', 'string', False, None, None, """
URL to publicly available thumbnail, not supported by all services.
"""),
            api_arg('picture_base64', 'string', False, None, None, """
Base 64 encoded PNG version of the picture used for attaching to emails.
"""),
            api_arg('description', 'string', False, None, None, """
Site provided description of the shared item, not supported by all services.
"""),
            api_arg('name', 'string', False, None, None, """
"""),
        ],
        response={'type': 'list', 'doc': 'raw data list'})
    def send(self, request):
        result = {}
        error = None
        acct = None
        domain = request.POST.get('domain')
        message = request.POST.get('message', '')
        username = request.POST.get('username')
        longurl = request.POST.get('link')
        shorten = asbool(request.POST.get('shorten', 0))
        shorturl = request.POST.get('shorturl')
        userid = request.POST.get('userid')
        to = request.POST.get('to')
        account_data = request.POST.get('account', None)
        if not domain:
            error = {
                'message': "'domain' is not optional",
                'code': constants.INVALID_PARAMS,
            }
            return {'result': result, 'error': error}

        if account_data:
            acct = json.loads(account_data)
        if not acct:
            metrics.track(request, 'send-noaccount', domain=domain)
            error = {'provider': domain,
                     'message': ("not logged in or no user "
                                 "account for that domain"),
                     'status': 401,
            }
            return {'result': result, 'error': error}

        args = copy.copy(request.POST)
        if shorten and not shorturl and longurl:
            link_timer = metrics.start_timer(request, long_url=longurl)
            u = urlparse(longurl)
            if not u.scheme:
                longurl = 'http://' + longurl
            shorturl = shorten_link(request.config, longurl)
            link_timer.track('link-shorten', short_url=shorturl)
            args['shorturl'] = shorturl

        acct_hash = hashlib.sha1(
            "%s#%s" % ((username or '').encode('utf-8'),
                       (userid or '').encode('utf-8'))).hexdigest()
        timer = metrics.start_timer(request, domain=domain,
                                    message_len=len(message),
                                    long_url=longurl,
                                    short_url=shorturl,
                                    acct_id=acct_hash)
        # send the item
        headers = get_passthrough_headers(request)
        try:
            services = get_services(self.app.config)
            result, error = services.sendmessage(domain, acct, message,
                                                 args, headers)
        except DomainNotRegisteredError:
            error = {
                'message': "'domain' is invalid",
                'code': constants.INVALID_PARAMS,
            }
            return {'result': result, 'error': error}
        except OAuthKeysException, e:
            # XXX - I doubt we really want a full exception logged here?
            #log.exception('error providing item to %s: %s', domain, e)
            # XXX we need to handle this better, but if for some reason the
            # oauth values are bad we will get a ValueError raised
            error = {'provider': domain,
                     'message': ("not logged in or no user account "
                                 "for that domain"),
                     'status': 401,
            }

            metrics.track(request, 'send-oauth-keys-missing', domain=domain)
            timer.track('send-error', error=error)
            return {'result': result, 'error': error}
        except ServiceUnavailableException, e:
            error = {'provider': domain,
                     'message': ("The service is temporarily unavailable "
                                 "- please try again later."),
                     'status': 503,
            }
            if e.debug_message:
                error['debug_message'] = e.debug_message
            metrics.track(request, 'send-service-unavailable', domain=domain)
            timer.track('send-error', error=error)
            return {'result': result, 'error': error}

        if error:
            timer.track('send-error', error=error)
            assert not result
            #log.error("send failure: %r %r %r", username, userid, error)
        else:
            # create a new record in the history table.
            assert result
            result['shorturl'] = shorturl
            result['from'] = userid
            result['to'] = to
            timer.track('send-success')
        # no redirects requests, just return the response.
        return {'result': result, 'error': error}

########NEW FILE########
__FILENAME__ = debug
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Raindrop.
#
# The Initial Developer of the Original Code is
# Mozilla Messaging, Inc..
# Portions created by the Initial Developer are Copyright (C) 2009
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#


# Guard the import of cProfile such that 2.4 people without lsprof can still
# use this script.
try:
    from cProfile import Profile
except ImportError:
    try:
        from lsprof import Profile
    except ImportError:
        from profile import Profile


class ContextualProfile(Profile):
    """ A subclass of Profile that adds a context manager for Python
    2.5 with: statements and a decorator.
    source: kernprof.py
    """

    def __init__(self, *args, **kwds):
        super(ContextualProfile, self).__init__(*args, **kwds)
        self.enable_count = 0

    def enable_by_count(self, subcalls=True, builtins=True):
        """ Enable the profiler if it hasn't been enabled before.
        """
        if self.enable_count == 0:
            self.enable(subcalls=subcalls, builtins=builtins)
        self.enable_count += 1

    def disable_by_count(self):
        """ Disable the profiler if the number of disable requests matches the
        number of enable requests.
        """
        if self.enable_count > 0:
            self.enable_count -= 1
            if self.enable_count == 0:
                self.disable()

    def __call__(self, func):
        """ Decorate a function to start the profiler on function entry and
        stop it on function exit.
        """
        def f(*args, **kwds):
            self.enable_by_count()
            try:
                result = func(*args, **kwds)
            finally:
                self.disable_by_count()
            return result
        f.__name__ = func.__name__
        f.__doc__ = func.__doc__
        f.__dict__.update(func.__dict__)
        return f

    def __enter__(self):
        self.enable_by_count()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disable_by_count()


# avoid having to remove all @profile decorators if you want to do
# a quick change to call profiling
def profile_wrapper(func):
    from decorator import decorator
    _profiler = __builtin__.__dict__['_profiler']  # make pyflakes happy

    def wrap(_f, *args, **kwds):
        if _profiler:
            if not hasattr(_f, '_prof_wrapped'):
                f = _profiler(_f)
                f._prof_wrapped = True
            return f(*args, **kwds)
        return _f(*args, **kwds)
    return decorator(wrap, func)

import __builtin__
__builtin__.__dict__['_profiler'] = None
__builtin__.__dict__['profile'] = profile_wrapper


class ProfilerMiddleware():
    """WSGI Middleware which profiles the subsequent handlers and outputs
    cachegrind files.

    in development.ini:

    [filter:profiler]
    enabled 0|1
    # type = line or call
    type = call|line
    # not used with line profiler, sort var is from cProfile
    sort = time
    # run a contextual profile
    builtin = 0|1
    # dump to stderr
    pprint = 0|1
    # convert to cachegrind (not used with line profiler)
    grind = 0|1
    # where to save profile data
    dir /some/predetermined/path

    Be sure apache has permission to write to profile_dir.

    Repeated runs will produce new profile output, remember to clean out
    the profile directoy on occasion.

    based on code from kernprof.py
    can use lsprofcalltree.py to convert profile data to kcachgrind format
    line profiling requires line_profiler: easy_install line_profiler
    """

    def __init__(self, app, g_config, config):
        self.app = app
        self.profile_type = config.get('type', 'call')
        self.profile_print = bool(int(config.get('pprint', '0')))
        self.profile_sort = config.get('sort', 'time')
        self.profile_grind = bool(int(config.get('grind', '0')))
        self.profile_builtin = bool(int(config.get('builtin', '0')))
        self.profile_data_dir = config.get('dir', None)

    def __call__(self, environ, start_response):
        """
        Profile this request and output results in a cachegrind
        compatible format.
        """
        catch_response = []
        body = []

        def replace_start_response(status, headers, exc_info=None):
            catch_response.extend([status, headers])
            start_response(status, headers, exc_info)
            return body.append

        def run_app():
            app_iter = self.app(environ, replace_start_response)
            try:
                body.extend(app_iter)
            finally:
                if hasattr(app_iter, 'close'):
                    app_iter.close()

        import __builtin__
        try:
            import lsprofcalltree
            calltree_enabled = True
        except ImportError:
            calltree_enabled = False

        import sys
        import os
        import time

        pstat_fn = None
        cg_fn = None

        calltree_enabled = calltree_enabled and self.profile_grind

        if self.profile_data_dir:
            # XXX fixme, this should end up in a better location
            if not os.path.exists(self.profile_data_dir):
                os.mkdir(self.profile_data_dir)
            path = environ.get('PATH_INFO', '/tmp')
            if path == '/':
                path = 'root'
            path = path.strip("/").replace("/", "_")
            pid = os.getpid()
            t = time.time()
            pstat_fn = os.path.join(self.profile_data_dir,
                                    "prof.out.%s.%d.%d" % (path, pid, t))
            if calltree_enabled:
                cg_fn = os.path.join(self.profile_data_dir,
                                     "cachegrind.out.%s.%d.%d" %
                                     (path, pid, t))

        if self.profile_type == 'line':
            import line_profiler
            p = line_profiler.LineProfiler()
            # line profiler aparently needs to be a builtin
            self.profile_builtin = True
            # line profiler has no get_stat, so converting to cachegrind
            # will not work
            calltree_enabled = False
        else:
            p = ContextualProfile()

        if self.profile_builtin:
            __builtin__.__dict__['_profiler'] = p

        if self.profile_type == 'line':
            # reset the profile for the next run
            for k in p.code_map.keys():
                p.code_map[k] = {}

        try:
            if self.profile_builtin:
                run_app()
            else:
                p.runctx('run_app()', globals(), locals())

        finally:
            if self.profile_print:
                if self.profile_type == 'line':
                    # line profiler doesn't support sort
                    p.print_stats()
                else:
                    p.print_stats(sort=self.profile_sort)

            if pstat_fn:
                print >> sys.stderr, "writing profile data to %s" % pstat_fn
                p.dump_stats(pstat_fn)

            if calltree_enabled:
                print >> sys.stderr, "writing cachegrind output to %s" % cg_fn
                k = lsprofcalltree.KCacheGrind(p)
                data = open(cg_fn, 'w+')
                k.output(data)
                data.close()
        return body


def make_profile_middleware(app, global_conf, **kw):
    """
    Wrap the application in a component that will profile each
    request.
    """
    return ProfilerMiddleware(app, global_conf, kw)


class DBGPMiddleware():
    """WSGI Middleware which loads the PyDBGP debugger.

    in development.ini:

    [DEFAULT]
    idekey         character key for use with dbgp proxy
    host           machine client debugger (e.g. Komodo IDE) or proxy runs on
    port           port the client debugger or proxy listens on
    breakonexcept  only start debugging when an uncaught exception occurs
    """

    def __init__(self, app, config, idekey='', host='127.0.0.1', port='9000',
                 breakonexcept='0'):
        self.app = app
        self.config = config

        self.idekey = idekey
        self.host = host
        self.port = int(port)
        self.brk = bool(int(breakonexcept))

    def __call__(self, environ, start_response):
        """
        Debug this request.
        """
        from dbgp import client
        if self.brk:
            # breaks on uncaught exceptions
            client.brkOnExcept(self.host, self.port, self.idekey)
        else:
            # breaks on the next executed line
            client.brk(self.host, self.port, self.idekey)

            # we might want to do this, but you end up in some random
            # middleware and it's not the best experience.  Instead, break
            # here, go set some breakpoints where you want to debug, the
            # continue

            #c = client.backendCmd(self.idekey)
            #c.stdin_enabled = 0
            #c.connect(self.host, self.port, 'application', [__file__])
            #
            ## despite it's name, this is how to run a function, it does not
            ## start a thread
            #return c.runThread(self.app, (environ, start_response), {})

        # run the app now, if you've stopped here in a debugger, I suggest
        # you go set some breakpoints and continue to those.
        return self.app(environ, start_response)


def make_dbgp_middleware(app, global_conf, idekey='', host='127.0.0.1',
                         port='9000', breakonexcept='0'):
    """
    Wrap the application in a component that will connect to a dbgp server
    for each request
    """
    return DBGPMiddleware(app, global_conf, idekey, host, port,
                          breakonexcept)

########NEW FILE########
__FILENAME__ = app_globals
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Raindrop.
#
# The Initial Developer of the Original Code is
# Mozilla Messaging, Inc..
# Portions created by the Initial Developer are Copyright (C) 2009
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#
"""The application's Globals object"""

from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options


class Globals(object):
    """Globals acts as a container for objects available throughout the
    life of the application

    """

    def __init__(self, config):
        """One instance of Globals is created during application
        initialization and is available during requests via the
        'app_globals' variable

        """
        self.cache = CacheManager(**parse_cache_config_options(config))

########NEW FILE########
__FILENAME__ = base
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Raindrop.
#
# The Initial Developer of the Original Code is
# Mozilla Messaging, Inc..
# Portions created by the Initial Developer are Copyright (C) 2009
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#

"""The base Controller API

Provides the BaseController class for subclassing.
"""


class BaseController(object):
    def __init__(self, app):
        self.app = app

########NEW FILE########
__FILENAME__ = constants


# json-rpc error codes, we'll use these since the error response object
# is basically json-rpc style.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

########NEW FILE########
__FILENAME__ = helpers
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Raindrop.
#
# The Initial Developer of the Original Code is
# Mozilla Messaging, Inc..
# Portions created by the Initial Developer are Copyright (C) 2009
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#

"""Helper functions

Consists of functions to typically be used within templates, but also
available to Controllers. This module is available to templates as 'h'.
"""
from decorator import decorator
import pprint
from xml.sax.saxutils import escape
import json
from webob.exc import HTTPException, status_map

import logging


from linkdrop.lib.metrics import metrics

log = logging.getLogger(__name__)


def get_redirect_response(url, code=302, additional_headers=[]):
    """Raises a redirect exception to the specified URL

    Optionally, a code variable may be passed with the status code of
    the redirect, ie::

        redirect(url(controller='home', action='index'), code=303)

    XXX explain additional_headers

    """
    exc = status_map[code]
    resp = exc(location=url)
    for k, v in additional_headers:
        resp.headers.add(k, v)
    return resp

## {{{ http://code.activestate.com/recipes/52281/ (r1) PSF License
import sgmllib
import string


class StrippingParser(sgmllib.SGMLParser):
    # These are the HTML tags that we will leave intact
    valid_tags = ('b', 'a', 'i', 'br', 'p')

    from htmlentitydefs import entitydefs  # replace entitydefs from sgmllib
    entitydefs  # make pyflakes happy

    def __init__(self):
        sgmllib.SGMLParser.__init__(self)
        self.result = ""
        self.endTagList = []

    def handle_data(self, data):
        if data:
            self.result = self.result + data

    def handle_charref(self, name):
        self.result = "%s&#%s;" % (self.result, name)

    def handle_entityref(self, name):
        if name in self.entitydefs:
            x = ';'
        else:
            # this breaks unstandard entities that end with ';'
            x = ''
        self.result = "%s&%s%s" % (self.result, name, x)

    def unknown_starttag(self, tag, attrs):
        """ Delete all tags except for legal ones """
        if tag in self.valid_tags:
            self.result = self.result + '<' + tag
            for k, v in attrs:
                if (string.lower(k[0:2]) != 'on'
                    and string.lower(v[0:10]) != 'javascript'):
                    self.result = '%s %s="%s"' % (self.result, k, v)
            endTag = '</%s>' % tag
            self.endTagList.insert(0, endTag)
            self.result = self.result + '>'

    def unknown_endtag(self, tag):
        if tag in self.valid_tags:
            self.result = "%s</%s>" % (self.result, tag)
            remTag = '</%s>' % tag
            self.endTagList.remove(remTag)

    def cleanup(self):
        """ Append missing closing tags """
        for j in range(len(self.endTagList)):
                self.result = self.result + self.endTagList[j]


def safeHTML(s):
    """ Strip illegal HTML tags from string s """
    parser = StrippingParser()
    parser.feed(s)
    parser.close()
    parser.cleanup()
    return parser.result
## end of http://code.activestate.com/recipes/52281/ }}}


# Fetch all of the headers in the originating request which we want to pass
# on to the services.
_PASSTHROUGH_HEADERS = ["Accept-Language"]
def get_passthrough_headers(request):
    headers = {}
    for name in _PASSTHROUGH_HEADERS:
        val = request.headers.get(name, None)
        if val is not None:
            headers[name] = val
    return headers


@decorator
def json_exception_response(func, *args, **kwargs):
    request = args[1]
    try:
        return func(*args, **kwargs)
    except HTTPException:
        raise
    except Exception, e:
        log.exception("%s(%s, %s) failed", func, args, kwargs)
        metrics.track(request, 'unhandled-exception',
                      function=func.__name__, error=e.__class__.__name__)
        return {
            'result': None,
            'error': {
                'name': e.__class__.__name__,
                'message': str(e),
            }
        }


@decorator
def api_response(func, *args, **kwargs):
    request = args[1]
    data = func(*args, **kwargs)
    format = request.params.get('format', 'json')

    if format == 'test':
        request.response.headers['Content-Type'] = 'text/plain'
        return pprint.pformat(data)
    elif format == 'xml':

        # a quick-dirty dict serializer
        def ser(d):
            r = ""
            for k, v in d.items():
                if isinstance(v, dict):
                    r += "<%s>%s</%s>" % (k, ser(v), k)
                elif isinstance(v, list):
                    for i in v:
                        #print k,i
                        r += ser({k: i})
                else:
                    r += "<%s>%s</%s>" % (k, escape("%s" % v), k)
            return r
        request.response.headers['Content-Type'] = 'text/xml'
        return ('<?xml version="1.0" encoding="UTF-8"?>'
                + ser({'response': data}).encode('utf-8'))
    request.response.headers['Content-Type'] = 'application/json'
    res = json.dumps(data)
    return res


def api_entry(**kw):
    """Decorator to add tags to functions.
    """
    def decorate(f):
        if not hasattr(f, "__api"):
            f.__api = kw
        if not getattr(f, "__doc__") and 'doc' in kw:
            doc = kw['doc'] + "\n"
            if 'name' in kw:
                doc = kw['name'] + "\n" + "=" * len(kw['name']) + "\n\n" + doc
            args = []
            for m in kw.get('urlargs', []):
                line = "  %(name)-20s %(type)-10s %(doc)s" % m
                opts = []
                if m['required']:
                    opts.append("required")
                if m['default']:
                    opts.append("default=%s" % m['default'])
                if m['allowed']:
                    opts.append("options=%r" % m['allowed'])
                if opts:
                    line = "%s (%s)" % (line, ','.join(opts),)
                args.append(line)
            args = []
            d = "URL Arguments\n-------------\n\n%s\n\n" % '\n'.join(args)
            for m in kw.get('queryargs', []):
                line = "  %(name)-20s %(type)-10s %(doc)s" % m
                opts = []
                if m['required']:
                    opts.append("required")
                if m['default']:
                    opts.append("default=%s" % m['default'])
                if m['allowed']:
                    opts.append("options=%r" % m['allowed'])
                if opts:
                    line = "%s (%s)" % (line, ','.join(opts),)
                args.append(line)
            d += ("Request Arguments\n-----------------\n\n%s\n\n"
                  % '\n'.join(args))
            if 'bodyargs' in kw:
                args = []
                assert 'body' not in kw, "can't specify body and bodyargs"
                for m in kw['bodyargs']:
                    line = "  %(name)-20s %(type)-10s %(doc)s" % m
                    opts = []
                    if m['required']:
                        opts.append("required")
                    if m['default']:
                        opts.append("default=%s" % m['default'])
                    if m['allowed']:
                        opts.append("options=%r" % m['allowed'])
                    if opts:
                        line = "%s (%s)" % (line, ','.join(opts),)
                    args.append(line)
                d = d + ("**Request Body**: A JSON object with the "
                        "following fields:\n")
                d = d + "\n".join(args) + "\n\n"
            elif 'body' in kw:
                d = d + ("**Request Body**:  %(type)-10s %(doc)s\n\n"
                        % kw['body'])
            if 'response' in kw:
                d = d + ("**Response Body**: %(type)-10s %(doc)s\n\n"
                        % kw['response'])
            f.__doc__ = doc + d
        return f
    return decorate


def api_arg(name, type=None, required=False, default=None, allowed=None,
            doc=None):
    return {
        'name': name,
        'type': type,
        'required': required,
        'default': default,
        'allowed': allowed,
        'doc': doc or '',
    }


if __name__ == '__main__':  # pragma: no cover

    @api_entry(
        name="contacts",
        body={'type': "json", 'doc': "A json object"},
        doc="""
See Portable Contacts for api for detailed documentation.

http://portablecontacts.net/draft-spec.html

**Examples**::

    /contacts                        returns all contacts
    /contacts/@{user}/@{group}       returns all contacts (user=me, group=all)
    /contacts/@{user}/@{group}/{id}  returns a specific contact

""",
        urlargs=[
            api_arg('user', 'string', True, None, ['me'],
                    'User to query'),
            api_arg('group', 'string', True, None, ['all', 'self'],
                    'Group to query'),
            api_arg('id', 'integer', False, None, None,
                    'Contact ID to return'),
            ],
        queryargs=[
            # name, type, required, default, allowed, doc
            api_arg('filterBy', 'string', False, None, None,
                    'Field name to query'),
            api_arg('filterOp', 'string', False, None,
                    ['equals', 'contains', 'startswith', 'present'],
                    'Filter operation'),
            api_arg('filterValue', 'string', False, None, None,
                    'A value to compare using filterOp '
                    '(not used with present)'),
            api_arg('startIndex', 'int', False, 0, None,
                    'The start index of the query, used for paging'),
            api_arg('count', 'int', False, 20, None,
                    'The number of results to return, used with paging'),
            api_arg('sortBy', 'string', False, 'ascending',
                    ['ascending', 'descending'],
                    'A list of conversation ids'),
            api_arg('sortOrder', 'string', False, 'ascending',
                    ['ascending', 'descending'], 'A list of conversation ids'),
            api_arg('fields', 'list', False, None, None,
                    'A list of fields to return'),
        ],
        response={'type': 'object',
                  'doc': ('An object that describes the API methods '
                          'and parameters.')})
    def foo():
        pass
    print foo.__doc__

########NEW FILE########
__FILENAME__ = metrics
# A simple metrics gathering interface for F1.
import time

_emptydict = {}


class MetricsConsumer(object):
    def consume(self, data):
        raise NotImplementedError


class MetricsCollector(object):
    def __init__(self, consumer):
        self.consumer = consumer
        self.enabled = True

    def _get_distinct_attrs(self, distinct_ob):
        # 'distinct attributes' are anything we want to group the metrics by -
        # eg, it may include the concept of a 'user', a 'remote address', etc.
        # if it is already a dict, assume it is already a set of attributes.
        if distinct_ob is None:
            return _emptydict
        if isinstance(distinct_ob, dict):
            return distinct_ob
        return self._distinct_object_to_attrs(distinct_ob)

    def _distinct_object_to_attrs(self, distinct_ob):
        raise NotImplementedError

    def track(self, distinct_ob, id, **data):
        if not self.enabled:
            return
        data.update(self._get_distinct_attrs(distinct_ob))
        # time can be formatted externally for lower perf impact here.
        data['when'] = time.time()
        data['id'] = id
        self.consumer.consume(data)

    def start_timer(self, distinct_ob, **init_data):
        init_data.update(self._get_distinct_attrs(distinct_ob))
        return TimedMetricsCollector(self, init_data)


class TimedMetricsCollector(object):
    def __init__(self, parent_collector, init_data):
        self.parent_collector = parent_collector
        self.init_data = init_data
        self.tracked = False
        self.started = time.time()

    def track(self, id, **data):
        assert not self.tracked
        self.tracked = True
        if self.init_data is not None:
            data.update(self.init_data)
        assert 'took' not in data, data
        data['took'] = time.time() - self.started
        self.parent_collector.track(None, id, **data)


# F1 specific stuff - should probably go into its own module once it gets
# more sophisticated or more options...
import logging
log = logging.getLogger('linkdrop-metrics')
errlog = logging.getLogger('linkdrop')


class F1MetricsConsumer(MetricsConsumer):
    def consume(self, data):
        # gozer has requested a simple format of name=value, space sep'd and
        # strings quoted.
        msg = " ".join(("%s=%r" % (n, v.encode("utf-8")
                                   if isinstance(v, unicode) else v)
                        for n, v in data.iteritems()))
        log.info("%s", msg)


class F1MetricsCollector(MetricsCollector):
    def _distinct_object_to_attrs(self, distinct_ob):
        # distinct_ob is expected to be a webob 'request' object
        # a proxy is used in production, so prefer HTTP_X_FORWARDED_FOR
        try:
            remote_address = distinct_ob.environ['HTTP_X_FORWARDED_FOR']
        except KeyError:
            remote_address = distinct_ob.environ.get("REMOTE_ADDR")
        # discard the last octet of the IP address.  Will almost certainly
        # need work for IPv6 :)
        result = {}
        if remote_address:
            try:
                remote_address = ".".join(remote_address.split(".", 3)[:-1]) \
                                 + ".0"
            except (ValueError, IndexError), exc:
                errlog.error("failed to anonymize remote address %r: %s",
                             remote_address, exc)
            else:
                result['remote_address'] = remote_address
        return result


# the object used by the code.
metrics = F1MetricsCollector(F1MetricsConsumer())

########NEW FILE########
__FILENAME__ = shortener
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Raindrop.
#
# The Initial Developer of the Original Code is
# Mozilla Messaging, Inc..
# Portions created by the Initial Developer are Copyright (C) 2009
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#

import cgi
import json
import urllib

import logging
log = logging.getLogger('__name__')


def shorten_link(config, long_url):
    longUrl = cgi.escape(long_url.encode('utf-8'))
    bitly_userid = config.get('bitly.userid')
    bitly_key = config.get('bitly.key')
    bitly_result = urllib.urlopen(
        "http://api.bit.ly/v3/shorten?"
        "login=%(bitly_userid)s&apiKey=%(bitly_key)s&"
        "longUrl=%(longUrl)s&format=json" % dict(longUrl=longUrl,
                                                 bitly_userid=bitly_userid,
                                                 bitly_key=bitly_key)).read()
    shorturl = bitly_data = None
    try:
        bitly_data = json.loads(bitly_result)['data']
        shorturl = bitly_data["url"]
    except (ValueError, TypeError):
        # bitly_data may be a list if there is an error, resulting in TypeError
        # when getting the url
        pass
    if not bitly_data or not shorturl:
        # The index of ['url'] is going to fail - it isn't clear what we
        # should do, but we might as well capture in the logs why.
        log.error("unexpected bitly response: %r", bitly_result)
    return shorturl

########NEW FILE########
__FILENAME__ = static
import os
import re

from paste import request
from paste import fileapp
from paste import httpexceptions
from paste.httpheaders import ETAG

version_re = re.compile("/\d+.\d+.\d+/", re.U)


class StaticURLParser(object):
    """
    based on Paste.urlparser.StaticURLParser, however we handle an internal
    redirect for versioning of static files.  This is only intended for
    development work, as we serve production from apache/mod_wsgi.
    """
    # @@: Should URLParser subclass from this?

    def __init__(self, directory, root_directory=None,
                 cache_max_age=None, version="/dev/"):
        self.directory = self.normpath(directory)
        self.root_directory = self.normpath(root_directory or directory)
        self.cache_max_age = cache_max_age
        self.version = version

    def normpath(path):
        return os.path.normcase(os.path.abspath(path))
    normpath = staticmethod(normpath)

    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO', '')
        if not path_info:
            return self.add_slash(environ, start_response)
        directory = "%s" % self.directory
        if (not path_info.startswith('/%s/' % self.version)
            and version_re.match(path_info) is None
            and directory == self.root_directory):
            directory = os.path.join(directory, self.version)
        if path_info == '/':
            # @@: This should obviously be configurable
            filename = 'index.html'
        else:
            filename = request.path_info_pop(environ)
        full = self.normpath(os.path.join(directory, filename))
        if not full.startswith(self.root_directory):
            # Out of bounds
            return self.not_found(environ, start_response)
        if not os.path.exists(full):
            return self.not_found(environ, start_response)
        if os.path.isdir(full):
            # @@: Cache?
            return self.__class__(full, root_directory=self.root_directory,
                                  version=self.version,
                                  cache_max_age=self.cache_max_age)(
                environ, start_response)
        if environ.get('PATH_INFO') and environ.get('PATH_INFO') != '/':
            return self.error_extra_path(environ, start_response)
        if_none_match = environ.get('HTTP_IF_NONE_MATCH')
        if if_none_match:
            mytime = os.stat(full).st_mtime
            if str(mytime) == if_none_match:
                headers = []
                ## FIXME: probably should be
                ## ETAG.update(headers, '"%s"' % mytime)
                ETAG.update(headers, mytime)
                start_response('304 Not Modified', headers)
                return ['']  # empty body

        fa = self.make_app(full)
        if self.cache_max_age:
            fa.cache_control(max_age=self.cache_max_age)
        return fa(environ, start_response)

    def make_app(self, filename):
        return fileapp.FileApp(filename)

    def add_slash(self, environ, start_response):
        """
        This happens when you try to get to a directory
        without a trailing /
        """
        url = request.construct_url(environ, with_query_string=False)
        url += '/'
        if environ.get('QUERY_STRING'):
            url += '?' + environ['QUERY_STRING']
        exc = httpexceptions.HTTPMovedPermanently(
            'The resource has moved to %s - you should be redirected '
            'automatically.' % url,
            headers=[('location', url)])
        return exc.wsgi_application(environ, start_response)

    def not_found(self, environ, start_response, debug_message=None):
        exc = httpexceptions.HTTPNotFound(
            'The resource at %s could not be found'
            % request.construct_url(environ),
            comment='SCRIPT_NAME=%r; PATH_INFO=%r; looking in %r; debug: %s'
            % (environ.get('SCRIPT_NAME'), environ.get('PATH_INFO'),
               self.directory, debug_message or '(none)'))
        return exc.wsgi_application(environ, start_response)

    def error_extra_path(self, environ, start_response):
        exc = httpexceptions.HTTPNotFound(
            'The trailing path %r is not allowed' % environ['PATH_INFO'])
        return exc.wsgi_application(environ, start_response)

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.directory)


def make_static(global_conf, document_root, cache_max_age=None, version="dev"):
    """
    Return a WSGI application that serves a directory (configured
    with document_root)

    cache_max_age - integer specifies CACHE_CONTROL max_age in seconds
    """
    if cache_max_age is not None:
        cache_max_age = int(cache_max_age)
    return StaticURLParser(
        document_root, cache_max_age=cache_max_age, version=version)

########NEW FILE########
__FILENAME__ = test_account
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Raindrop.
#
# The Initial Developer of the Original Code is
# Mozilla Messaging, Inc..
# Portions created by the Initial Developer are Copyright (C) 2009
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#    Rob Miller <rmiller@mozilla.com>
#
# ***** END LICENSE BLOCK *****

from linkdrop.controllers import account
from linkdrop.tests import TestController
from mock import Mock
from mock import patch
from nose import tools
from webob.exc import HTTPFound


class MockException(Exception):
    pass


class TestAccountController(TestController):
    def setUp(self):
        self.log_patcher = patch('linkdrop.controllers.account.log')
        self.gserv_patcher = patch('linkdrop.controllers.account.get_services')
        self.httpf_patcher = patch('linkdrop.controllers.account.HTTPFound')
        self.log_patcher.start()
        self.gserv_patcher.start()
        self.httpf_patcher.start()
        # funky hoop we jump through so we can tell what location gets passed
        account.HTTPFound.side_effect = HTTPFound
        self.request = Mock()
        self.controller = account.AccountController(self.app)

    def tearDown(self):
        self.log_patcher.stop()
        self.gserv_patcher.stop()
        self.httpf_patcher.stop()

    def test_authorize(self):
        provider = 'example.com'
        self.request.POST = dict(domain=provider)
        self.controller.authorize(self.request)
        logmsg = "authorize request for %r"
        account.log.info.assert_called_once_with(logmsg, provider)
        account.get_services.assert_called_once()
        mock_services = account.get_services()
        mock_services.request_access.assert_called_once_with(
            provider, self.request, self.request.urlgen,
            self.request.environ.get('beaker.session'))

    @patch('linkdrop.controllers.account.metrics')
    @patch('linkdrop.controllers.account.get_redirect_response')
    def test_verify(self, mock_get_redirect_response, mock_metrics):
        # first no oauth token -> verify failure
        provider = 'example.com'
        self.request.params = dict(provider=provider)
        self.request.config = dict(oauth_failure='http://example.com/foo#bar',
                                   oauth_success='SUCCESS')
        mock_services = account.get_services()
        mock_user = dict(profile={'accounts': (dict(),)},)
        mock_services.verify.return_value = mock_user
        mock_resp = mock_get_redirect_response()
        mock_resp.exception = MockException()
        tools.assert_raises(HTTPFound, self.controller.verify,
                            self.request)
        mock_services.verify.assert_called_with(
            provider, self.request, self.request.urlgen,
            self.request.environ.get('beaker.session'))
        errmsg = 'error=Unable+to+get+OAUTH+access'
        account.HTTPFound.assert_called_with(
            location='http://example.com/foo?%s#bar' % errmsg)

        # now with oauth token -> verify success
        mock_user = dict(profile={'accounts': ({'userid': 'USERID',
                                                'username': 'USERNAME'},)},
                         oauth_token=True,
                         oauth_token_secret=False)
        mock_services.verify.return_value = mock_user
        tools.assert_raises(MockException, self.controller.verify,
                            self.request)
        mock_get_redirect_response.assert_called_with('SUCCESS')

    @patch('linkdrop.controllers.account.get_redirect_response')
    def test_verify_access_exception(self, mock_get_redirect_response):
        provider = 'example.com'
        self.request.params = dict(provider=provider)
        self.request.config = dict(oauth_failure='http://example.com/foo#bar')
        mock_services = account.get_services()
        errmsg = 'ACCESSEXCEPTION'
        from linkoauth.errors import AccessException
        mock_services.verify.side_effect = AccessException(errmsg)
        mock_resp = mock_get_redirect_response()
        mock_resp.exception = MockException()
        tools.assert_raises(HTTPFound, self.controller.verify,
                            self.request)
        account.HTTPFound.assert_called_with(
            location='http://example.com/foo?error=%s#bar' % errmsg)

    @patch('linkdrop.controllers.account.get_redirect_response')
    def test_verify_http_exception(self, mock_get_redirect_response):
        provider = 'example.com'
        self.request.params = dict(provider=provider)
        self.request.config = dict(oauth_failure='http://example.com/foo#bar')
        mock_services = account.get_services()
        from linkdrop.controllers.account import HTTPException
        url = 'http://example.com/redirect'
        exc = HTTPException(url, None)
        mock_services.verify.side_effect = exc
        tools.assert_raises(HTTPException, self.controller.verify,
                            self.request)
        errmsg = "account verification for %s caused a redirection: %s"
        account.log.info.assert_called_with(errmsg, provider, exc)

########NEW FILE########
__FILENAME__ = test_contacts
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Raindrop.
#
# The Initial Developer of the Original Code is
# Mozilla Messaging, Inc..
# Portions created by the Initial Developer are Copyright (C) 2009
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#    Rob Miller <rmiller@mozilla.com>
#

from linkdrop.controllers import contacts
from linkdrop.tests import TestController
from mock import Mock
from mock import patch
from nose import tools
import json


class TestContactsController(TestController):
    def setUp(self):
        self.gserv_patcher = patch(
            'linkdrop.controllers.contacts.get_services')
        self.metrics_patcher = patch(
            'linkdrop.controllers.contacts.metrics')
        self.gserv_patcher.start()
        self.metrics_patcher.start()
        self.request = Mock()
        self.request.POST = dict()
        self.domain = 'example.com'
        self.request.sync_info = dict(domain=self.domain)
        self.controller = contacts.ContactsController(self.app)
        self.real_get = self.controller.get.undecorated.undecorated

    def tearDown(self):
        self.gserv_patcher.stop()
        self.metrics_patcher.stop()

    def test_get_no_acct(self):
        res = self.real_get(self.controller, self.request)
        contacts.metrics.track.assert_called_with(self.request,
                                                  'contacts-noaccount',
                                                  domain=self.domain)
        tools.ok_(res['result'] is None)
        tools.eq_(res['error']['provider'], self.domain)
        tools.eq_(res['error']['status'], 401)
        tools.ok_(res['error']['message'].startswith('not logged in'))

    def _setup_acct_data(self):
        acct_json = json.dumps({'username': 'USERNAME',
                                'userid': 'USERID'})
        self.request.POST['account'] = acct_json

    def test_get_no_provider(self):
        from linkoauth.errors import DomainNotRegisteredError
        mock_services = contacts.get_services()
        mock_services.getcontacts.side_effect = DomainNotRegisteredError()
        self._setup_acct_data()
        res = self.real_get(self.controller, self.request)
        tools.ok_(res['result'] is None)
        tools.eq_(res['error']['message'], "'domain' is invalid")

    def test_get_oauthkeysexception(self):
        from linkoauth.errors import OAuthKeysException
        oauthexc = OAuthKeysException('OAUTHKEYSEXCEPTION')
        mock_services = contacts.get_services()
        mock_services.getcontacts.side_effect = oauthexc
        domain = 'example.com'
        self._setup_acct_data()
        res = self.real_get(self.controller, self.request)
        contacts.metrics.track.assert_called_with(
            self.request, 'contacts-oauth-keys-missing',
            domain=self.domain)
        tools.ok_(res['result'] is None)
        tools.eq_(res['error']['provider'], self.domain)
        tools.eq_(res['error']['status'], 401)
        tools.ok_(res['error']['message'].startswith('not logged in'))

    def test_get_serviceunavailexception(self):
        from linkoauth.errors import ServiceUnavailableException
        servexc = ServiceUnavailableException('SERVUNAVAIL')
        mock_services = contacts.get_services()
        mock_services.getcontacts.side_effect = servexc
        self._setup_acct_data()
        res = self.real_get(self.controller, self.request)
        contacts.metrics.track.assert_called_with(
            self.request, 'contacts-service-unavailable',
            domain=self.domain)
        tools.ok_(res['result'] is None)
        tools.eq_(res['error']['provider'], self.domain)
        tools.eq_(res['error']['status'], 503)
        tools.ok_(res['error']['message'].startswith(
            'The service is temporarily unavailable'))

    def test_get_success(self):
        self._setup_acct_data()
        mock_services = contacts.get_services()
        mock_services.getcontacts.return_value = ('SUCCESS', None)
        res = self.real_get(self.controller, self.request)
        tools.eq_(res['result'], 'SUCCESS')
        tools.ok_(res['error'] is None)

########NEW FILE########
__FILENAME__ = test_send
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Raindrop.
#
# The Initial Developer of the Original Code is
# Mozilla Messaging, Inc..
# Portions created by the Initial Developer are Copyright (C) 2009
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#    Rob Miller <rmiller@mozilla.com>
#

from linkdrop.controllers import send
from linkdrop.tests import TestController
from mock import Mock
from mock import patch
from nose import tools
import hashlib
import json


class TestSendController(TestController):
    domain = 'example.com'
    username = 'USERNAME'
    userid = 'USERID'

    def setUp(self):
        self.gserv_patcher = patch(
            'linkdrop.controllers.send.get_services')
        self.metrics_patcher = patch(
            'linkdrop.controllers.send.metrics')
        self.gserv_patcher.start()
        self.metrics_patcher.start()
        self.request = Mock()
        self.request.POST = dict()
        self.controller = send.SendController(self.app)
        self.real_send = self.controller.send.undecorated.undecorated
        self.mock_sendmessage = send.get_services().sendmessage

    def tearDown(self):
        self.gserv_patcher.stop()
        self.metrics_patcher.stop()

    def _setup_domain(self, domain=None):
        if domain is None:
            domain = self.domain
        else:
            self.domain = domain
        self.request.POST['domain'] = domain

    def _setup_acct_data(self):
        self.request.POST['username'] = self.username
        self.request.POST['userid'] = self.userid
        acct_json = json.dumps({'username': self.username,
                                'userid': self.userid})
        self.request.POST['account'] = acct_json

    def _acct_hash(self):
        return hashlib.sha1(
            "%s#%s" % ((self.username).encode('utf-8'),
                       (self.userid).encode('utf-8'))).hexdigest()

    def _setup_provider(self, result=None, error=None):
        if result is None:
            result = dict(result='success', domain=self.domain)
        self.result = result
        self.error = error
        self.mock_sendmessage.return_value = result, error

    def test_send_no_domain(self):
        res = self.real_send(self.controller, self.request)
        tools.eq_(res['result'], dict())
        tools.eq_(res['error']['message'], "'domain' is not optional")

    def test_send_no_provider(self):
        self._setup_domain()
        self._setup_acct_data()
        from linkoauth.errors import DomainNotRegisteredError
        self.mock_sendmessage.side_effect = DomainNotRegisteredError
        res = self.real_send(self.controller, self.request)
        tools.eq_(res['result'], dict())
        tools.eq_(res['error']['message'], "'domain' is invalid")

    def test_send_no_acct(self):
        self._setup_domain()
        res = self.real_send(self.controller, self.request)
        send.metrics.track.assert_called_with(self.request, 'send-noaccount',
                                              domain=self.domain)
        tools.eq_(res['result'], dict())
        tools.ok_(res['error']['message'].startswith(
            'not logged in or no user'))
        tools.eq_(res['error']['provider'], self.domain)
        tools.eq_(res['error']['status'], 401)

    @patch('linkdrop.controllers.send.shorten_link')
    def test_send_shorten(self, mock_shorten):
        self._setup_domain()
        self._setup_acct_data()
        self._setup_provider()
        self.request.POST['shorten'] = True
        longurl = 'www.mozilla.org/path/to/something'
        self.request.POST['link'] = longurl
        shorturl = 'http://sh.ort/url'
        mock_shorten.return_value = shorturl
        res = self.real_send(self.controller, self.request)
        mock_shorten.assert_called_once_with(self.request.config,
                                             'http://' + longurl)
        timer_args = send.metrics.start_timer.call_args_list
        tools.eq_(len(timer_args), 2)
        tools.eq_(timer_args[0], ((self.request,), dict(long_url=longurl)))
        tools.eq_(timer_args[1][0][0], self.request)
        tools.eq_(timer_args[1][1]['long_url'], 'http://' + longurl)
        tools.eq_(timer_args[1][1]['short_url'], shorturl)
        tools.eq_(timer_args[1][1]['acct_id'], self._acct_hash())
        mock_timer = send.metrics.start_timer()
        track_args = mock_timer.track.call_args_list
        tools.eq_(len(track_args), 2)
        tools.eq_(track_args[0], (('link-shorten',),
                                 dict(short_url=shorturl)))
        tools.eq_(track_args[1], (('send-success',),))
        tools.eq_(res, dict(result=self.result, error=self.error))
        tools.eq_(res['result']['shorturl'], shorturl)

    def test_send_oauthkeysexception(self):
        from linkoauth.errors import OAuthKeysException

        def raise_oauthkeysexception(*args):
            raise OAuthKeysException('OAUTHKEYSEXCEPTION')
        self.mock_sendmessage.side_effect = raise_oauthkeysexception
        self._setup_domain()
        self._setup_acct_data()
        res = self.real_send(self.controller, self.request)
        send.metrics.track.assert_called_with(self.request,
                                              'send-oauth-keys-missing',
                                              domain=self.domain)
        tools.eq_(res['result'], dict())
        tools.eq_(res['error']['provider'], self.domain)
        tools.ok_(res['error']['message'].startswith(
            'not logged in or no user account'))
        tools.eq_(res['error']['status'], 401)

    def test_send_serviceunavailexception(self):
        from linkoauth.errors import ServiceUnavailableException
        debug_msg = 'DEBUG'
        e = ServiceUnavailableException('SERVUNAVAIL')
        e.debug_message = debug_msg
        self.mock_sendmessage.side_effect = e
        self._setup_domain()
        self._setup_acct_data()
        res = self.real_send(self.controller, self.request)
        send.metrics.track.assert_called_with(self.request,
                                              'send-service-unavailable',
                                              domain=self.domain)
        tools.eq_(res['result'], dict())
        tools.eq_(res['error']['provider'], self.domain)
        tools.ok_(res['error']['message'].startswith(
            'The service is temporarily unavailable'))
        tools.eq_(res['error']['status'], 503)
        tools.eq_(res['error']['debug_message'], debug_msg)

    def test_send_error(self):
        self._setup_domain()
        self._setup_acct_data()
        errmsg = 'ERROR'
        self.mock_sendmessage.return_value = (dict(), errmsg)
        res = self.real_send(self.controller, self.request)
        mock_timer = send.metrics.start_timer()
        mock_timer.track.assert_called_with('send-error', error=errmsg)
        tools.eq_(res['result'], dict())
        tools.eq_(res['error'], errmsg)

    def test_send_success(self):
        self._setup_domain()
        self._setup_acct_data()
        to_ = 'hueylewis@example.com'
        self.request.POST['to'] = to_
        self.mock_sendmessage.return_value = (
            dict(message='SUCCESS'), dict())
        res = self.real_send(self.controller, self.request)
        mock_timer = send.metrics.start_timer()
        mock_timer.track.assert_called_with('send-success')
        tools.eq_(res['result']['message'], 'SUCCESS')
        tools.ok_(res['result']['shorturl'] is None)
        tools.eq_(res['result']['from'], self.userid)
        tools.eq_(res['result']['to'], to_)

########NEW FILE########
__FILENAME__ = util
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Sync Server
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Tarek Ziade (tarek@mozilla.com)
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
"""
Various utilities
"""
import traceback
import random
import string
from hashlib import sha256, sha1
import base64
import simplejson as json
import itertools
import struct
from email.mime.text import MIMEText
from email.header import Header
import smtplib
import socket
import re
import datetime
import os
import logging
import urllib2
from urlparse import urlparse, urlunparse
from decimal import Decimal, InvalidOperation
import time

from webob.exc import HTTPBadRequest
from webob import Response


random.seed()
_RE_CODE = re.compile('[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}')


def randchar(chars=string.digits + string.letters):
    """Generates a random char using urandom.

    If the system does not support it, the function fallbacks on
    random.choice

    See Haypo's explanation on the used formula to pick a char:
    http://bitbucket.org/haypo/hasard/src/tip/doc/common_errors.rst
    """
    try:
        pos = int(float(ord(os.urandom(1))) * 256. / 255.)
        return chars[pos % len(chars)]
    except NotImplementedError:
        return random.choice(chars)


def text_response(data, **kw):
    """Returns Response containing a plain text"""
    return Response(str(data), content_type='text/plain', **kw)


def json_response(data, **kw):
    """Returns Response containing a json string"""
    return Response(json.dumps(data, use_decimal=True),
                               content_type='application/json', **kw)


def html_response(data, **kw):
    """Returns Response containing a plain text"""
    return Response(str(data), content_type='text/html', **kw)


def newlines_response(lines, **kw):
    """Returns a Response object containing a newlines output."""

    def _convert(line):
        line = json.dumps(line, use_decimal=True).replace('\n', '\u000a')
        return '%s\n' % line

    data = [_convert(line) for line in lines]
    return Response(''.join(data), content_type='application/newlines', **kw)


def whoisi_response(lines, **kw):
    """Returns a Response object containing a whoisi output."""

    def _convert(line):
        line = json.dumps(line, use_decimal=True)
        size = struct.pack('!I', len(line))
        return '%s%s' % (size, line)

    data = [_convert(line) for line in lines]
    return Response(''.join(data), content_type='application/whoisi', **kw)


def convert_response(request, lines, **kw):
    """Returns the response in the appropriate format, depending on the accept
    request."""
    content_type = request.accept.first_match(('application/json',
                                               'application/newlines',
                                               'application/whoisi'))

    if content_type == 'application/newlines':
        return newlines_response(lines, **kw)
    elif content_type == 'application/whoisi':
        return whoisi_response(lines, **kw)

    # default response format is json
    return json_response(lines, **kw)


def time2bigint(value):
    """Encodes a float timestamp into a big int"""
    return int(value * 100)


def bigint2time(value, precision=2):
    """Decodes a big int into a timestamp.

    The returned timestamp is a 2 digits Decimal.
    """
    if value is None:   # unexistant
        return None
    res = Decimal(value) / 100
    digits = '0' * precision
    return res.quantize(Decimal('1.' + digits))


def round_time(value=None, precision=2):
    """Transforms a timestamp into a two digits Decimal.

    Arg:
        value: timestamps representation - float or str.
        If None, uses time.time()

        precision: number of digits to keep. defaults to 2.

    Return:
        A Decimal two-digits instance.
    """
    if value is None:
        value = time.time()
    if not isinstance(value, str):
        value = str(value)

    try:
        digits = '0' * precision
        return Decimal(value).quantize(Decimal('1.' + digits))
    except InvalidOperation:
        raise ValueError(value)


_SALT_LEN = 8


def _gensalt():
    """Generates a salt"""
    return ''.join([randchar() for i in range(_SALT_LEN)])


def ssha(password, salt=None):
    """Returns a Salted-SHA password"""
    if salt is None:
        salt = _gensalt()
    ssha = base64.b64encode(sha1(password + salt).digest()
                               + salt).strip()
    return "{SSHA}%s" % ssha


def ssha256(password, salt=None):
    """Returns a Salted-SHA256 password"""
    if salt is None:
        salt = _gensalt()
    ssha = base64.b64encode(sha256(password + salt).digest()
                               + salt).strip()
    return "{SSHA-256}%s" % ssha


def validate_password(clear, hash):
    """Validates a Salted-SHA(256) password"""
    if hash.startswith('{SSHA-256}'):
        real_hash = hash.split('{SSHA-256}')[-1]
        hash_meth = ssha256
    else:
        real_hash = hash.split('{SSHA}')[-1]
        hash_meth = ssha

    salt = base64.decodestring(real_hash)[-_SALT_LEN:]
    password = hash_meth(clear, salt)
    return password == hash


def send_email(sender, rcpt, subject, body, smtp_host='localhost',
               smtp_port=25, smtp_user=None, smtp_password=None):
    """Sends a text/plain email synchronously.

    Args:
        sender: sender address - unicode + utf8
        rcpt: recipient address - unicode + utf8
        subject: subject - unicode + utf8
        body: email body - unicode + utf8
        smtp_host: smtp server -- defaults to localhost
        smtp_port: smtp port -- defaults to 25
        smtp_user: smtp user if the smtp server requires it
        smtp_password: smtp password if the smtp server requires it

    Returns:
        tuple: (True or False, Error Message)
    """
    # preparing the message
    msg = MIMEText(body.encode('utf8'), 'plain', 'utf8')
    msg['From'] = Header(sender, 'utf8')
    msg['To'] = Header(rcpt, 'utf8')
    msg['Subject'] = Header(subject, 'utf8')

    try:
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=5)
    except (smtplib.SMTPConnectError, socket.error), e:
        return False, str(e)

    # auth
    if smtp_user is not None and smtp_password is not None:
        try:
            server.login(smtp_user, smtp_password)
        except (smtplib.SMTPHeloError,
                smtplib.SMTPAuthenticationError,
                smtplib.SMTPException), e:
            return False, str(e)

    # the actual sending
    try:
        server.sendmail(sender, [rcpt], msg.as_string())
    finally:
        server.quit()

    return True, None


_USER = '(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))'
_IP_DOMAIN = '([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})'
_NAME_DOMAIN = '(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,})'
_DOMAIN = '(%s|%s)' % (_IP_DOMAIN, _NAME_DOMAIN)
_RE_EMAIL = '^%s@%s$' % (_USER, _DOMAIN)
_RE_EMAIL = re.compile(_RE_EMAIL)


def valid_email(email):
    """Checks if the email is well-formed

    Args:
        email: e-mail to check

    Returns:
        True or False
    """
    return _RE_EMAIL.match(email) is not None


def valid_password(user_name, password):
    """Checks a password strength.

    Args:
        user_name: user name associated with the password
        password: password

    Returns:
        True or False
    """
    if len(password) < 8:
        return False
    return user_name.lower().strip() != password.lower().strip()


def convert_config(config):
    """Loads the configuration.

    If a "configuration" option is found, reads it using config.Config.
    Each section/option is then converted to "section.option" in the resulting
    mapping.
    """
    from services.config import Config, convert
    res = {}
    for key, value in config.items():
        if not isinstance(value, basestring) or not value.startswith('file:'):
            res[key] = convert(value)
            continue
        # we load the configuration and inject it in the mapping
        filename = value[len('file:'):]
        if not os.path.exists(filename):
            raise ValueError('The configuration file was not found. "%s"' % \
                            filename)

        conf = Config(filename)
        res.update(conf.get_map())

    return res


def filter_params(namespace, data, replace_dot='_', splitchar='.'):
    """Keeps only params that starts with the namespace.
    """
    params = {}
    for key, value in data.items():
        if splitchar not in key:
            continue
        skey = key.split(splitchar)
        if skey[0] != namespace:
            continue
        params[replace_dot.join(skey[1:])] = value
    return params


def batch(iterable, size=100):
    """Returns the given iterable split into batches, of size."""
    counter = itertools.count()

    def ticker(key):
        return next(counter) // size

    for key, group in itertools.groupby(iter(iterable), ticker):
        yield group


class BackendError(Exception):
    """Raised when the backend is down or fails"""
    pass


class BackendTimeoutError(BackendError):
    """Raised when the backend times out."""
    pass


def generate_reset_code():
    """Generates a reset code

    Returns:
        reset code, expiration date
    """
    chars = string.ascii_uppercase + string.digits

    def _4chars():
        return ''.join([randchar(chars) for i in range(4)])

    code = '-'.join([_4chars() for i in range(4)])
    expiration = datetime.datetime.now() + datetime.timedelta(hours=6)
    return code, expiration


def check_reset_code(code):
    """Verify a reset code

    Args:
        code: reset code

    Returns:
        True or False
    """
    return _RE_CODE.match(code) is not None


class HTTPJsonBadRequest(HTTPBadRequest):
    """Allow WebOb Exception to hold Json responses.

    XXX Should be fixed in WebOb
    """
    def generate_response(self, environ, start_response):
        if self.content_length is not None:
            del self.content_length

        headerlist = [(key, value) for key, value in
                      list(self.headerlist)
                      if key != 'Content-Type']
        body = json.dumps(self.detail, use_decimal=True)
        resp = Response(body,
            status=self.status,
            headerlist=headerlist,
            content_type='application/json')
        return resp(environ, start_response)


def email_to_idn(addr):
    """ Convert an UTF-8 encoded email address to it's IDN (punycode)
        equivalent

        this method can raise the following:
        UnicodeError -- the passed string is not Unicode valid or BIDI
        compliant
          Be sure to examine the exception cause to determine the final error.
    """
    # decode the string if passed as MIME (some MIME encodes @)
    addr = urllib2.unquote(addr).decode('utf-8')
    if '@' not in addr:
        return addr
    prefix, suffix = addr.split('@', 1)
    return "%s@%s" % (prefix.encode('idna'), suffix.encode('idna'))


def extract_username(username):
    """Extracts the user name.

    Takes the username and if it is an email address, munges it down
    to the corresponding 32-character username
    """
    if '@' not in username:
        return username
    username = email_to_idn(username).lower()
    hashed = sha1(username).digest()
    return base64.b32encode(hashed).lower()


class CatchErrorMiddleware(object):
    """Middleware that catches error, log them and return a 500"""
    def __init__(self, app, logger_name='root', hook=None,
                 type='text/plain'):
        self.app = app
        self.logger = logging.getLogger(logger_name)
        self.hook = hook
        self.ctype = type

    def __call__(self, environ, start_response):
        try:
            return self.app(environ, start_response)
        except:
            err = traceback.format_exc()
            self.logger.error(err)
            start_response('500 Internal Server Error',
                           [('content-type', self.ctype)])
            response = "An unexpected error occurred"
            if self.hook:
                try:
                    response = self.hook()
                except Exception:
                    pass

            return [response]


def get_url(url, method='GET', data=None, user=None, password=None, timeout=5,
            get_body=True, extra_headers=None):
    """Performs a synchronous url call and returns the status and body.

    This function is to be used to provide a gateway service.

    If the url is not answering after `timeout` seconds, the function will
    return a (504, {}, error).

    If the url is not reachable at all, the function will
    return (502, {}, error)

    Other errors are managed by the urrlib2.urllopen call.

    Args:
        - url: url to visit
        - method: method to use
        - data: data to send
        - user: user to use for Basic Auth, if needed
        - password: password to use for Basic Auth
        - timeout: timeout in seconds.
        - extra headers: mapping of headers to add
        - get_body: if set to False, the body is not retrieved

    Returns:
        - tuple : status code, headers, body
    """
    req = urllib2.Request(url, data=data)
    req.get_method = lambda: method

    if user is not None and password is not None:
        auth = base64.encodestring('%s:%s' % (user, password))
        req.add_header("Authorization", "Basic %s" % auth.strip())

    if extra_headers is not None:
        for name, value in extra_headers.items():
            req.add_header(name, value)

    try:
        if hasattr(urllib2, 'old_urlopen'):
            urlopen = urllib2.old_urlopen
        else:
            urlopen = urllib2.urlopen

        res = urlopen(req, timeout=timeout)
    except urllib2.HTTPError, e:
        return e.code, {}, str(e)
    except urllib2.URLError, e:
        if isinstance(e.reason, socket.timeout):
            return 504, {}, str(e)
        return 502, {}, str(e)

    if get_body:
        body = res.read()
    else:
        body = ''

    return res.getcode(), dict(res.headers), body

from wsgiref.util import is_hop_by_hop


def proxy(request, scheme, netloc, timeout=5):
    """Proxies and return the result from the other server.

    - scheme: http or https
    - netloc: proxy location
    """
    parsed = urlparse(request.url)
    path = parsed.path
    params = parsed.params
    query = parsed.query
    fragment = parsed.fragment
    url = urlunparse((scheme, netloc, path, params, query, fragment))
    method = request.method

    if request.content_length:
        data = request.body
    else:
        data = None

    # copying all X- headers
    xheaders = {}
    for header, value in request.headers.items():
        if not header.startswith('X-'):
            continue
        xheaders[header] = value

    if 'X-Forwarded-For' not in request.headers:
        xheaders['X-Forwarded-For'] = request.remote_addr

    if hasattr(request, '_authorization'):
        xheaders['Authorization'] = request._authorization

    status, headers, body = get_url(url, method, data, timeout=timeout,
                                    extra_headers=xheaders)

    for name in list(headers.keys()):
        if is_hop_by_hop(name):
            del headers[name]
    return Response(body, status, headers.items())


def safe_execute(engine, *args, **kwargs):
    """Execution wrapper that will raise a HTTPServiceUnavailableError
    on any OperationalError errors and log it.
    """
    from sqlalchemy.exc import OperationalError
    try:
        return engine.execute(*args, **kwargs)
    except OperationalError:
        err = traceback.format_exc()
        from services import logger
        logger.error(err)
        raise BackendError()


def get_source_ip(environ):
    """Extracts the source IP from the environ."""
    if 'HTTP_X_FORWARDED_FOR' in environ:
        return environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
    elif 'REMOTE_ADDR' in environ:
        return environ['REMOTE_ADDR']
    return None

########NEW FILE########
__FILENAME__ = test_contacts
# Tests for invalid requests to the contacts end-point.
# This is primarily exercising missing and invalid params.
import json

from linkdrop.lib import constants

from linkdrop.tests import TestController
from linkdrop.tests import testable_services
from nose.tools import eq_
from routes.util import URLGenerator


class TestContactsInvalidParams(TestController):
    def getFullRequest(self, *except_for):
        account = {"oauth_token": "foo", "oauth_token_secret": "bar",
                   "profile": {"emails": [{'value': 'me@example.com'}],
                               "displayName": "Me",
                    },
                  }
        request = {'domain': 'google.com',
                   'account': json.dumps(account),
                   'to': 'you@example.com',
                }
        for elt in except_for:
            del request[elt]
        return request

    def checkContacts(self, request,
                  expected_message=None,
                  expected_code=constants.INVALID_PARAMS,
                  expected_status=None,
                  expected_http_code=200):

        # you must give *something* to check!
        assert expected_message or expected_code or expected_status
        domain = request.pop('domain')
        url = URLGenerator(self.app.mapper, dict(HTTP_HOST='localhost'))
        response = self.test_app.post(url(controller='contacts', action='get',
                                          domain=domain),
                                      params=request)
        assert response.status_int == expected_http_code, response.status_int
        try:
            got = json.loads(response.body)
        except ValueError:
            raise AssertionError("non-json response: %r" % (response.body,))

        assert 'error' in got, response.body
        if expected_message:
            eq_(got['error'].get('message'), expected_message, response.body)
        if expected_code:
            eq_(got['error'].get('code'), expected_code, response.body)
        if expected_status:
            eq_(got['error'].get('status'), expected_status, response.body)

    def testUnknownDomain(self):
        req = self.getFullRequest()
        req['domain'] = "foo.com"
        self.checkContacts(req)

    def testNoAccount(self):
        self.checkContacts(self.getFullRequest('account'), expected_status=401,
                           expected_code=None)

    # test missing OAuth params for each of the services.
    def checkMissingOAuth(self, service, missing_param):
        req = self.getFullRequest()
        req['domain'] = service
        acct = json.loads(req['account'])
        del acct[missing_param]
        req['account'] = json.dumps(acct)
        self.checkContacts(req, expected_status=401, expected_code=None)

    def testMissingOAuth(self):
        for service in testable_services:
            yield self.checkMissingOAuth, service, "oauth_token"

########NEW FILE########
__FILENAME__ = test_send
# Tests for invalid requests to the send end-point.
# This is primarily exercising missing and invalid params.
import json

from linkdrop.lib import constants

from linkdrop.tests import TestController
from linkdrop.tests import testable_services
from nose.tools import eq_
from routes.util import URLGenerator


class TestSendInvalidParams(TestController):
    def getFullRequest(self, *except_for):
        account = {"oauth_token": "foo", "oauth_token_secret": "bar",
                   "profile": {"emails": [{'value': 'me@example.com'}],
                            "displayName": "Me",
                    },
                  }
        result = {'domain': 'google.com',
                  'account': json.dumps(account),
                  'to': 'you@example.com',
                }
        for elt in except_for:
            del result[elt]
        return result

    def checkSend(self, request,
                  expected_message=None,
                  expected_code=constants.INVALID_PARAMS,
                  expected_status=None,
                  expected_http_code=200):
        # you must give *something* to check!
        assert expected_message or expected_code or expected_status
        url = URLGenerator(self.app.mapper, dict(HTTP_HOST='localhost'))
        response = self.test_app.post(url(controller='send', action='send'),
                                      params=request)

        assert response.status_int == expected_http_code, response.status_int
        try:
            got = json.loads(response.body)
        except ValueError:
            raise AssertionError("non-json response: %r" % (response.body,))

        assert 'error' in got, response.body
        if expected_message:
            eq_(got['error'].get('message'), expected_message, response.body)
        if expected_code:
            eq_(got['error'].get('code'), expected_code, response.body)
        if expected_status:
            eq_(got['error'].get('status'), expected_status, response.body)

    def testNoDomain(self):
        self.checkSend(self.getFullRequest('domain'))

    def testUnknownDomain(self):
        req = self.getFullRequest()
        req['domain'] = "foo.com"
        self.checkSend(req)

    def testNoAccount(self):
        self.checkSend(self.getFullRequest('account'), expected_status=401,
                       expected_code=None)

    # test missing OAuth params for each of the services.
    def checkMissingOAuth(self, service, missing_param):
        req = self.getFullRequest()
        req['domain'] = service
        acct = json.loads(req['account'])
        del acct[missing_param]
        req['account'] = json.dumps(acct)
        self.checkSend(req, expected_status=401, expected_code=None)

    def testMissingOAuth(self):
        for service in testable_services:
            yield self.checkMissingOAuth, service, "oauth_token"

########NEW FILE########
__FILENAME__ = test_helpers
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Raindrop.
#
# The Initial Developer of the Original Code is
# Mozilla Messaging, Inc..
# Portions created by the Initial Developer are Copyright (C) 2009
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#    Rob Miller <rmiller@mozilla.com>
#

from linkdrop.lib import helpers
from linkdrop.tests import TestController
from mock import Mock
from mock import patch
from nose import tools
import json
import pprint


class TestHelpers(TestController):
    @patch.dict('linkdrop.lib.helpers.status_map', {302: Mock()})
    def test_get_redirect_response(self):
        url = 'http://www.example.com/some/path'
        addl_headers = [('foo', 'bar'), ('baz', 'batch')]
        helpers.get_redirect_response(url, additional_headers=addl_headers)
        mock_resp = helpers.status_map[302]
        mock_resp.assert_called_once_with(location=url)
        headers_add_args = [args[0] for args in
                            mock_resp().headers.add.call_args_list if args]
        tools.eq_(dict(addl_headers), dict(headers_add_args))

    def test_safeHTML(self):
        unsafe = """
        <html><body><script>alert('hi');</script>
        <p id=foo>sometext&#169;&nbsp;&nbspp;
        <p id="bar">othertext</p></body></html>
        """
        safe = helpers.safeHTML(unsafe)
        tools.ok_('html' not in safe)
        tools.ok_('script' not in safe)
        tools.ok_('</p>' in safe)
        tools.ok_('&#169;' in safe)
        tools.ok_('&nbspp;' not in safe)
        tools.ok_('&nbspp' in safe)
        tools.ok_('id=foo' not in safe)
        tools.ok_('id="foo"' in safe)

    @patch('linkdrop.lib.helpers.log')
    @patch('linkdrop.lib.helpers.metrics')
    def test_json_exception_response(self, mock_metrics, mock_log):
        # first make sure HTTPException gets passed through
        from webob.exc import HTTPException
        http_exc = HTTPException('msg', 'wsgi_response')
        request = Mock()

        @helpers.json_exception_response
        def http_exception_raiser(self, request):
            raise http_exc
        tools.assert_raises(HTTPException, http_exception_raiser, None,
                            request)

        # then make sure other exceptions get converted to JSON
        @helpers.json_exception_response
        def other_exception_raiser(self, request):
            exc = Exception('EXCEPTION')
            raise exc
        res = other_exception_raiser(None, request)
        tools.ok_(res['result'] is None)
        tools.eq_(res['error']['name'], 'Exception')
        tools.eq_(res['error']['message'], 'EXCEPTION')
        track_args = mock_metrics.track.call_args
        tools.eq_(track_args[0][1], 'unhandled-exception')
        tools.eq_(track_args[1]['function'], 'other_exception_raiser')
        tools.eq_(track_args[1]['error'], 'Exception')

    def test_api_response(self):
        data = {'foo': 'bar', 'baz': 'bawlp'}

        @helpers.api_response
        def sample_data(self, request):
            return data
        request = Mock()
        response = request.response  # another Mock

        # json format
        request.params = dict()
        response.headers = dict()
        res = sample_data(None, request)
        tools.eq_(res, json.dumps(data))
        tools.eq_(response.headers['Content-Type'], 'application/json')

        # "test" format (i.e. pprinted output)
        request.params['format'] = 'test'
        response.headers = dict()
        res = sample_data(None, request)
        tools.eq_(res, pprint.pformat(data))
        tools.eq_(response.headers['Content-Type'], 'text/plain')

        # xml format / dict
        request.params['format'] = 'xml'
        response.headers = dict()
        res = sample_data(None, request)
        xml = ('<?xml version="1.0" encoding="UTF-8"?><response>'
               '<foo>bar</foo><baz>bawlp</baz></response>')
        tools.eq_(res, xml)
        tools.eq_(response.headers['Content-Type'], 'text/xml')

        # xml format / list
        data = ['foo', 'bar', 'baz', 'bawlp']

        @helpers.api_response
        def sample_data2(self, request):
            return data
        request.params['format'] = 'xml'
        response.headers = dict()
        res = sample_data(None, request)
        xml = ('<?xml version="1.0" encoding="UTF-8"?><response>foo</response>'
               '<response>bar</response><response>baz</response><response>'
               'bawlp</response>')
        tools.eq_(res, xml)
        tools.eq_(response.headers['Content-Type'], 'text/xml')

    def test_api_entry(self):
        @helpers.api_entry(
            doc="DOC",
            queryargs=[
                helpers.api_arg('qryarg1', 'string', True, None, None,
                                "QryArg1 Doc"),
                helpers.api_arg('qryarg2', 'boolean', False, True, None,
                                "QryArg2 Doc"),
                ],
            bodyargs=[
                helpers.api_arg('bodyarg1', 'string', True, None, None,
                                'BodyArg1 Doc'),
                helpers.api_arg('bodyarg2', 'boolean', False, True, None,
                                'BodyArg2 Doc'),
                ],
            response={'type': 'list', 'doc': 'callargs list'},
            name='NAME')
        def api_fn(arg1, arg2, kwarg1=None, kwarg2=None):
            return [(arg1, arg2), dict(kwarg1=kwarg1, kwarg2=kwarg2)]
        res = api_fn(1, 2, kwarg1='foo', kwarg2='bar')
        tools.eq_(res, [(1, 2), dict(kwarg1='foo', kwarg2='bar')])
        tools.ok_(api_fn.__doc__.startswith('NAME\n===='))
        tools.ok_("qryarg1              string     QryArg1 Doc (required)"
                  in api_fn.__doc__)
        tools.ok_("qryarg2              boolean    QryArg2 Doc (default=True)"
                  in api_fn.__doc__)
        tools.ok_("**Request Body**: A JSON object" in api_fn.__doc__)
        tools.ok_("bodyarg1             string     BodyArg1 Doc (required)"
                  in api_fn.__doc__)
        tools.ok_("**Response Body**: list       callargs list"
                  in api_fn.__doc__)

        @helpers.api_entry(
            doc="DOC",
            body={'type': 'list', 'doc': 'body list'},
            )
        def api_fn2():
            return
        tools.ok_("**Request Body**:  list       body list"
                  in api_fn2.__doc__)

########NEW FILE########
__FILENAME__ = test_metrics
from linkdrop.lib import metrics
from linkdrop.tests import TestController
from mock import Mock
from nose import tools


class TestMetricsConsumer(TestController):
    @tools.raises(NotImplementedError)
    def test_consume_raises_notimplemented(self):
        mc = metrics.MetricsConsumer()
        mc.consume('somedata')


class TestMetricsCollector(TestController):
    def setUp(self):
        self.consumer = Mock()
        self.collector = metrics.MetricsCollector(self.consumer)

    def test_get_distinct_attr(self):
        res = self.collector._get_distinct_attrs(None)
        tools.eq_(res, dict())
        distinct_ob = dict(foo='bar', baz='bawlp')
        res = self.collector._get_distinct_attrs(distinct_ob)
        tools.eq_(res, distinct_ob)
        tools.assert_raises(NotImplementedError,
                            self.collector._get_distinct_attrs,
                            list())

    def test_track_not_enabled(self):
        self.collector.enabled = False
        distinct_ob = dict(foo='bar', baz='bawlp')
        self.collector.track(distinct_ob, 'id')
        self.consumer.consume.assert_not_called()

    def test_track(self):
        distinct_ob = dict(foo='bar', baz='bawlp')
        self.collector.track(distinct_ob, 'id', hey='now')
        self.consumer.consume.assert_called_once()
        data = self.consumer.consume.call_args[0][0]
        tools.ok_(data.pop('when', False))
        distinct_ob.update(dict(id='id', hey='now'))
        tools.eq_(data, distinct_ob)

########NEW FILE########
__FILENAME__ = test_shortener
from cStringIO import StringIO
from linkdrop.lib import shortener
from mock import patch
from nose import tools
import json
import urlparse

config = {'bitly.userid': 'BITLY_USERID',
          'bitly.key': 'BITLY_KEY',
          }


@patch('linkdrop.lib.shortener.log')
@patch('linkdrop.lib.shortener.urllib')
def test_shorten_link_bad_response(mock_urllib, mock_log):
    longurl = 'http://example.com/long/long/really/no/i/mean/really/long/url'
    shortener_response = 'BAD RESPONSE'
    mock_urllib.urlopen.return_value = StringIO(shortener_response)
    res = shortener.shorten_link(config, longurl)
    tools.ok_(res is None)
    mock_urllib.urlopen.assert_called_once()
    urlopen_arg = mock_urllib.urlopen.call_args[0][0]
    tools.ok_('longUrl=%s' % longurl in urlopen_arg)
    mock_log.error.assert_called_once_with(
        "unexpected bitly response: %r", shortener_response)


@patch('linkdrop.lib.shortener.urllib')
def test_shorten_link(mock_urllib):
    longurl = 'http://example.com/long/long/really/no/i/mean/really/long/url'
    shorturl = 'http://sh.ort/url/%s/%s'

    def mock_shortener(url):
        query = urlparse.urlparse(url).query
        qdict = urlparse.parse_qs(query)
        bitly_userid = qdict.get('login')[0]
        bitly_key = qdict.get('apiKey')[0]
        result = shorturl % (bitly_userid, bitly_key)
        shortener_response = json.dumps({'data': {'url': result}})
        return StringIO(shortener_response)
    mock_urllib.urlopen.side_effect = mock_shortener
    res = shortener.shorten_link(config, longurl)
    tools.eq_(shorturl % (config['bitly.userid'], config['bitly.key']), res)
    mock_urllib.urlopen.assert_called_once()
    urlopen_arg = mock_urllib.urlopen.call_args[0][0]
    tools.ok_('longUrl=%s' % longurl in urlopen_arg)

########NEW FILE########
__FILENAME__ = test_headers
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is F1.
#
# The Initial Developer of the Original Code is Mozilla
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#


# Test that some request headers make it all the way to the service.
# Currently the only such header is "Accept-Language"

from linkdrop.tests import testable_services

from test_playback import (HttpReplayer, setupReplayers, teardownReplayers,
                           domain_to_test)

from nose import with_setup
from nose.tools import eq_

# A fake response object we return to the apis - we just pretend a 500
# error occured every time after checking the header we expect is there.
class FakeResponse(dict):
    def __init__(self):
        self['status'] = "500"

    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            raise AttributeError(attr)


class SimpleHttpReplayer(HttpReplayer):
    _expected_language = None
    def request(self, uri, method="GET", body=None, headers=None, **kw):
        # check the header is (or is not) sent to the service.
        for k, v in (headers or {}).iteritems():
            if k.lower()=="accept-language":
                eq_(v, self._expected_language)
                break
        else:
            assert self._expected_language is None
        # just return a 500 so things bail quickly.
        return FakeResponse(), ""


def doSetup():
    setupReplayers(SimpleHttpReplayer)


@with_setup(doSetup, teardownReplayers)
def check_with_headers(provider, req_type, exp_language, headers=None):
    SimpleHttpReplayer._expected_language = exp_language
    testclass = domain_to_test[provider]
    test = testclass()
    request = test.getDefaultRequest(req_type)
    response = test.getResponse(req_type, request, headers)

def test_all():
    for provider in testable_services:
        if provider in ["google.com", "googleapps.com"]:
            # these use SMTP which doesn't attempt to pass on the header.
            continue
        for req_type in ['send', 'contacts']:
            # test no header in f1 request means no header in service req.
            yield (check_with_headers, provider, req_type, None)
            # test "normal" case header makes it through.
            yield (check_with_headers, provider, req_type, 'something',
                   {'Accept-Language': 'something'})
            # test lower-case header names it through.
            yield (check_with_headers, provider, req_type, 'something-else',
                   {'accept-language': 'something-else'})

########NEW FILE########
__FILENAME__ = test_playback
import sys
import os
import glob
import httplib
import httplib2
import urllib
import json
import socket
import email
import difflib
from urlparse import parse_qsl
from pprint import pformat
from nose.tools import eq_
from nose import with_setup
from routes.util import URLGenerator

from linkdrop.tests import TestController


def assert_dicts_equal(got, expected):
    if got != expected:
        diff = "\n".join(difflib.unified_diff(pformat(expected).splitlines(),
                                              pformat(got).splitlines()))
        raise AssertionError("dictionaries are different\n%s" % (diff,))


def assert_dicts_with_oauth_equal(got, expected):
    # oauth params are a PITA for various reasons - the playback responses
    # generally don't include them - but even if they did they would not
    # match as the signature is based on the content which we have probably
    # redacted.  So we just nuke all OAuth tokens from 'expected'
    for k in expected.keys():
        if k.startswith("oauth_"):
            del expected[k]

    if got != expected:
        diff = "\n".join(difflib.unified_diff(pformat(expected).splitlines(),
                                              pformat(got).splitlines()))
        raise AssertionError("dictionaries are different\n%s" % (diff,))


def assert_messages_equal(got, expected):
    gotpl = got.get_payload(decode=True)
    expectedpl = expected.get_payload(decode=True)
    if isinstance(gotpl, list):
        assert isinstance(expectedpl, list)
        eq_(len(gotpl), len(expectedpl))
        for got_elt, expected_elt in zip(gotpl, expectedpl):
            assert_messages_equal(got_elt, expected_elt)
    else:
        eq_(got.get_content_type(), expected.get_content_type())
        if got.get_content_type() == "application/x-www-form-urlencoded":
            got_items = dict(parse_qsl(gotpl))
            expected_items = dict(parse_qsl(expectedpl))
            assert_dicts_with_oauth_equal(got_items, expected_items)
        elif got.get_content_type() == "application/json":
            got_items = json.loads(gotpl)
            expected_items = json.loads(expectedpl)
            assert_dicts_equal(got_items, expected_items)
        elif gotpl is None:
            assert expectedpl is None
        else:
            # rstrip the payloads as some of our corpus items have trailing
            # newlines to stop git/hg/etc complaining...
            eq_(gotpl.rstrip(), expectedpl.rstrip())


# Somewhat analogous to a protocap.ProtocolCapturingBase object - but
# instead of capturing, it replays an earlier capture.
# In general, the request we make to the service is ignored - we just
# replay back the pre-canned responses.
class ProtocolReplayer(object):
    def __init__(self, *args, **kw):
        pass

    def save_capture(self, reason=""):
        pass


class HttpReplayer(ProtocolReplayer):
    to_playback = []

    def request(self, uri, method="GET", body=None, headers=None, **kw):
        freq, fresp = self.to_playback.pop(0)
        if freq is not None:
            # We have an 'expected request' file - check it is what
            # is actually being requested.
            reqmethod, reqpath = freq.readline().strip().split(" ", 1)
            eq_(method, reqmethod)
            proto, rest = urllib.splittype(uri)
            host, path = urllib.splithost(rest)
            eq_(path, reqpath)
            reqob = email.message_from_string(freq.read().rstrip())
            headers = headers or {}
            if method == "POST":
                for n in headers.keys():
                    if n.lower() == "content-type":
                        break
                else:
                    headers['Content-Type'] = ("application/"
                                               "x-www-form-urlencoded")
            # We may wind up with the oauth stuff creating an 'Authorization'
            # header as unicode.  Force all headers back to a string and if
            # any blow up as being non-ascii, we have a deeper problem...
            gotheadersstr = "\r\n".join(
                    ["%s: %s" % (n, v.encode("ascii"))
                     for n, v in headers.iteritems()])
            bodystr = gotheadersstr + "\r\n\r\n" + (body or '')
            gotob = email.message_from_string(bodystr)
            if headers:
                if 'content-type' in gotob:
                    eq_(gotob.get_content_type(), reqob.get_content_type())
                else:
                    assert 'content-type' not in reqob
                # only check the headers specified - additional headers
                # may have been added by httplib but we can ignore them.
                for hname, hval in headers.iteritems():
                    if hname.lower() in ["content-length", "content-type",
                                         "authorization"]:
                        continue
                    # otherwise the header must match exactly.
                    eq_(hval, reqob[hname])
            # finally check the content (ie, the body) is as expected.
            assert_messages_equal(gotob, reqob)

        resp = httplib.HTTPResponse(socket.socket())
        resp.fp = fresp
        resp.begin()
        content = resp.read()
        return httplib2.Response(resp), content


from linkoauth.backends.google_ import SMTP


class SmtpReplayer(SMTP, ProtocolReplayer):
    to_playback = None

    def __init__(self, *args, **kw):
        self.next_playback = self.to_playback.readline()
        SMTP.__init__(self, *args, **kw)
        self.sock = socket.socket()

    def save_captures(self, reason=""):
        pass

    def set_debuglevel(self, debuglevel):
        pass  # don't want the print statements during testing.

    def connect(self, host='localhost', port=0):
        return self.getreply()

    def _get_next_comms(self):
        result = []
        line = self.next_playback
        if line.startswith("E "):
            # a recorded exception - reconstitute it...
            exc_info = json.loads(line[2:])
            module = (sys.modules[exc_info['module']]
                      if exc_info['module'] else __builtins__)
            exc_class = getattr(module, exc_info['name'])
            raise exc_class(*tuple(exc_info['args']))
        if not line.startswith("< ") and not line.startswith("> "):
            # hrm - this implies something is wrong maybe?
            raise RuntimeError("strange: %r" % (line,))
        direction = line[0]
        result.append(line[2:].strip())
        while True:
            line = self.next_playback = self.to_playback.readline()
            if not line.startswith("+ "):
                break
            # a continuation...
            result.append(line[2:].strip())
        return direction, "\n".join(result)

    def getreply(self):
        direction, data = self._get_next_comms()
        if direction != "<":
            # hrm - this implies something is wrong maybe?
            raise RuntimeError("playback is out of sync")
        code = int(data[:3])
        errmsg = data[3:]
        return code, errmsg

    def send(self, str):
        direction, data = self._get_next_comms()
        if direction != ">":
            # hrm - this implies something is wrong maybe?
            raise RuntimeError("playback is out of sync")
        # we just throw the data away!

    def quit(self):
        SmtpReplayer.to_playback.close()
        SmtpReplayer.to_playback = None


class CannedRequest(object):
    def __init__(self, path):
        meta_filename = os.path.join(path, "meta.json")
        self.path = path
        (self.protocol, self.host,
         self.req_type, self.comments) = os.path.basename(path).split("-", 3)
        with open(meta_filename) as f:
            self.meta = json.load(f)

    def __repr__(self):
        return "<canned request at '%s'>" % (self.path,)


def genCanned(glob_pattern="*"):
    import linkdrop.tests.services
    corpus_dir = os.path.join(linkdrop.tests.services.__path__[0], 'corpus')
    num = 0
    for dirname in glob.glob(os.path.join(corpus_dir, glob_pattern)):
        meta_fname = os.path.join(dirname, "meta.json")
        if os.path.isfile(meta_fname):
            yield CannedRequest(dirname)
            num += 1
    if not num:
        raise AssertionError("No tests match %r" % (glob_pattern,))


class ServiceReplayTestCase(TestController):
    def checkResponse(self, canned, response):
        # First look for an optional 'expected-f1-response.json' which
        # allows custom status and headers to be specified.
        try:
            with open(os.path.join(canned.path,
                                   "expected-f1-response.json")) as f:
                expected = json.load(f)
        except IOError:
            # No expected-f1-response - assume this means a 200 is
            # expected and expected-f1-data.json has what we want.
            pass
        else:
            assert response.status_int == expected['status'], (
                response.status_int, expected['status'])
            for exp_header_name, exp_header_val in expected.get(
                'headers', {}).iteritems():
                got = response.headers.get(exp_header_name, None)
                assert got == exp_header_val, (got, exp_header_val)
            return

        # No expected-f1-response.json - do the expected-f1-data thang...
        assert response.status_int == 200, response.status
        try:
            got = json.loads(response.body)
        except ValueError:
            raise AssertionError("non-json response: %r" % (response.body,))
        try:
            with open(os.path.join(canned.path, "expected-f1-data.json")) as f:
                expected = json.load(f)
        except IOError:
            print "*** No 'expected-f1-data.json' in '%s'" % (canned.path,)
            print "The F1 response was:"
            print json.dumps(got, sort_keys=True, indent=4)
            raise AssertionError("expected-f1-data.json is missing")
        # do a little massaging of the data to avoid too much noise.
        for top in ["error", "result"]:
            sub = expected.get(top)
            if sub is None:
                continue
            for subname, subval in sub.items():
                if subval == "*":
                    # indicates any value is acceptable.
                    assert subname in got[top], ("no attribute [%r][%r]"
                                                 % (top, subname))
                    del got[top][subname]
                    del expected[top][subname]
        assert_dicts_equal(got, expected)

    def getResponse(self, req_type, request, headers=None):
        url = URLGenerator(self.app.mapper, dict(HTTP_HOST='localhost'))
        if req_type == "send":
            response = self.test_app.post(url(controller='send',
                                              action='send'),
                                          params=request, headers=headers)
        elif req_type == "contacts":
            # send the 'contacts' request.
            domain = request.pop('domain')
            response = self.test_app.post(url(controller='contacts',
                                              action='get', domain=domain),
                                          params=request, headers=headers)
        elif req_type == "auth":
            # this is a little gross - we need to hit "authorize"
            # direct, then assume we got redirected to the service,
            # which then redirected us back to 'verify'
            request['end_point_auth_failure'] = "/failure"
            request['end_point_auth_success'] = "/success"
            response = self.test_app.post(url(controller='account',
                                              action='authorize'),
                                          params=request, headers=headers)
            assert response.status_int == 302
            # and even more hacky...
            request['provider'] = request.pop('domain')
            request['code'] = "the_code"
            response = self.test_app.get(url(controller='account',
                                             action='verify'),
                                         params=request, headers=headers)
        else:
            raise AssertionError(req_type)
        return response


class FacebookReplayTestCase(ServiceReplayTestCase):
    def getDefaultRequest(self, req_type):
        if req_type == "send" or req_type == "contacts":
            return {'domain': 'facebook.com',
                    'shareType': 'wall',
                    'account': ('{"oauth_token": "foo", '
                                '"oauth_token_secret": "bar"}'),
                   }
        if req_type == "auth":
            return {'domain': 'facebook.com', 'username': 'foo',
                    'userid': 'bar'}
        raise AssertionError(req_type)


class TwitterReplayTestCase(ServiceReplayTestCase):
    def getDefaultRequest(self, req_type):
        if req_type == "send" or req_type == "contacts":
            account = {"oauth_token": "foo", "oauth_token_secret": "bar",
                       "username": "mytwitterid"}
            return {'domain': 'twitter.com',
                    'shareType': 'public',
                    'account': json.dumps(account),
                   }
        if req_type == "auth":
            return {'domain': 'twitter.com', 'username': 'foo',
                    'userid': 'bar'}
        raise AssertionError(req_type)


class YahooReplayTestCase(ServiceReplayTestCase):
    def getDefaultRequest(self, req_type):
        if req_type == "send" or req_type == "contacts":
            account = {"oauth_token": "foo", "oauth_token_secret": "bar",
                       "profile": {
                       "verifiedEmail": "me@yahoo.com",
                       "displayName": "me",
                       }
                      }
            return {'domain': 'yahoo.com',
                    'to': 'you@example.com',
                    'account': json.dumps(account),
                   }
        if req_type == "auth":
            return {'domain': 'yahoo.com', 'username': 'foo', 'userid': 'bar'}
        raise AssertionError(req_type)


class GoogleReplayTestCase(ServiceReplayTestCase):
    def getDefaultRequest(self, req_type):
        if req_type == "send":
            account = {"oauth_token": "foo", "oauth_token_secret": "bar",
                       "profile": {"emails": [{'value': 'me@example.com'}],
                                   "displayName": "Me",
                        },
                      }
            return {'domain': 'google.com',
                    'account': json.dumps(account),
                    'to': 'you@example.com',
                    }
        if req_type == "contacts":
            account = {"oauth_token": "foo", "oauth_token_secret": "bar",
                       "profile": {"emails": [{'value': 'me@example.com'}],
                                "displayName": "Me",
                        },
                      }
            return {'username': 'me',
                    'userid': '123',
                    'keys': "1,2,3",
                    'account': json.dumps(account),
                    'domain': 'google.com',
                   }
        raise AssertionError(req_type)


class LinkedinReplayTestCase(ServiceReplayTestCase):
    def getDefaultRequest(self, req_type):
        if req_type == "send":
            account = {"oauth_token": "foo", "oauth_token_secret": "bar",
                       "profile": {"emails": [{'value': 'me@example.com'}],
                                   "displayName": "Me",
                        },
                      }
            return {'domain': 'linkedin.com',
                    'account': json.dumps(account),
                    'to': 'you@example.com',
                    }
        if req_type == "contacts":
            account = {"oauth_token": "foo", "oauth_token_secret": "bar",
                       "profile": {"emails": [{'value': 'me@example.com'}],
                                "displayName": "Me",
                        },
                      }
            return {'username': 'me',
                    'userid': '123',
                    'keys': "1,2,3",
                    'account': json.dumps(account),
                    'domain': 'linkedin.com',
                    'maxresults': 500,
                   }
        if req_type == "auth":
            return {'domain': 'linkedin.com', 'username': 'foo',
                    'userid': 'bar'}
        raise AssertionError(req_type)


def setupReplayers(httpReplayer=HttpReplayer, smtpReplayer=SmtpReplayer):
    from linkoauth.backends import facebook_
    facebook_.HttpRequestor = httpReplayer
    from linkoauth.backends import yahoo_
    yahoo_.HttpRequestor = httpReplayer
    from linkoauth.backends import google_
    google_.SMTPRequestor = smtpReplayer
    google_.OAuth2Requestor = httpReplayer
    from linkoauth.backends import twitter_
    twitter_.OAuth2Requestor = httpReplayer
    from linkoauth.backends import linkedin_
    linkedin_.OAuth2Requestor = httpReplayer
    import linkoauth.oauth
    linkoauth.oauth.HttpRequestor = httpReplayer
    HttpReplayer.to_playback = []
    SmtpReplayer.to_playback = None


def teardownReplayers():
    assert not HttpReplayer.to_playback, HttpReplayer.to_playback
    assert not SmtpReplayer.to_playback, SmtpReplayer.to_playback
    import linkoauth.protocap
    from linkoauth.backends import facebook_
    facebook_.HttpRequestor = linkoauth.protocap.HttpRequestor
    from linkoauth.backends import yahoo_
    yahoo_.HttpRequestor = linkoauth.protocap.HttpRequestor
    from linkoauth.backends import google_
    google_.SMTPRequestor = google_.SMTPRequestorImpl
    google_.OAuth2Requestor = linkoauth.protocap.OAuth2Requestor
    from linkoauth.backends import twitter_
    twitter_.OAuth2Requestor = linkoauth.protocap.OAuth2Requestor
    from  linkoauth.backends import linkedin_
    linkedin_.OAuth2Requestor = linkoauth.protocap.OAuth2Requestor
    from linkoauth import oauth
    oauth.HttpRequestor = linkoauth.protocap.HttpRequestor


host_to_domain = {
    'graph.facebook.com': 'facebook.com',
    'www.google.com': 'google.com',
    'smtp.gmail.com': 'google.com',
    'mail.yahooapis.com': 'yahoo.com',
    'social.yahooapis.com': 'yahoo.com',
    'api.twitter.com': 'twitter.com',
    'twitter.com': 'twitter.com',
    'api.linkedin.com': 'linkedin.com',
}


domain_to_test = {
    'facebook.com': FacebookReplayTestCase,
    'google.com': GoogleReplayTestCase,
    'googleapps.com': GoogleReplayTestCase,
    'yahoo.com': YahooReplayTestCase,
    'twitter.com': TwitterReplayTestCase,
    'linkedin.com': LinkedinReplayTestCase,
}


def queueForReplay(canned):
    if canned.protocol == "smtp":
        fname = os.path.join(canned.path, "smtp-trace")
        SmtpReplayer.to_playback = open(fname)
    elif canned.protocol == "http":
        # http playbacks can have multiple responses due to redirections...
        i = 0
        while True:
            fname = os.path.join(canned.path, "request-%d" % (i,))
            try:
                freq = open(fname)
            except IOError:
                freq = None
            fname = os.path.join(canned.path, "response-%d" % (i,))
            try:
                fresp = open(fname)
            except IOError:
                fresp = None
            if freq is None and fresp is None:
                break
            HttpReplayer.to_playback.append((freq, fresp))
            i += 1
    else:
        raise AssertionError(canned.protocol)


def runOne(canned):
    provider = host_to_domain[canned.host]
    testClass = domain_to_test[provider]
    test = testClass()
    queueForReplay(canned)
    try:
        with open(os.path.join(canned.path, "f1-request.json")) as f:
            request = json.load(f)
        # and the handling of 'account' totally sucks - it is a string...
        request['account'] = json.dumps(request['account'])
    except IOError:
        request = test.getDefaultRequest(canned.req_type)
    response = test.getResponse(canned.req_type, request)
    test.checkResponse(canned, response)

# *sob* - this used to use a nose "test generator", but that technique
# doesn't work well with discovery and only running one of the tests in
# the corpus.
# So we hack up the global namespace.  This allows you to say, eg,
# % nosetests ... linkdrop/tests/services/test_playback.py:test_service_replay_http_www_google_com_auth_successful
# to just run one specific test from the corpus.
for canned in genCanned():

    @with_setup(setupReplayers, teardownReplayers)
    def decoratedRunOne(canned=canned):
        runOne(canned)
    tail = os.path.basename(canned.path).replace("-", "_").replace(".", "_")
    name = "test_service_replay_" + tail
    decoratedRunOne.__name__ = name
    globals()[name] = decoratedRunOne

########NEW FILE########
__FILENAME__ = wsgiapp
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Raindrop.
#
# The Initial Developer of the Original Code is
# Mozilla Messaging, Inc..
# Portions created by the Initial Developer are Copyright (C) 2009
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Rob Miller (rmiller@mozilla.com)
#
# ***** END LICENSE BLOCK *****
"""
Application entry point.
"""
from linkdrop.controllers.account import AccountController
from linkdrop.controllers.contacts import ContactsController
from linkdrop.controllers.docs import DocsController
from linkdrop.controllers.send import SendController
from linkoauth.util import setup_config
from routes.util import URLGenerator
from services.baseapp import set_app, SyncServerApp
from webob.dec import wsgify

urls = [
    ('GET', '/docs', 'docs', 'index'),
    ('POST', '/send', 'send', 'send'),
    ('POST', '/account/authorize', 'account', 'authorize'),
    (('GET', 'POST'), '/account/verify', 'account', 'verify'),
    ('POST', '/contacts/{domain}', 'contacts', 'get'),
    ]

controllers = {'account': AccountController,
               'contacts': ContactsController,
               'docs': DocsController,
               'send': SendController,
               }


class ShareServerApp(SyncServerApp):
    """Share server WSGI application"""
    def __init__(self, urls, controllers, config, auth_class=None,
                 *args, **kwargs):
        if auth_class is not None:
            raise ValueError("A ShareServerApp's ``auth_class`` must be None.")
        setup_config(config)
        super(ShareServerApp, self).__init__(urls, controllers, config,
                                             auth_class, *args, **kwargs)

    @wsgify
    def __call__(self, request, *args, **kwargs):
        """Construct an URLGenerator"""
        request.urlgen = URLGenerator(self.mapper, request.environ)
        superclass = super(ShareServerApp, self)
        return superclass.__call__.undecorated(request, *args, **kwargs)


make_app = set_app(urls, controllers, klass=ShareServerApp, auth_class=None)

########NEW FILE########
__FILENAME__ = line_profiler
#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import cPickle
from cStringIO import StringIO
import inspect
import linecache
import optparse
import os
import sys
from decorator import decorator

from _line_profiler import LineProfiler as CLineProfiler


CO_GENERATOR = 0x0020
def is_generator(f):
    """ Return True if a function is a generator.
    """
    isgen = (f.func_code.co_flags & CO_GENERATOR) != 0 
    return isgen

# Code to exec inside of LineProfiler.__call__ to support PEP-342-style
# generators in Python 2.5+.
pep342_gen_wrapper = '''
def wrap_generator(self, func):
    """ Wrap a generator to profile it.
    """
    def f(*args, **kwds):
        g = func(*args, **kwds)
        # The first iterate will not be a .send()
        self.enable_by_count()
        try:
            item = g.next()
        finally:
            self.disable_by_count()
        input = (yield item)
        # But any following one might be.
        while True:
            self.enable_by_count()
            try:
                item = g.send(input)
            finally:
                self.disable_by_count()
            input = (yield item)
    return f
'''

class LineProfiler(CLineProfiler):
    """ A profiler that records the execution times of individual lines.
    """

    def __call__(self, func):
        """ Decorate a function to start the profiler on function entry and stop
        it on function exit.
        """
        self.add_function(func)
        if is_generator(func):
            f = self.wrap_generator(func)
        else:
            f = self.wrap_function(func)
        f.__module__ = func.__module__
        f.__name__ = func.__name__
        f.__doc__ = func.__doc__
        f.__dict__.update(getattr(func, '__dict__', {}))
        return f

    if sys.version_info[:2] >= (2,5):
        # Delay compilation because the syntax is not compatible with older
        # Python versions.
        exec pep342_gen_wrapper
    else:
        def wrap_generator(self, func):
            """ Wrap a generator to profile it.
            """
            def f(*args, **kwds):
                g = func(*args, **kwds)
                while True:
                    self.enable_by_count()
                    try:
                        item = g.next()
                    finally:
                        self.disable_by_count()
                    yield item
            return f

    def wrap_function(self, func):
        """ Wrap a function to profile it.
        """
        def f(_f, *args, **kwds):
            self.enable_by_count()
            try:
                import sys; print >> sys.stderr, args, kwds
                result = _f(*args, **kwds)
            finally:
                self.disable_by_count()
            return result
        # use decorator to keep the same arg signature on the function
        return decorator(f, func)

    def dump_stats(self, filename):
        """ Dump a representation of the data to a file as a pickled LineStats
        object from `get_stats()`.
        """
        lstats = self.get_stats()
        f = open(filename, 'wb')
        try:
            cPickle.dump(lstats, f, cPickle.HIGHEST_PROTOCOL)
        finally:
            f.close()

    def print_stats(self, stream=None):
        """ Show the gathered statistics.
        """
        lstats = self.get_stats()
        show_text(lstats.timings, lstats.unit, stream=stream)

    def run(self, cmd):
        """ Profile a single executable statment in the main namespace.
        """
        import __main__
        dict = __main__.__dict__
        return self.runctx(cmd, dict, dict)

    def runctx(self, cmd, globals, locals):
        """ Profile a single executable statement in the given namespaces.
        """
        self.enable_by_count()
        try:
            exec cmd in globals, locals
        finally:
            self.disable_by_count()
        return self

    def runcall(self, func, *args, **kw):
        """ Profile a single function call.
        """
        self.enable_by_count()
        try:
            return func(*args, **kw)
        finally:
            self.disable_by_count()


def show_func(filename, start_lineno, func_name, timings, unit, stream=None):
    """ Show results for a single function.
    """
    if not timings:
        return
    if stream is None:
        stream = sys.stdout
    print >>stream, "File: %s" % filename
    print >>stream, "Function: %s at line %s" % (func_name, start_lineno)
    template = '%6s %9s %12s %8s %8s  %-s'
    d = {}
    total_time = 0.0
    linenos = []
    for lineno, nhits, time in timings:
        total_time += time
        linenos.append(lineno)
    print >>stream, "Total time: %g s" % (total_time * unit)
    if not os.path.exists(filename):
        print >>stream, ""
        print >>stream, "Could not find file %s" % filename
        print >>stream, "Are you sure you are running this program from the same directory"
        print >>stream, "that you ran the profiler from?"
        print >>stream, "Continuing without the function's contents."
        # Fake empty lines so we can see the timings, if not the code.
        nlines = max(linenos) - min(min(linenos), start_lineno) + 1
        sublines = [''] * nlines
    else:
        all_lines = linecache.getlines(filename)
        sublines = inspect.getblock(all_lines[start_lineno-1:])
    for lineno, nhits, time in timings:
        d[lineno] = (nhits, time, '%5.1f' % (float(time) / nhits),
            '%5.1f' % (100*time / total_time))
    linenos = range(start_lineno, start_lineno + len(sublines))
    empty = ('', '', '', '')
    header = template % ('Line #', 'Hits', 'Time', 'Per Hit', '% Time', 
        'Line Contents')
    print >>stream, ""
    print >>stream, header
    print >>stream, '=' * len(header)
    for lineno, line in zip(linenos, sublines):
        nhits, time, per_hit, percent = d.get(lineno, empty)
        print >>stream, template % (lineno, nhits, time, per_hit, percent,
            line.rstrip('\n').rstrip('\r'))
    print >>stream, ""

def show_text(stats, unit, stream=None):
    """ Show text for the given timings.
    """
    if stream is None:
        stream = sys.stdout
    print >>stream, 'Timer unit: %g s' % unit
    print >>stream, ''
    for (fn, lineno, name), timings in sorted(stats.items()):
        show_func(fn, lineno, name, stats[fn, lineno, name], unit, stream=stream)

# A %lprun magic for IPython.
def magic_lprun(self, parameter_s=''):
    """ Execute a statement under the line-by-line profiler from the
    line_profiler module.

    Usage:
      %lprun -f func1 -f func2 <statement>

    The given statement (which doesn't require quote marks) is run via the
    LineProfiler. Profiling is enabled for the functions specified by the -f
    options. The statistics will be shown side-by-side with the code through the
    pager once the statement has completed.

    Options:
    
    -f <function>: LineProfiler only profiles functions and methods it is told
    to profile.  This option tells the profiler about these functions. Multiple
    -f options may be used. The argument may be any expression that gives
    a Python function or method object. However, one must be careful to avoid
    spaces that may confuse the option parser. Additionally, functions defined
    in the interpreter at the In[] prompt or via %run currently cannot be
    displayed.  Write these functions out to a separate file and import them.

    One or more -f options are required to get any useful results.

    -D <filename>: dump the raw statistics out to a pickle file on disk. The
    usual extension for this is ".lprof". These statistics may be viewed later
    by running line_profiler.py as a script.

    -T <filename>: dump the text-formatted statistics with the code side-by-side
    out to a text file.

    -r: return the LineProfiler object after it has completed profiling.
    """
    # Local import to avoid hard dependency.
    from IPython.genutils import page
    from IPython.ipstruct import Struct
    from IPython.ipapi import UsageError

    # Escape quote markers.
    opts_def = Struct(D=[''], T=[''], f=[])
    parameter_s = parameter_s.replace('"',r'\"').replace("'",r"\'")
    opts, arg_str = self.parse_options(parameter_s, 'rf:D:T:', list_all=True)
    opts.merge(opts_def)

    global_ns = self.shell.user_global_ns
    local_ns = self.shell.user_ns

    # Get the requested functions.
    funcs = []
    for name in opts.f:
        try:
            funcs.append(eval(name, global_ns, local_ns))
        except Exception, e:
            raise UsageError('Could not find function %r.\n%s: %s' % (name, 
                e.__class__.__name__, e))

    profile = LineProfiler(*funcs)

    # Add the profiler to the builtins for @profile.
    import __builtin__
    if 'profile' in __builtin__.__dict__:
        had_profile = True
        old_profile = __builtin__.__dict__['profile']
    else:
        had_profile = False
        old_profile = None
    __builtin__.__dict__['profile'] = profile

    try:
        try:
            profile.runctx(arg_str, global_ns, local_ns)
            message = ''
        except SystemExit:
            message = """*** SystemExit exception caught in code being profiled."""
        except KeyboardInterrupt:
            message = ("*** KeyboardInterrupt exception caught in code being "
                "profiled.")
    finally:
        if had_profile:
            __builtin__.__dict__['profile'] = old_profile

    # Trap text output.
    stdout_trap = StringIO()
    profile.print_stats(stdout_trap)
    output = stdout_trap.getvalue()
    output = output.rstrip()

    page(output, screen_lines=self.shell.rc.screen_length)
    print message,

    dump_file = opts.D[0]
    if dump_file:
        profile.dump_stats(dump_file)
        print '\n*** Profile stats pickled to file',\
              `dump_file`+'.',message

    text_file = opts.T[0]
    if text_file:
        pfile = open(text_file, 'w')
        pfile.write(output)
        pfile.close()
        print '\n*** Profile printout saved to text file',\
              `text_file`+'.',message

    return_value = None
    if opts.has_key('r'):
        return_value = profile

    return return_value

def load_stats(filename):
    """ Utility function to load a pickled LineStats object from a given
    filename.
    """
    f = open(filename, 'rb')
    try:
        lstats = cPickle.load(f)
    finally:
        f.close()
    return lstats


def main():
    usage = "usage: %prog profile.lprof"
    parser = optparse.OptionParser(usage=usage, version='%prog 1.0b2')

    options, args = parser.parse_args()
    if len(args) != 1:
        parser.error("Must provide a filename.")
    lstats = load_stats(args[0])
    show_text(lstats.timings, lstats.unit)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = lsprofcalltree
# lsprofcalltree.py: lsprof output which is readable by kcachegrind
# David Allouche
# Jp Calderone & Itamar Shtull-Trauring
# Johan Dahlin

import optparse
import os
import sys

try:
    import cProfile
except ImportError:
    raise SystemExit("This script requires cProfile from Python 2.5")

def label(code):
    if isinstance(code, str):
        return ('~', 0, code)    # built-in functions ('~' sorts at the end)
    else:
        return '%s %s:%d' % (code.co_name,
                             code.co_filename,
                             code.co_firstlineno)

class KCacheGrind(object):
    def __init__(self, profiler):
        self.data = profiler.getstats()
        self.out_file = None

    def output(self, out_file):
        self.out_file = out_file
        print >> out_file, 'events: Ticks'
        self._print_summary()
        for entry in self.data:
            self._entry(entry)

    def _print_summary(self):
        max_cost = 0
        for entry in self.data:
            totaltime = int(entry.totaltime * 1000)
            max_cost = max(max_cost, totaltime)
        print >> self.out_file, 'summary: %d' % (max_cost,)

    def _entry(self, entry):
        out_file = self.out_file

        code = entry.code
        #print >> out_file, 'ob=%s' % (code.co_filename,)
        if isinstance(code, str):
            print >> out_file, 'fi=~'
        else:
            print >> out_file, 'fi=%s' % (code.co_filename,)
        print >> out_file, 'fn=%s' % (label(code),)

        inlinetime = int(entry.inlinetime * 1000)
        if isinstance(code, str):
            print >> out_file, '0 ', inlinetime
        else:
            print >> out_file, '%d %d' % (code.co_firstlineno, inlinetime)

        # recursive calls are counted in entry.calls
        if entry.calls:
            calls = entry.calls
        else:
            calls = []

        if isinstance(code, str):
            lineno = 0
        else:
            lineno = code.co_firstlineno

        for subentry in calls:
            self._subentry(lineno, subentry)
        print >> out_file

    def _subentry(self, lineno, subentry):
        out_file = self.out_file
        code = subentry.code
        #print >> out_file, 'cob=%s' % (code.co_filename,)
        print >> out_file, 'cfn=%s' % (label(code),)
        if isinstance(code, str):
            print >> out_file, 'cfi=~'
            print >> out_file, 'calls=%d 0' % (subentry.callcount,)
        else:
            print >> out_file, 'cfi=%s' % (code.co_filename,)
            print >> out_file, 'calls=%d %d' % (
                subentry.callcount, code.co_firstlineno)

        totaltime = int(subentry.totaltime * 1000)
        print >> out_file, '%d %d' % (lineno, totaltime)

def main(args):
    usage = "%s [-o output_file_path] scriptfile [arg] ..."
    parser = optparse.OptionParser(usage=usage % sys.argv[0])
    parser.allow_interspersed_args = False
    parser.add_option('-o', '--outfile', dest="outfile",
                      help="Save stats to <outfile>", default=None)

    if not sys.argv[1:]:
        parser.print_usage()
        sys.exit(2)

    options, args = parser.parse_args()

    if not options.outfile:
        options.outfile = '%s.log' % os.path.basename(args[0])

    sys.argv[:] = args

    prof = cProfile.Profile()
    try:
        try:
            prof = prof.run('execfile(%r)' % (sys.argv[0],))
        except SystemExit:
            pass
    finally:
        kg = KCacheGrind(prof)
        kg.output(file(options.outfile, 'w'))

if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
