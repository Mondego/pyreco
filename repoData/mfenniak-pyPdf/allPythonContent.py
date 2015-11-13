__FILENAME__ = filters
# vim: sw=4:expandtab:foldmethod=marker
#
# Copyright (c) 2006, Mathieu Fenniak
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# * The name of the author may not be used to endorse or promote products
# derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


"""
Implementation of stream filters for PDF.
"""
__author__ = "Mathieu Fenniak"
__author_email__ = "biziqe@mathieu.fenniak.net"

from utils import PdfReadError
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

try:
    import zlib
    def decompress(data):
        return zlib.decompress(data)
    def compress(data):
        return zlib.compress(data)
except ImportError:
    # Unable to import zlib.  Attempt to use the System.IO.Compression
    # library from the .NET framework. (IronPython only)
    import System
    from System import IO, Collections, Array
    def _string_to_bytearr(buf):
        retval = Array.CreateInstance(System.Byte, len(buf))
        for i in range(len(buf)):
            retval[i] = ord(buf[i])
        return retval
    def _bytearr_to_string(bytes):
        retval = ""
        for i in range(bytes.Length):
            retval += chr(bytes[i])
        return retval
    def _read_bytes(stream):
        ms = IO.MemoryStream()
        buf = Array.CreateInstance(System.Byte, 2048)
        while True:
            bytes = stream.Read(buf, 0, buf.Length)
            if bytes == 0:
                break
            else:
                ms.Write(buf, 0, bytes)
        retval = ms.ToArray()
        ms.Close()
        return retval
    def decompress(data):
        bytes = _string_to_bytearr(data)
        ms = IO.MemoryStream()
        ms.Write(bytes, 0, bytes.Length)
        ms.Position = 0  # fseek 0
        gz = IO.Compression.DeflateStream(ms, IO.Compression.CompressionMode.Decompress)
        bytes = _read_bytes(gz)
        retval = _bytearr_to_string(bytes)
        gz.Close()
        return retval
    def compress(data):
        bytes = _string_to_bytearr(data)
        ms = IO.MemoryStream()
        gz = IO.Compression.DeflateStream(ms, IO.Compression.CompressionMode.Compress, True)
        gz.Write(bytes, 0, bytes.Length)
        gz.Close()
        ms.Position = 0 # fseek 0
        bytes = ms.ToArray()
        retval = _bytearr_to_string(bytes)
        ms.Close()
        return retval


class FlateDecode(object):
    def decode(data, decodeParms):
        data = decompress(data)
        predictor = 1
        if decodeParms:
            predictor = decodeParms.get("/Predictor", 1)
        # predictor 1 == no predictor
        if predictor != 1:
            columns = decodeParms["/Columns"]
            # PNG prediction:
            if predictor >= 10 and predictor <= 15:
                output = StringIO()
                # PNG prediction can vary from row to row
                rowlength = columns + 1
                assert len(data) % rowlength == 0
                prev_rowdata = (0,) * rowlength
                for row in xrange(len(data) / rowlength):
                    rowdata = [ord(x) for x in data[(row*rowlength):((row+1)*rowlength)]]
                    filterByte = rowdata[0]
                    if filterByte == 0:
                        pass
                    elif filterByte == 1:
                        for i in range(2, rowlength):
                            rowdata[i] = (rowdata[i] + rowdata[i-1]) % 256
                    elif filterByte == 2:
                        for i in range(1, rowlength):
                            rowdata[i] = (rowdata[i] + prev_rowdata[i]) % 256
                    else:
                        # unsupported PNG filter
                        raise PdfReadError("Unsupported PNG filter %r" % filterByte)
                    prev_rowdata = rowdata
                    output.write(''.join([chr(x) for x in rowdata[1:]]))
                data = output.getvalue()
            else:
                # unsupported predictor
                raise PdfReadError("Unsupported flatedecode predictor %r" % predictor)
        return data
    decode = staticmethod(decode)

    def encode(data):
        return compress(data)
    encode = staticmethod(encode)

class ASCIIHexDecode(object):
    def decode(data, decodeParms=None):
        retval = ""
        char = ""
        x = 0
        while True:
            c = data[x]
            if c == ">":
                break
            elif c.isspace():
                x += 1
                continue
            char += c
            if len(char) == 2:
                retval += chr(int(char, base=16))
                char = ""
            x += 1
        assert char == ""
        return retval
    decode = staticmethod(decode)

class ASCII85Decode(object):
    def decode(data, decodeParms=None):
        retval = ""
        group = []
        x = 0
        hitEod = False
        # remove all whitespace from data
        data = [y for y in data if not (y in ' \n\r\t')]
        while not hitEod:
            c = data[x]
            if len(retval) == 0 and c == "<" and data[x+1] == "~":
                x += 2
                continue
            #elif c.isspace():
            #    x += 1
            #    continue
            elif c == 'z':
                assert len(group) == 0
                retval += '\x00\x00\x00\x00'
                continue
            elif c == "~" and data[x+1] == ">":
                if len(group) != 0:
                    # cannot have a final group of just 1 char
                    assert len(group) > 1
                    cnt = len(group) - 1
                    group += [ 85, 85, 85 ]
                    hitEod = cnt
                else:
                    break
            else:
                c = ord(c) - 33
                assert c >= 0 and c < 85
                group += [ c ]
            if len(group) >= 5:
                b = group[0] * (85**4) + \
                    group[1] * (85**3) + \
                    group[2] * (85**2) + \
                    group[3] * 85 + \
                    group[4]
                assert b < (2**32 - 1)
                c4 = chr((b >> 0) % 256)
                c3 = chr((b >> 8) % 256)
                c2 = chr((b >> 16) % 256)
                c1 = chr(b >> 24)
                retval += (c1 + c2 + c3 + c4)
                if hitEod:
                    retval = retval[:-4+hitEod]
                group = []
            x += 1
        return retval
    decode = staticmethod(decode)

def decodeStreamData(stream):
    from generic import NameObject
    filters = stream.get("/Filter", ())
    if len(filters) and not isinstance(filters[0], NameObject):
        # we have a single filter instance
        filters = (filters,)
    data = stream._data
    for filterType in filters:
        if filterType == "/FlateDecode":
            data = FlateDecode.decode(data, stream.get("/DecodeParms"))
        elif filterType == "/ASCIIHexDecode":
            data = ASCIIHexDecode.decode(data)
        elif filterType == "/ASCII85Decode":
            data = ASCII85Decode.decode(data)
        elif filterType == "/Crypt":
            decodeParams = stream.get("/DecodeParams", {})
            if "/Name" not in decodeParams and "/Type" not in decodeParams:
                pass
            else:
                raise NotImplementedError("/Crypt filter with /Name or /Type not supported yet")
        else:
            # unsupported filter
            raise NotImplementedError("unsupported filter %s" % filterType)
    return data

if __name__ == "__main__":
    assert "abc" == ASCIIHexDecode.decode('61\n626\n3>')

    ascii85Test = """
     <~9jqo^BlbD-BleB1DJ+*+F(f,q/0JhKF<GL>Cj@.4Gp$d7F!,L7@<6@)/0JDEF<G%<+EV:2F!,
     O<DJ+*.@<*K0@<6L(Df-\\0Ec5e;DffZ(EZee.Bl.9pF"AGXBPCsi+DGm>@3BB/F*&OCAfu2/AKY
     i(DIb:@FD,*)+C]U=@3BN#EcYf8ATD3s@q?d$AftVqCh[NqF<G:8+EV:.+Cf>-FD5W8ARlolDIa
     l(DId<j@<?3r@:F%a+D58'ATD4$Bl@l3De:,-DJs`8ARoFb/0JMK@qB4^F!,R<AKZ&-DfTqBG%G
     >uD.RTpAKYo'+CT/5+Cei#DII?(E,9)oF*2M7/c~>
    """
    ascii85_originalText="Man is distinguished, not only by his reason, but by this singular passion from other animals, which is a lust of the mind, that by a perseverance of delight in the continued and indefatigable generation of knowledge, exceeds the short vehemence of any carnal pleasure."
    assert ASCII85Decode.decode(ascii85Test) == ascii85_originalText


########NEW FILE########
__FILENAME__ = generic
# vim: sw=4:expandtab:foldmethod=marker
#
# Copyright (c) 2006, Mathieu Fenniak
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# * The name of the author may not be used to endorse or promote products
# derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


"""
Implementation of generic PDF objects (dictionary, number, string, and so on)
"""
__author__ = "Mathieu Fenniak"
__author_email__ = "biziqe@mathieu.fenniak.net"

import re
from utils import readNonWhitespace, RC4_encrypt
import filters
import utils
import decimal
import codecs

def readObject(stream, pdf):
    tok = stream.read(1)
    stream.seek(-1, 1) # reset to start
    if tok == 't' or tok == 'f':
        # boolean object
        return BooleanObject.readFromStream(stream)
    elif tok == '(':
        # string object
        return readStringFromStream(stream)
    elif tok == '/':
        # name object
        return NameObject.readFromStream(stream)
    elif tok == '[':
        # array object
        return ArrayObject.readFromStream(stream, pdf)
    elif tok == 'n':
        # null object
        return NullObject.readFromStream(stream)
    elif tok == '<':
        # hexadecimal string OR dictionary
        peek = stream.read(2)
        stream.seek(-2, 1) # reset to start
        if peek == '<<':
            return DictionaryObject.readFromStream(stream, pdf)
        else:
            return readHexStringFromStream(stream)
    elif tok == '%':
        # comment
        while tok not in ('\r', '\n'):
            tok = stream.read(1)
        tok = readNonWhitespace(stream)
        stream.seek(-1, 1)
        return readObject(stream, pdf)
    else:
        # number object OR indirect reference
        if tok == '+' or tok == '-':
            # number
            return NumberObject.readFromStream(stream)
        peek = stream.read(20)
        stream.seek(-len(peek), 1) # reset to start
        if re.match(r"(\d+)\s(\d+)\sR[^a-zA-Z]", peek) != None:
            return IndirectObject.readFromStream(stream, pdf)
        else:
            return NumberObject.readFromStream(stream)

class PdfObject(object):
    def getObject(self):
        """Resolves indirect references."""
        return self


class NullObject(PdfObject):
    def writeToStream(self, stream, encryption_key):
        stream.write("null")

    def readFromStream(stream):
        nulltxt = stream.read(4)
        if nulltxt != "null":
            raise utils.PdfReadError, "error reading null object"
        return NullObject()
    readFromStream = staticmethod(readFromStream)


class BooleanObject(PdfObject):
    def __init__(self, value):
        self.value = value

    def writeToStream(self, stream, encryption_key):
        if self.value:
            stream.write("true")
        else:
            stream.write("false")

    def readFromStream(stream):
        word = stream.read(4)
        if word == "true":
            return BooleanObject(True)
        elif word == "fals":
            stream.read(1)
            return BooleanObject(False)
        assert False
    readFromStream = staticmethod(readFromStream)


class ArrayObject(list, PdfObject):
    def writeToStream(self, stream, encryption_key):
        stream.write("[")
        for data in self:
            stream.write(" ")
            data.writeToStream(stream, encryption_key)
        stream.write(" ]")

    def readFromStream(stream, pdf):
        arr = ArrayObject()
        tmp = stream.read(1)
        if tmp != "[":
            raise utils.PdfReadError, "error reading array"
        while True:
            # skip leading whitespace
            tok = stream.read(1)
            while tok.isspace():
                tok = stream.read(1)
            stream.seek(-1, 1)
            # check for array ending
            peekahead = stream.read(1)
            if peekahead == "]":
                break
            stream.seek(-1, 1)
            # read and append obj
            arr.append(readObject(stream, pdf))
        return arr
    readFromStream = staticmethod(readFromStream)


class IndirectObject(PdfObject):
    def __init__(self, idnum, generation, pdf):
        self.idnum = idnum
        self.generation = generation
        self.pdf = pdf

    def getObject(self):
        return self.pdf.getObject(self).getObject()

    def __repr__(self):
        return "IndirectObject(%r, %r)" % (self.idnum, self.generation)

    def __eq__(self, other):
        return (
            other != None and
            isinstance(other, IndirectObject) and
            self.idnum == other.idnum and
            self.generation == other.generation and
            self.pdf is other.pdf
            )

    def __ne__(self, other):
        return not self.__eq__(other)

    def writeToStream(self, stream, encryption_key):
        stream.write("%s %s R" % (self.idnum, self.generation))

    def readFromStream(stream, pdf):
        idnum = ""
        while True:
            tok = stream.read(1)
            if tok.isspace():
                break
            idnum += tok
        generation = ""
        while True:
            tok = stream.read(1)
            if tok.isspace():
                break
            generation += tok
        r = stream.read(1)
        if r != "R":
            raise utils.PdfReadError("error reading indirect object reference")
        return IndirectObject(int(idnum), int(generation), pdf)
    readFromStream = staticmethod(readFromStream)


class FloatObject(decimal.Decimal, PdfObject):
    def __new__(cls, value="0", context=None):
        return decimal.Decimal.__new__(cls, str(value), context)
    def __repr__(self):
        if self == self.to_integral():
            return str(self.quantize(decimal.Decimal(1)))
        else:
            # XXX: this adds useless extraneous zeros.
            return "%.5f" % self
    def writeToStream(self, stream, encryption_key):
        stream.write(repr(self))


class NumberObject(int, PdfObject):
    def __init__(self, value):
        int.__init__(value)

    def writeToStream(self, stream, encryption_key):
        stream.write(repr(self))

    def readFromStream(stream):
        name = ""
        while True:
            tok = stream.read(1)
            if tok != '+' and tok != '-' and tok != '.' and not tok.isdigit():
                stream.seek(-1, 1)
                break
            name += tok
        if name.find(".") != -1:
            return FloatObject(name)
        else:
            return NumberObject(name)
    readFromStream = staticmethod(readFromStream)


##
# Given a string (either a "str" or "unicode"), create a ByteStringObject or a
# TextStringObject to represent the string.
def createStringObject(string):
    if isinstance(string, unicode):
        return TextStringObject(string)
    elif isinstance(string, str):
        if string.startswith(codecs.BOM_UTF16_BE):
            retval = TextStringObject(string.decode("utf-16"))
            retval.autodetect_utf16 = True
            return retval
        else:
            # This is probably a big performance hit here, but we need to
            # convert string objects into the text/unicode-aware version if
            # possible... and the only way to check if that's possible is
            # to try.  Some strings are strings, some are just byte arrays.
            try:
                retval = TextStringObject(decode_pdfdocencoding(string))
                retval.autodetect_pdfdocencoding = True
                return retval
            except UnicodeDecodeError:
                return ByteStringObject(string)
    else:
        raise TypeError("createStringObject should have str or unicode arg")


def readHexStringFromStream(stream):
    stream.read(1)
    txt = ""
    x = ""
    while True:
        tok = readNonWhitespace(stream)
        if tok == ">":
            break
        x += tok
        if len(x) == 2:
            txt += chr(int(x, base=16))
            x = ""
    if len(x) == 1:
        x += "0"
    if len(x) == 2:
        txt += chr(int(x, base=16))
    return createStringObject(txt)


def readStringFromStream(stream):
    tok = stream.read(1)
    parens = 1
    txt = ""
    while True:
        tok = stream.read(1)
        if tok == "(":
            parens += 1
        elif tok == ")":
            parens -= 1
            if parens == 0:
                break
        elif tok == "\\":
            tok = stream.read(1)
            if tok == "n":
                tok = "\n"
            elif tok == "r":
                tok = "\r"
            elif tok == "t":
                tok = "\t"
            elif tok == "b":
                tok = "\b"
            elif tok == "f":
                tok = "\f"
            elif tok == "(":
                tok = "("
            elif tok == ")":
                tok = ")"
            elif tok == "\\":
                tok = "\\"
            elif tok.isdigit():
                # "The number ddd may consist of one, two, or three
                # octal digits; high-order overflow shall be ignored.
                # Three octal digits shall be used, with leading zeros
                # as needed, if the next character of the string is also
                # a digit." (PDF reference 7.3.4.2, p 16)
                for i in range(2):
                    ntok = stream.read(1)
                    if ntok.isdigit():
                        tok += ntok
                    else:
                        break
                tok = chr(int(tok, base=8))
            elif tok in "\n\r":
                # This case is  hit when a backslash followed by a line
                # break occurs.  If it's a multi-char EOL, consume the
                # second character:
                tok = stream.read(1)
                if not tok in "\n\r":
                    stream.seek(-1, 1)
                # Then don't add anything to the actual string, since this
                # line break was escaped:
                tok = ''
            else:
                raise utils.PdfReadError("Unexpected escaped string")
        txt += tok
    return createStringObject(txt)


##
# Represents a string object where the text encoding could not be determined.
# This occurs quite often, as the PDF spec doesn't provide an alternate way to
# represent strings -- for example, the encryption data stored in files (like
# /O) is clearly not text, but is still stored in a "String" object.
class ByteStringObject(str, PdfObject):

    ##
    # For compatibility with TextStringObject.original_bytes.  This method
    # returns self.
    original_bytes = property(lambda self: self)

    def writeToStream(self, stream, encryption_key):
        bytearr = self
        if encryption_key:
            bytearr = RC4_encrypt(encryption_key, bytearr)
        stream.write("<")
        stream.write(bytearr.encode("hex"))
        stream.write(">")


##
# Represents a string object that has been decoded into a real unicode string.
# If read from a PDF document, this string appeared to match the
# PDFDocEncoding, or contained a UTF-16BE BOM mark to cause UTF-16 decoding to
# occur.
class TextStringObject(unicode, PdfObject):
    autodetect_pdfdocencoding = False
    autodetect_utf16 = False

    ##
    # It is occasionally possible that a text string object gets created where
    # a byte string object was expected due to the autodetection mechanism --
    # if that occurs, this "original_bytes" property can be used to
    # back-calculate what the original encoded bytes were.
    original_bytes = property(lambda self: self.get_original_bytes())

    def get_original_bytes(self):
        # We're a text string object, but the library is trying to get our raw
        # bytes.  This can happen if we auto-detected this string as text, but
        # we were wrong.  It's pretty common.  Return the original bytes that
        # would have been used to create this object, based upon the autodetect
        # method.
        if self.autodetect_utf16:
            return codecs.BOM_UTF16_BE + self.encode("utf-16be")
        elif self.autodetect_pdfdocencoding:
            return encode_pdfdocencoding(self)
        else:
            raise Exception("no information about original bytes")

    def writeToStream(self, stream, encryption_key):
        # Try to write the string out as a PDFDocEncoding encoded string.  It's
        # nicer to look at in the PDF file.  Sadly, we take a performance hit
        # here for trying...
        try:
            bytearr = encode_pdfdocencoding(self)
        except UnicodeEncodeError:
            bytearr = codecs.BOM_UTF16_BE + self.encode("utf-16be")
        if encryption_key:
            bytearr = RC4_encrypt(encryption_key, bytearr)
            obj = ByteStringObject(bytearr)
            obj.writeToStream(stream, None)
        else:
            stream.write("(")
            for c in bytearr:
                if not c.isalnum() and c != ' ':
                    stream.write("\\%03o" % ord(c))
                else:
                    stream.write(c)
            stream.write(")")


class NameObject(str, PdfObject):
    delimiterCharacters = "(", ")", "<", ">", "[", "]", "{", "}", "/", "%"

    def __init__(self, data):
        str.__init__(data)

    def writeToStream(self, stream, encryption_key):
        stream.write(self)

    def readFromStream(stream):
        name = stream.read(1)
        if name != "/":
            raise utils.PdfReadError, "name read error"
        while True:
            tok = stream.read(1)
            if tok.isspace() or tok in NameObject.delimiterCharacters:
                stream.seek(-1, 1)
                break
            name += tok
        return NameObject(name)
    readFromStream = staticmethod(readFromStream)


class DictionaryObject(dict, PdfObject):

    def __init__(self, *args, **kwargs):
        if len(args) == 0:
            self.update(kwargs)
        elif len(args) == 1:
            arr = args[0]
            # If we're passed a list/tuple, make a dict out of it
            if not hasattr(arr, "iteritems"):
                newarr = {}
                for k, v in arr:
                    newarr[k] = v
                arr = newarr
            self.update(arr)
        else:
            raise TypeError("dict expected at most 1 argument, got 3")

    def update(self, arr):
        # note, a ValueError halfway through copying values
        # will leave half the values in this dict.
        for k, v in arr.iteritems():
            self.__setitem__(k, v)

    def raw_get(self, key):
        return dict.__getitem__(self, key)

    def __setitem__(self, key, value):
        if not isinstance(key, PdfObject):
            raise ValueError("key must be PdfObject")
        if not isinstance(value, PdfObject):
            raise ValueError("value must be PdfObject")
        return dict.__setitem__(self, key, value)

    def setdefault(self, key, value=None):
        if not isinstance(key, PdfObject):
            raise ValueError("key must be PdfObject")
        if not isinstance(value, PdfObject):
            raise ValueError("value must be PdfObject")
        return dict.setdefault(self, key, value)

    def __getitem__(self, key):
        return dict.__getitem__(self, key).getObject()

    ##
    # Retrieves XMP (Extensible Metadata Platform) data relevant to the
    # this object, if available.
    # <p>
    # Stability: Added in v1.12, will exist for all future v1.x releases.
    # @return Returns a {@link #xmp.XmpInformation XmlInformation} instance
    # that can be used to access XMP metadata from the document.  Can also
    # return None if no metadata was found on the document root.
    def getXmpMetadata(self):
        metadata = self.get("/Metadata", None)
        if metadata == None:
            return None
        metadata = metadata.getObject()
        import xmp
        if not isinstance(metadata, xmp.XmpInformation):
            metadata = xmp.XmpInformation(metadata)
            self[NameObject("/Metadata")] = metadata
        return metadata

    ##
    # Read-only property that accesses the {@link
    # #DictionaryObject.getXmpData getXmpData} function.
    # <p>
    # Stability: Added in v1.12, will exist for all future v1.x releases.
    xmpMetadata = property(lambda self: self.getXmpMetadata(), None, None)

    def writeToStream(self, stream, encryption_key):
        stream.write("<<\n")
        for key, value in self.items():
            key.writeToStream(stream, encryption_key)
            stream.write(" ")
            value.writeToStream(stream, encryption_key)
            stream.write("\n")
        stream.write(">>")

    def readFromStream(stream, pdf):
        tmp = stream.read(2)
        if tmp != "<<":
            raise utils.PdfReadError, "dictionary read error"
        data = {}
        while True:
            tok = readNonWhitespace(stream)
            if tok == ">":
                stream.read(1)
                break
            stream.seek(-1, 1)
            key = readObject(stream, pdf)
            tok = readNonWhitespace(stream)
            stream.seek(-1, 1)
            value = readObject(stream, pdf)
            if data.has_key(key):
                # multiple definitions of key not permitted
                raise utils.PdfReadError, "multiple definitions in dictionary"
            data[key] = value
        pos = stream.tell()
        s = readNonWhitespace(stream)
        if s == 's' and stream.read(5) == 'tream':
            eol = stream.read(1)
            # odd PDF file output has spaces after 'stream' keyword but before EOL.
            # patch provided by Danial Sandler
            while eol == ' ':
                eol = stream.read(1)
            assert eol in ("\n", "\r")
            if eol == "\r":
                # read \n after
                stream.read(1)
            # this is a stream object, not a dictionary
            assert data.has_key("/Length")
            length = data["/Length"]
            if isinstance(length, IndirectObject):
                t = stream.tell()
                length = pdf.getObject(length)
                stream.seek(t, 0)
            data["__streamdata__"] = stream.read(length)
            e = readNonWhitespace(stream)
            ndstream = stream.read(8)
            if (e + ndstream) != "endstream":
                # (sigh) - the odd PDF file has a length that is too long, so
                # we need to read backwards to find the "endstream" ending.
                # ReportLab (unknown version) generates files with this bug,
                # and Python users into PDF files tend to be our audience.
                # we need to do this to correct the streamdata and chop off
                # an extra character.
                pos = stream.tell()
                stream.seek(-10, 1)
                end = stream.read(9)
                if end == "endstream":
                    # we found it by looking back one character further.
                    data["__streamdata__"] = data["__streamdata__"][:-1]
                else:
                    stream.seek(pos, 0)
                    raise utils.PdfReadError, "Unable to find 'endstream' marker after stream."
        else:
            stream.seek(pos, 0)
        if data.has_key("__streamdata__"):
            return StreamObject.initializeFromDictionary(data)
        else:
            retval = DictionaryObject()
            retval.update(data)
            return retval
    readFromStream = staticmethod(readFromStream)


class StreamObject(DictionaryObject):
    def __init__(self):
        self._data = None
        self.decodedSelf = None

    def writeToStream(self, stream, encryption_key):
        self[NameObject("/Length")] = NumberObject(len(self._data))
        DictionaryObject.writeToStream(self, stream, encryption_key)
        del self["/Length"]
        stream.write("\nstream\n")
        data = self._data
        if encryption_key:
            data = RC4_encrypt(encryption_key, data)
        stream.write(data)
        stream.write("\nendstream")

    def initializeFromDictionary(data):
        if data.has_key("/Filter"):
            retval = EncodedStreamObject()
        else:
            retval = DecodedStreamObject()
        retval._data = data["__streamdata__"]
        del data["__streamdata__"]
        del data["/Length"]
        retval.update(data)
        return retval
    initializeFromDictionary = staticmethod(initializeFromDictionary)

    def flateEncode(self):
        if self.has_key("/Filter"):
            f = self["/Filter"]
            if isinstance(f, ArrayObject):
                f.insert(0, NameObject("/FlateDecode"))
            else:
                newf = ArrayObject()
                newf.append(NameObject("/FlateDecode"))
                newf.append(f)
                f = newf
        else:
            f = NameObject("/FlateDecode")
        retval = EncodedStreamObject()
        retval[NameObject("/Filter")] = f
        retval._data = filters.FlateDecode.encode(self._data)
        return retval


class DecodedStreamObject(StreamObject):
    def getData(self):
        return self._data

    def setData(self, data):
        self._data = data


class EncodedStreamObject(StreamObject):
    def __init__(self):
        self.decodedSelf = None

    def getData(self):
        if self.decodedSelf:
            # cached version of decoded object
            return self.decodedSelf.getData()
        else:
            # create decoded object
            decoded = DecodedStreamObject()
            decoded._data = filters.decodeStreamData(self)
            for key, value in self.items():
                if not key in ("/Length", "/Filter", "/DecodeParms"):
                    decoded[key] = value
            self.decodedSelf = decoded
            return decoded._data

    def setData(self, data):
        raise utils.PdfReadError, "Creating EncodedStreamObject is not currently supported"


class RectangleObject(ArrayObject):
    def __init__(self, arr):
        # must have four points
        assert len(arr) == 4
        # automatically convert arr[x] into NumberObject(arr[x]) if necessary
        ArrayObject.__init__(self, [self.ensureIsNumber(x) for x in arr])

    def ensureIsNumber(self, value):
        if not isinstance(value, (NumberObject, FloatObject)):
            value = FloatObject(value)
        return value

    def __repr__(self):
        return "RectangleObject(%s)" % repr(list(self))

    def getLowerLeft_x(self):
        return self[0]

    def getLowerLeft_y(self):
        return self[1]

    def getUpperRight_x(self):
        return self[2]

    def getUpperRight_y(self):
        return self[3]

    def getUpperLeft_x(self):
        return self.getLowerLeft_x()
    
    def getUpperLeft_y(self):
        return self.getUpperRight_y()

    def getLowerRight_x(self):
        return self.getUpperRight_x()

    def getLowerRight_y(self):
        return self.getLowerLeft_y()

    def getLowerLeft(self):
        return self.getLowerLeft_x(), self.getLowerLeft_y()

    def getLowerRight(self):
        return self.getLowerRight_x(), self.getLowerRight_y()

    def getUpperLeft(self):
        return self.getUpperLeft_x(), self.getUpperLeft_y()

    def getUpperRight(self):
        return self.getUpperRight_x(), self.getUpperRight_y()

    def setLowerLeft(self, value):
        self[0], self[1] = [self.ensureIsNumber(x) for x in value]

    def setLowerRight(self, value):
        self[2], self[1] = [self.ensureIsNumber(x) for x in value]

    def setUpperLeft(self, value):
        self[0], self[3] = [self.ensureIsNumber(x) for x in value]

    def setUpperRight(self, value):
        self[2], self[3] = [self.ensureIsNumber(x) for x in value]

    def getWidth(self):
        return self.getUpperRight_x() - self.getLowerLeft_x()

    def getHeight(self):
        return self.getUpperRight_y() - self.getLowerLeft_x()

    lowerLeft = property(getLowerLeft, setLowerLeft, None, None)
    lowerRight = property(getLowerRight, setLowerRight, None, None)
    upperLeft = property(getUpperLeft, setUpperLeft, None, None)
    upperRight = property(getUpperRight, setUpperRight, None, None)


def encode_pdfdocencoding(unicode_string):
    retval = ''
    for c in unicode_string:
        try:
            retval += chr(_pdfDocEncoding_rev[c])
        except KeyError:
            raise UnicodeEncodeError("pdfdocencoding", c, -1, -1,
                    "does not exist in translation table")
    return retval

def decode_pdfdocencoding(byte_array):
    retval = u''
    for b in byte_array:
        c = _pdfDocEncoding[ord(b)]
        if c == u'\u0000':
            raise UnicodeDecodeError("pdfdocencoding", b, -1, -1,
                    "does not exist in translation table")
        retval += c
    return retval

_pdfDocEncoding = (
  u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000',
  u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000',
  u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000', u'\u0000',
  u'\u02d8', u'\u02c7', u'\u02c6', u'\u02d9', u'\u02dd', u'\u02db', u'\u02da', u'\u02dc',
  u'\u0020', u'\u0021', u'\u0022', u'\u0023', u'\u0024', u'\u0025', u'\u0026', u'\u0027',
  u'\u0028', u'\u0029', u'\u002a', u'\u002b', u'\u002c', u'\u002d', u'\u002e', u'\u002f',
  u'\u0030', u'\u0031', u'\u0032', u'\u0033', u'\u0034', u'\u0035', u'\u0036', u'\u0037',
  u'\u0038', u'\u0039', u'\u003a', u'\u003b', u'\u003c', u'\u003d', u'\u003e', u'\u003f',
  u'\u0040', u'\u0041', u'\u0042', u'\u0043', u'\u0044', u'\u0045', u'\u0046', u'\u0047',
  u'\u0048', u'\u0049', u'\u004a', u'\u004b', u'\u004c', u'\u004d', u'\u004e', u'\u004f',
  u'\u0050', u'\u0051', u'\u0052', u'\u0053', u'\u0054', u'\u0055', u'\u0056', u'\u0057',
  u'\u0058', u'\u0059', u'\u005a', u'\u005b', u'\u005c', u'\u005d', u'\u005e', u'\u005f',
  u'\u0060', u'\u0061', u'\u0062', u'\u0063', u'\u0064', u'\u0065', u'\u0066', u'\u0067',
  u'\u0068', u'\u0069', u'\u006a', u'\u006b', u'\u006c', u'\u006d', u'\u006e', u'\u006f',
  u'\u0070', u'\u0071', u'\u0072', u'\u0073', u'\u0074', u'\u0075', u'\u0076', u'\u0077',
  u'\u0078', u'\u0079', u'\u007a', u'\u007b', u'\u007c', u'\u007d', u'\u007e', u'\u0000',
  u'\u2022', u'\u2020', u'\u2021', u'\u2026', u'\u2014', u'\u2013', u'\u0192', u'\u2044',
  u'\u2039', u'\u203a', u'\u2212', u'\u2030', u'\u201e', u'\u201c', u'\u201d', u'\u2018',
  u'\u2019', u'\u201a', u'\u2122', u'\ufb01', u'\ufb02', u'\u0141', u'\u0152', u'\u0160',
  u'\u0178', u'\u017d', u'\u0131', u'\u0142', u'\u0153', u'\u0161', u'\u017e', u'\u0000',
  u'\u20ac', u'\u00a1', u'\u00a2', u'\u00a3', u'\u00a4', u'\u00a5', u'\u00a6', u'\u00a7',
  u'\u00a8', u'\u00a9', u'\u00aa', u'\u00ab', u'\u00ac', u'\u0000', u'\u00ae', u'\u00af',
  u'\u00b0', u'\u00b1', u'\u00b2', u'\u00b3', u'\u00b4', u'\u00b5', u'\u00b6', u'\u00b7',
  u'\u00b8', u'\u00b9', u'\u00ba', u'\u00bb', u'\u00bc', u'\u00bd', u'\u00be', u'\u00bf',
  u'\u00c0', u'\u00c1', u'\u00c2', u'\u00c3', u'\u00c4', u'\u00c5', u'\u00c6', u'\u00c7',
  u'\u00c8', u'\u00c9', u'\u00ca', u'\u00cb', u'\u00cc', u'\u00cd', u'\u00ce', u'\u00cf',
  u'\u00d0', u'\u00d1', u'\u00d2', u'\u00d3', u'\u00d4', u'\u00d5', u'\u00d6', u'\u00d7',
  u'\u00d8', u'\u00d9', u'\u00da', u'\u00db', u'\u00dc', u'\u00dd', u'\u00de', u'\u00df',
  u'\u00e0', u'\u00e1', u'\u00e2', u'\u00e3', u'\u00e4', u'\u00e5', u'\u00e6', u'\u00e7',
  u'\u00e8', u'\u00e9', u'\u00ea', u'\u00eb', u'\u00ec', u'\u00ed', u'\u00ee', u'\u00ef',
  u'\u00f0', u'\u00f1', u'\u00f2', u'\u00f3', u'\u00f4', u'\u00f5', u'\u00f6', u'\u00f7',
  u'\u00f8', u'\u00f9', u'\u00fa', u'\u00fb', u'\u00fc', u'\u00fd', u'\u00fe', u'\u00ff'
)

assert len(_pdfDocEncoding) == 256

_pdfDocEncoding_rev = {}
for i in xrange(256):
    char = _pdfDocEncoding[i]
    if char == u"\u0000":
        continue
    assert char not in _pdfDocEncoding_rev
    _pdfDocEncoding_rev[char] = i


########NEW FILE########
__FILENAME__ = pdf
# -*- coding: utf-8 -*-
#
# vim: sw=4:expandtab:foldmethod=marker
#
# Copyright (c) 2006, Mathieu Fenniak
# Copyright (c) 2007, Ashish Kulkarni <kulkarni.ashish@gmail.com>
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# * The name of the author may not be used to endorse or promote products
# derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


"""
A pure-Python PDF library with very minimal capabilities.  It was designed to
be able to split and merge PDF files by page, and that's about all it can do.
It may be a solid base for future PDF file work in Python.
"""
__author__ = "Mathieu Fenniak"
__author_email__ = "biziqe@mathieu.fenniak.net"

import math
import struct
from sys import version_info
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import filters
import utils
import warnings
from generic import *
from utils import readNonWhitespace, readUntilWhitespace, ConvertFunctionsToVirtualList

if version_info < ( 2, 4 ):
   from sets import ImmutableSet as frozenset

if version_info < ( 2, 5 ):
    from md5 import md5
else:
    from hashlib import md5

##
# This class supports writing PDF files out, given pages produced by another
# class (typically {@link #PdfFileReader PdfFileReader}).
class PdfFileWriter(object):
    def __init__(self):
        self._header = "%PDF-1.3"
        self._objects = []  # array of indirect objects

        # The root of our page tree node.
        pages = DictionaryObject()
        pages.update({
                NameObject("/Type"): NameObject("/Pages"),
                NameObject("/Count"): NumberObject(0),
                NameObject("/Kids"): ArrayObject(),
                })
        self._pages = self._addObject(pages)

        # info object
        info = DictionaryObject()
        info.update({
                NameObject("/Producer"): createStringObject(u"Python PDF Library - http://pybrary.net/pyPdf/")
                })
        self._info = self._addObject(info)

        # root object
        root = DictionaryObject()
        root.update({
            NameObject("/Type"): NameObject("/Catalog"),
            NameObject("/Pages"): self._pages,
            })
        self._root = self._addObject(root)

    def _addObject(self, obj):
        self._objects.append(obj)
        return IndirectObject(len(self._objects), 0, self)

    def getObject(self, ido):
        if ido.pdf != self:
            raise ValueError("pdf must be self")
        return self._objects[ido.idnum - 1]

    ##
    # Common method for inserting or adding a page to this PDF file.
    #
    # @param page The page to add to the document.  This argument should be
    #             an instance of {@link #PageObject PageObject}.
    # @param action The function which will insert the page in the dictionnary.
    #               Takes: page list, page to add.
    def _addPage(self, page, action):
        assert page["/Type"] == "/Page"
        page[NameObject("/Parent")] = self._pages
        page = self._addObject(page)
        pages = self.getObject(self._pages)
        action(pages["/Kids"], page)
        pages[NameObject("/Count")] = NumberObject(pages["/Count"] + 1)

    ##
    # Adds a page to this PDF file.  The page is usually acquired from a
    # {@link #PdfFileReader PdfFileReader} instance.
    # <p>
    # Stability: Added in v1.0, will exist for all v1.x releases.
    #
    # @param page The page to add to the document.  This argument should be
    #             an instance of {@link #PageObject PageObject}.
    def addPage(self, page):
        self._addPage(page, list.append)

    ##
    # Insert a page in this PDF file.  The page is usually acquired from a
    # {@link #PdfFileReader PdfFileReader} instance.
    #
    # @param page The page to add to the document.  This argument should be
    #             an instance of {@link #PageObject PageObject}.
    # @param index Position at which the page will be inserted.
    def insertPage(self, page, index=0):
        self._addPage(page, lambda l, p: l.insert(index, p))

    ##
    # Retrieves a page by number from this PDF file.
    # @return Returns a {@link #PageObject PageObject} instance.
    def getPage(self, pageNumber):
        pages = self.getObject(self._pages)
        # XXX: crude hack
        return pages["/Kids"][pageNumber].getObject()

    ##
    # Return the number of pages.
    # @return The number of pages.
    def getNumPages(self):
        pages = self.getObject(self._pages)
        return int(pages[NameObject("/Count")])

    ##
    # Append a blank page to this PDF file and returns it. If no page size
    # is specified, use the size of the last page; throw
    # PageSizeNotDefinedError if it doesn't exist.
    # @param width The width of the new page expressed in default user
    # space units.
    # @param height The height of the new page expressed in default user
    # space units.
    def addBlankPage(self, width=None, height=None):
        page = PageObject.createBlankPage(self, width, height)
        self.addPage(page)
        return page

    ##
    # Insert a blank page to this PDF file and returns it. If no page size
    # is specified, use the size of the page in the given index; throw
    # PageSizeNotDefinedError if it doesn't exist.
    # @param width  The width of the new page expressed in default user
    #               space units.
    # @param height The height of the new page expressed in default user
    #               space units.
    # @param index  Position to add the page.
    def insertBlankPage(self, width=None, height=None, index=0):
        if width is None or height is None and \
                (self.getNumPages() - 1) >= index:
            oldpage = self.getPage(index)
            width = oldpage.mediaBox.getWidth()
            height = oldpage.mediaBox.getHeight()
        page = PageObject.createBlankPage(self, width, height)
        self.insertPage(page, index)
        return page

    ##
    # Encrypt this PDF file with the PDF Standard encryption handler.
    # @param user_pwd The "user password", which allows for opening and reading
    # the PDF file with the restrictions provided.
    # @param owner_pwd The "owner password", which allows for opening the PDF
    # files without any restrictions.  By default, the owner password is the
    # same as the user password.
    # @param use_128bit Boolean argument as to whether to use 128bit
    # encryption.  When false, 40bit encryption will be used.  By default, this
    # flag is on.
    def encrypt(self, user_pwd, owner_pwd = None, use_128bit = True):
        import time, random
        if owner_pwd == None:
            owner_pwd = user_pwd
        if use_128bit:
            V = 2
            rev = 3
            keylen = 128 / 8
        else:
            V = 1
            rev = 2
            keylen = 40 / 8
        # permit everything:
        P = -1
        O = ByteStringObject(_alg33(owner_pwd, user_pwd, rev, keylen))
        ID_1 = md5(repr(time.time())).digest()
        ID_2 = md5(repr(random.random())).digest()
        self._ID = ArrayObject((ByteStringObject(ID_1), ByteStringObject(ID_2)))
        if rev == 2:
            U, key = _alg34(user_pwd, O, P, ID_1)
        else:
            assert rev == 3
            U, key = _alg35(user_pwd, rev, keylen, O, P, ID_1, False)
        encrypt = DictionaryObject()
        encrypt[NameObject("/Filter")] = NameObject("/Standard")
        encrypt[NameObject("/V")] = NumberObject(V)
        if V == 2:
            encrypt[NameObject("/Length")] = NumberObject(keylen * 8)
        encrypt[NameObject("/R")] = NumberObject(rev)
        encrypt[NameObject("/O")] = ByteStringObject(O)
        encrypt[NameObject("/U")] = ByteStringObject(U)
        encrypt[NameObject("/P")] = NumberObject(P)
        self._encrypt = self._addObject(encrypt)
        self._encrypt_key = key

    ##
    # Writes the collection of pages added to this object out as a PDF file.
    # <p>
    # Stability: Added in v1.0, will exist for all v1.x releases.
    # @param stream An object to write the file to.  The object must support
    # the write method, and the tell method, similar to a file object.
    def write(self, stream):
        import struct

        externalReferenceMap = {}

        # PDF objects sometimes have circular references to their /Page objects
        # inside their object tree (for example, annotations).  Those will be
        # indirect references to objects that we've recreated in this PDF.  To
        # address this problem, PageObject's store their original object
        # reference number, and we add it to the external reference map before
        # we sweep for indirect references.  This forces self-page-referencing
        # trees to reference the correct new object location, rather than
        # copying in a new copy of the page object.
        for objIndex in xrange(len(self._objects)):
            obj = self._objects[objIndex]
            if isinstance(obj, PageObject) and obj.indirectRef != None:
                data = obj.indirectRef
                if not externalReferenceMap.has_key(data.pdf):
                    externalReferenceMap[data.pdf] = {}
                if not externalReferenceMap[data.pdf].has_key(data.generation):
                    externalReferenceMap[data.pdf][data.generation] = {}
                externalReferenceMap[data.pdf][data.generation][data.idnum] = IndirectObject(objIndex + 1, 0, self)

        self.stack = []
        self._sweepIndirectReferences(externalReferenceMap, self._root)
        del self.stack

        # Begin writing:
        object_positions = []
        stream.write(self._header + "\n")
        for i in range(len(self._objects)):
            idnum = (i + 1)
            obj = self._objects[i]
            object_positions.append(stream.tell())
            stream.write(str(idnum) + " 0 obj\n")
            key = None
            if hasattr(self, "_encrypt") and idnum != self._encrypt.idnum:
                pack1 = struct.pack("<i", i + 1)[:3]
                pack2 = struct.pack("<i", 0)[:2]
                key = self._encrypt_key + pack1 + pack2
                assert len(key) == (len(self._encrypt_key) + 5)
                md5_hash = md5(key).digest()
                key = md5_hash[:min(16, len(self._encrypt_key) + 5)]
            obj.writeToStream(stream, key)
            stream.write("\nendobj\n")

        # xref table
        xref_location = stream.tell()
        stream.write("xref\n")
        stream.write("0 %s\n" % (len(self._objects) + 1))
        stream.write("%010d %05d f \n" % (0, 65535))
        for offset in object_positions:
            stream.write("%010d %05d n \n" % (offset, 0))

        # trailer
        stream.write("trailer\n")
        trailer = DictionaryObject()
        trailer.update({
                NameObject("/Size"): NumberObject(len(self._objects) + 1),
                NameObject("/Root"): self._root,
                NameObject("/Info"): self._info,
                })
        if hasattr(self, "_ID"):
            trailer[NameObject("/ID")] = self._ID
        if hasattr(self, "_encrypt"):
            trailer[NameObject("/Encrypt")] = self._encrypt
        trailer.writeToStream(stream, None)
        
        # eof
        stream.write("\nstartxref\n%s\n%%%%EOF\n" % (xref_location))

    def _sweepIndirectReferences(self, externMap, data):
        if isinstance(data, DictionaryObject):
            for key, value in data.items():
                origvalue = value
                value = self._sweepIndirectReferences(externMap, value)
                if isinstance(value, StreamObject):
                    # a dictionary value is a stream.  streams must be indirect
                    # objects, so we need to change this value.
                    value = self._addObject(value)
                data[key] = value
            return data
        elif isinstance(data, ArrayObject):
            for i in range(len(data)):
                value = self._sweepIndirectReferences(externMap, data[i])
                if isinstance(value, StreamObject):
                    # an array value is a stream.  streams must be indirect
                    # objects, so we need to change this value
                    value = self._addObject(value)
                data[i] = value
            return data
        elif isinstance(data, IndirectObject):
            # internal indirect references are fine
            if data.pdf == self:
                if data.idnum in self.stack:
                    return data
                else:
                    self.stack.append(data.idnum)
                    realdata = self.getObject(data)
                    self._sweepIndirectReferences(externMap, realdata)
                    self.stack.pop()
                    return data
            else:
                newobj = externMap.get(data.pdf, {}).get(data.generation, {}).get(data.idnum, None)
                if newobj == None:
                    newobj = data.pdf.getObject(data)
                    self._objects.append(None) # placeholder
                    idnum = len(self._objects)
                    newobj_ido = IndirectObject(idnum, 0, self)
                    if not externMap.has_key(data.pdf):
                        externMap[data.pdf] = {}
                    if not externMap[data.pdf].has_key(data.generation):
                        externMap[data.pdf][data.generation] = {}
                    externMap[data.pdf][data.generation][data.idnum] = newobj_ido
                    newobj = self._sweepIndirectReferences(externMap, newobj)
                    self._objects[idnum-1] = newobj
                    return newobj_ido
                return newobj
        else:
            return data


##
# Initializes a PdfFileReader object.  This operation can take some time, as
# the PDF stream's cross-reference tables are read into memory.
# <p>
# Stability: Added in v1.0, will exist for all v1.x releases.
#
# @param stream An object that supports the standard read and seek methods
#               similar to a file object.
class PdfFileReader(object):
    def __init__(self, stream):
        self.flattenedPages = None
        self.resolvedObjects = {}
        self.read(stream)
        self.stream = stream
        self._override_encryption = False

    ##
    # Retrieves the PDF file's document information dictionary, if it exists.
    # Note that some PDF files use metadata streams instead of docinfo
    # dictionaries, and these metadata streams will not be accessed by this
    # function.
    # <p>
    # Stability: Added in v1.6, will exist for all future v1.x releases.
    # @return Returns a {@link #DocumentInformation DocumentInformation}
    #         instance, or None if none exists.
    def getDocumentInfo(self):
        if not self.trailer.has_key("/Info"):
            return None
        obj = self.trailer['/Info']
        retval = DocumentInformation()
        retval.update(obj)
        return retval

    ##
    # Read-only property that accesses the {@link
    # #PdfFileReader.getDocumentInfo getDocumentInfo} function.
    # <p>
    # Stability: Added in v1.7, will exist for all future v1.x releases.
    documentInfo = property(lambda self: self.getDocumentInfo(), None, None)

    ##
    # Retrieves XMP (Extensible Metadata Platform) data from the PDF document
    # root.
    # <p>
    # Stability: Added in v1.12, will exist for all future v1.x releases.
    # @return Returns a {@link #generic.XmpInformation XmlInformation}
    # instance that can be used to access XMP metadata from the document.
    # Can also return None if no metadata was found on the document root.
    def getXmpMetadata(self):
        try:
            self._override_encryption = True
            return self.trailer["/Root"].getXmpMetadata()
        finally:
            self._override_encryption = False

    ##
    # Read-only property that accesses the {@link #PdfFileReader.getXmpData
    # getXmpData} function.
    # <p>
    # Stability: Added in v1.12, will exist for all future v1.x releases.
    xmpMetadata = property(lambda self: self.getXmpMetadata(), None, None)

    ##
    # Calculates the number of pages in this PDF file.
    # <p>
    # Stability: Added in v1.0, will exist for all v1.x releases.
    # @return Returns an integer.
    def getNumPages(self):
        if self.flattenedPages == None:
            self._flatten()
        return len(self.flattenedPages)

    ##
    # Read-only property that accesses the {@link #PdfFileReader.getNumPages
    # getNumPages} function.
    # <p>
    # Stability: Added in v1.7, will exist for all future v1.x releases.
    numPages = property(lambda self: self.getNumPages(), None, None)

    ##
    # Retrieves a page by number from this PDF file.
    # <p>
    # Stability: Added in v1.0, will exist for all v1.x releases.
    # @return Returns a {@link #PageObject PageObject} instance.
    def getPage(self, pageNumber):
        ## ensure that we're not trying to access an encrypted PDF
        #assert not self.trailer.has_key("/Encrypt")
        if self.flattenedPages == None:
            self._flatten()
        return self.flattenedPages[pageNumber]

    ##
    # Read-only property that accesses the 
    # {@link #PdfFileReader.getNamedDestinations 
    # getNamedDestinations} function.
    # <p>
    # Stability: Added in v1.10, will exist for all future v1.x releases.
    namedDestinations = property(lambda self:
                                  self.getNamedDestinations(), None, None)

    ##
    # Retrieves the named destinations present in the document.
    # <p>
    # Stability: Added in v1.10, will exist for all future v1.x releases.
    # @return Returns a dict which maps names to {@link #Destination
    # destinations}.
    def getNamedDestinations(self, tree=None, retval=None):
        if retval == None:
            retval = {}
            catalog = self.trailer["/Root"]
            
            # get the name tree
            if catalog.has_key("/Dests"):
                tree = catalog["/Dests"]
            elif catalog.has_key("/Names"):
                names = catalog['/Names']
                if names.has_key("/Dests"):
                    tree = names['/Dests']
        
        if tree == None:
            return retval

        if tree.has_key("/Kids"):
            # recurse down the tree
            for kid in tree["/Kids"]:
                self.getNamedDestinations(kid.getObject(), retval)

        if tree.has_key("/Names"):
            names = tree["/Names"]
            for i in range(0, len(names), 2):
                key = names[i].getObject()
                val = names[i+1].getObject()
                if isinstance(val, DictionaryObject) and val.has_key('/D'):
                    val = val['/D']
                dest = self._buildDestination(key, val)
                if dest != None:
                    retval[key] = dest

        return retval

    ##
    # Read-only property that accesses the {@link #PdfFileReader.getOutlines
    # getOutlines} function.
    # <p>
    # Stability: Added in v1.10, will exist for all future v1.x releases.
    outlines = property(lambda self: self.getOutlines(), None, None)

    ##
    # Retrieves the document outline present in the document.
    # <p>
    # Stability: Added in v1.10, will exist for all future v1.x releases.
    # @return Returns a nested list of {@link #Destination destinations}.
    def getOutlines(self, node=None, outlines=None):
        if outlines == None:
            outlines = []
            catalog = self.trailer["/Root"]
            
            # get the outline dictionary and named destinations
            if catalog.has_key("/Outlines"):
                lines = catalog["/Outlines"]
                if lines.has_key("/First"):
                    node = lines["/First"]
            self._namedDests = self.getNamedDestinations()
            
        if node == None:
          return outlines
          
        # see if there are any more outlines
        while 1:
            outline = self._buildOutline(node)
            if outline:
                outlines.append(outline)

            # check for sub-outlines
            if node.has_key("/First"):
                subOutlines = []
                self.getOutlines(node["/First"], subOutlines)
                if subOutlines:
                    outlines.append(subOutlines)

            if not node.has_key("/Next"):
                break
            node = node["/Next"]

        return outlines

    def _buildDestination(self, title, array):
        page, typ = array[0:2]
        array = array[2:]
        return Destination(title, page, typ, *array)
          
    def _buildOutline(self, node):
        dest, title, outline = None, None, None
        
        if node.has_key("/A") and node.has_key("/Title"):
            # Action, section 8.5 (only type GoTo supported)
            title  = node["/Title"]
            action = node["/A"]
            if action["/S"] == "/GoTo":
                dest = action["/D"]
        elif node.has_key("/Dest") and node.has_key("/Title"):
            # Destination, section 8.2.1
            title = node["/Title"]
            dest  = node["/Dest"]

        # if destination found, then create outline
        if dest:
            if isinstance(dest, ArrayObject):
                outline = self._buildDestination(title, dest)
            elif isinstance(dest, unicode) and self._namedDests.has_key(dest):
                outline = self._namedDests[dest]
                outline[NameObject("/Title")] = title
            else:
                raise utils.PdfReadError("Unexpected destination %r" % dest)
        return outline

    ##
    # Read-only property that emulates a list based upon the {@link
    # #PdfFileReader.getNumPages getNumPages} and {@link #PdfFileReader.getPage
    # getPage} functions.
    # <p>
    # Stability: Added in v1.7, and will exist for all future v1.x releases.
    pages = property(lambda self: ConvertFunctionsToVirtualList(self.getNumPages, self.getPage),
            None, None)

    def _flatten(self, pages=None, inherit=None, indirectRef=None):
        inheritablePageAttributes = (
            NameObject("/Resources"), NameObject("/MediaBox"),
            NameObject("/CropBox"), NameObject("/Rotate")
            )
        if inherit == None:
            inherit = dict()
        if pages == None:
            self.flattenedPages = []
            catalog = self.trailer["/Root"].getObject()
            pages = catalog["/Pages"].getObject()
        t = pages["/Type"]
        if t == "/Pages":
            for attr in inheritablePageAttributes:
                if pages.has_key(attr):
                    inherit[attr] = pages[attr]
            for page in pages["/Kids"]:
                addt = {}
                if isinstance(page, IndirectObject):
                    addt["indirectRef"] = page
                self._flatten(page.getObject(), inherit, **addt)
        elif t == "/Page":
            for attr,value in inherit.items():
                # if the page has it's own value, it does not inherit the
                # parent's value:
                if not pages.has_key(attr):
                    pages[attr] = value
            pageObj = PageObject(self, indirectRef)
            pageObj.update(pages)
            self.flattenedPages.append(pageObj)

    def getObject(self, indirectReference):
        retval = self.resolvedObjects.get(indirectReference.generation, {}).get(indirectReference.idnum, None)
        if retval != None:
            return retval
        if indirectReference.generation == 0 and \
           self.xref_objStm.has_key(indirectReference.idnum):
            # indirect reference to object in object stream
            # read the entire object stream into memory
            stmnum,idx = self.xref_objStm[indirectReference.idnum]
            objStm = IndirectObject(stmnum, 0, self).getObject()
            assert objStm['/Type'] == '/ObjStm'
            assert idx < objStm['/N']
            streamData = StringIO(objStm.getData())
            for i in range(objStm['/N']):
                objnum = NumberObject.readFromStream(streamData)
                readNonWhitespace(streamData)
                streamData.seek(-1, 1)
                offset = NumberObject.readFromStream(streamData)
                readNonWhitespace(streamData)
                streamData.seek(-1, 1)
                t = streamData.tell()
                streamData.seek(objStm['/First']+offset, 0)
                obj = readObject(streamData, self)
                self.resolvedObjects[0][objnum] = obj
                streamData.seek(t, 0)
            return self.resolvedObjects[0][indirectReference.idnum]
        start = self.xref[indirectReference.generation][indirectReference.idnum]
        self.stream.seek(start, 0)
        idnum, generation = self.readObjectHeader(self.stream)
        assert idnum == indirectReference.idnum
        assert generation == indirectReference.generation
        retval = readObject(self.stream, self)

        # override encryption is used for the /Encrypt dictionary
        if not self._override_encryption and self.isEncrypted:
            # if we don't have the encryption key:
            if not hasattr(self, '_decryption_key'):
                raise Exception, "file has not been decrypted"
            # otherwise, decrypt here...
            import struct
            pack1 = struct.pack("<i", indirectReference.idnum)[:3]
            pack2 = struct.pack("<i", indirectReference.generation)[:2]
            key = self._decryption_key + pack1 + pack2
            assert len(key) == (len(self._decryption_key) + 5)
            md5_hash = md5(key).digest()
            key = md5_hash[:min(16, len(self._decryption_key) + 5)]
            retval = self._decryptObject(retval, key)

        self.cacheIndirectObject(generation, idnum, retval)
        return retval

    def _decryptObject(self, obj, key):
        if isinstance(obj, ByteStringObject) or isinstance(obj, TextStringObject):
            obj = createStringObject(utils.RC4_encrypt(key, obj.original_bytes))
        elif isinstance(obj, StreamObject):
            obj._data = utils.RC4_encrypt(key, obj._data)
        elif isinstance(obj, DictionaryObject):
            for dictkey, value in obj.items():
                obj[dictkey] = self._decryptObject(value, key)
        elif isinstance(obj, ArrayObject):
            for i in range(len(obj)):
                obj[i] = self._decryptObject(obj[i], key)
        return obj

    def readObjectHeader(self, stream):
        # Should never be necessary to read out whitespace, since the
        # cross-reference table should put us in the right spot to read the
        # object header.  In reality... some files have stupid cross reference
        # tables that are off by whitespace bytes.
        readNonWhitespace(stream); stream.seek(-1, 1)
        idnum = readUntilWhitespace(stream)
        generation = readUntilWhitespace(stream)
        obj = stream.read(3)
        readNonWhitespace(stream)
        stream.seek(-1, 1)
        return int(idnum), int(generation)

    def cacheIndirectObject(self, generation, idnum, obj):
        if not self.resolvedObjects.has_key(generation):
            self.resolvedObjects[generation] = {}
        self.resolvedObjects[generation][idnum] = obj

    def read(self, stream):
        # start at the end:
        stream.seek(-1, 2)
        line = ''
        while not line:
            line = self.readNextEndLine(stream)
        if line[:5] != "%%EOF":
            raise utils.PdfReadError, "EOF marker not found"

        # find startxref entry - the location of the xref table
        line = self.readNextEndLine(stream)
        startxref = int(line)
        line = self.readNextEndLine(stream)
        if line[:9] != "startxref":
            raise utils.PdfReadError, "startxref not found"

        # read all cross reference tables and their trailers
        self.xref = {}
        self.xref_objStm = {}
        self.trailer = DictionaryObject()
        while 1:
            # load the xref table
            stream.seek(startxref, 0)
            x = stream.read(1)
            if x == "x":
                # standard cross-reference table
                ref = stream.read(4)
                if ref[:3] != "ref":
                    raise utils.PdfReadError, "xref table read error"
                readNonWhitespace(stream)
                stream.seek(-1, 1)
                while 1:
                    num = readObject(stream, self)
                    readNonWhitespace(stream)
                    stream.seek(-1, 1)
                    size = readObject(stream, self)
                    readNonWhitespace(stream)
                    stream.seek(-1, 1)
                    cnt = 0
                    while cnt < size:
                        line = stream.read(20)
                        # It's very clear in section 3.4.3 of the PDF spec
                        # that all cross-reference table lines are a fixed
                        # 20 bytes.  However... some malformed PDF files
                        # use a single character EOL without a preceeding
                        # space.  Detect that case, and seek the stream
                        # back one character.  (0-9 means we've bled into
                        # the next xref entry, t means we've bled into the
                        # text "trailer"):
                        if line[-1] in "0123456789t":
                            stream.seek(-1, 1)
                        offset, generation = line[:16].split(" ")
                        offset, generation = int(offset), int(generation)
                        if not self.xref.has_key(generation):
                            self.xref[generation] = {}
                        if self.xref[generation].has_key(num):
                            # It really seems like we should allow the last
                            # xref table in the file to override previous
                            # ones. Since we read the file backwards, assume
                            # any existing key is already set correctly.
                            pass
                        else:
                            self.xref[generation][num] = offset
                        cnt += 1
                        num += 1
                    readNonWhitespace(stream)
                    stream.seek(-1, 1)
                    trailertag = stream.read(7)
                    if trailertag != "trailer":
                        # more xrefs!
                        stream.seek(-7, 1)
                    else:
                        break
                readNonWhitespace(stream)
                stream.seek(-1, 1)
                newTrailer = readObject(stream, self)
                for key, value in newTrailer.items():
                    if not self.trailer.has_key(key):
                        self.trailer[key] = value
                if newTrailer.has_key("/Prev"):
                    startxref = newTrailer["/Prev"]
                else:
                    break
            elif x.isdigit():
                # PDF 1.5+ Cross-Reference Stream
                stream.seek(-1, 1)
                idnum, generation = self.readObjectHeader(stream)
                xrefstream = readObject(stream, self)
                assert xrefstream["/Type"] == "/XRef"
                self.cacheIndirectObject(generation, idnum, xrefstream)
                streamData = StringIO(xrefstream.getData())
                idx_pairs = xrefstream.get("/Index", [0, xrefstream.get("/Size")])
                entrySizes = xrefstream.get("/W")
                for num, size in self._pairs(idx_pairs):
                    cnt = 0
                    while cnt < size:
                        for i in range(len(entrySizes)):
                            d = streamData.read(entrySizes[i])
                            di = convertToInt(d, entrySizes[i])
                            if i == 0:
                                xref_type = di
                            elif i == 1:
                                if xref_type == 0:
                                    next_free_object = di
                                elif xref_type == 1:
                                    byte_offset = di
                                elif xref_type == 2:
                                    objstr_num = di
                            elif i == 2:
                                if xref_type == 0:
                                    next_generation = di
                                elif xref_type == 1:
                                    generation = di
                                elif xref_type == 2:
                                    obstr_idx = di
                        if xref_type == 0:
                            pass
                        elif xref_type == 1:
                            if not self.xref.has_key(generation):
                                self.xref[generation] = {}
                            if not num in self.xref[generation]:
                                self.xref[generation][num] = byte_offset
                        elif xref_type == 2:
                            if not num in self.xref_objStm:
                                self.xref_objStm[num] = [objstr_num, obstr_idx]
                        cnt += 1
                        num += 1
                trailerKeys = "/Root", "/Encrypt", "/Info", "/ID"
                for key in trailerKeys:
                    if xrefstream.has_key(key) and not self.trailer.has_key(key):
                        self.trailer[NameObject(key)] = xrefstream.raw_get(key)
                if xrefstream.has_key("/Prev"):
                    startxref = xrefstream["/Prev"]
                else:
                    break
            else:
                # bad xref character at startxref.  Let's see if we can find
                # the xref table nearby, as we've observed this error with an
                # off-by-one before.
                stream.seek(-11, 1)
                tmp = stream.read(20)
                xref_loc = tmp.find("xref")
                if xref_loc != -1:
                    startxref -= (10 - xref_loc)
                    continue
                else:
                    # no xref table found at specified location
                    assert False
                    break

    def _pairs(self, array):
        i = 0
        while True:
            yield array[i], array[i+1]
            i += 2
            if (i+1) >= len(array):
                break

    def readNextEndLine(self, stream):
        line = ""
        while True:
            x = stream.read(1)
            stream.seek(-2, 1)
            if x == '\n' or x == '\r':
                while x == '\n' or x == '\r':
                    x = stream.read(1)
                    stream.seek(-2, 1)
                stream.seek(1, 1)
                break
            else:
                line = x + line
        return line

    ##
    # When using an encrypted / secured PDF file with the PDF Standard
    # encryption handler, this function will allow the file to be decrypted.
    # It checks the given password against the document's user password and
    # owner password, and then stores the resulting decryption key if either
    # password is correct.
    # <p>
    # It does not matter which password was matched.  Both passwords provide
    # the correct decryption key that will allow the document to be used with
    # this library.
    # <p>
    # Stability: Added in v1.8, will exist for all future v1.x releases.
    #
    # @return 0 if the password failed, 1 if the password matched the user
    # password, and 2 if the password matched the owner password.
    #
    # @exception NotImplementedError Document uses an unsupported encryption
    # method.
    def decrypt(self, password):
        self._override_encryption = True
        try:
            return self._decrypt(password)
        finally:
            self._override_encryption = False

    def _decrypt(self, password):
        encrypt = self.trailer['/Encrypt'].getObject()
        if encrypt['/Filter'] != '/Standard':
            raise NotImplementedError, "only Standard PDF encryption handler is available"
        if not (encrypt['/V'] in (1, 2)):
            raise NotImplementedError, "only algorithm code 1 and 2 are supported"
        user_password, key = self._authenticateUserPassword(password)
        if user_password:
            self._decryption_key = key
            return 1
        else:
            rev = encrypt['/R'].getObject()
            if rev == 2:
                keylen = 5
            else:
                keylen = encrypt['/Length'].getObject() / 8
            key = _alg33_1(password, rev, keylen)
            real_O = encrypt["/O"].getObject()
            if rev == 2:
                userpass = utils.RC4_encrypt(key, real_O)
            else:
                val = real_O
                for i in range(19, -1, -1):
                    new_key = ''
                    for l in range(len(key)):
                        new_key += chr(ord(key[l]) ^ i)
                    val = utils.RC4_encrypt(new_key, val)
                userpass = val
            owner_password, key = self._authenticateUserPassword(userpass)
            if owner_password:
                self._decryption_key = key
                return 2
        return 0

    def _authenticateUserPassword(self, password):
        encrypt = self.trailer['/Encrypt'].getObject()
        rev = encrypt['/R'].getObject()
        owner_entry = encrypt['/O'].getObject().original_bytes
        p_entry = encrypt['/P'].getObject()
        id_entry = self.trailer['/ID'].getObject()
        id1_entry = id_entry[0].getObject()
        if rev == 2:
            U, key = _alg34(password, owner_entry, p_entry, id1_entry)
        elif rev >= 3:
            U, key = _alg35(password, rev,
                    encrypt["/Length"].getObject() / 8, owner_entry,
                    p_entry, id1_entry,
                    encrypt.get("/EncryptMetadata", BooleanObject(False)).getObject())
        real_U = encrypt['/U'].getObject().original_bytes
        return U == real_U, key

    def getIsEncrypted(self):
        return self.trailer.has_key("/Encrypt")

    ##
    # Read-only boolean property showing whether this PDF file is encrypted.
    # Note that this property, if true, will remain true even after the {@link
    # #PdfFileReader.decrypt decrypt} function is called.
    isEncrypted = property(lambda self: self.getIsEncrypted(), None, None)


def getRectangle(self, name, defaults):
    retval = self.get(name)
    if isinstance(retval, RectangleObject):
        return retval
    if retval == None:
        for d in defaults:
            retval = self.get(d)
            if retval != None:
                break
    if isinstance(retval, IndirectObject):
        retval = self.pdf.getObject(retval)
    retval = RectangleObject(retval)
    setRectangle(self, name, retval)
    return retval

def setRectangle(self, name, value):
    if not isinstance(name, NameObject):
        name = NameObject(name)
    self[name] = value

def deleteRectangle(self, name):
    del self[name]

def createRectangleAccessor(name, fallback):
    return \
        property(
            lambda self: getRectangle(self, name, fallback),
            lambda self, value: setRectangle(self, name, value),
            lambda self: deleteRectangle(self, name)
            )

##
# This class represents a single page within a PDF file.  Typically this object
# will be created by accessing the {@link #PdfFileReader.getPage getPage}
# function of the {@link #PdfFileReader PdfFileReader} class, but it is
# also possible to create an empty page with the createBlankPage static
# method.
# @param pdf PDF file the page belongs to (optional, defaults to None).
class PageObject(DictionaryObject):
    def __init__(self, pdf=None, indirectRef=None):
        DictionaryObject.__init__(self)
        self.pdf = pdf
        # Stores the original indirect reference to this object in its source PDF
        self.indirectRef = indirectRef

    ##
    # Returns a new blank page.
    # If width or height is None, try to get the page size from the
    # last page of pdf. If pdf is None or contains no page, a
    # PageSizeNotDefinedError is raised.
    # @param pdf    PDF file the page belongs to
    # @param width  The width of the new page expressed in default user
    #               space units.
    # @param height The height of the new page expressed in default user
    #               space units.
    def createBlankPage(pdf=None, width=None, height=None):
        page = PageObject(pdf)

        # Creates a new page (cf PDF Reference  7.7.3.3)
        page.__setitem__(NameObject('/Type'), NameObject('/Page'))
        page.__setitem__(NameObject('/Parent'), NullObject())
        page.__setitem__(NameObject('/Resources'), DictionaryObject())
        if width is None or height is None:
            if pdf is not None and pdf.getNumPages() > 0:
                lastpage = pdf.getPage(pdf.getNumPages() - 1)
                width = lastpage.mediaBox.getWidth()
                height = lastpage.mediaBox.getHeight()
            else:
                raise utils.PageSizeNotDefinedError()
        page.__setitem__(NameObject('/MediaBox'),
            RectangleObject([0, 0, width, height]))

        return page
    createBlankPage = staticmethod(createBlankPage)

    ##
    # Rotates a page clockwise by increments of 90 degrees.
    # <p>
    # Stability: Added in v1.1, will exist for all future v1.x releases.
    # @param angle Angle to rotate the page.  Must be an increment of 90 deg.
    def rotateClockwise(self, angle):
        assert angle % 90 == 0
        self._rotate(angle)
        return self

    ##
    # Rotates a page counter-clockwise by increments of 90 degrees.
    # <p>
    # Stability: Added in v1.1, will exist for all future v1.x releases.
    # @param angle Angle to rotate the page.  Must be an increment of 90 deg.
    def rotateCounterClockwise(self, angle):
        assert angle % 90 == 0
        self._rotate(-angle)
        return self

    def _rotate(self, angle):
        currentAngle = self.get("/Rotate", 0)
        self[NameObject("/Rotate")] = NumberObject(currentAngle + angle)

    def _mergeResources(res1, res2, resource):
        newRes = DictionaryObject()
        newRes.update(res1.get(resource, DictionaryObject()).getObject())
        page2Res = res2.get(resource, DictionaryObject()).getObject()
        renameRes = {}
        for key in page2Res.keys():
            if newRes.has_key(key) and newRes[key] != page2Res[key]:
                newname = NameObject(key + "renamed")
                renameRes[key] = newname
                newRes[newname] = page2Res[key]
            elif not newRes.has_key(key):
                newRes[key] = page2Res.raw_get(key)
        return newRes, renameRes
    _mergeResources = staticmethod(_mergeResources)

    def _contentStreamRename(stream, rename, pdf):
        if not rename:
            return stream
        stream = ContentStream(stream, pdf)
        for operands,operator in stream.operations:
            for i in range(len(operands)):
                op = operands[i]
                if isinstance(op, NameObject):
                    operands[i] = rename.get(op, op)
        return stream
    _contentStreamRename = staticmethod(_contentStreamRename)

    def _pushPopGS(contents, pdf):
        # adds a graphics state "push" and "pop" to the beginning and end
        # of a content stream.  This isolates it from changes such as 
        # transformation matricies.
        stream = ContentStream(contents, pdf)
        stream.operations.insert(0, [[], "q"])
        stream.operations.append([[], "Q"])
        return stream
    _pushPopGS = staticmethod(_pushPopGS)

    def _addTransformationMatrix(contents, pdf, ctm):
        # adds transformation matrix at the beginning of the given
        # contents stream.
        a, b, c, d, e, f = ctm
        contents = ContentStream(contents, pdf)
        contents.operations.insert(0, [[FloatObject(a), FloatObject(b),
            FloatObject(c), FloatObject(d), FloatObject(e),
            FloatObject(f)], " cm"])
        return contents
    _addTransformationMatrix = staticmethod(_addTransformationMatrix)

    ##
    # Returns the /Contents object, or None if it doesn't exist.
    # /Contents is optionnal, as described in PDF Reference  7.7.3.3
    def getContents(self):
      if self.has_key("/Contents"):
        return self["/Contents"].getObject()
      else:
        return None

    ##
    # Merges the content streams of two pages into one.  Resource references
    # (i.e. fonts) are maintained from both pages.  The mediabox/cropbox/etc
    # of this page are not altered.  The parameter page's content stream will
    # be added to the end of this page's content stream, meaning that it will
    # be drawn after, or "on top" of this page.
    # <p>
    # Stability: Added in v1.4, will exist for all future 1.x releases.
    # @param page2 An instance of {@link #PageObject PageObject} to be merged
    #              into this one.
    def mergePage(self, page2):
        self._mergePage(page2)

    ##
    # Actually merges the content streams of two pages into one. Resource
    # references (i.e. fonts) are maintained from both pages. The
    # mediabox/cropbox/etc of this page are not altered. The parameter page's
    # content stream will be added to the end of this page's content stream,
    # meaning that it will be drawn after, or "on top" of this page.
    #
    # @param page2 An instance of {@link #PageObject PageObject} to be merged
    #              into this one.
    # @param page2transformation A fuction which applies a transformation to
    #                            the content stream of page2. Takes: page2
    #                            contents stream. Must return: new contents
    #                            stream. If omitted, the content stream will
    #                            not be modified.
    def _mergePage(self, page2, page2transformation=None):
        # First we work on merging the resource dictionaries.  This allows us
        # to find out what symbols in the content streams we might need to
        # rename.

        newResources = DictionaryObject()
        rename = {}
        originalResources = self["/Resources"].getObject()
        page2Resources = page2["/Resources"].getObject()

        for res in "/ExtGState", "/Font", "/XObject", "/ColorSpace", "/Pattern", "/Shading", "/Properties":
            new, newrename = PageObject._mergeResources(originalResources, page2Resources, res)
            if new:
                newResources[NameObject(res)] = new
                rename.update(newrename)

        # Combine /ProcSet sets.
        newResources[NameObject("/ProcSet")] = ArrayObject(
            frozenset(originalResources.get("/ProcSet", ArrayObject()).getObject()).union(
                frozenset(page2Resources.get("/ProcSet", ArrayObject()).getObject())
            )
        )

        newContentArray = ArrayObject()

        originalContent = self.getContents()
        if originalContent is not None:
            newContentArray.append(PageObject._pushPopGS(
                  originalContent, self.pdf))

        page2Content = page2.getContents()
        if page2Content is not None:
            if page2transformation is not None:
                page2Content = page2transformation(page2Content)
            page2Content = PageObject._contentStreamRename(
                page2Content, rename, self.pdf)
            page2Content = PageObject._pushPopGS(page2Content, self.pdf)
            newContentArray.append(page2Content)

        self[NameObject('/Contents')] = ContentStream(newContentArray, self.pdf)
        self[NameObject('/Resources')] = newResources

    ##
    # This is similar to mergePage, but a transformation matrix is
    # applied to the merged stream.
    #
    # @param page2 An instance of {@link #PageObject PageObject} to be merged.
    # @param ctm   A 6 elements tuple containing the operands of the
    #              transformation matrix
    def mergeTransformedPage(self, page2, ctm):
        self._mergePage(page2, lambda page2Content:
            PageObject._addTransformationMatrix(page2Content, page2.pdf, ctm))

    ##
    # This is similar to mergePage, but the stream to be merged is scaled
    # by appling a transformation matrix.
    #
    # @param page2 An instance of {@link #PageObject PageObject} to be merged.
    # @param factor The scaling factor
    def mergeScaledPage(self, page2, factor):
        # CTM to scale : [ sx 0 0 sy 0 0 ]
        return self.mergeTransformedPage(page2, [factor, 0,
                                                 0,      factor,
                                                 0,      0])

    ##
    # This is similar to mergePage, but the stream to be merged is rotated
    # by appling a transformation matrix.
    #
    # @param page2 An instance of {@link #PageObject PageObject} to be merged.
    # @param rotation The angle of the rotation, in degrees
    def mergeRotatedPage(self, page2, rotation):
        rotation = math.radians(rotation)
        return self.mergeTransformedPage(page2,
            [math.cos(rotation),  math.sin(rotation),
             -math.sin(rotation), math.cos(rotation),
             0,                   0])

    ##
    # This is similar to mergePage, but the stream to be merged is translated
    # by appling a transformation matrix.
    #
    # @param page2 An instance of {@link #PageObject PageObject} to be merged.
    # @param tx    The translation on X axis
    # @param tx    The translation on Y axis
    def mergeTranslatedPage(self, page2, tx, ty):
        return self.mergeTransformedPage(page2, [1,  0,
                                                 0,  1,
                                                 tx, ty])

    ##
    # This is similar to mergePage, but the stream to be merged is rotated
    # and scaled by appling a transformation matrix.
    #
    # @param page2 An instance of {@link #PageObject PageObject} to be merged.
    # @param rotation The angle of the rotation, in degrees
    # @param factor The scaling factor
    def mergeRotatedScaledPage(self, page2, rotation, scale):
        rotation = math.radians(rotation)
        rotating = [[math.cos(rotation), math.sin(rotation),0],
                    [-math.sin(rotation),math.cos(rotation), 0],
                    [0,                  0,                  1]]
        scaling = [[scale,0,    0],
                   [0,    scale,0],
                   [0,    0,    1]]
        ctm = utils.matrixMultiply(rotating, scaling)

        return self.mergeTransformedPage(page2,
                                         [ctm[0][0], ctm[0][1],
                                          ctm[1][0], ctm[1][1],
                                          ctm[2][0], ctm[2][1]])

    ##
    # This is similar to mergePage, but the stream to be merged is translated
    # and scaled by appling a transformation matrix.
    #
    # @param page2 An instance of {@link #PageObject PageObject} to be merged.
    # @param scale The scaling factor
    # @param tx    The translation on X axis
    # @param tx    The translation on Y axis
    def mergeScaledTranslatedPage(self, page2, scale, tx, ty):
        translation = [[1, 0, 0],
                       [0, 1, 0],
                       [tx,ty,1]]
        scaling = [[scale,0,    0],
                   [0,    scale,0],
                   [0,    0,    1]]
        ctm = utils.matrixMultiply(scaling, translation)

        return self.mergeTransformedPage(page2, [ctm[0][0], ctm[0][1],
                                                 ctm[1][0], ctm[1][1],
                                                 ctm[2][0], ctm[2][1]])

    ##
    # This is similar to mergePage, but the stream to be merged is translated,
    # rotated and scaled by appling a transformation matrix.
    #
    # @param page2 An instance of {@link #PageObject PageObject} to be merged.
    # @param tx    The translation on X axis
    # @param ty    The translation on Y axis
    # @param rotation The angle of the rotation, in degrees
    # @param scale The scaling factor
    def mergeRotatedScaledTranslatedPage(self, page2, rotation, scale, tx, ty):
        translation = [[1, 0, 0],
                       [0, 1, 0],
                       [tx,ty,1]]
        rotation = math.radians(rotation)
        rotating = [[math.cos(rotation), math.sin(rotation),0],
                    [-math.sin(rotation),math.cos(rotation), 0],
                    [0,                  0,                  1]]
        scaling = [[scale,0,    0],
                   [0,    scale,0],
                   [0,    0,    1]]
        ctm = utils.matrixMultiply(rotating, scaling)
        ctm = utils.matrixMultiply(ctm, translation)

        return self.mergeTransformedPage(page2, [ctm[0][0], ctm[0][1],
                                                 ctm[1][0], ctm[1][1],
                                                 ctm[2][0], ctm[2][1]])

    ##
    # Applys a transformation matrix the page.
    #
    # @param ctm   A 6 elements tuple containing the operands of the
    #              transformation matrix
    def addTransformation(self, ctm):
        originalContent = self.getContents()
        if originalContent is not None:
            newContent = PageObject._addTransformationMatrix(
                originalContent, self.pdf, ctm)
            newContent = PageObject._pushPopGS(newContent, self.pdf)
            self[NameObject('/Contents')] = newContent

    ##
    # Scales a page by the given factors by appling a transformation
    # matrix to its content and updating the page size.
    #
    # @param sx The scaling factor on horizontal axis
    # @param sy The scaling factor on vertical axis
    def scale(self, sx, sy):
        self.addTransformation([sx, 0,
                                0,  sy,
                                0,  0])
        self.mediaBox = RectangleObject([
            float(self.mediaBox.getLowerLeft_x()) * sx,
            float(self.mediaBox.getLowerLeft_y()) * sy,
            float(self.mediaBox.getUpperRight_x()) * sx,
            float(self.mediaBox.getUpperRight_y()) * sy])

    ##
    # Scales a page by the given factor by appling a transformation
    # matrix to its content and updating the page size.
    #
    # @param factor The scaling factor
    def scaleBy(self, factor):
        self.scale(factor, factor)

    ##
    # Scales a page to the specified dimentions by appling a
    # transformation matrix to its content and updating the page size.
    #
    # @param width The new width
    # @param height The new heigth
    def scaleTo(self, width, height):
        sx = width / (self.mediaBox.getUpperRight_x() -
                      self.mediaBox.getLowerLeft_x ())
        sy = height / (self.mediaBox.getUpperRight_y() -
                       self.mediaBox.getLowerLeft_x ())
        self.scale(sx, sy)

    ##
    # Compresses the size of this page by joining all content streams and
    # applying a FlateDecode filter.
    # <p>
    # Stability: Added in v1.6, will exist for all future v1.x releases.
    # However, it is possible that this function will perform no action if
    # content stream compression becomes "automatic" for some reason.
    def compressContentStreams(self):
        content = self.getContents()
        if content is not None:
            if not isinstance(content, ContentStream):
                content = ContentStream(content, self.pdf)
            self[NameObject("/Contents")] = content.flateEncode()

    ##
    # Locate all text drawing commands, in the order they are provided in the
    # content stream, and extract the text.  This works well for some PDF
    # files, but poorly for others, depending on the generator used.  This will
    # be refined in the future.  Do not rely on the order of text coming out of
    # this function, as it will change if this function is made more
    # sophisticated.
    # <p>
    # Stability: Added in v1.7, will exist for all future v1.x releases.  May
    # be overhauled to provide more ordered text in the future.
    # @return a unicode string object
    def extractText(self):
        text = u""
        content = self["/Contents"].getObject()
        if not isinstance(content, ContentStream):
            content = ContentStream(content, self.pdf)
        # Note: we check all strings are TextStringObjects.  ByteStringObjects
        # are strings where the byte->string encoding was unknown, so adding
        # them to the text here would be gibberish.
        for operands,operator in content.operations:
            if operator == "Tj":
                _text = operands[0]
                if isinstance(_text, TextStringObject):
                    text += _text
            elif operator == "T*":
                text += "\n"
            elif operator == "'":
                text += "\n"
                _text = operands[0]
                if isinstance(_text, TextStringObject):
                    text += operands[0]
            elif operator == '"':
                _text = operands[2]
                if isinstance(_text, TextStringObject):
                    text += "\n"
                    text += _text
            elif operator == "TJ":
                for i in operands[0]:
                    if isinstance(i, TextStringObject):
                        text += i
        return text

    ##
    # A rectangle (RectangleObject), expressed in default user space units,
    # defining the boundaries of the physical medium on which the page is
    # intended to be displayed or printed.
    # <p>
    # Stability: Added in v1.4, will exist for all future v1.x releases.
    mediaBox = createRectangleAccessor("/MediaBox", ())

    ##
    # A rectangle (RectangleObject), expressed in default user space units,
    # defining the visible region of default user space.  When the page is
    # displayed or printed, its contents are to be clipped (cropped) to this
    # rectangle and then imposed on the output medium in some
    # implementation-defined manner.  Default value: same as MediaBox.
    # <p>
    # Stability: Added in v1.4, will exist for all future v1.x releases.
    cropBox = createRectangleAccessor("/CropBox", ("/MediaBox",))

    ##
    # A rectangle (RectangleObject), expressed in default user space units,
    # defining the region to which the contents of the page should be clipped
    # when output in a production enviroment.
    # <p>
    # Stability: Added in v1.4, will exist for all future v1.x releases.
    bleedBox = createRectangleAccessor("/BleedBox", ("/CropBox", "/MediaBox"))

    ##
    # A rectangle (RectangleObject), expressed in default user space units,
    # defining the intended dimensions of the finished page after trimming.
    # <p>
    # Stability: Added in v1.4, will exist for all future v1.x releases.
    trimBox = createRectangleAccessor("/TrimBox", ("/CropBox", "/MediaBox"))

    ##
    # A rectangle (RectangleObject), expressed in default user space units,
    # defining the extent of the page's meaningful content as intended by the
    # page's creator.
    # <p>
    # Stability: Added in v1.4, will exist for all future v1.x releases.
    artBox = createRectangleAccessor("/ArtBox", ("/CropBox", "/MediaBox"))


class ContentStream(DecodedStreamObject):
    def __init__(self, stream, pdf):
        self.pdf = pdf
        self.operations = []
        # stream may be a StreamObject or an ArrayObject containing
        # multiple StreamObjects to be cat'd together.
        stream = stream.getObject()
        if isinstance(stream, ArrayObject):
            data = ""
            for s in stream:
                data += s.getObject().getData()
            stream = StringIO(data)
        else:
            stream = StringIO(stream.getData())
        self.__parseContentStream(stream)

    def __parseContentStream(self, stream):
        # file("f:\\tmp.txt", "w").write(stream.read())
        stream.seek(0, 0)
        operands = []
        while True:
            peek = readNonWhitespace(stream)
            if peek == '':
                break
            stream.seek(-1, 1)
            if peek.isalpha() or peek == "'" or peek == '"':
                operator = ""
                while True:
                    tok = stream.read(1)
                    if tok.isspace() or tok in NameObject.delimiterCharacters:
                        stream.seek(-1, 1)
                        break
                    elif tok == '':
                        break
                    operator += tok
                if operator == "BI":
                    # begin inline image - a completely different parsing
                    # mechanism is required, of course... thanks buddy...
                    assert operands == []
                    ii = self._readInlineImage(stream)
                    self.operations.append((ii, "INLINE IMAGE"))
                else:
                    self.operations.append((operands, operator))
                    operands = []
            elif peek == '%':
                # If we encounter a comment in the content stream, we have to
                # handle it here.  Typically, readObject will handle
                # encountering a comment -- but readObject assumes that
                # following the comment must be the object we're trying to
                # read.  In this case, it could be an operator instead.
                while peek not in ('\r', '\n'):
                    peek = stream.read(1)
            else:
                operands.append(readObject(stream, None))

    def _readInlineImage(self, stream):
        # begin reading just after the "BI" - begin image
        # first read the dictionary of settings.
        settings = DictionaryObject()
        while True:
            tok = readNonWhitespace(stream)
            stream.seek(-1, 1)
            if tok == "I":
                # "ID" - begin of image data
                break
            key = readObject(stream, self.pdf)
            tok = readNonWhitespace(stream)
            stream.seek(-1, 1)
            value = readObject(stream, self.pdf)
            settings[key] = value
        # left at beginning of ID
        tmp = stream.read(3)
        assert tmp[:2] == "ID"
        data = ""
        while True:
            tok = stream.read(1)
            if tok == "E":
                next = stream.read(1)
                if next == "I":
                    break
                else:
                    stream.seek(-1, 1)
                    data += tok
            else:
                data += tok
        x = readNonWhitespace(stream)
        stream.seek(-1, 1)
        return {"settings": settings, "data": data}

    def _getData(self):
        newdata = StringIO()
        for operands,operator in self.operations:
            if operator == "INLINE IMAGE":
                newdata.write("BI")
                dicttext = StringIO()
                operands["settings"].writeToStream(dicttext, None)
                newdata.write(dicttext.getvalue()[2:-2])
                newdata.write("ID ")
                newdata.write(operands["data"])
                newdata.write("EI")
            else:
                for op in operands:
                    op.writeToStream(newdata, None)
                    newdata.write(" ")
                newdata.write(operator)
            newdata.write("\n")
        return newdata.getvalue()

    def _setData(self, value):
        self.__parseContentStream(StringIO(value))

    _data = property(_getData, _setData)


##
# A class representing the basic document metadata provided in a PDF File.
# <p>
# As of pyPdf v1.10, all text properties of the document metadata have two
# properties, eg. author and author_raw.  The non-raw property will always
# return a TextStringObject, making it ideal for a case where the metadata is
# being displayed.  The raw property can sometimes return a ByteStringObject,
# if pyPdf was unable to decode the string's text encoding; this requires
# additional safety in the caller and therefore is not as commonly accessed.
class DocumentInformation(DictionaryObject):
    def __init__(self):
        DictionaryObject.__init__(self)

    def getText(self, key):
        retval = self.get(key, None)
        if isinstance(retval, TextStringObject):
            return retval
        return None

    ##
    # Read-only property accessing the document's title.  Added in v1.6, will
    # exist for all future v1.x releases.  Modified in v1.10 to always return a
    # unicode string (TextStringObject).
    # @return A unicode string, or None if the title is not provided.
    title = property(lambda self: self.getText("/Title"))
    title_raw = property(lambda self: self.get("/Title"))

    ##
    # Read-only property accessing the document's author.  Added in v1.6, will
    # exist for all future v1.x releases.  Modified in v1.10 to always return a
    # unicode string (TextStringObject).
    # @return A unicode string, or None if the author is not provided.
    author = property(lambda self: self.getText("/Author"))
    author_raw = property(lambda self: self.get("/Author"))

    ##
    # Read-only property accessing the subject of the document.  Added in v1.6,
    # will exist for all future v1.x releases.  Modified in v1.10 to always
    # return a unicode string (TextStringObject).
    # @return A unicode string, or None if the subject is not provided.
    subject = property(lambda self: self.getText("/Subject"))
    subject_raw = property(lambda self: self.get("/Subject"))

    ##
    # Read-only property accessing the document's creator.  If the document was
    # converted to PDF from another format, the name of the application (for
    # example, OpenOffice) that created the original document from which it was
    # converted.  Added in v1.6, will exist for all future v1.x releases.
    # Modified in v1.10 to always return a unicode string (TextStringObject).
    # @return A unicode string, or None if the creator is not provided.
    creator = property(lambda self: self.getText("/Creator"))
    creator_raw = property(lambda self: self.get("/Creator"))

    ##
    # Read-only property accessing the document's producer.  If the document
    # was converted to PDF from another format, the name of the application
    # (for example, OSX Quartz) that converted it to PDF.  Added in v1.6, will
    # exist for all future v1.x releases.  Modified in v1.10 to always return a
    # unicode string (TextStringObject).
    # @return A unicode string, or None if the producer is not provided.
    producer = property(lambda self: self.getText("/Producer"))
    producer_raw = property(lambda self: self.get("/Producer"))


##
# A class representing a destination within a PDF file.
# See section 8.2.1 of the PDF 1.6 reference.
# Stability: Added in v1.10, will exist for all v1.x releases.
class Destination(DictionaryObject):
    def __init__(self, title, page, typ, *args):
        DictionaryObject.__init__(self)
        self[NameObject("/Title")] = title
        self[NameObject("/Page")] = page
        self[NameObject("/Type")] = typ
        
        # from table 8.2 of the PDF 1.6 reference.
        if typ == "/XYZ":
            (self[NameObject("/Left")], self[NameObject("/Top")],
                self[NameObject("/Zoom")]) = args
        elif typ == "/FitR":
            (self[NameObject("/Left")], self[NameObject("/Bottom")],
                self[NameObject("/Right")], self[NameObject("/Top")]) = args
        elif typ in ["/FitH", "FitBH"]:
            self[NameObject("/Top")], = args
        elif typ in ["/FitV", "FitBV"]:
            self[NameObject("/Left")], = args
        elif typ in ["/Fit", "FitB"]:
            pass
        else:
            raise utils.PdfReadError("Unknown Destination Type: %r" % typ)
          
    ##
    # Read-only property accessing the destination title.
    # @return A string.
    title = property(lambda self: self.get("/Title"))

    ##
    # Read-only property accessing the destination page.
    # @return An integer.
    page = property(lambda self: self.get("/Page"))

    ##
    # Read-only property accessing the destination type.
    # @return A string.
    typ = property(lambda self: self.get("/Type"))

    ##
    # Read-only property accessing the zoom factor.
    # @return A number, or None if not available.
    zoom = property(lambda self: self.get("/Zoom", None))

    ##
    # Read-only property accessing the left horizontal coordinate.
    # @return A number, or None if not available.
    left = property(lambda self: self.get("/Left", None))

    ##
    # Read-only property accessing the right horizontal coordinate.
    # @return A number, or None if not available.
    right = property(lambda self: self.get("/Right", None))

    ##
    # Read-only property accessing the top vertical coordinate.
    # @return A number, or None if not available.
    top = property(lambda self: self.get("/Top", None))

    ##
    # Read-only property accessing the bottom vertical coordinate.
    # @return A number, or None if not available.
    bottom = property(lambda self: self.get("/Bottom", None))

def convertToInt(d, size):
    if size > 8:
        raise utils.PdfReadError("invalid size in convertToInt")
    d = "\x00\x00\x00\x00\x00\x00\x00\x00" + d
    d = d[-8:]
    return struct.unpack(">q", d)[0]

# ref: pdf1.8 spec section 3.5.2 algorithm 3.2
_encryption_padding = '\x28\xbf\x4e\x5e\x4e\x75\x8a\x41\x64\x00\x4e\x56' + \
        '\xff\xfa\x01\x08\x2e\x2e\x00\xb6\xd0\x68\x3e\x80\x2f\x0c' + \
        '\xa9\xfe\x64\x53\x69\x7a'

# Implementation of algorithm 3.2 of the PDF standard security handler,
# section 3.5.2 of the PDF 1.6 reference.
def _alg32(password, rev, keylen, owner_entry, p_entry, id1_entry, metadata_encrypt=True):
    # 1. Pad or truncate the password string to exactly 32 bytes.  If the
    # password string is more than 32 bytes long, use only its first 32 bytes;
    # if it is less than 32 bytes long, pad it by appending the required number
    # of additional bytes from the beginning of the padding string
    # (_encryption_padding).
    password = (password + _encryption_padding)[:32]
    # 2. Initialize the MD5 hash function and pass the result of step 1 as
    # input to this function.
    import struct
    m = md5(password)
    # 3. Pass the value of the encryption dictionary's /O entry to the MD5 hash
    # function.
    m.update(owner_entry)
    # 4. Treat the value of the /P entry as an unsigned 4-byte integer and pass
    # these bytes to the MD5 hash function, low-order byte first.
    p_entry = struct.pack('<i', p_entry)
    m.update(p_entry)
    # 5. Pass the first element of the file's file identifier array to the MD5
    # hash function.
    m.update(id1_entry)
    # 6. (Revision 3 or greater) If document metadata is not being encrypted,
    # pass 4 bytes with the value 0xFFFFFFFF to the MD5 hash function.
    if rev >= 3 and not metadata_encrypt:
        m.update("\xff\xff\xff\xff")
    # 7. Finish the hash.
    md5_hash = m.digest()
    # 8. (Revision 3 or greater) Do the following 50 times: Take the output
    # from the previous MD5 hash and pass the first n bytes of the output as
    # input into a new MD5 hash, where n is the number of bytes of the
    # encryption key as defined by the value of the encryption dictionary's
    # /Length entry.
    if rev >= 3:
        for i in range(50):
            md5_hash = md5(md5_hash[:keylen]).digest()
    # 9. Set the encryption key to the first n bytes of the output from the
    # final MD5 hash, where n is always 5 for revision 2 but, for revision 3 or
    # greater, depends on the value of the encryption dictionary's /Length
    # entry.
    return md5_hash[:keylen]

# Implementation of algorithm 3.3 of the PDF standard security handler,
# section 3.5.2 of the PDF 1.6 reference.
def _alg33(owner_pwd, user_pwd, rev, keylen):
    # steps 1 - 4
    key = _alg33_1(owner_pwd, rev, keylen)
    # 5. Pad or truncate the user password string as described in step 1 of
    # algorithm 3.2.
    user_pwd = (user_pwd + _encryption_padding)[:32]
    # 6. Encrypt the result of step 5, using an RC4 encryption function with
    # the encryption key obtained in step 4.
    val = utils.RC4_encrypt(key, user_pwd)
    # 7. (Revision 3 or greater) Do the following 19 times: Take the output
    # from the previous invocation of the RC4 function and pass it as input to
    # a new invocation of the function; use an encryption key generated by
    # taking each byte of the encryption key obtained in step 4 and performing
    # an XOR operation between that byte and the single-byte value of the
    # iteration counter (from 1 to 19).
    if rev >= 3:
        for i in range(1, 20):
            new_key = ''
            for l in range(len(key)):
                new_key += chr(ord(key[l]) ^ i)
            val = utils.RC4_encrypt(new_key, val)
    # 8. Store the output from the final invocation of the RC4 as the value of
    # the /O entry in the encryption dictionary.
    return val

# Steps 1-4 of algorithm 3.3
def _alg33_1(password, rev, keylen):
    # 1. Pad or truncate the owner password string as described in step 1 of
    # algorithm 3.2.  If there is no owner password, use the user password
    # instead.
    password = (password + _encryption_padding)[:32]
    # 2. Initialize the MD5 hash function and pass the result of step 1 as
    # input to this function.
    m = md5(password)
    # 3. (Revision 3 or greater) Do the following 50 times: Take the output
    # from the previous MD5 hash and pass it as input into a new MD5 hash.
    md5_hash = m.digest()
    if rev >= 3:
        for i in range(50):
            md5_hash = md5(md5_hash).digest()
    # 4. Create an RC4 encryption key using the first n bytes of the output
    # from the final MD5 hash, where n is always 5 for revision 2 but, for
    # revision 3 or greater, depends on the value of the encryption
    # dictionary's /Length entry.
    key = md5_hash[:keylen]
    return key

# Implementation of algorithm 3.4 of the PDF standard security handler,
# section 3.5.2 of the PDF 1.6 reference.
def _alg34(password, owner_entry, p_entry, id1_entry):
    # 1. Create an encryption key based on the user password string, as
    # described in algorithm 3.2.
    key = _alg32(password, 2, 5, owner_entry, p_entry, id1_entry)
    # 2. Encrypt the 32-byte padding string shown in step 1 of algorithm 3.2,
    # using an RC4 encryption function with the encryption key from the
    # preceding step.
    U = utils.RC4_encrypt(key, _encryption_padding)
    # 3. Store the result of step 2 as the value of the /U entry in the
    # encryption dictionary.
    return U, key

# Implementation of algorithm 3.4 of the PDF standard security handler,
# section 3.5.2 of the PDF 1.6 reference.
def _alg35(password, rev, keylen, owner_entry, p_entry, id1_entry, metadata_encrypt):
    # 1. Create an encryption key based on the user password string, as
    # described in Algorithm 3.2.
    key = _alg32(password, rev, keylen, owner_entry, p_entry, id1_entry)
    # 2. Initialize the MD5 hash function and pass the 32-byte padding string
    # shown in step 1 of Algorithm 3.2 as input to this function. 
    m = md5()
    m.update(_encryption_padding)
    # 3. Pass the first element of the file's file identifier array (the value
    # of the ID entry in the document's trailer dictionary; see Table 3.13 on
    # page 73) to the hash function and finish the hash.  (See implementation
    # note 25 in Appendix H.) 
    m.update(id1_entry)
    md5_hash = m.digest()
    # 4. Encrypt the 16-byte result of the hash, using an RC4 encryption
    # function with the encryption key from step 1. 
    val = utils.RC4_encrypt(key, md5_hash)
    # 5. Do the following 19 times: Take the output from the previous
    # invocation of the RC4 function and pass it as input to a new invocation
    # of the function; use an encryption key generated by taking each byte of
    # the original encryption key (obtained in step 2) and performing an XOR
    # operation between that byte and the single-byte value of the iteration
    # counter (from 1 to 19). 
    for i in range(1, 20):
        new_key = ''
        for l in range(len(key)):
            new_key += chr(ord(key[l]) ^ i)
        val = utils.RC4_encrypt(new_key, val)
    # 6. Append 16 bytes of arbitrary padding to the output from the final
    # invocation of the RC4 function and store the 32-byte result as the value
    # of the U entry in the encryption dictionary. 
    # (implementator note: I don't know what "arbitrary padding" is supposed to
    # mean, so I have used null bytes.  This seems to match a few other
    # people's implementations)
    return val + ('\x00' * 16), key

#if __name__ == "__main__":
#    output = PdfFileWriter()
#
#    input1 = PdfFileReader(file("test\\5000-s1-05e.pdf", "rb"))
#    page1 = input1.getPage(0)
#
#    input2 = PdfFileReader(file("test\\PDFReference16.pdf", "rb"))
#    page2 = input2.getPage(0)
#    page3 = input2.getPage(1)
#    page1.mergePage(page2)
#    page1.mergePage(page3)
#
#    input3 = PdfFileReader(file("test\\cc-cc.pdf", "rb"))
#    page1.mergePage(input3.getPage(0))
#
#    page1.compressContentStreams()
#
#    output.addPage(page1)
#    output.write(file("test\\merge-test.pdf", "wb"))



########NEW FILE########
__FILENAME__ = utils
# vim: sw=4:expandtab:foldmethod=marker
#
# Copyright (c) 2006, Mathieu Fenniak
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# * The name of the author may not be used to endorse or promote products
# derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


"""
Utility functions for PDF library.
"""
__author__ = "Mathieu Fenniak"
__author_email__ = "biziqe@mathieu.fenniak.net"

#ENABLE_PSYCO = False
#if ENABLE_PSYCO:
#    try:
#        import psyco
#    except ImportError:
#        ENABLE_PSYCO = False
#
#if not ENABLE_PSYCO:
#    class psyco:
#        def proxy(func):
#            return func
#        proxy = staticmethod(proxy)

def readUntilWhitespace(stream, maxchars=None):
    txt = ""
    while True:
        tok = stream.read(1)
        if tok.isspace() or not tok:
            break
        txt += tok
        if len(txt) == maxchars:
            break
    return txt

def readNonWhitespace(stream):
    tok = ' '
    while tok == '\n' or tok == '\r' or tok == ' ' or tok == '\t':
        tok = stream.read(1)
    return tok

class ConvertFunctionsToVirtualList(object):
    def __init__(self, lengthFunction, getFunction):
        self.lengthFunction = lengthFunction
        self.getFunction = getFunction

    def __len__(self):
        return self.lengthFunction()

    def __getitem__(self, index):
        if not isinstance(index, int):
            raise TypeError, "sequence indices must be integers"
        len_self = len(self)
        if index < 0:
            # support negative indexes
            index = len_self + index
        if index < 0 or index >= len_self:
            raise IndexError, "sequence index out of range"
        return self.getFunction(index)

def RC4_encrypt(key, plaintext):
    S = [i for i in range(256)]
    j = 0
    for i in range(256):
        j = (j + S[i] + ord(key[i % len(key)])) % 256
        S[i], S[j] = S[j], S[i]
    i, j = 0, 0
    retval = ""
    for x in range(len(plaintext)):
        i = (i + 1) % 256
        j = (j + S[i]) % 256
        S[i], S[j] = S[j], S[i]
        t = S[(S[i] + S[j]) % 256]
        retval += chr(ord(plaintext[x]) ^ t)
    return retval

def matrixMultiply(a, b):
    return [[sum([float(i)*float(j)
                  for i, j in zip(row, col)]
                ) for col in zip(*b)]
            for row in a]

class PyPdfError(Exception):
    pass

class PdfReadError(PyPdfError):
    pass

class PageSizeNotDefinedError(PyPdfError):
    pass

if __name__ == "__main__":
    # test RC4
    out = RC4_encrypt("Key", "Plaintext")
    print repr(out)
    pt = RC4_encrypt("Key", out)
    print repr(pt)

########NEW FILE########
__FILENAME__ = xmp
import re
import datetime
import decimal
from generic import PdfObject
from xml.dom import getDOMImplementation
from xml.dom.minidom import parseString

RDF_NAMESPACE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
DC_NAMESPACE = "http://purl.org/dc/elements/1.1/"
XMP_NAMESPACE = "http://ns.adobe.com/xap/1.0/"
PDF_NAMESPACE = "http://ns.adobe.com/pdf/1.3/"
XMPMM_NAMESPACE = "http://ns.adobe.com/xap/1.0/mm/"

# What is the PDFX namespace, you might ask?  I might ask that too.  It's
# a completely undocumented namespace used to place "custom metadata"
# properties, which are arbitrary metadata properties with no semantic or
# documented meaning.  Elements in the namespace are key/value-style storage,
# where the element name is the key and the content is the value.  The keys
# are transformed into valid XML identifiers by substituting an invalid
# identifier character with \u2182 followed by the unicode hex ID of the
# original character.  A key like "my car" is therefore "my\u21820020car".
#
# \u2182, in case you're wondering, is the unicode character
# \u{ROMAN NUMERAL TEN THOUSAND}, a straightforward and obvious choice for
# escaping characters.
#
# Intentional users of the pdfx namespace should be shot on sight.  A
# custom data schema and sensical XML elements could be used instead, as is
# suggested by Adobe's own documentation on XMP (under "Extensibility of
# Schemas").
#
# Information presented here on the /pdfx/ schema is a result of limited
# reverse engineering, and does not constitute a full specification.
PDFX_NAMESPACE = "http://ns.adobe.com/pdfx/1.3/"

iso8601 = re.compile("""
        (?P<year>[0-9]{4})
        (-
            (?P<month>[0-9]{2})
            (-
                (?P<day>[0-9]+)
                (T
                    (?P<hour>[0-9]{2}):
                    (?P<minute>[0-9]{2})
                    (:(?P<second>[0-9]{2}(.[0-9]+)?))?
                    (?P<tzd>Z|[-+][0-9]{2}:[0-9]{2})
                )?
            )?
        )?
        """, re.VERBOSE)

##
# An object that represents Adobe XMP metadata.
class XmpInformation(PdfObject):

    def __init__(self, stream):
        self.stream = stream
        docRoot = parseString(self.stream.getData())
        self.rdfRoot = docRoot.getElementsByTagNameNS(RDF_NAMESPACE, "RDF")[0]
        self.cache = {}

    def writeToStream(self, stream, encryption_key):
        self.stream.writeToStream(stream, encryption_key)

    def getElement(self, aboutUri, namespace, name):
        for desc in self.rdfRoot.getElementsByTagNameNS(RDF_NAMESPACE, "Description"):
            if desc.getAttributeNS(RDF_NAMESPACE, "about") == aboutUri:
                attr = desc.getAttributeNodeNS(namespace, name)
                if attr != None:
                    yield attr
                for element in desc.getElementsByTagNameNS(namespace, name):
                    yield element

    def getNodesInNamespace(self, aboutUri, namespace):
        for desc in self.rdfRoot.getElementsByTagNameNS(RDF_NAMESPACE, "Description"):
            if desc.getAttributeNS(RDF_NAMESPACE, "about") == aboutUri:
                for i in range(desc.attributes.length):
                    attr = desc.attributes.item(i)
                    if attr.namespaceURI == namespace:
                        yield attr
                for child in desc.childNodes:
                    if child.namespaceURI == namespace:
                        yield child

    def _getText(self, element):
        text = ""
        for child in element.childNodes:
            if child.nodeType == child.TEXT_NODE:
                text += child.data
        return text

    def _converter_string(value):
        return value

    def _converter_date(value):
        m = iso8601.match(value)
        year = int(m.group("year"))
        month = int(m.group("month") or "1")
        day = int(m.group("day") or "1")
        hour = int(m.group("hour") or "0")
        minute = int(m.group("minute") or "0")
        second = decimal.Decimal(m.group("second") or "0")
        seconds = second.to_integral(decimal.ROUND_FLOOR)
        milliseconds = (second - seconds) * 1000000
        tzd = m.group("tzd") or "Z"
        dt = datetime.datetime(year, month, day, hour, minute, seconds, milliseconds)
        if tzd != "Z":
            tzd_hours, tzd_minutes = [int(x) for x in tzd.split(":")]
            tzd_hours *= -1
            if tzd_hours < 0:
                tzd_minutes *= -1
            dt = dt + datetime.timedelta(hours=tzd_hours, minutes=tzd_minutes)
        return dt
    _test_converter_date = staticmethod(_converter_date)

    def _getter_bag(namespace, name, converter):
        def get(self):
            cached = self.cache.get(namespace, {}).get(name)
            if cached:
                return cached
            retval = []
            for element in self.getElement("", namespace, name):
                bags = element.getElementsByTagNameNS(RDF_NAMESPACE, "Bag")
                if len(bags):
                    for bag in bags:
                        for item in bag.getElementsByTagNameNS(RDF_NAMESPACE, "li"):
                            value = self._getText(item)
                            value = converter(value)
                            retval.append(value)
            ns_cache = self.cache.setdefault(namespace, {})
            ns_cache[name] = retval
            return retval
        return get

    def _getter_seq(namespace, name, converter):
        def get(self):
            cached = self.cache.get(namespace, {}).get(name)
            if cached:
                return cached
            retval = []
            for element in self.getElement("", namespace, name):
                seqs = element.getElementsByTagNameNS(RDF_NAMESPACE, "Seq")
                if len(seqs):
                    for seq in seqs:
                        for item in seq.getElementsByTagNameNS(RDF_NAMESPACE, "li"):
                            value = self._getText(item)
                            value = converter(value)
                            retval.append(value)
                else:
                    value = converter(self._getText(element))
                    retval.append(value)
            ns_cache = self.cache.setdefault(namespace, {})
            ns_cache[name] = retval
            return retval
        return get

    def _getter_langalt(namespace, name, converter):
        def get(self):
            cached = self.cache.get(namespace, {}).get(name)
            if cached:
                return cached
            retval = {}
            for element in self.getElement("", namespace, name):
                alts = element.getElementsByTagNameNS(RDF_NAMESPACE, "Alt")
                if len(alts):
                    for alt in alts:
                        for item in alt.getElementsByTagNameNS(RDF_NAMESPACE, "li"):
                            value = self._getText(item)
                            value = converter(value)
                            retval[item.getAttribute("xml:lang")] = value
                else:
                    retval["x-default"] = converter(self._getText(element))
            ns_cache = self.cache.setdefault(namespace, {})
            ns_cache[name] = retval
            return retval
        return get

    def _getter_single(namespace, name, converter):
        def get(self):
            cached = self.cache.get(namespace, {}).get(name)
            if cached:
                return cached
            value = None
            for element in self.getElement("", namespace, name):
                if element.nodeType == element.ATTRIBUTE_NODE:
                    value = element.nodeValue
                else:
                    value = self._getText(element)
                break
            if value != None:
                value = converter(value)
            ns_cache = self.cache.setdefault(namespace, {})
            ns_cache[name] = value
            return value
        return get

    ##
    # Contributors to the resource (other than the authors).  An unsorted
    # array of names.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_contributor = property(_getter_bag(DC_NAMESPACE, "contributor", _converter_string))

    ##
    # Text describing the extent or scope of the resource.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_coverage = property(_getter_single(DC_NAMESPACE, "coverage", _converter_string))

    ##
    # A sorted array of names of the authors of the resource, listed in order
    # of precedence.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_creator = property(_getter_seq(DC_NAMESPACE, "creator", _converter_string))

    ##
    # A sorted array of dates (datetime.datetime instances) of signifigance to
    # the resource.  The dates and times are in UTC.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_date = property(_getter_seq(DC_NAMESPACE, "date", _converter_date))

    ##
    # A language-keyed dictionary of textual descriptions of the content of the
    # resource.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_description = property(_getter_langalt(DC_NAMESPACE, "description", _converter_string))

    ##
    # The mime-type of the resource.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_format = property(_getter_single(DC_NAMESPACE, "format", _converter_string))

    ##
    # Unique identifier of the resource.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_identifier = property(_getter_single(DC_NAMESPACE, "identifier", _converter_string))

    ##
    # An unordered array specifying the languages used in the resource.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_language = property(_getter_bag(DC_NAMESPACE, "language", _converter_string))

    ##
    # An unordered array of publisher names.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_publisher = property(_getter_bag(DC_NAMESPACE, "publisher", _converter_string))

    ##
    # An unordered array of text descriptions of relationships to other
    # documents.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_relation = property(_getter_bag(DC_NAMESPACE, "relation", _converter_string))

    ##
    # A language-keyed dictionary of textual descriptions of the rights the
    # user has to this resource.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_rights = property(_getter_langalt(DC_NAMESPACE, "rights", _converter_string))

    ##
    # Unique identifier of the work from which this resource was derived.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_source = property(_getter_single(DC_NAMESPACE, "source", _converter_string))

    ##
    # An unordered array of descriptive phrases or keywrods that specify the
    # topic of the content of the resource.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_subject = property(_getter_bag(DC_NAMESPACE, "subject", _converter_string))

    ##
    # A language-keyed dictionary of the title of the resource.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_title = property(_getter_langalt(DC_NAMESPACE, "title", _converter_string))

    ##
    # An unordered array of textual descriptions of the document type.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    dc_type = property(_getter_bag(DC_NAMESPACE, "type", _converter_string))

    ##
    # An unformatted text string representing document keywords.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    pdf_keywords = property(_getter_single(PDF_NAMESPACE, "Keywords", _converter_string))

    ##
    # The PDF file version, for example 1.0, 1.3.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    pdf_pdfversion = property(_getter_single(PDF_NAMESPACE, "PDFVersion", _converter_string))

    ##
    # The name of the tool that created the PDF document.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    pdf_producer = property(_getter_single(PDF_NAMESPACE, "Producer", _converter_string))

    ##
    # The date and time the resource was originally created.  The date and
    # time are returned as a UTC datetime.datetime object.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    xmp_createDate = property(_getter_single(XMP_NAMESPACE, "CreateDate", _converter_date))
    
    ##
    # The date and time the resource was last modified.  The date and time
    # are returned as a UTC datetime.datetime object.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    xmp_modifyDate = property(_getter_single(XMP_NAMESPACE, "ModifyDate", _converter_date))

    ##
    # The date and time that any metadata for this resource was last
    # changed.  The date and time are returned as a UTC datetime.datetime
    # object.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    xmp_metadataDate = property(_getter_single(XMP_NAMESPACE, "MetadataDate", _converter_date))

    ##
    # The name of the first known tool used to create the resource.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    xmp_creatorTool = property(_getter_single(XMP_NAMESPACE, "CreatorTool", _converter_string))

    ##
    # The common identifier for all versions and renditions of this resource.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    xmpmm_documentId = property(_getter_single(XMPMM_NAMESPACE, "DocumentID", _converter_string))

    ##
    # An identifier for a specific incarnation of a document, updated each
    # time a file is saved.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    xmpmm_instanceId = property(_getter_single(XMPMM_NAMESPACE, "InstanceID", _converter_string))

    def custom_properties(self):
        if not hasattr(self, "_custom_properties"):
            self._custom_properties = {}
            for node in self.getNodesInNamespace("", PDFX_NAMESPACE):
                key = node.localName
                while True:
                    # see documentation about PDFX_NAMESPACE earlier in file
                    idx = key.find(u"\u2182")
                    if idx == -1:
                        break
                    key = key[:idx] + chr(int(key[idx+1:idx+5], base=16)) + key[idx+5:]
                if node.nodeType == node.ATTRIBUTE_NODE:
                    value = node.nodeValue
                else:
                    value = self._getText(node)
                self._custom_properties[key] = value
        return self._custom_properties

    ##
    # Retrieves custom metadata properties defined in the undocumented pdfx
    # metadata schema.
    # <p>Stability: Added in v1.12, will exist for all future v1.x releases.
    # @return Returns a dictionary of key/value items for custom metadata
    # properties.
    custom_properties = property(custom_properties)



########NEW FILE########
