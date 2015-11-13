__FILENAME__ = test
#!/usr/bin/env python

import unittest
import urllib2
import subprocess
import os
import time

import tornado.ioloop
import tornado.httpclient

import sys
sys.path.append('../')
from tornado_proxy import run_proxy

class TestStandaloneProxy(unittest.TestCase):
    def setUp(self):
        self.proxy = subprocess.Popen(['python', 'tornado_proxy/proxy.py',
            '8888'])
        proxy_support = urllib2.ProxyHandler({
            "https": "http://localhost:8888",
            "http": "http://localhost:8888"
        })
        opener = urllib2.build_opener(proxy_support)
        urllib2.install_opener(opener)
        # make sure the subprocess started listening on the port
        time.sleep(1)

    def tearDown(self):
        os.kill(self.proxy.pid, 15)
        time.sleep(1)
        os.kill(self.proxy.pid, 9)

    def test(self):
        base_url = '//httpbin.org/'
        urllib2.urlopen('https:' + base_url + 'get').read()
        urllib2.urlopen('http:' + base_url + 'get').read()
        urllib2.urlopen('https:' + base_url + 'post', '').read()
        urllib2.urlopen('http:' + base_url + 'post', '').read()


class TestTornadoProxy(unittest.TestCase):
    def setUp(self):
        self.ioloop = tornado.ioloop.IOLoop.instance()
        run_proxy(8889, start_ioloop=False)

    def tearDown(self):
        pass

    def test(self):
        def handle_response(resp):
            self.assertIsNone(resp.error)
            self.ioloop.stop()

        tornado.httpclient.AsyncHTTPClient.configure(
            "tornado.curl_httpclient.CurlAsyncHTTPClient")
        client = tornado.httpclient.AsyncHTTPClient()

        req = tornado.httpclient.HTTPRequest('http://httpbin.org/',
            proxy_host='127.0.0.1', proxy_port=8889)
        client.fetch(req, handle_response)
        self.ioloop.start()


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = proxy
#!/usr/bin/env python
#
# Simple asynchronous HTTP proxy with tunnelling (CONNECT).
#
# GET/POST proxying based on
# http://groups.google.com/group/python-tornado/msg/7bea08e7a049cf26
#
# Copyright (C) 2012 Senko Rasic <senko.rasic@dobarkod.hr>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import sys
import socket

import tornado.httpserver
import tornado.ioloop
import tornado.iostream
import tornado.web
import tornado.httpclient

__all__ = ['ProxyHandler', 'run_proxy']


class ProxyHandler(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ['GET', 'POST', 'CONNECT']

    @tornado.web.asynchronous
    def get(self):

        def handle_response(response):
            if response.error and not isinstance(response.error,
                    tornado.httpclient.HTTPError):
                self.set_status(500)
                self.write('Internal server error:\n' + str(response.error))
            else:
                self.set_status(response.code)
                for header in ('Date', 'Cache-Control', 'Server',
                        'Content-Type', 'Location'):
                    v = response.headers.get(header)
                    if v:
                        self.set_header(header, v)
                if response.body:
                    self.write(response.body)
            self.finish()

        req = tornado.httpclient.HTTPRequest(url=self.request.uri,
            method=self.request.method, body=self.request.body,
            headers=self.request.headers, follow_redirects=False,
            allow_nonstandard_methods=True)

        client = tornado.httpclient.AsyncHTTPClient()
        try:
            client.fetch(req, handle_response)
        except tornado.httpclient.HTTPError as e:
            if hasattr(e, 'response') and e.response:
                handle_response(e.response)
            else:
                self.set_status(500)
                self.write('Internal server error:\n' + str(e))
                self.finish()

    @tornado.web.asynchronous
    def post(self):
        return self.get()

    @tornado.web.asynchronous
    def connect(self):
        host, port = self.request.uri.split(':')
        client = self.request.connection.stream

        def read_from_client(data):
            upstream.write(data)

        def read_from_upstream(data):
            client.write(data)

        def client_close(data=None):
            if upstream.closed():
                return
            if data:
                upstream.write(data)
            upstream.close()

        def upstream_close(data=None):
            if client.closed():
                return
            if data:
                client.write(data)
            client.close()

        def start_tunnel():
            client.read_until_close(client_close, read_from_client)
            upstream.read_until_close(upstream_close, read_from_upstream)
            client.write(b'HTTP/1.0 200 Connection established\r\n\r\n')

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        upstream = tornado.iostream.IOStream(s)
        upstream.connect((host, int(port)), start_tunnel)


def run_proxy(port, start_ioloop=True):
    """
    Run proxy on the specified port. If start_ioloop is True (default),
    the tornado IOLoop will be started immediately.
    """
    app = tornado.web.Application([
        (r'.*', ProxyHandler),
    ])
    app.listen(port)
    ioloop = tornado.ioloop.IOLoop.instance()
    if start_ioloop:
        ioloop.start()

if __name__ == '__main__':
    port = 8888
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    print ("Starting HTTP proxy on port %d" % port)
    run_proxy(port)

########NEW FILE########
