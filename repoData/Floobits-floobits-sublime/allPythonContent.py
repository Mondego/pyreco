__FILENAME__ = api
import sys
import base64
import json
import subprocess
import traceback
from functools import wraps

try:
    import ssl
except ImportError:
    ssl = False


try:
    import __builtin__
    str_instances = (str, __builtin__.basestring)
except Exception:
    str_instances = (str, )

try:
    import urllib
    from urllib.request import Request, urlopen
    HTTPError = urllib.error.HTTPError
    URLError = urllib.error.URLError
except (AttributeError, ImportError, ValueError):
    import urllib2
    from urllib2 import Request, urlopen
    HTTPError = urllib2.HTTPError
    URLError = urllib2.URLError

try:
    from .. import editor
    from . import msg, shared as G, utils
    from .exc_fmt import str_e
except ImportError:
    import editor
    import msg
    import shared as G
    import utils
    from exc_fmt import str_e


def get_basic_auth(host):
    username = G.AUTH.get(host, {}).get('username')
    secret = G.AUTH.get(host, {}).get('secret')
    if username is None or secret is None:
        return
    basic_auth = ('%s:%s' % (username, secret)).encode('utf-8')
    basic_auth = base64.encodestring(basic_auth)
    return basic_auth.decode('ascii').replace('\n', '')


class APIResponse():
    def __init__(self, r):
        if isinstance(r, bytes):
            r = r.decode('utf-8')
        if isinstance(r, str_instances):
            lines = r.split('\n')
            self.code = int(lines[0])
            self.body = json.loads('\n'.join(lines[1:]))
        else:
            self.code = r.code
            self.body = json.loads(r.read().decode("utf-8"))


def proxy_api_request(host, url, data, method):
    args = ['python', '-m', 'floo.proxy',  '--host', host, '--url', url]
    if data:
        args += ["--data", json.dumps(data)]
    if method:
        args += ["--method", method]
    msg.log('Running %s (%s)' % (' '.join(args), G.PLUGIN_PATH))
    proc = subprocess.Popen(args, cwd=G.PLUGIN_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (stdout, stderr) = proc.communicate()
    if stderr:
        raise IOError(stderr)

    if proc.poll() != 0:
        raise IOError(stdout)
    r = APIResponse(stdout)
    return r


def user_agent():
    return 'Floobits Plugin %s %s %s py-%s.%s' % (
        editor.name(),
        G.__PLUGIN_VERSION__,
        editor.platform(),
        sys.version_info[0],
        sys.version_info[1]
    )


def hit_url(host, url, data, method):
    if data:
        data = json.dumps(data).encode('utf-8')
    r = Request(url, data=data)
    r.method = method
    r.get_method = lambda: method
    auth = get_basic_auth(host)
    if auth:
        r.add_header('Authorization', 'Basic %s' % auth)
    r.add_header('Accept', 'application/json')
    r.add_header('Content-type', 'application/json')
    r.add_header('User-Agent', user_agent())
    return urlopen(r, timeout=5)


def api_request(host, url, data=None, method=None):
    if data:
        method = method or 'POST'
    else:
        method = method or 'GET'
    if ssl is False:
        return proxy_api_request(host, url, data, method)
    try:
        r = hit_url(host, url, data, method)
    except HTTPError as e:
        r = e
    return APIResponse(r)


def create_workspace(host, post_data):
    api_url = 'https://%s/api/workspace' % host
    return api_request(host, api_url, post_data)


def update_workspace(workspace_url, data):
    result = utils.parse_url(workspace_url)
    api_url = 'https://%s/api/workspace/%s/%s' % (result['host'], result['owner'], result['workspace'])
    return api_request(result['host'], api_url, data, method='PUT')


def get_workspace_by_url(url):
    result = utils.parse_url(url)
    api_url = 'https://%s/api/workspace/%s/%s' % (result['host'], result['owner'], result['workspace'])
    return api_request(result['host'], api_url)


def get_workspace(host, owner, workspace):
    api_url = 'https://%s/api/workspace/%s/%s' % (host, owner, workspace)
    return api_request(host, api_url)


def get_workspaces(host):
    api_url = 'https://%s/api/workspace/can/view' % (host)
    return api_request(host, api_url)


def get_orgs(host):
    api_url = 'https://%s/api/orgs' % (host)
    return api_request(host, api_url)


def get_orgs_can_admin(host):
    api_url = 'https://%s/api/orgs/can/admin' % (host)
    return api_request(host, api_url)


def send_error(description=None, exception=None):
    G.ERROR_COUNT += 1
    if G.ERRORS_SENT >= G.MAX_ERROR_REPORTS:
        msg.warn('Already sent %s errors this session. Not sending any more.' % G.ERRORS_SENT)
        return
    data = {
        'jsondump': {
            'error_count': G.ERROR_COUNT
        },
        'message': {},
        'dir': G.COLAB_DIR,
    }
    if G.AGENT:
        data['owner'] = G.AGENT.owner
        data['username'] = G.AGENT.username
        data['workspace'] = G.AGENT.workspace
    if exception:
        data['message'] = {
            'description': str(exception),
            'stack': traceback.format_exc(exception)
        }
    msg.log('Floobits plugin error! Sending exception report: %s' % data['message'])
    if description:
        data['message']['description'] = description
    try:
        # TODO: use G.AGENT.proto.host?
        api_url = 'https://%s/api/log' % (G.DEFAULT_HOST)
        r = api_request(G.DEFAULT_HOST, api_url, data)
        G.ERRORS_SENT += 1
        return r
    except Exception as e:
        print(e)


def send_errors(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            send_error(None, e)
            raise
    return wrapped


def prejoin_workspace(workspace_url, dir_to_share, api_args):
    try:
        result = utils.parse_url(workspace_url)
    except Exception as e:
        msg.error(str_e(e))
        return False
    try:
        w = get_workspace_by_url(workspace_url)
    except Exception as e:
        editor.error_message('Error opening url %s: %s' % (workspace_url, str_e(e)))
        return False

    if w.code >= 400:
        try:
            d = utils.get_persistent_data()
            try:
                del d['workspaces'][result['owner']][result['name']]
            except Exception:
                pass
            try:
                del d['recent_workspaces'][workspace_url]
            except Exception:
                pass
            utils.update_persistent_data(d)
        except Exception as e:
            msg.debug(str_e(e))
        return False

    msg.debug('workspace: %s', json.dumps(w.body))
    anon_perms = w.body.get('perms', {}).get('AnonymousUser', [])
    msg.debug('api args: %s' % api_args)
    new_anon_perms = api_args.get('perms', {}).get('AnonymousUser', [])
    # TODO: prompt/alert user if going from private to public
    if set(anon_perms) != set(new_anon_perms):
        msg.debug(str(anon_perms), str(new_anon_perms))
        w.body['perms']['AnonymousUser'] = new_anon_perms
        response = update_workspace(workspace_url, w.body)
        msg.debug(str(response.body))
    utils.add_workspace_to_persistent_json(w.body['owner'], w.body['name'], workspace_url, dir_to_share)
    return result

########NEW FILE########
__FILENAME__ = cert
CA_CERT = '''-----BEGIN CERTIFICATE-----
MIIHyTCCBbGgAwIBAgIBATANBgkqhkiG9w0BAQUFADB9MQswCQYDVQQGEwJJTDEW
MBQGA1UEChMNU3RhcnRDb20gTHRkLjErMCkGA1UECxMiU2VjdXJlIERpZ2l0YWwg
Q2VydGlmaWNhdGUgU2lnbmluZzEpMCcGA1UEAxMgU3RhcnRDb20gQ2VydGlmaWNh
dGlvbiBBdXRob3JpdHkwHhcNMDYwOTE3MTk0NjM2WhcNMzYwOTE3MTk0NjM2WjB9
MQswCQYDVQQGEwJJTDEWMBQGA1UEChMNU3RhcnRDb20gTHRkLjErMCkGA1UECxMi
U2VjdXJlIERpZ2l0YWwgQ2VydGlmaWNhdGUgU2lnbmluZzEpMCcGA1UEAxMgU3Rh
cnRDb20gQ2VydGlmaWNhdGlvbiBBdXRob3JpdHkwggIiMA0GCSqGSIb3DQEBAQUA
A4ICDwAwggIKAoICAQDBiNsJvGxGfHiflXu1M5DycmLWwTYgIiRezul38kMKogZk
pMyONvg45iPwbm2xPN1yo4UcodM9tDMr0y+v/uqwQVlntsQGfQqedIXWeUyAN3rf
OQVSWff0G0ZDpNKFhdLDcfN1YjS6LIp/Ho/u7TTQEceWzVI9ujPW3U3eCztKS5/C
Ji/6tRYccjV3yjxd5srhJosaNnZcAdt0FCX+7bWgiA/deMotHweXMAEtcnn6RtYT
Kqi5pquDSR3l8u/d5AGOGAqPY1MWhWKpDhk6zLVmpsJrdAfkK+F2PrRt2PZE4XNi
HzvEvqBTViVsUQn3qqvKv3b9bZvzndu/PWa8DFaqr5hIlTpL36dYUNk4dalb6kMM
Av+Z6+hsTXBbKWWc3apdzK8BMewM69KN6Oqce+Zu9ydmDBpI125C4z/eIT574Q1w
+2OqqGwaVLRcJXrJosmLFqa7LH4XXgVNWG4SHQHuEhANxjJ/GP/89PrNbpHoNkm+
Gkhpi8KWTRoSsmkXwQqQ1vp5Iki/untp+HDH+no32NgN0nZPV/+Qt+OR0t3vwmC3
Zzrd/qqc8NSLf3Iizsafl7b4r4qgEKjZ+xjGtrVcUjyJthkqcwEKDwOzEmDyei+B
26Nu/yYwl/WL3YlXtq09s68rxbd2AvCl1iuahhQqcvbjM4xdCUsT37uMdBNSSwID
AQABo4ICUjCCAk4wDAYDVR0TBAUwAwEB/zALBgNVHQ8EBAMCAa4wHQYDVR0OBBYE
FE4L7xqkQFulF2mHMMo0aEPQQa7yMGQGA1UdHwRdMFswLKAqoCiGJmh0dHA6Ly9j
ZXJ0LnN0YXJ0Y29tLm9yZy9zZnNjYS1jcmwuY3JsMCugKaAnhiVodHRwOi8vY3Js
LnN0YXJ0Y29tLm9yZy9zZnNjYS1jcmwuY3JsMIIBXQYDVR0gBIIBVDCCAVAwggFM
BgsrBgEEAYG1NwEBATCCATswLwYIKwYBBQUHAgEWI2h0dHA6Ly9jZXJ0LnN0YXJ0
Y29tLm9yZy9wb2xpY3kucGRmMDUGCCsGAQUFBwIBFilodHRwOi8vY2VydC5zdGFy
dGNvbS5vcmcvaW50ZXJtZWRpYXRlLnBkZjCB0AYIKwYBBQUHAgIwgcMwJxYgU3Rh
cnQgQ29tbWVyY2lhbCAoU3RhcnRDb20pIEx0ZC4wAwIBARqBl0xpbWl0ZWQgTGlh
YmlsaXR5LCByZWFkIHRoZSBzZWN0aW9uICpMZWdhbCBMaW1pdGF0aW9ucyogb2Yg
dGhlIFN0YXJ0Q29tIENlcnRpZmljYXRpb24gQXV0aG9yaXR5IFBvbGljeSBhdmFp
bGFibGUgYXQgaHR0cDovL2NlcnQuc3RhcnRjb20ub3JnL3BvbGljeS5wZGYwEQYJ
YIZIAYb4QgEBBAQDAgAHMDgGCWCGSAGG+EIBDQQrFilTdGFydENvbSBGcmVlIFNT
TCBDZXJ0aWZpY2F0aW9uIEF1dGhvcml0eTANBgkqhkiG9w0BAQUFAAOCAgEAFmyZ
9GYMNPXQhV59CuzaEE44HF7fpiUFS5Eyweg78T3dRAlbB0mKKctmArexmvclmAk8
jhvh3TaHK0u7aNM5Zj2gJsfyOZEdUauCe37Vzlrk4gNXcGmXCPleWKYK34wGmkUW
FjgKXlf2Ysd6AgXmvB618p70qSmD+LIU424oh0TDkBreOKk8rENNZEXO3SipXPJz
ewT4F+irsfMuXGRuczE6Eri8sxHkfY+BUZo7jYn0TZNmezwD7dOaHZrzZVD1oNB1
ny+v8OqCQ5j4aZyJecRDjkZy42Q2Eq/3JR44iZB3fsNrarnDy0RLrHiQi+fHLB5L
EUTINFInzQpdn4XBidUaePKVEFMy3YCEZnXZtWgo+2EuvoSoOMCZEoalHmdkrQYu
L6lwhceWD3yJZfWOQ1QOq92lgDmUYMA0yZZwLKMS9R9Ie70cfmu3nZD0Ijuu+Pwq
yvqCUqDvr0tVk+vBtfAii6w0TiYiBKGHLHVKt+V9E9e4DGTANtLJL4YSjCMJwRuC
O3NJo2pXh5Tl1njFmUNj403gdy3hZZlyaQQaRwnmDwFWJPsfvw55qVguucQJAX6V
um0ABj6y6koQOdjQK/W/7HW/lwLFCRsI3FU34oH7N4RDYiDK51ZLZer+bMEkkySh
NOsF/5oirpt9P/FlUQqmMGqz9IgcgA38corog14=
-----END CERTIFICATE-----'''

########NEW FILE########
__FILENAME__ = event_emitter
class EventEmitter(object):
    def __init__(self):
        self._on_handlers = {}
        self._once_handlers = {}

    def on(self, event, handler):
        if event not in self._on_handlers:
            self._on_handlers[event] = []
        self._on_handlers[event].append(handler)

    def once(self, event, handler):
        if event not in self._once_handlers:
            self._once_handlers[event] = []
        self._once_handlers[event].append(handler)

    def emit(self, event, *args, **kwargs):
        handlers = self._once_handlers.pop(event, [])
        handlers += self._on_handlers.get(event, [])
        for handler in handlers:
            handler(*args, **kwargs)

########NEW FILE########
__FILENAME__ = exc_fmt
#!/usr/local/bin/python
# coding: utf-8
import sys
import warnings
import traceback

try:
    unicode()
except NameError:
    unicode = None


def str_e(e):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        message = getattr(e, "message", None)
        if not (message and unicode):
            return str(e)
        try:
            return unicode(message, "utf8").encode("utf8")
        except:
            return message.encode("utf8")


def pp_e(e):
    """returns a str in all pythons everywher"""
    # py3k has __traceback__
    tb = getattr(e, "__traceback__", None)
    if tb is not None:
        return "\n".join(traceback.format_tb(tb))

    # in case of sys.exc_clear()
    _, _, tb = sys.exc_info()
    if tb is not None:
        return "\n".join(traceback.format_tb(tb))

    return str_e(e)


if __name__ == "__main__":
    def test(excp):
        try:
            raise excp
        except Exception as e:
            stre = str_e(e)
            assert isinstance(stre, str)
            print(stre)

    def test2(excp):
        try:
            raise excp
        except Exception as e:
            sys.exc_clear()
            stre = str_e(e)
            assert isinstance(stre, str)
            print(stre)

    tests = [Exception("asdf"),  Exception(u"aß∂ƒ"),  Exception(u"asdf"),  Exception(b"asdf1234")]
    for t in tests:
        test(t)
        if getattr(sys, "exc_clear", None):
            test2(t)

########NEW FILE########
__FILENAME__ = account
import os
import sys
import traceback
import getpass

try:
    from . import base
    from .. import msg, api, shared as G, utils
    from ....floo import editor
    from ..exc_fmt import str_e
    from ..protocols import no_reconnect
    assert api and G and msg and utils
except (ImportError, ValueError):
    import base
    from floo import editor
    from floo.common.protocols import no_reconnect
    from floo.common.exc_fmt import str_e
    from .. import msg, api, shared as G, utils


class CreateAccountHandler(base.BaseHandler):
    PROTOCOL = no_reconnect.NoReconnectProto
    # TODO: timeout after 60 seconds

    def on_connect(self):
        try:
            username = getpass.getuser()
        except Exception:
            username = ''

        self.send({
            'name': 'create_user',
            'username': username,
            'client': self.client,
            'platform': sys.platform,
            'version': G.__VERSION__
        })

    def on_data(self, name, data):
        if name == 'create_user':
            del data['name']
            try:
                floorc = self.BASE_FLOORC + '\n'.join(['%s %s' % (k, v) for k, v in data.items()]) + '\n'
                with open(G.FLOORC_PATH, 'w') as floorc_fd:
                    floorc_fd.write(floorc)
                utils.reload_settings()
                if utils.can_auth():
                    p = os.path.join(G.BASE_DIR, 'welcome.md')
                    with open(p, 'w') as fd:
                        text = editor.welcome_text % (G.AUTH.get(self.proto.host, {}).get('username'), self.proto.host)
                        fd.write(text)
                    d = utils.get_persistent_data()
                    d['auto_generated_account'] = True
                    utils.update_persistent_data(d)
                    G.AUTO_GENERATED_ACCOUNT = True
                    editor.open_file(p)
                else:
                    editor.error_message('Something went wrong. You will need to sign up for an account to use Floobits.')
                    api.send_error('No username or secret')
            except Exception as e:
                msg.debug(traceback.format_exc())
                msg.error(str_e(e))
            try:
                d = utils.get_persistent_data()
                d['disable_account_creation'] = True
                utils.update_persistent_data(d)
            finally:
                self.proto.stop()

########NEW FILE########
__FILENAME__ = base
try:
    from ... import editor
except ValueError:
    from floo import editor
from .. import msg, event_emitter, shared as G, utils


BASE_FLOORC = '''# Floobits config

# Logs messages to Sublime Text console instead of a special view
#log_to_console 1

# Enables debug mode
#debug 1

'''


class BaseHandler(event_emitter.EventEmitter):
    BASE_FLOORC = BASE_FLOORC
    PROTOCOL = None

    def __init__(self):
        super(BaseHandler, self).__init__()
        self.joined_workspace = False
        G.AGENT = self
        # TODO: removeme?
        utils.reload_settings()

    def build_protocol(self, *args):
        self.proto = self.PROTOCOL(*args)
        self.proto.on("data", self.on_data)
        self.proto.on("connect", self.on_connect)
        return self.proto

    def send(self, *args, **kwargs):
        self.proto.put(*args, **kwargs)

    def on_data(self, name, data):
        handler = getattr(self, "_on_%s" % name, None)
        if handler:
            return handler(data)
        msg.debug('unknown name!', name, 'data:', data)

    @property
    def client(self):
        return editor.name()

    @property
    def codename(self):
        return editor.codename()

    def _on_error(self, data):
        message = 'Error from server! Message: %s' % str(data.get('msg'))
        msg.error(message)
        if data.get('flash'):
            editor.error_message('Error from Floobits server: %s' % str(data.get('msg')))

    def _on_disconnect(self, data):
        message = 'Disconnected from server! Reason: %s' % str(data.get('reason'))
        msg.error(message)
        editor.error_message(message)
        self.stop()

    def stop(self):
        from .. import reactor
        reactor.reactor.stop_handler(self)
        G.AGENT = None

    def is_ready(self):
        return self.joined_workspace

    def tick(self):
        pass

########NEW FILE########
__FILENAME__ = credentials
import os
import sys
import webbrowser

try:
    from . import base
    from .. import api, shared as G, utils
    from ... import editor
    from ..protocols import no_reconnect
    assert api and G and utils
except (ImportError, ValueError):
    import base
    from floo import editor
    from floo.common.protocols import no_reconnect
    from .. import api, shared as G, utils

WELCOME_MSG = """Welcome %s!\n\nYou are all set to collaborate.

You may want to check out our docs at https://%s/help/plugins/sublime#usage"""


class RequestCredentialsHandler(base.BaseHandler):
    PROTOCOL = no_reconnect.NoReconnectProto

    def __init__(self, token):
        super(RequestCredentialsHandler, self).__init__()
        self.token = token

    def build_protocol(self, *args):
        proto = super(RequestCredentialsHandler, self).build_protocol(*args)

        def on_stop():
            self.emit('end', False)
            self.stop()

        proto.once('stop', on_stop)
        return proto

    def is_ready(self):
        return False

    def on_connect(self):
        webbrowser.open('https://%s/dash/link_editor/%s/%s' % (self.proto.host, self.codename, self.token))
        self.send({
            'name': 'request_credentials',
            'client': self.client,
            'platform': sys.platform,
            'token': self.token,
            'version': G.__VERSION__
        })

    def on_data(self, name, data):
        if name == 'credentials':
            s = utils.load_floorc_json()
            auth = s.get('AUTH', {})
            auth[self.proto.host] = data['credentials']
            s['AUTH'] = auth
            utils.save_floorc_json(s)
            utils.reload_settings()
            success = utils.can_auth(self.proto.host)
            if not success:
                editor.error_message('Something went wrong. See https://%s/help/floorc to complete the installation.' % self.proto.host)
                api.send_error('No username or secret')
            else:
                p = os.path.join(G.BASE_DIR, 'welcome.md')
                with open(p, 'w') as fd:
                    text = WELCOME_MSG % (G.AUTH.get(self.proto.host, {}).get('username'), self.proto.host)
                    fd.write(text)
                editor.open_file(p)
            self.emit('end', success)
            self.stop()

########NEW FILE########
__FILENAME__ = floo_handler
import os
import sys
import hashlib
import base64
import collections
from functools import reduce
from operator import attrgetter

try:
    from . import base
    from ..reactor import reactor
    from ..lib import DMP
    from .. import msg, ignore, shared as G, utils
    from ..exc_fmt import str_e
    from ... import editor
    from ..protocols import floo_proto
except (ImportError, ValueError) as e:
    import base
    from floo import editor
    from floo.common.lib import DMP
    from floo.common.reactor import reactor
    from floo.common.exc_fmt import str_e
    from floo.common import msg, ignore, shared as G, utils
    from floo.common.protocols import floo_proto

try:
    unicode()
except NameError:
    unicode = str

try:
    import io
except ImportError:
    io = None


MAX_WORKSPACE_SIZE = 100000000  # 100MB
TOO_BIG_TEXT = '''Maximum workspace size is %.2fMB.\n
%s is too big (%.2fMB) to upload.\n\nWould you like to ignore the following and continue?\n\n%s'''


class FlooHandler(base.BaseHandler):
    PROTOCOL = floo_proto.FlooProtocol

    def __init__(self, owner, workspace, auth, upload=None):
        self.username = auth.get('username')
        self.secret = auth.get('secret')
        self.api_key = auth.get('api_key')
        # BaseHandler calls reload_settings()
        super(FlooHandler, self).__init__()
        self.owner = owner
        self.workspace = workspace
        self.upload_path = upload and utils.unfuck_path(upload)
        self.reset()

    def _on_highlight(self, data):
        raise NotImplementedError("_on_highlight not implemented")

    def ok_cancel_dialog(self, msg, cb=None):
        raise NotImplementedError("ok_cancel_dialog not implemented.")

    def get_view(self, buf_id):
        raise NotImplementedError("get_view not implemented")

    def get_view_text_by_path(self, rel_path):
        raise NotImplementedError("get_view_text_by_path not implemented")

    def build_protocol(self, *args):
        self.proto = super(FlooHandler, self).build_protocol(*args)

        def f():
            self.joined_workspace = False
        self.proto.on("cleanup", f)
        return self.proto

    def get_username_by_id(self, user_id):
        try:
            return self.workspace_info['users'][str(user_id)]['username']
        except Exception:
            return ''

    def get_buf_by_path(self, path):
        try:
            p = utils.to_rel_path(path)
        except ValueError:
            return
        buf_id = self.paths_to_ids.get(p)
        if buf_id:
            return self.bufs.get(buf_id)

    def get_buf(self, buf_id, view=None):
        self.send({
            'name': 'get_buf',
            'id': buf_id
        })
        buf = self.bufs[buf_id]
        msg.warn('Syncing buffer %s for consistency.' % buf['path'])
        if 'buf' in buf:
            del buf['buf']

        if view:
            view.set_read_only(True)
            view.set_status('Floobits locked this file until it is synced.')
            try:
                del G.VIEW_TO_HASH[view.native_id]
            except Exception:
                pass

    def save_view(self, view):
        view.save()

    def on_connect(self):
        utils.reload_settings()

        req = {
            'username': self.username,
            'secret': self.secret,
            'room': self.workspace,
            'room_owner': self.owner,
            'client': self.client,
            'platform': sys.platform,
            'supported_encodings': ['utf8', 'base64'],
            'version': G.__VERSION__
        }

        if self.api_key:
            req['api_key'] = self.api_key
        self.send(req)

    @property
    def workspace_url(self):
        protocol = self.proto.secure and 'https' or 'http'
        return '{protocol}://{host}/{owner}/{name}'.format(protocol=protocol, host=self.proto.host, owner=self.owner, name=self.workspace)

    def reset(self):
        self.bufs = {}
        self.paths_to_ids = {}
        self.save_on_get_bufs = set()
        self.on_load = collections.defaultdict(dict)
        self.upload_timeout = None

    def _on_patch(self, data):
        buf_id = data['id']
        buf = self.bufs[buf_id]
        if 'buf' not in buf:
            msg.debug('buf %s not populated yet. not patching' % buf['path'])
            return

        if buf['encoding'] == 'base64':
            # TODO apply binary patches
            return self.get_buf(buf_id, None)

        if len(data['patch']) == 0:
            msg.debug('wtf? no patches to apply. server is being stupid')
            return

        msg.debug('patch is', data['patch'])
        dmp_patches = DMP.patch_fromText(data['patch'])
        # TODO: run this in a separate thread
        old_text = buf['buf']

        view = self.get_view(buf_id)
        if view and not view.is_loading():
            view_text = view.get_text()
            if old_text == view_text:
                buf['forced_patch'] = False
            elif not buf.get('forced_patch'):
                patch = utils.FlooPatch(view_text, buf)
                # Update the current copy of the buffer
                buf['buf'] = patch.current
                buf['md5'] = hashlib.md5(patch.current.encode('utf-8')).hexdigest()
                buf['forced_patch'] = True
                msg.debug('forcing patch for %s' % buf['path'])
                self.send(patch.to_json())
                old_text = view_text
            else:
                msg.debug('forced patch is true. not sending another patch for buf %s' % buf['path'])
        md5_before = hashlib.md5(old_text.encode('utf-8')).hexdigest()
        if md5_before != data['md5_before']:
            msg.warn('starting md5s don\'t match for %s. this is dangerous!' % buf['path'])

        t = DMP.patch_apply(dmp_patches, old_text)

        clean_patch = True
        for applied_patch in t[1]:
            if not applied_patch:
                clean_patch = False
                break

        if G.DEBUG:
            if len(t[0]) == 0:
                try:
                    msg.debug('OMG EMPTY!')
                    msg.debug('Starting data:', buf['buf'])
                    msg.debug('Patch:', data['patch'])
                except Exception as e:
                    msg.error(e)

            if '\x01' in t[0]:
                msg.debug('FOUND CRAZY BYTE IN BUFFER')
                msg.debug('Starting data:', buf['buf'])
                msg.debug('Patch:', data['patch'])

        timeout_id = buf.get('timeout_id')
        if timeout_id:
            utils.cancel_timeout(timeout_id)
            del buf['timeout_id']

        if not clean_patch:
            msg.log('Couldn\'t patch %s cleanly.' % buf['path'])
            return self.get_buf(buf_id, view)

        cur_hash = hashlib.md5(t[0].encode('utf-8')).hexdigest()
        if cur_hash != data['md5_after']:
            buf['timeout_id'] = utils.set_timeout(self.get_buf, 2000, buf_id, view)

        buf['buf'] = t[0]
        buf['md5'] = cur_hash

        if not view:
            msg.debug('No view. Not saving buffer %s' % buf_id)

            def _on_load():
                v = self.get_view(buf_id)
                if v:
                    v.update(buf, message=False)
            self.on_load[buf_id]['patch'] = _on_load
            return

        view.apply_patches(buf, t, data['username'])

    def _on_get_buf(self, data):
        buf_id = data['id']
        buf = self.bufs.get(buf_id)
        if not buf:
            return msg.warn('no buf found: %s.  Hopefully you didn\'t need that' % data)
        timeout_id = buf.get('timeout_id')
        if timeout_id:
            utils.cancel_timeout(timeout_id)

        if data['encoding'] == 'base64':
            data['buf'] = base64.b64decode(data['buf'])

        self.bufs[buf_id] = data

        save = False
        if buf_id in self.save_on_get_bufs:
            self.save_on_get_bufs.remove(buf_id)
            save = True

        view = self.get_view(buf_id)
        if not view:
            msg.debug('No view for buf %s. Saving to disk.' % buf_id)
            return utils.save_buf(data)

        view.update(data)
        if save:
            view.save()

    def _on_create_buf(self, data):
        if data['encoding'] == 'base64':
            data['buf'] = base64.b64decode(data['buf'])
        self.bufs[data['id']] = data
        self.paths_to_ids[data['path']] = data['id']
        view = self.get_view(data['id'])
        if view:
            self.save_view(view)
        else:
            utils.save_buf(data)

    def _on_rename_buf(self, data):
        del self.paths_to_ids[data['old_path']]
        self.paths_to_ids[data['path']] = data['id']
        new = utils.get_full_path(data['path'])
        old = utils.get_full_path(data['old_path'])
        new_dir = os.path.split(new)[0]
        if new_dir:
            utils.mkdir(new_dir)
        view = self.get_view(data['id'])
        if view:
            view.rename(new)
        else:
            os.rename(old, new)
        self.bufs[data['id']]['path'] = data['path']

    def _on_delete_buf(self, data):
        buf_id = data['id']
        try:
            buf = self.bufs.get(buf_id)
            if buf:
                del self.paths_to_ids[buf['path']]
                del self.bufs[buf_id]
        except KeyError:
            msg.debug('KeyError deleting buf id %s' % buf_id)
        # TODO: if data['unlink'] == True, add to ignore?
        action = 'removed'
        path = utils.get_full_path(data['path'])
        if data.get('unlink', False):
            action = 'deleted'
            try:
                utils.rm(path)
            except Exception as e:
                msg.debug('Error deleting %s: %s' % (path, str_e(e)))
        user_id = data.get('user_id')
        username = self.get_username_by_id(user_id)
        msg.log('%s %s %s' % (username, action, path))

    def _upload_file_by_path(self, rel_path):
        return self._upload(utils.get_full_path(rel_path), self.get_view_text_by_path(rel_path))

    @utils.inlined_callbacks
    def _initial_upload(self, ig, missing_bufs, changed_bufs, cb):
        files, size = yield self.prompt_ignore, ig, G.PROJECT_PATH

        for buf in missing_bufs:
            self.send({'name': 'delete_buf', 'id': buf['id']})

        # TODO: pace ourselves (send through the uploader...)
        for buf in changed_bufs:
            self.send({
                'name': 'set_buf',
                'id': buf['id'],
                'buf': buf['buf'],
                'md5': buf['md5'],
                'encoding': buf['encoding'],
            })

        for p, buf_id in self.paths_to_ids.items():
            if p in files:
                files.discard(p)
                continue
            self.send({
                'name': 'delete_buf',
                'id': buf_id,
            })

        def __upload(rel_path):
            buf_id = self.paths_to_ids.get(rel_path)
            text = self.bufs.get(buf_id, {}).get('buf')
            # Only upload stuff that's not in self.bufs (new bufs). We already took care of everything else.
            if text is not None:
                return len(text)
            return self._upload(utils.get_full_path(rel_path), self.get_view_text_by_path(rel_path))

        self._rate_limited_upload(iter(files), size, upload_func=__upload)
        cb()

    @utils.inlined_callbacks
    def _on_room_info(self, data):
        self.reset()
        self.joined_workspace = True
        self.workspace_info = data
        G.PERMS = data['perms']

        read_only = False
        if 'patch' not in data['perms']:
            read_only = True
            no_perms_msg = '''You don't have permission to edit this workspace. All files will be read-only.'''
            msg.log('No patch permission. Setting buffers to read-only')
            if 'request_perm' in data['perms']:
                should_send = yield self.ok_cancel_dialog, no_perms_msg + '\nDo you want to request edit permission?'
                # TODO: wait for perms to be OK'd/denied before uploading or bailing
                if should_send:
                    self.send({'name': 'request_perms', 'perms': ['edit_room']})
            else:
                if G.EXPERT_MODE:
                    editor.status_message(no_perms_msg)
                else:
                    editor.error_message(no_perms_msg)

        floo_json = {
            'url': utils.to_workspace_url({
                'owner': self.owner,
                'workspace': self.workspace,
                'host': self.proto.host,
                'port': self.proto.port,
                'secure': self.proto.secure,
            })
        }
        utils.update_floo_file(os.path.join(G.PROJECT_PATH, '.floo'), floo_json)
        utils.update_recent_workspaces(self.workspace_url)

        changed_bufs = []
        missing_bufs = []
        new_files = set()
        ig = ignore.create_ignore_tree(G.PROJECT_PATH)
        G.IGNORE = ig
        if not read_only:
            new_files = set([utils.to_rel_path(x) for x in ig.list_paths()])

        for buf_id, buf in data['bufs'].items():
            buf_id = int(buf_id)  # json keys must be strings
            buf_path = utils.get_full_path(buf['path'])
            new_dir = os.path.dirname(buf_path)
            utils.mkdir(new_dir)
            self.bufs[buf_id] = buf
            self.paths_to_ids[buf['path']] = buf_id

            view = self.get_view(buf_id)
            if view and not view.is_loading() and buf['encoding'] == 'utf8':
                view_text = view.get_text()
                view_md5 = hashlib.md5(view_text.encode('utf-8')).hexdigest()
                buf['buf'] = view_text
                buf['view'] = view
                G.VIEW_TO_HASH[view.native_id] = view_md5
                if view_md5 == buf['md5']:
                    msg.debug('md5 sum matches view. not getting buffer %s' % buf['path'])
                else:
                    changed_bufs.append(buf)
                    buf['md5'] = view_md5
                continue

            try:
                if buf['encoding'] == "utf8":
                    if io:
                        buf_fd = io.open(buf_path, 'Urt', encoding='utf8')
                        buf_buf = buf_fd.read()
                    else:
                        buf_fd = open(buf_path, 'rb')
                        buf_buf = buf_fd.read().decode('utf-8').replace('\r\n', '\n')
                    md5 = hashlib.md5(buf_buf.encode('utf-8')).hexdigest()
                else:
                    buf_fd = open(buf_path, 'rb')
                    buf_buf = buf_fd.read()
                    md5 = hashlib.md5(buf_buf).hexdigest()
                buf_fd.close()
                buf['buf'] = buf_buf
                if md5 == buf['md5']:
                    msg.debug('md5 sum matches. not getting buffer %s' % buf['path'])
                else:
                    msg.debug('md5 differs. possibly getting buffer later %s' % buf['path'])
                    changed_bufs.append(buf)
                    buf['md5'] = md5
            except Exception as e:
                msg.debug('Error calculating md5 for %s, %s' % (buf['path'], str_e(e)))
                missing_bufs.append(buf)

        ignored = []
        for p, buf_id in self.paths_to_ids.items():
            if p not in new_files:
                ignored.append(p)
            new_files.discard(p)

        if self.upload_path:
            yield self._initial_upload, ig, missing_bufs, changed_bufs
            # TODO: maybe use org name here
            who = 'Your friends'
            anon_perms = G.AGENT.workspace_info.get('anon_perms')
            if 'get_buf' in anon_perms:
                who = 'Anyone'
            _msg = 'You are sharing:\n\n%s\n\n%s can join your workspace at:\n\n%s' % (G.PROJECT_PATH, who, G.AGENT.workspace_url)
            # Workaround for horrible Sublime Text bug
            utils.set_timeout(editor.message_dialog, 0, _msg)

        elif changed_bufs or missing_bufs or new_files:
            # TODO: handle readonly here
            stomp_local = yield self.stomp_prompt, changed_bufs, missing_bufs, list(new_files), ignored
            if stomp_local not in [0, 1]:
                self.stop()
                return
            if stomp_local:
                for buf in changed_bufs:
                    self.get_buf(buf['id'], buf.get('view'))
                    self.save_on_get_bufs.add(buf['id'])
                for buf in missing_bufs:
                    self.get_buf(buf['id'], buf.get('view'))
                    self.save_on_get_bufs.add(buf['id'])
            else:
                yield self._initial_upload, ig, missing_bufs, changed_bufs

        success_msg = 'Successfully joined workspace %s/%s' % (self.owner, self.workspace)
        msg.log(success_msg)
        editor.status_message(success_msg)

        data = utils.get_persistent_data()
        data['recent_workspaces'].insert(0, {"url": self.workspace_url})
        utils.update_persistent_data(data)
        utils.add_workspace_to_persistent_json(self.owner, self.workspace, self.workspace_url, G.PROJECT_PATH)

        temp_data = data.get('temp_data', {})
        hangout = temp_data.get('hangout', {})
        hangout_url = hangout.get('url')
        if hangout_url:
            self.prompt_join_hangout(hangout_url)

        self.emit("room_info")

    def _on_user_info(self, data):
        user_id = str(data['user_id'])
        user_info = data['user_info']
        self.workspace_info['users'][user_id] = user_info
        if user_id == str(self.workspace_info['user_id']):
            G.PERMS = user_info['perms']

    def _on_join(self, data):
        msg.log('%s joined the workspace' % data['username'])
        user_id = str(data['user_id'])
        self.workspace_info['users'][user_id] = data

    def _on_part(self, data):
        msg.log('%s left the workspace' % data['username'])
        user_id = str(data['user_id'])
        try:
            del self.workspace_info['users'][user_id]
        except Exception:
            msg.error('Unable to delete user %s from user list' % (data))

    def _on_set_temp_data(self, data):
        hangout_data = data.get('data', {})
        hangout = hangout_data.get('hangout', {})
        hangout_url = hangout.get('url')
        if hangout_url:
            self.prompt_join_hangout(hangout_url)

    def _on_saved(self, data):
        buf_id = data['id']
        buf = self.bufs.get(buf_id)
        if not buf:
            return
        on_view_load = self.on_load.get(buf_id)
        if on_view_load:
            try:
                del on_view_load['patch']
            except KeyError:
                pass
        view = self.get_view(data['id'])
        if view:
            self.save_view(view)
        elif 'buf' in buf:
            utils.save_buf(buf)
        username = self.get_username_by_id(data['user_id'])
        msg.log('%s saved buffer %s' % (username, buf['path']))

    @utils.inlined_callbacks
    def _on_request_perms(self, data):
        user_id = str(data.get('user_id'))
        username = self.get_username_by_id(user_id)
        if not username:
            msg.debug('Unknown user for id %s. Not handling request_perms event.' % user_id)
            return

        perm_mapping = {
            'edit_room': 'edit',
            'admin_room': 'admin',
        }
        perms = data.get('perms')
        perms_str = ''.join([perm_mapping.get(p) for p in perms])
        prompt = 'User %s is requesting %s permission for this room.' % (username, perms_str)
        message = data.get('message')
        if message:
            prompt += '\n\n%s says: %s' % (username, message)
        prompt += '\n\nDo you want to grant them permission?'
        confirm = yield self.ok_cancel_dialog, prompt
        self.send({
            'name': 'perms',
            'action': confirm and 'add' or 'reject',
            'user_id': user_id,
            'perms': perms,
        })

    def _on_perms(self, data):
        action = data['action']
        user_id = str(data['user_id'])
        user = self.workspace_info['users'].get(user_id)
        if user is None:
            msg.log('No user for id %s. Not handling perms event' % user_id)
            return
        perms = set(user['perms'])
        if action == 'add':
            perms |= set(data['perms'])
        elif action == 'remove':
            perms -= set(data['perms'])
        else:
            return
        user['perms'] = list(perms)
        if user_id == self.workspace_info['user_id']:
            G.PERMS = perms

    def _on_msg(self, data):
        self.on_msg(data)

    def _on_ping(self, data):
        self.send({'name': 'pong'})

    @utils.inlined_callbacks
    def prompt_ignore(self, ig, path, cb):
        ignore.create_flooignore(ig.path)
        dirs = ig.get_children()
        dirs.append(ig)
        dirs = sorted(dirs, key=attrgetter('size'))
        size = starting_size = reduce(lambda x, c: x + c.size, dirs, 0)
        too_big = []
        while size > MAX_WORKSPACE_SIZE and dirs:
            cd = dirs.pop()
            size -= cd.size
            too_big.append(cd)
        if size > MAX_WORKSPACE_SIZE:
            editor.error_message(
                'Maximum workspace size is %.2fMB.\n\n%s is too big (%.2fMB) to upload. Consider adding stuff to the .flooignore file.' %
                (MAX_WORKSPACE_SIZE / 1000000.0, path, ig.size / 1000000.0))
            cb([set(), 0])
            return
        if too_big:
            txt = TOO_BIG_TEXT % (MAX_WORKSPACE_SIZE / 1000000.0, path, starting_size / 1000000.0, "\n".join(set([x.path for x in too_big])))
            upload = yield self.ok_cancel_dialog, txt
            if not upload:
                cb([set(), 0])
                return
        files = set()
        for ig in dirs:
            files = files.union(set([utils.to_rel_path(x) for x in ig.files]))
        cb([files, size])

    def upload(self, path):
        if not utils.is_shared(path):
            editor.error_message('Cannot share %s because is not in shared path %s.\n\nPlease move it there and try again.' % (path, G.PROJECT_PATH))
            return
        ig = ignore.create_ignore_tree(G.PROJECT_PATH)
        G.IGNORE = ig
        is_dir = os.path.isdir(path)
        if ig.is_ignored(path, is_dir, True):
            editor.error_message('Cannot share %s because it is ignored.\n\nAdd an exclude rule (!%s) to your .flooignore file.' % (path, path))
            return
        rel_path = utils.to_rel_path(path)
        if not is_dir:
            self._upload_file_by_path(rel_path)
            return

        for p in rel_path.split('/'):
            child = ig.children.get(p)
            if not child:
                break
            ig = child

        if ig.path != path:
            msg.warn("%s is not the same as %s", ig.path, path)

        self._rate_limited_upload(ig.list_paths(), ig.total_size, upload_func=self._upload_file_by_path)

    def _rate_limited_upload(self, paths_iter, total_bytes, bytes_uploaded=0.0, upload_func=None):
        reactor.tick()
        upload_func = upload_func or (lambda x: self._upload(utils.get_full_path(x)))
        if len(self.proto) > 0:
            self.upload_timeout = utils.set_timeout(self._rate_limited_upload, 10, paths_iter, total_bytes, bytes_uploaded, upload_func)
            return

        bar_len = 20
        try:
            p = next(paths_iter)
            size = upload_func(p)
            bytes_uploaded += size
            try:
                percent = (bytes_uploaded / total_bytes)
            except ZeroDivisionError:
                percent = 0.5
            bar = '   |' + ('|' * int(bar_len * percent)) + (' ' * int((1 - percent) * bar_len)) + '|'
            editor.status_message('Uploading... %2.2f%% %s' % (percent * 100, bar))
        except StopIteration:
            editor.status_message('Uploading... 100% ' + ('|' * bar_len) + '| complete')
            msg.log('All done uploading')
            return
        self.upload_timeout = utils.set_timeout(self._rate_limited_upload, 50, paths_iter, total_bytes, bytes_uploaded, upload_func)

    def _upload(self, path, text=None):
        size = 0
        try:
            if text is None:
                with open(path, 'rb') as buf_fd:
                    buf = buf_fd.read()
            else:
                try:
                    # work around python 3 encoding issue
                    buf = text.encode('utf8')
                except Exception as e:
                    msg.debug('Error encoding buf %s: %s' % (path, str_e(e)))
                    # We're probably in python 2 so it's ok to do this
                    buf = text
            size = len(buf)
            encoding = 'utf8'
            rel_path = utils.to_rel_path(path)
            existing_buf = self.get_buf_by_path(path)
            if existing_buf:
                if text is None:
                    buf_md5 = hashlib.md5(buf).hexdigest()
                    if existing_buf['md5'] == buf_md5:
                        msg.log('%s already exists and has the same md5. Skipping.' % path)
                        return size
                    existing_buf['md5'] = buf_md5
                msg.log('Setting buffer ', rel_path)

                try:
                    buf = buf.decode('utf-8')
                except Exception:
                    buf = base64.b64encode(buf).decode('utf-8')
                    encoding = 'base64'

                existing_buf['buf'] = buf
                existing_buf['encoding'] = encoding

                self.send({
                    'name': 'set_buf',
                    'id': existing_buf['id'],
                    'buf': buf,
                    'md5': existing_buf['md5'],
                    'encoding': encoding,
                })
                return size

            try:
                buf = buf.decode('utf-8')
            except Exception:
                buf = base64.b64encode(buf).decode('utf-8')
                encoding = 'base64'

            msg.log('Creating buffer ', rel_path)
            event = {
                'name': 'create_buf',
                'buf': buf,
                'path': rel_path,
                'encoding': encoding,
            }
            self.send(event)
        except (IOError, OSError):
            msg.error('Failed to open %s.' % path)
        except Exception as e:
            msg.error('Failed to create buffer %s: %s' % (path, str_e(e)))
        return size

    def stop(self):
        if self.upload_timeout is not None:
            utils.cancel_timeout(self.upload_timeout)
            self.upload_timeout = None

        super(FlooHandler, self).stop()

########NEW FILE########
__FILENAME__ = tcp_server

try:
    from . import base
    from .. protocols import tcp_server
except (ImportError, ValueError):
    from floo.common.protocols import tcp_server
    import base


class TCPServerHandler(base.BaseHandler):
    PROTOCOL = tcp_server.TCPServerProtocol

    def __init__(self, factory, reactor):
        self.factory = factory
        self.reactor = reactor

    def is_ready(self):
        return True

    def on_connect(self, conn, host, port):
        self.reactor.connect(self.factory, host, port, False, conn)

########NEW FILE########
__FILENAME__ = ignore
import os
import errno
import fnmatch
import stat

try:
    from . import msg, utils
    from .exc_fmt import str_e
    assert msg and str_e and utils
except ImportError:
    import msg
    from exc_fmt import str_e

IGNORE_FILES = ['.gitignore', '.hgignore', '.flignore', '.flooignore']
HIDDEN_WHITELIST = ['.floo'] + IGNORE_FILES
BLACKLIST = [
    '.DS_Store',
    '.git',
    '.svn',
    '.hg',
]

# TODO: grab global git ignores:
# gitconfig_file = popen("git config -z --get core.excludesfile", "r");
DEFAULT_IGNORES = [
    '#*',
    '*.o',
    '*.pyc',
    '*~',
    'extern/',
    'node_modules/',
    'tmp',
    'vendor/',
]
MAX_FILE_SIZE = 1024 * 1024 * 5

IS_IG_IGNORED = 1
IS_IG_CHECK_CHILD = 2


def create_flooignore(path):
    flooignore = os.path.join(path, '.flooignore')
    # A very short race condition, but whatever.
    if os.path.exists(flooignore):
        return
    try:
        with open(flooignore, 'w') as fd:
            fd.write('\n'.join(DEFAULT_IGNORES))
    except Exception as e:
        msg.error('Error creating default .flooignore: %s' % str_e(e))


def create_ignore_tree(path):
    ig = Ignore(path)
    ig.ignores['/DEFAULT/'] = BLACKLIST
    ig.recurse(ig)
    return ig


class Ignore(object):
    def __init__(self, path, parent=None):
        self.parent = parent
        self.size = 0
        self.total_size = 0
        self.children = {}
        self.files = []
        self.ignores = {
            '/TOO_BIG/': []
        }
        self.path = utils.unfuck_path(path)

    def recurse(self, root):
        try:
            paths = os.listdir(self.path)
        except OSError as e:
            if e.errno != errno.ENOTDIR:
                msg.error('Error listing path %s: %s' % (self.path, str_e(e)))
            return
        except Exception as e:
            msg.error('Error listing path %s: %s' % (self.path, str_e(e)))
            return

        msg.debug('Initializing ignores for %s' % self.path)
        for ignore_file in IGNORE_FILES:
            try:
                self.load(ignore_file)
            except Exception:
                pass

        for p in paths:
            p_path = os.path.join(self.path, p)
            if p in BLACKLIST:
                msg.log('Ignoring blacklisted file %s' % p)
                continue
            if p == '.' or p == '..':
                continue
            try:
                s = os.stat(p_path)
            except Exception as e:
                msg.error('Error stat()ing path %s: %s' % (p_path, str_e(e)))
                continue

            is_dir = stat.S_ISDIR(s.st_mode)
            if root.is_ignored(p_path, is_dir, True):
                continue

            if is_dir:
                ig = Ignore(p_path, self)
                self.children[p] = ig
                ig.recurse(root)
                self.total_size += ig.total_size
                continue

            if stat.S_ISREG(s.st_mode):
                if s.st_size > (MAX_FILE_SIZE):
                    self.ignores['/TOO_BIG/'].append(p)
                    msg.log(self.is_ignored_message(p_path, p, '/TOO_BIG/', False))
                else:
                    self.size += s.st_size
                    self.total_size += s.st_size
                    self.files.append(p_path)

    def load(self, ignore_file):
        with open(os.path.join(self.path, ignore_file), 'r') as fd:
            ignores = fd.read()
        rules = []
        for ignore in ignores.split('\n'):
            ignore = ignore.strip()
            if len(ignore) == 0:
                continue
            if ignore[0] == '#':
                continue
            msg.debug('Adding %s to ignore patterns' % ignore)
            rules.insert(0, ignore)
        self.ignores[ignore_file] = rules

    def get_children(self):
        children = list(self.children.values())
        for c in children:
            children += c.get_children()
        return children

    def list_paths(self):
        for f in self.files:
            yield os.path.join(self.path, f)
        for c in self.children.values():
            for p in c.list_paths():
                yield p

    def is_ignored_message(self, rel_path, pattern, ignore_file, exclude):
        path = os.path.join(self.path, rel_path)
        exclude_msg = ''
        if exclude:
            exclude_msg = '__NOT__ '
        if ignore_file == '/TOO_BIG/':
            return '%s %signored because it is too big (more than %s bytes)' % (path, exclude_msg, MAX_FILE_SIZE)
        return '%s %signored by pattern %s in %s' % (path, exclude_msg, pattern, os.path.join(self.path, ignore_file))

    def is_ignored(self, path, is_dir=None, log=False):
        if is_dir is None:
            try:
                s = os.stat(path)
            except Exception as e:
                msg.error('Error lstat()ing path %s: %s' % (path, str_e(e)))
                return True
            is_dir = stat.S_ISDIR(s.st_mode)
        rel_path = os.path.relpath(path, self.path).replace(os.sep, '/')
        return self._is_ignored(rel_path, is_dir, log)

    def _is_ignored(self, rel_path, is_dir, log):
        base_path, file_name = os.path.split(rel_path)

        for ignore_file, patterns in self.ignores.items():
            for pattern in patterns:
                orig_pattern = pattern
                exclude = False
                match = False
                if pattern[0] == "!":
                    exclude = True
                    pattern = pattern[1:]

                if pattern[0] == '/':
                    match = fnmatch.fnmatch(rel_path, pattern[1:])
                else:
                    if len(pattern) > 0 and pattern[-1] == '/':
                        if is_dir:
                            pattern = pattern[:-1]
                    if fnmatch.fnmatch(file_name, pattern):
                        match = True
                    elif fnmatch.fnmatch(rel_path, pattern):
                        match = True
                if match:
                    if log:
                        msg.log(self.is_ignored_message(rel_path, orig_pattern, ignore_file, exclude))
                    if exclude:
                        return False
                    return True

        split = rel_path.split("/", 1)
        if len(split) != 2:
            return False
        name, new_path = split
        ig = self.children.get(name)
        if ig:
            return ig._is_ignored(new_path, is_dir, log)
        return False

########NEW FILE########
__FILENAME__ = diff_match_patch
#!/usr/bin/python2.4


"""Diff Match and Patch

Copyright 2006 Google Inc.
http://code.google.com/p/google-diff-match-patch/

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

"""Functions for diff, match and patch.

Computes the difference between two texts to create a patch.
Applies the patch onto another text, allowing for errors.
"""

__author__ = 'fraser@google.com (Neil Fraser)'

import re
import sys
import time
try:
    from urllib import parse
    assert parse
    unquote = lambda x: parse.unquote(x)
    str_instances = str
    unichr = chr
except ImportError:
    import urllib as parse
    unquote = lambda x: parse.unquote(x.encode('utf-8')).decode('utf-8')
    import __builtin__
    str_instances = (str, __builtin__.basestring)


class diff_match_patch:
    """Class containing the diff, match and patch methods.

    Also contains the behaviour settings.
    """

    def __init__(self):
        """Inits a diff_match_patch object with default settings.
        Redefine these in your program to override the defaults.
        """

        # Number of seconds to map a diff before giving up (0 for infinity).
        self.Diff_Timeout = 1.0
        # Cost of an empty edit operation in terms of edit characters.
        self.Diff_EditCost = 4
        # At what point is no match declared (0.0 = perfection, 1.0 = very loose).
        self.Match_Threshold = 0.5
        # How far to search for a match (0 = exact location, 1000+ = broad match).
        # A match this many characters away from the expected location will add
        # 1.0 to the score (0.0 is a perfect match).
        self.Match_Distance = 1000
        # When deleting a large block of text (over ~64 characters), how close do
        # the contents have to be to match the expected contents. (0.0 = perfection,
        # 1.0 = very loose).  Note that Match_Threshold controls how closely the
        # end points of a delete need to match.
        self.Patch_DeleteThreshold = 0.5
        # Chunk size for context length.
        self.Patch_Margin = 4

        # The number of bits in an int.
        # Python has no maximum, thus to disable patch splitting set to 0.
        # However to avoid long patches in certain pathological cases, use 32.
        # Multiple short patches (using native ints) are much faster than long ones.
        self.Match_MaxBits = 32

    #  DIFF FUNCTIONS

    # The data structure representing a diff is an array of tuples:
    # [(DIFF_DELETE, "Hello"), (DIFF_INSERT, "Goodbye"), (DIFF_EQUAL, " world.")]
    # which means: delete "Hello", add "Goodbye" and keep " world."
    DIFF_DELETE = -1
    DIFF_INSERT = 1
    DIFF_EQUAL = 0

    def diff_main(self, text1, text2, checklines=True, deadline=None):
        """Find the differences between two texts.  Simplifies the problem by
            stripping any common prefix or suffix off the texts before diffing.

        Args:
            text1: Old string to be diffed.
            text2: New string to be diffed.
            checklines: Optional speedup flag.  If present and false, then don't run
                a line-level diff first to identify the changed areas.
                Defaults to true, which does a faster, slightly less optimal diff.
            deadline: Optional time when the diff should be complete by.  Used
                internally for recursive calls.  Users should set DiffTimeout instead.

        Returns:
            Array of changes.
        """
        # Set a deadline by which time the diff must be complete.
        if deadline is None:
            # Unlike in most languages, Python counts time in seconds.
            if self.Diff_Timeout <= 0:
                deadline = sys.maxsize
            else:
                deadline = time.time() + self.Diff_Timeout

        # Check for null inputs.
        if text1 is None or text2 is None:
            raise ValueError("Null inputs. (diff_main)")

        # Check for equality (speedup).
        if text1 == text2:
            if text1:
                return [(self.DIFF_EQUAL, text1)]
            return []

        # Trim off common prefix (speedup).
        commonlength = self.diff_commonPrefix(text1, text2)
        commonprefix = text1[:commonlength]
        text1 = text1[commonlength:]
        text2 = text2[commonlength:]

        # Trim off common suffix (speedup).
        commonlength = self.diff_commonSuffix(text1, text2)
        if commonlength == 0:
            commonsuffix = ''
        else:
            commonsuffix = text1[-commonlength:]
            text1 = text1[:-commonlength]
            text2 = text2[:-commonlength]

        # Compute the diff on the middle block.
        diffs = self.diff_compute(text1, text2, checklines, deadline)

        # Restore the prefix and suffix.
        if commonprefix:
            diffs[:0] = [(self.DIFF_EQUAL, commonprefix)]
        if commonsuffix:
            diffs.append((self.DIFF_EQUAL, commonsuffix))
        self.diff_cleanupMerge(diffs)
        return diffs

    def diff_compute(self, text1, text2, checklines, deadline):
        """Find the differences between two texts.  Assumes that the texts do not
            have any common prefix or suffix.

        Args:
            text1: Old string to be diffed.
            text2: New string to be diffed.
            checklines: Speedup flag.  If false, then don't run a line-level diff
                first to identify the changed areas.
                If true, then run a faster, slightly less optimal diff.
            deadline: Time when the diff should be complete by.

        Returns:
            Array of changes.
        """
        if not text1:
            # Just add some text (speedup).
            return [(self.DIFF_INSERT, text2)]

        if not text2:
            # Just delete some text (speedup).
            return [(self.DIFF_DELETE, text1)]

        if len(text1) > len(text2):
            (longtext, shorttext) = (text1, text2)
        else:
            (shorttext, longtext) = (text1, text2)
        i = longtext.find(shorttext)
        if i != -1:
            # Shorter text is inside the longer text (speedup).
            diffs = [(self.DIFF_INSERT, longtext[:i]), (self.DIFF_EQUAL, shorttext),
                     (self.DIFF_INSERT, longtext[i + len(shorttext):])]
            # Swap insertions for deletions if diff is reversed.
            if len(text1) > len(text2):
                diffs[0] = (self.DIFF_DELETE, diffs[0][1])
                diffs[2] = (self.DIFF_DELETE, diffs[2][1])
            return diffs

        if len(shorttext) == 1:
            # Single character string.
            # After the previous speedup, the character can't be an equality.
            return [(self.DIFF_DELETE, text1), (self.DIFF_INSERT, text2)]
        longtext = shorttext = None  # Garbage collect.

        # Check to see if the problem can be split in two.
        hm = self.diff_halfMatch(text1, text2)
        if hm:
            # A half-match was found, sort out the return data.
            (text1_a, text1_b, text2_a, text2_b, mid_common) = hm
            # Send both pairs off for separate processing.
            diffs_a = self.diff_main(text1_a, text2_a, checklines, deadline)
            diffs_b = self.diff_main(text1_b, text2_b, checklines, deadline)
            # Merge the results.
            return diffs_a + [(self.DIFF_EQUAL, mid_common)] + diffs_b

        if checklines and len(text1) > 100 and len(text2) > 100:
            return self.diff_lineMode(text1, text2, deadline)

        return self.diff_bisect(text1, text2, deadline)

    def diff_lineMode(self, text1, text2, deadline):
        """Do a quick line-level diff on both strings, then rediff the parts for
            greater accuracy.
            This speedup can produce non-minimal diffs.

        Args:
            text1: Old string to be diffed.
            text2: New string to be diffed.
            deadline: Time when the diff should be complete by.

        Returns:
            Array of changes.
        """

        # Scan the text on a line-by-line basis first.
        (text1, text2, linearray) = self.diff_linesToChars(text1, text2)

        diffs = self.diff_main(text1, text2, False, deadline)

        # Convert the diff back to original text.
        self.diff_charsToLines(diffs, linearray)
        # Eliminate freak matches (e.g. blank lines)
        self.diff_cleanupSemantic(diffs)

        # Rediff any replacement blocks, this time character-by-character.
        # Add a dummy entry at the end.
        diffs.append((self.DIFF_EQUAL, ''))
        pointer = 0
        count_delete = 0
        count_insert = 0
        text_delete = ''
        text_insert = ''
        while pointer < len(diffs):
            if diffs[pointer][0] == self.DIFF_INSERT:
                count_insert += 1
                text_insert += diffs[pointer][1]
            elif diffs[pointer][0] == self.DIFF_DELETE:
                count_delete += 1
                text_delete += diffs[pointer][1]
            elif diffs[pointer][0] == self.DIFF_EQUAL:
                # Upon reaching an equality, check for prior redundancies.
                if count_delete >= 1 and count_insert >= 1:
                    # Delete the offending records and add the merged ones.
                    a = self.diff_main(text_delete, text_insert, False, deadline)
                    diffs[(pointer - count_delete - count_insert):pointer] = a
                    pointer = pointer - count_delete - count_insert + len(a)
                count_insert = 0
                count_delete = 0
                text_delete = ''
                text_insert = ''

            pointer += 1

        diffs.pop()  # Remove the dummy entry at the end.

        return diffs

    def diff_bisect(self, text1, text2, deadline):
        """Find the 'middle snake' of a diff, split the problem in two
            and return the recursively constructed diff.
            See Myers 1986 paper: An O(ND) Difference Algorithm and Its Variations.

        Args:
            text1: Old string to be diffed.
            text2: New string to be diffed.
            deadline: Time at which to bail if not yet complete.

        Returns:
            Array of diff tuples.
        """

        # Cache the text lengths to prevent multiple calls.
        text1_length = len(text1)
        text2_length = len(text2)
        max_d = (text1_length + text2_length + 1) // 2
        v_offset = max_d
        v_length = 2 * max_d
        v1 = [-1] * v_length
        v1[v_offset + 1] = 0
        v2 = v1[:]
        delta = text1_length - text2_length
        # If the total number of characters is odd, then the front path will
        # collide with the reverse path.
        front = (delta % 2 != 0)
        # Offsets for start and end of k loop.
        # Prevents mapping of space beyond the grid.
        k1start = 0
        k1end = 0
        k2start = 0
        k2end = 0
        for d in range(max_d):
            # Bail out if deadline is reached.
            if time.time() > deadline:
                break

            # Walk the front path one step.
            for k1 in range(-d + k1start, d + 1 - k1end, 2):
                k1_offset = v_offset + k1
                if k1 == -d or (k1 != d and v1[k1_offset - 1] < v1[k1_offset + 1]):
                    x1 = v1[k1_offset + 1]
                else:
                    x1 = v1[k1_offset - 1] + 1
                y1 = x1 - k1
                while (x1 < text1_length and y1 < text2_length and text1[x1] == text2[y1]):
                    x1 += 1
                    y1 += 1
                v1[k1_offset] = x1
                if x1 > text1_length:
                    # Ran off the right of the graph.
                    k1end += 2
                elif y1 > text2_length:
                    # Ran off the bottom of the graph.
                    k1start += 2
                elif front:
                    k2_offset = v_offset + delta - k1
                    if k2_offset >= 0 and k2_offset < v_length and v2[k2_offset] != -1:
                        # Mirror x2 onto top-left coordinate system.
                        x2 = text1_length - v2[k2_offset]
                        if x1 >= x2:
                            # Overlap detected.
                            return self.diff_bisectSplit(text1, text2, x1, y1, deadline)

            # Walk the reverse path one step.
            for k2 in range(-d + k2start, d + 1 - k2end, 2):
                k2_offset = v_offset + k2
                if k2 == -d or (k2 != d and v2[k2_offset - 1] < v2[k2_offset + 1]):
                    x2 = v2[k2_offset + 1]
                else:
                    x2 = v2[k2_offset - 1] + 1
                y2 = x2 - k2
                while (x2 < text1_length and y2 < text2_length and text1[-x2 - 1] == text2[-y2 - 1]):
                    x2 += 1
                    y2 += 1
                v2[k2_offset] = x2
                if x2 > text1_length:
                    # Ran off the left of the graph.
                    k2end += 2
                elif y2 > text2_length:
                    # Ran off the top of the graph.
                    k2start += 2
                elif not front:
                    k1_offset = v_offset + delta - k2
                    if k1_offset >= 0 and k1_offset < v_length and v1[k1_offset] != -1:
                        x1 = v1[k1_offset]
                        y1 = v_offset + x1 - k1_offset
                        # Mirror x2 onto top-left coordinate system.
                        x2 = text1_length - x2
                        if x1 >= x2:
                            # Overlap detected.
                            return self.diff_bisectSplit(text1, text2, x1, y1, deadline)

        # Diff took too long and hit the deadline or
        # number of diffs equals number of characters, no commonality at all.
        return [(self.DIFF_DELETE, text1), (self.DIFF_INSERT, text2)]

    def diff_bisectSplit(self, text1, text2, x, y, deadline):
        """Given the location of the 'middle snake', split the diff in two parts
        and recurse.

        Args:
            text1: Old string to be diffed.
            text2: New string to be diffed.
            x: Index of split point in text1.
            y: Index of split point in text2.
            deadline: Time at which to bail if not yet complete.

        Returns:
            Array of diff tuples.
        """
        text1a = text1[:x]
        text2a = text2[:y]
        text1b = text1[x:]
        text2b = text2[y:]

        # Compute both diffs serially.
        diffs = self.diff_main(text1a, text2a, False, deadline)
        diffsb = self.diff_main(text1b, text2b, False, deadline)

        return diffs + diffsb

    def diff_linesToChars(self, text1, text2):
        """Split two texts into an array of strings.  Reduce the texts to a string
        of hashes where each Unicode character represents one line.

        Args:
            text1: First string.
            text2: Second string.

        Returns:
            Three element tuple, containing the encoded text1, the encoded text2 and
            the array of unique strings.  The zeroth element of the array of unique
            strings is intentionally blank.
        """
        lineArray = []  # e.g. lineArray[4] == "Hello\n"
        lineHash = {}   # e.g. lineHash["Hello\n"] == 4

        # "\x00" is a valid character, but various debuggers don't like it.
        # So we'll insert a junk entry to avoid generating a null character.
        lineArray.append('')

        def diff_linesToCharsMunge(text):
            """Split a text into an array of strings.  Reduce the texts to a string
            of hashes where each Unicode character represents one line.
            Modifies linearray and linehash through being a closure.

            Args:
                text: String to encode.

            Returns:
                Encoded string.
            """
            chars = []
            # Walk the text, pulling out a substring for each line.
            # text.split('\n') would would temporarily double our memory footprint.
            # Modifying text would create many large strings to garbage collect.
            lineStart = 0
            lineEnd = -1
            while lineEnd < len(text) - 1:
                lineEnd = text.find('\n', lineStart)
                if lineEnd == -1:
                    lineEnd = len(text) - 1
                line = text[lineStart:lineEnd + 1]
                lineStart = lineEnd + 1

                if line in lineHash:
                    chars.append(unichr(lineHash[line]))
                else:
                    lineArray.append(line)
                    lineHash[line] = len(lineArray) - 1
                    chars.append(unichr(len(lineArray) - 1))
            return "".join(chars)

        chars1 = diff_linesToCharsMunge(text1)
        chars2 = diff_linesToCharsMunge(text2)
        return (chars1, chars2, lineArray)

    def diff_charsToLines(self, diffs, lineArray):
        """Rehydrate the text in a diff from a string of line hashes to real lines
        of text.

        Args:
            diffs: Array of diff tuples.
            lineArray: Array of unique strings.
        """
        for x in range(len(diffs)):
            text = []
            for char in diffs[x][1]:
                text.append(lineArray[ord(char)])
            diffs[x] = (diffs[x][0], "".join(text))

    def diff_commonPrefix(self, text1, text2):
        """Determine the common prefix of two strings.

        Args:
            text1: First string.
            text2: Second string.

        Returns:
            The number of characters common to the start of each string.
        """
        # Quick check for common null cases.
        if not text1 or not text2 or text1[0] != text2[0]:
            return 0
        # Binary search.
        # Performance analysis: http://neil.fraser.name/news/2007/10/09/
        pointermin = 0
        pointermax = min(len(text1), len(text2))
        pointermid = pointermax
        pointerstart = 0
        while pointermin < pointermid:
            if text1[pointerstart:pointermid] == text2[pointerstart:pointermid]:
                pointermin = pointermid
                pointerstart = pointermin
            else:
                pointermax = pointermid
            pointermid = (pointermax - pointermin) // 2 + pointermin
        return pointermid

    def diff_commonSuffix(self, text1, text2):
        """Determine the common suffix of two strings.

        Args:
            text1: First string.
            text2: Second string.

        Returns:
            The number of characters common to the end of each string.
        """
        # Quick check for common null cases.
        if not text1 or not text2 or text1[-1] != text2[-1]:
            return 0
        # Binary search.
        # Performance analysis: http://neil.fraser.name/news/2007/10/09/
        pointermin = 0
        pointermax = min(len(text1), len(text2))
        pointermid = pointermax
        pointerend = 0
        while pointermin < pointermid:
            if text1[-pointermid:len(text1) - pointerend] == text2[-pointermid:len(text2) - pointerend]:
                pointermin = pointermid
                pointerend = pointermin
            else:
                pointermax = pointermid
            pointermid = (pointermax - pointermin) // 2 + pointermin
        return pointermid

    def diff_commonOverlap(self, text1, text2):
        """Determine if the suffix of one string is the prefix of another.

        Args:
            text1 First string.
            text2 Second string.

        Returns:
            The number of characters common to the end of the first
            string and the start of the second string.
        """
        # Cache the text lengths to prevent multiple calls.
        text1_length = len(text1)
        text2_length = len(text2)
        # Eliminate the null case.
        if text1_length == 0 or text2_length == 0:
            return 0
        # Truncate the longer string.
        if text1_length > text2_length:
            text1 = text1[-text2_length:]
        elif text1_length < text2_length:
            text2 = text2[:text1_length]
        text_length = min(text1_length, text2_length)
        # Quick check for the worst case.
        if text1 == text2:
            return text_length

        # Start by looking for a single character match
        # and increase length until no match is found.
        # Performance analysis: http://neil.fraser.name/news/2010/11/04/
        best = 0
        length = 1
        while True:
            pattern = text1[-length:]
            found = text2.find(pattern)
            if found == -1:
                return best
            length += found
            if found == 0 or text1[-length:] == text2[:length]:
                best = length
                length += 1

    def diff_halfMatch(self, text1, text2):
        """Do the two texts share a substring which is at least half the length of
        the longer text?
        This speedup can produce non-minimal diffs.

        Args:
            text1: First string.
            text2: Second string.

        Returns:
            Five element Array, containing the prefix of text1, the suffix of text1,
            the prefix of text2, the suffix of text2 and the common middle.  Or None
            if there was no match.
        """
        if self.Diff_Timeout <= 0:
            # Don't risk returning a non-optimal diff if we have unlimited time.
            return None
        if len(text1) > len(text2):
            (longtext, shorttext) = (text1, text2)
        else:
            (shorttext, longtext) = (text1, text2)
        if len(longtext) < 4 or len(shorttext) * 2 < len(longtext):
            return None  # Pointless.

        def diff_halfMatchI(longtext, shorttext, i):
            """Does a substring of shorttext exist within longtext such that the
            substring is at least half the length of longtext?
            Closure, but does not reference any external variables.

            Args:
                longtext: Longer string.
                shorttext: Shorter string.
                i: Start index of quarter length substring within longtext.

            Returns:
                Five element Array, containing the prefix of longtext, the suffix of
                longtext, the prefix of shorttext, the suffix of shorttext and the
                common middle.  Or None if there was no match.
            """
            seed = longtext[i:i + len(longtext) // 4]
            best_common = ''
            j = shorttext.find(seed)
            while j != -1:
                prefixLength = self.diff_commonPrefix(longtext[i:], shorttext[j:])
                suffixLength = self.diff_commonSuffix(longtext[:i], shorttext[:j])
                if len(best_common) < suffixLength + prefixLength:
                    best_common = (shorttext[j - suffixLength:j] + shorttext[j:j + prefixLength])
                    best_longtext_a = longtext[:i - suffixLength]
                    best_longtext_b = longtext[i + prefixLength:]
                    best_shorttext_a = shorttext[:j - suffixLength]
                    best_shorttext_b = shorttext[j + prefixLength:]
                j = shorttext.find(seed, j + 1)

            if len(best_common) * 2 >= len(longtext):
                return (best_longtext_a, best_longtext_b,
                        best_shorttext_a, best_shorttext_b, best_common)
            else:
                return None

        # First check if the second quarter is the seed for a half-match.
        hm1 = diff_halfMatchI(longtext, shorttext, (len(longtext) + 3) // 4)
        # Check again based on the third quarter.
        hm2 = diff_halfMatchI(longtext, shorttext, (len(longtext) + 1) // 2)
        if not hm1 and not hm2:
            return None
        elif not hm2:
            hm = hm1
        elif not hm1:
            hm = hm2
        else:
            # Both matched.  Select the longest.
            if len(hm1[4]) > len(hm2[4]):
                hm = hm1
            else:
                hm = hm2

        # A half-match was found, sort out the return data.
        if len(text1) > len(text2):
            (text1_a, text1_b, text2_a, text2_b, mid_common) = hm
        else:
            (text2_a, text2_b, text1_a, text1_b, mid_common) = hm
        return (text1_a, text1_b, text2_a, text2_b, mid_common)

    def diff_cleanupSemantic(self, diffs):
        """Reduce the number of edits by eliminating semantically trivial
        equalities.

        Args:
            diffs: Array of diff tuples.
        """
        changes = False
        equalities = []  # Stack of indices where equalities are found.
        lastequality = None  # Always equal to diffs[equalities[-1]][1]
        pointer = 0  # Index of current position.
        # Number of chars that changed prior to the equality.
        length_insertions1, length_deletions1 = 0, 0
        # Number of chars that changed after the equality.
        length_insertions2, length_deletions2 = 0, 0
        while pointer < len(diffs):
            if diffs[pointer][0] == self.DIFF_EQUAL:  # Equality found.
                equalities.append(pointer)
                length_insertions1, length_insertions2 = length_insertions2, 0
                length_deletions1, length_deletions2 = length_deletions2, 0
                lastequality = diffs[pointer][1]
            else:  # An insertion or deletion.
                if diffs[pointer][0] == self.DIFF_INSERT:
                    length_insertions2 += len(diffs[pointer][1])
                else:
                    length_deletions2 += len(diffs[pointer][1])
                # Eliminate an equality that is smaller or equal to the edits on both
                # sides of it.
                if (lastequality and (len(lastequality) <=
                                      max(length_insertions1, length_deletions1)) and
                                     (len(lastequality) <= max(length_insertions2, length_deletions2))):
                    # Duplicate record.
                    diffs.insert(equalities[-1], (self.DIFF_DELETE, lastequality))
                    # Change second copy to insert.
                    diffs[equalities[-1] + 1] = (self.DIFF_INSERT, diffs[equalities[-1] + 1][1])
                    # Throw away the equality we just deleted.
                    equalities.pop()
                    # Throw away the previous equality (it needs to be reevaluated).
                    if len(equalities):
                        equalities.pop()
                    if len(equalities):
                        pointer = equalities[-1]
                    else:
                        pointer = -1
                    # Reset the counters.
                    length_insertions1, length_deletions1 = 0, 0
                    length_insertions2, length_deletions2 = 0, 0
                    lastequality = None
                    changes = True
            pointer += 1

        # Normalize the diff.
        if changes:
            self.diff_cleanupMerge(diffs)
        self.diff_cleanupSemanticLossless(diffs)

        # Find any overlaps between deletions and insertions.
        # e.g: <del>abcxxx</del><ins>xxxdef</ins>
        #   -> <del>abc</del>xxx<ins>def</ins>
        # e.g: <del>xxxabc</del><ins>defxxx</ins>
        #   -> <ins>def</ins>xxx<del>abc</del>
        # Only extract an overlap if it is as big as the edit ahead or behind it.
        pointer = 1
        while pointer < len(diffs):
            if (diffs[pointer - 1][0] == self.DIFF_DELETE and
                    diffs[pointer][0] == self.DIFF_INSERT):
                deletion = diffs[pointer - 1][1]
                insertion = diffs[pointer][1]
                overlap_length1 = self.diff_commonOverlap(deletion, insertion)
                overlap_length2 = self.diff_commonOverlap(insertion, deletion)
                if overlap_length1 >= overlap_length2:
                    if (overlap_length1 >= len(deletion) / 2.0 or
                            overlap_length1 >= len(insertion) / 2.0):
                        # Overlap found.  Insert an equality and trim the surrounding edits.
                        diffs.insert(pointer, (self.DIFF_EQUAL, insertion[:overlap_length1]))
                        diffs[pointer - 1] = (self.DIFF_DELETE, deletion[:len(deletion) - overlap_length1])
                        diffs[pointer + 1] = (self.DIFF_INSERT, insertion[overlap_length1:])
                        pointer += 1
                else:
                    if (overlap_length2 >= len(deletion) / 2.0 or
                            overlap_length2 >= len(insertion) / 2.0):
                        # Reverse overlap found.
                        # Insert an equality and swap and trim the surrounding edits.
                        diffs.insert(pointer, (self.DIFF_EQUAL, deletion[:overlap_length2]))
                        diffs[pointer - 1] = (self.DIFF_INSERT, insertion[:len(insertion) - overlap_length2])
                        diffs[pointer + 1] = (self.DIFF_DELETE, deletion[overlap_length2:])
                        pointer += 1
                pointer += 1
            pointer += 1

    def diff_cleanupSemanticLossless(self, diffs):
        """Look for single edits surrounded on both sides by equalities
        which can be shifted sideways to align the edit to a word boundary.
        e.g: The c<ins>at c</ins>ame. -> The <ins>cat </ins>came.

        Args:
            diffs: Array of diff tuples.
        """

        def diff_cleanupSemanticScore(one, two):
            """Given two strings, compute a score representing whether the
            internal boundary falls on logical boundaries.
            Scores range from 6 (best) to 0 (worst).
            Closure, but does not reference any external variables.

            Args:
                one: First string.
                two: Second string.

            Returns:
                The score.
            """
            if not one or not two:
                # Edges are the best.
                return 6

            # Each port of this function behaves slightly differently due to
            # subtle differences in each language's definition of things like
            # 'whitespace'.  Since this function's purpose is largely cosmetic,
            # the choice has been made to use each language's native features
            # rather than force total conformity.
            char1 = one[-1]
            char2 = two[0]
            nonAlphaNumeric1 = not char1.isalnum()
            nonAlphaNumeric2 = not char2.isalnum()
            whitespace1 = nonAlphaNumeric1 and char1.isspace()
            whitespace2 = nonAlphaNumeric2 and char2.isspace()
            lineBreak1 = whitespace1 and (char1 == "\r" or char1 == "\n")
            lineBreak2 = whitespace2 and (char2 == "\r" or char2 == "\n")
            blankLine1 = lineBreak1 and self.BLANKLINEEND.search(one)
            blankLine2 = lineBreak2 and self.BLANKLINESTART.match(two)

            if blankLine1 or blankLine2:
                # Five points for blank lines.
                return 5
            elif lineBreak1 or lineBreak2:
                # Four points for line breaks.
                return 4
            elif nonAlphaNumeric1 and not whitespace1 and whitespace2:
                # Three points for end of sentences.
                return 3
            elif whitespace1 or whitespace2:
                # Two points for whitespace.
                return 2
            elif nonAlphaNumeric1 or nonAlphaNumeric2:
                # One point for non-alphanumeric.
                return 1
            return 0

        pointer = 1
        # Intentionally ignore the first and last element (don't need checking).
        while pointer < len(diffs) - 1:
            if (diffs[pointer - 1][0] == self.DIFF_EQUAL and
                    diffs[pointer + 1][0] == self.DIFF_EQUAL):
                # This is a single edit surrounded by equalities.
                equality1 = diffs[pointer - 1][1]
                edit = diffs[pointer][1]
                equality2 = diffs[pointer + 1][1]

                # First, shift the edit as far left as possible.
                commonOffset = self.diff_commonSuffix(equality1, edit)
                if commonOffset:
                    commonString = edit[-commonOffset:]
                    equality1 = equality1[:-commonOffset]
                    edit = commonString + edit[:-commonOffset]
                    equality2 = commonString + equality2

                # Second, step character by character right, looking for the best fit.
                bestEquality1 = equality1
                bestEdit = edit
                bestEquality2 = equality2
                bestScore = (diff_cleanupSemanticScore(equality1, edit) +
                             diff_cleanupSemanticScore(edit, equality2))
                while edit and equality2 and edit[0] == equality2[0]:
                    equality1 += edit[0]
                    edit = edit[1:] + equality2[0]
                    equality2 = equality2[1:]
                    score = (diff_cleanupSemanticScore(equality1, edit) +
                             diff_cleanupSemanticScore(edit, equality2))
                    # The >= encourages trailing rather than leading whitespace on edits.
                    if score >= bestScore:
                        bestScore = score
                        bestEquality1 = equality1
                        bestEdit = edit
                        bestEquality2 = equality2

                if diffs[pointer - 1][1] != bestEquality1:
                    # We have an improvement, save it back to the diff.
                    if bestEquality1:
                        diffs[pointer - 1] = (diffs[pointer - 1][0], bestEquality1)
                    else:
                        del diffs[pointer - 1]
                        pointer -= 1
                    diffs[pointer] = (diffs[pointer][0], bestEdit)
                    if bestEquality2:
                        diffs[pointer + 1] = (diffs[pointer + 1][0], bestEquality2)
                    else:
                        del diffs[pointer + 1]
                        pointer -= 1
            pointer += 1

    # Define some regex patterns for matching boundaries.
    BLANKLINEEND = re.compile(r"\n\r?\n$")
    BLANKLINESTART = re.compile(r"^\r?\n\r?\n")

    def diff_cleanupEfficiency(self, diffs):
        """Reduce the number of edits by eliminating operationally trivial
        equalities.

        Args:
            diffs: Array of diff tuples.
        """
        changes = False
        equalities = []  # Stack of indices where equalities are found.
        lastequality = None  # Always equal to diffs[equalities[-1]][1]
        pointer = 0  # Index of current position.
        pre_ins = False  # Is there an insertion operation before the last equality.
        pre_del = False  # Is there a deletion operation before the last equality.
        post_ins = False  # Is there an insertion operation after the last equality.
        post_del = False  # Is there a deletion operation after the last equality.
        while pointer < len(diffs):
            if diffs[pointer][0] == self.DIFF_EQUAL:  # Equality found.
                if (len(diffs[pointer][1]) < self.Diff_EditCost and
                        (post_ins or post_del)):
                    # Candidate found.
                    equalities.append(pointer)
                    pre_ins = post_ins
                    pre_del = post_del
                    lastequality = diffs[pointer][1]
                else:
                    # Not a candidate, and can never become one.
                    equalities = []
                    lastequality = None

                post_ins = post_del = False
            else:  # An insertion or deletion.
                if diffs[pointer][0] == self.DIFF_DELETE:
                    post_del = True
                else:
                    post_ins = True

                # Five types to be split:
                # <ins>A</ins><del>B</del>XY<ins>C</ins><del>D</del>
                # <ins>A</ins>X<ins>C</ins><del>D</del>
                # <ins>A</ins><del>B</del>X<ins>C</ins>
                # <ins>A</del>X<ins>C</ins><del>D</del>
                # <ins>A</ins><del>B</del>X<del>C</del>

                if lastequality and ((pre_ins and pre_del and post_ins and post_del) or
                                    ((len(lastequality) < self.Diff_EditCost / 2) and
                                     (pre_ins + pre_del + post_ins + post_del) == 3)):
                    # Duplicate record.
                    diffs.insert(equalities[-1], (self.DIFF_DELETE, lastequality))
                    # Change second copy to insert.
                    diffs[equalities[-1] + 1] = (self.DIFF_INSERT, diffs[equalities[-1] + 1][1])
                    equalities.pop()  # Throw away the equality we just deleted.
                    lastequality = None
                    if pre_ins and pre_del:
                        # No changes made which could affect previous entry, keep going.
                        post_ins = post_del = True
                        equalities = []
                    else:
                        if len(equalities):
                            equalities.pop()  # Throw away the previous equality.
                        if len(equalities):
                            pointer = equalities[-1]
                        else:
                            pointer = -1
                        post_ins = post_del = False
                    changes = True
            pointer += 1

        if changes:
            self.diff_cleanupMerge(diffs)

    def diff_cleanupMerge(self, diffs):
        """Reorder and merge like edit sections.  Merge equalities.
        Any edit section can move as long as it doesn't cross an equality.

        Args:
            diffs: Array of diff tuples.
        """
        diffs.append((self.DIFF_EQUAL, ''))  # Add a dummy entry at the end.
        pointer = 0
        count_delete = 0
        count_insert = 0
        text_delete = ''
        text_insert = ''
        while pointer < len(diffs):
            if diffs[pointer][0] == self.DIFF_INSERT:
                count_insert += 1
                text_insert += diffs[pointer][1]
                pointer += 1
            elif diffs[pointer][0] == self.DIFF_DELETE:
                count_delete += 1
                text_delete += diffs[pointer][1]
                pointer += 1
            elif diffs[pointer][0] == self.DIFF_EQUAL:
                # Upon reaching an equality, check for prior redundancies.
                if count_delete + count_insert > 1:
                    if count_delete != 0 and count_insert != 0:
                        # Factor out any common prefixies.
                        commonlength = self.diff_commonPrefix(text_insert, text_delete)
                        if commonlength != 0:
                            x = pointer - count_delete - count_insert - 1
                            if x >= 0 and diffs[x][0] == self.DIFF_EQUAL:
                                diffs[x] = (diffs[x][0], diffs[x][1] +
                                            text_insert[:commonlength])
                            else:
                                diffs.insert(0, (self.DIFF_EQUAL, text_insert[:commonlength]))
                                pointer += 1
                            text_insert = text_insert[commonlength:]
                            text_delete = text_delete[commonlength:]
                        # Factor out any common suffixies.
                        commonlength = self.diff_commonSuffix(text_insert, text_delete)
                        if commonlength != 0:
                            diffs[pointer] = (diffs[pointer][0], text_insert[-commonlength:] +
                                              diffs[pointer][1])
                            text_insert = text_insert[:-commonlength]
                            text_delete = text_delete[:-commonlength]
                    # Delete the offending records and add the merged ones.
                    if count_delete == 0:
                        diffs[(pointer - count_insert):pointer] = [(self.DIFF_INSERT, text_insert)]
                    elif count_insert == 0:
                        diffs[(pointer - count_delete):pointer] = [(self.DIFF_DELETE, text_delete)]
                    else:
                        diffs[(pointer - count_delete - count_insert):pointer] = [
                            (self.DIFF_DELETE, text_delete),
                            (self.DIFF_INSERT, text_insert)]
                    pointer = pointer - count_delete - count_insert + 1
                    if count_delete != 0:
                        pointer += 1
                    if count_insert != 0:
                        pointer += 1
                elif pointer != 0 and diffs[pointer - 1][0] == self.DIFF_EQUAL:
                    # Merge this equality with the previous one.
                    diffs[pointer - 1] = (diffs[pointer - 1][0], diffs[pointer - 1][1] + diffs[pointer][1])
                    del diffs[pointer]
                else:
                    pointer += 1

                count_insert = 0
                count_delete = 0
                text_delete = ''
                text_insert = ''

        if diffs[-1][1] == '':
            diffs.pop()  # Remove the dummy entry at the end.

        # Second pass: look for single edits surrounded on both sides by equalities
        # which can be shifted sideways to eliminate an equality.
        # e.g: A<ins>BA</ins>C -> <ins>AB</ins>AC
        changes = False
        pointer = 1
        # Intentionally ignore the first and last element (don't need checking).
        while pointer < len(diffs) - 1:
            if (diffs[pointer - 1][0] == self.DIFF_EQUAL and
                    diffs[pointer + 1][0] == self.DIFF_EQUAL):
                # This is a single edit surrounded by equalities.
                if diffs[pointer][1].endswith(diffs[pointer - 1][1]):
                    # Shift the edit over the previous equality.
                    diffs[pointer] = (diffs[pointer][0],
                                      diffs[pointer - 1][1] +
                                      diffs[pointer][1][:-len(diffs[pointer - 1][1])])
                    diffs[pointer + 1] = (diffs[pointer + 1][0],
                                          diffs[pointer - 1][1] + diffs[pointer + 1][1])
                    del diffs[pointer - 1]
                    changes = True
                elif diffs[pointer][1].startswith(diffs[pointer + 1][1]):
                    # Shift the edit over the next equality.
                    diffs[pointer - 1] = (diffs[pointer - 1][0],
                                          diffs[pointer - 1][1] + diffs[pointer + 1][1])
                    diffs[pointer] = (diffs[pointer][0],
                                      diffs[pointer][1][len(diffs[pointer + 1][1]):] +
                                      diffs[pointer + 1][1])
                    del diffs[pointer + 1]
                    changes = True
            pointer += 1

        # If shifts were made, the diff needs reordering and another shift sweep.
        if changes:
            self.diff_cleanupMerge(diffs)

    def diff_xIndex(self, diffs, loc):
        """loc is a location in text1, compute and return the equivalent location
        in text2.  e.g. "The cat" vs "The big cat", 1->1, 5->8

        Args:
            diffs: Array of diff tuples.
            loc: Location within text1.

        Returns:
            Location within text2.
        """
        chars1 = 0
        chars2 = 0
        last_chars1 = 0
        last_chars2 = 0
        for x in range(len(diffs)):
            (op, text) = diffs[x]
            if op != self.DIFF_INSERT:  # Equality or deletion.
                chars1 += len(text)
            if op != self.DIFF_DELETE:  # Equality or insertion.
                chars2 += len(text)
            if chars1 > loc:  # Overshot the location.
                break
            last_chars1 = chars1
            last_chars2 = chars2

        if len(diffs) != x and diffs[x][0] == self.DIFF_DELETE:
            # The location was deleted.
            return last_chars2
        # Add the remaining len(character).
        return last_chars2 + (loc - last_chars1)

    def diff_prettyHtml(self, diffs):
        """Convert a diff array into a pretty HTML report.

        Args:
            diffs: Array of diff tuples.

        Returns:
            HTML representation.
        """
        html = []
        for (op, data) in diffs:
            text = (data.replace("&", "&amp;").replace("<", "&lt;")
                    .replace(">", "&gt;").replace("\n", "&para;<br>"))
            if op == self.DIFF_INSERT:
                html.append("<ins style=\"background:#e6ffe6;\">%s</ins>" % text)
            elif op == self.DIFF_DELETE:
                html.append("<del style=\"background:#ffe6e6;\">%s</del>" % text)
            elif op == self.DIFF_EQUAL:
                html.append("<span>%s</span>" % text)
        return "".join(html)

    def diff_text1(self, diffs):
        """Compute and return the source text (all equalities and deletions).

        Args:
            diffs: Array of diff tuples.

        Returns:
            Source text.
        """
        text = []
        for (op, data) in diffs:
            if op != self.DIFF_INSERT:
                text.append(data)
        return "".join(text)

    def diff_text2(self, diffs):
        """Compute and return the destination text (all equalities and insertions).

        Args:
            diffs: Array of diff tuples.

        Returns:
            Destination text.
        """
        text = []
        for (op, data) in diffs:
            if op != self.DIFF_DELETE:
                text.append(data)
        return "".join(text)

    def diff_levenshtein(self, diffs):
        """Compute the Levenshtein distance; the number of inserted, deleted or
        substituted characters.

        Args:
            diffs: Array of diff tuples.

        Returns:
            Number of changes.
        """
        levenshtein = 0
        insertions = 0
        deletions = 0
        for (op, data) in diffs:
            if op == self.DIFF_INSERT:
                insertions += len(data)
            elif op == self.DIFF_DELETE:
                deletions += len(data)
            elif op == self.DIFF_EQUAL:
                # A deletion and an insertion is one substitution.
                levenshtein += max(insertions, deletions)
                insertions = 0
                deletions = 0
        levenshtein += max(insertions, deletions)
        return levenshtein

    def diff_toDelta(self, diffs):
        """Crush the diff into an encoded string which describes the operations
        required to transform text1 into text2.
        E.g. =3\t-2\t+ing  -> Keep 3 chars, delete 2 chars, insert 'ing'.
        Operations are tab-separated.  Inserted text is escaped using %xx notation.

        Args:
            diffs: Array of diff tuples.

        Returns:
            Delta text.
        """
        text = []
        for (op, data) in diffs:
            if op == self.DIFF_INSERT:
                # High ascii will raise UnicodeDecodeError.  Use Unicode instead.
                data = data.encode("utf-8")
                text.append("+" + parse.quote(data, "!~*'();/?:@&=+$,# "))
            elif op == self.DIFF_DELETE:
                text.append("-%d" % len(data))
            elif op == self.DIFF_EQUAL:
                text.append("=%d" % len(data))
        return "\t".join(text)

    def diff_fromDelta(self, text1, delta):
        """Given the original text1, and an encoded string which describes the
        operations required to transform text1 into text2, compute the full diff.

        Args:
            text1: Source string for the diff.
            delta: Delta text.

        Returns:
            Array of diff tuples.

        Raises:
            ValueError: If invalid input.
        """
        if type(delta) == str:
            # Deltas should be composed of a subset of ascii chars, Unicode not
            # required.  If this encode raises UnicodeEncodeError, delta is invalid.
            delta.encode("ascii")
        diffs = []
        pointer = 0  # Cursor in text1
        tokens = delta.split("\t")
        for token in tokens:
            if token == "":
                # Blank tokens are ok (from a trailing \t).
                continue
            # Each token begins with a one character parameter which specifies the
            # operation of this token (delete, insert, equality).
            param = token[1:]
            if token[0] == "+":
                param = unquote(param)
                diffs.append((self.DIFF_INSERT, param))
            elif token[0] == "-" or token[0] == "=":
                try:
                    n = int(param)
                except ValueError:
                    raise ValueError("Invalid number in diff_fromDelta: " + param)
                if n < 0:
                    raise ValueError("Negative number in diff_fromDelta: " + param)
                text = text1[pointer:(pointer + n)]
                pointer += n
                if token[0] == "=":
                    diffs.append((self.DIFF_EQUAL, text))
                else:
                    diffs.append((self.DIFF_DELETE, text))
            else:
                # Anything else is an error.
                raise ValueError("Invalid diff operation in diff_fromDelta: " + token[0])
        if pointer != len(text1):
            raise ValueError(
                "Delta length (%d) does not equal source text length (%d)." %
                (pointer, len(text1)))
        return diffs

    #  MATCH FUNCTIONS

    def match_main(self, text, pattern, loc):
        """Locate the best instance of 'pattern' in 'text' near 'loc'.

        Args:
            text: The text to search.
            pattern: The pattern to search for.
            loc: The location to search around.

        Returns:
            Best match index or -1.
        """
        # Check for null inputs.
        if text is None or pattern is None:
            raise ValueError("Null inputs. (match_main)")

        loc = max(0, min(loc, len(text)))
        if text == pattern:
            # Shortcut (potentially not guaranteed by the algorithm)
            return 0
        elif not text:
            # Nothing to match.
            return -1
        elif text[loc:loc + len(pattern)] == pattern:
            # Perfect match at the perfect spot!  (Includes case of null pattern)
            return loc
        else:
            # Do a fuzzy compare.
            match = self.match_bitap(text, pattern, loc)
            return match

    def match_bitap(self, text, pattern, loc):
        """Locate the best instance of 'pattern' in 'text' near 'loc' using the
        Bitap algorithm.

        Args:
            text: The text to search.
            pattern: The pattern to search for.
            loc: The location to search around.

        Returns:
            Best match index or -1.
        """
        # Python doesn't have a maxint limit, so ignore this check.
        #if self.Match_MaxBits != 0 and len(pattern) > self.Match_MaxBits:
        #  raise ValueError("Pattern too long for this application.")

        # Initialise the alphabet.
        s = self.match_alphabet(pattern)

        def match_bitapScore(e, x):
            """Compute and return the score for a match with e errors and x location.
            Accesses loc and pattern through being a closure.

            Args:
                e: Number of errors in match.
                x: Location of match.

            Returns:
                Overall score for match (0.0 = good, 1.0 = bad).
            """
            accuracy = float(e) / len(pattern)
            proximity = abs(loc - x)
            if not self.Match_Distance:
                # Dodge divide by zero error.
                return proximity and 1.0 or accuracy
            return accuracy + (proximity / float(self.Match_Distance))

        # Highest score beyond which we give up.
        score_threshold = self.Match_Threshold
        # Is there a nearby exact match? (speedup)
        best_loc = text.find(pattern, loc)
        if best_loc != -1:
            score_threshold = min(match_bitapScore(0, best_loc), score_threshold)
            # What about in the other direction? (speedup)
            best_loc = text.rfind(pattern, loc + len(pattern))
            if best_loc != -1:
                score_threshold = min(match_bitapScore(0, best_loc), score_threshold)

        # Initialise the bit arrays.
        matchmask = 1 << (len(pattern) - 1)
        best_loc = -1

        bin_max = len(pattern) + len(text)
        # Empty initialization added to appease pychecker.
        last_rd = None
        for d in range(len(pattern)):
            # Scan for the best match each iteration allows for one more error.
            # Run a binary search to determine how far from 'loc' we can stray at
            # this error level.
            bin_min = 0
            bin_mid = bin_max
            while bin_min < bin_mid:
                if match_bitapScore(d, loc + bin_mid) <= score_threshold:
                    bin_min = bin_mid
                else:
                    bin_max = bin_mid
                bin_mid = (bin_max - bin_min) // 2 + bin_min

            # Use the result from this iteration as the maximum for the next.
            bin_max = bin_mid
            start = max(1, loc - bin_mid + 1)
            finish = min(loc + bin_mid, len(text)) + len(pattern)

            rd = [0] * (finish + 2)
            rd[finish + 1] = (1 << d) - 1
            for j in range(finish, start - 1, -1):
                if len(text) <= j - 1:
                    # Out of range.
                    charMatch = 0
                else:
                    charMatch = s.get(text[j - 1], 0)
                if d == 0:  # First pass: exact match.
                    rd[j] = ((rd[j + 1] << 1) | 1) & charMatch
                else:  # Subsequent passes: fuzzy match.
                    rd[j] = (((rd[j + 1] << 1) | 1) & charMatch) | (
                            ((last_rd[j + 1] | last_rd[j]) << 1) | 1) | last_rd[j + 1]
                if rd[j] & matchmask:
                    score = match_bitapScore(d, j - 1)
                    # This match will almost certainly be better than any existing match.
                    # But check anyway.
                    if score <= score_threshold:
                        # Told you so.
                        score_threshold = score
                        best_loc = j - 1
                        if best_loc > loc:
                            # When passing loc, don't exceed our current distance from loc.
                            start = max(1, 2 * loc - best_loc)
                        else:
                            # Already passed loc, downhill from here on in.
                            break
            # No hope for a (better) match at greater error levels.
            if match_bitapScore(d + 1, loc) > score_threshold:
                break
            last_rd = rd
        return best_loc

    def match_alphabet(self, pattern):
        """Initialise the alphabet for the Bitap algorithm.

        Args:
            pattern: The text to encode.

        Returns:
            Hash of character locations.
        """
        s = {}
        for char in pattern:
            s[char] = 0
        for i in range(len(pattern)):
            s[pattern[i]] |= 1 << (len(pattern) - i - 1)
        return s

    #  PATCH FUNCTIONS

    def patch_addContext(self, patch, text):
        """Increase the context until it is unique,
        but don't let the pattern expand beyond Match_MaxBits.

        Args:
            patch: The patch to grow.
            text: Source text.
        """
        if len(text) == 0:
            return
        pattern = text[patch.start2:(patch.start2 + patch.length1)]
        padding = 0

        # Look for the first and last matches of pattern in text.  If two different
        # matches are found, increase the pattern length.
        while (text.find(pattern) != text.rfind(pattern) and
              (self.Match_MaxBits == 0 or
                len(pattern) < self.Match_MaxBits - self.Patch_Margin -
                self.Patch_Margin)):
            padding += self.Patch_Margin
            pattern = text[max(0, patch.start2 - padding):(patch.start2 + patch.length1 + padding)]
        # Add one chunk for good luck.
        padding += self.Patch_Margin

        # Add the prefix.
        prefix = text[max(0, patch.start2 - padding):patch.start2]
        if prefix:
            patch.diffs[:0] = [(self.DIFF_EQUAL, prefix)]
        # Add the suffix.
        suffix = text[(patch.start2 + patch.length1):(patch.start2 + patch.length1 + padding)]
        if suffix:
            patch.diffs.append((self.DIFF_EQUAL, suffix))

        # Roll back the start points.
        patch.start1 -= len(prefix)
        patch.start2 -= len(prefix)
        # Extend lengths.
        patch.length1 += len(prefix) + len(suffix)
        patch.length2 += len(prefix) + len(suffix)

    def patch_make(self, a, b=None, c=None):
        """Compute a list of patches to turn text1 into text2.
        Use diffs if provided, otherwise compute it ourselves.
        There are four ways to call this function, depending on what data is
        available to the caller:
        Method 1:
        a = text1, b = text2
        Method 2:
        a = diffs
        Method 3 (optimal):
        a = text1, b = diffs
        Method 4 (deprecated, use method 3):
        a = text1, b = text2, c = diffs

        Args:
            a: text1 (methods 1,3,4) or Array of diff tuples for text1 to
                    text2 (method 2).
            b: text2 (methods 1,4) or Array of diff tuples for text1 to
                    text2 (method 3) or undefined (method 2).
            c: Array of diff tuples for text1 to text2 (method 4) or
                    undefined (methods 1,2,3).

        Returns:
            Array of Patch objects.
        """
        text1 = None
        diffs = None
        # Note that texts may arrive as 'str' or 'unicode'.
        if isinstance(a, str_instances) and isinstance(b, str_instances) and c is None:
            # Method 1: text1, text2
            # Compute diffs from text1 and text2.
            text1 = a
            diffs = self.diff_main(text1, b, True)
            if len(diffs) > 2:
                self.diff_cleanupSemantic(diffs)
                self.diff_cleanupEfficiency(diffs)
        elif isinstance(a, list) and b is None and c is None:
            # Method 2: diffs
            # Compute text1 from diffs.
            diffs = a
            text1 = self.diff_text1(diffs)
        elif isinstance(a, str_instances) and isinstance(b, list) and c is None:
            # Method 3: text1, diffs
            text1 = a
            diffs = b
        elif (isinstance(a, str_instances) and isinstance(b, str_instances) and isinstance(c, list)):
            # Method 4: text1, text2, diffs
            # text2 is not used.
            text1 = a
            diffs = c
        else:
            raise ValueError("Unknown call format to patch_make.")

        if not diffs:
            return []  # Get rid of the None case.
        patches = []
        patch = patch_obj()
        char_count1 = 0  # Number of characters into the text1 string.
        char_count2 = 0  # Number of characters into the text2 string.
        prepatch_text = text1  # Recreate the patches to determine context info.
        postpatch_text = text1
        for x in range(len(diffs)):
            (diff_type, diff_text) = diffs[x]
            if len(patch.diffs) == 0 and diff_type != self.DIFF_EQUAL:
                # A new patch starts here.
                patch.start1 = char_count1
                patch.start2 = char_count2
            if diff_type == self.DIFF_INSERT:
                # Insertion
                patch.diffs.append(diffs[x])
                patch.length2 += len(diff_text)
                postpatch_text = (postpatch_text[:char_count2] + diff_text +
                                  postpatch_text[char_count2:])
            elif diff_type == self.DIFF_DELETE:
                # Deletion.
                patch.length1 += len(diff_text)
                patch.diffs.append(diffs[x])
                postpatch_text = (postpatch_text[:char_count2] +
                                  postpatch_text[char_count2 + len(diff_text):])
            elif (diff_type == self.DIFF_EQUAL and
                  len(diff_text) <= 2 * self.Patch_Margin and
                  len(patch.diffs) != 0 and len(diffs) != x + 1):
                # Small equality inside a patch.
                patch.diffs.append(diffs[x])
                patch.length1 += len(diff_text)
                patch.length2 += len(diff_text)

            if (diff_type == self.DIFF_EQUAL and
                    len(diff_text) >= 2 * self.Patch_Margin):
                # Time for a new patch.
                if len(patch.diffs) != 0:
                    self.patch_addContext(patch, prepatch_text)
                    patches.append(patch)
                    patch = patch_obj()
                    # Unlike Unidiff, our patch lists have a rolling context.
                    # http://code.google.com/p/google-diff-match-patch/wiki/Unidiff
                    # Update prepatch text & pos to reflect the application of the
                    # just completed patch.
                    prepatch_text = postpatch_text
                    char_count1 = char_count2

            # Update the current character count.
            if diff_type != self.DIFF_INSERT:
                char_count1 += len(diff_text)
            if diff_type != self.DIFF_DELETE:
                char_count2 += len(diff_text)

        # Pick up the leftover patch if not empty.
        if len(patch.diffs) != 0:
            self.patch_addContext(patch, prepatch_text)
            patches.append(patch)
        return patches

    def patch_deepCopy(self, patches):
        """Given an array of patches, return another array that is identical.

        Args:
            patches: Array of Patch objects.

        Returns:
            Array of Patch objects.
        """
        patchesCopy = []
        for patch in patches:
            patchCopy = patch_obj()
            # No need to deep copy the tuples since they are immutable.
            patchCopy.diffs = patch.diffs[:]
            patchCopy.start1 = patch.start1
            patchCopy.start2 = patch.start2
            patchCopy.length1 = patch.length1
            patchCopy.length2 = patch.length2
            patchesCopy.append(patchCopy)
        return patchesCopy

    def patch_apply(self, patches, text):
        """Merge a set of patches onto the text.  Return a patched text, as well
        as a list of true/false values indicating which patches were applied.

        Args:
            patches: Array of Patch objects.
            text: Old text.

        Returns:
            Two element Array, containing the new text and an array of boolean values.
        """
        if not patches:
            return (text, [])

        # Deep copy the patches so that no changes are made to originals.
        patches = self.patch_deepCopy(patches)

        nullPadding = self.patch_addPadding(patches)
        text = nullPadding + text + nullPadding
        self.patch_splitMax(patches)

        # delta keeps track of the offset between the expected and actual location
        # of the previous patch.  If there are patches expected at positions 10 and
        # 20, but the first patch was found at 12, delta is 2 and the second patch
        # has an effective expected position of 22.
        delta = 0
        results = []
        for patch in patches:
            expected_loc = patch.start2 + delta
            text1 = self.diff_text1(patch.diffs)
            end_loc = -1
            if len(text1) > self.Match_MaxBits:
                # patch_splitMax will only provide an oversized pattern in the case of
                # a monster delete.
                start_loc = self.match_main(text, text1[:self.Match_MaxBits], expected_loc)
                if start_loc != -1:
                    end_loc = self.match_main(text, text1[-self.Match_MaxBits:],
                                              expected_loc + len(text1) - self.Match_MaxBits)
                    if end_loc == -1 or start_loc >= end_loc:
                        # Can't find valid trailing context.  Drop this patch.
                        start_loc = -1
            else:
                start_loc = self.match_main(text, text1, expected_loc)
            if start_loc == -1:
                # No match found.  :(
                results.append(False)
                # Subtract the delta for this failed patch from subsequent patches.
                delta -= patch.length2 - patch.length1
            else:
                # Found a match.  :)
                results.append(True)
                delta = start_loc - expected_loc
                if end_loc == -1:
                    text2 = text[start_loc:(start_loc + len(text1))]
                else:
                    text2 = text[start_loc:(end_loc + self.Match_MaxBits)]
                if text1 == text2:
                    # Perfect match, just shove the replacement text in.
                    text = (text[:start_loc] + self.diff_text2(patch.diffs) +
                            text[start_loc + len(text1):])
                else:
                    # Imperfect match.
                    # Run a diff to get a framework of equivalent indices.
                    diffs = self.diff_main(text1, text2, False)
                    if (len(text1) > self.Match_MaxBits and
                            self.diff_levenshtein(diffs) / float(len(text1)) >
                            self.Patch_DeleteThreshold):
                        # The end points match, but the content is unacceptably bad.
                        results[-1] = False
                    else:
                        self.diff_cleanupSemanticLossless(diffs)
                        index1 = 0
                        for (op, data) in patch.diffs:
                            if op != self.DIFF_EQUAL:
                                index2 = self.diff_xIndex(diffs, index1)
                            if op == self.DIFF_INSERT:  # Insertion
                                text = text[:start_loc + index2] + data + text[start_loc + index2:]
                            elif op == self.DIFF_DELETE:  # Deletion
                                text = text[:start_loc + index2] + text[start_loc + self.diff_xIndex(diffs, index1 + len(data)):]
                            if op != self.DIFF_DELETE:
                                index1 += len(data)
        # Strip the padding off.
        text = text[len(nullPadding):-len(nullPadding)]
        return (text, results)

    def patch_addPadding(self, patches):
        """Add some padding on text start and end so that edges can match
        something.  Intended to be called only from within patch_apply.

        Args:
            patches: Array of Patch objects.

        Returns:
            The padding string added to each side.
        """
        paddingLength = self.Patch_Margin
        nullPadding = ""
        for x in range(1, paddingLength + 1):
            nullPadding += unichr(x)

        # Bump all the patches forward.
        for patch in patches:
            patch.start1 += paddingLength
            patch.start2 += paddingLength

        # Add some padding on start of first diff.
        patch = patches[0]
        diffs = patch.diffs
        if not diffs or diffs[0][0] != self.DIFF_EQUAL:
            # Add nullPadding equality.
            diffs.insert(0, (self.DIFF_EQUAL, nullPadding))
            patch.start1 -= paddingLength  # Should be 0.
            patch.start2 -= paddingLength  # Should be 0.
            patch.length1 += paddingLength
            patch.length2 += paddingLength
        elif paddingLength > len(diffs[0][1]):
            # Grow first equality.
            extraLength = paddingLength - len(diffs[0][1])
            newText = nullPadding[len(diffs[0][1]):] + diffs[0][1]
            diffs[0] = (diffs[0][0], newText)
            patch.start1 -= extraLength
            patch.start2 -= extraLength
            patch.length1 += extraLength
            patch.length2 += extraLength

        # Add some padding on end of last diff.
        patch = patches[-1]
        diffs = patch.diffs
        if not diffs or diffs[-1][0] != self.DIFF_EQUAL:
            # Add nullPadding equality.
            diffs.append((self.DIFF_EQUAL, nullPadding))
            patch.length1 += paddingLength
            patch.length2 += paddingLength
        elif paddingLength > len(diffs[-1][1]):
            # Grow last equality.
            extraLength = paddingLength - len(diffs[-1][1])
            newText = diffs[-1][1] + nullPadding[:extraLength]
            diffs[-1] = (diffs[-1][0], newText)
            patch.length1 += extraLength
            patch.length2 += extraLength

        return nullPadding

    def patch_splitMax(self, patches):
        """Look through the patches and break up any which are longer than the
        maximum limit of the match algorithm.
        Intended to be called only from within patch_apply.

        Args:
            patches: Array of Patch objects.
        """
        patch_size = self.Match_MaxBits
        if patch_size == 0:
            # Python has the option of not splitting strings due to its ability
            # to handle integers of arbitrary precision.
            return
        for x in range(len(patches)):
            if patches[x].length1 <= patch_size:
                continue
            bigpatch = patches[x]
            # Remove the big old patch.
            del patches[x]
            x -= 1
            start1 = bigpatch.start1
            start2 = bigpatch.start2
            precontext = ''
            while len(bigpatch.diffs) != 0:
                # Create one of several smaller patches.
                patch = patch_obj()
                empty = True
                patch.start1 = start1 - len(precontext)
                patch.start2 = start2 - len(precontext)
                if precontext:
                    patch.length1 = patch.length2 = len(precontext)
                    patch.diffs.append((self.DIFF_EQUAL, precontext))

                while (len(bigpatch.diffs) != 0 and
                       patch.length1 < patch_size - self.Patch_Margin):
                    (diff_type, diff_text) = bigpatch.diffs[0]
                    if diff_type == self.DIFF_INSERT:
                        # Insertions are harmless.
                        patch.length2 += len(diff_text)
                        start2 += len(diff_text)
                        patch.diffs.append(bigpatch.diffs.pop(0))
                        empty = False
                    elif (diff_type == self.DIFF_DELETE and len(patch.diffs) == 1 and
                            patch.diffs[0][0] == self.DIFF_EQUAL and
                            len(diff_text) > 2 * patch_size):
                        # This is a large deletion.  Let it pass in one chunk.
                        patch.length1 += len(diff_text)
                        start1 += len(diff_text)
                        empty = False
                        patch.diffs.append((diff_type, diff_text))
                        del bigpatch.diffs[0]
                    else:
                        # Deletion or equality.  Only take as much as we can stomach.
                        diff_text = diff_text[:patch_size - patch.length1 - self.Patch_Margin]
                        patch.length1 += len(diff_text)
                        start1 += len(diff_text)
                        if diff_type == self.DIFF_EQUAL:
                            patch.length2 += len(diff_text)
                            start2 += len(diff_text)
                        else:
                            empty = False

                        patch.diffs.append((diff_type, diff_text))
                        if diff_text == bigpatch.diffs[0][1]:
                            del bigpatch.diffs[0]
                        else:
                            bigpatch.diffs[0] = (bigpatch.diffs[0][0], bigpatch.diffs[0][1][len(diff_text):])

                # Compute the head context for the next patch.
                precontext = self.diff_text2(patch.diffs)
                precontext = precontext[-self.Patch_Margin:]
                # Append the end context for this patch.
                postcontext = self.diff_text1(bigpatch.diffs)[:self.Patch_Margin]
                if postcontext:
                    patch.length1 += len(postcontext)
                    patch.length2 += len(postcontext)
                    if len(patch.diffs) != 0 and patch.diffs[-1][0] == self.DIFF_EQUAL:
                        patch.diffs[-1] = (self.DIFF_EQUAL, patch.diffs[-1][1] + postcontext)
                    else:
                        patch.diffs.append((self.DIFF_EQUAL, postcontext))

                if not empty:
                    x += 1
                    patches.insert(x, patch)

    def patch_toText(self, patches):
        """Take a list of patches and return a textual representation.

        Args:
            patches: Array of Patch objects.

        Returns:
            Text representation of patches.
        """
        text = []
        for patch in patches:
            text.append(str(patch))
        return "".join(text)

    def patch_fromText(self, textline):
        """Parse a textual representation of patches and return a list of patch
        objects.

        Args:
            textline: Text representation of patches.

        Returns:
            Array of Patch objects.

        Raises:
            ValueError: If invalid input.
        """
        patches = []
        if not textline:
            return patches
        text = textline.split('\n')
        while len(text) != 0:
            m = re.match("^@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@$", text[0])
            if not m:
                raise ValueError("Invalid patch string: " + text[0])
            patch = patch_obj()
            patches.append(patch)
            patch.start1 = int(m.group(1))
            if m.group(2) == '':
                patch.start1 -= 1
                patch.length1 = 1
            elif m.group(2) == '0':
                patch.length1 = 0
            else:
                patch.start1 -= 1
                patch.length1 = int(m.group(2))

            patch.start2 = int(m.group(3))
            if m.group(4) == '':
                patch.start2 -= 1
                patch.length2 = 1
            elif m.group(4) == '0':
                patch.length2 = 0
            else:
                patch.start2 -= 1
                patch.length2 = int(m.group(4))

            del text[0]

            while len(text) != 0:
                if text[0]:
                    sign = text[0][0]
                else:
                    sign = ''
                line = unquote(text[0][1:])
                if sign == '+':
                    # Insertion.
                    patch.diffs.append((self.DIFF_INSERT, line))
                elif sign == '-':
                    # Deletion.
                    patch.diffs.append((self.DIFF_DELETE, line))
                elif sign == ' ':
                    # Minor equality.
                    patch.diffs.append((self.DIFF_EQUAL, line))
                elif sign == '@':
                    # Start of next patch.
                    break
                elif sign == '':
                    # Blank line?  Whatever.
                    pass
                else:
                    # WTF?
                    raise ValueError("Invalid patch mode: '%s'\n%s" % (sign, line))
                del text[0]
        return patches


class patch_obj:
    """Class representing one patch operation.
    """

    def __init__(self):
        """Initializes with an empty list of diffs.
        """
        self.diffs = []
        self.start1 = None
        self.start2 = None
        self.length1 = 0
        self.length2 = 0

    def __str__(self):
        """Emmulate GNU diff's format.
        Header: @@ -382,8 +481,9 @@
        Indicies are printed as 1-based, not 0-based.

        Returns:
            The GNU diff string.
        """
        if self.length1 == 0:
            coords1 = str(self.start1) + ",0"
        elif self.length1 == 1:
            coords1 = str(self.start1 + 1)
        else:
            coords1 = str(self.start1 + 1) + "," + str(self.length1)
        if self.length2 == 0:
            coords2 = str(self.start2) + ",0"
        elif self.length2 == 1:
            coords2 = str(self.start2 + 1)
        else:
            coords2 = str(self.start2 + 1) + "," + str(self.length2)
        text = ["@@ -", coords1, " +", coords2, " @@\n"]
        # Escape the body of the patch with %xx notation.
        for (op, data) in self.diffs:
            if op == diff_match_patch.DIFF_INSERT:
                text.append("+")
            elif op == diff_match_patch.DIFF_DELETE:
                text.append("-")
            elif op == diff_match_patch.DIFF_EQUAL:
                text.append(" ")
            # High ascii will raise UnicodeDecodeError.  Use Unicode instead.
            data = data.encode("utf-8")
            text.append(parse.quote(data, "!~*'();/?:@&=+$,# ") + "\n")
        return "".join(text)

########NEW FILE########
__FILENAME__ = dmp_monkey
from .diff_match_patch import diff_match_patch as dmp


def patch_apply(self, patches, text):
    """Merge a set of patches onto the text.  Return a patched text, as well
    as a list of true/false values indicating which patches were applied.

    Args:
      patches: Array of Patch objects.
      text: Old text.

    Returns:
      Two element Array, containing the new text and an array of boolean values.
    """
    if not patches:
        return (text, [], [])

    # Deep copy the patches so that no changes are made to originals.
    patches = self.patch_deepCopy(patches)

    nullPadding = self.patch_addPadding(patches)
    np_len = len(nullPadding)
    text = nullPadding + text + nullPadding
    self.patch_splitMax(patches)

    # delta keeps track of the offset between the expected and actual location
    # of the previous patch.  If there are patches expected at positions 10 and
    # 20, but the first patch was found at 12, delta is 2 and the second patch
    # has an effective expected position of 22.
    delta = 0
    results = []
    positions = []
    for patch in patches:
        position = [3, 0, ""]
        expected_loc = patch.start2 + delta
        text1 = self.diff_text1(patch.diffs)
        end_loc = -1
        if len(text1) > self.Match_MaxBits:
        # patch_splitMax will only provide an oversized pattern in the case of
        # a monster delete.
            start_loc = self.match_main(text, text1[:self.Match_MaxBits],
                                        expected_loc)
            if start_loc != -1:
                end_loc = self.match_main(text, text1[-self.Match_MaxBits:], expected_loc + len(text1) - self.Match_MaxBits)
                if end_loc == -1 or start_loc >= end_loc:
                    # Can't find valid trailing context.  Drop this patch.
                    start_loc = -1
        else:
            start_loc = self.match_main(text, text1, expected_loc)
        if start_loc == -1:
            # No match found.  :(
            results.append(False)
            # Subtract the delta for this failed patch from subsequent patches.
            delta -= patch.length2 - patch.length1
        else:
            # Found a match.  :)
            results.append(True)
            delta = start_loc - expected_loc
            if end_loc == -1:
                text2 = text[start_loc: start_loc + len(text1)]
            else:
                text2 = text[start_loc: end_loc + self.Match_MaxBits]
            if text1 == text2:
                # Perfect match, just shove the replacement text in.
                replacement_str = self.diff_text2(patch.diffs)
                text = (text[:start_loc] + replacement_str + text[start_loc + len(text1):])
                position = [start_loc, len(text1), replacement_str]
            else:
                # Imperfect match.
                # Run a diff to get a framework of equivalent indices.
                diffs = self.diff_main(text1, text2, False)
                if len(text1) > self.Match_MaxBits and self.diff_levenshtein(diffs) / float(len(text1)) > self.Patch_DeleteThreshold:
                    # The end points match, but the content is unacceptably bad.
                    results[-1] = False
                else:
                    self.diff_cleanupSemanticLossless(diffs)
                    index1 = 0
                    delete_len = 0
                    inserted_text = ""
                    for (op, data) in patch.diffs:
                        if op != self.DIFF_EQUAL:
                            index2 = self.diff_xIndex(diffs, index1)
                        if op == self.DIFF_INSERT:  # Insertion
                            text = text[:start_loc + index2] + data + text[start_loc +
                                                                           index2:]
                            inserted_text += data
                        elif op == self.DIFF_DELETE:  # Deletion
                            diff_index = self.diff_xIndex(diffs, index1 + len(data))
                            text = text[:start_loc + index2] + text[start_loc + diff_index:]
                            delete_len += (diff_index - index2)
                        if op != self.DIFF_DELETE:
                            index1 += len(data)
                    position = [start_loc, delete_len, inserted_text]
        text_len = len(text)
        if position[0] < np_len:
            position[1] -= np_len - position[0]
            position[2] = position[2][np_len - position[0]:]
            position[0] = 0
        else:
            position[0] -= np_len

        too_close = (position[0] + len(position[2])) - (text_len - 2 * np_len)
        if too_close > 0:
            position[2] = position[2][:-too_close]

        positions.append(position)
    # Strip the padding off.
    text = text[np_len:-1 * np_len]
    return (text, results, positions)


def monkey_patch():
    dmp.patch_apply = patch_apply

########NEW FILE########
__FILENAME__ = migrations
import os
import json
import errno
from collections import defaultdict

try:
    from . import shared as G
    from . import utils
except (ImportError, ValueError):
    import shared as G
    import utils


def rename_floobits_dir():
    # TODO: one day this can be removed (once all our users have updated)
    old_colab_dir = os.path.realpath(os.path.expanduser(os.path.join('~', '.floobits')))
    if os.path.isdir(old_colab_dir) and not os.path.exists(G.BASE_DIR):
        print('renaming %s to %s' % (old_colab_dir, G.BASE_DIR))
        os.rename(old_colab_dir, G.BASE_DIR)
        os.symlink(G.BASE_DIR, old_colab_dir)


def get_legacy_projects():
    a = ['msgs.floobits.log', 'persistent.json']
    owners = os.listdir(G.COLAB_DIR)
    floorc_json = defaultdict(defaultdict)
    for owner in owners:
        if len(owner) > 0 and owner[0] == '.':
            continue
        if owner in a:
            continue
        workspaces_path = os.path.join(G.COLAB_DIR, owner)
        try:
            workspaces = os.listdir(workspaces_path)
        except OSError:
            continue
        for workspace in workspaces:
            workspace_path = os.path.join(workspaces_path, workspace)
            workspace_path = os.path.realpath(workspace_path)
            try:
                fd = open(os.path.join(workspace_path, '.floo'), 'rb')
                url = json.loads(fd.read())['url']
                fd.close()
            except Exception:
                url = utils.to_workspace_url({
                    'port': 3448, 'secure': True, 'host': 'floobits.com', 'owner': owner, 'workspace': workspace
                })
            floorc_json[owner][workspace] = {
                'path': workspace_path,
                'url': url
            }

    return floorc_json


def migrate_symlinks():
    data = {}
    old_path = os.path.join(G.COLAB_DIR, 'persistent.json')
    if not os.path.exists(old_path):
        return
    old_data = utils.get_persistent_data(old_path)
    data['workspaces'] = get_legacy_projects()
    data['recent_workspaces'] = old_data.get('recent_workspaces')
    utils.update_persistent_data(data)
    try:
        os.unlink(old_path)
        os.unlink(os.path.join(G.COLAB_DIR, 'msgs.floobits.log'))
    except Exception:
        pass


def __load_floorc():
    """try to read settings out of the .floorc file"""
    s = {}
    try:
        fd = open(G.FLOORC_PATH, 'r')
    except IOError as e:
        if e.errno == errno.ENOENT:
            return s
        raise

    default_settings = fd.read().split('\n')
    fd.close()

    for setting in default_settings:
        # TODO: this is horrible
        if len(setting) == 0 or setting[0] == '#':
            continue
        try:
            name, value = setting.split(' ', 1)
        except IndexError:
            continue
        s[name.upper()] = value
    return s


def migrate_floorc():
    s = __load_floorc()
    default_host = s.get('DEFAULT_HOST', G.DEFAULT_HOST)

    floorc_json = {
        'auth': {
            default_host: {}
        }
    }
    for k, v in s.items():
        k = k.lower()
        try:
            v = int(v)
        except Exception:
            pass

        if k in ['username', 'secret', 'api_key']:
            floorc_json['auth'][default_host][k] = v
        else:
            floorc_json[k] = v
    with open(G.FLOORC_JSON_PATH, 'w') as fd:
        fd.write(json.dumps(floorc_json, indent=4, sort_keys=True))

########NEW FILE########
__FILENAME__ = msg
import os
import time

try:
    from . import shared as G
    assert G
    unicode = str
    from .exc_fmt import str_e
    python2 = False
except ImportError:
    python2 = True
    from exc_fmt import str_e
    import shared as G


LOG_LEVELS = {
    'DEBUG': 1,
    'MSG': 2,
    'WARN': 3,
    'ERROR': 4,
}

LOG_LEVEL = LOG_LEVELS['MSG']
LOG_FILE = os.path.join(G.BASE_DIR, 'msgs.floobits.log')


try:
    fd = open(LOG_FILE, 'w')
    fd.close()
except Exception as e:
    pass


def safe_print(msg):
    # Some environments can have trouble printing unicode:
    #    "When print() is not outputting to the terminal (being redirected to
    #    a file, for instance), print() decides that it does not know what
    #    locale to use for that file and so it tries to convert to ASCII instead."
    # See: https://pythonhosted.org/kitchen/unicode-frustrations.html#frustration-3-inconsistent-treatment-of-output
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('utf-8'))


# Overridden by each editor
def editor_log(msg):
    safe_print(msg)


class MSG(object):
    def __init__(self, msg, timestamp=None, username=None, level=LOG_LEVELS['MSG']):
        self.msg = msg
        self.timestamp = timestamp or time.time()
        self.username = username
        self.level = level

    def display(self):
        if self.level < LOG_LEVEL:
            return

        msg = unicode(self)
        if G.LOG_TO_CONSOLE or G.CHAT_VIEW is None:
            # TODO: ridiculously inefficient
            try:
                fd = open(LOG_FILE, 'ab')
                fmsg = msg
                try:
                    fmsg = fmsg.encode('utf-8')
                except Exception:
                    pass
                fd.write(fmsg)
                fd.write(b'\n')
                fd.close()
            except Exception as e:
                safe_print(str_e(e))
            safe_print(msg)
        else:
            editor_log(msg)

    def __str__(self):
        if python2:
            return self.__unicode__().encode('utf-8')
        return self.__unicode__()

    def __unicode__(self):
        if self.username:
            msg = '[{time}] <{user}> {msg}'
        else:
            msg = '[{time}] {msg}'
        try:
            return unicode(msg).format(user=self.username, time=time.ctime(self.timestamp), msg=self.msg)
        except UnicodeEncodeError:
            return unicode(msg).format(user=self.username, time=time.ctime(self.timestamp), msg=self.msg.encode(
                'utf-8'))


def msg_format(message, *args, **kwargs):
    for arg in args:
        try:
            message += unicode(arg)
        except UnicodeEncodeError:
            message += arg
    if kwargs:
        message = message.format(**kwargs)
    return message


def _log(message, level, *args, **kwargs):
    if level >= LOG_LEVEL:
        # TODO: kill MSG class and just format and print the thing right away
        MSG(msg_format(message, *args, **kwargs), level=level).display()


def debug(message, *args, **kwargs):
    _log(message, LOG_LEVELS['DEBUG'], *args, **kwargs)


def log(message, *args, **kwargs):
    _log(message, LOG_LEVELS['MSG'], *args, **kwargs)


def warn(message, *args, **kwargs):
    _log(message, LOG_LEVELS['WARN'], *args, **kwargs)


def error(message, *args, **kwargs):
    _log(message, LOG_LEVELS['ERROR'], *args, **kwargs)

########NEW FILE########
__FILENAME__ = base
try:
    from .. import event_emitter
except (ImportError, ValueError):
    from floo.common import event_emitter


class BaseProtocol(event_emitter.EventEmitter):
    ''' Base FD Interface'''

    def __init__(self, host, port, secure=True):
        super(BaseProtocol, self).__init__()
        self.host = host
        self.port = port
        self.secure = secure

    def __len__(self):
        return 0

    def fileno(self):
        raise NotImplementedError("fileno not implemented.")

    def fd_set(self, readable, writeable, errorable):
        raise NotImplementedError("fd_set not implemented.")

    def cleanup(self):
        raise NotImplementedError("clean up not implemented.")

    def write(self):
        raise NotImplementedError("write not implemented.")

    def read(self):
        raise NotImplementedError("read not implemented.")

    def error(self):
        raise NotImplementedError("error not implemented.")

    def reconnect(self):
        raise NotImplementedError("reconnect not implemented.")

    def stop(self):
        self.cleanup()

    def connect(self, conn=None):
        self.emit("connect", conn)

########NEW FILE########
__FILENAME__ = floo_proto
import sys
import socket
import select
import collections
import json
import errno
import os.path

try:
    import ssl
    assert ssl
except ImportError:
    ssl = False

try:
    from ... import editor
    from .. import api, cert, msg, shared as G, utils
    from ..exc_fmt import str_e
    from . import base, proxy
    assert cert and G and msg and proxy and utils
except (ImportError, ValueError):
    from floo import editor
    from floo.common import api, cert, msg, shared as G, utils
    from floo.common.exc_fmt import str_e
    import base
    import proxy

try:
    connect_errno = (errno.WSAEWOULDBLOCK, errno.WSAEALREADY, errno.WSAEINVAL)
    iscon_errno = errno.WSAEISCONN
    write_again_errno = (errno.EWOULDBLOCK, errno.EAGAIN) + connect_errno
except Exception:
    connect_errno = (errno.EINPROGRESS, errno.EALREADY)
    iscon_errno = errno.EISCONN
    write_again_errno = (errno.EWOULDBLOCK, errno.EAGAIN) + connect_errno


PY2 = sys.version_info < (3, 0)


def sock_debug(*args, **kwargs):
    if G.SOCK_DEBUG:
        msg.log(*args, **kwargs)


class FlooProtocol(base.BaseProtocol):
    ''' Base FD Interface'''
    MAX_RETRIES = 20
    INITIAL_RECONNECT_DELAY = 500

    def __init__(self, host, port, secure=True):
        super(FlooProtocol, self).__init__(host, port, secure)
        self.connected = False
        self._needs_handshake = bool(secure)
        self._sock = None
        self._q = collections.deque()
        self._slice = bytes()
        self._buf_in = bytes()
        self._buf_out = bytes()
        self._reconnect_delay = self.INITIAL_RECONNECT_DELAY
        self._retries = self.MAX_RETRIES
        self._empty_reads = 0
        self._reconnect_timeout = None
        self._cert_path = os.path.join(G.BASE_DIR, 'startssl-ca.pem')

        self._host = host
        self._port = port
        self._secure = secure
        self._proc = None
        self.proxy = False
        # Sublime Text has a busted SSL module on Linux. Spawn a proxy using OS Python.
        if secure and ssl is False:
            self.proxy = True
            self._host = '127.0.0.1'
            self._port = None
            self._secure = False

    def start_proxy(self):
        if G.PROXY_PORT:
            self._port = int(G.PROXY_PORT)
            msg.log('SSL proxy in debug mode: Port is set to %s' % self._port)
            return
        args = ('python', '-m', 'floo.proxy', '--host=%s' % self.host, '--port=%s' % str(self.port), '--ssl=%s' % str(bool(self.secure)))

        self._proc = proxy.ProxyProtocol()
        self._port = self._proc.connect(args)

    def _handle(self, data):
        self._buf_in += data
        while True:
            before, sep, after = self._buf_in.partition(b'\n')
            if not sep:
                return
            try:
                # Node.js sends invalid utf8 even though we're calling write(string, "utf8")
                # Python 2 can figure it out, but python 3 hates it and will die here with some byte sequences
                # Instead of crashing the plugin, we drop the data. Yes, this is horrible.
                before = before.decode('utf-8', 'ignore')
                data = json.loads(before)
            except Exception as e:
                msg.error('Unable to parse json: %s' % str_e(e))
                msg.error('Data: %s' % before)
                # XXXX: THIS LOSES DATA
                self._buf_in = after
                continue

            name = data.get('name')
            try:
                msg.debug('got data ' + (name or 'no name'))
                self.emit('data', name, data)
            except Exception as e:
                api.send_error('Error handling %s event.' % name, str_e(e))
                if name == 'room_info':
                    editor.error_message('Error joining workspace: %s' % str_e(e))
                    self.stop()
            self._buf_in = after

    def _connect(self, attempts=0):
        if attempts > (self.proxy and 500 or 500):
            msg.error('Connection attempt timed out.')
            return self.reconnect()
        if not self._sock:
            msg.debug('_connect: No socket')
            return
        try:
            self._sock.connect((self._host, self._port))
            select.select([self._sock], [self._sock], [], 0)
        except socket.error as e:
            if e.errno == iscon_errno:
                pass
            elif e.errno in connect_errno:
                return utils.set_timeout(self._connect, 20, attempts + 1)
            else:
                msg.error('Error connecting:', e)
                return self.reconnect()
        if self._secure:
            sock_debug('SSL-wrapping socket')
            self._sock = ssl.wrap_socket(self._sock, ca_certs=self._cert_path, cert_reqs=ssl.CERT_REQUIRED, do_handshake_on_connect=False)

        self._q.clear()
        self._buf_out = bytes()
        self._reconnect_delay = self.INITIAL_RECONNECT_DELAY
        self._retries = self.MAX_RETRIES
        self.emit('connect')
        self.connected = True

    def __len__(self):
        return len(self._q)

    def fileno(self):
        return self._sock and self._sock.fileno()

    def fd_set(self, readable, writeable, errorable):
        if not self.connected:
            return

        fileno = self.fileno()
        errorable.append(fileno)

        if self._needs_handshake:
            return writeable.append(fileno)
        elif len(self) > 0 or self._buf_out:
            writeable.append(fileno)

        readable.append(fileno)

    def connect(self, conn=None):
        utils.cancel_timeout(self._reconnect_timeout)
        self._reconnect_timeout = None
        self.cleanup()

        self._empty_selects = 0

        if self.proxy:
            self.start_proxy()

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setblocking(False)
        if self._secure:
            with open(self._cert_path, 'wb') as cert_fd:
                cert_fd.write(cert.CA_CERT.encode('utf-8'))
        conn_msg = 'Connecting to %s:%s' % (self.host, self.port)
        if self.port != self._port or self.host != self._host:
            conn_msg += ' (proxying through %s:%s)' % (self._host, self._port)
        msg.log(conn_msg)
        editor.status_message(conn_msg)
        self._connect()

    def cleanup(self, *args, **kwargs):
        try:
            self._sock.shutdown(2)
        except Exception:
            pass
        try:
            self._sock.close()
        except Exception:
            pass
        try:
            self._proc.cleanup()
        except Exception:
            pass
        self._slice = bytes()
        self._buf_in = bytes()
        self._buf_out = bytes()
        self._sock = None
        self._needs_handshake = self._secure
        self.connected = False
        self._proc = None
        self.emit('cleanup')

    def _do_ssl_handshake(self):
        try:
            sock_debug('Doing SSL handshake')
            self._sock.do_handshake()
        except ssl.SSLError as e:
            sock_debug('Floobits: ssl.SSLError. This is expected sometimes.')
            if e.args[0] in [ssl.SSL_ERROR_WANT_READ, ssl.SSL_ERROR_WANT_WRITE]:
                return False
        except Exception as e:
            msg.error('Error in SSL handshake:', str_e(e))
        else:
            sock_debug('Successful handshake')
            self._needs_handshake = False
            editor.status_message('SSL handshake completed to %s:%s' % (self.host, self.port))
            return True

        self.reconnect()
        return False

    def write(self):
        sock_debug('Socket is writeable')
        if self._needs_handshake and not self._do_ssl_handshake():
            return

        total = 0
        if not self._slice:
            self._slice = self._buf_out[total:total + 65536]
        try:
            while True:
                if total < len(self._buf_out) or self._slice:
                    sent = self._sock.send(self._slice)
                    sock_debug('Sent %s bytes. Last 10 bytes were %s' % (sent, self._slice[-10:]))
                    if not sent:
                        raise IndexError('LOL')
                    total += sent
                    self._slice = self._buf_out[total:total + 65536]
                else:
                    self._buf_out = self._q.popleft().encode('utf-8')
                    total = 0
                    self._slice = self._buf_out[total:total + 65536]
        except IndexError:
            pass
        except socket.error as e:
            if e.errno not in write_again_errno:
                raise
        self._buf_out = self._buf_out[total:]
        sock_debug('Done writing for now')

    def read(self):
        sock_debug('Socket is readable')
        if self._needs_handshake and not self._do_ssl_handshake():
            return
        buf = ''.encode('utf-8')
        while True:
            try:
                d = self._sock.recv(65536)
                if not d:
                    break
                buf += d
            except (AttributeError):
                return self.reconnect()
            except (socket.error, TypeError):
                break

        if buf:
            self._empty_reads = 0
            # sock_debug('read data')
            return self._handle(buf)

        # sock_debug('empty select')
        self._empty_reads += 1
        if self._empty_reads > (2000 / G.TICK_TIME):
            msg.error('No data from sock.recv() {0} times.'.format(self._empty_reads))
            return self.reconnect()

    def error(self):
        raise NotImplementedError('error not implemented.')

    def stop(self):
        self._retries = -1
        utils.cancel_timeout(self._reconnect_timeout)
        self._reconnect_timeout = None
        self.cleanup()
        self.emit('stop')
        msg.log('Disconnected.')

    def reconnect(self):
        if self._reconnect_timeout:
            return
        self.cleanup()
        self._reconnect_delay = min(10000, int(1.5 * self._reconnect_delay))

        if self._retries > 0:
            msg.log('Floobits: Reconnecting in %sms' % self._reconnect_delay)
            self._reconnect_timeout = utils.set_timeout(self.connect, self._reconnect_delay)
        elif self._retries == 0:
            editor.error_message('Floobits Error! Too many reconnect failures. Giving up.')
        self._retries -= 1

    def put(self, item):
        if not item:
            return
        msg.debug('writing %s' % item.get('name', 'NO NAME'))
        self._q.append(json.dumps(item) + '\n')
        qsize = len(self._q)
        msg.debug('%s items in q' % qsize)
        return qsize

########NEW FILE########
__FILENAME__ = no_reconnect
try:
    from .. import api
    from ... import editor
    from ..exc_fmt import str_e
    from ..protocols import floo_proto
except (ImportError, ValueError):
    from floo import editor
    from floo.common import api
    from floo.common.exc_fmt import str_e
    from floo.common.protocols import floo_proto


PORT_BLOCK_MSG = '''The Floobits plugin can't work because outbound traffic on TCP port 3448 is being blocked.

See https://%s/help/network'''


class NoReconnectProto(floo_proto.FlooProtocol):
    def reconnect(self):
        try:
            api.get_workspace(self.host, 'Floobits', 'doesnotexist')
        except Exception as e:
            print(str_e(e))
            editor.error_message('Something went wrong. See https://%s/help/floorc to complete the installation.' % self.host)
        else:
            editor.error_message(PORT_BLOCK_MSG % self.host)
        self.stop()

########NEW FILE########
__FILENAME__ = proxy
import subprocess
import re
import os.path

try:
    import fcntl
except Exception:
    pass

try:
    from .. import event_emitter, msg, shared as G
    assert event_emitter and G and msg
except (ImportError, ValueError):
    from floo.common import event_emitter, msg, shared as G


class ProxyProtocol(event_emitter.EventEmitter):
    ''' Base Proxy Interface'''

    def __init__(self):
        super(ProxyProtocol, self).__init__()
        try:
            from .. import reactor
        except (ImportError, ValueError):
            from floo.common import reactor
        self.reactor = reactor.reactor
        self.cleanup()

    def __len__(self):
        return 0

    def fileno(self):
        return self.fd

    def fd_set(self, readable, writeable, errorable):
        if self.fd:
            readable.append(self.fd)
            errorable.append(self.fd)

    def cleanup(self):
        try:
            self._proc.kill()
        except Exception:
            pass
        self.fd = None
        self._proc = None
        self.buf = [b'']
        try:
            self.reactor._protos.remove(self)
        except Exception:
            pass

    def read(self):
        data = b''
        while True:
            try:
                d = os.read(self.fd, 65535)
                if not d:
                    break
                data += d
            except (IOError, OSError):
                break
        self.buf[0] += data
        if not data:
            return
        while True:
            before, sep, after = self.buf[0].partition(b'\n')
            if not sep:
                break
            self.buf[0] = after
            try:
                msg.debug("Floobits SSL proxy output: %s" % before.decode('utf-8', 'ignore'))
            except Exception:
                pass

    def error(self):
        self.cleanup()

    def reconnect(self):
        self.cleanup()

    def stop(self):
        self.cleanup()

    def connect(self, args):
        msg.debug('Running proxy with args %s in %s' % (args, G.PLUGIN_PATH))
        self._proc = proc = subprocess.Popen(args, cwd=G.PLUGIN_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        line = proc.stdout.readline().decode('utf-8')
        self.fd = proc.stdout.fileno()
        fl = fcntl.fcntl(self.fd, fcntl.F_GETFL)
        fcntl.fcntl(self.fd, fcntl.F_SETFL, fl | os.O_NONBLOCK | os.O_ASYNC)

        msg.log("Read line from Floobits SSL proxy: %s" % line)
        match = re.search('Now listening on <(\d+)>', line)
        if not match:
            raise Exception("Couldn't find port in line from proxy: %s" % line)
        self._port = int(match.group(1))
        self.reactor._protos.append(self)
        return self._port

########NEW FILE########
__FILENAME__ = tcp_server
import socket

try:
    from . import base
    from ..protocols import floo_proto
except (ImportError, ValueError):
    import base
    from floo.common.protocols import floo_proto


class TCPServerProtocol(base.BaseProtocol):
    PROTOCOL = floo_proto.FlooProtocol

    def __init__(self, host, port):
        super(TCPServerProtocol, self).__init__(host, port, False)
        self.host = host
        self.port = port
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((host, port))
        self._sock.listen(1)

    def __len__(self):
        return 0

    def fileno(self):
        return self._sock

    def fd_set(self, readable, writeable, errorable):
        readable.append(self._sock)

    def read(self):
        conn, addr = self._sock.accept()
        conn.setblocking(False)
        self.emit("connect", conn, addr[0], addr[1])

    def sockname(self):
        return self._sock.getsockname()

########NEW FILE########
__FILENAME__ = proxy
# coding: utf-8
import sys

try:
    from . import shared as G, utils, reactor
    from .handlers import base
    from .protocols import floo_proto
except (ImportError, ValueError):
    import msg
    import shared as G
    import reactor
    from handlers import base
    from protocols import floo_proto


# KANS: this should use base, but I want the connection logic from FlooProto (ie, move that shit to base)
class ProxiedProtocol(floo_proto.FlooProtocol):
    ''' Speaks floo proto, but is given the conn and we don't want to reconnect '''
    def _handle(self, data):
        self.proxy(data)


class FlooConn(base.BaseHandler):
    PROTOCOL = ProxiedProtocol

    def __init__(self, server):
        super(ProxyServer, self).__init__()
        self.proxy = server.send  # agent handler (to the backend connection)

    def tick(self):
        pass

    def on_connect(self):
        msg.log("have an conn!")
        self.proto.proxy = self.proxy


class ProxyProtocol(floo_proto.FlooProtocol):
    ''' Speaks floo proto, but is given the conn and we don't want to reconnect '''
    MAX_RETRIES = -1
    INITIAL_RECONNECT_DELAY = 0

    def connect(self, sock=None):
        self.emit('connected')
        self._sock = sock
        self.connected = True

    def reconnect(self):
        msg.error("client connection died")
        sys.exit(1)

    def stop(self):
        self.cleanup()


class ProxyServer(base.BaseHandler):
    PROTOCOL = ProxyProtocol

    def on_connect(self):
        msg.log("have an conn!")
        reactor.reactor.connect(FlooConn(self), G.DEFAULT_HOST, G.DEFAULT_PORT, True)


def main():
    G.__VERSION__ = '0.11'
    G.__PLUGIN_VERSION__ = '1.0'
    utils.reload_settings()

    floo_log_level = 'msg'
    if G.DEBUG:
        floo_log_level = 'debug'
    msg.LOG_LEVEL = msg.LOG_LEVELS.get(floo_log_level.upper(), msg.LOG_LEVELS['MSG'])

    proxy = ProxyServer()
    _, port = reactor.reactor.listen(proxy)

    def on_ready():
        print('Now listening on %s' % port)

    utils.set_timeout(on_ready, 100)
    reactor.reactor.block()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = reactor
import socket
import select

try:
    from . import api, msg
    from .. import editor
    from ..common.exc_fmt import str_e
    from ..common.handlers import tcp_server
    assert msg and tcp_server
except (ImportError, ValueError):
    from floo.common.exc_fmt import str_e
    from floo.common.handlers import tcp_server
    from floo.common import api, msg
    from floo import editor

reactor = None


class _Reactor(object):
    ''' Low level event driver '''
    def __init__(self):
        self._protos = []
        self._handlers = []

    def connect(self, factory, host, port, secure, conn=None):
        proto = factory.build_protocol(host, port, secure)
        self._protos.append(proto)
        proto.connect(conn)
        self._handlers.append(factory)

    def listen(self, factory, host='127.0.0.1', port=0):
        listener_factory = tcp_server.TCPServerHandler(factory, self)
        proto = listener_factory.build_protocol(host, port)
        self._protos.append(proto)
        self._handlers.append(listener_factory)
        return proto.sockname()

    def stop_handler(self, handler):
        try:
            handler.proto.stop()
        except Exception as e:
            msg.warn('Error stopping connection: %s' % str_e(e))
        try:
            self._handlers.remove(handler)
        except Exception:
            pass
        try:
            self._protos.remove(handler.proto)
        except Exception:
            pass
        if hasattr(handler, 'listener_factory'):
            return handler.listener_factory.stop()
        if not self._handlers and not self._protos:
            msg.log('All handlers stopped. Stopping reactor.')
            self.stop()

    def stop(self):
        for _conn in self._protos:
            _conn.stop()

        self._protos = []
        self._handlers = []
        msg.log('Reactor shut down.')
        editor.status_message('Disconnected.')

    def is_ready(self):
        if not self._handlers:
            return False
        for f in self._handlers:
            if not f.is_ready():
                return False
        return True

    def _reconnect(self, fd, *fd_sets):
        for fd_set in fd_sets:
            try:
                fd_set.remove(fd)
            except ValueError:
                pass
        fd.reconnect()

    @api.send_errors
    def tick(self, timeout=0):
        for factory in self._handlers:
            factory.tick()
        self.select(timeout)
        editor.call_timeouts()

    def block(self):
        while True:
            self.tick(.05)

    def select(self, timeout=0):
        if not self._protos:
            return

        readable = []
        writeable = []
        errorable = []
        fd_map = {}

        for fd in self._protos:
            fileno = fd.fileno()
            if not fileno:
                continue
            fd.fd_set(readable, writeable, errorable)
            fd_map[fileno] = fd

        if not readable and not writeable:
            return

        try:
            _in, _out, _except = select.select(readable, writeable, errorable, timeout)
        except (select.error, socket.error, Exception) as e:
            # TODO: with multiple FDs, must call select with just one until we find the error :(
            if len(readable) == 1:
                readable[0].reconnect()
                return msg.error('Error in select(): %s' % str_e(e))
            raise Exception("can't handle more than one fd exception in reactor")

        for fileno in _except:
            fd = fd_map[fileno]
            self._reconnect(fd, _in, _out)

        for fileno in _out:
            fd = fd_map[fileno]
            try:
                fd.write()
            except Exception as e:
                msg.error('Couldn\'t write to socket: %s' % str_e(e))
                return self._reconnect(fd, _in)

        for fileno in _in:
            fd = fd_map[fileno]
            try:
                fd.read()
            except Exception as e:
                msg.error('Couldn\'t read from socket: %s' % str_e(e))
                fd.reconnect()

reactor = _Reactor()

########NEW FILE########
__FILENAME__ = shared
import os

__VERSION__ = ''
__PLUGIN_VERSION__ = ''

# Config settings
AUTH = {}

DEBUG = False
SOCK_DEBUG = False

EXPERT_MODE = False

ALERT_ON_MSG = True
LOG_TO_CONSOLE = False

BASE_DIR = os.path.expanduser(os.path.join('~', 'floobits'))


# Shared globals
DEFAULT_HOST = 'floobits.com'
DEFAULT_PORT = 3448
SECURE = True
ERROR_COUNT = 0
ERRORS_SENT = 0
# Don't spam us with error reports
MAX_ERROR_REPORTS = 3

PROXY_PORT = 0  # Random port
SHARE_DIR = None
COLAB_DIR = ''
PROJECT_PATH = ''
WORKSPACE_WINDOW = None

PERMS = []
FOLLOW_MODE = False
SPLIT_MODE = False

AUTO_GENERATED_ACCOUNT = False
PLUGIN_PATH = None

CHAT_VIEW = None
CHAT_VIEW_PATH = None

TICK_TIME = 100
AGENT = None
IGNORE = None

IGNORE_MODIFIED_EVENTS = False
VIEW_TO_HASH = {}

FLOORC_PATH = os.path.expanduser(os.path.join('~', '.floorc'))
FLOORC_JSON_PATH = os.path.expanduser(os.path.join('~', '.floorc.json'))

########NEW FILE########
__FILENAME__ = utils
import os
import errno
import json
import re
import hashlib
import webbrowser

from functools import wraps

try:
    from urllib.parse import urlparse
    assert urlparse
except ImportError:
    from urlparse import urlparse

try:
    from .. import editor
    from . import shared as G
    from .exc_fmt import str_e
    from . import msg
    from .lib import DMP
    assert G and DMP
except ImportError:
    import editor
    import msg
    from exc_fmt import str_e
    import shared as G
    from lib import DMP


class FlooPatch(object):
    def __init__(self, current, buf):
        self.buf = buf
        self.current = current
        self.previous = buf['buf']
        if buf['encoding'] == 'base64':
            self.md5_before = hashlib.md5(self.previous).hexdigest()
        else:
            try:
                self.md5_before = hashlib.md5(self.previous.encode('utf-8')).hexdigest()
            except Exception:
                # Horrible fallback if for some reason encoding doesn't agree with actual object
                self.md5_before = hashlib.md5(self.previous).hexdigest()

    def __str__(self):
        return '%s - %s' % (self.buf['id'], self.buf['path'])

    def patches(self):
        return DMP.patch_make(self.previous, self.current)

    def to_json(self):
        patches = self.patches()
        if len(patches) == 0:
            return None
        patch_str = ''
        for patch in patches:
            patch_str += str(patch)

        if self.buf['encoding'] == 'base64':
            md5_after = hashlib.md5(self.current).hexdigest()
        else:
            md5_after = hashlib.md5(self.current.encode('utf-8')).hexdigest()

        return {
            'id': self.buf['id'],
            'md5_after': md5_after,
            'md5_before': self.md5_before,
            'path': self.buf['path'],
            'patch': patch_str,
            'name': 'patch'
        }


def reload_settings():
    floorc_settings = load_floorc_json()
    for name, val in floorc_settings.items():
        setattr(G, name, val)
    if G.SHARE_DIR:
        G.BASE_DIR = G.SHARE_DIR
    G.BASE_DIR = os.path.realpath(os.path.expanduser(G.BASE_DIR))
    G.COLAB_DIR = os.path.join(G.BASE_DIR, 'share')
    G.COLAB_DIR = os.path.realpath(G.COLAB_DIR)
    if G.DEBUG:
        msg.LOG_LEVEL = msg.LOG_LEVELS['DEBUG']
    else:
        msg.LOG_LEVEL = msg.LOG_LEVELS['MSG']
    mkdir(G.COLAB_DIR)
    return floorc_settings


def load_floorc_json():
    s = {}
    try:
        with open(G.FLOORC_JSON_PATH, 'r') as fd:
            floorc_json = fd.read()
    except IOError as e:
        if e.errno == errno.ENOENT:
            return s
        raise

    try:
        default_settings = json.loads(floorc_json)
    except ValueError:
        return s

    for k, v in default_settings.items():
        s[k.upper()] = v
    return s


def save_floorc_json(s):
    floorc_json = {}
    for k, v in s.items():
        floorc_json[k.lower()] = v
    msg.log('Writing %s' % floorc_json)
    with open(G.FLOORC_JSON_PATH, 'w') as fd:
        fd.write(json.dumps(floorc_json, indent=4, sort_keys=True))


def can_auth(host=None):
    auth = G.AUTH.get(host or G.DEFAULT_HOST, {})
    can_auth = (auth.get('username') or auth.get('api_key')) and auth.get('secret')
    return can_auth


cancelled_timeouts = set()
timeout_ids = set()


def set_timeout(func, timeout, *args, **kwargs):
    timeout_id = set_timeout._top_timeout_id
    if timeout_id > 100000:
        set_timeout._top_timeout_id = 0
    else:
        set_timeout._top_timeout_id += 1

    try:
        from . import api
    except ImportError:
        import api

    @api.send_errors
    def timeout_func():
        timeout_ids.discard(timeout_id)
        if timeout_id in cancelled_timeouts:
            cancelled_timeouts.remove(timeout_id)
            return
        func(*args, **kwargs)
    editor.set_timeout(timeout_func, timeout)
    timeout_ids.add(timeout_id)
    return timeout_id

set_timeout._top_timeout_id = 0


def cancel_timeout(timeout_id):
    if timeout_id in timeout_ids:
        cancelled_timeouts.add(timeout_id)


def parse_url(workspace_url):
    secure = G.SECURE
    owner = None
    workspace_name = None
    parsed_url = urlparse(workspace_url)
    port = parsed_url.port
    if G.DEBUG and parsed_url.scheme == 'http':
        # Only obey http if we're debugging
        if not port:
            port = 3148
        secure = False

    if not port:
        port = G.DEFAULT_PORT

    result = re.match('^/([-\@\+\.\w]+)/([-\.\w]+)/?$', parsed_url.path)
    if not result:
        # Old style URL
        result = re.match('^/r/([-\@\+\.\w]+)/([-\.\w]+)/?$', parsed_url.path)

    if result:
        (owner, workspace_name) = result.groups()
    else:
        raise ValueError('%s is not a valid Floobits URL' % workspace_url)

    return {
        'host': parsed_url.hostname,
        'owner': owner,
        'port': port,
        'workspace': workspace_name,
        'secure': secure,
    }


def to_workspace_url(r):
    port = int(r.get('port', 3448))
    if r['secure']:
        proto = 'https'
        if port == 3448:
            port = ''
    else:
        proto = 'http'
        if port == 3148:
            port = ''
    if port != '':
        port = ':%s' % port
    host = r.get('host', G.DEFAULT_HOST)
    workspace_url = '%s://%s%s/%s/%s' % (proto, host, port, r['owner'], r['workspace'])
    return workspace_url


def normalize_url(workspace_url):
    return to_workspace_url(parse_url(workspace_url))


def get_full_path(p):
    full_path = os.path.join(G.PROJECT_PATH, p)
    return unfuck_path(full_path)


def unfuck_path(p):
    return os.path.normpath(p)


def to_rel_path(p):
    return os.path.relpath(p, G.PROJECT_PATH).replace(os.sep, '/')


def to_scheme(secure):
    if secure is True:
        return 'https'
    return 'http'


def is_shared(p):
    if not G.AGENT or not G.AGENT.joined_workspace:
        return False
    p = unfuck_path(p)
    try:
        if to_rel_path(p).find('../') == 0:
            return False
    except ValueError:
        return False
    return True


def update_floo_file(path, data):
    try:
        floo_json = json.loads(open(path, 'r').read())
    except Exception:
        pass

    try:
        floo_json.update(data)
    except Exception:
        floo_json = data

    with open(path, 'w') as floo_fd:
        floo_fd.write(json.dumps(floo_json, indent=4, sort_keys=True))


def get_persistent_data(per_path=None):
    per_data = {'recent_workspaces': [], 'workspaces': {}}
    per_path = per_path or os.path.join(G.BASE_DIR, 'persistent.json')
    try:
        per = open(per_path, 'rb')
    except (IOError, OSError):
        msg.debug('Failed to open %s. Recent workspace list will be empty.' % per_path)
        return per_data
    try:
        data = per.read().decode('utf-8')
        persistent_data = json.loads(data)
    except Exception as e:
        msg.debug('Failed to parse %s. Recent workspace list will be empty.' % per_path)
        msg.debug(str_e(e))
        msg.debug(data)
        return per_data
    if 'recent_workspaces' not in persistent_data:
        persistent_data['recent_workspaces'] = []
    if 'workspaces' not in persistent_data:
        persistent_data['workspaces'] = {}
    return persistent_data


def update_persistent_data(data):
    seen = set()
    recent_workspaces = []
    for x in data['recent_workspaces']:
        try:
            if x['url'] in seen:
                continue
            seen.add(x['url'])
            recent_workspaces.append(x)
        except Exception as e:
            msg.debug(str_e(e))

    data['recent_workspaces'] = recent_workspaces
    per_path = os.path.join(G.BASE_DIR, 'persistent.json')
    with open(per_path, 'wb') as per:
        per.write(json.dumps(data, indent=2).encode('utf-8'))


# Cleans up URLs in persistent.json
def normalize_persistent_data():
    persistent_data = get_persistent_data()
    for rw in persistent_data['recent_workspaces']:
        rw['url'] = normalize_url(rw['url'])

    for owner, workspaces in persistent_data['workspaces'].items():
        for name, workspace in workspaces.items():
            workspace['url'] = normalize_url(workspace['url'])
            workspace['path'] = unfuck_path(workspace['path'])
    update_persistent_data(persistent_data)


def add_workspace_to_persistent_json(owner, name, url, path):
    d = get_persistent_data()
    workspaces = d['workspaces']
    if owner not in workspaces:
        workspaces[owner] = {}
    workspaces[owner][name] = {'url': url, 'path': path}
    update_persistent_data(d)


def update_recent_workspaces(workspace_url):
    d = get_persistent_data()
    recent_workspaces = d.get('recent_workspaces', [])
    recent_workspaces.insert(0, {'url': workspace_url})
    recent_workspaces = recent_workspaces[:100]
    seen = set()
    new = []
    for r in recent_workspaces:
        string = json.dumps(r)
        if string not in seen:
            new.append(r)
            seen.add(string)
    d['recent_workspaces'] = new
    update_persistent_data(d)


def get_workspace_by_path(path, _filter):
    path = unfuck_path(path)
    for owner, workspaces in get_persistent_data()['workspaces'].items():
        for name, workspace in workspaces.items():
            if unfuck_path(workspace['path']) == path:
                r = _filter(workspace['url'])
                if r:
                    return r


def rm(path):
    """removes path and dirs going up until a OSError"""
    os.remove(path)
    try:
        os.removedirs(os.path.split(path)[0])
    except OSError:
        pass


def mkdir(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            editor.error_message('Cannot create directory {0}.\n{1}'.format(path, str_e(e)))
            raise


def get_line_endings(path):
    try:
        with open(path, 'rb') as fd:
            line = fd.readline()
    except Exception:
        return
    if not line:
        return
    chunk = line[-2:]
    if chunk == "\r\n":
        return "\r\n"
    if chunk[-1:] == "\n":
        return "\n"


def save_buf(buf):
    path = get_full_path(buf['path'])
    mkdir(os.path.split(path)[0])
    if buf['encoding'] == 'utf8':
        newline = get_line_endings(path) or editor.get_line_endings(path)
    try:
        with open(path, 'wb') as fd:
            if buf['encoding'] == 'utf8':
                out = buf['buf']
                if newline != '\n':
                    out = out.split('\n')
                    out = newline.join(out)
                fd.write(out.encode('utf-8'))
            else:
                fd.write(buf['buf'])
    except Exception as e:
        msg.error('Error saving buf: %s' % str_e(e))


def _unwind_generator(gen_expr, cb=None, res=None):
    try:
        while True:
            maybe_func = res
            args = []
            if type(res) == tuple:
                maybe_func = len(res) and res[0]

            if not callable(maybe_func):
                # send only accepts one argument... this is slightly dangerous if
                # we ever just return a tuple of one elemetn
                # TODO: catch no generator
                if type(res) == tuple and len(res) == 1:
                    res = gen_expr.send(res[0])
                else:
                    res = gen_expr.send(res)
                continue

            def f(*args):
                return _unwind_generator(gen_expr, cb, args)
            args = list(res)[1:]
            args.append(f)
            return maybe_func(*args)
        # TODO: probably shouldn't catch StopIteration to return since that can occur by accident...
    except StopIteration:
        pass
    except __StopUnwindingException as e:
        res = e.ret_val
    if cb:
        return cb(res)
    return res


class __StopUnwindingException(BaseException):
    def __init__(self, ret_val):
        self.ret_val = ret_val


def return_value(args):
    raise __StopUnwindingException(args)


def inlined_callbacks(f):
    """ Branching logic in async functions generates a callback nightmare.
    Use this decorator to inline the results.  If you yield a function, it must
    accept a callback as its final argument that it is responsible for firing.

    example usage:
    """
    @wraps(f)
    def wrap(*args, **kwargs):
        return _unwind_generator(f(*args, **kwargs))
    return wrap


def has_browser():
    valid_browsers = [
        "MacOSX",  # Default mac browser.
        "Chrome",
        "Chromium",
        "Firefox",
        "Safari",
        "Opera"
    ]
    for browser in valid_browsers:
        try:
            webbrowser.get(browser)
            return True
        except Exception:
            continue
    return False

########NEW FILE########
__FILENAME__ = editor
import sys
import os

try:
    import sublime
except Exception:
    pass

welcome_text = 'Welcome %s!\n\nYou\'re all set to collaborate. You should check out our docs at https://%s/help/plugins/sublime#usage. \
You must run \'Floobits - Complete Sign Up\' in the command palette before you can sign in to floobits.com.'


def name():
    if sys.version_info < (3, 0):
        py_version = 2
    else:
        py_version = 3
    return 'Sublime Text %s' % py_version


def codename():
    return 'sublime'


def ok_cancel_dialog(dialog):
    return sublime.ok_cancel_dialog(dialog)


def error_message(msg):
    sublime.error_message(msg)


def status_message(msg):
    sublime.status_message(msg)


def platform():
    return sublime.platform()


def set_timeout(f, timeout):
    sublime.set_timeout(f, timeout)


def call_timeouts():
    return


def message_dialog(msg):
    sublime.message_dialog(msg)


def open_file(file):
    win = sublime.active_window()
    if win:
        win.open_file(file)


def get_line_endings(path=None):
    ending = sublime.load_settings('Preferences.sublime-settings').get('default_line_ending')
    if ending == 'system':
        return os.linesep
    if ending == 'windows':
        return '\r\n'
    return '\n'


def select_auth(*args):
    window, auths, cb = args

    if not auths:
        return cb(None)

    auths = dict(auths)
    for k, v in auths.items():
        v['host'] = k

    if len(auths) == 1:
        return cb(auths.values()[0])

    opts = [[h, 'Connect as %s' % a.get('username')] for h, a in auths.items()]
    opts.append(['Cancel'])

    def on_account(index):
        if index < 0 or index >= len(auths):
            # len(hosts) is cancel, appended to opts at end below
            return cb(None)
        host = opts[index][0]
        return cb(auths[host])

    return window.show_quick_panel(opts, on_account)

########NEW FILE########
__FILENAME__ = listener
import hashlib
import sublime_plugin
import collections

try:
    from .common import msg, shared as G, utils
    from .sublime_utils import get_buf, get_text
    assert G and G and utils and msg and get_buf and get_text
except ImportError:
    from common import msg, shared as G, utils
    from sublime_utils import get_buf, get_text


def if_connected(f):
    def wrapped(*args):
        if not G.AGENT or not G.AGENT.is_ready():
            return
        args = list(args)
        args.append(G.AGENT)
        return f(*args)
    return wrapped


def is_view_loaded(view):
    """returns a buf if the view is loaded in sublime and
    the buf is populated by us"""

    if not G.AGENT:
        return
    if not G.AGENT.joined_workspace:
        return
    if view.is_loading():
        return

    buf = get_buf(view)
    if not buf or buf.get('buf') is None:
        return

    return buf


class Listener(sublime_plugin.EventListener):

    def __init__(self, *args, **kwargs):
        sublime_plugin.EventListener.__init__(self, *args, **kwargs)
        self.between_save_events = collections.defaultdict(lambda: [0, ""])
        self.disable_follow_mode_timeout = None

    def name(self, view):
        return view.file_name()

    def on_new(self, view):
        msg.debug('new', self.name(view))

    @if_connected
    def reenable_follow_mode(self, agent):
        agent.temp_disable_follow = False
        self.disable_follow_mode_timeout = None

    @if_connected
    def disable_follow_mode(self, timeout, agent):
        if G.FOLLOW_MODE is True:
            agent.temp_disable_follow = True
        utils.cancel_timeout(self.disable_follow_mode_timeout)
        self.disable_follow_mode_timeout = utils.set_timeout(self.reenable_follow_mode, timeout)

    @if_connected
    def on_clone(self, view, agent):
        msg.debug('Sublime cloned %s' % self.name(view))
        buf = get_buf(view)
        if not buf:
            return
        buf_id = int(buf['id'])
        f = agent.on_clone.get(buf_id)
        if not f:
            return
        del agent.on_clone[buf_id]
        f(buf, view)

    @if_connected
    def on_close(self, view, agent):
        msg.debug('Sublime closed view %s' % self.name(view))

    @if_connected
    def on_load(self, view, agent):
        msg.debug('Sublime loaded %s' % self.name(view))
        buf = get_buf(view)
        if not buf:
            return
        buf_id = int(buf['id'])
        d = agent.on_load.get(buf_id)
        if not d:
            return
        del agent.on_load[buf_id]
        for _, f in d.items():
            f()

    @if_connected
    def on_pre_save(self, view, agent):
        if view.is_scratch():
            return
        p = view.name()
        if view.file_name():
            try:
                p = utils.to_rel_path(view.file_name())
            except ValueError:
                p = view.file_name()
        i = self.between_save_events[view.buffer_id()]
        i[0] += 1
        i[1] = p

    @if_connected
    def on_post_save(self, view, agent):
        view_buf_id = view.buffer_id()

        def cleanup():
            i = self.between_save_events[view_buf_id]
            i[0] -= 1

        if view.is_scratch():
            return

        i = self.between_save_events[view_buf_id]
        if agent.ignored_saves[view_buf_id] > 0:
            agent.ignored_saves[view_buf_id] -= 1
            return cleanup()
        old_name = i[1]

        i = self.between_save_events[view_buf_id]
        if i[0] > 1:
            return cleanup()
        old_name = i[1]

        event = None
        buf = get_buf(view)
        try:
            name = utils.to_rel_path(view.file_name())
        except ValueError:
            name = view.file_name()
        is_shared = utils.is_shared(view.file_name())

        if buf is None:
            if not is_shared:
                return cleanup()
            if G.IGNORE and G.IGNORE.is_ignored(view.file_name(), log=True):
                msg.log('%s is ignored. Not creating buffer.' % view.file_name())
                return cleanup()
            msg.log('Creating new buffer ', name, view.file_name())
            event = {
                'name': 'create_buf',
                'buf': get_text(view),
                'path': name
            }
        elif name != old_name:
            if is_shared:
                msg.log('renamed buffer {0} to {1}'.format(old_name, name))
                event = {
                    'name': 'rename_buf',
                    'id': buf['id'],
                    'path': name
                }
            else:
                msg.log('deleting buffer from shared: {0}'.format(name))
                event = {
                    'name': 'delete_buf',
                    'id': buf['id'],
                }

        if event:
            agent.send(event)
        if is_shared and buf:
            agent.send({'name': 'saved', 'id': buf['id']})

        cleanup()

    @if_connected
    def on_modified(self, view, agent):
        buf = is_view_loaded(view)
        if not buf:
            return

        text = get_text(view)
        if buf['encoding'] != 'utf8':
            return msg.warn('Floobits does not support patching binary files at this time')

        text = text.encode('utf-8')
        view_md5 = hashlib.md5(text).hexdigest()
        if view_md5 == G.VIEW_TO_HASH.get(view.buffer_id()):
            return

        G.VIEW_TO_HASH[view.buffer_id()] = view_md5

        msg.debug('changed view %s buf id %s' % (buf['path'], buf['id']))

        self.disable_follow_mode(2000)
        buf['forced_patch'] = False
        agent.views_changed.append((view, buf))

    @if_connected
    def on_selection_modified(self, view, agent, buf=None):
        buf = is_view_loaded(view)
        if buf:
            agent.selection_changed.append((view, buf, False))

    @if_connected
    def on_activated(self, view, agent):
        buf = get_buf(view)
        if buf:
            msg.debug('activated view %s buf id %s' % (buf['path'], buf['id']))
            self.on_modified(view)
            agent.selection_changed.append((view, buf, False))

    # ST3 calls on_window_command, but not on_post_window_command
    # resurrect when on_post_window_command works.
    # def on_window_command(self, window, command_name, args):
    #     if command_name not in ("show_quick_panel", "show_input_panel"):
    #         return
    #     self.pending_commands += 1
    #     if not G.AGENT:
    #         return
    #     G.AGENT.temp_disable_follow = True

    # def on_post_window_command(self, window, command_name, args):
    #     if command_name not in ("show_quick_panel", "show_input_panel", "show_panel"):
    #         return
    #     self.pending_commands -= 1
    #     if not G.AGENT or self.pending_commands > 0:
    #         return
    #     G.AGENT.temp_disable_follow = False

########NEW FILE########
__FILENAME__ = proxy
# coding: utf-8

from __future__ import print_function

from collections import defaultdict
import json
import optparse
import platform
import sys
import time
import copy

# Monkey patch editor
timeouts = defaultdict(list)
top_timeout_id = 0
cancelled_timeouts = set()
calling_timeouts = False


def name():
    if sys.version_info < (3, 0):
        py_version = 2
    else:
        py_version = 3
    return 'Floozy-%s' % py_version


def ok_cancel_dialog(dialog):
    print('Dialog:', dialog)


def error_message(msg):
    print(msg, file=sys.stderr)


def status_message(msg):
    print(msg)


def _platform():
    return platform.platform()


def set_timeout(func, timeout, *args, **kwargs):
    global top_timeout_id
    timeout_id = top_timeout_id
    top_timeout_id + 1
    if top_timeout_id > 100000:
        top_timeout_id = 0

    def timeout_func():
        if timeout_id in cancelled_timeouts:
            cancelled_timeouts.remove(timeout_id)
            return
        func(*args, **kwargs)

    then = time.time() + (timeout / 1000.0)
    timeouts[then].append(timeout_func)
    return timeout_id


def cancel_timeout(timeout_id):
    if timeout_id in timeouts:
        cancelled_timeouts.add(timeout_id)


def call_timeouts():
    global calling_timeouts
    if calling_timeouts:
        return
    calling_timeouts = True
    now = time.time()
    for t, tos in copy.copy(timeouts).items():
        if now >= t:
            for timeout in tos:
                timeout()
            del timeouts[t]
    calling_timeouts = False


def open_file(file):
    pass

try:
    from .common import api, msg, shared as G, utils, reactor, event_emitter
    from .common.handlers import base
    from .common.protocols import floo_proto
    from . import editor
except (ImportError, ValueError):
    from common import api, msg, shared as G, utils, reactor, event_emitter
    from common.handlers import base
    from common.protocols import floo_proto
    import editor


def editor_log(msg):
    print(msg)
    sys.stdout.flush()

editor.name = name
editor.ok_cancel_dialog = ok_cancel_dialog
editor.error_message = error_message
editor.status_message = status_message
editor.platform = _platform
editor.set_timeout = set_timeout
editor.cancel_timeout = cancel_timeout
editor.call_timeouts = call_timeouts
editor.open_file = open_file
msg.editor_log = editor_log

utils.reload_settings()
eventStream = event_emitter.EventEmitter()


def conn_log(action, item):
    try:
        item = item.decode('utf-8')
    except Exception:
        pass
    if G.SOCK_DEBUG:
        msg.log('%s: %s' % (action, item))
    sys.stdout.flush()

eventStream.on('to_floobits', lambda x: conn_log('to_floobits', x))
eventStream.on('from_floobits', lambda x: conn_log('from_floobits', x))


# KANS: this should use base, but I want the connection logic from FlooProto (ie, move that shit to base)
class RemoteProtocol(floo_proto.FlooProtocol):
    ''' Speaks floo proto, but is given the conn and we don't want to reconnect '''
    MAX_RETRIES = -1

    def __init__(self, *args, **kwargs):
        super(RemoteProtocol, self).__init__(*args, **kwargs)
        eventStream.on('to_floobits', self._q.append)

    def _handle(self, data):
        # Node.js sends invalid utf8 even though we're calling write(string, "utf8")
        # Python 2 can figure it out, but python 3 hates it and will die here with some byte sequences
        # Instead of crashing the plugin, we drop the data. Yes, this is horrible.
        data = data.decode('utf-8', 'ignore')
        eventStream.emit('from_floobits', data)

    def reconnect(self):
        msg.error('Remote connection died')
        sys.exit(1)


class FlooConn(base.BaseHandler):
    PROTOCOL = RemoteProtocol

    def __init__(self, server):
        super(FlooConn, self).__init__()

    def tick(self):
        pass

    def on_connect(self):
        msg.log('have a remote conn!')
        eventStream.emit('remote_conn')


class LocalProtocol(floo_proto.FlooProtocol):
    ''' Speaks floo proto, but is given the conn and we don't want to reconnect '''
    MAX_RETRIES = -1
    INITIAL_RECONNECT_DELAY = 0

    def __init__(self, *args, **kwargs):
        super(LocalProtocol, self).__init__(*args, **kwargs)
        eventStream.on('from_floobits', self._q.append)
        self.to_proxy = []
        self.remote_conn = False
        eventStream.on('remote_conn', self.on_remote_conn)

    def connect(self, sock=None):
        self.emit('connect')
        self._sock = sock
        self.connected = True

    def reconnect(self):
        msg.error('Client connection died')
        sys.exit(1)

    def stop(self):
        self.cleanup()

    def on_remote_conn(self):
        self.remote_conn = True
        while self.to_proxy:
            item = self.to_proxy.pop(0)
            eventStream.emit('to_floobits', item.decode('utf-8'))

    def _handle(self, data):
        if self.remote_conn:
            eventStream.emit('to_floobits', data.decode('utf-8'))
        else:
            self.to_proxy.append(data)


remote_host = G.DEFAULT_HOST
remote_port = G.DEFAULT_PORT
remote_ssl = True


class Server(base.BaseHandler):
    PROTOCOL = LocalProtocol

    def on_connect(self):
        self.conn = FlooConn(self)
        reactor.reactor.connect(self.conn, remote_host, remote_port, remote_ssl)


try:
    import urllib
    HTTPError = urllib.error.HTTPError
    URLError = urllib.error.URLError
except (AttributeError, ImportError, ValueError):
    import urllib2
    HTTPError = urllib2.HTTPError
    URLError = urllib2.URLError


def main():
    global remote_host, remote_port, remote_ssl
    msg.LOG_LEVEL = msg.LOG_LEVELS['ERROR']

    usage = 'Figure it out :P'
    parser = optparse.OptionParser(usage=usage)
    parser.add_option(
        '--url',
        dest='url',
        default=None
    )
    parser.add_option(
        '--data',
        dest='data',
        default=None
    )
    parser.add_option(
        '--method',
        dest='method',
        default=None
    )
    parser.add_option(
        '--host',
        dest='host',
        default=None
    )
    parser.add_option(
        '--port',
        dest='port',
        default=None
    )
    parser.add_option(
        '--ssl',
        dest='ssl',
        default=None
    )

    options, args = parser.parse_args()

    if options.url:
        data = None
        err = False
        if options.data:
            data = json.loads(options.data)
        try:
            r = api.hit_url(options.host, options.url, data, options.method)
        except HTTPError as e:
            r = e
        except URLError as e:
            r = e
            err = True

        try:
            print(r.code)
        except Exception:
            err = True
        print(r.read().decode('utf-8'))
        sys.exit(err)

    if not options.host:
        sys.exit(1)

    remote_host = options.host
    remote_port = int(options.port) or remote_port
    remote_ssl = bool(options.ssl) or remote_ssl

    proxy = Server()
    _, port = reactor.reactor.listen(proxy, port=int(G.PROXY_PORT))

    def on_ready():
        print('Now listening on <%s>' % port)
        sys.stdout.flush()

    utils.set_timeout(on_ready, 100)

    try:
        reactor.reactor.block()
    except KeyboardInterrupt:
        print('ciao')

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = sublime_connection
import os
import hashlib
import sublime
import collections

try:
    import ssl
    assert ssl
except ImportError:
    ssl = False

try:
    from . import editor
    from .common import msg, shared as G, utils
    from .common.exc_fmt import str_e
    from .view import View
    from .common.handlers import floo_handler
    from .sublime_utils import create_view, get_buf, send_summon, get_view_in_group, get_text
    assert G and msg and utils
except ImportError:
    from floo import editor
    from common import msg, shared as G, utils
    from common.exc_fmt import str_e
    from common.handlers import floo_handler
    from view import View
    from sublime_utils import create_view, get_buf, send_summon, get_view_in_group, get_text


class SublimeConnection(floo_handler.FlooHandler):

    def tick(self):
        reported = set()
        while self.views_changed:
            v, buf = self.views_changed.pop()
            if not self.joined_workspace:
                msg.debug('Not connected. Discarding view change.')
                continue
            if 'patch' not in G.PERMS:
                continue
            if 'buf' not in buf:
                msg.debug('No data for buf %s %s yet. Skipping sending patch' % (buf['id'], buf['path']))
                continue
            view = View(v, buf)
            if view.is_loading():
                msg.debug('View for buf %s is not ready. Ignoring change event' % buf['id'])
                continue
            if view.native_id in reported:
                continue
            reported.add(view.native_id)
            patch = utils.FlooPatch(view.get_text(), buf)
            # Update the current copy of the buffer
            buf['buf'] = patch.current
            buf['md5'] = hashlib.md5(patch.current.encode('utf-8')).hexdigest()
            self.send(patch.to_json())

        reported = set()
        while self.selection_changed:
            v, buf, summon = self.selection_changed.pop()

            if not self.joined_workspace:
                msg.debug('Not connected. Discarding selection change.')
                continue
            # consume highlight events to avoid leak
            if 'highlight' not in G.PERMS:
                continue

            view = View(v, buf)
            vb_id = view.native_id
            if vb_id in reported:
                continue

            reported.add(vb_id)
            highlight_json = {
                'id': buf['id'],
                'name': 'highlight',
                'ranges': view.get_selections(),
                'ping': summon,
                'summon': summon,
                'following': G.FOLLOW_MODE,
            }
            self.send(highlight_json)

        self._status_timeout += 1
        if self._status_timeout > (2000 / G.TICK_TIME):
            self.update_status_msg()

    def update_status_msg(self, status=''):
        self._status_timeout = 0
        if G.FOLLOW_MODE:
            status += 'Following changes in'
        else:
            status += 'Connected to'
        status += ' %s/%s as %s' % (self.owner, self.workspace, self.username)
        editor.status_message(status)

    def stomp_prompt(self, changed_bufs, missing_bufs, new_files, ignored, cb):
        if not G.EXPERT_MODE:
            editor.message_dialog('Your copy of %s/%s is out of sync. '
                                  'You will be prompted after you close this dialog.' % (self.owner, self.workspace))

        def pluralize(arg):
            return arg != 1 and 's' or ''

        overwrite_local = ''
        overwrite_remote = ''
        missing = [buf['path'] for buf in missing_bufs]
        changed = [buf['path'] for buf in changed_bufs]

        to_upload = set(new_files + changed).difference(set(ignored))
        to_remove = missing + ignored
        to_fetch = changed + missing
        to_upload_len = len(to_upload)
        to_remove_len = len(to_remove)
        remote_len = to_remove_len + to_upload_len
        to_fetch_len = len(to_fetch)

        msg.log('To fetch: %s' % ', '.join(to_fetch))
        msg.log('To upload: %s' % ', '.join(to_upload))
        msg.log('To remove: %s' % ', '.join(to_remove))

        if not to_fetch:
            overwrite_local = 'Fetch nothing'
        elif to_fetch_len < 5:
            overwrite_local = 'Fetch %s' % ', '.join(to_fetch)
        else:
            overwrite_local = 'Fetch %s file%s' % (to_fetch_len, pluralize(to_fetch_len))

        if to_upload_len < 5:
            to_upload_str = 'upload %s' % ', '.join(to_upload)
        else:
            to_upload_str = 'upload %s' % to_upload_len

        if to_remove_len < 5:
            to_remove_str = 'remove %s' % ', '.join(to_remove)
        else:
            to_remove_str = 'remove %s' % to_remove_len

        if to_upload:
            overwrite_remote += to_upload_str
            if to_remove:
                overwrite_remote += ' and '
        if to_remove:
            overwrite_remote += to_remove_str

        if remote_len >= 5 and overwrite_remote:
            overwrite_remote += ' files'

        overwrite_remote = overwrite_remote.capitalize()

        action = 'Overwrite'
        # TODO: change action based on numbers of stuff
        opts = [
            ['%s %s remote file%s.' % (action, remote_len, pluralize(remote_len)), overwrite_remote],
            ['%s %s local file%s.' % (action, to_fetch_len, pluralize(to_fetch_len)), overwrite_local],
            ['Cancel', 'Disconnect and resolve conflict manually.'],
        ]
        # TODO: sublime text doesn't let us focus a window. so use the active window. super lame
        # G.WORKSPACE_WINDOW.show_quick_panel(opts, cb)
        w = sublime.active_window() or G.WORKSPACE_WINDOW
        w.show_quick_panel(opts, cb)

    def ok_cancel_dialog(self, msg, cb=None):
        res = sublime.ok_cancel_dialog(msg)
        return (cb and cb(res) or res)

    def error_message(self, msg):
        sublime.error_message(msg)

    def status_message(self, msg):
        sublime.status_message(msg)

    def get_view_text_by_path(self, path):
        for v in G.WORKSPACE_WINDOW.views():
            if not v.file_name():
                continue
            try:
                rel_path = utils.to_rel_path(v.file_name())
            except ValueError:
                continue
            if path == rel_path:
                return get_text(v)

    def get_view(self, buf_id):
        buf = self.bufs.get(buf_id)
        if not buf:
            return

        for v in G.WORKSPACE_WINDOW.views():
            if not v.file_name():
                continue
            try:
                rel_path = utils.to_rel_path(v.file_name())
            except ValueError:
                continue
            if buf['path'] == rel_path:
                return View(v, buf)

    def save_view(self, view):
        self.ignored_saves[view.native_id] += 1
        view.save()

    def reset(self):
        super(self.__class__, self).reset()
        self.on_clone = {}
        self.create_buf_cbs = {}
        self.temp_disable_follow = False
        self.temp_ignore_highlight = {}
        self.temp_ignore_highlight = {}
        self.views_changed = []
        self.selection_changed = []
        self.ignored_saves = collections.defaultdict(int)
        self._status_timeout = 0
        self.last_highlight = None

    def prompt_join_hangout(self, hangout_url):
        hangout_client = None
        users = self.workspace_info.get('users')
        for user_id, user in users.items():
            if user['username'] == self.username and 'hangout' in user['client']:
                hangout_client = user
                break
        if not hangout_client:
            G.WORKSPACE_WINDOW.run_command('floobits_prompt_hangout', {'hangout_url': hangout_url})

    def on_msg(self, data):
        msg.MSG(data.get('data'), data['time'], data['username']).display()

    def get_username_by_id(self, user_id):
        try:
            return self.workspace_info['users'][str(user_id)]['username']
        except Exception:
            return ''

    def delete_buf(self, path, unlink=False):
        if not utils.is_shared(path):
            msg.error('Skipping deleting %s because it is not in shared path %s.' % (path, G.PROJECT_PATH))
            return
        if os.path.isdir(path):
            for dirpath, dirnames, filenames in os.walk(path):
                # TODO: rexamine this assumption
                # Don't care about hidden stuff
                dirnames[:] = [d for d in dirnames if d[0] != '.']
                for f in filenames:
                    f_path = os.path.join(dirpath, f)
                    if f[0] == '.':
                        msg.log('Not deleting buf for hidden file %s' % f_path)
                    else:
                        self.delete_buf(f_path, unlink)
            return
        buf_to_delete = self.get_buf_by_path(path)
        if buf_to_delete is None:
            msg.error('%s is not in this workspace' % path)
            return
        msg.log('deleting buffer ', utils.to_rel_path(path))
        event = {
            'name': 'delete_buf',
            'id': buf_to_delete['id'],
            'unlink': unlink,
        }
        self.send(event)

    def highlight(self, data=None):
        data = data or self.last_highlight
        if not data:
            msg.log('No recent highlight to replay.')
            return
        self._on_highlight(data)

    def _on_highlight(self, data, clone=True):
        self.last_highlight = data
        region_key = 'floobits-highlight-%s' % (data['user_id'])
        buf_id = int(data['id'])
        username = data['username']
        ranges = data['ranges']
        summon = data.get('ping', False)
        msg.debug(str([buf_id, region_key, username, ranges, summon, clone]))
        buf = self.bufs.get(buf_id)
        if not buf:
            return

        # TODO: move this state machine into one variable
        b = self.on_load.get(buf_id)
        if b and b.get('highlight'):
            msg.debug('ignoring command until on_load is complete')
            return
        if buf_id in self.on_clone:
            msg.debug('ignoring command until on_clone is complete')
            return
        if buf_id in self.temp_ignore_highlight:
            msg.debug('ignoring command until temp_ignore_highlight is complete')
            return

        if G.FOLLOW_MODE:
            if self.temp_disable_follow or data.get('following'):
                do_stuff = False
            else:
                do_stuff = True
        else:
            do_stuff = summon

        view = self.get_view(buf_id)
        if not view or view.is_loading():
            if do_stuff:
                msg.debug('creating view')
                create_view(buf)
                self.on_load[buf_id]['highlight'] = lambda: self._on_highlight(data, False)
            return
        view = view.view
        regions = []
        for r in ranges:
            # TODO: add one to the ranges that have a length of zero
            regions.append(sublime.Region(*r))

        def swap_regions(v):
            v.erase_regions(region_key)
            v.add_regions(region_key, regions, region_key, 'dot', sublime.DRAW_OUTLINED)

        if not do_stuff:
            return swap_regions(view)

        win = G.WORKSPACE_WINDOW

        if not G.SPLIT_MODE:
            win.focus_view(view)
            swap_regions(view)
            # Explicit summon by another user. Center the line.
            if summon:
                view.show_at_center(regions[0])
            # Avoid scrolling/jumping lots in follow mode
            else:
                view.show(regions[0])
            return

        focus_group = win.num_groups() - 1
        view_in_group = get_view_in_group(view.buffer_id(), focus_group)

        if view_in_group:
            msg.debug('view in group')
            win.focus_view(view_in_group)
            swap_regions(view_in_group)
            utils.set_timeout(win.focus_group, 0, 0)
            return view_in_group.show(regions[0])

        if not clone:
            msg.debug('no clone... moving ', view.buffer_id(), win.num_groups() - 1, 0)
            win.focus_view(view)
            win.set_view_index(view, win.num_groups() - 1, 0)

            def dont_crash_sublime():
                utils.set_timeout(win.focus_group, 0, 0)
                swap_regions(view)
                return view.show(regions[0])
            return utils.set_timeout(dont_crash_sublime, 0)

        msg.debug('View not in group... cloning')
        win.focus_view(view)

        def on_clone(buf, view):
            msg.debug('on clone')

            def poll_for_move():
                msg.debug('poll_for_move')
                win.focus_view(view)
                win.set_view_index(view, win.num_groups() - 1, 0)
                if not get_view_in_group(view.buffer_id(), focus_group):
                    return utils.set_timeout(poll_for_move, 20)
                msg.debug('found view, now moving ', view.name(), win.num_groups() - 1)
                swap_regions(view)
                view.show(regions[0])
                win.focus_view(view)
                utils.set_timeout(win.focus_group, 0, 0)
                try:
                    del self.temp_ignore_highlight[buf_id]
                except Exception:
                    pass
            utils.set_timeout(win.focus_group, 0, 0)
            poll_for_move()

        self.on_clone[buf_id] = on_clone
        self.temp_ignore_highlight[buf_id] = True
        win.run_command('clone_file')
        return win.focus_group(0)

    def clear_highlights(self, view):
        buf = get_buf(view)
        if not buf:
            return
        msg.debug('clearing highlights in %s, buf id %s' % (buf['path'], buf['id']))
        for user_id, username in self.workspace_info['users'].items():
            view.erase_regions('floobits-highlight-%s' % user_id)

    def summon(self, view):
        buf = get_buf(view)
        if buf:
            msg.debug('summoning selection in view %s, buf id %s' % (buf['path'], buf['id']))
            self.selection_changed.append((view, buf, True))
        else:
            path = view.file_name()
            if not utils.is_shared(path):
                sublime.error_message('Can\'t summon because %s is not in shared path %s.' % (path, G.PROJECT_PATH))
                return
            share = sublime.ok_cancel_dialog('This file isn\'t shared. Would you like to share it?', 'Share')
            if share:
                sel = [[x.a, x.b] for x in view.sel()]
                self.create_buf_cbs[utils.to_rel_path(path)] = lambda buf_id: send_summon(buf_id, sel)
                self.upload(path)

    def _on_delete_buf(self, data):
        # TODO: somehow tell the user about this
        view = self.get_view(data['id'])
        if view:
            try:
                view = view.view
                view.set_scratch(True)
                G.WORKSPACE_WINDOW.focus_view(view)
                G.WORKSPACE_WINDOW.run_command("close_file")
            except Exception as e:
                msg.debug('Error closing view: %s' % str_e(e))
        super(self.__class__, self)._on_delete_buf(data)

    def _on_create_buf(self, data):
        super(self.__class__, self)._on_create_buf(data)
        cb = self.create_buf_cbs.get(data['path'])
        if not cb:
            return
        del self.create_buf_cbs[data['path']]
        try:
            cb(data['id'])
        except Exception as e:
            print(str_e(e))

    def _on_part(self, data):
        super(self.__class__, self)._on_part(data)
        region_key = 'floobits-highlight-%s' % (str(data['user_id']))
        for window in sublime.windows():
            for view in window.views():
                view.erase_regions(region_key)

########NEW FILE########
__FILENAME__ = sublime_utils
import sublime

try:
    from .common import msg, shared as G, utils
    assert G and msg and utils
except (ImportError, ValueError):
    from common import msg, shared as G, utils


def get_text(view):
    return view.substr(sublime.Region(0, view.size()))


def create_view(buf):
    path = utils.get_full_path(buf['path'])
    view = G.WORKSPACE_WINDOW.open_file(path)
    if view:
        msg.debug('Created view', view.name() or view.file_name())
    return view


def get_buf(view):
    if not (G.AGENT and not view.is_scratch() and view.file_name()):
        return
    return G.AGENT.get_buf_by_path(view.file_name())


def send_summon(buf_id, sel):
    highlight_json = {
        'id': buf_id,
        'name': 'highlight',
        'ranges': sel,
        'ping': True,
        'summon': True,
    }
    if G.AGENT and G.AGENT.is_ready():
        G.AGENT.send(highlight_json)


def get_view_in_group(view_buffer_id, group):
    for v in G.WORKSPACE_WINDOW.views_in_group(group):
        if view_buffer_id == v.buffer_id():
            return v

########NEW FILE########
__FILENAME__ = version
PLUGIN_VERSION = '2.8.1'
# The line above is auto-generated by tag_release.py. Do not change it manually.

try:
    from .common import shared as G
    assert G
except ImportError:
    from common import shared as G

G.__VERSION__ = '0.11'
G.__PLUGIN_VERSION__ = PLUGIN_VERSION

########NEW FILE########
__FILENAME__ = view
from datetime import datetime

import sublime

try:
    from .common import msg, shared as G, utils
    from .sublime_utils import get_text
    from .common.exc_fmt import str_e
    assert utils
except (ImportError, ValueError):
    from common import msg, shared as G, utils
    from common.exc_fmt import str_e
    from sublime_utils import get_text


class View(object):
    """editors representation of the buffer"""

    def __init__(self, view, buf):
        self.view = view
        self.buf = buf

    def __repr__(self):
        return '%s %s %s' % (self.native_id, self.buf['id'], self.buf['path'].encode('utf-8'))

    def __str__(self):
        return repr(self)

    @property
    def native_id(self):
        return self.view.buffer_id()

    def is_loading(self):
        return self.view.is_loading()

    def get_text(self):
        return get_text(self.view)

    def apply_patches(self, buf, patches, username):
        regions = []
        commands = []
        for patch in patches[2]:
            offset = patch[0]
            length = patch[1]
            patch_text = patch[2]
            region = sublime.Region(offset, offset + length)
            regions.append(region)
            commands.append({'r': [offset, offset + length], 'data': patch_text})

        self.view.run_command('floo_view_replace_regions', {'commands': commands})
        region_key = 'floobits-patch-' + username
        self.view.add_regions(region_key, regions, 'floobits.patch', 'circle', sublime.DRAW_OUTLINED)
        utils.set_timeout(self.view.erase_regions, 2000, region_key)
        self.set_status('Changed by %s at %s' % (username, datetime.now().strftime('%H:%M')))

    def update(self, buf, message=True):
        self.buf = buf
        if message:
            msg.log('Floobits synced data for consistency: %s' % buf['path'])
        G.VIEW_TO_HASH[self.view.buffer_id()] = buf['md5']
        self.view.set_read_only(False)
        try:
            self.view.run_command('floo_view_replace_region', {'r': [0, self.view.size()], 'data': buf['buf']})
            if message:
                self.set_status('Floobits synced data for consistency.')
            utils.set_timeout(self.set_status, 5000, '')
        except Exception as e:
            msg.error('Exception updating view: %s' % str_e(e))
        if 'patch' not in G.PERMS:
            self.set_status('You don\'t have write permission. Buffer is read-only.')
            self.view.set_read_only(True)

    def set_status(self, status):
        self.view.set_status('Floobits', status)

    def set_read_only(self, ro):
        self.view.set_read_only(ro)

    def focus(self):
        raise NotImplemented()

    def set_cursor_position(self, offset):
        raise NotImplemented()

    def get_cursor_position(self):
        raise NotImplemented()

    def get_cursor_offset(self):
        raise NotImplemented()

    def get_selections(self):
        return [[x.a, x.b] for x in self.view.sel()]

    def clear_highlight(self, user_id):
        raise NotImplemented()

    def highlight(self, ranges, user_id):
        msg.debug('highlighting ranges %s' % (ranges))
        raise NotImplemented()

    def rename(self, name):
        self.view.retarget(name)

    def save(self):
        if 'buf' in self.buf:
            self.view.run_command('save')
        else:
            msg.debug("not saving because not populated")

########NEW FILE########
__FILENAME__ = floobits
# coding: utf-8
import sys
import os
import subprocess
import threading

import sublime

PY2 = sys.version_info < (3, 0)

if PY2 and sublime.platform() == 'windows':
    err_msg = '''Sorry, but the Windows version of Sublime Text 2 lacks Python's select module, so the Floobits plugin won't work.
Please upgrade to Sublime Text 3. :('''
    raise(Exception(err_msg))
elif sublime.platform() == 'osx':
    try:
        p = subprocess.Popen(['/usr/bin/sw_vers', '-productVersion'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result = p.communicate()
        if float(result[0][:4]) < 10.7:
            sublime.error_message('''Sorry, but the Floobits plugin doesn\'t work on 10.6 or earlier.
Please upgrade your operating system if you want to use this plugin. :(''')
    except Exception as e:
        print(e)

try:
    from .window_commands import create_or_link_account
    from .floo import version
    from .floo.listener import Listener
    from .floo.common import migrations, reactor, shared as G, utils
    from .floo.common.exc_fmt import str_e
    assert utils
except (ImportError, ValueError):
    from window_commands import create_or_link_account
    from floo import version
    from floo.listener import Listener
    from floo.common import migrations, reactor, shared as G, utils
    from floo.common.exc_fmt import str_e
assert Listener and version

reactor = reactor.reactor


def global_tick():
    # XXX: A couple of sublime 2 users have had reactor == None here
    reactor.tick()
    utils.set_timeout(global_tick, G.TICK_TIME)


called_plugin_loaded = False


# Sublime 3 calls this once the plugin API is ready
def plugin_loaded():
    global called_plugin_loaded
    if called_plugin_loaded:
        return
    called_plugin_loaded = True
    print('Floobits: Called plugin_loaded.')

    if not os.path.exists(G.FLOORC_JSON_PATH):
        migrations.migrate_floorc()
    utils.reload_settings()

    # TODO: one day this can be removed (once all our users have updated)
    old_colab_dir = os.path.realpath(os.path.expanduser(os.path.join('~', '.floobits')))
    if os.path.isdir(old_colab_dir) and not os.path.exists(G.BASE_DIR):
        print('Renaming %s to %s' % (old_colab_dir, G.BASE_DIR))
        os.rename(old_colab_dir, G.BASE_DIR)
        os.symlink(G.BASE_DIR, old_colab_dir)

    try:
        utils.normalize_persistent_data()
    except Exception as e:
        print('Floobits: Error normalizing persistent data:', str_e(e))
        # Keep on truckin' I guess

    d = utils.get_persistent_data()
    G.AUTO_GENERATED_ACCOUNT = d.get('auto_generated_account', False)

    # Sublime plugin API stuff can't be called right off the bat
    if not utils.can_auth():
        utils.set_timeout(create_or_link_account, 1)

    utils.set_timeout(global_tick, 1)

# Sublime 2 has no way to know when plugin API is ready. Horrible hack here.
if PY2:
    for i in range(0, 20):
        threading.Timer(i, utils.set_timeout, [plugin_loaded, 1]).start()

    def warning():
        if not called_plugin_loaded:
            print('Your computer is slow and could not start the Floobits reactor. Please contact us (support@floobits.com) or upgrade to Sublime Text 3.')
    threading.Timer(20, warning).start()

########NEW FILE########
__FILENAME__ = tag_release
#!/usr/bin/env python

import os
import re
import sys
from distutils.version import StrictVersion


def main():
    if len(sys.argv) != 2:
        print('Usage: %s version' % sys.argv[0])
        versions = os.popen('git tag').read().split('\n')
        versions = [v for v in versions if re.match("\\d\\.\\d\\.\\d", v)]
        versions.sort(key=StrictVersion)
        print(versions[-1])
        sys.exit()

    version = sys.argv[1]

    with open('floo/version.py', 'r') as fd:
        version_py = fd.read().split('\n')

    version_py[0] = "PLUGIN_VERSION = '%s'" % version

    with open('floo/version.py', 'w') as fd:
        fd.write('\n'.join(version_py))

    os.system('git add packages.json floo/version.py')
    os.system('git commit -m "Tag new release: %s"' % version)
    os.system('git tag %s' % version)
    os.system('git push --tags')
    os.system('git push')


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = text_commands
# coding: utf-8
import hashlib

import sublime_plugin
import sublime

try:
    from .floo import sublime_utils as sutils
    from .floo.common import shared as G
    assert G
except (ImportError, ValueError):
    from floo import sublime_utils as sutils
    from floo.common import shared as G


def transform_selections(selections, start, new_offset):
    new_sels = []
    for sel in selections:
        a = sel.a
        b = sel.b
        if sel.a > start:
            a += new_offset
        if sel.b > start:
            b += new_offset
        new_sels.append(sublime.Region(a, b))
    return new_sels


# The new ST3 plugin API sucks
class FlooViewReplaceRegion(sublime_plugin.TextCommand):
    def run(self, edit, *args, **kwargs):
        selections = [x for x in self.view.sel()]  # deep copy
        selections = self._run(edit, selections, *args, **kwargs)
        self.view.sel().clear()
        for sel in selections:
            self.view.sel().add(sel)

    def _run(self, edit, selections, r, data, view=None):
        global ignore_modified_timeout

        if not hasattr(self, 'view'):
            return selections

        G.IGNORE_MODIFIED_EVENTS = True
        start = max(int(r[0]), 0)
        stop = min(int(r[1]), self.view.size())
        region = sublime.Region(start, stop)

        if stop - start > 10000:
            self.view.replace(edit, region, data)
            G.VIEW_TO_HASH[self.view.buffer_id()] = hashlib.md5(sutils.get_text(self.view).encode('utf-8')).hexdigest()
            return transform_selections(selections, stop, 0)

        existing = self.view.substr(region)
        i = 0
        data_len = len(data)
        existing_len = len(existing)
        length = min(data_len, existing_len)
        while (i < length):
            if existing[i] != data[i]:
                break
            i += 1
        j = 0
        while j < (length - i):
            if existing[existing_len - j - 1] != data[data_len - j - 1]:
                break
            j += 1
        region = sublime.Region(start + i, stop - j)
        replace_str = data[i:data_len - j]
        self.view.replace(edit, region, replace_str)
        G.VIEW_TO_HASH[self.view.buffer_id()] = hashlib.md5(sutils.get_text(self.view).encode('utf-8')).hexdigest()
        new_offset = len(replace_str) - ((stop - j) - (start + i))
        return transform_selections(selections, start + i, new_offset)

    def is_visible(self):
        return False

    def is_enabled(self):
        return True

    def description(self):
        return


# The new ST3 plugin API sucks
class FlooViewReplaceRegions(FlooViewReplaceRegion):
    def run(self, edit, commands):
        is_read_only = self.view.is_read_only()
        self.view.set_read_only(False)
        selections = [x for x in self.view.sel()]  # deep copy
        for command in commands:
            selections = self._run(edit, selections, **command)

        self.view.set_read_only(is_read_only)
        self.view.sel().clear()
        for sel in selections:
            self.view.sel().add(sel)

    def is_visible(self):
        return False

    def is_enabled(self):
        return True

    def description(self):
        return

########NEW FILE########
__FILENAME__ = window_commands
# coding: utf-8
import sys
import os
import re
import json
import uuid
import binascii
import subprocess
import webbrowser

import sublime_plugin
import sublime

PY2 = sys.version_info < (3, 0)

try:
    from .floo import editor
    from .floo.sublime_connection import SublimeConnection
    from .floo.common import api, reactor, msg, shared as G, utils
    from .floo.common.exc_fmt import str_e
    from .floo.common.handlers.account import CreateAccountHandler
    from .floo.common.handlers.credentials import RequestCredentialsHandler
    assert api and G and msg and utils
except (ImportError, ValueError):
    from floo import editor
    from floo.common import api, reactor, msg, shared as G, utils
    from floo.common.exc_fmt import str_e
    from floo.common.handlers.account import CreateAccountHandler
    from floo.common.handlers.credentials import RequestCredentialsHandler
    from floo.sublime_connection import SublimeConnection

reactor = reactor.reactor


def disconnect_dialog():
    if G.AGENT and G.AGENT.joined_workspace:
        disconnect = sublime.ok_cancel_dialog('You can only be in one workspace at a time.', 'Leave %s/%s' % (G.AGENT.owner, G.AGENT.workspace))
        if disconnect:
            msg.debug('Stopping agent.')
            reactor.stop()
            G.AGENT = None
        return disconnect
    return True


def link_account(host, cb):
    account = sublime.ok_cancel_dialog('No credentials found in ~/.floorc.json for %s.\n\n'
                                       'Click "Link Account" to open a web browser and add credentials.' % host,
                                       'Link Account')
    if not account:
        return
    token = binascii.b2a_hex(uuid.uuid4().bytes).decode('utf-8')
    agent = RequestCredentialsHandler(token)
    if not agent:
        sublime.error_message('''A configuration error occured earlier. Please go to %s and sign up to use this plugin.\n
We're really sorry. This should never happen.''' % host)
        return

    agent.once('end', cb)

    try:
        reactor.connect(agent, host, G.DEFAULT_PORT, True)
    except Exception as e:
        print(str_e(e))


def create_or_link_account(force=False):
    disable_account_creation = utils.get_persistent_data().get('disable_account_creation')
    if disable_account_creation and not force:
        print('We could not automatically create or link your floobits account. Please go to floobits.com and sign up to use this plugin.')
        return

    opts = [
        ['Use existing Floobits account.', '(opens web page)'],
        ['Create a new Floobits account.', ''],
        ['Cancel', ''],
    ]

    def cb(index):
        if index == 0:
            token = binascii.b2a_hex(uuid.uuid4().bytes).decode('utf-8')
            agent = RequestCredentialsHandler(token)
        elif index == 1:
            agent = CreateAccountHandler()
        else:
            d = utils.get_persistent_data()
            if d.get('disable_account_creation'):
                return
            d['disable_account_creation'] = True
            utils.update_persistent_data(d)
            sublime.message_dialog('''You can set up a Floobits account at any time under\n\nTools -> Floobits -> Setup''')
        try:
            reactor.connect(agent, G.DEFAULT_HOST, G.DEFAULT_PORT, True)
        except Exception as e:
            print(str_e(e))

    def get_workspace_window():
        w = sublime.active_window()
        if w is None:
            return utils.set_timeout(get_workspace_window, 50)
        sublime.message_dialog('Thank you for installing the Floobits plugin!\n\nLet\'s set up your editor to work with Floobits.')
        w.show_quick_panel(opts, cb)
    get_workspace_window()


class FloobitsBaseCommand(sublime_plugin.WindowCommand):
    def is_visible(self):
        return True

    def is_enabled(self):
        return bool(G.AGENT and G.AGENT.is_ready())


class FloobitsOpenSettingsCommand(sublime_plugin.WindowCommand):
    def run(self):
        window = sublime.active_window()
        if window:
            window.open_file(G.FLOORC_PATH)


class FloobitsShareDirCommand(FloobitsBaseCommand):
    def is_enabled(self):
        return not super(FloobitsShareDirCommand, self).is_enabled()

    def run(self, dir_to_share=None, paths=None, current_file=False, api_args=None):
        self.api_args = api_args
        utils.reload_settings()
        if not utils.can_auth():
            return create_or_link_account()
        if paths:
            if len(paths) != 1:
                return sublime.error_message('Only one folder at a time, please. :(')
            return self.on_input(paths[0])
        if dir_to_share is None:
            folders = self.window.folders()
            if folders:
                dir_to_share = folders[0]
            else:
                dir_to_share = os.path.expanduser(os.path.join('~', 'share_me'))
        self.window.show_input_panel('Directory to share:', dir_to_share, self.on_input, None, None)

    @utils.inlined_callbacks
    def on_input(self, dir_to_share):
        file_to_share = None
        dir_to_share = os.path.expanduser(dir_to_share)
        dir_to_share = os.path.realpath(utils.unfuck_path(dir_to_share))
        workspace_name = os.path.basename(dir_to_share)
        workspace_url = None

        # TODO: use prejoin_workspace instead
        def find_workspace(workspace_url):
            r = api.get_workspace_by_url(workspace_url)
            if r.code < 400:
                return r
            try:
                result = utils.parse_url(workspace_url)
                d = utils.get_persistent_data()
                del d['workspaces'][result['owner']][result['name']]
                utils.update_persistent_data(d)
            except Exception as e:
                msg.debug(str_e(e))

        def join_workspace(workspace_url):
            try:
                w = find_workspace(workspace_url)
            except Exception as e:
                sublime.error_message('Error: %s' % str_e(e))
                return False
            if not w:
                return False
            msg.debug('workspace: %s', json.dumps(w.body))
            # if self.api_args:
            anon_perms = w.body.get('perms', {}).get('AnonymousUser', [])
            new_anon_perms = self.api_args.get('perms').get('AnonymousUser', [])
            # TODO: warn user about making a private workspace public
            if set(anon_perms) != set(new_anon_perms):
                msg.debug(str(anon_perms), str(new_anon_perms))
                w.body['perms']['AnonymousUser'] = new_anon_perms
                response = api.update_workspace(workspace_url, w.body)
                msg.debug(str(response.body))
            utils.add_workspace_to_persistent_json(w.body['owner'], w.body['name'], workspace_url, dir_to_share)
            self.window.run_command('floobits_join_workspace', {'workspace_url': workspace_url})
            return True

        if os.path.isfile(dir_to_share):
            file_to_share = dir_to_share
            dir_to_share = os.path.dirname(dir_to_share)

        try:
            utils.mkdir(dir_to_share)
        except Exception:
            sublime.error_message('The directory %s doesn\'t exist and I can\'t create it.' % dir_to_share)
            return

        floo_file = os.path.join(dir_to_share, '.floo')

        info = {}
        try:
            floo_info = open(floo_file, 'r').read()
            info = json.loads(floo_info)
        except (IOError, OSError):
            pass
        except Exception:
            msg.error('Couldn\'t read the floo_info file: %s' % floo_file)

        workspace_url = info.get('url')
        try:
            utils.parse_url(workspace_url)
        except Exception:
            workspace_url = None

        if workspace_url and join_workspace(workspace_url):
            return

        for owner, workspaces in utils.get_persistent_data()['workspaces'].items():
            for name, workspace in workspaces.items():
                if workspace['path'] == dir_to_share:
                    workspace_url = workspace['url']
                    if join_workspace(workspace_url):
                        return

        auth = yield editor.select_auth, self.window, G.AUTH
        if not auth:
            return

        username = auth.get('username')
        host = auth['host']

        def on_done(owner):
            msg.log('Colab dir: %s, Username: %s, Workspace: %s/%s' % (G.COLAB_DIR, username, owner[0], workspace_name))
            self.window.run_command('floobits_create_workspace', {
                'workspace_name': workspace_name,
                'dir_to_share': dir_to_share,
                'upload': file_to_share or dir_to_share,
                'api_args': self.api_args,
                'owner': owner[0],
                'host': host,
            })

        try:
            r = api.get_orgs_can_admin(host)
        except IOError as e:
            sublime.error_message('Error getting org list: %s' % str_e(e))
            return

        if r.code >= 400 or len(r.body) == 0:
            on_done([username])
            return

        orgs = [[org['name'], 'Create workspace owned by %s' % org['name']] for org in r.body]
        orgs.insert(0, [username, 'Create workspace owned by %s' % username])
        self.window.show_quick_panel(orgs, lambda index: index < 0 or on_done(orgs[index]))


class FloobitsCreateWorkspaceCommand(sublime_plugin.WindowCommand):
    def is_visible(self):
        return False

    def is_enabled(self):
        return True

    # TODO: throw workspace_name in api_args
    def run(self, workspace_name=None, dir_to_share=None, prompt='Workspace name:', api_args=None, owner=None, upload=None, host=None):
        if not disconnect_dialog():
            return
        self.owner = owner
        self.dir_to_share = dir_to_share
        self.workspace_name = workspace_name
        self.api_args = api_args or {}
        self.upload = upload
        self.host = host
        if workspace_name and dir_to_share and prompt == 'Workspace name:':
            return self.on_input(workspace_name, dir_to_share)
        self.window.show_input_panel(prompt, workspace_name, self.on_input, None, None)

    def on_input(self, workspace_name, dir_to_share=None):
        if dir_to_share:
            self.dir_to_share = dir_to_share
        if workspace_name == '':
            return self.run(dir_to_share=self.dir_to_share)
        try:
            self.api_args['name'] = workspace_name
            self.api_args['owner'] = self.owner
            msg.debug(str(self.api_args))
            r = api.create_workspace(self.host, self.api_args)
        except Exception as e:
            msg.error('Unable to create workspace: %s' % str_e(e))
            return sublime.error_message('Unable to create workspace: %s' % str_e(e))

        workspace_url = 'https://%s/%s/%s' % (self.host, self.owner, workspace_name)
        msg.log('Created workspace %s' % workspace_url)

        if r.code < 400:
            utils.add_workspace_to_persistent_json(self.owner, workspace_name, workspace_url, self.dir_to_share)
            return self.window.run_command('floobits_join_workspace', {
                'workspace_url': workspace_url,
                'upload': dir_to_share
            })

        msg.error('Unable to create workspace: %s' % r.body)
        if r.code not in [400, 402, 409]:
            try:
                r.body = r.body['detail']
            except Exception:
                pass
            return sublime.error_message('Unable to create workspace: %s' % r.body)

        kwargs = {
            'dir_to_share': self.dir_to_share,
            'workspace_name': workspace_name,
            'api_args': self.api_args,
            'owner': self.owner,
            'upload': self.upload,
            'host': self.host,
        }
        if r.code == 400:
            kwargs['workspace_name'] = re.sub('[^A-Za-z0-9_\-\.]', '-', workspace_name)
            kwargs['prompt'] = 'Invalid name. Workspace names must match the regex [A-Za-z0-9_\-\.]. Choose another name:'
        elif r.code == 402:
            try:
                r.body = r.body['detail']
            except Exception:
                pass
            if sublime.ok_cancel_dialog('%s' % r.body, 'Open billing settings'):
                webbrowser.open('https://%s/%s/settings#billing' % (self.host, self.owner))
            return
        else:
            kwargs['prompt'] = 'Workspace %s/%s already exists. Choose another name:' % (self.owner, workspace_name)

        return self.window.run_command('floobits_create_workspace', kwargs)


class FloobitsPromptJoinWorkspaceCommand(sublime_plugin.WindowCommand):

    def run(self, workspace=G.DEFAULT_HOST):
        for d in self.window.folders():
            floo_file = os.path.join(d, '.floo')
            try:
                floo_info = open(floo_file, 'r').read()
                wurl = json.loads(floo_info).get('url')
                utils.parse_url(wurl)
                # TODO: check if workspace actually exists
                workspace = wurl
                break
            except Exception:
                pass
        self.window.show_input_panel('Workspace URL:', workspace, self.on_input, None, None)

    def on_input(self, workspace_url):
        if disconnect_dialog():
            self.window.run_command('floobits_join_workspace', {
                'workspace_url': workspace_url,
            })


class FloobitsJoinWorkspaceCommand(sublime_plugin.WindowCommand):

    def run(self, workspace_url, agent_conn_kwargs=None, upload=None):
        agent_conn_kwargs = agent_conn_kwargs or {}
        self.upload = upload

        def get_workspace_window():
            workspace_window = None
            for w in sublime.windows():
                for f in w.folders():
                    if utils.unfuck_path(f) == utils.unfuck_path(G.PROJECT_PATH):
                        workspace_window = w
                        break
            return workspace_window

        def set_workspace_window(cb):
            workspace_window = get_workspace_window()
            if workspace_window is None:
                return utils.set_timeout(set_workspace_window, 50, cb)
            G.WORKSPACE_WINDOW = workspace_window
            cb()

        def open_workspace_window(cb):
            if PY2:
                open_workspace_window2(cb)
            else:
                open_workspace_window3(cb)

        def open_workspace_window2(cb):
            if sublime.platform() == 'linux':
                subl = open('/proc/self/cmdline').read().split(chr(0))[0]
            elif sublime.platform() == 'osx':
                floorc = utils.load_floorc_json()
                subl = floorc.get('SUBLIME_EXECUTABLE')
                if not subl:
                    settings = sublime.load_settings('Floobits.sublime-settings')
                    subl = settings.get('sublime_executable', '/Applications/Sublime Text 2.app/Contents/SharedSupport/bin/subl')
                if not os.path.exists(subl):
                    return sublime.error_message('''Can't find your Sublime Text executable at %s.
Please add "sublime_executable /path/to/subl" to your ~/.floorc and restart Sublime Text''' % subl)
            elif sublime.platform() == 'windows':
                subl = sys.executable
            else:
                raise Exception('WHAT PLATFORM ARE WE ON?!?!?')

            command = [subl]
            if get_workspace_window() is None:
                command.append('--new-window')
            command.append('--add')
            command.append(G.PROJECT_PATH)

            msg.debug('command:', command)
            p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            poll_result = p.poll()
            msg.debug('poll:', poll_result)

            set_workspace_window(cb)

        def open_workspace_window3(cb):
            def finish(w):
                G.WORKSPACE_WINDOW = w
                msg.debug('Setting project data. Path: %s' % G.PROJECT_PATH)
                G.WORKSPACE_WINDOW.set_project_data({'folders': [{'path': G.PROJECT_PATH}]})
                cb()

            def get_empty_window():
                for w in sublime.windows():
                    project_data = w.project_data()
                    try:
                        folders = project_data.get('folders', [])
                        if len(folders) == 0 or not folders[0].get('path'):
                            # no project data. co-opt this window
                            return w
                    except Exception as e:
                        print(str_e(e))

            def wait_empty_window(i):
                if i > 10:
                    print('Too many failures trying to find an empty window. Using active window.')
                    return finish(sublime.active_window())
                w = get_empty_window()
                if w:
                    return finish(w)
                return utils.set_timeout(wait_empty_window, 50, i + 1)

            w = get_workspace_window() or get_empty_window()
            if w:
                return finish(w)

            sublime.run_command('new_window')
            wait_empty_window(0)

        def make_dir(d):
            d = os.path.realpath(os.path.expanduser(d))

            if not os.path.isdir(d):
                make_dir = sublime.ok_cancel_dialog('%s is not a directory. Create it?' % d)
                if not make_dir:
                    return self.window.show_input_panel('%s is not a directory. Enter an existing path:' % d, d, None, None, None)
                try:
                    utils.mkdir(d)
                except Exception as e:
                    return sublime.error_message('Could not create directory %s: %s' % (d, str_e(e)))
            G.PROJECT_PATH = d

            if self.upload:
                result['upload'] = d
            else:
                result['upload'] = ""

            utils.add_workspace_to_persistent_json(result['owner'], result['workspace'], workspace_url, d)
            open_workspace_window(lambda: run_agent(**result))

        @utils.inlined_callbacks
        def run_agent(owner, workspace, host, port, secure, upload):
            if G.AGENT:
                msg.debug('Stopping agent.')
                reactor.stop()
                G.AGENT = None
            try:
                auth = G.AUTH.get(host)
                if not auth:
                    success = yield link_account, host
                    if not success:
                        return
                    auth = G.AUTH.get(host)
                conn = SublimeConnection(owner, workspace, auth, upload)
                reactor.connect(conn, host, port, secure)
            except Exception as e:
                msg.error(str_e(e))

        try:
            result = utils.parse_url(workspace_url)
        except Exception as e:
            return sublime.error_message(str_e(e))

        utils.reload_settings()
        if not utils.can_auth():
            return create_or_link_account()

        d = utils.get_persistent_data()
        try:
            G.PROJECT_PATH = d['workspaces'][result['owner']][result['workspace']]['path']
        except Exception:
            msg.log('%s/%s not in persistent.json' % (result['owner'], result['workspace']))
            G.PROJECT_PATH = ''

        msg.log('Project path is %s' % G.PROJECT_PATH)

        if not os.path.isdir(G.PROJECT_PATH):
            default_dir = None
            for w in sublime.windows():
                if default_dir:
                    break
                for d in self.window.folders():
                    floo_file = os.path.join(d, '.floo')
                    try:
                        floo_info = open(floo_file, 'r').read()
                        wurl = json.loads(floo_info).get('url')
                        if wurl == workspace_url:
                            # TODO: check if workspace actually exists
                            default_dir = d
                            break
                    except Exception:
                        pass

            default_dir = default_dir or os.path.realpath(os.path.join(G.COLAB_DIR, result['owner'], result['workspace']))

            return self.window.show_input_panel('Save workspace in directory:', default_dir, make_dir, None, None)

        open_workspace_window(lambda: run_agent(upload=upload, **result))


class FloobitsPinocchioCommand(sublime_plugin.WindowCommand):
    def is_visible(self):
        return self.is_enabled()

    def is_enabled(self):
        return G.AUTO_GENERATED_ACCOUNT

    def run(self):
        floorc = utils.load_floorc_json()
        auth = floorc.get('AUTH', {}).get(G.DEFAULT_HOST, {})
        username = auth.get('username')
        secret = auth.get('secret')
        print(username, secret)
        if not (username and secret):
            return sublime.error_message('You don\'t seem to have a Floobits account of any sort')
        webbrowser.open('https://%s/%s/pinocchio/%s' % (G.DEFAULT_HOST, username, secret))


class FloobitsLeaveWorkspaceCommand(FloobitsBaseCommand):

    def run(self):
        if G.AGENT:
            message = 'You have left the workspace.'
            G.AGENT.update_status_msg(message)
            reactor.stop()
            G.AGENT = None
            # TODO: Mention the name of the thing we left
            if not G.EXPERT_MODE:
                sublime.error_message(message)
        else:
            sublime.error_message('You are not joined to any workspace.')

    def is_enabled(self):
        return bool(G.AGENT)


class FloobitsClearHighlightsCommand(FloobitsBaseCommand):
    def run(self):
        G.AGENT.clear_highlights(self.window.active_view())


class FloobitsSummonCommand(FloobitsBaseCommand):
    # TODO: ghost this option if user doesn't have permissions
    def run(self):
        G.AGENT.summon(self.window.active_view())


class FloobitsJoinRecentWorkspaceCommand(sublime_plugin.WindowCommand):
    def _get_recent_workspaces(self):
        self.recent_workspaces = utils.get_persistent_data()['recent_workspaces']

        try:
            recent_workspaces = [x.get('url') for x in self.recent_workspaces if x.get('url') is not None]
        except Exception:
            pass
        return recent_workspaces

    def run(self, *args):
        workspaces = self._get_recent_workspaces()
        self.window.show_quick_panel(workspaces, self.on_done)

    def on_done(self, item):
        if item == -1:
            return
        workspace = self.recent_workspaces[item]
        if disconnect_dialog():
            self.window.run_command('floobits_join_workspace', {'workspace_url': workspace['url']})

    def is_enabled(self):
        return bool(len(self._get_recent_workspaces()) > 0)


class FloobitsAddToWorkspaceCommand(FloobitsBaseCommand):
    def run(self, paths, current_file=False):
        if not self.is_enabled():
            return

        if paths is None and current_file:
            paths = [self.window.active_view().file_name()]

        notshared = []
        for path in paths:
            if utils.is_shared(path):
                G.AGENT.upload(path)
            else:
                notshared.append(path)

        if notshared:
            limit = 5
            sublime.error_message("The following paths are not a child of\n\n%s\n\nand will not be shared for security reasons:\n\n%s%s." %
                                  (G.PROJECT_PATH, ",\n".join(notshared[:limit]), len(notshared) > limit and ",\n..." or ""))

    def description(self):
        return 'Add file or directory to currently-joined Floobits workspace.'


class FloobitsRemoveFromWorkspaceCommand(FloobitsBaseCommand):
    def run(self, paths, current_file=False):
        if not self.is_enabled():
            return

        unlink = bool(sublime.ok_cancel_dialog('Delete? Hit cancel to remove from the workspace without deleting.', 'Delete'))

        if paths is None and current_file:
            paths = [self.window.active_view().file_name()]

        for path in paths:
            G.AGENT.delete_buf(path, unlink)

    def description(self):
        return 'Add file or directory to currently-joined Floobits workspace.'


class FloobitsCreateHangoutCommand(FloobitsBaseCommand):
    def run(self):
        owner = G.AGENT.owner
        workspace = G.AGENT.workspace
        host = G.AGENT.proto.host
        webbrowser.open('https://plus.google.com/hangouts/_?gid=770015849706&gd=%s/%s/%s' % (host, owner, workspace))

    def is_enabled(self):
        return bool(super(FloobitsCreateHangoutCommand, self).is_enabled() and G.AGENT.owner and G.AGENT.workspace)


class FloobitsPromptHangoutCommand(FloobitsBaseCommand):
    def run(self, hangout_url):
        confirm = bool(sublime.ok_cancel_dialog('This workspace is being edited in a Google+ Hangout? Do you want to join the hangout?'))
        if not confirm:
            return
        webbrowser.open(hangout_url)

    def is_visible(self):
        return False

    def is_enabled(self):
        return bool(super(FloobitsPromptHangoutCommand, self).is_enabled() and G.AGENT.owner and G.AGENT.workspace)


class FloobitsOpenWebEditorCommand(FloobitsBaseCommand):
    def run(self):
        try:
            agent = G.AGENT
            url = utils.to_workspace_url({
                'port': agent.proto.port,
                'secure': agent.proto.secure,
                'owner': agent.owner,
                'workspace': agent.workspace,
                'host': agent.proto.host,
            })
            webbrowser.open(url)
        except Exception as e:
            sublime.error_message('Unable to open workspace in web editor: %s' % str_e(e))


class FloobitsHelpCommand(FloobitsBaseCommand):
    def run(self):
        webbrowser.open('https://floobits.com/help/plugins/sublime', new=2, autoraise=True)

    def is_visible(self):
        return True

    def is_enabled(self):
        return True


class FloobitsToggleFollowModeCommand(FloobitsBaseCommand):
    def run(self):
        if G.FOLLOW_MODE:
            self.window.run_command('floobits_disable_follow_mode')
        else:
            self.window.run_command('floobits_enable_follow_mode')


class FloobitsEnableFollowModeCommand(FloobitsBaseCommand):
    def run(self):
        G.FOLLOW_MODE = True
        msg.log('Follow mode enabled')
        G.AGENT.update_status_msg()
        G.AGENT.highlight()

    def is_visible(self):
        if G.AGENT:
            return self.is_enabled()
        return True

    def is_enabled(self):
        return bool(super(FloobitsEnableFollowModeCommand, self).is_enabled() and not G.FOLLOW_MODE)


class FloobitsDisableFollowModeCommand(FloobitsBaseCommand):
    def run(self):
        G.FOLLOW_MODE = False
        G.SPLIT_MODE = False
        msg.log('Follow mode disabled')
        G.AGENT.update_status_msg('Stopped following changes. ')

    def is_visible(self):
        return self.is_enabled()

    def is_enabled(self):
        return bool(super(FloobitsDisableFollowModeCommand, self).is_enabled() and G.FOLLOW_MODE)


class FloobitsOpenWorkspaceSettingsCommand(FloobitsBaseCommand):
    def run(self):
        url = G.AGENT.workspace_url + '/settings'
        webbrowser.open(url, new=2, autoraise=True)

    def is_enabled(self):
        return bool(super(FloobitsOpenWorkspaceSettingsCommand, self).is_enabled() and G.PERMS and 'kick' in G.PERMS)


class RequestPermissionCommand(FloobitsBaseCommand):
    def run(self, perms, *args, **kwargs):
        G.AGENT.send({
            'name': 'request_perms',
            'perms': perms
        })

    def is_enabled(self):
        if not super(RequestPermissionCommand, self).is_enabled():
            return False
        if 'patch' in G.PERMS:
            return False
        return True


class FloobitsFollowSplit(FloobitsBaseCommand):
    def run(self):
        G.SPLIT_MODE = True
        G.FOLLOW_MODE = True
        if self.window.num_groups() == 1:
            self.window.set_layout({
                'cols': [0.0, 1.0],
                'rows': [0.0, 0.5, 1.0],
                'cells': [[0, 0, 1, 1], [0, 1, 1, 2]]
            })


class FloobitsSetup(FloobitsBaseCommand):
    def is_visible(self):
        return True

    def is_enabled(self):
        return not utils.can_auth()

    def run(self):
        create_or_link_account(True)


class FloobitsNotACommand(sublime_plugin.WindowCommand):
    def run(self, *args, **kwargs):
        pass

    def is_visible(self):
        return True

    def is_enabled(self):
        return False

    def description(self):
        return

########NEW FILE########
