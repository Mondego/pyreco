__FILENAME__ = cli
"""Command line interface / frontend for skypipe

This module contains an argparse configuration and handles endpoint
loading for now. Ultimately it just runs the client.
"""
import sys
import os
import argparse
import atexit
import runpy

from dotcloud.ui.cli import CLI as DotCloudCLI

import skypipe
from skypipe import client
from skypipe import cloud

def fix_zmq_exit():
    """
    Temporary fix until master of pyzmq is released
    See: https://github.com/zeromq/pyzmq/pull/265
    """
    import zmq
    ctx = zmq.Context.instance()
    ctx.term()
atexit.register(fix_zmq_exit)

if sys.platform == 'win32':
    appdata = os.path.join(os.environ.get('APPDATA'), "skypipe")
else:
    appdata = os.path.expanduser(os.path.join("~",".{0}".format("skypipe")))
appconfig = os.path.join(appdata, "config")

def load_satellite_endpoint():
    """loads any cached endpoint data"""
    pass    

def save_satellite_endpoint(endpoint):
    """caches endpoint data in config"""
    pass

def get_parser():
    parser = argparse.ArgumentParser(prog='skypipe', epilog="""
Use --setup to find or deploy a satellite in the sky. You can configure
skypipe to use a custom satellite with the environment variable SATELLITE.
Example: SATELLITE=tcp://12.0.0.1:1234
    """.strip())
    parser.add_argument('name', metavar='NAME', type=str, nargs='?',
            help='use a named skypipe', default='')
    parser.add_argument('--version', action='version', 
            version='%(prog)s {0}'.format(skypipe.VERSION))
    parser.add_argument('--setup', action='store_const',
            const=True, default=False,
            help='setup account and satellite')
    parser.add_argument('--check', action='store_const',
            const=True, default=False,
            help='check if satellite is online')
    parser.add_argument('--reset', action='store_const',
            const=True, default=False,
            help='destroy any existing satellite')
    parser.add_argument('--satellite', action='store',
            default=None, metavar='PORT',
            help='manually run a satellite on PORT')
    return parser

def run():
    parser = get_parser()
    args = parser.parse_args()

    dotcloud_endpoint = os.environ.get('DOTCLOUD_API_ENDPOINT', 
            'https://rest.dotcloud.com/v1')
    cli = DotCloudCLI(endpoint=dotcloud_endpoint)

    if args.setup:
        cloud.setup(cli)
    elif args.reset:
        cloud.destroy_satellite(cli)
        cli.success("Skypipe system reset. Now run `skypipe --setup`")
    elif args.satellite:
        os.environ['PORT_ZMQ'] = args.satellite
        runpy.run_path('/'.join([os.path.dirname(__file__), 'satellite', 'server.py']))
    else:
        skypipe_endpoint = os.environ.get("SATELLITE", load_satellite_endpoint())
        skypipe_endpoint = skypipe_endpoint or cloud.discover_satellite(cli, deploy=False)
        if not skypipe_endpoint:
            cli.die("Unable to locate satellite. Please run `skypipe --setup`")
        save_satellite_endpoint(skypipe_endpoint)

        if args.check:
            cli.success("Skypipe is ready for action")
        else:
            client.run(skypipe_endpoint, args.name)

########NEW FILE########
__FILENAME__ = client
"""Skypipe client

This contains the client implementation for skypipe, which operates in
two modes:

1. Input mode: STDIN -> Skypipe satellite
2. Output mode: Skypipe satellite -> STDOUT

The satellite is a server managed by the cloud module. They use ZeroMQ
to message with each other. They use a simple protocol on top of ZeroMQ
using multipart messages. The first part is the header, which identifies
the name and version of the protocol being used. The second part is
always a command. Depending on the command there may be more parts.
There are only four commands as of 0.1:

1. HELLO: Used to ping the server. Server should HELLO back.
2. DATA <pipe> <data>: Send/recv one piece of data (usually a line) for pipe
3. LISTEN <pipe>: Start listening for data on a pipe
4. UNLISTEN <pipe>: Stop listening for data on a pipe

The pipe parameter is the name of the pipe. It can by an empty string to
represent the default pipe. 

EOF is an important concept for skypipe. We represent it with a DATA
command using an empty string for the data.
"""
import os
import sys
import time

import zmq

ctx = zmq.Context.instance()

SP_HEADER = "SKYPIPE/0.1"
SP_CMD_HELLO = "HELLO"
SP_CMD_DATA = "DATA"
SP_CMD_LISTEN = "LISTEN"
SP_CMD_UNLISTEN = "UNLISTEN"
SP_DATA_EOF = ""

def sp_msg(cmd, pipe=None, data=None):
    """Produces skypipe protocol multipart message"""
    msg = [SP_HEADER, cmd]
    if pipe is not None:
        msg.append(pipe)
    if data is not None:
        msg.append(data)
    return msg

def check_skypipe_endpoint(endpoint, timeout=10):
    """Skypipe endpoint checker -- pings endpoint

    Returns True if endpoint replies with valid header,
    Returns False if endpoint replies with invalid header,
    Returns None if endpoint does not reply within timeout
    """
    socket = ctx.socket(zmq.DEALER)
    socket.linger = 0
    socket.connect(endpoint)
    socket.send_multipart(sp_msg(SP_CMD_HELLO))
    timeout_time = time.time() + timeout
    while time.time() < timeout_time:
        reply = None
        try:
            reply = socket.recv_multipart(zmq.NOBLOCK)
            break
        except zmq.ZMQError:
            time.sleep(0.1)
    socket.close()
    if reply:
        return str(reply.pop(0)) == SP_HEADER


def stream_skypipe_output(endpoint, name=None):
    """Generator for reading skypipe data"""
    name = name or ''
    socket = ctx.socket(zmq.DEALER)
    socket.connect(endpoint)
    try:
        socket.send_multipart(sp_msg(SP_CMD_LISTEN, name))

        while True:
            msg = socket.recv_multipart()
            try:
                data = parse_skypipe_data_stream(msg, name)
                if data:
                    yield data
            except EOFError:
                raise StopIteration()

    finally:
        socket.send_multipart(sp_msg(SP_CMD_UNLISTEN, name))
        socket.close()

def parse_skypipe_data_stream(msg, for_pipe):
    """May return data from skypipe message or raises EOFError"""
    header = str(msg.pop(0))
    command = str(msg.pop(0))
    pipe_name = str(msg.pop(0))
    data = str(msg.pop(0))
    if header != SP_HEADER: return
    if pipe_name != for_pipe: return
    if command != SP_CMD_DATA: return
    if data == SP_DATA_EOF:
        raise EOFError()
    else:
        return data

def skypipe_input_stream(endpoint, name=None):
    """Returns a context manager for streaming data into skypipe"""
    name = name or ''
    class context_manager(object):
        def __enter__(self):
            self.socket = ctx.socket(zmq.DEALER)
            self.socket.connect(endpoint)
            return self

        def send(self, data):
            data_msg = sp_msg(SP_CMD_DATA, name, data)
            self.socket.send_multipart(data_msg)

        def __exit__(self, *args, **kwargs):
            eof_msg = sp_msg(SP_CMD_DATA, name, SP_DATA_EOF)
            self.socket.send_multipart(eof_msg)
            self.socket.close()

    return context_manager()

def stream_stdin_lines():
    """Generator for unbuffered line reading from STDIN"""
    stdin = os.fdopen(sys.stdin.fileno(), 'r', 0)
    while True:
        line = stdin.readline()
        if line:
            yield line
        else:
            break

def run(endpoint, name=None):
    """Runs the skypipe client"""
    try:
        if os.isatty(0):
            # output mode
            for data in stream_skypipe_output(endpoint, name):
                sys.stdout.write(data)
                sys.stdout.flush()

        else:
            # input mode
            with skypipe_input_stream(endpoint, name) as stream:
                for line in stream_stdin_lines():
                    stream.send(line)

    except KeyboardInterrupt:
        pass

########NEW FILE########
__FILENAME__ = cloud
"""Cloud satellite manager

Here we use dotcloud to lookup or deploy the satellite server. This also
means we need dotcloud credentials, so we get those if we need them.
Most of this functionality is pulled from the dotcloud client, but is
modified and organized to meet our needs. This is why we pass around and
work with a cli object. This is the CLI object from the dotcloud client.
"""
import time
import os
import os.path
import socket
import sys
import subprocess
import threading
from StringIO import StringIO

import dotcloud.ui.cli
from dotcloud.ui.config import GlobalConfig, CLIENT_KEY, CLIENT_SECRET
from dotcloud.client import RESTClient
from dotcloud.client.auth import NullAuth
from dotcloud.client.errors import RESTAPIError

from skypipe import client

APPNAME = "skypipe0"
satellite_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'satellite')

# This is a monkey patch to silence rsync output
class FakeSubprocess(object):
    @staticmethod
    def call(*args, **kwargs):
        kwargs['stdout'] = subprocess.PIPE
        return subprocess.call(*args, **kwargs)
dotcloud.ui.cli.subprocess = FakeSubprocess

def wait_for(text, finish=None, io=None):
    """Displays dots until returned event is set"""
    if finish:
        finish.set()
        time.sleep(0.1) # threads, sigh
    if not io:
        io = sys.stdout
    finish = threading.Event()
    io.write(text)
    def _wait():
        while not finish.is_set():
            io.write('.')
            io.flush()
            finish.wait(timeout=1)
        io.write('\n')
    threading.Thread(target=_wait).start()
    return finish


def lookup_endpoint(cli):
    """Looks up the application endpoint from dotcloud"""
    url = '/applications/{0}/environment'.format(APPNAME)
    environ = cli.user.get(url).item
    port = environ['DOTCLOUD_SATELLITE_ZMQ_PORT']
    host = socket.gethostbyname(environ['DOTCLOUD_SATELLITE_ZMQ_HOST'])
    return "tcp://{0}:{1}".format(host, port)


def setup_dotcloud_account(cli):
    """Gets user/pass for dotcloud, performs auth, and stores keys"""
    client = RESTClient(endpoint=cli.client.endpoint)
    client.authenticator = NullAuth()
    urlmap = client.get('/auth/discovery').item
    username = cli.prompt('dotCloud email')
    password = cli.prompt('Password', noecho=True)
    credential = {'token_url': urlmap.get('token'),
        'key': CLIENT_KEY, 'secret': CLIENT_SECRET}
    try:
        token = cli.authorize_client(urlmap.get('token'), credential, username, password)
    except Exception as e:
        cli.die('Username and password do not match. Try again.')
    token['url'] = credential['token_url']
    config = GlobalConfig()
    config.data = {'token': token}
    config.save()
    cli.global_config = GlobalConfig()  # reload
    cli.setup_auth()
    cli.get_keys()

def setup(cli):
    """Everything to make skypipe ready to use"""
    if not cli.global_config.loaded:
        setup_dotcloud_account(cli)
    discover_satellite(cli)
    cli.success("Skypipe is ready for action")


def discover_satellite(cli, deploy=True, timeout=5):
    """Looks to make sure a satellite exists, returns endpoint

    First makes sure we have dotcloud account credentials. Then it looks
    up the environment for the satellite app. This will contain host and
    port to construct an endpoint. However, if app doesn't exist, or
    endpoint does not check out, we call `launch_satellite` to deploy,
    which calls `discover_satellite` again when finished. Ultimately we
    return a working endpoint. If deploy is False it will not try to
    deploy.
    """
    if not cli.global_config.loaded:
        cli.die("Please setup skypipe by running `skypipe --setup`")

    try:
        endpoint = lookup_endpoint(cli)
        ok = client.check_skypipe_endpoint(endpoint, timeout)
        if ok:
            return endpoint
        else:
            return launch_satellite(cli) if deploy else None
    except (RESTAPIError, KeyError):
        return launch_satellite(cli) if deploy else None

def destroy_satellite(cli):
    url = '/applications/{0}'.format(APPNAME)
    try:
        res = cli.user.delete(url)
    except RESTAPIError:
        pass

def launch_satellite(cli):
    """Deploys a new satellite app over any existing app"""

    cli.info("Launching skypipe satellite:")

    finish = wait_for("    Pushing to dotCloud")

    # destroy any existing satellite
    destroy_satellite(cli)

    # create new satellite app
    url = '/applications'
    try:
        cli.user.post(url, {
            'name': APPNAME,
            'flavor': 'sandbox'
            })
    except RESTAPIError as e:
        if e.code == 409:
            cli.die('Application "{0}" already exists.'.format(APPNAME))
        else:
            cli.die('Creating application "{0}" failed: {1}'.format(APPNAME, e))
    class args: application = APPNAME
    #cli._connect(args)

    # push satellite code
    protocol = 'rsync'
    url = '/applications/{0}/push-endpoints{1}'.format(APPNAME, '')
    endpoint = cli._select_endpoint(cli.user.get(url).items, protocol)
    class args: path = satellite_path
    cli.push_with_rsync(args, endpoint)

    # tell dotcloud to deploy, then wait for it to finish
    revision = None
    clean = False
    url = '/applications/{0}/deployments'.format(APPNAME)
    response = cli.user.post(url, {'revision': revision, 'clean': clean})
    deploy_trace_id = response.trace_id
    deploy_id = response.item['deploy_id']


    original_stdout = sys.stdout

    finish = wait_for("    Waiting for deployment", finish, original_stdout)

    try:
        sys.stdout = StringIO()
        res = cli._stream_deploy_logs(APPNAME, deploy_id,
                deploy_trace_id=deploy_trace_id, follow=True)
        if res != 0:
            return res
    except KeyboardInterrupt:
        cli.error('You\'ve closed your log stream with Ctrl-C, ' \
            'but the deployment is still running in the background.')
        cli.error('If you aborted because of an error ' \
            '(e.g. the deployment got stuck), please e-mail\n' \
            'support@dotcloud.com and mention this trace ID: {0}'
            .format(deploy_trace_id))
        cli.error('If you want to continue following your deployment, ' \
                'try:\n{0}'.format(
                    cli._fmt_deploy_logs_command(deploy_id)))
        cli.die()
    except RuntimeError:
        # workaround for a bug in the current dotcloud client code
        pass
    finally:
        sys.stdout = original_stdout

    finish = wait_for("    Satellite coming online", finish)

    endpoint = lookup_endpoint(cli)
    ok = client.check_skypipe_endpoint(endpoint, 120)
   
    finish.set()
    time.sleep(0.1) # sigh, threads

    if ok:
        return endpoint
    else:
        cli.die("Satellite failed to come online")


########NEW FILE########
__FILENAME__ = server
import collections
import sys
import os
import zmq

SP_HEADER = "SKYPIPE/0.1"
SP_CMD_HELLO = "HELLO"
SP_CMD_DATA = "DATA"
SP_CMD_LISTEN = "LISTEN"
SP_CMD_UNLISTEN = "UNLISTEN"
SP_DATA_EOF = ""

context = zmq.Context()
port = os.environ.get("PORT_ZMQ", 9000)

router = context.socket(zmq.ROUTER)
router.bind("tcp://0.0.0.0:{}".format(port))

pipe_clients = collections.defaultdict(list) # connected skypipe clients
pipe_buffers = collections.defaultdict(list) # any buffered data for pipes

print "Skypipe satellite serving on {}...".format(port)

def cmd_listen():
    pipe_clients[pipe_name].append(client)
    if len(pipe_clients[pipe_name]) == 1:
        # if only client after adding, then previously there were
        # no clients and it was buffering, so spit out buffered data
        while len(pipe_buffers[pipe_name]) > 0:
            data = pipe_buffers[pipe_name].pop(0)
            router.send_multipart([client,
                SP_HEADER, SP_CMD_DATA, pipe_name, data])
            if data == SP_DATA_EOF:
                # remember this kicks the client, so stop
                # sending data until the next one listens
                break

def cmd_unlisten():
    if client in pipe_clients[pipe_name]:
        pipe_clients[pipe_name].remove(client)

def cmd_data():
    data = msg.pop(0)
    if not pipe_clients[pipe_name]:
        pipe_buffers[pipe_name].append(data)
    else:
        for listener in pipe_clients[pipe_name]:
            router.send_multipart([listener,
                SP_HEADER, SP_CMD_DATA, pipe_name, data])

while True:
    sys.stdout.flush()

    msg = router.recv_multipart()
    client = msg.pop(0)
    header = str(msg.pop(0))
    command = str(msg.pop(0))

    # Human-friendlier version of client UUID
    client_display = hex(abs(hash(client)))[-6:]

    if SP_CMD_HELLO == command:
        router.send_multipart([client, SP_HEADER, SP_CMD_HELLO])
    else:
        pipe_name = msg.pop(0)
        try:
            {
                SP_CMD_LISTEN: cmd_listen,
                SP_CMD_UNLISTEN: cmd_unlisten,
                SP_CMD_DATA: cmd_data,
            }[command]()
        except KeyError:
            print client_display, "Unknown command:", command


    print client_display, command

########NEW FILE########
