__FILENAME__ = database
#!/usr/bin/env python
#Copyright (c) 2011 Fabula Solutions. All rights reserved.
#Use of this source code is governed by a BSD-style license that can be
#found in the license.txt file.

# leveldb client
import zmq
import threading
import time
import json

class leveldb(object):
    """leveldb client"""
    def __init__(self, host="tcp://127.0.0.1:5147", timeout=10*1000):
        self.host = host
        self.timeout = timeout
        self.connect()
    
    def connect(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.XREQ)
        self.socket.connect(self.host)
        
    def get(self, key):
        self.socket.send_multipart(['get', json.dumps(key)])
        return self.socket.recv_multipart()[0]
    
    def put(self, key, value):
        self.socket.send_multipart(['put', json.dumps([key, value])])
        return self.socket.recv_multipart()[0]
    
    def delete(self, key):
        self.socket.send_multipart(['delete',  json.dumps(key)])
        return self.socket.recv_multipart()[0]
    
    def range(self, start=None, end=None):
        self.socket.send_multipart(['range', json.dumps([start, end])])
        return self.socket.recv_multipart()[0]

    def close(self):
        self.socket.close()
        self.context.term()


########NEW FILE########
__FILENAME__ = database
#!/usr/bin/env python
#Copyright (c) 2011 Fabula Solutions. All rights reserved.
#Use of this source code is governed by a BSD-style license that can be
#found in the license.txt file.

# leveldb client
import zmq
import threading
import time
import json

class leveldb(object):
    """leveldb client"""
    def __init__(self, host="tcp://127.0.0.1:5147", timeout=10*1000):
        self.host = host
        self.timeout = timeout
        self.connect()
    
    def connect(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.XREQ)
        self.socket.connect(self.host)
        
    def get(self, key):
        self.socket.send_multipart(['get', json.dumps(key)])
        return self.socket.recv_multipart()[0]
    
    def put(self, key, value):
        self.socket.send_multipart(['put', json.dumps([key, value])])
        return self.socket.recv_multipart()[0]
    
    def delete(self, key):
        self.socket.send_multipart(['delete',  json.dumps(key)])
        return self.socket.recv_multipart()[0]
    
    def range(self, start=None, end=None):
        self.socket.send_multipart(['range', json.dumps([start, end])])
        return self.socket.recv_multipart()[0]

    def close(self):
        self.socket.close()
        self.context.term()


########NEW FILE########
__FILENAME__ = leveldb-server
#Copyright (c) 2011 Fabula Solutions. All rights reserved.
#Use of this source code is governed by a BSD-style license that can be
#found in the license.txt file.

# leveldb server 
import threading
import zmq
import leveldb
import json
import optparse
from time import sleep

class workerThread(threading.Thread):
    """workerThread"""
    def __init__(self, context, db):
        threading.Thread.__init__ (self)
        self.context = context
        self.db = db
        self.running = True
        self.processing = False
        self.socket = self.context.socket(zmq.XREQ)

    def run(self):
        self.socket.connect('inproc://backend')
        while self.running:
            try:
                msg = self.socket.recv_multipart()
            except zmq.ZMQError:
                self.running = False
                continue

            self.processing = True
            if  len(msg) != 3:
                value = 'None'
                reply = [msg[0], value]
                self.socket.send_multipart(reply)
                continue
            id = msg[0]
            op = msg[1]
            data = json.loads(msg[2])
            reply = [id]
            if op == 'get':
                try:
                    value = self.db.Get(data)
                except:
                    value = ""
                reply.append(value)
                
            elif op == 'put':
                try:
                    self.db.Put(data[0], data[1])
                    value = "True"
                except:
                    value = ""
                reply.append(value)
                
            elif op == 'delete':
                self.db.Delete(data)
                value = ""
                reply.append(value)
                
            elif op == 'range':
                start = data[0]
                end = data[1]
                if start and end:
                    try:
                        arr = []
                        for value in self.db.RangeIter(start, end):
                            arr.append({value[0]: value[1]})
                        reply.append(json.dumps(arr))
                    except:
                        value = ""
                        reply.append(value)
                else:
                    try:
                        arr = []
                        for value in self.db.RangeIter():
                            arr.append({value[0]: value[1]})
                        reply.append(json.dumps(arr))
                    except:
                        value = ""
                        reply.append(value)
            else:
                value = ""
                reply.append(value)
            self.socket.send_multipart(reply)
            self.processing = False

    def close(self):
        self.running = False
        while self.processing:
            sleep(1)
        self.socket.close()

if __name__ == "__main__":
    optparser = optparse.OptionParser(
        prog='leveldb-server.py',
        version='0.1.1',
        description='leveldb-server',
        usage='%prog \n\t-p [port and host settings] Default: tcp://127.0.0.1:5147\n' + \
                    '\t-f [database file name] Default: level.db')
    optparser.add_option('--host', '-p', dest='host',
        default='tcp://127.0.0.1:5147')
    optparser.add_option('--dbfile', '-d', dest='dbfile',
        default='level.db')
    options, arguments = optparser.parse_args()
    
    if not (options.host and options.dbfile):
        optparser.print_help()

    print "Starting leveldb-server %s" % options.host
    context = zmq.Context()
    frontend = context.socket(zmq.XREP)
    frontend.bind(options.host)
    backend = context.socket(zmq.XREQ)
    backend.bind('inproc://backend')

    poll = zmq.Poller()
    poll.register(frontend, zmq.POLLIN)
    poll.register(backend,  zmq.POLLIN)

    db = leveldb.LevelDB(options.dbfile)

    workers = []
    for i in xrange(3):
        worker = workerThread(context, db)
        worker.start()
        workers.append(worker)
            
    try:
        while True:
            sockets = dict(poll.poll())
            if frontend in sockets:
                if sockets[frontend] == zmq.POLLIN:
                    msg = frontend.recv_multipart()
                    backend.send_multipart(msg)
                    
            if backend in sockets:
                if sockets[backend] == zmq.POLLIN:
                    msg = backend.recv_multipart()
                    frontend.send_multipart(msg)
    except KeyboardInterrupt:
        for worker in workers:
            worker.close()
        frontend.close()
        backend.close()
        context.term()


########NEW FILE########
