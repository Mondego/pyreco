__FILENAME__ = conf
# @gist config
import qiniu.conf

qiniu.conf.ACCESS_KEY = "<YOUR_APP_ACCESS_KEY>"
qiniu.conf.SECRET_KEY = "<YOUR_APP_SECRET_KEY>"
# @endgist

########NEW FILE########
__FILENAME__ = demo
# -*- coding: utf-8 -*-
import os
import sys
import StringIO

# @gist import_io
import qiniu.io
# @endgist
import qiniu.conf
# @gist import_rs
import qiniu.rs
# @endgist
# @gist import_fop
import qiniu.fop
# @endgist
# @gist import_resumable_io
import qiniu.resumable_io as rio
# @endgist
# @gist import_rsf
import qiniu.rsf
# @endgist

bucket_name = None
uptoken = None
key = None
key2 = None
key3 = None
domain = None
pic_key = None

# ----------------------------------------------------------


def setup(access_key, secret_key, bucketname, bucket_domain, pickey):
    global bucket_name, uptoken, key, key2, domain, key3, pic_key
    qiniu.conf.ACCESS_KEY = access_key
    qiniu.conf.SECRET_KEY = secret_key
    bucket_name = bucketname
    domain = bucket_domain
    pic_key = pickey
    # @gist uptoken
    policy = qiniu.rs.PutPolicy(bucket_name)
    uptoken = policy.token()
    # @endgist
    key = "python-demo-put-file"
    key2 = "python-demo-put-file-2"
    key3 = "python-demo-put-file-3"


def _setup():
    ''' 根据环境变量配置信息 '''
    access_key = getenv("QINIU_ACCESS_KEY")
    if access_key is None:
        exit("请配置环境变量 QINIU_ACCESS_KEY")
    secret_key = getenv("QINIU_SECRET_KEY")
    bucket_name = getenv("QINIU_TEST_BUCKET")
    domain = getenv("QINIU_TEST_DOMAIN")
    pickey = 'QINIU_UNIT_TEST_PIC'
    setup(access_key, secret_key, bucket_name, domain, pickey)


def getenv(name):
    env = os.getenv(name)
    if env is None:
        sys.stderr.write("请配置环境变量 %s\n" % name)
        exit(1)
    return env


def get_demo_list():
    return [put_file, put_binary,
            resumable_put, resumable_put_file,
            stat, copy, move, delete, batch,
            image_info, image_exif, image_view,
            list_prefix, list_prefix_all,
            ]


def run_demos(demos):
    for i, demo in enumerate(demos):
        print '%s.%s ' % (i + 1, demo.__doc__),
        demo()
        print

# ----------------------------------------------------------


def make_private_url(domain, key):
    ''' 生成私有下载链接 '''
    # @gist dntoken
    base_url = qiniu.rs.make_base_url(domain, key)
    policy = qiniu.rs.GetPolicy()
    private_url = policy.make_request(base_url)
    # @endgist
    return private_url


def put_file():
    ''' 演示上传文件的过程 '''
    # 尝试删除
    qiniu.rs.Client().delete(bucket_name, key)

    # @gist put_file
    localfile = "%s" % __file__

    ret, err = qiniu.io.put_file(uptoken, key, localfile)
    if err is not None:
        sys.stderr.write('error: %s ' % err)
        return
    # @endgist


def put_binary():
    ''' 上传二进制数据 '''
    # 尝试删除
    qiniu.rs.Client().delete(bucket_name, key)

    # @gist put
    extra = qiniu.io.PutExtra()
    extra.mime_type = "text/plain"

    # data 可以是str或read()able对象
    data = StringIO.StringIO("hello!")
    ret, err = qiniu.io.put(uptoken, key, data, extra)
    if err is not None:
        sys.stderr.write('error: %s ' % err)
        return
    # @endgist


def resumable_put():
    ''' 断点续上传 '''
    # 尝试删除
    qiniu.rs.Client().delete(bucket_name, key)

    # @gist resumable_put
    a = "resumable upload string"
    extra = rio.PutExtra(bucket_name)
    extra.mime_type = "text/plain"
    ret, err = rio.put(uptoken, key, StringIO.StringIO(a), len(a), extra)
    if err is not None:
        sys.stderr.write('error: %s ' % err)
        return
    print ret,
    # @endgist


def resumable_put_file():
    ''' 断点续上传文件 '''
    # 尝试删除
    qiniu.rs.Client().delete(bucket_name, key)

    # @gist resumable_put_file
    localfile = "%s" % __file__
    extra = rio.PutExtra(bucket_name)

    ret, err = rio.put_file(uptoken, key, localfile, extra)
    if err is not None:
        sys.stderr.write('error: %s ' % err)
        return
    print ret,
    # @endgist


def stat():
    ''' 查看上传文件的内容 '''
    # @gist stat
    ret, err = qiniu.rs.Client().stat(bucket_name, key)
    if err is not None:
        sys.stderr.write('error: %s ' % err)
        return
    print ret,
    # @endgist


def copy():
    ''' 复制文件 '''
    # 初始化
    qiniu.rs.Client().delete(bucket_name, key2)

    # @gist copy
    ret, err = qiniu.rs.Client().copy(bucket_name, key, bucket_name, key2)
    if err is not None:
        sys.stderr.write('error: %s ' % err)
        return
    # @endgist

    stat, err = qiniu.rs.Client().stat(bucket_name, key2)
    if err is not None:
        sys.stderr.write('error: %s ' % err)
        return
    print 'new file:', stat,


def move():
    ''' 移动文件 '''
    # 初始化
    qiniu.rs.Client().delete(bucket_name, key3)

    # @gist move
    ret, err = qiniu.rs.Client().move(bucket_name, key2, bucket_name, key3)
    if err is not None:
        sys.stderr.write('error: %s ' % err)
        return
    # @endgist

    # 查看文件是否移动成功
    ret, err = qiniu.rs.Client().stat(bucket_name, key3)
    if err is not None:
        sys.stderr.write('error: %s ' % err)
        return

    # 查看文件是否被删除
    ret, err = qiniu.rs.Client().stat(bucket_name, key2)
    if err is None:
        sys.stderr.write('error: %s ' % "删除失败")
        return


def delete():
    ''' 删除文件 '''
    # @gist delete
    ret, err = qiniu.rs.Client().delete(bucket_name, key3)
    if err is not None:
        sys.stderr.write('error: %s ' % err)
        return
    # @endgist

    ret, err = qiniu.rs.Client().stat(bucket_name, key3)
    if err is None:
        sys.stderr.write('error: %s ' % "删除失败")
        return


def image_info():
    ''' 查看图片的信息 '''

    # @gist image_info
    # 生成base_url
    url = qiniu.rs.make_base_url(domain, pic_key)

    # 生成fop_url
    image_info = qiniu.fop.ImageInfo()
    url = image_info.make_request(url)

    # 对其签名，生成private_url。如果是公有bucket此步可以省略
    policy = qiniu.rs.GetPolicy()
    url = policy.make_request(url)

    print '可以在浏览器浏览: %s' % url
    # @endgist


def image_exif():
    ''' 查看图片的exif信息 '''
    # @gist exif
    # 生成base_url
    url = qiniu.rs.make_base_url(domain, pic_key)

    # 生成fop_url
    image_exif = qiniu.fop.Exif()
    url = image_exif.make_request(url)

    # 对其签名，生成private_url。如果是公有bucket此步可以省略
    policy = qiniu.rs.GetPolicy()
    url = policy.make_request(url)

    print '可以在浏览器浏览: %s' % url
    # @endgist


def image_view():
    ''' 对图片进行预览处理 '''
    # @gist image_view
    iv = qiniu.fop.ImageView()
    iv.width = 100

    # 生成base_url
    url = qiniu.rs.make_base_url(domain, pic_key)
    # 生成fop_url
    url = iv.make_request(url)
    # 对其签名，生成private_url。如果是公有bucket此步可以省略
    policy = qiniu.rs.GetPolicy()
    url = policy.make_request(url)
    print '可以在浏览器浏览: %s' % url
    # @endgist


def batch():
    ''' 文件处理的批量操作 '''
    # @gist batch_path
    path_1 = qiniu.rs.EntryPath(bucket_name, key)
    path_2 = qiniu.rs.EntryPath(bucket_name, key2)
    path_3 = qiniu.rs.EntryPath(bucket_name, key3)
    # @endgist

    # 查看状态
    # @gist batch_stat
    rets, err = qiniu.rs.Client().batch_stat([path_1, path_2, path_3])
    if err is not None:
        sys.stderr.write('error: %s ' % err)
        return
    # @endgist
    if not [ret['code'] for ret in rets] == [200, 612, 612]:
        sys.stderr.write('error: %s ' % "批量获取状态与预期不同")
        return

    # 复制
    # @gist batch_copy
    pair_1 = qiniu.rs.EntryPathPair(path_1, path_3)
    rets, err = qiniu.rs.Client().batch_copy([pair_1])
    if not rets[0]['code'] == 200:
        sys.stderr.write('error: %s ' % "复制失败")
        return
    # @endgist

    qiniu.rs.Client().batch_delete([path_2])
    # @gist batch_move
    pair_2 = qiniu.rs.EntryPathPair(path_3, path_2)
    rets, err = qiniu.rs.Client().batch_move([pair_2])
    if not rets[0]['code'] == 200:
        sys.stderr.write('error: %s ' % "移动失败")
        return
    # @endgist

    # 删除残留文件
    # @gist batch_delete
    rets, err = qiniu.rs.Client().batch_delete([path_1, path_2])
    if not [ret['code'] for ret in rets] == [200, 200]:
        sys.stderr.write('error: %s ' % "删除失败")
        return
    # @endgist


def list_prefix():
    ''' 列出文件操作 '''
    # @gist list_prefix
    rets, err = qiniu.rsf.Client().list_prefix(
        bucket_name, prefix="test", limit=2)
    if err is not None:
        sys.stderr.write('error: %s ' % err)
        return
    print rets

    # 从上一次list_prefix的位置继续列出文件
    rets2, err = qiniu.rsf.Client().list_prefix(
        bucket_name, prefix="test", limit=1, marker=rets['marker'])
    if err is not None:
        sys.stderr.write('error: %s ' % err)
        return
    print rets2
    # @endgist


def list_prefix_all():
    ''' 列出所有 '''
    list_all(bucket_name, prefix='test_Z', limit=10)

# @gist list_all


def list_all(bucket, rs=None, prefix=None, limit=None):
    if rs is None:
        rs = qiniu.rsf.Client()
    marker = None
    err = None
    while err is None:
        ret, err = rs.list_prefix(
            bucket_name, prefix=prefix, limit=limit, marker=marker)
        marker = ret.get('marker', None)
        for item in ret['items']:
            # do something
            pass
    if err is not qiniu.rsf.EOF:
        # 错误处理
        pass
# @endgist

if __name__ == "__main__":
    _setup()

    demos = get_demo_list()
    run_demos(demos)

########NEW FILE########
__FILENAME__ = fetch
# coding=utf-8
import sys
sys.path.insert(0, "../../")

from base64 import urlsafe_b64encode as b64e
from qiniu.auth import digest

access_key = ""
secret_key = ""

src_url = ""
dest_bucket = ""
dest_key = ""

encoded_url = b64e(src_url)
dest_entry = "%s:%s" % (dest_bucket, dest_key)
encoded_entry = b64e(dest_entry)

api_host = "iovip.qbox.me"
api_path = "/fetch/%s/to/%s" % (encoded_url, encoded_entry)

mac = digest.Mac(access=access_key, secret=secret_key)
client = digest.Client(host=api_host, mac=mac)

ret, err = client.call(path=api_path)
if err is not None:
    print "failed"
    print err
else:
    print "success"

########NEW FILE########
__FILENAME__ = pfop
# coding=utf-8
import sys
sys.path.insert(0, "../../")

from urllib import quote
from qiniu.auth import digest

access_key = ""
secret_key = ""

bucket = ""
key = ""
fops = ""
notify_url = ""
force = False

api_host = "api.qiniu.com"
api_path = "/pfop/"
body = "bucket=%s&key=%s&fops=%s&notifyURL=%s" % \
       (quote(bucket), quote(key), quote(fops), quote(notify_url))

body = "%s&force=1" % (body,) if force is not False else body

content_type = "application/x-www-form-urlencoded"
content_length = len(body)

mac = digest.Mac(access=access_key, secret=secret_key)
client = digest.Client(host=api_host, mac=mac)

ret, err = client.call_with(path=api_path, body=body,
                            content_type=content_type, content_length=content_length)
if err is not None:
    print "failed"
    print err
else:
    print "success"
    print ret

########NEW FILE########
__FILENAME__ = prefetch
# coding=utf-8
import sys
sys.path.insert(0, "../../")

from base64 import urlsafe_b64encode as b64e
from qiniu.auth import digest

access_key = ""
secret_key = ""

bucket = ""
key = ""

entry = "%s:%s" % (bucket, key)
encoded_entry = b64e(entry)


api_host = "iovip.qbox.me"
api_path = "/prefetch/%s" % (encoded_entry)

mac = digest.Mac(access=access_key, secret=secret_key)
client = digest.Client(host=api_host, mac=mac)

ret, err = client.call(path=api_path)
if err is not None:
    print "failed"
    print err
else:
    print "success"

########NEW FILE########
__FILENAME__ = digest
# -*- coding: utf-8 -*-
from urlparse import urlparse
import hmac
from hashlib import sha1
from base64 import urlsafe_b64encode

from .. import rpc
from .. import conf


class Mac(object):
    access = None
    secret = None

    def __init__(self, access=None, secret=None):
        if access is None and secret is None:
            access, secret = conf.ACCESS_KEY, conf.SECRET_KEY
        self.access, self.secret = access, secret

    def __sign(self, data):
        hashed = hmac.new(self.secret, data, sha1)
        return urlsafe_b64encode(hashed.digest())

    def sign(self, data):
        return '%s:%s' % (self.access, self.__sign(data))

    def sign_with_data(self, b):
        data = urlsafe_b64encode(b)
        return '%s:%s:%s' % (self.access, self.__sign(data), data)

    def sign_request(self, path, body, content_type):
        parsedurl = urlparse(path)
        p_query = parsedurl.query
        p_path = parsedurl.path
        data = p_path
        if p_query != "":
            data = ''.join([data, '?', p_query])
        data = ''.join([data, "\n"])

        if body:
            incBody = [
                "application/x-www-form-urlencoded",
            ]
            if content_type in incBody:
                data += body

        return '%s:%s' % (self.access, self.__sign(data))


class Client(rpc.Client):

    def __init__(self, host, mac=None):
        if mac is None:
            mac = Mac()
        super(Client, self).__init__(host)
        self.mac = mac

    def round_tripper(self, method, path, body):
        token = self.mac.sign_request(
            path, body, self._header.get("Content-Type"))
        self.set_header("Authorization", "QBox %s" % token)
        return super(Client, self).round_tripper(method, path, body)

########NEW FILE########
__FILENAME__ = up
# -*- coding: utf-8 -*-
from .. import conf
from .. import rpc


class Client(rpc.Client):
    up_token = None

    def __init__(self, up_token, host=None):
        if host is None:
            host = conf.UP_HOST
        if host.startswith("http://"):
            host = host[7:]
        self.up_token = up_token
        super(Client, self).__init__(host)

    def round_tripper(self, method, path, body):
        self.set_header("Authorization", "UpToken %s" % self.up_token)
        return super(Client, self).round_tripper(method, path, body)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-

ACCESS_KEY = ""
SECRET_KEY = ""

RS_HOST = "rs.qbox.me"
RSF_HOST = "rsf.qbox.me"
UP_HOST = "up.qiniu.com"

from . import __version__
import platform

sys_info = "%s/%s" % (platform.system(), platform.machine())
py_ver = platform.python_version()

USER_AGENT = "QiniuPython/%s (%s) Python/%s" % (__version__, sys_info, py_ver)

########NEW FILE########
__FILENAME__ = fop
# -*- coding:utf-8 -*-


class Exif(object):

    def make_request(self, url):
        return '%s?exif' % url


class ImageView(object):
    mode = 1  # 1或2
    width = None  # width 默认为0，表示不限定宽度
    height = None
    quality = None  # 图片质量, 1-100
    format = None  # 输出格式, jpg, gif, png, tif 等图片格式

    def make_request(self, url):
        target = []
        target.append('%s' % self.mode)

        if self.width is not None:
            target.append("w/%s" % self.width)

        if self.height is not None:
            target.append("h/%s" % self.height)

        if self.quality is not None:
            target.append("q/%s" % self.quality)

        if self.format is not None:
            target.append("format/%s" % self.format)

        return "%s?imageView/%s" % (url, '/'.join(target))


class ImageInfo(object):

    def make_request(self, url):
        return '%s?imageInfo' % url

########NEW FILE########
__FILENAME__ = httplib_chunk
"""
Modified from standard httplib

1. HTTPConnection can send trunked data.
2. Remove httplib's automatic Content-Length insertion when data is a file-like object.
"""

# -*- coding: utf-8 -*-

import httplib
from httplib import _CS_REQ_STARTED, _CS_REQ_SENT, CannotSendHeader, NotConnected
import string
from array import array


class HTTPConnection(httplib.HTTPConnection):

    def send(self, data, is_chunked=False):
        """Send `data' to the server."""
        if self.sock is None:
            if self.auto_open:
                self.connect()
            else:
                raise NotConnected()

        if self.debuglevel > 0:
            print "send:", repr(data)
        blocksize = 8192
        if hasattr(data, 'read') and not isinstance(data, array):
            if self.debuglevel > 0:
                print "sendIng a read()able"
            datablock = data.read(blocksize)
            while datablock:
                if self.debuglevel > 0:
                    print 'chunked:', is_chunked
                if is_chunked:
                    if self.debuglevel > 0:
                        print 'send: with trunked data'
                    lenstr = string.upper(hex(len(datablock))[2:])
                    self.sock.sendall('%s\r\n%s\r\n' % (lenstr, datablock))
                else:
                    self.sock.sendall(datablock)
                datablock = data.read(blocksize)
            if is_chunked:
                self.sock.sendall('0\r\n\r\n')
        else:
            self.sock.sendall(data)

    def _set_content_length(self, body):
        # Set the content-length based on the body.
        thelen = None
        try:
            thelen = str(len(body))
        except (TypeError, AttributeError), te:
            # Don't send a length if this failed
            if self.debuglevel > 0:
                print "Cannot stat!!"
                print te

        if thelen is not None:
            self.putheader('Content-Length', thelen)
            return True
        return False

    def _send_request(self, method, url, body, headers):
        # Honor explicitly requested Host: and Accept-Encoding: headers.
        header_names = dict.fromkeys([k.lower() for k in headers])
        skips = {}
        if 'host' in header_names:
            skips['skip_host'] = 1
        if 'accept-encoding' in header_names:
            skips['skip_accept_encoding'] = 1

        self.putrequest(method, url, **skips)

        is_chunked = False
        if body and header_names.get('Transfer-Encoding') == 'chunked':
            is_chunked = True
        elif body and ('content-length' not in header_names):
            is_chunked = not self._set_content_length(body)
            if is_chunked:
                self.putheader('Transfer-Encoding', 'chunked')
        for hdr, value in headers.iteritems():
            self.putheader(hdr, value)

        self.endheaders(body, is_chunked=is_chunked)

    def endheaders(self, message_body=None, is_chunked=False):
        """Indicate that the last header line has been sent to the server.

        This method sends the request to the server.  The optional
        message_body argument can be used to pass a message body
        associated with the request.  The message body will be sent in
        the same packet as the message headers if it is string, otherwise it is
        sent as a separate packet.
        """
        if self.__state == _CS_REQ_STARTED:
            self.__state = _CS_REQ_SENT
        else:
            raise CannotSendHeader()
        self._send_output(message_body, is_chunked=is_chunked)

    def _send_output(self, message_body=None, is_chunked=False):
        """Send the currently buffered request and clear the buffer.

        Appends an extra \\r\\n to the buffer.
        A message_body may be specified, to be appended to the request.
        """
        self._buffer.extend(("", ""))
        msg = "\r\n".join(self._buffer)
        del self._buffer[:]
        # If msg and message_body are sent in a single send() call,
        # it will avoid performance problems caused by the interaction
        # between delayed ack and the Nagle algorithm.
        if isinstance(message_body, str):
            msg += message_body
            message_body = None
        self.send(msg)
        if message_body is not None:
            # message_body was not a string (i.e. it is a file) and
            # we must run the risk of Nagle
            self.send(message_body, is_chunked=is_chunked)

########NEW FILE########
__FILENAME__ = io
# -*- coding: utf-8 -*-
import rpc
import conf
import random
import string
try:
    import zlib
    binascii = zlib
except ImportError:
    zlib = None
    import binascii


# @gist PutExtra
class PutExtra(object):
    params = {}
    mime_type = 'application/octet-stream'
    crc32 = ""
    check_crc = 0
# @endgist


def put(uptoken, key, data, extra=None):
    """ put your data to Qiniu

    If key is None, the server will generate one.
    data may be str or read()able object.
    """
    fields = {
    }

    if not extra:
        extra = PutExtra()

    if extra.params:
        for k in extra.params:
            fields[k] = str(extra.params[k])

    if extra.check_crc:
        fields["crc32"] = str(extra.crc32)

    if key is not None:
        fields['key'] = key

    fields["token"] = uptoken

    fname = key
    if fname is None:
        fname = _random_str(9)
    elif fname is '':
        fname = 'index.html'
    files = [
        {'filename': fname, 'data': data, 'mime_type': extra.mime_type},
    ]
    return rpc.Client(conf.UP_HOST).call_with_multipart("/", fields, files)


def put_file(uptoken, key, localfile, extra=None):
    """ put a file to Qiniu

    If key is None, the server will generate one.
    """
    if extra is not None and extra.check_crc == 1:
        extra.crc32 = _get_file_crc32(localfile)
    with open(localfile, 'rb') as f:
        return put(uptoken, key, f, extra)


_BLOCK_SIZE = 1024 * 1024 * 4


def _get_file_crc32(filepath):
    with open(filepath, 'rb') as f:
        block = f.read(_BLOCK_SIZE)
        crc = 0
        while len(block) != 0:
            crc = binascii.crc32(block, crc) & 0xFFFFFFFF
            block = f.read(_BLOCK_SIZE)
    return crc


def _random_str(length):
    lib = string.ascii_lowercase
    return ''.join([random.choice(lib) for i in range(0, length)])

########NEW FILE########
__FILENAME__ = resumable_io
# coding=utf-8
import os
try:
    import zlib
    binascii = zlib
except ImportError:
    zlib = None
    import binascii
from base64 import urlsafe_b64encode

from auth import up as auth_up
import conf

_workers = 1
_task_queue_size = _workers * 4
_try_times = 3
_block_bits = 22
_block_size = 1 << _block_bits
_block_mask = _block_size - 1
_chunk_size = _block_size  # 简化模式，弃用


class ResumableIoError(object):
    value = None

    def __init__(self, value):
        self.value = value
        return

    def __str__(self):
        return self.value


err_invalid_put_progress = ResumableIoError("invalid put progress")
err_put_failed = ResumableIoError("resumable put failed")
err_unmatched_checksum = ResumableIoError("unmatched checksum")
err_putExtra_type = ResumableIoError("extra must the instance of PutExtra")


def setup(chunk_size=0, try_times=0):
    global _chunk_size, _try_times
    _chunk_size = 1 << 22 if chunk_size <= 0 else chunk_size
    _try_times = 3 if try_times == 0 else try_times
    return


def gen_crc32(data):
    return binascii.crc32(data) & 0xffffffff


class PutExtra(object):
    params = None          # 自定义用户变量, key需要x: 开头
    mimetype = None        # 可选。在 uptoken 没有指定 DetectMime 时，用户客户端可自己指定 MimeType
    chunk_size = None      # 可选。每次上传的Chunk大小 简化模式，弃用
    try_times = None       # 可选。尝试次数
    progresses = None      # 可选。上传进度
    notify = lambda self, idx, size, ret: None  # 可选。进度提示
    notify_err = lambda self, idx, size, err: None

    def __init__(self, bucket=None):
        self.bucket = bucket
        return


def put_file(uptoken, key, localfile, extra):
    """ 上传文件 """
    f = open(localfile, "rb")
    statinfo = os.stat(localfile)
    ret = put(uptoken, key, f, statinfo.st_size, extra)
    f.close()
    return ret


def put(uptoken, key, f, fsize, extra):
    """ 上传二进制流, 通过将data "切片" 分段上传 """
    if not isinstance(extra, PutExtra):
        print("extra must the instance of PutExtra")
        return

    block_cnt = block_count(fsize)
    if extra.progresses is None:
        extra.progresses = [None] * block_cnt
    else:
        if not len(extra.progresses) == block_cnt:
            return None, err_invalid_put_progress

    if extra.try_times is None:
        extra.try_times = _try_times

    if extra.chunk_size is None:
        extra.chunk_size = _chunk_size

    for i in xrange(block_cnt):
        try_time = extra.try_times
        read_length = _block_size
        if (i + 1) * _block_size > fsize:
            read_length = fsize - i * _block_size
        data_slice = f.read(read_length)
        while True:
            err = resumable_block_put(data_slice, i, extra, uptoken)
            if err is None:
                break

            try_time -= 1
            if try_time <= 0:
                return None, err_put_failed
            print err, ".. retry"

    mkfile_client = auth_up.Client(uptoken, extra.progresses[-1]["host"])
    return mkfile(mkfile_client, key, fsize, extra)


def resumable_block_put(block, index, extra, uptoken):
    block_size = len(block)

    mkblk_client = auth_up.Client(uptoken, conf.UP_HOST)
    if extra.progresses[index] is None or "ctx" not in extra.progresses[index]:
        crc32 = gen_crc32(block)
        block = bytearray(block)
        extra.progresses[index], err = mkblock(mkblk_client, block_size, block)
        if err is not None:
            extra.notify_err(index, block_size, err)
            return err
        if not extra.progresses[index]["crc32"] == crc32:
            return err_unmatched_checksum
        extra.notify(index, block_size, extra.progresses[index])
        return


def block_count(size):
    global _block_size
    return (size + _block_mask) / _block_size


def mkblock(client, block_size, first_chunk):
    url = "http://%s/mkblk/%s" % (conf.UP_HOST, block_size)
    content_type = "application/octet-stream"
    return client.call_with(url, first_chunk, content_type, len(first_chunk))


def putblock(client, block_ret, chunk):
    url = "%s/bput/%s/%s" % (block_ret["host"],
                             block_ret["ctx"], block_ret["offset"])
    content_type = "application/octet-stream"
    return client.call_with(url, chunk, content_type, len(chunk))


def mkfile(client, key, fsize, extra):
    url = ["http://%s/mkfile/%s" % (conf.UP_HOST, fsize)]

    if extra.mimetype:
        url.append("mimeType/%s" % urlsafe_b64encode(extra.mimetype))

    if key is not None:
        url.append("key/%s" % urlsafe_b64encode(key))

    if extra.params:
        for k, v in extra.params.iteritems():
            url.append("%s/%s" % (k, urlsafe_b64encode(v)))

    url = "/".join(url)
    body = ",".join([i["ctx"] for i in extra.progresses])
    return client.call_with(url, body, "text/plain", len(body))

########NEW FILE########
__FILENAME__ = rpc
# -*- coding: utf-8 -*-
import httplib_chunk as httplib
import json
import cStringIO
import conf


class Client(object):
    _conn = None
    _header = None

    def __init__(self, host):
        self._conn = httplib.HTTPConnection(host)
        self._header = {}

    def round_tripper(self, method, path, body):
        self._conn.request(method, path, body, self._header)
        resp = self._conn.getresponse()
        return resp

    def call(self, path):
        return self.call_with(path, None)

    def call_with(self, path, body, content_type=None, content_length=None):
        ret = None

        self.set_header("User-Agent", conf.USER_AGENT)
        if content_type is not None:
            self.set_header("Content-Type", content_type)

        if content_length is not None:
            self.set_header("Content-Length", content_length)

        resp = self.round_tripper("POST", path, body)
        try:
            ret = resp.read()
            ret = json.loads(ret)
        except IOError, e:
            return None, e
        except ValueError:
            pass

        if resp.status / 100 != 2:
            err_msg = ret if "error" not in ret else ret["error"]
            reqid = resp.getheader("X-Reqid", None)
            # detail = resp.getheader("x-log", None)
            if reqid is not None:
                err_msg += ", reqid:%s" % reqid

            return None, err_msg

        return ret, None

    def call_with_multipart(self, path, fields=None, files=None):
        """
         *  fields => {key}
         *  files => [{filename, data, content_type}]
        """
        content_type, mr = self.encode_multipart_formdata(fields, files)
        return self.call_with(path, mr, content_type, mr.length())

    def call_with_form(self, path, ops):
        """
         * ops => {"key": value/list()}
        """

        body = []
        for i in ops:
            if isinstance(ops[i], (list, tuple)):
                data = ('&%s=' % i).join(ops[i])
            else:
                data = ops[i]

            body.append('%s=%s' % (i, data))
        body = '&'.join(body)

        content_type = "application/x-www-form-urlencoded"
        return self.call_with(path, body, content_type, len(body))

    def set_header(self, field, value):
        self._header[field] = value

    def set_headers(self, headers):
        self._header.update(headers)

    def encode_multipart_formdata(self, fields, files):
        """
         *  fields => {key}
         *  files => [{filename, data, content_type}]
         *  return content_type, content_length, body
        """
        if files is None:
            files = []
        if fields is None:
            fields = {}

        readers = []
        BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
        CRLF = '\r\n'
        L1 = []
        for key in fields:
            L1.append('--' + BOUNDARY)
            L1.append('Content-Disposition: form-data; name="%s"' % key)
            L1.append('')
            L1.append(fields[key])
        b1 = CRLF.join(L1)
        readers.append(b1)

        for file_info in files:
            L = []
            L.append('')
            L.append('--' + BOUNDARY)
            disposition = "Content-Disposition: form-data;"
            filename = _qiniu_escape(file_info.get('filename'))
            L.append('%s name="file"; filename="%s"' % (disposition, filename))
            L.append('Content-Type: %s' %
                     file_info.get('mime_type', 'application/octet-stream'))
            L.append('')
            L.append('')
            b2 = CRLF.join(L)
            readers.append(b2)

            data = file_info.get('data')
            readers.append(data)

        L3 = ['', '--' + BOUNDARY + '--', '']
        b3 = CRLF.join(L3)
        readers.append(b3)

        content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
        return content_type, MultiReader(readers)


def _qiniu_escape(s):
    edits = [('\\', '\\\\'), ('\"', '\\\"')]
    for (search, replace) in edits:
        s = s.replace(search, replace)
    return s


class MultiReader(object):

    """ class MultiReader([readers...])

    MultiReader returns a read()able object that's the logical concatenation of
    the provided input readers.  They're read sequentially.
    """

    def __init__(self, readers):
        self.readers = []
        self.content_length = 0
        self.valid_content_length = True
        for r in readers:
            if hasattr(r, 'read'):
                if self.valid_content_length:
                    length = self._get_content_length(r)
                    if length is not None:
                        self.content_length += length
                    else:
                        self.valid_content_length = False
            else:
                buf = r
                if not isinstance(buf, basestring):
                    buf = str(buf)
                buf = encode_unicode(buf)
                r = cStringIO.StringIO(buf)
                self.content_length += len(buf)
            self.readers.append(r)

    # don't name it __len__, because the length of MultiReader is not alway
    # valid.
    def length(self):
        return self.content_length if self.valid_content_length else None

    def _get_content_length(self, reader):
        data_len = None
        if hasattr(reader, 'seek') and hasattr(reader, 'tell'):
            try:
                reader.seek(0, 2)
                data_len = reader.tell()
                reader.seek(0, 0)
            except OSError:
                # Don't send a length if this failed
                data_len = None
        return data_len

    def read(self, n=-1):
        if n is None or n == -1:
            return ''.join([encode_unicode(r.read()) for r in self.readers])
        else:
            L = []
            while len(self.readers) > 0 and n > 0:
                b = self.readers[0].read(n)
                if len(b) == 0:
                    self.readers = self.readers[1:]
                else:
                    L.append(encode_unicode(b))
                    n -= len(b)
            return ''.join(L)


def encode_unicode(u):
    if isinstance(u, unicode):
        u = u.encode('utf8')
    return u

########NEW FILE########
__FILENAME__ = rs
# -*- coding: utf-8 -*-
from base64 import urlsafe_b64encode

from ..auth import digest
from .. import conf


class Client(object):
    conn = None

    def __init__(self, mac=None):
        if mac is None:
            mac = digest.Mac()
        self.conn = digest.Client(host=conf.RS_HOST, mac=mac)

    def stat(self, bucket, key):
        return self.conn.call(uri_stat(bucket, key))

    def delete(self, bucket, key):
        return self.conn.call(uri_delete(bucket, key))

    def move(self, bucket_src, key_src, bucket_dest, key_dest):
        return self.conn.call(uri_move(bucket_src, key_src, bucket_dest, key_dest))

    def copy(self, bucket_src, key_src, bucket_dest, key_dest):
        return self.conn.call(uri_copy(bucket_src, key_src, bucket_dest, key_dest))

    def batch(self, ops):
        return self.conn.call_with_form("/batch", dict(op=ops))

    def batch_stat(self, entries):
        ops = []
        for entry in entries:
            ops.append(uri_stat(entry.bucket, entry.key))
        return self.batch(ops)

    def batch_delete(self, entries):
        ops = []
        for entry in entries:
            ops.append(uri_delete(entry.bucket, entry.key))
        return self.batch(ops)

    def batch_move(self, entries):
        ops = []
        for entry in entries:
            ops.append(uri_move(entry.src.bucket, entry.src.key,
                                entry.dest.bucket, entry.dest.key))
        return self.batch(ops)

    def batch_copy(self, entries):
        ops = []
        for entry in entries:
            ops.append(uri_copy(entry.src.bucket, entry.src.key,
                                entry.dest.bucket, entry.dest.key))
        return self.batch(ops)


class EntryPath(object):
    bucket = None
    key = None

    def __init__(self, bucket, key):
        self.bucket = bucket
        self.key = key


class EntryPathPair:
    src = None
    dest = None

    def __init__(self, src, dest):
        self.src = src
        self.dest = dest


def uri_stat(bucket, key):
    return "/stat/%s" % urlsafe_b64encode("%s:%s" % (bucket, key))


def uri_delete(bucket, key):
    return "/delete/%s" % urlsafe_b64encode("%s:%s" % (bucket, key))


def uri_move(bucket_src, key_src, bucket_dest, key_dest):
    src = urlsafe_b64encode("%s:%s" % (bucket_src, key_src))
    dest = urlsafe_b64encode("%s:%s" % (bucket_dest, key_dest))
    return "/move/%s/%s" % (src, dest)


def uri_copy(bucket_src, key_src, bucket_dest, key_dest):
    src = urlsafe_b64encode("%s:%s" % (bucket_src, key_src))
    dest = urlsafe_b64encode("%s:%s" % (bucket_dest, key_dest))
    return "/copy/%s/%s" % (src, dest)

########NEW FILE########
__FILENAME__ = rs_token
# -*- coding: utf-8 -*-
import json
import time
import urllib

from ..auth import digest
from ..import rpc

# @gist PutPolicy


class PutPolicy(object):
    scope = None             # 可以是 bucketName 或者 bucketName:key
    expires = 3600           # 默认是 3600 秒
    callbackUrl = None
    callbackBody = None
    returnUrl = None
    returnBody = None
    endUser = None
    asyncOps = None

    saveKey = None
    insertOnly = None
    detectMime = None
    mimeLimit = None
    fsizeLimit = None
    persistentNotifyUrl = None
    persistentOps = None

    def __init__(self, scope):
        self.scope = scope
# @endgist

    def token(self, mac=None):
        if mac is None:
            mac = digest.Mac()
        token = dict(
            scope=self.scope,
            deadline=int(time.time()) + self.expires,
        )

        if self.callbackUrl is not None:
            token["callbackUrl"] = self.callbackUrl

        if self.callbackBody is not None:
            token["callbackBody"] = self.callbackBody

        if self.returnUrl is not None:
            token["returnUrl"] = self.returnUrl

        if self.returnBody is not None:
            token["returnBody"] = self.returnBody

        if self.endUser is not None:
            token["endUser"] = self.endUser

        if self.asyncOps is not None:
            token["asyncOps"] = self.asyncOps

        if self.saveKey is not None:
            token["saveKey"] = self.saveKey

        if self.insertOnly is not None:
            token["exclusive"] = self.insertOnly

        if self.detectMime is not None:
            token["detectMime"] = self.detectMime

        if self.mimeLimit is not None:
            token["mimeLimit"] = self.mimeLimit

        if self.fsizeLimit is not None:
            token["fsizeLimit"] = self.fsizeLimit

        if self.persistentOps is not None:
            token["persistentOps"] = self.persistentOps

        if self.persistentNotifyUrl is not None:
            token["persistentNotifyUrl"] = self.persistentNotifyUrl

        b = json.dumps(token, separators=(',', ':'))
        return mac.sign_with_data(b)


class GetPolicy(object):
    expires = 3600

    def __init__(self, expires=3600):
        self.expires = expires

    def make_request(self, base_url, mac=None):
        '''
         *  return private_url
        '''
        if mac is None:
            mac = digest.Mac()

        deadline = int(time.time()) + self.expires
        if '?' in base_url:
            base_url += '&'
        else:
            base_url += '?'
        base_url = '%se=%s' % (base_url, str(deadline))

        token = mac.sign(base_url)
        return '%s&token=%s' % (base_url, token)


def make_base_url(domain, key):
    '''
     * domain => str
     * key => str
     * return base_url
    '''
    key = rpc.encode_unicode(key)
    return 'http://%s/%s' % (domain, urllib.quote(key))

########NEW FILE########
__FILENAME__ = rs_test
# -*- coding: utf-8 -*-
import unittest
import os
import random
import string

from qiniu import rs
from qiniu import conf


def r(length):
    lib = string.ascii_uppercase
    return ''.join([random.choice(lib) for i in range(0, length)])

conf.ACCESS_KEY = os.getenv("QINIU_ACCESS_KEY")
conf.SECRET_KEY = os.getenv("QINIU_SECRET_KEY")
key = 'QINIU_UNIT_TEST_PIC'
bucket_name = os.getenv("QINIU_TEST_BUCKET")
noexist_key = 'QINIU_UNIT_TEST_NOEXIST' + r(30)
key2 = "rs_demo_test_key_1_" + r(5)
key3 = "rs_demo_test_key_2_" + r(5)
key4 = "rs_demo_test_key_3_" + r(5)


class TestRs(unittest.TestCase):

    def test_stat(self):
        r = rs.Client()
        ret, err = r.stat(bucket_name, key)
        assert err is None
        assert ret is not None

        # error
        _, err = r.stat(bucket_name, noexist_key)
        assert err is not None

    def test_delete_move_copy(self):
        r = rs.Client()
        r.delete(bucket_name, key2)
        r.delete(bucket_name, key3)

        ret, err = r.copy(bucket_name, key, bucket_name, key2)
        assert err is None, err

        ret, err = r.move(bucket_name, key2, bucket_name, key3)
        assert err is None, err

        ret, err = r.delete(bucket_name, key3)
        assert err is None, err

        # error
        _, err = r.delete(bucket_name, key2)
        assert err is not None

        _, err = r.delete(bucket_name, key3)
        assert err is not None

    def test_batch_stat(self):
        r = rs.Client()
        entries = [
            rs.EntryPath(bucket_name, key),
            rs.EntryPath(bucket_name, key2),
        ]
        ret, err = r.batch_stat(entries)
        assert err is None
        self.assertEqual(ret[0]["code"], 200)
        self.assertEqual(ret[1]["code"], 612)

    def test_batch_delete_move_copy(self):
        r = rs.Client()
        e1 = rs.EntryPath(bucket_name, key)
        e2 = rs.EntryPath(bucket_name, key2)
        e3 = rs.EntryPath(bucket_name, key3)
        e4 = rs.EntryPath(bucket_name, key4)
        r.batch_delete([e2, e3, e4])

        # copy
        entries = [
            rs.EntryPathPair(e1, e2),
            rs.EntryPathPair(e1, e3),
        ]
        ret, err = r.batch_copy(entries)
        assert err is None
        self.assertEqual(ret[0]["code"], 200)
        self.assertEqual(ret[1]["code"], 200)

        ret, err = r.batch_move([rs.EntryPathPair(e2, e4)])
        assert err is None
        self.assertEqual(ret[0]["code"], 200)

        ret, err = r.batch_delete([e3, e4])
        assert err is None
        self.assertEqual(ret[0]["code"], 200)

        r.batch_delete([e2, e3, e4])

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = rs_token_test
# -*- coding: utf-8 -*-
import unittest
import os
import json
from base64 import urlsafe_b64decode as decode
from base64 import urlsafe_b64encode as encode
from hashlib import sha1
import hmac
import urllib

from qiniu import conf
from qiniu import rs

conf.ACCESS_KEY = os.getenv("QINIU_ACCESS_KEY")
conf.SECRET_KEY = os.getenv("QINIU_SECRET_KEY")
bucket_name = os.getenv("QINIU_TEST_BUCKET")
domain = os.getenv("QINIU_TEST_DOMAIN")
key = 'QINIU_UNIT_TEST_PIC'


class TestToken(unittest.TestCase):

    def test_put_policy(self):
        policy = rs.PutPolicy(bucket_name)
        policy.endUser = "hello!"
        policy.returnUrl = "http://localhost:1234/path?query=hello"
        policy.returnBody = "$(sha1)"
        # Do not specify the returnUrl and callbackUrl at the same time
        policy.callbackUrl = "http://1.2.3.4/callback"
        policy.callbackBody = "$(bucket)"

        policy.saveKey = "$(sha1)"
        policy.insertOnly = 1
        policy.detectMime = 1
        policy.fsizeLimit = 1024
        policy.persistentNotifyUrl = "http://4.3.2.1/persistentNotifyUrl"
        policy.persistentOps = "avthumb/flash"

        tokens = policy.token().split(':')

        # chcek first part of token
        self.assertEqual(conf.ACCESS_KEY, tokens[0])
        data = json.loads(decode(tokens[2]))

        # check if same
        self.assertEqual(data["scope"], bucket_name)
        self.assertEqual(data["endUser"], policy.endUser)
        self.assertEqual(data["returnUrl"], policy.returnUrl)
        self.assertEqual(data["returnBody"], policy.returnBody)
        self.assertEqual(data["callbackUrl"], policy.callbackUrl)
        self.assertEqual(data["callbackBody"], policy.callbackBody)
        self.assertEqual(data["saveKey"], policy.saveKey)
        self.assertEqual(data["exclusive"], policy.insertOnly)
        self.assertEqual(data["detectMime"], policy.detectMime)
        self.assertEqual(data["fsizeLimit"], policy.fsizeLimit)
        self.assertEqual(
            data["persistentNotifyUrl"], policy.persistentNotifyUrl)
        self.assertEqual(data["persistentOps"], policy.persistentOps)

        new_hmac = encode(hmac.new(conf.SECRET_KEY, tokens[2], sha1).digest())
        self.assertEqual(new_hmac, tokens[1])

    def test_get_policy(self):
        base_url = rs.make_base_url(domain, key)
        policy = rs.GetPolicy()
        private_url = policy.make_request(base_url)

        f = urllib.urlopen(private_url)
        body = f.read()
        f.close()
        self.assertEqual(len(body) > 100, True)


class Test_make_base_url(unittest.TestCase):

    def test_unicode(self):
        url1 = rs.make_base_url('1.com', '你好')
        url2 = rs.make_base_url('1.com', u'你好')
        assert url1 == url2

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = rsf
# -*- coding: utf-8 -*-
import auth.digest
import conf
import urllib

EOF = 'EOF'


class Client(object):
    conn = None

    def __init__(self, mac=None):
        if mac is None:
            mac = auth.digest.Mac()
        self.conn = auth.digest.Client(host=conf.RSF_HOST, mac=mac)

    def list_prefix(self, bucket, prefix=None, marker=None, limit=None):
        '''前缀查询:
         * bucket => str
         * prefix => str
         * marker => str
         * limit => int
         * return ret => {'items': items, 'marker': markerOut}, err => str

        1. 首次请求 marker = None
        2. 无论 err 值如何，均应该先看 ret.get('items') 是否有内容
        3. 如果后续没有更多数据，err 返回 EOF，markerOut 返回 None（但不通过该特征来判断是否结束）
        '''
        ops = {
            'bucket': bucket,
        }
        if marker is not None:
            ops['marker'] = marker
        if limit is not None:
            ops['limit'] = limit
        if prefix is not None:
            ops['prefix'] = prefix
        url = '%s?%s' % ('/list', urllib.urlencode(ops))
        ret, err = self.conn.call_with(
            url, body=None, content_type='application/x-www-form-urlencoded')
        if ret and not ret.get('marker'):
            err = EOF
        return ret, err

########NEW FILE########
__FILENAME__ = conf_test
# -*- coding: utf-8 -*-
import unittest
from qiniu import conf


class TestConfig(unittest.TestCase):

    def test_USER_AGENT(self):
        assert len(conf.USER_AGENT) >= len('qiniu python-sdk')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = fop_test
# -*- coding:utf-8 -*-
import unittest
from qiniu import fop

pic = "http://cheneya.qiniudn.com/hello_jpg"


class TestFop(unittest.TestCase):

    def test_exif(self):
        ie = fop.Exif()
        ret = ie.make_request(pic)
        self.assertEqual(ret, "%s?exif" % pic)

    def test_imageView(self):
        iv = fop.ImageView()
        iv.height = 100
        ret = iv.make_request(pic)
        self.assertEqual(ret, "%s?imageView/1/h/100" % pic)

        iv.quality = 20
        iv.format = "png"
        ret = iv.make_request(pic)
        self.assertEqual(ret, "%s?imageView/1/h/100/q/20/format/png" % pic)

    def test_imageInfo(self):
        ii = fop.ImageInfo()
        ret = ii.make_request(pic)
        self.assertEqual(ret, "%s?imageInfo" % pic)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = io_test
# -*- coding: utf-8 -*-
import os
import unittest
import string
import random
import urllib
try:
    import zlib
    binascii = zlib
except ImportError:
    zlib = None
    import binascii
import cStringIO

from qiniu import conf
from qiniu import rs
from qiniu import io

conf.ACCESS_KEY = os.getenv("QINIU_ACCESS_KEY")
conf.SECRET_KEY = os.getenv("QINIU_SECRET_KEY")
bucket_name = os.getenv("QINIU_TEST_BUCKET")

policy = rs.PutPolicy(bucket_name)
extra = io.PutExtra()
extra.mime_type = "text/plain"
extra.params = {'x:a': 'a'}


def r(length):
    lib = string.ascii_uppercase
    return ''.join([random.choice(lib) for i in range(0, length)])


class TestUp(unittest.TestCase):

    def test(self):
        def test_put():
            key = "test_%s" % r(9)
            # params = "op=3"
            data = "hello bubby!"
            extra.check_crc = 2
            extra.crc32 = binascii.crc32(data) & 0xFFFFFFFF
            ret, err = io.put(policy.token(), key, data, extra)
            assert err is None
            assert ret['key'] == key

        def test_put_same_crc():
            key = "test_%s" % r(9)
            data = "hello bubby!"
            extra.check_crc = 2
            ret, err = io.put(policy.token(), key, data, extra)
            assert err is None
            assert ret['key'] == key

        def test_put_no_key():
            data = r(100)
            extra.check_crc = 0
            ret, err = io.put(policy.token(), key=None, data=data, extra=extra)
            assert err is None
            assert ret['hash'] == ret['key']

        def test_put_quote_key():
            data = r(100)
            key = 'a\\b\\c"你好' + r(9)
            ret, err = io.put(policy.token(), key, data)
            print err
            assert err is None
            assert ret['key'].encode('utf8') == key

            data = r(100)
            key = u'a\\b\\c"你好' + r(9)
            ret, err = io.put(policy.token(), key, data)
            assert err is None
            assert ret['key'] == key

        def test_put_unicode1():
            key = "test_%s" % r(9) + '你好'
            data = key
            ret, err = io.put(policy.token(), key, data, extra)
            assert err is None
            assert ret[u'key'].endswith(u'你好')

        def test_put_unicode2():
            key = "test_%s" % r(9) + '你好'
            data = key
            data = data.decode('utf8')
            ret, err = io.put(policy.token(), key, data)
            assert err is None
            assert ret[u'key'].endswith(u'你好')

        def test_put_unicode3():
            key = "test_%s" % r(9) + '你好'
            data = key
            key = key.decode('utf8')
            ret, err = io.put(policy.token(), key, data)
            assert err is None
            assert ret[u'key'].endswith(u'你好')

        def test_put_unicode4():
            key = "test_%s" % r(9) + '你好'
            data = key
            key = key.decode('utf8')
            data = data.decode('utf8')
            ret, err = io.put(policy.token(), key, data)
            assert err is None
            assert ret[u'key'].endswith(u'你好')

        def test_put_StringIO():
            key = "test_%s" % r(9)
            data = cStringIO.StringIO('hello buddy!')
            ret, err = io.put(policy.token(), key, data)
            assert err is None
            assert ret['key'] == key

        def test_put_urlopen():
            key = "test_%s" % r(9)
            data = urllib.urlopen('http://cheneya.qiniudn.com/hello_jpg')
            ret, err = io.put(policy.token(), key, data)
            assert err is None
            assert ret['key'] == key

        def test_put_no_length():
            class test_reader(object):

                def __init__(self):
                    self.data = 'abc'
                    self.pos = 0

                def read(self, n=None):
                    if n is None or n < 0:
                        newpos = len(self.data)
                    else:
                        newpos = min(self.pos + n, len(self.data))
                    r = self.data[self.pos: newpos]
                    self.pos = newpos
                    return r
            key = "test_%s" % r(9)
            data = test_reader()

            extra.check_crc = 2
            extra.crc32 = binascii.crc32('abc') & 0xFFFFFFFF
            ret, err = io.put(policy.token(), key, data, extra)
            assert err is None
            assert ret['key'] == key

        test_put()
        test_put_same_crc()
        test_put_no_key()
        test_put_quote_key()
        test_put_unicode1()
        test_put_unicode2()
        test_put_unicode3()
        test_put_unicode4()
        test_put_StringIO()
        test_put_urlopen()
        test_put_no_length()

    def test_put_file(self):
        localfile = "%s" % __file__
        key = "test_%s" % r(9)

        extra.check_crc = 1
        ret, err = io.put_file(policy.token(), key, localfile, extra)
        assert err is None
        assert ret['key'] == key

    def test_put_crc_fail(self):
        key = "test_%s" % r(9)
        data = "hello bubby!"
        extra.check_crc = 2
        extra.crc32 = "wrong crc32"
        ret, err = io.put(policy.token(), key, data, extra)
        assert err is not None

    def test_put_fail_reqid(self):
        key = "test_%s" % r(9)
        data = "hello bubby!"
        ret, err = io.put("", key, data, extra)
        assert "reqid" in err


class Test_get_file_crc32(unittest.TestCase):

    def test_get_file_crc32(self):
        file_path = '%s' % __file__

        data = None
        with open(file_path, 'rb') as f:
            data = f.read()
        io._BLOCK_SIZE = 4
        assert binascii.crc32(
            data) & 0xFFFFFFFF == io._get_file_crc32(file_path)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = resumable_io_test
# -*- coding: utf-8 -*-
import os
import unittest
import string
import random
import platform
try:
    import zlib
    binascii = zlib
except ImportError:
    zlib = None
    import binascii
import urllib
import shutil

from qiniu import conf
from qiniu.auth import up
from qiniu import resumable_io
from qiniu import rs

bucket = os.getenv("QINIU_TEST_BUCKET")
conf.ACCESS_KEY = os.getenv("QINIU_ACCESS_KEY")
conf.SECRET_KEY = os.getenv("QINIU_SECRET_KEY")
test_env = os.getenv("QINIU_TEST_ENV")
is_travis = test_env == "travis"


def r(length):
    lib = string.ascii_uppercase
    return ''.join([random.choice(lib) for _ in range(0, length)])


class TestBlock(unittest.TestCase):

    def test_block(self):
        if is_travis:
            return
        policy = rs.PutPolicy(bucket)
        uptoken = policy.token()
        client = up.Client(uptoken)

        # rets = [0, 0]
        data_slice_2 = "\nbye!"
        ret, err = resumable_io.mkblock(
            client, len(data_slice_2), data_slice_2)
        assert err is None, err
        self.assertEqual(ret["crc32"], binascii.crc32(data_slice_2))

        extra = resumable_io.PutExtra(bucket)
        extra.mimetype = "text/plain"
        extra.progresses = [ret]
        lens = 0
        for i in xrange(0, len(extra.progresses)):
            lens += extra.progresses[i]["offset"]

        key = u"sdk_py_resumable_block_4_%s" % r(9)
        ret, err = resumable_io.mkfile(client, key, lens, extra)
        assert err is None, err
        self.assertEqual(
            ret["hash"], "FtCFo0mQugW98uaPYgr54Vb1QsO0", "hash not match")
        rs.Client().delete(bucket, key)

    def test_put(self):
        if is_travis:
            return
        src = urllib.urlopen("http://cheneya.qiniudn.com/hello_jpg")
        ostype = platform.system()
        if ostype.lower().find("windows") != -1:
            tmpf = "".join([os.getcwd(), os.tmpnam()])
        else:
            tmpf = os.tmpnam()
        dst = open(tmpf, 'wb')
        shutil.copyfileobj(src, dst)
        src.close()

        policy = rs.PutPolicy(bucket)
        extra = resumable_io.PutExtra(bucket)
        extra.bucket = bucket
        extra.params = {"x:foo": "test"}
        key = "sdk_py_resumable_block_5_%s" % r(9)
        localfile = dst.name
        ret, err = resumable_io.put_file(policy.token(), key, localfile, extra)
        assert ret.get("x:foo") == "test", "return data not contains 'x:foo'"
        dst.close()
        os.remove(tmpf)

        assert err is None, err
        self.assertEqual(
            ret["hash"], "FnyTMUqPNRTdk1Wou7oLqDHkBm_p", "hash not match")
        rs.Client().delete(bucket, key)

    def test_put_4m(self):
        if is_travis:
            return
        ostype = platform.system()
        if ostype.lower().find("windows") != -1:
            tmpf = "".join([os.getcwd(), os.tmpnam()])
        else:
            tmpf = os.tmpnam()
        dst = open(tmpf, 'wb')
        dst.write("abcd" * 1024 * 1024)
        dst.flush()

        policy = rs.PutPolicy(bucket)
        extra = resumable_io.PutExtra(bucket)
        extra.bucket = bucket
        extra.params = {"x:foo": "test"}
        key = "sdk_py_resumable_block_6_%s" % r(9)
        localfile = dst.name
        ret, err = resumable_io.put_file(policy.token(), key, localfile, extra)
        assert ret.get("x:foo") == "test", "return data not contains 'x:foo'"
        dst.close()
        os.remove(tmpf)

        assert err is None, err
        self.assertEqual(
            ret["hash"], "FnIVmMd_oaUV3MLDM6F9in4RMz2U", "hash not match")
        rs.Client().delete(bucket, key)


if __name__ == "__main__":
    if not is_travis:
        unittest.main()

########NEW FILE########
__FILENAME__ = rpc_test
# -*- coding: utf-8 -*-
import StringIO
import unittest

from qiniu import rpc
from qiniu import conf


def round_tripper(client, method, path, body):
    pass


class ClsTestClient(rpc.Client):

    def round_tripper(self, method, path, body):
        round_tripper(self, method, path, body)
        return super(ClsTestClient, self).round_tripper(method, path, body)

client = ClsTestClient(conf.RS_HOST)


class TestClient(unittest.TestCase):

    def test_call(self):
        global round_tripper

        def tripper(client, method, path, body):
            self.assertEqual(path, "/hello")
            assert body is None

        round_tripper = tripper
        client.call("/hello")

    def test_call_with(self):
        global round_tripper

        def tripper(client, method, path, body):
            self.assertEqual(body, "body")

        round_tripper = tripper
        client.call_with("/hello", "body")

    def test_call_with_multipart(self):
        global round_tripper

        def tripper(client, method, path, body):
            target_type = "multipart/form-data"
            self.assertTrue(
                client._header["Content-Type"].startswith(target_type))
            start_index = client._header["Content-Type"].find("boundary")
            boundary = client._header["Content-Type"][start_index + 9:]
            dispostion = 'Content-Disposition: form-data; name="auth"'
            tpl = "--%s\r\n%s\r\n\r\n%s\r\n--%s--\r\n" % (boundary, dispostion,
                                                          "auth_string", boundary)
            self.assertEqual(len(tpl), client._header["Content-Length"])
            self.assertEqual(len(tpl), body.length())

        round_tripper = tripper
        client.call_with_multipart("/hello", fields={"auth": "auth_string"})

    def test_call_with_form(self):
        global round_tripper

        def tripper(client, method, path, body):
            self.assertEqual(body, "action=a&op=a&op=b")
            target_type = "application/x-www-form-urlencoded"
            self.assertEqual(client._header["Content-Type"], target_type)
            self.assertEqual(client._header["Content-Length"], len(body))

        round_tripper = tripper
        client.call_with_form("/hello", dict(op=["a", "b"], action="a"))


class TestMultiReader(unittest.TestCase):

    def test_multi_reader1(self):
        a = StringIO.StringIO('你好')
        b = StringIO.StringIO('abcdefg')
        c = StringIO.StringIO(u'悲剧')
        mr = rpc.MultiReader([a, b, c])
        data = mr.read()
        assert data.index('悲剧') > data.index('abcdefg')

    def test_multi_reader2(self):
        a = StringIO.StringIO('你好')
        b = StringIO.StringIO('abcdefg')
        c = StringIO.StringIO(u'悲剧')
        mr = rpc.MultiReader([a, b, c])
        data = mr.read(8)
        assert len(data) is 8


def encode_multipart_formdata2(fields, files):
    if files is None:
        files = []
    if fields is None:
        fields = []

    BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
    CRLF = '\r\n'
    L = []
    for (key, value) in fields:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"' % key)
        L.append('')
        L.append(value)
    for (key, filename, value) in files:
        L.append('--' + BOUNDARY)
        disposition = "Content-Disposition: form-data;"
        L.append('%s name="%s"; filename="%s"' % (disposition, key, filename))
        L.append('Content-Type: application/octet-stream')
        L.append('')
        L.append(value)
    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body


class TestEncodeMultipartFormdata(unittest.TestCase):

    def test_encode(self):
        fields = {'a': '1', 'b': '2'}
        files = [
            {
                'filename': 'key1',
                'data': 'data1',
                        'mime_type': 'application/octet-stream',
            },
            {
                'filename': 'key2',
                'data': 'data2',
                        'mime_type': 'application/octet-stream',
            }
        ]
        content_type, mr = rpc.Client(
            'localhost').encode_multipart_formdata(fields, files)
        t, b = encode_multipart_formdata2(
            [('a', '1'), ('b', '2')],
            [('file', 'key1', 'data1'), ('file', 'key2', 'data2')]
        )
        assert t == content_type
        assert len(b) == mr.length()

    def test_unicode(self):
        def test1():
            files = [{'filename': '你好', 'data': '你好', 'mime_type': ''}]
            _, body = rpc.Client(
                'localhost').encode_multipart_formdata(None, files)
            return len(body.read())

        def test2():
            files = [{'filename': u'你好', 'data': '你好', 'mime_type': ''}]
            _, body = rpc.Client(
                'localhost').encode_multipart_formdata(None, files)
            return len(body.read())

        def test3():
            files = [{'filename': '你好', 'data': u'你好', 'mime_type': ''}]
            _, body = rpc.Client(
                'localhost').encode_multipart_formdata(None, files)
            return len(body.read())

        def test4():
            files = [{'filename': u'你好', 'data': u'你好', 'mime_type': ''}]
            _, body = rpc.Client(
                'localhost').encode_multipart_formdata(None, files)
            return len(body.read())

        assert test1() == test2()
        assert test2() == test3()
        assert test3() == test4()


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = rsf_test
# -*- coding: utf-8 -*-
import unittest
from qiniu import rsf
from qiniu import conf

import os
conf.ACCESS_KEY = os.getenv("QINIU_ACCESS_KEY")
conf.SECRET_KEY = os.getenv("QINIU_SECRET_KEY")
bucket_name = os.getenv("QINIU_TEST_BUCKET")


class TestRsf(unittest.TestCase):

    def test_list_prefix(self):
        c = rsf.Client()
        ret, err = c.list_prefix(bucket_name, limit=4)
        self.assertEqual(err is rsf.EOF or err is None, True)
        assert len(ret.get('items')) == 4


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
