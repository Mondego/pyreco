__FILENAME__ = quicktest
import os
import sys
import argparse

from django.conf import settings


class QuickDjangoTest(object):
    """
    A quick way to run the Django test suite without a fully-configured project.

    Example usage:

        >>> QuickDjangoTest('app1', 'app2')

    Based on a script published by Lukasz Dziedzia at:
    http://stackoverflow.com/questions/3841725/how-to-launch-tests-for-django-reusable-app
    """
    DIRNAME = os.path.dirname(__file__)
    INSTALLED_APPS = (
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.admin',
    )

    def __init__(self, *args, **kwargs):
        self.apps = args
        self.run_tests()

    def run_tests(self):
        """
        Fire up the Django test suite developed for version 1.2
        """
        settings.configure(
            DEBUG = True,
            DATABASES = {
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': os.path.join(self.DIRNAME, 'database.db'),
                    'USER': '',
                    'PASSWORD': '',
                    'HOST': '',
                    'PORT': '',
                }
            },
            LOGGING = {
                'version': 1,
                'formatters': {'simple': {'format': '%(levelname)s %(asctime)s %(name)s %(message)s'}},
                'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'}},
                'loggers': {'screamshot': {'handlers': ['console'], 'level': 'DEBUG'}}
            },
            INSTALLED_APPS = self.INSTALLED_APPS + self.apps
        )
        from django.test.simple import DjangoTestSuiteRunner
        failures = DjangoTestSuiteRunner().run_tests(self.apps, verbosity=1)
        if failures: # pragma: no cover
            sys.exit(failures)

if __name__ == '__main__':
    """
    What do when the user hits this file from the shell.

    Example usage:

        $ python quicktest.py app1 app2

    """
    parser = argparse.ArgumentParser(
        usage="[args]",
        description="Run Django tests on the provided applications."
    )
    parser.add_argument('apps', nargs='+', type=str)
    args = parser.parse_args()
    QuickDjangoTest(*args.apps)

########NEW FILE########
__FILENAME__ = decorators
import logging

from django.contrib.auth.decorators import login_required

from . import app_settings


logger = logging.getLogger(__name__)


def login_required_capturable(function=None):
    def _dec(view_func):
        def _view(request, *args, **kwargs):
            remote_ip = request.META.get('HTTP_X_FORWARDED_FOR',
                                         request.META.get('REMOTE_ADDR', ''))
            remote_ip = remote_ip.split(',')[0]
            if remote_ip not in app_settings.get('CAPTURE_ALLOWED_IPS'):
                return login_required(view_func)(request, *args, **kwargs)
            else:
                msg = "Do not require login for %s on %s" % (remote_ip,
                                                             request.path)
                logger.debug(msg)
                return view_func(request, *args, **kwargs)
        _view.__name__ = view_func.__name__
        _view.__dict__ = view_func.__dict__
        _view.__doc__ = view_func.__doc__
        return _view

    if function:
        return _dec(function)
    return _dec

########NEW FILE########
__FILENAME__ = models
# Create your models here.

########NEW FILE########
__FILENAME__ = screamshot
import base64
from StringIO import StringIO

from django import template

from ..utils import casperjs_capture


register = template.Library()


@register.simple_tag
def base64capture(url, selector):
    simage = StringIO()
    casperjs_capture(simage, url, selector=selector)
    # Convert to base64
    encoded = base64.encodestring(simage.getvalue())
    return "image/png;base64," + encoded


@register.filter
def mult(value, arg):
    "Multiplies the arg and the value"
    return int(value) * int(arg)


@register.filter
def sub(value, arg):
    "Subtracts the arg from the value"
    return int(value) - int(arg)


@register.filter
def div(value, arg):
    "Divides the value by the arg"
    return int(value) / int(arg)

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import os
import mock

from django.test import TestCase

from .utils import (process_casperjs_stdout, CaptureError, casperjs_capture,
                    logger as utils_logger)


here = os.path.abspath(os.path.dirname(__file__))


class CaptureOutputTest(TestCase):
    def setUp(self):
        self.fatal = ("INFO: page load\n"
                      "FATAL: Test fatal error")

    def test_fatal_error_raise_exception(self):
        self.assertRaises(CaptureError, process_casperjs_stdout, self.fatal)


class CaptureScriptTest(TestCase):
    def setUp(self):
        utils_logger.info = mock.Mock()
        utils_logger.error = mock.Mock()

    def test_console_message_are_logged(self):
        casperjs_capture('/tmp/file.png', '%s/data/test_page.html' % here)
        utils_logger.info.assert_any_call(' Hey hey')

    def test_javascript_errors_are_logged(self):
        casperjs_capture('/tmp/file.png', '%s/data/test_page.html' % here)
        utils_logger.error.assert_any_call(' Error: Ha ha')

    def test_missing_selector_raises_exception(self):
        self.assertRaises(CaptureError, casperjs_capture, '/tmp/file.png',
                          '%s/data/test_page.html' % here, selector='footer')

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from views import capture


urlpatterns = patterns('screamshot.views',
                       url(r'^$', capture, name='capture'))

########NEW FILE########
__FILENAME__ = utils
import os
import logging
import subprocess
from tempfile import NamedTemporaryFile
import json
from urlparse import urljoin
from mimetypes import guess_type, guess_all_extensions

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.urlresolvers import reverse
from django.core.validators import URLValidator

from . import app_settings


logger = logging.getLogger(__name__)


class UnsupportedImageFormat(Exception):
    pass


class CaptureError(Exception):
    pass


def casperjs_command_kwargs():
    """ will construct kwargs for cmd
    """
    kwargs = {
        'stdout': subprocess.PIPE,
        'stderr': subprocess.PIPE,
        'universal_newlines': True
    }
    phantom_js_cmd = app_settings['PHANTOMJS_CMD']
    if phantom_js_cmd:
        path = '{0}:{1}'.format(os.getenv('PATH', ''), phantom_js_cmd)
        kwargs.update({'env': {'PATH': path}})
    return kwargs


def casperjs_command():
    """
    If setting CASPERJS_CMD is not defined, then
    look up for ``casperjs`` in shell PATH and
    builds the whole capture command.
    """
    cmd = app_settings['CASPERJS_CMD']
    if cmd is None:
        sys_path = os.getenv('PATH', '').split(':')
        for binpath in sys_path:
            cmd = os.path.join(binpath, 'casperjs')
            if os.path.exists(cmd):
                break
    cmd = [cmd]
    try:
        proc = subprocess.Popen(cmd + ['--version'], **casperjs_command_kwargs())
        proc.communicate()
        status = proc.returncode
        assert status == 0
    except OSError:
        msg = "CasperJS binary cannot be found in PATH (%s)" % sys_path
        raise ImproperlyConfigured(msg)
    except AssertionError:
        msg = "CasperJS returned status code %s" % status
        raise ImproperlyConfigured(msg)

    # Add extra CLI arguments
    cmd += app_settings['CLI_ARGS']

    # Concatenate with capture script
    app_path = os.path.dirname(__file__)
    capture = os.path.join(app_path, 'scripts', 'capture.js')
    assert os.path.exists(capture), 'Cannot find %s' % capture
    return cmd + [capture]


CASPERJS_CMD = casperjs_command()


def casperjs_capture(stream, url, method=None, width=None, height=None,
                     selector=None, data=None, waitfor=None, size=None,
                     crop=None, render='png'):
    """
    Captures web pages using ``casperjs``
    """
    try:
        if isinstance(stream, basestring):
            output = stream
        else:
            with NamedTemporaryFile('rwb', suffix='.png', delete=False) as f:
                output = f.name

        cmd = CASPERJS_CMD + [url, output]

        # Extra command-line options
        if method:
            cmd += ['--method=%s' % method]
        if width:
            cmd += ['--width=%s' % width]
        if height:
            cmd += ['--height=%s' % height]
        if selector:
            cmd += ['--selector=%s' % selector]
        if data:
            cmd += ['--data="%s"' % json.dumps(data)]
        if waitfor:
            cmd += ['--waitfor=%s' % waitfor]
        logger.debug(cmd)
        # Run CasperJS process
        proc = subprocess.Popen(cmd, **casperjs_command_kwargs())
        stdout = proc.communicate()[0]
        process_casperjs_stdout(stdout)

        size = parse_size(size)
        render = parse_render(render)
        if size or (render and render != 'png'):
            image_postprocess(output, stream, size, crop, render)
        else:
            if stream != output:
                # From file to stream
                with open(output) as out:
                    stream.write(out.read())
                stream.flush()
    finally:
        if stream != output:
            os.unlink(output)


def process_casperjs_stdout(stdout):
    """Parse and digest capture script output.
    """
    for line in stdout.splitlines():
        bits = line.split(':', 1)
        if len(bits) < 2:
            bits = ('INFO', bits)
        level, msg = bits

        if level == 'FATAL':
            logger.fatal(msg)
            raise CaptureError(msg)
        elif level == 'ERROR':
            logger.error(msg)
        else:
            logger.info(msg)


def image_mimetype(render):
    """Return internet media(image) type.

    >>>image_mimetype(None)
    'image/png'
    >>>image_mimetype('jpg')
    'image/jpeg'
    >>>image_mimetype('png')
    'image/png'
    >>>image_mimetype('xbm')
    'image/x-xbitmap'
    """
    render = parse_render(render)
    # All most web browsers don't support 'image/x-ms-bmp'.
    if render == 'bmp':
        return 'image/bmp'
    return guess_type('foo.%s' % render)[0]


def parse_url(request, url):
    """Parse url URL parameter."""
    try:
        validate = URLValidator()
        validate(url)
    except ValidationError:
        if url.startswith('/'):
            host = request.get_host()
            scheme = 'https' if request.is_secure() else 'http'
            url = '{scheme}://{host}{uri}'.format(scheme=scheme,
                                                  host=host,
                                                  uri=url)
        else:
            url = request.build_absolute_uri(reverse(url))
    return url


def parse_render(render):
    """Parse render URL parameter.

    >>> parse_render(None)
    'png'
    >>> parse_render('html')
    'png'
    >>> parse_render('png')
    'png'
    >>> parse_render('jpg')
    'jpeg'
    >>> parse_render('gif')
    'gif'
    """
    formats = {
        'jpeg': guess_all_extensions('image/jpeg'),
        'png': guess_all_extensions('image/png'),
        'gif': guess_all_extensions('image/gif'),
        'bmp': guess_all_extensions('image/x-ms-bmp'),
        'tiff': guess_all_extensions('image/tiff'),
        'xbm': guess_all_extensions('image/x-xbitmap')
    }
    if not render:
        render = 'png'
    else:
        render = render.lower()
        for k, v in formats.iteritems():
            if '.%s' % render in v:
                render = k
                break
        else:
            render = 'png'
    return render


def parse_size(size_raw):
    """ Parse size URL parameter.

    >>> parse_size((100,None))
    None
    >>> parse_size('300x100')
    (300, 100)
    >>> parse_size('300x')
    None
    >>> parse_size('x100')
    None
    >>> parse_size('x')
    None
    """
    try:
        width_str, height_str = size_raw.lower().split('x')
    except AttributeError:
        size = None
    except ValueError:
        size = None
    else:
        try:
            width = int(width_str)
            assert width > 0
        except (ValueError, AssertionError):
            width = None
        try:
            height = int(height_str)
            assert height > 0
        except (ValueError, AssertionError):
            height = None
        size = width, height
        if not all(size):
            size = None
    return size


def image_postprocess(imagefile, output, size, crop, render):
    """
    Resize and crop captured image, and saves to output.
    (can be stream or filename)
    """
    try:
        from PIL import Image
    except ImportError:
        import Image

    img = Image.open(imagefile)
    size_crop = None
    img_resized = img
    if size and crop and crop.lower() == 'true':
        width_raw, height_raw = img.size
        width, height = size
        height_better = int(height_raw * (float(width) /
                                          width_raw))
        if height < height_better:
            size_crop = (0, 0, width, height)

    try:
        if size_crop:
            size_better = width, height_better
            img_better = img.resize(size_better, Image.ANTIALIAS)
            img_resized = img_better.crop(size_crop)
        elif size:
            img_resized = img.resize(size, Image.ANTIALIAS)

        # If save with 'bmp' use default mode('RGBA'), it will raise:
        # "IOError: cannot write mode RGBA as BMP".
        # So, we need convert image mode
        # from 'RGBA' to 'RGB' for 'bmp' format.
        if render == 'bmp':
            img_resized = img_resized.convert('RGB')
        # Fix IOError: cannot write mode RGBA as XBM
        elif render == 'xbm':
            img_resized = img_resized.convert('1')
        # Works with either filename or file-like object
        img_resized.save(output, render)
    except KeyError:
        raise UnsupportedImageFormat
    except IOError as e:
        raise CaptureError(e)


def build_absolute_uri(request, url):
    """
    Allow to override printing url, not necessarily on the same
    server instance.
    """
    if app_settings.get('CAPTURE_ROOT_URL'):
        return urljoin(app_settings.get('CAPTURE_ROOT_URL'), url)
    return request.build_absolute_uri(url)

########NEW FILE########
__FILENAME__ = views
import base64
import logging
from StringIO import StringIO

from django.core.urlresolvers import NoReverseMatch
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.translation import ugettext as _

from utils import (casperjs_capture, CaptureError, UnsupportedImageFormat,
                   image_mimetype, parse_url)

logger = logging.getLogger(__name__)


def capture(request):
    # Merge both QueryDict into dict
    parameters = dict([(k, v) for k, v in request.GET.items()])
    parameters.update(dict([(k, v) for k, v in request.POST.items()]))

    url = parameters.get('url')
    if not url:
        return HttpResponseBadRequest(_('Missing url parameter'))
    try:
        url = parse_url(request, url)
    except NoReverseMatch:
        error_msg = _("URL '%s' invalid (could not reverse)") % url
        return HttpResponseBadRequest(error_msg)

    method = parameters.get('method', request.method)
    selector = parameters.get('selector')
    data = parameters.get('data')
    waitfor = parameters.get('waitfor')
    render = parameters.get('render', 'png')
    size = parameters.get('size')
    crop = parameters.get('crop')

    try:
        width = int(parameters.get('width', ''))
    except ValueError:
        width = None
    try:
        height = int(parameters.get('height', ''))
    except ValueError:
        height = None

    stream = StringIO()
    try:
        casperjs_capture(stream, url, method=method.lower(), width=width,
                         height=height, selector=selector, data=data,
                         size=size, waitfor=waitfor, crop=crop, render=render)
    except CaptureError as e:
        return HttpResponseBadRequest(e)
    except ImportError:
        error_msg = _('Resize not supported (PIL not available)')
        return HttpResponseBadRequest(error_msg)
    except UnsupportedImageFormat:
        error_msg = _('Unsupported image format: %s' % render)
        return HttpResponseBadRequest(error_msg)

    if render == "html":
        response = HttpResponse(mimetype='text/html')
        body = """<html><body onload="window.print();">
                <img src="data:image/png;base64,%s"/></body></html>
                """ % base64.encodestring(stream.getvalue())
        response.write(body)
    else:
        response = HttpResponse(mimetype=image_mimetype(render))
        response.write(stream.getvalue())

    return response

########NEW FILE########
