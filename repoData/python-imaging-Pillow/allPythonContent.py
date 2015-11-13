__FILENAME__ = conf
# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.abspath('../'))
import PIL

### general configuration ###

needs_sphinx = '1.0'

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode',
              'sphinx.ext.intersphinx']
intersphinx_mapping = {'http://docs.python.org/2/': None}

source_suffix = '.rst'
templates_path = ['_templates']
#source_encoding = 'utf-8-sig'
master_doc = 'index'

project = u'Pillow (PIL fork)'
copyright = (u'1997-2011 by Secret Labs AB,'
             u' 1995-2011 by Fredrik Lundh, 2010-2013 Alex Clark')

# The short X.Y version.
version = PIL.PILLOW_VERSION
# The full version, including alpha/beta/rc tags.
release = version

# currently excluding autodoc'd plugs
exclude_patterns = ['_build', 'plugins.rst']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

### HTML output ###

from better import better_theme_path
html_theme_path = [better_theme_path]
html_theme = 'better'

html_title = "Pillow v{release} (PIL fork)".format(release=release)
html_short_title = "Home"
html_static_path = ['_static']

html_theme_options = {}

html_sidebars = {
    '**': ['localtoc.html', 'sourcelink.html', 'sidebarhelp.html',
           'searchbox.html'],
    'index': ['globaltoc.html', 'sidebarhelp.html', 'searchbox.html'],
}

# Output file base name for HTML help builder.
htmlhelp_basename = 'Pillowdoc'


### LaTeX output (RtD PDF output as well) ###

latex_elements = {}

latex_documents = [
    ('index', 'Pillow.tex', u'Pillow (PIL fork) Documentation', u'Author',
     'manual'),
]


# skip_api_docs setting will skip PIL.rst if True. Used for working on the
# guides; makes livereload basically instantaneous.
def setup(app):
    app.add_config_value('skip_api_docs', False, True)

skip_api_docs = False

if skip_api_docs:
    exclude_patterns += ['PIL.rst']

########NEW FILE########
__FILENAME__ = ArgImagePlugin
#
# THIS IS WORK IN PROGRESS
#
# The Python Imaging Library.
# $Id$
#
# ARG animation support code
#
# history:
# 1996-12-30 fl   Created
# 1996-01-06 fl   Added safe scripting environment
# 1996-01-10 fl   Added JHDR, UHDR and sYNC support
# 2005-03-02 fl   Removed AAPP and ARUN support
#
# Copyright (c) Secret Labs AB 1997.
# Copyright (c) Fredrik Lundh 1996-97.
#
# See the README file for information on usage and redistribution.
#

from __future__ import print_function

__version__ = "0.4"

from PIL import Image, ImageFile, ImagePalette

from PIL.PngImagePlugin import i8, i16, i32, ChunkStream, _MODES

MAGIC = b"\212ARG\r\n\032\n"

# --------------------------------------------------------------------
# ARG parser

class ArgStream(ChunkStream):
    "Parser callbacks for ARG data"

    def __init__(self, fp):

        ChunkStream.__init__(self, fp)

        self.eof = 0

        self.im = None
        self.palette = None

        self.__reset()

    def __reset(self):

        # reset decoder state (called on init and sync)

        self.count = 0
        self.id = None
        self.action = ("NONE",)

        self.images = {}
        self.names = {}


    def chunk_AHDR(self, offset, bytes):
        "AHDR -- animation header"

        # assertions
        if self.count != 0:
            raise SyntaxError("misplaced AHDR chunk")

        s = self.fp.read(bytes)
        self.size = i32(s), i32(s[4:])
        try:
            self.mode, self.rawmode = _MODES[(i8(s[8]), i8(s[9]))]
        except:
            raise SyntaxError("unknown ARG mode")

        if Image.DEBUG:
            print("AHDR size", self.size)
            print("AHDR mode", self.mode, self.rawmode)

        return s

    def chunk_AFRM(self, offset, bytes):
        "AFRM -- next frame follows"

        # assertions
        if self.count != 0:
            raise SyntaxError("misplaced AFRM chunk")

        self.show = 1
        self.id = 0
        self.count = 1
        self.repair = None

        s = self.fp.read(bytes)
        if len(s) >= 2:
            self.id = i16(s)
            if len(s) >= 4:
                self.count = i16(s[2:4])
                if len(s) >= 6:
                    self.repair = i16(s[4:6])
                else:
                    self.repair = None

        if Image.DEBUG:
            print("AFRM", self.id, self.count)

        return s

    def chunk_ADEF(self, offset, bytes):
        "ADEF -- store image"

        # assertions
        if self.count != 0:
            raise SyntaxError("misplaced ADEF chunk")

        self.show = 0
        self.id = 0
        self.count = 1
        self.repair = None

        s = self.fp.read(bytes)
        if len(s) >= 2:
            self.id = i16(s)
            if len(s) >= 4:
                self.count = i16(s[2:4])

        if Image.DEBUG:
            print("ADEF", self.id, self.count)

        return s

    def chunk_NAME(self, offset, bytes):
        "NAME -- name the current image"

        # assertions
        if self.count == 0:
            raise SyntaxError("misplaced NAME chunk")

        name = self.fp.read(bytes)
        self.names[self.id] = name

        return name

    def chunk_AEND(self, offset, bytes):
        "AEND -- end of animation"

        if Image.DEBUG:
            print("AEND")

        self.eof = 1

        raise EOFError("end of ARG file")

    def __getmodesize(self, s, full=1):

        size = i32(s), i32(s[4:])

        try:
            mode, rawmode = _MODES[(i8(s[8]), i8(s[9]))]
        except:
            raise SyntaxError("unknown image mode")

        if full:
            if i8(s[12]):
                pass # interlace not yet supported
            if i8(s[11]):
                raise SyntaxError("unknown filter category")

        return size, mode, rawmode

    def chunk_PAST(self, offset, bytes):
        "PAST -- paste one image into another"

        # assertions
        if self.count == 0:
            raise SyntaxError("misplaced PAST chunk")

        if self.repair is not None:
            # we must repair the target image before we
            # start pasting

            # brute force; a better solution would be to
            # update only the dirty rectangles in images[id].
            # note that if images[id] doesn't exist, it must
            # be created

            self.images[self.id] = self.images[self.repair].copy()
            self.repair = None

        s = self.fp.read(bytes)
        im = self.images[i16(s)]
        x, y = i32(s[2:6]), i32(s[6:10])
        bbox = x, y, im.size[0]+x, im.size[1]+y

        if im.mode in ["RGBA"]:
            # paste with transparency
            # FIXME: should handle P+transparency as well
            self.images[self.id].paste(im, bbox, im)
        else:
            # paste without transparency
            self.images[self.id].paste(im, bbox)

        self.action = ("PAST",)
        self.__store()

        return s

    def chunk_BLNK(self, offset, bytes):
        "BLNK -- create blank image"

        # assertions
        if self.count == 0:
            raise SyntaxError("misplaced BLNK chunk")

        s = self.fp.read(bytes)
        size, mode, rawmode = self.__getmodesize(s, 0)

        # store image (FIXME: handle colour)
        self.action = ("BLNK",)
        self.im = Image.core.fill(mode, size, 0)
        self.__store()

        return s

    def chunk_IHDR(self, offset, bytes):
        "IHDR -- full image follows"

        # assertions
        if self.count == 0:
            raise SyntaxError("misplaced IHDR chunk")

        # image header
        s = self.fp.read(bytes)
        size, mode, rawmode = self.__getmodesize(s)

        # decode and store image
        self.action = ("IHDR",)
        self.im = Image.core.new(mode, size)
        self.decoder = Image.core.zip_decoder(rawmode)
        self.decoder.setimage(self.im, (0,0) + size)
        self.data = b""

        return s

    def chunk_DHDR(self, offset, bytes):
        "DHDR -- delta image follows"

        # assertions
        if self.count == 0:
            raise SyntaxError("misplaced DHDR chunk")

        s = self.fp.read(bytes)

        size, mode, rawmode = self.__getmodesize(s)

        # delta header
        diff = i8(s[13])
        offs = i32(s[14:18]), i32(s[18:22])

        bbox = offs + (offs[0]+size[0], offs[1]+size[1])

        if Image.DEBUG:
            print("DHDR", diff, bbox)

        # FIXME: decode and apply image
        self.action = ("DHDR", diff, bbox)

        # setup decoder
        self.im = Image.core.new(mode, size)

        self.decoder = Image.core.zip_decoder(rawmode)
        self.decoder.setimage(self.im, (0,0) + size)

        self.data = b""

        return s

    def chunk_JHDR(self, offset, bytes):
        "JHDR -- JPEG image follows"

        # assertions
        if self.count == 0:
            raise SyntaxError("misplaced JHDR chunk")

        # image header
        s = self.fp.read(bytes)
        size, mode, rawmode = self.__getmodesize(s, 0)

        # decode and store image
        self.action = ("JHDR",)
        self.im = Image.core.new(mode, size)
        self.decoder = Image.core.jpeg_decoder(rawmode)
        self.decoder.setimage(self.im, (0,0) + size)
        self.data = b""

        return s

    def chunk_UHDR(self, offset, bytes):
        "UHDR -- uncompressed image data follows (EXPERIMENTAL)"

        # assertions
        if self.count == 0:
            raise SyntaxError("misplaced UHDR chunk")

        # image header
        s = self.fp.read(bytes)
        size, mode, rawmode = self.__getmodesize(s, 0)

        # decode and store image
        self.action = ("UHDR",)
        self.im = Image.core.new(mode, size)
        self.decoder = Image.core.raw_decoder(rawmode)
        self.decoder.setimage(self.im, (0,0) + size)
        self.data = b""

        return s

    def chunk_IDAT(self, offset, bytes):
        "IDAT -- image data block"

        # pass compressed chunks through the decoder
        s = self.fp.read(bytes)
        self.data = self.data + s
        n, e = self.decoder.decode(self.data)
        if n < 0:
            # end of image
            if e < 0:
                raise IOError("decoder error %d" % e)
        else:
            self.data = self.data[n:]

        return s

    def chunk_DEND(self, offset, bytes):
        return self.chunk_IEND(offset, bytes)

    def chunk_JEND(self, offset, bytes):
        return self.chunk_IEND(offset, bytes)

    def chunk_UEND(self, offset, bytes):
        return self.chunk_IEND(offset, bytes)

    def chunk_IEND(self, offset, bytes):
        "IEND -- end of image"

        # we now have a new image.  carry out the operation
        # defined by the image header.

        # won't need these anymore
        del self.decoder
        del self.data

        self.__store()

        return self.fp.read(bytes)

    def __store(self):

        # apply operation
        cid = self.action[0]

        if cid in ["BLNK", "IHDR", "JHDR", "UHDR"]:
            # store
            self.images[self.id] = self.im

        elif cid == "DHDR":
            # paste
            cid, mode, bbox = self.action
            im0 = self.images[self.id]
            im1 = self.im
            if mode == 0:
                im1 = im1.chop_add_modulo(im0.crop(bbox))
            im0.paste(im1, bbox)

        self.count = self.count - 1

        if self.count == 0 and self.show:
            self.im = self.images[self.id]
            raise EOFError # end of this frame

    def chunk_PLTE(self, offset, bytes):
        "PLTE -- palette data"

        s = self.fp.read(bytes)
        if self.mode == "P":
            self.palette = ImagePalette.raw("RGB", s)
        return s

    def chunk_sYNC(self, offset, bytes):
        "SYNC -- reset decoder"

        if self.count != 0:
            raise SyntaxError("misplaced sYNC chunk")

        s = self.fp.read(bytes)
        self.__reset()
        return s


# --------------------------------------------------------------------
# ARG reader

def _accept(prefix):
    return prefix[:8] == MAGIC

##
# Image plugin for the experimental Animated Raster Graphics format.

class ArgImageFile(ImageFile.ImageFile):

    format = "ARG"
    format_description = "Animated raster graphics"

    def _open(self):

        if Image.warnings:
            Image.warnings.warn(
                "The ArgImagePlugin driver is obsolete, and will be removed "
                "from a future release of PIL.  If you rely on this module, "
                "please contact the PIL authors.",
                RuntimeWarning
                )

        if self.fp.read(8) != MAGIC:
            raise SyntaxError("not an ARG file")

        self.arg = ArgStream(self.fp)

        # read and process the first chunk (AHDR)

        cid, offset, bytes = self.arg.read()

        if cid != "AHDR":
            raise SyntaxError("expected an AHDR chunk")

        s = self.arg.call(cid, offset, bytes)

        self.arg.crc(cid, s)

        # image characteristics
        self.mode = self.arg.mode
        self.size = self.arg.size

    def load(self):

        if self.arg.im is None:
            self.seek(0)

        # image data
        self.im = self.arg.im
        self.palette = self.arg.palette

        # set things up for further processing
        Image.Image.load(self)

    def seek(self, frame):

        if self.arg.eof:
            raise EOFError("end of animation")

        self.fp = self.arg.fp

        while True:

            #
            # process chunks

            cid, offset, bytes = self.arg.read()

            if self.arg.eof:
                raise EOFError("end of animation")

            try:
                s = self.arg.call(cid, offset, bytes)
            except EOFError:
                break

            except "glurk": # AttributeError
                if Image.DEBUG:
                    print(cid, bytes, "(unknown)")
                s = self.fp.read(bytes)

            self.arg.crc(cid, s)

        self.fp.read(4) # ship extra CRC

    def tell(self):
        return 0

    def verify(self):
        "Verify ARG file"

        # back up to first chunk
        self.fp.seek(8)

        self.arg.verify(self)
        self.arg.close()

        self.fp = None

#
# --------------------------------------------------------------------

Image.register_open("ARG", ArgImageFile, _accept)

Image.register_extension("ARG", ".arg")

Image.register_mime("ARG", "video/x-arg")

########NEW FILE########
__FILENAME__ = BdfFontFile
#
# The Python Imaging Library
# $Id$
#
# bitmap distribution font (bdf) file parser
#
# history:
# 1996-05-16 fl   created (as bdf2pil)
# 1997-08-25 fl   converted to FontFile driver
# 2001-05-25 fl   removed bogus __init__ call
# 2002-11-20 fl   robustification (from Kevin Cazabon, Dmitry Vasiliev)
# 2003-04-22 fl   more robustification (from Graham Dumpleton)
#
# Copyright (c) 1997-2003 by Secret Labs AB.
# Copyright (c) 1997-2003 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#

from PIL import Image
from PIL import FontFile


# --------------------------------------------------------------------
# parse X Bitmap Distribution Format (BDF)
# --------------------------------------------------------------------

bdf_slant = {
   "R": "Roman",
   "I": "Italic",
   "O": "Oblique",
   "RI": "Reverse Italic",
   "RO": "Reverse Oblique",
   "OT": "Other"
}

bdf_spacing = {
    "P": "Proportional",
    "M": "Monospaced",
    "C": "Cell"
}

def bdf_char(f):

    # skip to STARTCHAR
    while True:
        s = f.readline()
        if not s:
            return None
        if s[:9] == b"STARTCHAR":
            break
    id = s[9:].strip().decode('ascii')

    # load symbol properties
    props = {}
    while True:
        s = f.readline()
        if not s or s[:6] == b"BITMAP":
            break
        i = s.find(b" ")
        props[s[:i].decode('ascii')] = s[i+1:-1].decode('ascii')

    # load bitmap
    bitmap = []
    while True:
        s = f.readline()
        if not s or s[:7] == b"ENDCHAR":
            break
        bitmap.append(s[:-1])
    bitmap = b"".join(bitmap)

    [x, y, l, d] = [int(s) for s in props["BBX"].split()]
    [dx, dy] = [int(s) for s in props["DWIDTH"].split()]

    bbox = (dx, dy), (l, -d-y, x+l, -d), (0, 0, x, y)

    try:
        im = Image.frombytes("1", (x, y), bitmap, "hex", "1")
    except ValueError:
        # deal with zero-width characters
        im = Image.new("1", (x, y))

    return id, int(props["ENCODING"]), bbox, im

##
# Font file plugin for the X11 BDF format.

class BdfFontFile(FontFile.FontFile):

    def __init__(self, fp):

        FontFile.FontFile.__init__(self)

        s = fp.readline()
        if s[:13] != b"STARTFONT 2.1":
            raise SyntaxError("not a valid BDF file")

        props = {}
        comments = []

        while True:
            s = fp.readline()
            if not s or s[:13] == b"ENDPROPERTIES":
                break
            i = s.find(b" ")
            props[s[:i].decode('ascii')] = s[i+1:-1].decode('ascii')
            if s[:i] in [b"COMMENT", b"COPYRIGHT"]:
                if s.find(b"LogicalFontDescription") < 0:
                    comments.append(s[i+1:-1].decode('ascii'))

        font = props["FONT"].split("-")

        font[4] = bdf_slant[font[4].upper()]
        font[11] = bdf_spacing[font[11].upper()]

        ascent = int(props["FONT_ASCENT"])
        descent = int(props["FONT_DESCENT"])

        fontname = ";".join(font[1:])

        # print "#", fontname
        # for i in comments:
        #       print "#", i

        font = []
        while True:
            c = bdf_char(fp)
            if not c:
                break
            id, ch, (xy, dst, src), im = c
            if ch >= 0 and ch < len(self.glyph):
                self.glyph[ch] = xy, dst, src, im

########NEW FILE########
__FILENAME__ = BmpImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# BMP file handler
#
# Windows (and OS/2) native bitmap storage format.
#
# history:
# 1995-09-01 fl   Created
# 1996-04-30 fl   Added save
# 1997-08-27 fl   Fixed save of 1-bit images
# 1998-03-06 fl   Load P images as L where possible
# 1998-07-03 fl   Load P images as 1 where possible
# 1998-12-29 fl   Handle small palettes
# 2002-12-30 fl   Fixed load of 1-bit palette images
# 2003-04-21 fl   Fixed load of 1-bit monochrome images
# 2003-04-23 fl   Added limited support for BI_BITFIELDS compression
#
# Copyright (c) 1997-2003 by Secret Labs AB
# Copyright (c) 1995-2003 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#


__version__ = "0.7"


from PIL import Image, ImageFile, ImagePalette, _binary

i8 = _binary.i8
i16 = _binary.i16le
i32 = _binary.i32le
o8 = _binary.o8
o16 = _binary.o16le
o32 = _binary.o32le

#
# --------------------------------------------------------------------
# Read BMP file

BIT2MODE = {
    # bits => mode, rawmode
    1: ("P", "P;1"),
    4: ("P", "P;4"),
    8: ("P", "P"),
    16: ("RGB", "BGR;15"),
    24: ("RGB", "BGR"),
    32: ("RGB", "BGRX")
}

def _accept(prefix):
    return prefix[:2] == b"BM"

##
# Image plugin for the Windows BMP format.

class BmpImageFile(ImageFile.ImageFile):

    format = "BMP"
    format_description = "Windows Bitmap"

    def _bitmap(self, header = 0, offset = 0):

        if header:
            self.fp.seek(header)

        read = self.fp.read

        # CORE/INFO
        s = read(4)
        s = s + ImageFile._safe_read(self.fp, i32(s)-4)

        if len(s) == 12:

            # OS/2 1.0 CORE
            bits = i16(s[10:])
            self.size = i16(s[4:]), i16(s[6:])
            compression = 0
            lutsize = 3
            colors = 0
            direction = -1

        elif len(s) in [40, 64, 108, 124]:

            # WIN 3.1 or OS/2 2.0 INFO
            bits = i16(s[14:])
            self.size = i32(s[4:]), i32(s[8:])
            compression = i32(s[16:])
            lutsize = 4
            colors = i32(s[32:])
            direction = -1
            if i8(s[11]) == 0xff:
                # upside-down storage
                self.size = self.size[0], 2**32 - self.size[1]
                direction = 0

        else:
            raise IOError("Unsupported BMP header type (%d)" % len(s))

        if (self.size[0]*self.size[1]) > 2**31:
            # Prevent DOS for > 2gb images
            raise IOError("Unsupported BMP Size: (%dx%d)" % self.size)

        if not colors:
            colors = 1 << bits

        # MODE
        try:
            self.mode, rawmode = BIT2MODE[bits]
        except KeyError:
            raise IOError("Unsupported BMP pixel depth (%d)" % bits)

        if compression == 3:
            # BI_BITFIELDS compression
            mask = i32(read(4)), i32(read(4)), i32(read(4))
            if bits == 32 and mask == (0xff0000, 0x00ff00, 0x0000ff):
                rawmode = "BGRX"
            elif bits == 16 and mask == (0x00f800, 0x0007e0, 0x00001f):
                rawmode = "BGR;16"
            elif bits == 16 and mask == (0x007c00, 0x0003e0, 0x00001f):
                rawmode = "BGR;15"
            else:
                # print bits, map(hex, mask)
                raise IOError("Unsupported BMP bitfields layout")
        elif compression != 0:
            raise IOError("Unsupported BMP compression (%d)" % compression)

        # LUT
        if self.mode == "P":
            palette = []
            greyscale = 1
            if colors == 2:
                indices = (0, 255)
            elif colors > 2**16 or colors <=0: #We're reading a i32. 
                raise IOError("Unsupported BMP Palette size (%d)" % colors)
            else:
                indices = list(range(colors))
            for i in indices:
                rgb = read(lutsize)[:3]
                if rgb != o8(i)*3:
                    greyscale = 0
                palette.append(rgb)
            if greyscale:
                if colors == 2:
                    self.mode = rawmode = "1"
                else:
                    self.mode = rawmode = "L"
            else:
                self.mode = "P"
                self.palette = ImagePalette.raw(
                    "BGR", b"".join(palette)
                    )

        if not offset:
            offset = self.fp.tell()

        self.tile = [("raw",
                     (0, 0) + self.size,
                     offset,
                     (rawmode, ((self.size[0]*bits+31)>>3)&(~3), direction))]

        self.info["compression"] = compression

    def _open(self):

        # HEAD
        s = self.fp.read(14)
        if s[:2] != b"BM":
            raise SyntaxError("Not a BMP file")
        offset = i32(s[10:])

        self._bitmap(offset=offset)


class DibImageFile(BmpImageFile):

    format = "DIB"
    format_description = "Windows Bitmap"

    def _open(self):
        self._bitmap()

#
# --------------------------------------------------------------------
# Write BMP file

SAVE = {
    "1": ("1", 1, 2),
    "L": ("L", 8, 256),
    "P": ("P", 8, 256),
    "RGB": ("BGR", 24, 0),
}

def _save(im, fp, filename, check=0):

    try:
        rawmode, bits, colors = SAVE[im.mode]
    except KeyError:
        raise IOError("cannot write mode %s as BMP" % im.mode)

    if check:
        return check

    stride = ((im.size[0]*bits+7)//8+3)&(~3)
    header = 40 # or 64 for OS/2 version 2
    offset = 14 + header + colors * 4
    image  = stride * im.size[1]

    # bitmap header
    fp.write(b"BM" +                    # file type (magic)
             o32(offset+image) +        # file size
             o32(0) +                   # reserved
             o32(offset))               # image data offset

    # bitmap info header
    fp.write(o32(header) +              # info header size
             o32(im.size[0]) +          # width
             o32(im.size[1]) +          # height
             o16(1) +                   # planes
             o16(bits) +                # depth
             o32(0) +                   # compression (0=uncompressed)
             o32(image) +               # size of bitmap
             o32(1) + o32(1) +          # resolution
             o32(colors) +              # colors used
             o32(colors))               # colors important

    fp.write(b"\0" * (header - 40))    # padding (for OS/2 format)

    if im.mode == "1":
        for i in (0, 255):
            fp.write(o8(i) * 4)
    elif im.mode == "L":
        for i in range(256):
            fp.write(o8(i) * 4)
    elif im.mode == "P":
        fp.write(im.im.getpalette("RGB", "BGRX"))

    ImageFile._save(im, fp, [("raw", (0,0)+im.size, 0, (rawmode, stride, -1))])

#
# --------------------------------------------------------------------
# Registry

Image.register_open(BmpImageFile.format, BmpImageFile, _accept)
Image.register_save(BmpImageFile.format, _save)

Image.register_extension(BmpImageFile.format, ".bmp")

########NEW FILE########
__FILENAME__ = BufrStubImagePlugin
#
# The Python Imaging Library
# $Id$
#
# BUFR stub adapter
#
# Copyright (c) 1996-2003 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

from PIL import Image, ImageFile

_handler = None

##
# Install application-specific BUFR image handler.
#
# @param handler Handler object.

def register_handler(handler):
    global _handler
    _handler = handler

# --------------------------------------------------------------------
# Image adapter

def _accept(prefix):
    return prefix[:4] == b"BUFR" or prefix[:4] == b"ZCZC"

class BufrStubImageFile(ImageFile.StubImageFile):

    format = "BUFR"
    format_description = "BUFR"

    def _open(self):

        offset = self.fp.tell()

        if not _accept(self.fp.read(8)):
            raise SyntaxError("Not a BUFR file")

        self.fp.seek(offset)

        # make something up
        self.mode = "F"
        self.size = 1, 1

        loader = self._load()
        if loader:
            loader.open(self)

    def _load(self):
        return _handler

def _save(im, fp, filename):
    if _handler is None or not hasattr("_handler", "save"):
        raise IOError("BUFR save handler not installed")
    _handler.save(im, fp, filename)


# --------------------------------------------------------------------
# Registry

Image.register_open(BufrStubImageFile.format, BufrStubImageFile, _accept)
Image.register_save(BufrStubImageFile.format, _save)

Image.register_extension(BufrStubImageFile.format, ".bufr")

########NEW FILE########
__FILENAME__ = ContainerIO
#
# The Python Imaging Library.
# $Id$
#
# a class to read from a container file
#
# History:
# 1995-06-18 fl     Created
# 1995-09-07 fl     Added readline(), readlines()
#
# Copyright (c) 1997-2001 by Secret Labs AB
# Copyright (c) 1995 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

##
# A file object that provides read access to a part of an existing
# file (for example a TAR file).

class ContainerIO:

    ##
    # Create file object.
    #
    # @param file Existing file.
    # @param offset Start of region, in bytes.
    # @param length Size of region, in bytes.

    def __init__(self, file, offset, length):
        self.fh = file
        self.pos = 0
        self.offset = offset
        self.length = length
        self.fh.seek(offset)

    ##
    # Always false.

    def isatty(self):
        return 0

    ##
    # Move file pointer.
    #
    # @param offset Offset in bytes.
    # @param mode Starting position. Use 0 for beginning of region, 1
    #    for current offset, and 2 for end of region.  You cannot move
    #    the pointer outside the defined region.

    def seek(self, offset, mode = 0):
        if mode == 1:
            self.pos = self.pos + offset
        elif mode == 2:
            self.pos = self.length + offset
        else:
            self.pos = offset
        # clamp
        self.pos = max(0, min(self.pos, self.length))
        self.fh.seek(self.offset + self.pos)

    ##
    # Get current file pointer.
    #
    # @return Offset from start of region, in bytes.

    def tell(self):
        return self.pos

    ##
    # Read data.
    #
    # @def read(bytes=0)
    # @param bytes Number of bytes to read.  If omitted or zero,
    #     read until end of region.
    # @return An 8-bit string.

    def read(self, n = 0):
        if n:
            n = min(n, self.length - self.pos)
        else:
            n = self.length - self.pos
        if not n: # EOF
            return ""
        self.pos = self.pos + n
        return self.fh.read(n)

    ##
    # Read a line of text.
    #
    # @return An 8-bit string.

    def readline(self):
        s = ""
        while True:
            c = self.read(1)
            if not c:
                break
            s = s + c
            if c == "\n":
                break
        return s

    ##
    # Read multiple lines of text.
    #
    # @return A list of 8-bit strings.

    def readlines(self):
        l = []
        while True:
            s = self.readline()
            if not s:
                break
            l.append(s)
        return l

########NEW FILE########
__FILENAME__ = CurImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# Windows Cursor support for PIL
#
# notes:
#       uses BmpImagePlugin.py to read the bitmap data.
#
# history:
#       96-05-27 fl     Created
#
# Copyright (c) Secret Labs AB 1997.
# Copyright (c) Fredrik Lundh 1996.
#
# See the README file for information on usage and redistribution.
#


__version__ = "0.1"

from PIL import Image, BmpImagePlugin, _binary


#
# --------------------------------------------------------------------

i8 = _binary.i8
i16 = _binary.i16le
i32 = _binary.i32le


def _accept(prefix):
    return prefix[:4] == b"\0\0\2\0"

##
# Image plugin for Windows Cursor files.

class CurImageFile(BmpImagePlugin.BmpImageFile):

    format = "CUR"
    format_description = "Windows Cursor"

    def _open(self):

        offset = self.fp.tell()

        # check magic
        s = self.fp.read(6)
        if not _accept(s):
            raise SyntaxError("not an CUR file")

        # pick the largest cursor in the file
        m = b""
        for i in range(i16(s[4:])):
            s = self.fp.read(16)
            if not m:
                m = s
            elif i8(s[0]) > i8(m[0]) and i8(s[1]) > i8(m[1]):
                m = s
            #print "width", i8(s[0])
            #print "height", i8(s[1])
            #print "colors", i8(s[2])
            #print "reserved", i8(s[3])
            #print "hotspot x", i16(s[4:])
            #print "hotspot y", i16(s[6:])
            #print "bytes", i32(s[8:])
            #print "offset", i32(s[12:])

        # load as bitmap
        self._bitmap(i32(m[12:]) + offset)

        # patch up the bitmap height
        self.size = self.size[0], self.size[1]//2
        d, e, o, a = self.tile[0]
        self.tile[0] = d, (0,0)+self.size, o, a

        return


#
# --------------------------------------------------------------------

Image.register_open("CUR", CurImageFile, _accept)

Image.register_extension("CUR", ".cur")

########NEW FILE########
__FILENAME__ = DcxImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# DCX file handling
#
# DCX is a container file format defined by Intel, commonly used
# for fax applications.  Each DCX file consists of a directory
# (a list of file offsets) followed by a set of (usually 1-bit)
# PCX files.
#
# History:
# 1995-09-09 fl   Created
# 1996-03-20 fl   Properly derived from PcxImageFile.
# 1998-07-15 fl   Renamed offset attribute to avoid name clash
# 2002-07-30 fl   Fixed file handling
#
# Copyright (c) 1997-98 by Secret Labs AB.
# Copyright (c) 1995-96 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#

__version__ = "0.2"

from PIL import Image, _binary

from PIL.PcxImagePlugin import PcxImageFile

MAGIC = 0x3ADE68B1 # QUIZ: what's this value, then?

i32 = _binary.i32le

def _accept(prefix):
    return i32(prefix) == MAGIC

##
# Image plugin for the Intel DCX format.

class DcxImageFile(PcxImageFile):

    format = "DCX"
    format_description = "Intel DCX"

    def _open(self):

        # Header
        s = self.fp.read(4)
        if i32(s) != MAGIC:
            raise SyntaxError("not a DCX file")

        # Component directory
        self._offset = []
        for i in range(1024):
            offset = i32(self.fp.read(4))
            if not offset:
                break
            self._offset.append(offset)

        self.__fp = self.fp
        self.seek(0)

    def seek(self, frame):
        if frame >= len(self._offset):
            raise EOFError("attempt to seek outside DCX directory")
        self.frame = frame
        self.fp = self.__fp
        self.fp.seek(self._offset[frame])
        PcxImageFile._open(self)

    def tell(self):
        return self.frame


Image.register_open("DCX", DcxImageFile, _accept)

Image.register_extension("DCX", ".dcx")

########NEW FILE########
__FILENAME__ = EpsImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# EPS file handling
#
# History:
# 1995-09-01 fl   Created (0.1)
# 1996-05-18 fl   Don't choke on "atend" fields, Ghostscript interface (0.2)
# 1996-08-22 fl   Don't choke on floating point BoundingBox values
# 1996-08-23 fl   Handle files from Macintosh (0.3)
# 2001-02-17 fl   Use 're' instead of 'regex' (Python 2.1) (0.4)
# 2003-09-07 fl   Check gs.close status (from Federico Di Gregorio) (0.5)
# 2014-05-07 e    Handling of EPS with binary preview and fixed resolution resizing
#
# Copyright (c) 1997-2003 by Secret Labs AB.
# Copyright (c) 1995-2003 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

__version__ = "0.5"

import re
import io
from PIL import Image, ImageFile, _binary

#
# --------------------------------------------------------------------

i32 = _binary.i32le
o32 = _binary.o32le

split = re.compile(r"^%%([^:]*):[ \t]*(.*)[ \t]*$")
field = re.compile(r"^%[%!\w]([^:]*)[ \t]*$")

gs_windows_binary = None
import sys
if sys.platform.startswith('win'):
    import shutil
    if hasattr(shutil, 'which'):
        which = shutil.which
    else:
        # Python < 3.3
        import distutils.spawn
        which = distutils.spawn.find_executable
    for binary in ('gswin32c', 'gswin64c', 'gs'):
        if which(binary) is not None:
            gs_windows_binary = binary
            break
    else:
        gs_windows_binary = False

def has_ghostscript():
    if gs_windows_binary:
        return True
    if not sys.platform.startswith('win'):
        import subprocess
        try:
            gs = subprocess.Popen(['gs','--version'], stdout=subprocess.PIPE)
            gs.stdout.read()
            return True
        except OSError:
            # no ghostscript
            pass
    return False
   

def Ghostscript(tile, size, fp, scale=1):
    """Render an image using Ghostscript"""

    # Unpack decoder tile
    decoder, tile, offset, data = tile[0]
    length, bbox = data
   
    #Hack to support hi-res rendering
    scale = int(scale) or 1
    orig_size = size
    orig_bbox = bbox
    size = (size[0] * scale, size[1] * scale)
    # resolution is dependend on bbox and size
    res = ( float((72.0 * size[0]) / (bbox[2]-bbox[0])), float((72.0 * size[1]) / (bbox[3]-bbox[1])) )
    #print("Ghostscript", scale, size, orig_size, bbox, orig_bbox, res)

    import tempfile, os, subprocess

    out_fd, outfile = tempfile.mkstemp()
    os.close(out_fd)
    in_fd, infile = tempfile.mkstemp()
    os.close(in_fd)
    
    # ignore length and offset!
    # ghostscript can read it   
    # copy whole file to read in ghostscript
    with open(infile, 'wb') as f:
        # fetch length of fp
        fp.seek(0, 2)
        fsize = fp.tell()
        # ensure start position
        # go back
        fp.seek(0)
        lengthfile = fsize
        while lengthfile > 0:
            s = fp.read(min(lengthfile, 100*1024))
            if not s:
                break
            lengthfile = lengthfile - len(s)
            f.write(s)

    # Build ghostscript command
    command = ["gs",
               "-q",                        # quiet mode
               "-g%dx%d" % size,            # set output geometry (pixels)
               "-r%fx%f" % res,             # set input DPI (dots per inch)
               "-dNOPAUSE -dSAFER",         # don't pause between pages, safe mode
               "-sDEVICE=ppmraw",           # ppm driver
               "-sOutputFile=%s" % outfile, # output file
               "-c", "%d %d translate" % (-bbox[0], -bbox[1]),
                                            # adjust for image origin
               "-f", infile,                # input file
            ]
    
    if gs_windows_binary is not None:
        if not gs_windows_binary:
            raise WindowsError('Unable to locate Ghostscript on paths')
        command[0] = gs_windows_binary

    # push data through ghostscript
    try:
        gs = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        gs.stdin.close()
        status = gs.wait()
        if status:
            raise IOError("gs failed (status %d)" % status)
        im = Image.core.open_ppm(outfile)
    finally:
        try:
            os.unlink(outfile)
            os.unlink(infile)
        except: pass
    
    return im


class PSFile:
    """Wrapper that treats either CR or LF as end of line."""
    def __init__(self, fp):
        self.fp = fp
        self.char = None
    def __getattr__(self, id):
        v = getattr(self.fp, id)
        setattr(self, id, v)
        return v
    def seek(self, offset, whence=0):
        self.char = None
        self.fp.seek(offset, whence)
    def read(self, count):
        return self.fp.read(count).decode('latin-1')
    def readbinary(self, count):
        return self.fp.read(count)
    def tell(self):
        pos = self.fp.tell()
        if self.char:
            pos = pos - 1
        return pos
    def readline(self):
        s = b""
        if self.char:
            c = self.char
            self.char = None
        else:
            c = self.fp.read(1)
        while c not in b"\r\n":
            s = s + c
            c = self.fp.read(1)
        if c == b"\r":
            self.char = self.fp.read(1)
            if self.char == b"\n":
                self.char = None
        return s.decode('latin-1') + "\n"


def _accept(prefix):
    return prefix[:4] == b"%!PS" or i32(prefix) == 0xC6D3D0C5

##
# Image plugin for Encapsulated Postscript.  This plugin supports only
# a few variants of this format.

class EpsImageFile(ImageFile.ImageFile):
    """EPS File Parser for the Python Imaging Library"""

    format = "EPS"
    format_description = "Encapsulated Postscript"

    def _open(self):

        fp = PSFile(self.fp)

        # FIX for: Some EPS file not handled correctly / issue #302 
        # EPS can contain binary data
        # or start directly with latin coding
        # read header in both ways to handle both
        # file types
        # more info see http://partners.adobe.com/public/developer/en/ps/5002.EPSF_Spec.pdf
        
        # for HEAD without binary preview
        s = fp.read(4)
        # for HEAD with binary preview
        fp.seek(0)
        sb = fp.readbinary(160)

        if s[:4] == "%!PS":
            fp.seek(0, 2)
            length = fp.tell()
            offset = 0
        elif i32(sb[0:4]) == 0xC6D3D0C5:
            offset = i32(sb[4:8])
            length = i32(sb[8:12])
        else:
            raise SyntaxError("not an EPS file")

        # go to offset - start of "%!PS" 
        fp.seek(offset)
        
        box = None

        self.mode = "RGB"
        self.size = 1, 1 # FIXME: huh?

        #
        # Load EPS header

        s = fp.readline()
        
        while s:

            if len(s) > 255:
                raise SyntaxError("not an EPS file")

            if s[-2:] == '\r\n':
                s = s[:-2]
            elif s[-1:] == '\n':
                s = s[:-1]

            try:
                m = split.match(s)
            except re.error as v:
                raise SyntaxError("not an EPS file")

            if m:
                k, v = m.group(1, 2)
                self.info[k] = v
                if k == "BoundingBox":
                    try:
                        # Note: The DSC spec says that BoundingBox
                        # fields should be integers, but some drivers
                        # put floating point values there anyway.
                        box = [int(float(s)) for s in v.split()]
                        self.size = box[2] - box[0], box[3] - box[1]
                        self.tile = [("eps", (0,0) + self.size, offset,
                                      (length, box))]
                    except:
                        pass

            else:

                m = field.match(s)

                if m:
                    k = m.group(1)

                    if k == "EndComments":
                        break
                    if k[:8] == "PS-Adobe":
                        self.info[k[:8]] = k[9:]
                    else:
                        self.info[k] = ""
                elif s[0:1] == '%':
                    # handle non-DSC Postscript comments that some
                    # tools mistakenly put in the Comments section
                    pass
                else:
                    raise IOError("bad EPS header")

            s = fp.readline()

            if s[:1] != "%":
                break


        #
        # Scan for an "ImageData" descriptor

        while s[0] == "%":

            if len(s) > 255:
                raise SyntaxError("not an EPS file")

            if s[-2:] == '\r\n':
                s = s[:-2]
            elif s[-1:] == '\n':
                s = s[:-1]

            if s[:11] == "%ImageData:":

                [x, y, bi, mo, z3, z4, en, id] =\
                    s[11:].split(None, 7)

                x = int(x); y = int(y)

                bi = int(bi)
                mo = int(mo)

                en = int(en)

                if en == 1:
                    decoder = "eps_binary"
                elif en == 2:
                    decoder = "eps_hex"
                else:
                    break
                if bi != 8:
                    break
                if mo == 1:
                    self.mode = "L"
                elif mo == 2:
                    self.mode = "LAB"
                elif mo == 3:
                    self.mode = "RGB"
                else:
                    break

                if id[:1] == id[-1:] == '"':
                    id = id[1:-1]

                # Scan forward to the actual image data
                while True:
                    s = fp.readline()
                    if not s:
                        break
                    if s[:len(id)] == id:
                        self.size = x, y
                        self.tile2 = [(decoder,
                                       (0, 0, x, y),
                                       fp.tell(),
                                       0)]
                        return

            s = fp.readline()
            if not s:
                break

        if not box:
            raise IOError("cannot determine EPS bounding box")

    def load(self, scale=1):
        # Load EPS via Ghostscript
        if not self.tile:
            return
        self.im = Ghostscript(self.tile, self.size, self.fp, scale)
        self.mode = self.im.mode
        self.size = self.im.size
        self.tile = []

    def load_seek(self,*args,**kwargs):
        # we can't incrementally load, so force ImageFile.parser to
        # use our custom load method by defining this method. 
        pass

#
# --------------------------------------------------------------------

def _save(im, fp, filename, eps=1):
    """EPS Writer for the Python Imaging Library."""

    #
    # make sure image data is available
    im.load()

    #
    # determine postscript image mode
    if im.mode == "L":
        operator = (8, 1, "image")
    elif im.mode == "RGB":
        operator = (8, 3, "false 3 colorimage")
    elif im.mode == "CMYK":
        operator = (8, 4, "false 4 colorimage")
    else:
        raise ValueError("image mode is not supported")

    class NoCloseStream:
        def __init__(self, fp):
            self.fp = fp
        def __getattr__(self, name):
            return getattr(self.fp, name)
        def close(self):
            pass

    base_fp = fp
    fp = NoCloseStream(fp)
    if sys.version_info[0] > 2:
        fp = io.TextIOWrapper(fp, encoding='latin-1')

    if eps:
        #
        # write EPS header
        fp.write("%!PS-Adobe-3.0 EPSF-3.0\n")
        fp.write("%%Creator: PIL 0.1 EpsEncode\n")
        #fp.write("%%CreationDate: %s"...)
        fp.write("%%%%BoundingBox: 0 0 %d %d\n" % im.size)
        fp.write("%%Pages: 1\n")
        fp.write("%%EndComments\n")
        fp.write("%%Page: 1 1\n")
        fp.write("%%ImageData: %d %d " % im.size)
        fp.write("%d %d 0 1 1 \"%s\"\n" % operator)

    #
    # image header
    fp.write("gsave\n")
    fp.write("10 dict begin\n")
    fp.write("/buf %d string def\n" % (im.size[0] * operator[1]))
    fp.write("%d %d scale\n" % im.size)
    fp.write("%d %d 8\n" % im.size) # <= bits
    fp.write("[%d 0 0 -%d 0 %d]\n" % (im.size[0], im.size[1], im.size[1]))
    fp.write("{ currentfile buf readhexstring pop } bind\n")
    fp.write(operator[2] + "\n")
    fp.flush()

    ImageFile._save(im, base_fp, [("eps", (0,0)+im.size, 0, None)])

    fp.write("\n%%%%EndBinary\n")
    fp.write("grestore end\n")
    fp.flush()

#
# --------------------------------------------------------------------

Image.register_open(EpsImageFile.format, EpsImageFile, _accept)

Image.register_save(EpsImageFile.format, _save)

Image.register_extension(EpsImageFile.format, ".ps")
Image.register_extension(EpsImageFile.format, ".eps")

Image.register_mime(EpsImageFile.format, "application/postscript")

########NEW FILE########
__FILENAME__ = ExifTags
#
# The Python Imaging Library.
# $Id$
#
# EXIF tags
#
# Copyright (c) 2003 by Secret Labs AB
#
# See the README file for information on usage and redistribution.
#

##
# This module provides constants and clear-text names for various
# well-known EXIF tags.
##

##
# Maps EXIF tags to tag names.

TAGS = {

    # possibly incomplete
    0x00fe: "NewSubfileType",
    0x00ff: "SubfileType",
    0x0100: "ImageWidth",
    0x0101: "ImageLength",
    0x0102: "BitsPerSample",
    0x0103: "Compression",
    0x0106: "PhotometricInterpretation",
    0x0107: "Threshholding",
    0x0108: "CellWidth",
    0x0109: "CellLenght",
    0x010a: "FillOrder",
    0x010d: "DocumentName",
    0x011d: "PageName",
    0x010e: "ImageDescription",
    0x010f: "Make",
    0x0110: "Model",
    0x0111: "StripOffsets",
    0x0112: "Orientation",
    0x0115: "SamplesPerPixel",
    0x0116: "RowsPerStrip",
    0x0117: "StripByteConunts",
    0x0118: "MinSampleValue",
    0x0119: "MaxSampleValue",
    0x011a: "XResolution",
    0x011b: "YResolution",
    0x011c: "PlanarConfiguration",
    0x0120: "FreeOffsets",
    0x0121: "FreeByteCounts",
    0x0122: "GrayResponseUnit",
    0x0123: "GrayResponseCurve",
    0x0128: "ResolutionUnit",
    0x012d: "TransferFunction",
    0x0131: "Software",
    0x0132: "DateTime",
    0x013b: "Artist",
    0x013c: "HostComputer",
    0x013e: "WhitePoint",
    0x013f: "PrimaryChromaticities",
    0x0140: "ColorMap",
    0x0152: "ExtraSamples",
    0x0201: "JpegIFOffset",
    0x0202: "JpegIFByteCount",
    0x0211: "YCbCrCoefficients",
    0x0211: "YCbCrCoefficients",
    0x0212: "YCbCrSubSampling",
    0x0213: "YCbCrPositioning",
    0x0213: "YCbCrPositioning",
    0x0214: "ReferenceBlackWhite",
    0x0214: "ReferenceBlackWhite",
    0x1000: "RelatedImageFileFormat",
    0x1001: "RelatedImageLength",
    0x1001: "RelatedImageWidth",
    0x828d: "CFARepeatPatternDim",
    0x828e: "CFAPattern",
    0x828f: "BatteryLevel",
    0x8298: "Copyright",
    0x829a: "ExposureTime",
    0x829d: "FNumber",
    0x8769: "ExifOffset",
    0x8773: "InterColorProfile",
    0x8822: "ExposureProgram",
    0x8824: "SpectralSensitivity",
    0x8825: "GPSInfo",
    0x8827: "ISOSpeedRatings",
    0x8828: "OECF",
    0x8829: "Interlace",
    0x882a: "TimeZoneOffset",
    0x882b: "SelfTimerMode",
    0x9000: "ExifVersion",
    0x9003: "DateTimeOriginal",
    0x9004: "DateTimeDigitized",
    0x9101: "ComponentsConfiguration",
    0x9102: "CompressedBitsPerPixel",
    0x9201: "ShutterSpeedValue",
    0x9202: "ApertureValue",
    0x9203: "BrightnessValue",
    0x9204: "ExposureBiasValue",
    0x9205: "MaxApertureValue",
    0x9206: "SubjectDistance",
    0x9207: "MeteringMode",
    0x9208: "LightSource",
    0x9209: "Flash",
    0x920a: "FocalLength",
    0x920b: "FlashEnergy",
    0x920c: "SpatialFrequencyResponse",
    0x920d: "Noise",
    0x9211: "ImageNumber",
    0x9212: "SecurityClassification",
    0x9213: "ImageHistory",
    0x9214: "SubjectLocation",
    0x9215: "ExposureIndex",
    0x9216: "TIFF/EPStandardID",
    0x927c: "MakerNote",
    0x9286: "UserComment",
    0x9290: "SubsecTime",
    0x9291: "SubsecTimeOriginal",
    0x9292: "SubsecTimeDigitized",
    0xa000: "FlashPixVersion",
    0xa001: "ColorSpace",
    0xa002: "ExifImageWidth",
    0xa003: "ExifImageHeight",
    0xa004: "RelatedSoundFile",
    0xa005: "ExifInteroperabilityOffset",
    0xa20b: "FlashEnergy",
    0xa20c: "SpatialFrequencyResponse",
    0xa20e: "FocalPlaneXResolution",
    0xa20f: "FocalPlaneYResolution",
    0xa210: "FocalPlaneResolutionUnit",
    0xa214: "SubjectLocation",
    0xa215: "ExposureIndex",
    0xa217: "SensingMethod",
    0xa300: "FileSource",
    0xa301: "SceneType",
    0xa302: "CFAPattern",
    0xa401: "CustomRendered",
    0xa402: "ExposureMode",
    0xa403: "WhiteBalance",
    0xa404: "DigitalZoomRatio",
    0xa405: "FocalLengthIn35mmFilm",
    0xa406: "SceneCaptureType",
    0xa407: "GainControl",
    0xa408: "Contrast",
    0xa409: "Saturation",
    0xa40a: "Sharpness",
    0xa40b: "DeviceSettingDescription",
    0xa40c: "SubjectDistanceRange",
    0xa420: "ImageUniqueID",
    0xa430: "CameraOwnerName",
    0xa431: "BodySerialNumber",
    0xa432: "LensSpecification",
    0xa433: "LensMake",
    0xa434: "LensModel",
    0xa435: "LensSerialNumber",
    0xa500: "Gamma",

}

##
# Maps EXIF GPS tags to tag names.

GPSTAGS = {
    0: "GPSVersionID",
    1: "GPSLatitudeRef",
    2: "GPSLatitude",
    3: "GPSLongitudeRef",
    4: "GPSLongitude",
    5: "GPSAltitudeRef",
    6: "GPSAltitude",
    7: "GPSTimeStamp",
    8: "GPSSatellites",
    9: "GPSStatus",
    10: "GPSMeasureMode",
    11: "GPSDOP",
    12: "GPSSpeedRef",
    13: "GPSSpeed",
    14: "GPSTrackRef",
    15: "GPSTrack",
    16: "GPSImgDirectionRef",
    17: "GPSImgDirection",
    18: "GPSMapDatum",
    19: "GPSDestLatitudeRef",
    20: "GPSDestLatitude",
    21: "GPSDestLongitudeRef",
    22: "GPSDestLongitude",
    23: "GPSDestBearingRef",
    24: "GPSDestBearing",
    25: "GPSDestDistanceRef",
    26: "GPSDestDistance",
    27: "GPSProcessingMethod",
    28: "GPSAreaInformation",
    29: "GPSDateStamp",
    30: "GPSDifferential",
    31: "GPSHPositioningError",
}

########NEW FILE########
__FILENAME__ = FitsStubImagePlugin
#
# The Python Imaging Library
# $Id$
#
# FITS stub adapter
#
# Copyright (c) 1998-2003 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

from PIL import Image, ImageFile

_handler = None

##
# Install application-specific FITS image handler.
#
# @param handler Handler object.

def register_handler(handler):
    global _handler
    _handler = handler

# --------------------------------------------------------------------
# Image adapter

def _accept(prefix):
    return prefix[:6] == b"SIMPLE"

class FITSStubImageFile(ImageFile.StubImageFile):

    format = "FITS"
    format_description = "FITS"

    def _open(self):

        offset = self.fp.tell()

        if not _accept(self.fp.read(6)):
            raise SyntaxError("Not a FITS file")

        # FIXME: add more sanity checks here; mandatory header items
        # include SIMPLE, BITPIX, NAXIS, etc.

        self.fp.seek(offset)

        # make something up
        self.mode = "F"
        self.size = 1, 1

        loader = self._load()
        if loader:
            loader.open(self)

    def _load(self):
        return _handler


def _save(im, fp, filename):
    if _handler is None or not hasattr("_handler", "save"):
        raise IOError("FITS save handler not installed")
    _handler.save(im, fp, filename)


# --------------------------------------------------------------------
# Registry

Image.register_open(FITSStubImageFile.format, FITSStubImageFile, _accept)
Image.register_save(FITSStubImageFile.format, _save)

Image.register_extension(FITSStubImageFile.format, ".fit")
Image.register_extension(FITSStubImageFile.format, ".fits")

########NEW FILE########
__FILENAME__ = FliImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# FLI/FLC file handling.
#
# History:
#       95-09-01 fl     Created
#       97-01-03 fl     Fixed parser, setup decoder tile
#       98-07-15 fl     Renamed offset attribute to avoid name clash
#
# Copyright (c) Secret Labs AB 1997-98.
# Copyright (c) Fredrik Lundh 1995-97.
#
# See the README file for information on usage and redistribution.
#


__version__ = "0.2"

from PIL import Image, ImageFile, ImagePalette, _binary

i8 = _binary.i8
i16 = _binary.i16le
i32 = _binary.i32le
o8 = _binary.o8

#
# decoder

def _accept(prefix):
    return i16(prefix[4:6]) in [0xAF11, 0xAF12]

##
# Image plugin for the FLI/FLC animation format.  Use the <b>seek</b>
# method to load individual frames.

class FliImageFile(ImageFile.ImageFile):

    format = "FLI"
    format_description = "Autodesk FLI/FLC Animation"

    def _open(self):

        # HEAD
        s = self.fp.read(128)
        magic = i16(s[4:6])
        if not (magic in [0xAF11, 0xAF12] and
                i16(s[14:16]) in [0, 3] and  # flags
                s[20:22] == b"\x00\x00"): # reserved
            raise SyntaxError("not an FLI/FLC file")

        # image characteristics
        self.mode = "P"
        self.size = i16(s[8:10]), i16(s[10:12])

        # animation speed
        duration = i32(s[16:20])
        if magic == 0xAF11:
            duration = (duration * 1000) / 70
        self.info["duration"] = duration

        # look for palette
        palette = [(a,a,a) for a in range(256)]

        s = self.fp.read(16)

        self.__offset = 128

        if i16(s[4:6]) == 0xF100:
            # prefix chunk; ignore it
            self.__offset = self.__offset + i32(s)
            s = self.fp.read(16)

        if i16(s[4:6]) == 0xF1FA:
            # look for palette chunk
            s = self.fp.read(6)
            if i16(s[4:6]) == 11:
                self._palette(palette, 2)
            elif i16(s[4:6]) == 4:
                self._palette(palette, 0)

        palette = [o8(r)+o8(g)+o8(b) for (r,g,b) in palette]
        self.palette = ImagePalette.raw("RGB", b"".join(palette))

        # set things up to decode first frame
        self.frame = -1
        self.__fp = self.fp

        self.seek(0)

    def _palette(self, palette, shift):
        # load palette

        i = 0
        for e in range(i16(self.fp.read(2))):
            s = self.fp.read(2)
            i = i + i8(s[0])
            n = i8(s[1])
            if n == 0:
                n = 256
            s = self.fp.read(n * 3)
            for n in range(0, len(s), 3):
                r = i8(s[n]) << shift
                g = i8(s[n+1]) << shift
                b = i8(s[n+2]) << shift
                palette[i] = (r, g, b)
                i = i + 1

    def seek(self, frame):

        if frame != self.frame + 1:
            raise ValueError("cannot seek to frame %d" % frame)
        self.frame = frame

        # move to next frame
        self.fp = self.__fp
        self.fp.seek(self.__offset)

        s = self.fp.read(4)
        if not s:
            raise EOFError

        framesize = i32(s)

        self.decodermaxblock = framesize
        self.tile = [("fli", (0,0)+self.size, self.__offset, None)]

        self.__offset = self.__offset + framesize

    def tell(self):

        return self.frame

#
# registry

Image.register_open("FLI", FliImageFile, _accept)

Image.register_extension("FLI", ".fli")
Image.register_extension("FLI", ".flc")

########NEW FILE########
__FILENAME__ = FontFile
#
# The Python Imaging Library
# $Id$
#
# base class for raster font file parsers
#
# history:
# 1997-06-05 fl   created
# 1997-08-19 fl   restrict image width
#
# Copyright (c) 1997-1998 by Secret Labs AB
# Copyright (c) 1997-1998 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

import os
from PIL import Image, _binary

import marshal

try:
    import zlib
except ImportError:
    zlib = None

WIDTH = 800

def puti16(fp, values):
    # write network order (big-endian) 16-bit sequence
    for v in values:
        if v < 0:
            v = v + 65536
        fp.write(_binary.o16be(v))

##
# Base class for raster font file handlers.

class FontFile:

    bitmap = None

    def __init__(self):

        self.info = {}
        self.glyph = [None] * 256

    def __getitem__(self, ix):
        return self.glyph[ix]

    def compile(self):
        "Create metrics and bitmap"

        if self.bitmap:
            return

        # create bitmap large enough to hold all data
        h = w = maxwidth = 0
        lines = 1
        for glyph in self:
            if glyph:
                d, dst, src, im = glyph
                h = max(h, src[3] - src[1])
                w = w + (src[2] - src[0])
                if w > WIDTH:
                    lines = lines + 1
                    w = (src[2] - src[0])
                maxwidth = max(maxwidth, w)

        xsize = maxwidth
        ysize = lines * h

        if xsize == 0 and ysize == 0:
            return ""

        self.ysize = h

        # paste glyphs into bitmap
        self.bitmap = Image.new("1", (xsize, ysize))
        self.metrics = [None] * 256
        x = y = 0
        for i in range(256):
            glyph = self[i]
            if glyph:
                d, dst, src, im = glyph
                xx, yy = src[2] - src[0], src[3] - src[1]
                x0, y0 = x, y
                x = x + xx
                if x > WIDTH:
                    x, y = 0, y + h
                    x0, y0 = x, y
                    x = xx
                s = src[0] + x0, src[1] + y0, src[2] + x0, src[3] + y0
                self.bitmap.paste(im.crop(src), s)
                # print chr(i), dst, s
                self.metrics[i] = d, dst, s


    def save1(self, filename):
        "Save font in version 1 format"

        self.compile()

        # font data
        self.bitmap.save(os.path.splitext(filename)[0] + ".pbm", "PNG")

        # font metrics
        fp = open(os.path.splitext(filename)[0] + ".pil", "wb")
        fp.write(b"PILfont\n")
        fp.write((";;;;;;%d;\n" % self.ysize).encode('ascii')) # HACK!!!
        fp.write(b"DATA\n")
        for id in range(256):
            m = self.metrics[id]
            if not m:
                puti16(fp, [0] * 10)
            else:
                puti16(fp, m[0] + m[1] + m[2])
        fp.close()


    def save2(self, filename):
        "Save font in version 2 format"

        # THIS IS WORK IN PROGRESS

        self.compile()

        data = marshal.dumps((self.metrics, self.info))

        if zlib:
            data = b"z" + zlib.compress(data, 9)
        else:
            data = b"u" + data

        fp = open(os.path.splitext(filename)[0] + ".pil", "wb")

        fp.write(b"PILfont2\n" + self.name + "\n" + "DATA\n")

        fp.write(data)

        self.bitmap.save(fp, "PNG")

        fp.close()


    save = save1 # for now

########NEW FILE########
__FILENAME__ = FpxImagePlugin
#
# THIS IS WORK IN PROGRESS
#
# The Python Imaging Library.
# $Id$
#
# FlashPix support for PIL
#
# History:
# 97-01-25 fl   Created (reads uncompressed RGB images only)
#
# Copyright (c) Secret Labs AB 1997.
# Copyright (c) Fredrik Lundh 1997.
#
# See the README file for information on usage and redistribution.
#


__version__ = "0.1"


from PIL import Image, ImageFile
from PIL.OleFileIO import *


# we map from colour field tuples to (mode, rawmode) descriptors
MODES = {
    # opacity
    (0x00007ffe): ("A", "L"),
    # monochrome
    (0x00010000,): ("L", "L"),
    (0x00018000, 0x00017ffe): ("RGBA", "LA"),
    # photo YCC
    (0x00020000, 0x00020001, 0x00020002): ("RGB", "YCC;P"),
    (0x00028000, 0x00028001, 0x00028002, 0x00027ffe): ("RGBA", "YCCA;P"),
    # standard RGB (NIFRGB)
    (0x00030000, 0x00030001, 0x00030002): ("RGB","RGB"),
    (0x00038000, 0x00038001, 0x00038002, 0x00037ffe): ("RGBA","RGBA"),
}

#
# --------------------------------------------------------------------

def _accept(prefix):
    return prefix[:8] == MAGIC

##
# Image plugin for the FlashPix images.

class FpxImageFile(ImageFile.ImageFile):

    format = "FPX"
    format_description = "FlashPix"

    def _open(self):
        #
        # read the OLE directory and see if this is a likely
        # to be a FlashPix file

        try:
            self.ole = OleFileIO(self.fp)
        except IOError:
            raise SyntaxError("not an FPX file; invalid OLE file")

        if self.ole.root.clsid != "56616700-C154-11CE-8553-00AA00A1F95B":
            raise SyntaxError("not an FPX file; bad root CLSID")

        self._open_index(1)

    def _open_index(self, index = 1):
        #
        # get the Image Contents Property Set

        prop = self.ole.getproperties([
            "Data Object Store %06d" % index,
            "\005Image Contents"
        ])

        # size (highest resolution)

        self.size = prop[0x1000002], prop[0x1000003]

        size = max(self.size)
        i = 1
        while size > 64:
            size = size / 2
            i = i + 1
        self.maxid = i - 1

        # mode.  instead of using a single field for this, flashpix
        # requires you to specify the mode for each channel in each
        # resolution subimage, and leaves it to the decoder to make
        # sure that they all match.  for now, we'll cheat and assume
        # that this is always the case.

        id = self.maxid << 16

        s = prop[0x2000002|id]

        colors = []
        for i in range(i32(s, 4)):
            # note: for now, we ignore the "uncalibrated" flag
            colors.append(i32(s, 8+i*4) & 0x7fffffff)

        self.mode, self.rawmode = MODES[tuple(colors)]

        # load JPEG tables, if any
        self.jpeg = {}
        for i in range(256):
            id = 0x3000001|(i << 16)
            if id in prop:
                self.jpeg[i] = prop[id]

        # print len(self.jpeg), "tables loaded"

        self._open_subimage(1, self.maxid)

    def _open_subimage(self, index = 1, subimage = 0):
        #
        # setup tile descriptors for a given subimage

        stream = [
            "Data Object Store %06d" % index,
            "Resolution %04d" % subimage,
            "Subimage 0000 Header"
        ]

        fp = self.ole.openstream(stream)

        # skip prefix
        p = fp.read(28)

        # header stream
        s = fp.read(36)

        size = i32(s, 4), i32(s, 8)
        tilecount = i32(s, 12)
        tilesize = i32(s, 16), i32(s, 20)
        channels = i32(s, 24)
        offset = i32(s, 28)
        length = i32(s, 32)

        # print size, self.mode, self.rawmode

        if size != self.size:
            raise IOError("subimage mismatch")

        # get tile descriptors
        fp.seek(28 + offset)
        s = fp.read(i32(s, 12) * length)

        x = y = 0
        xsize, ysize = size
        xtile, ytile = tilesize
        self.tile = []

        for i in range(0, len(s), length):

            compression = i32(s, i+8)

            if compression == 0:
                self.tile.append(("raw", (x,y,x+xtile,y+ytile),
                        i32(s, i) + 28, (self.rawmode)))

            elif compression == 1:

                # FIXME: the fill decoder is not implemented
                self.tile.append(("fill", (x,y,x+xtile,y+ytile),
                        i32(s, i) + 28, (self.rawmode, s[12:16])))

            elif compression == 2:

                internal_color_conversion = i8(s[14])
                jpeg_tables = i8(s[15])
                rawmode = self.rawmode

                if internal_color_conversion:
                    # The image is stored as usual (usually YCbCr).
                    if rawmode == "RGBA":
                        # For "RGBA", data is stored as YCbCrA based on
                        # negative RGB. The following trick works around
                        # this problem :
                        jpegmode, rawmode = "YCbCrK", "CMYK"
                    else:
                        jpegmode = None # let the decoder decide

                else:
                    # The image is stored as defined by rawmode
                    jpegmode = rawmode

                self.tile.append(("jpeg", (x,y,x+xtile,y+ytile),
                        i32(s, i) + 28, (rawmode, jpegmode)))

                # FIXME: jpeg tables are tile dependent; the prefix
                # data must be placed in the tile descriptor itself!

                if jpeg_tables:
                    self.tile_prefix = self.jpeg[jpeg_tables]

            else:
                raise IOError("unknown/invalid compression")

            x = x + xtile
            if x >= xsize:
                x, y = 0, y + ytile
                if y >= ysize:
                    break # isn't really required

        self.stream = stream
        self.fp = None

    def load(self):

        if not self.fp:
            self.fp = self.ole.openstream(self.stream[:2] + ["Subimage 0000 Data"])

        ImageFile.ImageFile.load(self)

#
# --------------------------------------------------------------------

Image.register_open("FPX", FpxImageFile, _accept)

Image.register_extension("FPX", ".fpx")

########NEW FILE########
__FILENAME__ = GbrImagePlugin
#
# The Python Imaging Library
# $Id$
#
# load a GIMP brush file
#
# History:
#       96-03-14 fl     Created
#
# Copyright (c) Secret Labs AB 1997.
# Copyright (c) Fredrik Lundh 1996.
#
# See the README file for information on usage and redistribution.
#

from PIL import Image, ImageFile, _binary

i32 = _binary.i32be

def _accept(prefix):
    return i32(prefix) >= 20 and i32(prefix[4:8]) == 1

##
# Image plugin for the GIMP brush format.

class GbrImageFile(ImageFile.ImageFile):

    format = "GBR"
    format_description = "GIMP brush file"

    def _open(self):

        header_size = i32(self.fp.read(4))
        version = i32(self.fp.read(4))
        if header_size < 20 or version != 1:
            raise SyntaxError("not a GIMP brush")

        width = i32(self.fp.read(4))
        height = i32(self.fp.read(4))
        bytes = i32(self.fp.read(4))
        if width <= 0 or height <= 0 or bytes != 1:
            raise SyntaxError("not a GIMP brush")

        comment = self.fp.read(header_size - 20)[:-1]

        self.mode = "L"
        self.size = width, height

        self.info["comment"] = comment

        # Since the brush is so small, we read the data immediately
        self.data = self.fp.read(width * height)

    def load(self):

        if not self.data:
            return

        # create an image out of the brush data block
        self.im = Image.core.new(self.mode, self.size)
        self.im.frombytes(self.data)
        self.data = b""

#
# registry

Image.register_open("GBR", GbrImageFile, _accept)

Image.register_extension("GBR", ".gbr")

########NEW FILE########
__FILENAME__ = GdImageFile
#
# The Python Imaging Library.
# $Id$
#
# GD file handling
#
# History:
# 1996-04-12 fl   Created
#
# Copyright (c) 1997 by Secret Labs AB.
# Copyright (c) 1996 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#


# NOTE: This format cannot be automatically recognized, so the
# class is not registered for use with Image.open().  To open a
# gd file, use the GdImageFile.open() function instead.

# THE GD FORMAT IS NOT DESIGNED FOR DATA INTERCHANGE.  This
# implementation is provided for convenience and demonstrational
# purposes only.


__version__ = "0.1"

from PIL import ImageFile, ImagePalette, _binary
from PIL._util import isPath

try:
    import builtins
except ImportError:
    import __builtin__
    builtins = __builtin__

i16 = _binary.i16be

##
# Image plugin for the GD uncompressed format.  Note that this format
# is not supported by the standard <b>Image.open</b> function.  To use
# this plugin, you have to import the <b>GdImageFile</b> module and
# use the <b>GdImageFile.open</b> function.

class GdImageFile(ImageFile.ImageFile):

    format = "GD"
    format_description = "GD uncompressed images"

    def _open(self):

        # Header
        s = self.fp.read(775)

        self.mode = "L" # FIXME: "P"
        self.size = i16(s[0:2]), i16(s[2:4])

        # transparency index
        tindex = i16(s[5:7])
        if tindex < 256:
            self.info["transparent"] = tindex

        self.palette = ImagePalette.raw("RGB", s[7:])

        self.tile = [("raw", (0,0)+self.size, 775, ("L", 0, -1))]

##
# Load texture from a GD image file.
#
# @param filename GD file name, or an opened file handle.
# @param mode Optional mode.  In this version, if the mode argument
#     is given, it must be "r".
# @return An image instance.
# @exception IOError If the image could not be read.

def open(fp, mode = "r"):

    if mode != "r":
        raise ValueError("bad mode")

    if isPath(fp):
        filename = fp
        fp = builtins.open(fp, "rb")
    else:
        filename = ""

    try:
        return GdImageFile(fp, filename)
    except SyntaxError:
        raise IOError("cannot identify this image file")

########NEW FILE########
__FILENAME__ = GifImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# GIF file handling
#
# History:
# 1995-09-01 fl   Created
# 1996-12-14 fl   Added interlace support
# 1996-12-30 fl   Added animation support
# 1997-01-05 fl   Added write support, fixed local colour map bug
# 1997-02-23 fl   Make sure to load raster data in getdata()
# 1997-07-05 fl   Support external decoder (0.4)
# 1998-07-09 fl   Handle all modes when saving (0.5)
# 1998-07-15 fl   Renamed offset attribute to avoid name clash
# 2001-04-16 fl   Added rewind support (seek to frame 0) (0.6)
# 2001-04-17 fl   Added palette optimization (0.7)
# 2002-06-06 fl   Added transparency support for save (0.8)
# 2004-02-24 fl   Disable interlacing for small images
#
# Copyright (c) 1997-2004 by Secret Labs AB
# Copyright (c) 1995-2004 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#


__version__ = "0.9"


from PIL import Image, ImageFile, ImagePalette, _binary


# --------------------------------------------------------------------
# Helpers

i8 = _binary.i8
i16 = _binary.i16le
o8 = _binary.o8
o16 = _binary.o16le


# --------------------------------------------------------------------
# Identify/read GIF files

def _accept(prefix):
    return prefix[:6] in [b"GIF87a", b"GIF89a"]

##
# Image plugin for GIF images.  This plugin supports both GIF87 and
# GIF89 images.

class GifImageFile(ImageFile.ImageFile):

    format = "GIF"
    format_description = "Compuserve GIF"
    global_palette = None

    def data(self):
        s = self.fp.read(1)
        if s and i8(s):
            return self.fp.read(i8(s))
        return None

    def _open(self):

        # Screen
        s = self.fp.read(13)
        if s[:6] not in [b"GIF87a", b"GIF89a"]:
            raise SyntaxError("not a GIF file")

        self.info["version"] = s[:6]
        self.size = i16(s[6:]), i16(s[8:])
        self.tile = []
        flags = i8(s[10])
        bits = (flags & 7) + 1

        if flags & 128:
            # get global palette
            self.info["background"] = i8(s[11])
            # check if palette contains colour indices
            p = self.fp.read(3<<bits)
            for i in range(0, len(p), 3):
                if not (i//3 == i8(p[i]) == i8(p[i+1]) == i8(p[i+2])):
                    p = ImagePalette.raw("RGB", p)
                    self.global_palette = self.palette = p
                    break

        self.__fp = self.fp # FIXME: hack
        self.__rewind = self.fp.tell()
        self.seek(0) # get ready to read first frame

    def seek(self, frame):

        if frame == 0:
            # rewind
            self.__offset = 0
            self.dispose = None
            self.__frame = -1
            self.__fp.seek(self.__rewind)

        if frame != self.__frame + 1:
            raise ValueError("cannot seek to frame %d" % frame)
        self.__frame = frame

        self.tile = []

        self.fp = self.__fp
        if self.__offset:
            # backup to last frame
            self.fp.seek(self.__offset)
            while self.data():
                pass
            self.__offset = 0

        if self.dispose:
            self.im = self.dispose
            self.dispose = None

        from copy import copy
        self.palette = copy(self.global_palette)

        while True:

            s = self.fp.read(1)
            if not s or s == b";":
                break

            elif s == b"!":
                #
                # extensions
                #
                s = self.fp.read(1)
                block = self.data()
                if i8(s) == 249:
                    #
                    # graphic control extension
                    #
                    flags = i8(block[0])
                    if flags & 1:
                        self.info["transparency"] = i8(block[3])
                    self.info["duration"] = i16(block[1:3]) * 10
                    try:
                        # disposal methods
                        if flags & 8:
                            # replace with background colour
                            self.dispose = Image.core.fill("P", self.size,
                                self.info["background"])
                        elif flags & 16:
                            # replace with previous contents
                            self.dispose = self.im.copy()
                    except (AttributeError, KeyError):
                        pass
                elif i8(s) == 255:
                    #
                    # application extension
                    #
                    self.info["extension"] = block, self.fp.tell()
                    if block[:11] == b"NETSCAPE2.0":
                        block = self.data()
                        if len(block) >= 3 and i8(block[0]) == 1:
                            self.info["loop"] = i16(block[1:3])
                while self.data():
                    pass

            elif s == b",":
                #
                # local image
                #
                s = self.fp.read(9)

                # extent
                x0, y0 = i16(s[0:]), i16(s[2:])
                x1, y1 = x0 + i16(s[4:]), y0 + i16(s[6:])
                flags = i8(s[8])

                interlace = (flags & 64) != 0

                if flags & 128:
                    bits = (flags & 7) + 1
                    self.palette =\
                        ImagePalette.raw("RGB", self.fp.read(3<<bits))

                # image data
                bits = i8(self.fp.read(1))
                self.__offset = self.fp.tell()
                self.tile = [("gif",
                             (x0, y0, x1, y1),
                             self.__offset,
                             (bits, interlace))]
                break

            else:
                pass
                # raise IOError, "illegal GIF tag `%x`" % i8(s)

        if not self.tile:
            # self.__fp = None
            raise EOFError("no more images in GIF file")

        self.mode = "L"
        if self.palette:
            self.mode = "P"

    def tell(self):
        return self.__frame


# --------------------------------------------------------------------
# Write GIF files

try:
    import _imaging_gif
except ImportError:
    _imaging_gif = None

RAWMODE = {
    "1": "L",
    "L": "L",
    "P": "P",
}

def _save(im, fp, filename):

    if _imaging_gif:
        # call external driver
        try:
            _imaging_gif.save(im, fp, filename)
            return
        except IOError:
            pass # write uncompressed file

    try:
        rawmode = RAWMODE[im.mode]
        imOut = im
    except KeyError:
        # convert on the fly (EXPERIMENTAL -- I'm not sure PIL
        # should automatically convert images on save...)
        if Image.getmodebase(im.mode) == "RGB":
            palette_size = 256
            if im.palette:
                palette_size = len(im.palette.getdata()[1]) // 3
            imOut = im.convert("P", palette=1, colors=palette_size)
            rawmode = "P"
        else:
            imOut = im.convert("L")
            rawmode = "L"

    # header
    try:
        palette = im.encoderinfo["palette"]
    except KeyError:
        palette = None
        im.encoderinfo["optimize"] = im.encoderinfo.get("optimize", True)
        if im.encoderinfo["optimize"]:
            # When the mode is L, and we optimize, we end up with
            # im.mode == P and rawmode = L, which fails.
            # If we're optimizing the palette, we're going to be
            # in a rawmode of P anyway. 
            rawmode = 'P'

    header, usedPaletteColors = getheader(imOut, palette, im.encoderinfo)
    for s in header:
        fp.write(s)

    flags = 0

    try:
        interlace = im.encoderinfo["interlace"]
    except KeyError:
        interlace = 1

    # workaround for @PIL153
    if min(im.size) < 16:
        interlace = 0

    if interlace:
        flags = flags | 64

    try:
        transparency = im.encoderinfo["transparency"]
    except KeyError:
        pass
    else:
        transparency = int(transparency)
        # optimize the block away if transparent color is not used
        transparentColorExists = True
        # adjust the transparency index after optimize
        if usedPaletteColors is not None and len(usedPaletteColors) < 256:
            for i in range(len(usedPaletteColors)):
                if usedPaletteColors[i] == transparency:
                    transparency = i
                    transparentColorExists = True
                    break
                else:
                    transparentColorExists = False

        # transparency extension block
        if transparentColorExists:
            fp.write(b"!" +
                     o8(249) +              # extension intro
                     o8(4) +                # length
                     o8(1) +                # transparency info present
                     o16(0) +               # duration
                     o8(transparency)       # transparency index
                     + o8(0))

    # local image header
    fp.write(b"," +
             o16(0) + o16(0) +          # bounding box
             o16(im.size[0]) +          # size
             o16(im.size[1]) +
             o8(flags) +                # flags
             o8(8))                     # bits

    imOut.encoderconfig = (8, interlace)
    ImageFile._save(imOut, fp, [("gif", (0,0)+im.size, 0, rawmode)])

    fp.write(b"\0") # end of image data

    fp.write(b";") # end of file

    try:
        fp.flush()
    except: pass


def _save_netpbm(im, fp, filename):

    #
    # If you need real GIF compression and/or RGB quantization, you
    # can use the external NETPBM/PBMPLUS utilities.  See comments
    # below for information on how to enable this.

    import os
    file = im._dump()
    if im.mode != "RGB":
        os.system("ppmtogif %s >%s" % (file, filename))
    else:
        os.system("ppmquant 256 %s | ppmtogif >%s" % (file, filename))
    try: os.unlink(file)
    except: pass


# --------------------------------------------------------------------
# GIF utilities

def getheader(im, palette=None, info=None):
    """Return a list of strings representing a GIF header"""

    optimize = info and info.get("optimize", 0)

    # Header Block
    # http://www.matthewflickinger.com/lab/whatsinagif/bits_and_bytes.asp
    header = [
        b"GIF87a" +             # signature + version
        o16(im.size[0]) +       # canvas width
        o16(im.size[1])         # canvas height
    ]

    if im.mode == "P":
        if palette and isinstance(palette, bytes):
            sourcePalette = palette[:768]
        else:
            sourcePalette = im.im.getpalette("RGB")[:768]
    else: # L-mode
        if palette and isinstance(palette, bytes):
            sourcePalette = palette[:768]
        else:
            sourcePalette = bytearray([i//3 for i in range(768)])

    usedPaletteColors = paletteBytes = None

    if optimize:
        usedPaletteColors = []

        # check which colors are used
        i = 0
        for count in im.histogram():
            if count:
                usedPaletteColors.append(i)
            i += 1

        # create the new palette if not every color is used
        if len(usedPaletteColors) < 256:
            paletteBytes = b""
            newPositions = {}

            i = 0
            # pick only the used colors from the palette
            for oldPosition in usedPaletteColors:
                paletteBytes += sourcePalette[oldPosition*3:oldPosition*3+3]
                newPositions[oldPosition] = i
                i += 1

            # replace the palette color id of all pixel with the new id
            imageBytes = bytearray(im.tobytes())
            for i in range(len(imageBytes)):
                imageBytes[i] = newPositions[imageBytes[i]]
            im.frombytes(bytes(imageBytes))
            newPaletteBytes = paletteBytes + (768 - len(paletteBytes)) * b'\x00'
            im.putpalette(newPaletteBytes) 
            im.palette = ImagePalette.ImagePalette("RGB", palette = paletteBytes, size = len(paletteBytes))

    if not paletteBytes:
        paletteBytes = sourcePalette

    # Logical Screen Descriptor
    # calculate the palette size for the header
    import math
    colorTableSize = int(math.ceil(math.log(len(paletteBytes)//3, 2)))-1
    if colorTableSize < 0: colorTableSize = 0
    # size of global color table + global color table flag
    header.append(o8(colorTableSize + 128))
    # background + reserved/aspect
    header.append(o8(0) + o8(0))
    # end of Logical Screen Descriptor

    # add the missing amount of bytes
    # the palette has to be 2<<n in size
    actualTargetSizeDiff = (2<<colorTableSize) - len(paletteBytes)//3
    if actualTargetSizeDiff > 0:
        paletteBytes += o8(0) * 3 * actualTargetSizeDiff

    # Header + Logical Screen Descriptor + Global Color Table
    header.append(paletteBytes)
    return header, usedPaletteColors


def getdata(im, offset = (0, 0), **params):
    """Return a list of strings representing this image.
       The first string is a local image header, the rest contains
       encoded image data."""

    class collector:
        data = []
        def write(self, data):
            self.data.append(data)

    im.load() # make sure raster data is available

    fp = collector()

    try:
        im.encoderinfo = params

        # local image header
        fp.write(b"," +
                 o16(offset[0]) +       # offset
                 o16(offset[1]) +
                 o16(im.size[0]) +      # size
                 o16(im.size[1]) +
                 o8(0) +                # flags
                 o8(8))                 # bits

        ImageFile._save(im, fp, [("gif", (0,0)+im.size, 0, RAWMODE[im.mode])])

        fp.write(b"\0") # end of image data

    finally:
        del im.encoderinfo

    return fp.data


# --------------------------------------------------------------------
# Registry

Image.register_open(GifImageFile.format, GifImageFile, _accept)
Image.register_save(GifImageFile.format, _save)
Image.register_extension(GifImageFile.format, ".gif")
Image.register_mime(GifImageFile.format, "image/gif")

#
# Uncomment the following line if you wish to use NETPBM/PBMPLUS
# instead of the built-in "uncompressed" GIF encoder

# Image.register_save(GifImageFile.format, _save_netpbm)

########NEW FILE########
__FILENAME__ = GimpGradientFile
#
# Python Imaging Library
# $Id$
#
# stuff to read (and render) GIMP gradient files
#
# History:
#       97-08-23 fl     Created
#
# Copyright (c) Secret Labs AB 1997.
# Copyright (c) Fredrik Lundh 1997.
#
# See the README file for information on usage and redistribution.
#

from math import pi, log, sin, sqrt
from PIL._binary import o8

# --------------------------------------------------------------------
# Stuff to translate curve segments to palette values (derived from
# the corresponding code in GIMP, written by Federico Mena Quintero.
# See the GIMP distribution for more information.)
#

EPSILON = 1e-10

def linear(middle, pos):
    if pos <= middle:
        if middle < EPSILON:
            return 0.0
        else:
            return 0.5 * pos / middle
    else:
        pos = pos - middle
        middle = 1.0 - middle
        if middle < EPSILON:
            return 1.0
        else:
            return 0.5 + 0.5 * pos / middle

def curved(middle, pos):
    return pos ** (log(0.5) / log(max(middle, EPSILON)))

def sine(middle, pos):
    return (sin((-pi / 2.0) + pi * linear(middle, pos)) + 1.0) / 2.0

def sphere_increasing(middle, pos):
    return sqrt(1.0 - (linear(middle, pos) - 1.0) ** 2)

def sphere_decreasing(middle, pos):
    return 1.0 - sqrt(1.0 - linear(middle, pos) ** 2)

SEGMENTS = [ linear, curved, sine, sphere_increasing, sphere_decreasing ]

class GradientFile:

    gradient = None

    def getpalette(self, entries = 256):

        palette = []

        ix = 0
        x0, x1, xm, rgb0, rgb1, segment = self.gradient[ix]

        for i in range(entries):

            x = i / float(entries-1)

            while x1 < x:
                ix = ix + 1
                x0, x1, xm, rgb0, rgb1, segment = self.gradient[ix]

            w = x1 - x0

            if w < EPSILON:
                scale = segment(0.5, 0.5)
            else:
                scale = segment((xm - x0) / w, (x - x0) / w)

            # expand to RGBA
            r = o8(int(255 * ((rgb1[0] - rgb0[0]) * scale + rgb0[0]) + 0.5))
            g = o8(int(255 * ((rgb1[1] - rgb0[1]) * scale + rgb0[1]) + 0.5))
            b = o8(int(255 * ((rgb1[2] - rgb0[2]) * scale + rgb0[2]) + 0.5))
            a = o8(int(255 * ((rgb1[3] - rgb0[3]) * scale + rgb0[3]) + 0.5))

            # add to palette
            palette.append(r + g + b + a)

        return b"".join(palette), "RGBA"

##
# File handler for GIMP's gradient format.

class GimpGradientFile(GradientFile):

    def __init__(self, fp):

        if fp.readline()[:13] != b"GIMP Gradient":
            raise SyntaxError("not a GIMP gradient file")

        count = int(fp.readline())

        gradient = []

        for i in range(count):

            s = fp.readline().split()
            w = [float(x) for x in s[:11]]

            x0, x1  = w[0], w[2]
            xm      = w[1]
            rgb0    = w[3:7]
            rgb1    = w[7:11]

            segment = SEGMENTS[int(s[11])]
            cspace  = int(s[12])

            if cspace != 0:
                raise IOError("cannot handle HSV colour space")

            gradient.append((x0, x1, xm, rgb0, rgb1, segment))

        self.gradient = gradient

########NEW FILE########
__FILENAME__ = GimpPaletteFile
#
# Python Imaging Library
# $Id$
#
# stuff to read GIMP palette files
#
# History:
# 1997-08-23 fl     Created
# 2004-09-07 fl     Support GIMP 2.0 palette files.
#
# Copyright (c) Secret Labs AB 1997-2004.  All rights reserved.
# Copyright (c) Fredrik Lundh 1997-2004.
#
# See the README file for information on usage and redistribution.
#

import re
from PIL._binary import o8

##
# File handler for GIMP's palette format.

class GimpPaletteFile:

    rawmode = "RGB"

    def __init__(self, fp):

        self.palette = [o8(i)*3 for i in range(256)]

        if fp.readline()[:12] != b"GIMP Palette":
            raise SyntaxError("not a GIMP palette file")

        i = 0

        while i <= 255:

            s = fp.readline()

            if not s:
                break
            # skip fields and comment lines
            if re.match(b"\w+:|#", s):
                continue
            if len(s) > 100:
                raise SyntaxError("bad palette file")

            v = tuple(map(int, s.split()[:3]))
            if len(v) != 3:
                raise ValueError("bad palette entry")

            if 0 <= i <= 255:
                self.palette[i] = o8(v[0]) + o8(v[1]) + o8(v[2])

            i = i + 1

        self.palette = b"".join(self.palette)


    def getpalette(self):

        return self.palette, self.rawmode

########NEW FILE########
__FILENAME__ = GribStubImagePlugin
#
# The Python Imaging Library
# $Id$
#
# GRIB stub adapter
#
# Copyright (c) 1996-2003 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

from PIL import Image, ImageFile

_handler = None

##
# Install application-specific GRIB image handler.
#
# @param handler Handler object.

def register_handler(handler):
    global _handler
    _handler = handler

# --------------------------------------------------------------------
# Image adapter

def _accept(prefix):
    return prefix[0:4] == b"GRIB" and prefix[7] == b'\x01'

class GribStubImageFile(ImageFile.StubImageFile):

    format = "GRIB"
    format_description = "GRIB"

    def _open(self):

        offset = self.fp.tell()

        if not _accept(self.fp.read(8)):
            raise SyntaxError("Not a GRIB file")

        self.fp.seek(offset)

        # make something up
        self.mode = "F"
        self.size = 1, 1

        loader = self._load()
        if loader:
            loader.open(self)

    def _load(self):
        return _handler

def _save(im, fp, filename):
    if _handler is None or not hasattr("_handler", "save"):
        raise IOError("GRIB save handler not installed")
    _handler.save(im, fp, filename)


# --------------------------------------------------------------------
# Registry

Image.register_open(GribStubImageFile.format, GribStubImageFile, _accept)
Image.register_save(GribStubImageFile.format, _save)

Image.register_extension(GribStubImageFile.format, ".grib")

########NEW FILE########
__FILENAME__ = Hdf5StubImagePlugin
#
# The Python Imaging Library
# $Id$
#
# HDF5 stub adapter
#
# Copyright (c) 2000-2003 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

from PIL import Image, ImageFile

_handler = None

##
# Install application-specific HDF5 image handler.
#
# @param handler Handler object.

def register_handler(handler):
    global _handler
    _handler = handler

# --------------------------------------------------------------------
# Image adapter

def _accept(prefix):
    return prefix[:8] == b"\x89HDF\r\n\x1a\n"

class HDF5StubImageFile(ImageFile.StubImageFile):

    format = "HDF5"
    format_description = "HDF5"

    def _open(self):

        offset = self.fp.tell()

        if not _accept(self.fp.read(8)):
            raise SyntaxError("Not an HDF file")

        self.fp.seek(offset)

        # make something up
        self.mode = "F"
        self.size = 1, 1

        loader = self._load()
        if loader:
            loader.open(self)

    def _load(self):
        return _handler


def _save(im, fp, filename):
    if _handler is None or not hasattr("_handler", "save"):
        raise IOError("HDF5 save handler not installed")
    _handler.save(im, fp, filename)


# --------------------------------------------------------------------
# Registry

Image.register_open(HDF5StubImageFile.format, HDF5StubImageFile, _accept)
Image.register_save(HDF5StubImageFile.format, _save)

Image.register_extension(HDF5StubImageFile.format, ".h5")
Image.register_extension(HDF5StubImageFile.format, ".hdf")

########NEW FILE########
__FILENAME__ = IcnsImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# Mac OS X icns file decoder, based on icns.py by Bob Ippolito.
#
# history:
# 2004-10-09 fl   Turned into a PIL plugin; removed 2.3 dependencies.
#
# Copyright (c) 2004 by Bob Ippolito.
# Copyright (c) 2004 by Secret Labs.
# Copyright (c) 2004 by Fredrik Lundh.
# Copyright (c) 2014 by Alastair Houghton.
#
# See the README file for information on usage and redistribution.
#

from PIL import Image, ImageFile, PngImagePlugin, _binary
import struct, io

enable_jpeg2k = hasattr(Image.core, 'jp2klib_version')
if enable_jpeg2k:
    from PIL import Jpeg2KImagePlugin

i8 = _binary.i8

HEADERSIZE = 8

def nextheader(fobj):
    return struct.unpack('>4sI', fobj.read(HEADERSIZE))

def read_32t(fobj, start_length, size):
    # The 128x128 icon seems to have an extra header for some reason.
    (start, length) = start_length
    fobj.seek(start)
    sig = fobj.read(4)
    if sig != b'\x00\x00\x00\x00':
        raise SyntaxError('Unknown signature, expecting 0x00000000')
    return read_32(fobj, (start + 4, length - 4), size)

def read_32(fobj, start_length, size):
    """
    Read a 32bit RGB icon resource.  Seems to be either uncompressed or
    an RLE packbits-like scheme.
    """
    (start, length) = start_length
    fobj.seek(start)
    pixel_size = (size[0] * size[2], size[1] * size[2])
    sizesq = pixel_size[0] * pixel_size[1]
    if length == sizesq * 3:
        # uncompressed ("RGBRGBGB")
        indata = fobj.read(length)
        im = Image.frombuffer("RGB", pixel_size, indata, "raw", "RGB", 0, 1)
    else:
        # decode image
        im = Image.new("RGB", pixel_size, None)
        for band_ix in range(3):
            data = []
            bytesleft = sizesq
            while bytesleft > 0:
                byte = fobj.read(1)
                if not byte:
                    break
                byte = i8(byte)
                if byte & 0x80:
                    blocksize = byte - 125
                    byte = fobj.read(1)
                    for i in range(blocksize):
                        data.append(byte)
                else:
                    blocksize = byte + 1
                    data.append(fobj.read(blocksize))
                bytesleft = bytesleft - blocksize
                if bytesleft <= 0:
                    break
            if bytesleft != 0:
                raise SyntaxError(
                    "Error reading channel [%r left]" % bytesleft
                    )
            band = Image.frombuffer(
                "L", pixel_size, b"".join(data), "raw", "L", 0, 1
                )
            im.im.putband(band.im, band_ix)
    return {"RGB": im}

def read_mk(fobj, start_length, size):
    # Alpha masks seem to be uncompressed
    (start, length) = start_length
    fobj.seek(start)
    pixel_size = (size[0] * size[2], size[1] * size[2])
    sizesq = pixel_size[0] * pixel_size[1]
    band = Image.frombuffer(
        "L", pixel_size, fobj.read(sizesq), "raw", "L", 0, 1
        )
    return {"A": band}

def read_png_or_jpeg2000(fobj, start_length, size):
    (start, length) = start_length
    fobj.seek(start)
    sig = fobj.read(12)
    if sig[:8] == b'\x89PNG\x0d\x0a\x1a\x0a':
        fobj.seek(start)
        im = PngImagePlugin.PngImageFile(fobj)
        return {"RGBA": im}
    elif sig[:4] == b'\xff\x4f\xff\x51' \
        or sig[:4] == b'\x0d\x0a\x87\x0a' \
        or sig == b'\x00\x00\x00\x0cjP  \x0d\x0a\x87\x0a':
        if not enable_jpeg2k:
            raise ValueError('Unsupported icon subimage format (rebuild PIL with JPEG 2000 support to fix this)')
        # j2k, jpc or j2c
        fobj.seek(start)
        jp2kstream = fobj.read(length)
        f = io.BytesIO(jp2kstream)
        im = Jpeg2KImagePlugin.Jpeg2KImageFile(f)
        if im.mode != 'RGBA':
            im = im.convert('RGBA')
        return {"RGBA": im}
    else:
        raise ValueError('Unsupported icon subimage format')

class IcnsFile:

    SIZES = {
        (512, 512, 2): [
            (b'ic10', read_png_or_jpeg2000),
        ],
        (512, 512, 1): [
            (b'ic09', read_png_or_jpeg2000),
        ],
        (256, 256, 2): [
            (b'ic14', read_png_or_jpeg2000),
        ],
        (256, 256, 1): [
            (b'ic08', read_png_or_jpeg2000),
        ],
        (128, 128, 2): [
            (b'ic13', read_png_or_jpeg2000),
        ],
        (128, 128, 1): [
            (b'ic07', read_png_or_jpeg2000),
            (b'it32', read_32t),
            (b't8mk', read_mk),
        ],
        (64, 64, 1): [
            (b'icp6', read_png_or_jpeg2000),
        ],
        (32, 32, 2): [
            (b'ic12', read_png_or_jpeg2000),
        ],
        (48, 48, 1): [
            (b'ih32', read_32),
            (b'h8mk', read_mk),
        ],
        (32, 32, 1): [
            (b'icp5', read_png_or_jpeg2000),
            (b'il32', read_32),
            (b'l8mk', read_mk),
        ],
        (16, 16, 2): [
            (b'ic11', read_png_or_jpeg2000),
        ],
        (16, 16, 1): [
            (b'icp4', read_png_or_jpeg2000),
            (b'is32', read_32),
            (b's8mk', read_mk),
        ],
    }

    def __init__(self, fobj):
        """
        fobj is a file-like object as an icns resource
        """
        # signature : (start, length)
        self.dct = dct = {}
        self.fobj = fobj
        sig, filesize = nextheader(fobj)
        if sig != b'icns':
            raise SyntaxError('not an icns file')
        i = HEADERSIZE
        while i < filesize:
            sig, blocksize = nextheader(fobj)
            i = i + HEADERSIZE
            blocksize = blocksize - HEADERSIZE
            dct[sig] = (i, blocksize)
            fobj.seek(blocksize, 1)
            i = i + blocksize

    def itersizes(self):
        sizes = []
        for size, fmts in self.SIZES.items():
            for (fmt, reader) in fmts:
                if fmt in self.dct:
                    sizes.append(size)
                    break
        return sizes

    def bestsize(self):
        sizes = self.itersizes()
        if not sizes:
            raise SyntaxError("No 32bit icon resources found")
        return max(sizes)

    def dataforsize(self, size):
        """
        Get an icon resource as {channel: array}.  Note that
        the arrays are bottom-up like windows bitmaps and will likely
        need to be flipped or transposed in some way.
        """
        dct = {}
        for code, reader in self.SIZES[size]:
            desc = self.dct.get(code)
            if desc is not None:
                dct.update(reader(self.fobj, desc, size))
        return dct

    def getimage(self, size=None):
        if size is None:
            size = self.bestsize()
        if len(size) == 2:
            size = (size[0], size[1], 1)
        channels = self.dataforsize(size)

        im = channels.get('RGBA', None)
        if im:
            return im
        
        im = channels.get("RGB").copy()
        try:
            im.putalpha(channels["A"])
        except KeyError:
            pass
        return im

##
# Image plugin for Mac OS icons.

class IcnsImageFile(ImageFile.ImageFile):
    """
    PIL read-only image support for Mac OS .icns files.
    Chooses the best resolution, but will possibly load
    a different size image if you mutate the size attribute
    before calling 'load'.

    The info dictionary has a key 'sizes' that is a list
    of sizes that the icns file has.
    """

    format = "ICNS"
    format_description = "Mac OS icns resource"

    def _open(self):
        self.icns = IcnsFile(self.fp)
        self.mode = 'RGBA'
        self.best_size = self.icns.bestsize()
        self.size = (self.best_size[0] * self.best_size[2],
                     self.best_size[1] * self.best_size[2])
        self.info['sizes'] = self.icns.itersizes()
        # Just use this to see if it's loaded or not yet.
        self.tile = ('',)

    def load(self):
        if len(self.size) == 3:
            self.best_size = self.size
            self.size = (self.best_size[0] * self.best_size[2],
                         self.best_size[1] * self.best_size[2])

        Image.Image.load(self)
        if not self.tile:
            return
        self.load_prepare()
        # This is likely NOT the best way to do it, but whatever.
        im = self.icns.getimage(self.best_size)

        # If this is a PNG or JPEG 2000, it won't be loaded yet
        im.load()
        
        self.im = im.im
        self.mode = im.mode
        self.size = im.size
        self.fp = None
        self.icns = None
        self.tile = ()
        self.load_end()

Image.register_open("ICNS", IcnsImageFile, lambda x: x[:4] == b'icns')
Image.register_extension("ICNS", '.icns')

if __name__ == '__main__':
    import os, sys
    imf = IcnsImageFile(open(sys.argv[1], 'rb'))
    for size in imf.info['sizes']:
        imf.size = size
        imf.load()
        im = imf.im
        im.save('out-%s-%s-%s.png' % size)
    im = Image.open(open(sys.argv[1], "rb"))
    im.save("out.png")
    if sys.platform == 'windows':
        os.startfile("out.png")

########NEW FILE########
__FILENAME__ = IcoImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# Windows Icon support for PIL
#
# History:
#       96-05-27 fl     Created
#
# Copyright (c) Secret Labs AB 1997.
# Copyright (c) Fredrik Lundh 1996.
#
# See the README file for information on usage and redistribution.
#

# This plugin is a refactored version of Win32IconImagePlugin by Bryan Davis <casadebender@gmail.com>.
# https://code.google.com/p/casadebender/wiki/Win32IconImagePlugin
#
# Icon format references:
#   * http://en.wikipedia.org/wiki/ICO_(file_format)
#   * http://msdn.microsoft.com/en-us/library/ms997538.aspx


__version__ = "0.1"

from PIL import Image, ImageFile, BmpImagePlugin, PngImagePlugin, _binary
from math import log, ceil

#
# --------------------------------------------------------------------

i8 = _binary.i8
i16 = _binary.i16le
i32 = _binary.i32le

_MAGIC = b"\0\0\1\0"

def _accept(prefix):
    return prefix[:4] == _MAGIC


class IcoFile:
    def __init__(self, buf):
        """
        Parse image from file-like object containing ico file data
        """

        # check magic
        s = buf.read(6)
        if not _accept(s):
            raise SyntaxError("not an ICO file")

        self.buf = buf
        self.entry = []

        # Number of items in file
        self.nb_items = i16(s[4:])

        # Get headers for each item
        for i in range(self.nb_items):
            s = buf.read(16)

            icon_header = {
                'width': i8(s[0]),
                'height': i8(s[1]),
                'nb_color': i8(s[2]), # Number of colors in image (0 if >=8bpp)
                'reserved': i8(s[3]),
                'planes': i16(s[4:]),
                'bpp': i16(s[6:]),
                'size': i32(s[8:]),
                'offset': i32(s[12:])
            }

            # See Wikipedia
            for j in ('width', 'height'):
                if not icon_header[j]:
                    icon_header[j] = 256

            # See Wikipedia notes about color depth.
            # We need this just to differ images with equal sizes
            icon_header['color_depth'] = (icon_header['bpp'] or (icon_header['nb_color'] != 0 and ceil(log(icon_header['nb_color'],2))) or 256)

            icon_header['dim'] = (icon_header['width'], icon_header['height'])
            icon_header['square'] = icon_header['width'] * icon_header['height']

            self.entry.append(icon_header)

        self.entry = sorted(self.entry, key=lambda x: x['color_depth'])
        # ICO images are usually squares
        # self.entry = sorted(self.entry, key=lambda x: x['width'])
        self.entry = sorted(self.entry, key=lambda x: x['square'])
        self.entry.reverse()

    def sizes(self):
        """
        Get a list of all available icon sizes and color depths.
        """
        return set((h['width'], h['height']) for h in self.entry)

    def getimage(self, size, bpp=False):
        """
        Get an image from the icon
        """
        for (i, h) in enumerate(self.entry):
            if size == h['dim'] and (bpp == False or bpp == h['color_depth']):
                return self.frame(i)
        return self.frame(0)

    def frame(self, idx):
        """
        Get an image from frame idx
        """

        header = self.entry[idx]

        self.buf.seek(header['offset'])
        data = self.buf.read(8)
        self.buf.seek(header['offset'])

        if data[:8] == PngImagePlugin._MAGIC:
            # png frame
            im = PngImagePlugin.PngImageFile(self.buf)
        else:
            # XOR + AND mask bmp frame
            im = BmpImagePlugin.DibImageFile(self.buf)

            # change tile dimension to only encompass XOR image
            im.size = (im.size[0], int(im.size[1] / 2))
            d, e, o, a = im.tile[0]
            im.tile[0] = d, (0,0) + im.size, o, a

            # figure out where AND mask image starts
            mode = a[0]
            bpp = 8
            for k in BmpImagePlugin.BIT2MODE.keys():
                if mode == BmpImagePlugin.BIT2MODE[k][1]:
                    bpp = k
                    break

            if 32 == bpp:
                # 32-bit color depth icon image allows semitransparent areas
                # PIL's DIB format ignores transparency bits, recover them
                # The DIB is packed in BGRX byte order where X is the alpha channel

                # Back up to start of bmp data
                self.buf.seek(o)
                # extract every 4th byte (eg. 3,7,11,15,...)
                alpha_bytes = self.buf.read(im.size[0] * im.size[1] * 4)[3::4]

                # convert to an 8bpp grayscale image
                mask = Image.frombuffer(
                    'L',            # 8bpp
                    im.size,        # (w, h)
                    alpha_bytes,    # source chars
                    'raw',          # raw decoder
                    ('L', 0, -1)    # 8bpp inverted, unpadded, reversed
                )
            else:
                # get AND image from end of bitmap
                w = im.size[0]
                if (w % 32) > 0:
                    # bitmap row data is aligned to word boundaries
                    w += 32 - (im.size[0] % 32)

                # the total mask data is padded row size * height / bits per char

                and_mask_offset = o + int(im.size[0] * im.size[1] * (bpp / 8.0))
                total_bytes = int((w * im.size[1]) / 8)

                self.buf.seek(and_mask_offset)
                maskData = self.buf.read(total_bytes)

                # convert raw data to image
                mask = Image.frombuffer(
                    '1',            # 1 bpp
                    im.size,        # (w, h)
                    maskData,       # source chars
                    'raw',          # raw decoder
                    ('1;I', int(w/8), -1)  # 1bpp inverted, padded, reversed
                )

                # now we have two images, im is XOR image and mask is AND image

            # apply mask image as alpha channel
            im = im.convert('RGBA')
            im.putalpha(mask)

        return im

##
# Image plugin for Windows Icon files.

class IcoImageFile(ImageFile.ImageFile):
    """
    PIL read-only image support for Microsoft Windows .ico files.

    By default the largest resolution image in the file will be loaded. This can
    be changed by altering the 'size' attribute before calling 'load'.

    The info dictionary has a key 'sizes' that is a list of the sizes available
    in the icon file.

    Handles classic, XP and Vista icon formats.

    This plugin is a refactored version of Win32IconImagePlugin by Bryan Davis <casadebender@gmail.com>.
    https://code.google.com/p/casadebender/wiki/Win32IconImagePlugin
    """
    format = "ICO"
    format_description = "Windows Icon"

    def _open(self):
        self.ico = IcoFile(self.fp)
        self.info['sizes'] = self.ico.sizes()
        self.size = self.ico.entry[0]['dim']
        self.load()

    def load(self):
        im = self.ico.getimage(self.size)
        # if tile is PNG, it won't really be loaded yet
        im.load()
        self.im = im.im
        self.mode = im.mode
        self.size = im.size


    def load_seek(self):
        # Flage the ImageFile.Parser so that it just does all the decode at the end.
        pass
#
# --------------------------------------------------------------------

Image.register_open("ICO", IcoImageFile, _accept)
Image.register_extension("ICO", ".ico")

########NEW FILE########
__FILENAME__ = Image
#
# The Python Imaging Library.
# $Id$
#
# the Image class wrapper
#
# partial release history:
# 1995-09-09 fl   Created
# 1996-03-11 fl   PIL release 0.0 (proof of concept)
# 1996-04-30 fl   PIL release 0.1b1
# 1999-07-28 fl   PIL release 1.0 final
# 2000-06-07 fl   PIL release 1.1
# 2000-10-20 fl   PIL release 1.1.1
# 2001-05-07 fl   PIL release 1.1.2
# 2002-03-15 fl   PIL release 1.1.3
# 2003-05-10 fl   PIL release 1.1.4
# 2005-03-28 fl   PIL release 1.1.5
# 2006-12-02 fl   PIL release 1.1.6
# 2009-11-15 fl   PIL release 1.1.7
#
# Copyright (c) 1997-2009 by Secret Labs AB.  All rights reserved.
# Copyright (c) 1995-2009 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#

from __future__ import print_function

from PIL import VERSION, PILLOW_VERSION, _plugins

import warnings


class _imaging_not_installed:
    # module placeholder
    def __getattr__(self, id):
        raise ImportError("The _imaging C module is not installed")

try:
    # give Tk a chance to set up the environment, in case we're
    # using an _imaging module linked against libtcl/libtk (use
    # __import__ to hide this from naive packagers; we don't really
    # depend on Tk unless ImageTk is used, and that module already
    # imports Tkinter)
    __import__("FixTk")
except ImportError:
    pass

try:
    # If the _imaging C module is not present, you can still use
    # the "open" function to identify files, but you cannot load
    # them.  Note that other modules should not refer to _imaging
    # directly; import Image and use the Image.core variable instead.
    from PIL import _imaging as core
    if PILLOW_VERSION != getattr(core, 'PILLOW_VERSION', None):
        raise ImportError("The _imaging extension was built for another "
                          " version of Pillow or PIL")

except ImportError as v:
    core = _imaging_not_installed()
    # Explanations for ways that we know we might have an import error
    if str(v).startswith("Module use of python"):
        # The _imaging C module is present, but not compiled for
        # the right version (windows only).  Print a warning, if
        # possible.
        warnings.warn(
            "The _imaging extension was built for another version "
            "of Python.",
            RuntimeWarning
            )
    elif str(v).startswith("The _imaging extension"):
        warnings.warn(str(v), RuntimeWarning)
    elif "Symbol not found: _PyUnicodeUCS2_FromString" in str(v):
        warnings.warn(
            "The _imaging extension was built for Python with UCS2 support; "
            "recompile PIL or build Python --without-wide-unicode. ",
            RuntimeWarning
            )
    elif "Symbol not found: _PyUnicodeUCS4_FromString" in str(v):
        warnings.warn(
            "The _imaging extension was built for Python with UCS4 support; "
            "recompile PIL or build Python --with-wide-unicode. ",
            RuntimeWarning
            )
    # Fail here anyway. Don't let people run with a mostly broken Pillow.
    raise

try:
    import builtins
except ImportError:
    import __builtin__
    builtins = __builtin__

from PIL import ImageMode
from PIL._binary import i8
from PIL._util import isPath
from PIL._util import isStringType
from PIL._util import deferred_error

import os
import sys

# type stuff
import collections
import numbers

# works everywhere, win for pypy, not cpython
USE_CFFI_ACCESS = hasattr(sys, 'pypy_version_info')
try:
    import cffi
    HAS_CFFI = True
except:
    HAS_CFFI = False


def isImageType(t):
    """
    Checks if an object is an image object.

    .. warning::

       This function is for internal use only.

    :param t: object to check if it's an image
    :returns: True if the object is an image
    """
    return hasattr(t, "im")

#
# Debug level

DEBUG = 0

#
# Constants (also defined in _imagingmodule.c!)

NONE = 0

# transpose
FLIP_LEFT_RIGHT = 0
FLIP_TOP_BOTTOM = 1
ROTATE_90 = 2
ROTATE_180 = 3
ROTATE_270 = 4

# transforms
AFFINE = 0
EXTENT = 1
PERSPECTIVE = 2
QUAD = 3
MESH = 4

# resampling filters
NONE = 0
NEAREST = 0
ANTIALIAS = 1  # 3-lobed lanczos
LINEAR = BILINEAR = 2
CUBIC = BICUBIC = 3

# dithers
NONE = 0
NEAREST = 0
ORDERED = 1  # Not yet implemented
RASTERIZE = 2  # Not yet implemented
FLOYDSTEINBERG = 3  # default

# palettes/quantizers
WEB = 0
ADAPTIVE = 1

MEDIANCUT = 0
MAXCOVERAGE = 1
FASTOCTREE = 2

# categories
NORMAL = 0
SEQUENCE = 1
CONTAINER = 2

if hasattr(core, 'DEFAULT_STRATEGY'):
    DEFAULT_STRATEGY = core.DEFAULT_STRATEGY
    FILTERED = core.FILTERED
    HUFFMAN_ONLY = core.HUFFMAN_ONLY
    RLE = core.RLE
    FIXED = core.FIXED


# --------------------------------------------------------------------
# Registries

ID = []
OPEN = {}
MIME = {}
SAVE = {}
EXTENSION = {}

# --------------------------------------------------------------------
# Modes supported by this version

_MODEINFO = {
    # NOTE: this table will be removed in future versions.  use
    # getmode* functions or ImageMode descriptors instead.

    # official modes
    "1": ("L", "L", ("1",)),
    "L": ("L", "L", ("L",)),
    "I": ("L", "I", ("I",)),
    "F": ("L", "F", ("F",)),
    "P": ("RGB", "L", ("P",)),
    "RGB": ("RGB", "L", ("R", "G", "B")),
    "RGBX": ("RGB", "L", ("R", "G", "B", "X")),
    "RGBA": ("RGB", "L", ("R", "G", "B", "A")),
    "CMYK": ("RGB", "L", ("C", "M", "Y", "K")),
    "YCbCr": ("RGB", "L", ("Y", "Cb", "Cr")),
    "LAB": ("RGB", "L", ("L", "A", "B")),

    # Experimental modes include I;16, I;16L, I;16B, RGBa, BGR;15, and
    # BGR;24.  Use these modes only if you know exactly what you're
    # doing...

}

if sys.byteorder == 'little':
    _ENDIAN = '<'
else:
    _ENDIAN = '>'

_MODE_CONV = {
    # official modes
    "1": ('|b1', None),  # broken
    "L": ('|u1', None),
    "I": (_ENDIAN + 'i4', None),
    "F": (_ENDIAN + 'f4', None),
    "P": ('|u1', None),
    "RGB": ('|u1', 3),
    "RGBX": ('|u1', 4),
    "RGBA": ('|u1', 4),
    "CMYK": ('|u1', 4),
    "YCbCr": ('|u1', 3),
    "LAB": ('|u1', 3),  # UNDONE - unsigned |u1i1i1
    # I;16 == I;16L, and I;32 == I;32L
    "I;16": ('<u2', None),
    "I;16B": ('>u2', None),
    "I;16L": ('<u2', None),
    "I;16S": ('<i2', None),
    "I;16BS": ('>i2', None),
    "I;16LS": ('<i2', None),
    "I;32": ('<u4', None),
    "I;32B": ('>u4', None),
    "I;32L": ('<u4', None),
    "I;32S": ('<i4', None),
    "I;32BS": ('>i4', None),
    "I;32LS": ('<i4', None),
}


def _conv_type_shape(im):
    shape = im.size[1], im.size[0]
    typ, extra = _MODE_CONV[im.mode]
    if extra is None:
        return shape, typ
    else:
        return shape+(extra,), typ


MODES = sorted(_MODEINFO.keys())

# raw modes that may be memory mapped.  NOTE: if you change this, you
# may have to modify the stride calculation in map.c too!
_MAPMODES = ("L", "P", "RGBX", "RGBA", "CMYK", "I;16", "I;16L", "I;16B")


def getmodebase(mode):
    """
    Gets the "base" mode for given mode.  This function returns "L" for
    images that contain grayscale data, and "RGB" for images that
    contain color data.

    :param mode: Input mode.
    :returns: "L" or "RGB".
    :exception KeyError: If the input mode was not a standard mode.
    """
    return ImageMode.getmode(mode).basemode


def getmodetype(mode):
    """
    Gets the storage type mode.  Given a mode, this function returns a
    single-layer mode suitable for storing individual bands.

    :param mode: Input mode.
    :returns: "L", "I", or "F".
    :exception KeyError: If the input mode was not a standard mode.
    """
    return ImageMode.getmode(mode).basetype


def getmodebandnames(mode):
    """
    Gets a list of individual band names.  Given a mode, this function returns
    a tuple containing the names of individual bands (use
    :py:method:`~PIL.Image.getmodetype` to get the mode used to store each
    individual band.

    :param mode: Input mode.
    :returns: A tuple containing band names.  The length of the tuple
        gives the number of bands in an image of the given mode.
    :exception KeyError: If the input mode was not a standard mode.
    """
    return ImageMode.getmode(mode).bands


def getmodebands(mode):
    """
    Gets the number of individual bands for this mode.

    :param mode: Input mode.
    :returns: The number of bands in this mode.
    :exception KeyError: If the input mode was not a standard mode.
    """
    return len(ImageMode.getmode(mode).bands)

# --------------------------------------------------------------------
# Helpers

_initialized = 0


def preinit():
    "Explicitly load standard file format drivers."

    global _initialized
    if _initialized >= 1:
        return

    try:
        from PIL import BmpImagePlugin
    except ImportError:
        pass
    try:
        from PIL import GifImagePlugin
    except ImportError:
        pass
    try:
        from PIL import JpegImagePlugin
    except ImportError:
        pass
    try:
        from PIL import PpmImagePlugin
    except ImportError:
        pass
    try:
        from PIL import PngImagePlugin
    except ImportError:
        pass
#   try:
#       import TiffImagePlugin
#   except ImportError:
#       pass

    _initialized = 1


def init():
    """
    Explicitly initializes the Python Imaging Library. This function
    loads all available file format drivers.
    """

    global _initialized
    if _initialized >= 2:
        return 0

    for plugin in _plugins:
        try:
            if DEBUG:
                print ("Importing %s" % plugin)
            __import__("PIL.%s" % plugin, globals(), locals(), [])
        except ImportError:
            if DEBUG:
                print("Image: failed to import", end=' ')
                print(plugin, ":", sys.exc_info()[1])

    if OPEN or SAVE:
        _initialized = 2
        return 1


# --------------------------------------------------------------------
# Codec factories (used by tobytes/frombytes and ImageFile.load)

def _getdecoder(mode, decoder_name, args, extra=()):

    # tweak arguments
    if args is None:
        args = ()
    elif not isinstance(args, tuple):
        args = (args,)

    try:
        # get decoder
        decoder = getattr(core, decoder_name + "_decoder")
        # print(decoder, mode, args + extra)
        return decoder(mode, *args + extra)
    except AttributeError:
        raise IOError("decoder %s not available" % decoder_name)


def _getencoder(mode, encoder_name, args, extra=()):

    # tweak arguments
    if args is None:
        args = ()
    elif not isinstance(args, tuple):
        args = (args,)

    try:
        # get encoder
        encoder = getattr(core, encoder_name + "_encoder")
        # print(encoder, mode, args + extra)
        return encoder(mode, *args + extra)
    except AttributeError:
        raise IOError("encoder %s not available" % encoder_name)


# --------------------------------------------------------------------
# Simple expression analyzer

def coerce_e(value):
    return value if isinstance(value, _E) else _E(value)


class _E:
    def __init__(self, data):
        self.data = data

    def __add__(self, other):
        return _E((self.data, "__add__", coerce_e(other).data))

    def __mul__(self, other):
        return _E((self.data, "__mul__", coerce_e(other).data))


def _getscaleoffset(expr):
    stub = ["stub"]
    data = expr(_E(stub)).data
    try:
        (a, b, c) = data  # simplified syntax
        if (a is stub and b == "__mul__" and isinstance(c, numbers.Number)):
            return c, 0.0
        if (a is stub and b == "__add__" and isinstance(c, numbers.Number)):
            return 1.0, c
    except TypeError:
        pass
    try:
        ((a, b, c), d, e) = data  # full syntax
        if (a is stub and b == "__mul__" and isinstance(c, numbers.Number) and
                d == "__add__" and isinstance(e, numbers.Number)):
            return c, e
    except TypeError:
        pass
    raise ValueError("illegal expression")


# --------------------------------------------------------------------
# Implementation wrapper

class Image:
    """
    This class represents an image object.  To create
    :py:class:`~PIL.Image.Image` objects, use the appropriate factory
    functions.  There's hardly ever any reason to call the Image constructor
    directly.

    * :py:func:`~PIL.Image.open`
    * :py:func:`~PIL.Image.new`
    * :py:func:`~PIL.Image.frombytes`
    """
    format = None
    format_description = None

    def __init__(self):
        # FIXME: take "new" parameters / other image?
        # FIXME: turn mode and size into delegating properties?
        self.im = None
        self.mode = ""
        self.size = (0, 0)
        self.palette = None
        self.info = {}
        self.category = NORMAL
        self.readonly = 0
        self.pyaccess = None

    def _new(self, im):
        new = Image()
        new.im = im
        new.mode = im.mode
        new.size = im.size
        new.palette = self.palette
        if im.mode == "P" and not new.palette:
            from PIL import ImagePalette
            new.palette = ImagePalette.ImagePalette()
        try:
            new.info = self.info.copy()
        except AttributeError:
            # fallback (pre-1.5.2)
            new.info = {}
            for k, v in self.info:
                new.info[k] = v
        return new

    _makeself = _new  # compatibility

    # Context Manager Support
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        """
        Closes the file pointer, if possible.

        This operation will destroy the image core and release it's memory.
        The image data will be unusable afterward.

        This function is only required to close images that have not
        had their file read and closed by the
        :py:meth:`~PIL.Image.Image.load` method.
        """
        try:
            self.fp.close()
        except Exception as msg:
            if Image.DEBUG:
                print ("Error closing: %s" % msg)

        # Instead of simply setting to None, we're setting up a
        # deferred error that will better explain that the core image
        # object is gone.
        self.im = deferred_error(ValueError("Operation on closed image"))

    def _copy(self):
        self.load()
        self.im = self.im.copy()
        self.pyaccess = None
        self.readonly = 0

    def _dump(self, file=None, format=None):
        import os
        import tempfile
        suffix = ''
        if format:
            suffix = '.'+format
        if not file:
            f, file = tempfile.mkstemp(suffix)
            os.close(f)

        self.load()
        if not format or format == "PPM":
            self.im.save_ppm(file)
        else:
            if not file.endswith(format):
                file = file + "." + format
            self.save(file, format)
        return file

    def __eq__(self, other):
        a = (self.mode == other.mode)
        b = (self.size == other.size)
        c = (self.getpalette() == other.getpalette())
        d = (self.info == other.info)
        e = (self.category == other.category)
        f = (self.readonly == other.readonly)
        g = (self.tobytes() == other.tobytes())
        return a and b and c and d and e and f and g

    def __ne__(self, other):
        eq = (self == other)
        return not eq

    def __repr__(self):
        return "<%s.%s image mode=%s size=%dx%d at 0x%X>" % (
            self.__class__.__module__, self.__class__.__name__,
            self.mode, self.size[0], self.size[1],
            id(self)
            )

    def __getattr__(self, name):
        if name == "__array_interface__":
            # numpy array interface support
            new = {}
            shape, typestr = _conv_type_shape(self)
            new['shape'] = shape
            new['typestr'] = typestr
            new['data'] = self.tobytes()
            return new
        raise AttributeError(name)

    def __getstate__(self):
        return [
            self.info,
            self.mode,
            self.size,
            self.getpalette(),
            self.tobytes()]

    def __setstate__(self, state):
        Image.__init__(self)
        self.tile = []
        info, mode, size, palette, data = state
        self.info = info
        self.mode = mode
        self.size = size
        self.im = core.new(mode, size)
        if mode in ("L", "P"):
            self.putpalette(palette)
        self.frombytes(data)

    def tobytes(self, encoder_name="raw", *args):
        """
        Return image as a bytes object

        :param encoder_name: What encoder to use.  The default is to
                             use the standard "raw" encoder.
        :param args: Extra arguments to the encoder.
        :rtype: A bytes object.
        """

        # may pass tuple instead of argument list
        if len(args) == 1 and isinstance(args[0], tuple):
            args = args[0]

        if encoder_name == "raw" and args == ():
            args = self.mode

        self.load()

        # unpack data
        e = _getencoder(self.mode, encoder_name, args)
        e.setimage(self.im)

        bufsize = max(65536, self.size[0] * 4)  # see RawEncode.c

        data = []
        while True:
            l, s, d = e.encode(bufsize)
            data.append(d)
            if s:
                break
        if s < 0:
            raise RuntimeError("encoder error %d in tobytes" % s)

        return b"".join(data)

    # Declare tostring as alias to tobytes
    def tostring(self, *args, **kw):
        warnings.warn(
            'tostring() is deprecated. Please call tobytes() instead.',
            DeprecationWarning,
            stacklevel=2,
        )
        return self.tobytes(*args, **kw)

    def tobitmap(self, name="image"):
        """
        Returns the image converted to an X11 bitmap.

        .. note:: This method only works for mode "1" images.

        :param name: The name prefix to use for the bitmap variables.
        :returns: A string containing an X11 bitmap.
        :raises ValueError: If the mode is not "1"
        """

        self.load()
        if self.mode != "1":
            raise ValueError("not a bitmap")
        data = self.tobytes("xbm")
        return b"".join([
            ("#define %s_width %d\n" % (name, self.size[0])).encode('ascii'),
            ("#define %s_height %d\n" % (name, self.size[1])).encode('ascii'),
            ("static char %s_bits[] = {\n" % name).encode('ascii'), data, b"};"
            ])

    def frombytes(self, data, decoder_name="raw", *args):
        """
        Loads this image with pixel data from a bytes object.

        This method is similar to the :py:func:`~PIL.Image.frombytes` function,
        but loads data into this image instead of creating a new image object.
        """

        # may pass tuple instead of argument list
        if len(args) == 1 and isinstance(args[0], tuple):
            args = args[0]

        # default format
        if decoder_name == "raw" and args == ():
            args = self.mode

        # unpack data
        d = _getdecoder(self.mode, decoder_name, args)
        d.setimage(self.im)
        s = d.decode(data)

        if s[0] >= 0:
            raise ValueError("not enough image data")
        if s[1] != 0:
            raise ValueError("cannot decode image data")

    def fromstring(self, *args, **kw):
        """Deprecated alias to frombytes.

        .. deprecated:: 2.0
        """
        warnings.warn(
            'fromstring() is deprecated. Please call frombytes() instead.',
            DeprecationWarning)
        return self.frombytes(*args, **kw)

    def load(self):
        """
        Allocates storage for the image and loads the pixel data.  In
        normal cases, you don't need to call this method, since the
        Image class automatically loads an opened image when it is
        accessed for the first time. This method will close the file
        associated with the image.

        :returns: An image access object.
        """
        if self.im and self.palette and self.palette.dirty:
            # realize palette
            self.im.putpalette(*self.palette.getdata())
            self.palette.dirty = 0
            self.palette.mode = "RGB"
            self.palette.rawmode = None
            if "transparency" in self.info:
                if isinstance(self.info["transparency"], int):
                    self.im.putpalettealpha(self.info["transparency"], 0)
                else:
                    self.im.putpalettealphas(self.info["transparency"])
                self.palette.mode = "RGBA"

        if self.im:
            if HAS_CFFI and USE_CFFI_ACCESS:
                if self.pyaccess:
                    return self.pyaccess
                from PIL import PyAccess
                self.pyaccess = PyAccess.new(self, self.readonly)
                if self.pyaccess:
                    return self.pyaccess
            return self.im.pixel_access(self.readonly)

    def verify(self):
        """
        Verifies the contents of a file. For data read from a file, this
        method attempts to determine if the file is broken, without
        actually decoding the image data.  If this method finds any
        problems, it raises suitable exceptions.  If you need to load
        the image after using this method, you must reopen the image
        file.
        """
        pass

    def convert(self, mode=None, matrix=None, dither=None,
                palette=WEB, colors=256):
        """
        Returns a converted copy of this image. For the "P" mode, this
        method translates pixels through the palette.  If mode is
        omitted, a mode is chosen so that all information in the image
        and the palette can be represented without a palette.

        The current version supports all possible conversions between
        "L", "RGB" and "CMYK." The **matrix** argument only supports "L"
        and "RGB".

        When translating a color image to black and white (mode "L"),
        the library uses the ITU-R 601-2 luma transform::

            L = R * 299/1000 + G * 587/1000 + B * 114/1000

        The default method of converting a greyscale ("L") or "RGB"
        image into a bilevel (mode "1") image uses Floyd-Steinberg
        dither to approximate the original image luminosity levels. If
        dither is NONE, all non-zero values are set to 255 (white). To
        use other thresholds, use the :py:meth:`~PIL.Image.Image.point`
        method.

        :param mode: The requested mode.
        :param matrix: An optional conversion matrix.  If given, this
           should be 4- or 16-tuple containing floating point values.
        :param dither: Dithering method, used when converting from
           mode "RGB" to "P" or from "RGB" or "L" to "1".
           Available methods are NONE or FLOYDSTEINBERG (default).
        :param palette: Palette to use when converting from mode "RGB"
           to "P".  Available palettes are WEB or ADAPTIVE.
        :param colors: Number of colors to use for the ADAPTIVE palette.
           Defaults to 256.
        :rtype: :py:class:`~PIL.Image.Image`
        :returns: An :py:class:`~PIL.Image.Image` object.
        """

        if not mode:
            # determine default mode
            if self.mode == "P":
                self.load()
                if self.palette:
                    mode = self.palette.mode
                else:
                    mode = "RGB"
            else:
                return self.copy()

        self.load()

        if matrix:
            # matrix conversion
            if mode not in ("L", "RGB"):
                raise ValueError("illegal conversion")
            im = self.im.convert_matrix(mode, matrix)
            return self._new(im)

        if mode == "P" and self.mode == "RGBA":
            return self.quantize(colors)

        trns = None
        delete_trns = False
        # transparency handling
        if "transparency" in self.info and \
                self.info['transparency'] is not None:
            if self.mode in ('L', 'RGB') and mode == 'RGBA':
                # Use transparent conversion to promote from transparent
                # color to an alpha channel.
                return self._new(self.im.convert_transparent(
                    mode, self.info['transparency']))
            elif self.mode in ('L', 'RGB', 'P') and mode in ('L', 'RGB', 'P'):
                t = self.info['transparency']
                if isinstance(t, bytes):
                    # Dragons. This can't be represented by a single color
                    warnings.warn('Palette images with Transparency expressed ' +
                                  ' in bytes should be converted to RGBA images')
                    delete_trns = True
                else:
                    # get the new transparency color.
                    # use existing conversions
                    trns_im = Image()._new(core.new(self.mode, (1, 1)))
                    if self.mode == 'P':
                        trns_im.putpalette(self.palette)
                    trns_im.putpixel((0, 0), t)

                    if mode in ('L', 'RGB'):
                        trns_im = trns_im.convert(mode)
                    else:
                        # can't just retrieve the palette number, got to do it
                        # after quantization.
                        trns_im = trns_im.convert('RGB')
                    trns = trns_im.getpixel((0,0))

            elif self.mode == 'P' and mode == 'RGBA':
                delete_trns = True

        if mode == "P" and palette == ADAPTIVE:
            im = self.im.quantize(colors)
            new = self._new(im)
            from PIL import ImagePalette
            new.palette = ImagePalette.raw("RGB", new.im.getpalette("RGB"))
            if delete_trns:
                # This could possibly happen if we requantize to fewer colors.
                # The transparency would be totally off in that case.
                del(new.info['transparency'])
            if trns is not None:
                try:
                    new.info['transparency'] = new.palette.getcolor(trns)
                except:
                    # if we can't make a transparent color, don't leave the old
                    # transparency hanging around to mess us up.
                    del(new.info['transparency'])
                    warnings.warn("Couldn't allocate palette entry " +
                                  "for transparency")
            return new

        # colorspace conversion
        if dither is None:
            dither = FLOYDSTEINBERG

        try:
            im = self.im.convert(mode, dither)
        except ValueError:
            try:
                # normalize source image and try again
                im = self.im.convert(getmodebase(self.mode))
                im = im.convert(mode, dither)
            except KeyError:
                raise ValueError("illegal conversion")

        new_im = self._new(im)
        if delete_trns:
            # crash fail if we leave a bytes transparency in an rgb/l mode.
            del(new_im.info['transparency'])
        if trns is not None:
            if new_im.mode == 'P':
                try:
                    new_im.info['transparency'] = new_im.palette.getcolor(trns)
                except:
                    del(new_im.info['transparency'])
                    warnings.warn("Couldn't allocate palette entry " +
                                  "for transparency")
            else:
                new_im.info['transparency'] = trns
        return new_im

    def quantize(self, colors=256, method=None, kmeans=0, palette=None):

        # methods:
        #    0 = median cut
        #    1 = maximum coverage
        #    2 = fast octree

        # NOTE: this functionality will be moved to the extended
        # quantizer interface in a later version of PIL.

        self.load()

        if method is None:
            # defaults:
            method = 0
            if self.mode == 'RGBA':
                method = 2

        if self.mode == 'RGBA' and method != 2:
            # Caller specified an invalid mode.
            raise ValueError('Fast Octree (method == 2) is the ' +
                             ' only valid method for quantizing RGBA images')

        if palette:
            # use palette from reference image
            palette.load()
            if palette.mode != "P":
                raise ValueError("bad mode for palette image")
            if self.mode != "RGB" and self.mode != "L":
                raise ValueError(
                    "only RGB or L mode images can be quantized to a palette"
                    )
            im = self.im.convert("P", 1, palette.im)
            return self._makeself(im)

        im = self.im.quantize(colors, method, kmeans)
        return self._new(im)

    def copy(self):
        """
        Copies this image. Use this method if you wish to paste things
        into an image, but still retain the original.

        :rtype: :py:class:`~PIL.Image.Image`
        :returns: An :py:class:`~PIL.Image.Image` object.
        """
        self.load()
        im = self.im.copy()
        return self._new(im)

    def crop(self, box=None):
        """
        Returns a rectangular region from this image. The box is a
        4-tuple defining the left, upper, right, and lower pixel
        coordinate.

        This is a lazy operation.  Changes to the source image may or
        may not be reflected in the cropped image.  To break the
        connection, call the :py:meth:`~PIL.Image.Image.load` method on
        the cropped copy.

        :param box: The crop rectangle, as a (left, upper, right, lower)-tuple.
        :rtype: :py:class:`~PIL.Image.Image`
        :returns: An :py:class:`~PIL.Image.Image` object.
        """

        self.load()
        if box is None:
            return self.copy()

        # lazy operation
        return _ImageCrop(self, box)

    def draft(self, mode, size):
        """
        NYI

        Configures the image file loader so it returns a version of the
        image that as closely as possible matches the given mode and
        size.  For example, you can use this method to convert a color
        JPEG to greyscale while loading it, or to extract a 128x192
        version from a PCD file.

        Note that this method modifies the :py:class:`~PIL.Image.Image` object
        in place.  If the image has already been loaded, this method has no
        effect.

        :param mode: The requested mode.
        :param size: The requested size.
        """
        pass

    def _expand(self, xmargin, ymargin=None):
        if ymargin is None:
            ymargin = xmargin
        self.load()
        return self._new(self.im.expand(xmargin, ymargin, 0))

    def filter(self, filter):
        """
        Filters this image using the given filter.  For a list of
        available filters, see the :py:mod:`~PIL.ImageFilter` module.

        :param filter: Filter kernel.
        :returns: An :py:class:`~PIL.Image.Image` object.  """

        self.load()

        if isinstance(filter, collections.Callable):
            filter = filter()
        if not hasattr(filter, "filter"):
            raise TypeError("filter argument should be ImageFilter.Filter " +
                            "instance or class")

        if self.im.bands == 1:
            return self._new(filter.filter(self.im))
        # fix to handle multiband images since _imaging doesn't
        ims = []
        for c in range(self.im.bands):
            ims.append(self._new(filter.filter(self.im.getband(c))))
        return merge(self.mode, ims)

    def getbands(self):
        """
        Returns a tuple containing the name of each band in this image.
        For example, **getbands** on an RGB image returns ("R", "G", "B").

        :returns: A tuple containing band names.
        :rtype: tuple
        """
        return ImageMode.getmode(self.mode).bands

    def getbbox(self):
        """
        Calculates the bounding box of the non-zero regions in the
        image.

        :returns: The bounding box is returned as a 4-tuple defining the
           left, upper, right, and lower pixel coordinate. If the image
           is completely empty, this method returns None.

        """

        self.load()
        return self.im.getbbox()

    def getcolors(self, maxcolors=256):
        """
        Returns a list of colors used in this image.

        :param maxcolors: Maximum number of colors.  If this number is
           exceeded, this method returns None.  The default limit is
           256 colors.
        :returns: An unsorted list of (count, pixel) values.
        """

        self.load()
        if self.mode in ("1", "L", "P"):
            h = self.im.histogram()
            out = []
            for i in range(256):
                if h[i]:
                    out.append((h[i], i))
            if len(out) > maxcolors:
                return None
            return out
        return self.im.getcolors(maxcolors)

    def getdata(self, band=None):
        """
        Returns the contents of this image as a sequence object
        containing pixel values.  The sequence object is flattened, so
        that values for line one follow directly after the values of
        line zero, and so on.

        Note that the sequence object returned by this method is an
        internal PIL data type, which only supports certain sequence
        operations.  To convert it to an ordinary sequence (e.g. for
        printing), use **list(im.getdata())**.

        :param band: What band to return.  The default is to return
           all bands.  To return a single band, pass in the index
           value (e.g. 0 to get the "R" band from an "RGB" image).
        :returns: A sequence-like object.
        """

        self.load()
        if band is not None:
            return self.im.getband(band)
        return self.im  # could be abused

    def getextrema(self):
        """
        Gets the the minimum and maximum pixel values for each band in
        the image.

        :returns: For a single-band image, a 2-tuple containing the
           minimum and maximum pixel value.  For a multi-band image,
           a tuple containing one 2-tuple for each band.
        """

        self.load()
        if self.im.bands > 1:
            extrema = []
            for i in range(self.im.bands):
                extrema.append(self.im.getband(i).getextrema())
            return tuple(extrema)
        return self.im.getextrema()

    def getim(self):
        """
        Returns a capsule that points to the internal image memory.

        :returns: A capsule object.
        """

        self.load()
        return self.im.ptr

    def getpalette(self):
        """
        Returns the image palette as a list.

        :returns: A list of color values [r, g, b, ...], or None if the
           image has no palette.
        """

        self.load()
        try:
            if bytes is str:
                return [i8(c) for c in self.im.getpalette()]
            else:
                return list(self.im.getpalette())
        except ValueError:
            return None  # no palette

    def getpixel(self, xy):
        """
        Returns the pixel value at a given position.

        :param xy: The coordinate, given as (x, y).
        :returns: The pixel value.  If the image is a multi-layer image,
           this method returns a tuple.
        """

        self.load()
        if self.pyaccess:
            return self.pyaccess.getpixel(xy)
        return self.im.getpixel(xy)

    def getprojection(self):
        """
        Get projection to x and y axes

        :returns: Two sequences, indicating where there are non-zero
            pixels along the X-axis and the Y-axis, respectively.
        """

        self.load()
        x, y = self.im.getprojection()
        return [i8(c) for c in x], [i8(c) for c in y]

    def histogram(self, mask=None, extrema=None):
        """
        Returns a histogram for the image. The histogram is returned as
        a list of pixel counts, one for each pixel value in the source
        image. If the image has more than one band, the histograms for
        all bands are concatenated (for example, the histogram for an
        "RGB" image contains 768 values).

        A bilevel image (mode "1") is treated as a greyscale ("L") image
        by this method.

        If a mask is provided, the method returns a histogram for those
        parts of the image where the mask image is non-zero. The mask
        image must have the same size as the image, and be either a
        bi-level image (mode "1") or a greyscale image ("L").

        :param mask: An optional mask.
        :returns: A list containing pixel counts.
        """
        self.load()
        if mask:
            mask.load()
            return self.im.histogram((0, 0), mask.im)
        if self.mode in ("I", "F"):
            if extrema is None:
                extrema = self.getextrema()
            return self.im.histogram(extrema)
        return self.im.histogram()

    def offset(self, xoffset, yoffset=None):
        """
        .. deprecated:: 2.0

        .. note:: New code should use :py:func:`PIL.ImageChops.offset`.

        Returns a copy of the image where the data has been offset by the given
        distances. Data wraps around the edges. If **yoffset** is omitted, it
        is assumed to be equal to **xoffset**.

        :param xoffset: The horizontal distance.
        :param yoffset: The vertical distance.  If omitted, both
           distances are set to the same value.
        :returns: An :py:class:`~PIL.Image.Image` object.
        """
        if warnings:
            warnings.warn(
                "'offset' is deprecated; use 'ImageChops.offset' instead",
                DeprecationWarning, stacklevel=2
                )
        from PIL import ImageChops
        return ImageChops.offset(self, xoffset, yoffset)

    def paste(self, im, box=None, mask=None):
        """
        Pastes another image into this image. The box argument is either
        a 2-tuple giving the upper left corner, a 4-tuple defining the
        left, upper, right, and lower pixel coordinate, or None (same as
        (0, 0)).  If a 4-tuple is given, the size of the pasted image
        must match the size of the region.

        If the modes don't match, the pasted image is converted to the mode of
        this image (see the :py:meth:`~PIL.Image.Image.convert` method for
        details).

        Instead of an image, the source can be a integer or tuple
        containing pixel values.  The method then fills the region
        with the given color.  When creating RGB images, you can
        also use color strings as supported by the ImageColor module.

        If a mask is given, this method updates only the regions
        indicated by the mask.  You can use either "1", "L" or "RGBA"
        images (in the latter case, the alpha band is used as mask).
        Where the mask is 255, the given image is copied as is.  Where
        the mask is 0, the current value is preserved.  Intermediate
        values can be used for transparency effects.

        Note that if you paste an "RGBA" image, the alpha band is
        ignored.  You can work around this by using the same image as
        both source image and mask.

        :param im: Source image or pixel value (integer or tuple).
        :param box: An optional 4-tuple giving the region to paste into.
           If a 2-tuple is used instead, it's treated as the upper left
           corner.  If omitted or None, the source is pasted into the
           upper left corner.

           If an image is given as the second argument and there is no
           third, the box defaults to (0, 0), and the second argument
           is interpreted as a mask image.
        :param mask: An optional mask image.
        """

        if isImageType(box) and mask is None:
            # abbreviated paste(im, mask) syntax
            mask = box
            box = None

        if box is None:
            # cover all of self
            box = (0, 0) + self.size

        if len(box) == 2:
            # lower left corner given; get size from image or mask
            if isImageType(im):
                size = im.size
            elif isImageType(mask):
                size = mask.size
            else:
                # FIXME: use self.size here?
                raise ValueError(
                    "cannot determine region size; use 4-item box"
                    )
            box = box + (box[0]+size[0], box[1]+size[1])

        if isStringType(im):
            from PIL import ImageColor
            im = ImageColor.getcolor(im, self.mode)

        elif isImageType(im):
            im.load()
            if self.mode != im.mode:
                if self.mode != "RGB" or im.mode not in ("RGBA", "RGBa"):
                    # should use an adapter for this!
                    im = im.convert(self.mode)
            im = im.im

        self.load()
        if self.readonly:
            self._copy()

        if mask:
            mask.load()
            self.im.paste(im, box, mask.im)
        else:
            self.im.paste(im, box)

    def point(self, lut, mode=None):
        """
        Maps this image through a lookup table or function.

        :param lut: A lookup table, containing 256 (or 65336 if
           self.mode=="I" and mode == "L") values per band in the
           image.  A function can be used instead, it should take a
           single argument. The function is called once for each
           possible pixel value, and the resulting table is applied to
           all bands of the image.
        :param mode: Output mode (default is same as input).  In the
           current version, this can only be used if the source image
           has mode "L" or "P", and the output has mode "1" or the
           source image mode is "I" and the output mode is "L".
        :returns: An :py:class:`~PIL.Image.Image` object.
        """

        self.load()

        if isinstance(lut, ImagePointHandler):
            return lut.point(self)

        if callable(lut):
            # if it isn't a list, it should be a function
            if self.mode in ("I", "I;16", "F"):
                # check if the function can be used with point_transform
                # UNDONE wiredfool -- I think this prevents us from ever doing
                # a gamma function point transform on > 8bit images.
                scale, offset = _getscaleoffset(lut)
                return self._new(self.im.point_transform(scale, offset))
            # for other modes, convert the function to a table
            lut = [lut(i) for i in range(256)] * self.im.bands

        if self.mode == "F":
            # FIXME: _imaging returns a confusing error message for this case
            raise ValueError("point operation not supported for this mode")

        return self._new(self.im.point(lut, mode))

    def putalpha(self, alpha):
        """
        Adds or replaces the alpha layer in this image.  If the image
        does not have an alpha layer, it's converted to "LA" or "RGBA".
        The new layer must be either "L" or "1".

        :param alpha: The new alpha layer.  This can either be an "L" or "1"
           image having the same size as this image, or an integer or
           other color value.
        """

        self.load()
        if self.readonly:
            self._copy()

        if self.mode not in ("LA", "RGBA"):
            # attempt to promote self to a matching alpha mode
            try:
                mode = getmodebase(self.mode) + "A"
                try:
                    self.im.setmode(mode)
                    self.pyaccess = None
                except (AttributeError, ValueError):
                    # do things the hard way
                    im = self.im.convert(mode)
                    if im.mode not in ("LA", "RGBA"):
                        raise ValueError  # sanity check
                    self.im = im
                    self.pyaccess = None
                self.mode = self.im.mode
            except (KeyError, ValueError):
                raise ValueError("illegal image mode")

        if self.mode == "LA":
            band = 1
        else:
            band = 3

        if isImageType(alpha):
            # alpha layer
            if alpha.mode not in ("1", "L"):
                raise ValueError("illegal image mode")
            alpha.load()
            if alpha.mode == "1":
                alpha = alpha.convert("L")
        else:
            # constant alpha
            try:
                self.im.fillband(band, alpha)
            except (AttributeError, ValueError):
                # do things the hard way
                alpha = new("L", self.size, alpha)
            else:
                return

        self.im.putband(alpha.im, band)

    def putdata(self, data, scale=1.0, offset=0.0):
        """
        Copies pixel data to this image.  This method copies data from a
        sequence object into the image, starting at the upper left
        corner (0, 0), and continuing until either the image or the
        sequence ends.  The scale and offset values are used to adjust
        the sequence values: **pixel = value*scale + offset**.

        :param data: A sequence object.
        :param scale: An optional scale value.  The default is 1.0.
        :param offset: An optional offset value.  The default is 0.0.
        """

        self.load()
        if self.readonly:
            self._copy()

        self.im.putdata(data, scale, offset)

    def putpalette(self, data, rawmode="RGB"):
        """
        Attaches a palette to this image.  The image must be a "P" or
        "L" image, and the palette sequence must contain 768 integer
        values, where each group of three values represent the red,
        green, and blue values for the corresponding pixel
        index. Instead of an integer sequence, you can use an 8-bit
        string.

        :param data: A palette sequence (either a list or a string).
        """
        from PIL import ImagePalette

        if self.mode not in ("L", "P"):
            raise ValueError("illegal image mode")
        self.load()
        if isinstance(data, ImagePalette.ImagePalette):
            palette = ImagePalette.raw(data.rawmode, data.palette)
        else:
            if not isinstance(data, bytes):
                if bytes is str:
                    data = "".join(chr(x) for x in data)
                else:
                    data = bytes(data)
            palette = ImagePalette.raw(rawmode, data)
        self.mode = "P"
        self.palette = palette
        self.palette.mode = "RGB"
        self.load()  # install new palette

    def putpixel(self, xy, value):
        """
        Modifies the pixel at the given position. The color is given as
        a single numerical value for single-band images, and a tuple for
        multi-band images.

        Note that this method is relatively slow.  For more extensive changes,
        use :py:meth:`~PIL.Image.Image.paste` or the :py:mod:`~PIL.ImageDraw`
        module instead.

        See:

        * :py:meth:`~PIL.Image.Image.paste`
        * :py:meth:`~PIL.Image.Image.putdata`
        * :py:mod:`~PIL.ImageDraw`

        :param xy: The pixel coordinate, given as (x, y).
        :param value: The pixel value.
        """

        self.load()
        if self.readonly:
            self._copy()
            self.pyaccess = None
            self.load()

        if self.pyaccess:
            return self.pyaccess.putpixel(xy, value)
        return self.im.putpixel(xy, value)

    def resize(self, size, resample=NEAREST):
        """
        Returns a resized copy of this image.

        :param size: The requested size in pixels, as a 2-tuple:
           (width, height).
        :param resample: An optional resampling filter.  This can be
           one of :py:attr:`PIL.Image.NEAREST` (use nearest neighbour),
           :py:attr:`PIL.Image.BILINEAR` (linear interpolation in a 2x2
           environment), :py:attr:`PIL.Image.BICUBIC` (cubic spline
           interpolation in a 4x4 environment), or
           :py:attr:`PIL.Image.ANTIALIAS` (a high-quality downsampling filter).
           If omitted, or if the image has mode "1" or "P", it is
           set :py:attr:`PIL.Image.NEAREST`.
        :returns: An :py:class:`~PIL.Image.Image` object.
        """

        if resample not in (NEAREST, BILINEAR, BICUBIC, ANTIALIAS):
            raise ValueError("unknown resampling filter")

        self.load()

        if self.mode in ("1", "P"):
            resample = NEAREST

        if self.mode == 'RGBA':
            return self.convert('RGBa').resize(size, resample).convert('RGBA')

        if resample == ANTIALIAS:
            # requires stretch support (imToolkit & PIL 1.1.3)
            try:
                im = self.im.stretch(size, resample)
            except AttributeError:
                raise ValueError("unsupported resampling filter")
        else:
            im = self.im.resize(size, resample)

        return self._new(im)

    def rotate(self, angle, resample=NEAREST, expand=0):
        """
        Returns a rotated copy of this image.  This method returns a
        copy of this image, rotated the given number of degrees counter
        clockwise around its centre.

        :param angle: In degrees counter clockwise.
        :param filter: An optional resampling filter.  This can be
           one of :py:attr:`PIL.Image.NEAREST` (use nearest neighbour),
           :py:attr:`PIL.Image.BILINEAR` (linear interpolation in a 2x2
           environment), or :py:attr:`PIL.Image.BICUBIC`
           (cubic spline interpolation in a 4x4 environment).
           If omitted, or if the image has mode "1" or "P", it is
           set :py:attr:`PIL.Image.NEAREST`.
        :param expand: Optional expansion flag.  If true, expands the output
           image to make it large enough to hold the entire rotated image.
           If false or omitted, make the output image the same size as the
           input image.
        :returns: An :py:class:`~PIL.Image.Image` object.
        """

        if expand:
            import math
            angle = -angle * math.pi / 180
            matrix = [
                math.cos(angle), math.sin(angle), 0.0,
                -math.sin(angle), math.cos(angle), 0.0
                ]
            

            def transform(x, y, matrix=matrix):
                (a, b, c, d, e, f) = matrix
                return a*x + b*y + c, d*x + e*y + f

            # calculate output size
            w, h = self.size
            xx = []
            yy = []
            for x, y in ((0, 0), (w, 0), (w, h), (0, h)):
                x, y = transform(x, y)
                xx.append(x)
                yy.append(y)
            w = int(math.ceil(max(xx)) - math.floor(min(xx)))
            h = int(math.ceil(max(yy)) - math.floor(min(yy)))

            # adjust center
            x, y = transform(w / 2.0, h / 2.0)
            matrix[2] = self.size[0] / 2.0 - x
            matrix[5] = self.size[1] / 2.0 - y

            return self.transform((w, h), AFFINE, matrix, resample)

        if resample not in (NEAREST, BILINEAR, BICUBIC):
            raise ValueError("unknown resampling filter")

        self.load()

        if self.mode in ("1", "P"):
            resample = NEAREST

        return self._new(self.im.rotate(angle, resample))

    def save(self, fp, format=None, **params):
        """
        Saves this image under the given filename.  If no format is
        specified, the format to use is determined from the filename
        extension, if possible.

        Keyword options can be used to provide additional instructions
        to the writer. If a writer doesn't recognise an option, it is
        silently ignored. The available options are described later in
        this handbook.

        You can use a file object instead of a filename. In this case,
        you must always specify the format. The file object must
        implement the **seek**, **tell**, and **write**
        methods, and be opened in binary mode.

        :param file: File name or file object.
        :param format: Optional format override.  If omitted, the
           format to use is determined from the filename extension.
           If a file object was used instead of a filename, this
           parameter should always be used.
        :param options: Extra parameters to the image writer.
        :returns: None
        :exception KeyError: If the output format could not be determined
           from the file name.  Use the format option to solve this.
        :exception IOError: If the file could not be written.  The file
           may have been created, and may contain partial data.
        """

        if isPath(fp):
            filename = fp
        else:
            if hasattr(fp, "name") and isPath(fp.name):
                filename = fp.name
            else:
                filename = ""

        # may mutate self!
        self.load()

        self.encoderinfo = params
        self.encoderconfig = ()

        preinit()

        ext = os.path.splitext(filename)[1].lower()

        if not format:
            try:
                format = EXTENSION[ext]
            except KeyError:
                init()
                try:
                    format = EXTENSION[ext]
                except KeyError:
                    raise KeyError(ext)  # unknown extension

        try:
            save_handler = SAVE[format.upper()]
        except KeyError:
            init()
            save_handler = SAVE[format.upper()]  # unknown format

        if isPath(fp):
            fp = builtins.open(fp, "wb")
            close = 1
        else:
            close = 0

        try:
            save_handler(self, fp, filename)
        finally:
            # do what we can to clean up
            if close:
                fp.close()

    def seek(self, frame):
        """
        Seeks to the given frame in this sequence file. If you seek
        beyond the end of the sequence, the method raises an
        **EOFError** exception. When a sequence file is opened, the
        library automatically seeks to frame 0.

        Note that in the current version of the library, most sequence
        formats only allows you to seek to the next frame.

        See :py:meth:`~PIL.Image.Image.tell`.

        :param frame: Frame number, starting at 0.
        :exception EOFError: If the call attempts to seek beyond the end
            of the sequence.
        """

        # overridden by file handlers
        if frame != 0:
            raise EOFError

    def show(self, title=None, command=None):
        """
        Displays this image. This method is mainly intended for
        debugging purposes.

        On Unix platforms, this method saves the image to a temporary
        PPM file, and calls the **xv** utility.

        On Windows, it saves the image to a temporary BMP file, and uses
        the standard BMP display utility to show it (usually Paint).

        :param title: Optional title to use for the image window,
           where possible.
        :param command: command used to show the image
        """

        _show(self, title=title, command=command)

    def split(self):
        """
        Split this image into individual bands. This method returns a
        tuple of individual image bands from an image. For example,
        splitting an "RGB" image creates three new images each
        containing a copy of one of the original bands (red, green,
        blue).

        :returns: A tuple containing bands.
        """

        self.load()
        if self.im.bands == 1:
            ims = [self.copy()]
        else:
            ims = []
            for i in range(self.im.bands):
                ims.append(self._new(self.im.getband(i)))
        return tuple(ims)

    def tell(self):
        """
        Returns the current frame number. See :py:meth:`~PIL.Image.Image.seek`.

        :returns: Frame number, starting with 0.
        """
        return 0

    def thumbnail(self, size, resample=ANTIALIAS):
        """
        Make this image into a thumbnail.  This method modifies the
        image to contain a thumbnail version of itself, no larger than
        the given size.  This method calculates an appropriate thumbnail
        size to preserve the aspect of the image, calls the
        :py:meth:`~PIL.Image.Image.draft` method to configure the file reader
        (where applicable), and finally resizes the image.

        Note that the bilinear and bicubic filters in the current
        version of PIL are not well-suited for thumbnail generation.
        You should use :py:attr:`PIL.Image.ANTIALIAS` unless speed is much more
        important than quality.

        Also note that this function modifies the :py:class:`~PIL.Image.Image`
        object in place.  If you need to use the full resolution image as well,
        apply this method to a :py:meth:`~PIL.Image.Image.copy` of the original
        image.

        :param size: Requested size.
        :param resample: Optional resampling filter.  This can be one
           of :py:attr:`PIL.Image.NEAREST`, :py:attr:`PIL.Image.BILINEAR`,
           :py:attr:`PIL.Image.BICUBIC`, or :py:attr:`PIL.Image.ANTIALIAS`
           (best quality).  If omitted, it defaults to
           :py:attr:`PIL.Image.ANTIALIAS`. (was :py:attr:`PIL.Image.NEAREST`
           prior to version 2.5.0)
        :returns: None
        """

        # preserve aspect ratio
        x, y = self.size
        if x > size[0]:
            y = int(max(y * size[0] / x, 1))
            x = int(size[0])
        if y > size[1]:
            x = int(max(x * size[1] / y, 1))
            y = int(size[1])
        size = x, y

        if size == self.size:
            return

        self.draft(None, size)

        self.load()

        try:
            im = self.resize(size, resample)
        except ValueError:
            if resample != ANTIALIAS:
                raise
            im = self.resize(size, NEAREST)  # fallback

        self.im = im.im
        self.mode = im.mode
        self.size = size

        self.readonly = 0
        self.pyaccess = None

    # FIXME: the different tranform methods need further explanation
    # instead of bloating the method docs, add a separate chapter.
    def transform(self, size, method, data=None, resample=NEAREST, fill=1):
        """
        Transforms this image.  This method creates a new image with the
        given size, and the same mode as the original, and copies data
        to the new image using the given transform.

        :param size: The output size.
        :param method: The transformation method.  This is one of
          :py:attr:`PIL.Image.EXTENT` (cut out a rectangular subregion),
          :py:attr:`PIL.Image.AFFINE` (affine transform),
          :py:attr:`PIL.Image.PERSPECTIVE` (perspective transform),
          :py:attr:`PIL.Image.QUAD` (map a quadrilateral to a rectangle), or
          :py:attr:`PIL.Image.MESH` (map a number of source quadrilaterals
          in one operation).
        :param data: Extra data to the transformation method.
        :param resample: Optional resampling filter.  It can be one of
           :py:attr:`PIL.Image.NEAREST` (use nearest neighbour),
           :py:attr:`PIL.Image.BILINEAR` (linear interpolation in a 2x2
           environment), or :py:attr:`PIL.Image.BICUBIC` (cubic spline
           interpolation in a 4x4 environment). If omitted, or if the image
           has mode "1" or "P", it is set to :py:attr:`PIL.Image.NEAREST`.
        :returns: An :py:class:`~PIL.Image.Image` object.
        """

        if self.mode == 'RGBA':
            return self.convert('RGBa').transform(
                size, method, data, resample, fill).convert('RGBA')

        if isinstance(method, ImageTransformHandler):
            return method.transform(size, self, resample=resample, fill=fill)
        if hasattr(method, "getdata"):
            # compatibility w. old-style transform objects
            method, data = method.getdata()
        if data is None:
            raise ValueError("missing method data")

        im = new(self.mode, size, None)
        if method == MESH:
            # list of quads
            for box, quad in data:
                im.__transformer(box, self, QUAD, quad, resample, fill)
        else:
            im.__transformer((0, 0)+size, self, method, data, resample, fill)

        return im

    def __transformer(self, box, image, method, data,
                      resample=NEAREST, fill=1):

        # FIXME: this should be turned into a lazy operation (?)

        w = box[2]-box[0]
        h = box[3]-box[1]

        if method == AFFINE:
            # change argument order to match implementation
            data = (data[2], data[0], data[1],
                    data[5], data[3], data[4])
        elif method == EXTENT:
            # convert extent to an affine transform
            x0, y0, x1, y1 = data
            xs = float(x1 - x0) / w
            ys = float(y1 - y0) / h
            method = AFFINE
            data = (x0 + xs/2, xs, 0, y0 + ys/2, 0, ys)
        elif method == PERSPECTIVE:
            # change argument order to match implementation
            data = (data[2], data[0], data[1],
                    data[5], data[3], data[4],
                    data[6], data[7])
        elif method == QUAD:
            # quadrilateral warp.  data specifies the four corners
            # given as NW, SW, SE, and NE.
            nw = data[0:2]
            sw = data[2:4]
            se = data[4:6]
            ne = data[6:8]
            x0, y0 = nw
            As = 1.0 / w
            At = 1.0 / h
            data = (x0, (ne[0]-x0)*As, (sw[0]-x0)*At,
                    (se[0]-sw[0]-ne[0]+x0)*As*At,
                    y0, (ne[1]-y0)*As, (sw[1]-y0)*At,
                    (se[1]-sw[1]-ne[1]+y0)*As*At)
        else:
            raise ValueError("unknown transformation method")

        if resample not in (NEAREST, BILINEAR, BICUBIC):
            raise ValueError("unknown resampling filter")

        image.load()

        self.load()

        if image.mode in ("1", "P"):
            resample = NEAREST

        self.im.transform2(box, image.im, method, data, resample, fill)

    def transpose(self, method):
        """
        Transpose image (flip or rotate in 90 degree steps)

        :param method: One of :py:attr:`PIL.Image.FLIP_LEFT_RIGHT`,
          :py:attr:`PIL.Image.FLIP_TOP_BOTTOM`, :py:attr:`PIL.Image.ROTATE_90`,
          :py:attr:`PIL.Image.ROTATE_180`, or :py:attr:`PIL.Image.ROTATE_270`.
        :returns: Returns a flipped or rotated copy of this image.
        """

        self.load()
        im = self.im.transpose(method)
        return self._new(im)


# --------------------------------------------------------------------
# Lazy operations

class _ImageCrop(Image):

    def __init__(self, im, box):

        Image.__init__(self)

        x0, y0, x1, y1 = box
        if x1 < x0:
            x1 = x0
        if y1 < y0:
            y1 = y0

        self.mode = im.mode
        self.size = x1-x0, y1-y0

        self.__crop = x0, y0, x1, y1

        self.im = im.im

    def load(self):

        # lazy evaluation!
        if self.__crop:
            self.im = self.im.crop(self.__crop)
            self.__crop = None

        if self.im:
            return self.im.pixel_access(self.readonly)

        # FIXME: future versions should optimize crop/paste
        # sequences!


# --------------------------------------------------------------------
# Abstract handlers.

class ImagePointHandler:
    # used as a mixin by point transforms (for use with im.point)
    pass


class ImageTransformHandler:
    # used as a mixin by geometry transforms (for use with im.transform)
    pass


# --------------------------------------------------------------------
# Factories

#
# Debugging

def _wedge():
    "Create greyscale wedge (for debugging only)"

    return Image()._new(core.wedge("L"))


def new(mode, size, color=0):
    """
    Creates a new image with the given mode and size.

    :param mode: The mode to use for the new image.
    :param size: A 2-tuple, containing (width, height) in pixels.
    :param color: What color to use for the image.  Default is black.
       If given, this should be a single integer or floating point value
       for single-band modes, and a tuple for multi-band modes (one value
       per band).  When creating RGB images, you can also use color
       strings as supported by the ImageColor module.  If the color is
       None, the image is not initialised.
    :returns: An :py:class:`~PIL.Image.Image` object.
    """

    if color is None:
        # don't initialize
        return Image()._new(core.new(mode, size))

    if isStringType(color):
        # css3-style specifier

        from PIL import ImageColor
        color = ImageColor.getcolor(color, mode)

    return Image()._new(core.fill(mode, size, color))


def frombytes(mode, size, data, decoder_name="raw", *args):
    """
    Creates a copy of an image memory from pixel data in a buffer.

    In its simplest form, this function takes three arguments
    (mode, size, and unpacked pixel data).

    You can also use any pixel decoder supported by PIL.  For more
    information on available decoders, see the section
    **Writing Your Own File Decoder**.

    Note that this function decodes pixel data only, not entire images.
    If you have an entire image in a string, wrap it in a
    :py:class:`~io.BytesIO` object, and use :py:func:`~PIL.Image.open` to load
    it.

    :param mode: The image mode.
    :param size: The image size.
    :param data: A byte buffer containing raw data for the given mode.
    :param decoder_name: What decoder to use.
    :param args: Additional parameters for the given decoder.
    :returns: An :py:class:`~PIL.Image.Image` object.
    """

    # may pass tuple instead of argument list
    if len(args) == 1 and isinstance(args[0], tuple):
        args = args[0]

    if decoder_name == "raw" and args == ():
        args = mode

    im = new(mode, size)
    im.frombytes(data, decoder_name, args)
    return im


def fromstring(*args, **kw):
    """Deprecated alias to frombytes.

    .. deprecated:: 2.0
    """
    warnings.warn(
        'fromstring() is deprecated. Please call frombytes() instead.',
        DeprecationWarning,
        stacklevel=2
    )
    return frombytes(*args, **kw)


def frombuffer(mode, size, data, decoder_name="raw", *args):
    """
    Creates an image memory referencing pixel data in a byte buffer.

    This function is similar to :py:func:`~PIL.Image.frombytes`, but uses data
    in the byte buffer, where possible.  This means that changes to the
    original buffer object are reflected in this image).  Not all modes can
    share memory; supported modes include "L", "RGBX", "RGBA", and "CMYK".

    Note that this function decodes pixel data only, not entire images.
    If you have an entire image file in a string, wrap it in a
    **BytesIO** object, and use :py:func:`~PIL.Image.open` to load it.

    In the current version, the default parameters used for the "raw" decoder
    differs from that used for :py:func:`~PIL.Image.fromstring`.  This is a
    bug, and will probably be fixed in a future release.  The current release
    issues a warning if you do this; to disable the warning, you should provide
    the full set of parameters.  See below for details.

    :param mode: The image mode.
    :param size: The image size.
    :param data: A bytes or other buffer object containing raw
        data for the given mode.
    :param decoder_name: What decoder to use.
    :param args: Additional parameters for the given decoder.  For the
        default encoder ("raw"), it's recommended that you provide the
        full set of parameters::

            frombuffer(mode, size, data, "raw", mode, 0, 1)

    :returns: An :py:class:`~PIL.Image.Image` object.

    .. versionadded:: 1.1.4
    """
    "Load image from bytes or buffer"

    # may pass tuple instead of argument list
    if len(args) == 1 and isinstance(args[0], tuple):
        args = args[0]

    if decoder_name == "raw":
        if args == ():
            if warnings:
                warnings.warn(
                    "the frombuffer defaults may change in a future release; "
                    "for portability, change the call to read:\n"
                    "  frombuffer(mode, size, data, 'raw', mode, 0, 1)",
                    RuntimeWarning, stacklevel=2
                )
            args = mode, 0, -1  # may change to (mode, 0, 1) post-1.1.6
        if args[0] in _MAPMODES:
            im = new(mode, (1, 1))
            im = im._new(
                core.map_buffer(data, size, decoder_name, None, 0, args)
                )
            im.readonly = 1
            return im

    return frombytes(mode, size, data, decoder_name, args)


def fromarray(obj, mode=None):
    """
    Creates an image memory from an object exporting the array interface
    (using the buffer protocol).

    If obj is not contiguous, then the tobytes method is called
    and :py:func:`~PIL.Image.frombuffer` is used.

    :param obj: Object with array interface
    :param mode: Mode to use (will be determined from type if None)
    :returns: An image memory.

    .. versionadded:: 1.1.6
    """
    arr = obj.__array_interface__
    shape = arr['shape']
    ndim = len(shape)
    try:
        strides = arr['strides']
    except KeyError:
        strides = None
    if mode is None:
        try:
            typekey = (1, 1) + shape[2:], arr['typestr']
            mode, rawmode = _fromarray_typemap[typekey]
        except KeyError:
            # print typekey
            raise TypeError("Cannot handle this data type")
    else:
        rawmode = mode
    if mode in ["1", "L", "I", "P", "F"]:
        ndmax = 2
    elif mode == "RGB":
        ndmax = 3
    else:
        ndmax = 4
    if ndim > ndmax:
        raise ValueError("Too many dimensions: %d > %d." % (ndim, ndmax))

    size = shape[1], shape[0]
    if strides is not None:
        if hasattr(obj, 'tobytes'):
            obj = obj.tobytes()
        else:
            obj = obj.tostring()

    return frombuffer(mode, size, obj, "raw", rawmode, 0, 1)

_fromarray_typemap = {
    # (shape, typestr) => mode, rawmode
    # first two members of shape are set to one
    # ((1, 1), "|b1"): ("1", "1"), # broken
    ((1, 1), "|u1"): ("L", "L"),
    ((1, 1), "|i1"): ("I", "I;8"),
    ((1, 1), "<i2"): ("I", "I;16"),
    ((1, 1), ">i2"): ("I", "I;16B"),
    ((1, 1), "<i4"): ("I", "I;32"),
    ((1, 1), ">i4"): ("I", "I;32B"),
    ((1, 1), "<f4"): ("F", "F;32F"),
    ((1, 1), ">f4"): ("F", "F;32BF"),
    ((1, 1), "<f8"): ("F", "F;64F"),
    ((1, 1), ">f8"): ("F", "F;64BF"),
    ((1, 1, 3), "|u1"): ("RGB", "RGB"),
    ((1, 1, 4), "|u1"): ("RGBA", "RGBA"),
    }

# shortcuts
_fromarray_typemap[((1, 1), _ENDIAN + "i4")] = ("I", "I")
_fromarray_typemap[((1, 1), _ENDIAN + "f4")] = ("F", "F")


def open(fp, mode="r"):
    """
    Opens and identifies the given image file.

    This is a lazy operation; this function identifies the file, but
    the file remains open and the actual image data is not read from
    the file until you try to process the data (or call the
    :py:meth:`~PIL.Image.Image.load` method).  See
    :py:func:`~PIL.Image.new`.

    :param file: A filename (string) or a file object.  The file object
       must implement :py:meth:`~file.read`, :py:meth:`~file.seek`, and
       :py:meth:`~file.tell` methods, and be opened in binary mode.
    :param mode: The mode.  If given, this argument must be "r".
    :returns: An :py:class:`~PIL.Image.Image` object.
    :exception IOError: If the file cannot be found, or the image cannot be
       opened and identified.
    """

    if mode != "r":
        raise ValueError("bad mode %r" % mode)

    if isPath(fp):
        filename = fp
        fp = builtins.open(fp, "rb")
    else:
        filename = ""

    prefix = fp.read(16)

    preinit()

    for i in ID:
        try:
            factory, accept = OPEN[i]
            if not accept or accept(prefix):
                fp.seek(0)
                return factory(fp, filename)
        except (SyntaxError, IndexError, TypeError):
            # import traceback
            # traceback.print_exc()
            pass

    if init():

        for i in ID:
            try:
                factory, accept = OPEN[i]
                if not accept or accept(prefix):
                    fp.seek(0)
                    return factory(fp, filename)
            except (SyntaxError, IndexError, TypeError):
                # import traceback
                # traceback.print_exc()
                pass

    raise IOError("cannot identify image file %r"
                  % (filename if filename else fp))


#
# Image processing.

def alpha_composite(im1, im2):
    """
    Alpha composite im2 over im1.

    :param im1: The first image.
    :param im2: The second image.  Must have the same mode and size as
       the first image.
    :returns: An :py:class:`~PIL.Image.Image` object.
    """

    im1.load()
    im2.load()
    return im1._new(core.alpha_composite(im1.im, im2.im))


def blend(im1, im2, alpha):
    """
    Creates a new image by interpolating between two input images, using
    a constant alpha.::

        out = image1 * (1.0 - alpha) + image2 * alpha

    :param im1: The first image.
    :param im2: The second image.  Must have the same mode and size as
       the first image.
    :param alpha: The interpolation alpha factor.  If alpha is 0.0, a
       copy of the first image is returned. If alpha is 1.0, a copy of
       the second image is returned. There are no restrictions on the
       alpha value. If necessary, the result is clipped to fit into
       the allowed output range.
    :returns: An :py:class:`~PIL.Image.Image` object.
    """

    im1.load()
    im2.load()
    return im1._new(core.blend(im1.im, im2.im, alpha))


def composite(image1, image2, mask):
    """
    Create composite image by blending images using a transparency mask.

    :param image1: The first image.
    :param image2: The second image.  Must have the same mode and
       size as the first image.
    :param mask: A mask image.  This image can can have mode
       "1", "L", or "RGBA", and must have the same size as the
       other two images.
    """

    image = image2.copy()
    image.paste(image1, None, mask)
    return image


def eval(image, *args):
    """
    Applies the function (which should take one argument) to each pixel
    in the given image. If the image has more than one band, the same
    function is applied to each band. Note that the function is
    evaluated once for each possible pixel value, so you cannot use
    random components or other generators.

    :param image: The input image.
    :param function: A function object, taking one integer argument.
    :returns: An :py:class:`~PIL.Image.Image` object.
    """

    return image.point(args[0])


def merge(mode, bands):
    """
    Merge a set of single band images into a new multiband image.

    :param mode: The mode to use for the output image.
    :param bands: A sequence containing one single-band image for
        each band in the output image.  All bands must have the
        same size.
    :returns: An :py:class:`~PIL.Image.Image` object.
    """

    if getmodebands(mode) != len(bands) or "*" in mode:
        raise ValueError("wrong number of bands")
    for im in bands[1:]:
        if im.mode != getmodetype(mode):
            raise ValueError("mode mismatch")
        if im.size != bands[0].size:
            raise ValueError("size mismatch")
    im = core.new(mode, bands[0].size)
    for i in range(getmodebands(mode)):
        bands[i].load()
        im.putband(bands[i].im, i)
    return bands[0]._new(im)


# --------------------------------------------------------------------
# Plugin registry

def register_open(id, factory, accept=None):
    """
    Register an image file plugin.  This function should not be used
    in application code.

    :param id: An image format identifier.
    :param factory: An image file factory method.
    :param accept: An optional function that can be used to quickly
       reject images having another format.
    """
    id = id.upper()
    ID.append(id)
    OPEN[id] = factory, accept


def register_mime(id, mimetype):
    """
    Registers an image MIME type.  This function should not be used
    in application code.

    :param id: An image format identifier.
    :param mimetype: The image MIME type for this format.
    """
    MIME[id.upper()] = mimetype


def register_save(id, driver):
    """
    Registers an image save function.  This function should not be
    used in application code.

    :param id: An image format identifier.
    :param driver: A function to save images in this format.
    """
    SAVE[id.upper()] = driver


def register_extension(id, extension):
    """
    Registers an image extension.  This function should not be
    used in application code.

    :param id: An image format identifier.
    :param extension: An extension used for this format.
    """
    EXTENSION[extension.lower()] = id.upper()


# --------------------------------------------------------------------
# Simple display support.  User code may override this.

def _show(image, **options):
    # override me, as necessary
    _showxv(image, **options)


def _showxv(image, title=None, **options):
    from PIL import ImageShow
    ImageShow.show(image, title, **options)

########NEW FILE########
__FILENAME__ = ImageChops
#
# The Python Imaging Library.
# $Id$
#
# standard channel operations
#
# History:
# 1996-03-24 fl   Created
# 1996-08-13 fl   Added logical operations (for "1" images)
# 2000-10-12 fl   Added offset method (from Image.py)
#
# Copyright (c) 1997-2000 by Secret Labs AB
# Copyright (c) 1996-2000 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

from PIL import Image


def constant(image, value):
    """Fill a channel with a given grey level.

    :rtype: :py:class:`~PIL.Image.Image`
    """

    return Image.new("L", image.size, value)


def duplicate(image):
    """Copy a channel. Alias for :py:meth:`PIL.Image.Image.copy`.

    :rtype: :py:class:`~PIL.Image.Image`
    """

    return image.copy()


def invert(image):
    """
    Invert an image (channel).

    .. code-block:: python

        out = MAX - image

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image.load()
    return image._new(image.im.chop_invert())


def lighter(image1, image2):
    """
    Compares the two images, pixel by pixel, and returns a new image containing
    the lighter values.

    .. code-block:: python

        out = max(image1, image2)

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_lighter(image2.im))


def darker(image1, image2):
    """
    Compares the two images, pixel by pixel, and returns a new image
    containing the darker values.

    .. code-block:: python

        out = min(image1, image2)

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_darker(image2.im))


def difference(image1, image2):
    """
    Returns the absolute value of the pixel-by-pixel difference between the two
    images.

    .. code-block:: python

        out = abs(image1 - image2)

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_difference(image2.im))


def multiply(image1, image2):
    """
    Superimposes two images on top of each other.

    If you multiply an image with a solid black image, the result is black. If
    you multiply with a solid white image, the image is unaffected.

    .. code-block:: python

        out = image1 * image2 / MAX

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_multiply(image2.im))


def screen(image1, image2):
    """
    Superimposes two inverted images on top of each other.

    .. code-block:: python

        out = MAX - ((MAX - image1) * (MAX - image2) / MAX)

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_screen(image2.im))


def add(image1, image2, scale=1.0, offset=0):
    """
    Adds two images, dividing the result by scale and adding the
    offset. If omitted, scale defaults to 1.0, and offset to 0.0.

    .. code-block:: python

        out = ((image1 + image2) / scale + offset)

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_add(image2.im, scale, offset))


def subtract(image1, image2, scale=1.0, offset=0):
    """
    Subtracts two images, dividing the result by scale and adding the
    offset. If omitted, scale defaults to 1.0, and offset to 0.0.

    .. code-block:: python

        out = ((image1 - image2) / scale + offset)

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_subtract(image2.im, scale, offset))


def add_modulo(image1, image2):
    """Add two images, without clipping the result.

    .. code-block:: python

        out = ((image1 + image2) % MAX)

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_add_modulo(image2.im))


def subtract_modulo(image1, image2):
    """Subtract two images, without clipping the result.

    .. code-block:: python

        out = ((image1 - image2) % MAX)

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_subtract_modulo(image2.im))


def logical_and(image1, image2):
    """Logical AND between two images.

    .. code-block:: python

        out = ((image1 and image2) % MAX)

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_and(image2.im))


def logical_or(image1, image2):
    """Logical OR between two images.

    .. code-block:: python

        out = ((image1 or image2) % MAX)

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_or(image2.im))


def logical_xor(image1, image2):
    """Logical XOR between two images.

    .. code-block:: python

        out = ((bool(image1) != bool(image2)) % MAX)

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_xor(image2.im))


def blend(image1, image2, alpha):
    """Blend images using constant transparency weight. Alias for
    :py:meth:`PIL.Image.Image.blend`.

    :rtype: :py:class:`~PIL.Image.Image`
    """

    return Image.blend(image1, image2, alpha)


def composite(image1, image2, mask):
    """Create composite using transparency mask. Alias for
    :py:meth:`PIL.Image.Image.composite`.

    :rtype: :py:class:`~PIL.Image.Image`
    """

    return Image.composite(image1, image2, mask)


def offset(image, xoffset, yoffset=None):
    """Returns a copy of the image where data has been offset by the given
    distances. Data wraps around the edges. If **yoffset** is omitted, it
    is assumed to be equal to **xoffset**.

    :param xoffset: The horizontal distance.
    :param yoffset: The vertical distance.  If omitted, both
        distances are set to the same value.
    :rtype: :py:class:`~PIL.Image.Image`
    """

    if yoffset is None:
        yoffset = xoffset
    image.load()
    return image._new(image.im.offset(xoffset, yoffset))

########NEW FILE########
__FILENAME__ = ImageCms
#
# The Python Imaging Library.
# $Id$
#
# optional color managment support, based on Kevin Cazabon's PyCMS
# library.
#
# History:
# 2009-03-08 fl   Added to PIL.
#
# Copyright (C) 2002-2003 Kevin Cazabon
# Copyright (c) 2009 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.  See
# below for the original description.
#

from __future__ import print_function

DESCRIPTION = """
pyCMS

    a Python / PIL interface to the littleCMS ICC Color Management System
    Copyright (C) 2002-2003 Kevin Cazabon
    kevin@cazabon.com
    http://www.cazabon.com

    pyCMS home page:  http://www.cazabon.com/pyCMS
    littleCMS home page:  http://www.littlecms.com
    (littleCMS is Copyright (C) 1998-2001 Marti Maria)

    Originally released under LGPL.  Graciously donated to PIL in
    March 2009, for distribution under the standard PIL license

    The pyCMS.py module provides a "clean" interface between Python/PIL and
    pyCMSdll, taking care of some of the more complex handling of the direct
    pyCMSdll functions, as well as error-checking and making sure that all
    relevant data is kept together.

    While it is possible to call pyCMSdll functions directly, it's not highly
    recommended.

    Version History:

        1.0.0 pil       Oct 2013 Port to LCMS 2.

        0.1.0 pil mod   March 10, 2009

                        Renamed display profile to proof profile. The proof
                        profile is the profile of the device that is being
                        simulated, not the profile of the device which is
                        actually used to display/print the final simulation
                        (that'd be the output profile) - also see LCMSAPI.txt
                        input colorspace -> using 'renderingIntent' -> proof
                        colorspace -> using 'proofRenderingIntent' -> output
                        colorspace

                        Added LCMS FLAGS support.
                        Added FLAGS["SOFTPROOFING"] as default flag for
                        buildProofTransform (otherwise the proof profile/intent
                        would be ignored).

        0.1.0 pil       March 2009 - added to PIL, as PIL.ImageCms

        0.0.2 alpha     Jan 6, 2002

                        Added try/except statements arount type() checks of
                        potential CObjects... Python won't let you use type()
                        on them, and raises a TypeError (stupid, if you ask me!)

                        Added buildProofTransformFromOpenProfiles() function.
                        Additional fixes in DLL, see DLL code for details.

        0.0.1 alpha     first public release, Dec. 26, 2002

    Known to-do list with current version (of Python interface, not pyCMSdll):

        none

"""

VERSION = "1.0.0 pil"

# --------------------------------------------------------------------.

from PIL import Image
try:
    from PIL import _imagingcms
except ImportError as ex:
    # Allow error import for doc purposes, but error out when accessing
    # anything in core. 
    from _util import deferred_error
    _imagingcms = deferred_error(ex)
from PIL._util import isStringType

core = _imagingcms

#
# intent/direction values

INTENT_PERCEPTUAL = 0
INTENT_RELATIVE_COLORIMETRIC = 1
INTENT_SATURATION = 2
INTENT_ABSOLUTE_COLORIMETRIC = 3

DIRECTION_INPUT = 0
DIRECTION_OUTPUT = 1
DIRECTION_PROOF = 2

#
# flags

FLAGS = {
    "MATRIXINPUT": 1,
    "MATRIXOUTPUT": 2,
    "MATRIXONLY": (1|2),
    "NOWHITEONWHITEFIXUP": 4, # Don't hot fix scum dot
    "NOPRELINEARIZATION": 16, # Don't create prelinearization tables on precalculated transforms (internal use)
    "GUESSDEVICECLASS": 32, # Guess device class (for transform2devicelink)
    "NOTCACHE": 64, # Inhibit 1-pixel cache
    "NOTPRECALC": 256,
    "NULLTRANSFORM": 512, # Don't transform anyway
    "HIGHRESPRECALC": 1024, # Use more memory to give better accurancy
    "LOWRESPRECALC": 2048, # Use less memory to minimize resouces
    "WHITEBLACKCOMPENSATION": 8192,
    "BLACKPOINTCOMPENSATION": 8192,
    "GAMUTCHECK": 4096, # Out of Gamut alarm
    "SOFTPROOFING": 16384, # Do softproofing
    "PRESERVEBLACK": 32768, # Black preservation
    "NODEFAULTRESOURCEDEF": 16777216, # CRD special
    "GRIDPOINTS": lambda n: ((n) & 0xFF) << 16 # Gridpoints
}

_MAX_FLAG = 0
for flag in FLAGS.values():
    if isinstance(flag, int):
        _MAX_FLAG = _MAX_FLAG | flag

# --------------------------------------------------------------------.
# Experimental PIL-level API
# --------------------------------------------------------------------.

##
# Profile.

class ImageCmsProfile:

    def __init__(self, profile):
        # accepts a string (filename), a file-like object, or a low-level
        # profile object
        if isStringType(profile):
            self._set(core.profile_open(profile), profile)
        elif hasattr(profile, "read"):
            self._set(core.profile_frombytes(profile.read()))
        else:
            self._set(profile) # assume it's already a profile

    def _set(self, profile, filename=None):
        self.profile = profile
        self.filename = filename
        if profile:
            self.product_name = None #profile.product_name
            self.product_info = None #profile.product_info
        else:
            self.product_name = None
            self.product_info = None

class ImageCmsTransform(Image.ImagePointHandler):
    """Transform.  This can be used with the procedural API, or with the
    standard Image.point() method.
    """

    def __init__(self, input, output, input_mode, output_mode,
                 intent=INTENT_PERCEPTUAL,
                 proof=None, proof_intent=INTENT_ABSOLUTE_COLORIMETRIC, flags=0):
        if proof is None:
            self.transform = core.buildTransform(
                input.profile, output.profile,
                input_mode, output_mode,
                intent,
                flags
                )
        else:
            self.transform = core.buildProofTransform(
                input.profile, output.profile, proof.profile,
                input_mode, output_mode,
                intent, proof_intent,
                flags
                )
        # Note: inputMode and outputMode are for pyCMS compatibility only
        self.input_mode = self.inputMode = input_mode
        self.output_mode = self.outputMode = output_mode

    def point(self, im):
        return self.apply(im)

    def apply(self, im, imOut=None):
        im.load()
        if imOut is None:
            imOut = Image.new(self.output_mode, im.size, None)
        result = self.transform.apply(im.im.id, imOut.im.id)
        return imOut

    def apply_in_place(self, im):
        im.load()
        if im.mode != self.output_mode:
            raise ValueError("mode mismatch") # wrong output mode
        result = self.transform.apply(im.im.id, im.im.id)
        return im

def get_display_profile(handle=None):
    """ (experimental) Fetches the profile for the current display device.
    :returns: None if the profile is not known.
    """
    
    import sys
    if sys.platform == "win32":
        from PIL import ImageWin
        if isinstance(handle, ImageWin.HDC):
            profile = core.get_display_profile_win32(handle, 1)
        else:
            profile = core.get_display_profile_win32(handle or 0)
    else:
        try:
            get = _imagingcms.get_display_profile
        except AttributeError:
            return None
        else:
            profile = get()
    return ImageCmsProfile(profile)

# --------------------------------------------------------------------.
# pyCMS compatible layer
# --------------------------------------------------------------------.

class PyCMSError(Exception):
    """ (pyCMS) Exception class.  This is used for all errors in the pyCMS API. """
    pass

def profileToProfile(im, inputProfile, outputProfile, renderingIntent=INTENT_PERCEPTUAL, outputMode=None, inPlace=0, flags=0):
    """
    (pyCMS) Applies an ICC transformation to a given image, mapping from
    inputProfile to outputProfile.

    If the input or output profiles specified are not valid filenames, a
    PyCMSError will be raised.  If inPlace == TRUE and outputMode != im.mode,
    a PyCMSError will be raised.  If an error occurs during application of
    the profiles, a PyCMSError will be raised.  If outputMode is not a mode
    supported by the outputProfile (or by pyCMS), a PyCMSError will be
    raised.

    This function applies an ICC transformation to im from inputProfile's
    color space to outputProfile's color space using the specified rendering
    intent to decide how to handle out-of-gamut colors.

    OutputMode can be used to specify that a color mode conversion is to
    be done using these profiles, but the specified profiles must be able
    to handle that mode.  I.e., if converting im from RGB to CMYK using
    profiles, the input profile must handle RGB data, and the output
    profile must handle CMYK data.

    :param im: An open PIL image object (i.e. Image.new(...) or Image.open(...), etc.)
    :param inputProfile: String, as a valid filename path to the ICC input profile
        you wish to use for this image, or a profile object
    :param outputProfile: String, as a valid filename path to the ICC output
        profile you wish to use for this image, or a profile object
    :param renderingIntent: Integer (0-3) specifying the rendering intent you wish
        to use for the transform

            INTENT_PERCEPTUAL            = 0 (DEFAULT) (ImageCms.INTENT_PERCEPTUAL)
            INTENT_RELATIVE_COLORIMETRIC = 1 (ImageCms.INTENT_RELATIVE_COLORIMETRIC)
            INTENT_SATURATION            = 2 (ImageCms.INTENT_SATURATION)
            INTENT_ABSOLUTE_COLORIMETRIC = 3 (ImageCms.INTENT_ABSOLUTE_COLORIMETRIC)

        see the pyCMS documentation for details on rendering intents and what they do.
    :param outputMode: A valid PIL mode for the output image (i.e. "RGB", "CMYK",
        etc.).  Note: if rendering the image "inPlace", outputMode MUST be the
        same mode as the input, or omitted completely.  If omitted, the outputMode
        will be the same as the mode of the input image (im.mode)
    :param inPlace: Boolean (1 = True, None or 0 = False).  If True, the original
        image is modified in-place, and None is returned.  If False (default), a
        new Image object is returned with the transform applied.
    :param flags: Integer (0-...) specifying additional flags
    :returns: Either None or a new PIL image object, depending on value of inPlace
    :exception PyCMSError:
    """

    if outputMode is None:
        outputMode = im.mode

    if not isinstance(renderingIntent, int) or not (0 <= renderingIntent <=3):
        raise PyCMSError("renderingIntent must be an integer between 0 and 3")

    if not isinstance(flags, int) or not (0 <= flags <= _MAX_FLAG):
        raise PyCMSError("flags must be an integer between 0 and %s" + _MAX_FLAG)

    try:
        if not isinstance(inputProfile, ImageCmsProfile):
            inputProfile = ImageCmsProfile(inputProfile)
        if not isinstance(outputProfile, ImageCmsProfile):
            outputProfile = ImageCmsProfile(outputProfile)
        transform = ImageCmsTransform(
            inputProfile, outputProfile, im.mode, outputMode, renderingIntent, flags=flags
            )
        if inPlace:
            transform.apply_in_place(im)
            imOut = None
        else:
            imOut = transform.apply(im)
    except (IOError, TypeError, ValueError) as v:
        raise PyCMSError(v)

    return imOut


def getOpenProfile(profileFilename):
    """
    (pyCMS) Opens an ICC profile file.

    The PyCMSProfile object can be passed back into pyCMS for use in creating
    transforms and such (as in ImageCms.buildTransformFromOpenProfiles()).

    If profileFilename is not a vaild filename for an ICC profile, a PyCMSError
    will be raised.

    :param profileFilename: String, as a valid filename path to the ICC profile you
        wish to open, or a file-like object.
    :returns: A CmsProfile class object.
    :exception PyCMSError:
    """

    try:
        return ImageCmsProfile(profileFilename)
    except (IOError, TypeError, ValueError) as v:
        raise PyCMSError(v)

def buildTransform(inputProfile, outputProfile, inMode, outMode, renderingIntent=INTENT_PERCEPTUAL, flags=0):
    """
    (pyCMS) Builds an ICC transform mapping from the inputProfile to the
    outputProfile.  Use applyTransform to apply the transform to a given
    image.

    If the input or output profiles specified are not valid filenames, a
    PyCMSError will be raised.  If an error occurs during creation of the
    transform, a PyCMSError will be raised.

    If inMode or outMode are not a mode supported by the outputProfile (or
    by pyCMS), a PyCMSError will be raised.

    This function builds and returns an ICC transform from the inputProfile
    to the outputProfile using the renderingIntent to determine what to do
    with out-of-gamut colors.  It will ONLY work for converting images that
    are in inMode to images that are in outMode color format (PIL mode,
    i.e. "RGB", "RGBA", "CMYK", etc.).

    Building the transform is a fair part of the overhead in
    ImageCms.profileToProfile(), so if you're planning on converting multiple
    images using the same input/output settings, this can save you time.
    Once you have a transform object, it can be used with
    ImageCms.applyProfile() to convert images without the need to re-compute
    the lookup table for the transform.

    The reason pyCMS returns a class object rather than a handle directly
    to the transform is that it needs to keep track of the PIL input/output
    modes that the transform is meant for.  These attributes are stored in
    the "inMode" and "outMode" attributes of the object (which can be
    manually overridden if you really want to, but I don't know of any
    time that would be of use, or would even work).

    :param inputProfile: String, as a valid filename path to the ICC input profile
        you wish to use for this transform, or a profile object
    :param outputProfile: String, as a valid filename path to the ICC output
        profile you wish to use for this transform, or a profile object
    :param inMode: String, as a valid PIL mode that the appropriate profile also
        supports (i.e. "RGB", "RGBA", "CMYK", etc.)
    :param outMode: String, as a valid PIL mode that the appropriate profile also
        supports (i.e. "RGB", "RGBA", "CMYK", etc.)
    :param renderingIntent: Integer (0-3) specifying the rendering intent you
        wish to use for the transform

            INTENT_PERCEPTUAL            = 0 (DEFAULT) (ImageCms.INTENT_PERCEPTUAL)
            INTENT_RELATIVE_COLORIMETRIC = 1 (ImageCms.INTENT_RELATIVE_COLORIMETRIC)
            INTENT_SATURATION            = 2 (ImageCms.INTENT_SATURATION)
            INTENT_ABSOLUTE_COLORIMETRIC = 3 (ImageCms.INTENT_ABSOLUTE_COLORIMETRIC)

        see the pyCMS documentation for details on rendering intents and what they do.
    :param flags: Integer (0-...) specifying additional flags
    :returns: A CmsTransform class object.
    :exception PyCMSError:
    """

    if not isinstance(renderingIntent, int) or not (0 <= renderingIntent <=3):
        raise PyCMSError("renderingIntent must be an integer between 0 and 3")

    if not isinstance(flags, int) or not (0 <= flags <= _MAX_FLAG):
        raise PyCMSError("flags must be an integer between 0 and %s" + _MAX_FLAG)

    try:
        if not isinstance(inputProfile, ImageCmsProfile):
            inputProfile = ImageCmsProfile(inputProfile)
        if not isinstance(outputProfile, ImageCmsProfile):
            outputProfile = ImageCmsProfile(outputProfile)
        return ImageCmsTransform(inputProfile, outputProfile, inMode, outMode, renderingIntent, flags=flags)
    except (IOError, TypeError, ValueError) as v:
        raise PyCMSError(v)

def buildProofTransform(inputProfile, outputProfile, proofProfile, inMode, outMode, renderingIntent=INTENT_PERCEPTUAL, proofRenderingIntent=INTENT_ABSOLUTE_COLORIMETRIC, flags=FLAGS["SOFTPROOFING"]):
    """
    (pyCMS) Builds an ICC transform mapping from the inputProfile to the
    outputProfile, but tries to simulate the result that would be
    obtained on the proofProfile device.

    If the input, output, or proof profiles specified are not valid
    filenames, a PyCMSError will be raised.

    If an error occurs during creation of the transform, a PyCMSError will
    be raised.

    If inMode or outMode are not a mode supported by the outputProfile
    (or by pyCMS), a PyCMSError will be raised.

    This function builds and returns an ICC transform from the inputProfile
    to the outputProfile, but tries to simulate the result that would be
    obtained on the proofProfile device using renderingIntent and
    proofRenderingIntent to determine what to do with out-of-gamut
    colors.  This is known as "soft-proofing".  It will ONLY work for
    converting images that are in inMode to images that are in outMode
    color format (PIL mode, i.e. "RGB", "RGBA", "CMYK", etc.).

    Usage of the resulting transform object is exactly the same as with
    ImageCms.buildTransform().

    Proof profiling is generally used when using an output device to get a
    good idea of what the final printed/displayed image would look like on
    the proofProfile device when it's quicker and easier to use the
    output device for judging color.  Generally, this means that the
    output device is a monitor, or a dye-sub printer (etc.), and the simulated
    device is something more expensive, complicated, or time consuming
    (making it difficult to make a real print for color judgement purposes).

    Soft-proofing basically functions by adjusting the colors on the
    output device to match the colors of the device being simulated. However,
    when the simulated device has a much wider gamut than the output
    device, you may obtain marginal results.

    :param inputProfile: String, as a valid filename path to the ICC input profile
        you wish to use for this transform, or a profile object
    :param outputProfile: String, as a valid filename path to the ICC output
        (monitor, usually) profile you wish to use for this transform, or a
        profile object
    :param proofProfile: String, as a valid filename path to the ICC proof profile
        you wish to use for this transform, or a profile object
    :param inMode: String, as a valid PIL mode that the appropriate profile also
        supports (i.e. "RGB", "RGBA", "CMYK", etc.)
    :param outMode: String, as a valid PIL mode that the appropriate profile also
        supports (i.e. "RGB", "RGBA", "CMYK", etc.)
    :param renderingIntent: Integer (0-3) specifying the rendering intent you
        wish to use for the input->proof (simulated) transform

            INTENT_PERCEPTUAL            = 0 (DEFAULT) (ImageCms.INTENT_PERCEPTUAL)
            INTENT_RELATIVE_COLORIMETRIC = 1 (ImageCms.INTENT_RELATIVE_COLORIMETRIC)
            INTENT_SATURATION            = 2 (ImageCms.INTENT_SATURATION)
            INTENT_ABSOLUTE_COLORIMETRIC = 3 (ImageCms.INTENT_ABSOLUTE_COLORIMETRIC)

        see the pyCMS documentation for details on rendering intents and what they do.
    :param proofRenderingIntent: Integer (0-3) specifying the rendering intent you
        wish to use for proof->output transform

            INTENT_PERCEPTUAL            = 0 (DEFAULT) (ImageCms.INTENT_PERCEPTUAL)
            INTENT_RELATIVE_COLORIMETRIC = 1 (ImageCms.INTENT_RELATIVE_COLORIMETRIC)
            INTENT_SATURATION            = 2 (ImageCms.INTENT_SATURATION)
            INTENT_ABSOLUTE_COLORIMETRIC = 3 (ImageCms.INTENT_ABSOLUTE_COLORIMETRIC)

        see the pyCMS documentation for details on rendering intents and what they do.
    :param flags: Integer (0-...) specifying additional flags
    :returns: A CmsTransform class object.
    :exception PyCMSError:
    """
        
    if not isinstance(renderingIntent, int) or not (0 <= renderingIntent <=3):
        raise PyCMSError("renderingIntent must be an integer between 0 and 3")

    if not isinstance(flags, int) or not (0 <= flags <= _MAX_FLAG):
        raise PyCMSError("flags must be an integer between 0 and %s" + _MAX_FLAG)

    try:
        if not isinstance(inputProfile, ImageCmsProfile):
            inputProfile = ImageCmsProfile(inputProfile)
        if not isinstance(outputProfile, ImageCmsProfile):
            outputProfile = ImageCmsProfile(outputProfile)
        if not isinstance(proofProfile, ImageCmsProfile):
            proofProfile = ImageCmsProfile(proofProfile)
        return ImageCmsTransform(inputProfile, outputProfile, inMode, outMode, renderingIntent, proofProfile, proofRenderingIntent, flags)
    except (IOError, TypeError, ValueError) as v:
        raise PyCMSError(v)

buildTransformFromOpenProfiles = buildTransform
buildProofTransformFromOpenProfiles = buildProofTransform

def applyTransform(im, transform, inPlace=0):
    """
    (pyCMS) Applies a transform to a given image.

    If im.mode != transform.inMode, a PyCMSError is raised.

    If inPlace == TRUE and transform.inMode != transform.outMode, a
    PyCMSError is raised.

    If im.mode, transfer.inMode, or transfer.outMode is not supported by
    pyCMSdll or the profiles you used for the transform, a PyCMSError is
    raised.

    If an error occurs while the transform is being applied, a PyCMSError
    is raised.

    This function applies a pre-calculated transform (from
    ImageCms.buildTransform() or ImageCms.buildTransformFromOpenProfiles()) to an
    image.  The transform can be used for multiple images, saving
    considerable calcuation time if doing the same conversion multiple times.

    If you want to modify im in-place instead of receiving a new image as
    the return value, set inPlace to TRUE.  This can only be done if
    transform.inMode and transform.outMode are the same, because we can't
    change the mode in-place (the buffer sizes for some modes are
    different).  The  default behavior is to return a new Image object of
    the same dimensions in mode transform.outMode.

    :param im: A PIL Image object, and im.mode must be the same as the inMode
        supported by the transform.
    :param transform: A valid CmsTransform class object
    :param inPlace: Bool (1 == True, 0 or None == False).  If True, im is modified
        in place and None is returned, if False, a new Image object with the
        transform applied is returned (and im is not changed).  The default is False.
    :returns: Either None, or a new PIL Image object, depending on the value of inPlace
    :exception PyCMSError:
    """

    try:
        if inPlace:
            transform.apply_in_place(im)
            imOut = None
        else:
            imOut = transform.apply(im)
    except (TypeError, ValueError) as v:
        raise PyCMSError(v)

    return imOut

def createProfile(colorSpace, colorTemp=-1):
    """
    (pyCMS) Creates a profile.

    If colorSpace not in ["LAB", "XYZ", "sRGB"], a PyCMSError is raised

    If using LAB and colorTemp != a positive integer, a PyCMSError is raised.

    If an error occurs while creating the profile, a PyCMSError is raised.

    Use this function to create common profiles on-the-fly instead of
    having to supply a profile on disk and knowing the path to it.  It
    returns a normal CmsProfile object that can be passed to
    ImageCms.buildTransformFromOpenProfiles() to create a transform to apply
    to images.

    :param colorSpace: String, the color space of the profile you wish to create.
        Currently only "LAB", "XYZ", and "sRGB" are supported.
    :param colorTemp: Positive integer for the white point for the profile, in
        degrees Kelvin (i.e. 5000, 6500, 9600, etc.).  The default is for D50
        illuminant if omitted (5000k).  colorTemp is ONLY applied to LAB profiles,
        and is ignored for XYZ and sRGB.
    :returns: A CmsProfile class object
    :exception PyCMSError:
    """

    if colorSpace not in ["LAB", "XYZ", "sRGB"]:
        raise PyCMSError("Color space not supported for on-the-fly profile creation (%s)" % colorSpace)

    if colorSpace == "LAB":
        try:
            colorTemp = float(colorTemp)
        except:
            raise PyCMSError("Color temperature must be numeric, \"%s\" not valid" % colorTemp)

    try:
        return core.createProfile(colorSpace, colorTemp)
    except (TypeError, ValueError) as v:
        raise PyCMSError(v)

def getProfileName(profile):
    """

    (pyCMS) Gets the internal product name for the given profile.

     If profile isn't a valid CmsProfile object or filename to a profile,
    a PyCMSError is raised If an error occurs while trying to obtain the
    name tag, a PyCMSError is raised.

    Use this function to obtain the INTERNAL name of the profile (stored
    in an ICC tag in the profile itself), usually the one used when the
    profile was originally created.  Sometimes this tag also contains
    additional information supplied by the creator.

    :param profile: EITHER a valid CmsProfile object, OR a string of the filename
        of an ICC profile.
    :returns: A string containing the internal name of the profile as stored in an
        ICC tag.
    :exception PyCMSError:
    """

    try:
        # add an extra newline to preserve pyCMS compatibility
        if not isinstance(profile, ImageCmsProfile):
            profile = ImageCmsProfile(profile)
        # do it in python, not c.
        #    // name was "%s - %s" (model, manufacturer) || Description , 
        #    // but if the Model and Manufacturer were the same or the model 
        #    // was long, Just the model,  in 1.x
        model = profile.profile.product_model
        manufacturer = profile.profile.product_manufacturer

        if not (model or manufacturer):
            return profile.profile.product_description+"\n"
        if not manufacturer or len(model) > 30:
            return model + "\n"
        return "%s - %s\n" % (model, manufacturer)

    except (AttributeError, IOError, TypeError, ValueError) as v:
        raise PyCMSError(v)

def getProfileInfo(profile):
    """
    (pyCMS) Gets the internal product information for the given profile.

    If profile isn't a valid CmsProfile object or filename to a profile,
    a PyCMSError is raised.

    If an error occurs while trying to obtain the info tag, a PyCMSError
    is raised

    Use this function to obtain the information stored in the profile's
    info tag.  This often contains details about the profile, and how it
    was created, as supplied by the creator.

    :param profile: EITHER a valid CmsProfile object, OR a string of the filename
        of an ICC profile.
    :returns: A string containing the internal profile information stored in an ICC
        tag.
    :exception PyCMSError:
    """
    
    try:
        if not isinstance(profile, ImageCmsProfile):
            profile = ImageCmsProfile(profile)
        # add an extra newline to preserve pyCMS compatibility
        # Python, not C. the white point bits weren't working well, so skipping.
        #    // info was description \r\n\r\n copyright \r\n\r\n K007 tag \r\n\r\n whitepoint
        description = profile.profile.product_description
        cpright = profile.profile.product_copyright
        arr = []
        for elt in (description, cpright):
            if elt:
                arr.append(elt)
        return "\r\n\r\n".join(arr)+"\r\n\r\n"

    except (AttributeError, IOError, TypeError, ValueError) as v:
        raise PyCMSError(v)


def getProfileCopyright(profile):
    """
    (pyCMS) Gets the copyright for the given profile.

    If profile isn't a valid CmsProfile object or filename to a profile,
    a PyCMSError is raised.

    If an error occurs while trying to obtain the copyright tag, a PyCMSError
    is raised

    Use this function to obtain the information stored in the profile's
    copyright tag.  

    :param profile: EITHER a valid CmsProfile object, OR a string of the filename
        of an ICC profile.
    :returns: A string containing the internal profile information stored in an ICC
        tag.
    :exception PyCMSError:
    """
    try:
        # add an extra newline to preserve pyCMS compatibility
        if not isinstance(profile, ImageCmsProfile):
            profile = ImageCmsProfile(profile)
        return profile.profile.product_copyright + "\n"
    except (AttributeError, IOError, TypeError, ValueError) as v:
        raise PyCMSError(v)

def getProfileManufacturer(profile):
    """
    (pyCMS) Gets the manufacturer for the given profile.

    If profile isn't a valid CmsProfile object or filename to a profile,
    a PyCMSError is raised.

    If an error occurs while trying to obtain the manufacturer tag, a PyCMSError
    is raised

    Use this function to obtain the information stored in the profile's
    manufacturer tag.  

    :param profile: EITHER a valid CmsProfile object, OR a string of the filename
        of an ICC profile.
    :returns: A string containing the internal profile information stored in an ICC
        tag.
    :exception PyCMSError:
    """
    try:
        # add an extra newline to preserve pyCMS compatibility
        if not isinstance(profile, ImageCmsProfile):
            profile = ImageCmsProfile(profile)
        return profile.profile.product_manufacturer + "\n"
    except (AttributeError, IOError, TypeError, ValueError) as v:
        raise PyCMSError(v)

def getProfileModel(profile):
    """
    (pyCMS) Gets the model for the given profile.
    
    If profile isn't a valid CmsProfile object or filename to a profile,
    a PyCMSError is raised.
    
    If an error occurs while trying to obtain the model tag, a PyCMSError
    is raised
    
    Use this function to obtain the information stored in the profile's
    model tag.  
    
    :param profile: EITHER a valid CmsProfile object, OR a string of the filename
        of an ICC profile.
    :returns: A string containing the internal profile information stored in an ICC
        tag.
    :exception PyCMSError:
    """

    try:
        # add an extra newline to preserve pyCMS compatibility
        if not isinstance(profile, ImageCmsProfile):
            profile = ImageCmsProfile(profile)
        return profile.profile.product_model + "\n"
    except (AttributeError, IOError, TypeError, ValueError) as v:
        raise PyCMSError(v)

def getProfileDescription(profile):
    """
    (pyCMS) Gets the description for the given profile.

    If profile isn't a valid CmsProfile object or filename to a profile,
    a PyCMSError is raised.

    If an error occurs while trying to obtain the description tag, a PyCMSError
    is raised

    Use this function to obtain the information stored in the profile's
    description tag.  

    :param profile: EITHER a valid CmsProfile object, OR a string of the filename
        of an ICC profile.
    :returns: A string containing the internal profile information stored in an ICC
        tag.
    :exception PyCMSError:
    """

    try:
        # add an extra newline to preserve pyCMS compatibility
        if not isinstance(profile, ImageCmsProfile):
            profile = ImageCmsProfile(profile)
        return profile.profile.product_description + "\n"
    except (AttributeError, IOError, TypeError, ValueError) as v:
        raise PyCMSError(v)


def getDefaultIntent(profile):
    """
    (pyCMS) Gets the default intent name for the given profile.

    If profile isn't a valid CmsProfile object or filename to a profile,
    a PyCMSError is raised.

    If an error occurs while trying to obtain the default intent, a
    PyCMSError is raised.

    Use this function to determine the default (and usually best optomized)
    rendering intent for this profile.  Most profiles support multiple
    rendering intents, but are intended mostly for one type of conversion.
    If you wish to use a different intent than returned, use
    ImageCms.isIntentSupported() to verify it will work first.

    :param profile: EITHER a valid CmsProfile object, OR a string of the filename
        of an ICC profile.
    :returns: Integer 0-3 specifying the default rendering intent for this profile.

            INTENT_PERCEPTUAL            = 0 (DEFAULT) (ImageCms.INTENT_PERCEPTUAL)
            INTENT_RELATIVE_COLORIMETRIC = 1 (ImageCms.INTENT_RELATIVE_COLORIMETRIC)
            INTENT_SATURATION            = 2 (ImageCms.INTENT_SATURATION)
            INTENT_ABSOLUTE_COLORIMETRIC = 3 (ImageCms.INTENT_ABSOLUTE_COLORIMETRIC)

        see the pyCMS documentation for details on rendering intents and what they do.
    :exception PyCMSError:
    """

    try:
        if not isinstance(profile, ImageCmsProfile):
            profile = ImageCmsProfile(profile)
        return profile.profile.rendering_intent
    except (AttributeError, IOError, TypeError, ValueError) as v:
        raise PyCMSError(v)

def isIntentSupported(profile, intent, direction):
    """
    (pyCMS) Checks if a given intent is supported.

    Use this function to verify that you can use your desired
    renderingIntent with profile, and that profile can be used for the
    input/output/proof profile as you desire.

    Some profiles are created specifically for one "direction", can cannot
     be used for others.  Some profiles can only be used for certain
    rendering intents... so it's best to either verify this before trying
    to create a transform with them (using this function), or catch the
    potential PyCMSError that will occur if they don't support the modes
    you select.

    :param profile: EITHER a valid CmsProfile object, OR a string of the filename
        of an ICC profile.
    :param intent: Integer (0-3) specifying the rendering intent you wish to use
        with this profile

            INTENT_PERCEPTUAL            = 0 (DEFAULT) (ImageCms.INTENT_PERCEPTUAL)
            INTENT_RELATIVE_COLORIMETRIC = 1 (ImageCms.INTENT_RELATIVE_COLORIMETRIC)
            INTENT_SATURATION            = 2 (ImageCms.INTENT_SATURATION)
            INTENT_ABSOLUTE_COLORIMETRIC = 3 (ImageCms.INTENT_ABSOLUTE_COLORIMETRIC)

        see the pyCMS documentation for details on rendering intents and what they do.
    :param direction: Integer specifing if the profile is to be used for input,
        output, or proof

            INPUT  = 0 (or use ImageCms.DIRECTION_INPUT)
            OUTPUT = 1 (or use ImageCms.DIRECTION_OUTPUT)
            PROOF  = 2 (or use ImageCms.DIRECTION_PROOF)

    :returns: 1 if the intent/direction are supported, -1 if they are not.
    :exception PyCMSError:
    """

    try:
        if not isinstance(profile, ImageCmsProfile):
            profile = ImageCmsProfile(profile)
        # FIXME: I get different results for the same data w. different
        # compilers.  Bug in LittleCMS or in the binding?
        if profile.profile.is_intent_supported(intent, direction):
            return 1
        else:
            return -1
    except (AttributeError, IOError, TypeError, ValueError) as v:
        raise PyCMSError(v)

def versions():
    """
    (pyCMS) Fetches versions.
    """
    
    import sys
    return (
        VERSION, core.littlecms_version, sys.version.split()[0], Image.VERSION
        )

# --------------------------------------------------------------------

if __name__ == "__main__":
    # create a cheap manual from the __doc__ strings for the functions above

    from PIL import ImageCms
    print(__doc__)

    for f in dir(pyCMS):
        print("="*80)
        print("%s" %f)

        try:
            exec ("doc = ImageCms.%s.__doc__" %(f))
            if "pyCMS" in doc:
                # so we don't get the __doc__ string for imported modules
                print(doc)
        except AttributeError:
            pass

########NEW FILE########
__FILENAME__ = ImageColor
#
# The Python Imaging Library
# $Id$
#
# map CSS3-style colour description strings to RGB
#
# History:
# 2002-10-24 fl   Added support for CSS-style color strings
# 2002-12-15 fl   Added RGBA support
# 2004-03-27 fl   Fixed remaining int() problems for Python 1.5.2
# 2004-07-19 fl   Fixed gray/grey spelling issues
# 2009-03-05 fl   Fixed rounding error in grayscale calculation
#
# Copyright (c) 2002-2004 by Secret Labs AB
# Copyright (c) 2002-2004 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

from PIL import Image
import re

def getrgb(color):
    """
     Convert a color string to an RGB tuple. If the string cannot be parsed,
     this function raises a :py:exc:`ValueError` exception.

    .. versionadded:: 1.1.4

    :param color: A color string
    :return: ``(red, green, blue[, alpha])``
    """
    try:
        rgb = colormap[color]
    except KeyError:
        try:
            # fall back on case-insensitive lookup
            rgb = colormap[color.lower()]
        except KeyError:
            rgb = None
    # found color in cache
    if rgb:
        if isinstance(rgb, tuple):
            return rgb
        colormap[color] = rgb = getrgb(rgb)
        return rgb
    # check for known string formats
    m = re.match("#\w\w\w$", color)
    if m:
        return (
            int(color[1]*2, 16),
            int(color[2]*2, 16),
            int(color[3]*2, 16)
            )
    m = re.match("#\w\w\w\w\w\w$", color)
    if m:
        return (
            int(color[1:3], 16),
            int(color[3:5], 16),
            int(color[5:7], 16)
            )
    m = re.match("rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$", color)
    if m:
        return (
            int(m.group(1)),
            int(m.group(2)),
            int(m.group(3))
            )
    m = re.match("rgb\(\s*(\d+)%\s*,\s*(\d+)%\s*,\s*(\d+)%\s*\)$", color)
    if m:
        return (
            int((int(m.group(1)) * 255) / 100.0 + 0.5),
            int((int(m.group(2)) * 255) / 100.0 + 0.5),
            int((int(m.group(3)) * 255) / 100.0 + 0.5)
            )
    m = re.match("hsl\(\s*(\d+)\s*,\s*(\d+)%\s*,\s*(\d+)%\s*\)$", color)
    if m:
        from colorsys import hls_to_rgb
        rgb = hls_to_rgb(
            float(m.group(1)) / 360.0,
            float(m.group(3)) / 100.0,
            float(m.group(2)) / 100.0,
            )
        return (
            int(rgb[0] * 255 + 0.5),
            int(rgb[1] * 255 + 0.5),
            int(rgb[2] * 255 + 0.5)
            )
    m = re.match("rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$", color)
    if m:
        return (
            int(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
            int(m.group(4))
            )
    raise ValueError("unknown color specifier: %r" % color)

def getcolor(color, mode):
    """
    Same as :py:func:`~PIL.ImageColor.getrgb`, but converts the RGB value to a
    greyscale value if the mode is not color or a palette image. If the string
    cannot be parsed, this function raises a :py:exc:`ValueError` exception.

    .. versionadded:: 1.1.4

    :param color: A color string
    :return: ``(graylevel [, alpha]) or (red, green, blue[, alpha])``
    """
    # same as getrgb, but converts the result to the given mode
    color, alpha = getrgb(color), 255
    if len(color) == 4:
        color, alpha = color[0:3], color[3]

    if Image.getmodebase(mode) == "L":
        r, g, b = color
        color = (r*299 + g*587 + b*114)//1000
        if mode[-1] == 'A':
            return (color, alpha)
    else:
        if mode[-1] == 'A':
            return color + (alpha,)
    return color

colormap = {
    # X11 colour table (from "CSS3 module: Color working draft"), with
    # gray/grey spelling issues fixed.  This is a superset of HTML 4.0
    # colour names used in CSS 1.
    "aliceblue": "#f0f8ff",
    "antiquewhite": "#faebd7",
    "aqua": "#00ffff",
    "aquamarine": "#7fffd4",
    "azure": "#f0ffff",
    "beige": "#f5f5dc",
    "bisque": "#ffe4c4",
    "black": "#000000",
    "blanchedalmond": "#ffebcd",
    "blue": "#0000ff",
    "blueviolet": "#8a2be2",
    "brown": "#a52a2a",
    "burlywood": "#deb887",
    "cadetblue": "#5f9ea0",
    "chartreuse": "#7fff00",
    "chocolate": "#d2691e",
    "coral": "#ff7f50",
    "cornflowerblue": "#6495ed",
    "cornsilk": "#fff8dc",
    "crimson": "#dc143c",
    "cyan": "#00ffff",
    "darkblue": "#00008b",
    "darkcyan": "#008b8b",
    "darkgoldenrod": "#b8860b",
    "darkgray": "#a9a9a9",
    "darkgrey": "#a9a9a9",
    "darkgreen": "#006400",
    "darkkhaki": "#bdb76b",
    "darkmagenta": "#8b008b",
    "darkolivegreen": "#556b2f",
    "darkorange": "#ff8c00",
    "darkorchid": "#9932cc",
    "darkred": "#8b0000",
    "darksalmon": "#e9967a",
    "darkseagreen": "#8fbc8f",
    "darkslateblue": "#483d8b",
    "darkslategray": "#2f4f4f",
    "darkslategrey": "#2f4f4f",
    "darkturquoise": "#00ced1",
    "darkviolet": "#9400d3",
    "deeppink": "#ff1493",
    "deepskyblue": "#00bfff",
    "dimgray": "#696969",
    "dimgrey": "#696969",
    "dodgerblue": "#1e90ff",
    "firebrick": "#b22222",
    "floralwhite": "#fffaf0",
    "forestgreen": "#228b22",
    "fuchsia": "#ff00ff",
    "gainsboro": "#dcdcdc",
    "ghostwhite": "#f8f8ff",
    "gold": "#ffd700",
    "goldenrod": "#daa520",
    "gray": "#808080",
    "grey": "#808080",
    "green": "#008000",
    "greenyellow": "#adff2f",
    "honeydew": "#f0fff0",
    "hotpink": "#ff69b4",
    "indianred": "#cd5c5c",
    "indigo": "#4b0082",
    "ivory": "#fffff0",
    "khaki": "#f0e68c",
    "lavender": "#e6e6fa",
    "lavenderblush": "#fff0f5",
    "lawngreen": "#7cfc00",
    "lemonchiffon": "#fffacd",
    "lightblue": "#add8e6",
    "lightcoral": "#f08080",
    "lightcyan": "#e0ffff",
    "lightgoldenrodyellow": "#fafad2",
    "lightgreen": "#90ee90",
    "lightgray": "#d3d3d3",
    "lightgrey": "#d3d3d3",
    "lightpink": "#ffb6c1",
    "lightsalmon": "#ffa07a",
    "lightseagreen": "#20b2aa",
    "lightskyblue": "#87cefa",
    "lightslategray": "#778899",
    "lightslategrey": "#778899",
    "lightsteelblue": "#b0c4de",
    "lightyellow": "#ffffe0",
    "lime": "#00ff00",
    "limegreen": "#32cd32",
    "linen": "#faf0e6",
    "magenta": "#ff00ff",
    "maroon": "#800000",
    "mediumaquamarine": "#66cdaa",
    "mediumblue": "#0000cd",
    "mediumorchid": "#ba55d3",
    "mediumpurple": "#9370db",
    "mediumseagreen": "#3cb371",
    "mediumslateblue": "#7b68ee",
    "mediumspringgreen": "#00fa9a",
    "mediumturquoise": "#48d1cc",
    "mediumvioletred": "#c71585",
    "midnightblue": "#191970",
    "mintcream": "#f5fffa",
    "mistyrose": "#ffe4e1",
    "moccasin": "#ffe4b5",
    "navajowhite": "#ffdead",
    "navy": "#000080",
    "oldlace": "#fdf5e6",
    "olive": "#808000",
    "olivedrab": "#6b8e23",
    "orange": "#ffa500",
    "orangered": "#ff4500",
    "orchid": "#da70d6",
    "palegoldenrod": "#eee8aa",
    "palegreen": "#98fb98",
    "paleturquoise": "#afeeee",
    "palevioletred": "#db7093",
    "papayawhip": "#ffefd5",
    "peachpuff": "#ffdab9",
    "peru": "#cd853f",
    "pink": "#ffc0cb",
    "plum": "#dda0dd",
    "powderblue": "#b0e0e6",
    "purple": "#800080",
    "red": "#ff0000",
    "rosybrown": "#bc8f8f",
    "royalblue": "#4169e1",
    "saddlebrown": "#8b4513",
    "salmon": "#fa8072",
    "sandybrown": "#f4a460",
    "seagreen": "#2e8b57",
    "seashell": "#fff5ee",
    "sienna": "#a0522d",
    "silver": "#c0c0c0",
    "skyblue": "#87ceeb",
    "slateblue": "#6a5acd",
    "slategray": "#708090",
    "slategrey": "#708090",
    "snow": "#fffafa",
    "springgreen": "#00ff7f",
    "steelblue": "#4682b4",
    "tan": "#d2b48c",
    "teal": "#008080",
    "thistle": "#d8bfd8",
    "tomato": "#ff6347",
    "turquoise": "#40e0d0",
    "violet": "#ee82ee",
    "wheat": "#f5deb3",
    "white": "#ffffff",
    "whitesmoke": "#f5f5f5",
    "yellow": "#ffff00",
    "yellowgreen": "#9acd32",
}

########NEW FILE########
__FILENAME__ = ImageDraw
#
# The Python Imaging Library
# $Id$
#
# drawing interface operations
#
# History:
# 1996-04-13 fl   Created (experimental)
# 1996-08-07 fl   Filled polygons, ellipses.
# 1996-08-13 fl   Added text support
# 1998-06-28 fl   Handle I and F images
# 1998-12-29 fl   Added arc; use arc primitive to draw ellipses
# 1999-01-10 fl   Added shape stuff (experimental)
# 1999-02-06 fl   Added bitmap support
# 1999-02-11 fl   Changed all primitives to take options
# 1999-02-20 fl   Fixed backwards compatibility
# 2000-10-12 fl   Copy on write, when necessary
# 2001-02-18 fl   Use default ink for bitmap/text also in fill mode
# 2002-10-24 fl   Added support for CSS-style color strings
# 2002-12-10 fl   Added experimental support for RGBA-on-RGB drawing
# 2002-12-11 fl   Refactored low-level drawing API (work in progress)
# 2004-08-26 fl   Made Draw() a factory function, added getdraw() support
# 2004-09-04 fl   Added width support to line primitive
# 2004-09-10 fl   Added font mode handling
# 2006-06-19 fl   Added font bearing support (getmask2)
#
# Copyright (c) 1997-2006 by Secret Labs AB
# Copyright (c) 1996-2006 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

import numbers

from PIL import Image, ImageColor
from PIL._util import isStringType

try:
    import warnings
except ImportError:
    warnings = None

##
# A simple 2D drawing interface for PIL images.
# <p>
# Application code should use the <b>Draw</b> factory, instead of
# directly.

class ImageDraw:

    ##
    # Create a drawing instance.
    #
    # @param im The image to draw in.
    # @param mode Optional mode to use for color values.  For RGB
    #    images, this argument can be RGB or RGBA (to blend the
    #    drawing into the image).  For all other modes, this argument
    #    must be the same as the image mode.  If omitted, the mode
    #    defaults to the mode of the image.

    def __init__(self, im, mode=None):
        im.load()
        if im.readonly:
            im._copy() # make it writable
        blend = 0
        if mode is None:
            mode = im.mode
        if mode != im.mode:
            if mode == "RGBA" and im.mode == "RGB":
                blend = 1
            else:
                raise ValueError("mode mismatch")
        if mode == "P":
            self.palette = im.palette
        else:
            self.palette = None
        self.im = im.im
        self.draw = Image.core.draw(self.im, blend)
        self.mode = mode
        if mode in ("I", "F"):
            self.ink = self.draw.draw_ink(1, mode)
        else:
            self.ink = self.draw.draw_ink(-1, mode)
        if mode in ("1", "P", "I", "F"):
            # FIXME: fix Fill2 to properly support matte for I+F images
            self.fontmode = "1"
        else:
            self.fontmode = "L" # aliasing is okay for other modes
        self.fill = 0
        self.font = None

    ##
    # Set the default pen color.

    def setink(self, ink):
        # compatibility
        if warnings:
            warnings.warn(
                "'setink' is deprecated; use keyword arguments instead",
                DeprecationWarning, stacklevel=2
                )
        if isStringType(ink):
            ink = ImageColor.getcolor(ink, self.mode)
        if self.palette and not isinstance(ink, numbers.Number):
            ink = self.palette.getcolor(ink)
        self.ink = self.draw.draw_ink(ink, self.mode)

    ##
    # Set the default background color.

    def setfill(self, onoff):
        # compatibility
        if warnings:
            warnings.warn(
                "'setfill' is deprecated; use keyword arguments instead",
                DeprecationWarning, stacklevel=2
                )
        self.fill = onoff

    ##
    # Set the default font.

    def setfont(self, font):
        # compatibility
        self.font = font

    ##
    # Get the current default font.

    def getfont(self):
        if not self.font:
            # FIXME: should add a font repository
            from PIL import ImageFont
            self.font = ImageFont.load_default()
        return self.font

    def _getink(self, ink, fill=None):
        if ink is None and fill is None:
            if self.fill:
                fill = self.ink
            else:
                ink = self.ink
        else:
            if ink is not None:
                if isStringType(ink):
                    ink = ImageColor.getcolor(ink, self.mode)
                if self.palette and not isinstance(ink, numbers.Number):
                    ink = self.palette.getcolor(ink)
                ink = self.draw.draw_ink(ink, self.mode)
            if fill is not None:
                if isStringType(fill):
                    fill = ImageColor.getcolor(fill, self.mode)
                if self.palette and not isinstance(fill, numbers.Number):
                    fill = self.palette.getcolor(fill)
                fill = self.draw.draw_ink(fill, self.mode)
        return ink, fill

    ##
    # Draw an arc.

    def arc(self, xy, start, end, fill=None):
        ink, fill = self._getink(fill)
        if ink is not None:
            self.draw.draw_arc(xy, start, end, ink)

    ##
    # Draw a bitmap.

    def bitmap(self, xy, bitmap, fill=None):
        bitmap.load()
        ink, fill = self._getink(fill)
        if ink is None:
            ink = fill
        if ink is not None:
            self.draw.draw_bitmap(xy, bitmap.im, ink)

    ##
    # Draw a chord.

    def chord(self, xy, start, end, fill=None, outline=None):
        ink, fill = self._getink(outline, fill)
        if fill is not None:
            self.draw.draw_chord(xy, start, end, fill, 1)
        if ink is not None:
            self.draw.draw_chord(xy, start, end, ink, 0)

    ##
    # Draw an ellipse.

    def ellipse(self, xy, fill=None, outline=None):
        ink, fill = self._getink(outline, fill)
        if fill is not None:
            self.draw.draw_ellipse(xy, fill, 1)
        if ink is not None:
            self.draw.draw_ellipse(xy, ink, 0)

    ##
    # Draw a line, or a connected sequence of line segments.

    def line(self, xy, fill=None, width=0):
        ink, fill = self._getink(fill)
        if ink is not None:
            self.draw.draw_lines(xy, ink, width)

    ##
    # (Experimental) Draw a shape.

    def shape(self, shape, fill=None, outline=None):
        # experimental
        shape.close()
        ink, fill = self._getink(outline, fill)
        if fill is not None:
            self.draw.draw_outline(shape, fill, 1)
        if ink is not None:
            self.draw.draw_outline(shape, ink, 0)

    ##
    # Draw a pieslice.

    def pieslice(self, xy, start, end, fill=None, outline=None):
        ink, fill = self._getink(outline, fill)
        if fill is not None:
            self.draw.draw_pieslice(xy, start, end, fill, 1)
        if ink is not None:
            self.draw.draw_pieslice(xy, start, end, ink, 0)

    ##
    # Draw one or more individual pixels.

    def point(self, xy, fill=None):
        ink, fill = self._getink(fill)
        if ink is not None:
            self.draw.draw_points(xy, ink)

    ##
    # Draw a polygon.

    def polygon(self, xy, fill=None, outline=None):
        ink, fill = self._getink(outline, fill)
        if fill is not None:
            self.draw.draw_polygon(xy, fill, 1)
        if ink is not None:
            self.draw.draw_polygon(xy, ink, 0)

    ##
    # Draw a rectangle.

    def rectangle(self, xy, fill=None, outline=None):
        ink, fill = self._getink(outline, fill)
        if fill is not None:
            self.draw.draw_rectangle(xy, fill, 1)
        if ink is not None:
            self.draw.draw_rectangle(xy, ink, 0)

    ##
    # Draw text.

    def text(self, xy, text, fill=None, font=None, anchor=None):
        ink, fill = self._getink(fill)
        if font is None:
            font = self.getfont()
        if ink is None:
            ink = fill
        if ink is not None:
            try:
                mask, offset = font.getmask2(text, self.fontmode)
                xy = xy[0] + offset[0], xy[1] + offset[1]
            except AttributeError:
                try:
                    mask = font.getmask(text, self.fontmode)
                except TypeError:
                    mask = font.getmask(text)
            self.draw.draw_bitmap(xy, mask, ink)

    ##
    # Get the size of a given string, in pixels.

    def textsize(self, text, font=None):
        if font is None:
            font = self.getfont()
        return font.getsize(text)

##
# A simple 2D drawing interface for PIL images.
#
# @param im The image to draw in.
# @param mode Optional mode to use for color values.  For RGB
#    images, this argument can be RGB or RGBA (to blend the
#    drawing into the image).  For all other modes, this argument
#    must be the same as the image mode.  If omitted, the mode
#    defaults to the mode of the image.

def Draw(im, mode=None):
    try:
        return im.getdraw(mode)
    except AttributeError:
        return ImageDraw(im, mode)

# experimental access to the outline API
try:
    Outline = Image.core.outline
except:
    Outline = None

##
# (Experimental) A more advanced 2D drawing interface for PIL images,
# based on the WCK interface.
#
# @param im The image to draw in.
# @param hints An optional list of hints.
# @return A (drawing context, drawing resource factory) tuple.

def getdraw(im=None, hints=None):
    # FIXME: this needs more work!
    # FIXME: come up with a better 'hints' scheme.
    handler = None
    if not hints or "nicest" in hints:
        try:
            from PIL import _imagingagg as handler
        except ImportError:
            pass
    if handler is None:
        from PIL import ImageDraw2 as handler
    if im:
        im = handler.Draw(im)
    return im, handler

##
# (experimental) Fills a bounded region with a given color.
#
# @param image Target image.
# @param xy Seed position (a 2-item coordinate tuple).
# @param value Fill color.
# @param border Optional border value.  If given, the region consists of
#     pixels with a color different from the border color.  If not given,
#     the region consists of pixels having the same color as the seed
#     pixel.

def floodfill(image, xy, value, border=None):
    "Fill bounded region."
    # based on an implementation by Eric S. Raymond
    pixel = image.load()
    x, y = xy
    try:
        background = pixel[x, y]
        if background == value:
            return # seed point already has fill color
        pixel[x, y] = value
    except IndexError:
        return # seed point outside image
    edge = [(x, y)]
    if border is None:
        while edge:
            newedge = []
            for (x, y) in edge:
                for (s, t) in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
                    try:
                        p = pixel[s, t]
                    except IndexError:
                        pass
                    else:
                        if p == background:
                            pixel[s, t] = value
                            newedge.append((s, t))
            edge = newedge
    else:
        while edge:
            newedge = []
            for (x, y) in edge:
                for (s, t) in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
                    try:
                        p = pixel[s, t]
                    except IndexError:
                        pass
                    else:
                        if p != value and p != border:
                            pixel[s, t] = value
                            newedge.append((s, t))
            edge = newedge

########NEW FILE########
__FILENAME__ = ImageDraw2
#
# The Python Imaging Library
# $Id$
#
# WCK-style drawing interface operations
#
# History:
# 2003-12-07 fl   created
# 2005-05-15 fl   updated; added to PIL as ImageDraw2
# 2005-05-15 fl   added text support
# 2005-05-20 fl   added arc/chord/pieslice support
#
# Copyright (c) 2003-2005 by Secret Labs AB
# Copyright (c) 2003-2005 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

from PIL import Image, ImageColor, ImageDraw, ImageFont, ImagePath

class Pen:
    def __init__(self, color, width=1, opacity=255):
        self.color = ImageColor.getrgb(color)
        self.width = width

class Brush:
    def __init__(self, color, opacity=255):
        self.color = ImageColor.getrgb(color)

class Font:
    def __init__(self, color, file, size=12):
        # FIXME: add support for bitmap fonts
        self.color = ImageColor.getrgb(color)
        self.font = ImageFont.truetype(file, size)

class Draw:

    def __init__(self, image, size=None, color=None):
        if not hasattr(image, "im"):
            image = Image.new(image, size, color)
        self.draw = ImageDraw.Draw(image)
        self.image = image
        self.transform = None

    def flush(self):
        return self.image

    def render(self, op, xy, pen, brush=None):
        # handle color arguments
        outline = fill = None; width = 1
        if isinstance(pen, Pen):
            outline = pen.color
            width = pen.width
        elif isinstance(brush, Pen):
            outline = brush.color
            width = brush.width
        if isinstance(brush, Brush):
            fill = brush.color
        elif isinstance(pen, Brush):
            fill = pen.color
        # handle transformation
        if self.transform:
            xy = ImagePath.Path(xy)
            xy.transform(self.transform)
        # render the item
        if op == "line":
            self.draw.line(xy, fill=outline, width=width)
        else:
            getattr(self.draw, op)(xy, fill=fill, outline=outline)

    def settransform(self, offset):
        (xoffset, yoffset) = offset
        self.transform = (1, 0, xoffset, 0, 1, yoffset)

    def arc(self, xy, start, end, *options):
        self.render("arc", xy, start, end, *options)

    def chord(self, xy, start, end, *options):
        self.render("chord", xy, start, end, *options)

    def ellipse(self, xy, *options):
        self.render("ellipse", xy, *options)

    def line(self, xy, *options):
        self.render("line", xy, *options)

    def pieslice(self, xy, start, end, *options):
        self.render("pieslice", xy, start, end, *options)

    def polygon(self, xy, *options):
        self.render("polygon", xy, *options)

    def rectangle(self, xy, *options):
        self.render("rectangle", xy, *options)

    def symbol(self, xy, symbol, *options):
        raise NotImplementedError("not in this version")

    def text(self, xy, text, font):
        if self.transform:
            xy = ImagePath.Path(xy)
            xy.transform(self.transform)
        self.draw.text(xy, text, font=font.font, fill=font.color)

    def textsize(self, text, font):
        return self.draw.textsize(text, font=font.font)

########NEW FILE########
__FILENAME__ = ImageEnhance
#
# The Python Imaging Library.
# $Id$
#
# image enhancement classes
#
# For a background, see "Image Processing By Interpolation and
# Extrapolation", Paul Haeberli and Douglas Voorhies.  Available
# at http://www.sgi.com/grafica/interp/index.html
#
# History:
# 1996-03-23 fl  Created
# 2009-06-16 fl  Fixed mean calculation
#
# Copyright (c) Secret Labs AB 1997.
# Copyright (c) Fredrik Lundh 1996.
#
# See the README file for information on usage and redistribution.
#

from PIL import Image, ImageFilter, ImageStat


class _Enhance:

    def enhance(self, factor):
        """
        Returns an enhanced image.

        :param factor: A floating point value controlling the enhancement.
                       Factor 1.0 always returns a copy of the original image,
                       lower factors mean less color (brightness, contrast,
                       etc), and higher values more. There are no restrictions
                       on this value.
        :rtype: :py:class:`~PIL.Image.Image`
        """
        return Image.blend(self.degenerate, self.image, factor)


class Color(_Enhance):
    """Adjust image color balance.

    This class can be used to adjust the colour balance of an image, in
    a manner similar to the controls on a colour TV set. An enhancement
    factor of 0.0 gives a black and white image. A factor of 1.0 gives
    the original image.
    """
    def __init__(self, image):
        self.image = image
        self.degenerate = image.convert("L").convert(image.mode)


class Contrast(_Enhance):
    """Adjust image contrast.

    This class can be used to control the contrast of an image, similar
    to the contrast control on a TV set. An enhancement factor of 0.0
    gives a solid grey image. A factor of 1.0 gives the original image.
    """
    def __init__(self, image):
        self.image = image
        mean = int(ImageStat.Stat(image.convert("L")).mean[0] + 0.5)
        self.degenerate = Image.new("L", image.size, mean).convert(image.mode)


class Brightness(_Enhance):
    """Adjust image brightness.

    This class can be used to control the brighntess of an image.  An
    enhancement factor of 0.0 gives a black image. A factor of 1.0 gives the
    original image.
    """
    def __init__(self, image):
        self.image = image
        self.degenerate = Image.new(image.mode, image.size, 0)


class Sharpness(_Enhance):
    """Adjust image sharpness.

    This class can be used to adjust the sharpness of an image. An
    enhancement factor of 0.0 gives a blurred image, a factor of 1.0 gives the
    original image, and a factor of 2.0 gives a sharpened image.
    """
    def __init__(self, image):
        self.image = image
        self.degenerate = image.filter(ImageFilter.SMOOTH)

########NEW FILE########
__FILENAME__ = ImageFile
#
# The Python Imaging Library.
# $Id$
#
# base class for image file handlers
#
# history:
# 1995-09-09 fl   Created
# 1996-03-11 fl   Fixed load mechanism.
# 1996-04-15 fl   Added pcx/xbm decoders.
# 1996-04-30 fl   Added encoders.
# 1996-12-14 fl   Added load helpers
# 1997-01-11 fl   Use encode_to_file where possible
# 1997-08-27 fl   Flush output in _save
# 1998-03-05 fl   Use memory mapping for some modes
# 1999-02-04 fl   Use memory mapping also for "I;16" and "I;16B"
# 1999-05-31 fl   Added image parser
# 2000-10-12 fl   Set readonly flag on memory-mapped images
# 2002-03-20 fl   Use better messages for common decoder errors
# 2003-04-21 fl   Fall back on mmap/map_buffer if map is not available
# 2003-10-30 fl   Added StubImageFile class
# 2004-02-25 fl   Made incremental parser more robust
#
# Copyright (c) 1997-2004 by Secret Labs AB
# Copyright (c) 1995-2004 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

from PIL import Image
from PIL._util import isPath
import traceback, os, sys
import io

MAXBLOCK = 65536

SAFEBLOCK = 1024*1024

LOAD_TRUNCATED_IMAGES = False

ERRORS = {
    -1: "image buffer overrun error",
    -2: "decoding error",
    -3: "unknown error",
    -8: "bad configuration",
    -9: "out of memory error"
}

def raise_ioerror(error):
    try:
        message = Image.core.getcodecstatus(error)
    except AttributeError:
        message = ERRORS.get(error)
    if not message:
        message = "decoder error %d" % error
    raise IOError(message + " when reading image file")

#
# --------------------------------------------------------------------
# Helpers

def _tilesort(t):
    # sort on offset
    return t[2]

#
# --------------------------------------------------------------------
# ImageFile base class

class ImageFile(Image.Image):
    "Base class for image file format handlers."

    def __init__(self, fp=None, filename=None):
        Image.Image.__init__(self)

        self.tile = None
        self.readonly = 1 # until we know better

        self.decoderconfig = ()
        self.decodermaxblock = MAXBLOCK

        if isPath(fp):
            # filename
            self.fp = open(fp, "rb")
            self.filename = fp
        else:
            # stream
            self.fp = fp
            self.filename = filename

        try:
            self._open()
        except IndexError as v: # end of data
            if Image.DEBUG > 1:
                traceback.print_exc()
            raise SyntaxError(v)
        except TypeError as v: # end of data (ord)
            if Image.DEBUG > 1:
                traceback.print_exc()
            raise SyntaxError(v)
        except KeyError as v: # unsupported mode
            if Image.DEBUG > 1:
                traceback.print_exc()
            raise SyntaxError(v)
        except EOFError as v: # got header but not the first frame
            if Image.DEBUG > 1:
                traceback.print_exc()
            raise SyntaxError(v)

        if not self.mode or self.size[0] <= 0:
            raise SyntaxError("not identified by this driver")

    def draft(self, mode, size):
        "Set draft mode"

        pass

    def verify(self):
        "Check file integrity"

        # raise exception if something's wrong.  must be called
        # directly after open, and closes file when finished.
        self.fp = None

    def load(self):
        "Load image data based on tile list"

        pixel = Image.Image.load(self)

        if self.tile is None:
            raise IOError("cannot load this image")
        if not self.tile:
            return pixel

        self.map = None

        readonly = 0

        if self.filename and len(self.tile) == 1 and not hasattr(sys, 'pypy_version_info'):
            # As of pypy 2.1.0, memory mapping was failing here.
            # try memory mapping
            d, e, o, a = self.tile[0]
            if d == "raw" and a[0] == self.mode and a[0] in Image._MAPMODES:
                try:
                    if hasattr(Image.core, "map"):
                        # use built-in mapper
                        self.map = Image.core.map(self.filename)
                        self.map.seek(o)
                        self.im = self.map.readimage(
                            self.mode, self.size, a[1], a[2]
                            )
                    else:
                        # use mmap, if possible
                        import mmap
                        file = open(self.filename, "r+")
                        size = os.path.getsize(self.filename)
                        # FIXME: on Unix, use PROT_READ etc
                        self.map = mmap.mmap(file.fileno(), size)
                        self.im = Image.core.map_buffer(
                            self.map, self.size, d, e, o, a
                            )
                    readonly = 1
                except (AttributeError, EnvironmentError, ImportError):
                    self.map = None

        self.load_prepare()

        # look for read/seek overrides
        try:
            read = self.load_read
        except AttributeError:
            read = self.fp.read

        try:
            seek = self.load_seek
        except AttributeError:
            seek = self.fp.seek

        if not self.map:

            # sort tiles in file order
            self.tile.sort(key=_tilesort)

            try:
                # FIXME: This is a hack to handle TIFF's JpegTables tag.
                prefix = self.tile_prefix
            except AttributeError:
                prefix = b""

            for d, e, o, a in self.tile:
                d = Image._getdecoder(self.mode, d, a, self.decoderconfig)
                seek(o)
                try:
                    d.setimage(self.im, e)
                except ValueError:
                    continue
                b = prefix
                t = len(b)
                while True:
                    try:
                        s = read(self.decodermaxblock)
                    except IndexError as ie: # truncated png/gif
                        if LOAD_TRUNCATED_IMAGES:
                            break
                        else:
                            raise IndexError(ie)

                    if not s and not d.handles_eof: # truncated jpeg
                        self.tile = []

                        # JpegDecode needs to clean things up here either way
                        # If we don't destroy the decompressor, we have a memory leak.
                        d.cleanup()

                        if LOAD_TRUNCATED_IMAGES:
                            break
                        else:
                            raise IOError("image file is truncated (%d bytes not processed)" % len(b))

                    b = b + s
                    n, e = d.decode(b)
                    if n < 0:
                        break
                    b = b[n:]
                    t = t + n

        self.tile = []
        self.readonly = readonly

        self.fp = None # might be shared

        if not self.map and (not LOAD_TRUNCATED_IMAGES or t == 0) and e < 0:
            # still raised if decoder fails to return anything
            raise_ioerror(e)

        # post processing
        if hasattr(self, "tile_post_rotate"):
            # FIXME: This is a hack to handle rotated PCD's
            self.im = self.im.rotate(self.tile_post_rotate)
            self.size = self.im.size

        self.load_end()

        return Image.Image.load(self)

    def load_prepare(self):
        # create image memory if necessary
        if not self.im or\
           self.im.mode != self.mode or self.im.size != self.size:
            self.im = Image.core.new(self.mode, self.size)
        # create palette (optional)
        if self.mode == "P":
            Image.Image.load(self)

    def load_end(self):
        # may be overridden
        pass

    # may be defined for contained formats
    # def load_seek(self, pos):
    #     pass

    # may be defined for blocked formats (e.g. PNG)
    # def load_read(self, bytes):
    #     pass


class StubImageFile(ImageFile):
    """
    Base class for stub image loaders.

    A stub loader is an image loader that can identify files of a
    certain format, but relies on external code to load the file.
    """

    def _open(self):
        raise NotImplementedError(
            "StubImageFile subclass must implement _open"
            )

    def load(self):
        loader = self._load()
        if loader is None:
            raise IOError("cannot find loader for this %s file" % self.format)
        image = loader.load(self)
        assert image is not None
        # become the other object (!)
        self.__class__ = image.__class__
        self.__dict__ = image.__dict__

    def _load(self):
        "(Hook) Find actual image loader."
        raise NotImplementedError(
            "StubImageFile subclass must implement _load"
            )


class Parser:
    """
    Incremental image parser.  This class implements the standard
    feed/close consumer interface.

    In Python 2.x, this is an old-style class.
    """
    incremental = None
    image = None
    data = None
    decoder = None
    finished = 0

    def reset(self):
        """
        (Consumer) Reset the parser.  Note that you can only call this
        method immediately after you've created a parser; parser
        instances cannot be reused.
        """
        assert self.data is None, "cannot reuse parsers"

    def feed(self, data):
        """
        (Consumer) Feed data to the parser.

        :param data: A string buffer.
        :exception IOError: If the parser failed to parse the image file.
        """
        # collect data

        if self.finished:
            return

        if self.data is None:
            self.data = data
        else:
            self.data = self.data + data

        # parse what we have
        if self.decoder:

            if self.offset > 0:
                # skip header
                skip = min(len(self.data), self.offset)
                self.data = self.data[skip:]
                self.offset = self.offset - skip
                if self.offset > 0 or not self.data:
                    return

            n, e = self.decoder.decode(self.data)

            if n < 0:
                # end of stream
                self.data = None
                self.finished = 1
                if e < 0:
                    # decoding error
                    self.image = None
                    raise_ioerror(e)
                else:
                    # end of image
                    return
            self.data = self.data[n:]

        elif self.image:

            # if we end up here with no decoder, this file cannot
            # be incrementally parsed.  wait until we've gotten all
            # available data
            pass

        else:

            # attempt to open this file
            try:
                try:
                    fp = io.BytesIO(self.data)
                    im = Image.open(fp)
                finally:
                    fp.close() # explicitly close the virtual file
            except IOError:
                # traceback.print_exc()
                pass # not enough data
            else:
                flag = hasattr(im, "load_seek") or hasattr(im, "load_read")
                if flag or len(im.tile) != 1:
                    # custom load code, or multiple tiles
                    self.decode = None
                else:
                    # initialize decoder
                    im.load_prepare()
                    d, e, o, a = im.tile[0]
                    im.tile = []
                    self.decoder = Image._getdecoder(
                        im.mode, d, a, im.decoderconfig
                        )
                    self.decoder.setimage(im.im, e)

                    # calculate decoder offset
                    self.offset = o
                    if self.offset <= len(self.data):
                        self.data = self.data[self.offset:]
                        self.offset = 0

                self.image = im

    def close(self):
        """
        (Consumer) Close the stream.

        :returns: An image object.
        :exception IOError: If the parser failed to parse the image file either
                            because it cannot be identified or cannot be
                            decoded.
        """
        # finish decoding
        if self.decoder:
            # get rid of what's left in the buffers
            self.feed(b"")
            self.data = self.decoder = None
            if not self.finished:
                raise IOError("image was incomplete")
        if not self.image:
            raise IOError("cannot parse this image")
        if self.data:
            # incremental parsing not possible; reopen the file
            # not that we have all data
            try:
                fp = io.BytesIO(self.data)
                self.image = Image.open(fp)
            finally:
                self.image.load()
                fp.close() # explicitly close the virtual file
        return self.image

# --------------------------------------------------------------------

def _save(im, fp, tile, bufsize=0):
    """Helper to save image based on tile list

    :param im: Image object.
    :param fp: File object.
    :param tile: Tile list.
    :param bufsize: Optional buffer size
    """

    im.load()
    if not hasattr(im, "encoderconfig"):
        im.encoderconfig = ()
    tile.sort(key=_tilesort)
    # FIXME: make MAXBLOCK a configuration parameter
    # It would be great if we could have the encoder specifiy what it needs
    # But, it would need at least the image size in most cases. RawEncode is
    # a tricky case.
    bufsize = max(MAXBLOCK, bufsize, im.size[0] * 4) # see RawEncode.c
    try:
        fh = fp.fileno()
        fp.flush()
    except (AttributeError, io.UnsupportedOperation):
        # compress to Python file-compatible object
        for e, b, o, a in tile:
            e = Image._getencoder(im.mode, e, a, im.encoderconfig)
            if o > 0:
                fp.seek(o, 0)
            e.setimage(im.im, b)
            while True:
                l, s, d = e.encode(bufsize)
                fp.write(d)
                if s:
                    break
            if s < 0:
                raise IOError("encoder error %d when writing image file" % s)
    else:
        # slight speedup: compress to real file object
        for e, b, o, a in tile:
            e = Image._getencoder(im.mode, e, a, im.encoderconfig)
            if o > 0:
                fp.seek(o, 0)
            e.setimage(im.im, b)
            s = e.encode_to_file(fh, bufsize)
            if s < 0:
                raise IOError("encoder error %d when writing image file" % s)
    try:
        fp.flush()
    except: pass


def _safe_read(fp, size):
    """
    Reads large blocks in a safe way.  Unlike fp.read(n), this function
    doesn't trust the user.  If the requested size is larger than
    SAFEBLOCK, the file is read block by block.

    :param fp: File handle.  Must implement a <b>read</b> method.
    :param size: Number of bytes to read.
    :returns: A string containing up to <i>size</i> bytes of data.
    """
    if size <= 0:
        return b""
    if size <= SAFEBLOCK:
        return fp.read(size)
    data = []
    while size > 0:
        block = fp.read(min(size, SAFEBLOCK))
        if not block:
            break
        data.append(block)
        size = size - len(block)
    return b"".join(data)

########NEW FILE########
__FILENAME__ = ImageFileIO
#
# The Python Imaging Library.
# $Id$
#
# kludge to get basic ImageFileIO functionality
#
# History:
# 1998-08-06 fl   Recreated
#
# Copyright (c) Secret Labs AB 1998-2002.
#
# See the README file for information on usage and redistribution.
#
"""
The **ImageFileIO** module can be used to read an image from a
socket, or any other stream device.

Deprecated. New code should use the :class:`PIL.ImageFile.Parser`
class in the :mod:`PIL.ImageFile` module instead.

.. seealso:: modules :class:`PIL.ImageFile.Parser`
"""

from io import BytesIO


class ImageFileIO(BytesIO):
    def __init__(self, fp):
        """
        Adds buffering to a stream file object, in order to
        provide **seek** and **tell** methods required
        by the :func:`PIL.Image.Image.open` method. The stream object must
        implement **read** and **close** methods.

        :param fp: Stream file handle.

        .. seealso:: modules :func:`PIL.Image.open`
        """
        data = fp.read()
        BytesIO.__init__(self, data)

########NEW FILE########
__FILENAME__ = ImageFilter
#
# The Python Imaging Library.
# $Id$
#
# standard filters
#
# History:
# 1995-11-27 fl   Created
# 2002-06-08 fl   Added rank and mode filters
# 2003-09-15 fl   Fixed rank calculation in rank filter; added expand call
#
# Copyright (c) 1997-2003 by Secret Labs AB.
# Copyright (c) 1995-2002 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#

from functools import reduce


class Filter(object):
    pass


class Kernel(Filter):
    """
    Create a convolution kernel.  The current version only
    supports 3x3 and 5x5 integer and floating point kernels.

    In the current version, kernels can only be applied to
    "L" and "RGB" images.

    :param size: Kernel size, given as (width, height). In the current
                    version, this must be (3,3) or (5,5).
    :param kernel: A sequence containing kernel weights.
    :param scale: Scale factor. If given, the result for each pixel is
                    divided by this value.  the default is the sum of the
                    kernel weights.
    :param offset: Offset. If given, this value is added to the result,
                    after it has been divided by the scale factor.
    """

    def __init__(self, size, kernel, scale=None, offset=0):
        if scale is None:
            # default scale is sum of kernel
            scale = reduce(lambda a,b: a+b, kernel)
        if size[0] * size[1] != len(kernel):
            raise ValueError("not enough coefficients in kernel")
        self.filterargs = size, scale, offset, kernel

    def filter(self, image):
        if image.mode == "P":
            raise ValueError("cannot filter palette images")
        return image.filter(*self.filterargs)


class BuiltinFilter(Kernel):
    def __init__(self):
        pass


class RankFilter(Filter):
    """
    Create a rank filter.  The rank filter sorts all pixels in
    a window of the given size, and returns the **rank**'th value.

    :param size: The kernel size, in pixels.
    :param rank: What pixel value to pick.  Use 0 for a min filter,
                 ``size * size / 2`` for a median filter, ``size * size - 1``
                 for a max filter, etc.
    """
    name = "Rank"

    def __init__(self, size, rank):
        self.size = size
        self.rank = rank

    def filter(self, image):
        if image.mode == "P":
            raise ValueError("cannot filter palette images")
        image = image.expand(self.size//2, self.size//2)
        return image.rankfilter(self.size, self.rank)


class MedianFilter(RankFilter):
    """
    Create a median filter. Picks the median pixel value in a window with the
    given size.

    :param size: The kernel size, in pixels.
    """
    name = "Median"

    def __init__(self, size=3):
        self.size = size
        self.rank = size*size//2


class MinFilter(RankFilter):
    """
    Create a min filter.  Picks the lowest pixel value in a window with the
    given size.

    :param size: The kernel size, in pixels.
    """
    name = "Min"

    def __init__(self, size=3):
        self.size = size
        self.rank = 0


class MaxFilter(RankFilter):
    """
    Create a max filter.  Picks the largest pixel value in a window with the
    given size.

    :param size: The kernel size, in pixels.
    """
    name = "Max"

    def __init__(self, size=3):
        self.size = size
        self.rank = size*size-1


class ModeFilter(Filter):
    """

    Create a mode filter. Picks the most frequent pixel value in a box with the
    given size.  Pixel values that occur only once or twice are ignored; if no
    pixel value occurs more than twice, the original pixel value is preserved.

    :param size: The kernel size, in pixels.
    """
    name = "Mode"

    def __init__(self, size=3):
        self.size = size

    def filter(self, image):
        return image.modefilter(self.size)


class GaussianBlur(Filter):
    """Gaussian blur filter.

    :param radius: Blur radius.
    """
    name = "GaussianBlur"

    def __init__(self, radius=2):
        self.radius = radius

    def filter(self, image):
        return image.gaussian_blur(self.radius)


class UnsharpMask(Filter):
    """Unsharp mask filter.

    See Wikipedia's entry on `digital unsharp masking`_ for an explanation of
    the parameters.

    .. _digital unsharp masking: https://en.wikipedia.org/wiki/Unsharp_masking#Digital_unsharp_masking
    """
    name = "UnsharpMask"

    def __init__(self, radius=2, percent=150, threshold=3):
        self.radius = radius
        self.percent = percent
        self.threshold = threshold

    def filter(self, image):
        return image.unsharp_mask(self.radius, self.percent, self.threshold)


class BLUR(BuiltinFilter):
    name = "Blur"
    filterargs = (5, 5), 16, 0, (
        1,  1,  1,  1,  1,
        1,  0,  0,  0,  1,
        1,  0,  0,  0,  1,
        1,  0,  0,  0,  1,
        1,  1,  1,  1,  1
        )


class CONTOUR(BuiltinFilter):
    name = "Contour"
    filterargs = (3, 3), 1, 255, (
        -1, -1, -1,
        -1,  8, -1,
        -1, -1, -1
        )


class DETAIL(BuiltinFilter):
    name = "Detail"
    filterargs = (3, 3), 6, 0, (
        0, -1,  0,
        -1, 10, -1,
        0, -1,  0
        )


class EDGE_ENHANCE(BuiltinFilter):
    name = "Edge-enhance"
    filterargs = (3, 3), 2, 0, (
        -1, -1, -1,
        -1, 10, -1,
        -1, -1, -1
        )


class EDGE_ENHANCE_MORE(BuiltinFilter):
    name = "Edge-enhance More"
    filterargs = (3, 3), 1, 0, (
        -1, -1, -1,
        -1,  9, -1,
        -1, -1, -1
        )


class EMBOSS(BuiltinFilter):
    name = "Emboss"
    filterargs = (3, 3), 1, 128, (
        -1,  0,  0,
        0,  1,  0,
        0,  0,  0
        )


class FIND_EDGES(BuiltinFilter):
    name = "Find Edges"
    filterargs = (3, 3), 1, 0, (
        -1, -1, -1,
        -1,  8, -1,
        -1, -1, -1
        )


class SMOOTH(BuiltinFilter):
    name = "Smooth"
    filterargs = (3, 3), 13, 0, (
        1,  1,  1,
        1,  5,  1,
        1,  1,  1
        )


class SMOOTH_MORE(BuiltinFilter):
    name = "Smooth More"
    filterargs = (5, 5), 100, 0, (
        1,  1,  1,  1,  1,
        1,  5,  5,  5,  1,
        1,  5, 44,  5,  1,
        1,  5,  5,  5,  1,
        1,  1,  1,  1,  1
        )


class SHARPEN(BuiltinFilter):
    name = "Sharpen"
    filterargs = (3, 3), 16, 0, (
        -2, -2, -2,
        -2, 32, -2,
        -2, -2, -2
        )

########NEW FILE########
__FILENAME__ = ImageFont
#
# The Python Imaging Library.
# $Id$
#
# PIL raster font management
#
# History:
# 1996-08-07 fl   created (experimental)
# 1997-08-25 fl   minor adjustments to handle fonts from pilfont 0.3
# 1999-02-06 fl   rewrote most font management stuff in C
# 1999-03-17 fl   take pth files into account in load_path (from Richard Jones)
# 2001-02-17 fl   added freetype support
# 2001-05-09 fl   added TransposedFont wrapper class
# 2002-03-04 fl   make sure we have a "L" or "1" font
# 2002-12-04 fl   skip non-directory entries in the system path
# 2003-04-29 fl   add embedded default font
# 2003-09-27 fl   added support for truetype charmap encodings
#
# Todo:
# Adapt to PILFONT2 format (16-bit fonts, compressed, single file)
#
# Copyright (c) 1997-2003 by Secret Labs AB
# Copyright (c) 1996-2003 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

from __future__ import print_function

from PIL import Image
from PIL._util import isDirectory, isPath
import os, sys

try:
    import warnings
except ImportError:
    warnings = None

class _imagingft_not_installed:
    # module placeholder
    def __getattr__(self, id):
        raise ImportError("The _imagingft C module is not installed")

try:
    from PIL import _imagingft as core
except ImportError:
    core = _imagingft_not_installed()

# FIXME: add support for pilfont2 format (see FontFile.py)

# --------------------------------------------------------------------
# Font metrics format:
#       "PILfont" LF
#       fontdescriptor LF
#       (optional) key=value... LF
#       "DATA" LF
#       binary data: 256*10*2 bytes (dx, dy, dstbox, srcbox)
#
# To place a character, cut out srcbox and paste at dstbox,
# relative to the character position.  Then move the character
# position according to dx, dy.
# --------------------------------------------------------------------


class ImageFont:
    "PIL font wrapper"

    def _load_pilfont(self, filename):

        file = open(filename, "rb")

        for ext in (".png", ".gif", ".pbm"):
            try:
                fullname = os.path.splitext(filename)[0] + ext
                image = Image.open(fullname)
            except:
                pass
            else:
                if image and image.mode in ("1", "L"):
                    break
        else:
            raise IOError("cannot find glyph data file")

        self.file = fullname

        return self._load_pilfont_data(file, image)

    def _load_pilfont_data(self, file, image):

        # read PILfont header
        if file.readline() != b"PILfont\n":
            raise SyntaxError("Not a PILfont file")
        d = file.readline().split(b";")
        self.info = [] # FIXME: should be a dictionary
        while True:
            s = file.readline()
            if not s or s == b"DATA\n":
                break
            self.info.append(s)

        # read PILfont metrics
        data = file.read(256*20)

        # check image
        if image.mode not in ("1", "L"):
            raise TypeError("invalid font image mode")

        image.load()

        self.font = Image.core.font(image.im, data)

        # delegate critical operations to internal type
        self.getsize = self.font.getsize
        self.getmask = self.font.getmask

##
# Wrapper for FreeType fonts.  Application code should use the
# <b>truetype</b> factory function to create font objects.

class FreeTypeFont:
    "FreeType font wrapper (requires _imagingft service)"

    def __init__(self, font=None, size=10, index=0, encoding="", file=None):
        # FIXME: use service provider instead
        if file:
            if warnings:
                warnings.warn('file parameter deprecated, please use font parameter instead.', DeprecationWarning)
            font = file

        if isPath(font):
            self.font = core.getfont(font, size, index, encoding)
        else:
            self.font_bytes = font.read()
            self.font = core.getfont("", size, index, encoding, self.font_bytes)

    def getname(self):
        return self.font.family, self.font.style

    def getmetrics(self):
        return self.font.ascent, self.font.descent

    def getsize(self, text):
        return self.font.getsize(text)[0]

    def getoffset(self, text):
        return self.font.getsize(text)[1]

    def getmask(self, text, mode=""):
        return self.getmask2(text, mode)[0]

    def getmask2(self, text, mode="", fill=Image.core.fill):
        size, offset = self.font.getsize(text)
        im = fill("L", size, 0)
        self.font.render(text, im.id, mode=="1")
        return im, offset

##
# Wrapper that creates a transposed font from any existing font
# object.
#
# @param font A font object.
# @param orientation An optional orientation.  If given, this should
#     be one of Image.FLIP_LEFT_RIGHT, Image.FLIP_TOP_BOTTOM,
#     Image.ROTATE_90, Image.ROTATE_180, or Image.ROTATE_270.

class TransposedFont:
    "Wrapper for writing rotated or mirrored text"

    def __init__(self, font, orientation=None):
        self.font = font
        self.orientation = orientation # any 'transpose' argument, or None

    def getsize(self, text):
        w, h = self.font.getsize(text)
        if self.orientation in (Image.ROTATE_90, Image.ROTATE_270):
            return h, w
        return w, h

    def getmask(self, text, mode=""):
        im = self.font.getmask(text, mode)
        if self.orientation is not None:
            return im.transpose(self.orientation)
        return im


def load(filename):
    """
    Load a font file.  This function loads a font object from the given
    bitmap font file, and returns the corresponding font object.

    :param filename: Name of font file.
    :return: A font object.
    :exception IOError: If the file could not be read.
    """
    f = ImageFont()
    f._load_pilfont(filename)
    return f


def truetype(font=None, size=10, index=0, encoding="", filename=None):
    """
    Load a TrueType or OpenType font file, and create a font object.
    This function loads a font object from the given file, and creates
    a font object for a font of the given size.

    This function requires the _imagingft service.

    :param filename: A truetype font file. Under Windows, if the file
                     is not found in this filename, the loader also looks in
                     Windows :file:`fonts/` directory.
    :param size: The requested size, in points.
    :param index: Which font face to load (default is first available face).
    :param encoding: Which font encoding to use (default is Unicode). Common
                     encodings are "unic" (Unicode), "symb" (Microsoft
                     Symbol), "ADOB" (Adobe Standard), "ADBE" (Adobe Expert),
                     and "armn" (Apple Roman). See the FreeType documentation
                     for more information.
    :return: A font object.
    :exception IOError: If the file could not be read.
    """

    if filename:
        if warnings:
            warnings.warn('filename parameter deprecated, please use font parameter instead.', DeprecationWarning)
        font = filename

    try:
        return FreeTypeFont(font, size, index, encoding)
    except IOError:
        if sys.platform == "win32":
            # check the windows font repository
            # NOTE: must use uppercase WINDIR, to work around bugs in
            # 1.5.2's os.environ.get()
            windir = os.environ.get("WINDIR")
            if windir:
                filename = os.path.join(windir, "fonts", font)
                return FreeTypeFont(filename, size, index, encoding)
        raise


def load_path(filename):
    """
    Load font file. Same as :py:func:`~PIL.ImageFont.load`, but searches for a
    bitmap font along the Python path.

    :param filename: Name of font file.
    :return: A font object.
    :exception IOError: If the file could not be read.
    """
    for dir in sys.path:
        if isDirectory(dir):
            if not isinstance(filename, str):
                if bytes is str:
                    filename = filename.encode("utf-8")
                else:
                    filename = filename.decode("utf-8")
            try:
                return load(os.path.join(dir, filename))
            except IOError:
                pass
    raise IOError("cannot find font file")


def load_default():
    """Load a "better than nothing" default font.

    .. versionadded:: 1.1.4

    :return: A font object.
    """
    from io import BytesIO
    import base64
    f = ImageFont()
    f._load_pilfont_data(
         # courB08
         BytesIO(base64.decodestring(b'''
UElMZm9udAo7Ozs7OzsxMDsKREFUQQoAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAYAAAAA//8AAQAAAAAAAAABAAEA
BgAAAAH/+gADAAAAAQAAAAMABgAGAAAAAf/6AAT//QADAAAABgADAAYAAAAA//kABQABAAYAAAAL
AAgABgAAAAD/+AAFAAEACwAAABAACQAGAAAAAP/5AAUAAAAQAAAAFQAHAAYAAP////oABQAAABUA
AAAbAAYABgAAAAH/+QAE//wAGwAAAB4AAwAGAAAAAf/5AAQAAQAeAAAAIQAIAAYAAAAB//kABAAB
ACEAAAAkAAgABgAAAAD/+QAE//0AJAAAACgABAAGAAAAAP/6AAX//wAoAAAALQAFAAYAAAAB//8A
BAACAC0AAAAwAAMABgAAAAD//AAF//0AMAAAADUAAQAGAAAAAf//AAMAAAA1AAAANwABAAYAAAAB
//kABQABADcAAAA7AAgABgAAAAD/+QAFAAAAOwAAAEAABwAGAAAAAP/5AAYAAABAAAAARgAHAAYA
AAAA//kABQAAAEYAAABLAAcABgAAAAD/+QAFAAAASwAAAFAABwAGAAAAAP/5AAYAAABQAAAAVgAH
AAYAAAAA//kABQAAAFYAAABbAAcABgAAAAD/+QAFAAAAWwAAAGAABwAGAAAAAP/5AAUAAABgAAAA
ZQAHAAYAAAAA//kABQAAAGUAAABqAAcABgAAAAD/+QAFAAAAagAAAG8ABwAGAAAAAf/8AAMAAABv
AAAAcQAEAAYAAAAA//wAAwACAHEAAAB0AAYABgAAAAD/+gAE//8AdAAAAHgABQAGAAAAAP/7AAT/
/gB4AAAAfAADAAYAAAAB//oABf//AHwAAACAAAUABgAAAAD/+gAFAAAAgAAAAIUABgAGAAAAAP/5
AAYAAQCFAAAAiwAIAAYAAP////oABgAAAIsAAACSAAYABgAA////+gAFAAAAkgAAAJgABgAGAAAA
AP/6AAUAAACYAAAAnQAGAAYAAP////oABQAAAJ0AAACjAAYABgAA////+gAFAAAAowAAAKkABgAG
AAD////6AAUAAACpAAAArwAGAAYAAAAA//oABQAAAK8AAAC0AAYABgAA////+gAGAAAAtAAAALsA
BgAGAAAAAP/6AAQAAAC7AAAAvwAGAAYAAP////oABQAAAL8AAADFAAYABgAA////+gAGAAAAxQAA
AMwABgAGAAD////6AAUAAADMAAAA0gAGAAYAAP////oABQAAANIAAADYAAYABgAA////+gAGAAAA
2AAAAN8ABgAGAAAAAP/6AAUAAADfAAAA5AAGAAYAAP////oABQAAAOQAAADqAAYABgAAAAD/+gAF
AAEA6gAAAO8ABwAGAAD////6AAYAAADvAAAA9gAGAAYAAAAA//oABQAAAPYAAAD7AAYABgAA////
+gAFAAAA+wAAAQEABgAGAAD////6AAYAAAEBAAABCAAGAAYAAP////oABgAAAQgAAAEPAAYABgAA
////+gAGAAABDwAAARYABgAGAAAAAP/6AAYAAAEWAAABHAAGAAYAAP////oABgAAARwAAAEjAAYA
BgAAAAD/+gAFAAABIwAAASgABgAGAAAAAf/5AAQAAQEoAAABKwAIAAYAAAAA//kABAABASsAAAEv
AAgABgAAAAH/+QAEAAEBLwAAATIACAAGAAAAAP/5AAX//AEyAAABNwADAAYAAAAAAAEABgACATcA
AAE9AAEABgAAAAH/+QAE//wBPQAAAUAAAwAGAAAAAP/7AAYAAAFAAAABRgAFAAYAAP////kABQAA
AUYAAAFMAAcABgAAAAD/+wAFAAABTAAAAVEABQAGAAAAAP/5AAYAAAFRAAABVwAHAAYAAAAA//sA
BQAAAVcAAAFcAAUABgAAAAD/+QAFAAABXAAAAWEABwAGAAAAAP/7AAYAAgFhAAABZwAHAAYAAP//
//kABQAAAWcAAAFtAAcABgAAAAD/+QAGAAABbQAAAXMABwAGAAAAAP/5AAQAAgFzAAABdwAJAAYA
AP////kABgAAAXcAAAF+AAcABgAAAAD/+QAGAAABfgAAAYQABwAGAAD////7AAUAAAGEAAABigAF
AAYAAP////sABQAAAYoAAAGQAAUABgAAAAD/+wAFAAABkAAAAZUABQAGAAD////7AAUAAgGVAAAB
mwAHAAYAAAAA//sABgACAZsAAAGhAAcABgAAAAD/+wAGAAABoQAAAacABQAGAAAAAP/7AAYAAAGn
AAABrQAFAAYAAAAA//kABgAAAa0AAAGzAAcABgAA////+wAGAAABswAAAboABQAGAAD////7AAUA
AAG6AAABwAAFAAYAAP////sABgAAAcAAAAHHAAUABgAAAAD/+wAGAAABxwAAAc0ABQAGAAD////7
AAYAAgHNAAAB1AAHAAYAAAAA//sABQAAAdQAAAHZAAUABgAAAAH/+QAFAAEB2QAAAd0ACAAGAAAA
Av/6AAMAAQHdAAAB3gAHAAYAAAAA//kABAABAd4AAAHiAAgABgAAAAD/+wAF//0B4gAAAecAAgAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAYAAAAB
//sAAwACAecAAAHpAAcABgAAAAD/+QAFAAEB6QAAAe4ACAAGAAAAAP/5AAYAAAHuAAAB9AAHAAYA
AAAA//oABf//AfQAAAH5AAUABgAAAAD/+QAGAAAB+QAAAf8ABwAGAAAAAv/5AAMAAgH/AAACAAAJ
AAYAAAAA//kABQABAgAAAAIFAAgABgAAAAH/+gAE//sCBQAAAggAAQAGAAAAAP/5AAYAAAIIAAAC
DgAHAAYAAAAB//kABf/+Ag4AAAISAAUABgAA////+wAGAAACEgAAAhkABQAGAAAAAP/7AAX//gIZ
AAACHgADAAYAAAAA//wABf/9Ah4AAAIjAAEABgAAAAD/+QAHAAACIwAAAioABwAGAAAAAP/6AAT/
+wIqAAACLgABAAYAAAAA//kABP/8Ai4AAAIyAAMABgAAAAD/+gAFAAACMgAAAjcABgAGAAAAAf/5
AAT//QI3AAACOgAEAAYAAAAB//kABP/9AjoAAAI9AAQABgAAAAL/+QAE//sCPQAAAj8AAgAGAAD/
///7AAYAAgI/AAACRgAHAAYAAAAA//kABgABAkYAAAJMAAgABgAAAAH//AAD//0CTAAAAk4AAQAG
AAAAAf//AAQAAgJOAAACUQADAAYAAAAB//kABP/9AlEAAAJUAAQABgAAAAH/+QAF//4CVAAAAlgA
BQAGAAD////7AAYAAAJYAAACXwAFAAYAAP////kABgAAAl8AAAJmAAcABgAA////+QAGAAACZgAA
Am0ABwAGAAD////5AAYAAAJtAAACdAAHAAYAAAAA//sABQACAnQAAAJ5AAcABgAA////9wAGAAAC
eQAAAoAACQAGAAD////3AAYAAAKAAAAChwAJAAYAAP////cABgAAAocAAAKOAAkABgAA////9wAG
AAACjgAAApUACQAGAAD////4AAYAAAKVAAACnAAIAAYAAP////cABgAAApwAAAKjAAkABgAA////
+gAGAAACowAAAqoABgAGAAAAAP/6AAUAAgKqAAACrwAIAAYAAP////cABQAAAq8AAAK1AAkABgAA
////9wAFAAACtQAAArsACQAGAAD////3AAUAAAK7AAACwQAJAAYAAP////gABQAAAsEAAALHAAgA
BgAAAAD/9wAEAAACxwAAAssACQAGAAAAAP/3AAQAAALLAAACzwAJAAYAAAAA//cABAAAAs8AAALT
AAkABgAAAAD/+AAEAAAC0wAAAtcACAAGAAD////6AAUAAALXAAAC3QAGAAYAAP////cABgAAAt0A
AALkAAkABgAAAAD/9wAFAAAC5AAAAukACQAGAAAAAP/3AAUAAALpAAAC7gAJAAYAAAAA//cABQAA
Au4AAALzAAkABgAAAAD/9wAFAAAC8wAAAvgACQAGAAAAAP/4AAUAAAL4AAAC/QAIAAYAAAAA//oA
Bf//Av0AAAMCAAUABgAA////+gAGAAADAgAAAwkABgAGAAD////3AAYAAAMJAAADEAAJAAYAAP//
//cABgAAAxAAAAMXAAkABgAA////9wAGAAADFwAAAx4ACQAGAAD////4AAYAAAAAAAoABwASAAYA
AP////cABgAAAAcACgAOABMABgAA////+gAFAAAADgAKABQAEAAGAAD////6AAYAAAAUAAoAGwAQ
AAYAAAAA//gABgAAABsACgAhABIABgAAAAD/+AAGAAAAIQAKACcAEgAGAAAAAP/4AAYAAAAnAAoA
LQASAAYAAAAA//gABgAAAC0ACgAzABIABgAAAAD/+QAGAAAAMwAKADkAEQAGAAAAAP/3AAYAAAA5
AAoAPwATAAYAAP////sABQAAAD8ACgBFAA8ABgAAAAD/+wAFAAIARQAKAEoAEQAGAAAAAP/4AAUA
AABKAAoATwASAAYAAAAA//gABQAAAE8ACgBUABIABgAAAAD/+AAFAAAAVAAKAFkAEgAGAAAAAP/5
AAUAAABZAAoAXgARAAYAAAAA//gABgAAAF4ACgBkABIABgAAAAD/+AAGAAAAZAAKAGoAEgAGAAAA
AP/4AAYAAABqAAoAcAASAAYAAAAA//kABgAAAHAACgB2ABEABgAAAAD/+AAFAAAAdgAKAHsAEgAG
AAD////4AAYAAAB7AAoAggASAAYAAAAA//gABQAAAIIACgCHABIABgAAAAD/+AAFAAAAhwAKAIwA
EgAGAAAAAP/4AAUAAACMAAoAkQASAAYAAAAA//gABQAAAJEACgCWABIABgAAAAD/+QAFAAAAlgAK
AJsAEQAGAAAAAP/6AAX//wCbAAoAoAAPAAYAAAAA//oABQABAKAACgClABEABgAA////+AAGAAAA
pQAKAKwAEgAGAAD////4AAYAAACsAAoAswASAAYAAP////gABgAAALMACgC6ABIABgAA////+QAG
AAAAugAKAMEAEQAGAAD////4AAYAAgDBAAoAyAAUAAYAAP////kABQACAMgACgDOABMABgAA////
+QAGAAIAzgAKANUAEw==
''')), Image.open(BytesIO(base64.decodestring(b'''
iVBORw0KGgoAAAANSUhEUgAAAx4AAAAUAQAAAAArMtZoAAAEwElEQVR4nABlAJr/AHVE4czCI/4u
Mc4b7vuds/xzjz5/3/7u/n9vMe7vnfH/9++vPn/xyf5zhxzjt8GHw8+2d83u8x27199/nxuQ6Od9
M43/5z2I+9n9ZtmDBwMQECDRQw/eQIQohJXxpBCNVE6QCCAAAAD//wBlAJr/AgALyj1t/wINwq0g
LeNZUworuN1cjTPIzrTX6ofHWeo3v336qPzfEwRmBnHTtf95/fglZK5N0PDgfRTslpGBvz7LFc4F
IUXBWQGjQ5MGCx34EDFPwXiY4YbYxavpnhHFrk14CDAAAAD//wBlAJr/AgKqRooH2gAgPeggvUAA
Bu2WfgPoAwzRAABAAAAAAACQgLz/3Uv4Gv+gX7BJgDeeGP6AAAD1NMDzKHD7ANWr3loYbxsAD791
NAADfcoIDyP44K/jv4Y63/Z+t98Ovt+ub4T48LAAAAD//wBlAJr/AuplMlADJAAAAGuAphWpqhMx
in0A/fRvAYBABPgBwBUgABBQ/sYAyv9g0bCHgOLoGAAAAAAAREAAwI7nr0ArYpow7aX8//9LaP/9
SjdavWA8ePHeBIKB//81/83ndznOaXx379wAAAD//wBlAJr/AqDxW+D3AABAAbUh/QMnbQag/gAY
AYDAAACgtgD/gOqAAAB5IA/8AAAk+n9w0AAA8AAAmFRJuPo27ciC0cD5oeW4E7KA/wD3ECMAn2tt
y8PgwH8AfAxFzC0JzeAMtratAsC/ffwAAAD//wBlAJr/BGKAyCAA4AAAAvgeYTAwHd1kmQF5chkG
ABoMIHcL5xVpTfQbUqzlAAAErwAQBgAAEOClA5D9il08AEh/tUzdCBsXkbgACED+woQg8Si9VeqY
lODCn7lmF6NhnAEYgAAA/NMIAAAAAAD//2JgjLZgVGBg5Pv/Tvpc8hwGBjYGJADjHDrAwPzAjv/H
/Wf3PzCwtzcwHmBgYGcwbZz8wHaCAQMDOwMDQ8MCBgYOC3W7mp+f0w+wHOYxO3OG+e376hsMZjk3
AAAAAP//YmCMY2A4wMAIN5e5gQETPD6AZisDAwMDgzSDAAPjByiHcQMDAwMDg1nOze1lByRu5/47
c4859311AYNZzg0AAAAA//9iYGDBYihOIIMuwIjGL39/fwffA8b//xv/P2BPtzzHwCBjUQAAAAD/
/yLFBrIBAAAA//9i1HhcwdhizX7u8NZNzyLbvT97bfrMf/QHI8evOwcSqGUJAAAA//9iYBB81iSw
pEE170Qrg5MIYydHqwdDQRMrAwcVrQAAAAD//2J4x7j9AAMDn8Q/BgYLBoaiAwwMjPdvMDBYM1Tv
oJodAAAAAP//Yqo/83+dxePWlxl3npsel9lvLfPcqlE9725C+acfVLMEAAAA//9i+s9gwCoaaGMR
evta/58PTEWzr21hufPjA8N+qlnBwAAAAAD//2JiWLci5v1+HmFXDqcnULE/MxgYGBj+f6CaJQAA
AAD//2Ji2FrkY3iYpYC5qDeGgeEMAwPDvwQBBoYvcTwOVLMEAAAA//9isDBgkP///0EOg9z35v//
Gc/eeW7BwPj5+QGZhANUswMAAAD//2JgqGBgYGBgqEMXlvhMPUsAAAAA//8iYDd1AAAAAP//AwDR
w7IkEbzhVQAAAABJRU5ErkJggg==
'''))))
    return f


if __name__ == "__main__":
    # create font data chunk for embedding
    import base64, os, sys
    font = "../Images/courB08"
    print("    f._load_pilfont_data(")
    print("         # %s" % os.path.basename(font))
    print("         BytesIO(base64.decodestring(b'''")
    base64.encode(open(font + ".pil", "rb"), sys.stdout)
    print("''')), Image.open(BytesIO(base64.decodestring(b'''")
    base64.encode(open(font + ".pbm", "rb"), sys.stdout)
    print("'''))))")

########NEW FILE########
__FILENAME__ = ImageGrab
#
# The Python Imaging Library
# $Id$
#
# screen grabber (windows only)
#
# History:
# 2001-04-26 fl  created
# 2001-09-17 fl  use builtin driver, if present
# 2002-11-19 fl  added grabclipboard support
#
# Copyright (c) 2001-2002 by Secret Labs AB
# Copyright (c) 2001-2002 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

from PIL import Image


try:
    # built-in driver (1.1.3 and later)
    grabber = Image.core.grabscreen
except AttributeError:
    # stand-alone driver (pil plus)
    import _grabscreen
    grabber = _grabscreen.grab


def grab(bbox=None):
    size, data = grabber()
    im = Image.frombytes(
        "RGB", size, data,
        # RGB, 32-bit line padding, origo in lower left corner
        "raw", "BGR", (size[0]*3 + 3) & -4, -1
        )
    if bbox:
        im = im.crop(bbox)
    return im


def grabclipboard():
    debug = 0 # temporary interface
    data = Image.core.grabclipboard(debug)
    if isinstance(data, bytes):
        from PIL import BmpImagePlugin
        import io
        return BmpImagePlugin.DibImageFile(io.BytesIO(data))
    return data

########NEW FILE########
__FILENAME__ = ImageMath
#
# The Python Imaging Library
# $Id$
#
# a simple math add-on for the Python Imaging Library
#
# History:
# 1999-02-15 fl   Original PIL Plus release
# 2005-05-05 fl   Simplified and cleaned up for PIL 1.1.6
# 2005-09-12 fl   Fixed int() and float() for Python 2.4.1
#
# Copyright (c) 1999-2005 by Secret Labs AB
# Copyright (c) 2005 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

from PIL import Image
from PIL import _imagingmath
import sys

try:
    import builtins
except ImportError:
    import __builtin__
    builtins = __builtin__

VERBOSE = 0

def _isconstant(v):
    return isinstance(v, int) or isinstance(v, float)

class _Operand:
    # wraps an image operand, providing standard operators

    def __init__(self, im):
        self.im = im

    def __fixup(self, im1):
        # convert image to suitable mode
        if isinstance(im1, _Operand):
            # argument was an image.
            if im1.im.mode in ("1", "L"):
                return im1.im.convert("I")
            elif im1.im.mode in ("I", "F"):
                return im1.im
            else:
                raise ValueError("unsupported mode: %s" % im1.im.mode)
        else:
            # argument was a constant
            if _isconstant(im1) and self.im.mode in ("1", "L", "I"):
                return Image.new("I", self.im.size, im1)
            else:
                return Image.new("F", self.im.size, im1)

    def apply(self, op, im1, im2=None, mode=None):
        im1 = self.__fixup(im1)
        if im2 is None:
            # unary operation
            out = Image.new(mode or im1.mode, im1.size, None)
            im1.load()
            try:
                op = getattr(_imagingmath, op+"_"+im1.mode)
            except AttributeError:
                raise TypeError("bad operand type for '%s'" % op)
            _imagingmath.unop(op, out.im.id, im1.im.id)
        else:
            # binary operation
            im2 = self.__fixup(im2)
            if im1.mode != im2.mode:
                # convert both arguments to floating point
                if im1.mode != "F": im1 = im1.convert("F")
                if im2.mode != "F": im2 = im2.convert("F")
                if im1.mode != im2.mode:
                    raise ValueError("mode mismatch")
            if im1.size != im2.size:
                # crop both arguments to a common size
                size = (min(im1.size[0], im2.size[0]),
                        min(im1.size[1], im2.size[1]))
                if im1.size != size: im1 = im1.crop((0, 0) + size)
                if im2.size != size: im2 = im2.crop((0, 0) + size)
                out = Image.new(mode or im1.mode, size, None)
            else:
                out = Image.new(mode or im1.mode, im1.size, None)
            im1.load(); im2.load()
            try:
                op = getattr(_imagingmath, op+"_"+im1.mode)
            except AttributeError:
                raise TypeError("bad operand type for '%s'" % op)
            _imagingmath.binop(op, out.im.id, im1.im.id, im2.im.id)
        return _Operand(out)

    # unary operators
    def __bool__(self):
        # an image is "true" if it contains at least one non-zero pixel
        return self.im.getbbox() is not None

    if bytes is str:
        # Provide __nonzero__ for pre-Py3k
        __nonzero__ = __bool__
        del __bool__

    def __abs__(self):
        return self.apply("abs", self)
    def __pos__(self):
        return self
    def __neg__(self):
        return self.apply("neg", self)

    # binary operators
    def __add__(self, other):
        return self.apply("add", self, other)
    def __radd__(self, other):
        return self.apply("add", other, self)
    def __sub__(self, other):
        return self.apply("sub", self, other)
    def __rsub__(self, other):
        return self.apply("sub", other, self)
    def __mul__(self, other):
        return self.apply("mul", self, other)
    def __rmul__(self, other):
        return self.apply("mul", other, self)
    def __truediv__(self, other):
        return self.apply("div", self, other)
    def __rtruediv__(self, other):
        return self.apply("div", other, self)
    def __mod__(self, other):
        return self.apply("mod", self, other)
    def __rmod__(self, other):
        return self.apply("mod", other, self)
    def __pow__(self, other):
        return self.apply("pow", self, other)
    def __rpow__(self, other):
        return self.apply("pow", other, self)

    if bytes is str:
        # Provide __div__ and __rdiv__ for pre-Py3k
        __div__ = __truediv__
        __rdiv__ = __rtruediv__
        del __truediv__
        del __rtruediv__

    # bitwise
    def __invert__(self):
        return self.apply("invert", self)
    def __and__(self, other):
        return self.apply("and", self, other)
    def __rand__(self, other):
        return self.apply("and", other, self)
    def __or__(self, other):
        return self.apply("or", self, other)
    def __ror__(self, other):
        return self.apply("or", other, self)
    def __xor__(self, other):
        return self.apply("xor", self, other)
    def __rxor__(self, other):
        return self.apply("xor", other, self)
    def __lshift__(self, other):
        return self.apply("lshift", self, other)
    def __rshift__(self, other):
        return self.apply("rshift", self, other)

    # logical
    def __eq__(self, other):
        return self.apply("eq", self, other)
    def __ne__(self, other):
        return self.apply("ne", self, other)
    def __lt__(self, other):
        return self.apply("lt", self, other)
    def __le__(self, other):
        return self.apply("le", self, other)
    def __gt__(self, other):
        return self.apply("gt", self, other)
    def __ge__(self, other):
        return self.apply("ge", self, other)

# conversions
def imagemath_int(self):
    return _Operand(self.im.convert("I"))
def imagemath_float(self):
    return _Operand(self.im.convert("F"))

# logical
def imagemath_equal(self, other):
    return self.apply("eq", self, other, mode="I")
def imagemath_notequal(self, other):
    return self.apply("ne", self, other, mode="I")

def imagemath_min(self, other):
    return self.apply("min", self, other)
def imagemath_max(self, other):
    return self.apply("max", self, other)

def imagemath_convert(self, mode):
    return _Operand(self.im.convert(mode))

ops = {}
for k, v in list(globals().items()):
    if k[:10] == "imagemath_":
        ops[k[10:]] = v


def eval(expression, _dict={}, **kw):
    """
    Evaluates an image expression.

    :param expression: A string containing a Python-style expression.
    :param options: Values to add to the evaluation context.  You
                    can either use a dictionary, or one or more keyword
                    arguments.
    :return: The evaluated expression. This is usually an image object, but can
             also be an integer, a floating point value, or a pixel tuple,
             depending on the expression.
    """

    # build execution namespace
    args = ops.copy()
    args.update(_dict)
    args.update(kw)
    for k, v in list(args.items()):
        if hasattr(v, "im"):
            args[k] = _Operand(v)

    out = builtins.eval(expression, args)
    try:
        return out.im
    except AttributeError:
        return out

########NEW FILE########
__FILENAME__ = ImageMode
#
# The Python Imaging Library.
# $Id$
#
# standard mode descriptors
#
# History:
# 2006-03-20 fl   Added
#
# Copyright (c) 2006 by Secret Labs AB.
# Copyright (c) 2006 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#

# mode descriptor cache
_modes = {}

##
# Wrapper for mode strings.

class ModeDescriptor:

    def __init__(self, mode, bands, basemode, basetype):
        self.mode = mode
        self.bands = bands
        self.basemode = basemode
        self.basetype = basetype

    def __str__(self):
        return self.mode

##
# Gets a mode descriptor for the given mode.

def getmode(mode):
    if not _modes:
        # initialize mode cache
        from PIL import Image
        # core modes
        for m, (basemode, basetype, bands) in Image._MODEINFO.items():
            _modes[m] = ModeDescriptor(m, bands, basemode, basetype)
        # extra experimental modes
        _modes["LA"] = ModeDescriptor("LA", ("L", "A"), "L", "L")
        _modes["PA"] = ModeDescriptor("PA", ("P", "A"), "RGB", "L")
        # mapping modes
        _modes["I;16"] = ModeDescriptor("I;16", "I", "L", "L")
        _modes["I;16L"] = ModeDescriptor("I;16L", "I", "L", "L")
        _modes["I;16B"] = ModeDescriptor("I;16B", "I", "L", "L")
    return _modes[mode]

########NEW FILE########
__FILENAME__ = ImageOps
#
# The Python Imaging Library.
# $Id$
#
# standard image operations
#
# History:
# 2001-10-20 fl   Created
# 2001-10-23 fl   Added autocontrast operator
# 2001-12-18 fl   Added Kevin's fit operator
# 2004-03-14 fl   Fixed potential division by zero in equalize
# 2005-05-05 fl   Fixed equalize for low number of values
#
# Copyright (c) 2001-2004 by Secret Labs AB
# Copyright (c) 2001-2004 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

from PIL import Image
from PIL._util import isStringType
import operator
from functools import reduce

#
# helpers

def _border(border):
    if isinstance(border, tuple):
        if len(border) == 2:
            left, top = right, bottom = border
        elif len(border) == 4:
            left, top, right, bottom = border
    else:
        left = top = right = bottom = border
    return left, top, right, bottom

def _color(color, mode):
    if isStringType(color):
        from PIL import ImageColor
        color = ImageColor.getcolor(color, mode)
    return color

def _lut(image, lut):
    if image.mode == "P":
        # FIXME: apply to lookup table, not image data
        raise NotImplementedError("mode P support coming soon")
    elif image.mode in ("L", "RGB"):
        if image.mode == "RGB" and len(lut) == 256:
            lut = lut + lut + lut
        return image.point(lut)
    else:
        raise IOError("not supported for this image mode")

#
# actions


def autocontrast(image, cutoff=0, ignore=None):
    """
    Maximize (normalize) image contrast. This function calculates a
    histogram of the input image, removes **cutoff** percent of the
    lightest and darkest pixels from the histogram, and remaps the image
    so that the darkest pixel becomes black (0), and the lightest
    becomes white (255).

    :param image: The image to process.
    :param cutoff: How many percent to cut off from the histogram.
    :param ignore: The background pixel value (use None for no background).
    :return: An image.
    """
    histogram = image.histogram()
    lut = []
    for layer in range(0, len(histogram), 256):
        h = histogram[layer:layer+256]
        if ignore is not None:
            # get rid of outliers
            try:
                h[ignore] = 0
            except TypeError:
                # assume sequence
                for ix in ignore:
                    h[ix] = 0
        if cutoff:
            # cut off pixels from both ends of the histogram
            # get number of pixels
            n = 0
            for ix in range(256):
                n = n + h[ix]
            # remove cutoff% pixels from the low end
            cut = n * cutoff // 100
            for lo in range(256):
                if cut > h[lo]:
                    cut = cut - h[lo]
                    h[lo] = 0
                else:
                    h[lo] = h[lo] - cut
                    cut = 0
                if cut <= 0:
                    break
            # remove cutoff% samples from the hi end
            cut = n * cutoff // 100
            for hi in range(255, -1, -1):
                if cut > h[hi]:
                    cut = cut - h[hi]
                    h[hi] = 0
                else:
                    h[hi] = h[hi] - cut
                    cut = 0
                if cut <= 0:
                    break
        # find lowest/highest samples after preprocessing
        for lo in range(256):
            if h[lo]:
                break
        for hi in range(255, -1, -1):
            if h[hi]:
                break
        if hi <= lo:
            # don't bother
            lut.extend(list(range(256)))
        else:
            scale = 255.0 / (hi - lo)
            offset = -lo * scale
            for ix in range(256):
                ix = int(ix * scale + offset)
                if ix < 0:
                    ix = 0
                elif ix > 255:
                    ix = 255
                lut.append(ix)
    return _lut(image, lut)


def colorize(image, black, white):
    """
    Colorize grayscale image.  The **black** and **white**
    arguments should be RGB tuples; this function calculates a color
    wedge mapping all black pixels in the source image to the first
    color, and all white pixels to the second color.

    :param image: The image to colorize.
    :param black: The color to use for black input pixels.
    :param white: The color to use for white input pixels.
    :return: An image.
    """
    assert image.mode == "L"
    black = _color(black, "RGB")
    white = _color(white, "RGB")
    red = []; green = []; blue = []
    for i in range(256):
        red.append(black[0]+i*(white[0]-black[0])//255)
        green.append(black[1]+i*(white[1]-black[1])//255)
        blue.append(black[2]+i*(white[2]-black[2])//255)
    image = image.convert("RGB")
    return _lut(image, red + green + blue)


def crop(image, border=0):
    """
    Remove border from image.  The same amount of pixels are removed
    from all four sides.  This function works on all image modes.

    .. seealso:: :py:meth:`~PIL.Image.Image.crop`

    :param image: The image to crop.
    :param border: The number of pixels to remove.
    :return: An image.
    """
    left, top, right, bottom = _border(border)
    return image.crop(
        (left, top, image.size[0]-right, image.size[1]-bottom)
        )


def deform(image, deformer, resample=Image.BILINEAR):
    """
    Deform the image.

    :param image: The image to deform.
    :param deformer: A deformer object.  Any object that implements a
                    **getmesh** method can be used.
    :param resample: What resampling filter to use.
    :return: An image.
    """
    return image.transform(
        image.size, Image.MESH, deformer.getmesh(image), resample
        )


def equalize(image, mask=None):
    """
    Equalize the image histogram. This function applies a non-linear
    mapping to the input image, in order to create a uniform
    distribution of grayscale values in the output image.

    :param image: The image to equalize.
    :param mask: An optional mask.  If given, only the pixels selected by
                 the mask are included in the analysis.
    :return: An image.
    """
    if image.mode == "P":
        image = image.convert("RGB")
    h = image.histogram(mask)
    lut = []
    for b in range(0, len(h), 256):
        histo = [_f for _f in h[b:b+256] if _f]
        if len(histo) <= 1:
            lut.extend(list(range(256)))
        else:
            step = (reduce(operator.add, histo) - histo[-1]) // 255
            if not step:
                lut.extend(list(range(256)))
            else:
                n = step // 2
                for i in range(256):
                    lut.append(n // step)
                    n = n + h[i+b]
    return _lut(image, lut)


def expand(image, border=0, fill=0):
    """
    Add border to the image

    :param image: The image to expand.
    :param border: Border width, in pixels.
    :param fill: Pixel fill value (a color value).  Default is 0 (black).
    :return: An image.
    """
    "Add border to image"
    left, top, right, bottom = _border(border)
    width = left + image.size[0] + right
    height = top + image.size[1] + bottom
    out = Image.new(image.mode, (width, height), _color(fill, image.mode))
    out.paste(image, (left, top))
    return out


def fit(image, size, method=Image.NEAREST, bleed=0.0, centering=(0.5, 0.5)):
    """
    Returns a sized and cropped version of the image, cropped to the
    requested aspect ratio and size.

    This function was contributed by Kevin Cazabon.

    :param size: The requested output size in pixels, given as a
                 (width, height) tuple.
    :param method: What resampling method to use. Default is
                   :py:attr:`PIL.Image.NEAREST`.
    :param bleed: Remove a border around the outside of the image (from all
                  four edges. The value is a decimal percentage (use 0.01 for
                  one percent). The default value is 0 (no border).
    :param centering: Control the cropping position.  Use (0.5, 0.5) for
                      center cropping (e.g. if cropping the width, take 50% off
                      of the left side, and therefore 50% off the right side).
                      (0.0, 0.0) will crop from the top left corner (i.e. if
                      cropping the width, take all of the crop off of the right
                      side, and if cropping the height, take all of it off the
                      bottom).  (1.0, 0.0) will crop from the bottom left
                      corner, etc. (i.e. if cropping the width, take all of the
                      crop off the left side, and if cropping the height take
                      none from the top, and therefore all off the bottom).
    :return: An image.
    """

    # by Kevin Cazabon, Feb 17/2000
    # kevin@cazabon.com
    # http://www.cazabon.com

    # ensure inputs are valid
    if not isinstance(centering, list):
        centering = [centering[0], centering[1]]

    if centering[0] > 1.0 or centering[0] < 0.0:
        centering [0] = 0.50
    if centering[1] > 1.0 or centering[1] < 0.0:
        centering[1] = 0.50

    if bleed > 0.49999 or bleed < 0.0:
        bleed = 0.0

    # calculate the area to use for resizing and cropping, subtracting
    # the 'bleed' around the edges

    # number of pixels to trim off on Top and Bottom, Left and Right
    bleedPixels = (
        int((float(bleed) * float(image.size[0])) + 0.5),
        int((float(bleed) * float(image.size[1])) + 0.5)
        )

    liveArea = (0, 0, image.size[0], image.size[1])
    if bleed > 0.0:
        liveArea = (
            bleedPixels[0], bleedPixels[1], image.size[0] - bleedPixels[0] - 1,
            image.size[1] - bleedPixels[1] - 1
            )

    liveSize = (liveArea[2] - liveArea[0], liveArea[3] - liveArea[1])

    # calculate the aspect ratio of the liveArea
    liveAreaAspectRatio = float(liveSize[0])/float(liveSize[1])

    # calculate the aspect ratio of the output image
    aspectRatio = float(size[0]) / float(size[1])

    # figure out if the sides or top/bottom will be cropped off
    if liveAreaAspectRatio >= aspectRatio:
        # liveArea is wider than what's needed, crop the sides
        cropWidth = int((aspectRatio * float(liveSize[1])) + 0.5)
        cropHeight = liveSize[1]
    else:
        # liveArea is taller than what's needed, crop the top and bottom
        cropWidth = liveSize[0]
        cropHeight = int((float(liveSize[0])/aspectRatio) + 0.5)

    # make the crop
    leftSide = int(liveArea[0] + (float(liveSize[0]-cropWidth) * centering[0]))
    if leftSide < 0:
        leftSide = 0
    topSide = int(liveArea[1] + (float(liveSize[1]-cropHeight) * centering[1]))
    if topSide < 0:
        topSide = 0

    out = image.crop(
        (leftSide, topSide, leftSide + cropWidth, topSide + cropHeight)
        )

    # resize the image and return it
    return out.resize(size, method)


def flip(image):
    """
    Flip the image vertically (top to bottom).

    :param image: The image to flip.
    :return: An image.
    """
    return image.transpose(Image.FLIP_TOP_BOTTOM)


def grayscale(image):
    """
    Convert the image to grayscale.

    :param image: The image to convert.
    :return: An image.
    """
    return image.convert("L")


def invert(image):
    """
    Invert (negate) the image.

    :param image: The image to invert.
    :return: An image.
    """
    lut = []
    for i in range(256):
        lut.append(255-i)
    return _lut(image, lut)


def mirror(image):
    """
    Flip image horizontally (left to right).

    :param image: The image to mirror.
    :return: An image.
    """
    return image.transpose(Image.FLIP_LEFT_RIGHT)


def posterize(image, bits):
    """
    Reduce the number of bits for each color channel.

    :param image: The image to posterize.
    :param bits: The number of bits to keep for each channel (1-8).
    :return: An image.
    """
    lut = []
    mask = ~(2**(8-bits)-1)
    for i in range(256):
        lut.append(i & mask)
    return _lut(image, lut)


def solarize(image, threshold=128):
    """
    Invert all pixel values above a threshold.

    :param image: The image to posterize.
    :param threshold: All pixels above this greyscale level are inverted.
    :return: An image.
    """
    lut = []
    for i in range(256):
        if i < threshold:
            lut.append(i)
        else:
            lut.append(255-i)
    return _lut(image, lut)

# --------------------------------------------------------------------
# PIL USM components, from Kevin Cazabon.

def gaussian_blur(im, radius=None):
    """ PIL_usm.gblur(im, [radius])"""

    if radius is None:
        radius = 5.0

    im.load()

    return im.im.gaussian_blur(radius)

gblur = gaussian_blur

def unsharp_mask(im, radius=None, percent=None, threshold=None):
    """ PIL_usm.usm(im, [radius, percent, threshold])"""

    if radius is None:
        radius = 5.0
    if percent is None:
        percent = 150
    if threshold is None:
        threshold = 3

    im.load()

    return im.im.unsharp_mask(radius, percent, threshold)

usm = unsharp_mask

########NEW FILE########
__FILENAME__ = ImagePalette
#
# The Python Imaging Library.
# $Id$
#
# image palette object
#
# History:
# 1996-03-11 fl   Rewritten.
# 1997-01-03 fl   Up and running.
# 1997-08-23 fl   Added load hack
# 2001-04-16 fl   Fixed randint shadow bug in random()
#
# Copyright (c) 1997-2001 by Secret Labs AB
# Copyright (c) 1996-1997 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

import array
from PIL import Image, ImageColor


class ImagePalette:
    "Color palette for palette mapped images"

    def __init__(self, mode = "RGB", palette = None, size = 0):
        self.mode = mode
        self.rawmode = None # if set, palette contains raw data
        self.palette = palette or list(range(256))*len(self.mode)
        self.colors = {}
        self.dirty = None
        if ((size == 0 and len(self.mode)*256 != len(self.palette)) or 
                (size != 0 and size != len(self.palette))):
            raise ValueError("wrong palette size")

    def getdata(self):
        """
        Get palette contents in format suitable # for the low-level
        ``im.putpalette`` primitive.

        .. warning:: This method is experimental.
        """
        if self.rawmode:
            return self.rawmode, self.palette
        return self.mode + ";L", self.tobytes()

    def tobytes(self):
        """Convert palette to bytes.

        .. warning:: This method is experimental.
        """
        if self.rawmode:
            raise ValueError("palette contains raw palette data")
        if isinstance(self.palette, bytes):
            return self.palette
        arr = array.array("B", self.palette)
        if hasattr(arr, 'tobytes'):
            #py3k has a tobytes, tostring is deprecated.
            return arr.tobytes()
        return arr.tostring()

    # Declare tostring as an alias for tobytes
    tostring = tobytes

    def getcolor(self, color):
        """Given an rgb tuple, allocate palette entry.

        .. warning:: This method is experimental.
        """
        if self.rawmode:
            raise ValueError("palette contains raw palette data")
        if isinstance(color, tuple):
            try:
                return self.colors[color]
            except KeyError:
                # allocate new color slot
                if isinstance(self.palette, bytes):
                    self.palette = [int(x) for x in self.palette]
                index = len(self.colors)
                if index >= 256:
                    raise ValueError("cannot allocate more than 256 colors")
                self.colors[color] = index
                self.palette[index] = color[0]
                self.palette[index+256] = color[1]
                self.palette[index+512] = color[2]
                self.dirty = 1
                return index
        else:
            raise ValueError("unknown color specifier: %r" % color)

    def save(self, fp):
        """Save palette to text file.

        .. warning:: This method is experimental.
        """
        if self.rawmode:
            raise ValueError("palette contains raw palette data")
        if isinstance(fp, str):
            fp = open(fp, "w")
        fp.write("# Palette\n")
        fp.write("# Mode: %s\n" % self.mode)
        for i in range(256):
            fp.write("%d" % i)
            for j in range(i, len(self.palette), 256):
                fp.write(" %d" % self.palette[j])
            fp.write("\n")
        fp.close()

# --------------------------------------------------------------------
# Internal

def raw(rawmode, data):
    palette = ImagePalette()
    palette.rawmode = rawmode
    palette.palette = data
    palette.dirty = 1
    return palette

# --------------------------------------------------------------------
# Factories

def _make_linear_lut(black, white):
    lut = []
    if black == 0:
        for i in range(256):
            lut.append(white*i//255)
    else:
        raise NotImplementedError # FIXME
    return lut

def _make_gamma_lut(exp, mode="RGB"):
    lut = []
    for i in range(256):
        lut.append(int(((i / 255.0) ** exp) * 255.0 + 0.5))
    return lut

def new(mode, data):
    return Image.core.new_palette(mode, data)

def negative(mode="RGB"):
    palette = list(range(256))
    palette.reverse()
    return ImagePalette(mode, palette * len(mode))

def random(mode="RGB"):
    from random import randint
    palette = []
    for i in range(256*len(mode)):
        palette.append(randint(0, 255))
    return ImagePalette(mode, palette)

def sepia(white="#fff0c0"):
    r, g, b = ImageColor.getrgb(white)
    r = _make_linear_lut(0, r)
    g = _make_linear_lut(0, g)
    b = _make_linear_lut(0, b)
    return ImagePalette("RGB", r + g + b)

def wedge(mode="RGB"):
    return ImagePalette(mode, list(range(256)) * len(mode))

def load(filename):

    # FIXME: supports GIMP gradients only

    fp = open(filename, "rb")

    lut = None

    if not lut:
        try:
            from PIL import GimpPaletteFile
            fp.seek(0)
            p = GimpPaletteFile.GimpPaletteFile(fp)
            lut = p.getpalette()
        except (SyntaxError, ValueError):
            #import traceback
            #traceback.print_exc()
            pass

    if not lut:
        try:
            from PIL import GimpGradientFile
            fp.seek(0)
            p = GimpGradientFile.GimpGradientFile(fp)
            lut = p.getpalette()
        except (SyntaxError, ValueError):
            #import traceback
            #traceback.print_exc()
            pass

    if not lut:
        try:
            from PIL import PaletteFile
            fp.seek(0)
            p = PaletteFile.PaletteFile(fp)
            lut = p.getpalette()
        except (SyntaxError, ValueError):
            import traceback
            traceback.print_exc()
            pass

    if not lut:
        raise IOError("cannot load palette")

    return lut # data, rawmode

########NEW FILE########
__FILENAME__ = ImagePath
#
# The Python Imaging Library
# $Id$
#
# path interface
#
# History:
# 1996-11-04 fl   Created
# 2002-04-14 fl   Added documentation stub class
#
# Copyright (c) Secret Labs AB 1997.
# Copyright (c) Fredrik Lundh 1996.
#
# See the README file for information on usage and redistribution.
#

from PIL import Image


# the Python class below is overridden by the C implementation.


class Path:

    def __init__(self, xy):
        pass

    ##
    # Compacts the path, by removing points that are close to each
    # other.  This method modifies the path in place.

    def compact(self, distance=2):
        pass

    ##
    # Gets the bounding box.

    def getbbox(self):
        pass

    ##
    # Maps the path through a function.

    def map(self, function):
        pass

    ##
    # Converts the path to Python list.
    #
    # @param flat By default, this function returns a list of 2-tuples
    #     [(x, y), ...].  If this argument is true, it returns a flat
    #     list [x, y, ...] instead.
    # @return A list of coordinates.

    def tolist(self, flat=0):
        pass

    ##
    # Transforms the path.

    def transform(self, matrix):
        pass


# override with C implementation
Path = Image.core.path

########NEW FILE########
__FILENAME__ = ImageQt
#
# The Python Imaging Library.
# $Id$
#
# a simple Qt image interface.
#
# history:
# 2006-06-03 fl: created
# 2006-06-04 fl: inherit from QImage instead of wrapping it
# 2006-06-05 fl: removed toimage helper; move string support to ImageQt
# 2013-11-13 fl: add support for Qt5 (aurelien.ballier@cyclonit.com)
#
# Copyright (c) 2006 by Secret Labs AB
# Copyright (c) 2006 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

from PIL import Image
from PIL._util import isPath

try:
    from PyQt5.QtGui import QImage, qRgba
except:
    from PyQt4.QtGui import QImage, qRgba

##
# (Internal) Turns an RGB color into a Qt compatible color integer.

def rgb(r, g, b, a=255):
    # use qRgb to pack the colors, and then turn the resulting long
    # into a negative integer with the same bitpattern.
    return (qRgba(r, g, b, a) & 0xffffffff)

##
# An PIL image wrapper for Qt.  This is a subclass of PyQt4's QImage
# class.
#
# @param im A PIL Image object, or a file name (given either as Python
#     string or a PyQt string object).

class ImageQt(QImage):

    def __init__(self, im):

        data = None
        colortable = None

        # handle filename, if given instead of image name
        if hasattr(im, "toUtf8"):
            # FIXME - is this really the best way to do this?
            im = unicode(im.toUtf8(), "utf-8")
        if isPath(im):
            im = Image.open(im)

        if im.mode == "1":
            format = QImage.Format_Mono
        elif im.mode == "L":
            format = QImage.Format_Indexed8
            colortable = []
            for i in range(256):
                colortable.append(rgb(i, i, i))
        elif im.mode == "P":
            format = QImage.Format_Indexed8
            colortable = []
            palette = im.getpalette()
            for i in range(0, len(palette), 3):
                colortable.append(rgb(*palette[i:i+3]))
        elif im.mode == "RGB":
            data = im.tobytes("raw", "BGRX")
            format = QImage.Format_RGB32
        elif im.mode == "RGBA":
            try:
                data = im.tobytes("raw", "BGRA")
            except SystemError:
                # workaround for earlier versions
                r, g, b, a = im.split()
                im = Image.merge("RGBA", (b, g, r, a))
            format = QImage.Format_ARGB32
        else:
            raise ValueError("unsupported image mode %r" % im.mode)

        # must keep a reference, or Qt will crash!
        self.__data = data or im.tobytes()

        QImage.__init__(self, self.__data, im.size[0], im.size[1], format)

        if colortable:
            self.setColorTable(colortable)

########NEW FILE########
__FILENAME__ = ImageSequence
#
# The Python Imaging Library.
# $Id$
#
# sequence support classes
#
# history:
# 1997-02-20 fl     Created
#
# Copyright (c) 1997 by Secret Labs AB.
# Copyright (c) 1997 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#

##

class Iterator:
    """
    This class implements an iterator object that can be used to loop
    over an image sequence.

    You can use the ``[]`` operator to access elements by index. This operator
    will raise an :py:exc:`IndexError` if you try to access a nonexistent
    frame.

    :param im: An image object.
    """

    def __init__(self, im):
        if not hasattr(im, "seek"):
            raise AttributeError("im must have seek method")
        self.im = im

    def __getitem__(self, ix):
        try:
            if ix:
                self.im.seek(ix)
            return self.im
        except EOFError:
            raise IndexError # end of sequence

########NEW FILE########
__FILENAME__ = ImageShow
#
# The Python Imaging Library.
# $Id$
#
# im.show() drivers
#
# History:
# 2008-04-06 fl   Created
#
# Copyright (c) Secret Labs AB 2008.
#
# See the README file for information on usage and redistribution.
#

from __future__ import print_function

from PIL import Image
import os, sys

if(sys.version_info >= (3, 3)):
    from shlex import quote
else:
    from pipes import quote

_viewers = []

def register(viewer, order=1):
    try:
        if issubclass(viewer, Viewer):
            viewer = viewer()
    except TypeError:
        pass # raised if viewer wasn't a class
    if order > 0:
        _viewers.append(viewer)
    elif order < 0:
        _viewers.insert(0, viewer)

##
# Displays a given image.
#
# @param image An image object.
# @param title Optional title.  Not all viewers can display the title.
# @param **options Additional viewer options.
# @return True if a suitable viewer was found, false otherwise.

def show(image, title=None, **options):
    for viewer in _viewers:
        if viewer.show(image, title=title, **options):
            return 1
    return 0

##
# Base class for viewers.

class Viewer:

    # main api

    def show(self, image, **options):

        # save temporary image to disk
        if image.mode[:4] == "I;16":
            # @PIL88 @PIL101
            # "I;16" isn't an 'official' mode, but we still want to
            # provide a simple way to show 16-bit images.
            base = "L"
            # FIXME: auto-contrast if max() > 255?
        else:
            base = Image.getmodebase(image.mode)
        if base != image.mode and image.mode != "1":
            image = image.convert(base)

        return self.show_image(image, **options)

    # hook methods

    format = None

    def get_format(self, image):
        # return format name, or None to save as PGM/PPM
        return self.format

    def get_command(self, file, **options):
        raise NotImplementedError

    def save_image(self, image):
        # save to temporary file, and return filename
        return image._dump(format=self.get_format(image))

    def show_image(self, image, **options):
        # display given image
        return self.show_file(self.save_image(image), **options)

    def show_file(self, file, **options):
        # display given file
        os.system(self.get_command(file, **options))
        return 1

# --------------------------------------------------------------------

if sys.platform == "win32":

    class WindowsViewer(Viewer):
        format = "BMP"
        def get_command(self, file, **options):
            return ('start "Pillow" /WAIT "%s" '
                    '&& ping -n 2 127.0.0.1 >NUL '
                    '&& del /f "%s"' % (file, file))

    register(WindowsViewer)

elif sys.platform == "darwin":

    class MacViewer(Viewer):
        format = "BMP"
        def get_command(self, file, **options):
            # on darwin open returns immediately resulting in the temp
            # file removal while app is opening
            command = "open -a /Applications/Preview.app"
            command = "(%s %s; sleep 20; rm -f %s)&" % (command, quote(file), quote(file))
            return command

    register(MacViewer)

else:

    # unixoids

    def which(executable):
        path = os.environ.get("PATH")
        if not path:
            return None
        for dirname in path.split(os.pathsep):
            filename = os.path.join(dirname, executable)
            if os.path.isfile(filename):
                # FIXME: make sure it's executable
                return filename
        return None

    class UnixViewer(Viewer):
        def show_file(self, file, **options):
            command, executable = self.get_command_ex(file, **options)
            command = "(%s %s; rm -f %s)&" % (command, quote(file), quote(file))
            os.system(command)
            return 1

    # implementations

    class DisplayViewer(UnixViewer):
        def get_command_ex(self, file, **options):
            command = executable = "display"
            return command, executable

    if which("display"):
        register(DisplayViewer)

    class XVViewer(UnixViewer):
        def get_command_ex(self, file, title=None, **options):
            # note: xv is pretty outdated.  most modern systems have
            # imagemagick's display command instead.
            command = executable = "xv"
            if title:
                command = command + " -name %s" % quote(title)
            return command, executable

    if which("xv"):
        register(XVViewer)

if __name__ == "__main__":
    # usage: python ImageShow.py imagefile [title]
    print(show(Image.open(sys.argv[1]), *sys.argv[2:]))

########NEW FILE########
__FILENAME__ = ImageStat
#
# The Python Imaging Library.
# $Id$
#
# global image statistics
#
# History:
# 1996-04-05 fl   Created
# 1997-05-21 fl   Added mask; added rms, var, stddev attributes
# 1997-08-05 fl   Added median
# 1998-07-05 hk   Fixed integer overflow error
#
# Notes:
# This class shows how to implement delayed evaluation of attributes.
# To get a certain value, simply access the corresponding attribute.
# The __getattr__ dispatcher takes care of the rest.
#
# Copyright (c) Secret Labs AB 1997.
# Copyright (c) Fredrik Lundh 1996-97.
#
# See the README file for information on usage and redistribution.
#

from PIL import Image
import operator, math
from functools import reduce


class Stat:

    def __init__(self, image_or_list, mask = None):
        try:
            if mask:
                self.h = image_or_list.histogram(mask)
            else:
                self.h = image_or_list.histogram()
        except AttributeError:
            self.h = image_or_list # assume it to be a histogram list
        if not isinstance(self.h, list):
            raise TypeError("first argument must be image or list")
        self.bands = list(range(len(self.h) // 256))

    def __getattr__(self, id):
        "Calculate missing attribute"
        if id[:4] == "_get":
            raise AttributeError(id)
        # calculate missing attribute
        v = getattr(self, "_get" + id)()
        setattr(self, id, v)
        return v

    def _getextrema(self):
        "Get min/max values for each band in the image"

        def minmax(histogram):
            n = 255
            x = 0
            for i in range(256):
                if histogram[i]:
                    n = min(n, i)
                    x = max(x, i)
            return n, x # returns (255, 0) if there's no data in the histogram

        v = []
        for i in range(0, len(self.h), 256):
            v.append(minmax(self.h[i:]))
        return v

    def _getcount(self):
        "Get total number of pixels in each layer"

        v = []
        for i in range(0, len(self.h), 256):
            v.append(reduce(operator.add, self.h[i:i+256]))
        return v

    def _getsum(self):
        "Get sum of all pixels in each layer"

        v = []
        for i in range(0, len(self.h), 256):
            sum = 0.0
            for j in range(256):
                sum = sum + j * self.h[i+j]
            v.append(sum)
        return v

    def _getsum2(self):
        "Get squared sum of all pixels in each layer"

        v = []
        for i in range(0, len(self.h), 256):
            sum2 = 0.0
            for j in range(256):
                sum2 = sum2 + (j ** 2) * float(self.h[i+j])
            v.append(sum2)
        return v

    def _getmean(self):
        "Get average pixel level for each layer"

        v = []
        for i in self.bands:
            v.append(self.sum[i] / self.count[i])
        return v

    def _getmedian(self):
        "Get median pixel level for each layer"

        v = []
        for i in self.bands:
            s = 0
            l = self.count[i]//2
            b = i * 256
            for j in range(256):
                s = s + self.h[b+j]
                if s > l:
                    break
            v.append(j)
        return v

    def _getrms(self):
        "Get RMS for each layer"

        v = []
        for i in self.bands:
            v.append(math.sqrt(self.sum2[i] / self.count[i]))
        return v


    def _getvar(self):
        "Get variance for each layer"

        v = []
        for i in self.bands:
            n = self.count[i]
            v.append((self.sum2[i]-(self.sum[i]**2.0)/n)/n)
        return v

    def _getstddev(self):
        "Get standard deviation for each layer"

        v = []
        for i in self.bands:
            v.append(math.sqrt(self.var[i]))
        return v

Global = Stat # compatibility

########NEW FILE########
__FILENAME__ = ImageTk
#
# The Python Imaging Library.
# $Id$
#
# a Tk display interface
#
# History:
# 96-04-08 fl   Created
# 96-09-06 fl   Added getimage method
# 96-11-01 fl   Rewritten, removed image attribute and crop method
# 97-05-09 fl   Use PyImagingPaste method instead of image type
# 97-05-12 fl   Minor tweaks to match the IFUNC95 interface
# 97-05-17 fl   Support the "pilbitmap" booster patch
# 97-06-05 fl   Added file= and data= argument to image constructors
# 98-03-09 fl   Added width and height methods to Image classes
# 98-07-02 fl   Use default mode for "P" images without palette attribute
# 98-07-02 fl   Explicitly destroy Tkinter image objects
# 99-07-24 fl   Support multiple Tk interpreters (from Greg Couch)
# 99-07-26 fl   Automatically hook into Tkinter (if possible)
# 99-08-15 fl   Hook uses _imagingtk instead of _imaging
#
# Copyright (c) 1997-1999 by Secret Labs AB
# Copyright (c) 1996-1997 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

try:
    import tkinter
except ImportError:
    import Tkinter
    tkinter = Tkinter
    del Tkinter

from PIL import Image


# --------------------------------------------------------------------
# Check for Tkinter interface hooks

_pilbitmap_ok = None

def _pilbitmap_check():
    global _pilbitmap_ok
    if _pilbitmap_ok is None:
        try:
            im = Image.new("1", (1,1))
            tkinter.BitmapImage(data="PIL:%d" % im.im.id)
            _pilbitmap_ok = 1
        except tkinter.TclError:
            _pilbitmap_ok = 0
    return _pilbitmap_ok

# --------------------------------------------------------------------
# PhotoImage

class PhotoImage:
    """
    A Tkinter-compatible photo image.  This can be used
    everywhere Tkinter expects an image object.  If the image is an RGBA
    image, pixels having alpha 0 are treated as transparent.

    The constructor takes either a PIL image, or a mode and a size.
    Alternatively, you can use the **file** or **data** options to initialize
    the photo image object.

    :param image: Either a PIL image, or a mode string.  If a mode string is
                  used, a size must also be given.
    :param size: If the first argument is a mode string, this defines the size
                 of the image.
    :keyword file: A filename to load the image from (using
                   ``Image.open(file)``).
    :keyword data: An 8-bit string containing image data (as loaded from an
                   image file).
    """

    def __init__(self, image=None, size=None, **kw):

        # Tk compatibility: file or data
        if image is None:
            if "file" in kw:
                image = Image.open(kw["file"])
                del kw["file"]
            elif "data" in kw:
                from io import BytesIO
                image = Image.open(BytesIO(kw["data"]))
                del kw["data"]

        if hasattr(image, "mode") and hasattr(image, "size"):
            # got an image instead of a mode
            mode = image.mode
            if mode == "P":
                # palette mapped data
                image.load()
                try:
                    mode = image.palette.mode
                except AttributeError:
                    mode = "RGB" # default
            size = image.size
            kw["width"], kw["height"] = size
        else:
            mode = image
            image = None

        if mode not in ["1", "L", "RGB", "RGBA"]:
            mode = Image.getmodebase(mode)

        self.__mode = mode
        self.__size = size
        self.__photo = tkinter.PhotoImage(**kw)
        self.tk = self.__photo.tk
        if image:
            self.paste(image)

    def __del__(self):
        name = self.__photo.name
        self.__photo.name = None
        try:
            self.__photo.tk.call("image", "delete", name)
        except:
            pass # ignore internal errors


    def __str__(self):
        """
        Get the Tkinter photo image identifier.  This method is automatically
        called by Tkinter whenever a PhotoImage object is passed to a Tkinter
        method.

        :return: A Tkinter photo image identifier (a string).
        """
        return str(self.__photo)


    def width(self):
        """
        Get the width of the image.

        :return: The width, in pixels.
        """
        return self.__size[0]


    def height(self):
        """
        Get the height of the image.

        :return: The height, in pixels.
        """
        return self.__size[1]


    def paste(self, im, box=None):
        """
        Paste a PIL image into the photo image.  Note that this can
        be very slow if the photo image is displayed.

        :param im: A PIL image. The size must match the target region.  If the
                   mode does not match, the image is converted to the mode of
                   the bitmap image.
        :param box: A 4-tuple defining the left, upper, right, and lower pixel
                    coordinate.  If None is given instead of a tuple, all of
                    the image is assumed.
        """

        # convert to blittable
        im.load()
        image = im.im
        if image.isblock() and im.mode == self.__mode:
            block = image
        else:
            block = image.new_block(self.__mode, im.size)
            image.convert2(block, image) # convert directly between buffers

        tk = self.__photo.tk

        try:
            tk.call("PyImagingPhoto", self.__photo, block.id)
        except tkinter.TclError as v:
            # activate Tkinter hook
            try:
                from PIL import _imagingtk
                try:
                    _imagingtk.tkinit(tk.interpaddr(), 1)
                except AttributeError:
                    _imagingtk.tkinit(id(tk), 0)
                tk.call("PyImagingPhoto", self.__photo, block.id)
            except (ImportError, AttributeError, tkinter.TclError):
                raise # configuration problem; cannot attach to Tkinter

# --------------------------------------------------------------------
# BitmapImage


class BitmapImage:
    """

    A Tkinter-compatible bitmap image.  This can be used everywhere Tkinter
    expects an image object.

    The given image must have mode "1".  Pixels having value 0 are treated as
    transparent.  Options, if any, are passed on to Tkinter.  The most commonly
    used option is **foreground**, which is used to specify the color for the
    non-transparent parts.  See the Tkinter documentation for information on
    how to specify colours.

    :param image: A PIL image.
    """

    def __init__(self, image=None, **kw):

        # Tk compatibility: file or data
        if image is None:
            if "file" in kw:
                image = Image.open(kw["file"])
                del kw["file"]
            elif "data" in kw:
                from io import BytesIO
                image = Image.open(BytesIO(kw["data"]))
                del kw["data"]

        self.__mode = image.mode
        self.__size = image.size

        if _pilbitmap_check():
            # fast way (requires the pilbitmap booster patch)
            image.load()
            kw["data"] = "PIL:%d" % image.im.id
            self.__im = image # must keep a reference
        else:
            # slow but safe way
            kw["data"] = image.tobitmap()
        self.__photo = tkinter.BitmapImage(**kw)

    def __del__(self):
        name = self.__photo.name
        self.__photo.name = None
        try:
            self.__photo.tk.call("image", "delete", name)
        except:
            pass # ignore internal errors


    def width(self):
        """
        Get the width of the image.

        :return: The width, in pixels.
        """
        return self.__size[0]


    def height(self):
        """
        Get the height of the image.

        :return: The height, in pixels.
        """
        return self.__size[1]


    def __str__(self):
        """
        Get the Tkinter bitmap image identifier.  This method is automatically
        called by Tkinter whenever a BitmapImage object is passed to a Tkinter
        method.

        :return: A Tkinter bitmap image identifier (a string).
        """
        return str(self.__photo)


def getimage(photo):
    """Copies the contents of a PhotoImage to a PIL image memory."""
    photo.tk.call("PyImagingPhotoGet", photo)

# --------------------------------------------------------------------
# Helper for the Image.show method.

def _show(image, title):

    class UI(tkinter.Label):
        def __init__(self, master, im):
            if im.mode == "1":
                self.image = BitmapImage(im, foreground="white", master=master)
            else:
                self.image = PhotoImage(im, master=master)
            tkinter.Label.__init__(self, master, image=self.image,
                bg="black", bd=0)

    if not tkinter._default_root:
        raise IOError("tkinter not initialized")
    top = tkinter.Toplevel()
    if title:
        top.title(title)
    UI(top, image).pack()

########NEW FILE########
__FILENAME__ = ImageTransform
#
# The Python Imaging Library.
# $Id$
#
# transform wrappers
#
# History:
# 2002-04-08 fl   Created
#
# Copyright (c) 2002 by Secret Labs AB
# Copyright (c) 2002 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

from PIL import Image

class Transform(Image.ImageTransformHandler):
    def __init__(self, data):
        self.data = data
    def getdata(self):
        return self.method, self.data
    def transform(self, size, image, **options):
        # can be overridden
        method, data = self.getdata()
        return image.transform(size, method, data, **options)

##
# Define an affine image transform.
# <p>
# This function takes a 6-tuple (<i>a, b, c, d, e, f</i>) which
# contain the first two rows from an affine transform matrix. For
# each pixel (<i>x, y</i>) in the output image, the new value is
# taken from a position (a <i>x</i> + b <i>y</i> + c,
# d <i>x</i> + e <i>y</i> + f) in the input image, rounded to
# nearest pixel.
# <p>
# This function can be used to scale, translate, rotate, and shear the
# original image.
#
# @def AffineTransform(matrix)
# @param matrix A 6-tuple (<i>a, b, c, d, e, f</i>) containing
#    the first two rows from an affine transform matrix.
# @see Image#Image.transform

class AffineTransform(Transform):
    method = Image.AFFINE

##
# Define a transform to extract a subregion from an image.
# <p>
# Maps a rectangle (defined by two corners) from the image to a
# rectangle of the given size.  The resulting image will contain
# data sampled from between the corners, such that (<i>x0, y0</i>)
# in the input image will end up at (0,0) in the output image,
# and (<i>x1, y1</i>) at <i>size</i>.
# <p>
# This method can be used to crop, stretch, shrink, or mirror an
# arbitrary rectangle in the current image. It is slightly slower than
# <b>crop</b>, but about as fast as a corresponding <b>resize</b>
# operation.
#
# @def ExtentTransform(bbox)
# @param bbox A 4-tuple (<i>x0, y0, x1, y1</i>) which specifies
#    two points in the input image's coordinate system.
# @see Image#Image.transform

class ExtentTransform(Transform):
    method = Image.EXTENT

##
# Define an quad image transform.
# <p>
# Maps a quadrilateral (a region defined by four corners) from the
# image to a rectangle of the given size.
#
# @def QuadTransform(xy)
# @param xy An 8-tuple (<i>x0, y0, x1, y1, x2, y2, y3, y3</i>) which
#   contain the upper left, lower left, lower right, and upper right
#   corner of the source quadrilateral.
# @see Image#Image.transform

class QuadTransform(Transform):
    method = Image.QUAD

##
# Define an mesh image transform.  A mesh transform consists of one
# or more individual quad transforms.
#
# @def MeshTransform(data)
# @param data A list of (bbox, quad) tuples.
# @see Image#Image.transform

class MeshTransform(Transform):
    method = Image.MESH

########NEW FILE########
__FILENAME__ = ImageWin
#
# The Python Imaging Library.
# $Id$
#
# a Windows DIB display interface
#
# History:
# 1996-05-20 fl   Created
# 1996-09-20 fl   Fixed subregion exposure
# 1997-09-21 fl   Added draw primitive (for tzPrint)
# 2003-05-21 fl   Added experimental Window/ImageWindow classes
# 2003-09-05 fl   Added fromstring/tostring methods
#
# Copyright (c) Secret Labs AB 1997-2003.
# Copyright (c) Fredrik Lundh 1996-2003.
#
# See the README file for information on usage and redistribution.
#

import warnings
from PIL import Image


class HDC:
    """
    Wraps a HDC integer. The resulting object can be passed to the
    :py:meth:`~PIL.ImageWin.Dib.draw` and :py:meth:`~PIL.ImageWin.Dib.expose`
    methods.
    """
    def __init__(self, dc):
        self.dc = dc
    def __int__(self):
        return self.dc

class HWND:
    """
    Wraps a HWND integer. The resulting object can be passed to the
    :py:meth:`~PIL.ImageWin.Dib.draw` and :py:meth:`~PIL.ImageWin.Dib.expose`
    methods, instead of a DC.
    """
    def __init__(self, wnd):
        self.wnd = wnd
    def __int__(self):
        return self.wnd


class Dib:
    """
    A Windows bitmap with the given mode and size.  The mode can be one of "1",
    "L", "P", or "RGB".

    If the display requires a palette, this constructor creates a suitable
    palette and associates it with the image. For an "L" image, 128 greylevels
    are allocated. For an "RGB" image, a 6x6x6 colour cube is used, together
    with 20 greylevels.

    To make sure that palettes work properly under Windows, you must call the
    **palette** method upon certain events from Windows.

    :param image: Either a PIL image, or a mode string. If a mode string is
                  used, a size must also be given.  The mode can be one of "1",
                  "L", "P", or "RGB".
    :param size: If the first argument is a mode string, this
                 defines the size of the image.
    """

    def __init__(self, image, size=None):
        if hasattr(image, "mode") and hasattr(image, "size"):
            mode = image.mode
            size = image.size
        else:
            mode = image
            image = None
        if mode not in ["1", "L", "P", "RGB"]:
            mode = Image.getmodebase(mode)
        self.image = Image.core.display(mode, size)
        self.mode = mode
        self.size = size
        if image:
            self.paste(image)


    def expose(self, handle):
        """
        Copy the bitmap contents to a device context.

        :param handle: Device context (HDC), cast to a Python integer, or a HDC
                       or HWND instance.  In PythonWin, you can use the
                       :py:meth:`CDC.GetHandleAttrib` to get a suitable handle.
        """
        if isinstance(handle, HWND):
            dc = self.image.getdc(handle)
            try:
                result = self.image.expose(dc)
            finally:
                self.image.releasedc(handle, dc)
        else:
            result = self.image.expose(handle)
        return result

    def draw(self, handle, dst, src=None):
        """
        Same as expose, but allows you to specify where to draw the image, and
        what part of it to draw.

        The destination and source areas are given as 4-tuple rectangles. If
        the source is omitted, the entire image is copied. If the source and
        the destination have different sizes, the image is resized as
        necessary.
        """
        if not src:
            src = (0,0) + self.size
        if isinstance(handle, HWND):
            dc = self.image.getdc(handle)
            try:
                result = self.image.draw(dc, dst, src)
            finally:
                self.image.releasedc(handle, dc)
        else:
            result = self.image.draw(handle, dst, src)
        return result


    def query_palette(self, handle):
        """
        Installs the palette associated with the image in the given device
        context.

        This method should be called upon **QUERYNEWPALETTE** and
        **PALETTECHANGED** events from Windows. If this method returns a
        non-zero value, one or more display palette entries were changed, and
        the image should be redrawn.

        :param handle: Device context (HDC), cast to a Python integer, or an
                       HDC or HWND instance.
        :return: A true value if one or more entries were changed (this
                 indicates that the image should be redrawn).
        """
        if isinstance(handle, HWND):
            handle = self.image.getdc(handle)
            try:
                result = self.image.query_palette(handle)
            finally:
                self.image.releasedc(handle, handle)
        else:
            result = self.image.query_palette(handle)
        return result


    def paste(self, im, box=None):
        """
        Paste a PIL image into the bitmap image.

        :param im: A PIL image.  The size must match the target region.
                   If the mode does not match, the image is converted to the
                   mode of the bitmap image.
        :param box: A 4-tuple defining the left, upper, right, and
                    lower pixel coordinate.  If None is given instead of a
                    tuple, all of the image is assumed.
        """
        im.load()
        if self.mode != im.mode:
            im = im.convert(self.mode)
        if box:
            self.image.paste(im.im, box)
        else:
            self.image.paste(im.im)


    def frombytes(self, buffer):
        """
        Load display memory contents from byte data.

        :param buffer: A buffer containing display data (usually
                       data returned from <b>tobytes</b>)
        """
        return self.image.frombytes(buffer)


    def tobytes(self):
        """
        Copy display memory contents to bytes object.

        :return: A bytes object containing display data.
        """
        return self.image.tobytes()

    ##
    # Deprecated aliases to frombytes & tobytes.

    def fromstring(self, *args, **kw):
        warnings.warn(
            'fromstring() is deprecated. Please call frombytes() instead.',
            DeprecationWarning,
            stacklevel=2
        )
        return self.frombytes(*args, **kw)

    def tostring(self):
        warnings.warn(
            'tostring() is deprecated. Please call tobytes() instead.',
            DeprecationWarning,
            stacklevel=2
        )
        return self.tobytes()

##
# Create a Window with the given title size.

class Window:

    def __init__(self, title="PIL", width=None, height=None):
        self.hwnd = Image.core.createwindow(
            title, self.__dispatcher, width or 0, height or 0
            )

    def __dispatcher(self, action, *args):
        return getattr(self, "ui_handle_" + action)(*args)

    def ui_handle_clear(self, dc, x0, y0, x1, y1):
        pass

    def ui_handle_damage(self, x0, y0, x1, y1):
        pass

    def ui_handle_destroy(self):
        pass

    def ui_handle_repair(self, dc, x0, y0, x1, y1):
        pass

    def ui_handle_resize(self, width, height):
        pass

    def mainloop(self):
        Image.core.eventloop()

##
# Create an image window which displays the given image.

class ImageWindow(Window):

    def __init__(self, image, title="PIL"):
        if not isinstance(image, Dib):
            image = Dib(image)
        self.image = image
        width, height = image.size
        Window.__init__(self, title, width=width, height=height)

    def ui_handle_repair(self, dc, x0, y0, x1, y1):
        self.image.draw(dc, (x0, y0, x1, y1))

########NEW FILE########
__FILENAME__ = ImImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# IFUNC IM file handling for PIL
#
# history:
# 1995-09-01 fl   Created.
# 1997-01-03 fl   Save palette images
# 1997-01-08 fl   Added sequence support
# 1997-01-23 fl   Added P and RGB save support
# 1997-05-31 fl   Read floating point images
# 1997-06-22 fl   Save floating point images
# 1997-08-27 fl   Read and save 1-bit images
# 1998-06-25 fl   Added support for RGB+LUT images
# 1998-07-02 fl   Added support for YCC images
# 1998-07-15 fl   Renamed offset attribute to avoid name clash
# 1998-12-29 fl   Added I;16 support
# 2001-02-17 fl   Use 're' instead of 'regex' (Python 2.1) (0.7)
# 2003-09-26 fl   Added LA/PA support
#
# Copyright (c) 1997-2003 by Secret Labs AB.
# Copyright (c) 1995-2001 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#


__version__ = "0.7"

import re
from PIL import Image, ImageFile, ImagePalette
from PIL._binary import i8, o8


# --------------------------------------------------------------------
# Standard tags

COMMENT = "Comment"
DATE = "Date"
EQUIPMENT = "Digitalization equipment"
FRAMES = "File size (no of images)"
LUT = "Lut"
NAME = "Name"
SCALE = "Scale (x,y)"
SIZE = "Image size (x*y)"
MODE = "Image type"

TAGS = { COMMENT:0, DATE:0, EQUIPMENT:0, FRAMES:0, LUT:0, NAME:0,
         SCALE:0, SIZE:0, MODE:0 }

OPEN = {
    # ifunc93/p3cfunc formats
    "0 1 image": ("1", "1"),
    "L 1 image": ("1", "1"),
    "Greyscale image": ("L", "L"),
    "Grayscale image": ("L", "L"),
    "RGB image": ("RGB", "RGB;L"),
    "RLB image": ("RGB", "RLB"),
    "RYB image": ("RGB", "RLB"),
    "B1 image": ("1", "1"),
    "B2 image": ("P", "P;2"),
    "B4 image": ("P", "P;4"),
    "X 24 image": ("RGB", "RGB"),
    "L 32 S image": ("I", "I;32"),
    "L 32 F image": ("F", "F;32"),
    # old p3cfunc formats
    "RGB3 image": ("RGB", "RGB;T"),
    "RYB3 image": ("RGB", "RYB;T"),
    # extensions
    "LA image": ("LA", "LA;L"),
    "RGBA image": ("RGBA", "RGBA;L"),
    "RGBX image": ("RGBX", "RGBX;L"),
    "CMYK image": ("CMYK", "CMYK;L"),
    "YCC image": ("YCbCr", "YCbCr;L"),
}

# ifunc95 extensions
for i in ["8", "8S", "16", "16S", "32", "32F"]:
    OPEN["L %s image" % i] = ("F", "F;%s" % i)
    OPEN["L*%s image" % i] = ("F", "F;%s" % i)
for i in ["16", "16L", "16B"]:
    OPEN["L %s image" % i] = ("I;%s" % i, "I;%s" % i)
    OPEN["L*%s image" % i] = ("I;%s" % i, "I;%s" % i)
for i in ["32S"]:
    OPEN["L %s image" % i] = ("I", "I;%s" % i)
    OPEN["L*%s image" % i] = ("I", "I;%s" % i)
for i in range(2, 33):
    OPEN["L*%s image" % i] = ("F", "F;%s" % i)


# --------------------------------------------------------------------
# Read IM directory

split = re.compile(br"^([A-Za-z][^:]*):[ \t]*(.*)[ \t]*$")

def number(s):
    try:
        return int(s)
    except ValueError:
        return float(s)

##
# Image plugin for the IFUNC IM file format.

class ImImageFile(ImageFile.ImageFile):

    format = "IM"
    format_description = "IFUNC Image Memory"

    def _open(self):

        # Quick rejection: if there's not an LF among the first
        # 100 bytes, this is (probably) not a text header.

        if not b"\n" in self.fp.read(100):
            raise SyntaxError("not an IM file")
        self.fp.seek(0)

        n = 0

        # Default values
        self.info[MODE] = "L"
        self.info[SIZE] = (512, 512)
        self.info[FRAMES] = 1

        self.rawmode = "L"

        while True:

            s = self.fp.read(1)

            # Some versions of IFUNC uses \n\r instead of \r\n...
            if s == b"\r":
                continue

            if not s or s == b'\0' or s == b'\x1A':
                break

            # FIXME: this may read whole file if not a text file
            s = s + self.fp.readline()

            if len(s) > 100:
                raise SyntaxError("not an IM file")

            if s[-2:] == b'\r\n':
                s = s[:-2]
            elif s[-1:] == b'\n':
                s = s[:-1]

            try:
                m = split.match(s)
            except re.error as v:
                raise SyntaxError("not an IM file")

            if m:

                k, v = m.group(1,2)

                # Don't know if this is the correct encoding, but a decent guess
                # (I guess)
                k = k.decode('latin-1', 'replace')
                v = v.decode('latin-1', 'replace')

                # Convert value as appropriate
                if k in [FRAMES, SCALE, SIZE]:
                    v = v.replace("*", ",")
                    v = tuple(map(number, v.split(",")))
                    if len(v) == 1:
                        v = v[0]
                elif k == MODE and v in OPEN:
                    v, self.rawmode = OPEN[v]

                # Add to dictionary. Note that COMMENT tags are
                # combined into a list of strings.
                if k == COMMENT:
                    if k in self.info:
                        self.info[k].append(v)
                    else:
                        self.info[k] = [v]
                else:
                    self.info[k] = v

                if k in TAGS:
                    n = n + 1

            else:

                raise SyntaxError("Syntax error in IM header: " + s.decode('ascii', 'replace'))

        if not n:
            raise SyntaxError("Not an IM file")

        # Basic attributes
        self.size = self.info[SIZE]
        self.mode = self.info[MODE]

        # Skip forward to start of image data
        while s and s[0:1] != b'\x1A':
            s = self.fp.read(1)
        if not s:
            raise SyntaxError("File truncated")

        if LUT in self.info:
            # convert lookup table to palette or lut attribute
            palette = self.fp.read(768)
            greyscale = 1 # greyscale palette
            linear = 1 # linear greyscale palette
            for i in range(256):
                if palette[i] == palette[i+256] == palette[i+512]:
                    if i8(palette[i]) != i:
                        linear = 0
                else:
                    greyscale = 0
            if self.mode == "L" or self.mode == "LA":
                if greyscale:
                    if not linear:
                        self.lut = [i8(c) for c in palette[:256]]
                else:
                    if self.mode == "L":
                        self.mode = self.rawmode = "P"
                    elif self.mode == "LA":
                        self.mode = self.rawmode = "PA"
                    self.palette = ImagePalette.raw("RGB;L", palette)
            elif self.mode == "RGB":
                if not greyscale or not linear:
                    self.lut = [i8(c) for c in palette]

        self.frame = 0

        self.__offset = offs = self.fp.tell()

        self.__fp = self.fp # FIXME: hack

        if self.rawmode[:2] == "F;":

            # ifunc95 formats
            try:
                # use bit decoder (if necessary)
                bits = int(self.rawmode[2:])
                if bits not in [8, 16, 32]:
                    self.tile = [("bit", (0,0)+self.size, offs,
                                 (bits, 8, 3, 0, -1))]
                    return
            except ValueError:
                pass

        if self.rawmode in ["RGB;T", "RYB;T"]:
            # Old LabEye/3PC files.  Would be very surprised if anyone
            # ever stumbled upon such a file ;-)
            size = self.size[0] * self.size[1]
            self.tile = [("raw", (0,0)+self.size, offs, ("G", 0, -1)),
                         ("raw", (0,0)+self.size, offs+size, ("R", 0, -1)),
                         ("raw", (0,0)+self.size, offs+2*size, ("B", 0, -1))]
        else:
            # LabEye/IFUNC files
            self.tile = [("raw", (0,0)+self.size, offs, (self.rawmode, 0, -1))]

    def seek(self, frame):

        if frame < 0 or frame >= self.info[FRAMES]:
            raise EOFError("seek outside sequence")

        if self.frame == frame:
            return

        self.frame = frame

        if self.mode == "1":
            bits = 1
        else:
            bits = 8 * len(self.mode)

        size = ((self.size[0] * bits + 7) // 8) * self.size[1]
        offs = self.__offset + frame * size

        self.fp = self.__fp

        self.tile = [("raw", (0,0)+self.size, offs, (self.rawmode, 0, -1))]

    def tell(self):

        return self.frame

#
# --------------------------------------------------------------------
# Save IM files

SAVE = {
    # mode: (im type, raw mode)
    "1": ("0 1", "1"),
    "L": ("Greyscale", "L"),
    "LA": ("LA", "LA;L"),
    "P": ("Greyscale", "P"),
    "PA": ("LA", "PA;L"),
    "I": ("L 32S", "I;32S"),
    "I;16": ("L 16", "I;16"),
    "I;16L": ("L 16L", "I;16L"),
    "I;16B": ("L 16B", "I;16B"),
    "F": ("L 32F", "F;32F"),
    "RGB": ("RGB", "RGB;L"),
    "RGBA": ("RGBA", "RGBA;L"),
    "RGBX": ("RGBX", "RGBX;L"),
    "CMYK": ("CMYK", "CMYK;L"),
    "YCbCr": ("YCC", "YCbCr;L")
}

def _save(im, fp, filename, check=0):

    try:
        type, rawmode = SAVE[im.mode]
    except KeyError:
        raise ValueError("Cannot save %s images as IM" % im.mode)

    try:
        frames = im.encoderinfo["frames"]
    except KeyError:
        frames = 1

    if check:
        return check

    fp.write(("Image type: %s image\r\n" % type).encode('ascii'))
    if filename:
        fp.write(("Name: %s\r\n" % filename).encode('ascii'))
    fp.write(("Image size (x*y): %d*%d\r\n" % im.size).encode('ascii'))
    fp.write(("File size (no of images): %d\r\n" % frames).encode('ascii'))
    if im.mode == "P":
        fp.write(b"Lut: 1\r\n")
    fp.write(b"\000" * (511-fp.tell()) + b"\032")
    if im.mode == "P":
        fp.write(im.im.getpalette("RGB", "RGB;L")) # 768 bytes
    ImageFile._save(im, fp, [("raw", (0,0)+im.size, 0, (rawmode, 0, -1))])

#
# --------------------------------------------------------------------
# Registry

Image.register_open("IM", ImImageFile)
Image.register_save("IM", _save)

Image.register_extension("IM", ".im")

########NEW FILE########
__FILENAME__ = ImtImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# IM Tools support for PIL
#
# history:
# 1996-05-27 fl   Created (read 8-bit images only)
# 2001-02-17 fl   Use 're' instead of 'regex' (Python 2.1) (0.2)
#
# Copyright (c) Secret Labs AB 1997-2001.
# Copyright (c) Fredrik Lundh 1996-2001.
#
# See the README file for information on usage and redistribution.
#


__version__ = "0.2"

import re

from PIL import Image, ImageFile

#
# --------------------------------------------------------------------

field = re.compile(br"([a-z]*) ([^ \r\n]*)")

##
# Image plugin for IM Tools images.

class ImtImageFile(ImageFile.ImageFile):

    format = "IMT"
    format_description = "IM Tools"

    def _open(self):

        # Quick rejection: if there's not a LF among the first
        # 100 bytes, this is (probably) not a text header.

        if not b"\n" in self.fp.read(100):
            raise SyntaxError("not an IM file")
        self.fp.seek(0)

        xsize = ysize = 0

        while True:

            s = self.fp.read(1)
            if not s:
                break

            if s == b'\x0C':

                # image data begins
                self.tile = [("raw", (0,0)+self.size,
                             self.fp.tell(),
                             (self.mode, 0, 1))]

                break

            else:

                # read key/value pair
                # FIXME: dangerous, may read whole file
                s = s + self.fp.readline()
                if len(s) == 1 or len(s) > 100:
                    break
                if s[0] == b"*":
                    continue # comment

                m = field.match(s)
                if not m:
                    break
                k, v = m.group(1,2)
                if k == "width":
                    xsize = int(v)
                    self.size = xsize, ysize
                elif k == "height":
                    ysize = int(v)
                    self.size = xsize, ysize
                elif k == "pixel" and v == "n8":
                    self.mode = "L"


#
# --------------------------------------------------------------------

Image.register_open("IMT", ImtImageFile)

#
# no extension registered (".im" is simply too common)

########NEW FILE########
__FILENAME__ = IptcImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# IPTC/NAA file handling
#
# history:
# 1995-10-01 fl   Created
# 1998-03-09 fl   Cleaned up and added to PIL
# 2002-06-18 fl   Added getiptcinfo helper
#
# Copyright (c) Secret Labs AB 1997-2002.
# Copyright (c) Fredrik Lundh 1995.
#
# See the README file for information on usage and redistribution.
#

from __future__ import print_function

__version__ = "0.3"


from PIL import Image, ImageFile, _binary
import os, tempfile

i8 = _binary.i8
i16 = _binary.i16be
i32 = _binary.i32be
o8 = _binary.o8

COMPRESSION = {
    1: "raw",
    5: "jpeg"
}

PAD = o8(0) * 4

#
# Helpers

def i(c):
    return i32((PAD + c)[-4:])

def dump(c):
    for i in c:
        print("%02x" % i8(i), end=' ')
    print()

##
# Image plugin for IPTC/NAA datastreams.  To read IPTC/NAA fields
# from TIFF and JPEG files, use the <b>getiptcinfo</b> function.

class IptcImageFile(ImageFile.ImageFile):

    format = "IPTC"
    format_description = "IPTC/NAA"

    def getint(self, key):
        return i(self.info[key])

    def field(self):
        #
        # get a IPTC field header
        s = self.fp.read(5)
        if not len(s):
            return None, 0

        tag = i8(s[1]), i8(s[2])

        # syntax
        if i8(s[0]) != 0x1C or tag[0] < 1 or tag[0] > 9:
            raise SyntaxError("invalid IPTC/NAA file")

        # field size
        size = i8(s[3])
        if size > 132:
            raise IOError("illegal field length in IPTC/NAA file")
        elif size == 128:
            size = 0
        elif size > 128:
            size = i(self.fp.read(size-128))
        else:
            size = i16(s[3:])

        return tag, size

    def _is_raw(self, offset, size):
        #
        # check if the file can be mapped

        # DISABLED: the following only slows things down...
        return 0

        self.fp.seek(offset)
        t, sz = self.field()
        if sz != size[0]:
            return 0
        y = 1
        while True:
            self.fp.seek(sz, 1)
            t, s = self.field()
            if t != (8, 10):
                break
            if s != sz:
                return 0
            y = y + 1
        return y == size[1]

    def _open(self):

        # load descriptive fields
        while True:
            offset = self.fp.tell()
            tag, size = self.field()
            if not tag or tag == (8,10):
                break
            if size:
                tagdata = self.fp.read(size)
            else:
                tagdata = None
            if tag in list(self.info.keys()):
                if isinstance(self.info[tag], list):
                    self.info[tag].append(tagdata)
                else:
                    self.info[tag] = [self.info[tag], tagdata]
            else:
                self.info[tag] = tagdata

            # print tag, self.info[tag]

        # mode
        layers = i8(self.info[(3,60)][0])
        component = i8(self.info[(3,60)][1])
        if (3,65) in self.info:
            id = i8(self.info[(3,65)][0])-1
        else:
            id = 0
        if layers == 1 and not component:
            self.mode = "L"
        elif layers == 3 and component:
            self.mode = "RGB"[id]
        elif layers == 4 and component:
            self.mode = "CMYK"[id]

        # size
        self.size = self.getint((3,20)), self.getint((3,30))

        # compression
        try:
            compression = COMPRESSION[self.getint((3,120))]
        except KeyError:
            raise IOError("Unknown IPTC image compression")

        # tile
        if tag == (8,10):
            if compression == "raw" and self._is_raw(offset, self.size):
                self.tile = [(compression, (offset, size + 5, -1),
                             (0, 0, self.size[0], self.size[1]))]
            else:
                self.tile = [("iptc", (compression, offset),
                             (0, 0, self.size[0], self.size[1]))]

    def load(self):

        if len(self.tile) != 1 or self.tile[0][0] != "iptc":
            return ImageFile.ImageFile.load(self)

        type, tile, box = self.tile[0]

        encoding, offset = tile

        self.fp.seek(offset)

        # Copy image data to temporary file
        o_fd, outfile = tempfile.mkstemp(text=False)
        o = os.fdopen(o_fd)
        if encoding == "raw":
            # To simplify access to the extracted file,
            # prepend a PPM header
            o.write("P5\n%d %d\n255\n" % self.size)
        while True:
            type, size = self.field()
            if type != (8, 10):
                break
            while size > 0:
                s = self.fp.read(min(size, 8192))
                if not s:
                    break
                o.write(s)
                size = size - len(s)
        o.close()

        try:
            try:
                # fast
                self.im = Image.core.open_ppm(outfile)
            except:
                # slightly slower
                im = Image.open(outfile)
                im.load()
                self.im = im.im
        finally:
            try: os.unlink(outfile)
            except: pass


Image.register_open("IPTC", IptcImageFile)

Image.register_extension("IPTC", ".iim")

##
# Get IPTC information from TIFF, JPEG, or IPTC file.
#
# @param im An image containing IPTC data.
# @return A dictionary containing IPTC information, or None if
#     no IPTC information block was found.

def getiptcinfo(im):

    from PIL import TiffImagePlugin, JpegImagePlugin
    import io

    data = None

    if isinstance(im, IptcImageFile):
        # return info dictionary right away
        return im.info

    elif isinstance(im, JpegImagePlugin.JpegImageFile):
        # extract the IPTC/NAA resource
        try:
            app = im.app["APP13"]
            if app[:14] == "Photoshop 3.0\x00":
                app = app[14:]
                # parse the image resource block
                offset = 0
                while app[offset:offset+4] == "8BIM":
                    offset = offset + 4
                    # resource code
                    code = JpegImagePlugin.i16(app, offset)
                    offset = offset + 2
                    # resource name (usually empty)
                    name_len = i8(app[offset])
                    name = app[offset+1:offset+1+name_len]
                    offset = 1 + offset + name_len
                    if offset & 1:
                        offset = offset + 1
                    # resource data block
                    size = JpegImagePlugin.i32(app, offset)
                    offset = offset + 4
                    if code == 0x0404:
                        # 0x0404 contains IPTC/NAA data
                        data = app[offset:offset+size]
                        break
                    offset = offset + size
                    if offset & 1:
                        offset = offset + 1
        except (AttributeError, KeyError):
            pass

    elif isinstance(im, TiffImagePlugin.TiffImageFile):
        # get raw data from the IPTC/NAA tag (PhotoShop tags the data
        # as 4-byte integers, so we cannot use the get method...)
        try:
            data = im.tag.tagdata[TiffImagePlugin.IPTC_NAA_CHUNK]
        except (AttributeError, KeyError):
            pass

    if data is None:
        return None # no properties

    # create an IptcImagePlugin object without initializing it
    class FakeImage:
        pass
    im = FakeImage()
    im.__class__ = IptcImageFile

    # parse the IPTC information chunk
    im.info = {}
    im.fp = io.BytesIO(data)

    try:
        im._open()
    except (IndexError, KeyError):
        pass # expected failure

    return im.info

########NEW FILE########
__FILENAME__ = Jpeg2KImagePlugin
#
# The Python Imaging Library
# $Id$
#
# JPEG2000 file handling
#
# History:
# 2014-03-12 ajh  Created
#
# Copyright (c) 2014 Coriolis Systems Limited
# Copyright (c) 2014 Alastair Houghton
#
# See the README file for information on usage and redistribution.
#

__version__ = "0.1"

from PIL import Image, ImageFile, _binary
import struct
import os
import io

def _parse_codestream(fp):
    """Parse the JPEG 2000 codestream to extract the size and component
    count from the SIZ marker segment, returning a PIL (size, mode) tuple."""
    
    hdr = fp.read(2)
    lsiz = struct.unpack('>H', hdr)[0]
    siz = hdr + fp.read(lsiz - 2)
    lsiz, rsiz, xsiz, ysiz, xosiz, yosiz, xtsiz, ytsiz, \
    xtosiz, ytosiz, csiz \
        = struct.unpack('>HHIIIIIIIIH', siz[:38])
    ssiz = [None]*csiz
    xrsiz = [None]*csiz
    yrsiz = [None]*csiz
    for i in range(csiz):
        ssiz[i], xrsiz[i], yrsiz[i] \
            = struct.unpack('>BBB', siz[36 + 3 * i:39 + 3 * i])

    size = (xsiz - xosiz, ysiz - yosiz)
    if csiz == 1:
        mode = 'L'
    elif csiz == 2:
        mode = 'LA'
    elif csiz == 3:
        mode = 'RGB'
    elif csiz == 4:
        mode == 'RGBA'
    else:
        mode = None
    
    return (size, mode)

def _parse_jp2_header(fp):
    """Parse the JP2 header box to extract size, component count and
    color space information, returning a PIL (size, mode) tuple."""
    
    # Find the JP2 header box
    header = None
    while True:
        lbox, tbox = struct.unpack('>I4s', fp.read(8))
        if lbox == 1:
            lbox = struct.unpack('>Q', fp.read(8))[0]
            hlen = 16
        else:
            hlen = 8

        if tbox == b'jp2h':
            header = fp.read(lbox - hlen)
            break
        else:
            fp.seek(lbox - hlen, os.SEEK_CUR)

    if header is None:
        raise SyntaxError('could not find JP2 header')

    size = None
    mode = None
    
    hio = io.BytesIO(header)
    while True:
        lbox, tbox = struct.unpack('>I4s', hio.read(8))
        if lbox == 1:
            lbox = struct.unpack('>Q', hio.read(8))[0]
            hlen = 16
        else:
            hlen = 8

        content = hio.read(lbox - hlen)

        if tbox == b'ihdr':
            height, width, nc, bpc, c, unkc, ipr \
              = struct.unpack('>IIHBBBB', content)
            size = (width, height)
            if unkc:
                if nc == 1:
                    mode = 'L'
                elif nc == 2:
                    mode = 'LA'
                elif nc == 3:
                    mode = 'RGB'
                elif nc == 4:
                    mode = 'RGBA'
                break
        elif tbox == b'colr':
            meth, prec, approx = struct.unpack('>BBB', content[:3])
            if meth == 1:
                cs = struct.unpack('>I', content[3:7])[0]
                if cs == 16:   # sRGB
                    if nc == 3:
                        mode = 'RGB'
                    elif nc == 4:
                        mode = 'RGBA'
                    break
                elif cs == 17: # grayscale
                    if nc == 1:
                        mode = 'L'
                    elif nc == 2:
                        mode = 'LA'
                    break
                elif cs == 18: # sYCC
                    if nc == 3:
                        mode = 'RGB'
                    elif nc == 4:
                        mode == 'RGBA'
                    break

    return (size, mode)

##
# Image plugin for JPEG2000 images.

class Jpeg2KImageFile(ImageFile.ImageFile):
    format = "JPEG2000"
    format_description = "JPEG 2000 (ISO 15444)"

    def _open(self):
        sig = self.fp.read(4)
        if sig == b'\xff\x4f\xff\x51':
            self.codec = "j2k"
            self.size, self.mode = _parse_codestream(self.fp)
        else:
            sig = sig + self.fp.read(8)
        
            if sig == b'\x00\x00\x00\x0cjP  \x0d\x0a\x87\x0a':
                self.codec = "jp2"
                self.size, self.mode = _parse_jp2_header(self.fp)
            else:
                raise SyntaxError('not a JPEG 2000 file')
        
        if self.size is None or self.mode is None:
            raise SyntaxError('unable to determine size/mode')
        
        self.reduce = 0
        self.layers = 0

        fd = -1

        if hasattr(self.fp, "fileno"):
            try:
                fd = self.fp.fileno()
            except:
                fd = -1

        self.tile = [('jpeg2k', (0, 0) + self.size, 0,
                      (self.codec, self.reduce, self.layers, fd))]

    def load(self):
        if self.reduce:
            power = 1 << self.reduce
            adjust = power >> 1
            self.size = (int((self.size[0] + adjust) / power),
                         int((self.size[1] + adjust) / power))

        if self.tile:
            # Update the reduce and layers settings
            t = self.tile[0]
            t3 = (t[3][0], self.reduce, self.layers, t[3][3])
            self.tile = [(t[0], (0, 0) + self.size, t[2], t3)]
        
        ImageFile.ImageFile.load(self)
        
def _accept(prefix):
    return (prefix[:4] == b'\xff\x4f\xff\x51'
            or prefix[:12] == b'\x00\x00\x00\x0cjP  \x0d\x0a\x87\x0a')

# ------------------------------------------------------------
# Save support

def _save(im, fp, filename):
    if filename.endswith('.j2k'):
        kind = 'j2k'
    else:
        kind = 'jp2'

    # Get the keyword arguments
    info = im.encoderinfo

    offset = info.get('offset', None)
    tile_offset = info.get('tile_offset', None)
    tile_size = info.get('tile_size', None)
    quality_mode = info.get('quality_mode', 'rates')
    quality_layers = info.get('quality_layers', None)
    num_resolutions = info.get('num_resolutions', 0)
    cblk_size = info.get('codeblock_size', None)
    precinct_size = info.get('precinct_size', None)
    irreversible = info.get('irreversible', False)
    progression = info.get('progression', 'LRCP')
    cinema_mode = info.get('cinema_mode', 'no')
    fd = -1

    if hasattr(fp, "fileno"):
        try:
            fd = fp.fileno()
        except:
            fd = -1
    
    im.encoderconfig = (
        offset,
        tile_offset,
        tile_size,
        quality_mode,
        quality_layers,
        num_resolutions,
        cblk_size,
        precinct_size,
        irreversible,
        progression,
        cinema_mode,
        fd
        )
        
    ImageFile._save(im, fp, [('jpeg2k', (0, 0)+im.size, 0, kind)])
    
# ------------------------------------------------------------
# Registry stuff

Image.register_open('JPEG2000', Jpeg2KImageFile, _accept)
Image.register_save('JPEG2000', _save)

Image.register_extension('JPEG2000', '.jp2')
Image.register_extension('JPEG2000', '.j2k')
Image.register_extension('JPEG2000', '.jpc')
Image.register_extension('JPEG2000', '.jpf')
Image.register_extension('JPEG2000', '.jpx')
Image.register_extension('JPEG2000', '.j2c')

Image.register_mime('JPEG2000', 'image/jp2')
Image.register_mime('JPEG2000', 'image/jpx')

########NEW FILE########
__FILENAME__ = JpegImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# JPEG (JFIF) file handling
#
# See "Digital Compression and Coding of Continous-Tone Still Images,
# Part 1, Requirements and Guidelines" (CCITT T.81 / ISO 10918-1)
#
# History:
# 1995-09-09 fl   Created
# 1995-09-13 fl   Added full parser
# 1996-03-25 fl   Added hack to use the IJG command line utilities
# 1996-05-05 fl   Workaround Photoshop 2.5 CMYK polarity bug
# 1996-05-28 fl   Added draft support, JFIF version (0.1)
# 1996-12-30 fl   Added encoder options, added progression property (0.2)
# 1997-08-27 fl   Save mode 1 images as BW (0.3)
# 1998-07-12 fl   Added YCbCr to draft and save methods (0.4)
# 1998-10-19 fl   Don't hang on files using 16-bit DQT's (0.4.1)
# 2001-04-16 fl   Extract DPI settings from JFIF files (0.4.2)
# 2002-07-01 fl   Skip pad bytes before markers; identify Exif files (0.4.3)
# 2003-04-25 fl   Added experimental EXIF decoder (0.5)
# 2003-06-06 fl   Added experimental EXIF GPSinfo decoder
# 2003-09-13 fl   Extract COM markers
# 2009-09-06 fl   Added icc_profile support (from Florian Hoech)
# 2009-03-06 fl   Changed CMYK handling; always use Adobe polarity (0.6)
# 2009-03-08 fl   Added subsampling support (from Justin Huff).
#
# Copyright (c) 1997-2003 by Secret Labs AB.
# Copyright (c) 1995-1996 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#

__version__ = "0.6"

import array
import struct
from PIL import Image, ImageFile, _binary
from PIL.JpegPresets import presets
from PIL._util import isStringType

i8 = _binary.i8
o8 = _binary.o8
i16 = _binary.i16be
i32 = _binary.i32be


#
# Parser

def Skip(self, marker):
    n = i16(self.fp.read(2))-2
    ImageFile._safe_read(self.fp, n)


def APP(self, marker):
    #
    # Application marker.  Store these in the APP dictionary.
    # Also look for well-known application markers.

    n = i16(self.fp.read(2))-2
    s = ImageFile._safe_read(self.fp, n)

    app = "APP%d" % (marker & 15)

    self.app[app] = s  # compatibility
    self.applist.append((app, s))

    if marker == 0xFFE0 and s[:4] == b"JFIF":
        # extract JFIF information
        self.info["jfif"] = version = i16(s, 5)  # version
        self.info["jfif_version"] = divmod(version, 256)
        # extract JFIF properties
        try:
            jfif_unit = i8(s[7])
            jfif_density = i16(s, 8), i16(s, 10)
        except:
            pass
        else:
            if jfif_unit == 1:
                self.info["dpi"] = jfif_density
            self.info["jfif_unit"] = jfif_unit
            self.info["jfif_density"] = jfif_density
    elif marker == 0xFFE1 and s[:5] == b"Exif\0":
        # extract Exif information (incomplete)
        self.info["exif"] = s  # FIXME: value will change
    elif marker == 0xFFE2 and s[:5] == b"FPXR\0":
        # extract FlashPix information (incomplete)
        self.info["flashpix"] = s  # FIXME: value will change
    elif marker == 0xFFE2 and s[:12] == b"ICC_PROFILE\0":
        # Since an ICC profile can be larger than the maximum size of
        # a JPEG marker (64K), we need provisions to split it into
        # multiple markers. The format defined by the ICC specifies
        # one or more APP2 markers containing the following data:
        #   Identifying string      ASCII "ICC_PROFILE\0"  (12 bytes)
        #   Marker sequence number  1, 2, etc (1 byte)
        #   Number of markers       Total of APP2's used (1 byte)
        #   Profile data            (remainder of APP2 data)
        # Decoders should use the marker sequence numbers to
        # reassemble the profile, rather than assuming that the APP2
        # markers appear in the correct sequence.
        self.icclist.append(s)
    elif marker == 0xFFEE and s[:5] == b"Adobe":
        self.info["adobe"] = i16(s, 5)
        # extract Adobe custom properties
        try:
            adobe_transform = i8(s[1])
        except:
            pass
        else:
            self.info["adobe_transform"] = adobe_transform


def COM(self, marker):
    #
    # Comment marker.  Store these in the APP dictionary.
    n = i16(self.fp.read(2))-2
    s = ImageFile._safe_read(self.fp, n)

    self.app["COM"] = s  # compatibility
    self.applist.append(("COM", s))


def SOF(self, marker):
    #
    # Start of frame marker.  Defines the size and mode of the
    # image.  JPEG is colour blind, so we use some simple
    # heuristics to map the number of layers to an appropriate
    # mode.  Note that this could be made a bit brighter, by
    # looking for JFIF and Adobe APP markers.

    n = i16(self.fp.read(2))-2
    s = ImageFile._safe_read(self.fp, n)
    self.size = i16(s[3:]), i16(s[1:])

    self.bits = i8(s[0])
    if self.bits != 8:
        raise SyntaxError("cannot handle %d-bit layers" % self.bits)

    self.layers = i8(s[5])
    if self.layers == 1:
        self.mode = "L"
    elif self.layers == 3:
        self.mode = "RGB"
    elif self.layers == 4:
        self.mode = "CMYK"
    else:
        raise SyntaxError("cannot handle %d-layer images" % self.layers)

    if marker in [0xFFC2, 0xFFC6, 0xFFCA, 0xFFCE]:
        self.info["progressive"] = self.info["progression"] = 1

    if self.icclist:
        # fixup icc profile
        self.icclist.sort()  # sort by sequence number
        if i8(self.icclist[0][13]) == len(self.icclist):
            profile = []
            for p in self.icclist:
                profile.append(p[14:])
            icc_profile = b"".join(profile)
        else:
            icc_profile = None  # wrong number of fragments
        self.info["icc_profile"] = icc_profile
        self.icclist = None

    for i in range(6, len(s), 3):
        t = s[i:i+3]
        # 4-tuples: id, vsamp, hsamp, qtable
        self.layer.append((t[0], i8(t[1])//16, i8(t[1]) & 15, i8(t[2])))


def DQT(self, marker):
    #
    # Define quantization table.  Support baseline 8-bit tables
    # only.  Note that there might be more than one table in
    # each marker.

    # FIXME: The quantization tables can be used to estimate the
    # compression quality.

    n = i16(self.fp.read(2))-2
    s = ImageFile._safe_read(self.fp, n)
    while len(s):
        if len(s) < 65:
            raise SyntaxError("bad quantization table marker")
        v = i8(s[0])
        if v//16 == 0:
            self.quantization[v & 15] = array.array("b", s[1:65])
            s = s[65:]
        else:
            return  # FIXME: add code to read 16-bit tables!
            # raise SyntaxError, "bad quantization table element size"


#
# JPEG marker table

MARKER = {
    0xFFC0: ("SOF0", "Baseline DCT", SOF),
    0xFFC1: ("SOF1", "Extended Sequential DCT", SOF),
    0xFFC2: ("SOF2", "Progressive DCT", SOF),
    0xFFC3: ("SOF3", "Spatial lossless", SOF),
    0xFFC4: ("DHT", "Define Huffman table", Skip),
    0xFFC5: ("SOF5", "Differential sequential DCT", SOF),
    0xFFC6: ("SOF6", "Differential progressive DCT", SOF),
    0xFFC7: ("SOF7", "Differential spatial", SOF),
    0xFFC8: ("JPG", "Extension", None),
    0xFFC9: ("SOF9", "Extended sequential DCT (AC)", SOF),
    0xFFCA: ("SOF10", "Progressive DCT (AC)", SOF),
    0xFFCB: ("SOF11", "Spatial lossless DCT (AC)", SOF),
    0xFFCC: ("DAC", "Define arithmetic coding conditioning", Skip),
    0xFFCD: ("SOF13", "Differential sequential DCT (AC)", SOF),
    0xFFCE: ("SOF14", "Differential progressive DCT (AC)", SOF),
    0xFFCF: ("SOF15", "Differential spatial (AC)", SOF),
    0xFFD0: ("RST0", "Restart 0", None),
    0xFFD1: ("RST1", "Restart 1", None),
    0xFFD2: ("RST2", "Restart 2", None),
    0xFFD3: ("RST3", "Restart 3", None),
    0xFFD4: ("RST4", "Restart 4", None),
    0xFFD5: ("RST5", "Restart 5", None),
    0xFFD6: ("RST6", "Restart 6", None),
    0xFFD7: ("RST7", "Restart 7", None),
    0xFFD8: ("SOI", "Start of image", None),
    0xFFD9: ("EOI", "End of image", None),
    0xFFDA: ("SOS", "Start of scan", Skip),
    0xFFDB: ("DQT", "Define quantization table", DQT),
    0xFFDC: ("DNL", "Define number of lines", Skip),
    0xFFDD: ("DRI", "Define restart interval", Skip),
    0xFFDE: ("DHP", "Define hierarchical progression", SOF),
    0xFFDF: ("EXP", "Expand reference component", Skip),
    0xFFE0: ("APP0", "Application segment 0", APP),
    0xFFE1: ("APP1", "Application segment 1", APP),
    0xFFE2: ("APP2", "Application segment 2", APP),
    0xFFE3: ("APP3", "Application segment 3", APP),
    0xFFE4: ("APP4", "Application segment 4", APP),
    0xFFE5: ("APP5", "Application segment 5", APP),
    0xFFE6: ("APP6", "Application segment 6", APP),
    0xFFE7: ("APP7", "Application segment 7", APP),
    0xFFE8: ("APP8", "Application segment 8", APP),
    0xFFE9: ("APP9", "Application segment 9", APP),
    0xFFEA: ("APP10", "Application segment 10", APP),
    0xFFEB: ("APP11", "Application segment 11", APP),
    0xFFEC: ("APP12", "Application segment 12", APP),
    0xFFED: ("APP13", "Application segment 13", APP),
    0xFFEE: ("APP14", "Application segment 14", APP),
    0xFFEF: ("APP15", "Application segment 15", APP),
    0xFFF0: ("JPG0", "Extension 0", None),
    0xFFF1: ("JPG1", "Extension 1", None),
    0xFFF2: ("JPG2", "Extension 2", None),
    0xFFF3: ("JPG3", "Extension 3", None),
    0xFFF4: ("JPG4", "Extension 4", None),
    0xFFF5: ("JPG5", "Extension 5", None),
    0xFFF6: ("JPG6", "Extension 6", None),
    0xFFF7: ("JPG7", "Extension 7", None),
    0xFFF8: ("JPG8", "Extension 8", None),
    0xFFF9: ("JPG9", "Extension 9", None),
    0xFFFA: ("JPG10", "Extension 10", None),
    0xFFFB: ("JPG11", "Extension 11", None),
    0xFFFC: ("JPG12", "Extension 12", None),
    0xFFFD: ("JPG13", "Extension 13", None),
    0xFFFE: ("COM", "Comment", COM)
}


def _accept(prefix):
    return prefix[0:1] == b"\377"


##
# Image plugin for JPEG and JFIF images.

class JpegImageFile(ImageFile.ImageFile):

    format = "JPEG"
    format_description = "JPEG (ISO 10918)"

    def _open(self):

        s = self.fp.read(1)

        if i8(s[0]) != 255:
            raise SyntaxError("not a JPEG file")

        # Create attributes
        self.bits = self.layers = 0

        # JPEG specifics (internal)
        self.layer = []
        self.huffman_dc = {}
        self.huffman_ac = {}
        self.quantization = {}
        self.app = {}  # compatibility
        self.applist = []
        self.icclist = []

        while True:

            i = i8(s)
            if i == 0xFF:
                s = s + self.fp.read(1)
                i = i16(s)
            else:
                # Skip non-0xFF junk
                s = b"\xff"
                continue

            if i in MARKER:
                name, description, handler = MARKER[i]
                # print hex(i), name, description
                if handler is not None:
                    handler(self, i)
                if i == 0xFFDA:  # start of scan
                    rawmode = self.mode
                    if self.mode == "CMYK":
                        rawmode = "CMYK;I"  # assume adobe conventions
                    self.tile = [("jpeg", (0, 0) + self.size, 0, (rawmode, ""))]
                    # self.__offset = self.fp.tell()
                    break
                s = self.fp.read(1)
            elif i == 0 or i == 0xFFFF:
                # padded marker or junk; move on
                s = b"\xff"
            else:
                raise SyntaxError("no marker found")

    def draft(self, mode, size):

        if len(self.tile) != 1:
            return

        d, e, o, a = self.tile[0]
        scale = 0

        if a[0] == "RGB" and mode in ["L", "YCbCr"]:
            self.mode = mode
            a = mode, ""

        if size:
            scale = max(self.size[0] // size[0], self.size[1] // size[1])
            for s in [8, 4, 2, 1]:
                if scale >= s:
                    break
            e = e[0], e[1], (e[2]-e[0]+s-1)//s+e[0], (e[3]-e[1]+s-1)//s+e[1]
            self.size = ((self.size[0]+s-1)//s, (self.size[1]+s-1)//s)
            scale = s

        self.tile = [(d, e, o, a)]
        self.decoderconfig = (scale, 1)

        return self

    def load_djpeg(self):

        # ALTERNATIVE: handle JPEGs via the IJG command line utilities

        import tempfile
        import os
        f, path = tempfile.mkstemp()
        os.close(f)
        if os.path.exists(self.filename):
            os.system("djpeg '%s' >'%s'" % (self.filename, path))
        else:
            raise ValueError("Invalid Filename")

        try:
            self.im = Image.core.open_ppm(path)
        finally:
            try:
                os.unlink(path)
            except:
                pass

        self.mode = self.im.mode
        self.size = self.im.size

        self.tile = []

    def _getexif(self):
        return _getexif(self)


def _getexif(self):
    # Extract EXIF information.  This method is highly experimental,
    # and is likely to be replaced with something better in a future
    # version.
    from PIL import TiffImagePlugin
    import io

    def fixup(value):
        if len(value) == 1:
            return value[0]
        return value
    # The EXIF record consists of a TIFF file embedded in a JPEG
    # application marker (!).
    try:
        data = self.info["exif"]
    except KeyError:
        return None
    file = io.BytesIO(data[6:])
    head = file.read(8)
    exif = {}
    # process dictionary
    info = TiffImagePlugin.ImageFileDirectory(head)
    info.load(file)
    for key, value in info.items():
        exif[key] = fixup(value)
    # get exif extension
    try:
        file.seek(exif[0x8769])
    except KeyError:
        pass
    else:
        info = TiffImagePlugin.ImageFileDirectory(head)
        info.load(file)
        for key, value in info.items():
            exif[key] = fixup(value)
    # get gpsinfo extension
    try:
        file.seek(exif[0x8825])
    except KeyError:
        pass
    else:
        info = TiffImagePlugin.ImageFileDirectory(head)
        info.load(file)
        exif[0x8825] = gps = {}
        for key, value in info.items():
            gps[key] = fixup(value)
    return exif

# --------------------------------------------------------------------
# stuff to save JPEG files

RAWMODE = {
    "1": "L",
    "L": "L",
    "RGB": "RGB",
    "RGBA": "RGB",
    "RGBX": "RGB",
    "CMYK": "CMYK;I",  # assume adobe conventions
    "YCbCr": "YCbCr",
}

zigzag_index = ( 0,  1,  5,  6, 14, 15, 27, 28,
                 2,  4,  7, 13, 16, 26, 29, 42,
                 3,  8, 12, 17, 25, 30, 41, 43,
                 9, 11, 18, 24, 31, 40, 44, 53,
                10, 19, 23, 32, 39, 45, 52, 54,
                20, 22, 33, 38, 46, 51, 55, 60,
                21, 34, 37, 47, 50, 56, 59, 61,
                35, 36, 48, 49, 57, 58, 62, 63)

samplings = {
             (1, 1, 1, 1, 1, 1): 0,
             (2, 1, 1, 1, 1, 1): 1,
             (2, 2, 1, 1, 1, 1): 2,
            }


def convert_dict_qtables(qtables):
    qtables = [qtables[key] for key in range(len(qtables)) if key in qtables]
    for idx, table in enumerate(qtables):
        qtables[idx] = [table[i] for i in zigzag_index]
    return qtables


def get_sampling(im):
    sampling = im.layer[0][1:3] + im.layer[1][1:3] + im.layer[2][1:3]
    return samplings.get(sampling, -1)


def _save(im, fp, filename):

    try:
        rawmode = RAWMODE[im.mode]
    except KeyError:
        raise IOError("cannot write mode %s as JPEG" % im.mode)

    info = im.encoderinfo

    dpi = info.get("dpi", (0, 0))

    quality = info.get("quality", 0)
    subsampling = info.get("subsampling", -1)
    qtables = info.get("qtables")

    if quality == "keep":
        quality = 0
        subsampling = "keep"
        qtables = "keep"
    elif quality in presets:
        preset = presets[quality]
        quality = 0
        subsampling = preset.get('subsampling', -1)
        qtables = preset.get('quantization')
    elif not isinstance(quality, int):
        raise ValueError("Invalid quality setting")
    else:
        if subsampling in presets:
            subsampling = presets[subsampling].get('subsampling', -1)
        if qtables in presets:
            qtables = presets[qtables].get('quantization')

    if subsampling == "4:4:4":
        subsampling = 0
    elif subsampling == "4:2:2":
        subsampling = 1
    elif subsampling == "4:1:1":
        subsampling = 2
    elif subsampling == "keep":
        if im.format != "JPEG":
            raise ValueError("Cannot use 'keep' when original image is not a JPEG")
        subsampling = get_sampling(im)

    def validate_qtables(qtables):
        if qtables is None:
            return qtables
        if isStringType(qtables):
            try:
                lines = [int(num) for line in qtables.splitlines()
                         for num in line.split('#', 1)[0].split()]
            except ValueError:
                raise ValueError("Invalid quantization table")
            else:
                qtables = [lines[s:s+64] for s in range(0, len(lines), 64)]
        if isinstance(qtables, (tuple, list, dict)):
            if isinstance(qtables, dict):
                qtables = convert_dict_qtables(qtables)
            elif isinstance(qtables, tuple):
                qtables = list(qtables)
            if not (0 < len(qtables) < 5):
                raise ValueError("None or too many quantization tables")
            for idx, table in enumerate(qtables):
                try:
                    if len(table) != 64:
                        raise
                    table = array.array('b', table)
                except TypeError:
                    raise ValueError("Invalid quantization table")
                else:
                    qtables[idx] = list(table)
            return qtables

    if qtables == "keep":
        if im.format != "JPEG":
            raise ValueError("Cannot use 'keep' when original image is not a JPEG")
        qtables = getattr(im, "quantization", None)
    qtables = validate_qtables(qtables)

    extra = b""

    icc_profile = info.get("icc_profile")
    if icc_profile:
        ICC_OVERHEAD_LEN = 14
        MAX_BYTES_IN_MARKER = 65533
        MAX_DATA_BYTES_IN_MARKER = MAX_BYTES_IN_MARKER - ICC_OVERHEAD_LEN
        markers = []
        while icc_profile:
            markers.append(icc_profile[:MAX_DATA_BYTES_IN_MARKER])
            icc_profile = icc_profile[MAX_DATA_BYTES_IN_MARKER:]
        i = 1
        for marker in markers:
            size = struct.pack(">H", 2 + ICC_OVERHEAD_LEN + len(marker))
            extra = extra + (b"\xFF\xE2" + size + b"ICC_PROFILE\0" + o8(i) + o8(len(markers)) + marker)
            i = i + 1

    # get keyword arguments
    im.encoderconfig = (
        quality,
        # "progressive" is the official name, but older documentation
        # says "progression"
        # FIXME: issue a warning if the wrong form is used (post-1.1.7)
        "progressive" in info or "progression" in info,
        info.get("smooth", 0),
        "optimize" in info,
        info.get("streamtype", 0),
        dpi[0], dpi[1],
        subsampling,
        qtables,
        extra,
        info.get("exif", b"")
        )

    # if we optimize, libjpeg needs a buffer big enough to hold the whole image
    # in a shot. Guessing on the size, at im.size bytes. (raw pizel size is
    # channels*size, this is a value that's been used in a django patch.
    # https://github.com/jdriscoll/django-imagekit/issues/50
    bufsize = 0
    if "optimize" in info or "progressive" in info or "progression" in info:
        if quality >= 95:
            bufsize = 2 * im.size[0] * im.size[1]
        else:
            bufsize = im.size[0] * im.size[1]

    # The exif info needs to be written as one block, + APP1, + one spare byte.
    # Ensure that our buffer is big enough
    bufsize = max(ImageFile.MAXBLOCK, bufsize, len(info.get("exif", b"")) + 5)

    ImageFile._save(im, fp, [("jpeg", (0, 0)+im.size, 0, rawmode)], bufsize)


def _save_cjpeg(im, fp, filename):
    # ALTERNATIVE: handle JPEGs via the IJG command line utilities.
    import os
    file = im._dump()
    os.system("cjpeg %s >%s" % (file, filename))
    try:
        os.unlink(file)
    except:
        pass

# -------------------------------------------------------------------q-
# Registry stuff

Image.register_open("JPEG", JpegImageFile, _accept)
Image.register_save("JPEG", _save)

Image.register_extension("JPEG", ".jfif")
Image.register_extension("JPEG", ".jpe")
Image.register_extension("JPEG", ".jpg")
Image.register_extension("JPEG", ".jpeg")

Image.register_mime("JPEG", "image/jpeg")

########NEW FILE########
__FILENAME__ = JpegPresets
"""
JPEG quality settings equivalent to the Photoshop settings.

More presets can be added to the presets dict if needed.

Can be use when saving JPEG file.

To apply the preset, specify::

  quality="preset_name"

To apply only the quantization table::

  qtables="preset_name"

To apply only the subsampling setting::

  subsampling="preset_name"

Example::

  im.save("image_name.jpg", quality="web_high")


Subsampling
-----------

Subsampling is the practice of encoding images by implementing less resolution
for chroma information than for luma information.
(ref.: http://en.wikipedia.org/wiki/Chroma_subsampling)

Possible subsampling values are 0, 1 and 2 that correspond to 4:4:4, 4:2:2 and
4:1:1 (or 4:2:0?).

You can get the subsampling of a JPEG with the
`JpegImagePlugin.get_subsampling(im)` function.


Quantization tables
-------------------

They are values use by the DCT (Discrete cosine transform) to remove
*unnecessary* information from the image (the lossy part of the compression).
(ref.: http://en.wikipedia.org/wiki/Quantization_matrix#Quantization_matrices,
http://en.wikipedia.org/wiki/JPEG#Quantization)

You can get the quantization tables of a JPEG with::

  im.quantization

This will return a dict with a number of arrays. You can pass this dict directly
as the qtables argument when saving a JPEG.

The tables format between im.quantization and quantization in presets differ in
3 ways:

1. The base container of the preset is a list with sublists instead of dict.
   dict[0] -> list[0], dict[1] -> list[1], ...
2. Each table in a preset is a list instead of an array.
3. The zigzag order is remove in the preset (needed by libjpeg >= 6a).

You can convert the dict format to the preset format with the
`JpegImagePlugin.convert_dict_qtables(dict_qtables)` function.

Libjpeg ref.: http://www.jpegcameras.com/libjpeg/libjpeg-3.html

"""

presets = {
            'web_low':      {'subsampling':  2, # "4:1:1"
                            'quantization': [
                               [20, 16, 25, 39, 50, 46, 62, 68,
                                16, 18, 23, 38, 38, 53, 65, 68,
                                25, 23, 31, 38, 53, 65, 68, 68,
                                39, 38, 38, 53, 65, 68, 68, 68,
                                50, 38, 53, 65, 68, 68, 68, 68,
                                46, 53, 65, 68, 68, 68, 68, 68,
                                62, 65, 68, 68, 68, 68, 68, 68,
                                68, 68, 68, 68, 68, 68, 68, 68],
                               [21, 25, 32, 38, 54, 68, 68, 68,
                                25, 28, 24, 38, 54, 68, 68, 68,
                                32, 24, 32, 43, 66, 68, 68, 68,
                                38, 38, 43, 53, 68, 68, 68, 68,
                                54, 54, 66, 68, 68, 68, 68, 68,
                                68, 68, 68, 68, 68, 68, 68, 68,
                                68, 68, 68, 68, 68, 68, 68, 68,
                                68, 68, 68, 68, 68, 68, 68, 68]
                            ]},
            'web_medium':   {'subsampling':  2, # "4:1:1"
                            'quantization': [
                               [16, 11, 11, 16, 23, 27, 31, 30,
                                11, 12, 12, 15, 20, 23, 23, 30,
                                11, 12, 13, 16, 23, 26, 35, 47,
                                16, 15, 16, 23, 26, 37, 47, 64,
                                23, 20, 23, 26, 39, 51, 64, 64,
                                27, 23, 26, 37, 51, 64, 64, 64,
                                31, 23, 35, 47, 64, 64, 64, 64,
                                30, 30, 47, 64, 64, 64, 64, 64],
                               [17, 15, 17, 21, 20, 26, 38, 48,
                                15, 19, 18, 17, 20, 26, 35, 43,
                                17, 18, 20, 22, 26, 30, 46, 53,
                                21, 17, 22, 28, 30, 39, 53, 64,
                                20, 20, 26, 30, 39, 48, 64, 64,
                                26, 26, 30, 39, 48, 63, 64, 64,
                                38, 35, 46, 53, 64, 64, 64, 64,
                                48, 43, 53, 64, 64, 64, 64, 64]
                            ]},
            'web_high':     {'subsampling':  0, # "4:4:4"
                            'quantization': [
                               [ 6,  4,  4,  6,  9, 11, 12, 16,
                                 4,  5,  5,  6,  8, 10, 12, 12,
                                 4,  5,  5,  6, 10, 12, 14, 19,
                                 6,  6,  6, 11, 12, 15, 19, 28,
                                 9,  8, 10, 12, 16, 20, 27, 31,
                                11, 10, 12, 15, 20, 27, 31, 31,
                                12, 12, 14, 19, 27, 31, 31, 31,
                                16, 12, 19, 28, 31, 31, 31, 31],
                               [ 7,  7, 13, 24, 26, 31, 31, 31,
                                 7, 12, 16, 21, 31, 31, 31, 31,
                                13, 16, 17, 31, 31, 31, 31, 31,
                                24, 21, 31, 31, 31, 31, 31, 31,
                                26, 31, 31, 31, 31, 31, 31, 31,
                                31, 31, 31, 31, 31, 31, 31, 31,
                                31, 31, 31, 31, 31, 31, 31, 31,
                                31, 31, 31, 31, 31, 31, 31, 31]
                            ]},
            'web_very_high': {'subsampling':  0, # "4:4:4"
                            'quantization': [
                               [ 2,  2,  2,  2,  3,  4,  5,  6,
                                 2,  2,  2,  2,  3,  4,  5,  6,
                                 2,  2,  2,  2,  4,  5,  7,  9,
                                 2,  2,  2,  4,  5,  7,  9, 12,
                                 3,  3,  4,  5,  8, 10, 12, 12,
                                 4,  4,  5,  7, 10, 12, 12, 12,
                                 5,  5,  7,  9, 12, 12, 12, 12,
                                 6,  6,  9, 12, 12, 12, 12, 12],
                               [ 3,  3,  5,  9, 13, 15, 15, 15,
                                 3,  4,  6, 11, 14, 12, 12, 12,
                                 5,  6,  9, 14, 12, 12, 12, 12,
                                 9, 11, 14, 12, 12, 12, 12, 12,
                                13, 14, 12, 12, 12, 12, 12, 12,
                                15, 12, 12, 12, 12, 12, 12, 12,
                                15, 12, 12, 12, 12, 12, 12, 12,
                                15, 12, 12, 12, 12, 12, 12, 12]
                            ]},
            'web_maximum':  {'subsampling':  0, # "4:4:4"
                            'quantization': [
                               [ 1,  1,  1,  1,  1,  1,  1,  1,
                                 1,  1,  1,  1,  1,  1,  1,  1,
                                 1,  1,  1,  1,  1,  1,  1,  2,
                                 1,  1,  1,  1,  1,  1,  2,  2,
                                 1,  1,  1,  1,  1,  2,  2,  3,
                                 1,  1,  1,  1,  2,  2,  3,  3,
                                 1,  1,  1,  2,  2,  3,  3,  3,
                                 1,  1,  2,  2,  3,  3,  3,  3],
                               [ 1,  1,  1,  2,  2,  3,  3,  3,
                                 1,  1,  1,  2,  3,  3,  3,  3,
                                 1,  1,  1,  3,  3,  3,  3,  3,
                                 2,  2,  3,  3,  3,  3,  3,  3,
                                 2,  3,  3,  3,  3,  3,  3,  3,
                                 3,  3,  3,  3,  3,  3,  3,  3,
                                 3,  3,  3,  3,  3,  3,  3,  3,
                                 3,  3,  3,  3,  3,  3,  3,  3]
                            ]},
            'low':          {'subsampling':  2, # "4:1:1"
                            'quantization': [
                               [18, 14, 14, 21, 30, 35, 34, 17,
                                14, 16, 16, 19, 26, 23, 12, 12,
                                14, 16, 17, 21, 23, 12, 12, 12,
                                21, 19, 21, 23, 12, 12, 12, 12,
                                30, 26, 23, 12, 12, 12, 12, 12,
                                35, 23, 12, 12, 12, 12, 12, 12,
                                34, 12, 12, 12, 12, 12, 12, 12,
                                17, 12, 12, 12, 12, 12, 12, 12],
                               [20, 19, 22, 27, 20, 20, 17, 17,
                                19, 25, 23, 14, 14, 12, 12, 12,
                                22, 23, 14, 14, 12, 12, 12, 12,
                                27, 14, 14, 12, 12, 12, 12, 12,
                                20, 14, 12, 12, 12, 12, 12, 12,
                                20, 12, 12, 12, 12, 12, 12, 12,
                                17, 12, 12, 12, 12, 12, 12, 12,
                                17, 12, 12, 12, 12, 12, 12, 12]
                            ]},
            'medium':       {'subsampling':  2, # "4:1:1"
                            'quantization': [
                               [12,  8,  8, 12, 17, 21, 24, 17,
                                 8,  9,  9, 11, 15, 19, 12, 12,
                                 8,  9, 10, 12, 19, 12, 12, 12,
                                12, 11, 12, 21, 12, 12, 12, 12,
                                17, 15, 19, 12, 12, 12, 12, 12,
                                21, 19, 12, 12, 12, 12, 12, 12,
                                24, 12, 12, 12, 12, 12, 12, 12,
                                17, 12, 12, 12, 12, 12, 12, 12],
                               [13, 11, 13, 16, 20, 20, 17, 17,
                                11, 14, 14, 14, 14, 12, 12, 12,
                                13, 14, 14, 14, 12, 12, 12, 12,
                                16, 14, 14, 12, 12, 12, 12, 12,
                                20, 14, 12, 12, 12, 12, 12, 12,
                                20, 12, 12, 12, 12, 12, 12, 12,
                                17, 12, 12, 12, 12, 12, 12, 12,
                                17, 12, 12, 12, 12, 12, 12, 12]
                            ]},
            'high':         {'subsampling':  0, # "4:4:4"
                            'quantization': [
                               [ 6,  4,  4,  6,  9, 11, 12, 16,
                                 4,  5,  5,  6,  8, 10, 12, 12,
                                 4,  5,  5,  6, 10, 12, 12, 12,
                                 6,  6,  6, 11, 12, 12, 12, 12,
                                 9,  8, 10, 12, 12, 12, 12, 12,
                                11, 10, 12, 12, 12, 12, 12, 12,
                                12, 12, 12, 12, 12, 12, 12, 12,
                                16, 12, 12, 12, 12, 12, 12, 12],
                               [ 7,  7, 13, 24, 20, 20, 17, 17,
                                 7, 12, 16, 14, 14, 12, 12, 12,
                                13, 16, 14, 14, 12, 12, 12, 12,
                                24, 14, 14, 12, 12, 12, 12, 12,
                                20, 14, 12, 12, 12, 12, 12, 12,
                                20, 12, 12, 12, 12, 12, 12, 12,
                                17, 12, 12, 12, 12, 12, 12, 12,
                                17, 12, 12, 12, 12, 12, 12, 12]
                            ]},
            'maximum':      {'subsampling':  0, # "4:4:4"
                            'quantization': [
                               [ 2,  2,  2,  2,  3,  4,  5,  6,
                                 2,  2,  2,  2,  3,  4,  5,  6,
                                 2,  2,  2,  2,  4,  5,  7,  9,
                                 2,  2,  2,  4,  5,  7,  9, 12,
                                 3,  3,  4,  5,  8, 10, 12, 12,
                                 4,  4,  5,  7, 10, 12, 12, 12,
                                 5,  5,  7,  9, 12, 12, 12, 12,
                                 6,  6,  9, 12, 12, 12, 12, 12],
                               [ 3,  3,  5,  9, 13, 15, 15, 15,
                                 3,  4,  6, 10, 14, 12, 12, 12,
                                 5,  6,  9, 14, 12, 12, 12, 12,
                                 9, 10, 14, 12, 12, 12, 12, 12,
                                13, 14, 12, 12, 12, 12, 12, 12,
                                15, 12, 12, 12, 12, 12, 12, 12,
                                15, 12, 12, 12, 12, 12, 12, 12,
                                15, 12, 12, 12, 12, 12, 12, 12]
                            ]},
}
########NEW FILE########
__FILENAME__ = McIdasImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# Basic McIdas support for PIL
#
# History:
# 1997-05-05 fl  Created (8-bit images only)
# 2009-03-08 fl  Added 16/32-bit support.
#
# Thanks to Richard Jones and Craig Swank for specs and samples.
#
# Copyright (c) Secret Labs AB 1997.
# Copyright (c) Fredrik Lundh 1997.
#
# See the README file for information on usage and redistribution.
#

__version__ = "0.2"

import struct
from PIL import Image, ImageFile

def _accept(s):
    return s[:8] == b"\x00\x00\x00\x00\x00\x00\x00\x04"

##
# Image plugin for McIdas area images.

class McIdasImageFile(ImageFile.ImageFile):

    format = "MCIDAS"
    format_description = "McIdas area file"

    def _open(self):

        # parse area file directory
        s = self.fp.read(256)
        if not _accept(s) or len(s) != 256:
            raise SyntaxError("not an McIdas area file")

        self.area_descriptor_raw = s
        self.area_descriptor = w = [0] + list(struct.unpack("!64i", s))

        # get mode
        if w[11] == 1:
            mode = rawmode = "L"
        elif w[11] == 2:
            # FIXME: add memory map support
            mode = "I"; rawmode = "I;16B"
        elif w[11] == 4:
            # FIXME: add memory map support
            mode = "I"; rawmode = "I;32B"
        else:
            raise SyntaxError("unsupported McIdas format")

        self.mode = mode
        self.size = w[10], w[9]

        offset = w[34] + w[15]
        stride = w[15] + w[10]*w[11]*w[14]

        self.tile = [("raw", (0, 0) + self.size, offset, (rawmode, stride, 1))]

# --------------------------------------------------------------------
# registry

Image.register_open("MCIDAS", McIdasImageFile, _accept)

# no default extension

########NEW FILE########
__FILENAME__ = MicImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# Microsoft Image Composer support for PIL
#
# Notes:
#       uses TiffImagePlugin.py to read the actual image streams
#
# History:
#       97-01-20 fl     Created
#
# Copyright (c) Secret Labs AB 1997.
# Copyright (c) Fredrik Lundh 1997.
#
# See the README file for information on usage and redistribution.
#


__version__ = "0.1"


from PIL import Image, TiffImagePlugin
from PIL.OleFileIO import *


#
# --------------------------------------------------------------------


def _accept(prefix):
    return prefix[:8] == MAGIC

##
# Image plugin for Microsoft's Image Composer file format.

class MicImageFile(TiffImagePlugin.TiffImageFile):

    format = "MIC"
    format_description = "Microsoft Image Composer"

    def _open(self):

        # read the OLE directory and see if this is a likely
        # to be a Microsoft Image Composer file

        try:
            self.ole = OleFileIO(self.fp)
        except IOError:
            raise SyntaxError("not an MIC file; invalid OLE file")

        # find ACI subfiles with Image members (maybe not the
        # best way to identify MIC files, but what the... ;-)

        self.images = []
        for file in self.ole.listdir():
            if file[1:] and file[0][-4:] == ".ACI" and file[1] == "Image":
                self.images.append(file)

        # if we didn't find any images, this is probably not
        # an MIC file.
        if not self.images:
            raise SyntaxError("not an MIC file; no image entries")

        self.__fp = self.fp
        self.frame = 0

        if len(self.images) > 1:
            self.category = Image.CONTAINER

        self.seek(0)

    def seek(self, frame):

        try:
            filename = self.images[frame]
        except IndexError:
            raise EOFError("no such frame")

        self.fp = self.ole.openstream(filename)

        TiffImagePlugin.TiffImageFile._open(self)

        self.frame = frame

    def tell(self):

        return self.frame

#
# --------------------------------------------------------------------

Image.register_open("MIC", MicImageFile, _accept)

Image.register_extension("MIC", ".mic")

########NEW FILE########
__FILENAME__ = MpegImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# MPEG file handling
#
# History:
#       95-09-09 fl     Created
#
# Copyright (c) Secret Labs AB 1997.
# Copyright (c) Fredrik Lundh 1995.
#
# See the README file for information on usage and redistribution.
#

__version__ = "0.1"

from PIL import Image, ImageFile
from PIL._binary import i8

#
# Bitstream parser

class BitStream:

    def __init__(self, fp):
        self.fp = fp
        self.bits = 0
        self.bitbuffer = 0

    def next(self):
        return i8(self.fp.read(1))

    def peek(self, bits):
        while self.bits < bits:
            c = self.next()
            if c < 0:
                self.bits = 0
                continue
            self.bitbuffer = (self.bitbuffer << 8) + c
            self.bits = self.bits + 8
        return self.bitbuffer >> (self.bits - bits) & (1 << bits) - 1

    def skip(self, bits):
        while self.bits < bits:
            self.bitbuffer = (self.bitbuffer << 8) + i8(self.fp.read(1))
            self.bits = self.bits + 8
        self.bits = self.bits - bits

    def read(self, bits):
        v = self.peek(bits)
        self.bits = self.bits - bits
        return v

##
# Image plugin for MPEG streams.  This plugin can identify a stream,
# but it cannot read it.

class MpegImageFile(ImageFile.ImageFile):

    format = "MPEG"
    format_description = "MPEG"

    def _open(self):

        s = BitStream(self.fp)

        if s.read(32) != 0x1B3:
            raise SyntaxError("not an MPEG file")

        self.mode = "RGB"
        self.size = s.read(12), s.read(12)


# --------------------------------------------------------------------
# Registry stuff

Image.register_open("MPEG", MpegImageFile)

Image.register_extension("MPEG", ".mpg")
Image.register_extension("MPEG", ".mpeg")

Image.register_mime("MPEG", "video/mpeg")

########NEW FILE########
__FILENAME__ = MspImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# MSP file handling
#
# This is the format used by the Paint program in Windows 1 and 2.
#
# History:
#       95-09-05 fl     Created
#       97-01-03 fl     Read/write MSP images
#
# Copyright (c) Secret Labs AB 1997.
# Copyright (c) Fredrik Lundh 1995-97.
#
# See the README file for information on usage and redistribution.
#


__version__ = "0.1"

from PIL import Image, ImageFile, _binary


#
# read MSP files

i16 = _binary.i16le

def _accept(prefix):
    return prefix[:4] in [b"DanM", b"LinS"]

##
# Image plugin for Windows MSP images.  This plugin supports both
# uncompressed (Windows 1.0).

class MspImageFile(ImageFile.ImageFile):

    format = "MSP"
    format_description = "Windows Paint"

    def _open(self):

        # Header
        s = self.fp.read(32)
        if s[:4] not in [b"DanM", b"LinS"]:
            raise SyntaxError("not an MSP file")

        # Header checksum
        sum = 0
        for i in range(0, 32, 2):
            sum = sum ^ i16(s[i:i+2])
        if sum != 0:
            raise SyntaxError("bad MSP checksum")

        self.mode = "1"
        self.size = i16(s[4:]), i16(s[6:])

        if s[:4] == b"DanM":
            self.tile = [("raw", (0,0)+self.size, 32, ("1", 0, 1))]
        else:
            self.tile = [("msp", (0,0)+self.size, 32+2*self.size[1], None)]

#
# write MSP files (uncompressed only)

o16 = _binary.o16le

def _save(im, fp, filename):

    if im.mode != "1":
        raise IOError("cannot write mode %s as MSP" % im.mode)

    # create MSP header
    header = [0] * 16

    header[0], header[1] = i16(b"Da"), i16(b"nM") # version 1
    header[2], header[3] = im.size
    header[4], header[5] = 1, 1
    header[6], header[7] = 1, 1
    header[8], header[9] = im.size

    sum = 0
    for h in header:
        sum = sum ^ h
    header[12] = sum # FIXME: is this the right field?

    # header
    for h in header:
        fp.write(o16(h))

    # image body
    ImageFile._save(im, fp, [("raw", (0,0)+im.size, 32, ("1", 0, 1))])

#
# registry

Image.register_open("MSP", MspImageFile, _accept)
Image.register_save("MSP", _save)

Image.register_extension("MSP", ".msp")

########NEW FILE########
__FILENAME__ = OleFileIO
#!/usr/local/bin/python
# -*- coding: latin-1 -*-
"""
OleFileIO_PL:
Module to read Microsoft OLE2 files (also called Structured Storage or
Microsoft Compound Document File Format), such as Microsoft Office
documents, Image Composer and FlashPix files, Outlook messages, ...
This version is compatible with Python 2.6+ and 3.x

version 0.30 2014-02-04 Philippe Lagadec - http://www.decalage.info

Project website: http://www.decalage.info/python/olefileio

Improved version of the OleFileIO module from PIL library v1.1.6
See: http://www.pythonware.com/products/pil/index.htm

The Python Imaging Library (PIL) is
    Copyright (c) 1997-2005 by Secret Labs AB
    Copyright (c) 1995-2005 by Fredrik Lundh
OleFileIO_PL changes are Copyright (c) 2005-2014 by Philippe Lagadec

See source code and LICENSE.txt for information on usage and redistribution.

WARNING: THIS IS (STILL) WORK IN PROGRESS.
"""

# Starting with OleFileIO_PL v0.30, only Python 2.6+ and 3.x is supported
# This import enables print() as a function rather than a keyword
# (main requirement to be compatible with Python 3.x)
# The comment on the line below should be printed on Python 2.5 or older:
from __future__ import print_function # This version of OleFileIO_PL requires Python 2.6+ or 3.x.


__author__  = "Philippe Lagadec, Fredrik Lundh (Secret Labs AB)"
__date__    = "2014-02-04"
__version__ = '0.30'

#--- LICENSE ------------------------------------------------------------------

# OleFileIO_PL is an improved version of the OleFileIO module from the
# Python Imaging Library (PIL).

# OleFileIO_PL changes are Copyright (c) 2005-2014 by Philippe Lagadec
#
# The Python Imaging Library (PIL) is
#    Copyright (c) 1997-2005 by Secret Labs AB
#    Copyright (c) 1995-2005 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its associated
# documentation, you agree that you have read, understood, and will comply with
# the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and its
# associated documentation for any purpose and without fee is hereby granted,
# provided that the above copyright notice appears in all copies, and that both
# that copyright notice and this permission notice appear in supporting
# documentation, and that the name of Secret Labs AB or the author(s) not be used
# in advertising or publicity pertaining to distribution of the software
# without specific, written prior permission.
#
# SECRET LABS AB AND THE AUTHORS DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS
# SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS.
# IN NO EVENT SHALL SECRET LABS AB OR THE AUTHORS BE LIABLE FOR ANY SPECIAL,
# INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

#-----------------------------------------------------------------------------
# CHANGELOG: (only OleFileIO_PL changes compared to PIL 1.1.6)
# 2005-05-11 v0.10 PL: - a few fixes for Python 2.4 compatibility
#                        (all changes flagged with [PL])
# 2006-02-22 v0.11 PL: - a few fixes for some Office 2003 documents which raise
#                        exceptions in _OleStream.__init__()
# 2006-06-09 v0.12 PL: - fixes for files above 6.8MB (DIFAT in loadfat)
#                      - added some constants
#                      - added header values checks
#                      - added some docstrings
#                      - getsect: bugfix in case sectors >512 bytes
#                      - getsect: added conformity checks
#                      - DEBUG_MODE constant to activate debug display
# 2007-09-04 v0.13 PL: - improved/translated (lots of) comments
#                      - updated license
#                      - converted tabs to 4 spaces
# 2007-11-19 v0.14 PL: - added OleFileIO._raise_defect() to adapt sensitivity
#                      - improved _unicode() to use Python 2.x unicode support
#                      - fixed bug in _OleDirectoryEntry
# 2007-11-25 v0.15 PL: - added safety checks to detect FAT loops
#                      - fixed _OleStream which didn't check stream size
#                      - added/improved many docstrings and comments
#                      - moved helper functions _unicode and _clsid out of
#                        OleFileIO class
#                      - improved OleFileIO._find() to add Unix path syntax
#                      - OleFileIO._find() is now case-insensitive
#                      - added get_type() and get_rootentry_name()
#                      - rewritten loaddirectory and _OleDirectoryEntry
# 2007-11-27 v0.16 PL: - added _OleDirectoryEntry.kids_dict
#                      - added detection of duplicate filenames in storages
#                      - added detection of duplicate references to streams
#                      - added get_size() and exists() to _OleDirectoryEntry
#                      - added isOleFile to check header before parsing
#                      - added __all__ list to control public keywords in pydoc
# 2007-12-04 v0.17 PL: - added _load_direntry to fix a bug in loaddirectory
#                      - improved _unicode(), added workarounds for Python <2.3
#                      - added set_debug_mode and -d option to set debug mode
#                      - fixed bugs in OleFileIO.open and _OleDirectoryEntry
#                      - added safety check in main for large or binary
#                        properties
#                      - allow size>0 for storages for some implementations
# 2007-12-05 v0.18 PL: - fixed several bugs in handling of FAT, MiniFAT and
#                        streams
#                      - added option '-c' in main to check all streams
# 2009-12-10 v0.19 PL: - bugfix for 32 bit arrays on 64 bits platforms
#                        (thanks to Ben G. and Martijn for reporting the bug)
# 2009-12-11 v0.20 PL: - bugfix in OleFileIO.open when filename is not plain str
# 2010-01-22 v0.21 PL: - added support for big-endian CPUs such as PowerPC Macs
# 2012-02-16 v0.22 PL: - fixed bug in getproperties, patch by chuckleberryfinn
#                        (https://bitbucket.org/decalage/olefileio_pl/issue/7)
#                      - added close method to OleFileIO (fixed issue #2)
# 2012-07-25 v0.23 PL: - added support for file-like objects (patch by mete0r_kr)
# 2013-05-05 v0.24 PL: - getproperties: added conversion from filetime to python
#                        datetime
#                      - main: displays properties with date format
#                      - new class OleMetadata to parse standard properties
#                      - added get_metadata method
# 2013-05-07 v0.24 PL: - a few improvements in OleMetadata
# 2013-05-24 v0.25 PL: - getproperties: option to not convert some timestamps
#                      - OleMetaData: total_edit_time is now a number of seconds,
#                        not a timestamp
#                      - getproperties: added support for VT_BOOL, VT_INT, V_UINT
#                      - getproperties: filter out null chars from strings
#                      - getproperties: raise non-fatal defects instead of
#                        exceptions when properties cannot be parsed properly
# 2013-05-27       PL: - getproperties: improved exception handling
#                      - _raise_defect: added option to set exception type
#                      - all non-fatal issues are now recorded, and displayed
#                        when run as a script
# 2013-07-11 v0.26 PL: - added methods to get modification and creation times
#                        of a directory entry or a storage/stream
#                      - fixed parsing of direntry timestamps
# 2013-07-24       PL: - new options in listdir to list storages and/or streams
# 2014-02-04 v0.30 PL: - upgraded code to support Python 3.x by Martin Panter
#                      - several fixes for Python 2.6 (xrange, MAGIC)
#                      - reused i32 from Pillow's _binary

#-----------------------------------------------------------------------------
# TODO (for version 1.0):
# + isOleFile should accept file-like objects like open
# + fix how all the methods handle unicode str and/or bytes as arguments
# + add path attrib to _OleDirEntry, set it once and for all in init or
#   append_kids (then listdir/_list can be simplified)
# - TESTS with Linux, MacOSX, Python 1.5.2, various files, PIL, ...
# - add underscore to each private method, to avoid their display in
#   pydoc/epydoc documentation - Remove it for classes to be documented
# - replace all raised exceptions with _raise_defect (at least in OleFileIO)
# - merge code from _OleStream and OleFileIO.getsect to read sectors
#   (maybe add a class for FAT and MiniFAT ?)
# - add method to check all streams (follow sectors chains without storing all
#   stream in memory, and report anomalies)
# - use _OleDirectoryEntry.kids_dict to improve _find and _list ?
# - fix Unicode names handling (find some way to stay compatible with Py1.5.2)
#   => if possible avoid converting names to Latin-1
# - review DIFAT code: fix handling of DIFSECT blocks in FAT (not stop)
# - rewrite OleFileIO.getproperties
# - improve docstrings to show more sample uses
# - see also original notes and FIXME below
# - remove all obsolete FIXMEs
# - OleMetadata: fix version attrib according to
#   http://msdn.microsoft.com/en-us/library/dd945671%28v=office.12%29.aspx

# IDEAS:
# - in OleFileIO._open and _OleStream, use size=None instead of 0x7FFFFFFF for
#   streams with unknown size
# - use arrays of int instead of long integers for FAT/MiniFAT, to improve
#   performance and reduce memory usage ? (possible issue with values >2^31)
# - provide tests with unittest (may need write support to create samples)
# - move all debug code (and maybe dump methods) to a separate module, with
#   a class which inherits OleFileIO ?
# - fix docstrings to follow epydoc format
# - add support for 4K sectors ?
# - add support for big endian byte order ?
# - create a simple OLE explorer with wxPython

# FUTURE EVOLUTIONS to add write support:
# 1) add ability to write a stream back on disk from BytesIO (same size, no
#    change in FAT/MiniFAT).
# 2) rename a stream/storage if it doesn't change the RB tree
# 3) use rbtree module to update the red-black tree + any rename
# 4) remove a stream/storage: free sectors in FAT/MiniFAT
# 5) allocate new sectors in FAT/MiniFAT
# 6) create new storage/stream
#-----------------------------------------------------------------------------

#
# THIS IS WORK IN PROGRESS
#
# The Python Imaging Library
# $Id$
#
# stuff to deal with OLE2 Structured Storage files.  this module is
# used by PIL to read Image Composer and FlashPix files, but can also
# be used to read other files of this type.
#
# History:
# 1997-01-20 fl   Created
# 1997-01-22 fl   Fixed 64-bit portability quirk
# 2003-09-09 fl   Fixed typo in OleFileIO.loadfat (noted by Daniel Haertle)
# 2004-02-29 fl   Changed long hex constants to signed integers
#
# Notes:
# FIXME: sort out sign problem (eliminate long hex constants)
# FIXME: change filename to use "a/b/c" instead of ["a", "b", "c"]
# FIXME: provide a glob mechanism function (using fnmatchcase)
#
# Literature:
#
# "FlashPix Format Specification, Appendix A", Kodak and Microsoft,
#  September 1996.
#
# Quotes:
#
# "If this document and functionality of the Software conflict,
#  the actual functionality of the Software represents the correct
#  functionality" -- Microsoft, in the OLE format specification
#
# Copyright (c) Secret Labs AB 1997.
# Copyright (c) Fredrik Lundh 1997.
#
# See the README file for information on usage and redistribution.
#

#------------------------------------------------------------------------------


import io
import sys
import struct, array, os.path, datetime

#[PL] Define explicitly the public API to avoid private objects in pydoc:
__all__ = ['OleFileIO', 'isOleFile', 'MAGIC']

# For Python 3.x, need to redefine long as int:
if str is not bytes:
    long = int

# Need to make sure we use xrange both on Python 2 and 3.x:
try:
    # on Python 2 we need xrange:
    iterrange = xrange
except:
    # no xrange, for Python 3 it was renamed as range:
    iterrange = range

#[PL] workaround to fix an issue with array item size on 64 bits systems:
if array.array('L').itemsize == 4:
    # on 32 bits platforms, long integers in an array are 32 bits:
    UINT32 = 'L'
elif array.array('I').itemsize == 4:
    # on 64 bits platforms, integers in an array are 32 bits:
    UINT32 = 'I'
else:
    raise ValueError('Need to fix a bug with 32 bit arrays, please contact author...')


#[PL] These workarounds were inspired from the Path module
# (see http://www.jorendorff.com/articles/python/path/)
#TODO: test with old Python versions

# Pre-2.3 workaround for basestring.
try:
    basestring
except NameError:
    try:
        # is Unicode supported (Python >2.0 or >1.6 ?)
        basestring = (str, unicode)
    except NameError:
        basestring = str

#[PL] Experimental setting: if True, OLE filenames will be kept in Unicode
# if False (default PIL behaviour), all filenames are converted to Latin-1.
KEEP_UNICODE_NAMES = False

#[PL] DEBUG display mode: False by default, use set_debug_mode() or "-d" on
# command line to change it.
DEBUG_MODE = False
def debug_print(msg):
    print(msg)
def debug_pass(msg):
    pass
debug = debug_pass

def set_debug_mode(debug_mode):
    """
    Set debug mode on or off, to control display of debugging messages.
    mode: True or False
    """
    global DEBUG_MODE, debug
    DEBUG_MODE = debug_mode
    if debug_mode:
        debug = debug_print
    else:
        debug = debug_pass

MAGIC = b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'

#[PL]: added constants for Sector IDs (from AAF specifications)
MAXREGSECT = 0xFFFFFFFA; # maximum SECT
DIFSECT    = 0xFFFFFFFC; # (-4) denotes a DIFAT sector in a FAT
FATSECT    = 0xFFFFFFFD; # (-3) denotes a FAT sector in a FAT
ENDOFCHAIN = 0xFFFFFFFE; # (-2) end of a virtual stream chain
FREESECT   = 0xFFFFFFFF; # (-1) unallocated sector

#[PL]: added constants for Directory Entry IDs (from AAF specifications)
MAXREGSID  = 0xFFFFFFFA; # maximum directory entry ID
NOSTREAM   = 0xFFFFFFFF; # (-1) unallocated directory entry

#[PL] object types in storage (from AAF specifications)
STGTY_EMPTY     = 0 # empty directory entry (according to OpenOffice.org doc)
STGTY_STORAGE   = 1 # element is a storage object
STGTY_STREAM    = 2 # element is a stream object
STGTY_LOCKBYTES = 3 # element is an ILockBytes object
STGTY_PROPERTY  = 4 # element is an IPropertyStorage object
STGTY_ROOT      = 5 # element is a root storage


#
# --------------------------------------------------------------------
# property types

VT_EMPTY=0; VT_NULL=1; VT_I2=2; VT_I4=3; VT_R4=4; VT_R8=5; VT_CY=6;
VT_DATE=7; VT_BSTR=8; VT_DISPATCH=9; VT_ERROR=10; VT_BOOL=11;
VT_VARIANT=12; VT_UNKNOWN=13; VT_DECIMAL=14; VT_I1=16; VT_UI1=17;
VT_UI2=18; VT_UI4=19; VT_I8=20; VT_UI8=21; VT_INT=22; VT_UINT=23;
VT_VOID=24; VT_HRESULT=25; VT_PTR=26; VT_SAFEARRAY=27; VT_CARRAY=28;
VT_USERDEFINED=29; VT_LPSTR=30; VT_LPWSTR=31; VT_FILETIME=64;
VT_BLOB=65; VT_STREAM=66; VT_STORAGE=67; VT_STREAMED_OBJECT=68;
VT_STORED_OBJECT=69; VT_BLOB_OBJECT=70; VT_CF=71; VT_CLSID=72;
VT_VECTOR=0x1000;

# map property id to name (for debugging purposes)

VT = {}
for keyword, var in list(vars().items()):
    if keyword[:3] == "VT_":
        VT[var] = keyword

#
# --------------------------------------------------------------------
# Some common document types (root.clsid fields)

WORD_CLSID = "00020900-0000-0000-C000-000000000046"
#TODO: check Excel, PPT, ...

#[PL]: Defect levels to classify parsing errors - see OleFileIO._raise_defect()
DEFECT_UNSURE =    10    # a case which looks weird, but not sure it's a defect
DEFECT_POTENTIAL = 20    # a potential defect
DEFECT_INCORRECT = 30    # an error according to specifications, but parsing
                         # can go on
DEFECT_FATAL =     40    # an error which cannot be ignored, parsing is
                         # impossible

#[PL] add useful constants to __all__:
for key in list(vars().keys()):
    if key.startswith('STGTY_') or key.startswith('DEFECT_'):
        __all__.append(key)


#--- FUNCTIONS ----------------------------------------------------------------

def isOleFile (filename):
    """
    Test if file is an OLE container (according to its header).
    filename: file name or path (str, unicode)
    return: True if OLE, False otherwise.
    """
    f = open(filename, 'rb')
    header = f.read(len(MAGIC))
    if header == MAGIC:
        return True
    else:
        return False


if bytes is str:
    # version for Python 2.x
    def i8(c):
        return ord(c)
else:
    # version for Python 3.x
    def i8(c):
        return c if c.__class__ is int else c[0]


#TODO: replace i16 and i32 with more readable struct.unpack equivalent?

def i16(c, o = 0):
    """
    Converts a 2-bytes (16 bits) string to an integer.

    c: string containing bytes to convert
    o: offset of bytes to convert in string
    """
    return i8(c[o]) | (i8(c[o+1])<<8)


def i32(c, o = 0):
    """
    Converts a 4-bytes (32 bits) string to an integer.

    c: string containing bytes to convert
    o: offset of bytes to convert in string
    """
##    return int(ord(c[o])+(ord(c[o+1])<<8)+(ord(c[o+2])<<16)+(ord(c[o+3])<<24))
##    # [PL]: added int() because "<<" gives long int since Python 2.4
    # copied from Pillow's _binary:
    return i8(c[o]) | (i8(c[o+1])<<8) | (i8(c[o+2])<<16) | (i8(c[o+3])<<24)


def _clsid(clsid):
    """
    Converts a CLSID to a human-readable string.
    clsid: string of length 16.
    """
    assert len(clsid) == 16
    # if clsid is only made of null bytes, return an empty string:
    # (PL: why not simply return the string with zeroes?)
    if not clsid.strip(b"\0"):
        return ""
    return (("%08X-%04X-%04X-%02X%02X-" + "%02X" * 6) %
            ((i32(clsid, 0), i16(clsid, 4), i16(clsid, 6)) +
            tuple(map(i8, clsid[8:16]))))



# UNICODE support:
# (necessary to handle storages/streams names which use Unicode)

def _unicode(s, errors='replace'):
    """
    Map unicode string to Latin 1. (Python with Unicode support)

    s: UTF-16LE unicode string to convert to Latin-1
    errors: 'replace', 'ignore' or 'strict'.
    """
    #TODO: test if it OleFileIO works with Unicode strings, instead of
    #      converting to Latin-1.
    try:
        # First the string is converted to plain Unicode:
        # (assuming it is encoded as UTF-16 little-endian)
        u = s.decode('UTF-16LE', errors)
        if bytes is not str or KEEP_UNICODE_NAMES:
            return u
        else:
            # Second the unicode string is converted to Latin-1
            return u.encode('latin_1', errors)
    except:
        # there was an error during Unicode to Latin-1 conversion:
        raise IOError('incorrect Unicode name')


def filetime2datetime(filetime):
        """
        convert FILETIME (64 bits int) to Python datetime.datetime
        """
        # TODO: manage exception when microseconds is too large
        # inspired from http://code.activestate.com/recipes/511425-filetime-to-datetime/
        _FILETIME_null_date = datetime.datetime(1601, 1, 1, 0, 0, 0)
        #debug('timedelta days=%d' % (filetime//(10*1000000*3600*24)))
        return _FILETIME_null_date + datetime.timedelta(microseconds=filetime//10)



#=== CLASSES ==================================================================

class OleMetadata:
    """
    class to parse and store metadata from standard properties of OLE files.

    Available attributes:
    codepage, title, subject, author, keywords, comments, template,
    last_saved_by, revision_number, total_edit_time, last_printed, create_time,
    last_saved_time, num_pages, num_words, num_chars, thumbnail,
    creating_application, security, codepage_doc, category, presentation_target,
    bytes, lines, paragraphs, slides, notes, hidden_slides, mm_clips,
    scale_crop, heading_pairs, titles_of_parts, manager, company, links_dirty,
    chars_with_spaces, unused, shared_doc, link_base, hlinks, hlinks_changed,
    version, dig_sig, content_type, content_status, language, doc_version

    Note: an attribute is set to None when not present in the properties of the
    OLE file.

    References for SummaryInformation stream:
    - http://msdn.microsoft.com/en-us/library/dd942545.aspx
    - http://msdn.microsoft.com/en-us/library/dd925819%28v=office.12%29.aspx
    - http://msdn.microsoft.com/en-us/library/windows/desktop/aa380376%28v=vs.85%29.aspx
    - http://msdn.microsoft.com/en-us/library/aa372045.aspx
    - http://sedna-soft.de/summary-information-stream/
    - http://poi.apache.org/apidocs/org/apache/poi/hpsf/SummaryInformation.html

    References for DocumentSummaryInformation stream:
    - http://msdn.microsoft.com/en-us/library/dd945671%28v=office.12%29.aspx
    - http://msdn.microsoft.com/en-us/library/windows/desktop/aa380374%28v=vs.85%29.aspx
    - http://poi.apache.org/apidocs/org/apache/poi/hpsf/DocumentSummaryInformation.html

    new in version 0.25
    """

    # attribute names for SummaryInformation stream properties:
    # (ordered by property id, starting at 1)
    SUMMARY_ATTRIBS = ['codepage', 'title', 'subject', 'author', 'keywords', 'comments',
        'template', 'last_saved_by', 'revision_number', 'total_edit_time',
        'last_printed', 'create_time', 'last_saved_time', 'num_pages',
        'num_words', 'num_chars', 'thumbnail', 'creating_application',
        'security']

    # attribute names for DocumentSummaryInformation stream properties:
    # (ordered by property id, starting at 1)
    DOCSUM_ATTRIBS = ['codepage_doc', 'category', 'presentation_target', 'bytes', 'lines', 'paragraphs',
        'slides', 'notes', 'hidden_slides', 'mm_clips',
        'scale_crop', 'heading_pairs', 'titles_of_parts', 'manager',
        'company', 'links_dirty', 'chars_with_spaces', 'unused', 'shared_doc',
        'link_base', 'hlinks', 'hlinks_changed', 'version', 'dig_sig',
        'content_type', 'content_status', 'language', 'doc_version']

    def __init__(self):
        """
        Constructor for OleMetadata
        All attributes are set to None by default
        """
        # properties from SummaryInformation stream
        self.codepage = None
        self.title = None
        self.subject = None
        self.author = None
        self.keywords = None
        self.comments = None
        self.template = None
        self.last_saved_by = None
        self.revision_number = None
        self.total_edit_time = None
        self.last_printed = None
        self.create_time = None
        self.last_saved_time = None
        self.num_pages = None
        self.num_words = None
        self.num_chars = None
        self.thumbnail = None
        self.creating_application = None
        self.security = None
        # properties from DocumentSummaryInformation stream
        self.codepage_doc = None
        self.category = None
        self.presentation_target = None
        self.bytes = None
        self.lines = None
        self.paragraphs = None
        self.slides = None
        self.notes = None
        self.hidden_slides = None
        self.mm_clips = None
        self.scale_crop = None
        self.heading_pairs = None
        self.titles_of_parts = None
        self.manager = None
        self.company = None
        self.links_dirty = None
        self.chars_with_spaces = None
        self.unused = None
        self.shared_doc = None
        self.link_base = None
        self.hlinks = None
        self.hlinks_changed = None
        self.version = None
        self.dig_sig = None
        self.content_type = None
        self.content_status = None
        self.language = None
        self.doc_version = None


    def parse_properties(self, olefile):
        """
        Parse standard properties of an OLE file, from the streams
        "\x05SummaryInformation" and "\x05DocumentSummaryInformation",
        if present.
        Properties are converted to strings, integers or python datetime objects.
        If a property is not present, its value is set to None.
        """
        # first set all attributes to None:
        for attrib in (self.SUMMARY_ATTRIBS + self.DOCSUM_ATTRIBS):
            setattr(self, attrib, None)
        if olefile.exists("\x05SummaryInformation"):
            # get properties from the stream:
            # (converting timestamps to python datetime, except total_edit_time,
            # which is property #10)
            props = olefile.getproperties("\x05SummaryInformation",
                convert_time=True, no_conversion=[10])
            # store them into this object's attributes:
            for i in range(len(self.SUMMARY_ATTRIBS)):
                # ids for standards properties start at 0x01, until 0x13
                value = props.get(i+1, None)
                setattr(self, self.SUMMARY_ATTRIBS[i], value)
        if olefile.exists("\x05DocumentSummaryInformation"):
            # get properties from the stream:
            props = olefile.getproperties("\x05DocumentSummaryInformation",
                convert_time=True)
            # store them into this object's attributes:
            for i in range(len(self.DOCSUM_ATTRIBS)):
                # ids for standards properties start at 0x01, until 0x13
                value = props.get(i+1, None)
                setattr(self, self.DOCSUM_ATTRIBS[i], value)

    def dump(self):
        """
        Dump all metadata, for debugging purposes.
        """
        print('Properties from SummaryInformation stream:')
        for prop in self.SUMMARY_ATTRIBS:
            value = getattr(self, prop)
            print('- %s: %s' % (prop, repr(value)))
        print('Properties from DocumentSummaryInformation stream:')
        for prop in self.DOCSUM_ATTRIBS:
            value = getattr(self, prop)
            print('- %s: %s' % (prop, repr(value)))


#--- _OleStream ---------------------------------------------------------------

class _OleStream(io.BytesIO):
    """
    OLE2 Stream

    Returns a read-only file object which can be used to read
    the contents of a OLE stream (instance of the BytesIO class).
    To open a stream, use the openstream method in the OleFile class.

    This function can be used with either ordinary streams,
    or ministreams, depending on the offset, sectorsize, and
    fat table arguments.

    Attributes:
        - size: actual size of data stream, after it was opened.
    """

    # FIXME: should store the list of sects obtained by following
    # the fat chain, and load new sectors on demand instead of
    # loading it all in one go.

    def __init__(self, fp, sect, size, offset, sectorsize, fat, filesize):
        """
        Constructor for _OleStream class.

        fp        : file object, the OLE container or the MiniFAT stream
        sect      : sector index of first sector in the stream
        size      : total size of the stream
        offset    : offset in bytes for the first FAT or MiniFAT sector
        sectorsize: size of one sector
        fat       : array/list of sector indexes (FAT or MiniFAT)
        filesize  : size of OLE file (for debugging)
        return    : a BytesIO instance containing the OLE stream
        """
        debug('_OleStream.__init__:')
        debug('  sect=%d (%X), size=%d, offset=%d, sectorsize=%d, len(fat)=%d, fp=%s'
            %(sect,sect,size,offset,sectorsize,len(fat), repr(fp)))
        #[PL] To detect malformed documents with FAT loops, we compute the
        # expected number of sectors in the stream:
        unknown_size = False
        if size==0x7FFFFFFF:
            # this is the case when called from OleFileIO._open(), and stream
            # size is not known in advance (for example when reading the
            # Directory stream). Then we can only guess maximum size:
            size = len(fat)*sectorsize
            # and we keep a record that size was unknown:
            unknown_size = True
            debug('  stream with UNKNOWN SIZE')
        nb_sectors = (size + (sectorsize-1)) // sectorsize
        debug('nb_sectors = %d' % nb_sectors)
        # This number should (at least) be less than the total number of
        # sectors in the given FAT:
        if nb_sectors > len(fat):
            raise IOError('malformed OLE document, stream too large')
        # optimization(?): data is first a list of strings, and join() is called
        # at the end to concatenate all in one string.
        # (this may not be really useful with recent Python versions)
        data = []
        # if size is zero, then first sector index should be ENDOFCHAIN:
        if size == 0 and sect != ENDOFCHAIN:
            debug('size == 0 and sect != ENDOFCHAIN:')
            raise IOError('incorrect OLE sector index for empty stream')
        #[PL] A fixed-length for loop is used instead of an undefined while
        # loop to avoid DoS attacks:
        for i in range(nb_sectors):
            # Sector index may be ENDOFCHAIN, but only if size was unknown
            if sect == ENDOFCHAIN:
                if unknown_size:
                    break
                else:
                    # else this means that the stream is smaller than declared:
                    debug('sect=ENDOFCHAIN before expected size')
                    raise IOError('incomplete OLE stream')
            # sector index should be within FAT:
            if sect<0 or sect>=len(fat):
                debug('sect=%d (%X) / len(fat)=%d' % (sect, sect, len(fat)))
                debug('i=%d / nb_sectors=%d' %(i, nb_sectors))
##                tmp_data = b"".join(data)
##                f = open('test_debug.bin', 'wb')
##                f.write(tmp_data)
##                f.close()
##                debug('data read so far: %d bytes' % len(tmp_data))
                raise IOError('incorrect OLE FAT, sector index out of range')
            #TODO: merge this code with OleFileIO.getsect() ?
            #TODO: check if this works with 4K sectors:
            try:
                fp.seek(offset + sectorsize * sect)
            except:
                debug('sect=%d, seek=%d, filesize=%d' %
                    (sect, offset+sectorsize*sect, filesize))
                raise IOError('OLE sector index out of range')
            sector_data = fp.read(sectorsize)
            # [PL] check if there was enough data:
            # Note: if sector is the last of the file, sometimes it is not a
            # complete sector (of 512 or 4K), so we may read less than
            # sectorsize.
            if len(sector_data)!=sectorsize and sect!=(len(fat)-1):
                debug('sect=%d / len(fat)=%d, seek=%d / filesize=%d, len read=%d' %
                    (sect, len(fat), offset+sectorsize*sect, filesize, len(sector_data)))
                debug('seek+len(read)=%d' % (offset+sectorsize*sect+len(sector_data)))
                raise IOError('incomplete OLE sector')
            data.append(sector_data)
            # jump to next sector in the FAT:
            try:
                sect = fat[sect]
            except IndexError:
                # [PL] if pointer is out of the FAT an exception is raised
                raise IOError('incorrect OLE FAT, sector index out of range')
        #[PL] Last sector should be a "end of chain" marker:
        if sect != ENDOFCHAIN:
            raise IOError('incorrect last sector index in OLE stream')
        data = b"".join(data)
        # Data is truncated to the actual stream size:
        if len(data) >= size:
            data = data[:size]
            # actual stream size is stored for future use:
            self.size = size
        elif unknown_size:
            # actual stream size was not known, now we know the size of read
            # data:
            self.size = len(data)
        else:
            # read data is less than expected:
            debug('len(data)=%d, size=%d' % (len(data), size))
            raise IOError('OLE stream size is less than declared')
        # when all data is read in memory, BytesIO constructor is called
        io.BytesIO.__init__(self, data)
        # Then the _OleStream object can be used as a read-only file object.


#--- _OleDirectoryEntry -------------------------------------------------------

class _OleDirectoryEntry:

    """
    OLE2 Directory Entry
    """
    #[PL] parsing code moved from OleFileIO.loaddirectory

    # struct to parse directory entries:
    # <: little-endian byte order, standard sizes
    #    (note: this should guarantee that Q returns a 64 bits int)
    # 64s: string containing entry name in unicode (max 31 chars) + null char
    # H: uint16, number of bytes used in name buffer, including null = (len+1)*2
    # B: uint8, dir entry type (between 0 and 5)
    # B: uint8, color: 0=black, 1=red
    # I: uint32, index of left child node in the red-black tree, NOSTREAM if none
    # I: uint32, index of right child node in the red-black tree, NOSTREAM if none
    # I: uint32, index of child root node if it is a storage, else NOSTREAM
    # 16s: CLSID, unique identifier (only used if it is a storage)
    # I: uint32, user flags
    # Q (was 8s): uint64, creation timestamp or zero
    # Q (was 8s): uint64, modification timestamp or zero
    # I: uint32, SID of first sector if stream or ministream, SID of 1st sector
    #    of stream containing ministreams if root entry, 0 otherwise
    # I: uint32, total stream size in bytes if stream (low 32 bits), 0 otherwise
    # I: uint32, total stream size in bytes if stream (high 32 bits), 0 otherwise
    STRUCT_DIRENTRY = '<64sHBBIII16sIQQIII'
    # size of a directory entry: 128 bytes
    DIRENTRY_SIZE = 128
    assert struct.calcsize(STRUCT_DIRENTRY) == DIRENTRY_SIZE


    def __init__(self, entry, sid, olefile):
        """
        Constructor for an _OleDirectoryEntry object.
        Parses a 128-bytes entry from the OLE Directory stream.

        entry  : string (must be 128 bytes long)
        sid    : index of this directory entry in the OLE file directory
        olefile: OleFileIO containing this directory entry
        """
        self.sid = sid
        # ref to olefile is stored for future use
        self.olefile = olefile
        # kids is a list of children entries, if this entry is a storage:
        # (list of _OleDirectoryEntry objects)
        self.kids = []
        # kids_dict is a dictionary of children entries, indexed by their
        # name in lowercase: used to quickly find an entry, and to detect
        # duplicates
        self.kids_dict = {}
        # flag used to detect if the entry is referenced more than once in
        # directory:
        self.used = False
        # decode DirEntry
        (
            name,
            namelength,
            self.entry_type,
            self.color,
            self.sid_left,
            self.sid_right,
            self.sid_child,
            clsid,
            self.dwUserFlags,
            self.createTime,
            self.modifyTime,
            self.isectStart,
            sizeLow,
            sizeHigh
        ) = struct.unpack(_OleDirectoryEntry.STRUCT_DIRENTRY, entry)
        if self.entry_type not in [STGTY_ROOT, STGTY_STORAGE, STGTY_STREAM, STGTY_EMPTY]:
            olefile._raise_defect(DEFECT_INCORRECT, 'unhandled OLE storage type')
        # only first directory entry can (and should) be root:
        if self.entry_type == STGTY_ROOT and sid != 0:
            olefile._raise_defect(DEFECT_INCORRECT, 'duplicate OLE root entry')
        if sid == 0 and self.entry_type != STGTY_ROOT:
            olefile._raise_defect(DEFECT_INCORRECT, 'incorrect OLE root entry')
        #debug (struct.unpack(fmt_entry, entry[:len_entry]))
        # name should be at most 31 unicode characters + null character,
        # so 64 bytes in total (31*2 + 2):
        if namelength>64:
            olefile._raise_defect(DEFECT_INCORRECT, 'incorrect DirEntry name length')
            # if exception not raised, namelength is set to the maximum value:
            namelength = 64
        # only characters without ending null char are kept:
        name = name[:(namelength-2)]
        # name is converted from unicode to Latin-1:
        self.name = _unicode(name)

        debug('DirEntry SID=%d: %s' % (self.sid, repr(self.name)))
        debug(' - type: %d' % self.entry_type)
        debug(' - sect: %d' % self.isectStart)
        debug(' - SID left: %d, right: %d, child: %d' % (self.sid_left,
            self.sid_right, self.sid_child))

        # sizeHigh is only used for 4K sectors, it should be zero for 512 bytes
        # sectors, BUT apparently some implementations set it as 0xFFFFFFFF, 1
        # or some other value so it cannot be raised as a defect in general:
        if olefile.sectorsize == 512:
            if sizeHigh != 0 and sizeHigh != 0xFFFFFFFF:
                debug('sectorsize=%d, sizeLow=%d, sizeHigh=%d (%X)' %
                    (olefile.sectorsize, sizeLow, sizeHigh, sizeHigh))
                olefile._raise_defect(DEFECT_UNSURE, 'incorrect OLE stream size')
            self.size = sizeLow
        else:
            self.size = sizeLow + (long(sizeHigh)<<32)
        debug(' - size: %d (sizeLow=%d, sizeHigh=%d)' % (self.size, sizeLow, sizeHigh))

        self.clsid = _clsid(clsid)
        # a storage should have a null size, BUT some implementations such as
        # Word 8 for Mac seem to allow non-null values => Potential defect:
        if self.entry_type == STGTY_STORAGE and self.size != 0:
            olefile._raise_defect(DEFECT_POTENTIAL, 'OLE storage with size>0')
        # check if stream is not already referenced elsewhere:
        if self.entry_type in (STGTY_ROOT, STGTY_STREAM) and self.size>0:
            if self.size < olefile.minisectorcutoff \
            and self.entry_type==STGTY_STREAM: # only streams can be in MiniFAT
                # ministream object
                minifat = True
            else:
                minifat = False
            olefile._check_duplicate_stream(self.isectStart, minifat)



    def build_storage_tree(self):
        """
        Read and build the red-black tree attached to this _OleDirectoryEntry
        object, if it is a storage.
        Note that this method builds a tree of all subentries, so it should
        only be called for the root object once.
        """
        debug('build_storage_tree: SID=%d - %s - sid_child=%d'
            % (self.sid, repr(self.name), self.sid_child))
        if self.sid_child != NOSTREAM:
            # if child SID is not NOSTREAM, then this entry is a storage.
            # Let's walk through the tree of children to fill the kids list:
            self.append_kids(self.sid_child)

            # Note from OpenOffice documentation: the safest way is to
            # recreate the tree because some implementations may store broken
            # red-black trees...

            # in the OLE file, entries are sorted on (length, name).
            # for convenience, we sort them on name instead:
            # (see rich comparison methods in this class)
            self.kids.sort()


    def append_kids(self, child_sid):
        """
        Walk through red-black tree of children of this directory entry to add
        all of them to the kids list. (recursive method)

        child_sid : index of child directory entry to use, or None when called
                    first time for the root. (only used during recursion)
        """
        #[PL] this method was added to use simple recursion instead of a complex
        # algorithm.
        # if this is not a storage or a leaf of the tree, nothing to do:
        if child_sid == NOSTREAM:
            return
        # check if child SID is in the proper range:
        if child_sid<0 or child_sid>=len(self.olefile.direntries):
            self.olefile._raise_defect(DEFECT_FATAL, 'OLE DirEntry index out of range')
        # get child direntry:
        child = self.olefile._load_direntry(child_sid) #direntries[child_sid]
        debug('append_kids: child_sid=%d - %s - sid_left=%d, sid_right=%d, sid_child=%d'
            % (child.sid, repr(child.name), child.sid_left, child.sid_right, child.sid_child))
        # the directory entries are organized as a red-black tree.
        # (cf. Wikipedia for details)
        # First walk through left side of the tree:
        self.append_kids(child.sid_left)
        # Check if its name is not already used (case-insensitive):
        name_lower = child.name.lower()
        if name_lower in self.kids_dict:
            self.olefile._raise_defect(DEFECT_INCORRECT,
                "Duplicate filename in OLE storage")
        # Then the child_sid _OleDirectoryEntry object is appended to the
        # kids list and dictionary:
        self.kids.append(child)
        self.kids_dict[name_lower] = child
        # Check if kid was not already referenced in a storage:
        if child.used:
            self.olefile._raise_defect(DEFECT_INCORRECT,
                'OLE Entry referenced more than once')
        child.used = True
        # Finally walk through right side of the tree:
        self.append_kids(child.sid_right)
        # Afterwards build kid's own tree if it's also a storage:
        child.build_storage_tree()


    def __eq__(self, other):
        "Compare entries by name"
        return self.name == other.name

    def __lt__(self, other):
        "Compare entries by name"
        return self.name < other.name

    def __ne__(self, other):
        return not self.__eq__(other)

    def __le__(self, other):
        return self.__eq__(other) or self.__lt__(other)

    # Reflected __lt__() and __le__() will be used for __gt__() and __ge__()

    #TODO: replace by the same function as MS implementation ?
    # (order by name length first, then case-insensitive order)


    def dump(self, tab = 0):
        "Dump this entry, and all its subentries (for debug purposes only)"
        TYPES = ["(invalid)", "(storage)", "(stream)", "(lockbytes)",
                 "(property)", "(root)"]
        print(" "*tab + repr(self.name), TYPES[self.entry_type], end=' ')
        if self.entry_type in (STGTY_STREAM, STGTY_ROOT):
            print(self.size, "bytes", end=' ')
        print()
        if self.entry_type in (STGTY_STORAGE, STGTY_ROOT) and self.clsid:
            print(" "*tab + "{%s}" % self.clsid)

        for kid in self.kids:
            kid.dump(tab + 2)


    def getmtime(self):
        """
        Return modification time of a directory entry.

        return: None if modification time is null, a python datetime object
        otherwise (UTC timezone)

        new in version 0.26
        """
        if self.modifyTime == 0:
            return None
        return filetime2datetime(self.modifyTime)


    def getctime(self):
        """
        Return creation time of a directory entry.

        return: None if modification time is null, a python datetime object
        otherwise (UTC timezone)

        new in version 0.26
        """
        if self.createTime == 0:
            return None
        return filetime2datetime(self.createTime)


#--- OleFileIO ----------------------------------------------------------------

class OleFileIO:
    """
    OLE container object

    This class encapsulates the interface to an OLE 2 structured
    storage file.  Use the {@link listdir} and {@link openstream} methods to
    access the contents of this file.

    Object names are given as a list of strings, one for each subentry
    level.  The root entry should be omitted.  For example, the following
    code extracts all image streams from a Microsoft Image Composer file::

        ole = OleFileIO("fan.mic")

        for entry in ole.listdir():
            if entry[1:2] == "Image":
                fin = ole.openstream(entry)
                fout = open(entry[0:1], "wb")
                while True:
                    s = fin.read(8192)
                    if not s:
                        break
                    fout.write(s)

    You can use the viewer application provided with the Python Imaging
    Library to view the resulting files (which happens to be standard
    TIFF files).
    """

    def __init__(self, filename = None, raise_defects=DEFECT_FATAL):
        """
        Constructor for OleFileIO class.

        filename: file to open.
        raise_defects: minimal level for defects to be raised as exceptions.
        (use DEFECT_FATAL for a typical application, DEFECT_INCORRECT for a
        security-oriented application, see source code for details)
        """
        # minimal level for defects to be raised as exceptions:
        self._raise_defects_level = raise_defects
        # list of defects/issues not raised as exceptions:
        # tuples of (exception type, message)
        self.parsing_issues = []
        if filename:
            self.open(filename)


    def _raise_defect(self, defect_level, message, exception_type=IOError):
        """
        This method should be called for any defect found during file parsing.
        It may raise an IOError exception according to the minimal level chosen
        for the OleFileIO object.

        defect_level: defect level, possible values are:
            DEFECT_UNSURE    : a case which looks weird, but not sure it's a defect
            DEFECT_POTENTIAL : a potential defect
            DEFECT_INCORRECT : an error according to specifications, but parsing can go on
            DEFECT_FATAL     : an error which cannot be ignored, parsing is impossible
        message: string describing the defect, used with raised exception.
        exception_type: exception class to be raised, IOError by default
        """
        # added by [PL]
        if defect_level >= self._raise_defects_level:
            raise exception_type(message)
        else:
            # just record the issue, no exception raised:
            self.parsing_issues.append((exception_type, message))


    def open(self, filename):
        """
        Open an OLE2 file.
        Reads the header, FAT and directory.

        filename: string-like or file-like object
        """
        #[PL] check if filename is a string-like or file-like object:
        # (it is better to check for a read() method)
        if hasattr(filename, 'read'):
            # file-like object
            self.fp = filename
        else:
            # string-like object: filename of file on disk
            #TODO: if larger than 1024 bytes, this could be the actual data => BytesIO
            self.fp = open(filename, "rb")
        # old code fails if filename is not a plain string:
        #if isinstance(filename, (bytes, basestring)):
        #    self.fp = open(filename, "rb")
        #else:
        #    self.fp = filename
        # obtain the filesize by using seek and tell, which should work on most
        # file-like objects:
        #TODO: do it above, using getsize with filename when possible?
        #TODO: fix code to fail with clear exception when filesize cannot be obtained
        self.fp.seek(0, os.SEEK_END)
        try:
            filesize = self.fp.tell()
        finally:
            self.fp.seek(0)
        self._filesize = filesize

        # lists of streams in FAT and MiniFAT, to detect duplicate references
        # (list of indexes of first sectors of each stream)
        self._used_streams_fat = []
        self._used_streams_minifat = []

        header = self.fp.read(512)

        if len(header) != 512 or header[:8] != MAGIC:
            self._raise_defect(DEFECT_FATAL, "not an OLE2 structured storage file")

        # [PL] header structure according to AAF specifications:
        ##Header
        ##struct StructuredStorageHeader { // [offset from start (bytes), length (bytes)]
        ##BYTE _abSig[8]; // [00H,08] {0xd0, 0xcf, 0x11, 0xe0, 0xa1, 0xb1,
        ##                // 0x1a, 0xe1} for current version
        ##CLSID _clsid;   // [08H,16] reserved must be zero (WriteClassStg/
        ##                // GetClassFile uses root directory class id)
        ##USHORT _uMinorVersion; // [18H,02] minor version of the format: 33 is
        ##                       // written by reference implementation
        ##USHORT _uDllVersion;   // [1AH,02] major version of the dll/format: 3 for
        ##                       // 512-byte sectors, 4 for 4 KB sectors
        ##USHORT _uByteOrder;    // [1CH,02] 0xFFFE: indicates Intel byte-ordering
        ##USHORT _uSectorShift;  // [1EH,02] size of sectors in power-of-two;
        ##                       // typically 9 indicating 512-byte sectors
        ##USHORT _uMiniSectorShift; // [20H,02] size of mini-sectors in power-of-two;
        ##                          // typically 6 indicating 64-byte mini-sectors
        ##USHORT _usReserved; // [22H,02] reserved, must be zero
        ##ULONG _ulReserved1; // [24H,04] reserved, must be zero
        ##FSINDEX _csectDir; // [28H,04] must be zero for 512-byte sectors,
        ##                   // number of SECTs in directory chain for 4 KB
        ##                   // sectors
        ##FSINDEX _csectFat; // [2CH,04] number of SECTs in the FAT chain
        ##SECT _sectDirStart; // [30H,04] first SECT in the directory chain
        ##DFSIGNATURE _signature; // [34H,04] signature used for transactions; must
        ##                        // be zero. The reference implementation
        ##                        // does not support transactions
        ##ULONG _ulMiniSectorCutoff; // [38H,04] maximum size for a mini stream;
        ##                           // typically 4096 bytes
        ##SECT _sectMiniFatStart; // [3CH,04] first SECT in the MiniFAT chain
        ##FSINDEX _csectMiniFat; // [40H,04] number of SECTs in the MiniFAT chain
        ##SECT _sectDifStart; // [44H,04] first SECT in the DIFAT chain
        ##FSINDEX _csectDif; // [48H,04] number of SECTs in the DIFAT chain
        ##SECT _sectFat[109]; // [4CH,436] the SECTs of first 109 FAT sectors
        ##};

        # [PL] header decoding:
        # '<' indicates little-endian byte ordering for Intel (cf. struct module help)
        fmt_header = '<8s16sHHHHHHLLLLLLLLLL'
        header_size = struct.calcsize(fmt_header)
        debug( "fmt_header size = %d, +FAT = %d" % (header_size, header_size + 109*4) )
        header1 = header[:header_size]
        (
            self.Sig,
            self.clsid,
            self.MinorVersion,
            self.DllVersion,
            self.ByteOrder,
            self.SectorShift,
            self.MiniSectorShift,
            self.Reserved, self.Reserved1,
            self.csectDir,
            self.csectFat,
            self.sectDirStart,
            self.signature,
            self.MiniSectorCutoff,
            self.MiniFatStart,
            self.csectMiniFat,
            self.sectDifStart,
            self.csectDif
        ) = struct.unpack(fmt_header, header1)
        debug( struct.unpack(fmt_header,    header1))

        if self.Sig != MAGIC:
            # OLE signature should always be present
            self._raise_defect(DEFECT_FATAL, "incorrect OLE signature")
        if self.clsid != bytearray(16):
            # according to AAF specs, CLSID should always be zero
            self._raise_defect(DEFECT_INCORRECT, "incorrect CLSID in OLE header")
        debug( "MinorVersion = %d" % self.MinorVersion )
        debug( "DllVersion   = %d" % self.DllVersion )
        if self.DllVersion not in [3, 4]:
            # version 3: usual format, 512 bytes per sector
            # version 4: large format, 4K per sector
            self._raise_defect(DEFECT_INCORRECT, "incorrect DllVersion in OLE header")
        debug( "ByteOrder    = %X" % self.ByteOrder )
        if self.ByteOrder != 0xFFFE:
            # For now only common little-endian documents are handled correctly
            self._raise_defect(DEFECT_FATAL, "incorrect ByteOrder in OLE header")
            # TODO: add big-endian support for documents created on Mac ?
        self.SectorSize = 2**self.SectorShift
        debug( "SectorSize   = %d" % self.SectorSize )
        if self.SectorSize not in [512, 4096]:
            self._raise_defect(DEFECT_INCORRECT, "incorrect SectorSize in OLE header")
        if (self.DllVersion==3 and self.SectorSize!=512) \
        or (self.DllVersion==4 and self.SectorSize!=4096):
            self._raise_defect(DEFECT_INCORRECT, "SectorSize does not match DllVersion in OLE header")
        self.MiniSectorSize = 2**self.MiniSectorShift
        debug( "MiniSectorSize   = %d" % self.MiniSectorSize )
        if self.MiniSectorSize not in [64]:
            self._raise_defect(DEFECT_INCORRECT, "incorrect MiniSectorSize in OLE header")
        if self.Reserved != 0 or self.Reserved1 != 0:
            self._raise_defect(DEFECT_INCORRECT, "incorrect OLE header (non-null reserved bytes)")
        debug( "csectDir     = %d" % self.csectDir )
        if self.SectorSize==512 and self.csectDir!=0:
            self._raise_defect(DEFECT_INCORRECT, "incorrect csectDir in OLE header")
        debug( "csectFat     = %d" % self.csectFat )
        debug( "sectDirStart = %X" % self.sectDirStart )
        debug( "signature    = %d" % self.signature )
        # Signature should be zero, BUT some implementations do not follow this
        # rule => only a potential defect:
        if self.signature != 0:
            self._raise_defect(DEFECT_POTENTIAL, "incorrect OLE header (signature>0)")
        debug( "MiniSectorCutoff = %d" % self.MiniSectorCutoff )
        debug( "MiniFatStart     = %X" % self.MiniFatStart )
        debug( "csectMiniFat     = %d" % self.csectMiniFat )
        debug( "sectDifStart     = %X" % self.sectDifStart )
        debug( "csectDif         = %d" % self.csectDif )

        # calculate the number of sectors in the file
        # (-1 because header doesn't count)
        self.nb_sect = ( (filesize + self.SectorSize-1) // self.SectorSize) - 1
        debug( "Number of sectors in the file: %d" % self.nb_sect )

        # file clsid (probably never used, so we don't store it)
        clsid = _clsid(header[8:24])
        self.sectorsize = self.SectorSize #1 << i16(header, 30)
        self.minisectorsize = self.MiniSectorSize  #1 << i16(header, 32)
        self.minisectorcutoff = self.MiniSectorCutoff # i32(header, 56)

        # check known streams for duplicate references (these are always in FAT,
        # never in MiniFAT):
        self._check_duplicate_stream(self.sectDirStart)
        # check MiniFAT only if it is not empty:
        if self.csectMiniFat:
            self._check_duplicate_stream(self.MiniFatStart)
        # check DIFAT only if it is not empty:
        if self.csectDif:
            self._check_duplicate_stream(self.sectDifStart)

        # Load file allocation tables
        self.loadfat(header)
        # Load direcory.  This sets both the direntries list (ordered by sid)
        # and the root (ordered by hierarchy) members.
        self.loaddirectory(self.sectDirStart)#i32(header, 48))
        self.ministream = None
        self.minifatsect = self.MiniFatStart #i32(header, 60)


    def close(self):
        """
        close the OLE file, to release the file object
        """
        self.fp.close()


    def _check_duplicate_stream(self, first_sect, minifat=False):
        """
        Checks if a stream has not been already referenced elsewhere.
        This method should only be called once for each known stream, and only
        if stream size is not null.
        first_sect: index of first sector of the stream in FAT
        minifat: if True, stream is located in the MiniFAT, else in the FAT
        """
        if minifat:
            debug('_check_duplicate_stream: sect=%d in MiniFAT' % first_sect)
            used_streams = self._used_streams_minifat
        else:
            debug('_check_duplicate_stream: sect=%d in FAT' % first_sect)
            # some values can be safely ignored (not a real stream):
            if first_sect in (DIFSECT,FATSECT,ENDOFCHAIN,FREESECT):
                return
            used_streams = self._used_streams_fat
        #TODO: would it be more efficient using a dict or hash values, instead
        #      of a list of long ?
        if first_sect in used_streams:
            self._raise_defect(DEFECT_INCORRECT, 'Stream referenced twice')
        else:
            used_streams.append(first_sect)


    def dumpfat(self, fat, firstindex=0):
        "Displays a part of FAT in human-readable form for debugging purpose"
        # [PL] added only for debug
        if not DEBUG_MODE:
            return
        # dictionary to convert special FAT values in human-readable strings
        VPL=8 # valeurs par ligne (8+1 * 8+1 = 81)
        fatnames = {
            FREESECT:   "..free..",
            ENDOFCHAIN: "[ END. ]",
            FATSECT:    "FATSECT ",
            DIFSECT:    "DIFSECT "
            }
        nbsect = len(fat)
        nlines = (nbsect+VPL-1)//VPL
        print("index", end=" ")
        for i in range(VPL):
            print("%8X" % i, end=" ")
        print()
        for l in range(nlines):
            index = l*VPL
            print("%8X:" % (firstindex+index), end=" ")
            for i in range(index, index+VPL):
                if i>=nbsect:
                    break
                sect = fat[i]
                if sect in fatnames:
                    nom = fatnames[sect]
                else:
                    if sect == i+1:
                        nom = "    --->"
                    else:
                        nom = "%8X" % sect
                print(nom, end=" ")
            print()


    def dumpsect(self, sector, firstindex=0):
        "Displays a sector in a human-readable form, for debugging purpose."
        if not DEBUG_MODE:
            return
        VPL=8 # number of values per line (8+1 * 8+1 = 81)
        tab = array.array(UINT32, sector)
        nbsect = len(tab)
        nlines = (nbsect+VPL-1)//VPL
        print("index", end=" ")
        for i in range(VPL):
            print("%8X" % i, end=" ")
        print()
        for l in range(nlines):
            index = l*VPL
            print("%8X:" % (firstindex+index), end=" ")
            for i in range(index, index+VPL):
                if i>=nbsect:
                    break
                sect = tab[i]
                nom = "%8X" % sect
                print(nom, end=" ")
            print()

    def sect2array(self, sect):
        """
        convert a sector to an array of 32 bits unsigned integers,
        swapping bytes on big endian CPUs such as PowerPC (old Macs)
        """
        a = array.array(UINT32, sect)
        # if CPU is big endian, swap bytes:
        if sys.byteorder == 'big':
            a.byteswap()
        return a


    def loadfat_sect(self, sect):
        """
        Adds the indexes of the given sector to the FAT
        sect: string containing the first FAT sector, or array of long integers
        return: index of last FAT sector.
        """
        # a FAT sector is an array of ulong integers.
        if isinstance(sect, array.array):
            # if sect is already an array it is directly used
            fat1 = sect
        else:
            # if it's a raw sector, it is parsed in an array
            fat1 = self.sect2array(sect)
            self.dumpsect(sect)
        # The FAT is a sector chain starting at the first index of itself.
        for isect in fat1:
            #print("isect = %X" % isect)
            if isect == ENDOFCHAIN or isect == FREESECT:
                # the end of the sector chain has been reached
                break
            # read the FAT sector
            s = self.getsect(isect)
            # parse it as an array of 32 bits integers, and add it to the
            # global FAT array
            nextfat = self.sect2array(s)
            self.fat = self.fat + nextfat
        return isect


    def loadfat(self, header):
        """
        Load the FAT table.
        """
        # The header contains a sector  numbers
        # for the first 109 FAT sectors.  Additional sectors are
        # described by DIF blocks

        sect = header[76:512]
        debug( "len(sect)=%d, so %d integers" % (len(sect), len(sect)//4) )
        #fat    = []
        # [PL] FAT is an array of 32 bits unsigned ints, it's more effective
        # to use an array than a list in Python.
        # It's initialized as empty first:
        self.fat = array.array(UINT32)
        self.loadfat_sect(sect)
        #self.dumpfat(self.fat)
##      for i in range(0, len(sect), 4):
##          ix = i32(sect, i)
##          #[PL] if ix == -2 or ix == -1: # ix == 0xFFFFFFFE or ix == 0xFFFFFFFF:
##          if ix == 0xFFFFFFFE or ix == 0xFFFFFFFF:
##              break
##          s = self.getsect(ix)
##          #fat    = fat + [i32(s, i) for i in range(0, len(s), 4)]
##          fat = fat + array.array(UINT32, s)
        if self.csectDif != 0:
            # [PL] There's a DIFAT because file is larger than 6.8MB
            # some checks just in case:
            if self.csectFat <= 109:
                # there must be at least 109 blocks in header and the rest in
                # DIFAT, so number of sectors must be >109.
                self._raise_defect(DEFECT_INCORRECT, 'incorrect DIFAT, not enough sectors')
            if self.sectDifStart >= self.nb_sect:
                # initial DIFAT block index must be valid
                self._raise_defect(DEFECT_FATAL, 'incorrect DIFAT, first index out of range')
            debug( "DIFAT analysis..." )
            # We compute the necessary number of DIFAT sectors :
            # (each DIFAT sector = 127 pointers + 1 towards next DIFAT sector)
            nb_difat = (self.csectFat-109 + 126)//127
            debug( "nb_difat = %d" % nb_difat )
            if self.csectDif != nb_difat:
                raise IOError('incorrect DIFAT')
            isect_difat = self.sectDifStart
            for i in iterrange(nb_difat):
                debug( "DIFAT block %d, sector %X" % (i, isect_difat) )
                #TODO: check if corresponding FAT SID = DIFSECT
                sector_difat = self.getsect(isect_difat)
                difat = self.sect2array(sector_difat)
                self.dumpsect(sector_difat)
                self.loadfat_sect(difat[:127])
                # last DIFAT pointer is next DIFAT sector:
                isect_difat = difat[127]
                debug( "next DIFAT sector: %X" % isect_difat )
            # checks:
            if isect_difat not in [ENDOFCHAIN, FREESECT]:
                # last DIFAT pointer value must be ENDOFCHAIN or FREESECT
                raise IOError('incorrect end of DIFAT')
##          if len(self.fat) != self.csectFat:
##              # FAT should contain csectFat blocks
##              print("FAT length: %d instead of %d" % (len(self.fat), self.csectFat))
##              raise IOError('incorrect DIFAT')
        # since FAT is read from fixed-size sectors, it may contain more values
        # than the actual number of sectors in the file.
        # Keep only the relevant sector indexes:
        if len(self.fat) > self.nb_sect:
            debug('len(fat)=%d, shrunk to nb_sect=%d' % (len(self.fat), self.nb_sect))
            self.fat = self.fat[:self.nb_sect]
        debug('\nFAT:')
        self.dumpfat(self.fat)


    def loadminifat(self):
        """
        Load the MiniFAT table.
        """
        # MiniFAT is stored in a standard  sub-stream, pointed to by a header
        # field.
        # NOTE: there are two sizes to take into account for this stream:
        # 1) Stream size is calculated according to the number of sectors
        #    declared in the OLE header. This allocated stream may be more than
        #    needed to store the actual sector indexes.
        # (self.csectMiniFat is the number of sectors of size self.SectorSize)
        stream_size = self.csectMiniFat * self.SectorSize
        # 2) Actually used size is calculated by dividing the MiniStream size
        #    (given by root entry size) by the size of mini sectors, *4 for
        #    32 bits indexes:
        nb_minisectors = (self.root.size + self.MiniSectorSize-1) // self.MiniSectorSize
        used_size = nb_minisectors * 4
        debug('loadminifat(): minifatsect=%d, nb FAT sectors=%d, used_size=%d, stream_size=%d, nb MiniSectors=%d' %
            (self.minifatsect, self.csectMiniFat, used_size, stream_size, nb_minisectors))
        if used_size > stream_size:
            # This is not really a problem, but may indicate a wrong implementation:
            self._raise_defect(DEFECT_INCORRECT, 'OLE MiniStream is larger than MiniFAT')
        # In any case, first read stream_size:
        s = self._open(self.minifatsect, stream_size, force_FAT=True).read()
        #[PL] Old code replaced by an array:
        #self.minifat = [i32(s, i) for i in range(0, len(s), 4)]
        self.minifat = self.sect2array(s)
        # Then shrink the array to used size, to avoid indexes out of MiniStream:
        debug('MiniFAT shrunk from %d to %d sectors' % (len(self.minifat), nb_minisectors))
        self.minifat = self.minifat[:nb_minisectors]
        debug('loadminifat(): len=%d' % len(self.minifat))
        debug('\nMiniFAT:')
        self.dumpfat(self.minifat)

    def getsect(self, sect):
        """
        Read given sector from file on disk.
        sect: sector index
        returns a string containing the sector data.
        """
        # [PL] this original code was wrong when sectors are 4KB instead of
        # 512 bytes:
        #self.fp.seek(512 + self.sectorsize * sect)
        #[PL]: added safety checks:
        #print("getsect(%X)" % sect)
        try:
            self.fp.seek(self.sectorsize * (sect+1))
        except:
            debug('getsect(): sect=%X, seek=%d, filesize=%d' %
                (sect, self.sectorsize*(sect+1), self._filesize))
            self._raise_defect(DEFECT_FATAL, 'OLE sector index out of range')
        sector = self.fp.read(self.sectorsize)
        if len(sector) != self.sectorsize:
            debug('getsect(): sect=%X, read=%d, sectorsize=%d' %
                (sect, len(sector), self.sectorsize))
            self._raise_defect(DEFECT_FATAL, 'incomplete OLE sector')
        return sector


    def loaddirectory(self, sect):
        """
        Load the directory.
        sect: sector index of directory stream.
        """
        # The directory is  stored in a standard
        # substream, independent of its size.

        # open directory stream as a read-only file:
        # (stream size is not known in advance)
        self.directory_fp = self._open(sect)

        #[PL] to detect malformed documents and avoid DoS attacks, the maximum
        # number of directory entries can be calculated:
        max_entries = self.directory_fp.size // 128
        debug('loaddirectory: size=%d, max_entries=%d' %
            (self.directory_fp.size, max_entries))

        # Create list of directory entries
        #self.direntries = []
        # We start with a list of "None" object
        self.direntries = [None] * max_entries
##        for sid in iterrange(max_entries):
##            entry = fp.read(128)
##            if not entry:
##                break
##            self.direntries.append(_OleDirectoryEntry(entry, sid, self))
        # load root entry:
        root_entry = self._load_direntry(0)
        # Root entry is the first entry:
        self.root = self.direntries[0]
        # read and build all storage trees, starting from the root:
        self.root.build_storage_tree()


    def _load_direntry (self, sid):
        """
        Load a directory entry from the directory.
        This method should only be called once for each storage/stream when
        loading the directory.
        sid: index of storage/stream in the directory.
        return: a _OleDirectoryEntry object
        raise: IOError if the entry has always been referenced.
        """
        # check if SID is OK:
        if sid<0 or sid>=len(self.direntries):
            self._raise_defect(DEFECT_FATAL, "OLE directory index out of range")
        # check if entry was already referenced:
        if self.direntries[sid] is not None:
            self._raise_defect(DEFECT_INCORRECT,
                "double reference for OLE stream/storage")
            # if exception not raised, return the object
            return self.direntries[sid]
        self.directory_fp.seek(sid * 128)
        entry = self.directory_fp.read(128)
        self.direntries[sid] = _OleDirectoryEntry(entry, sid, self)
        return self.direntries[sid]


    def dumpdirectory(self):
        """
        Dump directory (for debugging only)
        """
        self.root.dump()


    def _open(self, start, size = 0x7FFFFFFF, force_FAT=False):
        """
        Open a stream, either in FAT or MiniFAT according to its size.
        (openstream helper)

        start: index of first sector
        size: size of stream (or nothing if size is unknown)
        force_FAT: if False (default), stream will be opened in FAT or MiniFAT
                   according to size. If True, it will always be opened in FAT.
        """
        debug('OleFileIO.open(): sect=%d, size=%d, force_FAT=%s' %
            (start, size, str(force_FAT)))
        # stream size is compared to the MiniSectorCutoff threshold:
        if size < self.minisectorcutoff and not force_FAT:
            # ministream object
            if not self.ministream:
                # load MiniFAT if it wasn't already done:
                self.loadminifat()
                # The first sector index of the miniFAT stream is stored in the
                # root directory entry:
                size_ministream = self.root.size
                debug('Opening MiniStream: sect=%d, size=%d' %
                    (self.root.isectStart, size_ministream))
                self.ministream = self._open(self.root.isectStart,
                    size_ministream, force_FAT=True)
            return _OleStream(self.ministream, start, size, 0,
                              self.minisectorsize, self.minifat,
                              self.ministream.size)
        else:
            # standard stream
            return _OleStream(self.fp, start, size, 512,
                              self.sectorsize, self.fat, self._filesize)


    def _list(self, files, prefix, node, streams=True, storages=False):
        """
        (listdir helper)
        files: list of files to fill in
        prefix: current location in storage tree (list of names)
        node: current node (_OleDirectoryEntry object)
        streams: bool, include streams if True (True by default) - new in v0.26
        storages: bool, include storages if True (False by default) - new in v0.26
        (note: the root storage is never included)
        """
        prefix = prefix + [node.name]
        for entry in node.kids:
            if entry.kids:
                # this is a storage
                if storages:
                    # add it to the list
                    files.append(prefix[1:] + [entry.name])
                # check its kids
                self._list(files, prefix, entry, streams, storages)
            else:
                # this is a stream
                if streams:
                    # add it to the list
                    files.append(prefix[1:] + [entry.name])


    def listdir(self, streams=True, storages=False):
        """
        Return a list of streams stored in this file

        streams: bool, include streams if True (True by default) - new in v0.26
        storages: bool, include storages if True (False by default) - new in v0.26
        (note: the root storage is never included)
        """
        files = []
        self._list(files, [], self.root, streams, storages)
        return files


    def _find(self, filename):
        """
        Returns directory entry of given filename. (openstream helper)
        Note: this method is case-insensitive.

        filename: path of stream in storage tree (except root entry), either:
            - a string using Unix path syntax, for example:
              'storage_1/storage_1.2/stream'
            - a list of storage filenames, path to the desired stream/storage.
              Example: ['storage_1', 'storage_1.2', 'stream']
        return: sid of requested filename
        raise IOError if file not found
        """

        # if filename is a string instead of a list, split it on slashes to
        # convert to a list:
        if isinstance(filename, basestring):
            filename = filename.split('/')
        # walk across storage tree, following given path:
        node = self.root
        for name in filename:
            for kid in node.kids:
                if kid.name.lower() == name.lower():
                    break
            else:
                raise IOError("file not found")
            node = kid
        return node.sid


    def openstream(self, filename):
        """
        Open a stream as a read-only file object (BytesIO).

        filename: path of stream in storage tree (except root entry), either:
            - a string using Unix path syntax, for example:
              'storage_1/storage_1.2/stream'
            - a list of storage filenames, path to the desired stream/storage.
              Example: ['storage_1', 'storage_1.2', 'stream']
        return: file object (read-only)
        raise IOError if filename not found, or if this is not a stream.
        """
        sid = self._find(filename)
        entry = self.direntries[sid]
        if entry.entry_type != STGTY_STREAM:
            raise IOError("this file is not a stream")
        return self._open(entry.isectStart, entry.size)


    def get_type(self, filename):
        """
        Test if given filename exists as a stream or a storage in the OLE
        container, and return its type.

        filename: path of stream in storage tree. (see openstream for syntax)
        return: False if object does not exist, its entry type (>0) otherwise:
            - STGTY_STREAM: a stream
            - STGTY_STORAGE: a storage
            - STGTY_ROOT: the root entry
        """
        try:
            sid = self._find(filename)
            entry = self.direntries[sid]
            return entry.entry_type
        except:
            return False


    def getmtime(self, filename):
        """
        Return modification time of a stream/storage.

        filename: path of stream/storage in storage tree. (see openstream for
        syntax)
        return: None if modification time is null, a python datetime object
        otherwise (UTC timezone)

        new in version 0.26
        """
        sid = self._find(filename)
        entry = self.direntries[sid]
        return entry.getmtime()


    def getctime(self, filename):
        """
        Return creation time of a stream/storage.

        filename: path of stream/storage in storage tree. (see openstream for
        syntax)
        return: None if creation time is null, a python datetime object
        otherwise (UTC timezone)

        new in version 0.26
        """
        sid = self._find(filename)
        entry = self.direntries[sid]
        return entry.getctime()


    def exists(self, filename):
        """
        Test if given filename exists as a stream or a storage in the OLE
        container.

        filename: path of stream in storage tree. (see openstream for syntax)
        return: True if object exist, else False.
        """
        try:
            sid = self._find(filename)
            return True
        except:
            return False


    def get_size(self, filename):
        """
        Return size of a stream in the OLE container, in bytes.

        filename: path of stream in storage tree (see openstream for syntax)
        return: size in bytes (long integer)
        raise: IOError if file not found, TypeError if this is not a stream.
        """
        sid = self._find(filename)
        entry = self.direntries[sid]
        if entry.entry_type != STGTY_STREAM:
            #TODO: Should it return zero instead of raising an exception ?
            raise TypeError('object is not an OLE stream')
        return entry.size


    def get_rootentry_name(self):
        """
        Return root entry name. Should usually be 'Root Entry' or 'R' in most
        implementations.
        """
        return self.root.name


    def getproperties(self, filename, convert_time=False, no_conversion=None):
        """
        Return properties described in substream.

        filename: path of stream in storage tree (see openstream for syntax)
        convert_time: bool, if True timestamps will be converted to Python datetime
        no_conversion: None or list of int, timestamps not to be converted
                       (for example total editing time is not a real timestamp)
        return: a dictionary of values indexed by id (integer)
        """
        # make sure no_conversion is a list, just to simplify code below:
        if no_conversion == None:
            no_conversion = []
        # stream path as a string to report exceptions:
        streampath = filename
        if not isinstance(streampath, str):
            streampath = '/'.join(streampath)

        fp = self.openstream(filename)

        data = {}

        try:
            # header
            s = fp.read(28)
            clsid = _clsid(s[8:24])

            # format id
            s = fp.read(20)
            fmtid = _clsid(s[:16])
            fp.seek(i32(s, 16))

            # get section
            s = b"****" + fp.read(i32(fp.read(4))-4)
            # number of properties:
            num_props = i32(s, 4)
        except BaseException as exc:
            # catch exception while parsing property header, and only raise
            # a DEFECT_INCORRECT then return an empty dict, because this is not
            # a fatal error when parsing the whole file
            msg = 'Error while parsing properties header in stream %s: %s' % (
                repr(streampath), exc)
            self._raise_defect(DEFECT_INCORRECT, msg, type(exc))
            return data

        for i in range(num_props):
            try:
                id = 0 # just in case of an exception
                id = i32(s, 8+i*8)
                offset = i32(s, 12+i*8)
                type = i32(s, offset)

                debug ('property id=%d: type=%d offset=%X' % (id, type, offset))

                # test for common types first (should perhaps use
                # a dictionary instead?)

                if type == VT_I2: # 16-bit signed integer
                    value = i16(s, offset+4)
                    if value >= 32768:
                        value = value - 65536
                elif type == VT_UI2: # 2-byte unsigned integer
                    value = i16(s, offset+4)
                elif type in (VT_I4, VT_INT, VT_ERROR):
                    # VT_I4: 32-bit signed integer
                    # VT_ERROR: HRESULT, similar to 32-bit signed integer,
                    # see http://msdn.microsoft.com/en-us/library/cc230330.aspx
                    value = i32(s, offset+4)
                elif type in (VT_UI4, VT_UINT): # 4-byte unsigned integer
                    value = i32(s, offset+4) # FIXME
                elif type in (VT_BSTR, VT_LPSTR):
                    # CodePageString, see http://msdn.microsoft.com/en-us/library/dd942354.aspx
                    # size is a 32 bits integer, including the null terminator, and
                    # possibly trailing or embedded null chars
                    #TODO: if codepage is unicode, the string should be converted as such
                    count = i32(s, offset+4)
                    value = s[offset+8:offset+8+count-1]
                    # remove all null chars:
                    value = value.replace(b'\x00', b'')
                elif type == VT_BLOB:
                    # binary large object (BLOB)
                    # see http://msdn.microsoft.com/en-us/library/dd942282.aspx
                    count = i32(s, offset+4)
                    value = s[offset+8:offset+8+count]
                elif type == VT_LPWSTR:
                    # UnicodeString
                    # see http://msdn.microsoft.com/en-us/library/dd942313.aspx
                    # "the string should NOT contain embedded or additional trailing
                    # null characters."
                    count = i32(s, offset+4)
                    value = _unicode(s[offset+8:offset+8+count*2])
                elif type == VT_FILETIME:
                    value = long(i32(s, offset+4)) + (long(i32(s, offset+8))<<32)
                    # FILETIME is a 64-bit int: "number of 100ns periods
                    # since Jan 1,1601".
                    if convert_time and id not in no_conversion:
                        debug('Converting property #%d to python datetime, value=%d=%fs'
                                %(id, value, float(value)/10000000))
                        # convert FILETIME to Python datetime.datetime
                        # inspired from http://code.activestate.com/recipes/511425-filetime-to-datetime/
                        _FILETIME_null_date = datetime.datetime(1601, 1, 1, 0, 0, 0)
                        debug('timedelta days=%d' % (value//(10*1000000*3600*24)))
                        value = _FILETIME_null_date + datetime.timedelta(microseconds=value//10)
                    else:
                        # legacy code kept for backward compatibility: returns a
                        # number of seconds since Jan 1,1601
                        value = value // 10000000 # seconds
                elif type == VT_UI1: # 1-byte unsigned integer
                    value = i8(s[offset+4])
                elif type == VT_CLSID:
                    value = _clsid(s[offset+4:offset+20])
                elif type == VT_CF:
                    # PropertyIdentifier or ClipboardData??
                    # see http://msdn.microsoft.com/en-us/library/dd941945.aspx
                    count = i32(s, offset+4)
                    value = s[offset+8:offset+8+count]
                elif type == VT_BOOL:
                    # VARIANT_BOOL, 16 bits bool, 0x0000=Fals, 0xFFFF=True
                    # see http://msdn.microsoft.com/en-us/library/cc237864.aspx
                    value = bool(i16(s, offset+4))
                else:
                    value = None # everything else yields "None"
                    debug ('property id=%d: type=%d not implemented in parser yet' % (id, type))

                # missing: VT_EMPTY, VT_NULL, VT_R4, VT_R8, VT_CY, VT_DATE,
                # VT_DECIMAL, VT_I1, VT_I8, VT_UI8,
                # see http://msdn.microsoft.com/en-us/library/dd942033.aspx

                # FIXME: add support for VT_VECTOR
                # VT_VECTOR is a 32 uint giving the number of items, followed by
                # the items in sequence. The VT_VECTOR value is combined with the
                # type of items, e.g. VT_VECTOR|VT_BSTR
                # see http://msdn.microsoft.com/en-us/library/dd942011.aspx

                #print("%08x" % id, repr(value), end=" ")
                #print("(%s)" % VT[i32(s, offset) & 0xFFF])

                data[id] = value
            except BaseException as exc:
                # catch exception while parsing each property, and only raise
                # a DEFECT_INCORRECT, because parsing can go on
                msg = 'Error while parsing property id %d in stream %s: %s' % (
                    id, repr(streampath), exc)
                self._raise_defect(DEFECT_INCORRECT, msg, type(exc))

        return data

    def get_metadata(self):
        """
        Parse standard properties streams, return an OleMetadata object
        containing all the available metadata.
        (also stored in the metadata attribute of the OleFileIO object)

        new in version 0.25
        """
        self.metadata = OleMetadata()
        self.metadata.parse_properties(self)
        return self.metadata

#
# --------------------------------------------------------------------
# This script can be used to dump the directory of any OLE2 structured
# storage file.

if __name__ == "__main__":

    import sys

    # [PL] display quick usage info if launched from command-line
    if len(sys.argv) <= 1:
        print(__doc__)
        print("""
Launched from command line, this script parses OLE files and prints info.

Usage: OleFileIO_PL.py [-d] [-c] <file> [file2 ...]

Options:
-d : debug mode (display a lot of debug information, for developers only)
-c : check all streams (for debugging purposes)
""")
        sys.exit()

    check_streams = False
    for filename in sys.argv[1:]:
##      try:
            # OPTIONS:
            if filename == '-d':
                # option to switch debug mode on:
                set_debug_mode(True)
                continue
            if filename == '-c':
                # option to switch check streams mode on:
                check_streams = True
                continue

            ole = OleFileIO(filename)#, raise_defects=DEFECT_INCORRECT)
            print("-" * 68)
            print(filename)
            print("-" * 68)
            ole.dumpdirectory()
            for streamname in ole.listdir():
                if streamname[-1][0] == "\005":
                    print(streamname, ": properties")
                    props = ole.getproperties(streamname, convert_time=True)
                    props = sorted(props.items())
                    for k, v in props:
                        #[PL]: avoid to display too large or binary values:
                        if isinstance(v, (basestring, bytes)):
                            if len(v) > 50:
                                v = v[:50]
                        if isinstance(v, bytes):
                            # quick and dirty binary check:
                            for c in (1,2,3,4,5,6,7,11,12,14,15,16,17,18,19,20,
                                21,22,23,24,25,26,27,28,29,30,31):
                                if c in bytearray(v):
                                    v = '(binary data)'
                                    break
                        print("   ", k, v)

            if check_streams:
                # Read all streams to check if there are errors:
                print('\nChecking streams...')
                for streamname in ole.listdir():
                    # print name using repr() to convert binary chars to \xNN:
                    print('-', repr('/'.join(streamname)),'-', end=' ')
                    st_type = ole.get_type(streamname)
                    if st_type == STGTY_STREAM:
                        print('size %d' % ole.get_size(streamname))
                        # just try to read stream in memory:
                        ole.openstream(streamname)
                    else:
                        print('NOT a stream : type=%d' % st_type)
                print()

##            for streamname in ole.listdir():
##                # print name using repr() to convert binary chars to \xNN:
##                print('-', repr('/'.join(streamname)),'-', end=' ')
##                print(ole.getmtime(streamname))
##            print()

            print('Modification/Creation times of all directory entries:')
            for entry in ole.direntries:
                if entry is not None:
                    print('- %s: mtime=%s ctime=%s' % (entry.name,
                        entry.getmtime(), entry.getctime()))
            print()

            # parse and display metadata:
            meta = ole.get_metadata()
            meta.dump()
            print()
            #[PL] Test a few new methods:
            root = ole.get_rootentry_name()
            print('Root entry name: "%s"' % root)
            if ole.exists('worddocument'):
                print("This is a Word document.")
                print("type of stream 'WordDocument':", ole.get_type('worddocument'))
                print("size :", ole.get_size('worddocument'))
                if ole.exists('macros/vba'):
                    print("This document may contain VBA macros.")

            # print parsing issues:
            print('\nNon-fatal issues raised during parsing:')
            if ole.parsing_issues:
                for exctype, msg in ole.parsing_issues:
                    print('- %s: %s' % (exctype.__name__, msg))
            else:
                print('None')
##      except IOError as v:
##          print("***", "cannot read", file, "-", v)

########NEW FILE########
__FILENAME__ = PaletteFile
#
# Python Imaging Library
# $Id$
#
# stuff to read simple, teragon-style palette files
#
# History:
#       97-08-23 fl     Created
#
# Copyright (c) Secret Labs AB 1997.
# Copyright (c) Fredrik Lundh 1997.
#
# See the README file for information on usage and redistribution.
#

from PIL._binary import o8

##
# File handler for Teragon-style palette files.

class PaletteFile:

    rawmode = "RGB"

    def __init__(self, fp):

        self.palette = [(i, i, i) for i in range(256)]

        while True:

            s = fp.readline()

            if not s:
                break
            if s[0:1] == b"#":
                continue
            if len(s) > 100:
                raise SyntaxError("bad palette file")

            v = [int(x) for x in s.split()]
            try:
                [i, r, g, b] = v
            except ValueError:
                [i, r] = v
                g = b = r

            if 0 <= i <= 255:
                self.palette[i] = o8(r) + o8(g) + o8(b)

        self.palette = b"".join(self.palette)


    def getpalette(self):

        return self.palette, self.rawmode

########NEW FILE########
__FILENAME__ = PalmImagePlugin
#
# The Python Imaging Library.
# $Id$
#

##
# Image plugin for Palm pixmap images (output only).
##

__version__ = "1.0"

from PIL import Image, ImageFile, _binary

_Palm8BitColormapValues = (
    ( 255, 255, 255 ), ( 255, 204, 255 ), ( 255, 153, 255 ), ( 255, 102, 255 ),
    ( 255,  51, 255 ), ( 255,   0, 255 ), ( 255, 255, 204 ), ( 255, 204, 204 ),
    ( 255, 153, 204 ), ( 255, 102, 204 ), ( 255,  51, 204 ), ( 255,   0, 204 ),
    ( 255, 255, 153 ), ( 255, 204, 153 ), ( 255, 153, 153 ), ( 255, 102, 153 ),
    ( 255,  51, 153 ), ( 255,   0, 153 ), ( 204, 255, 255 ), ( 204, 204, 255 ),
    ( 204, 153, 255 ), ( 204, 102, 255 ), ( 204,  51, 255 ), ( 204,   0, 255 ),
    ( 204, 255, 204 ), ( 204, 204, 204 ), ( 204, 153, 204 ), ( 204, 102, 204 ),
    ( 204,  51, 204 ), ( 204,   0, 204 ), ( 204, 255, 153 ), ( 204, 204, 153 ),
    ( 204, 153, 153 ), ( 204, 102, 153 ), ( 204,  51, 153 ), ( 204,   0, 153 ),
    ( 153, 255, 255 ), ( 153, 204, 255 ), ( 153, 153, 255 ), ( 153, 102, 255 ),
    ( 153,  51, 255 ), ( 153,   0, 255 ), ( 153, 255, 204 ), ( 153, 204, 204 ),
    ( 153, 153, 204 ), ( 153, 102, 204 ), ( 153,  51, 204 ), ( 153,   0, 204 ),
    ( 153, 255, 153 ), ( 153, 204, 153 ), ( 153, 153, 153 ), ( 153, 102, 153 ),
    ( 153,  51, 153 ), ( 153,   0, 153 ), ( 102, 255, 255 ), ( 102, 204, 255 ),
    ( 102, 153, 255 ), ( 102, 102, 255 ), ( 102,  51, 255 ), ( 102,   0, 255 ),
    ( 102, 255, 204 ), ( 102, 204, 204 ), ( 102, 153, 204 ), ( 102, 102, 204 ),
    ( 102,  51, 204 ), ( 102,   0, 204 ), ( 102, 255, 153 ), ( 102, 204, 153 ),
    ( 102, 153, 153 ), ( 102, 102, 153 ), ( 102,  51, 153 ), ( 102,   0, 153 ),
    (  51, 255, 255 ), (  51, 204, 255 ), (  51, 153, 255 ), (  51, 102, 255 ),
    (  51,  51, 255 ), (  51,   0, 255 ), (  51, 255, 204 ), (  51, 204, 204 ),
    (  51, 153, 204 ), (  51, 102, 204 ), (  51,  51, 204 ), (  51,   0, 204 ),
    (  51, 255, 153 ), (  51, 204, 153 ), (  51, 153, 153 ), (  51, 102, 153 ),
    (  51,  51, 153 ), (  51,   0, 153 ), (   0, 255, 255 ), (   0, 204, 255 ),
    (   0, 153, 255 ), (   0, 102, 255 ), (   0,  51, 255 ), (   0,   0, 255 ),
    (   0, 255, 204 ), (   0, 204, 204 ), (   0, 153, 204 ), (   0, 102, 204 ),
    (   0,  51, 204 ), (   0,   0, 204 ), (   0, 255, 153 ), (   0, 204, 153 ),
    (   0, 153, 153 ), (   0, 102, 153 ), (   0,  51, 153 ), (   0,   0, 153 ),
    ( 255, 255, 102 ), ( 255, 204, 102 ), ( 255, 153, 102 ), ( 255, 102, 102 ),
    ( 255,  51, 102 ), ( 255,   0, 102 ), ( 255, 255,  51 ), ( 255, 204,  51 ),
    ( 255, 153,  51 ), ( 255, 102,  51 ), ( 255,  51,  51 ), ( 255,   0,  51 ),
    ( 255, 255,   0 ), ( 255, 204,   0 ), ( 255, 153,   0 ), ( 255, 102,   0 ),
    ( 255,  51,   0 ), ( 255,   0,   0 ), ( 204, 255, 102 ), ( 204, 204, 102 ),
    ( 204, 153, 102 ), ( 204, 102, 102 ), ( 204,  51, 102 ), ( 204,   0, 102 ),
    ( 204, 255,  51 ), ( 204, 204,  51 ), ( 204, 153,  51 ), ( 204, 102,  51 ),
    ( 204,  51,  51 ), ( 204,   0,  51 ), ( 204, 255,   0 ), ( 204, 204,   0 ),
    ( 204, 153,   0 ), ( 204, 102,   0 ), ( 204,  51,   0 ), ( 204,   0,   0 ),
    ( 153, 255, 102 ), ( 153, 204, 102 ), ( 153, 153, 102 ), ( 153, 102, 102 ),
    ( 153,  51, 102 ), ( 153,   0, 102 ), ( 153, 255,  51 ), ( 153, 204,  51 ),
    ( 153, 153,  51 ), ( 153, 102,  51 ), ( 153,  51,  51 ), ( 153,   0,  51 ),
    ( 153, 255,   0 ), ( 153, 204,   0 ), ( 153, 153,   0 ), ( 153, 102,   0 ),
    ( 153,  51,   0 ), ( 153,   0,   0 ), ( 102, 255, 102 ), ( 102, 204, 102 ),
    ( 102, 153, 102 ), ( 102, 102, 102 ), ( 102,  51, 102 ), ( 102,   0, 102 ),
    ( 102, 255,  51 ), ( 102, 204,  51 ), ( 102, 153,  51 ), ( 102, 102,  51 ),
    ( 102,  51,  51 ), ( 102,   0,  51 ), ( 102, 255,   0 ), ( 102, 204,   0 ),
    ( 102, 153,   0 ), ( 102, 102,   0 ), ( 102,  51,   0 ), ( 102,   0,   0 ),
    (  51, 255, 102 ), (  51, 204, 102 ), (  51, 153, 102 ), (  51, 102, 102 ),
    (  51,  51, 102 ), (  51,   0, 102 ), (  51, 255,  51 ), (  51, 204,  51 ),
    (  51, 153,  51 ), (  51, 102,  51 ), (  51,  51,  51 ), (  51,   0,  51 ),
    (  51, 255,   0 ), (  51, 204,   0 ), (  51, 153,   0 ), (  51, 102,   0 ),
    (  51,  51,   0 ), (  51,   0,   0 ), (   0, 255, 102 ), (   0, 204, 102 ),
    (   0, 153, 102 ), (   0, 102, 102 ), (   0,  51, 102 ), (   0,   0, 102 ),
    (   0, 255,  51 ), (   0, 204,  51 ), (   0, 153,  51 ), (   0, 102,  51 ),
    (   0,  51,  51 ), (   0,   0,  51 ), (   0, 255,   0 ), (   0, 204,   0 ),
    (   0, 153,   0 ), (   0, 102,   0 ), (   0,  51,   0 ), (  17,  17,  17 ),
    (  34,  34,  34 ), (  68,  68,  68 ), (  85,  85,  85 ), ( 119, 119, 119 ),
    ( 136, 136, 136 ), ( 170, 170, 170 ), ( 187, 187, 187 ), ( 221, 221, 221 ),
    ( 238, 238, 238 ), ( 192, 192, 192 ), ( 128,   0,   0 ), ( 128,   0, 128 ),
    (   0, 128,   0 ), (   0, 128, 128 ), (   0,   0,   0 ), (   0,   0,   0 ),
    (   0,   0,   0 ), (   0,   0,   0 ), (   0,   0,   0 ), (   0,   0,   0 ),
    (   0,   0,   0 ), (   0,   0,   0 ), (   0,   0,   0 ), (   0,   0,   0 ),
    (   0,   0,   0 ), (   0,   0,   0 ), (   0,   0,   0 ), (   0,   0,   0 ),
    (   0,   0,   0 ), (   0,   0,   0 ), (   0,   0,   0 ), (   0,   0,   0 ),
    (   0,   0,   0 ), (   0,   0,   0 ), (   0,   0,   0 ), (   0,   0,   0 ),
    (   0,   0,   0 ), (   0,   0,   0 ), (   0,   0,   0 ), (   0,   0,   0 ))

# so build a prototype image to be used for palette resampling
def build_prototype_image():
    image = Image.new("L", (1,len(_Palm8BitColormapValues),))
    image.putdata(list(range(len(_Palm8BitColormapValues))))
    palettedata = ()
    for i in range(len(_Palm8BitColormapValues)):
        palettedata = palettedata + _Palm8BitColormapValues[i]
    for i in range(256 - len(_Palm8BitColormapValues)):
        palettedata = palettedata + (0, 0, 0)
    image.putpalette(palettedata)
    return image

Palm8BitColormapImage = build_prototype_image()

# OK, we now have in Palm8BitColormapImage, a "P"-mode image with the right palette
#
# --------------------------------------------------------------------

_FLAGS = {
    "custom-colormap": 0x4000,
    "is-compressed":   0x8000,
    "has-transparent": 0x2000,
    }

_COMPRESSION_TYPES = {
    "none":     0xFF,
    "rle":      0x01,
    "scanline": 0x00,
    }

o8 = _binary.o8
o16b = _binary.o16be

#
# --------------------------------------------------------------------

##
# (Internal) Image save plugin for the Palm format.

def _save(im, fp, filename, check=0):

    if im.mode == "P":

        # we assume this is a color Palm image with the standard colormap,
        # unless the "info" dict has a "custom-colormap" field

        rawmode = "P"
        bpp = 8
        version = 1

    elif im.mode == "L" and "bpp" in im.encoderinfo and im.encoderinfo["bpp"] in (1, 2, 4):

        # this is 8-bit grayscale, so we shift it to get the high-order bits, and invert it because
        # Palm does greyscale from white (0) to black (1)
        bpp = im.encoderinfo["bpp"]
        im = im.point(lambda x, shift=8-bpp, maxval=(1 << bpp)-1: maxval - (x >> shift))
        # we ignore the palette here
        im.mode = "P"
        rawmode = "P;" + str(bpp)
        version = 1

    elif im.mode == "L" and "bpp" in im.info and im.info["bpp"] in (1, 2, 4):

        # here we assume that even though the inherent mode is 8-bit grayscale, only
        # the lower bpp bits are significant.  We invert them to match the Palm.
        bpp = im.info["bpp"]
        im = im.point(lambda x, maxval=(1 << bpp)-1: maxval - (x & maxval))
        # we ignore the palette here
        im.mode = "P"
        rawmode = "P;" + str(bpp)
        version = 1

    elif im.mode == "1":

        # monochrome -- write it inverted, as is the Palm standard
        rawmode = "1;I"
        bpp = 1
        version = 0

    else:

        raise IOError("cannot write mode %s as Palm" % im.mode)

    if check:
        return check

    #
    # make sure image data is available
    im.load()

    # write header

    cols = im.size[0]
    rows = im.size[1]

    rowbytes = ((cols + (16//bpp - 1)) / (16 // bpp)) * 2;
    transparent_index = 0
    compression_type = _COMPRESSION_TYPES["none"]

    flags = 0;
    if im.mode == "P" and "custom-colormap" in im.info:
        flags = flags & _FLAGS["custom-colormap"]
        colormapsize = 4 * 256 + 2;
        colormapmode = im.palette.mode
        colormap = im.getdata().getpalette()
    else:
        colormapsize = 0

    if "offset" in im.info:
        offset = (rowbytes * rows + 16 + 3 + colormapsize) // 4;
    else:
        offset = 0

    fp.write(o16b(cols) + o16b(rows) + o16b(rowbytes) + o16b(flags))
    fp.write(o8(bpp))
    fp.write(o8(version))
    fp.write(o16b(offset))
    fp.write(o8(transparent_index))
    fp.write(o8(compression_type))
    fp.write(o16b(0))   # reserved by Palm

    # now write colormap if necessary

    if colormapsize > 0:
        fp.write(o16b(256))
        for i in range(256):
            fp.write(o8(i))
            if colormapmode == 'RGB':
                fp.write(o8(colormap[3 * i]) + o8(colormap[3 * i + 1]) + o8(colormap[3 * i + 2]))
            elif colormapmode == 'RGBA':
                fp.write(o8(colormap[4 * i]) + o8(colormap[4 * i + 1]) + o8(colormap[4 * i + 2]))

    # now convert data to raw form
    ImageFile._save(im, fp, [("raw", (0,0)+im.size, 0, (rawmode, rowbytes, 1))])

    fp.flush()


#
# --------------------------------------------------------------------

Image.register_save("Palm", _save)

Image.register_extension("Palm", ".palm")

Image.register_mime("Palm", "image/palm")

########NEW FILE########
__FILENAME__ = PcdImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# PCD file handling
#
# History:
#       96-05-10 fl     Created
#       96-05-27 fl     Added draft mode (128x192, 256x384)
#
# Copyright (c) Secret Labs AB 1997.
# Copyright (c) Fredrik Lundh 1996.
#
# See the README file for information on usage and redistribution.
#


__version__ = "0.1"


from PIL import Image, ImageFile, _binary

i8 = _binary.i8

##
# Image plugin for PhotoCD images.  This plugin only reads the 768x512
# image from the file; higher resolutions are encoded in a proprietary
# encoding.

class PcdImageFile(ImageFile.ImageFile):

    format = "PCD"
    format_description = "Kodak PhotoCD"

    def _open(self):

        # rough
        self.fp.seek(2048)
        s = self.fp.read(2048)

        if s[:4] != b"PCD_":
            raise SyntaxError("not a PCD file")

        orientation = i8(s[1538]) & 3
        if orientation == 1:
            self.tile_post_rotate = 90 # hack
        elif orientation == 3:
            self.tile_post_rotate = -90

        self.mode = "RGB"
        self.size = 768, 512 # FIXME: not correct for rotated images!
        self.tile = [("pcd", (0,0)+self.size, 96*2048, None)]

    def draft(self, mode, size):

        if len(self.tile) != 1:
            return

        d, e, o, a = self.tile[0]

        if size:
            scale = max(self.size[0] / size[0], self.size[1] / size[1])
            for s, o in [(4,0*2048), (2,0*2048), (1,96*2048)]:
                if scale >= s:
                    break
            # e = e[0], e[1], (e[2]-e[0]+s-1)/s+e[0], (e[3]-e[1]+s-1)/s+e[1]
            # self.size = ((self.size[0]+s-1)/s, (self.size[1]+s-1)/s)

        self.tile = [(d, e, o, a)]

        return self

#
# registry

Image.register_open("PCD", PcdImageFile)

Image.register_extension("PCD", ".pcd")

########NEW FILE########
__FILENAME__ = PcfFontFile
#
# THIS IS WORK IN PROGRESS
#
# The Python Imaging Library
# $Id$
#
# portable compiled font file parser
#
# history:
# 1997-08-19 fl   created
# 2003-09-13 fl   fixed loading of unicode fonts
#
# Copyright (c) 1997-2003 by Secret Labs AB.
# Copyright (c) 1997-2003 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#

from PIL import Image
from PIL import FontFile
from PIL import _binary

# --------------------------------------------------------------------
# declarations

PCF_MAGIC = 0x70636601 # "\x01fcp"

PCF_PROPERTIES = (1<<0)
PCF_ACCELERATORS = (1<<1)
PCF_METRICS = (1<<2)
PCF_BITMAPS = (1<<3)
PCF_INK_METRICS = (1<<4)
PCF_BDF_ENCODINGS = (1<<5)
PCF_SWIDTHS = (1<<6)
PCF_GLYPH_NAMES = (1<<7)
PCF_BDF_ACCELERATORS = (1<<8)

BYTES_PER_ROW = [
    lambda bits: ((bits+7)  >> 3),
    lambda bits: ((bits+15) >> 3) & ~1,
    lambda bits: ((bits+31) >> 3) & ~3,
    lambda bits: ((bits+63) >> 3) & ~7,
]

i8 = _binary.i8
l16 = _binary.i16le
l32 = _binary.i32le
b16 = _binary.i16be
b32 = _binary.i32be

def sz(s, o):
    return s[o:s.index(b"\0", o)]

##
# Font file plugin for the X11 PCF format.

class PcfFontFile(FontFile.FontFile):

    name = "name"

    def __init__(self, fp):

        magic = l32(fp.read(4))
        if magic != PCF_MAGIC:
            raise SyntaxError("not a PCF file")

        FontFile.FontFile.__init__(self)

        count = l32(fp.read(4))
        self.toc = {}
        for i in range(count):
            type = l32(fp.read(4))
            self.toc[type] = l32(fp.read(4)), l32(fp.read(4)), l32(fp.read(4))

        self.fp = fp

        self.info = self._load_properties()

        metrics = self._load_metrics()
        bitmaps = self._load_bitmaps(metrics)
        encoding = self._load_encoding()

        #
        # create glyph structure

        for ch in range(256):
            ix = encoding[ch]
            if ix is not None:
                x, y, l, r, w, a, d, f = metrics[ix]
                glyph = (w, 0), (l, d-y, x+l, d), (0, 0, x, y), bitmaps[ix]
                self.glyph[ch] = glyph

    def _getformat(self, tag):

        format, size, offset = self.toc[tag]

        fp = self.fp
        fp.seek(offset)

        format = l32(fp.read(4))

        if format & 4:
            i16, i32 = b16, b32
        else:
            i16, i32 = l16, l32

        return fp, format, i16, i32

    def _load_properties(self):

        #
        # font properties

        properties = {}

        fp, format, i16, i32 = self._getformat(PCF_PROPERTIES)

        nprops = i32(fp.read(4))

        # read property description
        p = []
        for i in range(nprops):
            p.append((i32(fp.read(4)), i8(fp.read(1)), i32(fp.read(4))))
        if nprops & 3:
            fp.seek(4 - (nprops & 3), 1) # pad

        data = fp.read(i32(fp.read(4)))

        for k, s, v in p:
            k = sz(data, k)
            if s:
                v = sz(data, v)
            properties[k] = v

        return properties

    def _load_metrics(self):

        #
        # font metrics

        metrics = []

        fp, format, i16, i32 = self._getformat(PCF_METRICS)

        append = metrics.append

        if (format & 0xff00) == 0x100:

            # "compressed" metrics
            for i in range(i16(fp.read(2))):
                left = i8(fp.read(1)) - 128
                right = i8(fp.read(1)) - 128
                width = i8(fp.read(1)) - 128
                ascent = i8(fp.read(1)) - 128
                descent = i8(fp.read(1)) - 128
                xsize = right - left
                ysize = ascent + descent
                append(
                    (xsize, ysize, left, right, width,
                     ascent, descent, 0)
                    )

        else:

            # "jumbo" metrics
            for i in range(i32(fp.read(4))):
                left = i16(fp.read(2))
                right = i16(fp.read(2))
                width = i16(fp.read(2))
                ascent = i16(fp.read(2))
                descent = i16(fp.read(2))
                attributes = i16(fp.read(2))
                xsize = right - left
                ysize = ascent + descent
                append(
                    (xsize, ysize, left, right, width,
                     ascent, descent, attributes)
                    )

        return metrics

    def _load_bitmaps(self, metrics):

        #
        # bitmap data

        bitmaps = []

        fp, format, i16, i32 = self._getformat(PCF_BITMAPS)

        nbitmaps = i32(fp.read(4))

        if nbitmaps != len(metrics):
            raise IOError("Wrong number of bitmaps")

        offsets = []
        for i in range(nbitmaps):
            offsets.append(i32(fp.read(4)))

        bitmapSizes = []
        for i in range(4):
            bitmapSizes.append(i32(fp.read(4)))

        byteorder = format & 4 # non-zero => MSB
        bitorder  = format & 8 # non-zero => MSB
        padindex  = format & 3

        bitmapsize = bitmapSizes[padindex]
        offsets.append(bitmapsize)

        data = fp.read(bitmapsize)

        pad  = BYTES_PER_ROW[padindex]
        mode = "1;R"
        if bitorder:
            mode = "1"

        for i in range(nbitmaps):
            x, y, l, r, w, a, d, f = metrics[i]
            b, e = offsets[i], offsets[i+1]
            bitmaps.append(
                Image.frombytes("1", (x, y), data[b:e], "raw", mode, pad(x))
                )

        return bitmaps

    def _load_encoding(self):

        # map character code to bitmap index
        encoding = [None] * 256

        fp, format, i16, i32 = self._getformat(PCF_BDF_ENCODINGS)

        firstCol, lastCol = i16(fp.read(2)), i16(fp.read(2))
        firstRow, lastRow = i16(fp.read(2)), i16(fp.read(2))

        default = i16(fp.read(2))

        nencoding = (lastCol - firstCol + 1) * (lastRow - firstRow + 1)

        for i in range(nencoding):
            encodingOffset = i16(fp.read(2))
            if encodingOffset != 0xFFFF:
                try:
                    encoding[i+firstCol] = encodingOffset
                except IndexError:
                    break # only load ISO-8859-1 glyphs

        return encoding

########NEW FILE########
__FILENAME__ = PcxImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# PCX file handling
#
# This format was originally used by ZSoft's popular PaintBrush
# program for the IBM PC.  It is also supported by many MS-DOS and
# Windows applications, including the Windows PaintBrush program in
# Windows 3.
#
# history:
# 1995-09-01 fl   Created
# 1996-05-20 fl   Fixed RGB support
# 1997-01-03 fl   Fixed 2-bit and 4-bit support
# 1999-02-03 fl   Fixed 8-bit support (broken in 1.0b1)
# 1999-02-07 fl   Added write support
# 2002-06-09 fl   Made 2-bit and 4-bit support a bit more robust
# 2002-07-30 fl   Seek from to current position, not beginning of file
# 2003-06-03 fl   Extract DPI settings (info["dpi"])
#
# Copyright (c) 1997-2003 by Secret Labs AB.
# Copyright (c) 1995-2003 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#

__version__ = "0.6"

from PIL import Image, ImageFile, ImagePalette, _binary

i8 = _binary.i8
i16 = _binary.i16le
o8 = _binary.o8

def _accept(prefix):
    return i8(prefix[0]) == 10 and i8(prefix[1]) in [0, 2, 3, 5]

##
# Image plugin for Paintbrush images.

class PcxImageFile(ImageFile.ImageFile):

    format = "PCX"
    format_description = "Paintbrush"

    def _open(self):

        # header
        s = self.fp.read(128)
        if not _accept(s):
            raise SyntaxError("not a PCX file")

        # image
        bbox = i16(s,4), i16(s,6), i16(s,8)+1, i16(s,10)+1
        if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            raise SyntaxError("bad PCX image size")
        if Image.DEBUG:
            print ("BBox: %s %s %s %s" % bbox)


        # format
        version = i8(s[1])
        bits = i8(s[3])
        planes = i8(s[65])
        stride = i16(s,66)
        if Image.DEBUG:
            print ("PCX version %s, bits %s, planes %s, stride %s" %
                   (version, bits, planes, stride))

        self.info["dpi"] = i16(s,12), i16(s,14)

        if bits == 1 and planes == 1:
            mode = rawmode = "1"

        elif bits == 1 and planes in (2, 4):
            mode = "P"
            rawmode = "P;%dL" % planes
            self.palette = ImagePalette.raw("RGB", s[16:64])

        elif version == 5 and bits == 8 and planes == 1:
            mode = rawmode = "L"
            # FIXME: hey, this doesn't work with the incremental loader !!!
            self.fp.seek(-769, 2)
            s = self.fp.read(769)
            if len(s) == 769 and i8(s[0]) == 12:
                # check if the palette is linear greyscale
                for i in range(256):
                    if s[i*3+1:i*3+4] != o8(i)*3:
                        mode = rawmode = "P"
                        break
                if mode == "P":
                    self.palette = ImagePalette.raw("RGB", s[1:])
            self.fp.seek(128)

        elif version == 5 and bits == 8 and planes == 3:
            mode = "RGB"
            rawmode = "RGB;L"

        else:
            raise IOError("unknown PCX mode")

        self.mode = mode
        self.size = bbox[2]-bbox[0], bbox[3]-bbox[1]

        bbox = (0, 0) + self.size
        if Image.DEBUG:
            print ("size: %sx%s" % self.size)
            
        self.tile = [("pcx", bbox, self.fp.tell(), (rawmode, planes * stride))]

# --------------------------------------------------------------------
# save PCX files

SAVE = {
    # mode: (version, bits, planes, raw mode)
    "1": (2, 1, 1, "1"),
    "L": (5, 8, 1, "L"),
    "P": (5, 8, 1, "P"),
    "RGB": (5, 8, 3, "RGB;L"),
}

o16 = _binary.o16le

def _save(im, fp, filename, check=0):

    try:
        version, bits, planes, rawmode = SAVE[im.mode]
    except KeyError:
        raise ValueError("Cannot save %s images as PCX" % im.mode)

    if check:
        return check

    # bytes per plane
    stride = (im.size[0] * bits + 7) // 8
    # stride should be even
    stride = stride + (stride % 2)
    # Stride needs to be kept in sync with the PcxEncode.c version.
    # Ideally it should be passed in in the state, but the bytes value
    # gets overwritten. 


    if Image.DEBUG:
        print ("PcxImagePlugin._save: xwidth: %d, bits: %d, stride: %d" % (
            im.size[0], bits, stride))

    # under windows, we could determine the current screen size with
    # "Image.core.display_mode()[1]", but I think that's overkill...

    screen = im.size

    dpi = 100, 100

    # PCX header
    fp.write(
        o8(10) + o8(version) + o8(1) + o8(bits) + o16(0) +
        o16(0) + o16(im.size[0]-1) + o16(im.size[1]-1) + o16(dpi[0]) +
        o16(dpi[1]) + b"\0"*24 + b"\xFF"*24 + b"\0" + o8(planes) +
        o16(stride) + o16(1) + o16(screen[0]) + o16(screen[1]) +
        b"\0"*54
        )

    assert fp.tell() == 128

    ImageFile._save(im, fp, [("pcx", (0,0)+im.size, 0,
                              (rawmode, bits*planes))])

    if im.mode == "P":
        # colour palette
        fp.write(o8(12))
        fp.write(im.im.getpalette("RGB", "RGB")) # 768 bytes
    elif im.mode == "L":
        # greyscale palette
        fp.write(o8(12))
        for i in range(256):
            fp.write(o8(i)*3)

# --------------------------------------------------------------------
# registry

Image.register_open("PCX", PcxImageFile, _accept)
Image.register_save("PCX", _save)

Image.register_extension("PCX", ".pcx")

########NEW FILE########
__FILENAME__ = PdfImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# PDF (Acrobat) file handling
#
# History:
# 1996-07-16 fl   Created
# 1997-01-18 fl   Fixed header
# 2004-02-21 fl   Fixes for 1/L/CMYK images, etc.
# 2004-02-24 fl   Fixes for 1 and P images.
#
# Copyright (c) 1997-2004 by Secret Labs AB.  All rights reserved.
# Copyright (c) 1996-1997 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#

##
# Image plugin for PDF images (output only).
##

__version__ = "0.4"

from PIL import Image, ImageFile
from PIL._binary import i8
import io


#
# --------------------------------------------------------------------

# object ids:
#  1. catalogue
#  2. pages
#  3. image
#  4. page
#  5. page contents

def _obj(fp, obj, **dict):
    fp.write("%d 0 obj\n" % obj)
    if dict:
        fp.write("<<\n")
        for k, v in dict.items():
            if v is not None:
                fp.write("/%s %s\n" % (k, v))
        fp.write(">>\n")


def _endobj(fp):
    fp.write("endobj\n")


##
# (Internal) Image save plugin for the PDF format.

def _save(im, fp, filename):
    resolution = im.encoderinfo.get("resolution", 72.0)

    #
    # make sure image data is available
    im.load()

    xref = [0]*(5+1)  # placeholders

    class TextWriter:
        def __init__(self, fp):
            self.fp = fp

        def __getattr__(self, name):
            return getattr(self.fp, name)

        def write(self, value):
            self.fp.write(value.encode('latin-1'))

    fp = TextWriter(fp)

    fp.write("%PDF-1.2\n")
    fp.write("% created by PIL PDF driver " + __version__ + "\n")

    #
    # Get image characteristics

    width, height = im.size

    # FIXME: Should replace ASCIIHexDecode with RunLengthDecode (packbits)
    # or LZWDecode (tiff/lzw compression).  Note that PDF 1.2 also supports
    # Flatedecode (zip compression).

    bits = 8
    params = None

    if im.mode == "1":
        filter = "/ASCIIHexDecode"
        colorspace = "/DeviceGray"
        procset = "/ImageB"  # grayscale
        bits = 1
    elif im.mode == "L":
        filter = "/DCTDecode"
        # params = "<< /Predictor 15 /Columns %d >>" % (width-2)
        colorspace = "/DeviceGray"
        procset = "/ImageB"  # grayscale
    elif im.mode == "P":
        filter = "/ASCIIHexDecode"
        colorspace = "[ /Indexed /DeviceRGB 255 <"
        palette = im.im.getpalette("RGB")
        for i in range(256):
            r = i8(palette[i*3])
            g = i8(palette[i*3+1])
            b = i8(palette[i*3+2])
            colorspace = colorspace + "%02x%02x%02x " % (r, g, b)
        colorspace = colorspace + "> ]"
        procset = "/ImageI"  # indexed color
    elif im.mode == "RGB":
        filter = "/DCTDecode"
        colorspace = "/DeviceRGB"
        procset = "/ImageC"  # color images
    elif im.mode == "CMYK":
        filter = "/DCTDecode"
        colorspace = "/DeviceCMYK"
        procset = "/ImageC"  # color images
    else:
        raise ValueError("cannot save mode %s" % im.mode)

    #
    # catalogue

    xref[1] = fp.tell()
    _obj(
        fp, 1,
        Type="/Catalog",
        Pages="2 0 R")
    _endobj(fp)

    #
    # pages

    xref[2] = fp.tell()
    _obj(
        fp, 2,
        Type="/Pages",
        Count=1,
        Kids="[4 0 R]")
    _endobj(fp)

    #
    # image

    op = io.BytesIO()

    if filter == "/ASCIIHexDecode":
        if bits == 1:
            # FIXME: the hex encoder doesn't support packed 1-bit
            # images; do things the hard way...
            data = im.tobytes("raw", "1")
            im = Image.new("L", (len(data), 1), None)
            im.putdata(data)
        ImageFile._save(im, op, [("hex", (0, 0)+im.size, 0, im.mode)])
    elif filter == "/DCTDecode":
        Image.SAVE["JPEG"](im, op, filename)
    elif filter == "/FlateDecode":
        ImageFile._save(im, op, [("zip", (0, 0)+im.size, 0, im.mode)])
    elif filter == "/RunLengthDecode":
        ImageFile._save(im, op, [("packbits", (0, 0)+im.size, 0, im.mode)])
    else:
        raise ValueError("unsupported PDF filter (%s)" % filter)

    xref[3] = fp.tell()
    _obj(
        fp, 3,
        Type="/XObject",
        Subtype="/Image",
        Width=width,  # * 72.0 / resolution,
        Height=height,  # * 72.0 / resolution,
        Length=len(op.getvalue()),
        Filter=filter,
        BitsPerComponent=bits,
        DecodeParams=params,
        ColorSpace=colorspace)

    fp.write("stream\n")
    fp.fp.write(op.getvalue())
    fp.write("\nendstream\n")

    _endobj(fp)

    #
    # page

    xref[4] = fp.tell()
    _obj(fp, 4)
    fp.write(
        "<<\n/Type /Page\n/Parent 2 0 R\n"
        "/Resources <<\n/ProcSet [ /PDF %s ]\n"
        "/XObject << /image 3 0 R >>\n>>\n"
        "/MediaBox [ 0 0 %d %d ]\n/Contents 5 0 R\n>>\n" % (
            procset,
            int(width * 72.0 / resolution),
            int(height * 72.0 / resolution)))
    _endobj(fp)

    #
    # page contents

    op = TextWriter(io.BytesIO())

    op.write(
        "q %d 0 0 %d 0 0 cm /image Do Q\n" % (
            int(width * 72.0 / resolution),
            int(height * 72.0 / resolution)))

    xref[5] = fp.tell()
    _obj(fp, 5, Length=len(op.fp.getvalue()))

    fp.write("stream\n")
    fp.fp.write(op.fp.getvalue())
    fp.write("\nendstream\n")

    _endobj(fp)

    #
    # trailer
    startxref = fp.tell()
    fp.write("xref\n0 %d\n0000000000 65535 f \n" % len(xref))
    for x in xref[1:]:
        fp.write("%010d 00000 n \n" % x)
    fp.write("trailer\n<<\n/Size %d\n/Root 1 0 R\n>>\n" % len(xref))
    fp.write("startxref\n%d\n%%%%EOF\n" % startxref)
    fp.flush()

#
# --------------------------------------------------------------------

Image.register_save("PDF", _save)

Image.register_extension("PDF", ".pdf")

Image.register_mime("PDF", "application/pdf")

########NEW FILE########
__FILENAME__ = PixarImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# PIXAR raster support for PIL
#
# history:
#       97-01-29 fl     Created
#
# notes:
#       This is incomplete; it is based on a few samples created with
#       Photoshop 2.5 and 3.0, and a summary description provided by
#       Greg Coats <gcoats@labiris.er.usgs.gov>.  Hopefully, "L" and
#       "RGBA" support will be added in future versions.
#
# Copyright (c) Secret Labs AB 1997.
# Copyright (c) Fredrik Lundh 1997.
#
# See the README file for information on usage and redistribution.
#

__version__ = "0.1"

from PIL import Image, ImageFile, _binary

#
# helpers

i16 = _binary.i16le
i32 = _binary.i32le

##
# Image plugin for PIXAR raster images.

class PixarImageFile(ImageFile.ImageFile):

    format = "PIXAR"
    format_description = "PIXAR raster image"

    def _open(self):

        # assuming a 4-byte magic label (FIXME: add "_accept" hook)
        s = self.fp.read(4)
        if s != b"\200\350\000\000":
            raise SyntaxError("not a PIXAR file")

        # read rest of header
        s = s + self.fp.read(508)

        self.size = i16(s[418:420]), i16(s[416:418])

        # get channel/depth descriptions
        mode = i16(s[424:426]), i16(s[426:428])

        if mode == (14, 2):
            self.mode = "RGB"
        # FIXME: to be continued...

        # create tile descriptor (assuming "dumped")
        self.tile = [("raw", (0,0)+self.size, 1024, (self.mode, 0, 1))]

#
# --------------------------------------------------------------------

Image.register_open("PIXAR", PixarImageFile)

#
# FIXME: what's the standard extension?

########NEW FILE########
__FILENAME__ = PngImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# PNG support code
#
# See "PNG (Portable Network Graphics) Specification, version 1.0;
# W3C Recommendation", 1996-10-01, Thomas Boutell (ed.).
#
# history:
# 1996-05-06 fl   Created (couldn't resist it)
# 1996-12-14 fl   Upgraded, added read and verify support (0.2)
# 1996-12-15 fl   Separate PNG stream parser
# 1996-12-29 fl   Added write support, added getchunks
# 1996-12-30 fl   Eliminated circular references in decoder (0.3)
# 1998-07-12 fl   Read/write 16-bit images as mode I (0.4)
# 2001-02-08 fl   Added transparency support (from Zircon) (0.5)
# 2001-04-16 fl   Don't close data source in "open" method (0.6)
# 2004-02-24 fl   Don't even pretend to support interlaced files (0.7)
# 2004-08-31 fl   Do basic sanity check on chunk identifiers (0.8)
# 2004-09-20 fl   Added PngInfo chunk container
# 2004-12-18 fl   Added DPI read support (based on code by Niki Spahiev)
# 2008-08-13 fl   Added tRNS support for RGB images
# 2009-03-06 fl   Support for preserving ICC profiles (by Florian Hoech)
# 2009-03-08 fl   Added zTXT support (from Lowell Alleman)
# 2009-03-29 fl   Read interlaced PNG files (from Conrado Porto Lopes Gouvua)
#
# Copyright (c) 1997-2009 by Secret Labs AB
# Copyright (c) 1996 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

from __future__ import print_function

__version__ = "0.9"

import re

from PIL import Image, ImageFile, ImagePalette, _binary
import zlib

i8 = _binary.i8
i16 = _binary.i16be
i32 = _binary.i32be

is_cid = re.compile(b"\w\w\w\w").match


_MAGIC = b"\211PNG\r\n\032\n"


_MODES = {
    # supported bits/color combinations, and corresponding modes/rawmodes
    (1, 0): ("1", "1"),
    (2, 0): ("L", "L;2"),
    (4, 0): ("L", "L;4"),
    (8, 0): ("L", "L"),
    (16,0): ("I", "I;16B"),
    (8, 2): ("RGB", "RGB"),
    (16,2): ("RGB", "RGB;16B"),
    (1, 3): ("P", "P;1"),
    (2, 3): ("P", "P;2"),
    (4, 3): ("P", "P;4"),
    (8, 3): ("P", "P"),
    (8, 4): ("LA", "LA"),
    (16,4): ("RGBA", "LA;16B"), # LA;16B->LA not yet available
    (8, 6): ("RGBA", "RGBA"),
    (16,6): ("RGBA", "RGBA;16B"),
}


_simple_palette = re.compile(b'^\xff+\x00\xff*$')

# --------------------------------------------------------------------
# Support classes.  Suitable for PNG and related formats like MNG etc.

class ChunkStream:

    def __init__(self, fp):

        self.fp = fp
        self.queue = []

        if not hasattr(Image.core, "crc32"):
            self.crc = self.crc_skip

    def read(self):
        "Fetch a new chunk. Returns header information."

        if self.queue:
            cid, pos, length = self.queue[-1]
            del self.queue[-1]
            self.fp.seek(pos)
        else:
            s = self.fp.read(8)
            cid = s[4:]
            pos = self.fp.tell()
            length = i32(s)

        if not is_cid(cid):
            raise SyntaxError("broken PNG file (chunk %s)" % repr(cid))

        return cid, pos, length

    def close(self):
        self.queue = self.crc = self.fp = None

    def push(self, cid, pos, length):

        self.queue.append((cid, pos, length))

    def call(self, cid, pos, length):
        "Call the appropriate chunk handler"

        if Image.DEBUG:
            print("STREAM", cid, pos, length)
        return getattr(self, "chunk_" + cid.decode('ascii'))(pos, length)

    def crc(self, cid, data):
        "Read and verify checksum"

        crc1 = Image.core.crc32(data, Image.core.crc32(cid))
        crc2 = i16(self.fp.read(2)), i16(self.fp.read(2))
        if crc1 != crc2:
            raise SyntaxError("broken PNG file"\
                "(bad header checksum in %s)" % cid)

    def crc_skip(self, cid, data):
        "Read checksum.  Used if the C module is not present"

        self.fp.read(4)

    def verify(self, endchunk = b"IEND"):

        # Simple approach; just calculate checksum for all remaining
        # blocks.  Must be called directly after open.

        cids = []

        while True:
            cid, pos, length = self.read()
            if cid == endchunk:
                break
            self.crc(cid, ImageFile._safe_read(self.fp, length))
            cids.append(cid)

        return cids


# --------------------------------------------------------------------
# PNG chunk container (for use with save(pnginfo=))

class PngInfo:

    def __init__(self):
        self.chunks = []

    def add(self, cid, data):
        self.chunks.append((cid, data))

    def add_text(self, key, value, zip=0):
        # The tEXt chunk stores latin-1 text
        if not isinstance(key, bytes):
            key = key.encode('latin-1', 'strict')

        if not isinstance(value, bytes):
            value = value.encode('latin-1', 'replace')

        if zip:
            import zlib
            self.add(b"zTXt", key + b"\0\0" + zlib.compress(value))
        else:
            self.add(b"tEXt", key + b"\0" + value)

# --------------------------------------------------------------------
# PNG image stream (IHDR/IEND)

class PngStream(ChunkStream):

    def __init__(self, fp):

        ChunkStream.__init__(self, fp)

        # local copies of Image attributes
        self.im_info = {}
        self.im_text = {}
        self.im_size = (0,0)
        self.im_mode = None
        self.im_tile = None
        self.im_palette = None

    def chunk_iCCP(self, pos, length):

        # ICC profile
        s = ImageFile._safe_read(self.fp, length)
        # according to PNG spec, the iCCP chunk contains:
        # Profile name  1-79 bytes (character string)
        # Null separator        1 byte (null character)
        # Compression method    1 byte (0)
        # Compressed profile    n bytes (zlib with deflate compression)
        i = s.find(b"\0")
        if Image.DEBUG:
            print("iCCP profile name", s[:i])
            print("Compression method", i8(s[i]))
        comp_method = i8(s[i])
        if comp_method != 0:
            raise SyntaxError("Unknown compression method %s in iCCP chunk" % comp_method)
        try:
            icc_profile = zlib.decompress(s[i+2:])
        except zlib.error:
            icc_profile = None # FIXME
        self.im_info["icc_profile"] = icc_profile
        return s

    def chunk_IHDR(self, pos, length):

        # image header
        s = ImageFile._safe_read(self.fp, length)
        self.im_size = i32(s), i32(s[4:])
        try:
            self.im_mode, self.im_rawmode = _MODES[(i8(s[8]), i8(s[9]))]
        except:
            pass
        if i8(s[12]):
            self.im_info["interlace"] = 1
        if i8(s[11]):
            raise SyntaxError("unknown filter category")
        return s

    def chunk_IDAT(self, pos, length):

        # image data
        self.im_tile = [("zip", (0,0)+self.im_size, pos, self.im_rawmode)]
        self.im_idat = length
        raise EOFError

    def chunk_IEND(self, pos, length):

        # end of PNG image
        raise EOFError

    def chunk_PLTE(self, pos, length):

        # palette
        s = ImageFile._safe_read(self.fp, length)
        if self.im_mode == "P":
            self.im_palette = "RGB", s
        return s

    def chunk_tRNS(self, pos, length):

        # transparency
        s = ImageFile._safe_read(self.fp, length)
        if self.im_mode == "P":
            if _simple_palette.match(s):
                i = s.find(b"\0")
                if i >= 0:
                    self.im_info["transparency"] = i
            else:
                self.im_info["transparency"] = s
        elif self.im_mode == "L":
            self.im_info["transparency"] = i16(s)
        elif self.im_mode == "RGB":
            self.im_info["transparency"] = i16(s), i16(s[2:]), i16(s[4:])
        return s

    def chunk_gAMA(self, pos, length):

        # gamma setting
        s = ImageFile._safe_read(self.fp, length)
        self.im_info["gamma"] = i32(s) / 100000.0
        return s

    def chunk_pHYs(self, pos, length):

        # pixels per unit
        s = ImageFile._safe_read(self.fp, length)
        px, py = i32(s), i32(s[4:])
        unit = i8(s[8])
        if unit == 1: # meter
            dpi = int(px * 0.0254 + 0.5), int(py * 0.0254 + 0.5)
            self.im_info["dpi"] = dpi
        elif unit == 0:
            self.im_info["aspect"] = px, py
        return s

    def chunk_tEXt(self, pos, length):

        # text
        s = ImageFile._safe_read(self.fp, length)
        try:
            k, v = s.split(b"\0", 1)
        except ValueError:
            k = s; v = b"" # fallback for broken tEXt tags
        if k:
            if bytes is not str:
                k = k.decode('latin-1', 'strict')
                v = v.decode('latin-1', 'replace')

            self.im_info[k] = self.im_text[k] = v
        return s

    def chunk_zTXt(self, pos, length):

        # compressed text
        s = ImageFile._safe_read(self.fp, length)
        try:
            k, v = s.split(b"\0", 1)
        except ValueError:
            k = s; v = b""
        if v:
            comp_method = i8(v[0])
        else:
            comp_method = 0
        if comp_method != 0:
            raise SyntaxError("Unknown compression method %s in zTXt chunk" % comp_method)
        import zlib
        try:
            v = zlib.decompress(v[1:])
        except zlib.error:
            v = b""

        if k:
            if bytes is not str:
                k = k.decode('latin-1', 'strict')
                v = v.decode('latin-1', 'replace')

            self.im_info[k] = self.im_text[k] = v
        return s

# --------------------------------------------------------------------
# PNG reader

def _accept(prefix):
    return prefix[:8] == _MAGIC

##
# Image plugin for PNG images.

class PngImageFile(ImageFile.ImageFile):

    format = "PNG"
    format_description = "Portable network graphics"

    def _open(self):

        if self.fp.read(8) != _MAGIC:
            raise SyntaxError("not a PNG file")

        #
        # Parse headers up to the first IDAT chunk

        self.png = PngStream(self.fp)

        while True:

            #
            # get next chunk

            cid, pos, length = self.png.read()

            try:
                s = self.png.call(cid, pos, length)
            except EOFError:
                break
            except AttributeError:
                if Image.DEBUG:
                    print(cid, pos, length, "(unknown)")
                s = ImageFile._safe_read(self.fp, length)

            self.png.crc(cid, s)

        #
        # Copy relevant attributes from the PngStream.  An alternative
        # would be to let the PngStream class modify these attributes
        # directly, but that introduces circular references which are
        # difficult to break if things go wrong in the decoder...
        # (believe me, I've tried ;-)

        self.mode = self.png.im_mode
        self.size = self.png.im_size
        self.info = self.png.im_info
        self.text = self.png.im_text # experimental
        self.tile = self.png.im_tile

        if self.png.im_palette:
            rawmode, data = self.png.im_palette
            self.palette = ImagePalette.raw(rawmode, data)

        self.__idat = length  # used by load_read()


    def verify(self):
        "Verify PNG file"

        if self.fp is None:
            raise RuntimeError("verify must be called directly after open")

        # back up to beginning of IDAT block
        self.fp.seek(self.tile[0][2] - 8)

        self.png.verify()
        self.png.close()

        self.fp = None

    def load_prepare(self):
        "internal: prepare to read PNG file"

        if self.info.get("interlace"):
            self.decoderconfig = self.decoderconfig + (1,)

        ImageFile.ImageFile.load_prepare(self)

    def load_read(self, read_bytes):
        "internal: read more image data"

        while self.__idat == 0:
            # end of chunk, skip forward to next one

            self.fp.read(4) # CRC

            cid, pos, length = self.png.read()

            if cid not in [b"IDAT", b"DDAT"]:
                self.png.push(cid, pos, length)
                return b""

            self.__idat = length  # empty chunks are allowed

        # read more data from this chunk
        if read_bytes <= 0:
            read_bytes = self.__idat
        else:
            read_bytes = min(read_bytes, self.__idat)

        self.__idat = self.__idat - read_bytes

        return self.fp.read(read_bytes)


    def load_end(self):
        "internal: finished reading image data"

        self.png.close()
        self.png = None


# --------------------------------------------------------------------
# PNG writer

o8 = _binary.o8
o16 = _binary.o16be
o32 = _binary.o32be

_OUTMODES = {
    # supported PIL modes, and corresponding rawmodes/bits/color combinations
    "1":   ("1",       b'\x01\x00'),
    "L;1": ("L;1",     b'\x01\x00'),
    "L;2": ("L;2",     b'\x02\x00'),
    "L;4": ("L;4",     b'\x04\x00'),
    "L":   ("L",       b'\x08\x00'),
    "LA":  ("LA",      b'\x08\x04'),
    "I":   ("I;16B",   b'\x10\x00'),
    "P;1": ("P;1",     b'\x01\x03'),
    "P;2": ("P;2",     b'\x02\x03'),
    "P;4": ("P;4",     b'\x04\x03'),
    "P":   ("P",       b'\x08\x03'),
    "RGB": ("RGB",     b'\x08\x02'),
    "RGBA":("RGBA",    b'\x08\x06'),
}

def putchunk(fp, cid, *data):
    "Write a PNG chunk (including CRC field)"

    data = b"".join(data)

    fp.write(o32(len(data)) + cid)
    fp.write(data)
    hi, lo = Image.core.crc32(data, Image.core.crc32(cid))
    fp.write(o16(hi) + o16(lo))

class _idat:
    # wrap output from the encoder in IDAT chunks

    def __init__(self, fp, chunk):
        self.fp = fp
        self.chunk = chunk
    def write(self, data):
        self.chunk(self.fp, b"IDAT", data)

def _save(im, fp, filename, chunk=putchunk, check=0):
    # save an image to disk (called by the save method)

    mode = im.mode

    if mode == "P":

        #
        # attempt to minimize storage requirements for palette images
        if "bits" in im.encoderinfo:
            # number of bits specified by user
            colors = 1 << im.encoderinfo["bits"]
        else:
            # check palette contents
            if im.palette:
                colors = max(min(len(im.palette.getdata()[1])//3, 256), 2)
            else:
                colors = 256

        if colors <= 2:
            bits = 1
        elif colors <= 4:
            bits = 2
        elif colors <= 16:
            bits = 4
        else:
            bits = 8
        if bits != 8:
            mode = "%s;%d" % (mode, bits)

    # encoder options
    if "dictionary" in im.encoderinfo:
        dictionary = im.encoderinfo["dictionary"]
    else:
        dictionary = b""

    im.encoderconfig = ("optimize" in im.encoderinfo,
        im.encoderinfo.get("compress_level", -1),
        im.encoderinfo.get("compress_type", -1),
        dictionary)

    # get the corresponding PNG mode
    try:
        rawmode, mode = _OUTMODES[mode]
    except KeyError:
        raise IOError("cannot write mode %s as PNG" % mode)

    if check:
        return check

    #
    # write minimal PNG file

    fp.write(_MAGIC)

    chunk(fp, b"IHDR",
          o32(im.size[0]), o32(im.size[1]),     #  0: size
          mode,                                 #  8: depth/type
          b'\0',                                # 10: compression
          b'\0',                                # 11: filter category
          b'\0')                                # 12: interlace flag

    if im.mode == "P":
        palette_byte_number = (2 ** bits) * 3
        palette_bytes = im.im.getpalette("RGB")[:palette_byte_number]
        while len(palette_bytes) < palette_byte_number:
            palette_bytes += b'\0'
        chunk(fp, b"PLTE", palette_bytes)

    transparency = im.encoderinfo.get('transparency',im.info.get('transparency', None))

    if transparency or transparency == 0:
        if im.mode == "P":
            # limit to actual palette size
            alpha_bytes = 2**bits
            if isinstance(transparency, bytes):
                chunk(fp, b"tRNS", transparency[:alpha_bytes])
            else:
                transparency = max(0, min(255, transparency))
                alpha = b'\xFF' * transparency + b'\0'
                chunk(fp, b"tRNS", alpha[:alpha_bytes])
        elif im.mode == "L":
            transparency = max(0, min(65535, transparency))
            chunk(fp, b"tRNS", o16(transparency))
        elif im.mode == "RGB":
            red, green, blue = transparency
            chunk(fp, b"tRNS", o16(red) + o16(green) + o16(blue))
        else:
            if "transparency" in im.encoderinfo:
                # don't bother with transparency if it's an RGBA
                # and it's in the info dict. It's probably just stale.
                raise IOError("cannot use transparency for this mode")
    else:
        if im.mode == "P" and im.im.getpalettemode() == "RGBA":
            alpha = im.im.getpalette("RGBA", "A")
            alpha_bytes = 2**bits
            chunk(fp, b"tRNS", alpha[:alpha_bytes])

    if 0:
        # FIXME: to be supported some day
        chunk(fp, b"gAMA", o32(int(gamma * 100000.0)))

    dpi = im.encoderinfo.get("dpi")
    if dpi:
        chunk(fp, b"pHYs",
              o32(int(dpi[0] / 0.0254 + 0.5)),
              o32(int(dpi[1] / 0.0254 + 0.5)),
              b'\x01')

    info = im.encoderinfo.get("pnginfo")
    if info:
        for cid, data in info.chunks:
            chunk(fp, cid, data)

    # ICC profile writing support -- 2008-06-06 Florian Hoech
    if im.info.get("icc_profile"):
        # ICC profile
        # according to PNG spec, the iCCP chunk contains:
        # Profile name  1-79 bytes (character string)
        # Null separator        1 byte (null character)
        # Compression method    1 byte (0)
        # Compressed profile    n bytes (zlib with deflate compression)
        name = b"ICC Profile"
        data = name + b"\0\0" + zlib.compress(im.info["icc_profile"])
        chunk(fp, b"iCCP", data)

    ImageFile._save(im, _idat(fp, chunk), [("zip", (0,0)+im.size, 0, rawmode)])

    chunk(fp, b"IEND", b"")

    try:
        fp.flush()
    except:
        pass


# --------------------------------------------------------------------
# PNG chunk converter

def getchunks(im, **params):
    """Return a list of PNG chunks representing this image."""

    class collector:
        data = []
        def write(self, data):
            pass
        def append(self, chunk):
            self.data.append(chunk)

    def append(fp, cid, *data):
        data = b"".join(data)
        hi, lo = Image.core.crc32(data, Image.core.crc32(cid))
        crc = o16(hi) + o16(lo)
        fp.append((cid, data, crc))

    fp = collector()

    try:
        im.encoderinfo = params
        _save(im, fp, None, append)
    finally:
        del im.encoderinfo

    return fp.data


# --------------------------------------------------------------------
# Registry

Image.register_open("PNG", PngImageFile, _accept)
Image.register_save("PNG", _save)

Image.register_extension("PNG", ".png")

Image.register_mime("PNG", "image/png")

########NEW FILE########
__FILENAME__ = PpmImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# PPM support for PIL
#
# History:
#       96-03-24 fl     Created
#       98-03-06 fl     Write RGBA images (as RGB, that is)
#
# Copyright (c) Secret Labs AB 1997-98.
# Copyright (c) Fredrik Lundh 1996.
#
# See the README file for information on usage and redistribution.
#


__version__ = "0.2"

import string

from PIL import Image, ImageFile

#
# --------------------------------------------------------------------

b_whitespace = string.whitespace
try:
    import locale
    locale_lang,locale_enc = locale.getlocale()
    if locale_enc is None:
        locale_lang,locale_enc = locale.getdefaultlocale() 
    b_whitespace = b_whitespace.decode(locale_enc)
except: pass
b_whitespace = b_whitespace.encode('ascii','ignore')

MODES = {
    # standard
    b"P4": "1",
    b"P5": "L",
    b"P6": "RGB",
    # extensions
    b"P0CMYK": "CMYK",
    # PIL extensions (for test purposes only)
    b"PyP": "P",
    b"PyRGBA": "RGBA",
    b"PyCMYK": "CMYK"
}

def _accept(prefix):
    return prefix[0:1] == b"P" and prefix[1] in b"0456y"

##
# Image plugin for PBM, PGM, and PPM images.

class PpmImageFile(ImageFile.ImageFile):

    format = "PPM"
    format_description = "Pbmplus image"

    def _token(self, s = b""):
        while True: # read until next whitespace
            c = self.fp.read(1)
            if not c or c in b_whitespace:
                break
            if c > b'\x79':
                raise ValueError("Expected ASCII value, found binary")
            s = s + c
            if (len(s) > 9):
                raise ValueError("Expected int, got > 9 digits")
        return s

    def _open(self):

        # check magic
        s = self.fp.read(1)
        if s != b"P":
            raise SyntaxError("not a PPM file")
        mode = MODES[self._token(s)]

        if mode == "1":
            self.mode = "1"
            rawmode = "1;I"
        else:
            self.mode = rawmode = mode

        for ix in range(3):
            while True:
                while True:
                    s = self.fp.read(1)
                    if s not in b_whitespace:
                        break
                if s != b"#":
                    break
                s = self.fp.readline()
            s = int(self._token(s))
            if ix == 0:
                xsize = s
            elif ix == 1:
                ysize = s
                if mode == "1":
                    break
            elif ix == 2:
                # maxgrey
                if s > 255:
                    if not mode == 'L':
                        raise ValueError("Too many colors for band: %s" %s)
                    if s < 2**16:
                        self.mode = 'I'
                        rawmode = 'I;16B'
                    else:
                        self.mode = 'I';
                        rawmode = 'I;32B'
                        
        self.size = xsize, ysize
        self.tile = [("raw",
                     (0, 0, xsize, ysize),
                     self.fp.tell(),
                     (rawmode, 0, 1))]

        # ALTERNATIVE: load via builtin debug function
        # self.im = Image.core.open_ppm(self.filename)
        # self.mode = self.im.mode
        # self.size = self.im.size

#
# --------------------------------------------------------------------

def _save(im, fp, filename):
    if im.mode == "1":
        rawmode, head = "1;I", b"P4"
    elif im.mode == "L":
        rawmode, head = "L", b"P5"
    elif im.mode == "I":
        if im.getextrema()[1] < 2**16:
            rawmode, head = "I;16B", b"P5"
        else:
            rawmode, head = "I;32B", b"P5"
    elif im.mode == "RGB":
        rawmode, head = "RGB", b"P6"
    elif im.mode == "RGBA":
        rawmode, head = "RGB", b"P6"
    else:
        raise IOError("cannot write mode %s as PPM" % im.mode)
    fp.write(head + ("\n%d %d\n" % im.size).encode('ascii'))
    if head == b"P6":
        fp.write(b"255\n")
    if head == b"P5":
        if rawmode == "L":
            fp.write(b"255\n")
        elif rawmode == "I;16B":
            fp.write(b"65535\n")
        elif rawmode == "I;32B":
            fp.write(b"2147483648\n")
    ImageFile._save(im, fp, [("raw", (0,0)+im.size, 0, (rawmode, 0, 1))])

    # ALTERNATIVE: save via builtin debug function
    # im._dump(filename)

#
# --------------------------------------------------------------------

Image.register_open("PPM", PpmImageFile, _accept)
Image.register_save("PPM", _save)

Image.register_extension("PPM", ".pbm")
Image.register_extension("PPM", ".pgm")
Image.register_extension("PPM", ".ppm")

########NEW FILE########
__FILENAME__ = PsdImagePlugin
#
# The Python Imaging Library
# $Id$
#
# Adobe PSD 2.5/3.0 file handling
#
# History:
# 1995-09-01 fl   Created
# 1997-01-03 fl   Read most PSD images
# 1997-01-18 fl   Fixed P and CMYK support
# 2001-10-21 fl   Added seek/tell support (for layers)
#
# Copyright (c) 1997-2001 by Secret Labs AB.
# Copyright (c) 1995-2001 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

__version__ = "0.4"

from PIL import Image, ImageFile, ImagePalette, _binary

MODES = {
    # (photoshop mode, bits) -> (pil mode, required channels)
    (0, 1): ("1", 1),
    (0, 8): ("L", 1),
    (1, 8): ("L", 1),
    (2, 8): ("P", 1),
    (3, 8): ("RGB", 3),
    (4, 8): ("CMYK", 4),
    (7, 8): ("L", 1), # FIXME: multilayer
    (8, 8): ("L", 1), # duotone
    (9, 8): ("LAB", 3)
}

#
# helpers

i8 = _binary.i8
i16 = _binary.i16be
i32 = _binary.i32be

# --------------------------------------------------------------------.
# read PSD images

def _accept(prefix):
    return prefix[:4] == b"8BPS"

##
# Image plugin for Photoshop images.

class PsdImageFile(ImageFile.ImageFile):

    format = "PSD"
    format_description = "Adobe Photoshop"

    def _open(self):

        read = self.fp.read

        #
        # header

        s = read(26)
        if s[:4] != b"8BPS" or i16(s[4:]) != 1:
            raise SyntaxError("not a PSD file")

        psd_bits = i16(s[22:])
        psd_channels = i16(s[12:])
        psd_mode = i16(s[24:])

        mode, channels = MODES[(psd_mode, psd_bits)]

        if channels > psd_channels:
            raise IOError("not enough channels")

        self.mode = mode
        self.size = i32(s[18:]), i32(s[14:])

        #
        # color mode data

        size = i32(read(4))
        if size:
            data = read(size)
            if mode == "P" and size == 768:
                self.palette = ImagePalette.raw("RGB;L", data)

        #
        # image resources

        self.resources = []

        size = i32(read(4))
        if size:
            # load resources
            end = self.fp.tell() + size
            while self.fp.tell() < end:
                signature = read(4)
                id = i16(read(2))
                name = read(i8(read(1)))
                if not (len(name) & 1):
                    read(1) # padding
                data = read(i32(read(4)))
                if (len(data) & 1):
                    read(1) # padding
                self.resources.append((id, name, data))
                if id == 1039: # ICC profile
                    self.info["icc_profile"] = data

        #
        # layer and mask information

        self.layers = []

        size = i32(read(4))
        if size:
            end = self.fp.tell() + size
            size = i32(read(4))
            if size:
                self.layers = _layerinfo(self.fp)
            self.fp.seek(end)

        #
        # image descriptor

        self.tile = _maketile(self.fp, mode, (0, 0) + self.size, channels)

        # keep the file open
        self._fp = self.fp
        self.frame = 0

    def seek(self, layer):
        # seek to given layer (1..max)
        if layer == self.frame:
            return
        try:
            if layer <= 0:
                raise IndexError
            name, mode, bbox, tile = self.layers[layer-1]
            self.mode = mode
            self.tile = tile
            self.frame = layer
            self.fp = self._fp
            return name, bbox
        except IndexError:
            raise EOFError("no such layer")

    def tell(self):
        # return layer number (0=image, 1..max=layers)
        return self.frame

    def load_prepare(self):
        # create image memory if necessary
        if not self.im or\
           self.im.mode != self.mode or self.im.size != self.size:
            self.im = Image.core.fill(self.mode, self.size, 0)
        # create palette (optional)
        if self.mode == "P":
            Image.Image.load(self)

def _layerinfo(file):
    # read layerinfo block
    layers = []
    read = file.read
    for i in range(abs(i16(read(2)))):

        # bounding box
        y0 = i32(read(4)); x0 = i32(read(4))
        y1 = i32(read(4)); x1 = i32(read(4))

        # image info
        info = []
        mode = []
        types = list(range(i16(read(2))))
        if len(types) > 4:
            continue

        for i in types:
            type = i16(read(2))

            if type == 65535:
                m = "A"
            else:
                m = "RGBA"[type]

            mode.append(m)
            size = i32(read(4))
            info.append((m, size))

        # figure out the image mode
        mode.sort()
        if mode == ["R"]:
            mode = "L"
        elif mode == ["B", "G", "R"]:
            mode = "RGB"
        elif mode == ["A", "B", "G", "R"]:
            mode = "RGBA"
        else:
            mode = None # unknown

        # skip over blend flags and extra information
        filler = read(12)
        name = ""
        size = i32(read(4))
        combined = 0
        if size:
            length = i32(read(4))
            if length:
                mask_y = i32(read(4)); mask_x = i32(read(4))
                mask_h = i32(read(4)) - mask_y; mask_w = i32(read(4)) - mask_x
                file.seek(length - 16, 1)
            combined += length + 4

            length = i32(read(4))
            if length:
                file.seek(length, 1)
            combined += length + 4

            length = i8(read(1))
            if length:
                # Don't know the proper encoding, Latin-1 should be a good guess
                name = read(length).decode('latin-1', 'replace')
            combined += length + 1

        file.seek(size - combined, 1)
        layers.append((name, mode, (x0, y0, x1, y1)))

    # get tiles
    i = 0
    for name, mode, bbox in layers:
        tile = []
        for m in mode:
            t = _maketile(file, m, bbox, 1)
            if t:
                tile.extend(t)
        layers[i] = name, mode, bbox, tile
        i = i + 1

    return layers

def _maketile(file, mode, bbox, channels):

    tile = None
    read = file.read

    compression = i16(read(2))

    xsize = bbox[2] - bbox[0]
    ysize = bbox[3] - bbox[1]

    offset = file.tell()

    if compression == 0:
        #
        # raw compression
        tile = []
        for channel in range(channels):
            layer = mode[channel]
            if mode == "CMYK":
                layer = layer + ";I"
            tile.append(("raw", bbox, offset, layer))
            offset = offset + xsize*ysize

    elif compression == 1:
        #
        # packbits compression
        i = 0
        tile = []
        bytecount = read(channels * ysize * 2)
        offset = file.tell()
        for channel in range(channels):
            layer = mode[channel]
            if mode == "CMYK":
                layer = layer + ";I"
            tile.append(
                ("packbits", bbox, offset, layer)
                )
            for y in range(ysize):
                offset = offset + i16(bytecount[i:i+2])
                i = i + 2

    file.seek(offset)

    if offset & 1:
        read(1) # padding

    return tile

# --------------------------------------------------------------------
# registry

Image.register_open("PSD", PsdImageFile, _accept)

Image.register_extension("PSD", ".psd")

########NEW FILE########
__FILENAME__ = PSDraw
#
# The Python Imaging Library
# $Id$
#
# simple postscript graphics interface
#
# History:
# 1996-04-20 fl   Created
# 1999-01-10 fl   Added gsave/grestore to image method
# 2005-05-04 fl   Fixed floating point issue in image (from Eric Etheridge)
#
# Copyright (c) 1997-2005 by Secret Labs AB.  All rights reserved.
# Copyright (c) 1996 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#

from __future__ import print_function

from PIL import EpsImagePlugin

##
# Simple Postscript graphics interface.

class PSDraw:
    """
    Sets up printing to the given file. If **file** is omitted,
    :py:attr:`sys.stdout` is assumed.
    """

    def __init__(self, fp=None):
        if not fp:
            import sys
            fp = sys.stdout
        self.fp = fp

    def begin_document(self, id = None):
        """Set up printing of a document. (Write Postscript DSC header.)"""
        # FIXME: incomplete
        self.fp.write("%!PS-Adobe-3.0\n"
                      "save\n"
                      "/showpage { } def\n"
                      "%%EndComments\n"
                      "%%BeginDocument\n")
        #self.fp.write(ERROR_PS) # debugging!
        self.fp.write(EDROFF_PS)
        self.fp.write(VDI_PS)
        self.fp.write("%%EndProlog\n")
        self.isofont = {}

    def end_document(self):
        """Ends printing. (Write Postscript DSC footer.)"""
        self.fp.write("%%EndDocument\n"
                      "restore showpage\n"
                      "%%End\n")
        if hasattr(self.fp, "flush"):
            self.fp.flush()

    def setfont(self, font, size):
        """
        Selects which font to use.

        :param font: A Postscript font name
        :param size: Size in points.
        """
        if font not in self.isofont:
            # reencode font
            self.fp.write("/PSDraw-%s ISOLatin1Encoding /%s E\n" %\
                          (font, font))
            self.isofont[font] = 1
        # rough
        self.fp.write("/F0 %d /PSDraw-%s F\n" % (size, font))

    def setink(self, ink):
        """
        .. warning::

            This has been in the PIL API for ages but was never implemented.
        """
        print("*** NOT YET IMPLEMENTED ***")

    def line(self, xy0, xy1):
        """
        Draws a line between the two points. Coordinates are given in
        Postscript point coordinates (72 points per inch, (0, 0) is the lower
        left corner of the page).
        """
        xy = xy0 + xy1
        self.fp.write("%d %d %d %d Vl\n" % xy)

    def rectangle(self, box):
        """
        Draws a rectangle.

        :param box: A 4-tuple of integers whose order and function is currently
                    undocumented.

                    Hint: the tuple is passed into this format string:

                    .. code-block:: python

                        %d %d M %d %d 0 Vr\n
        """
        self.fp.write("%d %d M %d %d 0 Vr\n" % box)

    def text(self, xy, text):
        """
        Draws text at the given position. You must use
        :py:meth:`~PIL.PSDraw.PSDraw.setfont` before calling this method.
        """
        text = "\\(".join(text.split("("))
        text = "\\)".join(text.split(")"))
        xy = xy + (text,)
        self.fp.write("%d %d M (%s) S\n" % xy)

    def image(self, box, im, dpi = None):
        """Draw a PIL image, centered in the given box."""
        # default resolution depends on mode
        if not dpi:
            if im.mode == "1":
                dpi = 200 # fax
            else:
                dpi = 100 # greyscale
        # image size (on paper)
        x = float(im.size[0] * 72) / dpi
        y = float(im.size[1] * 72) / dpi
        # max allowed size
        xmax = float(box[2] - box[0])
        ymax = float(box[3] - box[1])
        if x > xmax:
            y = y * xmax / x; x = xmax
        if y > ymax:
            x = x * ymax / y; y = ymax
        dx = (xmax - x) / 2 + box[0]
        dy = (ymax - y) / 2 + box[1]
        self.fp.write("gsave\n%f %f translate\n" % (dx, dy))
        if (x, y) != im.size:
            # EpsImagePlugin._save prints the image at (0,0,xsize,ysize)
            sx = x / im.size[0]
            sy = y / im.size[1]
            self.fp.write("%f %f scale\n" % (sx, sy))
        EpsImagePlugin._save(im, self.fp, None, 0)
        self.fp.write("\ngrestore\n")

# --------------------------------------------------------------------
# Postscript driver

#
# EDROFF.PS -- Postscript driver for Edroff 2
#
# History:
# 94-01-25 fl: created (edroff 2.04)
#
# Copyright (c) Fredrik Lundh 1994.
#

EDROFF_PS = """\
/S { show } bind def
/P { moveto show } bind def
/M { moveto } bind def
/X { 0 rmoveto } bind def
/Y { 0 exch rmoveto } bind def
/E {    findfont
        dup maxlength dict begin
        {
                1 index /FID ne { def } { pop pop } ifelse
        } forall
        /Encoding exch def
        dup /FontName exch def
        currentdict end definefont pop
} bind def
/F {    findfont exch scalefont dup setfont
        [ exch /setfont cvx ] cvx bind def
} bind def
"""

#
# VDI.PS -- Postscript driver for VDI meta commands
#
# History:
# 94-01-25 fl: created (edroff 2.04)
#
# Copyright (c) Fredrik Lundh 1994.
#

VDI_PS = """\
/Vm { moveto } bind def
/Va { newpath arcn stroke } bind def
/Vl { moveto lineto stroke } bind def
/Vc { newpath 0 360 arc closepath } bind def
/Vr {   exch dup 0 rlineto
        exch dup neg 0 exch rlineto
        exch neg 0 rlineto
        0 exch rlineto
        100 div setgray fill 0 setgray } bind def
/Tm matrix def
/Ve {   Tm currentmatrix pop
        translate scale newpath 0 0 .5 0 360 arc closepath
        Tm setmatrix
} bind def
/Vf { currentgray exch setgray fill setgray } bind def
"""

#
# ERROR.PS -- Error handler
#
# History:
# 89-11-21 fl: created (pslist 1.10)
#

ERROR_PS = """\
/landscape false def
/errorBUF 200 string def
/errorNL { currentpoint 10 sub exch pop 72 exch moveto } def
errordict begin /handleerror {
    initmatrix /Courier findfont 10 scalefont setfont
    newpath 72 720 moveto $error begin /newerror false def
    (PostScript Error) show errorNL errorNL
    (Error: ) show
        /errorname load errorBUF cvs show errorNL errorNL
    (Command: ) show
        /command load dup type /stringtype ne { errorBUF cvs } if show
        errorNL errorNL
    (VMstatus: ) show
        vmstatus errorBUF cvs show ( bytes available, ) show
        errorBUF cvs show ( bytes used at level ) show
        errorBUF cvs show errorNL errorNL
    (Operand stargck: ) show errorNL /ostargck load {
        dup type /stringtype ne { errorBUF cvs } if 72 0 rmoveto show errorNL
    } forall errorNL
    (Execution stargck: ) show errorNL /estargck load {
        dup type /stringtype ne { errorBUF cvs } if 72 0 rmoveto show errorNL
    } forall
    end showpage
} def end
"""

########NEW FILE########
__FILENAME__ = PyAccess
#
# The Python Imaging Library
# Pillow fork
#
# Python implementation of the PixelAccess Object
#
# Copyright (c) 1997-2009 by Secret Labs AB.  All rights reserved.
# Copyright (c) 1995-2009 by Fredrik Lundh.
# Copyright (c) 2013 Eric Soroos
#
# See the README file for information on usage and redistribution
#

# Notes:
#
#  * Implements the pixel access object following Access.
#  * Does not implement the line functions, as they don't appear to be used
#  * Taking only the tuple form, which is used from python.
#    * Fill.c uses the integer form, but it's still going to use the old Access.c implementation.
#

from __future__ import print_function

from cffi import FFI
import sys

DEBUG = 0
    
defs = """
struct Pixel_RGBA {
    unsigned char r,g,b,a;
};
struct Pixel_I16 {
    unsigned char l,r;
};
"""
ffi = FFI()
ffi.cdef(defs)


class PyAccess(object):
    
    def __init__(self, img, readonly = False):
        vals = dict(img.im.unsafe_ptrs)
        self.readonly = readonly
        self.image8 = ffi.cast('unsigned char **', vals['image8'])
        self.image32 = ffi.cast('int **', vals['image32'])
        self.image = ffi.cast('unsigned char **', vals['image'])
        self.xsize = vals['xsize']
        self.ysize = vals['ysize']
        
        if DEBUG:
            print (vals)
        self._post_init()

    def _post_init(): pass
        
    def __setitem__(self, xy, color):
        """
        Modifies the pixel at x,y. The color is given as a single
        numerical value for single band images, and a tuple for
        multi-band images

        :param xy: The pixel coordinate, given as (x, y).
        :param value: The pixel value.                
        """
        if self.readonly: raise ValueError('Attempt to putpixel a read only image') 
        (x,y) = self.check_xy(xy)
        return self.set_pixel(x,y,color)

    def __getitem__(self, xy):
        """
        Returns the pixel at x,y. The pixel is returned as a single
        value for single band images or a tuple for multiple band
        images

        :param xy: The pixel coordinate, given as (x, y).
        """
        
        (x,y) = self.check_xy(xy)
        return self.get_pixel(x,y)

    putpixel = __setitem__
    getpixel = __getitem__

    def check_xy(self, xy):
        (x,y) = xy
        if not (0 <= x < self.xsize and 0 <= y < self.ysize):
            raise ValueError('pixel location out of range')
        return xy

class _PyAccess32_2(PyAccess):
    """ PA, LA, stored in first and last bytes of a 32 bit word """
    def _post_init(self, *args, **kwargs):
        self.pixels = ffi.cast("struct Pixel_RGBA **", self.image32)
        
    def get_pixel(self, x,y):
        pixel = self.pixels[y][x]
        return (pixel.r, pixel.a)

    def set_pixel(self, x,y, color):
        pixel = self.pixels[y][x]
        # tuple
        pixel.r = min(color[0],255)
        pixel.a = min(color[1],255)
        
class _PyAccess32_3(PyAccess):
    """ RGB and friends, stored in the first three bytes of a 32 bit word """
    
    def _post_init(self, *args, **kwargs):
        self.pixels = ffi.cast("struct Pixel_RGBA **", self.image32)
        
    def get_pixel(self, x,y):
        pixel = self.pixels[y][x]
        return (pixel.r, pixel.g, pixel.b)

    def set_pixel(self, x,y, color):
        pixel = self.pixels[y][x]
        # tuple
        pixel.r = min(color[0],255)
        pixel.g = min(color[1],255)
        pixel.b = min(color[2],255)

class _PyAccess32_4(PyAccess):
    """ RGBA etc, all 4 bytes of a 32 bit word """
    def _post_init(self, *args, **kwargs):
        self.pixels = ffi.cast("struct Pixel_RGBA **", self.image32)
        
    def get_pixel(self, x,y):
        pixel = self.pixels[y][x]
        return (pixel.r, pixel.g, pixel.b, pixel.a)

    def set_pixel(self, x,y, color):
        pixel = self.pixels[y][x]
        # tuple
        pixel.r = min(color[0],255)
        pixel.g = min(color[1],255)
        pixel.b = min(color[2],255)
        pixel.a = min(color[3],255)

            
class _PyAccess8(PyAccess):
    """ 1, L, P, 8 bit images stored as uint8 """
    def _post_init(self, *args, **kwargs):
        self.pixels = self.image8
        
    def get_pixel(self, x,y):
        return self.pixels[y][x]

    def set_pixel(self, x,y, color):
        try:
            # integer
            self.pixels[y][x] = min(color,255)
        except:
            # tuple
            self.pixels[y][x] = min(color[0],255)

class _PyAccessI16_N(PyAccess):
    """ I;16 access, native bitendian without conversion """
    def _post_init(self, *args, **kwargs):
        self.pixels = ffi.cast('unsigned short **', self.image)

    def get_pixel(self, x,y):
        return self.pixels[y][x]

    def set_pixel(self, x,y, color):
        try:
            # integer
            self.pixels[y][x] = min(color, 65535)
        except:
            # tuple
            self.pixels[y][x] = min(color[0], 65535)

class _PyAccessI16_L(PyAccess):
    """ I;16L access, with conversion """
    def _post_init(self, *args, **kwargs):
        self.pixels = ffi.cast('struct Pixel_I16 **', self.image)

    def get_pixel(self, x,y):
        pixel = self.pixels[y][x]
        return pixel.l + pixel.r * 256

    def set_pixel(self, x,y, color):
        pixel = self.pixels[y][x]
        try:
            color = min(color, 65535)
        except:
            color = min(color[0], 65535)

        pixel.l = color & 0xFF
        pixel.r = color >> 8

class _PyAccessI16_B(PyAccess):
    """ I;16B access, with conversion """
    def _post_init(self, *args, **kwargs):
        self.pixels = ffi.cast('struct Pixel_I16 **', self.image)

    def get_pixel(self, x,y):
        pixel = self.pixels[y][x]
        return pixel.l *256  + pixel.r

    def set_pixel(self, x,y, color):
        pixel = self.pixels[y][x]
        try:
            color = min(color, 65535)
        except:
            color = min(color[0], 65535)

        pixel.l = color >> 8
        pixel.r = color & 0xFF

class _PyAccessI32_N(PyAccess):
    """ Signed Int32 access, native endian """
    def _post_init(self, *args, **kwargs):
        self.pixels = self.image32

    def get_pixel(self, x,y):
        return self.pixels[y][x]

    def set_pixel(self, x,y, color):
        self.pixels[y][x] = color

class _PyAccessI32_Swap(PyAccess):
    """ I;32L/B access, with byteswapping conversion """
    def _post_init(self, *args, **kwargs):
        self.pixels = self.image32

    def reverse(self, i):
        orig = ffi.new('int *', i)
        chars = ffi.cast('unsigned char *', orig)
        chars[0],chars[1],chars[2],chars[3] = chars[3], chars[2],chars[1],chars[0]
        return ffi.cast('int *', chars)[0]
        
    def get_pixel(self, x,y):
        return self.reverse(self.pixels[y][x])

    def set_pixel(self, x,y, color):
        self.pixels[y][x] = self.reverse(color)

class _PyAccessF(PyAccess):
    """ 32 bit float access """
    def _post_init(self, *args, **kwargs):
        self.pixels = ffi.cast('float **', self.image32)

    def get_pixel(self, x,y):
        return self.pixels[y][x]

    def set_pixel(self, x,y, color):
        try:
            # not a tuple
            self.pixels[y][x] = color
        except:
            # tuple
            self.pixels[y][x] = color[0]


mode_map = {'1': _PyAccess8,
            'L': _PyAccess8,
            'P': _PyAccess8,
            'LA': _PyAccess32_2,
            'PA': _PyAccess32_2,
            'RGB': _PyAccess32_3,
            'LAB': _PyAccess32_3,
            'YCbCr': _PyAccess32_3,
            'RGBA': _PyAccess32_4,
            'RGBa': _PyAccess32_4,
            'RGBX': _PyAccess32_4,
            'CMYK': _PyAccess32_4,
            'F': _PyAccessF,
            'I': _PyAccessI32_N,
            }

if sys.byteorder == 'little':
    mode_map['I;16'] = _PyAccessI16_N
    mode_map['I;16L'] = _PyAccessI16_N
    mode_map['I;16B'] = _PyAccessI16_B
    
    mode_map['I;32L'] = _PyAccessI32_N
    mode_map['I;32B'] = _PyAccessI32_Swap
else:
    mode_map['I;16'] = _PyAccessI16_L
    mode_map['I;16L'] = _PyAccessI16_L
    mode_map['I;16B'] = _PyAccessI16_N

    mode_map['I;32L'] = _PyAccessI32_Swap
    mode_map['I;32B'] = _PyAccessI32_N
    
def new(img, readonly=False):

    access_type = mode_map.get(img.mode, None)
    if not access_type:
        if DEBUG: print ("PyAccess Not Implemented: %s" % img.mode)
        return None
    if DEBUG: print ("New PyAccess: %s" % img.mode)
    return access_type(img, readonly)
    


########NEW FILE########
__FILENAME__ = SgiImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# SGI image file handling
#
# See "The SGI Image File Format (Draft version 0.97)", Paul Haeberli.
# <ftp://ftp.sgi.com/graphics/SGIIMAGESPEC>
#
# History:
# 1995-09-10 fl   Created
#
# Copyright (c) 2008 by Karsten Hiddemann.
# Copyright (c) 1997 by Secret Labs AB.
# Copyright (c) 1995 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#


__version__ = "0.2"


from PIL import Image, ImageFile, _binary

i8 = _binary.i8
i16 = _binary.i16be
i32 = _binary.i32be


def _accept(prefix):
    return i16(prefix) == 474

##
# Image plugin for SGI images.

class SgiImageFile(ImageFile.ImageFile):

    format = "SGI"
    format_description = "SGI Image File Format"

    def _open(self):

        # HEAD
        s = self.fp.read(512)
        if i16(s) != 474:
            raise SyntaxError("not an SGI image file")

        # relevant header entries
        compression = i8(s[2])

        # bytes, dimension, zsize
        layout = i8(s[3]), i16(s[4:]), i16(s[10:])

        # determine mode from bytes/zsize
        if layout == (1, 2, 1) or layout == (1, 1, 1):
            self.mode = "L"
        elif layout == (1, 3, 3):
            self.mode = "RGB"
        elif layout == (1, 3, 4):
            self.mode = "RGBA"
        else:
            raise SyntaxError("unsupported SGI image mode")

        # size
        self.size = i16(s[6:]), i16(s[8:])


        # decoder info
        if compression == 0:
            offset = 512
            pagesize = self.size[0]*self.size[1]*layout[0]
            self.tile = []
            for layer in self.mode:
                self.tile.append(("raw", (0,0)+self.size, offset, (layer,0,-1)))
                offset = offset + pagesize
        elif compression == 1:
            self.tile = [("sgi_rle", (0,0)+self.size, 512, (self.mode, 0, -1))]

#
# registry

Image.register_open("SGI", SgiImageFile, _accept)

Image.register_extension("SGI", ".bw")
Image.register_extension("SGI", ".rgb")
Image.register_extension("SGI", ".rgba")

Image.register_extension("SGI", ".sgi") # really?

########NEW FILE########
__FILENAME__ = SpiderImagePlugin
#
# The Python Imaging Library.
#
# SPIDER image file handling
#
# History:
# 2004-08-02    Created BB
# 2006-03-02    added save method
# 2006-03-13    added support for stack images
#
# Copyright (c) 2004 by Health Research Inc. (HRI) RENSSELAER, NY 12144.
# Copyright (c) 2004 by William Baxter.
# Copyright (c) 2004 by Secret Labs AB.
# Copyright (c) 2004 by Fredrik Lundh.
#

##
# Image plugin for the Spider image format.  This format is is used
# by the SPIDER software, in processing image data from electron
# microscopy and tomography.
##

#
# SpiderImagePlugin.py
#
# The Spider image format is used by SPIDER software, in processing
# image data from electron microscopy and tomography.
#
# Spider home page:
# http://www.wadsworth.org/spider_doc/spider/docs/spider.html
#
# Details about the Spider image format:
# http://www.wadsworth.org/spider_doc/spider/docs/image_doc.html
#

from __future__ import print_function

from PIL import Image, ImageFile
import os, struct, sys

def isInt(f):
    try:
        i = int(f)
        if f-i == 0: return 1
        else:        return 0
    except:
        return 0

iforms = [1,3,-11,-12,-21,-22]

# There is no magic number to identify Spider files, so just check a
# series of header locations to see if they have reasonable values.
# Returns no.of bytes in the header, if it is a valid Spider header,
# otherwise returns 0

def isSpiderHeader(t):
    h = (99,) + t   # add 1 value so can use spider header index start=1
    # header values 1,2,5,12,13,22,23 should be integers
    for i in [1,2,5,12,13,22,23]:
        if not isInt(h[i]): return 0
    # check iform
    iform = int(h[5])
    if not iform in iforms: return 0
    # check other header values
    labrec = int(h[13])   # no. records in file header
    labbyt = int(h[22])   # total no. of bytes in header
    lenbyt = int(h[23])   # record length in bytes
    #print "labrec = %d, labbyt = %d, lenbyt = %d" % (labrec,labbyt,lenbyt)
    if labbyt != (labrec * lenbyt): return 0
    # looks like a valid header
    return labbyt

def isSpiderImage(filename):
    fp = open(filename,'rb')
    f = fp.read(92)   # read 23 * 4 bytes
    fp.close()
    bigendian = 1
    t = struct.unpack('>23f',f)    # try big-endian first
    hdrlen = isSpiderHeader(t)
    if hdrlen == 0:
        bigendian = 0
        t = struct.unpack('<23f',f)  # little-endian
        hdrlen = isSpiderHeader(t)
    return hdrlen


class SpiderImageFile(ImageFile.ImageFile):

    format = "SPIDER"
    format_description = "Spider 2D image"

    def _open(self):
        # check header
        n = 27 * 4  # read 27 float values
        f = self.fp.read(n)

        try:
            self.bigendian = 1
            t = struct.unpack('>27f',f)    # try big-endian first
            hdrlen = isSpiderHeader(t)
            if hdrlen == 0:
                self.bigendian = 0
                t = struct.unpack('<27f',f)  # little-endian
                hdrlen = isSpiderHeader(t)
            if hdrlen == 0:
                raise SyntaxError("not a valid Spider file")
        except struct.error:
            raise SyntaxError("not a valid Spider file")

        h = (99,) + t   # add 1 value : spider header index starts at 1
        iform = int(h[5])
        if iform != 1:
            raise SyntaxError("not a Spider 2D image")

        self.size = int(h[12]), int(h[2]) # size in pixels (width, height)
        self.istack = int(h[24])
        self.imgnumber = int(h[27])

        if self.istack == 0 and self.imgnumber == 0:
            # stk=0, img=0: a regular 2D image
            offset = hdrlen
            self.nimages = 1
        elif self.istack > 0 and self.imgnumber == 0:
            # stk>0, img=0: Opening the stack for the first time
            self.imgbytes = int(h[12]) * int(h[2]) * 4
            self.hdrlen = hdrlen
            self.nimages = int(h[26])
            # Point to the first image in the stack
            offset = hdrlen * 2
            self.imgnumber = 1
        elif self.istack == 0 and self.imgnumber > 0:
            # stk=0, img>0: an image within the stack
            offset = hdrlen + self.stkoffset
            self.istack = 2  # So Image knows it's still a stack
        else:
            raise SyntaxError("inconsistent stack header values")

        if self.bigendian:
            self.rawmode = "F;32BF"
        else:
            self.rawmode = "F;32F"
        self.mode = "F"

        self.tile = [("raw", (0, 0) + self.size, offset,
                    (self.rawmode, 0, 1))]
        self.__fp = self.fp # FIXME: hack

    # 1st image index is zero (although SPIDER imgnumber starts at 1)
    def tell(self):
        if self.imgnumber < 1:
            return 0
        else:
            return self.imgnumber - 1

    def seek(self, frame):
        if self.istack == 0:
            return
        if frame >= self.nimages:
            raise EOFError("attempt to seek past end of file")
        self.stkoffset = self.hdrlen + frame * (self.hdrlen + self.imgbytes)
        self.fp = self.__fp
        self.fp.seek(self.stkoffset)
        self._open()

    # returns a byte image after rescaling to 0..255
    def convert2byte(self, depth=255):
        (min, max) = self.getextrema()
        m = 1
        if max != min:
            m = depth / (max-min)
        b = -m * min
        return self.point(lambda i, m=m, b=b: i * m + b).convert("L")

    # returns a ImageTk.PhotoImage object, after rescaling to 0..255
    def tkPhotoImage(self):
        from PIL import ImageTk
        return ImageTk.PhotoImage(self.convert2byte(), palette=256)

# --------------------------------------------------------------------
# Image series

# given a list of filenames, return a list of images
def loadImageSeries(filelist=None):
    " create a list of Image.images for use in montage "
    if filelist is None or len(filelist) < 1:
        return

    imglist = []
    for img in filelist:
        if not os.path.exists(img):
            print("unable to find %s" % img)
            continue
        try:
            im = Image.open(img).convert2byte()
        except:
            if not isSpiderImage(img):
                print(img + " is not a Spider image file")
            continue
        im.info['filename'] = img
        imglist.append(im)
    return imglist

# --------------------------------------------------------------------
# For saving images in Spider format

def makeSpiderHeader(im):
    nsam,nrow = im.size
    lenbyt = nsam * 4  # There are labrec records in the header
    labrec = 1024 / lenbyt
    if 1024%lenbyt != 0: labrec += 1
    labbyt = labrec * lenbyt
    hdr = []
    nvalues = labbyt / 4
    for i in range(nvalues):
        hdr.append(0.0)

    if len(hdr) < 23:
        return []

    # NB these are Fortran indices
    hdr[1]  = 1.0           # nslice (=1 for an image)
    hdr[2]  = float(nrow)   # number of rows per slice
    hdr[5]  = 1.0           # iform for 2D image
    hdr[12] = float(nsam)   # number of pixels per line
    hdr[13] = float(labrec) # number of records in file header
    hdr[22] = float(labbyt) # total number of bytes in header
    hdr[23] = float(lenbyt) # record length in bytes

    # adjust for Fortran indexing
    hdr = hdr[1:]
    hdr.append(0.0)
    # pack binary data into a string
    hdrstr = []
    for v in hdr:
        hdrstr.append(struct.pack('f',v))
    return hdrstr

def _save(im, fp, filename):
    if im.mode[0] != "F":
        im = im.convert('F')

    hdr = makeSpiderHeader(im)
    if len(hdr) < 256:
        raise IOError("Error creating Spider header")

    # write the SPIDER header
    try:
        fp = open(filename, 'wb')
    except:
        raise IOError("Unable to open %s for writing" % filename)
    fp.writelines(hdr)

    rawmode = "F;32NF"  #32-bit native floating point
    ImageFile._save(im, fp, [("raw", (0,0)+im.size, 0, (rawmode,0,1))])

    fp.close()

def _save_spider(im, fp, filename):
    # get the filename extension and register it with Image
    fn, ext = os.path.splitext(filename)
    Image.register_extension("SPIDER", ext)
    _save(im, fp, filename)

# --------------------------------------------------------------------

Image.register_open("SPIDER", SpiderImageFile)
Image.register_save("SPIDER", _save_spider)

if __name__ == "__main__":

    if not sys.argv[1:]:
        print("Syntax: python SpiderImagePlugin.py Spiderimage [outfile]")
        sys.exit()

    filename = sys.argv[1]
    if not isSpiderImage(filename):
        print("input image must be in Spider format")
        sys.exit()

    outfile = ""
    if len(sys.argv[1:]) > 1:
        outfile = sys.argv[2]

    im = Image.open(filename)
    print("image: " + str(im))
    print("format: " + str(im.format))
    print("size: " + str(im.size))
    print("mode: " + str(im.mode))
    print("max, min: ", end=' ')
    print(im.getextrema())

    if outfile != "":
        # perform some image operation
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
        print("saving a flipped version of %s as %s " % (os.path.basename(filename), outfile))
        im.save(outfile, "SPIDER")

########NEW FILE########
__FILENAME__ = SunImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# Sun image file handling
#
# History:
# 1995-09-10 fl   Created
# 1996-05-28 fl   Fixed 32-bit alignment
# 1998-12-29 fl   Import ImagePalette module
# 2001-12-18 fl   Fixed palette loading (from Jean-Claude Rimbault)
#
# Copyright (c) 1997-2001 by Secret Labs AB
# Copyright (c) 1995-1996 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#


__version__ = "0.3"


from PIL import Image, ImageFile, ImagePalette, _binary

i16 = _binary.i16be
i32 = _binary.i32be


def _accept(prefix):
    return i32(prefix) == 0x59a66a95

##
# Image plugin for Sun raster files.

class SunImageFile(ImageFile.ImageFile):

    format = "SUN"
    format_description = "Sun Raster File"

    def _open(self):

        # HEAD
        s = self.fp.read(32)
        if i32(s) != 0x59a66a95:
            raise SyntaxError("not an SUN raster file")

        offset = 32

        self.size = i32(s[4:8]), i32(s[8:12])

        depth = i32(s[12:16])
        if depth == 1:
            self.mode, rawmode = "1", "1;I"
        elif depth == 8:
            self.mode = rawmode = "L"
        elif depth == 24:
            self.mode, rawmode = "RGB", "BGR"
        else:
            raise SyntaxError("unsupported mode")

        compression = i32(s[20:24])

        if i32(s[24:28]) != 0:
            length = i32(s[28:32])
            offset = offset + length
            self.palette = ImagePalette.raw("RGB;L", self.fp.read(length))
            if self.mode == "L":
                self.mode = rawmode = "P"

        stride = (((self.size[0] * depth + 7) // 8) + 3) & (~3)

        if compression == 1:
            self.tile = [("raw", (0,0)+self.size, offset, (rawmode, stride))]
        elif compression == 2:
            self.tile = [("sun_rle", (0,0)+self.size, offset, rawmode)]

#
# registry

Image.register_open("SUN", SunImageFile, _accept)

Image.register_extension("SUN", ".ras")

########NEW FILE########
__FILENAME__ = TarIO
#
# The Python Imaging Library.
# $Id$
#
# read files from within a tar file
#
# History:
# 95-06-18 fl   Created
# 96-05-28 fl   Open files in binary mode
#
# Copyright (c) Secret Labs AB 1997.
# Copyright (c) Fredrik Lundh 1995-96.
#
# See the README file for information on usage and redistribution.
#

from PIL import ContainerIO

##
# A file object that provides read access to a given member of a TAR
# file.

class TarIO(ContainerIO.ContainerIO):

    ##
    # Create file object.
    #
    # @param tarfile Name of TAR file.
    # @param file Name of member file.

    def __init__(self, tarfile, file):

        fh = open(tarfile, "rb")

        while True:

            s = fh.read(512)
            if len(s) != 512:
                raise IOError("unexpected end of tar file")

            name = s[:100].decode('utf-8')
            i = name.find('\0')
            if i == 0:
                raise IOError("cannot find subfile")
            if i > 0:
                name = name[:i]

            size = int(s[124:135], 8)

            if file == name:
                break

            fh.seek((size + 511) & (~511), 1)

        # Open region
        ContainerIO.ContainerIO.__init__(self, fh, fh.tell(), size)

########NEW FILE########
__FILENAME__ = tests
import unittest


class PillowTests(unittest.TestCase):
    """
    Can we start moving the test suite here?
    """

    def test_suite_should_move_here(self):
        """
        Great idea!
        """
        assert True is True


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = TgaImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# TGA file handling
#
# History:
# 95-09-01 fl   created (reads 24-bit files only)
# 97-01-04 fl   support more TGA versions, including compressed images
# 98-07-04 fl   fixed orientation and alpha layer bugs
# 98-09-11 fl   fixed orientation for runlength decoder
#
# Copyright (c) Secret Labs AB 1997-98.
# Copyright (c) Fredrik Lundh 1995-97.
#
# See the README file for information on usage and redistribution.
#


__version__ = "0.3"

from PIL import Image, ImageFile, ImagePalette, _binary


#
# --------------------------------------------------------------------
# Read RGA file

i8 = _binary.i8
i16 = _binary.i16le
i32 = _binary.i32le


MODES = {
    # map imagetype/depth to rawmode
    (1, 8):  "P",
    (3, 1):  "1",
    (3, 8):  "L",
    (2, 16): "BGR;5",
    (2, 24): "BGR",
    (2, 32): "BGRA",
}


def _accept(prefix):
    return prefix[0:1] == b"\0"

##
# Image plugin for Targa files.

class TgaImageFile(ImageFile.ImageFile):

    format = "TGA"
    format_description = "Targa"

    def _open(self):

        # process header
        s = self.fp.read(18)

        id = i8(s[0])

        colormaptype = i8(s[1])
        imagetype = i8(s[2])

        depth = i8(s[16])

        flags = i8(s[17])

        self.size = i16(s[12:]), i16(s[14:])

        # validate header fields
        if id != 0 or colormaptype not in (0, 1) or\
           self.size[0] <= 0 or self.size[1] <= 0 or\
           depth not in (1, 8, 16, 24, 32):
            raise SyntaxError("not a TGA file")

        # image mode
        if imagetype in (3, 11):
            self.mode = "L"
            if depth == 1:
                self.mode = "1" # ???
        elif imagetype in (1, 9):
            self.mode = "P"
        elif imagetype in (2, 10):
            self.mode = "RGB"
            if depth == 32:
                self.mode = "RGBA"
        else:
            raise SyntaxError("unknown TGA mode")

        # orientation
        orientation = flags & 0x30
        if orientation == 0x20:
            orientation = 1
        elif not orientation:
            orientation = -1
        else:
            raise SyntaxError("unknown TGA orientation")

        self.info["orientation"] = orientation

        if imagetype & 8:
            self.info["compression"] = "tga_rle"

        if colormaptype:
            # read palette
            start, size, mapdepth = i16(s[3:]), i16(s[5:]), i16(s[7:])
            if mapdepth == 16:
                self.palette = ImagePalette.raw("BGR;16",
                    b"\0"*2*start + self.fp.read(2*size))
            elif mapdepth == 24:
                self.palette = ImagePalette.raw("BGR",
                    b"\0"*3*start + self.fp.read(3*size))
            elif mapdepth == 32:
                self.palette = ImagePalette.raw("BGRA",
                    b"\0"*4*start + self.fp.read(4*size))

        # setup tile descriptor
        try:
            rawmode = MODES[(imagetype&7, depth)]
            if imagetype & 8:
                # compressed
                self.tile = [("tga_rle", (0, 0)+self.size,
                              self.fp.tell(), (rawmode, orientation, depth))]
            else:
                self.tile = [("raw", (0, 0)+self.size,
                              self.fp.tell(), (rawmode, 0, orientation))]
        except KeyError:
            pass # cannot decode

#
# --------------------------------------------------------------------
# Write TGA file

o8 = _binary.o8
o16 = _binary.o16le
o32 = _binary.o32le

SAVE = {
    "1": ("1", 1, 0, 3),
    "L": ("L", 8, 0, 3),
    "P": ("P", 8, 1, 1),
    "RGB": ("BGR", 24, 0, 2),
    "RGBA": ("BGRA", 32, 0, 2),
}

def _save(im, fp, filename, check=0):

    try:
        rawmode, bits, colormaptype, imagetype = SAVE[im.mode]
    except KeyError:
        raise IOError("cannot write mode %s as TGA" % im.mode)

    if check:
        return check

    if colormaptype:
        colormapfirst, colormaplength, colormapentry = 0, 256, 24
    else:
        colormapfirst, colormaplength, colormapentry = 0, 0, 0

    if im.mode == "RGBA":
        flags = 8
    else:
        flags = 0

    orientation = im.info.get("orientation", -1)
    if orientation > 0:
        flags = flags | 0x20

    fp.write(b"\000" +
             o8(colormaptype) +
             o8(imagetype) +
             o16(colormapfirst) +
             o16(colormaplength) +
             o8(colormapentry) +
             o16(0) +
             o16(0) +
             o16(im.size[0]) +
             o16(im.size[1]) +
             o8(bits) +
             o8(flags))

    if colormaptype:
        fp.write(im.im.getpalette("RGB", "BGR"))

    ImageFile._save(im, fp, [("raw", (0,0)+im.size, 0, (rawmode, 0, orientation))])

#
# --------------------------------------------------------------------
# Registry

Image.register_open("TGA", TgaImageFile, _accept)
Image.register_save("TGA", _save)

Image.register_extension("TGA", ".tga")

########NEW FILE########
__FILENAME__ = TiffImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# TIFF file handling
#
# TIFF is a flexible, if somewhat aged, image file format originally
# defined by Aldus.  Although TIFF supports a wide variety of pixel
# layouts and compression methods, the name doesn't really stand for
# "thousands of incompatible file formats," it just feels that way.
#
# To read TIFF data from a stream, the stream must be seekable.  For
# progressive decoding, make sure to use TIFF files where the tag
# directory is placed first in the file.
#
# History:
# 1995-09-01 fl   Created
# 1996-05-04 fl   Handle JPEGTABLES tag
# 1996-05-18 fl   Fixed COLORMAP support
# 1997-01-05 fl   Fixed PREDICTOR support
# 1997-08-27 fl   Added support for rational tags (from Perry Stoll)
# 1998-01-10 fl   Fixed seek/tell (from Jan Blom)
# 1998-07-15 fl   Use private names for internal variables
# 1999-06-13 fl   Rewritten for PIL 1.0 (1.0)
# 2000-10-11 fl   Additional fixes for Python 2.0 (1.1)
# 2001-04-17 fl   Fixed rewind support (seek to frame 0) (1.2)
# 2001-05-12 fl   Added write support for more tags (from Greg Couch) (1.3)
# 2001-12-18 fl   Added workaround for broken Matrox library
# 2002-01-18 fl   Don't mess up if photometric tag is missing (D. Alan Stewart)
# 2003-05-19 fl   Check FILLORDER tag
# 2003-09-26 fl   Added RGBa support
# 2004-02-24 fl   Added DPI support; fixed rational write support
# 2005-02-07 fl   Added workaround for broken Corel Draw 10 files
# 2006-01-09 fl   Added support for float/double tags (from Russell Nelson)
#
# Copyright (c) 1997-2006 by Secret Labs AB.  All rights reserved.
# Copyright (c) 1995-1997 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

from __future__ import print_function

__version__ = "1.3.5"

from PIL import Image, ImageFile
from PIL import ImagePalette
from PIL import _binary
from PIL._util import isStringType

import warnings
import array, sys
import collections
import itertools
import os

# Set these to true to force use of libtiff for reading or writing. 
READ_LIBTIFF = False
WRITE_LIBTIFF= False

II = b"II" # little-endian (intel-style)
MM = b"MM" # big-endian (motorola-style)

i8 = _binary.i8
o8 = _binary.o8

if sys.byteorder == "little":
    native_prefix = II
else:
    native_prefix = MM

#
# --------------------------------------------------------------------
# Read TIFF files

il16 = _binary.i16le
il32 = _binary.i32le
ol16 = _binary.o16le
ol32 = _binary.o32le

ib16 = _binary.i16be
ib32 = _binary.i32be
ob16 = _binary.o16be
ob32 = _binary.o32be

# a few tag names, just to make the code below a bit more readable
IMAGEWIDTH = 256
IMAGELENGTH = 257
BITSPERSAMPLE = 258
COMPRESSION = 259
PHOTOMETRIC_INTERPRETATION = 262
FILLORDER = 266
IMAGEDESCRIPTION = 270
STRIPOFFSETS = 273
SAMPLESPERPIXEL = 277
ROWSPERSTRIP = 278
STRIPBYTECOUNTS = 279
X_RESOLUTION = 282
Y_RESOLUTION = 283
PLANAR_CONFIGURATION = 284
RESOLUTION_UNIT = 296
SOFTWARE = 305
DATE_TIME = 306
ARTIST = 315
PREDICTOR = 317
COLORMAP = 320
TILEOFFSETS = 324
EXTRASAMPLES = 338
SAMPLEFORMAT = 339
JPEGTABLES = 347
COPYRIGHT = 33432
IPTC_NAA_CHUNK = 33723 # newsphoto properties
PHOTOSHOP_CHUNK = 34377 # photoshop properties
ICCPROFILE = 34675
EXIFIFD = 34665
XMP = 700

# https://github.com/fiji/ImageJA/blob/master/src/main/java/ij/io/TiffDecoder.java
IMAGEJ_META_DATA_BYTE_COUNTS = 50838
IMAGEJ_META_DATA = 50839

COMPRESSION_INFO = {
    # Compression => pil compression name
    1: "raw",
    2: "tiff_ccitt",
    3: "group3",
    4: "group4",
    5: "tiff_lzw",
    6: "tiff_jpeg", # obsolete
    7: "jpeg",
    8: "tiff_adobe_deflate",
    32771: "tiff_raw_16", # 16-bit padding
    32773: "packbits",
    32809: "tiff_thunderscan",
    32946: "tiff_deflate",
    34676: "tiff_sgilog",
    34677: "tiff_sgilog24",
}

COMPRESSION_INFO_REV = dict([(v,k) for (k,v) in COMPRESSION_INFO.items()])

OPEN_INFO = {
    # (ByteOrder, PhotoInterpretation, SampleFormat, FillOrder, BitsPerSample,
    #  ExtraSamples) => mode, rawmode
    (II, 0, 1, 1, (1,), ()): ("1", "1;I"),
    (II, 0, 1, 2, (1,), ()): ("1", "1;IR"),
    (II, 0, 1, 1, (8,), ()): ("L", "L;I"),
    (II, 0, 1, 2, (8,), ()): ("L", "L;IR"),
    (II, 0, 3, 1, (32,), ()): ("F", "F;32F"),
    (II, 1, 1, 1, (1,), ()): ("1", "1"),
    (II, 1, 1, 2, (1,), ()): ("1", "1;R"),
    (II, 1, 1, 1, (8,), ()): ("L", "L"),
    (II, 1, 1, 1, (8,8), (2,)): ("LA", "LA"),
    (II, 1, 1, 2, (8,), ()): ("L", "L;R"),
    (II, 1, 1, 1, (12,), ()): ("I;16", "I;12"),
    (II, 1, 1, 1, (16,), ()): ("I;16", "I;16"),
    (II, 1, 2, 1, (16,), ()): ("I;16S", "I;16S"),
    (II, 1, 1, 1, (32,), ()): ("I", "I;32N"),
    (II, 1, 2, 1, (32,), ()): ("I", "I;32S"),
    (II, 1, 3, 1, (32,), ()): ("F", "F;32F"),
    (II, 2, 1, 1, (8,8,8), ()): ("RGB", "RGB"),
    (II, 2, 1, 2, (8,8,8), ()): ("RGB", "RGB;R"),
    (II, 2, 1, 1, (8,8,8,8), ()): ("RGBA", "RGBA"),  # missing ExtraSamples
    (II, 2, 1, 1, (8,8,8,8), (0,)): ("RGBX", "RGBX"),
    (II, 2, 1, 1, (8,8,8,8), (1,)): ("RGBA", "RGBa"),
    (II, 2, 1, 1, (8,8,8,8), (2,)): ("RGBA", "RGBA"),
    (II, 2, 1, 1, (8,8,8,8), (999,)): ("RGBA", "RGBA"), # corel draw 10
    (II, 3, 1, 1, (1,), ()): ("P", "P;1"),
    (II, 3, 1, 2, (1,), ()): ("P", "P;1R"),
    (II, 3, 1, 1, (2,), ()): ("P", "P;2"),
    (II, 3, 1, 2, (2,), ()): ("P", "P;2R"),
    (II, 3, 1, 1, (4,), ()): ("P", "P;4"),
    (II, 3, 1, 2, (4,), ()): ("P", "P;4R"),
    (II, 3, 1, 1, (8,), ()): ("P", "P"),
    (II, 3, 1, 1, (8,8), (2,)): ("PA", "PA"),
    (II, 3, 1, 2, (8,), ()): ("P", "P;R"),
    (II, 5, 1, 1, (8,8,8,8), ()): ("CMYK", "CMYK"),
    (II, 6, 1, 1, (8,8,8), ()): ("YCbCr", "YCbCr"),
    (II, 8, 1, 1, (8,8,8), ()): ("LAB", "LAB"),

    (MM, 0, 1, 1, (1,), ()): ("1", "1;I"),
    (MM, 0, 1, 2, (1,), ()): ("1", "1;IR"),
    (MM, 0, 1, 1, (8,), ()): ("L", "L;I"),
    (MM, 0, 1, 2, (8,), ()): ("L", "L;IR"),
    (MM, 1, 1, 1, (1,), ()): ("1", "1"),
    (MM, 1, 1, 2, (1,), ()): ("1", "1;R"),
    (MM, 1, 1, 1, (8,), ()): ("L", "L"),
    (MM, 1, 1, 1, (8,8), (2,)): ("LA", "LA"),
    (MM, 1, 1, 2, (8,), ()): ("L", "L;R"),
    (MM, 1, 1, 1, (16,), ()): ("I;16B", "I;16B"),
    (MM, 1, 2, 1, (16,), ()): ("I;16BS", "I;16BS"),
    (MM, 1, 2, 1, (32,), ()): ("I;32BS", "I;32BS"),
    (MM, 1, 3, 1, (32,), ()): ("F", "F;32BF"),
    (MM, 2, 1, 1, (8,8,8), ()): ("RGB", "RGB"),
    (MM, 2, 1, 2, (8,8,8), ()): ("RGB", "RGB;R"),
    (MM, 2, 1, 1, (8,8,8,8), (0,)): ("RGBX", "RGBX"),
    (MM, 2, 1, 1, (8,8,8,8), (1,)): ("RGBA", "RGBa"),
    (MM, 2, 1, 1, (8,8,8,8), (2,)): ("RGBA", "RGBA"),
    (MM, 2, 1, 1, (8,8,8,8), (999,)): ("RGBA", "RGBA"), # corel draw 10
    (MM, 3, 1, 1, (1,), ()): ("P", "P;1"),
    (MM, 3, 1, 2, (1,), ()): ("P", "P;1R"),
    (MM, 3, 1, 1, (2,), ()): ("P", "P;2"),
    (MM, 3, 1, 2, (2,), ()): ("P", "P;2R"),
    (MM, 3, 1, 1, (4,), ()): ("P", "P;4"),
    (MM, 3, 1, 2, (4,), ()): ("P", "P;4R"),
    (MM, 3, 1, 1, (8,), ()): ("P", "P"),
    (MM, 3, 1, 1, (8,8), (2,)): ("PA", "PA"),
    (MM, 3, 1, 2, (8,), ()): ("P", "P;R"),
    (MM, 5, 1, 1, (8,8,8,8), ()): ("CMYK", "CMYK"),
    (MM, 6, 1, 1, (8,8,8), ()): ("YCbCr", "YCbCr"),
    (MM, 8, 1, 1, (8,8,8), ()): ("LAB", "LAB"),

}

PREFIXES = [b"MM\000\052", b"II\052\000", b"II\xBC\000"]

def _accept(prefix):
    return prefix[:4] in PREFIXES

##
# Wrapper for TIFF IFDs.

class ImageFileDirectory(collections.MutableMapping):
    """ This class represents a TIFF tag directory.  To speed things
        up, we don't decode tags unless they're asked for.

        Exposes a dictionary interface of the tags in the directory
        ImageFileDirectory[key] = value
        value = ImageFileDirectory[key]

        Also contains a dictionary of tag types as read from the tiff
        image file, 'ImageFileDirectory.tagtype'


        Data Structures:
        'public'
        * self.tagtype = {} Key: numerical tiff tag number
                            Value: integer corresponding to the data type from
                            `TiffTags.TYPES`

        'internal'            
        * self.tags = {}  Key: numerical tiff tag number
                          Value: Decoded data, Generally a tuple.
                            * If set from __setval__ -- always a tuple
                            * Numeric types -- always a tuple
                            * String type -- not a tuple, returned as string
                            * Undefined data -- not a tuple, returned as bytes
                            * Byte -- not a tuple, returned as byte.
        * self.tagdata = {} Key: numerical tiff tag number
                            Value: undecoded byte string from file


        Tags will be found in either self.tags or self.tagdata, but
        not both. The union of the two should contain all the tags
        from the Tiff image file.  External classes shouldn't
        reference these unless they're really sure what they're doing.
        """

    def __init__(self, prefix=II):
        """
        :prefix: 'II'|'MM'  tiff endianness
        """
        self.prefix = prefix[:2]
        if self.prefix == MM:
            self.i16, self.i32 = ib16, ib32
            self.o16, self.o32 = ob16, ob32
        elif self.prefix == II:
            self.i16, self.i32 = il16, il32
            self.o16, self.o32 = ol16, ol32
        else:
            raise SyntaxError("not a TIFF IFD")
        self.reset()

    def reset(self):
        #: Tags is an incomplete dictionary of the tags of the image.
        #: For a complete dictionary, use the as_dict method.
        self.tags = {}
        self.tagdata = {}
        self.tagtype = {} # added 2008-06-05 by Florian Hoech
        self.next = None

    def __str__(self):
        return str(self.as_dict())

    def as_dict(self):
        """Return a dictionary of the image's tags."""
        return dict(self.items())

    def named(self):
        """Returns the complete tag dictionary, with named tags where posible."""
        from PIL import TiffTags
        result = {}
        for tag_code, value in self.items():
            tag_name = TiffTags.TAGS.get(tag_code, tag_code)
            result[tag_name] = value
        return result


    # dictionary API

    def __len__(self):
        return len(self.tagdata) + len(self.tags)

    def __getitem__(self, tag):
        try:
            return self.tags[tag]
        except KeyError:
            data = self.tagdata[tag] # unpack on the fly
            type = self.tagtype[tag]
            size, handler = self.load_dispatch[type]
            self.tags[tag] = data = handler(self, data)
            del self.tagdata[tag]
            return data

    def getscalar(self, tag, default=None):
        try:
            value = self[tag]
            if len(value) != 1:
                if tag == SAMPLEFORMAT:
                    # work around broken (?) matrox library
                    # (from Ted Wright, via Bob Klimek)
                    raise KeyError # use default
                raise ValueError("not a scalar")
            return value[0]
        except KeyError:
            if default is None:
                raise
            return default

    def __contains__(self, tag):
        return tag in self.tags or tag in self.tagdata

    if bytes is str:
        def has_key(self, tag):
            return tag in self

    def __setitem__(self, tag, value):
        # tags are tuples for integers
        # tags are not tuples for byte, string, and undefined data.
        # see load_*
        if not isinstance(value, tuple):
            value = (value,)
        self.tags[tag] = value

    def __delitem__(self, tag):
        self.tags.pop(tag, self.tagdata.pop(tag, None))

    def __iter__(self):
        return itertools.chain(self.tags.__iter__(), self.tagdata.__iter__())

    def items(self):
        keys = list(self.__iter__())
        values = [self[key] for key in keys]
        return zip(keys, values)

    # load primitives

    load_dispatch = {}

    def load_byte(self, data):
        return data
    load_dispatch[1] = (1, load_byte)

    def load_string(self, data):
        if data[-1:] == b'\0':
            data = data[:-1]
        return data.decode('latin-1', 'replace')
    load_dispatch[2] = (1, load_string)

    def load_short(self, data):
        l = []
        for i in range(0, len(data), 2):
            l.append(self.i16(data, i))
        return tuple(l)
    load_dispatch[3] = (2, load_short)

    def load_long(self, data):
        l = []
        for i in range(0, len(data), 4):
            l.append(self.i32(data, i))
        return tuple(l)
    load_dispatch[4] = (4, load_long)

    def load_rational(self, data):
        l = []
        for i in range(0, len(data), 8):
            l.append((self.i32(data, i), self.i32(data, i+4)))
        return tuple(l)
    load_dispatch[5] = (8, load_rational)

    def load_float(self, data):
        a = array.array("f", data)
        if self.prefix != native_prefix:
            a.byteswap()
        return tuple(a)
    load_dispatch[11] = (4, load_float)

    def load_double(self, data):
        a = array.array("d", data)
        if self.prefix != native_prefix:
            a.byteswap()
        return tuple(a)
    load_dispatch[12] = (8, load_double)

    def load_undefined(self, data):
        # Untyped data
        return data
    load_dispatch[7] = (1, load_undefined)

    def load(self, fp):
        # load tag dictionary

        self.reset()

        i16 = self.i16
        i32 = self.i32

        for i in range(i16(fp.read(2))):

            ifd = fp.read(12)

            tag, typ = i16(ifd), i16(ifd, 2)

            if Image.DEBUG:
                from PIL import TiffTags
                tagname = TiffTags.TAGS.get(tag, "unknown")
                typname = TiffTags.TYPES.get(typ, "unknown")
                print("tag: %s (%d)" % (tagname, tag), end=' ')
                print("- type: %s (%d)" % (typname, typ), end=' ')

            try:
                dispatch = self.load_dispatch[typ]
            except KeyError:
                if Image.DEBUG:
                    print("- unsupported type", typ)
                continue # ignore unsupported type

            size, handler = dispatch

            size = size * i32(ifd, 4)

            # Get and expand tag value
            if size > 4:
                here = fp.tell()
                fp.seek(i32(ifd, 8))
                data = ImageFile._safe_read(fp, size)
                fp.seek(here)
            else:
                data = ifd[8:8+size]

            if len(data) != size:
                warnings.warn("Possibly corrupt EXIF data.  Expecting to read %d bytes but only got %d. Skipping tag %s" % (size, len(data), tag))
                continue

            self.tagdata[tag] = data
            self.tagtype[tag] = typ

            if Image.DEBUG:
                if tag in (COLORMAP, IPTC_NAA_CHUNK, PHOTOSHOP_CHUNK, ICCPROFILE, XMP):
                    print("- value: <table: %d bytes>" % size)
                else:
                    print("- value:", self[tag])

        self.next = i32(fp.read(4))

    # save primitives

    def save(self, fp):

        o16 = self.o16
        o32 = self.o32

        fp.write(o16(len(self.tags)))

        # always write in ascending tag order
        tags = sorted(self.tags.items())

        directory = []
        append = directory.append

        offset = fp.tell() + len(self.tags) * 12 + 4

        stripoffsets = None

        # pass 1: convert tags to binary format
        for tag, value in tags:

            typ = None

            if tag in self.tagtype:
                typ = self.tagtype[tag]
                
            if Image.DEBUG:
                print ("Tag %s, Type: %s, Value: %s" % (tag, typ, value))
                   
            if typ == 1:
                # byte data
                if isinstance(value, tuple):
                    data = value = value[-1]
                else:
                    data = value
            elif typ == 7:
                # untyped data
                data = value = b"".join(value)
            elif isStringType(value[0]):
                # string data
                if isinstance(value, tuple):
                    value = value[-1]
                typ = 2
                # was b'\0'.join(str), which led to \x00a\x00b sorts
                # of strings which I don't see in in the wild tiffs
                # and doesn't match the tiff spec: 8-bit byte that
                # contains a 7-bit ASCII code; the last byte must be
                # NUL (binary zero). Also, I don't think this was well
                # excersized before. 
                data = value = b"" + value.encode('ascii', 'replace') + b"\0"
            else:
                # integer data
                if tag == STRIPOFFSETS:
                    stripoffsets = len(directory)
                    typ = 4 # to avoid catch-22
                elif tag in (X_RESOLUTION, Y_RESOLUTION) or typ==5:
                    # identify rational data fields
                    typ = 5
                    if isinstance(value[0], tuple):
                        # long name for flatten
                        value = tuple(itertools.chain.from_iterable(value))
                elif not typ:
                    typ = 3
                    for v in value:
                        if v >= 65536:
                            typ = 4
                if typ == 3:
                    data = b"".join(map(o16, value))
                else:
                    data = b"".join(map(o32, value))

            if Image.DEBUG:
                from PIL import TiffTags
                tagname = TiffTags.TAGS.get(tag, "unknown")
                typname = TiffTags.TYPES.get(typ, "unknown")
                print("save: %s (%d)" % (tagname, tag), end=' ')
                print("- type: %s (%d)" % (typname, typ), end=' ')
                if tag in (COLORMAP, IPTC_NAA_CHUNK, PHOTOSHOP_CHUNK, ICCPROFILE, XMP):
                    size = len(data)
                    print("- value: <table: %d bytes>" % size)
                else:
                    print("- value:", value)

            # figure out if data fits into the directory
            if len(data) == 4:
                append((tag, typ, len(value), data, b""))
            elif len(data) < 4:
                append((tag, typ, len(value), data + (4-len(data))*b"\0", b""))
            else:
                count = len(value)
                if typ == 5:
                    count = count // 2        # adjust for rational data field

                append((tag, typ, count, o32(offset), data))
                offset = offset + len(data)
                if offset & 1:
                    offset = offset + 1 # word padding

        # update strip offset data to point beyond auxiliary data
        if stripoffsets is not None:
            tag, typ, count, value, data = directory[stripoffsets]
            assert not data, "multistrip support not yet implemented"
            value = o32(self.i32(value) + offset)
            directory[stripoffsets] = tag, typ, count, value, data

        # pass 2: write directory to file
        for tag, typ, count, value, data in directory:
            if Image.DEBUG > 1:
                print(tag, typ, count, repr(value), repr(data))
            fp.write(o16(tag) + o16(typ) + o32(count) + value)

        # -- overwrite here for multi-page --
        fp.write(b"\0\0\0\0") # end of directory

        # pass 3: write auxiliary data to file
        for tag, typ, count, value, data in directory:
            fp.write(data)
            if len(data) & 1:
                fp.write(b"\0")

        return offset

##
# Image plugin for TIFF files.

class TiffImageFile(ImageFile.ImageFile):

    format = "TIFF"
    format_description = "Adobe TIFF"

    def _open(self):
        "Open the first image in a TIFF file"

        # Header
        ifh = self.fp.read(8)

        if ifh[:4] not in PREFIXES:
            raise SyntaxError("not a TIFF file")

        # image file directory (tag dictionary)
        self.tag = self.ifd = ImageFileDirectory(ifh[:2])

        # setup frame pointers
        self.__first = self.__next = self.ifd.i32(ifh, 4)
        self.__frame = -1
        self.__fp = self.fp

        if Image.DEBUG:
            print ("*** TiffImageFile._open ***")
            print ("- __first:", self.__first)
            print ("- ifh: ", ifh)

       # and load the first frame
        self._seek(0)

    def seek(self, frame):
        "Select a given frame as current image"

        if frame < 0:
            frame = 0
        self._seek(frame)

    def tell(self):
        "Return the current frame number"

        return self._tell()

    def _seek(self, frame):

        self.fp = self.__fp
        if frame < self.__frame:
            # rewind file
            self.__frame = -1
            self.__next = self.__first
        while self.__frame < frame:
            if not self.__next:
                raise EOFError("no more images in TIFF file")
            self.fp.seek(self.__next)
            self.tag.load(self.fp)
            self.__next = self.tag.next
            self.__frame = self.__frame + 1
        self._setup()

    def _tell(self):

        return self.__frame

    def _decoder(self, rawmode, layer, tile=None):
        "Setup decoder contexts"

        args = None
        if rawmode == "RGB" and self._planar_configuration == 2:
            rawmode = rawmode[layer]
        compression = self._compression
        if compression == "raw":
            args = (rawmode, 0, 1)
        elif compression == "jpeg":
            args = rawmode, ""
            if JPEGTABLES in self.tag:
                # Hack to handle abbreviated JPEG headers
                self.tile_prefix = self.tag[JPEGTABLES]
        elif compression == "packbits":
            args = rawmode
        elif compression == "tiff_lzw":
            args = rawmode
            if 317 in self.tag:
                # Section 14: Differencing Predictor
                self.decoderconfig = (self.tag[PREDICTOR][0],)

        if ICCPROFILE in self.tag:
            self.info['icc_profile'] = self.tag[ICCPROFILE]

        return args

    def _load_libtiff(self):
        """ Overload method triggered when we detect a compressed tiff
            Calls out to libtiff """

        pixel = Image.Image.load(self)

        if self.tile is None:
            raise IOError("cannot load this image")
        if not self.tile:
            return pixel

        self.load_prepare()

        if not len(self.tile) == 1:
            raise IOError("Not exactly one tile")

        # (self._compression, (extents tuple), 0, (rawmode, self._compression, fp))
        ignored, extents, ignored_2, args = self.tile[0]
        decoder = Image._getdecoder(self.mode, 'libtiff', args, self.decoderconfig)
        try:
            decoder.setimage(self.im, extents)
        except ValueError:
            raise IOError("Couldn't set the image")

        if hasattr(self.fp, "getvalue"):
            # We've got a stringio like thing passed in. Yay for all in memory.
            # The decoder needs the entire file in one shot, so there's not
            # a lot we can do here other than give it the entire file.
            # unless we could do something like get the address of the underlying
            # string for stringio.
            #
            # Rearranging for supporting byteio items, since they have a fileno
            # that returns an IOError if there's no underlying fp. Easier to deal
            # with here by reordering.
            if Image.DEBUG:
                print ("have getvalue. just sending in a string from getvalue")
            n,err = decoder.decode(self.fp.getvalue())
        elif hasattr(self.fp, "fileno"):
            # we've got a actual file on disk, pass in the fp.
            if Image.DEBUG:
                print ("have fileno, calling fileno version of the decoder.")
            self.fp.seek(0)
            n,err = decoder.decode(b"fpfp") # 4 bytes, otherwise the trace might error out
        else:
            # we have something else.
            if Image.DEBUG:
                print ("don't have fileno or getvalue. just reading")
            # UNDONE -- so much for that buffer size thing.
            n,err = decoder.decode(self.fp.read())


        self.tile = []
        self.readonly = 0
        # libtiff closed the fp in a, we need to close self.fp, if possible
        if hasattr(self.fp, 'close'):
            self.fp.close()
        self.fp = None # might be shared

        if err < 0:
            raise IOError(err)

        self.load_end()

        return Image.Image.load(self)

    def _setup(self):
        "Setup this image object based on current tags"

        if 0xBC01 in self.tag:
            raise IOError("Windows Media Photo files not yet supported")

        getscalar = self.tag.getscalar

        # extract relevant tags
        self._compression = COMPRESSION_INFO[getscalar(COMPRESSION, 1)]
        self._planar_configuration = getscalar(PLANAR_CONFIGURATION, 1)

        # photometric is a required tag, but not everyone is reading
        # the specification
        photo = getscalar(PHOTOMETRIC_INTERPRETATION, 0)

        fillorder = getscalar(FILLORDER, 1)

        if Image.DEBUG:
            print("*** Summary ***")
            print("- compression:", self._compression)
            print("- photometric_interpretation:", photo)
            print("- planar_configuration:", self._planar_configuration)
            print("- fill_order:", fillorder)

        # size
        xsize = getscalar(IMAGEWIDTH)
        ysize = getscalar(IMAGELENGTH)
        self.size = xsize, ysize

        if Image.DEBUG:
            print("- size:", self.size)

        format = getscalar(SAMPLEFORMAT, 1)

        # mode: check photometric interpretation and bits per pixel
        key = (
            self.tag.prefix, photo, format, fillorder,
            self.tag.get(BITSPERSAMPLE, (1,)),
            self.tag.get(EXTRASAMPLES, ())
            )
        if Image.DEBUG:
            print("format key:", key)
        try:
            self.mode, rawmode = OPEN_INFO[key]
        except KeyError:
            if Image.DEBUG:
                print("- unsupported format")
            raise SyntaxError("unknown pixel mode")

        if Image.DEBUG:
            print("- raw mode:", rawmode)
            print("- pil mode:", self.mode)

        self.info["compression"] = self._compression

        xres = getscalar(X_RESOLUTION, (1, 1))
        yres = getscalar(Y_RESOLUTION, (1, 1))

        if xres and not isinstance(xres, tuple):
            xres = (xres, 1.)
        if yres and not isinstance(yres, tuple):
            yres = (yres, 1.)
        if xres and yres:
            xres = xres[0] / (xres[1] or 1)
            yres = yres[0] / (yres[1] or 1)
            resunit = getscalar(RESOLUTION_UNIT, 1)
            if resunit == 2: # dots per inch
                self.info["dpi"] = xres, yres
            elif resunit == 3: # dots per centimeter. convert to dpi
                self.info["dpi"] = xres * 2.54, yres * 2.54
            else: # No absolute unit of measurement
                self.info["resolution"] = xres, yres

        # build tile descriptors
        x = y = l = 0
        self.tile = []
        if STRIPOFFSETS in self.tag:
            # striped image
            offsets = self.tag[STRIPOFFSETS]
            h = getscalar(ROWSPERSTRIP, ysize)
            w = self.size[0]
            if READ_LIBTIFF or self._compression in ["tiff_ccitt", "group3", "group4",
                                                     "tiff_jpeg", "tiff_adobe_deflate",
                                                     "tiff_thunderscan", "tiff_deflate",
                                                     "tiff_sgilog", "tiff_sgilog24",
                                                     "tiff_raw_16"]:
                ## if Image.DEBUG:
                ##     print "Activating g4 compression for whole file"

                # Decoder expects entire file as one tile.
                # There's a buffer size limit in load (64k)
                # so large g4 images will fail if we use that
                # function.
                #
                # Setup the one tile for the whole image, then
                # replace the existing load function with our
                # _load_libtiff function.

                self.load = self._load_libtiff

                # To be nice on memory footprint, if there's a
                # file descriptor, use that instead of reading
                # into a string in python.

                # libtiff closes the file descriptor, so pass in a dup.
                try:
                    fp = hasattr(self.fp, "fileno") and os.dup(self.fp.fileno())
                except IOError:
                    # io.BytesIO have a fileno, but returns an IOError if
                    # it doesn't use a file descriptor.
                    fp = False

                # libtiff handles the fillmode for us, so 1;IR should
                # actually be 1;I. Including the R double reverses the
                # bits, so stripes of the image are reversed.  See
                # https://github.com/python-imaging/Pillow/issues/279
                if fillorder == 2:
                    key = (
                        self.tag.prefix, photo, format, 1,
                        self.tag.get(BITSPERSAMPLE, (1,)),
                        self.tag.get(EXTRASAMPLES, ())
                        )
                    if Image.DEBUG:
                        print("format key:", key)
                    # this should always work, since all the
                    # fillorder==2 modes have a corresponding
                    # fillorder=1 mode
                    self.mode, rawmode = OPEN_INFO[key]
                # libtiff always returns the bytes in native order.
                # we're expecting image byte order. So, if the rawmode
                # contains I;16, we need to convert from native to image
                # byte order.
                if self.mode in ('I;16B', 'I;16') and 'I;16' in rawmode:
                    rawmode = 'I;16N'

                # Offset in the tile tuple is 0, we go from 0,0 to
                # w,h, and we only do this once -- eds
                a = (rawmode, self._compression, fp )
                self.tile.append(
                    (self._compression,
                     (0, 0, w, ysize),
                     0, a))
                a = None

            else:
                for i in range(len(offsets)):
                    a = self._decoder(rawmode, l, i)
                    self.tile.append(
                        (self._compression,
                        (0, min(y, ysize), w, min(y+h, ysize)),
                        offsets[i], a))
                    if Image.DEBUG:
                        print ("tiles: ", self.tile)
                    y = y + h
                    if y >= self.size[1]:
                        x = y = 0
                        l = l + 1
                    a = None
        elif TILEOFFSETS in self.tag:
            # tiled image
            w = getscalar(322)
            h = getscalar(323)
            a = None
            for o in self.tag[TILEOFFSETS]:
                if not a:
                    a = self._decoder(rawmode, l)
                # FIXME: this doesn't work if the image size
                # is not a multiple of the tile size...
                self.tile.append(
                    (self._compression,
                    (x, y, x+w, y+h),
                    o, a))
                x = x + w
                if x >= self.size[0]:
                    x, y = 0, y + h
                    if y >= self.size[1]:
                        x = y = 0
                        l = l + 1
                        a = None
        else:
            if Image.DEBUG:
                print("- unsupported data organization")
            raise SyntaxError("unknown data organization")

        # fixup palette descriptor

        if self.mode == "P":
            palette = [o8(a // 256) for a in self.tag[COLORMAP]]
            self.palette = ImagePalette.raw("RGB;L", b"".join(palette))
#
# --------------------------------------------------------------------
# Write TIFF files

# little endian is default except for image modes with explict big endian byte-order

SAVE_INFO = {
    # mode => rawmode, byteorder, photometrics, sampleformat, bitspersample, extra
    "1": ("1", II, 1, 1, (1,), None),
    "L": ("L", II, 1, 1, (8,), None),
    "LA": ("LA", II, 1, 1, (8,8), 2),
    "P": ("P", II, 3, 1, (8,), None),
    "PA": ("PA", II, 3, 1, (8,8), 2),
    "I": ("I;32S", II, 1, 2, (32,), None),
    "I;16": ("I;16", II, 1, 1, (16,), None),
    "I;16S": ("I;16S", II, 1, 2, (16,), None),
    "F": ("F;32F", II, 1, 3, (32,), None),
    "RGB": ("RGB", II, 2, 1, (8,8,8), None),
    "RGBX": ("RGBX", II, 2, 1, (8,8,8,8), 0),
    "RGBA": ("RGBA", II, 2, 1, (8,8,8,8), 2),
    "CMYK": ("CMYK", II, 5, 1, (8,8,8,8), None),
    "YCbCr": ("YCbCr", II, 6, 1, (8,8,8), None),
    "LAB": ("LAB", II, 8, 1, (8,8,8), None),

    "I;32BS": ("I;32BS", MM, 1, 2, (32,), None),
    "I;16B": ("I;16B", MM, 1, 1, (16,), None),
    "I;16BS": ("I;16BS", MM, 1, 2, (16,), None),
    "F;32BF": ("F;32BF", MM, 1, 3, (32,), None),
}

def _cvt_res(value):
    # convert value to TIFF rational number -- (numerator, denominator)
    if isinstance(value, collections.Sequence):
        assert(len(value) % 2 == 0)
        return value
    if isinstance(value, int):
        return (value, 1)
    value = float(value)
    return (int(value * 65536), 65536)

def _save(im, fp, filename):

    try:
        rawmode, prefix, photo, format, bits, extra = SAVE_INFO[im.mode]
    except KeyError:
        raise IOError("cannot write mode %s as TIFF" % im.mode)

    ifd = ImageFileDirectory(prefix)

    compression = im.encoderinfo.get('compression',im.info.get('compression','raw'))

    libtiff = WRITE_LIBTIFF or compression != 'raw' 

    # required for color libtiff images
    ifd[PLANAR_CONFIGURATION] = getattr(im, '_planar_configuration', 1)
    
    # -- multi-page -- skip TIFF header on subsequent pages
    if not libtiff and fp.tell() == 0:
        # tiff header (write via IFD to get everything right)
        # PIL always starts the first IFD at offset 8
        fp.write(ifd.prefix + ifd.o16(42) + ifd.o32(8))

    ifd[IMAGEWIDTH] = im.size[0]
    ifd[IMAGELENGTH] = im.size[1]

    # write any arbitrary tags passed in as an ImageFileDirectory
    info = im.encoderinfo.get("tiffinfo",{})
    if Image.DEBUG:
        print ("Tiffinfo Keys: %s"% info.keys)
    keys = list(info.keys())
    for key in keys:
        ifd[key] = info.get(key)
        try:
            ifd.tagtype[key] = info.tagtype[key]
        except:
            pass # might not be an IFD, Might not have populated type


    # additions written by Greg Couch, gregc@cgl.ucsf.edu
    # inspired by image-sig posting from Kevin Cazabon, kcazabon@home.com
    if hasattr(im, 'tag'):
        # preserve tags from original TIFF image file
        for key in (RESOLUTION_UNIT, X_RESOLUTION, Y_RESOLUTION,
                    IPTC_NAA_CHUNK, PHOTOSHOP_CHUNK, XMP):
            if key in im.tag:
                ifd[key] = im.tag[key]
            ifd.tagtype[key] = im.tag.tagtype.get(key, None)

        # preserve ICC profile (should also work when saving other formats
        # which support profiles as TIFF) -- 2008-06-06 Florian Hoech
        if "icc_profile" in im.info:
            ifd[ICCPROFILE] = im.info["icc_profile"]
            
    if "description" in im.encoderinfo:
        ifd[IMAGEDESCRIPTION] = im.encoderinfo["description"]
    if "resolution" in im.encoderinfo:
        ifd[X_RESOLUTION] = ifd[Y_RESOLUTION] \
                                = _cvt_res(im.encoderinfo["resolution"])
    if "x resolution" in im.encoderinfo:
        ifd[X_RESOLUTION] = _cvt_res(im.encoderinfo["x resolution"])
    if "y resolution" in im.encoderinfo:
        ifd[Y_RESOLUTION] = _cvt_res(im.encoderinfo["y resolution"])
    if "resolution unit" in im.encoderinfo:
        unit = im.encoderinfo["resolution unit"]
        if unit == "inch":
            ifd[RESOLUTION_UNIT] = 2
        elif unit == "cm" or unit == "centimeter":
            ifd[RESOLUTION_UNIT] = 3
        else:
            ifd[RESOLUTION_UNIT] = 1
    if "software" in im.encoderinfo:
        ifd[SOFTWARE] = im.encoderinfo["software"]
    if "date time" in im.encoderinfo:
        ifd[DATE_TIME] = im.encoderinfo["date time"]
    if "artist" in im.encoderinfo:
        ifd[ARTIST] = im.encoderinfo["artist"]
    if "copyright" in im.encoderinfo:
        ifd[COPYRIGHT] = im.encoderinfo["copyright"]

    dpi = im.encoderinfo.get("dpi")
    if dpi:
        ifd[RESOLUTION_UNIT] = 2
        ifd[X_RESOLUTION] = _cvt_res(dpi[0])
        ifd[Y_RESOLUTION] = _cvt_res(dpi[1])

    if bits != (1,):
        ifd[BITSPERSAMPLE] = bits
        if len(bits) != 1:
            ifd[SAMPLESPERPIXEL] = len(bits)
    if extra is not None:
        ifd[EXTRASAMPLES] = extra
    if format != 1:
        ifd[SAMPLEFORMAT] = format

    ifd[PHOTOMETRIC_INTERPRETATION] = photo

    if im.mode == "P":
        lut = im.im.getpalette("RGB", "RGB;L")
        ifd[COLORMAP] = tuple(i8(v) * 256 for v in lut)

    # data orientation
    stride = len(bits) * ((im.size[0]*bits[0]+7)//8)
    ifd[ROWSPERSTRIP] = im.size[1]
    ifd[STRIPBYTECOUNTS] = stride * im.size[1]
    ifd[STRIPOFFSETS] = 0 # this is adjusted by IFD writer
    ifd[COMPRESSION] = COMPRESSION_INFO_REV.get(compression,1) # no compression by default

    if libtiff:
        if Image.DEBUG:
            print ("Saving using libtiff encoder")
            print (ifd.items())
        _fp = 0
        if hasattr(fp, "fileno"):
            fp.seek(0)
            _fp = os.dup(fp.fileno())

        blocklist =  [STRIPOFFSETS, STRIPBYTECOUNTS, ROWSPERSTRIP, ICCPROFILE] # ICC Profile crashes.
        atts={}
        # bits per sample is a single short in the tiff directory, not a list. 
        atts[BITSPERSAMPLE] = bits[0]
        # Merge the ones that we have with (optional) more bits from
        # the original file, e.g x,y resolution so that we can
        # save(load('')) == original file.
        for k,v in itertools.chain(ifd.items(), getattr(im, 'ifd', {}).items()):
            if k not in atts and k not in blocklist:
                if type(v[0]) == tuple and len(v) > 1:
                    # A tuple of more than one rational tuples
                    # flatten to floats, following tiffcp.c->cpTag->TIFF_RATIONAL
                    atts[k] = [float(elt[0])/float(elt[1]) for elt in v]
                    continue
                if type(v[0]) == tuple and len(v) == 1:
                    # A tuple of one rational tuples
                    # flatten to floats, following tiffcp.c->cpTag->TIFF_RATIONAL
                    atts[k] = float(v[0][0])/float(v[0][1])
                    continue
                if type(v) == tuple and len(v) > 2:
                    # List of ints?
                    if type(v[0]) in (int, float):
                        atts[k] = list(v)
                    continue
                if type(v) == tuple and len(v) == 2:
                    # one rational tuple
                    # flatten to float, following tiffcp.c->cpTag->TIFF_RATIONAL
                    atts[k] = float(v[0])/float(v[1])
                    continue
                if type(v) == tuple and len(v) == 1:
                    v = v[0]
                    # drop through
                if isStringType(v):
                    atts[k] = bytes(v.encode('ascii', 'replace')) + b"\0"
                    continue
                else:
                    # int or similar
                    atts[k] = v

        if Image.DEBUG:
            print (atts)

        # libtiff always expects the bytes in native order.
        # we're storing image byte order. So, if the rawmode
        # contains I;16, we need to convert from native to image
        # byte order.
        if im.mode in ('I;16B', 'I;16'):
            rawmode = 'I;16N'

        a = (rawmode, compression, _fp, filename, atts)
        # print (im.mode, compression, a, im.encoderconfig)
        e = Image._getencoder(im.mode, 'libtiff', a, im.encoderconfig)
        e.setimage(im.im, (0,0)+im.size)
        while True:
            l, s, d = e.encode(16*1024) # undone, change to self.decodermaxblock
            if not _fp:
                fp.write(d)
            if s:
                break
        if s < 0:
            raise IOError("encoder error %d when writing image file" % s)

    else:
        offset = ifd.save(fp)

        ImageFile._save(im, fp, [
            ("raw", (0,0)+im.size, offset, (rawmode, stride, 1))
            ])


    # -- helper for multi-page save --
    if "_debug_multipage" in im.encoderinfo:
        #just to access o32 and o16 (using correct byte order)
        im._debug_multipage = ifd

#
# --------------------------------------------------------------------
# Register

Image.register_open("TIFF", TiffImageFile, _accept)
Image.register_save("TIFF", _save)

Image.register_extension("TIFF", ".tif")
Image.register_extension("TIFF", ".tiff")

Image.register_mime("TIFF", "image/tiff")

########NEW FILE########
__FILENAME__ = TiffTags
#
# The Python Imaging Library.
# $Id$
#
# TIFF tags
#
# This module provides clear-text names for various well-known
# TIFF tags.  the TIFF codec works just fine without it.
#
# Copyright (c) Secret Labs AB 1999.
#
# See the README file for information on usage and redistribution.
#

##
# This module provides constants and clear-text names for various
# well-known TIFF tags.
##

##
# Map tag numbers (or tag number, tag value tuples) to tag names.

TAGS = {

    254: "NewSubfileType",
    255: "SubfileType",
    256: "ImageWidth",
    257: "ImageLength",
    258: "BitsPerSample",

    259: "Compression",
    (259, 1): "Uncompressed",
    (259, 2): "CCITT 1d",
    (259, 3): "Group 3 Fax",
    (259, 4): "Group 4 Fax",
    (259, 5): "LZW",
    (259, 6): "JPEG",
    (259, 32773): "PackBits",

    262: "PhotometricInterpretation",
    (262, 0): "WhiteIsZero",
    (262, 1): "BlackIsZero",
    (262, 2): "RGB",
    (262, 3): "RGB Palette",
    (262, 4): "Transparency Mask",
    (262, 5): "CMYK",
    (262, 6): "YCbCr",
    (262, 8): "CieLAB",
    (262, 32803): "CFA", # TIFF/EP, Adobe DNG
    (262, 32892): "LinearRaw", # Adobe DNG

    263: "Thresholding",
    264: "CellWidth",
    265: "CellHeight",
    266: "FillOrder",
    269: "DocumentName",

    270: "ImageDescription",
    271: "Make",
    272: "Model",
    273: "StripOffsets",
    274: "Orientation",
    277: "SamplesPerPixel",
    278: "RowsPerStrip",
    279: "StripByteCounts",

    280: "MinSampleValue",
    281: "MaxSampleValue",
    282: "XResolution",
    283: "YResolution",
    284: "PlanarConfiguration",
    (284, 1): "Contigous",
    (284, 2): "Separate",

    285: "PageName",
    286: "XPosition",
    287: "YPosition",
    288: "FreeOffsets",
    289: "FreeByteCounts",

    290: "GrayResponseUnit",
    291: "GrayResponseCurve",
    292: "T4Options",
    293: "T6Options",
    296: "ResolutionUnit",
    297: "PageNumber",

    301: "TransferFunction",
    305: "Software",
    306: "DateTime",

    315: "Artist",
    316: "HostComputer",
    317: "Predictor",
    318: "WhitePoint",
    319: "PrimaryChromaticies",

    320: "ColorMap",
    321: "HalftoneHints",
    322: "TileWidth",
    323: "TileLength",
    324: "TileOffsets",
    325: "TileByteCounts",

    332: "InkSet",
    333: "InkNames",
    334: "NumberOfInks",
    336: "DotRange",
    337: "TargetPrinter",
    338: "ExtraSamples",
    339: "SampleFormat",

    340: "SMinSampleValue",
    341: "SMaxSampleValue",
    342: "TransferRange",

    347: "JPEGTables",

    # obsolete JPEG tags
    512: "JPEGProc",
    513: "JPEGInterchangeFormat",
    514: "JPEGInterchangeFormatLength",
    515: "JPEGRestartInterval",
    517: "JPEGLosslessPredictors",
    518: "JPEGPointTransforms",
    519: "JPEGQTables",
    520: "JPEGDCTables",
    521: "JPEGACTables",

    529: "YCbCrCoefficients",
    530: "YCbCrSubSampling",
    531: "YCbCrPositioning",
    532: "ReferenceBlackWhite",

    # XMP
    700: "XMP",

    33432: "Copyright",

    # various extensions (should check specs for "official" names)
    33723: "IptcNaaInfo",
    34377: "PhotoshopInfo",

    # Exif IFD
    34665: "ExifIFD",

    # ICC Profile
    34675: "ICCProfile",

    # Adobe DNG
    50706: "DNGVersion",
    50707: "DNGBackwardVersion",
    50708: "UniqueCameraModel",
    50709: "LocalizedCameraModel",
    50710: "CFAPlaneColor",
    50711: "CFALayout",
    50712: "LinearizationTable",
    50713: "BlackLevelRepeatDim",
    50714: "BlackLevel",
    50715: "BlackLevelDeltaH",
    50716: "BlackLevelDeltaV",
    50717: "WhiteLevel",
    50718: "DefaultScale",
    50741: "BestQualityScale",
    50719: "DefaultCropOrigin",
    50720: "DefaultCropSize",
    50778: "CalibrationIlluminant1",
    50779: "CalibrationIlluminant2",
    50721: "ColorMatrix1",
    50722: "ColorMatrix2",
    50723: "CameraCalibration1",
    50724: "CameraCalibration2",
    50725: "ReductionMatrix1",
    50726: "ReductionMatrix2",
    50727: "AnalogBalance",
    50728: "AsShotNeutral",
    50729: "AsShotWhiteXY",
    50730: "BaselineExposure",
    50731: "BaselineNoise",
    50732: "BaselineSharpness",
    50733: "BayerGreenSplit",
    50734: "LinearResponseLimit",
    50735: "CameraSerialNumber",
    50736: "LensInfo",
    50737: "ChromaBlurRadius",
    50738: "AntiAliasStrength",
    50740: "DNGPrivateData",
    50741: "MakerNoteSafety",

    #ImageJ
    50838: "ImageJMetaDataByteCounts", # private tag registered with Adobe
    50839: "ImageJMetaData", # private tag registered with Adobe
}

##
# Map type numbers to type names.

TYPES = {

    1: "byte",
    2: "ascii",
    3: "short",
    4: "long",
    5: "rational",
    6: "signed byte",
    7: "undefined",
    8: "signed short",
    9: "signed long",
    10: "signed rational",
    11: "float",
    12: "double",

}

########NEW FILE########
__FILENAME__ = WalImageFile
# -*- coding: iso-8859-1 -*-
#
# The Python Imaging Library.
# $Id$
#
# WAL file handling
#
# History:
# 2003-04-23 fl   created
#
# Copyright (c) 2003 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#

# NOTE: This format cannot be automatically recognized, so the reader
# is not registered for use with Image.open().  To open a WEL file, use
# the WalImageFile.open() function instead.

# This reader is based on the specification available from:
#    http://www.flipcode.com/tutorials/tut_q2levels.shtml
# and has been tested with a few sample files found using google.

from __future__ import print_function

from PIL import Image, _binary

try:
    import builtins
except ImportError:
    import __builtin__
    builtins = __builtin__

i32 = _binary.i32le

##
# Load texture from a Quake2 WAL texture file.
# <p>
# By default, a Quake2 standard palette is attached to the texture.
# To override the palette, use the <b>putpalette</b> method.
#
# @param filename WAL file name, or an opened file handle.
# @return An image instance.

def open(filename):
    # FIXME: modify to return a WalImageFile instance instead of
    # plain Image object ?

    if hasattr(filename, "read"):
        fp = filename
    else:
        fp = builtins.open(filename, "rb")

    # read header fields
    header = fp.read(32+24+32+12)
    size = i32(header, 32), i32(header, 36)
    offset = i32(header, 40)

    # load pixel data
    fp.seek(offset)

    im = Image.frombytes("P", size, fp.read(size[0] * size[1]))
    im.putpalette(quake2palette)

    im.format = "WAL"
    im.format_description = "Quake2 Texture"

    # strings are null-terminated
    im.info["name"] = header[:32].split(b"\0", 1)[0]
    next_name = header[56:56+32].split(b"\0", 1)[0]
    if next_name:
        im.info["next_name"] = next_name

    return im


quake2palette = (
    # default palette taken from piffo 0.93 by Hans Häggström
    b"\x01\x01\x01\x0b\x0b\x0b\x12\x12\x12\x17\x17\x17\x1b\x1b\x1b\x1e"
    b"\x1e\x1e\x22\x22\x22\x26\x26\x26\x29\x29\x29\x2c\x2c\x2c\x2f\x2f"
    b"\x2f\x32\x32\x32\x35\x35\x35\x37\x37\x37\x3a\x3a\x3a\x3c\x3c\x3c"
    b"\x24\x1e\x13\x22\x1c\x12\x20\x1b\x12\x1f\x1a\x10\x1d\x19\x10\x1b"
    b"\x17\x0f\x1a\x16\x0f\x18\x14\x0d\x17\x13\x0d\x16\x12\x0d\x14\x10"
    b"\x0b\x13\x0f\x0b\x10\x0d\x0a\x0f\x0b\x0a\x0d\x0b\x07\x0b\x0a\x07"
    b"\x23\x23\x26\x22\x22\x25\x22\x20\x23\x21\x1f\x22\x20\x1e\x20\x1f"
    b"\x1d\x1e\x1d\x1b\x1c\x1b\x1a\x1a\x1a\x19\x19\x18\x17\x17\x17\x16"
    b"\x16\x14\x14\x14\x13\x13\x13\x10\x10\x10\x0f\x0f\x0f\x0d\x0d\x0d"
    b"\x2d\x28\x20\x29\x24\x1c\x27\x22\x1a\x25\x1f\x17\x38\x2e\x1e\x31"
    b"\x29\x1a\x2c\x25\x17\x26\x20\x14\x3c\x30\x14\x37\x2c\x13\x33\x28"
    b"\x12\x2d\x24\x10\x28\x1f\x0f\x22\x1a\x0b\x1b\x14\x0a\x13\x0f\x07"
    b"\x31\x1a\x16\x30\x17\x13\x2e\x16\x10\x2c\x14\x0d\x2a\x12\x0b\x27"
    b"\x0f\x0a\x25\x0f\x07\x21\x0d\x01\x1e\x0b\x01\x1c\x0b\x01\x1a\x0b"
    b"\x01\x18\x0a\x01\x16\x0a\x01\x13\x0a\x01\x10\x07\x01\x0d\x07\x01"
    b"\x29\x23\x1e\x27\x21\x1c\x26\x20\x1b\x25\x1f\x1a\x23\x1d\x19\x21"
    b"\x1c\x18\x20\x1b\x17\x1e\x19\x16\x1c\x18\x14\x1b\x17\x13\x19\x14"
    b"\x10\x17\x13\x0f\x14\x10\x0d\x12\x0f\x0b\x0f\x0b\x0a\x0b\x0a\x07"
    b"\x26\x1a\x0f\x23\x19\x0f\x20\x17\x0f\x1c\x16\x0f\x19\x13\x0d\x14"
    b"\x10\x0b\x10\x0d\x0a\x0b\x0a\x07\x33\x22\x1f\x35\x29\x26\x37\x2f"
    b"\x2d\x39\x35\x34\x37\x39\x3a\x33\x37\x39\x30\x34\x36\x2b\x31\x34"
    b"\x27\x2e\x31\x22\x2b\x2f\x1d\x28\x2c\x17\x25\x2a\x0f\x20\x26\x0d"
    b"\x1e\x25\x0b\x1c\x22\x0a\x1b\x20\x07\x19\x1e\x07\x17\x1b\x07\x14"
    b"\x18\x01\x12\x16\x01\x0f\x12\x01\x0b\x0d\x01\x07\x0a\x01\x01\x01"
    b"\x2c\x21\x21\x2a\x1f\x1f\x29\x1d\x1d\x27\x1c\x1c\x26\x1a\x1a\x24"
    b"\x18\x18\x22\x17\x17\x21\x16\x16\x1e\x13\x13\x1b\x12\x12\x18\x10"
    b"\x10\x16\x0d\x0d\x12\x0b\x0b\x0d\x0a\x0a\x0a\x07\x07\x01\x01\x01"
    b"\x2e\x30\x29\x2d\x2e\x27\x2b\x2c\x26\x2a\x2a\x24\x28\x29\x23\x27"
    b"\x27\x21\x26\x26\x1f\x24\x24\x1d\x22\x22\x1c\x1f\x1f\x1a\x1c\x1c"
    b"\x18\x19\x19\x16\x17\x17\x13\x13\x13\x10\x0f\x0f\x0d\x0b\x0b\x0a"
    b"\x30\x1e\x1b\x2d\x1c\x19\x2c\x1a\x17\x2a\x19\x14\x28\x17\x13\x26"
    b"\x16\x10\x24\x13\x0f\x21\x12\x0d\x1f\x10\x0b\x1c\x0f\x0a\x19\x0d"
    b"\x0a\x16\x0b\x07\x12\x0a\x07\x0f\x07\x01\x0a\x01\x01\x01\x01\x01"
    b"\x28\x29\x38\x26\x27\x36\x25\x26\x34\x24\x24\x31\x22\x22\x2f\x20"
    b"\x21\x2d\x1e\x1f\x2a\x1d\x1d\x27\x1b\x1b\x25\x19\x19\x21\x17\x17"
    b"\x1e\x14\x14\x1b\x13\x12\x17\x10\x0f\x13\x0d\x0b\x0f\x0a\x07\x07"
    b"\x2f\x32\x29\x2d\x30\x26\x2b\x2e\x24\x29\x2c\x21\x27\x2a\x1e\x25"
    b"\x28\x1c\x23\x26\x1a\x21\x25\x18\x1e\x22\x14\x1b\x1f\x10\x19\x1c"
    b"\x0d\x17\x1a\x0a\x13\x17\x07\x10\x13\x01\x0d\x0f\x01\x0a\x0b\x01"
    b"\x01\x3f\x01\x13\x3c\x0b\x1b\x39\x10\x20\x35\x14\x23\x31\x17\x23"
    b"\x2d\x18\x23\x29\x18\x3f\x3f\x3f\x3f\x3f\x39\x3f\x3f\x31\x3f\x3f"
    b"\x2a\x3f\x3f\x20\x3f\x3f\x14\x3f\x3c\x12\x3f\x39\x0f\x3f\x35\x0b"
    b"\x3f\x32\x07\x3f\x2d\x01\x3d\x2a\x01\x3b\x26\x01\x39\x21\x01\x37"
    b"\x1d\x01\x34\x1a\x01\x32\x16\x01\x2f\x12\x01\x2d\x0f\x01\x2a\x0b"
    b"\x01\x27\x07\x01\x23\x01\x01\x1d\x01\x01\x17\x01\x01\x10\x01\x01"
    b"\x3d\x01\x01\x19\x19\x3f\x3f\x01\x01\x01\x01\x3f\x16\x16\x13\x10"
    b"\x10\x0f\x0d\x0d\x0b\x3c\x2e\x2a\x36\x27\x20\x30\x21\x18\x29\x1b"
    b"\x10\x3c\x39\x37\x37\x32\x2f\x31\x2c\x28\x2b\x26\x21\x30\x22\x20"
)

if __name__ == "__main__":
    im = open("../hacks/sample.wal")
    print(im.info, im.mode, im.size)
    im.save("../out.png")

########NEW FILE########
__FILENAME__ = WebPImagePlugin
from PIL import Image
from PIL import ImageFile
from io import BytesIO
from PIL import _webp


_VALID_WEBP_MODES = {
    "RGB": True,
    "RGBA": True,
    }

_VP8_MODES_BY_IDENTIFIER = {
    b"VP8 ": "RGB",
    b"VP8X": "RGBA",
    b"VP8L": "RGBA", # lossless
    }


def _accept(prefix):
    is_riff_file_format = prefix[:4] == b"RIFF"
    is_webp_file = prefix[8:12] == b"WEBP"
    is_valid_vp8_mode = prefix[12:16] in _VP8_MODES_BY_IDENTIFIER

    return is_riff_file_format and is_webp_file and is_valid_vp8_mode


class WebPImageFile(ImageFile.ImageFile):

    format = "WEBP"
    format_description = "WebP image"

    def _open(self):
        data, width, height, self.mode, icc_profile, exif = _webp.WebPDecode(self.fp.read())

        if icc_profile:
            self.info["icc_profile"] = icc_profile
        if exif:
            self.info["exif"] = exif

        self.size = width, height
        self.fp = BytesIO(data)
        self.tile = [("raw", (0, 0) + self.size, 0, self.mode)]

    def _getexif(self):
        from PIL.JpegImagePlugin import _getexif
        return _getexif(self)


def _save(im, fp, filename):
    image_mode = im.mode
    if im.mode not in _VALID_WEBP_MODES:
        raise IOError("cannot write mode %s as WEBP" % image_mode)

    lossless = im.encoderinfo.get("lossless", False)
    quality = im.encoderinfo.get("quality", 80)
    icc_profile = im.encoderinfo.get("icc_profile", "")
    exif = im.encoderinfo.get("exif", "")

    data = _webp.WebPEncode(
        im.tobytes(),
        im.size[0],
        im.size[1],
        lossless,
        float(quality),
        im.mode,
        icc_profile,
        exif
    )
    if data is None:
        raise IOError("cannot write file as WEBP (encoder returned None)")

    fp.write(data)


Image.register_open("WEBP", WebPImageFile, _accept)
Image.register_save("WEBP", _save)

Image.register_extension("WEBP", ".webp")
Image.register_mime("WEBP", "image/webp")

########NEW FILE########
__FILENAME__ = WmfImagePlugin
#
# The Python Imaging Library
# $Id$
#
# WMF stub codec
#
# history:
# 1996-12-14 fl   Created
# 2004-02-22 fl   Turned into a stub driver
# 2004-02-23 fl   Added EMF support
#
# Copyright (c) Secret Labs AB 1997-2004.  All rights reserved.
# Copyright (c) Fredrik Lundh 1996.
#
# See the README file for information on usage and redistribution.
#

__version__ = "0.2"

from PIL import Image, ImageFile, _binary

_handler = None

if str != bytes:
    long = int

##
# Install application-specific WMF image handler.
#
# @param handler Handler object.

def register_handler(handler):
    global _handler
    _handler = handler

if hasattr(Image.core, "drawwmf"):
    # install default handler (windows only)

    class WmfHandler:

        def open(self, im):
            im.mode = "RGB"
            self.bbox = im.info["wmf_bbox"]

        def load(self, im):
            im.fp.seek(0) # rewind
            return Image.frombytes(
                "RGB", im.size,
                Image.core.drawwmf(im.fp.read(), im.size, self.bbox),
                "raw", "BGR", (im.size[0]*3 + 3) & -4, -1
                )

    register_handler(WmfHandler())

# --------------------------------------------------------------------

word = _binary.i16le

def short(c, o=0):
    v = word(c, o)
    if v >= 32768:
        v = v - 65536
    return v

dword = _binary.i32le

#
# --------------------------------------------------------------------
# Read WMF file

def _accept(prefix):
    return (
        prefix[:6] == b"\xd7\xcd\xc6\x9a\x00\x00" or
        prefix[:4] == b"\x01\x00\x00\x00"
        )

##
# Image plugin for Windows metafiles.

class WmfStubImageFile(ImageFile.StubImageFile):

    format = "WMF"
    format_description = "Windows Metafile"

    def _open(self):

        # check placable header
        s = self.fp.read(80)

        if s[:6] == b"\xd7\xcd\xc6\x9a\x00\x00":

            # placeable windows metafile

            # get units per inch
            inch = word(s, 14)

            # get bounding box
            x0 = short(s, 6); y0 = short(s, 8)
            x1 = short(s, 10); y1 = short(s, 12)

            # normalize size to 72 dots per inch
            size = (x1 - x0) * 72 // inch, (y1 - y0) * 72 // inch

            self.info["wmf_bbox"] = x0, y0, x1, y1

            self.info["dpi"] = 72

            # print self.mode, self.size, self.info

            # sanity check (standard metafile header)
            if s[22:26] != b"\x01\x00\t\x00":
                raise SyntaxError("Unsupported WMF file format")

        elif dword(s) == 1 and s[40:44] == b" EMF":
            # enhanced metafile

            # get bounding box
            x0 = dword(s, 8); y0 = dword(s, 12)
            x1 = dword(s, 16); y1 = dword(s, 20)

            # get frame (in 0.01 millimeter units)
            frame = dword(s, 24), dword(s, 28), dword(s, 32), dword(s, 36)

            # normalize size to 72 dots per inch
            size = x1 - x0, y1 - y0

            # calculate dots per inch from bbox and frame
            xdpi = 2540 * (x1 - y0) // (frame[2] - frame[0])
            ydpi = 2540 * (y1 - y0) // (frame[3] - frame[1])

            self.info["wmf_bbox"] = x0, y0, x1, y1

            if xdpi == ydpi:
                self.info["dpi"] = xdpi
            else:
                self.info["dpi"] = xdpi, ydpi

        else:
            raise SyntaxError("Unsupported file format")

        self.mode = "RGB"
        self.size = size

        loader = self._load()
        if loader:
            loader.open(self)

    def _load(self):
        return _handler


def _save(im, fp, filename):
    if _handler is None or not hasattr("_handler", "save"):
        raise IOError("WMF save handler not installed")
    _handler.save(im, fp, filename)

#
# --------------------------------------------------------------------
# Registry stuff

Image.register_open(WmfStubImageFile.format, WmfStubImageFile, _accept)
Image.register_save(WmfStubImageFile.format, _save)

Image.register_extension(WmfStubImageFile.format, ".wmf")
Image.register_extension(WmfStubImageFile.format, ".emf")

########NEW FILE########
__FILENAME__ = XbmImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# XBM File handling
#
# History:
# 1995-09-08 fl   Created
# 1996-11-01 fl   Added save support
# 1997-07-07 fl   Made header parser more tolerant
# 1997-07-22 fl   Fixed yet another parser bug
# 2001-02-17 fl   Use 're' instead of 'regex' (Python 2.1) (0.4)
# 2001-05-13 fl   Added hotspot handling (based on code from Bernhard Herzog)
# 2004-02-24 fl   Allow some whitespace before first #define
#
# Copyright (c) 1997-2004 by Secret Labs AB
# Copyright (c) 1996-1997 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

__version__ = "0.6"

import re
from PIL import Image, ImageFile

# XBM header
xbm_head = re.compile(
    b"\s*#define[ \t]+[^_]*_width[ \t]+(?P<width>[0-9]+)[\r\n]+"
    b"#define[ \t]+[^_]*_height[ \t]+(?P<height>[0-9]+)[\r\n]+"
    b"(?P<hotspot>"
    b"#define[ \t]+[^_]*_x_hot[ \t]+(?P<xhot>[0-9]+)[\r\n]+"
    b"#define[ \t]+[^_]*_y_hot[ \t]+(?P<yhot>[0-9]+)[\r\n]+"
    b")?"
    b"[\\000-\\377]*_bits\\[\\]"
)

def _accept(prefix):
    return prefix.lstrip()[:7] == b"#define"

##
# Image plugin for X11 bitmaps.

class XbmImageFile(ImageFile.ImageFile):

    format = "XBM"
    format_description = "X11 Bitmap"

    def _open(self):

        m = xbm_head.match(self.fp.read(512))

        if m:

            xsize = int(m.group("width"))
            ysize = int(m.group("height"))

            if m.group("hotspot"):
                self.info["hotspot"] = (
                    int(m.group("xhot")), int(m.group("yhot"))
                    )

            self.mode = "1"
            self.size = xsize, ysize

            self.tile = [("xbm", (0, 0)+self.size, m.end(), None)]


def _save(im, fp, filename):

    if im.mode != "1":
        raise IOError("cannot write mode %s as XBM" % im.mode)

    fp.write(("#define im_width %d\n" % im.size[0]).encode('ascii'))
    fp.write(("#define im_height %d\n" % im.size[1]).encode('ascii'))

    hotspot = im.encoderinfo.get("hotspot")
    if hotspot:
        fp.write(("#define im_x_hot %d\n" % hotspot[0]).encode('ascii'))
        fp.write(("#define im_y_hot %d\n" % hotspot[1]).encode('ascii'))

    fp.write(b"static char im_bits[] = {\n")

    ImageFile._save(im, fp, [("xbm", (0,0)+im.size, 0, None)])

    fp.write(b"};\n")


Image.register_open("XBM", XbmImageFile, _accept)
Image.register_save("XBM", _save)

Image.register_extension("XBM", ".xbm")

Image.register_mime("XBM", "image/xbm")

########NEW FILE########
__FILENAME__ = XpmImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# XPM File handling
#
# History:
# 1996-12-29 fl   Created
# 2001-02-17 fl   Use 're' instead of 'regex' (Python 2.1) (0.7)
#
# Copyright (c) Secret Labs AB 1997-2001.
# Copyright (c) Fredrik Lundh 1996-2001.
#
# See the README file for information on usage and redistribution.
#


__version__ = "0.2"


import re
from PIL import Image, ImageFile, ImagePalette
from PIL._binary import i8, o8

# XPM header
xpm_head = re.compile(b"\"([0-9]*) ([0-9]*) ([0-9]*) ([0-9]*)")


def _accept(prefix):
    return prefix[:9] == b"/* XPM */"

##
# Image plugin for X11 pixel maps.

class XpmImageFile(ImageFile.ImageFile):

    format = "XPM"
    format_description = "X11 Pixel Map"

    def _open(self):

        if not _accept(self.fp.read(9)):
            raise SyntaxError("not an XPM file")

        # skip forward to next string
        while True:
            s = self.fp.readline()
            if not s:
                raise SyntaxError("broken XPM file")
            m = xpm_head.match(s)
            if m:
                break

        self.size = int(m.group(1)), int(m.group(2))

        pal = int(m.group(3))
        bpp = int(m.group(4))

        if pal > 256 or bpp != 1:
            raise ValueError("cannot read this XPM file")

        #
        # load palette description

        palette = [b"\0\0\0"] * 256

        for i in range(pal):

            s = self.fp.readline()
            if s[-2:] == b'\r\n':
                s = s[:-2]
            elif s[-1:] in b'\r\n':
                s = s[:-1]

            c = i8(s[1])
            s = s[2:-2].split()

            for i in range(0, len(s), 2):

                if s[i] == b"c":

                    # process colour key
                    rgb = s[i+1]
                    if rgb == b"None":
                        self.info["transparency"] = c
                    elif rgb[0:1] == b"#":
                        # FIXME: handle colour names (see ImagePalette.py)
                        rgb = int(rgb[1:], 16)
                        palette[c] = o8((rgb >> 16) & 255) +\
                                     o8((rgb >> 8) & 255) +\
                                     o8(rgb & 255)
                    else:
                        # unknown colour
                        raise ValueError("cannot read this XPM file")
                    break

            else:

                # missing colour key
                raise ValueError("cannot read this XPM file")

        self.mode = "P"
        self.palette = ImagePalette.raw("RGB", b"".join(palette))

        self.tile = [("raw", (0, 0)+self.size, self.fp.tell(), ("P", 0, 1))]

    def load_read(self, bytes):

        #
        # load all image data in one chunk

        xsize, ysize = self.size

        s = [None] * ysize

        for i in range(ysize):
            s[i] = self.fp.readline()[1:xsize+1].ljust(xsize)

        self.fp = None

        return b"".join(s)

#
# Registry

Image.register_open("XPM", XpmImageFile, _accept)

Image.register_extension("XPM", ".xpm")

Image.register_mime("XPM", "image/xpm")

########NEW FILE########
__FILENAME__ = XVThumbImagePlugin
#
# The Python Imaging Library.
# $Id$
#
# XV Thumbnail file handler by Charles E. "Gene" Cash
# (gcash@magicnet.net)
#
# see xvcolor.c and xvbrowse.c in the sources to John Bradley's XV,
# available from ftp://ftp.cis.upenn.edu/pub/xv/
#
# history:
# 98-08-15 cec  created (b/w only)
# 98-12-09 cec  added color palette
# 98-12-28 fl   added to PIL (with only a few very minor modifications)
#
# To do:
# FIXME: make save work (this requires quantization support)
#

__version__ = "0.1"

from PIL import Image, ImageFile, ImagePalette, _binary

o8 = _binary.o8

# standard color palette for thumbnails (RGB332)
PALETTE = b""
for r in range(8):
    for g in range(8):
        for b in range(4):
            PALETTE = PALETTE + (o8((r*255)//7)+o8((g*255)//7)+o8((b*255)//3))

##
# Image plugin for XV thumbnail images.

class XVThumbImageFile(ImageFile.ImageFile):

    format = "XVThumb"
    format_description = "XV thumbnail image"

    def _open(self):

        # check magic
        s = self.fp.read(6)
        if s != b"P7 332":
            raise SyntaxError("not an XV thumbnail file")

        # Skip to beginning of next line
        self.fp.readline()

        # skip info comments
        while True:
            s = self.fp.readline()
            if not s:
                raise SyntaxError("Unexpected EOF reading XV thumbnail file")
            if s[0] != b'#':
                break

        # parse header line (already read)
        s = s.strip().split()

        self.mode = "P"
        self.size = int(s[0:1]), int(s[1:2])

        self.palette = ImagePalette.raw("RGB", PALETTE)

        self.tile = [
            ("raw", (0, 0)+self.size,
             self.fp.tell(), (self.mode, 0, 1)
             )]

# --------------------------------------------------------------------

Image.register_open("XVThumb", XVThumbImageFile)

########NEW FILE########
__FILENAME__ = _binary
#
# The Python Imaging Library.
# $Id$
#
# Binary input/output support routines.
#
# Copyright (c) 1997-2003 by Secret Labs AB
# Copyright (c) 1995-2003 by Fredrik Lundh
# Copyright (c) 2012 by Brian Crowell
#
# See the README file for information on usage and redistribution.
#

if bytes is str:
    def i8(c):
        return ord(c)

    def o8(i):
        return chr(i&255)
else:
    def i8(c):
        return c if c.__class__ is int else c[0]

    def o8(i):
        return bytes((i&255,))

# Input, le = little endian, be = big endian
#TODO: replace with more readable struct.unpack equivalent
def i16le(c, o=0):
    """
    Converts a 2-bytes (16 bits) string to an integer.

    c: string containing bytes to convert
    o: offset of bytes to convert in string
    """
    return i8(c[o]) | (i8(c[o+1])<<8)

def i32le(c, o=0):
    """
    Converts a 4-bytes (32 bits) string to an integer.

    c: string containing bytes to convert
    o: offset of bytes to convert in string
    """
    return i8(c[o]) | (i8(c[o+1])<<8) | (i8(c[o+2])<<16) | (i8(c[o+3])<<24)

def i16be(c, o=0):
    return (i8(c[o])<<8) | i8(c[o+1])

def i32be(c, o=0):
    return (i8(c[o])<<24) | (i8(c[o+1])<<16) | (i8(c[o+2])<<8) | i8(c[o+3])

# Output, le = little endian, be = big endian
def o16le(i):
    return o8(i) + o8(i>>8)

def o32le(i):
    return o8(i) + o8(i>>8) + o8(i>>16) + o8(i>>24)

def o16be(i):
    return o8(i>>8) + o8(i)

def o32be(i):
    return o8(i>>24) + o8(i>>16) + o8(i>>8) + o8(i)


########NEW FILE########
__FILENAME__ = _util
import os

if bytes is str:
    def isStringType(t):
        return isinstance(t, basestring)
    def isPath(f):
        return isinstance(f, basestring)
else:
    def isStringType(t):
        return isinstance(t, str)
    def isPath(f):
        return isinstance(f, (bytes, str))

# Checks if an object is a string, and that it points to a directory.
def isDirectory(f):
    return isPath(f) and os.path.isdir(f)

class deferred_error(object):
    def __init__(self, ex):
        self.ex = ex
    def __getattr__(self, elt):
        raise self.ex

########NEW FILE########
__FILENAME__ = demo_numarray
#!/usr/bin/env python

#
# Shows how to scan a 16 bit grayscale image into a numarray object
#

from __future__ import print_function

# Get the path set up to find PIL modules if not installed yet:
import sys ; sys.path.append('../PIL')

from numarray import *
import sane
import Image

def toImage(arr):
    if arr.type().bytes == 1:
        # need to swap coordinates btw array and image (with [::-1])
        im = Image.frombytes('L', arr.shape[::-1], arr.tostring())
    else:
        arr_c = arr - arr.min()
        arr_c *= (255./arr_c.max())
        arr = arr_c.astype(UInt8)
        # need to swap coordinates btw array and image (with [::-1])
        im = Image.frombytes('L', arr.shape[::-1], arr.tostring())
    return im

print('SANE version:', sane.init())
print('Available devices=', sane.get_devices())

s = sane.open(sane.get_devices()[0][0])

# Set scan parameters
s.mode = 'gray'
s.br_x=320. ; s.br_y=240.

print('Device parameters:', s.get_parameters())

s.depth=16
arr16 = s.arr_scan()
toImage(arr16).show()

########NEW FILE########
__FILENAME__ = demo_pil
#!/usr/bin/env python

#
# Shows how to scan a color image into a PIL rgb-image
#

from __future__ import print_function

# Get the path set up to find PIL modules if not installed yet:
import sys ; sys.path.append('../PIL')

import sane
print('SANE version:', sane.init())
print('Available devices=', sane.get_devices())

s = sane.open(sane.get_devices()[0][0])

s.mode = 'color'
s.br_x=320. ; s.br_y=240.

print('Device parameters:', s.get_parameters())

# Initiate the scan
s.start()

# Get an Image object
# (For my B&W QuickCam, this is a grey-scale image.  Other scanning devices
#  may return a
im=s.snap()

# Write the image out as a GIF file
#im.save('foo.gif')

# The show method() simply saves the image to a temporary file and calls "xv".
im.show()

########NEW FILE########
__FILENAME__ = sane
# sane.py
#
# Python wrapper on top of the _sane module, which is in turn a very
# thin wrapper on top of the SANE library.  For a complete understanding
# of SANE, consult the documentation at the SANE home page:
# http://www.mostang.com/sane/ .

__version__ = '2.0'
__author__  = ['Andrew Kuchling', 'Ralph Heinkel']

from PIL import Image

import _sane
from _sane import *

TYPE_STR = { TYPE_BOOL:   "TYPE_BOOL",   TYPE_INT:    "TYPE_INT",
             TYPE_FIXED:  "TYPE_FIXED",  TYPE_STRING: "TYPE_STRING",
             TYPE_BUTTON: "TYPE_BUTTON", TYPE_GROUP:  "TYPE_GROUP" }

UNIT_STR = { UNIT_NONE:        "UNIT_NONE",
             UNIT_PIXEL:       "UNIT_PIXEL",
             UNIT_BIT:         "UNIT_BIT",
             UNIT_MM:          "UNIT_MM",
             UNIT_DPI:         "UNIT_DPI",
             UNIT_PERCENT:     "UNIT_PERCENT",
             UNIT_MICROSECOND: "UNIT_MICROSECOND" }


class Option:
    """Class representing a SANE option.
    Attributes:
    index -- number from 0 to n, giving the option number
    name -- a string uniquely identifying the option
    title -- single-line string containing a title for the option
    desc -- a long string describing the option; useful as a help message
    type -- type of this option.  Possible values: TYPE_BOOL,
            TYPE_INT, TYPE_STRING, and so forth.
    unit -- units of this option.  Possible values: UNIT_NONE,
            UNIT_PIXEL, etc.
    size -- size of the value in bytes
    cap -- capabilities available; CAP_EMULATED, CAP_SOFT_SELECT, etc.
    constraint -- constraint on values.  Possible values:
        None : No constraint
        (min,max,step)  Integer values, from min to max, stepping by
        list of integers or strings: only the listed values are allowed
    """

    def __init__(self, args, scanDev):
        self.scanDev = scanDev # needed to get current value of this option
        self.index, self.name = args[0], args[1]
        self.title, self.desc = args[2], args[3]
        self.type, self.unit  = args[4], args[5]
        self.size, self.cap   = args[6], args[7]
        self.constraint = args[8]
        def f(x):
            if x=='-': return '_'
            else: return x
        if not isinstance(self.name, str): self.py_name=str(self.name)
        else: self.py_name=''.join(map(f, self.name))

    def is_active(self):
        return _sane.OPTION_IS_ACTIVE(self.cap)
    def is_settable(self):
        return _sane.OPTION_IS_SETTABLE(self.cap)
    def __repr__(self):
        if self.is_settable():
            settable = 'yes'
        else:
            settable = 'no'
        if self.is_active():
            active = 'yes'
            curValue = repr(getattr(self.scanDev, self.py_name))
        else:
            active = 'no'
            curValue = '<not available, inactive option>'
        s = """\nName:      %s
Cur value: %s
Index:     %d
Title:     %s
Desc:      %s
Type:      %s
Unit:      %s
Constr:    %s
active:    %s
settable:  %s\n""" % (self.py_name, curValue,
                      self.index, self.title, self.desc,
                      TYPE_STR[self.type], UNIT_STR[self.unit],
                      repr(self.constraint), active, settable)
        return s


class _SaneIterator:
    """ intended for ADF scans.
    """

    def __init__(self, device):
        self.device = device

    def __iter__(self):
        return self

    def __del__(self):
        self.device.cancel()

    def next(self):
        try:
            self.device.start()
        except error as v:
            if v == 'Document feeder out of documents':
                raise StopIteration
            else:
                raise
        return self.device.snap(1)



class SaneDev:
    """Class representing a SANE device.
    Methods:
    start()    -- initiate a scan, using the current settings
    snap()     -- snap a picture, returning an Image object
    arr_snap() -- snap a picture, returning a numarray object
    cancel()   -- cancel an in-progress scanning operation
    fileno()   -- return the file descriptor for the scanner (handy for select)

    Also available, but rather low-level:
    get_parameters() -- get the current parameter settings of the device
    get_options()    -- return a list of tuples describing all the options.

    Attributes:
    optlist -- list of option names

    You can also access an option name to retrieve its value, and to
    set it.  For example, if one option has a .name attribute of
    imagemode, and scanner is a SaneDev object, you can do:
         print scanner.imagemode
         scanner.imagemode = 'Full frame'
         scanner.['imagemode'] returns the corresponding Option object.
    """
    def __init__(self, devname):
        d=self.__dict__
        d['sane_signature'] = self._getSaneSignature(devname)
        d['scanner_model']  = d['sane_signature'][1:3]
        d['dev'] = _sane._open(devname)
        self.__load_option_dict()

    def _getSaneSignature(self, devname):
        devices = get_devices()
        if not devices:
            raise RuntimeError('no scanner available')
        for dev in devices:
            if devname == dev[0]:
                return dev
        raise RuntimeError('no such scan device "%s"' % devname)

    def __load_option_dict(self):
        d=self.__dict__
        d['opt']={}
        optlist=d['dev'].get_options()
        for t in optlist:
            o=Option(t, self)
            if o.type!=TYPE_GROUP:
                d['opt'][o.py_name]=o

    def __setattr__(self, key, value):
        dev=self.__dict__['dev']
        optdict=self.__dict__['opt']
        if key not in optdict:
            self.__dict__[key]=value ; return
        opt=optdict[key]
        if opt.type==TYPE_GROUP:
            raise AttributeError("Groups can't be set: "+key)
        if not _sane.OPTION_IS_ACTIVE(opt.cap):
            raise AttributeError('Inactive option: '+key)
        if not _sane.OPTION_IS_SETTABLE(opt.cap):
            raise AttributeError("Option can't be set by software: "+key)
        if isinstance(value, int) and opt.type == TYPE_FIXED:
            # avoid annoying errors of backend if int is given instead float:
            value = float(value)
        self.last_opt = dev.set_option(opt.index, value)
        # do binary AND to find if we have to reload options:
        if self.last_opt & INFO_RELOAD_OPTIONS:
            self.__load_option_dict()

    def __getattr__(self, key):
        dev=self.__dict__['dev']
        optdict=self.__dict__['opt']
        if key=='optlist':
            return list(self.opt.keys())
        if key=='area':
            return (self.tl_x, self.tl_y),(self.br_x, self.br_y)
        if key not in optdict:
            raise AttributeError('No such attribute: '+key)
        opt=optdict[key]
        if opt.type==TYPE_BUTTON:
            raise AttributeError("Buttons don't have values: "+key)
        if opt.type==TYPE_GROUP:
            raise AttributeError("Groups don't have values: "+key)
        if not _sane.OPTION_IS_ACTIVE(opt.cap):
            raise AttributeError('Inactive option: '+key)
        value = dev.get_option(opt.index)
        return value

    def __getitem__(self, key):
        return self.opt[key]

    def get_parameters(self):
        """Return a 5-tuple holding all the current device settings:
   (format, last_frame, (pixels_per_line, lines), depth, bytes_per_line)

- format is one of 'L' (grey), 'RGB', 'R' (red), 'G' (green), 'B' (blue).
- last_frame [bool] indicates if this is the last frame of a multi frame image
- (pixels_per_line, lines) specifies the size of the scanned image (x,y)
- lines denotes the number of scanlines per frame
- depth gives number of pixels per sample
"""
        return self.dev.get_parameters()

    def get_options(self):
        "Return a list of tuples describing all the available options"
        return self.dev.get_options()

    def start(self):
        "Initiate a scanning operation"
        return self.dev.start()

    def cancel(self):
        "Cancel an in-progress scanning operation"
        return self.dev.cancel()

    def snap(self, no_cancel=0):
        "Snap a picture, returning a PIL image object with the results"
        (mode, last_frame,
         (xsize, ysize), depth, bytes_per_line) = self.get_parameters()
        if mode in ['gray', 'red', 'green', 'blue']:
            format = 'L'
        elif mode == 'color':
            format = 'RGB'
        else:
            raise ValueError('got unknown "mode" from self.get_parameters()')
        im=Image.new(format, (xsize,ysize))
        self.dev.snap( im.im.id, no_cancel )
        return im

    def scan(self):
        self.start()
        return self.snap()

    def multi_scan(self):
        return _SaneIterator(self)

    def arr_snap(self, multipleOf=1):
        """Snap a picture, returning a numarray object with the results.
        By default the resulting array has the same number of pixels per
        line as specified in self.get_parameters()[2][0]
        However sometimes it is necessary to obtain arrays where
        the number of pixels per line is e.g. a multiple of 4. This can then
        be achieved with the option 'multipleOf=4'. So if the scanner
        scanned 34 pixels per line, you will obtain an array with 32 pixels
        per line.
        """
        (mode, last_frame, (xsize, ysize), depth, bpl) = self.get_parameters()
        if not mode in ['gray', 'red', 'green', 'blue']:
            raise RuntimeError('arr_snap() only works with monochrome images')
        if multipleOf < 1:
            raise ValueError('option "multipleOf" must be a positive number')
        elif multipleOf > 1:
            pixels_per_line = xsize - divmod(xsize, 4)[1]
        else:
            pixels_per_line = xsize
        return self.dev.arr_snap(pixels_per_line)

    def arr_scan(self, multipleOf=1):
        self.start()
        return self.arr_snap(multipleOf=multipleOf)

    def fileno(self):
        "Return the file descriptor for the scanning device"
        return self.dev.fileno()

    def close(self):
        self.dev.close()


def open(devname):
    "Open a device for scanning"
    new=SaneDev(devname)
    return new

########NEW FILE########
__FILENAME__ = enhancer
#!/usr/bin/env python
#
# The Python Imaging Library
# $Id$
#
# this demo script creates four windows containing an image and a slider.
# drag the slider to modify the image.
#

try:
    from tkinter import *
except ImportError:
    from Tkinter import *

from PIL import Image, ImageTk, ImageEnhance
import sys

#
# enhancer widget

class Enhance(Frame):
    def __init__(self, master, image, name, enhancer, lo, hi):
        Frame.__init__(self, master)

        # set up the image
        self.tkim = ImageTk.PhotoImage(image.mode, image.size)
        self.enhancer = enhancer(image)
        self.update("1.0") # normalize

        # image window
        Label(self, image=self.tkim).pack()

        # scale
        s = Scale(self, label=name, orient=HORIZONTAL,
                  from_=lo, to=hi, resolution=0.01,
                  command=self.update)
        s.set(self.value)
        s.pack()

    def update(self, value):
        self.value = eval(value)
        self.tkim.paste(self.enhancer.enhance(self.value))

#
# main

root = Tk()

im = Image.open(sys.argv[1])

im.thumbnail((200, 200))

Enhance(root, im, "Color", ImageEnhance.Color, 0.0, 4.0).pack()
Enhance(Toplevel(), im, "Sharpness", ImageEnhance.Sharpness, -2.0, 2.0).pack()
Enhance(Toplevel(), im, "Brightness", ImageEnhance.Brightness, -1.0, 3.0).pack()
Enhance(Toplevel(), im, "Contrast", ImageEnhance.Contrast, -1.0, 3.0).pack()

root.mainloop()

########NEW FILE########
__FILENAME__ = explode
#!/usr/bin/env python
#
# The Python Imaging Library
# $Id$
#
# split an animation into a number of frame files
#

from __future__ import print_function

from PIL import Image
import os, sys

class Interval:

    def __init__(self, interval = "0"):

        self.setinterval(interval)

    def setinterval(self, interval):

        self.hilo = []

        for s in interval.split(","):
            if not s.strip():
                continue
            try:
                v = int(s)
                if v < 0:
                    lo, hi = 0, -v
                else:
                    lo = hi = v
            except ValueError:
                i = s.find("-")
                lo, hi = int(s[:i]), int(s[i+1:])

            self.hilo.append((hi, lo))

        if not self.hilo:
            self.hilo = [(sys.maxsize, 0)]

    def __getitem__(self, index):

        for hi, lo in self.hilo:
            if hi >= index >= lo:
                return 1
        return 0

# --------------------------------------------------------------------
# main program

html = 0

if sys.argv[1:2] == ["-h"]:
    html = 1
    del sys.argv[1]

if not sys.argv[2:]:
    print()
    print("Syntax: python explode.py infile template [range]")
    print()
    print("The template argument is used to construct the names of the")
    print("individual frame files.  The frames are numbered file001.ext,")
    print("file002.ext, etc.  You can insert %d to control the placement")
    print("and syntax of the frame number.")
    print()
    print("The optional range argument specifies which frames to extract.")
    print("You can give one or more ranges like 1-10, 5, -15 etc.  If")
    print("omitted, all frames are extracted.")
    sys.exit(1)

infile = sys.argv[1]
outfile = sys.argv[2]

frames = Interval(",".join(sys.argv[3:]))

try:
    # check if outfile contains a placeholder
    outfile % 1
except TypeError:
    file, ext = os.path.splitext(outfile)
    outfile = file + "%03d" + ext

ix = 1

im = Image.open(infile)

if html:
    file, ext = os.path.splitext(outfile)
    html = open(file+".html", "w")
    html.write("<html>\n<body>\n")

while True:

    if frames[ix]:
        im.save(outfile % ix)
        print(outfile % ix)

        if html:
            html.write("<img src='%s'><br>\n" % outfile % ix)

    try:
        im.seek(ix)
    except EOFError:
        break

    ix = ix + 1

if html:
    html.write("</body>\n</html>\n")

########NEW FILE########
__FILENAME__ = gifmaker
#!/usr/bin/env python
#
# The Python Imaging Library
# $Id$
#
# convert sequence format to GIF animation
#
# history:
#       97-01-03 fl     created
#
# Copyright (c) Secret Labs AB 1997.  All rights reserved.
# Copyright (c) Fredrik Lundh 1997.
#
# See the README file for information on usage and redistribution.
#

#
# For special purposes, you can import this module and call
# the makedelta or compress functions yourself.  For example,
# if you have an application that generates a sequence of
# images, you can convert it to a GIF animation using some-
# thing like the following code:
#
#       import Image
#       import gifmaker
#
#       sequence = []
#
#       # generate sequence
#       for i in range(100):
#           im = <generate image i>
#           sequence.append(im)
#
#       # write GIF animation
#       fp = open("out.gif", "wb")
#       gifmaker.makedelta(fp, sequence)
#       fp.close()
#
# Alternatively, use an iterator to generate the sequence, and
# write data directly to a socket.  Or something...
#

from __future__ import print_function

from PIL import Image, ImageChops

from PIL.GifImagePlugin import getheader, getdata

# --------------------------------------------------------------------
# sequence iterator

class image_sequence:
    def __init__(self, im):
        self.im = im
    def __getitem__(self, ix):
        try:
            if ix:
                self.im.seek(ix)
            return self.im
        except EOFError:
            raise IndexError # end of sequence

# --------------------------------------------------------------------
# straightforward delta encoding

def makedelta(fp, sequence):
    """Convert list of image frames to a GIF animation file"""

    frames = 0

    previous = None

    for im in sequence:

        #
        # FIXME: write graphics control block before each frame

        if not previous:

            # global header
            for s in getheader(im) + getdata(im):
                fp.write(s)

        else:

            # delta frame
            delta = ImageChops.subtract_modulo(im, previous)

            bbox = delta.getbbox()

            if bbox:

                # compress difference
                for s in getdata(im.crop(bbox), offset = bbox[:2]):
                    fp.write(s)

            else:
                # FIXME: what should we do in this case?
                pass

        previous = im.copy()

        frames = frames + 1

    fp.write(";")

    return frames

# --------------------------------------------------------------------
# main hack

def compress(infile, outfile):

    # open input image, and force loading of first frame
    im = Image.open(infile)
    im.load()

    # open output file
    fp = open(outfile, "wb")

    seq = image_sequence(im)

    makedelta(fp, seq)

    fp.close()


if __name__ == "__main__":

    import sys

    if len(sys.argv) < 3:
        print("GIFMAKER -- create GIF animations")
        print("Usage: gifmaker infile outfile")
        sys.exit(1)

    compress(sys.argv[1], sys.argv[2])

########NEW FILE########
__FILENAME__ = painter
#!/usr/bin/env python
#
# The Python Imaging Library
# $Id$
#
# this demo script illustrates pasting into an already displayed
# photoimage.  note that the current version of Tk updates the whole
# image everytime we paste, so to get decent performance, we split
# the image into a set of tiles.
#

try:
    from tkinter import *
except ImportError:
    from Tkinter import *

from PIL import Image, ImageTk
import sys

#
# painter widget

class PaintCanvas(Canvas):
    def __init__(self, master, image):
        Canvas.__init__(self, master, width=image.size[0], height=image.size[1])

        # fill the canvas
        self.tile = {}
        self.tilesize = tilesize = 32
        xsize, ysize = image.size
        for x in range(0, xsize, tilesize):
            for y in range(0, ysize, tilesize):
                box = x, y, min(xsize, x+tilesize), min(ysize, y+tilesize)
                tile = ImageTk.PhotoImage(image.crop(box))
                self.create_image(x, y, image=tile, anchor=NW)
                self.tile[(x,y)] = box, tile

        self.image = image

        self.bind("<B1-Motion>", self.paint)

    def paint(self, event):
        xy = event.x - 10, event.y - 10, event.x + 10, event.y + 10
        im = self.image.crop(xy)

        # process the image in some fashion
        im = im.convert("L")

        self.image.paste(im, xy)
        self.repair(xy)

    def repair(self, box):
        # update canvas
        dx = box[0] % self.tilesize
        dy = box[1] % self.tilesize
        for x in range(box[0]-dx, box[2]+1, self.tilesize):
            for y in range(box[1]-dy, box[3]+1, self.tilesize):
                try:
                    xy, tile = self.tile[(x, y)]
                    tile.paste(self.image.crop(xy))
                except KeyError:
                    pass # outside the image
        self.update_idletasks()

#
# main

root = Tk()

im = Image.open(sys.argv[1])

if im.mode != "RGB":
    im = im.convert("RGB")

PaintCanvas(root, im).pack()

root.mainloop()

########NEW FILE########
__FILENAME__ = pilconvert
#!/usr/bin/env python
#
# The Python Imaging Library.
# $Id$
#
# convert image files
#
# History:
# 0.1   96-04-20 fl     Created
# 0.2   96-10-04 fl     Use draft mode when converting images
# 0.3   96-12-30 fl     Optimize output (PNG, JPEG)
# 0.4   97-01-18 fl     Made optimize an option (PNG, JPEG)
# 0.5   98-12-30 fl     Fixed -f option (from Anthony Baxter)
#

from __future__ import print_function

import site
import getopt, string, sys

from PIL import Image

def usage():
    print("PIL Convert 0.5/1998-12-30 -- convert image files")
    print("Usage: pilconvert [option] infile outfile")
    print()
    print("Options:")
    print()
    print("  -c <format>  convert to format (default is given by extension)")
    print()
    print("  -g           convert to greyscale")
    print("  -p           convert to palette image (using standard palette)")
    print("  -r           convert to rgb")
    print()
    print("  -o           optimize output (trade speed for size)")
    print("  -q <value>   set compression quality (0-100, JPEG only)")
    print()
    print("  -f           list supported file formats")
    sys.exit(1)

if len(sys.argv) == 1:
    usage()

try:
    opt, argv = getopt.getopt(sys.argv[1:], "c:dfgopq:r")
except getopt.error as v:
    print(v)
    sys.exit(1)

format = None
convert = None

options = { }

for o, a in opt:

    if o == "-f":
        Image.init()
        id = sorted(Image.ID)
        print("Supported formats (* indicates output format):")
        for i in id:
            if i in Image.SAVE:
                print(i+"*", end=' ')
            else:
                print(i, end=' ')
        sys.exit(1)

    elif o == "-c":
        format = a

    if o == "-g":
        convert = "L"
    elif o == "-p":
        convert = "P"
    elif o == "-r":
        convert = "RGB"

    elif o == "-o":
        options["optimize"] = 1
    elif o == "-q":
        options["quality"] = string.atoi(a)

if len(argv) != 2:
    usage()

try:
    im = Image.open(argv[0])
    if convert and im.mode != convert:
        im.draft(convert, im.size)
        im = im.convert(convert)
    if format:
        im.save(argv[1], format, **options)
    else:
        im.save(argv[1], **options)
except:
    print("cannot convert image", end=' ')
    print("(%s:%s)" % (sys.exc_info()[0], sys.exc_info()[1]))

########NEW FILE########
__FILENAME__ = pildriver
#!/usr/bin/env python
"""PILdriver, an image-processing calculator using PIL.

An instance of class PILDriver is essentially a software stack machine
(Polish-notation interpreter) for sequencing PIL image
transformations.  The state of the instance is the interpreter stack.

The only method one will normally invoke after initialization is the
`execute' method.  This takes an argument list of tokens, pushes them
onto the instance's stack, and then tries to clear the stack by
successive evaluation of PILdriver operators.  Any part of the stack
not cleaned off persists and is part of the evaluation context for
the next call of the execute method.

PILDriver doesn't catch any exceptions, on the theory that these
are actually diagnostic information that should be interpreted by
the calling code.

When called as a script, the command-line arguments are passed to
a PILDriver instance.  If there are no command-line arguments, the
module runs an interactive interpreter, each line of which is split into
space-separated tokens and passed to the execute method.

In the method descriptions below, a first line beginning with the string
`usage:' means this method can be invoked with the token that follows
it.  Following <>-enclosed arguments describe how the method interprets
the entries on the stack.  Each argument specification begins with a
type specification: either `int', `float', `string', or `image'.

All operations consume their arguments off the stack (use `dup' to
keep copies around).  Use `verbose 1' to see the stack state displayed
before each operation.

Usage examples:

    `show crop 0 0 200 300 open test.png' loads test.png, crops out a portion
of its upper-left-hand corner and displays the cropped portion.

    `save rotated.png rotate 30 open test.tiff' loads test.tiff, rotates it
30 degrees, and saves the result as rotated.png (in PNG format).
"""
# by Eric S. Raymond <esr@thyrsus.com>
# $Id$

# TO DO:
# 1. Add PILFont capabilities, once that's documented.
# 2. Add PILDraw operations.
# 3. Add support for composing and decomposing multiple-image files.
#

from __future__ import print_function

from PIL import Image

class PILDriver:

    verbose = 0

    def do_verbose(self):
        """usage: verbose <int:num>

        Set verbosity flag from top of stack.
        """
        self.verbose = int(self.do_pop())

    # The evaluation stack (internal only)

    stack = []          # Stack of pending operations

    def push(self, item):
        "Push an argument onto the evaluation stack."
        self.stack = [item] + self.stack

    def top(self):
        "Return the top-of-stack element."
        return self.stack[0]

    # Stack manipulation (callable)

    def do_clear(self):
        """usage: clear

        Clear the stack.
        """
        self.stack = []

    def do_pop(self):
        """usage: pop

        Discard the top element on the stack.
        """
        top = self.stack[0]
        self.stack = self.stack[1:]
        return top

    def do_dup(self):
        """usage: dup

        Duplicate the top-of-stack item.
        """
        if hasattr(self, 'format'):     # If it's an image, do a real copy
            dup = self.stack[0].copy()
        else:
            dup = self.stack[0]
        self.stack = [dup] + self.stack

    def do_swap(self):
        """usage: swap

        Swap the top-of-stack item with the next one down.
        """
        self.stack = [self.stack[1], self.stack[0]] + self.stack[2:]

    # Image module functions (callable)

    def do_new(self):
        """usage: new <int:xsize> <int:ysize> <int:color>:

        Create and push a greyscale image of given size and color.
        """
        xsize = int(self.do_pop())
        ysize = int(self.do_pop())
        color = int(self.do_pop())
        self.push(Image.new("L", (xsize, ysize), color))

    def do_open(self):
        """usage: open <string:filename>

        Open the indicated image, read it, push the image on the stack.
        """
        self.push(Image.open(self.do_pop()))

    def do_blend(self):
        """usage: blend <image:pic1> <image:pic2> <float:alpha>

        Replace two images and an alpha with the blended image.
        """
        image1 = self.do_pop()
        image2 = self.do_pop()
        alpha = float(self.do_pop())
        self.push(Image.blend(image1, image2, alpha))

    def do_composite(self):
        """usage: composite <image:pic1> <image:pic2> <image:mask>

        Replace two images and a mask with their composite.
        """
        image1 = self.do_pop()
        image2 = self.do_pop()
        mask = self.do_pop()
        self.push(Image.composite(image1, image2, mask))

    def do_merge(self):
        """usage: merge <string:mode> <image:pic1> [<image:pic2> [<image:pic3> [<image:pic4>]]]

        Merge top-of stack images in a way described by the mode.
        """
        mode = self.do_pop()
        bandlist = []
        for band in mode:
            bandlist.append(self.do_pop())
        self.push(Image.merge(mode, bandlist))

    # Image class methods

    def do_convert(self):
        """usage: convert <string:mode> <image:pic1>

        Convert the top image to the given mode.
        """
        mode = self.do_pop()
        image = self.do_pop()
        self.push(image.convert(mode))

    def do_copy(self):
        """usage: copy <image:pic1>

        Make and push a true copy of the top image.
        """
        self.dup()

    def do_crop(self):
        """usage: crop <int:left> <int:upper> <int:right> <int:lower> <image:pic1>

        Crop and push a rectangular region from the current image.
        """
        left = int(self.do_pop())
        upper = int(self.do_pop())
        right = int(self.do_pop())
        lower = int(self.do_pop())
        image = self.do_pop()
        self.push(image.crop((left, upper, right, lower)))

    def do_draft(self):
        """usage: draft <string:mode> <int:xsize> <int:ysize>

        Configure the loader for a given mode and size.
        """
        mode = self.do_pop()
        xsize = int(self.do_pop())
        ysize = int(self.do_pop())
        self.push(self.draft(mode, (xsize, ysize)))

    def do_filter(self):
        """usage: filter <string:filtername> <image:pic1>

        Process the top image with the given filter.
        """
        from PIL import ImageFilter
        filter = eval("ImageFilter." + self.do_pop().upper())
        image = self.do_pop()
        self.push(image.filter(filter))

    def do_getbbox(self):
        """usage: getbbox

        Push left, upper, right, and lower pixel coordinates of the top image.
        """
        bounding_box = self.do_pop().getbbox()
        self.push(bounding_box[3])
        self.push(bounding_box[2])
        self.push(bounding_box[1])
        self.push(bounding_box[0])

    def do_getextrema(self):
        """usage: extrema

        Push minimum and maximum pixel values of the top image.
        """
        extrema = self.do_pop().extrema()
        self.push(extrema[1])
        self.push(extrema[0])

    def do_offset(self):
        """usage: offset <int:xoffset> <int:yoffset> <image:pic1>

        Offset the pixels in the top image.
        """
        xoff = int(self.do_pop())
        yoff = int(self.do_pop())
        image = self.do_pop()
        self.push(image.offset(xoff, yoff))

    def do_paste(self):
        """usage: paste <image:figure> <int:xoffset> <int:yoffset> <image:ground>

        Paste figure image into ground with upper left at given offsets.
        """
        figure = self.do_pop()
        xoff = int(self.do_pop())
        yoff = int(self.do_pop())
        ground = self.do_pop()
        if figure.mode == "RGBA":
            ground.paste(figure, (xoff, yoff), figure)
        else:
            ground.paste(figure, (xoff, yoff))
        self.push(ground)

    def do_resize(self):
        """usage: resize <int:xsize> <int:ysize> <image:pic1>

        Resize the top image.
        """
        ysize = int(self.do_pop())
        xsize = int(self.do_pop())
        image = self.do_pop()
        self.push(image.resize((xsize, ysize)))

    def do_rotate(self):
        """usage: rotate <int:angle> <image:pic1>

        Rotate image through a given angle
        """
        angle = int(self.do_pop())
        image = self.do_pop()
        self.push(image.rotate(angle))

    def do_save(self):
        """usage: save <string:filename> <image:pic1>

        Save image with default options.
        """
        filename = self.do_pop()
        image = self.do_pop()
        image.save(filename)

    def do_save2(self):
        """usage: save2 <string:filename> <string:options> <image:pic1>

        Save image with specified options.
        """
        filename = self.do_pop()
        options = self.do_pop()
        image = self.do_pop()
        image.save(filename, None, options)

    def do_show(self):
        """usage: show <image:pic1>

        Display and pop the top image.
        """
        self.do_pop().show()

    def do_thumbnail(self):
        """usage: thumbnail <int:xsize> <int:ysize> <image:pic1>

        Modify the top image in the stack to contain a thumbnail of itself.
        """
        ysize = int(self.do_pop())
        xsize = int(self.do_pop())
        self.top().thumbnail((xsize, ysize))

    def do_transpose(self):
        """usage: transpose <string:operator> <image:pic1>

        Transpose the top image.
        """
        transpose = self.do_pop().upper()
        image = self.do_pop()
        self.push(image.transpose(transpose))

    # Image attributes

    def do_format(self):
        """usage: format <image:pic1>

        Push the format of the top image onto the stack.
        """
        self.push(self.do_pop().format)

    def do_mode(self):
        """usage: mode <image:pic1>

        Push the mode of the top image onto the stack.
        """
        self.push(self.do_pop().mode)

    def do_size(self):
        """usage: size <image:pic1>

        Push the image size on the stack as (y, x).
        """
        size = self.do_pop().size
        self.push(size[0])
        self.push(size[1])

    # ImageChops operations

    def do_invert(self):
        """usage: invert <image:pic1>

        Invert the top image.
        """
        from PIL import ImageChops
        self.push(ImageChops.invert(self.do_pop()))

    def do_lighter(self):
        """usage: lighter <image:pic1> <image:pic2>

        Pop the two top images, push an image of the lighter pixels of both.
        """
        from PIL import ImageChops
        image1 = self.do_pop()
        image2 = self.do_pop()
        self.push(ImageChops.lighter(image1, image2))

    def do_darker(self):
        """usage: darker <image:pic1> <image:pic2>

        Pop the two top images, push an image of the darker pixels of both.
        """
        from PIL import ImageChops
        image1 = self.do_pop()
        image2 = self.do_pop()
        self.push(ImageChops.darker(image1, image2))

    def do_difference(self):
        """usage: difference <image:pic1> <image:pic2>

        Pop the two top images, push the difference image
        """
        from PIL import ImageChops
        image1 = self.do_pop()
        image2 = self.do_pop()
        self.push(ImageChops.difference(image1, image2))

    def do_multiply(self):
        """usage: multiply <image:pic1> <image:pic2>

        Pop the two top images, push the multiplication image.
        """
        from PIL import ImageChops
        image1 = self.do_pop()
        image2 = self.do_pop()
        self.push(ImageChops.multiply(image1, image2))

    def do_screen(self):
        """usage: screen <image:pic1> <image:pic2>

        Pop the two top images, superimpose their inverted versions.
        """
        from PIL import ImageChops
        image2 = self.do_pop()
        image1 = self.do_pop()
        self.push(ImageChops.screen(image1, image2))

    def do_add(self):
        """usage: add <image:pic1> <image:pic2> <int:offset> <float:scale>

        Pop the two top images, produce the scaled sum with offset.
        """
        from PIL import ImageChops
        image1 = self.do_pop()
        image2 = self.do_pop()
        scale = float(self.do_pop())
        offset = int(self.do_pop())
        self.push(ImageChops.add(image1, image2, scale, offset))

    def do_subtract(self):
        """usage: subtract <image:pic1> <image:pic2> <int:offset> <float:scale>

        Pop the two top images, produce the scaled difference with offset.
        """
        from PIL import ImageChops
        image1 = self.do_pop()
        image2 = self.do_pop()
        scale = float(self.do_pop())
        offset = int(self.do_pop())
        self.push(ImageChops.subtract(image1, image2, scale, offset))

    # ImageEnhance classes

    def do_color(self):
        """usage: color <image:pic1>

        Enhance color in the top image.
        """
        from PIL import ImageEnhance
        factor = float(self.do_pop())
        image = self.do_pop()
        enhancer = ImageEnhance.Color(image)
        self.push(enhancer.enhance(factor))

    def do_contrast(self):
        """usage: contrast <image:pic1>

        Enhance contrast in the top image.
        """
        from PIL import ImageEnhance
        factor = float(self.do_pop())
        image = self.do_pop()
        enhancer = ImageEnhance.Contrast(image)
        self.push(enhancer.enhance(factor))

    def do_brightness(self):
        """usage: brightness <image:pic1>

        Enhance brightness in the top image.
        """
        from PIL import ImageEnhance
        factor = float(self.do_pop())
        image = self.do_pop()
        enhancer = ImageEnhance.Brightness(image)
        self.push(enhancer.enhance(factor))

    def do_sharpness(self):
        """usage: sharpness <image:pic1>

        Enhance sharpness in the top image.
        """
        from PIL import ImageEnhance
        factor = float(self.do_pop())
        image = self.do_pop()
        enhancer = ImageEnhance.Sharpness(image)
        self.push(enhancer.enhance(factor))

    # The interpreter loop

    def execute(self, list):
        "Interpret a list of PILDriver commands."
        list.reverse()
        while len(list) > 0:
            self.push(list[0])
            list = list[1:]
            if self.verbose:
                print("Stack: " + repr(self.stack))
            top = self.top()
            if not isinstance(top, str):
                continue;
            funcname = "do_" + top
            if not hasattr(self, funcname):
                continue
            else:
                self.do_pop()
                func = getattr(self, funcname)
                func()

if __name__ == '__main__':
    import sys
    try:
        import readline
    except ImportError:
        pass # not available on all platforms

    # If we see command-line arguments, interpret them as a stack state
    # and execute.  Otherwise go interactive.

    driver = PILDriver()
    if len(sys.argv[1:]) > 0:
        driver.execute(sys.argv[1:])
    else:
        print("PILDriver says hello.")
        while True:
            try:
                if sys.version_info[0] >= 3:
                    line = input('pildriver> ');
                else:
                    line = raw_input('pildriver> ');
            except EOFError:
                print("\nPILDriver says goodbye.")
                break
            driver.execute(line.split())
            print(driver.stack)

# The following sets edit modes for GNU EMACS
# Local Variables:
# mode:python
# End:

########NEW FILE########
__FILENAME__ = pilfile
#!/usr/bin/env python
#
# The Python Imaging Library.
# $Id$
#
# a utility to identify image files
#
# this script identifies image files, extracting size and
# pixel mode information for known file formats.  Note that
# you don't need the PIL C extension to use this module.
#
# History:
# 0.0 1995-09-01 fl   Created
# 0.1 1996-05-18 fl   Modified options, added debugging mode
# 0.2 1996-12-29 fl   Added verify mode
# 0.3 1999-06-05 fl   Don't mess up on class exceptions (1.5.2 and later)
# 0.4 2003-09-30 fl   Expand wildcards on Windows; robustness tweaks
#

from __future__ import print_function

import site
import getopt, glob, sys

from PIL import Image

if len(sys.argv) == 1:
    print("PIL File 0.4/2003-09-30 -- identify image files")
    print("Usage: pilfile [option] files...")
    print("Options:")
    print("  -f  list supported file formats")
    print("  -i  show associated info and tile data")
    print("  -v  verify file headers")
    print("  -q  quiet, don't warn for unidentified/missing/broken files")
    sys.exit(1)

try:
    opt, args = getopt.getopt(sys.argv[1:], "fqivD")
except getopt.error as v:
    print(v)
    sys.exit(1)

verbose = quiet = verify = 0

for o, a in opt:
    if o == "-f":
        Image.init()
        id = sorted(Image.ID)
        print("Supported formats:")
        for i in id:
            print(i, end=' ')
        sys.exit(1)
    elif o == "-i":
        verbose = 1
    elif o == "-q":
        quiet = 1
    elif o == "-v":
        verify = 1
    elif o == "-D":
        Image.DEBUG = Image.DEBUG + 1

def globfix(files):
    # expand wildcards where necessary
    if sys.platform == "win32":
        out = []
        for file in files:
            if glob.has_magic(file):
                out.extend(glob.glob(file))
            else:
                out.append(file)
        return out
    return files

for file in globfix(args):
    try:
        im = Image.open(file)
        print("%s:" % file, im.format, "%dx%d" % im.size, im.mode, end=' ')
        if verbose:
            print(im.info, im.tile, end=' ')
        print()
        if verify:
            try:
                im.verify()
            except:
                if not quiet:
                    print("failed to verify image", end=' ')
                    print("(%s:%s)" % (sys.exc_info()[0], sys.exc_info()[1]))
    except IOError as v:
        if not quiet:
            print(file, "failed:", v)
    except:
        import traceback
        if not quiet:
            print(file, "failed:", "unexpected error")
            traceback.print_exc(file=sys.stdout)

########NEW FILE########
__FILENAME__ = pilfont
#!/usr/bin/env python
#
# The Python Imaging Library
# $Id$
#
# PIL raster font compiler
#
# history:
# 1997-08-25 fl   created
# 2002-03-10 fl   use "from PIL import"
#

from __future__ import print_function

VERSION = "0.4"

import glob, sys

# drivers
from PIL import BdfFontFile
from PIL import PcfFontFile

if len(sys.argv) <= 1:
    print("PILFONT", VERSION, "-- PIL font compiler.")
    print()
    print("Usage: pilfont fontfiles...")
    print()
    print("Convert given font files to the PIL raster font format.")
    print("This version of pilfont supports X BDF and PCF fonts.")
    sys.exit(1)

files = []
for f in sys.argv[1:]:
    files = files + glob.glob(f)

for f in files:

    print(f + "...", end=' ')

    try:

        fp = open(f, "rb")

        try:
            p = PcfFontFile.PcfFontFile(fp)
        except SyntaxError:
            fp.seek(0)
            p = BdfFontFile.BdfFontFile(fp)

        p.save(f)

    except (SyntaxError, IOError):
        print("failed")

    else:
        print("OK")

########NEW FILE########
__FILENAME__ = pilprint
#!/usr/bin/env python
#
# The Python Imaging Library.
# $Id$
#
# print image files to postscript printer
#
# History:
# 0.1   1996-04-20 fl   Created
# 0.2   1996-10-04 fl   Use draft mode when converting.
# 0.3   2003-05-06 fl   Fixed a typo or two.
#

from __future__ import print_function

VERSION = "pilprint 0.3/2003-05-05"

from PIL import Image
from PIL import PSDraw

letter = ( 1.0*72, 1.0*72, 7.5*72, 10.0*72 )

def description(file, image):
    import os
    title = os.path.splitext(os.path.split(file)[1])[0]
    format = " (%dx%d "
    if image.format:
        format = " (" + image.format + " %dx%d "
    return title + format % image.size + image.mode + ")"

import getopt, os, sys

if len(sys.argv) == 1:
    print("PIL Print 0.2a1/96-10-04 -- print image files")
    print("Usage: pilprint files...")
    print("Options:")
    print("  -c            colour printer (default is monochrome)")
    print("  -p            print via lpr (default is stdout)")
    print("  -P <printer>  same as -p but use given printer")
    sys.exit(1)

try:
    opt, argv = getopt.getopt(sys.argv[1:], "cdpP:")
except getopt.error as v:
    print(v)
    sys.exit(1)

printer = None # print to stdout
monochrome = 1 # reduce file size for most common case

for o, a in opt:
    if o == "-d":
        # debug: show available drivers
        Image.init()
        print(Image.ID)
        sys.exit(1)
    elif o == "-c":
        # colour printer
        monochrome = 0
    elif o == "-p":
        # default printer channel
        printer = "lpr"
    elif o == "-P":
        # printer channel
        printer = "lpr -P%s" % a

for file in argv:
    try:

        im = Image.open(file)

        title = description(file, im)

        if monochrome and im.mode not in ["1", "L"]:
            im.draft("L", im.size)
            im = im.convert("L")

        if printer:
            fp = os.popen(printer, "w")
        else:
            fp = sys.stdout

        ps = PSDraw.PSDraw(fp)

        ps.begin_document()
        ps.setfont("Helvetica-Narrow-Bold", 18)
        ps.text((letter[0], letter[3]+24), title)
        ps.setfont("Helvetica-Narrow-Bold", 8)
        ps.text((letter[0], letter[1]-30), VERSION)
        ps.image(letter, im)
        ps.end_document()

    except:
        print("cannot print image", end=' ')
        print("(%s:%s)" % (sys.exc_info()[0], sys.exc_info()[1]))

########NEW FILE########
__FILENAME__ = player
#!/usr/bin/env python
#
# The Python Imaging Library
# $Id$
#

from __future__ import print_function

try:
    from tkinter import *
except ImportError:
    from Tkinter import *

from PIL import Image, ImageTk
import sys


Image.DEBUG = 0


# --------------------------------------------------------------------
# experimental: support ARG animation scripts

import ArgImagePlugin

def applet_hook(animation, images):
    app = animation(animation_display, images)
    app.run()

ArgImagePlugin.APPLET_HOOK = applet_hook

class AppletDisplay:
    def __init__(self, ui):
        self.__ui = ui
    def paste(self, im, bbox):
        self.__ui.image.paste(im, bbox)
    def update(self):
        self.__ui.update_idletasks()

# --------------------------------------------------------------------
# an image animation player

class UI(Label):

    def __init__(self, master, im):
        if isinstance(im, list):
            # list of images
            self.im = im[1:]
            im = self.im[0]
        else:
            # sequence
            self.im = im

        if im.mode == "1":
            self.image = ImageTk.BitmapImage(im, foreground="white")
        else:
            self.image = ImageTk.PhotoImage(im)

        # APPLET SUPPORT (very crude, and not 100% safe)
        global animation_display
        animation_display = AppletDisplay(self)

        Label.__init__(self, master, image=self.image, bg="black", bd=0)

        self.update()

        try:
            duration = im.info["duration"]
        except KeyError:
            duration = 100
        self.after(duration, self.next)

    def next(self):

        if isinstance(self.im, list):

            try:
                im = self.im[0]
                del self.im[0]
                self.image.paste(im)
            except IndexError:
                return # end of list

        else:

            try:
                im = self.im
                im.seek(im.tell() + 1)
                self.image.paste(im)
            except EOFError:
                return # end of file

        try:
            duration = im.info["duration"]
        except KeyError:
            duration = 100
        self.after(duration, self.next)

        self.update_idletasks()


# --------------------------------------------------------------------
# script interface

if __name__ == "__main__":

    if not sys.argv[1:]:
        print("Syntax: python player.py imagefile(s)")
        sys.exit(1)

    filename = sys.argv[1]

    root = Tk()
    root.title(filename)

    if len(sys.argv) > 2:
        # list of images
        print("loading...")
        im = []
        for filename in sys.argv[1:]:
            im.append(Image.open(filename))
    else:
        # sequence
        im = Image.open(filename)

    UI(root, im).pack()

    root.mainloop()

########NEW FILE########
__FILENAME__ = thresholder
#!/usr/bin/env python
#
# The Python Imaging Library
# $Id$
#
# this demo script illustrates how a 1-bit BitmapImage can be used
# as a dynamically updated overlay
#

try:
    from tkinter import *
except ImportError:
    from Tkinter import *

from PIL import Image, ImageTk
import sys

#
# an image viewer

class UI(Frame):
    def __init__(self, master, im, value = 128):
        Frame.__init__(self, master)

        self.image = im
        self.value = value

        self.canvas = Canvas(self, width=im.size[0], height=im.size[1])
        self.backdrop = ImageTk.PhotoImage(im)
        self.canvas.create_image(0, 0, image=self.backdrop, anchor=NW)
        self.canvas.pack()

        scale = Scale(self, orient=HORIZONTAL, from_=0, to=255,
                      resolution=1, command=self.update, length=256)
        scale.set(value)
        scale.bind("<ButtonRelease-1>", self.redraw)
        scale.pack()

        # uncomment the following line for instant feedback (might
        # be too slow on some platforms)
        # self.redraw()

    def update(self, value):
        self.value = eval(value)

        self.redraw()

    def redraw(self, event = None):

        # create overlay (note the explicit conversion to mode "1")
        im = self.image.point(lambda v,t=self.value: v>=t, "1")
        self.overlay = ImageTk.BitmapImage(im, foreground="green")

        # update canvas
        self.canvas.delete("overlay")
        self.canvas.create_image(0, 0, image=self.overlay, anchor=NW,
                tags="overlay")

# --------------------------------------------------------------------
# main

root = Tk()

im = Image.open(sys.argv[1])

if im.mode != "L":
    im = im.convert("L")

# im.thumbnail((320,200))

UI(root, im).pack()

root.mainloop()

########NEW FILE########
__FILENAME__ = viewer
#!/usr/bin/env python
#
# The Python Imaging Library
# $Id$
#

from __future__ import print_function

try:
    from tkinter import *
except ImportError:
    from Tkinter import *

from PIL import Image, ImageTk

#
# an image viewer

class UI(Label):

    def __init__(self, master, im):

        if im.mode == "1":
            # bitmap image
            self.image = ImageTk.BitmapImage(im, foreground="white")
            Label.__init__(self, master, image=self.image, bg="black", bd=0)

        else:
            # photo image
            self.image = ImageTk.PhotoImage(im)
            Label.__init__(self, master, image=self.image, bd=0)

#
# script interface

if __name__ == "__main__":

    import sys

    if not sys.argv[1:]:
        print("Syntax: python viewer.py imagefile")
        sys.exit(1)

    filename = sys.argv[1]

    root = Tk()
    root.title(filename)

    im = Image.open(filename)

    UI(root, im).pack()

    root.mainloop()

########NEW FILE########
__FILENAME__ = selftest
# minimal sanity check
from __future__ import print_function

import sys
import os

if "--installed" in sys.argv:
    sys_path_0 = sys.path[0]
    del sys.path[0]

from PIL import Image, ImageDraw, ImageFilter, ImageMath

if "--installed" in sys.argv:
    sys.path.insert(0, sys_path_0)

ROOT = "."

try:
    Image.core.ping
except ImportError as v:
    print("***", v)
    sys.exit()
except AttributeError:
    pass


def _info(im):
    im.load()
    return im.format, im.mode, im.size


def testimage():
    """
    PIL lets you create in-memory images with various pixel types:

    >>> im = Image.new("1", (128, 128)) # monochrome
    >>> _info(im)
    (None, '1', (128, 128))
    >>> _info(Image.new("L", (128, 128))) # grayscale (luminance)
    (None, 'L', (128, 128))
    >>> _info(Image.new("P", (128, 128))) # palette
    (None, 'P', (128, 128))
    >>> _info(Image.new("RGB", (128, 128))) # truecolor
    (None, 'RGB', (128, 128))
    >>> _info(Image.new("I", (128, 128))) # 32-bit integer
    (None, 'I', (128, 128))
    >>> _info(Image.new("F", (128, 128))) # 32-bit floating point
    (None, 'F', (128, 128))

    Or open existing files:

    >>> im = Image.open(os.path.join(ROOT, "Images/lena.gif"))
    >>> _info(im)
    ('GIF', 'P', (128, 128))
    >>> _info(Image.open(os.path.join(ROOT, "Images/lena.ppm")))
    ('PPM', 'RGB', (128, 128))
    >>> try:
    ...  _info(Image.open(os.path.join(ROOT, "Images/lena.jpg")))
    ... except IOError as v:
    ...  print(v)
    ('JPEG', 'RGB', (128, 128))

    PIL doesn't actually load the image data until it's needed,
    or you call the "load" method:

    >>> im = Image.open(os.path.join(ROOT, "Images/lena.ppm"))
    >>> print(im.im) # internal image attribute
    None
    >>> a = im.load()
    >>> type(im.im) # doctest: +ELLIPSIS
    <... '...ImagingCore'>

    You can apply many different operations on images.  Most
    operations return a new image:

    >>> im = Image.open(os.path.join(ROOT, "Images/lena.ppm"))
    >>> _info(im.convert("L"))
    (None, 'L', (128, 128))
    >>> _info(im.copy())
    (None, 'RGB', (128, 128))
    >>> _info(im.crop((32, 32, 96, 96)))
    (None, 'RGB', (64, 64))
    >>> _info(im.filter(ImageFilter.BLUR))
    (None, 'RGB', (128, 128))
    >>> im.getbands()
    ('R', 'G', 'B')
    >>> im.getbbox()
    (0, 0, 128, 128)
    >>> len(im.getdata())
    16384
    >>> im.getextrema()
    ((61, 255), (26, 234), (44, 223))
    >>> im.getpixel((0, 0))
    (223, 162, 133)
    >>> len(im.getprojection())
    2
    >>> len(im.histogram())
    768
    >>> _info(im.point(list(range(256))*3))
    (None, 'RGB', (128, 128))
    >>> _info(im.resize((64, 64)))
    (None, 'RGB', (64, 64))
    >>> _info(im.rotate(45))
    (None, 'RGB', (128, 128))
    >>> [_info(ch) for ch in im.split()]
    [(None, 'L', (128, 128)), (None, 'L', (128, 128)), (None, 'L', (128, 128))]
    >>> len(im.convert("1").tobitmap())
    10456
    >>> len(im.tobytes())
    49152
    >>> _info(im.transform((512, 512), Image.AFFINE, (1,0,0,0,1,0)))
    (None, 'RGB', (512, 512))
    >>> _info(im.transform((512, 512), Image.EXTENT, (32,32,96,96)))
    (None, 'RGB', (512, 512))

    The ImageDraw module lets you draw stuff in raster images:

    >>> im = Image.new("L", (128, 128), 64)
    >>> d = ImageDraw.ImageDraw(im)
    >>> d.line((0, 0, 128, 128), fill=128)
    >>> d.line((0, 128, 128, 0), fill=128)
    >>> im.getextrema()
    (64, 128)

    In 1.1.4, you can specify colors in a number of ways:

    >>> xy = 0, 0, 128, 128
    >>> im = Image.new("RGB", (128, 128), 0)
    >>> d = ImageDraw.ImageDraw(im)
    >>> d.rectangle(xy, "#f00")
    >>> im.getpixel((0, 0))
    (255, 0, 0)
    >>> d.rectangle(xy, "#ff0000")
    >>> im.getpixel((0, 0))
    (255, 0, 0)
    >>> d.rectangle(xy, "rgb(255,0,0)")
    >>> im.getpixel((0, 0))
    (255, 0, 0)
    >>> d.rectangle(xy, "rgb(100%,0%,0%)")
    >>> im.getpixel((0, 0))
    (255, 0, 0)
    >>> d.rectangle(xy, "hsl(0, 100%, 50%)")
    >>> im.getpixel((0, 0))
    (255, 0, 0)
    >>> d.rectangle(xy, "red")
    >>> im.getpixel((0, 0))
    (255, 0, 0)

    In 1.1.6, you can use the ImageMath module to do image
    calculations.

    >>> im = ImageMath.eval("float(im + 20)", im=im.convert("L"))
    >>> im.mode, im.size
    ('F', (128, 128))

    PIL can do many other things, but I'll leave that for another
    day.  If you're curious, check the handbook, available from:

        http://www.pythonware.com

    Cheers /F
    """


def check_module(feature, module):
    try:
        __import__(module)
    except ImportError:
        print("***", feature, "support not installed")
    else:
        print("---", feature, "support ok")


def check_codec(feature, codec):
    if codec + "_encoder" not in dir(Image.core):
        print("***", feature, "support not installed")
    else:
        print("---", feature, "support ok")


if __name__ == "__main__":
    # check build sanity

    exit_status = 0

    print("-"*68)
    print("Pillow", Image.PILLOW_VERSION, "TEST SUMMARY ")
    print("-"*68)
    print("Python modules loaded from", os.path.dirname(Image.__file__))
    print("Binary modules loaded from", os.path.dirname(Image.core.__file__))
    print("-"*68)
    check_module("PIL CORE", "PIL._imaging")
    check_module("TKINTER", "PIL._imagingtk")
    check_codec("JPEG", "jpeg")
    check_codec("JPEG 2000", "jpeg2k")
    check_codec("ZLIB (PNG/ZIP)", "zip")
    check_codec("LIBTIFF", "libtiff")
    check_module("FREETYPE2", "PIL._imagingft")
    check_module("LITTLECMS2", "PIL._imagingcms")
    check_module("WEBP", "PIL._webp")
    try:
        from PIL import _webp
        if _webp.WebPDecoderBuggyAlpha():
            print("***", "Transparent WEBP", "support not installed")
        else:
            print("---", "Transparent WEBP", "support ok")
    except Exception:
        pass
    print("-"*68)

    # use doctest to make sure the test program behaves as documented!
    import doctest
    import selftest
    print("Running selftest:")
    status = doctest.testmod(selftest)
    if status[0]:
        print("*** %s tests of %d failed." % status)
        exit_status = 1
    else:
        print("--- %s tests passed." % status[1])

    sys.exit(exit_status)

########NEW FILE########
__FILENAME__ = bench_cffi_access
from tester import *

# not running this test by default. No DOS against travis.

from PIL import PyAccess
from PIL import Image

import time

def iterate_get(size, access):
    (w,h) = size
    for x in range(w):
        for y in range(h):
            access[(x,y)]

def iterate_set(size, access):
    (w,h) = size
    for x in range(w):
        for y in range(h):
            access[(x,y)] = (x %256,y%256,0)

def timer(func, label, *args):
    iterations = 5000
    starttime = time.time()
    for x in range(iterations):
        func(*args)
        if time.time()-starttime > 10:
            print ("%s: breaking at %s iterations, %.6f per iteration"%(label, x+1, (time.time()-starttime)/(x+1.0)))
            break
    if x == iterations-1:
        endtime = time.time()
        print ("%s: %.4f s  %.6f per iteration" %(label, endtime-starttime, (endtime-starttime)/(x+1.0)))

def test_direct():
    im = lena()
    im.load()
    #im = Image.new( "RGB", (2000,2000), (1,3,2))
    caccess = im.im.pixel_access(False)
    access = PyAccess.new(im, False)

    assert_equal(caccess[(0,0)], access[(0,0)])

    print ("Size: %sx%s" % im.size)
    timer(iterate_get, 'PyAccess - get', im.size, access)
    timer(iterate_set, 'PyAccess - set', im.size, access)
    timer(iterate_get, 'C-api - get', im.size, caccess)
    timer(iterate_set, 'C-api - set', im.size, caccess)
    
    

    

########NEW FILE########
__FILENAME__ = bench_get
import sys
sys.path.insert(0, ".")

import tester
import timeit

def bench(mode):
    im = tester.lena(mode)
    get = im.im.getpixel
    xy = 50, 50 # position shouldn't really matter
    t0 = timeit.default_timer()
    for i in range(1000000):
        get(xy)
    print(mode, timeit.default_timer() - t0, "us")

bench("L")
bench("I")
bench("I;16")
bench("F")
bench("RGB")

########NEW FILE########
__FILENAME__ = cms_test
# PyCMSTests.py
# Examples of how to use pyCMS, as well as tests to verify it works properly
# By Kevin Cazabon (kevin@cazabon.com)

# Imports
import os
from PIL import Image
from PIL import ImageCms

# import PyCMSError separately so we can catch it
PyCMSError = ImageCms.PyCMSError

#######################################################################
# Configuration:
#######################################################################
# set this to the image you want to test with
IMAGE = "c:\\temp\\test.tif"

# set this to where you want to save the output images
OUTPUTDIR = "c:\\temp\\"

# set these to two different ICC profiles, one for input, one for output
# set the corresponding mode to the proper PIL mode for that profile
INPUT_PROFILE = "c:\\temp\\profiles\\sRGB.icm"
INMODE = "RGB"

OUTPUT_PROFILE = "c:\\temp\\profiles\\genericRGB.icm"
OUTMODE = "RGB"

PROOF_PROFILE = "c:\\temp\\profiles\\monitor.icm"

# set to True to show() images, False to save them into OUTPUT_DIRECTORY
SHOW = False

# Tests you can enable/disable
TEST_error_catching                 = True
TEST_profileToProfile               = True
TEST_profileToProfile_inPlace       = True
TEST_buildTransform                 = True
TEST_buildTransformFromOpenProfiles = True
TEST_buildProofTransform            = True
TEST_getProfileInfo                 = True
TEST_misc                           = False

#######################################################################
# helper functions
#######################################################################
def outputImage(im, funcName = None):
    # save or display the image, depending on value of SHOW_IMAGES
    if SHOW:
        im.show()
    else:
        im.save(os.path.join(OUTPUTDIR, "%s.tif" %funcName))


#######################################################################
# The tests themselves
#######################################################################

if TEST_error_catching:
    im = Image.open(IMAGE)
    try:
        #neither of these proifles exists (unless you make them), so we should
        # get an error
        imOut = ImageCms.profileToProfile(im, "missingProfile.icm", "cmyk.icm")

    except PyCMSError as reason:
        print("We caught a PyCMSError: %s\n\n" %reason)

    print("error catching test completed successfully (if you see the message \
    above that we caught the error).")

if TEST_profileToProfile:
    # open the image file using the standard PIL function Image.open()
    im = Image.open(IMAGE)

    # send the image, input/output profiles, and rendering intent to
    # ImageCms.profileToProfile()
    imOut = ImageCms.profileToProfile(im, INPUT_PROFILE, OUTPUT_PROFILE, \
                outputMode = OUTMODE)

    # now that the image is converted, save or display it
    outputImage(imOut, "profileToProfile")

    print("profileToProfile test completed successfully.")

if TEST_profileToProfile_inPlace:
    # we'll do the same test as profileToProfile, but modify im in place
    # instead of getting a new image returned to us
    im = Image.open(IMAGE)

    # send the image to ImageCms.profileToProfile(), specifying inPlace = True
    result = ImageCms.profileToProfile(im, INPUT_PROFILE, OUTPUT_PROFILE, \
                outputMode = OUTMODE, inPlace = True)

    # now that the image is converted, save or display it
    if result is None:
        # this is the normal result when modifying in-place
        outputImage(im, "profileToProfile_inPlace")
    else:
        # something failed...
        print("profileToProfile in-place failed: %s" %result)

    print("profileToProfile in-place test completed successfully.")

if TEST_buildTransform:
    # make a transform using the input and output profile path strings
    transform = ImageCms.buildTransform(INPUT_PROFILE, OUTPUT_PROFILE, INMODE, \
                OUTMODE)

    # now, use the trnsform to convert a couple images
    im = Image.open(IMAGE)

    # transform im normally
    im2 = ImageCms.applyTransform(im, transform)
    outputImage(im2, "buildTransform")

    # then transform it again using the same transform, this time in-place.
    result = ImageCms.applyTransform(im, transform, inPlace = True)
    outputImage(im, "buildTransform_inPlace")

    print("buildTransform test completed successfully.")

    # and, to clean up a bit, delete the transform
    # this should call the C destructor for the transform structure.
    # Python should also do this automatically when it goes out of scope.
    del(transform)

if TEST_buildTransformFromOpenProfiles:
    # we'll actually test a couple profile open/creation functions here too

    # first, get a handle to an input profile, in this case we'll create
    # an sRGB profile on the fly:
    inputProfile = ImageCms.createProfile("sRGB")

    # then, get a handle to the output profile
    outputProfile = ImageCms.getOpenProfile(OUTPUT_PROFILE)

    # make a transform from these
    transform = ImageCms.buildTransformFromOpenProfiles(inputProfile, \
                outputProfile, INMODE, OUTMODE)

    # now, use the trnsform to convert a couple images
    im = Image.open(IMAGE)

    # transform im normally
    im2 = ImageCms.applyTransform(im, transform)
    outputImage(im2, "buildTransformFromOpenProfiles")

    # then do it again using the same transform, this time in-place.
    result = ImageCms.applyTransform(im, transform, inPlace = True)
    outputImage(im, "buildTransformFromOpenProfiles_inPlace")

    print("buildTransformFromOpenProfiles test completed successfully.")

    # and, to clean up a bit, delete the transform
    # this should call the C destructor for the each item.
    # Python should also do this automatically when it goes out of scope.
    del(inputProfile)
    del(outputProfile)
    del(transform)

if TEST_buildProofTransform:
    # make a transform using the input and output and proof profile path
    # strings
    # images converted with this transform will simulate the appearance
    # of the output device while actually being displayed/proofed on the
    # proof device.  This usually means a monitor, but can also mean
    # other proof-printers like dye-sub, etc.
    transform = ImageCms.buildProofTransform(INPUT_PROFILE, OUTPUT_PROFILE, \
                PROOF_PROFILE, INMODE, OUTMODE)

    # now, use the trnsform to convert a couple images
    im = Image.open(IMAGE)

    # transform im normally
    im2 = ImageCms.applyTransform(im, transform)
    outputImage(im2, "buildProofTransform")

    # then transform it again using the same transform, this time in-place.
    result = ImageCms.applyTransform(im, transform, inPlace = True)
    outputImage(im, "buildProofTransform_inPlace")

    print("buildProofTransform test completed successfully.")

    # and, to clean up a bit, delete the transform
    # this should call the C destructor for the transform structure.
    # Python should also do this automatically when it goes out of scope.
    del(transform)

if TEST_getProfileInfo:
    # get a profile handle
    profile = ImageCms.getOpenProfile(INPUT_PROFILE)

    # lets print some info about our input profile:
    print("Profile name (retrieved from profile string path name): %s" %ImageCms.getProfileName(INPUT_PROFILE))

    # or, you could do the same thing using a profile handle as the arg
    print("Profile name (retrieved from profile handle): %s" %ImageCms.getProfileName(profile))

    # now lets get the embedded "info" tag contents
    # once again, you can use a path to a profile, or a profile handle
    print("Profile info (retrieved from profile handle): %s" %ImageCms.getProfileInfo(profile))

    # and what's the default intent of this profile?
    print("The default intent is (this will be an integer): %d" %(ImageCms.getDefaultIntent(profile)))

    # Hmmmm... but does this profile support INTENT_ABSOLUTE_COLORIMETRIC?
    print("Does it support INTENT_ABSOLUTE_COLORIMETRIC?: (1 is yes, -1 is no): %s" \
            %ImageCms.isIntentSupported(profile, ImageCms.INTENT_ABSOLUTE_COLORIMETRIC, \
            ImageCms.DIRECTION_INPUT))

    print("getProfileInfo test completed successfully.")

if TEST_misc:
    # test the versions, about, and copyright functions
    print("Versions: %s" %str(ImageCms.versions()))
    print("About:\n\n%s" %ImageCms.about())
    print("Copyright:\n\n%s" %ImageCms.copyright())

    print("misc test completed successfully.")


########NEW FILE########
__FILENAME__ = crash_ttf_memory_error
from PIL import Image, ImageFont, ImageDraw

font = "../pil-archive/memory-error-2.ttf"

s = "Test Text"
f = ImageFont.truetype(font, 64, index=0, encoding="unicode")
w, h = f.getsize(s)
i = Image.new("RGB", (500, h), "white")
d = ImageDraw.Draw(i)

# this line causes a MemoryError
d.text((0,0), s, font=f, fill=0)

i.show()

########NEW FILE########
__FILENAME__ = import_all
import sys
sys.path.insert(0, ".")

import glob, os
import traceback

for file in glob.glob("PIL/*.py"):
    module = os.path.basename(file)[:-3]
    try:
        exec("from PIL import " + module)
    except (ImportError, SyntaxError):
        print("===", "failed to import", module)
        traceback.print_exc()

########NEW FILE########
__FILENAME__ = large_memory_numpy_test
from tester import *

# This test is not run automatically.
#
# It requires > 2gb memory for the >2 gigapixel image generated in the
# second test.  Running this automatically would amount to a denial of
# service on our testing infrastructure.  I expect this test to fail
# on any 32 bit machine, as well as any smallish things (like
# raspberrypis).

from PIL import Image
try:
    import numpy as np
except:
    skip()
    
ydim = 32769
xdim = 48000
f = tempfile('temp.png')

def _write_png(xdim,ydim):
    dtype = np.uint8
    a = np.zeros((xdim, ydim), dtype=dtype)
    im = Image.fromarray(a, 'L')
    im.save(f)
    success()

def test_large():
    """ succeeded prepatch"""
    _write_png(xdim,ydim)
def test_2gpx():
    """failed prepatch"""
    _write_png(xdim,xdim)





########NEW FILE########
__FILENAME__ = large_memory_test
from tester import *

# This test is not run automatically.
#
# It requires > 2gb memory for the >2 gigapixel image generated in the
# second test.  Running this automatically would amount to a denial of
# service on our testing infrastructure.  I expect this test to fail
# on any 32 bit machine, as well as any smallish things (like
# raspberrypis). It does succeed on a 3gb Ubuntu 12.04x64 VM on python
# 2.7 an 3.2

from PIL import Image
ydim = 32769
xdim = 48000
f = tempfile('temp.png')

def _write_png(xdim,ydim):
    im = Image.new('L',(xdim,ydim),(0))
    im.save(f)
    success()

def test_large():
    """ succeeded prepatch"""
    _write_png(xdim,ydim)
def test_2gpx():
    """failed prepatch"""
    _write_png(xdim,xdim)

########NEW FILE########
__FILENAME__ = make_hash
# brute-force search for access descriptor hash table

import random

modes = [
    "1",
    "L", "LA",
    "I", "I;16", "I;16L", "I;16B", "I;32L", "I;32B",
    "F",
    "P", "PA",
    "RGB", "RGBA", "RGBa", "RGBX",
    "CMYK",
    "YCbCr",
    ]

def hash(s, i):
    # djb2 hash: multiply by 33 and xor character
    for c in s:
        i = (((i<<5) + i) ^ ord(c)) & 0xffffffff
    return i

def check(size, i0):
    h = [None] * size
    for m in modes:
        i = hash(m, i0)
        i = i % size
        if h[i]:
            return 0
        h[i] = m
    return h

min_start = 0

# 1) find the smallest table size with no collisions
for min_size in range(len(modes), 16384):
    if check(min_size, 0):
        print(len(modes), "modes fit in", min_size, "slots")
        break

# 2) see if we can do better with a different initial value
for i0 in range(65556):
    for size in range(1, min_size):
        if check(size, i0):
            if size < min_size:
                print(len(modes), "modes fit in", size, "slots with start", i0)
                min_size = size
                min_start = i0

print()

# print check(min_size, min_start)

print("#define ACCESS_TABLE_SIZE", min_size)
print("#define ACCESS_TABLE_HASH", min_start)

# for m in modes:
#     print m, "=>", hash(m, min_start) % min_size

########NEW FILE########
__FILENAME__ = run
from __future__ import print_function

# minimal test runner

import glob
import os
import os.path
import re
import sys
import tempfile

try:
    root = os.path.dirname(__file__)
except NameError:
    root = os.path.dirname(sys.argv[0])

if not os.path.isfile("PIL/Image.py"):
    print("***", "please run this script from the PIL development directory as")
    print("***", "$ python Tests/run.py")
    sys.exit(1)

print("-"*68)

python_options = []
tester_options = []

if "--installed" not in sys.argv:
    os.environ["PYTHONPATH"] = "."

if "--coverage" in sys.argv:
    tester_options.append("--coverage")

if "--log" in sys.argv:
    tester_options.append("--log")

files = glob.glob(os.path.join(root, "test_*.py"))
files.sort()

success = failure = 0
include = [x for x in sys.argv[1:] if x[:2] != "--"]
skipped = []
failed = []

python_options = " ".join(python_options)
tester_options = " ".join(tester_options)

ignore_re = re.compile('^ignore: (.*)$', re.MULTILINE)

for file in files:
    test, ext = os.path.splitext(os.path.basename(file))
    if include and test not in include:
        continue
    print("running", test, "...")
    # 2>&1 works on unix and on modern windowses.  we might care about
    # very old Python versions, but not ancient microsoft products :-)
    out = os.popen("%s %s -u %s %s 2>&1" % (
        sys.executable, python_options, file, tester_options
        ))
    result = out.read()

    result_lines = result.splitlines()
    if len(result_lines):
        if result_lines[0] == "ignore_all_except_last_line":
            result = result_lines[-1]

    # Extract any ignore patterns
    ignore_pats = ignore_re.findall(result)
    result = ignore_re.sub('', result)

    try:
        def fix_re(p):
            if not p.startswith('^'):
                p = '^' + p
            if not p.endswith('$'):
                p = p + '$'
            return p

        ignore_res = [re.compile(fix_re(p), re.MULTILINE) for p in ignore_pats]
    except:
        print('(bad ignore patterns %r)' % ignore_pats)
        ignore_res = []

    for r in ignore_res:
        result = r.sub('', result)

    result = result.strip()

    if result == "ok":
        result = None
    elif result == "skip":
        print("---", "skipped")  # FIXME: driver should include a reason
        skipped.append(test)
        continue
    elif not result:
        result = "(no output)"
    status = out.close()
    if status or result:
        if status:
            print("=== error", status)
        if result:
            if result[-3:] == "\nok":
                # if there's an ok at the end, it's not really ok
                result = result[:-3]
            print(result)
        failed.append(test)
    else:
        success = success + 1

print("-"*68)

temp_root = os.path.join(tempfile.gettempdir(), 'pillow-tests')
tempfiles = glob.glob(os.path.join(temp_root, "temp_*"))
if tempfiles:
    print("===", "remaining temporary files")
    for file in tempfiles:
        print(file)
    print("-"*68)


def tests(n):
    if n == 1:
        return "1 test"
    else:
        return "%d tests" % n

if skipped:
    print("---", tests(len(skipped)), "skipped:")
    print(", ".join(skipped))
if failed:
    failure = len(failed)
    print("***", tests(failure), "of", (success + failure), "failed:")
    print(", ".join(failed))
    sys.exit(1)
else:
    print(tests(success), "passed.")

########NEW FILE########
__FILENAME__ = show_icc
import sys
sys.path.insert(0, ".")

from PIL import Image
from PIL import ImageCms

try:
    filename = sys.argv[1]
except IndexError:
    filename = "../pil-archive/cmyk.jpg"

i = Image.open(filename)

print(i.format)
print(i.mode)
print(i.size)
print(i.tile)

p = ImageCms.getMemoryProfile(i.info["icc_profile"])

print(repr(p.product_name))
print(repr(p.product_info))

o = ImageCms.createProfile("sRGB")
t = ImageCms.buildTransformFromOpenProfiles(p, o, i.mode, "RGB")
i = ImageCms.applyTransform(i, t)

i.show()

########NEW FILE########
__FILENAME__ = show_mcidas
import sys
sys.path.insert(0, ".")

from PIL import Image
from PIL import ImageMath

try:
    filename = sys.argv[1]
except IndexError:
    filename = "../pil-archive/goes12.2005.140.190925.BAND_01.mcidas"
    # filename = "../pil-archive/goes12.2005.140.190925.BAND_01.im"

im = Image.open(filename)

print(im.format)
print(im.mode)
print(im.size)
print(im.tile)

lo, hi = im.getextrema()

print("map", lo, hi, "->", end=' ')
im = ImageMath.eval("convert(im*255/hi, 'L')", im=im, hi=hi)
print(im.getextrema())

im.show()

########NEW FILE########
__FILENAME__ = tester
from __future__ import print_function

# require that deprecation warnings are triggered
import warnings
warnings.simplefilter('default')
# temporarily turn off resource warnings that warn about unclosed
# files in the test scripts.
try:
    warnings.filterwarnings("ignore", category=ResourceWarning)
except NameError:
    # we expect a NameError on py2.x, since it doesn't have ResourceWarnings.
    pass

import sys
py3 = (sys.version_info >= (3, 0))

# some test helpers

_target = None
_tempfiles = []
_logfile = None


def success():
    import sys
    success.count += 1
    if _logfile:
        print(sys.argv[0], success.count, failure.count, file=_logfile)
    return True


def failure(msg=None, frame=None):
    import sys
    import linecache
    failure.count += 1
    if _target:
        if frame is None:
            frame = sys._getframe()
            while frame.f_globals.get("__name__") != _target.__name__:
                frame = frame.f_back
        location = (frame.f_code.co_filename, frame.f_lineno)
        prefix = "%s:%d: " % location
        line = linecache.getline(*location)
        print(prefix + line.strip() + " failed:")
    if msg:
        print("- " + msg)
    if _logfile:
        print(sys.argv[0], success.count, failure.count, file=_logfile)
    return False

success.count = failure.count = 0


# predicates

def assert_true(v, msg=None):
    if v:
        success()
    else:
        failure(msg or "got %r, expected true value" % v)


def assert_false(v, msg=None):
    if v:
        failure(msg or "got %r, expected false value" % v)
    else:
        success()


def assert_equal(a, b, msg=None):
    if a == b:
        success()
    else:
        failure(msg or "got %r, expected %r" % (a, b))


def assert_almost_equal(a, b, msg=None, eps=1e-6):
    if abs(a-b) < eps:
        success()
    else:
        failure(msg or "got %r, expected %r" % (a, b))


def assert_deep_equal(a, b, msg=None):
    try:
        if len(a) == len(b):
            if all([x == y for x, y in zip(a, b)]):
                success()
            else:
                failure(msg or "got %s, expected %s" % (a, b))
        else:
            failure(msg or "got length %s, expected %s" % (len(a), len(b)))
    except:
        assert_equal(a, b, msg)


def assert_greater(a, b, msg=None):
    if a > b:
        success()
    else:
        failure(msg or "%r unexpectedly not greater than %r" % (a, b))


def assert_greater_equal(a, b, msg=None):
    if a >= b:
        success()
    else:
        failure(
            msg or "%r unexpectedly not greater than or equal to %r" % (a, b))


def assert_less(a, b, msg=None):
    if a < b:
        success()
    else:
        failure(msg or "%r unexpectedly not less than %r" % (a, b))


def assert_less_equal(a, b, msg=None):
    if a <= b:
        success()
    else:
        failure(
            msg or "%r unexpectedly not less than or equal to %r" % (a, b))


def assert_is_instance(a, b, msg=None):
    if isinstance(a, b):
        success()
    else:
        failure(msg or "got %r, expected %r" % (type(a), b))


def assert_in(a, b, msg=None):
    if a in b:
        success()
    else:
        failure(msg or "%r unexpectedly not in %r" % (a, b))


def assert_match(v, pattern, msg=None):
    import re
    if re.match(pattern, v):
        success()
    else:
        failure(msg or "got %r, doesn't match pattern %r" % (v, pattern))


def assert_exception(exc_class, func):
    import sys
    import traceback
    try:
        func()
    except exc_class:
        success()
    except:
        failure("expected %r exception, got %r" % (
                exc_class.__name__, sys.exc_info()[0].__name__))
        traceback.print_exc()
    else:
        failure("expected %r exception, got no exception" % exc_class.__name__)


def assert_no_exception(func):
    import sys
    import traceback
    try:
        func()
    except:
        failure("expected no exception, got %r" % sys.exc_info()[0].__name__)
        traceback.print_exc()
    else:
        success()


def assert_warning(warn_class, func):
    # note: this assert calls func three times!
    import warnings

    def warn_error(message, category=UserWarning, **options):
        raise category(message)

    def warn_ignore(message, category=UserWarning, **options):
        pass
    warn = warnings.warn
    result = None
    try:
        warnings.warn = warn_ignore
        assert_no_exception(func)
        result = func()
        warnings.warn = warn_error
        assert_exception(warn_class, func)
    finally:
        warnings.warn = warn  # restore
    return result

# helpers

from io import BytesIO


def fromstring(data):
    from PIL import Image
    return Image.open(BytesIO(data))


def tostring(im, format, **options):
    out = BytesIO()
    im.save(out, format, **options)
    return out.getvalue()


def lena(mode="RGB", cache={}):
    from PIL import Image
    im = cache.get(mode)
    if im is None:
        if mode == "RGB":
            im = Image.open("Images/lena.ppm")
        elif mode == "F":
            im = lena("L").convert(mode)
        elif mode[:4] == "I;16":
            im = lena("I").convert(mode)
        else:
            im = lena("RGB").convert(mode)
    cache[mode] = im
    return im


def assert_image(im, mode, size, msg=None):
    if mode is not None and im.mode != mode:
        failure(msg or "got mode %r, expected %r" % (im.mode, mode))
    elif size is not None and im.size != size:
        failure(msg or "got size %r, expected %r" % (im.size, size))
    else:
        success()


def assert_image_equal(a, b, msg=None):
    if a.mode != b.mode:
        failure(msg or "got mode %r, expected %r" % (a.mode, b.mode))
    elif a.size != b.size:
        failure(msg or "got size %r, expected %r" % (a.size, b.size))
    elif a.tobytes() != b.tobytes():
        failure(msg or "got different content")
    else:
        success()


def assert_image_completely_equal(a, b, msg=None):
    if a != b:
        failure(msg or "images different")
    else:
        success()


def assert_image_similar(a, b, epsilon, msg=None):
    epsilon = float(epsilon)
    if a.mode != b.mode:
        return failure(msg or "got mode %r, expected %r" % (a.mode, b.mode))
    elif a.size != b.size:
        return failure(msg or "got size %r, expected %r" % (a.size, b.size))
    diff = 0
    try:
        ord(b'0')
        for abyte, bbyte in zip(a.tobytes(), b.tobytes()):
            diff += abs(ord(abyte)-ord(bbyte))
    except:
        for abyte, bbyte in zip(a.tobytes(), b.tobytes()):
            diff += abs(abyte-bbyte)
    ave_diff = float(diff)/(a.size[0]*a.size[1])
    if epsilon < ave_diff:
        return failure(
            msg or "average pixel value difference %.4f > epsilon %.4f" % (
                ave_diff, epsilon))
    else:
        return success()


def tempfile(template, *extra):
    import os
    import os.path
    import sys
    import tempfile
    files = []
    root = os.path.join(tempfile.gettempdir(), 'pillow-tests')
    try:
        os.mkdir(root)
    except OSError:
        pass
    for temp in (template,) + extra:
        assert temp[:5] in ("temp.", "temp_")
        name = os.path.basename(sys.argv[0])
        name = temp[:4] + os.path.splitext(name)[0][4:]
        name = name + "_%d" % len(_tempfiles) + temp[4:]
        name = os.path.join(root, name)
        files.append(name)
    _tempfiles.extend(files)
    return files[0]


# test runner

def run():
    global _target, _tests, run
    import sys
    import traceback
    _target = sys.modules["__main__"]
    run = None  # no need to run twice
    tests = []
    for name, value in list(vars(_target).items()):
        if name[:5] == "test_" and type(value) is type(success):
            tests.append((value.__code__.co_firstlineno, name, value))
    tests.sort()  # sort by line
    for lineno, name, func in tests:
        try:
            _tests = []
            func()
            for func, args in _tests:
                func(*args)
        except:
            t, v, tb = sys.exc_info()
            tb = tb.tb_next
            if tb:
                failure(frame=tb.tb_frame)
                traceback.print_exception(t, v, tb)
            else:
                print("%s:%d: cannot call test function: %s" % (
                    sys.argv[0], lineno, v))
                failure.count += 1


def yield_test(function, *args):
    # collect delayed/generated tests
    _tests.append((function, args))


def skip(msg=None):
    import os
    print("skip")
    os._exit(0)  # don't run exit handlers


def ignore(pattern):
    """Tells the driver to ignore messages matching the pattern, for the
    duration of the current test."""
    print('ignore: %s' % pattern)


def _setup():
    global _logfile

    import sys
    if "--coverage" in sys.argv:
        # Temporary: ignore PendingDeprecationWarning from Coverage (Py3.4)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import coverage
        cov = coverage.coverage(auto_data=True, include="PIL/*")
        cov.start()

    def report():
        if run:
            run()
        if success.count and not failure.count:
            print("ok")
            # only clean out tempfiles if test passed
            import os
            import os.path
            import tempfile
            for file in _tempfiles:
                try:
                    os.remove(file)
                except OSError:
                    pass  # report?
            temp_root = os.path.join(tempfile.gettempdir(), 'pillow-tests')
            try:
                os.rmdir(temp_root)
            except OSError:
                pass

    import atexit
    atexit.register(report)

    if "--log" in sys.argv:
        _logfile = open("test.log", "a")


_setup()

########NEW FILE########
__FILENAME__ = test_000_sanity
from __future__ import print_function
from tester import *

import PIL
import PIL.Image

# Make sure we have the binary extension
im = PIL.Image.core.new("L", (100, 100))

assert PIL.Image.VERSION[:3] == '1.1'

# Create an image and do stuff with it.
im = PIL.Image.new("1", (100, 100))
assert (im.mode, im.size) == ('1', (100, 100))
assert len(im.tobytes()) == 1300

# Create images in all remaining major modes.
im = PIL.Image.new("L", (100, 100))
im = PIL.Image.new("P", (100, 100))
im = PIL.Image.new("RGB", (100, 100))
im = PIL.Image.new("I", (100, 100))
im = PIL.Image.new("F", (100, 100))

print("ok")

########NEW FILE########
__FILENAME__ = test_001_archive
import PIL
import PIL.Image

import glob, os

for file in glob.glob("../pil-archive/*"):
    f, e = os.path.splitext(file)
    if e in [".txt", ".ttf", ".otf", ".zip"]:
        continue
    try:
        im = PIL.Image.open(file)
        im.load()
    except IOError as v:
        print("-", "failed to open", file, "-", v)
    else:
        print("+", file, im.mode, im.size, im.format)
        if e == ".exif":
            try:
                info = im._getexif()
            except KeyError as v:
                print("-", "failed to get exif info from", file, "-", v)

print("ok")

########NEW FILE########
__FILENAME__ = test_bmp_reference
from tester import *

from PIL import Image
import os

base = os.path.join('Tests', 'images', 'bmp')


def get_files(d, ext='.bmp'):
    return [os.path.join(base,d,f) for f
            in os.listdir(os.path.join(base, d)) if ext in f]

def test_bad():
    """ These shouldn't crash/dos, but they shouldn't return anything either """
    for f in get_files('b'):
        try:
            im = Image.open(f)
            im.load()
        except Exception as msg:
            pass
            # print ("Bad Image %s: %s" %(f,msg))

def test_questionable():
    """ These shouldn't crash/dos, but its not well defined that these are in spec """
    for f in get_files('q'):
        try:
            im = Image.open(f)
            im.load()
        except Exception as msg:
            pass
            # print ("Bad Image %s: %s" %(f,msg))


def test_good():
    """ These should all work. There's a set of target files in the
    html directory that we can compare against. """

    # Target files, if they're not just replacing the extension
    file_map = { 'pal1wb.bmp': 'pal1.png',
                 'pal4rle.bmp': 'pal4.png', 
                 'pal8-0.bmp': 'pal8.png',
                 'pal8rle.bmp': 'pal8.png',
                 'pal8topdown.bmp': 'pal8.png',
                 'pal8nonsquare.bmp': 'pal8nonsquare-v.png',
                 'pal8os2.bmp': 'pal8.png',
                 'pal8os2sp.bmp': 'pal8.png',
                 'pal8os2v2.bmp': 'pal8.png',
                 'pal8os2v2-16.bmp': 'pal8.png',
                 'pal8v4.bmp': 'pal8.png',
                 'pal8v5.bmp': 'pal8.png',
                 'rgb16-565pal.bmp': 'rgb16-565.png',
                 'rgb24pal.bmp': 'rgb24.png',
                 'rgb32.bmp': 'rgb24.png',
                 'rgb32bf.bmp': 'rgb24.png'
                 }     
                 
    def get_compare(f):
        (head, name) = os.path.split(f)
        if name in file_map:
            return os.path.join(base, 'html', file_map[name])
        (name,ext) = os.path.splitext(name)
        return os.path.join(base, 'html', "%s.png"%name)
    
    for f in get_files('g'):
        try:
            im = Image.open(f)
            im.load()
            compare = Image.open(get_compare(f))
            compare.load()
            if im.mode == 'P':
                # assert image similar doesn't really work
                # with paletized image, since the palette might
                # be differently ordered for an equivalent image.
                im = im.convert('RGBA')
                compare = im.convert('RGBA')
            assert_image_similar(im, compare,5)
            
            
        except Exception as msg:
            # there are three here that are unsupported:
            unsupported = (os.path.join(base, 'g', 'rgb32bf.bmp'),
                           os.path.join(base, 'g', 'pal8rle.bmp'),
                           os.path.join(base, 'g', 'pal4rle.bmp'))
            if f not in unsupported:
                assert_true(False, "Unsupported Image %s: %s" %(f,msg))


########NEW FILE########
__FILENAME__ = test_cffi
from tester import *

try:
    import cffi
except:
    skip()
    
from PIL import Image, PyAccess

import test_image_putpixel as put
import test_image_getpixel as get


Image.USE_CFFI_ACCESS = True

def test_put():
    put.test_sanity()

def test_get():
    get.test_basic()
    get.test_signedness()

def _test_get_access(im):
    """ Do we get the same thing as the old pixel access """

    """ Using private interfaces, forcing a capi access and a pyaccess for the same image """
    caccess = im.im.pixel_access(False)
    access = PyAccess.new(im, False)

    w,h = im.size
    for x in range(0,w,10):
        for y in range(0,h,10):
            assert_equal(access[(x,y)], caccess[(x,y)])

def test_get_vs_c():
    _test_get_access(lena('RGB'))
    _test_get_access(lena('RGBA'))
    _test_get_access(lena('L'))
    _test_get_access(lena('LA'))
    _test_get_access(lena('1'))
    _test_get_access(lena('P'))
    #_test_get_access(lena('PA')) # PA   -- how do I make a PA image???
    _test_get_access(lena('F'))
    
    im = Image.new('I;16', (10,10), 40000)
    _test_get_access(im)
    im = Image.new('I;16L', (10,10), 40000)
    _test_get_access(im)
    im = Image.new('I;16B', (10,10), 40000)
    _test_get_access(im)
    
    im = Image.new('I', (10,10), 40000)
    _test_get_access(im)
    # These don't actually appear to be modes that I can actually make,
    # as unpack sets them directly into the I mode. 
    #im = Image.new('I;32L', (10,10), -2**10)
    #_test_get_access(im)
    #im = Image.new('I;32B', (10,10), 2**10)
    #_test_get_access(im)



def _test_set_access(im, color):
    """ Are we writing the correct bits into the image? """

    """ Using private interfaces, forcing a capi access and a pyaccess for the same image """
    caccess = im.im.pixel_access(False)
    access = PyAccess.new(im, False)

    w,h = im.size
    for x in range(0,w,10):
        for y in range(0,h,10):
            access[(x,y)] = color
            assert_equal(color, caccess[(x,y)])

def test_set_vs_c():
    _test_set_access(lena('RGB'), (255, 128,0) )
    _test_set_access(lena('RGBA'), (255, 192, 128, 0))
    _test_set_access(lena('L'), 128)
    _test_set_access(lena('LA'), (128,128))
    _test_set_access(lena('1'), 255)
    _test_set_access(lena('P') , 128)
    ##_test_set_access(i, (128,128)) #PA  -- undone how to make
    _test_set_access(lena('F'), 1024.0)
    
    im = Image.new('I;16', (10,10), 40000)
    _test_set_access(im, 45000)
    im = Image.new('I;16L', (10,10), 40000)
    _test_set_access(im, 45000)
    im = Image.new('I;16B', (10,10), 40000)
    _test_set_access(im, 45000)
    

    im = Image.new('I', (10,10), 40000)
    _test_set_access(im, 45000)
#    im = Image.new('I;32L', (10,10), -(2**10))
#    _test_set_access(im, -(2**13)+1)
    #im = Image.new('I;32B', (10,10), 2**10)
   #_test_set_access(im, 2**13-1)

########NEW FILE########
__FILENAME__ = test_file_bmp
from tester import *

from PIL import Image
import io

def roundtrip(im):
    outfile = tempfile("temp.bmp")

    im.save(outfile, 'BMP')

    reloaded = Image.open(outfile)
    reloaded.load()
    assert_equal(im.mode, reloaded.mode)
    assert_equal(im.size, reloaded.size)
    assert_equal(reloaded.format, "BMP")


def test_sanity():
    roundtrip(lena())
    
    roundtrip(lena("1"))
    roundtrip(lena("L"))
    roundtrip(lena("P"))
    roundtrip(lena("RGB"))


def test_save_to_bytes():
    output = io.BytesIO()
    im = lena()
    im.save(output, "BMP")

    output.seek(0)
    reloaded = Image.open(output)
    
    assert_equal(im.mode, reloaded.mode)
    assert_equal(im.size, reloaded.size)
    assert_equal(reloaded.format, "BMP")
    

########NEW FILE########
__FILENAME__ = test_file_eps
from tester import *

from PIL import Image, EpsImagePlugin
import io

if not EpsImagePlugin.has_ghostscript():
    skip()

# Our two EPS test files (they are identical except for their bounding boxes)
file1 = "Tests/images/zero_bb.eps"
file2 = "Tests/images/non_zero_bb.eps"

# Due to palletization, we'll need to convert these to RGB after load
file1_compare = "Tests/images/zero_bb.png"
file1_compare_scale2 = "Tests/images/zero_bb_scale2.png"

file2_compare = "Tests/images/non_zero_bb.png"
file2_compare_scale2 = "Tests/images/non_zero_bb_scale2.png"

# EPS test files with binary preview
file3 = "Tests/images/binary_preview_map.eps"

def test_sanity():
    # Regular scale
    image1 = Image.open(file1)
    image1.load()
    assert_equal(image1.mode, "RGB")
    assert_equal(image1.size, (460, 352))
    assert_equal(image1.format, "EPS")

    image2 = Image.open(file2)
    image2.load()
    assert_equal(image2.mode, "RGB")
    assert_equal(image2.size, (360, 252))
    assert_equal(image2.format, "EPS")

    # Double scale
    image1_scale2 = Image.open(file1)
    image1_scale2.load(scale=2)
    assert_equal(image1_scale2.mode, "RGB")
    assert_equal(image1_scale2.size, (920, 704))
    assert_equal(image1_scale2.format, "EPS")

    image2_scale2 = Image.open(file2)
    image2_scale2.load(scale=2)
    assert_equal(image2_scale2.mode, "RGB")
    assert_equal(image2_scale2.size, (720, 504))
    assert_equal(image2_scale2.format, "EPS")


def test_file_object():
    # issue 479
    image1 = Image.open(file1)
    with open(tempfile('temp_file.eps'), 'wb') as fh:
        image1.save(fh, 'EPS')


def test_iobase_object():
    # issue 479
    image1 = Image.open(file1)
    with io.open(tempfile('temp_iobase.eps'), 'wb') as fh:
        image1.save(fh, 'EPS')


def test_render_scale1():
    # We need png support for these render test
    codecs = dir(Image.core)
    if "zip_encoder" not in codecs or "zip_decoder" not in codecs:
        skip("zip/deflate support not available")

    # Zero bounding box
    image1_scale1 = Image.open(file1)
    image1_scale1.load()
    image1_scale1_compare = Image.open(file1_compare).convert("RGB")
    image1_scale1_compare.load()
    assert_image_similar(image1_scale1, image1_scale1_compare, 5)

    # Non-Zero bounding box
    image2_scale1 = Image.open(file2)
    image2_scale1.load()
    image2_scale1_compare = Image.open(file2_compare).convert("RGB")
    image2_scale1_compare.load()
    assert_image_similar(image2_scale1, image2_scale1_compare, 10)


def test_render_scale2():
    # We need png support for these render test
    codecs = dir(Image.core)
    if "zip_encoder" not in codecs or "zip_decoder" not in codecs:
        skip("zip/deflate support not available")

    # Zero bounding box
    image1_scale2 = Image.open(file1)
    image1_scale2.load(scale=2)
    image1_scale2_compare = Image.open(file1_compare_scale2).convert("RGB")
    image1_scale2_compare.load()
    assert_image_similar(image1_scale2, image1_scale2_compare, 5)

    # Non-Zero bounding box
    image2_scale2 = Image.open(file2)
    image2_scale2.load(scale=2)
    image2_scale2_compare = Image.open(file2_compare_scale2).convert("RGB")
    image2_scale2_compare.load()
    assert_image_similar(image2_scale2, image2_scale2_compare, 10)


def test_resize():
    # Arrange
    image1 = Image.open(file1)
    image2 = Image.open(file2)
    new_size = (100, 100)

    # Act
    image1 = image1.resize(new_size)
    image2 = image2.resize(new_size)

    # Assert
    assert_equal(image1.size, new_size)
    assert_equal(image2.size, new_size)


def test_thumbnail():
    # Issue #619
    # Arrange
    image1 = Image.open(file1)
    image2 = Image.open(file2)
    new_size = (100, 100)

    # Act
    image1.thumbnail(new_size)
    image2.thumbnail(new_size)

    # Assert
    assert_equal(max(image1.size), max(new_size))
    assert_equal(max(image2.size), max(new_size))

def test_read_binary_preview():
    # Issue 302
    # open image with binary preview
    image1 = Image.open(file3)

# End of file

########NEW FILE########
__FILENAME__ = test_file_fli
from tester import *

from PIL import Image

# sample ppm stream
file = "Images/lena.fli"
data = open(file, "rb").read()

def test_sanity():
    im = Image.open(file)
    im.load()
    assert_equal(im.mode, "P")
    assert_equal(im.size, (128, 128))
    assert_equal(im.format, "FLI")

########NEW FILE########
__FILENAME__ = test_file_gif
from tester import *

from PIL import Image

codecs = dir(Image.core)

if "gif_encoder" not in codecs or "gif_decoder" not in codecs:
    skip("gif support not available") # can this happen?

# sample gif stream
file = "Images/lena.gif"
with open(file, "rb") as f:
    data = f.read()

def test_sanity():
    im = Image.open(file)
    im.load()
    assert_equal(im.mode, "P")
    assert_equal(im.size, (128, 128))
    assert_equal(im.format, "GIF")

def test_optimize():
    def test(optimize):
        im = Image.new("L", (1, 1), 0)
        file = BytesIO()
        im.save(file, "GIF", optimize=optimize)
        return len(file.getvalue())
    assert_equal(test(0), 800)
    assert_equal(test(1), 38)

def test_roundtrip():
    out = tempfile('temp.gif')
    im = lena()
    im.save(out)
    reread = Image.open(out)

    assert_image_similar(reread.convert('RGB'), im, 50)

def test_roundtrip2():
    #see https://github.com/python-imaging/Pillow/issues/403
    out = tempfile('temp.gif')
    im = Image.open('Images/lena.gif')
    im2 = im.copy()
    im2.save(out)
    reread = Image.open(out)

    assert_image_similar(reread.convert('RGB'), lena(), 50)


def test_palette_handling():
    # see https://github.com/python-imaging/Pillow/issues/513

    im = Image.open('Images/lena.gif')
    im = im.convert('RGB')
    
    im = im.resize((100,100), Image.ANTIALIAS)
    im2 = im.convert('P', palette=Image.ADAPTIVE, colors=256)

    f = tempfile('temp.gif')
    im2.save(f, optimize=True)

    reloaded = Image.open(f)
    
    assert_image_similar(im, reloaded.convert('RGB'), 10)
    
def test_palette_434():
    # see https://github.com/python-imaging/Pillow/issues/434

    def roundtrip(im, *args, **kwargs):
        out = tempfile('temp.gif')
        im.save(out, *args, **kwargs)
        reloaded = Image.open(out)

        return [im, reloaded]

    orig = "Tests/images/test.colors.gif"
    im = Image.open(orig)

    assert_image_equal(*roundtrip(im))
    assert_image_equal(*roundtrip(im, optimize=True))
    
    im = im.convert("RGB")
    # check automatic P conversion
    reloaded = roundtrip(im)[1].convert('RGB')
    assert_image_equal(im, reloaded)

    

########NEW FILE########
__FILENAME__ = test_file_icns
from tester import *

from PIL import Image

# sample icon file
file = "Images/pillow.icns"
data = open(file, "rb").read()

enable_jpeg2k = hasattr(Image.core, 'jp2klib_version')

def test_sanity():
    # Loading this icon by default should result in the largest size
    # (512x512@2x) being loaded
    im = Image.open(file)
    im.load()
    assert_equal(im.mode, "RGBA")
    assert_equal(im.size, (1024, 1024))
    assert_equal(im.format, "ICNS")

def test_sizes():
    # Check that we can load all of the sizes, and that the final pixel
    # dimensions are as expected
    im = Image.open(file)
    for w,h,r in im.info['sizes']:
        wr = w * r
        hr = h * r
        im2 = Image.open(file)
        im2.size = (w, h, r)
        im2.load()
        assert_equal(im2.mode, 'RGBA')
        assert_equal(im2.size, (wr, hr))

def test_older_icon():
    # This icon was made with Icon Composer rather than iconutil; it still
    # uses PNG rather than JP2, however (since it was made on 10.9).
    im = Image.open('Tests/images/pillow2.icns')
    for w,h,r in im.info['sizes']:
        wr = w * r
        hr = h * r
        im2 = Image.open('Tests/images/pillow2.icns')
        im2.size = (w, h, r)
        im2.load()
        assert_equal(im2.mode, 'RGBA')
        assert_equal(im2.size, (wr, hr))

def test_jp2_icon():
    # This icon was made by using Uli Kusterer's oldiconutil to replace
    # the PNG images with JPEG 2000 ones.  The advantage of doing this is
    # that OS X 10.5 supports JPEG 2000 but not PNG; some commercial
    # software therefore does just this.
    
    # (oldiconutil is here: https://github.com/uliwitness/oldiconutil)

    if not enable_jpeg2k:
        return
    
    im = Image.open('Tests/images/pillow3.icns')
    for w,h,r in im.info['sizes']:
        wr = w * r
        hr = h * r
        im2 = Image.open('Tests/images/pillow3.icns')
        im2.size = (w, h, r)
        im2.load()
        assert_equal(im2.mode, 'RGBA')
        assert_equal(im2.size, (wr, hr))
    

########NEW FILE########
__FILENAME__ = test_file_ico
from tester import *

from PIL import Image

# sample ppm stream
file = "Images/lena.ico"
data = open(file, "rb").read()

def test_sanity():
    im = Image.open(file)
    im.load()
    assert_equal(im.mode, "RGBA")
    assert_equal(im.size, (16, 16))
    assert_equal(im.format, "ICO")

########NEW FILE########
__FILENAME__ = test_file_jpeg
from tester import *

import random

from PIL import Image
from PIL import ImageFile

codecs = dir(Image.core)

if "jpeg_encoder" not in codecs or "jpeg_decoder" not in codecs:
    skip("jpeg support not available")

test_file = "Images/lena.jpg"


def roundtrip(im, **options):
    out = BytesIO()
    im.save(out, "JPEG", **options)
    bytes = out.tell()
    out.seek(0)
    im = Image.open(out)
    im.bytes = bytes  # for testing only
    return im

# --------------------------------------------------------------------


def test_sanity():

    # internal version number
    assert_match(Image.core.jpeglib_version, "\d+\.\d+$")

    im = Image.open(test_file)
    im.load()
    assert_equal(im.mode, "RGB")
    assert_equal(im.size, (128, 128))
    assert_equal(im.format, "JPEG")


# --------------------------------------------------------------------

def test_app():
    # Test APP/COM reader (@PIL135)
    im = Image.open(test_file)
    assert_equal(im.applist[0],
                 ("APP0", b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"))
    assert_equal(im.applist[1], ("COM", b"Python Imaging Library"))
    assert_equal(len(im.applist), 2)


def test_cmyk():
    # Test CMYK handling.  Thanks to Tim and Charlie for test data,
    # Michael for getting me to look one more time.
    f = "Tests/images/pil_sample_cmyk.jpg"
    im = Image.open(f)
    # the source image has red pixels in the upper left corner.
    c, m, y, k = [x / 255.0 for x in im.getpixel((0, 0))]
    assert_true(c == 0.0 and m > 0.8 and y > 0.8 and k == 0.0)
    # the opposite corner is black
    c, m, y, k = [x / 255.0 for x in im.getpixel((im.size[0]-1, im.size[1]-1))]
    assert_true(k > 0.9)
    # roundtrip, and check again
    im = roundtrip(im)
    c, m, y, k = [x / 255.0 for x in im.getpixel((0, 0))]
    assert_true(c == 0.0 and m > 0.8 and y > 0.8 and k == 0.0)
    c, m, y, k = [x / 255.0 for x in im.getpixel((im.size[0]-1, im.size[1]-1))]
    assert_true(k > 0.9)


def test_dpi():
    def test(xdpi, ydpi=None):
        im = Image.open(test_file)
        im = roundtrip(im, dpi=(xdpi, ydpi or xdpi))
        return im.info.get("dpi")
    assert_equal(test(72), (72, 72))
    assert_equal(test(300), (300, 300))
    assert_equal(test(100, 200), (100, 200))
    assert_equal(test(0), None)  # square pixels


def test_icc():
    # Test ICC support
    im1 = Image.open("Tests/images/rgb.jpg")
    icc_profile = im1.info["icc_profile"]
    assert_equal(len(icc_profile), 3144)
    # Roundtrip via physical file.
    f = tempfile("temp.jpg")
    im1.save(f, icc_profile=icc_profile)
    im2 = Image.open(f)
    assert_equal(im2.info.get("icc_profile"), icc_profile)
    # Roundtrip via memory buffer.
    im1 = roundtrip(lena())
    im2 = roundtrip(lena(), icc_profile=icc_profile)
    assert_image_equal(im1, im2)
    assert_false(im1.info.get("icc_profile"))
    assert_true(im2.info.get("icc_profile"))


def test_icc_big():
    # Make sure that the "extra" support handles large blocks
    def test(n):
        # The ICC APP marker can store 65519 bytes per marker, so
        # using a 4-byte test code should allow us to detect out of
        # order issues.
        icc_profile = (b"Test"*int(n/4+1))[:n]
        assert len(icc_profile) == n  # sanity
        im1 = roundtrip(lena(), icc_profile=icc_profile)
        assert_equal(im1.info.get("icc_profile"), icc_profile or None)
    test(0)
    test(1)
    test(3)
    test(4)
    test(5)
    test(65533-14)  # full JPEG marker block
    test(65533-14+1)  # full block plus one byte
    test(ImageFile.MAXBLOCK)  # full buffer block
    test(ImageFile.MAXBLOCK+1)  # full buffer block plus one byte
    test(ImageFile.MAXBLOCK*4+3)  # large block


def test_optimize():
    im1 = roundtrip(lena())
    im2 = roundtrip(lena(), optimize=1)
    assert_image_equal(im1, im2)
    assert_true(im1.bytes >= im2.bytes)


def test_optimize_large_buffer():
    # https://github.com/python-imaging/Pillow/issues/148
    f = tempfile('temp.jpg')
    # this requires ~ 1.5x Image.MAXBLOCK
    im = Image.new("RGB", (4096, 4096), 0xff3333)
    im.save(f, format="JPEG", optimize=True)


def test_progressive():
    im1 = roundtrip(lena())
    im2 = roundtrip(lena(), progressive=True)
    assert_image_equal(im1, im2)
    assert_true(im1.bytes >= im2.bytes)


def test_progressive_large_buffer():
    f = tempfile('temp.jpg')
    # this requires ~ 1.5x Image.MAXBLOCK
    im = Image.new("RGB", (4096, 4096), 0xff3333)
    im.save(f, format="JPEG", progressive=True)


def test_progressive_large_buffer_highest_quality():
    f = tempfile('temp.jpg')
    if py3:
        a = bytes(random.randint(0, 255) for _ in range(256 * 256 * 3))
    else:
        a = b''.join(chr(random.randint(0, 255)) for _ in range(256 * 256 * 3))
    im = Image.frombuffer("RGB", (256, 256), a, "raw", "RGB", 0, 1)
    # this requires more bytes than pixels in the image
    im.save(f, format="JPEG", progressive=True, quality=100)


def test_large_exif():
    # https://github.com/python-imaging/Pillow/issues/148
    f = tempfile('temp.jpg')
    im = lena()
    im.save(f, 'JPEG', quality=90, exif=b"1"*65532)


def test_progressive_compat():
    im1 = roundtrip(lena())
    im2 = roundtrip(lena(), progressive=1)
    im3 = roundtrip(lena(), progression=1)  # compatibility
    assert_image_equal(im1, im2)
    assert_image_equal(im1, im3)
    assert_false(im1.info.get("progressive"))
    assert_false(im1.info.get("progression"))
    assert_true(im2.info.get("progressive"))
    assert_true(im2.info.get("progression"))
    assert_true(im3.info.get("progressive"))
    assert_true(im3.info.get("progression"))


def test_quality():
    im1 = roundtrip(lena())
    im2 = roundtrip(lena(), quality=50)
    assert_image(im1, im2.mode, im2.size)
    assert_true(im1.bytes >= im2.bytes)


def test_smooth():
    im1 = roundtrip(lena())
    im2 = roundtrip(lena(), smooth=100)
    assert_image(im1, im2.mode, im2.size)


def test_subsampling():
    def getsampling(im):
        layer = im.layer
        return layer[0][1:3] + layer[1][1:3] + layer[2][1:3]
    # experimental API
    im = roundtrip(lena(), subsampling=-1)  # default
    assert_equal(getsampling(im), (2, 2, 1, 1, 1, 1))
    im = roundtrip(lena(), subsampling=0)  # 4:4:4
    assert_equal(getsampling(im), (1, 1, 1, 1, 1, 1))
    im = roundtrip(lena(), subsampling=1)  # 4:2:2
    assert_equal(getsampling(im), (2, 1, 1, 1, 1, 1))
    im = roundtrip(lena(), subsampling=2)  # 4:1:1
    assert_equal(getsampling(im), (2, 2, 1, 1, 1, 1))
    im = roundtrip(lena(), subsampling=3)  # default (undefined)
    assert_equal(getsampling(im), (2, 2, 1, 1, 1, 1))

    im = roundtrip(lena(), subsampling="4:4:4")
    assert_equal(getsampling(im), (1, 1, 1, 1, 1, 1))
    im = roundtrip(lena(), subsampling="4:2:2")
    assert_equal(getsampling(im), (2, 1, 1, 1, 1, 1))
    im = roundtrip(lena(), subsampling="4:1:1")
    assert_equal(getsampling(im), (2, 2, 1, 1, 1, 1))

    assert_exception(TypeError, lambda: roundtrip(lena(), subsampling="1:1:1"))


def test_exif():
    im = Image.open("Tests/images/pil_sample_rgb.jpg")
    info = im._getexif()
    assert_equal(info[305], 'Adobe Photoshop CS Macintosh')


def test_quality_keep():
    im = Image.open("Images/lena.jpg")
    f = tempfile('temp.jpg')
    assert_no_exception(lambda: im.save(f, quality='keep'))


def test_junk_jpeg_header():
    # https://github.com/python-imaging/Pillow/issues/630
    filename = "Tests/images/junk_jpeg_header.jpg"
    assert_no_exception(lambda: Image.open(filename))

# End of file

########NEW FILE########
__FILENAME__ = test_file_jpeg2k
from tester import *

from PIL import Image
from PIL import ImageFile

codecs = dir(Image.core)

if "jpeg2k_encoder" not in codecs or "jpeg2k_decoder" not in codecs:
    skip('JPEG 2000 support not available')

# OpenJPEG 2.0.0 outputs this debugging message sometimes; we should
# ignore it---it doesn't represent a test failure.
ignore('Not enough memory to handle tile data')

test_card = Image.open('Tests/images/test-card.png')
test_card.load()

def roundtrip(im, **options):
    out = BytesIO()
    im.save(out, "JPEG2000", **options)
    bytes = out.tell()
    out.seek(0)
    im = Image.open(out)
    im.bytes = bytes # for testing only
    im.load()
    return im

# ----------------------------------------------------------------------

def test_sanity():
    # Internal version number
    assert_match(Image.core.jp2klib_version, '\d+\.\d+\.\d+$')

    im = Image.open('Tests/images/test-card-lossless.jp2')
    im.load()
    assert_equal(im.mode, 'RGB')
    assert_equal(im.size, (640, 480))
    assert_equal(im.format, 'JPEG2000')
    
# ----------------------------------------------------------------------

# These two test pre-written JPEG 2000 files that were not written with
# PIL (they were made using Adobe Photoshop)

def test_lossless():
    im = Image.open('Tests/images/test-card-lossless.jp2')
    im.load()
    im.save('/tmp/test-card.png')
    assert_image_similar(im, test_card, 1.0e-3)

def test_lossy_tiled():
    im = Image.open('Tests/images/test-card-lossy-tiled.jp2')
    im.load()
    assert_image_similar(im, test_card, 2.0)

# ----------------------------------------------------------------------

def test_lossless_rt():
    im = roundtrip(test_card)
    assert_image_equal(im, test_card)

def test_lossy_rt():
    im = roundtrip(test_card, quality_layers=[20])
    assert_image_similar(im, test_card, 2.0)

def test_tiled_rt():
    im = roundtrip(test_card, tile_size=(128, 128))
    assert_image_equal(im, test_card)

def test_tiled_offset_rt():
    im = roundtrip(test_card, tile_size=(128, 128), tile_offset=(0, 0),
                   offset=(32, 32))
    assert_image_equal(im, test_card)
    
def test_irreversible_rt():
    im = roundtrip(test_card, irreversible=True, quality_layers=[20])
    assert_image_similar(im, test_card, 2.0)

def test_prog_qual_rt():
    im = roundtrip(test_card, quality_layers=[60, 40, 20], progression='LRCP')
    assert_image_similar(im, test_card, 2.0)

def test_prog_res_rt():
    im = roundtrip(test_card, num_resolutions=8, progression='RLCP')
    assert_image_equal(im, test_card)

# ----------------------------------------------------------------------

def test_reduce():
    im = Image.open('Tests/images/test-card-lossless.jp2')
    im.reduce = 2
    im.load()
    assert_equal(im.size, (160, 120))

def test_layers():
    out = BytesIO()
    test_card.save(out, 'JPEG2000', quality_layers=[100, 50, 10],
                   progression='LRCP')
    out.seek(0)
    
    im = Image.open(out)
    im.layers = 1
    im.load()
    assert_image_similar(im, test_card, 13)

    out.seek(0)
    im = Image.open(out)
    im.layers = 3
    im.load()
    assert_image_similar(im, test_card, 0.4)

########NEW FILE########
__FILENAME__ = test_file_libtiff
from tester import *
import os

from PIL import Image, TiffImagePlugin

codecs = dir(Image.core)

if "libtiff_encoder" not in codecs or "libtiff_decoder" not in codecs:
    skip("tiff support not available")

def _assert_noerr(im):
    """Helper tests that assert basic sanity about the g4 tiff reading"""
    #1 bit
    assert_equal(im.mode, "1")

    # Does the data actually load
    assert_no_exception(lambda: im.load())
    assert_no_exception(lambda: im.getdata())

    try:
        assert_equal(im._compression, 'group4')
    except:
        print("No _compression")
        print (dir(im))

    # can we write it back out, in a different form.
    out = tempfile("temp.png")
    assert_no_exception(lambda: im.save(out))

def test_g4_tiff():
    """Test the ordinary file path load path"""

    file = "Tests/images/lena_g4_500.tif"
    im = Image.open(file)

    assert_equal(im.size, (500,500))
    _assert_noerr(im)

def test_g4_large():
    file = "Tests/images/pport_g4.tif"
    im = Image.open(file)
    _assert_noerr(im)

def test_g4_tiff_file():
    """Testing the string load path"""

    file = "Tests/images/lena_g4_500.tif"
    with open(file,'rb') as f:
        im = Image.open(f)

        assert_equal(im.size, (500,500))
        _assert_noerr(im)

def test_g4_tiff_bytesio():
    """Testing the stringio loading code path"""
    from io import BytesIO
    file = "Tests/images/lena_g4_500.tif"
    s = BytesIO()
    with open(file,'rb') as f:
        s.write(f.read())
        s.seek(0)
    im = Image.open(s)

    assert_equal(im.size, (500,500))
    _assert_noerr(im)

def test_g4_eq_png():
    """ Checking that we're actually getting the data that we expect"""
    png = Image.open('Tests/images/lena_bw_500.png')
    g4 = Image.open('Tests/images/lena_g4_500.tif')

    assert_image_equal(g4, png)

# see https://github.com/python-imaging/Pillow/issues/279
def test_g4_fillorder_eq_png():
    """ Checking that we're actually getting the data that we expect"""
    png = Image.open('Tests/images/g4-fillorder-test.png')
    g4 = Image.open('Tests/images/g4-fillorder-test.tif')

    assert_image_equal(g4, png)

def test_g4_write():
    """Checking to see that the saved image is the same as what we wrote"""
    file = "Tests/images/lena_g4_500.tif"
    orig = Image.open(file)

    out = tempfile("temp.tif")
    rot = orig.transpose(Image.ROTATE_90)
    assert_equal(rot.size,(500,500))
    rot.save(out)

    reread = Image.open(out)
    assert_equal(reread.size,(500,500))
    _assert_noerr(reread)
    assert_image_equal(reread, rot)
    assert_equal(reread.info['compression'], 'group4')

    assert_equal(reread.info['compression'], orig.info['compression'])
    
    assert_false(orig.tobytes() == reread.tobytes())

def test_adobe_deflate_tiff():
    file = "Tests/images/tiff_adobe_deflate.tif"
    im = Image.open(file)

    assert_equal(im.mode, "RGB")
    assert_equal(im.size, (278, 374))
    assert_equal(im.tile[0][:3], ('tiff_adobe_deflate', (0, 0, 278, 374), 0))
    assert_no_exception(lambda: im.load())

def test_write_metadata():
    """ Test metadata writing through libtiff """
    img = Image.open('Tests/images/lena_g4.tif')
    f = tempfile('temp.tiff')

    img.save(f, tiffinfo = img.tag)

    loaded = Image.open(f)

    original = img.tag.named()
    reloaded = loaded.tag.named()

    # PhotometricInterpretation is set from SAVE_INFO, not the original image. 
    ignored = ['StripByteCounts', 'RowsPerStrip', 'PageNumber', 'PhotometricInterpretation']

    for tag, value in reloaded.items():
        if tag not in ignored:
            if tag.endswith('Resolution'):
                val = original[tag]
                assert_almost_equal(val[0][0]/val[0][1], value[0][0]/value[0][1],
                                    msg="%s didn't roundtrip" % tag)
            else:
                assert_equal(original[tag], value, "%s didn't roundtrip" % tag)

    for tag, value in original.items():
        if tag not in ignored: 
            if tag.endswith('Resolution'):
                val = reloaded[tag]
                assert_almost_equal(val[0][0]/val[0][1], value[0][0]/value[0][1],
                                    msg="%s didn't roundtrip" % tag)
            else:
                assert_equal(value, reloaded[tag], "%s didn't roundtrip" % tag)


def test_g3_compression():
    i = Image.open('Tests/images/lena_g4_500.tif')
    out = tempfile("temp.tif")
    i.save(out, compression='group3')

    reread = Image.open(out)
    assert_equal(reread.info['compression'], 'group3')
    assert_image_equal(reread, i)

def test_little_endian():
    im = Image.open('Tests/images/16bit.deflate.tif')
    assert_equal(im.getpixel((0,0)), 480)
    assert_equal(im.mode, 'I;16')

    b = im.tobytes()
    # Bytes are in image native order (little endian)
    if py3:
        assert_equal(b[0], ord(b'\xe0'))
        assert_equal(b[1], ord(b'\x01'))
    else:
        assert_equal(b[0], b'\xe0')
        assert_equal(b[1], b'\x01')
        

    out = tempfile("temp.tif")
    #out = "temp.le.tif"
    im.save(out)
    reread = Image.open(out)

    assert_equal(reread.info['compression'], im.info['compression'])
    assert_equal(reread.getpixel((0,0)), 480)
    # UNDONE - libtiff defaults to writing in native endian, so
    # on big endian, we'll get back mode = 'I;16B' here. 
    
def test_big_endian():
    im = Image.open('Tests/images/16bit.MM.deflate.tif')

    assert_equal(im.getpixel((0,0)), 480)
    assert_equal(im.mode, 'I;16B')

    b = im.tobytes()

    # Bytes are in image native order (big endian)
    if py3:
        assert_equal(b[0], ord(b'\x01'))
        assert_equal(b[1], ord(b'\xe0'))
    else:
        assert_equal(b[0], b'\x01')
        assert_equal(b[1], b'\xe0')
    
    out = tempfile("temp.tif")
    im.save(out)
    reread = Image.open(out)

    assert_equal(reread.info['compression'], im.info['compression'])
    assert_equal(reread.getpixel((0,0)), 480)

def test_g4_string_info():
    """Tests String data in info directory"""
    file = "Tests/images/lena_g4_500.tif"
    orig = Image.open(file)
    
    out = tempfile("temp.tif")

    orig.tag[269] = 'temp.tif'
    orig.save(out)
             
    reread = Image.open(out)
    assert_equal('temp.tif', reread.tag[269])

def test_12bit_rawmode():
    """ Are we generating the same interpretation of the image as Imagemagick is? """
    TiffImagePlugin.READ_LIBTIFF = True
    #Image.DEBUG = True
    im = Image.open('Tests/images/12bit.cropped.tif')
    im.load()
    TiffImagePlugin.READ_LIBTIFF = False
    # to make the target --
    # convert 12bit.cropped.tif -depth 16 tmp.tif
    # convert tmp.tif -evaluate RightShift 4 12in16bit2.tif
    # imagemagick will auto scale so that a 12bit FFF is 16bit FFF0,
    # so we need to unshift so that the integer values are the same. 
    
    im2 = Image.open('Tests/images/12in16bit.tif')

    if Image.DEBUG:
        print (im.getpixel((0,0)))
        print (im.getpixel((0,1)))
        print (im.getpixel((0,2)))

        print (im2.getpixel((0,0)))
        print (im2.getpixel((0,1)))
        print (im2.getpixel((0,2)))
  
    assert_image_equal(im, im2)

def test_blur():
    # test case from irc, how to do blur on b/w image and save to compressed tif. 
    from PIL import ImageFilter
    out = tempfile('temp.tif')
    im = Image.open('Tests/images/pport_g4.tif')
    im = im.convert('L')

    im=im.filter(ImageFilter.GaussianBlur(4))
    im.save(out, compression='tiff_adobe_deflate')

    im2 = Image.open(out)
    im2.load()

    assert_image_equal(im, im2)


def test_compressions():
    im = lena('RGB')
    out = tempfile('temp.tif')

    for compression in ('packbits', 'tiff_lzw'):
        im.save(out, compression=compression)
        im2 = Image.open(out)
        assert_image_equal(im, im2)

    im.save(out, compression='jpeg')
    im2 = Image.open(out)
    assert_image_similar(im, im2, 30)
                            

def test_cmyk_save():
    im = lena('CMYK')
    out = tempfile('temp.tif')

    im.save(out, compression='tiff_adobe_deflate')
    im2 = Image.open(out)
    assert_image_equal(im, im2)

def xtest_bw_compression_wRGB():
    """ This test passes, but when running all tests causes a failure due to
        output on stderr from the error thrown by libtiff. We need to capture that
        but not now"""
    
    im = lena('RGB')
    out = tempfile('temp.tif')

    assert_exception(IOError, lambda: im.save(out, compression='tiff_ccitt'))
    assert_exception(IOError, lambda: im.save(out, compression='group3'))
    assert_exception(IOError, lambda: im.save(out, compression='group4'))

def test_fp_leak():
    im = Image.open("Tests/images/lena_g4_500.tif")
    fn = im.fp.fileno()

    assert_no_exception(lambda: os.fstat(fn))
    im.load()  # this should close it. 
    assert_exception(OSError, lambda: os.fstat(fn)) 
    im = None  # this should force even more closed.
    assert_exception(OSError, lambda: os.fstat(fn)) 
    assert_exception(OSError, lambda: os.close(fn))

########NEW FILE########
__FILENAME__ = test_file_libtiff_small
from tester import *

from PIL import Image

from test_file_libtiff import _assert_noerr

codecs = dir(Image.core)

if "libtiff_encoder" not in codecs or "libtiff_decoder" not in codecs:
    skip("tiff support not available")

""" The small lena image was failing on open in the libtiff
    decoder because the file pointer was set to the wrong place
    by a spurious seek. It wasn't failing with the byteio method.

    It was fixed by forcing an lseek to the beginning of the
    file just before reading in libtiff. These tests remain
    to ensure that it stays fixed. """


def test_g4_lena_file():
    """Testing the open file load path"""

    file = "Tests/images/lena_g4.tif"
    with open(file,'rb') as f:
        im = Image.open(f)

        assert_equal(im.size, (128,128))
        _assert_noerr(im)

def test_g4_lena_bytesio():
    """Testing the bytesio loading code path"""
    from io import BytesIO
    file = "Tests/images/lena_g4.tif"
    s = BytesIO()
    with open(file,'rb') as f:
        s.write(f.read())
        s.seek(0)
    im = Image.open(s)

    assert_equal(im.size, (128,128))
    _assert_noerr(im)

def test_g4_lena():
    """The 128x128 lena image fails for some reason. Investigating"""

    file = "Tests/images/lena_g4.tif"
    im = Image.open(file)

    assert_equal(im.size, (128,128))
    _assert_noerr(im)


########NEW FILE########
__FILENAME__ = test_file_msp
from tester import *

from PIL import Image

def test_sanity():

    file = tempfile("temp.msp")

    lena("1").save(file)

    im = Image.open(file)
    im.load()
    assert_equal(im.mode, "1")
    assert_equal(im.size, (128, 128))
    assert_equal(im.format, "MSP")

########NEW FILE########
__FILENAME__ = test_file_pcx
from tester import *

from PIL import Image


def _roundtrip(im):
    f = tempfile("temp.pcx")
    im.save(f)
    im2 = Image.open(f)

    assert_equal(im2.mode, im.mode)
    assert_equal(im2.size, im.size)
    assert_equal(im2.format, "PCX")
    assert_image_equal(im2, im)
    
def test_sanity():
    for mode in ('1', 'L', 'P', 'RGB'):
        _roundtrip(lena(mode))

def test_odd():
    # see issue #523, odd sized images should have a stride that's even.
    # not that imagemagick or gimp write pcx that way. 
    # we were not handling properly. 
    for mode in ('1', 'L', 'P', 'RGB'):
        # larger, odd sized images are better here to ensure that
        # we handle interrupted scan lines properly.
        _roundtrip(lena(mode).resize((511,511)))
        

def test_pil184():
    # Check reading of files where xmin/xmax is not zero.

    file = "Tests/images/pil184.pcx"
    im = Image.open(file)

    assert_equal(im.size, (447, 144))
    assert_equal(im.tile[0][1], (0, 0, 447, 144))

    # Make sure all pixels are either 0 or 255.
    assert_equal(im.histogram()[0] + im.histogram()[255], 447*144)

########NEW FILE########
__FILENAME__ = test_file_pdf
from tester import *
import os.path


def helper_save_as_pdf(mode):
    # Arrange
    im = lena(mode)
    outfile = tempfile("temp_" + mode + ".pdf")

    # Act
    im.save(outfile)

    # Assert
    assert_true(os.path.isfile(outfile))
    assert_greater(os.path.getsize(outfile), 0)


def test_monochrome():
    # Arrange
    mode = "1"

    # Act / Assert
    helper_save_as_pdf(mode)


def test_greyscale():
    # Arrange
    mode = "L"

    # Act / Assert
    helper_save_as_pdf(mode)


def test_rgb():
    # Arrange
    mode = "RGB"

    # Act / Assert
    helper_save_as_pdf(mode)


def test_p_mode():
    # Arrange
    mode = "P"

    # Act / Assert
    helper_save_as_pdf(mode)


def test_cmyk_mode():
    # Arrange
    mode = "CMYK"

    # Act / Assert
    helper_save_as_pdf(mode)


# End of file

########NEW FILE########
__FILENAME__ = test_file_png
from tester import *

from PIL import Image
from PIL import PngImagePlugin
import zlib

codecs = dir(Image.core)

if "zip_encoder" not in codecs or "zip_decoder" not in codecs:
    skip("zip/deflate support not available")

# sample png stream

file = "Images/lena.png"
data = open(file, "rb").read()

# stuff to create inline PNG images

MAGIC = PngImagePlugin._MAGIC

def chunk(cid, *data):
    file = BytesIO()
    PngImagePlugin.putchunk(*(file, cid) + data)
    return file.getvalue()

o32 = PngImagePlugin.o32

IHDR = chunk(b"IHDR", o32(1), o32(1), b'\x08\x02', b'\0\0\0')
IDAT = chunk(b"IDAT")
IEND = chunk(b"IEND")

HEAD = MAGIC + IHDR
TAIL = IDAT + IEND

def load(data):
    return Image.open(BytesIO(data))

def roundtrip(im, **options):
    out = BytesIO()
    im.save(out, "PNG", **options)
    out.seek(0)
    return Image.open(out)

# --------------------------------------------------------------------

def test_sanity():

    # internal version number
    assert_match(Image.core.zlib_version, "\d+\.\d+\.\d+(\.\d+)?$")

    file = tempfile("temp.png")

    lena("RGB").save(file)

    im = Image.open(file)
    im.load()
    assert_equal(im.mode, "RGB")
    assert_equal(im.size, (128, 128))
    assert_equal(im.format, "PNG")

    lena("1").save(file)
    im = Image.open(file)

    lena("L").save(file)
    im = Image.open(file)

    lena("P").save(file)
    im = Image.open(file)

    lena("RGB").save(file)
    im = Image.open(file)

    lena("I").save(file)
    im = Image.open(file)

# --------------------------------------------------------------------

def test_broken():
    # Check reading of totally broken files.  In this case, the test
    # file was checked into Subversion as a text file.

    file = "Tests/images/broken.png"
    assert_exception(IOError, lambda: Image.open(file))

def test_bad_text():
    # Make sure PIL can read malformed tEXt chunks (@PIL152)

    im = load(HEAD + chunk(b'tEXt') + TAIL)
    assert_equal(im.info, {})

    im = load(HEAD + chunk(b'tEXt', b'spam') + TAIL)
    assert_equal(im.info, {'spam': ''})

    im = load(HEAD + chunk(b'tEXt', b'spam\0') + TAIL)
    assert_equal(im.info, {'spam': ''})

    im = load(HEAD + chunk(b'tEXt', b'spam\0egg') + TAIL)
    assert_equal(im.info, {'spam': 'egg'})

    im = load(HEAD + chunk(b'tEXt', b'spam\0egg\0') + TAIL)
    assert_equal(im.info,  {'spam': 'egg\x00'})

def test_bad_ztxt():
    # Test reading malformed zTXt chunks (python-imaging/Pillow#318)

    im = load(HEAD + chunk(b'zTXt') + TAIL)
    assert_equal(im.info, {})

    im = load(HEAD + chunk(b'zTXt', b'spam') + TAIL)
    assert_equal(im.info, {'spam': ''})

    im = load(HEAD + chunk(b'zTXt', b'spam\0') + TAIL)
    assert_equal(im.info, {'spam': ''})

    im = load(HEAD + chunk(b'zTXt', b'spam\0\0') + TAIL)
    assert_equal(im.info, {'spam': ''})

    im = load(HEAD + chunk(b'zTXt', b'spam\0\0' + zlib.compress(b'egg')[:1]) + TAIL)
    assert_equal(im.info, {'spam': ''})

    im = load(HEAD + chunk(b'zTXt', b'spam\0\0' + zlib.compress(b'egg')) + TAIL)
    assert_equal(im.info,  {'spam': 'egg'})

def test_interlace():

    file = "Tests/images/pil123p.png"
    im = Image.open(file)

    assert_image(im, "P", (162, 150))
    assert_true(im.info.get("interlace"))

    assert_no_exception(lambda: im.load())

    file = "Tests/images/pil123rgba.png"
    im = Image.open(file)

    assert_image(im, "RGBA", (162, 150))
    assert_true(im.info.get("interlace"))

    assert_no_exception(lambda: im.load())

def test_load_transparent_p():
    file = "Tests/images/pil123p.png"
    im = Image.open(file)

    assert_image(im, "P", (162, 150))
    im = im.convert("RGBA")
    assert_image(im, "RGBA", (162, 150))

    # image has 124 uniqe qlpha values
    assert_equal(len(im.split()[3].getcolors()), 124)

def test_load_transparent_rgb():
    file = "Tests/images/rgb_trns.png"
    im = Image.open(file)

    assert_image(im, "RGB", (64, 64))
    im = im.convert("RGBA")
    assert_image(im, "RGBA", (64, 64))

    # image has 876 transparent pixels
    assert_equal(im.split()[3].getcolors()[0][0], 876)

def test_save_p_transparent_palette():
    in_file = "Tests/images/pil123p.png"
    im = Image.open(in_file)

    file = tempfile("temp.png")
    assert_no_exception(lambda: im.save(file))

def test_save_p_single_transparency():
    in_file = "Tests/images/p_trns_single.png"
    im = Image.open(in_file)

    file = tempfile("temp.png")
    assert_no_exception(lambda: im.save(file))

def test_save_l_transparency():
    in_file = "Tests/images/l_trns.png"
    im = Image.open(in_file)

    file = tempfile("temp.png")
    assert_no_exception(lambda: im.save(file))

    # There are 559 transparent pixels. 
    im = im.convert('RGBA')
    assert_equal(im.split()[3].getcolors()[0][0], 559)

def test_save_rgb_single_transparency():
    in_file = "Tests/images/caption_6_33_22.png"
    im = Image.open(in_file)

    file = tempfile("temp.png")
    assert_no_exception(lambda: im.save(file))

def test_load_verify():
    # Check open/load/verify exception (@PIL150)

    im = Image.open("Images/lena.png")
    assert_no_exception(lambda: im.verify())

    im = Image.open("Images/lena.png")
    im.load()
    assert_exception(RuntimeError, lambda: im.verify())

def test_roundtrip_dpi():
    # Check dpi roundtripping

    im = Image.open(file)

    im = roundtrip(im, dpi=(100, 100))
    assert_equal(im.info["dpi"], (100, 100))

def test_roundtrip_text():
    # Check text roundtripping

    im = Image.open(file)

    info = PngImagePlugin.PngInfo()
    info.add_text("TXT", "VALUE")
    info.add_text("ZIP", "VALUE", 1)

    im = roundtrip(im, pnginfo=info)
    assert_equal(im.info, {'TXT': 'VALUE', 'ZIP': 'VALUE'})
    assert_equal(im.text, {'TXT': 'VALUE', 'ZIP': 'VALUE'})

def test_scary():
    # Check reading of evil PNG file.  For information, see:
    # http://scary.beasts.org/security/CESA-2004-001.txt
    # The first byte is removed from pngtest_bad.png
    # to avoid classification as malware.

    with open("Tests/images/pngtest_bad.png.bin", 'rb') as fd:
        data = b'\x89' + fd.read()

    pngfile = BytesIO(data)
    assert_exception(IOError, lambda: Image.open(pngfile))

def test_trns_rgb():
    # Check writing and reading of tRNS chunks for RGB images.
    # Independent file sample provided by Sebastian Spaeth.

    file = "Tests/images/caption_6_33_22.png"
    im = Image.open(file)
    assert_equal(im.info["transparency"], (248, 248, 248))

    # check saving transparency by default
    im = roundtrip(im)
    assert_equal(im.info["transparency"], (248, 248, 248))

    im = roundtrip(im, transparency=(0, 1, 2))
    assert_equal(im.info["transparency"], (0, 1, 2))

def test_trns_p():
    # Check writing a transparency of 0, issue #528
    im = lena('P')
    im.info['transparency']=0
    
    f = tempfile("temp.png")
    im.save(f)

    im2 = Image.open(f)
    assert_true('transparency' in im2.info)

    assert_image_equal(im2.convert('RGBA'), im.convert('RGBA'))
        
    
def test_save_icc_profile_none():
    # check saving files with an ICC profile set to None (omit profile)
    in_file = "Tests/images/icc_profile_none.png"
    im = Image.open(in_file)
    assert_equal(im.info['icc_profile'], None)

    im = roundtrip(im)
    assert_false('icc_profile' in im.info)

def test_roundtrip_icc_profile():
    # check that we can roundtrip the icc profile
    im = lena('RGB')

    jpeg_image = Image.open('Tests/images/flower2.jpg')
    expected_icc = jpeg_image.info['icc_profile']

    im.info['icc_profile'] = expected_icc
    im = roundtrip(im)
    assert_equal(im.info['icc_profile'], expected_icc)


########NEW FILE########
__FILENAME__ = test_file_ppm
from tester import *

from PIL import Image

# sample ppm stream
file = "Images/lena.ppm"
data = open(file, "rb").read()

def test_sanity():
    im = Image.open(file)
    im.load()
    assert_equal(im.mode, "RGB")
    assert_equal(im.size, (128, 128))
    assert_equal(im.format, "PPM")

def test_16bit_pgm():
    im = Image.open('Tests/images/16_bit_binary.pgm')
    im.load()
    assert_equal(im.mode, 'I')
    assert_equal(im.size, (20,100))

    tgt = Image.open('Tests/images/16_bit_binary_pgm.png')
    assert_image_equal(im, tgt)


def test_16bit_pgm_write():
    im = Image.open('Tests/images/16_bit_binary.pgm')
    im.load()

    f = tempfile('temp.pgm')
    assert_no_exception(lambda: im.save(f, 'PPM'))

    reloaded = Image.open(f)
    assert_image_equal(im, reloaded)



########NEW FILE########
__FILENAME__ = test_file_psd
from tester import *

from PIL import Image

# sample ppm stream
file = "Images/lena.psd"
data = open(file, "rb").read()

def test_sanity():
    im = Image.open(file)
    im.load()
    assert_equal(im.mode, "RGB")
    assert_equal(im.size, (128, 128))
    assert_equal(im.format, "PSD")

########NEW FILE########
__FILENAME__ = test_file_tar
from tester import *

from PIL import Image, TarIO

codecs = dir(Image.core)
if "zip_decoder" not in codecs and "jpeg_decoder" not in codecs:
    skip("neither jpeg nor zip support not available")

# sample ppm stream
tarfile = "Images/lena.tar"

def test_sanity():
    if "zip_decoder" in codecs:
        tar = TarIO.TarIO(tarfile, 'lena.png')
        im = Image.open(tar)
        im.load()
        assert_equal(im.mode, "RGB")
        assert_equal(im.size, (128, 128))
        assert_equal(im.format, "PNG")

    if "jpeg_decoder" in codecs:
        tar = TarIO.TarIO(tarfile, 'lena.jpg')
        im = Image.open(tar)
        im.load()
        assert_equal(im.mode, "RGB")
        assert_equal(im.size, (128, 128))
        assert_equal(im.format, "JPEG")


########NEW FILE########
__FILENAME__ = test_file_tiff
from tester import *

from PIL import Image

def test_sanity():

    file = tempfile("temp.tif")

    lena("RGB").save(file)

    im = Image.open(file)
    im.load()
    assert_equal(im.mode, "RGB")
    assert_equal(im.size, (128, 128))
    assert_equal(im.format, "TIFF")

    lena("1").save(file)
    im = Image.open(file)

    lena("L").save(file)
    im = Image.open(file)

    lena("P").save(file)
    im = Image.open(file)

    lena("RGB").save(file)
    im = Image.open(file)

    lena("I").save(file)
    im = Image.open(file)

def test_mac_tiff():
    # Read RGBa images from Mac OS X [@PIL136]

    file = "Tests/images/pil136.tiff"
    im = Image.open(file)

    assert_equal(im.mode, "RGBA")
    assert_equal(im.size, (55, 43))
    assert_equal(im.tile, [('raw', (0, 0, 55, 43), 8, ('RGBa', 0, 1))])
    assert_no_exception(lambda: im.load())

def test_gimp_tiff():
    # Read TIFF JPEG images from GIMP [@PIL168]

    codecs = dir(Image.core)
    if "jpeg_decoder" not in codecs:
        skip("jpeg support not available")

    file = "Tests/images/pil168.tif"
    im = Image.open(file)

    assert_equal(im.mode, "RGB")
    assert_equal(im.size, (256, 256))
    assert_equal(im.tile, [
            ('jpeg', (0, 0, 256, 64), 8, ('RGB', '')),
            ('jpeg', (0, 64, 256, 128), 1215, ('RGB', '')),
            ('jpeg', (0, 128, 256, 192), 2550, ('RGB', '')),
            ('jpeg', (0, 192, 256, 256), 3890, ('RGB', '')),
            ])
    assert_no_exception(lambda: im.load())

def test_xyres_tiff():
    from PIL.TiffImagePlugin import X_RESOLUTION, Y_RESOLUTION
    file = "Tests/images/pil168.tif"
    im = Image.open(file)
    assert isinstance(im.tag.tags[X_RESOLUTION][0], tuple)
    assert isinstance(im.tag.tags[Y_RESOLUTION][0], tuple)
    #Try to read a file where X,Y_RESOLUTION are ints
    im.tag.tags[X_RESOLUTION] = (72,)
    im.tag.tags[Y_RESOLUTION] = (72,)
    im._setup()
    assert_equal(im.info['dpi'], (72., 72.))


def test_little_endian():
	im = Image.open('Tests/images/16bit.cropped.tif')
	assert_equal(im.getpixel((0,0)), 480)
	assert_equal(im.mode, 'I;16')

	b = im.tobytes()
	# Bytes are in image native order (little endian)
	if py3:
		assert_equal(b[0], ord(b'\xe0'))
		assert_equal(b[1], ord(b'\x01'))
	else:
		assert_equal(b[0], b'\xe0')
		assert_equal(b[1], b'\x01')
		

def test_big_endian():
	im = Image.open('Tests/images/16bit.MM.cropped.tif')
	assert_equal(im.getpixel((0,0)), 480)
	assert_equal(im.mode, 'I;16B')

	b = im.tobytes()

	# Bytes are in image native order (big endian)
	if py3:
		assert_equal(b[0], ord(b'\x01'))
		assert_equal(b[1], ord(b'\xe0'))
	else:
		assert_equal(b[0], b'\x01')
		assert_equal(b[1], b'\xe0')


def test_12bit_rawmode():
    """ Are we generating the same interpretation of the image as Imagemagick is? """

    #Image.DEBUG = True
    im = Image.open('Tests/images/12bit.cropped.tif')

    # to make the target --
    # convert 12bit.cropped.tif -depth 16 tmp.tif
    # convert tmp.tif -evaluate RightShift 4 12in16bit2.tif
    # imagemagick will auto scale so that a 12bit FFF is 16bit FFF0,
    # so we need to unshift so that the integer values are the same. 
    
    im2 = Image.open('Tests/images/12in16bit.tif')

    if Image.DEBUG:
        print (im.getpixel((0,0)))
        print (im.getpixel((0,1)))
        print (im.getpixel((0,2)))

        print (im2.getpixel((0,0)))
        print (im2.getpixel((0,1)))
        print (im2.getpixel((0,2)))
  
    assert_image_equal(im, im2)

def test_32bit_float():
    # Issue 614, specific 32 bit float format
    path = 'Tests/images/10ct_32bit_128.tiff'
    im = Image.open(path)
    im.load()

    assert_equal(im.getpixel((0,0)), -0.4526388943195343)
    assert_equal(im.getextrema(), (-3.140936851501465, 3.140684127807617))

    

########NEW FILE########
__FILENAME__ = test_file_tiff_metadata
from tester import *
from PIL import Image, TiffImagePlugin, TiffTags

tag_ids = dict(zip(TiffTags.TAGS.values(), TiffTags.TAGS.keys()))

def test_rt_metadata():
    """ Test writing arbitray metadata into the tiff image directory
        Use case is ImageJ private tags, one numeric, one arbitrary
        data.  https://github.com/python-imaging/Pillow/issues/291
        """
    
    img = lena()

    textdata = "This is some arbitrary metadata for a text field"
    info = TiffImagePlugin.ImageFileDirectory()

    info[tag_ids['ImageJMetaDataByteCounts']] = len(textdata)
    info[tag_ids['ImageJMetaData']] = textdata

    f = tempfile("temp.tif")

    img.save(f, tiffinfo=info)
    
    loaded = Image.open(f)

    assert_equal(loaded.tag[50838], (len(textdata),))
    assert_equal(loaded.tag[50839], textdata)
    
def test_read_metadata():
    img = Image.open('Tests/images/lena_g4.tif')
    
    known = {'YResolution': ((1207959552, 16777216),),
             'PlanarConfiguration': (1,),
             'BitsPerSample': (1,),
             'ImageLength': (128,),
             'Compression': (4,),
             'FillOrder': (1,),
             'DocumentName': 'lena.g4.tif',
             'RowsPerStrip': (128,),
             'ResolutionUnit': (1,),
             'PhotometricInterpretation': (0,),
             'PageNumber': (0, 1),
             'XResolution': ((1207959552, 16777216),),
             'ImageWidth': (128,),
             'Orientation': (1,),
             'StripByteCounts': (1796,),
             'SamplesPerPixel': (1,),
             'StripOffsets': (8,),
             'Software': 'ImageMagick 6.5.7-8 2012-08-17 Q16 http://www.imagemagick.org'}

    # assert_equal is equivalent, but less helpful in telling what's wrong. 
    named = img.tag.named()
    for tag, value in named.items():
        assert_equal(known[tag], value)

    for tag, value in known.items():
        assert_equal(value, named[tag])


def test_write_metadata():
    """ Test metadata writing through the python code """
    img = Image.open('Tests/images/lena.tif')

    f = tempfile('temp.tiff')
    img.save(f, tiffinfo = img.tag)

    loaded = Image.open(f)

    original = img.tag.named()
    reloaded = loaded.tag.named()

    ignored = ['StripByteCounts', 'RowsPerStrip', 'PageNumber', 'StripOffsets']
    
    for tag, value in reloaded.items():
        if tag not in ignored:
            assert_equal(original[tag], value, "%s didn't roundtrip" % tag)

    for tag, value in original.items():
        if tag not in ignored: 
            assert_equal(value, reloaded[tag], "%s didn't roundtrip" % tag)

########NEW FILE########
__FILENAME__ = test_file_webp
from tester import *

from PIL import Image


try:
    from PIL import _webp
except:
    skip('webp support not installed')


def test_version():
    assert_no_exception(lambda: _webp.WebPDecoderVersion())
    assert_no_exception(lambda: _webp.WebPDecoderBuggyAlpha())

def test_read_rgb():

    file_path = "Images/lena.webp"
    image = Image.open(file_path)

    assert_equal(image.mode, "RGB")
    assert_equal(image.size, (128, 128))
    assert_equal(image.format, "WEBP")
    assert_no_exception(lambda: image.load())
    assert_no_exception(lambda: image.getdata())

    # generated with: dwebp -ppm ../../Images/lena.webp -o lena_webp_bits.ppm
    target = Image.open('Tests/images/lena_webp_bits.ppm')
    assert_image_similar(image, target, 20.0)


def test_write_rgb():
    """
    Can we write a RGB mode file to webp without error. Does it have the bits we
    expect?

    """

    temp_file = tempfile("temp.webp")

    lena("RGB").save(temp_file)

    image = Image.open(temp_file)
    image.load()

    assert_equal(image.mode, "RGB")
    assert_equal(image.size, (128, 128))
    assert_equal(image.format, "WEBP")
    assert_no_exception(lambda: image.load())
    assert_no_exception(lambda: image.getdata())

    # If we're using the exact same version of webp, this test should pass.
    # but it doesn't if the webp is generated on Ubuntu and tested on Fedora.

    # generated with: dwebp -ppm temp.webp -o lena_webp_write.ppm
    #target = Image.open('Tests/images/lena_webp_write.ppm')
    #assert_image_equal(image, target)

    # This test asserts that the images are similar. If the average pixel difference
    # between the two images is less than the epsilon value, then we're going to
    # accept that it's a reasonable lossy version of the image. The included lena images
    # for webp are showing ~16 on Ubuntu, the jpegs are showing ~18.
    target = lena("RGB")
    assert_image_similar(image, target, 20.0)





########NEW FILE########
__FILENAME__ = test_file_webp_alpha
from tester import *

from PIL import Image

try:
    from PIL import _webp
except:
    skip('webp support not installed')


if _webp.WebPDecoderBuggyAlpha():
    skip("Buggy early version of webp installed, not testing transparency")

def test_read_rgba():
    # Generated with `cwebp transparent.png -o transparent.webp`
    file_path = "Images/transparent.webp"
    image = Image.open(file_path)

    assert_equal(image.mode, "RGBA")
    assert_equal(image.size, (200, 150))
    assert_equal(image.format, "WEBP")
    assert_no_exception(lambda: image.load())
    assert_no_exception(lambda: image.getdata())

    orig_bytes  = image.tobytes()

    target = Image.open('Images/transparent.png')
    assert_image_similar(image, target, 20.0)


def test_write_lossless_rgb():
    temp_file = tempfile("temp.webp")
    #temp_file = "temp.webp"
    
    pil_image = lena('RGBA')

    mask = Image.new("RGBA", (64, 64), (128,128,128,128))
    pil_image.paste(mask, (0,0), mask)   # add some partially transparent bits.
    
    pil_image.save(temp_file, lossless=True)
    
    image = Image.open(temp_file)
    image.load()

    assert_equal(image.mode, "RGBA")
    assert_equal(image.size, pil_image.size)
    assert_equal(image.format, "WEBP")
    assert_no_exception(lambda: image.load())
    assert_no_exception(lambda: image.getdata())


    assert_image_equal(image, pil_image)

def test_write_rgba():
    """
    Can we write a RGBA mode file to webp without error. Does it have the bits we
    expect?

    """

    temp_file = tempfile("temp.webp")

    pil_image = Image.new("RGBA", (10, 10), (255, 0, 0, 20))
    pil_image.save(temp_file)

    if _webp.WebPDecoderBuggyAlpha():
        return

    image = Image.open(temp_file)
    image.load()

    assert_equal(image.mode, "RGBA")
    assert_equal(image.size, (10, 10))
    assert_equal(image.format, "WEBP")
    assert_no_exception(image.load)
    assert_no_exception(image.getdata)

    assert_image_similar(image, pil_image, 1.0)





########NEW FILE########
__FILENAME__ = test_file_webp_lossless
from tester import *

from PIL import Image


try:
    from PIL import _webp
except:
    skip('webp support not installed')


if (_webp.WebPDecoderVersion() < 0x0200):
    skip('lossless not included')

def test_write_lossless_rgb():
    temp_file = tempfile("temp.webp")

    lena("RGB").save(temp_file, lossless=True)

    image = Image.open(temp_file)
    image.load()

    assert_equal(image.mode, "RGB")
    assert_equal(image.size, (128, 128))
    assert_equal(image.format, "WEBP")
    assert_no_exception(lambda: image.load())
    assert_no_exception(lambda: image.getdata())


    assert_image_equal(image, lena("RGB"))




########NEW FILE########
__FILENAME__ = test_file_webp_metadata
from tester import *

from PIL import Image

try:
    from PIL import _webp
    if not _webp.HAVE_WEBPMUX:
        skip('webpmux support not installed')
except:
    skip('webp support not installed')



def test_read_exif_metadata():

    file_path = "Images/flower.webp"
    image = Image.open(file_path)

    assert_equal(image.format, "WEBP")
    exif_data = image.info.get("exif", None)
    assert_true(exif_data)

    exif = image._getexif()

    #camera make
    assert_equal(exif[271], "Canon")

    jpeg_image = Image.open('Tests/images/flower.jpg')
    expected_exif = jpeg_image.info['exif']

    assert_equal(exif_data, expected_exif)


def test_write_exif_metadata():
    file_path = "Tests/images/flower.jpg"
    image = Image.open(file_path)
    expected_exif = image.info['exif']

    buffer = BytesIO()

    image.save(buffer, "webp", exif=expected_exif)

    buffer.seek(0)
    webp_image = Image.open(buffer)

    webp_exif = webp_image.info.get('exif', None)
    assert_true(webp_exif)
    if webp_exif:
        assert_equal(webp_exif, expected_exif, "Webp Exif didn't match")


def test_read_icc_profile():

    file_path = "Images/flower2.webp"
    image = Image.open(file_path)

    assert_equal(image.format, "WEBP")
    assert_true(image.info.get("icc_profile", None))

    icc = image.info['icc_profile']

    jpeg_image = Image.open('Tests/images/flower2.jpg')
    expected_icc = jpeg_image.info['icc_profile']

    assert_equal(icc, expected_icc)


def test_write_icc_metadata():
    file_path = "Tests/images/flower2.jpg"
    image = Image.open(file_path)
    expected_icc_profile = image.info['icc_profile']

    buffer = BytesIO()

    image.save(buffer, "webp", icc_profile=expected_icc_profile)

    buffer.seek(0)
    webp_image = Image.open(buffer)

    webp_icc_profile = webp_image.info.get('icc_profile', None)
    
    assert_true(webp_icc_profile)
    if webp_icc_profile:
        assert_equal(webp_icc_profile, expected_icc_profile, "Webp ICC didn't match")


def test_read_no_exif():
    file_path = "Tests/images/flower.jpg"
    image = Image.open(file_path)
    expected_exif = image.info['exif']

    buffer = BytesIO()

    image.save(buffer, "webp")
    
    buffer.seek(0)
    webp_image = Image.open(buffer)

    assert_false(webp_image._getexif())
    
 

########NEW FILE########
__FILENAME__ = test_file_xbm
from tester import *

from PIL import Image

PIL151 = b"""
#define basic_width 32
#define basic_height 32
static char basic_bits[] = {
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
0x00, 0x00, 0x00, 0x00,
0x80, 0xff, 0xff, 0x01, 0x40, 0x00, 0x00, 0x02,
0x20, 0x00, 0x00, 0x04, 0x20, 0x00, 0x00, 0x04, 0x10, 0x00, 0x00, 0x08,
0x10, 0x00, 0x00, 0x08,
0x10, 0x00, 0x00, 0x08, 0x10, 0x00, 0x00, 0x08,
0x10, 0x00, 0x00, 0x08, 0x10, 0x00, 0x00, 0x08, 0x10, 0x00, 0x00, 0x08,
0x20, 0x00, 0x00, 0x04,
0x20, 0x00, 0x00, 0x04, 0x40, 0x00, 0x00, 0x02,
0x80, 0xff, 0xff, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
0x00, 0x00, 0x00, 0x00,
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
0x00, 0x00, 0x00, 0x00,
};
"""

def test_pil151():

    im = Image.open(BytesIO(PIL151))

    assert_no_exception(lambda: im.load())
    assert_equal(im.mode, '1')
    assert_equal(im.size, (32, 32))

########NEW FILE########
__FILENAME__ = test_file_xpm
from tester import *

from PIL import Image

# sample ppm stream
file = "Images/lena.xpm"
data = open(file, "rb").read()

def test_sanity():
    im = Image.open(file)
    im.load()
    assert_equal(im.mode, "P")
    assert_equal(im.size, (128, 128))
    assert_equal(im.format, "XPM")

########NEW FILE########
__FILENAME__ = test_font_bdf
from tester import *

from PIL import Image, FontFile, BdfFontFile

filename = "Images/courB08.bdf"

def test_sanity():

    file = open(filename, "rb")
    font = BdfFontFile.BdfFontFile(file)

    assert_true(isinstance(font, FontFile.FontFile))
    assert_equal(len([_f for _f in font.glyph if _f]), 190)

########NEW FILE########
__FILENAME__ = test_font_pcf
from tester import *

from PIL import Image, FontFile, PcfFontFile
from PIL import ImageFont, ImageDraw

codecs = dir(Image.core)

if "zip_encoder" not in codecs or "zip_decoder" not in codecs:
    skip("zlib support not available")

fontname = "Tests/fonts/helvO18.pcf"
tempname = tempfile("temp.pil", "temp.pbm")

message  = "hello, world"

def test_sanity():

    file = open(fontname, "rb")
    font = PcfFontFile.PcfFontFile(file)
    assert_true(isinstance(font, FontFile.FontFile))
    assert_equal(len([_f for _f in font.glyph if _f]), 192)

    font.save(tempname)

def xtest_draw():

    font = ImageFont.load(tempname)
    image = Image.new("L", font.getsize(message), "white")
    draw = ImageDraw.Draw(image)
    draw.text((0, 0), message, font=font)
    # assert_signature(image, "7216c60f988dea43a46bb68321e3c1b03ec62aee")

def _test_high_characters(message):

    font = ImageFont.load(tempname)
    image = Image.new("L", font.getsize(message), "white")
    draw = ImageDraw.Draw(image)
    draw.text((0, 0), message, font=font)

    compare = Image.open('Tests/images/high_ascii_chars.png')
    assert_image_equal(image, compare)

def test_high_characters():
    message = "".join([chr(i+1) for i in range(140,232)])
    _test_high_characters(message)
    # accept bytes instances in Py3. 
    if bytes is not str:
        _test_high_characters(message.encode('latin1'))


########NEW FILE########
__FILENAME__ = test_format_lab
from tester import *

from PIL import Image

def test_white():
    i = Image.open('Tests/images/lab.tif')

    bits = i.load()
    
    assert_equal(i.mode, 'LAB')

    assert_equal(i.getbands(), ('L','A', 'B'))

    k = i.getpixel((0,0))
    assert_equal(k, (255,128,128))

    L  = i.getdata(0)
    a = i.getdata(1)
    b = i.getdata(2)

    assert_equal(list(L), [255]*100)
    assert_equal(list(a), [128]*100)
    assert_equal(list(b), [128]*100)
    

def test_green():
    # l= 50 (/100), a = -100 (-128 .. 128) b=0 in PS
    # == RGB: 0, 152, 117
    i = Image.open('Tests/images/lab-green.tif')

    k = i.getpixel((0,0))
    assert_equal(k, (128,28,128))


def test_red():
    # l= 50 (/100), a = 100 (-128 .. 128) b=0 in PS
    # == RGB: 255, 0, 124
    i = Image.open('Tests/images/lab-red.tif')

    k = i.getpixel((0,0))
    assert_equal(k, (128,228,128))

########NEW FILE########
__FILENAME__ = test_image
from tester import *

from PIL import Image

def test_sanity():

    im = Image.new("L", (100, 100))
    assert_equal(repr(im)[:45], "<PIL.Image.Image image mode=L size=100x100 at")
    assert_equal(im.mode, "L")
    assert_equal(im.size, (100, 100))

    im = Image.new("RGB", (100, 100))
    assert_equal(repr(im)[:45], "<PIL.Image.Image image mode=RGB size=100x100 ")
    assert_equal(im.mode, "RGB")
    assert_equal(im.size, (100, 100))

    im1 = Image.new("L", (100, 100), None)
    im2 = Image.new("L", (100, 100), 0)
    im3 = Image.new("L", (100, 100), "black")

    assert_equal(im2.getcolors(), [(10000, 0)])
    assert_equal(im3.getcolors(), [(10000, 0)])

    assert_exception(ValueError, lambda: Image.new("X", (100, 100)))
    # assert_exception(MemoryError, lambda: Image.new("L", (1000000, 1000000)))

def test_internals():

    im = Image.new("L", (100, 100))
    im.readonly = 1
    im._copy()
    assert_false(im.readonly)

    im.readonly = 1
    im.paste(0, (0, 0, 100, 100))
    assert_false(im.readonly)

    file = tempfile("temp.ppm")
    im._dump(file)

########NEW FILE########
__FILENAME__ = test_imagechops
from tester import *

from PIL import Image
from PIL import ImageChops

def test_sanity():

    im = lena("L")

    ImageChops.constant(im, 128)
    ImageChops.duplicate(im)
    ImageChops.invert(im)
    ImageChops.lighter(im, im)
    ImageChops.darker(im, im)
    ImageChops.difference(im, im)
    ImageChops.multiply(im, im)
    ImageChops.screen(im, im)

    ImageChops.add(im, im)
    ImageChops.add(im, im, 2.0)
    ImageChops.add(im, im, 2.0, 128)
    ImageChops.subtract(im, im)
    ImageChops.subtract(im, im, 2.0)
    ImageChops.subtract(im, im, 2.0, 128)

    ImageChops.add_modulo(im, im)
    ImageChops.subtract_modulo(im, im)

    ImageChops.blend(im, im, 0.5)
    ImageChops.composite(im, im, im)

    ImageChops.offset(im, 10)
    ImageChops.offset(im, 10, 20)

def test_logical():

    def table(op, a, b):
        out = []
        for x in (a, b):
            imx = Image.new("1", (1, 1), x)
            for y in (a, b):
                imy = Image.new("1", (1, 1), y)
                out.append(op(imx, imy).getpixel((0, 0)))
        return tuple(out)

    assert_equal(table(ImageChops.logical_and, 0, 1), (0, 0, 0, 255))
    assert_equal(table(ImageChops.logical_or, 0, 1), (0, 255, 255, 255))
    assert_equal(table(ImageChops.logical_xor, 0, 1), (0, 255, 255, 0))

    assert_equal(table(ImageChops.logical_and, 0, 128), (0, 0, 0, 255))
    assert_equal(table(ImageChops.logical_or, 0, 128), (0, 255, 255, 255))
    assert_equal(table(ImageChops.logical_xor, 0, 128), (0, 255, 255, 0))

    assert_equal(table(ImageChops.logical_and, 0, 255), (0, 0, 0, 255))
    assert_equal(table(ImageChops.logical_or, 0, 255), (0, 255, 255, 255))
    assert_equal(table(ImageChops.logical_xor, 0, 255), (0, 255, 255, 0))

########NEW FILE########
__FILENAME__ = test_imagecms
from tester import *

from PIL import Image
try:
    from PIL import ImageCms
    ImageCms.core.profile_open
except ImportError:
    skip()

SRGB = "Tests/icc/sRGB.icm"

def test_sanity():

    # basic smoke test.
    # this mostly follows the cms_test outline.

    v = ImageCms.versions() # should return four strings
    assert_equal(v[0], '1.0.0 pil')
    assert_equal(list(map(type, v)), [str, str, str, str])

    # internal version number
    assert_match(ImageCms.core.littlecms_version, "\d+\.\d+$")

    i = ImageCms.profileToProfile(lena(), SRGB, SRGB)
    assert_image(i, "RGB", (128, 128))

    t = ImageCms.buildTransform(SRGB, SRGB, "RGB", "RGB")
    i = ImageCms.applyTransform(lena(), t)
    assert_image(i, "RGB", (128, 128))

    p = ImageCms.createProfile("sRGB")
    o = ImageCms.getOpenProfile(SRGB)
    t = ImageCms.buildTransformFromOpenProfiles(p, o, "RGB", "RGB")
    i = ImageCms.applyTransform(lena(), t)
    assert_image(i, "RGB", (128, 128))

    t = ImageCms.buildProofTransform(SRGB, SRGB, SRGB, "RGB", "RGB")
    assert_equal(t.inputMode, "RGB")
    assert_equal(t.outputMode, "RGB")
    i = ImageCms.applyTransform(lena(), t)
    assert_image(i, "RGB", (128, 128))

    # test PointTransform convenience API
    im = lena().point(t)

def test_name():
    # get profile information for file
    assert_equal(ImageCms.getProfileName(SRGB).strip(),
                 'IEC 61966-2.1 Default RGB colour space - sRGB')
def x_test_info():
    assert_equal(ImageCms.getProfileInfo(SRGB).splitlines(),
                 ['sRGB IEC61966-2.1', '',
                  'Copyright (c) 1998 Hewlett-Packard Company', '',
                  'WhitePoint : D65 (daylight)', '',
                  'Tests/icc/sRGB.icm'])

def test_intent():
    assert_equal(ImageCms.getDefaultIntent(SRGB), 0)
    assert_equal(ImageCms.isIntentSupported(
            SRGB, ImageCms.INTENT_ABSOLUTE_COLORIMETRIC,
            ImageCms.DIRECTION_INPUT), 1)

def test_profile_object():
    # same, using profile object
    p = ImageCms.createProfile("sRGB")
#    assert_equal(ImageCms.getProfileName(p).strip(),
#                 'sRGB built-in - (lcms internal)')
#    assert_equal(ImageCms.getProfileInfo(p).splitlines(),
#                 ['sRGB built-in', '', 'WhitePoint : D65 (daylight)', '', ''])
    assert_equal(ImageCms.getDefaultIntent(p), 0)
    assert_equal(ImageCms.isIntentSupported(
            p, ImageCms.INTENT_ABSOLUTE_COLORIMETRIC,
            ImageCms.DIRECTION_INPUT), 1)

def test_extensions():
    # extensions
    i = Image.open("Tests/images/rgb.jpg")
    p = ImageCms.getOpenProfile(BytesIO(i.info["icc_profile"]))
    assert_equal(ImageCms.getProfileName(p).strip(),
                 'IEC 61966-2.1 Default RGB colour space - sRGB')

def test_exceptions():
    # the procedural pyCMS API uses PyCMSError for all sorts of errors
    assert_exception(ImageCms.PyCMSError, lambda: ImageCms.profileToProfile(lena(), "foo", "bar"))
    assert_exception(ImageCms.PyCMSError, lambda: ImageCms.buildTransform("foo", "bar", "RGB", "RGB"))
    assert_exception(ImageCms.PyCMSError, lambda: ImageCms.getProfileName(None))
    assert_exception(ImageCms.PyCMSError, lambda: ImageCms.isIntentSupported(SRGB, None, None))


def test_display_profile():
    # try fetching the profile for the current display device
    assert_no_exception(lambda: ImageCms.get_display_profile())


def test_lab_color_profile():
    pLab = ImageCms.createProfile("LAB", 5000)
    pLab = ImageCms.createProfile("LAB", 6500)

def test_simple_lab():
    i = Image.new('RGB', (10,10), (128,128,128))

    pLab = ImageCms.createProfile("LAB")    
    t = ImageCms.buildTransform(SRGB, pLab, "RGB", "LAB")

    i_lab = ImageCms.applyTransform(i, t)


    assert_equal(i_lab.mode, 'LAB')

    k = i_lab.getpixel((0,0))
    assert_equal(k, (137,128,128)) # not a linear luminance map. so L != 128

    L  = i_lab.getdata(0)
    a = i_lab.getdata(1)
    b = i_lab.getdata(2)

    assert_equal(list(L), [137]*100)
    assert_equal(list(a), [128]*100)
    assert_equal(list(b), [128]*100)

    
def test_lab_color():
    pLab = ImageCms.createProfile("LAB")    
    t = ImageCms.buildTransform(SRGB, pLab, "RGB", "LAB")
    # need to add a type mapping for some PIL type to TYPE_Lab_8 in findLCMSType,
    # and have that mapping work back to a PIL mode. (likely RGB)
    i = ImageCms.applyTransform(lena(), t)
    assert_image(i, "LAB", (128, 128))
    
    # i.save('temp.lab.tif')  # visually verified vs PS. 

    target = Image.open('Tests/images/lena.Lab.tif')

    assert_image_similar(i, target, 30)

def test_lab_srgb():
    pLab = ImageCms.createProfile("LAB")    
    t = ImageCms.buildTransform(pLab, SRGB, "LAB", "RGB")

    img = Image.open('Tests/images/lena.Lab.tif')

    img_srgb = ImageCms.applyTransform(img, t)

    # img_srgb.save('temp.srgb.tif') # visually verified vs ps. 
    
    assert_image_similar(lena(), img_srgb, 30)

def test_lab_roundtrip():
    # check to see if we're at least internally consistent. 
    pLab = ImageCms.createProfile("LAB")    
    t = ImageCms.buildTransform(SRGB, pLab, "RGB", "LAB")

    t2 = ImageCms.buildTransform(pLab, SRGB, "LAB", "RGB")

    i = ImageCms.applyTransform(lena(), t)
    out = ImageCms.applyTransform(i, t2)

    assert_image_similar(lena(), out, 2)



########NEW FILE########
__FILENAME__ = test_imagecolor
from tester import *

from PIL import Image
from PIL import ImageColor

# --------------------------------------------------------------------
# sanity

assert_equal((255, 0, 0), ImageColor.getrgb("#f00"))
assert_equal((255, 0, 0), ImageColor.getrgb("#ff0000"))
assert_equal((255, 0, 0), ImageColor.getrgb("rgb(255,0,0)"))
assert_equal((255, 0, 0), ImageColor.getrgb("rgb(255, 0, 0)"))
assert_equal((255, 0, 0), ImageColor.getrgb("rgb(100%,0%,0%)"))
assert_equal((255, 0, 0), ImageColor.getrgb("hsl(0, 100%, 50%)"))
assert_equal((255, 0, 0, 0), ImageColor.getrgb("rgba(255,0,0,0)"))
assert_equal((255, 0, 0, 0), ImageColor.getrgb("rgba(255, 0, 0, 0)"))
assert_equal((255, 0, 0), ImageColor.getrgb("red"))

# --------------------------------------------------------------------
# look for rounding errors (based on code by Tim Hatch)

for color in list(ImageColor.colormap.keys()):
    expected = Image.new("RGB", (1, 1), color).convert("L").getpixel((0, 0))
    actual = Image.new("L", (1, 1), color).getpixel((0, 0))
    assert_equal(expected, actual)

assert_equal((0, 0, 0), ImageColor.getcolor("black", "RGB"))
assert_equal((255, 255, 255), ImageColor.getcolor("white", "RGB"))
assert_equal((0, 255, 115), ImageColor.getcolor("rgba(0, 255, 115, 33)", "RGB"))
Image.new("RGB", (1, 1), "white")

assert_equal((0, 0, 0, 255), ImageColor.getcolor("black", "RGBA"))
assert_equal((255, 255, 255, 255), ImageColor.getcolor("white", "RGBA"))
assert_equal((0, 255, 115, 33), ImageColor.getcolor("rgba(0, 255, 115, 33)", "RGBA"))
Image.new("RGBA", (1, 1), "white")

assert_equal(0, ImageColor.getcolor("black", "L"))
assert_equal(255, ImageColor.getcolor("white", "L"))
assert_equal(162, ImageColor.getcolor("rgba(0, 255, 115, 33)", "L"))
Image.new("L", (1, 1), "white")

assert_equal(0, ImageColor.getcolor("black", "1"))
assert_equal(255, ImageColor.getcolor("white", "1"))
# The following test is wrong, but is current behavior
# The correct result should be 255 due to the mode 1 
assert_equal(162, ImageColor.getcolor("rgba(0, 255, 115, 33)", "1"))
# Correct behavior
# assert_equal(255, ImageColor.getcolor("rgba(0, 255, 115, 33)", "1"))
Image.new("1", (1, 1), "white")

assert_equal((0, 255), ImageColor.getcolor("black", "LA"))
assert_equal((255, 255), ImageColor.getcolor("white", "LA"))
assert_equal((162, 33), ImageColor.getcolor("rgba(0, 255, 115, 33)", "LA"))
Image.new("LA", (1, 1), "white")

########NEW FILE########
__FILENAME__ = test_imagedraw
from tester import *

from PIL import Image
from PIL import ImageDraw

def test_sanity():

    im = lena("RGB").copy()

    draw = ImageDraw.ImageDraw(im)
    draw = ImageDraw.Draw(im)

    draw.ellipse(list(range(4)))
    draw.line(list(range(10)))
    draw.polygon(list(range(100)))
    draw.rectangle(list(range(4)))

    success()

def test_deprecated():

    im = lena().copy()

    draw = ImageDraw.Draw(im)

    assert_warning(DeprecationWarning, lambda: draw.setink(0))
    assert_warning(DeprecationWarning, lambda: draw.setfill(0))


########NEW FILE########
__FILENAME__ = test_imageenhance
from tester import *

from PIL import Image
from PIL import ImageEnhance

def test_sanity():

    # FIXME: assert_image
    assert_no_exception(lambda: ImageEnhance.Color(lena()).enhance(0.5))
    assert_no_exception(lambda: ImageEnhance.Contrast(lena()).enhance(0.5))
    assert_no_exception(lambda: ImageEnhance.Brightness(lena()).enhance(0.5))
    assert_no_exception(lambda: ImageEnhance.Sharpness(lena()).enhance(0.5))

def test_crash():

    # crashes on small images
    im = Image.new("RGB", (1, 1))
    assert_no_exception(lambda: ImageEnhance.Sharpness(im).enhance(0.5))


########NEW FILE########
__FILENAME__ = test_imagefile
from tester import *

from PIL import Image
from PIL import ImageFile
from PIL import EpsImagePlugin

codecs = dir(Image.core)

# save original block sizes
MAXBLOCK = ImageFile.MAXBLOCK
SAFEBLOCK = ImageFile.SAFEBLOCK

def test_parser():

    def roundtrip(format):

        im = lena("L").resize((1000, 1000))
        if format in ("MSP", "XBM"):
            im = im.convert("1")

        file = BytesIO()

        im.save(file, format)

        data = file.getvalue()

        parser = ImageFile.Parser()
        parser.feed(data)
        imOut = parser.close()

        return im, imOut

    assert_image_equal(*roundtrip("BMP"))
    assert_image_equal(*roundtrip("GIF"))
    assert_image_equal(*roundtrip("IM"))
    assert_image_equal(*roundtrip("MSP"))
    if "zip_encoder" in codecs:
        try:
            # force multiple blocks in PNG driver
            ImageFile.MAXBLOCK = 8192
            assert_image_equal(*roundtrip("PNG"))
        finally:
            ImageFile.MAXBLOCK = MAXBLOCK
    assert_image_equal(*roundtrip("PPM"))
    assert_image_equal(*roundtrip("TIFF"))
    assert_image_equal(*roundtrip("XBM"))
    assert_image_equal(*roundtrip("TGA"))
    assert_image_equal(*roundtrip("PCX"))

    if EpsImagePlugin.has_ghostscript():
        im1, im2 = roundtrip("EPS")
        assert_image_similar(im1, im2.convert('L'),20) # EPS comes back in RGB      
    
    if "jpeg_encoder" in codecs:
        im1, im2 = roundtrip("JPEG") # lossy compression
        assert_image(im1, im2.mode, im2.size)

    # XXX Why assert exception and why does it fail?
    # https://github.com/python-imaging/Pillow/issues/78
    #assert_exception(IOError, lambda: roundtrip("PDF"))

def test_ico():
    with open('Tests/images/python.ico', 'rb') as f:
        data = f.read()
    p = ImageFile.Parser()
    p.feed(data)
    assert_equal((48,48), p.image.size)

def test_safeblock():

    im1 = lena()

    if "zip_encoder" not in codecs:
        skip("PNG (zlib) encoder not available")

    try:
        ImageFile.SAFEBLOCK = 1
        im2 = fromstring(tostring(im1, "PNG"))
    finally:
        ImageFile.SAFEBLOCK = SAFEBLOCK

    assert_image_equal(im1, im2)

########NEW FILE########
__FILENAME__ = test_imagefileio
from tester import *

from PIL import Image
from PIL import ImageFileIO

def test_fileio():

    class DumbFile:
        def __init__(self, data):
            self.data = data
        def read(self, bytes=None):
            assert_equal(bytes, None)
            return self.data
        def close(self):
            pass

    im1 = lena()

    io = ImageFileIO.ImageFileIO(DumbFile(tostring(im1, "PPM")))

    im2 = Image.open(io)
    assert_image_equal(im1, im2)



########NEW FILE########
__FILENAME__ = test_imagefilter
from tester import *

from PIL import Image
from PIL import ImageFilter

def test_sanity():
    # see test_image_filter for more tests

    assert_no_exception(lambda: ImageFilter.MaxFilter)
    assert_no_exception(lambda: ImageFilter.MedianFilter)
    assert_no_exception(lambda: ImageFilter.MinFilter)
    assert_no_exception(lambda: ImageFilter.ModeFilter)
    assert_no_exception(lambda: ImageFilter.Kernel((3, 3), list(range(9))))
    assert_no_exception(lambda: ImageFilter.GaussianBlur)
    assert_no_exception(lambda: ImageFilter.GaussianBlur(5))
    assert_no_exception(lambda: ImageFilter.UnsharpMask)
    assert_no_exception(lambda: ImageFilter.UnsharpMask(10))

    assert_no_exception(lambda: ImageFilter.BLUR)
    assert_no_exception(lambda: ImageFilter.CONTOUR)
    assert_no_exception(lambda: ImageFilter.DETAIL)
    assert_no_exception(lambda: ImageFilter.EDGE_ENHANCE)
    assert_no_exception(lambda: ImageFilter.EDGE_ENHANCE_MORE)
    assert_no_exception(lambda: ImageFilter.EMBOSS)
    assert_no_exception(lambda: ImageFilter.FIND_EDGES)
    assert_no_exception(lambda: ImageFilter.SMOOTH)
    assert_no_exception(lambda: ImageFilter.SMOOTH_MORE)
    assert_no_exception(lambda: ImageFilter.SHARPEN)




########NEW FILE########
__FILENAME__ = test_imagefont
from tester import *

from PIL import Image
from io import BytesIO
import os

try:
    from PIL import ImageFont
    ImageFont.core.getfont # check if freetype is available
except ImportError:
    skip()

from PIL import ImageDraw

font_path = "Tests/fonts/FreeMono.ttf"
font_size=20

def test_sanity():
    assert_match(ImageFont.core.freetype2_version, "\d+\.\d+\.\d+$")

def test_font_with_name():
    assert_no_exception(lambda: ImageFont.truetype(font_path, font_size))
    assert_no_exception(lambda: _render(font_path))
    _clean()

def _font_as_bytes():
    with open(font_path, 'rb') as f:
        font_bytes = BytesIO(f.read())
    return font_bytes

def test_font_with_filelike():
    assert_no_exception(lambda: ImageFont.truetype(_font_as_bytes(), font_size))
    assert_no_exception(lambda: _render(_font_as_bytes()))
    # Usage note:  making two fonts from the same buffer fails.
    #shared_bytes = _font_as_bytes()
    #assert_no_exception(lambda: _render(shared_bytes))
    #assert_exception(Exception, lambda: _render(shared_bytes))
    _clean()

def test_font_with_open_file():
    with open(font_path, 'rb') as f:
        assert_no_exception(lambda: _render(f))
    _clean()

def test_font_old_parameters():
    assert_warning(DeprecationWarning, lambda: ImageFont.truetype(filename=font_path, size=font_size))

def _render(font):
    txt = "Hello World!"
    ttf = ImageFont.truetype(font, font_size)
    w, h = ttf.getsize(txt)
    img = Image.new("RGB", (256, 64), "white")
    d = ImageDraw.Draw(img)
    d.text((10, 10), txt, font=ttf, fill='black')

    img.save('font.png')
    return img

def _clean():
    os.unlink('font.png')

def test_render_equal():
    img_path = _render(font_path)
    with open(font_path, 'rb') as f:
        font_filelike = BytesIO(f.read())
    img_filelike = _render(font_filelike)

    assert_image_equal(img_path, img_filelike)
    _clean()


def test_render_multiline():
    im = Image.new(mode='RGB', size=(300,100))
    draw = ImageDraw.Draw(im)
    ttf = ImageFont.truetype(font_path, font_size)
    line_spacing = draw.textsize('A', font=ttf)[1] + 8
    lines = ['hey you', 'you are awesome', 'this looks awkward']
    y = 0
    for line in lines:
        draw.text((0, y), line, font=ttf)
        y += line_spacing


    target = 'Tests/images/multiline_text.png'
    target_img = Image.open(target)
	
	# some versions of freetype have different horizontal spacing.
	# setting a tight epsilon, I'm showing the original test failure
	# at epsilon = ~38.
    assert_image_similar(im, target_img,.5)


def test_rotated_transposed_font():
    img_grey = Image.new("L", (100, 100))
    draw = ImageDraw.Draw(img_grey)
    word = "testing"
    font = ImageFont.truetype(font_path, font_size)

    orientation = Image.ROTATE_90
    transposed_font = ImageFont.TransposedFont(font, orientation=orientation)

    # Original font
    draw.setfont(font)
    box_size_a = draw.textsize(word)

    # Rotated font
    draw.setfont(transposed_font)
    box_size_b = draw.textsize(word)

    # Check (w,h) of box a is (h,w) of box b
    assert_equal(box_size_a[0], box_size_b[1])
    assert_equal(box_size_a[1], box_size_b[0])


def test_unrotated_transposed_font():
    img_grey = Image.new("L", (100, 100))
    draw = ImageDraw.Draw(img_grey)
    word = "testing"
    font = ImageFont.truetype(font_path, font_size)

    orientation = None
    transposed_font = ImageFont.TransposedFont(font, orientation=orientation)

    # Original font
    draw.setfont(font)
    box_size_a = draw.textsize(word)

    # Rotated font
    draw.setfont(transposed_font)
    box_size_b = draw.textsize(word)

    # Check boxes a and b are same size
    assert_equal(box_size_a, box_size_b)



########NEW FILE########
__FILENAME__ = test_imagegrab
from tester import *

from PIL import Image
try:
    from PIL import ImageGrab
except ImportError as v:
    skip(v)

def test_grab():
    im = ImageGrab.grab()
    assert_image(im, im.mode, im.size)



########NEW FILE########
__FILENAME__ = test_imagemath
from tester import *

from PIL import Image
from PIL import ImageMath

def pixel(im):
    if hasattr(im, "im"):
        return "%s %r" % (im.mode, im.getpixel((0, 0)))
    else:
        if isinstance(im, type(0)):
            return int(im) # hack to deal with booleans
        print(im)

A = Image.new("L", (1, 1), 1)
B = Image.new("L", (1, 1), 2)
F = Image.new("F", (1, 1), 3)
I = Image.new("I", (1, 1), 4)

images = {"A": A, "B": B, "F": F, "I": I}

def test_sanity():
    assert_equal(ImageMath.eval("1"), 1)
    assert_equal(ImageMath.eval("1+A", A=2), 3)
    assert_equal(pixel(ImageMath.eval("A+B", A=A, B=B)), "I 3")
    assert_equal(pixel(ImageMath.eval("A+B", images)), "I 3")
    assert_equal(pixel(ImageMath.eval("float(A)+B", images)), "F 3.0")
    assert_equal(pixel(ImageMath.eval("int(float(A)+B)", images)), "I 3")

def test_ops():

    assert_equal(pixel(ImageMath.eval("-A", images)), "I -1")
    assert_equal(pixel(ImageMath.eval("+B", images)), "L 2")

    assert_equal(pixel(ImageMath.eval("A+B", images)), "I 3")
    assert_equal(pixel(ImageMath.eval("A-B", images)), "I -1")
    assert_equal(pixel(ImageMath.eval("A*B", images)), "I 2")
    assert_equal(pixel(ImageMath.eval("A/B", images)), "I 0")
    assert_equal(pixel(ImageMath.eval("B**2", images)), "I 4")
    assert_equal(pixel(ImageMath.eval("B**33", images)), "I 2147483647")

    assert_equal(pixel(ImageMath.eval("float(A)+B", images)), "F 3.0")
    assert_equal(pixel(ImageMath.eval("float(A)-B", images)), "F -1.0")
    assert_equal(pixel(ImageMath.eval("float(A)*B", images)), "F 2.0")
    assert_equal(pixel(ImageMath.eval("float(A)/B", images)), "F 0.5")
    assert_equal(pixel(ImageMath.eval("float(B)**2", images)), "F 4.0")
    assert_equal(pixel(ImageMath.eval("float(B)**33", images)), "F 8589934592.0")

def test_logical():
    assert_equal(pixel(ImageMath.eval("not A", images)), 0)
    assert_equal(pixel(ImageMath.eval("A and B", images)), "L 2")
    assert_equal(pixel(ImageMath.eval("A or B", images)), "L 1")

def test_convert():
    assert_equal(pixel(ImageMath.eval("convert(A+B, 'L')", images)), "L 3")
    assert_equal(pixel(ImageMath.eval("convert(A+B, '1')", images)), "1 0")
    assert_equal(pixel(ImageMath.eval("convert(A+B, 'RGB')", images)), "RGB (3, 3, 3)")

def test_compare():
    assert_equal(pixel(ImageMath.eval("min(A, B)", images)), "I 1")
    assert_equal(pixel(ImageMath.eval("max(A, B)", images)), "I 2")
    assert_equal(pixel(ImageMath.eval("A == 1", images)), "I 1")
    assert_equal(pixel(ImageMath.eval("A == 2", images)), "I 0")

########NEW FILE########
__FILENAME__ = test_imagemode
from tester import *

from PIL import Image
from PIL import ImageMode

ImageMode.getmode("1")
ImageMode.getmode("L")
ImageMode.getmode("P")
ImageMode.getmode("RGB")
ImageMode.getmode("I")
ImageMode.getmode("F")

m = ImageMode.getmode("1")
assert_equal(m.mode, "1")
assert_equal(m.bands, ("1",))
assert_equal(m.basemode, "L")
assert_equal(m.basetype, "L")

m = ImageMode.getmode("RGB")
assert_equal(m.mode, "RGB")
assert_equal(m.bands, ("R", "G", "B"))
assert_equal(m.basemode, "RGB")
assert_equal(m.basetype, "L")

########NEW FILE########
__FILENAME__ = test_imageops
from tester import *

from PIL import Image
from PIL import ImageOps

class Deformer:
    def getmesh(self, im):
        x, y = im.size
        return [((0, 0, x, y), (0, 0, x, 0, x, y, y, 0))]

deformer = Deformer()

def test_sanity():

    ImageOps.autocontrast(lena("L"))
    ImageOps.autocontrast(lena("RGB"))

    ImageOps.autocontrast(lena("L"), cutoff=10)
    ImageOps.autocontrast(lena("L"), ignore=[0, 255])

    ImageOps.colorize(lena("L"), (0, 0, 0), (255, 255, 255))
    ImageOps.colorize(lena("L"), "black", "white")

    ImageOps.crop(lena("L"), 1)
    ImageOps.crop(lena("RGB"), 1)

    ImageOps.deform(lena("L"), deformer)
    ImageOps.deform(lena("RGB"), deformer)

    ImageOps.equalize(lena("L"))
    ImageOps.equalize(lena("RGB"))

    ImageOps.expand(lena("L"), 1)
    ImageOps.expand(lena("RGB"), 1)
    ImageOps.expand(lena("L"), 2, "blue")
    ImageOps.expand(lena("RGB"), 2, "blue")

    ImageOps.fit(lena("L"), (128, 128))
    ImageOps.fit(lena("RGB"), (128, 128))

    ImageOps.flip(lena("L"))
    ImageOps.flip(lena("RGB"))

    ImageOps.grayscale(lena("L"))
    ImageOps.grayscale(lena("RGB"))

    ImageOps.invert(lena("L"))
    ImageOps.invert(lena("RGB"))

    ImageOps.mirror(lena("L"))
    ImageOps.mirror(lena("RGB"))

    ImageOps.posterize(lena("L"), 4)
    ImageOps.posterize(lena("RGB"), 4)

    ImageOps.solarize(lena("L"))
    ImageOps.solarize(lena("RGB"))

    success()

def test_1pxfit():
    # Division by zero in equalize if image is 1 pixel high
    newimg = ImageOps.fit(lena("RGB").resize((1,1)), (35,35))
    assert_equal(newimg.size,(35,35))
    
    newimg = ImageOps.fit(lena("RGB").resize((1,100)), (35,35))
    assert_equal(newimg.size,(35,35))

    newimg = ImageOps.fit(lena("RGB").resize((100,1)), (35,35))
    assert_equal(newimg.size,(35,35))

def test_pil163():
    # Division by zero in equalize if < 255 pixels in image (@PIL163)

    i = lena("RGB").resize((15, 16))

    ImageOps.equalize(i.convert("L"))
    ImageOps.equalize(i.convert("P"))
    ImageOps.equalize(i.convert("RGB"))

    success()

########NEW FILE########
__FILENAME__ = test_imageops_usm
from tester import *

from PIL import Image
from PIL import ImageOps
from PIL import ImageFilter

im = Image.open("Images/lena.ppm")

def test_ops_api():

    i = ImageOps.gaussian_blur(im, 2.0)
    assert_equal(i.mode, "RGB")
    assert_equal(i.size, (128, 128))
    # i.save("blur.bmp")

    i = ImageOps.usm(im, 2.0, 125, 8)
    assert_equal(i.mode, "RGB")
    assert_equal(i.size, (128, 128))
    # i.save("usm.bmp")

def test_filter_api():

    filter = ImageFilter.GaussianBlur(2.0)
    i = im.filter(filter)
    assert_equal(i.mode, "RGB")
    assert_equal(i.size, (128, 128))

    filter = ImageFilter.UnsharpMask(2.0, 125, 8)
    i = im.filter(filter)
    assert_equal(i.mode, "RGB")
    assert_equal(i.size, (128, 128))

def test_usm():

    usm = ImageOps.unsharp_mask
    assert_exception(ValueError, lambda: usm(im.convert("1")))
    assert_no_exception(lambda: usm(im.convert("L")))
    assert_exception(ValueError, lambda: usm(im.convert("I")))
    assert_exception(ValueError, lambda: usm(im.convert("F")))
    assert_no_exception(lambda: usm(im.convert("RGB")))
    assert_no_exception(lambda: usm(im.convert("RGBA")))
    assert_no_exception(lambda: usm(im.convert("CMYK")))
    assert_exception(ValueError, lambda: usm(im.convert("YCbCr")))

def test_blur():

    blur = ImageOps.gaussian_blur
    assert_exception(ValueError, lambda: blur(im.convert("1")))
    assert_no_exception(lambda: blur(im.convert("L")))
    assert_exception(ValueError, lambda: blur(im.convert("I")))
    assert_exception(ValueError, lambda: blur(im.convert("F")))
    assert_no_exception(lambda: blur(im.convert("RGB")))
    assert_no_exception(lambda: blur(im.convert("RGBA")))
    assert_no_exception(lambda: blur(im.convert("CMYK")))
    assert_exception(ValueError, lambda: blur(im.convert("YCbCr")))

########NEW FILE########
__FILENAME__ = test_imagepalette
from tester import *

from PIL import Image
from PIL import ImagePalette

ImagePalette = ImagePalette.ImagePalette

def test_sanity():

    assert_no_exception(lambda: ImagePalette("RGB", list(range(256))*3))
    assert_exception(ValueError, lambda: ImagePalette("RGB", list(range(256))*2))

def test_getcolor():

    palette = ImagePalette()

    map = {}
    for i in range(256):
        map[palette.getcolor((i, i, i))] = i

    assert_equal(len(map), 256)
    assert_exception(ValueError, lambda: palette.getcolor((1, 2, 3)))

def test_file():

    palette = ImagePalette()

    file = tempfile("temp.lut")

    palette.save(file)

    from PIL.ImagePalette import load, raw

    p = load(file)

    # load returns raw palette information
    assert_equal(len(p[0]), 768)
    assert_equal(p[1], "RGB")

    p = raw(p[1], p[0])
    assert_true(isinstance(p, ImagePalette))




########NEW FILE########
__FILENAME__ = test_imagepath
from tester import *

from PIL import Image
from PIL import ImagePath

import array

def test_path():

    p = ImagePath.Path(list(range(10)))

    # sequence interface
    assert_equal(len(p), 5)
    assert_equal(p[0], (0.0, 1.0))
    assert_equal(p[-1], (8.0, 9.0))
    assert_equal(list(p[:1]), [(0.0, 1.0)])
    assert_equal(list(p), [(0.0, 1.0), (2.0, 3.0), (4.0, 5.0), (6.0, 7.0), (8.0, 9.0)])

    # method sanity check
    assert_equal(p.tolist(), [(0.0, 1.0), (2.0, 3.0), (4.0, 5.0), (6.0, 7.0), (8.0, 9.0)])
    assert_equal(p.tolist(1), [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0])

    assert_equal(p.getbbox(), (0.0, 1.0, 8.0, 9.0))

    assert_equal(p.compact(5), 2)
    assert_equal(list(p), [(0.0, 1.0), (4.0, 5.0), (8.0, 9.0)])

    p.transform((1,0,1,0,1,1))
    assert_equal(list(p), [(1.0, 2.0), (5.0, 6.0), (9.0, 10.0)])

    # alternative constructors
    p = ImagePath.Path([0, 1])
    assert_equal(list(p), [(0.0, 1.0)])
    p = ImagePath.Path([0.0, 1.0])
    assert_equal(list(p), [(0.0, 1.0)])
    p = ImagePath.Path([0, 1])
    assert_equal(list(p), [(0.0, 1.0)])
    p = ImagePath.Path([(0, 1)])
    assert_equal(list(p), [(0.0, 1.0)])
    p = ImagePath.Path(p)
    assert_equal(list(p), [(0.0, 1.0)])
    p = ImagePath.Path(p.tolist(0))
    assert_equal(list(p), [(0.0, 1.0)])
    p = ImagePath.Path(p.tolist(1))
    assert_equal(list(p), [(0.0, 1.0)])
    p = ImagePath.Path(array.array("f", [0, 1]))
    assert_equal(list(p), [(0.0, 1.0)])

    arr = array.array("f", [0, 1])
    if hasattr(arr, 'tobytes'):
        p = ImagePath.Path(arr.tobytes())
    else:
        p = ImagePath.Path(arr.tostring())
    assert_equal(list(p), [(0.0, 1.0)])

########NEW FILE########
__FILENAME__ = test_imageqt
from tester import *

from PIL import Image

try:
    from PyQt5.QtGui import QImage, qRgb, qRgba
except:
    try:
        from PyQt4.QtGui import QImage, qRgb, qRgba
    except:
        skip('PyQT4 or 5 not installed')

from PIL import ImageQt

def test_rgb():
    # from https://qt-project.org/doc/qt-4.8/qcolor.html
    # typedef QRgb
    # An ARGB quadruplet on the format #AARRGGBB, equivalent to an unsigned int.

    assert_equal(qRgb(0,0,0), qRgba(0,0,0,255))
    
    def checkrgb(r,g,b):
        val = ImageQt.rgb(r,g,b)
        val = val % 2**24 # drop the alpha
        assert_equal(val >> 16, r)
        assert_equal(((val >> 8 ) % 2**8), g)
        assert_equal(val % 2**8, b)
        
    checkrgb(0,0,0)
    checkrgb(255,0,0)
    checkrgb(0,255,0)
    checkrgb(0,0,255)


def test_image():
    for mode in ('1', 'RGB', 'RGBA', 'L', 'P'):
        assert_no_exception(lambda: ImageQt.ImageQt(lena(mode)))

########NEW FILE########
__FILENAME__ = test_imagesequence
from tester import *

from PIL import Image
from PIL import ImageSequence

def test_sanity():

    file = tempfile("temp.im")

    im = lena("RGB")
    im.save(file)

    seq = ImageSequence.Iterator(im)

    index = 0
    for frame in seq:
        assert_image_equal(im, frame)
        assert_equal(im.tell(), index)
        index = index + 1

    assert_equal(index, 1)


########NEW FILE########
__FILENAME__ = test_imageshow
from tester import *

from PIL import Image
from PIL import ImageShow

success()

########NEW FILE########
__FILENAME__ = test_imagestat
from tester import *

from PIL import Image
from PIL import ImageStat

def test_sanity():

    im = lena()

    st = ImageStat.Stat(im)
    st = ImageStat.Stat(im.histogram())
    st = ImageStat.Stat(im, Image.new("1", im.size, 1))

    assert_no_exception(lambda: st.extrema)
    assert_no_exception(lambda: st.sum)
    assert_no_exception(lambda: st.mean)
    assert_no_exception(lambda: st.median)
    assert_no_exception(lambda: st.rms)
    assert_no_exception(lambda: st.sum2)
    assert_no_exception(lambda: st.var)
    assert_no_exception(lambda: st.stddev)
    assert_exception(AttributeError, lambda: st.spam)

    assert_exception(TypeError, lambda: ImageStat.Stat(1))

def test_lena():

    im = lena()

    st = ImageStat.Stat(im)

    # verify a few values
    assert_equal(st.extrema[0], (61, 255))
    assert_equal(st.median[0], 197)
    assert_equal(st.sum[0], 2954416)
    assert_equal(st.sum[1], 2027250)
    assert_equal(st.sum[2], 1727331)

def test_constant():

    im = Image.new("L", (128, 128), 128)

    st = ImageStat.Stat(im)

    assert_equal(st.extrema[0], (128, 128))
    assert_equal(st.sum[0], 128**3)
    assert_equal(st.sum2[0], 128**4)
    assert_equal(st.mean[0], 128)
    assert_equal(st.median[0], 128)
    assert_equal(st.rms[0], 128)
    assert_equal(st.var[0], 0)
    assert_equal(st.stddev[0], 0)

########NEW FILE########
__FILENAME__ = test_imagetk
from tester import *

from PIL import Image
try:
    from PIL import ImageTk
except (OSError, ImportError) as v:
    skip(v)

success()

########NEW FILE########
__FILENAME__ = test_imagetransform
from tester import *

from PIL import Image
from PIL import ImageTransform

im = Image.new("L", (100, 100))

seq = tuple(range(10))

def test_sanity():
    transform = ImageTransform.AffineTransform(seq[:6])
    assert_no_exception(lambda: im.transform((100, 100), transform))
    transform = ImageTransform.ExtentTransform(seq[:4])
    assert_no_exception(lambda: im.transform((100, 100), transform))
    transform = ImageTransform.QuadTransform(seq[:8])
    assert_no_exception(lambda: im.transform((100, 100), transform))
    transform = ImageTransform.MeshTransform([(seq[:4], seq[:8])])
    assert_no_exception(lambda: im.transform((100, 100), transform))

########NEW FILE########
__FILENAME__ = test_imagewin
from tester import *

from PIL import Image
from PIL import ImageWin

success()

########NEW FILE########
__FILENAME__ = test_image_array
from tester import *

from PIL import Image

im = lena().resize((128, 100))

def test_toarray():
    def test(mode):
        ai = im.convert(mode).__array_interface__
        return ai["shape"], ai["typestr"], len(ai["data"])
    # assert_equal(test("1"), ((100, 128), '|b1', 1600))
    assert_equal(test("L"), ((100, 128), '|u1', 12800))
    assert_equal(test("I"), ((100, 128), Image._ENDIAN + 'i4', 51200)) # FIXME: wrong?
    assert_equal(test("F"), ((100, 128), Image._ENDIAN + 'f4', 51200)) # FIXME: wrong?
    assert_equal(test("RGB"), ((100, 128, 3), '|u1', 38400))
    assert_equal(test("RGBA"), ((100, 128, 4), '|u1', 51200))
    assert_equal(test("RGBX"), ((100, 128, 4), '|u1', 51200))

def test_fromarray():
    def test(mode):
        i = im.convert(mode)
        a = i.__array_interface__
        a["strides"] = 1 # pretend it's non-contigous
        i.__array_interface__ = a # patch in new version of attribute
        out = Image.fromarray(i)
        return out.mode, out.size, list(i.getdata()) == list(out.getdata())
    # assert_equal(test("1"), ("1", (128, 100), True))
    assert_equal(test("L"), ("L", (128, 100), True))
    assert_equal(test("I"), ("I", (128, 100), True))
    assert_equal(test("F"), ("F", (128, 100), True))
    assert_equal(test("RGB"), ("RGB", (128, 100), True))
    assert_equal(test("RGBA"), ("RGBA", (128, 100), True))
    assert_equal(test("RGBX"), ("RGBA", (128, 100), True))

########NEW FILE########
__FILENAME__ = test_image_convert
from tester import *

from PIL import Image


def test_sanity():

    def convert(im, mode):
        out = im.convert(mode)
        assert_equal(out.mode, mode)
        assert_equal(out.size, im.size)

    modes = "1", "L", "I", "F", "RGB", "RGBA", "RGBX", "CMYK", "YCbCr"

    for mode in modes:
        im = lena(mode)
        for mode in modes:
            yield_test(convert, im, mode)


def test_default():

    im = lena("P")
    assert_image(im, "P", im.size)
    im = im.convert()
    assert_image(im, "RGB", im.size)
    im = im.convert()
    assert_image(im, "RGB", im.size)


# ref https://github.com/python-imaging/Pillow/issues/274

def _test_float_conversion(im):
    orig = im.getpixel((5, 5))
    converted = im.convert('F').getpixel((5, 5))
    assert_equal(orig, converted)


def test_8bit():
    im = Image.open('Images/lena.jpg')
    _test_float_conversion(im.convert('L'))


def test_16bit():
    im = Image.open('Tests/images/16bit.cropped.tif')
    _test_float_conversion(im)


def test_16bit_workaround():
    im = Image.open('Tests/images/16bit.cropped.tif')
    _test_float_conversion(im.convert('I'))


def test_rgba_p():
    im = lena('RGBA')
    im.putalpha(lena('L'))

    converted = im.convert('P')
    comparable = converted.convert('RGBA')

    assert_image_similar(im, comparable, 20)


def test_trns_p():
    im = lena('P')
    im.info['transparency'] = 0

    f = tempfile('temp.png')

    l = im.convert('L')
    assert_equal(l.info['transparency'], 0)  # undone
    assert_no_exception(lambda: l.save(f))

    rgb = im.convert('RGB')
    assert_equal(rgb.info['transparency'], (0, 0, 0))  # undone
    assert_no_exception(lambda: rgb.save(f))


# ref https://github.com/python-imaging/Pillow/issues/664

def test_trns_p_rgba():
    # Arrange
    im = lena('P')
    im.info['transparency'] = 128

    # Act
    rgba = im.convert('RGBA')

    # Assert
    assert_false('transparency' in rgba.info)


def test_trns_l():
    im = lena('L')
    im.info['transparency'] = 128

    f = tempfile('temp.png')

    rgb = im.convert('RGB')
    assert_equal(rgb.info['transparency'], (128, 128, 128))  # undone
    assert_no_exception(lambda: rgb.save(f))

    p = im.convert('P')
    assert_true('transparency' in p.info)
    assert_no_exception(lambda: p.save(f))

    p = assert_warning(UserWarning,
                       lambda: im.convert('P', palette=Image.ADAPTIVE))
    assert_false('transparency' in p.info)
    assert_no_exception(lambda: p.save(f))


def test_trns_RGB():
    im = lena('RGB')
    im.info['transparency'] = im.getpixel((0, 0))

    f = tempfile('temp.png')

    l = im.convert('L')
    assert_equal(l.info['transparency'], l.getpixel((0, 0)))  # undone
    assert_no_exception(lambda: l.save(f))

    p = im.convert('P')
    assert_true('transparency' in p.info)
    assert_no_exception(lambda: p.save(f))

    p = assert_warning(UserWarning,
                       lambda: im.convert('P', palette=Image.ADAPTIVE))
    assert_false('transparency' in p.info)
    assert_no_exception(lambda: p.save(f))

########NEW FILE########
__FILENAME__ = test_image_copy
from tester import *

from PIL import Image

def test_copy():
    def copy(mode):
        im = lena(mode)
        out = im.copy()
        assert_equal(out.mode, mode)
        assert_equal(out.size, im.size)
    for mode in "1", "P", "L", "RGB", "I", "F":
        yield_test(copy, mode)

########NEW FILE########
__FILENAME__ = test_image_crop
from tester import *

from PIL import Image

def test_crop():
    def crop(mode):
        out = lena(mode).crop((50, 50, 100, 100))
        assert_equal(out.mode, mode)
        assert_equal(out.size, (50, 50))
    for mode in "1", "P", "L", "RGB", "I", "F":
        yield_test(crop, mode)

def test_wide_crop():

    def crop(*bbox):
        i = im.crop(bbox)
        h = i.histogram()
        while h and not h[-1]:
            del h[-1]
        return tuple(h)

    im = Image.new("L", (100, 100), 1)

    assert_equal(crop(0, 0, 100, 100), (0, 10000))
    assert_equal(crop(25, 25, 75, 75), (0, 2500))

    # sides
    assert_equal(crop(-25, 0, 25, 50), (1250, 1250))
    assert_equal(crop(0, -25, 50, 25), (1250, 1250))
    assert_equal(crop(75, 0, 125, 50), (1250, 1250))
    assert_equal(crop(0, 75, 50, 125), (1250, 1250))

    assert_equal(crop(-25, 25, 125, 75), (2500, 5000))
    assert_equal(crop(25, -25, 75, 125), (2500, 5000))

    # corners
    assert_equal(crop(-25, -25, 25, 25), (1875, 625))
    assert_equal(crop(75, -25, 125, 25), (1875, 625))
    assert_equal(crop(75, 75, 125, 125), (1875, 625))
    assert_equal(crop(-25, 75, 25, 125), (1875, 625))

# --------------------------------------------------------------------

def test_negative_crop():
    # Check negative crop size (@PIL171)

    im = Image.new("L", (512, 512))
    im = im.crop((400, 400, 200, 200))

    assert_equal(im.size, (0, 0))
    assert_equal(len(im.getdata()), 0)
    assert_exception(IndexError, lambda: im.getdata()[0])

########NEW FILE########
__FILENAME__ = test_image_draft
from tester import *

from PIL import Image

codecs = dir(Image.core)

if "jpeg_encoder" not in codecs or "jpeg_decoder" not in codecs:
    skip("jpeg support not available")

filename = "Images/lena.jpg"

data = tostring(Image.open(filename).resize((512, 512)), "JPEG")

def draft(mode, size):
    im = fromstring(data)
    im.draft(mode, size)
    return im

def test_size():
    assert_equal(draft("RGB", (512, 512)).size, (512, 512))
    assert_equal(draft("RGB", (256, 256)).size, (256, 256))
    assert_equal(draft("RGB", (128, 128)).size, (128, 128))
    assert_equal(draft("RGB", (64, 64)).size, (64, 64))
    assert_equal(draft("RGB", (32, 32)).size, (64, 64))

def test_mode():
    assert_equal(draft("1", (512, 512)).mode, "RGB")
    assert_equal(draft("L", (512, 512)).mode, "L")
    assert_equal(draft("RGB", (512, 512)).mode, "RGB")
    assert_equal(draft("YCbCr", (512, 512)).mode, "YCbCr")

########NEW FILE########
__FILENAME__ = test_image_filter
from tester import *

from PIL import Image
from PIL import ImageFilter

def test_sanity():

    def filter(filter):
        im = lena("L")
        out = im.filter(filter)
        assert_equal(out.mode, im.mode)
        assert_equal(out.size, im.size)

    filter(ImageFilter.BLUR)
    filter(ImageFilter.CONTOUR)
    filter(ImageFilter.DETAIL)
    filter(ImageFilter.EDGE_ENHANCE)
    filter(ImageFilter.EDGE_ENHANCE_MORE)
    filter(ImageFilter.EMBOSS)
    filter(ImageFilter.FIND_EDGES)
    filter(ImageFilter.SMOOTH)
    filter(ImageFilter.SMOOTH_MORE)
    filter(ImageFilter.SHARPEN)
    filter(ImageFilter.MaxFilter)
    filter(ImageFilter.MedianFilter)
    filter(ImageFilter.MinFilter)
    filter(ImageFilter.ModeFilter)
    filter(ImageFilter.Kernel((3, 3), list(range(9))))

    assert_exception(TypeError, lambda: filter("hello"))

def test_crash():

    # crashes on small images
    im = Image.new("RGB", (1, 1))
    assert_no_exception(lambda: im.filter(ImageFilter.SMOOTH))

    im = Image.new("RGB", (2, 2))
    assert_no_exception(lambda: im.filter(ImageFilter.SMOOTH))

    im = Image.new("RGB", (3, 3))
    assert_no_exception(lambda: im.filter(ImageFilter.SMOOTH))

def test_modefilter():

    def modefilter(mode):
        im = Image.new(mode, (3, 3), None)
        im.putdata(list(range(9)))
        # image is:
        #   0 1 2
        #   3 4 5
        #   6 7 8
        mod = im.filter(ImageFilter.ModeFilter).getpixel((1, 1))
        im.putdata([0, 0, 1, 2, 5, 1, 5, 2, 0]) # mode=0
        mod2 = im.filter(ImageFilter.ModeFilter).getpixel((1, 1))
        return mod, mod2

    assert_equal(modefilter("1"), (4, 0))
    assert_equal(modefilter("L"), (4, 0))
    assert_equal(modefilter("P"), (4, 0))
    assert_equal(modefilter("RGB"), ((4, 0, 0), (0, 0, 0)))

def test_rankfilter():

    def rankfilter(mode):
        im = Image.new(mode, (3, 3), None)
        im.putdata(list(range(9)))
        # image is:
        #   0 1 2
        #   3 4 5
        #   6 7 8
        min = im.filter(ImageFilter.MinFilter).getpixel((1, 1))
        med = im.filter(ImageFilter.MedianFilter).getpixel((1, 1))
        max = im.filter(ImageFilter.MaxFilter).getpixel((1, 1))
        return min, med, max

    assert_equal(rankfilter("1"), (0, 4, 8))
    assert_equal(rankfilter("L"), (0, 4, 8))
    assert_exception(ValueError, lambda: rankfilter("P"))
    assert_equal(rankfilter("RGB"), ((0, 0, 0), (4, 0, 0), (8, 0, 0)))
    assert_equal(rankfilter("I"), (0, 4, 8))
    assert_equal(rankfilter("F"), (0.0, 4.0, 8.0))

########NEW FILE########
__FILENAME__ = test_image_frombytes
from tester import *

from PIL import Image

def test_sanity():
    im1 = lena()
    im2 = Image.frombytes(im1.mode, im1.size, im1.tobytes())

    assert_image_equal(im1, im2)


########NEW FILE########
__FILENAME__ = test_image_getbands
from tester import *

from PIL import Image

def test_getbands():

    assert_equal(Image.new("1", (1, 1)).getbands(), ("1",))
    assert_equal(Image.new("L", (1, 1)).getbands(), ("L",))
    assert_equal(Image.new("I", (1, 1)).getbands(), ("I",))
    assert_equal(Image.new("F", (1, 1)).getbands(), ("F",))
    assert_equal(Image.new("P", (1, 1)).getbands(), ("P",))
    assert_equal(Image.new("RGB", (1, 1)).getbands(), ("R", "G", "B"))
    assert_equal(Image.new("RGBA", (1, 1)).getbands(), ("R", "G", "B", "A"))
    assert_equal(Image.new("CMYK", (1, 1)).getbands(), ("C", "M", "Y", "K"))
    assert_equal(Image.new("YCbCr", (1, 1)).getbands(), ("Y", "Cb", "Cr"))

########NEW FILE########
__FILENAME__ = test_image_getbbox
from tester import *

from PIL import Image

def test_sanity():

    bbox = lena().getbbox()
    assert_true(isinstance(bbox, tuple))

def test_bbox():

    # 8-bit mode
    im = Image.new("L", (100, 100), 0)
    assert_equal(im.getbbox(), None)

    im.paste(255, (10, 25, 90, 75))
    assert_equal(im.getbbox(), (10, 25, 90, 75))

    im.paste(255, (25, 10, 75, 90))
    assert_equal(im.getbbox(), (10, 10, 90, 90))

    im.paste(255, (-10, -10, 110, 110))
    assert_equal(im.getbbox(), (0, 0, 100, 100))

    # 32-bit mode
    im = Image.new("RGB", (100, 100), 0)
    assert_equal(im.getbbox(), None)

    im.paste(255, (10, 25, 90, 75))
    assert_equal(im.getbbox(), (10, 25, 90, 75))

    im.paste(255, (25, 10, 75, 90))
    assert_equal(im.getbbox(), (10, 10, 90, 90))

    im.paste(255, (-10, -10, 110, 110))
    assert_equal(im.getbbox(), (0, 0, 100, 100))

########NEW FILE########
__FILENAME__ = test_image_getcolors
from tester import *

from PIL import Image

def test_getcolors():

    def getcolors(mode, limit=None):
        im = lena(mode)
        if limit:
            colors = im.getcolors(limit)
        else:
            colors = im.getcolors()
        if colors:
            return len(colors)
        return None

    assert_equal(getcolors("1"), 2)
    assert_equal(getcolors("L"), 193)
    assert_equal(getcolors("I"), 193)
    assert_equal(getcolors("F"), 193)
    assert_equal(getcolors("P"), 54) # fixed palette
    assert_equal(getcolors("RGB"), None)
    assert_equal(getcolors("RGBA"), None)
    assert_equal(getcolors("CMYK"), None)
    assert_equal(getcolors("YCbCr"), None)

    assert_equal(getcolors("L", 128), None)
    assert_equal(getcolors("L", 1024), 193)

    assert_equal(getcolors("RGB", 8192), None)
    assert_equal(getcolors("RGB", 16384), 14836)
    assert_equal(getcolors("RGB", 100000), 14836)

    assert_equal(getcolors("RGBA", 16384), 14836)
    assert_equal(getcolors("CMYK", 16384), 14836)
    assert_equal(getcolors("YCbCr", 16384), 11995)

# --------------------------------------------------------------------

def test_pack():
    # Pack problems for small tables (@PIL209)

    im = lena().quantize(3).convert("RGB")

    expected = [(3236, (227, 183, 147)), (6297, (143, 84, 81)), (6851, (208, 143, 112))]

    A = im.getcolors(maxcolors=2)
    assert_equal(A, None)

    A = im.getcolors(maxcolors=3)
    A.sort()
    assert_equal(A, expected)

    A = im.getcolors(maxcolors=4)
    A.sort()
    assert_equal(A, expected)

    A = im.getcolors(maxcolors=8)
    A.sort()
    assert_equal(A, expected)

    A = im.getcolors(maxcolors=16)
    A.sort()
    assert_equal(A, expected)

########NEW FILE########
__FILENAME__ = test_image_getdata
from tester import *

from PIL import Image

def test_sanity():

    data = lena().getdata()

    assert_no_exception(lambda: len(data))
    assert_no_exception(lambda: list(data))

    assert_equal(data[0], (223, 162, 133))

def test_roundtrip():

    def getdata(mode):
        im = lena(mode).resize((32, 30))
        data = im.getdata()
        return data[0], len(data), len(list(data))

    assert_equal(getdata("1"), (255, 960, 960))
    assert_equal(getdata("L"), (176, 960, 960))
    assert_equal(getdata("I"), (176, 960, 960))
    assert_equal(getdata("F"), (176.0, 960, 960))
    assert_equal(getdata("RGB"), ((223, 162, 133), 960, 960))
    assert_equal(getdata("RGBA"), ((223, 162, 133, 255), 960, 960))
    assert_equal(getdata("CMYK"), ((32, 93, 122, 0), 960, 960))
    assert_equal(getdata("YCbCr"), ((176, 103, 160), 960, 960))

########NEW FILE########
__FILENAME__ = test_image_getextrema
from tester import *

from PIL import Image

def test_extrema():

    def extrema(mode):
        return lena(mode).getextrema()

    assert_equal(extrema("1"), (0, 255))
    assert_equal(extrema("L"), (40, 235))
    assert_equal(extrema("I"), (40, 235))
    assert_equal(extrema("F"), (40.0, 235.0))
    assert_equal(extrema("P"), (11, 218)) # fixed palette
    assert_equal(extrema("RGB"), ((61, 255), (26, 234), (44, 223)))
    assert_equal(extrema("RGBA"), ((61, 255), (26, 234), (44, 223), (255, 255)))
    assert_equal(extrema("CMYK"), ((0, 194), (21, 229), (32, 211), (0, 0)))

########NEW FILE########
__FILENAME__ = test_image_getim
from tester import *

from PIL import Image

def test_sanity():

    im = lena()
    type_repr = repr(type(im.getim()))

    if py3:
        assert_true("PyCapsule" in type_repr)

    assert_true(isinstance(im.im.id, int))


########NEW FILE########
__FILENAME__ = test_image_getpalette
from tester import *

from PIL import Image

def test_palette():
    def palette(mode):
        p = lena(mode).getpalette()
        if p:
            return p[:10]
        return None
    assert_equal(palette("1"), None)
    assert_equal(palette("L"), None)
    assert_equal(palette("I"), None)
    assert_equal(palette("F"), None)
    assert_equal(palette("P"), [0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    assert_equal(palette("RGB"), None)
    assert_equal(palette("RGBA"), None)
    assert_equal(palette("CMYK"), None)
    assert_equal(palette("YCbCr"), None)

########NEW FILE########
__FILENAME__ = test_image_getpixel
from tester import *

from PIL import Image

Image.USE_CFFI_ACCESS=False

def color(mode):
    bands = Image.getmodebands(mode)
    if bands == 1:
        return 1
    else:
        return tuple(range(1, bands+1))



def check(mode, c=None):
    if not c:
        c = color(mode)
        
    #check putpixel
    im = Image.new(mode, (1, 1), None)
    im.putpixel((0, 0), c)
    assert_equal(im.getpixel((0, 0)), c,
                 "put/getpixel roundtrip failed for mode %s, color %s" %
                 (mode, c))
    
    # check inital color
    im = Image.new(mode, (1, 1), c)
    assert_equal(im.getpixel((0, 0)), c,
                 "initial color failed for mode %s, color %s " %
                 (mode, color))

def test_basic():    
    for mode in ("1", "L", "LA", "I", "I;16", "I;16B", "F",
                 "P", "PA", "RGB", "RGBA", "RGBX", "CMYK","YCbCr"):
        check(mode)

def test_signedness():
    # see https://github.com/python-imaging/Pillow/issues/452
    # pixelaccess is using signed int* instead of uint*
    for mode in ("I;16", "I;16B"):
        check(mode, 2**15-1)
        check(mode, 2**15)
        check(mode, 2**15+1)
        check(mode, 2**16-1)

                



########NEW FILE########
__FILENAME__ = test_image_getprojection
from tester import *

from PIL import Image

def test_sanity():

    im = lena()

    projection = im.getprojection()

    assert_equal(len(projection), 2)
    assert_equal(len(projection[0]), im.size[0])
    assert_equal(len(projection[1]), im.size[1])

    # 8-bit image
    im = Image.new("L", (10, 10))
    assert_equal(im.getprojection()[0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    assert_equal(im.getprojection()[1], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    im.paste(255, (2, 4, 8, 6))
    assert_equal(im.getprojection()[0], [0, 0, 1, 1, 1, 1, 1, 1, 0, 0])
    assert_equal(im.getprojection()[1], [0, 0, 0, 0, 1, 1, 0, 0, 0, 0])

    # 32-bit image
    im = Image.new("RGB", (10, 10))
    assert_equal(im.getprojection()[0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    assert_equal(im.getprojection()[1], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    im.paste(255, (2, 4, 8, 6))
    assert_equal(im.getprojection()[0], [0, 0, 1, 1, 1, 1, 1, 1, 0, 0])
    assert_equal(im.getprojection()[1], [0, 0, 0, 0, 1, 1, 0, 0, 0, 0])


########NEW FILE########
__FILENAME__ = test_image_histogram
from tester import *

from PIL import Image

def test_histogram():

    def histogram(mode):
        h = lena(mode).histogram()
        return len(h), min(h), max(h)

    assert_equal(histogram("1"), (256, 0, 8872))
    assert_equal(histogram("L"), (256, 0, 199))
    assert_equal(histogram("I"), (256, 0, 199))
    assert_equal(histogram("F"), (256, 0, 199))
    assert_equal(histogram("P"), (256, 0, 2912))
    assert_equal(histogram("RGB"), (768, 0, 285))
    assert_equal(histogram("RGBA"), (1024, 0, 16384))
    assert_equal(histogram("CMYK"), (1024, 0, 16384))
    assert_equal(histogram("YCbCr"), (768, 0, 741))

########NEW FILE########
__FILENAME__ = test_image_load
from tester import *

from PIL import Image

import os

def test_sanity():

    im = lena()

    pix = im.load()

    assert_equal(pix[0, 0], (223, 162, 133))

def test_close():    
    im = Image.open("Images/lena.gif")
    assert_no_exception(lambda: im.close())
    assert_exception(ValueError, lambda: im.load())
    assert_exception(ValueError, lambda: im.getpixel((0,0)))

def test_contextmanager():
    fn = None
    with Image.open("Images/lena.gif") as im:
        fn = im.fp.fileno()
        assert_no_exception(lambda: os.fstat(fn))

    assert_exception(OSError, lambda: os.fstat(fn))    

########NEW FILE########
__FILENAME__ = test_image_mode
from tester import *

from PIL import Image

def test_sanity():

    im = lena()
    assert_no_exception(lambda: im.mode)

def test_properties():
    def check(mode, *result):
        signature = (
            Image.getmodebase(mode), Image.getmodetype(mode),
            Image.getmodebands(mode), Image.getmodebandnames(mode),
            )
        assert_equal(signature, result)
    check("1", "L", "L", 1, ("1",))
    check("L", "L", "L", 1, ("L",))
    check("P", "RGB", "L", 1, ("P",))
    check("I", "L", "I", 1, ("I",))
    check("F", "L", "F", 1, ("F",))
    check("RGB", "RGB", "L", 3, ("R", "G", "B"))
    check("RGBA", "RGB", "L", 4, ("R", "G", "B", "A"))
    check("RGBX", "RGB", "L", 4, ("R", "G", "B", "X"))
    check("RGBX", "RGB", "L", 4, ("R", "G", "B", "X"))
    check("CMYK", "RGB", "L", 4, ("C", "M", "Y", "K"))
    check("YCbCr", "RGB", "L", 3, ("Y", "Cb", "Cr"))

########NEW FILE########
__FILENAME__ = test_image_offset
from tester import *

from PIL import Image

def test_offset():

    im1 = lena()

    im2 = assert_warning(DeprecationWarning, lambda: im1.offset(10))
    assert_equal(im1.getpixel((0, 0)), im2.getpixel((10, 10)))

    im2 = assert_warning(DeprecationWarning, lambda: im1.offset(10, 20))
    assert_equal(im1.getpixel((0, 0)), im2.getpixel((10, 20)))

    im2 = assert_warning(DeprecationWarning, lambda: im1.offset(20, 20))
    assert_equal(im1.getpixel((0, 0)), im2.getpixel((20, 20)))

########NEW FILE########
__FILENAME__ = test_image_paste
from tester import *

from PIL import Image

success()

########NEW FILE########
__FILENAME__ = test_image_point
from tester import *

from PIL import Image

if hasattr(sys, 'pypy_version_info'):
    # This takes _forever_ on pypy. Open Bug,
    # see https://github.com/python-imaging/Pillow/issues/484
    skip()

def test_sanity():

    im = lena()

    assert_exception(ValueError, lambda: im.point(list(range(256))))
    assert_no_exception(lambda: im.point(list(range(256))*3))
    assert_no_exception(lambda: im.point(lambda x: x))

    im = im.convert("I")
    assert_exception(ValueError, lambda: im.point(list(range(256))))
    assert_no_exception(lambda: im.point(lambda x: x*1))
    assert_no_exception(lambda: im.point(lambda x: x+1))
    assert_no_exception(lambda: im.point(lambda x: x*1+1))
    assert_exception(TypeError, lambda: im.point(lambda x: x-1))
    assert_exception(TypeError, lambda: im.point(lambda x: x/1))


def test_16bit_lut():
    """ Tests for 16 bit -> 8 bit lut for converting I->L images
        see https://github.com/python-imaging/Pillow/issues/440
    """

    im = lena("I")
    assert_no_exception(lambda: im.point(list(range(256))*256, 'L'))

########NEW FILE########
__FILENAME__ = test_image_putalpha
from tester import *

from PIL import Image

def test_interface():

    im = Image.new("RGBA", (1, 1), (1, 2, 3, 0))
    assert_equal(im.getpixel((0, 0)), (1, 2, 3, 0))

    im = Image.new("RGBA", (1, 1), (1, 2, 3))
    assert_equal(im.getpixel((0, 0)), (1, 2, 3, 255))

    im.putalpha(Image.new("L", im.size, 4))
    assert_equal(im.getpixel((0, 0)), (1, 2, 3, 4))

    im.putalpha(5)
    assert_equal(im.getpixel((0, 0)), (1, 2, 3, 5))

def test_promote():

    im = Image.new("L", (1, 1), 1)
    assert_equal(im.getpixel((0, 0)), 1)

    im.putalpha(2)
    assert_equal(im.mode, 'LA')
    assert_equal(im.getpixel((0, 0)), (1, 2))

    im = Image.new("RGB", (1, 1), (1, 2, 3))
    assert_equal(im.getpixel((0, 0)), (1, 2, 3))

    im.putalpha(4)
    assert_equal(im.mode, 'RGBA')
    assert_equal(im.getpixel((0, 0)), (1, 2, 3, 4))

def test_readonly():

    im = Image.new("RGB", (1, 1), (1, 2, 3))
    im.readonly = 1

    im.putalpha(4)
    assert_false(im.readonly)
    assert_equal(im.mode, 'RGBA')
    assert_equal(im.getpixel((0, 0)), (1, 2, 3, 4))

########NEW FILE########
__FILENAME__ = test_image_putdata
from tester import *

import sys

from PIL import Image

def test_sanity():

    im1 = lena()

    data = list(im1.getdata())

    im2 = Image.new(im1.mode, im1.size, 0)
    im2.putdata(data)

    assert_image_equal(im1, im2)

    # readonly
    im2 = Image.new(im1.mode, im2.size, 0)
    im2.readonly = 1
    im2.putdata(data)

    assert_false(im2.readonly)
    assert_image_equal(im1, im2)


def test_long_integers():
    # see bug-200802-systemerror
    def put(value):
        im = Image.new("RGBA", (1, 1))
        im.putdata([value])
        return im.getpixel((0, 0))
    assert_equal(put(0xFFFFFFFF), (255, 255, 255, 255))
    assert_equal(put(0xFFFFFFFF), (255, 255, 255, 255))
    assert_equal(put(-1), (255, 255, 255, 255))
    assert_equal(put(-1), (255, 255, 255, 255))
    if sys.maxsize > 2**32:
        assert_equal(put(sys.maxsize), (255, 255, 255, 255))
    else:
        assert_equal(put(sys.maxsize), (255, 255, 255, 127))

########NEW FILE########
__FILENAME__ = test_image_putpalette
from tester import *

from PIL import Image
from PIL import ImagePalette

def test_putpalette():
    def palette(mode):
        im = lena(mode).copy()
        im.putpalette(list(range(256))*3)
        p = im.getpalette()
        if p:
            return im.mode, p[:10]
        return im.mode
    assert_exception(ValueError, lambda: palette("1"))
    assert_equal(palette("L"), ("P", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]))
    assert_equal(palette("P"), ("P", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]))
    assert_exception(ValueError, lambda: palette("I"))
    assert_exception(ValueError, lambda: palette("F"))
    assert_exception(ValueError, lambda: palette("RGB"))
    assert_exception(ValueError, lambda: palette("RGBA"))
    assert_exception(ValueError, lambda: palette("YCbCr"))

def test_imagepalette():
    im = lena("P")
    assert_no_exception(lambda: im.putpalette(ImagePalette.negative()))
    assert_no_exception(lambda: im.putpalette(ImagePalette.random()))
    assert_no_exception(lambda: im.putpalette(ImagePalette.sepia()))
    assert_no_exception(lambda: im.putpalette(ImagePalette.wedge()))

########NEW FILE########
__FILENAME__ = test_image_putpixel
from tester import *

from PIL import Image

Image.USE_CFFI_ACCESS=False

def test_sanity():

    im1 = lena()
    im2 = Image.new(im1.mode, im1.size, 0)

    for y in range(im1.size[1]):
        for x in range(im1.size[0]):
            pos = x, y
            im2.putpixel(pos, im1.getpixel(pos))

    assert_image_equal(im1, im2)

    im2 = Image.new(im1.mode, im1.size, 0)
    im2.readonly = 1

    for y in range(im1.size[1]):
        for x in range(im1.size[0]):
            pos = x, y
            im2.putpixel(pos, im1.getpixel(pos))

    assert_false(im2.readonly)
    assert_image_equal(im1, im2)

    im2 = Image.new(im1.mode, im1.size, 0)

    pix1 = im1.load()
    pix2 = im2.load()

    for y in range(im1.size[1]):
        for x in range(im1.size[0]):
            pix2[x, y] = pix1[x, y]

    assert_image_equal(im1, im2)




# see test_image_getpixel for more tests


########NEW FILE########
__FILENAME__ = test_image_quantize
from tester import *

from PIL import Image

def test_sanity():

    im = lena()

    im = im.quantize()
    assert_image(im, "P", im.size)

    im = lena()
    im = im.quantize(palette=lena("P"))
    assert_image(im, "P", im.size)

def test_octree_quantize():
    im = lena()

    im = im.quantize(100, Image.FASTOCTREE)
    assert_image(im, "P", im.size)

    assert len(im.getcolors()) == 100

def test_rgba_quantize():
    im = lena('RGBA')
    assert_no_exception(lambda: im.quantize())
    assert_exception(Exception, lambda: im.quantize(method=0))

########NEW FILE########
__FILENAME__ = test_image_resize
from tester import *

from PIL import Image

def test_resize():
    def resize(mode, size):
        out = lena(mode).resize(size)
        assert_equal(out.mode, mode)
        assert_equal(out.size, size)
    for mode in "1", "P", "L", "RGB", "I", "F":
        yield_test(resize, mode, (100, 100))
        yield_test(resize, mode, (200, 200))

########NEW FILE########
__FILENAME__ = test_image_rotate
from tester import *

from PIL import Image

def test_rotate():
    def rotate(mode):
        im = lena(mode)
        out = im.rotate(45)
        assert_equal(out.mode, mode)
        assert_equal(out.size, im.size) # default rotate clips output
        out = im.rotate(45, expand=1)
        assert_equal(out.mode, mode)
        assert_true(out.size != im.size)
    for mode in "1", "P", "L", "RGB", "I", "F":
        yield_test(rotate, mode)

########NEW FILE########
__FILENAME__ = test_image_save
from tester import *

from PIL import Image

success()

########NEW FILE########
__FILENAME__ = test_image_seek
from tester import *

from PIL import Image

success()

########NEW FILE########
__FILENAME__ = test_image_show
from tester import *

from PIL import Image

success()

########NEW FILE########
__FILENAME__ = test_image_split
from tester import *

from PIL import Image

def test_split():
    def split(mode):
        layers = lena(mode).split()
        return [(i.mode, i.size[0], i.size[1]) for i in layers]
    assert_equal(split("1"), [('1', 128, 128)])
    assert_equal(split("L"), [('L', 128, 128)])
    assert_equal(split("I"), [('I', 128, 128)])
    assert_equal(split("F"), [('F', 128, 128)])
    assert_equal(split("P"), [('P', 128, 128)])
    assert_equal(split("RGB"), [('L', 128, 128), ('L', 128, 128), ('L', 128, 128)])
    assert_equal(split("RGBA"), [('L', 128, 128), ('L', 128, 128), ('L', 128, 128), ('L', 128, 128)])
    assert_equal(split("CMYK"), [('L', 128, 128), ('L', 128, 128), ('L', 128, 128), ('L', 128, 128)])
    assert_equal(split("YCbCr"), [('L', 128, 128), ('L', 128, 128), ('L', 128, 128)])

def test_split_merge():
    def split_merge(mode):
        return Image.merge(mode, lena(mode).split())
    assert_image_equal(lena("1"), split_merge("1"))
    assert_image_equal(lena("L"), split_merge("L"))
    assert_image_equal(lena("I"), split_merge("I"))
    assert_image_equal(lena("F"), split_merge("F"))
    assert_image_equal(lena("P"), split_merge("P"))
    assert_image_equal(lena("RGB"), split_merge("RGB"))
    assert_image_equal(lena("RGBA"), split_merge("RGBA"))
    assert_image_equal(lena("CMYK"), split_merge("CMYK"))
    assert_image_equal(lena("YCbCr"), split_merge("YCbCr"))

def test_split_open():
    codecs = dir(Image.core)

    if 'zip_encoder' in codecs:
        file = tempfile("temp.png")
    else:
        file = tempfile("temp.pcx")

    def split_open(mode):
        lena(mode).save(file)
        im = Image.open(file)
        return len(im.split())
    assert_equal(split_open("1"), 1)
    assert_equal(split_open("L"), 1)
    assert_equal(split_open("P"), 1)
    assert_equal(split_open("RGB"), 3)
    if 'zip_encoder' in codecs:
        assert_equal(split_open("RGBA"), 4)

########NEW FILE########
__FILENAME__ = test_image_tell
from tester import *

from PIL import Image

success()

########NEW FILE########
__FILENAME__ = test_image_thumbnail
from tester import *

from PIL import Image

def test_sanity():

    im = lena()
    im.thumbnail((100, 100))

    assert_image(im, im.mode, (100, 100))

def test_aspect():

    im = lena()
    im.thumbnail((100, 100))
    assert_image(im, im.mode, (100, 100))

    im = lena().resize((128, 256))
    im.thumbnail((100, 100))
    assert_image(im, im.mode, (50, 100))

    im = lena().resize((128, 256))
    im.thumbnail((50, 100))
    assert_image(im, im.mode, (50, 100))

    im = lena().resize((256, 128))
    im.thumbnail((100, 100))
    assert_image(im, im.mode, (100, 50))

    im = lena().resize((256, 128))
    im.thumbnail((100, 50))
    assert_image(im, im.mode, (100, 50))

    im = lena().resize((128, 128))
    im.thumbnail((100, 100))
    assert_image(im, im.mode, (100, 100))

########NEW FILE########
__FILENAME__ = test_image_tobitmap
from tester import *

from PIL import Image

def test_sanity():

    assert_exception(ValueError, lambda: lena().tobitmap())
    assert_no_exception(lambda: lena().convert("1").tobitmap())

    im1 = lena().convert("1")

    bitmap = im1.tobitmap()

    assert_true(isinstance(bitmap, bytes))
    assert_image_equal(im1, fromstring(bitmap))

########NEW FILE########
__FILENAME__ = test_image_tobytes
from tester import *

from PIL import Image

def test_sanity():
    data = lena().tobytes()
    assert_true(isinstance(data, bytes))

########NEW FILE########
__FILENAME__ = test_image_transform
from tester import *

from PIL import Image

def test_extent():
    im = lena('RGB')
    (w,h) = im.size
    transformed = im.transform(im.size, Image.EXTENT,
                               (0,0,
                                w//2,h//2), # ul -> lr
                               Image.BILINEAR)

    
    scaled = im.resize((w*2, h*2), Image.BILINEAR).crop((0,0,w,h))
    
    assert_image_similar(transformed, scaled, 10) # undone -- precision?

def test_quad():
    # one simple quad transform, equivalent to scale & crop upper left quad
    im = lena('RGB')
    (w,h) = im.size
    transformed = im.transform(im.size, Image.QUAD,
                               (0,0,0,h//2,
                                w//2,h//2,w//2,0), # ul -> ccw around quad
                               Image.BILINEAR)
    
    scaled = im.resize((w*2, h*2), Image.BILINEAR).crop((0,0,w,h))
    
    assert_image_equal(transformed, scaled)

def test_mesh():
    # this should be a checkerboard of halfsized lenas in ul, lr
    im = lena('RGBA')
    (w,h) = im.size
    transformed = im.transform(im.size, Image.MESH,
                               [((0,0,w//2,h//2), # box
                                (0,0,0,h,
                                 w,h,w,0)), # ul -> ccw around quad
                                ((w//2,h//2,w,h), # box
                                (0,0,0,h,
                                 w,h,w,0))], # ul -> ccw around quad
                               Image.BILINEAR)

    #transformed.save('transformed.png')

    scaled = im.resize((w//2, h//2), Image.BILINEAR)

    checker = Image.new('RGBA', im.size)
    checker.paste(scaled, (0,0))
    checker.paste(scaled, (w//2,h//2))
        
    assert_image_equal(transformed, checker) 

    # now, check to see that the extra area is (0,0,0,0)
    blank = Image.new('RGBA', (w//2,h//2), (0,0,0,0))

    assert_image_equal(blank, transformed.crop((w//2,0,w,h//2)))
    assert_image_equal(blank, transformed.crop((0,h//2,w//2,h)))

def _test_alpha_premult(op):
     # create image with half white, half black, with the black half transparent.
    # do op, 
    # there should be no darkness in the white section.
    im = Image.new('RGBA', (10,10), (0,0,0,0));
    im2 = Image.new('RGBA', (5,10), (255,255,255,255));
    im.paste(im2, (0,0))
    
    im = op(im, (40,10))
    im_background = Image.new('RGB', (40,10), (255,255,255))
    im_background.paste(im, (0,0), im)
    
    hist = im_background.histogram()
    assert_equal(40*10, hist[-1])

    
def test_alpha_premult_resize():

    def op (im, sz):
        return im.resize(sz, Image.LINEAR)
    
    _test_alpha_premult(op)
    
def test_alpha_premult_transform():
    
    def op(im, sz):
        (w,h) = im.size
        return im.transform(sz, Image.EXTENT,
                            (0,0,
                             w,h), 
                            Image.BILINEAR)

    _test_alpha_premult(op)


def test_blank_fill():
    # attempting to hit
    # https://github.com/python-imaging/Pillow/issues/254 reported
    #
    # issue is that transforms with transparent overflow area
    # contained junk from previous images, especially on systems with
    # constrained memory. So, attempt to fill up memory with a
    # pattern, free it, and then run the mesh test again. Using a 1Mp
    # image with 4 bands, for 4 megs of data allocated, x 64. OMM (64
    # bit 12.04 VM with 512 megs available, this fails with Pillow <
    # a0eaf06cc5f62a6fb6de556989ac1014ff3348ea
    #
    # Running by default, but I'd totally understand not doing it in
    # the future
    
    foo = [Image.new('RGBA',(1024,1024), (a,a,a,a))
             for a in range(1,65)]   

    # Yeah. Watch some JIT optimize this out. 
    foo = None

    test_mesh()

########NEW FILE########
__FILENAME__ = test_image_transpose
from tester import *

from PIL import Image

FLIP_LEFT_RIGHT = Image.FLIP_LEFT_RIGHT
FLIP_TOP_BOTTOM = Image.FLIP_TOP_BOTTOM
ROTATE_90 = Image.ROTATE_90
ROTATE_180 = Image.ROTATE_180
ROTATE_270 = Image.ROTATE_270

def test_sanity():

    im = lena()

    assert_no_exception(lambda: im.transpose(FLIP_LEFT_RIGHT))
    assert_no_exception(lambda: im.transpose(FLIP_TOP_BOTTOM))

    assert_no_exception(lambda: im.transpose(ROTATE_90))
    assert_no_exception(lambda: im.transpose(ROTATE_180))
    assert_no_exception(lambda: im.transpose(ROTATE_270))

def test_roundtrip():

    im = lena()

    def transpose(first, second):
        return im.transpose(first).transpose(second)

    assert_image_equal(im, transpose(FLIP_LEFT_RIGHT, FLIP_LEFT_RIGHT))
    assert_image_equal(im, transpose(FLIP_TOP_BOTTOM, FLIP_TOP_BOTTOM))

    assert_image_equal(im, transpose(ROTATE_90, ROTATE_270))
    assert_image_equal(im, transpose(ROTATE_180, ROTATE_180))


########NEW FILE########
__FILENAME__ = test_image_verify
from tester import *

from PIL import Image

success()

########NEW FILE########
__FILENAME__ = test_lib_image
from tester import *

from PIL import Image

def test_setmode():

    im = Image.new("L", (1, 1), 255)
    im.im.setmode("1")
    assert_equal(im.im.getpixel((0, 0)), 255)
    im.im.setmode("L")
    assert_equal(im.im.getpixel((0, 0)), 255)

    im = Image.new("1", (1, 1), 1)
    im.im.setmode("L")
    assert_equal(im.im.getpixel((0, 0)), 255)
    im.im.setmode("1")
    assert_equal(im.im.getpixel((0, 0)), 255)

    im = Image.new("RGB", (1, 1), (1, 2, 3))
    im.im.setmode("RGB")
    assert_equal(im.im.getpixel((0, 0)), (1, 2, 3))
    im.im.setmode("RGBA")
    assert_equal(im.im.getpixel((0, 0)), (1, 2, 3, 255))
    im.im.setmode("RGBX")
    assert_equal(im.im.getpixel((0, 0)), (1, 2, 3, 255))
    im.im.setmode("RGB")
    assert_equal(im.im.getpixel((0, 0)), (1, 2, 3))

    assert_exception(ValueError, lambda: im.im.setmode("L"))
    assert_exception(ValueError, lambda: im.im.setmode("RGBABCDE"))

########NEW FILE########
__FILENAME__ = test_lib_pack
from tester import *

from PIL import Image

def pack():
    pass # not yet

def test_pack():

    def pack(mode, rawmode):
        if len(mode) == 1:
            im = Image.new(mode, (1, 1), 1)
        else:
            im = Image.new(mode, (1, 1), (1, 2, 3, 4)[:len(mode)])

        if py3:
            return list(im.tobytes("raw", rawmode))
        else:
            return [ord(c) for c in im.tobytes("raw", rawmode)]

    order = 1 if Image._ENDIAN == '<' else -1

    assert_equal(pack("1", "1"), [128])
    assert_equal(pack("1", "1;I"), [0])
    assert_equal(pack("1", "1;R"), [1])
    assert_equal(pack("1", "1;IR"), [0])

    assert_equal(pack("L", "L"), [1])

    assert_equal(pack("I", "I"), [1, 0, 0, 0][::order])

    assert_equal(pack("F", "F"), [0, 0, 128, 63][::order])

    assert_equal(pack("LA", "LA"), [1, 2])

    assert_equal(pack("RGB", "RGB"), [1, 2, 3])
    assert_equal(pack("RGB", "RGB;L"), [1, 2, 3])
    assert_equal(pack("RGB", "BGR"), [3, 2, 1])
    assert_equal(pack("RGB", "RGBX"), [1, 2, 3, 255]) # 255?
    assert_equal(pack("RGB", "BGRX"), [3, 2, 1, 0])
    assert_equal(pack("RGB", "XRGB"), [0, 1, 2, 3])
    assert_equal(pack("RGB", "XBGR"), [0, 3, 2, 1])

    assert_equal(pack("RGBX", "RGBX"), [1, 2, 3, 4]) # 4->255?

    assert_equal(pack("RGBA", "RGBA"), [1, 2, 3, 4])

    assert_equal(pack("CMYK", "CMYK"), [1, 2, 3, 4])
    assert_equal(pack("YCbCr", "YCbCr"), [1, 2, 3])

def test_unpack():

    def unpack(mode, rawmode, bytes_):
        im = None

        if py3:
            data = bytes(range(1,bytes_+1))
        else:
            data = ''.join(chr(i) for i in range(1,bytes_+1))

        im = Image.frombytes(mode, (1, 1), data, "raw", rawmode, 0, 1)

        return im.getpixel((0, 0))

    def unpack_1(mode, rawmode, value):
        assert mode == "1"
        im = None

        if py3:
            im = Image.frombytes(mode, (8, 1), bytes([value]), "raw", rawmode, 0, 1)
        else:
            im = Image.frombytes(mode, (8, 1), chr(value), "raw", rawmode, 0, 1)

        return tuple(im.getdata())

    X = 255

    assert_equal(unpack_1("1", "1", 1),    (0,0,0,0,0,0,0,X))
    assert_equal(unpack_1("1", "1;I", 1),  (X,X,X,X,X,X,X,0))
    assert_equal(unpack_1("1", "1;R", 1),  (X,0,0,0,0,0,0,0))
    assert_equal(unpack_1("1", "1;IR", 1), (0,X,X,X,X,X,X,X))

    assert_equal(unpack_1("1", "1", 170),    (X,0,X,0,X,0,X,0))
    assert_equal(unpack_1("1", "1;I", 170),  (0,X,0,X,0,X,0,X))
    assert_equal(unpack_1("1", "1;R", 170),  (0,X,0,X,0,X,0,X))
    assert_equal(unpack_1("1", "1;IR", 170), (X,0,X,0,X,0,X,0))

    assert_equal(unpack("L", "L;2", 1), 0)
    assert_equal(unpack("L", "L;4", 1), 0)
    assert_equal(unpack("L", "L", 1), 1)
    assert_equal(unpack("L", "L;I", 1), 254)
    assert_equal(unpack("L", "L;R", 1), 128)
    assert_equal(unpack("L", "L;16", 2), 2) # little endian
    assert_equal(unpack("L", "L;16B", 2), 1) # big endian

    assert_equal(unpack("LA", "LA", 2), (1, 2))
    assert_equal(unpack("LA", "LA;L", 2), (1, 2))

    assert_equal(unpack("RGB", "RGB", 3), (1, 2, 3))
    assert_equal(unpack("RGB", "RGB;L", 3), (1, 2, 3))
    assert_equal(unpack("RGB", "RGB;R", 3), (128, 64, 192))
    assert_equal(unpack("RGB", "RGB;16B", 6), (1, 3, 5)) # ?
    assert_equal(unpack("RGB", "BGR", 3), (3, 2, 1))
    assert_equal(unpack("RGB", "RGB;15", 2), (8, 131, 0))
    assert_equal(unpack("RGB", "BGR;15", 2), (0, 131, 8))
    assert_equal(unpack("RGB", "RGB;16", 2), (8, 64, 0))
    assert_equal(unpack("RGB", "BGR;16", 2), (0, 64, 8))
    assert_equal(unpack("RGB", "RGB;4B", 2), (17, 0, 34))

    assert_equal(unpack("RGB", "RGBX", 4), (1, 2, 3))
    assert_equal(unpack("RGB", "BGRX", 4), (3, 2, 1))
    assert_equal(unpack("RGB", "XRGB", 4), (2, 3, 4))
    assert_equal(unpack("RGB", "XBGR", 4), (4, 3, 2))

    assert_equal(unpack("RGBA", "RGBA", 4), (1, 2, 3, 4))
    assert_equal(unpack("RGBA", "BGRA", 4), (3, 2, 1, 4))
    assert_equal(unpack("RGBA", "ARGB", 4), (2, 3, 4, 1))
    assert_equal(unpack("RGBA", "ABGR", 4), (4, 3, 2, 1))
    assert_equal(unpack("RGBA", "RGBA;15", 2), (8, 131, 0, 0))
    assert_equal(unpack("RGBA", "BGRA;15", 2), (0, 131, 8, 0))
    assert_equal(unpack("RGBA", "RGBA;4B", 2), (17, 0, 34, 0))

    assert_equal(unpack("RGBX", "RGBX", 4), (1, 2, 3, 4)) # 4->255?
    assert_equal(unpack("RGBX", "BGRX", 4), (3, 2, 1, 255))
    assert_equal(unpack("RGBX", "XRGB", 4), (2, 3, 4, 255))
    assert_equal(unpack("RGBX", "XBGR", 4), (4, 3, 2, 255))
    assert_equal(unpack("RGBX", "RGB;15", 2), (8, 131, 0, 255))
    assert_equal(unpack("RGBX", "BGR;15", 2), (0, 131, 8, 255))
    assert_equal(unpack("RGBX", "RGB;4B", 2), (17, 0, 34, 255))

    assert_equal(unpack("CMYK", "CMYK", 4), (1, 2, 3, 4))
    assert_equal(unpack("CMYK", "CMYK;I", 4), (254, 253, 252, 251))

    assert_exception(ValueError, lambda: unpack("L", "L", 0))
    assert_exception(ValueError, lambda: unpack("RGB", "RGB", 2))
    assert_exception(ValueError, lambda: unpack("CMYK", "CMYK", 2))

run()

########NEW FILE########
__FILENAME__ = test_locale
from tester import *
from PIL import Image

import locale

# ref https://github.com/python-imaging/Pillow/issues/272
## on windows, in polish locale:

## import locale
## print locale.setlocale(locale.LC_ALL, 'polish')
## import string
## print len(string.whitespace)
## print ord(string.whitespace[6])

## Polish_Poland.1250
## 7
## 160

# one of string.whitespace is not freely convertable into ascii. 

path = "Images/lena.jpg"

def test_sanity():
    assert_no_exception(lambda: Image.open(path))
    try:
        locale.setlocale(locale.LC_ALL, "polish")
    except:
        skip('polish locale not available')
    import string
    assert_no_exception(lambda: Image.open(path))


########NEW FILE########
__FILENAME__ = test_mode_i16
from tester import *

from PIL import Image


def verify(im1):
    im2 = lena("I")
    assert_equal(im1.size, im2.size)
    pix1 = im1.load()
    pix2 = im2.load()
    for y in range(im1.size[1]):
        for x in range(im1.size[0]):
            xy = x, y
            if pix1[xy] != pix2[xy]:
                failure(
                    "got %r from mode %s at %s, expected %r" %
                    (pix1[xy], im1.mode, xy, pix2[xy])
                    )
                return
    success()


def test_basic():
    # PIL 1.1 has limited support for 16-bit image data.  Check that
    # create/copy/transform and save works as expected.

    def basic(mode):

        imIn = lena("I").convert(mode)
        verify(imIn)

        w, h = imIn.size

        imOut = imIn.copy()
        verify(imOut)  # copy

        imOut = imIn.transform((w, h), Image.EXTENT, (0, 0, w, h))
        verify(imOut)  # transform

        filename = tempfile("temp.im")
        imIn.save(filename)

        imOut = Image.open(filename)

        verify(imIn)
        verify(imOut)

        imOut = imIn.crop((0, 0, w, h))
        verify(imOut)

        imOut = Image.new(mode, (w, h), None)
        imOut.paste(imIn.crop((0, 0, w//2, h)), (0, 0))
        imOut.paste(imIn.crop((w//2, 0, w, h)), (w//2, 0))

        verify(imIn)
        verify(imOut)

        imIn = Image.new(mode, (1, 1), 1)
        assert_equal(imIn.getpixel((0, 0)), 1)

        imIn.putpixel((0, 0), 2)
        assert_equal(imIn.getpixel((0, 0)), 2)

        if mode == "L":
            max = 255
        else:
            max = 32767

        imIn = Image.new(mode, (1, 1), 256)
        assert_equal(imIn.getpixel((0, 0)), min(256, max))

        imIn.putpixel((0, 0), 512)
        assert_equal(imIn.getpixel((0, 0)), min(512, max))

    basic("L")

    basic("I;16")
    basic("I;16B")
    basic("I;16L")

    basic("I")


def test_tobytes():

    def tobytes(mode):
        return Image.new(mode, (1, 1), 1).tobytes()

    order = 1 if Image._ENDIAN == '<' else -1

    assert_equal(tobytes("L"), b"\x01")
    assert_equal(tobytes("I;16"), b"\x01\x00")
    assert_equal(tobytes("I;16B"), b"\x00\x01")
    assert_equal(tobytes("I"), b"\x01\x00\x00\x00"[::order])


def test_convert():

    im = lena("I")

    verify(im.convert("I;16"))
    verify(im.convert("I;16").convert("L"))
    verify(im.convert("I;16").convert("I"))

    verify(im.convert("I;16B"))
    verify(im.convert("I;16B").convert("L"))
    verify(im.convert("I;16B").convert("I"))

########NEW FILE########
__FILENAME__ = test_numpy
from tester import *

from PIL import Image
import struct

try:
    import site
    import numpy
except ImportError:
    skip()

def test_numpy_to_image():

    def to_image(dtype, bands=1, bool=0):
        if bands == 1:
            if bool:
                data = [0, 1] * 50
            else:
                data = list(range(100))
            a = numpy.array(data, dtype=dtype)
            a.shape = 10, 10
            i = Image.fromarray(a)
            if list(i.getdata()) != data:
                print("data mismatch for", dtype)
        else:
            data = list(range(100))
            a = numpy.array([[x]*bands for x in data], dtype=dtype)
            a.shape = 10, 10, bands
            i = Image.fromarray(a)
            if list(i.split()[0].getdata()) != list(range(100)):
                print("data mismatch for", dtype)
        # print dtype, list(i.getdata())
        return i

    # assert_image(to_image(numpy.bool, bool=1), "1", (10, 10))
    # assert_image(to_image(numpy.bool8, bool=1), "1", (10, 10))

    assert_exception(TypeError, lambda: to_image(numpy.uint))
    assert_image(to_image(numpy.uint8), "L", (10, 10))
    assert_exception(TypeError, lambda: to_image(numpy.uint16))
    assert_exception(TypeError, lambda: to_image(numpy.uint32))
    assert_exception(TypeError, lambda: to_image(numpy.uint64))

    assert_image(to_image(numpy.int8), "I", (10, 10))
    if Image._ENDIAN == '<': # Little endian
        assert_image(to_image(numpy.int16), "I;16", (10, 10))
    else:
        assert_image(to_image(numpy.int16), "I;16B", (10, 10))
    assert_image(to_image(numpy.int32), "I", (10, 10))
    assert_exception(TypeError, lambda: to_image(numpy.int64))

    assert_image(to_image(numpy.float), "F", (10, 10))
    assert_image(to_image(numpy.float32), "F", (10, 10))
    assert_image(to_image(numpy.float64), "F", (10, 10))

    assert_image(to_image(numpy.uint8, 3), "RGB", (10, 10))
    assert_image(to_image(numpy.uint8, 4), "RGBA", (10, 10))


# based on an erring example at http://is.gd/6F0esS  (which resolves to)
# http://stackoverflow.com/questions/10854903/what-is-causing-dimension-dependent-attributeerror-in-pil-fromarray-function
def test_3d_array():
    a = numpy.ones((10, 10, 10), dtype=numpy.uint8)
    assert_image(Image.fromarray(a[1, :, :]), "L", (10, 10))
    assert_image(Image.fromarray(a[:, 1, :]), "L", (10, 10))
    assert_image(Image.fromarray(a[:, :, 1]), "L", (10, 10))


def _test_img_equals_nparray(img, np):
    assert_equal(img.size, np.shape[0:2])
    px = img.load()
    for x in range(0, img.size[0], int(img.size[0]/10)):
        for y in range(0, img.size[1], int(img.size[1]/10)):
            assert_deep_equal(px[x,y], np[y,x])


def test_16bit():
    img = Image.open('Tests/images/16bit.cropped.tif')
    np_img = numpy.array(img)
    _test_img_equals_nparray(img, np_img)
    assert_equal(np_img.dtype, numpy.dtype('<u2'))

def test_to_array():

    def _to_array(mode, dtype):
        img = lena(mode)            
        np_img = numpy.array(img)
        _test_img_equals_nparray(img, np_img)
        assert_equal(np_img.dtype, numpy.dtype(dtype))
    
     
    modes = [("L", 'uint8'),
             ("I", 'int32'),
             ("F", 'float32'),
             ("RGB", 'uint8'),
             ("RGBA", 'uint8'),
             ("RGBX", 'uint8'),
             ("CMYK", 'uint8'),
             ("YCbCr", 'uint8'),
             ("I;16", '<u2'),
             ("I;16B", '>u2'),
             ("I;16L", '<u2'),
             ]
    

    for mode in modes:
        assert_no_exception(lambda: _to_array(*mode))


def test_point_lut():
    # see https://github.com/python-imaging/Pillow/issues/439
    
    data = list(range(256))*3
    lut = numpy.array(data, dtype='uint8')

    im = lena()

    assert_no_exception(lambda: im.point(lut))
    


########NEW FILE########
__FILENAME__ = test_olefileio
from __future__ import print_function
from tester import *
import datetime

import PIL.OleFileIO as OleFileIO


def test_isOleFile_false():
    # Arrange
    non_ole_file = "Tests/images/flower.jpg"

    # Act
    is_ole = OleFileIO.isOleFile(non_ole_file)

    # Assert
    assert_false(is_ole)


def test_isOleFile_true():
    # Arrange
    ole_file = "Tests/images/test-ole-file.doc"

    # Act
    is_ole = OleFileIO.isOleFile(ole_file)

    # Assert
    assert_true(is_ole)


def test_exists_worddocument():
    # Arrange
    ole_file = "Tests/images/test-ole-file.doc"
    ole = OleFileIO.OleFileIO(ole_file)

    # Act
    exists = ole.exists('worddocument')

    # Assert
    assert_true(exists)
    ole.close()


def test_exists_no_vba_macros():
    # Arrange
    ole_file = "Tests/images/test-ole-file.doc"
    ole = OleFileIO.OleFileIO(ole_file)

    # Act
    exists = ole.exists('macros/vba')

    # Assert
    assert_false(exists)
    ole.close()


def test_get_type():
    # Arrange
    ole_file = "Tests/images/test-ole-file.doc"
    ole = OleFileIO.OleFileIO(ole_file)

    # Act
    type = ole.get_type('worddocument')

    # Assert
    assert_equal(type, OleFileIO.STGTY_STREAM)
    ole.close()


def test_get_size():
    # Arrange
    ole_file = "Tests/images/test-ole-file.doc"
    ole = OleFileIO.OleFileIO(ole_file)

    # Act
    size = ole.get_size('worddocument')

    # Assert
    assert_greater(size, 0)
    ole.close()


def test_get_rootentry_name():
    # Arrange
    ole_file = "Tests/images/test-ole-file.doc"
    ole = OleFileIO.OleFileIO(ole_file)

    # Act
    root = ole.get_rootentry_name()

    # Assert
    assert_equal(root, "Root Entry")
    ole.close()


def test_meta():
    # Arrange
    ole_file = "Tests/images/test-ole-file.doc"
    ole = OleFileIO.OleFileIO(ole_file)

    # Act
    meta = ole.get_metadata()

    # Assert
    assert_equal(meta.author, b"Laurence Ipsum")
    assert_equal(meta.num_pages, 1)
    ole.close()


def test_gettimes():
    # Arrange
    ole_file = "Tests/images/test-ole-file.doc"
    ole = OleFileIO.OleFileIO(ole_file)
    root_entry = ole.direntries[0]

    # Act
    ctime = root_entry.getctime()
    mtime = root_entry.getmtime()

    # Assert
    assert_is_instance(ctime, type(None))
    assert_is_instance(mtime, datetime.datetime)
    assert_equal(ctime, None)
    assert_equal(mtime.year, 2014)
    ole.close()


def test_listdir():
    # Arrange
    ole_file = "Tests/images/test-ole-file.doc"
    ole = OleFileIO.OleFileIO(ole_file)

    # Act
    dirlist = ole.listdir()

    # Assert
    assert_in(['WordDocument'], dirlist)
    ole.close()


def test_debug():
    # Arrange
    print("ignore_all_except_last_line")
    ole_file = "Tests/images/test-ole-file.doc"
    ole = OleFileIO.OleFileIO(ole_file)
    meta = ole.get_metadata()

    # Act
    OleFileIO.set_debug_mode(True)
    ole.dumpdirectory()
    meta.dump()

    OleFileIO.set_debug_mode(False)
    ole.dumpdirectory()
    meta.dump()

    # Assert
    # No assert, just check they run ok
    print("ok")
    ole.close()


# End of file

########NEW FILE########
__FILENAME__ = test_pickle
from tester import *

from PIL import Image


def helper_test_pickle_file(pickle, protocol=0):
    im = Image.open('Images/lena.jpg')
    filename = tempfile('temp.pkl')

    # Act
    with open(filename, 'wb') as f:
        pickle.dump(im, f, protocol)
    with open(filename, 'rb') as f:
        loaded_im = pickle.load(f)

    # Assert
    assert_image_completely_equal(im, loaded_im)


def helper_test_pickle_string(pickle, protocol=0, file='Images/lena.jpg'):
    im = Image.open(file)

    # Act
    dumped_string = pickle.dumps(im, protocol)
    loaded_im = pickle.loads(dumped_string)

    # Assert
    assert_image_completely_equal(im, loaded_im)


def test_pickle_image():
    # Arrange
    import pickle

    # Act / Assert
    for protocol in range(0, pickle.HIGHEST_PROTOCOL + 1):
        helper_test_pickle_string(pickle, protocol)
        helper_test_pickle_file(pickle, protocol)


def test_cpickle_image():
    # Arrange
    try:
        import cPickle
    except ImportError:
        return

    # Act / Assert
    for protocol in range(0, cPickle.HIGHEST_PROTOCOL + 1):
        helper_test_pickle_string(cPickle, protocol)
        helper_test_pickle_file(cPickle, protocol)


def test_pickle_p_mode():
    # Arrange
    import pickle

    # Act / Assert
    for file in [
            "Tests/images/test-card.png",
            "Tests/images/zero_bb.png",
            "Tests/images/zero_bb_scale2.png",
            "Tests/images/non_zero_bb.png",
            "Tests/images/non_zero_bb_scale2.png",
            "Tests/images/p_trns_single.png",
            "Tests/images/pil123p.png"
    ]:
        helper_test_pickle_string(pickle, file=file)

# End of file

########NEW FILE########
__FILENAME__ = threaded_save
from PIL import Image

import sys, time
import io
import threading, queue

try:
    format = sys.argv[1]
except:
    format = "PNG"

im = Image.open("Images/lena.ppm")
im.load()

queue = queue.Queue()

result = []

class Worker(threading.Thread):
    def run(self):
        while True:
            im = queue.get()
            if im is None:
                queue.task_done()
                sys.stdout.write("x")
                break
            f = io.BytesIO()
            im.save(f, format, optimize=1)
            data = f.getvalue()
            result.append(len(data))
            im = Image.open(io.BytesIO(data))
            im.load()
            sys.stdout.write(".")
            queue.task_done()

t0 = time.time()

threads = 20
jobs = 100

for i in range(threads):
    w = Worker()
    w.start()

for i in range(jobs):
    queue.put(im)

for i in range(threads):
    queue.put(None)

queue.join()

print()
print(time.time() - t0)
print(len(result), sum(result))
print(result)

########NEW FILE########
__FILENAME__ = versions
from PIL import Image

def version(module, version):
    v = getattr(module.core, version + "_version", None)
    if v:
        print(version, v)

version(Image, "jpeglib")
version(Image, "zlib")

try:
    from PIL import ImageFont
except ImportError:
    pass
else:
    version(ImageFont, "freetype2")

try:
    from PIL import ImageCms
except ImportError:
    pass
else:
    version(ImageCms, "littlecms")

########NEW FILE########
