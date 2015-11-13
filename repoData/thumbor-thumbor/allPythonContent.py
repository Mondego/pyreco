__FILENAME__ = conf
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

########NEW FILE########
__FILENAME__ = conf1
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

########NEW FILE########
__FILENAME__ = default
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

# the domains that can have theyre images resized
ALLOWED_SOURCES = ['s.glbimg.com', 'www.globo.com']

# the max width of the resized image
MAX_WIDTH = 1280

# the max height of the resized image
MAX_HEIGHT = 800

ENGINE = 'thumbor.engines.pil'

LOADER = 'thumbor.loaders.http_loader'

STORAGE = 'thumbor.storages.file_storage'

FILE_STORAGE_ROOT_PATH = "/tmp/thumbor/storage"

# this is the security key used to encrypt/decrypt urls.
# make sure this is unique and not well-known
# This can be any string of up to 24 characters
SECURITY_KEY = "MY_SECURE_KEY"

# if you enable this, the unencryted URL will be available
# to users.
# IT IS VERY ADVISED TO SET THIS TO False TO STOP OVERLOADING
# OF THE SERVER FROM MALICIOUS USERS
ALLOW_UNSAFE_URL = True

########NEW FILE########
__FILENAME__ = file_loader_conf
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

LOADER = 'thumbor.loaders.file_loader'

# LOADER SPECIFIC CONFIGURATIONS
FILE_LOADER_ROOT_PATH = '@@rootdir@@'

########NEW FILE########
__FILENAME__ = file_storage_conf
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

STORAGE = 'thumbor.storages.file_storage'

# STORAGE SPECIFIC CONFIGURATIONS
FILE_STORAGE_ROOT_PATH = '/tmp/thumbor/storage'

########NEW FILE########
__FILENAME__ = file_storage_conf_2
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

STORAGE = 'thumbor.storages.file_storage'

# STORAGE SPECIFIC CONFIGURATIONS
FILE_STORAGE_ROOT_PATH = '/tmp/thumbor/storage'

STORES_CRYPTO_KEY_FOR_EACH_IMAGE = True

########NEW FILE########
__FILENAME__ = file_storage_conf_3
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

STORAGE = 'thumbor.storages.file_storage'

# STORAGE SPECIFIC CONFIGURATIONS
FILE_STORAGE_ROOT_PATH = '/tmp/thumbor/storage'

STORES_CRYPTO_KEY_FOR_EACH_IMAGE = True

SECURITY_KEY = 'MY-SECURITY-KEY'

########NEW FILE########
__FILENAME__ = jsonp
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

META_CALLBACK_NAME = 'callback'

LOADER = 'thumbor.loaders.http_loader'

STORAGE = 'thumbor.storages.file_storage'

FILE_STORAGE_ROOT_PATH = "/tmp/thumbor/storage"

# this is the security key used to encrypt/decrypt urls.
# make sure this is unique and not well-known
# This can be any string of up to 24 characters
SECURITY_KEY = "MY_SECURE_KEY"

# if you enable this, the unencryted URL will be available
# to users.
# IT IS VERY ADVISED TO SET THIS TO False TO STOP OVERLOADING
# OF THE SERVER FROM MALICIOUS USERS
ALLOW_UNSAFE_URL = True

########NEW FILE########
__FILENAME__ = mongo_storage_conf
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

STORAGE = 'thumbor.storages.mongo_storage'

MONGO_STORAGE_SERVER_HOST = 'localhost'
MONGO_STORAGE_SERVER_PORT = 27017
MONGO_STORAGE_SERVER_DB = 'thumbor_test'
MONGO_STORAGE_SERVER_COLLECTION = 'images'

########NEW FILE########
__FILENAME__ = mysql_storage_conf
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

STORAGE = 'thumbor.storages.mysql_storage'

MYSQL_STORAGE_SERVER_HOST = 'localhost'
MYSQL_STORAGE_SERVER_PORT = 3306
MYSQL_STORAGE_SERVER_DB = 'thumbor_tests'
MYSQL_STORAGE_SERVER_USER = 'root'
MYSQL_STORAGE_SERVER_PASSWORD = ''
MYSQL_STORAGE_SERVER_TABLE = 'images'

########NEW FILE########
__FILENAME__ = no_storage_conf
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

STORAGE = 'thumbor.storages.file_storage'

# STORAGE SPECIFIC CONFIGURATIONS
FILE_STORAGE_ROOT_PATH = '/tmp/thumbor/storage'

########NEW FILE########
__FILENAME__ = test_app
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import sys
from os.path import join, abspath, dirname

sys.path.append(abspath(join(dirname(__file__), '..')))

from tornado.testing import AsyncHTTPTestCase
from thumbor.app import ThumborServiceApp


class ThumborServiceTest(AsyncHTTPTestCase):

    def get_app(self):
        return ThumborServiceApp()

    def test_app_exists_and_is_instanceof_thumborserviceapp(self):
        assert isinstance(self._app, ThumborServiceApp), 'App does not exist or is not instance of the ThumborServiceApp class'

########NEW FILE########
__FILENAME__ = test_detectors
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from os.path import join, dirname, abspath
from cStringIO import StringIO

from thumbor.detectors.face_detector import Detector as FaceDetector
from thumbor.detectors.glasses_detector import Detector as GlassesDetector
from transform_helper import MockEngine
from PIL import Image


__dirname = abspath(dirname(__file__))


def get_context_from(image, detectors):
    filename = join(__dirname, 'fixtures', 'img', image)
    buffer = open(filename).read()
    size = Image.open(StringIO(buffer)).size
    context = dict(
        engine=MockEngine(size),
        buffer=buffer,
        file=filename,
        focal_points=[]
    )
    detectors[0](index=0, detectors=detectors).detect(context)
    return context


def test_should_not_create_focal_points_on_images_that_has_no_face():
    focal_points = get_context_from('fixture1.png', [FaceDetector])['focal_points']
    assert len(focal_points) == 0


def test_should_return_detect_a_face():
    focal_points = get_context_from('face.jpg', [FaceDetector])['focal_points']
    assert len(focal_points) == 1
    assert focal_points[0].x == 96
    assert focal_points[0].y == 80.48
    assert focal_points[0].weight == 13689


def test_should_not_detect_glasses():
    focal_points = get_context_from('fixture1.png', [GlassesDetector])['focal_points']
    assert len(focal_points) == 0


def test_should_detect_glasses():
    focal_points = get_context_from('glasses.jpg', [GlassesDetector])['focal_points']
    assert len(focal_points) == 1

########NEW FILE########
__FILENAME__ = test_drop_shadow_filter
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import re

from thumbor.filters.drop_shadow import Filter


def test_drop_shadow_filter_regex():
    reg = Filter.regex

    url = '''shadow(10, 10, "#ffffff", '#000000')/'''

    match = re.match(reg, url)

    assert match

    keys = match.groupdict()

    assert keys
    assert 'drop_shadow' in keys
    assert keys['drop_shadow'] == 'shadow(10, 10, "#ffffff", \'#000000\')', keys['drop_shadow']

########NEW FILE########
__FILENAME__ = test_file_loader
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import tempfile
from os.path import join, abspath, dirname

from tornado.testing import AsyncHTTPTestCase

import thumbor.loaders.file_loader as file_loader
from thumbor.app import ThumborServiceApp

fixtures_folder = join(abspath(dirname(__file__)), 'fixtures')


class FileLoaderTest(AsyncHTTPTestCase):

    def get_app(self):
        conf = open(join(fixtures_folder, 'file_loader_conf.py')).read()
        conf = conf.replace(r'@@rootdir@@', fixtures_folder)
        conf_file = tempfile.NamedTemporaryFile(mode='w+b', dir='/tmp', delete=False)
        conf_file.write(conf)
        conf_file.close()
        return ThumborServiceApp(conf_file.name)

    def test_loads_image(self):
        image_url = 'img/fixture1.png'
        file_loaded = file_loader.load(image_url)
        response = open(join(fixtures_folder, 'img', 'fixture1.png')).read()

        self.assertEqual(file_loaded, response, 'file_loaded is not the same as the filesystem equivalent')

########NEW FILE########
__FILENAME__ = test_focal_points
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from thumbor.point import FocalPoint


def test_focal_point():
    point = FocalPoint(x=10.0, y=20.0, weight=3.4)

    assert point.x == 10.0
    assert point.y == 20.0
    assert point.weight == 3.4


def test_default_weight_is_one():
    point = FocalPoint(x=10.0, y=20.0)

    assert point.weight == 1.0


def test_from_square():
    point = FocalPoint.from_square(x=10.0, y=20.0, width=100, height=200)
    assert point.x == 55.0
    assert point.y == 110.0
    assert point.weight == 20000.0


def test_focal_points_alignments():
    for point in [
        ('left', 'top', 100, 200, 0.0, 0.0),
        ('left', 'middle', 100, 200, 0.0, 100.0),
        ('left', 'bottom', 100, 200, 0.0, 200.0),
        ('center', 'top', 100, 200, 50.0, 0.0),
        ('center', 'middle', 100, 200, 50.0, 100.0),
        ('center', 'bottom', 100, 200, 50.0, 200.0),
        ('right', 'top', 100, 200, 100.0, 0.0),
        ('right', 'middle', 100, 200, 100.0, 100.0),
        ('right', 'bottom', 100, 200, 100.0, 200.0)
    ]:
        yield assert_point_from_alignment, point


def assert_point_from_alignment(point):
    comp_point = FocalPoint.from_alignment(point[0], point[1], width=point[2], height=point[3])

    assert comp_point.x == point[4], "Expected x => %.2f Got x => %.2f" % (point[4], comp_point.x)
    assert comp_point.y == point[5], "Expected y => %.2f Got y => %.2f" % (point[5], comp_point.y)
    assert comp_point.weight == 1.0

########NEW FILE########
__FILENAME__ = test_handlers
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import os
from os.path import join, abspath, dirname
from cStringIO import StringIO
import unittest

from PIL import Image
from tornado.testing import AsyncHTTPTestCase

from thumbor.app import ThumborServiceApp

get_conf_path = lambda filename: abspath(join(os.environ.get('test_path', dirname(__file__)), 'fixtures', filename))


class MainHandlerSourcePathTest(AsyncHTTPTestCase):

    def get_app(self):
        return ThumborServiceApp(get_conf_path('conf1.py'))

    def test_validates_passed_url_is_in_valid_source(self):
        self.http_client.fetch(self.get_url('/unsafe/www.mydomain.com/logo2.jpg'), self.stop)
        response = self.wait()
        self.assertEqual(404, response.code)


class MainHandlerTest(AsyncHTTPTestCase):

    def get_app(self):
        return ThumborServiceApp(get_conf_path('default.py'))

    def test_returns_success_status_code(self):
        self.http_client.fetch(self.get_url('/unsafe/www.globo.com/media/globocom/img/sprite1.png'), self.stop)
        response = self.wait(timeout=20)
        self.assertEqual(200, response.code)


class ImageTestCase(AsyncHTTPTestCase):

    def get_app(self):
        return ThumborServiceApp(get_conf_path('default.py'))

    def fetch_image(self, url):
        self.http_client.fetch(self.get_url(url), self.stop)
        response = self.wait()
        self.assertEqual(200, response.code)
        return Image.open(StringIO(response.body))


class MainHandlerImagesTest(ImageTestCase):

    def test_resizes_the_passed_image(self):
        image = self.fetch_image('/unsafe/200x300/www.globo.com/media/globocom/img/sprite1.png')
        img_width, img_height = image.size
        self.assertEqual(img_width, 200)
        self.assertEqual(img_height, 300)

    def test_flips_horizontaly_the_passed_image(self):
        image = self.fetch_image('/unsafe/www.globo.com/media/common/img/estrutura/borderbottom.gif')
        image_flipped = self.fetch_image('/unsafe/-3x/www.globo.com/media/common/img/estrutura/borderbottom.gif')
        pixels = list(image.getdata())
        pixels_flipped = list(image_flipped.getdata())

        self.assertEqual(len(pixels), len(pixels_flipped), 'the images do not have the same size')

        reversed_pixels_flipped = list(reversed(pixels_flipped))

        self.assertEqual(pixels, reversed_pixels_flipped, 'did not flip the image')


class MainHandlerFitInImagesTest(ImageTestCase):

    def test_fits_in_image_horizontally(self):
        #620x470
        image = self.fetch_image('/unsafe/fit-in/200x300/s.glbimg.com/es/ge/f/original/2011/04/19/adriano_ae62.jpg')

        width, height = image.size

        assert width == 200, width
        assert height == 151, height

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_meta_transform
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from os.path import abspath, dirname, join
import json

from tornado.testing import AsyncHTTPTestCase
from tornado.options import options

from thumbor.app import ThumborServiceApp

get_conf_path = lambda filename: abspath(join(dirname(__file__), 'fixtures', filename))


class MetaHandlerTestCase(AsyncHTTPTestCase):

    def get_app(self):
        app = ThumborServiceApp(get_conf_path('default.py'))
        return app

    def test_meta_returns_200(self):
        options.META_CALLBACK_NAME = None
        self.http_client.fetch(self.get_url('/unsafe/meta/s.glbimg.com/es/ge/f/original/2011/03/22/boavista_x_botafogo.jpg'), self.stop)
        response = self.wait()

        self.assertEqual(200, response.code)

    def test_meta_returns_appjson_code(self):
        options.META_CALLBACK_NAME = None
        self.http_client.fetch(self.get_url('/unsafe/meta/s.glbimg.com/es/ge/f/original/2011/03/22/boavista_x_botafogo.jpg'), self.stop)
        response = self.wait()

        assert response.code == 200
        content_type = response.headers['Content-Type']
        self.assertEqual("application/json", content_type)

    def test_meta_returns_proper_json_for_no_ops(self):
        options.META_CALLBACK_NAME = None
        image_url = "s.glbimg.com/es/ge/f/original/2011/03/22/boavista_x_botafogo.jpg"
        self.http_client.fetch(self.get_url('/unsafe/meta/%s' % image_url), self.stop)
        response = self.wait()

        text = response.body
        operations = json.loads(text)

        assert operations
        assert operations['thumbor']
        assert operations['thumbor']['source']['url'] == image_url
        assert operations['thumbor']['source']['width'] == 620
        assert operations['thumbor']['source']['height'] == 349
        assert "operations" in operations['thumbor']
        assert not operations['thumbor']['operations']

    def test_meta_returns_proper_json_for_resize_and_crop(self):
        options.META_CALLBACK_NAME = None
        image_url = "s.glbimg.com/es/ge/f/original/2011/03/22/boavista_x_botafogo.jpg"
        self.http_client.fetch(self.get_url('/unsafe/meta/300x200/%s' % image_url), self.stop)
        response = self.wait()

        text = response.body
        thumbor_json = json.loads(text)

        operations = thumbor_json['thumbor']['operations']

        assert len(operations) == 2

        assert operations[0]['type'] == 'crop'
        assert operations[0]['top'] == 0
        assert operations[0]['right'] == 572
        assert operations[0]['bottom'] == 349
        assert operations[0]['left'] == 48

        assert operations[1]['type'] == 'resize'
        assert operations[1]['width'] == 300
        assert operations[1]['height'] == 200

    def test_meta_returns_proper_json_for_resize_and_manual_crop(self):
        options.META_CALLBACK_NAME = None
        image_url = "s.glbimg.com/es/ge/f/original/2011/03/22/boavista_x_botafogo.jpg"
        self.http_client.fetch(self.get_url('/unsafe/meta/0x0:100x100/50x0/%s' % image_url), self.stop)
        response = self.wait()

        text = response.body
        thumbor_json = json.loads(text)

        target = thumbor_json['thumbor']['target']

        assert target['width'] == 50
        assert target['height'] == 50, target['height']

    def test_meta_returns_proper_target_for_resize_and_crop(self):
        options.META_CALLBACK_NAME = None
        image_url = "s.glbimg.com/es/ge/f/original/2011/03/22/boavista_x_botafogo.jpg"
        self.http_client.fetch(self.get_url('/unsafe/meta/300x200/%s' % image_url), self.stop)
        response = self.wait()

        text = response.body
        thumbor_json = json.loads(text)

        target = thumbor_json['thumbor']['target']

        assert target['width'] == 300
        assert target['height'] == 200

    def test_meta_returns_proper_target_for_crop(self):
        options.META_CALLBACK_NAME = None
        image_url = "s.glbimg.com/es/ge/f/original/2011/03/22/boavista_x_botafogo.jpg"
        self.http_client.fetch(self.get_url('/unsafe/meta/0x0:100x100/%s' % image_url), self.stop)
        response = self.wait()

        text = response.body
        thumbor_json = json.loads(text)

        target = thumbor_json['thumbor']['target']

        assert target['width'] == 100
        assert target['height'] == 100

    def test_meta_returns_proper_target_for_crop_and_resize(self):
        options.META_CALLBACK_NAME = None
        image_url = "s.glbimg.com/es/ge/f/original/2011/03/22/boavista_x_botafogo.jpg"
        self.http_client.fetch(self.get_url('/unsafe/meta/0x0:200x250/200x0/%s' % image_url), self.stop)
        response = self.wait()

        text = response.body
        thumbor_json = json.loads(text)

        target = thumbor_json['thumbor']['target']

        image_url = "s.glbimg.com/es/ge/f/original/2011/03/22/boavista_x_botafogo.jpg"
        self.http_client.fetch(self.get_url('/unsafe/meta/50x40:250x290/200x0/%s' % image_url), self.stop)
        response = self.wait()

        text = response.body
        thumbor_json = json.loads(text)

        target_2 = thumbor_json['thumbor']['target']

        image_url = "s.glbimg.com/es/ge/f/original/2011/03/22/boavista_x_botafogo.jpg"
        self.http_client.fetch(self.get_url('/unsafe/meta/250x80:450x330/200x0/%s' % image_url), self.stop)
        response = self.wait()

        text = response.body
        thumbor_json = json.loads(text)

        target_3 = thumbor_json['thumbor']['target']

        assert target['width'] == target_2['width']
        assert target['height'] == target_2['height']

        assert target['width'] == target_3['width']
        assert target['height'] == target_3['height']

    def test_meta_returns_proper_json_for_flip(self):
        options.META_CALLBACK_NAME = None
        image_url = "s.glbimg.com/es/ge/f/original/2011/03/22/boavista_x_botafogo.jpg"
        self.http_client.fetch(self.get_url('/unsafe/meta/-300x-200/%s' % image_url), self.stop)
        response = self.wait()

        text = response.body
        thumbor_json = json.loads(text)

        operations = thumbor_json['thumbor']['operations']

        assert len(operations) == 4

        assert operations[2]['type'] == 'flip_horizontally'
        assert operations[3]['type'] == 'flip_vertically'


class MetaHandlerJSONPTestCase(AsyncHTTPTestCase):

    def get_app(self):
        return ThumborServiceApp(get_conf_path('jsonp.py'))

    def test_meta_returns_proper_json_for_no_ops_with_callback(self):
        image_url = "s.glbimg.com/es/ge/f/original/2011/03/22/boavista_x_botafogo.jpg"
        self.http_client.fetch(self.get_url('/unsafe/meta/%s' % image_url), self.stop)
        response = self.wait()

        text = response.body

        assert text.strip().startswith('callback({')
        assert text.strip().endswith('});')

########NEW FILE########
__FILENAME__ = test_transformer

########NEW FILE########
__FILENAME__ = test_urls
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

########NEW FILE########
__FILENAME__ = transform_helper
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

########NEW FILE########
__FILENAME__ = compare_engines
#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
from os.path import abspath, dirname, join, exists
import shutil
import time

from jinja2 import FileSystemLoader, Environment
from tornado.options import parse_config_file

#required for importing configuration
import thumbor.app
import thumbor.handlers


REPETITIONS = 200
IMAGE_NAME = 'fred'


def get_engine(engine_name):
    module_name = 'thumbor.engines.%s' % engine_name
    module = __import__(module_name)
    return reduce(getattr, module_name.split('.')[1:], module).Engine


def main():
    root = abspath(dirname(__file__))
    image = join(root, '%s.jpg' % IMAGE_NAME)

    conf_file = join(root, 'thumbor.conf')
    parse_config_file(conf_file)

    engines = [('PIL', 'pil'),]

    build_dir = join(root, 'build')
    if exists(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir)

    source = file(image).read()

    originals = []
    resized = []
    qualities = {}
    times = {}

    for key, engine_class_name in engines:
        engine_class = get_engine(engine_class_name)
        engine = engine_class()
        engine.load(source, '.jpg')

        filename = '%s_%s.jpg' % (IMAGE_NAME, key)
        file(join(build_dir, filename), 'w').write(engine.read('.jpg'))
        originals.append((key, filename))

        engine.resize(300, 300)

        filename = '%s_%s_300x300.jpg' % (IMAGE_NAME, key)
        file(join(build_dir, filename), 'w').write(engine.read('.jpg'))
        resized.append((key, '300x300', filename))

        qualities[key] = []
        for quality in range(10):
            if quality == 0:
                continue
            filename = '%s_%s_300x300_%d.jpg' % (IMAGE_NAME, key, quality)
            file(join(build_dir, filename), 'w').write(engine.read('.jpg', quality=quality * 10))
            qualities[key].append(('300x300', quality, filename))

    number_of_engines = len(engines)
    current_engine = 0

    for key, engine_class_name in engines:
        start = time.time()

        print "Started benchmarking of %s" % key
        for i in range(REPETITIONS):
            print "%.2f%%" % (((float(current_engine) * REPETITIONS + i) / (float(number_of_engines) * REPETITIONS)) * 100)
            engine_class = get_engine(engine_class_name)
            engine = engine_class()
            engine.load(source, '.jpg')
            engine.crop(100, 100, 200, 200)
            engine.resize(50, 50)
            engine.read('.jpg')

        times[key] = "%.6f" % (time.time() - start)

        current_engine += 1

    loader = FileSystemLoader(root)
    env = Environment(loader=loader)
    template = env.get_template('template.html')
    file(join(build_dir, 'results.html'), 'w').write(template.render(no_resized=originals, resized=resized, qualities=qualities, times=times, image_name=IMAGE_NAME))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = detect
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import glob
import os
import tempfile
import sys
from os.path import dirname, abspath, join, basename, splitext, exists

import cv
from tornado.options import define

define('MAGICKWAND_PATH', [])

__dirname = abspath(dirname(__file__))
sys.path.insert(0, abspath(join(__dirname, '..', '..')))

from thumbor.vendor.pythonmagickwand.image import Image


cascade_files = (
    join('face_detector', 'haarcascade_frontalface_alt.xml'),
    join('profile_detector', 'haarcascade_profileface.xml'),
    join('glasses_detector', 'haarcascade_eye_tree_eyeglasses.xml')
)

cascade_files = [abspath(join(__dirname, '..', '..', 'thumbor', 'detectors', cascade_file)) for cascade_file in cascade_files]

images_path = glob.glob(abspath(join(__dirname, '..', 'fixtures', 'img', '*.*')))

for cascade_file in cascade_files:
    loaded_cascade_file = cv.Load(cascade_file)

    for image_path in images_path:

        with tempfile.NamedTemporaryFile() as temp_file:
            file_name = temp_file.name

            #imagick
            img = Image(image_path)
            img.format = 'JPEG'
            img.save(file_name)

            #pil
            #PILImage.open(image_path).convert('RGB').save(file_name, 'JPEG')

            grayscale = cv.LoadImageM(file_name, cv.CV_LOAD_IMAGE_GRAYSCALE)

            faces = cv.HaarDetectObjects(
                grayscale, loaded_cascade_file,
                cv.CreateMemStorage(), 1.1, 3, cv.CV_HAAR_DO_CANNY_PRUNING, (30, 30))

            if faces:
                for (left, top, width, height), neighbors in faces:
                    cv.Rectangle(
                        grayscale,
                        (int(left), int(top)),
                        (int(left + width), int(top + height)),
                        255
                    )
                cascade_file_name = splitext(basename(cascade_file))[0]
                destination_folder = join(__dirname, 'img')
                if not exists(destination_folder):
                    os.makedirs(destination_folder)
                cv.SaveImage(join(destination_folder, '%s_%s' % (cascade_file_name, basename(image_path))), grayscale)
                print 'face detected on %s using %s' % (basename(image_path), basename(cascade_file))

########NEW FILE########
__FILENAME__ = app
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com
import tornado.web
import tornado.ioloop

from thumbor.handlers.healthcheck import HealthcheckHandler
from thumbor.handlers.upload import UploadHandler
from thumbor.handlers.images import ImagesHandler
from thumbor.handlers.image import ImageHandler
from thumbor.url import Url
from thumbor.handlers.imaging import ImagingHandler


class ThumborServiceApp(tornado.web.Application):

    def __init__(self, context):
        self.context = context
        super(ThumborServiceApp, self).__init__(self.get_handlers())

    def get_handlers(self):
        handlers = [
            (r'/healthcheck', HealthcheckHandler),
        ]

        if self.context.config.UPLOAD_ENABLED:
            # TODO Old handler to upload images
            handlers.append(
                (r'/upload', UploadHandler, {'context': self.context})
            )

            # Handler to upload images (POST).
            handlers.append(
                (r'/image', ImagesHandler, {'context': self.context})
            )

            # Handler to retrieve or modify existing images  (GET, PUT, DELETE)
            handlers.append(
                (r'/image/(.*)', ImageHandler, {'context': self.context})
            )

        # Imaging handler (GET)
        handlers.append(
            (Url.regex(), ImagingHandler, {'context': self.context})
        )

        return handlers

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from os.path import join
import tempfile

import derpconf.config as config
from derpconf.config import Config

from thumbor import __version__

Config.define(
    'THUMBOR_LOG_FORMAT', '%(asctime)s %(name)s:%(levelname)s %(message)s',
    'Log Format to be used by thumbor when writing log messages.', 'Logging')

Config.define(
    'THUMBOR_LOG_DATE_FORMAT', '%Y-%m-%d %H:%M:%S',
    'Date Format to be used by thumbor when writing log messages.', 'Logging')

Config.define('MAX_WIDTH', 0, "Max width in pixels for images read or generated by thumbor", 'Imaging')
Config.define('MAX_HEIGHT', 0, "Max height in pixels for images read or generated by thumbor", 'Imaging')
Config.define('MIN_WIDTH', 1, "Min width in pixels for images read or generated by thumbor", 'Imaging')
Config.define('MIN_HEIGHT', 1, "Min width in pixels for images read or generated by thumbor", 'Imaging')
Config.define('ALLOWED_SOURCES', [], "Allowed domains for the http loader to download. These are regular expressions.", 'Imaging')
Config.define('QUALITY', 80, 'Quality index used for generated JPEG images', 'Imaging')
Config.define('WEBP_QUALITY', None, 'Quality index used for generated WebP images. If not set (None) the same level of JPEG quality will be used.', 'Imaging')
Config.define('AUTO_WEBP', False, 'Specifies whether WebP format should be used automatically if the request accepts it (via Accept header)', 'Imaging')
Config.define('MAX_AGE', 24 * 60 * 60, 'Max AGE sent as a header for the image served by thumbor in seconds', 'Imaging')
Config.define(
    'MAX_AGE_TEMP_IMAGE', 0,
    "Indicates the Max AGE header in seconds for temporary images (images with failed smart detection)", 'Imaging')
Config.define(
    'RESPECT_ORIENTATION', False,
    'Indicates whether thumbor should rotate images that have an Orientation EXIF header', 'Imaging')
Config.define(
    'IGNORE_SMART_ERRORS', False,
    'Ignore errors during smart detections and return image as a temp image (not saved in result storage and with MAX_AGE_TEMP_IMAGE age)', 'Imaging')

Config.define(
    'PRESERVE_EXIF_INFO', False,
    'Preserves exif information in generated images. Increases image size in kbytes, use with caution.', 'Imaging')

Config.define(
    'ALLOW_ANIMATED_GIFS', True,
    'Indicates whether thumbor should enable the EXPERIMENTAL support for animated gifs.', 'Imaging')

Config.define(
    'LOADER', 'thumbor.loaders.http_loader',
    'The loader thumbor should use to load the original image. This must be the full name of a python module ' +
    '(python must be able to import it)', 'Extensibility')
Config.define(
    'STORAGE', 'thumbor.storages.file_storage',
    'The file storage thumbor should use to store original images. This must be the full name of a python module ' +
    '(python must be able to import it)', 'Extensibility')
Config.define(
    'RESULT_STORAGE', None,
    'The result storage thumbor should use to store generated images. This must be the full name of a python ' +
    'module (python must be able to import it)', 'Extensibility')
Config.define(
    'ENGINE', 'thumbor.engines.pil',
    'The imaging engine thumbor should use to perform image operations. This must be the full name of a ' +
    'python module (python must be able to import it)', 'Extensibility')

Config.define('SECURITY_KEY', 'MY_SECURE_KEY', 'The security key thumbor uses to sign image URLs', 'Security')

Config.define('ALLOW_UNSAFE_URL', True, 'Indicates if the /unsafe URL should be available', 'Security')
Config.define('ALLOW_OLD_URLS', True, 'Indicates if encrypted (old style) URLs should be allowed', 'Security')


# FILE LOADER OPTIONS
Config.define('FILE_LOADER_ROOT_PATH', '/tmp', 'The root path where the File Loader will try to find images', 'File Loader')

# HTTP LOADER OPTIONS
Config.define(
    'HTTP_LOADER_CONNECT_TIMEOUT', 5,
    'The maximum number of seconds libcurl can take to connect to an image being loaded', 'HTTP Loader')
Config.define(
    'HTTP_LOADER_REQUEST_TIMEOUT', 20,
    'The maximum number of seconds libcurl can take to download an image', 'HTTP Loader')
Config.define(
    'HTTP_LOADER_FOLLOW_REDIRECTS', True,
    'Indicates whether libcurl should follow redirects when downloading an image', 'HTTP Loader')
Config.define(
    'HTTP_LOADER_MAX_REDIRECTS', 5,
    'Indicates the number of redirects libcurl should follow when downloading an image', 'HTTP Loader')
Config.define(
    'HTTP_LOADER_FORWARD_USER_AGENT', False,
    'Indicates whether thumbor should forward the user agent of the requesting user', 'HTTP Loader')
Config.define(
    'HTTP_LOADER_DEFAULT_USER_AGENT', "Thumbor/%s" % __version__,
    'Default user agent for thumbor http loader requests', 'HTTP Loader')
Config.define(
    'HTTP_LOADER_PROXY_HOST', None,
    'The proxy host needed to load images through', 'HTTP Loader')
Config.define(
    'HTTP_LOADER_PROXY_PORT', None,
    'The proxy port for the proxy host', 'HTTP Loader')
Config.define(
    'HTTP_LOADER_PROXY_USERNAME', None,
    'The proxy username for the proxy host', 'HTTP Loader')
Config.define(
    'HTTP_LOADER_PROXY_PASSWORD', None,
    'The proxy password for the proxy host', 'HTTP Loader')

# FILE STORAGE GENERIC OPTIONS
Config.define(
    'STORAGE_EXPIRATION_SECONDS', 60 * 60 * 24 * 30,
    "Expiration in seconds for the images in the File Storage. Defaults to one month", 'File Storage')
Config.define(
    'STORES_CRYPTO_KEY_FOR_EACH_IMAGE', False,
    'Indicates whether thumbor should store the signing key for each image in the file storage. ' +
    'This allows the key to be changed and old images to still be properly found', 'File Storage')

# FILE STORAGE OPTIONS
Config.define(
    'FILE_STORAGE_ROOT_PATH', join(tempfile.gettempdir(), 'thumbor', 'storage'),
    'The root path where the File Storage will try to find images', 'File Storage')

# PHOTO UPLOAD OPTIONS
Config.define('UPLOAD_MAX_SIZE', 0, "Max size in Kb for images uploaded to thumbor", 'Upload')
Config.define('UPLOAD_ENABLED', False, 'Indicates whether thumbor should enable File uploads', 'Upload')
Config.define(
    'UPLOAD_PHOTO_STORAGE', 'thumbor.storages.file_storage',
    'The type of storage to store uploaded images with', 'Upload')
Config.define('UPLOAD_DELETE_ALLOWED', False, 'Indicates whether image deletion should be allowed', 'Upload')
Config.define('UPLOAD_PUT_ALLOWED', False, 'Indicates whether image overwrite should be allowed', 'Upload')
Config.define('UPLOAD_DEFAULT_FILENAME', 'image', 'Default filename for image uploaded', 'Upload')

# ALIASES FOR OLD PHOTO UPLOAD OPTIONS
Config.alias('MAX_SIZE', 'UPLOAD_MAX_SIZE')
Config.alias('ENABLE_ORIGINAL_PHOTO_UPLOAD', 'UPLOAD_ENABLED')
Config.alias('ORIGINAL_PHOTO_STORAGE', 'UPLOAD_PHOTO_STORAGE')
Config.alias('ALLOW_ORIGINAL_PHOTO_DELETION', 'UPLOAD_DELETE_ALLOWED')
Config.alias('ALLOW_ORIGINAL_PHOTO_PUTTING', 'UPLOAD_PUT_ALLOWED')

# MONGO STORAGE OPTIONS
Config.define('MONGO_STORAGE_SERVER_HOST', 'localhost', 'MongoDB storage server host', 'MongoDB Storage')
Config.define('MONGO_STORAGE_SERVER_PORT', 27017, 'MongoDB storage server port', 'MongoDB Storage')
Config.define('MONGO_STORAGE_SERVER_DB', 'thumbor', 'MongoDB storage server database name', 'MongoDB Storage')
Config.define('MONGO_STORAGE_SERVER_COLLECTION', 'images', 'MongoDB storage image collection', 'MongoDB Storage')

# REDIS STORAGE OPTIONS
Config.define('REDIS_STORAGE_SERVER_HOST', 'localhost', 'Redis storage server host', 'Redis Storage')
Config.define('REDIS_STORAGE_SERVER_PORT', 6379, 'Redis storage server port', 'Redis Storage')
Config.define('REDIS_STORAGE_SERVER_DB', 0, 'Redis storage database index', 'Redis Storage')
Config.define('REDIS_STORAGE_SERVER_PASSWORD', None, 'Redis storage server password', 'Redis Storage')

# MEMCACHE STORAGE OPTIONS
Config.define('MEMCACHE_STORAGE_SERVERS', ['localhost:11211'], 'List of Memcache storage server hosts', 'Memcache Storage')

# MIXED STORAGE OPTIONS
Config.define(
    'MIXED_STORAGE_FILE_STORAGE', 'thumbor.storages.no_storage',
    'Mixed Storage file storage. This must be the full name of a python module (python must be able ' +
    'to import it)', 'Mixed Storage')
Config.define(
    'MIXED_STORAGE_CRYPTO_STORAGE', 'thumbor.storages.no_storage',
    'Mixed Storage signing key storage. This must be the full name of a python module (python must be ' +
    'able to import it)', 'Mixed Storage')
Config.define(
    'MIXED_STORAGE_DETECTOR_STORAGE', 'thumbor.storages.no_storage',
    'Mixed Storage detector information storage. This must be the full name of a python module (python ' +
    'must be able to import it)', 'Mixed Storage')

# JSON META ENGINE OPTIONS
Config.define(
    'META_CALLBACK_NAME', None,
    'The callback function name that should be used by the META route for JSONP access', 'Meta')

# DETECTORS OPTIONS
Config.define(
    'DETECTORS', [],
    'List of detectors that thumbor should use to find faces and/or features. All of them must be ' +
    'full names of python modules (python must be able to import it)', 'Detection')

# FACE DETECTOR CASCADE FILE
Config.define(
    'FACE_DETECTOR_CASCADE_FILE', 'haarcascade_frontalface_alt.xml',
    'The cascade file that opencv will use to detect faces', 'Detection')

# AVAILABLE FILTERS
Config.define(
    'FILTERS', [
        'thumbor.filters.brightness',
        'thumbor.filters.contrast',
        'thumbor.filters.rgb',
        'thumbor.filters.round_corner',
        'thumbor.filters.quality',
        'thumbor.filters.noise',
        'thumbor.filters.watermark',
        'thumbor.filters.equalize',
        'thumbor.filters.fill',
        'thumbor.filters.sharpen',
        'thumbor.filters.strip_icc',
        'thumbor.filters.frame',
        'thumbor.filters.grayscale',
        'thumbor.filters.format',
        'thumbor.filters.max_bytes',
        'thumbor.filters.convolution',
        'thumbor.filters.blur',
        'thumbor.filters.extract_focal',
    ],
    'List of filters that thumbor will allow to be used in generated images. All of them must be ' +
    'full names of python modules (python must be able to import it)', 'Filters')

# RESULT STORAGE
Config.define(
    'RESULT_STORAGE_EXPIRATION_SECONDS', 0,
    'Expiration in seconds of generated images in the result storage', 'Result Storage')  # Never expires
Config.define(
    'RESULT_STORAGE_FILE_STORAGE_ROOT_PATH', join(tempfile.gettempdir(), 'thumbor', 'result_storage'),
    'Path where the Result storage will store generated images', 'Result Storage')
Config.define(
    'RESULT_STORAGE_STORES_UNSAFE', False,
    'Indicates whether unsafe requests should also be stored in the Result Storage', 'Result Storage')

# QUEUED DETECTOR REDIS OPTIONS
Config.define('REDIS_QUEUE_SERVER_HOST', 'localhost', 'Server host for the queued redis detector', 'Queued Redis Detector')
Config.define('REDIS_QUEUE_SERVER_PORT', 6379, 'Server port for the queued redis detector', 'Queued Redis Detector')
Config.define('REDIS_QUEUE_SERVER_DB', 0, 'Server database index for the queued redis detector', 'Queued Redis Detector')
Config.define('REDIS_QUEUE_SERVER_PASSWORD', None, 'Server password for the queued redis detector', 'Queued Redis Detector')

# QUEUED DETECTOR SQS OPTIONS
Config.define('SQS_QUEUE_KEY_ID', None, 'AWS key id', 'Queued SQS Detector')
Config.define('SQS_QUEUE_KEY_SECRET', None, 'AWS key secret', 'Queued SQS Detector')
Config.define('SQS_QUEUE_REGION', 'us-east-1', 'AWS SQS region', 'Queued SQS Detector')

# ERROR HANDLING
Config.define(
    'USE_CUSTOM_ERROR_HANDLING', False,
    'This configuration indicates whether thumbor should use a custom error handler.', 'Errors')
Config.define(
    'ERROR_HANDLER_MODULE', 'thumbor.error_handlers.sentry',
    'Error reporting module. Needs to contain a class called ErrorHandler with a ' +
    'handle_error(context, handler, exception) method.', 'Errors')

# SENTRY REPORTING MODULE
Config.define(
    'SENTRY_DSN_URL', '',
    'Sentry thumbor project dsn. i.e.: ' +
    'http://5a63d58ae7b94f1dab3dee740b301d6a:73eea45d3e8649239a973087e8f21f98@localhost:9000/2', 'Errors - Sentry')

# FILE REPORTING MODULE
Config.define('ERROR_FILE_LOGGER', None, 'File of error log as json', 'Errors')


def generate_config():
    config.generate_config()


def format_value(value):
    if isinstance(value, basestring):
        return "'%s'" % value
    if isinstance(value, (tuple, list, set)):
        representation = '[\n'
        for item in value:
            representation += '#    %s' % item
        representation += '#]'
        return representation
    return value

if __name__ == '__main__':
    generate_config()

########NEW FILE########
__FILENAME__ = console
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import optparse

from thumbor.context import ServerParameters
from thumbor import __version__


def get_server_parameters(arguments=None):
    parser = optparse.OptionParser(usage="thumbor or type thumbor -h (--help) for help", description=__doc__, version=__version__)
    parser.add_option("-p", "--port", type="int", dest="port", default=8888, help="The port to run this thumbor instance at [default: %default].")
    parser.add_option("-i", "--ip", dest="ip", default="0.0.0.0", help="The host address to run this thumbor instance at [default: %default].")
    parser.add_option("-f", "--fd", dest="file_descriptor", help="The file descriptor number or path to listen for connections on (--port and --ip will be ignored if this is set) [default: %default].")
    parser.add_option("-c", "--conf", dest="conf", default="", help="The path of the configuration file to use for this thumbor instance [default: %default].")
    parser.add_option("-k", "--keyfile", dest="keyfile", default="", help="The path of the security key file to use for this thumbor instance [default: %default].")
    parser.add_option("-l", "--log-level", dest="log_level", default="warning", help="The log level to be used. Possible values are: debug, info, warning, error, critical or notset. [default: %default].")
    parser.add_option("-a", "--app", dest="app", default='thumbor.app.ThumborServiceApp', help="A custom app to use for this thumbor server in case you subclassed ThumborServiceApp [default: %default].")

    (options, args) = parser.parse_args(arguments)

    port = options.port
    ip = options.ip
    fd = options.file_descriptor
    conf = options.conf or None
    keyfile = options.keyfile or None
    log_level = options.log_level

    return ServerParameters(port=port,
                            ip=ip,
                            config_path=conf,
                            keyfile=keyfile,
                            log_level=log_level,
                            app_class=options.app,
                            fd=fd)

########NEW FILE########
__FILENAME__ = context
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from os.path import abspath, exists

from thumbor.filters import FiltersFactory
from thumbor.url import Url


class Context:
    '''
    Class responsible for containing:
    * Server Configuration Parameters (port, ip, key, etc);
    * Configurations read from config file (or defaults);
    * Importer with imported modules (engine, filters, detectors, etc);
    * Request Parameters (width, height, smart, meta, etc).

    Each instance of this class MUST be unique per request. This class should not be cached in the server.
    '''

    def __init__(self, server=None, config=None, importer=None, request_handler=None):
        self.server = server
        self.config = config
        if importer:
            self.modules = ContextImporter(self, importer)
        else:
            self.modules = None
        self.filters_factory = FiltersFactory(self.modules.filters if self.modules else [])
        self.request_handler = request_handler


class ServerParameters(object):
    def __init__(self, port, ip, config_path, keyfile, log_level, app_class, fd=None):
        self.port = port
        self.ip = ip
        self.config_path = config_path
        self.keyfile = keyfile
        self.log_level = log_level
        self.app_class = app_class
        self._security_key = None
        self.fd = fd
        self.load_security_key()

    @property
    def security_key(self):
        return self._security_key

    @security_key.setter
    def security_key(self, key):
        if isinstance(key, unicode):
            key = key.encode('utf-8')
        self._security_key = key

    def load_security_key(self):
        if not self.keyfile:
            return

        path = abspath(self.keyfile)
        if not exists(path):
            raise ValueError('Could not find security key file at %s. Please verify the keypath argument.' % path)

        with open(path, 'r') as f:
            security_key = f.read().strip()

        self.security_key = security_key


class RequestParameters:

    def __init__(self,
                 debug=False,
                 meta=False,
                 trim=None,
                 crop_left=None,
                 crop_top=None,
                 crop_right=None,
                 crop_bottom=None,
                 crop=None,
                 adaptive=False,
                 fit_in=False,
                 width=0,
                 height=0,
                 horizontal_flip=False,
                 vertical_flip=False,
                 halign='center',
                 valign='middle',
                 filters=None,
                 smart=False,
                 quality=80,
                 image=None,
                 url=None,
                 extension=None,
                 buffer=None,
                 focal_points=None,
                 unsafe=False,
                 hash=None,
                 accepts_webp=False,
                 request=None):

        self.debug = bool(debug)
        self.meta = bool(meta)
        self.trim = trim
        if trim is not None:
            trim_parts = trim.split(':')
            self.trim_pos = trim_parts[1] if len(trim_parts) > 1 else "top-left"
            self.trim_tolerance = int(trim_parts[2]) if len(trim_parts) > 2 else 0

        if crop is not None:
            self.crop = crop
        else:
            self.crop = {
                'left': self.int_or_0(crop_left),
                'right': self.int_or_0(crop_right),
                'top': self.int_or_0(crop_top),
                'bottom': self.int_or_0(crop_bottom)
            }

        self.should_crop = \
            self.crop['left'] > 0 or \
            self.crop['top'] > 0 or \
            self.crop['right'] > 0 or \
            self.crop['bottom'] > 0

        self.adaptive = bool(adaptive)
        self.fit_in = bool(fit_in)

        self.width = width == "orig" and "orig" or self.int_or_0(width)
        self.height = height == "orig" and "orig" or self.int_or_0(height)
        self.horizontal_flip = bool(horizontal_flip)
        self.vertical_flip = bool(vertical_flip)
        self.halign = halign or 'center'
        self.valign = valign or 'middle'
        self.smart = bool(smart)

        if filters is None:
            filters = []

        self.filters = filters
        self.image_url = image
        self.url = url
        self.detection_error = None
        self.quality = quality
        self.buffer = None

        if focal_points is None:
            focal_points = []

        self.focal_points = focal_points
        self.hash = hash
        self.prevent_result_storage = False
        self.unsafe = unsafe == 'unsafe' or unsafe is True
        self.format = None
        self.accepts_webp = accepts_webp
        self.max_bytes = None

        if request:
            if request.query:
                self.image_url += '?%s' % request.query
            self.url = request.path
            self.accepts_webp = 'image/webp' in request.headers.get('Accept', '')
            self.image_url = Url.encode_url(self.image_url.encode('utf-8'))

    def int_or_0(self, value):
        return 0 if value is None else int(value)


class ContextImporter:
    def __init__(self, context, importer):
        self.context = context
        self.importer = importer

        self.engine = None
        if importer.engine:
            self.engine = importer.engine(context)

        self.storage = None
        if importer.storage:
            self.storage = importer.storage(context)

        self.result_storage = None
        if importer.result_storage:
            self.result_storage = importer.result_storage(context)

        self.upload_photo_storage = None
        if importer.upload_photo_storage:
            self.upload_photo_storage = importer.upload_photo_storage(context)

        self.loader = importer.loader
        self.detectors = importer.detectors
        self.filters = importer.filters

########NEW FILE########
__FILENAME__ = crypto
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import base64
import hashlib
import hmac

from Crypto.Cipher import AES

from thumbor.url import Url


class Cryptor(object):
    def __init__(self, security_key):
        self.security_key = (security_key * 16)[:16]

    def encrypt(self,
                width,
                height,
                smart,
                adaptive,
                fit_in,
                flip_horizontal,
                flip_vertical,
                halign,
                valign,
                trim,
                crop_left,
                crop_top,
                crop_right,
                crop_bottom,
                filters,
                image):

        generated_url = Url.generate_options(
            width=width,
            height=height,
            smart=smart,
            meta=False,
            adaptive=adaptive,
            fit_in=fit_in,
            horizontal_flip=flip_horizontal,
            vertical_flip=flip_vertical,
            halign=halign,
            valign=valign,
            trim=trim,
            crop_left=crop_left,
            crop_top=crop_top,
            crop_right=crop_right,
            crop_bottom=crop_bottom,
            filters=filters
        )

        url = "%s/%s" % (generated_url, hashlib.md5(image).hexdigest())

        pad = lambda s: s + (16 - len(s) % 16) * "{"
        cipher = AES.new(self.security_key)
        encrypted = base64.urlsafe_b64encode(cipher.encrypt(pad(url.encode('utf-8'))))

        return encrypted

    def get_options(self, encrypted_url_part, image_url):
        try:
            opt = self.decrypt(encrypted_url_part)
        except ValueError:
            opt = None

        if not opt and not self.security_key and self.context.config.STORES_CRYPTO_KEY_FOR_EACH_IMAGE:
            security_key = self.storage.get_crypto(image_url)

            if security_key is not None:
                cr = Cryptor(security_key)
                try:
                    opt = cr.decrypt(encrypted_url_part)
                except ValueError:
                    opt = None

        if opt is None:
            return None

        image_hash = opt and opt.get('image_hash')
        image_hash = image_hash[1:] if image_hash and image_hash.startswith('/') else image_hash

        path_hash = hashlib.md5(image_url.encode('utf-8')).hexdigest()

        if not image_hash or image_hash != path_hash:
            return None

        opt['image'] = image_url
        opt['hash'] = opt['image_hash']
        del opt['image_hash']

        return opt

    def decrypt(self, encrypted):
        cipher = AES.new(self.security_key)

        try:
            debased = base64.urlsafe_b64decode(encrypted.encode("utf-8"))
            decrypted = cipher.decrypt(debased).rstrip('{')
        except TypeError:
            return None

        result = Url.parse_decrypted('/%s' % decrypted)

        result['image_hash'] = result['image']
        del result['image']

        return result


class Signer:
    def __init__(self, security_key):
        if isinstance(security_key, unicode):
            security_key = security_key.encode('utf-8')
        self.security_key = security_key

    def validate(self, actual_signature, url):
        url_signature = self.signature(url)
        return url_signature == actual_signature

    def signature(self, url):
        return base64.urlsafe_b64encode(hmac.new(self.security_key, unicode(url).encode('utf-8'), hashlib.sha1).digest())

########NEW FILE########
__FILENAME__ = local_detector
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from os.path import join, dirname, abspath, isabs

try:
    import cv
except ImportError:
    import cv2.cv as cv

from thumbor.point import FocalPoint
from thumbor.detectors import BaseDetector


class CascadeLoaderDetector(BaseDetector):

    def load_cascade_file(self, module_path, cascade_file_path):
        if not hasattr(self.__class__, 'cascade'):
            if isabs(cascade_file_path):
                cascade_file = cascade_file_path
            else:
                cascade_file = join(abspath(dirname(module_path)), cascade_file_path)
            self.__class__.cascade = cv.Load(cascade_file)

    def get_min_size_for(self, size):
        ratio = int(min(size) / 15)
        ratio = max(20, ratio)
        return (ratio, ratio)

    def get_features(self):
        engine = self.context.modules.engine

        mode, converted_image = engine.image_data_as_rgb(False)
        size = engine.size

        image = cv.CreateImageHeader(size, cv.IPL_DEPTH_8U, 3)
        cv.SetData(image, converted_image)

        gray = cv.CreateImage(size, 8, 1)
        convert_mode = getattr(cv, 'CV_%s2GRAY' % mode)
        cv.CvtColor(image, gray, convert_mode)

        min_size = self.get_min_size_for(size)
        haar_scale = 1.2
        min_neighbors = 3

        cv.EqualizeHist(gray, gray)

        faces = cv.HaarDetectObjects(
            gray,
            self.__class__.cascade, cv.CreateMemStorage(0),
            haar_scale, min_neighbors,
            cv.CV_HAAR_DO_CANNY_PRUNING, min_size)

        faces_scaled = []

        for ((x, y, w, h), n) in faces:
            # the input to cv.HaarDetectObjects was resized, so scale the
            # bounding box of each face and convert it to two CvPoints
            x2, y2 = (x + w), (y + h)
            faces_scaled.append(((x, y, x2 - x, y2 - y), n))

        return faces_scaled

    def detect(self, callback):
        features = self.get_features()

        if features:
            for square, neighbors in features:
                self.context.request.focal_points.append(FocalPoint.from_square(*square))
            callback()
        else:
            self.next(callback)

########NEW FILE########
__FILENAME__ = queued_complete_detector
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com


from thumbor.detectors.queued_detector import QueuedDetector


class Detector(QueuedDetector):
    detection_type = 'all'

########NEW FILE########
__FILENAME__ = queued_face_detector
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com


from thumbor.detectors.queued_detector import QueuedDetector


class Detector(QueuedDetector):
    detection_type = 'face'

########NEW FILE########
__FILENAME__ = queued_feature_detector
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com


from thumbor.detectors.queued_detector import QueuedDetector


class Detector(QueuedDetector):
    detection_type = 'feature'

########NEW FILE########
__FILENAME__ = pil
# -*- coding: utf-8 -*-
#   Copyright (C) 2012, Almar Klein, Ant1, Marius van Voorden
#
#   This code is subject to the (new) BSD license:
#
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the <organization> nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

""" Module images2gif

Provides functionality for reading and writing animated GIF images.
Use writeGif to write a series of numpy arrays or PIL images as an
animated GIF. Use readGif to read an animated gif as a series of numpy
arrays.

Note that since July 2004, all patents on the LZW compression patent have
expired. Therefore the GIF format may now be used freely.

Acknowledgements
----------------

Many thanks to Ant1 for:
* noting the use of "palette=PIL.Image.ADAPTIVE", which significantly
  improves the results.
* the modifications to save each image with its own palette, or optionally
  the global palette (if its the same).

Many thanks to Marius van Voorden for porting the NeuQuant quantization
algorithm of Anthony Dekker to Python (See the NeuQuant class for its
license).

Many thanks to Alex Robinson for implementing the concept of subrectangles,
which (depening on image content) can give a very significant reduction in
file size.

This code is based on gifmaker (in the scripts folder of the source
distribution of PIL)


Usefull links
-------------
  * http://tronche.com/computer-graphics/gif/
  * http://en.wikipedia.org/wiki/Graphics_Interchange_Format
  * http://www.w3.org/Graphics/GIF/spec-gif89a.txt

"""
# todo: This module should be part of imageio (or at least based on)

import os

try:
    import PIL
    from PIL import Image
    from PIL.GifImagePlugin import getheader, getdata
except ImportError:
    PIL = None

try:
    import numpy as np
except ImportError:
    np = None


def get_cKDTree():
    try:
        from scipy.spatial import cKDTree
    except ImportError:
        cKDTree = None
    return cKDTree


# getheader gives a 87a header and a color palette (two elements in a list).
# getdata()[0] gives the Image Descriptor up to (including) "LZW min code size".
# getdatas()[1:] is the image data itself in chuncks of 256 bytes (well
# technically the first byte says how many bytes follow, after which that
# amount (max 255) follows).

def checkImages(images):
    """ checkImages(images)
    Check numpy images and correct intensity range etc.
    The same for all movie formats.
    """
    # Init results
    images2 = []

    for im in images:
        if PIL and isinstance(im, PIL.Image.Image):
            # We assume PIL images are allright
            images2.append(im)

        elif np and isinstance(im, np.ndarray):
            # Check and convert dtype
            if im.dtype == np.uint8:
                images2.append(im)  # Ok
            elif im.dtype in [np.float32, np.float64]:
                im = im.copy()
                im[im < 0] = 0
                im[im > 1] = 1
                im *= 255
                images2.append(im.astype(np.uint8))
            else:
                im = im.astype(np.uint8)
                images2.append(im)
            # Check size
            if im.ndim == 2:
                pass  # ok
            elif im.ndim == 3:
                if im.shape[2] not in [3, 4]:
                    raise ValueError('This array can not represent an image.')
            else:
                raise ValueError('This array can not represent an image.')
        else:
            raise ValueError('Invalid image type: ' + str(type(im)))

    # Done
    return images2


def intToBin(i):
    """ Integer to two bytes """
    # devide in two parts (bytes)
    i1 = i % 256
    i2 = int(i / 256)
    # make string (little endian)
    return chr(i1) + chr(i2)


class GifWriter:
    """ GifWriter()

    Class that contains methods for helping write the animated GIF file.

    """

    def getheaderAnim(self, im):
        """ getheaderAnim(im)

        Get animation header. To replace PILs getheader()[0]

        """
        bb = "GIF89a"
        bb += intToBin(im.size[0])
        bb += intToBin(im.size[1])
        bb += "\x87\x00\x00"
        return bb

    def getImageDescriptor(self, im, xy=None):
        """ getImageDescriptor(im, xy=None)

        Used for the local color table properties per image.
        Otherwise global color table applies to all frames irrespective of
        whether additional colors comes in play that require a redefined
        palette. Still a maximum of 256 color per frame, obviously.

        Written by Ant1 on 2010-08-22
        Modified by Alex Robinson in Janurari 2011 to implement subrectangles.

        """

        # Defaule use full image and place at upper left
        if xy is None:
            xy = (0, 0)

        # Image separator,
        bb = '\x2C'

        # Image position and size
        bb += intToBin(xy[0])  # Left position
        bb += intToBin(xy[1])  # Top position
        bb += intToBin(im.size[0])  # image width
        bb += intToBin(im.size[1])  # image height

        # packed field: local color table flag1, interlace0, sorted table0,
        # reserved00, lct size111=7=2^(7+1)=256.

        bb += '\x87'

        # LZW minimum size code now comes later, begining of [image data] blocks
        return bb

    def getAppExt(self, loops=float('inf')):
        """ getAppExt(loops=float('inf'))

        Application extention. This part specifies the amount of loops.
        If loops is 0 or inf, it goes on infinitely.

        """

        if loops == 0 or loops == float('inf'):
            loops = 2 ** 16 - 1
            #bb = "" # application extension should not be used
                    # (the extension interprets zero loops
                    # to mean an infinite number of loops)
                    # Mmm, does not seem to work
        if True:
            bb = "\x21\xFF\x0B"  # application extension
            bb += "NETSCAPE2.0"
            bb += "\x03\x01"
            bb += intToBin(loops)
            bb += '\x00'  # end
        return bb

    def getGraphicsControlExt(self, duration=0.1, dispose=2):
        """ getGraphicsControlExt(duration=0.1, dispose=2)

        Graphics Control Extension. A sort of header at the start of
        each image. Specifies duration and transparancy.

        Dispose
        -------
          * 0 - No disposal specified.
          * 1 - Do not dispose. The graphic is to be left in place.
          * 2 - Restore to background color. The area used by the graphic
            must be restored to the background color.
          * 3 - Restore to previous. The decoder is required to restore the
            area overwritten by the graphic with what was there prior to
            rendering the graphic.
          * 4-7 -To be defined.

        """

        bb = '\x21\xF9\x04'
        bb += chr((dispose & 3) << 2)  # low bit 1 == transparency,
        # 2nd bit 1 == user input , next 3 bits, the low two of which are used,
        # are dispose.
        bb += intToBin(int(duration * 100))  # in 100th of seconds
        bb += '\x00'  # no transparant color
        bb += '\x00'  # end
        return bb

    def handleSubRectangles(self, images, subRectangles):
        """ handleSubRectangles(images)

        Handle the sub-rectangle stuff. If the rectangles are given by the
        user, the values are checked. Otherwise the subrectangles are
        calculated automatically.

        """

        if isinstance(subRectangles, (tuple, list)):
            # xy given directly

            # Check xy
            xy = subRectangles
            if xy is None:
                xy = (0, 0)
            if hasattr(xy, '__len__'):
                if len(xy) == len(images):
                    xy = [xxyy for xxyy in xy]
                else:
                    raise ValueError("len(xy) doesn't match amount of images.")
            else:
                xy = [xy for im in images]
            xy[0] = (0, 0)

        else:
            # Calculate xy using some basic image processing

            # Check Numpy
            if np is None:
                raise RuntimeError("Need Numpy to use auto-subRectangles.")

            # First make numpy arrays if required
            for i in range(len(images)):
                im = images[i]
                if isinstance(im, Image.Image):
                    tmp = im.convert()  # Make without palette
                    a = np.asarray(tmp)
                    if len(a.shape) == 0:
                        raise MemoryError("Too little memory to convert PIL image to array")
                    images[i] = a

            # Determine the sub rectangles
            images, xy = self.getSubRectangles(images)

        # Done
        return images, xy

    def getSubRectangles(self, ims):
        """ getSubRectangles(ims)

        Calculate the minimal rectangles that need updating each frame.
        Returns a two-element tuple containing the cropped images and a
        list of x-y positions.

        Calculating the subrectangles takes extra time, obviously. However,
        if the image sizes were reduced, the actual writing of the GIF
        goes faster. In some cases applying this method produces a GIF faster.

        """

        # Check image count
        if len(ims) < 2:
            return ims, [(0, 0) for i in ims]

        # We need numpy
        if np is None:
            raise RuntimeError("Need Numpy to calculate sub-rectangles. ")

        # Prepare
        ims2 = [ims[0]]
        xy = [(0, 0)]
        #t0 = time.time()

        # Iterate over images
        prev = ims[0]
        for im in ims[1:]:

            # Get difference, sum over colors
            diff = np.abs(im - prev)
            if diff.ndim == 3:
                diff = diff.sum(2)
            # Get begin and end for both dimensions
            X = np.argwhere(diff.sum(0))
            Y = np.argwhere(diff.sum(1))
            # Get rect coordinates
            if X.size and Y.size:
                x0, x1 = X[0], X[-1] + 1
                y0, y1 = Y[0], Y[-1] + 1
            else:  # No change ... make it minimal
                x0, x1 = 0, 2
                y0, y1 = 0, 2

            # Cut out and store
            im2 = im[y0:y1, x0:x1]
            prev = im
            ims2.append(im2)
            xy.append((x0, y0))

        # Done
        #print('%1.2f seconds to determine subrectangles of  %i images' %
        #    (time.time()-t0, len(ims2)) )
        return ims2, xy

    def convertImagesToPIL(self, images, dither, nq=0):
        """ convertImagesToPIL(images, nq=0)

        Convert images to Paletted PIL images, which can then be
        written to a single animaged GIF.

        """

        # Convert to PIL images
        images2 = []
        for im in images:
            if isinstance(im, Image.Image):
                images2.append(im)
            elif np and isinstance(im, np.ndarray):
                if im.ndim == 3 and im.shape[2] == 3:
                    im = Image.fromarray(im, 'RGB')
                elif im.ndim == 3 and im.shape[2] == 4:
                    im = Image.fromarray(im[:, :, :3], 'RGB')
                elif im.ndim == 2:
                    im = Image.fromarray(im, 'L')
                images2.append(im)

        # Convert to paletted PIL images
        images, images2 = images2, []

        # Adaptive PIL algorithm
        AD = Image.ADAPTIVE
        for im in images:
            im = im.convert('P', palette=AD, dither=dither)
            images2.append(im)

        # Done
        return images2

    def writeGifToFile(self, fp, images, durations, loops, xys, disposes):
        """ writeGifToFile(fp, images, durations, loops, xys, disposes)

        Given a set of images writes the bytes to the specified stream.

        """
        # Obtain palette for all images and count each occurance
        palettes, occur = [], []
        for im in images:
            header, usedPaletteColors = getheader(im)
            palettes.append(header[-1])  # Last part of the header is the frame palette
        for palette in palettes:
            occur.append(palettes.count(palette))

        # Select most-used palette as the global one (or first in case no max)
        globalPalette = palettes[occur.index(max(occur))]

        # Init
        frames = 0
        firstFrame = True

        for im, palette in zip(images, palettes):

            if firstFrame:
                # Write header

                # Gather info
                header = self.getheaderAnim(im)
                appext = self.getAppExt(loops)

                # Write
                fp.write(header)
                fp.write(globalPalette)
                fp.write(appext)

                # Next frame is not the first
                firstFrame = False

            if True:
                # Write palette and image data

                # Gather info
                data = getdata(im)

                imdes, data = data[0], data[1:]
                graphext = self.getGraphicsControlExt(durations[frames], disposes[frames])
                # Make image descriptor suitable for using 256 local color palette
                lid = self.getImageDescriptor(im, xys[frames])

                # Write local header
                if (palette != globalPalette) or (disposes[frames] != 2):
                    # Use local color palette
                    fp.write(graphext)
                    fp.write(lid)  # write suitable image descriptor
                    fp.write(palette)  # write local color table
                    fp.write('\x08')  # LZW minimum size code
                else:
                    # Use global color palette
                    fp.write(graphext)
                    fp.write(imdes)  # write suitable image descriptor

                for d in data:
                    fp.write(d)

            # Prepare for next round
            frames = frames + 1

        fp.write(";")  # end gif
        return frames


## Exposed functions
def writeGif(
        filename, images, duration=0.1, repeat=True, dither=False,
        nq=0, subRectangles=True, dispose=None):
    """ writeGif(filename, images, duration=0.1, repeat=True, dither=False,
                    nq=0, subRectangles=True, dispose=None)

    Write an animated gif from the specified images.

    Parameters
    ----------
    filename : string
        The name of the file to write the image to.
    images : list
        Should be a list consisting of PIL images or numpy arrays.
        The latter should be between 0 and 255 for integer types, and
        between 0 and 1 for float types.
    duration : scalar or list of scalars
        The duration for all frames, or (if a list) for each frame.
    repeat : bool or integer
        The amount of loops. If True, loops infinitetely.
    dither : bool
        Whether to apply dithering
    nq : integer
        If nonzero, applies the NeuQuant quantization algorithm to create
        the color palette. This algorithm is superior, but slower than
        the standard PIL algorithm. The value of nq is the quality
        parameter. 1 represents the best quality. 10 is in general a
        good tradeoff between quality and speed. When using this option,
        better results are usually obtained when subRectangles is False.
    subRectangles : False, True, or a list of 2-element tuples
        Whether to use sub-rectangles. If True, the minimal rectangle that
        is required to update each frame is automatically detected. This
        can give significant reductions in file size, particularly if only
        a part of the image changes. One can also give a list of x-y
        coordinates if you want to do the cropping yourself. The default
        is True.
    dispose : int
        How to dispose each frame. 1 means that each frame is to be left
        in place. 2 means the background color should be restored after
        each frame. 3 means the decoder should restore the previous frame.
        If subRectangles==False, the default is 2, otherwise it is 1.

    """

    # Check PIL
    if PIL is None:
        raise RuntimeError("Need PIL to write animated gif files.")

    # Check images
    images = checkImages(images)

    # Instantiate writer object
    gifWriter = GifWriter()

    # Check loops
    if repeat is False:
        loops = 1
    elif repeat is True:
        loops = 0  # zero means infinite
    else:
        loops = int(repeat)

    # Check duration
    if hasattr(duration, '__len__'):
        if len(duration) == len(images):
            duration = [d for d in duration]
        else:
            raise ValueError("len(duration) doesn't match amount of images.")
    else:
        duration = [duration for im in images]

    # Check subrectangles
    if subRectangles:
        images, xy = gifWriter.handleSubRectangles(images, subRectangles)
        defaultDispose = 1  # Leave image in place
    else:
        # Normal mode
        xy = [(0, 0) for im in images]
        defaultDispose = 2  # Restore to background color.

    # Check dispose
    if dispose is None:
        dispose = defaultDispose
    if hasattr(dispose, '__len__'):
        if len(dispose) != len(images):
            raise ValueError("len(xy) doesn't match amount of images.")
    else:
        dispose = [dispose for im in images]

    # Make images in a format that we can write easy
    images = gifWriter.convertImagesToPIL(images, dither, nq)

    # Write
    fp = open(filename, 'wb')
    try:
        gifWriter.writeGifToFile(fp, images, duration, loops, xy, dispose)
    finally:
        fp.close()


def readGif(filename, asNumpy=True):
    """ readGif(filename, asNumpy=True)

    Read images from an animated GIF file.  Returns a list of numpy
    arrays, or, if asNumpy is false, a list if PIL images.

    """

    # Check PIL
    if PIL is None:
        raise RuntimeError("Need PIL to read animated gif files.")

    # Check Numpy
    if np is None:
        raise RuntimeError("Need Numpy to read animated gif files.")

    # Check whether it exists
    if not os.path.isfile(filename):
        raise IOError('File not found: ' + str(filename))

    # Load file using PIL
    pilIm = PIL.Image.open(filename)
    pilIm.seek(0)

    # Read all images inside
    images = []
    try:
        while True:
            # Get image as numpy array
            tmp = pilIm.convert()  # Make without palette
            a = np.asarray(tmp)
            if len(a.shape) == 0:
                raise MemoryError("Too little memory to convert PIL image to array")
            # Store, and next
            images.append(a)
            pilIm.seek(pilIm.tell() + 1)
    except EOFError:
        pass

    # Convert to normal PIL images if needed
    if not asNumpy:
        images2 = images
        images = []
        for im in images2:
            images.append(PIL.Image.fromarray(im))

    # Done
    return images

########NEW FILE########
__FILENAME__ = json_engine
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import json

from thumbor.engines import BaseEngine


class JSONEngine(BaseEngine):

    def __init__(self, engine, path, callback_name=None):
        super(JSONEngine, self).__init__(engine.context)
        self.engine = engine
        self.width, self.height = self.engine.size
        self.path = path
        self.callback_name = callback_name
        self.operations = []
        self.focal_points = []
        self.refresh_image()

    def refresh_image(self):
        self.image = self.engine.image

    @property
    def size(self):
        return self.engine.size

    def resize(self, width, height):
        self.operations.append({
            "type": "resize",
            "width": width,
            "height": height
        })
        self.engine.resize(width, height)
        self.refresh_image()

    def crop(self, left, top, right, bottom):
        self.operations.append({
            "type": "crop",
            "left": left,
            "top": top,
            "right": right,
            "bottom": bottom
        })
        self.engine.crop(left, top, right, bottom)
        self.refresh_image()

    def focus(self, points):
        for point in points:
            self.focal_points.append(point.to_dict())

    def flip_vertically(self):
        self.operations.append({"type": "flip_vertically"})

    def flip_horizontally(self):
        self.operations.append({"type": "flip_horizontally"})

    def get_target_dimensions(self):
        width = self.width
        height = self.height

        for operation in self.operations:
            if operation['type'] == 'crop':
                width = operation['right'] - operation['left']
                height = operation['bottom'] - operation['top']

            if operation['type'] == 'resize':
                width = operation['width']
                height = operation['height']

        return (width, height)

    def gen_image(self, size, color):
        return self.engine.gen_image(size, color)

    def create_image(self, buffer):
        return self.engine.create_image(buffer)

    def draw_rectangle(self, x, y, width, height):
        return self.engine.draw_rectangle(x, y, width, height)

    def rotate(self, degrees):
        return self.engine.rotate(degrees)

    def read_multiple(self, images, extension=None):
        return self.engine.read_multiple(images, extension)

    def paste(self, other_engine, pos, merge=True):
        return self.engine.paste(other_engine, pos, merge)

    def enable_alpha(self):
        return self.engine.enable_alpha()

    def strip_icc(self):
        return self.engine.strip_icc()

    def get_image_mode(self):
        return self.engine.get_image_mode()

    def get_image_data(self):
        return self.engine.get_image_data()

    def set_image_data(self, data):
        return self.engine.set_image_data(data)

    def image_data_as_rgb(self, update_image=True):
        return self.engine.image_data_as_rgb(update_image)

    def convert_to_grayscale(self):
        pass

    def read(self, extension, quality):
        target_width, target_height = self.get_target_dimensions()
        thumbor_json = {
            "thumbor": {
                "source": {
                    "url": self.path,
                    "width": self.width,
                    "height": self.height,
                },
                "operations": self.operations,
                "target": {
                    "width": target_width,
                    "height": target_height
                }
            }
        }

        if self.focal_points:
            thumbor_json["thumbor"]["focal_points"] = self.focal_points

        thumbor_json = json.dumps(thumbor_json)

        if self.callback_name:
            return "%s(%s);" % (self.callback_name, thumbor_json)

        return thumbor_json

########NEW FILE########
__FILENAME__ = pil
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import os
from tempfile import mkstemp
from subprocess import Popen, PIPE
from io import BytesIO

from PIL import Image, ImageFile, ImageDraw, ImageSequence

from thumbor.engines import BaseEngine
from thumbor.engines.extensions.pil import GifWriter
from thumbor.utils import logger, deprecated

try:
    from thumbor.ext.filters import _composite
    FILTERS_AVAILABLE = True
except ImportError:
    FILTERS_AVAILABLE = False


FORMATS = {
    '.jpg': 'JPEG',
    '.jpeg': 'JPEG',
    '.gif': 'GIF',
    '.png': 'PNG',
    '.webp': 'WEBP'
}

ImageFile.MAXBLOCK = 2 ** 25

if hasattr(ImageFile, 'IGNORE_DECODING_ERRORS'):
    ImageFile.IGNORE_DECODING_ERRORS = True


class Engine(BaseEngine):

    def gen_image(self, size, color):
        img = Image.new("RGBA", size, color)
        return img

    def create_image(self, buffer):
        img = Image.open(BytesIO(buffer))
        self.icc_profile = img.info.get('icc_profile')
        self.transparency = img.info.get('transparency')
        self.exif = img.info.get('exif')

        if self.context.config.ALLOW_ANIMATED_GIFS and self.extension == '.gif':
            frames = []
            for frame in ImageSequence.Iterator(img):
                frames.append(frame.convert('P'))
            img.seek(0)
            return frames

        return img

    def draw_rectangle(self, x, y, width, height):
        d = ImageDraw.Draw(self.image)
        d.rectangle([x, y, x + width, y + height])

        del d

    def resize(self, width, height):
        self.image = self.image.resize((int(width), int(height)), Image.ANTIALIAS)

    def crop(self, left, top, right, bottom):
        self.image = self.image.crop((
            int(left),
            int(top),
            int(right),
            int(bottom)
        ))

    def rotate(self, degrees):
        self.image = self.image.rotate(degrees)

    def flip_vertically(self):
        self.image = self.image.transpose(Image.FLIP_TOP_BOTTOM)

    def flip_horizontally(self):
        self.image = self.image.transpose(Image.FLIP_LEFT_RIGHT)

    def read(self, extension=None, quality=None):
        #returns image buffer in byte format.
        img_buffer = BytesIO()

        ext = extension or self.extension

        options = {
            'quality': quality
        }

        if ext == '.jpg' or ext == '.jpeg':
            options['optimize'] = True
            options['progressive'] = True

            if self.image.mode in ['L']:
                self.image = self.image.convert('RGB')
            else:
                if self.extension == '.jpg':
                    quantization = getattr(self.image, 'quantization', None)
                    if quality is None and quantization and 2 <= len(quantization) <= 4:
                        options['quality'] = 'keep'

        if options['quality'] is None:
            options['quality'] = self.context.config.QUALITY

        if self.icc_profile is not None:
            options['icc_profile'] = self.icc_profile

        if self.context.config.PRESERVE_EXIF_INFO:
            if self.exif is not None:
                options['exif'] = self.exif

        if self.image.mode == 'P' and self.transparency:
            options['transparency'] = self.transparency

        try:
            if ext == '.webp':
                if self.image.mode not in ['RGB', 'RGBA']:
                    mode = None
                    if self.image.mode != 'P':
                        mode = 'RGBA' if self.image.mode[-1] == 'A' else 'RGB'
                    self.image = self.image.convert(mode)

            if ext == '.png' and self.image.mode == 'CMYK':
                self.image = self.image.convert('RGBA')

            self.image.save(img_buffer, FORMATS[ext], **options)
        except IOError:
            logger.exception('Could not save as improved image, consider to increase ImageFile.MAXBLOCK')
            self.image.save(img_buffer, FORMATS[ext])
        except KeyError:
            logger.exception('Image format not found in PIL: %s' % ext)

            #extension is not present or could not help determine format => force JPEG
            if self.image.mode in ['P', 'RGBA', 'LA']:
                self.image.format = FORMATS['.png']
                self.image.save(img_buffer, FORMATS['.png'])
            else:
                self.image.format = FORMATS['.jpg']
                self.image.save(img_buffer, FORMATS['.jpg'])

        results = img_buffer.getvalue()
        img_buffer.close()
        return results

    def read_multiple(self, images, extension=None):
        gifWriter = GifWriter()
        img_buffer = BytesIO()

        duration = []
        converted_images = []
        xy = []
        dispose = []

        for im in images:
            duration.append(float(im.info.get('duration', 80)) / 1000)
            converted_images.append(im.convert("RGB"))
            xy.append((0, 0))
            dispose.append(1)

        loop = int(self.image.info.get('loop', 1))

        images = gifWriter.convertImagesToPIL(converted_images, False, None)
        gifWriter.writeGifToFile(img_buffer, images, duration, loop, xy, dispose)

        results = img_buffer.getvalue()
        img_buffer.close()

        tmp_fd, tmp_file_path = mkstemp()
        f = os.fdopen(tmp_fd, "w")
        f.write(results)
        f.close()

        popen = Popen("gifsicle --colors 256 %s" % tmp_file_path, shell=True, stdout=PIPE)
        pipe = popen.stdout
        pipe_output = pipe.read()
        pipe.close()

        if popen.wait() == 0:
            results = pipe_output

        os.remove(tmp_file_path)

        return results

    @deprecated("Use image_data_as_rgb instead.")
    def get_image_data(self):
        return self.image.tostring()

    def set_image_data(self, data):
        self.image.fromstring(data)

    @deprecated("Use image_data_as_rgb instead.")
    def get_image_mode(self):
        return self.image.mode

    def image_data_as_rgb(self, update_image=True):
        converted_image = self.image
        if converted_image.mode not in ['RGB', 'RGBA']:
            if 'A' in converted_image.mode:
                converted_image = converted_image.convert('RGBA')
            else:
                converted_image = converted_image.convert('RGB')
        if update_image:
            self.image = converted_image
        return converted_image.mode, converted_image.tostring()

    def convert_to_grayscale(self):
        if 'A' in self.image.mode:
            self.image = self.image.convert('LA')
        else:
            self.image = self.image.convert('L')

    def paste(self, other_engine, pos, merge=True):
        if merge and not FILTERS_AVAILABLE:
            raise RuntimeError(
                'You need filters enabled to use paste with merge. Please reinstall ' +
                'thumbor with proper compilation of its filters.')

        self.enable_alpha()
        other_engine.enable_alpha()

        image = self.image
        other_image = other_engine.image

        if merge:
            sz = self.size
            other_size = other_engine.size
            mode, data = self.image_data_as_rgb()
            other_mode, other_data = other_engine.image_data_as_rgb()
            imgdata = _composite.apply(
                mode, data, sz[0], sz[1],
                other_data, other_size[0], other_size[1], pos[0], pos[1])
            self.set_image_data(imgdata)
        else:
            image.paste(other_image, pos)

    def enable_alpha(self):
        if self.image.mode != 'RGBA':
            self.image = self.image.convert('RGBA')

    def strip_icc(self):
        self.icc_profile = None

########NEW FILE########
__FILENAME__ = file
#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging, logging.handlers, json
from thumbor import __version__

class ErrorHandler(object):
    def __init__(self, config):

        file = config.ERROR_FILE_LOGGER
        if not file:
            raise RuntimeError(
                "If you set USE_CUSTOM_ERROR_HANDLING to True, and you are using thumbor_file_logger.logger, " +
                "then you must specify the file path to log to with the ERROR_FILE_LOGGER configuration."
            )


        self.logger = logging.getLogger('error_handler')
        self.logger.setLevel(logging.ERROR)
        self.logger.addHandler(logging.handlers.WatchedFileHandler(config.ERROR_FILE_LOGGER))
            
    def handle_error(self, context, handler, exception):
        req = handler.request
        extra = {
            'thumbor-version': __version__
        }
        extra.update({
            'Headers': req.headers
        })
        cookies_header = extra.get('Headers', {}).get('Cookie', {})
        if isinstance(cookies_header, basestring):
            cookies = {}
            for cookie in cookies_header.split(';'):
                if not cookie:
                    continue
                values = cookie.strip().split('=')
                key, val = values[0], "".join(values[1:])
                cookies[key] = val
        else:
            cookies = cookies_header
        extra['Headers']['Cookie'] = cookies

        data = {
            'Http': {
                'url': req.full_url(),
                'method': req.method,
                'data': req.arguments,
                'body': req.body,
                'query_string': req.query
            },
            'interfaces.User': {
                'ip': req.remote_ip,
            },
            'exception': str(exception),
            'extra': extra
        }

        self.logger.error(json.dumps(data))

########NEW FILE########
__FILENAME__ = sentry
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import pkgutil
import pkg_resources

from thumbor import __version__


class ErrorHandler(object):
    def __init__(self, config, client=None):
        import raven

        dsn = config.SENTRY_DSN_URL
        if not dsn:
            raise RuntimeError(
                "If you set USE_CUSTOM_ERROR_HANDLING to True, and you are using thumbor.error_handlers.sentry, " +
                "then you must specify the Sentry DSN using the SENTRY_DSN_URL configuration."
            )

        self.sentry = client or raven.Client(dsn)
        self.modules = self.get_modules()

    def get_modules(self):
        resolved = {}
        modules = [mod[1] for mod in tuple(pkgutil.iter_modules())]
        for module in modules:
            try:
                res_mod = pkg_resources.get_distribution(module)
                if res_mod is not None:
                    resolved[module] = res_mod.version
            except pkg_resources.DistributionNotFound:
                pass

        return resolved

    def handle_error(self, context, handler, exception):
        req = handler.request

        extra = {
            'thumbor-version': __version__
        }

        extra.update({
            'Headers': req.headers
        })

        cookies_header = extra.get('Headers', {}).get('Cookie', {})

        if isinstance(cookies_header, basestring):
            cookies = {}
            for cookie in cookies_header.split(';'):
                if not cookie:
                    continue
                values = cookie.strip().split('=')
                key, val = values[0], "".join(values[1:])
                cookies[key] = val
        else:
            cookies = cookies_header

        extra['Headers']['Cookie'] = cookies

        data = {
            'sentry.interfaces.Http': {
                'url': req.full_url(),
                'method': req.method,
                'data': req.arguments,
                'body': req.body,
                'query_string': req.query
            },
            'sentry.interfaces.User': {
                'ip': req.remote_ip,
            },
            'modules': self.modules
        }
        self.sentry.captureException(exception, extra=extra, data=data)

########NEW FILE########
__FILENAME__ = blur
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import math

from thumbor.filters import BaseFilter, filter_method
from thumbor.ext.filters import _convolution

MAX_RADIUS = 150


class Filter(BaseFilter):
    """
        Usage: /filters:blur(<radius> [, <sigma>])
        Examples of use:
            /filters:blur(1)/
            /filters:blur(4)/
            /filters:blur(4, 2)/
    """

    def generate_1d_matrix(self, sigma, radius):
        matrix_size = (radius * 2) + 1
        matrix = []
        two_sigma_squared = float(2 * sigma * sigma)
        for x in xrange(matrix_size):
            adj_x = x - radius
            exp = math.e ** -(((adj_x * adj_x)) / two_sigma_squared)
            matrix.append(exp / math.sqrt(two_sigma_squared * math.pi))
        return tuple(matrix), matrix_size

    @filter_method(BaseFilter.PositiveNumber, BaseFilter.DecimalNumber)
    def blur(self, radius, sigma=0):
        if sigma == 0:
            sigma = radius
        if radius > MAX_RADIUS:
            radius = MAX_RADIUS
        matrix, matrix_size = self.generate_1d_matrix(sigma, radius)
        mode, data = self.engine.image_data_as_rgb()
        imgdata = _convolution.apply(mode, data, self.engine.size[0], self.engine.size[1], matrix, matrix_size, True)
        imgdata = _convolution.apply(mode, imgdata, self.engine.size[0], self.engine.size[1], matrix, 1, True)
        self.engine.set_image_data(imgdata)

########NEW FILE########
__FILENAME__ = brightness
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from thumbor.filters import BaseFilter, filter_method
from thumbor.ext.filters import _brightness


class Filter(BaseFilter):

    @filter_method(BaseFilter.Number)
    def brightness(self, value):
        mode, data = self.engine.image_data_as_rgb()
        imgdata = _brightness.apply(mode, value, data)
        self.engine.set_image_data(imgdata)

########NEW FILE########
__FILENAME__ = contrast
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from thumbor.filters import BaseFilter, filter_method
from thumbor.ext.filters import _contrast


class Filter(BaseFilter):

    @filter_method(BaseFilter.Number)
    def contrast(self, value):
        mode, data = self.engine.image_data_as_rgb()
        imgdata = _contrast.apply(mode, value, data)
        self.engine.set_image_data(imgdata)

########NEW FILE########
__FILENAME__ = convolution
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from thumbor.filters import BaseFilter, filter_method
from thumbor.ext.filters import _convolution


class Filter(BaseFilter):
    """
        Usage: /filters:convolution(<semicolon separated matrix items>, <number of columns in matrix>, <should normalize boolean>)
        Example of blur filter: /filters:convolution(1;2;1;2;4;2;1;2;1,3,true)/
    """

    @filter_method(r'(?:[-]?[\d]+\.?[\d]*[;])*(?:[-]?[\d]+\.?[\d]*)', BaseFilter.PositiveNumber, BaseFilter.Boolean)
    def convolution(self, matrix, columns, should_normalize=True):
        matrix = tuple(matrix.split(';'))
        mode, data = self.engine.image_data_as_rgb()
        imgdata = _convolution.apply(mode, data, self.engine.size[0], self.engine.size[1], matrix, columns, should_normalize)
        self.engine.set_image_data(imgdata)

########NEW FILE########
__FILENAME__ = equalize
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from thumbor.filters import BaseFilter, filter_method
from thumbor.ext.filters import _equalize


class Filter(BaseFilter):

    @filter_method()
    def equalize(self):
        mode, data = self.engine.image_data_as_rgb()
        imgdata = _equalize.apply(mode, data)
        self.engine.set_image_data(imgdata)

########NEW FILE########
__FILENAME__ = extract_focal
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import re

from thumbor.filters import BaseFilter, filter_method, PHASE_PRE_LOAD
from thumbor.url import Url
from thumbor.point import FocalPoint


MAX_LEVEL = 10


class Filter(BaseFilter):
    phase = PHASE_PRE_LOAD

    domain_regex = re.compile(r'^(https?://)?.*?/')
    url_regex = re.compile(Url.regex())

    def parse_url(self, url):
        level = 0
        while level < MAX_LEVEL:
            url = self.domain_regex.sub('', url)
            result = self.url_regex.match(url)
            if not result:
                return None

            parts = result.groupdict()
            image = parts.get('image', None)

            if not (image and (parts.get('hash', None) or parts.get('unsafe', None))):
                return None

            top, right, left, bottom = parts.get('crop_top', None), parts.get('crop_right', None), parts.get('crop_left', None), parts.get('crop_bottom', None)
            if top and right and left and bottom:
                return (image, top, right, left, bottom)

            url = image
            level += 1

        return None

    @filter_method()
    def extract_focal(self):
        parts = self.parse_url(self.context.request.image_url)
        if parts:
            image, top, right, left, bottom = parts
            top, right, left, bottom = int(top), int(right), int(left), int(bottom)

            width = right - left
            height = bottom - top
            self.context.request.focal_points.append(
                FocalPoint.from_square(left, top, width, height, origin="Original Extraction")
            )
            self.context.request.image_url = image

########NEW FILE########
__FILENAME__ = fill
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from thumbor.filters import BaseFilter, filter_method
from thumbor.ext.filters import _fill


class Filter(BaseFilter):

    def get_median_color(self):
        mode, data = self.engine.image_data_as_rgb()
        r, g, b = _fill.apply(mode, data)
        return '%02x%02x%02x' % (r, g, b)

    @filter_method(r'[\w]+', BaseFilter.Boolean)
    def fill(self, color, fill_transparent=False):

        self.fill_engine = self.engine.__class__(self.context)
        bx = self.context.request.width if self.context.request.width != 0 else self.engine.size[0]
        by = self.context.request.height if self.context.request.height != 0 else self.engine.size[1]

        # if the color is 'auto'
        # we will calculate the median color of
        # all the pixels in the image and return
        if color == 'auto':
            color = self.get_median_color()

        try:
            self.fill_engine.image = self.fill_engine.gen_image((bx, by), color)
        except (ValueError, RuntimeError):
            self.fill_engine.image = self.fill_engine.gen_image((bx, by), '#%s' % color)

        ix, iy = self.engine.size

        px = (bx - ix) / 2  # top left
        py = (by - iy) / 2

        self.fill_engine.paste(self.engine, (px, py), merge=fill_transparent)
        self.engine.image = self.fill_engine.image

########NEW FILE########
__FILENAME__ = format
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from thumbor.filters import BaseFilter, filter_method
from thumbor.utils import logger


ALLOWED_FORMATS = ['png', 'jpeg', 'jpg', 'gif', 'webp']


class Filter(BaseFilter):

    @filter_method(BaseFilter.String)
    def format(self, format):
        if format.lower() not in ALLOWED_FORMATS:
            logger.debug('Format not allowed: %s' % format.lower())
            self.context.request.format = None
        else:
            logger.debug('Format specified: %s' % format.lower())
            self.context.request.format = format.lower()

########NEW FILE########
__FILENAME__ = frame
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from thumbor.ext.filters import _nine_patch
from thumbor.filters import BaseFilter, filter_method
from os.path import splitext


class Filter(BaseFilter):
    regex = r'(?:frame\((?P<url>.*?))'

    def on_image_ready(self, buffer):
        self.nine_patch_engine.load(buffer, self.extension)
        self.nine_patch_engine.enable_alpha()
        self.engine.enable_alpha()

        nine_patch_mode, nine_patch_data = self.nine_patch_engine.image_data_as_rgb()
        padding = _nine_patch.get_padding(nine_patch_mode,
                                          nine_patch_data,
                                          self.nine_patch_engine.size[0],
                                          self.nine_patch_engine.size[1])

        self.handle_padding(padding)

        mode, data = self.engine.image_data_as_rgb()

        if mode != nine_patch_mode:
            raise RuntimeError('Image mode mismatch: %s != %s' % (
                mode, nine_patch_mode)
            )

        imgdata = _nine_patch.apply(mode,
                                    data,
                                    self.engine.size[0],
                                    self.engine.size[1],
                                    nine_patch_data,
                                    self.nine_patch_engine.size[0],
                                    self.nine_patch_engine.size[1])
        self.engine.set_image_data(imgdata)
        self.callback()

    def handle_padding(self, padding):
        '''Pads the image with transparent pixels if necessary.'''
        left = padding[0]
        top = padding[1]
        right = padding[2]
        bottom = padding[3]

        offset_x = 0
        offset_y = 0
        new_width = self.engine.size[0]
        new_height = self.engine.size[1]

        if left > 0:
            offset_x = left
            new_width += left
        if top > 0:
            offset_y = top
            new_height += top
        if right > 0:
            new_width += right
        if bottom > 0:
            new_height += bottom
        new_engine = self.context.modules.engine.__class__(self.context)
        new_engine.image = new_engine.gen_image((new_width, new_height), '#fff')
        new_engine.enable_alpha()
        new_engine.paste(self.engine, (offset_x, offset_y))
        self.engine.image = new_engine.image

    def on_fetch_done(self, buffer):
        self.nine_patch_engine.load(buffer, self.extension)
        self.storage.put(self.url, self.nine_patch_engine.read())
        self.storage.put_crypto(self.url)
        self.on_image_ready(buffer)

    @filter_method(BaseFilter.String, async=True)
    def frame(self, callback, url):
        self.url = url
        self.callback = callback
        self.extension = splitext(self.url)[-1].lower()
        self.nine_patch_engine = self.context.modules.engine.__class__(self.context)
        self.storage = self.context.modules.storage

        buffer = self.storage.get(self.url)
        if buffer is not None:
            self.on_image_ready(buffer)
        else:
            self.context.modules.loader.load(self.context, self.url, self.on_fetch_done)

########NEW FILE########
__FILENAME__ = grayscale
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from thumbor.filters import BaseFilter, filter_method


class Filter(BaseFilter):

    @filter_method()
    def grayscale(self):
        engine = self.context.modules.engine
        engine.convert_to_grayscale()

########NEW FILE########
__FILENAME__ = max_bytes
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from thumbor.filters import BaseFilter, filter_method


class Filter(BaseFilter):

    @filter_method(BaseFilter.PositiveNumber)
    def max_bytes(self, value):
        self.context.request.max_bytes = int(value)

########NEW FILE########
__FILENAME__ = noise
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from thumbor.filters import BaseFilter, filter_method
from thumbor.ext.filters import _noise


class Filter(BaseFilter):

    @filter_method(BaseFilter.PositiveNumber)
    def noise(self, amount):
        mode, data = self.engine.image_data_as_rgb()
        imgdata = _noise.apply(mode, amount, data)
        self.engine.set_image_data(imgdata)

########NEW FILE########
__FILENAME__ = quality
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from thumbor.filters import BaseFilter, filter_method


class Filter(BaseFilter):

    @filter_method(BaseFilter.PositiveNumber)
    def quality(self, value):
        self.context.request.quality = value

########NEW FILE########
__FILENAME__ = redeye
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from os.path import abspath, dirname, join

import cv

from thumbor.filters import BaseFilter, filter_method

FACE_ORIGIN = 'Face Detection'
CASCADE_FILE_PATH = abspath(join(dirname(__file__), 'haarcascade_eye.xml'))

MIN_SIZE = (20, 20)
HAAR_SCALE = 1.2
MIN_NEIGHBORS = 3
HAAR_FLAGS = 0
RED_THRESHOLD = 2.0


class Filter(BaseFilter):

    def get_pixels(self, image, w, h, mode):
        pixels = []

        for row in range(h):
            for col in range(w):
                pixel = cv.Get2D(image, row, col)

                pixels.append({
                    'x': col,
                    'y': row,
                    'r': pixel[mode.index('r')],
                    'g': pixel[mode.index('g')],
                    'b': pixel[mode.index('b')]
                })

        return pixels

    def filter_eyes(self, eyes):
        intersected_eyes = []

        for eye in eyes:
            #if eye in intersected_eyes: continue
            (x, y, w, h), other = eye
            for eye2 in eyes:
                (x2, y2, w2, h2), other2 = eye2
                if x == x2 and w == w2 and y == y2 and h == h2:
                    continue
                #if eye2 in intersected_eyes: continue

                if (y2 >= y and y2 + h2 <= y + h) or (y2 + h2 >= y and y2 <= y + h):
                    intersected_eyes.append(eye)
                    #intersected_eyes.append(eye2)

        return intersected_eyes

    @filter_method()
    def red_eye(self):
        self.load_cascade_file()
        faces = [face for face in self.context.request.focal_points if face.origin == 'Face Detection']
        if faces:
            engine = self.context.modules.engine
            mode, data = engine.image_data_as_rgb()
            mode = mode.lower()
            sz = engine.size
            image = cv.CreateImageHeader(sz, cv.IPL_DEPTH_8U, 3)
            cv.SetData(image, data)

            for face in faces:
                face_x = int(face.x - face.width / 2)
                face_y = int(face.y - face.height / 2)

                face_roi = (
                    int(face_x),
                    int(face_y),
                    int(face.width),
                    int(face.height)
                )

                cv.SetImageROI(image, face_roi)

                eyes = cv.HaarDetectObjects(
                    image,
                    self.cascade,
                    cv.CreateMemStorage(0),
                    HAAR_SCALE,
                    MIN_NEIGHBORS,
                    HAAR_FLAGS,
                    MIN_SIZE)

                for (x, y, w, h), other in self.filter_eyes(eyes):
                    # Set the image Region of interest to be the eye area [this reduces processing time]
                    cv.SetImageROI(image, (face_x + x, face_y + y, w, h))

                    if self.context.request.debug:
                        cv.Rectangle(
                            image,
                            (0, 0),
                            (w, h),
                            cv.RGB(255, 255, 255),
                            2,
                            8,
                            0
                        )

                    for pixel in self.get_pixels(image, w, h, mode):
                        green_blue_avg = (pixel['g'] + pixel['b']) / 2

                        if not green_blue_avg:
                            red_intensity = RED_THRESHOLD
                        else:
                            # Calculate the intensity compared to blue and green average
                            red_intensity = pixel['r'] / green_blue_avg

                        # If the red intensity is greater than 2.0, lower the value
                        if red_intensity >= RED_THRESHOLD:
                            new_red_value = (pixel['g'] + pixel['b']) / 2
                            # Insert the new red value for the pixel to the image
                            cv.Set2D(
                                image,
                                pixel['y'],
                                pixel['x'],
                                cv.RGB(new_red_value, pixel['g'], pixel['b'])
                            )

                    # Reset the image region of interest back to full image
                    cv.ResetImageROI(image)

            self.context.modules.engine.set_image_data(image.tostring())

    def load_cascade_file(self):
        if not hasattr(self.__class__, 'cascade'):
            setattr(self.__class__, 'cascade', cv.Load(CASCADE_FILE_PATH))

########NEW FILE########
__FILENAME__ = rgb
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from thumbor.filters import BaseFilter, filter_method
from thumbor.ext.filters import _rgb


class Filter(BaseFilter):

    @filter_method(BaseFilter.Number, BaseFilter.Number, BaseFilter.Number)
    def rgb(self, r, g, b):
        mode, data = self.engine.image_data_as_rgb()
        imgdata = _rgb.apply(mode, r, g, b, data)
        self.engine.set_image_data(imgdata)

########NEW FILE########
__FILENAME__ = round_corner
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from thumbor.filters import BaseFilter, filter_method
from thumbor.ext.filters import _round_corner


class Filter(BaseFilter):

    @filter_method(r'[\d]+(?:\|[\d]+)?', BaseFilter.PositiveNumber, BaseFilter.PositiveNumber, BaseFilter.PositiveNumber)
    def round_corner(self, radius, r, g, b):
        width, height = self.engine.size
        radius_parts = radius.split('|')
        a_radius = int(radius_parts[0])
        b_radius = int(radius_parts[1]) if len(radius_parts) > 1 else a_radius

        mode, data = self.engine.image_data_as_rgb()
        imgdata = _round_corner.apply(
            1, mode, a_radius, b_radius, r, g, b,
            width, height, data
        )
        self.engine.set_image_data(imgdata)

########NEW FILE########
__FILENAME__ = sharpen
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from thumbor.filters import BaseFilter, filter_method
from thumbor.ext.filters import _sharpen


class Filter(BaseFilter):

    @filter_method(BaseFilter.DecimalNumber, BaseFilter.DecimalNumber, BaseFilter.Boolean)
    def sharpen(self, amount, radius, luminance_only):
        width, height = self.engine.size
        mode, data = self.engine.image_data_as_rgb()
        imgdata = _sharpen.apply(
            mode, width, height, amount, radius,
            luminance_only, data
        )
        self.engine.set_image_data(imgdata)

########NEW FILE########
__FILENAME__ = strip_icc
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from thumbor.filters import BaseFilter, filter_method


class Filter(BaseFilter):

    @filter_method()
    def strip_icc(self):
        self.engine.strip_icc()

########NEW FILE########
__FILENAME__ = watermark
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from thumbor.ext.filters import _alpha
from thumbor.filters import BaseFilter, filter_method
from os.path import splitext


class Filter(BaseFilter):
    regex = r'(?:watermark\((?P<url>.*?),(?P<x>-?[\d]*?),(?P<y>-?[\d]*?),(?P<alpha>[\d]*?)\))'

    def on_image_ready(self, buffer):
        self.watermark_engine.load(buffer, self.extension)
        self.watermark_engine.enable_alpha()

        mode, data = self.watermark_engine.image_data_as_rgb()
        imgdata = _alpha.apply(mode,
                               self.alpha,
                               data)

        self.watermark_engine.set_image_data(imgdata)

        inv_x = self.x[0] == '-'
        inv_y = self.y[0] == '-'
        x, y = int(self.x), int(self.y)

        sz = self.engine.size
        watermark_sz = self.watermark_engine.size
        if inv_x:
            x = (sz[0] - watermark_sz[0]) + x
        if inv_y:
            y = (sz[1] - watermark_sz[1]) + y

        self.engine.paste(self.watermark_engine, (x, y), merge=True)

        self.callback()

    def on_fetch_done(self, buffer):
        self.watermark_engine.load(buffer, self.extension)
        self.storage.put(self.url, self.watermark_engine.read())
        self.storage.put_crypto(self.url)
        self.on_image_ready(buffer)

    @filter_method(BaseFilter.String, r'-?[\d]+', r'-?[\d]+', BaseFilter.PositiveNumber, async=True)
    def watermark(self, callback, url, x, y, alpha):
        self.url = url
        self.x = x
        self.y = y
        self.alpha = alpha
        self.callback = callback
        self.extension = splitext(self.url)[-1].lower()
        self.watermark_engine = self.context.modules.engine.__class__(self.context)
        self.storage = self.context.modules.storage

        buffer = self.storage.get(self.url)
        if buffer is not None:
            self.on_image_ready(buffer)
        else:
            self.context.modules.loader.load(self.context, self.url, self.on_fetch_done)

########NEW FILE########
__FILENAME__ = healthcheck
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from thumbor.handlers import BaseHandler


class HealthcheckHandler(BaseHandler):
    def get(self):
        self.write('WORKING')

    def head(self, *args, **kwargs):
        self.set_status(200)

########NEW FILE########
__FILENAME__ = image
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com
import datetime

from thumbor.handlers import ImageApiHandler
from thumbor.engines import BaseEngine


##
# Handler to retrieve or modify existing images
# This handler support GET, PUT and DELETE method to manipulate existing images
##
class ImageHandler(ImageApiHandler):

    def put(self, id):
        id = id[:32]
        # Check if image overwriting is allowed
        if not self.context.config.UPLOAD_PUT_ALLOWED:
            self._error(405, 'Unable to modify an uploaded image')
            return

        # Check if the image uploaded is valid
        if self.validate(self.request.body):
            self.write_file(id, self.request.body)
            self.set_status(204)

    def delete(self, id):
        id = id[:32]
        # Check if image deleting is allowed
        if not self.context.config.UPLOAD_DELETE_ALLOWED:
            self._error(405, 'Unable to delete an uploaded image')
            return

        # Check if image exists
        if self.context.modules.storage.exists(id):
            self.context.modules.storage.remove(id)
            self.set_status(204)
        else:
            self._error(404, 'Image not found at the given URL')

    def get(self, id):
        id = id[:32]
        # Check if image exists
        if self.context.modules.storage.exists(id):
            body = self.context.modules.storage.get(id)
            self.set_status(200)

            mime = BaseEngine.get_mimetype(body)
            if mime:
                self.set_header('Content-Type', mime)

            max_age = self.context.config.MAX_AGE
            if max_age:
                self.set_header('Cache-Control', 'max-age=' + str(max_age) + ',public')
                self.set_header('Expires', datetime.datetime.utcnow() + datetime.timedelta(seconds=max_age))
            self.write(body)
        else:
            self._error(404, 'Image not found at the given URL')

########NEW FILE########
__FILENAME__ = images
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import uuid
import mimetypes
from thumbor.handlers import ImageApiHandler
from thumbor.engines import BaseEngine


##
# Handler to upload images.
# This handler support only POST method, but images can be uploaded  :
#   - through multipart/form-data (designed for forms)
#   - or with the image content in the request body (rest style)
##
class ImagesHandler(ImageApiHandler):

    def post(self):
        # Check if the image uploaded is a multipart/form-data
        if self.multipart_form_data():
            file_data = self.request.files['media'][0]
            body = file_data['body']

            # Retrieve filename from 'filename' field
            filename = file_data['filename']
        else:
            body = self.request.body

            # Retrieve filename from 'Slug' header
            filename = self.request.headers.get('Slug')

        # Check if the image uploaded is valid
        if self.validate(body):

            # Use the default filename for the uploaded images
            if not filename:
                content_type = self.request.headers.get('Content-Type', BaseEngine.get_mimetype(body))
                extension = mimetypes.guess_extension(content_type, False)
                if extension == '.jpe':
                    extension = '.jpg'  # Hack because mimetypes return .jpe by default
                filename = self.context.config.UPLOAD_DEFAULT_FILENAME + extension

            # Build image id based on a random uuid (32 characters)
            id = str(uuid.uuid4().hex)
            self.write_file(id, body)
            self.set_status(201)
            self.set_header('Location', self.location(id, filename))

    def multipart_form_data(self):
        if not 'media' in self.request.files or not self.request.files['media']:
            return False
        else:
            return True

    def location(self, id, filename):
        base_uri = self.request.uri
        return base_uri + '/' + id + '/' + filename

########NEW FILE########
__FILENAME__ = imaging
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import tornado.web

from thumbor.handlers import ContextHandler
from thumbor.context import RequestParameters
from thumbor.crypto import Cryptor, Signer
from thumbor.utils import logger
from thumbor.url import Url


class ImagingHandler(ContextHandler):

    @tornado.web.asynchronous
    def get(self, **kw):
        # Check if an image with an uuid exists in storage
        if self.context.modules.storage.exists(kw['image'][:32]):
            kw['image'] = kw['image'][:32]

        url = self.request.uri

        if not self.validate(kw['image']):
            self._error(404, 'No original image was specified in the given URL')
            return

        kw['request'] = self.request

        self.context.request = RequestParameters(**kw)

        has_none = not self.context.request.unsafe and not self.context.request.hash
        has_both = self.context.request.unsafe and self.context.request.hash

        if has_none or has_both:
            self._error(404, 'URL does not have hash or unsafe, or has both: %s' % url)
            return

        if self.context.request.unsafe and not self.context.config.ALLOW_UNSAFE_URL:
            self._error(404, 'URL has unsafe but unsafe is not allowed by the config: %s' % url)
            return

        url_signature = self.context.request.hash
        if url_signature:
            signer = Signer(self.context.server.security_key)

            url_to_validate = Url.encode_url(url).replace('/%s/' % self.context.request.hash, '')
            valid = signer.validate(url_signature, url_to_validate)

            if not valid and self.context.config.STORES_CRYPTO_KEY_FOR_EACH_IMAGE:
                # Retrieves security key for this image if it has been seen before
                security_key = self.context.modules.storage.get_crypto(self.context.request.image_url)
                if security_key is not None:
                    signer = Signer(security_key)
                    valid = signer.validate(url_signature, url_to_validate)

            if not valid:
                is_valid = True
                if self.context.config.ALLOW_OLD_URLS:
                    cr = Cryptor(self.context.server.security_key)
                    options = cr.get_options(self.context.request.hash, self.context.request.image_url)
                    if options is None:
                        is_valid = False
                    else:
                        options['request'] = self.request
                        self.context.request = RequestParameters(**options)
                        logger.warning(
                            'OLD FORMAT URL DETECTED!!! This format of URL will be discontinued in ' +
                            'upcoming versions. Please start using the new format as soon as possible. ' +
                            'More info at https://github.com/globocom/thumbor/wiki/3.0.0-release-changes'
                        )
                else:
                    is_valid = False

                if not is_valid:
                    self._error(404, 'Malformed URL: %s' % url)
                    return

        return self.execute_image_operations()

########NEW FILE########
__FILENAME__ = upload
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import urllib

from thumbor.handlers import ContextHandler


class BadRequestError(ValueError):
    pass


class UploadHandler(ContextHandler):

    def write_file(self, filename, body, overwrite):
        storage = self.context.modules.upload_photo_storage
        path = filename
        if hasattr(storage, 'resolve_original_photo_path'):
            path = storage.resolve_original_photo_path(self.request, filename)

        if not overwrite and storage.exists(path):
            raise RuntimeError('File already exists.')

        stored_path = storage.put(path, body)

        return stored_path

    def extract_file_data(self):
        if not 'media' in self.request.files:
            raise RuntimeError("File was not uploaded properly.")
        if not self.request.files['media']:
            raise RuntimeError("File was not uploaded properly.")

        return self.request.files['media'][0]

    def save_and_render(self, overwrite=False):
        file_data = self.extract_file_data()
        body = file_data['body']
        filename = file_data['filename']
        path = ""
        try:
            path = self.write_file(filename, body, overwrite=overwrite)
            self.set_status(201)
            self.set_header('Location', path)
        except RuntimeError:
            self.set_status(409)
            path = 'File already exists.'
        except BadRequestError:
            self.set_status(400)
            path = 'Invalid request'
        self.write(path)

    def post(self):
        if self.validate():
            self.save_and_render()
        else:
            self.set_status(412)
            self.write('File is too big, not an image or too small image')

    def put(self):
        if not self.context.config.UPLOAD_PUT_ALLOWED:
            self.set_status(405)
            return

        if self.validate():
            self.save_and_render(overwrite=True)
        else:
            self.set_status(412)
            self.write('File is too big, not an image or too small image')

    def delete(self):
        if not self.context.config.UPLOAD_DELETE_ALLOWED:
            self.set_status(405)
            return

        path = 'file_path' in self.request.arguments and self.request.arguments['file_path'] or None
        if path is None and self.request.body is None:
            raise RuntimeError('The file_path argument is mandatory to delete an image')
        path = urllib.unquote(self.request.body.split('=')[-1])

        if self.context.modules.storage.exists(path):
            self.context.modules.storage.remove(path)

    def validate(self):
        conf = self.context.config
        engine = self.context.modules.engine

        if (conf.UPLOAD_MAX_SIZE != 0 and len(self.extract_file_data()['body']) > conf.UPLOAD_MAX_SIZE):
            return False

        try:
            engine.load(self.extract_file_data()['body'], None)
        except IOError:
            return False

        size = engine.size
        if (conf.MIN_WIDTH > size[0] or conf.MIN_HEIGHT > size[1]):
            return False

        return True

########NEW FILE########
__FILENAME__ = importer
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from thumbor.utils import logger
from functools import reduce


class Importer:
    def __init__(self, config):
        self.config = config
        self.engine = None
        self.loader = None
        self.upload_photo_storage = None
        self.storage = None
        self.result_storage = None
        self.detectors = []
        self.filters = []
        self.error_handler_class = None

    def import_class(self, name, get_module=False):
        module_name = get_module and name or '.'.join(name.split('.')[:-1])
        klass = name.split('.')[-1]

        module = get_module and __import__(name) or __import__(module_name)
        if '.' in module_name:
            module = reduce(getattr, module_name.split('.')[1:], module)

        return get_module and module or getattr(module, klass)

    def import_modules(self):
        self.config.validates_presence_of('ENGINE', 'LOADER', 'STORAGE', 'DETECTORS', 'FILTERS')
        self.import_item('ENGINE', 'Engine')
        self.import_item('LOADER')
        self.import_item('STORAGE', 'Storage')
        self.import_item('DETECTORS', 'Detector', is_multiple=True)
        self.import_item('FILTERS', 'Filter', is_multiple=True, ignore_errors=True)

        if self.config.RESULT_STORAGE:
            self.import_item('RESULT_STORAGE', 'Storage')

        if self.config.UPLOAD_PHOTO_STORAGE:
            self.import_item('UPLOAD_PHOTO_STORAGE', 'Storage')

        if self.config.USE_CUSTOM_ERROR_HANDLING:
            self.import_item('ERROR_HANDLER_MODULE', 'ErrorHandler')
            self.error_handler_class = self.error_handler_module

    def import_item(self, config_key=None, class_name=None, is_multiple=False, item_value=None, ignore_errors=False):
        if item_value is None:
            conf_value = getattr(self.config, config_key)
        else:
            conf_value = item_value

        if is_multiple:
            modules = []
            if conf_value:
                for module_name in conf_value:
                    try:
                        if class_name is not None:
                            module = self.import_class('%s.%s' % (module_name, class_name))
                        else:
                            module = self.import_class(module_name, get_module=True)
                        modules.append(module)
                    except ImportError:
                        if ignore_errors:
                            logger.warn('Module %s could not be imported.' % module_name)
                        else:
                            raise
            setattr(self, config_key.lower(), tuple(modules))
        else:
            if class_name is not None:
                module = self.import_class('%s.%s' % (conf_value, class_name))
            else:
                module = self.import_class(conf_value, get_module=True)
            setattr(self, config_key.lower(), module)

########NEW FILE########
__FILENAME__ = pil_test
from thumbor.integration_tests import EngineTestCase


class PILTest(EngineTestCase):
    engine = 'thumbor.engines.pil'

########NEW FILE########
__FILENAME__ = urls_helpers
#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from os.path import join
from itertools import product

from colorama import Fore


debugs = [
    '',
    'debug'
]

metas = [
    'meta'
]

trims = [
    'trim',
    'trim:top-left',
    'trim:bottom-right',
    'trim:top-left:10',
    'trim:bottom-right:20',
]

crops = [
    '10x10:100x100'
]

fitins = [
    'fit-in',
    'adaptive-fit-in',
]

sizes = [
    '200x200',
    '-300x100',
    '100x-300',
    '-100x-300',
    'origx300',
    '200xorig',
    'origxorig',
]

haligns = [
    'left',
    'right',
    'center',
]

valigns = [
    'top',
    'bottom',
    'middle',
]

smarts = [
    'smart',
]

filters = [
    'filters:brightness(10)',
    'filters:contrast(10)',
    'filters:equalize()',
    'filters:grayscale()',
    'filters:noise(10)',
    'filters:quality(5)',
    'filters:redeye()',
    'filters:rgb(10,-10,20)',
    'filters:round_corner(20,255,255,100)',
    'filters:sharpen(6,2.5,false)',
    'filters:sharpen(6,2.5,true)',
    'filters:strip_icc()',
    'filters:watermark(brasil_45.png,10,10,50)',
    'filters:frame(frame.9.png)',
    'filters:fill(ff0000)',
    'filters:fill(auto)',
    'filters:fill(ff0000,true)',
    'filters:blur(2)',
    'filters:extract_focal()',
]

original_images_base = [
    'dilmahaddad.jpg',
    'cmyk.jpg',
    'logo-FV.png-menor.png',
]

original_images_gif_webp = [
    '5.webp',
    'alerta.gif',
    'tumblr_m9u52mZMgk1qz99y7o1_400.gif',
]


class UrlsTester(object):

    def __init__(self, fetcher, group):
        self.failed_items = []
        self.test_group(fetcher, group)

    def report(self):
        assert len(self.failed_items) == 0, "Failed urls:\n%s" % '\n'.join(self.failed_items)

    def try_url(self, fetcher, url):
        result = None
        failed = False

        try:
            result = fetcher("/%s" % url)
        except Exception:
            logging.exception('Error in %s' % url)
            failed = True

        if result is not None and result.code == 200 and not failed:
            print("{0.GREEN} SUCCESS ({1}){0.RESET}".format(Fore, url))
            return

        self.failed_items.append(url)
        print("{0.RED} FAILED ({1}) - ERR({2}) {0.RESET}".format(Fore, url, result and result.code))

    def test_group(self, fetcher, group):
        group = list(group)
        count = len(group)

        print("Requests count: %d" % count)
        for options in group:
            joined_parts = join(*options)
            url = "unsafe/%s" % joined_parts
            self.try_url(fetcher, url)

        self.report()


def single_dataset(fetcher, with_gif=True):
    images = original_images_base[:]
    if with_gif:
        images += original_images_gif_webp
    all_options = trims + crops + fitins + sizes + haligns + valigns + smarts + filters
    UrlsTester(fetcher, product(all_options, images))


def combined_dataset(fetcher, with_gif=True):
    images = original_images_base[:]
    if with_gif:
        images += original_images_gif_webp
    combined_options = product(trims[:2], crops[:2], fitins[:2], sizes[:2], haligns[:2], valigns[:2], smarts[:2], filters[:2], images)
    UrlsTester(fetcher, combined_options)

########NEW FILE########
__FILENAME__ = file_loader
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from os.path import join, exists, abspath


def load(context, path, callback):
    file_path = join(context.config.FILE_LOADER_ROOT_PATH.rstrip('/'), path.lstrip('/'))
    file_path = abspath(file_path)
    inside_root_path = file_path.startswith(context.config.FILE_LOADER_ROOT_PATH)

    if inside_root_path and exists(file_path):
        with open(file_path, 'r') as f:
            callback(f.read())
    else:
        callback(None)

########NEW FILE########
__FILENAME__ = http_loader
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import re
from urlparse import urlparse
from functools import partial

import tornado.httpclient

from thumbor.utils import logger


def _normalize_url(url):
    return url if url.startswith('http') else 'http://%s' % url


def validate(context, url):
    url = _normalize_url(url)
    res = urlparse(url)

    if not res.hostname:
        return False

    if not context.config.ALLOWED_SOURCES:
        return True

    for pattern in context.config.ALLOWED_SOURCES:
        if re.match('^%s$' % pattern, res.hostname):
            return True

    return False


def return_contents(response, url, callback):
    if response.error:
        logger.warn("ERROR retrieving image {0}: {1}".format(url, str(response.error)))
        callback(None)
    elif response.body is None or len(response.body) == 0:
        logger.warn("ERROR retrieving image {0}: Empty response.".format(url))
        callback(None)
    else:
        callback(response.body)


def load(context, url, callback):
    if context.config.HTTP_LOADER_PROXY_HOST and context.config.HTTP_LOADER_PROXY_PORT:
        tornado.httpclient.AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
    client = tornado.httpclient.AsyncHTTPClient()

    user_agent = None
    if context.config.HTTP_LOADER_FORWARD_USER_AGENT:
        if 'User-Agent' in context.request_handler.request.headers:
            user_agent = context.request_handler.request.headers['User-Agent']
    if user_agent is None:
        user_agent = context.config.HTTP_LOADER_DEFAULT_USER_AGENT

    url = _normalize_url(url)
    req = tornado.httpclient.HTTPRequest(
        url=encode(url),
        connect_timeout=context.config.HTTP_LOADER_CONNECT_TIMEOUT,
        request_timeout=context.config.HTTP_LOADER_REQUEST_TIMEOUT,
        follow_redirects=context.config.HTTP_LOADER_FOLLOW_REDIRECTS,
        max_redirects=context.config.HTTP_LOADER_MAX_REDIRECTS,
        user_agent=user_agent,
        proxy_host=encode(context.config.HTTP_LOADER_PROXY_HOST),
        proxy_port=context.config.HTTP_LOADER_PROXY_PORT,
        proxy_username=encode(context.config.HTTP_LOADER_PROXY_USERNAME),
        proxy_password=encode(context.config.HTTP_LOADER_PROXY_PASSWORD)
    )

    client.fetch(req, callback=partial(return_contents, url=url, callback=callback))

def encode(string):
    return None if string is None else string.encode('ascii')

########NEW FILE########
__FILENAME__ = point
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com


class FocalPoint(object):
    ALIGNMENT_PERCENTAGES = {
        'left': 0.0,
        'center': 0.5,
        'right': 1.0,
        'top': 0.0,
        'middle': 0.5,
        'bottom': 1.0
    }

    def to_dict(self):
        return {
            'x': self.x,
            'y': self.y,
            'z': self.weight,
            'height': self.height,
            'width': self.width,
            'origin': self.origin
        }

    @classmethod
    def from_dict(cls, values):
        return cls(
            x=float(values['x']),
            y=float(values['y']),
            weight=float(values['z']),
            width=float(values.get('width', 1)),
            height=float(values.get('height', 1)),
            origin=values.get('origin', 'alignment')
        )

    def __init__(self, x, y, height=1, width=1, weight=1.0, origin="alignment"):
        self.x = x
        self.y = y
        self.height = height
        self.width = width
        self.weight = weight
        self.origin = origin

    @classmethod
    def from_square(cls, x, y, width, height, origin='detection'):
        center_x = x + (width / 2)
        center_y = y + (height / 2)
        return cls(center_x, center_y, height=height, width=width, weight=width * height, origin=origin)

    @classmethod
    def from_alignment(cls, halign, valign, width, height):
        x = width * cls.ALIGNMENT_PERCENTAGES[halign]
        y = height * cls.ALIGNMENT_PERCENTAGES[valign]

        return cls(x, y)

    def __repr__(self):
        return 'FocalPoint(x: %d, y: %d, width: %d, height: %d, weight: %d, origin: %s)' % (
            self.x, self.y, self.width, self.height, self.weight, self.origin
        )

########NEW FILE########
__FILENAME__ = file_storage
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from datetime import datetime
from uuid import uuid4
from shutil import move

from os.path import exists, dirname, join, getmtime, abspath

from thumbor.result_storages import BaseStorage
from thumbor.utils import logger


class Storage(BaseStorage):
    PATH_FORMAT_VERSION = 'v2'

    @property
    def is_auto_webp(self):
        return self.context.config.AUTO_WEBP and self.context.request.accepts_webp

    def put(self, bytes):
        file_abspath = self.normalize_path(self.context.request.url)
        if not self.validate_path(file_abspath):
            logger.warn("[RESULT_STORAGE] unable to write outside root path: %s" % file_abspath)
            return
        temp_abspath = "%s.%s" % (file_abspath, str(uuid4()).replace('-', ''))
        file_dir_abspath = dirname(file_abspath)
        logger.debug("[RESULT_STORAGE] putting at %s (%s)" % (file_abspath, file_dir_abspath))

        self.ensure_dir(file_dir_abspath)

        with open(temp_abspath, 'w') as _file:
            _file.write(bytes)

        move(temp_abspath, file_abspath)

    def get(self):
        path = self.context.request.url
        file_abspath = self.normalize_path(path)
        if not self.validate_path(file_abspath):
            logger.warn("[RESULT_STORAGE] unable to read from outside root path: %s" % file_abspath)
            return None
        logger.debug("[RESULT_STORAGE] getting from %s" % file_abspath)

        if not exists(file_abspath) or self.is_expired(file_abspath):
            logger.debug("[RESULT_STORAGE] image not found at %s" % file_abspath)
            return None
        with open(file_abspath, 'r') as f:
            return f.read()

    def validate_path(self, path):
        return abspath(path).startswith(self.context.config.RESULT_STORAGE_FILE_STORAGE_ROOT_PATH)

    def normalize_path(self, path):
        path_segments = [self.context.config.RESULT_STORAGE_FILE_STORAGE_ROOT_PATH.rstrip('/'), Storage.PATH_FORMAT_VERSION, ]
        if self.is_auto_webp:
            path_segments.append("webp")

        path_segments.extend([self.partition(path), path.lstrip('/'), ])

        normalized_path = join(*path_segments).replace('http://', '')
        return normalized_path

    def partition(self, path_raw):
        path = path_raw.lstrip('/')
        return join("".join(path[0:2]), "".join(path[2:4]))

    def is_expired(self, path):
        expire_in_seconds = self.context.config.get('RESULT_STORAGE_EXPIRATION_SECONDS', None)

        if expire_in_seconds is None or expire_in_seconds == 0:
            return False

        timediff = datetime.now() - datetime.fromtimestamp(getmtime(path))
        return timediff.seconds > expire_in_seconds

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import sys
import logging
import os
import socket
from os.path import expanduser, dirname

import tornado.ioloop
from tornado.httpserver import HTTPServer

from thumbor.console import get_server_parameters
from thumbor.config import Config
from thumbor.importer import Importer
from thumbor.context import Context


def get_as_integer(value):
    try:
        return int(value)
    except ValueError:
        return None

def main(arguments=None):
    '''Runs thumbor server with the specified arguments.'''

    server_parameters = get_server_parameters(arguments)

    lookup_paths = [os.curdir,
                    expanduser('~'),
                    '/etc/',
                    dirname(__file__)]

    config = Config.load(server_parameters.config_path, conf_name='thumbor.conf', lookup_paths=lookup_paths)

    logging.basicConfig(
        level=getattr(logging, server_parameters.log_level.upper()),
        format=config.THUMBOR_LOG_FORMAT,
        datefmt=config.THUMBOR_LOG_DATE_FORMAT
    )

    importer = Importer(config)
    importer.import_modules()

    if importer.error_handler_class is not None:
        importer.error_handler = importer.error_handler_class(config)

    if server_parameters.security_key is None:
        server_parameters.security_key = config.SECURITY_KEY

    if not isinstance(server_parameters.security_key, basestring):
        raise RuntimeError(
            'No security key was found for this instance of thumbor. ' +
            'Please provide one using the conf file or a security key file.')

    context = Context(server=server_parameters, config=config, importer=importer)

    application = importer.import_class(server_parameters.app_class)(context)

    server = HTTPServer(application)

    if context.server.fd is not None:
        fd_number = get_as_integer(context.server.fd)
        if fd_number is None:
            with open(context.server.fd, 'r') as sock:
                fd_number = sock.fileno()

        sock = socket.fromfd(fd_number,
                             socket.AF_INET | socket.AF_INET6,
                             socket.SOCK_STREAM)
        server.add_socket(sock)
    else:
        server.bind(context.server.port, context.server.ip)

    server.start(1)

    try:
        logging.debug('thumbor running at %s:%d' % (context.server.ip, context.server.port))
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        print
        print "-- thumbor closed by user interruption --"

if __name__ == "__main__":
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = file_storage
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import os
from shutil import move
from json import dumps, loads
from datetime import datetime
from os.path import exists, dirname, join, getmtime, splitext
import hashlib
from uuid import uuid4

import thumbor.storages as storages


class Storage(storages.BaseStorage):

    def put(self, path, bytes):
        file_abspath = self.path_on_filesystem(path)
        temp_abspath = "%s.%s" % (file_abspath, str(uuid4()).replace('-', ''))
        file_dir_abspath = dirname(file_abspath)

        self.ensure_dir(file_dir_abspath)

        with open(temp_abspath, 'w') as _file:
            _file.write(bytes)

        move(temp_abspath, file_abspath)

        return path

    def put_crypto(self, path):
        if not self.context.config.STORES_CRYPTO_KEY_FOR_EACH_IMAGE:
            return

        file_abspath = self.path_on_filesystem(path)
        file_dir_abspath = dirname(file_abspath)

        self.ensure_dir(file_dir_abspath)

        if not self.context.server.security_key:
            raise RuntimeError("STORES_CRYPTO_KEY_FOR_EACH_IMAGE can't be True if no SECURITY_KEY specified")

        crypto_path = '%s.txt' % splitext(file_abspath)[0]
        temp_abspath = "%s.%s" % (crypto_path, str(uuid4()).replace('-', ''))
        with open(temp_abspath, 'w') as _file:
            _file.write(self.context.server.security_key)

        move(temp_abspath, crypto_path)

        return file_abspath

    def put_detector_data(self, path, data):
        file_abspath = self.path_on_filesystem(path)

        path = '%s.detectors.txt' % splitext(file_abspath)[0]
        temp_abspath = "%s.%s" % (path, str(uuid4()).replace('-', ''))

        file_dir_abspath = dirname(file_abspath)
        self.ensure_dir(file_dir_abspath)

        with open(temp_abspath, 'w') as _file:
            _file.write(dumps(data))

        move(temp_abspath, path)

        return file_abspath

    def get_crypto(self, path):
        file_abspath = self.path_on_filesystem(path)
        crypto_file = "%s.txt" % (splitext(file_abspath)[0])

        if not exists(crypto_file):
            return None
        return file(crypto_file).read()

    def get(self, path):
        file_abspath = self.path_on_filesystem(path)

        if not exists(file_abspath) or self.__is_expired(file_abspath):
            return None
        return open(file_abspath, 'r').read()

    def get_detector_data(self, path):
        file_abspath = self.path_on_filesystem(path)
        path = '%s.detectors.txt' % splitext(file_abspath)[0]

        if not exists(path) or self.__is_expired(path):
            return None

        return loads(open(path, 'r').read())

    def path_on_filesystem(self, path):
        digest = hashlib.sha1(path.encode('utf-8')).hexdigest()
        return "%s/%s/%s" % (self.context.config.FILE_STORAGE_ROOT_PATH.rstrip('/'), digest[:2], digest[2:])

    def exists(self, path):
        n_path = self.path_on_filesystem(path)
        return os.path.exists(n_path)

    def remove(self, path):
        n_path = self.path_on_filesystem(path)
        return os.remove(n_path)

    def __is_expired(self, path):
        timediff = datetime.now() - datetime.fromtimestamp(getmtime(path))
        return timediff.seconds > self.context.config.STORAGE_EXPIRATION_SECONDS

########NEW FILE########
__FILENAME__ = memcache_storage
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from json import loads, dumps

import pylibmc

from thumbor.storages import BaseStorage


class Storage(BaseStorage):

    def __init__(self, context):
        BaseStorage.__init__(self, context)

        self.storage = pylibmc.Client(
            self.context.config.MEMCACHE_STORAGE_SERVERS,
            binary=True,
            behaviors={
                "tcp_nodelay": True,
                'no_block': True,
                "ketama": True
            }
        )

    def __key_for(self, url):
        return 'thumbor-crypto-%s' % url

    def __detector_key_for(self, url):
        return 'thumbor-detector-%s' % url

    def put(self, path, bytes):
        self.storage.set(path, bytes, time=self.context.config.STORAGE_EXPIRATION_SECONDS)
        return path

    def put_crypto(self, path):
        if not self.context.config.STORES_CRYPTO_KEY_FOR_EACH_IMAGE:
            return

        if not self.context.server.security_key:
            raise RuntimeError("STORES_CRYPTO_KEY_FOR_EACH_IMAGE can't be True if no SECURITY_KEY specified")

        key = self.__key_for(path)
        self.storage.set(key, self.context.server.security_key)
        return key

    def put_detector_data(self, path, data):
        key = self.__detector_key_for(path)
        self.storage.set(key, dumps(data))
        return key

    def get_crypto(self, path):
        if not self.context.config.STORES_CRYPTO_KEY_FOR_EACH_IMAGE:
            return None

        crypto = self.storage.get(self.__key_for(path))

        if not crypto:
            return None
        return crypto

    def get_detector_data(self, path):
        data = self.storage.get(self.__detector_key_for(path))

        if not data:
            return None
        return loads(data)

    def exists(self, path):
        return self.storage.get(path) is not None

    def remove(self, path):
        if not self.exists(path):
            return
        return self.storage.delete(path)

    def get(self, path):
        return self.storage.get(path)

########NEW FILE########
__FILENAME__ = mixed_storage
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from thumbor.storages import BaseStorage


class Storage(BaseStorage):
    def __init__(self, context, file_storage=None, crypto_storage=None, detector_storage=None):
        BaseStorage.__init__(self, context)

        self.file_storage = file_storage

        self.crypto_storage = crypto_storage

        self.detector_storage = detector_storage

    def _init_file_storage(self):
        if self.file_storage is None:
            self.context.modules.importer.import_item(
                config_key='file_storage',
                item_value=self.context.config.MIXED_STORAGE_FILE_STORAGE,
                class_name='Storage'
            )
            self.file_storage = self.context.modules.file_storage = self.context.modules.importer.file_storage(self.context)

    def _init_crypto_storage(self):
        if self.crypto_storage is None:
            self.context.modules.importer.import_item(
                config_key='crypto_storage',
                item_value=self.context.config.MIXED_STORAGE_CRYPTO_STORAGE,
                class_name='Storage'
            )
            self.crypto_storage = self.context.modules.crypto_storage = self.context.modules.importer.crypto_storage(self.context)

    def _init_detector_storage(self):
        if self.detector_storage is None:
            self.context.modules.importer.import_item(
                config_key='detector_storage',
                item_value=self.context.config.MIXED_STORAGE_DETECTOR_STORAGE,
                class_name='Storage'
            )
            self.detector_storage = self.context.modules.detector_storage = \
                self.context.modules.importer.detector_storage(self.context)

    def put(self, path, bytes):
        self._init_file_storage()
        self.file_storage.put(path, bytes)

    def put_detector_data(self, path, data):
        self._init_detector_storage()
        self.detector_storage.put_detector_data(path, data)

    def put_crypto(self, path):
        self._init_crypto_storage()
        self.crypto_storage.put_crypto(path)

    def get_crypto(self, path):
        self._init_crypto_storage()
        return self.crypto_storage.get_crypto(path)

    def get_detector_data(self, path):
        self._init_detector_storage()
        return self.detector_storage.get_detector_data(path)

    def get(self, path):
        self._init_file_storage()
        return self.file_storage.get(path)

    def exists(self, path):
        self._init_file_storage()
        return self.file_storage.exists(path)

    def resolve_original_photo_path(self, request, filename):
        return self.file_storage.resolve_original_photo_path(request, filename)

########NEW FILE########
__FILENAME__ = mongo_storage
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from datetime import datetime, timedelta
from cStringIO import StringIO

from pymongo import Connection
import gridfs

from thumbor.storages import BaseStorage


class Storage(BaseStorage):

    def __conn__(self):
        connection = Connection(self.context.config.MONGO_STORAGE_SERVER_HOST, self.context.config.MONGO_STORAGE_SERVER_PORT)
        db = connection[self.context.config.MONGO_STORAGE_SERVER_DB]
        storage = db[self.context.config.MONGO_STORAGE_SERVER_COLLECTION]

        return connection, db, storage

    def put(self, path, bytes):
        connection, db, storage = self.__conn__()

        doc = {
            'path': path,
            'created_at': datetime.now()
        }

        doc_with_crypto = dict(doc)
        if self.context.config.STORES_CRYPTO_KEY_FOR_EACH_IMAGE:
            if not self.context.server.security_key:
                raise RuntimeError("STORES_CRYPTO_KEY_FOR_EACH_IMAGE can't be True if no SECURITY_KEY specified")
            doc_with_crypto['crypto'] = self.context.server.security_key

        fs = gridfs.GridFS(db)
        file_data = fs.put(StringIO(bytes), **doc)

        doc_with_crypto['file_id'] = file_data
        storage.insert(doc_with_crypto)
        return path

    def put_crypto(self, path):
        if not self.context.config.STORES_CRYPTO_KEY_FOR_EACH_IMAGE:
            return

        connection, db, storage = self.__conn__()

        if not self.context.server.security_key:
            raise RuntimeError("STORES_CRYPTO_KEY_FOR_EACH_IMAGE can't be True if no SECURITY_KEY specified")

        crypto = storage.find_one({'path': path})

        crypto['crypto'] = self.context.server.security_key
        storage.update({'path': path}, crypto)
        return path

    def put_detector_data(self, path, data):
        connection, db, storage = self.__conn__()

        storage.update({'path': path}, {"$set": {"detector_data": data}})
        return path

    def get_crypto(self, path):
        connection, db, storage = self.__conn__()

        crypto = storage.find_one({'path': path})
        return crypto.get('crypto') if crypto else None

    def get_detector_data(self, path):
        connection, db, storage = self.__conn__()

        doc = storage.find_one({'path': path})
        return doc.get('detector_data') if doc else None

    def get(self, path):
        connection, db, storage = self.__conn__()

        stored = storage.find_one({'path': path})

        if not stored or self.__is_expired(stored):
            return None

        fs = gridfs.GridFS(db)

        contents = fs.get(stored['file_id']).read()

        return str(contents)

    def exists(self, path):
        connection, db, storage = self.__conn__()

        stored = storage.find_one({'path': path})

        if not stored or self.__is_expired(stored):
            return False

        return True

    def remove(self, path):
        if not self.exists(path):
            return

        connection, db, storage = self.__conn__()
        storage.remove({'path': path})

    def __is_expired(self, stored):
        timediff = datetime.now() - stored.get('created_at')
        return timediff > timedelta(seconds=self.context.config.STORAGE_EXPIRATION_SECONDS)

########NEW FILE########
__FILENAME__ = no_storage
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from thumbor.storages import BaseStorage


class Storage(BaseStorage):

    def put(self, path, bytes):
        return path

    def put_crypto(self, path):
        return path

    def put_detector_data(self, path, data):
        return path

    def get_crypto(self, path):
        return None

    def get_detector_data(self, path):
        return None

    def get(self, path):
        return None

    def exists(self, path):
        return False

    def remove(self, path):
        pass

########NEW FILE########
__FILENAME__ = redis_storage
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from json import loads, dumps
from datetime import datetime, timedelta

from redis import Redis, RedisError

from thumbor.storages import BaseStorage
from thumbor.utils import on_exception


class Storage(BaseStorage):

    storage = None

    def __init__(self, context):
        BaseStorage.__init__(self, context)
        self.storage = self.reconnect_redis()

    def reconnect_redis(self):
        if not Storage.storage:
            Storage.storage = Redis(port=self.context.config.REDIS_STORAGE_SERVER_PORT,
                                    host=self.context.config.REDIS_STORAGE_SERVER_HOST,
                                    db=self.context.config.REDIS_STORAGE_SERVER_DB,
                                    password=self.context.config.REDIS_STORAGE_SERVER_PASSWORD)
        return Storage.storage

    def on_redis_error(self):
        Storage.storage = None

    def __key_for(self, url):
        return 'thumbor-crypto-%s' % url

    def __detector_key_for(self, url):
        return 'thumbor-detector-%s' % url

    @on_exception(on_redis_error, RedisError)
    def put(self, path, bytes):
        self.storage.set(path, bytes)
        self.storage.expireat(path, datetime.now() + timedelta(seconds=self.context.config.STORAGE_EXPIRATION_SECONDS))
        return path

    @on_exception(on_redis_error, RedisError)
    def put_crypto(self, path):
        if not self.context.config.STORES_CRYPTO_KEY_FOR_EACH_IMAGE:
            return

        if not self.context.server.security_key:
            raise RuntimeError("STORES_CRYPTO_KEY_FOR_EACH_IMAGE can't be True if no SECURITY_KEY specified")

        key = self.__key_for(path)
        self.storage.set(key, self.context.server.security_key)
        return key

    @on_exception(on_redis_error, RedisError)
    def put_detector_data(self, path, data):
        key = self.__detector_key_for(path)
        self.storage.set(key, dumps(data))
        return key

    @on_exception(on_redis_error, RedisError)
    def get_crypto(self, path):
        if not self.context.config.STORES_CRYPTO_KEY_FOR_EACH_IMAGE:
            return None

        crypto = self.storage.get(self.__key_for(path))

        if not crypto:
            return None
        return crypto

    @on_exception(on_redis_error, RedisError)
    def get_detector_data(self, path):
        data = self.storage.get(self.__detector_key_for(path))

        if not data:
            return None
        return loads(data)

    @on_exception(on_redis_error, RedisError)
    def exists(self, path):
        return self.storage.exists(path)

    @on_exception(on_redis_error, RedisError)
    def remove(self, path):
        if not self.exists(path):
            return
        return self.storage.delete(path)

    @on_exception(on_redis_error, RedisError)
    def get(self, path):
        return self.storage.get(path)

########NEW FILE########
__FILENAME__ = transformer
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import math
import sys

from thumbor.point import FocalPoint
from thumbor.utils import logger

trim_enabled = True
try:
    from thumbor.ext.filters import _bounding_box
except ImportError:
    logger.warn("Error importing bounding_box filter, trimming won't work")
    trim_enabled = False


class Transformer(object):
    def __init__(self, context):
        self.context = context
        self.engine = self.context.modules.engine

    def calculate_target_dimensions(self):
        source_width, source_height = self.engine.size
        source_width = float(source_width)
        source_height = float(source_height)

        if not self.context.request.width and not self.context.request.height:
            self.target_width = source_width
            self.target_height = source_height
        else:
            if self.context.request.width:
                if self.context.request.width == "orig":
                    self.target_width = source_width
                else:
                    self.target_width = float(self.context.request.width)
            else:
                self.target_width = self.engine.get_proportional_width(self.context.request.height)

            if self.context.request.height:
                if self.context.request.height == "orig":
                    self.target_height = source_height
                else:
                    self.target_height = float(self.context.request.height)
            else:
                self.target_height = self.engine.get_proportional_height(self.context.request.width)

    def adjust_focal_points(self):
        source_width, source_height = self.engine.size

        self.focal_points = None

        if self.context.request.focal_points:
            if self.context.request.should_crop:
                self.focal_points = []
                crop = self.context.request.crop
                for point in self.context.request.focal_points:
                    if point.x < crop['left'] or point.x > crop['right'] or point.y < crop['top'] or point.y > crop['bottom']:
                        continue
                    point.x -= crop['left'] or 0
                    point.y -= crop['top'] or 0
                    self.focal_points.append(point)
            else:
                self.focal_points = self.context.request.focal_points

        if not self.focal_points:
            self.focal_points = [
                FocalPoint.from_alignment(self.context.request.halign,
                                          self.context.request.valign,
                                          source_width,
                                          source_height)
            ]

        self.engine.focus(self.focal_points)

    def transform(self, callback):
        self.done_callback = callback
        if self.context.config.RESPECT_ORIENTATION:
            self.engine.reorientate()
        self.trim()
        self.smart_detect()

    def trim(self):
        if self.context.request.trim is None or not trim_enabled:
            return

        mode, data = self.engine.image_data_as_rgb()
        box = _bounding_box.apply(
            mode,
            self.engine.size[0],
            self.engine.size[1],
            self.context.request.trim_pos,
            self.context.request.trim_tolerance,
            data
        )

        if box[2] < box[0] or box[3] < box[1]:
            logger.warn("Ignoring trim, there wouldn't be any image left, check the tolerance.")
            return

        self.engine.crop(box[0], box[1], box[2] + 1, box[3] + 1)
        if self.context.request.should_crop:
            self.context.request.crop['left'] -= box[0]
            self.context.request.crop['top'] -= box[1]
            self.context.request.crop['right'] -= box[0]
            self.context.request.crop['bottom'] -= box[1]

    @property
    def smart_storage_key(self):
        return self.context.request.image_url

    def smart_detect(self):
        if not (self.context.modules.detectors and self.context.request.smart):
            self.do_image_operations()
            return

        try:
            # Beware! Boolean hell ahead.
            #
            # The `running_smart_detection` flag is needed so we can know
            # whether `after_smart_detect()` is running synchronously or not.
            #
            # If we're running it in a sync fashion it will set
            # `should_run_image_operations` to True so we can avoid running
            # image operation inside the try block.
            self.should_run_image_operations = False
            self.running_smart_detection = True
            self.do_smart_detection()
            self.running_smart_detection = False
        except Exception:
            if not self.context.config.IGNORE_SMART_ERRORS:
                raise

            logger.exception("Ignored error during smart detection")
            if self.context.config.USE_CUSTOM_ERROR_HANDLING:
                self.context.modules.importer.error_handler.handle_error(
                    context=self.context,
                    handler=self.context.request_handler,
                    exception=sys.exc_info()
                )

            self.context.request.prevent_result_storage = True
            self.context.request.detection_error = True
            self.do_image_operations()

        if self.should_run_image_operations:
            self.do_image_operations()

    def do_smart_detection(self):
        focal_points = self.context.modules.storage.get_detector_data(self.smart_storage_key)
        if focal_points is not None:
            self.after_smart_detect(focal_points, points_from_storage=True)
        else:
            detectors = self.context.modules.detectors
            detectors[0](self.context, index=0, detectors=detectors).detect(self.after_smart_detect)

    def after_smart_detect(self, focal_points=[], points_from_storage=False):
        for point in focal_points:
            self.context.request.focal_points.append(FocalPoint.from_dict(point))

        if self.context.request.focal_points and self.context.modules.storage and not points_from_storage:
            storage = self.context.modules.storage
            points = []
            for point in self.context.request.focal_points:
                points.append(point.to_dict())

            storage.put_detector_data(self.smart_storage_key, points)

        if self.running_smart_detection:
            self.should_run_image_operations = True
            return

        self.do_image_operations()

    def do_image_operations(self):
        self.manual_crop()
        self.calculate_target_dimensions()
        self.adjust_focal_points()

        if self.context.request.debug:
            self.debug()
        else:
            if self.context.request.fit_in:
                self.fit_in_resize()
            else:
                self.auto_crop()
                self.resize()
            self.flip()

        self.done_callback()

    def manual_crop(self):
        if self.context.request.should_crop:
            limit = lambda dimension, maximum: min(max(dimension, 0), maximum)

            source_width, source_height = self.engine.size
            crop = self.context.request.crop

            crop['left'] = limit(crop['left'], source_width)
            crop['top'] = limit(crop['top'], source_height)
            crop['right'] = limit(crop['right'], source_width)
            crop['bottom'] = limit(crop['bottom'], source_height)

            if crop['left'] >= crop['right'] or crop['top'] >= crop['bottom']:
                self.context.request.should_crop = False
                crop['left'] = crop['right'] = crop['top'] = crop['bottom'] = 0
                return

            self.engine.crop(crop['left'], crop['top'], crop['right'], crop['bottom'])

    def auto_crop(self):
        source_width, source_height = self.engine.size

        target_height = self.target_height or 1
        target_width = self.target_width or 1

        source_ratio = round(float(source_width) / source_height, 2)
        target_ratio = round(float(target_width) / target_height, 2)

        if source_ratio == target_ratio:
            return

        focal_x, focal_y = self.get_center_of_mass()

        if self.target_width / source_width > self.target_height / source_height:
            crop_width = source_width
            crop_height = int(round(source_width * self.target_height / target_width, 0))
        else:
            crop_width = int(round(math.ceil(self.target_width * source_height / target_height), 0))
            crop_height = source_height

        crop_left = int(round(min(max(focal_x - (crop_width / 2), 0.0), source_width - crop_width)))
        crop_right = min(crop_left + crop_width, source_width)

        crop_top = int(round(min(max(focal_y - (crop_height / 2), 0.0), source_height - crop_height)))
        crop_bottom = min(crop_top + crop_height, source_height)

        self.engine.crop(crop_left, crop_top, crop_right, crop_bottom)

    def flip(self):
        if self.context.request.horizontal_flip:
            self.engine.flip_horizontally()
        if self.context.request.vertical_flip:
            self.engine.flip_vertically()

    def get_center_of_mass(self):
        total_weight = 0.0
        total_x = 0.0
        total_y = 0.0

        for focal_point in self.focal_points:
            total_weight += focal_point.weight

            total_x += focal_point.x * focal_point.weight
            total_y += focal_point.y * focal_point.weight

        x = total_x / total_weight
        y = total_y / total_weight

        return x, y

    def resize(self):
        source_width, source_height = self.engine.size
        if self.target_width == source_width and self.target_height == source_height:
            return
        self.engine.resize(self.target_width or 1, self.target_height or 1)  # avoiding 0px images

    def fit_in_resize(self):
        source_width, source_height = self.engine.size

        #invert width and height if image orientation is not the same as request orientation and need adaptive
        if self.context.request.adaptive and (
            (source_width - source_height < 0 and self.target_width - self.target_height > 0) or
            (source_width - source_height > 0 and self.target_width - self.target_height < 0)
        ):
            tmp = self.context.request.width
            self.context.request.width = self.context.request.height
            self.context.request.height = tmp
            tmp = self.target_width
            self.target_width = self.target_height
            self.target_height = tmp

        if self.target_width >= source_width and self.target_height >= source_height:
            return

        if source_width / self.target_width >= source_height / self.target_height:
            resize_height = round(source_height * self.target_width / source_width)
            resize_width = self.target_width
        else:
            resize_height = self.target_height
            resize_width = round(source_width * self.target_height / source_height)

        self.engine.resize(resize_width, resize_height)

    def debug(self):
        if not self.context.request.focal_points:
            return

        for point in self.context.request.focal_points:
            if point.width <= 1:
                point.width = 10
            if point.height <= 1:
                point.height = 10
            self.engine.draw_rectangle(int(point.x - (point.width / 2)),
                                       int(point.y - (point.height / 2)),
                                       point.width,
                                       point.height)

########NEW FILE########
__FILENAME__ = url
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import re
from urllib import quote


class Url(object):

    unsafe_or_hash = r'(?:(?:(?P<unsafe>unsafe)|(?P<hash>[^/]{28,}?))/)?'
    debug = '(?:(?P<debug>debug)/)?'
    meta = '(?:(?P<meta>meta)/)?'
    trim = '(?:(?P<trim>trim(?::(?:top-left|bottom-right))?(?::\d+)?)/)?'
    crop = '(?:(?P<crop_left>\d+)x(?P<crop_top>\d+):(?P<crop_right>\d+)x(?P<crop_bottom>\d+)/)?'
    fit_in = '(?:(?P<adaptive>adaptive-)?(?P<fit_in>fit-in)/)?'
    dimensions = '(?:(?P<horizontal_flip>-)?(?P<width>(?:\d+|orig))?x(?P<vertical_flip>-)?(?P<height>(?:\d+|orig))?/)?'
    halign = r'(?:(?P<halign>left|right|center)/)?'
    valign = r'(?:(?P<valign>top|bottom|middle)/)?'
    smart = r'(?:(?P<smart>smart)/)?'
    filters = r'(?:filters:(?P<filters>.+?\))/)?'
    image = r'(?P<image>.+)'

    compiled_regex = None

    @classmethod
    def regex(cls, has_unsafe_or_hash=True):
        reg = ['/?']

        if has_unsafe_or_hash:
            reg.append(cls.unsafe_or_hash)
        reg.append(cls.debug)
        reg.append(cls.meta)
        reg.append(cls.trim)
        reg.append(cls.crop)
        reg.append(cls.fit_in)
        reg.append(cls.dimensions)
        reg.append(cls.halign)
        reg.append(cls.valign)
        reg.append(cls.smart)
        reg.append(cls.filters)
        reg.append(cls.image)

        return ''.join(reg)

    @classmethod
    def parse_decrypted(cls, url):
        if cls.compiled_regex:
            reg = cls.compiled_regex
        else:
            reg = cls.compiled_regex = re.compile(cls.regex(has_unsafe_or_hash=False))

        result = reg.match(url)

        if not result:
            return None

        result = result.groupdict()

        int_or_0 = lambda value: 0 if value is None else int(value)
        values = {
            'debug': result['debug'] == 'debug',
            'meta': result['meta'] == 'meta',
            'trim': result['trim'],
            'crop': {
                'left': int_or_0(result['crop_left']),
                'top': int_or_0(result['crop_top']),
                'right': int_or_0(result['crop_right']),
                'bottom': int_or_0(result['crop_bottom'])
            },
            'adaptive': result['adaptive'] == 'adaptive',
            'fit_in': result['fit_in'] == 'fit-in',
            'width': result['width'] == 'orig' and 'orig' or int_or_0(result['width']),
            'height': result['height'] == 'orig' and 'orig' or int_or_0(result['height']),
            'horizontal_flip': result['horizontal_flip'] == '-',
            'vertical_flip': result['vertical_flip'] == '-',
            'halign': result['halign'] or 'center',
            'valign': result['valign'] or 'middle',
            'smart': result['smart'] == 'smart',
            'filters': result['filters'] or '',
            'image': 'image' in result and result['image'] or None
        }

        return values

    @classmethod
    def generate_options(cls,
                         debug=False,
                         width=0,
                         height=0,
                         smart=False,
                         meta=False,
                         trim=None,
                         adaptive=False,
                         fit_in=False,
                         horizontal_flip=False,
                         vertical_flip=False,
                         halign='center',
                         valign='middle',
                         crop_left=None,
                         crop_top=None,
                         crop_right=None,
                         crop_bottom=None,
                         filters=None):

        url = []

        if debug:
            url.append('debug')

        if meta:
            url.append('meta')

        if trim:
            if isinstance(trim, bool):
                url.append('trim')
            else:
                url.append('trim:%s' % trim)

        crop = crop_left or crop_top or crop_right or crop_bottom
        if crop:
            url.append('%sx%s:%sx%s' % (
                crop_left,
                crop_top,
                crop_right,
                crop_bottom
            ))

        if fit_in:
            if adaptive:
                url.append('adaptive-fit-in')
            else:
                url.append('fit-in')

        if horizontal_flip:
            width = '-%s' % width
        if vertical_flip:
            height = '-%s' % height

        if width or height:
            url.append('%sx%s' % (width, height))

        if halign != 'center':
            url.append(halign)
        if valign != 'middle':
            url.append(valign)

        if smart:
            url.append('smart')

        if filters:
            url.append('filters:%s' % filters)

        return '/'.join(url)

    @classmethod
    def encode_url(kls, url):
        return quote(url, '/:?%=&()~",\'')

########NEW FILE########
__FILENAME__ = url_composer
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import sys
import optparse

from thumbor import __version__
from thumbor.crypto import Cryptor, Signer
from thumbor.url import Url
from thumbor.config import Config


def main(arguments=None):
    '''Converts a given url with the specified arguments.'''
    if arguments is None:
        arguments = sys.argv[1:]

    parser = optparse.OptionParser(usage='thumbor-url [options] imageurl or type thumbor-url -h (--help) for help', description=__doc__, version=__version__)

    parser.add_option('-l', '--key_file', dest='key_file', default=None, help='The file to read the security key from [default: %default].')
    parser.add_option('-k', '--key', dest='key', default=None, help='The security key to encrypt the url with [default: %default].')
    parser.add_option('-w', '--width', dest='width', type='int', default=0, help='The target width for the image [default: %default].')
    parser.add_option('-e', '--height', dest='height', type='int', default=0, help='The target height for the image [default: %default].')
    parser.add_option('-n', '--fitin', dest='fitin', action='store_true', default=False, help='Indicates that fit-in resizing should be performed.')
    parser.add_option('-m', '--meta', dest='meta', action='store_true', default=False, help='Indicates that meta information should be retrieved.')
    parser.add_option('', '--adaptive', action='store_true', dest='adaptive', default=False, help='Indicates that adaptive fit-in cropping should be used.')
    parser.add_option('-s', '--smart', action='store_true', dest='smart', default=False, help='Indicates that smart cropping should be used.')
    parser.add_option('-t', '--trim', action='store_true', default=False, help='Indicate that surrounding whitespace should be trimmed.')
    parser.add_option('-f', '--horizontal-flip', action='store_true', dest='horizontal_flip', default=False, help='Indicates that the image should be horizontally flipped.')
    parser.add_option('-v', '--vertical-flip', action='store_true', dest='vertical_flip', default=False, help='Indicates that the image should be vertically flipped.')
    parser.add_option('-a', '--halign', dest='halign', default='center', help='The horizontal alignment to use for cropping [default: %default].')
    parser.add_option('-i', '--valign', dest='valign', default='middle', help='The vertical alignment to use for cropping [default: %default].')
    parser.add_option('', '--filters', dest='filters', default='', help='Filters to be applied to the image, e.g. brightness(10) [default: %default].')
    parser.add_option('-o', '--old-format', dest='old', action='store_true', default=False, help='Indicates that thumbor should generate old-format urls [default: %default].')

    parser.add_option('-c', '--crop', dest='crop', default=None, help='The coordinates of the points to manual cropping in the format leftxtop:rightxbottom (100x200:400x500) [default: %default].')

    (parsed_options, arguments) = parser.parse_args(arguments)

    if not arguments:
        print 'Error: The image argument is mandatory. For more information type thumbor-url -h'
        return

    image_url = arguments[0]
    if image_url.startswith('/'):
        image_url = image_url[1:]

    try:
        config = Config.load(None)
    except:
        config = None

    if not parsed_options.key and not config:
        print 'Error: The -k or --key argument is mandatory. For more information type thumbor-url -h'
        return

    if parsed_options.key_file:
        f = open(parsed_options.key_file)
        security_key = f.read().strip()
        f.close()
    else:
        security_key = config.SECURITY_KEY if not parsed_options.key else parsed_options.key

    crop_left = crop_top = crop_right = crop_bottom = 0
    if parsed_options.crop:
        crops = parsed_options.crop.split(':')
        crop_left, crop_top = crops[0].split('x')
        crop_right, crop_bottom = crops[1].split('x')

    if parsed_options.old:
        crypt = Cryptor(security_key)
        opt = crypt.encrypt(parsed_options.width,
                            parsed_options.height,
                            parsed_options.smart,
                            parsed_options.adaptive,
                            parsed_options.fitin,
                            parsed_options.horizontal_flip,
                            parsed_options.vertical_flip,
                            parsed_options.halign,
                            parsed_options.valign,
                            parsed_options.trim,
                            crop_left,
                            crop_top,
                            crop_right,
                            crop_bottom,
                            parsed_options.filters,
                            image_url)
        url = '/%s/%s' % (opt, image_url)

        print 'Encrypted URL:'
    else:
        signer = Signer(security_key)
        url = Url.generate_options(
            width=parsed_options.width,
            height=parsed_options.height,
            smart=parsed_options.smart,
            meta=parsed_options.meta,
            adaptive=parsed_options.adaptive,
            fit_in=parsed_options.fitin,
            horizontal_flip=parsed_options.horizontal_flip,
            vertical_flip=parsed_options.vertical_flip,
            halign=parsed_options.halign,
            valign=parsed_options.valign,
            trim=parsed_options.trim,
            crop_left=crop_left,
            crop_top=crop_top,
            crop_right=crop_right,
            crop_bottom=crop_bottom,
            filters=parsed_options.filters
        )

        url = '%s/%s' % (url, image_url)
        url = url.lstrip('/')

        signature = signer.signature(url)

        url = '/%s/%s' % (signature, url)

        print 'Signed URL:'

    print url
    return url

if __name__ == '__main__':
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import logging
from functools import reduce, wraps


def real_import(name):
    if '.' in name:
        return reduce(getattr, name.split('.')[1:], __import__(name))
    return __import__(name)

logger = logging.getLogger('thumbor')


class on_exception(object):

    def __init__(self, callback, exception_class=Exception):
        self.callback = callback
        self.exception_class = exception_class

    def __call__(self, fn):
        def wrapper(*args, **kwargs):
            self_instance = args[0] if len(args) > 0 else None
            try:
                return fn(*args, **kwargs)
            except self.exception_class:
                if self.callback:
                    self.callback(self_instance) if self_instance else self.callback()
                raise
        return wrapper


class deprecated(object):

    def __init__(self, msg=None):
        self.msg = ": {0}".format(msg) if msg else "."

    def __call__(self, func):
        @wraps(func)
        def new_func(*args, **kwargs):
            logger.warn(
                "Deprecated function {0}{1}".format(func.__name__, self.msg)
            )
            return func(*args, **kwargs)
        return new_func

########NEW FILE########
__FILENAME__ = app_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from pyvows import Vows, expect

from thumbor.app import ThumborServiceApp
from thumbor.context import Context
from thumbor.config import Config


@Vows.batch
class AppVows(Vows.Context):

    class CanCreateApp(Vows.Context):
        def topic(self):
            context = Context(None, Config(), None)
            return ThumborServiceApp(context)

        def should_be_ThumborServiceApp(self, topic):
            expect(topic).to_be_instance_of(ThumborServiceApp)

########NEW FILE########
__FILENAME__ = cascade_loader_detector_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from os import path

from pyvows import Vows, expect
ctx = Vows.Context

from mock import Mock
from thumbor.detectors.local_detector import CascadeLoaderDetector
from thumbor.point import FocalPoint


cascade_file_path = path.join(
    __file__, '..', '..', 'thumbor',
    'detectors', 'face_detector', 'haarcascade_frontalface_alt.xml')
CASCADE_FILE_PATH = path.abspath(cascade_file_path)


@Vows.batch
class CascadeLoaderDetectorVows(ctx):

    class CreateInstanceVows(ctx):
        def topic(self):
            return CascadeLoaderDetector("context", 1, "detectors")

        def should_not_be_null(self, topic):
            expect(topic).not_to_be_null()
            expect(topic).not_to_be_an_error()

        class LoadCascadefile(ctx):

            def topic(self, detector):
                detector.load_cascade_file(None, CASCADE_FILE_PATH)
                return detector

            def should_set_the_cascade_attribute_in_the_class(self, topic):
                # ugly check because there is no becautifull way to see
                # if this object is an instance of some class or if it has some
                # kind of attribute
                expect(repr(topic.__class__.cascade)).to_include('<HaarClassifierCascade')

        class GetMinSizeFor(ctx):

            def topic(self, detector):
                return detector.get_min_size_for((400, 700))

            def should_return_the_expected_min_size(self, topic):
                expect(topic).to_equal((26, 26))

        # couldnt make this work because of a pyvows bug
        # on the order of the setup/teardown execution
        #class GetFeatures(ctx):

            #def setup(self):
                #self.cv = patch('thumbor.detectors.local_detector.cv')
                #self.cv.start()

            #def teardown(self):
                #self.cv.stop()

            #def topic(self, detector):
                #return detector.get_features()

        class Detect(ctx):

            def topic(self, detector):
                detector.context = Mock()
                detector.get_features = Mock(return_value=[((1, 2, 3, 4), 10), ((5, 6, 7, 8), 11)])
                detector.detect(lambda: None)
                return detector

            def should_append_2_focal_points_to_context_request(self, topic):
                expect(topic.context.request.focal_points.append.call_count).to_equal(2)

            def should_append_the_returned_focal_points_to_context_request(self, topic):
                focal_point1_repr = FocalPoint.from_square(1, 2, 3, 4).to_dict()
                focal_point2_repr = FocalPoint.from_square(5, 6, 7, 8).to_dict()

                calls = topic.context.request.focal_points.append.call_args_list

                first_call_arg_repr = calls[0][0][0].to_dict()
                secon_call_arg_repr = calls[1][0][0].to_dict()

                expect(first_call_arg_repr).to_equal(focal_point1_repr)
                expect(secon_call_arg_repr).to_equal(focal_point2_repr)

########NEW FILE########
__FILENAME__ = config_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from pyvows import Vows, expect

from thumbor.config import Config

STORAGE_DEFAULT_VALUE = 'thumbor.storages.file_storage'

TEST_DATA = (
    ('MAX_WIDTH', 0),
    ('MAX_HEIGHT', 0),
    ('ALLOWED_SOURCES', []),
    ('QUALITY', 80),
    ('LOADER', 'thumbor.loaders.http_loader'),
    ('STORAGE', STORAGE_DEFAULT_VALUE),
    ('ENGINE', 'thumbor.engines.pil'),
    ('ALLOW_UNSAFE_URL', True),
    ('FILE_LOADER_ROOT_PATH', '/tmp'),
    ('STORAGE_EXPIRATION_SECONDS', 60 * 60 * 24 * 30),
    ('STORES_CRYPTO_KEY_FOR_EACH_IMAGE', False),
    ('MONGO_STORAGE_SERVER_HOST', 'localhost'),
    ('MONGO_STORAGE_SERVER_PORT', 27017),
    ('MONGO_STORAGE_SERVER_DB', 'thumbor'),
    ('MONGO_STORAGE_SERVER_COLLECTION', 'images'),
    ('REDIS_STORAGE_SERVER_HOST', 'localhost'),
    ('REDIS_STORAGE_SERVER_PORT', 6379),
    ('REDIS_STORAGE_SERVER_DB', 0),
    ('MIXED_STORAGE_FILE_STORAGE', 'thumbor.storages.no_storage'),
    ('MIXED_STORAGE_CRYPTO_STORAGE', 'thumbor.storages.no_storage'),
    ('MIXED_STORAGE_DETECTOR_STORAGE', 'thumbor.storages.no_storage'),
    ('DETECTORS', []),
    ('FACE_DETECTOR_CASCADE_FILE', 'haarcascade_frontalface_alt.xml'),
    ('FILTERS', [
        'thumbor.filters.brightness',
        'thumbor.filters.contrast',
        'thumbor.filters.rgb',
        'thumbor.filters.round_corner',
        'thumbor.filters.quality',
        'thumbor.filters.noise',
        'thumbor.filters.watermark',
        'thumbor.filters.equalize',
        'thumbor.filters.fill',
        'thumbor.filters.sharpen',
        'thumbor.filters.strip_icc',
        'thumbor.filters.frame',
        'thumbor.filters.grayscale',
        'thumbor.filters.format',
        'thumbor.filters.max_bytes',
        'thumbor.filters.convolution',
        'thumbor.filters.blur',
        'thumbor.filters.extract_focal',
    ])
)


@Vows.batch
class Configuration(Vows.Context):

    class DefaultThumborConf(Vows.Context):
        def topic(self):
            for data in TEST_DATA:
                yield data

        class VerifyDefaultValueContext(Vows.Context):
            def topic(self, data):
                key, default_value = data
                cfg = Config()
                return (getattr(cfg, key), default_value)

            def should_have_default_value(self, topic):
                expect(topic).not_to_be_an_error()
                expect(topic).to_length(2)
                actual, expected = topic
                expect(actual).not_to_be_null()
                expect(actual).to_equal(expected)

    class WhenSettingAnAlias(Vows.Context):

        def topic(self):
            Config.alias('OTHER_ENGINE', 'ENGINE')
            return Config(OTHER_ENGINE='x')

        def should_set_engine_attribute(self, config):
            expect(config.ENGINE).to_equal('x')

        def should_set_other_engine_attribute(self, config):
            expect(config.OTHER_ENGINE).to_equal('x')

    class WhenSettingAnAliasedKey(Vows.Context):
        def topic(self):
            Config.alias('LOADER_ALIAS', 'LOADER')
            return Config(LOADER='y')

        def should_set_loader_attribute(self, config):
            expect(config.LOADER).to_equal('y')

        def should_set_loader_alias_attribute(self, config):
            expect(config.LOADER_ALIAS).to_equal('y')

    class WithAliasedAliases(Vows.Context):
        def topic(self):
            Config.alias('STORAGE_ALIAS', 'STORAGE')
            Config.alias('STORAGE_ALIAS_ALIAS', 'STORAGE_ALIAS')
            return Config(STORAGE_ALIAS_ALIAS='z')

        def should_set_storage_attribute(self, config):
            expect(config.STORAGE).to_equal('z')

        def should_set_storage_alias_attribute(self, config):
            expect(config.STORAGE_ALIAS).to_equal('z')

        def should_set_storage_alias_alias_attribute(self, config):
            expect(config.STORAGE_ALIAS_ALIAS).to_equal('z')

        class WithDefaultValues(Vows.Context):
            def topic(self):
                return Config()

            def should_set_storage_attribute(self, config):
                expect(config.STORAGE).to_equal(STORAGE_DEFAULT_VALUE)

            def should_set_storage_alias_attribute(self, config):
                expect(config.STORAGE_ALIAS).to_equal(STORAGE_DEFAULT_VALUE)

            def should_set_storage_alias_alias_attribute(self, config):
                expect(config.STORAGE_ALIAS_ALIAS).to_equal(STORAGE_DEFAULT_VALUE)

            def should_be_a_derpconf(self, config):
                expect(config.__class__.__module__).to_equal('derpconf.config')

#class ConfigContext(Vows.Context):
    #def _camel_split(self, string):
        #return re.sub('((?=[A-Z][a-z])|(?<=[a-z])(?=[A-Z])|(?=[0-9]\b))', ' ', string).strip()

    #def _config_name(self):
        #return '_'.join(self._camel_split(self.__class__.__name__).split(' ')).upper()

    #def topic(self):
        #config = self._config_name()
        #return getattr(conf, config)

    #def is_not_an_error(self, topic):
        #expect(topic).not_to_be_an_error()

#class NumericConfigContext(ConfigContext):

    #def is_numeric(self, topic):
        #expect(topic).to_be_numeric()

#@Vows.batch
#class Configuration(Vows.Context):

    #class Defaults(Vows.Context):

        ##class SecurityKey(ConfigContext):

            ##def defaults_to_null(self, topic):

                ##expect(topic).to_be_null()

        #class AllowUnsafeUrl(ConfigContext):

            #def defaults_to_true(self, topic):
                #expect(topic).to_be_true()

        #class MaxWidth(NumericConfigContext):

            #def defaults_to_0(self, topic):
                #expect(topic).to_equal(0)

        #class MaxHeight(NumericConfigContext):

            #def defaults_to_0(self, topic):
                #expect(topic).to_equal(0)

        ##class AllowedSources(ConfigContext):

            ##def defaults_to_empty(self, topic):
                ##expect(topic).to_be_empty()

        #class Quality(NumericConfigContext):

            #def defaults_to_85(self, topic):
                #expect(topic).to_equal(85)

        ##class Loader(ConfigContext):

            ##def defaults_to_http_loader(self, topic):
                ##expect(topic).to_equal('thumbor.loaders.http_loader')

        #class MaxSourceSize(NumericConfigContext):

            #def defaults_to_0(self, topic):
                #expect(topic).to_equal(0)

        #class RequestTimeoutSeconds(NumericConfigContext):

            #def defaults_to_120(self, topic):
                #expect(topic).to_equal(120)

        #class Engine(ConfigContext):

            #def defaults_to_pil(self, topic):
                #expect(topic).to_equal('thumbor.engines.pil')

        #class Storage(ConfigContext):

            #def defaults_to_file_storage(self, topic):
                #expect(topic).to_equal('thumbor.storages.file_storage')

            #class StorageExpirationSeconds(NumericConfigContext):

                #def defaults_to_one_month(self, topic):
                    #expect(topic).to_equal(60 * 60 * 24 * 30)

            #class MongoStorage(Vows.Context):

                #class MongoStorageServerHost(ConfigContext):

                    #def defaults_to_localhost(self, topic):
                        #expect(topic).to_equal('localhost')

                #class MongoStorageServerPort(NumericConfigContext):

                    #def defaults_to_27017(self, topic):
                        #expect(topic).to_equal(27017)

                #class MongoStorageServerDb(ConfigContext):

                    #def defaults_to_thumbor(self, topic):
                        #expect(topic).to_equal('thumbor')

                #class MongoStorageServerCollection(ConfigContext):

                    #def defaults_to_images(self, topic):
                        #expect(topic).to_equal('images')

            #class RedisStorage(Vows.Context):

                #class RedisStorageServerHost(ConfigContext):

                    #def defaults_to_localhost(self, topic):
                        #expect(topic).to_equal('localhost')

                #class RedisStorageServerPort(NumericConfigContext):

                    #def defaults_to_6379(self, topic):
                        #expect(topic).to_equal(6379)

                #class RedisStorageServerDb(NumericConfigContext):

                    #def defaults_to_0(self, topic):
                        #expect(topic).to_equal(0)

            #class MySqlStorage(Vows.Context):

                #class MysqlStorageServerHost(ConfigContext):

                    #def defaults_to_localhost(self, topic):
                        #expect(topic).to_equal('localhost')

                #class MysqlStorageServerPort(NumericConfigContext):

                    #def defaults_to_3306(self, topic):
                        #expect(topic).to_equal(3306)

                #class MysqlStorageServerUser(ConfigContext):

                    #def defaults_to_root(self, topic):
                        #expect(topic).to_equal('root')

                #class MysqlStorageServerPassword(ConfigContext):

                    #def defaults_to_empty(self, topic):
                        #expect(topic).to_be_empty()

                #class MysqlStorageServerDb(ConfigContext):

                    #def defaults_to_thumbor(self, topic):
                        #expect(topic).to_equal('thumbor')

                #class MysqlStorageServerTable(ConfigContext):

                    #def defaults_to_images(self, topic):
                        #expect(topic).to_equal('images')

        #class Engines(Vows.Context):

            #class ImageMagick(Vows.Context):

                #class MagickwandPath(ConfigContext):

                    #def defaults_to_empty(self, topic):
                        #expect(topic).to_be_empty()

            #class Json(Vows.Context):

                #class MetaCallbackName(ConfigContext):

                    #def defaults_to_null(self, topic):
                        #expect(topic).to_be_null()

        #class Detectors(ConfigContext):

            #def default_includes_face_detector(self, topic):
                #expect(topic).to_include('thumbor.detectors.face_detector')

            #def default_includes_feature_detector(self, topic):
                #expect(topic).to_include('thumbor.detectors.feature_detector')

            #class FaceDetector(Vows.Context):
                #class FaceDetectorCascadeFile(ConfigContext):

                    #def defaults_to_haarcascade_frontalface_alt(self, topic):
                        #expect(topic).to_equal('haarcascade_frontalface_alt.xml')

########NEW FILE########
__FILENAME__ = console_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from pyvows import Vows, expect

import thumbor.console
from thumbor.context import ServerParameters


@Vows.batch
class ConsoleVows(Vows.Context):

    class CanParseArguments(Vows.Context):
        def topic(self):
            server_parameters = thumbor.console.get_server_parameters(['-p', '2000'])
            return server_parameters

        def should_not_be_null(self, topic):
            expect(topic).not_to_be_null()

        def should_be_console(self, topic):
            expect(topic).to_be_instance_of(ServerParameters)

        def should_have_specific_port(self, topic):
            expect(topic.port).to_equal(2000)

        def should_use_the_default_thumbor_app(self, topic):
            expect(topic.app_class).to_equal('thumbor.app.ThumborServiceApp')

    class CanUseACustomApp(Vows.Context):
        def topic(self):
            server_parameters = thumbor.console.get_server_parameters(['-a', 'vows.fixtures.custom_app.MyCustomApp'])
            return server_parameters

        def should_have_my_custom_app_value(self, topic):
            expect(topic.app_class).to_equal('vows.fixtures.custom_app.MyCustomApp')

########NEW FILE########
__FILENAME__ = context_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from pyvows import Vows, expect

from thumbor.context import Context, ServerParameters


@Vows.batch
class ContextVows(Vows.Context):

    class CanCreateContext(Vows.Context):
        def topic(self):
            ctx = Context()
            return ctx

        def should_not_be_null(self, topic):
            expect(topic).not_to_be_null()

        def should_be_context(self, topic):
            expect(topic).to_be_instance_of(Context)


@Vows.batch
class ServerParameterVows(Vows.Context):

    class CanCreateServerParameters(Vows.Context):
        def topic(self):
            params = ServerParameters(port=8888,
                                      ip='127.0.0.1',
                                      config_path='config_path',
                                      keyfile=None,
                                      log_level='log_level',
                                      app_class=None)
            return params

        def should_not_be_null(self, topic):
            expect(topic).not_to_be_null()

        def should_be_context(self, topic):
            expect(topic).to_be_instance_of(ServerParameters)

        def should_have_proper_port(self, topic):
            expect(topic.port).to_equal(8888)

        def should_have_proper_ip(self, topic):
            expect(topic.ip).to_equal('127.0.0.1')

        def should_have_proper_config_path(self, topic):
            expect(topic.config_path).to_equal('config_path')

        def should_have_null_keyfile(self, topic):
            expect(topic.keyfile).to_be_null()

        def should_have_proper_log_level(self, topic):
            expect(topic.log_level).to_equal('log_level')

        def should_have_null_app_class(self, topic):
            expect(topic.app_class).to_be_null()

########NEW FILE########
__FILENAME__ = crypto_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import hashlib
import base64
import hmac
import copy

from pyvows import Vows, expect

from thumbor.crypto import Cryptor, Signer


@Vows.batch
class CryptoVows(Vows.Context):
    def topic(self):
        return Cryptor(security_key="something")

    def should_be_crypto_instance(self, topic):
        expect(topic).to_be_instance_of(Cryptor)

    def should_calculate_salt(self, topic):
        expect(topic.security_key).to_equal('somethingsomethi')

    class DecryptInvalidString(Vows.Context):

        def topic(self, crypto):
            return crypto.decrypt('some string')

        def should_be_null(self, topic):
            expect(topic).to_be_null()

    class Encrypt(Vows.Context):
        def topic(self, crypto):
            return crypto.encrypt(width=300,
                                  height=300,
                                  smart=True,
                                  adaptive=False,
                                  fit_in=False,
                                  flip_horizontal=True,
                                  flip_vertical=True,
                                  halign="center",
                                  valign="middle",
                                  trim=True,
                                  crop_left=10,
                                  crop_top=11,
                                  crop_right=12,
                                  crop_bottom=13,
                                  filters='some_filter()',
                                  image="/some/image.jpg")

        def should_equal_encrypted_string(self, topic):
            encrypted_str = "hELdyDzyYtjXU5GhGxJVHjRvGrSP_iYKnIQbq_MuVq86rSObCeJvo2iXFRUjLgs" + \
                "U9wDzhqK9J_SHmpxDJHW_rBD8eilO26x2M_hzJfGB-V9cGF65GO_7CgJXI8Ktw188"
            expect(topic).to_equal(encrypted_str)

        class Decrypt(Vows.Context):

            def topic(self, encrypted, crypto):
                return crypto.decrypt(encrypted)

            def should_not_be_an_error(self, topic):
                expect(topic).not_to_be_an_error()

            def should_not_be_an_empty_dict(self, topic):
                expect(topic).not_to_be_empty()

            def should_have_300_of_width(self, topic):
                expect(topic['width']).to_equal(300)

            def should_have_200_of_height(self, topic):
                expect(topic['height']).to_equal(300)

            def should_have_smart_flag(self, topic):
                expect(topic['smart']).to_be_true()

            def should_not_have_fitin_flag(self, topic):
                expect(topic['fit_in']).to_be_false()

            def should_have_flip_horizontal_flag(self, topic):
                expect(topic['horizontal_flip']).to_be_true()

            def should_have_flip_vertical_flag(self, topic):
                expect(topic['vertical_flip']).to_be_true()

            def should_have_center_halign(self, topic):
                expect(topic['halign']).to_equal('center')

            def should_have_middle_valign(self, topic):
                expect(topic['valign']).to_equal('middle')

            def should_have_crop_left_of_10(self, topic):
                expect(topic['crop']['left']).to_equal(10)

            def should_have_crop_top_of_11(self, topic):
                expect(topic['crop']['top']).to_equal(11)

            def should_have_crop_right_of_12(self, topic):
                expect(topic['crop']['right']).to_equal(12)

            def should_have_crop_bottom_of_13(self, topic):
                expect(topic['crop']['bottom']).to_equal(13)

            def should_have_filter_as_some_filter(self, topic):
                expect(topic['filters']).to_equal('some_filter()')

            def should_have_image_hash(self, topic):
                image_hash = hashlib.md5('/some/image.jpg').hexdigest()
                expect(topic['image_hash']).to_equal(image_hash)

        class DecryptWrongKey(Vows.Context):

            def topic(self, encrypted, crypto):
                crypto2 = Cryptor(security_key="simething")

                return (crypto2.decrypt(encrypted), crypto.decrypt(encrypted))

            def should_return_empty(self, topic):
                wrong, right = topic
                expect(wrong['image_hash']).not_to_equal(right['image_hash'])


@Vows.batch
class SignerVows(Vows.Context):
    def topic(self):
        return Signer(security_key="something")

    def should_be_signer_instance(self, topic):
        expect(topic).to_be_instance_of(Signer)

    def should_have_security_key(self, topic):
        expect(topic.security_key).to_equal('something')

    class Sign(Vows.Context):
        def topic(self, signer):
            url = '10x11:12x13/-300x-300/center/middle/smart/some/image.jpg'
            expected = base64.urlsafe_b64encode(hmac.new('something', unicode(url).encode('utf-8'), hashlib.sha1).digest())
            return (signer.signature(url), expected)

        def should_equal_encrypted_string(self, test_data):
            topic, expected = test_data
            expect(topic).to_equal(expected)


BASE_IMAGE_URL = 'my.domain.com/some/image/url.jpg'
BASE_IMAGE_MD5 = 'f33af67e41168e80fcc5b00f8bd8061a'

BASE_PARAMS = {
    'width': 0,
    'height': 0,
    'smart': False,
    'adaptive': False,
    'fit_in': False,
    'flip_horizontal': False,
    'flip_vertical': False,
    'halign': 'center',
    'valign': 'middle',
    'trim': '',
    'crop_left': 0,
    'crop_top': 0,
    'crop_right': 0,
    'crop_bottom': 0,
    'filters': '',
    'image': ''
}

DECRYPT_TESTS = [
    {
        'params': {
            'width': 300, 'height': 200, 'image': BASE_IMAGE_URL
        },
        'result': {
            "horizontal_flip": False,
            "vertical_flip": False,
            "smart": False,
            "meta": False,
            "fit_in": False,
            "crop": {
                "left": 0,
                "top": 0,
                "right": 0,
                "bottom": 0
            },
            "valign": 'middle',
            "halign": 'center',
            "image_hash": BASE_IMAGE_MD5,
            "width": 300,
            "height": 200,
            'filters': '',
            'debug': False,
            'adaptive': False,
            'trim': None
        }
    },
    {
        'params': {
            'filters': "quality(20):brightness(10)",
            'image': BASE_IMAGE_URL
        },
        'result': {
            "horizontal_flip": False,
            "vertical_flip": False,
            "smart": False,
            "meta": False,
            "fit_in": False,
            "crop": {
                "left": 0,
                "top": 0,
                "right": 0,
                "bottom": 0
            },
            "valign": 'middle',
            "halign": 'center',
            "image_hash": BASE_IMAGE_MD5,
            "width": 0,
            "height": 0,
            'filters': 'quality(20):brightness(10)',
            'debug': False,
            'adaptive': False,
            'trim': None
        }
    }
]


@Vows.batch
class CryptoDecryptVows(Vows.Context):
    def topic(self):
        cryptor = Cryptor('my-security-key')
        for test in DECRYPT_TESTS:
            base_copy = copy.copy(BASE_PARAMS)
            base_copy.update(test['params'])
            encrypted = cryptor.encrypt(**base_copy)
            yield(cryptor.decrypt(encrypted), test['result'])

    def decrypted_result_should_match(self, test_data):
        decrypted, expected = test_data
        expect(decrypted).to_be_like(expected)

########NEW FILE########
__FILENAME__ = detector_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from pyvows import Vows, expect
ctx = Vows.Context

from thumbor.detectors import BaseDetector


def get_detector(name):
    class MockDetector:
        def __init__(self, context, index, detectors):
            self.context = context
            self.index = index
            self.detectors = detectors
            self.name = name

        def detect(self, callback):
            callback(self.name)

    return MockDetector


@Vows.batch
class BaseDetectorVows(ctx):

    class CreateInstanceVows(ctx):
        def topic(self):
            return BaseDetector("context", 1, "detectors")

        def should_not_be_null(self, topic):
            expect(topic).not_to_be_null()
            expect(topic).not_to_be_an_error()

    class DetectShouldRaise(ctx):
        def topic(self):
            BaseDetector("context", 1, "detectors").detect(None)

        def should_be_an_error(self, topic):
            expect(topic).to_be_an_error()
            expect(topic).to_be_an_error_like(NotImplementedError)

    class NextVows(ctx):
        @Vows.async_topic
        def topic(self, callback):
            detector = BaseDetector("context", 0, [
                get_detector("a"),
                get_detector("b")
            ])
            return detector.next(callback)

        def should_be_detector_b(self, topic):
            expect(topic.args[0]).to_equal("b")

    class LastDetectorVows(ctx):
        @Vows.async_topic
        def topic(self, callback):
            detector = BaseDetector("context", 0, [
                get_detector("a")
            ])
            return detector.next(callback)

        def should_be_null(self, topic):
            expect(topic.args).to_length(0)

########NEW FILE########
__FILENAME__ = file_error_handler_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from pyvows import Vows, expect

from thumbor import __version__
from thumbor.error_handlers.file import ErrorHandler
from thumbor.config import Config
from thumbor.context import Context, ServerParameters

import json,tempfile


class FakeRequest(object):
    def __init__(self):
        self.headers = {
            'header1': 'value1',
            'Cookie': 'cookie1=value; cookie2=value2;'
        }

        self.url = "test/"
        self.method = "GET"
        self.arguments = []
        self.body = "body"
        self.query = "a=1&b=2"
        self.remote_ip = "127.0.0.1"

    def full_url(self):
        return "http://test/%s" % self.url


class FakeHandler(object):
    def __init__(self):
        self.request = FakeRequest()

@Vows.batch
class ErrorHandlerVows(Vows.Context):
    class WhenInvalidConfiguration(Vows.Context):
        def topic(self):
            cfg = Config()
            ErrorHandler(cfg)

        def should_be_error(self, topic):
            expect(topic).to_be_an_error()
            expect(topic).to_be_an_error_like(RuntimeError)

    class WhenErrorOccurs(Vows.Context):
        def topic(self):
            #use temporary file to store logs
            tmp = tempfile.NamedTemporaryFile(prefix='thumborTest')

            cfg = Config(SECURITY_KEY='ACME-SEC', ERROR_FILE_LOGGER=tmp.name)
            server = ServerParameters(8889, 'localhost', 'thumbor.conf', None, 'info', None)
            server.security_key = 'ACME-SEC'
            ctx = Context(server, cfg, None)

            handler = ErrorHandler(cfg)
            http_handler = FakeHandler()

            handler.handle_error(ctx, http_handler, RuntimeError("Test"))
            #return content of file
            return tmp.read()
      
        def should_have_called_client(self, topic):
            #check against json version
            expect(json.loads(topic)).to_be_like ({
                'Http': {
                    'url': 'http://test/test/',
                    'method': 'GET',
                    'data': [],
                    'body': "body",
                    'query_string': "a=1&b=2"
                },
                'interfaces.User': {
                    'ip': "127.0.0.1",
                },
                'exception': 'Test',
                'extra': {
                    'thumbor-version':  __version__,
                    'Headers' : {
                        'header1': 'value1', 
                        'Cookie': {
                            'cookie1': 'value', 
                            'cookie2': 'value2'
                        }
                    },
                }
            })


########NEW FILE########
__FILENAME__ = file_loader_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from os.path import abspath, join, dirname

from pyvows import Vows, expect

from thumbor.context import Context
from thumbor.config import Config
from thumbor.loaders.file_loader import load


STORAGE_PATH = abspath(join(dirname(__file__), 'fixtures/'))


@Vows.batch
class FileLoaderVows(Vows.Context):

    def topic(self):
        config = Config(FILE_LOADER_ROOT_PATH=STORAGE_PATH)
        return Context(config=config)

    class LoadsFromRootPath(Vows.Context):
        @Vows.async_topic
        def topic(self, callback, context):
            load(context, 'image.jpg', callback)

        def should_load_file(self, data):
            expect(data.args[0]).to_equal(open(join(STORAGE_PATH, 'image.jpg')).read())

    class DoesNotLoadInexistentFile(Vows.Context):
        @Vows.async_topic
        def topic(self, callback, context):
            load(context, 'image_NOT.jpg', callback)

        def should_load_file(self, data):
            expect(data.args[0]).to_equal(None)

    class DoesNotLoadFromOutsideRootPath(Vows.Context):
        @Vows.async_topic
        def topic(self, callback, context):
            load(context, '../file_loader_vows.py', callback)

        def should_load_file(self, data):
            expect(data.args[0]).to_equal(None)

########NEW FILE########
__FILENAME__ = file_storage_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from os.path import exists, dirname, join
import random
import shutil

from pyvows import Vows, expect

import thumbor.storages.file_storage as Storage
from thumbor.storages.file_storage import Storage as FileStorage
from thumbor.context import Context
from thumbor.config import Config
from fixtures.storage_fixture import IMAGE_URL, SAME_IMAGE_URL, IMAGE_BYTES, get_server


@Vows.batch
class FileStorageVows(Vows.Context):
    class CreatesRootPathIfNoneFound(Vows.Context):
        def topic(self):
            config = Config(FILE_STORAGE_ROOT_PATH="/tmp/thumbor/file_storage/%s" % random.randint(1, 10000000))
            storage = FileStorage(Context(config=config, server=get_server('ACME-SEC')))
            storage.ensure_dir(config.FILE_STORAGE_ROOT_PATH)
            return exists(config.FILE_STORAGE_ROOT_PATH)

        def should_exist(self, topic):
            expect(topic).to_be_true()

    class CanStoreImage(Vows.Context):
        def topic(self):
            config = Config(FILE_STORAGE_ROOT_PATH="/tmp/thumbor/file_storage/")
            storage = FileStorage(Context(config=config, server=get_server('ACME-SEC')))
            storage.put(IMAGE_URL % 1, IMAGE_BYTES)
            return storage.get(IMAGE_URL % 1)

        def should_be_in_catalog(self, topic):
            expect(topic).not_to_be_null()
            expect(topic).not_to_be_an_error()

    class CanStoreImagesInSameFolder(Vows.Context):
        def topic(self):
            config = Config(FILE_STORAGE_ROOT_PATH="/tmp/thumbor/file_storage/")
            root_path = join(config.FILE_STORAGE_ROOT_PATH, dirname(SAME_IMAGE_URL % 999))
            if exists(root_path):
                shutil.rmtree(root_path)

            old_exists = Storage.storages.exists
            Storage.storages.exists = lambda path: False
            try:
                storage = Storage.Storage(Context(config=config, server=get_server('ACME-SEC')))

                storage.put(SAME_IMAGE_URL % 998, IMAGE_BYTES)
                storage.put(SAME_IMAGE_URL % 999, IMAGE_BYTES)
            finally:
                Storage.storages.exists = old_exists

            return storage.get(SAME_IMAGE_URL % 999)

        def should_be_in_catalog(self, topic):
            expect(topic).not_to_be_null()
            expect(topic).not_to_be_an_error()

    class CanGetImage(Vows.Context):
        def topic(self):
            config = Config(FILE_STORAGE_ROOT_PATH="/tmp/thumbor/file_storage/")
            storage = FileStorage(Context(config=config, server=get_server('ACME-SEC')))

            storage.put(IMAGE_URL % 2, IMAGE_BYTES)
            return storage.get(IMAGE_URL % 2)

        def should_not_be_null(self, topic):
            expect(topic).not_to_be_null()
            expect(topic).not_to_be_an_error()

        def should_have_proper_bytes(self, topic):
            expect(topic).to_equal(IMAGE_BYTES)

    class CryptoVows(Vows.Context):
        class RaisesIfInvalidConfig(Vows.Context):
            def topic(self):
                config = Config(FILE_STORAGE_ROOT_PATH="/tmp/thumbor/file_storage/", STORES_CRYPTO_KEY_FOR_EACH_IMAGE=True)
                storage = FileStorage(Context(config=config, server=get_server('')))
                storage.put(IMAGE_URL % 3, IMAGE_BYTES)
                storage.put_crypto(IMAGE_URL % 3)

            def should_be_an_error(self, topic):
                expect(topic).to_be_an_error_like(RuntimeError)
                expect(topic).to_have_an_error_message_of(
                    "STORES_CRYPTO_KEY_FOR_EACH_IMAGE can't be True if no SECURITY_KEY specified"
                )

        class GettingCryptoForANewImageReturnsNone(Vows.Context):
            def topic(self):
                config = Config(FILE_STORAGE_ROOT_PATH="/tmp/thumbor/file_storage/", STORES_CRYPTO_KEY_FOR_EACH_IMAGE=True)
                storage = FileStorage(Context(config=config, server=get_server('ACME-SEC')))
                return storage.get_crypto(IMAGE_URL % 9999)

            def should_be_null(self, topic):
                expect(topic).to_be_null()

        class DoesNotStoreIfConfigSaysNotTo(Vows.Context):
            def topic(self):
                config = Config(FILE_STORAGE_ROOT_PATH="/tmp/thumbor/file_storage/")
                storage = FileStorage(Context(config=config, server=get_server('ACME-SEC')))
                storage.put(IMAGE_URL % 5, IMAGE_BYTES)
                storage.put_crypto(IMAGE_URL % 5)
                return storage.get_crypto(IMAGE_URL % 5)

            def should_be_null(self, topic):
                expect(topic).to_be_null()

        class CanStoreCrypto(Vows.Context):
            def topic(self):
                config = Config(FILE_STORAGE_ROOT_PATH="/tmp/thumbor/file_storage/", STORES_CRYPTO_KEY_FOR_EACH_IMAGE=True)
                storage = FileStorage(Context(config=config, server=get_server('ACME-SEC')))

                storage.put(IMAGE_URL % 6, IMAGE_BYTES)
                storage.put_crypto(IMAGE_URL % 6)
                return storage.get_crypto(IMAGE_URL % 6)

            def should_not_be_null(self, topic):
                expect(topic).not_to_be_null()
                expect(topic).not_to_be_an_error()

            def should_have_proper_key(self, topic):
                expect(topic).to_equal('ACME-SEC')

    class DetectorVows(Vows.Context):
        class CanStoreDetectorData(Vows.Context):
            def topic(self):
                config = Config(FILE_STORAGE_ROOT_PATH="/tmp/thumbor/file_storage/")
                storage = FileStorage(Context(config=config, server=get_server('ACME-SEC')))
                storage.put(IMAGE_URL % 7, IMAGE_BYTES)
                storage.put_detector_data(IMAGE_URL % 7, 'some-data')
                return storage.get_detector_data(IMAGE_URL % 7)

            def should_not_be_null(self, topic):
                expect(topic).not_to_be_null()
                expect(topic).not_to_be_an_error()

            def should_equal_some_data(self, topic):
                expect(topic).to_equal('some-data')

        class ReturnsNoneIfNoDetectorData(Vows.Context):
            def topic(self):
                config = Config(FILE_STORAGE_ROOT_PATH="/tmp/thumbor/file_storage/")
                storage = FileStorage(Context(config=config, server=get_server('ACME-SEC')))
                return storage.get_detector_data(IMAGE_URL % 10000)

            def should_not_be_null(self, topic):
                expect(topic).to_be_null()

########NEW FILE########
__FILENAME__ = fill_filter_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from pyvows import Vows, expect

from thumbor.filters.fill import Filter
from thumbor.context import Context, RequestParameters
from thumbor.config import Config
from thumbor.importer import Importer
import thumbor.filters

DATA = [
    # size requested, resized/cropped image size, result size, image color, detected color
    ((20, 20), (10, 10), (20, 20), '#fff', "ffffff"),
    ((20, 0), (10, 10), (20, 10), '#333', "333333"),
    ((0, 20), (10, 10), (10, 20), '#123103', "123103")
]


def get_context():
    conf = Config()
    conf.ENGINE = 'thumbor.engines.pil'
    imp = Importer(conf)
    imp.import_modules()
    imp.filters = [Filter]
    return Context(None, conf, imp)


@Vows.batch
class FillFilterVows(Vows.Context):

    class checkImageSizes():

        def topic(self):
            ctx = get_context()
            for item in DATA:
                ctx.modules.engine.image = ctx.modules.engine.gen_image(item[1], '#fff')
                req = RequestParameters(fit_in=True, width=item[0][0], height=item[0][1])
                ctx.request = req

                runner = ctx.filters_factory.create_instances(ctx, "fill(blue)")
                filter_instances = runner.filter_instances[thumbor.filters.PHASE_POST_TRANSFORM]
                filter_instances[0].run()
                yield (filter_instances[0].engine.image.size, item[2])

        def image_should_be_filled(self, topic):
            expect(topic[0]).to_equal(topic[1])

    class checkFilterWithFillTransparent():

        def topic(self):
            ctx = get_context()
            ctx.modules.engine.image = ctx.modules.engine.gen_image((10, 10), 'rgba(0,0,0,0)')
            req = RequestParameters(width=10, height=10)
            ctx.request = req

            runner = ctx.filters_factory.create_instances(ctx, "fill(ff0000, true)")
            filter_instances = runner.filter_instances[thumbor.filters.PHASE_POST_TRANSFORM]
            filter_instances[0].run()
            return ctx.modules.engine

        def image_should_be_filled(self, topic):
            expect(topic).not_to_be_an_error()
            data = topic.get_image_data()
            expect(data).to_equal('\xff\x00\x00\xff' * 100)

    class checkFilterWithoutFillTransparent():

        def topic(self):
            ctx = get_context()
            ctx.modules.engine.image = ctx.modules.engine.gen_image((10, 10), 'rgba(0,0,0,0)')
            req = RequestParameters(width=10, height=10)
            ctx.request = req

            runner = ctx.filters_factory.create_instances(ctx, "fill(ff0000, false)")
            filter_instances = runner.filter_instances[thumbor.filters.PHASE_POST_TRANSFORM]
            filter_instances[0].run()
            return ctx.modules.engine

        def image_should_be_filled(self, topic):
            expect(topic).not_to_be_an_error()
            data = topic.get_image_data()
            expect(data).to_equal('\x00\x00\x00\x00' * 100)

    class checkAutoDetectedColor():

        def topic(self):
            ctx = get_context()
            for item in DATA:
                (size_requested, size_cropped, size_results, image_color, detected_color) = item

                ctx.modules.engine.image = ctx.modules.engine.gen_image(size_cropped, image_color)
                req = RequestParameters(fit_in=True, width=size_requested[0], height=size_requested[1])
                ctx.request = req

                runner = ctx.filters_factory.create_instances(ctx, "fill(auto)")
                filter_instances = runner.filter_instances[thumbor.filters.PHASE_POST_TRANSFORM]

                yield (filter_instances[0].get_median_color(), detected_color)

        def the_median_color_should_be_detected(self, topic):
            expect(topic).not_to_be_an_error()
            expect(topic[0]).to_equal(topic[1])

########NEW FILE########
__FILENAME__ = filters_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import functools

from pyvows import Vows, expect

from thumbor.filters import BaseFilter, FiltersFactory, filter_method
import thumbor.filters

FILTER_PARAMS_DATA = [
    {
        'type': BaseFilter.Number,
        'values': [
            ('1', 1), ('10', 10), ('99', 99), ('-1', -1), ('-10', -10), ('010', 10), ('  1 ', 1), ('0', 0)
        ],
        'invalid_values': ['x', 'x10', '10x', '- 1', '']
    },
    {
        'type': BaseFilter.PositiveNumber,
        'values': [
            ('1', 1), ('10', 10), ('99', 99), (' 1 ', 1), ('010', 10), ('0', 0)
        ],
        'invalid_values': ['-1', 'x', 'x10', '10x', '']
    },
    {
        'type': BaseFilter.NegativeNumber,
        'values': [
            ('-1', -1), ('-10', -10), (' -9 ', -9), ('-0', 0)
        ],
        'invalid_values': ['x', 'x10', '10x', '- 1', '']
    },
    {
        'type': BaseFilter.DecimalNumber,
        'values': [
            ('1', 1.0), ('10', 10.0), ('99', 99.0), ('-1', -1.0), ('-10', -10.0), ('010', 10.0), ('  1 ', 1.0),
            ('1.0', 1.0), ('10.12', 10.12), ('9.9', 9.9), ('-1.1', -1.1), (' -10.2 ', -10.2), ('  1 ', 1.0),
            ('.11', 0.11), ('0.111', 0.111), ('0', 0.0)
        ],
        'invalid_values': ['x', 'x10', '10x', '- 1.1', '', '.']
    },
    {
        'type': BaseFilter.String,
        'values': [
            ('a', 'a'), ('bbbb', 'bbbb'), ('  cccc  ', 'cccc'), ('  cc:cc  ', 'cc:cc'), ('\'a,b\'', 'a,b')
        ],
        'invalid_values': ['', ',', ',,,,']
    },
    {
        'type': BaseFilter.Boolean,
        'values': [
            ('1', True), ('True', True), ('true', True), ('0', False), ('False', False), ('false', False), (' True ', True)
        ],
        'invalid_values': ['', 'x', 'TRUE', '111']
    },
    {
        'type': r'\dx\d',
        'values': [
            ('1x1', '1x1'), (' 9x9   ', '9x9')
        ],
        'invalid_values': ['a', ',', '9 x 9']
    }
]


@Vows.batch
class FilterParamsVows(Vows.Context):
    def topic(self):
        for test_data in FILTER_PARAMS_DATA:
            yield(test_data)

    class WithValidValues(Vows.Context):
        def topic(self, test_data):
            for value in test_data['values']:
                yield(test_data['type'], value[0], value[1])

        def should_correctly_parse_value(self, data):
            type, test_data, expected_data = data
            BaseFilter.compile_regex({'name': 'x', 'params': [type]})
            f = BaseFilter('x(%s)' % test_data)
            expect(f.params[0]).to_equal(expected_data)

    class WithInvalidValues(Vows.Context):
        def topic(self, test_data):
            for value in test_data['invalid_values']:
                yield(test_data['type'], value)

        def should_not_parse_invalid_value(self, data):
            type, test_data = data
            BaseFilter.compile_regex({'name': 'x', 'params': [type]})
            f = BaseFilter('x(%s)' % test_data)
            expect(f.params).to_be_null()


class MyFilter(BaseFilter):
    @filter_method(BaseFilter.Number, BaseFilter.DecimalNumber)
    def my_filter(self, value1, value2):
        return (value1, value2)


class StringFilter(BaseFilter):
    @filter_method(BaseFilter.String)
    def my_string_filter(self, value):
        return value


class EmptyFilter(BaseFilter):
    @filter_method()
    def my_empty_filter(self):
        return 'ok'


class AsyncFilter(BaseFilter):
    @filter_method(BaseFilter.String, async=True)
    def my_async_filter(self, callback, value):
        callback(value)


class InvalidFilter(BaseFilter):
    def my_invalid_filter(self, value):
        return value


class DoubleStringFilter(BaseFilter):
    @filter_method(BaseFilter.String, BaseFilter.String)
    def my_string_filter(self, value1, value2):
        return (value1, value2)


class OptionalParamFilter(BaseFilter):
    @filter_method(BaseFilter.String, BaseFilter.String)
    def my_optional_filter(self, value1, value2="not provided"):
        return (value1, value2)


class PreLoadFilter(BaseFilter):
    phase = thumbor.filters.PHASE_PRE_LOAD

    @filter_method(BaseFilter.String)
    def my_pre_load_filter(self, value):
        return value


@Vows.batch
class FilterVows(Vows.Context):

    class CreatingFilterInstances(Vows.Context):
        def topic(self):
            class Any:
                pass
            ctx = Any()
            ctx.modules = Any()
            engine = Any()
            is_multiple = lambda: False
            engine.is_multiple = is_multiple
            ctx.modules.engine = engine
            fact = FiltersFactory([MyFilter, StringFilter, OptionalParamFilter, PreLoadFilter])
            return (fact, ctx)

        class RunnerWithParameters(Vows.Context):

            def topic(self, parent_topic):
                factory, context = parent_topic
                return factory.create_instances(context, 'my_string_filter(aaaa):my_string_filter(bbb):my_pre_load_filter(ccc)')

            def should_create_two_instances(self, runner):
                post_instances = runner.filter_instances[thumbor.filters.PHASE_POST_TRANSFORM]
                pre_instances = runner.filter_instances[thumbor.filters.PHASE_PRE_LOAD]
                expect(len(post_instances)).to_equal(2)
                expect(post_instances[0].__class__).to_equal(StringFilter)
                expect(post_instances[1].__class__).to_equal(StringFilter)
                expect(len(pre_instances)).to_equal(1)
                expect(pre_instances[0].__class__).to_equal(PreLoadFilter)

            class RunningPostFilters(Vows.Context):
                @Vows.async_topic
                def topic(self, callback, runner):
                    runner.apply_filters(thumbor.filters.PHASE_POST_TRANSFORM, functools.partial(callback, runner))

                def should_run_only_post_filters(self, args):
                    runner = args.args[0]
                    post_instances = runner.filter_instances[thumbor.filters.PHASE_POST_TRANSFORM]
                    pre_instances = runner.filter_instances[thumbor.filters.PHASE_PRE_LOAD]
                    expect(len(post_instances)).to_equal(0)
                    expect(len(pre_instances)).to_equal(1)

                class RunningPreFilters(Vows.Context):
                    @Vows.async_topic
                    def topic(self, callback, args):
                        runner = args.args[0]
                        runner.apply_filters(thumbor.filters.PHASE_PRE_LOAD, functools.partial(callback, runner))

                    def should_run_only_pre_filters(self, args):
                        runner = args.args[0]
                        post_instances = runner.filter_instances[thumbor.filters.PHASE_POST_TRANSFORM]
                        pre_instances = runner.filter_instances[thumbor.filters.PHASE_PRE_LOAD]
                        expect(len(post_instances)).to_equal(0)
                        expect(len(pre_instances)).to_equal(0)

        class WithOneValidParam(Vows.Context):
            def topic(self, parent_topic):
                factory, context = parent_topic
                runner = factory.create_instances(context, 'my_filter(1, 0a):my_string_filter(aaaa)')
                return runner.filter_instances[thumbor.filters.PHASE_POST_TRANSFORM]

            def should_create_one_instance(self, instances):
                expect(len(instances)).to_equal(1)
                expect(instances[0].__class__).to_equal(StringFilter)

        class WithParameterContainingColons(Vows.Context):
            def topic(self, parent_topic):
                factory, context = parent_topic
                runner = factory.create_instances(context, 'my_string_filter(aaaa):my_string_filter(aa:aa)')
                return runner.filter_instances[thumbor.filters.PHASE_POST_TRANSFORM]

            def should_create_two_instances(self, instances):
                expect(len(instances)).to_equal(2)
                expect(instances[0].__class__).to_equal(StringFilter)
                expect(instances[1].__class__).to_equal(StringFilter)

            def should_understant_parameters(self, instances):
                expect(instances[0].params).to_equal(["aaaa"])
                expect(instances[1].params).to_equal(["aa:aa"])

        class WithValidParams(Vows.Context):
            def topic(self, parent_topic):
                factory, context = parent_topic
                runner = factory.create_instances(context, 'my_filter(1, 0):my_string_filter(aaaa)')
                return runner.filter_instances[thumbor.filters.PHASE_POST_TRANSFORM]

            def should_create_two_instances(self, instances):
                expect(len(instances)).to_equal(2)
                expect(instances[0].__class__).to_equal(MyFilter)
                expect(instances[1].__class__).to_equal(StringFilter)

            class WhenRunning(Vows.Context):
                def topic(self, instances):
                    result = []
                    for instance in instances:
                        result.append(instance.run())
                    return result

                def should_create_two_instances(self, result):
                    expect(result[0]).to_equal([(1, 0.0)])
                    expect(result[1]).to_equal(['aaaa'])

        class WithOptionalParamFilter(Vows.Context):
            def topic(self, parent_topic):
                factory, context = parent_topic
                runner = factory.create_instances(context, 'my_optional_filter(aa, bb)')
                return runner.filter_instances[thumbor.filters.PHASE_POST_TRANSFORM]

            def should_create_two_instances(self, instances):
                expect(len(instances)).to_equal(1)
                expect(instances[0].__class__).to_equal(OptionalParamFilter)

            def should_understand_parameters(self, instances):
                expect(instances[0].run()).to_equal([("aa", "bb")])

        class WithOptionalParamsInOptionalFilter(Vows.Context):
            def topic(self, parent_topic):
                factory, context = parent_topic
                runner = factory.create_instances(context, 'my_optional_filter(aa)')
                return runner.filter_instances[thumbor.filters.PHASE_POST_TRANSFORM]

            def should_create_two_instances(self, instances):
                expect(len(instances)).to_equal(1)
                expect(instances[0].__class__).to_equal(OptionalParamFilter)

            def should_understand_parameters(self, instances):
                expect(instances[0].run()).to_equal([("aa", "not provided")])

        class WithInvalidOptionalFilter(Vows.Context):
            def topic(self, parent_topic):
                factory, context = parent_topic
                runner = factory.create_instances(context, 'my_optional_filter()')
                return runner.filter_instances[thumbor.filters.PHASE_POST_TRANSFORM]

            def should_create_two_instances(self, instances):
                expect(len(instances)).to_equal(0)

        class WithPreLoadFilter(Vows.Context):
            def topic(self, parent_topic):
                factory, context = parent_topic
                runner = factory.create_instances(context, 'my_pre_load_filter(aaaa)')
                return runner.filter_instances[thumbor.filters.PHASE_PRE_LOAD]

            def should_create_two_instances(self, instances):
                expect(len(instances)).to_equal(1)
                expect(instances[0].__class__).to_equal(PreLoadFilter)

            def should_understant_parameters(self, instances):
                expect(instances[0].params).to_equal(["aaaa"])

    class WithInvalidFilter(Vows.Context):
        def topic(self):
            InvalidFilter.pre_compile()
            return InvalidFilter

        def doesnt_create_a_runnable_method(self, cls):
            expect(hasattr(cls, 'runnable_method')).to_be_false()

    class WithValidFilter(Vows.Context):
        def topic(self):
            MyFilter.pre_compile()
            return MyFilter

        def creates_a_runnable_method(self, cls):
            expect(cls.runnable_method).to_equal(MyFilter.my_filter)

        class WithValidNumber:
            def topic(self, cls):
                f = cls("my_filter(1, -1.1)")
                return f.run()

            def sets_correct_result_value(self, topic):
                expect(topic).to_equal([(1, -1.1)])

        class WithInvalidNumber:
            def topic(self, cls):
                f = cls("my_invalid_filter(x, 1)")
                return f.run()

            def throws_an_error(self, topic):
                expect(hasattr(topic, 'result')).to_be_false()

        class WhenPassedCallback:
            @Vows.async_topic
            def topic(self, callback, cls):
                f = cls("my_filter(1, -1.1)")
                f.run(callback)

            def calls_callback(self, topic):
                expect(topic.args).to_equal(())

    class DoubleStringFilter(Vows.Context):
        def topic(self):
            DoubleStringFilter.pre_compile()
            return DoubleStringFilter

        class WithTwoNormalStrings:
            def topic(self, cls):
                f = cls("my_string_filter(a, b)")
                return f.run()

            def sets_correct_values(self, topic):
                expect(topic).to_equal([('a', 'b')])

        class WithStringsWithCommas:
            def topic(self, cls):
                tests = [
                    ("my_string_filter(a,'b, c')", [('a', 'b, c')]),
                    ("my_string_filter('a,b', c)", [('a,b', 'c')]),
                    ("my_string_filter('ab', c)", [('ab', 'c')]),
                    ("my_string_filter('ab,', c)", [('ab,', 'c')]),
                    ("my_string_filter('ab,', ',c')", [('ab,', ',c')]),
                    ("my_string_filter('ab, c)", [('\'ab', 'c')]),
                    ("my_string_filter('ab, c',d)", [('ab, c', 'd')]),
                    ("my_string_filter('a,b, c)", None),
                    ("my_string_filter('a,b, c')", None),
                ]
                for (test, expected) in tests:
                    f = cls(test)
                    yield f.run(), expected

            def sets_correct_values(self, test_data):
                result, expected = test_data
                expect(result).to_equal(expected)

    class WithEmptyFilter(Vows.Context):
        def topic(self):
            EmptyFilter.pre_compile()
            f = EmptyFilter('my_empty_filter()')
            return f.run()

        def should_call_filter(self, value):
            expect(value).to_equal(['ok'])

    class WithAsyncFilter(Vows.Context):
        @Vows.async_topic
        def topic(self, callback):
            AsyncFilter.pre_compile()
            f = AsyncFilter("my_async_filter(yyy)")
            f.run(callback)

        def should_call_callback(self, topic):
            expect(topic.args[0]).to_equal('yyy')

########NEW FILE########
__FILENAME__ = detection_error_detector
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com


from thumbor.detectors import BaseDetector


class Detector(BaseDetector):
    def detect(self, callback):
        self.context.request.detection_error = True
        callback()

########NEW FILE########
__FILENAME__ = encrypted_handler_conf
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

ALLOWED_SOURCES = ['s.glbimg.com']

SECURITY_KEY = 'HandlerVows'

LOADER = 'thumbor.loaders.file_loader'
FILE_LOADER_ROOT_PATH = './vows/fixtures'

########NEW FILE########
__FILENAME__ = http_loader_options
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

ALLOWED_SOURCES = ['s.glbimg.com']

MAX_SOURCE_SIZE = 5000

REQUEST_TIMEOUT_SECONDS = 180

########NEW FILE########
__FILENAME__ = max_age_conf
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com


LOADER = 'thumbor.loaders.file_loader'
FILE_LOADER_ROOT_PATH = './vows/fixtures'
STORAGE = 'thumbor.storages.no_storage'

MAX_AGE = 2
MAX_AGE_TEMP_IMAGE = 1

########NEW FILE########
__FILENAME__ = prevent_result_storage_detector
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com


from thumbor.detectors import BaseDetector


class Detector(BaseDetector):
    def detect(self, callback):
        self.context.request.prevent_result_storage = True
        callback()

########NEW FILE########
__FILENAME__ = storage_fixture
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from os.path import join, abspath, dirname

from thumbor.context import ServerParameters, Context
from thumbor.config import Config
from thumbor.importer import Importer

SAME_IMAGE_URL = 's.glbimg.com/some_other/image_%d.jpg'
IMAGE_URL = 's.glbimg.com/some/image_%d.jpg'
IMAGE_PATH = join(abspath(dirname(__file__)), 'image.jpg')

with open(IMAGE_PATH, 'r') as img:
    IMAGE_BYTES = img.read()


def get_server(key=None):
    server_params = ServerParameters(8888, 'localhost', 'thumbor.conf', None, 'info', None)
    server_params.security_key = key
    return server_params


def get_context(server=None, config=None, importer=None):
    if not server:
        server = get_server()

    if not config:
        config = Config()

    if not importer:
        importer = Importer(config)

    ctx = Context(server=server, config=config, importer=importer)
    return ctx

########NEW FILE########
__FILENAME__ = format_filter_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from pyvows import Vows, expect

from thumbor.context import Context, RequestParameters
from thumbor.config import Config
from thumbor.importer import Importer
from thumbor.filters.format import Filter
import thumbor.filters


@Vows.batch
class FormatFilterVows(Vows.Context):
    class DisallowsInvalidContext(Vows.Context):
        def topic(self):
            conf = Config()
            imp = Importer(conf)
            imp.filters = [Filter]
            ctx = Context(None, conf, imp)
            ctx.request = RequestParameters()

            runner = ctx.filters_factory.create_instances(ctx, "format(invalid)")
            filter_instances = runner.filter_instances[thumbor.filters.PHASE_POST_TRANSFORM]

            filter_instances[0].run()

        def should_be_none(self, format):
            expect(format).to_be_null()

    class SetsProperFormat(Vows.Context):
        def topic(self):
            conf = Config()
            imp = Importer(conf)
            imp.filters = [Filter]
            ctx = Context(None, conf, imp)
            ctx.request = RequestParameters()

            runner = ctx.filters_factory.create_instances(ctx, "format(webp)")
            filter_instances = runner.filter_instances[thumbor.filters.PHASE_POST_TRANSFORM]

            filter_instances[0].run()
            return ctx.request.format

        def should_equal_10(self, format):
            expect(format).to_equal("webp")

########NEW FILE########
__FILENAME__ = handler_images_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from os.path import abspath, join, dirname, exists
from shutil import rmtree

from pyvows import Vows, expect
from tornado_pyvows.context import TornadoHTTPContext

from thumbor.app import ThumborServiceApp
from thumbor.importer import Importer
from thumbor.config import Config
from thumbor.context import Context, ServerParameters
from thumbor.engines.pil import Engine as PILEngine
from thumbor.storages.file_storage import Storage as FileStorage

storage_path = abspath(join(dirname(__file__), 'fixtures/'))

FILE_STORAGE_ROOT_PATH = '/tmp/thumbor-vows/handler_image_vows'


class BaseContext(TornadoHTTPContext):
    def __init__(self, *args, **kw):
        super(BaseContext, self).__init__(*args, **kw)


@Vows.batch
class GetImage(BaseContext):
    def get_app(self):
        cfg = Config(SECURITY_KEY='ACME-SEC')
        cfg.LOADER = "thumbor.loaders.file_loader"
        cfg.FILE_LOADER_ROOT_PATH = storage_path
        cfg.STORAGE = "thumbor.storages.file_storage"
        cfg.FILE_STORAGE_ROOT_PATH = FILE_STORAGE_ROOT_PATH
        if exists(FILE_STORAGE_ROOT_PATH):
            rmtree(FILE_STORAGE_ROOT_PATH)

        importer = Importer(cfg)
        importer.import_modules()
        server = ServerParameters(8889, 'localhost', 'thumbor.conf', None, 'info', None)
        server.security_key = 'ACME-SEC'
        ctx = Context(server, cfg, importer)
        application = ThumborServiceApp(ctx)

        return application

    class WithRegularImage(TornadoHTTPContext):
        def topic(self):
            response = self.get('/unsafe/smart/image.jpg')
            return (response.code, response.headers)

        def should_be_200(self, response):
            code, _ = response
            expect(code).to_equal(200)

    class WithSignedRegularImage(TornadoHTTPContext):
        def topic(self):
            response = self.get('/_wIUeSaeHw8dricKG2MGhqu5thk=/smart/image.jpg')
            return (response.code, response.headers)

        def should_be_200(self, response):
            code, _ = response
            expect(code).to_equal(200)

    class without_unsafe_url_image(TornadoHTTPContext):
        def topic(self):
            response = self.get('/alabama1_ap620%C3%A9.jpg')
            return (response.code, response.headers)

        def should_be_404(self, response):
            code, _ = response
            expect(code).to_equal(404)

    class without_image(TornadoHTTPContext):
        def topic(self):
            response = self.get('/unsafe/')
            return (response.code, response.headers)

        def should_be_404(self, response):
            code, _ = response
            expect(code).to_equal(404)

    class with_UTF8_URLEncoded_image_name_using_encoded_url(TornadoHTTPContext):
        def topic(self):
            url = '/lc6e3kkm_2Ww7NWho8HPOe-sqLU=/smart/alabama1_ap620%C3%A9.jpg'
            response = self.get(url)
            return (response.code, response.headers)

        def should_be_200(self, response):
            code, _ = response
            expect(code).to_equal(200)

    class with_UTF8_URLEncoded_image_name_using_unsafe(TornadoHTTPContext):
        def topic(self):
            response = self.get(u'/unsafe/smart/alabama1_ap620%C3%A9.jpg')
            return (response.code, response.headers)

        def should_be_200(self, response):
            code, _ = response
            expect(code).to_equal(200)

    class with_spaces_on_url(TornadoHTTPContext):
        def topic(self):
            response = self.get(u'/unsafe/image%20space.jpg')
            return (response.code, response.headers)

        def should_be_200(self, response):
            code, _ = response
            expect(code).to_equal(200)

    class with_filter(TornadoHTTPContext):
        def topic(self):
            response = self.get('/5YRxzS2yxZxj9SZ50SoZ11eIdDI=/filters:fill(blue)/image.jpg')
            return (response.code, response.headers)

        def should_be_200(self, response):
            code, _ = response
            expect(code).to_equal(200)

    class WithInvalidQuantizationTableJPEG(BaseContext):
        def topic(self):
            response = self.get('/unsafe/invalid_quantization.jpg')
            return (response.code, response.headers)

        def should_be_200(self, response):
            code, _ = response
            expect(code).to_equal(200)



@Vows.batch
class GetImageWithoutUnsafe(BaseContext):
    def get_app(self):
        cfg = Config(SECURITY_KEY='ACME-SEC')
        cfg.LOADER = "thumbor.loaders.file_loader"
        cfg.FILE_LOADER_ROOT_PATH = storage_path
        cfg.ALLOW_UNSAFE_URL = False

        importer = Importer(cfg)
        importer.import_modules()
        server = ServerParameters(8890, 'localhost', 'thumbor.conf', None, 'info', None)
        server.security_key = 'ACME-SEC'
        ctx = Context(server, cfg, importer)
        application = ThumborServiceApp(ctx)

        return application

    class WithSignedRegularImage(TornadoHTTPContext):
        def topic(self):
            response = self.get('/_wIUeSaeHw8dricKG2MGhqu5thk=/smart/image.jpg')
            return (response.code, response.headers)

        def should_be_200(self, response):
            code, _ = response
            expect(code).to_equal(200)

    class WithRegularImage(TornadoHTTPContext):
        def topic(self):
            response = self.get('/unsafe/smart/image.jpg')
            return (response.code, response.headers)

        def should_be_404(self, response):
            code, _ = response
            expect(code).to_equal(404)


@Vows.batch
class GetImageWithOLDFormat(BaseContext):
    def get_app(self):
        cfg = Config(SECURITY_KEY='ACME-SEC')
        cfg.LOADER = "thumbor.loaders.file_loader"
        cfg.FILE_LOADER_ROOT_PATH = storage_path
        cfg.ALLOW_UNSAFE_URL = False
        cfg.ALLOW_OLD_URLS = True

        importer = Importer(cfg)
        importer.import_modules()
        server = ServerParameters(8890, 'localhost', 'thumbor.conf', None, 'info', None)
        server.security_key = 'ACME-SEC'
        ctx = Context(server, cfg, importer)
        application = ThumborServiceApp(ctx)

        return application

    class WithEncryptedRegularImage(TornadoHTTPContext):
        def topic(self):
            response = self.get('/J4ZFjCICZSwwIKfEKNldBNjcG145LDiD2z-4RlOa5ZG4ZY_-8KoEyDOBDfqDBljH/image.jpg')
            return (response.code, response.headers)

        def should_be_200(self, response):
            code, _ = response
            expect(code).to_equal(200)

    class WithBadEncryptedRegularImage(TornadoHTTPContext):
        def topic(self):
            response = self.get('/27m-vYMKohY6nvEt_D3Zwo7apVq63MS8TP-m1j3BXPGTftnrReTOEoScq1xMXe7h/alabama1_ap620é.jpg')
            return (response.code, response.headers)

        def should_be_404(self, response):
            code, _ = response
            expect(code).to_equal(404)


@Vows.batch
class GetImageWithStoredKeys(BaseContext):
    def get_app(self):
        cfg = Config(SECURITY_KEY='MYKEY')
        cfg.LOADER = "thumbor.loaders.file_loader"
        cfg.FILE_LOADER_ROOT_PATH = storage_path
        cfg.ALLOW_UNSAFE_URL = False
        cfg.ALLOW_OLD_URLS = True
        cfg.STORES_CRYPTO_KEY_FOR_EACH_IMAGE = True

        importer = Importer(cfg)
        importer.import_modules()
        server = ServerParameters(8891, 'localhost', 'thumbor.conf', None, 'info', None)
        server.security_key = 'MYKEY'
        ctx = Context(server, cfg, importer)
        application = ThumborServiceApp(ctx)

        storage = FileStorage(Context(config=cfg, server=server))

        # Store fixtures (image.jpg and image.txt) into the file storage
        storage.put('image.jpg', open(join(storage_path, 'image.jpg')).read())
        storage.put_crypto('image.jpg')   # Write a file on the file storage containing the security key

        return application

    class WithEncryptedRegularImage(TornadoHTTPContext):
        def topic(self):
            response = self.get('/nty7gpBIRJ3GWtYDLLw6q1PgqTo=/smart/image.jpg')
            return (response.code, response.headers)

        def should_be_200(self, response):
            code, _ = response
            expect(code).to_equal(200)


@Vows.batch
class GetImageWithAutoWebP(BaseContext):
    def get_app(self):
        cfg = Config(SECURITY_KEY='ACME-SEC')
        cfg.LOADER = "thumbor.loaders.file_loader"
        cfg.FILE_LOADER_ROOT_PATH = storage_path
        cfg.AUTO_WEBP = True

        importer = Importer(cfg)
        importer.import_modules()
        server = ServerParameters(8889, 'localhost', 'thumbor.conf', None, 'info', None)
        server.security_key = 'ACME-SEC'
        ctx = Context(server, cfg, importer)
        application = ThumborServiceApp(ctx)

        self.engine = PILEngine(ctx)

        return application

    class CanConvertJPEG(BaseContext):
        def topic(self):
            return self.get('/unsafe/image.jpg', headers={
                "Accept": 'image/webp,*/*;q=0.8'
            })

        def should_be_webp(self, response):
            expect(response.code).to_equal(200)
            expect(response.headers).to_include('Vary')
            expect(response.headers['Vary']).to_include('Accept')

            image = self.engine.create_image(response.body)
            expect(image.format.lower()).to_equal('webp')

    class ShouldNotConvertWebPImage(BaseContext):
        def topic(self):
            return self.get('/unsafe/image.webp', headers={
                "Accept": 'image/webp,*/*;q=0.8'
            })

        def should_not_have_vary(self, response):
            expect(response.code).to_equal(200)
            expect(response.headers).not_to_include('Vary')
            image = self.engine.create_image(response.body)
            expect(image.format.lower()).to_equal('webp')

    class ShouldNotConvertAnimatedGif(BaseContext):
        def topic(self):
            return self.get('/unsafe/animated_image.gif', headers={
                "Accept": 'image/webp,*/*;q=0.8'
            })

        def should_not_be_webp(self, response):
            expect(response.code).to_equal(200)
            expect(response.headers).not_to_include('Vary')

            image = self.engine.create_image(response.body)
            expect(image.format.lower()).to_equal('gif')

    class WithImageWithSmallWidthAndNoHeight(BaseContext):
        def topic(self):
            response = self.get('/unsafe/0x0:1681x596/1x/hidrocarbonetos_9.jpg')
            return (response.code, response.headers)

        def should_be_200(self, response):
            code, _ = response
            expect(code).to_equal(200)

    class WithMonochromaticJPEG(BaseContext):
        def topic(self):
            response = self.get('/unsafe/wellsford.jpg')
            return (response.code, response.headers)

        def should_be_200(self, response):
            code, _ = response
            expect(code).to_equal(200)

    class WithCMYK_JPEG(BaseContext):
        def topic(self):
            response = self.get('/unsafe/merrit.jpg')
            return (response.code, response.headers)

        def should_be_200(self, response):
            code, _ = response
            expect(code).to_equal(200)

    class WithCMYK_JPEG_AsPNG(BaseContext):
        def topic(self):
            response = self.get('/unsafe/filters:format(png)/merrit.jpg')
            return (response.code, response.headers)

        def should_be_200(self, response):
            code, _ = response
            expect(code).to_equal(200)

    class WithCMYK_JPEG_AsPNG_AcceptingWEBP(BaseContext):
        def topic(self):
            response = self.get('/unsafe/filters:format(png)/merrit.jpg', headers={
                "Accept": 'image/webp,*/*;q=0.8'
            })
            return response

        def should_be_200(self, response):
            expect(response.code).to_equal(200)
            image = self.engine.create_image(response.body)
            expect(image.format.lower()).to_equal('png')

    class WithJPEG_AsGIF_AcceptingWEBP(BaseContext):
        def topic(self):
            response = self.get('/unsafe/filters:format(gif)/image.jpg', headers={
                "Accept": 'image/webp,*/*;q=0.8'
            })
            return response

        def should_be_200(self, response):
            expect(response.code).to_equal(200)
            image = self.engine.create_image(response.body)
            expect(image.format.lower()).to_equal('gif')

########NEW FILE########
__FILENAME__ = healthcheck_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from pyvows import Vows, expect
from tornado_pyvows.context import TornadoHTTPContext

from thumbor.app import ThumborServiceApp
from thumbor.config import Config
from thumbor.context import Context


@Vows.batch
class HealthCheck(TornadoHTTPContext):
    def get_app(self):
        cfg = Config()
        ctx = Context(None, cfg, None)
        application = ThumborServiceApp(ctx)
        return application

    class WhenRunning(TornadoHTTPContext):
        def topic(self):
            response = self.get('/healthcheck')
            return (response.code, response.body)

        class StatusCode(TornadoHTTPContext):
            def topic(self, response):
                return response[0]

            def should_not_be_an_error(self, topic):
                expect(topic).to_equal(200)

        class Body(TornadoHTTPContext):
            def topic(self, response):
                return response[1]

            def should_equal_working(self, topic):
                expect(topic.lower().strip()).to_equal('working')

    class HeadHandler(TornadoHTTPContext):
        def topic(self):
            response = self.head('/healthcheck')
            return (response.code, response.body)

        class StatusCode(TornadoHTTPContext):
            def topic(self, response):
                return response[0]

            def should_not_be_an_error(self, topic):
                expect(topic).to_equal(200)


########NEW FILE########
__FILENAME__ = http_loader_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from os.path import abspath, join, dirname

from pyvows import Vows, expect
from tornado_pyvows.context import TornadoHTTPContext
import tornado.web

import thumbor.loaders.http_loader as loader
from thumbor.context import Context
from thumbor.config import Config

fixture_for = lambda filename: abspath(join(dirname(__file__), 'fixtures', filename))


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('Hello')


class EchoUserAgentHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(self.request.headers['User-Agent'])


class HandlerMock(object):
    def __init__(self, headers):
        self.request = RequestMock(headers)


class RequestMock(object):
    def __init__(self, headers):
        self.headers = headers


class ResponseMock:
    def __init__(self, error=None, content_type=None, body=None):
        self.error = error

        self.headers = {
            'Content-Type': 'image/jpeg'
        }

        if content_type:
            self.headers['Content-Type'] = content_type

        self.body = body


@Vows.batch
class ReturnContentVows(Vows.Context):
    class ShouldReturnNoneOnError(Vows.Context):
        @Vows.async_topic
        def topic(self, callback):
            mock = ResponseMock(error='Error')
            return loader.return_contents(mock, 'some-url', callback)

        def should_be_none(self, topic):
            expect(topic.args[0]).to_be_null()

    class ShouldReturnBodyIfValid(Vows.Context):
        @Vows.async_topic
        def topic(self, callback):
            mock = ResponseMock(body='body')
            return loader.return_contents(mock, 'some-url', callback)

        def should_be_none(self, topic):
            expect(topic.args[0]).to_equal('body')


@Vows.batch
class HttpLoader(TornadoHTTPContext):
    def get_app(self):
        application = tornado.web.Application([
            (r"/", MainHandler),
        ])

        return application

    class ValidateURL(TornadoHTTPContext):
        def topic(self):
            config = Config()
            config.ALLOWED_SOURCES = ['s.glbimg.com']
            ctx = Context(None, config, None)
            is_valid = loader.validate(ctx, 'http://www.google.com/logo.jpg')
            return is_valid

        def should_default_to_none(self, topic):
            expect(topic).to_be_false()

        class AllowAll(TornadoHTTPContext):
            def topic(self):
                config = Config()
                config.ALLOWED_SOURCES = []
                ctx = Context(None, config, None)
                is_valid = loader.validate(ctx, 'http://www.google.com/logo.jpg')
                return is_valid

            def should_validate(self, topic):
                expect(topic).to_be_true()

        class ValidDomainValidates(TornadoHTTPContext):
            def topic(self):
                config = Config()
                config.ALLOWED_SOURCES = ['s.glbimg.com']
                ctx = Context(None, config, None)
                is_valid = loader.validate(ctx, 'http://s.glbimg.com/logo.jpg')
                return is_valid

            def should_validate(self, topic):
                expect(topic).to_be_true()

        class UnallowedDomainDoesNotValidate(TornadoHTTPContext):
            def topic(self):
                config = Config()
                config.ALLOWED_SOURCES = ['s.glbimg.com']
                ctx = Context(None, config, None)
                is_valid = loader.validate(ctx, 'http://s2.glbimg.com/logo.jpg')
                return is_valid

            def should_validate(self, topic):
                expect(topic).to_be_false()

        class InvalidDomainDoesNotValidate(TornadoHTTPContext):
            def topic(self):
                config = Config()
                config.ALLOWED_SOURCES = ['s2.glbimg.com']
                ctx = Context(None, config, None)
                is_valid = loader.validate(ctx, '/glob=:sfoir%20%20%3Co-pmb%20%20%20%20_%20%20%20%200%20%20g.-%3E%3Ca%20hplass=')
                return is_valid

            def should_validate(self, topic):
                expect(topic).to_be_false()

    class NormalizeURL(TornadoHTTPContext):
        class WhenStartsWithHttp(TornadoHTTPContext):
            def topic(self):
                return loader._normalize_url('http://some.url')

            def should_return_same_url(self, topic):
                expect(topic).to_equal('http://some.url')

        class WhenDoesNotStartWithHttp(TornadoHTTPContext):
            def topic(self):
                return loader._normalize_url('some.url')

            def should_return_normalized_url(self, topic):
                expect(topic).to_equal('http://some.url')

    class LoadAndVerifyImage(TornadoHTTPContext):
        class Load(TornadoHTTPContext):
            @Vows.async_topic
            def topic(self, callback):
                url = self.get_url('/')
                loader.http_client = self._http_client

                config = Config()
                config.ALLOWED_SOURCES = ['s.glbimg.com']
                ctx = Context(None, config, None)

                loader.load(ctx, url, callback)

            def should_equal_hello(self, topic):
                expect(topic.args[0]).to_equal('Hello')


@Vows.batch
class HttpLoaderWithUserAgentForwarding(TornadoHTTPContext):
    def get_app(self):
        application = tornado.web.Application([
            (r"/", EchoUserAgentHandler),
        ])

        return application

    class Load(TornadoHTTPContext):
        @Vows.async_topic
        def topic(self, callback):
            url = self.get_url('/')
            loader.http_client = self._http_client

            config = Config()
            config.HTTP_LOADER_FORWARD_USER_AGENT = True
            ctx = Context(None, config, None, HandlerMock({"User-Agent": "test-user-agent"}))

            loader.load(ctx, url, callback)

        def should_equal_hello(self, topic):
            expect(topic.args[0]).to_equal('test-user-agent')

    class LoadDefaultUserAgent(TornadoHTTPContext):
        @Vows.async_topic
        def topic(self, callback):
            url = self.get_url('/')
            loader.http_client = self._http_client

            config = Config()
            config.HTTP_LOADER_FORWARD_USER_AGENT = True
            config.HTTP_LOADER_DEFAULT_USER_AGENT = "DEFAULT_USER_AGENT"
            ctx = Context(None, config, None, HandlerMock({}))

            loader.load(ctx, url, callback)

        def should_equal_hello(self, topic):
            expect(topic.args[0]).to_equal('DEFAULT_USER_AGENT')

########NEW FILE########
__FILENAME__ = importer_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from pyvows import Vows, expect

from thumbor.importer import Importer
from thumbor.config import Config
from thumbor.engines.pil import Engine as pil_engine
from thumbor.loaders import http_loader
from thumbor.storages.file_storage import Storage as file_storage
from thumbor.result_storages.file_storage import Storage as result_file_storage
from thumbor.detectors.face_detector import Detector as face_detector
from thumbor.detectors import feature_detector
from thumbor.filters.rgb import Filter as rgb_filter


test_data = [
    ('ENGINE', pil_engine),
    ('LOADER', http_loader),
    ('STORAGE', file_storage),
    ('UPLOAD_PHOTO_STORAGE', file_storage),
    ('RESULT_STORAGE', result_file_storage),
    ('DETECTORS', (face_detector,)),
    ('FILTERS', (rgb_filter,)),
]


@Vows.batch
class ImporterVows(Vows.Context):

    class AllConfigurationVows(Vows.Context):
        def topic(self):
            for data in test_data:
                complete_config = Config(
                    ENGINE=r'thumbor.engines.pil',
                    LOADER=r'thumbor.loaders.http_loader',
                    STORAGE=r'thumbor.storages.file_storage',
                    UPLOAD_PHOTO_STORAGE=r'thumbor.storages.file_storage',
                    RESULT_STORAGE=r'thumbor.result_storages.file_storage',
                    DETECTORS=['thumbor.detectors.face_detector'],
                    FILTERS=['thumbor.filters.rgb']
                )

                yield data, complete_config

        class CanImportItem(Vows.Context):
            def topic(self, test_item):
                test_data, config = test_item
                importer = Importer(config)
                importer.import_modules()

                if hasattr(importer, test_data[0].lower()):
                    return (getattr(importer, test_data[0].lower()), test_data[1])
                return (None, None)

            def should_be_proper_item(self, topic):
                if topic[0] is tuple:
                    for index, item in enumerate(topic[0]):
                        expect(item).not_to_be_null()
                        expect(item).to_equal(topic[1][index])
                else:
                    expect(topic[0]).not_to_be_null()
                    expect(topic[0]).to_equal(topic[1])

    class ImportWithFixedValueVows(Vows.Context):

        class SingleItem(Vows.Context):
            def topic(self):
                importer = Importer(None)
                importer.import_item(config_key='file_storage', item_value='thumbor.storages.file_storage', class_name='Storage')
                return importer.file_storage

            def should_equal_file_storage(self, topic):
                expect(topic).to_equal(file_storage)

        class MultipleItems(Vows.Context):
            def topic(self):
                importer = Importer(None)
                importer.import_item(
                    config_key='detectors', is_multiple=True,
                    item_value=(
                        'thumbor.detectors.feature_detector',
                        'thumbor.detectors.feature_detector'
                    )
                )
                return importer.detectors

            def should_have_length_of_2(self, topic):
                expect(topic).to_length(2)

            def should_contain_both_detectors(self, topic):
                expect(topic).to_include(feature_detector)

########NEW FILE########
__FILENAME__ = json_engine_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import re
from json import loads

from pyvows import Vows, expect
ctx = Vows.Context

from thumbor.engines.json_engine import JSONEngine
from thumbor.point import FocalPoint


class MockImage:
    def __init__(self, size, data=None):
        self.size = size
        self.data = data


class MockEngine:
    def __init__(self, size):
        self.context = None
        self.image = MockImage(size)

    def get_image_mode(self):
        return 'RGB'

    def get_image_data(self):
        return self.image.data

    def set_image_data(self, data):
        self.image.data = data

    def resize(self, width, height):
        self.image.size = (width, height)

    def crop(self, left, top, right, bottom):
        self.image.size = (right - left, bottom - top)

    def image_data_as_rgb(self, update_image=True):
        return 'RGB', self.image.data

    @property
    def size(self):
        return self.image.size


IMAGE_PATH = '/some/image/path.jpg'
IMAGE_SIZE = (300, 200)


@Vows.batch
class JsonEngineVows(ctx):

    class CreateInstanceVows(ctx):
        def topic(self):
            engine = MockEngine(size=IMAGE_SIZE)
            json = JSONEngine(engine=engine, path=IMAGE_PATH)

            return json

        def should_not_be_null_or_error(self, topic):
            expect(topic).not_to_be_null()
            expect(topic).not_to_be_an_error()

        def should_have_proper_engine(self, topic):
            expect(topic.engine).to_be_instance_of(MockEngine)

        def should_have_proper_dimensions(self, topic):
            expect(topic.width).to_equal(300)
            expect(topic.height).to_equal(200)

        def should_have_proper_path(self, topic):
            expect(topic.path).to_equal(IMAGE_PATH)

        def should_have_null_callback_name(self, topic):
            expect(topic.callback_name).to_be_null()

        def should_have_empty_operations(self, topic):
            expect(topic.operations).to_be_empty()

        def should_have_empty_focal_points(self, topic):
            expect(topic.focal_points).to_be_empty()

        def should_have_proper_image(self, topic):
            expect(topic.image).to_be_instance_of(MockImage)

        def should_return_size(self, topic):
            expect(topic.size).to_equal((300, 200))

        class GetImageMode(ctx):
            def topic(self, engine):
                return engine.get_image_mode()

            def should_return_proper_image_mode(self, topic):
                expect(topic).to_equal('RGB')

        class GetImageDataAsRgb(ctx):
            def topic(self, engine):
                engine.set_image_data('SOME DATA')
                return engine.image_data_as_rgb()

            def should_return_proper_image_data(self, (mode, data)):
                expect(mode).to_equal('RGB')
                expect(data).to_equal('SOME DATA')

        class GetImageData(ctx):
            def topic(self, engine):
                engine.set_image_data('SOME DATA')
                return engine.get_image_data()

            def should_return_proper_image_data(self, topic):
                expect(topic).to_equal('SOME DATA')

        class Read(ctx):
            def topic(self, engine):
                return loads(engine.read('jpg', 100))

            def should_be_proper_json(self, topic):
                expected = {
                    "thumbor": {
                        "operations": [],
                        "source": {
                            "url": "/some/image/path.jpg",
                            "width": 300,
                            "height": 200
                        },
                        "target": {
                            "width": 300,
                            "height": 200
                        }
                    }
                }
                expect(topic).to_be_like(expected)

    class ReadWithCallbackName(ctx):
        def topic(self):
            engine = MockEngine(size=IMAGE_SIZE)
            json = JSONEngine(engine=engine, path=IMAGE_PATH, callback_name="callback")

            jsonp = json.read('jpg', 100)
            match = re.match('^callback\((.+)\);', jsonp)
            return match

        def should_not_be_null(self, topic):
            expect(topic).not_to_be_null()

        class JsonCompare(ctx):
            def topic(self, match):
                json = match.groups()[0]
                return loads(json)

            def should_be_proper_json(self, topic):
                expected = {
                    "thumbor": {
                        "operations": [],
                        "source": {
                            "url": "/some/image/path.jpg",
                            "width": 300,
                            "height": 200
                        },
                        "target": {
                            "width": 300,
                            "height": 200
                        }
                    }
                }
                expect(topic).to_be_like(expected)

    class ResizeVows(ctx):
        def topic(self):
            engine = MockEngine(size=IMAGE_SIZE)
            json = JSONEngine(engine=engine, path=IMAGE_PATH)

            json.resize(200, 300)

            return loads(json.read('jpg', 100))

        def should_be_proper_json(self, topic):
            expected = {
                "thumbor": {
                    "operations": [
                        {u'width': 200, u'type': u'resize', u'height': 300}
                    ],
                    "source": {
                        "url": "/some/image/path.jpg",
                        "width": 300,
                        "height": 200
                    },
                    "target": {
                        "width": 200,
                        "height": 300
                    }
                }
            }
            expect(topic).to_be_like(expected)

    class CropVows(ctx):
        def topic(self):
            engine = MockEngine(size=IMAGE_SIZE)
            json = JSONEngine(engine=engine, path=IMAGE_PATH)

            json.crop(100, 100, 200, 150)

            return loads(json.read('jpg', 100))

        def should_be_proper_json(self, topic):
            expected = {
                "thumbor": {
                    "operations": [
                        {u'top': 100, u'right': 200, u'type': u'crop', u'left': 100, u'bottom': 150}
                    ],
                    "source": {
                        "url": "/some/image/path.jpg",
                        "width": 300,
                        "height": 200
                    },
                    "target": {
                        "width": 100,
                        "height": 50
                    }
                }
            }
            expect(topic).to_be_like(expected)

    class FlipVows(ctx):
        def topic(self):
            engine = MockEngine(size=IMAGE_SIZE)
            json = JSONEngine(engine=engine, path=IMAGE_PATH)

            json.flip_vertically()
            json.flip_horizontally()

            return loads(json.read('jpg', 100))

        def should_be_proper_json(self, topic):
            expected = {
                "thumbor": {
                    "operations": [
                        {u'type': u'flip_vertically'},
                        {u'type': u'flip_horizontally'}
                    ],
                    "source": {
                        "url": "/some/image/path.jpg",
                        "width": 300,
                        "height": 200
                    },
                    "target": {
                        "width": 300,
                        "height": 200
                    }
                }
            }
            expect(topic).to_be_like(expected)

    class FocalVows(ctx):
        def topic(self):
            engine = MockEngine(size=IMAGE_SIZE)
            json = JSONEngine(engine=engine, path=IMAGE_PATH)

            json.focus([
                FocalPoint(100, 100),
                FocalPoint(200, 200)
            ])

            return loads(json.read('jpg', 100))

        def should_be_proper_json(self, topic):
            expected = {
                "thumbor": {
                    "operations": [
                    ],
                    "focal_points": [
                        {u'origin': u'alignment', u'height': 1, u'width': 1, u'y': 100, u'x': 100, u'z': 1.0},
                        {u'origin': u'alignment', u'height': 1, u'width': 1, u'y': 200, u'x': 200, u'z': 1.0}
                    ],
                    "source": {
                        "url": "/some/image/path.jpg",
                        "width": 300,
                        "height": 200
                    },
                    "target": {
                        "width": 300,
                        "height": 200
                    }
                }
            }
            expect(topic).to_be_like(expected)
########NEW FILE########
__FILENAME__ = max_age_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com
from os.path import abspath, join, dirname

from pyvows import Vows, expect
from tornado_pyvows.context import TornadoHTTPContext

from thumbor.app import ThumborServiceApp
from thumbor.importer import Importer
from thumbor.config import Config
from thumbor.context import Context, ServerParameters


fixture_for = lambda path: abspath(join(dirname(__file__), 'fixtures', path))


def get_url():
    return '/unsafe/smart/alabama1_ap620.jpg'


def get_app(prevent_result_storage=False, detection_error=False):
    cfg = Config.load(fixture_for('max_age_conf.py'))
    server_params = ServerParameters(None, None, None, None, None, None)

    cfg.DETECTORS = []
    if prevent_result_storage:
        cfg.DETECTORS.append('fixtures.prevent_result_storage_detector')
    if detection_error:
        cfg.DETECTORS.append('fixtures.detection_error_detector')

    importer = Importer(cfg)
    importer.import_modules()
    ctx = Context(server_params, cfg, importer)
    application = ThumborServiceApp(ctx)

    return application


# commented til we fix tornado-pyvows issue
#@Vows.batch
class MaxAgeVows(Vows.Context):

    class WithRegularImage(TornadoHTTPContext):
        def get_app(self):
            return get_app()

        def topic(self):
            response = self.get(get_url())
            return (response.code, response.headers)

        def should_be_200(self, response):
            code, _ = response
            expect(code).to_equal(200)

        def should_set_cache_control(self, response):
            _, headers = response
            expect(headers['Cache-Control']).to_equal('max-age=2,public')

        def should_set_expires(self, response):
            _, headers = response
            expect(headers).to_include('Expires')

    class WithNonStoragedImage(TornadoHTTPContext):
        def get_app(self):
            return get_app(prevent_result_storage=True)

        def topic(self):
            response = self.get(get_url())
            return (response.code, response.headers)

        def should_be_200(self, response):
            code, _ = response
            expect(code).to_equal(200)

        def should_set_cache_control(self, response):
            _, headers = response
            expect(headers['Cache-Control']).to_equal('max-age=1,public')

        def should_set_expires(self, response):
            _, headers = response
            expect(headers).to_include('Expires')

    class WithDetectionErrorImage(TornadoHTTPContext):
        def get_app(self):
            return get_app(detection_error=True)

        def topic(self):
            response = self.get(get_url())
            return (response.code, response.headers)

        def should_be_200(self, response):
            code, _ = response
            expect(code).to_equal(200)

        def should_set_cache_control(self, response):
            _, headers = response
            expect(headers['Cache-Control']).to_equal('max-age=1,public')

        def should_set_expires(self, response):
            _, headers = response
            expect(headers).to_include('Expires')

########NEW FILE########
__FILENAME__ = max_bytes_filter_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from os.path import abspath, join, dirname

from pyvows import Vows, expect
from tornado_pyvows.context import TornadoHTTPContext

from thumbor.app import ThumborServiceApp
#from thumbor.filters.max_bytes import Filter
from thumbor.context import Context, ServerParameters
from thumbor.config import Config
from thumbor.importer import Importer

storage_path = abspath(join(dirname(__file__), 'fixtures/'))


@Vows.batch
class MaxBytesFilterVows(TornadoHTTPContext):

    def get_app(self):
        cfg = Config(SECURITY_KEY='ACME-SEC')
        cfg.LOADER = "thumbor.loaders.file_loader"
        cfg.FILE_LOADER_ROOT_PATH = storage_path

        importer = Importer(cfg)
        importer.import_modules()
        server = ServerParameters(8889, 'localhost', 'thumbor.conf', None, 'info', None)
        server.security_key = 'ACME-SEC'
        ctx = Context(server, cfg, importer)
        application = ThumborServiceApp(ctx)

        return application

    class WithRegularImage(TornadoHTTPContext):
        def topic(self):
            response = self.get('/unsafe/filters:max_bytes(10000)/conselheira_tutelar.jpg')
            return (response.code, response.body)

        def should_be_200(self, response):
            code, image = response
            expect(code).to_equal(200)
            expect(len(image)).to_be_lesser_or_equal_to(10000)

########NEW FILE########
__FILENAME__ = meta_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from os.path import abspath, join, dirname

from pyvows import Vows, expect
from tornado_pyvows.context import TornadoHTTPContext

from thumbor.app import ThumborServiceApp
from thumbor.importer import Importer
from thumbor.config import Config
from thumbor.context import Context, ServerParameters

storage_path = abspath(join(dirname(__file__), 'fixtures/'))


class BaseContext(TornadoHTTPContext):
    def __init__(self, *args, **kw):
        super(BaseContext, self).__init__(*args, **kw)


@Vows.batch
class GetMeta(BaseContext):
    def get_app(self):
        cfg = Config(
            SECURITY_KEY='ACME-SEC',
            LOADER='thumbor.loaders.file_loader',
            RESULT_STORAGE='thumbor.result_storages.file_storage',
            RESULT_STORAGE_STORES_UNSAFE=True,
            RESULT_STORAGE_EXPIRATION_SECONDS=2592000,
            FILE_LOADER_ROOT_PATH=storage_path
        )

        importer = Importer(cfg)
        importer.import_modules()
        server = ServerParameters(8889, 'localhost', 'thumbor.conf', None, 'info', None)
        server.security_key = 'ACME-SEC'
        ctx = Context(server, cfg, importer)
        application = ThumborServiceApp(ctx)

        return application

    class WithMetadata(TornadoHTTPContext):
        def topic(self):
            response = self.get('/unsafe/meta/800x400/image.jpg')
            return (response.code, response.headers)

        def should_be_200(self, response):
            code, _ = response
            expect(code).to_equal(200)

        class FromCacheWithMetadata(TornadoHTTPContext):
            def topic(self):
                response = self.get('/unsafe/meta/800x400/image.jpg')
                return (response.code, response.headers)

            def should_be_200(self, response):
                code, _ = response
                expect(code).to_equal(200)

########NEW FILE########
__FILENAME__ = mixed_storage_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from collections import defaultdict

from pyvows import Vows, expect

from thumbor.storages.no_storage import Storage as NoStorage
from thumbor.storages.mixed_storage import Storage as MixedStorage
from fixtures.storage_fixture import get_context


class Storage(object):
    def __init__(self, security_key):
        self.storage = defaultdict(dict)
        self.security_key = security_key

    def put(self, path, contents):
        self.storage[path]['path'] = path
        self.storage[path]['contents'] = contents

    def put_crypto(self, path):
        self.storage[path]['crypto'] = self.security_key

    def put_detector_data(self, path, data):
        self.storage[path]['detector'] = data

    def get_crypto(self, path):
        if path not in self.storage:
            raise RuntimeError('%s was not found in storage' % path)

        return self.storage[path]['crypto']

    def get_detector_data(self, path):
        if path not in self.storage or 'detector' not in self.storage[path]:
            return None

        return self.storage[path]['detector']

    def get(self, path):
        if path not in self.storage:
            raise RuntimeError('%s was not found in storage' % path)

        return self.storage[path]['contents']


@Vows.batch
class MixedStorageVows(Vows.Context):
    def topic(self):
        return (Storage('security-key'), Storage('security-key'), Storage('detector'))

    class Put(Vows.Context):
        def topic(self, storages):
            file_storage, crypto_storage, detector_storage = storages
            storage = MixedStorage(None, file_storage, crypto_storage, detector_storage)

            storage.put('path1', 'contents')
            storage.put_crypto('path1')
            storage.put_detector_data('path1', 'detector')

            return storage

        class IncludesPath(Vows.Context):
            def should_record_path(self, topic):
                file_storage, crypto_storage = topic.file_storage, topic.crypto_storage
                expect(file_storage.storage['path1']['path']).to_equal('path1')

            def should_record_contents_on_file_storage(self, topic):
                file_storage, crypto_storage = topic.file_storage, topic.crypto_storage
                expect(file_storage.storage['path1']['contents']).to_equal('contents')

            def should_get_contents(self, topic):
                contents = topic.get('path1')
                expect(contents).to_equal('contents')

            def should_not_record_crypto_on_file_storage(self, topic):
                file_storage, crypto_storage = topic.file_storage, topic.crypto_storage
                expect(file_storage.storage['path1']).not_to_include('crypto')

            def should_not_record_contents_on_crypto_storage(self, topic):
                file_storage, crypto_storage = topic.file_storage, topic.crypto_storage
                expect(crypto_storage.storage['path1']).not_to_include('contents')

            def should_record_crypto_on_crypto_storage(self, topic):
                file_storage, crypto_storage = topic.file_storage, topic.crypto_storage
                expect(crypto_storage.storage['path1']['crypto']).to_equal('security-key')

            def should_get_crypto(self, topic):
                contents = topic.get_crypto('path1')
                expect(contents).to_equal('security-key')

            def should_get_detector_data(self, topic):
                contents = topic.get_detector_data('path1')
                expect(contents).to_equal('detector')

    class GetFromConfig(Vows.Context):
        def topic(self, storages):
            context = get_context()
            file_storage, crypto_storage, detector_storage = storages
            storage = MixedStorage(context)

            return storage

        class GetData(Vows.Context):
            def topic(self, storage):
                return (storage, storage.get('path'))

            def should_have_proper_file_storage(self, topic):
                expect(topic[0].file_storage).to_be_instance_of(NoStorage)

            def should_be_null(self, topic):
                expect(topic[1]).to_be_null()

        class GetDetectorData(Vows.Context):
            def topic(self, storage):
                return (storage, storage.get_detector_data('path'))

            def should_have_proper_detector_storage(self, topic):
                expect(topic[0].detector_storage).to_be_instance_of(NoStorage)

            def should_be_null(self, topic):
                expect(topic[1]).to_be_null()

        class GetCrypto(Vows.Context):
            def topic(self, storage):
                return (storage, storage.get_crypto('path'))

            def should_have_proper_crypto_storage(self, topic):
                expect(topic[0].crypto_storage).to_be_instance_of(NoStorage)

            def should_be_null(self, topic):
                expect(topic[1]).to_be_null()

########NEW FILE########
__FILENAME__ = mongo_storage_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from os.path import abspath, join, dirname

from pymongo import Connection
from pyvows import Vows, expect

from thumbor.storages.mongo_storage import Storage as MongoStorage
from thumbor.context import Context
from thumbor.config import Config
from fixtures.storage_fixture import IMAGE_URL, IMAGE_BYTES, get_server

FIXTURES_FOLDER = join(abspath(dirname(__file__)), 'fixtures')
CONNECTION = Connection('localhost', 7777)
COLLECTION = CONNECTION['thumbor']['images']


class MongoDBContext(Vows.Context):
    def teardown(self):
        CONNECTION.drop_database('thumbor')


@Vows.batch
class MongoStorageVows(MongoDBContext):
    class CanStoreImage(Vows.Context):
        def topic(self):
            storage = MongoStorage(Context(config=Config(MONGO_STORAGE_SERVER_PORT=7777)))
            storage.put(IMAGE_URL % 1, IMAGE_BYTES)
            return COLLECTION.find_one({'path': IMAGE_URL % 1})

        def should_be_in_catalog(self, topic):
            expect(topic).not_to_be_null()
            expect(topic).not_to_be_an_error()

    class KnowsIfImageExists(Vows.Context):
        def topic(self):
            storage = MongoStorage(Context(config=Config(MONGO_STORAGE_SERVER_PORT=7777)))
            storage.put(IMAGE_URL % 10000, IMAGE_BYTES)
            return storage.exists(IMAGE_URL % 10000)

        def should_exist(self, topic):
            expect(topic).not_to_be_an_error()
            expect(topic).to_be_true()

    class KnowsIfImageDoesNotExist(Vows.Context):
        def topic(self):
            storage = MongoStorage(Context(config=Config(MONGO_STORAGE_SERVER_PORT=7777)))
            return storage.exists(IMAGE_URL % 20000)

        def should_not_exist(self, topic):
            expect(topic).not_to_be_an_error()
            expect(topic).to_be_false()

    class CanRemoveImage(Vows.Context):
        def topic(self):
            storage = MongoStorage(Context(config=Config(MONGO_STORAGE_SERVER_PORT=7777)))
            storage.put(IMAGE_URL % 9999, IMAGE_BYTES)
            storage.remove(IMAGE_URL % 9999)
            return COLLECTION.find_one({'path': IMAGE_URL % 9999})

        def should_not_be_in_catalog(self, topic):
            expect(topic).not_to_be_an_error()
            expect(topic).to_be_null()

        class CanReRemoveImage(Vows.Context):
            def topic(self):
                storage = MongoStorage(Context(config=Config(MONGO_STORAGE_SERVER_PORT=7777)))
                storage.remove(IMAGE_URL % 9999)
                return COLLECTION.find_one({'path': IMAGE_URL % 9999})

            def should_not_be_in_catalog(self, topic):
                expect(topic).not_to_be_an_error()
                expect(topic).to_be_null()

    class CanGetImage(Vows.Context):
        def topic(self):
            storage = MongoStorage(Context(config=Config(MONGO_STORAGE_SERVER_PORT=7777)))
            storage.put(IMAGE_URL % 2, IMAGE_BYTES)
            return storage.get(IMAGE_URL % 2)

        def should_not_be_null(self, topic):
            expect(topic).not_to_be_null()
            expect(topic).not_to_be_an_error()

        def should_have_proper_bytes(self, topic):
            expect(topic).to_equal(IMAGE_BYTES)

    class GettingReturnsNoneWhenImageDoesNotExist(Vows.Context):
        def topic(self):
            storage = MongoStorage(Context(config=Config(MONGO_STORAGE_SERVER_PORT=7777)))
            return storage.get(IMAGE_URL % 99)

        def should_be_null(self, topic):
            expect(topic).to_be_null()

    class StoresCrypto(Vows.Context):
        class DoesNotStoreWhenConfigIsFalseInPutMethod(Vows.Context):
            def topic(self):
                storage = MongoStorage(
                    Context(config=Config(MONGO_STORAGE_SERVER_PORT=7777, STORES_CRYPTO_KEY_FOR_EACH_IMAGE=False)))
                storage.put(IMAGE_URL % 3, IMAGE_BYTES)

                return COLLECTION.find_one({'path': IMAGE_URL % 3})

            def should_be_in_catalog(self, topic):
                expect(topic).not_to_be_null()
                expect(topic).not_to_be_an_error()

            def should_not_have_crypto_key(self, topic):
                expect(topic).Not.to_include('crypto')

        class StoringEmptyKeyRaises(Vows.Context):
            def topic(self):
                conf = Config(MONGO_STORAGE_SERVER_PORT=7777, STORES_CRYPTO_KEY_FOR_EACH_IMAGE=True)
                server = get_server()
                storage = MongoStorage(Context(server=server, config=conf))
                storage.put(IMAGE_URL % 4, IMAGE_BYTES)

            def should_be_an_error(self, topic):
                expect(topic).to_be_an_error_like(RuntimeError)
                expect(topic).to_have_an_error_message_of(
                    "STORES_CRYPTO_KEY_FOR_EACH_IMAGE can't be True if no SECURITY_KEY specified"
                )

        class StoringProperKey(Vows.Context):
            def topic(self):
                conf = Config(MONGO_STORAGE_SERVER_PORT=7777, STORES_CRYPTO_KEY_FOR_EACH_IMAGE=True)

                storage = MongoStorage(
                    Context(
                        config=conf,
                        server=get_server('ACME-SEC')
                    )
                )

                storage.put(IMAGE_URL % 5, IMAGE_BYTES)

                return COLLECTION.find_one({'path': IMAGE_URL % 5})

            def should_be_in_catalog(self, topic):
                expect(topic).not_to_be_null()
                expect(topic).not_to_be_an_error()

            def should_have_crypto_key(self, topic):
                expect(topic).to_include('crypto')
                expect(topic['crypto']).to_equal('ACME-SEC')

        class GetProperKey(Vows.Context):
            def topic(self):
                conf = Config(MONGO_STORAGE_SERVER_PORT=7777, STORES_CRYPTO_KEY_FOR_EACH_IMAGE=True)
                server = get_server('ACME-SEC')
                storage = MongoStorage(Context(config=conf, server=server))
                storage.put(IMAGE_URL % 6, IMAGE_BYTES)

                return storage.get_crypto(IMAGE_URL % 6)

            def should_be_in_catalog(self, topic):
                expect(topic).not_to_be_null()
                expect(topic).not_to_be_an_error()

            def should_have_crypto_key(self, topic):
                expect(topic).to_equal('ACME-SEC')

        class GetNoKey(Vows.Context):
            def topic(self):
                storage = MongoStorage(
                    Context(config=Config(
                        MONGO_STORAGE_SERVER_PORT=7777, STORES_CRYPTO_KEY_FOR_EACH_IMAGE=True,
                        SECURITY_KEY='ACME-SEC')
                    )
                )
                return storage.get_crypto(IMAGE_URL % 7)

            def should_not_be_in_catalog(self, topic):
                expect(topic).to_be_null()

        class GetProperKeyBeforeExpiration(Vows.Context):
            def topic(self):
                conf = Config(
                    MONGO_STORAGE_SERVER_PORT=7777, STORES_CRYPTO_KEY_FOR_EACH_IMAGE=True,
                    STORAGE_EXPIRATION_SECONDS=5000
                )
                server = get_server('ACME-SEC')
                storage = MongoStorage(Context(server=server, config=conf))
                storage.put(IMAGE_URL % 8, IMAGE_BYTES)
                return storage.get(IMAGE_URL % 8)

            def should_be_in_catalog(self, topic):
                expect(topic).not_to_be_null()
                expect(topic).not_to_be_an_error()

            def should_have_crypto_key(self, topic):
                expect(topic).to_equal(IMAGE_BYTES)

        class GetNothingAfterExpiration(Vows.Context):
            def topic(self):
                config = Config(
                    MONGO_STORAGE_SERVER_PORT=7777, STORES_CRYPTO_KEY_FOR_EACH_IMAGE=True,
                    SECURITY_KEY='ACME-SEC', STORAGE_EXPIRATION_SECONDS=0
                )
                storage = MongoStorage(Context(config=config))
                storage.put(IMAGE_URL % 10, IMAGE_BYTES)

                item = storage.get(IMAGE_URL % 10)
                return item is None

            def should_be_expired(self, topic):
                expect(topic).to_be_true()

        class StoresCryptoAfterStoringImage(Vows.Context):
            def topic(self):
                conf = Config(MONGO_STORAGE_SERVER_PORT=7777, STORES_CRYPTO_KEY_FOR_EACH_IMAGE=False)
                server = get_server('ACME-SEC')
                storage = MongoStorage(Context(config=conf, server=server))
                storage.put(IMAGE_URL % 11, IMAGE_BYTES)

                conf.STORES_CRYPTO_KEY_FOR_EACH_IMAGE = True
                storage.put_crypto(IMAGE_URL % 11)

                item = storage.get_crypto(IMAGE_URL % 11)
                return item

            def should_be_acme_sec(self, topic):
                expect(topic).not_to_be_null()
                expect(topic).to_equal('ACME-SEC')

        class DoesNotStoreCryptoIfNoNeed(Vows.Context):
            def topic(self):
                conf = Config(MONGO_STORAGE_SERVER_PORT=7777, STORES_CRYPTO_KEY_FOR_EACH_IMAGE=False, SECURITY_KEY='ACME-SEC')
                storage = MongoStorage(Context(config=conf))
                storage.put(IMAGE_URL % 12, IMAGE_BYTES)
                storage.put_crypto(IMAGE_URL % 12)

                item = storage.get_crypto(IMAGE_URL % 12)
                return item

            def should_be_null(self, topic):
                expect(topic).to_be_null()

        class RaisesIfWrongConfig(Vows.Context):
            def topic(self):
                conf = Config(MONGO_STORAGE_SERVER_PORT=7777, STORES_CRYPTO_KEY_FOR_EACH_IMAGE=False)
                server = get_server('')
                storage = MongoStorage(Context(config=conf, server=server))
                storage.put(IMAGE_URL % 13, IMAGE_BYTES)

                conf.STORES_CRYPTO_KEY_FOR_EACH_IMAGE = True
                storage.put_crypto(IMAGE_URL % 13)

            def should_be_an_error(self, topic):
                expect(topic).to_be_an_error_like(RuntimeError)
                expect(topic).to_have_an_error_message_of(
                    "STORES_CRYPTO_KEY_FOR_EACH_IMAGE can't be True if no SECURITY_KEY specified"
                )

    class DetectorData(Vows.Context):
        def topic(self):
            conf = Config(MONGO_STORAGE_SERVER_PORT=7777)
            storage = MongoStorage(Context(config=conf))
            storage.put(IMAGE_URL % 14, IMAGE_BYTES)
            storage.put_detector_data(IMAGE_URL % 14, "some data")

            return storage.get_detector_data(IMAGE_URL % 14)

        def should_be_some_data(self, topic):
            expect(topic).to_equal('some data')

########NEW FILE########
__FILENAME__ = no_storage_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from pyvows import Vows, expect

from thumbor.storages.no_storage import Storage as NoStorage
from fixtures.storage_fixture import IMAGE_URL, IMAGE_BYTES


@Vows.batch
class NoStorageVows(Vows.Context):
    class CanStoreImage(Vows.Context):
        def topic(self):
            storage = NoStorage(None)
            storage.put(IMAGE_URL % 1, IMAGE_BYTES)
            return storage.get(IMAGE_URL % 1)

        def should_be_null(self, topic):
            expect(topic).to_be_null()

    class KnowsNoImages(Vows.Context):
        def topic(self):
            storage = NoStorage(None)
            return storage.exists(IMAGE_URL % 1)

        def should_be_false(self, topic):
            expect(topic).to_be_false()

    class RemovesImage(Vows.Context):
        def topic(self):
            storage = NoStorage(None)
            return storage.remove(IMAGE_URL % 1)

        def should_be_null(self, topic):
            expect(topic).to_be_null()

    class StoresCrypto(Vows.Context):
        def topic(self):
            storage = NoStorage(None)
            storage.put_crypto(IMAGE_URL % 2)

            return storage.get_crypto(IMAGE_URL % 2)

        def should_be_null(self, topic):
            expect(topic).to_be_null()

    class DetectorData(Vows.Context):
        def topic(self):
            storage = NoStorage(None)
            storage.put_detector_data(IMAGE_URL % 3, "some data")
            return storage.get_detector_data(IMAGE_URL % 3)

        def should_be_null(self, topic):
            expect(topic).to_be_null()

########NEW FILE########
__FILENAME__ = pil_engine_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from pyvows import Vows, expect
ctx = Vows.Context

import thumbor.engines.pil as PIL


@Vows.batch
class PilEngineVows(ctx):

    class ShouldRaiseIfFiltersNotAvailable(ctx):
        def topic(self):
            FILTERS_AVAILABLE_BAK = PIL.FILTERS_AVAILABLE
            PIL.FILTERS_AVAILABLE = False
            engine = PIL.Engine(None)
            try:
                return engine.paste(None, None, True)
            finally:
                PIL.FILTERS_AVAILABLE = FILTERS_AVAILABLE_BAK

        def should_be_an_error(self, topic):
            expect(topic).to_be_an_error()
            expect(topic).to_be_an_error_like(RuntimeError)
            expected = 'You need filters enabled to use paste with merge. Please reinstall thumbor with proper ' + \
                'compilation of its filters.'
            expect(topic).to_have_an_error_message_of(expected)

########NEW FILE########
__FILENAME__ = point_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from pyvows import Vows, expect

from thumbor.point import FocalPoint


@Vows.batch
class FocalPointVows(Vows.Context):

    class DefaultAlignmentPercentages(Vows.Context):
        def topic(self):
            return FocalPoint.ALIGNMENT_PERCENTAGES

        def should_have_left_alignment_of_0(self, topic):
            expect(topic['left']).to_equal(0.0)

        def should_have_center_alignment_of_half(self, topic):
            expect(topic['center']).to_equal(0.5)

        def should_have_right_alignment_of_one(self, topic):
            expect(topic['right']).to_equal(1.0)

        def should_have_top_alignment_of_0(self, topic):
            expect(topic['top']).to_equal(0.0)

        def should_have_middle_alignment_of_half(self, topic):
            expect(topic['middle']).to_equal(0.5)

        def should_have_bottom_alignment_of_one(self, topic):
            expect(topic['bottom']).to_equal(1.0)

    class NewPoint(Vows.Context):

        class DefaultWeight(Vows.Context):
            def topic(self):
                return FocalPoint(10, 20)

            def should_have_x_coord_of_10(self, topic):
                expect(topic.x).to_equal(10)

            def should_have_y_coord_of_20(self, topic):
                expect(topic.y).to_equal(20)

        class Weighted(Vows.Context):
            def topic(self):
                return FocalPoint(x=10, y=20, height=1.0, width=3.0, weight=3.0)

            def should_have_weight_of_three(self, topic):
                expect(topic.weight).to_equal(3.0)

            def should_have_proper_representation(self, topic):
                expect(str(topic)).to_equal('FocalPoint(x: 10, y: 20, width: 3, height: 1, weight: 3, origin: alignment)')

        class FromDict(Vows.Context):
            def topic(self):
                return FocalPoint.from_dict({'x': 10.1, 'y': 20.1, 'z': 5.1})

            def should_have_x_coord_of_10_1(self, topic):
                expect(topic.x).to_equal(10.1)

            def should_have_y_coord_of_20_1(self, topic):
                expect(topic.y).to_equal(20.1)

            def should_have_weight_of_5_1(self, topic):
                expect(topic.weight).to_equal(5.1)

            class ToDict(Vows.Context):
                def topic(self, prev_topic):
                    return prev_topic.to_dict()

                def should_create_the_original_dictionary(self, topic):
                    expect(topic).to_be_like({'x': 10.1, 'y': 20.1, 'z': 5.1, 'origin': 'alignment', 'width': 1.0, 'height': 1.0})

    class SquarePoint(Vows.Context):

        def topic(self):
            return FocalPoint.from_square(x=350, y=50, width=110, height=110)

        def should_have_x_of_450(self, topic):
            expect(topic.x).to_equal(405)

        def should_have_x_of_150(self, topic):
            expect(topic.y).to_equal(105)

        def should_have_weight_of_12100(self, topic):
            expect(topic.weight).to_equal(12100)

    class AlignedPoint(Vows.Context):

        class CenterMiddle(Vows.Context):
            def topic(self):
                return FocalPoint.from_alignment('center', 'middle', 300, 200)

            def should_have_x_of_150(self, topic):
                expect(topic.x).to_equal(150)

            def should_have_y_of_100(self, topic):
                expect(topic.y).to_equal(100)

            def should_have_weight_of_1(self, topic):
                expect(topic.weight).to_equal(1.0)

        class TopLeft(Vows.Context):
            def topic(self):
                return FocalPoint.from_alignment('left', 'top', 300, 200)

            def should_have_x_of_0(self, topic):
                expect(topic.x).to_equal(0)

            def should_have_y_of_0(self, topic):
                expect(topic.y).to_equal(0)

            def should_have_weight_of_1(self, topic):
                expect(topic.weight).to_equal(1.0)

        class BottomRight(Vows.Context):
            def topic(self):
                return FocalPoint.from_alignment('right', 'bottom', 300, 200)

            def should_have_x_of_300(self, topic):
                expect(topic.x).to_equal(300)

            def should_have_y_of_200(self, topic):
                expect(topic.y).to_equal(200)

            def should_have_weight_of_1(self, topic):
                expect(topic.weight).to_equal(1.0)

########NEW FILE########
__FILENAME__ = quality_filter_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from pyvows import Vows, expect

from thumbor.context import Context, RequestParameters
from thumbor.config import Config
from thumbor.importer import Importer
from thumbor.filters.quality import Filter
import thumbor.filters


@Vows.batch
class QualityFilterVows(Vows.Context):
    def topic(self):
        conf = Config()
        imp = Importer(conf)
        imp.filters = [Filter]
        ctx = Context(None, conf, imp)
        ctx.request = RequestParameters()

        runner = ctx.filters_factory.create_instances(ctx, "quality(10)")
        filter_instances = runner.filter_instances[thumbor.filters.PHASE_POST_TRANSFORM]

        filter_instances[0].run()
        return ctx.request.quality

    def should_equal_10(self, quality):
        expect(quality).to_equal(10)

########NEW FILE########
__FILENAME__ = redis_storage_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import redis
from pyvows import Vows, expect

from thumbor.storages.redis_storage import Storage as RedisStorage
from thumbor.context import Context
from thumbor.config import Config
from fixtures.storage_fixture import IMAGE_URL, IMAGE_BYTES, get_server


class RedisDBContext(Vows.Context):
    def setup(self):
        self.connection = redis.Redis(port=6668,
                                      host='localhost',
                                      db=0,
                                      password='hey_you')


@Vows.batch
class RedisStorageVows(RedisDBContext):
    class CanStoreImage(Vows.Context):
        def topic(self):
            config = Config(REDIS_STORAGE_SERVER_PORT=6668, REDIS_STORAGE_SERVER_PASSWORD='hey_you')
            storage = RedisStorage(Context(config=config, server=get_server('ACME-SEC')))
            storage.put(IMAGE_URL % 1, IMAGE_BYTES)
            return self.parent.connection.get(IMAGE_URL % 1)

        def should_be_in_catalog(self, topic):
            expect(topic).not_to_be_null()
            expect(topic).not_to_be_an_error()

    class KnowsImageExists(Vows.Context):
        def topic(self):
            config = Config(REDIS_STORAGE_SERVER_PORT=6668, REDIS_STORAGE_SERVER_PASSWORD='hey_you')
            storage = RedisStorage(Context(config=config, server=get_server('ACME-SEC')))
            storage.put(IMAGE_URL % 9999, IMAGE_BYTES)
            return storage.exists(IMAGE_URL % 9999)

        def should_exist(self, topic):
            expect(topic).not_to_be_an_error()
            expect(topic).to_be_true()

    class KnowsImageDoesNotExist(Vows.Context):
        def topic(self):
            config = Config(REDIS_STORAGE_SERVER_PORT=6668, REDIS_STORAGE_SERVER_PASSWORD='hey_you')
            storage = RedisStorage(Context(config=config, server=get_server('ACME-SEC')))
            return storage.exists(IMAGE_URL % 10000)

        def should_not_exist(self, topic):
            expect(topic).not_to_be_an_error()
            expect(topic).to_be_false()

    class CanRemoveImage(Vows.Context):
        def topic(self):
            config = Config(REDIS_STORAGE_SERVER_PORT=6668, REDIS_STORAGE_SERVER_PASSWORD='hey_you')
            storage = RedisStorage(Context(config=config, server=get_server('ACME-SEC')))
            storage.put(IMAGE_URL % 10001, IMAGE_BYTES)
            storage.remove(IMAGE_URL % 10001)
            return self.parent.connection.get(IMAGE_URL % 10001)

        def should_not_be_in_catalog(self, topic):
            expect(topic).not_to_be_an_error()
            expect(topic).to_be_null()

        class CanReRemoveImage(Vows.Context):
            def topic(self):
                config = Config(REDIS_STORAGE_SERVER_PORT=6668, REDIS_STORAGE_SERVER_PASSWORD='hey_you')
                storage = RedisStorage(Context(config=config, server=get_server('ACME-SEC')))
                return storage.remove(IMAGE_URL % 10001)

            def should_not_be_in_catalog(self, topic):
                expect(topic).not_to_be_an_error()
                expect(topic).to_be_null()

    class CanGetImage(Vows.Context):
        def topic(self):
            config = Config(REDIS_STORAGE_SERVER_PORT=6668, REDIS_STORAGE_SERVER_PASSWORD='hey_you')
            storage = RedisStorage(Context(config=config, server=get_server('ACME-SEC')))

            storage.put(IMAGE_URL % 2, IMAGE_BYTES)
            return storage.get(IMAGE_URL % 2)

        def should_not_be_null(self, topic):
            expect(topic).not_to_be_null()
            expect(topic).not_to_be_an_error()

        def should_have_proper_bytes(self, topic):
            expect(topic).to_equal(IMAGE_BYTES)

    class CryptoVows(Vows.Context):
        class RaisesIfInvalidConfig(Vows.Context):
            def topic(self):
                config = Config(
                    REDIS_STORAGE_SERVER_PORT=6668, REDIS_STORAGE_SERVER_PASSWORD='hey_you',
                    STORES_CRYPTO_KEY_FOR_EACH_IMAGE=True)
                storage = RedisStorage(Context(config=config, server=get_server('')))
                storage.put(IMAGE_URL % 3, IMAGE_BYTES)
                storage.put_crypto(IMAGE_URL % 3)

            def should_be_an_error(self, topic):
                expect(topic).to_be_an_error_like(RuntimeError)
                expect(topic).to_have_an_error_message_of(
                    "STORES_CRYPTO_KEY_FOR_EACH_IMAGE can't be True if no SECURITY_KEY specified"
                )

        class GettingCryptoForANewImageReturnsNone(Vows.Context):
            def topic(self):
                config = Config(
                    REDIS_STORAGE_SERVER_PORT=6668, REDIS_STORAGE_SERVER_PASSWORD='hey_you',
                    STORES_CRYPTO_KEY_FOR_EACH_IMAGE=True
                )
                storage = RedisStorage(Context(config=config, server=get_server('ACME-SEC')))
                return storage.get_crypto(IMAGE_URL % 9999)

            def should_be_null(self, topic):
                expect(topic).to_be_null()

        class DoesNotStoreIfConfigSaysNotTo(Vows.Context):
            def topic(self):
                config = Config(REDIS_STORAGE_SERVER_PORT=6668, REDIS_STORAGE_SERVER_PASSWORD='hey_you')
                storage = RedisStorage(Context(config=config, server=get_server('ACME-SEC')))
                storage.put(IMAGE_URL % 5, IMAGE_BYTES)
                storage.put_crypto(IMAGE_URL % 5)
                return storage.get_crypto(IMAGE_URL % 5)

            def should_be_null(self, topic):
                expect(topic).to_be_null()

        class CanStoreCrypto(Vows.Context):
            def topic(self):
                config = Config(
                    REDIS_STORAGE_SERVER_PORT=6668, REDIS_STORAGE_SERVER_PASSWORD='hey_you',
                    STORES_CRYPTO_KEY_FOR_EACH_IMAGE=True
                )
                storage = RedisStorage(Context(config=config, server=get_server('ACME-SEC')))

                storage.put(IMAGE_URL % 6, IMAGE_BYTES)
                storage.put_crypto(IMAGE_URL % 6)
                return storage.get_crypto(IMAGE_URL % 6)

            def should_not_be_null(self, topic):
                expect(topic).not_to_be_null()
                expect(topic).not_to_be_an_error()

            def should_have_proper_key(self, topic):
                expect(topic).to_equal('ACME-SEC')

    class DetectorVows(Vows.Context):
        class CanStoreDetectorData(Vows.Context):
            def topic(self):
                config = Config(REDIS_STORAGE_SERVER_PORT=6668, REDIS_STORAGE_SERVER_PASSWORD='hey_you')
                storage = RedisStorage(Context(config=config, server=get_server('ACME-SEC')))
                storage.put(IMAGE_URL % 7, IMAGE_BYTES)
                storage.put_detector_data(IMAGE_URL % 7, 'some-data')
                return storage.get_detector_data(IMAGE_URL % 7)

            def should_not_be_null(self, topic):
                expect(topic).not_to_be_null()
                expect(topic).not_to_be_an_error()

            def should_equal_some_data(self, topic):
                expect(topic).to_equal('some-data')

        class ReturnsNoneIfNoDetectorData(Vows.Context):
            def topic(self):
                config = Config(REDIS_STORAGE_SERVER_PORT=6668, REDIS_STORAGE_SERVER_PASSWORD='hey_you')
                storage = RedisStorage(Context(config=config, server=get_server('ACME-SEC')))
                return storage.get_detector_data(IMAGE_URL % 10000)

            def should_not_be_null(self, topic):
                expect(topic).to_be_null()

########NEW FILE########
__FILENAME__ = result_storages_file_storage_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import random

from pyvows import Vows, expect

from thumbor.context import Context, RequestParameters
from thumbor.config import Config
from thumbor.result_storages.file_storage import Storage as FileStorage

TEST_HTTP_PATH = 'http://example.com/path/to/a.jpg'

@Vows.batch
class ResultStoragesFileStorageVows(Vows.Context):
    class NormalizedPathWithAutoWebpVow(Vows.Context):
        def topic(self):
            config = Config(
                AUTO_WEBP=True,
                RESULT_STORAGE_FILE_STORAGE_ROOT_PATH="/tmp/thumbor/result_storages%s" % (random.choice(['', '/'])))
            context = Context(config=config)
            context.request = RequestParameters(accepts_webp=True)
            return FileStorage(context)

        def check_http_path(self, topic):
            expect(topic).not_to_be_null()
            expect(topic.normalize_path(TEST_HTTP_PATH)).to_equal('/tmp/thumbor/result_storages/v2/webp/ht/tp/example.com/path/to/a.jpg')

    class NormalizedPathNoWebpVow(Vows.Context):
        def topic(self):
            config = Config(
                AUTO_WEBP=False,
                RESULT_STORAGE_FILE_STORAGE_ROOT_PATH="/tmp/thumbor/result_storages%s" % (random.choice(['', '/'])))
            context = Context(config=config)
            context.request = RequestParameters(accepts_webp=False)
            return FileStorage(context)

        def check_http_path(self, topic):
            expect(topic).not_to_be_null()
            expect(topic.normalize_path(TEST_HTTP_PATH)).to_equal('/tmp/thumbor/result_storages/v2/ht/tp/example.com/path/to/a.jpg')

########NEW FILE########
__FILENAME__ = sentry_error_handler_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from pyvows import Vows, expect

from thumbor import __version__
from thumbor.error_handlers.sentry import ErrorHandler
from thumbor.config import Config
from thumbor.context import Context, ServerParameters


class FakeSentry(object):
    def __init__(self, dsn):
        self.captured_exceptions = []

    def captureException(self, exception, *args, **kw):
        self.captured_exceptions.append((exception, args, kw))


class FakeRequest(object):
    def __init__(self):
        self.headers = {
            'header1': 'value1',
            'Cookie': 'cookie1=value; cookie2=value2;'
        }

        self.url = "test/"
        self.method = "GET"
        self.arguments = []
        self.body = "body"
        self.query = "a=1&b=2"
        self.remote_ip = "127.0.0.1"

    def full_url(self):
        return "http://test/%s" % self.url


class FakeHandler(object):
    def __init__(self):
        self.request = FakeRequest()


@Vows.batch
class SentrErrorHandlerVows(Vows.Context):
    class WhenInvalidConfiguration(Vows.Context):
        def topic(self):
            cfg = Config()
            ErrorHandler(cfg)

        def should_be_error(self, topic):
            expect(topic).to_be_an_error()
            expect(topic).to_be_an_error_like(RuntimeError)

    class WhenErrorOccurs(Vows.Context):
        def topic(self):
            cfg = Config(SECURITY_KEY='ACME-SEC', SENTRY_DSN_URL="http://sentry-dsn-url")
            server = ServerParameters(8889, 'localhost', 'thumbor.conf', None, 'info', None)
            server.security_key = 'ACME-SEC'
            ctx = Context(server, cfg, None)

            client_mock = FakeSentry("FAKE DSN")
            handler = ErrorHandler(cfg, client=client_mock)
            http_handler = FakeHandler()

            handler.handle_error(ctx, http_handler, RuntimeError("Test"))

            return client_mock

        def should_have_called_client(self, topic):
            expect(topic.captured_exceptions).not_to_be_empty()
            expect(topic.captured_exceptions).to_length(1)

            exception, args, kw = topic.captured_exceptions[0]
            expect(exception.__class__.__name__).to_equal("RuntimeError")
            expect(kw).to_include('data')
            expect(kw).to_include('extra')

            data, extra = kw['data'], kw['extra']

            expect(extra).to_include('thumbor-version')
            expect(extra['thumbor-version']).to_equal(__version__)

            expect(extra).to_include('Headers')
            expect(extra['Headers']).to_length(2)

            expect(extra['Headers']).to_include('Cookie')
            expect(extra['Headers']['Cookie']).to_length(2)

            expect(data['modules']).not_to_be_empty()

            del data['modules']

            expect(data).to_be_like({
                'sentry.interfaces.Http': {
                    'url': "http://test/test/",
                    'method': "GET",
                    'data': [],
                    'body': "body",
                    'query_string': "a=1&b=2"
                },
                'sentry.interfaces.User': {
                    'ip': "127.0.0.1",
                }
            })

########NEW FILE########
__FILENAME__ = transformer_test_data
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from thumbor.point import FocalPoint as fp
from thumbor.context import Context, RequestParameters
from thumbor.config import Config
from thumbor.importer import Importer
from thumbor.detectors import BaseDetector
from thumbor.storages.no_storage import Storage as NoStorage


class MockEngine(object):
    def __init__(self, size):
        self.size = size
        self.calls = {
            'resize': [],
            'crop': [],
            'vertical_flip': 0,
            'horizontal_flip': 0
        }
        self.focal_points = None

    def resize(self, width, height):
        self.calls['resize'].append({
            'width': width,
            'height': height
        })

    def crop(self, left, top, right, bottom):
        self.calls['crop'].append({
            'left': left,
            'top': top,
            'right': right,
            'bottom': bottom
        })

    def flip_horizontally(self):
        self.calls['horizontal_flip'] += 1

    def flip_vertically(self):
        self.calls['vertical_flip'] += 1

    def get_proportional_width(self, new_height):
        width, height = self.size
        return float(new_height) * width / height

    def get_proportional_height(self, new_width):
        width, height = self.size
        return float(new_width) * height / width

    def focus(self, focal_points):
        self.focal_points = focal_points


class MockSyncDetector(BaseDetector):
    def detect(self, callback):
        callback([])


class MockErrorSyncDetector(BaseDetector):
    def detect(self, callback):
        raise Exception('x')


class TestData(object):
    def __init__(
            self,
            source_width, source_height,
            target_width, target_height,
            halign, valign, focal_points,
            crop_left, crop_top, crop_right, crop_bottom,
            fit_in=False, adaptive=False, meta=False):

        self.source_width = source_width
        self.source_height = source_height
        self.target_width = target_width
        self.target_height = target_height
        self.halign = halign
        self.valign = valign
        self.focal_points = focal_points
        self.crop_left = crop_left
        self.crop_top = crop_top
        self.crop_right = crop_right
        self.crop_bottom = crop_bottom
        self.fit_in = fit_in
        self.adaptive = adaptive
        self.meta = meta

    def __repr__(self):
        return self.__str__()

    def __unicode__(self):
        return self.__str__()

    def __str__(self):
        crop_message = ""
        if self.crop_left is not None:
            crop_message = "it should crop %dx%d-%dx%d and " % (
                self.crop_left, self.crop_top,
                self.crop_right, self.crop_bottom
            )
        return "For an image of %dx%d resizing to %sx%s, %sit should resize to %sx%s" % (
            self.source_width, self.source_height,
            self.target_width, self.target_height,
            crop_message,
            self.target_width, self.target_height
        )

    def to_context(self, detectors=[], ignore_detector_error=False):
        self.engine = MockEngine((self.source_width, self.source_height))

        flip_horizontally = self.target_width < 0
        flip_vertically = self.target_height < 0
        self.target_width = self.target_width == "orig" and "orig" or abs(self.target_width)
        self.target_height = self.target_height == "orig" and "orig" or abs(self.target_height)

        importer = Importer(None)
        importer.detectors = detectors
        importer.storage = NoStorage
        config = Config()
        config.IGNORE_SMART_ERRORS = ignore_detector_error
        ctx = Context(server=None, config=config, importer=importer)
        ctx.modules.engine = self.engine

        ctx.request = RequestParameters(
            buffer=None,
            debug=False,
            meta=self.meta,
            crop={
                'left': self.crop_left,
                'top': self.crop_top,
                'right': self.crop_right,
                'bottom': self.crop_bottom
            },
            adaptive=self.adaptive,
            fit_in=self.fit_in,
            horizontal_flip=flip_horizontally,
            vertical_flip=flip_vertically,
            width=self.target_width,
            height=self.target_height,
            halign=self.halign,
            valign=self.valign,
            focal_points=self.focal_points,
            smart=True,
            extension="JPEG",
            filters=[],
            quality=80,
            image="some.jpeg"
        )

        return ctx

    @property
    def resize_error_message(self):
        message = "The engine resize should have been called with %sx%s" % (self.target_width, self.target_height)
        if not self.engine.calls['resize']:
            return "%s, but was never called" % message
        else:
            last_resize = self.engine.calls['resize'][0]
            return "%s, but was called with %sx%s" % (message, last_resize['width'], last_resize['height'])

    def has_resized_properly(self):
        if not self.target_width and not self.target_height:
            return True

        if (self.target_width == self.source_width and self.target_height == self.source_height) or \
           (self.target_width == self.source_width and self.target_height == "orig") or \
           (self.target_width == "orig" and self.target_height == self.source_height) or \
           (self.target_width == "orig" and self.target_height == "orig"):
            return True

        assert self.engine.calls['resize'], self.resize_error_message

        if not self.target_width:
            assert self.engine.calls['resize'][0]['width'] == float(self.source_width) * self.target_height / self.source_height, self.resize_error_message
            assert self.engine.calls['resize'][0]['height'] == self.target_height, self.resize_error_message
            return True

        if not self.target_height:
            assert self.engine.calls['resize'][0]['width'] == self.target_width, self.resize_error_message
            assert self.engine.calls['resize'][0]['height'] == float(self.source_height) * self.target_width / self.source_width, self.resize_error_message
            return True

        assert self.engine.calls['resize'][0]['width'] == \
            (self.target_width == "orig" and self.source_width or self.target_width), self.resize_error_message
        assert self.engine.calls['resize'][0]['height'] == \
            (self.target_height == "orig" and self.source_height or self.target_height), self.resize_error_message
        return True

    @property
    def crop_error_message(self):
        message = "The engine crop should have been called with %dx%d %dx%d" % (self.crop_left, self.crop_top, self.crop_right, self.crop_bottom)
        if not self.engine.calls['crop']:
            return "%s, but was never called" % message
        else:
            last_crop = self.engine.calls['crop'][0]
            return "%s, but was called with %dx%d %dx%d" % (message, last_crop['left'], last_crop['top'], last_crop['right'], last_crop['bottom'])

    def has_cropped_properly(self):
        if self.crop_left is None:
            assert not self.engine.calls['crop'], 'The engine crop should NOT have been called but was with %(left)dx%(top)d %(right)dx%(bottom)d' % (self.engine.calls['crop'][0])
            return True
        assert self.engine.calls['crop'], self.crop_error_message
        assert self.engine.calls['crop'][0]['left'] == self.crop_left, self.crop_error_message

        assert self.engine.calls['crop'][0]['top'] == self.crop_top, self.crop_error_message

        assert self.engine.calls['crop'][0]['right'] == self.crop_right, self.crop_error_message

        assert self.engine.calls['crop'][0]['bottom'] == self.crop_bottom, self.crop_error_message

        return True

TESTITEMS = [
    TestData(
        source_width=800, source_height=600,
        target_width=400, target_height=150,
        halign="center", valign="middle",
        focal_points=[],
        crop_left=0, crop_top=75, crop_right=800, crop_bottom=375
    ),
    TestData(
        source_width=600, source_height=800,
        target_width=150, target_height=400,
        halign="center", valign="middle",
        focal_points=[],
        crop_left=150, crop_top=0, crop_right=450, crop_bottom=800
    ),
    TestData(
        source_width=600, source_height=800,
        target_width=300, target_height=400,
        halign="center", valign="middle",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),
    TestData(
        source_width=800, source_height=600,
        target_width=0, target_height=0,
        halign="center", valign="middle",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),
    TestData(
        source_width=800, source_height=600,
        target_width=400, target_height=0,
        halign="center", valign="middle",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),
    TestData(
        source_width=200, source_height=140,
        target_width=180, target_height=100,
        halign="center", valign="middle",
        focal_points=[],
        crop_left=0, crop_top=3, crop_right=200, crop_bottom=114
    ),

    # tests with focal points
    TestData(
        source_width=200, source_height=200,
        target_width=100, target_height=100,
        halign="center", valign="middle",
        focal_points=[fp(100, 100, 1)],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),
    TestData(
        source_width=400, source_height=200,
        target_width=100, target_height=100,
        halign="center", valign="middle",
        focal_points=[fp(100, 100, 1)],
        crop_left=50.0, crop_top=0, crop_right=250.0, crop_bottom=200
    ),
    TestData(
        source_width=400, source_height=200,
        target_width=100, target_height=200,
        halign="center", valign="middle",
        focal_points=[fp(100, 50, 1), fp(300, 50, 1)],
        crop_left=150.0, crop_top=0, crop_right=250.0, crop_bottom=200
    ),
    TestData(
        source_width=400, source_height=200,
        target_width=100, target_height=200,
        halign="center", valign="middle",
        focal_points=[fp(100, 150, 1), fp(300, 150, 1)],
        crop_left=150.0, crop_top=0, crop_right=250.0, crop_bottom=200
    ),
    TestData(
        source_width=400, source_height=200,
        target_width=100, target_height=200,
        halign="center", valign="middle",
        focal_points=[fp(100, 50, 1), fp(100, 150, 1)],
        crop_left=75.0, crop_top=0, crop_right=175.0, crop_bottom=200
    ),
    TestData(
        source_width=400, source_height=200,
        target_width=100, target_height=200,
        halign="center", valign="middle",
        focal_points=[fp(300, 50, 1), fp(300, 150, 1)],
        crop_left=225.0, crop_top=0, crop_right=325.0, crop_bottom=200
    ),
    TestData(
        source_width=200, source_height=400,
        target_width=100, target_height=200,
        halign="center", valign="middle",
        focal_points=[fp(100, 50, 1), fp(300, 50, 1)],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),
    TestData(
        source_width=200, source_height=400,
        target_width=100, target_height=200,
        halign="center", valign="middle",
        focal_points=[fp(100, 150, 1), fp(300, 150, 1)],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),
    TestData(
        source_width=200, source_height=400,
        target_width=100, target_height=200,
        halign="center", valign="middle",
        focal_points=[fp(100, 50, 1), fp(100, 150, 1)],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),
    TestData(
        source_width=200, source_height=400,
        target_width=100, target_height=200,
        halign="center", valign="middle",
        focal_points=[fp(300, 50, 1), fp(300, 150, 1)],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),
    TestData(
        source_width=400, source_height=200,
        target_width=100, target_height=100,
        halign="center", valign="middle",
        focal_points=[fp(50, 100, 1), fp(50, 300, 1), fp(150, 100, 1), fp(150, 300, 1)],
        crop_left=50.0, crop_top=0, crop_right=250.0, crop_bottom=200
    ),

    #Width maior

    TestData(
        source_width=800, source_height=600,
        target_width=400, target_height=300,
        halign="center", valign="bottom",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),

    TestData(
        source_width=700, source_height=300,
        target_width=150, target_height=300,
        halign="center", valign="bottom",
        focal_points=[],
        crop_left=275, crop_top=0, crop_right=425, crop_bottom=300
    ),

    TestData(
        source_width=700, source_height=300,
        target_width=300, target_height=150,
        halign="right", valign="bottom",
        focal_points=[],
        crop_left=100, crop_top=0, crop_right=700, crop_bottom=300
    ),

    TestData(
        source_width=700, source_height=300,
        target_width=300, target_height=150,
        halign="left", valign="bottom",
        focal_points=[],
        crop_left=0, crop_top=0, crop_right=600, crop_bottom=300
    ),

    TestData(
        source_width=700, source_height=300,
        target_width=150, target_height=300,
        halign="center", valign="bottom",
        focal_points=[],
        crop_left=275, crop_top=0, crop_right=425, crop_bottom=300
    ),

    TestData(
        source_width=700, source_height=300,
        target_width=150, target_height=300,
        halign="left", valign="bottom",
        focal_points=[],
        crop_left=0, crop_top=0, crop_right=150, crop_bottom=300
    ),

    TestData(
        source_width=700, source_height=300,
        target_width=150, target_height=300,
        halign="right", valign="bottom",
        focal_points=[],
        crop_left=550, crop_top=0, crop_right=700, crop_bottom=300
    ),

    ##/* Height maior */
    TestData(
        source_width=300, source_height=800,
        target_width=200, target_height=300,
        halign="center", valign="bottom",
        focal_points=[],
        crop_left=0, crop_top=251, crop_right=300, crop_bottom=701
    ),

    TestData(
        source_width=300, source_height=800,
        target_width=200, target_height=300,
        halign="left", valign="bottom",
        focal_points=[],
        crop_left=0, crop_top=251, crop_right=300, crop_bottom=701
    ),

    TestData(
        source_width=300, source_height=800,
        target_width=200, target_height=300,
        halign="right", valign="bottom",
        focal_points=[],
        crop_left=0, crop_top=251, crop_right=300, crop_bottom=701
    ),

    TestData(
        source_width=500, source_height=600,
        target_width=300, target_height=250,
        halign="center", valign="bottom",
        focal_points=[],
        crop_left=0, crop_top=119, crop_right=500, crop_bottom=536
    ),

    TestData(
        source_width=500, source_height=600,
        target_width=300, target_height=250,
        halign="left", valign="bottom",
        focal_points=[],
        crop_left=0, crop_top=119, crop_right=500, crop_bottom=536
    ),

    TestData(
        source_width=500, source_height=600,
        target_width=300, target_height=250,
        halign="right", valign="bottom",
        focal_points=[],
        crop_left=0, crop_top=119, crop_right=500, crop_bottom=536
    ),

    ##Height na proporçao#
    TestData(
        source_width=600, source_height=800,
        target_width=300, target_height=0,
        halign="right", valign="bottom",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),

    TestData(
        source_width=600, source_height=800,
        target_width=300, target_height=0,
        halign="center", valign="bottom",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),

    TestData(
        source_width=600, source_height=800,
        target_width=300, target_height=0,
        halign="left", valign="bottom",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),

    TestData(
        source_width=600, source_height=800,
        target_width=250, target_height=0,
        halign="left", valign="bottom",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),

    TestData(
        source_width=600, source_height=800,
        target_width=250, target_height=0,
        halign="right", valign="bottom",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),

    TestData(
        source_width=600, source_height=800,
        target_width=250, target_height=0,
        halign="center", valign="bottom",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),

    #Width na proporçao
    TestData(
        source_width=600, source_height=800,
        target_width=0, target_height=400,
        halign="right", valign="bottom",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),

    TestData(
        source_width=600, source_height=800,
        target_width=0, target_height=400,
        halign="left", valign="bottom",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),

    TestData(
        source_width=600, source_height=800,
        target_width=0, target_height=400,
        halign="center", valign="bottom",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),

    TestData(
        source_width=600, source_height=800,
        target_width=0, target_height=350,
        halign="center", valign="bottom",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),

    TestData(
        source_width=600, source_height=800,
        target_width=0, target_height=350,
        halign="left", valign="bottom",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),

    TestData(
        source_width=600, source_height=800,
        target_width=0, target_height=350,
        halign="right", valign="bottom",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),

    TestData(
        source_width=800, source_height=600,
        target_width=400, target_height=150,
        halign="center", valign="middle",
        focal_points=[],
        crop_left=0, crop_top=75, crop_right=800, crop_bottom=375
    ),

    TestData(
        source_width=800, source_height=300,
        target_width=400, target_height=150,
        halign="center", valign="middle",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),

    TestData(
        source_width=800, source_height=300,
        target_width=400, target_height=150,
        halign="right", valign="middle",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),

    TestData(
        source_width=800, source_height=300,
        target_width=400, target_height=150,
        halign="left", valign="middle",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),

    TestData(
        source_width=700, source_height=300,
        target_width=300, target_height=150,
        halign="center", valign="middle",
        focal_points=[],
        crop_left=50, crop_top=0, crop_right=650, crop_bottom=300
    ),

    TestData(
        source_width=700, source_height=300,
        target_width=300, target_height=150,
        halign="left", valign="middle",
        focal_points=[],
        crop_left=0, crop_top=0, crop_right=600, crop_bottom=300
    ),

    TestData(
        source_width=700, source_height=300,
        target_width=300, target_height=150,
        halign="right", valign="middle",
        focal_points=[],
        crop_left=100, crop_top=0, crop_right=700, crop_bottom=300
    ),

    TestData(
        source_width=700, source_height=300,
        target_width=150, target_height=300,
        halign="center", valign="middle",
        focal_points=[],
        crop_left=275, crop_top=0, crop_right=425, crop_bottom=300
    ),

    TestData(
        source_width=700, source_height=300,
        target_width=150, target_height=300,
        halign="left", valign="middle",
        focal_points=[],
        crop_left=0, crop_top=0, crop_right=150, crop_bottom=300
    ),

    TestData(
        source_width=700, source_height=300,
        target_width=150, target_height=300,
        halign="right", valign="middle",
        focal_points=[],
        crop_left=550, crop_top=0, crop_right=700, crop_bottom=300
    ),

    TestData(
        source_width=350, source_height=700,
        target_width=200, target_height=600,
        halign="left", valign="middle",
        focal_points=[],
        crop_left=0, crop_top=0, crop_right=234, crop_bottom=700
    ),

    TestData(
        source_width=350, source_height=700,
        target_width=200, target_height=600,
        halign="center", valign="middle",
        focal_points=[],
        crop_left=58, crop_top=0, crop_right=292, crop_bottom=700
    ),

    TestData(
        source_width=350, source_height=700,
        target_width=200, target_height=600,
        halign="right", valign="middle",
        focal_points=[],
        crop_left=116, crop_top=0, crop_right=350, crop_bottom=700
    ),

    TestData(
        source_width=500, source_height=600,
        target_width=300, target_height=250,
        halign="left", valign="middle",
        focal_points=[],
        crop_left=0, crop_top=27, crop_right=500, crop_bottom=444
    ),

    TestData(
        source_width=500, source_height=600,
        target_width=300, target_height=250,
        halign="center", valign="middle",
        focal_points=[],
        crop_left=0, crop_top=27, crop_right=500, crop_bottom=444
    ),

    TestData(
        source_width=500, source_height=600,
        target_width=300, target_height=250,
        halign="right", valign="middle",
        focal_points=[],
        crop_left=0, crop_top=27, crop_right=500, crop_bottom=444
    ),

    TestData(
        source_width=1, source_height=1,
        target_width=0, target_height=0,
        halign="left", valign="middle",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),

    TestData(
        source_width=1, source_height=1,
        target_width=0, target_height=0,
        halign="center", valign="middle",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),

    TestData(
        source_width=1, source_height=1,
        target_width=0, target_height=0,
        halign="right", valign="middle",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),

    TestData(
        source_width=200, source_height=400,
        target_width=0, target_height=1,
        halign="left", valign="middle",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),

    TestData(
        source_width=200, source_height=200,
        target_width=16, target_height=16,
        halign="left", valign="middle",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),

    #--------------------Normal---------------------------------------
    TestData(
        source_width=800, source_height=600,
        target_width=400, target_height=150,
        halign="left", valign="top",
        focal_points=[],
        crop_left=0, crop_top=0, crop_right=800, crop_bottom=300
    ),
    TestData(
        source_width=800, source_height=600,
        target_width=400, target_height=150,
        halign="center", valign="top",
        focal_points=[],
        crop_left=0, crop_top=0, crop_right=800, crop_bottom=300
    ),
    TestData(
        source_width=800, source_height=600,
        target_width=400, target_height=150,
        halign="right", valign="top",
        focal_points=[],
        crop_left=0, crop_top=0, crop_right=800, crop_bottom=300
    ),
    #---------------Normal Invertido---------------------------
    TestData(
        source_width=600, source_height=800,
        target_width=150, target_height=400,
        halign="left", valign="top",
        focal_points=[],
        crop_left=0, crop_top=0, crop_right=300, crop_bottom=800
    ),
    TestData(
        source_width=600, source_height=800,
        target_width=150, target_height=400,
        halign="center", valign="top",
        focal_points=[],
        crop_left=150, crop_top=0, crop_right=450, crop_bottom=800
    ),
    TestData(
        source_width=600, source_height=800,
        target_width=150, target_height=400,
        halign="right", valign="top",
        focal_points=[],
        crop_left=300, crop_top=0, crop_right=600, crop_bottom=800
    ),
    #-----------Largo e Baixo---------------------
    TestData(
        source_width=800, source_height=60,
        target_width=400, target_height=15,
        halign="left", valign="top",
        focal_points=[],
        crop_left=0, crop_top=0, crop_right=800, crop_bottom=30
    ),
    TestData(
        source_width=800, source_height=60,
        target_width=400, target_height=15,
        halign="center", valign="top",
        focal_points=[],
        crop_left=0, crop_top=0, crop_right=800, crop_bottom=30
    ),
    TestData(
        source_width=800, source_height=60,
        target_width=400, target_height=15,
        halign="right", valign="top",
        focal_points=[],
        crop_left=0, crop_top=0, crop_right=800, crop_bottom=30
    ),
    #----------------Alto e Estreito--------------------------
    TestData(
        source_width=60, source_height=800,
        target_width=15, target_height=400,
        halign="left", valign="top",
        focal_points=[],
        crop_left=0, crop_top=0, crop_right=30, crop_bottom=800
    ),
    TestData(
        source_width=60, source_height=800,
        target_width=15, target_height=400,
        halign="center", valign="top",
        focal_points=[],
        crop_left=15, crop_top=0, crop_right=45, crop_bottom=800
    ),
    TestData(
        source_width=60, source_height=800,
        target_width=15, target_height=400,
        halign="right", valign="top",
        focal_points=[],
        crop_left=30, crop_top=0, crop_right=60, crop_bottom=800
    ),
    #------------------Valores Pequenos--------------------------
    TestData(
        source_width=8, source_height=6,
        target_width=4, target_height=2,
        halign="left", valign="top",
        focal_points=[],
        crop_left=0, crop_top=0, crop_right=8, crop_bottom=4
    ),
    TestData(
        source_width=8, source_height=6,
        target_width=4, target_height=2,
        halign="center", valign="top",
        focal_points=[],
        crop_left=0, crop_top=0, crop_right=8, crop_bottom=4
    ),
    TestData(
        source_width=8, source_height=6,
        target_width=4, target_height=2,
        halign="right", valign="top",
        focal_points=[],
        crop_left=0, crop_top=0, crop_right=8, crop_bottom=4
    ),
    #----------------Valores Pequeno Invertido-------------
    TestData(
        source_width=6, source_height=8,
        target_width=2, target_height=4,
        halign="left", valign="top",
        focal_points=[],
        crop_left=0, crop_top=0, crop_right=4, crop_bottom=8
    ),
    TestData(
        source_width=6, source_height=8,
        target_width=2, target_height=4,
        halign="center", valign="top",
        focal_points=[],
        crop_left=1, crop_top=0, crop_right=5, crop_bottom=8
    ),
    TestData(
        source_width=6, source_height=8,
        target_width=2, target_height=4,
        halign="right", valign="top",
        focal_points=[],
        crop_left=2, crop_top=0, crop_right=6, crop_bottom=8
    ),
    #----------------Valores Proporcionais-------------
    TestData(
        source_width=800, source_height=600,
        target_width=400, target_height=300,
        halign="left", valign="top",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),
    TestData(
        source_width=800, source_height=600,
        target_width=400, target_height=300,
        halign="center", valign="top",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),
    TestData(
        source_width=800, source_height=600,
        target_width=400, target_height=300,
        halign="right", valign="top",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),
    #----------------Valores Iguais-----------------------
    TestData(
        source_width=800, source_height=600,
        target_width=800, target_height=600,
        halign="left", valign="top",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),
    TestData(
        source_width=800, source_height=600,
        target_width=800, target_height=600,
        halign="center", valign="top",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),
    TestData(
        source_width=800, source_height=600,
        target_width=800, target_height=600,
        halign="right", valign="top",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
    ),
    TestData(
        source_width=800, source_height=400,
        target_width=400, target_height="orig",
        halign="middle", valign="middle",
        focal_points=[],
        crop_left=200, crop_top=0, crop_right=600, crop_bottom=400
    ),
    TestData(
        source_width=800, source_height=400,
        target_width="orig", target_height=100,
        halign="middle", valign="middle",
        focal_points=[],
        crop_left=200, crop_top=0, crop_right=600, crop_bottom=400
    ),
    TestData(
        source_width=800, source_height=400,
        target_width="orig", target_height="orig",
        halign="middle", valign="middle",
        focal_points=[],
        crop_left=200, crop_top=0, crop_right=600, crop_bottom=400
    )
]

FIT_IN_CROP_DATA = [
    (TestData(
        source_width=800, source_height=400,
        target_width=400, target_height=100,
        halign="middle", valign="middle",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None,
        fit_in=True
    ), (200, 100, 1)),

    (TestData(
        source_width=1000, source_height=250,
        target_width=500, target_height=200,
        halign="middle", valign="middle",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None,
        fit_in=True
    ), (500, 125, 1)),

    (TestData(
        source_width=200, source_height=250,
        target_width=500, target_height=400,
        halign="middle", valign="middle",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None,
        fit_in=True
    ), (200, 250, 0)),

    (TestData(
        source_width=800, source_height=400,
        target_width=100, target_height=400,
        halign="middle", valign="middle",
        focal_points=[],
        crop_left=None, crop_top=None, crop_right=None, crop_bottom=None,
        fit_in=True, adaptive=True
    ), (200, 100, 1))
]

########NEW FILE########
__FILENAME__ = transformer_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from pyvows import Vows, expect

from vows.transformer_test_data import TESTITEMS, FIT_IN_CROP_DATA, TestData, MockSyncDetector, MockErrorSyncDetector

from thumbor.transformer import Transformer


class EngineContext(Vows.Context):
    def _prepare_engine(self, topic, callback):
        context = topic[0].to_context()
        self.engine = context.modules.engine
        self.test_data = topic

        trans = Transformer(context)
        trans.transform(callback)


@Vows.assertion
def to_be_resized(topic):
    expect(topic.has_resized_properly()).to_be_true()


@Vows.assertion
def to_be_cropped(topic):
    expect(topic.has_cropped_properly()).to_be_true()


@Vows.batch
class TransformerVows(Vows.Context):

    class InvalidCrop(Vows.Context):
        @Vows.async_topic
        def topic(self, callback):
            data = TestData(
                source_width=800, source_height=600,
                target_width=800, target_height=600,
                halign="right", valign="top",
                focal_points=[],
                crop_left=200, crop_top=0, crop_right=100, crop_bottom=100
            )

            ctx = data.to_context()
            self.engine = ctx.modules.engine

            trans = Transformer(ctx)
            trans.transform(callback)

        def should_not_crop(self, topic):
            expect(self.engine.calls['crop']).to_be_empty()

    class MetaWithOrientation(Vows.Context):
        @Vows.async_topic
        def topic(self, callback):
            data = TestData(
                source_width=800, source_height=600,
                target_width=100, target_height=100,
                halign="right", valign="top",
                focal_points=[],
                crop_left=None, crop_top=None, crop_right=None, crop_bottom=None,
                meta=True
            )

            ctx = data.to_context()
            ctx.config.RESPECT_ORIENTATION = True
            self.engine = ctx.modules.engine

            trans = Transformer(ctx)
            trans.transform(callback)

        def should_work_well(self, topic):
            expect(topic).to_be_true()

    class Flip(Vows.Context):
        @Vows.async_topic
        def topic(self, callback):
            data = TestData(
                source_width=800, source_height=600,
                target_width=-800, target_height=-600,
                halign="right", valign="top",
                focal_points=[],
                crop_left=None, crop_top=None, crop_right=None, crop_bottom=None
            )

            ctx = data.to_context()
            self.engine = ctx.modules.engine

            trans = Transformer(ctx)
            trans.transform(callback)

        def should_do_horizontal_flip(self, topic):
            expect(self.engine.calls['horizontal_flip']).to_equal(1)

        def should_do_vertical_flip(self, topic):
            expect(self.engine.calls['vertical_flip']).to_equal(1)

    class ResizeCrop(Vows.Context):
        def topic(self):
            for item in TESTITEMS:
                yield item

        class AsyncResizeCrop(Vows.Context):
            @Vows.async_topic
            def topic(self, callback, topic):
                self.test_data = topic
                context = topic.to_context()
                trans = Transformer(context)
                trans.transform(callback)

            def should_resize_properly(self, topic):
                expect(self.test_data).to_be_resized()

            def should_crop_properly(self, topic):
                expect(self.test_data).to_be_cropped()

    class ResizeCropWithDetectors(Vows.Context):
        def topic(self):
            for item in TESTITEMS:
                yield item

        class AsyncResizeCrop(Vows.Context):
            @Vows.async_topic
            def topic(self, callback, topic):
                self.test_data = topic
                context = topic.to_context(detectors=[MockSyncDetector])
                trans = Transformer(context)
                trans.transform(callback)

            def should_resize_properly(self, topic):
                expect(self.test_data).to_be_resized()

            def should_crop_properly(self, topic):
                expect(self.test_data).to_be_cropped()

    class ResizeCropWithDetectorErrorsIgnored(Vows.Context):
        @Vows.async_topic
        def topic(self, callback):
            self.test_data = TestData(
                source_width=800, source_height=600,
                target_width=400, target_height=150,
                halign="center", valign="middle",
                focal_points=[],
                crop_left=0, crop_top=75, crop_right=800, crop_bottom=375
            )
            context = self.test_data.to_context(detectors=[MockErrorSyncDetector], ignore_detector_error=True)
            trans = Transformer(context)
            trans.transform(callback)

        def should_resize_properly(self, topic):
            expect(self.test_data).to_be_resized()

        def should_crop_properly(self, topic):
            expect(self.test_data).to_be_cropped()

    class ResizeCropWithoutDetectorErrorsIgnored(Vows.Context):
        @Vows.async_topic
        def topic(self, callback):
            self.test_data = TestData(
                source_width=800, source_height=600,
                target_width=400, target_height=150,
                halign="center", valign="middle",
                focal_points=[],
                crop_left=0, crop_top=75, crop_right=800, crop_bottom=375
            )
            context = self.test_data.to_context(detectors=[MockErrorSyncDetector], ignore_detector_error=False)
            trans = Transformer(context)
            trans.transform(callback)

        def should_resize_properly(self, topic):
            expect(self.test_data.engine.calls['resize']).to_length(0)

    class FitIn(Vows.Context):
        def topic(self, callback):
            for item in FIT_IN_CROP_DATA:
                yield item

        class AsyncFitIn(EngineContext):
            @Vows.async_topic
            def topic(self, callback, topic):
                self._prepare_engine(topic, callback)

            def should_not_have_crop(self, topic):
                expect(self.engine.calls['crop']).to_be_empty()

            def should_have_resize(self, topic):
                if not self.test_data[1][2]:
                    expect(self.engine.calls['resize']).to_be_empty()
                    return

                expect(self.engine.calls['resize']).not_to_be_empty()

            def should_have_proper_resize_calls(self, topic):
                length = self.test_data[1][2]
                expect(self.engine.calls['resize']).to_length(length)

            def should_have_proper_width(self, topic):
                if not self.test_data[1][2]:
                    return
                expect(self.engine.calls['resize'][0]['width']).to_equal(self.test_data[1][0])

            def should_have_proper_height(self, topic):
                if not self.test_data[1][2]:
                    return
                expect(self.engine.calls['resize'][0]['height']).to_equal(self.test_data[1][1])

########NEW FILE########
__FILENAME__ = translate_coordinates_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from pyvows import Vows, expect

from thumbor.handlers import BaseHandler

DATA = [
    dict(
        original_width=3000,
        original_height=2000,
        width=1200,
        height=800,
        crop_left=100,
        crop_top=100,
        crop_right=200,
        crop_bottom=200,
        expected_crop=(40, 40, 80, 80)
    )
]


@Vows.batch
class TranslateCoordinatesContext(Vows.Context):

    def topic(self):
        for coords in DATA:
            yield coords

    class CoordContext(Vows.Context):
        def topic(self, coords):
            return (BaseHandler.translate_crop_coordinates(
                original_width=coords['original_width'],
                original_height=coords['original_height'],
                width=coords['width'],
                height=coords['height'],
                crop_left=coords['crop_left'],
                crop_top=coords['crop_top'],
                crop_right=coords['crop_right'],
                crop_bottom=coords['crop_bottom']
            ), coords)

        def should_be_a_list_of_coords(self, topic):
            expect(topic[0]).to_be_instance_of(tuple)

        def should_translate_from_original_to_resized(self, topic):
            expect(topic[0]).to_equal(topic[1]['expected_crop'])

########NEW FILE########
__FILENAME__ = upload_api_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from os.path import abspath, join, dirname, exists
import re

from pyvows import Vows, expect
from tornado_pyvows.context import TornadoHTTPContext

from shutil import rmtree
from thumbor.app import ThumborServiceApp
from thumbor.config import Config
from thumbor.importer import Importer
from thumbor.context import Context

import urllib
import hashlib
import mimetypes


file_storage_root_path = '/tmp/thumbor-vows/storage'
file_path = ''


##
# Images used for tests :
#   - valid image      : JPEG 620x465, 69.88 KB
#   - too small image  : JPEG 20x20, 822 B
#   - too weight image : JPEG 300x400, 85.32 KB
##
def valid_image():
    path = abspath(join(dirname(__file__), 'fixtures/alabama1_ap620é.jpg'))
    with open(path, 'r') as stream:
        body = stream.read()
    return body


def too_small_image():
    path = abspath(join(dirname(__file__), 'crocodile.jpg'))
    with open(path, 'r') as stream:
        body = stream.read()
    return body


def too_weight_image():
    path = abspath(join(dirname(__file__), 'fixtures/conselheira_tutelar.jpg'))
    with open(path, 'r') as stream:
        body = stream.read()
    return body


if exists(file_storage_root_path):
    rmtree(file_storage_root_path)


##
# Path on file system (filestorage)
##
def path_on_filesystem(path):
    digest = hashlib.sha1(path).hexdigest()
    return join(file_storage_root_path.rstrip('/'), digest[:2] + '/' + digest[2:])


def encode_multipart_formdata(fields, files):
    BOUNDARY = 'thumborUploadFormBoundary'
    CRLF = '\r\n'
    L = []
    for key, value in fields.items():
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"' % key)
        L.append('')
        L.append(value)
    for (key, filename, value) in files:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
        L.append('Content-Type: %s' % mimetypes.guess_type(filename)[0] or 'application/octet-stream')
        L.append('')
        L.append(value)
    L.append('')
    L.append('')
    L.append('--' + BOUNDARY + '--')
    body = CRLF.join([str(item) for item in L])
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body


##
# Image Context defining post / put / delete / get
##
class ImageContext(TornadoHTTPContext):
    def __init__(self, *args, **kw):
        super(ImageContext, self).__init__(*args, **kw)
        self.ignore('get', 'post', 'put', 'delete', 'post_files')
        self.base_uri = "/image"

    def get(self, path, headers):
        return self.fetch(path,
                          method='GET',
                          body=urllib.urlencode({}, doseq=True),
                          headers=headers,
                          allow_nonstandard_methods=True)

    def post(self, path, headers, body):
        return self.fetch(path,
                          method='POST',
                          body=body,
                          headers=headers,
                          allow_nonstandard_methods=True)

    def put(self, path, headers, body):
        return self.fetch(path,
                          method='PUT',
                          body=body,
                          headers=headers,
                          allow_nonstandard_methods=True)

    def delete(self, path, headers):
        return self.fetch(path,
                          method='DELETE',
                          body=urllib.urlencode({}, doseq=True),
                          headers=headers,
                          allow_nonstandard_methods=True)

    def post_files(self, path, data={}, files=[]):
        multipart_data = encode_multipart_formdata(data, files)

        return self.fetch(path,
                          method='POST',
                          body=multipart_data[1],
                          headers={
                              'Content-Type': multipart_data[0]
                          },
                          allow_nonstandard_methods=True)


##
# Upload new images with POST method
##
@Vows.batch
class PostingANewImage(ImageContext):
    def get_app(self):
        self.default_filename = 'image'

        cfg = Config()
        cfg.UPLOAD_ENABLED = True
        cfg.UPLOAD_PHOTO_STORAGE = 'thumbor.storages.file_storage'
        cfg.FILE_STORAGE_ROOT_PATH = file_storage_root_path
        cfg.UPLOAD_DELETE_ALLOWED = False
        cfg.UPLOAD_PUT_ALLOWED = False
        cfg.UPLOAD_DEFAULT_FILENAME = self.default_filename

        importer = Importer(cfg)
        importer.import_modules()

        ctx = Context(None, cfg, importer)
        application = ThumborServiceApp(ctx)
        return application

    ##
    # Posting a new image with a filename through the REST API
    ##
    class WhenPostingANewImageWithAFilename(ImageContext):
        def topic(self):
            self.filename = 'new_image_with_a_filename.jpg'
            response = self.post(self.base_uri, {'Content-Type': 'image/jpeg', 'Slug': self.filename}, valid_image())
            return response

        class HttpStatusCode(ImageContext):
            def topic(self, response):
                return response.code

            def should_be_201_created(self, topic):
                expect(topic).to_equal(201)

        class HttpHeaders(ImageContext):
            def topic(self, response):
                return response.headers

            def should_contain_a_location_header_containing_the_filename(self, headers):
                expect(headers).to_include('Location')
                expect(headers['Location']).to_match(self.base_uri + r'/[^\/]{32}/' + self.filename)

        class Image(ImageContext):
            def topic(self, response):
                return re.compile(self.base_uri + r'/([^\/]{32})/' + self.filename).search(
                    response.headers['Location']).group(1)

            def should_be_store_at_right_path(self, topic):
                path = path_on_filesystem(topic)
                expect(exists(path)).to_be_true()

    ##
    # Posting a new image without filename through the REST API
    ##
    class WhenPostingANewImageWithoutFilename(ImageContext):
        def topic(self):
            self.filename = self.default_filename + '.jpg'
            response = self.post(self.base_uri, {'Content-Type': 'image/jpeg'}, valid_image())
            return response

        class HttpStatusCode(ImageContext):
            def topic(self, response):
                return response.code

            def should_be_201_created(self, topic):
                expect(topic).to_equal(201)

        class HttpHeaders(ImageContext):
            def topic(self, response):
                return response.headers

            def should_contain_a_location_header_containing_the_filename(self, headers):
                expect(headers).to_include('Location')
                expect(headers['Location']).to_match(self.base_uri + r'/[^\/]{32}/' + self.filename)

        class Image(ImageContext):
            def topic(self, response):
                return re.compile(self.base_uri + r'/([^\/]{32})/' + self.filename).search(
                    response.headers['Location']).group(1)

            def should_be_store_at_right_path(self, topic):
                path = path_on_filesystem(topic)
                expect(exists(path)).to_be_true()

    ##
    # Posting a new image through an HTML Form (multipart/form-data)
    ##
    class WhenPostingAValidImageThroughAnHtmlForm(ImageContext):
        def topic(self):
            self.filename = 'crocodile2.jpg'
            image = ('media', self.filename, valid_image())
            response = self.post_files(self.base_uri, {'Slug': 'another_filename.jpg'}, (image, ))
            return response

        class HttpStatusCode(ImageContext):
            def topic(self, response):
                return response.code

            def should_be_201_created(self, topic):
                expect(topic).to_equal(201)

        class HttpHeaders(ImageContext):
            def topic(self, response):
                return response.headers

            def should_contain_a_location_header_containing_the_filename(self, headers):
                expect(headers).to_include('Location')
                expect(headers['Location']).to_match(self.base_uri + r'/[^\/]{32}/' + self.filename)

        class Image(ImageContext):
            def topic(self, response):
                return re.compile(self.base_uri + r'/([^\/]{32})/' + self.filename).search(
                    response.headers['Location']).group(1)

            def should_be_store_at_right_path(self, topic):
                path = path_on_filesystem(topic)
                expect(exists(path)).to_be_true()


##
# Modifying an image
##
@Vows.batch
class ModifyingAnImage(ImageContext):

    def get_app(self):
        self.default_filename = 'image'

        cfg = Config()
        cfg.UPLOAD_ENABLED = True
        cfg.UPLOAD_PHOTO_STORAGE = 'thumbor.storages.file_storage'
        cfg.FILE_STORAGE_ROOT_PATH = file_storage_root_path
        cfg.UPLOAD_DELETE_ALLOWED = False
        cfg.UPLOAD_PUT_ALLOWED = True
        cfg.UPLOAD_DEFAULT_FILENAME = self.default_filename

        importer = Importer(cfg)
        importer.import_modules()

        ctx = Context(None, cfg, importer)
        application = ThumborServiceApp(ctx)
        return application

    ##
    # Modifying an image
    ##
    class WhenModifyingAnExistingImage(ImageContext):
        def topic(self):
            self.filename = self.default_filename + '.jpg'
            response = self.post(self.base_uri, {'Content-Type': 'image/jpeg'}, valid_image())
            self.location = response.headers['Location']
            response = self.put(self.location, {'Content-Type': 'image/jpeg'}, valid_image())
            return response

        class HttpStatusCode(ImageContext):
            def topic(self, response):
                return response.code

            def should_be_204_no_content(self, topic):
                expect(topic).to_equal(204)

        class Image(ImageContext):
            def topic(self, response):
                return re.compile(self.base_uri + r'/([^\/]{32})/' + self.filename).search(self.location).group(1)

            def should_be_store_at_right_path(self, topic):
                # Only file with uuid should be store
                id_should_exists = re.compile(self.base_uri + r'/([^\/]{32})/' + self.filename).search(self.location).group(1)
                expect(exists(path_on_filesystem(id_should_exists))).to_be_true()

                id_shouldnt_exists = re.compile(self.base_uri + r'/(.*)').search(self.location).group(1)
                expect(exists(path_on_filesystem(id_shouldnt_exists))).to_be_false()


##
# Delete image with DELETE method
##
@Vows.batch
class DeletingAnImage(ImageContext):
    def get_app(self):
        self.default_filename = 'image'

        cfg = Config()
        cfg.UPLOAD_ENABLED = True
        cfg.UPLOAD_PHOTO_STORAGE = 'thumbor.storages.file_storage'
        cfg.FILE_STORAGE_ROOT_PATH = file_storage_root_path
        cfg.UPLOAD_DELETE_ALLOWED = True
        cfg.UPLOAD_PUT_ALLOWED = False
        cfg.UPLOAD_DEFAULT_FILENAME = self.default_filename

        importer = Importer(cfg)
        importer.import_modules()

        ctx = Context(None, cfg, importer)
        application = ThumborServiceApp(ctx)
        return application

    ##
    # Deleting  an existing image
    ##
    class WhenDeletingAnExistingImage(ImageContext):
        def topic(self):
            self.filename = self.default_filename + '.jpg'
            response = self.post(self.base_uri, {'Content-Type': 'image/jpeg'}, valid_image())
            self.location = response.headers['Location']
            response = self.delete(self.location, {})
            return response

        class HttpStatusCode(ImageContext):
            def topic(self, response):
                return response.code

            def should_be_204_no_content(self, topic):
                expect(topic).to_equal(204)

        class Image(ImageContext):
            def topic(self, response):
                return response

            def should_be_deleted_from_storage(self, topic):
                # Only file with uuid should be store
                id_shouldnt_exists = re.compile(self.base_uri + r'/([^\/]{32})/' + self.filename).search(self.location).group(1)
                expect(exists(path_on_filesystem(id_shouldnt_exists))).to_be_false()

    ##
    # Deleting  an unknown image
    ##
    class WhenDeletingAnUnknownImage(ImageContext):
        def topic(self):
            self.uri = self.base_uri + '/an/unknown/image'
            response = self.delete(self.uri, {})
            return response

        class HttpStatusCode(ImageContext):
            def topic(self, response):
                return response.code

            def should_be_404_not_found(self, topic):
                expect(topic).to_equal(404)


##
# Retrieving image
##
@Vows.batch
class RetrievingAnImage(ImageContext):
    def get_app(self):
        self.default_filename = 'image'

        cfg = Config()
        cfg.UPLOAD_ENABLED = True
        cfg.UPLOAD_PHOTO_STORAGE = 'thumbor.storages.file_storage'
        cfg.FILE_STORAGE_ROOT_PATH = file_storage_root_path
        cfg.UPLOAD_DELETE_ALLOWED = True
        cfg.UPLOAD_PUT_ALLOWED = False
        cfg.UPLOAD_DEFAULT_FILENAME = self.default_filename

        importer = Importer(cfg)
        importer.import_modules()

        ctx = Context(None, cfg, importer)
        application = ThumborServiceApp(ctx)
        return application

    class WhenRetrievingAnExistingImage(ImageContext):
        def topic(self):
            response = self.post(self.base_uri, {'Content-Type': 'image/jpeg'}, valid_image())
            self.location = response.headers['Location']
            response = self.get(self.location, {'Accept': 'image/jpeg'})
            return response

        class HttpStatusCode(ImageContext):
            def topic(self, response):
                return response.code

            def should_be_200_ok(self, topic):
                expect(topic).to_equal(200)

        class Body(ImageContext):
            def topic(self, response):
                return response.body

            def should_be_the_expected_image(self, topic):
                expect(topic).to_equal(valid_image())

    class WhenRetrievingAnUnknownImage(ImageContext):
        def topic(self):
            self.uri = self.base_uri + '/an/unknown/image'
            response = self.get(self.uri, {'Accept': 'image/jpeg'})
            return response

        class HttpStatusCode(ImageContext):
            def topic(self, response):
                return response.code

            def should_be_404_not_found(self, topic):
                expect(topic).to_equal(404)


##
# Validation :
#   - Invalid image
#   - Size constraints
#   - Weight constraints
##
@Vows.batch
class Validation(ImageContext):

    def get_app(self):
        self.default_filename = 'image'

        cfg = Config()
        cfg.UPLOAD_ENABLED = True
        cfg.UPLOAD_PUT_ALLOWED = True
        cfg.UPLOAD_PHOTO_STORAGE = 'thumbor.storages.file_storage'
        cfg.FILE_STORAGE_ROOT_PATH = file_storage_root_path
        cfg.UPLOAD_DEFAULT_FILENAME = self.default_filename
        cfg.MIN_WIDTH = 40
        cfg.MIN_HEIGHT = 40
        cfg.UPLOAD_MAX_SIZE = 72000

        importer = Importer(cfg)
        importer.import_modules()
        ctx = Context(None, cfg, importer)
        application = ThumborServiceApp(ctx)
        return application

    ##
    # Invalid Image
    ##
    class InvalidImage(ImageContext):

        ##
        # Posting an invalid image
        ##
        class WhenPostingAnInvalidImage(ImageContext):
            def topic(self):
                response = self.post(self.base_uri, {'Content-Type': 'image/jpeg'}, 'invalid image')
                return response

            class HttpStatusCode(ImageContext):
                def topic(self, response):
                    return response.code

                def should_be_415_media_type_not_supported(self, topic):
                    expect(topic).to_equal(415)

        ##
        # Posting an invalid image through an html form (multipart/form-data)
        ##
        class WhenPostingAnInvalidImageThroughAnHtmlForm(ImageContext):
            def topic(self):
                image = ('media', u'crocodile9999.jpg', 'invalid image')
                response = self.post_files(self.base_uri, {}, (image, ))
                return response

            class HttpStatusCode(ImageContext):
                def topic(self, response):
                    return response.code

                def should_be_415_media_type_not_supported(self, topic):
                        expect(topic).to_equal(415)

        ##
        # Modifying an existing image by an invalid image
        ##
        class WhenModifyingAnExistingImageByAnInvalidImage(ImageContext):
            def topic(self):
                response = self.post(self.base_uri, {'Content-Type': 'image/jpeg'}, valid_image())
                self.location = response.headers['Location']
                response = self.put(self.location, {'Content-Type': 'image/jpeg'}, 'invalid image')
                return response

            class HttpStatusCode(ImageContext):
                def topic(self, response):
                    return response.code

                def should_be_415_media_type_not_supported(self, topic):
                    expect(topic).to_equal(415)

    ##
    # Size constraints
    ##
    class ImageSizeConstraints(ImageContext):

        ##
        # Posting a too small image
        ##
        class WhenPostingATooSmallImage(ImageContext):
            def topic(self):
                response = self.post(self.base_uri, {'Content-Type': 'image/jpeg'}, too_small_image())
                return response

            class HttpStatusCode(ImageContext):
                def topic(self, response):
                    return response.code

                def should_be_412_precondition_failed(self, topic):
                    expect(topic).to_equal(412)

        ##
        # Posting a too small image through an html form (multipart/form-data)
        ##
        class WhenPostingTooSmallImageThroughAnHtmlForm(ImageContext):
            def topic(self):
                image = ('media', u'crocodile9999.jpg', too_small_image())
                response = self.post_files(self.base_uri, {}, (image, ))
                return (response.code, response.body)

            def should_be_an_error(self, topic):
                expect(topic[0]).to_equal(412)

        ##
        # Modifying an existing image by a too small image
        ##
        class WhenModifyingAnExistingImageByATooSmallImage(ImageContext):
            def topic(self):
                response = self.post(self.base_uri, {'Content-Type': 'image/jpeg'}, valid_image())
                self.location = response.headers['Location']
                response = self.put(self.location, {'Content-Type': 'image/jpeg'}, too_small_image())
                return response

            class HttpStatusCode(ImageContext):
                def topic(self, response):
                    return response.code

                def should_be_412_precondition_failed(self, topic):
                    expect(topic).to_equal(412)

    ##
    # Weight constraints
    ##
    class WeightConstraints(ImageContext):

        ##
        # Posting a too weight image
        ##
        class WhenPostingATooWeightImage(ImageContext):
            def topic(self):
                response = self.post(self.base_uri, {'Content-Type': 'image/jpeg'}, too_weight_image())
                return response

            class HttpStatusCode(ImageContext):
                def topic(self, response):
                    return response.code

                def should_be_412_precondition_failed(self, topic):
                    expect(topic).to_equal(412)

        ##
        # Posting a too weight image through an html form (multipart/form-data)
        ##
        class WhenPostingATooWeightImageThroughAnHtmlForm(ImageContext):
            def topic(self):
                image = ('media', u'oversized9999.jpg', too_weight_image())
                response = self.post_files(self.base_uri, {}, (image, ))
                return (response.code, response.body)

            def should_be_an_error(self, topic):
                expect(topic[0]).to_equal(412)

        ##
        # Modifying an existing image by a too weight image
        ##
        class WhenModifyingAnExistingImageByATooWeightImage(ImageContext):
            def topic(self):
                response = self.post(self.base_uri, {'Content-Type': 'image/jpeg'}, valid_image())
                self.location = response.headers['Location']
                response = self.put(self.location, {'Content-Type': 'image/jpeg'}, too_weight_image())
                return response

            class HttpStatusCode(ImageContext):
                def topic(self, response):
                    return response.code

                def should_be_412_precondition_failed(self, topic):
                    expect(topic).to_equal(412)

########NEW FILE########
__FILENAME__ = upload_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import mimetypes
import urllib
import hashlib
from os.path import abspath, join, dirname, exists
from shutil import rmtree

from pyvows import Vows, expect
from tornado_pyvows.context import TornadoHTTPContext

from thumbor.app import ThumborServiceApp
from thumbor.config import Config
from thumbor.importer import Importer
from thumbor.context import Context

file_storage_root_path = '/tmp/thumbor-vows/storage'
crocodile_file_path = abspath(join(dirname(__file__), 'crocodile.jpg'))
oversized_file_path = abspath(join(dirname(__file__), 'fixtures/image.jpg'))

with open(crocodile_file_path, 'r') as croc:
    croc_content = croc.read()

if exists(file_storage_root_path):
    rmtree(file_storage_root_path)


def get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'


# adapted from: http://code.activestate.com/recipes/146306/
def encode_multipart_formdata(fields, files):
    """
    fields is a sequence of (name, value) elements for regular form
fields.
    files is a sequence of (name, filename, value) elements for data
to be uploaded as files
    Return (content_type, body) ready for httplib.HTTP instance
    """
    BOUNDARY = 'thumborUploadFormBoundary'
    CRLF = '\r\n'
    L = []
    for key, value in fields.items():
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"' % key)
        L.append('')
        L.append(value)
    for (key, filename, value) in files:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
        L.append('Content-Type: %s' % get_content_type(filename))
        L.append('')
        L.append(value)
    L.append('')
    L.append('')
    L.append('--' + BOUNDARY + '--')

    body = CRLF.join([str(item) for item in L])

    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY

    return content_type, body


def path_on_filesystem(path):
    digest = hashlib.sha1(path).hexdigest()
    return join(file_storage_root_path.rstrip('/'), digest[:2] + '/' + digest[2:])


class BaseContext(TornadoHTTPContext):
    def __init__(self, *args, **kw):
        super(BaseContext, self).__init__(*args, **kw)
        self.ignore('post_files', 'delete')

    def delete(self, path, data={}):
        return self.fetch(path, method="DELETE", body=urllib.urlencode(data, doseq=True), allow_nonstandard_methods=True)

    def post_files(self, method, path, data={}, files=[]):
        multipart_data = encode_multipart_formdata(data, files)

        return self.fetch(
            path, method=method.upper(), body=multipart_data[1],
            headers={'Content-Type': multipart_data[0]}, allow_nonstandard_methods=True)


@Vows.batch
class Upload(BaseContext):
    def get_app(self):
        cfg = Config()
        cfg.UPLOAD_ENABLED = True
        cfg.UPLOAD_PHOTO_STORAGE = 'thumbor.storages.file_storage'
        cfg.FILE_STORAGE_ROOT_PATH = file_storage_root_path
        cfg.UPLOAD_DELETE_ALLOWED = True
        cfg.UPLOAD_PUT_ALLOWED = True

        importer = Importer(cfg)
        importer.import_modules()
        ctx = Context(None, cfg, importer)
        application = ThumborServiceApp(ctx)
        return application

    class WhenPutting(BaseContext):
        def topic(self):
            image = ('media', u'crocodile.jpg', croc_content)
            response = self.post_files('put', '/upload', {}, (image, ))
            return response

        class StatusCode(TornadoHTTPContext):
            def topic(self, response):
                return response.code

            def should_not_be_an_error(self, topic):
                expect(topic).to_equal(201)

        class Body(TornadoHTTPContext):
            def topic(self, response):
                return response.body

            def should_be_in_right_path(self, topic):
                path = path_on_filesystem('crocodile.jpg')
                expect(topic).to_equal('crocodile.jpg')
                expect(exists(path)).to_be_true()

        class Headers(TornadoHTTPContext):
            def topic(self, response):
                return response.headers

            def should_set_correct_location(self, headers):
                expect(headers).to_include('Location')
                expect(headers['Location']).to_equal('crocodile.jpg')

    class WhenPuttingInvalidImage(BaseContext):
        def topic(self):
            image = ('media', u'crocodile9999.jpg', 'toto')
            response = self.post_files('put', '/upload', {}, (image, ))
            return (response.code, response.body)

        def should_be_an_error(self, topic):
            expect(topic[0]).to_equal(412)

    class WhenPostingInvalidImage(BaseContext):
        def topic(self):
            image = ('media', u'crocodile9999.jpg', 'toto')
            response = self.post_files('post', '/upload', {}, (image, ))
            return (response.code, response.body)

        def should_be_an_error(self, topic):
            expect(topic[0]).to_equal(412)

    class WhenPosting(BaseContext):
        def topic(self):
            image = ('media', u'crocodile2.jpg', croc_content)

            response = self.post_files('post', '/upload', {}, (image, ))

            return response

        class StatusCode(TornadoHTTPContext):
            def topic(self, response):
                return response.code

            def should_not_be_an_error(self, topic):
                expect(topic).to_equal(201)

        class Body(TornadoHTTPContext):
            def topic(self, response):
                return response.body

            def should_be_in_right_path(self, topic):
                path = path_on_filesystem('crocodile2.jpg')
                expect(topic).to_equal('crocodile2.jpg')
                expect(exists(path)).to_be_true()

        class Headers(TornadoHTTPContext):
            def topic(self, response):
                return response.headers

            def should_set_correct_location(self, headers):
                expect(headers).to_include('Location')
                expect(headers['Location']).to_equal('crocodile2.jpg')

            class WhenRePosting(BaseContext):
                def topic(self):
                    image = ('media', u'crocodile2.jpg', croc_content)
                    response = self.post_files('post', '/upload', {}, (image, ))
                    return (response.code, response.body)

                class StatusCode(TornadoHTTPContext):
                    def topic(self, response):
                        return response[0]

                    def should_be_an_error(self, topic):
                        expect(topic).to_equal(409)

    class WhenDeleting(BaseContext):
        def topic(self):
            image = ('media', u'crocodile-delete.jpg', croc_content)

            response = self.post_files('post', '/upload', {}, (image, ))
            response = self.delete('/upload', {'file_path': 'crocodile-delete.jpg'})
            return (response.code, response.body)

        class StatusCode(TornadoHTTPContext):
            def topic(self, response):
                return response[0]

            def should_not_be_an_error_and_file_should_not_exist(self, topic):
                path = path_on_filesystem('crocodile-delete.jpg')
                expect(topic).to_equal(200)
                expect(exists(path)).to_be_false()

            class DeletingAgainDoesNothing(BaseContext):
                def topic(self):
                    response = self.delete('/upload', {'file_path': 'crocodile-delete.jpg'})
                    return (response.code, response.body)

                class StatusCode(TornadoHTTPContext):
                    def topic(self, response):
                        return response[0]

                    def should_not_be_an_error_and_file_should_not_exist(self, topic):
                        expect(topic).to_equal(200)

        class DeletingWithInvalidPathDoesNothing(BaseContext):
            def topic(self):
                response = self.delete('/upload', {'file_path': 'crocodile5.jpg'})
                return (response.code, response.body)

            class StatusCode(TornadoHTTPContext):
                def topic(self, response):
                    return response[0]

                def should_not_be_an_error_and_file_should_not_exist(self, topic):
                    expect(topic).to_equal(200)


@Vows.batch
class UploadWithoutDeletingAllowed(BaseContext):
    def get_app(self):
        cfg = Config()
        cfg.UPLOAD_ENABLED = True
        cfg.UPLOAD_PHOTO_STORAGE = 'thumbor.storages.file_storage'
        cfg.FILE_STORAGE_ROOT_PATH = file_storage_root_path
        cfg.UPLOAD_DELETE_ALLOWED = False

        importer = Importer(cfg)
        importer.import_modules()
        ctx = Context(None, cfg, importer)
        application = ThumborServiceApp(ctx)
        return application

    class WhenPosting(BaseContext):
        def topic(self):
            image = ('media', u'crocodile3.jpg', croc_content)
            response = self.post_files('post', '/upload', {}, (image, ))
            return (response.code, response.body)

        class ThenDeleting(BaseContext):
            def topic(self):
                response = self.delete('/upload', {'file_path': 'crocodile3.jpg'})
                return (response.code, response.body)

            class StatusCode(TornadoHTTPContext):
                def topic(self, response):
                    return response[0]

                def should_be_an_error_and_file_should_not_exist(self, topic):
                    path = path_on_filesystem('crocodile3.jpg')
                    expect(topic).to_equal(405)
                    expect(exists(path)).to_be_true()


@Vows.batch
class UploadWithMinWidthAndHeight(BaseContext):
    def get_app(self):
        cfg = Config()
        cfg.UPLOAD_ENABLED = True
        cfg.UPLOAD_PUT_ALLOWED = True
        cfg.UPLOAD_PHOTO_STORAGE = 'thumbor.storages.file_storage'
        cfg.FILE_STORAGE_ROOT_PATH = file_storage_root_path
        cfg.MIN_WIDTH = 40
        cfg.MIN_HEIGHT = 40

        importer = Importer(cfg)
        importer.import_modules()
        ctx = Context(None, cfg, importer)
        application = ThumborServiceApp(ctx)
        return application

    class WhenPuttingTooSmallImage(BaseContext):
        def topic(self):
            image = ('media', u'crocodile9999.jpg', croc_content)
            response = self.post_files('put', '/upload', {}, (image, ))
            return (response.code, response.body)

        def should_be_an_error(self, topic):
            expect(topic[0]).to_equal(412)

    class WhenPostingTooSmallImage(BaseContext):
        def topic(self):
            image = ('media', u'crocodile9999.jpg', croc_content)
            response = self.post_files('post', '/upload', {}, (image, ))
            return (response.code, response.body)

        def should_be_an_error(self, topic):
            expect(topic[0]).to_equal(412)


@Vows.batch
class UploadWithMaxSize(BaseContext):
    def get_app(self):
        cfg = Config()
        cfg.UPLOAD_ENABLED = True
        cfg.UPLOAD_PUT_ALLOWED = True
        cfg.UPLOAD_PHOTO_STORAGE = 'thumbor.storages.file_storage'
        cfg.FILE_STORAGE_ROOT_PATH = file_storage_root_path
        cfg.UPLOAD_MAX_SIZE = 40000

        importer = Importer(cfg)
        importer.import_modules()
        ctx = Context(None, cfg, importer)
        application = ThumborServiceApp(ctx)
        return application

    class WhenPuttingTooBigFile(BaseContext):
        def topic(self):
            with open(oversized_file_path, 'r') as croc:
                image = ('media', u'oversized9999.jpg', croc.read())
            response = self.post_files('put', '/upload', {}, (image, ))
            return (response.code, response.body)

        def should_be_an_error(self, topic):
            expect(topic[0]).to_equal(412)

    class WhenPostingTooBigFile(BaseContext):
        def topic(self):
            with open(oversized_file_path, 'r') as croc:
                image = ('media', u'oversized9999.jpg', croc.read())
            response = self.post_files('post', '/upload', {}, (image, ))
            return (response.code, response.body)

        def should_be_an_error(self, topic):
            expect(topic[0]).to_equal(412)

########NEW FILE########
__FILENAME__ = url_composer_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from pyvows import Vows, expect

from thumbor.url_composer import main


@Vows.batch
class AppVows(Vows.Context):

    class ErrorsWhenNoArguments(Vows.Context):
        def topic(self):
            return main([])

        def should_be_null(self, topic):
            expect(topic).to_be_null()

    class WhenProperArguments(Vows.Context):
        def topic(self):
            return main([
                "-k", "MY-SECURITY-KEY",
                "-w", "200",
                "-e", "300",
                "myserver.com/myimg.jpg"
            ])

        def should_be_proper_url(self, topic):
            expect(topic).to_equal('/G_dykuWBGyEil5JnNh9cBke0Ajo=/200x300/myserver.com/myimg.jpg')

    class WhenOldFormat(Vows.Context):
        def topic(self):
            return main([
                "-k", "MY-SECURITY-KEY",
                "-w", "200",
                "-e", "300",
                "--old-format",
                "myserver.com/myimg.jpg"
            ])

        def should_be_proper_url(self, topic):
            expect(topic).to_equal('/6LSog0KmY0NQg8GK4Tsti0FAR9emvaF4xfyLY3FUmOI0HVcqF8HxibsAjVCbxFfl/myserver.com/myimg.jpg')

########NEW FILE########
__FILENAME__ = url_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from pyvows import Vows, expect

from thumbor.url import Url


def ctx(**kw):
    class Context(Vows.Context):
        def topic(self):
            return Url.generate_options(**kw)

    return Context


@Vows.batch
class UrlVows(Vows.Context):

    class UrlGeneration(Vows.Context):

        class Default(ctx()):

            def should_return_empty_url(self, topic):
                expect(topic).to_be_empty()

        class Minimum(ctx(width=300, height=200)):

            def should_return_proper_url(self, topic):
                expect(topic).to_equal('300x200')

        class Smart(ctx(width=300, height=200, smart=True)):

            def should_return_proper_url(self, topic):
                expect(topic).to_equal('300x200/smart')

        class Debug(ctx(debug=True, smart=True)):

            def should_return_proper_url(self, topic):
                expect(topic).to_equal('debug/smart')

        class Alignments(ctx(halign='left', valign='top')):

            def should_return_proper_url(self, topic):
                expect(topic).to_equal('left/top')

        class Flipping(ctx(width=300, height=200, smart=True, horizontal_flip=True, vertical_flip=True)):

            def should_return_proper_url(self, topic):
                expect(topic).to_equal('-300x-200/smart')

        class Crop(ctx(width=300, height=200, crop_left=10, crop_top=11, crop_right=12, crop_bottom=13)):

            def should_return_proper_url(self, topic):
                expect(topic).to_equal('10x11:12x13/300x200')

        class Meta(ctx(meta=True)):

            def should_return_proper_url(self, topic):
                expect(topic).to_equal('meta')

        class FitIn(ctx(fit_in=True)):

            def should_return_proper_url(self, topic):
                expect(topic).to_equal('fit-in')

        class Filters(ctx(filters='brightness(-10):contrast(5)')):

            def should_return_proper_url(self, topic):
                expect(topic).to_equal('filters:brightness(-10):contrast(5)')

        class Adaptive(ctx(fit_in=True, adaptive=True)):

            def should_return_proper_url(self, topic):
                expect(topic).to_equal('adaptive-fit-in')

        class Complete(ctx(
                width=300, height=200, smart=True, fit_in=True, meta=True, horizontal_flip=True,
                vertical_flip=True, crop_left=10, crop_top=11, crop_right=12, crop_bottom=13,
                filters="a(10):b(-10)")):

            def should_return_proper_url(self, topic):
                expect(topic).to_equal('meta/10x11:12x13/fit-in/-300x-200/smart/filters:a(10):b(-10)')

    class Regex(Vows.Context):
        def topic(self):
            return Url.regex()

        def should_contain_unsafe_or_hash(self, topic):
            expect(topic).to_include('(?:(?:(?P<unsafe>unsafe)|(?P<hash>[^/]{28,}?))/)?')

        def should_contain_meta(self, topic):
            expect(topic).to_include('(?:(?P<meta>meta)/)?')

        def should_contain_crop(self, topic):
            expect(topic).to_include('(?:(?P<crop_left>\d+)x(?P<crop_top>\d+):(?P<crop_right>\d+)x(?P<crop_bottom>\d+)/)?')

        def should_contain_fit_in(self, topic):
            expect(topic).to_include('(?:(?P<adaptive>adaptive-)?(?P<fit_in>fit-in)/)?')

        def should_contain_dimensions(self, topic):
            expect(topic).to_include(
                '(?:(?P<horizontal_flip>-)?(?P<width>(?:\d+|orig))?x(?P<vertical_flip>-)?(?P<height>(?:\d+|orig))?/)?')

        def should_contain_halign(self, topic):
            expect(topic).to_include('(?:(?P<halign>left|right|center)/)?')

        def should_contain_valign(self, topic):
            expect(topic).to_include('(?:(?P<valign>top|bottom|middle)/)?')

        def should_contain_smart(self, topic):
            expect(topic).to_include('(?:(?P<smart>smart)/)?')

        def should_contain_filters(self, topic):
            expect(topic).to_include('(?:filters:(?P<filters>.+?\))/)?')

        def should_contain_image(self, topic):
            expect(topic).to_include('(?P<image>.+)')

        class WithOldFormat(Vows.Context):
            def topic(self):
                return Url.regex(old_format=True)

            def should_not_include_image(self, topic):
                expect(topic).not_to_include('(?:(?P<hash>[^/]{28,}?)/)?')

    class Parse(Vows.Context):
        class WithoutInitialSlash(Vows.Context):
            def topic(self):
                return Url.parse_decrypted('meta/10x11:12x13/-300x-200/left/top/smart/filters:some_filter()/img')

            def should_not_be_null(self, topic):
                expect(topic).not_to_be_null()

        class WithoutResult(Vows.Context):
            def topic(self):
                return Url.parse_decrypted("some fake url")

            def should_be_null(self, topic):
                expect(topic['image']).to_equal("some fake url")

        class WithoutImage(Vows.Context):
            def topic(self):
                return Url.parse_decrypted('/meta/10x11:12x13/fit-in/-300x-200/left/top/smart/filters:some_filter()/img')

            def should_have_meta(self, topic):
                expect(topic['meta']).to_be_true()

            def should_have_crop_left_of_10(self, topic):
                expect(topic['crop']['left']).to_equal(10)

            def should_have_crop_top_of_11(self, topic):
                expect(topic['crop']['top']).to_equal(11)

            def should_have_crop_right_of_12(self, topic):
                expect(topic['crop']['right']).to_equal(12)

            def should_have_crop_bottom_of_13(self, topic):
                expect(topic['crop']['bottom']).to_equal(13)

            def should_have_width_of_300(self, topic):
                expect(topic['width']).to_equal(300)

            def should_have_height_of_200(self, topic):
                expect(topic['height']).to_equal(200)

            def should_have_horizontal_flip(self, topic):
                expect(topic['horizontal_flip']).to_be_true()

            def should_have_vertical_flip(self, topic):
                expect(topic['vertical_flip']).to_be_true()

            def should_have_halign_of_left(self, topic):
                expect(topic['halign']).to_equal('left')

            def should_have_valign_of_top(self, topic):
                expect(topic['valign']).to_equal('top')

            def should_have_smart(self, topic):
                expect(topic['smart']).to_be_true()

            def should_have_fit_in(self, topic):
                expect(topic['fit_in']).to_be_true()

            def should_have_filters(self, topic):
                expect(topic['filters']).to_equal('some_filter()')

        class WithImage(Vows.Context):
            def topic(self):
                image_url = 's.glbimg.com/es/ge/f/original/2011/03/29/orlandosilva_60.jpg'

                return Url.parse_decrypted('/meta/10x11:12x13/-300x-200/left/top/smart/%s' % image_url)

            def should_have_image(self, topic):
                expect(topic).to_include('image')

            def should_have_image_like_url(self, topic):
                image_url = 's.glbimg.com/es/ge/f/original/2011/03/29/orlandosilva_60.jpg'
                expect(topic['image']).to_equal(image_url)

        class WithUrlInFilter(Vows.Context):
            def topic(self):
                return Url.parse_decrypted(
                    '/filters:watermark(s.glbimg.com/es/ge/f/original/2011/03/29/orlandosilva_60.jpg,0,0,0)/img')

            def should_have_image(self, topic):
                expect(topic['image']).to_equal('img')

            def should_have_filters(self, topic):
                expect(topic['filters']).to_equal('watermark(s.glbimg.com/es/ge/f/original/2011/03/29/orlandosilva_60.jpg,0,0,0)')

        class WithMultipleFilters(Vows.Context):
            def topic(self):
                return Url.parse_decrypted(
                    '/filters:watermark(s.glbimg.com/es/ge/f/original/2011/03/29/orlandosilva_60.jpg,0,0,0):brightness(-50):grayscale()/img')

            def should_have_image(self, topic):
                expect(topic['image']).to_equal('img')

            def should_have_filters(self, topic):
                expect(topic['filters']).to_equal('watermark(s.glbimg.com/es/ge/f/original/2011/03/29/orlandosilva_60.jpg,0,0,0):brightness(-50):grayscale()')

        class WithThumborOfThumbor(Vows.Context):
            def topic(self):
                return Url.parse_decrypted(
                    '/90x100/my.image.path/unsafe/filters:watermark(s.glbimg.com/some/image.jpg,0,0,0)/some.domain/img/path/img.jpg')

            def should_have_image(self, topic):
                expect(topic['image']).to_equal('my.image.path/unsafe/filters:watermark(s.glbimg.com/some/image.jpg,0,0,0)/some.domain/img/path/img.jpg')

            def should_have_size(self, topic):
                expect(topic['width']).to_equal(90)
                expect(topic['height']).to_equal(100)

        class WithThumborOfThumborWithFilters(Vows.Context):
            def topic(self):
                return Url.parse_decrypted(
                    '/90x100/filters:brightness(-50):contrast(20)/my.image.path/unsafe/filters:watermark(s.glbimg.com/some/image.jpg,0,0,0)/some.domain/img/path/img.jpg')

            def should_have_image(self, topic):
                expect(topic['image']).to_equal('my.image.path/unsafe/filters:watermark(s.glbimg.com/some/image.jpg,0,0,0)/some.domain/img/path/img.jpg')

            def should_have_filters(self, topic):
                expect(topic['filters']).to_equal('brightness(-50):contrast(20)')

            def should_have_size(self, topic):
                expect(topic['width']).to_equal(90)
                expect(topic['height']).to_equal(100)

########NEW FILE########
__FILENAME__ = util_vows
#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/globocom/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

import logging

from pyvows import Vows, expect

from thumbor.utils import logger, real_import


@Vows.batch
class UtilVows(Vows.Context):

    class Logger(Vows.Context):
        def topic(self):
            return logger

        def should_be_instance_of_python_logger(self, topic):
            expect(topic).to_be_instance_of(logging.Logger)

        def should_not_be_null(self, topic):
            expect(topic).not_to_be_null()

        def should_not_be_an_error(self, topic):
            expect(topic).not_to_be_an_error()

    class RealImport(Vows.Context):

        class WhenRegularModules(Vows.Context):
            def topic(self):
                return real_import('pyvows')

            def should_have_expect(self, topic):
                expect(topic.expect).not_to_be_null()

        class WhenUsingSubmodules(Vows.Context):
            def topic(self):
                return real_import('thumbor.utils')

            def should_not_be_an_error(self, topic):
                expect(topic).not_to_be_an_error()

            def should_not_be_null(self, topic):
                expect(topic).not_to_be_null()

            def should_return_module(self, topic):
                expect(topic.logger).not_to_be_null()

########NEW FILE########
