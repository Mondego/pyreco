__FILENAME__ = adjustments
""" Adjustment factory functions.

An adjustment is a function that takes a list of four identically-sized channel
arrays (red, green, blue, and alpha) and returns a new list of four channels.
The factory functions in this module return functions that perform adjustments.
"""
import sympy
import numpy

def threshold(red_value, green_value=None, blue_value=None):
    """ Return a function that applies a threshold operation.
    """
    if green_value is None or blue_value is None:
        # if there aren't three provided, use the one
        green_value, blue_value = red_value, red_value

    # knowns are given in 0-255 range, need to be converted to floats
    red_value, green_value, blue_value = red_value / 255.0, green_value / 255.0, blue_value / 255.0
    
    def adjustfunc(rgba):
        red, green, blue, alpha = rgba
        
        red[red > red_value] = 1
        red[red <= red_value] = 0
        
        green[green > green_value] = 1
        green[green <= green_value] = 0
        
        blue[blue > blue_value] = 1
        blue[blue <= blue_value] = 0
        
        return red, green, blue, alpha
    
    return adjustfunc

def curves(black, grey, white):
    """ Return a function that applies a curves operation.
        
        Adjustment inspired by Photoshop "Curves" feature.
    
        Arguments are three integers that are intended to be mapped to black,
        grey, and white outputs. Curves2 offers more flexibility, see
        curves2().
        
        Darken a light image by pushing light grey to 50% grey, 0xCC to 0x80
        with black=0, grey=204, white=255.
    """
    # knowns are given in 0-255 range, need to be converted to floats
    black, grey, white = black / 255.0, grey / 255.0, white / 255.0
    
    # coefficients
    a, b, c = [sympy.Symbol(n) for n in 'abc']
    
    # black, gray, white
    eqs = [a * black**2 + b * black + c - 0.0,
           a *  grey**2 + b *  grey + c - 0.5,
           a * white**2 + b * white + c - 1.0]
    
    co = sympy.solve(eqs, a, b, c)
    
    def adjustfunc(rgba):
        red, green, blue, alpha = rgba
    
        # arrays for each coefficient
        do, re, mi = [float(co[n]) * numpy.ones(red.shape, numpy.float32) for n in (a, b, c)]
        
        # arithmetic
        red   = numpy.clip(do * red**2   + re * red   + mi, 0, 1)
        green = numpy.clip(do * green**2 + re * green + mi, 0, 1)
        blue  = numpy.clip(do * blue**2  + re * blue  + mi, 0, 1)
        
        return red, green, blue, alpha
    
    return adjustfunc

def curves2(map_red, map_green=None, map_blue=None):
    """ Return a function that applies a curves operation.
        
        Adjustment inspired by Photoshop "Curves" feature.
    
        Arguments are given in the form of three value mappings, typically
        mapping black, grey and white input and output values. One argument
        indicates an effect applicable to all channels, three arguments apply
        effects to each channel separately.
    
        Simple monochrome inversion:
            map_red=[[0, 255], [128, 128], [255, 0]]
    
        Darken a light image by pushing light grey down by 50%, 0x99 to 0x66:
            map_red=[[0, 255], [153, 102], [255, 0]]
    
        Shaded hills, with Imhof-style purple-blue shadows and warm highlights:
            map_red=[[0, 22], [128, 128], [255, 255]],
            map_green=[[0, 29], [128, 128], [255, 255]],
            map_blue=[[0, 65], [128, 128], [255, 228]]
    """
    if map_green is None or map_blue is None:
        # if there aren't three provided, use the one
        map_green, map_blue = map_red, map_red

    def adjustfunc(rgba):
        red, green, blue, alpha = rgba
        out = []
        
        for (chan, input) in ((red, map_red), (green, map_green), (blue, map_blue)):
            # coefficients
            a, b, c = [sympy.Symbol(n) for n in 'abc']
            
            # parameters given in 0-255 range, need to be converted to floats
            (in_1, out_1), (in_2, out_2), (in_3, out_3) \
                = [(in_ / 255.0, out_ / 255.0) for (in_, out_) in input]
            
            # quadratic function
            eqs = [a * in_1**2 + b * in_1 + c - out_1,
                   a * in_2**2 + b * in_2 + c - out_2,
                   a * in_3**2 + b * in_3 + c - out_3]
            
            co = sympy.solve(eqs, a, b, c)
            
            # arrays for each coefficient
            a, b, c = [float(co[n]) * numpy.ones(chan.shape, numpy.float32) for n in (a, b, c)]
            
            # arithmetic
            out.append(numpy.clip(a * chan**2 + b * chan + c, 0, 1))
        
        return out + [alpha]
    
    return adjustfunc

########NEW FILE########
__FILENAME__ = blends
""" Blend functions.

A blend is a function that accepts two identically-sized
input channel arrays and returns a single output array.
"""
import numpy

def combine(bottom_rgba, top_rgb, mask_chan, opacity, blendfunc):
    """ Blend arrays using a given mask, opacity, and blend function.
    
        A blend function accepts two floating point, two-dimensional
        numpy arrays with values in 0-1 range and returns a third.
    """
    if opacity == 0 or not mask_chan.any():
        # no-op for zero opacity or empty mask
        return [numpy.copy(chan) for chan in bottom_rgba]
    
    # prepare unitialized output arrays
    output_rgba = [numpy.empty_like(chan) for chan in bottom_rgba]
    
    if not blendfunc:
        # plain old paste
        output_rgba[:3] = [numpy.copy(chan) for chan in top_rgb]

    else:
        output_rgba[:3] = [blendfunc(bottom_rgba[c], top_rgb[c]) for c in (0, 1, 2)]
        
    # comined effective mask channel
    if opacity < 1:
        mask_chan = mask_chan * opacity

    # pixels from mask that aren't full-white
    gr = mask_chan < 1
    
    if gr.any():
        # we have some shades of gray to take care of
        for c in (0, 1, 2):
            #
            # Math borrowed from Wikipedia; C0 is the variable alpha_denom:
            # http://en.wikipedia.org/wiki/Alpha_compositing#Analytical_derivation_of_the_over_operator
            #
            
            alpha_denom = 1 - (1 - mask_chan) * (1 - bottom_rgba[3])
            nz = alpha_denom > 0 # non-zero alpha denominator
            
            alpha_ratio = mask_chan[nz] / alpha_denom[nz]
            
            output_rgba[c][nz] = output_rgba[c][nz] * alpha_ratio \
                               + bottom_rgba[c][nz] * (1 - alpha_ratio)
            
            # let the zeros perish
            output_rgba[c][~nz] = 0
    
    # output mask is the screen of the existing and overlaid alphas
    output_rgba[3] = screen(bottom_rgba[3], mask_chan)

    return output_rgba

def screen(bottom_chan, top_chan):
    """ Screen blend function.
    
        Math from http://illusions.hu/effectwiki/doku.php?id=screen_blending
    """
    return 1 - (1 - bottom_chan) * (1 - top_chan)

def add(bottom_chan, top_chan):
    """ Additive blend function.
    
        Math from http://illusions.hu/effectwiki/doku.php?id=additive_blending
    """
    return numpy.clip(bottom_chan + top_chan, 0, 1)

def multiply(bottom_chan, top_chan):
    """ Multiply blend function.
    
        Math from http://illusions.hu/effectwiki/doku.php?id=multiply_blending
    """
    return bottom_chan * top_chan

def subtract(bottom_chan, top_chan):
    """ Subtractive blend function.
    
        Math from http://illusions.hu/effectwiki/doku.php?id=subtractive_blending
    """
    return numpy.clip(bottom_chan - top_chan, 0, 1)

def linear_light(bottom_chan, top_chan):
    """ Linear light blend function.
    
        Math from http://illusions.hu/effectwiki/doku.php?id=linear_light_blending
    """
    return numpy.clip(bottom_chan + 2 * top_chan - 1, 0, 1)

def hard_light(bottom_chan, top_chan):
    """ Hard light blend function.
    
        Math from http://illusions.hu/effectwiki/doku.php?id=hard_light_blending
    """
    # different pixel subsets for dark and light parts of overlay
    dk, lt = top_chan < .5, top_chan >= .5
    
    output_chan = numpy.empty(bottom_chan.shape, bottom_chan.dtype)
    output_chan[dk] = 2 * bottom_chan[dk] * top_chan[dk]
    output_chan[lt] = 1 - 2 * (1 - bottom_chan[lt]) * (1 - top_chan[lt])
    
    return output_chan

########NEW FILE########
__FILENAME__ = photoshop
''' Simple Photoshop file (PSD) writing support.

Blit blending operations normally return new, flattened bitmap objects.
By starting with a PSD layer class, Blit can maintain a chain of separated
layers and allows saving to PSD files.

>>> from Blit import Color, Bitmap, blends, photoshop
>>> psd = photoshop.PSD(128, 128)
>>> psd = psd.blend('Orange', Color(255, 153, 0), Bitmap('photo.jpg'))
>>> psd = psd.blend('Photo', Bitmap('photo.jpg'), blendfunc=blends.linear_light)
>>> psd.save('photo.psd')

Output PSD files have been tested with Photoshop CS3 on Mac, based on this spec:
    http://www.adobe.com/devnet-apps/photoshop/fileformatashtml/PhotoshopFileFormats.htm

Photoshop is a registered trademark of Adobe Corporation.
'''
from struct import pack

import numpy
import Image

from . import Layer
from . import utils
from . import blends
    
def uint8(num):
    return pack('>B', num)

def int16(num):
    return pack('>h', num)

def uint16(num):
    return pack('>H', num)

def uint32(num):
    return pack('>I', num)

def double(num):
    return pack('>d', num)

def pascal_string(chars, pad_to):
    base = uint8(len(chars)) + chars
    base += '\x00' * ((pad_to - len(base) % pad_to) % pad_to)
    
    return base

class Dummy:
    ''' Filler base class for portions of the Photoshop file specification omitted.
    '''
    def tostring(self):
        return uint32(0)

class PhotoshopFile:
    ''' Complete Photoshop file.
    
        http://www.adobe.com/devnet-apps/photoshop/fileformatashtml/PhotoshopFileFormats.htm#50577409_pgfId-1036097
        
        The Photoshop file format is divided into five major parts, as shown
        in the Photoshop file structure:
            http://www.adobe.com/devnet-apps/photoshop/fileformatashtml/images/PhotoshopFileFormatsStructure.gif
    '''
    def __init__(self, file_header, color_mode_data, image_resources, layer_mask_info, image_data):
        self.file_header = file_header
        self.color_mode_data = color_mode_data
        self.image_resources = image_resources
        self.layer_mask_info = layer_mask_info
        self.image_data = image_data
    
    def tostring(self):
        return self.file_header.tostring() + self.color_mode_data.tostring() \
             + self.image_resources.tostring() + self.layer_mask_info.tostring() \
             + self.image_data.tostring()

class FileHeader:
    ''' The file header contains the basic properties of the image.
    
        http://www.adobe.com/devnet-apps/photoshop/fileformatashtml/PhotoshopFileFormats.htm#50577409_19840
    '''
    def __init__(self, channel_count, height, width, depth, color_mode):
        self.channel_count = channel_count
        self.height = height
        self.width = width
        self.depth = depth
        self.color_mode = color_mode
    
    def tostring(self):
        
        parts = [
            '8BPS',
            uint16(1),
            '\x00' * 6,
            uint16(self.channel_count),
            uint32(self.height),
            uint32(self.width),
            uint16(self.depth),
            uint16(self.color_mode)
        ]
        
        return ''.join(parts)

class ColorModeData (Dummy):
    ''' http://www.adobe.com/devnet-apps/photoshop/fileformatashtml/PhotoshopFileFormats.htm#50577409_71638
    '''
    pass

class ImageResourceSection (Dummy):
    ''' http://www.adobe.com/devnet-apps/photoshop/fileformatashtml/PhotoshopFileFormats.htm#50577409_69883
    '''
    pass

class LayerMaskInformation:
    ''' The fourth section of a Photoshop file with information about layers and masks.
    
        http://www.adobe.com/devnet-apps/photoshop/fileformatashtml/PhotoshopFileFormats.htm#50577409_75067
    '''
    def __init__(self, layer_info, global_layer_mask):
        self.layer_info = layer_info
        self.global_layer_mask = global_layer_mask
    
    def tostring(self):
        layer_info = self.layer_info.tostring()
        global_layer_mask = self.global_layer_mask.tostring()
        
        layer_mask_info = layer_info + global_layer_mask
        return uint32(len(layer_mask_info)) + layer_mask_info

class LayerInformation:
    ''' Layer info shows the high-level organization of the layer information.
    
        http://www.adobe.com/devnet-apps/photoshop/fileformatashtml/PhotoshopFileFormats.htm#50577409_16000
    '''
    def __init__(self, layer_count, layer_records, channel_image_data):
        self.layer_count = layer_count
        self.layer_records = layer_records
        self.channel_image_data = channel_image_data
    
    def tostring(self):
        layer_count = uint16(self.layer_count)
        layer_records = ''.join([record.tostring() for record in self.layer_records])
        channel_image_data = self.channel_image_data.tostring()
        
        layer_info = layer_count + layer_records + channel_image_data
        return uint32(len(layer_info)) + layer_info

class LayerRecord:
    ''' Information about each layer.
    
        http://www.adobe.com/devnet-apps/photoshop/fileformatashtml/PhotoshopFileFormats.htm#50577409_13084
    '''
    def __init__(self, rectangle, channel_count, channel_info, blend_mode, opacity,
                 clipping, mask_data, blending_ranges, name, additional_infos):
        self.rectangle = rectangle
        self.channel_count = channel_count
        self.channel_info = channel_info
        self.blend_mode = blend_mode
        self.opacity = opacity
        self.clipping = clipping
        self.mask_data = mask_data
        self.blending_ranges = blending_ranges
        self.name = name
        self.additional_infos = additional_infos
    
    def tostring(self):
        pixel_count = (self.rectangle[2] - self.rectangle[0]) * (self.rectangle[3] - self.rectangle[1])
        mask_data = self.mask_data.tostring()
        blending_ranges = self.blending_ranges.tostring()
        name = pascal_string(self.name, 4)
        additional_infos = ''.join([info.tostring() for info in self.additional_infos])
    
        parts = [
            ''.join(map(uint32, self.rectangle)),
            uint16(self.channel_count),
            ''.join([int16(chid) + uint32(2 + pixel_count) for chid in self.channel_info]),
            '8BIM',
            self.blend_mode,
            uint8(self.opacity),
            uint8(self.clipping),
            uint8(0b00000000),
            uint8(0x00),
            uint32(len(mask_data + blending_ranges + name + additional_infos)),
            mask_data,
            blending_ranges,
            name,
            additional_infos
        ]
        
        return ''.join(parts)

class GlobalLayerMask (Dummy):
    ''' http://www.adobe.com/devnet-apps/photoshop/fileformatashtml/PhotoshopFileFormats.htm#50577409_17115
    '''
    pass

class AdditionalLayerInfo:
    ''' Several types of layer information added in Photoshop 4.0 and later.
    
        http://www.adobe.com/devnet-apps/photoshop/fileformatashtml/PhotoshopFileFormats.htm#50577409_71546
    '''
    code, data = None, None
    
    def tostring(self):
        return '8BIM' + self.code + uint32(len(self.data)) + self.data

class SolidColorInfo (AdditionalLayerInfo):
    ''' Solid color sheet setting (Photoshop 6.0).
    '''
    def __init__(self, red, green, blue):
        red, green, blue = [double(component) for component in (red, green, blue)]
    
        self.code = 'SoCo'
        self.data = '\x00\x00\x00\x10\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00null\x00\x00\x00\x01\x00\x00\x00\x00Clr Objc\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00RGBC\x00\x00\x00\x03\x00\x00\x00\x00Rd  doub%(red)s\x00\x00\x00\x00Grn doub%(green)s\x00\x00\x00\x00Bl  doub%(blue)s' % locals()

class LayerMaskAdjustmentData (Dummy):
    ''' http://www.adobe.com/devnet-apps/photoshop/fileformatashtml/PhotoshopFileFormats.htm#50577409_22582
    '''
    pass

class LayerBlendingRangesData (Dummy):
    ''' http://www.adobe.com/devnet-apps/photoshop/fileformatashtml/PhotoshopFileFormats.htm#50577409_21332
    '''
    pass

class ChannelImageData:
    ''' Bitmap content of color channels.
    
        http://www.adobe.com/devnet-apps/photoshop/fileformatashtml/PhotoshopFileFormats.htm#50577409_26431
    '''
    def __init__(self, channels):
        self.channels = channels
    
    def tostring(self):
        '''
        '''
        # Compression. 0 = Raw Data, 1 = RLE compressed, 2/3 = ZIP.
        return ''.join(['\x00\x00' + chan.tostring() for chan in self.channels])

class ImageData:
    ''' Bitmap content of flattened whole-file preview.
    
        http://www.adobe.com/devnet-apps/photoshop/fileformatashtml/PhotoshopFileFormats.htm#50577409_89817
    '''
    def __init__(self, channels):
        self.channels = channels
    
    def tostring(self):
        '''
        '''
        # Compression. 0 = Raw Data, 1 = RLE compressed, 2/3 = ZIP.
        return '\x00\x00' + ''.join([chan.tostring() for chan in self.channels])

class PSD (Layer):
    ''' Represents a Photoshop document that can be combined with other layers.
    
        Behaves identically to Blit.Layer with addition of a save() method.
    '''
    def __init__(self, width, height):
        ''' Create a new, plain-black PSD instance with specified width and height.
        '''
        channels = [numpy.zeros((height, width), dtype=float)] * 4
        Layer.__init__(self, channels)
        
        self.head = FileHeader(3, height, width, 8, 3)
        self.info = 'Background', self, None, 0xff, 'norm', False
    
    def blend(self, name, other, mask=None, opacity=1, blendfunc=None, clipped=False):
        ''' Return a new PSD instance, with data from another layer included.
        '''
        return _PSDMore(self, name, other, mask, opacity, blendfunc, clipped)
    
    def adjust(self, adjustfunc):
        ''' Adjustment layers are currently not implemented in PSD.
        '''
        raise NotImplementedError("Sorry, no adjustments on PSD")

    def save(self, outfile):
        ''' Save Photoshop-compatible file to a named file or file-like object.
        '''
        #
        # Follow the chain of PSD instances to build up a list of layers.
        #
        info = []
        psd = self
        
        while psd.info:
            info.insert(0, psd.info)
            
            if psd.head:
                file_header = psd.head
                break

            psd = psd.base
        
        #
        # Iterate over layers, make new LayerRecord objects and add channels.
        #
        records = []
        channels = []
        
        for (index, (name, layer, mask, opacity, mode, clipped)) in enumerate(info):
        
            record = dict(
                name = name,
                channel_count = 4,
                channel_info = (0, 1, 2, -1),
                blend_mode = mode,
                opacity = opacity,
                clipping = int(bool(clipped)),
                mask_data = LayerMaskAdjustmentData(),
                blending_ranges = LayerBlendingRangesData(),
                rectangle = (0, 0) + (self.size()[1], self.size()[0]),
                additional_infos = []
                )
            
            channels += utils.rgba2img(layer.rgba(*self.size())).split()

            if index == 0:
                #
                # Background layer has its alpha channel removed.
                #
                record['channel_count'] = 3
                record['channel_info'] = (0, 1, 2)
                channels.pop()
            
            elif layer.size() is None:
                #
                # Layers without sizes are treated as solid colors.
                #
                red, green, blue = [chan[0,0] * 255 for chan in layer.rgba(1, 1)[0:3]]
                record['additional_infos'].append(SolidColorInfo(red, green, blue))
            
            if mask:
                #
                # Add a layer mask channel.
                #
                record['channel_count'] = 5
                record['channel_info'] = (0, 1, 2, -1, -2)
                luminance = utils.rgba2lum(mask.rgba(*self.size()))
                channels.append(utils.chan2img(luminance))
            
            records.append(LayerRecord(**record))
        
        info = LayerInformation(len(records), records, ChannelImageData(channels))
        layer_mask_info = LayerMaskInformation(info, GlobalLayerMask())
        image_data = ImageData(self.image().split()[0:3])
        
        file = PhotoshopFile(file_header, ColorModeData(), ImageResourceSection(), layer_mask_info, image_data)
        
        if not hasattr(outfile, 'write'):
            outfile = open(outfile, 'w')
        
        outfile.write(file.tostring())
        outfile.close()

_modes = {
    blends.screen: 'scrn',
    blends.add: 'lddg',
    blends.multiply: 'mul ',
    blends.linear_light: 'lLit',
    blends.hard_light: 'hLit'
    }

class _PSDMore (PSD):
    ''' Represents a Photoshop document that can be combined with other layers.
    
        Behaves identically to Blit.Layer with addition of a save() method.
    '''
    head = None

    def __init__(self, base, name, other, mask=None, opacity=1, blendfunc=None, clipped=False):
        ''' Create a new PSD instance with the given additional Layer blended.
        
            Arguments
              base: existing PSD instance.
              name: string with name of new layer for Photoshop output.
              other, mask, etc.: identical arguments as Layer.blend().
              clipped: boolean to clip this layer or no.
        '''
        more = Layer.blend(base, other, mask, opacity, blendfunc)
        Layer.__init__(self, more.rgba(*more.size()))
        
        self.base = base
        self.info = name, other, mask, int(opacity * 0xff), \
                    _modes.get(blendfunc, 'norm'), bool(clipped)

########NEW FILE########
__FILENAME__ = tests
""" Tests for Blit.

Run as a module, like this:
    python -m Blit.tests
"""
import unittest
import Image

from . import Bitmap, Color, Layer, blends, adjustments, utils, photoshop

def _str2img(str):
    """
    """
    return Image.fromstring('RGBA', (3, 3), str)

class Tests(unittest.TestCase):

    def setUp(self):
        """
        """
        # Sort of a sw/ne diagonal street, with a top-left corner halo:
        # 
        # +------+   +------+   +------+   +------+   +------+
        # |\\\\\\|   |++++--|   |  ////|   |    ''|   |\\//''|
        # |\\\\\\| + |++++--| + |//////| + |  ''  | > |//''\\|
        # |\\\\\\|   |------|   |////  |   |''    |   |''\\\\|
        # +------+   +------+   +------+   +------+   +------+
        # base       halos      outlines   streets    output
        #
        # Just trust the tests.
        #
        _fff, _ccc, _999, _000, _nil = '\xFF\xFF\xFF\xFF', '\xCC\xCC\xCC\xFF', '\x99\x99\x99\xFF', '\x00\x00\x00\xFF', '\x00\x00\x00\x00'
        
        self.base = Bitmap(_str2img(_ccc * 9))
        self.halos = Bitmap(_str2img(_fff + _fff + _000 + _fff + _fff + (_000 * 4)))
        self.outlines = Bitmap(_str2img(_nil + (_999 * 7) + _nil))
        self.streets = Bitmap(_str2img(_nil + _nil + _fff + _nil + _fff + _nil + _fff + _nil + _nil))
    
    def test0(self):
    
        out = self.base
        out = out.blend(self.outlines)
        out = out.blend(self.streets)
        
        img = out.image()

        assert img.getpixel((0, 0)) == (0xCC, 0xCC, 0xCC, 0xFF), 'top left pixel'
        assert img.getpixel((1, 0)) == (0x99, 0x99, 0x99, 0xFF), 'top center pixel'
        assert img.getpixel((2, 0)) == (0xFF, 0xFF, 0xFF, 0xFF), 'top right pixel'
        assert img.getpixel((0, 1)) == (0x99, 0x99, 0x99, 0xFF), 'center left pixel'
        assert img.getpixel((1, 1)) == (0xFF, 0xFF, 0xFF, 0xFF), 'middle pixel'
        assert img.getpixel((2, 1)) == (0x99, 0x99, 0x99, 0xFF), 'center right pixel'
        assert img.getpixel((0, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom left pixel'
        assert img.getpixel((1, 2)) == (0x99, 0x99, 0x99, 0xFF), 'bottom center pixel'
        assert img.getpixel((2, 2)) == (0xCC, 0xCC, 0xCC, 0xFF), 'bottom right pixel'
    
    def test1(self):

        out = self.base
        out = out.blend(self.outlines, self.halos)
        out = out.blend(self.streets)
        
        img = out.image()

        assert img.getpixel((0, 0)) == (0xCC, 0xCC, 0xCC, 0xFF), 'top left pixel'
        assert img.getpixel((1, 0)) == (0x99, 0x99, 0x99, 0xFF), 'top center pixel'
        assert img.getpixel((2, 0)) == (0xFF, 0xFF, 0xFF, 0xFF), 'top right pixel'
        assert img.getpixel((0, 1)) == (0x99, 0x99, 0x99, 0xFF), 'center left pixel'
        assert img.getpixel((1, 1)) == (0xFF, 0xFF, 0xFF, 0xFF), 'middle pixel'
        assert img.getpixel((2, 1)) == (0xCC, 0xCC, 0xCC, 0xFF), 'center right pixel'
        assert img.getpixel((0, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom left pixel'
        assert img.getpixel((1, 2)) == (0xCC, 0xCC, 0xCC, 0xFF), 'bottom center pixel'
        assert img.getpixel((2, 2)) == (0xCC, 0xCC, 0xCC, 0xFF), 'bottom right pixel'
    
    def test2(self):
    
        out = Color(0xcc, 0xcc, 0xcc)
        out = out.blend(self.outlines, self.halos)
        out = out.blend(self.streets)
        
        img = out.image()
        
        assert img.getpixel((0, 0)) == (0xCC, 0xCC, 0xCC, 0xFF), 'top left pixel'
        assert img.getpixel((1, 0)) == (0x99, 0x99, 0x99, 0xFF), 'top center pixel'
        assert img.getpixel((2, 0)) == (0xFF, 0xFF, 0xFF, 0xFF), 'top right pixel'
        assert img.getpixel((0, 1)) == (0x99, 0x99, 0x99, 0xFF), 'center left pixel'
        assert img.getpixel((1, 1)) == (0xFF, 0xFF, 0xFF, 0xFF), 'middle pixel'
        assert img.getpixel((2, 1)) == (0xCC, 0xCC, 0xCC, 0xFF), 'center right pixel'
        assert img.getpixel((0, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom left pixel'
        assert img.getpixel((1, 2)) == (0xCC, 0xCC, 0xCC, 0xFF), 'bottom center pixel'
        assert img.getpixel((2, 2)) == (0xCC, 0xCC, 0xCC, 0xFF), 'bottom right pixel'
    
    def test3(self):
        
        out = Color(0xcc, 0xcc, 0xcc)
        out = out.blend(Color(0x99, 0x99, 0x99), self.halos)
        out = out.blend(self.streets)
        
        img = out.image()
        
        assert img.getpixel((0, 0)) == (0x99, 0x99, 0x99, 0xFF), 'top left pixel'
        assert img.getpixel((1, 0)) == (0x99, 0x99, 0x99, 0xFF), 'top center pixel'
        assert img.getpixel((2, 0)) == (0xFF, 0xFF, 0xFF, 0xFF), 'top right pixel'
        assert img.getpixel((0, 1)) == (0x99, 0x99, 0x99, 0xFF), 'center left pixel'
        assert img.getpixel((1, 1)) == (0xFF, 0xFF, 0xFF, 0xFF), 'middle pixel'
        assert img.getpixel((2, 1)) == (0xCC, 0xCC, 0xCC, 0xFF), 'center right pixel'
        assert img.getpixel((0, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom left pixel'
        assert img.getpixel((1, 2)) == (0xCC, 0xCC, 0xCC, 0xFF), 'bottom center pixel'
        assert img.getpixel((2, 2)) == (0xCC, 0xCC, 0xCC, 0xFF), 'bottom right pixel'
    
    def test4(self):

        out = Color(0x00, 0x00, 0x00, 0x00)
        out = out.blend(Color(0x99, 0x99, 0x99), self.halos)
        out = out.blend(self.streets)
        
        img = out.image()
        
        assert img.getpixel((0, 0)) == (0x99, 0x99, 0x99, 0xFF), 'top left pixel'
        assert img.getpixel((1, 0)) == (0x99, 0x99, 0x99, 0xFF), 'top center pixel'
        assert img.getpixel((2, 0)) == (0xFF, 0xFF, 0xFF, 0xFF), 'top right pixel'
        assert img.getpixel((0, 1)) == (0x99, 0x99, 0x99, 0xFF), 'center left pixel'
        assert img.getpixel((1, 1)) == (0xFF, 0xFF, 0xFF, 0xFF), 'middle pixel'
        assert img.getpixel((2, 1)) == (0x00, 0x00, 0x00, 0x00), 'center right pixel'
        assert img.getpixel((0, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom left pixel'
        assert img.getpixel((1, 2)) == (0x00, 0x00, 0x00, 0x00), 'bottom center pixel'
        assert img.getpixel((2, 2)) == (0x00, 0x00, 0x00, 0x00), 'bottom right pixel'
    
    def test5(self):

        out = Color(0x00, 0x00, 0x00, 0x00)
        out = out.blend(Color(0x99, 0x99, 0x99))
        
        img = out.image()
        
        assert img.getpixel((0, 0)) == (0x99, 0x99, 0x99, 0xFF)

    def test6(self):
    
        image = Image.new('RGBA', (10, 20), (0xff, 0x00, 0xff, 0xff))
        layer = Layer(utils.img2rgba(image))
        assert layer.size() == image.size
        
        image = utils.rgba2img(layer.rgba(10, 20))
        assert image.size == layer.size()

        assert image.getpixel((0, 0)) == (0xff, 0x00, 0xff, 0xff)
        assert image.getpixel((9, 19)) == (0xff, 0x00, 0xff, 0xff)

class AlphaTests(unittest.TestCase):
    """
    """
    def setUp(self):

        _808f = '\x80\x80\x80\xFF'
        _fff0, _fff8, _ffff = '\xFF\xFF\xFF\x00', '\xFF\xFF\xFF\x80', '\xFF\xFF\xFF\xFF'
        _0000, _0008, _000f = '\x00\x00\x00\x00', '\x00\x00\x00\x80', '\x00\x00\x00\xFF'
        
        # 50% gray all over
        self.gray = Bitmap(_str2img(_808f * 9))
            
        # nothing anywhere
        self.nothing = Bitmap(_str2img(_0000 * 9))
            
        # opaque horizontal gradient, black to white
        self.h_gradient = Bitmap(_str2img((_000f + _808f + _ffff) * 3))
            
        # transparent white at top to opaque white at bottom
        self.white_wipe = Bitmap(_str2img(_fff0 * 3 + _fff8 * 3 + _ffff * 3))
            
        # transparent black at top to opaque black at bottom
        self.black_wipe = Bitmap(_str2img(_0000 * 3 + _0008 * 3 + _000f * 3))
    
    def test0(self):
    
        out = self.gray
        out = out.blend(self.white_wipe)
        
        img = out.image()
        
        assert img.getpixel((0, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top left pixel'
        assert img.getpixel((1, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top center pixel'
        assert img.getpixel((2, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top right pixel'
        assert img.getpixel((0, 1)) == (0xC0, 0xC0, 0xC0, 0xFF), 'center left pixel'
        assert img.getpixel((1, 1)) == (0xC0, 0xC0, 0xC0, 0xFF), 'middle pixel'
        assert img.getpixel((2, 1)) == (0xC0, 0xC0, 0xC0, 0xFF), 'center right pixel'
        assert img.getpixel((0, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom left pixel'
        assert img.getpixel((1, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom center pixel'
        assert img.getpixel((2, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom right pixel'
    
    def test1(self):
        
        out = self.gray
        out = out.blend(self.black_wipe)
        
        img = out.image()
        
        assert img.getpixel((0, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top left pixel'
        assert img.getpixel((1, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top center pixel'
        assert img.getpixel((2, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top right pixel'
        assert img.getpixel((0, 1)) == (0x40, 0x40, 0x40, 0xFF), 'center left pixel'
        assert img.getpixel((1, 1)) == (0x40, 0x40, 0x40, 0xFF), 'middle pixel'
        assert img.getpixel((2, 1)) == (0x40, 0x40, 0x40, 0xFF), 'center right pixel'
        assert img.getpixel((0, 2)) == (0x00, 0x00, 0x00, 0xFF), 'bottom left pixel'
        assert img.getpixel((1, 2)) == (0x00, 0x00, 0x00, 0xFF), 'bottom center pixel'
        assert img.getpixel((2, 2)) == (0x00, 0x00, 0x00, 0xFF), 'bottom right pixel'
    
    def test2(self):
    
        out = self.gray
        out = out.blend(self.white_wipe, self.h_gradient)
        
        img = out.image()
        
        assert img.getpixel((0, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top left pixel'
        assert img.getpixel((1, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top center pixel'
        assert img.getpixel((2, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top right pixel'
        assert img.getpixel((0, 1)) == (0x80, 0x80, 0x80, 0xFF), 'center left pixel'
        assert img.getpixel((1, 1)) == (0xA0, 0xA0, 0xA0, 0xFF), 'middle pixel'
        assert img.getpixel((2, 1)) == (0xC0, 0xC0, 0xC0, 0xFF), 'center right pixel'
        assert img.getpixel((0, 2)) == (0x80, 0x80, 0x80, 0xFF), 'bottom left pixel'
        assert img.getpixel((1, 2)) == (0xC0, 0xC0, 0xC0, 0xFF), 'bottom center pixel'
        assert img.getpixel((2, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom right pixel'
    
    def test3(self):
        
        out = self.gray
        out = out.blend(self.black_wipe, self.h_gradient)
        
        img = out.image()
        
        assert img.getpixel((0, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top left pixel'
        assert img.getpixel((1, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top center pixel'
        assert img.getpixel((2, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top right pixel'
        assert img.getpixel((0, 1)) == (0x80, 0x80, 0x80, 0xFF), 'center left pixel'
        assert img.getpixel((1, 1)) == (0x60, 0x60, 0x60, 0xFF), 'middle pixel'
        assert img.getpixel((2, 1)) == (0x40, 0x40, 0x40, 0xFF), 'center right pixel'
        assert img.getpixel((0, 2)) == (0x80, 0x80, 0x80, 0xFF), 'bottom left pixel'
        assert img.getpixel((1, 2)) == (0x40, 0x40, 0x40, 0xFF), 'bottom center pixel'
        assert img.getpixel((2, 2)) == (0x00, 0x00, 0x00, 0xFF), 'bottom right pixel'
    
    def test4(self):
        
        out = self.nothing
        out = out.blend(self.white_wipe)
        
        img = out.image()
        
        assert img.getpixel((0, 0)) == (0x00, 0x00, 0x00, 0x00), 'top left pixel'
        assert img.getpixel((1, 0)) == (0x00, 0x00, 0x00, 0x00), 'top center pixel'
        assert img.getpixel((2, 0)) == (0x00, 0x00, 0x00, 0x00), 'top right pixel'
        assert img.getpixel((0, 1)) == (0xFF, 0xFF, 0xFF, 0x80), 'center left pixel'
        assert img.getpixel((1, 1)) == (0xFF, 0xFF, 0xFF, 0x80), 'middle pixel'
        assert img.getpixel((2, 1)) == (0xFF, 0xFF, 0xFF, 0x80), 'center right pixel'
        assert img.getpixel((0, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom left pixel'
        assert img.getpixel((1, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom center pixel'
        assert img.getpixel((2, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom right pixel'

class BlendTests(unittest.TestCase):
    """
    """
    def setUp(self):
    
        _808f = '\x80\x80\x80\xFF'
        _ffff = '\xFF\xFF\xFF\xFF'
        _000f = '\x00\x00\x00\xFF'
        
        # opaque horizontal gradient, black to white
        self.h_gradient = Bitmap(_str2img((_000f + _808f + _ffff) * 3))
            
        # opaque vertical gradient, black to white
        self.v_gradient = Bitmap(_str2img(_000f * 3 + _808f * 3 + _ffff * 3))
    
    def test0(self):
        
        out = self.h_gradient
        out = out.blend(self.v_gradient, blendfunc=blends.screen)
        
        img = out.image()
        
        assert img.getpixel((0, 0)) == (0x00, 0x00, 0x00, 0xFF), 'top left pixel'
        assert img.getpixel((1, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top center pixel'
        assert img.getpixel((2, 0)) == (0xFF, 0xFF, 0xFF, 0xFF), 'top right pixel'
        assert img.getpixel((0, 1)) == (0x80, 0x80, 0x80, 0xFF), 'center left pixel'
        assert img.getpixel((1, 1)) == (0xC0, 0xC0, 0xC0, 0xFF), 'middle pixel'
        assert img.getpixel((2, 1)) == (0xFF, 0xFF, 0xFF, 0xFF), 'center right pixel'
        assert img.getpixel((0, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom left pixel'
        assert img.getpixel((1, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom center pixel'
        assert img.getpixel((2, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom right pixel'
    
    def test1(self):
        
        out = self.h_gradient
        out = out.blend(self.v_gradient, blendfunc=blends.multiply)
        
        img = out.image()
        
        assert img.getpixel((0, 0)) == (0x00, 0x00, 0x00, 0xFF), 'top left pixel'
        assert img.getpixel((1, 0)) == (0x00, 0x00, 0x00, 0xFF), 'top center pixel'
        assert img.getpixel((2, 0)) == (0x00, 0x00, 0x00, 0xFF), 'top right pixel'
        assert img.getpixel((0, 1)) == (0x00, 0x00, 0x00, 0xFF), 'center left pixel'
        assert img.getpixel((1, 1)) == (0x40, 0x40, 0x40, 0xFF), 'middle pixel'
        assert img.getpixel((2, 1)) == (0x80, 0x80, 0x80, 0xFF), 'center right pixel'
        assert img.getpixel((0, 2)) == (0x00, 0x00, 0x00, 0xFF), 'bottom left pixel'
        assert img.getpixel((1, 2)) == (0x80, 0x80, 0x80, 0xFF), 'bottom center pixel'
        assert img.getpixel((2, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom right pixel'
    
    def test2(self):
        
        out = self.h_gradient
        out = out.blend(self.v_gradient, blendfunc=blends.linear_light)
        
        img = out.image()
        
        assert img.getpixel((0, 0)) == (0x00, 0x00, 0x00, 0xFF), 'top left pixel'
        assert img.getpixel((1, 0)) == (0x00, 0x00, 0x00, 0xFF), 'top center pixel'
        assert img.getpixel((2, 0)) == (0x00, 0x00, 0x00, 0xFF), 'top right pixel'
        assert img.getpixel((0, 1)) == (0x01, 0x01, 0x01, 0xFF), 'center left pixel'
        assert img.getpixel((1, 1)) == (0x81, 0x81, 0x81, 0xFF), 'middle pixel'
        assert img.getpixel((2, 1)) == (0xFF, 0xFF, 0xFF, 0xFF), 'center right pixel'
        assert img.getpixel((0, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom left pixel'
        assert img.getpixel((1, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom center pixel'
        assert img.getpixel((2, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom right pixel'
    
    def test3(self):
        
        out = self.h_gradient
        out = out.blend(self.v_gradient, blendfunc=blends.hard_light)
        
        img = out.image()
        
        assert img.getpixel((0, 0)) == (0x00, 0x00, 0x00, 0xFF), 'top left pixel'
        assert img.getpixel((1, 0)) == (0x00, 0x00, 0x00, 0xFF), 'top center pixel'
        assert img.getpixel((2, 0)) == (0x00, 0x00, 0x00, 0xFF), 'top right pixel'
        assert img.getpixel((0, 1)) == (0x01, 0x01, 0x01, 0xFF), 'center left pixel'
        assert img.getpixel((1, 1)) == (0x80, 0x80, 0x80, 0xFF), 'middle pixel'
        assert img.getpixel((2, 1)) == (0xFF, 0xFF, 0xFF, 0xFF), 'center right pixel'
        assert img.getpixel((0, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom left pixel'
        assert img.getpixel((1, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom center pixel'
        assert img.getpixel((2, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom right pixel'
    
    def test4(self):
        
        out = self.h_gradient
        out = out.blend(self.v_gradient, opacity=0.5)
        
        img = out.image()
        
        assert img.getpixel((0, 0)) == (0x00, 0x00, 0x00, 0xFF), 'top left pixel'
        assert img.getpixel((1, 0)) == (0x40, 0x40, 0x40, 0xFF), 'top center pixel'
        assert img.getpixel((2, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top right pixel'
        assert img.getpixel((0, 1)) == (0x40, 0x40, 0x40, 0xFF), 'center left pixel'
        assert img.getpixel((1, 1)) == (0x80, 0x80, 0x80, 0xFF), 'middle pixel'
        assert img.getpixel((2, 1)) == (0xC0, 0xC0, 0xC0, 0xFF), 'center right pixel'
        assert img.getpixel((0, 2)) == (0x80, 0x80, 0x80, 0xFF), 'bottom left pixel'
        assert img.getpixel((1, 2)) == (0xC0, 0xC0, 0xC0, 0xFF), 'bottom center pixel'
        assert img.getpixel((2, 2)) == (0xFF, 0xFF, 0xFF, 0xFF), 'bottom right pixel'
    
    def test5(self):
        psd = photoshop.PSD(3, 6).blend('dark', Color(0, 0, 0), opacity=0.5)
        
        assert psd.size() == (3, 6)

class AdjustmentTests(unittest.TestCase):
    """
    """
    def setUp(self):
    
        _808f = '\x80\x80\x80\xFF'
        _ffff = '\xFF\xFF\xFF\xFF'
        _000f = '\x00\x00\x00\xFF'
        
        # simple 50% gray dot
        self.gray = Color(0x80, 0x80, 0x80)
    
        # opaque horizontal gradient, black to white
        self.h_gradient = Bitmap(_str2img((_000f + _808f + _ffff) * 3))
    
    def test0(self):
        
        out = self.h_gradient.adjust(adjustments.threshold(0x99))
        
        img = out.image()
        
        assert img.getpixel((0, 0)) == (0x00, 0x00, 0x00, 0xFF), 'top left pixel'
        assert img.getpixel((1, 0)) == (0x00, 0x00, 0x00, 0xFF), 'top center pixel'
        assert img.getpixel((2, 0)) == (0xFF, 0xFF, 0xFF, 0xFF), 'top right pixel'
    
    def test1(self):
        
        out = self.h_gradient.adjust(adjustments.threshold(0x99, 0x66, 0x66))
        
        img = out.image()
        
        assert img.getpixel((0, 0)) == (0x00, 0x00, 0x00, 0xFF), 'top left pixel'
        assert img.getpixel((1, 0)) == (0x00, 0xFF, 0xFF, 0xFF), 'top center pixel'
        assert img.getpixel((2, 0)) == (0xFF, 0xFF, 0xFF, 0xFF), 'top right pixel'
    
    def test2(self):
        
        out = self.h_gradient.adjust(adjustments.curves(0xFF, 0xC0, 0x00))
        
        img = out.image()
        
        assert img.getpixel((0, 0)) == (0xFF, 0xFF, 0xFF, 0xFF), 'top left pixel'
        assert img.getpixel((1, 0)) == (0xD6, 0xD6, 0xD6, 0xFF), 'top center pixel'
        assert img.getpixel((2, 0)) == (0x00, 0x00, 0x00, 0xFF), 'top right pixel'
    
    def test3(self):
        
        red_map = [[0x00, 0x00], [0x80, 0x40], [0xFF, 0xFF]]
        out = self.h_gradient.adjust(adjustments.curves2(red_map))
        
        img = out.image()
        
        assert img.getpixel((0, 0)) == (0x00, 0x00, 0x00, 0xFF), 'top left pixel'
        assert img.getpixel((1, 0)) == (0x40, 0x40, 0x40, 0xFF), 'top center pixel'
        assert img.getpixel((2, 0)) == (0xFF, 0xFF, 0xFF, 0xFF), 'top right pixel'
    
    def test4(self):
        
        red_map = [[0x00, 0xFF], [0x80, 0x80], [0xFF, 0x00]]
        out = self.h_gradient.adjust(adjustments.curves2(red_map))
        
        img = out.image()
        
        assert img.getpixel((0, 0)) == (0xFF, 0xFF, 0xFF, 0xFF), 'top left pixel'
        assert img.getpixel((1, 0)) == (0x80, 0x80, 0x80, 0xFF), 'top center pixel'
        assert img.getpixel((2, 0)) == (0x00, 0x00, 0x00, 0xFF), 'top right pixel'
    
    def test4(self):
        
        red_map   = [[0, 22], [128, 128], [255, 255]]
        green_map = [[0, 29], [128, 128], [255, 255]]
        blue_map  = [[0, 65], [128, 128], [255, 228]]
        out = self.h_gradient.adjust(adjustments.curves2(red_map, green_map, blue_map))
        
        img = out.image()
        
        assert img.getpixel((0, 0)) == ( 22,  29,  65, 0xFF), 'top left pixel'
        assert img.getpixel((1, 0)) == (128, 128, 128, 0xFF), 'top center pixel'
        assert img.getpixel((2, 0)) == (255, 255, 228, 0xFF), 'top right pixel'
    
    def test5(self):
        
        out = self.gray.adjust(adjustments.threshold(0x99))
        img = out.image()
        
        assert img.getpixel((0, 0)) == (0x00, 0x00, 0x00, 0xFF)
    
    def test6(self):
        
        out = self.gray.adjust(adjustments.threshold(0x66))
        img = out.image()
        
        assert img.getpixel((0, 0)) == (0xFF, 0xFF, 0xFF, 0xFF)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = utils
import numpy
import Image

def arr2img(ar):
    """ Convert Numeric array to PIL Image.
    """
    return Image.fromstring('L', (ar.shape[1], ar.shape[0]), ar.astype(numpy.ubyte).tostring())

def img2arr(im):
    """ Convert PIL Image to Numeric array.
    """
    assert im.mode == 'L'
    return numpy.reshape(numpy.fromstring(im.tostring(), numpy.ubyte), (im.size[1], im.size[0]))

def chan2img(chan):
    """ Convert single Numeric array object to one-channel PIL Image.
    """
    return arr2img(numpy.round(chan * 255.0).astype(numpy.ubyte))

def img2chan(img):
    """ Convert one-channel PIL Image to single Numeric array object.
    """
    return img2arr(img).astype(numpy.float32) / 255.0

def rgba2img(rgba):
    """ Convert four Numeric array objects to PIL Image.
    """
    assert type(rgba) in (tuple, list)
    return Image.merge('RGBA', [chan2img(band) for band in rgba])

def img2rgba(im):
    """ Convert PIL Image to four Numeric array objects.
    """
    assert im.mode == 'RGBA'
    return [img2chan(band) for band in im.split()]

def rgba2lum(rgba):
    """ Convert four Numeric array objects to single luminance array.

        Use the RGB information from the supplied channels,
        but convert it to a single channel as in YUV:
        http://en.wikipedia.org/wiki/YUV#Conversion_to.2Ffrom_RGB
        
        Discard alpha channel.
    """
    red, green, blue = rgba[0:3]
    luminance = 0.299 * red + 0.587 * green + 0.114 * blue
    return luminance

########NEW FILE########
