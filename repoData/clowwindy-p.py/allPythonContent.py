__FILENAME__ = p
#!/usr/bin/python
import sys
from twisted.web import http, proxy
from twisted.internet import reactor

HEAD = 'Fuck GFW\x01\r\n'
f = http.HTTPFactory()
f.protocol = proxy.Proxy
if 'client' in sys.argv:
    _connectTCP = reactor.connectTCP  # redirect to our server
    reactor.connectTCP = lambda host, p, factory: _connectTCP(sys.argv[2], 1984, factory)
    _sendCommand = http.HTTPClient.sendCommand  # prepend HEAD
    http.HTTPClient.sendCommand = lambda self, command, path: _sendCommand(self, HEAD + command, path)
    reactor.listenTCP(8080, f)
elif 'server' in sys.argv:
    _process = proxy.ProxyRequest.process  # convert to absolute path
    proxy.ProxyRequest.process = lambda self: (setattr(self, 'uri', 'http://%s%s' % (self.getHeader('host'), self.uri)), _process(self))
    _lineReceived = http.HTTPChannel.lineReceived  # remove HEAD, if no HEAD, raise
    http.HTTPChannel.lineReceived = lambda self, line: (
        _lineReceived(self, line) or self.v if line != HEAD.strip() else setattr(self, 'v', None)
    )
    reactor.listenTCP(1984, f)
else:
    sys.exit('p.py server\np.py client server_ip')
reactor.run()

########NEW FILE########
