__FILENAME__ = echo_client
from pynanomsg import *
import sys

ADDRESS = "tcp://127.0.0.1:5556"

if len(sys.argv) != 2:
    sys.stderr.write("usage: %s msg\n" % sys.argv[0])
    sys.exit(1)
msg = sys.argv[1]
assert(len(msg) < 32) # TODO use NN_MSG

dom = Domain(AF_SP)
req = dom.socket(REQ)
req.setsockopt(REQ, REQ_RESEND_IVL, 1000)
req.connect(ADDRESS)
req.send(msg)
echo = req.recv(32) # TODO use NN_MSG
assert(echo == msg)

########NEW FILE########
__FILENAME__ = echo_server
from pynanomsg import *

ADDRESS = "tcp://127.0.0.1:5556"

dom = Domain(AF_SP)
rep = dom.socket(REP)

echo = ""
while echo != "EXIT":
    cid = rep.bind(ADDRESS)
    echo = rep.recv(32) # TODO use NN_MSG
    print "GOT: %s" % echo
    rep.send(echo)
    rep.shutdown(cid)

########NEW FILE########
__FILENAME__ = test_basic
from pynanomsg import *
from time import sleep
import unittest

class TestReqRep(unittest.TestCase):

    def test_reqrep(self):
        dom = Domain(AF_SP)
        sock_a = dom.socket(REQ)
        sock_a.connect('inproc://a')

        sock_b = dom.socket(REP)
        sock_b.bind('inproc://a')

        msg = 'ABC'
        sock_a.send(msg)
        assert sock_b.recv(3) == msg

        sock_a.close()
        sock_b.close()

class TestPair(unittest.TestCase):

    def test_pair(self):
        dom = Domain(AF_SP)
        sock_a = dom.socket(PAIR)
        sock_a.bind('inproc://a')

        sock_b = dom.socket(PAIR)
        sock_b.connect('inproc://a')

        msg = 'ABC'
        sock_a.send(msg)
        assert sock_b.recv(3) == msg

        sock_a.close()
        sock_b.close()

class TestPubSub(unittest.TestCase):

    def test_pubsub(self):
        dom = Domain(AF_SP)
        sock_a = dom.socket(PUB)
        sock_a.bind('inproc://a')

        sock_b = dom.socket(SUB)
        sock_b.connect('inproc://a')
        sock_b.setsockopt(SUB, SUB_SUBSCRIBE, "");

        msg = 'ABC'
        sock_a.send(msg)
        sleep(1)
        assert sock_b.recv(3) == msg

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
