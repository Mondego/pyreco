__FILENAME__ = base
"""
colors.base
===========
Convert colors between rgb, hsv, and hex, perform arithmetic, blend modes,
and generate random colors within boundaries.
"""
import colorsys
import random as random_

__all__ = ('Color', 'HSVColor', 'RGBColor', 'HexColor', 'ColorWheel',
           'rgb', 'hsv', 'hex',)

HEX_RANGE = frozenset('0123456789abcdef')


class _ColorMetaClass(type):
    """
    Metaclass for Color to simply map the cls.Meta.properties to getters.

    >>> RGBColor(r=150, g=0, b=100).red
    150
    """
    def __new__(cls, name, bases, attrs):
        # Check for internal Meta class providing a property map
        if 'Meta' in attrs and hasattr(attrs['Meta'], 'properties'):
            for index, prop in enumerate(attrs['Meta'].properties):
                # Assign pretty getters to each property name
                attrs[prop] = property(lambda self, index=index: self._color[index])
        return super(_ColorMetaClass, cls).__new__(cls, name, bases, attrs)


class Color(object):
    """ Abstract base class for all color types. """
    __metaclass__ = _ColorMetaClass

    @property
    def hex(self):
        """ Hex is used the same way for all types. """
        return HexColor('%02x%02x%02x' % tuple(self.rgb))

    @property
    def rgb(self):
        raise NotImplemented

    @property
    def hsv(self):
        raise NotImplemented

    def multiply(self, other):
        self_rgb = self.rgb
        other_rgb = other.rgb
        return RGBColor(
            self_rgb.red * other_rgb.red / 255.0,
            self_rgb.green * other_rgb.green / 255.0,
            self_rgb.blue * other_rgb.blue / 255.0
        )

    __mul__ = multiply

    def add(self, other):
        self_rgb = self.rgb
        other_rgb = other.rgb
        return RGBColor(
            min(255, self_rgb.red + other_rgb.red),
            min(255, self_rgb.green + other_rgb.green),
            min(255, self_rgb.blue + other_rgb.blue),
        )

    __add__ = add

    def divide(self, other):
        self_rgb = self.rgb
        other_rgb = other.rgb
        if 0 in other_rgb:
            raise ZeroDivisionError
        return RGBColor(
            self_rgb.red / float(other_rgb.red),
            self_rgb.green / float(other_rgb.green),
            self_rgb.blue / float(other_rgb.blue),
        )

    __div__ = divide

    def subtract(self, other):
        self_rgb = self.rgb
        other_rgb = other.rgb
        return RGBColor(
            max(0, (self_rgb.red - other_rgb.red)),
            max(0, (self_rgb.green - other_rgb.green)),
            max(0, (self_rgb.blue - other_rgb.blue)),
        )

    __sub__ = subtract

    def screen(self, other):
        self_rgb = self.rgb
        other_rgb = other.rgb
        return RGBColor(
            255 - (((255 - self_rgb.red) * (255 - other_rgb.red)) / 255.0),
            255 - (((255 - self_rgb.green) * (255 - other_rgb.green)) / 255.0),
            255 - (((255 - self_rgb.blue) * (255 - other_rgb.blue)) / 255.0),
        )

    def difference(self, other):
        self_rgb = self.rgb
        other_rgb = other.rgb
        return RGBColor(
            abs(self_rgb.red - other_rgb.red),
            abs(self_rgb.green - other_rgb.green),
            abs(self_rgb.blue - other_rgb.blue),
        )

    def overlay(self, other):
        return self.screen(self.multiply(other))

    def invert(self):
        return self.difference(RGBColor(255, 255, 255))

    def __eq__(self, other):
        self_rgb = self.rgb
        other_rgb = other.rgb
        return self_rgb.red == other_rgb.red \
           and self_rgb.green == other_rgb.green \
           and self_rgb.blue == other_rgb.blue

    def __contains__(self, item):
        return item in self._color

    def __ne__(self, other):
        return not self.__eq__(other)

    def __iter__(self):
        """ Treat the color object as an iterable to iterate over color values
        Allows mapping such as:

        >>> list(rgb(100, 50, 0))
        [100, 50, 0]
        >>> for i in rgb(100, 50, 0): print i
        100
        50
        0
        """
        return iter(self._color)

    def __len__(self):
        return len(self._color)

    def __str__(self):
        return ', '.join(map(str, self._color))

    def __repr__(self):
        base = u'<%s %s>'
        properties = [
            '%s: %s' % (prop, getattr(self, prop)) \
                for prop in self.Meta.properties
        ]
        return base % (self.__class__.__name__, ', '.join(properties))


class HSVColor(Color):
    """ Hue Saturation Value """

    def __init__(self, h=0, s=0, v=0):
        if s > 1:
            raise ValueError('Saturation has to be less than 1')
        if v > 1:
            raise ValueError('Value has to be less than 1')

        # Hue can safely circle around 1
        if h >= 1:
            h -= int(h)

        self._color = h, s, v

    @property
    def rgb(self):
        return RGBColor(*map(lambda c: c * 255, colorsys.hsv_to_rgb(*self._color)))

    @property
    def hsv(self):
        return self

    class Meta:
        properties = ('hue', 'saturation', 'value')


class RGBColor(Color):
    """ Red Green Blue """

    def __init__(self, r=0, g=0, b=0):
        self._color = r, g, b
        for c in self._color:
            if c < 0 or c > 255:
                raise ValueError('Color values must be between 0 and 255')

    @property
    def rgb(self):
        return self

    @property
    def hsv(self):
        return HSVColor(*colorsys.rgb_to_hsv(*map(lambda c: c / 255.0, self._color)))

    class Meta:
        properties = ('red', 'green', 'blue')


class HexColor(RGBColor):
    """ Typical 6 digit hexadecimal colors.

    Warning: accuracy is lost when converting a color to hex
    """

    def __init__(self, hex='000000'):
        if len(hex) != 6:
            raise ValueError('Hex color must be 6 digits')

        hex = hex.lower()
        if not set(hex).issubset(HEX_RANGE):
            raise ValueError('Not a valid hex number')

        self._color = hex[:2], hex[2:4], hex[4:6]

    @property
    def rgb(self):
        return RGBColor(*[int(c, 16) for c in self._color])

    @property
    def hsv(self):
        return self.rgb.hsv

    @property
    def hex(self):
        return self

    def __str__(self):
        return '%s%s%s' % self._color


class ColorWheel(object):
    """ Iterate random colors disributed relatively evenly
    around the color wheel.

    >>> from colors import ColorWheel
    >>> wheel = ColorWheel()
    >>> print '#%s' % wheel.next().hex
    #cc8b00
    >>> wheel = ColorWheel(start=0.2)
    >>> print '#%s' % wheel.next().hex
    #00cc26
    >>> print '#%s' % wheel.next().hex
    #009ecc
    """
    def __init__(self, start=0):
        # A 1.1 shift is identical to 0.1
        if start >= 1:
            start -= 1
        self._phase = start

    def __iter__(self):
        return self

    def next(self):
        shift = (random_.random() * 0.1) + 0.1
        self._phase += shift
        if self._phase >= 1:
            self._phase -= 1
        return HSVColor(self._phase, 1, 0.8)


def random():  # This name might be a bad idea?
    """ Generate a random color.

    >>> from colors import random
    >>> random()
    <HSVColor hue: 0.310089903395, saturation: 0.765033516918, value: 0.264921257867>
    >>> print '#%s' % random().hex
    #ae47a7

    """
    return HSVColor(random_.random(), random_.random(), random_.random())

# Simple aliases
rgb = RGBColor  # rgb(100, 100, 100), or rgb(r=100, g=100, b=100)
hsv = HSVColor  # hsv(0.5, 1, 1), or hsv(h=0.5, s=1, v=1)
hex = HexColor  # hex('BADA55')

########NEW FILE########
__FILENAME__ = primary
"""
colors.primary
==============
"""
from .base import rgb

black = rgb(0, 0, 0)
white = rgb(255, 255, 255)
red = rgb(255, 0, 0)
green = rgb(0, 255, 0)
blue = rgb(0, 0, 255)

########NEW FILE########
__FILENAME__ = rainbow
"""
colors.rainbow
==============
ROYGBIV!
"""
from .base import rgb

red = rgb(255, 0, 0)
orange = rgb(255, 165, 0)
yellow = rgb(255, 255, 0)
green = rgb(0, 128, 0)
blue = rgb(0, 0, 255)
indigo = rgb(75, 0, 130)
violet = rgb(238, 130, 238)

########NEW FILE########
__FILENAME__ = w3c
"""
colors.w3c
==========
Official CSS colors, scraped from: http://www.w3schools.com/tags/ref_color_tryit.asp
"""
from .base import rgb

aliceblue = rgb(240, 248, 255)
antiquewhite = rgb(250, 235, 215)
aqua = rgb(0, 255, 255)
aquamarine = rgb(127, 255, 212)
azure = rgb(240, 255, 255)
beige = rgb(245, 245, 220)
bisque = rgb(255, 228, 196)
black = rgb(0, 0, 0)
blanchedalmond = rgb(255, 235, 205)
blue = rgb(0, 0, 255)
blueviolet = rgb(138, 43, 226)
brown = rgb(165, 42, 42)
burlywood = rgb(222, 184, 135)
cadetblue = rgb(95, 158, 160)
chartreuse = rgb(127, 255, 0)
chocolate = rgb(210, 105, 30)
coral = rgb(255, 127, 80)
cornflowerblue = rgb(100, 149, 237)
cornsilk = rgb(255, 248, 220)
crimson = rgb(220, 20, 60)
cyan = rgb(0, 255, 255)
darkblue = rgb(0, 0, 139)
darkcyan = rgb(0, 139, 139)
darkgoldenrod = rgb(184, 134, 11)
darkgray = rgb(169, 169, 169)
darkgrey = rgb(169, 169, 169)
darkgreen = rgb(0, 100, 0)
darkkhaki = rgb(189, 183, 107)
darkmagenta = rgb(139, 0, 139)
darkolivegreen = rgb(85, 107, 47)
darkorange = rgb(255, 140, 0)
darkorchid = rgb(153, 50, 204)
darkred = rgb(139, 0, 0)
darksalmon = rgb(233, 150, 122)
darkseagreen = rgb(143, 188, 143)
darkslateblue = rgb(72, 61, 139)
darkslategray = rgb(47, 79, 79)
darkslategrey = rgb(47, 79, 79)
darkturquoise = rgb(0, 206, 209)
darkviolet = rgb(148, 0, 211)
deeppink = rgb(255, 20, 147)
deepskyblue = rgb(0, 191, 255)
dimgray = rgb(105, 105, 105)
dimgrey = rgb(105, 105, 105)
dodgerblue = rgb(30, 144, 255)
firebrick = rgb(178, 34, 34)
floralwhite = rgb(255, 250, 240)
forestgreen = rgb(34, 139, 34)
fuchsia = rgb(255, 0, 255)
gainsboro = rgb(220, 220, 220)
ghostwhite = rgb(248, 248, 255)
gold = rgb(255, 215, 0)
goldenrod = rgb(218, 165, 32)
gray = rgb(128, 128, 128)
grey = rgb(128, 128, 128)
green = rgb(0, 128, 0)
greenyellow = rgb(173, 255, 47)
honeydew = rgb(240, 255, 240)
hotpink = rgb(255, 105, 180)
indianred = rgb(205, 92, 92)
indigo = rgb(75, 0, 130)
ivory = rgb(255, 255, 240)
khaki = rgb(240, 230, 140)
lavender = rgb(230, 230, 250)
lavenderblush = rgb(255, 240, 245)
lawngreen = rgb(124, 252, 0)
lemonchiffon = rgb(255, 250, 205)
lightblue = rgb(173, 216, 230)
lightcoral = rgb(240, 128, 128)
lightcyan = rgb(224, 255, 255)
lightgoldenrodyellow = rgb(250, 250, 210)
lightgray = rgb(211, 211, 211)
lightgrey = rgb(211, 211, 211)
lightgreen = rgb(144, 238, 144)
lightpink = rgb(255, 182, 193)
lightsalmon = rgb(255, 160, 122)
lightseagreen = rgb(32, 178, 170)
lightskyblue = rgb(135, 206, 250)
lightslategray = rgb(119, 136, 153)
lightslategrey = rgb(119, 136, 153)
lightsteelblue = rgb(176, 196, 222)
lightyellow = rgb(255, 255, 224)
lime = rgb(0, 255, 0)
limegreen = rgb(50, 205, 50)
linen = rgb(250, 240, 230)
magenta = rgb(255, 0, 255)
maroon = rgb(128, 0, 0)
mediumaquamarine = rgb(102, 205, 170)
mediumblue = rgb(0, 0, 205)
mediumorchid = rgb(186, 85, 211)
mediumpurple = rgb(147, 112, 219)
mediumseagreen = rgb(60, 179, 113)
mediumslateblue = rgb(123, 104, 238)
mediumspringgreen = rgb(0, 250, 154)
mediumturquoise = rgb(72, 209, 204)
mediumvioletred = rgb(199, 21, 133)
midnightblue = rgb(25, 25, 112)
mintcream = rgb(245, 255, 250)
mistyrose = rgb(255, 228, 225)
moccasin = rgb(255, 228, 181)
navajowhite = rgb(255, 222, 173)
navy = rgb(0, 0, 128)
oldlace = rgb(253, 245, 230)
olive = rgb(128, 128, 0)
olivedrab = rgb(107, 142, 35)
orange = rgb(255, 165, 0)
orangered = rgb(255, 69, 0)
orchid = rgb(218, 112, 214)
palegoldenrod = rgb(238, 232, 170)
palegreen = rgb(152, 251, 152)
paleturquoise = rgb(175, 238, 238)
palevioletred = rgb(219, 112, 147)
papayawhip = rgb(255, 239, 213)
peachpuff = rgb(255, 218, 185)
peru = rgb(205, 133, 63)
pink = rgb(255, 192, 203)
plum = rgb(221, 160, 221)
powderblue = rgb(176, 224, 230)
purple = rgb(128, 0, 128)
red = rgb(255, 0, 0)
rosybrown = rgb(188, 143, 143)
royalblue = rgb(65, 105, 225)
saddlebrown = rgb(139, 69, 19)
salmon = rgb(250, 128, 114)
sandybrown = rgb(244, 164, 96)
seagreen = rgb(46, 139, 87)
seashell = rgb(255, 245, 238)
sienna = rgb(160, 82, 45)
silver = rgb(192, 192, 192)
skyblue = rgb(135, 206, 235)
slateblue = rgb(106, 90, 205)
slategray = rgb(112, 128, 144)
slategrey = rgb(112, 128, 144)
snow = rgb(255, 250, 250)
springgreen = rgb(0, 255, 127)
steelblue = rgb(70, 130, 180)
tan = rgb(210, 180, 140)
teal = rgb(0, 128, 128)
thistle = rgb(216, 191, 216)
tomato = rgb(255, 99, 71)
turquoise = rgb(64, 224, 208)
violet = rgb(238, 130, 238)
wheat = rgb(245, 222, 179)
white = rgb(255, 255, 255)
whitesmoke = rgb(245, 245, 245)
yellow = rgb(255, 255, 0)
yellowgreen = rgb(154, 205, 50)

########NEW FILE########
