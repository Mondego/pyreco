__FILENAME__ = conf
import sys, os
from os.path import abspath, dirname, join


doc_root = dirname(__file__)
# autodoc_dump_rst = open(join(doc_root, 'autodoc.rst'), 'w')

os.chdir(doc_root)
sys.path.insert(0, abspath('..')) # for module itself
sys.path.append(abspath('.')) # for extenstions

needs_sphinx = '1.1'
extensions = ['sphinx.ext.autodoc', 'sphinx_local_hooks']

master_doc = 'api'
pygments_style = 'sphinx'

source_suffix = '.rst'
# exclude_patterns = ['_build']
# templates_path = ['_templates']

autoclass_content = 'class'
autodoc_member_order = 'bysource'
autodoc_default_flags = ['members', 'undoc-members', 'show-inheritance']

########NEW FILE########
__FILENAME__ = sphinx_local_hooks
#-*- coding: utf-8 -*-
from __future__ import print_function

import itertools as it, operator as op, functools as ft
from collections import Iterable
import os, sys, types, re

from sphinx.ext.autodoc import Documenter

_autodoc_add_line = Documenter.add_line


@ft.wraps(_autodoc_add_line)
def autodoc_add_line(self, line, *argz, **kwz):
    tee = self.env.app.config.autodoc_dump_rst
    if tee:
        tee_line = self.indent + line
        if isinstance(tee, file):
            tee.write(tee_line + '\n')
        elif tee is True:
            print(tee_line)
        else:
            raise ValueError('Unrecognized'
                             ' value for "autodoc_dump_rst" option: {!r}'.format(tee))
    return _autodoc_add_line(self, line, *argz, **kwz)


Documenter.add_line = autodoc_add_line


def process_docstring(app, what, name, obj, options, lines):
    if not lines: return

    i, ld = 0, dict(enumerate(lines)) # to allow arbitrary peeks
    i_max = max(ld)

    def process_line(i):
        line, i_next = ld[i], i + 1
        while i_next not in ld and i_next <= i_max: i_next += 1
        line_next = ld.get(i_next)

        if line_next and line_next[0] in u' \t': # tabbed continuation of the sentence
            ld[i] = u'{} {}'.format(line, line_next.strip())
            del ld[i_next]
            process_line(i)
        elif line.endswith(u'.') or (line_next and line_next[0].isupper()):
            ld[i + 0.5] = u''

    for i in xrange(i_max + 1):
        if i not in ld: continue # was removed
        process_line(i)

    # Overwrite the list items inplace, extending the list if necessary
    for i, (k, line) in enumerate(sorted(ld.viewitems())):
        try:
            lines[i] = line
        except IndexError:
            lines.append(line)


def skip_override(app, what, name, obj, skip, options):
    if options.get('exclude-members'):
        include_only = set(re.compile(k[3:])
            for k in options['exclude-members'] if k.startswith('rx:'))
        if include_only:
            for pat in include_only:
                if pat.search(name): break
            else:
                return True
    if what == 'exception':
        return False if name == '__init__' \
            and isinstance(obj, types.UnboundMethodType) else True
    elif what == 'class':
        if name in ['__init__', '__call__'] \
            and isinstance(obj, types.UnboundMethodType):
            return False
        elif getattr(obj, 'im_class', None) is type:
            return False
    return skip


def setup(app):
    app.connect('autodoc-process-docstring', process_docstring)
    app.connect('autodoc-skip-member', skip_override)
    app.add_config_value('autodoc_dump_rst', None, True)

########NEW FILE########
__FILENAME__ = sphinx_text_to_md
#!/usr/bin/env python
#-*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import itertools as it, operator as op, functools as ft
import os, sys, re


class FormatError(Exception): pass


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Convert sphinx-produced autodoc.apidoc text to markdown.')
    parser.add_argument('src', nargs='?', help='Source file (default: use stdin).')
    optz = parser.parse_args()

    src = open(optz.src) if optz.src else sys.stdin
    dst = sys.stdout

    py_name = r'[\w_\d]+'
    out = ft.partial(print, file=dst)

    st_attrdoc = 0
    st_cont, lse_nl = False, None

    for line in src:
        ls = line.strip()
        if not ls: # blank line
            out(line, end='')
            continue

        line_indent = re.search(r'^( +)', line)
        if not line_indent:
            line_indent = 0
        else:
            line_indent = len(line_indent.group(1))
            if line_indent % 3: raise FormatError('Weird indent size: {}'.format(line_indent))
            line_indent = line_indent / 3

        lp = line.split()
        lse = re.sub(r'(<\S+) at 0x[\da-f]+(>)', r'\1\2', ls)
        lse = re.sub(r'([_*<>])', r'\\\1', lse)
        for url in re.findall(r'\b\w+://\S+', lse):
            lse = lse.replace(url, url.replace(r'\_', '_'))
        lse = re.sub(r'\bu([\'"])', r'\1', lse)
        st_cont, lse_nl = bool(lse_nl), '' if re.search(r'\b\w+://\S+-$', lse) else '\n'

        st_attrdoc_reset = True
        if not line_indent:
            if len(lp) > 2 and lp[0] == lp[1]:
                if lp[0] in ('exception', 'class'): # class, exception
                    out('\n' * 1, end='')
                    out('* **{}**'.format(' '.join(lse.split()[1:])))

            else:
                raise FormatError('Unhandled: {!r}'.format(line))

        elif line_indent == 1:
            if re.search(r'^(\w+ )?{}\('.format(py_name), ls): # function
                out('\n' * 1, end='')
                out('{}* {}'.format(' ' * 4, lse))
                st_attrdoc, st_attrdoc_reset = 8, False
            elif re.search(r'^{}\s+=\s+'.format(py_name), ls): # attribute
                out('{}* {}'.format(' ' * 4, lse))
                st_attrdoc, st_attrdoc_reset = 8, False
            elif lp[0] == 'Bases:': # class bases
                out('{}{}'.format(' ' * 4, lse))
                st_attrdoc, st_attrdoc_reset = 4, False
            else:
                out('{}{}'.format(' ' * (4 * st_cont), ls), end=lse_nl) # class docstring

        else: # description line
            if ls[0] in '-*': line = '\\' + line.lstrip()
            out('{}{}'.format(' ' * (st_attrdoc * st_cont), line.strip()), end=lse_nl)
            st_attrdoc_reset = False

        if st_attrdoc and st_attrdoc_reset: st_attrdoc = 0


if __name__ == '__main__': main()

########NEW FILE########
__FILENAME__ = api_v5
#-*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import os
import urllib
import urlparse
import json
import types
import itertools as it
import operator as op
import functools as ft

from datetime import datetime, timedelta
from posixpath import join as ujoin # used for url pahs
from os.path import join, basename

from onedrive.conf import ConfigMixin

import logging

log = logging.getLogger(__name__)


class OneDriveInteractionError(Exception):
    pass


class ProtocolError(OneDriveInteractionError):
    def __init__(self, code, msg):
        super(ProtocolError, self).__init__(code, msg)
        self.code = code


class AuthenticationError(OneDriveInteractionError):
    pass


class DoesNotExists(OneDriveInteractionError):
    """Only raised from OneDriveAPI.resolve_path()."""


class OneDriveHTTPClient(object):
    def _requests_tls_workarounds(self, requests):
        # Workaround for TLSv1.2 issue with Microsoft livefilestore.com hosts.
        session = None

        if requests.__version__ in ['0.14.1', '0.14.2']:
            # These versions can only be monkey-patched, unfortunately.
            # See README and following related links for details:
            #  https://github.com/mk-fg/python-onedrive/issues/1
            #  https://github.com/kennethreitz/requests/pull/799
            #  https://github.com/kennethreitz/requests/pull/900
            #  https://github.com/kennethreitz/requests/issues/1083
            #  https://github.com/shazow/urllib3/pull/109

            try:
                from requests.packages.urllib3 import connectionpool as cp
            except ImportError:
                from urllib3 import connectionpool as cp

            socket, ssl, match_hostname = cp.socket, cp.ssl, cp.match_hostname

            class VerifiedHTTPSConnection(cp.VerifiedHTTPSConnection):
                def connect(self):
                    sock = socket.create_connection((self.host, self.port),
                                                    self.timeout)

                    self.sock = ssl.wrap_socket(sock,
                                                self.key_file,
                                                self.cert_file,
                                                cert_reqs=self.cert_reqs,
                                                ca_certs=self.ca_certs,
                                                ssl_version=ssl.PROTOCOL_TLSv1)
                    if self.ca_certs:
                        match_hostname(self.sock.getpeercert(), self.host)

            cp.VerifiedHTTPSConnection = VerifiedHTTPSConnection

        else:
            version = tuple(it.imap(int, requests.__version__.split('.')))
            if version > (1, 0, 0):
                # Less hacks necessary - session HTTPAdapter can be used
                try:
                    from requests.packages.urllib3.poolmanager import PoolManager
                except ImportError:
                    from urllib3.poolmanager import PoolManager

                from requests.adapters import HTTPAdapter
                import ssl

                _default_block = object()

                class TLSv1Adapter(HTTPAdapter):
                    def init_poolmanager(self, connections, maxsize,
                                         block=_default_block):
                        pool_kw = dict()
                        if block is _default_block:
                            try:
                                # 1.2.1+
                                from requests.adapters import DEFAULT_POOLBLOCK
                            except ImportError:
                                pass
                            else:
                                pool_kw['block'] = DEFAULT_POOLBLOCK
                        self.poolmanager = PoolManager(
                            num_pools=connections, maxsize=maxsize,
                            ssl_version=ssl.PROTOCOL_TLSv1, **pool_kw)

                session = requests.Session()
                session.mount('https://', TLSv1Adapter())

        requests._onedrive_tls_fixed = True
        return session

    def request(self, url, method='get', data=None,
                files=None, raw=False, headers=dict(), raise_for=dict(),
                session=None):
        """Make synchronous HTTP request.
            Can be overidden to use different http module
            (e.g. urllib2, twisted, etc)."""

        import requests  # import here to avoid dependency on the module

        if not getattr(requests, '_onedrive_tls_fixed', False):
            # temp fix for https://github.com/mk-fg/python-onedrive/issues/1
            patched_session = self._requests_tls_workarounds(requests)
            if patched_session is not None:
                self._requests_session = patched_session

        if session is None:
            try:
                session = self._requests_session
            except AttributeError:
                session = self._requests_session = requests.session()
        elif not session:
            session = requests

        method = method.lower()
        kwz, func = dict(), getattr(session, method,
                                    ft.partial(session.request, method.upper())
                                    )
        if data is not None:
            if method == 'post':
                kwz['data'] = data
            else:
                kwz['data'] = json.dumps(data)
                headers = headers.copy()
                headers.setdefault('Content-Type', 'application/json')
        if files is not None:
            # requests-2+ doesn't seem to add default content-type header
            for k, file_tuple in files.iteritems():
                if len(file_tuple) == 2:
                    files[k] = tuple(file_tuple) + ('application/octet-stream',)
                # rewind is necessary because request can be repeated due to auth failure
                file_tuple[1].seek(0)
            kwz['files'] = files
        if headers is not None:
            kwz['headers'] = headers
        code = res = None
        try:
            res = func(url, **kwz)
            # log.debug('Response headers: {}'.format(res.headers))
            code = res.status_code
            if code == requests.codes.no_content:
                return
            if code != requests.codes.ok:
                res.raise_for_status()
            return json.loads(res.text) if not raw else res.content
        except requests.RequestException as err:
            try:
                if res is None:
                    raise ValueError
                message = res.json()['error']
            except (ValueError, KeyError):
                message = err.message
            raise raise_for.get(code, ProtocolError)(code, message)


class OneDriveAuth(OneDriveHTTPClient):
    #: Client id/secret should be static on per-application basis.
    #: Can be received from LiveConnect by any registered user at
    #: https://manage.dev.live.com/

    #: API ToS can be found at
    #: http://msdn.microsoft.com/en-US/library/live/ff765012

    client_id = client_secret = None

    auth_url_user = 'https://login.live.com/oauth20_authorize.srf'
    auth_url_token = 'https://login.live.com/oauth20_token.srf'
    auth_scope = 'wl.skydrive', 'wl.skydrive_update', 'wl.offline_access'
    auth_redirect_uri_mobile = 'https://login.live.com/oauth20_desktop.srf'

    #: Set by auth_get_token() method, not used internally.
    #: Might be useful for debugging or extension purposes.
    auth_access_expires = auth_access_data_raw = None

    #: At least one of auth_code, auth_refresh_token or auth_access_token
    #: should be set before data requests.
    auth_code = auth_refresh_token = auth_access_token = None

    #: This (default) redirect_uri is special -
    #: app must be marked as "mobile" to use it.
    auth_redirect_uri = auth_redirect_uri_mobile

    def __init__(self, **config):
        """Initialize API wrapper class with specified properties set."""
        for k, v in config.viewitems():
            try:
                getattr(self, k)
            except AttributeError:
                raise AttributeError('Unrecognized configuration key: {}'
                                     .format(k))
            setattr(self, k, v)

    def auth_user_get_url(self, scope=None):
        """Build authorization URL for User Agent."""
        if not self.client_id:
            raise AuthenticationError('No client_id specified')
        return '{}?{}'.format(self.auth_url_user, urllib.urlencode(dict(
            client_id=self.client_id, scope=' '.join(scope or self.auth_scope),
            response_type='code', redirect_uri=self.auth_redirect_uri)))

    def auth_user_process_url(self, url):
        """Process tokens and errors from redirect_uri."""
        url = urlparse.urlparse(url)
        url_qs = dict(it.chain.from_iterable(
            urlparse.parse_qsl(v) for v in [url.query, url.fragment]))
        if url_qs.get('error'):
            raise AuthenticationError('{} :: {}'.format(
                url_qs['error'], url_qs.get('error_description')))
        self.auth_code = url_qs['code']
        return self.auth_code

    def auth_get_token(self, check_scope=True):
        """Refresh or acquire access_token."""
        res = self.auth_access_data_raw = self._auth_token_request()
        return self._auth_token_process(res, check_scope=check_scope)

    def _auth_token_request(self):
        post_data = dict(client_id=self.client_id,
                         client_secret=self.client_secret,
                         redirect_uri=self.auth_redirect_uri)
        if not self.auth_refresh_token:
            log.debug(
                'Requesting new access_token through authorization_code grant')

            post_data.update(code=self.auth_code,
                             grant_type='authorization_code')

        else:
            if self.auth_redirect_uri == self.auth_redirect_uri_mobile:
                # not necessary for "mobile" apps
                del post_data['client_secret']

            log.debug('Refreshing access_token')

            post_data.update(refresh_token=self.auth_refresh_token,
                             grant_type='refresh_token')

        post_data_missing_keys = list(k for k in ['client_id', 'client_secret',
                                                  'code', 'refresh_token',
                                                  'grant_type']
                                      if k in post_data and not post_data[k])
        if post_data_missing_keys:
            raise AuthenticationError('Insufficient authentication'
                                      ' data provided (missing keys: {})'
                                      .format(post_data_missing_keys))

        return self.request(self.auth_url_token, method='post', data=post_data)

    def _auth_token_process(self, res, check_scope=True):
        assert res['token_type'] == 'bearer'
        for k in 'access_token', 'refresh_token':
            if k in res:
                setattr(self, 'auth_{}'.format(k), res[k])
        self.auth_access_expires = None if 'expires_in' not in res \
            else (datetime.utcnow() + timedelta(0, res['expires_in']))

        scope_granted = res.get('scope', '').split()
        if check_scope and set(self.auth_scope) != set(scope_granted):
            raise AuthenticationError(
                "Granted scope ({}) doesn't match requested one ({})."
                .format(', '.join(scope_granted), ', '.join(self.auth_scope)))
        return scope_granted


class OneDriveAPIWrapper(OneDriveAuth):
    """Less-biased OneDrive API wrapper class.
        All calls made here return result of self.request() call directly,
        so it can easily be made async (e.g. return twisted deferred object)
        by overriding http request method in subclass."""

    api_url_base = 'https://apis.live.net/v5.0/'

    def _api_url(self, path, query=dict(),
                 pass_access_token=True, pass_empty_values=False):
        query = query.copy()

        if pass_access_token:
            query.setdefault('access_token', self.auth_access_token)

        if not pass_empty_values:
            for k, v in query.viewitems():
                if not v:
                    raise AuthenticationError(
                        'Empty key {!r} for API call (path: {})'
                        .format(k, path))

        return urlparse.urljoin(self.api_url_base,
                                '{}?{}'.format(path, urllib.urlencode(query)))

    def __call__(self, url='me/skydrive', query=dict(), query_filter=True,
                 auth_header=False, auto_refresh_token=True, **request_kwz):
        """Make an arbitrary call to LiveConnect API.
            Shouldn't be used directly under most circumstances."""
        if query_filter:
            query = dict((k, v) for k, v in
                         query.viewitems() if v is not None)
        if auth_header:
            request_kwz.setdefault('headers', dict())['Authorization'] = (
                'Bearer {}'.format(self.auth_access_token))

        kwz = request_kwz.copy()
        kwz.setdefault('raise_for', dict())[401] = AuthenticationError
        api_url = ft.partial(self._api_url,
                             url, query, pass_access_token=not auth_header)
        try:
            return self.request(api_url(), **kwz)

        except AuthenticationError:
            if not auto_refresh_token:
                raise
            self.auth_get_token()
            if auth_header:  # update auth header with a new token
                request_kwz['headers']['Authorization'] \
                    = 'Bearer {}'.format(self.auth_access_token)
            return self.request(api_url(), **request_kwz)

    def get_quota(self):
        """Get OneDrive object, representing quota."""
        return self('me/skydrive/quota')

    def listdir(self, folder_id='me/skydrive', limit=None):
        """Get OneDrive object, representing list of objects in a folder."""
        return self(ujoin(folder_id, 'files'), dict(limit=limit))

    def info(self, obj_id='me/skydrive'):
        """Return metadata of a specified object.
            See http://msdn.microsoft.com/en-us/library/live/hh243648.aspx
            for the list and description of metadata keys for
            each object type."""
        return self(obj_id)

    def get(self, obj_id, byte_range=None):
        """Download and return a file object or a specified byte_range from it.
            See HTTP Range header (rfc2616) for possible byte_range formats,
            Examples: "0-499" - byte offsets 0-499 (inclusive),
                      "-500" - final 500 bytes."""
        kwz = dict()
        if byte_range:
            kwz['headers'] = dict(Range='bytes={}'.format(byte_range))
        return self(ujoin(obj_id, 'content'), dict(download='true'),
                    raw=True, **kwz)

    def put(self, path_or_tuple, folder_id='me/skydrive', overwrite=True):
        """Upload a file (object), possibly overwriting (default behavior)
            a file with the same "name" attribute, if it exists.

            First argument can be either path to a local file or tuple
             of "(name, file)", where "file" can be either a file-like object
             or just a string of bytes.

            overwrite option can be set to False to allow two identically-named
             files or "ChooseNewName" to let OneDrive derive some similar
             unique name. Behavior of this option mimics underlying API."""

        if overwrite is not None:
            if overwrite is False:
                overwrite = 'false'
            elif overwrite in ('true', True):
                overwrite = None  # don't pass it
            elif overwrite != 'ChooseNewName':
                raise ValueError('overwrite parameter'
                                 ' must be True, False or "ChooseNewName".')
        name, src = (basename(path_or_tuple), open(path_or_tuple, 'rb')) \
            if isinstance(path_or_tuple, types.StringTypes) \
            else (path_or_tuple[0], path_or_tuple[1])

        return self(ujoin(folder_id, 'files'), dict(overwrite=overwrite),
                    method='post', files=dict(file=(name, src)))

    def mkdir(self, name=None, folder_id='me/skydrive', metadata=dict()):
        """Create a folder with a specified "name" attribute.
            folder_id allows to specify a parent folder. metadata mapping may
            contain additional folder properties to pass to an API."""
        metadata = metadata.copy()
        if name:
            metadata['name'] = name
        return self(folder_id, data=metadata, method='post', auth_header=True)

    def delete(self, obj_id):
        'Delete specified object.'
        return self(obj_id, method='delete')

    def info_update(self, obj_id, data):
        """Update metadata with of a specified object.
            See http://msdn.microsoft.com/en-us/library/live/hh243648.aspx
            for the list of RW keys for each object type."""
        return self(obj_id, method='put', data=data, auth_header=True)

    def link(self, obj_id, link_type='shared_read_link'):
        """Return a preauthenticated (usable by anyone) link to a
            specified object. Object will be considered "shared" by OneDrive,
            even if link is never actually used.

           link_type can be either "embed" (returns html), "shared_read_link"
            or "shared_edit_link"."""

        assert link_type in ['embed', 'shared_read_link', 'shared_edit_link']
        return self(ujoin(obj_id, link_type), method='get')

    def copy(self, obj_id, folder_id, move=False):
        """Copy specified file (object) to a folder with a given ID.
            Well-known folder names (like "me/skydrive")
            don't seem to work here.

           Folders cannot be copied; this is an API limitation."""
        return self(obj_id,
                    method='copy' if not move else 'move',
                    data=dict(destination=folder_id), auth_header=True)

    def move(self, obj_id, folder_id):
        """Move specified file (object) to a folder.
            Note that folders cannot be moved, this is API limitation."""
        return self.copy(obj_id, folder_id, move=True)

    def comments(self, obj_id):
        """Get OneDrive object, representing a list of comments
            for an object."""
        return self(ujoin(obj_id, 'comments'))

    def comment_add(self, obj_id, message):
        """Add comment message to a specified object."""
        return self(ujoin(obj_id, 'comments'), method='post',
                    data=dict(message=message), auth_header=True)

    def comment_delete(self, comment_id):
        """Delete specified comment.
            comment_id can be acquired by listing comments for an object."""
        return self(comment_id, method='delete')


class OneDriveAPI(OneDriveAPIWrapper):
    """Biased synchronous OneDrive API interface.
        Adds some derivative convenience methods over OneDriveAPIWrapper."""

    def resolve_path(self, path,
                     root_id='me/skydrive', objects=False):
        """Return id (or metadata) of an object, specified by chain
            (iterable or fs-style path string) of "name" attributes of
            its ancestors, or raises DoesNotExists error.

           Requires many calls to resolve each name in path, so use with care.
            root_id parameter allows to specify path relative to some folder_id
            (default: me/skydrive)."""
        if path:
            if isinstance(path, types.StringTypes):
                if not path.startswith('me/skydrive'):
                    path = filter(None, path.split(os.sep))
                else:
                    root_id, path = path, None
            if path:
                try:
                    for i, name in enumerate(path):
                        root_id = dict(it.imap(op.itemgetter('name', 'id'),
                                               self.listdir(root_id)))[name]
                except (KeyError, ProtocolError) as err:
                    if isinstance(err, ProtocolError) and err.code != 404:
                        raise
                    raise DoesNotExists(root_id, path[i:])
        return root_id if not objects else self.info(root_id)

    def get_quota(self):
        """Return tuple of (bytes_available, bytes_quota)."""
        return (op.itemgetter('available', 'quota')(
                super(OneDriveAPI, self).get_quota()))

    def listdir(self, folder_id='me/skydrive', type_filter=None, limit=None):
        """Return a list of objects in the specified folder_id.
            limit is passed to the API, so might be used as optimization.
            type_filter can be set to type (str) or sequence
            of object types to return, post-api-call processing."""
        lst = super(OneDriveAPI, self).listdir(folder_id=folder_id,
                                               limit=limit)['data']
        if type_filter:
            if isinstance(type_filter, types.StringTypes):
                type_filter = {type_filter}
            lst = list(obj for obj in lst if obj['type'] in type_filter)
        return lst

    def copy(self, obj_id, folder_id, move=False):
        """Copy specified file (object) to a folder.
            Note that folders cannot be copied, this is API limitation."""
        if folder_id.startswith('me/skydrive'):
            log.info(
                "Special folder names (like 'me/skydrive') don't"
                " seem to work with copy/move operations, resolving it to id")
            folder_id = self.info(folder_id)['id']
        return super(OneDriveAPI, self).copy(obj_id, folder_id, move=move)

    def comments(self, obj_id):
        """Get a list of comments (message + metadata) for an object."""
        return super(OneDriveAPI, self).comments(obj_id)['data']


class PersistentOneDriveAPI(OneDriveAPI, ConfigMixin):
    conf_raise_structure_errors = True

    @ft.wraps(OneDriveAPI.auth_get_token)
    def auth_get_token(self, *argz, **kwz):
        # Wrapped to push new tokens to storage asap.
        ret = super(PersistentOneDriveAPI, self).auth_get_token(*argz, **kwz)
        self.sync()
        return ret

    def __del__(self):
        self.sync()

########NEW FILE########
__FILENAME__ = cli_tool
#!/usr/bin/env python
#-*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import itertools as it, operator as op, functools as ft
from os.path import dirname, basename, exists, isdir, join, abspath
from collections import defaultdict
import os, sys, io, re, types, json

try:
    import chardet
except ImportError: # optional
    chardet = None

try:
    from onedrive import api_v5, conf
except ImportError:
    # Make sure it works from a checkout
    if isdir(join(dirname(__file__), 'onedrive')) \
        and exists(join(dirname(__file__), 'setup.py')):
        sys.path.insert(0, dirname(__file__))
        from onedrive import api_v5, conf
    else:
        import api_v5, conf


force_encoding = None

def tree_node(): return defaultdict(tree_node)

def print_result(data, file, indent='', indent_first=None, indent_level=' '*2):
    # Custom printer is used because pyyaml isn't very pretty with unicode
    if isinstance(data, list):
        for v in data:
            print_result(v, file=file, indent=indent + '  ',
                indent_first=(indent_first if indent_first is not None else indent) + '- ')
            indent_first = None
    elif isinstance(data, dict):
        indent_cur = indent_first if indent_first is not None else indent
        for k, v in sorted(data.viewitems(), key=op.itemgetter(0)):
            print(indent_cur + decode_obj(k, force=True) + ':', file=file, end='')
            indent_cur = indent
            if not isinstance(v, (list, dict)): # peek to display simple types inline
                print_result(v, file=file, indent=' ')
            else:
                print('', file=file)
                print_result(v, file=file, indent=indent_cur+indent_level)
    else:
        if indent_first is not None: indent = indent_first
        print(indent + decode_obj(data, force=True), file=file)

def decode_obj(obj, force=False):
    'Convert or dump object to unicode.'
    if isinstance(obj, unicode):
        return obj
    elif isinstance(obj, bytes):
        if force_encoding is not None:
            return obj.decode(force_encoding)
        if chardet:
            enc_guess = chardet.detect(obj)
            if enc_guess['confidence'] > 0.7:
                return obj.decode(enc_guess['encoding'])
        return obj.decode('utf-8')
    else:
        return obj if not force else repr(obj)


def size_units(size,
               _units=list(reversed(list((u, 2 ** (i * 10))
                   for i, u in enumerate('BKMGT')))) ):
    for u, u1 in _units:
        if size > u1: break
    return size / float(u1), u


def id_match( s,
              _re_id=re.compile(r'^(file|folder)\.[0-9a-f]{16}\.[0-9A-F]{16}!\d+|folder\.[0-9a-f]{16}$') ):
    return s if s and _re_id.search(s) else None


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Tool to manipulate OneDrive contents.')
    parser.add_argument('-c', '--config',
                        metavar='path', default=conf.ConfigMixin.conf_path_default,
                        help='Writable configuration state-file (yaml).'
                             ' Used to store authorization_code, access and refresh tokens.'
                             ' Should initially contain at least something like "{client: {id: xxx, secret: yyy}}".'
                             ' Default: %(default)s')

    parser.add_argument('-p', '--path', action='store_true',
                        help='Interpret file/folder arguments only as human paths, not ids (default: guess).'
                             ' Avoid using such paths if non-unique "name" attributes'
                             ' of objects in the same parent folder might be used.')
    parser.add_argument('-i', '--id', action='store_true',
                        help='Interpret file/folder arguments only as ids (default: guess).')

    parser.add_argument('-e', '--encoding', metavar='enc',
                        action='store', help='Use specified encoding (example: utf-8) for CLI input/output.'
                             ' See full list of supported encodings at:'
                                 ' http://docs.python.org/2/library/codecs.html#standard-encodings .'
                             ' Default behavior is to detect input encoding via chardet module,'
                                 ' if available, falling back to utf-8 and use terminal encoding for output.')

    parser.add_argument('--debug',
                        action='store_true', help='Verbose operation mode.')

    cmds = parser.add_subparsers(title='Supported operations')

    def add_command(name, **kwz):
        cmd = cmds.add_parser(name, **kwz)
        cmd.set_defaults(call=name)
        return cmd

    cmd = add_command('auth', help='Perform user authentication.')
    cmd.add_argument('url', nargs='?',
                     help='URL with the authorization_code.')

    add_command('quota', help='Print quota information.')
    add_command('recent', help='List recently changed objects.')

    cmd = add_command('info', help='Display object metadata.')
    cmd.add_argument('object',
                     nargs='?', default='me/skydrive',
                     help='Object to get info on (default: %(default)s).')

    cmd = add_command('info_set', help='Manipulate object metadata.')
    cmd.add_argument('object',
                     help='Object to manipulate metadata for.')
    cmd.add_argument('data',
                     help='JSON mapping of values to set'
                          ' (example: {"name": "new_file_name.jpg"}).')

    cmd = add_command('link', help='Get a link to a file.')
    cmd.add_argument('object', help='Object to get link for.')
    cmd.add_argument('-t', '--type', default='shared_read_link',
                     help='Type of link to request. Possible values'
                          ' (default: %(default)s): shared_read_link, embed, shared_edit_link.')

    cmd = add_command('ls', help='List folder contents.')
    cmd.add_argument('folder',
                     nargs='?', default='me/skydrive',
                     help='Folder to list contents of (default: %(default)s).')
    cmd.add_argument('-o', '--objects', action='store_true',
                     help='Dump full objects, not just name and id.')

    cmd = add_command('mkdir', help='Create a folder.')
    cmd.add_argument('name',
                     help='Name (or a path consisting of dirname + basename) of a folder to create.')
    cmd.add_argument('folder',
                     nargs='?', default=None,
                     help='Parent folder (default: me/skydrive).')
    cmd.add_argument('-m', '--metadata',
                     help='JSON mappings of metadata to set for the created folder.'
                          ' Optonal. Example: {"description": "Photos from last trip to Mordor"}')

    cmd = add_command('get', help='Download file contents.')
    cmd.add_argument('file', help='File (object) to read.')
    cmd.add_argument('file_dst', nargs='?', help='Name/path to save file (object) as.')
    cmd.add_argument('-b', '--byte-range',
                     help='Specific range of bytes to read from a file (default: read all).'
                          ' Should be specified in rfc2616 Range HTTP header format.'
                          ' Examples: 0-499 (start - 499), -500 (end-500 to end).')

    cmd = add_command('put', help='Upload a file.')
    cmd.add_argument('file', help='Path to a local file to upload.')
    cmd.add_argument('folder',
                     nargs='?', default='me/skydrive',
                     help='Folder to put file into (default: %(default)s).')
    cmd.add_argument('-n', '--no-overwrite', action='store_true',
                     help='Do not overwrite existing files with the same "name" attribute (visible name).')

    cmd = add_command('cp', help='Copy file to a folder.')
    cmd.add_argument('file', help='File (object) to copy.')
    cmd.add_argument('folder',
                     nargs='?', default='me/skydrive',
                     help='Folder to copy file to (default: %(default)s).')

    cmd = add_command('mv', help='Move file to a folder.')
    cmd.add_argument('file', help='File (object) to move.')
    cmd.add_argument('folder',
                     nargs='?', default='me/skydrive',
                     help='Folder to move file to (default: %(default)s).')

    cmd = add_command('rm', help='Remove object (file or folder).')
    cmd.add_argument('object', nargs='+', help='Object(s) to remove.')

    cmd = add_command('comments', help='Show comments for a file, object or folder.')
    cmd.add_argument('object', help='Object to show comments for.')

    cmd = add_command('comment_add', help='Add comment for a file, object or folder.')
    cmd.add_argument('object', help='Object to add comment for.')
    cmd.add_argument('message', help='Comment message to add.')

    cmd = add_command('comment_delete', help='Delete comment from a file, object or folder.')
    cmd.add_argument('comment_id',
                     help='ID of the comment to remove (use "comments"'
                          ' action to get comment ids along with the messages).')

    cmd = add_command('tree',
                      help='Show contents of onedrive (or folder) as a tree of file/folder names.'
                           ' Note that this operation will have to (separately) request a listing'
                           ' of every folder under the specified one, so can be quite slow for large'
                           ' number of these.')
    cmd.add_argument('folder',
                     nargs='?', default='me/skydrive',
                     help='Folder to display contents of (default: %(default)s).')
    cmd.add_argument('-o', '--objects', action='store_true',
                     help='Dump full objects, not just name and type.')

    optz = parser.parse_args()

    if optz.path and optz.id:
        parser.error('--path and --id options cannot be used together.')

    if optz.encoding:
        global force_encoding
        force_encoding = optz.encoding

        import codecs
        sys.stdin = codecs.getreader(optz.encoding)(sys.stdin)
        sys.stdout = codecs.getwriter(optz.encoding)(sys.stdout)

    import logging

    log = logging.getLogger()
    logging.basicConfig(level=logging.WARNING
    if not optz.debug else logging.DEBUG)

    api = api_v5.PersistentOneDriveAPI.from_conf(optz.config)
    res = xres = None
    resolve_path_wrap = lambda s: api.resolve_path(s and s.replace('\\', '/').strip('/'))
    resolve_path = ( (lambda s: id_match(s) or resolve_path_wrap(s)) \
                         if not optz.path else resolve_path_wrap ) if not optz.id else lambda obj_id: obj_id

    # Make best-effort to decode all CLI options to unicode
    for k, v in vars(optz).viewitems():
        if isinstance(v, bytes):
            setattr(optz, k, decode_obj(v))
        elif isinstance(v, list):
            setattr(optz, k, map(decode_obj, v))

    if optz.call == 'auth':
        if not optz.url:
            print('Visit the following URL in any web browser (firefox, chrome, safari, etc),\n'
                  '  authorize there, confirm access permissions, and paste URL of an empty page\n'
                  '  (starting with "https://login.live.com/oauth20_desktop.srf")'
                  ' you will get redirected to in the end.')
            print('Alternatively, use the returned (after redirects)'
                  ' URL with "{} auth <URL>" command.\n'.format(sys.argv[0]))
            print('URL to visit: {}\n'.format(api.auth_user_get_url()))
            optz.url = raw_input('URL after last redirect: ').strip()
        if optz.url:
            api.auth_user_process_url(optz.url)
            api.auth_get_token()
            print('API authorization was completed successfully.')

    elif optz.call == 'quota':
        df, ds = map(size_units, api.get_quota())
        res = dict(free='{:.1f}{}'.format(*df), quota='{:.1f}{}'.format(*ds))
    elif optz.call == 'recent':
        res = api('me/skydrive/recent_docs')['data']

    elif optz.call == 'ls':
        res = list(api.listdir(resolve_path(optz.folder)))
        if not optz.objects: res = map(op.itemgetter('name'), res)

    elif optz.call == 'info':
        res = api.info(resolve_path(optz.object))
    elif optz.call == 'info_set':
        xres = api.info_update(
            resolve_path(optz.object), json.loads(optz.data))
    elif optz.call == 'link':
        res = api.link(resolve_path(optz.object), optz.type)
    elif optz.call == 'comments':
        res = api.comments(resolve_path(optz.object))
    elif optz.call == 'comment_add':
        res = api.comment_add(resolve_path(optz.object), optz.message)
    elif optz.call == 'comment_delete':
        res = api.comment_delete(optz.comment_id)

    elif optz.call == 'mkdir':
        name, path = optz.name, optz.folder
        if '/' in name.replace('\\', '/'):
            name = optz.name.replace('\\', '/')
            name, path_ext = basename(name), dirname(name)
            path = join(path, path_ext.strip('/')) if path else path_ext
        xres = api.mkdir(name=name, folder_id=resolve_path(path),
                         metadata=optz.metadata and json.loads(optz.metadata) or dict())

    elif optz.call == 'get':
        contents = api.get(resolve_path(optz.file), byte_range=optz.byte_range)
        if optz.file_dst:
            dst_dir = dirname(abspath(optz.file_dst))
            if not isdir(dst_dir):
                os.makedirs(dst_dir)
            with open(optz.file_dst, "wb") as dst:
                dst.write(contents)
        else:
            sys.stdout.write(contents)
            sys.stdout.flush()

    elif optz.call == 'put':
        xres = api.put(optz.file,
                       resolve_path(optz.folder), overwrite=not optz.no_overwrite)

    elif optz.call in ['cp', 'mv']:
        argz = map(resolve_path, [optz.file, optz.folder])
        xres = (api.move if optz.call == 'mv' else api.copy)(*argz)

    elif optz.call == 'rm':
        for obj in it.imap(resolve_path, optz.object): xres = api.delete(obj)


    elif optz.call == 'tree':

        def recurse(obj_id):
            node = tree_node()
            for obj in api.listdir(obj_id):
                # Make sure to dump files as lists with -o,
                #  not dicts, to make them distinguishable from dirs
                res = obj['type'] if not optz.objects else [obj['type'], obj]
                node[obj['name']] = recurse(obj['id']) \
                    if obj['type'] in ['folder', 'album'] else res
            return node

        root_id = resolve_path(optz.folder)
        res = {api.info(root_id)['name']: recurse(root_id)}


    else:
        parser.error('Unrecognized command: {}'.format(optz.call))

    if res is not None: print_result(res, file=sys.stdout)
    if optz.debug and xres is not None:
        buff = io.StringIO()
        print_result(xres, file=buff)
        log.debug('Call result:\n{0}\n{1}{0}'.format('-' * 20, buff.getvalue()))


if __name__ == '__main__': main()

########NEW FILE########
__FILENAME__ = conf
#-*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import itertools as it, operator as op, functools as ft
import os, sys, io, errno, tempfile, stat
from os.path import dirname, basename

import logging

log = logging.getLogger(__name__)


class ConfigMixin(object):
    #: Path to configuration file to use in from_conf() by default.
    conf_path_default = b'~/.lcrc'

    #: If set to some path, updates will be written back to it.
    conf_save = False

    #: Raise human-readable errors on structure issues,
    #:  which assume that there is an user-accessible configuration file
    conf_raise_structure_errors = False

    #: Hierarchical list of keys to write back
    #:  to configuration file (preserving the rest) on updates.
    conf_update_keys = dict(
        client={'id', 'secret'},
        auth={'code', 'refresh_token', 'access_expires', 'access_token'})


    def __init__(self, **kwz):
        raise NotImplementedError('Init should be overidden with something configurable')


    @classmethod
    def from_conf(cls, path=None, **overrides):
        '''Initialize instance from YAML configuration file,
            writing updates (only to keys, specified by "conf_update_keys") back to it.'''
        from onedrive import portalocker
        import yaml

        if path is None:
            path = cls.conf_path_default
            log.debug('Using default state-file path: %r', path)
        path = os.path.expanduser(path)
        with open(path, 'rb') as src:
            portalocker.lock(src, portalocker.LOCK_SH)
            conf = yaml.load(src.read())
            portalocker.unlock(src)
        conf.setdefault('conf_save', path)

        conf_cls = dict()
        for ns, keys in cls.conf_update_keys.viewitems():
            for k in keys:
                try:
                    v = conf.get(ns, dict()).get(k)
                except AttributeError:
                    if not cls.conf_raise_structure_errors: raise
                    raise KeyError('Unable to get value for configuration parameter'
                                   ' "{k}" in section "{ns}", check configuration file (path: {path}) syntax'
                                   ' near the aforementioned section/value.'.format(ns=ns, k=k, path=path))
                if v is not None:
                    conf_cls['{}_{}'.format(ns, k)] = conf[ns][k]
        conf_cls.update(overrides)

        self = cls(**conf_cls)
        self.conf_save = conf['conf_save']
        return self

    def sync(self):
        if not self.conf_save: return
        from onedrive import portalocker
        import yaml

        retry = False
        with open(self.conf_save, 'r+b') as src:
            portalocker.lock(src, portalocker.LOCK_SH)
            conf_raw = src.read()
            conf = yaml.load(io.BytesIO(conf_raw)) if conf_raw else dict()
            portalocker.unlock(src)

            conf_updated = False
            for ns, keys in self.conf_update_keys.viewitems():
                for k in keys:
                    v = getattr(self, '{}_{}'.format(ns, k), None)
                    if isinstance(v, unicode): v = v.encode('utf-8')
                    if v != conf.get(ns, dict()).get(k):
                        # log.debug(
                        # 	'Different val ({}.{}): {!r} != {!r}'\
                        # 	.format(ns, k, v, conf.get(ns, dict()).get(k)) )
                        conf.setdefault(ns, dict())[k] = v
                        conf_updated = True

            if conf_updated:
                log.debug('Updating configuration file (%r)', src.name)
                conf_new = yaml.safe_dump(conf, default_flow_style=False)
                if os.name == 'nt':
                    # lockf + tempfile + rename doesn't work on windows due to
                    #  "[Error 32] ... being used by another process",
                    #  so this update can potentially leave broken file there
                    # Should probably be fixed by someone who uses/knows about windows
                    portalocker.lock(src, portalocker.LOCK_EX)
                    src.seek(0)
                    if src.read() != conf_raw:
                        retry = True
                    else:
                        src.seek(0)
                        src.truncate()
                        src.write(conf_new)
                        src.flush()
                        portalocker.unlock(src)

                else:
                    with tempfile.NamedTemporaryFile(
                            prefix='{}.'.format(basename(self.conf_save)),
                            dir=dirname(self.conf_save), delete=False) as tmp:
                        try:
                            portalocker.lock(src, portalocker.LOCK_EX)
                            src.seek(0)
                            if src.read() != conf_raw:
                                retry = True
                            else:
                                portalocker.lock(tmp, portalocker.LOCK_EX)
                                tmp.write(conf_new)
                                os.fchmod(tmp.fileno(), stat.S_IMODE(os.fstat(src.fileno()).st_mode))
                                os.rename(tmp.name, src.name)
                                # Non-atomic update for pids that already have fd to old file,
                                #  but (presumably) are waiting for the write-lock to be released
                                src.seek(0)
                                src.truncate()
                                src.write(conf_new)
                        finally:
                            try:
                                os.unlink(tmp.name)
                            except OSError:
                                pass

        if retry:
            log.debug( 'Configuration file (%r) was changed'
                        ' during merge, restarting merge', self.conf_save)
            return self.sync()

########NEW FILE########
__FILENAME__ = portalocker
#-*- coding: utf-8 -*-

import os

if os.name == 'nt':
    # Needs pywin32 to work on Windows (NT, 2K, XP, _not_ /95 or /98)
    try: import win32con, win32file, pywintypes
    except ImportError as err:
        raise ImportError( 'Failed to import pywin32'
            ' extensions (make sure pywin32 is installed correctly) - {}'.format(err) )

    LOCK_EX = win32con.LOCKFILE_EXCLUSIVE_LOCK
    LOCK_SH = 0 # the default
    LOCK_NB = win32con.LOCKFILE_FAIL_IMMEDIATELY
    __overlapped = pywintypes.OVERLAPPED()

    def lock(file, flags):
        hfile = win32file._get_osfhandle(file.fileno())
        win32file.LockFileEx(hfile, flags, 0, 0x7FFFFFFF, __overlapped)

    def unlock(file):
        hfile = win32file._get_osfhandle(file.fileno())
        win32file.UnlockFileEx(hfile, 0, 0x7FFFFFFF, __overlapped)

elif os.name == 'posix':
    from fcntl import lockf, LOCK_EX, LOCK_SH, LOCK_NB, LOCK_UN

    def lock(file, flags):
        lockf(file, flags)

    def unlock(file):
        lockf(file, LOCK_UN)

else:
    raise RuntimeError("PortaLocker only defined for nt and posix platforms")

########NEW FILE########
