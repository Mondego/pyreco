__FILENAME__ = C
import os
import sys
import glob
import ctypes
import ctypes.util
import binwalk.core.common
from binwalk.core.compat import *

class Function(object):
    '''
    Container class for defining library functions.
    '''
    def __init__(self, **kwargs):
        self.name = None
        self.type = int

        for (k, v) in iterator(kwargs):
            setattr(self, k, v)

class FunctionHandler(object):
    '''
    Class for abstracting function calls via ctypes and handling Python 2/3 compatibility issues.
    '''
    PY2CTYPES = {
            bytes   : ctypes.c_char_p,
            str     : ctypes.c_char_p,
            int     : ctypes.c_int,
            float   : ctypes.c_float,
            bool    : ctypes.c_int,
            None    : ctypes.c_int,
    }

    RETVAL_CONVERTERS = {
            None    : int,
            int     : int,
            float   : float,
            bool    : bool,
            str     : bytes2str,
            bytes   : str2bytes,
    }
        
    def __init__(self, library, function):
        '''
        Class constructor.

        @library - Library handle as returned by ctypes.cdll.LoadLibrary.
        @function - An instance of the binwalk.core.C.Function class.

        Returns None.
        '''
        self.name = function.name
        self.retype = function.type
        self.function = getattr(library, self.name)

        if has_key(self.PY2CTYPES, self.retype):
            self.function.restype = self.PY2CTYPES[self.retype]
            self.retval_converter = self.RETVAL_CONVERTERS[self.retype]
        else:
            self.function.restype = self.retype
            self.retval_converter = None
            #raise Exception("Unknown return type: '%s'" % self.retype)

    def run(self, *args):
        '''
        Executes the library function, handling Python 2/3 compatibility and properly converting the return type.

        @*args - Library function arguments.

        Returns the return value from the libraray function.
        '''
        args = list(args)

        # Python3 expects a bytes object for char *'s, not a str. 
        # This allows us to pass either, regardless of the Python version.
        for i in range(0, len(args)):
            if isinstance(args[i], str):
                args[i] = str2bytes(args[i])

        retval = self.function(*args)
        if self.retval_converter is not None:
            retval = self.retval_converter(retval)

        return retval
        
class Library(object):
    '''
    Class for loading the specified library via ctypes.
    '''

    def __init__(self, library, functions):
        '''
        Class constructor.

        @library   - Library name (e.g., 'magic' for libmagic).
        @functions - A dictionary of function names and their return types (e.g., {'magic_buffer' : str})

        Returns None.
        '''
        self.library = ctypes.cdll.LoadLibrary(self.find_library(library))
        if not self.library:
            raise Exception("Failed to load library '%s'" % library)

        for function in functions:    
            f = FunctionHandler(self.library, function)
            setattr(self, function.name, f.run)

    def find_library(self, library):
        '''
        Locates the specified library.

        @library - Library name (e.g., 'magic' for libmagic).
 
        Returns a string to be passed to ctypes.cdll.LoadLibrary.
        '''
        lib_path = None
        system_paths = {
            'linux'   : ['/usr/local/lib/lib%s.so' % library],
            'linux2'  : ['/usr/local/lib/lib%s.so' % library],
            'linux3'  : ['/usr/local/lib/lib%s.so' % library],
            'darwin'  : ['/opt/local/lib/lib%s.dylib' % library,
                        '/usr/local/lib/lib%s.dylib' % library,
                       ] + glob.glob('/usr/local/Cellar/lib%s/*/lib/lib%s.dylib' % (library, library)),

            'cygwin'  : ['/usr/local/lib/lib%s.so' % library],
            'win32'   : ['%s.dll' % library]
        }

        # Search the common install directories first; these are usually not in the library search path
        # Search these *first*, since a) they are the most likely locations and b) there may be a
        # discrepency between where ctypes.util.find_library and ctypes.cdll.LoadLibrary search for libs.
        for path in system_paths[sys.platform]:
            if os.path.exists(path):
                lib_path = path
                break

        # If we failed to find the library, check the standard library search paths
        if not lib_path:
            lib_path = ctypes.util.find_library(library)

        # If we still couldn't find the library, error out
        if not lib_path:
            raise Exception("Failed to locate library '%s'" % library)

        binwalk.core.common.debug("Found library: " + lib_path)
        return lib_path


########NEW FILE########
__FILENAME__ = common
# Common functions used throughout various parts of binwalk code.

import io
import os
import re
import sys
import ast
import hashlib
import operator as op
from binwalk.core.compat import *

# This allows other modules/scripts to subclass BlockFile from a custom class. Defaults to io.FileIO.
if has_key(__builtins__, 'BLOCK_FILE_PARENT_CLASS'):
    BLOCK_FILE_PARENT_CLASS = __builtins__['BLOCK_FILE_PARENT_CLASS']
else:
    BLOCK_FILE_PARENT_CLASS = io.FileIO

# The __debug__ value is a bit backwards; by default it is set to True, but
# then set to False if the Python interpreter is run with the -O option.
if not __debug__:
    DEBUG = True
else:
    DEBUG = False

def debug(msg):
    '''
    Displays debug messages to stderr only if the Python interpreter was invoked with the -O flag.
    '''
    if DEBUG:
        sys.stderr.write("DEBUG: " + msg + "\n")
        sys.stderr.flush()

def warning(msg):
    '''
    Prints warning messages to stderr
    '''
    sys.stderr.write("\nWARNING: " + msg + "\n")

def error(msg):
    '''
    Prints error messages to stderr
    '''
    sys.stderr.write("\nERROR: " + msg + "\n")

def file_md5(file_name):
    '''
    Generate an MD5 hash of the specified file.
    
    @file_name - The file to hash.

    Returns an MD5 hex digest string.
    '''
    md5 = hashlib.md5()

    with open(file_name, 'rb') as f:
        for chunk in iter(lambda: f.read(128*md5.block_size), b''):
            md5.update(chunk)

    return md5.hexdigest()

def file_size(filename):
    '''
    Obtains the size of a given file.

    @filename - Path to the file.

    Returns the size of the file.
    '''
    # Using open/lseek works on both regular files and block devices
    fd = os.open(filename, os.O_RDONLY)
    try:
        return os.lseek(fd, 0, os.SEEK_END)
    except KeyboardInterrupt as e:
        raise e
    except Exception as e:
        raise Exception("file_size failed to obtain the size of '%s': %s" % (filename, str(e)))
    finally:
        os.close(fd)

def strip_quoted_strings(string):
    '''
    Strips out data in between double quotes.
    
    @string - String to strip.

    Returns a sanitized string.
    '''
    # This regex removes all quoted data from string.
    # Note that this removes everything in between the first and last double quote.
    # This is intentional, as printed (and quoted) strings from a target file may contain 
    # double quotes, and this function should ignore those. However, it also means that any 
    # data between two quoted strings (ex: '"quote 1" you won't see me "quote 2"') will also be stripped.
    return re.sub(r'\"(.*)\"', "", string)

def get_quoted_strings(string):
    '''
    Returns a string comprised of all data in between double quotes.

    @string - String to get quoted data from.

    Returns a string of quoted data on success.
    Returns a blank string if no quoted data is present.
    '''
    try:
        # This regex grabs all quoted data from string.
        # Note that this gets everything in between the first and last double quote.
        # This is intentional, as printed (and quoted) strings from a target file may contain 
        # double quotes, and this function should ignore those. However, it also means that any 
        # data between two quoted strings (ex: '"quote 1" non-quoted data "quote 2"') will also be included.
        return re.findall(r'\"(.*)\"', string)[0]
    except KeyboardInterrupt as e:
        raise e
    except Exception:
        return ''

def unique_file_name(base_name, extension=''):
    '''
    Creates a unique file name based on the specified base name.

    @base_name - The base name to use for the unique file name.
    @extension - The file extension to use for the unique file name.

    Returns a unique file string.
    '''
    idcount = 0
    
    if extension and not extension.startswith('.'):
        extension = '.%s' % extension

    fname = base_name + extension

    while os.path.exists(fname):
        fname = "%s-%d%s" % (base_name, idcount, extension)
        idcount += 1

    return fname

def strings(filename, minimum=4):
    '''
    A strings generator, similar to the Unix strings utility.

    @filename - The file to search for strings in.
    @minimum  - The minimum string length to search for.

    Yeilds printable ASCII strings from filename.
    '''
    result = ""

    with BlockFile(filename) as f:
        while True:
            (data, dlen) = f.read_block()
            if not data:
                break

            for c in data:
                if c in string.printable:
                    result += c
                    continue
                elif len(result) >= minimum:
                    yield result
                    result = ""
                else:
                    result = ""

class MathExpression(object):
    '''
    Class for safely evaluating mathematical expressions from a string.
    Stolen from: http://stackoverflow.com/questions/2371436/evaluating-a-mathematical-expression-in-a-string
    '''

    OPERATORS = {
        ast.Add: op.add,
        ast.Sub: op.sub,
        ast.Mult: op.mul,
        ast.Div: op.truediv, 
        ast.Pow: op.pow, 
        ast.BitXor: op.xor
    }

    def __init__(self, expression):
        self.expression = expression
        self.value = None

        if expression:
            try:
                self.value = self.evaluate(self.expression)
            except KeyboardInterrupt as e:
                raise e
            except Exception:
                pass

    def evaluate(self, expr):
        return self._eval(ast.parse(expr).body[0].value)

    def _eval(self, node):
        if isinstance(node, ast.Num): # <number>
            return node.n
        elif isinstance(node, ast.operator): # <operator>
            return self.OPERATORS[type(node)]
        elif isinstance(node, ast.BinOp): # <left> <operator> <right>
            return self._eval(node.op)(self._eval(node.left), self._eval(node.right))
        else:
            raise TypeError(node)


class BlockFile(BLOCK_FILE_PARENT_CLASS):
    '''
    Abstraction class for accessing binary files.

    This class overrides io.FilIO's read and write methods. This guaruntees two things:

        1. All requested data will be read/written via the read and write methods.
        2. All reads return a str object and all writes can accept either a str or a
           bytes object, regardless of the Python interpreter version.

    However, the downside is that other io.FileIO methods won't work properly in Python 3,
    namely things that are wrappers around self.read (e.g., readline, readlines, etc).

    This class also provides a read_block method, which is used by binwalk to read in a
    block of data, plus some additional data (MAX_TRAILING_SIZE), but on the next block read
    pick up at the end of the previous data block (not the end of the additional data). This
    is necessary for scans where a signature may span a block boundary.

    The descision to force read to return a str object instead of a bytes object is questionable
    for Python 3, it seemed the best way to abstract differences in Python 2/3 from the rest
    of the code (especially for people writing plugins) and to add Python 3 support with 
    minimal code change.
    '''

    # The MAX_TRAILING_SIZE limits the amount of data available to a signature.
    # While most headers/signatures are far less than this value, some may reference 
    # pointers in the header structure which may point well beyond the header itself.
    # Passing the entire remaining buffer to libmagic is resource intensive and will
    # significantly slow the scan; this value represents a reasonable buffer size to
    # pass to libmagic which will not drastically affect scan time.
    DEFAULT_BLOCK_PEEK_SIZE = 8 * 1024

    # Max number of bytes to process at one time. This needs to be large enough to 
    # limit disk I/O, but small enough to limit the size of processed data blocks.
    DEFAULT_BLOCK_READ_SIZE = 1 * 1024 * 1024

    def __init__(self, fname, mode='r', length=0, offset=0, block=DEFAULT_BLOCK_READ_SIZE, peek=DEFAULT_BLOCK_PEEK_SIZE, swap=0):
        '''
        Class constructor.

        @fname  - Path to the file to be opened.
        @mode   - Mode to open the file in (default: 'r').
        @length - Maximum number of bytes to read from the file via self.block_read().
        @offset - Offset at which to start reading from the file.
        @block  - Size of data block to read (excluding any trailing size),
        @peek   - Size of trailing data to append to the end of each block.
        @swap   - Swap every n bytes of data.

        Returns None.
        '''
        self.total_read = 0
        self.swap_size = swap
        self.block_read_size = self.DEFAULT_BLOCK_READ_SIZE
        self.block_peek_size = self.DEFAULT_BLOCK_PEEK_SIZE

        # Python 2.6 doesn't like modes like 'rb' or 'wb'
        mode = mode.replace('b', '')

        try:
            self.size = file_size(fname)
        except KeyboardInterrupt as e:
            raise e
        except Exception:
            self.size = 0

        if offset < 0:
            self.offset = self.size + offset
        else:
            self.offset = offset

        if self.offset < 0:
            self.offset = 0
        elif self.offset > self.size:
            self.offset = self.size

        if offset < 0:
            self.length = offset * -1
        elif length:
            self.length = length
        else:
            self.length = self.size - offset

        if self.length < 0:
            self.length = 0
        elif self.length > self.size:
            self.length = self.size

        if block is not None:
            self.block_read_size = block
        self.base_block_size = self.block_read_size
            
        if peek is not None:
            self.block_peek_size = peek
        self.base_peek_size = self.block_peek_size

        super(self.__class__, self).__init__(fname, mode)

        # Work around for python 2.6 where FileIO._name is not defined
        try:
            self.name
        except AttributeError:
            self._name = fname

        self.seek(self.offset)

    def _swap_data_block(self, block):
        '''
        Reverses every self.swap_size bytes inside the specified data block.
        Size of data block must be a multiple of self.swap_size.

        @block - The data block to swap.

        Returns a swapped string.
        '''
        i = 0
        data = ""
        
        if self.swap_size > 0:
            while i < len(block):
                data += block[i:i+self.swap_size][::-1]
                i += self.swap_size
        else:
            data = block

        return data

    def reset(self):
        self.set_block_size(block=self.base_block_size, peek=self.base_peek_size)
        self.seek(self.offset)

    def set_block_size(self, block=None, peek=None):
        if block is not None:
            self.block_read_size = block
        if peek is not None:
            self.block_peek_size = peek

    def write(self, data):
        '''
        Writes data to the opened file.
        
        io.FileIO.write does not guaruntee that all data will be written;
        this method overrides io.FileIO.write and does guaruntee that all data will be written.

        Returns the number of bytes written.
        '''
        n = 0
        l = len(data)
        data = str2bytes(data)

        while n < l:
            n += super(self.__class__, self).write(data[n:])

        return n

    def read(self, n=-1):
        ''''
        Reads up to n bytes of data (or to EOF if n is not specified).
        Will not read more than self.length bytes.

        io.FileIO.read does not guaruntee that all requested data will be read;
        this method overrides io.FileIO.read and does guaruntee that all data will be read.

        Returns a str object containing the read data.
        '''
        l = 0
        data = b''

        if self.total_read < self.length:
            # Don't read more than self.length bytes from the file
            if (self.total_read + n) > self.length:
                n = self.length - self.total_read
                
            while n < 0 or l < n:
                tmp = super(self.__class__, self).read(n-l)
                if tmp:
                    data += tmp
                    l += len(tmp)
                else:
                    break

            self.total_read += len(data)

        return self._swap_data_block(bytes2str(data))

    def peek(self, n=-1):
        '''
        Peeks at data in file.
        '''
        pos = self.tell()
        data = self.read(n)
        self.seek(pos)
        return data

    def seek(self, n, whence=os.SEEK_SET):
        if whence == os.SEEK_SET:
            self.total_read = n - self.offset
        elif whence == os.SEEK_CUR:
            self.total_read += n
        elif whence == os.SEEK_END:
            self.total_read = self.size + n

        super(self.__class__, self).seek(n, whence)

    def read_block(self):
        '''
        Reads in a block of data from the target file.

        Returns a tuple of (str(file block data), block data length).
        '''
        data = self.read(self.block_read_size)
        dlen = len(data)
        data += self.peek(self.block_peek_size)

        return (data, dlen)


########NEW FILE########
__FILENAME__ = compat
# All Python 2/3 compatibility stuffs go here.

from __future__ import print_function
import sys
import string

PY_MAJOR_VERSION = sys.version_info[0]

if PY_MAJOR_VERSION > 2:
    string.letters = string.ascii_letters

def iterator(dictionary):
    '''
    For cross compatibility between Python 2 and Python 3 dictionaries.
    '''
    if PY_MAJOR_VERSION > 2:
        return dictionary.items()
    else:
        return dictionary.iteritems()

def has_key(dictionary, key):
    '''
    For cross compatibility between Python 2 and Python 3 dictionaries.
    '''
    if PY_MAJOR_VERSION > 2:
        return key in dictionary
    else:
        return dictionary.has_key(key)

def get_keys(dictionary):
    '''
    For cross compatibility between Python 2 and Python 3 dictionaries.
    '''
    if PY_MAJOR_VERSION > 2:
        return list(dictionary.keys())
    else:
        return dictionary.keys()

def str2bytes(string):
    '''
    For cross compatibility between Python 2 and Python 3 strings.
    '''
    if isinstance(string, type('')) and PY_MAJOR_VERSION > 2:
        return bytes(string, 'latin1')
    else:
        return string

def bytes2str(bs):
    '''
    For cross compatibility between Python 2 and Python 3 strings.
    '''
    if isinstance(bs, type(b'')) and PY_MAJOR_VERSION > 2:
        return bs.decode('latin1')
    else:
        return bs

def string_decode(string):
    '''
    For cross compatibility between Python 2 and Python 3 strings.
    '''
    if PY_MAJOR_VERSION > 2:
        return bytes(string, 'utf-8').decode('unicode_escape')
    else:
        return string.decode('string_escape')

def user_input(prompt=''):
    '''
    For getting raw user input in Python 2 and 3.
    '''
    if PY_MAJOR_VERSION > 2:
        return input(prompt)
    else:
        return raw_input(prompt)


########NEW FILE########
__FILENAME__ = display
# Code to handle displaying and logging of results.
# Anything in binwalk that prints results to screen should use this class.

import sys
import csv as pycsv
import datetime
import binwalk.core.common
from binwalk.core.compat import *

class Display(object):
    '''
    Class to handle display of output and writing to log files.
    This class is instantiated for all modules implicitly and should not need to be invoked directly by most modules.
    '''
    SCREEN_WIDTH = 0
    HEADER_WIDTH = 150
    DEFAULT_FORMAT = "%s\n"

    def __init__(self, quiet=False, verbose=False, log=None, csv=False, fit_to_screen=False, filter=None):
        self.quiet = quiet
        self.filter = filter
        self.verbose = verbose
        self.fit_to_screen = fit_to_screen
        self.fp = None
        self.csv = None
        self.num_columns = 0
        self.custom_verbose_format = ""
        self.custom_verbose_args = []

        self._configure_formatting()

        if log:
            self.fp = open(log, "a")
            if csv:
                self.csv = pycsv.writer(self.fp)

    def format_strings(self, header, result):
        self.result_format = result
        self.header_format = header
        
        if self.num_columns == 0:
            self.num_columns = len(header.split())

    def log(self, fmt, columns):
        if self.fp:
            if self.csv:
                self.csv.writerow(columns)
            else:
                self.fp.write(fmt % tuple(columns))

            self.fp.flush()

    def add_custom_header(self, fmt, args):
        self.custom_verbose_format = fmt
        self.custom_verbose_args = args

    def header(self, *args, **kwargs):
        file_name = None
        self.num_columns = len(args)

        if has_key(kwargs, 'file_name'):
            file_name = kwargs['file_name']

        if self.verbose and file_name:
            md5sum = binwalk.core.common.file_md5(file_name)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if self.csv:
                self.log("", ["FILE", "MD5SUM", "TIMESTAMP"])
                self.log("", [file_name, md5sum, timestamp])

            self._fprint("%s", "\n", csv=False)
            self._fprint("Scan Time:     %s\n", [timestamp], csv=False, filter=False)
            self._fprint("Target File:   %s\n", [file_name], csv=False, filter=False)
            self._fprint("MD5 Checksum:  %s\n", [md5sum], csv=False, filter=False)
            if self.custom_verbose_format and self.custom_verbose_args:
                self._fprint(self.custom_verbose_format, self.custom_verbose_args, csv=False, filter=False)

        self._fprint("%s", "\n", csv=False, filter=False)
        self._fprint(self.header_format, args, filter=False)
        self._fprint("%s", ["-" * self.HEADER_WIDTH + "\n"], csv=False, filter=False)

    def result(self, *args):
        # Convert to list for item assignment
        args = list(args)

        # Replace multiple spaces with single spaces. This is to prevent accidentally putting
        # four spaces in the description string, which would break auto-formatting.
        for i in range(len(args)):
            if isinstance(args[i], str):
                while "    " in args[i]:
                    args[i] = args[i].replace("  " , " ")

        self._fprint(self.result_format, tuple(args))

    def footer(self):
        self._fprint("%s", "\n", csv=False, filter=False)

    def _fprint(self, fmt, columns, csv=True, stdout=True, filter=True):
        line = fmt % tuple(columns)
        
        if not filter or self.filter.valid_result(line):
            if not self.quiet and stdout:
                sys.stdout.write(self._format_line(line.strip()) + "\n")
                sys.stdout.flush()

            if self.fp and not (self.csv and not csv):
                self.log(fmt, columns)

    def _append_to_data_parts(self, data, start, end):
        '''
        Intelligently appends data to self.string_parts.
        For use by self._format.
        '''
        try:
            while data[start] == ' ':
                start += 1

            if start == end:
                end = len(data[start:])

            self.string_parts.append(data[start:end])
        except KeyboardInterrupt as e:
            raise e
        except Exception:
            try:
                self.string_parts.append(data[start:])
            except KeyboardInterrupt as e:
                raise e
            except Exception:
                pass
        
        return start

    def _format_line(self, line):
        '''
        Formats a line of text to fit in the terminal window.
        For Tim.
        '''
        delim = '\n'
        offset = 0
        self.string_parts = []

        if self.fit_to_screen and len(line) > self.SCREEN_WIDTH:
            # Split the line into an array of columns, e.g., ['0', '0x00000000', 'Some description here']
            line_columns = line.split(None, self.num_columns-1)
            # Find where the start of the last column (description) starts in the line of text.
            # All line wraps need to be aligned to this offset.
            offset = line.rfind(line_columns[-1])
            # The delimiter will be a newline followed by spaces padding out the line wrap to the alignment offset.
            delim += ' ' * offset
            # Calculate the maximum length that each wrapped line can be
            max_line_wrap_length = self.SCREEN_WIDTH - offset

            # Append all but the last column to formatted_line
            formatted_line = line[:offset]

            # Loop to split up line into multiple max_line_wrap_length pieces
            while len(line[offset:]) > max_line_wrap_length:
                # Find the nearest space to wrap the line at (so we don't split a word across two lines)
                split_offset = line[offset:offset+max_line_wrap_length].rfind(' ')
                # If there were no good places to split the line, just truncate it at max_line_wrap_length
                if split_offset < 1:
                    split_offset = max_line_wrap_length

                self._append_to_data_parts(line, offset, offset+split_offset)
                offset += split_offset

            # Add any remaining data (guarunteed to be max_line_wrap_length long or shorter) to self.string_parts
            self._append_to_data_parts(line, offset, offset+len(line[offset:]))

            # Append self.string_parts to formatted_line; each part seperated by delim
            formatted_line += delim.join(self.string_parts)
        else:
            # Line fits on screen as-is, no need to format it
            formatted_line = line

        return formatted_line

    def _configure_formatting(self):
        '''
        Configures output formatting, and fitting output to the current terminal width.

        Returns None.
        '''
        self.format_strings(self.DEFAULT_FORMAT, self.DEFAULT_FORMAT)

        if self.fit_to_screen:
            try:
                import fcntl
                import struct
                import termios

                # Get the terminal window width
                hw = struct.unpack('hh', fcntl.ioctl(1, termios.TIOCGWINSZ, '1234'))
                self.SCREEN_WIDTH = self.HEADER_WIDTH = hw[1]
            except KeyboardInterrupt as e:
                raise e
            except Exception:
                pass


########NEW FILE########
__FILENAME__ = filter
# Code for filtering of results (e.g., removing invalid results)

import re
import binwalk.core.common as common
from binwalk.core.smart import Signature
from binwalk.core.compat import *

class FilterType(object):

    FILTER_INCLUDE = 0
    FILTER_EXCLUDE = 1

    def __init__(self, **kwargs):
        self.type = None
        self.filter = None
        self.regex = None

        for (k,v) in iterator(kwargs):
            setattr(self, k, v)

        if self.regex is None:
            self.regex = re.compile(self.filter)

class FilterInclude(FilterType):
    
    def __init__(self, **kwargs):
        super(FilterInclude, self).__init__(**kwargs)
        self.type = self.FILTER_INCLUDE

class FilterExclude(FilterType):
    
    def __init__(self, **kwargs):
        super(FilterExclude, self).__init__(**kwargs)
        self.type = self.FILTER_EXCLUDE

class Filter(object):
    '''
    Class to filter results based on include/exclude rules and false positive detection.
    Note that all filter strings should be in lower case.
    '''

    # If the result returned by libmagic is "data" or contains the text
    # 'invalid' or a backslash are known to be invalid/false positives.
    UNKNOWN_RESULTS = ["data", "very short file (no magic)"]
    INVALID_RESULTS = ["invalid", "\\"]
    INVALID_RESULT = "invalid"
    NON_PRINTABLE_RESULT = "\\"

    def __init__(self, show_invalid_results=None):
        '''
        Class constructor.

        @show_invalid_results - A function to call that will return True to display results marked as invalid.

        Returns None.
        '''
        self.filters = []
        self.grep_filters = []
        self.show_invalid_results = show_invalid_results
        self.exclusive_filter = False
        self.smart = Signature(self)

    def include(self, match, exclusive=True):
        '''
        Adds a new filter which explicitly includes results that contain
        the specified matching text.

        @match     - Regex, or list of regexs, to match.
        @exclusive - If True, then results that do not explicitly contain
                 a FILTER_INCLUDE match will be excluded. If False,
                 signatures that contain the FILTER_INCLUDE match will
                 be included in the scan, but will not cause non-matching
                 results to be excluded.
        
        Returns None.
        '''
        if not isinstance(match, type([])):
            matches = [match]
        else:
            matches = match

        for m in matches:
            if m:
                if exclusive and not self.exclusive_filter:
                    self.exclusive_filter = True

                self.filters.append(FilterInclude(filter=m))

    def exclude(self, match):
        '''
        Adds a new filter which explicitly excludes results that contain
        the specified matching text.

        @match - Regex, or list of regexs, to match.
        
        Returns None.
        '''
        if not isinstance(match, type([])):
            matches = [match]
        else:
            matches = match

        for m in matches:
            if m:
                self.filters.append(FilterExclude(filter=m))

    def filter(self, data):
        '''
        Checks to see if a given string should be excluded from or included in the results.
        Called internally by Binwalk.scan().

        @data - String to check.

        Returns FILTER_INCLUDE if the string should be included.
        Returns FILTER_EXCLUDE if the string should be excluded.
        '''
        data = data.lower()

        # Loop through the filters to see if any of them are a match. 
        # If so, return the registered type for the matching filter (FILTER_INCLUDE || FILTER_EXCLUDE). 
        for f in self.filters:
            if f.regex.search(data):
                return f.type

        # If there was not explicit match and exclusive filtering is enabled, return FILTER_EXCLUDE.
        if self.exclusive_filter:
            return FilterType.FILTER_EXCLUDE

        return FilterType.FILTER_INCLUDE

    def valid_result(self, data):
        '''
        Checks if the given string contains invalid data.

        @data - String to validate.

        Returns True if data is valid, False if invalid.
        '''
        # A result of 'data' is never ever valid (for libmagic results)
        if data in self.UNKNOWN_RESULTS:
            return False

        # Make sure this result wasn't filtered
        if self.filter(data) == FilterType.FILTER_EXCLUDE:
            return False

        # If showing invalid results, just return True without further checking.
        if self.show_invalid_results:
            return True

        # Don't include quoted strings or keyword arguments in this search, as 
        # strings from the target file may legitimately contain the INVALID_RESULT text.
        if self.INVALID_RESULT in common.strip_quoted_strings(self.smart.strip_tags(data)):
            return False

        # There should be no non-printable characters in any of the data
        if self.NON_PRINTABLE_RESULT in data:
            return False

        return True

    def grep(self, data=None, filters=[]):
        '''
        Add or check case-insensitive grep filters against the supplied data string.

        @data    - Data string to check grep filters against. Not required if filters is specified.
        @filters - Regex, or list of regexs, to add to the grep filters list. Not required if data is specified.

        Returns None if data is not specified.
        If data is specified, returns True if the data contains a grep filter, or if no grep filters exist.
        If data is specified, returns False if the data does not contain any grep filters.
        '''
        # Add any specified filters to self.grep_filters
        if filters:
            if not isinstance(filters, type([])):
                gfilters = [filters]
            else:
                gfilters = filters

            for gfilter in gfilters:
                # Filters are case insensitive
                self.grep_filters.append(re.compile(gfilter))

        # Check the data against all grep filters until one is found
        if data is not None:
            # If no grep filters have been created, always return True
            if not self.grep_filters:
                return True

            # Filters are case insensitive
            data = data.lower()

            # If a filter exists in data, return True
            for gfilter in self.grep_filters:
                if gfilter.search(data):
                    return True

            # Else, return False
            return False
    
        return None

    def clear(self):
        '''
        Clears all include, exclude and grep filters.
        
        Retruns None.
        '''
        self.filters = []
        self.grep_filters = []

########NEW FILE########
__FILENAME__ = magic
# Python wrapper for the libmagic library.
# Although libmagic comes with its own wrapper, there are compatibility issues with older libmagic versions
# as well as unofficial libmagic Python wrappers, so it's easier to just have our own wrapper.

import binwalk.core.C
import binwalk.core.common
from ctypes import *
from binwalk.core.compat import *

class magic_set(Structure):
    pass
magic_set._fields_ = []
magic_t = POINTER(magic_set)

class Magic(object):
    '''
    Minimalist Python wrapper around libmagic.
    '''

    LIBMAGIC_FUNCTIONS = [
            binwalk.core.C.Function(name="magic_open", type=magic_t),
            binwalk.core.C.Function(name="magic_close", type=int),
            binwalk.core.C.Function(name="magic_load", type=int),
            binwalk.core.C.Function(name="magic_buffer", type=str),
    ]

    MAGIC_CONTINUE          = 0x000020
    MAGIC_NO_CHECK_TEXT     = 0x020000
    MAGIC_NO_CHECK_APPTYPE  = 0x008000
    MAGIC_NO_CHECK_TOKENS   = 0x100000
    MAGIC_NO_CHECK_ENCODING = 0x200000
    
    MAGIC_FLAGS = MAGIC_NO_CHECK_TEXT | MAGIC_NO_CHECK_ENCODING | MAGIC_NO_CHECK_APPTYPE | MAGIC_NO_CHECK_TOKENS

    def __init__(self, magic_file=None, flags=0):
        if magic_file:
            self.magic_file = str2bytes(magic_file)
        else:
            self.magic_file = None

        self.libmagic = binwalk.core.C.Library("inmagic", self.LIBMAGIC_FUNCTIONS)

        binwalk.core.common.debug("libmagic.magic_open(0x%X)" % (self.MAGIC_FLAGS | flags))
        self.magic_cookie = self.libmagic.magic_open(self.MAGIC_FLAGS | flags)

        binwalk.core.common.debug("libmagic.magic_load(%s, %s)" % (type(self.magic_cookie), self.magic_file))
        self.libmagic.magic_load(self.magic_cookie, self.magic_file)
        binwalk.core.common.debug("libmagic loaded OK!")

    def close(self):
        if self.magic_cookie:
            self.libmagic.magic_close(self.magic_cookie)
            del self.magic_cookie
            self.magic_cookie = None

    def buffer(self, data):
        if self.magic_cookie:
            return self.libmagic.magic_buffer(self.magic_cookie, str2bytes(data), len(data))


########NEW FILE########
__FILENAME__ = module
# Core code relating to binwalk modules and supporting classes.
# In particular, the Module class (base class for all binwalk modules)
# and the Modules class (main class for managing and executing binwalk modules)
# are most critical.

import io
import os
import sys
import inspect
import argparse
import traceback
import binwalk.core.common
import binwalk.core.settings
import binwalk.core.plugin
from binwalk.core.compat import *

class Option(object):
    '''
    A container class that allows modules to declare command line options.
    '''

    def __init__(self, kwargs={}, priority=0, description="", short="", long="", type=None, dtype=None):
        '''
        Class constructor.

        @kwargs      - A dictionary of kwarg key-value pairs affected by this command line option.
        @priority    - A value from 0 to 100. Higher priorities will override kwarg values set by lower priority options.
        @description - A description to be displayed in the help output.
        @short       - The short option to use (optional).
        @long        - The long option to use (if None, this option will not be displayed in help output).
        @type        - The accepted data type (one of: io.FileIO/argparse.FileType/binwalk.core.common.BlockFile, list, str, int, float).
        @dtype       - The displayed accepted type string, to be shown in help output.

        Returns None.
        '''
        self.kwargs = kwargs
        self.priority = priority
        self.description = description
        self.short = short
        self.long = long
        self.type = type
        self.dtype = dtype

        if not self.dtype and self.type:
            if self.type in [io.FileIO, argparse.FileType, binwalk.core.common.BlockFile]:
                self.dtype = 'file'
            elif self.type in [int, float, str]:
                self.dtype = self.type.__name__
            else:
                self.type = str
                self.dtype = str.__name__

    def convert(self, value, default_value):
        if self.type and (self.type.__name__ == self.dtype):
            # Be sure to specify a base of 0 for int() so that the base is auto-detected
            if self.type == int:
                t = self.type(value, 0)
            else:
                t = self.type(value)
        elif default_value or default_value is False:
            t = default_value
        else:
            t = value

        return t

class Kwarg(object):
    '''
    A container class allowing modules to specify their expected __init__ kwarg(s).
    '''

    def __init__(self, name="", default=None, description=""):
        '''
        Class constructor.
    
        @name        - Kwarg name.
        @default     - Default kwarg value.
        @description - Description string.

        Return None.
        '''
        self.name = name
        self.default = default
        self.description = description

class Dependency(object):
    '''
    A container class for declaring module dependencies.
    '''

    def __init__(self, attribute="", name="", kwargs={}):
        self.attribute = attribute
        self.name = name
        self.kwargs = kwargs
        self.module = None

class Result(object):
    '''
    Generic class for storing and accessing scan results.
    '''

    def __init__(self, **kwargs):
        '''
        Class constructor.

        @offset      - The file offset of the result.
        @size        - Size of the result, if known.
        @description - The result description, as displayed to the user.
        @module      - Name of the module that generated the result.
        @file        - The file object of the scanned file.
        @valid       - Set to True if the result if value, False if invalid.
        @display     - Set to True to display the result to the user, False to hide it.
        @extract     - Set to True to flag this result for extraction.
        @plot        - Set to Flase to exclude this result from entropy plots.
        @name        - Name of the result found (None if not applicable or unknown).

        Provide additional kwargs as necessary.
        Returns None.
        '''
        self.offset = 0
        self.size = 0
        self.description = ''
        self.module = ''
        self.file = None
        self.valid = True
        self.display = True
        self.extract = True
        self.plot = True
        self.name = None

        for (k, v) in iterator(kwargs):
            setattr(self, k, v)

class Error(Result):
    '''
    A subclass of binwalk.core.module.Result.
    '''
    
    def __init__(self, **kwargs):
        '''
        Accepts all the same kwargs as binwalk.core.module.Result, but the following are also added:

        @exception - In case of an exception, this is the exception object.

        Returns None.
        '''
        self.exception = None
        Result.__init__(self, **kwargs)

class Module(object):
    '''
    All module classes must be subclassed from this.
    '''
    # The module title, as displayed in help output
    TITLE = ""

    # A list of binwalk.core.module.Option command line options
    CLI = []

    # A list of binwalk.core.module.Kwargs accepted by __init__
    KWARGS = []

    # A list of default dependencies for all modules; do not override this unless you
    # understand the consequences of doing so.
    DEFAULT_DEPENDS = [
            Dependency(name='General',
                       attribute='config'),
            Dependency(name='Extractor',
                       attribute='extractor'),
    ]
    
    # A list of binwalk.core.module.Dependency instances that can be filled in as needed by each individual module.
    DEPENDS = []

    # Format string for printing the header during a scan.
    # Must be set prior to calling self.header.
    HEADER_FORMAT = "%-12s  %-12s    %s\n"

    # Format string for printing each result during a scan. 
    # Must be set prior to calling self.result.
    RESULT_FORMAT = "%-12d  0x%-12X  %s\n"

    # Format string for printing custom information in the verbose header output.
    # Must be set prior to calling self.header.
    VERBOSE_FORMAT = ""

    # The header to print during a scan.
    # Set to None to not print a header.
    # Note that this will be formatted per the HEADER_FORMAT format string.
    # Must be set prior to calling self.header.
    HEADER = ["DECIMAL", "HEXADECIMAL", "DESCRIPTION"]

    # The Result attribute names to print during a scan, as provided to the self.results method.
    # Set to None to not print any results.
    # Note that these will be formatted per the RESULT_FORMAT format string.
    # Must be set prior to calling self.result.
    RESULT = ["offset", "offset", "description"]

    # The custom data to print in the verbose header output.
    # Note that these will be formatted per the VERBOSE_FORMAT format string.
    # Must be set prior to calling self.header.
    VERBOSE = []

    # If set to True, the progress status will be automatically updated for each result
    # containing valid file and offset attributes.
    AUTO_UPDATE_STATUS = True

    # Modules with higher priorities are executed first
    PRIORITY = 5

    # Modules with a higher order are displayed first in help output
    ORDER = 5

    # Set to False if this is not a primary module (e.g., General, Extractor modules)
    PRIMARY = True

    def __init__(self, **kwargs):
        self.errors = []
        self.results = []

        self.target_file_list = []
        self.status = None
        self.enabled = False
        self.current_target_file_name = None
        self.name = self.__class__.__name__
        self.plugins = binwalk.core.plugin.Plugins(self)
        self.dependencies = self.DEFAULT_DEPENDS + self.DEPENDS

        process_kwargs(self, kwargs)
        
        self.plugins.load_plugins()
        
        try:
            self.load()
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            self.error(exception=e)

        try:
            self.target_file_list = list(self.config.target_files)
        except AttributeError as e:
            pass

    def __del__(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, x, z, y):
        return None

    def load(self):
        '''
        Invoked at module load time.
        May be overridden by the module sub-class.
        '''
        return None

    def reset(self):
        '''
        Invoked only for dependency modules immediately prior to starting a new primary module.
        '''
        return None

    def init(self):
        '''
        Invoked prior to self.run.
        May be overridden by the module sub-class.

        Returns None.
        '''
        return None

    def run(self):
        '''
        Executes the main module routine.
        Must be overridden by the module sub-class.

        Returns True on success, False on failure.
        '''
        return False

    def callback(self, r):
        '''
        Processes the result from all modules. Called for all dependency modules when a valid result is found.

        @r - The result, an instance of binwalk.core.module.Result.

        Returns None.
        '''
        return None

    def validate(self, r):
        '''
        Validates the result.
        May be overridden by the module sub-class.

        @r - The result, an instance of binwalk.core.module.Result.

        Returns None.
        '''
        r.valid = True
        return None

    def _plugins_pre_scan(self):
        self.plugins.pre_scan_callbacks(self)

    def _plugins_post_scan(self):
        self.plugins.post_scan_callbacks(self)

    def _plugins_result(self, r):
        self.plugins.scan_callbacks(r)

    def _build_display_args(self, r):
        args = []

        if self.RESULT:
            if type(self.RESULT) != type([]):
                result = [self.RESULT]
            else:
                result = self.RESULT
    
            for name in result:
                args.append(getattr(r, name))
        
        return args

    def next_file(self):
        '''
        Gets the next file to be scanned (including pending extracted files, if applicable).
        Also re/initializes self.status.
        All modules should access the target file list through this method.
        '''
        fp = None

        # Add any pending extracted files to the target_files list and reset the extractor's pending file list
        self.target_file_list += [self.config.open_file(f) for f in self.extractor.pending]
        self.extractor.pending = []
        
        if self.target_file_list:
            fp = self.target_file_list.pop(0)
            self.status.clear()
            self.status.total = fp.length

        if fp is not None:
            self.current_target_file_name = fp.name    
        else:
            self.current_target_file_name = None

        return fp

    def clear(self, results=True, errors=True):
        '''
        Clears results and errors lists.
        '''
        if results:
            self.results = []
        if errors:
            self.errors = []

    def result(self, r=None, **kwargs):
        '''
        Validates a result, stores it in self.results and prints it.
        Accepts the same kwargs as the binwalk.core.module.Result class.

        @r - An existing instance of binwalk.core.module.Result.

        Returns an instance of binwalk.core.module.Result.
        '''
        if r is None:
            r = Result(**kwargs)

        r.module = self.__class__.__name__

        # Any module that is reporting results, valid or not, should be marked as enabled
        if not self.enabled:
            self.enabled = True

        self.validate(r)
        self._plugins_result(r)

        for dependency in self.dependencies:
            try:
                getattr(self, dependency.attribute).callback(r)
            except AttributeError:
                continue

        if r.valid:
            self.results.append(r)

            # Update the progress status automatically if it is not being done manually by the module
            if r.offset and r.file and self.AUTO_UPDATE_STATUS:
                self.status.total = r.file.length
                self.status.completed = r.offset

            if r.display:
                display_args = self._build_display_args(r)
                if display_args:
                    self.config.display.format_strings(self.HEADER_FORMAT, self.RESULT_FORMAT)
                    self.config.display.result(*display_args)
            else:
                # If this specific result has been marked to not be displayed to the user (e.g., 
                # it has been excluded via a -x or -y option), then disable extraction as well.
                # Note that this does not effect results that are not displayed globally (i.e.,
                # if --quiet was specified).
                r.extract = False

        return r

    def error(self, **kwargs):
        '''
        Stores the specified error in self.errors.

        Accepts the same kwargs as the binwalk.core.module.Error class.

        Returns None.
        '''
        exception_header_width = 100

        e = Error(**kwargs)
        e.module = self.__class__.__name__

        self.errors.append(e)
        
        if e.exception:
            sys.stderr.write("\n" + e.module + " Exception: " + str(e.exception) + "\n")
            sys.stderr.write("-" * exception_header_width + "\n")
            traceback.print_exc(file=sys.stderr)
            sys.stderr.write("-" * exception_header_width + "\n\n")
        elif e.description:
            sys.stderr.write("\n" + e.module + " Error: " + e.description + "\n\n")

    def header(self):
        '''
        Displays the scan header, as defined by self.HEADER and self.HEADER_FORMAT.

        Returns None.
        '''
        self.config.display.format_strings(self.HEADER_FORMAT, self.RESULT_FORMAT)
        self.config.display.add_custom_header(self.VERBOSE_FORMAT, self.VERBOSE)

        if type(self.HEADER) == type([]):
            self.config.display.header(*self.HEADER, file_name=self.current_target_file_name)
        elif self.HEADER:
            self.config.display.header(self.HEADER, file_name=self.current_target_file_name)
    
    def footer(self):
        '''
        Displays the scan footer.

        Returns None.
        '''
        self.config.display.footer()
            
    def main(self, parent):
        '''
        Responsible for calling self.init, initializing self.config.display, and calling self.run.

        Returns the value returned from self.run.
        '''
        self.status = parent.status
        self.modules = parent.loaded_modules

        # A special exception for the extractor module, which should be allowed to
        # override the verbose setting, e.g., if --matryoshka has been specified
        if hasattr(self, "extractor") and self.extractor.config.verbose:
            self.config.verbose = self.config.display.verbose = True

        # Reset all dependency modules
        for dependency in self.dependencies:
            if hasattr(self, dependency.attribute):
                getattr(self, dependency.attribute).reset()

        if not self.config.files:
            binwalk.core.common.debug("No target files specified, module %s terminated" % self.name)
            return False

        try:
            self.init()
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            self.error(exception=e)
            return False

        try:
            self.config.display.format_strings(self.HEADER_FORMAT, self.RESULT_FORMAT)
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            self.error(exception=e)
            return False
        
        self._plugins_pre_scan()

        try:
            retval = self.run()
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            self.error(exception=e)
            return False

        self._plugins_post_scan()

        return retval

class Status(object):
    '''
    Class used for tracking module status (e.g., % complete).
    '''

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.clear()

    def clear(self):
        for (k,v) in iterator(self.kwargs):
            setattr(self, k, v)

class ModuleException(Exception):
    '''
    Module exception class.
    Nothing special here except the name.
    '''
    pass

class Modules(object):
    '''
    Main class used for running and managing modules.
    '''

    def __init__(self, *argv, **kargv):
        '''
        Class constructor.

        @argv  - List of command line options. Must not include the program name (e.g., sys.argv[1:]).
        @kargv - Keyword dictionary of command line options.

        Returns None.
        '''
        self.arguments = []
        self.loaded_modules = {}
        self.default_dependency_modules = {}
        self.status = Status(completed=0, total=0)

        self._set_arguments(list(argv), kargv)

    def _set_arguments(self, argv=[], kargv={}):
        for (k,v) in iterator(kargv):
            k = self._parse_api_opt(k)
            if v not in [True, False, None]:
                if not isinstance(v, list):
                    v = [v]
                for value in v:
                    if not isinstance(value, str):
                        value = str(bytes2str(value))
                    argv.append(k)
                    argv.append(value)
            else:
                argv.append(k)

        if not argv and not self.arguments:
            self.arguments = sys.argv[1:]
        elif argv:
            self.arguments = argv

    def _parse_api_opt(self, opt):
        # If the argument already starts with a hyphen, don't add hyphens in front of it
        if opt.startswith('-'):
            return opt
        # Short options are only 1 character
        elif len(opt) == 1:
            return '-' + opt
        else:
            return '--' + opt

    def list(self, attribute="run"):
        '''
        Finds all modules with the specified attribute.

        @attribute - The desired module attribute.

        Returns a list of modules that contain the specified attribute, in the order they should be executed.
        '''
        import binwalk.modules
        modules = {}

        for (name, module) in inspect.getmembers(binwalk.modules):
            if inspect.isclass(module) and hasattr(module, attribute):
                modules[module] = module.PRIORITY

        return sorted(modules, key=modules.get, reverse=True)

    def help(self):
        '''
        Generates formatted help output.

        Returns the help string.
        '''
        modules = {}
        help_string = "\nBinwalk v%s\nCraig Heffner, http://www.binwalk.org\n" % binwalk.core.settings.Settings.VERSION
        help_string += "\nUsage: binwalk [OPTIONS] [FILE1] [FILE2] [FILE3] ...\n"

        # Build a dictionary of modules and their ORDER attributes.
        # This makes it easy to sort modules by their ORDER attribute for display.
        for module in self.list(attribute="CLI"):
            if module.CLI:
                modules[module] = module.ORDER

        for module in sorted(modules, key=modules.get, reverse=True):
            help_string += "\n%s Options:\n" % module.TITLE

            for module_option in module.CLI:
                if module_option.long:
                    long_opt = '--' + module_option.long
                    
                    if module_option.dtype:
                        optargs = "=<%s>" % module_option.dtype
                    else:
                        optargs = ""

                    if module_option.short:
                        short_opt = "-" + module_option.short + ","
                    else:
                        short_opt = "   "

                    fmt = "    %%s %%s%%-%ds%%s\n" % (32-len(long_opt))
                    help_string += fmt % (short_opt, long_opt, optargs, module_option.description)

        return help_string + "\n"

    def execute(self, *args, **kwargs):
        '''
        Executes all appropriate modules according to the options specified in args/kwargs.

        Returns a list of executed module objects.
        '''
        run_modules = []
        orig_arguments = self.arguments

        if args or kwargs:
            self._set_arguments(list(args), kwargs)

        # Run all modules
        for module in self.list():
            obj = self.run(module)

        # Add all loaded modules that marked themselves as enabled to the run_modules list
        for (module, obj) in iterator(self.loaded_modules):
            # Report the results if the module is enabled and if it is a primary module or if it reported any results/errors
            if obj.enabled and (obj.PRIMARY or obj.results or obj.errors):
                run_modules.append(obj)

        self.arguments = orig_arguments

        return run_modules

    def run(self, module, dependency=False, kwargs={}):
        '''
        Runs a specific module.
        '''
        obj = self.load(module, kwargs)

        if isinstance(obj, binwalk.core.module.Module) and obj.enabled:
            obj.main(parent=self)
            self.status.clear()

        # If the module is not being loaded as a dependency, add it to the loaded modules dictionary
        if not dependency:
            self.loaded_modules[module] = obj

        return obj
            
    def load(self, module, kwargs={}):
        argv = self.argv(module, argv=self.arguments)
        argv.update(kwargs)
        argv.update(self.dependencies(module, argv['enabled']))
        return module(**argv)
        
    def dependencies(self, module, module_enabled):
        import binwalk.modules
        attributes = {}

        for dependency in module.DEFAULT_DEPENDS+module.DEPENDS:

            # The dependency module must be imported by binwalk.modules.__init__.py
            if hasattr(binwalk.modules, dependency.name):
                dependency.module = getattr(binwalk.modules, dependency.name)
            else:
                raise ModuleException("%s depends on %s which was not found in binwalk.modules.__init__.py\n" % (str(module), dependency.name))
                
            # No recursive dependencies, thanks
            if dependency.module == module:
                continue

            # Only load dependencies with custom kwargs from modules that are enabled, else madness ensues.
            # Example: Heursitic module depends on entropy module, and sets entropy kwargs to contain 'enabled' : True.
            #          Without this check, an entropy scan would always be run, even if -H or -E weren't specified!
            #
            # Modules that are not enabled (e.g., extraction module) can load any dependency as long as they don't
            # set any custom kwargs for those dependencies.
            if module_enabled or not dependency.kwargs:
                depobj = self.run(dependency.module, dependency=True, kwargs=dependency.kwargs)
            
            # If a dependency failed, consider this a non-recoverable error and raise an exception
            if depobj.errors:
                raise ModuleException("Failed to load " + dependency.name + " module")
            else:
                attributes[dependency.attribute] = depobj

        return attributes

    def argv(self, module, argv=sys.argv[1:]):
        '''
        Processes argv for any options specific to the specified module.
    
        @module - The module to process argv for.
        @argv   - A list of command line arguments (excluding argv[0]).

        Returns a dictionary of kwargs for the specified module.
        '''
        kwargs = {'enabled' : False}
        last_priority = {}
        longs = []
        shorts = ""
        parser = argparse.ArgumentParser(add_help=False)
        # Hack: This allows the ListActionParser class to correllate short options to long options.
        #       There is probably a built-in way to do this in the argparse.ArgumentParser class?
        parser.short_to_long = {}

        # Must build arguments from all modules so that:
        #
        #    1) Any conflicting arguments will raise an exception
        #    2) The only unknown arguments will be the target files, making them easy to identify
        for m in self.list(attribute="CLI"):

            for module_option in m.CLI:

                parser_args = []
                parser_kwargs = {}

                if not module_option.long:
                    continue

                if module_option.short:
                    parser_args.append('-' + module_option.short)
                parser_args.append('--' + module_option.long)
                parser_kwargs['dest'] = module_option.long

                if module_option.type is None:
                    parser_kwargs['action'] = 'store_true'
                elif module_option.type is list:
                    parser_kwargs['action'] = 'append'
                    parser.short_to_long[module_option.short] = module_option.long

                parser.add_argument(*parser_args, **parser_kwargs)

        args, unknown = parser.parse_known_args(argv)
        args = args.__dict__

        # Only add parsed options pertinent to the requested module
        for module_option in module.CLI:

            if module_option.type == binwalk.core.common.BlockFile:

                for k in get_keys(module_option.kwargs):
                    kwargs[k] = []
                    for unk in unknown:
                        kwargs[k].append(unk)

            elif has_key(args, module_option.long) and args[module_option.long] not in [None, False]:

                # Loop through all the kwargs for this command line option
                for (name, default_value) in iterator(module_option.kwargs):
                    
                    # If this kwarg has not been previously processed, or if its priority is equal to or
                    # greater than the previously processed kwarg's priority, then let's process it.
                    if not has_key(last_priority, name) or last_priority[name] <= module_option.priority:

                        # Track the priority for future iterations that may process the same kwarg name
                        last_priority[name] = module_option.priority

                        try:
                            kwargs[name] = module_option.convert(args[module_option.long], default_value)
                        except KeyboardInterrupt as e:
                            raise e
                        except Exception as e:
                            raise ModuleException("Invalid usage: %s" % str(e))

        binwalk.core.common.debug("%s :: %s => %s" % (module.TITLE, str(argv), str(kwargs)))
        return kwargs
    
    def kwargs(self, obj, kwargs):
        '''
        Processes a module's kwargs. All modules should use this for kwarg processing.

        @obj    - An instance of the module (e.g., self)
        @kwargs - The kwargs passed to the module

        Returns None.
        '''
        if hasattr(obj, "KWARGS"):
            for module_argument in obj.KWARGS:
                if has_key(kwargs, module_argument.name):
                    arg_value = kwargs[module_argument.name]
                else:
                    arg_value = module_argument.default

                setattr(obj, module_argument.name, arg_value)

            for (k, v) in iterator(kwargs):
                if not hasattr(obj, k):
                    setattr(obj, k, v)
        else:
            raise Exception("binwalk.core.module.Modules.process_kwargs: %s has no attribute 'KWARGS'" % str(obj))


def process_kwargs(obj, kwargs):
    '''
    Convenience wrapper around binwalk.core.module.Modules.kwargs.

    @obj    - The class object (an instance of a sub-class of binwalk.core.module.Module).
    @kwargs - The kwargs provided to the object's __init__ method.

    Returns None.
    '''
    return Modules().kwargs(obj, kwargs)

def show_help(fd=sys.stdout):
    '''
    Convenience wrapper around binwalk.core.module.Modules.help.

    @fd - An object with a write method (e.g., sys.stdout, sys.stderr, etc).

    Returns None.
    '''
    fd.write(Modules().help())



########NEW FILE########
__FILENAME__ = parser
# Code for performing minimal parsing of libmagic-compatible signature files.
# This allows for building a single signature file from multiple other signature files,
# and for parsing out the initial magic signature bytes for each signature (used for
# pre-processing of data to limit the number of actual calls into libmagic).
# 
# Also performs splitting/formatting of libmagic result text.

import io
import re
import os.path
import tempfile
import binwalk.core.common
from binwalk.core.compat import *
from binwalk.core.filter import FilterType

class MagicSignature(object):

    def __init__(self, **kwargs):
        self.offset = 0
        self.type = ''
        self.condition = ''
        self.description = ''
        self.length = 0
        
        for (k,v) in iterator(kwargs):
            try:
                v = int(v, 0)
            except KeyboardInterrupt as e:
                raise e
            except Exception:
                pass

            setattr(self, k, v)

class MagicParser(object):
    '''
    Class for loading, parsing and creating libmagic-compatible magic files.
    
    This class is primarily used internally by the Binwalk class, and a class instance of it is available via the Binwalk.parser object.

    One useful method however, is file_from_string(), which will generate a temporary magic file from a given signature string:

        import binwalk

        bw = binwalk.Binwalk()

        # Create a temporary magic file that contains a single entry with a signature of '\\x00FOOBAR\\xFF', and append the resulting 
        # temporary file name to the list of magic files in the Binwalk class instance.
        bw.magic_files.append(bw.parser.file_from_string('\\x00FOOBAR\\xFF', display_name='My custom signature'))

        bw.scan('firmware.bin')
    
    All magic files generated by this class will be deleted when the class deconstructor is called.
    '''

    BIG_ENDIAN = 'big'
    LITTLE_ENDIAN = 'little'

    MAGIC_STRING_FORMAT = "%d\tstring\t%s\t%s\n"
    DEFAULT_DISPLAY_NAME = "Raw string signature"

    WILDCARD = 'x'

    # If libmagic returns multiple results, they are delimited with this string.    
    RESULT_SEPERATOR = "\\012- "

    def __init__(self, filter=None, smart=None):
        '''
        Class constructor.

        @filter - Instance of the MagicFilter class. May be None if the parse/parse_file methods are not used.
        @smart  - Instance of the SmartSignature class. May be None if the parse/parse_file methods are not used.
        Returns None.
        '''
        self.matches = set([])
        self.signatures = {}
        self.filter = filter
        self.smart = smart
        self.raw_fd = None
        self.signature_count = 0
        self.signature_set = set()

    def __del__(self):
        try:
            self.cleanup()
        except KeyboardInterrupt as e:
            raise e
        except Exception:
            pass

    def rm_magic_files(self):
        '''
        Cleans up the temporary magic file(s).

        Returns None.
        '''
        try:
            self.fd.close()
        except KeyboardInterrupt as e:
            raise e
        except Exception:
            pass
        
        try:
            self.raw_fd.close()
        except KeyboardInterrupt as e:
            raise e
        except Exception:
            pass

    def cleanup(self):
        '''
        Cleans up any tempfiles created by the class instance.

        Returns None.
        '''
        self.rm_magic_files()

    def file_from_string(self, signature_string, offset=0, display_name=DEFAULT_DISPLAY_NAME):
        '''
        Generates a magic file from a signature string.
        This method is intended to be used once per instance.
        If invoked multiple times, any previously created magic files will be closed and deleted.

        @signature_string - The string signature to search for.
        @offset           - The offset at which the signature should occur.
        @display_name     - The text to display when the signature is found.

        Returns the name of the generated temporary magic file.
        '''
        self.raw_fd = tempfile.NamedTemporaryFile()
        self.raw_fd.write(str2bytes(self.MAGIC_STRING_FORMAT % (offset, signature_string, display_name)))
        self.raw_fd.seek(0)
        return self.raw_fd.name

    def parse(self, file_name):
        '''
        Parses magic file(s) and contatenates them into a single temporary magic file
        while simultaneously removing filtered signatures.

        @file_name - Magic file, or list of magic files, to parse.

        Returns the name of the generated temporary magic file, which will be automatically
        deleted when the class deconstructor is called.
        '''
        self.matches = set([])
        self.signatures = {}
        self.signature_count = 0
        self.fd = tempfile.NamedTemporaryFile()

        if isinstance(file_name, type([])):
            files = file_name
        else:
            files = [file_name]

        for fname in files:
            if fname:
                if os.path.exists(fname) and os.path.isfile(fname):
                    self.parse_file(fname)
                else:
                    binwalk.core.common.warning("Magic file '%s' does not exist!" % fname)

        self.fd.seek(0)
        return self.fd.name

    def parse_file(self, file_name):
        '''
        Parses a magic file and appends valid signatures to the temporary magic file, as allowed
        by the existing filter rules.

        @file_name - Magic file to parse.
        
        Returns None.
        '''
        # Default to not including signature entries until we've
        # found what looks like a valid entry.
        include = False
        line_count = 0

        try:
            fp = open(file_name, 'rb')
            for line in fp.readlines():
                line = bytes2str(line)
                line_count += 1

                # Check if this is the first line of a signature entry
                entry = self._parse_line(line)

                if entry is not None:
                    # If this signature is marked for inclusion, include it.
                    if self.filter.filter(entry.description) == FilterType.FILTER_INCLUDE:

                        include = True    
                        self.signature_count += 1

                        if not has_key(self.signatures, entry.offset):
                            self.signatures[entry.offset] = []
                        
                        if entry.condition not in self.signatures[entry.offset]:
                            self.signatures[entry.offset].append(entry.condition)
                    else:
                        include = False

                # Keep writing lines of the signature to the temporary magic file until 
                # we detect a signature that should not be included.
                if include:
                    self.fd.write(str2bytes(line))

            fp.close()
            self.build_signature_set()
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            raise Exception("Error parsing magic file '%s' on line %d: %s" % (file_name, line_count, str(e)))
        
    def _parse_line(self, line):
        '''
        Parses a signature line into its four parts (offset, type, condition and description),
        looking for the first line of a given signature.

        @line - The signature line to parse.

        Returns a dictionary with the respective line parts populated if the line is the first of a signature.
        Returns a dictionary with all parts set to None if the line is not the first of a signature.
        '''
        entry = MagicSignature()

        # Quick and dirty pre-filter. We are only concerned with the first line of a
        # signature, which will always start with a number. Make sure the first byte of
        # the line is a number; if not, don't process.
        if line[:1] < '0' or line[:1] > '9':
            return None

        try:
            # Split the line into white-space separated parts.
            # For this to work properly, replace escaped spaces ('\ ') with '\x20'.
            # This means the same thing, but doesn't confuse split().
            line_parts = line.replace('\\ ', '\\x20').split()
            entry.offset = line_parts[0]
            entry.type = line_parts[1]
            # The condition line may contain escaped sequences, so be sure to decode it properly.
            entry.condition = string_decode(line_parts[2])
            entry.description = ' '.join(line_parts[3:])
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            raise Exception("%s :: %s", (str(e), line))

        # We've already verified that the first character in this line is a number, so this *shouldn't*
        # throw an exception, but let's catch it just in case...
        try:
            entry.offset = int(entry.offset, 0)
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            raise Exception("%s :: %s", (str(e), line))

        # If this is a string, get the length of the string
        if 'string' in entry.type or entry.condition == self.WILDCARD:
            entry.length = len(entry.condition)
        # Else, we need to jump through a few more hoops...
        else:    
            # Default to little endian, unless the type field starts with 'be'. 
            # This assumes that we're running on a little endian system...
            if entry.type.startswith('be'):
                endianess = self.BIG_ENDIAN
            else:
                endianess = self.LITTLE_ENDIAN
            
            # Try to convert the condition to an integer. This does not allow
            # for more advanced conditions for the first line of a signature, 
            # but needing that is rare.
            try:
                intval = int(entry.condition.strip('L'), 0)
            except KeyboardInterrupt as e:
                raise e
            except Exception as e:
                raise Exception("Failed to evaluate condition for '%s' type: '%s', condition: '%s', error: %s" % (entry['description'], entry['type'], entry['condition'], str(e)))

            # How long is the field type?
            if entry.type == 'byte':
                entry.length = 1
            elif 'short' in entry.type:
                entry.length = 2
            elif 'long' in entry.type:
                entry.length = 4
            elif 'quad' in entry.type:
                entry.length = 8

            # Convert the integer value to a string of the appropriate endianess
            entry.condition = self._to_string(intval, entry.length, endianess)

        return entry

    def build_signature_set(self):
        '''
        Builds a set of signature tuples.

        Returns a set of tuples in the format: [(<signature offset>, [signature regex])].
        '''
        self.signature_set = set()

        for (offset, sigs) in iterator(self.signatures):
            
            for sig in sigs:
                if sig == self.WILDCARD:
                    sig = re.compile('.')
                else:
                    sig = re.compile(re.escape(sig))

                self.signature_set.add((offset, sig))

        return self.signature_set

    def find_signature_candidates(self, data, end):
        '''
        Finds candidate signatures inside of the data buffer.
        Called internally by Binwalk.single_scan.

        @data - Data to scan for candidate signatures.
        @end  - Don't look for signatures beyond this offset.

        Returns an ordered list of offsets inside of data at which candidate offsets were found.
        '''
        candidate_offsets = []

        for (offset, regex) in self.signature_set:
            candidate_offsets += [(match.start() - offset) for match in regex.finditer(data) if (match.start() - offset) < end  and (match.start() - offset) >= 0]

        candidate_offsets = list(set(candidate_offsets))
        candidate_offsets.sort()

        return candidate_offsets

    def _to_string(self, value, size, endianess):
        '''
        Converts an integer value into a raw string.

        @value     - The integer value to convert.
        @size      - Size, in bytes, of the integer value.
        @endianess - One of self.LITTLE_ENDIAN | self.BIG_ENDIAN.

        Returns a raw string containing value.
        '''
        data = ""

        for i in range(0, size):
            data += chr((value >> (8*i)) & 0xFF)

        if endianess != self.LITTLE_ENDIAN:
            data = data[::-1]

        return data

    def split(self, data):
        '''
        Splits multiple libmagic results in the data string into a list of separate results.

        @data - Data string returned from libmagic.

        Returns a list of result strings.
        '''
        try:
            return data.split(self.RESULT_SEPERATOR)
        except KeyboardInterrupt as e:
            raise e
        except Exception:
            return []


########NEW FILE########
__FILENAME__ = plugin
# Core code for supporting and managing plugins.

import os
import sys
import imp
import inspect
import binwalk.core.common
import binwalk.core.settings
from binwalk.core.compat import *

class Plugin(object):
    '''
    Class from which all plugin classes are based.
    '''
    # A list of case-sensitive module names for which this plugin should be loaded.
    # If no module names are specified, the plugin will be loaded for all modules.
    MODULES = []

    def __init__(self, module):
        '''
        Class constructor.

        @module - A handle to the current module that this plugin is loaded for.

        Returns None.
        '''
        self.module = module
        
        if not self.MODULES or self.module.name in self.MODULES:
            self._enabled = True
            self.init()
        else:
            self._enabled = False

    def init(self):
        '''
        Child class should override this if needed.
        Invoked during plugin initialization.
        '''
        pass

    def pre_scan(self):
        '''
        Child class should override this if needed.
        '''
        pass

    def scan(self, result):
        '''
        Child class should override this if needed.
        '''
        pass

    def post_scan(self):
        '''
        Child class should override this if needed.
        '''
        pass

class Plugins(object):
    '''
    Class to load and call plugin callback functions, handled automatically by Binwalk.scan / Binwalk.single_scan.
    An instance of this class is available during a scan via the Binwalk.plugins object.

    Each plugin must be placed in the user or system plugins directories, and must define a class named 'Plugin'.
    The Plugin class constructor (__init__) is passed one argument, which is the current instance of the Binwalk class.
    The Plugin class constructor is called once prior to scanning a file or set of files.
    The Plugin class destructor (__del__) is called once after scanning all files.

    The Plugin class can define one or all of the following callback methods:

        o pre_scan(self, fd)
          This method is called prior to running a scan against a file. It is passed the file object of
          the file about to be scanned.

        o pre_parser(self, result)
          This method is called every time any result - valid or invalid - is found in the file being scanned.
          It is passed a dictionary with one key ('description'), which contains the raw string returned by libmagic.
          The contents of this dictionary key may be modified as necessary by the plugin.

        o callback(self, results)
          This method is called every time a valid result is found in the file being scanned. It is passed a 
          dictionary of results. This dictionary is identical to that passed to Binwalk.single_scan's callback 
          function, and its contents may be modified as necessary by the plugin.

        o post_scan(self, fd)
          This method is called after running a scan against a file, but before the file has been closed.
          It is passed the file object of the scanned file.

    Values returned by pre_scan affect all results during the scan of that particular file.
    Values returned by callback affect only that specific scan result.
    Values returned by post_scan are ignored since the scan of that file has already been completed.

    By default, all plugins are loaded during binwalk signature scans. Plugins that wish to be disabled by 
    default may create a class variable named 'ENABLED' and set it to False. If ENABLED is set to False, the
    plugin will only be loaded if it is explicitly named in the plugins whitelist.
    '''

    SCAN = 'scan'
    PRESCAN = 'pre_scan'
    POSTSCAN = 'post_scan'
    MODULE_EXTENSION = '.py'

    def __init__(self, parent=None):
        self.scan = []
        self.pre_scan = []
        self.post_scan = []
        self.parent = parent
        self.settings = binwalk.core.settings.Settings()

    def __del__(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, t, v, traceback):
        pass

    def _call_plugins(self, callback_list, arg):
        for callback in callback_list:
            try:
                if arg:
                    callback(arg)
                else:
                    callback()
            except KeyboardInterrupt as e:
                raise e
            except Exception as e:
                binwalk.core.common.warning("%s.%s failed: %s" % (callback.__module__, callback.__name__, e))

    def _find_plugin_class(self, plugin):
        for (name, klass) in inspect.getmembers(plugin, inspect.isclass):
            if issubclass(klass, Plugin) and klass != Plugin:
                return klass
        raise Exception("Failed to locate Plugin class in " + plugin)

    def list_plugins(self):
        '''
        Obtain a list of all user and system plugin modules.

        Returns a dictionary of:

            {
                'user'      : {
                            'modules'       : [list, of, module, names],
                            'descriptions'  : {'module_name' : 'module pydoc string'},
                            'enabled'       : {'module_name' : True},
                            'path'          : "path/to/module/plugin/directory"
                },
                'system'    : {
                            'modules'       : [list, of, module, names],
                            'descriptions'  : {'module_name' : 'module pydoc string'},
                            'enabled'       : {'module_name' : True},
                            'path'          : "path/to/module/plugin/directory"
                }
            }
        '''

        plugins = {
            'user'   : {
                    'modules'       : [],
                    'descriptions'  : {},
                    'enabled'       : {},
                    'path'          : None,
            },
            'system' : {
                    'modules'       : [],
                    'descriptions'  : {},
                    'enabled'       : {},
                    'path'          : None,
            }
        }

        for key in plugins.keys():
            plugins[key]['path'] = self.settings.get_file_path(key, self.settings.PLUGINS)

            if plugins[key]['path']:
                for file_name in os.listdir(plugins[key]['path']):
                    if file_name.endswith(self.MODULE_EXTENSION):
                        module = file_name[:-len(self.MODULE_EXTENSION)]
                    
                        try: 
                            plugin = imp.load_source(module, os.path.join(plugins[key]['path'], file_name))
                            plugin_class = self._find_plugin_class(plugin)

                            plugins[key]['enabled'][module] = True
                            plugins[key]['modules'].append(module)
                        except KeyboardInterrupt as e:
                            raise e
                        except Exception as e:
                            binwalk.core.common.warning("Error loading plugin '%s': %s" % (file_name, str(e)))
                            plugins[key]['enabled'][module] = False
                        
                        try:
                            plugins[key]['descriptions'][module] = plugin_class.__doc__.strip().split('\n')[0]
                        except KeyboardInterrupt as e:
                            raise e
                        except Exception as e:
                            plugins[key]['descriptions'][module] = 'No description'
        return plugins

    def load_plugins(self):
        plugins = self.list_plugins()
        self._load_plugin_modules(plugins['user'])
        self._load_plugin_modules(plugins['system'])

    def _load_plugin_modules(self, plugins):
        for module in plugins['modules']:
            try:
                file_path = os.path.join(plugins['path'], module + self.MODULE_EXTENSION)
            except KeyboardInterrupt as e:
                raise e
            except Exception:
                continue

            try:
                plugin = imp.load_source(module, file_path)
                plugin_class = self._find_plugin_class(plugin)

                class_instance = plugin_class(self.parent)
                if not class_instance._enabled:
                    continue

                try:
                    self.scan.append(getattr(class_instance, self.SCAN))
                except KeyboardInterrupt as e:
                    raise e
                except Exception as e:
                    pass

                try:
                    self.pre_scan.append(getattr(class_instance, self.PRESCAN))
                except KeyboardInterrupt as e:
                    raise e
                except Exception as e:
                    pass

                try:
                    self.post_scan.append(getattr(class_instance, self.POSTSCAN))
                except KeyboardInterrupt as e:
                    raise e
                except Exception as e:
                    pass
                            
            except KeyboardInterrupt as e:
                raise e
            except Exception as e:
                binwalk.core.common.warning("Failed to load plugin module '%s': %s" % (module, str(e)))

    def pre_scan_callbacks(self, obj):
        return self._call_plugins(self.pre_scan, None)

    def post_scan_callbacks(self, obj):
        return self._call_plugins(self.post_scan, None)

    def scan_callbacks(self, obj):
        return self._call_plugins(self.scan, obj)


########NEW FILE########
__FILENAME__ = settings
# Code for loading and accessing binwalk settings (extraction rules, signature files, etc).

import os
import binwalk.core.common as common
from binwalk.core.compat import *

class Settings:
    '''
    Binwalk settings class, used for accessing user and system file paths and general configuration settings.
    
    After instatiating the class, file paths can be accessed via the self.paths dictionary.
    System file paths are listed under the 'system' key, user file paths under the 'user' key.

    Valid file names under both the 'user' and 'system' keys are as follows:

        o BINWALK_MAGIC_FILE  - Path to the default binwalk magic file.
        o PLUGINS             - Path to the plugins directory.
    '''
    # Release version
    VERSION = "2.0.0"

    # Sub directories
    BINWALK_USER_DIR = ".binwalk"
    BINWALK_MAGIC_DIR = "magic"
    BINWALK_CONFIG_DIR = "config"
    BINWALK_PLUGINS_DIR = "plugins"

    # File names
    PLUGINS = "plugins"
    EXTRACT_FILE = "extract.conf"
    BINWALK_MAGIC_FILE = "binwalk"
    BINARCH_MAGIC_FILE = "binarch"
    BINCAST_MAGIC_FILE = "bincast"

    def __init__(self):
        '''
        Class constructor. Enumerates file paths and populates self.paths.
        '''
        # Path to the user binwalk directory
        self.user_dir = self._get_user_dir()
        # Path to the system wide binwalk directory
        self.system_dir = self._get_system_dir()

        # Dictionary of all absolute user/system file paths
        self.paths = {
            'user'      : {},
            'system'    : {},
        }

        # Build the paths to all user-specific files
        self.paths['user'][self.BINWALK_MAGIC_FILE] = self._user_path(self.BINWALK_MAGIC_DIR, self.BINWALK_MAGIC_FILE)
        self.paths['user'][self.BINARCH_MAGIC_FILE] = self._user_path(self.BINWALK_MAGIC_DIR, self.BINARCH_MAGIC_FILE)
        self.paths['user'][self.BINCAST_MAGIC_FILE] = self._user_path(self.BINWALK_MAGIC_DIR, self.BINCAST_MAGIC_FILE)
        self.paths['user'][self.EXTRACT_FILE] = self._user_path(self.BINWALK_CONFIG_DIR, self.EXTRACT_FILE)
        self.paths['user'][self.PLUGINS] = self._user_path(self.BINWALK_PLUGINS_DIR)

        # Build the paths to all system-wide files
        self.paths['system'][self.BINWALK_MAGIC_FILE] = self._system_path(self.BINWALK_MAGIC_DIR, self.BINWALK_MAGIC_FILE)
        self.paths['system'][self.BINARCH_MAGIC_FILE] = self._system_path(self.BINWALK_MAGIC_DIR, self.BINARCH_MAGIC_FILE)
        self.paths['system'][self.BINCAST_MAGIC_FILE] = self._system_path(self.BINWALK_MAGIC_DIR, self.BINCAST_MAGIC_FILE)
        self.paths['system'][self.EXTRACT_FILE] = self._system_path(self.BINWALK_CONFIG_DIR, self.EXTRACT_FILE)
        self.paths['system'][self.PLUGINS] = self._system_path(self.BINWALK_PLUGINS_DIR)

    def get_file_path(self, usersys, fname):
        '''
        Retrieves the specified file path from self.paths.

        @usersys - One of: 'user', 'system'.
        @fname   - The file name (e.g., self.BINWALK_MAGIC_FILE, self.PLUGINS, etc)

        Returns the path, if it exists; returns None otherwise.
        '''
        if has_key(self.paths, usersys) and has_key(self.paths[usersys], fname) and self.paths[usersys][fname]:
            return self.paths[usersys][fname]
        return None

    def find_magic_file(self, fname, system_only=False, user_only=False):
        '''
        Finds the specified magic file name in the system / user magic file directories.

        @fname       - The name of the magic file.
        @system_only - If True, only the system magic file directory will be searched.
        @user_only   - If True, only the user magic file directory will be searched.

        If system_only and user_only are not set, the user directory is always searched first.

        Returns the path to the file on success; returns None on failure.
        '''
        loc = None

        if not system_only:
            fpath = self._user_path(self.BINWALK_MAGIC_DIR, fname)
            if os.path.exists(fpath) and common.file_size(fpath) > 0:
                loc = fpath

        if loc is None and not user_only:
            fpath = self._system_path(self.BINWALK_MAGIC_DIR, fname)
            if os.path.exists(fpath) and common.file_size(fpath) > 0:
                loc = fpath

        return fpath
    
    def _get_system_dir(self):
        '''
        Find the directory where the binwalk module is installed on the system.
        '''
        try:
            root = __file__
            if os.path.islink(root):
                root = os.path.realpath(root)
            return os.path.dirname(os.path.dirname(os.path.abspath(root)))
        except KeyboardInterrupt as e:
            raise e
        except Exception:
            return ''

    def _get_user_dir(self):
        '''
        Get the user's home directory.
        '''
        try:
            # This should work in both Windows and Unix environments
            return os.getenv('USERPROFILE') or os.getenv('HOME')
        except KeyboardInterrupt as e:
            raise e
        except Exception:
            return ''

    def _file_path(self, dirname, filename):
        '''
        Builds an absolute path and creates the directory and file if they don't already exist.

        @dirname  - Directory path.
        @filename - File name.
        
        Returns a full path of 'dirname/filename'.
        '''
        if not os.path.exists(dirname):
            try:
                os.makedirs(dirname)
            except KeyboardInterrupt as e:
                raise e
            except Exception:
                pass
        
        fpath = os.path.join(dirname, filename)

        if not os.path.exists(fpath):
            try:
                open(fpath, "w").close()
            except KeyboardInterrupt as e:
                raise e
            except Exception:
                pass

        return fpath

    def _user_path(self, subdir, basename=''):
        '''
        Gets the full path to the 'subdir/basename' file in the user binwalk directory.

        @subdir   - Subdirectory inside the user binwalk directory.
        @basename - File name inside the subdirectory.

        Returns the full path to the 'subdir/basename' file.
        '''
        try:
            return self._file_path(os.path.join(self.user_dir, self.BINWALK_USER_DIR, subdir), basename)
        except KeyboardInterrupt as e :
            raise e
        except Exception:
            return None

    def _system_path(self, subdir, basename=''):
        '''
        Gets the full path to the 'subdir/basename' file in the system binwalk directory.
        
        @subdir   - Subdirectory inside the system binwalk directory.
        @basename - File name inside the subdirectory.
        
        Returns the full path to the 'subdir/basename' file.
        '''
        try:
            return self._file_path(os.path.join(self.system_dir, subdir), basename)
        except KeyboardInterrupt as e :
            raise e
        except Exception:
            return None


########NEW FILE########
__FILENAME__ = smart
# "Smart" parser for handling libmagic signature results. Specifically, this implements
# support for binwalk's custom libmagic signature extensions (keyword tags, string processing,
# false positive detection, etc).

import re
import binwalk.core.module
from binwalk.core.compat import *
from binwalk.core.common import get_quoted_strings, MathExpression

class Tag(object):
    
    TAG_DELIM_START = "{"
    TAG_DELIM_END = "}"
    TAG_ARG_SEPERATOR = ":"

    def __init__(self, **kwargs):
        self.name = None
        self.keyword = None
        self.type = None
        self.handler = None
        self.tag = None
        self.default = None

        for (k,v) in iterator(kwargs):
            setattr(self, k, v)

        if self.type == int:
            self.default = 0
        elif self.type == str:
            self.default = ''

        if self.keyword is not None:
            self.tag = self.TAG_DELIM_START + self.keyword
            if self.type is None:
                self.tag += self.TAG_DELIM_END
            else:
                self.tag += self.TAG_ARG_SEPERATOR

        if self.handler is None:
            if self.type == int:
                self.handler = 'get_math_arg'
            elif self.type == str:
                self.handler = 'get_keyword_arg'

class Signature(object):
    '''
    Class for parsing smart signature tags in libmagic result strings.

    This class is intended for internal use only, but a list of supported 'smart keywords' that may be used 
    in magic files is available via the SmartSignature.KEYWORDS dictionary:

        from binwalk import SmartSignature

        for tag in SmartSignature.TAGS:
            print tag.keyword
    '''

    TAGS = [
        Tag(name='raw-string', keyword='raw-string', type=str, handler='parse_raw_string'),
        Tag(name='string-len', keyword='string-len', type=str, handler='parse_string_len'),
        Tag(name='math', keyword='math', type=int, handler='parse_math'),
        Tag(name='one-of-many', keyword='one-of-many', handler='one_of_many'),

        Tag(name='jump', keyword='jump-to-offset', type=int),
        Tag(name='name', keyword='file-name', type=str),
        Tag(name='size', keyword='file-size', type=int),
        Tag(name='adjust', keyword='offset-adjust', type=int),
        Tag(name='delay', keyword='extract-delay', type=str),
        Tag(name='year', keyword='file-year', type=str),
        Tag(name='epoch', keyword='file-epoch', type=int),
        
        Tag(name='raw-size', keyword='raw-string-length', type=int),
        Tag(name='raw-replace', keyword='raw-replace'),
        Tag(name='string-len-replace', keyword='string-len'),
    ]

    def __init__(self, filter, ignore_smart_signatures=False):
        '''
        Class constructor.

        @filter                  - Instance of the MagicFilter class.
        @ignore_smart_signatures - Set to True to ignore smart signature keywords.

        Returns None.
        '''
        self.filter = filter
        self.last_one_of_many = None
        self.ignore_smart_signatures = ignore_smart_signatures

    def parse(self, data):
        '''
        Parse a given data string for smart signature keywords. If any are found, interpret them and strip them.

        @data - String to parse, as returned by libmagic.

        Returns a dictionary of parsed values.
        '''
        results = {}
        self.valid = True
        self.display = True

        if data:
            for tag in self.TAGS:
                if tag.handler is not None:
                    (d, arg) = getattr(self, tag.handler)(data, tag)
                    if not self.ignore_smart_signatures:
                        data = d

                    if isinstance(arg, type(False)) and arg == False and not self.ignore_smart_signatures:
                        self.valid = False
                    elif tag.type is not None:
                        if self.ignore_smart_signatures:
                            results[tag.name] = tag.default
                        else:
                            results[tag.name] = arg

            if self.ignore_smart_signatures:
                results['description'] = data
            else:
                results['description'] = self.strip_tags(data)
        else:
            self.valid = False
            
        results['valid'] = self.valid
        results['display'] = self.display

        return binwalk.core.module.Result(**results)

    def tag_lookup(self, keyword):
        for tag in self.TAGS:
            if tag.keyword == keyword:
                return tag
        return None

    def is_valid(self, data):
        '''
        Validates that result data does not contain smart keywords in file-supplied strings.

        @data - Data string to validate.

        Returns True if data is OK.
        Returns False if data is not OK.
        '''
        # All strings printed from the target file should be placed in strings, else there is
        # no way to distinguish between intended keywords and unintended keywords. Get all the
        # quoted strings.
        quoted_data = get_quoted_strings(data)

        # Check to see if there was any quoted data, and if so, if it contained the keyword starting delimiter
        if quoted_data and Tag.TAG_DELIM_START in quoted_data:
            # If so, check to see if the quoted data contains any of our keywords.
            # If any keywords are found inside of quoted data, consider the keywords invalid.
            for tag in self.TAGS:
                if tag.tag in quoted_data:
                    return False
        return True

    def safe_string(self, data):
        '''
        Strips out quoted data (i.e., data taken directly from a file).
        '''
        quoted_string = get_quoted_strings(data)
        if quoted_string:
            data = data.replace('"' + quoted_string + '"', "")
        return data

    def one_of_many(self, data, tag):
        '''
        Determines if a given data string is one result of many.

        @data - String result data.

        Returns False if the string result is one of many and should not be displayed.
        Returns True if the string result is not one of many and should be displayed.
        '''
        if self.filter.valid_result(data):
            if self.last_one_of_many is not None and data.startswith(self.last_one_of_many):
                self.display = False
            elif tag.tag in data:
                # Only match on the data before the first comma, as that is typically unique and static
                self.last_one_of_many = data.split(',')[0]
            else:
                self.last_one_of_many = None
            
        return (data, True)

    def get_keyword_arg(self, data, tag):
        '''
        Retrieves the argument for keywords that specify arguments.

        @data    - String result data, as returned by libmagic.
        @keyword - Keyword index in KEYWORDS.

        Returns the argument string value on success.
        Returns a blank string on failure.
        '''
        arg = ''
        safe_data = self.safe_string(data)

        if tag.tag in safe_data:
            arg = safe_data.split(tag.tag)[1].split(tag.TAG_DELIM_END)[0]
        
        return (data, arg)

    def get_math_arg(self, data, tag):
        '''
        Retrieves the argument for keywords that specifiy mathematical expressions as arguments.

        @data    - String result data, as returned by libmagic.
        @keyword - Keyword index in KEYWORDS.

        Returns the resulting calculated value.
        '''
        value = 0

        (data, arg) = self.get_keyword_arg(data, tag)
        if arg:
            value = MathExpression(arg).value
            if value is None:
                value = 0
                self.valid = False

        return (data, value)

    def parse_math(self, data, tag):
        '''
        Replace math keywords with the requested values.
            
        @data - String result data.

        Returns the modified string result data.
        '''
        while tag.tag in self.safe_string(data):
            (data, arg) = self.get_keyword_arg(data, tag)
            v = '%s%s%s' % (tag.tag, arg, tag.TAG_DELIM_END)
            (data, math_value) = self.get_math_arg(data, tag)
            data = data.replace(v, "%d" % math_value)

        return (data, None)

    def parse_raw_string(self, data, raw_str_tag):
        '''
        Process strings that aren't NULL byte terminated, but for which we know the string length.
        This should be called prior to any other smart parsing functions.

        @data - String to parse.

        Returns a parsed string.
        '''
        if self.is_valid(data):
            raw_str_length_tag = self.tag_lookup('raw-string-length')
            raw_replace_tag = self.tag_lookup('raw-replace')

            # Get the raw string  keyword arg
            (data, raw_string) = self.get_keyword_arg(data, raw_str_tag)
            
            # Was a raw string keyword specified?
            if raw_string:
                # Get the raw string length arg
                (data, raw_size) = self.get_math_arg(data, raw_str_length_tag)

                # Replace all instances of raw-replace in data with raw_string[:raw_size]
                # Also strip out everything after the raw-string keyword, including the keyword itself.
                # Failure to do so may (will) result in non-printable characters and this string will be 
                # marked as invalid when it shouldn't be.
                data = data[:data.find(raw_str_tag.tag)].replace(raw_replace_tag.tag, '"' + raw_string[:raw_size] + '"')

        return (data, True)
        
    def parse_string_len(self, data, str_len_tag):
        '''
        Process {string-len} macros. 

        @data - String to parse.

        Returns parsed data string.
        '''
        if not self.ignore_smart_signatures and self.is_valid(data):

            str_len_replace_tag = self.tag_lookup('string-len-replace')

            # Get the raw string  keyword arg
            (data, raw_string) = self.get_keyword_arg(data, str_len_tag)

            # Was a string-len  keyword specified?
            if raw_string:
                # Get the string length
                try:
                    string_length = '%d' % len(raw_string)
                except KeyboardInterrupt as e:
                    raise e
                except Exception:
                    string_length = '0'

                # Strip out *everything* after the string-len keyword, including the keyword itself.
                # Failure to do so can potentially allow keyword injection from a maliciously created file.
                data = data.split(str_len_tag.tag)[0].replace(str_len_replace_tag.tag, string_length)

        return (data, True)

    def strip_tags(self, data):
        '''
        Strips the smart tags from a result string.

        @data - String result data.

        Returns a sanitized string.
        '''
        if not self.ignore_smart_signatures:
            for tag in self.TAGS:
                start = data.find(tag.tag)
                if start != -1:
                    end = data[start:].find(tag.TAG_DELIM_END)
                    if end != -1:
                        data = data.replace(data[start:start+end+1], "")
        return data


########NEW FILE########
__FILENAME__ = binvis
# Generates 3D visualizations of input files.

import os
from binwalk.core.compat import *
from binwalk.core.common import BlockFile
from binwalk.core.module import Module, Option, Kwarg

class Plotter(Module):
    '''
    Base class for visualizing binaries in Qt.
    Other plotter classes are derived from this.
    '''
    VIEW_DISTANCE = 1024
    MAX_2D_PLOT_POINTS = 12500
    MAX_3D_PLOT_POINTS = 25000

    TITLE = "Binary Visualization"

    CLI = [
            Option(short='3',
                   long='3D',
                   kwargs={'axis' : 3, 'enabled' : True},
                   description='Generate a 3D binary visualization'),
            Option(short='2',
                   long='2D',
                   kwargs={'axis' : 2, 'enabled' : True},
                   description='Project data points onto 3D cube walls only'),
            Option(short='Z',
                   long='points',
                   type=int,
                   kwargs={'max_points' : 0},
                   description='Set the maximum number of plotted data points'),
            Option(short='V',
                   long='grids',
                   kwargs={'show_grids' : True},
                   description='Display the x-y-z grids in the resulting plot'),
    ]

    KWARGS = [
            Kwarg(name='axis', default=3),
            Kwarg(name='max_points', default=0),
            Kwarg(name='show_grids', default=False),
            Kwarg(name='enabled', default=False),
    ]

    # There isn't really any useful data to print to console. Disable header and result output.
    HEADER = None
    RESULT = None

    def init(self):
        import pyqtgraph.opengl as gl
        from pyqtgraph.Qt import QtGui

        self.verbose = self.config.verbose
        self.offset = self.config.offset
        self.length = self.config.length
        self.plane_count = -1
        self.plot_points = None

        if self.axis == 2:
            self.MAX_PLOT_POINTS = self.MAX_2D_PLOT_POINTS
            self._generate_data_point = self._generate_2d_data_point
        elif self.axis == 3:
            self.MAX_PLOT_POINTS = self.MAX_3D_PLOT_POINTS
            self._generate_data_point = self._generate_3d_data_point
        else:
            raise Exception("Invalid Plotter axis specified: %d. Must be one of: [2,3]" % self.axis)

        if not self.max_points:
            self.max_points = self.MAX_PLOT_POINTS

        self.app = QtGui.QApplication([])
        self.window = gl.GLViewWidget()
        self.window.opts['distance'] = self.VIEW_DISTANCE
        
        if len(self.config.target_files) == 1:
            self.window.setWindowTitle(self.config.target_files[0].name)

    def _print(self, message):
        '''
        Print console messages. For internal use only.
        '''
        if self.verbose:
            print(message)

    def _generate_plot_points(self, data_points):
        '''
        Generates plot points from a list of data points.
        
        @data_points - A dictionary containing each unique point and its frequency of occurance.

        Returns a set of plot points.
        '''
        total = 0
        min_weight = 0
        weightings = {}
        plot_points = {}

        # If the number of data points exceeds the maximum number of allowed data points, use a
        # weighting system to eliminate data points that occur less freqently.
        if sum(data_points.itervalues()) > self.max_points:

            # First, generate a set of weight values 1 - 10
            for i in range(1, 11):
                weightings[i] = 0

            # Go through every data point and how many times that point occurs
            for (point, count) in iterator(data_points):
                # For each data point, compare it to each remaining weight value
                for w in get_keys(weightings):

                    # If the number of times this data point occurred is >= the weight value,
                    # then increment the weight value. Since weight values are ordered lowest
                    # to highest, this means that more frequent data points also increment lower
                    # weight values. Thus, the more high-frequency data points there are, the
                    # more lower-frequency data points are eliminated.
                    if count >= w:
                        weightings[w] += 1
                    else:
                        break

                    # Throw out weight values that exceed the maximum number of data points
                    if weightings[w] > self.max_points:
                        del weightings[w]

                # If there's only one weight value left, no sense in continuing the loop...
                if len(weightings) == 1:
                    break

            # The least weighted value is our minimum weight
            min_weight = min(weightings)

            # Get rid of all data points that occur less frequently than our minimum weight
            for point in get_keys(data_points):
                if data_points[point] < min_weight:
                    del data_points[point]

        for point in sorted(data_points, key=data_points.get, reverse=True):
            plot_points[point] = data_points[point]
            # Register this as a result in case future modules need access to the raw point information,
            # but mark plot as False to prevent the entropy module from attempting to overlay this data on its graph.
            self.result(point=point, plot=False)
            total += 1
            if total >= self.max_points:
                break
                    
        return plot_points

    def _generate_data_point(self, data):
        '''
        Subclasses must override this to return the appropriate data point.

        @data - A string of data self.axis in length.

        Returns a data point tuple.
        '''
        return (0,0,0)

    def _generate_data_points(self, fp):
        '''
        Generates a dictionary of data points and their frequency of occurrance.

        @fp - The BlockFile object to generate data points from.

        Returns a dictionary.
        '''
        i = 0
        data_points = {}

        self._print("Generating data points for %s" % fp.name)

        # We don't need any extra data from BlockFile
        fp.set_block_size(peek=0)

        while True:
            (data, dlen) = fp.read_block()
            if not data or not dlen:
                break

            i = 0
            while (i+(self.axis-1)) < dlen:
                point = self._generate_data_point(data[i:i+self.axis])
                if has_key(data_points, point):    
                    data_points[point] += 1
                else:
                    data_points[point] = 1
                i += 3

        return data_points

    def _generate_plot(self, plot_points):
        import numpy as np
        import pyqtgraph.opengl as gl
        
        nitems = float(len(plot_points))

        pos = np.empty((nitems, 3))
        size = np.empty((nitems))
        color = np.empty((nitems, 4))

        i = 0
        for (point, weight) in iterator(plot_points):
            r = 0.0
            g = 0.0
            b = 0.0

            pos[i] = point
            frequency_percentage = (weight / nitems)

            # Give points that occur more frequently a brighter color and larger point size.
            # Frequency is determined as a percentage of total unique data points.
            if frequency_percentage > .005:
                size[i] = .20
                r = 1.0
            elif frequency_percentage > .002:
                size[i] = .10
                g = 1.0
                r = 1.0
            else:
                size[i] = .05
                g = 1.0

            color[i] = (r, g, b, 1.0)

            i += 1

        scatter_plot = gl.GLScatterPlotItem(pos=pos, size=size, color=color, pxMode=False)
        scatter_plot.translate(-127.5, -127.5, -127.5)

        return scatter_plot

    def plot(self, wait=True):
        import pyqtgraph.opengl as gl

        self.window.show()

        if self.show_grids:
            xgrid = gl.GLGridItem()
            ygrid = gl.GLGridItem()
            zgrid = gl.GLGridItem()

            self.window.addItem(xgrid)
            self.window.addItem(ygrid)
            self.window.addItem(zgrid)

            # Rotate x and y grids to face the correct direction
            xgrid.rotate(90, 0, 1, 0)
            ygrid.rotate(90, 1, 0, 0)

            # Scale grids to the appropriate dimensions
            xgrid.scale(12.8, 12.8, 12.8)
            ygrid.scale(12.8, 12.8, 12.8)
            zgrid.scale(12.8, 12.8, 12.8)

        for fd in iter(self.next_file, None):
            data_points = self._generate_data_points(fd)

            self._print("Generating plot points from %d data points" % len(data_points))

            self.plot_points = self._generate_plot_points(data_points)
            del data_points

            self._print("Generating graph from %d plot points" % len(self.plot_points))

            self.window.addItem(self._generate_plot(self.plot_points))

        if wait:
            self.wait()

    def wait(self):
        from pyqtgraph.Qt import QtCore, QtGui

        t = QtCore.QTimer()
        t.start(50)
        QtGui.QApplication.instance().exec_()

    def _generate_3d_data_point(self, data):
        '''
        Plot data points within a 3D cube.
        '''
        return (ord(data[0]), ord(data[1]), ord(data[2]))
    
    def _generate_2d_data_point(self, data):
        '''
        Plot data points projected on each cube face.
        '''
        self.plane_count += 1
        if self.plane_count > 5:
            self.plane_count = 0

        if self.plane_count == 0:
            return (0, ord(data[0]), ord(data[1]))
        elif self.plane_count == 1:
            return (ord(data[0]), 0, ord(data[1]))
        elif self.plane_count == 2:
            return (ord(data[0]), ord(data[1]), 0)
        elif self.plane_count == 3:
            return (255, ord(data[0]), ord(data[1]))
        elif self.plane_count == 4:
            return (ord(data[0]), 255, ord(data[1]))
        elif self.plane_count == 5:
            return (ord(data[0]), ord(data[1]), 255)
    
    def run(self):
        self.plot()
        return True


########NEW FILE########
__FILENAME__ = compression
# Performs raw decompression of various compression algorithms (currently, only deflate).

import os
import binwalk.core.C
from binwalk.core.module import Option, Kwarg, Module

class Deflate(object):
    '''
    Finds and extracts raw deflate compression streams.
    '''

    ENABLED = False
    BLOCK_SIZE = 33*1024
    # To prevent many false positives, only show data that decompressed to a reasonable size and didn't just result in a bunch of NULL bytes
    MIN_DECOMP_SIZE = 32*1024
    DESCRIPTION = "Raw deflate compression stream"

    TINFL_NAME = "tinfl"

    TINFL_FUNCTIONS = [
            binwalk.core.C.Function(name="is_deflated", type=int),
            binwalk.core.C.Function(name="inflate_raw_file", type=None),
    ]

    def __init__(self, module):
        self.module = module

        # The tinfl library is built and installed with binwalk
        self.tinfl = binwalk.core.C.Library(self.TINFL_NAME, self.TINFL_FUNCTIONS)
        
        # Add an extraction rule
        if self.module.extractor.enabled:
            self.module.extractor.add_rule(regex='^%s' % self.DESCRIPTION.lower(), extension="deflate", cmd=self._extractor)

    def _extractor(self, file_name):
        out_file = os.path.splitext(file_name)[0]
        self.tinfl.inflate_raw_file(file_name, out_file)

    def decompress(self, data):
        description = None

        decomp_size = self.tinfl.is_deflated(data, len(data), 0)
        if decomp_size >= self.MIN_DECOMP_SIZE:
            description = self.DESCRIPTION + ', uncompressed size >= %d' % decomp_size

        return description

class RawCompression(Module):

    DECOMPRESSORS = {
            'deflate' : Deflate,
    }

    TITLE = 'Raw Compression'

    CLI = [
            Option(short='X',
                   long='deflate',
                   kwargs={'enabled' : True, 'decompressor_class' : 'deflate'},
                   description='Scan for raw deflate compression streams'),
    ]

    KWARGS = [
            Kwarg(name='enabled', default=False),
            Kwarg(name='decompressor_class', default=None),
    ]

    def init(self):
        self.decompressor = self.DECOMPRESSORS[self.decompressor_class](self)

    def run(self):
        for fp in iter(self.next_file, None):

            fp.set_block_size(peek=self.decompressor.BLOCK_SIZE)

            self.header()

            while True:
                (data, dlen) = fp.read_block()
                if not data:
                    break

                for i in range(0, dlen):
                    description = self.decompressor.decompress(data[i:i+self.decompressor.BLOCK_SIZE])
                    if description:
                        self.result(description=description, file=fp, offset=fp.tell()-dlen+i)

                self.status.completed = fp.tell() - fp.offset

            self.footer()


########NEW FILE########
__FILENAME__ = entropy
# Calculates and optionally plots the entropy of input files.

import os
import math
import binwalk.core.common
from binwalk.core.compat import *
from binwalk.core.module import Module, Option, Kwarg

class Entropy(Module):

    XLABEL = 'Offset'
    YLABEL = 'Entropy'

    XUNITS = 'B'
    YUNITS = 'E'

    FILE_WIDTH = 1024
    FILE_FORMAT = 'png'

    COLORS = ['r', 'g', 'c', 'b', 'm']

    DEFAULT_BLOCK_SIZE = 1024

    TITLE = "Entropy Analysis"
    ORDER = 8
    
    CLI = [
            Option(short='E',
                   long='entropy',
                   kwargs={'enabled' : True},
                   description='Calculate file entropy'),
            Option(short='J',
                   long='save',
                   kwargs={'save_plot' : True},
                   description='Save plot as a PNG'),
            Option(short='N',
                   long='nplot',
                   kwargs={'do_plot' : False},
                   description='Do not generate an entropy plot graph'),
            Option(short='Q',
                   long='nlegend',
                   kwargs={'show_legend' : False},
                   description='Omit the legend from the entropy plot graph'),
    ]

    KWARGS = [
            Kwarg(name='enabled', default=False),
            Kwarg(name='save_plot', default=False),
            Kwarg(name='display_results', default=True),
            Kwarg(name='do_plot', default=True),
            Kwarg(name='show_legend', default=True),
            Kwarg(name='block_size', default=0),
    ]

    # Run this module last so that it can process all other module's results and overlay them on the entropy graph
    PRIORITY = 0

    def init(self):
        self.HEADER[-1] = "ENTROPY"
        self.algorithm = self.shannon
        self.max_description_length = 0
        self.file_markers = {}

        # Get a list of all other module's results to mark on the entropy graph
        for (module, obj) in iterator(self.modules):
            for result in obj.results:
                if result.plot and result.file and result.description:
                    description = result.description.split(',')[0]

                    if not has_key(self.file_markers, result.file.name):
                        self.file_markers[result.file.name] = []

                    if len(description) > self.max_description_length:
                        self.max_description_length = len(description)

                    self.file_markers[result.file.name].append((result.offset, description))

        # If other modules have been run and they produced results, don't spam the terminal with entropy results
        if self.file_markers:
            self.display_results = False

        if not self.block_size:
            if self.config.block:
                self.block_size = self.config.block
            else:
                self.block_size = self.DEFAULT_BLOCK_SIZE

    def run(self):
        for fp in iter(self.next_file, None):

            if self.display_results:
                self.header()

            self.calculate_file_entropy(fp)

            if self.display_results:
                self.footer()
    
        if self.do_plot and not self.save_plot:    
            from pyqtgraph.Qt import QtGui
            QtGui.QApplication.instance().exec_()

    def calculate_file_entropy(self, fp):
        # Clear results from any previously analyzed files
        self.clear(results=True)

        while True:
            file_offset = fp.tell()

            (data, dlen) = fp.read_block()
            if not data:
                break

            i = 0
            while i < dlen:
                entropy = self.algorithm(data[i:i+self.block_size])
                r = self.result(offset=(file_offset + i), file=fp, entropy=entropy, description=("%f" % entropy), display=self.display_results)
                i += self.block_size

        if self.do_plot:
            self.plot_entropy(fp.name)

    def shannon(self, data):
        '''
        Performs a Shannon entropy analysis on a given block of data.
        '''
        entropy = 0

        if data:
            length = len(data)
            
            seen = dict(((chr(x), 0) for x in range(0, 256)))
            for byte in data:
                seen[byte] += 1

            for x in range(0, 256):
                p_x = float(seen[chr(x)]) / length
                if p_x > 0:
                    entropy += - p_x*math.log(p_x, 2)

        return (entropy / 8)

    def gzip(self, data, truncate=True):
        '''
        Performs an entropy analysis based on zlib compression ratio.
        This is faster than the shannon entropy analysis, but not as accurate.
        '''
        # Entropy is a simple ratio of: <zlib compressed size> / <original size>
        e = float(float(len(zlib.compress(data, 9))) / float(len(data)))

        if truncate and e > 1.0:
            e = 1.0

        return e

    def plot_entropy(self, fname):
        import numpy as np
        import pyqtgraph as pg
        import pyqtgraph.exporters as exporters

        i = 0
        x = []
        y = []
        plotted_colors = {}

        for r in self.results:
            x.append(r.offset)
            y.append(r.entropy)

        plt = pg.plot(title=fname, clear=True)

        if self.show_legend and has_key(self.file_markers, fname):
            plt.addLegend(size=(self.max_description_length*10, 0))

            for (offset, description) in self.file_markers[fname]:
                # If this description has already been plotted at a different offset, we need to 
                # use the same color for the marker, but set the description to None to prevent
                # duplicate entries in the graph legend.
                #
                # Else, get the next color and use it to mark descriptions of this type.
                if has_key(plotted_colors, description):
                    color = plotted_colors[description]
                    description = None
                else:
                    color = self.COLORS[i]
                    plotted_colors[description] = color

                    i += 1
                    if i >= len(self.COLORS):
                        i = 0

                plt.plot(x=[offset,offset], y=[0,1.1], name=description, pen=pg.mkPen(color, width=2.5))

        # Plot data points
        plt.plot(x, y, pen='y')

        # TODO: legend is not displayed properly when saving plots to disk
        if self.save_plot:
            exporter = exporters.ImageExporter.ImageExporter(plt.plotItem)
            exporter.parameters()['width'] = self.FILE_WIDTH
            exporter.export(binwalk.core.common.unique_file_name(os.path.basename(fname), self.FILE_FORMAT))
        else:
            plt.setLabel('left', self.YLABEL, units=self.YUNITS)
            plt.setLabel('bottom', self.XLABEL, units=self.XUNITS)


########NEW FILE########
__FILENAME__ = extractor
# Performs extraction of data that matches extraction rules.
# This is automatically invoked by core.module code if extraction has been
# enabled by the user; other modules need not reference this module directly.

import os
import re
import sys
import shlex
import tempfile
import subprocess
import binwalk.core.common
from binwalk.core.compat import *
from binwalk.core.module import Module, Option, Kwarg
from binwalk.core.common import file_size, unique_file_name, BlockFile

class Extractor(Module):
    '''
    Extractor class, responsible for extracting files from the target file and executing external applications, if requested.
    '''
    # Extract rules are delimited with a colon.
    # <case insensitive matching string>:<file extension>[:<command to run>]
    RULE_DELIM = ':'

    # Comments in the extract.conf files start with a pound
    COMMENT_DELIM ='#'

    # Place holder for the extracted file name in the command 
    FILE_NAME_PLACEHOLDER = '%e'

    TITLE = 'Extraction'
    ORDER = 9
    PRIMARY = False

    CLI = [
            Option(short='e',
                   long='extract',
                   kwargs={'load_default_rules' : True, 'enabled' : True},
                   description='Automatically extract known file types'),
            Option(short='D',
                   long='dd',
                   type=list,
                   dtype='type:ext:cmd',
                   kwargs={'manual_rules' : [], 'enabled' : True},
                   description='Extract <type> signatures, give the files an extension of <ext>, and execute <cmd>'),
            Option(short='M',
                   long='matryoshka',
                   kwargs={'matryoshka' : 8},
                   description='Recursively scan extracted files'),
            Option(short='d',
                   long='depth',
                   type=int,
                   kwargs={'matryoshka' : 0},
                   description='Limit matryoshka recursion depth (default: 8 levels deep)'),
            Option(short='j',
                   long='size',
                   type=int,
                   kwargs={'max_size' : 0},
                   description='Limit the size of each extracted file'),
            Option(short='r',
                   long='rm',
                   kwargs={'remove_after_execute' : True},
                   description='Cleanup extracted / zero-size files after extraction'),
            Option(short='z',
                   long='carve',
                   kwargs={'run_extractors' : False},
                   description="Carve data from files, but don't execute extraction utilities"),
    ]

    KWARGS = [
            Kwarg(name='max_size', default=None),
            Kwarg(name='remove_after_execute', default=False),
            Kwarg(name='load_default_rules', default=False),
            Kwarg(name='run_extractors', default=True),
            Kwarg(name='manual_rules', default=[]),
            Kwarg(name='matryoshka', default=0),
            Kwarg(name='enabled', default=False),
    ]

    def load(self):
        # Holds a list of extraction rules loaded either from a file or when manually specified.
        self.extract_rules = []

        if self.load_default_rules:
            self.load_defaults()

        for manual_rule in self.manual_rules:
            self.add_rule(manual_rule)

        if self.matryoshka:
            self.config.verbose = True

    def reset(self):
        # Holds a list of pending files that should be scanned; only populated if self.matryoshka == True
        self.pending = []
        # Holds a dictionary of extraction directories created for each scanned file.
        self.extraction_directories = {}
        # Holds a dictionary of the last directory listing for a given directory; used for identifying
        # newly created/extracted files that need to be appended to self.pending.
        self.last_directory_listing = {}
        # Set to the directory path of the first extracted directory; this allows us to track recursion depth.
        self.base_recursion_dir = ""

    def callback(self, r):
        # Make sure the file attribute is set to a compatible instance of binwalk.core.common.BlockFile
        try:
            r.file.size
        except KeyboardInterrupt as e:
            pass
        except Exception as e:
            return

        if not r.size:
            size = r.file.size - r.offset
        else:
            size = r.size

        if r.valid:
            binwalk.core.common.debug("Extractor callback for %s:%d [%s & %s & %s]" % (r.file.name, r.offset, str(r.valid), str(r.display), str(r.extract)))
        
        # Only extract valid results that have been marked for extraction
        if r.valid and r.extract:
            # Do the extraction
            binwalk.core.common.debug("Attempting extraction...")
            (extraction_directory, dd_file) = self.extract(r.offset, r.description, r.file.name, size, r.name)

            # If the extraction was successful, self.extract will have returned the output directory and name of the dd'd file
            if extraction_directory and dd_file:
                # Get the full path to the dd'd file
                dd_file_path = os.path.join(extraction_directory, dd_file)

                # Do a directory listing of the output directory
                directory_listing = set(os.listdir(extraction_directory))

                # If this is a newly created output directory, self.last_directory_listing won't have a record of it.
                # If we've extracted other files to this directory before, it will.
                if not has_key(self.last_directory_listing, extraction_directory):
                    self.last_directory_listing[extraction_directory] = set()

                # Loop through a list of newly created files (i.e., files that weren't listed in the last directory listing)
                for f in directory_listing.difference(self.last_directory_listing[extraction_directory]):
                    # Build the full file path and add it to the extractor results
                    file_path = os.path.join(extraction_directory, f)
                    real_file_path = os.path.realpath(file_path)
                    self.result(description=file_path, display=False)

                    # If recursion was specified, and the file is not the same one we just dd'd, and if it is not a directory
                    if self.matryoshka and file_path != dd_file_path and not os.path.isdir(file_path):
                        # If the recursion level of this file is less than or equal to our desired recursion level
                        if len(real_file_path.split(self.base_recursion_dir)[1].split(os.path.sep)) <= self.matryoshka:
                            # Add the file to our list of pending files
                            self.pending.append(file_path)

                # Update the last directory listing for the next time we extract a file to this same output directory
                self.last_directory_listing[extraction_directory] = directory_listing

    def append_rule(self, r):
        self.extract_rules.append(r.copy())

    def add_rule(self, txtrule=None, regex=None, extension=None, cmd=None):
        '''
        Adds a set of rules to the extraction rule list.

        @txtrule   - Rule string, or list of rule strings, in the format <regular expression>:<file extension>[:<command to run>]
        @regex     - If rule string is not specified, this is the regular expression string to use.
        @extension - If rule string is not specified, this is the file extension to use.
        @cmd       - If rule string is not specified, this is the command to run.
                     Alternatively a callable object may be specified, which will be passed one argument: the path to the file to extract.

        Returns None.
        '''
        rules = []
        match = False
        r = {
            'extension'    : '',
            'cmd'        : '',
            'regex'        : None
        }

        # Process single explicitly specified rule
        if not txtrule and regex and extension:
            r['extension'] = extension
            r['regex'] = re.compile(regex)
            if cmd:
                r['cmd'] = cmd
        
            self.append_rule(r)    
            return

        # Process rule string, or list of rule strings
        if not isinstance(txtrule, type([])):
            rules = [txtrule]
        else:
            rules = txtrule
        
        for rule in rules:
            r['cmd'] = ''
            r['extension'] = ''

            try:
                values = self._parse_rule(rule)
                match = values[0]
                r['regex'] = re.compile(values[0])
                r['extension'] = values[1]
                r['cmd'] = values[2]
            except KeyboardInterrupt as e:
                raise e
            except Exception:
                pass

            # Verify that the match string was retrieved.
            if match: 
                self.append_rule(r)

    def remove_rule(self, text):
        '''
        Remove all rules that match a specified text.

        @text - The text to match against.

        Returns the number of rules removed.
        '''
        rm = []

        for i in range(0, len(self.extract_rules)):
            if self.extract_rules[i]['regex'].match(text):
                rm.append(i)
        
        for i in rm:
            self.extract_rules.pop(i)

        return len(rm)

    def clear_rules(self):
        '''
        Deletes all extraction rules.

        Returns None.
        '''
        self.extract_rules = []

    def get_rules(self):
        '''
        Returns a list of all extraction rules.
        '''
        return self.extract_rules

    def load_from_file(self, fname):
        '''
        Loads extraction rules from the specified file.

        @fname - Path to the extraction rule file.
        
        Returns None.
        '''
        try:
            # Process each line from the extract file, ignoring comments
            with open(fname, 'r') as f:
                for rule in f.readlines():
                    self.add_rule(rule.split(self.COMMENT_DELIM, 1)[0])
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            raise Exception("Extractor.load_from_file failed to load file '%s': %s" % (fname, str(e)))

    def load_defaults(self):
        '''
        Loads default extraction rules from the user and system extract.conf files.

        Returns None.
        '''
        # Load the user extract file first to ensure its rules take precedence.
        extract_files = [
            self.config.settings.get_file_path('user', self.config.settings.EXTRACT_FILE),
            self.config.settings.get_file_path('system', self.config.settings.EXTRACT_FILE),
        ]

        for extract_file in extract_files:
            if extract_file:
                try:
                    self.load_from_file(extract_file)
                except KeyboardInterrupt as e:
                    raise e
                except Exception as e:
                    if binwalk.core.common.DEBUG:
                        raise Exception("Extractor.load_defaults failed to load file '%s': %s" % (extract_file, str(e)))

    def build_output_directory(self, path):
        '''
        Set the output directory for extracted files.

        @path - The path to the file that data will be extracted from.

        Returns None.
        '''
        # If we have not already created an output directory for this target file, create one now
        if not has_key(self.extraction_directories, path):
            output_directory = os.path.join(os.path.dirname(path), unique_file_name('_' + os.path.basename(path), extension='extracted'))

            if not os.path.exists(output_directory):
                os.mkdir(output_directory)

            self.extraction_directories[path] = output_directory
        # Else, just use the already created directory
        else:
            output_directory = self.extraction_directories[path]

        # Set the initial base extraction directory for later determining the level of recusion
        if not self.base_recursion_dir:
            self.base_recursion_dir = os.path.realpath(output_directory) + os.path.sep

        return output_directory


    def cleanup_extracted_files(self, tf=None):
        '''
        Set the action to take after a file is extracted.

        @tf - If set to True, extracted files will be cleaned up after running a command against them.
              If set to False, extracted files will not be cleaned up after running a command against them.
              If set to None or not specified, the current setting will not be changed.

        Returns the current cleanup status (True/False).
        '''
        if tf is not None:
            self.remove_after_execute = tf

        return self.remove_after_execute
    
    def extract(self, offset, description, file_name, size, name=None):
        '''
        Extract an embedded file from the target file, if it matches an extract rule.
        Called automatically by Binwalk.scan().

        @offset      - Offset inside the target file to begin the extraction.
        @description - Description of the embedded file to extract, as returned by libmagic.
        @file_name   - Path to the target file.
        @size        - Number of bytes to extract.
        @name        - Name to save the file as.

        Returns the name of the extracted file (blank string if nothing was extracted).
        '''
        fname = ''
        cleanup_extracted_fname = True
        original_dir = os.getcwd()
        rules = self._match(description)
        file_path = os.path.realpath(file_name)

        # No extraction rules for this file
        if not rules:
            return (None, None)

        output_directory = self.build_output_directory(file_name)

        # Extract to end of file if no size was specified    
        if not size:
            size = file_size(file_path) - offset
                
        if os.path.isfile(file_path):
            os.chdir(output_directory)
            
            # Loop through each extraction rule until one succeeds
            for i in range(0, len(rules)):
                rule = rules[i]

                # Copy out the data to disk, if we haven't already
                fname = self._dd(file_path, offset, size, rule['extension'], output_file_name=name)

                # If there was a command specified for this rule, try to execute it.
                # If execution fails, the next rule will be attempted.
                if rule['cmd']:

                    # Many extraction utilities will extract the file to a new file, just without
                    # the file extension (i.e., myfile.7z -> myfile). If the presumed resulting
                    # file name already exists before executing the extract command, do not attempt 
                    # to clean it up even if its resulting file size is 0.
                    if self.remove_after_execute:
                        extracted_fname = os.path.splitext(fname)[0]
                        if os.path.exists(extracted_fname):
                            cleanup_extracted_fname = False

                    # Execute the specified command against the extracted file
                    if self.run_extractors:
                        extract_ok = self.execute(rule['cmd'], fname)
                    else:
                        extract_ok = True

                    # Only clean up files if remove_after_execute was specified                
                    if extract_ok == True and self.remove_after_execute:

                        # Remove the original file that we extracted
                        try:
                            os.unlink(fname)
                        except KeyboardInterrupt as e:
                            raise e
                        except Exception as e:
                            pass

                        # If the command worked, assume it removed the file extension from the extracted file
                        # If the extracted file name file exists and is empty, remove it
                        if cleanup_extracted_fname and os.path.exists(extracted_fname) and file_size(extracted_fname) == 0:
                            try:
                                os.unlink(extracted_fname)
                            except KeyboardInterrupt as e:
                                raise e
                            except Exception as e:
                                pass
                    
                    # If the command executed OK, don't try any more rules
                    if extract_ok == True:
                        break
                    # Else, remove the extracted file if this isn't the last rule in the list.
                    # If it is the last rule, leave the file on disk for the user to examine.
                    elif i != (len(rules)-1):
                        try:
                            os.unlink(fname)
                        except KeyboardInterrupt as e:
                            raise e
                        except Exception as e:
                            pass

                # If there was no command to execute, just use the first rule
                else:
                    break

            os.chdir(original_dir)

        return (output_directory, fname)

    def _entry_offset(self, index, entries, description):
        '''
        Gets the offset of the first entry that matches the description.

        @index       - Index into the entries list to begin searching.
        @entries     - Dictionary of result entries.
        @description - Case insensitive description.

        Returns the offset, if a matching description is found.
        Returns -1 if a matching description is not found.
        '''
        description = description.lower()

        for (offset, infos) in entries[index:]:
            for info in infos:
                if info['description'].lower().startswith(description):
                    return offset
        return -1

    def _match(self, description):
        '''
        Check to see if the provided description string matches an extract rule.
        Called internally by self.extract().

        @description - Description string to check.

        Returns the associated rule dictionary if a match is found.
        Returns None if no match is found.
        '''
        rules = []
        description = description.lower()

        for rule in self.extract_rules:
            if rule['regex'].search(description):
                rules.append(rule)
        return rules

    def _parse_rule(self, rule):
        '''
        Parses an extraction rule.

        @rule - Rule string.

        Returns an array of ['<case insensitive matching string>', '<file extension>', '<command to run>'].
        '''
        return rule.strip().split(self.RULE_DELIM, 2)

    def _dd(self, file_name, offset, size, extension, output_file_name=None):
        '''
        Extracts a file embedded inside the target file.

        @file_name        - Path to the target file.
        @offset           - Offset inside the target file where the embedded file begins.
        @size             - Number of bytes to extract.
        @extension        - The file exension to assign to the extracted file on disk.
        @output_file_name - The requested name of the output file.

        Returns the extracted file name.
        '''
        total_size = 0
        # Default extracted file name is <hex offset>.<extension>
        default_bname = "%X" % offset

        if self.max_size and size > self.max_size:
            size = self.max_size

        if not output_file_name or output_file_name is None:
            bname = default_bname
        else:
            # Strip the output file name of invalid/dangerous characters (like file paths)    
            bname = os.path.basename(output_file_name)
        
        fname = unique_file_name(bname, extension)
            
        try:
            # Open the target file and seek to the offset
            fdin = self.config.open_file(file_name, length=size, offset=offset)
            
            # Open the output file
            try:
                fdout = BlockFile(fname, 'w')
            except KeyboardInterrupt as e:
                raise e
            except Exception as e:
                # Fall back to the default name if the requested name fails
                fname = unique_file_name(default_bname, extension)
                fdout = BlockFile(fname, 'w')

            while total_size < size:
                (data, dlen) = fdin.read_block()
                if not data:
                    break
                else:
                    fdout.write(str2bytes(data[:dlen]))
                    total_size += dlen

            # Cleanup
            fdout.close()
            fdin.close()
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            raise Exception("Extractor.dd failed to extract data from '%s' to '%s': %s" % (file_name, fname, str(e)))
       
        binwalk.core.common.debug("Carved data block 0x%X - 0x%X from '%s' to '%s'" % (offset, offset+size, file_name, fname)) 
        return fname

    def execute(self, cmd, fname):
        '''
        Execute a command against the specified file.

        @cmd   - Command to execute.
        @fname - File to run command against.

        Returns True on success, False on failure, or None if the external extraction utility could not be found.
        '''
        tmp = None
        rval = 0
        retval = True

        binwalk.core.common.debug("Running extractor '%s'" % str(cmd))

        try:
            if callable(cmd):
                try:
                    cmd(fname)
                except KeyboardInterrupt as e:
                    raise e
                except Exception as e:
                    binwalk.core.common.warning("Extractor.execute failed to run internal extractor '%s': %s" % (str(cmd), str(e)))
            else:
                # If not in debug mode, create a temporary file to redirect stdout and stderr to
                if not binwalk.core.common.DEBUG:
                    tmp = tempfile.TemporaryFile()

                # Execute.
                for command in cmd.split("&&"):
                    # Replace all instances of FILE_NAME_PLACEHOLDER in the command with fname
                    command = command.strip().replace(self.FILE_NAME_PLACEHOLDER, fname)

                    binwalk.core.common.debug("subprocess.call(%s, stdout=%s, stderr=%s)" % (command, str(tmp), str(tmp)))    
                    rval = subprocess.call(shlex.split(command), stdout=tmp, stderr=tmp)
                    binwalk.core.common.debug('External extractor command "%s" completed with return code %d' % (cmd, rval))
                    
                    if rval == 0:
                        retval = True
                    else:
                        retval = False
                        break

        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            # Silently ignore no such file or directory errors. Why? Because these will inevitably be raised when
            # making the switch to the new firmware mod kit directory structure. We handle this elsewhere, but it's
            # annoying to see this spammed out to the console every time.
            if binwalk.core.common.DEBUG or (not hasattr(e, 'errno') or e.errno != 2):
                binwalk.core.common.warning("Extractor.execute failed to run external extrator '%s': %s" % (str(cmd), str(e)))
            retval = None
        
        if tmp is not None:
            tmp.close()

        return retval
    


########NEW FILE########
__FILENAME__ = general
# Module to process general user input options (scan length, starting offset, etc).

import os
import sys
import argparse
import binwalk.core.filter
import binwalk.core.common
import binwalk.core.display
import binwalk.core.settings
from binwalk.core.compat import *
from binwalk.core.module import Module, Option, Kwarg, show_help

class General(Module):

    TITLE = "General"
    ORDER = 0

    DEFAULT_DEPENDS = []
        
    CLI = [
        Option(long='length',
               short='l',
               type=int,
               kwargs={'length' : 0},
               description='Number of bytes to scan'),
        Option(long='offset',
               short='o',
               type=int,
               kwargs={'offset' : 0},
               description='Start scan at this file offset'),
        Option(long='block',
               short='K',
               type=int,
               kwargs={'block' : 0},
               description='Set file block size'),
        Option(long='swap',
               short='g',
               type=int,
               kwargs={'swap_size' : 0},
               description='Reverse every n bytes before scanning'),
        Option(short='I',
               long='invalid',
               kwargs={'show_invalid' : True},
               description='Show results marked as invalid'),
        Option(short='x',
               long='exclude',
               kwargs={'exclude_filters' : []},
               type=list,
               dtype=str.__name__,
               description='Exclude results that match <str>'),
        Option(short='y',
               long='include',
               kwargs={'include_filters' : []},
               type=list,
               dtype=str.__name__,
               description='Only show results that match <str>'),
        Option(long='log',
               short='f',
               type=argparse.FileType,
               kwargs={'log_file' : None},
               description='Log results to file'),
        Option(long='csv',
               short='c',
               kwargs={'csv' : True},
               description='Log results to file in CSV format'),
        Option(long='term',
               short='t',
               kwargs={'format_to_terminal' : True},
               description='Format output to fit the terminal window'),
        Option(long='quiet',
               short='q',
               kwargs={'quiet' : True},
               description='Supress output to stdout'),
        Option(long='verbose',
               short='v',
               kwargs={'verbose' : True},
               description='Enable verbose output'),
        Option(short='h',
               long='help',
               kwargs={'show_help' : True},
               description='Show help output'),
        Option(long=None,
               short=None,
               type=binwalk.core.common.BlockFile,
               kwargs={'files' : []}),
    ]

    KWARGS = [
        Kwarg(name='length', default=0),
        Kwarg(name='offset', default=0),
        Kwarg(name='block', default=0),
        Kwarg(name='swap_size', default=0),
        Kwarg(name='show_invalid', default=False),
        Kwarg(name='include_filters', default=[]),
        Kwarg(name='exclude_filters', default=[]),
        Kwarg(name='log_file', default=None),
        Kwarg(name='csv', default=False),
        Kwarg(name='format_to_terminal', default=False),
        Kwarg(name='quiet', default=False),
        Kwarg(name='verbose', default=False),
        Kwarg(name='files', default=[]),
        Kwarg(name='show_help', default=False),
    ]

    PRIMARY = False

    def load(self):
        self.target_files = []

        # Order is important with these two methods        
        self._open_target_files()
        self._set_verbosity()

        #self.filter = binwalk.core.filter.Filter(self._display_invalid)
        self.filter = binwalk.core.filter.Filter(self.show_invalid)

        # Set any specified include/exclude filters
        for regex in self.exclude_filters:
            self.filter.exclude(regex)
        for regex in self.include_filters:
            self.filter.include(regex)

        self.settings = binwalk.core.settings.Settings()
        self.display = binwalk.core.display.Display(log=self.log_file,
                                                    csv=self.csv,
                                                    quiet=self.quiet,
                                                    verbose=self.verbose,
                                                    filter=self.filter,
                                                    fit_to_screen=self.format_to_terminal)
        
        if self.show_help:
            show_help()
            sys.exit(0)

    def reset(self):
        for fp in self.target_files:
            fp.reset()

    def __del__(self):
        self._cleanup()

    def __exit__(self, a, b, c):
        self._cleanup()

    def _cleanup(self):
        if hasattr(self, 'target_files'):
            for fp in self.target_files:
                fp.close()

    def _set_verbosity(self):
        '''
        Sets the appropriate verbosity.
        Must be called after self._test_target_files so that self.target_files is properly set.
        '''
        # If more than one target file was specified, enable verbose mode; else, there is
        # nothing in some outputs to indicate which scan corresponds to which file. 
        if len(self.target_files) > 1 and not self.verbose:
            self.verbose = True

    def open_file(self, fname, length=None, offset=None, swap=None, block=None, peek=None):
        '''
        Opens the specified file with all pertinent configuration settings.
        '''
        if length is None:
            length = self.length
        if offset is None:
            offset = self.offset
        if swap is None:
            swap = self.swap_size

        return binwalk.core.common.BlockFile(fname, length=length, offset=offset, swap=swap, block=block, peek=peek)

    def _open_target_files(self):
        '''
        Checks if the target files can be opened.
        Any files that cannot be opened are removed from the self.target_files list.
        '''
        # Validate the target files listed in target_files
        for tfile in self.files:
            # Ignore directories.
            if not os.path.isdir(tfile):
                # Make sure we can open the target files
                try:
                    self.target_files.append(self.open_file(tfile))
                except KeyboardInterrupt as e:
                    raise e
                except Exception as e:
                    self.error(description="Cannot open file : %s" % str(e))
        

########NEW FILE########
__FILENAME__ = hashmatch
# Performs fuzzy hashing against files/directories.
# Unlike other scans, this doesn't produce any file offsets, so its results are not applicable to 
# some other scans, such as the entropy scan.
# Additionally, this module currently doesn't support certian general options (length, offset, swap, etc),
# as the libfuzzy C library is responsible for opening and scanning the specified files.

import os
import re
import ctypes
import fnmatch
import binwalk.core.C
import binwalk.core.common
from binwalk.core.compat import *
from binwalk.core.module import Module, Option, Kwarg

class HashResult(object):
    '''
    Class for storing libfuzzy hash results.
    For internal use only.
    '''

    def __init__(self, name, hash=None, strings=None):
        self.name = name
        self.hash = hash
        self.strings = strings

class HashMatch(Module):
    '''
    Class for fuzzy hash matching of files and directories.
    '''
    DEFAULT_CUTOFF = 0
    CONSERVATIVE_CUTOFF = 90

    TITLE = "Fuzzy Hash"

    CLI = [
        Option(short='F',
               long='fuzzy',
               kwargs={'enabled' : True},
               description='Perform fuzzy hash matching on files/directories'),
        Option(short='u',
               long='cutoff',
               priority=100,
               type=int,
               kwargs={'cutoff' : DEFAULT_CUTOFF},
               description='Set the cutoff percentage'),
        Option(short='S',
               long='strings',
               kwargs={'strings' : True},
               description='Diff strings inside files instead of the entire file'),
        Option(short='s',
               long='same',
               kwargs={'same' : True, 'cutoff' : CONSERVATIVE_CUTOFF},
               description='Only show files that are the same'),
        Option(short='p',
               long='diff',
               kwargs={'same' : False, 'cutoff' : CONSERVATIVE_CUTOFF},
               description='Only show files that are different'),
        Option(short='n',
               long='name',
               kwargs={'filter_by_name' : True},
               description='Only compare files whose base names are the same'),
        Option(short='L',
               long='symlinks',
               kwargs={'symlinks' : True},
               description="Don't ignore symlinks"),
    ]

    KWARGS = [
        Kwarg(name='cutoff', default=DEFAULT_CUTOFF),
        Kwarg(name='strings', default=False),
        Kwarg(name='same', default=True),
        Kwarg(name='symlinks', default=False),
        Kwarg(name='max_results', default=None),
        Kwarg(name='abspath', default=False),
        Kwarg(name='filter_by_name', default=False),
        Kwarg(name='symlinks', default=False),
        Kwarg(name='enabled', default=False),
    ]

    # Requires libfuzzybinwalk.so
    LIBRARY_NAME = "infuzzy"
    LIBRARY_FUNCTIONS = [
            binwalk.core.C.Function(name="fuzzy_hash_buf", type=int),
            binwalk.core.C.Function(name="fuzzy_hash_filename", type=int),
            binwalk.core.C.Function(name="fuzzy_compare", type=int),
    ]

    # Max result is 148 (http://ssdeep.sourceforge.net/api/html/fuzzy_8h.html)
    FUZZY_MAX_RESULT = 150
    # Files smaller than this won't produce meaningful fuzzy results (from ssdeep.h)
    FUZZY_MIN_FILE_SIZE = 4096

    HEADER_FORMAT = "\n%s" + " " * 11 + "%s\n" 
    RESULT_FORMAT = "%d%%" + " " * 17 + "%s\n"
    HEADER = ["SIMILARITY", "FILE NAME"]
    RESULT = ["percentage", "description"]

    def init(self):
        self.total = 0
        self.last_file1 = HashResult(None)
        self.last_file2 = HashResult(None)

        self.lib = binwalk.core.C.Library(self.LIBRARY_NAME, self.LIBRARY_FUNCTIONS)

    def _get_strings(self, fname):
        return ''.join(list(binwalk.core.common.strings(fname, minimum=10)))

    def _show_result(self, match, fname):
        if self.abspath:
            fname = os.path.abspath(fname)

        # Add description string padding for alignment
        if match < 100:
            fname = ' ' + fname
        if match < 10:
            fname = ' ' + fname

        self.result(percentage=match, description=fname, plot=False)

    def _compare_files(self, file1, file2):
        '''
        Fuzzy diff two files.
            
        @file1 - The first file to diff.
        @file2 - The second file to diff.
    
        Returns the match percentage.    
        Returns None on error.
        '''
        status = 0
        file1_dup = False
        file2_dup = False

        if not self.filter_by_name or os.path.basename(file1) == os.path.basename(file2):
            if os.path.exists(file1) and os.path.exists(file2):

                hash1 = ctypes.create_string_buffer(self.FUZZY_MAX_RESULT)
                hash2 = ctypes.create_string_buffer(self.FUZZY_MAX_RESULT)

                # Check if the last file1 or file2 matches this file1 or file2; no need to re-hash if they match.
                if file1 == self.last_file1.name and self.last_file1.hash:
                    file1_dup = True
                else:
                    self.last_file1.name = file1

                if file2 == self.last_file2.name and self.last_file2.hash:
                    file2_dup = True
                else:
                    self.last_file2.name = file2

                try:
                    if self.strings:
                        if file1_dup:
                            file1_strings = self.last_file1.strings
                        else:
                            self.last_file1.strings = file1_strings = self._get_strings(file1)
                            
                        if file2_dup:
                            file2_strings = self.last_file2.strings
                        else:
                            self.last_file2.strings = file2_strings = self._get_strings(file2)

                        if file1_strings == file2_strings:
                            return 100
                        else:
                            if file1_dup:
                                hash1 = self.last_file1.hash
                            else:
                                status |= self.lib.fuzzy_hash_buf(file1_strings, len(file1_strings), hash1)

                            if file2_dup:
                                hash2 = self.last_file2.hash
                            else:
                                status |= self.lib.fuzzy_hash_buf(file2_strings, len(file2_strings), hash2)
                        
                    else:
                        if file1_dup:
                            hash1 = self.last_file1.hash
                        else:
                            status |= self.lib.fuzzy_hash_filename(file1, hash1)
                            
                        if file2_dup:
                            hash2 = self.last_file2.hash
                        else:
                            status |= self.lib.fuzzy_hash_filename(file2, hash2)
                
                    if status == 0:
                        if not file1_dup:
                            self.last_file1.hash = hash1
                        if not file2_dup:
                            self.last_file2.hash = hash2

                        if hash1.raw == hash2.raw:
                            return 100
                        else:
                            return self.lib.fuzzy_compare(hash1, hash2)
                except Exception as e:
                    binwalk.core.common.warning("Exception while doing fuzzy hash: %s" % str(e))

        return None

    def is_match(self, match):
        '''
        Returns True if this is a good match.
        Returns False if his is not a good match.
        '''
        return (match is not None and ((match >= self.cutoff and self.same) or (match < self.cutoff and not self.same)))

    def _get_file_list(self, directory):
        '''
        Generates a directory tree.

        @directory - The root directory to start from.

        Returns a set of file paths, excluding the root directory.
        '''
        file_list = []

        # Normalize directory path so that we can exclude it from each individual file path
        directory = os.path.abspath(directory) + os.path.sep

        for (root, dirs, files) in os.walk(directory):
            # Don't include the root directory in the file paths
            root = ''.join(root.split(directory, 1)[1:])

            # Get a list of files, with or without symlinks as specified during __init__
            files = [os.path.join(root, f) for f in files if self.symlinks or not os.path.islink(f)]

            file_list += files
            
        return set(file_list)

    def hash_files(self, needle, haystack):
        '''
        Compare one file against a list of other files.
        
        Returns a list of tuple results.
        '''
        self.total = 0

        for f in haystack:
            m = self._compare_files(needle, f)
            if m is not None and self.is_match(m):
                self._show_result(m, f)
                    
                self.total += 1
                if self.max_results and self.total >= self.max_results:
                    break

    def hash_file(self, needle, haystack):
        '''
        Search for one file inside one or more directories.

        Returns a list of tuple results.
        '''
        matching_files = []
        self.total = 0
        done = False

        for directory in haystack:
            for f in self._get_file_list(directory):
                f = os.path.join(directory, f)
                m = self._compare_files(needle, f)
                if m is not None and self.is_match(m):
                    self._show_result(m, f)
                    matching_files.append((m, f))
                    
                    self.total += 1
                    if self.max_results and self.total >= self.max_results:
                        done = True
                        break
            if done:
                break
                    
        return matching_files

    def hash_directories(self, needle, haystack):
        '''
        Compare the contents of one directory with the contents of other directories.

        Returns a list of tuple results.
        '''
        done = False
        self.total = 0

        source_files = self._get_file_list(needle)

        for directory in haystack:
            dir_files = self._get_file_list(directory)

            for source_file in source_files:
                for dir_file in dir_files:
                    file1 = os.path.join(needle, source_file)
                    file2 = os.path.join(directory, dir_file)

                    m = self._compare_files(file1, file2)
                    if m is not None and self.is_match(m):
                        self._show_result(m, "%s => %s" % (file1, file2))

                        self.total += 1
                        if self.max_results and self.total >= self.max_results:
                            done = True
                            break
            if done:
                break

    def run(self):
        '''
        Main module method.
        '''
        # Access the raw self.config.files list directly here, since we accept both
        # files and directories and self.next_file only works for files.
        needle = self.config.files[0]
        haystack = self.config.files[1:]

        self.header()
                
        if os.path.isfile(needle):
            if os.path.isfile(haystack[0]):
                self.hash_files(needle, haystack)
            else:
                self.hash_file(needle, haystack)
        else:
            self.hash_directories(needle, haystack)

        self.footer()

        return True

########NEW FILE########
__FILENAME__ = heuristics
# Routines to perform Chi Squared tests. 
# Used for fingerprinting unknown areas of high entropy (e.g., is this block of high entropy data compressed or encrypted?).
# Inspired by people who actually know what they're doing: http://www.fourmilab.ch/random/

import math
from binwalk.core.compat import *
from binwalk.core.module import Module, Kwarg, Option, Dependency

class ChiSquare(object):
    '''
    Performs a Chi Squared test against the provided data.
    '''

    IDEAL = 256.0

    def __init__(self):
        '''
        Class constructor.

        Returns None.
        '''
        self.bytes = {}
        self.freedom = self.IDEAL - 1 
        
        # Initialize the self.bytes dictionary with keys for all possible byte values (0 - 255)
        for i in range(0, int(self.IDEAL)):
            self.bytes[chr(i)] = 0
        
        self.reset()

    def reset(self):
        self.xc2 = 0.0
        self.byte_count = 0

        for key in self.bytes.keys():
            self.bytes[key] = 0        

    def update(self, data):
        '''
        Updates the current byte counts with new data.

        @data - String of bytes to update.

        Returns None.
        '''
        # Count the number of occurances of each byte value
        for i in data:
            self.bytes[i] += 1

        self.byte_count += len(data)

    def chisq(self):
        '''
        Calculate the Chi Square critical value.

        Returns the critical value.
        '''
        expected = self.byte_count / self.IDEAL

        if expected:
            for byte in self.bytes.values():
                self.xc2 += ((byte - expected) ** 2 ) / expected

        return self.xc2

class EntropyBlock(object):

    def __init__(self, **kwargs):
        self.start = None
        self.end = None
        self.length = None
        for (k,v) in iterator(kwargs):
            setattr(self, k, v)

class HeuristicCompressionAnalyzer(Module):
    '''
    Performs analysis and attempts to interpret the results.
    '''

    BLOCK_SIZE = 32
    CHI_CUTOFF = 512
    ENTROPY_TRIGGER = .90
    MIN_BLOCK_SIZE = 4096
    BLOCK_OFFSET = 1024
    ENTROPY_BLOCK_SIZE = 1024

    TITLE = "Heuristic Compression"

    DEPENDS = [
            Dependency(name='Entropy',
                       attribute='entropy',
                       kwargs={'enabled' : True, 'do_plot' : False, 'display_results' : False, 'block_size' : ENTROPY_BLOCK_SIZE}),
    ]
    
    CLI = [
            Option(short='H',
                   long='heuristic',
                   kwargs={'enabled' : True},
                   description='Heuristically classify high entropy data'),
            Option(short='a',
                   long='trigger',
                   kwargs={'trigger_level' : 0},
                   type=float,
                   description='Set the entropy trigger level (0.0 - 1.0, default: %.2f)' % ENTROPY_TRIGGER),
    ]

    KWARGS = [
            Kwarg(name='enabled', default=False),
            Kwarg(name='trigger_level', default=ENTROPY_TRIGGER),
    ]

    def init(self):
        self.blocks = {}

        self.HEADER[-1] = "HEURISTIC ENTROPY ANALYSIS"

        # Trigger level sanity check
        if self.trigger_level > 1.0:
            self.trigger_level = 1.0
        elif self.trigger_level < 0.0:
            self.trigger_level = 0.0

        if self.config.block:
            self.block_size = self.config.block
        else:
            self.block_size = self.BLOCK_SIZE

        for result in self.entropy.results:
            if not has_key(self.blocks, result.file.name):
                self.blocks[result.file.name] = []

            if result.entropy >= self.trigger_level and (not self.blocks[result.file.name] or self.blocks[result.file.name][-1].end is not None):
                self.blocks[result.file.name].append(EntropyBlock(start=result.offset + self.BLOCK_OFFSET))
            elif result.entropy < self.trigger_level and self.blocks[result.file.name] and self.blocks[result.file.name][-1].end is None:
                self.blocks[result.file.name][-1].end = result.offset - self.BLOCK_OFFSET

    def run(self):
        for fp in iter(self.next_file, None):
            
            if has_key(self.blocks, fp.name):

                self.header()
                
                for block in self.blocks[fp.name]:

                    if block.end is None:
                        block.length = fp.offset + fp.length - block.start
                    else:
                        block.length = block.end - block.start

                    if block.length >= self.MIN_BLOCK_SIZE:
                        self.analyze(fp, block)

                self.footer()

    def analyze(self, fp, block):
        '''
        Perform analysis and interpretation.
        '''
        i = 0
        num_error = 0
        analyzer_results = []

        chi = ChiSquare()
        fp.seek(block.start)

        while i < block.length:
            j = 0
            (d, dlen) = fp.read_block()
            if not d:
                break

            while j < dlen:
                chi.reset()

                data = d[j:j+self.block_size]
                if len(data) < self.block_size:
                    break

                chi.update(data)

                if chi.chisq() >= self.CHI_CUTOFF:
                    num_error += 1
                
                j += self.block_size

                if (j + i) > block.length:
                    break

            i += dlen

        if num_error > 0:
            verdict = 'Moderate entropy data, best guess: compressed'
        else:
            verdict = 'High entropy data, best guess: encrypted'

        desc = '%s, size: %d, %d low entropy blocks' % (verdict, block.length, num_error)
        self.result(offset=block.start, description=desc, file=fp)

########NEW FILE########
__FILENAME__ = hexdiff
import os
import sys
import curses
import string
import platform
import binwalk.core.common as common
from binwalk.core.compat import *
from binwalk.core.module import Module, Option, Kwarg

class HexDiff(Module):


    COLORS = {
        'red'   : '31',
        'green' : '32',
        'blue'  : '34',
    }

    SEPERATORS = ['\\', '/']
    DEFAULT_BLOCK_SIZE = 16

    SKIPPED_LINE = "*"
    CUSTOM_DISPLAY_FORMAT = "0x%.8X    %s"

    TITLE = "Binary Diffing"

    CLI = [
            Option(short='W',
                   long='hexdump',
                   kwargs={'enabled' : True},
                   description='Perform a hexdump / diff of a file or files'),
            Option(short='G',
                   long='green',
                   kwargs={'show_green' : True, 'show_blue' : False, 'show_red' : False},
                   description='Only show lines containing bytes that are the same among all files'),
            Option(short='i',
                   long='red',
                   kwargs={'show_red' : True, 'show_blue' : False, 'show_green' : False},
                   description='Only show lines containing bytes that are different among all files'),
            Option(short='U',
                   long='blue',
                   kwargs={'show_blue' : True, 'show_red' : False, 'show_green' : False},
                   description='Only show lines containing bytes that are different among some files'),
            Option(short='w',
                   long='terse',
                   kwargs={'terse' : True},
                   description='Diff all files, but only display a hex dump of the first file'),
    ]
    
    KWARGS = [
            Kwarg(name='show_red', default=True),
            Kwarg(name='show_blue', default=True),
            Kwarg(name='show_green', default=True),
            Kwarg(name='terse', default=False),
            Kwarg(name='enabled', default=False),
    ]

    RESULT_FORMAT = "%s\n"
    RESULT = ['display']
    
    def _no_colorize(self, c, color="red", bold=True):
        return c

    def _colorize(self, c, color="red", bold=True):
        attr = []

        attr.append(self.COLORS[color])
        if bold:
            attr.append('1')

        return "\x1b[%sm%s\x1b[0m" % (';'.join(attr), c)

    def _color_filter(self, data):
        red = '\x1b[' + self.COLORS['red'] + ';'
        green = '\x1b[' + self.COLORS['green'] + ';'
        blue = '\x1b[' + self.COLORS['blue'] + ';'

        if self.show_blue and blue in data:
            return True
        elif self.show_green and green in data:
            return True
        elif self.show_red and red in data:
            return True

        return False

    def hexascii(self, target_data, byte, offset):
        color = "green"

        for (fp_i, data_i) in iterator(target_data):
            diff_count = 0

            for (fp_j, data_j) in iterator(target_data):
                if fp_i == fp_j:
                    continue

                try:
                    if data_i[offset] != data_j[offset]:
                        diff_count += 1
                except IndexError as e:
                    diff_count += 1

            if diff_count == len(target_data)-1:
                color = "red"
            elif diff_count > 0:
                color = "blue"
                break

        hexbyte = self.colorize("%.2X" % ord(byte), color)
        
        if byte not in string.printable or byte in string.whitespace:
            byte = "."
        
        asciibyte = self.colorize(byte, color)

        return (hexbyte, asciibyte)

    def diff_files(self, target_files):
        last_line = None
        loop_count = 0
        sep_count = 0

        while True:
            line = ""
            done_files = 0
            block_data = {}
            seperator = self.SEPERATORS[sep_count % 2]

            for fp in target_files:
                block_data[fp] = fp.read(self.block)
                if not block_data[fp]:
                    done_files += 1

            # No more data from any of the target files? Done.
            if done_files == len(target_files):
                break

            for fp in target_files:
                hexline = ""
                asciiline = ""

                for i in range(0, self.block):
                    if i >= len(block_data[fp]):
                        hexbyte = "XX"
                        asciibyte = "."
                    else:
                        (hexbyte, asciibyte) = self.hexascii(block_data, block_data[fp][i], i)

                    hexline += "%s " % hexbyte
                    asciiline += "%s" % asciibyte

                line += "%s |%s|" % (hexline, asciiline)

                if self.terse:
                    break

                if fp != target_files[-1]:
                    line += " %s " % seperator

            offset = fp.offset + (self.block * loop_count)

            if not self._color_filter(line):
                display = line = self.SKIPPED_LINE
            else:
                display = self.CUSTOM_DISPLAY_FORMAT % (offset, line)
                sep_count += 1
            
            if line != self.SKIPPED_LINE or last_line != line:
                self.result(offset=offset, description=line, display=display)

            last_line = line
            loop_count += 1
                
    def init(self):
        # Disable the invalid description auto-filtering feature.
        # This will not affect our own validation.
        self.config.filter.show_invalid_results = True

        # Always disable terminal formatting, as it won't work properly with colorized output
        self.config.display.fit_to_screen = False

        # Set the block size (aka, hexdump line size)
        self.block = self.config.block
        if not self.block:
            self.block = self.DEFAULT_BLOCK_SIZE

        # Build a list of files to hexdiff
        self.hex_target_files = [x for x in iter(self.next_file, None)]

        # Build the header format string
        header_width = (self.block * 4) + 2
        if self.terse:
            file_count = 1
        else:
            file_count = len(self.hex_target_files)
        self.HEADER_FORMAT = "OFFSET      " + (("%%-%ds   " % header_width) * file_count) + "\n"

        # Build the header argument list
        self.HEADER = [fp.name for fp in self.hex_target_files]
        if self.terse and len(self.HEADER) > 1:
            self.HEADER = self.HEADER[0]

        # Set up the tty for colorization, if it is supported
        if hasattr(sys.stderr, 'isatty') and sys.stderr.isatty() and platform.system() != 'Windows':
            curses.setupterm()
            self.colorize = self._colorize
        else:
            self.colorize = self._no_colorize

    def run(self):
        if self.hex_target_files:
            self.header()
            self.diff_files(self.hex_target_files)
            self.footer()


########NEW FILE########
__FILENAME__ = signature
# Basic signature scan module. This is the default (and primary) feature of binwalk.

import binwalk.core.magic
import binwalk.core.smart
import binwalk.core.parser
from binwalk.core.module import Module, Option, Kwarg

class Signature(Module):

    TITLE = "Signature Scan"
    ORDER = 10

    CLI = [
            Option(short='B',
                   long='signature',
                   kwargs={'enabled' : True, 'explicit_signature_scan' : True},
                   description='Scan target file(s) for common file signatures'),
            Option(short='R',
                   long='raw',
                   kwargs={'enabled' : True, 'raw_bytes' : ''},
                   type=str,
                   description='Scan target file(s) for the specified sequence of bytes'),
            Option(short='A',
                   long='opcodes',
                   kwargs={'enabled' : True, 'search_for_opcodes' : True},
                   description='Scan target file(s) for common executable opcodes'),
            Option(short='C',
                   long='cast',
                   kwargs={'enabled' : True, 'cast_data_types' : True},
                   description='Cast offsets as a given data type (use -y to specify the data type / endianess)'),
            Option(short='m',
                   long='magic',
                   kwargs={'enabled' : True, 'magic_files' : []},
                   type=list,
                   dtype='file',
                   description='Specify a custom magic file to use'),
            Option(short='b',
                   long='dumb',
                   kwargs={'dumb_scan' : True},
                   description='Disable smart signature keywords'),
    ]

    KWARGS = [
            Kwarg(name='enabled', default=False),
            Kwarg(name='raw_bytes', default=None),
            Kwarg(name='search_for_opcodes', default=False),
            Kwarg(name='explicit_signature_scan', default=False),
            Kwarg(name='cast_data_types', default=False),
            Kwarg(name='dumb_scan', default=False),
            Kwarg(name='magic_files', default=[]),
    ]

    VERBOSE_FORMAT = "%s    %d"

    def init(self):
        # Create Signature and MagicParser class instances. These are mostly for internal use.
        self.smart = binwalk.core.smart.Signature(self.config.filter, ignore_smart_signatures=self.dumb_scan)
        self.parser = binwalk.core.parser.MagicParser(self.config.filter, self.smart)

        # If a raw byte sequence was specified, build a magic file from that instead of using the default magic files
        if self.raw_bytes is not None:
            self.magic_files = [self.parser.file_from_string(self.raw_bytes)]

        # Append the user's magic file first so that those signatures take precedence
        elif self.search_for_opcodes:
            self.magic_files = [
                    self.config.settings.get_file_path('user', self.config.settings.BINARCH_MAGIC_FILE),
                    self.config.settings.get_file_path('system', self.config.settings.BINARCH_MAGIC_FILE),
            ]

        elif self.cast_data_types:
            self.magic_files = [
                    self.config.settings.get_file_path('user', self.config.settings.BINCAST_MAGIC_FILE),
                    self.config.settings.get_file_path('system', self.config.settings.BINCAST_MAGIC_FILE),
            ]

        # Use the system default magic file if no other was specified, or if -B was explicitly specified
        if (not self.magic_files) or (self.explicit_signature_scan and not self.cast_data_types):
            self.magic_files.append(self.config.settings.get_file_path('user', self.config.settings.BINWALK_MAGIC_FILE))
            self.magic_files.append(self.config.settings.get_file_path('system', self.config.settings.BINWALK_MAGIC_FILE))

        # Parse the magic file(s) and initialize libmagic
        binwalk.core.common.debug("Loading magic files: %s" % str(self.magic_files))
        self.mfile = self.parser.parse(self.magic_files)
        self.magic = binwalk.core.magic.Magic(self.mfile)
        
        # Once the temporary magic files are loaded into libmagic, we don't need them anymore; delete the temp files
        self.parser.rm_magic_files()

        self.VERBOSE = ["Signatures:", self.parser.signature_count]

    def validate(self, r):
        '''
        Called automatically by self.result.
        '''
        if not r.description:
            r.valid = False

        if r.size and (r.size + r.offset) > r.file.size:
            r.valid = False

        if r.jump and (r.jump + r.offset) > r.file.size:
            r.valid = False

        r.valid = self.config.filter.valid_result(r.description)

    def scan_file(self, fp):
        current_file_offset = 0

        while True:
            (data, dlen) = fp.read_block()
            if not data:
                break

            current_block_offset = 0
            block_start = fp.tell() - dlen
            self.status.completed = block_start - fp.offset

            for candidate_offset in self.parser.find_signature_candidates(data, dlen):

                # current_block_offset is set when a jump-to-offset keyword is encountered while
                # processing signatures. This points to an offset inside the current data block
                # that scanning should jump to, so ignore any subsequent candidate signatures that
                # occurr before this offset inside the current data block.
                if candidate_offset < current_block_offset:
                    continue

                # Pass the data to libmagic for parsing
                magic_result = self.magic.buffer(data[candidate_offset:candidate_offset+fp.block_peek_size])
                if not magic_result:
                    continue
                
                # The smart filter parser returns a binwalk.core.module.Result object
                r = self.smart.parse(magic_result)

                # Set the absolute offset inside the target file
                r.offset = block_start + candidate_offset + r.adjust

                # Provide an instance of the current file object
                r.file = fp
        
                # Register the result for futher processing/display
                # self.result automatically calls self.validate for result validation
                self.result(r=r)
       
                # Is this a valid result and did it specify a jump-to-offset keyword?
                if r.valid and r.jump > 0:
                    absolute_jump_offset = r.offset + r.jump
                    current_block_offset = candidate_offset + r.jump

                    # If the jump-to-offset is beyond the confines of the current block, seek the file to
                    # that offset and quit processing this block of data.
                    if absolute_jump_offset >= fp.tell():
                        fp.seek(r.offset + r.jump)
                        break

    def run(self):
        for fp in iter(self.next_file, None):
            self.header()
            self.scan_file(fp)
            self.footer()

        if hasattr(self, "magic") and self.magic:
            self.magic.close()


########NEW FILE########
__FILENAME__ = compressd
import binwalk.core.C
import binwalk.core.plugin
from binwalk.core.common import *

class CompressdPlugin(binwalk.core.plugin.Plugin):
    '''
    Searches for and validates compress'd data.
    '''

    MODULES = ['Signature']

    READ_SIZE = 64

    COMPRESS42 = "compress42"
    COMPRESS42_FUNCTIONS = [
        binwalk.core.C.Function(name="is_compressed", type=bool),
    ]

    comp = None

    def init(self):
        self.comp = binwalk.core.C.Library(self.COMPRESS42, self.COMPRESS42_FUNCTIONS)

    def scan(self, result):
        if result.file and result.description.lower().startswith("compress'd data"):
            fd = self.module.config.open_file(result.file.name, offset=result.offset, length=self.READ_SIZE)
            compressed_data = fd.read(self.READ_SIZE)
            fd.close()
                        
            if not self.comp.is_compressed(compressed_data, len(compressed_data)):
                result.valid = False



########NEW FILE########
__FILENAME__ = cpio
import binwalk.core.plugin

class CPIOPlugin(binwalk.core.plugin.Plugin):
    '''
    Ensures that ASCII CPIO archive entries only get extracted once.    
    '''

    MODULES = ['Signature']

    def pre_scan(self):
        # Be sure to re-set this at the beginning of every scan
        self.found_archive = False
        self.found_archive_in_file = None

    def scan(self, result):
        if result.valid:
            # ASCII CPIO archives consist of multiple entries, ending with an entry named 'TRAILER!!!'.
            # Displaying each entry is useful, as it shows what files are contained in the archive,
            # but we only want to extract the archive when the first entry is found.
            if result.description.startswith('ASCII cpio archive'):
                if not self.found_archive or self.found_archive_in_file != result.file.name:
                    # This is the first entry. Set found_archive and allow the scan to continue normally.
                    self.found_archive_in_file = result.file.name
                    self.found_archive = True
                    result.extract = True
                elif 'TRAILER!!!' in result.description:
                    # This is the last entry, un-set found_archive.
                    self.found_archive = False
                    result.extract = False
                else:
                    # The first entry has already been found and this is not the last entry, or the last entry 
                    # has not yet been found. Don't extract.
                    result.extract = False
            else:
                # If this was a valid non-CPIO archive result, reset these values; else, a previous
                # false positive CPIO result could leave these set, causing a subsequent valid CPIO
                # result to not be extracted.
                self.found_archive = False
                self.found_archive_in_file = None

########NEW FILE########
__FILENAME__ = lzmamod
import os
import shutil
import binwalk.core.plugin
from binwalk.core.compat import *
from binwalk.core.common import BlockFile

class LZMAModPlugin(binwalk.core.plugin.Plugin):
    '''
    Finds and extracts modified LZMA files commonly found in cable modems.
    Based on Bernardo Rodrigues' work: http://w00tsec.blogspot.com/2013/11/unpacking-firmware-images-from-cable.html
    '''
    MODULES = ['Signature']

    FAKE_LZMA_SIZE = "\x00\x00\x00\x10\x00\x00\x00\x00"
    SIGNATURE = "lzma compressed data"

    def init(self):
        self.original_cmd = ''

        # Replace the existing LZMA extraction command with our own
        # Note that this assumes that there is *one* LZMA extraction command...
        rules = self.module.extractor.get_rules()
        for i in range(0, len(rules)):
            if rules[i]['regex'] and rules[i]['cmd'] and rules[i]['regex'].match(self.SIGNATURE):
                self.original_cmd = rules[i]['cmd']
                rules[i]['cmd'] = self.lzma_cable_extractor
                break

    def lzma_cable_extractor(self, fname):
        # Try extracting the LZMA file without modification first
        result = self.module.extractor.execute(self.original_cmd, fname)
        
        # If the external extractor was successul (True) or didn't exist (None), don't do anything.
        if result not in [True, None]:
            out_name = os.path.splitext(fname)[0] + '-patched' + os.path.splitext(fname)[1]
            fp_out = BlockFile(out_name, 'w')
            # Use self.module.config.open_file here to ensure that other config settings (such as byte-swapping) are honored
            fp_in = self.module.config.open_file(fname, offset=0, length=0)
            fp_in.set_block_size(peek=0)
            i = 0

            while i < fp_in.length:
                (data, dlen) = fp_in.read_block()
                
                if i == 0:
                    out_data = data[0:5] + self.FAKE_LZMA_SIZE + data[5:]
                else:
                    out_data = data
                
                fp_out.write(out_data)
    
                i += dlen

            fp_in.close()
            fp_out.close()

            # Overwrite the original file so that it can be cleaned up if -r was specified
            shutil.move(out_name, fname)
            self.module.extractor.execute(self.original_cmd, fname)

    def scan(self, result):
        # The modified cable modem LZMA headers all have valid dictionary sizes and a properties byte of 0x5D.
        if result.description.lower().startswith(self.SIGNATURE) and "invalid uncompressed size" in result.description:
            if "properties: 0x5D" in result.description and "invalid dictionary size" not in result.description:
                result.valid = True
                result.description = result.description.split("invalid uncompressed size")[0] + "missing uncompressed size"


########NEW FILE########
__FILENAME__ = tar
import time
import math
import binwalk.core.plugin

class TarPlugin(binwalk.core.plugin.Plugin):

    MODULES = ['Signature']

    # "borrowed from pythons tarfile module"
    TAR_BLOCKSIZE = 512

    def nts(self, s):
        """
        Convert a null-terminated string field to a python string.
        """
        # Use the string up to the first null char.
        p = s.find("\0")
        if p == -1:
            return s
        return s[:p]

    def nti(self, s):
        """
        Convert a number field to a python number.
        """
        # There are two possible encodings for a number field, see
        # itn() below.
        if s[0] != chr(0x80):
            try:
                n = int(self.nts(s) or "0", 8)
            except ValueError:
                raise ValueError("invalid tar header")
        else:
            n = 0
            for i in xrange(len(s) - 1):
                n <<= 8
                n += ord(s[i + 1])
        return n

    def scan(self, result):
        if result.description.lower().startswith('posix tar archive'):
            is_tar = True
            file_offset = result.offset
            fd = self.module.config.open_file(result.file.name, offset=result.offset)

            while is_tar:
                # read in the tar header struct
                buf = fd.read(self.TAR_BLOCKSIZE)
                
                # check to see if we are still in a tarball
                if buf[257:262] == 'ustar':
                    # get size of tarred file convert to blocks (plus 1 to include header)
                    try:
                        size = self.nti(buf[124:136])
                        blocks = math.ceil(size/float(self.TAR_BLOCKSIZE)) + 1
                    except ValueError as e:
                        is_tar = False
                        break

                    # update file offset for next file in tarball
                    file_offset += int(self.TAR_BLOCKSIZE*blocks)

                    if file_offset >= result.file.size:
                        # we hit the end of the file
                        is_tar = False
                    else:
                        fd.seek(file_offset)
                else:
                    is_tar = False            

            result.jump = file_offset

########NEW FILE########
__FILENAME__ = zlibvalid
import binwalk.core.C
import binwalk.core.plugin
from binwalk.core.common import BlockFile

class ZlibPlugin(binwalk.core.plugin.Plugin):
    '''
    Searches for and validates zlib compressed data.
    '''
    MODULES = ['Signature']

    MIN_DECOMP_SIZE = 16 * 1024
    MAX_DATA_SIZE = 33 * 1024

    TINFL = "tinfl"
    TINFL_FUNCTIONS = [
        binwalk.core.C.Function(name="is_deflated", type=int),
    ]

    def init(self):
        # Load libtinfl.so
        self.tinfl = binwalk.core.C.Library(self.TINFL, self.TINFL_FUNCTIONS)

    def scan(self, result):
        # If this result is a zlib signature match, try to decompress the data
        if result.file and result.description.lower().startswith('zlib'):
            # Seek to and read the suspected zlib data
            fd = self.module.config.open_file(result.file.name, offset=result.offset, length=self.MAX_DATA_SIZE)
            data = fd.read(self.MAX_DATA_SIZE)
            fd.close()

            # Check if this is valid zlib data
            decomp_size = self.tinfl.is_deflated(data, len(data), 1)
            if decomp_size > 0:
                result.description += ", uncompressed size >= %d" % decomp_size
            else:
                result.valid = False


########NEW FILE########
__FILENAME__ = example
#! /usr/bin/python

import magic

ms = magic.open(magic.NONE)
ms.load()
tp = ms.file("/bin/ls")
print (tp)

f = open("/bin/ls", "rb")
buf = f.read(4096)
f.close()

tp = ms.buffer(buf)
print (tp)

ms.close()

########NEW FILE########
__FILENAME__ = magic
#!/usr/bin/env python
'''
Python bindings for libmagic
'''

import ctypes

from ctypes import *
from ctypes.util import find_library

def _init():
    """
    Loads the shared library through ctypes and returns a library
    L{ctypes.CDLL} instance 
    """
    return ctypes.cdll.LoadLibrary(find_library('magic'))

_libraries = {}
_libraries['magic'] = _init()

# Flag constants for open and setflags
MAGIC_NONE = NONE = 0
MAGIC_DEBUG = DEBUG = 1
MAGIC_SYMLINK = SYMLINK = 2
MAGIC_COMPRESS = COMPRESS = 4
MAGIC_DEVICES = DEVICES = 8
MAGIC_MIME_TYPE = MIME_TYPE = 16
MAGIC_CONTINUE = CONTINUE = 32
MAGIC_CHECK = CHECK = 64
MAGIC_PRESERVE_ATIME = PRESERVE_ATIME = 128
MAGIC_RAW = RAW = 256
MAGIC_ERROR = ERROR = 512
MAGIC_MIME_ENCODING = MIME_ENCODING = 1024
MAGIC_MIME = MIME = 1040
MAGIC_APPLE = APPLE = 2048

MAGIC_NO_CHECK_COMPRESS = NO_CHECK_COMPRESS = 4096
MAGIC_NO_CHECK_TAR = NO_CHECK_TAR = 8192
MAGIC_NO_CHECK_SOFT = NO_CHECK_SOFT = 16384
MAGIC_NO_CHECK_APPTYPE = NO_CHECK_APPTYPE = 32768
MAGIC_NO_CHECK_ELF = NO_CHECK_ELF = 65536
MAGIC_NO_CHECK_TEXT = NO_CHECK_TEXT = 131072
MAGIC_NO_CHECK_CDF = NO_CHECK_CDF = 262144
MAGIC_NO_CHECK_TOKENS = NO_CHECK_TOKENS = 1048576
MAGIC_NO_CHECK_ENCODING = NO_CHECK_ENCODING = 2097152

MAGIC_NO_CHECK_BUILTIN = NO_CHECK_BUILTIN = 4173824

class magic_set(Structure):
    pass
magic_set._fields_ = []
magic_t = POINTER(magic_set)

_open = _libraries['magic'].magic_open
_open.restype = magic_t
_open.argtypes = [c_int]

_close = _libraries['magic'].magic_close
_close.restype = None
_close.argtypes = [magic_t]

_file = _libraries['magic'].magic_file
_file.restype = c_char_p
_file.argtypes = [magic_t, c_char_p]

_descriptor = _libraries['magic'].magic_descriptor
_descriptor.restype = c_char_p
_descriptor.argtypes = [magic_t, c_int]

_buffer = _libraries['magic'].magic_buffer
_buffer.restype = c_char_p
_buffer.argtypes = [magic_t, c_void_p, c_size_t]

_error = _libraries['magic'].magic_error
_error.restype = c_char_p
_error.argtypes = [magic_t]

_setflags = _libraries['magic'].magic_setflags
_setflags.restype = c_int
_setflags.argtypes = [magic_t, c_int]

_load = _libraries['magic'].magic_load
_load.restype = c_int
_load.argtypes = [magic_t, c_char_p]

_compile = _libraries['magic'].magic_compile
_compile.restype = c_int
_compile.argtypes = [magic_t, c_char_p]

_check = _libraries['magic'].magic_check
_check.restype = c_int
_check.argtypes = [magic_t, c_char_p]

_list = _libraries['magic'].magic_list
_list.restype = c_int
_list.argtypes = [magic_t, c_char_p]

_errno = _libraries['magic'].magic_errno
_errno.restype = c_int
_errno.argtypes = [magic_t]

class Magic(object):
    def __init__(self, ms):
        self._magic_t = ms

    def close(self):
        """
        Closes the magic database and deallocates any resources used.
        """
        _close(self._magic_t)

    def file(self, filename):
        """
        Returns a textual description of the contents of the argument passed
        as a filename or None if an error occurred and the MAGIC_ERROR flag
        is set.  A call to errno() will return the numeric error code.
        """
        try: # attempt python3 approach first
            bi = bytes(filename, 'utf-8')
            return str(_file(self._magic_t, bi), 'utf-8')
        except:
            return _file(self._magic_t, filename.encode('utf-8'))

    def descriptor(self, fd):
        """
        Like the file method, but the argument is a file descriptor.
        """
        return _descriptor(self._magic_t, fd)

    def buffer(self, buf):
        """
        Returns a textual description of the contents of the argument passed
        as a buffer or None if an error occurred and the MAGIC_ERROR flag
        is set. A call to errno() will return the numeric error code.
        """
        try: # attempt python3 approach first
            return str(_buffer(self._magic_t, buf, len(buf)), 'utf-8')
        except:
            return _buffer(self._magic_t, buf, len(buf))

    def error(self):
        """
        Returns a textual explanation of the last error or None
        if there was no error.
        """
        try: # attempt python3 approach first
            return str(_error(self._magic_t), 'utf-8')
        except:
            return _error(self._magic_t)
  
    def setflags(self, flags):
        """
        Set flags on the magic object which determine how magic checking behaves;
        a bitwise OR of the flags described in libmagic(3), but without the MAGIC_
        prefix.

        Returns -1 on systems that don't support utime(2) or utimes(2)
        when PRESERVE_ATIME is set.
        """
        return _setflags(self._magic_t, flags)

    def load(self, filename=None):
        """
        Must be called to load entries in the colon separated list of database files
        passed as argument or the default database file if no argument before
        any magic queries can be performed.
        
        Returns 0 on success and -1 on failure.
        """
        return _load(self._magic_t, filename)

    def compile(self, dbs):
        """
        Compile entries in the colon separated list of database files
        passed as argument or the default database file if no argument.
        Returns 0 on success and -1 on failure.
        The compiled files created are named from the basename(1) of each file
        argument with ".mgc" appended to it.
        """
        return _compile(self._magic_t, dbs)

    def check(self, dbs):
        """
        Check the validity of entries in the colon separated list of
        database files passed as argument or the default database file
        if no argument.
        Returns 0 on success and -1 on failure.
        """
        return _check(self._magic_t, dbs)

    def list(self, dbs):
        """
        Check the validity of entries in the colon separated list of
        database files passed as argument or the default database file
        if no argument.
        Returns 0 on success and -1 on failure.
        """
        return _list(self._magic_t, dbs)
    
    def errno(self):
        """
        Returns a numeric error code. If return value is 0, an internal
        magic error occurred. If return value is non-zero, the value is
        an OS error code. Use the errno module or os.strerror() can be used
        to provide detailed error information.
        """
        return _errno(self._magic_t)

def open(flags):
    """
    Returns a magic object on success and None on failure.
    Flags argument as for setflags.
    """
    return Magic(_open(flags))

########NEW FILE########
__FILENAME__ = binwalk_simple
#!/usr/bin/env python

import binwalk

# Since no options are specified, they are by default taken from sys.argv.
# Effecitvely, this duplicates the functionality of the normal binwalk script.
binwalk.Modules().execute()

########NEW FILE########
__FILENAME__ = signature_scan
#!/usr/bin/env python

import sys
import binwalk

try:
    # Perform a signature scan against the files specified on the command line and suppress the usual binwalk output.
	for module in binwalk.Modules().execute(*sys.argv[1:], signature=True, quiet=True):
		print ("%s Results:" % module.name)
		for result in module.results:
			print ("\t%s    0x%.8X    %s" % (result.file.name, result.offset, result.description))
except binwalk.ModuleException as e:
	pass

########NEW FILE########
