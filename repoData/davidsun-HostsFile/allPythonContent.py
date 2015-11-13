__FILENAME__ = getHostsFile
import os
import sys
import socket
import threading

from lib import synchronizedOutput, synchronizedQueue

class myThread(threading.Thread) :
    def __init__(self, queue, output) :
        threading.Thread.__init__(self)
        self.queue = queue
        self.output = output
    def run(self) :
        while True :
            cur = self.queue.get()
            if (cur == None) : break
            try :
                result = socket.gethostbyname(cur)
                self.output.out(result + '\t' + cur)
            except : pass

if len(sys.argv) != 2 :
    print sys.argv[0] + ' <Input File>'
else :
    q = synchronizedQueue()
    out = synchronizedOutput()
    f = file(sys.argv[1])
    for line in f.readlines() :
        q.put(line[ : -1])
    threads = list()
    for i in range(0, 5) :
        t = myThread(q, out)
        t.start()
        threads.append(t)
    for t in threads :
        t.join()

########NEW FILE########
__FILENAME__ = lib
import threading
import Queue

class synchronizedQueue :
    def __init__(self) :
        self.lock = threading.Lock()
        self.queue = Queue.Queue()
    def put(self, e) :
        self.lock.acquire()
        self.queue.put(e)
        self.lock.release()
    def get(self) :
        self.lock.acquire()
        ret = None if self.queue.empty() else self.queue.get()
        self.lock.release()
        return ret

class synchronizedOutput : 
    def __init__(self) :
        self.lock = threading.Lock()
    def out(self, string) : 
        self.lock.acquire()
        print string
        self.lock.release()


########NEW FILE########
