__FILENAME__ = bencode
import sys

try:
    unicode
except NameError:
    unicode = str

try:
    long
except NameError:
    long = int

if bytes == str:
    def f(s, *args, **kwargs):
        return str(s)
    bytes = f

class BTFailure(Exception):
    pass

def bytes_index(s, pattern, start):
    if sys.version_info[0] == 2:
        return s.index(pattern, start)

    assert len(pattern) == 1
    for i, e in enumerate(s[start:]):
        if e == ord(pattern):
            return i + start
    raise ValueError('substring not found')

def ord_(s):
    if sys.version_info[0] == 3:
        return ord(s)
    return s

def chr_(s):
    if sys.version_info[0] == 3:
        return chr(s)
    return s

def decode_int(x, f):
    f += 1
    newf = bytes_index(x, 'e', f)
    n = int(x[f:newf])
    if x[f] == ord_('-'):
        if x[f + 1] == ord_('0'):
            raise ValueError
    elif x[f] == ord_('0') and newf != f+1:
        raise ValueError
    return (n, newf+1)

def decode_string(x, f):
    colon = bytes_index(x, ':', f)
    n = int(x[f:colon])
    if x[f] == ord_('0') and colon != f+1:
        raise ValueError
    colon += 1
    return (x[colon:colon+n], colon+n)

def decode_list(x, f):
    r, f = [], f+1
    while x[f] != ord_('e'):
        v, f = decode_func[chr_(x[f])](x, f)
        r.append(v)
    return (r, f + 1)

def decode_dict(x, f):
    r, f = {}, f+1
    while x[f] != ord_('e'):
        k, f = decode_string(x, f)
        r[k], f = decode_func[chr_(x[f])](x, f)
    return (r, f + 1)

decode_func = {}
decode_func['l'] = decode_list
decode_func['d'] = decode_dict
decode_func['i'] = decode_int
decode_func['0'] = decode_string
decode_func['1'] = decode_string
decode_func['2'] = decode_string
decode_func['3'] = decode_string
decode_func['4'] = decode_string
decode_func['5'] = decode_string
decode_func['6'] = decode_string
decode_func['7'] = decode_string
decode_func['8'] = decode_string
decode_func['9'] = decode_string

def bdecode(x):
    try:
        r, l = decode_func[chr_(x[0])](x, 0)
    except (IndexError, KeyError, ValueError):
        raise
        raise BTFailure("not a valid bencoded string")
    if l != len(x):
        raise BTFailure("invalid bencoded value (data after valid prefix)")
    return r

class Bencached(object):

    __slots__ = ['bencoded']

    def __init__(self, s):
        self.bencoded = s

def encode_bencached(x,r):
    r.append(x.bencoded)

def encode_int(x, r):
    r.append(b'i')
    r.append(bytes(str(x), 'ascii'))
    r.append(b'e')

def encode_bool(x, r):
    if x:
        encode_int(1, r)
    else:
        encode_int(0, r)

def encode_string(x, r):
    r.extend((bytes(str(len(x)), 'ascii'), b':', x))

def encode_list(x, r):
    r.append(b'l')
    for i in x:
        encode_func[type(i)](i, r)
    r.append(b'e')

def encode_dict(x,r):
    r.append(b'd')
    ilist = list(x.items())
    ilist.sort()
    for k, v in ilist:
        r.extend((bytes(str(len(k)), 'ascii'), b':', k))
        encode_func[type(v)](v, r)
    r.append(b'e')

encode_func = {}
encode_func[Bencached] = encode_bencached
encode_func[int] = encode_int
encode_func[long] = encode_int
encode_func[str] = encode_string
encode_func[bytes] = encode_string
encode_func[unicode] = encode_string
encode_func[list] = encode_list
encode_func[tuple] = encode_list
encode_func[dict] = encode_dict

try:
    from types import BooleanType
    encode_func[BooleanType] = encode_bool
except ImportError:
    pass

def bencode(x):
    r = []
    encode_func[type(x)](x, r)
    return b''.join(r)

########NEW FILE########
__FILENAME__ = btc
import re, os
import json, sys
import argparse
import fileinput
import atexit
from . import utils
from .btclient import BTClient, BTClientError
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

def finish():
    try:
        sys.stdout.close()
    except:
        pass
    try:
        sys.stderr.close()
    except:
        pass

atexit.register(finish)

encoder = json.JSONEncoder(indent = 2)
decoder = json.JSONDecoder()

def error(msg, die=True):
    sys.stderr.write('%s: error: %s%s' % (os.path.basename(sys.argv[0]), msg, os.linesep))
    if die:
        exit(1)

def warning(msg):
    sys.stderr.write('%s: warning: %s%s' % (os.path.basename(sys.argv[0]), msg, os.linesep))

original_config = {}
env_config_file = os.getenv('BTC_CONFIG_FILE')
env_varname = 'HOME'
if sys.platform.startswith('win') and 'HOME' not in os.environ:
    env_varname = 'HOMEPATH'
home_config_file = os.path.join(os.getenv(env_varname), '.btc')
config_file = env_config_file if env_config_file else home_config_file
config = {}

if os.path.exists(config_file):
    _c = open(config_file, 'r')
    content = _c.read()
    if len(content.strip()) != 0:
        try:
            original_config = decoder.decode(content)
        except:
            msg = 'settings file parse error: %s' % config_file
            msg += '%scontent is:\n%s' % (2 * os.linesep, content)
            error(msg)
    _c.close()

config = dict(original_config)
default = {
    'host': '127.0.0.1',
    'port': 8080,
    'username': 'admin',
    'password': ''
}

for k in default:
    if k not in config:
        config[k] = default[k]

client = BTClient(decoder, config['host'], config['port'],
                  config['username'], config['password'])


def usage(commands):
    app = os.path.basename(sys.argv[0]).split(' ')[0]
    print('usage: %s <command> [<args>]' % app)
    print('')
    print('commands are:')
    for c in sorted(commands.keys()):
        if hasattr(commands[c], '_description'):
            desc = commands[c]._description
        else:
            desc = 'NO _description DEFINED FOR SUBCOMMAND'
        print('    %-10s: %s' % (c, desc))
    print('')
    print("hint: use any command and --help if lost")
    print("hint: try to run 'btc list' to begin")

def list_to_dict(l, key):
    d = {}
    for t in l:
        d[t[key]] = dict(t)
        del d[t[key]][key]
    return d

def dict_to_list(d, key):
    l = []
    for k in d:
        new = dict(d[k])
        new[key] = k
        l.append(new)
    return l

def cmp_to_key(mycmp):
    class K(object):
        def __init__(self, obj, *args):
            self.obj = obj
        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0
        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0
        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0
        def __le__(self, other):
            return mycmp(self.obj, other.obj) <= 0
        def __ge__(self, other):
            return mycmp(self.obj, other.obj) >= 0
        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0
    return K

def cmp(a, b):
    a = a[0]
    b = b[0]
    l = ['name', 'hash', 'sid', 'fileid']
    if a == b:
        return 0
    elif a in l and b not in l:
        return -1
    elif b in l and a not in l:
        return 1
    elif a in l and b in l:
        return l.index(a) < l.index(b) and -1 or 1
    else:
        return a < b and -1 or 1

def ordered_dict(d1):
    vals = sorted([(k, d1[k]) for k in list(d1.keys())], key=cmp_to_key(cmp))
    d2 = OrderedDict(vals)
    return d2

def main():
    commands = {}
    for fp in os.listdir(os.path.dirname(__file__)):
        match = re.match(r'btc_(.*)\.py', fp)

        if not match:
            continue

        name = match.group(1)
        module_name = 'btc_%s' % name
        module = getattr(__import__('btc.%s' % module_name), module_name)
        commands[name] = module

    if len(sys.argv) < 2:
        usage(commands)
        exit(1)

    if sys.argv[1] not in commands:
        error('no such command: %s' % sys.argv[1], False)
        print('')
        usage(commands)
        exit(1)

    module = commands[sys.argv[1]]
    sys.argv[0] += ' %s' % sys.argv[1]
    del sys.argv[1]

    try:
        module.main()
    except utils.HTTPError:
        verb = os.path.exists(config_file) and 'modify the' or 'create a'
        msg = 'connection failed, try to %s settings file%s' % (verb, os.linesep)
        msg += 'note: settings file is: %s%s' % (config_file, os.linesep)
        msg += 'note: current settings are:%s' % os.linesep
        for k in sorted(config.keys()):
            msg += '    %8s: %s%s' % (k, config[k], os.linesep)
        msg += "\nhint: you can use 'btc set key value' to modify settings\n"
        error(msg[0:len(msg) - 1])
    except BTClientError as e:
        error('%s' % e)
    except KeyboardInterrupt:
        pass
    except IOError:
        # might be better to put `raise` when debugging
        pass

    exit(0)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = btclient
import re, os
import json, sys
import argparse
import fileinput
import datetime
from . import utils

try:
    unicode
except NameError:
    unicode = str

class BTClientError(Exception):
    pass

class BTClient:
    def __init__(self, decoder, host='127.0.0.1', port=8080, username='admin', password=''):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.decoder = decoder

    def get_token_argument(self):
        response = self.send_command(root='/gui/token.html', token=False)
        m = re.sub(r"<.*?>", "", response)
        if not m:
            raise BTClientError('token authentification problem')
        return str(m)

    def send_command(self, params='', root='/gui/', token=True,
                     torrent_file=None, username=None, password=None):

        if username is None:
            username = self.username
        if password is None:
            password = self.password

        host = '%s:%s' % (self.host, self.port)
        if token:
            token = self.get_token_argument()
            params = 'token=%s&%s' % (token, params)
        if params:
            url = '%s?%s' % (root, params)
        else:
            url = root
        if torrent_file:
            ret = utils.post_multipart(host, url, [('torrent_file', torrent_file)],
                                        [], username, password)
        else:
            ret = utils.get(host, url, username, password)

        try:
            ret_json = json.loads(ret)
            if 'error' in ret_json:
                raise BTClientError(ret_json['error'])
        except BTClientError:
            raise
        except: # Output might not be JSON
            pass

        return ret

    def list_torrents(self):
        return self.torrent_list(self.send_command('list=1'))

    def add_torrent_url(self, url):
        self.send_command('action=add-url&s=%s' % url)

    def add_torrent_file(self, torrent_file_path):
        torrent_file = open(torrent_file_path, 'rb')
        self.send_command('action=add-file', torrent_file=torrent_file.read())
        torrent_file.close()

    def remove_torrent(self, thash, keep_data=True, keep_torrent=False):
        cmd = None
        if keep_data and keep_torrent:
            cmd = 'action=remove&hash=%s'
        elif keep_data and not keep_torrent:
            cmd = 'action=removetorrent&hash=%s'
        elif keep_torrent and not keep_data:
            cmd = 'action=removedata&hash=%s'
        elif not keep_torrent and not keep_data:
            cmd = 'action=removedatatorrent&hash=%s'
        self.send_command(cmd % thash)

    def stop_torrent(self, thash):
        self.send_command('action=stop&hash=%s' % thash)

    def start_torrent(self, thash):
        self.send_command('action=start&hash=%s' % thash)

    def torrent_files(self, thash, sids={}):
        if isinstance(thash, list):
            if len(thash) == 0:
                return []
            thash = '&hash='.join(thash)
        l = self.send_command('action=getfiles&format=json&hash=%s' % thash)
        return self.files_dict(l, sids)

    def torrent_download_file(self, sid, fileid, name, path='.'):
        cmd = 'sid=%s&file=%d&service=DOWNLOAD&qos=0&disposition=inline' % (sid, fileid)
        content = self.send_command(cmd, root='/proxy', token=False)
        filename = os.path.join(path, name)
        f = open(filename, 'w')
        f.write(content)
        f.close()

    def torrent_stream_url(self, sid, fileid):
        return 'http://%s:%s@%s:%d/proxy?sid=%s&file=%d&service=DOWNLOAD&qos=0&disposition=inline' % \
          (self.username, self.password, self.host, self.port, sid, fileid)


    def _get_state(self, status, remaining):
        TFS_STARTED = 1
        # the torrent is checking its file, to figure out which
        # parts of the files we already have
        TFS_CHECKING = 2
        # start the torrent when the file-check completes
        TFS_START_AFTER_CHECK = 4
        # The files in this torrent have been checked. No need
        # to check them again
        TFS_CHECKED = 8
        # An error ocurred
        TFS_ERROR = 16
        # The torrent is paused. i.e. all transfers are suspended
        TFS_PAUSED = 32
        # Auto managed. uTorrent will automatically start and stop
        # the torrent based on the number of active torrents etc.
        TFS_AUTO = 64
        # The .torrent file has been loaded
        TFS_LOADED = 128
        # the torrent is transforming (usually copying data from
        # another torrent in order to download a similar torrent)
        TFS_TRANSFORMING = 256
        # start the torrent when the transformation completes
        TFS_START_AFTER_TRANSFORM = 512

        if status & TFS_ERROR:
            return "ERROR"
        elif status & TFS_CHECKING:
            return "CHECKED"
        elif status & TFS_TRANSFORMING:
            return "TRANSFORMING"
        else:
            if status & TFS_STARTED:
                if status & TFS_PAUSED:
                    return "PAUSED"
                elif status & TFS_AUTO:
                    return "SEEDING" if remaining == 0 else "DOWNLOADING"
                else:
                    return "SEEDING_FORCED" if remaining == 0 else "DOWNLOADING_FORCED"
            else:
                if status & TFS_PAUSED:
                    return "PAUSED"
                elif remaining == 0:
                    return "QUEUED_SEED" if status & TFS_AUTO else "FINISHED"
                else:
                    return "QUEUED" if status & TFS_AUTO else "STOPPED"


    def torrent_list(self, response):
        response_dict = self.decoder.decode(response)
        response = []
        for torrent_response in response_dict['torrents']:
            torrent_dict = {}
            response.append(torrent_dict)
            torrent_dict['hash'] = str(torrent_response[0].upper())
            torrent_dict['state_code'] = torrent_response[1]
            torrent_dict['name'] = torrent_response[2]
            torrent_dict['size'] = torrent_response[3]
            torrent_dict['progress'] = round(torrent_response[4] / 10., 2)
            torrent_dict['downloaded'] = torrent_response[5]
            torrent_dict['uploaded'] = torrent_response[6]
            torrent_dict['ratio'] = torrent_response[7]
            torrent_dict['upload_rate'] = torrent_response[8]
            torrent_dict['download_rate'] = torrent_response[9]
            torrent_dict['eta'] = torrent_response[10]
            torrent_dict['label'] = torrent_response[11]
            torrent_dict['peers_connected'] = torrent_response[12]
            torrent_dict['peers'] = torrent_response[13]
            torrent_dict['seeds_connected'] = torrent_response[14]
            torrent_dict['seeds'] = torrent_response[15]
            torrent_dict['avail_factor'] = torrent_response[16]
            torrent_dict['order'] = torrent_response[17]
            torrent_dict['remaining'] = torrent_response[18]
            torrent_dict['download_url'] = torrent_response[19]
            torrent_dict['feed_url'] = torrent_response[20]
            torrent_dict['sid'] = torrent_response[22]
            torrent_dict['date_added'] = '%s' % datetime.datetime.fromtimestamp(torrent_response[23])
            torrent_dict['date_completed'] = '%s' % datetime.datetime.fromtimestamp(torrent_response[24])
            torrent_dict['folder'] = torrent_response[26]
            torrent_dict['state'] = self._get_state(torrent_response[1], torrent_dict['remaining'])

        return response

    def files_dict(self, response, sids={}):
        response_dict = self.decoder.decode(response)
        response = list()

        if 'files' not in response_dict:
            return response

        h = None
        for e in response_dict['files']:
            if isinstance(e, unicode):
                h = e.upper()
            elif isinstance(e, list):
                i = 0
                for l in e:
                    f = dict()
                    if h in sids:
                        f['sid'] = sids[h]

                    f['fileid'] = i
                    f['hash'] = h.upper()
                    f['name'] = l[0]
                    f['size'] = l[1]
                    f['downloaded'] = l[2]
                    f['priority'] = l[3]

                    f['streamable'] = l[4]
                    f['encoded_rate'] = l[5]
                    f['duration'] = l[6]
                    f['width'] = l[7]
                    f['height'] = l[8]
                    f['time_to_play'] = l[9]

                    f['progress'] = round(100. * l[2] / l[1], 2)
                    response.append(f)
                    i += 1

        return response

########NEW FILE########
__FILENAME__ = btc_add
import argparse
import time
import hashlib
import os
from . import btclient
from . import utils
from .bencode import bdecode, bencode
from .btc import encoder, decoder, client, error

_description = 'add torrent to client'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('value')
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('-u', '--url', default=False, action='store_true')
    group.add_argument('-f', '--file', default=False, action='store_true')
    args = parser.parse_args()

    if not args.url and not args.file:
        args.file = os.path.exists(args.value)
        args.url = not args.file

    if args.url:
        args.value = utils.httpize(args.value)
        try:
            torrent = utils.get(args.value, utf8=False)
        except utils.HTTPError:
            error('invalid url: %s' % args.value)
        client.add_torrent_url(args.value)
    elif args.file:
        if not os.path.exists(args.value):
            error('no such file: %s' % args.value)
        try:
            f = open(args.value, 'rb')
            torrent = f.read()
            f.close()
        except:
            error('reading file: %s' % args.value)
        client.add_torrent_file(args.value)

    added = None

    try:
        decoded = bdecode(torrent)
        encoded = bencode(decoded[b'info'])
    except:
        error('invalid torrent file')

    h = hashlib.sha1(encoded).hexdigest().upper()
    while not added:
        l = client.list_torrents()
        for t in l:
            if t['hash'] == h:
                added = t
                break
        time.sleep(1)

    print(encoder.encode([added]))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = btc_download
import argparse
import sys
import os
from .btc import encoder, decoder, error, warning, list_to_dict, dict_to_list, client, config

_description = 'download torrent file locally'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--directory', default='.')
    parser.add_argument('-o', '--output', default=None)
    parser.add_argument('-w', '--windows', default=False, action='store_true',
                        help='client is running on windows')
    args = parser.parse_args()

    if not args.windows and 'windows' in config:
        args.windows = config['windows']

    if sys.stdin.isatty():
        parser.error('no input, pipe another btc command output into this command')
    files = sys.stdin.read()

    if len(files.strip()) == 0:
        exit(1)

    try:
        files = decoder.decode(files)
    except ValueError:
        error('unexpected input: %s' % files)

    if not os.path.exists(args.directory):
        error('no such directory: %s' % args.directory)

    if args.output and len(files) > 1:
        if sys.stdout.isatty():
            warning('multiple files: --output is ignored')

    for f in files:
        if 'fileid' not in f:
            warning('ignoring non-file entry: %s' % f['name'])
            continue

        if args.windows and os.sep == '/':
            f['name'] = f['name'].replace('\\', '/')
        elif not args.windows and os.sep == '\\':
            f['name'] = f['name'].replace('/', '\\')

        filename = args.output or f['name']

        complete = float(f['downloaded']) / float(f['size']) * 100
        if sys.stdout.isatty() and complete < 100.0:
            print('skipping incomplete file: %s' % f['name'])
            continue

        if args.output and len(files) > 1:
            filename = f['name']
        if args.output and len(files) == 1:
            directory = os.path.dirname(os.path.join(args.directory, args.output))
            if not os.path.exists(directory):
                error('no such directory: %s' % directory)
        else:
            directory = os.path.dirname(os.path.join(args.directory, f['name']))
            if not os.path.exists(directory):
                os.makedirs(directory)

        if sys.stdout.isatty():
            print('downloading: %s' % os.path.join(args.directory, filename))

        client.torrent_download_file(f['sid'], f['fileid'], filename, args.directory)

    if not sys.stdout.isatty():
        l = client.list_torrents()
        print(encoder.encode(l))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = btc_files
import argparse
import sys
import fnmatch
import os
from .btc import encoder, decoder, error, warning, client, ordered_dict, config

_description = 'list files of torrents'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('name', nargs='?', default=None)
    parser.add_argument('-s', '--case-sensitive', default=False, action="store_true")
    parser.add_argument('-w', '--windows', default=False, action='store_true',
                        help='bittorrent client is running on windows')
    args = parser.parse_args()

    if not args.windows and 'windows' in config:
        args.windows = config['windows']

    if sys.stdin.isatty():
        torrents = sorted(client.list_torrents(), key=lambda x: x['name'].lower())
    else:
        torrents = sys.stdin.read()

        if len(torrents.strip()) == 0:
            exit(1)

        try:
            torrents = decoder.decode(torrents)
        except ValueError:
            error('unexpected input: %s' % torrents)

    sids = {}
    hashes = []
    for t in torrents:
        if 'hash' not in t or 'sid' not in t or 'fileid' in t:
            warning('ignoring non-torrent entry')
            continue
        sids[t['hash']] = t['sid']
        hashes.append(t['hash'])

    if len(hashes) == 0:
        print(encoder.encode([]))
        exit(0)

    files = client.torrent_files(hashes, sids)
    matched = []
    if args.name:
        for f in files:
            def case(x):
                if args.case_sensitive:
                    return x
                return x.lower()

            if fnmatch.fnmatch(case(f['name']), case(args.name)):
                matched.append(f)
    else:
        matched = files

    for f in matched:
        if args.windows and os.sep == '/':
            f['name'] = f['name'].replace('\\', '/')
        elif not args.windows and os.sep == '\\':
            f['name'] = f['name'].replace('/', '\\')

    matched = sorted(matched, key=lambda x: x['name'].lower())
    print(encoder.encode([ordered_dict(d) for d in matched]))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = btc_filter
import argparse
import fnmatch
import sys
import re
from .btc import encoder, decoder, error

try:
    unicode
except NameError:
    unicode = str

_description = 'filter elements of a list'

# TODO: add support for dates (date_added, date_completed)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--nth', metavar='N',
                        help='select the Nth entry (1-based)',
                        type=int, default=None)
    parser.add_argument('-f', '--first', metavar='N',
                        help='select the N first entires',
                        type=int, default=None)
    parser.add_argument('-v', '--invert-match', default=False, action='store_true',
                        help='select all entries but the ones that match')
    parser.add_argument('-k', '--key', default='name',
                        help='change the key used for the match (default is name)')
    parser.add_argument('-s', '--case-sensitive', default=False, action='store_true')

    parser.add_argument('value', metavar='VALUE', nargs='?', default=None,
                        help='string or numerical value to match')

    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('-e', '--numeric-equals', default=False, action='store_true')
    group.add_argument('-d', '--numeric-differs', default=False, action='store_true')
    group.add_argument('-G', '--greater', default=False, action='store_true')
    group.add_argument('-g', '--greater-or-equal', default=False, action='store_true')
    group.add_argument('-l', '--less-or-equal', default=False, action='store_true')
    group.add_argument('-L', '--less', default=False, action='store_true')
    group.add_argument('-T', '--true', default=False, action='store_true')
    group.add_argument('-F', '--false', default=False, action='store_true')

    args = parser.parse_args()

    if (args.value is not None) and (args.false or args.true):
        parser.error('cannot specify value for boolean matching')

    if sys.stdin.isatty():
        parser.error('no input, pipe another btc command output into this command')
    l = sys.stdin.read()

    if len(l.strip()) == 0:
        exit(1)

    try:
        l = decoder.decode(l)
    except ValueError:
        error('unexpected input: %s' % l)

    new = list()
    for o in l:
        try:
            if args.numeric_equals:
                if float(o[args.key]) == float(args.value):
                    new.append(o)
            elif args.numeric_differs:
                if float(o[args.key]) != float(args.value):
                    new.append(o)
            elif args.greater:
                if float(o[args.key]) > float(args.value):
                    new.append(o)
            elif args.greater_or_equal:
                if float(o[args.key]) >= float(args.value):
                    new.append(o)
            elif args.less_or_equal:
                if float(o[args.key]) <= float(args.value):
                    new.append(o)
            elif args.less:
                if float(o[args.key]) < float(args.value):
                    new.append(o)
            elif args.true:
                if bool(o[args.key]):
                    new.append(o)
            elif args.false:
                if not bool(o[args.key]):
                    new.append(o)
            elif args.value is not None:
                def case(x):
                    if args.case_sensitive:
                        return x
                    return x.lower()
                if fnmatch.fnmatch(case(unicode(o[args.key])), case(unicode(args.value))):
                    new.append(o)
            else:
                new.append(o)
        except KeyError:
            pass
        except ValueError as e:
            error('value error: %s' % e)

    if args.first is not None:
        new = new[0:min(args.first,len(new))]

    if args.nth is not None:
        new = [new[args.nth - 1]]

    if args.invert_match:
        new = [o for o in l if o not in new]

    print(encoder.encode(new))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = btc_list
import argparse
import fnmatch
from .btc import encoder, decoder, client, ordered_dict

_description = 'list client torrents'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('name', nargs='?', default=None)
    parser.add_argument('-s', '--case-sensitive', default=False, action="store_true")
    args = parser.parse_args()
    l = sorted(client.list_torrents(), key=lambda x: x['name'].lower())
    if args.name:
        def case(x):
            if args.case_sensitive:
                return x
            return x.lower()
        l = [x for x in l if fnmatch.fnmatch(case(x['name']), case(args.name))]

    print(encoder.encode([ordered_dict(d) for d in l]))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = btc_reduce
import argparse
import fnmatch
import sys
import os
import re
import collections
from .btc import encoder, decoder, error, ordered_dict

_description = 'show values and items'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('key', metavar='KEY', nargs='?', default=None,
                        help='key associated with values to reduce')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--min', action='store_true', default=None)
    group.add_argument('--max', action='store_true', default=None)
    group.add_argument('--sum', action='store_true', default=None)
    group.add_argument('--mean', action='store_true', default=None)
    group.add_argument('--dist', action='store_true', default=None)
    group.add_argument('--count', action='store_true', default=None)
    group.add_argument('--unique', action='store_true', default=None)
    group.add_argument('--join', metavar='STR', default=None, help='string to use for a join')
    args = parser.parse_args()

    if sys.stdin.isatty():
        parser.error('no input, pipe another btc command output into this command')
    l = sys.stdin.read()

    if len(l.strip()) == 0:
        exit(1)

    try:
        l = decoder.decode(l)
    except ValueError:
        error('unexpected input: %s' % l)

    if not isinstance(l, list):
        error('input must be a list')
    elif args.key and not all(isinstance(x, dict) for x in l):
        error('list items must be dictionaries when specifying a key')

    out = []
    for i, e in enumerate(l):
        try:
            out.append(e[args.key] if args.key else e)
        except KeyError:
            error('key not found: {}'.format(args.key))

    f = None
    if args.min:
        f = min
    elif args.max:
        f = max
    elif args.sum:
        if not all(isinstance(x, float) or isinstance(x, int) for x in out):
            error('sum requires numerical values')
        f = sum
    elif args.mean:
        if not all(isinstance(x, float) or isinstance(x, int) for x in out):
            error('mean requires numerical values')
        f = lambda l: float(sum(l)) / len(l) if len(l) > 0 else float('nan')
    elif args.dist:
        f = lambda l: dict(collections.Counter(l).most_common())
    elif args.count:
        f = lambda l: len(l)
    elif args.unique:
        f = lambda l: list(set(l))
    elif args.join is not None:
        f = lambda l: args.join.join(l)
    else:
        f = lambda l: '\n'.join(l)

    if args.unique or args.dist:
        print(encoder.encode(f(out)))
    else:
        print(f(out))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = btc_remove
import argparse
import sys
import time
from .btc import encoder, decoder, error, list_to_dict, dict_to_list, client

_description = 'remove torrent'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--drop-data', default=False, action="store_true")
    parser.add_argument('-k', '--keep-torrent', default=False, action="store_true")
    args = parser.parse_args()

    if sys.stdin.isatty():
        parser.error('no input, pipe another btc command output into this command')
    torrents = sys.stdin.read()

    if len(torrents.strip()) == 0:
        exit(1)

    try:
        torrents = decoder.decode(torrents)
    except ValueError:
        error('unexpected input: %s' % torrents)

    hashes = [t['hash'] for t in torrents]
    for h in hashes:
        client.remove_torrent(h, keep_data=not args.drop_data,
                              keep_torrent=args.keep_torrent)

    while True:
        l = client.list_torrents()
        all_removed = True
        for t in l:
            if t['hash'] in hashes:
                all_removed = False
                break
        if all_removed:
            break
        time.sleep(1)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = btc_select
import argparse
import fnmatch
import sys
import os
import re
from .btc import encoder, decoder, error, ordered_dict

_description = 'select some values'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('keys', metavar='KEY', nargs='+', default=None,
                        help='keys associated with values to be selected')
    args = parser.parse_args()

    if sys.stdin.isatty():
        parser.error('no input, pipe another btc command output into this command')
    l = sys.stdin.read()

    if len(l.strip()) == 0:
        exit(1)

    try:
        l = decoder.decode(l)
    except ValueError:
        error('unexpected input: %s' % l)

    if not isinstance(l, list):
        error('input must be a list')
    elif not all(isinstance(x, dict) for x in l):
        error('list items must be dictionaries')

    out = []
    for i, e in enumerate(l):
        e_out = {}
        for key in args.keys:
            try:
                if len(args.keys) == 1:
                    e_out = e[key]
                else:
                    e_out[key] = e[key]
            except KeyError:
                error('key not found: {}'.format(key))
        out.append(e_out)

    if len(args.keys) > 1:
        print(encoder.encode([ordered_dict(d) for d in out]))
    else:
        print(encoder.encode([e for e in out]))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = btc_set
import argparse
import sys
import os
from .btc import encoder, decoder, error, config_file, original_config

_description = 'manage settings file'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('key')
    parser.add_argument('value', nargs='?', default=None)
    parser.add_argument('-f', '--force-quotes', default=False, action="store_true")
    parser.add_argument('-d', '--delete', default=False, action="store_true")
    args = parser.parse_args()

    config = original_config

    if args.delete:
        if args.value:
            error('value was given but delete was requested')

        if args.key not in config:
            error('not in settings file: %s' % args.key)
        del config[args.key]
    else:
        if args.value is None:
            error('value is missing')

        if not args.force_quotes:
            try:
                args.value = decoder.decode(args.value)
            except ValueError:
                pass

        config[args.key] = args.value

    f = open(config_file, 'w')
    f.write(encoder.encode(config))
    f.close()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = btc_show
import argparse
import fnmatch
import sys
import os
import re
from .btc import encoder, decoder, error, ordered_dict

_description = 'show values and items'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('keys', metavar='KEY', nargs='*', default=None,
                        help='keys associated with values to be printed')
    parser.add_argument('-k', '--show-keys', action='store_true', default=False)
    parser.add_argument('-s', '--separator', default=' ')
    parser.add_argument('-S', '--entry-separator', default='')
    parser.add_argument('-q', '--quote', default='')
    args = parser.parse_args()

    if sys.stdin.isatty():
        parser.error('no input, pipe another btc command output into this command')
    l = sys.stdin.read()

    if len(l.strip()) == 0:
        exit(1)

    try:
        l = decoder.decode(l)
    except ValueError:
        error('unexpected input: %s' % l)

    if isinstance(l, dict):
        l = [l]

    if not isinstance(l, list):
        error('input must be a list')
    elif args.keys and not all(isinstance(x, dict) for x in l):
        error('list items must be dictionaries when specifying a key')

    for i, e in enumerate(l):
        if isinstance(e, dict):
            keys = args.keys or ordered_dict(e).keys()
            if i != 0 and len(keys) > 1:
                print(args.entry_separator)
            for key in keys:
                s = ''
                if args.show_keys:
                    s += '{0}{1}{0}{2}'.format(args.quote, key, args.separator)
                try:
                    print('{0}{1}{2}{1}'.format(s, args.quote, e[key]))
                except KeyError:
                    error('key not found: {}'.format(key))
        else:
            print(e)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = btc_sort
import argparse
import sys
from .btc import encoder, decoder, error, list_to_dict, dict_to_list, ordered_dict

try:
    unicode
except NameError:
    unicode = str

_description = 'sort elements of a list'

# TODO: add support for dates (date_added, date_completed)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-k', '--key', default='name')
    parser.add_argument('-s', '--case-sensitive', default=False, action='store_true')
    parser.add_argument('-r', '--reverse', default=False, action='store_true')
    args = parser.parse_args()

    if sys.stdin.isatty():
        parser.error('no input, pipe another btc command output into this command')
    l = sys.stdin.read()

    if len(l.strip()) == 0:
        exit(1)

    try:
        l = decoder.decode(l)
    except ValueError:
        error('unexpected input: %s' % l)

    def key(x):
        key = x[args.key]
        if ((isinstance(x[args.key], str)
             or isinstance(x[args.key], unicode))
            and not args.case_sensitive):
            return key.lower()
        return key

    l = sorted(l, key=key)

    if args.reverse:
        l = list(reversed(l))

    print(encoder.encode([ordered_dict(d) for d in l]))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = btc_start
import argparse
import sys
import time
from .btc import encoder, decoder, error, list_to_dict, dict_to_list, client

_description = 'start torrent'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--delay', default=0, type=int)
    args = parser.parse_args()

    if sys.stdin.isatty():
        parser.error('no input, pipe another btc command output into this command')
    torrents = sys.stdin.read()

    if len(torrents.strip()) == 0:
        exit(1)

    try:
        torrents = decoder.decode(torrents)
    except ValueError:
        error('unexpected input: %s' % torrents)

    time.sleep(args.delay)

    hashes = [t['hash'] for t in torrents]
    for h in hashes:
        client.start_torrent(h)

    while True:
        d = list_to_dict(client.list_torrents(), 'hash')
        all_started = True
        for h in d:
            if h not in hashes:
                continue
            if d[h]['state'] not in ('DOWNLOADING', 'DOWNLOADING_FORCED', 'SEEDING',
                                     'SEEDING_FORCED', 'QUEUED_SEED'):
                all_started = False
                break
        if all_started:
            break
        time.sleep(1)


    if not sys.stdout.isatty():
        d = list_to_dict(client.list_torrents(), 'hash')
        d = dict((h, d[h]) for h in hashes if h in d)
        print(encoder.encode(dict_to_list(l)))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = btc_stop
import argparse
import sys
import time
from .btc import encoder, decoder, error, list_to_dict, dict_to_list, client

_description = 'stop torrent'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--delay', type=int, default=0)
    args = parser.parse_args()

    if sys.stdin.isatty():
        parser.error('no input, pipe another btc command output into this command')
    torrents = sys.stdin.read()

    if len(torrents.strip()) == 0:
        exit(1)

    try:
        torrents = decoder.decode(torrents)
    except ValueError:
        error('unexpected input: %s' % torrents)

    time.sleep(args.delay)

    hashes = [t['hash'] for t in torrents]
    for h in hashes:
        client.stop_torrent(h)

    while True:
        d = list_to_dict(client.list_torrents(), 'hash')
        all_stopped = True
        for h in d:
            if h not in hashes:
                continue
            if d[h]['state'] not in ('STOPPED', 'FINISHED'):
                all_stopped = False
                break
        if all_stopped:
            break
        time.sleep(1)

    if not sys.stdout.isatty():
        d = list_to_dict(client.list_torrents(), 'hash')
        d = dict((h, d[h]) for h in hashes if h in d)
        print(encoder.encode(dict_to_list(l)))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = btc_stream
import subprocess
import argparse
import sys
import re
import os
from .btc import encoder, decoder, error, warning, list_to_dict, dict_to_list, client

_description = 'stream torrent file locally'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--command', default=None)
    parser.add_argument('-t', '--together', default=False, action='store_true')
    args = parser.parse_args()

    if args.command:
        args.command = re.sub(r'[ \t]+', ' ', args.command)
    else:
        warning('no stream command specified, outputing streaming links')

    if sys.stdin.isatty():
        parser.error('no input, pipe another btc command output into this command')
    files = sys.stdin.read()

    if len(files.strip()) == 0:
        exit(1)

    try:
        files = decoder.decode(files)
    except ValueError:
        error('unexpected input: %s' % files)

    if args.together:
        call = []
        if args.command:
            call = args.command.split(' ')
        for f in files:
            if 'fileid' not in f:
                warning('ignoring non-file entry: %s' % f['name'])
                continue
            call.append(client.torrent_stream_url(f['sid'], f['fileid']))
        if sys.stdout.isatty() and args.command:
            print('running: %s' % ' '.join(call))
            try:
                subprocess.call(call)
            except OSError as e:
                error(e.strerror)
        elif sys.stdout.isatty():
            for (ff, url) in zip([f['name'] for f in files if 'fileid' in f], call):
                sys.stdout.write('%s' % url)
            print('')
    else:
        for f in files:
            if 'fileid' not in f:
                warning('ignoring non-file entry: %s' % f['name'])
                continue
            call = []
            if args.command:
                call = args.command.split(' ')
            url = client.torrent_stream_url(f['sid'], f['fileid'])
            call.append(url)
            if sys.stdout.isatty() and args.command:
                print('running: %s' % ' '.join(call))
                try:
                    subprocess.call(call)
                except OSError as e:
                    error(e.strerror)
            elif sys.stdout.isatty():
                print('%s: %s' % (f['name'], url))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = btc_wait
import argparse
import sys
import time
from . import btclient
from .btc import encoder, decoder, error, list_to_dict, dict_to_list, client

_description = 'wait for torrents or files download to complete'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--refresh-s', default=1)
    args = parser.parse_args()

    if sys.stdin.isatty():
        torrents = sorted(client.list_torrents(), key=lambda x: x['name'].lower())
    else:
        torrents = sys.stdin.read()

        if len(torrents.strip()) == 0:
            exit(1)

        try:
            torrents = decoder.decode(torrents)
        except ValueError:
            error('unexpected input: %s' % torrents)

    hashes = [t['hash'] for t in torrents if 'fileid' not in t]
    fileids = [(t['fileid'], t['hash'], t['sid']) for t in torrents
               if 'fileid' in t]

    while True:
        if len(fileids) == 0 and len(hashes) == 0:
            break

        d = list_to_dict(client.list_torrents(), 'hash')

        all_finished = True

        for h in hashes:
            if d[h]['state'] not in ('FINISHED', 'SEEDING', 'SEEDING_FORCED', 'QUEUED_SEED'):
                all_finished = False
                break

        files = client.torrent_files([f[1] for f in fileids],
                                     dict([(f[1], f[2]) for f in fileids]))

        files_hashes = set([f['hash'] for f in files])
        files_dict = dict([(h, dict()) for h in files_hashes])
        for f in files:
            files_dict[f['hash']][f['fileid']] = f

        for (fileid, h, sid) in fileids:
            f = files_dict[h][fileid]
            if float(f['downloaded']) < float(f['size']):
                all_finished = False
                break

        if all_finished:
            break
        time.sleep(args.refresh_s)

    if not sys.stdout.isatty():
        d = list_to_dict(client.list_torrents(), 'hash')
        d = dict((h, d[h]) for h in hashes if h in d)
        print(encoder.encode(dict_to_list(d)))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = utils
import httplib2, mimetypes, base64, socket
import re

try:
    basestring
except NameError:
    basestring = str

if bytes == str:
    def f(s, *args, **kwargs):
        return str(s)
    bytes = f

class Cookie (dict):
    pattern = re.compile(r'(.*?)=(.*?)(?:;\s*|$)')

    def __init__(self, wevs={}):
        if isinstance(wevs, basestring):
            wevs = self.pattern.findall(wevs)
        super(Cookie, self).__init__(wevs)

    def __str__(self):
        return '; '.join('{0}={1}'.format(k,v) for k,v in self.items())

    def update(self, new):
        super(Cookie, self).update(Cookie(new))

class HTTPError (Exception):
    pass

cookie = Cookie()
timeout = 2

def encode_multipart_formdata(fields, files):
    """
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return (content_type, body) ready for httplib.HTTP instance
    """
    BOUNDARY = b'----------ThIs_Is_tHe_bouNdaRY_$'
    CRLF = b'\r\n'
    L = []
    for (key, value) in fields:
        L.append(b'--' + BOUNDARY)
        L.append(bytes('Content-Disposition: form-data; name="%s"' % key, 'ascii'))
        L.append(b'')
        L.append(value)
    for (key, filename, value) in files:
        L.append(b'--' + BOUNDARY)
        L.append(bytes('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename), 'ascii'))
        L.append(bytes('Content-Type: %s' % mimetypes.guess_type(filename)[0] or 'application/octet-stream', 'ascii'))
        L.append(b'')
        L.append(value)
    L.append(b'--' + BOUNDARY + b'--')
    L.append(b'')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY.decode('ascii')
    return content_type, body

def httpize(url):
    if not url.startswith('http'):
        return 'http://{0}'.format(url)
    return url

def make_request(http, *args, **kwargs):
    try:
        return http.request(*args, **kwargs)
    except httplib2.ServerNotFoundError:
        raise HTTPError('404')
    except (socket.timeout, socket.error):
        raise HTTPError('host does not answer')

def post_multipart(host, selector, fields, files, username, password):
    """
    Post fields and files to an http host as multipart/form-data.
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return the server's response page.
    """
    base64string = base64.encodestring(bytes('%s:%s' % (username, password), 'ascii'))[:-1].decode('ascii')
    content_type, body = encode_multipart_formdata(fields, files)
    h = httplib2.Http(timeout=timeout)
    headers = { 'Authorization': 'Basic %s' % base64string,
                'Content-Type': content_type,
                'Content-Length': str(len(body)),
                'Cookie': str(cookie) }

    host = httpize(host)
    response, content = make_request(h, host + selector, method='POST', body=body, headers=headers)

    if response['status'] == '200' and 'set-cookie' in response:
        cookie.update(response['set-cookie'])
    elif response['status'] != '200':
        raise HTTPError(response['status'])

    return content.decode('utf-8')

def get(host, selector="", username=None, password=None, utf8=True):
    if username:
        base64string = base64.encodestring(bytes('%s:%s' % (username, password), 'ascii'))[:-1].decode('ascii')
    h = httplib2.Http(timeout=timeout)
    if username:
        headers = { 'Authorization': 'Basic %s' % base64string,
                    'Cookie': str(cookie) }
    else:
        headers = {}

    host = httpize(host)
    response, content = make_request(h, host + selector, headers=headers)

    if response['status'] == '200' and 'set-cookie' in response:
        cookie.update(response['set-cookie'])
    elif response['status'] != '200':
        raise HTTPError(response['status'])

    if utf8:
        return content.decode('utf-8')
    return content

########NEW FILE########
