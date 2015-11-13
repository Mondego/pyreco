__FILENAME__ = bin_packing
# media_bundler/bundle.py

"""A simple 2D bin packing algorithm for making sprites."""

import math


class Box(object):

    """A simple 2D rectangle with width and height attributes.  Immutable."""

    def __init__(self, width, height):
        self.__width = width
        self.__height = height

    @property
    def width(self): return self.__width

    @property
    def height(self): return self.__height

    def __eq__(self, other):
        return self.width == other.width and self.height == other.height

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return "Box(%r, %r)" % (self.width, self.height)


def pack_boxes(boxes, max_width=None):
    """Approximately packs boxes in a rectangle with minimal area.

    Basic algorithm:
    - Pick a width so that our rectangle comes out squarish.
    - Sort the boxes by their width.
    - While there are more boxes, attempt to fill a horizontal strip:
      - For each box that we haven't already placed, if it fits in the strip,
        place it, otherwise continue checking the rest of the boxes.
    """
    if max_width is None:
        total_area = sum(box.width * box.height for box in boxes)
        max_width = max(max(box.width for box in boxes),
                        int(math.sqrt(total_area)))
    unplaced = sorted(boxes, key=lambda box: (-box.height, -box.width))
    packing = []
    y_off = 0
    while unplaced:
        strip_width = 0
        strip_height = 0
        next_unplaced = []
        for box in unplaced:
            if strip_width + box.width <= max_width:
                packing.append((strip_width, y_off, box))
                strip_width += box.width
                strip_height = max(strip_height, box.height)
            else:
                next_unplaced.append(box)
        y_off += strip_height
        unplaced = next_unplaced
    return (max_width, y_off, packing)


def boxes_overlap((x1, y1, box1), (x2, y2, box2)):
    """Return True if the two boxes at (x1, y1) and (x2, y2) overlap."""
    left1 = x1
    top1 = y1
    right1 = x1 + box1.width
    bottom1 = y1 + box1.height
    left2 = x2
    top2 = y2
    right2 = x2 + box2.width
    bottom2 = y2 + box2.height
    return ((left2 <= left1  <  right2 and top2 <= top1    <  bottom2) or
            (left2 <  right1 <= right2 and top2 <= top1    <  bottom2) or
            (left2 <= left1  <  right2 and top2 <  bottom1 <= bottom2) or
            (left2 <  right1 <= right2 and top2 <  bottom1 <= bottom2))


def check_no_overlap(packing):
    """Return True if none of the boxes in the packing overlap."""
    # TODO(rnk): It would be great if we could avoid comparing each box twice.
    for left in packing:
        for right in packing:
            if left == right:
                continue
            if boxes_overlap(left, right):
                return False
    return True

########NEW FILE########
__FILENAME__ = bin_packing_test
#!/usr/bin/env python

"""Tests for the bin packing algorithm."""

import random
import unittest

from bin_packing import Box, pack_boxes, check_no_overlap


class BinPackingTest(unittest.TestCase):

    def testCheckOverlap(self):
        # The second box has a top left point in the center of the first.
        packing = [(0, 0, Box(2, 2)), (1, 1, Box(2, 2))]
        self.assert_(not check_no_overlap(packing))

    def testCheckNoOverlap(self):
        # These boxes touch but do not overlap.
        packing = [(0, 0, Box(2, 2)), (2, 0, Box(2, 2))]
        self.assert_(check_no_overlap(packing))

    def testPackSingle(self):
        boxes = [Box(1, 1)]
        packing = [(0, 0, Box(1, 1))]
        (_, _, actual) = pack_boxes(boxes, 1)
        self.assert_(check_no_overlap(actual))
        self.assertEqual(actual, packing)

    def testPackEasy(self):
        # AA
        # B
        # C
        boxes = [
            Box(2, 1),
            Box(1, 1),
            Box(1, 1),
        ]
        # AA
        # BC
        packing = [
            (0, 0, Box(2, 1)),
            (0, 1, Box(1, 1)),
            (1, 1, Box(1, 1)),
        ]
        (_, _, actual) = pack_boxes(boxes, 2)
        self.assert_(check_no_overlap(actual))
        self.assertEqual(actual, packing)

    def testPackSequentialWidth(self):
        # AAAAAAAA
        # BBBBBBB
        # CCCCCC
        # DDDDD
        # EEEE
        # FFF
        # GG
        # H
        boxes = [Box(i, 1) for i in range(1, 9)]
        # AAAAAAAA
        # BBBBBBBH
        # CCCCCCGG
        # DDDDDFFF
        # EEEE
        packing = [
            (0, 0, Box(8, 1)),
            (0, 1, Box(7, 1)),
            (7, 1, Box(1, 1)),
            (0, 2, Box(6, 1)),
            (6, 2, Box(2, 1)),
            (0, 3, Box(5, 1)),
            (5, 3, Box(3, 1)),
            (0, 4, Box(4, 1)),
        ]
        (_, _, actual) = pack_boxes(boxes, 8)
        self.assert_(check_no_overlap(actual))
        self.assertEqual(actual, packing)

    def testPackSequenceHeightWidth(self):
        # A
        # B
        # B
        # C
        # C
        # C
        # DD
        # EE
        # EE
        # FF
        # FF
        # FF
        # GGG
        # HHH
        # HHH
        # III
        # III
        # III
        boxes = [Box(i, j) for i in range(1, 4) for j in range(1, 4)]
        # III
        # III
        # III
        # FFC
        # FFC
        # FFC
        # HHH
        # HHH
        # EEB
        # EEB
        # GGG
        # DDA
        packing = [
            (0, 0, Box(3, 3)),
            (0, 3, Box(2, 3)),
            (2, 3, Box(1, 3)),
            (0, 6, Box(3, 2)),
            (0, 8, Box(2, 2)),
            (2, 8, Box(1, 2)),
            (0, 10, Box(3, 1)),
            (0, 11, Box(2, 1)),
            (2, 11, Box(1, 1)),
        ]
        (_, _, actual) = pack_boxes(boxes, 3)
        self.assert_(check_no_overlap(actual))
        self.assertEqual(actual, packing)

    def testRandomNoOverlap(self):
        # Not having overlap is an important invariant we need to maintain.
        # This just checks it.
        for _ in xrange(3):
            boxes = [Box(random.randrange(1, 40), random.randrange(1, 40))
                     for _ in xrange(100)]
            (_, _, actual) = pack_boxes(boxes)
            self.assert_(check_no_overlap(actual))


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = bundler
# media_bundler/bundle.py

from __future__ import with_statement

import math
import os
import shutil
import subprocess
import re
from StringIO import StringIO

from media_bundler.conf import bundler_settings
from media_bundler.bin_packing import Box, pack_boxes
from media_bundler.jsmin import jsmin
from media_bundler.cssmin import minify_css
from media_bundler import versioning


class InvalidBundleType(Exception):

    def __init__(self, type_):
        msg = "Invalid bundle type: %r" % type_
        super(InvalidBundleType, self).__init__(msg)


def concatenate_files(paths):
    """Generate the contents of several files in 8K blocks."""
    for path in paths:
        with open(path) as input:
            buffer = input.read(8192)
            while buffer:
                yield buffer
                buffer = input.read(8192)


class Bundle(object):

    """Base class for a bundle of media files.

    A bundle is a collection of related static files that can be concatenated
    together and served as a single file to improve performance.
    """

    def __init__(self, name, path, url, files, type):
        self.name = name
        self.path = path
        self.url = url
        if not url.endswith("/"):
            raise ValueError("Bundle URLs must end with a '/'.")
        self.files = files
        self.type = type

    @classmethod
    def check_attr(cls, attrs, attr):
        errmsg = "Invalid bundle: %r attribute %r required." % (attrs, attr)
        assert attr in attrs, errmsg

    @classmethod
    def from_dict(cls, attrs):
        for attr in ("type", "name", "path", "url", "files"):
            cls.check_attr(attrs, attr)
        if attrs["type"] == "javascript":
            return JavascriptBundle(attrs["name"], attrs["path"], attrs["url"],
                                    attrs["files"], attrs["type"],
                                    attrs.get("minify", False))
        elif attrs["type"] == "css":
            return CssBundle(attrs["name"], attrs["path"], attrs["url"],
                             attrs["files"], attrs["type"],
                             attrs.get("minify", False))
        elif attrs["type"] == "png-sprite":
            cls.check_attr(attrs, "css_file")
            return PngSpriteBundle(attrs["name"], attrs["path"], attrs["url"],
                                   attrs["files"], attrs["type"],
                                   attrs["css_file"])
        else:
            raise InvalidBundleType(attrs["type"])

    def get_paths(self):
        return [os.path.join(self.path, f) for f in self.files]

    def get_extension(self):
        raise NotImplementedError

    def get_bundle_filename(self):
        return self.name + self.get_extension()

    def get_bundle_path(self):
        filename = self.get_bundle_filename()
        return os.path.join(self.path, filename)

    def get_bundle_url(self):
        unversioned = self.get_bundle_filename()
        filename = versioning.get_bundle_versions().get(self.name, unversioned)
        return self.url + filename

    def make_bundle(self, versioner):
        self._make_bundle()
        if versioner:
            versioner.update_bundle_version(self)

    def do_text_bundle(self, minifier=None):
        with open(self.get_bundle_path(), "w") as output:
            generator = concatenate_files(self.get_paths())
            if minifier:
                # Eventually we should use generators to concatenate and minify
                # things one bit at a time, but for now we use strings.
                output.write(minifier("".join(generator)))
            else:
                output.write("".join(generator))


class JavascriptBundle(Bundle):

    """Bundle for JavaScript."""

    def __init__(self, name, path, url, files, type, minify):
        super(JavascriptBundle, self).__init__(name, path, url, files, type)
        self.minify = minify

    def get_extension(self):
        return ".js"

    def _make_bundle(self):
        minifier = jsmin if self.minify else None
        self.do_text_bundle(minifier)


class CssBundle(Bundle):

    """Bundle for CSS."""

    def __init__(self, name, path, url, files, type, minify):
        super(CssBundle, self).__init__(name, path, url, files, type)
        self.minify = minify

    def get_extension(self):
        return ".css"

    def _make_bundle(self):
        minifier = minify_css if self.minify else None
        self.do_text_bundle(minifier)


class PngSpriteBundle(Bundle):

    """Bundle for PNG sprites.

    In addition to generating a PNG sprite, it also generates CSS rules so that
    the user can easily place their sprites.  We build sprite bundles before CSS
    bundles so that the user can bundle the generated CSS with the rest of their
    CSS.
    """

    def __init__(self, name, path, url, files, type, css_file):
        super(PngSpriteBundle, self).__init__(name, path, url, files, type)
        self.css_file = css_file

    def get_extension(self):
        return ".png"

    def make_bundle(self, versioner):
        import Image  # If this fails, you need the Python Imaging Library.
        boxes = [ImageBox(Image.open(path), path) for path in self.get_paths()]
        # Pick a max_width so that the sprite is squarish and a multiple of 16,
        # and so no image is too wide to fit.
        total_area = sum(box.width * box.height for box in boxes)
        width = max(max(box.width for box in boxes),
                    (int(math.sqrt(total_area)) // 16 + 1) * 16)
        (_, height, packing) = pack_boxes(boxes, width)
        sprite = Image.new("RGBA", (width, height))
        for (left, top, box) in packing:
            # This is a bit of magic to make the transparencies work.  To
            # preserve transparency, we pass the image so it can take its
            # alpha channel mask or something.  However, if the image has no
            # alpha channels, then it fails, we we have to check if the
            # image is RGBA here.
            img = box.image
            mask = img if img.mode == "RGBA" else None
            sprite.paste(img, (left, top), mask)
        sprite.save(self.get_bundle_path(), "PNG")
        self._optimize_output()
        # It's *REALLY* important that this happen here instead of after the
        # generate_css() call, because if we waited, the CSS woudl have the URL
        # of the last version of this bundle.
        if versioner:
            versioner.update_bundle_version(self)
        self.generate_css(packing)

    def _optimize_output(self):
        """Optimize the PNG with pngcrush."""
        sprite_path = self.get_bundle_path()
        tmp_path = sprite_path + '.tmp'
        args = ['pngcrush', '-rem', 'alla', sprite_path, tmp_path]
        proc = subprocess.Popen(args, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        proc.wait()
        if proc.returncode != 0:
            raise Exception('pngcrush returned error code: %r\nOutput was:\n\n'
                            '%s' % (proc.returncode, proc.stdout.read()))
        shutil.move(tmp_path, sprite_path)

    def generate_css(self, packing):
        """Generate the background offset CSS rules."""
        with open(self.css_file, "w") as css:
            css.write("/* Generated classes for django-media-bundler sprites.  "
                      "Don't edit! */\n")
            props = {
                "background-image": "url('%s')" % self.get_bundle_url(),
            }
            css.write(self.make_css(None, props))
            for (left, top, box) in packing:
                props = {
                    "background-position": "%dpx %dpx" % (-left, -top),
                    "width": "%dpx" % box.width,
                    "height": "%dpx" % box.height,
                }
                css.write(self.make_css(os.path.basename(box.filename), props))

    CSS_REGEXP = re.compile(r"[^a-zA-Z\-_]")

    def css_class_name(self, rule_name):
        name = self.name
        if rule_name:
            name += "-" + rule_name
        name = name.replace(" ", "-").replace(".", "-")
        return self.CSS_REGEXP.sub("", name)

    def make_css(self, name, props):
        # We try to format it nicely here in case the user actually looks at it.
        # If he wants it small, he'll bundle it up in his CssBundle.
        css_class = self.css_class_name(name)
        css_propstr = "".join("     %s: %s;\n" % p for p in props.iteritems())
        return "\n.%s {\n%s}\n" % (css_class, css_propstr)


class ImageBox(Box):

    """A Box representing an image.

    We hand these off to the bin packing algorithm.  After the boxes have been
    arranged, we can place the associated image in the sprite.
    """

    def __init__(self, image, filename):
        (width, height) = image.size
        super(ImageBox, self).__init__(width, height)
        self.image = image
        self.filename = filename

    def __repr__(self):
        return "<ImageBox: filename=%r image=%r>" % (self.filename, self.image)


_bundles = None

def get_bundles():
    """Return a dict of bundle names and bundles as described in settings.py.

    The result of this function is cached, because settings should never change
    throughout the execution of the program.
    """
    global _bundles
    if not _bundles:
        _bundles = dict((bundle["name"], Bundle.from_dict(bundle))
                        for bundle in bundler_settings.MEDIA_BUNDLES)
    return _bundles

########NEW FILE########
__FILENAME__ = bundler_settings
# media_bundler/conf/bundler_settings.py

"""
media_bundler specific settings with the defaults filled in.

If the user has overridden a setting in their settings module, we'll use that
value, but otherwise we'll fall back on the value from
media_bundler.default_settings.  All bundler- specific settings checks should
go through this module, but to check global Django settings, use the normal
django.conf.settings module.
"""

from django.conf import settings

from media_bundler.conf import default_settings


USE_BUNDLES = getattr(settings, "USE_BUNDLES",
                      default_settings.USE_BUNDLES)
DEFER_JAVASCRIPT = getattr(settings, "DEFER_JAVASCRIPT",
                           default_settings.DEFER_JAVASCRIPT)
MEDIA_BUNDLES = getattr(settings, "MEDIA_BUNDLES",
                        default_settings.MEDIA_BUNDLES)
BUNDLE_VERSION_FILE = getattr(settings, "BUNDLE_VERSION_FILE",
                              default_settings.BUNDLE_VERSION_FILE)
BUNDLE_VERSIONER = getattr(settings, "BUNDLE_VERSIONER",
                           default_settings.BUNDLE_VERSIONER)

########NEW FILE########
__FILENAME__ = default_settings
# media_bundler/conf/default_settings.py

"""
These are the default settings for media_bunder.

You can copy, paste, and modify these values into your own settings.py file.
"""

from django.conf import settings

# This flag determines whether to enable bundling or not.  To assist in
# debugging, we recommend keeping files separate during development and bundle
# them during production, so by default we just use settings.DEBUG, but you can
# override that value if you wish by setting FORCE_BUNDLES to True in your
# settings file.
USE_BUNDLES = getattr(settings, 'FORCE_BUNDLES', False) or not settings.DEBUG

# This puts your JavaScript at the bottom of your templates instead of the top
# in order to allow the page to load before script execution, as described in
# YUI rule #5:
# http://developer.yahoo.net/blog/archives/2007/07/high_performanc_5.html
DEFER_JAVASCRIPT = True

# This setting enables bundle versioning and cache busting.  This should be a
# file path to a Python module that will be live when the site is deployed.  The
# bundler will write out Python code defining a dictionary mapping bundle names
# to versions.
BUNDLE_VERSION_FILE = None  # Ex: PROJECT_ROOT + "/bundle_versions.py"

# If bundle versioning is enabled, this setting controls how the bundler
# computes the current version.  Possible values are 'sha1', 'md5', and 'mtime'.
# The md5 and sha1 versioners are preferred because they create less false
# versions.
BUNDLE_VERSIONER = 'sha1'

MEDIA_BUNDLES = (
    # This should contain something like:

    #{"type": "javascript",
    # "name": "myapp_scripts",
    # "path": MEDIA_ROOT + "/scripts/",
    # "url": MEDIA_URL + "/scripts/",
    # "minify": True,  # If you want to minify your source.
    # "files": (
    #     "foo.js",
    #     "bar.js",
    #     "baz.js",
    # )},

    #{"type": "css",
    # "name": "myapp_styles",
    # "path": MEDIA_ROOT + "/styles/",
    # "url": MEDIA_URL + "/styles/",
    # "minify": True,  # If you want to minify your source.
    # "files": (
    #     "foo.css",
    #     "bar.css",
    #     "baz.css",
    #     "myapp-sprites.css",  # Include this generated CSS file.
    # )},

    #{"type": "png-sprite",
    # "name": "myapp_sprites",
    # "path": MEDIA_ROOT + "/images/",
    # "url": MEDIA_URL + "/images/",
    # # Where the generated CSS rules go.
    # "css_file": MEDIA_ROOT + "/styles/myapp-sprites.css",
    # "files": (
    #     "foo.png",
    #     "bar.png",
    #     "baz.png",
    # )},
)

########NEW FILE########
__FILENAME__ = cssmin
# media_bundler/cssmin.py

# Original source code:
# http://stackoverflow.com/questions/222581/python-script-for-minifying-css

# This is obviously a hacky script, and it probably has bugs.

import re

def minify_css(css):
    # remove comments - this will break a lot of hacks :-P
    css = re.sub(r'\s*/\*\s*\*/', "$$HACK1$$", css)
    css = re.sub(r'/\*[\s\S]*?\*/', "", css)
    css = css.replace("$$HACK1$$", '/**/') # preserve IE<6 comment hack
    # url() don't need quotes
    css = re.sub(r'url\((["\'])([^)]*)\1\)', "url(\\2)", css)
    # spaces may be safely collapsed as generated content will collapse them anyway
    css = re.sub(r'\s+', " ", css)
    return "".join(generate_rules(css))

def generate_rules(css):
    for rule in re.findall(r'([^{]+){([^}]*)}', css):
        selectors = []
        for selector in rule[0].split(','):
            selectors.append(selector.strip())
        # order is important, but we still want to discard repetitions
        properties = {}
        porder  = []
        for prop in re.findall('(.*?):(.*?)(;|$)', rule[1]):
            key = prop[0].strip().lower()
            if key not in porder:
                porder.insert(0, key)
            properties[ key ] = prop[1].strip()
        porder.reverse()
        # output rule if it contains any declarations
        if len(properties) > 0:
            s = ";".join(key + ":" + properties[key] for key in porder)
            yield ",".join(selectors) + "{" + s + "}"

########NEW FILE########
__FILENAME__ = jsmin
#!/usr/bin/python

# This code is original from jsmin by Douglas Crockford, it was translated to
# Python by Baruch Even. The original code had the following copyright and
# license.
#
# /* jsmin.c
#    2007-05-22
#
# Copyright (c) 2002 Douglas Crockford  (www.crockford.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# The Software shall be used for Good, not Evil.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# */

def jsmin(js):
    from StringIO import StringIO
    ins = StringIO(js)
    outs = StringIO()
    JavascriptMinify().minify(ins, outs)
    str = outs.getvalue()
    if len(str) > 0 and str[0] == '\n':
        str = str[1:]
    return str

def isAlphanum(c):
    """return true if the character is a letter, digit, underscore,
           dollar sign, or non-ASCII character.
    """
    return ((c >= 'a' and c <= 'z') or (c >= '0' and c <= '9') or
            (c >= 'A' and c <= 'Z') or c == '_' or c == '$' or c == '\\' or
            (c is not None and ord(c) > 126))

class UnterminatedComment(Exception):
    pass

class UnterminatedStringLiteral(Exception):
    pass

class UnterminatedRegularExpression(Exception):
    pass

class JavascriptMinify(object):

    def _outA(self):
        self.outstream.write(self.theA)
    def _outB(self):
        self.outstream.write(self.theB)

    def _get(self):
        """return the next character from stdin. Watch out for lookahead. If
           the character is a control character, translate it to a space or
           linefeed.
        """
        c = self.theLookahead
        self.theLookahead = None
        if c == None:
            c = self.instream.read(1)
        if c >= ' ' or c == '\n':
            return c
        if c == '': # EOF
            return '\000'
        if c == '\r':
            return '\n'
        return ' '

    def _peek(self):
        self.theLookahead = self._get()
        return self.theLookahead

    def _next(self):
        """get the next character, excluding comments. peek() is used to see
           if an unescaped '/' is followed by a '/' or '*'.
        """
        c = self._get()
        if c == '/' and self.theA != '\\':
            p = self._peek()
            if p == '/':
                c = self._get()
                while c > '\n':
                    c = self._get()
                return c
            if p == '*':
                c = self._get()
                while 1:
                    c = self._get()
                    if c == '*':
                        if self._peek() == '/':
                            self._get()
                            return ' '
                    if c == '\000':
                        raise UnterminatedComment()

        return c

    def _action(self, action):
        """do something! What you do is determined by the argument:
           1   Output A. Copy B to A. Get the next B.
           2   Copy B to A. Get the next B. (Delete A).
           3   Get the next B. (Delete B).
           action treats a string as a single character. Wow!
           action recognizes a regular expression if it is preceded by ( or , or =.
        """
        if action <= 1:
            self._outA()

        if action <= 2:
            self.theA = self.theB
            if self.theA == "'" or self.theA == '"':
                while 1:
                    self._outA()
                    self.theA = self._get()
                    if self.theA == self.theB:
                        break
                    if self.theA <= '\n':
                        raise UnterminatedStringLiteral()
                    if self.theA == '\\':
                        self._outA()
                        self.theA = self._get()


        if action <= 3:
            self.theB = self._next()
            if self.theB == '/' and (self.theA == '(' or self.theA == ',' or
                                     self.theA == '=' or self.theA == ':' or
                                     self.theA == '[' or self.theA == '?' or
                                     self.theA == '!' or self.theA == '&' or
                                     self.theA == '|' or self.theA == ';' or
                                     self.theA == '{' or self.theA == '}' or
                                     self.theA == '\n'):
                self._outA()
                self._outB()
                while 1:
                    self.theA = self._get()
                    if self.theA == '/':
                        break
                    elif self.theA == '\\':
                        self._outA()
                        self.theA = self._get()
                    elif self.theA <= '\n':
                        raise UnterminatedRegularExpression()
                    self._outA()
                self.theB = self._next()


    def _jsmin(self):
        """Copy the input to the output, deleting the characters which are
           insignificant to JavaScript. Comments will be removed. Tabs will be
           replaced with spaces. Carriage returns will be replaced with linefeeds.
           Most spaces and linefeeds will be removed.
        """
        self.theA = '\n'
        self._action(3)

        while self.theA != '\000':
            if self.theA == ' ':
                if isAlphanum(self.theB):
                    self._action(1)
                else:
                    self._action(2)
            elif self.theA == '\n':
                if self.theB in ['{', '[', '(', '+', '-']:
                    self._action(1)
                elif self.theB == ' ':
                    self._action(3)
                else:
                    if isAlphanum(self.theB):
                        self._action(1)
                    else:
                        self._action(2)
            else:
                if self.theB == ' ':
                    if isAlphanum(self.theA):
                        self._action(1)
                    else:
                        self._action(3)
                elif self.theB == '\n':
                    if self.theA in ['}', ']', ')', '+', '-', '"', '\'']:
                        self._action(1)
                    else:
                        if isAlphanum(self.theA):
                            self._action(1)
                        else:
                            self._action(3)
                else:
                    self._action(1)

    def minify(self, instream, outstream):
        self.instream = instream
        self.outstream = outstream
        self.theA = '\n'
        self.theB = None
        self.theLookahead = None

        self._jsmin()
        self.instream.close()

if __name__ == '__main__':
    import sys
    jsm = JavascriptMinify()
    jsm.minify(sys.stdin, sys.stdout)

########NEW FILE########
__FILENAME__ = bundle_media
# media_bundler/management/commands/bundle_media.py

"""
A Django management command to bundle our media.

This command should be integrated into any build or deploy process used with
the project.
"""

from django.core.management.base import NoArgsCommand

from media_bundler.conf import bundler_settings
from media_bundler import bundler
from media_bundler import versioning


class Command(NoArgsCommand):

    """Bundles your media as specified in settings.py."""

    def handle_noargs(self, **options):
        version_file = bundler_settings.BUNDLE_VERSION_FILE
        if version_file:
            vers_str = bundler_settings.BUNDLE_VERSIONER
            versioner = versioning.VERSIONERS[vers_str]()
        else:
            versioner = None
        # We do the image bundles first because they generate CSS that may get
        # bundled by a CssBundle.
        def key(bundle):
            return -int(isinstance(bundle, bundler.PngSpriteBundle))
        bundles = sorted(bundler.get_bundles().itervalues(), key=key)
        for bundle in bundles:
            bundle.make_bundle(versioner)
        if versioner:
            versioning.write_versions(versioner.versions)

########NEW FILE########
__FILENAME__ = bundler_tags
# media_bundler/templatetags/bundler_tags.py

"""
Template tags for the django media bundler.
"""

from django import template
from django.template import Variable

from media_bundler import bundler
from media_bundler.conf import bundler_settings

register = template.Library()


def context_set_default(context, key, default):
    """Like setdefault for Contexts, only we use the root Context dict."""
    if context.has_key(key):
        return context[key]
    else:
        # Set the value on the root context so our value isn't popped off.
        context.dicts[-1][key] = default
        return default


def bundle_tag(tag_func):
    def new_tag_func(parser, token):
        try:
            tag_name, bundle_name, file_name = token.split_contents()
        except ValueError:
            tag_name = token.contents.split()[0]
            msg = "%r tag takes two arguments: bundle_name and file_name."
            raise template.TemplateSyntaxError(msg % tag_name)
        bundle_name_var = Variable(bundle_name)
        file_name_var = Variable(file_name)
        return tag_func(bundle_name_var, file_name_var)
    # Hack so that register.tag behaves correctly.
    new_tag_func.__name__ = tag_func.__name__
    return new_tag_func


def resolve_variable(var, context):
    try:
        return var.resolve(context)
    except AttributeError:
        return var


class BundleNode(template.Node):

    """Base class for any nodes that are linking bundles.

    Subclasses must define class variables TAG and CONTEXT_VAR.  They can
    optionally override the method 'really_render(url)' to control tag-specific
    rendering behavior.
    """

    TAG = None

    CONTEXT_VAR = None

    def __init__(self, bundle_name, file_name):
        super(BundleNode, self).__init__()
        self.bundle_name = bundle_name
        self.file_name = file_name

    def render(self, context):
        bundle_name = resolve_variable(self.bundle_name, context)
        file_name = resolve_variable(self.file_name, context)
        bundle = bundler.get_bundles()[bundle_name]
        if file_name not in bundle.files:
            msg = "File %r is not in bundle %r." % (file_name,
                                                    bundle_name)
            raise template.TemplateSyntaxError(msg)
        url_set = context_set_default(context, self.CONTEXT_VAR, set())
        if bundler_settings.USE_BUNDLES:
            url = bundle.get_bundle_url()
        else:
            url = bundle.url + file_name
        if url in url_set:
            return ""  # Don't add a bundle or css url twice.
        else:
            url_set.add(url)
            return self.really_render(context, url, bundle_name, file_name)

    def really_render(self, context, url, bundle_name, file_name):
        """Implement bundle type specific rendering behavior."""
        return self.TAG % url


@register.tag
@bundle_tag
def javascript(bundle_name, script_name):
    """Tag to include JavaScript in the template."""
    return JavascriptNode(bundle_name, script_name)


class JavascriptNode(BundleNode):

    """Add a script tag for a script or its bundle inline or at the bottom."""

    TAG = '<script type="text/javascript" src="%s"></script>'

    CONTEXT_VAR = "_script_urls"

    def __init__(self, bundle_name, script_name):
        super(JavascriptNode, self).__init__(bundle_name, script_name)

    def really_render(self, context, url, bundle_name, file_name):
        content = super(JavascriptNode, self).really_render(context, url,
                bundle_name, file_name)
        if bundler_settings.DEFER_JAVASCRIPT:
            deferred = context_set_default(context, "_deferred_content", [])
            deferred.append(content)
            return ""
        else:
            return content


@register.tag
@bundle_tag
def css(bundle_name, css_name):
    """Tag to include CSS in the template."""
    return CssNode(bundle_name, css_name)


class CssNode(BundleNode):

    """Add link tags for a CSS file or its bundle."""

    TAG = '<link rel="stylesheet" type="text/css" href="%s"/>'

    CONTEXT_VAR = "_css_urls"

    def __init__(self, bundle_name, css_name):
        super(CssNode, self).__init__(bundle_name, css_name)


@register.tag
def defer(parser, token):
    nodelist = parser.parse(('enddefer',))
    parser.delete_first_token()
    return DeferNode(nodelist)


class DeferNode(template.Node):

    """Defer some content until later."""

    def __init__(self, nodelist):
        super(DeferNode, self).__init__()
        self.nodelist = nodelist

    def render(self, context):
        # We render the content in this context so that the scoping rules make
        # sense, ie all variables that seem to be in scope really are.
        content = self.nodelist.render(context)
        if bundler_settings.DEFER_JAVASCRIPT:
            deferred = context_set_default(context, "_deferred_content", [])
            deferred.append(content)
            return ""
        else:
            return content


@register.tag
def deferred_content(parser, token):
    """Tag to load deferred content."""
    return DeferredContentNode()


class DeferredContentNode(template.Node):

    """Add script tags for deferred scripts."""

    def render(self, context):
        return "\n".join(context.get("_deferred_content", ()))


class MultiBundleNode(template.Node):

    """Node loading a complete bundle by name."""

    bundle_type_handlers = {
        "javascript": JavascriptNode,
        "css": CssNode,
    }

    def __init__(self, bundle_name_var, **kwargs):
        self.bundle_name_var = Variable(bundle_name_var)

        for attr_name, attr_value in kwargs.items():
            if hasattr(self, attr_name):
                setattr(self, attr_name, attr_value)

    def render(self, context):
        bundle_name = self.bundle_name_var.resolve(context)
        bundle = bundler.get_bundles()[bundle_name]
        type_handler = self.bundle_type_handlers[bundle.type]

        def process_file(file_name):
            return type_handler(self.bundle_name_var,
                                file_name).render(context)

        tags = [process_file(file_name) for file_name in bundle.files]
        return "\n".join(tags)


@register.tag
def load_bundle(parser, token):
    try:
        tag_name, bundle_name = token.split_contents()
    except ValueError:
        tag_name = token.contents.split()[0]
        msg = "%r tag takes a single argument: bundle_name."
        raise template.TemplateSyntaxError(msg % tag_name)
    return MultiBundleNode(bundle_name)

########NEW FILE########
__FILENAME__ = versioning
# media_bundler/versioning.py

"""
Module for versioning bundles.

Ideas and code credited to the Andreas Pelme and other authors of the
django-compress project:
http://code.google.com/p/django-compress/

This is a rewrite of their original code to not rely on reading the version
information from a directory listing and work with the rest of
django-media-bundler.
"""

from __future__ import with_statement

from hashlib import md5, sha1
import os
import shutil

from media_bundler.conf import bundler_settings


_bundle_versions = None

def get_bundle_versions():
    global _bundle_versions
    if not bundler_settings.BUNDLE_VERSION_FILE:
        _bundle_versions = {}  # Should this be None?
    if _bundle_versions is None:
        update_versions()
    return _bundle_versions


def update_versions():
    """Executes the bundle versions file and updates the cache."""
    global _bundle_versions
    vars = {}
    try:
        execfile(bundler_settings.BUNDLE_VERSION_FILE, vars)
    except IOError:
        _bundle_versions = {}
    else:
        _bundle_versions = vars['BUNDLE_VERSIONS']


def write_versions(versions):
    global _bundle_versions
    _bundle_versions = _bundle_versions.copy()
    _bundle_versions.update(versions)
    with open(bundler_settings.BUNDLE_VERSION_FILE, 'w') as output:
        versions_str = '\n'.join('    %r: %r,' % (name, vers)
                                 for (name, vers) in versions.iteritems())
        output.write('''\
#!/usr/bin/env python

"""
Media bundle versions.

DO NOT EDIT!  Module generated by 'manage.py bundle_media'.
"""

BUNDLE_VERSIONS = {
%s
}
''' % versions_str)


class VersioningError(Exception):

    """This exception is raised when version creation fails."""


class VersioningBase(object):

    def __init__(self):
        self.versions = get_bundle_versions().copy()

    def get_version(self, source_files):
        raise NotImplementedError

    def update_bundle_version(self, bundle):
        version = self.get_version(bundle)
        orig_path = bundle.get_bundle_path()
        dir, basename = os.path.split(orig_path)
        if '.' in basename:
            name, _, extension = basename.rpartition('.')
            versioned_basename = '.'.join((name, version, extension))
        else:
            versioned_basename += '.' + version
        self.versions[bundle.name] = versioned_basename
        versioned_path = os.path.join(dir, versioned_basename)
        shutil.copy(orig_path, versioned_path)


class MtimeVersioning(VersioningBase):

    def get_version(self, bundle):
        """Return the modification time for the newest source file."""
        return str(max(int(os.stat(f).st_mtime) for f in bundle.get_paths()))


class HashVersioningBase(VersioningBase):

    def __init__(self, hash_method):
        super(HashVersioningBase, self).__init__()
        self.hash_method = hash_method

    def get_version(self, bundle):
        buf = open(bundle.get_bundle_path())
        return self.get_hash(buf)

    def get_hash(self, f, chunk_size=2**14):
        """Compute the hash of a file."""
        m = self.hash_method()
        while 1:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            m.update(chunk)
        return m.hexdigest()


class Md5Versioning(HashVersioningBase):

    def __init__(self):
        super(Md5Versioning, self).__init__(md5)


class Sha1Versioning(HashVersioningBase):

    def __init__(self):
        super(Sha1Versioning, self).__init__(sha1)


VERSIONERS = {
    'sha1': Sha1Versioning,
    'md5': Md5Versioning,
    'mtime': MtimeVersioning,
}

########NEW FILE########
