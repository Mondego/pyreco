__FILENAME__ = api
try:
    unicode()
except NameError:
    unicode = str

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
except ImportError:
    import editor
    import msg
    import shared as G
    import utils


def get_basic_auth():
    basic_auth = ('%s:%s' % (G.USERNAME, G.SECRET)).encode('utf-8')
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


def proxy_api_request(url, data, method):
    args = ['python', '-m', 'floo.proxy', '--url', url]
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


def hit_url(url, data, method):
    if data:
        data = json.dumps(data).encode('utf-8')
    r = Request(url, data=data)
    r.method = method
    r.get_method = lambda: method
    r.add_header('Authorization', 'Basic %s' % get_basic_auth())
    r.add_header('Accept', 'application/json')
    r.add_header('Content-type', 'application/json')
    r.add_header('User-Agent', user_agent())
    return urlopen(r, timeout=5)


def api_request(url, data=None, method=None):
    if data:
        method = method or 'POST'
    else:
        method = method or 'GET'
    if ssl is False:
        return proxy_api_request(url, data, method)
    try:
        r = hit_url(url, data, method)
    except HTTPError as e:
        r = e
    return APIResponse(r)


def create_workspace(post_data):
    api_url = 'https://%s/api/workspace' % G.DEFAULT_HOST
    return api_request(api_url, post_data)


def update_workspace(owner, workspace, data):
    api_url = 'https://%s/api/workspace/%s/%s' % (G.DEFAULT_HOST, owner, workspace)
    return api_request(api_url, data, method='PUT')


def get_workspace_by_url(url):
    result = utils.parse_url(url)
    api_url = 'https://%s/api/workspace/%s/%s' % (result['host'], result['owner'], result['workspace'])
    return api_request(api_url)


def get_workspace(owner, workspace):
    api_url = 'https://%s/api/workspace/%s/%s' % (G.DEFAULT_HOST, owner, workspace)
    return api_request(api_url)


def get_workspaces():
    api_url = 'https://%s/api/workspace/can/view' % (G.DEFAULT_HOST)
    return api_request(api_url)


def get_orgs():
    api_url = 'https://%s/api/orgs' % (G.DEFAULT_HOST)
    return api_request(api_url)


def get_orgs_can_admin():
    api_url = 'https://%s/api/orgs/can/admin' % (G.DEFAULT_HOST)
    return api_request(api_url)


def send_error(description=None, exception=None):
    G.ERROR_COUNT += 1
    if G.ERRORS_SENT > G.MAX_ERROR_REPORTS:
        msg.warn('Already sent %s errors this session. Not sending any more.' % G.ERRORS_SENT)
        return
    data = {
        'jsondump': {
            'error_count': G.ERROR_COUNT
        },
        'username': G.USERNAME,
        'dir': G.COLAB_DIR,
    }
    if G.AGENT:
        data['owner'] = G.AGENT.owner
        data['workspace'] = G.AGENT.workspace
    if description:
        data['description'] = description
    if exception:
        data['message'] = {
            'msg': str(exception),
            'stack': traceback.format_exc(exception)
        }
        msg.log('Floobits plugin error! Sending exception report: %s' % data['message'])
    try:
        api_url = 'https://%s/api/log' % (G.DEFAULT_HOST)
        r = api_request(api_url, data)
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
        msg.error(unicode(e))
        return False
    try:
        w = get_workspace_by_url(workspace_url)
    except Exception as e:
        editor.error_message('Error opening url %s: %s' % (workspace_url, str(e)))
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
            msg.debug(unicode(e))
        return False

    msg.debug('workspace: %s', json.dumps(w.body))
    anon_perms = w.body.get('perms', {}).get('AnonymousUser', [])
    msg.debug('api args: %s' % api_args)
    new_anon_perms = api_args.get('perms', {}).get('AnonymousUser', [])
    # TODO: prompt/alert user if going from private to public
    if set(anon_perms) != set(new_anon_perms):
        msg.debug(str(anon_perms), str(new_anon_perms))
        w.body['perms']['AnonymousUser'] = new_anon_perms
        response = update_workspace(w.body['owner'], w.body['name'], w.body)
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
__FILENAME__ = account
import os
import sys
import traceback
import getpass

try:
    from . import base
    from .. import msg, api, shared as G, utils
    from ....floo import editor
    from ..protocols import floo_proto
    assert api and G and msg and utils
except (ImportError, ValueError):
    import base
    from floo import editor
    from floo.common.protocols import floo_proto
    from .. import msg, api, shared as G, utils


class CreateAccountHandler(base.BaseHandler):
    PROTOCOL = floo_proto.FlooProtocol

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
                if False in [bool(x) for x in (G.USERNAME, G.API_KEY, G.SECRET)]:
                    editor.error_message('Something went wrong. You will need to sign up for an account to use Floobits.')
                    api.send_error('No username or secret')
                else:
                    p = os.path.join(G.BASE_DIR, 'welcome.md')
                    with open(p, 'w') as fd:
                        text = editor.welcome_text % (G.USERNAME, self.proto.host)
                        fd.write(text)
                    d = utils.get_persistent_data()
                    d['auto_generated_account'] = True
                    utils.update_persistent_data(d)
                    G.AUTO_GENERATED_ACCOUNT = True
                    editor.open_file(p)
            except Exception as e:
                msg.debug(traceback.format_exc())
                msg.error(str(e))
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
        self.reload_settings()

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

    def is_ready(self):
        return self.joined_workspace

    def reload_settings(self):
        utils.reload_settings()
        self.username = G.USERNAME
        self.secret = G.SECRET
        self.api_key = G.API_KEY

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
    from ..protocols import floo_proto
    assert api and G and utils
except (ImportError, ValueError):
    import base
    from floo import editor
    from floo.common.protocols import floo_proto
    from .. import api, shared as G, utils

WELCOME_MSG = """Welcome %s!\n\nYou are all set to collaborate.

You may want to check out our docs at https://%s/help/plugins"""


class RequestCredentialsHandler(base.BaseHandler):
    PROTOCOL = floo_proto.FlooProtocol

    def __init__(self, token):
        super(RequestCredentialsHandler, self).__init__()
        self.token = token

    def build_protocol(self, *args):
        proto = super(RequestCredentialsHandler, self).build_protocol(*args)
        webbrowser.open('https://%s/dash/link_editor/%s/%s' % (proto.host, self.codename, self.token))
        return proto

    def is_ready(self):
        return False

    def on_connect(self):
        self.send({
            'name': 'request_credentials',
            'client': self.client,
            'platform': sys.platform,
            'token': self.token,
            'version': G.__VERSION__
        })

    def on_data(self, name, data):
        if name == 'credentials':
            with open(G.FLOORC_PATH, 'w') as floorc_fd:
                floorc = self.BASE_FLOORC + '\n'.join(['%s %s' % (k, v) for k, v in data['credentials'].items()]) + '\n'
                floorc_fd.write(floorc)
            utils.reload_settings()
            if not G.USERNAME or not G.SECRET:
                editor.error_message('Something went wrong. See https://%s/help/floorc to complete the installation.' % self.proto.host)
                api.send_error('No username or secret')
            else:
                p = os.path.join(G.BASE_DIR, 'welcome.md')
                with open(p, 'w') as fd:
                    text = WELCOME_MSG % (G.USERNAME, self.proto.host)
                    fd.write(text)
                editor.open_file(p)
            self.proto.stop()

########NEW FILE########
__FILENAME__ = floo_handler
import os
import sys
import hashlib
import base64
import collections
from operator import attrgetter

try:
    import io
except ImportError:
    io = None

try:
    from . import base
    from ..reactor import reactor
    from ..lib import DMP
    from .. import msg, ignore, shared as G, utils
    from ... import editor
    from ..protocols import floo_proto
except (ImportError, ValueError) as e:
    import base
    from floo import editor
    from floo.common.lib import DMP
    from floo.common.reactor import reactor
    from floo.common import msg, ignore, shared as G, utils
    from floo.common.protocols import floo_proto

try:
    unicode()
except NameError:
    unicode = str

MAX_WORKSPACE_SIZE = 50000000  # 50MB


class FlooHandler(base.BaseHandler):
    PROTOCOL = floo_proto.FlooProtocol

    def __init__(self, owner, workspace, get_bufs=True):
        super(FlooHandler, self).__init__()
        self.owner = owner
        self.workspace = workspace
        self.should_get_bufs = get_bufs
        self.reset()

    def _on_highlight(self, data):
        raise NotImplementedError("_on_highlight not implemented")

    def ok_cancel_dialog(self, msg, cb=None):
        raise NotImplementedError("ok_cancel_dialog not implemented.")

    def get_view(self, buf_id):
        raise NotImplementedError("get_view not implemented")

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
            return ""

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
        self.reload_settings()

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
                    print(e)

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
                msg.debug('Error deleting %s: %s' % (path, str(e)))
        user_id = data.get('user_id')
        username = self.get_username_by_id(user_id)
        msg.log('%s %s %s' % (username, action, path))

    @utils.inlined_callbacks
    def _on_room_info(self, data):
        self.reset()
        self.joined_workspace = True
        self.workspace_info = data
        G.PERMS = data['perms']

        if 'patch' not in data['perms']:
            no_perms_msg = '''You don't have permission to edit this workspace. All files will be read-only.'''
            msg.log('No patch permission. Setting buffers to read-only')
            if 'request_perm' in data['perms']:
                should_send = yield self.ok_cancel_dialog, no_perms_msg + '\nDo you want to request edit permission?'
                if should_send:
                    self.send({'name': 'request_perms', 'perms': ['edit_room']})
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

        changed_bufs = []
        missing_bufs = []
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
                    changed_bufs.append(buf_id)
                    buf['md5'] = view_md5
            else:
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
                        changed_bufs.append(buf_id)
                        buf['md5'] = md5
                except Exception as e:
                    msg.debug('Error calculating md5 for %s, %s' % (buf['path'], e))
                    missing_bufs.append(buf_id)

        stomp_local = self.should_get_bufs
        if stomp_local and (changed_bufs or missing_bufs):
            changed = [self.bufs[buf_id] for buf_id in changed_bufs]
            missing = [self.bufs[buf_id] for buf_id in missing_bufs]
            choice = yield self.stomp_prompt, changed, missing
            if choice not in [0, 1]:
                self.stop()
                return
            stomp_local = bool(choice)

        for buf_id in changed_bufs:
            buf = self.bufs[buf_id]
            if stomp_local:
                self.get_buf(buf_id, buf.get('view'))
                self.save_on_get_bufs.add(buf_id)
            else:
                self._upload(utils.get_full_path(buf['path']), buf['buf'])

        for buf_id in missing_bufs:
            buf = self.bufs[buf_id]
            if stomp_local:
                self.get_buf(buf_id, buf.get('view'))
                self.save_on_get_bufs.add(buf_id)
            else:
                self.send({
                    'name': 'delete_buf',
                    'id': buf['id'],
                })

        success_msg = 'Successfully joined workspace %s/%s' % (self.owner, self.workspace)
        msg.log(success_msg)
        editor.status_message(success_msg)

        temp_data = data.get('temp_data', {})
        hangout = temp_data.get('hangout', {})
        hangout_url = hangout.get('url')
        if hangout_url:
            self.prompt_join_hangout(hangout_url)

        data = utils.get_persistent_data()
        data['recent_workspaces'].insert(0, {"url": self.workspace_url})
        utils.update_persistent_data(data)
        utils.add_workspace_to_persistent_json(self.owner, self.workspace, self.workspace_url, G.PROJECT_PATH)
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
            print('Unable to delete user %s from user list' % (data))

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
            del on_view_load['patch']
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
    def upload(self, path, cb=None):
        ig = ignore.Ignore(None, path)
        if ig.size > MAX_WORKSPACE_SIZE:
            size = ig.size
            child_dirs = sorted(ig.children, key=attrgetter("size"))
            ignored_cds = []
            while size > MAX_WORKSPACE_SIZE and child_dirs:
                cd = child_dirs.pop()
                ignored_cds.append(cd)
                size -= cd.size
            if size > MAX_WORKSPACE_SIZE:
                editor.error_message(
                    'Maximum workspace size is %.2fMB.\n\n%s is too big (%.2fMB) to upload. Consider adding stuff to the .flooignore file.' %
                    (MAX_WORKSPACE_SIZE / 1000000.0, path, ig.size / 1000000.0))
                return
            upload = yield self.ok_cancel_dialog, '''Maximum workspace size is %.2fMB.\n
%s is too big (%.2fMB) to upload.\n\nWould you like to ignore the following and continue?\n\n%s''' % \
                (MAX_WORKSPACE_SIZE / 1000000.0, path, ig.size / 1000000.0, "\n".join([x.path for x in ignored_cds]))
            if not upload:
                return
            ig.children = child_dirs
        self._uploader(ig.list_paths(), cb, ig.size)

    def _uploader(self, paths_iter, cb, total_bytes, bytes_uploaded=0.0):
        reactor.tick()
        if len(self.proto) > 0:
            return utils.set_timeout(self._uploader, 10, paths_iter, cb, total_bytes, bytes_uploaded)

        bar_len = 20
        try:
            p = next(paths_iter)
            size = self._upload(p)
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
            return cb and cb()
        return utils.set_timeout(self._uploader, 50, paths_iter, cb, total_bytes, bytes_uploaded)

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
                    msg.debug('Error encoding buf %s: %s' % (path, str(e)))
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
            msg.error('Failed to create buffer %s: %s' % (path, unicode(e)))
        return size

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
    assert msg and utils
except ImportError:
    import msg

try:
    unicode()
except NameError:
    unicode = str


IGNORE_FILES = ['.gitignore', '.hgignore', '.flignore', '.flooignore']
# TODO: make this configurable
HIDDEN_WHITELIST = ['.floo'] + IGNORE_FILES
# TODO: grab global git ignores:
# gitconfig_file = popen("git config -z --get core.excludesfile", "r");
DEFAULT_IGNORES = ['extern', 'node_modules', 'tmp', 'vendor']
MAX_FILE_SIZE = 1024 * 1024 * 5


def create_flooignore(path):
    flooignore = os.path.join(path, '.flooignore')
    # A very short race condition, but whatever.
    if os.path.exists(flooignore):
        return
    try:
        with open(flooignore, 'w') as fd:
            fd.write('\n'.join(DEFAULT_IGNORES))
    except Exception as e:
        msg.error('Error creating default .flooignore: %s' % str(e))


class Ignore(object):
    def __init__(self, parent, path, recurse=True):
        self.parent = parent
        self.size = 0
        self.children = []
        self.files = []
        self.ignores = {
            '/TOO_BIG/': []
        }
        self.path = utils.unfuck_path(path)

        try:
            paths = os.listdir(self.path)
        except OSError as e:
            if e.errno != errno.ENOTDIR:
                msg.error('Error listing path %s: %s' % (path, unicode(e)))
                return
            self.path = os.path.dirname(self.path)
            self.add_file(os.path.basename(path))
            return
        except Exception as e:
            msg.error('Error listing path %s: %s' % (path, unicode(e)))
            return

        msg.debug('Initializing ignores for %s' % path)
        for ignore_file in IGNORE_FILES:
            try:
                self.load(ignore_file)
            except Exception:
                pass

        if recurse:
            for p in paths:
                self.add_file(p)

    def add_file(self, p):
        p_path = os.path.join(self.path, p)
        if p[0] == '.' and p not in HIDDEN_WHITELIST:
            msg.log('Ignoring hidden path %s' % p_path)
            return
        is_ignored = self.is_ignored(p_path)
        if is_ignored:
            msg.log(is_ignored)
            return
        try:
            s = os.stat(p_path)
        except Exception as e:
            msg.error('Error stat()ing path %s: %s' % (p_path, unicode(e)))
            return
        if stat.S_ISDIR(s.st_mode):
            ig = Ignore(self, p_path)
            self.children.append(ig)
            self.size += ig.size
            return
        elif stat.S_ISREG(s.st_mode):
            if s.st_size > (MAX_FILE_SIZE):
                self.ignores['/TOO_BIG/'].append(p)
                msg.log(self.is_ignored_message(p_path, p, '/TOO_BIG/'))
            else:
                self.size += s.st_size
                self.files.append(p)

    def load(self, ignore_file):
        with open(os.path.join(self.path, ignore_file), 'r') as fd:
            ignores = fd.read()
        self.ignores[ignore_file] = []
        for ignore in ignores.split('\n'):
            ignore = ignore.strip()
            if len(ignore) == 0:
                continue
            if ignore[0] == '#':
                continue
            msg.debug('Adding %s to ignore patterns' % ignore)
            self.ignores[ignore_file].append(ignore)

    def list_paths(self):
        for f in self.files:
            yield os.path.join(self.path, f)
        for c in self.children:
            for p in c.list_paths():
                yield p

    def is_ignored_message(self, path, pattern, ignore_file):
        if ignore_file == '/TOO_BIG/':
            return '%s ignored because it is too big (more than %s bytes)' % (path, MAX_FILE_SIZE)
        return '%s ignored by pattern %s in %s' % (path, pattern, os.path.join(self.path, ignore_file))

    def is_ignored(self, path, is_dir=None):
        rel_path = os.path.relpath(path, self.path)
        for ignore_file, patterns in self.ignores.items():
            for pattern in patterns:
                base_path, file_name = os.path.split(rel_path)
                if pattern[0] == '/':
                    # Only match immediate children
                    if utils.unfuck_path(base_path) == self.path and fnmatch.fnmatch(file_name, pattern[1:]):
                        return self.is_ignored_message(path, pattern, ignore_file)
                else:
                    if len(pattern) > 0 and pattern[-1] == '/':
                        if is_dir is None:
                            try:
                                s = os.stat(path)
                            except Exception as e:
                                msg.error('Error lstat()ing path %s: %s' % (path, unicode(e)))
                                continue
                            is_dir = stat.S_ISDIR(s.st_mode)
                        if is_dir:
                            pattern = pattern[:-1]
                    if fnmatch.fnmatch(file_name, pattern):
                        return self.is_ignored_message(path, pattern, ignore_file)
                    if fnmatch.fnmatch(rel_path, pattern):
                        return self.is_ignored_message(path, pattern, ignore_file)
        if self.parent:
            return self.parent.is_ignored(path)
        return False


def is_ignored(current_path, abs_path=None):
    abs_path = abs_path or current_path
    if not utils.is_shared(current_path):
        return True

    path = utils.to_rel_path(current_path)  # Never throws ValueError because is_shared would return False
    if path == ".":
        return False

    base_path, file_name = os.path.split(current_path)
    ig = Ignore(None, base_path, recurse=False)
    if ig.is_ignored(abs_path):
        return True

    return is_ignored(base_path, abs_path)

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

########NEW FILE########
__FILENAME__ = msg
import os
import time

try:
    from . import shared as G
    assert G
    unicode = str
    python2 = False
except ImportError:
    python2 = True
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
                safe_print(unicode(e))
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
    from . import base, proxy
    assert cert and G and msg and proxy and utils
except (ImportError, ValueError):
    from floo import editor
    from floo.common import api, cert, msg, shared as G, utils
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
                msg.error('Unable to parse json: %s' % str(e))
                msg.error('Data: %s' % before)
                # XXXX: THIS LOSES DATA
                self._buf_in = after
                continue
            name = data.get('name')
            try:
                msg.debug('got data ' + (name or 'no name'))
                self.emit('data', name, data)
            except Exception as e:
                api.send_error('Error handling %s event.' % name, e)
                if name == 'room_info':
                    editor.error_message('Error joining workspace: %s' % str(e))
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
        self.reconnect_delay = self.INITIAL_RECONNECT_DELAY
        self.retries = self.MAX_RETRIES
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
            msg.error('Error in SSL handshake:', e)
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
        self.retries = -1
        utils.cancel_timeout(self._reconnect_timeout)
        self._reconnect_timeout = None
        self.cleanup()
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
    unicode()
except NameError:
    unicode = str

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


#KANS: this should use base, but I want the connection logic from FlooProto (ie, move that shit to base)
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
    from ..common.handlers import tcp_server
    assert msg and tcp_server
except (ImportError, ValueError):
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
            msg.warn('Error stopping connection: %s' % str(e))
        self._handlers.remove(handler)
        self._protos.remove(handler.proto)
        if not self._handlers and not self._protos:
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
                return msg.error('Error in select(): %s' % str(e))
            raise Exception("can't handle more than one fd exception in reactor")

        for fileno in _except:
            fd = fd_map[fileno]
            self._reconnect(fd, _in, _out)

        for fileno in _out:
            fd = fd_map[fileno]
            try:
                fd.write()
            except Exception as e:
                msg.error('Couldn\'t write to socket: %s' % str(e))
                return self._reconnect(fd, _in)

        for fileno in _in:
            fd = fd_map[fileno]
            try:
                fd.read()
            except Exception as e:
                msg.error('Couldn\'t read from socket: %s' % str(e))
                fd.reconnect()

reactor = _Reactor()

########NEW FILE########
__FILENAME__ = shared
import os

__VERSION__ = ''
__PLUGIN_VERSION__ = ''

# Config settings
USERNAME = ''
SECRET = ''
API_KEY = ''

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
MAX_ERROR_REPORTS = 2

PROXY_PORT = 0  # Random port
SHARE_DIR = None
COLAB_DIR = ''
PROJECT_PATH = ''
WORKSPACE_WINDOW = None

PERMS = []
STALKER_MODE = False
SPLIT_MODE = False

AUTO_GENERATED_ACCOUNT = False
PLUGIN_PATH = None

CHAT_VIEW = None
CHAT_VIEW_PATH = None

TICK_TIME = 100
AGENT = None

IGNORE_MODIFIED_EVENTS = False
VIEW_TO_HASH = {}

FLOORC_PATH = os.path.expanduser(os.path.join('~', '.floorc'))

########NEW FILE########
__FILENAME__ = utils
import os
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
    from . import msg
    from .lib import DMP
    assert G and DMP
except ImportError:
    import editor
    import msg
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


class Waterfall(object):
    def __init__(self):
        self.chain = []

    def add(self, f, *args, **kwargs):
        self.chain.append(lambda: f(*args, **kwargs))

    def call(self):
        res = [f() for f in self.chain]
        self.chain = []
        return res


def reload_settings():
    floorc_settings = load_floorc()
    for name, val in floorc_settings.items():
        setattr(G, name, val)
    if G.SHARE_DIR:
        G.BASE_DIR = G.SHARE_DIR
    G.BASE_DIR = os.path.realpath(os.path.expanduser(G.BASE_DIR))
    G.COLAB_DIR = os.path.join(G.BASE_DIR, 'share')
    G.COLAB_DIR = os.path.realpath(G.COLAB_DIR)
    if G.DEBUG == '1':
        msg.LOG_LEVEL = msg.LOG_LEVELS['DEBUG']
    else:
        msg.LOG_LEVEL = msg.LOG_LEVELS['MSG']
    mkdir(G.COLAB_DIR)


def load_floorc():
    """try to read settings out of the .floorc file"""
    s = {}
    try:
        fd = open(G.FLOORC_PATH, 'r')
    except IOError as e:
        if e.errno == 2:
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
        msg.debug(str(e))
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
            msg.debug(str(e))

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
        if e.errno != 17:
            editor.error_message('Cannot create directory {0}.\n{1}'.format(path, e))
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
        msg.error('Error saving buf: %s' % str(e))


def _unwind_generator(gen_expr, cb=None, res=None):
    try:
        while True:
            arg0 = res
            args = []
            if type(res) == tuple:
                arg0 = res[0]
                args = list(res[1:])
            if not callable(arg0):
                # send only accepts one argument... this is slightly dangerous if
                # we ever just return a tuple of one elemetn
                if type(res) == tuple and len(res) == 1:
                    res = gen_expr.send(res[0])
                else:
                    res = gen_expr.send(res)
            else:
                def f(*args):
                    return _unwind_generator(gen_expr, cb, args)
                args.append(f)
                return arg0(*args)
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
from collections import defaultdict
import time

import vim

try:
    from .common import shared as G
    from .common import msg
except (ImportError, ValueError):
    import common.shared as G
    from common import msg


timeouts = defaultdict(list)
top_timeout_id = 0
cancelled_timeouts = set()
calling_timeouts = False
line_endings = "\n"
welcome_text = 'Welcome %s!\n\nYou are all set to collaborate. You should check out our docs at https://%s/help/plugins/#sublime-usage. \
You must run \':FlooCompleteSignup\' before you can login to floobits.com.'


def name():
    if sys.version_info < (3, 0):
        py_version = 2
    else:
        py_version = 3
    return 'Vim-py%s' % py_version


def codename():
    return 'vim'


def windows(*args, **kwargs):
    return []


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
    to_remove = []
    for t, tos in timeouts.items():
        if now >= t:
            for timeout in tos:
                timeout()
            to_remove.append(t)
    for k in to_remove:
        del timeouts[k]
    calling_timeouts = False


def error_message(*args, **kwargs):
    editor = getattr(G, 'editor', None)
    if editor:
        editor.error_message(*args, **kwargs)
    else:
        print(args, kwargs)


def status_message(msg):
    editor = getattr(G, 'editor', None)
    if editor:
        editor.status_message(msg)
    else:
        print(msg)


def message_dialog(message):
    msg.log(message)


def vim_choice(prompt, default, choices):
    default = choices.index(default) + 1
    choices_str = '\n'.join(['&%s' % choice for choice in choices])
    try:
        choice = int(vim.eval('confirm("%s", "%s", %s)' % (prompt, choices_str, default)))
    except KeyboardInterrupt:
        return None
    if choice == 0:
        return None
    return choices[choice - 1]


def ok_cancel_dialog(prompt):
    choice = vim_choice(prompt, 'ok', ['ok', 'cancel'])
    return choice == 'ok'


def open_file(filename):
    current_buffer = vim.eval('expand("%:p")')
    if current_buffer != filename:
        vim.command(':silent! edit! %s | :silent! :filetype detect' % filename)


def platform():
    return sys.platform


def get_line_endings(path=None):
    return line_endings

########NEW FILE########
__FILENAME__ = view
import vim
import editor

from common import msg, utils
from collections import defaultdict

# Foreground: background
COLORS = (
    ('white', 'red'),
    ('black', 'yellow'),
    ('black', 'green'),
    ('white', 'blue'),
)
HL_RULES = ['ctermfg=%s ctermbg=%s guifg=%s guibg=%s' % (fg, bg, fg, bg) for fg, bg in COLORS]


def user_id_to_region(user_id):
    return "floobitsuser%s" % user_id


def redraw():
    def doit():
        msg.debug("redrawing!")
        vim.command(":redraw!")
    utils.set_timeout(doit, 100)


class View(object):
    """editors representation of the buffer"""

    current_highlights = defaultdict(list)
    pending_highlights = {}

    def __init__(self, vim_buf):
        self.vim_buf = vim_buf

    def __repr__(self):
        return '%s %s' % (self.native_id, self.vim_buf.name)

    def __str__(self):
        return repr(self)

    def _offset_to_vim(self, offset):
        current_offset = 0
        for line_num, line in enumerate(self.vim_buf):
            next_offset = len(line) + 1
            if current_offset + next_offset > offset:
                break
            current_offset += next_offset
        col = offset - current_offset
        msg.debug('offset %s is line %s column %s' % (offset, line_num + 1, col + 1))
        return line_num + 1, col + 1

    @property
    def native_id(self):
        return self.vim_buf.number

    def is_loading(self):
        return False

    def get_text(self):
        # Work around EOF new line handling in Vim. Vim always puts a newline at the end of a file,
        # but never exposes that newline in the view text.
        tail = '\n'
        if self.vim_buf[-1] == '':
            tail = ''
        text = '\n'.join(self.vim_buf[:]) + tail
        return text.decode('utf-8')

    def update(self, data, message=True):
        self.set_text(data["buf"])

    def set_text(self, text):
        msg.debug('\n\nabout to patch %s %s' % (str(self), self.vim_buf.name))
        try:
            self.vim_buf[:] = text.encode('utf-8').split('\n')
        except Exception as e:
            msg.error("couldn't apply patches because: %s!\nThe unencoded text was: %s" % (str(e), text))
            raise

    def set_read_only(self, read_only=True):
        # TODO
        pass

    def set_status(self, *args):
        pass

    def apply_patches(self, buf, patches, username):
        cursor_offset = self.get_cursor_offset()
        msg.debug('cursor offset is %s bytes' % cursor_offset)
        self.set_text(patches[0])

        for patch in patches[2]:
            offset = patch[0]
            length = patch[1]
            patch_text = patch[2]
            if cursor_offset > offset:
                new_offset = len(patch_text) - length
                cursor_offset += new_offset

        self.set_cursor_position(cursor_offset)

    def focus(self):
        editor.open_file(self.vim_buf.name)

    def set_cursor_position(self, offset):
        line_num, col = self._offset_to_vim(offset)
        command = ':silent! call setpos(".", [%s, %s, %s, %s])' % (self.native_id, line_num, col, 0)
        msg.debug('setting pos: %s' % command)
        vim.command(command)

    def get_cursor_offset(self):
        return int(vim.eval('line2byte(line("."))+col(".")')) - 2

    def get_selections(self):
        # Vim likes to return strings for numbers even if you use str2nr:
        return [[int(pos) for pos in range_] for range_ in vim.eval("g:FloobitsGetSelection()")]

    def clear_highlight(self, user_id):
        msg.debug('clearing selections for user %s in view %s' % (user_id, self.vim_buf.name))
        for hl in self.current_highlights[user_id]:
            vim.command(":silent! :call matchdelete(%s)" % (hl,))
        del self.current_highlights[user_id]

    def highlight(self, ranges, user_id):
        msg.debug("got a highlight %s" % ranges)

        def doit():
            msg.debug("doing timed highlights")
            stored_ranges = self.pending_highlights[user_id]
            del self.pending_highlights[user_id]
            self._set_highlight(stored_ranges, user_id)

        if user_id not in self.pending_highlights:
            utils.set_timeout(doit, 150)
        self.pending_highlights[user_id] = ranges

    def _set_highlight(self, ranges, user_id):
        msg.debug('highlighting ranges %s' % (ranges))
        if vim.current.buffer.number != self.vim_buf.number:
            return
        region = user_id_to_region(user_id)

        hl_rule = HL_RULES[user_id % len(HL_RULES)]
        vim.command(":silent! highlight %s %s" % (region, hl_rule))

        self.clear_highlight(user_id)

        for _range in ranges:
            start_row, start_col = self._offset_to_vim(_range[0])
            end_row, end_col = self._offset_to_vim(_range[1])
            if start_row == end_row and start_col == end_col:
                if end_col >= len(self.vim_buf[end_row - 1]):
                    end_row += 1
                    end_col = 1
                else:
                    end_col += 1
            vim_region = "matchadd('{region}', '\%{start_row}l\%{start_col}v\_.*\%{end_row}l\%{end_col}v', 100)".\
                format(region=region, start_row=start_row, start_col=start_col, end_row=end_row, end_col=end_col)
            msg.debug("vim_region: %s" % (vim_region,))
            self.current_highlights[user_id].append(vim.eval(vim_region))
        redraw()

    def rename(self, name):
        msg.debug('renaming %s to %s' % (self.vim_buf.name, name))
        current = vim.current.buffer
        text = self.get_text()
        old_name = self.vim_buf.name
        old_number = self.native_id
        with open(name, 'wb') as fd:
            fd.write(text.encode('utf-8'))
        vim.command('edit! %s' % name)
        self.vim_buf = vim.current.buffer
        vim.command('edit! %s' % current.name)
        vim.command('bdelete! %s' % old_number)
        try:
            utils.rm(old_name)
        except Exception as e:
            msg.debug("couldn't delete %s... maybe thats OK?" % str(e))

    def save(self):
        # TODO: switch to the correct buffer, then save, then switch back
        vim.command(':silent! w!')

    def file_name(self):
        return self.vim_buf.name

########NEW FILE########
__FILENAME__ = vim_handler
import os
import time
import hashlib
import collections
import webbrowser

try:
    import ssl
    assert ssl
except ImportError:
    ssl = False

try:
    unicode()
except NameError:
    unicode = str

import vim

try:
    from . import editor
    from .common import msg, shared as G, utils
    from .view import View
    from .common.handlers import floo_handler
    assert G and msg and utils
except ImportError:
    from floo import editor
    from common import msg, shared as G, utils
    from common.handlers import floo_handler
    from view import View


def get_buf(view):
    if not (G.AGENT and G.AGENT.is_ready()):
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


class VimHandler(floo_handler.FlooHandler):
    def __init__(self, *args, **kwargs):
        super(VimHandler, self).__init__(*args, **kwargs)
        self.user_highlights = {}

    def tick(self):
        reported = set()
        while self.views_changed:
            v, buf = self.views_changed.pop()
            if not G.AGENT or not G.AGENT.joined_workspace:
                msg.debug('Not connected. Discarding view change.')
                continue
            if 'patch' not in G.PERMS:
                continue
            if 'buf' not in buf:
                msg.debug('No data for buf %s %s yet. Skipping sending patch' % (buf['id'], buf['path']))
                continue
            view = View(v)
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

            if not G.AGENT or not G.AGENT.joined_workspace:
                msg.debug('Not connected. Discarding selection change.')
                continue
            # consume highlight events to avoid leak
            if 'highlight' not in G.PERMS:
                continue

            view = View(v)
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
            }
            self.send(highlight_json)

    def maybe_selection_changed(self, vim_buf, is_ping):
        buf = self.get_buf_by_path(vim_buf.name)
        if not buf:
            msg.debug('no buffer found for view %s' % vim_buf.number)
            return
        view = self.get_view(buf['id'])
        msg.debug("selection changed: %s %s %s" % (vim_buf.number, buf['id'], view))
        self.selection_changed.append([vim_buf, buf, is_ping])

    def maybe_buffer_changed(self, vim_buf):
        buf = self.get_buf_by_path(vim_buf.name)
        if not buf or 'buf' not in buf:
            return

        if buf['buf'] != vim_buf[:]:
            self.views_changed.append([vim_buf, buf])

    def create_view(self, buf):
        path = buf['path']
        utils.save_buf(buf)
        vb = self.get_vim_buf_by_path(path)
        if vb:
            return View(vb)

        vim.command(':edit! %s' % path)
        vb = self.get_vim_buf_by_path(path)
        if vb is None:
            msg.debug('vim buffer is none even though we tried to open it: %s' % path)
            return
        return View(vb)

    def stomp_prompt(self, changed_bufs, missing_bufs, cb):
        choices = ['remote', 'local', 'cancel']
        prompt = 'The workspace is out of sync. '
        # TODO: better prompt.
        prompt += 'Overwrite (r)emote files, (l)ocal files, or (c)ancel and disconnect?'
        choice = editor.vim_choice(prompt, 'remote', choices)
        if choice == 'remote':
            return cb(0)
        if choice == 'local':
            return cb(1)
        if choice == 'cancel':
            return cb(2)
        return cb(-1)

    def ok_cancel_dialog(self, msg, cb=None):
        res = editor.ok_cancel_dialog(msg)
        return (cb and cb(res) or res)

    def get_vim_buf_by_path(self, p):
        for vim_buf in vim.buffers:
            if vim_buf.name and p == utils.to_rel_path(vim_buf.name):
                return vim_buf
        return None

    def get_view(self, buf_id):
        buf = self.bufs.get(buf_id)
        if not buf:
            return None

        vb = self.get_vim_buf_by_path(buf['path'])
        if not vb:
            return None

        if vim.eval('bufloaded(%s)' % vb.number) == '0':
            return None

        return View(vb)

    def save_view(self, view):
        self.ignored_saves[view.native_id] += 1
        view.save()

    def reset(self):
        super(self.__class__, self).reset()
        self.on_clone = {}
        self.create_buf_cbs = {}
        self.temp_disable_stalk = False
        self.temp_ignore_highlight = {}
        self.temp_ignore_highlight = {}
        self.views_changed = []
        self.selection_changed = []
        self.ignored_saves = collections.defaultdict(int)
        self.chat_deck = collections.deque(maxlen=50)

    def send_msg(self, text):
        self.send({'name': 'msg', 'data': text})
        timestamp = time.time()
        msgText = self.format_msg(text, self.username, timestamp)
        msg.log(msgText)
        self.chat_deck.appendleft(msgText)

    def chat(self, username, timestamp, message, self_msg=False):
        raise NotImplementedError("reconnect not implemented.")

    def prompt_join_hangout(self, hangout_url):
        if not utils.has_browser():
            return
        hangout_client = None
        users = self.workspace_info.get('users')
        for user_id, user in users.items():
            if user['username'] == G.USERNAME and 'hangout' in user['client']:
                hangout_client = user
                break
        if hangout_client:
            return
        choice = editor.vim_choice('This workspace is being edited in a hangout. Join the hangout?', 'yes', ['yes', 'no'])
        if choice == 'yes':
            webbrowser.open(hangout_url, new=2, autoraise=True)

    def format_msg(self, msg, username, timestamp):
        return '[%s] <%s> %s' % (time.ctime(timestamp), username, msg)

    def on_msg(self, data):
        timestamp = data.get('time') or time.time()
        msgText = self.format_msg(data.get('data', ''), data.get('username', ''), timestamp)
        msg.log(msgText)
        self.chat_deck.appendleft(msgText)

    def get_messages(self):
        return list(self.chat_deck)

    def get_username_by_id(self, user_id):
        try:
            return self.workspace_info['users'][str(user_id)]['username']
        except Exception:
            return ''

    def get_buf(self, buf_id, view=None):
        req = {
            'name': 'get_buf',
            'id': buf_id
        }
        buf = self.bufs.get(buf_id)
        if buf:
            msg.warn('Syncing buffer %s for consistency.' % buf['path'])
            if 'buf' in buf:
                del buf['buf']
        if view:
            view.set_read_only(True)
            view.set_status('Floobits', 'Floobits locked this file until it is synced.')
        G.AGENT.send(req)

    def delete_buf(self, path):
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
                        self.delete_buf(f_path)
            return
        buf_to_delete = self.get_buf_by_path(path)
        if buf_to_delete is None:
            msg.error('%s is not in this workspace' % path)
            return
        msg.log('deleting buffer ', utils.to_rel_path(path))
        event = {
            'name': 'delete_buf',
            'id': buf_to_delete['id'],
        }
        G.AGENT.send(event)

    def summon(self, view):
        buf = get_buf(view)
        if buf:
            msg.debug('summoning selection in view %s, buf id %s' % (buf['path'], buf['id']))
            self.selection_changed.append((view, buf, True))
        else:
            path = view.file_name()
            if not utils.is_shared(path):
                editor.error_message('Can\'t summon because %s is not in shared path %s.' % (path, G.PROJECT_PATH))
                return
            share = editor.ok_cancel_dialog('This file isn\'t shared. Would you like to share it?', 'Share')
            if share:
                sel = [[x.a, x.b] for x in view.sel()]
                self.create_buf_cbs[utils.to_rel_path(path)] = lambda buf_id: send_summon(buf_id, sel)
                self.upload(path)

    def _on_room_info(self, data):
        super(VimHandler, self)._on_room_info(data)
        vim.command(':Explore %s | redraw' % G.PROJECT_PATH)

    def _on_delete_buf(self, data):
        # TODO: somehow tell the user about this
        buf_id = data['id']
        view = self.get_view(buf_id)
        try:
            if view:
                view = view.view
                view.set_scratch(True)
                G.WORKSPACE_WINDOW.focus_view(view)
                G.WORKSPACE_WINDOW.run_command("close_file")
        except Exception as e:
            msg.debug('Error closing view: %s' % unicode(e))
        try:
            buf = self.bufs.get(buf_id)
            if buf:
                del self.paths_to_ids[buf['path']]
                del self.bufs[buf_id]
        except KeyError:
            msg.debug('KeyError deleting buf id %s' % buf_id)
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
            print(e)

    def _on_part(self, data):
        super(self.__class__, self)._on_part(data)
        user_id = data['user_id']
        highlight = self.user_highlights.get(user_id)
        if not highlight:
            return
        view = self.get_view(highlight['id'])
        if not view:
            return
        if vim.current.buffer.number != view.native_id:
            return
        view.clear_highlight(user_id)
        del self.user_highlights[user_id]

    def _on_highlight(self, data):
        buf_id = data['id']
        user_id = data['user_id']
        username = data.get('username', 'an unknown user')
        ping = G.STALKER_MODE or data.get('ping', False)
        previous_highlight = self.user_highlights.get(user_id)
        buf = self.bufs.get(buf_id)
        if not buf:
            return
        view = self.get_view(buf_id)
        if not view:
            if not ping:
                return
            view = self.create_view(buf)
            if not view:
                return
        data['path'] = buf['path']
        self.user_highlights[user_id] = data
        if ping:
            try:
                offset = data['ranges'][0][0]
            except IndexError as e:
                msg.debug('could not get offset from range %s' % e)
            else:
                if data.get('ping'):
                    msg.log('You have been summoned by %s' % (username))
                view.focus()
                view.set_cursor_position(offset)
        if G.SHOW_HIGHLIGHTS:
            if previous_highlight and previous_highlight['id'] == data['id']:
                view.clear_highlight(user_id)
            view.highlight(data['ranges'], user_id)

########NEW FILE########
__FILENAME__ = floobits
# coding: utf-8
import os
import os.path
import json
import re
import traceback
import atexit
import subprocess
import webbrowser
import uuid
import binascii
import imp
from functools import wraps

try:
    unicode()
except NameError:
    unicode = str

try:
    import urllib
    urllib = imp.reload(urllib)
    from urllib import request
    request = imp.reload(request)
    Request = request.Request
    urlopen = request.urlopen
    HTTPError = urllib.error.HTTPError
    URLError = urllib.error.URLError
    assert Request and urlopen and HTTPError and URLError
except ImportError:
    import urllib2
    urllib2 = imp.reload(urllib2)
    Request = urllib2.Request
    urlopen = urllib2.urlopen
    HTTPError = urllib2.HTTPError
    URLError = urllib2.URLError

import vim

from floo.common import api, ignore, migrations, msg, reactor, utils, shared as G
from floo.common.handlers.account import CreateAccountHandler
from floo.common.handlers.credentials import RequestCredentialsHandler
from floo.vim_handler import VimHandler
from floo import editor


reactor = reactor.reactor

# Protocol version
G.__VERSION__ = '0.11'
G.__PLUGIN_VERSION__ = '2.1.1'

utils.reload_settings()

migrations.rename_floobits_dir()
migrations.migrate_symlinks()

G.DELETE_LOCAL_FILES = bool(int(vim.eval('floo_delete_local_files')))
G.SHOW_HIGHLIGHTS = bool(int(vim.eval('floo_show_highlights')))
G.SPARSE_MODE = bool(int(vim.eval('floo_sparse_mode')))
G.TIMERS = bool(int(vim.eval('has("timers")')))


call_feedkeys = False
ticker = None
ticker_errors = 0
using_feedkeys = False

ticker_python = '''import sys; import subprocess; import time
args = ['{binary}', '--servername', '{servername}', '--remote-expr', 'g:FloobitsGlobalTick()']
while True:
    time.sleep({sleep})
    # TODO: learn to speak vim or something :(
    proc = subprocess.Popen(args,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE)
    (stdoutdata, stderrdata) = proc.communicate()
    # # yes, this is stupid...
    if stdoutdata.strip() == '0':
        continue
    if len(stderrdata) == 0:
        continue
    sys.stderr.write(stderrdata)
    sys.exit(1)
'''

FLOOBITS_INFO = '''
floobits_version: {version}
# not updated until FlooJoinWorkspace is called
mode: {mode}
updatetime: {updatetime}
clientserver_support: {cs}
servername: {servername}
ticker_errors: {ticker_errors}
'''


def _get_line_endings():
    formats = vim.eval('&fileformats')
    if not formats:
        return '\n'
    name = formats.split(',')[0]
    if name == 'dos':
        return '\r\n'
    return '\n'


def floobits_info():
    kwargs = {
        'cs': bool(int(vim.eval('has("clientserver")'))),
        'mode': (using_feedkeys and 'feedkeys') or 'client-server',
        'servername': vim.eval('v:servername'),
        'ticker_errors': ticker_errors,
        'updatetime': vim.eval('&l:updatetime'),
        'version': G.__PLUGIN_VERSION__,
    }

    msg.log(FLOOBITS_INFO.format(**kwargs))


def floobits_pause():
    global call_feedkeys, ticker

    if G.TIMERS:
        return

    if using_feedkeys:
        call_feedkeys = False
        vim.command('set updatetime=4000')
    else:
        if ticker is None:
            return
        try:
            ticker.kill()
        except Exception as e:
            print(e)
        ticker = None


def floobits_unpause():
    global call_feedkeys

    if G.TIMERS:
        return

    if using_feedkeys:
        call_feedkeys = True
        vim.command('set updatetime=250')
    else:
        start_event_loop()


def fallback_to_feedkeys(warning):
    global using_feedkeys
    using_feedkeys = True
    warning += ' Falling back to f//e hack which will break some key commands. You may need to call FlooPause/FlooUnPause before some commands.'
    msg.warn(warning)
    floobits_unpause()


def ticker_watcher(ticker):
    global ticker_errors
    if not G.AGENT:
        return
    ticker.poll()
    if ticker.returncode is None:
        return
    msg.warn('respawning new ticker')
    ticker_errors += 1
    if ticker_errors > 10:
        return fallback_to_feedkeys('Too much trouble with the floobits external ticker.')
    start_event_loop()
    utils.set_timeout(ticker_watcher, 2000, ticker)


def start_event_loop():
    global ticker

    if G.TIMERS:
        msg.debug('Your Vim was compiled with +timer support. Awesome!')
        return

    if not bool(int(vim.eval('has("clientserver")'))):
        return fallback_to_feedkeys('This VIM was not compiled with clientserver support. You should consider using a different vim!')

    exe = getattr(G, 'VIM_EXECUTABLE', None)
    if not exe:
        return fallback_to_feedkeys('Your vim was compiled with clientserver, but I don\'t know the name of the vim executable.'
                                    'Please define it in your ~/.floorc using the vim_executable directive. e.g. \'vim_executable mvim\'.')

    servername = vim.eval('v:servername')
    if not servername:
        return fallback_to_feedkeys('I can not identify the servername of this vim. You may need to pass --servername to vim at startup.')

    evaler = ticker_python.format(binary=exe, servername=servername, sleep='1.0')
    ticker = subprocess.Popen(['python', '-c', evaler],
                              stderr=subprocess.PIPE,
                              stdout=subprocess.PIPE)
    ticker.poll()
    utils.set_timeout(ticker_watcher, 500, ticker)


def vim_choice(prompt, default, choices):
    default = choices.index(default) + 1
    choices_str = '\n'.join(['&%s' % choice for choice in choices])
    try:
        choice = int(vim.eval('confirm("%s", "%s", %s)' % (prompt, choices_str, default)))
    except KeyboardInterrupt:
        return None
    if choice == 0:
        return None
    return choices[choice - 1]


def vim_input(prompt, default, completion=None):
    vim.command('call inputsave()')
    if completion:
        cmd = "let user_input = input('%s', '%s', '%s')" % (prompt, default, completion)
    else:
        cmd = "let user_input = input('%s', '%s')" % (prompt, default)
    vim.command(cmd)
    vim.command('call inputrestore()')
    return vim.eval('user_input')


def floobits_global_tick():
    reactor.tick()


def floobits_cursor_hold():
    floobits_global_tick()
    if not call_feedkeys:
        return
    return vim.command("call feedkeys(\"f\\e\", 'n')")


def floobits_cursor_holdi():
    floobits_global_tick()
    if not call_feedkeys:
        return
    linelen = int(vim.eval("col('$')-1"))
    if linelen > 0:
        if int(vim.eval("col('.')")) == 1:
            vim.command("call feedkeys(\"\<Right>\<Left>\",'n')")
        else:
            vim.command("call feedkeys(\"\<Left>\<Right>\",'n')")
    else:
        vim.command("call feedkeys(\"\ei\",'n')")


def is_connected(warn=False):
    def outer(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            if reactor.is_ready():
                return func(*args, **kwargs)
            if warn:
                msg.error('ignoring request (%s) because you aren\'t in a workspace.' % func.__name__)
            else:
                msg.debug('ignoring request (%s) because you aren\'t in a workspace.' % func.__name__)
        return wrapped
    return outer


@is_connected()
def floobits_maybe_selection_changed(ping=False):
    G.AGENT.maybe_selection_changed(vim.current.buffer, ping)


@is_connected()
def floobits_maybe_buffer_changed():
    G.AGENT.maybe_buffer_changed(vim.current.buffer)


@is_connected()
def floobits_follow(follow_mode=None):
    if follow_mode is None:
        follow_mode = not G.STALKER_MODE
    G.STALKER_MODE = follow_mode


@is_connected()
def floobits_maybe_new_file():
    path = vim.current.buffer.name
    if path is None or path == '':
        msg.debug('get:buf buffer has no filename')
        return None

    if not os.path.exists(path):
        return None
    if not utils.is_shared(path):
        msg.debug('get_buf: %s is not shared' % path)
        return None

    buf = G.AGENT.get_buf_by_path(path)
    if not buf:
        if not ignore.is_ignored(path):
            G.AGENT.upload(path)


@is_connected()
def floobits_on_save():
    buf = G.AGENT.get_buf_by_path(vim.current.buffer.name)
    if buf:
        G.AGENT.send({
            'name': 'saved',
            'id': buf['id'],
        })


@is_connected(True)
def floobits_open_in_browser():
    url = G.AGENT.workspace_url
    webbrowser.open(url)


@is_connected(True)
def floobits_add_buf(path=None):
    path = path or vim.current.buffer.name
    G.AGENT._upload(path)


@is_connected(True)
def floobits_delete_buf():
    name = vim.current.buffer.name
    G.AGENT.delete_buf(name)


@is_connected()
def floobits_buf_enter():
    buf = G.AGENT.get_buf_by_path(vim.current.buffer.name)
    if not buf:
        return
    buf_id = buf['id']
    d = G.AGENT.on_load.get(buf_id)
    if d:
        del G.AGENT.on_load[buf_id]
        try:
            d['patch']()
        except Exception as e:
            msg.debug('Error running on_load patch handler for buf %s: %s' % (buf_id, str(e)))
    # NOTE: we call highlight twice in follow mode... thats stupid
    for user_id, highlight in G.AGENT.user_highlights.items():
        if highlight['id'] == buf_id:
            G.AGENT._on_highlight(highlight)


@is_connected()
def floobits_clear():
    buf = G.AGENT.get_buf_by_path(vim.current.buffer.name)
    if not buf:
        return
    view = G.AGENT.get_view(buf['id'])
    if view:
        for user_id, username in G.AGENT.workspace_info['users'].items():
            view.clear_highlight(int(user_id))


@is_connected()
def floobits_toggle_highlights():
    G.SHOW_HIGHLIGHTS = not G.SHOW_HIGHLIGHTS
    if G.SHOW_HIGHLIGHTS:
        floobits_buf_enter()
        msg.log('Highlights enabled')
        return
    floobits_clear()
    msg.log('Highlights disabled')


def floobits_share_dir_private(dir_to_share):
    return floobits_share_dir(dir_to_share, perms={'AnonymousUser': []})


def floobits_share_dir_public(dir_to_share):
    return floobits_share_dir(dir_to_share, perms={'AnonymousUser': ['view_room']})


def floobits_share_dir(dir_to_share, perms):
    utils.reload_settings()
    workspace_name = os.path.basename(dir_to_share)
    G.PROJECT_PATH = os.path.realpath(dir_to_share)
    msg.debug('%s %s %s' % (G.USERNAME, workspace_name, G.PROJECT_PATH))

    file_to_share = None
    dir_to_share = os.path.expanduser(dir_to_share)
    dir_to_share = utils.unfuck_path(dir_to_share)
    dir_to_share = os.path.abspath(dir_to_share)
    dir_to_share = os.path.realpath(dir_to_share)

    workspace_name = os.path.basename(dir_to_share)

    if os.path.isfile(dir_to_share):
        file_to_share = dir_to_share
        dir_to_share = os.path.dirname(dir_to_share)

    try:
        utils.mkdir(dir_to_share)
    except Exception:
        return msg.error("The directory %s doesn't exist and I can't create it." % dir_to_share)

    if not os.path.isdir(dir_to_share):
        return msg.error('The directory %s doesn\'t appear to exist' % dir_to_share)

    floo_file = os.path.join(dir_to_share, '.floo')
    # look for the .floo file for hints about previous behavior
    info = {}
    try:
        floo_info = open(floo_file, 'rb').read().decode('utf-8')
        info = json.loads(floo_info)
    except (IOError, OSError):
        pass
    except Exception:
        msg.warn('couldn\'t read the floo_info file: %s' % floo_file)

    workspace_url = info.get('url')
    if workspace_url:
        parsed_url = api.prejoin_workspace(workspace_url, dir_to_share, {'perms': perms})
        if parsed_url:
            return floobits_join_workspace(workspace_url, dir_to_share, upload_path=file_to_share or dir_to_share)

    filter_func = lambda workspace_url: api.prejoin_workspace(workspace_url, dir_to_share, {'perms': perms})
    parsed_url = utils.get_workspace_by_path(dir_to_share, filter_func)

    if parsed_url:
        return floobits_join_workspace(workspace_url, dir_to_share, upload_path=file_to_share or dir_to_share)
    try:
        r = api.get_orgs_can_admin()
    except IOError as e:
        return editor.error_message('Error getting org list: %s' % str(e))
    if r.code >= 400 or len(r.body) == 0:
        workspace_name = vim_input('Workspace name:', workspace_name, "file")
        return create_workspace(workspace_name, dir_to_share, G.USERNAME, perms, upload_path=file_to_share or dir_to_share)

    orgs = r.body
    if len(orgs) == 0:
        return create_workspace(workspace_name, dir_to_share, G.USERNAME, perms, upload_path=file_to_share or dir_to_share)
    choices = []
    choices.append(G.USERNAME)
    for o in orgs:
        choices.append(o['name'])

    owner = vim_choice('Create workspace for:', G.USERNAME, choices)
    if owner:
        return create_workspace(workspace_name, dir_to_share, owner, perms, upload_path=file_to_share or dir_to_share)


def create_workspace(workspace_name, share_path, owner, perms=None, upload_path=None):
    workspace_url = 'https://%s/%s/%s' % (G.DEFAULT_HOST, G.USERNAME, workspace_name)
    try:
        api_args = {
            'name': workspace_name,
            'owner': owner,
        }
        if perms:
            api_args['perms'] = perms
        r = api.create_workspace(api_args)
    except Exception as e:
        return editor.error_message('Unable to create workspace %s: %s' % (workspace_url, unicode(e)))

    if r.code < 400:
        msg.debug('Created workspace %s' % workspace_url)
        return floobits_join_workspace(workspace_url, share_path, upload_path=upload_path)

    if r.code == 402:
        # TODO: Better behavior. Ask to create a public workspace instead?
        detail = r.body.get('detail')
        err_msg = 'Unable to create workspace because you have reached your maximum number of workspaces'
        if detail:
            err_msg += detail
        return editor.error_message(err_msg)

    if r.code == 400:
        workspace_name = re.sub('[^A-Za-z0-9_\-]', '-', workspace_name)
        workspace_name = vim_input(
            '%s is an invalid name. Workspace names must match the regex [A-Za-z0-9_\-]. Choose another name:' % workspace_name, workspace_name)
    elif r.code == 409:
        workspace_name = vim_input('Workspace %s already exists. Choose another name: ' % workspace_name, workspace_name + '1', 'file')
    else:
        return editor.error_message('Unable to create workspace: %s %s' % (workspace_url, unicode(e)))
    return create_workspace(workspace_name, share_path, perms, upload_path=upload_path)


def floobits_stop_everything():
    if G.AGENT:
        reactor.stop()
        G.AGENT = None
    floobits_pause()
    # TODO: get this value from vim and reset it
    vim.command('set updatetime=4000')

# NOTE: not strictly necessary
atexit.register(floobits_stop_everything)


def floobits_complete_signup():
    msg.debug('Completing signup.')
    if not utils.has_browser():
        msg.log('You need a modern browser to complete the sign up. Go to https://floobits.com to sign up.')
        return
    floorc = utils.load_floorc()
    username = floorc.get('USERNAME')
    secret = floorc.get('SECRET')
    msg.debug('Completing sign up with %s %s' % (username, secret))
    if not (username and secret):
        return msg.error('You don\'t seem to have a Floobits account of any sort.')
    webbrowser.open('https://%s/%s/pinocchio/%s' % (G.DEFAULT_HOST, username, secret))


def floobits_check_credentials():
    msg.debug('Print checking credentials.')
    if not (G.USERNAME and G.SECRET):
        if not utils.has_browser():
            msg.log('You need a Floobits account to use the Floobits plugin. Go to https://floobits.com to sign up.')
            return
        floobits_setup_credentials()


def floobits_setup_credentials():
    prompt = 'You need a Floobits account! Do you have one? If no we will create one for you [y/n]. '
    d = vim_input(prompt, '')
    if d and (d != 'y' and d != 'n'):
        return floobits_setup_credentials()
    agent = None
    if d == 'y':
        msg.debug('You have an account.')
        token = binascii.b2a_hex(uuid.uuid4().bytes).decode('utf-8')
        agent = RequestCredentialsHandler(token)
    elif not utils.get_persistent_data().get('disable_account_creation'):
        agent = CreateAccountHandler()
    if not agent:
        msg.error('A configuration error occured earlier. Please go to floobits.com and sign up to use this plugin.\n\n'
                  'We\'re really sorry. This should never happen.')
        return
    try:
        reactor.connect(agent, G.DEFAULT_HOST, G.DEFAULT_PORT, True)
    except Exception as e:
        msg.error(str(e))
        msg.debug(traceback.format_exc())


def floobits_check_and_join_workspace(workspace_url):
    try:
        r = api.get_workspace_by_url(workspace_url)
    except Exception as e:
        return editor.error_message('Error joining %s: %s' % (workspace_url, str(e)))
    if r.code >= 400:
        return editor.error_message('Error joining %s: %s' % (workspace_url, r.body))
    msg.debug('Workspace %s exists' % workspace_url)
    return floobits_join_workspace(workspace_url)


def floobits_join_workspace(workspace_url, d='', upload_path=None):
    editor.line_endings = _get_line_endings()
    msg.debug('workspace url is %s' % workspace_url)
    try:
        result = utils.parse_url(workspace_url)
    except Exception as e:
        return msg.error(str(e))

    if d:
        utils.mkdir(d)
    else:
        try:
            d = utils.get_persistent_data()['workspaces'][result['owner']][result['workspace']]['path']
        except Exception:
            d = os.path.realpath(os.path.join(G.COLAB_DIR, result['owner'], result['workspace']))

    prompt = 'Save workspace files to: '
    if not os.path.isdir(d):
        while True:
            d = vim_input(prompt, d, 'dir')
            if d == '':
                continue
            d = os.path.realpath(os.path.expanduser(d))
            if os.path.isfile(d):
                prompt = '%s is not a directory. Enter an existing path or a path I can create: ' % d
                continue
            if not os.path.isdir(d):
                try:
                    utils.mkdir(d)
                except Exception as e:
                    prompt = 'Couldn\'t make dir %s: %s ' % (d, str(e))
                    continue
            break
    d = os.path.realpath(os.path.abspath(d) + os.sep)
    try:
        utils.add_workspace_to_persistent_json(result['owner'], result['workspace'], workspace_url, d)
    except Exception as e:
        return msg.error('Error adding workspace to persistent.json: %s' % str(e))

    G.PROJECT_PATH = d
    vim.command('cd %s' % G.PROJECT_PATH)
    msg.debug('Joining workspace %s' % workspace_url)

    floobits_stop_everything()
    try:
        conn = VimHandler(result['owner'], result['workspace'])
        if upload_path:
            conn.once('room_info', lambda: G.AGENT.upload(upload_path))
        reactor.connect(conn, result['host'], result['port'], result['secure'])
    except Exception as e:
        msg.error(str(e))
        tb = traceback.format_exc()
        msg.debug(tb)
    if not G.TIMERS:
        start_event_loop()


def floobits_part_workspace():
    if not G.AGENT:
        return msg.warn('Unable to leave workspace: You are not joined to a workspace.')
    floobits_stop_everything()
    msg.log('You left the workspace.')


def floobits_users_in_workspace():
    if not G.AGENT:
        return msg.warn('Not connected to a workspace.')
    vim.command('echom "Users connected to %s"' % (G.AGENT.workspace,))
    for user in G.AGENT.workspace_info['users'].values():
        vim.command('echom "  %s connected with %s on %s"' % (user['username'], user['client'], user['platform']))


def floobits_list_messages():
    if not G.AGENT:
        return msg.warn('Not connected to a workspace.')
    vim.command('echom "Recent messages for %s"' % (G.AGENT.workspace,))
    for message in G.AGENT.get_messages():
        vim.command('echom "  %s"' % (message,))


def floobits_say_something():
    if not G.AGENT:
        return msg.warn('Not connected to a workspace.')
    something = vim_input('Say something in %s: ' % (G.AGENT.workspace,), '')
    if something:
        G.AGENT.send_msg(something)

########NEW FILE########
__FILENAME__ = floobits_wrapper
import floobits

# code run after our own by other plugins can not pollute the floobits namespace
__globals = globals()
for k, v in floobits.__dict__.items():
    __globals[k] = v

# Vim essentially runs python by concating the python string into a single python file and running it.
# Before we did this, the following would happen:

# 1. import utils
# 2. from ycm import utils
# 3. utils.parse_url # references the wrong utils ...

########NEW FILE########
