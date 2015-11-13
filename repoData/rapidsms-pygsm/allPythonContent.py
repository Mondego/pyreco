__FILENAME__ = devicewrapper
#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8

# arch: pacman -S python-pyserial
# debian/ubuntu: apt-get install python-serial
import serial
import re
import errors

class DeviceWrapper(object):
    
    def __init__(self, logger, *args, **kwargs):

        # Sanitize arguments before sending to pySerial

        # force cast strings from the .ini (which show up
        # in kwargs) to ints because strings seem to make
        # pySerial on Windows unhappy
        
        for key in ['baudrate', 
                    'xonxoff',
                    'rtscts',
                    'stopbits',
                    'timeout'
                    ]:
            if key in kwargs:
                try:
                    kwargs[key] = int(kwargs[key])
                except:
                    # not a valid value, just remove
                    kwargs.pop(key)

        self.device = serial.Serial(*args, **kwargs)
        self.logger = logger

    def isOpen(self):
        return self.device.isOpen()

    def close(self):
        self.device.close()
    
    def write(self, str):
        self.device.write(str)
            
    def _read(self, read_term=None, read_timeout=None):
        """Read from the modem (blocking) until _terminator_ is hit,
           (defaults to \r\n, which reads a single "line"), and return."""
        
        buffer = []

        # if a different timeout was requested just
        # for _this_ read, store and override the
        # current device setting (not thread safe!)
        if read_timeout is not None:
            old_timeout = self.device.timeout
            self.device.timeout = read_timeout

        def __reset_timeout():
            """restore the device's previous timeout
               setting, if we overrode it earlier."""
            if read_timeout is not None:
                self.device.timeout =\
                    old_timeout

        # the default terminator reads
        # until a newline is hit
        if read_term is None:
            read_term = "\r\n"

        while(True):
            buf = self.device.read()
            buffer.append(buf)            
            # if a timeout was hit, raise an exception including the raw data that
            # we've already read (in case the calling func was _expecting_ a timeout
            # (wouldn't it be nice if serial.Serial.read returned None for this?)
            if buf == '':
                __reset_timeout()
                raise(errors.GsmReadTimeoutError(buffer))

            # if last n characters of the buffer match the read
            # terminator, return what we've received so far
            if ''.join(buffer[-len(read_term):]) == read_term:
                buf_str = ''.join(buffer)
                __reset_timeout()

                self._log(repr(buf_str), 'read')
                return buf_str


    def read_lines(self, read_term=None, read_timeout=None):
        """Read from the modem (blocking) one line at a time until a response
           terminator ("OK", "ERROR", or "CMx ERROR...") is hit, then return
           a list containing the lines."""
        buffer = []

        # keep on looping until a command terminator
        # is encountered. these are NOT the same as the
        # "read_term" argument - only OK or ERROR is valid
        while(True):
            buf = self._read(
                read_term=read_term,
                read_timeout=read_timeout)

            buf = buf.strip()
            buffer.append(buf)

            # most commands return OK for success, but there
            # are some exceptions. we're not checking those
            # here (unlike RubyGSM), because they should be
            # handled when they're _expected_
            if buf == "OK":
                return buffer

            # some errors contain useful error codes, so raise a
            # proper error with a description from pygsm/errors.py
            m = re.match(r"^\+(CM[ES]) ERROR: (\d+)$", buf)
            if m is not None:
                type, code = m.groups()
                raise(errors.GsmModemError(type, int(code)))

            # ...some errors are not so useful
            # (at+cmee=1 should enable error codes)
            if buf == "ERROR":
                raise(errors.GsmModemError)

    def _log(self, str_, type_="debug"):
        if hasattr(self, "logger"):
            self.logger(self, str_, type_)    
            

########NEW FILE########
__FILENAME__ = errors
#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4


import serial


class GsmError(serial.SerialException):
    pass


class GsmIOError(GsmError):
    pass


class GsmWriteError(GsmIOError):
    pass


class GsmReadError(GsmIOError):
    pass


class GsmReadTimeoutError(GsmReadError):
    def __init__(self, pending_data):
        self.pending_data = pending_data


class GsmModemError(GsmError):
    STRINGS = {
        "CME": {
            3:   "Operation not allowed",
            4:   "Operation not supported",
            5:   "PH-SIM PIN required (SIM lock)",
            10:  "SIM not inserted",
            11:  "SIM PIN required",
            12:  "SIM PUK required",
            13:  "SIM failure",
            16:  "Incorrect password",
            17:  "SIM PIN2 required",
            18:  "SIM PUK2 required",
            20:  "Memory full",
            21:  "Invalid index",
            22:  "Not found",
            24:  "Text string too long",
            26:  "Dial string too long",
            27:  "Invalid characters in dial string",
            30:  "No network service",
            32:  "Network not allowed. Emergency calls only",
            40:  "Network personal PIN required (Network lock)",
            103: "Illegal MS (#3)",
            106: "Illegal ME (#6)",
            107: "GPRS services not allowed",
            111: "PLMN not allowed",
            112: "Location area not allowed",
            113: "Roaming not allowed in this area",
            132: "Service option not supported",
            133: "Requested service option not subscribed",
            134: "Service option temporarily out of order",
            148: "unspecified GPRS error",
            149: "PDP authentication failure",
            150: "Invalid mobile class" },
        "CMS": {
            021: "Call Rejected (out of credit?)",
            301: "SMS service of ME reserved",
            302: "Operation not allowed",
            303: "Operation not supported",
            304: "Invalid PDU mode parameter",
            305: "Invalid text mode parameter",
            310: "SIM not inserted",
            311: "SIM PIN required",
            312: "PH-SIM PIN required",
            313: "SIM failure",
            316: "SIM PUK required",
            317: "SIM PIN2 required",
            318: "SIM PUK2 required",
            321: "Invalid memory index",
            322: "SIM memory full",
            330: "SC address unknown",
            340: "No +CNMA acknowledgement expected",
            500: "Unknown error",
            512: "MM establishment failure (for SMS)",
            513: "Lower layer failure (for SMS)",
            514: "CP error (for SMS)",
            515: "Please wait, init or command processing in progress",
            517: "SIM Toolkit facility not supported",
            518: "SIM Toolkit indication not received",
            519: "Reset product to activate or change new echo cancellation algo",
            520: "Automatic abort about get PLMN list for an incomming call",
            526: "PIN deactivation forbidden with this SIM card",
            527: "Please wait, RR or MM is busy. Retry your selection later",
            528: "Location update failure. Emergency calls only",
            529: "PLMN selection failure. Emergency calls only",
            531: "SMS not send: the <da> is not in FDN phonebook, and FDN lock is enabled (for SMS)" }}

    def __init__(self, type=None, code=None):
        self.type = type
        self.code = code

    def __str__(self):
        if self.type and self.code:
            return "%s ERROR %d: %s" % (
                self.type, self.code,
                self.STRINGS[self.type][self.code])

        # no type and/or code were provided
        else: return "Unknown GSM Error"

########NEW FILE########
__FILENAME__ = gsm0338
# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8

""" Python Character Mapping Codec based on gsm0338 generated from './GSM0338.TXT' with gencodec.py.
    
    With extra sauce to deal with the 'multibyte' extensions!

"""#"

import codecs
import re

### Codec APIs

#
# Shared funcs
#
def _encode(input,errors='strict'):
    # split to see if we have any 'extended' characters
    runs=unicode_splitter.split(input)
    
    # now iterate through handling any 'multibyte' ourselves
    out_str=list()
    consumed=0
    extended=extended_encode_map.keys()
    for run in runs:
        if len(run)==1 and run[0] in extended:
            out_str.append(extended_indicator+extended_encode_map[run])
            consumed+=1
        else:
            # pass it to the standard encoder
            out,cons=codecs.charmap_encode(run,errors,encoding_table)
            out_str.append(out)
            consumed+=cons
    return (''.join(out_str),consumed)

def _decode(input,errors='strict'):
    # opposite of above, look for multibye 'marker'
    # and handle it ourselves, pass the rest to the
    # standard decoder
    
    # split to see if we have any 'extended' characters
    runs = str_splitter.split(input)

    # now iterate through handling any 'multibyte' ourselves
    out_uni = []
    consumed = 0
    for run in runs:
        if len(run)==0:
            # first char was a marker, but we don't care
            # the marker itself will come up in the next run
            continue
        if len(run)==2 and run[0]==extended_indicator:
            try:
                out_uni.append(extended_decode_map[run[1]])
                consumed += 2
                continue
            except KeyError:
                # second char was not an extended, so
                # let this pass through and the marker
                # will be interpreted by the table as a NBSP
                pass

        # pass it to the standard encoder
        out,cons=codecs.charmap_decode(run,errors,decoding_table)
        out_uni.append(out)
        consumed+=cons
    return (u''.join(out_uni),consumed)


class Codec(codecs.Codec):
    def encode(self,input,errors='strict'):
        return _encode(input,errors)

    def decode(self,input,errors='strict'):
        # strip any trailing '\x00's as the standard
        # says trailing ones are _not_ @'s and 
        # are in fact blanks
        if input[-1]=='\x00':
            input=input[:-1]
        return _decode(input,errors)

class IncrementalEncoder(codecs.IncrementalEncoder):
    def encode(self, input, final=False):
        # just use the standard encoding as there is no need
        # to hold state
        return _encode(input,self.errors)[0]

class IncrementalDecoder(codecs.IncrementalDecoder):
    # a little trickier 'cause input _might_ come in
    # split right on the extended char marker boundary
    def __init__(self,errors='strict'):
        codecs.IncrementalDecoder.__init__(self,errors)
        self.last_saw_mark=False

    def decode(self, input, final=False):
        if final:
            # check for final '\x00' which should not
            # be interpreted as a '@'
            if input[-1]=='\x00':
                input=input[:-1]

        # keep track of how many chars we've added or
        # removed to the run to adjust the response from
        # _decode
        consumed_delta=0
        # see if last char was a 2-byte mark
        if self.last_saw_mark:
            # add it back to the current run
            input=extended_indicator+input
            consumed_delta-=1 # 'cause we added a char
            self.last_saw_mark=False # reset
        if input[-1:]==extended_indicator and not final:
            # chop it off
            input=input[:-1]
            consumed_delta+=1 # because we just consumed one char
            self.last_saw_mark=True

            # NOTE: if we are final and last mark is 
            # and extended indicator, it will be interpreted
            # as NBSP
        return _decode(input,self.errors)[0]

    def reset(self):
        self.last_saw_mark=False

class StreamWriter(Codec,codecs.StreamWriter):
    pass

class StreamReader(Codec,codecs.StreamReader):
    pass

### encodings module API

def getregentry():
    return codecs.CodecInfo(
        name='gsm0338',
        encode=Codec().encode,
        decode=Codec().decode,
        incrementalencoder=IncrementalEncoder,
        incrementaldecoder=IncrementalDecoder,
        streamreader=StreamReader,
        streamwriter=StreamWriter,
    )


### Decoding Tables

# gsm 'extended' character.
# gsm, annoyingly, is MOSTLY 7-bit chars
#
# BUT has 10 'extended' chars represented
# by 2-chars, an idicator, and then one of 
# the 10

# first of the 2-chars is indicator
extended_indicator='\x1b'

# second char is the 'extended' character
extended_encode_map = { # Unicode->GSM string
    u'\x0c':'\x0a',  # FORM FEED
    u'^':'\x14',     # CIRCUMFLEX ACCENT
    u'{':'\x28',     # LEFT CURLY BRACKET
    u'}':'\x29',     # RIGHT CURLY BRACKET
    u'\\':'\x2f',    # REVERSE SOLIDUS
    u'[':'\x3c',     # LEFT SQUARE BRACKET
    u'~':'\x3d',     # TILDE
    u']':'\x3e',     # RIGHT SQUARE BRACKET
    u'|':'\x40',     # VERTICAL LINE
    u'\u20ac':'\x65' # EURO SIGN
}

# reverse the map above for decoding
# GSM String->Unicode
uni,gsm=zip(*extended_encode_map.items())
extended_decode_map=dict(zip(gsm,uni))

# splitter
str_splitter=re.compile('(%(ind)s[^%(ind)s])' % { 'ind':extended_indicator })
unicode_splitter=re.compile(u'([%s])' % re.escape(''.join(extended_encode_map.keys())), re.UNICODE)

# the normal 1-char table
decoding_table = (
    u'@'        #  0x00 -> COMMERCIAL AT
    u'\xa3'     #  0x01 -> POUND SIGN
    u'$'        #  0x02 -> DOLLAR SIGN
    u'\xa5'     #  0x03 -> YEN SIGN
    u'\xe8'     #  0x04 -> LATIN SMALL LETTER E WITH GRAVE
    u'\xe9'     #  0x05 -> LATIN SMALL LETTER E WITH ACUTE
    u'\xf9'     #  0x06 -> LATIN SMALL LETTER U WITH GRAVE
    u'\xec'     #  0x07 -> LATIN SMALL LETTER I WITH GRAVE
    u'\xf2'     #  0x08 -> LATIN SMALL LETTER O WITH GRAVE
    u'\xe7'     #  0x09 -> LATIN SMALL LETTER C WITH CEDILLA
    u'\n'       #  0x0A -> LINE FEED
    u'\xd8'     #  0x0B -> LATIN CAPITAL LETTER O WITH STROKE
    u'\xf8'     #  0x0C -> LATIN SMALL LETTER O WITH STROKE
    u'\r'       #  0x0D -> CARRIAGE RETURN
    u'\xc5'     #  0x0E -> LATIN CAPITAL LETTER A WITH RING ABOVE
    u'\xe5'     #  0x0F -> LATIN SMALL LETTER A WITH RING ABOVE
    u'\u0394'   #  0x10 -> GREEK CAPITAL LETTER DELTA
    u'_'        #  0x11 -> LOW LINE
    u'\u03a6'   #  0x12 -> GREEK CAPITAL LETTER PHI
    u'\u0393'   #  0x13 -> GREEK CAPITAL LETTER GAMMA
    u'\u039b'   #  0x14 -> GREEK CAPITAL LETTER LAMDA
    u'\u03a9'   #  0x15 -> GREEK CAPITAL LETTER OMEGA
    u'\u03a0'   #  0x16 -> GREEK CAPITAL LETTER PI
    u'\u03a8'   #  0x17 -> GREEK CAPITAL LETTER PSI
    u'\u03a3'   #  0x18 -> GREEK CAPITAL LETTER SIGMA
    u'\u0398'   #  0x19 -> GREEK CAPITAL LETTER THETA
    u'\u039e'   #  0x1A -> GREEK CAPITAL LETTER XI
    u'\xa0'     #  0x1B -> ESCAPE TO EXTENSION TABLE (or displayed as NBSP, see note above)
    u'\xc6'     #  0x1C -> LATIN CAPITAL LETTER AE
    u'\xe6'     #  0x1D -> LATIN SMALL LETTER AE
    u'\xdf'     #  0x1E -> LATIN SMALL LETTER SHARP S (German)
    u'\xc9'     #  0x1F -> LATIN CAPITAL LETTER E WITH ACUTE
    u' '        #  0x20 -> SPACE
    u'!'        #  0x21 -> EXCLAMATION MARK
    u'"'        #  0x22 -> QUOTATION MARK
    u'#'        #  0x23 -> NUMBER SIGN
    u'\xa4'     #  0x24 -> CURRENCY SIGN
    u'%'        #  0x25 -> PERCENT SIGN
    u'&'        #  0x26 -> AMPERSAND
    u"'"        #  0x27 -> APOSTROPHE
    u'('        #  0x28 -> LEFT PARENTHESIS
    u')'        #  0x29 -> RIGHT PARENTHESIS
    u'*'        #  0x2A -> ASTERISK
    u'+'        #  0x2B -> PLUS SIGN
    u','        #  0x2C -> COMMA
    u'-'        #  0x2D -> HYPHEN-MINUS
    u'.'        #  0x2E -> FULL STOP
    u'/'        #  0x2F -> SOLIDUS
    u'0'        #  0x30 -> DIGIT ZERO
    u'1'        #  0x31 -> DIGIT ONE
    u'2'        #  0x32 -> DIGIT TWO
    u'3'        #  0x33 -> DIGIT THREE
    u'4'        #  0x34 -> DIGIT FOUR
    u'5'        #  0x35 -> DIGIT FIVE
    u'6'        #  0x36 -> DIGIT SIX
    u'7'        #  0x37 -> DIGIT SEVEN
    u'8'        #  0x38 -> DIGIT EIGHT
    u'9'        #  0x39 -> DIGIT NINE
    u':'        #  0x3A -> COLON
    u';'        #  0x3B -> SEMICOLON
    u'<'        #  0x3C -> LESS-THAN SIGN
    u'='        #  0x3D -> EQUALS SIGN
    u'>'        #  0x3E -> GREATER-THAN SIGN
    u'?'        #  0x3F -> QUESTION MARK
    u'\xa1'     #  0x40 -> INVERTED EXCLAMATION MARK
    u'A'        #  0x41 -> LATIN CAPITAL LETTER A
    u'B'        #  0x42 -> LATIN CAPITAL LETTER B
    u'C'        #  0x43 -> LATIN CAPITAL LETTER C
    u'D'        #  0x44 -> LATIN CAPITAL LETTER D
    u'E'        #  0x45 -> LATIN CAPITAL LETTER E
    u'F'        #  0x46 -> LATIN CAPITAL LETTER F
    u'G'        #  0x47 -> LATIN CAPITAL LETTER G
    u'H'        #  0x48 -> LATIN CAPITAL LETTER H
    u'I'        #  0x49 -> LATIN CAPITAL LETTER I
    u'J'        #  0x4A -> LATIN CAPITAL LETTER J
    u'K'        #  0x4B -> LATIN CAPITAL LETTER K
    u'L'        #  0x4C -> LATIN CAPITAL LETTER L
    u'M'        #  0x4D -> LATIN CAPITAL LETTER M
    u'N'        #  0x4E -> LATIN CAPITAL LETTER N
    u'O'        #  0x4F -> LATIN CAPITAL LETTER O
    u'P'        #  0x50 -> LATIN CAPITAL LETTER P
    u'Q'        #  0x51 -> LATIN CAPITAL LETTER Q
    u'R'        #  0x52 -> LATIN CAPITAL LETTER R
    u'S'        #  0x53 -> LATIN CAPITAL LETTER S
    u'T'        #  0x54 -> LATIN CAPITAL LETTER T
    u'U'        #  0x55 -> LATIN CAPITAL LETTER U
    u'V'        #  0x56 -> LATIN CAPITAL LETTER V
    u'W'        #  0x57 -> LATIN CAPITAL LETTER W
    u'X'        #  0x58 -> LATIN CAPITAL LETTER X
    u'Y'        #  0x59 -> LATIN CAPITAL LETTER Y
    u'Z'        #  0x5A -> LATIN CAPITAL LETTER Z
    u'\xc4'     #  0x5B -> LATIN CAPITAL LETTER A WITH DIAERESIS
    u'\xd6'     #  0x5C -> LATIN CAPITAL LETTER O WITH DIAERESIS
    u'\xd1'     #  0x5D -> LATIN CAPITAL LETTER N WITH TILDE
    u'\xdc'     #  0x5E -> LATIN CAPITAL LETTER U WITH DIAERESIS
    u'\xa7'     #  0x5F -> SECTION SIGN
    u'\xbf'     #  0x60 -> INVERTED QUESTION MARK
    u'a'        #  0x61 -> LATIN SMALL LETTER A
    u'b'        #  0x62 -> LATIN SMALL LETTER B
    u'c'        #  0x63 -> LATIN SMALL LETTER C
    u'd'        #  0x64 -> LATIN SMALL LETTER D
    u'e'        #  0x65 -> LATIN SMALL LETTER E
    u'f'        #  0x66 -> LATIN SMALL LETTER F
    u'g'        #  0x67 -> LATIN SMALL LETTER G
    u'h'        #  0x68 -> LATIN SMALL LETTER H
    u'i'        #  0x69 -> LATIN SMALL LETTER I
    u'j'        #  0x6A -> LATIN SMALL LETTER J
    u'k'        #  0x6B -> LATIN SMALL LETTER K
    u'l'        #  0x6C -> LATIN SMALL LETTER L
    u'm'        #  0x6D -> LATIN SMALL LETTER M
    u'n'        #  0x6E -> LATIN SMALL LETTER N
    u'o'        #  0x6F -> LATIN SMALL LETTER O
    u'p'        #  0x70 -> LATIN SMALL LETTER P
    u'q'        #  0x71 -> LATIN SMALL LETTER Q
    u'r'        #  0x72 -> LATIN SMALL LETTER R
    u's'        #  0x73 -> LATIN SMALL LETTER S
    u't'        #  0x74 -> LATIN SMALL LETTER T
    u'u'        #  0x75 -> LATIN SMALL LETTER U
    u'v'        #  0x76 -> LATIN SMALL LETTER V
    u'w'        #  0x77 -> LATIN SMALL LETTER W
    u'x'        #  0x78 -> LATIN SMALL LETTER X
    u'y'        #  0x79 -> LATIN SMALL LETTER Y
    u'z'        #  0x7A -> LATIN SMALL LETTER Z
    u'\xe4'     #  0x7B -> LATIN SMALL LETTER A WITH DIAERESIS
    u'\xf6'     #  0x7C -> LATIN SMALL LETTER O WITH DIAERESIS
    u'\xf1'     #  0x7D -> LATIN SMALL LETTER N WITH TILDE
    u'\xfc'     #  0x7E -> LATIN SMALL LETTER U WITH DIAERESIS
    u'\xe0'     #  0x7F -> LATIN SMALL LETTER A WITH GRAVE
    u'\ufffe'   #  0x80 -> UNDEFINED
    u'\ufffe'   #  0x81 -> UNDEFINED
    u'\ufffe'   #  0x82 -> UNDEFINED
    u'\ufffe'   #  0x83 -> UNDEFINED
    u'\ufffe'   #  0x84 -> UNDEFINED
    u'\ufffe'   #  0x85 -> UNDEFINED
    u'\ufffe'   #  0x86 -> UNDEFINED
    u'\ufffe'   #  0x87 -> UNDEFINED
    u'\ufffe'   #  0x88 -> UNDEFINED
    u'\ufffe'   #  0x89 -> UNDEFINED
    u'\ufffe'   #  0x8A -> UNDEFINED
    u'\ufffe'   #  0x8B -> UNDEFINED
    u'\ufffe'   #  0x8C -> UNDEFINED
    u'\ufffe'   #  0x8D -> UNDEFINED
    u'\ufffe'   #  0x8E -> UNDEFINED
    u'\ufffe'   #  0x8F -> UNDEFINED
    u'\ufffe'   #  0x90 -> UNDEFINED
    u'\ufffe'   #  0x91 -> UNDEFINED
    u'\ufffe'   #  0x92 -> UNDEFINED
    u'\ufffe'   #  0x93 -> UNDEFINED
    u'\ufffe'   #  0x94 -> UNDEFINED
    u'\ufffe'   #  0x95 -> UNDEFINED
    u'\ufffe'   #  0x96 -> UNDEFINED
    u'\ufffe'   #  0x97 -> UNDEFINED
    u'\ufffe'   #  0x98 -> UNDEFINED
    u'\ufffe'   #  0x99 -> UNDEFINED
    u'\ufffe'   #  0x9A -> UNDEFINED
    u'\ufffe'   #  0x9B -> UNDEFINED
    u'\ufffe'   #  0x9C -> UNDEFINED
    u'\ufffe'   #  0x9D -> UNDEFINED
    u'\ufffe'   #  0x9E -> UNDEFINED
    u'\ufffe'   #  0x9F -> UNDEFINED
    u'\ufffe'   #  0xA0 -> UNDEFINED
    u'\ufffe'   #  0xA1 -> UNDEFINED
    u'\ufffe'   #  0xA2 -> UNDEFINED
    u'\ufffe'   #  0xA3 -> UNDEFINED
    u'\ufffe'   #  0xA4 -> UNDEFINED
    u'\ufffe'   #  0xA5 -> UNDEFINED
    u'\ufffe'   #  0xA6 -> UNDEFINED
    u'\ufffe'   #  0xA7 -> UNDEFINED
    u'\ufffe'   #  0xA8 -> UNDEFINED
    u'\ufffe'   #  0xA9 -> UNDEFINED
    u'\ufffe'   #  0xAA -> UNDEFINED
    u'\ufffe'   #  0xAB -> UNDEFINED
    u'\ufffe'   #  0xAC -> UNDEFINED
    u'\ufffe'   #  0xAD -> UNDEFINED
    u'\ufffe'   #  0xAE -> UNDEFINED
    u'\ufffe'   #  0xAF -> UNDEFINED
    u'\ufffe'   #  0xB0 -> UNDEFINED
    u'\ufffe'   #  0xB1 -> UNDEFINED
    u'\ufffe'   #  0xB2 -> UNDEFINED
    u'\ufffe'   #  0xB3 -> UNDEFINED
    u'\ufffe'   #  0xB4 -> UNDEFINED
    u'\ufffe'   #  0xB5 -> UNDEFINED
    u'\ufffe'   #  0xB6 -> UNDEFINED
    u'\ufffe'   #  0xB7 -> UNDEFINED
    u'\ufffe'   #  0xB8 -> UNDEFINED
    u'\ufffe'   #  0xB9 -> UNDEFINED
    u'\ufffe'   #  0xBA -> UNDEFINED
    u'\ufffe'   #  0xBB -> UNDEFINED
    u'\ufffe'   #  0xBC -> UNDEFINED
    u'\ufffe'   #  0xBD -> UNDEFINED
    u'\ufffe'   #  0xBE -> UNDEFINED
    u'\ufffe'   #  0xBF -> UNDEFINED
    u'\ufffe'   #  0xC0 -> UNDEFINED
    u'\ufffe'   #  0xC1 -> UNDEFINED
    u'\ufffe'   #  0xC2 -> UNDEFINED
    u'\ufffe'   #  0xC3 -> UNDEFINED
    u'\ufffe'   #  0xC4 -> UNDEFINED
    u'\ufffe'   #  0xC5 -> UNDEFINED
    u'\ufffe'   #  0xC6 -> UNDEFINED
    u'\ufffe'   #  0xC7 -> UNDEFINED
    u'\ufffe'   #  0xC8 -> UNDEFINED
    u'\ufffe'   #  0xC9 -> UNDEFINED
    u'\ufffe'   #  0xCA -> UNDEFINED
    u'\ufffe'   #  0xCB -> UNDEFINED
    u'\ufffe'   #  0xCC -> UNDEFINED
    u'\ufffe'   #  0xCD -> UNDEFINED
    u'\ufffe'   #  0xCE -> UNDEFINED
    u'\ufffe'   #  0xCF -> UNDEFINED
    u'\ufffe'   #  0xD0 -> UNDEFINED
    u'\ufffe'   #  0xD1 -> UNDEFINED
    u'\ufffe'   #  0xD2 -> UNDEFINED
    u'\ufffe'   #  0xD3 -> UNDEFINED
    u'\ufffe'   #  0xD4 -> UNDEFINED
    u'\ufffe'   #  0xD5 -> UNDEFINED
    u'\ufffe'   #  0xD6 -> UNDEFINED
    u'\ufffe'   #  0xD7 -> UNDEFINED
    u'\ufffe'   #  0xD8 -> UNDEFINED
    u'\ufffe'   #  0xD9 -> UNDEFINED
    u'\ufffe'   #  0xDA -> UNDEFINED
    u'\ufffe'   #  0xDB -> UNDEFINED
    u'\ufffe'   #  0xDC -> UNDEFINED
    u'\ufffe'   #  0xDD -> UNDEFINED
    u'\ufffe'   #  0xDE -> UNDEFINED
    u'\ufffe'   #  0xDF -> UNDEFINED
    u'\ufffe'   #  0xE0 -> UNDEFINED
    u'\ufffe'   #  0xE1 -> UNDEFINED
    u'\ufffe'   #  0xE2 -> UNDEFINED
    u'\ufffe'   #  0xE3 -> UNDEFINED
    u'\ufffe'   #  0xE4 -> UNDEFINED
    u'\ufffe'   #  0xE5 -> UNDEFINED
    u'\ufffe'   #  0xE6 -> UNDEFINED
    u'\ufffe'   #  0xE7 -> UNDEFINED
    u'\ufffe'   #  0xE8 -> UNDEFINED
    u'\ufffe'   #  0xE9 -> UNDEFINED
    u'\ufffe'   #  0xEA -> UNDEFINED
    u'\ufffe'   #  0xEB -> UNDEFINED
    u'\ufffe'   #  0xEC -> UNDEFINED
    u'\ufffe'   #  0xED -> UNDEFINED
    u'\ufffe'   #  0xEE -> UNDEFINED
    u'\ufffe'   #  0xEF -> UNDEFINED
    u'\ufffe'   #  0xF0 -> UNDEFINED
    u'\ufffe'   #  0xF1 -> UNDEFINED
    u'\ufffe'   #  0xF2 -> UNDEFINED
    u'\ufffe'   #  0xF3 -> UNDEFINED
    u'\ufffe'   #  0xF4 -> UNDEFINED
    u'\ufffe'   #  0xF5 -> UNDEFINED
    u'\ufffe'   #  0xF6 -> UNDEFINED
    u'\ufffe'   #  0xF7 -> UNDEFINED
    u'\ufffe'   #  0xF8 -> UNDEFINED
    u'\ufffe'   #  0xF9 -> UNDEFINED
    u'\ufffe'   #  0xFA -> UNDEFINED
    u'\ufffe'   #  0xFB -> UNDEFINED
    u'\ufffe'   #  0xFC -> UNDEFINED
    u'\ufffe'   #  0xFD -> UNDEFINED
    u'\ufffe'   #  0xFE -> UNDEFINED
    u'\ufffe'   #  0xFF -> UNDEFINED
)

encoding_table=codecs.charmap_build(decoding_table)


if __name__ == "__main__":
    """
    Run this as a script for poor-man's unit tests

    """
    isoLatin15_alpha=u" !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJLKMNOPQRSTUVWXYZ[\\]^-`abcdefghijklmnopqrstuvwxyz{|}~¡¢£€¥Š§š©ª«¬®¯°±²³Žµ¶·ž¹º»ŒœŸ¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ"

    gsm_alpha=u"\u00A0@£$¥èéùìòçØøÅåΔ_ΦΓΛΩΠΨΣΘΞ^{}\\[~]|\u00A0\u00A0€ÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà\u00A0"

    gsm_alpha_encoded='1b000102030405060708090b0c0e0f101112131415161718191a1b141b281b291b2f1b3c1b3d1b3e1b401b1b1b651c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f1b'

    gsm_alpha_gsm=gsm_alpha_encoded.decode('hex')


    # some simple tests
    print "Assert GSM alphabet, encoded in GSM is correct (unicode->gsm_str)..."
    encoded=_encode(gsm_alpha)[0].encode('hex')
    print encoded
    assert(encoded==gsm_alpha_encoded)
    print "Good"
    print
    print "Assert GSM encoded string converts to correct Unicode (gsm_str->unicode)..."
    assert(_decode(gsm_alpha_gsm)[0]==gsm_alpha)
    print "Good"
    print

    # test Codec objects
    print "Try the codec objects unicode_test_str->encode->decode==unicode_test_str..."
    c=Codec()
    gsm_str,out=c.encode(gsm_alpha)
    assert(c.decode(gsm_str)[0]==gsm_alpha)
    print "Good"
    print
    print "Try the incremental codecs, same test, but loop it..."

    def _inc_encode(ie):
        encoded=list()
        hop=17 # make it something odd
        final=False
        for i in range(0,len(gsm_alpha),hop):
            end=i+hop
            if end>=len(gsm_alpha): final=True
            encoded.append(ie.encode(gsm_alpha[i:end],final))
        return ''.join(encoded)

    enc=IncrementalEncoder()            
    assert(_inc_encode(enc)==gsm_alpha_gsm)
    print "Good"
    print
    print "Now do that again with the same encoder to make sure state is reset..."
    enc.reset()
    assert(_inc_encode(enc)==gsm_alpha_gsm)
    print "Good"
    print
    print "Now decode the encoded string back to unicode..."

    def _inc_decode(idec):
        decoded=list()
        # define so we KNOW we hit a mark as last char
        hop=gsm_alpha_gsm.index('\x1b')+1
        final=False
        for i in range(0,len(gsm_alpha_gsm),hop):
            end=i+hop
            if end>=len(gsm_alpha_gsm): final=True
            decoded.append(idec.decode(gsm_alpha_gsm[i:end],final))
        return ''.join(decoded)

    dec=IncrementalDecoder()
    assert(_inc_decode(dec)==gsm_alpha)
    print "Good"
    print
    print "Do it again with some decoder to make sure state is cleared..."
    dec.reset()
    assert(_inc_decode(dec)==gsm_alpha)
    print "Good"
    print
    

########NEW FILE########
__FILENAME__ = gsmmodem
#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8


from __future__ import with_statement

# debian/ubuntu: apt-get install python-tz

import re
import time
import errors
import threading
import gsmcodecs
from devicewrapper import DeviceWrapper
from pdusmshandler import PduSmsHandler
from textsmshandler import TextSmsHandler

class GsmModem(object):
    """pyGSM is a Python module which uses pySerial to provide a nifty
       interface to send and receive SMS via a GSM Modem. It was ported
       from RubyGSM, and provides (almost) all of the same features. It's
       easy to get started:

          # create a GsmModem object:
          >>> import pygsm
          >>> modem = pygsm.GsmModem(port="/dev/ttyUSB0")

          # harass Evan over SMS:
          # (try to do this before 11AM)
          >>> modem.send_sms("+13364130840", "Hey, wake up!")

          # check for incoming SMS:
          >>> print modem.next_message()
          <pygsm.IncomingMessage from +13364130840: "Leave me alone!">


       There are various ways of polling for incoming messages -- a choice
       which has been deliberately left to the application author (unlike
       RubyGSM). Execute `python -m pygsm.gsmmodem` to run this example:

          # connect to the modem
          modem = pygsm.GsmModem(port=sys.argv[1])

          # check for new messages every two
          # seconds for the rest of forever
          while True:
              msg = modem.next_message()

              # we got a message! respond with
              # something useless, as an example
              if msg is not None:
                  msg.respond("Thanks for those %d characters!" %
                      len(msg.text))

              # no messages? wait a couple
              # of seconds and try again
              else: time.sleep(2)


       pyGSM is distributed via GitHub:
       http://github.com/adammck/pygsm

       Bugs reports (especially for
       unsupported devices) are welcome:
       http://github.com/adammck/pygsm/issues"""


    # override these after init, and
    # before boot. they're not sanity
    # checked, so go crazy.
    cmd_delay = 0.1
    retry_delay = 2
    max_retries = 10
    modem_lock = threading.RLock()
    
    
    def __init__(self, *args, **kwargs):
        """Creates, connects to, and boots a GSM Modem. All of the arguments
           are optional (although "port=" should almost always be provided),
           and passed along to serial.Serial.__init__ verbatim. For all of
           the possible configration options, see:

           http://pyserial.wiki.sourceforge.net/pySerial#tocpySerial10

           Alternatively, a single "device" kwarg can be passed, which overrides
           the default proxy-args-to-pySerial behavior. This is useful when testing,
           or wrapping the serial connection with some custom logic."""

        if "logger" in kwargs:
            self.logger = kwargs.pop("logger")
        
        mode = "PDU"
        if "mode" in kwargs:
            mode = kwargs.pop("mode")
        
        # if a ready-made device was provided, store it -- self.connect
        # will see that we're already connected, and do nothing. we'll
        # just assume it quacks like a serial port
        if "device" in kwargs:
            self.device = kwargs.pop("device")

            # if a device is given, the other args are never
            # used, so were probably included by mistake.
            if len(args) or len(kwargs):
                raise(TypeError("__init__() does not accept other arguments when a 'device' is given"))

        # for regular serial connections, store the connection args, since
        # we might need to recreate the serial connection again later
        else:
            self.device_args = args
            self.device_kwargs = kwargs

        # to cache parts of multi-part messages
        # until the last part is delivered
        self.multipart = {}

        # to store unhandled incoming messages
        self.incoming_queue = []
        
        if mode.lower() == "text":
            self.smshandler = TextSmsHandler(self)
        else:
            self.smshandler = PduSmsHandler(self)
        # boot the device on init, to fail as
        # early as possible if it can't be opened
        self.boot()
    
    
    LOG_LEVELS = {
        "traffic": 4,
        "read":    4,
        "write":   4,
        "debug":   3,
        "warn":    2,
        "error":   1 }
    
    
    def _log(self, str_, type_="debug"):
        """Proxies a log message to this Modem's logger, if one has been set.
           This is useful for applications embedding pyGSM that wish to show
           or log what's going on inside.

           The *logger* should be a function with three arguments:
             modem:   a reference to this GsmModem instance
             message: the log message (a unicode string)
             type:    a string contaning one of the keys
                      of GsmModem.LOG_LEVELS, indicating
                      the importance of this message.

           GsmModem.__init__ accepts an optional "logger" kwarg, and a minimal
           (dump to STDOUT) logger is available at GsmModem.logger:

           >>> GsmModem("/dev/ttyUSB0", logger=GsmModem.logger)"""
        
        if hasattr(self, "logger"):
            self.logger(self, str_, type_)
    
    
    @staticmethod
    def logger(_modem, message_, type_):
        print "%8s %s" % (type_, message_)
    
    
    def connect(self, reconnect=False):
        """Creates the connection to the modem via pySerial, optionally
           killing and re-creating any existing connection."""
           
        self._log("Connecting")
        
        # if no connection exists, create it
        # the reconnect flag is irrelevant
        if not hasattr(self, "device") or (self.device is None):
            with self.modem_lock:
                self.device = DeviceWrapper(
                    self.logger, *self.device_args,
                    **self.device_kwargs)
                
        # the port already exists, but if we're
        # reconnecting, then kill it and recurse
        # to recreate it. this is useful when the
        # connection has died, but nobody noticed
        elif reconnect:
            
            self.disconnect()
            self.connect(False)

        return self.device


    def disconnect(self):
        """Disconnects from the modem."""
        
        self._log("Disconnecting")
        
        # attempt to close and destroy the device
        if hasattr(self, "device") and (self.device is not None):
            with self.modem_lock:
                if self.device.isOpen():
                    self.device.close()
                    self.device = None
                    return True
        
        # for some reason, the device
        # couldn't be closed. it probably
        # just isn't open yet
        return False


    def set_modem_config(self):
        """initialize the modem configuration with settings needed to process
           commands and send/receive SMS.
        """
        
        # set some sensible defaults, to make
        # the various modems more consistant
        self.command("ATE0",      raise_errors=False) # echo off
        self.command("AT+CMEE=1", raise_errors=False) # useful error messages
        self.command("AT+WIND=0", raise_errors=False) # disable notifications
        self.command("AT+CSMS=1", raise_errors=False) # set SMS mode to phase 2+
        self.command(self.smshandler.get_mode_cmd()      ) # make sure in PDU mode

        # enable new message notification
        self.command(
            "AT+CNMI=2,2,0,0,0",
            raise_errors=False)


    def boot(self, reboot=False):
        """Initializes the modem. Must be called after init and connect,
           but before doing anything that expects the modem to be ready."""
        
        self._log("Booting")
        
        if reboot:
            # If reboot==True, force a reconnection and full modem reset. SLOW
            self.connect(reconnect=True)
            self.command("AT+CFUN=1")
        else:
            # else just verify connection
            self.connect()

        # In both cases, reset the modem's config
        self.set_modem_config()        

        # And check for any waiting messages PRIOR to setting
        # the CNMI call--this is not supported by all modems--
        # in which case we catch the exception and plow onward
        try:
            self._fetch_stored_messages()
        except errors.GsmError:
            pass


    def reboot(self):
        """Forces a reconnect to the serial port and then a full modem reset to factory
           and reconnect to GSM network. SLOW.
        """
        self.boot(reboot=True)


    def _write(self, str):
        """Write a string to the modem."""
        
        self._log(repr(str), "write")

        try:
            self.device.write(str)

        # if the device couldn't be written to,
        # wrap the error in something that can
        # sensibly be caught at a higher level
        except OSError, err:
            raise(errors.GsmWriteError)

    def _parse_incoming_sms(self, lines):
        """Parse a list of lines (the output of GsmModem._wait), to extract any
           incoming SMS and append them to GsmModem.incoming_queue. Returns the
           same lines with the incoming SMS removed. Other unsolicited data may
           remain, which must be cropped separately."""

        output_lines = []
        n = 0

        # iterate the lines like it's 1984
        # (because we're patching the array,
        # which is hard work for iterators)
        while n < len(lines):

            # not a CMT string? add it back into the
            # output (since we're not interested in it)
            # and move on to the next
            if lines[n][0:5] != "+CMT:":
                output_lines.append(lines[n])
                n += 1
                continue

            msg_line = lines[n+1].strip()

            # notify the network that we accepted
            # the incoming message (for read receipt)
            # BEFORE pushing it to the incoming queue
            # (to avoid really ugly race condition if
            # the message is grabbed from the queue
            # and responded to quickly, before we get
            # a chance to issue at+cnma)
            try:
                self.command("AT+CNMA")

            # Some networks don't handle notification, in which case this
            # fails. Not a big deal, so ignore.
            except errors.GsmError:
                #self.log("Receipt acknowledgement (CNMA) was rejected")
                # TODO: also log this!
                pass

            msg = self.smshandler.parse_incoming_message(lines[n], msg_line)
            if msg is not None:
                self.incoming_queue.append(msg)

            # jump over the CMT line, and the
            # pdu line, and continue iterating
            n += 2
 
        # return the lines that we weren't
        # interested in (almost all of them!)
        return output_lines
        
    def command(self, cmd, read_term=None, read_timeout=None, write_term="\r", raise_errors=True):
        """Issue a single AT command to the modem, and return the sanitized
           response. Sanitization removes status notifications, command echo,
           and incoming messages, (hopefully) leaving only the actual response
           from the command.
           
           If Error 515 (init or command in progress) is returned, the command
           is automatically retried up to _GsmModem.max_retries_ times."""

        # keep looping until the command
        # succeeds or we hit the limit
        retries = 0
        while retries < self.max_retries:
            try:

                # issue the command, and wait for the
                # response
                with self.modem_lock:
                    self._write(cmd + write_term)
                    lines = self.device.read_lines(
                        read_term=read_term,
                        read_timeout=read_timeout)
                    
                # no exception was raised, so break
                # out of the enclosing WHILE loop
                break

            # Outer handler: if the command caused an error,
            # maybe wrap it and return None
            except errors.GsmError, err:
                # if GSM Error 515 (init or command in progress) was raised,
                # lock the thread for a short while, and retry. don't lock
                # the modem while we're waiting, because most commands WILL
                # work during the init period - just not _cmd_
                if getattr(err, "code", None) == 515:
                    time.sleep(self.retry_delay)
                    retries += 1
                    continue

                # if raise_errors is disabled, it doesn't matter
                # *what* went wrong - we'll just ignore it
                if not raise_errors:
                    return None

                # otherwise, allow errors to propagate upwards,
                # and hope someone is waiting to catch them
                else: 
                    raise(err)

        # if the first line of the response echoes the cmd
        # (it shouldn't, if ATE0 worked), silently drop it
        if lines[0] == cmd:
            lines.pop(0)

        # remove all blank lines and unsolicited
        # status messages. i can't seem to figure
        # out how to reliably disable them, and
        # AT+WIND=0 doesn't work on this modem
        lines = [
            line
            for line in lines
            if line      != "" or\
               line[0:6] == "+WIND:" or\
               line[0:6] == "+CREG:" or\
               line[0:7] == "+CGRED:"]

        # parse out any incoming sms that were bundled
        # with this data (to be fetched later by an app)
        lines = self._parse_incoming_sms(lines)

        # rest up for a bit (modems are
        # slow, and get confused easily)
        time.sleep(self.cmd_delay)

        return lines


    def query(self, cmd, prefix=None):
        """Issues a single AT command to the modem, and returns the relevant
           part of the response. This only works for commands that return a
           single line followed by "OK", but conveniently, this covers almost
           all AT commands that I've ever needed to use.

           For all other commands, returns None."""

        # issue the command, which might return incoming
        # messages, but we'll leave them in the queue
        out = self.command(cmd)

        # the only valid response to a "query" is a
        # single line followed by "OK". if all looks
        # well, return just the single line
        if(len(out) == 2) and (out[-1] == "OK"):
            if prefix is None:
                return out[0].strip()

            # if a prefix was provided, check that the
            # response starts with it, and return the
            # cropped remainder
            else:
                if out[0][:len(prefix)] == prefix:
                    return out[0][len(prefix):].strip()

        # something went wrong, so return the very
        # ambiguous None. it's better than blowing up
        return None


    def send_sms(self, recipient, text, max_messages = 255):
        """
        Sends an SMS to _recipient_ containing _text_. 

        Method will automatically split long 'text' into
        multiple SMSs up to max_messages.

        To enforce only a single SMS, set max_messages=1
        
        If max_messages > 255 it is forced to 255
        If max_messages < 1 it is forced to 1

        Raises 'ValueError' if text will not fit in max_messages
        
        NOTE: Only PDU mode respects max_messages! It has no effect in TEXT mode

        """
        mm = 255
        try:
            mm = int(max_messages)
        except:
            # dunno what type mm was, so just leave at deafult 255
            pass
        
        if mm > 255:
            mm = 255
        elif mm < 1:
            mm = 1
        
        with self.modem_lock:
            self.smshandler.send_sms(recipient, text, mm)
        return True

    def break_out_of_prompt(self):
        self._write(chr(27))

    def hardware(self):
        """Returns a dict of containing information about the physical
           modem. The contents of each value are entirely manufacturer
           dependant, and vary wildly between devices."""

        return {
            "manufacturer": self.query("AT+CGMI"),
            "model":        self.query("AT+CGMM"),
            "revision":     self.query("AT+CGMR"),
            "serial":       self.query("AT+CGSN") }


    def signal_strength(self):
        """Returns an integer between 1 and 99, representing the current
           signal strength of the GSM network, False if we don't know, or
           None if the modem can't report it."""

        data = self.query("AT+CSQ")
        md = re.match(r"^\+CSQ: (\d+),", data)

        # 99 represents "not known or not detectable". we'll
        # return False for that (so we can test it for boolean
        # equality), or an integer of the signal strength.
        if md is not None:
            csq = int(md.group(1))
            return csq if csq < 99 else False

        # the response from AT+CSQ couldn't be parsed. return
        # None, so we can test it in the same way as False, but
        # check the type without raising an exception
        return None


    def wait_for_network(self):
        """Blocks until the signal strength indicates that the
           device is active on the GSM network. It's a good idea
           to call this before trying to send or receive anything."""

        while True:
            csq = self.signal_strength()
            if csq: return csq
            time.sleep(1)


    def ping(self):
        """Sends the "AT" command to the device, and returns true
           if it is acknowledged. Since incoming notifications and
           messages are intercepted automatically, this is a good
           way to poll for new messages without using a worker
           thread like RubyGSM."""

        try:
            self.command("AT")
            return True

        except errors.GsmError:
            return None


    def _strip_ok(self,lines):
        """Strip 'OK' from end of command response"""
        if lines is not None and len(lines)>0 and \
                lines[-1]=='OK':
            lines=lines[:-1] # strip last entry
        return lines


    def _fetch_stored_messages(self):
        """
        Fetch stored messages with CMGL and add to incoming queue
        Return number fetched
        
        """    
        lines = self.command('AT+CMGL=%s' % self.smshandler.CMGL_STATUS)
        lines = self._strip_ok(lines)
        messages = self.smshandler.parse_stored_messages(lines)
        for msg in messages:
            self.incoming_queue.append(msg)

    def next_message(self, ping=True, fetch=True):
        """Returns the next waiting IncomingMessage object, or None if the
           queue is empty. The optional _ping_ and _fetch_ parameters control
           whether the modem is pinged (to allow new messages to be delivered
           instantly, on those modems which support it) and queried for unread
           messages in storage, which can both be disabled in case you're
           already polling in a separate thread."""

        # optionally ping the modem, to give it a
        # chance to deliver any waiting messages
        if ping:
            self.ping()

        # optionally check the storage for unread messages.
        # we must do this just as often as ping, because most
        # handsets don't support CNMI-style delivery
        if fetch:
            self._fetch_stored_messages()

        # abort if there are no messages waiting
        if not self.incoming_queue:
            return None

        # remove the message that has been waiting
        # longest from the queue, and return it
        return self.incoming_queue.pop(0)


if __name__ == "__main__":

    import sys
    if len(sys.argv) >= 2:

        # the first argument is SERIAL PORT
        # (required, since we have no autodetect yet)
        port = sys.argv[1]

        # all subsequent options are parsed as key=value
        # pairs, to be passed on to GsmModem.__init__ as
        # kwargs, to configure the serial connection
        conf = dict([
            arg.split("=", 1)
            for arg in sys.argv[2:]
            if arg.find("=") > -1
        ])

        # dump the connection settings
        print "pyGSM Demo App"
        print "  Port: %s" % (port)
        print "  Config: %r" % (conf)
        print

        # connect to the modem (this might hang
        # if the connection settings are wrong)
        print "Connecting to GSM Modem..."
        modem = GsmModem(port=port, **conf)
        print "Waiting for incoming messages..."

        # check for new messages every two
        # seconds for the rest of forever
        while True:
            msg = modem.next_message()

            # we got a message! respond with
            # something useless, as an example
            if msg is not None:
                print "Got Message: %r" % msg
                msg.respond("Received: %d characters '%s'" %
                    (len(msg.text),msg.text))

            # no messages? wait a couple
            # of seconds and try again
            else: 
                time.sleep(2)

    # the serial port must be provided
    # we're not auto-detecting, yet
    else:
        print "Usage: python -m pygsm.gsmmodem PORT [OPTIONS]"

########NEW FILE########
__FILENAME__ = gsmpdu
#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8


from __future__ import with_statement

import re, datetime
import math
import pytz
import codecs
import gsmcodecs
import threading

MSG_LIMITS = {
    # 'encoding', (max_normal, max_csm)
    'gsm': (160,152),
    'ucs2': (70,67)
}
MAX_CSM_SEGMENTS = 255

# used to track csm reference numbers per receiver
__csm_refs = {}
__ref_lock = threading.Lock()

def get_outbound_pdus(text, recipient):
    """
    Returns a list of PDUs to send the provided
    text to the given recipient.

    If everything fits in one message, the list
    will have just one PDU.

    Otherwise is will be a list of Concatenated SM PDUs

    If the message goes beyond the max length for a CSM
    (it's gotta be _REALLY BIG_), this will raise a 'ValueError'

    """

    # first figure out the encoding
    # if 'gsm', encode it to account for
    # multi-byte char length
    encoding = 'ucs2'
    try:
        encoded_text = text.encode('gsm')
        encoding = 'gsm'
    except:
        encoded_text = text

    csm_max = MSG_LIMITS[encoding][1]
    if len(encoded_text)>(MAX_CSM_SEGMENTS*csm_max):
        raise ValueError('Message text too long')

    # see if we are under the single PDU limit
    if len(encoded_text)<=MSG_LIMITS[encoding][0]:
        return [OutboundGsmPdu(text, recipient)]

    # ok, we are a CSM, so lets figure out
    # the parts
    
    # get our ref
    with __ref_lock:
        if recipient not in __csm_refs:
            __csm_refs[recipient]=0
        csm_ref = __csm_refs[recipient] % 256
        __csm_refs[recipient]+=1

    # make the PDUs
    num = int(math.ceil(len(encoded_text)/float(MSG_LIMITS[encoding][0])))
    pdus=[]
    for seq in range(num):
        i = seq*csm_max
        seg_txt = encoded_text[i:i+csm_max]
        if encoding=='gsm':
            # a little silly to encode, decode, then have PDU
            # re-encode but keeps PDU API clean
            seg_txt = seg_txt.decode('gsm')
        pdus.append(
            OutboundGsmPdu(
                seg_txt,
                recipient,
                csm_ref=csm_ref,
                csm_seq=seq+1,
                csm_total=num
                )
            )

    return pdus


class SmsParseException(Exception):
    pass

class SmsEncodeException(Exception):
    pass

class GsmPdu(object):
    def __init__(self):
        self.is_csm = False
        self.csm_seq = None
        self.csm_total = None
        self.csm_ref = None
        self.address = None
        self.text = None
        self.pdu_string = None
        self.sent_ts = None

    def dump(self):
        """
        Return a useful multiline rep of self

        """
        header='Addressee: %s\nLength: %s\nSent %s' % \
            (self.address, len(self.text), self.sent_ts)
        csm_info=''
        if self.is_csm:
            csm_info='\nCSM: %d of %d for Ref# %d' % (self.csm_seq, self.csm_total,self.csm_ref)
        return '%s%s\nMessage: \n%s\nPDU: %s' % (header, csm_info,self.text,self.pdu_string)


class OutboundGsmPdu(GsmPdu):
    """
    Formatted outbound PDU. Basically just
    a struct.
  
    Don't instantiate directly! Use 'get_outbound_pdus()'
    which will return a list of PDUs needed to
    send the message

    """
    
    def __init__(self, text, recipient, csm_ref=None, csm_seq=None, csm_total=None):
        GsmPdu.__init__(self)

        self.address = recipient
        self.text = text
        self.gsm_text = None # if we are gsm, put the gsm encoded str here
        self.is_csm = csm_ref is not None
        self.csm_ref = ( None if csm_ref is None else int(csm_ref) )
        self.csm_seq = ( None if csm_seq is None else int(csm_seq) )
        self.csm_total = ( None if csm_total is None else int(csm_total) )
        
        try:
            # following does two things:
            # 1. Raises exception if text cannot be encoded GSM
            # 2. measures the number of chars after encoding
            #    since GSM is partially multi-byte, a string
            #    in GSM can be longer than the obvious num of chars
            #    e.g. 'hello' is 5 but 'hello^' is _7_
            self.gsm_text=self.text.encode('gsm')
            num_chars=len(self.gsm_text)
        except:
            num_chars=len(self.text)

        if self.is_csm:
            max = MSG_LIMITS[self.encoding][1]
        else:
            max = MSG_LIMITS[self.encoding][0]
            
        if num_chars>max:
            raise SmsEncodeException('Text length too great')
        
    @property
    def encoding(self):
        return ( 'gsm' if self.is_gsm else 'ucs2' )

    @property
    def is_gsm(self):
        return self.gsm_text is not None

    @property
    def is_ucs2(self):
        return not self.is_gsm
        
    def __get_pdu_string(self):
        # now put the PDU string together
        # first octet is SMSC info, 00 means get from stored on SIM
        pdu=['00'] 
        # Next is 'SMS-SUBMIT First Octet' -- '11' means submit w/validity. 
        # '51' means Concatendated SM w/validity
        pdu.append('51' if self.is_csm else '11') 
        # Next is 'message' reference. '00' means phone can set this
        pdu.append('00')
        # now recipient number, first type
        if self.address[0]=='+':
            num = self.address[1:]
            type = '91' # international
        else:
            num = self.address
            type = 'A8' # national number
            
        # length
        num_len = len(num)
        # twiddle it
        num = _twiddle(num, False)
        pdu.append('%02X' % num_len) # length
        pdu.append(type)
        pdu.append(num)
            
        # now protocol ID
        pdu.append('00')
            
        # data coding scheme
        pdu.append('00' if self.is_gsm else '08')

        # validity period, just default to 4 days
        pdu.append('AA')

        # Now the fun! Make the user data (the text message)
        # Complications:
        # 1. If we are a CSM, need the CSM header
        # 2. If we are a CSM and GSM, need to pad the data
        padding = 0
        udh=''
        if self.is_csm:
            # data header always starts the same:
            # length: 5 octets '05'
            # type: CSM '00'
            # length of CSM info, 3 octets '03'
            udh='050003%02X%02X%02X' % (self.csm_ref, self.csm_total, self.csm_seq)

            if self.is_gsm:
                # padding is number of pits to pad-out beyond
                # the header to make everything land on a '7-bit' 
                # boundary rather than 8-bit.
                # Can calculate as 7 - (UDH*8 % 7), but the UDH
                # is always 48, so padding is always 1
                padding = 1
                
        # now encode contents
        encoded_sm = ( 
            _pack_septets(self.gsm_text, padding=padding)
            if self.is_gsm 
            else self.text.encode('utf_16_be') 
            )
        encoded_sm = encoded_sm.encode('hex').upper()

        # and get the data length which is in septets
        # if GSM, and octets otherwise
        if self.is_gsm:
            # just take length of encoded gsm text
            # as each char becomes a septet when encoded
            udl = len(self.gsm_text)
            if len(udh)>0:
                udl+=7 # header is always 7 septets (inc. padding)
        else:
            # in this case just the byte length of content + header
            udl = (len(encoded_sm)+len(udh))/2
            
        # now add it all to the pdu
        pdu.append('%02X' % udl)
        pdu.append(udh)
        pdu.append(encoded_sm)
        return ''.join(pdu)
    
    def __set_pdu_string(self, val):
        pass
    pdu_string=property(__get_pdu_string, __set_pdu_string)
                
class ReceivedGsmPdu(GsmPdu):
    """
    A nice little class to parse a PDU and give you useful
    properties.

    Maybe one day it will let you set text and sender info and 
    ask it to write itself out as a PDU!

    """
    def __init__(self, pdu_str):
        GsmPdu.__init__(self)
        
        # hear are the properties that are set below in the 
        # ugly parse code. 

        self.tp_mms = False # more messages to send
        self.tp_sri = False # status report indication
        self.address = None # phone number of sender as string
        self.sent_ts = None # Datetime of when SMSC stamped the message, roughly when sent
        self.text = None # string of message contents
        self.pdu_string = pdu_str.upper() # original data as a string
        self.is_csm = False # is this one of a sequence of concatenated messages?
        self.csm_ref = 0 # reference number
        self.csm_seq = 0 # this chunks sequence num, 1-based
        self.csm_total = 0 # number of chunks total
        self.encoding = None # either 'gsm' or 'ucs2'

        self.__parse_pdu()

    
    """
    This is truly hideous, just don't look below this line!
    
    It's times like this that I miss closed-compiled source...

    """

    def __parse_pdu(self):
        pdu=self.pdu_string # make copy
        
        # grab smsc header, and throw away
        # length is held in first octet
        smsc_len,pdu=_consume_one_int(pdu)

        # consume smsc header
        c,pdu=_consume(pdu, smsc_len)

        # grab the deliver octect
        deliver_attrs,pdu=_consume_one_int(pdu)

        if deliver_attrs & 0x03 != 0:
            raise SmsParseException("Not a SMS-DELIVER, we ignore")

        self.tp_mms=deliver_attrs & 0x04 # more messages to send
        self.tp_sri=deliver_attrs & 0x20 # Status report indication
        tp_udhi=deliver_attrs & 0x40 # There is a user data header in the user data portion
        # get the sender number. 
        # First the length which is given in 'nibbles' (half octets)
        # so divide by 2 and round up for odd
        sender_dec_len,pdu=_consume_one_int(pdu)
        sender_len=int(math.ceil(sender_dec_len/2.0))
        
        # next is sender id type
        sender_type,pdu=_consume(pdu,1)

        # now the number itself, (unparsed)
        num,pdu=_consume(pdu,sender_len)

        # now parse the number
        self.address=_parse_phone_num(sender_type,num)

        # now the protocol id
        # we only understand SMS (0)
        tp_pid,pdu=_consume_one_int(pdu)
        if tp_pid >= 32:
            # can't deal
            print "TP PID: %s" % tp_pid
            raise SmsParseException("Not SMS protocol, bailing")

        # get and interpet DCS (char encoding info)
        self.encoding,pdu=_consume(pdu,1,_read_dcs)
        if self.encoding not in ['gsm','ucs2']:
            raise SmsParseException("Don't understand short message encoding")

        #get and interpret timestamp
        self.sent_ts,pdu=_consume(pdu,7,_read_ts)

        # ok, how long is ud? 
        # note, if encoding is GSM this is num 7-bit septets
        # if ucs2, it's num bytes
        udl,pdu=_consume_one_int(pdu)

        # Now to deal with the User Data header!
        if tp_udhi:
            # yup, we got one, probably part of a 'concatenated short message',
            # what happens when you type too much text and your phone sends
            # multiple SMSs
            #
            # in fact this is the _only_ case we care about
            
            # get the header length
            udhl,pdu=_consume_decimal(pdu)
            
            # now loop through consuming the header
            # and looking to see if we are a csm
            i=0
            while i<udhl:
                # get info about the element
                ie_type,pdu=_consume_one_int(pdu)
                ie_l,pdu=_consume_decimal(pdu) 
                ie_d,pdu=_consume(pdu,ie_l)
                i+=(ie_l+2) # move index up for all bytes read
                if ie_type == 0x00:
                    # got csm info!
                    self.is_csm=True
                    (ref,self.csm_total,self.csm_seq),r=_consume_bytes(ie_d,3)
                    self.csm_ref=ref % 256 # the definition is 'modulo 256'
        # ok, done with header

        # now see if we are gsm, in which case we need to unpack bits
        if self.encoding=='gsm':
            # if we had a data header, we need to figure out padding
            if tp_udhi:
                # num septets * 7 bits minus
                # 8 * header length (+1 for length indicator octet)
                # mod'd by 7 to git the number of leftover padding bits
                padding=((7*udl) - (8*(udhl+1))) % 7
            else:
                padding=0

            # now decode
            try:
                self.text=_unpack_septets(pdu, padding).decode('gsm')
            except Exception, ex:
                # we have bogus data! But don't die
                # as we are used deeply embedded
                raise SmsParseException('GSM encoded data is invalid')

        else:
            # we are just good old UCS2
            # problem is, we don't necessarily know the byte order
            # some phones include it, some--including some
            # popular Nokia's _don't_, in which case it
            # seems they use big-endian...
        
            bom=pdu[0:4]
            decoded_text = ''
            if bom==codecs.BOM_UTF16_LE.encode('hex'):
                decoded_text=pdu[4:].decode('hex').decode('utf_16_le')
            else:
                decoded_text=pdu.decode('hex').decode('utf_16_be')
            self.text=decoded_text
        # some phones add a leading <cr> so strip it
        self.text=self.text.strip()

#
# And all the ugly helper functions
#

def _read_dcs(dcs):
    # make an int for masking
    dcs=int(dcs,16)

    # for an SMS, as opposed to a 'voice mail waiting'
    # indicator, first 4-bits must be zero
    if dcs & 0xf0 != 0:
        # not an SMS!
        return None

    dcs &= 0x0c # mask off everything but bits 3&2
    if dcs==0:
        return 'gsm'
    elif dcs==8:
        return 'ucs2'

    # not a type we know about, but should never get here
    return None

def _B(slot):
    """Convert slot to Byte boundary"""
    return slot*2

def _consume(seq, num,func=None):
    """
    Consume the num of BYTES

    return a tuple of (consumed,remainder)

    func -- a function to call on the consumed. Result in tuple[0]
    
    """
    num=_B(num)
    c=seq[:num]
    r=seq[num:]
    if func:
        c=func(c)
    return (c,r)

def _consume_decimal(seq):
    """read 2 chars as a decimal"""
    return (int(seq[0:2],10),seq[2:])

def _consume_one_int(seq):
    """
    Consumes one byte and returns int and remainder
    (int, remainder_of_seq)
    
    """
    
    ints,remainder = _consume_bytes(seq,1)
    return (ints[0],remainder)
    
def _consume_bytes(seq,num=1):
    """
    consumes bytes for num ints (e.g. 2-chars per byte)
    coverts to int, returns tuple of  ([byte...], remainder)
       
    """
    
    bytes=[]
    for i in range(0,_B(num),2):
        bytes.append(int(seq[i:i+2],16))
    
    return (bytes,seq[_B(num):])

def _twiddle(seq, decode=True):
    seq=seq.upper() # just in case
    result=list()
    for i in range(0,len(seq)-1,2):
        result.extend((seq[i+1],seq[i]))
    
    if len(result)<len(seq) and not decode:
        # encoding odd length
        result.extend(('F',seq[-1]))
    elif decode and result[-1:][0]=='F':
        # strip trailing 'F'
        result.pop()

    return ''.join(result)

def _parse_phone_num(num_type,seq):
    if num_type[0]=='D':
        # it's gsm encoded!
        return _unpack_septets(seq).decode('gsm')

    # sender number is encoded in DECIMAL with each octect swapped, and 
    # padded to even length with F
    # so 1 415 555 1212 is: 41 51 55 15 12 f2
    num=_twiddle(seq)

    intl_code=''
    if num_type[0]=='9':
        intl_code='+'
    return '%s%s' % (intl_code,num)

def _chop(seq,how_much):
    """chops the number of octets given off front of seq"""
    return seq[_B(how_much):]

TS_MATCHER=re.compile(r'^(..)(..)(..)(..)(..)(..)(..)$')
TZ_SIGN_MASK=0x08

def _read_ts(seq):

    ts=_twiddle(seq)
    m = TS_MATCHER.match(ts)
    if m is None:
        print "TS not valid: %s" % ts
        return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
    
    yr,mo,dy,hr,mi,se=[int(g) for g in m.groups()[:-1]]

    # handle time-zone separately to deal with
    # the MSB bit for negative
    tz = int(m.groups()[-1],16)
    neg = False
    if tz>0x80:
        neg = True
        tz-=0x80
    # now convert BACK to dec rep,
    # I know, ridiculous, but that's
    # the format...
    tz = int('%02X' % tz)
    tz_offset = tz/4
    if neg:
        tz_offset = -tz_offset
    tz_delta = datetime.timedelta(hours=tz_offset)
        
    # year is 2 digit! Yeah! Y2K problem again!!
    if yr<90:
        yr+=2000
    else:
        yr+=1900

    # python sucks with timezones, 
    # so create UTC not using this offset
    dt = None
    try:
        # parse TS and adjust for TZ to get into UTC
        dt = datetime.datetime(yr,mo,dy,hr,mi,se, tzinfo=pytz.utc) - tz_delta 
    except ValueError, ex:
        #  Timestamp was bogus, set it to UTC now
        dt =  datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
   
    return dt

def _to_binary(n):
    s = ""
    for i in range(8):
        s = ("%1d" % (n & 1)) + s
        n >>= 1
    return s

def _unpack_septets(seq,padding=0):
    """ 
    this function taken from:
    http://offog.org/darcs/misccode/desms.py

    Thank you Adam Sampson <ats@offog.org>!
    """

    # Unpack 7-bit characters
    msgbytes,r = _consume_bytes(seq,len(seq)/2)
    msgbytes.reverse()
    asbinary = ''.join(map(_to_binary, msgbytes))
    if padding != 0:
        asbinary = asbinary[:-padding]
    chars = []
    while len(asbinary) >= 7:
        chars.append(int(asbinary[-7:], 2))
        asbinary = asbinary[:-7]
    return "".join(map(chr, chars))

def _pack_septets(str, padding=0):
    bytes=[ord(c) for c in str]
    bytes.reverse()
    asbinary = ''.join([_to_binary(b)[1:] for b in bytes])
    # add padding
    for i in range(padding):
        asbinary+='0'
    
    # zero extend last octet if needed
    extra = len(asbinary) % 8
    if extra>0:
        for i in range(8-extra):
            asbinary='0'+asbinary
        
    # convert back to bytes
    bytes=[]
    for i in range(0,len(asbinary),8):
        bytes.append(int(asbinary[i:i+8],2))
    bytes.reverse()
    return ''.join([chr(b) for b in bytes])

if __name__ == "__main__":
    # poor man's unit tests
    
    pdus = [
        "0791227167830001040C912271479288270600902132210403001D31D90CE40E87E9F4FAF9CD06B9C3E6F75B5EA6BFE7F4B01B0402"
        "07912180958729F6040B814151733717F500009011709055902B0148",
        "07912180958729F6400B814151733717F500009070208044148AA0050003160201986FF719C47EBBCF20F6DB7D06B1DFEE3388FD769F41ECB7FB0C62BFDD6710FBED3E83D8ECB73B0D62BFDD67109BFD76A741613719C47EBBCF20F6DB7D06BCF61BC466BF41ECF719C47EBBCF20F6D",
        "07912180958729F6440B814151733717F500009070207095828AA00500030E0201986FF719C47EBBCF20F6DB7D06B1DFEE3388FD769F41ECB7FB0C62BFDD6710FBED3E83D8ECB7",
        "07912180958729F6040B814151733717F500009070103281418A09D93728FFDE940303",
        "07912180958729F6040B814151733717F500009070102230438A02D937",
        "0791227167830001040C912271271640910008906012024514001C002E004020AC00A300680065006C006C006F002000E900EC006B00F0",
       "07917283010010F5040BC87238880900F10000993092516195800AE8329BFD4697D9EC37",
        "0791448720900253040C914497035290960000500151614414400DD4F29C9E769F41E17338ED06",
        "0791448720003023440C91449703529096000050015132532240A00500037A020190E9339A9D3EA3E920FA1B1466B341E472193E079DD3EE73D85DA7EB41E7B41C1407C1CBF43228CC26E3416137390F3AABCFEAB3FAAC3EABCFEAB3FAAC3EABCFEAB3FAAC3EABCFEAB3FADC3EB7CFED73FBDC3EBF5D4416D9457411596457137D87B7E16438194E86BBCF6D16D9055D429548A28BE822BA882E6370196C2A8950E291E822BA88",
        "0791448720003023440C91449703529096000050015132537240310500037A02025C4417D1D52422894EE5B17824BA8EC423F1483C129BC725315464118FCDE011247C4A8B44",
        "07914477790706520414D06176198F0EE361F2321900005001610013334014C324350B9287D12079180D92A3416134480E",
        "0791448720003023440C91449703529096000050016121855140A005000301060190F5F31C447F83C8E5327CEE0221EBE73988FE0691CB65F8DC05028190F5F31C447F83C8E5327CEE028140C8FA790EA2BF41E472193E7781402064FD3C07D1DF2072B90C9FBB402010B27E9E83E86F10B95C86CF5D2064FD3C07D1DF2072B90C9FBB40C8FA790EA2BF41E472193E7781402064FD3C07D1DF2072B90C9FBB402010B27E9E83E8",
        "0791448720003023440C91449703529096000050016121850240A0050003010602DE2072B90C9FBB402010B27E9E83E86F10B95C86CF5D201008593FCF41F437885C2EC3E72E100884AC9FE720FA1B442E97E1731708593FCF41F437885C2EC3E72E100884AC9FE720FA1B442E97E17317080442D6CF7310FD0D2297CBF0B90B040221EBE73988FE0691CB65F8DC05028190F5F31C447F83C8E5327CEE028140C8FA790EA2BF41",
      "0791448720003023440C91449703529096000050016121854240A0050003010603C8E5327CEE0221EBE73988FE0691CB65F8DC05028190F5F31C447F83C8E5327CEE028140C8FA790EA2BF41E472193E7781402064FD3C07D1DF2072B90C9FBB402010B27E9E83E86F10B95C86CF5D201008593FCF41F437885C2EC3E72E10B27E9E83E86F10B95C86CF5D201008593FCF41F437885C2EC3E72E100884AC9FE720FA1B442E97E1",
       "0791448720003023400C91449703529096000050016121853340A005000301060540C8FA790EA2BF41E472193E7781402064FD3C07D1DF2072B90C9FBB402010B27E9E83E86F10B95C86CF5D201008593FCF41F437885C2EC3E72E100884AC9FE720FA1B442E97E17317080442D6CF7310FD0D2297CBF0B90B84AC9FE720FA1B442E97E17317080442D6CF7310FD0D2297CBF0B90B040221EBE73988FE0691CB65F8DC05028190",
        "0791448720003023440C914497035290960000500161218563402A050003010606EAE73988FE0691CB65F8DC05028190F5F31C447F83C8E5327CEE0281402010",
        ]
    """
    print
    print '\n'.join([
            p.dump() for p in get_outbound_pdus(
                u'\u5c71hellohello hellohello hellohello hellohello hellohello hellohello hellohello hellohello hellohello hellohello hellohello hellohello hellohello hellohello hellohello hellohello', 
                '+14153773715'
                )
            ])
    """

    for p in pdus:
        print '\n-------- Received ----------\nPDU: %s\n' % p 
        rp = ReceivedGsmPdu(p)
        print rp.dump()
        op = get_outbound_pdus(rp.text, rp.address)[0]
        print '\nOut ------> \n'
        print op.dump()
        print '-----------------------------'

        
        





########NEW FILE########
__FILENAME__ = incoming
#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4


import datetime
import pytz


class IncomingMessage(object):
    def __init__(self, device, sender, sent, text):

        # move the arguments into "private" attrs,
        # to try to prevent from from being modified
        self._device = device
        self._sender = sender
        self._sent   = sent
        self._text   = text

        # assume that the message was
        # received right now, since we
        # don't have an incoming buffer
        self._received = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)


    def __repr__(self):
        return "<pygsm.IncomingMessage from %s: %r>" %\
            (self.sender, self.text)


    def respond(self, text):
        """Responds to this IncomingMessage by sending a message containing
           _text_ back to the sender via the modem that created this object."""
        return self.device.send_sms(self.sender, text)


    @property
    def device(self):
        """Returns the pygsm.GsmModem device which received
           the SMS, and created this IncomingMessage object."""
        return self._device

    @property
    def sender(self):
        """Returns the phone number of the originator of this IncomingMessage.
           It is stored directly as reported by the modem, so no assumptions
           can be made about it's format."""
        return self._sender

    @property
    def sent(self):
        """Returns a datetime object containing the date and time that this
           IncomingMessage was sent, as reported by the modem. Sometimes, a
           network or modem will not report this field, so it will be None."""
        return self._sent

    @property
    def text(self):
        """Returns the text contents of this IncomingMessage. It will usually
           be 160 characters or less, by virtue of being an SMS, but multipart
           messages can, technically, be up to 39015 characters long."""
        return self._text

    @property
    def received(self):
        """Returns a datetime object containing the date and time that this
           IncomingMessage was created, which is a close aproximation of when
           the SMS was received."""
        return self._received

########NEW FILE########
__FILENAME__ = outgoing
#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4


class OutgoingMessage(object):
	pass

########NEW FILE########
__FILENAME__ = pdusmshandler
#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8

import gsmpdu
import traceback
import errors, message
import re
from smshandler import SmsHandler

class PduSmsHandler(SmsHandler):
    CMGL_MATCHER =re.compile(r'^\+CMGL:.*?$')
    CMGL_STATUS="0"
    
    def __init__(self, modem):
        SmsHandler.__init__(self, modem)
    
    def get_mode_cmd(self):
        return "AT+CMGF=0"

    def send_sms(self, recipient, text, max_messages = 255):
        """
        Method will automatically split long 'text' into
        multiple SMSs up to max_messages.
 
        To enforce only a single SMS, set max_messages=1
 
        Raises 'ValueError' if text will not fit in max_messages
        """ 
        pdus = gsmpdu.get_outbound_pdus(text, recipient)
        if len(pdus) > max_messages:
            raise ValueError(
                'Max_message is %d and text requires %d messages' %
                (max_messages, len(pdus))
                )

        for pdu in pdus:
            self._send_pdu(pdu)
        return True
            
    def _send_pdu(self, pdu):
        # outer try to catch any error and make sure to
        # get the modem out of 'waiting for data' mode
        try:
            # accesing the property causes the pdu_string
            # to be generated, so do once and cache
            pdu_string = pdu.pdu_string

            # try to catch write timeouts
            try:
                # content length is in bytes, so half PDU minus
                # the first blank '00' byte
                self.modem.command( 
                'AT+CMGS=%d' % (len(pdu_string)/2 - 1), 
                read_timeout=1
                )

                # if no error is raised within the timeout period,
                # and the text-mode prompt WAS received, send the
                # sms text, wait until it is accepted or rejected
                # (text-mode messages are terminated with ascii char 26
                # "SUBSTITUTE" (ctrl+z)), and return True (message sent)
            except errors.GsmReadTimeoutError, err:
                if err.pending_data[0] == ">":
                    self.modem.command(pdu_string, write_term=chr(26))
                    return True

                    # a timeout was raised, but no prompt nor
                    # error was received. i have no idea what
                    # is going on, so allow the error to propagate
                else:
                    raise

            finally:
                pass

        # for all other errors...
        # (likely CMS or CME from device)
        except Exception:
            traceback.print_exc()
            # whatever went wrong, break out of the
            # message prompt. if this is missed, all
            # subsequent writes will go into the message!
            self.modem.break_out_of_prompt()

            # rule of thumb: pyGSM is meant to be embedded,
            # so DO NOT EVER allow exceptions to propagate
            # (obviously, this sucks. there should be an
            # option, at least, but i'm being cautious)
            return None
    
    def parse_incoming_message(self, header_line, line):
        pdu = None
        try:
            pdu = gsmpdu.ReceivedGsmPdu(line)
        except Exception, ex:
            traceback.print_exc(ex)
            self.modem._log('Error parsing PDU: %s' % line) 

        return self._process_incoming_pdu(pdu)   
    
    def parse_stored_messages(self, lines):
        # loop through all the lines attempting to match CMGL lines (the header)
        # and then match NOT CMGL lines (the content)
        # need to seed the loop first 'cause Python no like 'until' loops
        pdu_lines=[]
        messages = []
        m = None
        if len(lines)>0:
            m=self.CMGL_MATCHER.match(lines[0])

        while len(lines)>0:
            if m is None:
                # couldn't match OR no text data following match
                raise(errors.GsmReadError())

            # if here, we have a match AND text
            # start by popping the header (which we have stored in the 'm'
            # matcher object already)
            lines.pop(0)

            # now loop through, popping content until we get
            # the next CMGL or out of lines
            while len(lines)>0:
                m=self.CMGL_MATCHER.match(lines[0])
                if m is not None:
                    # got another header, get out
                    break
                else:
                    # HACK: For some reason on the multitechs the first
                    # PDU line has the second '+CMGL' response tacked on
                    # this may be a multitech bug or our bug in 
                    # reading the responses. For now, split the response
                    # on +CMGL
                    line = lines.pop(0)
                    line, cmgl, rest = line.partition('+CMGL')
                    if len(cmgl)>0:
                        lines.insert(0,'%s%s' % (cmgl,rest))
                    pdu_lines.append(line)

            # now create and process PDUs
            for pl in pdu_lines:
                try:
                    pdu = gsmpdu.ReceivedGsmPdu(pl)
                    msg = self._process_incoming_pdu(pdu)
                    if msg is not None:
                        messages.append(msg)

                except Exception, ex:
                    traceback.print_exc(ex)
                    self.modem._log('Error parsing PDU: %s' % pl) # TODO log

        return messages
        
    def _incoming_pdu_to_msg(self, pdu):
        if pdu.text is None or len(pdu.text)==0:
            self.modem._log('Blank inbound text, ignoring')
            return
        
        msg = message.IncomingMessage(self,
                                      pdu.address,
                                      pdu.sent_ts,
                                      pdu.text)
        return msg

    def _process_incoming_pdu(self, pdu):
        if pdu is None:
            return None

        # is this a multi-part (concatenated short message, csm)?
        if pdu.is_csm:
            # process pdu will either
            # return a 'super' pdu with the entire
            # message (if this is the last segment)
            # or None if there are more segments coming
            pdu = self._process_csm(pdu)
 
        if pdu is not None:
            return self._incoming_pdu_to_msg(pdu)
        return None

    def _process_csm(self, pdu):
        if not pdu.is_csm:
            return pdu

        # self.multipart is a dict of dicts of dicts
        # holding all parts of messages by sender
        # e.g. { '4155551212' : { 0: { seq1: pdu1, seq2: pdu2{ } }
        #
        if pdu.address not in self.multipart:
            self.multipart[pdu.address]={}

        sender_msgs=self.multipart[pdu.address]
        if pdu.csm_ref not in sender_msgs:
            sender_msgs[pdu.csm_ref]={}

        # these are all the pdus in this 
        # sequence we've recived
        received = sender_msgs[pdu.csm_ref]
        received[pdu.csm_seq]=pdu
        
        # do we have them all?
        if len(received)==pdu.csm_total:
            pdus=received.values()
            pdus.sort(key=lambda x: x.csm_seq)
            text = ''.join([p.text for p in pdus])
            
            # now make 'super-pdu' out of the first one
            # to hold the full text
            super_pdu = pdus[0]
            super_pdu.csm_seq = 0
            super_pdu.csm_total = 0
            super_pdu.pdu_string = None
            super_pdu.text = text
            super_pdu.encoding = None
        
            del sender_msgs[pdu.csm_ref]
            
            return super_pdu
        else:
            return None

########NEW FILE########
__FILENAME__ = smshandler
#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8

import re

ERR_MSG = "Must use one of concrete subclasses:PduSmsHandler or TextSmsHandler"

class SmsHandler(object):
    
    def __init__(self,modem):
        self.modem = modem
        self.multipart = {}

    def send_sms(self, recipient, text, max_messages = 255):
        """
        Note: Only PDU mode handler respects 'max_messages'
        
        """
        raise Exception(ERR_MSG)
    
    def get_mode_cmd(self):
        raise Exception(ERR_MSG)
    
    # returns a list of messages
    def parse_stored_messages(self, lines):
        raise Exception(ERR_MSG)

    # returns a single message   
    def parse_incoming_message(self, header_line, line):
        raise Exception(ERR_MSG)
########NEW FILE########
__FILENAME__ = textsmshandler
#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8

import errors, traceback, message
import re, datetime, time
import StringIO
import pytz
from smshandler import SmsHandler

class TextSmsHandler(SmsHandler):
    SCTS_FMT = "%y/%m/%d,%H:%M:%S"
    CMGL_MATCHER=re.compile(r'^\+CMGL: (\d+),"(.+?)","(.+?)",*?,"(.+?)".*?$')
    CMGL_STATUS='"REC UNREAD"'
    
    def __init__(self, modem):
        SmsHandler.__init__(self, modem)
    
    def get_mode_cmd(self):
        return "AT+CMGF=1"
        
    def send_sms(self, recipient, text, max_messages = 255):
        """Sends an SMS to _recipient_ containing _text_. Some networks
           will automatically chunk long messages into multiple parts,
           and reassembled them upon delivery, but some will silently
           drop them. At the moment, pyGSM does nothing to avoid this,
           so try to keep _text_ under 160 characters.
           
           Currently 'max_messages' is ignored
        """

        old_mode = None
        try:
            try:
                # cast the text to a string, to check that
                # it doesn't contain non-ascii characters
                try:
                    text = str(text)

                # uh-oh. unicode ahoy
                except UnicodeEncodeError:

                    # fetch and store the current mode (so we can
                    # restore it later), and override it with UCS2
                    csmp = self.modem.query("AT+CSMP?", "+CSMP:")
                    if csmp is not None:
                        old_mode = csmp.split(",")
                        mode = old_mode[:]
                        mode[3] = "8"

                        # enable hex mode, and set the encoding
                        # to UCS2 for the full character set
                        self.modem.command('AT+CSCS="HEX"')
                        self.modem.command("AT+CSMP=%s" % ",".join(mode))
                        text = text.encode("utf-16").encode("hex")

                # initiate the sms, and give the device a second
                # to raise an error. unfortunately, we can't just
                # wait for the "> " prompt, because some modems
                # will echo it FOLLOWED BY a CMS error
                result = self.modem.command(
                        'AT+CMGS=\"%s\"' % (recipient),
                        read_timeout=1)

            # if no error is raised within the timeout period,
            # and the text-mode prompt WAS received, send the
            # sms text, wait until it is accepted or rejected
            # (text-mode messages are terminated with ascii char 26
            # "SUBSTITUTE" (ctrl+z)), and return True (message sent)
            except errors.GsmReadTimeoutError, err:
                if err.pending_data[0] == ">":
                    self.modem.command(text, write_term=chr(26))
                    return True

                # a timeout was raised, but no prompt nor
                # error was received. i have no idea what
                # is going on, so allow the error to propagate
                else:
                    raise

        # for all other errors...
        # (likely CMS or CME from device)
        except Exception, err:
            traceback.print_exc(err)
            # whatever went wrong, break out of the
            # message prompt. if this is missed, all
            # subsequent writes will go into the message!
            self.modem.break_out_of_prompt()

            # rule of thumb: pyGSM is meant to be embedded,
            # so DO NOT EVER allow exceptions to propagate
            # (obviously, this sucks. there should be an
            # option, at least, but i'm being cautious)
            return None

        finally:

            # if the mode was overridden above, (if this
            # message contained unicode), switch it back
            if old_mode is not None:
                self.modem.command("AT+CSMP=%s" % ",".join(old_mode))
                self.modem.command('AT+CSCS="GSM"')
        return True

    # returns a list of messages
    def parse_stored_messages(self, lines):
        # loop through all the lines attempting to match CMGL lines (the header)
        # and then match NOT CMGL lines (the content)
        # need to seed the loop first
        messages = []
        if len(lines)>0:
            m=self.CMGL_MATCHER.match(lines[0])

        while len(lines)>0:
            if m is None:
                # couldn't match OR no text data following match
                raise(errors.GsmReadError())

            # if here, we have a match AND text
            # start by popping the header (which we have stored in the 'm'
            # matcher object already)
            lines.pop(0)

            # now put the captures into independent vars
            index, status, sender, timestamp = m.groups()

            # now loop through, popping content until we get
            # the next CMGL or out of lines
            msg_buf=StringIO.StringIO()
            while len(lines)>0:
                m=self.CMGL_MATCHER.match(lines[0])
                if m is not None:
                    # got another header, get out
                    break
                else:
                    msg_buf.write(lines.pop(0))

            # get msg text
            msg_text=msg_buf.getvalue().strip()

            # now create message
            messages.append(self._incoming_to_msg(timestamp,sender,msg_text))
        return messages

    # returns a single message   
    def parse_incoming_message(self, header_line, text):
        # since this line IS a CMT string (an incoming
        # SMS), parse it and store it to deal with later
        m = re.match(r'^\+CMT: "(.+?)",.*?,"(.+?)".*?$', header_line)
        sender = ""
        timestamp = None
        if m is not None:

            # extract the meta-info from the CMT line,
            # and the message from the FOLLOWING line
            sender, timestamp = m.groups()

        # multi-part messages begin with ASCII 130 followed
        # by "@" (ASCII 64). TODO: more docs on this, i wrote
        # this via reverse engineering and lost my notes
        if (ord(text[0]) == 130) and (text[1] == "@"):
            part_text = text[7:]
            
            # ensure we have a place for the incoming
            # message part to live as they are delivered
            if sender not in self.multipart:
                self.multipart[sender] = []

            # append THIS PART
            self.multipart[sender].append(part_text)

            # abort if this is not the last part
            if ord(text[5]) != 173:
                return None
            
            # last part, so switch out the received
            # part with the whole message, to be processed
            # below (the sender and timestamp are the same
            # for all parts, so no change needed there)
            text = "".join(self.multipart[sender])
            del self.multipart[sender]

        return self._incoming_to_msg(timestamp, sender, text)
            
    def _incoming_to_msg(self, timestamp, sender, text):

        # since neither message notifications nor messages
        # fetched from storage give any indication of their
        # encoding, we're going to have to guess. if the
        # text has a multiple-of-four length and starts
        # with a UTF-16 Byte Order Mark, try to decode it
        # into a unicode string
        try:
            if (len(text) % 4 == 0) and (len(text) > 0):
                bom = text[:4].lower()
                if bom == "fffe"\
                or bom == "feff":
                    
                    # decode the text into a unicode string,
                    # so developers embedding pyGSM need never
                    # experience this confusion and pain
                    text = text.decode("hex").decode("utf-16")

        # oh dear. it looked like hex-encoded utf-16,
        # but wasn't. who sends a message like that?!
        except:
            pass

        # create and store the IncomingMessage object
        time_sent = None
        if timestamp is not None:
            time_sent = self._parse_incoming_timestamp(timestamp)
        return message.IncomingMessage(self, sender, time_sent, text)
         
    def _parse_incoming_timestamp(self, timestamp):
        """Parse a Service Center Time Stamp (SCTS) string into a Python datetime
           object, or None if the timestamp couldn't be parsed. The SCTS format does
           not seem to be standardized, but looks something like: YY/MM/DD,HH:MM:SS."""

        # timestamps usually have trailing timezones, measured
        # in 15-minute intervals (?!), which is not handled by
        # python's datetime lib. if _this_ timezone does, chop
        # it off, and note the actual offset in minutes
        tz_pattern = r"([-+])(\d+)$"
        m = re.search(tz_pattern, timestamp)
        if m is not None:
            timestamp = re.sub(tz_pattern, "", timestamp)
            tz_offset = datetime.timedelta(minutes=int(m.group(2)) * 15)
            if m.group(1)=='-':
                tz_offset = -tz_offset

        # we won't be modifying the output, but
        # still need an empty timedelta to subtract
        else: 
            tz_offset = datetime.timedelta()

        # attempt to parse the (maybe modified) timestamp into
        # a time_struct, and convert it into a datetime object
        try:
            time_struct = time.strptime(timestamp, self.SCTS_FMT)
            dt = datetime.datetime(*time_struct[:6])
            dt.replace(tzinfo=pytz.utc)
           
            # patch the time to represent UTC, since
            dt-=tz_offset
            return dt

        # if the timestamp couldn't be parsed, we've encountered
        # a format the pyGSM doesn't support. this sucks, but isn't
        # important enough to explode like RubyGSM does
        except ValueError:
            traceback.print_exc()
            return None

########NEW FILE########
__FILENAME__ = run_tests
#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4

import os
import sys
import re
import unittest

DIR_PATH = os.curdir
EXTRA_PATHS = [
  DIR_PATH,
  os.path.join(DIR_PATH, 'lib'),
  os.path.join(DIR_PATH, 'test', 'messages'),
  os.path.join(DIR_PATH, 'test')
]

TEST_FILE_PATTERN = re.compile('([a-z]+_)+test\.py$')

def callback( arg, dirname, fnames ):
    for file in fnames:
		fullpath = os.path.join(dirname,file)
		if os.path.isfile(fullpath) and TEST_FILE_PATTERN.match(file, 1):
			files.append(file.replace('.py', ''))

if __name__ == '__main__':
  sys.path = EXTRA_PATHS + sys.path
  print sys.path
  files = []
  os.path.walk(os.path.join(DIR_PATH, 'test'),callback,files)
  loader = unittest.TestLoader()
  suite = unittest.TestSuite()
  for f in files:
	print f
	suite.addTests(loader.loadTestsFromName(f))
  unittest.TextTestRunner(verbosity=2).run(suite)
  		

########NEW FILE########
__FILENAME__ = gsmmodem_test
#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4


import unittest
import pygsm

from mock.device import MockDevice, MockSenderDevice


class TestModem(unittest.TestCase):
    
    def testMaxMessageArgs(self):
        # this device is much more complicated than
        # most, so is tucked away in mock.device
        device = MockSenderDevice()
        gsmPDU = pygsm.GsmModem(device=device, mode="PDU")
        gsmTEXT = pygsm.GsmModem(device=device, mode="TEXT")

        for gsm in (gsmPDU, gsmTEXT):
            # test with no max_message arg
            gsm.send_sms("1234", "Test Message")
            self.assertEqual(device.sent_messages[0]["recipient"], "21")
            self.assertEqual(device.sent_messages[0]["text"], "00110004A821430000AA0CD4F29C0E6A96E7F3F0B90C")
            
            # test with reasonable max_message arg, should have no impact
            gsm.send_sms("1234", "Test Message", max_messages = 20)
            self.assertEqual(device.sent_messages[0]["recipient"], "21")
            self.assertEqual(device.sent_messages[0]["text"], "00110004A821430000AA0CD4F29C0E6A96E7F3F0B90C")
            
            # test with max_message = 0, should internally set to 1 with no problems
            gsm.send_sms("1234", "Test Message", -1)
            self.assertEqual(device.sent_messages[0]["recipient"], "21")
            self.assertEqual(device.sent_messages[0]["text"], "00110004A821430000AA0CD4F29C0E6A96E7F3F0B90C")
            
            # test with max_message > 255, should internally force to 255
            gsm.send_sms("1234", "Test Message", 1024)
            self.assertEqual(device.sent_messages[0]["recipient"], "21")
            self.assertEqual(device.sent_messages[0]["text"], "00110004A821430000AA0CD4F29C0E6A96E7F3F0B90C")
            
        # test with max_message = 1 and message too long to fit
        # should throw a value exception
        #
        # ONLY SUPPORTED IN PDU MODE, so run on PDU configured gsmmodem only
        msg="""
        0123456789012345678901234567890123456789012345678901234567890123456789
        0123456789012345678901234567890123456789012345678901234567890123456789
        0123456789012345678901234567890123456789012345678901234567890123456789
        0123456789012345678901234567890123456789012345678901234567890123456789
        0123456789012345678901234567890123456789012345678901234567890123456789
        0123456789012345678901234567890123456789012345678901234567890123456789
        0123456789012345678901234567890123456789012345678901234567890123456789
        """
        try:
            gsmPDU.send_sms("1234", msg, max_messages=1)
        except ValueError:
            print "ValueError caught"
        else:
            # Should have thrown an error!
            self.assertTrue(False) # SMS too big should throw ValueError

    def testSendSmsPDUMode(self):
        """Checks that the GsmModem in PDU mode accepts outgoing SMS,
           when the text is within ASCII chars 22 - 126."""

        # this device is much more complicated than
        # most, so is tucked away in mock.device
        device = MockSenderDevice()
        gsm = pygsm.GsmModem(device=device, mode="PDU")

        # send an sms, and check that it arrived safely
        gsm.send_sms("1234", "Test Message")
        self.assertEqual(device.sent_messages[0]["recipient"], "21")
        self.assertEqual(device.sent_messages[0]["text"], "00110004A821430000AA0CD4F29C0E6A96E7F3F0B90C")

    def testSendSmsTextMode(self):
        """Checks that the GsmModem in TEXT mode accepts outgoing SMS,
           when the text is within ASCII chars 22 - 126."""

        # this device is much more complicated than
        # most, so is tucked away in mock.device
        device = MockSenderDevice()
        gsm = pygsm.GsmModem(device=device, mode="TEXT")

        # send an sms, and check that it arrived safely
        gsm.send_sms("1234", "Test Message")
        self.assertEqual(device.sent_messages[0]["recipient"], "1234")
        self.assertEqual(device.sent_messages[0]["text"], "Test Message")

    def testRetryCommands(self):
        """Checks that the GsmModem automatically retries
           commands that fail with a CMS 515 error, and does
           not retry those that fail with other errors."""
        
        class MockBusyDevice(MockDevice):
            def __init__(self):
                MockDevice.__init__(self)
                self.last_cmd = None
                self.retried = []
            
            # this command is special (and totally made up)
            # it does not return 515 errors like the others
            def at_test(self, one):
                return True
            
            def process(self, cmd):
                
                # if this is the first time we've seen
                # this command, return a BUSY error to
                # (hopefully) prompt a retry
                if self.last_cmd != cmd:
                    self._output("+CMS ERROR: 515")
                    self.last_cmd = cmd
                    return None
                
                # the second time, note that this command was
                # retried, then fail. kind of anticlimatic
                self.retried.append(cmd)
                return False
        
        # boot the modem, and make sure that
        # some commands were retried (i won't
        # check _exactly_ how many, since we
        # change the boot sequence often)
        device = MockBusyDevice()
        n = len(device.retried)
        gsm = pygsm.GsmModem(device=device)
        self.assert_(len(device.retried) > n)
        
        # try the special AT+TEST command, which doesn't
        # fail - the number of retries shouldn't change
        n = len(device.retried)
        gsm.command("AT+TEST=1")
        self.assertEqual(len(device.retried), n)
        


    def testEchoOff(self):
        """Checks that GsmModem disables echo at some point
           during boot, to simplify logging and processing."""

        class MockEchoDevice(MockDevice):
            def process(self, cmd):
                
                # raise and error for any
                # cmd other than ECHO OFF
                if cmd != "ATE0":
                    return False
                
                self.echo = False
                return True

        device = MockEchoDevice()
        gsm = pygsm.GsmModem(device=device)
        self.assertEqual(device.echo, False)


    def testUsefulErrors(self):
        """Checks that GsmModem attempts to enable useful errors
           during boot, to make the errors raised useful to humans.
           Many modems don't support this, but it's very useful."""

        class MockUsefulErrorsDevice(MockDevice):
            def __init__(self):
                MockDevice.__init__(self)
                self.useful_errors = False

            def at_cmee(self, error_mode):
                if error_mode == "1":
                    self.useful_errors = True 
                    return True

                elif error_mode == "0":
                    self.useful_errors = False
                    return True

                # invalid mode
                return False

        device = MockUsefulErrorsDevice()
        gsm = pygsm.GsmModem(device=device)
        self.assertEqual(device.useful_errors, True)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = incoming_test
#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4


import unittest
import pygsm


class TestIncomingMessage(unittest.TestCase):
    def testRespond(self):
        """Check that the IncomingMessage calls send_sms (with
           the correct arguments) when .respond is called."""

        caller   = "123"
        in_text  = "alpha"
        out_text = "beta"


        # this mock pygsm.gsmmodem does nothing, except note
        # down the parameters which .send_sms is called with
        class MockGsmModem(object):
            def __init__(self):
                self.sent_sms = []

            def send_sms(self, recipient, text):
                self.sent_sms.append({
                    "recipient": recipient,
                    "text": text
                })

        mock_gsm = MockGsmModem()


        # simulate an incoming message, and a respond to it
        msg = pygsm.message.IncomingMessage(mock_gsm, caller, None, in_text)
        msg.respond(out_text)

        # check that MockDevice.send_sms was called with
        # the correct args by IncomingMessage.respond
        self.assertEqual(mock_gsm.sent_sms[0]["recipient"], caller)
        self.assertEqual(mock_gsm.sent_sms[0]["text"], out_text)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = device
#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4


import time, re
from pygsm import errors

class MockDevice(object):

    print_traffic = False
    read_interval = 0.1
    mode = "PDU" # or TEXT
    echo = True


    def __init__(self):
        self.buf_read = []
        self.buf_write = []
        self.timeout = None


    def _debug(self, str):
        """If self.print_traffic is True, prints
           _str_ to STDOUT. Otherwise, does nothing."""

        if self.print_traffic:
            print str


    def read(self, size=1):
        """Reads and returns _size_ characters from the read buffer, which
           represents the output of the "serial port" of this "modem". This
           method is a very rough port of Serial.write. If the self.timeout
           attribute is set, this method may time out and return only as many
           characters as possible -- just like a modem."""

        waited = 0
        read = ""

        # keep on reading until we have _size_
        # number of characters/bytes
        while len(read) < size:
            if len(self.buf_read):
                read += self.buf_read.pop(0)

            else:
                # there's no data in the buffer. if we've
                # been waiting longer than self.timeout,
                # just return what we have
                if self.timeout and waited > self.timeout:
                    self._debug("TIMEOUT (%d)" % self.timeout)
                    break

                # otherwise, wait for a short while
                # before trying the buffer again
                time.sleep(self.read_interval)
                waited += self.read_interval

        self._debug("READ (%d): %r" % (size, read))
        return read

    def _read(self, read_timeout=None):
        """Read from the modem (blocking) until _terminator_ is hit,
           (defaults to \r\n, which reads a single "line"), and return."""
        
        buffer = []
        read_term = "\r\n"
        self.timeout = read_timeout
        while(True):
            buf = self.read()
            buffer.append(buf)			
            # if a timeout was hit, raise an exception including the raw data that
            # we've already read (in case the calling func was _expecting_ a timeout
            # (wouldn't it be nice if serial.Serial.read returned None for this?)
            if buf == '':
                raise(errors.GsmReadTimeoutError(buffer))

            # if last n characters of the buffer match the read
            # terminator, return what we've received so far
            if ''.join(buffer[-len(read_term):]) == read_term:
                buf_str = ''.join(buffer)
                print 'Read ' + buf_str
                return buf_str

    def read_lines(self, read_term=None, read_timeout=None):
        """Read from the modem (blocking) one line at a time until a response
           terminator ("OK", "ERROR", or "CMx ERROR...") is hit, then return
           a list containing the lines."""
        buffer = []

        # keep on looping until a command terminator
        # is encountered. these are NOT the same as the
        # "read_term" argument - only OK or ERROR is valid
        while(True):
            buf = self._read(read_timeout)

            buf = buf.strip()
            buffer.append(buf)

            # most commands return OK for success, but there
            # are some exceptions. we're not checking those
            # here (unlike RubyGSM), because they should be
            # handled when they're _expected_
            if buf == "OK":
                return buffer

            # some errors contain useful error codes, so raise a
            # proper error with a description from pygsm/errors.py
            m = re.match(r"^\+(CM[ES]) ERROR: (\d+)$", buf)
            if m is not None:
                type, code = m.groups()
                raise(errors.GsmModemError(type, int(code)))

            # ...some errors are not so useful
            # (at+cmee=1 should enable error codes)
            if buf == "ERROR":
                raise(errors.GsmModemError)

    def write(self, str):
        """Appends _str_ to the write buffer, which represents input to this "modem".
           If _str_ ends with a GSM command terminator (\r), the contents of the write
           buffer are passed on to self._process."""

        self._debug("WRITE: %r" % (str))

        # push each character
        # to the write buffer
        for char in str:
            self.buf_write.append(char)

            # if character echo is currently ON, also
            # push this character back to read buffer
            if self.echo:
                self.buf_read.append(char)

        # if the last character is a terminator, process
        # the current contents of the buffer, and clear it.
        # TODO: this doesn't work if "AT\rAT\rAT\r" if passed.
        if self.buf_write[-1] == "\r":
            self._process("".join(self.buf_write))
            self.buf_write = []

        return True


    def _process(self, cmd):
        """Receives a command, and passes it on to self.process, which should be defined
           by subclasses to respond to the command(s) which their testcase is interested
           in, and return True or False when done. If the call succeeds, this method will
           call self._ok -- otherwise, calls self._error."""

        self._debug("CMD: %r" % (cmd))

        def _respond(out):
            """Given the output from a command-handling function,
               injects a status line into the read buffer, to avoid
               repeating it in every handler."""
            
            # boolean values result in OK or ERROR
            # being injected into the read buffer
            if   out == True:  return self._ok()
            elif out == False: return self._error()

            # for any other return value, leave the
            # read buffer alone (we'll assume that
            # the method has injected its own output)
            else: return None

        # we can probably ignore whitespace,
        # even though a modem never would
        cmd = cmd.strip()
        
        # if this command looks like an AT+SOMETHING=VAL string (which most
        # do), check for an at_something method to handle the command. this
        # is bad, since mock modems should handle as little as possible (and
        # return ERROR for everything else), but some commands are _required_
        # (AT+CMGF=1 # switch to text mode) for anything to work.
        m = re.match(r"^AT\+([A-Z]+)=(.+)$", cmd)
        if m is not None:
            key, val = m.groups()
            method = "at_%s" % key.lower()

            # if the value is wrapped in "quotes", remove
            # them. this is sloppy, but we're only mocking
            val = val.strip('"')

            # call the method, and insert OK or ERROR into the
            # read buffer depending on the True/False output
            if hasattr(self, method):
                out = getattr(self, method)(val)
                return _respond(out)

        # attempt to hand off this
        # command to the subclass
        if hasattr(self, "process"):
            out = self.process(cmd)
            return _respond(out)

        # this modem has no "process" method,
        # or it was called and failed. either
        # way, report an unknown error
        return self._error()


    def at_cmgf(self, mode):
        """Switches this "modem" into PDU mode (0) or TEXT mode (1).
           Returns True for success, or False for unrecognized modes."""

        if mode == "0":
            self.mode = "PDU"
            return True

        elif mode == "1":
            self.mode = "TEXT"
            return True

        else:
            self.mode = None
            return False


    def _output(self, str, delimiters=True):
        """Insert a GSM response into the read buffer, with leading and
           trailing terminators (\r\n). This spews whitespace everywhere,
           but is (curiously) how most modems work."""

        def _delimit():
            self.buf_read.extend(["\r", "\n"])

        # add each letter to the buf_read array,
        # optionally surrounded by the delimiters
        if delimiters: _delimit()
        self.buf_read.extend(str)
        if delimiters: _delimit()

        # what could possibly
        # have gone wrong?
        return True


    def _ok(self):
        """Insert a GSM "OK" string into the read buffer.
           This should be called when a command succeeds."""

        self._output("OK")
        return True


    def _error(self):
        """Insert a GSM "ERROR" string into the read buffer.
           This should be called when a command fails."""
        
        self._output("ERROR")
        return False



class MockSenderDevice(MockDevice):
    """This mock device accepts outgoing SMS (in text mode), and stores them in
       self.sent_messages for later retrieval. This functionality is encapsulated
       here, because it's confusing and ugly."""

    def __init__(self):
        MockDevice.__init__(self)
        self.sent_messages = []
        self.recipient = None
        self.message = None


    def _prompt(self):
        """Outputs the message prompt, which indicates that the device
           is currently accepting the text contents of an SMS."""
        self._output("\r\n>", False)
        return None


    def write(self, str):

        # if we are currently writing a message, and
        # ascii 26 (ctrl+z) was hit, it's time to send!
        if self.recipient:
            if str[-1] == chr(26):
                MockDevice.write(self, str[0:-1])
                self.message.append("".join(self.buf_write))
                self.buf_write = []

                # just store this outgoing message to be checked
                # later on. we're not _really_ sending anything
                self.sent_messages.append({
                    "recipient": self.recipient,
                    "text": "\n".join(self.message)
                })

                # confirm that the message was
                # accepted, and clear the state
                self._output("+CMGS: 1")
                self.recipient = None
                self.message = None
                return self._ok()

        # most of the time, invoke the superclass
        return MockDevice.write(self, str)


    def _process(self, cmd):

        # if we're currently building a message,
        # store this line and prompt for the next
        if self.recipient:
            self.message.append(cmd)
            return self._prompt()

        # otherwise, behave normally
        else: MockDevice._process(self, cmd)    


    def at_cmgs(self, recipient):

        # note the recipient's number (to attach to
        # the message when we're finished), and make
        # a space for the text to be collected
        self.recipient = recipient
        self.message = []

        # start prompting for text
        return self._prompt()

########NEW FILE########
__FILENAME__ = pdumode_test
#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4


import unittest
from test_base import TestBase

class PduModeTest(TestBase):
  
    def get_mode(self):
        return 'PDU'
    
    def testSendSmsPduMode(self):
        """Checks that the GsmModem in PDU mode accepts outgoing SMS,
           when the text is within ASCII chars 22 - 126."""
        
        # setup expectation to raise a timeout error with prompt
        self.mockDevice.write("AT+CMGS=21\r").AndRaise(self.read_time_out)
        self.mockDevice.write("00110004A821430000AA0CD4F29C0E6A96E7F3F0B90C\x1a")
        self.mockDevice.read_lines(**self.rl_args).AndReturn(self.ok)
        self.mocker.ReplayAll()
        self.gsm.send_sms("1234", "Test Message")
       
        self.mocker.VerifyAll()
      
    def testSendSmsPduModeError(self):
        """
        Checks that the GsmModem in PDU mode does not send message if error,
        when the text is within ASCII chars 22 - 126.
        
        """

        # setup expectation to raise a non-timeout error with prompt
        self.mockDevice.write("AT+CMGS=21\r").AndRaise(Exception("not timeout"))
        # must see command to break out of command prompt
        self.mockDevice.write("\x1b")
        self.mocker.ReplayAll()
        self.gsm.send_sms("1234", "Test Message")
       
        # must NOT see command (or anything else) with text and terminating char
        self.mocker.VerifyAll()
        
    def testShouldParseIncomingSms(self):
        # verify that ping command AT is issued
        self.mockDevice.write("AT\r")   

        lines = [
                 "+CMT:",
                 "07912180958729F6040B814151733717F500009070102230438A02D937",
                 ] + self.ok
        
        self.mockDevice.read_lines(**self.rl_args).AndReturn(lines)
        # verify that command is issued for read receipt
        self.mockDevice.write("AT+CNMA\r")
        # allow any number of reads
        self.mockDevice.read_lines(**self.rl_args).AndReturn(self.ok)

        self.mocker.ReplayAll()
        pdu = self.gsm.next_message(ping=True,fetch=False)
        self.assertEquals("Yo", pdu.text);
        self.assertEquals("14153773715", pdu.sender);
        self.mocker.VerifyAll()
    
    def testShouldParseIncomingSmsHelloInChinese(self): 
        lines = [
                "+CMT:",
                "07912180958729F8040B814151733717F500089090035194358A044F60597D",
                ] + self.ok
        self.mockDevice.write("AT\r")  
        self.mockDevice.read_lines(**self.rl_args).AndReturn(lines)
        
        # verify that command is issued for read receipt
        self.mockDevice.write("AT+CNMA\r")
        self.mockDevice.read_lines(**self.rl_args).AndReturn(self.ok)
        

        self.mocker.ReplayAll()
        pdu = self.gsm.next_message(ping=True,fetch=False)

        self.assertEquals(u'\u4f60\u597d', pdu.text);
        self.assertEquals("14153773715", pdu.sender);
        self.mocker.VerifyAll()
        
    def testShouldReturnEmptyIfNoStoredMessages(self):
        self.mockDevice.write("AT+CMGL=0\r") 
        self.mockDevice.read_lines(**self.rl_args).AndReturn(self.ok)
        self.mocker.ReplayAll()
        self.assertEquals(None, self.gsm.next_message(ping=False, fetch=True));
        self.mocker.VerifyAll()
        
    def testShouldReturnStoredMessage(self):
        lines = [
                 "+CMGL:",
                 "07912180958729F6040B814151733717F500009070102230438A02D937",
                 ] + self.ok
        self.mockDevice.write("AT+CMGL=0\r") 
        self.mockDevice.read_lines(**self.rl_args).AndReturn(lines)
        self.mocker.ReplayAll()
        pdu = self.gsm.next_message(ping=False,fetch=True)
        self.assertEquals("Yo", pdu.text);
        self.assertEquals("14153773715", pdu.sender);
        # allow any number of reads
        self.mocker.VerifyAll()

    def testShouldHandleMultipartCSMPdus(self):
        lines = [
                 "+CMGL:",
                 "0791448720003023440C91449703529096000050015132532240A00500037A020190E9339A9D3EA3E920FA1B1466B341E472193E079DD3EE73D85DA7EB41E7B41C1407C1CBF43228CC26E3416137390F3AABCFEAB3FAAC3EABCFEAB3FAAC3EABCFEAB3FAAC3EABCFEAB3FADC3EB7CFED73FBDC3EBF5D4416D9457411596457137D87B7E16438194E86BBCF6D16D9055D429548A28BE822BA882E6370196C2A8950E291E822BA88",
                 "0791448720003023440C91449703529096000050015132537240310500037A02025C4417D1D52422894EE5B17824BA8EC423F1483C129BC725315464118FCDE011247C4A8B44"
                 ] + self.ok
        self.mockDevice.write("AT+CMGL=0\r") 
        self.mockDevice.read_lines(**self.rl_args).AndReturn(lines)
        self.mocker.ReplayAll()
        pdu = self.gsm.next_message(ping=False,fetch=True)
        self.assertEquals("Highlight to all deeps ginganutz gir q pete aldx andy gjgjgjgjgjgjgjgjgjgjgjgjgjgjgjgmgmgmgmgmgo.D,d.D.D,d.Mhwpmpdpdpdpngm,d.PKPJHD.D.D.D.FAKAMJDPDGD.D.D.D.D.MDHDNJGEGD.GDGDGDGDMGKD!E,DGMAG BORED", pdu.text);
      
        self.mocker.VerifyAll()

    def testShouldNotCreateMessageIfAllPartsOfCsmPduAreNotReceived(self):
        lines = [
                 "+CMGL:",
                 "07912180958729F6400B814151733717F500009070208044148AA0050003160201986FF719C47EBBCF20F6DB7D06B1DFEE3388FD769F41ECB7FB0C62BFDD6710FBED3E83D8ECB73B0D62BFDD67109BFD76A741613719C47EBBCF20F6DB7D06BCF61BC466BF41ECF719C47EBBCF20F6D"
                ] + self.ok
        self.mockDevice.write("AT+CMGL=0\r") 
        self.mockDevice.read_lines(**self.rl_args).AndReturn(lines)
        self.mocker.ReplayAll()
        pdu = self.gsm.next_message(ping=False,fetch=True)
        self.assertEquals(None, pdu)
      
        self.mocker.VerifyAll()
        
if __name__ == "__main__":
    unittest.main()
    
########NEW FILE########
__FILENAME__ = test_base
#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8

import unittest
import pygsm
import mox

class TestBase(unittest.TestCase):
    mode_map = { 
                'text': 1,
                'pdu': 0 
                }
    
    cmgl_map = {
                'text': '"REC UNREAD"',
                'pdu':'0'
                }
    
    # Some useful constants for the tests
    read_time_out = pygsm.errors.GsmReadTimeoutError(">") 
    rl_args={'read_timeout': mox.IgnoreArg(),
                      'read_term': mox.IgnoreArg()}
    ok = ["","OK"]
    
    def get_mode(self):
        """
        Subclass overrides this to return 'TEXT' or 'PDU'
        
        """
        return None
    
    def setUp(self):
        self.mocker = mox.Mox()
        self.mockDevice = self.mocker.CreateMock(pygsm.devicewrapper.DeviceWrapper)
        
        # verify the config commands
        self.mockDevice.write("ATE0\r")
        self.mockDevice.read_lines(**self.rl_args).AndReturn(self.ok)
        
        self.mockDevice.write("AT+CMEE=1\r")
        self.mockDevice.read_lines(**self.rl_args).AndReturn(self.ok)
       
        self.mockDevice.write("AT+WIND=0\r")
        self.mockDevice.read_lines(**self.rl_args).AndReturn(self.ok)
        
        self.mockDevice.write("AT+CSMS=1\r")
        self.mockDevice.read_lines(**self.rl_args).AndReturn(self.ok)
         
        # must see command to set PDU mode
        mode_int = self.mode_map[self.get_mode().lower()]
        self.mockDevice.write("AT+CMGF=%d\r" % mode_int)
                              
        self.mockDevice.read_lines(**self.rl_args).AndReturn(self.ok)
        
        self.mockDevice.write("AT+CNMI=2,2,0,0,0\r")
        self.mockDevice.read_lines(**self.rl_args).AndReturn(self.ok)
        
        # verify fetch_stored_messages in boot
        cmgl_str = self.cmgl_map[self.get_mode().lower()]
        self.mockDevice.write("AT+CMGL=%s\r" % cmgl_str)
        self.mockDevice.read_lines(**self.rl_args).AndReturn(self.ok)
        
        self.mocker.ReplayAll()
        self.gsm = pygsm.GsmModem(device=self.mockDevice, mode=self.get_mode())
        
        self.mocker.ResetAll()
        

########NEW FILE########
__FILENAME__ = textmode_test
#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4


import unittest
import datetime

from pygsm import errors
from test_base import TestBase

class SendSmsTextModeTest(TestBase):  
    def get_mode(self):
        return 'TEXT'
        
    def testSendSmsTextMode(self):
        """Checks that the GsmModem in Text mode accepts outgoing SMS,
           when the text is within ASCII chars 22 - 126."""        

        self.mockDevice.write("AT+CMGS=\"1234\"\r").AndRaise(self.read_time_out)
        self.mockDevice.write("Test Message\x1a")
        self.mockDevice.read_lines(**self.rl_args).AndReturn(self.ok)
        self.mocker.ReplayAll()
        self.gsm.send_sms("1234", "Test Message")

        self.mocker.VerifyAll()
 
    """    
    def testSendSmsTextModeWithHexUTF16Encoding(self):
        #Checks that the GsmModem in Text mode accepts outgoing SMS,
        #  when the text has Non-ASCII
        
        csmp_response_lines = []
        csmp_response_lines.append("+CSMP:1,2,3,4")
        csmp_response_lines.append("OK")
        err = errors.GsmReadTimeoutError(">")
        when(self.mockDevice).read_lines().thenReturn(csmp_response_lines).thenReturn(self.oklines).thenReturn(self.oklines).thenRaise(err).thenReturn(self.oklines)
        self.gsm.send_sms("1234", u'La Pe\xf1a')
        
        verify(self.mockDevice, times=1).write("AT+CSMP?\r")
        verify(self.mockDevice, times=1).write("AT+CSCS=\"HEX\"\r")
        verify(self.mockDevice, times=1).write("AT+CSMP=1,2,3,8\r")
        
        # must see command with recipient
        verify(self.mockDevice, times=1).write("AT+CMGS=\"1234\"\r")
        # must see command with encoded text and terminating char
        verify(self.mockDevice, times=1).write("fffe4c006100200050006500f1006100\x1a")
        # command to set mode back 
        verify(self.mockDevice, times=1).write("AT+CSMP=1,2,3,4\r")
        verify(self.mockDevice, times=1).write("AT+CSCS=\"GSM\"\r")
        # allow any number of reads
        verify(self.mockDevice, atleast=1).read_lines()
        verifyNoMoreInteractions(self.mockDevice)
    """
        
    def testShouldReturnStoredMessage(self):
        lines = [
                 '+CMGL: 1,"status","14153773715",,"09/09/11,10:10:10"',
                 'Yo'
                 ] + self.ok
        self.mockDevice.write('AT+CMGL="REC UNREAD"\r')        
        self.mockDevice.read_lines(**self.rl_args).AndReturn(lines)
        self.mocker.ReplayAll()
        
        msg = self.gsm.next_message(ping=False)
        self.assertEquals("Yo", msg.text);
        self.assertEquals("14153773715", msg.sender)
        self.assertEquals(datetime.datetime(2009, 9, 11, 10, 10, 10), msg.sent)
        # verify command to fetch_stored_messages
       
        self.mocker.VerifyAll()

    """
    def testShouldReturnHexUTF16EncodedStoredMessage(self):
        lines = []
        lines.append("+CMGL: 1,\"status\",\"14153773715\",,\"09/09/11,10:10:10\"")
        lines.append("Yo".encode("utf-16").encode("hex"))
        when(self.mockDevice).read_lines().thenReturn(lines)
        msg = self.gsm.next_message(ping=False)
        self.assertEquals("Yo", msg.text);
        self.assertEquals("14153773715", msg.sender)
        self.assertEquals(datetime.datetime(2009, 9, 11, 10, 10, 10), msg.sent)
        # verify command to fetch_stored_messages
        verify(self.mockDevice,times=2).write("AT+CMGL=\"REC UNREAD\"\r")
        # allow any number of reads
        verify(self.mockDevice, atleast=1).read_lines()
        
        verifyNoMoreInteractions(self.mockDevice)
    """
    
    def testShouldParseIncomingSms(self):
        lines = [
                 '+CMT: "14153773715",,"09/09/11,10:10:10"',
                 'Yo'
                ] + self.ok

        self.mockDevice.write("AT\r")
        self.mockDevice.read_lines(**self.rl_args).AndReturn(lines)
        self.mockDevice.write("AT+CNMA\r")
        self.mockDevice.read_lines(**self.rl_args).AndReturn(self.ok)
        self.mocker.ReplayAll()
        
        msg = self.gsm.next_message(ping=True,fetch=False)        
        self.assertEquals("Yo", msg.text);
        self.assertEquals("14153773715", msg.sender);
        self.assertEquals(datetime.datetime(2009, 9, 11, 10, 10, 10), msg.sent);
       
        self.mocker.VerifyAll()
    
    def testShouldParseIncomingSmsWithMangledHeader(self):
        lines = [
                 '+CMT: "14153773715",',
                 'Yo'
                ] + self.ok
 
        self.mockDevice.write("AT\r")
        self.mockDevice.read_lines(**self.rl_args).AndReturn(lines)
        self.mockDevice.write("AT+CNMA\r")
        self.mockDevice.read_lines(**self.rl_args).AndReturn(self.ok)
        self.mocker.ReplayAll()
        
        msg = self.gsm.next_message(ping=True,fetch=False) 

        self.assertEquals("Yo", msg.text);
        self.assertEquals("", msg.sender);
        self.assertEquals(None, msg.sent);
        
        self.mocker.VerifyAll()
    
    
    def testShouldParseIncomingMultipartSms(self):
        header = '+CMT: "14153773715",,"09/09/11,10:10:10"'
                 
        # first part of multi-part msg
        lines = [header]
        lines.append(chr(130) + "@" + "ignorfirstpartofmultipart")
        # second part of multi-part msg
        lines.append(header)
        lines.append(chr(130) + "@" + "345" + chr(173) + "7secondpartofmultipart")
        lines.append(self.ok)
        self.mockDevice.write("AT\r")
        self.mockDevice.read_lines(**self.rl_args).AndReturn(lines)
        self.mockDevice.write("AT+CNMA\r")
        self.mockDevice.read_lines(**self.rl_args).AndReturn(self.ok)
        self.mockDevice.write("AT+CNMA\r")
        self.mockDevice.read_lines(**self.rl_args).AndReturn(self.ok)
        self.mocker.ReplayAll()
        
        msg = self.gsm.next_message(ping=True,fetch=False)
       
        self.assertEquals("firstpartofmultipartsecondpartofmultipart", msg.text);
        self.assertEquals("14153773715", msg.sender);
        self.assertEquals(datetime.datetime(2009, 9, 11, 10, 10, 10), msg.sent);
       
        self.mocker.VerifyAll()
        

if __name__ == "__main__":
    unittest.main()
########NEW FILE########
