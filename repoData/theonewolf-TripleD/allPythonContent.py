__FILENAME__ = cpfromddd
#!/usr/bin/env python

import libtripled, logging, sys, os

# CONSTANTS
log = logging.getLogger('tripled.cpfromddd')

def next_chunk(tripled, path):
    chunks = tripled.read_file(path)
    for chunk in chunks:
       log.debug('reading from worker[%s] path[%s]' % (chunk[0], chunk[1]))
       yield tripled.read_block(chunk[0], chunk[1]) 

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    if len(sys.argv) < 4:
        print '%s <master> <tripled src> <local dst>' % (sys.argv[0])
        exit(-1)

    tripled = libtripled.tripled(sys.argv[1])
    try: os.makedirs(os.path.dirname(sys.argv[3]))
    except OSError: pass
    with open(sys.argv[3], 'w') as f:
        for chunk in next_chunk(tripled, sys.argv[2]):
                f.write(chunk)

########NEW FILE########
__FILENAME__ = cptoddd
#!/usr/bin/env python

import libtripled, logging, sys, os

# CONSTANTS
log = logging.getLogger('tripled.cptoddd')
CHUNK_SIZE = 64*1024**2

def next_chunk(f):
    data = f.read(CHUNK_SIZE)
    while (data):
        yield data
        data = f.read(CHUNK_SIZE)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    
    if len(sys.argv) < 4:
        print '%s <master> <local src> <tripled dst>' % (sys.argv[0])
        exit(-1)

    tripled = libtripled.tripled(sys.argv[1])
    with open(sys.argv[2], 'r') as f:
        for i, chunk in enumerate(next_chunk(f)):
                tripled.write_block(sys.argv[3], i, chunk)

########NEW FILE########
__FILENAME__ = libtripled
#!/bin/env python

import logging, zmq

log = logging.getLogger('tripled.libtripled') 

class tripled:
    def __init__(self, master):
        self.context = zmq.Context()
        self.workers = {}
        self.master = self.get_master(master)

    def get_master(self, master):
        socket = self.context.socket(zmq.REQ)
        uri = 'tcp://%s:1337' % (master)
        log.debug('master connect string[%s]', uri)
        socket.connect(uri)
        return socket

    def get_worker(self, worker):
        if worker in self.workers:
            log.debug('using cached worker connection')
            worker = self.workers[worker]
        else:
            socket = self.context.socket(zmq.REQ)
            uri = 'tcp://%s:8008' % (worker)
            log.debug('worker connect string[%s]', uri)
            socket.connect(uri)
            self.workers[worker] = socket
            worker = self.workers[worker]
        return worker 

    def read_file(self, path):
        self.master.send_pyobj(('read', path), protocol=0)
        blocks = self.master.recv()
        log.debug('blocks: %s', blocks)
        return blocks

    def write_block(self, path, block, data):
        self.master.send_pyobj(('write', path, block), protocol=0)
        details = self.master.recv()
        self.worker_write_block(details[0], details[1], data)

    def read_block(self, worker, path):
        worker = self.get_worker(worker)
        worker.send_pyobj(('read',path), protocol=0)
        return worker.recv()

    def worker_write_block(self, worker, path, data):
        log.debug('writing[%s] to worker[%s]' % (path, worker))
        worker = self.get_worker(worker)
        log.debug('got socket...writing data[%d]' % (len(data)))
        worker.send_pyobj(('write', path, data), protocol=0)
        log.debug('sent message...')
        return worker.recv()

if __name__ == '__main__':
    print 'This is a library of client functions.'

########NEW FILE########
__FILENAME__ = lsddd
#!/usr/bin/env python

import logging, os, redis, sys

# CONSTANTS
REDIS_HOST = 'localhost'
log = logging.getLogger('tripled.ls')

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    if len(sys.argv) < 2:
        print '%s <path>' % (sys.argv[0])
        exit(-1)

    redis = redis.Redis(host=REDIS_HOST, port=6379, db=0)
    search_string = os.path.join(sys.argv[1], '*')
    log.info('searching: %s', search_string)
    print '\n'.join(redis.keys(search_string))

########NEW FILE########
__FILENAME__ = master
#!/usr/bin/env python

import fileinput, hashlib, logging, os, sys, redis, zmq

# CONSTANTS
log = logging.getLogger('tripled.master')
REDIS_SERVER = 'localhost'
CHUNK_DIR = '/tmp/tripled_chunks/'

class master:
    def __init__(self):
        self.redis = redis.Redis(host=REDIS_SERVER, port=6379, db=0)
        self.workers = []
        self.count = 0
        self.written_blocks = 0

    def add_worker(self, worker):
        self.workers.append(worker)
        self.count += 1

    def client_read_file(self, client, file):
        blocks = self.redis.lrange(file, 0, -1)
        client.send_pyobj(blocks, protocol=0)

    def client_write(self, client, file, block):
        worker = self.workers[self.written_blocks % self.count]
        directory = os.path.join(CHUNK_DIR, hashlib.sha256(file).hexdigest())
        path = os.path.join(directory, str(block))
        log.debug('writing to worker[%s] path[%s]'% (worker, path))
        self.written_blocks += 1
        serialized = (worker, path)
        self.redis.rpush(file, serialized)
        client.send_pyobj(serialized, protocol=0)

    def parse_client_command(self, client, command):
        log.debug('command: %s', command)
        if command[0] == 'read':
            self.client_read_file(client, command[1])
        elif command[0] == 'write':
            self.client_write(client, command[1], command[2])
        else:
            log.error('Error parsing client command.  Failing.')
            exit(-1)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    if len(sys.argv) < 2:
        print '%s <stdin | [<worker.cfg> [ worker2.cfg ...]]>' % (sys.argv[0])

    workers = []
    for line in fileinput.input():
        workers.append(line.strip())
        log.debug('new worker: %s', workers[-1])
        
    master = master()
    for worker in workers:
        master.add_worker(worker)
     
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind('tcp://*:1337')

    while True:
        master.parse_client_command(socket, socket.recv())

########NEW FILE########
__FILENAME__ = worker
#!/usr/bin/env python

import logging, os, zmq

log = logging.getLogger('tripled.worker')

class worker:
    def __init__(self):
        pass

    def client_read_block(self, client, path):
        log.info('worker reading block[%s]', path)
        with open(path, 'r') as f:
                client.send_pyobj(f.read(), protocol=0)

    def client_write_block(self, client, command):
        log.info('worker writing block[%s]', command[1])
        try: os.makedirs(os.path.dirname(command[1]))
        except OSError: pass
        with open(command[1], 'w') as f:
                f.write(command[2])
        client.send_pyobj(True, protocol=0)

    def parse_client_command(self, client, command):
        log.debug('command: %s' % (command[0:1]))
        if command[0] == 'read':
            self.client_read_block(client, command[1])
        elif command[0] == 'write':
            self.client_write_block(client, command)
        else:
            log.error('Error parsing client command. Failing.')
            exit(-1)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind('tcp://*:8008')

    worker = worker()
    
    while True:
        worker.parse_client_command(socket, socket.recv())

########NEW FILE########
