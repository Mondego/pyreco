__FILENAME__ = server
from twisted.python import log
from twisted.web import http, proxy

__author__ = "Yashin Mehaboobe (@sp3ctr3)"

class ProxyClient(proxy.ProxyClient):
    """Modify response as well as header here.
    """
    def handleHeader(self, key, value):
        """
        Modify header here
        """
        log.msg("Header: %s: %s" % (key, value))
        proxy.ProxyClient.handleHeader(self, key, value)

    def handleResponsePart(self, buffer):
        """
        Modify buffer to modify response. For example replacing buffer with buffer[::-1] will lead to a reversed output.
        This might cause content encoding errors. Currently test only on text only websites
        """
        log.msg("Content: %s" % (buffer,))
        proxy.ProxyClient.handleResponsePart(self, buffer)

class ProxyClientFactory(proxy.ProxyClientFactory):
    protocol = ProxyClient

class ProxyRequest(proxy.ProxyRequest):
    protocols = dict(http=ProxyClientFactory)

class Proxy(proxy.Proxy):
    requestFactory = ProxyRequest

class ProxyFactory(http.HTTPFactory):
    protocol = Proxy
portstr = "tcp:8080:interface=localhost" # serve on localhost:8080

if __name__ == '__main__': 
    import sys
    from twisted.internet import endpoints, reactor

    def shutdown(reason, reactor, stopping=[]):
        """Stop the reactor."""
        if stopping: return
        stopping.append(True)
        if reason:
            log.msg(reason.value)
        reactor.callWhenRunning(reactor.stop)

    log.startLogging(sys.stdout)
    endpoint = endpoints.serverFromString(reactor, portstr)
    d = endpoint.listen(ProxyFactory())
    d.addErrback(shutdown, reactor)
    reactor.run()


########NEW FILE########
__FILENAME__ = testclient
import urllib2, sys
from BeautifulSoup import BeautifulSoup
from difflib import context_diff
from optparse import OptionParser

def testBasicRequest(url = None):
	#Change proxy settings here
	proxy = urllib2.ProxyHandler({'http': '127.0.0.1:8080'})
	opener = urllib2.build_opener(proxy)
	
	#allows custom urls
	if url is None:
		req = urllib2.Request('http://www.google.com')
	else:
		req = urllib2.Request(url)
		
	#Add headers here by calling req.add_header
	req.add_header('Referrer', 'OpenFaux')
	urllib2.install_opener(opener)
	res=urllib2.urlopen(req)
	soup=BeautifulSoup(res.read())
	print soup.prettify()
	
def evalOpenfauxProxy(url = None):
	#Change proxy settings here
	proxy = urllib2.ProxyHandler({'http': '127.0.0.1:8080'})
	opener = urllib2.build_opener(proxy)
	
	#allows custom urls
	if url is None:
		req = urllib2.Request('http://www.google.com')
	else:
		req = urllib2.Request(url)
		
	res_no_proxy = urllib2.urlopen(req)
	res = opener.open(req)

	#print the diff of the responses
	#This could be more elaborate
	s1 = res_no_proxy.readlines()
	s2 = res.readlines()
	for line in context_diff(s1, s2, fromfile='NoProxy', tofile='Proxy'):
		sys.stdout.write(line)
		
# Option parsing could be cleaned up a bit
def main(argv):
	usage = "usage: %prog [options] arg"
	parser = OptionParser(usage)
	# Add cmdline options here
	parser.add_option("-b", "--basicrequest", action="store_true", dest="basicrequest")
	parser.add_option("-e", "--eval", action="store_true", dest="evaluate")
	parser.add_option("-u", "--url", action="store", dest="url")
	
	(options, args) = parser.parse_args()
	if options.basicrequest:
		testBasicRequest(options.url)
	if options.evaluate:
		evalOpenfauxProxy(options.url)
		
main(sys.argv)
		
	

########NEW FILE########
