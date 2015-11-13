__FILENAME__ = get-poetry
# This is the asynchronous Get Poetry Now! client.

import datetime, errno, optparse, select, socket


def parse_args():
    usage = """usage: %prog [options] [hostname]:port ...

This is the Get Poetry Now! client, asynchronous edition.
Run it like this:

  python get-poetry.py port1 port2 port3 ...

If you are in the base directory of the twisted-intro package,
you could run it like this:

  python async-client/get-poetry.py 10001 10002 10003

to grab poetry from servers on ports 10001, 10002, and 10003.

Of course, there need to be servers listening on those ports
for that to work.
"""

    parser = optparse.OptionParser(usage)

    _, addresses = parser.parse_args()

    if not addresses:
        print parser.format_help()
        parser.exit()

    def parse_address(addr):
        if ':' not in addr:
            host = '127.0.0.1'
            port = addr
        else:
            host, port = addr.split(':', 1)

        if not port.isdigit():
            parser.error('Ports must be integers.')

        return host, int(port)

    return map(parse_address, addresses)


def get_poetry(sockets):
    """Download poety from all the given sockets."""

    poems = dict.fromkeys(sockets, '') # socket -> accumulated poem

    # socket -> task numbers
    sock2task = dict([(s, i + 1) for i, s in enumerate(sockets)])

    sockets = list(sockets) # make a copy

    # we go around this loop until we've gotten all the poetry
    # from all the sockets. This is the 'reactor loop'.

    while sockets:
        # this select call blocks until one or more of the
        # sockets is ready for read I/O
        rlist, _, _ = select.select(sockets, [], [])

        # rlist is the list of sockets with data ready to read

        for sock in rlist:
            data = ''

            while True:
                try:
                    new_data = sock.recv(1024)
                except socket.error, e:
                    if e.args[0] == errno.EWOULDBLOCK:
                        # this error code means we would have
                        # blocked if the socket was blocking.
                        # instead we skip to the next socket
                        break
                    raise
                else:
                    if not new_data:
                        break
                    else:
                        data += new_data

            # Each execution of this inner loop corresponds to
            # working on one asynchronous task in Figure 3 here:
            # http://krondo.com/?p=1209#figure3

            task_num = sock2task[sock]

            if not data:
                sockets.remove(sock)
                sock.close()
                print 'Task %d finished' % task_num
            else:
                addr_fmt = format_address(sock.getpeername())
                msg = 'Task %d: got %d bytes of poetry from %s'
                print  msg % (task_num, len(data), addr_fmt)

            poems[sock] += data

    return poems


def connect(address):
    """Connect to the given server and return a non-blocking socket."""

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(address)
    sock.setblocking(0)
    return sock


def format_address(address):
    host, port = address
    return '%s:%s' % (host or '127.0.0.1', port)


def main():
    addresses = parse_args()

    start = datetime.datetime.now()

    sockets = map(connect, addresses)

    poems = get_poetry(sockets)

    elapsed = datetime.datetime.now() - start

    for i, sock in enumerate(sockets):
        print 'Task %d: %d bytes of poetry' % (i + 1, len(poems[sock]))

    print 'Got %d poems in %s' % (len(addresses), elapsed)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = countdown

class Countdown(object):

    counter = 5

    def count(self):
        if self.counter == 0:
            reactor.stop()
        else:
            print self.counter, '...'
            self.counter -= 1
            reactor.callLater(1, self.count)

from twisted.internet import reactor

reactor.callWhenRunning(Countdown().count)

print 'Start!'
reactor.run()
print 'Stop!'

########NEW FILE########
__FILENAME__ = exception

def falldown():
    raise Exception('I fall down.')

def upagain():
    print 'But I get up again.'
    reactor.stop()

from twisted.internet import reactor

reactor.callWhenRunning(falldown)
reactor.callWhenRunning(upagain)

print 'Starting the reactor.'
reactor.run()

########NEW FILE########
__FILENAME__ = hello

def hello():
    print 'Hello from the reactor loop!'
    print 'Lately I feel like I\'m stuck in a rut.'

from twisted.internet import reactor

reactor.callWhenRunning(hello)

print 'Starting the reactor.'
reactor.run()

########NEW FILE########
__FILENAME__ = log
import sys

from twisted.python import log
from twisted.internet import defer

"""This example illustrates some Twisted logging basics."""

log.msg('This will not be logged, we have not installed a logger.')

log.startLogging(sys.stdout)

log.msg('This will be logged.')
log.err('This will be logged as an error.')

def bad_callback(result):
    xxx

try:
    bad_callback()
except:
    log.err('The next function call will log the traceback as an error.')
    log.err()

d = defer.Deferred()

def on_error(failure):
    log.err('The next function call will log the failure as an error.')
    log.err(failure)

d.addCallback(bad_callback)
d.addErrback(on_error)

d.callback(True)

log.msg('End of example.')

########NEW FILE########
__FILENAME__ = simple-poll
from twisted.internet import pollreactor
pollreactor.install()

from twisted.internet import reactor
reactor.run()

########NEW FILE########
__FILENAME__ = simple
from twisted.internet import reactor
reactor.run()

########NEW FILE########
__FILENAME__ = stack
import traceback

def stack():
    print 'The python stack:'
    traceback.print_stack()

from twisted.internet import reactor
reactor.callWhenRunning(stack)
reactor.run()

########NEW FILE########
__FILENAME__ = get-poetry
# This is the blocking Get Poetry Now! client.

import datetime, optparse, socket


def parse_args():
    usage = """usage: %prog [options] [hostname]:port ...

This is the Get Poetry Now! client, blocking edition.
Run it like this:

  python get-poetry.py port1 port2 port3 ...

If you are in the base directory of the twisted-intro package,
you could run it like this:

  python blocking-client/get-poetry.py 10001 10002 10003

to grab poetry from servers on ports 10001, 10002, and 10003.

Of course, there need to be servers listening on those ports
for that to work.
"""

    parser = optparse.OptionParser(usage)

    _, addresses = parser.parse_args()

    if not addresses:
        print parser.format_help()
        parser.exit()

    def parse_address(addr):
        if ':' not in addr:
            host = '127.0.0.1'
            port = addr
        else:
            host, port = addr.split(':', 1)

        if not port.isdigit():
            parser.error('Ports must be integers.')

        return host, int(port)

    return map(parse_address, addresses)


def get_poetry(address):
    """Download a piece of poetry from the given address."""

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(address)

    poem = ''

    while True:

        # This is the 'blocking' call in this synchronous program.
        # The recv() method will block for an indeterminate period
        # of time waiting for bytes to be received from the server.

        data = sock.recv(1024)

        if not data:
            sock.close()
            break

        poem += data

    return poem


def format_address(address):
    host, port = address
    return '%s:%s' % (host or '127.0.0.1', port)


def main():
    addresses = parse_args()

    elapsed = datetime.timedelta()

    for i, address in enumerate(addresses):
        addr_fmt = format_address(address)

        print 'Task %d: get poetry from: %s' % (i + 1, addr_fmt)

        start = datetime.datetime.now()

        # Each execution of 'get_poetry' corresponds to the
        # execution of one synchronous task in Figure 1 here:
        # http://krondo.com/?p=1209#figure1

        poem = get_poetry(address)

        time = datetime.datetime.now() - start

        msg = 'Task %d: got %d bytes of poetry from %s in %s'
        print  msg % (i + 1, len(poem), addr_fmt, time)

        elapsed += time

    print 'Got %d poems in %s' % (len(addresses), elapsed)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = slowpoetry
# This is the blocking version of the Slow Poetry Server.

import optparse, os, socket, time


def parse_args():
    usage = """usage: %prog [options] poetry-file

This is the Slow Poetry Server, blocking edition.
Run it like this:

  python slowpoetry.py <path-to-poetry-file>

If you are in the base directory of the twisted-intro package,
you could run it like this:

  python blocking-server/slowpoetry.py poetry/ecstasy.txt

to serve up John Donne's Ecstasy, which I know you want to do.
"""

    parser = optparse.OptionParser(usage)

    help = "The port to listen on. Default to a random available port."
    parser.add_option('--port', type='int', help=help)

    help = "The interface to listen on. Default is localhost."
    parser.add_option('--iface', help=help, default='localhost')

    help = "The number of seconds between sending bytes."
    parser.add_option('--delay', type='float', help=help, default=.7)

    help = "The number of bytes to send at a time."
    parser.add_option('--num-bytes', type='int', help=help, default=10)

    options, args = parser.parse_args()

    if len(args) != 1:
        parser.error('Provide exactly one poetry file.')

    poetry_file = args[0]

    if not os.path.exists(args[0]):
        parser.error('No such file: %s' % poetry_file)

    return options, poetry_file


def send_poetry(sock, poetry_file, num_bytes, delay):
    """Send some poetry slowly down the socket."""

    inputf = open(poetry_file)

    while True:
        bytes = inputf.read(num_bytes)

        if not bytes: # no more poetry :(
            sock.close()
            inputf.close()
            return

        print 'Sending %d bytes' % len(bytes)

        try:
            sock.sendall(bytes) # this is a blocking call
        except socket.error:
            sock.close()
            inputf.close()
            return

        time.sleep(delay)


def serve(listen_socket, poetry_file, num_bytes, delay):
    while True:
        sock, addr = listen_socket.accept()

        print 'Somebody at %s wants poetry!' % (addr,)

        send_poetry(sock, poetry_file, num_bytes, delay)


def main():
    options, poetry_file= parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((options.iface, options.port or 0))

    sock.listen(5)

    print 'Serving %s on port %s.' % (poetry_file, sock.getsockname()[1])

    serve(sock, poetry_file, options.num_bytes, options.delay)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = defer-cancel-1
from twisted.internet import defer

def callback(res):
    print 'callback got:', res

d = defer.Deferred()
d.addCallback(callback)
d.cancel()
print 'done'

########NEW FILE########
__FILENAME__ = defer-cancel-10
from twisted.internet.defer import Deferred

def send_poem(d):
    print 'Sending poem'
    d.callback('Once upon a midnight dreary')

def get_poem():
    """Return a poem 5 seconds later."""
    from twisted.internet import reactor
    d = Deferred()
    reactor.callLater(5, send_poem, d)
    return d


def got_poem(poem):
    print 'I got a poem:', poem

def poem_error(err):
    print 'get_poem failed:', err

def main():
    from twisted.internet import reactor
    reactor.callLater(10, reactor.stop) # stop the reactor in 10 seconds

    d = get_poem()
    d.addCallbacks(got_poem, poem_error)

    reactor.callLater(2, d.cancel) # cancel after 2 seconds

    reactor.run()

main()

########NEW FILE########
__FILENAME__ = defer-cancel-11
from twisted.internet.defer import Deferred

def send_poem(d):
    print 'Sending poem'
    d.callback('Once upon a midnight dreary')

def get_poem():
    """Return a poem 5 seconds later."""

    def canceler(d):
        # They don't want the poem anymore, so cancel the delayed call
        delayed_call.cancel()

        # At this point we have three choices:
        #   1. Do nothing, and the deferred will fire the errback
        #      chain with CancelledError.
        #   2. Fire the errback chain with a different error.
        #   3. Fire the callback chain with an alternative result.

    d = Deferred(canceler)

    from twisted.internet import reactor
    delayed_call = reactor.callLater(5, send_poem, d)

    return d


def got_poem(poem):
    print 'I got a poem:', poem

def poem_error(err):
    print 'get_poem failed:', err

def main():
    from twisted.internet import reactor
    reactor.callLater(10, reactor.stop) # stop the reactor in 10 seconds

    d = get_poem()
    d.addCallbacks(got_poem, poem_error)

    reactor.callLater(2, d.cancel) # cancel after 2 seconds

    reactor.run()

main()

########NEW FILE########
__FILENAME__ = defer-cancel-12
from twisted.internet import defer

def cancel_outer(d):
    print "outer cancel callback."

def cancel_inner(d):
    print "inner cancel callback."

def first_outer_callback(res):
    print 'first outer callback, returning inner deferred'
    return inner_d

def second_outer_callback(res):
    print 'second outer callback got:', res

def outer_errback(err):
    print 'outer errback got:', err

outer_d = defer.Deferred(cancel_outer)
inner_d = defer.Deferred(cancel_inner)

outer_d.addCallback(first_outer_callback)
outer_d.addCallbacks(second_outer_callback, outer_errback)

outer_d.callback('result')

# at this point the outer deferred has fired, but is paused
# on the inner deferred.

print 'canceling outer deferred.'
outer_d.cancel()

print 'done'

########NEW FILE########
__FILENAME__ = defer-cancel-2
from twisted.internet import defer

def callback(res):
    print 'callback got:', res

def errback(err):
    print 'errback got:', err

d = defer.Deferred()
d.addCallbacks(callback, errback)
d.cancel()
print 'done'

########NEW FILE########
__FILENAME__ = defer-cancel-3
from twisted.internet import defer

def callback(res):
    print 'callback got:', res

def errback(err):
    print 'errback got:', err

d = defer.Deferred()
d.addCallbacks(callback, errback)
d.callback('result')
d.cancel()
print 'done'

########NEW FILE########
__FILENAME__ = defer-cancel-4
from twisted.internet import defer

def callback(res):
    print 'callback got:', res

def errback(err):
    print 'errback got:', err

d = defer.Deferred()
d.addCallbacks(callback, errback)
d.cancel()
d.callback('result')
print 'done'

########NEW FILE########
__FILENAME__ = defer-cancel-5
from twisted.internet import defer

def canceller(d):
    print "I need to cancel this deferred:", d

def callback(res):
    print 'callback got:', res

def errback(err):
    print 'errback got:', err

d = defer.Deferred(canceller) # created by lower-level code
d.addCallbacks(callback, errback) # added by higher-level code
d.cancel()
print 'done'

########NEW FILE########
__FILENAME__ = defer-cancel-6
from twisted.internet import defer

def canceller(d):
    print "I need to cancel this deferred:", d
    print "Firing the deferred with a result"
    d.callback('result')

def callback(res):
    print 'callback got:', res

def errback(err):
    print 'errback got:', err

d = defer.Deferred(canceller) # created by lower-level code
d.addCallbacks(callback, errback) # added by higher-level code
d.cancel()
print 'done'

########NEW FILE########
__FILENAME__ = defer-cancel-7
from twisted.internet import defer

def canceller(d):
    print "I need to cancel this deferred:", d
    print "Firing the deferred with an error"
    d.errback(Exception('error!'))

def callback(res):
    print 'callback got:', res

def errback(err):
    print 'errback got:', err

d = defer.Deferred(canceller) # created by lower-level code
d.addCallbacks(callback, errback) # added by higher-level code
d.cancel()
print 'done'

########NEW FILE########
__FILENAME__ = defer-cancel-8
from twisted.internet import defer

def canceller(d):
    print "I need to cancel this deferred:", d

def callback(res):
    print 'callback got:', res

def errback(err):
    print 'errback got:', err

d = defer.Deferred(canceller) # created by lower-level code
d.addCallbacks(callback, errback) # added by higher-level code
d.callback('result')
d.cancel()
print 'done'

########NEW FILE########
__FILENAME__ = defer-cancel-9
from twisted.internet.defer import Deferred

def send_poem(d):
    print 'Sending poem'
    d.callback('Once upon a midnight dreary')

def get_poem():
    """Return a poem 5 seconds later."""
    from twisted.internet import reactor
    d = Deferred()
    reactor.callLater(5, send_poem, d)
    return d


def got_poem(poem):
    print 'I got a poem:', poem

def poem_error(err):
    print 'get_poem failed:', err

def main():
    from twisted.internet import reactor
    reactor.callLater(10, reactor.stop) # stop the reactor in 10 seconds

    d = get_poem()
    d.addCallbacks(got_poem, poem_error)

    reactor.run()

main()

########NEW FILE########
__FILENAME__ = deferred-list-1
from twisted.internet import defer

def got_results(res):
    print 'We got:', res

print 'Empty List.'
d = defer.DeferredList([])
print 'Adding Callback.'
d.addCallback(got_results)

########NEW FILE########
__FILENAME__ = deferred-list-2
from twisted.internet import defer

def got_results(res):
    print 'We got:', res

print 'One Deferred.'
d1 = defer.Deferred()
d = defer.DeferredList([d1])
print 'Adding Callback.'
d.addCallback(got_results)
print 'Firing d1.'
d1.callback('d1 result')

########NEW FILE########
__FILENAME__ = deferred-list-3
from twisted.internet import defer

def got_results(res):
    print 'We got:', res

print 'Two Deferreds.'
d1 = defer.Deferred()
d2 = defer.Deferred()
d = defer.DeferredList([d1, d2])
print 'Adding Callback.'
d.addCallback(got_results)
print 'Firing d1.'
d1.callback('d1 result')
print 'Firing d2.'
d2.callback('d2 result')

########NEW FILE########
__FILENAME__ = deferred-list-4
from twisted.internet import defer

def got_results(res):
    print 'We got:', res

print 'Two Deferreds.'
d1 = defer.Deferred()
d2 = defer.Deferred()
d = defer.DeferredList([d1, d2])
print 'Adding Callback.'
d.addCallback(got_results)
print 'Firing d2.'
d2.callback('d2 result')
print 'Firing d1.'
d1.callback('d1 result')

########NEW FILE########
__FILENAME__ = deferred-list-5
from twisted.internet import defer

def got_results(res):
    print 'We got:', res

d1 = defer.Deferred()
d2 = defer.Deferred()
d = defer.DeferredList([d1, d2], consumeErrors=True)
d.addCallback(got_results)
print 'Firing d1.'
d1.callback('d1 result')
print 'Firing d2 with errback.'
d2.errback(Exception('d2 failure'))

########NEW FILE########
__FILENAME__ = deferred-list-6
from twisted.internet import defer

def got_results(res):
    print 'We got:', res

d1 = defer.Deferred()
d2 = defer.Deferred()
d = defer.DeferredList([d1, d2])
d.addCallback(got_results)
print 'Firing d1.'
d1.callback('d1 result')
print 'Firing d2 with errback.'
d2.errback(Exception('d2 failure'))

########NEW FILE########
__FILENAME__ = deferred-list-7
from twisted.internet import defer

def got_results(res):
    print 'We got:', res

d1 = defer.Deferred()
d2 = defer.Deferred()
d = defer.DeferredList([d1, d2])
d2.addErrback(lambda err: None) # handle d2 error
d.addCallback(got_results)
print 'Firing d1.'
d1.callback('d1 result')
print 'Firing d2 with errback.'
d2.errback(Exception('d2 failure'))

########NEW FILE########
__FILENAME__ = gen-1

def my_generator():
    print 'starting up'
    yield 1
    print "workin'"
    yield 2
    print "still workin'"
    yield 3
    print 'done'

for n in my_generator():
    print n

########NEW FILE########
__FILENAME__ = gen-2

def my_generator():
    print 'starting up'
    yield 1
    print "workin'"
    yield 2
    print "still workin'"
    yield 3
    print 'done'

gen = my_generator()

while True:
    try:
        n = gen.next()
    except StopIteration:
        break
    else:
        print n

########NEW FILE########
__FILENAME__ = gen-3

def my_generator():
    yield 1
    yield 2
    yield 3

def my_other_generator():
    yield 10
    yield 20
    yield 30
    yield 40

gens = [my_generator(), my_other_generator()]

while gens:
    for g in gens[:]:
        try:
            n = g.next()
        except StopIteration:
            gens.remove(g)
        else:
            print n

########NEW FILE########
__FILENAME__ = gen-4

class Malfunction(Exception):
    pass

def my_generator():
    print 'starting up'

    val = yield 1
    print 'got:', val

    val = yield 2
    print 'got:', val

    try:
        yield 3
    except Malfunction:
        print 'malfunction!'

    yield 4

    print 'done'

gen = my_generator()

print gen.next() # start the generator
print gen.send(10) # send the value 10
print gen.send(20) # send the value 20
print gen.throw(Malfunction()) # raise an exception inside the generator

try:
    gen.next()
except StopIteration:
    pass

########NEW FILE########
__FILENAME__ = inline-callbacks-1

from twisted.internet.defer import inlineCallbacks, Deferred

@inlineCallbacks
def my_callbacks():
    from twisted.internet import reactor

    print 'first callback'
    result = yield 1 # yielded values that aren't deferred come right back

    print 'second callback got', result
    d = Deferred()
    reactor.callLater(5, d.callback, 2)
    result = yield d # yielded deferreds will pause the generator

    print 'third callback got', result # the result of the deferred

    d = Deferred()
    reactor.callLater(5, d.errback, Exception(3))

    try:
        yield d
    except Exception, e:
        result = e

    print 'fourth callback got', repr(result) # the exception from the deferred

    reactor.stop()

from twisted.internet import reactor
reactor.callWhenRunning(my_callbacks)
reactor.run()

########NEW FILE########
__FILENAME__ = inline-callbacks-2

from twisted.internet.defer import inlineCallbacks, Deferred, returnValue

@inlineCallbacks
def my_callbacks_1():
    from twisted.internet import reactor

    print 'my_callbacks_1 first callback'
    d = Deferred()
    reactor.callLater(2, d.callback, None)
    yield d

    print 'my_callbacks_1 second callback'
    d = Deferred()
    reactor.callLater(2, d.callback, None)
    yield d

    print 'my_callbacks_1 third callback'
    returnValue(1)

@inlineCallbacks
def my_callbacks_err():
    from twisted.internet import reactor

    print 'my_callbacks_err first callback'
    d = Deferred()
    reactor.callLater(3, d.callback, None)
    yield d

    print 'my_callbacks_err second callback'
    d = Deferred()
    reactor.callLater(3, d.callback, None)
    yield d

    print 'my_callbacks_err third callback'
    raise Exception('uh oh')

def got_result(res):
    print 'got result:', res

def got_error(err):
    print 'got error:', err

def run_callbacks():
    d1 = my_callbacks_1()
    d1.addCallbacks(got_result, got_error)

    d2 = my_callbacks_err()
    d2.addCallbacks(got_result, got_error)

    from twisted.internet import reactor

    def callbacks_finished(_):
        callbacks_finished.count += 1
        if callbacks_finished.count == 2:
            print 'all done'
            reactor.stop()
    callbacks_finished.count = 0

    d1.addBoth(callbacks_finished)
    d2.addBoth(callbacks_finished)


from twisted.internet import reactor
reactor.callWhenRunning(run_callbacks)
reactor.run()

########NEW FILE########
__FILENAME__ = inline-callbacks-tb

import traceback

from twisted.internet.defer import inlineCallbacks

@inlineCallbacks
def my_callbacks():
    yield 1
    traceback.print_stack()
    from twisted.internet import reactor
    reactor.stop()

from twisted.internet import reactor
reactor.callWhenRunning(my_callbacks)
reactor.run()

########NEW FILE########
__FILENAME__ = get-poetry
import optparse, sys

from twisted.internet import defer
from twisted.internet.protocol import Protocol, ClientFactory


class TimeoutError(Exception):
    pass


def parse_args():
    usage = """usage: %prog [options] [hostname]:port ...

Get Poetry Now!

Run it like this:

  python get-poetry.py port1 port2 port3 ...
"""

    parser = optparse.OptionParser(usage)

    help = "Timeout in seconds."
    parser.add_option('-t', '--timeout', type='float', help=help, default=5.0)

    options, addresses = parser.parse_args()

    if not addresses:
        print parser.format_help()
        parser.exit()

    def parse_address(addr):
        if ':' not in addr:
            host = '127.0.0.1'
            port = addr
        else:
            host, port = addr.split(':', 1)

        if not port.isdigit():
            parser.error('Ports must be integers.')

        return host, int(port)

    return map(parse_address, addresses), options


class PoetryProtocol(Protocol):

    poem = ''

    def dataReceived(self, data):
        self.poem += data

    def connectionLost(self, reason):
        self.poemReceived(self.poem)

    def poemReceived(self, poem):
        self.factory.poem_finished(poem)


class PoetryClientFactory(ClientFactory):

    protocol = PoetryProtocol

    def __init__(self, deferred, timeout):
        self.deferred = deferred
        self.timeout = timeout
        self.timeout_call = None

    def startedConnecting(self, connector):
        from twisted.internet import reactor
        self.timeout_call = reactor.callLater(self.timeout,
                                              self.on_timeout,
                                              connector)

    def poem_finished(self, poem):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.callback(poem)
        self.cancel_timeout()

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason)
        self.cancel_timeout()

    def on_timeout(self, connector):
        self.timeout_call = None

        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(TimeoutError())
            connector.disconnect()

    def cancel_timeout(self):
        if self.timeout_call is not None:
            call, self.timeout_call = self.timeout_call, None
            call.cancel()


def get_poetry(host, port, timeout):
    """
    Download a poem from the given host and port. This function
    returns a Deferred which will be fired with the complete text of
    the poem or a Failure if the poem could not be downloaded.

    If timeout seconds elapse before the poem is received, the
    Deferred will fire with a TimeoutError.
    """
    d = defer.Deferred()
    from twisted.internet import reactor
    factory = PoetryClientFactory(d, timeout)
    reactor.connectTCP(host, port, factory)
    return d


def poetry_main():
    addresses, options = parse_args()

    from twisted.internet import reactor

    poems = []
    errors = []

    def got_poem(poem):
        poems.append(poem)

    def poem_failed(err):
        print >>sys.stderr, 'Poem failed:', err
        errors.append(err)

    def poem_done(_):
        if len(poems) + len(errors) == len(addresses):
            reactor.stop()

    for address in addresses:
        host, port = address
        d = get_poetry(host, port, options.timeout)
        d.addCallbacks(got_poem, poem_failed)
        d.addBoth(poem_done)

    reactor.run()

    for poem in poems:
        print poem


if __name__ == '__main__':
    poetry_main()

########NEW FILE########
__FILENAME__ = test_poetry
from twisted.internet.defer import Deferred
from twisted.internet.error import ConnectError
from twisted.internet.protocol import ClientFactory, ServerFactory, Protocol
from twisted.trial.unittest import TestCase

# Normally we would import the classes we want to test.
# But to make the examples self-contained, we're just
# copying them here, with a few modifications.

class PoetryServerProtocol(Protocol):

    def connectionMade(self):
        self.transport.write(self.factory.poem)
        self.transport.loseConnection()

class PoetryServerFactory(ServerFactory):

    protocol = PoetryServerProtocol

    def __init__(self, poem):
        self.poem = poem


class PoetryClientProtocol(Protocol):

    poem = ''

    def dataReceived(self, data):
        self.poem += data

    def connectionLost(self, reason):
        self.poemReceived(self.poem)

    def poemReceived(self, poem):
        self.factory.poem_finished(poem)


class PoetryClientFactory(ClientFactory):

    protocol = PoetryClientProtocol

    def __init__(self):
        self.deferred = Deferred()

    def poem_finished(self, poem):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.callback(poem)

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason)


def get_poetry(host, port):
    from twisted.internet import reactor
    factory = PoetryClientFactory()
    reactor.connectTCP(host, port, factory)
    return factory.deferred


TEST_POEM = '''\
This is a test.
This is only a test.'''


class PoetryTestCase(TestCase):

    def setUp(self):
        factory = PoetryServerFactory(TEST_POEM)
        from twisted.internet import reactor
        self.port = reactor.listenTCP(0, factory, interface="127.0.0.1")
        self.portnum = self.port.getHost().port

    def tearDown(self):
        port, self.port = self.port, None
        return port.stopListening()

    def test_client(self):
        """The correct poem is returned by get_poetry."""
        d = get_poetry('127.0.0.1', self.portnum)

        def got_poem(poem):
            self.assertEquals(poem, TEST_POEM)

        d.addCallback(got_poem)

        return d

    def test_failure(self):
        """The correct failure is returned by get_poetry when
        connecting to a port with no server."""
        d = get_poetry('127.0.0.1', 0)
        return self.assertFailure(d, ConnectError)

########NEW FILE########
__FILENAME__ = fastpoetry_plugin
# This is the Twisted Fast Poetry Server, version 3.0

from zope.interface import implements

from twisted.python import usage, log
from twisted.plugin import IPlugin
from twisted.internet.protocol import ServerFactory, Protocol
from twisted.application import internet, service


# Normally we would import these classes from another module.

class PoetryProtocol(Protocol):

    def connectionMade(self):
        poem = self.factory.service.poem
        log.msg('sending %d bytes of poetry to %s'
                % (len(poem), self.transport.getPeer()))
        self.transport.write(poem)
        self.transport.loseConnection()


class PoetryFactory(ServerFactory):

    protocol = PoetryProtocol

    def __init__(self, service):
        self.service = service


class PoetryService(service.Service):

    def __init__(self, poetry_file):
        self.poetry_file = poetry_file

    def startService(self):
        service.Service.startService(self)
        self.poem = open(self.poetry_file).read()
        log.msg('loaded a poem from: %s' % (self.poetry_file,))


# This is the main body of the plugin. First we define
# our command-line options.

class Options(usage.Options):

    optParameters = [
        ['port', 'p', 10000, 'The port number to listen on.'],
        ['poem', None, None, 'The file containing the poem.'],
        ['iface', None, 'localhost', 'The interface to listen on.'],
        ]

# Now we define our 'service maker', an object which knows
# how to construct our service.

class PoetryServiceMaker(object):

    implements(service.IServiceMaker, IPlugin)

    tapname = "fastpoetry"
    description = "A fast poetry service."
    options = Options

    def makeService(self, options):
        top_service = service.MultiService()

        poetry_service = PoetryService(options['poem'])
        poetry_service.setServiceParent(top_service)

        factory = PoetryFactory(poetry_service)
        tcp_service = internet.TCPServer(int(options['port']), factory,
                                         interface=options['iface'])
        tcp_service.setServiceParent(top_service)

        return top_service

# This variable name is irrelevent. What matters is that
# instances of PoetryServiceMaker implement IServiceMaker
# and IPlugin.

service_maker = PoetryServiceMaker()

########NEW FILE########
__FILENAME__ = get-poetry-broken
# This is the *Broken* Twisted Get Poetry Now! client, version 1.0.

# NOTE: This should not be used as the basis for production code.
# It uses low-level Twisted APIs as a learning exercise.

# Also, it's totally broken. See the explanation in Part 4
# to understand why.

import datetime, optparse, socket

from twisted.internet import main


def parse_args():
    usage = """usage: %prog [options] [hostname]:port ...

This is the *Broken* Get Poetry Now! client, Twisted version 1.0.
Run it like this:

  python get-poetry-broken.py port1 port2 port3 ...

If you are in the base directory of the twisted-intro package,
you could run it like this:

  python twisted-client-1/get-poetry-broken.py 10001 10002 10003

to grab poetry from servers on ports 10001, 10002, and 10003.

Of course, there need to be servers listening on those ports
for that to work.
"""

    parser = optparse.OptionParser(usage)

    _, addresses = parser.parse_args()

    if not addresses:
        print parser.format_help()
        parser.exit()

    def parse_address(addr):
        if ':' not in addr:
            host = '127.0.0.1'
            port = addr
        else:
            host, port = addr.split(':', 1)

        if not port.isdigit():
            parser.error('Ports must be integers.')

        return host, int(port)

    return map(parse_address, addresses)


class PoetrySocket(object):

    poem = ''

    def __init__(self, task_num, address):
        self.task_num = task_num
        self.address = address
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(address)
        #self.sock.setblocking(0) we don't set non-blocking -- broken!

        # tell the Twisted reactor to monitor this socket for reading
        from twisted.internet import reactor
        reactor.addReader(self)

    def fileno(self):
        try:
            return self.sock.fileno()
        except socket.error:
            return -1

    def connectionLost(self, reason):
        self.sock.close()

        # stop monitoring this socket
        from twisted.internet import reactor
        reactor.removeReader(self)

        # see if there are any poetry sockets left
        for reader in reactor.getReaders():
            if isinstance(reader, PoetrySocket):
                return

        reactor.stop() # no more poetry

    def doRead(self):
        poem = ''

        while True: # we're just reading everything (blocking) -- broken!
            bytes = self.sock.recv(1024)
            if not bytes:
                break
            poem += bytes

        msg = 'Task %d: got %d bytes of poetry from %s'
        print  msg % (self.task_num, len(poem), self.format_addr())

        self.poem = poem

        return main.CONNECTION_DONE

    def logPrefix(self):
        return 'poetry'

    def format_addr(self):
        host, port = self.address
        return '%s:%s' % (host or '127.0.0.1', port)


def poetry_main():
    addresses = parse_args()

    start = datetime.datetime.now()

    sockets = [PoetrySocket(i + 1, addr) for i, addr in enumerate(addresses)]

    from twisted.internet import reactor
    reactor.run()

    elapsed = datetime.datetime.now() - start

    for i, sock in enumerate(sockets):
        print 'Task %d: %d bytes of poetry' % (i + 1, len(sock.poem))

    print 'Got %d poems in %s' % (len(addresses), elapsed)


if __name__ == '__main__':
    poetry_main()

########NEW FILE########
__FILENAME__ = get-poetry
# This is the Twisted Get Poetry Now! client, version 1.0.

# NOTE: This should not be used as the basis for production code.
# It uses low-level Twisted APIs as a learning exercise.

import datetime, errno, optparse, socket

from twisted.internet import main


def parse_args():
    usage = """usage: %prog [options] [hostname]:port ...

This is the Get Poetry Now! client, Twisted version 1.0.
Run it like this:

  python get-poetry.py port1 port2 port3 ...

If you are in the base directory of the twisted-intro package,
you could run it like this:

  python twisted-client-1/get-poetry.py 10001 10002 10003

to grab poetry from servers on ports 10001, 10002, and 10003.

Of course, there need to be servers listening on those ports
for that to work.
"""

    parser = optparse.OptionParser(usage)

    _, addresses = parser.parse_args()

    if not addresses:
        print parser.format_help()
        parser.exit()

    def parse_address(addr):
        if ':' not in addr:
            host = '127.0.0.1'
            port = addr
        else:
            host, port = addr.split(':', 1)

        if not port.isdigit():
            parser.error('Ports must be integers.')

        return host, int(port)

    return map(parse_address, addresses)


class PoetrySocket(object):

    poem = ''

    def __init__(self, task_num, address):
        self.task_num = task_num
        self.address = address
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(address)
        self.sock.setblocking(0)

        # tell the Twisted reactor to monitor this socket for reading
        from twisted.internet import reactor
        reactor.addReader(self)

    def fileno(self):
        try:
            return self.sock.fileno()
        except socket.error:
            return -1

    def connectionLost(self, reason):
        self.sock.close()

        # stop monitoring this socket
        from twisted.internet import reactor
        reactor.removeReader(self)

        # see if there are any poetry sockets left
        for reader in reactor.getReaders():
            if isinstance(reader, PoetrySocket):
                return

        reactor.stop() # no more poetry

    def doRead(self):
        bytes = ''

        while True:
            try:
                bytesread = self.sock.recv(1024)
                if not bytesread:
                    break
                else:
                    bytes += bytesread
            except socket.error, e:
                if e.args[0] == errno.EWOULDBLOCK:
                    break
                return main.CONNECTION_LOST

        if not bytes:
            print 'Task %d finished' % self.task_num
            return main.CONNECTION_DONE
        else:
            msg = 'Task %d: got %d bytes of poetry from %s'
            print  msg % (self.task_num, len(bytes), self.format_addr())

        self.poem += bytes

    def logPrefix(self):
        return 'poetry'

    def format_addr(self):
        host, port = self.address
        return '%s:%s' % (host or '127.0.0.1', port)


def poetry_main():
    addresses = parse_args()

    start = datetime.datetime.now()

    sockets = [PoetrySocket(i + 1, addr) for i, addr in enumerate(addresses)]

    from twisted.internet import reactor
    reactor.run()

    elapsed = datetime.datetime.now() - start

    for i, sock in enumerate(sockets):
        print 'Task %d: %d bytes of poetry' % (i + 1, len(sock.poem))

    print 'Got %d poems in %s' % (len(addresses), elapsed)


if __name__ == '__main__':
    poetry_main()

########NEW FILE########
__FILENAME__ = get-poetry-simple
# This is the Twisted Get Poetry Now! client, version 2.1.

# NOTE: This should not be used as the basis for production code.

import optparse

from twisted.internet.protocol import Protocol, ClientFactory


def parse_args():
    usage = """usage: %prog [options] [hostname]:port ...

This is the Get Poetry Now! client, Twisted version 2.1.
Run it like this:

  python get-poetry-simple.py port1 port2 port3 ...

If you are in the base directory of the twisted-intro package,
you could run it like this:

  python twisted-client-2/get-poetry-simple.py 10001 10002 10003

to grab poetry from servers on ports 10001, 10002, and 10003.

Of course, there need to be servers listening on those ports
for that to work.
"""

    parser = optparse.OptionParser(usage)

    _, addresses = parser.parse_args()

    if not addresses:
        print parser.format_help()
        parser.exit()

    def parse_address(addr):
        if ':' not in addr:
            host = '127.0.0.1'
            port = addr
        else:
            host, port = addr.split(':', 1)

        if not port.isdigit():
            parser.error('Ports must be integers.')

        return host, int(port)

    return map(parse_address, addresses)


class PoetryProtocol(Protocol):

    poem = ''

    def dataReceived(self, data):
        self.poem += data

    def connectionLost(self, reason):
        self.poemReceived(self.poem)

    def poemReceived(self, poem):
        self.factory.poem_finished(poem)


class PoetryClientFactory(ClientFactory):

    protocol = PoetryProtocol # tell base class what proto to build

    def __init__(self, poetry_count):
        self.poetry_count = poetry_count
        self.poems = []

    def poem_finished(self, poem=None):
        if poem is not None:
            self.poems.append(poem)

        self.poetry_count -= 1

        if self.poetry_count == 0:
            self.report()
            from twisted.internet import reactor
            reactor.stop()

    def report(self):
        for poem in self.poems:
            print poem

    def clientConnectionFailed(self, connector, reason):
        print 'Failed to connect to:', connector.getDestination()
        self.poem_finished()


def poetry_main():
    addresses = parse_args()

    factory = PoetryClientFactory(len(addresses))

    from twisted.internet import reactor

    for address in addresses:
        host, port = address
        reactor.connectTCP(host, port, factory)

    reactor.run()


if __name__ == '__main__':
    poetry_main()

########NEW FILE########
__FILENAME__ = get-poetry-stack
# This is the Twisted Get Poetry Now! client, version 2.0, with stacktrace.

# NOTE: This should not be used as the basis for production code.

import datetime, optparse, os, traceback

from twisted.internet.protocol import Protocol, ClientFactory


def parse_args():
    usage = """usage: %prog [options] [hostname]:port ...

This is the Get Poetry Now! client, Twisted version 2.0, with stacktrace.
Run it like this:

  python get-poetry-stack.py port1 port2 port3 ...

If you are in the base directory of the twisted-intro package,
you could run it like this:

  python twisted-client-2/get-poetry-stack.py 10001 10002 10003

But it's just going to print out a stacktrace as soon as it
gets the first bits of a poem.
"""

    parser = optparse.OptionParser(usage)

    _, addresses = parser.parse_args()

    if not addresses:
        print parser.format_help()
        parser.exit()

    def parse_address(addr):
        if ':' not in addr:
            host = '127.0.0.1'
            port = addr
        else:
            host, port = addr.split(':', 1)

        if not port.isdigit():
            parser.error('Ports must be integers.')

        return host, int(port)

    return map(parse_address, addresses)


class PoetryProtocol(Protocol):

    poem = ''
    task_num = 0

    def dataReceived(self, data):
        traceback.print_stack()
        os._exit(0)

    def connectionLost(self, reason):
        self.poemReceived(self.poem)

    def poemReceived(self, poem):
        self.factory.poem_finished(self.task_num, poem)


class PoetryClientFactory(ClientFactory):

    task_num = 1

    protocol = PoetryProtocol # tell base class what proto to build

    def __init__(self, poetry_count):
        self.poetry_count = poetry_count
        self.poems = {} # task num -> poem

    def buildProtocol(self, address):
        proto = ClientFactory.buildProtocol(self, address)
        proto.task_num = self.task_num
        self.task_num += 1
        return proto

    def poem_finished(self, task_num=None, poem=None):
        if task_num is not None:
            self.poems[task_num] = poem

        self.poetry_count -= 1

        if self.poetry_count == 0:
            self.report()
            from twisted.internet import reactor
            reactor.stop()

    def report(self):
        for i in self.poems:
            print 'Task %d: %d bytes of poetry' % (i, len(self.poems[i]))

    def clientConnectionFailed(self, connector, reason):
        print 'Failed to connect to:', connector.getDestination()
        self.poem_finished()


def poetry_main():
    addresses = parse_args()

    start = datetime.datetime.now()

    factory = PoetryClientFactory(len(addresses))

    from twisted.internet import reactor

    for address in addresses:
        host, port = address
        reactor.connectTCP(host, port, factory)

    reactor.run()

    elapsed = datetime.datetime.now() - start

    print 'Got %d poems in %s' % (len(addresses), elapsed)


if __name__ == '__main__':
    poetry_main()

########NEW FILE########
__FILENAME__ = get-poetry
# This is the Twisted Get Poetry Now! client, version 2.0.

# NOTE: This should not be used as the basis for production code.

import datetime, optparse

from twisted.internet.protocol import Protocol, ClientFactory


def parse_args():
    usage = """usage: %prog [options] [hostname]:port ...

This is the Get Poetry Now! client, Twisted version 2.0.
Run it like this:

  python get-poetry.py port1 port2 port3 ...

If you are in the base directory of the twisted-intro package,
you could run it like this:

  python twisted-client-2/get-poetry.py 10001 10002 10003

to grab poetry from servers on ports 10001, 10002, and 10003.

Of course, there need to be servers listening on those ports
for that to work.
"""

    parser = optparse.OptionParser(usage)

    _, addresses = parser.parse_args()

    if not addresses:
        print parser.format_help()
        parser.exit()

    def parse_address(addr):
        if ':' not in addr:
            host = '127.0.0.1'
            port = addr
        else:
            host, port = addr.split(':', 1)

        if not port.isdigit():
            parser.error('Ports must be integers.')

        return host, int(port)

    return map(parse_address, addresses)


class PoetryProtocol(Protocol):

    poem = ''
    task_num = 0

    def dataReceived(self, data):
        self.poem += data
        msg = 'Task %d: got %d bytes of poetry from %s'
        print  msg % (self.task_num, len(data), self.transport.getPeer())

    def connectionLost(self, reason):
        self.poemReceived(self.poem)

    def poemReceived(self, poem):
        self.factory.poem_finished(self.task_num, poem)


class PoetryClientFactory(ClientFactory):

    task_num = 1

    protocol = PoetryProtocol # tell base class what proto to build

    def __init__(self, poetry_count):
        self.poetry_count = poetry_count
        self.poems = {} # task num -> poem

    def buildProtocol(self, address):
        proto = ClientFactory.buildProtocol(self, address)
        proto.task_num = self.task_num
        self.task_num += 1
        return proto

    def poem_finished(self, task_num=None, poem=None):
        if task_num is not None:
            self.poems[task_num] = poem

        self.poetry_count -= 1

        if self.poetry_count == 0:
            self.report()
            from twisted.internet import reactor
            reactor.stop()

    def report(self):
        for i in self.poems:
            print 'Task %d: %d bytes of poetry' % (i, len(self.poems[i]))

    def clientConnectionFailed(self, connector, reason):
        print 'Failed to connect to:', connector.getDestination()
        self.poem_finished()


def poetry_main():
    addresses = parse_args()

    start = datetime.datetime.now()

    factory = PoetryClientFactory(len(addresses))

    from twisted.internet import reactor

    for address in addresses:
        host, port = address
        reactor.connectTCP(host, port, factory)

    reactor.run()

    elapsed = datetime.datetime.now() - start

    print 'Got %d poems in %s' % (len(addresses), elapsed)


if __name__ == '__main__':
    poetry_main()

########NEW FILE########
__FILENAME__ = get-poetry-1
# This is the Twisted Get Poetry Now! client, version 3.1.

# NOTE: This should not be used as the basis for production code.

import optparse, sys

from twisted.internet.protocol import Protocol, ClientFactory


def parse_args():
    usage = """usage: %prog [options] [hostname]:port ...

This is the Get Poetry Now! client, Twisted version 3.1
Run it like this:

  python get-poetry-1.py port1 port2 port3 ...

If you are in the base directory of the twisted-intro package,
you could run it like this:

  python twisted-client-3/get-poetry-1.py 10001 10002 10003

to grab poetry from servers on ports 10001, 10002, and 10003.

Of course, there need to be servers listening on those ports
for that to work.
"""

    parser = optparse.OptionParser(usage)

    _, addresses = parser.parse_args()

    if not addresses:
        print parser.format_help()
        parser.exit()

    def parse_address(addr):
        if ':' not in addr:
            host = '127.0.0.1'
            port = addr
        else:
            host, port = addr.split(':', 1)

        if not port.isdigit():
            parser.error('Ports must be integers.')

        return host, int(port)

    return map(parse_address, addresses)


class PoetryProtocol(Protocol):

    poem = ''

    def dataReceived(self, data):
        self.poem += data

    def connectionLost(self, reason):
        self.poemReceived(self.poem)

    def poemReceived(self, poem):
        self.factory.poem_finished(poem)


class PoetryClientFactory(ClientFactory):

    protocol = PoetryProtocol

    def __init__(self, callback, errback):
        self.callback = callback
        self.errback = errback

    def poem_finished(self, poem):
        self.callback(poem)

    def clientConnectionFailed(self, connector, reason):
        self.errback(reason)


def get_poetry(host, port, callback, errback):
    """
    Download a poem from the given host and port and invoke

      callback(poem)

    when the poem is complete. If there is a failure, invoke:

      errback(err)

    instead, where err is a twisted.python.failure.Failure instance.
    """
    from twisted.internet import reactor
    factory = PoetryClientFactory(callback, errback)
    reactor.connectTCP(host, port, factory)


def poetry_main():
    addresses = parse_args()

    from twisted.internet import reactor

    poems = []
    errors = []

    def got_poem(poem):
        poems.append(poem)
        poem_done()

    def poem_failed(err):
        print >>sys.stderr, 'Poem failed:', err
        errors.append(err)
        poem_done()

    def poem_done():
        if len(poems) + len(errors) == len(addresses):
            reactor.stop()

    for address in addresses:
        host, port = address
        get_poetry(host, port, got_poem, poem_failed)

    reactor.run()

    for poem in poems:
        print poem


if __name__ == '__main__':
    poetry_main()

########NEW FILE########
__FILENAME__ = get-poetry
# This is the Twisted Get Poetry Now! client, version 3.0.

# NOTE: This should not be used as the basis for production code.

import optparse

from twisted.internet.protocol import Protocol, ClientFactory


def parse_args():
    usage = """usage: %prog [options] [hostname]:port ...

This is the Get Poetry Now! client, Twisted version 3.0
Run it like this:

  python get-poetry-1.py port1 port2 port3 ...

If you are in the base directory of the twisted-intro package,
you could run it like this:

  python twisted-client-3/get-poetry-1.py 10001 10002 10003

to grab poetry from servers on ports 10001, 10002, and 10003.

Of course, there need to be servers listening on those ports
for that to work.
"""

    parser = optparse.OptionParser(usage)

    _, addresses = parser.parse_args()

    if not addresses:
        print parser.format_help()
        parser.exit()

    def parse_address(addr):
        if ':' not in addr:
            host = '127.0.0.1'
            port = addr
        else:
            host, port = addr.split(':', 1)

        if not port.isdigit():
            parser.error('Ports must be integers.')

        return host, int(port)

    return map(parse_address, addresses)


class PoetryProtocol(Protocol):

    poem = ''

    def dataReceived(self, data):
        self.poem += data

    def connectionLost(self, reason):
        self.poemReceived(self.poem)

    def poemReceived(self, poem):
        self.factory.poem_finished(poem)


class PoetryClientFactory(ClientFactory):

    protocol = PoetryProtocol

    def __init__(self, callback):
        self.callback = callback

    def poem_finished(self, poem):
        self.callback(poem)


def get_poetry(host, port, callback):
    """
    Download a poem from the given host and port and invoke

      callback(poem)

    when the poem is complete.
    """
    from twisted.internet import reactor
    factory = PoetryClientFactory(callback)
    reactor.connectTCP(host, port, factory)


def poetry_main():
    addresses = parse_args()

    from twisted.internet import reactor

    poems = []

    def got_poem(poem):
        poems.append(poem)
        if len(poems) == len(addresses):
            reactor.stop()

    for address in addresses:
        host, port = address
        get_poetry(host, port, got_poem)

    reactor.run()

    for poem in poems:
        print poem


if __name__ == '__main__':
    poetry_main()

########NEW FILE########
__FILENAME__ = get-poetry-stack
# This is the Twisted Get Poetry Now! client, version 4.0, with stacktrace.

import optparse, os, sys, traceback

from twisted.internet import defer
from twisted.internet.protocol import Protocol, ClientFactory


def parse_args():
    usage = """usage: %prog [options] [hostname]:port ...

This is the Get Poetry Now! client, Twisted version 4.0, with stacktrace.
Run it like this:

  python get-poetry-stack.py port1 port2 port3 ...

If you are in the base directory of the twisted-intro package,
you could run it like this:

  python twisted-client-4/get-poetry-stack.py 10001 10002 10003

to grab poetry from servers on ports 10001, 10002, and 10003.

But it's just going to print out a stacktrace as soon as it
gets the first poem.
"""

    parser = optparse.OptionParser(usage)

    _, addresses = parser.parse_args()

    if not addresses:
        print parser.format_help()
        parser.exit()

    def parse_address(addr):
        if ':' not in addr:
            host = '127.0.0.1'
            port = addr
        else:
            host, port = addr.split(':', 1)

        if not port.isdigit():
            parser.error('Ports must be integers.')

        return host, int(port)

    return map(parse_address, addresses)


class PoetryProtocol(Protocol):

    poem = ''

    def dataReceived(self, data):
        self.poem += data

    def connectionLost(self, reason):
        self.poemReceived(self.poem)

    def poemReceived(self, poem):
        self.factory.poem_finished(poem)


class PoetryClientFactory(ClientFactory):

    protocol = PoetryProtocol

    def __init__(self, deferred):
        self.deferred = deferred

    def poem_finished(self, poem):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.callback(poem)

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason)


def get_poetry(host, port):
    """
    Download a poem from the given host and port. This function
    returns a Deferred which will be fired with the complete text of
    the poem or a Failure if the poem could not be downloaded.
    """
    d = defer.Deferred()
    from twisted.internet import reactor
    factory = PoetryClientFactory(d)
    reactor.connectTCP(host, port, factory)
    return d


def poetry_main():
    addresses = parse_args()

    from twisted.internet import reactor

    poems = []
    errors = []

    def got_poem(poem):
        traceback.print_stack()
        os._exit(0)

    def poem_failed(err):
        print >>sys.stderr, 'Poem failed:', err
        errors.append(err)

    def poem_done(_):
        if len(poems) + len(errors) == len(addresses):
            reactor.stop()

    for address in addresses:
        host, port = address
        d = get_poetry(host, port)
        d.addCallbacks(got_poem, poem_failed)
        d.addBoth(poem_done)

    reactor.run()

    for poem in poems:
        print poem


if __name__ == '__main__':
    poetry_main()

########NEW FILE########
__FILENAME__ = get-poetry
# This is the Twisted Get Poetry Now! client, version 4.0

import optparse, sys

from twisted.internet import defer
from twisted.internet.protocol import Protocol, ClientFactory


def parse_args():
    usage = """usage: %prog [options] [hostname]:port ...

This is the Get Poetry Now! client, Twisted version 4.0
Run it like this:

  python get-poetry.py port1 port2 port3 ...

If you are in the base directory of the twisted-intro package,
you could run it like this:

  python twisted-client-4/get-poetry.py 10001 10002 10003

to grab poetry from servers on ports 10001, 10002, and 10003.

Of course, there need to be servers listening on those ports
for that to work.
"""

    parser = optparse.OptionParser(usage)

    _, addresses = parser.parse_args()

    if not addresses:
        print parser.format_help()
        parser.exit()

    def parse_address(addr):
        if ':' not in addr:
            host = '127.0.0.1'
            port = addr
        else:
            host, port = addr.split(':', 1)

        if not port.isdigit():
            parser.error('Ports must be integers.')

        return host, int(port)

    return map(parse_address, addresses)


class PoetryProtocol(Protocol):

    poem = ''

    def dataReceived(self, data):
        self.poem += data

    def connectionLost(self, reason):
        self.poemReceived(self.poem)

    def poemReceived(self, poem):
        self.factory.poem_finished(poem)


class PoetryClientFactory(ClientFactory):

    protocol = PoetryProtocol

    def __init__(self, deferred):
        self.deferred = deferred

    def poem_finished(self, poem):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.callback(poem)

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason)


def get_poetry(host, port):
    """
    Download a poem from the given host and port. This function
    returns a Deferred which will be fired with the complete text of
    the poem or a Failure if the poem could not be downloaded.
    """
    d = defer.Deferred()
    from twisted.internet import reactor
    factory = PoetryClientFactory(d)
    reactor.connectTCP(host, port, factory)
    return d


def poetry_main():
    addresses = parse_args()

    from twisted.internet import reactor

    poems = []
    errors = []

    def got_poem(poem):
        poems.append(poem)

    def poem_failed(err):
        print >>sys.stderr, 'Poem failed:', err
        errors.append(err)

    def poem_done(_):
        if len(poems) + len(errors) == len(addresses):
            reactor.stop()

    for address in addresses:
        host, port = address
        d = get_poetry(host, port)
        d.addCallbacks(got_poem, poem_failed)
        d.addBoth(poem_done)

    reactor.run()

    for poem in poems:
        print poem


if __name__ == '__main__':
    poetry_main()

########NEW FILE########
__FILENAME__ = get-poetry-1
# This is the Twisted Get Poetry Now! client, version 5.1

import optparse, random, sys

from twisted.internet import defer
from twisted.internet.protocol import Protocol, ClientFactory


def parse_args():
    usage = """usage: %prog [options] [hostname]:port ...

This is the Get Poetry Now! client, Twisted version 5.1
Run it like this:

  python get-poetry-1.py port1 port2 port3 ...

If you are in the base directory of the twisted-intro package,
you could run it like this:

  python twisted-client-5/get-poetry-1.py 10001 10002 10003

to grab poetry from servers on ports 10001, 10002, and 10003.

Of course, there need to be servers listening on those ports
for that to work.
"""

    parser = optparse.OptionParser(usage)

    _, addresses = parser.parse_args()

    if not addresses:
        print parser.format_help()
        parser.exit()

    def parse_address(addr):
        if ':' not in addr:
            host = '127.0.0.1'
            port = addr
        else:
            host, port = addr.split(':', 1)

        if not port.isdigit():
            parser.error('Ports must be integers.')

        return host, int(port)

    return map(parse_address, addresses)


class PoetryProtocol(Protocol):

    poem = ''

    def dataReceived(self, data):
        self.poem += data

    def connectionLost(self, reason):
        self.poemReceived(self.poem)

    def poemReceived(self, poem):
        self.factory.poem_finished(poem)


class PoetryClientFactory(ClientFactory):

    protocol = PoetryProtocol

    def __init__(self, deferred):
        self.deferred = deferred

    def poem_finished(self, poem):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.callback(poem)

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason)


def get_poetry(host, port):
    """
    Download a poem from the given host and port. This function
    returns a Deferred which will be fired with the complete text of
    the poem or a Failure if the poem could not be downloaded.
    """
    d = defer.Deferred()
    from twisted.internet import reactor
    factory = PoetryClientFactory(d)
    reactor.connectTCP(host, port, factory)
    return d


class GibberishError(Exception): pass

class CannotCummingsify(Exception): pass

def cummingsify(poem):
    """
    Randomly do one of the following:

    1. Return a cummingsified version of the poem.
    2. Raise a GibberishError.
    3. Raise a CannotCummingsify error with the original poem
       as the first argument.
    """

    def success():
        return poem.lower()

    def gibberish():
        raise GibberishError()

    def bug():
        raise CannotCummingsify(poem)

    return random.choice([success, gibberish, bug])()


def poetry_main():
    addresses = parse_args()

    from twisted.internet import reactor

    poems = []
    errors = []

    def cummingsify_failed(err):
        if err.check(CannotCummingsify):
            print 'Cummingsify failed!'
            return err.value.args[0]
        return err

    def got_poem(poem):
        print poem
        poems.append(poem)

    def poem_failed(err):
        print >>sys.stderr, 'The poem download failed.'
        errors.append(err)

    def poem_done(_):
        if len(poems) + len(errors) == len(addresses):
            reactor.stop()

    for address in addresses:
        host, port = address
        d = get_poetry(host, port)
        d.addCallback(cummingsify)
        d.addErrback(cummingsify_failed)
        d.addCallbacks(got_poem, poem_failed)
        d.addBoth(poem_done)

    reactor.run()


if __name__ == '__main__':
    poetry_main()

########NEW FILE########
__FILENAME__ = get-poetry
# This is the Twisted Get Poetry Now! client, version 5.0

import optparse, random, sys

from twisted.internet import defer
from twisted.internet.protocol import Protocol, ClientFactory


def parse_args():
    usage = """usage: %prog [options] [hostname]:port ...

This is the Get Poetry Now! client, Twisted version 5.0
Run it like this:

  python get-poetry.py port1 port2 port3 ...

If you are in the base directory of the twisted-intro package,
you could run it like this:

  python twisted-client-5/get-poetry.py 10001 10002 10003

to grab poetry from servers on ports 10001, 10002, and 10003.

Of course, there need to be servers listening on those ports
for that to work.
"""

    parser = optparse.OptionParser(usage)

    _, addresses = parser.parse_args()

    if not addresses:
        print parser.format_help()
        parser.exit()

    def parse_address(addr):
        if ':' not in addr:
            host = '127.0.0.1'
            port = addr
        else:
            host, port = addr.split(':', 1)

        if not port.isdigit():
            parser.error('Ports must be integers.')

        return host, int(port)

    return map(parse_address, addresses)


class PoetryProtocol(Protocol):

    poem = ''

    def dataReceived(self, data):
        self.poem += data

    def connectionLost(self, reason):
        self.poemReceived(self.poem)

    def poemReceived(self, poem):
        self.factory.poem_finished(poem)


class PoetryClientFactory(ClientFactory):

    protocol = PoetryProtocol

    def __init__(self, deferred):
        self.deferred = deferred

    def poem_finished(self, poem):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.callback(poem)

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason)


def get_poetry(host, port):
    """
    Download a poem from the given host and port. This function
    returns a Deferred which will be fired with the complete text of
    the poem or a Failure if the poem could not be downloaded.
    """
    d = defer.Deferred()
    from twisted.internet import reactor
    factory = PoetryClientFactory(d)
    reactor.connectTCP(host, port, factory)
    return d


class GibberishError(Exception): pass

def cummingsify(poem):
    """
    Randomly do one of the following:

    1. Return a cummingsified version of the poem.
    2. Raise a GibberishError.
    3. Raise a ValueError.
    """

    def success():
        return poem.lower()

    def gibberish():
        raise GibberishError()

    def bug():
        raise ValueError()

    return random.choice([success, gibberish, bug])()


def poetry_main():
    addresses = parse_args()

    from twisted.internet import reactor

    poems = []
    errors = []

    def try_to_cummingsify(poem):
        try:
            return cummingsify(poem)
        except GibberishError:
            raise
        except:
            print 'Cummingsify failed!'
            return poem

    def got_poem(poem):
        print poem
        poems.append(poem)

    def poem_failed(err):
        print >>sys.stderr, 'The poem download failed.'
        errors.append(err)

    def poem_done(_):
        if len(poems) + len(errors) == len(addresses):
            reactor.stop()

    for address in addresses:
        host, port = address
        d = get_poetry(host, port)
        d.addCallback(try_to_cummingsify)
        d.addCallbacks(got_poem, poem_failed)
        d.addBoth(poem_done)

    reactor.run()


if __name__ == '__main__':
    poetry_main()

########NEW FILE########
__FILENAME__ = get-poetry
# This is the Twisted Get Poetry Now! client, version 6.0

import optparse, sys

from twisted.internet import defer
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.protocols.basic import NetstringReceiver


def parse_args():
    usage = """usage: %prog [options] [hostname]:port ...

This is the Get Poetry Now! client, Twisted version 6.0
Run it like this:

  python get-poetry.py xform-port port1 port2 ...

If you are in the base directory of the twisted-intro package,
you could run it like this:

  python twisted-client-6/get-poetry.py 10001 10002 10003

to grab poetry from servers on ports 10002, and 10003 and transform
it using the server on port 10001.

Of course, there need to be appropriate servers listening on those
ports for that to work.
"""

    parser = optparse.OptionParser(usage)

    _, addresses = parser.parse_args()

    if len(addresses) < 2:
        print parser.format_help()
        parser.exit()

    def parse_address(addr):
        if ':' not in addr:
            host = '127.0.0.1'
            port = addr
        else:
            host, port = addr.split(':', 1)

        if not port.isdigit():
            parser.error('Ports must be integers.')

        return host, int(port)

    return map(parse_address, addresses)


class PoetryProtocol(Protocol):

    poem = ''

    def dataReceived(self, data):
        self.poem += data

    def connectionLost(self, reason):
        self.poemReceived(self.poem)

    def poemReceived(self, poem):
        self.factory.poem_finished(poem)


class PoetryClientFactory(ClientFactory):

    protocol = PoetryProtocol

    def __init__(self, deferred):
        self.deferred = deferred

    def poem_finished(self, poem):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.callback(poem)

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason)


class TransformClientProtocol(NetstringReceiver):

    def connectionMade(self):
        self.sendRequest(self.factory.xform_name, self.factory.poem)

    def sendRequest(self, xform_name, poem):
        self.sendString(xform_name + '.' + poem)

    def stringReceived(self, s):
        self.transport.loseConnection()
        self.poemReceived(s)

    def poemReceived(self, poem):
        self.factory.handlePoem(poem)


class TransformClientFactory(ClientFactory):

    protocol = TransformClientProtocol

    def __init__(self, xform_name, poem):
        self.xform_name = xform_name
        self.poem = poem
        self.deferred = defer.Deferred()

    def handlePoem(self, poem):
        d, self.deferred = self.deferred, None
        d.callback(poem)

    def clientConnectionLost(self, _, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason)

    clientConnectionFailed = clientConnectionLost


class TransformProxy(object):
    """
    I proxy requests to a transformation service.
    """

    def __init__(self, host, port):
        self.host = host
        self.port = port

    def xform(self, xform_name, poem):
        factory = TransformClientFactory(xform_name, poem)
        from twisted.internet import reactor
        reactor.connectTCP(self.host, self.port, factory)
        return factory.deferred


def get_poetry(host, port):
    """
    Download a poem from the given host and port. This function
    returns a Deferred which will be fired with the complete text of
    the poem or a Failure if the poem could not be downloaded.
    """
    d = defer.Deferred()
    from twisted.internet import reactor
    factory = PoetryClientFactory(d)
    reactor.connectTCP(host, port, factory)
    return d


def poetry_main():
    addresses = parse_args()

    xform_addr = addresses.pop(0)

    proxy = TransformProxy(*xform_addr)

    from twisted.internet import reactor

    poems = []
    errors = []

    def try_to_cummingsify(poem):
        d = proxy.xform('cummingsify', poem)

        def fail(err):
            print >>sys.stderr, 'Cummingsify failed!'
            return poem

        return d.addErrback(fail)

    def got_poem(poem):
        print poem
        poems.append(poem)

    def poem_failed(err):
        print >>sys.stderr, 'The poem download failed.'
        errors.append(err)

    def poem_done(_):
        if len(poems) + len(errors) == len(addresses):
            reactor.stop()

    for address in addresses:
        host, port = address
        d = get_poetry(host, port)
        d.addCallback(try_to_cummingsify)
        d.addCallbacks(got_poem, poem_failed)
        d.addBoth(poem_done)

    reactor.run()


if __name__ == '__main__':
    poetry_main()

########NEW FILE########
__FILENAME__ = get-poetry
# This is the Twisted Get Poetry Now! client, version 7.0

import optparse, sys

from twisted.internet import defer
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.protocols.basic import NetstringReceiver


def parse_args():
    usage = """usage: %prog [options] [hostname]:port ...

This is the Get Poetry Now! client, Twisted version 7.0
Run it like this:

  python get-poetry.py xform-port port1 port2 ...

If you are in the base directory of the twisted-intro package,
you could run it like this:

  python twisted-client-6/get-poetry.py 10001 10002 10003

to grab poetry from servers on ports 10002, and 10003 and transform
it using the server on port 10001.

Of course, there need to be appropriate servers listening on those
ports for that to work.
"""

    parser = optparse.OptionParser(usage)

    _, addresses = parser.parse_args()

    if len(addresses) < 2:
        print parser.format_help()
        parser.exit()

    def parse_address(addr):
        if ':' not in addr:
            host = '127.0.0.1'
            port = addr
        else:
            host, port = addr.split(':', 1)

        if not port.isdigit():
            parser.error('Ports must be integers.')

        return host, int(port)

    return map(parse_address, addresses)


class PoetryProtocol(Protocol):

    poem = ''

    def dataReceived(self, data):
        self.poem += data

    def connectionLost(self, reason):
        self.poemReceived(self.poem)

    def poemReceived(self, poem):
        self.factory.poem_finished(poem)


class PoetryClientFactory(ClientFactory):

    protocol = PoetryProtocol

    def __init__(self, deferred):
        self.deferred = deferred

    def poem_finished(self, poem):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.callback(poem)

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason)


class TransformClientProtocol(NetstringReceiver):

    def connectionMade(self):
        self.sendRequest(self.factory.xform_name, self.factory.poem)

    def sendRequest(self, xform_name, poem):
        self.sendString(xform_name + '.' + poem)

    def stringReceived(self, s):
        self.transport.loseConnection()
        self.poemReceived(s)

    def poemReceived(self, poem):
        self.factory.handlePoem(poem)


class TransformClientFactory(ClientFactory):

    protocol = TransformClientProtocol

    def __init__(self, xform_name, poem):
        self.xform_name = xform_name
        self.poem = poem
        self.deferred = defer.Deferred()

    def handlePoem(self, poem):
        d, self.deferred = self.deferred, None
        d.callback(poem)

    def clientConnectionLost(self, _, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason)

    clientConnectionFailed = clientConnectionLost


class TransformProxy(object):
    """
    I proxy requests to a transformation service.
    """

    def __init__(self, host, port):
        self.host = host
        self.port = port

    def xform(self, xform_name, poem):
        factory = TransformClientFactory(xform_name, poem)
        from twisted.internet import reactor
        reactor.connectTCP(self.host, self.port, factory)
        return factory.deferred


def get_poetry(host, port):
    """
    Download a poem from the given host and port. This function
    returns a Deferred which will be fired with the complete text of
    the poem or a Failure if the poem could not be downloaded.
    """
    d = defer.Deferred()
    from twisted.internet import reactor
    factory = PoetryClientFactory(d)
    reactor.connectTCP(host, port, factory)
    return d


def poetry_main():
    addresses = parse_args()

    xform_addr = addresses.pop(0)

    proxy = TransformProxy(*xform_addr)

    from twisted.internet import reactor

    results = []

    @defer.inlineCallbacks
    def get_transformed_poem(host, port):
        try:
            poem = yield get_poetry(host, port)
        except Exception, e:
            print >>sys.stderr, 'The poem download failed:', e
            raise

        try:
            poem = yield proxy.xform('cummingsify', poem)
        except Exception:
            print >>sys.stderr, 'Cummingsify failed!'

        defer.returnValue(poem)

    def got_poem(poem):
        print poem

    def poem_done(_):
        results.append(_)
        if len(results) == len(addresses):
            reactor.stop()

    for address in addresses:
        host, port = address
        d = get_transformed_poem(host, port)
        d.addCallbacks(got_poem)
        d.addBoth(poem_done)

    reactor.run()


if __name__ == '__main__':
    poetry_main()

########NEW FILE########
__FILENAME__ = get-poetry
# This is the Twisted Get Poetry Now! client, version 8.0

import optparse, sys

from twisted.internet import defer
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.protocols.basic import NetstringReceiver


def parse_args():
    usage = """usage: %prog [options] [hostname]:port ...

This is the Get Poetry Now! client, Twisted version 8.0
Run it like this:

  python get-poetry.py xform-port port1 port2 ...

If you are in the base directory of the twisted-intro package,
you could run it like this:

  python twisted-client-6/get-poetry.py 10001 10002 10003

to grab poetry from servers on ports 10002, and 10003 and transform
it using the server on port 10001.

Of course, there need to be appropriate servers listening on those
ports for that to work.
"""

    parser = optparse.OptionParser(usage)

    _, addresses = parser.parse_args()

    if len(addresses) < 2:
        print parser.format_help()
        parser.exit()

    def parse_address(addr):
        if ':' not in addr:
            host = '127.0.0.1'
            port = addr
        else:
            host, port = addr.split(':', 1)

        if not port.isdigit():
            parser.error('Ports must be integers.')

        return host, int(port)

    return map(parse_address, addresses)


class PoetryProtocol(Protocol):

    poem = ''

    def dataReceived(self, data):
        self.poem += data

    def connectionLost(self, reason):
        self.poemReceived(self.poem)

    def poemReceived(self, poem):
        self.factory.poem_finished(poem)


class PoetryClientFactory(ClientFactory):

    protocol = PoetryProtocol

    def __init__(self, deferred):
        self.deferred = deferred

    def poem_finished(self, poem):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.callback(poem)

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason)


class TransformClientProtocol(NetstringReceiver):

    def connectionMade(self):
        self.sendRequest(self.factory.xform_name, self.factory.poem)

    def sendRequest(self, xform_name, poem):
        self.sendString(xform_name + '.' + poem)

    def stringReceived(self, s):
        self.transport.loseConnection()
        self.poemReceived(s)

    def poemReceived(self, poem):
        self.factory.handlePoem(poem)


class TransformClientFactory(ClientFactory):

    protocol = TransformClientProtocol

    def __init__(self, xform_name, poem):
        self.xform_name = xform_name
        self.poem = poem
        self.deferred = defer.Deferred()

    def handlePoem(self, poem):
        d, self.deferred = self.deferred, None
        d.callback(poem)

    def clientConnectionLost(self, _, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason)

    clientConnectionFailed = clientConnectionLost


class TransformProxy(object):
    """
    I proxy requests to a transformation service.
    """

    def __init__(self, host, port):
        self.host = host
        self.port = port

    def xform(self, xform_name, poem):
        factory = TransformClientFactory(xform_name, poem)
        from twisted.internet import reactor
        reactor.connectTCP(self.host, self.port, factory)
        return factory.deferred


def get_poetry(host, port):
    """
    Download a poem from the given host and port. This function
    returns a Deferred which will be fired with the complete text of
    the poem or a Failure if the poem could not be downloaded.
    """
    d = defer.Deferred()
    from twisted.internet import reactor
    factory = PoetryClientFactory(d)
    reactor.connectTCP(host, port, factory)
    return d


def poetry_main():
    addresses = parse_args()

    xform_addr = addresses.pop(0)

    proxy = TransformProxy(*xform_addr)

    from twisted.internet import reactor

    @defer.inlineCallbacks
    def get_transformed_poem(host, port):
        try:
            poem = yield get_poetry(host, port)
        except Exception, e:
            print >>sys.stderr, 'The poem download failed:', e
            raise

        try:
            poem = yield proxy.xform('cummingsify', poem)
        except Exception:
            print >>sys.stderr, 'Cummingsify failed!'

        defer.returnValue(poem)

    def got_poem(poem):
        print poem

    ds = []

    for (host, port) in addresses:
        d = get_transformed_poem(host, port)
        d.addCallbacks(got_poem)
        ds.append(d)

    dlist = defer.DeferredList(ds, consumeErrors=True)
    dlist.addCallback(lambda res : reactor.stop())

    reactor.run()


if __name__ == '__main__':
    poetry_main()

########NEW FILE########
__FILENAME__ = defer-1
from twisted.internet.defer import Deferred

def got_poem(res):
    print 'Your poem is served:'
    print res

def poem_failed(err):
    print 'No poetry for you.'

d = Deferred()

# add a callback/errback pair to the chain
d.addCallbacks(got_poem, poem_failed)

# fire the chain with a normal result
d.callback('This poem is short.')

print "Finished"

########NEW FILE########
__FILENAME__ = defer-10
from twisted.internet.defer import Deferred

print """
This example illustrates how callbacks in a deferred
chain can return deferreds themselves.
"""

# three simple callbacks

def callback_1(res):
    print 'callback_1 got', res
    return 1

def callback_2(res):
    print 'callback_2 got', res
    return 2

def callback_3(res):
    print 'callback_3 got', res
    return 3


# We add them all to a deferred and fire it:

d = Deferred()

d.addCallback(callback_1)
d.addCallback(callback_2)
d.addCallback(callback_3)

print """
Here we are firing a deferred with three callbacks that just print
their argument and return simple values:
"""

d.callback(0)

# And you get output like this:
# callback_1 got 0
# callback_2 got 1
# callback_3 got 2


# Now we make a callback that returns a deferred:

deferred_2 = None # NOTE: because we aren't using a reactor, we have
                  #       to fire this deferred from the 'outside'.
                  #       We store it in a global variable for this
                  #       purpose. In a normal Twisted program you
                  #       would never store a deferred in a global or
                  #       fire it from the outside. By 'outside' we
                  #       mean the deferred is not being fired by an
                  #       action set in motion by the callback that
                  #       created and returned the deferred, as is
                  #       normally the case.

def callback_2_async(res):
    print 'callback_2 got', res
    global deferred_2 # never do this in a real program
    deferred_2 = Deferred()
    return deferred_2


# We do the same thing, but use the async callback:

d = Deferred()

d.addCallback(callback_1)
d.addCallback(callback_2_async)
d.addCallback(callback_3)

print """
Here we are firing a deferred as above but the middle callback is
returning a deferred:
"""

d.callback(0)

# And you get output like this:
# callback_1 got 0
# callback_2 got 1

print """
Notice the output from the third callback is missing. That's because
the second callback returned a deferred and now the 'outer' deferred
is paused. It's not waiting in a thread or anything like that, it just
stopped invoking the callbacks in the chain. Instead, it registered
some callbacks on the 'inner' deferred which will start the outer
deferred back up when the inner deferred is fired.

We can see this in action by firing the inner deferred:
"""

deferred_2.callback(2)

# And you get output like this:
# callback_3 got 2

print """
Note the argument to the inner deferred's callback() method became
the result passed to the next callback in the outer deferred.
"""

########NEW FILE########
__FILENAME__ = defer-11
from twisted.internet.defer import Deferred

print """\
This example illustrates how deferreds can
be fired before they are returned. First we
make a new deferred, fire it, then add some
callbacks.
"""

# three simple callbacks

def callback_1(res):
    print 'callback_1 got', res
    return 1

def callback_2(res):
    print 'callback_2 got', res
    return 2

def callback_3(res):
    print 'callback_3 got', res
    return 3

# We create a deferred and fire it immediately:
d = Deferred()

print 'Firing empty deferred.'
d.callback(0)

# Now we add the callbacks to the deferred.
# Notice how each callback fires immediately.

print 'Adding first callback.'
d.addCallback(callback_1)

print 'Adding second callback.'
d.addCallback(callback_2)

print 'Adding third callback.'
d.addCallback(callback_3)

print"""
Because the deferred was already fired, it
invoked each callback as soon as it was added.

Now we create a deferred and fire it, but
pause it first with the pause() method.
"""

# We do the same thing, but pause the deferred:

d = Deferred()
print 'Pausing, then firing deferred.'
d.pause()
d.callback(0)

print 'Adding callbacks.'
d.addCallback(callback_1)
d.addCallback(callback_2)
d.addCallback(callback_3)

print 'Unpausing the deferred.'
d.unpause()

########NEW FILE########
__FILENAME__ = defer-2
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure

def got_poem(res):
    print 'Your poem is served:'
    print res

def poem_failed(err):
    print 'No poetry for you.'

d = Deferred()

# add a callback/errback pair to the chain
d.addCallbacks(got_poem, poem_failed)

# fire the chain with an error result
d.errback(Failure(Exception('I have failed.')))

print "Finished"

########NEW FILE########
__FILENAME__ = defer-3
from twisted.internet.defer import Deferred

def got_poem(res):
    print 'Your poem is served:'
    print res

def poem_failed(err):
    print err.__class__
    print err
    print 'No poetry for you.'

d = Deferred()

# add a callback/errback pair to the chain
d.addCallbacks(got_poem, poem_failed)

# fire the chain with an error result
d.errback(Exception('I have failed.'))

########NEW FILE########
__FILENAME__ = defer-4
from twisted.internet.defer import Deferred
def out(s): print s
d = Deferred()
d.addCallbacks(out, out)
d.callback('First result')
d.callback('Second result')
print 'Finished'

########NEW FILE########
__FILENAME__ = defer-5
from twisted.internet.defer import Deferred
def out(s): print s
d = Deferred()
d.addCallbacks(out, out)
d.callback('First result')
d.errback(Exception('First error'))
print 'Finished'

########NEW FILE########
__FILENAME__ = defer-6
from twisted.internet.defer import Deferred
def out(s): print s
d = Deferred()
d.addCallbacks(out, out)
d.errback(Exception('First error'))
d.errback(Exception('Second error'))
print 'Finished'

########NEW FILE########
__FILENAME__ = defer-7
from twisted.internet.defer import Deferred
def out(s): print s
d = Deferred()
d.addCallbacks(out, out)
d.errback(Exception('First error'))
d.callback('First result')
print 'Finished'

########NEW FILE########
__FILENAME__ = defer-8
import sys

from twisted.internet.defer import Deferred

def got_poem(poem):
    print poem
    from twisted.internet import reactor
    reactor.stop()

def poem_failed(err):
    print >>sys.stderr, 'poem download failed'
    print >>sys.stderr, 'I am terribly sorry'
    print >>sys.stderr, 'try again later?'
    from twisted.internet import reactor
    reactor.stop()

d = Deferred()

d.addCallbacks(got_poem, poem_failed)

from twisted.internet import reactor

reactor.callWhenRunning(d.callback, 'Another short poem.')

reactor.run()

########NEW FILE########
__FILENAME__ = defer-9
import sys

from twisted.internet.defer import Deferred

def got_poem(poem):
    print poem

def poem_failed(err):
    print >>sys.stderr, 'poem download failed'
    print >>sys.stderr, 'I am terribly sorry'
    print >>sys.stderr, 'try again later?'

def poem_done(_):
    from twisted.internet import reactor
    reactor.stop()

d = Deferred()

d.addCallbacks(got_poem, poem_failed)
d.addBoth(poem_done)

from twisted.internet import reactor

reactor.callWhenRunning(d.callback, 'Another short poem.')

reactor.run()

########NEW FILE########
__FILENAME__ = defer-block
import sys, time

from twisted.internet.defer import Deferred

def start_chain(_):
    print "The start of the callback chain."

def blocking_poem(_):
    def delayed_write(s, delay):
        time.sleep(delay)
        sys.stdout.write(s)
        sys.stdout.flush()

    delayed_write('\n', 0)
    delayed_write('I', .6)
    delayed_write(' block', .4)
    delayed_write('\n  and', 1)
    delayed_write(' the', .4)
    delayed_write(' deferred', .6)
    delayed_write('\n  blocks', 1.5)
    delayed_write(' with', .2)
    delayed_write(' me', .2)
    delayed_write('\nas does', 1)
    delayed_write('\n the reactor', .6)
    delayed_write('\nkeep that', 1)
    delayed_write('\n factor', .6)
    delayed_write('\nin', 1)
    delayed_write(' mind', .4)
    delayed_write('\n\n', 2)

def end_chain(_):
    print "The end of the callback chain."
    from twisted.internet import reactor
    reactor.stop()

d = Deferred()

d.addCallback(start_chain)
d.addCallback(blocking_poem)
d.addCallback(end_chain)

def fire():
    print 'Firing deferred.'
    d.callback(True)
    print 'Firing finished.'

from twisted.internet import reactor

reactor.callWhenRunning(fire)

print 'Starting reactor.'
reactor.run()
print 'Done.'

########NEW FILE########
__FILENAME__ = defer-unhandled
from twisted.internet.defer import Deferred

def callback(res):
    raise Exception('oops')

d = Deferred()

d.addCallback(callback)

d.callback('Here is your result.')

print "Finished"

########NEW FILE########
__FILENAME__ = deferred-simulator
#!/usr/bin/env python

import optparse, sys

from twisted.internet import defer
from twisted.python.failure import Failure

__doc__ = """\
usage: %prog
A Deferred simulator. Use this to see how a particular
set of callbacks and errbacks will fire in a deferred.\
"""

class BadInput(Exception): pass


def parse_args():
    parser = optparse.OptionParser(usage=__doc__)

    help = "draw all three chains in one column"
    parser.add_option('--narrow', action='store_true', help=help)

    options, args = parser.parse_args()

    if args:
        parser.error('No arguments supported.')

    return options


class Screen(object):
    """An ascii screen."""

    def __init__(self):
        self.pixels = {} # (x, y) -> char

    def draw_char(self, x, y, char):
        self.pixels[x,y] = char

    def draw_horiz_line(self, x, y, width):
        for i in range(width):
            self.draw_char(x + i, y, '-')

    def draw_vert_line(self, x, y, height, end_arrow=False):
        for i in range(height):
            self.draw_char(x, y + i, '|')
        if end_arrow:
            self.draw_char(x - 1, y + height - 1, '\\')
            self.draw_char(x + 1, y + height - 1, '/')

    def draw_text(self, x, y, text):
        for i, char in enumerate(text):
            self.draw_char(x + i, y, char)

    def clear(self):
        self.pixels.clear()

    def __str__(self):
        width = max([p[0] + 1 for p in self.pixels] + [0])
        height = max([p[1] + 1 for p in self.pixels] + [0])

        s = ''

        for y in range(height):
            for x in range(width):
                s += self.pixels.get((x,y), ' ')
            s += '\n'

        return s
        

class Callback(object):
    """
    A widget representing a single callback or errback.

    Each callback widget has one of three styles:

      return - a callback that returns a given value
      fail - a callback that raises an Exception(value)
      passthru - a callback that returns its argument unchanged

    The widget is also a callable that behaves according
    to the widget's style.
    """

    height = 5

    def __init__(self, style, value=None):
        self.style = style
        self.value = value
        self.min_width = len('0123456*') + len('return ') + 3

    def __call__(self, res):
        if self.style == 'return':
            return self.value
        if self.style == 'fail':
            return Failure(Exception(self.value))
        return res

    @property
    def caption(self):
        if self.style == 'passthru':
            return 'passthru'
        return self.style + ' ' + self.value

    def format_value(self, res):
        if isinstance(res, Failure):
            return res.value.args[0] + '*'
        return res

    def draw_passive(self, screen, x, y, width):
        self.draw_box(screen, x, y, width)
        self.draw_text(screen, x, y + 2, width, self.caption)

    def draw_active(self, screen, x, y, width, res):
        self.draw_box(screen, x, y, width)
        self.draw_text(screen, x, y + 1, width, self.format_value(res))
        self.draw_text(screen, x, y + 3, width, self.format_value(self(res)))

    def draw_box(self, screen, x, y, width):
        screen.draw_horiz_line(x, y, width)
        screen.draw_horiz_line(x, y + 4, width)
        screen.draw_vert_line(x, y + 1, 3)
        screen.draw_vert_line(x + width - 1, y + 1, 3)

    def draw_text(self, screen, x, y, width, text):
        screen.draw_text(x + 1, y, text.center(width - 2))
        

class Deferred(object):
    """
    An widget for a deferred.

    It is initialize with a non-empty list of Callback pairs,
    representing a callback chain in a Twisted Deferred.
    """

    def __init__(self, pairs):
        assert pairs
        self.pairs = pairs
        self.callback_width = max([p[0].min_width for p in self.pairs] + [0])
        self.callback_width = max([p[1].min_width for p in self.pairs]
                                  + [self.callback_width])
        self.width = self.callback_width * 2 + 2
        self.height = Callback.height * len(self.pairs)
        self.height += 3 * len(self.pairs[1:])

    def draw(self, screen, x, y):
        """
        Draw a representation of the callback/errback chain
        on the given screen at the given coordinates.
        """
        for callback, errback in self.pairs:
            callback.draw_passive(screen, x, y, self.callback_width)
            errback.draw_passive(screen, x + self.callback_width + 2,
                                 y, self.callback_width)
            y += Callback.height + 3


class FiredDeferred(object):
    """
    A widget for a fired deferred.

    It is initialized with a Deferred widget (not a real deferred)
    and the method name ('callback' or 'errback') to draw the firing
    sequence for.
    """

    callback_y_offset = 4

    def __init__(self, deferred, method):
        self.deferred = deferred
        self.method = method
        self.height = deferred.height + 8
        self.width = deferred.width

    def draw(self, screen, x, y, result='initial'):
        d = self.make_drawing_deferred(screen, x, y)

        if self.method == 'callback':
            d.callback(result)
        else:
            d.errback(Exception(result))

    def make_drawing_deferred(self, screen, x, y):
        """
        Return a new deferred that, when fired, will draw its
        firing sequence onto the given screen at the given coordinates.
        """

        callback_width = self.deferred.callback_width

        callback_mid_x = x - 1 + callback_width / 2

        errback_left_x = x + callback_width + 2
        errback_mid_x = errback_left_x - 1 + callback_width / 2

        class DrawState(object):
            last_x = None
            last_y = None

        state = DrawState()

        def draw_connection(x):
            if state.last_x == x:
                screen.draw_vert_line(x - 1 + callback_width / 2,
                                      state.last_y - 3, 3, True)
                return

            if state.last_x < x:
                screen.draw_vert_line(callback_mid_x, state.last_y - 3, 2)
                screen.draw_vert_line(errback_mid_x,
                                      state.last_y - 2, 2, True)
            else:
                screen.draw_vert_line(errback_mid_x, state.last_y - 3, 2)
                screen.draw_vert_line(callback_mid_x,
                                      state.last_y - 2, 2, True)

            screen.draw_horiz_line(callback_mid_x + 1,
                                   state.last_y - 2,
                                   errback_mid_x - callback_mid_x - 1)

        def wrap_callback(cb, x):
            def callback(res):
                cb.draw_active(screen, x, state.last_y, callback_width, res)
                draw_connection(x)
                state.last_x = x
                state.last_y += cb.height + 3
                return cb(res)
            return callback

        def draw_value(res, y):
            if isinstance(res, Failure):
                text = res.value.args[0] + '*'
                text = text.center(callback_width + 20)
                screen.draw_text(errback_left_x - 10, y, text)
            else:
                screen.draw_text(x, y, res.center(callback_width))

        def draw_start(res):
            draw_value(res, y)
            if isinstance(res, Failure):
                state.last_x = errback_left_x
            else:
                state.last_x = x
            state.last_y = y + 4
            return res

        def draw_end(res):
            draw_value(res, state.last_y)
            if isinstance(res, Failure):
                draw_connection(errback_left_x)
            else:
                draw_connection(x)

        d = defer.Deferred()

        d.addBoth(draw_start)

        for pair in self.deferred.pairs:
            callback = wrap_callback(pair[0], x)
            errback = wrap_callback(pair[1], errback_left_x)
            d.addCallbacks(callback, errback)

        d.addBoth(draw_end)

        return d


def get_next_pair():
    """Get the next callback/errback pair from the user."""

    def get_cb():
        if not parts:
            raise BadInput('missing command')

        cmd = parts.pop(0).lower()

        for command in ('return', 'fail', 'passthru'):
            if command.startswith(cmd):
                cmd = command
                break
        else:
            raise BadInput('bad command: %s' % cmd)

        if cmd in ('return', 'fail'):
            if not parts:
                raise BadInput('missing argument')

            result = parts.pop(0)

            if len(result) > 6:
                raise BadInput('result more than 6 chars long', result)

            return Callback(cmd, result)
        else:
            return Callback(cmd)

    try:
        line = raw_input()
    except EOFError:
        sys.exit()

    if not line:
        return None

    parts = line.strip().split()

    callback, errback = get_cb(), get_cb()

    if parts:
        raise BadInput('extra arguments')

    return callback, errback


def get_pairs():
    """
    Get the list of callback/errback pairs from the user.
    They are returned as Callback widgets.
    """

    print """\
Enter a list of callback/errback pairs in the form:

  CALLBACK ERRBACK

Where CALLBACK and ERRBACK are one of:

  return VALUE
  fail VALUE
  passthru

And where VALUE is a string of only letters and numbers (no spaces),
no more than 6 characters long.

Each pair should be on a single line and you can abbreviate
return/fail/passthru as r/f/p.

Examples:

  r good f bad  # callback returns 'good'
                # and errback raises Exception('bad')

  f googly p    # callback raises Exception('googly')
                # and errback passes its failure along

Enter a blank line when you are done, and a diagram of the deferred
will be printed next to the firing patterns for both the callback()
and errback() methods. In the diagram, a value followed by '*' is
really an Exception wrapped in a Failure, i.e:

  value* == Failure(Exception(value))

You will want to make your terminal as wide as possible.
"""

    pairs = []

    while True:
        try:
            pair = get_next_pair()
        except BadInput, e:
            print 'ERROR:', e
            continue

        if pair is None:
            if not pairs:
                print 'You must enter at least one pair.'
                continue
            else:
                break

        pairs.append(pair)
           
    return pairs


def draw_single_column(d, callback, errback):
    screen = Screen()

    screen.draw_text(0, 1, 'Deferred'.center(d.width))
    screen.draw_text(0, 2, '--------'.center(d.width))

    d.draw(screen, 0, 4)

    print screen

    screen.clear()

    screen.draw_text(0, 2, 'd.callback(initial)'.center(d.width))
    screen.draw_text(0, 3, '-------------------'.center(d.width))

    callback.draw(screen, 0, 5)

    print screen

    screen.clear()

    screen.draw_text(0, 2, 'd.errback(initial*)'.center(d.width))
    screen.draw_text(0, 3, '-------------------'.center(d.width))

    errback.draw(screen, 0, 5)

    print screen


def draw_multi_column(d, callback, errback):
    screen = Screen()

    screen.draw_text(0, 0, 'Deferred'.center(d.width))
    screen.draw_text(0, 1, '--------'.center(d.width))

    screen.draw_text(d.width + 6, 0, 'd.callback(initial)'.center(d.width))
    screen.draw_text(d.width + 6, 1, '-------------------'.center(d.width))

    screen.draw_text(2 * (d.width + 6), 0, 'd.errback(initial*)'.center(d.width))
    screen.draw_text(2 * (d.width + 6), 1, '-------------------'.center(d.width))

    d.draw(screen, 0, callback.callback_y_offset + 3)
    callback.draw(screen, d.width + 6, 3)
    errback.draw(screen, 2 * (d.width + 6), 3)

    screen.draw_vert_line(d.width + 3, 3, callback.height)
    screen.draw_vert_line(d.width + 3 + d.width + 6, 3, callback.height)

    print screen


def main():
    options = parse_args()

    d = Deferred(get_pairs())
    callback = FiredDeferred(d, 'callback')
    errback = FiredDeferred(d, 'errback')

    if options.narrow:
        draw_single_column(d, callback, errback)
    else:
        draw_multi_column(d, callback, errback)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = failure-examples
# This code illustrates a few aspects of Failures.
# Generally, Twisted makes Failures for us.

from twisted.python.failure import Failure

class RhymeSchemeViolation(Exception): pass


print 'Just making an exception:'
print

e = RhymeSchemeViolation()

failure = Failure(e)

# Note this failure doesn't include any traceback info
print failure

print
print

print 'Catching an exception:'
print

def analyze_poem(poem):
    raise RhymeSchemeViolation()

try:
    analyze_poem("""\
Roses are red.
Violets are violet.
That's why they're called Violets.
Duh.
""")
except:
    failure = Failure()


# This failure saved both the exception and the traceback
print failure

########NEW FILE########
__FILENAME__ = fastpoetry
# This is the Twisted Fast Poetry Server, version 1.0

import optparse, os

from twisted.internet.protocol import ServerFactory, Protocol


def parse_args():
    usage = """usage: %prog [options] poetry-file

This is the Fast Poetry Server, Twisted edition.
Run it like this:

  python fastpoetry.py <path-to-poetry-file>

If you are in the base directory of the twisted-intro package,
you could run it like this:

  python twisted-server-1/fastpoetry.py poetry/ecstasy.txt

to serve up John Donne's Ecstasy, which I know you want to do.
"""

    parser = optparse.OptionParser(usage)

    help = "The port to listen on. Default to a random available port."
    parser.add_option('--port', type='int', help=help)

    help = "The interface to listen on. Default is localhost."
    parser.add_option('--iface', help=help, default='localhost')

    options, args = parser.parse_args()

    if len(args) != 1:
        parser.error('Provide exactly one poetry file.')

    poetry_file = args[0]

    if not os.path.exists(args[0]):
        parser.error('No such file: %s' % poetry_file)

    return options, poetry_file


class PoetryProtocol(Protocol):

    def connectionMade(self):
        self.transport.write(self.factory.poem)
        self.transport.loseConnection()


class PoetryFactory(ServerFactory):

    protocol = PoetryProtocol

    def __init__(self, poem):
        self.poem = poem


def main():
    options, poetry_file = parse_args()

    poem = open(poetry_file).read()

    factory = PoetryFactory(poem)

    from twisted.internet import reactor

    port = reactor.listenTCP(options.port or 0, factory,
                             interface=options.iface)

    print 'Serving %s on %s.' % (poetry_file, port.getHost())

    reactor.run()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = poetry-proxy
# This is the Twisted Poetry Proxy, version 1.0

import optparse

from twisted.internet.defer import Deferred, maybeDeferred
from twisted.internet.protocol import ClientFactory, ServerFactory, Protocol


def parse_args():
    usage = """usage: %prog [options] [hostname]:port

This is the Poetry Proxy, version 1.0.

  python poetry-proxy.py [hostname]:port

If you are in the base directory of the twisted-intro package,
you could run it like this:

  python twisted-server-1/poetry-proxy.py 10000

to proxy the poem for the server running on port 10000.
"""

    parser = optparse.OptionParser(usage)

    help = "The port to listen on. Default to a random available port."
    parser.add_option('--port', type='int', help=help)

    help = "The interface to listen on. Default is localhost."
    parser.add_option('--iface', help=help, default='localhost')

    options, args = parser.parse_args()

    if len(args) != 1:
        parser.error('Provide exactly one server address.')

    def parse_address(addr):
        if ':' not in addr:
            host = '127.0.0.1'
            port = addr
        else:
            host, port = addr.split(':', 1)

        if not port.isdigit():
            parser.error('Ports must be integers.')

        return host, int(port)

    return options, parse_address(args[0])


class PoetryProxyProtocol(Protocol):

    def connectionMade(self):
        d = maybeDeferred(self.factory.service.get_poem)
        d.addCallback(self.transport.write)
        d.addBoth(lambda r: self.transport.loseConnection())


class PoetryProxyFactory(ServerFactory):

    protocol = PoetryProxyProtocol

    def __init__(self, service):
        self.service = service


class PoetryClientProtocol(Protocol):

    poem = ''

    def dataReceived(self, data):
        self.poem += data

    def connectionLost(self, reason):
        self.poemReceived(self.poem)

    def poemReceived(self, poem):
        self.factory.poem_finished(poem)


class PoetryClientFactory(ClientFactory):

    protocol = PoetryClientProtocol

    def __init__(self):
        self.deferred = Deferred()

    def poem_finished(self, poem):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.callback(poem)

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason)


class ProxyService(object):

    poem = None # the cached poem

    def __init__(self, host, port):
        self.host = host
        self.port = port

    def get_poem(self):
        if self.poem is not None:
            print 'Using cached poem.'
            return self.poem

        print 'Fetching poem from server.'
        factory = PoetryClientFactory()
        factory.deferred.addCallback(self.set_poem)
        from twisted.internet import reactor
        reactor.connectTCP(self.host, self.port, factory)
        return factory.deferred

    def set_poem(self, poem):
        self.poem = poem
        return poem


def main():
    options, server_addr = parse_args()

    service = ProxyService(*server_addr)

    factory = PoetryProxyFactory(service)

    from twisted.internet import reactor

    port = reactor.listenTCP(options.port or 0, factory,
                             interface=options.iface)

    print 'Proxying %s on %s.' % (server_addr, port.getHost())

    reactor.run()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = transformedpoetry
# This is the Twisted Poetry Transform Server, version 1.0

import optparse

from twisted.internet.protocol import ServerFactory
from twisted.protocols.basic import NetstringReceiver


def parse_args():
    usage = """usage: %prog [options]

This is the Poetry Transform Server.
Run it like this:

  python transformedpoetry.py

If you are in the base directory of the twisted-intro package,
you could run it like this:

  python twisted-server-1/transformedpoetry.py --port 11000

to provide poetry transformation on port 11000.
"""

    parser = optparse.OptionParser(usage)

    help = "The port to listen on. Default to a random available port."
    parser.add_option('--port', type='int', help=help)

    help = "The interface to listen on. Default is localhost."
    parser.add_option('--iface', help=help, default='localhost')

    options, args = parser.parse_args()

    if len(args) != 0:
        parser.error('Bad arguments.')

    return options


class TransformService(object):

    def cummingsify(self, poem):
        return poem.lower()


class TransformProtocol(NetstringReceiver):

    def stringReceived(self, request):
        if '.' not in request: # bad request
            self.transport.loseConnection()
            return

        xform_name, poem = request.split('.', 1)

        self.xformRequestReceived(xform_name, poem)

    def xformRequestReceived(self, xform_name, poem):
        new_poem = self.factory.transform(xform_name, poem)

        if new_poem is not None:
            self.sendString(new_poem)

        self.transport.loseConnection()


class TransformFactory(ServerFactory):

    protocol = TransformProtocol

    def __init__(self, service):
        self.service = service

    def transform(self, xform_name, poem):
        thunk = getattr(self, 'xform_%s' % (xform_name,), None)

        if thunk is None: # no such transform
            return None

        try:
            return thunk(poem)
        except:
            return None # transform failed

    def xform_cummingsify(self, poem):
        return self.service.cummingsify(poem)


def main():
    options = parse_args()

    service = TransformService()

    factory = TransformFactory(service)

    from twisted.internet import reactor

    port = reactor.listenTCP(options.port or 0, factory,
                             interface=options.iface)

    print 'Serving transforms on %s.' % (port.getHost(),)

    reactor.run()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = poetry-proxy
# This is the Twisted Poetry Proxy, version 2.0

import optparse

from twisted.internet.defer import Deferred, succeed
from twisted.internet.protocol import ClientFactory, ServerFactory, Protocol


def parse_args():
    usage = """usage: %prog [options] [hostname]:port

This is the Poetry Proxy, version 2.0.

  python poetry-proxy.py [hostname]:port

If you are in the base directory of the twisted-intro package,
you could run it like this:

  python twisted-server-2/poetry-proxy.py 10000

to proxy the poem for the server running on port 10000.
"""

    parser = optparse.OptionParser(usage)

    help = "The port to listen on. Default to a random available port."
    parser.add_option('--port', type='int', help=help)

    help = "The interface to listen on. Default is localhost."
    parser.add_option('--iface', help=help, default='localhost')

    options, args = parser.parse_args()

    if len(args) != 1:
        parser.error('Provide exactly one server address.')

    def parse_address(addr):
        if ':' not in addr:
            host = '127.0.0.1'
            port = addr
        else:
            host, port = addr.split(':', 1)

        if not port.isdigit():
            parser.error('Ports must be integers.')

        return host, int(port)

    return options, parse_address(args[0])


class PoetryProxyProtocol(Protocol):

    def connectionMade(self):
        d = self.factory.service.get_poem()
        d.addCallback(self.transport.write)
        d.addBoth(lambda r: self.transport.loseConnection())


class PoetryProxyFactory(ServerFactory):

    protocol = PoetryProxyProtocol

    def __init__(self, service):
        self.service = service


class PoetryClientProtocol(Protocol):

    poem = ''

    def dataReceived(self, data):
        self.poem += data

    def connectionLost(self, reason):
        self.poemReceived(self.poem)

    def poemReceived(self, poem):
        self.factory.poem_finished(poem)


class PoetryClientFactory(ClientFactory):

    protocol = PoetryClientProtocol

    def __init__(self):
        self.deferred = Deferred()

    def poem_finished(self, poem):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.callback(poem)

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason)


class ProxyService(object):

    poem = None # the cached poem

    def __init__(self, host, port):
        self.host = host
        self.port = port

    def get_poem(self):
        if self.poem is not None:
            print 'Using cached poem.'
            # return an already-fired deferred
            return succeed(self.poem)

        print 'Fetching poem from server.'
        factory = PoetryClientFactory()
        factory.deferred.addCallback(self.set_poem)
        from twisted.internet import reactor
        reactor.connectTCP(self.host, self.port, factory)
        return factory.deferred

    def set_poem(self, poem):
        self.poem = poem
        return poem


def main():
    options, server_addr = parse_args()

    service = ProxyService(*server_addr)

    factory = PoetryProxyFactory(service)

    from twisted.internet import reactor

    port = reactor.listenTCP(options.port or 0, factory,
                             interface=options.iface)

    print 'Proxying %s on %s.' % (server_addr, port.getHost())

    reactor.run()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = fastpoetry
# This is the Twisted Fast Poetry Server, version 2.0

from twisted.application import internet, service
from twisted.internet.protocol import ServerFactory, Protocol
from twisted.python import log

# Normally we would import these classes from another module.

class PoetryProtocol(Protocol):

    def connectionMade(self):
        poem = self.factory.service.poem
        log.msg('sending %d bytes of poetry to %s'
                % (len(poem), self.transport.getPeer()))
        self.transport.write(poem)
        self.transport.loseConnection()


class PoetryFactory(ServerFactory):

    protocol = PoetryProtocol

    def __init__(self, service):
        self.service = service


class PoetryService(service.Service):

    def __init__(self, poetry_file):
        self.poetry_file = poetry_file

    def startService(self):
        service.Service.startService(self)
        self.poem = open(self.poetry_file).read()
        log.msg('loaded a poem from: %s' % (self.poetry_file,))


# configuration parameters
port = 10000
iface = 'localhost'
poetry_file = 'poetry/ecstasy.txt'

# this will hold the services that combine to form the poetry server
top_service = service.MultiService()

# the poetry service holds the poem. it will load the poem when it is
# started
poetry_service = PoetryService(poetry_file)
poetry_service.setServiceParent(top_service)

# the tcp service connects the factory to a listening socket. it will
# create the listening socket when it is started
factory = PoetryFactory(poetry_service)
tcp_service = internet.TCPServer(port, factory, interface=iface)
tcp_service.setServiceParent(top_service)

# this variable has to be named 'application'
application = service.Application("fastpoetry")

# this hooks the collection we made to the application
top_service.setServiceParent(application)

# at this point, the application is ready to go. when started by
# twistd it will start the child services, thus starting up the
# poetry server

########NEW FILE########
__FILENAME__ = poetry-proxy
# This is the Twisted Poetry Proxy, version 3.0

import optparse

from twisted.internet.defer import Deferred, succeed
from twisted.internet.protocol import ClientFactory, ServerFactory, Protocol


def parse_args():
    usage = """usage: %prog [options] [hostname]:port

This is the Poetry Proxy, version 3.0.

  python poetry-proxy.py [hostname]:port

If you are in the base directory of the twisted-intro package,
you could run it like this:

  python twisted-server-4/poetry-proxy.py 10000

to proxy the poem for the server running on port 10000.
"""

    parser = optparse.OptionParser(usage)

    help = "The port to listen on. Default to a random available port."
    parser.add_option('--port', type='int', help=help)

    help = "The interface to listen on. Default is localhost."
    parser.add_option('--iface', help=help, default='localhost')

    options, args = parser.parse_args()

    if len(args) != 1:
        parser.error('Provide exactly one server address.')

    def parse_address(addr):
        if ':' not in addr:
            host = '127.0.0.1'
            port = addr
        else:
            host, port = addr.split(':', 1)

        if not port.isdigit():
            parser.error('Ports must be integers.')

        return host, int(port)

    return options, parse_address(args[0])


class PoetryProxyProtocol(Protocol):

    def connectionMade(self):
        self.deferred = self.factory.service.get_poem()
        self.deferred.addCallback(self.transport.write)
        self.deferred.addBoth(lambda r: self.transport.loseConnection())

    def connectionLost(self, reason):
        if self.deferred is not None:
            deferred, self.deferred = self.deferred, None
            deferred.cancel() # cancel the deferred if it hasn't fired


class PoetryProxyFactory(ServerFactory):

    protocol = PoetryProxyProtocol

    def __init__(self, service):
        self.service = service


class PoetryClientProtocol(Protocol):

    poem = ''

    def dataReceived(self, data):
        self.poem += data

    def connectionLost(self, reason):
        self.poemReceived(self.poem)

    def poemReceived(self, poem):
        self.factory.poem_finished(poem)


class PoetryClientFactory(ClientFactory):

    protocol = PoetryClientProtocol

    def __init__(self, deferred):
        self.deferred = deferred

    def poem_finished(self, poem):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.callback(poem)

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason)


class ProxyService(object):

    poem = None # the cached poem

    def __init__(self, host, port):
        self.host = host
        self.port = port

    def get_poem(self):
        if self.poem is not None:
            print 'Using cached poem.'
            # return an already-fired deferred
            return succeed(self.poem)

        def canceler(d):
            print 'Canceling poem download.'
            factory.deferred = None
            connector.disconnect()

        print 'Fetching poem from server.'
        deferred = Deferred(canceler)
        deferred.addCallback(self.set_poem)
        factory = PoetryClientFactory(deferred)
        from twisted.internet import reactor
        connector = reactor.connectTCP(self.host, self.port, factory)
        return factory.deferred

    def set_poem(self, poem):
        self.poem = poem
        return poem


def main():
    options, server_addr = parse_args()

    service = ProxyService(*server_addr)

    factory = PoetryProxyFactory(service)

    from twisted.internet import reactor

    port = reactor.listenTCP(options.port or 0, factory,
                             interface=options.iface)

    print 'Proxying %s on %s.' % (server_addr, port.getHost())

    reactor.run()


if __name__ == '__main__':
    main()

########NEW FILE########
