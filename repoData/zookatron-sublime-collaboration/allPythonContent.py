__FILENAME__ = client
import logging, doc, connection

class CollabClient:
    def __init__(self, host, port):
        self.docs = {}
        self.state = 'connecting'

        self.waiting_for_docs = []

        self.connected = False
        self.id = None

        self.socket = connection.ClientSocket(host, port)
        self.socket.on('message', self.socket_message)
        self.socket.on('error', self.socket_error)
        self.socket.on('open', self.socket_open)
        self.socket.on('close', self.socket_close)
        self.socket.start()

        self._events = {}

    def on(self, event, fct):
        if event not in self._events: self._events[event] = []
        self._events[event].append(fct)
        return self

    def removeListener(self, event, fct):
        if event not in self._events: return self
        self._events[event].remove(fct)
        return self

    def emit(self, event, *args):
        if event not in self._events: return self
        for callback in self._events[event]:
            callback(*args)
        return self

    def socket_open(self):
        self.set_state('handshaking')

    def socket_close(self, reason=''):
        self.set_state('closed', reason)
        self.socket = None

    def socket_error(self, error):
        self.emit('error', error)

    def socket_message(self, msg):
        if 'auth' in msg:
            if msg['auth'] is None or msg['auth'] == '':
                logging.warning('Authentication failed: {0}'.format(msg['error']))
                self.disconnect()
            else:
                self.id = msg['auth']
                self.set_state('ok')
            return

        if 'docs' in msg:
            if 'error' in msg:
                for callback in self.waiting_for_docs:
                    callback(msg['error'], None)
            else:
                for callback in self.waiting_for_docs:
                    callback(None, msg['docs'])
            self.waiting_for_docs = []
            return

        if 'doc' in msg and msg['doc'] in self.docs:
            self.docs[msg['doc']].on_message(msg)
        else:
            logging.error('Unhandled message {0}'.format(msg))

    def set_state(self, state, data=None):
        if self.state is state: return
        self.state = state

        if state is 'closed':
            self.id = None
        self.emit(state, data)

    def send(self, data):
        if self.state is not "closed":
            self.socket.send(data)

    def disconnect(self):
        if self.state is not "closed":
            self.socket.close()

    def get_docs(self, callback):
        if self.state is 'closed':
            return callback('connection closed', None)

        if self.state is 'connecting':
            return self.on('ok', lambda x: self.get_docs(callback))

        if not self.waiting_for_docs:
            self.send({"docs":None})
        self.waiting_for_docs.append(callback)

    def open(self, name, callback, **kwargs):
        if self.state is 'closed':
            return callback('connection closed', None)

        if self.state is 'connecting':
            return self.on('ok', lambda x: self.open(name, callback))

        if name in self.docs:
            return callback("doc {0} already open".format(name), None)

        newdoc = doc.CollabDoc(self, name, kwargs.get('snapshot', None))
        self.docs[name] = newdoc

        newdoc.open(lambda error, doc: callback(error, doc if not error else None))

    def closed(self, name):
        del self.docs[name]


########NEW FILE########
__FILENAME__ = connection
import json, threading, socket, base64, hashlib

debug = False

class ClientSocket(threading.Thread):
    def __init__(self, host, port):
        threading.Thread.__init__(self)

        self.host = host
        self.port = port
        self.sock = None

        self.saved_data = ''
        self.target_size = None

        self.keep_running = True

        self._events = {}

    def on(self, event, fct):
        if event not in self._events: self._events[event] = []
        self._events[event].append(fct)
        return self

    def removeListener(self, event, fct):
        if event not in self._events: return self
        self._events[event].remove(fct)
        return self

    def emit(self, event, *args):
        if event not in self._events: return self
        for callback in self._events[event]:
            callback(*args)
        return self

    def send(self, data):
        global debug
        if debug:
            print('Sending:{0}'.format(data))

        msg = json.dumps(data)

        #A pretty terrible hacky framing system, I'll need to come up with a better one soon
        try:
            self.sock.send(u"0"*(10-len(unicode(len(msg))))+unicode(len(msg))+msg)
        except:
            self.close()

    def close(self):
        self.keep_running = False
        if self.sock:
            self.sock.shutdown(socket.SHUT_RDWR)

    def run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.host, self.port))
        except:
            self.emit('error', 'could not connect to server')
            self.emit('close')
            self.sock = None
            return
        self.emit('open')
        while self.keep_running:
            try:
                data = self.sock.recv(self.target_size if self.target_size else 10)
            except:
                break
            if data is None or data == "":
                break

            global debug
            if debug:
                print('Recieved:{0}'.format(data))

            if self.target_size:
                self.saved_data += data
                if len(self.saved_data) == self.target_size:
                    self.emit('message', json.loads(self.saved_data, "utf-8"))
                    self.saved_data = ''
                    self.target_size = None
            else:
                self.target_size = int(data)

        self.sock.close()
        self.emit('close')
        self.sock = None



class ServerSocket(threading.Thread):
    def __init__(self, sock, addr):
        threading.Thread.__init__(self)

        self.sock = sock
        sock.settimeout(None)

        self.address = addr
        self.headers = None

        self.saved_data = ''
        self.target_size = None

        self._ready = False
        self._events = {}

    def on(self, event, fct):
        if event not in self._events: self._events[event] = []
        self._events[event].append(fct)
        return self

    def removeListener(self, event, fct):
        if event not in self._events: return self
        self._events[event].remove(fct)
        return self

    def emit(self, event, *args):
        if event not in self._events: return self
        for callback in self._events[event]:
            callback(*args)
        return self

    def run(self):
        self._ready = True
        self.emit('ok')

        while self._ready:
            try:
                data = self.sock.recv(self.target_size if self.target_size else 10)
            except:
                break
            if data is None or data == "":
                break

            global debug
            if debug:
                print('Server Recieved from {0}:{1}'.format(self.address, data))

            if self.target_size:
                self.saved_data += data
                if len(self.saved_data) == self.target_size:
                    self.emit('message', json.loads(self.saved_data, "utf-8"))
                    self.saved_data = ''
                    self.target_size = None
            else:
                self.target_size = int(data)

        self._ready = False
        self.emit('close')
        self.close()

    def close(self):
        self._ready = False
        self.sock.shutdown(socket.SHUT_RDWR)

    def send(self, data):
        if not self._ready: return

        global debug
        if debug:
            print('Server Sending to {0}:{1}'.format(self.address, data))

        msg = json.dumps(data)

        #A pretty terrible hacky framing system, I'll need to come up with a better one soon
        try:
            self.sock.send(u"0"*(10-len(unicode(len(msg))))+unicode(len(msg))+msg)
        except:
            self.close()

    def ready(self):
        return self._ready

    def abort(self):
        self.close()

    def stop(self):
        self.close()



class SocketServer:
    def __init__(self, host='127.0.0.1', port=6633):
        self.host = host
        self.port = port
        self.sock = None
        self.keep_running = True
        self.closed = False
        self.connections = []
        self._events = {}

    def on(self, event, fct):
        if event not in self._events: self._events[event] = []
        self._events[event].append(fct)
        return self

    def removeListener(self, event, fct):
        if event not in self._events: return self
        self._events[event].remove(fct)
        return self

    def emit(self, event, *args):
        if event not in self._events: return self
        for callback in self._events[event]:
            callback(*args)
        return self

    def run_forever(self):
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(0.1)
        self.sock.bind(('', self.port))
        self.sock.listen(1)

        while self.keep_running:
            try:
                conn, addr = self.sock.accept()
            except socket.timeout:
                continue
            #print('Connected by {0}'.format(addr))
            connection = ServerSocket(conn, addr)
            self.connections.append(connection)
            def on_close():
                #print('Disconnected by {0}'.format(addr))
                if connection in self.connections:
                    self.connections.remove(connection)
            connection.on('close', on_close)
            connection.start()
            self.emit('connection', connection)

        self.closed = True

    def close(self):
        self.keep_running = False
        for connection in self.connections:
            connection.close()
        self.sock.close()
        while not self.closed: pass

########NEW FILE########
__FILENAME__ = doc
import functools, optransform

class CollabDoc():
    def __init__(self, connection, name, snapshot=None):
        self.connection = connection
        self.name = name
        self.version = 0
        self.snapshot = snapshot
        self.state = 'closed'

        self._events = {}

        self.on('remoteop', self.on_doc_remoteop)

        self.connection.on('closed', lambda data: self.set_state('closed', data))

        self.inflight_op = None
        self.inflight_callbacks = []
        self.pending_op = None
        self.pending_callbacks = []
        self.server_ops = {}

        self._open_callback = None

    def on(self, event, fct):
        if event not in self._events: self._events[event] = []
        self._events[event].append(fct)
        return self

    def removeListener(self, event, fct):
        if event not in self._events: return self
        self._events[event].remove(fct)
        return self

    def emit(self, event, *args):
        if event not in self._events: return self
        for callback in self._events[event]:
            callback(*args)
        return self

    def set_state(self, state, data=None):
        if self.state is state: return
        self.state = state

        if state is 'closed':
            if self._open_callback: self._open_callback(data if data else "disconnected", None)

        self.emit(state, data)

    def get_text(self):
        return self.snapshot

    def insert(self, pos, text, callback=None):
        op = [{'p':pos, 'i':text}]
        self.submit_op(op, callback)
        return op

    def delete(self, pos, length, callback=None):
        op = [{'p':pos, 'd':self.snapshot[pos:(pos+length)]}]
        self.submit_op(op, callback)
        return op

    def on_doc_remoteop(self, op, snapshot):
        for component in op:
            if 'i' in component:
                self.emit('insert', component['p'], component['i'])
            else:
                self.emit('delete', component['p'], component['d'])

    def open(self, callback=None):
        if self.state != 'closed': return

        self.connection.send({'doc': self.name, 'open': True, 'snapshot': self.snapshot, 'create': True})
        self.set_state('opening')

        self._open_callback = callback

    def close(self):
        self.connection.send({'doc':self.name, 'open':False})
        self.set_state('closed', 'closed by local client')

    def submit_op(self, op, callback):
        op = optransform.normalize(op)
        self.snapshot = optransform.apply(self.snapshot, op)

        if self.pending_op is not None:
            self.pending_op = optransform.compose(self.pending_op, op)
        else:
            self.pending_op = op

        if callback:
            self.pending_callbacks.append(callback)

        self.emit('change', op)

        self.flush()

    def flush(self):
        if not (self.connection.state == 'ok' and self.inflight_op is None and self.pending_op is not None):
            return

        self.inflight_op = self.pending_op
        self.inflight_callbacks = self.pending_callbacks

        self.pending_op = None
        self.pending_callbacks = []

        self.connection.send({'doc':self.name, 'op':self.inflight_op, 'v':self.version})

    def apply_op(self, op, is_remote):
        oldSnapshot = self.snapshot
        self.snapshot = optransform.apply(self.snapshot, op)

        self.emit('change', op, oldSnapshot)
        if is_remote:
            self.emit('remoteop', op, oldSnapshot)

    def on_message(self, msg):
        if msg['doc'] != self.name:
            return self.emit('error', "Expected docName '{0}' but got {1}".format(self.name, msg['doc']))

        if 'open' in msg:
            if msg['open'] == True:

                if 'create' in msg and msg['create'] and not self.snapshot:
                    self.snapshot = ''
                else:
                    if 'snapshot' in msg:
                        self.snapshot = msg['snapshot']

                if 'v' in msg:
                    self.version = msg['v']

                self.state = 'open'
                self.emit('open')

                if self._open_callback:
                    self._open_callback(None, self)
                    self._open_callback = None

            elif msg['open'] == False:
                if 'error' in msg:
                    self.emit('error', msg['error'])
                    if self._open_callback:
                        self._open_callback(msg['error'], None)
                        self._open_callback = None

                self.set_state('closed', 'closed by remote server')
                self.connection.closed(self.name)

        elif 'op' not in msg and 'v' in msg:
            if msg['v'] != self.version:
                return self.emit('error', "Expected version {0} but got {1}".format(self.version, msg['v']))

            oldinflight_op = self.inflight_op
            self.inflight_op = None

            if 'error' in msg:
                error = msg['error']
                undo = optransform.invert(oldinflight_op)
                if self.pending_op:
                    self.pending_op, undo = optransform.transform_x(self.pending_op, undo)
                for callback in self.inflight_callbacks:
                    callback(error, None)
            else:
                self.server_ops[self.version] = oldinflight_op
                self.version += 1
                for callback in self.inflight_callbacks:
                    callback(None, oldinflight_op)

            self.flush()

        elif 'op' in msg and 'v' in msg:
            if msg['v'] != self.version:
                return self.emit('error', "Expected version {0} but got {1}".format(self.version, msg['v']))

            op = msg['op']
            self.server_ops[self.version] = op

            if self.inflight_op is not None:
                self.inflight_op, op = optransform.transform_x(self.inflight_op, op)
            if self.pending_op is not None:
                self.pending_op, op = optransform.transform_x(self.pending_op, op)

            self.version += 1
            self.apply_op(op, True)
        else:
            logging.error('Unhandled document message: {0}'.format(msg))

########NEW FILE########
__FILENAME__ = model
import time, re, logging, optransform

class CollabModel(object):
    def __init__(self, options=None):
        self.options = options if options else {}
        self.options.setdefault('numCachedOps', 20)
        self.options.setdefault('opsBeforeCommit', 20)
        self.options.setdefault('maximumAge', 20)

        self.docs = {}

    def process_queue(self, doc):
        if doc['queuelock'] or len(doc['queue']) == 0:
            return

        doc['queuelock'] = True
        op, callback = doc['queue'].pop(0)
        self.handle_op(doc, op, callback)
        doc['queuelock'] = False

        self.process_queue(doc)

    def handle_op(self, doc, op, callback):
        if 'v' not in op or op['v'] < 0:
            return callback('Version missing', None)
        if op['v'] > doc['v']:
            return callback('Op at future version', None)
        if op['v'] < doc['v'] - self.options['maximumAge']:
            return callback('Op too old', None)
        if op['v'] < 0:
            return callback('Invalid version', None)

        ops = doc['ops'][(len(doc['ops'])+op['v']-doc['v']):]

        if doc['v'] - op['v'] != len(ops):
            logging.error("Could not get old ops in model for document {1}. Expected ops {1} to {2} and got {3} ops".format(doc['name'], op['v'], doc['v'], len(ops)))
            return callback('Internal error', None)

        for oldOp in ops:
            op['op'] = optransform.transform(op['op'], oldOp['op'], 'left')
            op['v']+=1

        newSnapshot = optransform.apply(doc['snapshot'], op['op'])

        if op['v'] != doc['v']:
            logging.error("Version mismatch detected in model. File a ticket - this is a bug. Expecting {0} == {1}".format(op['v'], doc['v']))
            return callback('Internal error', None)

        oldSnapshot = doc['snapshot']
        doc['v'] = op['v'] + 1
        doc['snapshot'] = newSnapshot
        for listener in doc['listeners']:
            listener(op, newSnapshot, oldSnapshot)

        def save_op_callback(error=None):
            if error:
                logging.error("Error saving op: {0}".format(error))
                return callback(error, None)
            else:
                return callback(None, op['v'])
        self.save_op(doc['name'], op, save_op_callback)

    def save_op(self, docname, op, callback):
        doc = self.docs[docname]
        doc['ops'].append(op)
        if len(doc['ops']) > self.options['numCachedOps']:
            doc['ops'].pop(0)
        if not doc['savelock'] and doc['savedversion'] + self.options['opsBeforeCommit'] <= doc['v']:
            pass
        callback(None)

    def exists(self, docname):
        return docname in self.docs

    def get_docs(self, callback):
        callback(None, [self.docs[doc]['name'] for doc in self.docs])

    def add(self, docname, data):
        self.docs[docname] = {
            'name': docname,
            'snapshot': data['snapshot'],
            'v': data['v'],
            'ops': data['ops'],
            'listeners': [],
            'savelock': False,
            'savedversion': 0,
            'queue': [],
            'queuelock': False,
        }

    def load(self, docname, callback):
        try:
            return callback(None, self.docs[docname])
        except KeyError:
            return callback('Document does not exist', None)

        # self.loadingdocs = {}
        # self.loadingdocs.setdefault(docname, []).append(callback)
        # if docname in self.loadingdocs:
        #     for callback in self.loadingdocs[docname]:
        #         callback(None, doc)
        #     del self.loadingdocs[docname]

    def create(self, docname, snapshot=None, callback=None):
        if not re.match("^[A-Za-z0-9._-]*$", docname):
            return callback('Invalid document name') if callback else None
        if self.exists(docname):
            return callback('Document already exists') if callback else None

        data = {
            'snapshot': snapshot if snapshot else '',
            'v': 0,
            'ops': []
        }
        self.add(docname, data)

        return callback(None) if callback else None

    def delete(self, docname, callback=None):
        if docname not in self.docs: raise Exception('delete called but document does not exist')
        del self.docs[docname]
        return callback(None) if callback else None

    def listen(self, docname, listener, callback=None):
        def done(error, doc):
            if error: return callback(error, None) if callback else None
            doc['listeners'].append(listener)
            return callback(None, doc['v']) if callback else None
        self.load(docname, done)

    def remove_listener(self, docname, listener):
        if docname not in self.docs: raise Exception('remove_listener called but document not loaded')
        self.docs[docname]['listeners'].remove(listener)

    def get_version(self, docname, callback):
        self.load(docname, lambda error, doc: callback(error, None if error else doc['v']))

    def get_snapshot(self, docname, callback):
        self.load(docname, lambda error, doc: callback(error, None if error else doc['snapshot']))

    def get_data(self, docname, callback):
        self.load(docname, lambda error, doc: callback(error, None if error else doc))

    def apply_op(self, docname, op, callback):
        def on_load(error, doc):
            if error:
                callback(error, None)
            else:
                doc['queue'].append((op, callback))
                self.process_queue(doc)
        self.load(docname, on_load)
        
    def flush(self, callback=None):
        return callback() if callback else None

    def close(self):
        self.flush()

########NEW FILE########
__FILENAME__ = optransform
def inject(s1, pos, s2):
    return s1[:pos] + s2 + s1[pos:]

def apply(snapshot, op):
    for component in op:
        if 'i' in component:
            snapshot = inject(snapshot, component['p'], component['i'])
        else:
            deleted = snapshot[component['p']:(component['p'] + len(component['d']))]
            if(component['d'] != deleted): raise Exception("Delete component '{0}' does not match deleted text '{1}'".format(component['d'], deleted))
            snapshot = snapshot[:component['p']] + snapshot[(component['p'] + len(component['d'])):]
    return snapshot

def append(newOp, c):
    if 'i' in c and c['i'] == '': return
    if 'd' in c and c['d'] == '': return
    if len(newOp) == 0:
        newOp.append(c)
    else:
        last = newOp[len(newOp) - 1]

        if 'i' in last and 'i' in c and last['p'] <= c['p'] <= (last['p'] + len(last['i'])):
            newOp[len(newOp) - 1] = {'i':inject(last['i'], c['p'] - last['p'], c['i']), 'p':last['p']}
        elif 'd' in last and 'd' in c and c['p'] <= last['p'] <= (c['p'] + len(c['d'])):
            newOp[len(newOp) - 1] = {'d':inject(c['d'], last['p'] - c['p'], last['d']), 'p':c['p']}
        else:
            newOp.append(c)

def compose(op1, op2):
    newOp = list(op1)
    [append(newOp, c) for c in op2]
    return newOp

def compress(op):
    return compose([], op)

def normalize(op):
    newOp = []

    if(isinstance(op, dict)): op = [op]

    for c in op:
        if 'p' not in c or not c['p']: c['p'] = 0
        append(newOp, c)

    return newOp

def invert_component(c):
    if 'i' in c:
        return {'d':c['i'], 'p':c['p']}
    else:
        return {'i':c['d'], 'p':c['p']}

def invert(op):
    return [invert_component(c) for c in reversed(op)]

def transform_position(pos, c, insertAfter=False):
    if 'i' in c:
        if c['p'] < pos or (c['p'] == pos and insertAfter):
            return pos + len(c['i'])
        else:
            return pos
    else:
        if pos <= c['p']:
            return pos
        elif pos <= c['p'] + len(c['d']):
            return c['p']
        else:
            return pos - len(c['d'])

def transform_cursor(position, op, insertAfter=False):
    for c in op:
        position = transform_position(position, c, insertAfter) 
    return position

def transform_component(dest, c, otherC, type):
    if 'i' in c:
        append(dest, {'i':c['i'], 'p':transform_position(c['p'], otherC, type == 'right')})
    else:
        if 'i' in otherC:
            s = c['d']
            if c['p'] < otherC['p']:
                append(dest, {'d':s[:otherC['p'] - c['p']], 'p':c['p']})
                s = s[(otherC['p'] - c['p']):]
                pass
            if s != '':
                append(dest, {'d':s, 'p':c['p'] + len(otherC['i'])})
        else:
            if c['p'] >= otherC['p'] + len(otherC['d']):
                append(dest, {'d':c['d'], 'p':c['p'] - len(otherC['d'])})
            elif c['p'] + len(c['d']) <= otherC['p']:
                append(dest, c)
            else:
                newC = {'d':'', 'p':c['p']}
                if c['p'] < otherC['p']:
                    newC['d'] = c['d'][:(otherC['p'] - c['p'])]
                    pass
                if c['p'] + len(c['d']) > otherC['p'] + len(otherC['d']):
                    newC['d'] += c['d'][(otherC['p'] + len(otherC['d']) - c['p']):]
                    pass

                intersectStart = max(c['p'], otherC['p'])
                intersectEnd = min(c['p'] + len(c['d']), otherC['p'] + len(otherC['d']))
                cIntersect = c['d'][intersectStart - c['p']:intersectEnd - c['p']]
                otherIntersect = otherC['d'][intersectStart - otherC['p']:intersectEnd - otherC['p']]
                if cIntersect != otherIntersect:
                    raise Exception('Delete ops delete different text in the same region of the document')

                if newC['d'] != '':
                    newC['p'] = transform_position(newC['p'], otherC)
                append(dest, newC)

    return dest

def transform_component_x(left, right, destLeft, destRight):
    transform_component(destLeft, left, right, 'left')
    transform_component(destRight, right, left, 'right')

def transform_x(leftOp, rightOp):
    newRightOp = []

    for rightComponent in rightOp:
        newLeftOp = []

        k = 0
        while k < len(leftOp):
            nextC = []
            transform_component_x(leftOp[k], rightComponent, newLeftOp, nextC)
            k+=1

            if len(nextC) == 1:
                rightComponent = nextC[0]
            elif len(nextC) == 0:
                [append(newLeftOp, l) for l in leftOp[k:]]
                rightComponent = None
                break
            else:
                l_, r_ = transform_x(leftOp[k:], nextC)
                [append(newLeftOp, l) for l in l_]
                [append(newRightOp, r) for r in r_]
                rightComponent = None
                break
    
        if rightComponent:
            append(newRightOp, rightComponent)
        leftOp = newLeftOp

    return [leftOp, newRightOp]

def transform(op, otherOp, side):
    if side != 'left' and side != 'right':
        raise ValueError("side must be 'left' or 'right'")

    if len(otherOp) == 0:
        return op

    if len(op) == 1 and len(otherOp) == 1:
        return transform_component([], op[0], otherOp[0], side)

    if side == 'left':
        left, _ = transform_x(op, otherOp)
        return left
    else:
        _, right = transform_x(otherOp, op)
        return right

########NEW FILE########
__FILENAME__ = server
import threading, session, model, connection

class CollabServer(object):
	def __init__(self, options=None):
		if not options:
			options = {}

		self.options = options
		self.model = model.CollabModel(options)
		self.host = self.options.get('host', '127.0.0.1')
		self.port = self.options.get('port', 6633)
		self.idtrack = 0

		self.server = connection.SocketServer(self.host, self.port)
		self.server.on('connection', lambda connection: session.CollabSession(connection, self.model, self.new_id()))

	def run_forever(self):
		threading.Thread(target=self.server.run_forever).start()

	def new_id(self):
		self.idtrack += 1
		return self.idtrack

	def close(self):
		self.model.close()
		self.server.close()

########NEW FILE########
__FILENAME__ = session
import logging

class CollabSession(object):
    def __init__(self, connection, model, id):
        self.connection = connection
        self.model = model

        self.docs = {}
        self.userid = id

        if self.connection.ready():
            self.on_session_create()
        else:
            self.connection.on('ok', lambda: self.on_session_create)
        self.connection.on('close', self.on_session_close)
        self.connection.on('message', self.on_session_message)

    def on_session_create(self):
        self.connection.send({'auth':self.userid})

    def on_session_close(self):
        for docname in self.docs:
            if 'listener' in self.docs[docname]:
                self.model.remove_listener(docname, self.docs[docname]['listener'])
        self.docs = None

    def on_session_message(self, query, callback=None):
        if 'docs' in query:
            return self.model.get_docs(lambda e, docs: self.on_get_docs(e, docs, callback))

        error = None
        if 'doc' not in query or not isinstance(query['doc'], (str, unicode)):
            error = 'doc name invalid or missing'
        if 'create' in query and query['create'] is not True:
            error = "'create' must be True or missing"
        if 'open' in query and query['open'] not in [True, False]:
            error = "'open' must be True, False or missing"
        if 'v' in query and (not isinstance(query['v'], (int, float)) or query['v'] < 0):
            error = "'v' invalid"

        if error:
            logging.error("Invalid query {0} from {1}: {2}".format(query, self.userid, error))
            self.connection.abort()
            return callback() if callback else None

        if query['doc'] not in self.docs:
            self.docs[query['doc']] = {'queue': [], 'queuelock': False}

        doc = self.docs[query['doc']]
        doc['queue'].append((query, callback))
        self.process_queue(doc)

    def on_get_docs(self, error, docs, callback):
        self.send({"docs":docs} if not error else {"docs":None, "error":error})
        return callback() if callback else None

    def process_queue(self, doc):
        if doc['queuelock'] or len(doc['queue']) == 0:
            return

        doc['queuelock'] = True
        query, callback = doc['queue'].pop(0)
        self.handle_message(query, callback)
        doc['queuelock'] = False

        self.process_queue(doc)

    def handle_message(self, query, callback = None):
        if not self.docs:
            return callback() if callback else None
        
        if 'open' in query and query['open'] == False:
            if 'listener' not in self.docs[query['doc']]:
                self.send({'doc':query['doc'], 'open':False, 'error':'Doc is not open'})
            else:
                self.model.remove_listener(query['doc'], self.docs[query['doc']]['listener'])
                del self.docs[query['doc']]['listener']
                self.send({'doc':query['doc'], 'open':False})
            return callback() if callback else None

        elif 'open' in query or ('snapshot' in query and query['snapshot'] is None) or 'create' in query:
            self.handle_opencreatesnapshot(query, callback)

        elif 'op' in query and 'v' in query:
            def apply_op(error, appliedVersion):
                self.send({'doc':query['doc'], 'v':None, 'error':error} if error else {'doc':query['doc'], 'v':appliedVersion})
                return callback() if callback else None
            self.model.apply_op(query['doc'], {'doc':query['doc'], 'v':query['v'], 'op':query['op'], 'source':self.userid}, apply_op)

        else:
            logging.error("Invalid query {0} from {1}".format(query, self.userid))
            self.connection.abort()
            return callback() if callback else None

    def on_remote_message(self, message, snapshot, oldsnapshot):
        if message['source'] is self.userid: return
        self.send(message)

    def send(self, msg):
        self.connection.send(msg)

    def handle_opencreatesnapshot(self, query, callback = None):
        def finished(message):
            if 'error' in message:
                if 'create' in query and 'create' not in message: message['create'] = False
                if 'snapshot' in query and 'snapshot' not in message: message['snapshot'] = None
                if 'open' in query and 'open' not in message: message['open'] = False
            self.send(message)
            return callback() if callback else None

        def step1Create(message):
            if 'create' not in query:
                return step2Snapshot(message)

            def model_create(error=None):
                if error == 'Document already exists':
                    message['create'] = False
                    return step2Snapshot(message)
                elif error:
                    message['create'] = False
                    message['error'] = error
                    return finished(message)
                else:
                    message['create'] = True
                    return step2Snapshot(message)

            self.model.create(query['doc'], query.get('snapshot', None), model_create)

        def step2Snapshot(message):
            if 'snapshot' not in query or message['create']:
                return step3Open(message)

            def model_get_data(error, data):
                if error:
                    message['snapshot'] = None
                    message['error'] = error
                    return finished(message)
                message['v'] = data['v']
                message['snapshot'] = data['snapshot']
                return step3Open(message)

            return self.model.get_data(query['doc'], model_get_data)

        def step3Open(message):
            if 'open' not in query:
                return finished(message)

            doc = self.docs[query['doc']]
            if 'listener' in doc:
                message['open'] = True
                return finished(message)
            
            doc['listener'] = self.on_remote_message

            def model_listen(error, v):
                if error:
                    del doc['listener']
                    message['open'] = False
                    message['error'] = error
                message['open'] = True
                if 'v' not in message: message['v'] = v
                return finished(message)
            self.model.listen(query['doc'], doc['listener'], model_listen)

        step1Create({'doc':query['doc']})
########NEW FILE########
__FILENAME__ = collaboration
import collab, sublime, sublime_plugin

class SublimeListener(sublime_plugin.EventListener):
    _events = {}

    @classmethod
    def on(klass, event, fct):
        if event not in klass._events: klass._events[event] = []
        klass._events[event].append(fct)

    @classmethod
    def removeListener(klass, event, fct):
        if event not in klass._events: return
        klass._events[event].remove(fct)

    def emit(self, event, *args):
        if event not in self._events: return
        for callback in self._events[event]:
            callback(*args)
        return self

    def on_modified(self, view):
        self.emit("modified", view)

    def on_new(self, view):
        self.emit("new", view)

    def on_clone(self, view):
        self.emit("clone", view)

    def on_load(self, view):
        self.emit("load", view)

    def on_close(self, view):
        self.emit("close", view)

    def on_pre_save(self, view):
        self.emit("pre_save", view)

    def on_post_save(self, view):
        self.emit("post_save", view)

    def on_selection_modified(self, view):
        self.emit("selection_modified", view)

    def on_activated(self, view):
        self.emit("activated", view)

    def on_deactivated(self, view):
        self.emit("deactivated", view)



class SublimeEditor(object):
    def __init__(self, view, doc):
        self.doc = None
        self.view = view
        self.doc = doc
        self._events = {}
        self.state = "ok"
        self.in_remoteop = False

        SublimeListener.on("modified", self._on_view_modified)
        SublimeListener.on("close", self._on_view_close)
        SublimeListener.on("post_save", self._on_view_post_save)
        self.doc.on("closed", self.close)
        self.doc.on("remoteop", self._on_doc_remoteop)

        sublime.set_timeout(lambda: self._initialize(self.doc.get_text()), 0)

        print("opened "+doc.name)

    def on(self, event, fct):
        if event not in self._events: self._events[event] = []
        self._events[event].append(fct)
        return self

    def removeListener(self, event, fct):
        if event not in self._events: return self
        self._events[event].remove(fct)
        return self

    def emit(self, event, *args):
        if event not in self._events: return self
        for callback in self._events[event]:
            callback(*args)
        return self

    def focus(self):
        sublime.set_timeout(lambda: sublime.active_window().focus_view(self.view), 0)

    def close(self, reason=None):
        if self.state != "closed":
            self.state = "closed"
            print("closed "+self.doc.name+(": "+reason if reason else ''))
            self.doc.close()
            SublimeListener.removeListener("modified", self._on_view_modified)
            SublimeListener.removeListener("close", self._on_view_close)
            SublimeListener.removeListener("post_save", self._on_view_post_save)
            self.doc.removeListener("closed", self.close)
            self.doc.removeListener("remoteop", self._on_doc_remoteop)
            self.view = None
            self.doc = None
            self.emit("closed")

    def _on_view_modified(self, view):
        if self.in_remoteop: return
        if self.view == None: return
        if view.id() == self.view.id() and self.doc:
            self._apply_change(self.doc, self.doc.get_text(), self._get_text())

    def _on_view_post_save(self, view):
        if self.view == None: return
        if view.id() == self.view.id() and self.doc:
            view.set_scratch(False)

    def _on_view_close(self, view):
        if self.view == None: return
        if view.id() == self.view.id() and self.doc:
            self.close()

    def _apply_change(self, doc, oldval, newval):
        if oldval == newval:
            return

        commonStart = 0
        while commonStart < len(oldval) and commonStart < len(newval) and oldval[commonStart] == newval[commonStart]:
            commonStart+=1

        commonEnd = 0
        while commonEnd+commonStart < len(oldval) and commonEnd+commonStart < len(newval) and oldval[len(oldval)-1-commonEnd] == newval[len(newval)-1-commonEnd]:
            commonEnd+=1

        if len(oldval) != commonStart+commonEnd:
            doc.delete(commonStart, len(oldval)-commonStart-commonEnd)
        if len(newval) != commonStart+commonEnd:
            doc.insert(commonStart, newval[commonStart:len(newval)-commonEnd])

    def _on_doc_remoteop(self, op, old_snapshot):
        sublime.set_timeout(lambda: self._apply_remoteop(op), 0)

    def _get_text(self):
        return self.view.substr(sublime.Region(0, self.view.size())).replace('\r\n', '\n')

    def _initialize(self, text):
        if self._get_text() == text: return
        edit = self.view.begin_edit()
        self.view.replace(edit, sublime.Region(0, self.view.size()), text)
        self.view.end_edit(edit)

    def _apply_remoteop(self, op):
        self.in_remoteop = True
        edit = self.view.begin_edit()
        for component in op:
            if 'i' in component:
                self.view.insert(edit, component['p'], component['i'])
            else:
                self.view.erase(edit, sublime.Region(component['p'], component['p']+len(component['d'])))
        self.view.end_edit(edit)
        self.in_remoteop = False



client = None
server = None
editors = {}

class SublimeCollaboration(object):
    def connect(self, host):
        global client
        if client: self.disconnect()
        client = collab.client.CollabClient(host, 6633)
        client.on('error', lambda error: sublime.error_message("Client error: {0}".format(error)))
        client.on('closed', self.on_close)
        self.set_status()
        print("connected")

    def disconnect(self):
        global client
        if not client: return
        client.disconnect()
        self.set_status()

    def on_close(self, reason=None):
        global client
        if not client: return
        client = None
        self.set_status()
        print("disconnected")

    def open_get_docs(self, error, items):
        global client
        if not client: return

        if error:
            sublime.error_message("Error retrieving document names: {0}".format(error))
        else:
            if items:
                sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(items, lambda x: None if x < 0 else self.open(items[x])), 0)
            else:
                sublime.error_message("No documents availible to open")

    def open(self, name):
        global client
        if not client: return
        if name in editors:
            print(name+" is already open")
            return editors[name].focus()
        client.open(name, self.open_callback)
        self.set_status()

    def add_current(self, name):
        global client
        if not client: return
        if name in editors:
            print(name+" is already open")
            return editors[name].focus()
        view = sublime.active_window().active_view()
        if view.id() in (editor.view.id() for editor in editors.values()): return
        if view != None:
            client.open(name, lambda error, doc: self.add_callback(view, error, doc), snapshot=view.substr(sublime.Region(0, view.size())))
        self.set_status()

    def open_callback(self, error, doc):
        if error:
            sublime.error_message("Error opening document: {0}".format(error))
        else:
            sublime.set_timeout(lambda: self.create_editor(doc), 0)

    def add_callback(self, view, error, doc):
        if error:
            sublime.error_message("Error adding document: {0}".format(error))
        else:
            sublime.set_timeout(lambda: self.add_editor(view, doc), 0)

    def create_editor(self, doc):
        view = sublime.active_window().new_file()
        view.set_scratch(True)
        view.set_name(doc.name)
        self.add_editor(view, doc)
        self.set_status()

    def add_editor(self, view, doc):
        global editors
        editor = SublimeEditor(view, doc)
        editor.on('closed', lambda: editors.pop(doc.name))
        editors[doc.name] = editor

    def toggle_server(self):
        global server
        if server:
            server.close()
            server = None
            print("server closed")
        else:
            server = collab.server.CollabServer({'host':'127.0.0.1', 'port':6633})
            server.run_forever()
            print("server started")
        self.set_status()

    def set_status(self):
        global server, client

        if server or client:
            if server:
                server_status = 'running'
            else:
                server_status = 'off'

            if client:
                host = client.socket.host
                state = client.state
                client_status = 'client:%(host)s...%(state)s' % locals()
            else:
                client_status = 'disconnected'

            status_value = "Collab (server:%(server_status)s; %(client_status)s)" % locals()
        else:
            status_value = ''

        for view in sublime.active_window().views():
            view.set_status('collab_server_status', status_value)

class CollabConnectToServerCommand(sublime_plugin.ApplicationCommand, SublimeCollaboration):
    def run(self):
        sublime.active_window().show_input_panel("Enter server IP:", "localhost", self.connect, None, None)

class CollabDisconnectFromServerCommand(sublime_plugin.ApplicationCommand, SublimeCollaboration):
    def run(self):
        self.disconnect()
    def is_enabled(self):
        global client
        return client

class CollabToggleServerCommand(sublime_plugin.ApplicationCommand, SublimeCollaboration):
    def run(self):
        self.toggle_server()

class CollabOpenDocumentCommand(sublime_plugin.ApplicationCommand, SublimeCollaboration):
    def run(self):
        global client
        if not client: return
        client.get_docs(self.open_get_docs)
    def is_enabled(self):
        global client
        return client

class CollabAddCurrentDocumentCommand(sublime_plugin.ApplicationCommand, SublimeCollaboration):
    def run(self):
        global client, editors
        if not client: return
        if sublime.active_window() == None: return
        view = sublime.active_window().active_view()
        if view == None: return
        if view.id() in (editor.view.id() for editor in editors.values()): return
        sublime.active_window().show_input_panel("Enter new document name:", view.name(), self.add_current, None, None)
    def is_enabled(self):
        global client
        return client

class CollabToggleDebugCommand(sublime_plugin.ApplicationCommand, SublimeCollaboration):
    def run(self):
        collab.connection.debug = not collab.connection.debug

########NEW FILE########
__FILENAME__ = run_server
#!/usr/bin/env python
import sys
import collab

def main(argv):
    if len(argv) == 1:
        if ':' not in argv[0]:
            sys.stderr.write("please provide `host:port' to bind or just `host:' for default port\n")
            return -2
        else:
            host, port = argv[0].split(':', 1)
    elif len(argv) == 2:
        host,port = [x.strip() for x in argv]
    elif len(argv) > 2:
        sys.stderr.write("use `host:port' arguments\n")
        return -3
    else:
        host, port = '', ''

    if host == '':
        host = '0.0.0.0'
    if port == '':
        port = 6633
    try:
        sys.stderr.write('Starting at ' + host +':' + str(port) + '...')
        server = collab.server.CollabServer({'host':host, 'port': int(port)})
        sys.stderr.write(' started.\n')
        server.run_forever()
    except KeyboardInterrupt:
        print("^C received, server stopped")
        return -1

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

########NEW FILE########
