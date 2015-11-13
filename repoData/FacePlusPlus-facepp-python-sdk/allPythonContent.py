__FILENAME__ = cmdtool
#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# $File: cmdtool.py
# $Date: Sat Apr 06 15:42:43 2013 +0800
# $Author: jiakai@megvii.com
#
# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# http://sam.zoy.org/wtfpl/COPYING (copied as below) for more details.
#
#                DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE 
#                        Version 2, December 2004 
#
#     Copyright (C) 2004 Sam Hocevar <sam@hocevar.net> 
#
#     Everyone is permitted to copy and distribute verbatim or modified 
#     copies of this license document, and changing it is allowed as long 
#     as the name is changed. 
#
#                DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE 
#       TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION 
#
#      0. You just DO WHAT THE FUCK YOU WANT TO. 

def init():
    import sys
    import os
    import os.path
    if sys.version_info.major != 2:
        sys.exit('Python 2 is required to run this program')

    fdir = None
    if hasattr(sys, "frozen") and \
            sys.frozen in ("windows_exe", "console_exe"):
        fdir = os.path.dirname(os.path.abspath(sys.executable))
        sys.path.append(fdir)
        fdir = os.path.join(fdir, '..')
    else:
        fdir = os.path.dirname(__file__)

    with open(os.path.join(fdir, 'apikey.cfg')) as f:
        exec(f.read())

    srv = locals().get('SERVER')
    from facepp import API
    return API(API_KEY, API_SECRET, srv = srv)

api = init()

from facepp import API, File

del init

def _run():
    global _run
    _run = lambda: None

    msg = """
===================================================
Welcome to Face++ Interactive Shell!
Here, you can explore and play with Face++ APIs :)
---------------------------------------------------
Getting Started:
    0. Register a user and API key on http://www.faceplusplus.com
    1. Write your API key/secret in apikey.cfg
    2. Start this interactive shell and try various APIs
        For example, to find all faces in a local image file, just type:
            api.detection.detect(img = File(r'<path to the image file>'))

Enjoy!
"""

    try:
        from IPython import embed
        embed(banner2 = msg)
    except ImportError:
        import code
        code.interact(msg, local = globals())


if __name__ == '__main__':
    _run()

########NEW FILE########
__FILENAME__ = cmdtool
../../../cmdtool.py
########NEW FILE########
__FILENAME__ = facepp
../../../facepp.py
########NEW FILE########
__FILENAME__ = facepp
# -*- coding: utf-8 -*-
# $File: facepp.py
# $Date: Thu May 16 14:59:36 2013 +0800
# $Author: jiakai@megvii.com
#
# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# http://sam.zoy.org/wtfpl/COPYING (copied as below) for more details.
#
#                DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE 
#                        Version 2, December 2004 
#
#     Copyright (C) 2004 Sam Hocevar <sam@hocevar.net> 
#
#     Everyone is permitted to copy and distribute verbatim or modified 
#     copies of this license document, and changing it is allowed as long 
#     as the name is changed. 
#
#                DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE 
#       TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION 
#
#      0. You just DO WHAT THE FUCK YOU WANT TO. 

"""a simple facepp sdk
example:
api = API(key, secret)
api.detection.detect(img = File('/tmp/test.jpg'))"""

__all__ = ['File', 'APIError', 'API']


DEBUG_LEVEL = 1

import sys
import socket
import urllib
import urllib2
import json
import os
import os.path
import itertools
import mimetools
import mimetypes
import time
import tempfile
from collections import Iterable
from cStringIO import StringIO

class File(object):
    """an object representing a local file"""
    path = None
    content = None
    def __init__(self, path):
        self.path = path
        self._get_content()

    def _resize_cv2(self, ftmp):
        try:
            import cv2
        except ImportError:
            return False
        img = cv2.imread(self.path)
        assert img is not None and img.size != 0, 'Invalid image'
        bigdim = max(img.shape[0], img.shape[1])
        downscale = max(1., bigdim / 600.)
        img = cv2.resize(img,
                (int(img.shape[1] / downscale),
                    int(img.shape[0] / downscale)))
        cv2.imwrite(ftmp, img)
        return True

    def _resize_PIL(self, ftmp):
        try:
            import PIL.Image
        except ImportError:
            return False

        img = PIL.Image.open(self.path)
        bigdim = max(img.size[0], img.size[1])
        downscale = max(1., bigdim / 600.)
        img = img.resize(
                (int(img.size[0] / downscale), int(img.size[1] / downscale)))
        img.save(ftmp)
        return True

    def _get_content(self):
        """read image content; resize the image if necessary"""

        if os.path.getsize(self.path) > 2 * 1024 * 1024:
            ftmp = tempfile.NamedTemporaryFile(
                    suffix = '.jpg', delete = False).name
            try:
                if not (self._resize_cv2(ftmp) or self._resize_PIL(ftmp)):
                    raise APIError(-1, None, 'image file size too large')
                with open(ftmp, 'rb') as f:
                    self.content = f.read()
            finally:
                os.unlink(ftmp)
        else:
            with open(self.path, 'rb') as f:
                self.content = f.read()

    def get_filename(self):
        return os.path.basename(self.path)


class APIError(Exception):
    code = None
    """HTTP status code"""

    url = None
    """request URL"""

    body = None
    """server response body; or detailed error information"""

    def __init__(self, code, url, body):
        self.code = code
        self.url = url
        self.body = body

    def __str__(self):
        return 'code={s.code}\nurl={s.url}\n{s.body}'.format(s = self)

    __repr__ = __str__


class API(object):
    key = None
    secret = None
    server = 'http://api.faceplusplus.com/'

    decode_result = True
    timeout = None
    max_retries = None
    retry_delay = None

    def __init__(self, key, secret, srv = None,
            decode_result = True, timeout = 30, max_retries = 10,
            retry_delay = 5):
        """:param srv: The API server address
        :param decode_result: whether to json_decode the result
        :param timeout: HTTP request timeout in seconds
        :param max_retries: maximal number of retries after catching URL error
            or socket error
        :param retry_delay: time to sleep before retrying"""
        self.key = key
        self.secret = secret
        if srv:
            self.server = srv
        self.decode_result = decode_result
        assert timeout >= 0 or timeout is None
        assert max_retries >= 0
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        _setup_apiobj(self, self, [])

    def wait_async(self, session_id, referesh_interval = 2):
        """wait for asynchronous operations to complete"""
        while True:
            rst = self.info.get_session(session_id = session_id)
            if rst['status'] != u'INQUEUE':
                return rst
            _print_debug(rst)
            time.sleep(referesh_interval)

    def update_request(self, request):
        """overwrite this function to update the request before sending it to
        server"""
        pass


def _setup_apiobj(self, api, path):
    if self is not api:
        self._api = api
        self._urlbase = api.server + '/'.join(path)

    lvl = len(path)
    done = set()
    for i in _APIS:
        if len(i) <= lvl:
            continue
        cur = i[lvl]
        if i[:lvl] == path and cur not in done:
            done.add(cur)
            setattr(self, cur, _APIProxy(api, i[:lvl + 1]))

class _APIProxy(object):
    _api = None
    """underlying :class:`API` object"""

    _urlbase = None

    def __init__(self, api, path):
        _setup_apiobj(self, api, path)

    def __call__(self, post = False, *args, **kargs):
        if len(args):
            raise TypeError('Only keyword arguments are allowed')
        if type(post) is not bool:
            raise TypeError('post argument can only be True or False')
        form = _MultiPartForm()
        add_form = False
        for (k, v) in kargs.iteritems():
            if isinstance(v, File):
                add_form = True
                form.add_file(k, v.get_filename(), v.content)

        if post:
            url = self._urlbase
            for k, v in self._mkarg(kargs).iteritems():
                form.add_field(k, v)
            add_form = True
        else:
            url = self.geturl(**kargs)

        request = urllib2.Request(url)
        if add_form:
            body = str(form)
            request.add_header('Content-type', form.get_content_type())
            request.add_header('Content-length', str(len(body)))
            request.add_data(body)

        self._api.update_request(request)

        retry = self._api.max_retries
        while True:
            retry -= 1
            try:
                ret = urllib2.urlopen(request, timeout = self._api.timeout).read()
                break
            except urllib2.HTTPError as e:
                raise APIError(e.code, url, e.read())
            except (socket.error, urllib2.URLError) as e:
                if retry < 0:
                    raise e
                _print_debug('caught error: {}; retrying'.format(e))
                time.sleep(self._api.retry_delay)

        if self._api.decode_result:
            try:
                ret = json.loads(ret)
            except:
                raise APIError(-1, url, 'json decode error, value={0!r}'.format(ret))
        return ret

    def _mkarg(self, kargs):
        """change the argument list (encode value, add api key/secret)
        :return: the new argument list"""
        def enc(x):
            if isinstance(x, unicode):
                return x.encode('utf-8')
            return str(x)

        kargs = kargs.copy()
        kargs['api_key'] = self._api.key
        kargs['api_secret'] = self._api.secret
        for (k, v) in kargs.items():
            if isinstance(v, Iterable) and not isinstance(v, basestring):
                kargs[k] = ','.join([enc(i) for i in v])
            elif isinstance(v, File) or v is None:
                del kargs[k]
            else:
                kargs[k] = enc(v)

        return kargs

    def geturl(self, **kargs):
        """return the request url"""
        return self._urlbase + '?' + urllib.urlencode(self._mkarg(kargs)) 

    def visit(self, browser = 'chromium', **kargs):
        """visit the url in browser"""
        os.system('{0} "{1}"'.format(browser, self.geturl(**kargs)))



# ref: http://www.doughellmann.com/PyMOTW/urllib2/
class _MultiPartForm(object):
    """Accumulate the data to be used when posting a form."""

    def __init__(self):
        self.form_fields = []
        self.files = []
        self.boundary = mimetools.choose_boundary()
        return
    
    def get_content_type(self):
        return 'multipart/form-data; boundary=%s' % self.boundary

    def add_field(self, name, value):
        """Add a simple field to the form data."""
        self.form_fields.append((name, value))
        return

    def add_file(self, fieldname, filename, content, mimetype = None):
        """Add a file to be uploaded."""
        if mimetype is None:
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        self.files.append((fieldname, filename, mimetype, content))
        return
    
    def __str__(self):
        """Return a string representing the form data, including attached files."""
        # Build a list of lists, each containing "lines" of the
        # request.  Each part is separated by a boundary string.
        # Once the list is built, return a string where each
        # line is separated by '\r\n'.  
        parts = []
        part_boundary = '--' + self.boundary
        
        # Add the form fields
        parts.extend(
            [ part_boundary,
              'Content-Disposition: form-data; name="%s"' % name,
              '',
              value,
            ]
            for name, value in self.form_fields
            )
        
        # Add the files to upload
        parts.extend(
            [ part_boundary,
              'Content-Disposition: file; name="%s"; filename="%s"' % \
                 (field_name, filename),
              'Content-Type: %s' % content_type,
              '',
              body,
            ]
            for field_name, filename, content_type, body in self.files
            )
        
        # Flatten the list and add closing boundary marker,
        # then return CR+LF separated data
        flattened = list(itertools.chain(*parts))
        flattened.append('--' + self.boundary + '--')
        flattened.append('')
        return '\r\n'.join(flattened)


def _print_debug(msg):
    if DEBUG_LEVEL:
        sys.stderr.write(str(msg) + '\n')

_APIS = [
  '/detection/detect',
  '/detection/landmark',
  '/faceset/add_face',
  '/faceset/create',
  '/faceset/delete',
  '/faceset/get_info',
  '/faceset/remove_face',
  '/faceset/set_info',
  '/group/add_person',
  '/group/create',
  '/group/delete',
  '/group/get_info',
  '/group/remove_person',
  '/group/set_info',
  '/grouping/grouping',
  '/info/get_app',
  '/info/get_face',
  '/info/get_faceset_list',
  '/info/get_group_list',
  '/info/get_image',
  '/info/get_person_list',
  '/info/get_quota',
  '/info/get_session',
  '/person/add_face',
  '/person/create',
  '/person/delete',
  '/person/get_info',
  '/person/remove_face',
  '/person/set_info',
  '/recognition/compare',
  '/recognition/group_search',
  '/recognition/identify',
  '/recognition/recognize',
  '/recognition/search',
  '/recognition/test_train',
  '/recognition/train',
  '/recognition/verify',
  '/train/group_search',
  '/train/identify',
  '/train/recognize',
  '/train/search',
  '/train/verify'
]

_APIS = [i.split('/')[1:] for i in _APIS]

########NEW FILE########
__FILENAME__ = hello
#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# $File: hello.py

# In this tutorial, you will learn how to call Face ++ APIs and implement a
# simple App which could recognize a face image in 3 candidates.
# 在本教程中，您将了解到Face ++ API的基本调用方法，并实现一个简单的App，用以在3
# 张备选人脸图片中识别一个新的人脸图片。

# You need to register your App first, and enter you API key/secret.
# 您需要先注册一个App，并将得到的API key和API secret写在这里。
API_KEY = '<your API key here>'
API_SECRET = '<your API secret here>'

# Import system libraries and define helper functions
# 导入系统库并定义辅助函数
import time
from pprint import pformat
def print_result(hint, result):
    def encode(obj):
        if type(obj) is unicode:
            return obj.encode('utf-8')
        if type(obj) is dict:
            return {encode(k): encode(v) for (k, v) in obj.iteritems()}
        if type(obj) is list:
            return [encode(i) for i in obj]
        return obj
    print hint
    result = encode(result)
    print '\n'.join(['  ' + i for i in pformat(result, width = 75).split('\n')])

# First import the API class from the SDK
# 首先，导入SDK中的API类
from facepp import API

api = API(API_KEY, API_SECRET)

# Here are the person names and their face images
# 人名及其脸部图片
IMAGE_DIR = 'http://cn.faceplusplus.com/static/resources/python_demo/'
PERSONS = [
    ('Jim Parsons', IMAGE_DIR + '1.jpg'),
    ('Leonardo DiCaprio', IMAGE_DIR + '2.jpg'),
    ('Andy Liu', IMAGE_DIR + '3.jpg')
]
TARGET_IMAGE = IMAGE_DIR + '4.jpg'

# Step 1: Detect faces in the 3 pictures and find out their positions and
# attributes
# 步骤1：检测出三张输入图片中的Face，找出图片中Face的位置及属性

FACES = {name: api.detection.detect(url = url)
        for name, url in PERSONS}

for name, face in FACES.iteritems():
    print_result(name, face)


# Step 2: create persons using the face_id
# 步骤2：引用face_id，创建新的person
for name, face in FACES.iteritems():
    rst = api.person.create(
            person_name = name, face_id = face['face'][0]['face_id'])
    print_result('create person {}'.format(name), rst)

# Step 3: create a new group and add those persons in it
# 步骤3：.创建Group，将之前创建的Person加入这个Group
rst = api.group.create(group_name = 'test')
print_result('create group', rst)
rst = api.group.add_person(group_name = 'test', person_name = FACES.iterkeys())
print_result('add these persons to group', rst)

# Step 4: train the model
# 步骤4：训练模型
rst = api.train.identify(group_name = 'test')
print_result('train', rst)
# wait for training to complete
# 等待训练完成
rst = api.wait_async(rst['session_id'])
print_result('wait async', rst)

# Step 5: recognize face in a new image
# 步骤5：识别新图中的Face
rst = api.recognition.identify(group_name = 'test', url = TARGET_IMAGE)
print_result('recognition result', rst)
print '=' * 60
print 'The person with highest confidence:', \
        rst['face'][0]['candidate'][0]['person_name']

# Finally, delete the persons and group because they are no longer needed
# 最终，删除无用的person和group
api.group.delete(group_name = 'test')
api.person.delete(person_name = FACES.iterkeys())

# Congratulations! You have finished this tutorial, and you can continue
# reading our API document and start writing your own App using Face++ API!
# Enjoy :)
# 恭喜！您已经完成了本教程，可以继续阅读我们的API文档并利用Face++ API开始写您自
# 己的App了！
# 旅途愉快 :)

########NEW FILE########
__FILENAME__ = cmdtool
../cmdtool.py
########NEW FILE########
__FILENAME__ = facepp
../facepp.py
########NEW FILE########
