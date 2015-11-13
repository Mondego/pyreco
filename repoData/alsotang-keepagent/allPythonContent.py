__FILENAME__ = certutil
#! /usr/bin/env python
# coding=utf-8

import threading
import lib
import sys
import logging
import time
import os

try:
    from OpenSSL import crypto
except ImportError:
    logging.error('You should install `OpenSSL`, run `sudo pip install pyopenssl` or other command depends on your system.')
    sys.exit(-1)


CA = None
CALock = threading.Lock()
EXPIRE_DELAY = 60*60*24*365*10 # 10 years

CERT_SUBJECTS = crypto.X509Name(crypto.X509().get_subject())
CERT_SUBJECTS.C = 'CN'
CERT_SUBJECTS.ST = 'SiChuan'
CERT_SUBJECTS.L = 'SiChuan Univ.'
CERT_SUBJECTS.OU = 'KeepAgent Branch'


CA_SUBJECTS = crypto.X509Name(CERT_SUBJECTS)
CA_SUBJECTS.OU = 'KeepAgent Root'
CA_SUBJECTS.O = 'KeepAgent'
CA_SUBJECTS.CN = 'KeepAgent CA'

def readBinFile(filename):
    with open(filename, 'rb') as f:
        content = f.read()
    return content

def writeBinFile(filename, content):
    with open(filename, 'wb') as f:
        f.write(content)

def loadPEM(pem, method):
    methods = ('load_certificate', 'load_privatekey')
    return getattr(crypto, methods[method])(crypto.FILETYPE_PEM, pem)


def dumpPEM(obj, method):
    methods = ('dump_certificate', 'dump_privatekey')
    return getattr(crypto, methods[method])(crypto.FILETYPE_PEM, obj)


def createPKey():
    pkey = crypto.PKey()
    pkey.generate_key(crypto.TYPE_RSA, 1024)
    return pkey


def createCert(host, digest='sha1'):
    cert = crypto.X509() # 得到一个X509对象
    cert.set_version(0)
    cert.set_serial_number( int(time.time() * 10000000) ) # 序号，不重复即可。

    #证书有效与过期时间
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(EXPIRE_DELAY )

    cert.set_issuer(CA[0].get_subject() ) # 得到CA的信息

    subjects = crypto.X509Name(CERT_SUBJECTS)
    subjects.O = host
    subjects.CN = host
    cert.set_subject(subjects)

    pubkey = createPKey()
    cert.set_pubkey(pubkey)

    cert.sign(CA[1], digest)

    return (dumpPEM(cert, 0), dumpPEM(pubkey, 1))


def getCertificate(host):
    certFile = os.path.join(lib.basedir, 'certs/%s.crt' % host)
    keyFile = os.path.join(lib.basedir, 'certs/%s.key' % host)

    if os.path.exists(certFile):
        return (certFile, keyFile)
    else:
        with CALock:
            if not os.path.exists(certFile):
                logging.info('generate certificate for %s', host)
                cert, pkey = createCert(host)
                writeBinFile(certFile, str(cert))
                writeBinFile(keyFile, str(pkey))
    return (certFile, keyFile)


def init():
    certFile = os.path.join( lib.basedir, 'CA.crt') 
    keyFile = os.path.join( lib.basedir, 'CA.key')
    cacert = readBinFile(certFile)
    cakey = readBinFile(keyFile)
    global CA
    CA = (loadPEM(cacert, 0), loadPEM(cakey, 1))

def makeCA():
    '''得到一对新的CA.crt与CA.key'''

    cert = crypto.X509()
    cert.set_version(0)
    cert.set_serial_number(0)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(EXPIRE_DELAY)
    cert.set_issuer(CA_SUBJECTS)
    cert.set_subject(CA_SUBJECTS)

    pubkey = createPKey()
    cert.set_pubkey(pubkey)
    cert.sign(pubkey, 'sha1')
    return (dumpPEM(cert, 0), dumpPEM(pubkey, 1))

if __name__ == '__main__':
    # 不要随便运行这段代码，运行后将生成新的CA相关文件，需要把浏览器中的CA文件删除后
    # 重新导入新生成的。

    for f in os.listdir('certs'):
        if f.endswith('.md'): continue
        os.remove( os.path.join('certs', f))

    certFile = os.path.join(lib.basedir, 'CA.crt')
    keyFile = os.path.join(lib.basedir, 'CA.key')

    cert, key = makeCA()
    writeBinFile(certFile, cert)
    writeBinFile(keyFile, key)
    














    




########NEW FILE########
__FILENAME__ = cipher
# coding=utf-8
from Crypto.Cipher import AES
import os

BLOCK_SIZE = AES.block_size

cipher = None

def init(key):
    '''
    @key key要求是32字节的str
    '''
    global cipher
    cipher = AES.new(key)


def pad(data):
    patlen = BLOCK_SIZE - len(data) % BLOCK_SIZE
    return data + (patlen - 1) * ' ' + chr(patlen)

def unpad(data):
    patlen = ord(data[-1])
    return data[:-patlen]

def encrypt(data):
    return cipher.encrypt(pad(data))
    
def decrypt(data):
    return unpad(cipher.decrypt(data))

if __name__ == '__main__':
    import hashlib
    key = hashlib.md5(os.urandom(128)).hexdigest() # 随机生成一个32 bytes的key
    print key
    init(key) # 32 bytes 的str
    data = 'hello world' * 10
    print decrypt(encrypt(data))


########NEW FILE########
__FILENAME__ = config
appid = 'keepagent'

listen_port = 7808


########NEW FILE########
__FILENAME__ = keepagent
#! /usr/bin/env python
# coding=utf-8

# Inspired by and based on [GoAgent](https://code.google.com/p/goagent/).

import SocketServer
import BaseHTTPServer
import logging
import json
import urllib2
import socket
import ssl
import random

import lib
import config
import certutil

# 初始化并返回一个 get_g_opener 闭包函数，调用该函数会随机返回一个google的ip
def init_g_opener():

    # 得到google.cn的ip集合: `googlecn_ips`
    google_cn_host = 'g.cn'

    def get_g_ips(host):
        '''由域名得到相应的ip列表'''

        results = socket.getaddrinfo(host, None)
        ips = set() # 不要重复的ip
        for i in results:
            ip = i[4][0]
            if ':' not in ip:
                ips.add(ip)
        ips = list(ips)
        return ips

    google_cn_ips = get_g_ips(google_cn_host)

    def get_g_opener():
        '''返回一个使用google_cn或者google_hk作为代理的urllib2 opener'''

        proxy_handler = urllib2.ProxyHandler(
            # 从google_cn_ips中随机选择一个IP出来
            {'http': random.choice( google_cn_ips )}
            )
        g_opener = urllib2.build_opener(proxy_handler)
        return g_opener

    return get_g_opener

class LocalProxyHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    # refer to: https://developers.google.com/appengine/docs/python/urlfetch/overview
    forbidden_headers = ('host', 'vary', # content-length, 
                         'via', 'x-forwarded-for', 'x-proxyuser-iP')
    
    def do_GET(self):

        # headers is a dict-like object, it doesn't have `iteritems` method, so convert it to `dict`
        req_headers = dict(self.headers)  # dict
        req_headers = dict((h, v) for h, v in req_headers.iteritems() if h.lower() not in self.forbidden_headers)

        req_body_len = int(req_headers.get('content-length', 0))
        req_body = self.rfile.read(req_body_len) # bin or str

        payload = {
            'command': self.command, # str
            'path': self.path, # str
            'headers': json.dumps(req_headers), # json
            'payload': lib.btoa(req_body), # str
        }

        #导出并压缩payload
        payload = lib.dumpDict(payload)

        #判断是否需要加密
        if self.path.startswith('https'):
            payload = lib.encrypt(payload)
        else:
            payload = '0' + payload

        # 向GAE获取的过程
        for i in range(4):
            try:
                res = urllib2.urlopen(gaeServer, payload, lib.deadlineRetry[i])
            except (urllib2.URLError, socket.timeout) as e: 
                logging.error(e)
                continue

            if res.code == 200:  # 如果打开GAE没发生错误
                result = res.read()
                result = lib.decrypt(result)
                result = lib.loadDict( result )

                res_status_code = result.status_code
                res_headers = json.loads(result.headers)
                res_content = lib.atob(result.content)
                break
        else:
            # 如果urllib2打开GAE都出错的话，就换个g_opener吧。
            urllib2.install_opener( get_g_opener() ) 

        # 返回数据给浏览器的过程
        try:
            self.send_response(res_status_code) # 200 or or 301 or 404

            res_headers['connection'] = 'close' # 这样不会对速度造成影响，反而能使很多的请求表现得更为准确。
            for k, v in res_headers.iteritems():
                try:
                    self.send_header(k, v)
                except UnicodeEncodeError: # google plus里面就遇到了v包含中文的情况
                    pass
            self.end_headers()
            self.wfile.write(res_content)
        except socket.error, e:
            # 打开了网页后，在数据到达浏览器之前又把网页关闭了而导致的错误。
            logging.error(e)

    def do_POST(self):
        return self.do_GET()

    def do_CONNECT(self): 
        host, _, port = self.path.rpartition(':')

        self.connection.sendall('%s 200 Connection established\r\n\r\n' % self.protocol_version)

        hostCert, hostKey = certutil.getCertificate(host)

        self._realpath = self.path

        self.request = ssl.wrap_socket(self.connection, hostKey, hostCert, True)
        self.setup()

        self.raw_requestline = self.rfile.readline(65537)

        self.parse_request()

        self.path = 'https://%s%s' % (self._realpath, self.path)

        self.do_GET()

        try:
            self.connection.shutdown(socket.SHUT_WR) # TODO: 发送相应http指令使socket关闭
        except socket.error:
            pass
        

class LocalProxyServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer): 
    daemon_threads = True
    

def init_info():
    return (
        '#' * 50 +
'''
        KeepAgent version: %s
        Protocol: %s
        Listening Adress: localhost:%s
        Appid: %s
''' % (lib.version,
       lib.protocol,
       config.listen_port, 
       config.appid
      ) + 
        '#' * 50
        )

get_g_opener = init_g_opener()

gaeServer = ('http://%s.appspot.com/' % config.appid)
urllib2.install_opener( get_g_opener() )


def main():
    print init_info() 
    
    certutil.init()

    server_address = ('', config.listen_port)
    httpd = LocalProxyServer(server_address, LocalProxyHandler)

    print '获取更新信息当中...'
    print '~~%s~~' % urllib2.urlopen(gaeServer + 'getupdate').read()
    print 'server is running...'
    httpd.serve_forever()

    


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = lib
#! /usr/bin/env python
# coding=utf-8

import base64
import json
import zlib
import os

try:
    import cipher
    #如果修改了crypt_key，记得重新上传server。
    crypt_key = ''
    if crypt_key:
        cipher.init(crypt_key)
except ImportError, e:
    cipher = None

version = 'v1.1.1'

###

protocol = 'keepagent v2'

deadlineRetry = (2, 3, 5, 60)

basedir = os.path.dirname(__file__)

def encrypt(blob):
    if cipher and crypt_key:
        return '1' + cipher.encrypt(blob)
    return '0' + blob

def decrypt(blob):
    if blob[0] == '0':
        return blob[1:]
    else:
        return cipher.decrypt(blob[1:])

class JSDict(dict):
    '''convert a `dict` to a JavaScript-style object'''

    def __getattr__(self, attr):
        return self.get(attr, None)

def dumpDict(d):
    ''' d is a `dict`'''

    j = json.dumps(d)
    z = zlib.compress(j)
    return z

def loadDict(z):
    ''' z is a zlib blob'''

    j = zlib.decompress(z)
    d = json.loads(j)
    jd = JSDict(d)
    return jd

def btoa(s):
    '''convert blob to string in orther to
    be included in a JSON.
    '''

    return base64.encodestring(s)

def atob(b):
    '''inverse of `btoa`'''

    return base64.decodestring(b)


if __name__ == '__main__':
    text = 'hello world ' * 10
    print decrypt(encrypt(text))



    





########NEW FILE########
__FILENAME__ = cipher
../client_linux/cipher.py
########NEW FILE########
__FILENAME__ = lib
../client_linux/lib.py
########NEW FILE########
__FILENAME__ = main
#! /usr/bin/env python
# coding=utf-8

import webapp2
import logging
import json

from google.appengine.api import urlfetch

import lib

class MainPage(webapp2.RequestHandler):
    def get(self):
        text = '''<p>This version of keepagent server use <strong>%s</strong> protocol.</p>
        <p>请检查您的客户端是否使用了同一协议。</p>''' % lib.protocol

        self.response.headers['Content-Type'] = 'text/html; charset=UTF-8'
        self.response.write(text)
    
    def post(self):
        #记录一个是否加密的状态变量
        is_crypted = int(self.request.body[0])

        req_body = lib.decrypt(self.request.body)
        req_body = lib.loadDict(req_body)

        method = getattr(urlfetch, req_body.command)

        # 如超时则自动重试4次，4次失败后，GAE会抛错并返回给client 500错误。
        for dl in lib.deadlineRetry:
            try:
                res = urlfetch.fetch(url=req_body.path,
                                     payload=lib.atob(req_body.payload),
                                     method=method,
                                     headers=json.loads(req_body.headers),
                                     follow_redirects=False,
                                     deadline=dl,
                                     validate_certificate=True,
                                     )
            except urlfetch.DownloadError, e:
                logging.error(u'下载错误: %s' % e)
            else:
                break #没有抛出任何异常则跳出循环

        result = {
            'status_code': res.status_code, # int
            # TODO: If there are multiple headers with the same name, their values will be joined into a single comma-separated string. If the values already contained commas (for example, Set-Cookie headers), you may want to use header_msg.get_headers(header_name) to retrieve a list of values instead.
            'headers': json.dumps(dict(res.headers)), 
            'content': lib.btoa(res.content), # str
        }

        result = lib.dumpDict(result)

        if is_crypted:
            result = lib.encrypt(result)
        else:
            result = '0' + result
        
        self.response.write(result)




class UpdatePage(webapp2.RequestHandler):
    def get(self):
        text = urlfetch.fetch(url='https://raw.github.com/alsotang/keepagent/master/update_message').content

        self.response.headers['Content-Type'] = 'text/html; charset=UTF-8'
        self.response.write(text)

app = webapp2.WSGIApplication([(r'/getupdate', UpdatePage),
                               (r'/.*', MainPage)])

########NEW FILE########
