__FILENAME__ = asm_generic_ioctl
# Warning: not part of the published Quick2Wire API.
#
# Converted from <asm-generic/ioctl.h>

# ioctl command encoding: 32 bits total, command in lower 16 bits,
# size of the parameter structure in the lower 14 bits of the
# upper 16 bits.
#
# Encoding the size of the parameter structure in the ioctl request
# is useful for catching programs compiled with old versions
# and to avoid overwriting user space outside the user buffer area.
# The highest 2 bits are reserved for indicating the ``access mode''.
#
# NOTE: This limits the max parameter size to 16kB -1 !

# The following is for compatibility across the various Linux
# platforms.  The generic ioctl numbering scheme doesn't really enforce
# a type field.  De facto, however, the top 8 bits of the lower 16
# bits are indeed used as a type field, so we might just as well make
# this explicit here.  Please be sure to use the decoding macros
# below from now on.

import ctypes

_IOC_NRBITS =	8
_IOC_TYPEBITS =	8

_IOC_SIZEBITS =	14
_IOC_DIRBITS =	2

_IOC_NRMASK =   (1 << _IOC_NRBITS) - 1
_IOC_TYPEMASK = (1 << _IOC_TYPEBITS) - 1
_IOC_SIZEMASK = (1 << _IOC_SIZEBITS) - 1
_IOC_DIRMASK =  (1 << _IOC_DIRBITS) - 1

_IOC_NRSHIFT =	 0
_IOC_TYPESHIFT = _IOC_NRSHIFT + _IOC_NRBITS
_IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
_IOC_DIRSHIFT =	 _IOC_SIZESHIFT + _IOC_SIZEBITS

# Direction bits

_IOC_NONE = 0
_IOC_WRITE = 1
_IOC_READ = 2

def _IOC(dir, type, nr, size):
    return (dir  << _IOC_DIRSHIFT) | \
           (type << _IOC_TYPESHIFT) | \
           (nr   << _IOC_NRSHIFT) | \
           (size << _IOC_SIZESHIFT)

def _IOC_TYPECHECK(t):
    return ctypes.sizeof(t)


# used to create ioctl numbers

def _IO(type, nr):
    return _IOC(_IOC_NONE, type, nr, 0)

def _IOR(type, nr, size):
    return _IOC(_IOC_READ, type, nr, _IOC_TYPECHECK(size))

def _IOW(type, nr, size):
    return _IOC(_IOC_WRITE, type, nr, _IOC_TYPECHECK(size))

def _IOWR(type,nr,size):
    return _IOC(_IOC_READ|_IOC_WRITE, type, nr, _IOC_TYPECHECK(size))

def _IOR_BAD(type,nr,size):
    return _IOC(_IOC_READ, type, nr, sizeof(size))

def _IOW_BAD(type,nr,size):
    return _IOC(_IOC_WRITE,type,nr, sizeof(size))

def _IOWR_BAD(type,nr,size):
    return _IOC(_IOC_READ|_IOC_WRITE, type, nr, sizeof(size))


# ...and for the drivers/sound files...

IOC_IN = _IOC_WRITE << _IOC_DIRSHIFT
IOC_OUT = _IOC_READ << _IOC_DIRSHIFT
IOC_INOUT = (_IOC_WRITE|_IOC_READ) << _IOC_DIRSHIFT
IOCSIZE_MASK = _IOC_SIZEMASK << _IOC_SIZESHIFT
IOCSIZE_SHIFT = _IOC_SIZESHIFT


########NEW FILE########
__FILENAME__ = board_revision
def revision():
    try:
        with open('/proc/cpuinfo','r') as f:
            for line in f:
                if line.startswith('Revision'):
                    return 1 if line.rstrip()[-1] in ['2','3'] else 2
            else:
                return 0
    except:
        return 0


########NEW FILE########
__FILENAME__ = eventfd

from ctypes import *
import quick2wire.syscall as syscall
import os
import errno

# From sys/eventfd.h

EFD_SEMAPHORE = 1
EFD_CLOEXEC = 0o2000000
EFD_NONBLOCK = 0o4000

_libc = CDLL(None, use_errno=True)

eventfd_t = c_uint64

eventfd = syscall.lookup(c_int, "eventfd", (c_uint, c_int))


class Semaphore(syscall.SelfClosing):
    """A Semaphore implemented with eventfd that can be added to a Selector."""
    
    def __init__(self, count=0, blocking=True):
        """Creates a Semaphore with an initial count.
        
        Arguments:
        count -- the initial count.
        blocking -- if False calls to wait() do not block if the Semaphore
                    has a count of zero. (default = True)
        """
        self._initial_count = count
        self._flags = EFD_SEMAPHORE|((not blocking)*EFD_NONBLOCK)
        self._fd = None
    
    def close(self):
        """Closes the Semaphore and releases its file descriptor."""
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
    
    def fileno(self):
        """Returns the Semaphore's file descriptor."""
        if self._fd is None:
            self._fd = eventfd(self._initial_count, self._flags)
        return self._fd
    
    def signal(self):
        """Signal the semaphore.
        
        Signalling a semaphore increments its count by one and wakes a
        blocked task that is waiting on the semaphore.
        """
        return os.write(self.fileno(), eventfd_t(1))
    
    def wait(self):
        """Receive a signal from the Semaphore, decrementing its count by one.
        
        If the Semaphore is already has a count of zero, either wait
        for a signal if the Semaphore is in blocking mode, or return
        False immediately.
        
        Returns:
        True  -- the Semaphore received a signal.
        False -- the Semaphore did not receive a signal and is in 
                 non-blocking mode.
        """
        try:
            os.read(self.fileno(), 8)
            return True
        except OSError as e:
            if e.errno == errno.EAGAIN:
                return False
            else:
                raise

########NEW FILE########
__FILENAME__ = gpio
"""A convenient API to access the GPIO pins of the Raspberry Pi.

"""

import os
import subprocess
from contextlib import contextmanager
from quick2wire.board_revision import revision
from quick2wire.selector import EDGE


def gpio_admin(subcommand, pin, pull=None):
    if pull:
        subprocess.check_call(["gpio-admin", subcommand, str(pin), pull])
    else:
        subprocess.check_call(["gpio-admin", subcommand, str(pin)])


Out = "out"
In = "in"
    
Rising = "rising"
Falling = "falling"
Both = "both"
    
PullDown = "pulldown"
PullUp = "pullup"



class PinAPI(object):
    def __init__(self, bank, index):
        self._bank = bank
        self._index = index
    
    @property
    def index(self):
        return self._index
    
    @property
    def bank(self):
        return self._bank
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
    
    value = property(lambda p: p.get(), 
                     lambda p,v: p.set(v), 
                     doc="""The value of the pin: 1 if the pin is high, 0 if the pin is low.""")
    

class PinBankAPI(object):
    def __getitem__(self, n):
        if 0 < n < len(self):
            raise ValueError("no pin index {n} out of range", n=n)
        return self.pin(n)
    
    def write(self):
        pass
    
    def read(self):
        pass



class Pin(PinAPI):
    """Controls a GPIO pin."""
    
    __trigger__ = EDGE
    
    def __init__(self, bank, index, soc_pin_number, direction=In, interrupt=None, pull=None):
        """Creates a pin
        
        Parameters:
        user_pin_number -- the identity of the pin used to create the derived class.
        soc_pin_number  -- the pin on the header to control, identified by the SoC pin number.
        direction       -- (optional) the direction of the pin, either In or Out.
        interrupt       -- (optional)
        pull            -- (optional)
        
        Raises:
        IOError        -- could not export the pin (if direction is given)
        """
        super(Pin,self).__init__(None, index)
        self._soc_pin_number = soc_pin_number
        self._file = None
        self._direction = direction
        self._interrupt = interrupt
        self._pull = pull
    
    
    @property
    def soc_pin_number(self):
        return self._soc_pin_number
    
    def open(self):
        gpio_admin("export", self.soc_pin_number, self._pull)
        self._file = open(self._pin_path("value"), "r+")
        self._write("direction", self._direction)
        if self._direction == In:
            self._write("edge", self._interrupt if self._interrupt is not None else "none")
            
    def close(self):
        if not self.closed:
            if self.direction == Out:
                self.value = 0
            self._file.close()
            self._file = None
            self._write("direction", In)
            self._write("edge", "none")
            gpio_admin("unexport", self.soc_pin_number)
    
    def get(self):
        """The current value of the pin: 1 if the pin is high or 0 if the pin is low.
        
        The value can only be set if the pin's direction is Out.
        
        Raises: 
        IOError -- could not read or write the pin's value.
        """
        self._check_open()
        self._file.seek(0)
        v = self._file.read()
        return int(v) if v else 0
    
    def set(self, new_value):
        self._check_open()
        if self._direction != Out:
            raise ValueError("not an output pin")
        self._file.seek(0)
        self._file.write(str(int(new_value)))
        self._file.flush()
    
    @property
    def direction(self):
        """The direction of the pin: either In or Out.
        
        The value of the pin can only be set if its direction is Out.
        
        Raises:
        IOError -- could not set the pin's direction.
        """
        return self._direction
    
    @direction.setter
    def direction(self, new_value):
        self._write("direction", new_value)
        self._direction = new_value
    
    @property 
    def interrupt(self):
        """The interrupt property specifies what event (if any) will raise an interrupt.
        
        One of: 
        Rising  -- voltage changing from low to high
        Falling -- voltage changing from high to low
        Both    -- voltage changing in either direction
        None    -- interrupts are not raised
        
        Raises:
        IOError -- could not read or set the pin's interrupt trigger
        """
        return self._interrupt
    
    @interrupt.setter
    def interrupt(self, new_value):
        self._write("edge", new_value)
        self._interrupt = new_value

    @property
    def pull(self):
        return self._pull
    
    def fileno(self):
        """Return the underlying file descriptor.  Useful for select, epoll, etc."""
        return self._file.fileno()
    
    @property
    def closed(self):
        """Returns if this pin is closed"""
        return self._file is None or self._file.closed
    
    def _check_open(self):
        if self.closed:
            raise IOError(str(self) + " is closed")
    
    def _write(self, filename, value):
        with open(self._pin_path(filename), "w+") as f:
            f.write(value)
    
    def _pin_path(self, filename=""):
        return "/sys/devices/virtual/gpio/gpio%i/%s" % (self.soc_pin_number, filename)
    
    def __repr__(self):
        return self.__module__ + "." + str(self)
    
    def __str__(self):
        return "{type}({index})".format(
            type=self.__class__.__name__, 
            index=self.index)





class PinBank(PinBankAPI):
    def __init__(self, index_to_soc_fn, count=None):
        super(PinBank,self).__init__()
        self._index_to_soc = index_to_soc_fn
        self._count = count
    
    def pin(self, index, *args, **kwargs):
        return Pin(self, index, self._index_to_soc(index), *args, **kwargs)
    
    @property
    def has_len(self):
        return self._count is not None
    
    def __len__(self):
        if self._count is not None:
            return self._count
        else:
            raise TypeError(self.__class__.__name__ + " has no len")


BUTTON = 0
LED = 1
SPI_INTERRUPT = 6
I2C_INTERRUPT = 7


_pi_revision = revision()

if _pi_revision == 0:
    # Not running on the Raspberry Pi, so define no-op pin banks
    pins = PinBank(lambda p: p)
    pi_broadcom_soc = pins
    pi_header_1 = pins

else:
    def by_revision(d):
        return d[_pi_revision]


    # Maps header pin numbers to SoC GPIO numbers
    # See http://elinux.org/RPi_Low-level_peripherals
    #
    # Note: - header pins are numbered from 1, SoC GPIO from zero 
    #       - the Pi documentation identifies some header pins as GPIO0,
    #         GPIO1, etc., but these are not the same as the SoC GPIO
    #         numbers.
    
    _pi_header_1_pins = {
        3:  by_revision({1:0, 2:2}), 
        5:  by_revision({1:1, 2:3}), 
        7:  4, 
        8:  14, 
        10: 15, 
        11: 17, 
        12: 18, 
        13: by_revision({1:21, 2:27}), 
        15: 22, 
        16: 23, 
        18: 24, 
        19: 10, 
        21: 9, 
        22: 25, 
        23: 11, 
        24: 8,
        26: 7
        }
    
    _pi_gpio_pins = [_pi_header_1_pins[i] for i in [11, 12, 13, 15, 16, 18, 22, 7]]
    
    
    def lookup(pin_mapping, i):
        try:
            if i >= 0:
                return pin_mapping[i]
        except LookupError:
            pass
        
        raise IndexError(str(i) + " is not a valid pin index")

    def map_with(pin_mapping):
        return lambda i: lookup(pin_mapping,i)
    
    
    pi_broadcom_soc = PinBank(lambda p: p)
    pi_header_1 = PinBank(map_with(_pi_header_1_pins))
    pins = PinBank(map_with(_pi_gpio_pins), len(_pi_gpio_pins))
    


########NEW FILE########
__FILENAME__ = display
class AnalogueDisplay():
    def __init__(self, max, *pins):
        self._pins = pins
        self._pin_levels = [(pins[index], index * max / len(pins)) for index in range(len(pins))]

    def display(self, value):
        for (pin, level) in self._pin_levels:
            pin.value = 1 if value < level else 0


########NEW FILE########
__FILENAME__ = i2c

import sys
from contextlib import closing
import posix
from fcntl import ioctl
from quick2wire.i2c_ctypes import *
from ctypes import create_string_buffer, sizeof, c_int, byref, pointer, addressof, string_at
from quick2wire.board_revision import revision

assert sys.version_info.major >= 3, __name__ + " is only supported on Python 3"


default_bus = 1 if revision() > 1 else 0

class I2CMaster(object):
    """Performs I2C I/O transactions on an I2C bus.
    
    Transactions are performed by passing one or more I2C I/O messages
    to the transaction method of the I2CMaster.  I2C I/O messages are
    created with the reading, reading_into, writing and writing_bytes
    functions defined in the quick2wire.i2c module.
    
    An I2CMaster acts as a context manager, allowing it to be used in a
    with statement.  The I2CMaster's file descriptor is closed at
    the end of the with statement and the instance cannot be used for
    further I/O.
    
    For example:
    
        from quick2wire.i2c import I2CMaster, writing
        
        with I2CMaster() as i2c:
            i2c.transaction(
                writing(0x20, bytes([0x01, 0xFF])))
    """
    
    def __init__(self, n=default_bus, extra_open_flags=0):
        """Opens the bus device.
        
        Arguments:
        n                -- the number of the bus (default is
                            the bus on the Raspberry Pi accessible
                            via the header pins).
        extra_open_flags -- extra flags passed to posix.open when 
                            opening the I2C bus device file (default 0; 
                            e.g. no extra flags).
        """
        self.fd = posix.open("/dev/i2c-%i"%n, posix.O_RDWR|extra_open_flags)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
    
    def close(self):
        """
        Closes the I2C bus device.
        """
        posix.close(self.fd)
    
    def transaction(self, *msgs):
        """
        Perform an I2C I/O transaction.

        Arguments:
        *msgs -- I2C messages created by one of the reading, reading_into,
                 writing or writing_bytes functions.
        
        Returns: a list of byte sequences, one for each read operation 
                 performed.
        """
        
        msg_count = len(msgs)
        msg_array = (i2c_msg*msg_count)(*msgs)
        ioctl_arg = i2c_rdwr_ioctl_data(msgs=msg_array, nmsgs=msg_count)
        
        ioctl(self.fd, I2C_RDWR, ioctl_arg)
        
        return [i2c_msg_to_bytes(m) for m in msgs if (m.flags & I2C_M_RD)]



def reading(addr, n_bytes):
    """An I2C I/O message that reads n_bytes bytes of data"""
    return reading_into(addr, create_string_buffer(n_bytes))

def reading_into(addr, buf):
    """An I2C I/O message that reads into an existing ctypes string buffer."""
    return _new_i2c_msg(addr, I2C_M_RD, buf)

def writing_bytes(addr, *bytes):
    """An I2C I/O message that writes one or more bytes of data. 
    
    Each byte is passed as an argument to this function.
    """
    return writing(addr, bytes)

def writing(addr, byte_seq):
    """An I2C I/O message that writes one or more bytes of data.
    
    The bytes are passed to this function as a sequence.
    """
    buf = bytes(byte_seq)
    return _new_i2c_msg(addr, 0, create_string_buffer(buf, len(buf)))


def _new_i2c_msg(addr, flags, buf):
    return i2c_msg(addr=addr, flags=flags, len=sizeof(buf), buf=buf)


def i2c_msg_to_bytes(m):
    return string_at(m.buf, m.len)

########NEW FILE########
__FILENAME__ = i2c_ctypes
# Warning: not part of the published Quick2Wire API.
#
# Converted from i2c.h and i2c-dev.h
# I2C only, no SMB definitions

from ctypes import c_int, c_uint16, c_ushort, c_short, c_ubyte, c_char, POINTER, Structure

# /usr/include/linux/i2c-dev.h: 38
class i2c_msg(Structure):
    """<linux/i2c-dev.h> struct i2c_msg"""
    
    _fields_ = [
        ('addr', c_uint16),
        ('flags', c_ushort),
        ('len', c_short),
        ('buf', POINTER(c_char))]
    
    __slots__ = [name for name,type in _fields_]



# i2c_msg flags
I2C_M_TEN		= 0x0010	# this is a ten bit chip address
I2C_M_RD		= 0x0001	# read data, from slave to master
I2C_M_NOSTART		= 0x4000	# if I2C_FUNC_PROTOCOL_MANGLING
I2C_M_REV_DIR_ADDR	= 0x2000	# if I2C_FUNC_PROTOCOL_MANGLING
I2C_M_IGNORE_NAK	= 0x1000	# if I2C_FUNC_PROTOCOL_MANGLING
I2C_M_NO_RD_ACK		= 0x0800	# if I2C_FUNC_PROTOCOL_MANGLING
I2C_M_RECV_LEN		= 0x0400	# length will be first received byte


# /usr/include/linux/i2c-dev.h: 155
class i2c_rdwr_ioctl_data(Structure):
    """<linux/i2c-dev.h> struct i2c_rdwr_ioctl_data"""
    _fields_ = [
        ('msgs', POINTER(i2c_msg)),
        ('nmsgs', c_int)]

    __slots__ = [name for name,type in _fields_]

I2C_FUNC_I2C			= 0x00000001
I2C_FUNC_10BIT_ADDR		= 0x00000002
I2C_FUNC_PROTOCOL_MANGLING	= 0x00000004 # I2C_M_NOSTART etc.


# ioctls

I2C_SLAVE	= 0x0703	# Change slave address			
				# Attn.: Slave address is 7 or 10 bits  
I2C_SLAVE_FORCE	= 0x0706	# Change slave address			
				# Attn.: Slave address is 7 or 10 bits  
				# This changes the address, even if it  
				# is already taken!			
I2C_TENBIT	= 0x0704	# 0 for 7 bit addrs, != 0 for 10 bit	
I2C_FUNCS	= 0x0705	# Get the adapter functionality         
I2C_RDWR	= 0x0707	# Combined R/W transfer (one stop only) 

########NEW FILE########
__FILENAME__ = mcp23017
"""
Low-level register access and a high-level application-programming
interface for the MCP23017 I2C GPIO expander.
"""

from quick2wire.i2c import writing_bytes, reading
import quick2wire.parts.mcp23x17 as mcp23x17
from quick2wire.parts.mcp23x17 import deferred_read, immediate_read, deferred_write, immediate_write, In, Out

class MCP23017(mcp23x17.PinBanks):
    """Application programming interface to the MCP23017 GPIO extender"""
    
    def __init__(self, master, address=0x20):
        """Initialise to control an MCP23017 at the specified address via the given I2CMaster.
        
        Parameters:
        master  -- the quick2wire.i2c.I2CMaster used to communicate with the chip.
        address -- the address of the chip on the I2C bus (defaults to 0x20).
        """
        super().__init__(Registers(master, address))
        

class Registers(mcp23x17.Registers):
    """Low level access to the MCP23017 registers

    The MCP23017 has two register addressing modes, depending on the
    value of bit7 of IOCON. We assume bank=0 addressing (which is the
    POR default value).
    """
    
    def __init__(self, master, address):
        """Initialise to control an MCP23017 at the specified address via the given I2CMaster.
        
        Parameters:
        master  -- the quick2wire.i2c.I2CMaster used to communicate with the chip.
        address -- the address of the chip on the I2C bus (defaults to 0x20).
        """
        self.master = master
        self.address = address
        
    def write_register(self, register_id, byte):
        """Write the value of a register.
        
        Parameters:
        reg   -- the register address
        value -- the new value of the register
        """
        self.master.transaction(
            writing_bytes(self.address, register_id, byte))
    
    def read_register(self, register_id):
        """Read the value of a register.
        
        Parameters:
        reg   -- the register address
        
        Returns: the value of the register.
        """
        return self.master.transaction(
            writing_bytes(self.address, register_id),
            reading(self.address, 1))[0][0]



########NEW FILE########
__FILENAME__ = mcp23x17
"""
Low-level register access and a high-level application-programming
interface for the MCP23x17 series of GPIO expanders.

The definitions in this module are common to the I2C MCP23017 and SPI
MCP23S17. Only the methods for reading and writing to registers
differ, and they must be defined by subclassing the Registers class.
"""

import contextlib
from warnings import warn
from quick2wire.gpio import PinAPI, PinBankAPI

# TODO - import from GPIO or common definitions module
In = "in"
Out = "out"

# Bits within the IOCON regiseter
IOCON_INTPOL=1
IOCON_ODR=2
IOCON_MIRROR=6

# Register names within a bank
IODIR=0
IPOL=1
GPINTEN=2
DEFVAL=3
INTCON=4
IOCON=5
GPPU=6
INTF=7
INTCAP=8
GPIO=9
OLAT=10

bank_register_names = sorted([s for s in globals().keys() if s.upper() == s], 
                             key=lambda s: globals()[s])


BANK_SIZE = 11

_BankA = 0
_BankB = 1

def _banked_register(bank, reg):
    return reg*2 + bank

IODIRA = _banked_register(_BankA, IODIR)
IODIRB = _banked_register(_BankB, IODIR)
IPOLA = _banked_register(_BankA, IPOL)
IPOLB = _banked_register(_BankB, IPOL)
GPINTENA =_banked_register(_BankA, GPINTEN)
GPINTENB = _banked_register(_BankB, GPINTEN)
DEFVALA = _banked_register(_BankA, DEFVAL)
DEFVALB = _banked_register(_BankB, DEFVAL)
INTCONA = _banked_register(_BankA, INTCON)
INTCONB = _banked_register(_BankB, INTCON)
IOCONA = _banked_register(_BankA, IOCON)
IOCONB = _banked_register(_BankB, IOCON) # Actually addresses the same register as IOCONA
IOCON_BOTH = IOCONA
GPPUA = _banked_register(_BankA, GPPU)
GPPUB = _banked_register(_BankB, GPPU)
INTFA = _banked_register(_BankA, INTF)
INTFB = _banked_register(_BankB, INTF)
INTCAPA = _banked_register(_BankA, INTCAP)
INTCAPB = _banked_register(_BankB, INTCAP)
GPIOA = _banked_register(_BankA, GPIO)
GPIOB = _banked_register(_BankB, GPIO)
OLATA = _banked_register(_BankA, OLAT)
OLATB = _banked_register(_BankB, OLAT)

register_names = sorted([s for s in globals().keys() if s[-1] in ('A','B') and s.upper() == s], 
                        key=lambda s: globals()[s])

_initial_register_values = (
    ((IODIR,), 0xFF),
    ((IPOL, GPINTEN, DEFVAL, INTCON, GPPU, INTF, INTCAP, GPIO, OLAT), 0x00))

def _reset_sequence():
    return [(reg,value) for regs, value in _initial_register_values for reg in regs]


class Registers(object):
    """Abstract interface for reading/writing MCP23x17 registers over the I2C or SPI bus.
    
    You shouldn't normally need to use this class.

    The MCP23x17 has two register addressing modes, depending on the
    value of bit7 of IOCON. We assume bank=0 addressing (which is the
    POR default value).
    """
    
    def reset(self, iocon=0x00):
        """Reset to power-on state
        """
        self.write_register(IOCON_BOTH, iocon)
        
        for reg, value in _reset_sequence():
            self.write_banked_register(_BankA, reg, value)
            self.write_banked_register(_BankB, reg, value)
    
    def write_banked_register(self, bank, reg, value):
        """Write the value of a register within a bank.
        """
        self.write_register(_banked_register(bank, reg), value)
        
    def read_banked_register(self, bank, reg):
        """Read the value of a register within a bank.
        """
        return self.read_register(_banked_register(bank, reg))
    
    def write_register(self, reg, value):
        """Write the value of a register.
        
        Implement in subclasses.
        
        Parameters:
        reg   -- the register address
        value -- the new value of the register
        """
        pass
    
    def read_register(self, reg):
        """Read the value of a register.
        
        Implement in subclasses.
        
        Parameters:
        reg   -- the register address
        
        Returns: the value of the register.
        """
        pass



def _set_bit(current_value, bit_index, new_value):
    bit_mask = 1 << bit_index
    return (current_value | bit_mask) if new_value else (current_value & ~bit_mask)


class PinBanks(object):
    """The pin banks of an MCP23x17 chip."""
    
    def __init__(self, registers):
        self.registers = registers
        self._banks = (PinBank(self, 0), PinBank(self, 1))
    
    def __len__(self):
        """Returns the number of pin banks. (2 for the MCP23x17)"""
        return len(self._banks)
    
    def bank(self, n):
        """Returns bank n."""
        return self._banks[n]
    
    __getitem__ = bank
    
    def reset(self, interrupt_polarity=0, interrupt_open_drain=False, interrupt_mirror=True):
        """Resets the chip to power-on state and sets configuration flags in the IOCON register
        
        Parameters:
        interrupt_polarity   -- sets the polarity of the interrupt output 
                                pin: 1 = active-high. 0 = active-low.
        interrupt_open_drain -- configures the interrupt output pin as an 
                                open-drain output.
                                True = Open-drain output (overrides the 
                                interrupt_polarity).
                                False = Active driver output (the 
                                interrupt_polarity parameter sets the 
                                polarity).
        interrupt_mirror     -- Sets the interrupt output mirroring.
                                True = the interrupt output pins are 
                                internally connected.
                                False = the interrupt output pins are 
                                not connected, INTA is associated with
                                PortA and INTB is associated with PortB.
                                Should be set to True (the default) if 
                                using the Quick2Wire MCP23017 expander 
                                board.
        """
        
        self.registers.reset((interrupt_polarity << IOCON_INTPOL)
                            |(interrupt_open_drain << IOCON_ODR)
                            |(interrupt_mirror << IOCON_MIRROR))
        
        for bank in self._banks:
            bank._reset_cache()


# Read and write modes

def deferred_read(f):
    """A PinBank read mode: read() must be called explicitly."""
    pass

def immediate_read(f):
    """A PinBank read mode: read() is called automatically whenever a pin value is read.
    
    Note: this mode is not compatible with interrupts. A warning will
    be issued if interrupts are enabled on a PinBank that is in
    immediate_read mode.
    """
    f()

def deferred_write(f):
    """A PinBank write mode: write() must be called explicitly."""
    pass

def immediate_write(f):
    """A PinBank write mode: registers are written whenever Pin attributes are set."""
    f()


class PinBank(PinBankAPI):
    """A bank of 8 GPIO pins"""
    
    def __init__(self, chip, bank_id):
        self.chip = chip
        self._bank_id = bank_id
        self._pins = tuple([Pin(self, i) for i in range(8)])
        self._register_cache = [None]*BANK_SIZE # self._register_cache[IOCON] is ignored
        self._outstanding_writes = []
        self.read_mode = immediate_read
        self.write_mode = immediate_write
        self._reset_cache()
    
    @property
    def index(self):
        """The index of this bank (0 or 1)."""
        return self._bank_id
    

    def __len__(self):
        """The number of pins in the bank. (8 for the MCP23x17)"""
        return len(self._pins)
    
    
    def pin(self, n):
        """Returns pin n."""
        pin = self._pins[n]
        return pin
    
    __getitem__ = pin
    

    def read(self):
        """Read the GPIO input and interrupt capture registers from the chip.
        
        If the bank's read_mode is set to deferred_read, this must be
        called to make value property of the bank's Pins reflect the
        state of the chip's physical input pins.
        
        If the bank's read_mode is set to immediate_read, read() is
        called whenever the value property of any of the bank's Pins
        is read.
        """
        self._read_register(INTCAP)
        self._read_register(GPIO)
    

    def write(self):
        """Write changes to the pin's state capture and GPIO input registers from the chip.
        
        If the bank's write_mode is set to deferred_write, this must be
        update the chip's physical input pins so that they reflect the
        value property of the bank's Pins.
        
        If the bank's write_mode is set to immediate_write, write() is
        called whenever the value property of any of the bank's Pins
        is set.
        """
        for r in self._outstanding_writes:
            self._write_register(r, self._register_cache[r])
        self._outstanding_writes = []
    

    def _get_register_bit(self, register, bit_index):
        self.read_mode(lambda:self._read_register(register))
        
        if self._register_cache[register] is None:
            self._read_register(register)
        
        return bool(self._register_cache[register] & (1<<bit_index))
    
    
    def _read_register(self, register):
        self._register_cache[register] = self.chip.registers.read_banked_register(self._bank_id, register)
    
    
    def _set_register_bit(self, register, bit_index, new_value):
        self._register_cache[register] = _set_bit(self._register_cache[register], bit_index, new_value)
        if register not in self._outstanding_writes:
            self._outstanding_writes.append(register)
        
        self.write_mode(self.write)
    
    
    def _write_register(self, register, new_value):
        self.chip.registers.write_banked_register(self._bank_id, register, new_value)


    def _reset_cache(self):
        self._outstanding_writes = []
        for reg, value in _reset_sequence():
            self._register_cache[reg] = value
    
    
    def _check_read_mode_for_interrupts(self):
        if self.read_mode == immediate_read:
            warn("interrupts enabled when in immediate read mode", stacklevel=1)
    
    
    def __str__(self):
        return "PinBank("+self.index+")"
    

def _register_bit(register, doc, high_value=True, low_value=False):
    def _read(self):
        return high_value if self._get_register_bit(register) else low_value

    def _write(self, value):
        self._set_register_bit(register, value == high_value)
    
    return property(_read, _write, doc=doc)

class Pin(PinAPI):
    """A digital Pin that can be used for input or output."""
    
    def __init__(self, bank, index):
        """Called by the PinBank.  Not used by application code."""
        super(Pin,self).__init__(bank,index)
        self._is_claimed = False
    
    def open(self):
        """Acquire the Pin for use.
        
        Raises: ValueError if the pin is already in use.
        """
        if self._is_claimed:
            raise ValueError("pin already in use")
        self._is_claimed = True
    
    def close(self):
        self._is_claimed = False
    
    def get(self):
        """Returns the value of the pin.  
        
        The same as pin.value, but a method so that it can easily be passed around as a function.
        """
        return self._get_register_bit(GPIO)
    
    def set(self, new_value):
        """Sets the value of the pin.  
        
        The same as pin.value, but a method so that it can easily be passed around as a function.
        """
        self._set_register_bit(OLAT, new_value)
    
    direction = _register_bit(IODIR, high_value=In, low_value=Out,
                              doc="""The direction of the pin: In if the pin is used for input, Out if it is used for output.""")
    
    inverted = _register_bit(IPOL, 
        """Controls the polarity of the pin. If True, the value property will return the inverted signal on the hardware pin.""")
    
    pull_up = _register_bit(GPPU,
        """Is the pull up resistor enabled for the pin?
        True:  the pull up resistor is enabled
        False: the pull up resistor is not enabled
        """)
    
    def enable_interrupts(self, value=None):
        """Signal an interrupt on the bank's interrupt line whenever the value of the pin changes.
        
        Parameters:
        value -- If set, the interrupt is signalled when the pin's value is changed to this value.
                 If not set, the interrupt is signalled whenever the pin's value changes.
        """
        
        self.bank._check_read_mode_for_interrupts()
        if value is None:
            self._set_register_bit(INTCON, 0)
        else:
            self._set_register_bit(INTCON, 1)
            self._set_register_bit(DEFVAL, not value)
        self._set_register_bit(GPINTEN, 1)
    
    def disable_interrupts(self):
        """Do not signal an interrupt when the value of the pin changes."""
        self._set_register_bit(GPINTEN, 0)
    
    @property
    def interrupt(self):
        """Has the pin signalled an interrupt that has not been services?
        
        True:  the pin has signalled an interrupt
        False: the pin has not signalled an interrupt
        """
        return self._get_register_bit(INTCAP)
    
    def _set_register_bit(self, register, new_value):
        self.bank._set_register_bit(register, self.index, new_value)
    
    def _get_register_bit(self, register):
        return self.bank._get_register_bit(register, self.index)
        
    def __repr__(self):
        return "Pin(banks["+ str(self.bank.index) + "], " + str(self.index) + ")"


########NEW FILE########
__FILENAME__ = pcf8591
"""
API for the PCF8591 I2C A/D D/A converter.

The PCF8591 chip has four physical input pins, named AIN0 to AIN3, at
which it measures voltage, and a single physical output pin, named
AOUT, at which it generates analogue output.

Applications  control the  chip by  setting  or getting  the state  of
logical channels that the chip maps to its physical pins. There is one
output channel and  up to four input channels,  depending on the mode.
Input channels  are either _single-ended_, measuring the  voltage on a
input pin, or _differential_, measuring the voltage difference between
two input pins.

Applications talk to the chip via objects of the PCF8591 class. A
PCF8591 object is created with an I2CMaster, through which it
communicates with the chip, and a mode, one of:

FOUR_SINGLE_ENDED -- four single-ended channels reporting voltage at
                     AIN0 to AIN3, no differential inputs.

THREE_DIFFERENTIAL -- three differential inputs reporting voltage
                      difference between AIN0 to AIN2 and AIN3. No
                      single-ended channels.

SINGLE_ENDED_AND_DIFFERENTIAL -- two single ended channels reporting
                                 voltage at AIN0 and AIN1 and one
                                 differential channel reporting the
                                 voltage difference between AIN2 and
                                 AIN3.

TWO_DIFFERENTIAL -- two differential channels, the first reporting the
                    voltage difference between AIN0 and AIN1, and the
                    second reporting the voltage difference between
                    AIN2 and AIN3. No single-ended channels.

(See the documentation for the PCF8591 class for additional, optional
constructor parameters.)

For example:

    with I2CMaster() as i2c:
        adc = PCF8591(i2c, SINGLE_ENDED_AND_DIFFERENTIAL)
        
        assert adc.single_ended_input_count == 2
        assert adc.differential_input_count == 1


Once created you can use the channels of the PCF8591.  Input channels
are obtained from the `single_ended_input` and `differential_input`
methods.

    input = adc.single_ended_input(0)
    dinput = adc.differential_input(0)

The analogue signal of a channel is obtained by querying its `value`
property.  For single-ended channels the value varies between 0 and 1.
For differential channels the value varies between -0.5 and 0.5,
because the PCF8591 chip can only detect voltage differences of half
that between its reference voltage and ground.

The output channel must be opened before use, to turn on the chip's
D/A converter, and closed when no longer required, to turn it off
again and conserve power. It's easiest to do this with a context
manager.  When turned on, assigning a value between 0 and 1 to the
output channel's `value` property with set the voltage at the chip's
physical AOUT pin:

    with adc.output as output:
        # the D/A converter in the chip is now turned on
        output.value = 0.75
   
    # at the end of the with statement the D/A converter is turned off again


"""

from quick2wire.i2c import writing_bytes, reading
from quick2wire.gpio import Out, In

BASE_ADDRESS = 0x48

FOUR_SINGLE_ENDED = 0
THREE_DIFFERENTIAL = 1
SINGLE_ENDED_AND_DIFFERENTIAL = 2
TWO_DIFFERENTIAL = 3

_ANALOGUE_OUTPUT_ENABLE_FLAG = 1 << 6



class PCF8591(object):
    """API to query and control an PCF8591 A/D and D/A converter via I2C.
    
    See module documentation for details on how to use this class.
    """
    
    def __init__(self, master, mode, address=BASE_ADDRESS):
        """Initialises a PCF8591.
        
        Parameters:
        master -- the I2CMaster with which to communicate with the
                  PCF8591 chip.
        mode -- one of FOUR_SINGLE_ENDED, TWO_DIFFERENTIAL, 
                THREE_DIFFERENTIAL or SINGLE_ENDED_AND_DIFFERENTIAL.
        address -- the I2C address of the PCF8591 chip.
                   (optional, default = BASE_ADDRESS)
        """
        self.master = master
        self.address = address
        self._control_flags = (mode << 4)
        self._last_channel_read = None
        self._output = _OutputChannel(self)
        
        if mode == FOUR_SINGLE_ENDED:
            self._single_ended_inputs = tuple(self._create_single_ended_channel(i) for i in range(4))
            self._differential_inputs = ()
        elif mode == TWO_DIFFERENTIAL:
            self._single_ended_inputs = ()
            self._differential_inputs = tuple(self._create_differential_channel(i) for i in range(2))
        elif mode == SINGLE_ENDED_AND_DIFFERENTIAL:
            self._single_ended_inputs = tuple(self._create_single_ended_channel(i) for i in (0,1))
            self._differential_inputs = (self._create_differential_channel(2),)
        elif mode == THREE_DIFFERENTIAL:
            self._single_ended_inputs = ()
            self._differential_inputs = tuple(self._create_differential_channel(i) for i in range(3))
        else:
            raise ValueError("invalid mode " + str(mode))
    
    def _create_single_ended_channel(self, i):
        return _InputChannel(self, i, self.read_single_ended, 255.0)
    
    def _create_differential_channel(self, i):
        return _InputChannel(self, i, self.read_differential, 256.0)
    
    @property
    def output(self):
        """The single analogue output channel"""
        return self._output
    
    @property
    def single_ended_input_count(self):
        """The number of single-ended analogue input channels"""
        return len(self._single_ended_inputs)
    
    def single_ended_input(self, n):
        """Returns the n'th single-ended analogue input channel"""        
        return self._single_ended_inputs[n]
    
    @property
    def differential_input_count(self):
        """The number of differential analogue input channels"""
        return len(self._differential_inputs)
    
    def differential_input(self, n):
        """Returns the n'th differential analogue input channel"""        
        return self._differential_inputs[n]
    
    def enable_output(self):
        self._control_flags |= _ANALOGUE_OUTPUT_ENABLE_FLAG
        self._write_control_flags()
    
    def disable_output(self):
        self._control_flags &= ~_ANALOGUE_OUTPUT_ENABLE_FLAG
        self._write_control_flags()
    
    def _write_control_flags(self):
        if self._last_channel_read is None:
            self._last_channel_read = 0
        
        self.master.transaction(
            writing_bytes(self.address, self._control_flags|self._last_channel_read))
    
    def write(self, value):
        self.write_raw(min(max(0, int(value*255)), 0xFF))
        
    def write_raw(self, int_value):
        if self._last_channel_read is None:
            self._last_channel_read = 0
        
        self.master.transaction(
            writing_bytes(self.address, self._control_flags|self._last_channel_read, int_value))
    
    def read_single_ended(self, channel):
        """Read the 8-bit value of a single-ended input channel."""
        return self.read_raw(channel)
    
    def read_differential(self, channel):
        """Read the 8-bit value of a differential input channel."""
        unsigned = self.read_raw(channel)
        return (unsigned & 127) - (unsigned & 128)
    
    def read_raw(self, channel):
        if channel != self._last_channel_read:
            self.master.transaction(writing_bytes(self.address, self._control_flags|channel),
                                    reading(self.address, 2))
            self._last_channel_read = channel
        
        results = self.master.transaction(
            reading(self.address, 2))
        return results[0][-1]


class _OutputChannel(object):
    def __init__(self, bank):
        self.bank = bank
        self._value = 0x80
    
    def open(self):
        self.bank.enable_output()
    
    def close(self):
        self.bank.disable_output()
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, *exc):
        self.close()
        return False
    
    @property
    def direction(self):
        return Out
    
    def get(self):
        return self._value
    
    def set(self, value):
        self._value = value
        self.bank.write(self._value)
    
    value = property(get, set)


class _InputChannel(object):
    def __init__(self, bank, index, read_fn, scale):
        self.bank = bank
        self.index = index
        self._read = read_fn
        self._scale = scale
    
    @property
    def direction(self):
        return In
    
    def get(self):
        return self.get_raw() / self._scale
    
    value = property(get)
    
    def get_raw(self):
        return self._read(self.index)
    
    raw_value = property(get_raw)
    
    # No-op implementations of Pin resource management API
    
    def open(self):
        pass
    
    def close(self):
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, *exc):
        return False


########NEW FILE########
__FILENAME__ = test_mcp23017_interrupts_loopback
from quick2wire.i2c import I2CMaster
from quick2wire.gpio import pins, In, Out, I2C_INTERRUPT
from quick2wire.parts.mcp23017 import MCP23017, deferred_read
from quick2wire.parts.test_mcp23017_loopback import Topology, inverse
import pytest



@pytest.mark.loopback
@pytest.mark.mcp23017
@pytest.mark.gpio
def test_mcp23017_interrupts():
    i2c_int = pins.pin(I2C_INTERRUPT, direction=In)
    
    with i2c_int, I2CMaster() as i2c:
        chip = MCP23017(i2c)
        chip.reset(interrupt_polarity=1)
        
        check_interrupts(chip, i2c_int, Topology)
        check_interrupts(chip, i2c_int, inverse(Topology))



def check_interrupts(chip, int_pin, topology):
    for (outb, outp), (inb, inp) in topology:
        outbank = chip.bank(outb)
        outpin = outbank.pin(outp)
        
        inbank = chip.bank(inb)
        inpin = inbank.pin(inp)
        
        inbank.read_mode = deferred_read
        
        with outpin, inpin:
            outpin.direction = Out
            inpin.direction = In
            inpin.enable_interrupts()
            
            for v in [1,0,1,0]:
                outpin.value = v
                
                assert int_pin.value == 1
                
                inbank.read()
                
                assert int_pin.value == 0
                assert inpin.value == v
                

########NEW FILE########
__FILENAME__ = test_mcp23017_loopback
import quick2wire.i2c as i2c
from quick2wire.parts.mcp23017 import Registers as MCP23017Registers, MCP23017
from quick2wire.parts.mcp23017 import deferred_read, deferred_write, In, Out
from quick2wire.parts.mcp23x17 import IODIRA, IODIRB, GPIO
import pytest



# Simplest test - pins of bank 0 connected to corresponding pin of bank 1
Topology = [((0,i), (1,i)) for i in range(8)]

def inverse(topology):
    return [(b,a) for (a,b) in topology]

def bit(n):
    return 1 << n
    

def check_mcp23017_loopback(chip_class, checker):
    with i2c.I2CMaster() as master:
        chip = chip_class(master, 0x20)        
        
        chip.reset()
        checker(chip, Topology)
        
        chip.reset()
        checker(chip, inverse(Topology))


@pytest.mark.loopback
@pytest.mark.mcp23017
def test_loopback_via_registers():
    check_mcp23017_loopback(MCP23017Registers, check_connectivity_via_registers)


@pytest.mark.loopback
@pytest.mark.mcp23017
def test_loopback_via_pins():
    check_mcp23017_loopback(MCP23017, check_connectivity_via_pins)


@pytest.mark.loopback
@pytest.mark.mcp23017
def test_loopback_via_pins_deferred():
    check_mcp23017_loopback(MCP23017, check_connectivity_via_pins_deferred)



def check_connectivity_via_registers(chip, topology):
    iodira, iodirb = iodir_values(topology)
    
    chip.write_register(IODIRA, iodira)
    chip.write_register(IODIRB, iodirb)
    
    for (outbank, outpin), (inbank, inpin) in topology:
        chip.write_banked_register(outbank, GPIO, bit(outpin))
        assert chip.read_banked_register(inbank, GPIO) == bit(inpin)


def iodir_values(topology):
    iodirs = [0xFF,0xFF]
    for (bank1, pin1), (bank2, pin2) in topology:
        iodirs[bank1] &= ~bit(pin1)
    return iodirs


def check_connectivity_via_pins(chip, topology):
    for (outb, outp), (inb, inp) in topology:
        with chip[outb][outp] as outpin, chip[inb][inp] as inpin:
            outpin.direction = Out
            inpin.direction = In
            
            for v in [1,0,1,0]:
                outpin.value = v
                assert inpin.value == v



def check_connectivity_via_pins_deferred(chip, topology):
    for (outb, outp), (inb, inp) in topology:
        chip.reset()
        
        with chip[outb][outp] as outpin, chip[inb][inp] as inpin:
            inpin.direction = In
            outpin.direction = Out
            
            chip[outb].write_mode = deferred_write
            chip[inb].read_mode = deferred_read
            
            for v in [1,0,1,0]:
                outpin.value = v
                
                assert inpin.value != v
                
                outpin.bank.write()
                assert inpin.value != v
                
                inpin.bank.read()
                assert inpin.value == v
                

########NEW FILE########
__FILENAME__ = test_mcp23x17

from itertools import product, permutations, count
from warnings import catch_warnings, simplefilter as issue_warnings
import quick2wire.parts.mcp23x17 as mcp23x17
from quick2wire.parts.mcp23x17 import *
from quick2wire.parts.mcp23x17 import _banked_register
from factcheck import *

bits = from_range(2)
bank_ids = from_range(2)
pin_ids = from_range(0,8)
banked_pin_ids = tuples(bank_ids, pin_ids)
pin_pairs = ((p1,p2) for (p1,p2) in tuples(banked_pin_ids,banked_pin_ids) if p1 != p2)

def all_pins_of_chip():
    global chip
    
    for b,p in banked_pin_ids:
        with chip[b][p] as pin:
            yield pin

def setup_function(function=None):
    global chip, registers
    
    registers = FakeRegisters()
    chip = PinBanks(registers)
    chip.reset()


def test_has_two_banks_of_eight_pins():
    assert len(chip) == 2
    assert len(chip[0]) == 8
    assert len(chip[1]) == 8


@forall(b=bank_ids, p=pin_ids, samples=3)
def test_all_pins_report_their_bank_and_index(b, p):
    assert chip[b][p].bank == chip[b]
    assert chip[b][p].index == p


@forall(b=bank_ids, p=pin_ids, samples=3)
def test_can_use_a_context_manager_to_claim_ownership_of_a_pin_in_a_bank_and_release_it(b, p):
    with chip[b][p] as pin:
        try:
            with chip[b][p] as pin2:
                raise AssertionError("claiming the pin should have failed")
        except ValueError as e:
            pass


@forall(b=bank_ids, p=pin_ids, samples=3)
def test_a_pin_can_be_claimed_after_being_released(b, p):
    with chip[b][p] as pin:
        pass
    
    with chip[b][p] as pin_again:
        pass


@forall(b=bank_ids, p=pin_ids, samples=3)
def test_after_reset_or_poweron_all_pins_are_input_pins(b,p):
    # Chip is reset in setup
    with chip[b][p] as pin:
        assert pin.direction == In


def test_resets_iocon_before_other_registers():
    registers.clear_writes()
    
    chip.reset()
    assert chip.registers.writes[0][0] in (IOCONA, IOCONB)


@forall(intpol=bits, odr=bits, mirror=bits, samples=4)
def test_can_set_configuration_of_chip_on_reset(intpol, odr, mirror):
    """Note: IOCON is duplicated in both banks so only need to test the contents in one bank"""
    
    chip.reset(interrupt_polarity=intpol, interrupt_open_drain=odr, interrupt_mirror=mirror)
    
    assert registers.register_bit(0, IOCON, IOCON_INTPOL) == intpol
    assert registers.register_bit(0, IOCON, IOCON_ODR) == odr
    assert registers.register_bit(0, IOCON, IOCON_MIRROR) == mirror



@forall(b=bank_ids, p=pin_ids, samples=3)
def test_can_read_logical_value_of_input_pin(b,p):
    chip.reset()
    
    with chip[b][p] as pin:
        pin.direction = In
    
        registers.given_gpio_inputs(b, 1 << p)
        assert pin.value == 1
        
        registers.given_gpio_inputs(b, 0)
        assert pin.value == 0



@forall(b=bank_ids)
def test_initially_banks_are_in_immediate_mode(b):
    assert chip[b].read_mode == immediate_read
    assert chip[b].write_mode == immediate_write


@forall(b = bank_ids, p=pin_ids, samples=2)
def test_in_deferred_read_mode_bank_must_be_read_explicitly_before_pin_value_is_visible(b, p):
    chip.reset()
    
    bank = chip[b]
    
    bank.read_mode = deferred_read
    
    with bank[p] as pin:
        assert pin.value == 0
        
        registers.given_gpio_inputs(b, 1<<p)
        assert pin.value == 0
        
        bank.read()
        assert pin.value == 1
        
        registers.given_gpio_inputs(b, 0)        
        assert pin.value == 1
        
        bank.read()
        assert pin.value == 0


@forall(b=bank_ids, p=pin_ids, samples=3)
def test_can_set_pin_to_output_mode_and_set_its_logical_value(b,p):
    with chip[b][p] as pin:
        pin.direction = Out
        
        pin.value = 1
        assert registers.read_banked_register(b, OLAT) == (1 << p)
    
        pin.value = 0
        assert registers.read_banked_register(b, OLAT) == (0 << p)


@forall(ps=pin_pairs, p2_value=bits, samples=5)
def test_can_write_value_of_pin_without_affecting_other_output_pins(ps, p2_value):
    (b1,p1), (b2,p2) = ps
    
    with chip[b1][p1] as pin1, chip[b2][p2] as pin2:
        pin1.direction = Out
        pin2.direction = Out
        
        pin2.value = p2_value
        
        pin1.value = 0
        assert registers.read_banked_register(b1, GPIO) & (1 << p1) == 0
        assert registers.read_banked_register(b2, GPIO) & (1 << p2) == (p2_value << p2)
        
        pin1.value = 1
        assert registers.read_banked_register(b1, GPIO) & (1 << p1) == (1 << p1)
        assert registers.read_banked_register(b2, GPIO) & (1 << p2) == (p2_value << p2)
        
        pin1.value = 0
        assert registers.read_banked_register(b1, GPIO) & (1 << p1) == 0
        assert registers.read_banked_register(b2, GPIO) & (1 << p2) == (p2_value << p2)
        

@forall(ps=pin_pairs, inpin_value=bits, samples=3)
def test_can_read_an_input_bit_then_write_then_read_same_bit(ps, inpin_value):
    (inb, inp), (outb, outp) = ps
    
    registers.given_gpio_inputs(inb, inpin_value<<inp)
    
    with chip[inb][inp] as inpin, chip[outb][outp] as outpin:
        inpin.direction = In
        outpin.direction = Out
        
        assert inpin.value == inpin_value
        
        outpin.value = 1
        assert inpin.value == inpin_value
        
        outpin.value = 0
        assert inpin.value == inpin_value
        
        outpin.value = 1
        assert inpin.value == inpin_value


@forall(b=bank_ids, p=pin_ids, samples=3)
def test_can_configure_polarity(b, p):
    chip.reset()
    
    registers.given_register_value(b, IPOL, 0x00)
    
    with chip[b][p] as pin:
        assert not pin.inverted
        pin.inverted = True
        assert pin.inverted
        assert registers.read_banked_register(b, IPOL) == (1<<p)
        
        registers.given_register_value(b, IPOL, 0xFF)
        
        registers.clear_writes()
        
        assert pin.inverted
        pin.inverted = False
        assert not pin.inverted
        
        assert registers.read_banked_register(b, IPOL) == ~(1<<p) & 0xFF


@forall(b=bank_ids, p=pin_ids, samples=3)
def test_can_configure_pull_up_resistors(b, p):
    chip.reset()
    
    registers.given_register_value(b, GPPU, 0x00)
    
    with chip[b][p] as pin:
        assert not pin.pull_up
        pin.pull_up = True
        assert pin.pull_up
        assert registers.read_banked_register(b, GPPU) == (1<<p)
        
        registers.given_register_value(b, GPPU, 0xFF)
        
        registers.clear_writes()
        
        assert pin.pull_up
        pin.pull_up = False
        assert not pin.pull_up
        
        assert registers.read_banked_register(b, GPPU) == ~(1<<p) & 0xFF


@forall(b=bank_ids, p=pin_ids, samples=3)
def test_can_set_pin_to_interrupt_when_input_changes(b, p):
    with chip[b][p] as pin:
        registers.given_register_value(b, GPINTEN, 0)
        registers.given_register_value(b, INTCON, 0xFF)
        
        pin.bank.read_mode = deferred_read
        pin.enable_interrupts()
        
        assert registers.register_bit(b, GPINTEN, p) == 1
        assert registers.register_bit(b, INTCON, p) == 0


@forall(b=bank_ids, p=pin_ids, samples=3)
def test_can_set_pin_to_interrupt_when_input_changes_to_specific_value(b, p):
    with chip[b][p] as pin:
        registers.given_register_value(b, GPINTEN, 0)
        registers.given_register_value(b, INTCON, 0)
        
        pin.bank.read_mode = deferred_read
        pin.enable_interrupts(value=1)
        
        assert registers.register_bit(b, GPINTEN, p) == 1
        assert registers.register_bit(b, INTCON, p) == 1

@forall(b=bank_ids, p=pin_ids, samples=3)
def test_can_disable_interrupts(b, p):
    with chip[b][p] as pin:
        pin.bank.read_mode = deferred_read
        pin.enable_interrupts()
        
        pin.disable_interrupts()
        
        assert registers.register_bit(b, GPINTEN, p) == 0\


@forall(b=bank_ids, p=pin_ids, samples=3)
def test_issues_warning_if_interrupt_enabled_when_pin_is_in_immediate_read_mode(b, p):
    with chip[b][p] as pin:
        pin.bank.read_mode = immediate_read
        
        with catch_warnings(record=True) as warnings:
            issue_warnings("always")
            
            pin.enable_interrupts(value=1)
            
            assert len(warnings) > 0


@forall(b=bank_ids, p=pin_ids, samples=3)
def test_issues_no_warning_if_interrupt_enabled_when_pin_is_in_deferred_read_mode(b, p):
    with chip[b][p] as pin:
        pin.bank.read_mode = deferred_read
        
        with catch_warnings(record=True) as warnings:
            issue_warnings("always")
            
            pin.enable_interrupts()
            
            print(warnings)
            assert len(warnings) == 0


@forall(b=bank_ids, p=pin_ids, samples=3)
def test_issues_no_warning_if_interrupt_enabled_when_pin_is_in_custom_read_mode(b, p):
    def custom_read_mode(f):
        pass
    
    with chip[b][p] as pin:
        pin.bank.read_mode = custom_read_mode
        
        with catch_warnings(record=True) as warnings:
            issue_warnings("always")
            
            pin.enable_interrupts()
            
            assert len(warnings) == 0


@forall(b=bank_ids, p=pin_ids, samples=3)
def test_must_explicitly_read_to_update_interrupt_state(b, p):
    chip.reset()
    
    with chip[b][p] as pin:
        pin.direction = In
        pin.bank.read_mode = deferred_read
        
        pin.enable_interrupts()
        
        registers.given_register_value(b, INTCAP, 1<<p)
        
        assert not pin.interrupt
        pin.bank.read()
        assert pin.interrupt


@forall(b=bank_ids, p1=pin_ids, p2=pin_ids, where=lambda b,p1,p2: p1 != p2, samples=3)
def test_in_deferred_write_mode_the_bank_caches_pin_states_until_written_to_chip(b, p1, p2):
    chip.reset()
    
    with chip[b][p1] as pin1, chip[b][p2] as pin2:
        chip[b].write_mode = deferred_write
        
        pin1.direction = Out
        pin2.direction = Out
        
        assert registers.register_value(b, IODIR) == 0xFF
        assert registers.register_value(b, OLAT) == 0x00
        
        pin1.value = True
        
        assert registers.register_value(b, OLAT) == 0x00
        
        pin1.bank.write()
        
        assert registers.register_bit(b, IODIR, p1) == 0
        assert registers.register_bit(b, IODIR, p2) == 0
        assert registers.register_bit(b, OLAT, p1) == 1



@forall(b=bank_ids, p=pin_ids, samples=3)
def test_in_deferred_write_mode_can_set_value_of_input_pin_without_explicit_reset(b,p):
    chip = PinBanks(registers)
    bank = chip[b]
    
    with bank[p] as pin:
        bank.write_mode = deferred_write
        
        pin.value = 1 
        bank.write()
        assert registers.register_bit(b, OLAT, p) == 1


@forall(b=bank_ids, p=pin_ids, samples=3)
def test_in_deferred_write_mode_a_reset_discards_outstanding_writes(b, p):
    chip.reset()
    
    bank = chip[b]
    with bank[p] as pin:
        pin.direction = Out
        bank.write_mode = deferred_write
        
        pin.value = 1
        chip.reset()
        
        registers.clear_writes()
        bank.write()
        
        assert registers.writes == []


class FakeRegisters(Registers):
    """Note - does not simulate effect of the IPOL{A,B} registers."""
    
    def __init__(self):
        self.registers = [0]*(BANK_SIZE*2)
        self.writes = []
        self.reset()
    
    def write_register(self, reg, value):
        self.writes.append((reg, value))
        
        if reg in (IOCONA, IOCONB):
            self.registers[IOCONA] = value
            self.registers[IOCONB] = value
        elif reg == GPIOA:
            self.registers[OLATA] = value
        elif reg == GPIOB:
            self.registers[OLATB] = value
        elif reg not in (INTFA, INTFB, INTCAPA, INTCAPB):
            self.registers[reg] = value
    
    def read_register(self, reg):
        if reg == GPIOA:
            value = (self.registers[GPIOA] & self.registers[IODIRA]) | (self.registers[OLATA] & ~self.registers[IODIRA])
        elif reg == GPIOB:
            value = (self.registers[GPIOB] & self.registers[IODIRB]) | (self.registers[OLATB] & ~self.registers[IODIRB])
        else:
            value = self.registers[reg]

        if reg in (INTCAPA, GPIOA):
            self.registers[INTCAPA] = 0
        elif reg in (INTCAPB, GPIOB):
            self.registers[INTCAPB] = 0
          
        return value
    
    def register_value(self, bank, reg):
        return self.registers[_banked_register(bank,reg)]
    
    def register_bit(self, bank, reg, bit):
        return (self.register_value(bank,reg) >> bit) & 0x01
    
    def given_gpio_inputs(self, bank, value):
        self.given_register_value(bank, GPIO, value)
    
    def given_register_value(self, bank, reg, value):
        self.registers[_banked_register(bank,reg)] = value
    
    def print_registers(self):
        for reg, value in zip(count(), self.registers):
            print(register_names[reg].ljust(8) + " = " + "%02X"%value)
    
    def print_writes(self):
        for reg, value in self.writes:
            print(register_names[reg].ljust(8) + " := " + "%02X"%value)

    def clear_writes(self):
        self.writes = []
        
    def __repr__(self):
        return type(self).__name__ + "()"
    
    def __str__(self):
        return repr(self)



########NEW FILE########
__FILENAME__ = test_pcf8591

from quick2wire.i2c_ctypes import I2C_M_RD
from quick2wire.gpio import In
from quick2wire.parts.pcf8591 import PCF8591, FOUR_SINGLE_ENDED, THREE_DIFFERENTIAL, SINGLE_ENDED_AND_DIFFERENTIAL, TWO_DIFFERENTIAL
import pytest


class FakeI2CMaster:
    def __init__(self):
        self._requests = []
        self._responses = []
        self._next_response = 0
        self.message_precondition = lambda m: True
        
    def all_messages_must(self, p):
        self.message_precondition
    
    def clear(self):
        self.__init__()
    
    def transaction(self, *messages):
        for m in messages:
            self.message_precondition(m)
        
        self._requests.append(messages)
        
        read_count = sum(bool(m.flags & I2C_M_RD) for m in messages)
        if read_count == 0:
            return []
        elif self._next_response < len(self._responses):
            response = self._responses[self._next_response]
            self._next_response += 1
            return response
        else:
            return [(0x00,)]*read_count
    
    def add_response(self, *messages):
        self._responses.append(messages)
    
    @property
    def request_count(self):
        return len(self._requests)
    
    def request(self, n):
        return self._requests[n]


i2c = FakeI2CMaster()

def is_read(m):
    return bool(m.flags & I2C_M_RD)

def is_write(m):
    return not is_read(m)

def assert_is_approx(expected, value, delta=0.005):
    assert abs(value - expected) <= delta


def correct_message_for(adc):
    def check(m):
        assert m.addr == adc.address
        assert m.flags in (0, I2C_M_RD)
        assert m.len == 1 or m.len == 2
    
    return check



def setup_function(f):
    i2c.clear()

def create_pcf8591(*args, **kwargs):
    adc = PCF8591(*args, **kwargs)
    i2c.message_precondition = correct_message_for(adc)
    return adc

def assert_all_input_pins_report_direction(adc):
    assert all(adc.single_ended_input(p).direction == In for p in range(adc.single_ended_input_count))
    assert all(adc.differential_input(p).direction == In for p in range(adc.differential_input_count))


def test_can_be_created_with_four_single_ended_inputs():
    adc = PCF8591(i2c, FOUR_SINGLE_ENDED)
    assert adc.single_ended_input_count == 4
    assert adc.differential_input_count == 0
    assert_all_input_pins_report_direction(adc)

def test_can_be_created_with_three_differential_inputs():
    adc = PCF8591(i2c, THREE_DIFFERENTIAL)
    assert adc.single_ended_input_count == 0
    assert adc.differential_input_count == 3
    assert_all_input_pins_report_direction(adc)

def test_can_be_created_with_one_differential_and_two_single_ended_inputs():
    adc = PCF8591(i2c, SINGLE_ENDED_AND_DIFFERENTIAL)
    assert adc.single_ended_input_count == 2
    assert adc.differential_input_count == 1
    assert_all_input_pins_report_direction(adc)

def test_can_be_created_with_two_differential_inputs():
    adc = PCF8591(i2c, TWO_DIFFERENTIAL)
    assert adc.single_ended_input_count == 0
    assert adc.differential_input_count == 2
    assert_all_input_pins_report_direction(adc)

def test_cannot_be_created_with_an_invalid_mode():
    with pytest.raises(ValueError):
        PCF8591(i2c, 999)

def test_can_read_a_single_ended_pin():
    adc = create_pcf8591(i2c, FOUR_SINGLE_ENDED)
    
    pin = adc.single_ended_input(2)
    
    i2c.add_response(bytes([0x80, 0x60]))
    i2c.add_response(bytes([0x40, 0x40]))
    
    sample = pin.value
    
    assert i2c.request_count == 2
    
    m1a,m1b = i2c.request(0)
    assert is_write(m1a)
    assert m1a.len == 1
    assert m1a.buf[0][0] == 0b00000010
    
    assert is_read(m1b)
    assert m1b.len == 2
    
    m2, = i2c.request(1)
    assert is_read(m2)
    assert m2.len == 2
    
    assert_is_approx(0.25, sample)


def test_can_read_raw_value_of_a_single_ended_pin():
    adc = create_pcf8591(i2c, FOUR_SINGLE_ENDED)
    
    pin = adc.single_ended_input(2)
    
    i2c.add_response(bytes([0x80, 0x60]))
    i2c.add_response(bytes([0x40, 0x40]))
    
    sample = pin.raw_value
    
    assert i2c.request_count == 2
    
    m1a,m1b = i2c.request(0)
    assert is_write(m1a)
    assert m1a.len == 1
    assert m1a.buf[0][0] == 0b00000010
    
    assert is_read(m1b)
    assert m1b.len == 2
    
    m2, = i2c.request(1)
    assert is_read(m2)
    assert m2.len == 2
    
    assert sample == 0x40


def test_can_read_a_differential_pin():
    adc = create_pcf8591(i2c, THREE_DIFFERENTIAL)
    
    pin = adc.differential_input(1)
    

    i2c.add_response(bytes([0x80, 0x60]))
    
    # -64 in 8-bit 2's complement representation
    i2c.add_response(bytes([0xC0, 0xC0]))
    
    sample = pin.raw_value
    
    assert i2c.request_count == 2
    
    m1a,m1b = i2c.request(0)
    assert is_write(m1a)
    assert m1a.len == 1
    assert m1a.buf[0][0] == 0b00010001
    
    assert is_read(m1b)
    assert m1b.len == 2
    
    m2, = i2c.request(1)
    assert is_read(m2)
    assert m2.len == 2
    
    assert sample == -64


def test_can_read_raw_value_of_a_differential_pin():
    adc = create_pcf8591(i2c, THREE_DIFFERENTIAL)
    
    pin = adc.differential_input(1)
    
    i2c.add_response(bytes([0x80, 0x60]))
    
    # -64 in 8-bit 2's complement representation
    i2c.add_response(bytes([0xC0, 0xC0]))
    
    sample = pin.value
    
    assert i2c.request_count == 2
    
    m1a,m1b = i2c.request(0)
    assert is_write(m1a)
    assert m1a.len == 1
    assert m1a.buf[0][0] == 0b00010001
    
    assert is_read(m1b)
    assert m1b.len == 2
    
    m2, = i2c.request(1)
    assert is_read(m2)
    assert m2.len == 2
    
    assert_is_approx(-0.25, sample)


def test_sends_correct_mode_bits_for_four_single_ended_mode():
    adc = create_pcf8591(i2c, FOUR_SINGLE_ENDED)
    
    pin = adc.single_ended_input(1)
    
    pin.get()
    
    assert i2c.request(0)[0].buf[0][0] == 0b00000001


def test_sends_correct_mode_bits_for_four_single_ended_mode():
    adc = create_pcf8591(i2c, FOUR_SINGLE_ENDED)
    
    pin = adc.single_ended_input(1)
    
    pin.get()
    
    assert i2c.request(0)[0].buf[0][0] == 0b00000001


def test_sends_correct_mode_bits_for_two_differential_mode():
    adc = create_pcf8591(i2c, TWO_DIFFERENTIAL)

    pin = adc.differential_input(1)
    
    pin.get()
    
    assert i2c.request(0)[0].buf[0][0] == 0b00110001


def test_sends_correct_mode_bits_for_single_ended_and_differential_mode():
    adc = create_pcf8591(i2c, SINGLE_ENDED_AND_DIFFERENTIAL)
    
    pin = adc.single_ended_input(1)
    
    pin.get()
    
    assert i2c.request(0)[0].buf[0][0] == 0b00100001
    

def test_does_not_switch_channel_and_only_reads_once_for_subsequent_reads_from_same_pin():
    adc = create_pcf8591(i2c, FOUR_SINGLE_ENDED)
    
    pin0 = adc.single_ended_input(0)
    
    sample = pin0.value
    assert i2c.request_count == 2
    
    sample = pin0.value
    assert i2c.request_count == 3
    
    sample = pin0.value
    assert i2c.request_count == 4


def test_switches_channel_and_reads_twice_when_reading_from_different_pin():
    adc = create_pcf8591(i2c, FOUR_SINGLE_ENDED)
    
    pin0 = adc.single_ended_input(0)
    pin1 = adc.single_ended_input(1)
    
    sample = pin0.value
    assert i2c.request_count == 2
    
    sample = pin0.value
    assert i2c.request_count == 3
    
    sample = pin1.value
    assert i2c.request_count == 5
    
    ma,mb = i2c.request(3)
    assert is_write(ma)
    assert ma.len == 1
    assert ma.buf[0][0] == 0b00000001
    assert is_read(mb)
    assert mb.len == 2
    

def test_opening_and_closing_the_output_pin_turns_the_digital_to_analogue_converter_on_and_off():
    adc = create_pcf8591(i2c, FOUR_SINGLE_ENDED)
    
    adc.output.open()
    assert i2c.request_count == 1
    m1, = i2c.request(0)
    assert is_write(m1)
    assert m1.len == 1
    assert m1.buf[0][0] == 0b01000000
    
    adc.output.close()
    assert i2c.request_count == 2
    m2, = i2c.request(1)
    assert is_write(m2)
    assert m2.len == 1
    assert m2.buf[0][0] == 0b00000000


def test_output_pin_opens_and_closes_itself_when_used_as_a_context_manager():
    adc = create_pcf8591(i2c, FOUR_SINGLE_ENDED)
    
    with adc.output:
        assert i2c.request_count == 1
    
    assert i2c.request_count == 2


def test_setting_value_of_output_pin_sends_value_as_second_written_byte():
    adc = create_pcf8591(i2c, FOUR_SINGLE_ENDED)
    
    with adc.output as pin:
        pin.value = 0.5
        
        assert i2c.request_count == 2
        m1, = i2c.request(1)
        assert m1.len == 2
        assert m1.buf[0][0] == 0b01000000
        assert m1.buf[1][0] == 127

        pin.value = 0.25
        
        assert i2c.request_count == 3
        m2, = i2c.request(2)
        assert m2.len == 2
        assert m2.buf[0][0] == 0b01000000
        assert m2.buf[1][0] == 63



def test_setting_value_of_output_pin_does_not_affect_currently_selected_input_pin():
    adc = create_pcf8591(i2c, FOUR_SINGLE_ENDED)
    
    with adc.output as opin:
        assert i2c.request_count == 1
        
        adc.single_ended_input(1).get()
        assert i2c.request_count == 3
        
        opin.value = 0.5
        assert i2c.request_count == 4
        assert i2c.request(3)[0].buf[0][0] == 0b01000001
        
        adc.single_ended_input(2).get()
        assert i2c.request_count == 6
        
        opin.value = 0.5
        assert i2c.request_count == 7
        assert i2c.request(6)[0].buf[0][0] == 0b01000010

########NEW FILE########
__FILENAME__ = test_pcf8591_loopback
"""Loopback tests for the PCF8591 API

Topology:

 - connect AIN1 to ground
 - connect AIN2 to 3V3
 - connect AIN3 to AOUT
 - connect VREF to 3v3
 - connect AGND to ground
 - AIN0 is unused

"""

from time import sleep
from quick2wire.i2c import I2CMaster
from quick2wire.parts.pcf8591 import PCF8591, FOUR_SINGLE_ENDED, THREE_DIFFERENTIAL
import pytest


def setup_function(f):
    global i2c
    i2c = I2CMaster()


def teardown_function(f):
    i2c.close()


def assert_is_approx(expected, actual, delta=0.02):
    assert abs(actual - expected) <= delta


@pytest.mark.loopback
@pytest.mark.pcf8591
def test_pcf8591_loopback_single_ended():
    adc = PCF8591(i2c, FOUR_SINGLE_ENDED)
    input = adc.single_ended_input(3)
    
    with adc.output as output:
        for v in (i/255.0 for i in range(256)):
            output.value = v
            assert_is_approx(v, input.value)


@pytest.mark.loopback
@pytest.mark.pcf8591
def test_pcf8591_loopback_switching_channels():
    adc = PCF8591(i2c, FOUR_SINGLE_ENDED)
    p1 = adc.single_ended_input(1)
    p2 = adc.single_ended_input(2)
    
    for i in range(8):
        assert p1.value == 0.0
        assert p2.value == 1.0


@pytest.mark.loopback
@pytest.mark.pcf8591
def test_pcf8591_loopback_differential_vref_to_ain3():
    adc = PCF8591(i2c, THREE_DIFFERENTIAL)
    cmp_vref = adc.differential_input(2)
    
    with adc.output as output:
        for v in (i/255.0 for i in range(256)):
            output.value = v
            assert_is_approx(min(0.5, 1-v), cmp_vref.value)


@pytest.mark.loopback
@pytest.mark.pcf8591
def test_pcf8591_loopback_differential_gnd_to_ain3():
    adc = PCF8591(i2c, THREE_DIFFERENTIAL)
    cmp_gnd = adc.differential_input(1)
    
    with adc.output as output:
        for v in (i/255.0 for i in range(256)):
            output.value = v
            assert_is_approx(max(-0.5, -v), cmp_gnd.value)

########NEW FILE########
__FILENAME__ = selector
"""Event notification for I/O, timers, inter-thread and inter-process
communication.
"""

import select
from quick2wire.syscall import SelfClosing
from quick2wire.eventfd import Semaphore
from quick2wire.timerfd import Timer

INPUT = select.EPOLLIN
OUTPUT = select.EPOLLOUT
ERROR = select.EPOLLERR
HANGUP = select.EPOLLHUP
PRIORITY_INPUT = select.EPOLLPRI

LEVEL = 0
EDGE = 1


class Selector(SelfClosing):
    """Lets a thread wait for multiple events and handle them one at a time."""
    
    def __init__(self, size_hint=-1):
        """Initialises a Selector.
        
        Arguments:
        size_hint -- A hint of the number of event sources that will
                     be added to the Selector, or -1 for the default.
                     Used to optimize internal data structures, it
                     doesn't limit the maximum number of monitored
                     event sources.
        """
        self._size_hint = size_hint
        self._epoll = None
        self._sources = {}
        self.ready = None
        self.events = 0
    
    def _get_epoll(self):
        if self._epoll is None:
            self._epoll = select.epoll(self._size_hint)
        return self._epoll

    def fileno(self):
        """Returns the Selector's file descriptor."""
        return self._get_epoll().fileno()
    
    def add(self, source, eventmask=INPUT|ERROR, trigger=None, identifier=None):
        """Adds an event source to the Selector.
        
        Arguments:
        source     -- the event source to add.  Must provide a fileno() 
                      method that returns its file descriptor.
                      
        eventmask  -- the events that the Selector will report.  A
                      bit-mask of:
                      INPUT          -- there is input to be read from 
                                        the source
                      OUTPUT         -- output can be written to the source
                      ERROR          -- an error has occurred on the source
                      HANGUP         -- a remote hangup has occured on the 
                                        source
                      PRIORITY_INPUT -- urgent out-of-band data is waiting 
                                        to be read from the source
                      The default is INPUT|ERROR.
        trigger    -- LEVEL -- the event source is level triggered (the 
                      default),
                      EDGE  -- the event source is edge triggered.
        identifier -- A value to be stored in the `ready` property when an
                      event has occurred on the source.  Default is the 
                      source itself.
        """
        fileno = source.fileno()
        trigger = trigger if trigger is not None else getattr(source, "__trigger__", LEVEL)
        
        self._sources[fileno] = identifier if identifier is not None else source
        self._get_epoll().register(fileno, eventmask|(select.EPOLLET*trigger))
    
    def remove(self, source):
        """Removes an event source from the Selector.
        
        Arguments:
        source -- the event source to remove.
        """
        fileno = source.fileno()
        self._get_epoll().unregister(source)
        del self._sources[fileno]

    def wait(self, timeout=-1):
        """Wait for an event to occur on any of the sources that have been added to the Selector.
        
        After wait returns, the `ready` property is set to the
        identifier of a source that has an event that needs to be
        responded to and the `events` property is set to a bit-set
        indicating which events have occurred on the source.  The
        `has_input`, `has_output`, `has_error`, `has_hangup` and
        `has_priority_input` events provide convenient access to the
        bits of the `event` bit-set.
        
        If a timeout is specified and no events occur before the
        timeout, the `ready` property is `None`.
        
        Arguments: 
        timeout -- maximum time to wait for an event. Specified in
                   seconds (can be less than one). Default is no
                   timeout: wait forever for an event.
        """
        self.ready = None
        self.events = 0
        
        readies = self._get_epoll().poll(timeout, maxevents=1)
        if readies:
            fileno, self.events = readies[0]
            self.ready = self._sources[fileno]
            
    @property
    def has_input(self):
        """Returns whether the ready event source has input that can be read."""
        return bool(self.events & INPUT)
    
    @property
    def has_output(self):
        """Returns whether output can be written to the ready event source."""
        return bool(self.events & OUTPUT)
    
    @property
    def has_error(self):
        """Returns whetheran error has occurred on the ready event source."""
        return bool(self.events & ERROR)
    
    @property
    def has_hangup(self):
        """Returns whether a remote hangup has occured on the ready event source."""
        return bool(self.events & HANGUP)
    
    @property
    def has_priority_input(self):
        """Returns whether urgent out-of-band data is waiting to be read from the ready event source."""
        return bool(self.events & PRIORITY_INPUT)
    
    def close(self):
        """Closes the Selector and releases its file descriptor."""
        if self._epoll is not None:
            self._epoll.close()

__all__ = ['Selector', 'Timer', 'Semaphore', 'INPUT', 'OUTPUT', 'ERROR', 'HANGUP', 'PRIORITY_INPUT', 'LEVEL', 'EDGE']

########NEW FILE########
__FILENAME__ = spi
import sys
from ctypes import addressof, create_string_buffer, sizeof, string_at
import struct
import posix
from fcntl import ioctl
from quick2wire.spi_ctypes import *
from quick2wire.spi_ctypes import spi_ioc_transfer, SPI_IOC_MESSAGE

assert sys.version_info.major >= 3, __name__ + " is only supported on Python 3"


class SPIDevice:
    """Communicates with a hardware device over an SPI bus.
    
    Transactions are performed by passing one or more SPI I/O requests
    to the transaction method of the SPIDevice.  SPI I/O requests are
    created with the reading, writing, writing_bytes, duplex and
    duplex_bytes functions defined in the quick2wire.spi module.
    
    An SPIDevice acts as a context manager, allowing it to be used in
    a with statement.  The SPIDevice's file descriptor is closed at
    the end of the with statement and the instance cannot be used for
    further I/O.

    For example:
    
        from quick2wire.spi import SPIDevice, writing
        
        with SPIDevice(0) as spi0:
            spi0.transaction(
                writing(0x20, bytes([0x01, 0xFF])))
    """
    
    def __init__(self, chip_select, bus=0):
        """Opens the SPI device.
        
        Arguments:
        chip_select -- the SPI chip select line to use. The Raspberry Pi
                       only has two chip select lines, numbered 0 and 1.
        bus         -- the number of the bus (default 0, the only SPI bus
                       on the Raspberry Pi).
        """
        self.fd = posix.open("/dev/spidev%i.%i"%(bus,chip_select), posix.O_RDWR)

    def transaction(self, *transfers):
        """
        Perform an SPI I/O transaction.
        
        Arguments:
        *transfers -- SPI transfer requests created by one of the reading,
                      writing, writing_bytes, duplex or duplex_bytes 
                      functions.

        Returns: a list of byte sequences, one for each read or duplex
                 operation performed.
        """
        transfer_count = len(transfers)
        ioctl_arg = (spi_ioc_transfer*transfer_count)()

        # populate array from transfers
        for i, transfer in enumerate(transfers):
            ioctl_arg[i] = transfers[i].to_spi_ioc_transfer()

        ioctl(self.fd, SPI_IOC_MESSAGE(transfer_count), addressof(ioctl_arg))

        return [transfer.to_read_bytes() for t in transfers if t.has_read_buf]

    def close(self):
        """
        Closes the file descriptor.
        """
        posix.close(self.fd)

    @property
    def clock_mode(self):
        """
        Returns the current clock mode for the SPI bus
        """
        return ord(struct.unpack('c', ioctl(self.fd, SPI_IOC_RD_MODE, " "))[0])

    @clock_mode.setter
    def clock_mode(self,mode):
        """
        Changes the clock mode for this SPI bus

        For example:
             #start clock low, sample trailing edge
             spi.clock_mode = SPI_MODE_1
        """
        ioctl(self.fd, SPI_IOC_WR_MODE, struct.pack('I', mode))

    @property
    def speed_hz(self):
        """
        Returns the current speed in Hz for this SPI bus
        """
        return struct.unpack('I', ioctl(self.fd, SPI_IOC_RD_MAX_SPEED_HZ, "    "))[0]

    @speed_hz.setter
    def speed_hz(self,speedHz):
        """
        Changes the speed in Hz for this SPI bus
        """
        ioctl(self.fd, SPI_IOC_WR_MAX_SPEED_HZ, struct.pack('I', speedHz))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class _SPITransfer:
    def __init__(self, write_byte_seq = None, read_byte_count = None):
        if write_byte_seq is not None:
            self.write_bytes = bytes(write_byte_seq)
            self.write_buf = create_string_buffer(self.write_bytes, len(self.write_bytes))
        else:
            self.write_bytes = None
            self.write_buf = None
        
        if read_byte_count is not None:
            self.read_buf = create_string_buffer(read_byte_count)
        else:
            self.read_buf = None
    
    def to_spi_ioc_transfer(self):
        return spi_ioc_transfer(
            tx_buf=_safe_address_of(self.write_buf),
            rx_buf=_safe_address_of(self.read_buf),
            len=_safe_size_of(self.write_buf, self.read_buf))

    @property
    def has_read_buf(self):
        return self.read_buf is not None

    def to_read_bytes(self):
        return string_at(self.read_buf, sizeof(self.read_buf))


def _safe_size_of(write_buf, read_buf):
    if write_buf is not None and read_buf is not None:
        assert sizeof(write_buf) == sizeof(read_buf)
        return sizeof(write_buf)
    elif write_buf is not None:
        return sizeof(write_buf)
    else:
        return sizeof(read_buf)

def _safe_address_of(buf):
    return 0 if buf is None else addressof(buf)

def duplex(write_byte_sequence):
    """An SPI transfer that writes the write_byte_sequence to the device and reads len(write_byte_sequence) bytes from the device.
    
    The bytes to be written are passed to this function as a sequence.
    """
    return _SPITransfer(write_byte_seq=write_byte_sequence, read_byte_count=len(write_byte_sequence))

def duplex_bytes(*write_bytes):
    """An SPI transfer that writes the write_bytes to the device and reads len(write_bytes) bytes from the device.
    
    Each byte to be written is passed as an argument to this function.
    """
    return duplex(write_bytes)

def reading(byte_count):
    """An SPI transfer that shifts out byte_count zero bytes and reads byte_counts bytes from the device."""
    return _SPITransfer(read_byte_count=byte_count)

def writing(byte_sequence):
    """An SPI transfer that writes one or more bytes of data and ignores any bytes read from the device.
    
    The bytes are passed to this function as a sequence.
    """
    return _SPITransfer(write_byte_seq=byte_sequence)

def writing_bytes(*byte_values):
    """An SPI transfer that writes one or more bytes of data and ignores any bytes read from the device.
    
    Each byte is passed as an argument to this function.
    """
    return writing(byte_values)


########NEW FILE########
__FILENAME__ = spi_ctypes
# Warning: not part of the published Quick2Wire API.
#
# User space versions of kernel symbols for SPI clocking modes,
# matching <linux/spi/spi.h>
# 
# Ported to Python ctypes from <linux/spi/spidev.h>

from ctypes import *
from quick2wire.asm_generic_ioctl import _IOR, _IOW, _IOC_SIZEBITS

SPI_CPHA = 0x01
SPI_CPOL = 0x02

SPI_MODE_0 = 0
SPI_MODE_1 = SPI_CPHA
SPI_MODE_2 = SPI_CPOL
SPI_MODE_3 = SPI_CPOL|SPI_CPHA

SPI_CS_HIGH = 0x04
SPI_LSB_FIRST = 0x08
SPI_3WIRE = 0x10
SPI_LOOP = 0x20
SPI_NO_CS = 0x40
SPI_READY = 0x80


# IOCTL commands */

SPI_IOC_MAGIC = 107 # ord('k')


# struct spi_ioc_transfer - describes a single SPI transfer
#
# tx_buf:        Holds pointer to userspace buffer with transmit data, or null.
#                If no data is provided, zeroes are shifted out.
# rx_buf:        Holds pointer to userspace buffer for receive data, or null.
# len:           Length of tx and rx buffers, in bytes.
# speed_hz:      Temporary override of the device's bitrate.
# bits_per_word: Temporary override of the device's wordsize.
# delay_usecs:   If nonzero, how long to delay after the last bit transfer
#	         before optionally deselecting the device before the next transfer.
# cs_change:     True to deselect device before starting the next transfer.
#
# This structure is mapped directly to the kernel spi_transfer structure;
# the fields have the same meanings, except of course that the pointers
# are in a different address space (and may be of different sizes in some
# cases, such as 32-bit i386 userspace over a 64-bit x86_64 kernel).
# Zero-initialize the structure, including currently unused fields, to
# accomodate potential future updates.
#
# SPI_IOC_MESSAGE gives userspace the equivalent of kernel spi_sync().
# Pass it an array of related transfers, they'll execute together.
# Each transfer may be half duplex (either direction) or full duplex.
#
#	struct spi_ioc_transfer mesg[4];
#	...
#	status = ioctl(fd, SPI_IOC_MESSAGE(4), mesg);
#
# So for example one transfer might send a nine bit command (right aligned
# in a 16-bit word), the next could read a block of 8-bit data before
# terminating that command by temporarily deselecting the chip; the next
# could send a different nine bit command (re-selecting the chip), and the
# last transfer might write some register values.

class spi_ioc_transfer(Structure):
    """<linux/spi/spidev.h> struct spi_ioc_transfer"""
    
    _fields_ = [
        ("tx_buf", c_uint64),
        ("rx_buf", c_uint64),
        ("len", c_uint32),
        ("speed_hz", c_uint32),
        ("delay_usecs", c_uint16),
        ("bits_per_word", c_uint8),
        ("cs_change", c_uint8),
        ("pad", c_uint32)]
    
    __slots__ = [name for name,type in _fields_]


# not all platforms use <asm-generic/ioctl.h> or _IOC_TYPECHECK() ...
def SPI_MSGSIZE(N):
    if ((N)*(sizeof(spi_ioc_transfer))) < (1 << _IOC_SIZEBITS):
        return (N)*(sizeof(spi_ioc_transfer))
    else:
        return 0

def SPI_IOC_MESSAGE(N):
    return _IOW(SPI_IOC_MAGIC, 0, c_char*SPI_MSGSIZE(N))

# Read / Write of SPI mode (SPI_MODE_0..SPI_MODE_3)
SPI_IOC_RD_MODE =			_IOR(SPI_IOC_MAGIC, 1, c_uint8)
SPI_IOC_WR_MODE =			_IOW(SPI_IOC_MAGIC, 1, c_uint8)

# Read / Write SPI bit justification
SPI_IOC_RD_LSB_FIRST =		_IOR(SPI_IOC_MAGIC, 2, c_uint8)
SPI_IOC_WR_LSB_FIRST =		_IOW(SPI_IOC_MAGIC, 2, c_uint8)

# Read / Write SPI device word length (1..N)
SPI_IOC_RD_BITS_PER_WORD =	_IOR(SPI_IOC_MAGIC, 3, c_uint8)
SPI_IOC_WR_BITS_PER_WORD =	_IOW(SPI_IOC_MAGIC, 3, c_uint8)

# Read / Write SPI device default max speed hz
SPI_IOC_RD_MAX_SPEED_HZ =		_IOR(SPI_IOC_MAGIC, 4, c_uint32)
SPI_IOC_WR_MAX_SPEED_HZ =		_IOW(SPI_IOC_MAGIC, 4, c_uint32)


########NEW FILE########
__FILENAME__ = syscall

import os
import errno
import ctypes

libc = ctypes.CDLL(None, use_errno=True)

def errcheck(result, func, args):
    if result < 0:
        e = ctypes.get_errno()
        raise OSError(e, errno.strerror(e))
    return result

def lookup(restype, name, argtypes):
    f = libc[name]
    f.restye = restype
    f.argtypes = argtypes
    f.errcheck = errcheck
    return f


class SelfClosing(object):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    

########NEW FILE########
__FILENAME__ = test_eventfd

from select import epoll, EPOLLIN
from contextlib import closing
from quick2wire.eventfd import Semaphore



def test_can_signal_poll_and_receive_a_semaphore():
    with closing(Semaphore()) as s, closing(epoll()) as poller:
        poller.register(s, EPOLLIN)
        
        assert poller.poll(timeout=0) == []
        
        s.signal()
        
        assert poller.poll(timeout=0) == [(s.fileno(), EPOLLIN)]
        assert poller.poll(timeout=0) == [(s.fileno(), EPOLLIN)]
        
        assert s.wait() == True
        
        assert poller.poll(timeout=0) == []


def test_can_initialise_a_semaphore_with_a_count():
    with closing(Semaphore(1)) as s, closing(epoll()) as poller:
        poller.register(s, EPOLLIN)
        
        assert poller.poll(timeout=0) == [(s.fileno(), EPOLLIN)]
         

def test_a_semaphore_can_be_nonblocking():
    with closing(Semaphore(blocking=False)) as s, closing(epoll()) as poller:
        poller.register(s, EPOLLIN)
        
        assert s.wait() == False
        assert poller.poll(timeout=0) == []
        
        s.signal()
        
        assert poller.poll(timeout=0) == [(s.fileno(), EPOLLIN)]
        assert poller.poll(timeout=0) == [(s.fileno(), EPOLLIN)]
        
        assert s.wait() == True
        
        assert s.wait() == False
        assert poller.poll(timeout=0) == []
        


########NEW FILE########
__FILENAME__ = test_gpio

import os
from quick2wire.gpio import pins, In, Out, PullDown, gpio_admin
import pytest


@pytest.mark.gpio
@pytest.mark.loopback
class TestGPIO:
    def test_pin_must_be_opened_before_use_and_is_unusable_after_being_closed(self):
        pin = pins.pin(0)
        
        with pytest.raises(IOError):
            pin.value
        
        pin.open()
        try:
            pin.value
        finally:
            pin.close()
        
        with pytest.raises(IOError):
            pin.value
    
    
    def test_opens_and_closes_itself_when_used_as_a_context_manager(self):
        pin = pins.pin(0)
        
        with pin:
            pin.value
        
        with pytest.raises(IOError):
            pin.value
    
    
    def test_exports_gpio_device_to_userspace_when_opened_and_unexports_when_closed(self):
        with pins.pin(0) as pin:
            assert os.path.exists('/sys/class/gpio/gpio17/value')
        
        assert not os.path.exists('/sys/class/gpio/gpio17/value')
    
    
    def test_can_set_and_query_direction_of_pin_when_open(self):
        with pins.pin(0) as pin:
            pin.direction = Out
            assert pin.direction == Out
            
            assert content_of("/sys/class/gpio/gpio17/direction") == "out\n"
            
            pin.direction = In
            assert pin.direction == In
            
            assert content_of("/sys/class/gpio/gpio17/direction") == "in\n"
    
    
    def test_can_set_direction_on_construction(self):
        pin = pins.pin(0, Out)
        
        assert pin.direction == Out
        assert not os.path.exists("/sys/class/gpio/gpio17/direction")
        
        with pin:
            assert content_of("/sys/class/gpio/gpio17/direction") == "out\n"
            assert pin.direction == Out
    
    
    def test_setting_value_of_output_pin_writes_to_device_file(self):
        with pins.pin(0) as pin:
            pin.direction = Out
            
            pin.value = 1
            assert pin.value == 1
            assert content_of('/sys/class/gpio/gpio17/value') == '1\n'
            
            pin.value = 0
            assert pin.value == 0
            assert content_of('/sys/class/gpio/gpio17/value') == '0\n'
    
    
    def test_direction_and_value_of_pin_is_reset_when_closed(self):
        with pins.pin(0, Out) as pin:
            pin.value = 1
        
        gpio_admin("export", 17, PullDown)
        try:
            assert content_of('/sys/class/gpio/gpio17/value') == '0\n'
            assert content_of('/sys/class/gpio/gpio17/direction') == 'in\n'
        finally:
            gpio_admin("unexport", 17)

    def test_cannot_get_a_pin_with_an_invalid_index(self):
        with pytest.raises(IndexError):
            pins.pin(-1)
        
        with pytest.raises(IndexError):
            pins.pin(len(pins))

        
def content_of(filename):
    with open(filename, 'r') as f:
        return f.read()


########NEW FILE########
__FILENAME__ = test_gpio_loopback
"""Loopback tests for the GPIO pins

Topology:

 - connect P2 to P3
 - connect P4 to P5
 - P0 and P1 are left free to be jumpered to the LED and button
 - P6 and P7 are reserved for testing I2C and SPI interrupts
"""

from quick2wire.gpio import pins, pi_header_1, In, Out
from time import sleep
import pytest


def inverse(topology):
    return [(b,a) for (a,b) in topology]


@pytest.mark.loopback
@pytest.mark.gpio
def test_gpio_loopback():
    assert_outputs_seen_at_corresponding_inputs(pins, [(0,1), (2,3), (4,5)])


@pytest.mark.loopback
@pytest.mark.gpio
def test_gpio_loopback_by_header_pin():
    assert_outputs_seen_at_corresponding_inputs(pi_header_1, [(11,12), (13,15), (16,18)])


def assert_outputs_seen_at_corresponding_inputs(pin_bank, topology):
    for (op, ip) in topology:
        assert_output_seen_at_input(pin_bank, op, ip)
    
    for (op, ip) in inverse(topology):
        assert_output_seen_at_input(pin_bank, op, ip)


def assert_output_seen_at_input(pin_bank, op, ip):
  with pin_bank.pin(op, direction=Out) as output_pin,\
       pin_bank.pin(ip, direction=In) as input_pin:
    for value in [1, 0, 1, 0]:
      output_pin.value = value
      assert input_pin.value == value

########NEW FILE########
__FILENAME__ = test_selector

from contextlib import closing
from itertools import islice
from quick2wire.selector import Selector, INPUT, OUTPUT, ERROR, Semaphore, Timer


def test_selector_is_a_convenient_api_to_epoll():
    selector = Selector()
    ev1 = Semaphore(blocking=False)
    with selector, ev1:
        selector.add(ev1, INPUT)
        
        ev1.signal()
        
        selector.wait()
        assert selector.ready == ev1
        assert selector.has_input == True
        assert selector.has_output == False
        assert selector.has_error == False
        assert selector.has_hangup == False
        assert selector.has_priority_input == False


def test_event_mask_defaults_to_input_and_error():
    selector = Selector()
    ev1 = Semaphore(blocking=False)
    with selector, ev1:
        selector.add(ev1)
        ev1.signal()
        
        selector.wait(timeout=0)
        assert selector.ready == ev1
        assert selector.has_input == True


def test_selecting_from_multiple_event_sources():
    selector = Selector()
    ev1 = Semaphore(blocking=False)
    ev2 = Semaphore(blocking=False)
    with selector, ev1, ev2:
        selector.add(ev1, INPUT)
        selector.add(ev2, INPUT)
        
        ev1.signal()
        ev2.signal()
        
        selector.wait()
        first = selector.ready
        first.wait()
        
        selector.wait()
        second = selector.ready
        second.wait()
        
        assert first in (ev1, ev2)
        assert second in (ev1, ev2)
        assert first is not second
        
        
def test_can_use_a_different_value_to_identify_the_event_source():
    selector = Selector()
    ev1 = Semaphore(blocking=False)
    with selector, ev1:
        selector.add(ev1, INPUT, identifier=999)
        
        ev1.signal()
        
        selector.wait()
        assert selector.ready == 999

        
def test_can_wait_with_a_timeout():
    selector = Selector()
    ev1 = Semaphore(blocking=False)
    with selector, ev1:
        selector.add(ev1, INPUT, identifier=999)
        
        selector.wait(timeout=0)
        assert selector.ready == None


def test_can_remove_source_from_selector():
    selector = Selector()
    ev1 = Semaphore(blocking=False)
    with selector, ev1:
        selector.add(ev1, INPUT)
        
        ev1.signal()
        
        selector.wait(timeout=0)
        assert selector.ready == ev1
        
        selector.remove(ev1)
        
        selector.wait(timeout=0)
        assert selector.ready == None


def test_can_wait_for_timer():
    selector = Selector()
    timer = Timer(blocking=False,offset=0.0125)
    with selector, timer:
        selector.add(timer, INPUT)
        
        timer.start()
        
        selector.wait()
        
        assert selector.ready == timer

########NEW FILE########
__FILENAME__ = test_spi_loopback
"""
This is a loopback test which uses the MCP23S17 to test the quick2wire.spi.SPIDevice class.

# For the loopback test, each pin on PORTA is connected to the PORTB pin opposite. Thus,
# GPA0 <-> GPB7
# GPA1 <-> GBP6
# ...
# GPA7 <-> GPB0
# The bit pattern input is therefore the output pattern reflected.

Note: this test does *not* depend on the quick2wire.mcp23s17 module, so that it can be
released independently
"""

from quick2wire.spi import *
import pytest

# MCP23S17 registers using bank=0
IODIRA=0x00
IODIRB=0x01
GPIOA=0x12
GPIOB=0x13
MCP23S17_BASE_ADDRESS = 0x40

ALL_OUTPUTS = 0x00
ALL_INPUTS = 0xFF

bits_out = [(1 << i) for i in range(0,8)]
bits_in = [(1 << (7 - i)) for i in range(0, 8)]
bits = zip(bits_out, bits_in)

address = MCP23S17_BASE_ADDRESS


@pytest.mark.hardware
@pytest.mark.loopback
@pytest.mark.spi
def test_loopback_bits():
    with SPIDevice(0, 0) as mcp23s17:
        prepare_to_send_from_a_to_b(mcp23s17)
        for (port_a, port_b) in bits:
            check_sending_from_a_to_b(mcp23s17, port_a, port_b)
        prepare_to_send_from_b_to_a(mcp23s17)
        for (port_b, port_a) in bits:
            check_sending_from_b_to_a(mcp23s17, port_b, port_a)

def prepare_to_send_from_a_to_b(mcp23s17):
    set_io_direction_a(mcp23s17, ALL_OUTPUTS) # Port A set to output
    set_io_direction_b(mcp23s17, ALL_INPUTS)  # Port B set to input

def check_sending_from_a_to_b(mcp23s17, port_a, port_b):
    write_register(mcp23s17, GPIOA, port_a)
    assert read_register(mcp23s17, GPIOB) == port_b

def prepare_to_send_from_b_to_a(mcp23s17):
    set_io_direction_a(mcp23s17, ALL_INPUTS)  # Port A set to input
    set_io_direction_b(mcp23s17, ALL_OUTPUTS) # Port B set to output

def check_sending_from_b_to_a(mcp23s17, port_b, port_a):
    write_register(mcp23s17, GPIOB, port_b)
    assert read_register(mcp23s17, GPIOA) == port_a

def set_io_direction_a(mcp23s17, b):
    write_register(mcp23s17, IODIRA, b)

def set_io_direction_b(mcp23s17, b):
    write_register(mcp23s17, IODIRB, b)

def write_register(mcp23s17, reg, b):
    mcp23s17.transaction(writing_bytes(address, reg, b))

def read_register(mcp23s17, reg):
    return ord(mcp23s17.transaction(writing_bytes(address+1, reg), reading(1))[0])

########NEW FILE########
__FILENAME__ = test_timerfd

from time import time, sleep
from quick2wire.timerfd import Timer, timespec, itimerspec
import pytest


@pytest.mark.loopback
@pytest.mark.timer
def test_timespec_can_be_created_from_seconds():
    t = timespec.from_seconds(4.125)
    assert t.sec == 4
    assert t.nsec == 125000000


@pytest.mark.loopback
@pytest.mark.timer
def test_itimerspec_can_be_created_from_seconds():
    t = itimerspec.from_seconds(offset=4.125, interval=1.25)
    assert t.value.sec == 4
    assert t.value.nsec == 125000000
    assert t.interval.sec == 1
    assert t.interval.nsec == 250000000


@pytest.mark.loopback
@pytest.mark.timer
def test_timer_waits_for_time_to_pass():
    with Timer(offset=0.125) as timer:
        start = time()
        
        timer.start()
        timer.wait()
        
        duration = time() - start
        
        assert duration >= 0.125


@pytest.mark.loopback
@pytest.mark.timer
def test_timer_can_repeat_with_interval():
    with Timer(interval=0.125) as timer:
        start = time()
        
        timer.start()
        timer.wait()
        timer.wait()
        
        duration = time() - start
        
        assert duration >= 0.25


@pytest.mark.loopback
@pytest.mark.timer
def test_timer_can_repeat_with_interval_after_offset():
    with Timer(offset=0.25, interval=0.125) as timer:
        start = time()
        
        timer.start()
        timer.wait()
        timer.wait()
        timer.wait()
        
        duration = time() - start
        
        assert duration >= 0.5


@pytest.mark.loopback
@pytest.mark.timer
def test_can_change_offset_while_timer_is_running():
    with Timer(offset=1.0) as timer:
        start = time()
        timer.start()
        timer.offset = 0.125
        timer.wait()
        
        duration = time() - start
        
        assert duration < 1


@pytest.mark.loopback
@pytest.mark.timer
def test_can_change_interval_while_timer_is_running():
    with Timer(offset=0.125, interval=1.0) as timer:
        start = time()
        timer.start()
        timer.wait()
        timer.interval = 0.125
        timer.wait()
        
        duration = time() - start
        
        assert duration < 1


@pytest.mark.loopback
@pytest.mark.timer
def test_timer_cannot_be_started_if_offset_and_interval_are_both_zero():
    with Timer() as timer:
        try:
            timer.start()
            assert False, "should have thrown ValueError"
        except ValueError:
            # expected
            pass


@pytest.mark.loopback
@pytest.mark.timer
def test_timer_reports_how_many_times_it_triggered_since_last_wait():
    with Timer(interval=0.0125) as timer:
        timer.start()
        sleep(0.5)
        n = timer.wait()
        
        assert n >= 4

########NEW FILE########
__FILENAME__ = timerfd


import math
import os
from ctypes import *
import struct
from contextlib import closing
import quick2wire.syscall as syscall


# From <time.h>

time_t = c_long

clockid_t = c_ulong

class timespec(Structure):
    _fields_ = [("sec", time_t),
                ("nsec", c_long)]
    
    __slots__ = [name for name,type in _fields_]
    
    @classmethod
    def from_seconds(cls, secs):
        t = cls()
        t.seconds = secs
        return t
    
    @property
    def seconds(self):
        if self.nsec == 0:
            return self.sec
        else:
            return self.sec + self.nsec / 1000000000.0
        
    @seconds.setter
    def seconds(self, secs):
        fractional, whole = math.modf(secs)
        self.sec = int(whole)
        self.nsec = int(fractional * 1000000000)


class itimerspec(Structure):
    _fields_ = [("interval", timespec), 
                ("value", timespec)]
    
    __slots__ = [name for name,type in _fields_]
    
    @classmethod
    def from_seconds(cls, offset, interval):
        spec = cls()
        spec.value.seconds = offset
        spec.interval.seconds = interval
        return spec


# from <bits/time.h>

CLOCK_REALTIME           = 0 # Identifier for system-wide realtime clock.
CLOCK_MONOTONIC	         = 1 # Monotonic system-wide clock.
CLOCK_PROCESS_CPUTIME_ID = 2 # High-resolution timer from the CPU
CLOCK_THREAD_CPUTIME_ID	 = 3 # Thread-specific CPU-time clock. 
CLOCK_MONOTONIC_RAW      = 4 # Monotonic system-wide clock, not adjusted for frequency scaling. 
CLOCK_REALTIME_COARSE    = 5 # Identifier for system-wide realtime clock, updated only on ticks. 
CLOCK_MONOTONIC_COARSE   = 6 # Monotonic system-wide clock, updated only on ticks. 
CLOCK_BOOTTIME	         = 7 # Monotonic system-wide clock that includes time spent in suspension. 
CLOCK_REALTIME_ALARM     = 8 # Like CLOCK_REALTIME but also wakes suspended system.
CLOCK_BOOTTIME_ALARM     = 9 # Like CLOCK_BOOTTIME but also wakes suspended system.


# From <sys/timerfd.h>

# Bits to be set in the FLAGS parameter of `timerfd_create'.
TFD_CLOEXEC = 0o2000000,
TFD_NONBLOCK = 0o4000

# Bits to be set in the FLAGS parameter of `timerfd_settime'.
TFD_TIMER_ABSTIME = 1 << 0



# Return file descriptor for new interval timer source.
#
# extern int timerfd_create (clockid_t __clock_id, int __flags)

timerfd_create = syscall.lookup(c_int, "timerfd_create", (clockid_t, c_int))

# Set next expiration time of interval timer source UFD to UTMR.  If
# FLAGS has the TFD_TIMER_ABSTIME flag set the timeout value is
# absolute.  Optionally return the old expiration time in OTMR.
#
# extern int timerfd_settime (int __ufd, int __flags,
# 			      __const struct itimerspec *__utmr,
# 			      struct itimerspec *__otmr)
timerfd_settime = syscall.lookup(c_int, "timerfd_settime", (c_int, c_int, POINTER(itimerspec), POINTER(itimerspec)))

# Return the next expiration time of UFD.
#
# extern int timerfd_gettime (int __ufd, struct itimerspec *__otmr)

timerfd_gettime = syscall.lookup(c_int, "timerfd_gettime", (c_int, POINTER(itimerspec)))


class Timer(syscall.SelfClosing):
    """A one-shot or repeating timer that can be added to a Selector."""
    
    def __init__(self, offset=0, interval=0, blocking=True, clock=CLOCK_REALTIME):
        """Creates a new Timer.
        
        Arguments:
        offset   -- the initial expiration time, measured in seconds from
                    the call to start().
        interval -- if non-zero, the interval for periodic timer expirations, 
                    measured in seconds.
        blocking -- if False calls to wait() do not block until the timer 
                    expires but return 0 if the timer has not expired. 
                    (default = True)
        clock    -- the system clock used to measure time:
                    CLOCK_REALTIME  -- system-wide realtime clock.
                    CLOCK_MONOTONIC -- monotonic system-wide clock.
        """
        self._clock = clock
        self._flags = (not blocking)*TFD_NONBLOCK
        self._fd = None
        self._offset = offset
        self._interval = interval
        self._started = False
    
    def close(self):
        """Closes the Timer and releases its file descriptor."""
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        
    def fileno(self):
        """Returns the Timer's file descriptor."""
        if self._fd is None:
            self._fd = timerfd_create(self._clock, self._flags)
        return self._fd

    @property
    def offset(self):
        """the initial expiration time, measured in seconds from the call to start()."""
        return self._offset
    
    @offset.setter
    def offset(self, new_offset):
        self._offset = new_offset
        if self._started:
            self._apply_schedule()
    
    @property
    def interval(self):
        """The interval, specified in seconds, with which the timer will repeat.
        
        If zero, the timer only fires once, when the offset expires.
        """
        return self._interval
    
    @interval.setter
    def interval(self, new_interval):
        self._interval = new_interval
        if self._started:
            self._apply_schedule()
    
    def start(self):
        """Starts the timer running.
        
        Raises:
        ValueError -- if offset and interval are both zero.
        """
        if self._offset == 0 and self._interval == 0:
            raise ValueError("timer will not fire because offset and interval are both zero")
        
        self._apply_schedule()
        self._started = True
        
    def stop(self):
        """Stops the timer running. Any scheduled timer events will not fire."""
        self._schedule(0, 0)
        self._started = False
    
    def wait(self):
        """Receives timer events.
        
        If the timer has already expired one or more times since its
        settings were last modified or wait() was last called then
        wait() returns the number of expirations that have occurred.

        If no timer expirations have occurred, then the call either
        blocks until the next timer expiration, or returns 0 if the
        Timer is non-blocking (was created with the blocking parameter
        set to False).
        
        Raises:
        OSError -- an OS error occurred reading the state of the timer.
        """
        try:
            buf = os.read(self.fileno(), 8)
            return struct.unpack("Q", buf)[0]
        except OSError as e:
            if e.errno == errno.EAGAIN:
                return 0
            else:
                raise e
    
    def _apply_schedule(self):
        self._schedule(self._offset or self._interval, self._interval)
    
    def _schedule(self, offset, interval):
        spec = itimerspec.from_seconds(offset, interval)
        timerfd_settime(self.fileno(), 0, byref(spec), None)
    

########NEW FILE########
