__FILENAME__ = artwork_file
#-------------------------------------------------------------------------------
#
# iOS .artwork file extractor
# (c)2008-2012 Dave Peck <davepeck [at] davepeck [dot] org> All Rights Reserved
#
# Released under the three-clause BSD license.
#
# http://github.com/davepeck/iOS-artwork/
#
#-------------------------------------------------------------------------------

import PIL.Image
from .binary_file import BinaryFile, WritableBinaryFile


#------------------------------------------------------------------------------
# ArtworkImage
#------------------------------------------------------------------------------

class ArtworkImage(object):
    """
    Abstract class for metadata and accessor for a single image in
    an artwork file.
    """
    def __init__(self, artwork_file, artwork_set):
        super(ArtworkImage, self).__init__()
        self.artwork_file = artwork_file
        self.artwork_set = artwork_set

    @property
    def name(self):
        raise NotImplementedError("Implement in a derived class.")

    @property
    def width(self):
        raise NotImplementedError("Implement in a derived class.")

    @property
    def height(self):
        raise NotImplementedError("Implement in a derived class.")

    @property
    def image_offset(self):
        raise NotImplementedError("Implement in a derived class.")

    @property
    def is_greyscale(self):
        raise NotImplementedError("Implement in a derived class.")

    @property
    def retina_appropriate_name(self):
        name = self.name
        if self.artwork_set.is_retina and ("@2x" not in name):
            name = name.replace(".png", "@2x.png")
        return name

    def get_pil_image(self):
        return self.artwork_file.read_pil_image_at(self.image_offset, self.width, self.height, self.is_greyscale)



#------------------------------------------------------------------------------
# ArtworkSet
#------------------------------------------------------------------------------

class ArtworkSet(object):
    """
    Abstract base class for a group of objects that repsent metadata
    for all images found in an artwork file.
    """
    def __init__(self, artwork_file):
        super(ArtworkSet, self).__init__()
        self.artwork_file = artwork_file

    @property
    def version(self):
        raise NotImplementedError("Implement in a derived class.")

    @property
    def image_count(self):
        raise NotImplementedError("Implement in a derived class.")

    def iter_images(self):
        raise NotImplementedError("Implement in a derived class.")

    @property
    def name(self):
        return self.artwork_file.basename

    @property
    def is_retina(self):
        return "@2x" in self.name


#------------------------------------------------------------------------------
# ArtworkFileCommon
#------------------------------------------------------------------------------

class ArtworkFileCommon(object):
    """
    APIs that apply to both read and write artwork files.
    """
    def byte_align(self, offset, alignment):
        """Perform packing alignment appropriate for image pixels in the .artwork file"""
        remainder = offset % alignment
        if remainder != 0:
            offset += (alignment - remainder)
        return offset

    def width_byte_align(self, width, **kwargs):
        return self.byte_align(width, self.width_byte_packing(**kwargs))

    def width_byte_packing(self, **kwargs):
        raise NotImplementedError("Implement in a derived class.")

    @property
    def artwork_set(self):
        raise NotImplementedError("Implement in a derived class.")


#------------------------------------------------------------------------------
# ArtworkFile
#------------------------------------------------------------------------------

class ArtworkFile(BinaryFile, ArtworkFileCommon):
    """Base class for reading an iOS SDK .artwork file, of any iOS era."""

    def __init__(self, filename):
        super(ArtworkFile, self).__init__(filename)
        self.greyscale_pixel_size = 1
        self.color_pixel_size = 4

    def read_greyscale_pixel_at(self, offset):
        return self.read_byte_at(offset)

    def read_color_pixel_at(self, offset):
        # Returns b, g, r, a
        return self.unpack("BBBB", offset)

    def read_pil_greyscale_pixel_at(self, offset):
        grey = self.read_greyscale_pixel_at(offset)
        return (grey, grey, grey, 255)

    def read_pil_color_pixel_at(self, offset):
        b, g, r, a = self.read_color_pixel_at(offset)
        # Handle premultiplied alpha
        if (a != 0):
            r = (r * 255 + a // 2) // a
            g = (g * 255 + a // 2) // a
            b = (b * 255 + a // 2) // a
        return (r, g, b, a)

    def read_pil_image_at(self, offset, width, height, is_greyscale):
        """Return a PIL image instance of given size, at a given offset in the .artwork file."""
        pil_image = PIL.Image.new("RGBA", (width, height))
        pil_pixels = pil_image.load()
        aligned_width = self.width_byte_align(width, is_greyscale=is_greyscale)
        pixel_width = self.greyscale_pixel_size if is_greyscale else self.color_pixel_size

        for y in range(height):
            for x in range(width):
                pixel_offset = offset + (pixel_width * ((y * aligned_width) + x))
                if is_greyscale:
                    pil_pixels[x, y] = self.read_pil_greyscale_pixel_at(pixel_offset)
                else:
                    pil_pixels[x, y] = self.read_pil_color_pixel_at(pixel_offset)

        return pil_image

    def iter_images(self):
        raise NotImplementedError("Implement in a derived class.")


#------------------------------------------------------------------------------
# WritableArtworkFile
#------------------------------------------------------------------------------

class WriteableArtworkFile(WritableBinaryFile, ArtworkFileCommon):
    """Represents a writable iOS SDK .artwork file"""

    def __init__(self, filename, template_binary):
        super(WriteableArtworkFile, self).__init__(filename, template_binary)

    def write_greyscale_pixel_at(self, offset, grey):
        self.write_byte_at(offset, grey)

    def write_color_pixel_at(self, offset, b, g, r, a):
        self.pack("BBBB", offset, b, g, r, a)

    def write_pil_greyscale_pixel_at(self, offset, r, g, b, a):
        self.write_greyscale_pixel_at(offset, grey=b)

    def write_pil_color_pixel_at(self, offset, r, g, b, a):
        # handle premultiplied alpha
        r = (r * a + 127) // 255
        g = (g * a + 127) // 255
        b = (b * a + 127) // 255
        self.write_color_pixel_at(offset, b, g, r, a)

    def write_pil_image_at(self, offset, width, height, is_greyscale, pil_image):
        """Write a PIL image instance of given size, to a given offset in the .artwork file."""
        pil_pixels = pil_image.load()
        aligned_width = self.width_byte_align(width, is_greyscale=is_greyscale)
        pixel_width = 1 if is_greyscale else 4

        for y in range(height):
            for x in range(width):
                pixel_offset = offset + (pixel_width * ((y * aligned_width) + x))

                if pil_image.mode == 'RGBA':
                    r, g, b, a = pil_pixels[x, y]
                else:
                    r, g, b = pil_pixels[x, y]
                    a = 255

                if is_greyscale:
                    self.write_pil_greyscale_pixel_at(pixel_offset, r, g, b, a)
                else:
                    self.write_pil_color_pixel_at(pixel_offset, r, g, b, a)


########NEW FILE########
__FILENAME__ = binary_file
#-------------------------------------------------------------------------------
#
# iOS .artwork file extractor
# (c)2008-2012 Dave Peck <davepeck [at] davepeck [dot] org> All Rights Reserved
# 
# Released under the three-clause BSD license.
#
# http://github.com/davepeck/iOS-artwork/
#
#-------------------------------------------------------------------------------

import os
import os.path
import struct
import mmap


#------------------------------------------------------------------------------
# BinaryFile
#------------------------------------------------------------------------------

class BinaryFile(object):
    """
    A read-only binary file on disk, with some basic tools to read from it.
    """
    BYTE = 1
    SHORT = 2
    LONG = 4

    def __init__(self, filename, endian="<"):
        super(BinaryFile, self).__init__()
        self.filename = filename
        self._file = None
        self._data = None
        self._data_length = -1
        self._endian = endian
        
    def __del__(self):
        if self._data is not None:
            self._data.close()
            self._data = None
        if self._file is not None:
            self._file.close()
            self._file = None

    @property
    def is_little_endian(self):
        return self._endian == "<"
        
    @property
    def basename(self):
        return os.path.basename(self.filename)
            
    @property
    def file_size(self):
        return os.path.getsize(self.filename)
            
    @property
    def data(self):
        if self._data is None:
            self._file = open(self.filename, "rb")
            self._data = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)
        return self._data
        
    @property
    def data_length(self):
        if self._data_length == -1:
            self._data_length = len(self.data)
        return self._data_length

    def unpack(self, structure, offset):
        return struct.unpack_from("%s%s" % (self._endian, structure), self.data, offset)

    def read_long_at(self, offset):
        return self.unpack("L", offset)[0]

    def read_short_at(self, offset):
        return self.unpack("H", offset)[0]

    def read_byte_at(self, offset):
        return self.unpack("B", offset)[0]

    def read_null_terminated_utf8_string_at(self, offset):
        start = offset
        while ord(self.data[offset]) != 0:
            offset += 1
        bytes = self.data[start:offset]
        return bytes.decode("utf-8")


#------------------------------------------------------------------------------
# WritableBinaryFile
#------------------------------------------------------------------------------

class WritableBinaryFile(BinaryFile):
    """
    A writable binary file on disk, backed by a template read-only binary.
    """
    def __init__(self, filename, template_binary, endian="<"):
        super(WritableBinaryFile, self).__init__(filename, endian)
        self.template_binary = template_binary
        self._data_length = template_binary.data_length

    @property
    def data(self):
        if self._data is None:
            # Copy over the template binary's contents
            self._file = open(self.filename, "wb")
            self._file.write(self.template_binary.data)
            self._file.close()

            self._file = open(self.filename, "r+b")
            self._data = mmap.mmap(self._file.fileno(), self.data_length, access=mmap.ACCESS_WRITE)
        return self._data
    
    @property
    def data_length(self):
        return self._data_length
        
    def open(self):
        return self.data  # HACK -- obviously a bogus OM.
        
    def close(self):
        self._data.flush()
        self._data.close()
        self._file.close()
        self._data = None
        self._file = None
        
    def delete(self):
        self.close()
        os.remove(self.filename)

    def pack(self, structure, offset, *values):
        struct.pack_into("%s%s" % (self._endian, structure), self.data, offset, *values)

    def write_long_at(self, offset, l):
        self.pack("L", offset, l)

    def write_short_at(self, offset, h):
        self.pack("H", offset, h)

    def write_byte_at(self, offset, b):
        self.pack("B", offset, b)

    def write_null_terminated_utf8_string_at(self, offset, s):
        bytes = s.encode("utf-8")
        for byte in bytes:
            self.data[offset] = byte
            offset += 1
        self.data[offset] = chr(0)




########NEW FILE########
__FILENAME__ = framework_file
#-------------------------------------------------------------------------------
#
# iOS .artwork file extractor
# (c)2008-2012 Dave Peck <davepeck [at] davepeck [dot] org> All Rights Reserved
# 
# Released under the three-clause BSD license.
#
# http://github.com/davepeck/iOS-artwork/
#
#-------------------------------------------------------------------------------

from .binary_file import BinaryFile


#-------------------------------------------------------------------------------
# CFString
#-------------------------------------------------------------------------------

class CFString(object):
    """struct __builtin_CFString { const int *isa; int flags; const char *str; long length; }"""
    SIZE = 16
    
    # See http://www.opensource.apple.com/source/CF/CF-550.42/CFString.c
    kCFHasLengthByte = 0x04
    kCFHasNullByte = 0x08
    kCFIsUnicode = 0x10
    
    def __init__(self, framework_file, offset):
        self.framework_file = framework_file
        self.objc_class, self.flags, self.pointer, self.length = self.framework_file.unpack("LLLL", offset)
        
    @property
    def string(self):
        """Read the const char* (string) portion of a CFString."""
        s = None
        
        if (self.flags & CFString.kCFHasLengthByte):
            assert ord(self.framework_file.data[self.pointer]) == self.length, "Invalid length or length byte."
            self.pointer += 1
        
        if (self.flags & CFString.kCFIsUnicode):
            bytes = self.framework_file.data[self.pointer:self.pointer + (self.length * 2)]
            last_byte = self.framework_file.data[self.pointer + (self.length * 2)]
            if self.is_little_endian:
                s = bytes.decode('utf-16le')
            else:
                s = bytes.decode('utf-16be')
        else:
            bytes = self.framework_file.data[self.pointer:self.pointer + self.length]
            last_byte = self.framework_file.data[self.pointer + self.length]
            s = bytes.decode('ascii')
        
        if (self.flags & CFString.kCFHasNullByte):
            assert last_byte == '\0', "Something went wrong reading a CFString."
            
        return s


#-------------------------------------------------------------------------------
# ArtworkSetMetadata
#-------------------------------------------------------------------------------

class ArtworkSetMetadata(object):
    SIZE = 36

    def __init__(self, framework_file, offset):
        self.framework_file = framework_file
        # sizes_offset points directly to an array of ArtworkMetadataInformation structs
        # names_offset is the address of an array of pointers to cfstrings. (yikes.)
        self.set_name_offset, _, _, self.sizes_offset, self.names_offset, self.artwork_count, _, _, _, _ = self.framework_file.unpack("LLLLLHHLLL", offset)

    def __repr__(self):
        return "ArtworkSetInformation %s [sno: %x; so: %x; no: %x; ac: %d; e: %r; o: %x]" % (self.name, self.set_name_offset, self.sizes_offset, self.names_offset, self.artwork_count, self.endian, self.offset)
    
    @property
    def name(self):
        return CFString(self.framework_file, self.set_name_offset).string

    @property
    def image_count(self):
        return self.artwork_count

    @property
    def version(self):
        return "6.0.0" # For now?

    @property
    def is_retina(self):
        return "@2x" in self.name
    
    def iter_images(self):
        size_offset = self.sizes_offset
        name_offset = self.names_offset

        # Walk through the artwork and gather information.
        for artwork_i in range(self.artwork_count):
            name_pointer = self.framework_file.read_long_at(name_offset)
            artwork_image_metadata = ArtworkImageMetadata(self.framework_file, self, size_offset, name_pointer)
            size_offset += ArtworkImageMetadata.SIZE
            name_offset += 4
            yield artwork_image_metadata

    def to_jsonable(self):
        return {
            "images": [image_metadata.to_jsonable() for image_metadata in self.iter_images()],
            "name": self.name,
            "version": self.version,
            "byte_size": "FILL_THIS_IN",
        }
            

#-------------------------------------------------------------------------------
# ArtworkImageMetadata
#-------------------------------------------------------------------------------

class ArtworkImageMetadata(object):
    """
    Appears to be struct 
    { 
        unsigned int24_t offset_into_artwork_file; 
        unsigned char flags; // these are deep and mysterious.
        unsigned int width; 
        unsigned int height; 
    }
    """
    SIZE = 8

    def __init__(self, framework_file, artwork_set_metadata, size_offset, name_pointer):
        self.framework_file = framework_file
        self.artwork_set_metadata = artwork_set_metadata
        offset_with_flags, self.width, self.height = self.framework_file.unpack("LHH", size_offset)
        self.flags = (offset_with_flags & 0xFF) # Flags only
        self.image_offset = (offset_with_flags & 0xFFFFFF00) # Remove the flags
        self.name = CFString(self.framework_file, name_pointer).string

    @property
    def retina_appropriate_name(self):
        name = self.name
        if self.artwork_set_metadata.is_retina and ("@2x" not in name):
            name = name.replace(".png", "@2x.png")
        return name

    def to_jsonable(self):
        return [
            self.retina_appropriate_name,
            self.width,
            self.height,
            self.image_offset,
            self.flags,
        ]


#-------------------------------------------------------------------------------
# FrameworkFile
#-------------------------------------------------------------------------------

class FrameworkFile(BinaryFile):
    """
    Random hacknology collection for cracking open Mach-O
    framework binaries, although we partially ignore the
    Mach-O-ness of them.
    """
    def __init__(self, filename):
        super(FrameworkFile, self).__init__(filename)

    def read_artwork_set_metadata_at(self, offset):
        return ArtworkSetMetadata(self, offset)





########NEW FILE########
__FILENAME__ = legacy_artwork_file
#-------------------------------------------------------------------------------
#
# iOS .artwork file extractor
# (c)2008-2012 Dave Peck <davepeck [at] davepeck [dot] org> All Rights Reserved
#
# Released under the three-clause BSD license.
#
# http://github.com/davepeck/iOS-artwork/
#
#-------------------------------------------------------------------------------

from __future__ import with_statement  # For compatibility with python 2.5 -- this is legacy.

import os
import os.path
import json
from .artwork_file import ArtworkImage, ArtworkSet, ArtworkFile, WriteableArtworkFile

#
# Legacy *.artwork files are found in iOS5 and earlier, and are also
# found in the occasional odd iOS6 artwork file (such as AssistantMic@2x.artwork)
#
# These artwork files contain images in raw RGBA and/or greyscale form,
# but the problem is that the metadata needed to extract those images
# (namely, their names, sizes, colorspaces, and byte offsets in the file)
# are *not* found in the artwork file. Instead, the metadata are found
# in a motley assortment of Mach-O binaries. For example, you can find
# the metadata for iOS5's Shared~iphone.artwork in the UIKit binary.
#
# If you look through the history of this repo, you'll discover a script
# (now deleted) called generate-from-macho-binary.py that looks for
# (unexported) symbols that point to the metadata table. That script
# outputs the files now housed in the legacy_metadata/ directory.
#
# In order to crack a legacy artwork binary file, it must be married
# with a corresponding json file. If the json file is missing, the file
# is not supported, although you could try and support it by going
# back in time and running generate-from-macho-binary.py yourself.
#


#------------------------------------------------------------------------------
# LegacyArtworkImage: for iOS5 and previous (and one or two iOS6 files, ugh.)
#------------------------------------------------------------------------------

class LegacyArtworkImage(ArtworkImage):
    def __init__(self, artwork_file, artwork_set, jsonable):
        super(LegacyArtworkImage, self).__init__(artwork_file, artwork_set)
        try:
            self._name, self._width, self._height, self._image_offset, self._flags = jsonable
        except Exception:
            # iOS3 json files don't even have the flags info
            self._name, self._width, self._height, self._image_offset = jsonable
            self._flags = 0

    @property
    def name(self):
        return self._name

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def image_offset(self):
        return self._image_offset

    @property
    def is_greyscale(self):
        return (self._flags & 0x02) != 0


#------------------------------------------------------------------------------
# LegacyArtworkSet
#------------------------------------------------------------------------------

class LegacyArtworkSet(ArtworkSet):
    def __init__(self, artwork_file, jsonable):
        super(LegacyArtworkSet, self).__init__(artwork_file)
        self._jsonable = jsonable

    @property
    def version(self):
        return self._jsonable["version"]

    @property
    def image_count(self):
        return len(self._jsonable["images"])

    def iter_images(self):
        for image_jsonable in self._jsonable["images"]:
            yield LegacyArtworkImage(self.artwork_file, self, image_jsonable)


#------------------------------------------------------------------------------
# LegacyArtworkFile
#------------------------------------------------------------------------------

class LegacyArtworkFile(ArtworkFile):
    def __init__(self, filename):
        super(LegacyArtworkFile, self).__init__(filename)

    def width_byte_packing(self, **kwargs):
        return 8

    @property
    def artwork_set(self):
        return LegacyArtworkSet(self, self.legacy_jsonable)

    @property
    def _script_directory(self):
        return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    @property
    def _legacy_metadata_directory(self):
        return os.path.join(self._script_directory, "legacy_metadata")

    @property
    def _legacy_metadata_json_file_name(self):
        return os.path.join(self._legacy_metadata_directory, "%s-%d.json" % (self.basename, self.file_size))

    @property
    def legacy_jsonable(self):
        with open(self._legacy_metadata_json_file_name) as f:
            jsonable = json.loads(f.read())
        return jsonable

    @property
    def is_legacy(self):
        return True

    @property
    def is_modern(self):
        return False

    @property
    def is_legacy_supported(self):
        legacy_metadata_json_file_name = self._legacy_metadata_json_file_name
        return os.path.exists(legacy_metadata_json_file_name)



#------------------------------------------------------------------------------
# LegacyWriteableArtworkFile
#------------------------------------------------------------------------------

class WriteableLegacyArtworkFile(WriteableArtworkFile):
    def __init__(self, filename, template_binary):
        super(WriteableLegacyArtworkFile, self).__init__(filename, template_binary)

    def width_byte_packing(self, **kwargs):
        return 8

    @property
    def artwork_set(self):
        return self.template_binary.artwork_set()



########NEW FILE########
__FILENAME__ = modern_artwork_file
#-------------------------------------------------------------------------------
#
# iOS .artwork file extractor
# (c)2008-2012 Dave Peck <davepeck [at] davepeck [dot] org> All Rights Reserved
#
# Released under the three-clause BSD license.
#
# http://github.com/davepeck/iOS-artwork/
#
#-------------------------------------------------------------------------------

from .artwork_file import ArtworkImage, ArtworkSet, ArtworkFile, WriteableArtworkFile

#
# Modern *.artwork files are found in iOS6 and (hopefully) above.
# Just about all of the iOS6 SDK artwork files are "modern" -- there appear
# to be a handful of stragglers.
#
# Unlike previous generations of iOS, these files are self-contained:
# they contain both the images (in raw RGBA and/or greyscale form)
# and they contain the metadata (names, sizes, byte offsets) for the
# images. This means that ModernArtwork* classes have code to crack
# this metadata directly from the artwork file in question -- no need
# to crack a mach-o binary for metadata anymore! (Thank goodness.)
#
# iOS6 artwork files start with a header, and end with image contents.
# The header is packed as follows:
#
# image_count: LONG
# offset_to_information_array: LONG
# image_name_offsets_array: image_count array of LONG
# information_array: image_count array of 12-byte values, each of which is:
#   flags: LONG -- stuff like the color space, and mysterious other things
#   width: SHORT
#   height: SHORT
#   offset: LONG
#


#------------------------------------------------------------------------------
# ModernArtworkImage: for iOS6 and (hopefully) beyond
#------------------------------------------------------------------------------

class ModernArtworkImage(ArtworkImage):
    SIZE = 12

    def __init__(self, artwork_file, artwork_set, name, info_offset):
        super(ModernArtworkImage, self).__init__(artwork_file, artwork_set)
        self._name = name
        self._flags, self._width, self._height, self._image_offset = self.artwork_file.unpack("LHHL", info_offset)

    @property
    def name(self):
        return self._name

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def image_offset(self):
        return self._image_offset

    @property
    def is_greyscale(self):
        return (self._flags & 0x02) != 0


#------------------------------------------------------------------------------
# ModernArtworkSet
#------------------------------------------------------------------------------

class ModernArtworkSet(ArtworkSet):
    _NAME_OFFSET_ARRAY_OFFSET = 8

    def __init__(self, artwork_file):
        super(ModernArtworkSet, self).__init__(artwork_file)

    @property
    def version(self):
        return "iOS6+"

    @property
    def image_count(self):
        return self.artwork_file.read_long_at(0)

    @property
    def _image_info_array_offset(self):
        return self.artwork_file.read_long_at(4)

    def iter_images(self):
        info_offset = self._image_info_array_offset
        name_offset_offset = ModernArtworkSet._NAME_OFFSET_ARRAY_OFFSET
        for i in range(self.image_count):
            name_offset = self.artwork_file.read_long_at(name_offset_offset)
            name = self.artwork_file.read_null_terminated_utf8_string_at(name_offset)
            yield ModernArtworkImage(self.artwork_file, self, name, info_offset)
            name_offset_offset += ModernArtworkFile.LONG
            info_offset += ModernArtworkImage.SIZE


#------------------------------------------------------------------------------
# ModernArtworkFile
#------------------------------------------------------------------------------

class ModernArtworkFile(ArtworkFile):
    def __init__(self, filename):
        super(ModernArtworkFile, self).__init__(filename)

    def width_byte_packing(self, is_greyscale, **kwargs):
        return 4 if is_greyscale else 1

    @property
    def artwork_set(self):
        return ModernArtworkSet(self)

    @property
    def is_legacy(self):
        return False

    @property
    def is_modern(self):
        return True

    @property
    def is_modern_supported(self):
        artwork_set = self.artwork_set
        return (artwork_set.image_count > 0) and (artwork_set.image_count <= 4096)


#------------------------------------------------------------------------------
# ModernWriteableArtworkFile
#------------------------------------------------------------------------------

class WriteableModernArtworkFile(WriteableArtworkFile):
    def __init__(self, filename, template_binary):
        super(WriteableModernArtworkFile, self).__init__(filename, template_binary)

    def width_byte_packing(self, is_greyscale, **kwargs):
        return 4 if is_greyscale else 1

    @property
    def artwork_set(self):
        return self.template_binary.artwork_set()



########NEW FILE########
__FILENAME__ = generate-legacy-metadata
#!/usr/bin/env python

#-------------------------------------------------------------------------------
#
# iOS .artwork file extractor
# (c)2008-2012 Dave Peck <davepeck [at] davepeck [dot] org> All Rights Reserved
# 
# Released under the three-clause BSD license.
#
# http://github.com/davepeck/iOS-artwork/
#
#-------------------------------------------------------------------------------

#
# NOTE: you almost certainly don't want or need to use this script. ;-)
#

import sys
import json
from artwork.framework_file import FrameworkFile



#-------------------------------------------------------------------------------
# __main__ :: supremely hacknological, but handy, at the moment
#-------------------------------------------------------------------------------

# Want to know what offset to toss in here?
#
# 1. Find the name of an arwork file, say Foo@2x.artwork
# 2. Use hex fiend to find the location of the string "Foo@2x\0" in the appropriate framework binary
# 3. Work backwards in the hex editor to find the CFString, and then the pointer to that CFString.
# 4. Use the offset where the pointer to the CFString is located!
#
# For example, in iOS 6.0.0, in the Assistant Mach-O binary, the offset
# you want for AssistantMic@2x.artwork is: 0x70BC0 (461760)

def main(framework_file_name, artwork_set_metadata_offset):
    framework_file = FrameworkFile(framework_file_name)
    artwork_set_metadata = framework_file.read_artwork_set_metadata_at(artwork_set_metadata_offset)
    jsonable = artwork_set_metadata.to_jsonable()
    json_string = json.dumps(jsonable, indent=4)
    print json_string    

if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))

########NEW FILE########
__FILENAME__ = iOS-artwork
#!/usr/bin/env python

#-------------------------------------------------------------------------------
#
# iOS .artwork file extractor
# (c)2008-2012 Dave Peck <davepeck [at] davepeck [dot] org> All Rights Reserved
# 
# Released under the three-clause BSD license.
#
# http://github.com/davepeck/iOS-artwork/
#
#-------------------------------------------------------------------------------

# iOS-artwork.py
#
# This script makes it easy to extract images from the .artwork files found
# in the iOS SDK. To use it, you must have python and the Python Imaging Libraries
# (PIL) installed.
#
# Run it as:
#
#   ./iOS-artwork.py export -a artwork_file.artwork -d export_directory
#
# You can also create a new .artwork file by importing a directory of images:
#
#   ./iOS-artwork.py create -a original_artwork_file.artwork -d import_directory -c created_artwork_file.artwork
#
# Please see the README file for more details.

import os
import sys
import PIL
import PIL.Image
from optparse import OptionParser

# import PIL.Image

from artwork.legacy_artwork_file import LegacyArtworkFile, WriteableLegacyArtworkFile
from artwork.modern_artwork_file import ModernArtworkFile, WriteableModernArtworkFile
    
COMMANDS = ["export", "create"]

def usage(parser):
    parser.print_help()
    sys.exit(-1)

def bail(message):
    print "\n%s\n" % message
    sys.exit(-1)

def file_extension(file_name):
    return os.path.splitext(file_name)[1][1:]
    
def action_export(artwork_file_name, directory):
    artwork_file = LegacyArtworkFile(artwork_file_name)
    if not artwork_file.is_legacy_supported:
        artwork_file = ModernArtworkFile(artwork_file_name)
        if not artwork_file.is_modern_supported:
            bail("FAIL. This tool does not currently support %s" % artwork_file_name)

    artwork_set = artwork_file.artwork_set    
    print "\nExporting %d images from %s (version %s)..." % (artwork_set.image_count, artwork_set.name, artwork_set.version)
    
    for artwork_image in artwork_set.iter_images():
        pil_image = artwork_image.get_pil_image()
        export_file_name = os.path.join(directory, artwork_image.retina_appropriate_name)
        pil_image.save(export_file_name, file_extension(export_file_name))
        print "\texported %s" % export_file_name
        
    print "\nDONE EXPORTING!"
    
def action_create(artwork_file_name, directory, create_file_name):
    artwork_file = LegacyArtworkFile(artwork_file_name)
    if not artwork_file.is_legacy_supported:
        artwork_file = ModernArtworkFile(artwork_file_name)
        if not artwork_file.is_modern_supported:
            bail("FAIL. This tool does not currently support %s" % artwork_file_name)

    if artwork_file.is_legacy:
        create_file = WriteableLegacyArtworkFile(create_file_name, artwork_file)
    else:
        create_file = WriteableModernArtworkFile(create_file_name, artwork_file)        
    create_file.open()

    artwork_set = artwork_file.artwork_set
    print "\nCreating a new file named %s by importing %d images...\n\t(Using %s version %s as a template.)" % (create_file_name, artwork_set.image_count, artwork_set.name, artwork_set.version)
    
    for artwork_image in artwork_set.iter_images():
        #
        # Grab the image from disk
        #
        pil_image_name = os.path.join(directory, artwork_image.retina_appropriate_name)
        if not os.path.exists(pil_image_name):
            create_file.delete()
            bail("FAIL. An image named %s was not found in directory %s" % (artwork_image.retina_appropriate_name, directory))
            
        #
        # Validate the image
        #
        try:
            pil_image = PIL.Image.open(pil_image_name)
        except IOError:
            create_file.delete()
            bail("FAIL. The image file named %s was invalid or could not be read." % pil_image_name)
        
        actual_width, actual_height = pil_image.size
        if (actual_width != artwork_image.width) or (actual_height != artwork_image.height):
            create_file.delete()
            bail("FAIL. The image file named %s should be %d x %d in size, but is actually %d x %d." % (pil_image_name, artwork_image.width, artwork_image.height, actual_width, actual_height))
        
        try:
            if (pil_image.mode != 'RGBA') and (pil_image.mode != 'RGB'):
                pil_image = pil_image.convert('RGBA')
        except:
            create_file.delete()
            bail("FAIL. The image file named %s could not be converted to a usable format." % pil_image_name)
        
        #
        # Write it
        #
        create_file.write_pil_image_at(artwork_image.image_offset, artwork_image.width, artwork_image.height, artwork_image.is_greyscale, pil_image)
        print "\timported %s" % artwork_image.retina_appropriate_name
    
    create_file.close()
    
    print "\nDONE CREATING!"
    
def main(argv):
    #
    # Set up command-line options parser
    #
    parser = OptionParser(usage = """%prog [command] [parameters]

    export 
        -a artwork_file.artwork 
        -d export_directory
    
        Exports the contents of artwork_file.artwork as a set
        of images in the export_directory
    
    create  
        -a original_artwork_file.artwork 
        -d import_directory 
        -c created_artwork_file.artwork
         
        Imports the images found in import_directory into a new
        artwork file named created_artwork_file.artwork. Uses
        the original file for sizing and other information, but
        never writes to the original file.
    """)
    parser.add_option("-a", "--artwork", dest="artwork_file_name", help="Specify the input artwork file name. (Read-only.)", default = None)
    parser.add_option("-d", "--directory", dest="directory", help="Specify the directory to export images to/import images from.", default = None)
    parser.add_option("-c", "--create", dest="create_file_name", help="Specify the output artwork file name. (Write-only.)", default = None)

    #
    # Parse
    #
    (options, arguments) = parser.parse_args()
    
    #
    # Validate
    #
    if (len(arguments) != 1) or (options.artwork_file_name is None) or (options.directory is None):
        usage(parser)
        
    command = arguments[0].lower()
    if command not in COMMANDS:
        usage(parser)
        
    if (command == "create") and (options.create_file_name is None):
        usage(parser)
        
    abs_artwork_file_name = os.path.abspath(options.artwork_file_name)
    
    if not os.path.exists(abs_artwork_file_name):
        bail("No artwork file named %s was found." % options.artwork_file_name)
        
    abs_directory = os.path.abspath(options.directory)
    
    if not os.path.exists(abs_directory):
        bail("No directory named %s was found." % options.directory)


    #
    # Execute
    #

    if command == "export":
        action_export(abs_artwork_file_name, abs_directory)
    elif command == "create":
        abs_create_file_name = os.path.abspath(options.create_file_name)
        if os.path.exists(abs_create_file_name):
            bail("FAIL. The create file %s already exists -- don't want to overwrite it." % options.create_file_name)
        action_create(abs_artwork_file_name, abs_directory, abs_create_file_name)
            
if __name__ == "__main__":
    main(sys.argv)
    

    

########NEW FILE########
