__FILENAME__ = app
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals
import os
import sys
import logging
import datetime
import hashlib
import flask
from flask import Flask, render_template, request, send_file
from helpers.fakeimg import FakeImg
from helpers.converters import ColorConverter, ImgSizeConverter, AlphaConverter
try:
    from raven.contrib.flask import Sentry
except ImportError:
    pass


app = Flask(__name__)
# Custom converter for matching hexadecimal colors
app.url_map.converters['c'] = ColorConverter
# Custom converter for not having an image > 4000px
app.url_map.converters['i'] = ImgSizeConverter
app.url_map.converters['a'] = AlphaConverter
# Generate Last-Modified timestamp
launch_date = datetime.datetime.now()


@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@app.route('/<i:width>/')
@app.route('/<i:width>/<c:bgd>/')
@app.route('/<i:width>/<c:bgd>,<a:alphabgd>/')
@app.route('/<i:width>/<c:bgd>/<c:fgd>/')
@app.route('/<i:width>/<c:bgd>,<a:alphabgd>/<c:fgd>/')
@app.route('/<i:width>/<c:bgd>/<c:fgd>,<a:alphafgd>/')
@app.route('/<i:width>/<c:bgd>,<a:alphabgd>/<c:fgd>,<a:alphafgd>/')
@app.route('/<i:width>x<i:height>/')
@app.route('/<i:width>x<i:height>/<c:bgd>/')
@app.route('/<i:width>x<i:height>/<c:bgd>,<a:alphabgd>/')
@app.route('/<i:width>x<i:height>/<c:bgd>/<c:fgd>/')
@app.route('/<i:width>x<i:height>/<c:bgd>,<a:alphabgd>/<c:fgd>/')
@app.route('/<i:width>x<i:height>/<c:bgd>/<c:fgd>,<a:alphafgd>/')
@app.route('/<i:width>x<i:height>/<c:bgd>,<a:alphabgd>/<c:fgd>,<a:alphafgd>/')
def placeholder(width, height=None,
                bgd="cccccc", fgd="909090",
                alphabgd=255, alphafgd=255):
    """This endpoint generates the placeholder itself, based on arguments.
    If the height is missing, just make the image square.
    """
    # processing image
    args = {
        "width": width,
        "height": height or width,
        "background_color": bgd,
        "alpha_background": alphabgd,
        "foreground_color": fgd,
        "alpha_foreground": alphafgd,
        "text": request.args.get('text'),
        "font_name": request.args.get('font'),
        "font_size": request.args.get('font_size'),
        "retina": "retina" in request.args
    }
    image = FakeImg(**args)
    # return static file
    return send_file(image.raw, mimetype='image/png', add_etags=False)


# caching stuff
@app.before_request
def handle_cache():
    """if resource is the same, return 304"""
    # we test Etag first, as it's a strong validator
    url_bytes = request.url.encode('utf-8')
    etag = hashlib.sha1(url_bytes).hexdigest()
    if request.headers.get('If-None-Match') == etag:
        return flask.Response(status=304)
    # then we try with Last-Modified
    if request.headers.get('If-Modified-Since') == str(launch_date):
        return flask.Response(status=304)


@app.after_request
def add_header(response):
    """Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 hours. Should be served by
    Varnish servers.
    """
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'public,max-age=36000'
    response.headers['Last-Modified'] = launch_date
    url_bytes = request.url.encode('utf-8')
    response.headers['Etag'] = hashlib.sha1(url_bytes).hexdigest()
    return response


@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon.ico')


@app.route('/<file_name>.txt')
def send_text_file(file_name):
    """Send your static text file."""
    file_dot_text = '{0}.txt'.format(file_name)
    return app.send_static_file(file_dot_text)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


# Sentry
SENTRY_DSN = os.environ.get('SENTRY_DSN')
if SENTRY_DSN:
    app.config['SENTRY_DSN'] = SENTRY_DSN
    sentry = Sentry(app)


if __name__ == '__main__':
    # app.debug = True
    port = int(os.environ.get('PORT', 8000))
    # logging
    if not app.debug:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.WARNING)
        app.logger.addHandler(handler)

    app.run(host='0.0.0.0', port=port)

########NEW FILE########
__FILENAME__ = converters
# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals
from werkzeug.routing import BaseConverter, IntegerConverter


class ColorConverter(BaseConverter):
    """This converter is used to be sure that the color setted in the URL is a
    valid hexadecimal one.
    """
    def __init__(self, url_map):
        super(ColorConverter, self).__init__(url_map)
        self.regex = "([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})"


class ImgSizeConverter(IntegerConverter):
    """This converter is used to be sure that the requested image size is not
    too big
    """
    def __init__(self, url_map):
        super(ImgSizeConverter, self).__init__(url_map, min=1, max=4000)


class AlphaConverter(IntegerConverter):
    """This converter was made to simplify the routes"""
    def __init__(self, url_map):
        super(AlphaConverter, self).__init__(url_map, min=0, max=255)


########NEW FILE########
__FILENAME__ = fakeimg
# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals, division
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont


class FakeImg():
    """A Fake Image.

    This class uses PIL to create an image based on passed parameters.

    Attributes:
        pil_image (PIL.Image.Image): PIL object.
        raw (str): Real image in PNG format.
    """
    def __init__(self, width, height, background_color, foreground_color,
                 alpha_background, alpha_foreground,
                 text=None,
                 font_name=None,
                 font_size=None,
                 retina=False):
        """Init FakeImg with parameters.

        Args:
            width (int): The width of the image.
            height (int): The height of the image.
            background_color (str): The background color of the image. It
                should be in web hexadecimal format.
                Example: #FFF, #123456.
            alpha_background (int): Alpha value of the background color.
            foreground_color (str): The text color of the image. It should be
                in web hexadecimal format.
                Example: #FFF, #123456.
            alpha_foreground (int): Alpha value of the foreground color.
            text (str): Optional. The actual text which will be drawn on the
                image.
                Default: "{0} x {1}".format(width, height)
            font_name (str): Optional. The font name to use.
                Default: "yanone".
                Fallback to "yanone" if font not found.
            font_size (int): Optional. The font size to use.
                Default value is calculated based on the image dimension.
            retina (bool): Optional. Wether to use retina display or not.
                It basically just multiplies dimension of the image by 2.
        """
        if retina:
            self.width, self.height = [x * 2 for x in [width, height]]
        else:
            self.width, self.height = width, height
        self.background_color = "#{0}".format(background_color)
        self.alpha_background = alpha_background
        self.foreground_color = "#{0}".format(foreground_color)
        self.alpha_foreground = alpha_foreground
        self.text = text or "{0} x {1}".format(width, height)
        self.font_name = font_name or "yanone"
        try:
            if int(font_size) > 0:
                self.font_size = int(font_size)
            else:
                raise ValueError
        except (ValueError, TypeError):
            self.font_size = self._calculate_font_size()
        self.font = self._choose_font()
        self.pil_image = self._draw()

    @property
    def raw(self):
        """Create the image on memory and return it"""
        img_io = BytesIO()
        self.pil_image.save(img_io, 'PNG')
        img_io.seek(0)
        return img_io

    def _calculate_font_size(self):
        min_side = min(self.width, self.height)
        return int(min_side / 4)

    def _choose_font(self):
        """Choosing a font, the fallback is Yanone"""
        font_folder = os.path.dirname(os.path.dirname(__file__))
        font_path = '{0}/font/{1}.otf'.format(font_folder, self.font_name)
        try:
            return ImageFont.truetype(font_path, self.font_size)
        except IOError:
            # font not found: fallback
            self.font_name = "yanone"
            return self._choose_font()

    @staticmethod
    def _hex_to_int(hex_string):
        return int(hex_string, 16)

    def _hex_alpha_to_rgba(self, hex_color, alpha):
        """Convert hexadecimal + alpha value to a rgba tuple"""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([v*2 for v in list(hex_color)])

        red = self._hex_to_int(hex_color[0:2])
        green = self._hex_to_int(hex_color[2:4])
        blue = self._hex_to_int(hex_color[4:6])

        return red, green, blue, alpha

    def _draw(self):
        """Image creation using Pillow (PIL fork)"""
        size = (self.width, self.height)

        rgba_background = self._hex_alpha_to_rgba(self.background_color,
                                                  self.alpha_background)

        image = Image.new("RGBA", size, rgba_background)
        # Draw on the image
        draw = ImageDraw.Draw(image)

        text_width, text_height = self.font.getsize(self.text)
        text_coord = ((self.width - text_width) / 2,
                      (self.height - text_height) / 2)

        rgba_foreground = self._hex_alpha_to_rgba(self.foreground_color,
                                                  self.alpha_foreground)

        draw.text(text_coord, self.text,
                  fill=rgba_foreground, font=self.font)

        del draw

        return image

########NEW FILE########
__FILENAME__ = tests
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals
import unittest
from app import app
from PIL import Image
from io import BytesIO


class AppTestCase(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        self.app = app.test_client()

    def _open_image(self, image_data):
        strio = BytesIO()
        strio.write(image_data)
        strio.seek(0)
        return Image.open(strio)

    # Routes

    def testIndex(self):
        with self.app.get('/') as r:
            self.assertEqual(r.status_code, 200)

    def test404(self):
        with self.app.get('/this-does-not-exist-bitch') as r:
            self.assertEqual(r.status_code, 404)

    def testHeaders(self):
        with self.app.get('/') as r:
            headers = r.headers
            self.assertEqual(headers['X-UA-Compatible'], 'IE=Edge,chrome=1')
            self.assertEqual(headers['Cache-Control'], 'public,max-age=36000')

    def testFavicon(self):
        with self.app.get('/favicon.ico') as r:
            self.assertEqual(r.status_code, 200)

    def testRobotsTxt(self):
        with self.app.get('/robots.txt') as r:
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.mimetype, 'text/plain')

    def testHumansTxt(self):
        with self.app.get('/humans.txt') as r:
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.mimetype, 'text/plain')

    def testTrailingSlash(self):
        # redirected to /100/
        with self.app.get('/100') as r:
            self.assertEqual(r.status_code, 301)

    def testPlaceholder1(self):
        with self.app.get('/300/') as r:
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.mimetype, 'image/png')
            img = self._open_image(r.data)
            width, height = img.size
            self.assertEqual(width, 300)
            self.assertEqual(height, 300)

        with self.app.get('/5000/') as r:
            self.assertEqual(r.status_code, 404)

    def testPlaceholder2(self):
        with self.app.get('/200x100/') as r:
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.mimetype, 'image/png')
            img = self._open_image(r.data)
            width, height = img.size
            self.assertEqual(width, 200)
            self.assertEqual(height, 100)

        with self.app.get('/4005x300/') as r:
            self.assertEqual(r.status_code, 404)

        with self.app.get('/200x4050/') as r:
            self.assertEqual(r.status_code, 404)

    def testPlaceholder3(self):
        with self.app.get('/200x100/CCCCCC/') as r:
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.mimetype, 'image/png')
            img = self._open_image(r.data)
            width, height = img.size
            self.assertEqual(width, 200)
            self.assertEqual(height, 100)

        with self.app.get('/200x100/CCCCCC,50/') as r:
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.mimetype, 'image/png')
            img = self._open_image(r.data)
            width, height = img.size
            self.assertEqual(width, 200)
            self.assertEqual(height, 100)

        with self.app.get('/200x100/prout/') as r:
            self.assertEqual(r.status_code, 404)

        with self.app.get('/200x100/CCCCCC,5123/') as r:
            self.assertEqual(r.status_code, 404)

    def testPlaceholder4(self):
        with self.app.get('/200x100/eee/000/') as r:
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.mimetype, 'image/png')
            img = self._open_image(r.data)
            width, height = img.size
            self.assertEqual(width, 200)
            self.assertEqual(height, 100)

        with self.app.get('/200x100/eee,10/000/') as r:
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.mimetype, 'image/png')
            img = self._open_image(r.data)
            width, height = img.size
            self.assertEqual(width, 200)
            self.assertEqual(height, 100)

        with self.app.get('/200x100/eee/000,25/') as r:
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.mimetype, 'image/png')
            img = self._open_image(r.data)
            width, height = img.size
            self.assertEqual(width, 200)
            self.assertEqual(height, 100)

        with self.app.get('/200x100/eee,15/000,15/') as r:
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.mimetype, 'image/png')
            img = self._open_image(r.data)
            width, height = img.size
            self.assertEqual(width, 200)
            self.assertEqual(height, 100)

        with self.app.get('/200x100/fff/ee/') as r:
            self.assertEqual(r.status_code, 404)

        with self.app.get('/200x100/eee,25555/000/') as r:
            self.assertEqual(r.status_code, 404)

        with self.app.get('/200x100/eee/000,b/') as r:
            self.assertEqual(r.status_code, 404)

        with self.app.get('/200x100/eee,458/000,2555/') as r:
            self.assertEqual(r.status_code, 404)

    def testRetina(self):
        with self.app.get('/200x100/eee/000/?retina=1') as r:
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.mimetype, 'image/png')
            img = self._open_image(r.data)
            width, height = img.size
            self.assertEqual(width, 400)
            self.assertEqual(height, 200)

        with self.app.get('/200x100/eee,10/000,10/?retina=1') as r:
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.mimetype, 'image/png')
            img = self._open_image(r.data)
            width, height = img.size
            self.assertEqual(width, 400)
            self.assertEqual(height, 200)

    def testFontsize(self):
        with self.app.get('/200x100/eee/000/?font_size=1') as r:
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.mimetype, 'image/png')
            img = self._open_image(r.data)
            width, height = img.size
            self.assertEqual(width, 200)
            self.assertEqual(height, 100)

        # Make it work with wrong value (ie. not crash)

        with self.app.get('/200x100/eee/000/?font_size=0') as r:
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.mimetype, 'image/png')
            img = self._open_image(r.data)
            width, height = img.size
            self.assertEqual(width, 200)
            self.assertEqual(height, 100)

        with self.app.get('/200x100/eee/000/?font_size=-1') as r:
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.mimetype, 'image/png')
            img = self._open_image(r.data)
            width, height = img.size
            self.assertEqual(width, 200)
            self.assertEqual(height, 100)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
