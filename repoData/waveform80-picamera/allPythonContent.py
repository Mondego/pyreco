__FILENAME__ = conf
#!/usr/bin/env python3
# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013,2014 Dave Hughes <dave@waveform.org.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import setup as _setup

# -- General configuration ------------------------------------------------

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode', 'sphinx.ext.intersphinx']
templates_path = ['_templates']
source_suffix = '.rst'
#source_encoding = 'utf-8-sig'
master_doc = 'index'
project = _setup.__project__.title()
copyright = '2013,2014 %s' % _setup.__author__
version = _setup.__version__
release = _setup.__version__
#language = None
#today_fmt = '%B %d, %Y'
exclude_patterns = ['_build']
#default_role = None
#add_function_parentheses = True
#add_module_names = True
#show_authors = False
pygments_style = 'sphinx'
#modindex_common_prefix = []
#keep_warnings = False

# -- Autodoc configuration ------------------------------------------------

autodoc_member_order = 'groupwise'

# -- Intersphinx configuration --------------------------------------------

intersphinx_mapping = {'python': ('http://docs.python.org/3.2', None)}

# -- Options for HTML output ----------------------------------------------

html_theme = 'default'
#html_theme_options = {}
#html_theme_path = []
#html_title = None
#html_short_title = None
#html_logo = None
#html_favicon = None
html_static_path = ['_static']
#html_extra_path = []
#html_last_updated_fmt = '%b %d, %Y'
#html_use_smartypants = True
#html_sidebars = {}
#html_additional_pages = {}
#html_domain_indices = True
#html_use_index = True
#html_split_index = False
#html_show_sourcelink = True
#html_show_sphinx = True
#html_show_copyright = True
#html_use_opensearch = ''
#html_file_suffix = None
htmlhelp_basename = '%sdoc' % _setup.__project__

# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    'papersize': 'a4paper',
    'pointsize': '10pt',
    #'preamble': '',
}

latex_documents = [
    (
        'index',                       # source start file
        '%s.tex' % _setup.__project__, # target filename
        '%s Documentation' % project,  # title
        _setup.__author__,             # author
        'manual',                      # documentclass
        ),
]

#latex_logo = None
#latex_use_parts = False
#latex_show_pagerefs = False
#latex_show_urls = False
#latex_appendices = []
#latex_domain_indices = True

# -- Options for manual page output ---------------------------------------

man_pages = []

#man_show_urls = False

# -- Options for Texinfo output -------------------------------------------

texinfo_documents = []

#texinfo_appendices = []
#texinfo_domain_indices = True
#texinfo_show_urls = 'footnote'
#texinfo_no_detailmenu = False

########NEW FILE########
__FILENAME__ = maildebs
#!/usr/bin/env python3

import io
import os
import re
import sys
import subprocess
import smtplib
import configparser
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from setup import __project__, __version__


HERE = os.path.dirname(__file__)


def create_message(sender, recipients, subject, body, attachments):
    root_container = MIMEMultipart(_subtype='related')
    root_container['From'] = sender
    root_container['To'] = recipients
    root_container['Subject'] = subject
    root_container.preamble = 'This is a multi-part message in MIME format.'
    root_container.attach(MIMEText(body, _subtype='plain'))
    for attachment in attachments:
        with io.open(attachment, 'rb') as f:
            attachment_container = MIMEApplication(f.read())
        filename = os.path.split(attachment)[1]
        attachment_container.add_header('Content-Id', '<%s>' % filename)
        attachment_container.add_header('Content-Disposition', 'attachment', filename=filename)
        root_container.attach(attachment_container)
    return root_container


def send_email(message, host='localhost', port=25):
    server = smtplib.SMTP(host, port)
    try:
        server.ehlo()
        server.sendmail(
            message['From'],
            message['To'],
            message.as_string())
    finally:
        server.quit()


def main():
    config = configparser.ConfigParser()
    config.read(os.path.expanduser('~/.maildebs.conf'))
    project = __project__
    version = __version__
    recipient = config['message']['recipient']
    sender = config['message'].get('sender', '%s <%s>' % (
        subprocess.check_output(['git', 'config', '--global', 'user.name']).decode('utf-8').strip(),
        subprocess.check_output(['git', 'config', '--global', 'user.email']).decode('utf-8').strip(),
        ))
    sender_match = re.match(r'(?P<name>[^<]+) <(?P<email>[^>]+)>', sender)
    recipient_match = re.match(r'(?P<name>[^<]+) <(?P<email>[^>]+)>', recipient)
    subst = {
        'project': project,
        'version': version,
        'recipient_name': recipient_match.group('name').split(),
        'recipient_email': recipient_match.group('email'),
        'recipient_forename': recipient_match.group('name').split()[0],
        'recipient_surname': recipient_match.group('name').split()[1],
        'sender_name': sender_match.group('name').split(),
        'sender_email': sender_match.group('email'),
        'sender_forename': sender_match.group('name').split()[0],
        'sender_surname': sender_match.group('name').split()[1],
        }
    subject = config['message']['subject'].format(**subst)
    body = config['message']['body'].format(**subst)
    attachments = sys.argv[1:]
    send_email(
        create_message(sender, recipient, subject, body, attachments),
        config['smtp'].get('host', 'localhost'),
        config['smtp'].get('port', 25))


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = bcm_host
# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python header conversion
# Copyright (c) 2013,2014 Dave Hughes <dave@waveform.org.uk>
#
# Original headers
# Copyright (c) 2012, Broadcom Europe Ltd
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str equivalent to Py3's
str = type('')

import ctypes as ct
import warnings

try:
    _lib = ct.CDLL('libbcm_host.so')
except OSError:
    warnings.warn(
        'Unable to locate libbcm_host.so; using a mock object instead. This '
        'functionality only exists to support building the package '
        'documentation on non-Raspberry Pi systems. If you see this message '
        'on the Raspberry Pi then you are missing a required library',
        RuntimeWarning)
    class _Mock(object):
        def __getattr__(self, attr):
            return self
        def __call__(self, *args, **kwargs):
            return self
    _lib = _Mock()

# bcm_host.h #################################################################

bcm_host_init = _lib.bcm_host_init
bcm_host_init.argtypes = []
bcm_host_init.restype = None

bcm_host_deinit = _lib.bcm_host_deinit
bcm_host_deinit.argtypes = []
bcm_host_deinit.restype = None

graphics_get_display_size = _lib.graphics_get_display_size
graphics_get_display_size.argtypes = [ct.c_uint16, ct.POINTER(ct.c_uint32), ct.POINTER(ct.c_uint32)]
graphics_get_display_size.restype = ct.c_int32


########NEW FILE########
__FILENAME__ = camera
# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013,2014 Dave Hughes <dave@waveform.org.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str and range equivalent to Py3's
str = type('')
try:
    range = xrange
except NameError:
    pass

import warnings
import datetime
import mimetypes
import ctypes as ct
import fractions

import picamera.mmal as mmal
import picamera.bcm_host as bcm_host
from picamera.exc import (
    PiCameraError,
    PiCameraValueError,
    PiCameraRuntimeError,
    PiCameraMMALError,
    mmal_check,
    )
from picamera.encoders import (
    PiVideoFrame,
    PiVideoEncoder,
    PiImageEncoder,
    PiRawOneImageEncoder,
    PiRawMultiImageEncoder,
    PiCookedOneImageEncoder,
    PiCookedMultiImageEncoder,
    )

try:
    import RPi.GPIO as GPIO
except ImportError:
    # Can't find RPi.GPIO so just null-out the reference
    GPIO = None


__all__ = ['PiCamera']


def _control_callback(port, buf):
    if buf[0].cmd != mmal.MMAL_EVENT_PARAMETER_CHANGED:
        raise PiCameraRuntimeError(
            "Received unexpected camera control callback event, 0x%08x" % buf[0].cmd)
    mmal.mmal_buffer_header_release(buf)
_control_callback = mmal.MMAL_PORT_BH_CB_T(_control_callback)


# Guardian variable set upon initialization of PiCamera and used to ensure that
# no more than one PiCamera is instantiated at a given time
_CAMERA = None


class PiCameraFraction(fractions.Fraction):
    """
    Extends :class:`~fractions.Fraction` to act as a (numerator, denominator)
    tuple when required.
    """
    def __len__(self):
        return 2

    def __getitem__(self, index):
        if index == 0:
            return self.numerator
        elif index == 1:
            return self.denominator
        else:
            raise IndexError('invalid index %d' % index)

    def __contains__(self, value):
        return value in (self.numerator, self.denominator)


def to_rational(value):
    """
    Converts a value to a numerator, denominator tuple.

    Given a :class:`int`, :class:`float`, or :class:`~fractions.Fraction`
    instance, returns the value as a `(numerator, denominator)` tuple where the
    numerator and denominator are integer values.
    """
    try:
        # int, long, or fraction
        n, d = value.numerator, value.denominator
    except AttributeError:
        try:
            # float
            n, d = value.as_integer_ratio()
        except AttributeError:
            try:
                # tuple
                n, d = value
            except (TypeError, ValueError):
                # anything else...
                n = int(value)
                d = 1
    # Ensure denominator is reasonable
    if d == 0:
        raise PiCameraValueError("Denominator cannot be 0")
    elif d > 65536:
        f = fractions.Fraction(n, d).limit_denominator(65536)
        n, d = f.numerator, f.denominator
    return n, d


class PiCamera(object):
    """
    Provides a pure Python interface to the Raspberry Pi's camera module.

    Upon construction, this class initializes the camera. As there is only a
    single camera supported by the Raspberry Pi, this means that only a single
    instance of this class can exist at any given time (it is effectively a
    singleton class although it is not implemented as such).

    No preview or recording is started automatically upon construction.  Use
    the :meth:`capture` method to capture images, the :meth:`start_recording`
    method to begin recording video, or the :meth:`start_preview` method to
    start live display of the camera's input.

    Several attributes are provided to adjust the camera's configuration. Some
    of these can be adjusted while a recording is running, like
    :attr:`brightness`. Others, like :attr:`resolution`, can only be adjusted
    when the camera is idle.

    When you are finished with the camera, you should ensure you call the
    :meth:`close` method to release the camera resources (failure to do this
    leads to GPU memory leaks)::

        camera = PiCamera()
        try:
            # do something with the camera
            pass
        finally:
            camera.close()

    The class supports the context manager protocol to make this particularly
    easy (upon exiting the ``with`` statement, the :meth:`close` method is
    automatically called)::

        with PiCamera() as camera:
            # do something with the camera
            pass
    """

    CAMERA_PREVIEW_PORT = 0
    CAMERA_VIDEO_PORT = 1
    CAMERA_CAPTURE_PORT = 2
    CAMERA_PORTS = (
        CAMERA_PREVIEW_PORT,
        CAMERA_VIDEO_PORT,
        CAMERA_CAPTURE_PORT,
        )
    MAX_RESOLUTION = (2592, 1944)
    MAX_IMAGE_RESOLUTION = (2592, 1944) # Deprecated - use MAX_RESOLUTION instead
    MAX_VIDEO_RESOLUTION = (1920, 1080) # Deprecated - use MAX_RESOLUTION instead
    DEFAULT_FRAME_RATE_NUM = 30
    DEFAULT_FRAME_RATE_DEN = 1
    VIDEO_OUTPUT_BUFFERS_NUM = 3

    METER_MODES = {
        'average': mmal.MMAL_PARAM_EXPOSUREMETERINGMODE_AVERAGE,
        'spot':    mmal.MMAL_PARAM_EXPOSUREMETERINGMODE_SPOT,
        'backlit': mmal.MMAL_PARAM_EXPOSUREMETERINGMODE_BACKLIT,
        'matrix':  mmal.MMAL_PARAM_EXPOSUREMETERINGMODE_MATRIX,
        }

    EXPOSURE_MODES = {
        'auto':          mmal.MMAL_PARAM_EXPOSUREMODE_AUTO,
        'night':         mmal.MMAL_PARAM_EXPOSUREMODE_NIGHT,
        'nightpreview':  mmal.MMAL_PARAM_EXPOSUREMODE_NIGHTPREVIEW,
        'backlight':     mmal.MMAL_PARAM_EXPOSUREMODE_BACKLIGHT,
        'spotlight':     mmal.MMAL_PARAM_EXPOSUREMODE_SPOTLIGHT,
        'sports':        mmal.MMAL_PARAM_EXPOSUREMODE_SPORTS,
        'snow':          mmal.MMAL_PARAM_EXPOSUREMODE_SNOW,
        'beach':         mmal.MMAL_PARAM_EXPOSUREMODE_BEACH,
        'verylong':      mmal.MMAL_PARAM_EXPOSUREMODE_VERYLONG,
        'fixedfps':      mmal.MMAL_PARAM_EXPOSUREMODE_FIXEDFPS,
        'antishake':     mmal.MMAL_PARAM_EXPOSUREMODE_ANTISHAKE,
        'fireworks':     mmal.MMAL_PARAM_EXPOSUREMODE_FIREWORKS,
        }

    AWB_MODES = {
        'off':           mmal.MMAL_PARAM_AWBMODE_OFF,
        'auto':          mmal.MMAL_PARAM_AWBMODE_AUTO,
        'sunlight':      mmal.MMAL_PARAM_AWBMODE_SUNLIGHT,
        'cloudy':        mmal.MMAL_PARAM_AWBMODE_CLOUDY,
        'shade':         mmal.MMAL_PARAM_AWBMODE_SHADE,
        'tungsten':      mmal.MMAL_PARAM_AWBMODE_TUNGSTEN,
        'fluorescent':   mmal.MMAL_PARAM_AWBMODE_FLUORESCENT,
        'incandescent':  mmal.MMAL_PARAM_AWBMODE_INCANDESCENT,
        'flash':         mmal.MMAL_PARAM_AWBMODE_FLASH,
        'horizon':       mmal.MMAL_PARAM_AWBMODE_HORIZON,
        }

    IMAGE_EFFECTS = {
        'none':          mmal.MMAL_PARAM_IMAGEFX_NONE,
        'negative':      mmal.MMAL_PARAM_IMAGEFX_NEGATIVE,
        'solarize':      mmal.MMAL_PARAM_IMAGEFX_SOLARIZE,
        'posterize':     mmal.MMAL_PARAM_IMAGEFX_POSTERIZE,
        'whiteboard':    mmal.MMAL_PARAM_IMAGEFX_WHITEBOARD,
        'blackboard':    mmal.MMAL_PARAM_IMAGEFX_BLACKBOARD,
        'sketch':        mmal.MMAL_PARAM_IMAGEFX_SKETCH,
        'denoise':       mmal.MMAL_PARAM_IMAGEFX_DENOISE,
        'emboss':        mmal.MMAL_PARAM_IMAGEFX_EMBOSS,
        'oilpaint':      mmal.MMAL_PARAM_IMAGEFX_OILPAINT,
        'hatch':         mmal.MMAL_PARAM_IMAGEFX_HATCH,
        'gpen':          mmal.MMAL_PARAM_IMAGEFX_GPEN,
        'pastel':        mmal.MMAL_PARAM_IMAGEFX_PASTEL,
        'watercolor':    mmal.MMAL_PARAM_IMAGEFX_WATERCOLOUR,
        'film':          mmal.MMAL_PARAM_IMAGEFX_FILM,
        'blur':          mmal.MMAL_PARAM_IMAGEFX_BLUR,
        'saturation':    mmal.MMAL_PARAM_IMAGEFX_SATURATION,
        'colorswap':     mmal.MMAL_PARAM_IMAGEFX_COLOURSWAP,
        'washedout':     mmal.MMAL_PARAM_IMAGEFX_WASHEDOUT,
        'posterise':     mmal.MMAL_PARAM_IMAGEFX_POSTERISE,
        'colorpoint':    mmal.MMAL_PARAM_IMAGEFX_COLOURPOINT,
        'colorbalance':  mmal.MMAL_PARAM_IMAGEFX_COLOURBALANCE,
        'cartoon':       mmal.MMAL_PARAM_IMAGEFX_CARTOON,
        }

    RAW_FORMATS = {
        # For some bizarre reason, the non-alpha formats are backwards...
        'yuv':  mmal.MMAL_ENCODING_I420,
        'rgb':  mmal.MMAL_ENCODING_BGR24,
        'rgba': mmal.MMAL_ENCODING_RGBA,
        'bgr':  mmal.MMAL_ENCODING_RGB24,
        'bgra': mmal.MMAL_ENCODING_BGRA,
        }

    _METER_MODES_R    = {v: k for (k, v) in METER_MODES.items()}
    _EXPOSURE_MODES_R = {v: k for (k, v) in EXPOSURE_MODES.items()}
    _AWB_MODES_R      = {v: k for (k, v) in AWB_MODES.items()}
    _IMAGE_EFFECTS_R  = {v: k for (k, v) in IMAGE_EFFECTS.items()}
    _RAW_FORMATS_R    = {v: k for (k, v) in RAW_FORMATS.items()}

    def __init__(self):
        global _CAMERA
        if _CAMERA:
            raise PiCameraRuntimeError(
                "Only one PiCamera object can be in existence at a time")
        _CAMERA = self
        bcm_host.bcm_host_init()
        mimetypes.add_type('application/h264',  '.h264',  False)
        mimetypes.add_type('application/mjpeg', '.mjpg',  False)
        mimetypes.add_type('application/mjpeg', '.mjpeg', False)
        self._used_led = False
        self._camera = None
        self._camera_config = None
        self._preview = None
        self._preview_connection = None
        self._null_sink = None
        self._splitter = None
        self._splitter_connection = None
        self._encoders = {}
        self._raw_format = 'yuv'
        self._exif_tags = {
            'IFD0.Model': 'RP_OV5647',
            'IFD0.Make': 'RaspberryPi',
            }
        try:
            self._init_camera()
            self._init_defaults()
            self._init_preview()
            self._init_splitter()
        except:
            self.close()
            raise

    def _init_led(self):
        global GPIO
        if GPIO:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                GPIO.setup(5, GPIO.OUT, initial=GPIO.LOW)
                self._used_led = True
            except RuntimeError:
                # We're probably not running as root. In this case, forget the
                # GPIO reference so we don't try anything further
                GPIO = None

    def _init_camera(self):
        self._camera = ct.POINTER(mmal.MMAL_COMPONENT_T)()
        self._camera_config = mmal.MMAL_PARAMETER_CAMERA_CONFIG_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_CAMERA_CONFIG,
                ct.sizeof(mmal.MMAL_PARAMETER_CAMERA_CONFIG_T)
                ))
        try:
            mmal_check(
                mmal.mmal_component_create(
                    mmal.MMAL_COMPONENT_DEFAULT_CAMERA, self._camera),
                prefix="Failed to create camera component")
        except PiCameraMMALError as e:
            if e.status == mmal.MMAL_ENOMEM:
                raise PiCameraError(
                    "Camera is not enabled. Try running 'sudo raspi-config' "
                    "and ensure that the camera has been enabled.")
            else:
                raise
        if not self._camera[0].output_num:
            raise PiCameraError("Camera doesn't have output ports")

        mmal_check(
            mmal.mmal_port_enable(
                self._camera[0].control,
                _control_callback),
            prefix="Unable to enable control port")

        # Get screen resolution
        w = ct.c_uint32()
        h = ct.c_uint32()
        bcm_host.graphics_get_display_size(0, w, h)
        w = int(w.value)
        h = int(h.value)
        cc = self._camera_config
        cc.max_stills_w = w
        cc.max_stills_h = h
        cc.stills_yuv422 = 0
        cc.one_shot_stills = 1
        cc.max_preview_video_w = w
        cc.max_preview_video_h = h
        cc.num_preview_video_frames = 3
        cc.stills_capture_circular_buffer_height = 0
        cc.fast_preview_resume = 0
        cc.use_stc_timestamp = mmal.MMAL_PARAM_TIMESTAMP_MODE_RESET_STC
        mmal_check(
            mmal.mmal_port_parameter_set(self._camera[0].control, cc.hdr),
            prefix="Camera control port couldn't be configured")

        for p in self.CAMERA_PORTS:
            port = self._camera[0].output[p]
            fmt = port[0].format
            fmt[0].encoding = mmal.MMAL_ENCODING_I420 if p != self.CAMERA_PREVIEW_PORT else mmal.MMAL_ENCODING_OPAQUE
            fmt[0].encoding_variant = mmal.MMAL_ENCODING_I420
            fmt[0].es[0].video.width = mmal.VCOS_ALIGN_UP(w, 32)
            fmt[0].es[0].video.height = mmal.VCOS_ALIGN_UP(h, 16)
            fmt[0].es[0].video.crop.x = 0
            fmt[0].es[0].video.crop.y = 0
            fmt[0].es[0].video.crop.width = w
            fmt[0].es[0].video.crop.height = h
            # 0 implies variable frame-rate
            fmt[0].es[0].video.frame_rate.num = self.DEFAULT_FRAME_RATE_NUM if p != self.CAMERA_CAPTURE_PORT else 0
            fmt[0].es[0].video.frame_rate.den = self.DEFAULT_FRAME_RATE_DEN
            mmal_check(
                mmal.mmal_port_format_commit(self._camera[0].output[p]),
                prefix="Camera %s format couldn't be set" % {
                    self.CAMERA_PREVIEW_PORT: "preview",
                    self.CAMERA_VIDEO_PORT:   "video",
                    self.CAMERA_CAPTURE_PORT: "still",
                    }[p])
            if p != self.CAMERA_PREVIEW_PORT:
                port[0].buffer_num = port[0].buffer_num_min
                port[0].buffer_size = port[0].buffer_size_recommended

        mmal_check(
            mmal.mmal_component_enable(self._camera),
            prefix="Camera component couldn't be enabled")

    def _init_defaults(self):
        self.sharpness = 0
        self.contrast = 0
        self.brightness = 50
        self.saturation = 0
        self.ISO = 0 # auto
        self.video_stabilization = False
        self.exposure_compensation = 0
        self.exposure_mode = 'auto'
        self.meter_mode = 'average'
        self.awb_mode = 'auto'
        self.image_effect = 'none'
        self.color_effects = None
        self.rotation = 0
        self.hflip = self.vflip = False
        self.crop = (0.0, 0.0, 1.0, 1.0)

    def _init_splitter(self):
        # Create a splitter component for the video port. This is to permit
        # video recordings and captures where use_video_port=True to occur
        # simultaneously (#26)
        self._splitter = ct.POINTER(mmal.MMAL_COMPONENT_T)()
        mmal_check(
            mmal.mmal_component_create(
                mmal.MMAL_COMPONENT_DEFAULT_VIDEO_SPLITTER, self._splitter),
            prefix="Failed to create video splitter")
        if not self._splitter[0].input_num:
            raise PiCameraError("No input ports on splitter component")
        if self._splitter[0].output_num != 4:
            raise PiCameraError(
                "Expected 4 output ports on splitter "
                "(found %d)" % self._splitter[0].output_num)
        self._reconfigure_splitter()
        self._splitter_connection = self._connect_ports(
            self._camera[0].output[self.CAMERA_VIDEO_PORT],
            self._splitter[0].input[0])

    def _init_preview(self):
        # Create and enable the preview component, but don't actually connect
        # it to the camera at this time
        self._preview = ct.POINTER(mmal.MMAL_COMPONENT_T)()
        mmal_check(
            mmal.mmal_component_create(
                mmal.MMAL_COMPONENT_DEFAULT_VIDEO_RENDERER, self._preview),
            prefix="Failed to create preview component")
        if not self._preview[0].input_num:
            raise PiCameraError("No input ports on preview component")

        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
            ))
        mp.set = (
            mmal.MMAL_DISPLAY_SET_LAYER |
            mmal.MMAL_DISPLAY_SET_ALPHA |
            mmal.MMAL_DISPLAY_SET_FULLSCREEN)
        mp.layer = 2
        mp.alpha = 255
        mp.fullscreen = 1
        mmal_check(
            mmal.mmal_port_parameter_set(self._preview[0].input[0], mp.hdr),
            prefix="Unable to set preview port parameters")

        mmal_check(
            mmal.mmal_component_enable(self._preview),
            prefix="Preview component couldn't be enabled")

        # Create a null-sink component, enable it and connect it to the
        # camera's preview port. If nothing is connected to the preview port,
        # the camera doesn't measure exposure and captured images gradually
        # fade to black (issue #22)
        self._null_sink = ct.POINTER(mmal.MMAL_COMPONENT_T)()
        mmal_check(
            mmal.mmal_component_create(
                mmal.MMAL_COMPONENT_DEFAULT_NULL_SINK, self._null_sink),
            prefix="Failed to create null sink component")
        if not self._null_sink[0].input_num:
            raise PiCameraError("No input ports on null sink component")
        mmal_check(
            mmal.mmal_component_enable(self._null_sink),
            prefix="Null sink component couldn't be enabled")

        self._preview_connection = self._connect_ports(
            self._camera[0].output[self.CAMERA_PREVIEW_PORT],
            self._null_sink[0].input[0])

    def _connect_ports(self, output_port, input_port):
        """
        Connect the specified output and input ports
        """
        result = ct.POINTER(mmal.MMAL_CONNECTION_T)()
        mmal_check(
            mmal.mmal_connection_create(
                result, output_port, input_port,
                mmal.MMAL_CONNECTION_FLAG_TUNNELLING |
                mmal.MMAL_CONNECTION_FLAG_ALLOCATION_ON_INPUT),
            prefix="Failed to create connection")
        mmal_check(
            mmal.mmal_connection_enable(result),
            prefix="Failed to enable connection")
        return result

    def _get_ports(self, from_video_port, splitter_port):
        """
        Determine the camera and output ports for given capture options
        """
        camera_port = (
            self._camera[0].output[self.CAMERA_VIDEO_PORT]
            if from_video_port else
            self._camera[0].output[self.CAMERA_CAPTURE_PORT]
            )
        output_port = (
            self._splitter[0].output[splitter_port]
            if from_video_port else
            camera_port
            )
        return (camera_port, output_port)

    def _reconfigure_splitter(self):
        """
        Copy the camera's video port config to the video splitter
        """
        mmal.mmal_format_copy(
            self._splitter[0].input[0][0].format,
            self._camera[0].output[self.CAMERA_VIDEO_PORT][0].format)
        self._splitter[0].input[0][0].buffer_num = max(
            self._splitter[0].input[0][0].buffer_num,
            self.VIDEO_OUTPUT_BUFFERS_NUM)
        mmal_check(
            mmal.mmal_port_format_commit(self._splitter[0].input[0]),
            prefix="Couldn't set splitter input port format")
        for p in range(4):
            mmal.mmal_format_copy(
                self._splitter[0].output[p][0].format,
                self._splitter[0].input[0][0].format)
            mmal_check(
                mmal.mmal_port_format_commit(self._splitter[0].output[p]),
                prefix="Couldn't set splitter output port %d format" % p)

    def _disable_camera(self):
        """
        Temporarily disable the camera and all permanently attached components
        """
        mmal_check(
            mmal.mmal_connection_disable(self._splitter_connection),
            prefix="Failed to disable splitter connection")
        mmal_check(
            mmal.mmal_connection_disable(self._preview_connection),
            prefix="Failed to disable preview connection")
        mmal_check(
            mmal.mmal_component_disable(self._camera),
            prefix="Failed to disable camera")

    def _enable_camera(self):
        """
        Re-enable the camera and all permanently attached components
        """
        self._reconfigure_splitter()
        mmal_check(
            mmal.mmal_component_enable(self._camera),
            prefix="Failed to enable camera")
        mmal_check(
            mmal.mmal_connection_enable(self._preview_connection),
            prefix="Failed to enable preview connection")
        mmal_check(
            mmal.mmal_connection_enable(self._splitter_connection),
            prefix="Failed to enable splitter connection")

    def _check_camera_open(self):
        """
        Raise an exception if the camera is already closed
        """
        if self.closed:
            raise PiCameraRuntimeError("Camera is closed")

    def _check_recording_stopped(self):
        """
        Raise an exception if the camera is currently recording
        """
        if self.recording:
            raise PiCameraRuntimeError("Recording is currently running")

    def _get_format(self, output, format):
        if format:
            return format
        elif isinstance(output, (bytes, str)):
            filename = output
        elif hasattr(output, 'name'):
            filename = output.name
        else:
            raise PiCameraValueError(
                'Format must be specified when output has no filename')
        (type, encoding) = mimetypes.guess_type(filename, strict=False)
        if type:
            return type
        raise PiCameraValueError(
            'Unable to determine type from filename %s' % filename)

    def _get_image_format(self, output, format):
        format = self._get_format(output, format)
        format = (
            format[6:] if format.startswith('image/') else
            format)
        if format == 'x-ms-bmp':
            format = 'bmp'
        if format == 'raw':
            format = self.raw_format
        return format

    def _get_video_format(self, output, format):
        format = self._get_format(output, format)
        format = (
            format[6:]  if format.startswith('video/') else
            format[12:] if format.startswith('application/') else
            format)
        return format

    def close(self):
        """
        Finalizes the state of the camera.

        After successfully constructing a :class:`PiCamera` object, you should
        ensure you call the :meth:`close` method once you are finished with the
        camera (e.g. in the ``finally`` section of a ``try..finally`` block).
        This method stops all recording and preview activities and releases all
        resources associated with the camera; this is necessary to prevent GPU
        memory leaks.
        """
        global _CAMERA
        for port in self._encoders:
            self.stop_recording(splitter_port=port)
        assert not self.recording
        if self._splitter_connection:
            mmal.mmal_connection_destroy(self._splitter_connection)
            self._splitter_connection = None
        if self._preview_connection:
            mmal.mmal_connection_destroy(self._preview_connection)
            self._preview_connection = None
        if self._null_sink:
            mmal.mmal_component_destroy(self._null_sink)
            self._null_sink = None
        if self._splitter:
            mmal.mmal_component_destroy(self._splitter)
            self._splitter = None
        if self._preview:
            mmal.mmal_component_destroy(self._preview)
            self._preview = None
        if self._camera:
            mmal.mmal_component_destroy(self._camera)
            self._camera = None
        _CAMERA = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def start_preview(self):
        """
        Displays the preview window.

        This method starts a new preview running at the configured resolution
        (see :attr:`resolution`). Most camera properties can be modified "live"
        while the preview is running (e.g. :attr:`brightness`). The preview
        overrides whatever is currently visible on the display. More
        specifically, the preview does not rely on a graphical environment like
        X-Windows (it can run quite happily from a TTY console); it is simply
        an overlay on the Pi's video output.

        To stop the preview and reveal the display again, call
        :meth:`stop_preview`. The preview can be started and stopped multiple
        times during the lifetime of the :class:`PiCamera` object.

        .. note::
            Because the preview typically obscures the screen, ensure you have
            a means of stopping a preview before starting one. If the preview
            obscures your interactive console you won't be able to Alt+Tab back
            to it as the preview isn't in a window. If you are in an
            interactive Python session, simply pressing Ctrl+D usually suffices
            to terminate the environment, including the camera and its
            associated preview.
        """
        self._check_camera_open()
        # Switch the camera's preview port from the null sink to the
        # preview component
        if self._preview_connection:
            mmal.mmal_connection_destroy(self._preview_connection)
            self._null_connection = None
        self._preview_connection = self._connect_ports(
            self._camera[0].output[self.CAMERA_PREVIEW_PORT],
            self._preview[0].input[0])

    def stop_preview(self):
        """
        Closes the preview window display.

        If :meth:`start_preview` has previously been called, this method shuts
        down the preview display which generally results in the underlying TTY
        becoming visible again. If a preview is not currently running, no
        exception is raised - the method will simply do nothing.
        """
        self._check_camera_open()
        # This is the reverse of start_preview; disconnect the camera from the
        # preview component (if it's connected) and connect it to the null sink
        if self._preview_connection:
            mmal.mmal_connection_destroy(self._preview_connection)
            self._preview_connection = None
        self._preview_connection = self._connect_ports(
            self._camera[0].output[self.CAMERA_PREVIEW_PORT],
            self._null_sink[0].input[0])

    def start_recording(
            self, output, format=None, resize=None, splitter_port=1, **options):
        """
        Start recording video from the camera, storing it in *output*.

        If *output* is a string, it will be treated as a filename for a new
        file which the video will be written to. Otherwise, *output* is assumed
        to be a file-like object and the video data is appended to it (the
        implementation only assumes the object has a ``write()`` method - no
        other methods will be called).

        If *format* is ``None`` (the default), the method will attempt to guess
        the required video format from the extension of *output* (if it's a
        string), or from the *name* attribute of *output* (if it has one). In
        the case that the format cannot be determined, a
        :exc:`PiCameraValueError` will be raised.

        If *format* is not ``None``, it must be a string specifying the format
        that you want the image written to. The format can be a MIME-type or
        one of the following strings:

        * ``'h264'`` - Write an H.264 video stream
        * ``'mjpeg'`` - Write an M-JPEG video stream

        If *resize* is not ``None`` (the default), it must be a two-element
        tuple specifying the width and height that the video recording should
        be resized to. This is particularly useful for recording video using
        the full area of the camera sensor (which is not possible without
        down-sizing the output).

        The *splitter_port* parameter specifies the port of the built-in
        splitter that the video encoder will be attached to. This defaults to
        ``1`` and most users will have no need to specify anything different.
        If you wish to record multiple (presumably resized) streams
        simultaneously, specify a value between ``0`` and ``3`` inclusive for
        this parameter, ensuring that you do not specify a port that is
        currently in use.

        Certain formats accept additional options which can be specified
        as keyword arguments. The ``'h264'`` format accepts the following
        additional options:

        * *profile* - The H.264 profile to use for encoding. Defaults to
          'high', but can be one of 'baseline', 'main', 'high', or
          'constrained'.

        * *intra_period* - The key frame rate (the rate at which I-frames are
          inserted in the output). Defaults to 0, but can be any positive
          32-bit integer value representing the number of frames between
          successive I-frames.

        * *inline_headers* - When ``True``, specifies that the encoder should
          output SPS/PPS headers within the stream to ensure GOPs (groups of
          pictures) are self describing. This is important for streaming
          applications where the client may wish to seek within the stream, and
          enables the use of :meth:`split_recording`. Defaults to ``True`` if
          not specified.

        * *sei* - When ``True``, specifies the encoder should include
          "Supplemental Enhancement Information" within the output stream.
          Defaults to ``False`` if not specified.

        All formats accept the following additional options:

        * *bitrate* - The bitrate at which video will be encoded. Defaults to
          17000000 (17Mbps) if not specified. A value of 0 implies VBR
          (variable bitrate) encoding. The maximum value is 25000000 (25Mbps).

        * *quantization* - When *bitrate* is zero (for variable bitrate
          encodings), this parameter specifies the quality that the encoder
          should attempt to maintain.

          For the ``'h264'`` format, use values between 10 and 40 where 10 is
          extremely high quality, and 40 is extremely low (20-25 is usually a
          reasonable range for H.264 encoding). Note that
          :meth:`split_recording` cannot be used in VBR mode.

        .. versionchanged:: 1.0
            The *resize* parameter was added, and ``'mjpeg'`` was added as a
            recording format

        .. versionchanged:: 1.3
            The *splitter_port* parameter was added
        """
        if splitter_port in self._encoders:
            raise PiCameraRuntimeError(
                    'The camera is already recording on '
                    'port %d' % splitter_port)
        camera_port, output_port = self._get_ports(True, splitter_port)
        format = self._get_video_format(output, format)
        self._still_encoding = mmal.MMAL_ENCODING_I420
        encoder = PiVideoEncoder(
                self, camera_port, output_port, format, resize, **options)
        self._encoders[splitter_port] = encoder
        try:
            encoder.start(output)
        except Exception as e:
            encoder.close()
            del self._encoders[splitter_port]
            raise

    def split_recording(self, output, splitter_port=1):
        """
        Continue the recording in the specified output; close existing output.

        When called, the video encoder will wait for the next appropriate
        split point (an inline SPS header), then will cease writing to the
        current output (and close it, if it was specified as a filename), and
        continue writing to the newly specified *output*.

        If *output* is a string, it will be treated as a filename for a new
        file which the video will be written to. Otherwise, *output* is assumed
        to be a file-like object and the video data is appended to it (the
        implementation only assumes the object has a ``write()`` method - no
        other methods will be called).

        The *splitter_port* parameter specifies which port of the video
        splitter the encoder you wish to change outputs is attached to. This
        defaults to ``1`` and most users will have no need to specify anything
        different. Valid values are between ``0`` and ``3`` inclusive.

        Note that unlike :meth:`start_recording`, you cannot specify format or
        options as these cannot be changed in the middle of recording. Only the
        new *output* can be specified. Furthermore, the format of the recording
        is currently limited to H264, *inline_headers* must be ``True``, and
        *bitrate* must be non-zero (CBR mode) when :meth:`start_recording` is
        called (this is the default).

        .. versionchanged:: 1.3
            The *splitter_port* parameter was added
        """
        try:
            self._encoders[splitter_port].split(output)
        except KeyError:
            raise PiCameraRuntimeError(
                    'There is no recording in progress on '
                    'port %d' % splitter_port)

    def wait_recording(self, timeout=0, splitter_port=1):
        """
        Wait on the video encoder for timeout seconds.

        It is recommended that this method is called while recording to check
        for exceptions. If an error occurs during recording (for example out of
        disk space), an exception will only be raised when the
        :meth:`wait_recording` or :meth:`stop_recording` methods are called.

        If ``timeout`` is 0 (the default) the function will immediately return
        (or raise an exception if an error has occurred).

        The *splitter_port* parameter specifies which port of the video
        splitter the encoder you wish to wait on is attached to. This
        defaults to ``1`` and most users will have no need to specify anything
        different. Valid values are between ``0`` and ``3`` inclusive.

        .. versionchanged:: 1.3
            The *splitter_port* parameter was added
        """
        assert timeout is not None
        try:
            self._encoders[splitter_port].wait(timeout)
        except KeyError:
            raise PiCameraRuntimeError(
                    'There is no recording in progress on '
                    'port %d' % splitter_port)

    def stop_recording(self, splitter_port=1):
        """
        Stop recording video from the camera.

        After calling this method the video encoder will be shut down and
        output will stop being written to the file-like object specified with
        :meth:`start_recording`. If an error occurred during recording and
        :meth:`wait_recording` has not been called since the error then this
        method will raise the exception.

        The *splitter_port* parameter specifies which port of the video
        splitter the encoder you wish to stop is attached to. This defaults to
        ``1`` and most users will have no need to specify anything different.
        Valid values are between ``0`` and ``3`` inclusive.

        .. versionchanged:: 1.3
            The *splitter_port* parameter was added
        """
        try:
            self.wait_recording(0, splitter_port)
        finally:
            encoder = self._encoders[splitter_port]
            del self._encoders[splitter_port]
            encoder.close()

    def record_sequence(
            self, outputs, format='h264', resize=None, splitter_port=1, **options):
        """
        Record a sequence of video clips from the camera.

        This method accepts a sequence or iterator of *outputs* each of which
        must either be a string specifying a filename for output, or a
        file-like object with a ``write`` method.

        The method acts as an iterator itself, yielding each item of the
        sequence in turn. In this way, the caller can control how long to
        record to each item by only permitting the loop to continue when ready
        to switch to the next output.

        The *format*, *splitter_port*, *resize*, and *options* parameters are
        the same as in :meth:`start_recording`, but *format* defaults to
        ``'h264'``.  The format is **not** derived from the filenames in
        *outputs* by this method.

        For example, to record 3 consecutive 10-second video clips, writing the
        output to a series of H.264 files named clip01.h264, clip02.h264, and
        clip03.h264 one could use the following::

            import picamera
            with picamera.PiCamera() as camera:
                for filename in camera.record_sequence([
                        'clip01.h264',
                        'clip02.h264',
                        'clip03.h264']):
                    print('Recording to %s' % filename)
                    camera.wait_recording(10)

        Alternatively, a more flexible method of writing the previous example
        (which is easier to expand to a large number of output files) is by
        using a generator expression as the input sequence::

            import picamera
            with picamera.PiCamera() as camera:
                for filename in camera.record_sequence(
                        'clip%02d.h264' % i for i in range(3)):
                    print('Recording to %s' % filename)
                    camera.wait_recording(10)

        More advanced techniques are also possible by utilising infinite
        sequences, such as those generated by :func:`itertools.cycle`. In the
        following example, recording is switched between two in-memory streams.
        Whilst one stream is recording, the other is being analysed. The script
        only stops recording when a video recording meets some criteria defined
        by the ``process`` function::

            import io
            import itertools
            import picamera
            with picamera.PiCamera() as camera:
                analyse = None
                for stream in camera.record_sequence(
                        itertools.cycle((io.BytesIO(), io.BytesIO()))):
                    if analyse is not None:
                        if process(analyse):
                            break
                        analyse.seek(0)
                        analyse.truncate()
                    camera.wait_recording(5)
                    analyse = stream

        .. versionadded:: 1.3
        """
        if splitter_port in self._encoders:
            raise PiCameraRuntimeError(
                    'The camera is already recording on '
                    'port %d' % splitter_port)
        camera_port, output_port = self._get_ports(True, splitter_port)
        format = self._get_video_format('', format)
        self._still_encoding = mmal.MMAL_ENCODING_I420
        encoder = PiVideoEncoder(
                self, camera_port, output_port, format, resize, **options)
        self._encoders[splitter_port] = encoder
        try:
            start = True
            for output in outputs:
                if start:
                    start = False
                    encoder.start(output)
                else:
                    encoder.split(output)
                yield output
        finally:
            try:
                encoder.wait(0)
            finally:
                del self._encoders[splitter_port]
                encoder.close()

    def capture(
            self, output, format=None, use_video_port=False, resize=None,
            splitter_port=0, **options):
        """
        Capture an image from the camera, storing it in *output*.

        If *output* is a string, it will be treated as a filename for a new
        file which the image will be written to. Otherwise, *output* is assumed
        to a be a file-like object and the image data is appended to it (the
        implementation only assumes the object has a ``write()`` method - no
        other methods will be called).

        If *format* is ``None`` (the default), the method will attempt to guess
        the required image format from the extension of *output* (if it's a
        string), or from the *name* attribute of *output* (if it has one). In
        the case that the format cannot be determined, a
        :exc:`PiCameraValueError` will be raised.

        If *format* is not ``None``, it must be a string specifying the format
        that you want the image written to. The format can be a MIME-type or
        one of the following strings:

        * ``'jpeg'`` - Write a JPEG file

        * ``'png'`` - Write a PNG file

        * ``'gif'`` - Write a GIF file

        * ``'bmp'`` - Write a Windows bitmap file

        * ``'yuv'`` - Write the raw image data to a file in YUV420 format

        * ``'rgb'`` - Write the raw image data to a file in 24-bit RGB format

        * ``'rgba'`` - Write the raw image data to a file in 32-bit RGBA format

        * ``'bgr'`` - Write the raw image data to a file in 24-bit BGR format

        * ``'bgra'`` - Write the raw image data to a file in 32-bit BGRA format

        * ``'raw'`` - Deprecated option for raw captures; the format is taken
          from the deprecated :attr:`raw_format` attribute

        The *use_video_port* parameter controls whether the camera's image or
        video port is used to capture images. It defaults to ``False`` which
        means that the camera's image port is used. This port is slow but
        produces better quality pictures. If you need rapid capture up to the
        rate of video frames, set this to ``True``.

        When *use_video_port* is ``True``, the *splitter_port* parameter
        specifies the port of the video splitter that the image encoder will be
        attached to. This defaults to ``0`` and most users will have no need to
        specify anything different. This parameter is ignored when
        *use_video_port* is ``False``. See :ref:`under_the_hood` for more
        information about the video splitter.

        If *resize* is not ``None`` (the default), it must be a two-element
        tuple specifying the width and height that the image should be resized
        to.

        .. warning::

            If *resize* is specified, or *use_video_port* is ``True``, Exif
            metadata will **not** be included in JPEG output. This is due to an
            underlying firmware limitation.

        Certain file formats accept additional options which can be specified
        as keyword arguments. Currently, only the ``'jpeg'`` encoder accepts
        additional options, which are:

        * *quality* - Defines the quality of the JPEG encoder as an integer
          ranging from 1 to 100. Defaults to 85.

        * *thumbnail* - Defines the size and quality of the thumbnail to embed
          in the Exif metadata. Specifying ``None`` disables thumbnail
          generation.  Otherwise, specify a tuple of ``(width, height,
          quality)``. Defaults to ``(64, 48, 35)``.

        * *bayer* - If ``True``, the raw bayer data from the camera's sensor
          is included in the Exif metadata.

        .. note::

            The so-called "raw" formats listed above (``'yuv'``, ``'rgb'``,
            etc.) do not represent the raw bayer data from the camera's sensor.
            Rather they provide access to the image data after GPU processing,
            but before format encoding (JPEG, PNG, etc). Currently, the only
            method of accessing the raw bayer data is via the *bayer* parameter
            described above.

        .. versionchanged:: 1.0
            The *resize* parameter was added, and raw capture formats can now
            be specified directly

        .. versionchanged:: 1.3
            The *splitter_port* parameter was added, and *bayer* was added as
            an option for the ``'jpeg'`` format

        """
        if use_video_port and (splitter_port in self._encoders):
            raise PiCameraRuntimeError(
                    'The camera is already recording on '
                    'port %d' % splitter_port)
        camera_port, output_port = self._get_ports(use_video_port, splitter_port)
        format = self._get_image_format(output, format)
        if not use_video_port:
            if resize:
                self._still_encoding = mmal.MMAL_ENCODING_I420
            else:
                self._still_encoding = self.RAW_FORMATS.get(
                    format, mmal.MMAL_ENCODING_OPAQUE)
        encoder_class = (
                PiRawOneImageEncoder if format in self.RAW_FORMATS else
                PiCookedOneImageEncoder)
        encoder = encoder_class(
                self, camera_port, output_port, format, resize, **options)
        try:
            encoder.start(output)
            # Wait for the callback to set the event indicating the end of
            # image capture
            if not encoder.wait(30):
                raise PiCameraRuntimeError(
                    'Timed out waiting for capture to end')
        finally:
            encoder.close()
            encoder = None

    def capture_sequence(
            self, outputs, format='jpeg', use_video_port=False, resize=None,
            splitter_port=0, **options):
        """
        Capture a sequence of consecutive images from the camera.

        This method accepts a sequence or iterator of *outputs* each of which
        must either be a string specifying a filename for output, or a
        file-like object with a ``write`` method. For each item in the sequence
        or iterator of outputs, the camera captures a single image as fast as
        it can.

        The *format*, *use_video_port*, *splitter_port*, *resize*, and
        *options* parameters are the same as in :meth:`capture`, but *format*
        defaults to ``'jpeg'``.  The format is **not** derived from the
        filenames in *outputs* by this method.

        For example, to capture 3 consecutive images::

            import time
            import picamera
            with picamera.PiCamera() as camera:
                camera.start_preview()
                time.sleep(2)
                camera.capture_sequence([
                    'image1.jpg',
                    'image2.jpg',
                    'image3.jpg',
                    ])
                camera.stop_preview()

        If you wish to capture a large number of images, a list comprehension
        or generator expression can be used to construct the list of filenames
        to use::

            import time
            import picamera
            with picamera.PiCamera() as camera:
                camera.start_preview()
                time.sleep(2)
                camera.capture_sequence([
                    'image%02d.jpg' % i
                    for i in range(100)
                    ])
                camera.stop_preview()

        More complex effects can be obtained by using a generator function to
        provide the filenames or output objects.

        .. versionchanged:: 1.0
            The *resize* parameter was added, and raw capture formats can now
            be specified directly

        .. versionchanged:: 1.3
            The *splitter_port* parameter was added
        """
        if use_video_port and (splitter_port in self._encoders):
            raise PiCameraRuntimeError(
                    'The camera is already recording on '
                    'port %d' % splitter_port)
        camera_port, output_port = self._get_ports(use_video_port, splitter_port)
        format = self._get_image_format('', format)
        if format == 'jpeg' and not use_video_port and not resize:
            self._still_encoding = mmal.MMAL_ENCODING_OPAQUE
        else:
            self._still_encoding = mmal.MMAL_ENCODING_I420
        if use_video_port:
            encoder_class = (
                    PiRawMultiImageEncoder if format in self.RAW_FORMATS else
                    PiCookedMultiImageEncoder)
            encoder = encoder_class(
                    self, camera_port, output_port, format, resize, **options)
            try:
                encoder.start(outputs)
                encoder.wait()
            finally:
                encoder.close()
        else:
            encoder_class = (
                    PiRawOneImageEncoder if format in self.RAW_FORMATS else
                    PiCookedOneImageEncoder)
            encoder = encoder_class(
                    self, camera_port, output_port, format, resize, **options)
            try:
                for output in outputs:
                    encoder.start(output)
                    if not encoder.wait(30):
                        raise PiCameraRuntimeError(
                            'Timed out waiting for capture to end')
            finally:
                encoder.close()

    def capture_continuous(
            self, output, format=None, use_video_port=False, resize=None,
            splitter_port=0, **options):
        """
        Capture images continuously from the camera as an infinite iterator.

        This method returns an infinite iterator of images captured
        continuously from the camera. If *output* is a string, each captured
        image is stored in a file named after *output* after substitution of
        two values with the :meth:`~str.format` method. Those two values are:

        * ``{counter}`` - a simple incrementor that starts at 1 and increases
          by 1 for each image taken

        * ``{timestamp}`` - a :class:`~datetime.datetime` instance

        The table below contains several example values of *output* and the
        sequence of filenames those values could produce:

        +--------------------------------------------+--------------------------------------------+-------+
        | *output* Value                             | Filenames                                  | Notes |
        +============================================+============================================+=======+
        | ``'image{counter}.jpg'``                   | image1.jpg, image2.jpg, image3.jpg, ...    |       |
        +--------------------------------------------+--------------------------------------------+-------+
        | ``'image{counter:02d}.jpg'``               | image01.jpg, image02.jpg, image03.jpg, ... |       |
        +--------------------------------------------+--------------------------------------------+-------+
        | ``'image{timestamp}.jpg'``                 | image2013-10-05 12:07:12.346743.jpg,       | (1)   |
        |                                            | image2013-10-05 12:07:32.498539, ...       |       |
        +--------------------------------------------+--------------------------------------------+-------+
        | ``'image{timestamp:%H-%M-%S-%f}.jpg'``     | image12-10-02-561527.jpg,                  |       |
        |                                            | image12-10-14-905398.jpg                   |       |
        +--------------------------------------------+--------------------------------------------+-------+
        | ``'{timestamp:%H%M%S}-{counter:03d}.jpg'`` | 121002-001.jpg, 121013-002.jpg,            | (2)   |
        |                                            | 121014-003.jpg, ...                        |       |
        +--------------------------------------------+--------------------------------------------+-------+

        1. Note that because timestamp's default output includes colons (:),
           the resulting filenames are not suitable for use on Windows. For
           this reason (and the fact the default contains spaces) it is
           strongly recommended you always specify a format when using
           ``{timestamp}``.

        2. You can use both ``{timestamp}`` and ``{counter}`` in a single
           format string (multiple times too!) although this tends to be
           redundant.

        If *output* is not a string, it is assumed to be a file-like object
        and each image is simply written to this object sequentially. In this
        case you will likely either want to write something to the object
        between the images to distinguish them, or clear the object between
        iterations.

        The *format*, *use_video_port*, *splitter_port*, *resize*, and
        *options* parameters are the same as in :meth:`capture`.

        For example, to capture 60 images with a one second delay between them,
        writing the output to a series of JPEG files named image01.jpg,
        image02.jpg, etc. one could do the following::

            import time
            import picamera
            with picamera.PiCamera() as camera:
                camera.start_preview()
                try:
                    for i, filename in enumerate(camera.capture_continuous('image{counter:02d}.jpg')):
                        print(filename)
                        time.sleep(1)
                        if i == 59:
                            break
                finally:
                    camera.stop_preview()

        Alternatively, to capture JPEG frames as fast as possible into an
        in-memory stream, performing some processing on each stream until
        some condition is satisfied::

            import io
            import time
            import picamera
            with picamera.PiCamera() as camera:
                stream = io.BytesIO()
                for foo in camera.capture_continuous(stream, format='jpeg'):
                    # Truncate the stream to the current position (in case
                    # prior iterations output a longer image)
                    stream.truncate()
                    stream.seek(0)
                    if process(stream):
                        break

        .. versionchanged:: 1.0
            The *resize* parameter was added, and raw capture formats can now
            be specified directly

        .. versionchanged:: 1.3
            The *splitter_port* parameter was added
        """
        if use_video_port and (splitter_port in self._encoders):
            raise PiCameraRuntimeError(
                    'The camera is already recording on '
                    'port %d' % splitter_port)
        camera_port, output_port = self._get_ports(use_video_port, splitter_port)
        format = self._get_image_format(output, format)
        if format == 'jpeg' and not use_video_port and not resize:
            self._still_encoding = mmal.MMAL_ENCODING_OPAQUE
        else:
            self._still_encoding = mmal.MMAL_ENCODING_I420
        encoder_class = (
                PiRawOneImageEncoder if format in self.RAW_FORMATS else
                PiCookedOneImageEncoder)
        encoder = encoder_class(
                self, camera_port, output_port, format, resize, **options)
        try:
            if isinstance(output, bytes):
                # If we're fed a bytes string, assume it's UTF-8 encoded and
                # convert it to Unicode. Technically this is wrong
                # (file-systems use all sorts of encodings), but UTF-8 is a
                # reasonable default and this keeps compatibility with Python 2
                # simple although it breaks the edge cases of non-UTF-8 encoded
                # bytes strings with non-UTF-8 encoded file-systems
                output = output.decode('utf-8')
            if isinstance(output, str):
                counter = 1
                while True:
                    filename = output.format(
                        counter=counter,
                        timestamp=datetime.datetime.now(),
                        )
                    encoder.start(filename)
                    if not encoder.wait(30):
                        raise PiCameraRuntimeError(
                            'Timed out waiting for capture to end')
                    yield filename
                    counter += 1
            else:
                while True:
                    encoder.start(output)
                    if not encoder.wait(30):
                        raise PiCameraRuntimeError(
                            'Timed out waiting for capture to end')
                    yield output
        finally:
            encoder.close()

    @property
    def closed(self):
        """
        Returns ``True`` if the :meth:`close` method has been called.
        """
        return not self._camera

    @property
    def recording(self):
        """
        Returns ``True`` if the :meth:`start_recording` method has been called,
        and no :meth:`stop_recording` call has been made yet.
        """
        # XXX Should probably check this is actually enabled...
        return bool(self._encoders)

    @property
    def previewing(self):
        """
        Returns ``True`` if the :meth:`start_preview` method has been called,
        and no :meth:`stop_preview` call has been made yet.
        """
        return (
                bool(self._preview_connection)
                and self._preview_connection[0].is_enabled
                and self._preview_connection[0].in_[0].name.startswith(
                    mmal.MMAL_COMPONENT_DEFAULT_VIDEO_RENDERER)
                )

    @property
    def exif_tags(self):
        """
        Holds a mapping of the Exif tags to apply to captured images.

        .. note::

            Please note that Exif tagging is only supported with the ``jpeg``
            format.

        By default several Exif tags are automatically applied to any images
        taken with the :meth:`capture` method: ``IFD0.Make`` (which is set to
        ``RaspberryPi``), ``IFD0.Model`` (which is set to ``RP_OV5647``), and
        three timestamp tags: ``IFD0.DateTime``, ``EXIF.DateTimeOriginal``, and
        ``EXIF.DateTimeDigitized`` which are all set to the current date and
        time just before the picture is taken.

        If you wish to set additional Exif tags, or override any of the
        aforementioned tags, simply add entries to the exif_tags map before
        calling :meth:`capture`. For example::

            camera.exif_tags['IFD0.Copyright'] = 'Copyright (c) 2013 Foo Industries'

        The Exif standard mandates ASCII encoding for all textual values, hence
        strings containing non-ASCII characters will cause an encoding error to
        be raised when :meth:`capture` is called.  If you wish to set binary
        values, use a :func:`bytes` value::

            camera.exif_tags['EXIF.UserComment'] = b'Something containing\\x00NULL characters'

        .. warning::

            Binary Exif values are currently ignored; this appears to be a
            libmmal or firmware bug.

        You may also specify datetime values, integer, or float values, all of
        which will be converted to appropriate ASCII strings (datetime values
        are formatted as ``YYYY:MM:DD HH:MM:SS`` in accordance with the Exif
        standard).

        The currently supported Exif tags are:

        +-------+-------------------------------------------------------------+
        | Group | Tags                                                        |
        +=======+=============================================================+
        | IFD0, | ImageWidth, ImageLength, BitsPerSample, Compression,        |
        | IFD1  | PhotometricInterpretation, ImageDescription, Make, Model,   |
        |       | StripOffsets, Orientation, SamplesPerPixel, RowsPerString,  |
        |       | StripByteCounts, Xresolution, Yresolution,                  |
        |       | PlanarConfiguration, ResolutionUnit, TransferFunction,      |
        |       | Software, DateTime, Artist, WhitePoint,                     |
        |       | PrimaryChromaticities, JPEGInterchangeFormat,               |
        |       | JPEGInterchangeFormatLength, YcbCrCoefficients,             |
        |       | YcbCrSubSampling, YcbCrPositioning, ReferenceBlackWhite,    |
        |       | Copyright                                                   |
        +-------+-------------------------------------------------------------+
        | EXIF  | ExposureTime, FNumber, ExposureProgram,                     |
        |       | SpectralSensitivity, ISOSpeedRatings, OECF, ExifVersion,    |
        |       | DateTimeOriginal, DateTimeDigitized,                        |
        |       | ComponentsConfiguration, CompressedBitsPerPixel,            |
        |       | ShutterSpeedValue, ApertureValue, BrightnessValue,          |
        |       | ExposureBiasValue, MaxApertureValue, SubjectDistance,       |
        |       | MeteringMode, LightSource, Flash, FocalLength, SubjectArea, |
        |       | MakerNote, UserComment, SubSecTime, SubSecTimeOriginal,     |
        |       | SubSecTimeDigitized, FlashpixVersion, ColorSpace,           |
        |       | PixelXDimension, PixelYDimension, RelatedSoundFile,         |
        |       | FlashEnergy, SpacialFrequencyResponse,                      |
        |       | FocalPlaneXResolution, FocalPlaneYResolution,               |
        |       | FocalPlaneResolutionUnit, SubjectLocation, ExposureIndex,   |
        |       | SensingMethod, FileSource, SceneType, CFAPattern,           |
        |       | CustomRendered, ExposureMode, WhiteBalance,                 |
        |       | DigitalZoomRatio, FocalLengthIn35mmFilm, SceneCaptureType,  |
        |       | GainControl, Contrast, Saturation, Sharpness,               |
        |       | DeviceSettingDescription, SubjectDistanceRange,             |
        |       | ImageUniqueID                                               |
        +-------+-------------------------------------------------------------+
        | GPS   | GPSVersionID, GPSLatitudeRef, GPSLatitude, GPSLongitudeRef, |
        |       | GPSLongitude, GPSAltitudeRef, GPSAltitude, GPSTimeStamp,    |
        |       | GPSSatellites, GPSStatus, GPSMeasureMode, GPSDOP,           |
        |       | GPSSpeedRef, GPSSpeed, GPSTrackRef, GPSTrack,               |
        |       | GPSImgDirectionRef, GPSImgDirection, GPSMapDatum,           |
        |       | GPSDestLatitudeRef, GPSDestLatitude, GPSDestLongitudeRef,   |
        |       | GPSDestLongitude, GPSDestBearingRef, GPSDestBearing,        |
        |       | GPSDestDistanceRef, GPSDestDistance, GPSProcessingMethod,   |
        |       | GPSAreaInformation, GPSDateStamp, GPSDifferential           |
        +-------+-------------------------------------------------------------+
        | EINT  | InteroperabilityIndex, InteroperabilityVersion,             |
        |       | RelatedImageFileFormat, RelatedImageWidth,                  |
        |       | RelatedImageLength                                          |
        +-------+-------------------------------------------------------------+
        """
        return self._exif_tags

    def _set_led(self, value):
        if not self._used_led:
            self._init_led()
        if not GPIO:
            raise PiCameraRuntimeError(
                "GPIO library not found, or not accessible; please install "
                "RPi.GPIO and run the script as root")
        GPIO.output(5, bool(value))
    led = property(None, _set_led, doc="""
        Sets the state of the camera's LED via GPIO.

        If a GPIO library is available (only RPi.GPIO is currently supported),
        and if the python process has the necessary privileges (typically this
        means running as root via sudo), this property can be used to set the
        state of the camera's LED as a boolean value (``True`` is on, ``False``
        is off).

        .. note::

            This is a write-only property. While it can be used to control the
            camera's LED, you cannot query the state of the camera's LED using
            this property.
        """)

    def _get_raw_format(self):
        return self._raw_format
    def _set_raw_format(self, value):
        warnings.warn(
            'PiCamera.raw_format is deprecated; use required format directly '
            'with capture methods instead', DeprecationWarning)
        try:
            self.RAW_FORMATS[value]
        except KeyError:
            raise PiCameraValueError("Invalid raw format: %s" % value)
        self._raw_format = value
    raw_format = property(_get_raw_format, _set_raw_format, doc="""
        Retrieves or sets the raw format of the camera's ports.

        .. deprecated:: 1.0
            Please use ``'yuv'`` or ``'rgb'`` directly as a format in the
            various capture methods instead.
        """)

    def _get_frame(self):
        # XXX This is rather messy; see if we can't come up with a better
        # design in 2.0
        if not self._encoders:
            raise PiCameraRuntimeError(
                "Cannot query frame information when camera is not recording")
        elif len(self._encoders) == 1:
            return next(iter(self._encoders.values())).frame
        else:
            return {
                    port: encoder.frame
                    for (port, encoder) in self._encoders.items()
                    }
    frame = property(_get_frame, doc="""
        Retrieves information about the current frame recorded from the camera.

        When video recording is active (after a call to
        :meth:`start_recording`), this attribute will return a
        :class:`PiVideoFrame` tuple containing information about the current
        frame that the camera is recording.

        If multiple video recordings are currently in progress (after multiple
        calls to :meth:`start_recording` with different values for the
        ``splitter_port`` parameter), this attribute will return a
        :class:`dict` mapping active port numbers to a :class:`PiVideoFrame`
        tuples.

        Querying this property when the camera is not recording will result in
        an exception.

        .. note::

            There is a small window of time when querying this attribute will
            return ``None`` after calling :meth:`start_recording`. If this
            attribute returns ``None``, this means that the video encoder has
            been initialized, but the camera has not yet returned any frames.
        """)

    def _get_framerate(self):
        self._check_camera_open()
        fmt = self._camera[0].output[self.CAMERA_VIDEO_PORT][0].format[0].es[0]
        return PiCameraFraction(fmt.video.frame_rate.num, fmt.video.frame_rate.den)
    def _set_framerate(self, value):
        self._check_camera_open()
        self._check_recording_stopped()
        n, d = to_rational(value)
        if not (0 <= n / d <= 90):
            raise PiCameraValueError("Invalid framerate: %.2ffps" % (n / d))
        self._disable_camera()
        for port in (self.CAMERA_VIDEO_PORT, self.CAMERA_PREVIEW_PORT):
            fmt = self._camera[0].output[port][0].format[0].es[0]
            fmt.video.frame_rate.num = n
            fmt.video.frame_rate.den = d
            mmal_check(
                mmal.mmal_port_format_commit(self._camera[0].output[port]),
                prefix="Camera video format couldn't be set")
        self._enable_camera()
    framerate = property(_get_framerate, _set_framerate, doc="""
        Retrieves or sets the framerate at which video-port based image
        captures, video recordings, and previews will run.

        When queried, the :attr:`framerate` property returns the rate at which
        the camera's video and preview ports will operate as a
        :class:`~fractions.Fraction` instance which can be easily converted to
        an :class:`int` or :class:`float`.

        .. note::

            For backwards compatibility, a derivative of the
            :class:`~fractions.Fraction` class is actually used which permits
            the value to be treated as a tuple of ``(numerator, denominator)``.

        When set, the property reconfigures the camera so that the next call to
        recording and previewing methods will use the new framerate.  The
        framerate can be specified as an :class:`int`, :class:`float`,
        :class:`~fractions.Fraction`, or a ``(numerator, denominator)`` tuple.
        The camera must not be closed, and no recording must be active when the
        property is set.

        .. note::

            This attribute, in combination with :attr:`resolution`, determines
            the mode that the camera operates in. The actual sensor framerate
            and resolution used by the camera is influenced, but not directly
            set, by this property. See :ref:`camera_modes` for more
            information.
        """)

    def _get_resolution(self):
        self._check_camera_open()
        return (
            int(self._camera_config.max_stills_w),
            int(self._camera_config.max_stills_h)
            )
    def _set_resolution(self, value):
        self._check_camera_open()
        self._check_recording_stopped()
        n, d = self.framerate
        try:
            w, h = value
        except (TypeError, ValueError) as e:
            raise PiCameraValueError(
                "Invalid resolution (width, height) tuple: %s" % value)
        self._disable_camera()
        self._camera_config.max_stills_w = w
        self._camera_config.max_stills_h = h
        self._camera_config.max_preview_video_w = w
        self._camera_config.max_preview_video_h = h
        mmal_check(
            mmal.mmal_port_parameter_set(self._camera[0].control, self._camera_config.hdr),
            prefix="Failed to set preview resolution")
        for port in (self.CAMERA_CAPTURE_PORT, self.CAMERA_VIDEO_PORT, self.CAMERA_PREVIEW_PORT):
            fmt = self._camera[0].output[port][0].format[0].es[0]
            fmt.video.width = mmal.VCOS_ALIGN_UP(w, 32)
            fmt.video.height = mmal.VCOS_ALIGN_UP(h, 16)
            fmt.video.crop.x = 0
            fmt.video.crop.y = 0
            fmt.video.crop.width = w
            fmt.video.crop.height = h
            if port != self.CAMERA_CAPTURE_PORT:
                fmt.video.frame_rate.num = n
                fmt.video.frame_rate.den = d
            mmal_check(
                mmal.mmal_port_format_commit(self._camera[0].output[port]),
                prefix="Camera video format couldn't be set")
        self._enable_camera()
    resolution = property(_get_resolution, _set_resolution, doc="""
        Retrieves or sets the resolution at which image captures, video
        recordings, and previews will be captured.

        When queried, the :attr:`resolution` property returns the resolution at
        which the camera will operate as a tuple of ``(width, height)``
        measured in pixels. This is the resolution that the :meth:`capture`
        method will produce images at, and the resolution that
        :meth:`start_recording` will produce videos at.

        When set, the property reconfigures the camera so that the next call to
        these methods will use the new resolution.  The resolution must be
        specified as a ``(width, height)`` tuple, the camera must not be
        closed, and no recording must be active when the property is set.

        The property defaults to the Pi's currently configured display
        resolution.

        .. note::

            This attribute, in combination with :attr:`framerate`, determines
            the mode that the camera operates in. The actual sensor framerate
            and resolution used by the camera is influenced, but not directly
            set, by this property. See :ref:`camera_modes` for more
            information.
        """)

    def _get_still_encoding(self):
        self._check_camera_open()
        port = self._camera[0].output[self.CAMERA_CAPTURE_PORT]
        return port[0].format[0].encoding
    def _set_still_encoding(self, value):
        self._check_camera_open()
        if value == self._still_encoding.value:
            return
        self._check_recording_stopped()
        self._disable_camera()
        port = self._camera[0].output[self.CAMERA_CAPTURE_PORT]
        port[0].format[0].encoding = value
        if value == mmal.MMAL_ENCODING_OPAQUE:
            port[0].format[0].encoding_variant = mmal.MMAL_ENCODING_I420
        else:
            port[0].format[0].encoding_variant = value
        mmal_check(
            mmal.mmal_port_format_commit(port),
            prefix="Couldn't set capture port encoding")
        # buffer_num and buffer_size are increased by port_format_commit, if
        # they are less than the minimum, but they are not decreased. I420 uses
        # a few very large buffers, while OPQV requires lots of very small
        # buffers. Therefore, after a switch to OPQV and back to I420, ENOMEM
        # can be raised on subsequent captures. Unfortunately, there is an
        # upstream issue with the buffer_num_recommended which means it can't
        # currently be used (see discussion in raspberrypi/userland#167)
        port[0].buffer_num = port[0].buffer_num_min
        port[0].buffer_size = port[0].buffer_size_recommended
        self._enable_camera()
    _still_encoding = property(_get_still_encoding, _set_still_encoding, doc="""
        Configures the encoding of the camera's still port.

        This attribute is intended for internal use only.
        """)

    def _get_saturation(self):
        self._check_camera_open()
        mp = mmal.MMAL_RATIONAL_T()
        mmal_check(
            mmal.mmal_port_parameter_get_rational(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_SATURATION,
                mp
                ),
            prefix="Failed to get saturation")
        return mp.num
    def _set_saturation(self, value):
        self._check_camera_open()
        try:
            if not (-100 <= value <= 100):
                raise PiCameraValueError(
                    "Invalid saturation value: %d (valid range -100..100)" % value)
        except TypeError:
            raise PiCameraValueError("Invalid saturation value: %s" % value)
        mmal_check(
            mmal.mmal_port_parameter_set_rational(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_SATURATION,
                mmal.MMAL_RATIONAL_T(value, 100)
                ),
            prefix="Failed to set saturation")
    saturation = property(_get_saturation, _set_saturation, doc="""
        Retrieves or sets the saturation setting of the camera.

        When queried, the :attr:`saturation` property returns the color
        saturation of the camera as an integer between -100 and 100. When set,
        the property adjusts the saturation of the camera. Saturation can be
        adjusted while previews or recordings are in progress. The default
        value is 0.
        """)

    def _get_sharpness(self):
        self._check_camera_open()
        mp = mmal.MMAL_RATIONAL_T()
        mmal_check(
            mmal.mmal_port_parameter_get_rational(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_SHARPNESS,
                mp
                ),
            prefix="Failed to get sharpness")
        return mp.num
    def _set_sharpness(self, value):
        self._check_camera_open()
        try:
            if not (-100 <= value <= 100):
                raise PiCameraValueError(
                    "Invalid sharpness value: %d (valid range -100..100)" % value)
        except TypeError:
            raise PiCameraValueError("Invalid sharpness value: %s" % value)
        mmal_check(
            mmal.mmal_port_parameter_set_rational(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_SHARPNESS,
                mmal.MMAL_RATIONAL_T(value, 100)
                ),
            prefix="Failed to set sharpness")
    sharpness = property(_get_sharpness, _set_sharpness, doc="""
        Retrieves or sets the sharpness setting of the camera.

        When queried, the :attr:`sharpness` property returns the sharpness
        level of the camera (a measure of the amount of post-processing to
        reduce or increase image sharpness) as an integer between -100 and 100.
        When set, the property adjusts the sharpness of the camera. Sharpness
        can be adjusted while previews or recordings are in progress. The
        default value is 0.
        """)

    def _get_contrast(self):
        self._check_camera_open()
        mp = mmal.MMAL_RATIONAL_T()
        mmal_check(
            mmal.mmal_port_parameter_get_rational(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_CONTRAST,
                mp
                ),
            prefix="Failed to get contrast")
        return mp.num
    def _set_contrast(self, value):
        self._check_camera_open()
        try:
            if not (-100 <= value <= 100):
                raise PiCameraValueError(
                    "Invalid contrast value: %d (valid range -100..100)" % value)
        except TypeError:
            raise PiCameraValueError("Invalid contrast value: %s" % value)
        mmal_check(
            mmal.mmal_port_parameter_set_rational(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_CONTRAST,
                mmal.MMAL_RATIONAL_T(value, 100)
                ),
            prefix="Failed to set contrast")
    contrast = property(_get_contrast, _set_contrast, doc="""
        Retrieves or sets the contrast setting of the camera.

        When queried, the :attr:`contrast` property returns the contrast level
        of the camera as an integer between -100 and 100.  When set, the
        property adjusts the contrast of the camera. Contrast can be adjusted
        while previews or recordings are in progress. The default value is 0.
        """)

    def _get_brightness(self):
        self._check_camera_open()
        mp = mmal.MMAL_RATIONAL_T()
        mmal_check(
            mmal.mmal_port_parameter_get_rational(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_BRIGHTNESS,
                mp
                ),
            prefix="Failed to get brightness")
        return mp.num
    def _set_brightness(self, value):
        self._check_camera_open()
        try:
            if not (0 <= value <= 100):
                raise PiCameraValueError(
                    "Invalid brightness value: %d (valid range 0..100)" % value)
        except TypeError:
            raise PiCameraValueError("Invalid brightness value: %s" % value)
        mmal_check(
            mmal.mmal_port_parameter_set_rational(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_BRIGHTNESS,
                mmal.MMAL_RATIONAL_T(value, 100)
                ),
            prefix="Failed to set brightness")
    brightness = property(_get_brightness, _set_brightness, doc="""
        Retrieves or sets the brightness setting of the camera.

        When queried, the :attr:`brightness` property returns the brightness
        level of the camera as an integer between 0 and 100.  When set, the
        property adjusts the brightness of the camera. Brightness can be
        adjusted while previews or recordings are in progress. The default
        value is 50.
        """)

    def _get_shutter_speed(self):
        self._check_camera_open()
        mp = ct.c_uint32()
        mmal_check(
            mmal.mmal_port_parameter_get_uint32(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_SHUTTER_SPEED,
                mp
                ),
            prefix="Failed to get shutter speed")
        return mp.value
    def _set_shutter_speed(self, value):
        self._check_camera_open()
        # XXX Valid values?
        mmal_check(
            mmal.mmal_port_parameter_set_uint32(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_SHUTTER_SPEED,
                value
                ),
            prefix="Failed to set shutter speed")
    shutter_speed = property(_get_shutter_speed, _set_shutter_speed, doc="""
        Retrieves or sets the shutter speed of the camera in microseconds.

        When queried, the :attr:`shutter_speed` property returns the shutter
        speed of the camera in microseconds, or 0 which indicates that the
        speed will be automatically determined according to lighting
        conditions. Faster shutter times naturally require greater amounts of
        illumination and vice versa.

        When set, the property adjusts the shutter speed of the camera, which
        most obviously affects the illumination of subsequently captured
        images. Shutter speed can be adjusted while previews or recordings are
        running. The default value is 0 (auto).
        """)

    def _get_ISO(self):
        self._check_camera_open()
        mp = ct.c_uint32()
        mmal_check(
            mmal.mmal_port_parameter_get_uint32(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_ISO,
                mp
                ),
            prefix="Failed to get ISO")
        return mp.value
    def _set_ISO(self, value):
        self._check_camera_open()
        try:
            if not (0 <= value <= 800):
                raise PiCameraValueError(
                    "Invalid ISO value: %d (valid range 0..800)" % value)
        except TypeError:
            raise PiCameraValueError("Invalid ISO value: %s" % value)
        mmal_check(
            mmal.mmal_port_parameter_set_uint32(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_ISO,
                value
                ),
            prefix="Failed to set ISO")
    ISO = property(_get_ISO, _set_ISO, doc="""
        Retrieves or sets the apparent ISO setting of the camera.

        When queried, the :attr:`ISO` property returns the ISO setting of the
        camera, a value which represents the `sensitivity of the camera to
        light`_. Lower ISO speeds (e.g. 100) imply less sensitivity than higher
        ISO speeds (e.g. 400 or 800). Lower sensitivities tend to produce less
        "noisy" (smoother) images, but operate poorly in low light conditions.

        When set, the property adjusts the sensitivity of the camera. Valid
        values are between 0 (auto) and 800. The actual value used when ISO is
        explicitly set will be one of the following values (whichever is
        closest): 100, 200, 320, 400, 500, 640, 800.

        ISO can be adjusted while previews or recordings are in progress. The
        default value is 0 which means the ISO is automatically set according
        to image-taking conditions.

        .. note::

            With ISO settings other than 0 (auto), the :attr:`exposure_mode`
            property becomes non-functional.

        .. _sensitivity of the camera to light: http://en.wikipedia.org/wiki/Film_speed#Digital
        """)

    def _get_meter_mode(self):
        self._check_camera_open()
        mp = mmal.MMAL_PARAMETER_EXPOSUREMETERINGMODE_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_EXP_METERING_MODE,
                ct.sizeof(mmal.MMAL_PARAMETER_EXPOSUREMETERINGMODE_T)
                ))
        mmal_check(
            mmal.mmal_port_parameter_get(self._camera[0].control, mp.hdr),
            prefix="Failed to get meter mode")
        return self._METER_MODES_R[mp.value]
    def _set_meter_mode(self, value):
        self._check_camera_open()
        try:
            mp = mmal.MMAL_PARAMETER_EXPOSUREMETERINGMODE_T(
                mmal.MMAL_PARAMETER_HEADER_T(
                    mmal.MMAL_PARAMETER_EXP_METERING_MODE,
                    ct.sizeof(mmal.MMAL_PARAMETER_EXPOSUREMETERINGMODE_T)
                    ),
                self.METER_MODES[value]
                )
            mmal_check(
                mmal.mmal_port_parameter_set(self._camera[0].control, mp.hdr),
                prefix="Failed to set meter mode")
        except KeyError:
            raise PiCameraValueError("Invalid metering mode: %s" % value)
    meter_mode = property(_get_meter_mode, _set_meter_mode, doc="""
        Retrieves or sets the metering mode of the camera.

        When queried, the :attr:`meter_mode` property returns the method by
        which the camera `determines the exposure`_ as one of the following
        strings:

        +---------------+---------------------------------------------------+
        | Value         | Description                                       |
        +===============+===================================================+
        | ``'average'`` | The camera measures the average of the entire     |
        |               | scene.                                            |
        +---------------+---------------------------------------------------+
        | ``'spot'``    | The camera measures the center of the scene.      |
        +---------------+---------------------------------------------------+
        | ``'backlit'`` | The camera measures a larger central area,        |
        |               | ignoring the edges of the scene.                  |
        +---------------+---------------------------------------------------+
        | ``'matrix'``  | The camera measures several points within the     |
        |               | scene.                                            |
        +---------------+---------------------------------------------------+

        When set, the property adjusts the camera's metering mode. The property
        can be set while recordings or previews are in progress. The default
        value is ``'average'``. All possible values for the attribute can be
        obtained from the ``PiCamera.METER_MODES`` attribute.

        .. _determines the exposure: http://en.wikipedia.org/wiki/Metering_mode
        """)

    def _get_video_stabilization(self):
        self._check_camera_open()
        mp = mmal.MMAL_BOOL_T()
        mmal_check(
            mmal.mmal_port_parameter_get_boolean(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_VIDEO_STABILISATION,
                mp
                ),
            prefix="Failed to get video stabilization")
        return mp.value != mmal.MMAL_FALSE
    def _set_video_stabilization(self, value):
        self._check_camera_open()
        try:
            mmal_check(
                mmal.mmal_port_parameter_set_boolean(
                    self._camera[0].control,
                    mmal.MMAL_PARAMETER_VIDEO_STABILISATION,
                    {
                        False: mmal.MMAL_FALSE,
                        True:  mmal.MMAL_TRUE,
                        }[value]
                    ),
                prefix="Failed to set video stabilization")
        except KeyError:
            raise PiCameraValueError(
                "Invalid video stabilization boolean value: %s" % value)
    video_stabilization = property(
        _get_video_stabilization, _set_video_stabilization, doc="""
        Retrieves or sets the video stabilization mode of the camera.

        When queried, the :attr:`video_stabilization` property returns a
        boolean value indicating whether or not the camera attempts to
        compensate for motion.

        When set, the property activates or deactivates video stabilization.
        The property can be set while recordings or previews are in progress.
        The default value is ``False``.

        .. note::

            The built-in video stabilization only accounts for `vertical and
            horizontal motion`_, not rotation.

        .. _vertical and horizontal motion: http://www.raspberrypi.org/phpBB3/viewtopic.php?p=342667&sid=ec7d95e887ab74a90ffaab87888c48cd#p342667
        """)

    def _get_exposure_compensation(self):
        self._check_camera_open()
        mp = ct.c_int32()
        mmal_check(
            mmal.mmal_port_parameter_get_int32(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_EXPOSURE_COMP,
                mp
                ),
            prefix="Failed to get exposure compensation")
        return mp.value
    def _set_exposure_compensation(self, value):
        self._check_camera_open()
        try:
            if not (-25 <= value <= 25):
                raise PiCameraValueError(
                    "Invalid exposure compensation value: "
                    "%d (valid range -25..25)" % value)
        except TypeError:
            raise PiCameraValueError(
                "Invalid exposure compensation value: %s" % value)
        mmal_check(
            mmal.mmal_port_parameter_set_int32(
                self._camera[0].control,
                mmal.MMAL_PARAMETER_EXPOSURE_COMP,
                value
                ),
            prefix="Failed to set exposure compensation")
    exposure_compensation = property(
        _get_exposure_compensation, _set_exposure_compensation, doc="""
        Retrieves or sets the exposure compensation level of the camera.

        When queried, the :attr:`exposure_compensation` property returns an
        integer value between -25 and 25 indicating the exposure level of the
        camera. Larger values result in brighter images.

        When set, the property adjusts the camera's exposure compensation
        level. Each increment represents 1/6th of a stop. Hence setting the
        attribute to 6 increases exposure by 1 stop. The property can be set
        while recordings or previews are in progress. The default value is 0.
        """)

    def _get_exposure_mode(self):
        self._check_camera_open()
        mp = mmal.MMAL_PARAMETER_EXPOSUREMODE_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_EXPOSURE_MODE,
                ct.sizeof(mmal.MMAL_PARAMETER_EXPOSUREMODE_T)
                ))
        mmal_check(
            mmal.mmal_port_parameter_get(self._camera[0].control, mp.hdr),
            prefix="Failed to get exposure mode")
        return self._EXPOSURE_MODES_R[mp.value]
    def _set_exposure_mode(self, value):
        self._check_camera_open()
        try:
            mp = mmal.MMAL_PARAMETER_EXPOSUREMODE_T(
                mmal.MMAL_PARAMETER_HEADER_T(
                    mmal.MMAL_PARAMETER_EXPOSURE_MODE,
                    ct.sizeof(mmal.MMAL_PARAMETER_EXPOSUREMODE_T)
                    ),
                self.EXPOSURE_MODES[value]
                )
            mmal_check(
                mmal.mmal_port_parameter_set(self._camera[0].control, mp.hdr),
                prefix="Failed to set exposure mode")
        except KeyError:
            raise PiCameraValueError("Invalid exposure mode: %s" % value)
    exposure_mode = property(_get_exposure_mode, _set_exposure_mode, doc="""
        Retrieves or sets the exposure mode of the camera.

        When queried, the :attr:`exposure_mode` property returns a string
        representing the exposure setting of the camera. The possible values
        can be obtained from the ``PiCamera.EXPOSURE_MODES`` attribute.

        When set, the property adjusts the camera's exposure mode.  The
        property can be set while recordings or previews are in progress. The
        default value is ``'auto'``.
        """)

    def _get_awb_mode(self):
        self._check_camera_open()
        mp = mmal.MMAL_PARAMETER_AWBMODE_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_AWB_MODE,
                ct.sizeof(mmal.MMAL_PARAMETER_AWBMODE_T)
                ))
        mmal_check(
            mmal.mmal_port_parameter_get(self._camera[0].control, mp.hdr),
            prefix="Failed to get auto-white-balance mode")
        return self._AWB_MODES_R[mp.value]
    def _set_awb_mode(self, value):
        self._check_camera_open()
        try:
            mp = mmal.MMAL_PARAMETER_AWBMODE_T(
                mmal.MMAL_PARAMETER_HEADER_T(
                    mmal.MMAL_PARAMETER_AWB_MODE,
                    ct.sizeof(mmal.MMAL_PARAMETER_AWBMODE_T)
                    ),
                self.AWB_MODES[value]
                )
            mmal_check(
                mmal.mmal_port_parameter_set(self._camera[0].control, mp.hdr),
                prefix="Failed to set auto-white-balance mode")
        except KeyError:
            raise PiCameraValueError("Invalid auto-white-balance mode: %s" % value)
    awb_mode = property(_get_awb_mode, _set_awb_mode, doc="""
        Retrieves or sets the auto-white-balance mode of the camera.

        When queried, the :attr:`awb_mode` property returns a string
        representing the auto-white-balance setting of the camera. The possible
        values can be obtained from the ``PiCamera.AWB_MODES`` attribute.

        When set, the property adjusts the camera's auto-white-balance mode.
        The property can be set while recordings or previews are in progress.
        The default value is ``'auto'``.
        """)

    def _get_awb_gains(self):
        raise NotImplementedError
        #self._check_camera_open()
        #mp = mmal.MMAL_PARAMETER_AWB_GAINS_T(
        #    mmal.MMAL_PARAMETER_HEADER_T(
        #        mmal.MMAL_PARAMETER_CUSTOM_AWB_GAINS,
        #        ct.sizeof(mmal.MMAL_PARAMETER_AWB_GAINS_T)
        #        ))
        #mmal_check(
        #    mmal.mmal_port_parameter_get(self._camera[0].control, mp.hdr),
        #    prefix="Failed to get auto-white-balance gains")
        #return mp.r_gain, mp.b_gain
    def _set_awb_gains(self, value):
        self._check_camera_open()
        try:
            red_gain, blue_gain = value
        except (ValueError, TypeError):
            red_gain = blue_gain = value
        if not (0.0 <= red_gain <= 8.0 and 0.0 <= blue_gain <= 8.0):
            raise PiCameraValueError(
                "Invalid gain(s) in (%f, %f) (valid range: 0.0-8.0)" % (
                    red_gain, blue_gain))
        mp = mmal.MMAL_PARAMETER_AWB_GAINS_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_CUSTOM_AWB_GAINS,
                ct.sizeof(mmal.MMAL_PARAMETER_AWB_GAINS_T)
                ),
            mmal.MMAL_RATIONAL_T(*to_rational(red_gain)),
            mmal.MMAL_RATIONAL_T(*to_rational(blue_gain)),
            )
        mmal_check(
            mmal.mmal_port_parameter_set(self._camera[0].control, mp.hdr),
            prefix="Failed to set auto-white-balance gains")
    awb_gains = property(_get_awb_gains, _set_awb_gains, doc="""
        Sets the auto-white-balance gains of the camera.

        When set, this attribute adjusts the camera's auto-white-balance gains.
        The property can be specified as a single value in which case both red
        and blue gains will be adjusted equally, or as a `(red, blue)` tuple.
        Values can be specified as an :class:`int`, :class:`float` or
        :class:`~fractions.Fraction` and each gain must be between 0.0 and 8.0.
        Typical values for the gains are between 0.9 and 1.9.  The property can
        be set while recordings or previews are in progress.

        .. note::

            This attribute only has an effect when :attr:`awb_mode` is set to
            ``'off'``. The write-only nature of this attribute is a firmware
            limitation.
        """)

    def _get_image_effect(self):
        self._check_camera_open()
        mp = mmal.MMAL_PARAMETER_IMAGEFX_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_IMAGE_EFFECT,
                ct.sizeof(mmal.MMAL_PARAMETER_IMAGEFX_T)
                ))
        mmal_check(
            mmal.mmal_port_parameter_get(self._camera[0].control, mp.hdr),
            prefix="Failed to get image effect")
        return self._IMAGE_EFFECTS_R[mp.value]
    def _set_image_effect(self, value):
        self._check_camera_open()
        try:
            mp = mmal.MMAL_PARAMETER_IMAGEFX_T(
                mmal.MMAL_PARAMETER_HEADER_T(
                    mmal.MMAL_PARAMETER_IMAGE_EFFECT,
                    ct.sizeof(mmal.MMAL_PARAMETER_IMAGEFX_T)
                    ),
                self.IMAGE_EFFECTS[value]
                )
            mmal_check(
                mmal.mmal_port_parameter_set(self._camera[0].control, mp.hdr),
                prefix="Failed to set image effect")
        except KeyError:
            raise PiCameraValueError("Invalid image effect: %s" % value)
    image_effect = property(_get_image_effect, _set_image_effect, doc="""
        Retrieves or sets the current image effect applied by the camera.

        When queried, the :attr:`image_effect` property returns a string
        representing the effect the camera will apply to captured video. The
        possible values can be obtained from the ``PiCamera.IMAGE_EFFECTS``
        attribute.

        When set, the property changes the effect applied by the camera.  The
        property can be set while recordings or previews are in progress, but
        only certain effects work while recording video (notably ``'negative'``
        and ``'solarize'``). The default value is ``'none'``.
        """)

    def _get_color_effects(self):
        self._check_camera_open()
        mp = mmal.MMAL_PARAMETER_COLOURFX_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_COLOUR_EFFECT,
                ct.sizeof(mmal.MMAL_PARAMETER_COLOURFX_T)
                ))
        mmal_check(
            mmal.mmal_port_parameter_get(self._camera[0].control, mp.hdr),
            prefix="Failed to get color effects")
        if mp.enable != mmal.MMAL_FALSE:
            return (mp.u, mp.v)
        else:
            return None
    def _set_color_effects(self, value):
        self._check_camera_open()
        if value is None:
            enable = mmal.MMAL_FALSE
            u = v = 128
        else:
            enable = mmal.MMAL_TRUE
            try:
                u, v = value
            except (TypeError, ValueError) as e:
                raise PiCameraValueError(
                    "Invalid color effect (u, v) tuple: %s" % value)
            if not ((0 <= u <= 255) and (0 <= v <= 255)):
                raise PiCameraValueError(
                    "(u, v) values must be between 0 and 255")
        mp = mmal.MMAL_PARAMETER_COLOURFX_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_COLOUR_EFFECT,
                ct.sizeof(mmal.MMAL_PARAMETER_COLOURFX_T)
                ),
            enable, u, v
            )
        mmal_check(
            mmal.mmal_port_parameter_set(self._camera[0].control, mp.hdr),
            prefix="Failed to set color effects")
    color_effects = property(_get_color_effects, _set_color_effects, doc="""
        Retrieves or sets the current color effect applied by the camera.

        When queried, the :attr:`color_effects` property either returns
        ``None`` which indicates that the camera is using normal color
        settings, or a ``(u, v)`` tuple where ``u`` and ``v`` are integer
        values between 0 and 255.

        When set, the property changes the color effect applied by the camera.
        The property can be set while recordings or previews are in progress.
        For example, to make the image black and white set the value to ``(128,
        128)``. The default value is ``None``.
        """)

    def _get_rotation(self):
        self._check_camera_open()
        mp = ct.c_int32()
        mmal_check(
            mmal.mmal_port_parameter_get_int32(
                self._camera[0].output[0],
                mmal.MMAL_PARAMETER_ROTATION,
                mp
                ),
            prefix="Failed to get rotation")
        return mp.value
    def _set_rotation(self, value):
        self._check_camera_open()
        try:
            value = ((int(value) % 360) // 90) * 90
        except ValueError:
            raise PiCameraValueError("Invalid rotation angle: %s" % value)
        for p in self.CAMERA_PORTS:
            mmal_check(
                mmal.mmal_port_parameter_set_int32(
                    self._camera[0].output[p],
                    mmal.MMAL_PARAMETER_ROTATION,
                    value
                    ),
                prefix="Failed to set rotation")
    rotation = property(_get_rotation, _set_rotation, doc="""
        Retrieves or sets the current rotation of the camera's image.

        When queried, the :attr:`rotation` property returns the rotation
        applied to the image. Valid values are 0, 90, 180, and 270.

        When set, the property changes the color effect applied by the camera.
        The property can be set while recordings or previews are in progress.
        The default value is ``0``.
        """)

    def _get_vflip(self):
        self._check_camera_open()
        mp = mmal.MMAL_PARAMETER_MIRROR_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_MIRROR,
                ct.sizeof(mmal.MMAL_PARAMETER_MIRROR_T)
                ))
        mmal_check(
            mmal.mmal_port_parameter_get(self._camera[0].output[0], mp.hdr),
            prefix="Failed to get vertical flip")
        return mp.value in (mmal.MMAL_PARAM_MIRROR_VERTICAL, mmal.MMAL_PARAM_MIRROR_BOTH)
    def _set_vflip(self, value):
        self._check_camera_open()
        value = bool(value)
        for p in self.CAMERA_PORTS:
            mp = mmal.MMAL_PARAMETER_MIRROR_T(
                mmal.MMAL_PARAMETER_HEADER_T(
                    mmal.MMAL_PARAMETER_MIRROR,
                    ct.sizeof(mmal.MMAL_PARAMETER_MIRROR_T)
                    ),
                {
                    (False, False): mmal.MMAL_PARAM_MIRROR_NONE,
                    (True,  False): mmal.MMAL_PARAM_MIRROR_VERTICAL,
                    (False, True):  mmal.MMAL_PARAM_MIRROR_HORIZONTAL,
                    (True,  True):  mmal.MMAL_PARAM_MIRROR_BOTH,
                    }[(value, self.hflip)]
                )
            mmal_check(
                mmal.mmal_port_parameter_set(self._camera[0].output[p], mp.hdr),
                prefix="Failed to set vertical flip")
    vflip = property(_get_vflip, _set_vflip, doc="""
        Retrieves or sets whether the camera's output is vertically flipped.

        When queried, the :attr:`vflip` property returns a boolean indicating
        whether or not the camera's output is vertically flipped. The property
        can be set while recordings or previews are in progress. The default
        value is ``False``.
        """)

    def _get_hflip(self):
        self._check_camera_open()
        mp = mmal.MMAL_PARAMETER_MIRROR_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_MIRROR,
                ct.sizeof(mmal.MMAL_PARAMETER_MIRROR_T)
                ))
        mmal_check(
            mmal.mmal_port_parameter_get(self._camera[0].output[0], mp.hdr),
            prefix="Failed to get horizontal flip")
        return mp.value in (mmal.MMAL_PARAM_MIRROR_HORIZONTAL, mmal.MMAL_PARAM_MIRROR_BOTH)
    def _set_hflip(self, value):
        self._check_camera_open()
        value = bool(value)
        for p in self.CAMERA_PORTS:
            mp = mmal.MMAL_PARAMETER_MIRROR_T(
                mmal.MMAL_PARAMETER_HEADER_T(
                    mmal.MMAL_PARAMETER_MIRROR,
                    ct.sizeof(mmal.MMAL_PARAMETER_MIRROR_T)
                    ),
                {
                    (False, False): mmal.MMAL_PARAM_MIRROR_NONE,
                    (True,  False): mmal.MMAL_PARAM_MIRROR_VERTICAL,
                    (False, True):  mmal.MMAL_PARAM_MIRROR_HORIZONTAL,
                    (True,  True):  mmal.MMAL_PARAM_MIRROR_BOTH,
                    }[(self.vflip, value)]
                )
            mmal_check(
                mmal.mmal_port_parameter_set(self._camera[0].output[p], mp.hdr),
                prefix="Failed to set horizontal flip")
    hflip = property(_get_hflip, _set_hflip, doc="""
        Retrieves or sets whether the camera's output is horizontally flipped.

        When queried, the :attr:`hflip` property returns a boolean indicating
        whether or not the camera's output is horizontally flipped. The
        property can be set while recordings or previews are in progress. The
        default value is ``False``.
        """)

    def _get_crop(self):
        self._check_camera_open()
        mp = mmal.MMAL_PARAMETER_INPUT_CROP_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_INPUT_CROP,
                ct.sizeof(mmal.MMAL_PARAMETER_INPUT_CROP_T)
                ))
        mmal_check(
            mmal.mmal_port_parameter_get(self._camera[0].control, mp.hdr),
            prefix="Failed to get crop")
        return (
            mp.rect.x / 65535.0,
            mp.rect.y / 65535.0,
            mp.rect.width / 65535.0,
            mp.rect.height / 65535.0,
            )
    def _set_crop(self, value):
        self._check_camera_open()
        try:
            x, y, w, h = value
        except (TypeError, ValueError) as e:
            raise PiCameraValueError(
                "Invalid crop rectangle (x, y, w, h) tuple: %s" % value)
        mp = mmal.MMAL_PARAMETER_INPUT_CROP_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_INPUT_CROP,
                ct.sizeof(mmal.MMAL_PARAMETER_INPUT_CROP_T)
                ),
            mmal.MMAL_RECT_T(
                max(0, min(65535, int(65535 * x))),
                max(0, min(65535, int(65535 * y))),
                max(0, min(65535, int(65535 * w))),
                max(0, min(65535, int(65535 * h))),
                ),
            )
        mmal_check(
            mmal.mmal_port_parameter_set(self._camera[0].control, mp.hdr),
            prefix="Failed to set crop")
    crop = property(_get_crop, _set_crop, doc="""
        Retrieves or sets the crop applied to the camera's input.

        When queried, the :attr:`crop` property returns a ``(x, y, w, h)``
        tuple of floating point values ranging from 0.0 to 1.0, indicating the
        proportion of the image to include in the output (the "Region of
        Interest" or ROI). The default value is ``(0.0, 0.0, 1.0, 1.0)`` which
        indicates that everything should be included. The property can be set
        while recordings or previews are in progress.
        """)

    def _get_preview_alpha(self):
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
            ))
        mmal_check(
            mmal.mmal_port_parameter_get(self._preview[0].input[0], mp.hdr),
            prefix="Failed to get preview alpha")
        return mp.alpha
    def _set_preview_alpha(self, value):
        self._check_camera_open()
        try:
            if not (0 <= value <= 255):
                raise PiCameraValueError(
                    "Invalid alpha value: %d (valid range 0..255)" % value)
        except TypeError:
            raise PiCameraValueError("Invalid alpha value: %s" % value)
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
                ),
            set=mmal.MMAL_DISPLAY_SET_ALPHA,
            alpha=value
            )
        mmal_check(
            mmal.mmal_port_parameter_set(self._preview[0].input[0], mp.hdr),
            prefix="Failed to set preview alpha")
    preview_alpha = property(_get_preview_alpha, _set_preview_alpha, doc="""
        Retrieves or sets the opacity of the preview window.

        When queried, the :attr:`preview_alpha` property returns a value
        between 0 and 255 indicating the opacity of the preview window, where 0
        is completely transparent and 255 is completely opaque. The default
        value is 255. The property can be set while recordings or previews are
        in progress.

        .. note::

            If the preview is not running, the property will not reflect
            changes to it, but they will be in effect next time the preview is
            started. In other words, you can set preview_alpha to 128, but
            querying it will still return 255 (the default) until you call
            :meth:`start_preview` at which point the preview will appear
            semi-transparent and :attr:`preview_alpha` will suddenly return
            128. This appears to be a firmware issue.
        """)

    def _get_preview_layer(self):
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
            ))
        mmal_check(
            mmal.mmal_port_parameter_get(self._preview[0].input[0], mp.hdr),
            prefix="Failed to get preview alpha")
        return mp.layer
    def _set_preview_layer(self, value):
        self._check_camera_open()
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
                ),
            set=mmal.MMAL_DISPLAY_SET_LAYER,
            layer=value
            )
        mmal_check(
            mmal.mmal_port_parameter_set(self._preview[0].input[0], mp.hdr),
            prefix="Failed to set preview layer")
    preview_layer = property(
            _get_preview_layer, _set_preview_layer, doc="""
        Retrieves of sets the layer of the preview window.

        The :attr:`preview_layer` property is an integer which controls the
        layer that the preview window occupies. It defaults to 2 which results
        in the preview appearing above all other output.

        .. warning::

            Operation of this attribute is not yet fully understood. The
            documentation above is incomplete and may be incorrect!
        """)

    def _get_preview_fullscreen(self):
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
            ))
        mmal_check(
            mmal.mmal_port_parameter_get(self._preview[0].input[0], mp.hdr),
            prefix="Failed to get preview fullscreen")
        return mp.fullscreen != mmal.MMAL_FALSE
    def _set_preview_fullscreen(self, value):
        self._check_camera_open()
        value = bool(value)
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
                ),
            set=mmal.MMAL_DISPLAY_SET_FULLSCREEN,
            fullscreen={
                False: mmal.MMAL_FALSE,
                True:  mmal.MMAL_TRUE,
                }[value]
            )
        mmal_check(
            mmal.mmal_port_parameter_set(self._preview[0].input[0], mp.hdr),
            prefix="Failed to set preview fullscreen")
    preview_fullscreen = property(
            _get_preview_fullscreen, _set_preview_fullscreen, doc="""
        Retrieves or sets full-screen for the preview window.

        The :attr:`preview_fullscreen` property is a bool which controls
        whether the preview window takes up the entire display or not. When
        set to ``False``, the :attr:`preview_window` property can be used to
        control the precise size of the preview display. The property can be
        set while recordings or previews are active.

        .. note::

            The :attr:`preview_fullscreen` attribute is afflicted by the same
            issue as :attr:`preview_alpha` with regards to changes while the
            preview is not running.
        """)

    def _get_preview_window(self):
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
            ))
        mmal_check(
            mmal.mmal_port_parameter_get(self._preview[0].input[0], mp.hdr),
            prefix="Failed to get preview window")
        return (
            mp.dest_rect.x,
            mp.dest_rect.y,
            mp.dest_rect.width,
            mp.dest_rect.height,
            )
    def _set_preview_window(self, value):
        self._check_camera_open()
        try:
            x, y, w, h = value
        except (TypeError, ValueError) as e:
            raise PiCameraValueError(
                "Invalid window rectangle (x, y, w, h) tuple: %s" % value)
        mp = mmal.MMAL_DISPLAYREGION_T(
            mmal.MMAL_PARAMETER_HEADER_T(
                mmal.MMAL_PARAMETER_DISPLAYREGION,
                ct.sizeof(mmal.MMAL_DISPLAYREGION_T)
                ),
            set=mmal.MMAL_DISPLAY_SET_DEST_RECT,
            dest_rect=mmal.MMAL_RECT_T(x, y, w, h),
            )
        mmal_check(
            mmal.mmal_port_parameter_set(self._preview[0].input[0], mp.hdr),
            prefix="Failed to set preview window")
    preview_window = property(_get_preview_window, _set_preview_window, doc="""
        Retrieves or sets the size of the preview window.

        When the :attr:`preview_fullscreen` property is set to ``False``, the
        :attr:`preview_window` property specifies the size and position of the
        preview window on the display. The property is a 4-tuple consisting of
        ``(x, y, width, height)``. The property can be set while recordings or
        previews are active.

        .. note::

            The :attr:`preview_window` attribute is afflicted by the same issue
            as :attr:`preview_alpha` with regards to changes while the preview
            is not running.
        """)


########NEW FILE########
__FILENAME__ = encoders
# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013,2014 Dave Hughes <dave@waveform.org.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str and range equivalent to Py3's
str = type('')
try:
    range = xrange
except NameError:
    pass

import io
import datetime
import threading
import warnings
import ctypes as ct
from collections import namedtuple

import picamera.mmal as mmal
from picamera.exc import (
    mmal_check,
    PiCameraWarning,
    PiCameraError,
    PiCameraMMALError,
    PiCameraValueError,
    PiCameraRuntimeError,
    )


__all__ = [
    'PiEncoder',
    'PiVideoEncoder',
    'PiImageEncoder',
    'PiRawImageEncoder',
    'PiOneImageEncoder',
    'PiMultiImageEncoder',
    ]


class PiVideoFrame(namedtuple('PiVideoFrame', (
    'index',         # the frame number, where the first frame is 0
    'keyframe',      # True when the frame is a keyframe
    'frame_size',    # the size (in bytes) of the frame's data
    'video_size',    # the size (in bytes) of the video so far
    'split_size',    # the size (in bytes) of the video since the last split
    'timestamp',     # the presentation timestamp (PTS) of the frame
    'header',        # the frame is an SPS/PPS header
    ))):

    @property
    def position(self):
        return self.split_size - self.frame_size


def _encoder_callback(port, buf):
    encoder = ct.cast(port[0].userdata, ct.POINTER(ct.py_object))[0]
    encoder._callback(port, buf)
_encoder_callback = mmal.MMAL_PORT_BH_CB_T(_encoder_callback)


class PiEncoder(object):
    """
    Abstract base implemetation of an MMAL encoder for use by PiCamera
    """

    encoder_type = None

    def __init__(
            self, parent, camera_port, input_port, format, resize, **options):
        self.parent = parent
        self.format = format
        self.encoder = None
        self.resizer = None
        self.encoder_connection = None
        self.resizer_connection = None
        self.camera_port = camera_port
        self.input_port = input_port
        self.output_port = None
        self.pool = None
        self.started_capture = False
        self.opened_output = False
        self.output = None
        self.lock = threading.Lock() # protects access to self.output
        self.exception = None
        self.event = threading.Event()
        self.stopped = True
        try:
            if parent.closed:
                raise PiCameraRuntimeError("Camera is closed")
            if resize:
                self._create_resizer(*resize)
            self._create_encoder(**options)
            self._create_pool()
            self._create_connection()
        except:
            self.close()
            raise

    def _create_encoder(self):
        """
        Creates and configures the encoder itself
        """
        assert not self.encoder
        self.encoder = ct.POINTER(mmal.MMAL_COMPONENT_T)()
        mmal_check(
            mmal.mmal_component_create(self.encoder_type, self.encoder),
            prefix="Failed to create encoder component")
        if not self.encoder[0].input_num:
            raise PiCameraError("No input ports on encoder component")
        if not self.encoder[0].output_num:
            raise PiCameraError("No output ports on encoder component")
        # Ensure output format is the same as the input
        self.output_port = self.encoder[0].output[0]
        if self.resizer:
            mmal.mmal_format_copy(
                self.encoder[0].input[0][0].format, self.resizer[0].output[0][0].format)
        else:
            mmal.mmal_format_copy(
                self.encoder[0].input[0][0].format, self.input_port[0].format)
        mmal_check(
            mmal.mmal_port_format_commit(self.encoder[0].input[0]),
            prefix="Failed to set encoder input port format")
        mmal.mmal_format_copy(
            self.output_port[0].format, self.encoder[0].input[0][0].format)
        # Set buffer size and number to appropriate values
        self.output_port[0].buffer_size = self.output_port[0].buffer_size_recommended
        self.output_port[0].buffer_num = self.output_port[0].buffer_num_recommended
        # NOTE: We deliberately don't commit the output port format here as
        # this is a base class and the output configuration is incomplete at
        # this point. Descendents are expected to finish configuring the
        # encoder and then commit the port format themselves

    def _create_resizer(self, width, height):
        self.resizer = ct.POINTER(mmal.MMAL_COMPONENT_T)()
        mmal_check(
            mmal.mmal_component_create(
                mmal.MMAL_COMPONENT_DEFAULT_RESIZER, self.resizer),
            prefix="Failed to create resizer component")
        if not self.resizer[0].input_num:
            raise PiCameraError("No input ports on resizer component")
        if not self.resizer[0].output_num:
            raise PiCameraError("No output ports on resizer component")
        # Copy the original input port's format to the resizer's input,
        # then the resizer's input format to the output, and configure it
        mmal.mmal_format_copy(
            self.resizer[0].input[0][0].format, self.input_port[0].format)
        mmal_check(
            mmal.mmal_port_format_commit(self.resizer[0].input[0]),
            prefix="Failed to set resizer input port format")
        mmal.mmal_format_copy(
            self.resizer[0].output[0][0].format, self.resizer[0].input[0][0].format)
        fmt = self.resizer[0].output[0][0].format
        fmt[0].es[0].video.width = mmal.VCOS_ALIGN_UP(width, 32)
        fmt[0].es[0].video.height = mmal.VCOS_ALIGN_UP(height, 16)
        fmt[0].es[0].video.crop.x = 0
        fmt[0].es[0].video.crop.y = 0
        fmt[0].es[0].video.crop.width = width
        fmt[0].es[0].video.crop.height = height
        mmal_check(
            mmal.mmal_port_format_commit(self.resizer[0].output[0]),
            prefix="Failed to set resizer output port format")

    def _create_pool(self):
        """
        Allocates a pool of buffers for the encoder
        """
        assert not self.pool
        self.pool = mmal.mmal_port_pool_create(
            self.output_port,
            self.output_port[0].buffer_num,
            self.output_port[0].buffer_size)
        if not self.pool:
            raise PiCameraError(
                "Failed to create buffer header pool for encoder component")

    def _create_connection(self):
        """
        Connects the camera to the encoder object
        """
        assert not self.encoder_connection
        if self.resizer:
            self.resizer_connection = self.parent._connect_ports(
                self.input_port, self.resizer[0].input[0])
            self.encoder_connection = self.parent._connect_ports(
                self.resizer[0].output[0], self.encoder[0].input[0])
        else:
            self.encoder_connection = self.parent._connect_ports(
                self.input_port, self.encoder[0].input[0])

    def _callback(self, port, buf):
        """
        The encoder's main callback function
        """
        if self.stopped:
            mmal.mmal_buffer_header_release(buf)
        else:
            stop = False
            try:
                try:
                    stop = self._callback_write(buf)
                finally:
                    mmal.mmal_buffer_header_release(buf)
                    self._callback_recycle(port, buf)
            except Exception as e:
                stop = True
                self.exception = e
            if stop:
                self.stopped = True
                self.event.set()

    def _callback_write(self, buf):
        """
        Performs output writing on behalf of the encoder callback function;
        return value determines whether writing has completed.
        """
        if buf[0].length:
            mmal_check(
                mmal.mmal_buffer_header_mem_lock(buf),
                prefix="Unable to lock buffer header memory")
            try:
                with self.lock:
                    if self.output:
                        written = self.output.write(
                           ct.string_at(buf[0].data, buf[0].length))
                        # Ignore None return value; most Python 2 streams have
                        # no return value for write()
                        if (written is not None) and (written != buf[0].length):
                            raise PiCameraError(
                                "Unable to write buffer to file - aborting")
            finally:
                mmal.mmal_buffer_header_mem_unlock(buf)
        return bool(buf[0].flags & mmal.MMAL_BUFFER_HEADER_FLAG_EOS)

    def _callback_recycle(self, port, buf):
        """
        Recycles the buffer on behalf of the encoder callback function
        """
        new_buf = mmal.mmal_queue_get(self.pool[0].queue)
        if not new_buf:
            raise PiCameraError(
                "Unable to get a buffer to return to the encoder port")
        mmal_check(
            mmal.mmal_port_send_buffer(port, new_buf),
            prefix="Unable to return a buffer to the encoder port")

    def _open_output(self, output):
        """
        Opens the specified output object, if necessary and tracks whether
        we were the one to open it.
        """
        with self.lock:
            self.opened_output = isinstance(output, (bytes, str))
            if self.opened_output:
                # Open files in binary mode with a decent buffer size
                self.output = io.open(output, 'wb', buffering=65536)
            else:
                self.output = output

    def _close_output(self):
        """
        Closes the output object, if necessary or simply flushes it if we
        didn't open it and it has a flush method.
        """
        with self.lock:
            if self.output:
                if self.opened_output:
                    self.output.close()
                elif hasattr(self.output, 'flush'):
                    self.output.flush()
                self.output = None
                self.opened_output = False

    def start(self, output):
        """
        Starts the encoder object writing to the specified output
        """
        self.event.clear()
        self.stopped = False
        self.exception = None
        self._open_output(output)
        self.output_port[0].userdata = ct.cast(
            ct.pointer(ct.py_object(self)),
            ct.c_void_p)
        mmal_check(
            mmal.mmal_port_enable(self.output_port, _encoder_callback),
            prefix="Failed to enable encoder output port")

        for q in range(mmal.mmal_queue_length(self.pool[0].queue)):
            buf = mmal.mmal_queue_get(self.pool[0].queue)
            if not buf:
                raise PiCameraRuntimeError(
                    "Unable to get a required buffer from pool queue")
            mmal_check(
                mmal.mmal_port_send_buffer(self.output_port, buf),
                prefix="Unable to send a buffer to encoder output port")
        b = mmal.MMAL_BOOL_T()
        mmal_check(
            mmal.mmal_port_parameter_get_boolean(
                self.camera_port,
                mmal.MMAL_PARAMETER_CAPTURE,
                b),
            prefix="Failed to query capture status")
        self.started_capture = not bool(b)
        if self.started_capture:
            mmal_check(
                mmal.mmal_port_parameter_set_boolean(
                    self.camera_port,
                    mmal.MMAL_PARAMETER_CAPTURE,
                    mmal.MMAL_TRUE),
                prefix="Failed to start capture")

    def wait(self, timeout=None):
        """
        Waits for the encoder to finish (successfully or otherwise)
        """
        result = self.event.wait(timeout)
        if result:
            if self.started_capture:
                self.started_capture = False
                mmal_check(
                    mmal.mmal_port_parameter_set_boolean(
                        self.camera_port,
                        mmal.MMAL_PARAMETER_CAPTURE,
                        mmal.MMAL_FALSE),
                    prefix="Failed to stop capture")
            try:
                mmal_check(
                    mmal.mmal_port_disable(self.output_port),
                    prefix="Failed to disable encoder output port")
            except PiCameraMMALError as e:
                if e.status != mmal.MMAL_EINVAL:
                    raise
            self._close_output()
            # Check whether the callback set an exception
            if self.exception:
                raise self.exception
        return result

    def stop(self):
        """
        Stops the encoder, regardless of whether it's finished
        """
        # The check on is_enabled below is not a race condition; we ignore the
        # EINVAL error in the case the port turns out to be disabled when we
        # disable below. The check exists purely to prevent stderr getting
        # spammed by our continued attempts to disable an already disabled port
        if self.encoder and self.output_port[0].is_enabled:
            if self.started_capture:
                self.started_capture = False
                mmal_check(
                    mmal.mmal_port_parameter_set_boolean(
                        self.camera_port,
                        mmal.MMAL_PARAMETER_CAPTURE,
                        mmal.MMAL_FALSE),
                    prefix="Failed to stop capture")
            try:
                mmal_check(
                    mmal.mmal_port_disable(self.output_port),
                    prefix="Failed to disable encoder output port")
            except PiCameraMMALError as e:
                if e.status != mmal.MMAL_EINVAL:
                    raise
        self.stopped = True
        self.event.set()
        self._close_output()

    def close(self):
        """
        Finalizes the encoder and deallocates all structures
        """
        self.stop()
        if self.encoder_connection:
            mmal.mmal_connection_destroy(self.encoder_connection)
            self.encoder_connection = None
        if self.pool:
            mmal.mmal_port_pool_destroy(self.output_port, self.pool)
            self.pool = None
        if self.resizer_connection:
            mmal.mmal_connection_destroy(self.resizer_connection)
        if self.encoder:
            mmal.mmal_component_destroy(self.encoder)
            self.encoder = None
        if self.resizer:
            mmal.mmal_component_destroy(self.resizer)
            self.resizer = None
        self.output_port = None


class PiVideoEncoder(PiEncoder):
    encoder_type = mmal.MMAL_COMPONENT_DEFAULT_VIDEO_ENCODER

    def __init__(
            self, parent, camera_port, input_port, format, resize, **options):
        super(PiVideoEncoder, self).__init__(
                parent, camera_port, input_port, format, resize, **options)
        self._next_output = []
        self.frame = None

    def _create_encoder(
            self, bitrate=17000000, intra_period=0, profile='high',
            quantization=0, inline_headers=True, sei=False):
        super(PiVideoEncoder, self)._create_encoder()

        try:
            self.output_port[0].format[0].encoding = {
                'h264':  mmal.MMAL_ENCODING_H264,
                'mjpeg': mmal.MMAL_ENCODING_MJPEG,
                }[self.format]
        except KeyError:
            raise PiCameraValueError('Unrecognized format %s' % self.format)

        if not (0 <= bitrate <= 25000000):
            raise PiCameraValueError('bitrate must be between 0 (VBR) and 25Mbps')
        if quantization and bitrate:
            warnings.warn('Setting bitrate to 0 as quantization is non-zero', PiCameraWarning)
            bitrate = 0
        self.output_port[0].format[0].bitrate = bitrate
        mmal_check(
            mmal.mmal_port_format_commit(self.output_port),
            prefix="Unable to set format on encoder output port")

        if self.format == 'h264':
            mp = mmal.MMAL_PARAMETER_VIDEO_PROFILE_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_PROFILE,
                        ct.sizeof(mmal.MMAL_PARAMETER_VIDEO_PROFILE_T),
                        ),
                    )
            try:
                mp.profile[0].profile = {
                    'baseline':    mmal.MMAL_VIDEO_PROFILE_H264_BASELINE,
                    'main':        mmal.MMAL_VIDEO_PROFILE_H264_MAIN,
                    'high':        mmal.MMAL_VIDEO_PROFILE_H264_HIGH,
                    'constrained': mmal.MMAL_VIDEO_PROFILE_H264_CONSTRAINED_BASELINE,
                }[profile]
            except KeyError:
                raise PiCameraValueError("Invalid H.264 profile %s" % profile)
            mp.profile[0].level = mmal.MMAL_VIDEO_LEVEL_H264_4
            mmal_check(
                mmal.mmal_port_parameter_set(self.output_port, mp.hdr),
                prefix="Unable to set encoder H.264 profile")

            mmal_check(
                mmal.mmal_port_parameter_set_boolean(
                    self.output_port,
                    mmal.MMAL_PARAMETER_VIDEO_ENCODE_INLINE_HEADER,
                    int(inline_headers)),
                prefix="Unable to set inline_headers")

            mmal_check(
                mmal.mmal_port_parameter_set_boolean(
                    self.output_port,
                    mmal.MMAL_PARAMETER_VIDEO_ENCODE_SEI_ENABLE,
                    int(sei)),
                prefix="Enable to set SEI")

            if not (bitrate and inline_headers):
                # If inline_headers is disabled, or VBR encoding is configured,
                # disable the split function
                self._next_output = None

            # We need the intra-period to calculate the SPS header timeout in
            # the split method below. If one is not set explicitly, query the
            # encoder's default
            if intra_period:
                mp = mmal.MMAL_PARAMETER_UINT32_T(
                        mmal.MMAL_PARAMETER_HEADER_T(
                            mmal.MMAL_PARAMETER_INTRAPERIOD,
                            ct.sizeof(mmal.MMAL_PARAMETER_UINT32_T),
                            ),
                        intra_period
                        )
                mmal_check(
                    mmal.mmal_port_parameter_set(self.output_port, mp.hdr),
                    prefix="Unable to set encoder intra_period")
                self._intra_period = intra_period
            else:
                mp = mmal.MMAL_PARAMETER_UINT32_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_INTRAPERIOD,
                        ct.sizeof(mmal.MMAL_PARAMETER_UINT32_T),
                        ))
                mmal_check(
                    mmal.mmal_port_parameter_get(self.output_port, mp.hdr),
                    prefix="Unable to get encoder intra_period")
                self._intra_period = mp.value

        elif self.format == 'mjpeg':
            # MJPEG doesn't have an intra_period setting as such, but as every
            # frame is a full-frame, the intra_period is effectively 1
            self._intra_period = 1

        if quantization:
            mp = mmal.MMAL_PARAMETER_UINT32_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_VIDEO_ENCODE_INITIAL_QUANT,
                        ct.sizeof(mmal.MMAL_PARAMETER_UINT32_T),
                        ),
                    quantization
                    )
            mmal_check(
                mmal.mmal_port_parameter_set(self.output_port, mp.hdr),
                prefix="Unable to set initial quantization")
            mp = mmal.MMAL_PARAMETER_UINT32_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_VIDEO_ENCODE_MIN_QUANT,
                        ct.sizeof(mmal.MMAL_PARAMETER_UINT32_T),
                        ),
                    quantization,
                    )
            mmal_check(
                mmal.mmal_port_parameter_set(self.output_port, mp.hdr),
                prefix="Unable to set minimum quantization")
            mp = mmal.MMAL_PARAMETER_UINT32_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_VIDEO_ENCODE_MAX_QUANT,
                        ct.sizeof(mmal.MMAL_PARAMETER_UINT32_T),
                        ),
                    quantization,
                    )
            mmal_check(
                mmal.mmal_port_parameter_set(self.output_port, mp.hdr),
                prefix="Unable to set maximum quantization")

        mmal_check(
            mmal.mmal_port_parameter_set_boolean(
                self.encoder[0].input[0],
                mmal.MMAL_PARAMETER_VIDEO_IMMUTABLE_INPUT,
                1),
            prefix="Unable to set immutable flag on encoder input port")

        mmal_check(
            mmal.mmal_component_enable(self.encoder),
            prefix="Unable to enable video encoder component")

    def start(self, output):
        self._size = 0 # internal counter for frame size
        self.frame = PiVideoFrame(
                index=-1,
                keyframe=False,
                frame_size=0,
                video_size=0,
                split_size=0,
                timestamp=0,
                header=False,
                )
        super(PiVideoEncoder, self).start(output)

    def split(self, output):
        with self.lock:
            if self._next_output is None:
                raise PiCameraRuntimeError(
                    'Cannot use split_recording without inline_headers and CBR')
            self._next_output.append(output)
        # intra_period / framerate gives the time between I-frames (which
        # should also coincide with SPS headers). We multiply by two to ensure
        # the timeout is deliberately excessive
        timeout = float(self._intra_period / self.parent.framerate) * 2.0
        if not self.event.wait(timeout):
            raise PiCameraRuntimeError('Timed out waiting for an SPS header')
        self.event.clear()

    def _callback_write(self, buf):
        self._size += buf[0].length
        if buf[0].flags & mmal.MMAL_BUFFER_HEADER_FLAG_FRAME_END:
            self.frame = PiVideoFrame(
                    index=self.frame.index + 1,
                    keyframe=bool(buf[0].flags & mmal.MMAL_BUFFER_HEADER_FLAG_KEYFRAME),
                    frame_size=self._size,
                    video_size=self.frame.video_size + self._size,
                    split_size=self.frame.split_size + self._size,
                    timestamp=None if buf[0].pts in (0, mmal.MMAL_TIME_UNKNOWN) else buf[0].pts,
                    header=bool(buf[0].flags & mmal.MMAL_BUFFER_HEADER_FLAG_CONFIG),
                    )
            self._size = 0
        if self.format != 'h264' or (buf[0].flags & mmal.MMAL_BUFFER_HEADER_FLAG_CONFIG):
            new_output = None
            with self.lock:
                if self._next_output:
                    new_output = self._next_output.pop(0)
            if new_output:
                self._close_output()
                self.frame = PiVideoFrame(
                        index=self.frame.index,
                        keyframe=self.frame.keyframe,
                        frame_size=self.frame.frame_size,
                        video_size=self.frame.video_size,
                        split_size=0,
                        timestamp=self.frame.timestamp,
                        header=self.frame.header,
                        )
                self._open_output(new_output)
                self.event.set()
        super(PiVideoEncoder, self)._callback_write(buf)


class PiImageEncoder(PiEncoder):
    encoder_type = mmal.MMAL_COMPONENT_DEFAULT_IMAGE_ENCODER

    def _create_encoder(self, quality=85, thumbnail=(64, 48, 35), bayer=False):
        super(PiImageEncoder, self)._create_encoder()

        try:
            self.output_port[0].format[0].encoding = {
                'jpeg': mmal.MMAL_ENCODING_JPEG,
                'png':  mmal.MMAL_ENCODING_PNG,
                'gif':  mmal.MMAL_ENCODING_GIF,
                'bmp':  mmal.MMAL_ENCODING_BMP,
                }[self.format]
        except KeyError:
            raise PiCameraValueError("Unrecognized format %s" % self.format)
        mmal_check(
            mmal.mmal_port_format_commit(self.output_port),
            prefix="Unable to set format on encoder output port")

        if self.format == 'jpeg':
            mmal_check(
                mmal.mmal_port_parameter_set_uint32(
                    self.output_port,
                    mmal.MMAL_PARAMETER_JPEG_Q_FACTOR,
                    quality),
                prefix="Failed to set JPEG quality")

            mmal_check(
                mmal.mmal_port_parameter_set_boolean(
                    self.camera_port,
                    mmal.MMAL_PARAMETER_ENABLE_RAW_CAPTURE,
                    int(bool(bayer))),
                prefix="Failed to set raw capture")

            if thumbnail is None:
                mp = mmal.MMAL_PARAMETER_THUMBNAIL_CONFIG_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_THUMBNAIL_CONFIGURATION,
                        ct.sizeof(mmal.MMAL_PARAMETER_THUMBNAIL_CONFIG_T)
                        ),
                    0, 0, 0, 0)
            else:
                mp = mmal.MMAL_PARAMETER_THUMBNAIL_CONFIG_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_THUMBNAIL_CONFIGURATION,
                        ct.sizeof(mmal.MMAL_PARAMETER_THUMBNAIL_CONFIG_T)
                        ),
                    1, *thumbnail)
            mmal_check(
                mmal.mmal_port_parameter_set(self.encoder[0].control, mp.hdr),
                prefix="Failed to set thumbnail configuration")

        mmal_check(
            mmal.mmal_component_enable(self.encoder),
            prefix="Unable to enable encoder component")


class PiOneImageEncoder(PiImageEncoder):
    def _callback_write(self, buf):
        return (
            super(PiOneImageEncoder, self)._callback_write(buf)
            ) or bool(
            buf[0].flags & (
                mmal.MMAL_BUFFER_HEADER_FLAG_FRAME_END |
                mmal.MMAL_BUFFER_HEADER_FLAG_TRANSMISSION_FAILED)
            )


class PiMultiImageEncoder(PiImageEncoder):
    def _open_output(self, outputs):
        self._output_iter = iter(outputs)
        self._next_output()

    def _next_output(self):
        if self.output:
            self._close_output()
        super(PiMultiImageEncoder, self)._open_output(next(self._output_iter))

    def _callback_write(self, buf):
        try:
            if (
                super(PiMultiImageEncoder, self)._callback_write(buf)
                ) or bool(
                buf[0].flags & (
                    mmal.MMAL_BUFFER_HEADER_FLAG_FRAME_END |
                    mmal.MMAL_BUFFER_HEADER_FLAG_TRANSMISSION_FAILED)
                ):
                self._next_output()
            return False
        except StopIteration:
            return True


class PiCookedOneImageEncoder(PiOneImageEncoder):
    exif_encoding = 'ascii'

    def _add_exif_tag(self, tag, value):
        # Format the tag and value into an appropriate bytes string, encoded
        # with the Exif encoding (ASCII)
        if isinstance(tag, str):
            tag = tag.encode(self.exif_encoding)
        if isinstance(value, str):
            value = value.encode(self.exif_encoding)
        elif isinstance(value, datetime.datetime):
            value = value.strftime('%Y:%m:%d %H:%M:%S').encode(self.exif_encoding)
        # MMAL_PARAMETER_EXIF_T is a variable sized structure, hence all the
        # mucking about with string buffers here...
        buf = ct.create_string_buffer(
            ct.sizeof(mmal.MMAL_PARAMETER_EXIF_T) + len(tag) + len(value) + 1)
        mp = ct.cast(buf, ct.POINTER(mmal.MMAL_PARAMETER_EXIF_T))
        mp[0].hdr.id = mmal.MMAL_PARAMETER_EXIF
        mp[0].hdr.size = len(buf)
        if (b'=' in tag or b'\x00' in value):
            data = tag + value
            mp[0].keylen = len(tag)
            mp[0].value_offset = len(tag)
            mp[0].valuelen = len(value)
        else:
            data = tag + b'=' + value
        ct.memmove(mp[0].data, data, len(data))
        mmal_check(
            mmal.mmal_port_parameter_set(self.output_port, mp[0].hdr),
            prefix="Failed to set Exif tag %s" % tag)

    def start(self, output):
        timestamp = datetime.datetime.now()
        timestamp_tags = (
            'EXIF.DateTimeDigitized',
            'EXIF.DateTimeOriginal',
            'IFD0.DateTime')
        # Timestamp tags are always included with the value calculated
        # above, but the user may choose to override the value in the
        # exif_tags mapping
        for tag in timestamp_tags:
            self._add_exif_tag(tag, self.parent.exif_tags.get(tag, timestamp))
        # All other tags are just copied in verbatim
        for tag, value in self.parent.exif_tags.items():
            if not tag in timestamp_tags:
                self._add_exif_tag(tag, value)
        super(PiCookedOneImageEncoder, self).start(output)


class PiCookedMultiImageEncoder(PiMultiImageEncoder):
    # No Exif stuff here as video-port encodes (which is all
    # PiCookedMultiImageEncoder gets called for) don't support Exif output
    pass


class PiRawEncoderMixin(PiImageEncoder):

    RAW_ENCODINGS = {
        # name   mmal-encoding            bytes-per-pixel
        'yuv':  (mmal.MMAL_ENCODING_I420, 1.5),
        'rgb':  (mmal.MMAL_ENCODING_RGBA, 3),
        'rgba': (mmal.MMAL_ENCODING_RGBA, 4),
        'bgr':  (mmal.MMAL_ENCODING_BGRA, 3),
        'bgra': (mmal.MMAL_ENCODING_BGRA, 4),
        }

    def __init__(
            self, parent, camera_port, input_port, format, resize, **options):
        # If a resize hasn't been requested, check the input_port format. If
        # it requires conversion, force the use of a resizer to perform the
        # conversion
        if not resize:
            if parent.RAW_FORMATS[format] != input_port[0].format[0].encoding.value:
                resize = parent.resolution
        # Workaround: If a non-alpha format is requested when a resizer is
        # required, we use the alpha-inclusive format and set a flag to get the
        # callback to strip the alpha bytes (for some reason the resizer won't
        # work with non-alpha output formats - firmware bug?)
        if resize:
            width, height = resize
            self._strip_alpha = format in ('rgb', 'bgr')
        else:
            width, height = parent.resolution
            self._strip_alpha = False
        width = mmal.VCOS_ALIGN_UP(width, 32)
        height = mmal.VCOS_ALIGN_UP(height, 16)
        # Workaround (#83): when the resizer is used the width and height must
        # be aligned (both the actual and crop values) to avoid an error when
        # the output port format is set
        if resize:
            resize = (width, height)
        # Workaround: Calculate the expected image size, to be used by the
        # callback to decide when a frame ends. This is to work around a
        # firmware bug that causes the raw image to be returned twice when the
        # maximum camera resolution is requested
        self._expected_size = int(width * height * self.RAW_ENCODINGS[format][1])
        self._image_size = 0
        super(PiRawEncoderMixin, self).__init__(
                parent, camera_port, input_port, format, resize, **options)

    def _create_resizer(self, width, height):
        super(PiRawEncoderMixin, self)._create_resizer(width, height)
        encoding = self.RAW_ENCODINGS[self.format][0]
        port = self.resizer[0].output[0]
        port[0].format[0].encoding = encoding
        port[0].format[0].encoding_variant = encoding
        mmal_check(
            mmal.mmal_port_format_commit(port),
            prefix="Failed to set resizer output port format")

    def _create_encoder(self):
        # Overridden to skip creating an encoder. Instead we simply use the
        # resizer's port as the output port (if we have a resizer) or the
        # input port otherwise
        if self.resizer:
            self.output_port = self.resizer[0].output[0]
        else:
            self.output_port = self.input_port

    def _create_connection(self):
        # Overridden to skip creating an encoder connection; we only need the
        # resizer connection (if we have a resizer)
        if self.resizer:
            self.resizer_connection = self.parent._connect_ports(
                self.input_port, self.resizer[0].input[0])

    def _callback_write(self, buf):
        # Overridden to strip alpha bytes when necessary (see _create_resizer),
        # and manually calculate the frame end
        if buf[0].length and self._image_size:
            mmal_check(
                mmal.mmal_buffer_header_mem_lock(buf),
                prefix="Unable to lock buffer header memory")
            try:
                s = ct.string_at(buf[0].data, buf[0].length)
                if self._strip_alpha:
                    s = b''.join(s[i:i+3] for i in range(0, len(s), 4))
                with self.lock:
                    if self.output:
                        written = self.output.write(s)
                        # Ignore None return value; most Python 2 streams have
                        # no return value for write()
                        if (written is not None) and (written != len(s)):
                            raise PiCameraError(
                                "Unable to write buffer to file - aborting")
                        self._image_size -= len(s)
                        assert self._image_size >= 0
            finally:
                mmal.mmal_buffer_header_mem_unlock(buf)
        return self._image_size <= 0

    def start(self, output):
        self._image_size = self._expected_size
        super(PiRawEncoderMixin, self).start(output)


class PiRawOneImageEncoder(PiOneImageEncoder, PiRawEncoderMixin):
    pass


class PiRawMultiImageEncoder(PiMultiImageEncoder, PiRawEncoderMixin):
    def _next_output(self):
        super(PiRawMultiImageEncoder, self)._next_output()
        self._image_size = self._expected_size


########NEW FILE########
__FILENAME__ = exc
# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013,2014 Dave Hughes <dave@waveform.org.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str equivalent to Py3's
str = type('')


import picamera.mmal as mmal


__all__ = [
    'PiCameraWarning',
    'PiCameraError',
    'PiCameraRuntimeError',
    'PiCameraValueError',
    'PiCameraMMALError',
    'mmal_check',
    ]


class PiCameraWarning(Warning):
    """
    Base class for PiCamera warnings
    """


class PiCameraError(Exception):
    """
    Base class for PiCamera errors
    """


class PiCameraRuntimeError(PiCameraError, RuntimeError):
    """
    Raised when an invalid sequence of operations is attempted with a PiCamera object
    """


class PiCameraValueError(PiCameraError, ValueError):
    """
    Raised when an invalid value is fed to a PiCamera object
    """


class PiCameraMMALError(PiCameraError):
    """
    Raised when an MMAL operation fails for whatever reason
    """
    def __init__(self, status, prefix=""):
        self.status = status
        PiCameraError.__init__(self, "%s%s%s" % (prefix, ": " if prefix else "", {
            mmal.MMAL_ENOMEM:    "Out of memory",
            mmal.MMAL_ENOSPC:    "Out of resources (other than memory)",
            mmal.MMAL_EINVAL:    "Argument is invalid",
            mmal.MMAL_ENOSYS:    "Function not implemented",
            mmal.MMAL_ENOENT:    "No such file or directory",
            mmal.MMAL_ENXIO:     "No such device or address",
            mmal.MMAL_EIO:       "I/O error",
            mmal.MMAL_ESPIPE:    "Illegal seek",
            mmal.MMAL_ECORRUPT:  "Data is corrupt #FIXME not POSIX",
            mmal.MMAL_ENOTREADY: "Component is not ready #FIXME not POSIX",
            mmal.MMAL_ECONFIG:   "Component is not configured #FIXME not POSIX",
            mmal.MMAL_EISCONN:   "Port is already connected",
            mmal.MMAL_ENOTCONN:  "Port is disconnected",
            mmal.MMAL_EAGAIN:    "Resource temporarily unavailable; try again later",
            mmal.MMAL_EFAULT:    "Bad address",
            }.get(status, "Unknown status error")))


def mmal_check(status, prefix=""):
    """
    Checks the return status of an mmal call and raises an exception on
    failure.

    The optional prefix parameter specifies a prefix message to place at the
    start of the exception's message to provide some context.
    """
    if status != mmal.MMAL_SUCCESS:
        raise PiCameraMMALError(status, prefix)


########NEW FILE########
__FILENAME__ = mmal
# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python header conversion
# Copyright (c) 2013,2014 Dave Hughes <dave@waveform.org.uk>
#
# Original headers
# Copyright (c) 2012, Broadcom Europe Ltd
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str equivalent to Py3's
str = type('')

import ctypes as ct
import warnings

try:
    _lib = ct.CDLL('libmmal.so')
except OSError:
    warnings.warn(
        'Unable to locate libmmal.so; using a mock object instead. This '
        'functionality only exists to support building the package '
        'documentation on non-Raspberry Pi systems. If you see this message '
        'on the Raspberry Pi then you are missing a required library',
        RuntimeWarning)
    class _Mock(object):
        def __getattr__(self, attr):
            return self
        def __call__(self, *args, **kwargs):
            return self
    _lib = _Mock()

# vcos_types.h ###############################################################

def VCOS_ALIGN_UP(value, round_to):
    # Note: this function assumes round_to is some power of 2.
    return (value + (round_to - 1)) & ~(round_to - 1)

# mmal.h #####################################################################

MMAL_VERSION_MAJOR = 0
MMAL_VERSION_MINOR = 1
MMAL_VERSION = (MMAL_VERSION_MAJOR << 16 | MMAL_VERSION_MINOR)

def MMAL_VERSION_TO_MAJOR(a):
    return a >> 16

def MMAL_VERSION_TO_MINOR(a):
    return a & 0xFFFF

# mmal_common.h ##############################################################

def MMAL_FOURCC(s):
    return sum(ord(c) << (i * 8) for (i, c) in enumerate(s))

MMAL_MAGIC = MMAL_FOURCC('mmal')

MMAL_BOOL_T = ct.c_int32
MMAL_FALSE = 0
MMAL_TRUE = 1

class MMAL_CORE_STATISTICS_T(ct.Structure):
    _fields_ = [
        ('buffer_count',      ct.c_uint32),
        ('first_buffer_time', ct.c_uint32),
        ('last_buffer_time',  ct.c_uint32),
        ('max_delay',         ct.c_uint32),
        ]

class MMAL_CORE_PORT_STATISTICS_T(ct.Structure):
    _fields_ = [
        ('rx', MMAL_CORE_STATISTICS_T),
        ('tx', MMAL_CORE_STATISTICS_T),
        ]

MMAL_FIXED_16_16_T = ct.c_uint32

# mmal_types.h ###############################################################

MMAL_STATUS_T = ct.c_uint32 # enum
(
    MMAL_SUCCESS,
    MMAL_ENOMEM,
    MMAL_ENOSPC,
    MMAL_EINVAL,
    MMAL_ENOSYS,
    MMAL_ENOENT,
    MMAL_ENXIO,
    MMAL_EIO,
    MMAL_ESPIPE,
    MMAL_ECORRUPT,
    MMAL_ENOTREADY,
    MMAL_ECONFIG,
    MMAL_EISCONN,
    MMAL_ENOTCONN,
    MMAL_EAGAIN,
    MMAL_EFAULT,
) = range(0, 16)
MMAL_STATUS_MAX = 0x7FFFFFFF

class MMAL_RECT_T(ct.Structure):
    _fields_ = [
        ('x',      ct.c_int32),
        ('y',      ct.c_int32),
        ('width',  ct.c_int32),
        ('height', ct.c_int32),
        ]

    def __repr__(self):
        return '(%d, %d)->(%d, %d)' % (
                self.x, self.y, self.x + self.width, self.y + self.height)

class MMAL_RATIONAL_T(ct.Structure):
    _fields_ = [
        ('num',  ct.c_int32),
        ('den',  ct.c_int32),
        ]

    def __repr__(self):
        return '%d/%d' % (self.num, self.den)

MMAL_TIME_UNKNOWN = ct.c_int64(1<<63)

class MMAL_FOURCC_T(ct.c_uint32):
    def __repr__(self):
        return "MMAL_FOURCC('%s')" % ''.join(chr(self.value >> i & 0xFF) for i in range(0, 32, 8))

# mmal_format.h ##############################################################

MMAL_ES_TYPE_T = ct.c_uint32 # enum
(
   MMAL_ES_TYPE_UNKNOWN,
   MMAL_ES_TYPE_CONTROL,
   MMAL_ES_TYPE_AUDIO,
   MMAL_ES_TYPE_VIDEO,
   MMAL_ES_TYPE_SUBPICTURE,
) = range(5)

class MMAL_VIDEO_FORMAT_T(ct.Structure):
    _fields_ = [
        ('width',       ct.c_uint32),
        ('height',      ct.c_uint32),
        ('crop',        MMAL_RECT_T),
        ('frame_rate',  MMAL_RATIONAL_T),
        ('par',         MMAL_RATIONAL_T),
        ('color_space', MMAL_FOURCC_T),
        ]

    def __repr__(self):
        return '<MMAL_VIDEO_FORMAT_T width=%d, height=%d, crop=%r, frame_rate=%r, par=%r, color_space=%r>' % (
                self.width, self.height, self.crop, self.frame_rate, self.par, self.color_space)

class MMAL_AUDIO_FORMAT_T(ct.Structure):
    _fields_ = [
        ('channels',        ct.c_uint32),
        ('sample_rate',     ct.c_uint32),
        ('bits_per_sample', ct.c_uint32),
        ('block_align',     ct.c_uint32),
        ]

    def __repr__(self):
        return '<MMAL_AUDIO_FORMAT_T channels=%d, sample_rate=%d, bits_per_sample=%d, block_align=%d>' % (
                self.channels, self.sample_rate, self.bits_per_sample, self.block_align)

class MMAL_SUBPICTURE_FORMAT_T(ct.Structure):
    _fields_ = [
        ('x_offset', ct.c_uint32),
        ('y_offset', ct.c_uint32),
        ]

    def __repr__(self):
        return '<MMAL_SUBPICTURE_FORMAT_T x_offset=%d, y_offset=%d>' % (
                self.x_offset, self.y_offset)

class MMAL_ES_SPECIFIC_FORMAT_T(ct.Union):
    _fields_ = [
        ('audio',      MMAL_AUDIO_FORMAT_T),
        ('video',      MMAL_VIDEO_FORMAT_T),
        ('subpicture', MMAL_SUBPICTURE_FORMAT_T),
        ]

MMAL_ES_FORMAT_FLAG_FRAMED = 0x01
MMAL_ENCODING_UNKNOWN = 0
MMAL_ENCODING_VARIANT_DEFAULT = 0

class MMAL_ES_FORMAT_T(ct.Structure):
    _fields_ = [
        ('type',             MMAL_ES_TYPE_T),
        ('encoding',         MMAL_FOURCC_T),
        ('encoding_variant', MMAL_FOURCC_T),
        ('es',               ct.POINTER(MMAL_ES_SPECIFIC_FORMAT_T)),
        ('bitrate',          ct.c_uint32),
        ('flags',            ct.c_uint32),
        ('extradata_size',   ct.c_uint32),
        ('extradata',        ct.POINTER(ct.c_uint8)),
        ]

    def __repr__(self):
        return '<MMAL_ES_FORMAT_T type=%r, encoding=%r, ...>' % (self.type, self.encoding)

mmal_format_alloc = _lib.mmal_format_alloc
mmal_format_alloc.argtypes = []
mmal_format_alloc.restype = ct.POINTER(MMAL_ES_FORMAT_T)

mmal_format_free = _lib.mmal_format_free
mmal_format_free.argtypes = [ct.POINTER(MMAL_ES_FORMAT_T)]
mmal_format_free.restype = None

mmal_format_extradata_alloc = _lib.mmal_format_extradata_alloc
mmal_format_extradata_alloc.argtypes = [ct.POINTER(MMAL_ES_FORMAT_T), ct.c_uint]
mmal_format_extradata_alloc.restype = MMAL_STATUS_T

mmal_format_copy = _lib.mmal_format_copy
mmal_format_copy.argtypes = [ct.POINTER(MMAL_ES_FORMAT_T), ct.POINTER(MMAL_ES_FORMAT_T)]
mmal_format_copy.restype = None

mmal_format_full_copy = _lib.mmal_format_full_copy
mmal_format_full_copy.argtypes = [ct.POINTER(MMAL_ES_FORMAT_T), ct.POINTER(MMAL_ES_FORMAT_T)]
mmal_format_full_copy.restype = MMAL_STATUS_T

MMAL_ES_FORMAT_COMPARE_FLAG_TYPE             = 0x01
MMAL_ES_FORMAT_COMPARE_FLAG_ENCODING         = 0x02
MMAL_ES_FORMAT_COMPARE_FLAG_BITRATE          = 0x04
MMAL_ES_FORMAT_COMPARE_FLAG_FLAGS            = 0x08
MMAL_ES_FORMAT_COMPARE_FLAG_EXTRADATA        = 0x10

MMAL_ES_FORMAT_COMPARE_FLAG_VIDEO_RESOLUTION   = 0x0100
MMAL_ES_FORMAT_COMPARE_FLAG_VIDEO_CROPPING     = 0x0200
MMAL_ES_FORMAT_COMPARE_FLAG_VIDEO_FRAME_RATE   = 0x0400
MMAL_ES_FORMAT_COMPARE_FLAG_VIDEO_ASPECT_RATIO = 0x0800
MMAL_ES_FORMAT_COMPARE_FLAG_VIDEO_COLOR_SPACE  = 0x1000

MMAL_ES_FORMAT_COMPARE_FLAG_ES_OTHER = 0x10000000

mmal_format_compare = _lib.mmal_format_compare
mmal_format_compare.argtypes = [ct.POINTER(MMAL_ES_FORMAT_T), ct.POINTER(MMAL_ES_FORMAT_T)]
mmal_format_compare.restype = ct.c_uint32

# mmal_buffer.h ##############################################################

class MMAL_BUFFER_HEADER_VIDEO_SPECIFIC_T(ct.Structure):
    _fields_ = [
        ('planes', ct.c_uint32),
        ('offset', ct.c_uint32 * 4),
        ('pitch',  ct.c_uint32 * 4),
        ('flags',  ct.c_uint32),
        ]

class MMAL_BUFFER_HEADER_TYPE_SPECIFIC_T(ct.Union):
    _fields_ = [
        ('video', MMAL_BUFFER_HEADER_VIDEO_SPECIFIC_T),
        ]

class MMAL_BUFFER_HEADER_PRIVATE_T(ct.Structure):
    _fields_ = []

class MMAL_BUFFER_HEADER_T(ct.Structure):
    pass

MMAL_BUFFER_HEADER_T._fields_ = [
        ('next',       ct.POINTER(MMAL_BUFFER_HEADER_T)), # self-reference
        ('priv',       ct.POINTER(MMAL_BUFFER_HEADER_PRIVATE_T)),
        ('cmd',        ct.c_uint32),
        ('data',       ct.POINTER(ct.c_uint8)),
        ('alloc_size', ct.c_uint32),
        ('length',     ct.c_uint32),
        ('offset',     ct.c_uint32),
        ('flags',      ct.c_uint32),
        ('pts',        ct.c_int64),
        ('dts',        ct.c_int64),
        ('type',       ct.POINTER(MMAL_BUFFER_HEADER_TYPE_SPECIFIC_T)),
        ('user_data',  ct.c_void_p),
        ]

MMAL_BUFFER_HEADER_FLAG_EOS                    = (1<<0)
MMAL_BUFFER_HEADER_FLAG_FRAME_START            = (1<<1)
MMAL_BUFFER_HEADER_FLAG_FRAME_END              = (1<<2)
MMAL_BUFFER_HEADER_FLAG_FRAME                  = (MMAL_BUFFER_HEADER_FLAG_FRAME_START|MMAL_BUFFER_HEADER_FLAG_FRAME_END)
MMAL_BUFFER_HEADER_FLAG_KEYFRAME               = (1<<3)
MMAL_BUFFER_HEADER_FLAG_DISCONTINUITY          = (1<<4)
MMAL_BUFFER_HEADER_FLAG_CONFIG                 = (1<<5)
MMAL_BUFFER_HEADER_FLAG_ENCRYPTED              = (1<<6)
MMAL_BUFFER_HEADER_FLAG_CODECSIDEINFO          = (1<<7)
MMAL_BUFFER_HEADER_FLAGS_SNAPSHOT              = (1<<8)
MMAL_BUFFER_HEADER_FLAG_CORRUPTED              = (1<<9)
MMAL_BUFFER_HEADER_FLAG_TRANSMISSION_FAILED    = (1<<10)

MMAL_BUFFER_HEADER_VIDEO_FLAG_INTERLACED       = (1<<0)
MMAL_BUFFER_HEADER_VIDEO_FLAG_TOP_FIELD_FIRST  = (1<<2)
MMAL_BUFFER_HEADER_VIDEO_FLAG_DISPLAY_EXTERNAL = (1<<3)
MMAL_BUFFER_HEADER_VIDEO_FLAG_PROTECTED        = (1<<4)

mmal_buffer_header_acquire = _lib.mmal_buffer_header_acquire
mmal_buffer_header_acquire.argtypes = [ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_buffer_header_acquire.restype = None

mmal_buffer_header_reset = _lib.mmal_buffer_header_reset
mmal_buffer_header_reset.argtypes = [ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_buffer_header_reset.restype = None

mmal_buffer_header_release = _lib.mmal_buffer_header_release
mmal_buffer_header_release.argtypes = [ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_buffer_header_release.restype = None

mmal_buffer_header_release_continue = _lib.mmal_buffer_header_release_continue
mmal_buffer_header_release_continue.argtypes = [ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_buffer_header_release_continue.restype = None

MMAL_BH_PRE_RELEASE_CB_T = ct.CFUNCTYPE(
    MMAL_BOOL_T,
    ct.POINTER(MMAL_BUFFER_HEADER_T), ct.c_void_p)

mmal_buffer_header_pre_release_cb_set = _lib.mmal_buffer_header_pre_release_cb_set
mmal_buffer_header_pre_release_cb_set.argtypes = [ct.POINTER(MMAL_BUFFER_HEADER_T), MMAL_BH_PRE_RELEASE_CB_T, ct.c_void_p]
mmal_buffer_header_pre_release_cb_set.restype = None

mmal_buffer_header_replicate = _lib.mmal_buffer_header_replicate
mmal_buffer_header_replicate.argtypes = [ct.POINTER(MMAL_BUFFER_HEADER_T), ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_buffer_header_replicate.restype = MMAL_STATUS_T

mmal_buffer_header_mem_lock = _lib.mmal_buffer_header_mem_lock
mmal_buffer_header_mem_lock.argtypes = [ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_buffer_header_mem_lock.restype = MMAL_STATUS_T

mmal_buffer_header_mem_unlock = _lib.mmal_buffer_header_mem_unlock
mmal_buffer_header_mem_unlock.argtypes = [ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_buffer_header_mem_unlock.restype = None

# mmal_parameters_common.h ###################################################

MMAL_PARAMETER_GROUP_COMMON   = (0<<16)
MMAL_PARAMETER_GROUP_CAMERA   = (1<<16)
MMAL_PARAMETER_GROUP_VIDEO    = (2<<16)
MMAL_PARAMETER_GROUP_AUDIO    = (3<<16)
MMAL_PARAMETER_GROUP_CLOCK    = (4<<16)
MMAL_PARAMETER_GROUP_MIRACAST = (5<<16)

(
    MMAL_PARAMETER_UNUSED,
    MMAL_PARAMETER_SUPPORTED_ENCODINGS,
    MMAL_PARAMETER_URI,
    MMAL_PARAMETER_CHANGE_EVENT_REQUEST,
    MMAL_PARAMETER_ZERO_COPY,
    MMAL_PARAMETER_BUFFER_REQUIREMENTS,
    MMAL_PARAMETER_STATISTICS,
    MMAL_PARAMETER_CORE_STATISTICS,
    MMAL_PARAMETER_MEM_USAGE,
    MMAL_PARAMETER_BUFFER_FLAG_FILTER,
    MMAL_PARAMETER_SEEK,
    MMAL_PARAMETER_POWERMON_ENABLE,
    MMAL_PARAMETER_LOGGING,
    MMAL_PARAMETER_SYSTEM_TIME,
    MMAL_PARAMETER_NO_IMAGE_PADDING,
) = range(MMAL_PARAMETER_GROUP_COMMON, MMAL_PARAMETER_GROUP_COMMON + 15)

class MMAL_PARAMETER_HEADER_T(ct.Structure):
    _fields_ = [
        ('id',   ct.c_uint32),
        ('size', ct.c_uint32),
        ]

class MMAL_PARAMETER_CHANGE_EVENT_REQUEST_T(ct.Structure):
    _fields_ = [
        ('hdr',       MMAL_PARAMETER_HEADER_T),
        ('change_id', ct.c_uint32),
        ('enable',    MMAL_BOOL_T),
        ]

class MMAL_PARAMETER_BUFFER_REQUIREMENTS_T(ct.Structure):
    _fields_ = [
        ('hdr',                     MMAL_PARAMETER_HEADER_T),
        ('buffer_num_min',          ct.c_uint32),
        ('buffer_size_min',         ct.c_uint32),
        ('buffer_alignment_min',    ct.c_uint32),
        ('buffer_num_recommended',  ct.c_uint32),
        ('buffer_size_recommended', ct.c_uint32),
        ]

class MMAL_PARAMETER_SEEK_T(ct.Structure):
    _fields_ = [
        ('hdr',    MMAL_PARAMETER_HEADER_T),
        ('offset', ct.c_int64),
        ('flags',  ct.c_uint32),
        ]

MMAL_PARAM_SEEK_FLAG_PRECISE = 0x01
MMAL_PARAM_SEEK_FLAG_FORWARD = 0x02

class MMAL_PARAMETER_STATISTICS_T(ct.Structure):
    _fields_ = [
        ('hdr',                 MMAL_PARAMETER_HEADER_T),
        ('buffer_count',        ct.c_uint32),
        ('frame_count',         ct.c_uint32),
        ('frames_skipped',      ct.c_uint32),
        ('frames_discarded',    ct.c_uint32),
        ('eos_seen',            ct.c_uint32),
        ('maximum_frame_bytes', ct.c_uint32),
        ('total_bytes',         ct.c_int64),
        ('corrupt_macroblocks', ct.c_uint32),
        ]

MMAL_CORE_STATS_DIR = ct.c_uint32 # enum
(
    MMAL_CORE_STATS_RX,
    MMAL_CORE_STATS_TX,
) = range(2)
MMAL_CORE_STATS_MAX = 0x7fffffff

class MMAL_PARAMETER_CORE_STATISTICS_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('dir',   MMAL_CORE_STATS_DIR),
        ('reset', MMAL_BOOL_T),
        ('stats', MMAL_CORE_STATISTICS_T),
        ]

class MMAL_PARAMETER_MEM_USAGE_T(ct.Structure):
    _fields_ = [
        ('hdr',                 MMAL_PARAMETER_HEADER_T),
        ('pool_mem_alloc_size', ct.c_uint32),
        ]

class MMAL_PARAMETER_LOGGING_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('set',   ct.c_uint32),
        ('clear', ct.c_uint32),
        ]

# mmal_parameters_camera.h ###################################################

(
    MMAL_PARAMETER_THUMBNAIL_CONFIGURATION,
    MMAL_PARAMETER_CAPTURE_QUALITY,
    MMAL_PARAMETER_ROTATION,
    MMAL_PARAMETER_EXIF_DISABLE,
    MMAL_PARAMETER_EXIF,
    MMAL_PARAMETER_AWB_MODE,
    MMAL_PARAMETER_IMAGE_EFFECT,
    MMAL_PARAMETER_COLOUR_EFFECT,
    MMAL_PARAMETER_FLICKER_AVOID,
    MMAL_PARAMETER_FLASH,
    MMAL_PARAMETER_REDEYE,
    MMAL_PARAMETER_FOCUS,
    MMAL_PARAMETER_FOCAL_LENGTHS,
    MMAL_PARAMETER_EXPOSURE_COMP,
    MMAL_PARAMETER_ZOOM,
    MMAL_PARAMETER_MIRROR,
    MMAL_PARAMETER_CAMERA_NUM,
    MMAL_PARAMETER_CAPTURE,
    MMAL_PARAMETER_EXPOSURE_MODE,
    MMAL_PARAMETER_EXP_METERING_MODE,
    MMAL_PARAMETER_FOCUS_STATUS,
    MMAL_PARAMETER_CAMERA_CONFIG,
    MMAL_PARAMETER_CAPTURE_STATUS,
    MMAL_PARAMETER_FACE_TRACK,
    MMAL_PARAMETER_DRAW_BOX_FACES_AND_FOCUS,
    MMAL_PARAMETER_JPEG_Q_FACTOR,
    MMAL_PARAMETER_FRAME_RATE,
    MMAL_PARAMETER_USE_STC,
    MMAL_PARAMETER_CAMERA_INFO,
    MMAL_PARAMETER_VIDEO_STABILISATION,
    MMAL_PARAMETER_FACE_TRACK_RESULTS,
    MMAL_PARAMETER_ENABLE_RAW_CAPTURE,
    MMAL_PARAMETER_DPF_FILE,
    MMAL_PARAMETER_ENABLE_DPF_FILE,
    MMAL_PARAMETER_DPF_FAIL_IS_FATAL,
    MMAL_PARAMETER_CAPTURE_MODE,
    MMAL_PARAMETER_FOCUS_REGIONS,
    MMAL_PARAMETER_INPUT_CROP,
    MMAL_PARAMETER_SENSOR_INFORMATION,
    MMAL_PARAMETER_FLASH_SELECT,
    MMAL_PARAMETER_FIELD_OF_VIEW,
    MMAL_PARAMETER_HIGH_DYNAMIC_RANGE,
    MMAL_PARAMETER_DYNAMIC_RANGE_COMPRESSION,
    MMAL_PARAMETER_ALGORITHM_CONTROL,
    MMAL_PARAMETER_SHARPNESS,
    MMAL_PARAMETER_CONTRAST,
    MMAL_PARAMETER_BRIGHTNESS,
    MMAL_PARAMETER_SATURATION,
    MMAL_PARAMETER_ISO,
    MMAL_PARAMETER_ANTISHAKE,
    MMAL_PARAMETER_IMAGE_EFFECT_PARAMETERS,
    MMAL_PARAMETER_CAMERA_BURST_CAPTURE,
    MMAL_PARAMETER_CAMERA_MIN_ISO,
    MMAL_PARAMETER_CAMERA_USE_CASE,
    MMAL_PARAMETER_CAPTURE_STATS_PASS,
    MMAL_PARAMETER_CAMERA_CUSTOM_SENSOR_CONFIG,
    MMAL_PARAMETER_ENABLE_REGISTER_FILE,
    MMAL_PARAMETER_REGISTER_FAIL_IS_FATAL,
    MMAL_PARAMETER_CONFIGFILE_REGISTERS,
    MMAL_PARAMETER_CONFIGFILE_CHUNK_REGISTERS,
    MMAL_PARAMETER_JPEG_ATTACH_LOG,
    MMAL_PARAMETER_ZERO_SHUTTER_LAG,
    MMAL_PARAMETER_FPS_RANGE,
    MMAL_PARAMETER_CAPTURE_EXPOSURE_COMP,
    MMAL_PARAMETER_SW_SHARPEN_DISABLE,
    MMAL_PARAMETER_FLASH_REQUIRED,
    MMAL_PARAMETER_SW_SATURATION_DISABLE,
    MMAL_PARAMETER_SHUTTER_SPEED,
    MMAL_PARAMETER_CUSTOM_AWB_GAINS,
) = range(MMAL_PARAMETER_GROUP_CAMERA, MMAL_PARAMETER_GROUP_CAMERA + 69)

class MMAL_PARAMETER_THUMBNAIL_CONFIG_T(ct.Structure):
    _fields_ = [
        ('hdr',     MMAL_PARAMETER_HEADER_T),
        ('enable',  ct.c_uint32),
        ('width',   ct.c_uint32),
        ('height',  ct.c_uint32),
        ('quality', ct.c_uint32),
        ]

class MMAL_PARAMETER_EXIF_T(ct.Structure):
    _fields_ = [
        ('hdr',          MMAL_PARAMETER_HEADER_T),
        ('keylen',       ct.c_uint32),
        ('value_offset', ct.c_uint32),
        ('valuelen',     ct.c_uint32),
        ('data',         ct.c_uint8 * 1),
        ]

MMAL_PARAM_EXPOSUREMODE_T = ct.c_uint32 # enum
(
    MMAL_PARAM_EXPOSUREMODE_OFF,
    MMAL_PARAM_EXPOSUREMODE_AUTO,
    MMAL_PARAM_EXPOSUREMODE_NIGHT,
    MMAL_PARAM_EXPOSUREMODE_NIGHTPREVIEW,
    MMAL_PARAM_EXPOSUREMODE_BACKLIGHT,
    MMAL_PARAM_EXPOSUREMODE_SPOTLIGHT,
    MMAL_PARAM_EXPOSUREMODE_SPORTS,
    MMAL_PARAM_EXPOSUREMODE_SNOW,
    MMAL_PARAM_EXPOSUREMODE_BEACH,
    MMAL_PARAM_EXPOSUREMODE_VERYLONG,
    MMAL_PARAM_EXPOSUREMODE_FIXEDFPS,
    MMAL_PARAM_EXPOSUREMODE_ANTISHAKE,
    MMAL_PARAM_EXPOSUREMODE_FIREWORKS,
) = range(13)
MMAL_PARAM_EXPOSUREMODE_MAX = 0x7fffffff

class MMAL_PARAMETER_EXPOSUREMODE_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', MMAL_PARAM_EXPOSUREMODE_T),
        ]

MMAL_PARAM_EXPOSUREMETERINGMODE_T = ct.c_uint32 # enum
(
    MMAL_PARAM_EXPOSUREMETERINGMODE_AVERAGE,
    MMAL_PARAM_EXPOSUREMETERINGMODE_SPOT,
    MMAL_PARAM_EXPOSUREMETERINGMODE_BACKLIT,
    MMAL_PARAM_EXPOSUREMETERINGMODE_MATRIX,
) = range(4)
MMAL_PARAM_EXPOSUREMETERINGMODE_MAX = 0x7fffffff

class MMAL_PARAMETER_EXPOSUREMETERINGMODE_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', MMAL_PARAM_EXPOSUREMETERINGMODE_T),
        ]

MMAL_PARAM_AWBMODE_T = ct.c_uint32 # enum
(
    MMAL_PARAM_AWBMODE_OFF,
    MMAL_PARAM_AWBMODE_AUTO,
    MMAL_PARAM_AWBMODE_SUNLIGHT,
    MMAL_PARAM_AWBMODE_CLOUDY,
    MMAL_PARAM_AWBMODE_SHADE,
    MMAL_PARAM_AWBMODE_TUNGSTEN,
    MMAL_PARAM_AWBMODE_FLUORESCENT,
    MMAL_PARAM_AWBMODE_INCANDESCENT,
    MMAL_PARAM_AWBMODE_FLASH,
    MMAL_PARAM_AWBMODE_HORIZON,
) = range(10)
MMAL_PARAM_AWBMODE_MAX = 0x7fffffff

class MMAL_PARAMETER_AWBMODE_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', MMAL_PARAM_AWBMODE_T),
        ]

MMAL_PARAM_IMAGEFX_T = ct.c_uint32 # enum
(
    MMAL_PARAM_IMAGEFX_NONE,
    MMAL_PARAM_IMAGEFX_NEGATIVE,
    MMAL_PARAM_IMAGEFX_SOLARIZE,
    MMAL_PARAM_IMAGEFX_POSTERIZE,
    MMAL_PARAM_IMAGEFX_WHITEBOARD,
    MMAL_PARAM_IMAGEFX_BLACKBOARD,
    MMAL_PARAM_IMAGEFX_SKETCH,
    MMAL_PARAM_IMAGEFX_DENOISE,
    MMAL_PARAM_IMAGEFX_EMBOSS,
    MMAL_PARAM_IMAGEFX_OILPAINT,
    MMAL_PARAM_IMAGEFX_HATCH,
    MMAL_PARAM_IMAGEFX_GPEN,
    MMAL_PARAM_IMAGEFX_PASTEL,
    MMAL_PARAM_IMAGEFX_WATERCOLOUR,
    MMAL_PARAM_IMAGEFX_FILM,
    MMAL_PARAM_IMAGEFX_BLUR,
    MMAL_PARAM_IMAGEFX_SATURATION,
    MMAL_PARAM_IMAGEFX_COLOURSWAP,
    MMAL_PARAM_IMAGEFX_WASHEDOUT,
    MMAL_PARAM_IMAGEFX_POSTERISE,
    MMAL_PARAM_IMAGEFX_COLOURPOINT,
    MMAL_PARAM_IMAGEFX_COLOURBALANCE,
    MMAL_PARAM_IMAGEFX_CARTOON,
) = range(23)
MMAL_PARAM_IMAGEFX_MAX = 0x7fffffff

class MMAL_PARAMETER_IMAGEFX_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', MMAL_PARAM_IMAGEFX_T),
        ]

MMAL_MAX_IMAGEFX_PARAMETERS = 5

class MMAL_PARAMETER_IMAGEFX_PARAMETERS_T(ct.Structure):
    _fields_ = [
        ('hdr',               MMAL_PARAMETER_HEADER_T),
        ('effect',            MMAL_PARAM_IMAGEFX_T),
        ('num_effect_params', ct.c_uint32),
        ('effect_parameter',  ct.c_uint32 * MMAL_MAX_IMAGEFX_PARAMETERS),
        ]

class MMAL_PARAMETER_COLOURFX_T(ct.Structure):
    _fields_ = [
        ('hdr',    MMAL_PARAMETER_HEADER_T),
        ('enable', ct.c_int32),
        ('u',      ct.c_uint32),
        ('v',      ct.c_uint32),
        ]

MMAL_CAMERA_STC_MODE_T = ct.c_uint32 # enum
(
    MMAL_PARAM_STC_MODE_OFF,
    MMAL_PARAM_STC_MODE_RAW,
    MMAL_PARAM_STC_MODE_COOKED,
) = range(3)
MMAL_PARAM_STC_MODE_MAX = 0x7fffffff

class MMAL_PARAMETER_CAMERA_STC_MODE_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', MMAL_CAMERA_STC_MODE_T),
        ]

MMAL_PARAM_FLICKERAVOID_T = ct.c_uint32 # enum
(
    MMAL_PARAM_FLICKERAVOID_OFF,
    MMAL_PARAM_FLICKERAVOID_AUTO,
    MMAL_PARAM_FLICKERAVOID_50HZ,
    MMAL_PARAM_FLICKERAVOID_60HZ,
) = range(4)
MMAL_PARAM_FLICKERAVOID_MAX = 0x7FFFFFFF

class MMAL_PARAMETER_FLICKERAVOID_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', MMAL_PARAM_FLICKERAVOID_T),
        ]

MMAL_PARAM_FLASH_T = ct.c_uint32 # enum
(
    MMAL_PARAM_FLASH_OFF,
    MMAL_PARAM_FLASH_AUTO,
    MMAL_PARAM_FLASH_ON,
    MMAL_PARAM_FLASH_REDEYE,
    MMAL_PARAM_FLASH_FILLIN,
    MMAL_PARAM_FLASH_TORCH,
) = range(6)
MMAL_PARAM_FLASH_MAX = 0x7FFFFFFF

class MMAL_PARAMETER_FLASH_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', MMAL_PARAM_FLASH_T),
        ]

MMAL_PARAM_REDEYE_T = ct.c_uint32 # enum
(
    MMAL_PARAM_REDEYE_OFF,
    MMAL_PARAM_REDEYE_ON,
    MMAL_PARAM_REDEYE_SIMPLE,
) = range(3)
MMAL_PARAM_REDEYE_MAX = 0x7FFFFFFF

class MMAL_PARAMETER_REDEYE_T(ct.Structure):
    _fields_ = [
        ('hdr', MMAL_PARAMETER_HEADER_T),
        ('value', MMAL_PARAM_REDEYE_T),
        ]

MMAL_PARAM_FOCUS_T = ct.c_uint32 # enum
(
    MMAL_PARAM_FOCUS_AUTO,
    MMAL_PARAM_FOCUS_AUTO_NEAR,
    MMAL_PARAM_FOCUS_AUTO_MACRO,
    MMAL_PARAM_FOCUS_CAF,
    MMAL_PARAM_FOCUS_CAF_NEAR,
    MMAL_PARAM_FOCUS_FIXED_INFINITY,
    MMAL_PARAM_FOCUS_FIXED_HYPERFOCAL,
    MMAL_PARAM_FOCUS_FIXED_NEAR,
    MMAL_PARAM_FOCUS_FIXED_MACRO,
    MMAL_PARAM_FOCUS_EDOF,
    MMAL_PARAM_FOCUS_CAF_MACRO,
    MMAL_PARAM_FOCUS_CAF_FAST,
    MMAL_PARAM_FOCUS_CAF_NEAR_FAST,
    MMAL_PARAM_FOCUS_CAF_MACRO_FAST,
    MMAL_PARAM_FOCUS_FIXED_CURRENT,
) = range(15)
MMAL_PARAM_FOCUS_MAX = 0x7FFFFFFF

class MMAL_PARAMETER_FOCUS_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', MMAL_PARAM_FOCUS_T),
        ]

MMAL_PARAM_CAPTURE_STATUS_T = ct.c_uint32 # enum
(
    MMAL_PARAM_CAPTURE_STATUS_NOT_CAPTURING,
    MMAL_PARAM_CAPTURE_STATUS_CAPTURE_STARTED,
    MMAL_PARAM_CAPTURE_STATUS_CAPTURE_ENDED,
) = range(3)
MMAL_PARAM_CAPTURE_STATUS_MAX = 0x7FFFFFFF

class MMAL_PARAMETER_CAPTURE_STATUS_T(ct.Structure):
    _fields_ = [
        ('hdr',    MMAL_PARAMETER_HEADER_T),
        ('status', MMAL_PARAM_CAPTURE_STATUS_T),
        ]

MMAL_PARAM_FOCUS_STATUS_T = ct.c_uint32 # enum
(
    MMAL_PARAM_FOCUS_STATUS_OFF,
    MMAL_PARAM_FOCUS_STATUS_REQUEST,
    MMAL_PARAM_FOCUS_STATUS_REACHED,
    MMAL_PARAM_FOCUS_STATUS_UNABLE_TO_REACH,
    MMAL_PARAM_FOCUS_STATUS_LOST,
    MMAL_PARAM_FOCUS_STATUS_CAF_MOVING,
    MMAL_PARAM_FOCUS_STATUS_CAF_SUCCESS,
    MMAL_PARAM_FOCUS_STATUS_CAF_FAILED,
    MMAL_PARAM_FOCUS_STATUS_MANUAL_MOVING,
    MMAL_PARAM_FOCUS_STATUS_MANUAL_REACHED,
    MMAL_PARAM_FOCUS_STATUS_CAF_WATCHING,
    MMAL_PARAM_FOCUS_STATUS_CAF_SCENE_CHANGED,
) = range(12)
MMAL_PARAM_FOCUS_STATUS_MAX = 0x7FFFFFFF

class MMAL_PARAMETER_FOCUS_STATUS_T(ct.Structure):
    _fields_ = [
        ('hdr',    MMAL_PARAMETER_HEADER_T),
        ('status', MMAL_PARAM_FOCUS_STATUS_T),
        ]

MMAL_PARAM_FACE_TRACK_MODE_T = ct.c_uint32 # enum
(
    MMAL_PARAM_FACE_DETECT_NONE,
    MMAL_PARAM_FACE_DETECT_ON,
) = range(2)
MMAL_PARAM_FACE_DETECT_MAX = 0x7FFFFFFF

class MMAL_PARAMETER_FACE_TRACK_T(ct.Structure):
    _fields_ = [
        ('hdr',        MMAL_PARAMETER_HEADER_T),
        ('mode',       MMAL_PARAM_FACE_TRACK_MODE_T),
        ('maxRegions', ct.c_uint32),
        ('frames',     ct.c_uint32),
        ('quality',    ct.c_uint32),
        ]

class MMAL_PARAMETER_FACE_TRACK_FACE_T (ct.Structure):
    _fields_ = [
        ('face_id',    ct.c_int32),
        ('score',      ct.c_int32),
        ('face_rect',  MMAL_RECT_T),
        ('eye_rect',   MMAL_RECT_T * 2),
        ('mouth_rect', MMAL_RECT_T),
        ]

class MMAL_PARAMETER_FACE_TRACK_RESULTS_T (ct.Structure):
    _fields_ = [
        ('hdr',          MMAL_PARAMETER_HEADER_T),
        ('num_faces',    ct.c_uint32),
        ('frame_width',  ct.c_uint32),
        ('frame_height', ct.c_uint32),
        ('faces',        MMAL_PARAMETER_FACE_TRACK_FACE_T * 1),
        ]

MMAL_PARAMETER_CAMERA_CONFIG_TIMESTAMP_MODE_T = ct.c_uint32 # enum
(
    MMAL_PARAM_TIMESTAMP_MODE_ZERO,
    MMAL_PARAM_TIMESTAMP_MODE_RAW_STC,
    MMAL_PARAM_TIMESTAMP_MODE_RESET_STC,
) = range(3)
MMAL_PARAM_TIMESTAMP_MODE_MAX = 0x7FFFFFFF

class MMAL_PARAMETER_CAMERA_CONFIG_T(ct.Structure):
    _fields_ = [
        ('hdr',                                   MMAL_PARAMETER_HEADER_T),
        ('max_stills_w',                          ct.c_uint32),
        ('max_stills_h',                          ct.c_uint32),
        ('stills_yuv422',                         ct.c_uint32),
        ('one_shot_stills',                       ct.c_uint32),
        ('max_preview_video_w',                   ct.c_uint32),
        ('max_preview_video_h',                   ct.c_uint32),
        ('num_preview_video_frames',              ct.c_uint32),
        ('stills_capture_circular_buffer_height', ct.c_uint32),
        ('fast_preview_resume',                   ct.c_uint32),
        ('use_stc_timestamp',                     MMAL_PARAMETER_CAMERA_CONFIG_TIMESTAMP_MODE_T),
        ]

MMAL_PARAMETER_CAMERA_INFO_MAX_CAMERAS = 4
MMAL_PARAMETER_CAMERA_INFO_MAX_FLASHES = 2

class MMAL_PARAMETER_CAMERA_INFO_CAMERA_T(ct.Structure):
    _fields_ = [
        ('port_id',      ct.c_uint32),
        ('max_width',    ct.c_uint32),
        ('max_height',   ct.c_uint32),
        ('lens_present', MMAL_BOOL_T),
        ]

MMAL_PARAMETER_CAMERA_INFO_FLASH_TYPE_T = ct.c_uint32 # enum
MMAL_PARAMETER_CAMERA_INFO_FLASH_TYPE_XENON = 0
MMAL_PARAMETER_CAMERA_INFO_FLASH_TYPE_LED   = 1
MMAL_PARAMETER_CAMERA_INFO_FLASH_TYPE_OTHER = 2
MMAL_PARAMETER_CAMERA_INFO_FLASH_TYPE_MAX = 0x7FFFFFFF

class MMAL_PARAMETER_CAMERA_INFO_FLASH_T(ct.Structure):
    _fields_ = [
        ('flash_type', MMAL_PARAMETER_CAMERA_INFO_FLASH_TYPE_T),
        ]

class MMAL_PARAMETER_CAMERA_INFO_T(ct.Structure):
    _fields_ = [
        ('hdr',         MMAL_PARAMETER_HEADER_T),
        ('num_cameras', ct.c_uint32),
        ('num_flashes', ct.c_uint32),
        ('cameras',     MMAL_PARAMETER_CAMERA_INFO_CAMERA_T * MMAL_PARAMETER_CAMERA_INFO_MAX_CAMERAS),
        ('flashes',     MMAL_PARAMETER_CAMERA_INFO_FLASH_T * MMAL_PARAMETER_CAMERA_INFO_MAX_FLASHES),
        ]

MMAL_PARAMETER_CAPTUREMODE_MODE_T = ct.c_uint32 # enum
(
    MMAL_PARAM_CAPTUREMODE_WAIT_FOR_END,
    MMAL_PARAM_CAPTUREMODE_WAIT_FOR_END_AND_HOLD,
    MMAL_PARAM_CAPTUREMODE_RESUME_VF_IMMEDIATELY,
) = range(3)

class MMAL_PARAMETER_CAPTUREMODE_T(ct.Structure):
    _fields_ = [
        ('hdr',  MMAL_PARAMETER_HEADER_T),
        ('mode', MMAL_PARAMETER_CAPTUREMODE_MODE_T),
        ]

MMAL_PARAMETER_FOCUS_REGION_TYPE_T = ct.c_uint32 # enum
(
    MMAL_PARAMETER_FOCUS_REGION_TYPE_NORMAL,
    MMAL_PARAMETER_FOCUS_REGION_TYPE_FACE,
    MMAL_PARAMETER_FOCUS_REGION_TYPE_MAX,
) = range(3)

class MMAL_PARAMETER_FOCUS_REGION_T(ct.Structure):
    _fields_ = [
        ('rect',   MMAL_RECT_T),
        ('weight', ct.c_uint32),
        ('mask',   ct.c_uint32),
        ('type',   MMAL_PARAMETER_FOCUS_REGION_TYPE_T),
        ]

class MMAL_PARAMETER_FOCUS_REGIONS_T(ct.Structure):
    _fields_ = [
        ('hdr',           MMAL_PARAMETER_HEADER_T),
        ('num_regions',   ct.c_uint32),
        ('lock_to_faces', MMAL_BOOL_T),
        ('regions',       MMAL_PARAMETER_FOCUS_REGION_T * 1),
        ]

class MMAL_PARAMETER_INPUT_CROP_T(ct.Structure):
    _fields_ = [
        ('hdr',  MMAL_PARAMETER_HEADER_T),
        ('rect', MMAL_RECT_T),
        ]

class MMAL_PARAMETER_SENSOR_INFORMATION_T(ct.Structure):
    _fields_ = [
        ('hdr',             MMAL_PARAMETER_HEADER_T),
        ('f_number',        MMAL_RATIONAL_T),
        ('focal_length',    MMAL_RATIONAL_T),
        ('model_id',        ct.c_uint32),
        ('manufacturer_id', ct.c_uint32),
        ('revision',        ct.c_uint32),
        ]

class MMAL_PARAMETER_FLASH_SELECT_T(ct.Structure):
    _fields_ = [
        ('hdr',        MMAL_PARAMETER_HEADER_T),
        ('flash_type', MMAL_PARAMETER_CAMERA_INFO_FLASH_TYPE_T),
        ]

class MMAL_PARAMETER_FIELD_OF_VIEW_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('fov_h', MMAL_RATIONAL_T),
        ('fov_v', MMAL_RATIONAL_T),
        ]

MMAL_PARAMETER_DRC_STRENGTH_T = ct.c_uint32 # enum
(
    MMAL_PARAMETER_DRC_STRENGTH_OFF,
    MMAL_PARAMETER_DRC_STRENGTH_LOW,
    MMAL_PARAMETER_DRC_STRENGTH_MEDIUM,
    MMAL_PARAMETER_DRC_STRENGTH_HIGH,
) = range(4)
MMAL_PARAMETER_DRC_STRENGTH_MAX = 0x7fffffff

class MMAL_PARAMETER_DRC_T(ct.Structure):
    _fields_ = [
        ('hdr',      MMAL_PARAMETER_HEADER_T),
        ('strength', MMAL_PARAMETER_DRC_STRENGTH_T),
        ]

MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_T = ct.c_uint32 # enum
(
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_FACETRACKING,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_REDEYE_REDUCTION,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_VIDEO_STABILISATION,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_WRITE_RAW,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_VIDEO_DENOISE,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_STILLS_DENOISE,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_TEMPORAL_DENOISE,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_ANTISHAKE,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_IMAGE_EFFECTS,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_DYNAMIC_RANGE_COMPRESSION,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_FACE_RECOGNITION,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_FACE_BEAUTIFICATION,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_SCENE_DETECTION,
    MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_HIGH_DYNAMIC_RANGE,
) = range(14)
MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_MAX = 0x7fffffff

class MMAL_PARAMETER_ALGORITHM_CONTROL_T(ct.Structure):
    _fields_ = [
        ('hdr',       MMAL_PARAMETER_HEADER_T),
        ('algorithm', MMAL_PARAMETER_ALGORITHM_CONTROL_ALGORITHMS_T),
        ('enabled',   MMAL_BOOL_T),
        ]

MMAL_PARAM_CAMERA_USE_CASE_T = ct.c_uint32 # enum
(
   MMAL_PARAM_CAMERA_USE_CASE_UNKNOWN,
   MMAL_PARAM_CAMERA_USE_CASE_STILLS_CAPTURE,
   MMAL_PARAM_CAMERA_USE_CASE_VIDEO_CAPTURE,
) = range(3)
MMAL_PARAM_CAMERA_USE_CASE_MAX = 0x7fffffff

class MMAL_PARAMETER_CAMERA_USE_CASE_T(ct.Structure):
    _fields_ = [
        ('hdr',      MMAL_PARAMETER_HEADER_T),
        ('use_case', MMAL_PARAM_CAMERA_USE_CASE_T),
        ]

class MMAL_PARAMETER_FPS_RANGE_T(ct.Structure):
    _fields_ = [
        ('hdr',      MMAL_PARAMETER_HEADER_T),
        ('fps_low',  MMAL_RATIONAL_T),
        ('fps_high', MMAL_RATIONAL_T),
        ]

class MMAL_PARAMETER_ZEROSHUTTERLAG_T(ct.Structure):
    _fields_ = [
        ('hdr',                   MMAL_PARAMETER_HEADER_T),
        ('zero_shutter_lag_mode', MMAL_BOOL_T),
        ('concurrent_capture',    MMAL_BOOL_T),
        ]

class MMAL_PARAMETER_AWB_GAINS_T(ct.Structure):
    _fields_ = [
        ('hdr',    MMAL_PARAMETER_HEADER_T),
        ('r_gain', MMAL_RATIONAL_T),
        ('b_gain', MMAL_RATIONAL_T),
        ]

# mmal_parameters_video.h ####################################################

(
   MMAL_PARAMETER_DISPLAYREGION,
   MMAL_PARAMETER_SUPPORTED_PROFILES,
   MMAL_PARAMETER_PROFILE,
   MMAL_PARAMETER_INTRAPERIOD,
   MMAL_PARAMETER_RATECONTROL,
   MMAL_PARAMETER_NALUNITFORMAT,
   MMAL_PARAMETER_MINIMISE_FRAGMENTATION,
   MMAL_PARAMETER_MB_ROWS_PER_SLICE,
   MMAL_PARAMETER_VIDEO_LEVEL_EXTENSION,
   MMAL_PARAMETER_VIDEO_EEDE_ENABLE,
   MMAL_PARAMETER_VIDEO_EEDE_LOSSRATE,
   MMAL_PARAMETER_VIDEO_REQUEST_I_FRAME,
   MMAL_PARAMETER_VIDEO_INTRA_REFRESH,
   MMAL_PARAMETER_VIDEO_IMMUTABLE_INPUT,
   MMAL_PARAMETER_VIDEO_BIT_RATE,
   MMAL_PARAMETER_VIDEO_FRAME_RATE,
   MMAL_PARAMETER_VIDEO_ENCODE_MIN_QUANT,
   MMAL_PARAMETER_VIDEO_ENCODE_MAX_QUANT,
   MMAL_PARAMETER_VIDEO_ENCODE_RC_MODEL,
   MMAL_PARAMETER_EXTRA_BUFFERS,
   MMAL_PARAMETER_VIDEO_ALIGN_HORIZ,
   MMAL_PARAMETER_VIDEO_ALIGN_VERT,
   MMAL_PARAMETER_VIDEO_DROPPABLE_PFRAMES,
   MMAL_PARAMETER_VIDEO_ENCODE_INITIAL_QUANT,
   MMAL_PARAMETER_VIDEO_ENCODE_QP_P,
   MMAL_PARAMETER_VIDEO_ENCODE_RC_SLICE_DQUANT,
   MMAL_PARAMETER_VIDEO_ENCODE_FRAME_LIMIT_BITS,
   MMAL_PARAMETER_VIDEO_ENCODE_PEAK_RATE,
   MMAL_PARAMETER_VIDEO_ENCODE_H264_DISABLE_CABAC,
   MMAL_PARAMETER_VIDEO_ENCODE_H264_LOW_LATENCY,
   MMAL_PARAMETER_VIDEO_ENCODE_H264_AU_DELIMITERS,
   MMAL_PARAMETER_VIDEO_ENCODE_H264_DEBLOCK_IDC,
   MMAL_PARAMETER_VIDEO_ENCODE_H264_MB_INTRA_MODE,
   MMAL_PARAMETER_VIDEO_ENCODE_HEADER_ON_OPEN,
   MMAL_PARAMETER_VIDEO_ENCODE_PRECODE_FOR_QP,
   MMAL_PARAMETER_VIDEO_DRM_INIT_INFO,
   MMAL_PARAMETER_VIDEO_TIMESTAMP_FIFO,
   MMAL_PARAMETER_VIDEO_DECODE_ERROR_CONCEALMENT,
   MMAL_PARAMETER_VIDEO_DRM_PROTECT_BUFFER,
   MMAL_PARAMETER_VIDEO_DECODE_CONFIG_VD3,
   MMAL_PARAMETER_VIDEO_ENCODE_H264_VCL_HRD_PARAMETERS,
   MMAL_PARAMETER_VIDEO_ENCODE_H264_LOW_DELAY_HRD_FLAG,
   MMAL_PARAMETER_VIDEO_ENCODE_INLINE_HEADER,
   MMAL_PARAMETER_VIDEO_ENCODE_SEI_ENABLE,
   MMAL_PARAMETER_VIDEO_ENCODE_INLINE_VECTORS,
) = range(MMAL_PARAMETER_GROUP_VIDEO, MMAL_PARAMETER_GROUP_VIDEO + 45)

MMAL_DISPLAYTRANSFORM_T  = ct.c_uint32 # enum
MMAL_DISPLAY_ROT0 = 0
MMAL_DISPLAY_MIRROR_ROT0 = 1
MMAL_DISPLAY_MIRROR_ROT180 = 2
MMAL_DISPLAY_ROT180 = 3
MMAL_DISPLAY_MIRROR_ROT90 = 4
MMAL_DISPLAY_ROT270 = 5
MMAL_DISPLAY_ROT90 = 6
MMAL_DISPLAY_MIRROR_ROT270 = 7
MMAL_DISPLAY_DUMMY = 0x7FFFFFFF

MMAL_DISPLAYMODE_T = ct.c_uint32 # enum
MMAL_DISPLAY_MODE_FILL = 0
MMAL_DISPLAY_MODE_LETTERBOX = 1
MMAL_DISPLAY_MODE_DUMMY = 0x7FFFFFFF

MMAL_DISPLAYSET_T = ct.c_uint32 # enum
MMAL_DISPLAY_SET_NONE = 0
MMAL_DISPLAY_SET_NUM = 1
MMAL_DISPLAY_SET_FULLSCREEN = 2
MMAL_DISPLAY_SET_TRANSFORM = 4
MMAL_DISPLAY_SET_DEST_RECT = 8
MMAL_DISPLAY_SET_SRC_RECT = 0x10
MMAL_DISPLAY_SET_MODE = 0x20
MMAL_DISPLAY_SET_PIXEL = 0x40
MMAL_DISPLAY_SET_NOASPECT = 0x80
MMAL_DISPLAY_SET_LAYER = 0x100
MMAL_DISPLAY_SET_COPYPROTECT = 0x200
MMAL_DISPLAY_SET_ALPHA = 0x400
MMAL_DISPLAY_SET_DUMMY = 0x7FFFFFFF

class MMAL_DISPLAYREGION_T(ct.Structure):
    _fields_ = [
        ('hdr',                  MMAL_PARAMETER_HEADER_T),
        ('set',                  ct.c_uint32),
        ('display_num',          ct.c_uint32),
        ('fullscreen',           MMAL_BOOL_T),
        ('transform',            MMAL_DISPLAYTRANSFORM_T),
        ('dest_rect',            MMAL_RECT_T),
        ('src_rect',             MMAL_RECT_T),
        ('noaspect',             MMAL_BOOL_T),
        ('mode',                 MMAL_DISPLAYMODE_T),
        ('pixel_x',              ct.c_uint32),
        ('pixel_y',              ct.c_uint32),
        ('layer',                ct.c_int32),
        ('copyprotect_required', MMAL_BOOL_T),
        ('alpha',                ct.c_uint32),
        ]

MMAL_VIDEO_PROFILE_T = ct.c_uint32 # enum
(
    MMAL_VIDEO_PROFILE_H263_BASELINE,
    MMAL_VIDEO_PROFILE_H263_H320CODING,
    MMAL_VIDEO_PROFILE_H263_BACKWARDCOMPATIBLE,
    MMAL_VIDEO_PROFILE_H263_ISWV2,
    MMAL_VIDEO_PROFILE_H263_ISWV3,
    MMAL_VIDEO_PROFILE_H263_HIGHCOMPRESSION,
    MMAL_VIDEO_PROFILE_H263_INTERNET,
    MMAL_VIDEO_PROFILE_H263_INTERLACE,
    MMAL_VIDEO_PROFILE_H263_HIGHLATENCY,
    MMAL_VIDEO_PROFILE_MP4V_SIMPLE,
    MMAL_VIDEO_PROFILE_MP4V_SIMPLESCALABLE,
    MMAL_VIDEO_PROFILE_MP4V_CORE,
    MMAL_VIDEO_PROFILE_MP4V_MAIN,
    MMAL_VIDEO_PROFILE_MP4V_NBIT,
    MMAL_VIDEO_PROFILE_MP4V_SCALABLETEXTURE,
    MMAL_VIDEO_PROFILE_MP4V_SIMPLEFACE,
    MMAL_VIDEO_PROFILE_MP4V_SIMPLEFBA,
    MMAL_VIDEO_PROFILE_MP4V_BASICANIMATED,
    MMAL_VIDEO_PROFILE_MP4V_HYBRID,
    MMAL_VIDEO_PROFILE_MP4V_ADVANCEDREALTIME,
    MMAL_VIDEO_PROFILE_MP4V_CORESCALABLE,
    MMAL_VIDEO_PROFILE_MP4V_ADVANCEDCODING,
    MMAL_VIDEO_PROFILE_MP4V_ADVANCEDCORE,
    MMAL_VIDEO_PROFILE_MP4V_ADVANCEDSCALABLE,
    MMAL_VIDEO_PROFILE_MP4V_ADVANCEDSIMPLE,
    MMAL_VIDEO_PROFILE_H264_BASELINE,
    MMAL_VIDEO_PROFILE_H264_MAIN,
    MMAL_VIDEO_PROFILE_H264_EXTENDED,
    MMAL_VIDEO_PROFILE_H264_HIGH,
    MMAL_VIDEO_PROFILE_H264_HIGH10,
    MMAL_VIDEO_PROFILE_H264_HIGH422,
    MMAL_VIDEO_PROFILE_H264_HIGH444,
    MMAL_VIDEO_PROFILE_H264_CONSTRAINED_BASELINE,
) = range(33)
MMAL_VIDEO_PROFILE_DUMMY = 0x7FFFFFFF

MMAL_VIDEO_LEVEL_T = ct.c_uint32 # enum
(
    MMAL_VIDEO_LEVEL_H263_10,
    MMAL_VIDEO_LEVEL_H263_20,
    MMAL_VIDEO_LEVEL_H263_30,
    MMAL_VIDEO_LEVEL_H263_40,
    MMAL_VIDEO_LEVEL_H263_45,
    MMAL_VIDEO_LEVEL_H263_50,
    MMAL_VIDEO_LEVEL_H263_60,
    MMAL_VIDEO_LEVEL_H263_70,
    MMAL_VIDEO_LEVEL_MP4V_0,
    MMAL_VIDEO_LEVEL_MP4V_0b,
    MMAL_VIDEO_LEVEL_MP4V_1,
    MMAL_VIDEO_LEVEL_MP4V_2,
    MMAL_VIDEO_LEVEL_MP4V_3,
    MMAL_VIDEO_LEVEL_MP4V_4,
    MMAL_VIDEO_LEVEL_MP4V_4a,
    MMAL_VIDEO_LEVEL_MP4V_5,
    MMAL_VIDEO_LEVEL_MP4V_6,
    MMAL_VIDEO_LEVEL_H264_1,
    MMAL_VIDEO_LEVEL_H264_1b,
    MMAL_VIDEO_LEVEL_H264_11,
    MMAL_VIDEO_LEVEL_H264_12,
    MMAL_VIDEO_LEVEL_H264_13,
    MMAL_VIDEO_LEVEL_H264_2,
    MMAL_VIDEO_LEVEL_H264_21,
    MMAL_VIDEO_LEVEL_H264_22,
    MMAL_VIDEO_LEVEL_H264_3,
    MMAL_VIDEO_LEVEL_H264_31,
    MMAL_VIDEO_LEVEL_H264_32,
    MMAL_VIDEO_LEVEL_H264_4,
    MMAL_VIDEO_LEVEL_H264_41,
    MMAL_VIDEO_LEVEL_H264_42,
    MMAL_VIDEO_LEVEL_H264_5,
    MMAL_VIDEO_LEVEL_H264_51,
) = range(33)
MMAL_VIDEO_LEVEL_DUMMY = 0x7FFFFFFF

class MMAL_PARAMETER_VIDEO_PROFILE_S(ct.Structure):
    _fields_ = [
        ('profile', MMAL_VIDEO_PROFILE_T),
        ('level',   MMAL_VIDEO_LEVEL_T),
        ]

class MMAL_PARAMETER_VIDEO_PROFILE_T(ct.Structure):
    _fields_ = [
        ('hdr', MMAL_PARAMETER_HEADER_T),
        ('profile', MMAL_PARAMETER_VIDEO_PROFILE_S * 1),
        ]

MMAL_VIDEO_RATECONTROL_T = ct.c_uint32 # enum
(
    MMAL_VIDEO_RATECONTROL_DEFAULT,
    MMAL_VIDEO_RATECONTROL_VARIABLE,
    MMAL_VIDEO_RATECONTROL_CONSTANT,
    MMAL_VIDEO_RATECONTROL_VARIABLE_SKIP_FRAMES,
    MMAL_VIDEO_RATECONTROL_CONSTANT_SKIP_FRAMES,
) = range(5)
MMAL_VIDEO_RATECONTROL_DUMMY = 0x7fffffff

MMAL_VIDEO_INTRA_REFRESH_T = ct.c_uint32
(
    MMAL_VIDEO_INTRA_REFRESH_CYCLIC,
    MMAL_VIDEO_INTRA_REFRESH_ADAPTIVE,
    MMAL_VIDEO_INTRA_REFRESH_BOTH,
) = range(3)
MMAL_VIDEO_INTRA_REFRESH_KHRONOSEXTENSIONS = 0x6F000000
MMAL_VIDEO_INTRA_REFRESH_VENDORSTARTUNUSED = 0x7F000000
(
    MMAL_VIDEO_INTRA_REFRESH_CYCLIC_MROWS,
    MMAL_VIDEO_INTRA_REFRESH_PSEUDO_RAND,
    MMAL_VIDEO_INTRA_REFRESH_MAX,
) = range(MMAL_VIDEO_INTRA_REFRESH_VENDORSTARTUNUSED, MMAL_VIDEO_INTRA_REFRESH_VENDORSTARTUNUSED + 3)
MMAL_VIDEO_INTRA_REFRESH_DUMMY         = 0x7FFFFFFF

MMAL_VIDEO_ENCODE_RC_MODEL_T = ct.c_uint32
MMAL_VIDEO_ENCODER_RC_MODEL_DEFAULT = 0
(
    MMAL_VIDEO_ENCODER_RC_MODEL_JVT,
    MMAL_VIDEO_ENCODER_RC_MODEL_VOWIFI,
    MMAL_VIDEO_ENCODER_RC_MODEL_CBR,
    MMAL_VIDEO_ENCODER_RC_MODEL_LAST,
) = range(MMAL_VIDEO_ENCODER_RC_MODEL_DEFAULT, MMAL_VIDEO_ENCODER_RC_MODEL_DEFAULT + 4)
MMAL_VIDEO_ENCODER_RC_MODEL_DUMMY      = 0x7FFFFFFF

class MMAL_PARAMETER_VIDEO_ENCODE_RC_MODEL_T(ct.Structure):
    _fields_ = [
        ('hdr',      MMAL_PARAMETER_HEADER_T),
        ('rc_model', MMAL_VIDEO_ENCODE_RC_MODEL_T),
        ]

class MMAL_PARAMETER_VIDEO_RATECONTROL_T(ct.Structure):
    _fields_ = [
        ('hdr',     MMAL_PARAMETER_HEADER_T),
        ('control', MMAL_VIDEO_RATECONTROL_T),
        ]

MMAL_VIDEO_ENCODE_H264_MB_INTRA_MODES_T = ct.c_uint32 # enum
MMAL_VIDEO_ENCODER_H264_MB_4x4_INTRA = 1
MMAL_VIDEO_ENCODER_H264_MB_8x8_INTRA = 2
MMAL_VIDEO_ENCODER_H264_MB_16x16_INTRA = 4
MMAL_VIDEO_ENCODER_H264_MB_INTRA_DUMMY = 0x7fffffff

class MMAL_PARAMETER_VIDEO_ENCODER_H264_MB_INTRA_MODES_T(ct.Structure):
    _fields_ = [
        ('hdr',     MMAL_PARAMETER_HEADER_T),
        ('mb_mode', MMAL_VIDEO_ENCODE_H264_MB_INTRA_MODES_T),
        ]

MMAL_VIDEO_NALUNITFORMAT_T = ct.c_uint32
MMAL_VIDEO_NALUNITFORMAT_STARTCODES = 1
MMAL_VIDEO_NALUNITFORMAT_NALUNITPERBUFFER = 2
MMAL_VIDEO_NALUNITFORMAT_ONEBYTEINTERLEAVELENGTH = 4
MMAL_VIDEO_NALUNITFORMAT_TWOBYTEINTERLEAVELENGTH = 8
MMAL_VIDEO_NALUNITFORMAT_FOURBYTEINTERLEAVELENGTH = 16
MMAL_VIDEO_NALUNITFORMAT_DUMMY = 0x7fffffff

class MMAL_PARAMETER_VIDEO_NALUNITFORMAT_T(ct.Structure):
    _fields_ = [
        ('hdr',    MMAL_PARAMETER_HEADER_T),
        ('format', MMAL_VIDEO_NALUNITFORMAT_T),
        ]

class MMAL_PARAMETER_VIDEO_LEVEL_EXTENSION_T(ct.Structure):
    _fields_ = [
        ('hdr',                   MMAL_PARAMETER_HEADER_T),
        ('custom_max_mbps',       ct.c_uint32),
        ('custom_max_fs',         ct.c_uint32),
        ('custom_max_br_and_cpb', ct.c_uint32),
        ]

class MMAL_PARAMETER_VIDEO_INTRA_REFRESH_T(ct.Structure):
    _fields_ = [
        ('hdr',          MMAL_PARAMETER_HEADER_T),
        ('refresh_mode', MMAL_VIDEO_INTRA_REFRESH_T),
        ('air_mbs',      ct.c_uint32),
        ('air_ref',      ct.c_uint32),
        ('cir_mbs',      ct.c_uint32),
        ('pir_mbs',      ct.c_uint32),
        ]

class MMAL_PARAMETER_VIDEO_EEDE_ENABLE_T(ct.Structure):
    _fields_ = [
        ('hdr',    MMAL_PARAMETER_HEADER_T),
        ('enable', ct.c_uint32),
        ]

class MMAL_PARAMETER_VIDEO_EEDE_LOSSRATE_T(ct.Structure):
    _fields_ = [
        ('hdr',       MMAL_PARAMETER_HEADER_T),
        ('loss_rate', ct.c_uint32),
        ]

class MMAL_PARAMETER_VIDEO_DRM_INIT_INFO_T(ct.Structure):
    _fields_ = [
        ('hdr',           MMAL_PARAMETER_HEADER_T),
        ('current_time',  ct.c_uint32),
        ('ticks_per_sec', ct.c_uint32),
        ('lhs',           ct.c_uint8 * 32),
        ]

class MMAL_PARAMETER_VIDEO_DRM_PROTECT_BUFFER_T(ct.Structure):
    _fields_ = [
        ('hdr',         MMAL_PARAMETER_HEADER_T),
        ('size_wanted', ct.c_uint32),
        ('protect',     ct.c_uint32),
        ('mem_handle',  ct.c_uint32),
        ('phys_addr',   ct.c_void_p),
        ]

# mmal_parameters_audio.h ####################################################

(
   MMAL_PARAMETER_AUDIO_DESTINATION,
   MMAL_PARAMETER_AUDIO_LATENCY_TARGET,
   MMAL_PARAMETER_AUDIO_SOURCE
) = range(MMAL_PARAMETER_GROUP_AUDIO, MMAL_PARAMETER_GROUP_AUDIO + 3)

class MMAL_PARAMETER_AUDIO_LATENCY_TARGET_T(ct.Structure):
    _fields_ = [
        ('hdr',          MMAL_PARAMETER_HEADER_T),
        ('enable',       MMAL_BOOL_T),
        ('filter',       ct.c_uint32),
        ('target',       ct.c_uint32),
        ('shift',        ct.c_uint32),
        ('speed_factor', ct.c_int32),
        ('inter_factor', ct.c_int32),
        ('adj_cap',      ct.c_int32),
        ]

# mmal_parameters_clock.h ####################################################

(
   MMAL_PARAMETER_CLOCK_REFERENCE,
   MMAL_PARAMETER_CLOCK_ACTIVE,
   MMAL_PARAMETER_CLOCK_SCALE,
   MMAL_PARAMETER_CLOCK_TIME,
   MMAL_PARAMETER_CLOCK_TIME_OFFSET,
   MMAL_PARAMETER_CLOCK_UPDATE_THRESHOLD,
   MMAL_PARAMETER_CLOCK_DISCONT_THRESHOLD,
   MMAL_PARAMETER_CLOCK_REQUEST_THRESHOLD,
) = range(MMAL_PARAMETER_GROUP_CLOCK, MMAL_PARAMETER_GROUP_CLOCK + 8)

class MMAL_PARAMETER_CLOCK_UPDATE_THRESHOLD_T(ct.Structure):
    _fields_ = [
        ('hdr',             MMAL_PARAMETER_HEADER_T),
        ('threshold_lower', ct.c_int64),
        ('threshold_upper', ct.c_int64),
        ]

class MMAL_PARAMETER_CLOCK_DISCONT_THRESHOLD_T(ct.Structure):
    _fields_ = [
        ('hdr',       MMAL_PARAMETER_HEADER_T),
        ('threshold', ct.c_int64),
        ('duration',  ct.c_int64),
        ]

class MMAL_PARAMETER_CLOCK_REQUEST_THRESHOLD_T(ct.Structure):
    _fields_ = [
        ('hdr',              MMAL_PARAMETER_HEADER_T),
        ('threshold',        ct.c_int64),
        ('threshold_enable', MMAL_BOOL_T),
        ]

# mmal_parameters.h ##########################################################

class MMAL_PARAMETER_UINT64_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', ct.c_uint64),
        ]

class MMAL_PARAMETER_INT64_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', ct.c_int64),
        ]

class MMAL_PARAMETER_UINT32_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', ct.c_uint32),
        ]

class MMAL_PARAMETER_INT32_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', ct.c_int32),
        ]

class MMAL_PARAMETER_RATIONAL_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', MMAL_RATIONAL_T),
        ]

class MMAL_PARAMETER_BOOLEAN_T(ct.Structure):
    _fields_ = [
        ('hdr',    MMAL_PARAMETER_HEADER_T),
        ('enable', MMAL_BOOL_T),
        ]

class MMAL_PARAMETER_STRING_T(ct.Structure):
    _fields_ = [
        ('hdr', MMAL_PARAMETER_HEADER_T),
        ('str', ct.c_char_p),
        ]

class MMAL_PARAMETER_BYTES_T(ct.Structure):
    _fields_ = [
        ('hdr',  MMAL_PARAMETER_HEADER_T),
        ('data', ct.POINTER(ct.c_uint8)),
        ]

#define MMAL_FIXED_16_16_ONE  (1 << 16)

class MMAL_PARAMETER_SCALEFACTOR_T(ct.Structure):
    _fields_ = [
        ('hdr',     MMAL_PARAMETER_HEADER_T),
        ('scale_x', MMAL_FIXED_16_16_T),
        ('scale_y', MMAL_FIXED_16_16_T),
        ]

MMAL_PARAM_MIRROR_T = ct.c_uint32 # enum
(
   MMAL_PARAM_MIRROR_NONE,
   MMAL_PARAM_MIRROR_VERTICAL,
   MMAL_PARAM_MIRROR_HORIZONTAL,
   MMAL_PARAM_MIRROR_BOTH,
) = range(4)

class MMAL_PARAMETER_MIRROR_T(ct.Structure):
    _fields_ = [
        ('hdr',   MMAL_PARAMETER_HEADER_T),
        ('value', MMAL_PARAM_MIRROR_T),
        ]

class MMAL_PARAMETER_URI_T(ct.Structure):
    _fields_ = [
        ('hdr', MMAL_PARAMETER_HEADER_T),
        ('uri', ct.c_char_p),
        ]

class MMAL_PARAMETER_ENCODING_T(ct.Structure):
    _fields_ = [
        ('hdr',      MMAL_PARAMETER_HEADER_T),
        ('encoding', ct.POINTER(ct.c_uint32)),
        ]

class MMAL_PARAMETER_FRAME_RATE_T(ct.Structure):
    _fields_ = [
        ('hdr',        MMAL_PARAMETER_HEADER_T),
        ('frame_rate', MMAL_RATIONAL_T),
        ]

class MMAL_PARAMETER_CONFIGFILE_T(ct.Structure):
    _fields_ = [
        ('hdr',       MMAL_PARAMETER_HEADER_T),
        ('file_size', ct.c_uint32),
        ]

class MMAL_PARAMETER_CONFIGFILE_CHUNK_T(ct.Structure):
    _fields_ = [
        ('hdr',    MMAL_PARAMETER_HEADER_T),
        ('size',   ct.c_uint32),
        ('offset', ct.c_uint32),
        ('data',   ct.c_char_p),
        ]

# mmal_port.h ################################################################

MMAL_PORT_TYPE_T = ct.c_uint32 # enum
(
    MMAL_PORT_TYPE_UNKNOWN,
    MMAL_PORT_TYPE_CONTROL,
    MMAL_PORT_TYPE_INPUT,
    MMAL_PORT_TYPE_OUTPUT,
    MMAL_PORT_TYPE_CLOCK,
) = range(5)
MMAL_PORT_TYPE_INVALID = 0xffffffff

MMAL_PORT_CAPABILITY_PASSTHROUGH = 0x01
MMAL_PORT_CAPABILITY_ALLOCATION = 0x02
MMAL_PORT_CAPABILITY_SUPPORTS_EVENT_FORMAT_CHANGE = 0x04

class MMAL_PORT_PRIVATE_T(ct.Structure):
    _fields_ = []

class MMAL_PORT_T(ct.Structure):
    # NOTE Defined in mmal_component.h below after definition of MMAL_COMPONENT_T
    pass

mmal_port_format_commit = _lib.mmal_port_format_commit
mmal_port_format_commit.argtypes = [ct.POINTER(MMAL_PORT_T)]
mmal_port_format_commit.restype = MMAL_STATUS_T

MMAL_PORT_BH_CB_T = ct.CFUNCTYPE(
    None,
    ct.POINTER(MMAL_PORT_T), ct.POINTER(MMAL_BUFFER_HEADER_T))

mmal_port_enable = _lib.mmal_port_enable
mmal_port_enable.argtypes = [ct.POINTER(MMAL_PORT_T), MMAL_PORT_BH_CB_T]
mmal_port_enable.restype = MMAL_STATUS_T

mmal_port_disable = _lib.mmal_port_disable
mmal_port_disable.argtypes = [ct.POINTER(MMAL_PORT_T)]
mmal_port_disable.restype = MMAL_STATUS_T

mmal_port_flush = _lib.mmal_port_flush
mmal_port_flush.argtypes = [ct.POINTER(MMAL_PORT_T)]
mmal_port_flush.restype = MMAL_STATUS_T

mmal_port_parameter_set = _lib.mmal_port_parameter_set
mmal_port_parameter_set.argtypes = [ct.POINTER(MMAL_PORT_T), ct.POINTER(MMAL_PARAMETER_HEADER_T)]
mmal_port_parameter_set.restype = MMAL_STATUS_T

mmal_port_parameter_get = _lib.mmal_port_parameter_get
mmal_port_parameter_get.argtypes = [ct.POINTER(MMAL_PORT_T), ct.POINTER(MMAL_PARAMETER_HEADER_T)]
mmal_port_parameter_get.restype = MMAL_STATUS_T

mmal_port_send_buffer = _lib.mmal_port_send_buffer
mmal_port_send_buffer.argtypes = [ct.POINTER(MMAL_PORT_T), ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_port_send_buffer.restype = MMAL_STATUS_T

mmal_port_connect = _lib.mmal_port_connect
mmal_port_connect.argtypes = [ct.POINTER(MMAL_PORT_T), ct.POINTER(MMAL_PORT_T)]
mmal_port_connect.restype = MMAL_STATUS_T

mmal_port_disconnect = _lib.mmal_port_disconnect
mmal_port_disconnect.argtypes = [ct.POINTER(MMAL_PORT_T)]
mmal_port_disconnect.restype = MMAL_STATUS_T

mmal_port_payload_alloc = _lib.mmal_port_payload_alloc
mmal_port_payload_alloc.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32]
mmal_port_payload_alloc.restype = ct.POINTER(ct.c_uint8)

mmal_port_payload_free = _lib.mmal_port_payload_free
mmal_port_payload_free.argtypes = [ct.POINTER(MMAL_PORT_T), ct.POINTER(ct.c_uint8)]
mmal_port_payload_free.restype = None

mmal_port_event_get = _lib.mmal_port_event_get
mmal_port_event_get.argtypes = [ct.POINTER(MMAL_PORT_T), ct.POINTER(ct.POINTER(MMAL_BUFFER_HEADER_T)), ct.c_uint32]
mmal_port_event_get.restype = MMAL_STATUS_T

# mmal_component.h ###########################################################

class MMAL_COMPONENT_PRIVATE_T(ct.Structure):
    _fields_ = []

class MMAL_COMPONENT_T(ct.Structure):
    _fields_ = [
        ('priv',       ct.POINTER(MMAL_COMPONENT_PRIVATE_T)),
        ('userdata',   ct.c_void_p),
        ('name',       ct.c_char_p),
        ('is_enabled', ct.c_uint32),
        ('control',    ct.POINTER(MMAL_PORT_T)),
        ('input_num',  ct.c_uint32),
        ('input',      ct.POINTER(ct.POINTER(MMAL_PORT_T))),
        ('output_num', ct.c_uint32),
        ('output',     ct.POINTER(ct.POINTER(MMAL_PORT_T))),
        ('clock_num',  ct.c_uint32),
        ('clock',      ct.POINTER(ct.POINTER(MMAL_PORT_T))),
        ('port_num',   ct.c_uint32),
        ('port',       ct.POINTER(ct.POINTER(MMAL_PORT_T))),
        ('id',         ct.c_uint32),
        ]

# NOTE MMAL_PORT_T's fields are declared here as they reference
# MMAL_COMPONENT_T which in turn references MMAL_PORT_T, hence the empty
# forward decl in mmal_port.h above

MMAL_PORT_T._fields_ = [
        ('priv',                    ct.POINTER(MMAL_PORT_PRIVATE_T)),
        ('name',                    ct.c_char_p),
        ('type',                    MMAL_PORT_TYPE_T),
        ('index',                   ct.c_uint16),
        ('index_all',               ct.c_uint16),
        ('is_enabled',              ct.c_uint32),
        ('format',                  ct.POINTER(MMAL_ES_FORMAT_T)),
        ('buffer_num_min',          ct.c_uint32),
        ('buffer_size_min',         ct.c_uint32),
        ('buffer_alignment_min',    ct.c_uint32),
        ('buffer_num_recommended',  ct.c_uint32),
        ('buffer_size_recommended', ct.c_uint32),
        ('buffer_num',              ct.c_uint32),
        ('buffer_size',             ct.c_uint32),
        ('component',               ct.POINTER(MMAL_COMPONENT_T)),
        ('userdata',                ct.c_void_p),
        ('capabilities',            ct.c_uint32),
        ]

mmal_component_create = _lib.mmal_component_create
mmal_component_create.argtypes = [ct.c_char_p, ct.POINTER(ct.POINTER(MMAL_COMPONENT_T))]
mmal_component_create.restype = MMAL_STATUS_T

mmal_component_acquire = _lib.mmal_component_acquire
mmal_component_acquire.argtypes = [ct.POINTER(MMAL_COMPONENT_T)]
mmal_component_acquire.restype = None

mmal_component_release = _lib.mmal_component_release
mmal_component_release.argtypes = [ct.POINTER(MMAL_COMPONENT_T)]
mmal_component_release.restype = MMAL_STATUS_T

mmal_component_destroy = _lib.mmal_component_destroy
mmal_component_destroy.argtypes = [ct.POINTER(MMAL_COMPONENT_T)]
mmal_component_destroy.restype = MMAL_STATUS_T

mmal_component_enable = _lib.mmal_component_enable
mmal_component_enable.argtypes = [ct.POINTER(MMAL_COMPONENT_T)]
mmal_component_enable.restype = MMAL_STATUS_T

mmal_component_disable = _lib.mmal_component_disable
mmal_component_disable.argtypes = [ct.POINTER(MMAL_COMPONENT_T)]
mmal_component_disable.restype = MMAL_STATUS_T

# mmal_metadata.h ############################################################

# XXX This does not appear to be in libmmal.so...

#MMAL_METADATA_HELLO_WORLD = MMAL_FOURCC('HELO')
#
#class MMAL_METADATA_T(ct.Structure):
#    _fields_ = [
#        ('id',   ct.c_uint32),
#        ('size', ct.c_uint32),
#        ]
#
#class MMAL_METADATA_HELLO_WORLD_T(ct.Structure):
#    _fields_ = [
#        ('id',      ct.c_uint32),
#        ('size',    ct.c_uint32),
#        ('myvalue', ct.c_uint32),
#        ]
#
#mmal_metadata_get = _lib.mmal_metadata_get
#mmal_metadata_get.argtypes = [ct.POINTER(MMAL_BUFFER_HEADER_T), ct.c_uint32]
#mmal_metadata_get.restype = ct.POINTER(MMAL_METADATA_T)
#
#mmal_metadata_set = _lib.mmal_metadata_set
#mmal_metadata_set.argtypes = [ct.POINTER(MMAL_BUFFER_HEADER_T), ct.POINTER(MMAL_METADATA_T)]
#mmal_metadata_set.restype = MMAL_STATUS_T

# mmal_queue.h ###############################################################

class MMAL_QUEUE_T(ct.Structure):
    _fields_ = []

mmal_queue_create = _lib.mmal_queue_create
mmal_queue_create.argtypes = [ct.POINTER(MMAL_QUEUE_T), ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_queue_create.restype = ct.POINTER(MMAL_QUEUE_T)

mmal_queue_put = _lib.mmal_queue_put
mmal_queue_put.argtypes = [ct.POINTER(MMAL_QUEUE_T), ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_queue_put.restype = None

mmal_queue_put_back = _lib.mmal_queue_put_back
mmal_queue_put_back.argtypes = [ct.POINTER(MMAL_QUEUE_T), ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_queue_put_back.restype = None

mmal_queue_get = _lib.mmal_queue_get
mmal_queue_get.argtypes = [ct.POINTER(MMAL_QUEUE_T)]
mmal_queue_get.restype = ct.POINTER(MMAL_BUFFER_HEADER_T)

mmal_queue_wait = _lib.mmal_queue_wait
mmal_queue_wait.argtypes = [ct.POINTER(MMAL_QUEUE_T)]
mmal_queue_wait.restype = ct.POINTER(MMAL_BUFFER_HEADER_T)

mmal_queue_length = _lib.mmal_queue_length
mmal_queue_length.argtypes = [ct.POINTER(MMAL_QUEUE_T)]
mmal_queue_length.restype = ct.c_uint

mmal_queue_destroy = _lib.mmal_queue_destroy
mmal_queue_destroy.argtypes = [ct.POINTER(MMAL_QUEUE_T)]
mmal_queue_destroy.restype = None

# mmal_pool.h ################################################################

class MMAL_POOL_T(ct.Structure):
    _fields_ = [
        ('queue',       ct.POINTER(MMAL_QUEUE_T)),
        ('headers_num', ct.c_uint32),
        ('header',      ct.POINTER(ct.POINTER(MMAL_BUFFER_HEADER_T))),
        ]

mmal_pool_allocator_alloc_t = ct.CFUNCTYPE(
    None,
    ct.c_void_p, ct.c_uint32)
mmal_pool_allocator_free_t = ct.CFUNCTYPE(
    None,
    ct.c_void_p, ct.c_void_p)

mmal_pool_create = _lib.mmal_pool_create
mmal_pool_create.argtypes = [ct.c_uint, ct.c_uint32]
mmal_pool_create.restype = ct.POINTER(MMAL_POOL_T)

mmal_pool_create_with_allocator = _lib.mmal_pool_create_with_allocator
mmal_pool_create_with_allocator.argtypes = [
        ct.c_uint,
        ct.c_uint32,
        ct.c_void_p,
        mmal_pool_allocator_alloc_t,
        mmal_pool_allocator_free_t,
        ]
mmal_pool_create_with_allocator.restype = ct.POINTER(MMAL_POOL_T)

mmal_pool_destroy = _lib.mmal_pool_destroy
mmal_pool_destroy.argtypes = [ct.POINTER(MMAL_POOL_T)]
mmal_pool_destroy.restype = None

mmal_pool_resize = _lib.mmal_pool_resize
mmal_pool_resize.argtypes = [ct.POINTER(MMAL_POOL_T), ct.c_uint, ct.c_uint32]
mmal_pool_resize.restype = MMAL_STATUS_T

MMAL_POOL_BH_CB_T = ct.CFUNCTYPE(
    MMAL_BOOL_T,
    ct.POINTER(MMAL_POOL_T), ct.POINTER(MMAL_BUFFER_HEADER_T), ct.c_void_p)

mmal_pool_callback_set = _lib.mmal_pool_callback_set
mmal_pool_callback_set.argtypes = [ct.POINTER(MMAL_POOL_T), MMAL_POOL_BH_CB_T]
mmal_pool_callback_set.restype = None

mmal_pool_pre_release_callback_set = _lib.mmal_pool_pre_release_callback_set
mmal_pool_pre_release_callback_set.argtypes = [ct.POINTER(MMAL_POOL_T), MMAL_BH_PRE_RELEASE_CB_T, ct.c_void_p]
mmal_pool_pre_release_callback_set.restype = None

# mmal_events.h ##############################################################

MMAL_EVENT_ERROR              = MMAL_FOURCC('ERRO')
MMAL_EVENT_EOS                = MMAL_FOURCC('EEOS')
MMAL_EVENT_FORMAT_CHANGED     = MMAL_FOURCC('EFCH')
MMAL_EVENT_PARAMETER_CHANGED  = MMAL_FOURCC('EPCH')

class MMAL_EVENT_END_OF_STREAM_T(ct.Structure):
    _fields_ = [
        ('port_type',  MMAL_PORT_TYPE_T),
        ('port_index', ct.c_uint32),
        ]

class MMAL_EVENT_FORMAT_CHANGED_T(ct.Structure):
    _fields_ = [
        ('buffer_size_min',         ct.c_uint32),
        ('buffer_num_min',          ct.c_uint32),
        ('buffer_size_recommended', ct.c_uint32),
        ('buffer_num_recommended',  ct.c_uint32),
        ('format',                  ct.POINTER(MMAL_ES_FORMAT_T)),
        ]

class MMAL_EVENT_PARAMETER_CHANGED_T(ct.Structure):
    _fields_ = [
        ('hdr', MMAL_PARAMETER_HEADER_T),
        ]

mmal_event_format_changed_get = _lib.mmal_event_format_changed_get
mmal_event_format_changed_get.argtypes = [ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_event_format_changed_get.restype = ct.POINTER(MMAL_EVENT_FORMAT_CHANGED_T)

mmal_event_error_send = _lib.mmal_event_error_send
mmal_event_error_send.argtypes = [ct.POINTER(MMAL_COMPONENT_T), MMAL_STATUS_T]
mmal_event_error_send.restype = MMAL_STATUS_T

# mmal_encodings.h ###########################################################

MMAL_ENCODING_H264            = MMAL_FOURCC('H264')
MMAL_ENCODING_H263            = MMAL_FOURCC('H263')
MMAL_ENCODING_MP4V            = MMAL_FOURCC('MP4V')
MMAL_ENCODING_MP2V            = MMAL_FOURCC('MP2V')
MMAL_ENCODING_MP1V            = MMAL_FOURCC('MP1V')
MMAL_ENCODING_WMV3            = MMAL_FOURCC('WMV3')
MMAL_ENCODING_WMV2            = MMAL_FOURCC('WMV2')
MMAL_ENCODING_WMV1            = MMAL_FOURCC('WMV1')
MMAL_ENCODING_WVC1            = MMAL_FOURCC('WVC1')
MMAL_ENCODING_VP8             = MMAL_FOURCC('VP8 ')
MMAL_ENCODING_VP7             = MMAL_FOURCC('VP7 ')
MMAL_ENCODING_VP6             = MMAL_FOURCC('VP6 ')
MMAL_ENCODING_THEORA          = MMAL_FOURCC('THEO')
MMAL_ENCODING_SPARK           = MMAL_FOURCC('SPRK')
MMAL_ENCODING_MJPEG           = MMAL_FOURCC('MJPG')

MMAL_ENCODING_JPEG            = MMAL_FOURCC('JPEG')
MMAL_ENCODING_GIF             = MMAL_FOURCC('GIF ')
MMAL_ENCODING_PNG             = MMAL_FOURCC('PNG ')
MMAL_ENCODING_PPM             = MMAL_FOURCC('PPM ')
MMAL_ENCODING_TGA             = MMAL_FOURCC('TGA ')
MMAL_ENCODING_BMP             = MMAL_FOURCC('BMP ')

MMAL_ENCODING_I420            = MMAL_FOURCC('I420')
MMAL_ENCODING_I420_SLICE      = MMAL_FOURCC('S420')
MMAL_ENCODING_YV12            = MMAL_FOURCC('YV12')
MMAL_ENCODING_I422            = MMAL_FOURCC('I422')
MMAL_ENCODING_I422_SLICE      = MMAL_FOURCC('S422')
MMAL_ENCODING_YUYV            = MMAL_FOURCC('YUYV')
MMAL_ENCODING_YVYU            = MMAL_FOURCC('YVYU')
MMAL_ENCODING_UYVY            = MMAL_FOURCC('UYVY')
MMAL_ENCODING_VYUY            = MMAL_FOURCC('VYUY')
MMAL_ENCODING_NV12            = MMAL_FOURCC('NV12')
MMAL_ENCODING_NV21            = MMAL_FOURCC('NV21')
MMAL_ENCODING_ARGB            = MMAL_FOURCC('ARGB')
MMAL_ENCODING_RGBA            = MMAL_FOURCC('RGBA')
MMAL_ENCODING_ABGR            = MMAL_FOURCC('ABGR')
MMAL_ENCODING_BGRA            = MMAL_FOURCC('BGRA')
MMAL_ENCODING_RGB16           = MMAL_FOURCC('RGB2')
MMAL_ENCODING_RGB24           = MMAL_FOURCC('RGB3')
MMAL_ENCODING_RGB32           = MMAL_FOURCC('RGB4')
MMAL_ENCODING_BGR16           = MMAL_FOURCC('BGR2')
MMAL_ENCODING_BGR24           = MMAL_FOURCC('BGR3')
MMAL_ENCODING_BGR32           = MMAL_FOURCC('BGR4')

MMAL_ENCODING_YUVUV128        = MMAL_FOURCC('SAND')
MMAL_ENCODING_OPAQUE          = MMAL_FOURCC('OPQV')

MMAL_ENCODING_EGL_IMAGE       = MMAL_FOURCC('EGLI')
MMAL_ENCODING_PCM_UNSIGNED_BE = MMAL_FOURCC('PCMU')
MMAL_ENCODING_PCM_UNSIGNED_LE = MMAL_FOURCC('pcmu')
MMAL_ENCODING_PCM_SIGNED_BE   = MMAL_FOURCC('PCMS')
MMAL_ENCODING_PCM_SIGNED_LE   = MMAL_FOURCC('pcms')
MMAL_ENCODING_PCM_FLOAT_BE    = MMAL_FOURCC('PCMF')
MMAL_ENCODING_PCM_FLOAT_LE    = MMAL_FOURCC('pcmf')
MMAL_ENCODING_PCM_UNSIGNED    = MMAL_ENCODING_PCM_UNSIGNED_LE
MMAL_ENCODING_PCM_SIGNED      = MMAL_ENCODING_PCM_SIGNED_LE
MMAL_ENCODING_PCM_FLOAT       = MMAL_ENCODING_PCM_FLOAT_LE

MMAL_ENCODING_MP4A            = MMAL_FOURCC('MP4A')
MMAL_ENCODING_MPGA            = MMAL_FOURCC('MPGA')
MMAL_ENCODING_ALAW            = MMAL_FOURCC('ALAW')
MMAL_ENCODING_MULAW           = MMAL_FOURCC('ULAW')
MMAL_ENCODING_ADPCM_MS        = MMAL_FOURCC('MS\x00\x02')
MMAL_ENCODING_ADPCM_IMA_MS    = MMAL_FOURCC('MS\x00\x01')
MMAL_ENCODING_ADPCM_SWF       = MMAL_FOURCC('ASWF')
MMAL_ENCODING_WMA1            = MMAL_FOURCC('WMA1')
MMAL_ENCODING_WMA2            = MMAL_FOURCC('WMA2')
MMAL_ENCODING_WMAP            = MMAL_FOURCC('WMAP')
MMAL_ENCODING_WMAL            = MMAL_FOURCC('WMAL')
MMAL_ENCODING_AMRNB           = MMAL_FOURCC('AMRN')
MMAL_ENCODING_AMRWB           = MMAL_FOURCC('AMRW')
MMAL_ENCODING_AMRWBP          = MMAL_FOURCC('AMRP')
MMAL_ENCODING_AC3             = MMAL_FOURCC('AC3 ')
MMAL_ENCODING_EAC3            = MMAL_FOURCC('EAC3')
MMAL_ENCODING_DTS             = MMAL_FOURCC('DTS ')
MMAL_ENCODING_MLP             = MMAL_FOURCC('MLP ')
MMAL_ENCODING_FLAC            = MMAL_FOURCC('FLAC')
MMAL_ENCODING_VORBIS          = MMAL_FOURCC('VORB')
MMAL_ENCODING_SPEEX           = MMAL_FOURCC('SPX ')
MMAL_ENCODING_ATRAC3          = MMAL_FOURCC('ATR3')
MMAL_ENCODING_ATRACX          = MMAL_FOURCC('ATRX')
MMAL_ENCODING_ATRACL          = MMAL_FOURCC('ATRL')
MMAL_ENCODING_MIDI            = MMAL_FOURCC('MIDI')
MMAL_ENCODING_EVRC            = MMAL_FOURCC('EVRC')
MMAL_ENCODING_NELLYMOSER      = MMAL_FOURCC('NELY')
MMAL_ENCODING_QCELP           = MMAL_FOURCC('QCEL')
MMAL_ENCODING_MP4V_DIVX_DRM   = MMAL_FOURCC('M4VD')

MMAL_ENCODING_VARIANT_H264_DEFAULT = 0
MMAL_ENCODING_VARIANT_H264_AVC1    = MMAL_FOURCC('AVC1')
MMAL_ENCODING_VARIANT_H264_RAW     = MMAL_FOURCC('RAW ')
MMAL_ENCODING_VARIANT_MP4A_DEFAULT = 0
MMAL_ENCODING_VARIANT_MP4A_ADTS    = MMAL_FOURCC('ADTS')

MMAL_COLOR_SPACE_UNKNOWN      = 0
MMAL_COLOR_SPACE_ITUR_BT601   = MMAL_FOURCC('Y601')
MMAL_COLOR_SPACE_ITUR_BT709   = MMAL_FOURCC('Y709')
MMAL_COLOR_SPACE_JPEG_JFIF    = MMAL_FOURCC('YJFI')
MMAL_COLOR_SPACE_FCC          = MMAL_FOURCC('YFCC')
MMAL_COLOR_SPACE_SMPTE240M    = MMAL_FOURCC('Y240')
MMAL_COLOR_SPACE_BT470_2_M    = MMAL_FOURCC('Y__M')
MMAL_COLOR_SPACE_BT470_2_BG   = MMAL_FOURCC('Y_BG')
MMAL_COLOR_SPACE_JFIF_Y16_255 = MMAL_FOURCC('YY16')

# util/mmal_default_components.h #############################################

MMAL_COMPONENT_DEFAULT_VIDEO_DECODER   = b"vc.ril.video_decode"
MMAL_COMPONENT_DEFAULT_VIDEO_ENCODER   = b"vc.ril.video_encode"
MMAL_COMPONENT_DEFAULT_VIDEO_RENDERER  = b"vc.ril.video_render"
MMAL_COMPONENT_DEFAULT_IMAGE_DECODER   = b"vc.ril.image_decode"
MMAL_COMPONENT_DEFAULT_IMAGE_ENCODER   = b"vc.ril.image_encode"
MMAL_COMPONENT_DEFAULT_CAMERA          = b"vc.ril.camera"
MMAL_COMPONENT_DEFAULT_VIDEO_CONVERTER = b"vc.video_convert"
MMAL_COMPONENT_DEFAULT_SPLITTER        = b"vc.splitter"
MMAL_COMPONENT_DEFAULT_SCHEDULER       = b"vc.scheduler"
MMAL_COMPONENT_DEFAULT_VIDEO_INJECTER  = b"vc.video_inject"
MMAL_COMPONENT_DEFAULT_VIDEO_SPLITTER  = b"vc.ril.video_splitter"
MMAL_COMPONENT_DEFAULT_AUDIO_DECODER   = b"none"
MMAL_COMPONENT_DEFAULT_AUDIO_RENDERER  = b"vc.ril.audio_render"
MMAL_COMPONENT_DEFAULT_MIRACAST        = b"vc.miracast"
# The following two components aren't in the MMAL headers, but do exist
MMAL_COMPONENT_DEFAULT_NULL_SINK       = b"vc.null_sink"
MMAL_COMPONENT_DEFAULT_RESIZER         = b"vc.ril.resize"

# util/mmal_util_params.h ####################################################

mmal_port_parameter_set_boolean = _lib.mmal_port_parameter_set_boolean
mmal_port_parameter_set_boolean.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, MMAL_BOOL_T]
mmal_port_parameter_set_boolean.restype = MMAL_STATUS_T

mmal_port_parameter_get_boolean = _lib.mmal_port_parameter_get_boolean
mmal_port_parameter_get_boolean.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.POINTER(MMAL_BOOL_T)]
mmal_port_parameter_get_boolean.restype = MMAL_STATUS_T

mmal_port_parameter_set_uint64 = _lib.mmal_port_parameter_set_uint64
mmal_port_parameter_set_uint64.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.c_uint64]
mmal_port_parameter_set_uint64.restype = MMAL_STATUS_T

mmal_port_parameter_get_uint64 = _lib.mmal_port_parameter_get_uint64
mmal_port_parameter_get_uint64.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.POINTER(ct.c_uint64)]
mmal_port_parameter_get_uint64.restype = MMAL_STATUS_T

mmal_port_parameter_set_int64 = _lib.mmal_port_parameter_set_int64
mmal_port_parameter_set_int64.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.c_int64]
mmal_port_parameter_set_int64.restype = MMAL_STATUS_T

mmal_port_parameter_get_int64 = _lib.mmal_port_parameter_get_int64
mmal_port_parameter_get_int64.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.POINTER(ct.c_int64)]
mmal_port_parameter_get_int64.restype = MMAL_STATUS_T

mmal_port_parameter_set_uint32 = _lib.mmal_port_parameter_set_uint32
mmal_port_parameter_set_uint32.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.c_uint32]
mmal_port_parameter_set_uint32.restype = MMAL_STATUS_T

mmal_port_parameter_get_uint32 = _lib.mmal_port_parameter_get_uint32
mmal_port_parameter_get_uint32.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.POINTER(ct.c_uint32)]
mmal_port_parameter_get_uint32.restype = MMAL_STATUS_T

mmal_port_parameter_set_int32 = _lib.mmal_port_parameter_set_int32
mmal_port_parameter_set_int32.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.c_int32]
mmal_port_parameter_set_int32.restype = MMAL_STATUS_T

mmal_port_parameter_get_int32 = _lib.mmal_port_parameter_get_int32
mmal_port_parameter_get_int32.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.POINTER(ct.c_int32)]
mmal_port_parameter_get_int32.restype = MMAL_STATUS_T

mmal_port_parameter_set_rational = _lib.mmal_port_parameter_set_rational
mmal_port_parameter_set_rational.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, MMAL_RATIONAL_T]
mmal_port_parameter_set_rational.restype = MMAL_STATUS_T

mmal_port_parameter_get_rational = _lib.mmal_port_parameter_get_rational
mmal_port_parameter_get_rational.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.POINTER(MMAL_RATIONAL_T)]
mmal_port_parameter_get_rational.restype = MMAL_STATUS_T

mmal_port_parameter_set_string = _lib.mmal_port_parameter_set_string
mmal_port_parameter_set_string.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.c_char_p]
mmal_port_parameter_set_string.restype = MMAL_STATUS_T

mmal_port_parameter_set_bytes = _lib.mmal_port_parameter_set_bytes
mmal_port_parameter_set_bytes.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.POINTER(ct.c_uint8), ct.c_uint]
mmal_port_parameter_set_bytes.restype = MMAL_STATUS_T

mmal_util_port_set_uri = _lib.mmal_util_port_set_uri
mmal_util_port_set_uri.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_char_p]
mmal_util_port_set_uri.restype = MMAL_STATUS_T

mmal_util_set_display_region = _lib.mmal_util_set_display_region
mmal_util_set_display_region.argtypes = [ct.POINTER(MMAL_PORT_T), ct.POINTER(MMAL_DISPLAYREGION_T)]
mmal_util_set_display_region.restype = MMAL_STATUS_T

mmal_util_camera_use_stc_timestamp = _lib.mmal_util_camera_use_stc_timestamp
mmal_util_camera_use_stc_timestamp.argtypes = [ct.POINTER(MMAL_PORT_T), MMAL_CAMERA_STC_MODE_T]
mmal_util_camera_use_stc_timestamp.restype = MMAL_STATUS_T

mmal_util_get_core_port_stats = _lib.mmal_util_get_core_port_stats
mmal_util_get_core_port_stats.argtypes = [ct.POINTER(MMAL_PORT_T), MMAL_CORE_STATS_DIR, MMAL_BOOL_T, ct.POINTER(MMAL_CORE_STATISTICS_T)]
mmal_util_get_core_port_stats.restype = MMAL_STATUS_T

# util/mmal_connection.h #####################################################

MMAL_CONNECTION_FLAG_TUNNELLING = 0x1
MMAL_CONNECTION_FLAG_ALLOCATION_ON_INPUT = 0x2
MMAL_CONNECTION_FLAG_ALLOCATION_ON_OUTPUT = 0x4

class MMAL_CONNECTION_T(ct.Structure):
    # Forward type declaration
    pass

MMAL_CONNECTION_CALLBACK_T = ct.CFUNCTYPE(
    None,
    ct.POINTER(MMAL_CONNECTION_T))

MMAL_CONNECTION_T._fields_ = [
    ('user_data',    ct.c_void_p),
    ('callback',     MMAL_CONNECTION_CALLBACK_T),
    ('is_enabled',   ct.c_uint32),
    ('flags',        ct.c_uint32),
    # Originally "in", but this is a Python keyword
    ('in_',          ct.POINTER(MMAL_PORT_T)),
    ('out',          ct.POINTER(MMAL_PORT_T)),
    ('pool',         ct.POINTER(MMAL_POOL_T)),
    ('queue',        ct.POINTER(MMAL_QUEUE_T)),
    ('name',         ct.c_char_p),
    ('time_setup',   ct.c_int64),
    ('time_enable',  ct.c_int64),
    ('time_disable', ct.c_int64),
    ]

mmal_connection_create = _lib.mmal_connection_create
mmal_connection_create.argtypes = [ct.POINTER(ct.POINTER(MMAL_CONNECTION_T)), ct.POINTER(MMAL_PORT_T), ct.POINTER(MMAL_PORT_T), ct.c_uint32]
mmal_connection_create.restype = MMAL_STATUS_T

mmal_connection_acquire = _lib.mmal_connection_acquire
mmal_connection_acquire.argtypes = [ct.POINTER(MMAL_CONNECTION_T)]
mmal_connection_acquire.restype = None

mmal_connection_release = _lib.mmal_connection_release
mmal_connection_release.argtypes = [ct.POINTER(MMAL_CONNECTION_T)]
mmal_connection_release.restype = MMAL_STATUS_T

mmal_connection_destroy = _lib.mmal_connection_destroy
mmal_connection_destroy.argtypes = [ct.POINTER(MMAL_CONNECTION_T)]
mmal_connection_destroy.restype = MMAL_STATUS_T

mmal_connection_enable = _lib.mmal_connection_enable
mmal_connection_enable.argtypes = [ct.POINTER(MMAL_CONNECTION_T)]
mmal_connection_enable.restype = MMAL_STATUS_T

mmal_connection_disable = _lib.mmal_connection_disable
mmal_connection_disable.argtypes = [ct.POINTER(MMAL_CONNECTION_T)]
mmal_connection_disable.restype = MMAL_STATUS_T

mmal_connection_event_format_changed = _lib.mmal_connection_event_format_changed
mmal_connection_event_format_changed.argtypes = [ct.POINTER(MMAL_CONNECTION_T), ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_connection_event_format_changed.restype = MMAL_STATUS_T

# util/mmal_util.h ###########################################################

mmal_status_to_string = _lib.mmal_status_to_string
mmal_status_to_string.argtypes = [MMAL_STATUS_T]
mmal_status_to_string.restype = ct.c_char_p

mmal_encoding_stride_to_width = _lib.mmal_encoding_stride_to_width
mmal_encoding_stride_to_width.argtypes = [ct.c_uint32, ct.c_uint32]
mmal_encoding_stride_to_width.restype = ct.c_uint32

mmal_encoding_width_to_stride = _lib.mmal_encoding_width_to_stride
mmal_encoding_width_to_stride.argtypes = [ct.c_uint32, ct.c_uint32]
mmal_encoding_width_to_stride.restype = ct.c_uint32

mmal_port_type_to_string = _lib.mmal_port_type_to_string
mmal_port_type_to_string.argtypes = [MMAL_PORT_TYPE_T]
mmal_port_type_to_string.restype = ct.c_char_p

mmal_port_parameter_alloc_get = _lib.mmal_port_parameter_alloc_get
mmal_port_parameter_alloc_get.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint32, ct.c_uint32, ct.POINTER(MMAL_STATUS_T)]
mmal_port_parameter_alloc_get.restype = ct.POINTER(MMAL_PARAMETER_HEADER_T)

mmal_port_parameter_free = _lib.mmal_port_parameter_free
mmal_port_parameter_free.argtypes = [ct.POINTER(MMAL_PARAMETER_HEADER_T)]
mmal_port_parameter_free.restype = None

mmal_buffer_header_copy_header = _lib.mmal_buffer_header_copy_header
mmal_buffer_header_copy_header.argtypes = [ct.POINTER(MMAL_BUFFER_HEADER_T), ct.POINTER(MMAL_BUFFER_HEADER_T)]
mmal_buffer_header_copy_header.restype = None

mmal_port_pool_create = _lib.mmal_port_pool_create
mmal_port_pool_create.argtypes = [ct.POINTER(MMAL_PORT_T), ct.c_uint, ct.c_uint32]
mmal_port_pool_create.restype = ct.POINTER(MMAL_POOL_T)

mmal_port_pool_destroy = _lib.mmal_port_pool_destroy
mmal_port_pool_destroy.argtypes = [ct.POINTER(MMAL_PORT_T), ct.POINTER(MMAL_POOL_T)]
mmal_port_pool_destroy.restype = None

mmal_log_dump_port = _lib.mmal_log_dump_port
mmal_log_dump_port.argtypes = [ct.POINTER(MMAL_PORT_T)]
mmal_log_dump_port.restype = None

mmal_log_dump_format = _lib.mmal_log_dump_format
mmal_log_dump_format.argtypes = [ct.POINTER(MMAL_ES_FORMAT_T)]
mmal_log_dump_format.restype = None

mmal_util_get_port = _lib.mmal_util_get_port
mmal_util_get_port.argtypes = [ct.POINTER(MMAL_COMPONENT_T), MMAL_PORT_TYPE_T, ct.c_uint]
mmal_util_get_port.restype = ct.POINTER(MMAL_PORT_T)

mmal_4cc_to_string = _lib.mmal_4cc_to_string
mmal_4cc_to_string.argtypes = [ct.c_char_p, ct.c_size_t, ct.c_uint32]
mmal_4cc_to_string.restype = ct.c_char_p


########NEW FILE########
__FILENAME__ = streams
# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013,2014 Dave Hughes <dave@waveform.org.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str equivalent to Py3's
str = type('')


import io
from threading import RLock
from collections import deque

from picamera.exc import PiCameraValueError
from picamera.encoders import PiVideoFrame


__all__ = [
    'CircularIO',
    'PiCameraCircularIO',
    ]


class CircularIO(io.IOBase):
    """
    A thread-safe stream which uses a ring buffer for storage.

    CircularIO provides an in-memory stream similar to the :class:`io.BytesIO`
    class. However, unlike BytesIO its underlying storage is a `ring buffer`_
    with a fixed maximum size. Once the maximum size is reached, writing
    effectively loops round to the beginning to the ring and starts overwriting
    the oldest content.

    The *size* parameter specifies the maximum size of the stream in bytes. The
    :meth:`read`, :meth:`tell`, and :meth:`seek` methods all operate
    equivalently to those in :class:`io.BytesIO` whilst :meth:`write` only
    differs in the wrapping behaviour described above. A :meth:`read1` method
    is also provided for efficient reading of the underlying ring buffer in
    write-sized chunks (or less).

    A re-entrant threading lock guards all operations, and is accessible for
    external use via the :attr:`lock` attribute.

    The performance of the class is geared toward faster writing than reading
    on the assumption that writing will be the common operation and reading the
    rare operation (a reasonable assumption for the camera use-case, but not
    necessarily for more general usage).

    .. _ring buffer: http://en.wikipedia.org/wiki/Circular_buffer
    """
    def __init__(self, size):
        if size < 1:
            raise ValueError('size must be a positive integer')
        self._lock = RLock()
        self._data = deque()
        self._size = size
        self._length = 0
        self._pos = 0
        self._pos_index = 0
        self._pos_offset = 0

    @property
    def lock(self):
        """
        A re-entrant threading lock which is used to guard all operations.
        """
        return self._lock

    @property
    def size(self):
        """
        Return the maximum size of the buffer in bytes.
        """
        return self._size

    def readable(self):
        """
        Returns ``True``, indicating that the stream supports :meth:`read`.
        """
        return True

    def writable(self):
        """
        Returns ``True``, indicating that the stream supports :meth:`write`.
        """
        return True

    def seekable(self):
        """
        Returns ``True``, indicating the stream supports :meth:`seek` and
        :meth:`tell`.
        """
        return True

    def getvalue(self):
        """
        Return ``bytes`` containing the entire contents of the buffer.
        """
        with self.lock:
            return b''.join(self._data)

    def _set_pos(self, value):
        self._pos = value
        self._pos_index = -1
        self._pos_offset = chunk_pos = 0
        for self._pos_index, chunk in enumerate(self._data):
            if chunk_pos + len(chunk) > value:
                self._pos_offset = value - chunk_pos
                return
            else:
                chunk_pos += len(chunk)
        self._pos_index += 1
        self._pos_offset = value - chunk_pos

    def tell(self):
        """
        Return the current stream position.
        """
        return self._pos

    def seek(self, offset, whence=io.SEEK_SET):
        """
        Change the stream position to the given byte *offset*. *offset* is
        interpreted relative to the position indicated by *whence*. Values for
        *whence* are:

        * ``SEEK_SET`` or ``0`` – start of the stream (the default); *offset*
          should be zero or positive

        * ``SEEK_CUR`` or ``1`` – current stream position; *offset* may be
          negative

        * ``SEEK_END`` or ``2`` – end of the stream; *offset* is usually
          negative

        Return the new absolute position.
        """
        with self.lock:
            if whence == io.SEEK_CUR:
                offset = self._pos + offset
            elif whence == io.SEEK_END:
                offset = self._length + offset
            if offset < 0:
                raise ValueError(
                    'New position is before the start of the stream')
            self._set_pos(offset)
            return self._pos

    def read(self, n=-1):
        """
        Read up to *n* bytes from the stream and return them. As a convenience,
        if *n* is unspecified or -1, :meth:`readall` is called. Fewer than *n*
        bytes may be returned if there are fewer than *n* bytes from the
        current stream position to the end of the stream.

        If 0 bytes are returned, and *n* was not 0, this indicates end of the
        stream.
        """
        with self.lock:
            if self._pos == self._length:
                return b''
            if n == -1:
                n = self._length - self._pos
            from_index, from_offset = self._pos_index, self._pos_offset
            self._set_pos(self._pos + n)
            result = self._data[from_index][from_offset:from_offset + n]
            # Bah ... can't slice a deque
            for i in range(from_index + 1, self._pos_index):
                result += self._data[i]
            if from_index < self._pos_index < len(self._data):
                result += self._data[self._pos_index][:self._pos_offset]
            return result

    def read1(self, n=-1):
        """
        Read up to *n* bytes from the stream using only a single call to the
        underlying object.

        In the case of :class:`CircularIO` this roughly corresponds to
        returning the content from the current position up to the end of the
        write that added that content to the stream (assuming no subsequent
        writes overwrote the content). :meth:`read1` is particularly useful
        for efficient copying of the stream's content.
        """
        with self.lock:
            if self._pos == self._length:
                return b''
            chunk = self._data[self._pos_index]
            if n == -1:
                n = len(chunk) - self._pos_offset
            result = chunk[self._pos_offset:self._pos_offset + n]
            self._pos += len(result)
            self._pos_offset += n
            if self._pos_offset >= len(chunk):
                self._pos_index += 1
                self._pos_offset = 0
            return result

    def truncate(self, size=None):
        """
        Resize the stream to the given *size* in bytes (or the current position
        if *size* is not specified). This resizing can extend or reduce the
        current stream size. In case of extension, the contents of the new file
        area will be NUL (``\\x00``) bytes. The new stream size is returned.

        The current stream position isn’t changed unless the resizing is
        expanding the stream, in which case it may be set to the maximum stream
        size if the expansion causes the ring buffer to loop around.
        """
        with self.lock:
            if size is None:
                size = self._pos
            if size < 0:
                raise ValueError('size must be zero, or a positive integer')
            if size > self._length:
                # Backfill the space between stream end and current position
                # with NUL bytes
                fill = b'\x00' * (size - self._length)
                self._set_pos(self._length)
                self.write(fill)
            elif size < self._length:
                # Lop off chunks until we get to the last one at the truncation
                # point, and slice that one
                save_pos = self._pos
                self._set_pos(size)
                while self._pos_index < len(self._data) - 1:
                    self._data.pop()
                self._data[self._pos_index] = self._data[self._pos_index][:self._pos_offset]
                self._length = size
                self._pos_index += 1
                self._pos_offset = 0
                if self._pos != save_pos:
                    self._set_pos(save_pos)

    def write(self, b):
        """
        Write the given bytes or bytearray object, *b*, to the underlying
        stream and return the number of bytes written.
        """
        b = bytes(b)
        with self.lock:
            # Special case: stream position is beyond the end of the stream.
            # Call truncate to backfill space first
            if self._pos > self._length:
                self.truncate()
            result = len(b)
            if self._pos == self._length:
                # Fast path: stream position is at the end of the stream so
                # just append a new chunk
                self._data.append(b)
                self._length += len(b)
                self._pos = self._length
                self._pos_index = len(self._data)
                self._pos_offset = 0
            else:
                # Slow path: stream position is somewhere in the middle;
                # overwrite bytes in the current (and if necessary, subsequent)
                # chunk(s), without extending them. If we reach the end of the
                # stream, call ourselves recursively to continue down the fast
                # path
                while b and (self._pos < self._length):
                    chunk = self._data[self._pos_index]
                    head = b[:len(chunk) - self._pos_offset]
                    assert head
                    b = b[len(head):]
                    self._data[self._pos_index] = b''.join((
                            chunk[:self._pos_offset],
                            head,
                            chunk[self._pos_offset + len(head):]
                            ))
                    self._pos += len(head)
                    if self._pos_offset + len(head) >= len(chunk):
                        self._pos_index += 1
                        self._pos_offset = 0
                    else:
                        self._pos_offset += len(head)
                if b:
                    self.write(b)
            # If the stream is now beyond the specified size limit, remove
            # chunks (or part of a chunk) until the size is within the limit
            # again
            while self._length > self._size:
                chunk = self._data[0]
                if self._length - len(chunk) >= self._size:
                    # Need to remove the entire chunk
                    self._data.popleft()
                    self._length -= len(chunk)
                    self._pos -= len(chunk)
                    self._pos_index -= 1
                    # no need to adjust self._pos_offset
                else:
                    # need to remove the head of the chunk
                    self._data[0] = chunk[self._length - self._size:]
                    self._pos -= self._length - self._size
                    self._length = self._size
            return result


class PiCameraDequeHack(deque):
    def __init__(self, camera):
        super(PiCameraDequeHack, self).__init__()
        self.camera = camera
        self._last_frame = None

    def append(self, item):
        if self._last_frame:
            assert self._last_frame <= self.camera.frame.index
            if self._last_frame == self.camera.frame.index:
                return super(PiCameraDequeHack, self).append((item, None))
        # If the chunk being appended is the end of a new frame, include
        # the frame's metadata from the camera
        self._last_frame = self.camera.frame.index
        return super(PiCameraDequeHack, self).append((item, self.camera.frame))

    def pop(self):
        return super(PiCameraDequeHack, self).pop()[0]

    def popleft(self):
        return super(PiCameraDequeHack, self).popleft()[0]

    def __getitem__(self, index):
        return super(PiCameraDequeHack, self).__getitem__(index)[0]

    def __setitem__(self, index, value):
        frame = super(PiCameraDequeHack, self).__getitem__(index)[1]
        return super(PiCameraDequeHack, self).__setitem__(index, (value, frame))

    def __iter__(self):
        for item, frame in super(PiCameraDequeHack, self).__iter__():
            yield item

    @property
    def frames(self):
        pos = 0
        for item, frame in super(PiCameraDequeHack, self).__iter__():
            pos += len(item)
            if frame:
                # Rewrite the video_size and split_size attributes according
                # to the current position of the chunk
                frame = PiVideoFrame(
                    index=frame.index,
                    keyframe=frame.keyframe,
                    frame_size=frame.frame_size,
                    video_size=pos,
                    split_size=pos,
                    timestamp=frame.timestamp,
                    header=frame.header,
                    )
                # Only yield the frame meta-data if the start of the frame
                # still exists in the stream
                if pos - frame.frame_size >= 0:
                    yield frame


class PiCameraCircularIO(CircularIO):
    """
    A derivative of :class:`CircularIO` which tracks camera frames.

    PiCameraCircularIO provides an in-memory stream based on a ring buffer. It
    is a specialization of :class:`CircularIO` which associates video frame
    meta-data with the recorded stream, accessible from the :attr:`frames`
    property.

    .. warning::

        The class makes a couple of assumptions which will cause the frame
        meta-data tracking to break if they are not adhered to:

        * the stream is only ever appended to - no writes ever start from
          the middle of the stream

        * the stream is never truncated (from the right; being ring buffer
          based, left truncation will occur automatically)

    The *camera* parameter specifies the :class:`PiCamera` instance that will
    be recording video to the stream. If specified, the *size* parameter
    determines the maximum size of the stream in bytes. If *size* is not
    specified (or ``None``), then *seconds* must be specified instead. This
    provides the maximum length of the stream in seconds, assuming a data rate
    in bits-per-second given by the *bitrate* parameter (which defaults to
    ``17000000``, or 17Mbps, which is also the default bitrate used for video
    recording by :class:`PiCamera`). You cannot specify both *size* and
    *seconds*.
    """
    def __init__(self, camera, size=None, seconds=None, bitrate=17000000):
        if size is None and seconds is None:
            raise PiCameraValueError('You must specify either size, or seconds')
        if size is not None and seconds is not None:
            raise PiCameraValueError('You cannot specify both size and seconds')
        if seconds is not None:
            size = bitrate * seconds // 8
        super(PiCameraCircularIO, self).__init__(size)
        self.camera = camera
        self._data = PiCameraDequeHack(camera)

    @property
    def frames(self):
        """
        Returns an iterator over the frame meta-data.

        As the camera records video to the stream, the class captures the
        meta-data associated with each frame (in the form of a
        :class:`PiVideoFrame` tuple), discarding meta-data for frames which are
        no longer fully stored within the underlying ring buffer.  You can use
        the frame meta-data to locate, for example, the first keyframe present
        in the stream in order to determine an appropriate range to extract.
        """
        with self.lock:
            for frame in self._data.frames:
                yield frame


########NEW FILE########
__FILENAME__ = conftest
# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013,2014 Dave Hughes <dave@waveform.org.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str equivalent to Py3's
str = type('')

import picamera
import pytest


# The basic camera fixture returns a camera which is not running a preview.
# This should be used for tests which cannot be run when a preview is active
@pytest.fixture(scope='module')
def camera(request):
    camera = picamera.PiCamera()
    def fin():
        camera.close()
    request.addfinalizer(fin)
    return camera

# Activates and deactivates preview mode to test things in both states
@pytest.fixture(params=(False, True))
def previewing(request, camera):
    if request.param and not camera.previewing:
        camera.start_preview()
    if not request.param and camera.previewing:
        camera.stop_preview()
    return request.param

# Run tests at a variety of resolutions (and aspect ratios, 1:1, 4:3, 16:9) and
# framerates (which dictate the input mode of the camera)
@pytest.fixture(params=(
    ((100, 100), 60),
    ((320, 240), 5),
    ((1280, 720), 30),
    ((1920, 1080), 24),
    ((2592, 1944), 15),
    ))
def mode(request, camera):
    save_resolution = camera.resolution
    save_framerate = camera.framerate
    new_resolution, new_framerate = request.param
    camera.resolution = new_resolution
    camera.framerate = new_framerate
    def fin():
        try:
            for port in camera._encoders:
                camera.stop_recording(splitter_port=port)
        finally:
            camera.resolution = save_resolution
            camera.framerate = save_framerate
    request.addfinalizer(fin)
    return request.param



########NEW FILE########
__FILENAME__ = test_attr
# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013,2014 Dave Hughes <dave@waveform.org.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str equivalent to Py3's
str = type('')

import picamera
import pytest
from fractions import Fraction


def numeric_attr(camera, attr, value_min, value_max, step=1):
    save_value = getattr(camera, attr)
    try:
        for value in range(value_min, value_max + 1, step):
            setattr(camera, attr, value)
            assert value == getattr(camera, attr)
        with pytest.raises(picamera.PiCameraError):
            setattr(camera, attr, value_min - 1)
        with pytest.raises(picamera.PiCameraError):
            setattr(camera, attr, value_max + 1)
    finally:
        setattr(camera, attr, save_value)

def keyword_attr(camera, attr, values):
    save_value = getattr(camera, attr)
    try:
        for value in values:
            setattr(camera, attr, value)
            assert value == getattr(camera, attr)
        with pytest.raises(picamera.PiCameraError):
            setattr(camera, attr, 'foobar')
    finally:
        setattr(camera, attr, save_value)

def boolean_attr(camera, attr):
    save_value = getattr(camera, attr)
    try:
        setattr(camera, attr, False)
        assert not getattr(camera, attr)
        setattr(camera, attr, True)
        assert getattr(camera, attr)
    finally:
        setattr(camera, attr, save_value)


def test_awb_mode(camera, previewing):
    keyword_attr(camera, 'awb_mode', camera.AWB_MODES)

def test_awb_gains(camera, previewing):
    save_mode = camera.awb_mode
    try:
        # XXX Workaround: can't use numeric_attr here as awb_mode is write-only
        camera.awb_mode = 'off'
        for i in range (9):
            camera.awb_gains = i
        camera.awb_gains = 1.5
        camera.awb_gains = (1.5, 1.5)
        camera.awb_gains = (Fraction(16, 10), 1.9)
        with pytest.raises(picamera.PiCameraError):
            camera.awb_gains = Fraction(20, 1)
    finally:
        camera.awb_mode = save_mode

def test_brightness(camera, previewing):
    numeric_attr(camera, 'brightness', 0, 100)

def test_color_effects(camera, previewing):
    save_value = camera.color_effects
    try:
        camera.color_effects = None
        assert camera.color_effects is None
        camera.color_effects = (128, 128)
        assert camera.color_effects == (128, 128)
        camera.color_effects = (0, 255)
        assert camera.color_effects == (0, 255)
        camera.color_effects = (255, 0)
        assert camera.color_effects == (255, 0)
        with pytest.raises(picamera.PiCameraError):
            camera.color_effects = (-1, -1)
        with pytest.raises(picamera.PiCameraError):
            camera.color_effects = (0, 300)
    finally:
        camera.color_effects = save_value

def test_contrast(camera, previewing):
    numeric_attr(camera, 'contrast', -100, 100)

def test_exposure_compensation(camera, previewing):
    numeric_attr(camera, 'exposure_compensation', -25, 25)

def test_exposure_mode(camera, previewing):
    # XXX Workaround: setting mode verylong can cause locks so exclude it from
    # tests for now
    keyword_attr(camera, 'exposure_mode', (
        e for e in camera.EXPOSURE_MODES if e != 'verylong'))

def test_image_effect(camera, previewing):
    # XXX Workaround: setting posterize, whiteboard and blackboard doesn't
    # currently work
    keyword_attr(camera, 'image_effect', (
        e for e in camera.IMAGE_EFFECTS
        if e not in ('blackboard', 'whiteboard', 'posterize')))

def test_meter_mode(camera, previewing):
    keyword_attr(camera, 'meter_mode', camera.METER_MODES)

def test_rotation(camera, previewing):
    save_value = camera.rotation
    try:
        for value in range(0, 360):
            camera.rotation = value
            assert camera.rotation == [0, 90, 180, 270][value // 90]
        camera.rotation = 360
        assert camera.rotation == 0
    finally:
        camera.rotation = save_value

def test_saturation(camera, previewing):
    numeric_attr(camera, 'saturation', -100, 100)

def test_sharpness(camera, previewing):
    numeric_attr(camera, 'sharpness', -100, 100)

def test_video_stabilization(camera, previewing):
    boolean_attr(camera, 'video_stabilization')

def test_hflip(camera, previewing):
    boolean_attr(camera, 'hflip')

def test_vflip(camera, previewing):
    boolean_attr(camera, 'vflip')

def test_shutter_speed(camera, previewing):
    # Shutter speed is now clamped by frame-rate; set frame-rate to something
    # nice and low to enable the test to run correctly
    save_framerate = camera.framerate
    camera.framerate = 1
    try:
        # When setting shutter speed manually, ensure the actual shutter speed
        # is within 50usec of the specified amount
        for value in range(0, 200000, 50):
            camera.shutter_speed = value
            assert (value - 50) <= camera.shutter_speed <= value
        # Test the shutter speed clamping by framerate
        camera.framerate = 30
        assert 33000 <= camera.shutter_speed <= 33333
    finally:
        camera.framerate = save_framerate
        camera.shutter_speed = 0

def test_crop(camera, previewing):
    save_crop = camera.crop
    try:
        camera.crop = (0.0, 0.0, 1.0, 1.0)
        assert camera.crop == (0.0, 0.0, 1.0, 1.0)
        camera.crop = (0.2, 0.2, 0.6, 0.6)
        assert camera.crop == (0.2, 0.2, 0.6, 0.6)
        camera.crop = (0.1, 0.1, 0.8, 0.8)
        # 0.1 doesn't quite make the round trip...
        assert camera.crop == (int(0.1*65535.0)/65535.0, int(0.1*65535.0)/65535.0, 0.8, 0.8)
    finally:
        camera.crop = save_crop

# XXX The preview properties work, but don't return correct values unless the
# preview is actually running; if this isn't expected behaviour then we should
# xfail these tests instead of simply testing for previewing...

def test_preview_alpha(camera, previewing):
    if previewing:
        numeric_attr(camera, 'preview_alpha', 0, 255)

def test_preview_layer(camera, previewing):
    if previewing:
        numeric_attr(camera, 'preview_layer', 0, 10)

def test_preview_fullscreen(camera, previewing):
    if previewing:
        boolean_attr(camera, 'preview_fullscreen')

def test_preview_window(camera, previewing):
    if previewing:
        camera.preview_window = (0, 0, 320, 240)
        assert camera.preview_window == (0, 0, 320, 240)
        camera.preview_window = (1280-320, 720-240, 320, 240)
        assert camera.preview_window == (1280-320, 720-240, 320, 240)
        camera.preview_window = (0, 0, 640, 360)
        assert camera.preview_window == (0, 0, 640, 360)
        camera.preview_window = (0, 720-360, 640, 360)
        assert camera.preview_window == (0, 720-360, 640, 360)
        camera.preview_window = (1280-640, 0, 640, 360)
        assert camera.preview_window == (1280-640, 0, 640, 360)
        camera.preview_window = (1280-640, 720-360, 640, 360)
        assert camera.preview_window == (1280-640, 720-360, 640, 360)
        camera.preview_window = (0, 0, 1920, 1080)
        assert camera.preview_window == (0, 0, 1920, 1080)

def test_framerate(camera, previewing):
    save_framerate = camera.framerate
    try:
        assert len(camera.framerate) == 2
        camera.framerate = (30, 1)
        n, d = camera.framerate
        assert n/d == 30
        camera.framerate = (15, 1)
        n, d = camera.framerate
        assert n/d == 15
        camera.framerate = 30
        n, d = camera.framerate
        assert n/d == 30
        camera.framerate = 15.0
        n, d = camera.framerate
        assert n/d == 15
        camera.framerate = Fraction(30, 2)
        n, d = camera.framerate
        assert n/d == 15
        camera.framerate = 60
        n, d = camera.framerate
        assert n/d == 60
        camera.framerate = 90
        n, d = camera.framerate
        assert n/d == 90
        with pytest.raises(picamera.PiCameraError):
            camera.framerate = (30, 0)
        with pytest.raises(picamera.PiCameraError):
            camera.framerate = -1
        with pytest.raises(picamera.PiCameraError):
            camera.framerate = 100
    finally:
        camera.framerate = save_framerate

def test_resolution(camera, previewing):
    save_resolution = camera.resolution
    try:
        # Test setting some regular resolutions
        camera.resolution = (320, 240)
        assert camera.resolution == (320, 240)
        assert camera._camera[0].port[2][0].format[0].es[0].video.width == 320
        assert camera._camera[0].port[2][0].format[0].es[0].video.height == 240
        camera.resolution = (640, 480)
        assert camera.resolution == (640, 480)
        assert camera._camera[0].port[2][0].format[0].es[0].video.width == 640
        assert camera._camera[0].port[2][0].format[0].es[0].video.height == 480
        camera.resolution = (1280, 720)
        assert camera.resolution == (1280, 720)
        assert camera._camera[0].port[2][0].format[0].es[0].video.width == 1280
        assert camera._camera[0].port[2][0].format[0].es[0].video.height == 720
        camera.resolution = (1920, 1080)
        assert camera.resolution == (1920, 1080)
        # Camera's vertical resolution is always a multiple of 16, and
        # horizontal is a multiple of 32, hence the difference in the video
        # formats here and below
        assert camera._camera[0].port[2][0].format[0].es[0].video.width == 1920
        assert camera._camera[0].port[2][0].format[0].es[0].video.height == 1088
        camera.resolution = (2592, 1944)
        assert camera.resolution == (2592, 1944)
        assert camera._camera[0].port[2][0].format[0].es[0].video.width == 2592
        assert camera._camera[0].port[2][0].format[0].es[0].video.height == 1952
        # Test some irregular resolutions
        camera.resolution = (100, 100)
        assert camera.resolution == (100, 100)
        assert camera._camera[0].port[2][0].format[0].es[0].video.width == 128
        assert camera._camera[0].port[2][0].format[0].es[0].video.height == 112
        # Anything below 16,16 will fail (because the camera's vertical
        # resolution works in increments of 16)
        with pytest.raises(picamera.PiCameraError):
            camera.resolution = (0, 0)
        with pytest.raises(picamera.PiCameraError):
            camera.resolution = (15, 15)
    finally:
        camera.resolution = save_resolution


########NEW FILE########
__FILENAME__ = test_capture
# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013,2014 Dave Hughes <dave@waveform.org.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str equivalent to Py3's
str = type('')

import io
import os
import time
import tempfile
import picamera
import pytest
from PIL import Image
from collections import namedtuple
from verify import verify_image, verify_raw


CaptureCase = namedtuple('CaptureCase', ('format', 'ext', 'options'))

CAPTURE_CASES = (
    CaptureCase('jpeg', '.jpg', {'quality': 95}),
    CaptureCase('jpeg', '.jpg', {}),
    CaptureCase('jpeg', '.jpg', {'resize': (640, 480)}),
    CaptureCase('jpeg', '.jpg', {'quality': 50}),
    CaptureCase('gif',  '.gif', {}),
    CaptureCase('png',  '.png', {}),
    CaptureCase('bmp',  '.bmp', {}),
    )


# Run tests with a variety of file suffixes and expected formats
@pytest.fixture(scope='module', params=CAPTURE_CASES)
def filename_format_options(request):
    filename = tempfile.mkstemp(suffix=request.param.ext)[1]
    def fin():
        os.unlink(filename)
    request.addfinalizer(fin)
    return filename, request.param.format, request.param.options

# Run tests with a variety of format specs
@pytest.fixture(params=CAPTURE_CASES)
def format_options(request):
    return request.param.format, request.param.options

# Run tests with one of the two supported raw formats
@pytest.fixture(params=('yuv', 'rgb', 'rgba', 'bgr', 'bgra'))
def raw_format(request):
    return request.param

@pytest.fixture(params=(False, True))
def use_video_port(request):
    return request.param


def test_capture_to_file(
        camera, previewing, mode, filename_format_options, use_video_port):
    filename, format, options = filename_format_options
    resolution, framerate = mode
    #if resolution == (2592, 1944) and format == 'gif' and not use_video_port:
    #    pytest.xfail('Camera runs out of memory with this combination')
    #if resolution == (2592, 1944) and 'resize' in options:
    #    pytest.xfail('Camera runs out of memory with this combination')
    camera.capture(filename, use_video_port=use_video_port, **options)
    if 'resize' in options:
        resolution = options['resize']
    verify_image(filename, format, resolution)

def test_capture_to_stream(
        camera, previewing, mode, format_options, use_video_port):
    stream = io.BytesIO()
    format, options = format_options
    resolution, framerate = mode
    #if resolution == (2592, 1944) and format == 'gif' and not use_video_port:
    #    pytest.xfail('Camera runs out of memory with this combination')
    #if resolution == (2592, 1944) and 'resize' in options:
    #    pytest.xfail('Camera runs out of memory with this combination')
    if 'resize' in options:
        resolution = options['resize']
    camera.capture(stream, format, use_video_port=use_video_port, **options)
    stream.seek(0)
    verify_image(stream, format, resolution)

def test_capture_continuous_to_file(
        camera, previewing, mode, tmpdir, use_video_port):
    resolution, framerate = mode
    for i, filename in enumerate(
            camera.capture_continuous(os.path.join(
                str(tmpdir), 'image{counter:02d}.jpg'),
                use_video_port=use_video_port)):
        verify_image(filename, 'jpeg', resolution)
        if i == 3:
            break

def test_capture_continuous_to_stream(
        camera, previewing, mode, use_video_port):
    resolution, framerate = mode
    stream = io.BytesIO()
    for i, foo in enumerate(
            camera.capture_continuous(stream, format='jpeg',
                use_video_port=use_video_port)):
        stream.truncate()
        stream.seek(0)
        verify_image(stream, 'jpeg', resolution)
        stream.seek(0)
        if i == 3:
            break

def test_capture_sequence_to_file(
        camera, previewing, mode, tmpdir, use_video_port):
    resolution, framerate = mode
    filenames = [os.path.join(str(tmpdir), 'image%d.jpg' % i) for i in range(3)]
    camera.capture_sequence(filenames, use_video_port=use_video_port)
    for filename in filenames:
        verify_image(filename, 'jpeg', resolution)

def test_capture_sequence_to_stream(
        camera, previewing, mode, use_video_port):
    resolution, framerate = mode
    streams = [io.BytesIO() for i in range(3)]
    camera.capture_sequence(streams, use_video_port=use_video_port)
    for stream in streams:
        stream.seek(0)
        verify_image(stream, 'jpeg', resolution)

def test_capture_raw(camera, mode, raw_format, use_video_port):
    resolution, framerate = mode
    if resolution == (2592, 1944) and raw_format in ('rgba', 'bgra') and not use_video_port:
        pytest.xfail('Camera runs out of memory with this combination')
    if resolution == (2592, 1944) and raw_format in ('rgb', 'bgr'):
        pytest.xfail('Camera times out with this combination')
    stream = io.BytesIO()
    camera.capture(stream, format=raw_format, use_video_port=use_video_port)
    verify_raw(stream, raw_format, resolution)

def test_capture_continuous_raw(camera, mode, raw_format, use_video_port):
    resolution, framerate = mode
    if resolution == (2592, 1944) and raw_format in ('rgba', 'bgra') and not use_video_port:
        pytest.xfail('Camera runs out of memory with this combination')
    if resolution == (2592, 1944) and raw_format in ('rgb', 'bgr'):
        pytest.xfail('Camera times out with this combination')
    for i, stream in enumerate(camera.capture_continuous(
            io.BytesIO(), format=raw_format, use_video_port=use_video_port)):
        if i == 3:
            break
        verify_raw(stream, raw_format, resolution)
        stream.seek(0)
        stream.truncate()

def test_capture_sequence_raw(camera, mode, raw_format, use_video_port):
    resolution, framerate = mode
    if resolution == (2592, 1944) and raw_format in ('rgba', 'bgra') and not use_video_port:
        pytest.xfail('Camera runs out of memory with this combination')
    if resolution == (2592, 1944) and raw_format in ('rgb', 'bgr'):
        pytest.xfail('Camera times out with this combination')
    streams = [io.BytesIO() for i in range(3)]
    camera.capture_sequence(streams, format=raw_format, use_video_port=use_video_port)
    for stream in streams:
        verify_raw(stream, raw_format, resolution)

def test_capture_bayer(camera, mode):
    stream = io.BytesIO()
    camera.capture(stream, format='jpeg', bayer=True)
    # Bayer data is always the last 6404096 bytes of the stream, and starts
    # with 'BRCM'
    stream.seek(-6404096, io.SEEK_END)
    assert stream.read(4) == 'BRCM'

def test_exif_ascii(camera, mode):
    camera.exif_tags['IFD0.Artist'] = 'Me!'
    camera.exif_tags['IFD0.Copyright'] = 'Copyright (c) 2000 Foo'
    # Exif is only supported with JPEGs...
    stream = io.BytesIO()
    camera.capture(stream, 'jpeg')
    stream.seek(0)
    img = Image.open(stream)
    exif = img._getexif()
    # IFD0.Artist = 315
    # IFD0.Copyright = 33432
    assert exif[315] == 'Me!'
    assert exif[33432] == 'Copyright (c) 2000 Foo'

@pytest.mark.xfail(reason="Exif binary values don't work")
def test_exif_binary(camera, mode):
    camera.exif_tags['IFD0.Copyright'] = b'Photographer copyright (c) 2000 Foo\x00Editor copyright (c) 2002 Bar\x00'
    camera.exif_tags['IFD0.UserComment'] = b'UNICODE\x00\xff\xfeF\x00o\x00o\x00'
    # Exif is only supported with JPEGs...
    stream = io.BytesIO()
    camera.capture(stream, 'jpeg')
    stream.seek(0)
    img = Image.open(stream)
    exif = img._getexif()
    # IFD0.Copyright = 33432
    # IFD0.UserComment = 37510
    assert exif[33432] == b'Photographer copyright (c) 2000 Foo\x00Editor copyright (c) 2002 Bar\x00'
    assert exif[37510] == b'UNICODE\x00\xff\xfeF\x00o\x00o\x00'


########NEW FILE########
__FILENAME__ = test_exc
# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013,2014 Dave Hughes <dave@waveform.org.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str equivalent to Py3's
str = type('')

from picamera import mmal
from picamera.exc import mmal_check, PiCameraError
import pytest

def test_mmal_check():
    mmal_check(mmal.MMAL_SUCCESS)
    with pytest.raises(PiCameraError):
        mmal_check(mmal.MMAL_ENOSYS)
    with pytest.raises(PiCameraError):
        mmal_check(mmal.MMAL_ENOMEM)
    with pytest.raises(PiCameraError):
        mmal_check(mmal.MMAL_ENOSPC)
    with pytest.raises(PiCameraError):
        mmal_check(mmal.MMAL_EINVAL)

########NEW FILE########
__FILENAME__ = test_misc
# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013,2014 Dave Hughes <dave@waveform.org.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str equivalent to Py3's
str = type('')

import picamera
import pytest

def test_dual_camera(camera):
    with pytest.raises(picamera.PiCameraError):
        another_camera = picamera.PiCamera()


########NEW FILE########
__FILENAME__ = test_mock
# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013,2014 Dave Hughes <dave@waveform.org.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str equivalent to Py3's
str = type('')

import ctypes as ct
import picamera.mmal as mmal
import picamera
import pytest
import mock

def test_camera_init():
    with \
            mock.patch('picamera.camera.bcm_host') as bcm_host, \
            mock.patch('picamera.camera.mmal') as mmal, \
            mock.patch('picamera.camera.ct') as ct:
        mmal.mmal_component_create.return_value = 1
        with pytest.raises(picamera.PiCameraError) as e:
            picamera.PiCamera()
        assert e.value.args[0].startswith("Failed to create camera component")
        mmal.mmal_component_create.return_value = 0
        ct.POINTER.return_value.return_value[0].output_num = 0
        ct.sizeof.return_value = 0
        with pytest.raises(picamera.PiCameraError) as e:
            picamera.PiCamera()
        assert e.value.args[0] == "Camera doesn't have output ports"
        ct.POINTER.return_value.return_value[0].output_num = 3
        mmal.mmal_port_enable.return_value = 1
        with pytest.raises(picamera.PiCameraError) as e:
            picamera.PiCamera()
        assert e.value.args[0].startswith("Unable to enable control port")
        mmal.mmal_port_enable.return_value = 0
        mmal.mmal_port_parameter_set.return_value = 1
        with pytest.raises(picamera.PiCameraError) as e:
            picamera.PiCamera()
        assert e.value.args[0].startswith("Camera control port couldn't be configured")
        mmal.mmal_port_parameter_set.return_value = 0
        mmal.mmal_port_format_commit.return_value = 0
        for p in picamera.PiCamera.CAMERA_PORTS:
            ct.POINTER.return_value.return_value[0].output[p][0].buffer_num = 1
        mmal.mmal_component_enable.return_value = 1
        with pytest.raises(picamera.PiCameraError) as e:
            picamera.PiCamera()
        assert e.value.args[0].startswith("Camera component couldn't be enabled")

def test_camera_led():
    with mock.patch('picamera.camera.GPIO') as GPIO:
        with picamera.PiCamera() as camera:
            camera.led = True
            GPIO.setmode.assert_called_once_with(GPIO.BCM)
            GPIO.setup.assert_called_once_with(5, GPIO.OUT, initial=GPIO.LOW)
            GPIO.output.assert_called_with(5, True)
            camera.led = False
            GPIO.output.assert_called_with(5, False)
            with pytest.raises(AttributeError):
                camera.led

########NEW FILE########
__FILENAME__ = test_record
# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013,2014 Dave Hughes <dave@waveform.org.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str equivalent to Py3's
str = type('')

import os
import time
import tempfile
import picamera
import pytest
from collections import namedtuple
from verify import verify_video, verify_image


RecordingCase = namedtuple('RecordingCase', ('format', 'ext', 'options'))

RECORDING_CASES = (
    RecordingCase('h264',  '.h264', {'profile': 'baseline'}),
    RecordingCase('h264',  '.h264', {'profile': 'main'}),
    RecordingCase('h264',  '.h264', {'profile': 'high'}),
    RecordingCase('h264',  '.h264', {'profile': 'constrained'}),
    RecordingCase('h264',  '.h264', {'resize': (640, 480)}),
    RecordingCase('h264',  '.h264', {'bitrate': 0, 'quantization': 10}),
    RecordingCase('h264',  '.h264', {'bitrate': 0, 'quantization': 20}),
    RecordingCase('h264',  '.h264', {'bitrate': 0, 'quantization': 40}),
    RecordingCase('h264',  '.h264', {'bitrate': 10000000, 'intra_period': 15}),
    RecordingCase('h264',  '.h264', {'bitrate': 10000000, 'inline_headers': False}),
    RecordingCase('h264',  '.h264', {'bitrate': 10000000, 'sei': True}),
    RecordingCase('h264',  '.h264', {'bitrate': 15000000}),
    RecordingCase('h264',  '.h264', {'bitrate': 20000000, 'profile': 'main'}),
    RecordingCase('mjpeg', '.mjpg', {}),
    RecordingCase('mjpeg', '.mjpg', {'bitrate': 10000000}),
    RecordingCase('mjpeg', '.mjpg', {'bitrate': 0, 'quantization': 20}),
    )


@pytest.fixture(params=RECORDING_CASES)
def filenames_format_options(request):
    filename1 = tempfile.mkstemp(suffix=request.param.ext)[1]
    filename2 = tempfile.mkstemp(suffix=request.param.ext)[1]
    def fin():
        os.unlink(filename1)
        os.unlink(filename2)
    request.addfinalizer(fin)
    return filename1, filename2, request.param.format, request.param.options

# Run tests with a variety of format specs
@pytest.fixture(params=RECORDING_CASES)
def format_options(request):
    return request.param.format, request.param.options


def test_record_to_file(camera, previewing, mode, filenames_format_options):
    filename1, filename2, format, options = filenames_format_options
    resolution, framerate = mode
    if resolution == (2592, 1944) and 'resize' not in options:
        pytest.xfail('Cannot encode video at max resolution')
    if resolution[1] > 480 and format == 'mjpeg':
        pytest.xfail('Locks up camera')
    camera.start_recording(filename1, **options)
    try:
        camera.wait_recording(1)
        verify2 = (
                format != 'h264' or (
                    options.get('inline_headers', True) and
                    options.get('bitrate', 1)
                    )
                )
        if verify2:
            camera.split_recording(filename2)
            camera.wait_recording(1)
        else:
            with pytest.raises(picamera.PiCameraRuntimeError):
                camera.split_recording(filename2)
    finally:
        camera.stop_recording()
    if 'resize' in options:
        resolution = options['resize']
    verify_video(filename1, format, resolution)
    if verify2:
        verify_video(filename2, format, resolution)

def test_record_to_stream(camera, previewing, mode, format_options):
    format, options = format_options
    resolution, framerate = mode
    if resolution == (2592, 1944) and 'resize' not in options:
        pytest.xfail('Cannot encode video at max resolution')
    if resolution[1] > 480 and format == 'mjpeg':
        pytest.xfail('Locks up camera')
    stream1 = tempfile.SpooledTemporaryFile()
    stream2 = tempfile.SpooledTemporaryFile()
    camera.start_recording(stream1, format, **options)
    try:
        camera.wait_recording(1)
        verify2 = (
                format != 'h264' or (
                    options.get('inline_headers', True) and
                    options.get('bitrate', 1)
                    )
                )
        if verify2:
            camera.split_recording(stream2)
            camera.wait_recording(1)
        else:
            with pytest.raises(picamera.PiCameraRuntimeError):
                camera.split_recording(stream2)
    finally:
        camera.stop_recording()
    stream1.seek(0)
    if 'resize' in options:
        resolution = options['resize']
    verify_video(stream1, format, resolution)
    if verify2:
        stream2.seek(0)
        verify_video(stream2, format, resolution)

def test_record_sequence_to_file(camera, previewing, mode, tmpdir):
    resolution, framerate = mode
    if resolution == (2592, 1944):
        pytest.xfail('Cannot encode video at max resolution')
    filenames = [os.path.join(str(tmpdir), 'clip%d.h264' % i) for i in range(3)]
    for filename in camera.record_sequence(filenames):
        camera.wait_recording(1)
    for filename in filenames:
        verify_video(filename, 'h264', resolution)

def test_record_sequence_to_stream(camera, previewing, mode):
    resolution, framerate = mode
    if resolution == (2592, 1944):
        pytest.xfail('Cannot encode video at max resolution')
    streams = [tempfile.SpooledTemporaryFile() for i in range(3)]
    for stream in camera.record_sequence(streams):
        camera.wait_recording(1)
    for stream in streams:
        stream.seek(0)
        verify_video(stream, 'h264', resolution)

def test_circular_record(camera, previewing, mode):
    resolution, framerate = mode
    if resolution == (2592, 1944):
        pytest.xfail('Cannot encode video at max resolution')
    stream = picamera.PiCameraCircularIO(camera, seconds=4)
    camera.start_recording(stream, format='h264')
    try:
        # Keep recording until the stream is definitely full and starts
        # removing earlier bits, or until 20 seconds
        start = time.time()
        while stream._length < stream._size and time.time() - start < 20:
            camera.wait_recording(1)
        # Record one more second, then test the result
        camera.wait_recording(1)
    finally:
        camera.stop_recording()
    temp = tempfile.SpooledTemporaryFile()
    for frame in stream.frames:
        if frame.header:
            stream.seek(frame.position)
            break
    while True:
        buf = stream.read1()
        if not buf:
            break
        temp.write(buf)
    temp.seek(0)
    verify_video(temp, 'h264', resolution)

def test_split_and_capture(camera, previewing, mode):
    resolution, framerate = mode
    if resolution == (2592, 1944):
        pytest.xfail('Cannot encode video at max resolution')
    v_stream1 = tempfile.SpooledTemporaryFile()
    v_stream2 = tempfile.SpooledTemporaryFile()
    c_stream1 = tempfile.SpooledTemporaryFile()
    camera.start_recording(v_stream1, format='h264')
    try:
        camera.wait_recording(1)
        camera.capture(c_stream1, format='jpeg', use_video_port=True)
        camera.split_recording(v_stream2)
        camera.wait_recording(1)
    finally:
        camera.stop_recording()
    v_stream1.seek(0)
    v_stream2.seek(0)
    c_stream1.seek(0)
    verify_image(c_stream1, 'jpeg', resolution)
    verify_video(v_stream1, 'h264', resolution)
    verify_video(v_stream2, 'h264', resolution)

def test_multi_res_record(camera, previewing, mode):
    resolution, framerate = mode
    if resolution == (2592, 1944):
        pytest.xfail('Cannot encode video at max resolution')
    v_stream1 = tempfile.SpooledTemporaryFile()
    v_stream2 = tempfile.SpooledTemporaryFile()
    new_res = (resolution[0] // 2, resolution[1] // 2)
    camera.start_recording(v_stream1, format='h264')
    try:
        camera.start_recording(v_stream2, format='h264', resize=new_res, splitter_port=2)
        try:
            camera.wait_recording(1)
            camera.wait_recording(1, splitter_port=2)
        finally:
            camera.stop_recording(splitter_port=2)
    finally:
        camera.stop_recording()
    v_stream1.seek(0)
    v_stream2.seek(0)
    verify_video(v_stream1, 'h264', resolution)
    verify_video(v_stream2, 'h264', new_res)


########NEW FILE########
__FILENAME__ = test_streams
# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013,2014 Dave Hughes <dave@waveform.org.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str equivalent to Py3's
str = type('')

import io
import pytest
from picamera.streams import CircularIO


def test_circular_io():
    with pytest.raises(ValueError):
        CircularIO(-1)
    stream = CircularIO(10)
    assert stream.readable()
    assert stream.writable()
    assert stream.seekable()
    assert stream.size == 10
    assert stream.tell() == 0
    stream.write(b'')
    assert stream.tell() == 0
    assert stream.getvalue() == b''
    stream.write(b'abc')
    assert stream.getvalue() == b'abc'
    assert stream.tell() == 3
    stream.write(b'def')
    assert stream.getvalue() == b'abcdef'
    assert stream.tell() == 6
    stream.write(b'ghijklm')
    assert stream.getvalue() == b'defghijklm'
    stream.seek(0)
    assert stream.read(1) == b'd'
    assert stream.read(4) == b'efgh'
    assert stream.read() == b'ijklm'
    assert stream.tell() == 10
    stream.seek(0)
    assert stream.read() == stream.getvalue()
    stream.seek(0)
    assert stream.tell() == 0
    stream.write(b'')
    assert stream.getvalue() == b'defghijklm'
    assert stream.tell() == 0
    stream.write(b'a')
    assert stream.getvalue() == b'aefghijklm'
    assert stream.tell() == 1
    stream.write(b'bcd')
    assert stream.getvalue() == b'abcdhijklm'
    assert stream.tell() == 4
    stream.seek(0)
    assert stream.tell() == 0
    stream.write(b'efghijklmnop')
    assert stream.getvalue() == b'ghijklmnop'
    assert stream.tell() == 10
    assert stream.seek(-1, io.SEEK_CUR) == 9
    assert stream.seek(0, io.SEEK_END) == 10
    with pytest.raises(ValueError):
        stream.seek(-1)
    stream.seek(15)
    assert stream.tell() == 15
    stream.write(b'qrs')
    assert stream.getvalue() == b'op\x00\x00\x00\x00\x00qrs'
    assert stream.tell() == 10
    with pytest.raises(ValueError):
        stream.truncate(-1)
    stream.seek(4)
    stream.truncate()
    assert stream.getvalue() == b'op\x00\x00'
    assert stream.tell() == 4
    stream.write(b'tuv')
    stream.write(b'wxyz')
    assert stream.getvalue() == b'p\x00\x00tuvwxyz'
    assert stream.tell() == 10
    stream.truncate(5)
    assert stream.getvalue() == b'p\x00\x00tu'
    assert stream.tell() == 10
    stream.write(b'')
    assert stream.getvalue() == b'p\x00\x00tu\x00\x00\x00\x00\x00'
    assert stream.tell() == 10


########NEW FILE########
__FILENAME__ = verify
# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013,2014 Dave Hughes <dave@waveform.org.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str equivalent to Py3's
str = type('')

import os
import re
import math
import subprocess
from PIL import Image


def verify_video(filename_or_obj, format, resolution):
    """
    Verify that the video in filename_or_obj has the specified format and
    resolution.
    """
    width, height = resolution
    if isinstance(filename_or_obj, str):
        p = subprocess.Popen([
            'avconv',
            '-f', format,
            '-i', filename_or_obj,
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    else:
        p = subprocess.Popen([
            'avconv',
            '-f', format,
            '-i', '-',
            ], stdin=filename_or_obj, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = p.communicate()[0]
    assert p.returncode == 1, 'avconv returned unexpected code %d' % p.returncode
    state = 'start'
    for line in out.splitlines():
        line = line.decode('utf-8').strip()
        if state == 'start' and re.match(r'^Input #0', line):
            state = 'input'
        elif state == 'input' and re.match(r'^Duration', line):
            state = 'dur'
        elif state == 'dur' and re.match(r'^Stream #0\.0', line):
            assert re.match(
                r'^Stream #0\.0: '
                r'Video: %s( \(.*\))?, '
                r'yuvj?420p, '
                r'%dx%d( \[PAR \d+:\d+ DAR \d+:\d+\])?, '
                r'\d+ fps, \d+ tbr, \d+k? tbn, \d+k? tbc$' % (
                    format, width, height),
                line
                ), 'Unexpected avconv output: %s' % line
            return
    assert False, 'Failed to locate stream analysis in avconv output'


def verify_image(filename_or_obj, format, resolution):
    """
    Verify that the image in filename_or_obj has the specified format and
    resolution.
    """
    img = Image.open(filename_or_obj)
    assert img.size == resolution
    assert img.format.lower() == format.lower()
    img.verify()


def verify_raw(stream, format, resolution):
    # Calculate the expected size of the streams for the current
    # resolution; horizontal resolution is rounded up to the nearest
    # multiple of 32, and vertical to the nearest multiple of 16 by the
    # camera for raw data. RGB format holds 3 bytes per pixel, YUV format
    # holds 1.5 bytes per pixel (1 byte of Y per pixel, and 2 bytes of Cb
    # and Cr per 4 pixels), etc.
    size = (
            math.ceil(resolution[0] / 32) * 32
            * math.ceil(resolution[1] / 16) * 16
            * {
                'yuv': 1.5,
                'rgb': 3,
                'bgr': 3,
                'rgba': 4,
                'bgra': 4
                }[format]
            )
    stream.seek(0, os.SEEK_END)
    assert stream.tell() == size


########NEW FILE########
