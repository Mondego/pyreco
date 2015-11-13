__FILENAME__ = ConsoleLogger
# Copyright (C) 2011 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import sys
from time import time
from datetime import datetime

def formatNumber(n):
    """Format a positive integer in a more readable fashion."""
    if n < 0:
        raise ValueError('can only format positive integers')
    prefixes = 'KMGTP'
    whole = str(int(n))
    decimal = ''
    i = 0
    while len(whole) > 3:
        if i + 1 < len(prefixes):
            decimal = '.%s' % whole[-3:-1]
            whole = whole[:-3]
            i += 1
        else:
            break
    return '%s%s %s' % (whole, decimal, prefixes[i])

class ConsoleLogger(object):
    """This class will handle printing messages to the console."""

    TIME_FORMAT = '[%d/%m/%Y %H:%M:%S]'

    UPDATE_TIME = 1.0

    def __init__(self, miner, verbose=False):
        self.verbose = verbose
        self.miner = miner
        self.lastUpdate = time() - 1
        self.rate = 0
        self.accepted = 0
        self.invalid = 0
        self.lineLength = 0
        self.connectionType = None

    def reportRate(self, rate, update=True):
        """Used to tell the logger the current Khash/sec."""
        self.rate = rate
        if update:
            self.updateStatus()

    def reportType(self, type):
        self.connectionType = type

    def reportBlock(self, block):
        self.log('Currently on block: ' + str(block))

    def reportFound(self, hash, accepted):
        if accepted:
            self.accepted += 1
        else:
            self.invalid += 1

        hexHash = hash[::-1]
        hexHash = hexHash[:8].encode('hex')
        if self.verbose:
            self.log('Result %s... %s' % (hexHash,
                'accepted' if accepted else 'rejected'))
        else:
            self.log('Result: %s %s' % (hexHash[8:],
                'accepted' if accepted else 'rejected'))

    def reportMsg(self, message):
        self.log(('MSG: ' + message), True, True)

    def reportConnected(self, connected):
        if connected:
            self.log('Connected to server')
        else:
            self.log('Disconnected from server')

    def reportConnectionFailed(self):
        self.log('Failed to connect, retrying...')

    def reportDebug(self, message):
        if self.verbose:
            self.log(message)

    def updateStatus(self, force=False):
        #only update if last update was more than a second ago
        dt = time() - self.lastUpdate
        if force or dt > self.UPDATE_TIME:
            rate = self.rate if (not self.miner.idle) else 0
            type = " [" + str(self.connectionType) + "]" if self.connectionType is not None else ''
            status = (
                "[" + formatNumber(rate) + "hash/sec] "
                "[" + str(self.accepted) + " Accepted] "
                "[" + str(self.invalid) + " Rejected]" + type)
            self.say(status)
            self.lastUpdate = time()

    def say(self, message, newLine=False, hideTimestamp=False):
        #add new line if requested
        if newLine:
            message += '\n'
            if hideTimestamp:
                timestamp = ''
            else:
                timestamp = datetime.now().strftime(self.TIME_FORMAT) + ' '

            message = timestamp + message

        #erase the previous line
        if self.lineLength > 0:
            sys.stdout.write('\b \b' * self.lineLength)
            sys.stdout.write(' ' * self.lineLength)
            sys.stdout.write('\b \b' * self.lineLength)

        #print the line
        sys.stdout.write(message)
        sys.stdout.flush()

        #cache the current line length
        if newLine:
            self.lineLength = 0
        else:
            self.lineLength = len(message)

    def log(self, message, update=True, hideTimestamp=False):
        self.say(message, True, hideTimestamp)
        if update:
            self.updateStatus(True)

########NEW FILE########
__FILENAME__ = KernelInterface
# Copyright (C) 2011 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import os
from struct import pack, unpack
from hashlib import sha256
from twisted.internet import defer, reactor

# I'm using this as a sentinel value to indicate that an option has no default;
# it must be specified.
REQUIRED = object()

class KernelOption(object):
    """This works like a property, and is used in defining easy option tables
    for kernels.
    """

    def __init__(self, name, type, help=None, default=REQUIRED,
        advanced=False, **kwargs):
        self.localValues = {}
        self.name = name
        self.type = type
        self.help = help
        self.default = default
        self.advanced = advanced

    def __get__(self, instance, owner):
        if instance in self.localValues:
            return self.localValues[instance]
        else:
            return instance.interface._getOption(
                self.name, self.type, self.default)

    def __set__(self, instance, value):
        self.localValues[instance] = value

class CoreInterface(object):
    """An internal class provided for kernels to use when reporting info for
    one core.

    Only KernelInterface should create this.
    """

    def __init__(self, kernelInterface):
        self.kernelInterface = kernelInterface
        self.averageSamples = []
        self.kernelInterface.miner._addCore(self)

    def updateRate(self, rate):
        """Called by a kernel core to report its current rate."""

        numSamples = self.kernelInterface.miner.options.getAvgSamples()

        self.averageSamples.append(rate)
        self.averageSamples = self.averageSamples[-numSamples:]

        self.kernelInterface.miner.updateAverage()

    def getRate(self):
        """Retrieve the average rate for this core."""

        if not self.averageSamples:
            return 0

        return sum(self.averageSamples)/len(self.averageSamples)

    def getKernelInterface(self):
        return self.kernelInterface

class KernelInterface(object):
    """This is an object passed to kernels as an API back to the Phoenix
    framework.
    """

    def __init__(self, miner):
        self.miner = miner
        self._core = None

    def _getOption(self, name, type, default):
        """KernelOption uses this to read the actual value of the option."""
        if not name in self.miner.options.kernelOptions:
            if default == REQUIRED:
                self.fatal('Required option %s not provided!' % name)
            else:
                return default

        givenOption = self.miner.options.kernelOptions[name]
        if type == bool:
            # The following are considered true
            return givenOption is None or \
                givenOption.lower() in ('t', 'true', 'on', '1', 'y', 'yes')

        try:
            return type(givenOption)
        except (TypeError, ValueError):
            self.fatal('Option %s expects a value of type %s!' % (name, type))

    def getRevision(self):
        """Return the Phoenix core revision, so that kernels can require a
        minimum revision before operating (such as if they rely on a certain
        feature added in a certain revision)
        """

        return self.miner.REVISION

    def setWorkFactor(self, workFactor):
        """Deprecated. Kernels are now responsible for requesting optimal size
        work"""

    def setMeta(self, var, value):
        """Set metadata for this kernel."""

        self.miner.connection.setMeta(var, value)

    def fetchRange(self, size=None):
        """Fetch a range from the WorkQueue, optionally specifying a size
        (in nonces) to include in the range.
        """

        if size is None:
            return self.miner.queue.fetchRange()
        else:
            return self.miner.queue.fetchRange(size)

    def addStaleCallback(self, callback):
        """Register a new function to be called, with no arguments, whenever
        a new block comes out that would render all previous work stale,
        requiring a kernel to switch immediately.
        """

        # This should be implemented in a better way in the future...
        if callback not in self.miner.queue.staleCallbacks:
            self.miner.queue.staleCallbacks.append(callback)

    def removeStaleCallback(self, callback):
        """Undo an addStaleCallback."""

        # Likewise.
        if callback in self.miner.queue.staleCallbacks:
            self.miner.queue.staleCallbacks.remove(callback)

    def addCore(self):
        """Return a CoreInterface for a new core."""
        return CoreInterface(self)

    def checkTarget(self, hash, target):
        """Utility function that the kernel can use to see if a nonce meets a
        target before sending it back to the core.

        Since the target is checked before submission anyway, this is mostly
        intended to be used in hardware sanity-checks.
        """

        # This for loop compares the bytes of the target and hash in reverse
        # order, because both are 256-bit little endian.
        for t,h in zip(target[::-1], hash[::-1]):
            if ord(t) > ord(h):
                return True
            elif ord(t) < ord(h):
                return False
        return True

    def calculateHash(self, nr, nonce):
        """Given a NonceRange and a nonce, calculate the SHA-256 hash of the
        solution. The resulting hash is returned as a string, which may be
        compared with the target as a 256-bit little endian unsigned integer.
        """
        # Sometimes kernels send weird nonces down the pipe. We can assume they
        # accidentally set bits outside of the 32-bit space. If the resulting
        # nonce is invalid, it will be caught anyway...
        nonce &= 0xFFFFFFFF

        staticDataUnpacked = unpack('<' + 'I'*19, nr.unit.data[:76])
        staticData = pack('>' + 'I'*19, *staticDataUnpacked)
        hashInput = pack('>76sI', staticData, nonce)
        return sha256(sha256(hashInput).digest()).digest()

    def foundNonce(self, nr, nonce):
        """Called by kernels when they may have found a nonce."""

        # Sometimes kernels send weird nonces down the pipe. We can assume they
        # accidentally set bits outside of the 32-bit space. If the resulting
        # nonce is invalid, it will be caught anyway...
        nonce &= 0xFFFFFFFF

        # Check if the block has changed while this NonceRange was being
        # processed by the kernel. If so, don't send it to the server.
        if self.miner.queue.isRangeStale(nr):
            return False

        # Check if the hash meets the full difficulty before sending.
        hash = self.calculateHash(nr, nonce)

        if self.checkTarget(hash, nr.unit.target):
            formattedResult = pack('<76sI', nr.unit.data[:76], nonce)
            d = self.miner.connection.sendResult(formattedResult)
            def callback(accepted):
                self.miner.logger.reportFound(hash, accepted)
            d.addCallback(callback)
            return True
        else:
            self.miner.logger.reportDebug("Result didn't meet full "
                   "difficulty, not sending")
            return False

    def debug(self, msg):
        """Log information as debug so that it can be viewed only when -v is
        enabled.
        """
        self.miner.logger.reportDebug(msg)

    def log(self, msg, withTimestamp=True, withIdentifier=True):
        """Log some general kernel information to the console."""
        self.miner.logger.log(msg, True, not withTimestamp)

    def error(self, msg=None):
        """The kernel has an issue that requires user attention."""
        if msg is not None:
            self.miner.logger.log('Kernel error: ' + msg)

    def fatal(self, msg=None):
        """The kernel has an issue that is preventing it from continuing to
        operate.
        """
        if msg is not None:
            self.miner.logger.log('FATAL kernel error: ' + msg, False)
        if reactor.running:
            reactor.stop()
        os._exit(0)

########NEW FILE########
__FILENAME__ = BFIPatcher
# Copyright (C) 2011 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import struct

class PatchError(Exception): pass

class BFIPatcher(object):
    """Patches .ELF files compiled for Evergreen GPUs; changes the microcode
    so that any BYTE_ALIGN_INT instructions become BFI_INT.
    """

    def __init__(self, interface):
        self.interface = interface

    def patch(self, data):
        """Run the process of patching an ELF."""

        self.interface.debug('Finding inner ELF...')
        innerPos = self.locateInner(data)
        self.interface.debug('Patching inner ELF...')
        inner = data[innerPos:]
        patched = self.patchInner(inner)
        self.interface.debug('Patch complete, returning to kernel...')
        return data[:innerPos] + patched

    def patchInner(self, data):
        sections = self.readELFSections(data)
        # We're looking for .text -- there should be two of them.
        textSections = filter(lambda x: x[0] == '.text', sections)
        if len(textSections) != 2:
            self.interface.debug('Inner ELF does not have 2 .text sections!')
            self.interface.debug('Sections are: %r' % sections)
            raise PatchError()
        name, offset, size = textSections[1]
        before, text2, after = (data[:offset], data[offset:offset+size],
            data[offset+size:])

        self.interface.debug('Patching instructions...')
        text2 = self.patchInstructions(text2)
        return before + text2 + after

    def patchInstructions(self, data):
        output = ''
        nPatched = 0
        for i in xrange(len(data)/8):
            inst, = struct.unpack('Q', data[i*8:i*8+8])
            # Is it BYTE_ALIGN_INT?
            if (inst&0x9003f00002001000) == 0x0001a00000000000:
                nPatched += 1
                inst ^=  (0x0001a00000000000 ^ 0x0000c00000000000) # BFI_INT
            output += struct.pack('Q', inst)
        self.interface.debug('BFI-patched %d instructions...' % nPatched)
        if nPatched < 60:
            self.interface.debug('Patch safety threshold not met!')
            raise PatchError()
        return output

    def locateInner(self, data):
        """ATI uses an ELF-in-an-ELF. I don't know why. This function's job is
        to find it.
        """

        pos = data.find('\x7fELF', 1)
        if pos == -1 or data.find('\x7fELF', pos+1) != -1: # More than 1 is bad
            self.interface.debug('Inner ELF not located!')
            raise PatchError()
        return pos

    def readELFSections(self, data):
        try:
            (ident1, ident2, type, machine, version, entry, phoff,
                shoff, flags, ehsize, phentsize, phnum, shentsize, shnum,
                shstrndx) = struct.unpack('QQHHIIIIIHHHHHH', data[:52])

            if ident1 != 0x64010101464c457f:
                self.interface.debug('Invalid ELF header!')
                raise PatchError()

            # No section header?
            if shoff == 0:
                return []

            # Find out which section contains the section header names
            shstr = data[shoff+shstrndx*shentsize:shoff+(shstrndx+1)*shentsize]
            (nameIdx, type, flags, addr, nameTableOffset, size, link, info,
                addralign, entsize) = struct.unpack('IIIIIIIIII', shstr)

            # Grab the section header.
            sh = data[shoff:shoff+shnum*shentsize]

            sections = []
            for i in xrange(shnum):
                rawEntry = sh[i*shentsize:(i+1)*shentsize]
                (nameIdx, type, flags, addr, offset, size, link, info,
                    addralign, entsize) = struct.unpack('IIIIIIIIII', rawEntry)
                nameOffset = nameTableOffset + nameIdx
                name = data[nameOffset:data.find('\x00', nameOffset)]
                sections.append((name, offset, size))

            return sections
        except struct.error:
            self.interface.debug('A struct.error occurred while reading ELF!')
            raise PatchError()
########NEW FILE########
__FILENAME__ = BFIPatcher
# Copyright (C) 2011 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import struct

class PatchError(Exception): pass

class BFIPatcher(object):
    """Patches .ELF files compiled for Evergreen GPUs; changes the microcode
    so that any BYTE_ALIGN_INT instructions become BFI_INT.
    """

    def __init__(self, interface):
        self.interface = interface

    def patch(self, data):
        """Run the process of patching an ELF."""

        self.interface.debug('Finding inner ELF...')
        innerPos = self.locateInner(data)
        self.interface.debug('Patching inner ELF...')
        inner = data[innerPos:]
        patched = self.patchInner(inner)
        self.interface.debug('Patch complete, returning to kernel...')
        return data[:innerPos] + patched

    def patchInner(self, data):
        sections = self.readELFSections(data)
        # We're looking for .text -- there should be two of them.
        textSections = filter(lambda x: x[0] == '.text', sections)
        if len(textSections) != 2:
            self.interface.debug('Inner ELF does not have 2 .text sections!')
            self.interface.debug('Sections are: %r' % sections)
            raise PatchError()
        name, offset, size = textSections[1]
        before, text2, after = (data[:offset], data[offset:offset+size],
            data[offset+size:])

        self.interface.debug('Patching instructions...')
        text2 = self.patchInstructions(text2)
        return before + text2 + after

    def patchInstructions(self, data):
        output = ''
        nPatched = 0
        for i in xrange(len(data)/8):
            inst, = struct.unpack('Q', data[i*8:i*8+8])
            # Is it BYTE_ALIGN_INT?
            if (inst&0x9003f00002001000) == 0x0001a00000000000:
                nPatched += 1
                inst ^=  (0x0001a00000000000 ^ 0x0000c00000000000) # BFI_INT
            output += struct.pack('Q', inst)
        self.interface.debug('BFI-patched %d instructions...' % nPatched)
        if nPatched < 60:
            self.interface.debug('Patch safety threshold not met!')
            raise PatchError()
        return output

    def locateInner(self, data):
        """ATI uses an ELF-in-an-ELF. I don't know why. This function's job is
        to find it.
        """

        pos = data.find('\x7fELF', 1)
        if pos == -1 or data.find('\x7fELF', pos+1) != -1: # More than 1 is bad
            self.interface.debug('Inner ELF not located!')
            raise PatchError()
        return pos

    def readELFSections(self, data):
        try:
            (ident1, ident2, type, machine, version, entry, phoff,
                shoff, flags, ehsize, phentsize, phnum, shentsize, shnum,
                shstrndx) = struct.unpack('QQHHIIIIIHHHHHH', data[:52])

            if ident1 != 0x64010101464c457f:
                self.interface.debug('Invalid ELF header!')
                raise PatchError()

            # No section header?
            if shoff == 0:
                return []

            # Find out which section contains the section header names
            shstr = data[shoff+shstrndx*shentsize:shoff+(shstrndx+1)*shentsize]
            (nameIdx, type, flags, addr, nameTableOffset, size, link, info,
                addralign, entsize) = struct.unpack('IIIIIIIIII', shstr)

            # Grab the section header.
            sh = data[shoff:shoff+shnum*shentsize]

            sections = []
            for i in xrange(shnum):
                rawEntry = sh[i*shentsize:(i+1)*shentsize]
                (nameIdx, type, flags, addr, offset, size, link, info,
                    addralign, entsize) = struct.unpack('IIIIIIIIII', rawEntry)
                nameOffset = nameTableOffset + nameIdx
                name = data[nameOffset:data.find('\x00', nameOffset)]
                sections.append((name, offset, size))

            return sections
        except struct.error:
            self.interface.debug('A struct.error occurred while reading ELF!')
            raise PatchError()
########NEW FILE########
__FILENAME__ = BFIPatcher
# Copyright (C) 2011 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import struct

class PatchError(Exception): pass

class BFIPatcher(object):
    """Patches .ELF files compiled for Evergreen GPUs; changes the microcode
    so that any BYTE_ALIGN_INT instructions become BFI_INT.
    """

    def __init__(self, interface):
        self.interface = interface

    def patch(self, data):
        """Run the process of patching an ELF."""

        self.interface.debug('Finding inner ELF...')
        innerPos = self.locateInner(data)
        self.interface.debug('Patching inner ELF...')
        inner = data[innerPos:]
        patched = self.patchInner(inner)
        self.interface.debug('Patch complete, returning to kernel...')
        return data[:innerPos] + patched

    def patchInner(self, data):
        sections = self.readELFSections(data)
        # We're looking for .text -- there should be two of them.
        textSections = filter(lambda x: x[0] == '.text', sections)
        if len(textSections) != 2:
            self.interface.debug('Inner ELF does not have 2 .text sections!')
            self.interface.debug('Sections are: %r' % sections)
            raise PatchError()
        name, offset, size = textSections[1]
        before, text2, after = (data[:offset], data[offset:offset+size],
            data[offset+size:])

        self.interface.debug('Patching instructions...')
        text2 = self.patchInstructions(text2)
        return before + text2 + after

    def patchInstructions(self, data):
        output = ''
        nPatched = 0
        for i in xrange(len(data)/8):
            inst, = struct.unpack('Q', data[i*8:i*8+8])
            # Is it BYTE_ALIGN_INT?
            if (inst&0x9003f00002001000) == 0x0001a00000000000:
                nPatched += 1
                inst ^=  (0x0001a00000000000 ^ 0x0000c00000000000) # BFI_INT
            output += struct.pack('Q', inst)
        self.interface.debug('BFI-patched %d instructions...' % nPatched)
        if nPatched < 60:
            self.interface.debug('Patch safety threshold not met!')
            raise PatchError()
        return output

    def locateInner(self, data):
        """ATI uses an ELF-in-an-ELF. I don't know why. This function's job is
        to find it.
        """

        pos = data.find('\x7fELF', 1)
        if pos == -1 or data.find('\x7fELF', pos+1) != -1: # More than 1 is bad
            self.interface.debug('Inner ELF not located!')
            raise PatchError()
        return pos

    def readELFSections(self, data):
        try:
            (ident1, ident2, type, machine, version, entry, phoff,
                shoff, flags, ehsize, phentsize, phnum, shentsize, shnum,
                shstrndx) = struct.unpack('QQHHIIIIIHHHHHH', data[:52])

            if ident1 != 0x64010101464c457f:
                self.interface.debug('Invalid ELF header!')
                raise PatchError()

            # No section header?
            if shoff == 0:
                return []

            # Find out which section contains the section header names
            shstr = data[shoff+shstrndx*shentsize:shoff+(shstrndx+1)*shentsize]
            (nameIdx, type, flags, addr, nameTableOffset, size, link, info,
                addralign, entsize) = struct.unpack('IIIIIIIIII', shstr)

            # Grab the section header.
            sh = data[shoff:shoff+shnum*shentsize]

            sections = []
            for i in xrange(shnum):
                rawEntry = sh[i*shentsize:(i+1)*shentsize]
                (nameIdx, type, flags, addr, offset, size, link, info,
                    addralign, entsize) = struct.unpack('IIIIIIIIII', rawEntry)
                nameOffset = nameTableOffset + nameIdx
                name = data[nameOffset:data.find('\x00', nameOffset)]
                sections.append((name, offset, size))

            return sections
        except struct.error:
            self.interface.debug('A struct.error occurred while reading ELF!')
            raise PatchError()
########NEW FILE########
__FILENAME__ = Miner
# Copyright (C) 2011 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import platform
from time import time
from twisted.internet import reactor
from minerutil.MMPProtocol import MMPClient
from KernelInterface import KernelInterface

#The main managing class for the miner itself.
class Miner(object):

    # This must be manually set for Git
    VER = (1, 7, 5)
    REVISION = reduce(lambda x,y: x*100+y, VER)
    VERSION = 'v%s' % '.'.join(str(x) for x in VER)

    def __init__(self):
        self.logger = None
        self.options = None
        self.connection = None
        self.kernel = None
        self.queue = None
        self.idle = True
        self.cores = []
        self.backup = False
        self.failures = 0
        self.lastMetaRate = 0.0
        self.lastRateUpdate = time()

    # Connection callbacks...
    def onFailure(self):
        self.logger.reportConnectionFailed()

        #handle failover if url2 has been specified
        if self.options.url2 is not None:
            self.failoverCheck()

    def onConnect(self):
        self.logger.reportConnected(True)
    def onDisconnect(self):
        self.logger.reportConnected(False)
    def onBlock(self, block):
        self.logger.reportBlock(block)
    def onMsg(self, msg):
        self.logger.reportMsg(msg)
    def onWork(self, work):
        self.logger.reportDebug('Server gave new work; passing to WorkQueue')
        self.queue.storeWork(work)
    def onLongpoll(self, lp):
        self.logger.reportType('RPC' + (' (+LP)' if lp else ''))
    def onPush(self, ignored):
        self.logger.log('LP: New work pushed')
    def onLog(self, message):
        self.logger.log(message)
    def onDebug(self, message):
        self.logger.reportDebug(message)

    def failoverCheck(self):
        if self.backup:
            if (self.failures >= 1):
                #disconnect and set connection to none
                self.connection.disconnect()
                self.connection = None

                #log
                self.logger.log("Backup server failed,")
                self.logger.log("attempting to return to primary server.")

                #reset failure count and return to primary server
                self.failures = 0
                self.backup = False
                self.connection = self.options.makeConnection(self)
                self.connection.connect()
            else:
                self.failures += 1
        else:
            #The main pool must fail 3 times before moving to the backup pool
            if (self.failures >= 2):
                #disconnect and set connection to none
                self.connection.disconnect()
                self.connection = None

                #log
                self.logger.log("Primary server failed too many times,")
                self.logger.log("attempting to connect to backup server.")

                #reset failure count and connect to backup server
                self.failures = 0
                self.backup = True
                self.connection = self.options.makeConnection(self, True)
                self.connection.connect()
            else:
                self.failures += 1

                #since the main pool may fail from time to time, decrement the
                #failure count after 5 minutes so we don't end up moving to the
                #back pool when it isn't nessesary
                def decrementFailures():
                    if self.failures > 1 and (not self.backup):
                        self.failures -= 1
                reactor.callLater(300, decrementFailures)

    def start(self, options):
        #Configures the Miner via the options specified and begins mining.

        self.options = options
        self.logger = self.options.makeLogger(self, self)
        self.connection = self.options.makeConnection(self)
        self.kernel = self.options.makeKernel(KernelInterface(self))
        self.queue = self.options.makeQueue(self)

        #log a message to let the user know that phoenix is starting
        self.logger.log("Phoenix %s starting..." % self.VERSION)

        #this will need to be changed to add new protocols
        if isinstance(self.connection, MMPClient):
            self.logger.reportType('MMP')
        else:
            self.logger.reportType('RPC')

        self.applyMeta()

        # Go!
        self.connection.connect()
        self.kernel.start()
        reactor.addSystemEventTrigger('before', 'shutdown', self.shutdown)

    def shutdown(self):
        """Disconnect from the server and kill the kernel."""
        self.kernel.stop()
        self.connection.disconnect()

    def applyMeta(self):
        #Applies any static metafields to the connection, such as version,
        #kernel, hardware, etc.

        # It's important to note here that the name is already put in place by
        # the Options's makeConnection function, since the Options knows the
        # user's desired name for this miner anyway.

        self.connection.setVersion(
            'phoenix', 'Phoenix Miner', self.VERSION)
        system = platform.system() + ' ' + platform.version()
        self.connection.setMeta('os', system)

    #called by CoreInterface to add cores for total hashrate calculation
    def _addCore(self, core):
        self.cores.append(core)

    #used by WorkQueue to report when the miner is idle
    def reportIdle(self, idle):

        #if idle status has changed force an update
        if self.idle != idle:
            if idle:
                self.idle = idle
                self.logger.log("Warning: work queue empty, miner is idle")
                self.logger.reportRate(0, True)
                self.connection.setMeta('rate', 0)
                self.lastMetaRate = time()
                self.idleFixer()
            else:
                self.idle = idle
                self.logger.updateStatus(True)

    #request work from the protocol every 15 seconds while idle
    def idleFixer(self):
        if self.idle:
            self.connection.requestWork()
            reactor.callLater(15, self.idleFixer)

    def updateAverage(self):
        #Query all mining cores for their Khash/sec rate and sum.

        total = 0
        if not self.idle:
            for core in self.cores:
                total += core.getRate()

        self.logger.reportRate(total)

        # Let's not spam the server with rate messages.
        if self.lastMetaRate+30 < time():
            self.connection.setMeta('rate', total)
            self.lastMetaRate = time()
########NEW FILE########
__FILENAME__ = ClientBase
# Copyright (C) 2011 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import struct

class AssignedWork(object):
    data = None
    mask = None
    target = None
    maxtime = None
    time = None
    identifier = None
    def setMaxTimeIncrement(self, n):
        self.time = n
        self.maxtime = struct.unpack('>I', self.data[68:72])[0] + n

class ClientBase(object):
    callbacksActive = True

    def _deactivateCallbacks(self):
        """Shut down the runCallback function. Typically used post-disconnect.
        """
        self.callbacksActive = False

    def runCallback(self, callback, *args):
        """Call the callback on the handler, if it's there, specifying args."""

        if not self.callbacksActive:
            return

        func = getattr(self.handler, 'on' + callback.capitalize(), None)
        if callable(func):
            func(*args)
########NEW FILE########
__FILENAME__ = Midstate
# Copyright (C) 2011 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import struct

# Some SHA-256 constants...
K = [
     0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
     0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
     0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
     0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
     0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
     0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
     0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
     0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
     0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
     0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
     0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
    ]

A0 = 0x6a09e667
B0 = 0xbb67ae85
C0 = 0x3c6ef372
D0 = 0xa54ff53a
E0 = 0x510e527f
F0 = 0x9b05688c
G0 = 0x1f83d9ab
H0 = 0x5be0cd19

def rotateright(i,p):
    """i>>>p"""
    p &= 0x1F # p mod 32
    return i>>p | ((i<<(32-p)) & 0xFFFFFFFF)

def addu32(*i):
    return sum(list(i))&0xFFFFFFFF

def calculateMidstate(data, state=None, rounds=None):
    """Given a 512-bit (64-byte) block of (little-endian byteswapped) data,
    calculate a Bitcoin-style midstate. (That is, if SHA-256 were little-endian
    and only hashed the first block of input.)
    """
    if len(data) != 64:
        raise ValueError('data must be 64 bytes long')

    w = list(struct.unpack('<IIIIIIIIIIIIIIII', data))

    if state is not None:
        if len(state) != 32:
            raise ValueError('state must be 32 bytes long')
        a,b,c,d,e,f,g,h = struct.unpack('<IIIIIIII', state)
    else:
        a = A0
        b = B0
        c = C0
        d = D0
        e = E0
        f = F0
        g = G0
        h = H0

    consts = K if rounds is None else K[:rounds]
    for k in consts:
        s0 = rotateright(a,2) ^ rotateright(a,13) ^ rotateright(a,22)
        s1 = rotateright(e,6) ^ rotateright(e,11) ^ rotateright(e,25)
        ma = (a&b) ^ (a&c) ^ (b&c)
        ch = (e&f) ^ ((~e)&g)

        h = addu32(h,w[0],k,ch,s1)
        d = addu32(d,h)
        h = addu32(h,ma,s0)

        a,b,c,d,e,f,g,h = h,a,b,c,d,e,f,g

        s0 = rotateright(w[1],7) ^ rotateright(w[1],18) ^ (w[1] >> 3)
        s1 = rotateright(w[14],17) ^ rotateright(w[14],19) ^ (w[14] >> 10)
        w.append(addu32(w[0], s0, w[9], s1))
        w.pop(0)

    if rounds is None:
        a = addu32(a, A0)
        b = addu32(b, B0)
        c = addu32(c, C0)
        d = addu32(d, D0)
        e = addu32(e, E0)
        f = addu32(f, F0)
        g = addu32(g, G0)
        h = addu32(h, H0)

    return struct.pack('<IIIIIIII', a, b, c, d, e, f, g, h)
########NEW FILE########
__FILENAME__ = MMPProtocol
# Copyright (C) 2011 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from twisted.internet import reactor, defer
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.protocols.basic import LineReceiver

from ClientBase import *

class MMPProtocolBase(LineReceiver):
    delimiter = '\r\n'
    commands = {} # To be overridden by superclasses...

    def lineReceived(self, line):
        # The protocol uses IRC-style argument passing. i.e. space-separated
        # arguments, with the final one optionally beginning with ':' (in which
        # case, the final argument is the only one that may contain spaces).
        halves = line.split(' :', 1)
        args = halves[0].split(' ') # The space-separated part.
        if len(halves) == 2:
            args.append(halves[1]) # The final argument; could contain spaces.

        cmd = args[0]
        args = args[1:]

        self.handleCommand(cmd, args)

    def handleCommand(self, cmd, args):
        """Handle a parsed command.

        This function takes care of converting arguments to their appropriate
        types and then calls the function handler. If a command is unknown,
        it is dispatched to illegalCommand.
        """
        function = getattr(self, 'cmd_' + cmd, None)

        if function is None or cmd not in self.commands:
            return

        types = self.commands[cmd]

        if len(types) != len(args):
            converted = False
        else:
            converted = True # Unless the below loop has a conversion problem.
            for i,t in enumerate(types):
                try:
                    args[i] = t(args[i])
                except (ValueError, TypeError):
                    converted = False
                    break

        if converted:
            function(*args)
        else:
            self.illegalCommand(cmd)

    def illegalCommand(self, cmd):
        pass # To be overridden by superclasses...

class MMPClientProtocol(MMPProtocolBase, ClientBase):
    """The actual connection to an MMP server. Probably not a good idea to use
    this directly, use MMPClient instead.
    """

    # A suitable default, but the server really should set this itself.
    target = ('\xff'*28) + ('\x00'*4)
    time = 0

    metaSent = False

    commands = {
        'MSG':      (str,),
        'TARGET':   (str,),
        'WORK':     (str, int),
        'BLOCK':    (int,),
        'ACCEPTED': (str,),
        'REJECTED': (str,),
        'TIME':     (int,),
    }

    def connectionMade(self):
        self.factory.connection = self
        self.runCallback('connect')
        self.sendLine('LOGIN %s :%s' % (self.factory.username,
                                        self.factory.password))
        # Got meta?
        for var,value in self.factory.meta.items():
            self.sendMeta(var, value)
        self.metaSent = True

    def connectionLost(self, reason):
        self.runCallback('disconnect')
        self.factory.connection = None
        self.factory._purgeDeferreds()

    def sendMeta(self, var, value):
        # Don't include ':' when sending a meta int, as per the protocol spec.
        colon = '' if isinstance(value, int) else ':'
        self.sendLine('META %s %s%s' % (var, colon, value))

    def cmd_MSG(self, message):
        self.runCallback('msg', message)

    def cmd_TARGET(self, target):
        try:
            t = target.decode('hex')
        except (ValueError, TypeError):
            return
        if len(t) == 32:
            self.target = t

    def cmd_TIME(self, time):
        self.time = time

    def cmd_WORK(self, work, mask):
        try:
            data = work.decode('hex')
        except (ValueError, TypeError):
            return
        if len(data) != 80:
            return
        wu = AssignedWork()
        wu.data = data
        wu.mask = mask
        wu.target = self.target
        wu.setMaxTimeIncrement(self.time)
        wu.identifier = data[4:36]
        self.runCallback('work', wu)
        # Since the server is giving work, we know it has accepted our
        # login details, so we can reset the factory's reconnect delay.
        self.factory.resetDelay()

    def cmd_BLOCK(self, block):
        self.runCallback('block', block)

    def cmd_ACCEPTED(self, data):
        self.factory._resultReturned(data, True)
    def cmd_REJECTED(self, data):
        self.factory._resultReturned(data, False)

class MMPClient(ReconnectingClientFactory, ClientBase):
    """This class implements an outbound connection to an MMP server.

    It's a factory so that it can automatically reconnect when the connection
    is lost.
    """

    protocol = MMPClientProtocol
    maxDelay = 60
    initialDelay = 0.2

    username = None
    password = None
    meta = {'version': 'MMPClient v1.0 by CFSworks'}

    deferreds = {}
    connection = None

    def __init__(self, handler, host, port, username, password):
        self.handler = handler
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def buildProtocol(self, addr):
        p = self.protocol()
        p.factory = self
        p.handler = self.handler
        return p

    def clientConnectionFailed(self, connector, reason):
        self.runCallback('failure')

        return ReconnectingClientFactory.clientConnectionFailed(
            self, connector, reason)

    def connect(self):
        """Tells the MMPClient to connect if it hasn't already."""

        reactor.connectTCP(self.host, self.port, self)

    def disconnect(self):
        """Tells the MMPClient to disconnect or stop connecting.
        The MMPClient shouldn't be used again.
        """

        self._deactivateCallbacks()

        if self.connection is not None:
            self.connection.transport.loseConnection()

        self.stopTrying()

    def requestWork(self):
        """If connected, ask the server for more work. The request is not sent
        if the client isn't connected, since the server will provide work upon
        next login anyway.
        """
        if self.connection is not None:
            self.connection.sendLine('MORE')

    def setMeta(self, var, value):
        """Set a metavariable, which gets sent to the server on-connect (or
        immediately, if already connected.)
        """
        self.meta[var] = value
        if self.connection and self.connection.metaSent:
            self.connection.sendMeta(var, value)

    def setVersion(self, shortname, longname=None, version=None, author=None):
        """Tells the protocol the application's version."""

        vstr = longname if longname is not None else shortname

        if version is not None:
            if not version.startswith('v') and not version.startswith('r'):
                version = 'v' + version
            vstr += ' ' + version

        if author is not None:
            vstr += ' by ' + author

        self.setMeta('version', vstr)

    def sendResult(self, result):
        """Submit a work result to the server. Returns a deferred which
        provides a True/False depending on whether or not the server
        accepetd the work.
        """
        if self.connection is None:
            return defer.succeed(False)

        d = defer.Deferred()

        if result in self.deferreds:
            self.deferreds[result].chainDeferred(d)
        else:
            self.deferreds[result] = d

        self.connection.sendLine('RESULT ' + result.encode('hex'))
        return d

    def _purgeDeferreds(self):
        for d in self.deferreds.values():
            d.callback(False)
        self.deferreds = {}

    def _resultReturned(self, data, accepted):
        try:
            data = data.decode('hex')
        except (TypeError, ValueError):
            return

        if data in self.deferreds:
            self.deferreds[data].callback(accepted)
            del self.deferreds[data]
########NEW FILE########
__FILENAME__ = RPCProtocol
# Copyright (C) 2011 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import urlparse
import json
import sys
import httplib
import socket
from twisted.internet import defer, reactor, error, threads
from twisted.python import failure

from ClientBase import ClientBase, AssignedWork

class ServerMessage(Exception): pass

class HTTPBase(object):
    connection = None
    timeout = None
    __lock = None
    __response = None

    def __makeResponse(self, *args, **kwargs):
        # This function exists as a workaround: If the connection is closed,
        # we also want to kill the response to allow the socket to die, but
        # httplib doesn't keep the response hanging around at all, so we need
        # to intercept its creation (hence this function) and store it.
        self.__response = httplib.HTTPResponse(*args, **kwargs)
        return self.__response

    def doRequest(self, *args):
        if self.__lock is None:
            self.__lock = defer.DeferredLock()
        return self.__lock.run(threads.deferToThread, self._doRequest, *args)

    def closeConnection(self):
        if self.connection is not None:
            if self.connection.sock is not None:
                self.connection.sock._sock.close()
            try:
                self.connection.close()
            except (AttributeError):
                #This is to fix "'NoneType' object has no attribute 'close'"
                #Theoretically this shouldn't be possible as we specifically
                #verify that self.connection isn't NoneType before trying to
                #call close(). I would add a debug message here, but HTTPBase
                #isn't passed a reference to the miner. The stack trace causing
                #this problem originates from the errback on line 138 (ask())
                #Most likely some sort of threading problem (race condition)
                pass

        if self.__response is not None:
            try:
                self.__response.close()
            except (AttributeError):
                #This was added for the same reason as the above
                pass
        self.connection = None
        self.__response = None

    def _doRequest(self, url, *args):
        if self.connection is None:
            connectionClass = (httplib.HTTPSConnection
                               if url.scheme.lower() == 'https' else
                               httplib.HTTPConnection)
            self.connection = connectionClass(url.hostname,
                                              url.port,
                                              timeout=self.timeout)
            # Intercept the creation of the response class (see above)
            self.connection.response_class = self.__makeResponse
            self.connection.connect()
            self.connection.sock.setsockopt(socket.SOL_TCP,
                                            socket.TCP_NODELAY, 1)
            self.connection.sock.setsockopt(socket.SOL_SOCKET,
                                            socket.SO_KEEPALIVE, 1)
        try:
            self.connection.request(*args)
            response = self.connection.getresponse()
            headers = response.getheaders()
            data = response.read()
            return (headers, data)
        except (httplib.HTTPException, socket.error):
            self.closeConnection()
            raise

class RPCPoller(HTTPBase):
    """Polls the root's chosen bitcoind or pool RPC server for work."""

    timeout = 5

    def __init__(self, root):
        self.root = root
        self.askInterval = None
        self.askCall = None
        self.currentAsk = None

    def setInterval(self, interval):
        """Change the interval at which to poll the getwork() function."""
        self.askInterval = interval
        self._startCall()

    def _startCall(self):
        self._stopCall()
        if self.root.disconnected:
            return
        if self.askInterval:
            self.askCall = reactor.callLater(self.askInterval, self.ask)
        else:
            self.askCall = None

    def _stopCall(self):
        if self.askCall:
            try:
                self.askCall.cancel()
            except (error.AlreadyCancelled, error.AlreadyCalled):
                pass
            self.askCall = None

    def ask(self):
        """Run a getwork request immediately."""

        if self.currentAsk and not self.currentAsk.called:
             return
        self._stopCall()

        self.currentAsk = self.call('getwork')

        def errback(failure):
            try:
                if failure.check(ServerMessage):
                    self.root.runCallback('msg', failure.getErrorMessage())
                self.root._failure()
            finally:
                self._startCall()

        self.currentAsk.addErrback(errback)

        def callback(x):
            try:
                try:
                    (headers, result) = x
                except TypeError:
                    return
                self.root.handleWork(result, headers)
                self.root.handleHeaders(headers)
            finally:
                self._startCall()
        self.currentAsk.addCallback(callback)

    @defer.inlineCallbacks
    def call(self, method, params=[]):
        """Call the specified remote function."""

        body = json.dumps({'method': method, 'params': params, 'id': 1})
        path = self.root.url.path or '/'
        if self.root.url.query:
            path += '?' + self.root.url.query
        response = yield self.doRequest(
            self.root.url,
            'POST',
            path,
            body,
            {
                'Authorization': self.root.auth,
                'User-Agent': self.root.version,
                'Content-Type': 'application/json',
                'X-Work-Identifier': '1'
            })

        (headers, data) = response
        result = self.parse(data)
        defer.returnValue((dict(headers), result))

    @classmethod
    def parse(cls, data):
        """Attempt to load JSON-RPC data."""

        response = json.loads(data)
        try:
            message = response['error']['message']
        except (KeyError, TypeError):
            pass
        else:
            raise ServerMessage(message)

        return response.get('result')

class LongPoller(HTTPBase):
    """Polls a long poll URL, reporting any parsed work results to the
    callback function.
    """

    #Changed to 3600, since 600 seconds will cause it to reconnect
    #once every 10 minutes. Most pools will not cancel a long poll if the block
    #exceeds 10 minutes. 60 minutes should be a sane value for this.
    timeout = 3600

    def __init__(self, url, root):
        self.url = url
        self.root = root
        self.polling = False

    def start(self):
        """Begin requesting data from the LP server, if we aren't already..."""
        if self.polling:
            return
        self.polling = True
        self._request()

    def _request(self):
        if self.polling:
            path = self.url.path or '/'
            if self.url.query:
                path += '?' + self.url.query
            d = self.doRequest(
                self.url,
                'GET',
                path,
                None,
                {
                    'Authorization': self.root.auth,
                    'User-Agent': self.root.version,
                    'X-Work-Identifier': '1'
                })
            d.addBoth(self._requestComplete)

    def stop(self):
        """Stop polling. This LongPoller probably shouldn't be reused."""
        self.polling = False
        self.closeConnection()

    def _requestComplete(self, response):
        try:
            if not self.polling:
                return

            if isinstance(response, failure.Failure):
                return

            try:
                (headers, data) = response
            except TypeError:
                #handle case where response doesn't contain valid data
                self.root.runCallback('debug', 'TypeError in LP response:')
                self.root.runCallback('debug', str(response))
                return

            try:
                result = RPCPoller.parse(data)
            except ValueError:
                return
            except ServerMessage:
                exctype, value = sys.exc_info()[:2]
                self.root.runCallback('msg', str(value))
                return

        finally:
            self._request()

        self.root.handleWork(result, headers, True)

class RPCClient(ClientBase):
    """The actual root of the whole RPC client system."""

    def __init__(self, handler, url):
        self.handler = handler
        self.url = url
        self.params = {}
        for param in url.params.split('&'):
            s = param.split('=',1)
            if len(s) == 2:
                self.params[s[0]] = s[1]
        self.auth = 'Basic ' + ('%s:%s' % (
            url.username, url.password)).encode('base64').strip()
        self.version = 'RPCClient/2.0'

        self.poller = RPCPoller(self)
        self.longPoller = None # Gets created later...
        self.disconnected = False
        self.saidConnected = False
        self.block = None
        self.setupMaxtime()

    def connect(self):
        """Begin communicating with the server..."""

        self.poller.ask()

    def disconnect(self):
        """Cease server communications immediately. The client is probably not
        reusable, so it's probably best not to try.
        """

        self._deactivateCallbacks()
        self.disconnected = True
        self.poller.setInterval(None)
        self.poller.closeConnection()
        if self.longPoller:
            self.longPoller.stop()
            self.longPoller = None

    def setupMaxtime(self):
        try:
            self.maxtime = int(self.params['maxtime'])
            if self.maxtime < 0:
                self.maxtime = 0
            elif self.maxtime > 3600:
                self.maxtime = 3600
        except (KeyError, ValueError):
            self.maxtime = 60

    def setMeta(self, var, value):
        """RPC clients do not support meta. Ignore."""

    def setVersion(self, shortname, longname=None, version=None, author=None):
        if version is not None:
            self.version = '%s/%s' % (shortname, version)
        else:
            self.version = shortname

    def requestWork(self):
        """Application needs work right now. Ask immediately."""
        self.poller.ask()

    def sendResult(self, result):
        """Sends a result to the server, returning a Deferred that fires with
        a bool to indicate whether or not the work was accepted.
        """

        # Must be a 128-byte response, but the last 48 are typically ignored.
        result += '\x00'*48

        d = self.poller.call('getwork', [result.encode('hex')])

        def errback(*ignored):
            return False # ANY error while turning in work is a Bad Thing(TM).

        #we need to return the result, not the headers
        def callback(x):
            try:
                (headers, accepted) = x
            except TypeError:
                self.runCallback('debug',
                        'TypeError in RPC sendResult callback')
                return False

            if (not accepted):
                self.handleRejectReason(headers)

            return accepted

        d.addErrback(errback)
        d.addCallback(callback)
        return d

    #if the server sends a reason for reject then print that
    def handleRejectReason(self, headers):
        reason = headers.get('x-reject-reason')
        if reason is not None:
            self.runCallback('debug', 'Reject reason: ' + str(reason))

    def useAskrate(self, variable):
        defaults = {'askrate': 10, 'retryrate': 15, 'lpaskrate': 0}
        try:
            askrate = int(self.params[variable])
        except (KeyError, ValueError):
            askrate = defaults.get(variable, 10)
        self.poller.setInterval(askrate)

    def handleWork(self, work, headers, pushed=False):
        if work is None:
            return;

        try:
            rollntime = headers.get('x-roll-ntime')
        except:
            rollntime = None

        if rollntime:
            if rollntime.lower().startswith('expire='):
                try:
                    maxtime = int(rollntime[7:])
                except:
                    #if the server supports rollntime but doesn't format the
                    #request properly, then use a sensible default
                    maxtime = self.maxtime
            else:
                if rollntime.lower() in ('t', 'true', 'on', '1', 'y', 'yes'):
                    maxtime = self.maxtime
                elif rollntime.lower() in ('f', 'false', 'off', '0', 'n', 'no'):
                    maxtime = 0
                else:
                    try:
                        maxtime = int(rollntime)
                    except:
                        maxtime = self.maxtime
        else:
            maxtime = 0

        if self.maxtime < maxtime:
            maxtime = self.maxtime

        if not self.saidConnected:
            self.saidConnected = True
            self.runCallback('connect')
            self.useAskrate('askrate')

        aw = AssignedWork()
        aw.data = work['data'].decode('hex')[:80]
        aw.target = work['target'].decode('hex')
        aw.mask = work.get('mask', 32)
        aw.setMaxTimeIncrement(maxtime)
        aw.identifier = work.get('identifier', aw.data[4:36])
        if pushed:
            self.runCallback('push', aw)
        self.runCallback('work', aw)

    def handleHeaders(self, headers):
        try:
            block = int(headers['x-blocknum'])
        except (KeyError, ValueError):
            pass
        else:
            if self.block != block:
                self.block = block
                self.runCallback('block', block)
        try:
            longpoll = headers.get('x-long-polling')
        except:
            longpoll = None

        if longpoll:
            lpParsed = urlparse.urlparse(longpoll)
            lpURL = urlparse.ParseResult(
                lpParsed.scheme or self.url.scheme,
                lpParsed.netloc or self.url.netloc,
                lpParsed.path, lpParsed.query, '', '')
            if self.longPoller and self.longPoller.url != lpURL:
                self.longPoller.stop()
                self.longPoller = None
            if not self.longPoller:
                self.longPoller = LongPoller(lpURL, self)
                self.longPoller.start()
                self.useAskrate('lpaskrate')
                self.runCallback('longpoll', True)
        elif self.longPoller:
            self.longPoller.stop()
            self.longPoller = None
            self.useAskrate('askrate')
            self.runCallback('longpoll', False)

    def _failure(self):
        if self.saidConnected:
            self.saidConnected = False
            self.runCallback('disconnect')
        else:
            self.runCallback('failure')
        self.useAskrate('retryrate')
        if self.longPoller:
            self.longPoller.stop()
            self.longPoller = None
            self.runCallback('longpoll', False)

########NEW FILE########
__FILENAME__ = phoenix
#!/usr/bin/python

# Copyright (C) 2011 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import imp
from sys import exit
from twisted.internet import reactor
from optparse import OptionParser

import minerutil
from ConsoleLogger import ConsoleLogger
from WorkQueue import WorkQueue
from Miner import Miner

class CommandLineOptions(object):
    """Implements the Options interface for user-specified command-line
    arguments.
    """

    def __init__(self):
        self.parsedSettings = None
        self.url = None
        self.url2 = None
        self.logger = None
        self.kernel = None
        self.queue = None
        self.kernelOptions = {}
        self._parse()

    def _parse(self):
        parser = OptionParser(usage="%prog -u URL [-k kernel] [kernel params]")
        parser.add_option("-v", "--verbose", action="store_true",
            dest="verbose", default=False, help="show debug messages")
        parser.add_option("-k", "--kernel", dest="kernel", default="phatk2",
            help="the name of the kernel to use")
        parser.add_option("-u", "--url", dest="url", default=None,
            help="the URL of the mining server to work for [REQUIRED]")
        parser.add_option("-b", "--backupurl", dest="url2", default=None,
            help="the URL of the backup mining server to work for if the "
            "primary is down [OPTIONAL]")
        parser.add_option("-q", "--queuesize", dest="queuesize", type="int",
            default=1, help="how many work units to keep queued at all times")
        parser.add_option("-a", "--avgsamples", dest="avgsamples", type="int",
            default=10,
            help="how many samples to use for hashrate average")

        self.parsedSettings, args = parser.parse_args()

        if self.parsedSettings.url is None:
            parser.print_usage()
            exit()
        else:
            self.url = self.parsedSettings.url
            self.url2 = self.parsedSettings.url2

        for arg in args:
            self._kernelOption(arg)

    def getQueueSize(self):
        return max(1, self.parsedSettings.queuesize)
    def getAvgSamples(self):
        return self.parsedSettings.avgsamples

    def _kernelOption(self, arg):
        pair = arg.split('=',1)
        if len(pair) < 2:
            pair.append(None)
        var, value = tuple(pair)
        self.kernelOptions[var.upper()] = value

    def makeLogger(self, requester, miner):
        if not self.logger:
            self.logger = ConsoleLogger(miner, self.parsedSettings.verbose)
        return self.logger

    def makeConnection(self, requester, backup = False):
        url = self.url2 if backup else self.url
        try:
            connection = minerutil.openURL(url, requester)
        except ValueError, e:
            print(e)
            exit()
        return connection

    def makeKernel(self, requester):
        if not self.kernel:
            module = self.parsedSettings.kernel
            try:
                file, filename, smt = imp.find_module(module, ['kernels'])
            except ImportError:
                print("Could not locate the specified kernel!")
                exit()
            kernelModule = imp.load_module(module, file, filename, smt)
            self.kernel = kernelModule.MiningKernel(requester)
        return self.kernel

    def makeQueue(self, requester):
        if not self.queue:
            self.queue = WorkQueue(requester, self)
        return self.queue

if __name__ == '__main__':
    options = CommandLineOptions()
    miner = Miner()
    miner.start(options)

    reactor.run()
########NEW FILE########
__FILENAME__ = QueueReader
# Copyright (C) 2011 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from time import time
from Queue import Queue, Empty
from twisted.internet import reactor, defer

from KernelInterface import CoreInterface

class QueueReader(object):
    """A QueueReader is a very efficient WorkQueue reader that keeps the next
    nonce range available at all times. The benefit is that threaded mining
    kernels waste no time getting the next range, since this class will have it
    completely requested and preprocessed for the next iteration.

    The QueueReader is iterable, so a dedicated mining thread needs only to do
    for ... in self.qr:
    """

    SAMPLES = 3

    def __init__(self, core, preprocessor=None, workSizeCallback=None):
        if not isinstance(core, CoreInterface):
            # Older kernels used to pass the KernelInterface, and not a
            # CoreInterface. This is deprecated. We'll go ahead and take care
            # of that, though...
            core = core.addCore()
        self.core = core
        self.interface = core.getKernelInterface()
        self.preprocessor = preprocessor
        self.workSizeCallback = workSizeCallback

        if self.preprocessor is not None:
            if not callable(self.preprocessor):
                raise TypeError('the given preprocessor must be callable')
        if self.workSizeCallback is not None:
            if not callable(self.workSizeCallback):
                raise TypeError('the given workSizeCallback must be callable')

        # This shuttles work to the dedicated thread.
        self.dataQueue = Queue()

        # Used in averaging the last execution times.
        self.executionTimeSamples = []
        self.averageExecutionTime = None

        # This gets changed by _updateWorkSize.
        self.executionSize = None

        # Statistics accessed by the dedicated thread.
        self.currentData = None
        self.startedAt = None

    def start(self):
        """Called by the kernel when it's actually starting."""
        self._updateWorkSize(None, None)
        self._requestMore()
        # We need to know when the current NonceRange in the dataQueue is old.
        self.interface.addStaleCallback(self._staleCallback)

    def stop(self):
        """Called by the kernel when it's told to stop. This also brings down
        the loop running in the mining thread.
        """
        # Tell the other thread to exit cleanly.
        while not self.dataQueue.empty():
            try:
                self.dataQueue.get(False)
            except Empty:
                pass
        self.dataQueue.put(StopIteration())

    def _ranExecution(self, dt, nr):
        """An internal function called after an execution completes, with the
        time it took. Used to keep track of the time so kernels can use it to
        tune their execution times.
        """

        if dt > 0:
            self.core.updateRate(int(nr.size/dt/1000))

        self.executionTimeSamples.append(dt)
        self.executionTimeSamples = self.executionTimeSamples[-self.SAMPLES:]

        if len(self.executionTimeSamples) == self.SAMPLES:
            averageExecutionTime = (sum(self.executionTimeSamples) /
                                    len(self.executionTimeSamples))

            self._updateWorkSize(averageExecutionTime, nr.size)

    def _updateWorkSize(self, time, size):
        """An internal function that tunes the executionSize to that specified
        by the workSizeCallback; which is in turn passed the average of the
        last execution times.
        """
        if self.workSizeCallback:
            self.executionSize = self.workSizeCallback(time, size)

    def _requestMore(self):
        """This is used to start the process of making a new item available in
        the dataQueue, so the dedicated thread doesn't have to block.
        """

        # This should only run if there's no ready-to-go work in the queue.
        if not self.dataQueue.empty():
            return

        if self.executionSize is None:
            d = self.interface.fetchRange()
        else:
            d = self.interface.fetchRange(self.executionSize)

        def preprocess(nr):
            # If preprocessing is not necessary, just tuplize right away.
            if not self.preprocessor:
                return (nr, nr)

            d2 = defer.maybeDeferred(self.preprocessor, nr)

            # Tuplize the preprocessed result.
            def callback(x):
                return (x, nr)
            d2.addCallback(callback)
            return d2
        d.addCallback(preprocess)

        d.addCallback(self.dataQueue.put_nowait)

    def _staleCallback(self):
        """Called when the WorkQueue gets new work, rendering whatever is in
        dataQueue old.
        """

        #only clear queue and request more if no work present, since that
        #meas a request for more work is already in progress
        if not self.dataQueue.empty():
            # Out with the old...
            while not self.dataQueue.empty():
                try:
                    self.dataQueue.get(False)
                except Empty: continue
            # ...in with the new.
            self._requestMore()

    def __iter__(self):
        return self
    def next(self):
        """Since QueueReader is iterable, this is the function that runs the
        for-loop and dispatches work to the thread.

        This should be the only thread that executes outside of the Twisted
        main thread.
        """

        # If we just completed a range, we should tell the main thread.
        now = time()
        if self.currentData:
            dt = now - self.startedAt
            # self.currentData[1] is the un-preprocessed NonceRange.
            reactor.callFromThread(self._ranExecution, dt, self.currentData[1])
        self.startedAt = now

        # Block for more data from the main thread. In 99% of cases, though,
        # there should already be something here.
        # Note that this comes back with either a tuple, or a StopIteration()
        self.currentData = self.dataQueue.get(True)

        # Does the main thread want us to shut down, or pass some more data?
        if isinstance(self.currentData, StopIteration):
            raise self.currentData

        # We just took the only item in the queue. It needs to be restocked.
        reactor.callFromThread(self._requestMore)

        # currentData is actually a tuple, with item 0 intended for the kernel.
        return self.currentData[0]
########NEW FILE########
__FILENAME__ = WorkQueue
# Copyright (C) 2011 by jedi95 <jedi95@gmail.com> and
#                       CFSworks <CFSworks@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from minerutil.Midstate import calculateMidstate
from twisted.internet import defer
from collections import deque

"""A WorkUnit is a single unit containing 2^32 nonces. A single getWork
request returns a WorkUnit.
"""
class WorkUnit(object):
    data = None
    target = None
    midstate = None
    nonces = None
    base = None
    identifier = None

"""A NonceRange is a range of nonces from a WorkUnit, to be dispatched in a
single execution of a mining kernel. The size of the NonceRange can be
adjusted to tune the performance of the kernel.

This class doesn't actually do anything, it's just a well-defined container
that kernels can pull information out of.
"""
class NonceRange(object):

    def __init__(self, unit, base, size):
        self.unit = unit # The WorkUnit this NonceRange comes from.
        self.base = base # The base nonce.
        self.size = size # How many nonces this NonceRange says to test.


class WorkQueue(object):
    """A WorkQueue contains WorkUnits and dispatches NonceRanges when requested
    by the miner. WorkQueues dispatch deffereds when they runs out of nonces.
    """

    def __init__(self, miner, options):

        self.miner = miner
        self.queueSize = options.getQueueSize()
        self.logger = options.makeLogger(self, miner)

        self.queue = deque('', self.queueSize)
        self.deferredQueue = deque()
        self.currentUnit = None
        self.block = ''
        self.lastBlock = None

        # This is set externally. Not the best practice, but it can be changed
        # in the future.
        self.staleCallbacks = []

    # Called by foundNonce to check if a NonceRange is stale before submitting
    def isRangeStale(self, nr):
        return (nr.unit.identifier != self.block)

    def storeWork(self, aw):

        #check if this work matches the previous block
        if self.lastBlock is not None and (aw.identifier == self.lastBlock):
            self.logger.reportDebug('Server gave work from the previous '
                                    'block, ignoring.')
            #if the queue is too short request more work
            if (len(self.queue)) < (self.queueSize):
                self.miner.connection.requestWork()
            return

        #create a WorkUnit
        work = WorkUnit()
        work.data = aw.data
        work.target = aw.target
        work.midstate = calculateMidstate(work.data[:64])
        work.nonces = 2 ** aw.mask
        work.base = 0
        work.identifier = aw.identifier

        #check if there is a new block, if so reset queue
        newBlock = (aw.identifier != self.block)
        if newBlock:
            self.queue.clear()
            self.currentUnit = None
            self.lastBlock = self.block
            self.block = aw.identifier
            self.logger.reportDebug("New block (WorkQueue)")

        #clear the idle flag since we just added work to queue
        self.miner.reportIdle(False)

        #add new WorkUnit to queue
        if work.data and work.target and work.midstate and work.nonces:
            self.queue.append(work)

        #if the queue is too short request more work
        if (len(self.queue)) < (self.queueSize):
            self.miner.connection.requestWork()

        #if there is a new block notify kernels that their work is now stale
        if newBlock:
            for callback in self.staleCallbacks:
                callback()

        #check if there are deferred NonceRange requests pending
        #since requests to fetch a NonceRange can add additional deferreds to
        #the queue, cache the size beforehand to avoid infinite loops.
        for i in range(len(self.deferredQueue)):
            df, size = self.deferredQueue.popleft()
            d = self.fetchRange(size)
            d.chainDeferred(df)

    #gets the next WorkUnit from queue
    def getNext(self):

        #check if the queue will fall below desired size
        if (len(self.queue) - 1) < (self.queueSize):
            self.miner.connection.requestWork()

        #return next WorkUnit
        return self.queue.popleft()

    def getRangeFromUnit(self, size):

        #get remaining nonces
        noncesLeft = self.currentUnit.nonces - self.currentUnit.base

        #if there are enough nonces to fill the full reqest
        if noncesLeft >= size:
            nr = NonceRange(self.currentUnit, self.currentUnit.base, size)

            #check if this uses up the rest of the WorkUnit
            if size >= noncesLeft:
                self.currentUnit = None
            else:
                self.currentUnit.base += size

        #otherwise send whatever is left
        else:
            nr = NonceRange(
                self.currentUnit, self.currentUnit.base, noncesLeft)
            self.currentUnit = None

        #return the range
        return nr

    def fetchRange(self, size=0x10000):

        #make sure size is not too large
        size = min(size, 0x100000000)

        #make sure size is not too small
        size = max(size, 256)

        #check if the current unit exists
        if self.currentUnit is not None:

            #get a nonce range
            nr = self.getRangeFromUnit(size)

            #return the range
            return defer.succeed(nr)

        #if there is no current unit
        else:
            #if there is another unit in queue
            if len(self.queue) >= 1:

                #get the next unit from queue
                self.currentUnit = self.getNext()

                #get a nonce range
                nr = self.getRangeFromUnit(size)

                #return the range
                return defer.succeed(nr)

            #if the queue is empty
            else:

                #request more work
                self.miner.connection.requestWork()

                #report that the miner is idle
                self.miner.reportIdle(True)

                #set up and return deferred
                df = defer.Deferred()
                self.deferredQueue.append((df, size))
                return df

########NEW FILE########
