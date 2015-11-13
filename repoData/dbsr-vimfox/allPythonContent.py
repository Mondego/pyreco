__FILENAME__ = run
# -*- coding: utf-8 -*-
# dydrmntion@gmail.com ~ 2013
import sys
import os

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_here, 'ext'))

from socketio.server import SocketIOServer
from gevent import monkey

monkey.patch_all()

from server import app


def start_server(host_address):
    try:
        server = SocketIOServer(host_address, app, resource='socket.io')
        server.serve_forever()
    except:
        # assume for now server is already running
        pass


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--debug", type=bool)
    parser.add_argument("--hide-status", type=bool)
    args = parser.parse_args()
    host_address = (args.host, args.port)
    app.debug = args.debug
    if not args.debug:
        app.logger.propagate = False
        app.logger.level = 40
    app.vimfox['hide_status'] = not args.hide_status

    start_server(host_address)

########NEW FILE########
__FILENAME__ = server
# -*- coding: utf-8 -*-
# dydrmntion@gmail.com ~ 2013

import os
import time

from socketio import socketio_manage
from socketio.namespace import BaseNamespace
from flask import Flask, send_file, Response, request

app = Flask(__name__)
app.vimfox = {
    'ready': 0
}


@app.route('/vimfox/<path:filename>')
def send_vimfox_file(filename):
    app.logger.info(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', filename))
    try:
        return send_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', filename))
    except:
        return Response(':(', status=404)


class VimFoxNamespace(BaseNamespace):
    sockets = {}

    def initialize(self):
        self.logger = app.logger
        self.log('socket initialized')
        self.sockets[id(self)] = self

        return True

    def log(self, msg):
        self.logger.info("[{0}] {1}".format(self.socket.sessid, msg))

    def disconnect(self, *args, **kwargs):
        self.log("connection lost")
        if id(self) in self.sockets:
            del self.sockets[id(self)]
            self.emit('disconnect')
        app.vimfox['ready'] = True

    def on_busy(self):
        self.log("processing event request.")
        app.vimfox['ready'] = time.time()

    def on_ready(self):
        self.log("ready for new event requests.")
        app.vimfox['ready'] = True

    def on_settings(self):
        self.log("processing settings request.")
        self.emit("settings", {"debug_mode": app.debug, "hide_status": app.vimfox['hide_status']})

    @classmethod
    def socketio_send(self, data):
        event = data['event']
        del data['event']
        app.logger.info("event emit request: {0!r}.".format(repr(data)))
        for ws in self.sockets.values():
            ws.emit(event, data)


@app.route('/socket.io/<path:remaining>')
def socketio(remaining):
    try:
        socketio_manage(request.environ, {'/ws': VimFoxNamespace}, request)
    except:
        app.logger.error("Socket Error.", exc_info=True)

    return Response()


@app.route('/socket', methods=['POST'])
def reload():
    if app.vimfox['ready'] or time.time() - app.vimfox['ready'] > 5:
        VimFoxNamespace.socketio_send(dict(request.json))

        return Response('OK', 200)
    else:

        return Response('zZz', 503)


@app.route('/get-server-pid')
def get_server_pid():
    return Response(str(os.getpid()), 200)


@app.route('/debug')
def debug():
    return Response("""
            <!DOCTYPE html>
        <html>
        <head>
            <title></title>
            <meta charset="utf-8" />
            <link rel="stylesheet" href="/assets/css/style2.css">
            <link rel="stylesheet" href="/assets/css/style3.css">
        </head>
        <body>
            <script rel="text/javascript" src="/vimfox/vimfox.js"></script>
        </body>
        </html>""")

########NEW FILE########
__FILENAME__ = vimfox
# -*- coding: utf-8 -*-
# dydrmntion@gmail.com ~ 2013

import os
import subprocess
import urllib2
import json


RUN_SERVER_PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server', 'run.py')


class VimFox(object):

    server_prc = None
    server_prc_pid = None

    def __init__(self, host, port, debug, hide_status):
        self.host = host
        self.port = port
        self.debug = debug
        self.hide_status = hide_status
        self.start_server()

    def start_server(self):
        if self.server_is_down():
            cmd = ['python', RUN_SERVER_PY, '--host', str(self.host), '--port', str(self.port),
                   '--debug', str(self.debug), '--hide-status', str(self.hide_status)]
            if not self.server_prc or self.server_prc.poll():
                self.server_prc = subprocess.Popen(cmd)
                self.server_prc_pid = self.server_prc.pid

    def kill_server(self):
        """Attempts to terminate the server's subprocess. First it will try to
        send the SIGTERM straight to the subprocess instance. This should work most
        of the time. If vim crashed while vimfox was running we might have missed
        the on close autocmd which means the server was still running when we started
        vim. Now we'll have to try and use the pid send to us from the server when
        we checked it was alive."""

        if self.server_prc and not self.server_prc.poll():
            self.server_prc.kill()
        else:
            from signal import SIGTERM
            try:
                os.kill(self.server_prc_pid, SIGTERM)
            except OSError:
                pass

    def ws_send(self, event, delay, fname=None):
        """Sends commands to the vimfox HTTP server which acts as a relay between
        vim and the websockets on the page."""

        req = urllib2.Request("http://{0}:{1}/socket".format(self.host, self.port),
                              json.dumps({'event': event, 'fname': fname, 'delay': delay}),
                              {'Content-Type': 'application/json'})
        try:
            urllib2.urlopen(req)
        except urllib2.HTTPError as e:
            if e.code == 503:
                # ws is busy, ignore this request"
                pass
            else:
                raise(e)

    def server_is_down(self):
        """Checks whether the vimfox server is up and running. If it's up the response
        contains the pid number of the vimfox server process."""
        req = urllib2.Request("http://{0}:{1}/get-server-pid".format(self.host, self.port))
        try:
            r = urllib2.urlopen(req)
        except urllib2.URLError:
            return True
        else:
            self.server_prc_pid = int(r.read())
            return False

if __name__ == '__main__':
    vf = VimFox('l27.0.0.1', 9999, True)

########NEW FILE########
