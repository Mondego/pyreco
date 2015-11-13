__FILENAME__ = plugin
from bottle import request

def websocket(callback):
    def wrapper(*args, **kwargs):
        callback(request.environ.get('wsgi.websocket'), *args, **kwargs)

    return wrapper

########NEW FILE########
__FILENAME__ = server
from bottle import ServerAdapter
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler

class GeventWebSocketServer(ServerAdapter):
    def run(self, handler):
        pywsgi.WSGIServer((self.host, self.port), handler, handler_class=WebSocketHandler).serve_forever()

########NEW FILE########
__FILENAME__ = chat
from bottle import default_app, get, template
from bottle.ext.websocket import GeventWebSocketServer
from bottle.ext.websocket import websocket

users = set()

@get('/')
def index():
    return template('index')

@get('/websocket', apply=[websocket])
def chat(ws):
    users.add(ws)
    while True:
        msg = ws.receive()
        if msg is not None:
            for u in users:
                u.send(msg)
        else: break
    users.remove(ws)

application = default_app()

########NEW FILE########
__FILENAME__ = echo
from bottle import get, run, template
from bottle.ext.websocket import GeventWebSocketServer
from bottle.ext.websocket import websocket

@get('/')
def index():
    return template('index')

@get('/websocket', apply=[websocket])
def echo(ws):
    while True:
        msg = ws.receive()
        if msg is not None:
            ws.send(msg)
        else: break

run(host='127.0.0.1', port=8080, server=GeventWebSocketServer)

########NEW FILE########
